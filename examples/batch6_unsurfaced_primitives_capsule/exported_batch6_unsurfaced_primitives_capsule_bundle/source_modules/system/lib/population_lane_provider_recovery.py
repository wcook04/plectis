"""Wave 20: provider recovery + admission for the population lane's
transport-repair planner.

Wave 19 made transport repair structurally correct (only retry
transport-only rows, never re-run the cohort, suppress providers with
fresh transport failures). It correctly discovered that the canary's
two configured lanes are both unhealthy, so `rows_planned_for_retry=0`
under the current pool.

Wave 20 makes that bottleneck addressable. This module builds a
provider-recovery plan that distinguishes:

- `eligible_now`           — provider/model is configured, structurally
                              available, and not in active cooldown.
- `eligible_after_cooldown` — provider/model is in cooldown, but the
                              cooldown window will lapse and a retry is
                              possible thereafter.
- `temporarily_suppressed`  — has fresh transport failures in the
                              current transport-only set OR is in
                              active cooldown that has not lapsed.
- `structurally_unavailable` — not present in the compute provider
                              registry, or marked inactive there.

`build_provider_recovery_plan` returns a packet a repair planner can
use to (a) pick fallback candidates, (b) allow same-provider retry only
after cooldown/admission says yes, or (c) emit a hard
`provider_capacity_missing_for_transport_repair` blocker when no
actionable provider exists.

Read-only over `provider_health` and `compute_policy.load_provider_registry`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


# Wave 20: keep this in sync with tools/meta/control/python_navigation_population_lane.py::DEFAULT_LANES.
# Duplicated rather than imported to keep the metrics layer free of CLI deps.
DEFAULT_CONFIGURED_LANES: tuple[dict[str, Any], ...] = (
    {"provider_id": "nvidia_nim", "model_id": "deepseek-ai/deepseek-v4-flash", "structured_output": False, "timeout_s": 180},
    {"provider_id": "nvidia_nim", "model_id": "z-ai/glm5", "structured_output": False, "timeout_s": 180},
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Wave 22: model-scoped admission. The previous (Wave 20/21) admission
# layer aggregated fresh transport failures by provider_id only. That
# was too coarse: provider_health is already keyed by
# `<provider_id>:<model_id>`, so a `nvidia_nim:z-ai/glm-5.1` timeout
# would suppress every nvidia_nim model, including healthy alternates
# already present in the registry. The fix is a status-typed
# suppression policy.
TRANSPORT_SUPPRESSION_POLICY: dict[str, dict[str, str]] = {
    # 429 means the provider rate-limited; conservative default is
    # provider-wide because rate-limit windows usually span an account
    # / provider tier, not a specific model.
    "429": {"scope": "provider", "reason": "rate_limit_provider_wide_default"},
    # 5xx means the provider's hosting layer returned a server error;
    # not model-specific.
    "5xx": {"scope": "provider", "reason": "server_error_class_provider_wide"},
    # Timeout is usually model-specific (the model itself was slow);
    # the same provider's other models can still be tried.
    "timeout": {"scope": "provider_model", "reason": "model_specific_timeout"},
    # Worker errors typically reflect the chosen model's path through
    # the harness/adapter; model-specific by default.
    "worker_error": {"scope": "provider_model", "reason": "model_specific_worker_error"},
    # Row-fingerprint dedup blocks must NOT suppress provider/model
    # capacity — they're a per-row safety net, not a health signal.
    "blocked_duplicate": {
        "scope": "row_fingerprint",
        "reason": "row_dedup_block_does_not_suppress_capacity",
    },
}


def transport_suppression_scope(
    status: str,
    provider_id: str,
    model_id: str | None,
    *,
    row_job_id: str | None = None,
) -> dict[str, str]:
    """Wave 22: classify a transport failure's suppression scope.
    Returns {scope, key, reason}.

    - scope='provider'        — provider-wide; suppresses every model
                                 under that provider_id for the
                                 duration of the suppression window.
    - scope='provider_model'  — only suppresses (provider_id, model_id);
                                 sibling models on the same provider
                                 remain eligible.
    - scope='row_fingerprint' — does NOT suppress capacity; only marks
                                 the row.

    Unknown statuses default to `provider` (conservative).
    """
    policy = TRANSPORT_SUPPRESSION_POLICY.get(status)
    if not policy:
        return {
            "scope": "provider",
            "key": provider_id,
            "reason": f"unknown_transport_status_{status}_provider_wide_default",
        }
    scope = policy["scope"]
    if scope == "provider":
        return {"scope": "provider", "key": provider_id, "reason": policy["reason"]}
    if scope == "provider_model":
        return {
            "scope": "provider_model",
            "key": f"{provider_id}:{model_id or ''}",
            "reason": policy["reason"],
        }
    return {
        "scope": "row_fingerprint",
        "key": str(row_job_id or ""),
        "reason": policy["reason"],
    }


def _aggregate_scoped_failures(
    evidence: list[Mapping[str, Any]],
) -> tuple[dict[str, int], dict[tuple[str, str], int], dict[str, int]]:
    """Walk transport-only evidence rows and aggregate fresh failures
    into three scoped buckets:

    - provider-wide       (429, 5xx, unknown statuses)
    - provider:model       (timeout, worker_error)
    - row_fingerprint      (blocked_duplicate; informational only,
                            does NOT contribute to suppression)

    Both winner attempts and alternate-attempt failures are walked.
    The same (provider, model, status) is not double-counted within
    one row.
    """
    provider_wide: dict[str, int] = {}
    provider_model: dict[tuple[str, str], int] = {}
    row_blocks: dict[str, int] = {}
    for r in evidence:
        rj = str(r.get("row_job_id") or "")
        wp = str(r.get("winner_provider_id") or "")
        wm = str(r.get("winner_model_id") or "")
        ws = str(r.get("winner_status") or "")
        # Per-row dedup so we don't double-count winner + alternate
        # entries that name the same (provider, model, status).
        seen: set[tuple[str, str, str]] = set()
        if wp and ws:
            seen.add((wp, wm, ws))
            scope = transport_suppression_scope(ws, wp, wm or None, row_job_id=rj)
            if scope["scope"] == "provider":
                provider_wide[wp] = provider_wide.get(wp, 0) + 1
            elif scope["scope"] == "provider_model":
                provider_model[(wp, wm)] = provider_model.get((wp, wm), 0) + 1
            else:  # row_fingerprint
                row_blocks[rj] = row_blocks.get(rj, 0) + 1
        for att in (r.get("attempts_seen") or []):
            if not isinstance(att, Mapping):
                continue
            pid = str(att.get("provider_id") or "")
            mid = str(att.get("model_id") or "")
            st = str(att.get("receipt_status") or "")
            if not (pid and st) or st not in TRANSPORT_RECEIPT_KEYS:
                continue
            if (pid, mid, st) in seen:
                continue
            seen.add((pid, mid, st))
            scope = transport_suppression_scope(st, pid, mid or None, row_job_id=rj)
            if scope["scope"] == "provider":
                provider_wide[pid] = provider_wide.get(pid, 0) + 1
            elif scope["scope"] == "provider_model":
                provider_model[(pid, mid)] = provider_model.get((pid, mid), 0) + 1
            else:
                row_blocks[rj] = row_blocks.get(rj, 0) + 1
    return provider_wide, provider_model, row_blocks


# Local copy to avoid circular imports with population_lane_metrics.
TRANSPORT_RECEIPT_KEYS: frozenset[str] = frozenset({
    "429", "5xx", "timeout", "worker_error", "blocked_duplicate",
})


def _classify_admission(
    *,
    structurally_available: bool,
    health_record: Mapping[str, Any] | None,
    provider_wide_failures_in_set: int = 0,
    provider_model_failures_in_set: int = 0,
    now_iso: str,
    # Wave 20 back-compat: callers that still pass the single
    # `transport_failures_in_set` keyword get treated as provider-wide
    # (the conservative, pre-Wave-22 behavior).
    transport_failures_in_set: int | None = None,
) -> tuple[str, bool, bool, str | None]:
    """Wave 22: scoped admission. Suppress this (provider, model) lane
    when EITHER:
      - the provider has any provider-wide fresh transport failure
        (e.g. a 429 or 5xx); OR
      - this exact (provider, model) has a fresh model-scoped failure
        (e.g. a timeout or worker_error).

    Sibling models on the same provider remain eligible_now when only
    a model-scoped failure exists.

    Returns (admission_state, can_retry_now, can_retry_after_cooldown,
    suppression_reason).
    """
    if transport_failures_in_set is not None:
        # Legacy kwarg path: treat as provider-wide for back-compat
        # with Wave 20 callers.
        provider_wide_failures_in_set = max(
            provider_wide_failures_in_set, int(transport_failures_in_set)
        )
    total_suppression = (
        int(provider_wide_failures_in_set) + int(provider_model_failures_in_set)
    )
    if not structurally_available:
        return (
            "structurally_unavailable",
            False,
            False,
            "not_in_compute_provider_registry_or_inactive",
        )

    def _suppression_reason() -> str:
        bits: list[str] = []
        if provider_wide_failures_in_set > 0:
            bits.append(f"provider_wide_failures_(count={provider_wide_failures_in_set})")
        if provider_model_failures_in_set > 0:
            bits.append(f"provider_model_failures_(count={provider_model_failures_in_set})")
        return "; ".join(bits) or "transport_failures_in_current_transport_only_set"

    state = (health_record or {}).get("health_state") or "eligible"
    if state == "cooldown":
        try:
            from system.lib.python_navigation_population_provider_health import is_eligible
            past_cooldown = is_eligible(health_record or {}, now_iso=now_iso)
        except Exception:
            past_cooldown = False
        if past_cooldown:
            if total_suppression > 0:
                return ("temporarily_suppressed", False, True, _suppression_reason())
            return ("eligible_now", True, True, None)
        if total_suppression > 0:
            return (
                "temporarily_suppressed", False, True,
                "active_cooldown_plus_" + _suppression_reason(),
            )
        return ("eligible_after_cooldown", False, True, "active_cooldown_pending")
    # state == "eligible"
    if total_suppression > 0:
        return ("temporarily_suppressed", False, True, _suppression_reason())
    return ("eligible_now", True, True, None)


def _adapter_module_importable(adapter_module: str) -> bool:
    """Return True iff `adapter_module` is importable. Used by Wave 21
    discovery to reject candidate lanes whose registry pointer references
    an adapter that does not exist in the repo (e.g. provider configured
    in registry but no Python module shipped)."""
    if not adapter_module:
        return False
    try:
        import importlib
        importlib.import_module(adapter_module)
        return True
    except Exception:
        return False


def build_provider_capacity_discovery(
    repo_root: Path | str,
    *,
    lane_id: str,
    task_class: str = "populate_routing_atoms",
    configured_default_lanes: list[Mapping[str, Any]] | None = None,
    transport_only_evidence: list[Mapping[str, Any]] | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    """Wave 21: discover registry-backed candidate lanes for transport
    repair, beyond the lane's `DEFAULT_LANES` configuration.

    Walks `provider_registry.json`. For each provider:
      - rejects if `status != active`              → reason `inactive_provider`
      - rejects if task_class is forbidden         → reason `task_class_forbidden`
      - rejects if task_class is unregistered      → reason `task_class_unregistered`
      - rejects if operator_approval_required      → reason `approval_required`
      - rejects if adapter_module is not importable→ reason `missing_adapter`
      - rejects if !capabilities.chat_completion   → reason `not_chat_completion_capable`

    For each surviving (provider, model_profile):
      - rejects if model status == `inactive`      → reason `inactive_model`
      - otherwise: classifies admission via `_classify_admission`,
        emitting `eligible_now` only when no fresh transport failures
        in the current transport_only set AND health is eligible.

    Returns a packet with: configured_default_lanes,
    registry_candidate_lanes, adapter_available_lanes,
    eligible_now_lanes, ineligible_lanes (each ineligible carries a
    typed `reason`), and a `provider_capacity_unavailable_after_discovery`
    flag distinct from Wave 20's `provider_capacity_missing_for_transport_repair`.
    """
    repo_root = Path(repo_root)
    now_iso = now_iso or _now_iso()
    evidence = list(transport_only_evidence or [])
    if configured_default_lanes is None:
        configured_default_lanes = [dict(l) for l in DEFAULT_CONFIGURED_LANES]

    # Load registry. If absent, return an empty discovery packet rather
    # than raising — the caller can still distinguish "no registry"
    # from "registry has zero candidates".
    registry: Mapping[str, Any] = {}
    try:
        from system.lib import python_navigation_population_compute_policy as compute_policy
        registry = compute_policy.load_provider_registry(str(repo_root))
    except Exception:
        compute_policy = None  # type: ignore[assignment]

    # Health payload (for admission filtering of survivors).
    health_payload: Mapping[str, Any] = {}
    health_for_fn = None
    try:
        from system.lib.python_navigation_population_provider_health import load_health, health_for
        health_payload = load_health(repo_root, lane_id)
        health_for_fn = health_for
    except Exception:
        pass

    # Wave 22: aggregate fresh transport-failure counts at the right
    # scope (provider-wide vs provider:model) so 429/5xx don't
    # over-suppress sibling models, and timeout/worker_error don't
    # over-suppress unrelated providers.
    provider_wide_fresh, provider_model_fresh, _row_blocks = _aggregate_scoped_failures(evidence)

    registry_candidate_lanes: list[dict[str, Any]] = []
    adapter_available_lanes: list[dict[str, Any]] = []
    eligible_now_lanes: list[dict[str, Any]] = []
    ineligible_lanes: list[dict[str, Any]] = []

    providers = (registry.get("providers") if isinstance(registry, Mapping) else {}) or {}
    for pid, spec in providers.items():
        if not isinstance(spec, Mapping):
            continue
        status = str(spec.get("status") or "")
        if status != "active":
            ineligible_lanes.append({
                "provider_id": pid,
                "model_id": None,
                "reason": "inactive_provider",
                "detail": f"provider.status={status!r}",
            })
            continue
        capabilities = spec.get("capabilities") or {}
        if not bool(capabilities.get("chat_completion")):
            ineligible_lanes.append({
                "provider_id": pid,
                "model_id": None,
                "reason": "not_chat_completion_capable",
                "detail": "provider.capabilities.chat_completion is not True",
            })
            continue
        # Task-class admission (compute policy authority).
        task_verdict, task_rationale = (
            compute_policy.is_task_class_allowed(registry, pid, task_class)
            if compute_policy is not None
            else ("allowed", "no compute_policy module available")
        )
        if task_verdict == "forbidden":
            ineligible_lanes.append({
                "provider_id": pid, "model_id": None,
                "reason": "task_class_forbidden",
                "detail": task_rationale,
            })
            continue
        if task_verdict == "unregistered":
            ineligible_lanes.append({
                "provider_id": pid, "model_id": None,
                "reason": "task_class_unregistered",
                "detail": task_rationale,
            })
            continue
        if compute_policy is not None and compute_policy.operator_approval_required(registry, pid):
            ineligible_lanes.append({
                "provider_id": pid, "model_id": None,
                "reason": "approval_required",
                "detail": "registry.risk.operator_approval_required is True",
            })
            continue
        adapter_module = str(spec.get("adapter_module") or "")
        adapter_ok = _adapter_module_importable(adapter_module)
        if not adapter_ok:
            ineligible_lanes.append({
                "provider_id": pid, "model_id": None,
                "reason": "missing_adapter",
                "detail": f"adapter_module={adapter_module!r} not importable",
            })
            continue

        # Provider passes provider-level gates. Walk model_profiles.
        for profile_key, profile in (spec.get("model_profiles") or {}).items():
            if not isinstance(profile, Mapping):
                continue
            model_id = str(profile.get("model_id") or "")
            if not model_id:
                continue
            role = str(profile.get("role") or "")
            # Skip embedding / rerank roles — they aren't chat-completion
            # candidates for the populate_routing_atoms task class.
            if role.startswith("general_doctrine_text_retrieval") or "embed" in role or "rerank" in role:
                ineligible_lanes.append({
                    "provider_id": pid, "model_id": model_id,
                    "reason": "non_chat_completion_role",
                    "detail": f"model_profile role={role!r} is not a chat-completion lane",
                })
                continue
            model_status = str(profile.get("status") or "")
            if model_status == "inactive":
                ineligible_lanes.append({
                    "provider_id": pid, "model_id": model_id,
                    "reason": "inactive_model",
                    "detail": f"model_profile.status={model_status!r}",
                })
                continue
            candidate = {
                "provider_id": pid,
                "model_id": model_id,
                "profile_key": profile_key,
                "role": role,
                "model_status": model_status,
                "adapter_module": adapter_module,
            }
            registry_candidate_lanes.append(candidate)
            adapter_available_lanes.append(candidate)
            # Admission via Wave 20's classifier.
            record = None
            if health_for_fn is not None:
                try:
                    record = health_for_fn(health_payload, provider_id=pid, model_id=model_id, now_iso=now_iso)
                except Exception:
                    record = None
            provider_wide_in_set = int(provider_wide_fresh.get(pid, 0))
            provider_model_in_set = int(provider_model_fresh.get((pid, model_id), 0))
            admission_state, can_now, can_after, suppression_reason = _classify_admission(
                structurally_available=True,
                health_record=record,
                provider_wide_failures_in_set=provider_wide_in_set,
                provider_model_failures_in_set=provider_model_in_set,
                now_iso=now_iso,
            )
            candidate_with_admission = {
                **candidate,
                "admission_state": admission_state,
                "can_retry_now": can_now,
                "can_retry_after_cooldown": can_after,
                "suppression_reason": suppression_reason,
                "fresh_transport_failures_in_set": (
                    provider_wide_in_set + provider_model_in_set
                ),
                "provider_wide_failures_in_set": provider_wide_in_set,
                "provider_model_failures_in_set": provider_model_in_set,
            }
            if admission_state == "eligible_now":
                eligible_now_lanes.append(candidate_with_admission)
            else:
                ineligible_lanes.append({
                    "provider_id": pid,
                    "model_id": model_id,
                    "reason": "health_suppressed",
                    "detail": (
                        f"admission_state={admission_state}; "
                        f"suppression_reason={suppression_reason}"
                    ),
                    "admission_state": admission_state,
                })

    capacity_unavailable_after_discovery = (
        len(evidence) > 0 and len(eligible_now_lanes) == 0
    )

    return {
        "kind": "population_lane_provider_capacity_discovery",
        "schema_version": "population_lane_provider_capacity_discovery_v1",
        "lane_id": lane_id,
        "task_class": task_class,
        "now_iso": now_iso,
        "configured_default_lanes": [dict(l) for l in configured_default_lanes],
        "registry_candidate_lanes": registry_candidate_lanes,
        "adapter_available_lanes": adapter_available_lanes,
        "eligible_now_lanes": eligible_now_lanes,
        "ineligible_lanes": ineligible_lanes,
        "eligible_now_lane_count": len(eligible_now_lanes),
        "registry_candidate_count": len(registry_candidate_lanes),
        "ineligible_count": len(ineligible_lanes),
        "transport_only_evidence_row_count": len(evidence),
        "provider_capacity_unavailable_after_discovery": capacity_unavailable_after_discovery,
        "missing_capacity_diagnosis_after_discovery": (
            None
            if not capacity_unavailable_after_discovery
            else (
                "Discovery walked the provider registry and found zero "
                "eligible_now lanes for this task_class. Either restore "
                "an existing provider's health, or add a new active "
                "provider/model to provider_registry.json with the "
                "required task_class allowance and a working adapter "
                "module."
            )
        ),
    }


def build_provider_recovery_plan(
    repo_root: Path | str,
    *,
    lane_id: str,
    configured_lanes: list[Mapping[str, Any]] | None = None,
    transport_only_evidence: list[Mapping[str, Any]] | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    """Build the lane's provider recovery + admission plan.

    Inputs:
    - configured_lanes: registered (provider_id, model_id) pairs the lane
      can dispatch through. Defaults to DEFAULT_CONFIGURED_LANES.
    - transport_only_evidence: rows from the current transport_only set;
      used to count fresh per-provider failures for suppression decisions.
    - now_iso: clock; defaults to wall-clock UTC.

    Returns a packet with one entry per configured (provider, model)
    plus a top-level `actionable_providers` list (admission_state ==
    `eligible_now`) and a `provider_capacity_missing_for_transport_repair`
    bool flag.
    """
    repo_root = Path(repo_root)
    now_iso = now_iso or _now_iso()
    lanes = list(configured_lanes) if configured_lanes is not None else [dict(l) for l in DEFAULT_CONFIGURED_LANES]
    evidence = list(transport_only_evidence or [])

    # Wave 22: scoped aggregation. Provider-wide failures (429, 5xx)
    # apply to every model under that provider; provider:model failures
    # (timeout, worker_error) apply only to the named model. The
    # `_aggregate_scoped_failures` helper walks both winner and
    # alternate attempts and uses TRANSPORT_SUPPRESSION_POLICY to bucket.
    provider_wide_fresh, provider_model_fresh, _row_blocks = _aggregate_scoped_failures(evidence)
    # Per-status by provider for the legacy `observed_statuses` surface.
    fresh_failures_by_provider_status: dict[tuple[str, str], int] = {}
    for r in evidence:
        wp = str(r.get("winner_provider_id") or "")
        ws = str(r.get("winner_status") or "")
        if wp and ws:
            fresh_failures_by_provider_status[(wp, ws)] = (
                fresh_failures_by_provider_status.get((wp, ws), 0) + 1
            )
        for att in (r.get("attempts_seen") or []):
            if not isinstance(att, Mapping):
                continue
            pid = str(att.get("provider_id") or "")
            st = str(att.get("receipt_status") or "")
            if pid and st in TRANSPORT_RECEIPT_KEYS:
                if pid != wp or st != ws:
                    fresh_failures_by_provider_status[(pid, st)] = (
                        fresh_failures_by_provider_status.get((pid, st), 0) + 1
                    )

    # Read provider_health for the lane.
    health_payload: Mapping[str, Any] = {}
    try:
        from system.lib.python_navigation_population_provider_health import load_health, health_for
        health_payload = load_health(repo_root, lane_id)
    except Exception:
        load_health = None  # type: ignore[assignment]
        health_for = None  # type: ignore[assignment]

    # Read compute provider registry for structural availability.
    structurally_active: dict[str, bool] = {}
    registry: Mapping[str, Any] = {}
    try:
        from system.lib import python_navigation_population_compute_policy as compute_policy
        registry = compute_policy.load_provider_registry(str(repo_root))
        for lane in lanes:
            pid = str(lane.get("provider_id") or "")
            if pid:
                structurally_active[pid] = compute_policy.is_provider_active(registry, pid)
    except Exception:
        for lane in lanes:
            pid = str(lane.get("provider_id") or "")
            if pid:
                structurally_active[pid] = True  # conservative default when registry unreadable

    providers_packet: list[dict[str, Any]] = []
    for lane in lanes:
        pid = str(lane.get("provider_id") or "")
        mid = lane.get("model_id")
        if not pid:
            continue
        record: Mapping[str, Any] | None = None
        if health_for is not None:
            try:
                record = health_for(health_payload, provider_id=pid, model_id=mid, now_iso=now_iso)
            except Exception:
                record = None
        provider_wide_in_set = int(provider_wide_fresh.get(pid, 0))
        provider_model_in_set = int(provider_model_fresh.get((pid, str(mid or "")), 0))
        admission_state, can_retry_now, can_retry_after_cooldown, suppression_reason = (
            _classify_admission(
                structurally_available=structurally_active.get(pid, True),
                health_record=record,
                provider_wide_failures_in_set=provider_wide_in_set,
                provider_model_failures_in_set=provider_model_in_set,
                now_iso=now_iso,
            )
        )
        observed_statuses: dict[str, int] = {}
        for (p, st), n in fresh_failures_by_provider_status.items():
            if p == pid:
                observed_statuses[st] = observed_statuses.get(st, 0) + n
        providers_packet.append({
            "provider_id": pid,
            "model_id": str(mid or ""),
            "configured": True,
            "structurally_available": bool(structurally_active.get(pid, True)),
            "health_state": (record or {}).get("health_state") or "eligible",
            "next_attempt_after": (record or {}).get("next_attempt_after"),
            "cooldown_reason": (record or {}).get("cooldown_reason"),
            "consecutive_failures": (record or {}).get("consecutive_failures") or {},
            "consecutive_ok": int((record or {}).get("consecutive_ok") or 0),
            "retry_budget_remaining": int(
                (record or {}).get("retry_budget_remaining") if record and "retry_budget_remaining" in record else 0
            ),
            "observed_statuses_in_transport_only_set": observed_statuses,
            "transport_failures_in_current_transport_only_set": (
                provider_wide_in_set + provider_model_in_set
            ),
            "provider_wide_failures_in_set": provider_wide_in_set,
            "provider_model_failures_in_set": provider_model_in_set,
            "admission_state": admission_state,
            "can_retry_now": can_retry_now,
            "can_retry_after_cooldown": can_retry_after_cooldown,
            "suppression_reason": suppression_reason,
        })

    actionable = [p for p in providers_packet if p["admission_state"] == "eligible_now"]
    capacity_missing = (len(evidence) > 0) and (len(actionable) == 0)

    return {
        "kind": "population_lane_provider_recovery_plan",
        "schema_version": "population_lane_provider_recovery_plan_v1",
        "lane_id": lane_id,
        "now_iso": now_iso,
        "providers": providers_packet,
        "actionable_providers": actionable,
        "actionable_provider_count": len(actionable),
        "configured_provider_count": len(lanes),
        "transport_only_evidence_row_count": len(evidence),
        "provider_capacity_missing_for_transport_repair": capacity_missing,
        "missing_capacity_diagnosis": (
            None
            if not capacity_missing
            else (
                "All configured providers are unhealthy or suppressed; "
                "add a third provider/model lane via --lanes, or wait "
                "for a cooldown to lapse, before invoking "
                "`repair-transport --allow-live`."
            )
        ),
    }
