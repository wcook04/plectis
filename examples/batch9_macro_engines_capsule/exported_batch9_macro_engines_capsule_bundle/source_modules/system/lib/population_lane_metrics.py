"""
[PURPOSE]
- Teleology: Generate live lane telemetry from runs on disk so the
  population_lane_registry.json stays stable. The registry owns lane
  identity and callables; this module owns derived counts, rates,
  applied_count_lifetime, last_success_target, and the
  promotion_recommendation that the daemon and operator digest read.
- Mechanism: Walk
  state/python_navigation_population/runs/<run_id>/{classifications,
  augmented_row_patches,applied_rows,operator_digest}.json and aggregate
  per-lane metrics; emit into state/population/metrics/<lane_id>.json
  atomic-write style.
- Objective: Eliminate the stale-telemetry-in-registry anti-pattern. A
  registry edit is doctrine-grade; a metrics refresh is generated state.

[INTERFACE]
- Inputs: repo_root (Path), lane_id (str).
- Outputs: dict with stable schema; same dict is persisted under
  state/population/metrics/<lane_id>.json on demand.
- Exports: `compute_lane_metrics`, `persist_lane_metrics`,
  `load_lane_metrics`, `recommend_promotion`, `LANE_RUNS_ROOT`.

[FLOW]
1. Discover all run dirs under state/python_navigation_population/runs/.
2. For each run dir, load classifications.json, applied_rows.json (when
   present), and operator_digest.json (when present).
3. Aggregate counts per lane: cohorts seen, rows seen, gate-class counts,
   provider receipt status counts, applied count, rollback count,
   failure-class distribution (via population_skill_evolution).
4. Identify last_success_target from the most recent applied_rows entry.
5. Recommend a promotion stage based on the thresholds named in
   std_population_lane.json (telemetry-only; never operator-confirmed).

[DEPENDENCIES]
- Required: stdlib (json, pathlib, datetime).
- Optional Runtime: system.lib.population_skill_evolution for failure
  classification (best-effort; metrics still compute when unavailable).

[CONSTRAINTS]
1. Read-only over runs and registry; only writes
   state/population/metrics/<lane_id>.json.
2. Deterministic: identical inputs yield byte-identical metrics (modulo
   the generated_at timestamp which the test fixtures normalize).
3. Atomic: persist via tempfile-rename to avoid torn writes.
4. Couples: metric field names mirror std_population_lane.json's
   suggested generated metrics so consumers can swap the registry-stored
   telemetry pattern for this module without surface change.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

LANE_RUNS_ROOT = "state/python_navigation_population/runs"
METRICS_ROOT = "state/population/metrics"

# Wave 18: receipt_status values that mean the winning provider attempt
# never produced a content-quality signal for the row (the provider
# returned a transport error before/instead of the model output).
TRANSPORT_RECEIPT_STATUSES: frozenset[str] = frozenset({
    "429",
    "5xx",
    "timeout",
    "worker_error",
    "blocked_duplicate",
})


def _parse_iso_utc(ts: str | None) -> datetime | None:
    """Wave 18: parse an ISO-8601 timestamp into an aware UTC datetime.
    Accepts both `Z` suffix and `+HH:MM` offsets, with or without
    fractional seconds. Returns None for missing or unparseable input.
    Naive datetimes are interpreted as UTC (legacy compatibility)."""
    if not ts:
        return None
    s = ts.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_post_milestone(event_at: str | None, milestone_at: str | None) -> bool:
    """Wave 18: aware-UTC comparison replacing raw lexicographic timestamp
    comparison. Fixes the live-observed bug where
    `2026-04-29T03:17:20.483991+00:00` failed to compare equal-or-after
    `2026-04-29T03:17:20Z` because `Z` (0x5A) sorts after `.` (0x2E).

    Semantics:
    - milestone_at is None  → all events pass.
    - milestone unparseable → no events pass (be conservative).
    - event_at missing/unparseable AND milestone is set → does NOT pass
      (Wave 18 invariant: missing-time evidence must not silently count
      as post-milestone).
    - both parseable        → e >= m as aware UTC datetimes.
    """
    if not milestone_at:
        return True
    m = _parse_iso_utc(milestone_at)
    if m is None:
        return False
    e = _parse_iso_utc(event_at)
    if e is None:
        return False
    return e >= m


def _winning_attempt_status(paired_row: Mapping[str, Any]) -> str | None:
    """Return the receipt_status of the winner_provider_id's attempt, or
    None if the winner attempt is missing/unknown."""
    winner = str(paired_row.get("winner_provider_id") or "")
    if not winner:
        return None
    for att in (paired_row.get("attempts") or []):
        if isinstance(att, Mapping) and str(att.get("provider_id") or "") == winner:
            s = str(att.get("receipt_status") or "")
            return s or None
    return None


def _winning_attempt_model(paired_row: Mapping[str, Any]) -> str | None:
    """Wave 22: return the model_id of the winner_provider_id's attempt.
    Used by the repair planner to (a) avoid re-selecting the exact
    failed (provider, model) lane, and (b) allow same-provider
    different-model swaps when the registry has alternate models."""
    winner = str(paired_row.get("winner_provider_id") or "")
    if not winner:
        return None
    for att in (paired_row.get("attempts") or []):
        if isinstance(att, Mapping) and str(att.get("provider_id") or "") == winner:
            m = str(att.get("model_id") or "")
            return m or None
    return None


def _row_has_alternate_green(paired_row: Mapping[str, Any]) -> bool:
    """True iff any attempt (even by a non-winner provider) reached
    gate_class=green. Used to distinguish recoverable-via-routing rows
    from pure transport-only rows."""
    for att in (paired_row.get("attempts") or []):
        if isinstance(att, Mapping) and str(att.get("gate_class") or "") == "green":
            return True
    return False


def _resolve_repair_outcome(
    attempts: list[Any] | None,
) -> tuple[str | None, str | None]:
    """Wave 19: collapse a row's `transport_repair_attempts.json` entries
    into a single (effective_gate, receipt_status) verdict.

    Precedence: any green-with-non-transport-status wins; otherwise any
    amber-with-non-transport-status; otherwise any non-transport-status
    attempt; otherwise None (no successful repair, row remains
    transport-only).
    """
    if not isinstance(attempts, list):
        return None, None
    best_gate: str | None = None
    best_status: str | None = None
    for a in attempts:
        if not isinstance(a, Mapping):
            continue
        st = str(a.get("receipt_status") or "")
        if not st or st in TRANSPORT_RECEIPT_STATUSES:
            continue  # a transport-failed retry leaves the row transport-only
        gate = str(a.get("gate_class") or "")
        if gate == "green":
            return "green", st  # green is the strongest verdict
        if gate == "amber" and best_gate is None:
            best_gate, best_status = "amber", st
        elif gate == "red" and best_gate is None:
            best_gate, best_status = "red", st
        elif best_gate is None:
            best_gate, best_status = gate or None, st
    return best_gate, best_status


def _classify_transport_only(
    classifications: Any,
    paired: Any,
    repair_attempts: Any = None,
) -> dict[str, Any]:
    """Wave 18: classify amber/red classification rows as
    `provider_transport_only` when the winning attempt's receipt_status
    is in TRANSPORT_RECEIPT_STATUSES AND no alternate provider attempt
    reached green. These rows MUST be excluded from
    live_quality_eligible_since_last_milestone (they are not a
    model-quality signal) and MUST contribute to the
    provider_transport_unhealthy_since_last_milestone blocker.

    Wave 19: also consult `transport_repair_attempts.json` for the run.
    A row whose repair produced a non-transport receipt becomes a real
    quality result (green/amber/red) and is no longer transport-only;
    `repair_overrides` carries the new effective gate so the calling
    code counts it correctly. A row whose repair was attempted but ALL
    attempts were transport failures stays transport-only and is
    counted under `repeated_transport_failure_count`.
    """
    out: dict[str, Any] = {
        "transport_only_row_ids": [],
        "transport_only_count": 0,
        "transport_only_by_provider": {},
        "transport_only_by_status": {},
        "repair_overrides": {},
        "repaired_to_green_count": 0,
        "repaired_to_amber_count": 0,
        "repaired_to_red_count": 0,
        "repeated_transport_failure_count": 0,
    }
    if not isinstance(classifications, list) or not isinstance(paired, list):
        return out
    # Index paired_comparison rows by row_job_id.
    paired_index: dict[str, Mapping[str, Any]] = {}
    for p in paired:
        if isinstance(p, Mapping):
            rj = str(p.get("row_job_id") or "")
            if rj:
                paired_index[rj] = p
    # Index repair attempts by row_job_id.
    repair_by_row: dict[str, list[Any]] = {}
    if isinstance(repair_attempts, Mapping):
        atts = repair_attempts.get("attempts") or []
    elif isinstance(repair_attempts, list):
        atts = repair_attempts
    else:
        atts = []
    for a in atts:
        if isinstance(a, Mapping):
            rj = str(a.get("row_job_id") or "")
            if rj:
                repair_by_row.setdefault(rj, []).append(a)

    transport_only_ids: list[str] = []
    by_provider: dict[str, int] = {}
    by_status: dict[str, int] = {}
    repair_overrides: dict[str, str] = {}
    repaired_green = 0
    repaired_amber = 0
    repaired_red = 0
    repeated_transport = 0

    for c in classifications:
        if not isinstance(c, Mapping):
            continue
        gate = str(c.get("gate_class") or "")
        if gate not in {"amber", "red"}:
            continue
        rj = str(c.get("row_job_id") or "")
        if not rj or rj not in paired_index:
            continue
        prow = paired_index[rj]
        status = _winning_attempt_status(prow)
        if status is None or status not in TRANSPORT_RECEIPT_STATUSES:
            continue  # winner produced content; this is a real quality amber
        if _row_has_alternate_green(prow):
            continue  # an alternate provider attempt reached green; routing-recoverable

        # Wave 19: did a repair attempt land a non-transport result?
        repair_gate, repair_status = _resolve_repair_outcome(repair_by_row.get(rj))
        if repair_gate == "green":
            repair_overrides[rj] = "green"
            repaired_green += 1
            continue  # not transport-only anymore
        if repair_gate == "amber":
            repair_overrides[rj] = "amber"
            repaired_amber += 1
            continue
        if repair_gate == "red":
            repair_overrides[rj] = "red"
            repaired_red += 1
            continue

        # Row is still transport-only. If a repair was attempted but
        # produced only transport failures, count it as repeated.
        if rj in repair_by_row:
            repeated_transport += 1
        transport_only_ids.append(rj)
        provider = str(prow.get("winner_provider_id") or "unknown")
        by_provider[provider] = by_provider.get(provider, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
    out["transport_only_row_ids"] = transport_only_ids
    out["transport_only_count"] = len(transport_only_ids)
    out["transport_only_by_provider"] = by_provider
    out["transport_only_by_status"] = by_status
    out["repair_overrides"] = repair_overrides
    out["repaired_to_green_count"] = repaired_green
    out["repaired_to_amber_count"] = repaired_amber
    out["repaired_to_red_count"] = repaired_red
    out["repeated_transport_failure_count"] = repeated_transport
    return out


def _runs_for_lane(repo_root: Path, lane_id: str) -> list[Path]:
    runs_dir = repo_root / LANE_RUNS_ROOT
    if not runs_dir.is_dir():
        return []
    return sorted([p for p in runs_dir.iterdir() if p.is_dir()])


def _safe_load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def compute_lane_metrics(
    repo_root: Path | str,
    *,
    lane_id: str,
    milestone_at_override: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Aggregate live telemetry for one registered lane from the
      runs on disk, suitable for emission into the lane's metrics file.
      Promotion_readiness uses ONLY live runs — fake/replay/fixture runs
      cannot promote the lane no matter how green they look.
    - Mechanism: Walk every run dir, read source_mode from operator_digest,
      accumulate gate counts per source_mode, surface live-only views for
      promotion gating.
    - Reads: state/python_navigation_population/runs/<run_id>/*.json.
    - Guarantee: Returns a dict with metrics_v3 schema. counts_by_gate is
      ALL runs; live_counts_by_gate / fake_counts_by_gate / replay_counts_by_gate
      / fixture_counts_by_gate split by source_mode.
    """
    repo_root = Path(repo_root)
    runs = _runs_for_lane(repo_root, lane_id)

    cohort_count = len(runs)
    total_rows = 0
    counts_by_gate = {"green": 0, "amber": 0, "red": 0}
    # Per-source-mode gate counts; promotion uses live only.
    counts_by_mode: dict[str, dict[str, int]] = {
        mode: {"green": 0, "amber": 0, "red": 0}
        for mode in ("live", "fake_provider", "replay", "fixture")
    }
    # Wave 14.1: split live runs by evidence_role so A/B prompt-variant
    # experiments persist for quality-audit but do NOT pollute the
    # promotion-eligible numerator/denominator. Default for runs missing
    # the field (legacy runs) is `promotion` for backward compatibility.
    live_promotion_counts_by_gate = {"green": 0, "amber": 0, "red": 0}
    live_experiment_counts_by_gate = {"green": 0, "amber": 0, "red": 0}
    failure_class_counts_by_mode: dict[str, dict[str, int]] = {
        mode: {} for mode in counts_by_mode
    }
    promotion_eligible_run_count = 0
    receipt_status_counts: dict[str, int] = {}
    applied_count = 0
    rollback_count = 0
    auto_rolled_back_count = 0
    last_run_id: str | None = None
    last_run_counts_by_gate: dict[str, int] | None = None
    last_run_per_lane: dict[str, dict[str, int]] = {}
    last_success_target: str | None = None
    last_success_at: str | None = None
    failure_class_counts: dict[str, int] = {}
    # Wave 16: per-run metadata + per-run failure_class_counts so we can
    # post-filter by (created_at >= milestone) AND (source_mode=live)
    # AND (evidence_role=promotion). Promotion blockers must be
    # milestone-relative; lifetime distribution is archaeology.
    per_run_meta: list[dict[str, Any]] = []

    for run_dir in runs:
        run_id = run_dir.name
        classifications = _safe_load(run_dir / "classifications.json")
        digest = _safe_load(run_dir / "operator_digest.json")
        applied_rows = _safe_load(run_dir / "applied_rows.json")
        augmented = _safe_load(run_dir / "augmented_row_patches.json")

        # Source-mode authority: prefer run_meta.json (Wave 11) over
        # operator_digest (Wave 10 backfill compat). Either source must
        # explicitly set source_mode for the run to count toward live
        # promotion; absence defaults to fixture.
        source_mode = "fixture"
        promotion_eligible = False
        evidence_role = "promotion"  # Wave 14.1 default for legacy runs
        run_meta = _safe_load(run_dir / "run_meta.json")
        if isinstance(run_meta, Mapping):
            source_mode = str(run_meta.get("source_mode") or "fixture")
            promotion_eligible = bool(run_meta.get("promotion_eligible"))
            evidence_role = str(run_meta.get("evidence_role") or "promotion")
        elif isinstance(digest, Mapping):
            source_mode = str(digest.get("source_mode") or "fixture")
            promotion_eligible = bool(digest.get("promotion_eligible"))
            evidence_role = str(digest.get("evidence_role") or "promotion")
        if source_mode not in counts_by_mode:
            source_mode = "fixture"
        if evidence_role not in ("promotion", "experiment"):
            evidence_role = "promotion"
        if promotion_eligible:
            promotion_eligible_run_count += 1

        if classifications:
            total_rows += len(classifications)
            for c in classifications:
                gate = str(c.get("gate_class") or "unknown")
                if gate in counts_by_gate:
                    counts_by_gate[gate] += 1
                if gate in counts_by_mode[source_mode]:
                    counts_by_mode[source_mode][gate] += 1
                # Wave 14.1: split live by evidence_role.
                if source_mode == "live" and gate in live_promotion_counts_by_gate:
                    if evidence_role == "experiment":
                        live_experiment_counts_by_gate[gate] += 1
                    else:
                        live_promotion_counts_by_gate[gate] += 1
            last_run_id = run_id
            run_counts = {"green": 0, "amber": 0, "red": 0}
            for c in classifications:
                gate = str(c.get("gate_class") or "")
                if gate in run_counts:
                    run_counts[gate] += 1
            last_run_counts_by_gate = run_counts
            for c in classifications:
                provider = str(c.get("provider_id") or "unknown")
                gate = str(c.get("gate_class") or "")
                if gate in {"green", "amber", "red"}:
                    bucket = last_run_per_lane.setdefault(provider, {"green": 0, "amber": 0, "red": 0})
                    bucket[gate] += 1

        if isinstance(applied_rows, list):
            for entry in applied_rows:
                if not isinstance(entry, Mapping):
                    continue
                applied_count += 1
                target = str(entry.get("target_path") or "")
                applied_at = str(entry.get("applied_at") or "")
                if target:
                    last_success_target = target
                    last_success_at = applied_at

        commit_packet = _safe_load(run_dir / "apply_green_commit.json")
        if isinstance(commit_packet, Mapping):
            auto_rolled_back_count += int(commit_packet.get("auto_rolled_back_count") or 0)
            # Backfill: historical apply-green commits predating the
            # applied_rows.json ledger still count toward applied_count_lifetime.
            # Only counted when the run dir has NO applied_rows.json — once
            # the ledger exists it is the source of truth and we avoid
            # double-counting.
            if not isinstance(applied_rows, list):
                plan = commit_packet.get("plan") or []
                for entry in plan:
                    if isinstance(entry, Mapping) and entry.get("status") == "applied":
                        applied_count += 1
                        target = str(entry.get("target_path") or "")
                        applied_at = str(commit_packet.get("committed_at") or "")
                        if target:
                            last_success_target = target
                            last_success_at = applied_at

        if digest and isinstance(digest, Mapping):
            top = digest.get("top_failure_classes") or []
            if isinstance(top, list):
                for row in top:
                    if isinstance(row, Mapping):
                        klass = str(row.get("status") or "")
                        if klass:
                            receipt_status_counts[klass] = receipt_status_counts.get(klass, 0) + int(row.get("count") or 0)
            rollback_count += int(digest.get("rollback_count") or 0)

        run_failure_class_counts: dict[str, int] = {}
        try:
            from system.lib import population_skill_evolution as evo
            if classifications:
                # Wave 16: synthesize receipts from paired_comparison's
                # winning attempts so classify_one_failure's transport-
                # status precedence kicks in. Without this, a row whose
                # provider returned 429/worker_error and was strict-typed
                # normalized as `; schema_problems=legacy_provider_shape`
                # gets classified as schema_fail.legacy_provider_shape
                # (quality domain → blocks promotion) when it should be
                # provider.429 / provider.worker_error (provider_transport
                # domain → does not block).
                paired = _safe_load(run_dir / "paired_comparison.json")
                synth_receipts: list[dict[str, Any]] = []
                if isinstance(paired, list):
                    for row in paired:
                        if not isinstance(row, Mapping):
                            continue
                        rj = str(row.get("row_job_id") or "")
                        winning = str(row.get("winner_provider_id") or "")
                        winning_status: str | None = None
                        for att in (row.get("attempts") or []):
                            if not isinstance(att, Mapping):
                                continue
                            if str(att.get("provider_id") or "") == winning:
                                winning_status = str(att.get("receipt_status") or "") or None
                                break
                        if rj and winning_status:
                            synth_receipts.append({
                                "row_job_id": rj,
                                "status": winning_status,
                            })
                run_counts_failures = evo.cluster_failure_classes(
                    classifications, augmented or [], synth_receipts or None,
                )
                for klass, n in run_counts_failures.items():
                    failure_class_counts[klass] = failure_class_counts.get(klass, 0) + n
                    by_mode = failure_class_counts_by_mode.setdefault(source_mode, {})
                    by_mode[klass] = by_mode.get(klass, 0) + n
                    run_failure_class_counts[klass] = run_failure_class_counts.get(klass, 0) + n
        except Exception:
            pass

        # Wave 16: stash per-run metadata for milestone-relative blocker
        # computation. created_at comes from run_meta (Wave 11+) or
        # operator_digest (legacy fallback).
        run_at = ""
        if isinstance(run_meta, Mapping):
            run_at = str(run_meta.get("created_at") or "")
        if not run_at and isinstance(digest, Mapping):
            run_at = str(digest.get("generated_at") or "")
        per_run_meta.append({
            "run_id": run_id,
            "source_mode": source_mode,
            "evidence_role": evidence_role,
            "promotion_eligible": promotion_eligible,
            "created_at": run_at,
            "failure_class_counts": run_failure_class_counts,
        })

    # Failure-domain split: classify each failure into provider_transport
    # (transport noise; tolerated), quality (skill/proof/schema; gates promotion),
    # or substrate (stale fingerprint, projection drift; gates promotion).
    # Compute both the all-runs view and the live-only view.
    failure_domain_counts = {"provider_transport": 0, "quality": 0, "substrate": 0}
    live_failure_domain_counts = {"provider_transport": 0, "quality": 0, "substrate": 0}
    try:
        from system.lib.population_skill_evolution import failure_domain_for_class
        for klass, n in failure_class_counts.items():
            domain = failure_domain_for_class(klass)
            failure_domain_counts[domain] = failure_domain_counts.get(domain, 0) + int(n)
        for klass, n in failure_class_counts_by_mode.get("live", {}).items():
            domain = failure_domain_for_class(klass)
            live_failure_domain_counts[domain] = live_failure_domain_counts.get(domain, 0) + int(n)
    except Exception:
        # If skill_evolution is unavailable, lump everything as quality
        # (conservative — never promote on missing telemetry).
        failure_domain_counts["quality"] = sum(int(n) for n in failure_class_counts.values())
        live_failure_domain_counts["quality"] = sum(int(n) for n in failure_class_counts_by_mode.get("live", {}).values())

    total = max(1, total_rows)
    green_count = counts_by_gate["green"]
    transport_amber = failure_domain_counts.get("provider_transport", 0)
    quality_amber = failure_domain_counts.get("quality", 0)
    substrate_amber = failure_domain_counts.get("substrate", 0)
    # quality_green_rate: of the rows that were quality-eligible (i.e., NOT
    # blocked by transport noise), what fraction reached green? This is the
    # stricter score the operator's promotion contract requires.
    quality_eligible = green_count + quality_amber + substrate_amber
    quality_green_rate = (green_count / quality_eligible) if quality_eligible > 0 else None
    # provider_availability_rate: of all attempts, what fraction were not
    # blocked by transport noise? Transport rate is throughput planning, not
    # skill quality.
    provider_availability_rate = ((total - transport_amber) / total) if total > 0 else None

    # Live-only promotion view. promotion_readiness uses live_* exclusively;
    # synthesized green never promotes the lane.
    live_total = max(1, sum(counts_by_mode["live"].values()))
    live_green_count = counts_by_mode["live"]["green"]
    live_red_count = counts_by_mode["live"]["red"]
    live_quality_amber = live_failure_domain_counts.get("quality", 0)
    live_substrate_amber = live_failure_domain_counts.get("substrate", 0)
    live_quality_eligible = live_green_count + live_quality_amber + live_substrate_amber
    live_quality_green_rate = (
        live_green_count / live_quality_eligible if live_quality_eligible > 0 else None
    )
    live_red_rate = live_red_count / live_total

    # Milestone-relative metrics: we count rollbacks and quality-green
    # eligibility from the latest milestone forward, so historical bug
    # rollbacks (e.g. the triple-quote auto-rollbacks pre-Wave 9) cannot
    # block promotion forever.
    milestone = _resolve_latest_milestone(repo_root, lane_id)
    # Wave 16.1: milestone_at_override lets the milestone-whatif simulator
    # ask "what would the metrics look like if we set the milestone here?"
    # without persisting a registry edit. None → use the persisted milestone.
    effective_milestone_at = (
        milestone_at_override
        if milestone_at_override is not None
        else (milestone.get("entered_at") if milestone else None)
    )
    milestone_metrics = _compute_milestone_relative_metrics(
        runs=runs,
        milestone_at=effective_milestone_at,
    )

    # Wave 16: blocker source must be milestone-relative AND
    # promotion-role-only AND source_mode=live. Lifetime distribution
    # remains preserved as `live_failure_class_distribution` for
    # archaeology; promotion blockers read from the milestone-relative
    # filter so pre-Wave-13 archaeology cannot stall a fixed lane.
    milestone_at_str = effective_milestone_at
    live_promotion_failure_class_distribution_since_last_milestone: dict[str, int] = {}
    archaeological_failure_class_distribution: dict[str, int] = {}
    for entry in per_run_meta:
        if entry["source_mode"] != "live":
            continue
        # Wave 18: aware-UTC datetime comparison; missing-time evidence
        # does NOT silently pass the milestone filter (it falls into the
        # archaeological bucket instead).
        is_post_milestone = _is_post_milestone(
            entry["created_at"], milestone_at_str,
        )
        is_promotion = entry["evidence_role"] == "promotion"
        for klass, n in (entry["failure_class_counts"] or {}).items():
            if is_post_milestone and is_promotion:
                live_promotion_failure_class_distribution_since_last_milestone[klass] = (
                    live_promotion_failure_class_distribution_since_last_milestone.get(klass, 0) + int(n)
                )
            else:
                archaeological_failure_class_distribution[klass] = (
                    archaeological_failure_class_distribution.get(klass, 0) + int(n)
                )

    # Wave 20+22+24: when transport_only > 0, check whether ANY
    # actionable provider/model lane exists. Wave 20 used the recovery
    # plan (DEFAULT_LANES only). Wave 24 upgrades to discovery (full
    # registry walk + model-scoped admission), so the capacity blocker
    # only fires when no eligible_now lane exists ANYWHERE in the
    # registry — not just in the default config. The recovery plan is
    # still computed and surfaced for visibility.
    provider_capacity_missing = False
    provider_recovery_summary: dict[str, Any] = {}
    if int(milestone_metrics["transport_only_count_since_last_milestone"]) > 0:
        try:
            from system.lib.population_lane_provider_recovery import (
                build_provider_recovery_plan,
                build_provider_capacity_discovery,
            )
            evidence_rows = find_lane_transport_only_rows(repo_root, lane_id=lane_id)
            recovery = build_provider_recovery_plan(
                repo_root,
                lane_id=lane_id,
                transport_only_evidence=evidence_rows,
            )
            discovery = build_provider_capacity_discovery(
                repo_root,
                lane_id=lane_id,
                transport_only_evidence=evidence_rows,
            )
            # Capacity is missing only when BOTH default-lane recovery
            # AND registry-wide discovery yield zero actionable lanes.
            recovery_missing = bool(recovery.get("provider_capacity_missing_for_transport_repair"))
            discovery_missing = bool(discovery.get("provider_capacity_unavailable_after_discovery"))
            provider_capacity_missing = recovery_missing and discovery_missing
            provider_recovery_summary = {
                "actionable_provider_count_default_lanes": int(
                    recovery.get("actionable_provider_count") or 0
                ),
                "actionable_provider_count_registry_wide": int(
                    discovery.get("eligible_now_lane_count") or 0
                ),
                "configured_provider_count": int(recovery.get("configured_provider_count") or 0),
                "transport_only_evidence_row_count": int(
                    recovery.get("transport_only_evidence_row_count") or 0
                ),
                "provider_capacity_missing_for_transport_repair": provider_capacity_missing,
                "recovery_missing_default_lanes": recovery_missing,
                "discovery_missing_registry_wide": discovery_missing,
                "admission_states": [
                    {
                        "provider_id": p["provider_id"],
                        "model_id": p["model_id"],
                        "admission_state": p["admission_state"],
                    }
                    for p in (recovery.get("providers") or [])
                ],
            }
        except Exception:
            # If recovery/discovery cannot be computed, default to NOT
            # raising the missing-capacity blocker; the existing
            # transport blocker still gates promotion. Surface the
            # failure for diagnostics.
            provider_recovery_summary = {"error": "recovery_or_discovery_unavailable"}

    promotion_readiness = _promotion_readiness(
        quality_green_rate=live_quality_green_rate,
        red_rate=live_red_rate,
        rollback_count=milestone_metrics["rollback_count_since_last_milestone"],
        applied_count=applied_count,
        # Wave 16: pass the milestone-relative + promotion-role-only
        # distribution. Lifetime distribution is exposed in the metrics
        # output but no longer drives blockers.
        failure_class_counts=live_promotion_failure_class_distribution_since_last_milestone,
        promotion_eligible_run_count=promotion_eligible_run_count,
        live_quality_green_rate_since_last_milestone=milestone_metrics["live_quality_green_rate_since_last_milestone"],
        projection_consumption_verified_count_since_last_milestone=milestone_metrics["projection_consumption_verified_count_since_last_milestone"],
        # Wave 18: provider-health + missing-time blockers.
        transport_only_count_since_last_milestone=milestone_metrics["transport_only_count_since_last_milestone"],
        missing_run_at_count_since_last_milestone=milestone_metrics["missing_run_at_count_since_last_milestone"],
        missing_committed_at_count_since_last_milestone=milestone_metrics["missing_committed_at_count_since_last_milestone"],
        # Wave 20: hard blocker when no actionable provider exists.
        transport_repair_capacity_missing=provider_capacity_missing,
    )

    # Track E (Wave 9): accepted-provider counts, projection-consumption
    # verified count, fallback-used count.
    accepted_provider_counts = _accepted_provider_counts_from_runs(runs)
    projection_consumption_verified = _projection_consumption_verified_count(runs)
    fallback_used = _fallback_used_count(runs)

    return {
        "kind": "population_lane_metrics",
        "schema_version": "population_lane_metrics_v4",
        "lane_id": lane_id,
        "registry_ref": "codex/doctrine/population/population_lane_registry.json",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohort_count": cohort_count,
        "promotion_eligible_run_count": promotion_eligible_run_count,
        "total_rows_seen": total_rows,
        "all_counts_by_gate": counts_by_gate,
        "counts_by_gate": counts_by_gate,  # back-compat alias
        "live_counts_by_gate": counts_by_mode["live"],
        "live_promotion_counts_by_gate": live_promotion_counts_by_gate,
        "live_experiment_counts_by_gate": live_experiment_counts_by_gate,
        "fake_counts_by_gate": counts_by_mode["fake_provider"],
        "replay_counts_by_gate": counts_by_mode["replay"],
        "fixture_counts_by_gate": counts_by_mode["fixture"],
        "live_quality_green_rate": live_quality_green_rate,
        "live_red_rate": live_red_rate,
        "live_failure_domain_counts": live_failure_domain_counts,
        "live_failure_class_distribution": failure_class_counts_by_mode.get("live", {}),
        # Wave 16: milestone-relative + promotion-role-only failure class
        # distribution. This is what promotion_readiness consults for
        # blockers; the lifetime distribution above is preserved for
        # archaeology only.
        "live_promotion_failure_class_distribution_since_last_milestone": (
            live_promotion_failure_class_distribution_since_last_milestone
        ),
        "promotion_blocking_failure_class_distribution": (
            live_promotion_failure_class_distribution_since_last_milestone
        ),
        "archaeological_failure_class_distribution": archaeological_failure_class_distribution,
        "quality_eligible_rows": green_count + quality_amber + substrate_amber,
        "quality_green_count": green_count,
        "transport_failure_count": transport_amber,
        "accepted_provider_counts": accepted_provider_counts,
        "fallback_used_count": fallback_used,
        "projection_consumption_verified_count": projection_consumption_verified,
        "failure_domain_counts": failure_domain_counts,
        "rates": {
            "green_rate": counts_by_gate["green"] / total,
            "amber_rate": counts_by_gate["amber"] / total,
            "red_rate": counts_by_gate["red"] / total,
        },
        "quality_green_rate": quality_green_rate,  # ALL runs (back-compat)
        "provider_availability_rate": provider_availability_rate,
        "receipt_status_counts": receipt_status_counts,
        "applied_count_lifetime": applied_count,
        "rollback_count_lifetime": rollback_count,
        "auto_rolled_back_count_lifetime": auto_rolled_back_count,
        "milestones": _milestones_for_lane(repo_root, lane_id),
        "milestone_metrics": milestone_metrics,
        # Wave 20: provider recovery summary (only populated when
        # transport_only > 0 since that's the only time the blocker
        # logic depends on it).
        "provider_recovery_summary": provider_recovery_summary,
        "last_run_id": last_run_id,
        "last_run_counts_by_gate": last_run_counts_by_gate,
        "last_run_per_lane": last_run_per_lane,
        "last_success_target": last_success_target,
        "last_success_at": last_success_at,
        "failure_class_distribution": failure_class_counts,
        "promotion_readiness": promotion_readiness,
        "promotion_recommendation": recommend_promotion(
            counts_by_gate=counts_by_mode["live"],
            applied_count=applied_count,
            rollback_count=milestone_metrics["rollback_count_since_last_milestone"],
            cohort_count=promotion_eligible_run_count,
            quality_green_rate=live_quality_green_rate,
            failure_class_counts=failure_class_counts_by_mode.get("live", {}),
        ),
    }


def _milestones_for_lane(repo_root: Path, lane_id: str) -> list[Mapping[str, Any]]:
    try:
        registry = json.loads((repo_root / "codex/doctrine/population/population_lane_registry.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    lane = (registry.get("lanes") or {}).get(lane_id) or {}
    milestones = lane.get("milestones") or []
    return [m for m in milestones if isinstance(m, Mapping)]


def _resolve_latest_milestone(repo_root: Path, lane_id: str) -> Mapping[str, Any] | None:
    milestones = _milestones_for_lane(repo_root, lane_id)
    if not milestones:
        return None
    # Sort by entered_at; latest wins.
    return sorted(milestones, key=lambda m: str(m.get("entered_at") or ""))[-1]


def _compute_milestone_relative_metrics(
    *,
    runs: list[Path],
    milestone_at: str | None,
) -> dict[str, Any]:
    """Compute rollback / live-quality-green / projection-consumption metrics
    relative to the latest milestone. If milestone_at is None, lifetime
    counts are used.

    Wave 18 changes from Wave 16.1:
    - Timestamp comparison is aware-UTC datetime via `_is_post_milestone`,
      not raw lexicographic string compare.
    - Missing event-time evidence does NOT silently pass the milestone
      filter; missing-count surfaces are tracked separately.
    - Transport-only amber/red rows (winner had a transport receipt status
      and no alternate green) are excluded from
      live_quality_eligible_since_last_milestone but contribute to a
      separate transport_only_count.
    """
    rollback_since = 0
    auto_rolled_back_since = 0
    live_eligible_since = 0
    live_green_since = 0
    projection_verified_since = 0
    counted_runs = 0
    # Wave 18 surfaces.
    missing_run_at = 0
    missing_committed_at = 0
    transport_only_total = 0
    transport_only_by_provider: dict[str, int] = {}
    transport_only_by_status: dict[str, int] = {}
    # Wave 19 surfaces: repair-aware counters fed by transport_repair_attempts.json.
    repaired_to_green = 0
    repaired_to_amber = 0
    repeated_transport_failure = 0

    for run_dir in runs:
        digest = _safe_load(run_dir / "operator_digest.json")
        run_meta = _safe_load(run_dir / "run_meta.json")
        run_at = ""
        run_mode = "fixture"
        evidence_role = "promotion"  # Wave 14.1 default for legacy runs
        if isinstance(run_meta, Mapping):
            run_mode = str(run_meta.get("source_mode") or "fixture")
            evidence_role = str(run_meta.get("evidence_role") or "promotion")
            run_at = str(run_meta.get("created_at") or "")
        if not run_at and isinstance(digest, Mapping):
            run_at = str(digest.get("generated_at") or "")
            if run_mode == "fixture":
                run_mode = str(digest.get("source_mode") or "fixture")
            if evidence_role == "promotion" and digest.get("evidence_role"):
                evidence_role = str(digest.get("evidence_role") or "promotion")

        # Wave 16.1 / Wave 18: apply/projection/rollback evidence is
        # filtered by commit.committed_at (NOT run_meta.created_at). A
        # post-canary milestone must NOT erase a projection-consumption
        # proof that happened AFTER the milestone, even if the run that
        # produced the canary was created before. Quality-row filtering
        # remains by run_at. Comparison is aware-UTC datetime.
        commit = _safe_load(run_dir / "apply_green_commit.json")
        if isinstance(commit, Mapping):
            committed_at = str(commit.get("committed_at") or "")
            applied_count_in_commit = int(commit.get("applied_count") or 0)
            if milestone_at and not committed_at and applied_count_in_commit > 0:
                missing_committed_at += applied_count_in_commit
            if _is_post_milestone(committed_at, milestone_at):
                rollback_since += int(commit.get("auto_rolled_back_count") or 0)
                auto_rolled_back_since += int(commit.get("auto_rolled_back_count") or 0)
                projection_verified_since += int(
                    commit.get("projection_consumption_verified_count") or 0
                )

        if milestone_at and not run_at:
            missing_run_at += 1
        if not _is_post_milestone(run_at, milestone_at):
            continue
        counted_runs += 1
        # Wave 14.1: only promotion-role live runs feed milestone-relative
        # quality numerators/denominators. Experiments persist (so
        # quality-audit can read them) but never move the promotion needle.
        if run_mode == "live" and evidence_role == "promotion":
            classifications = _safe_load(run_dir / "classifications.json")
            paired = _safe_load(run_dir / "paired_comparison.json")
            # Wave 19: repair attempts are loaded per run; their gate
            # outcomes override transport-only classifications.
            repair_attempts = _safe_load(run_dir / "transport_repair_attempts.json")
            transport_class = _classify_transport_only(
                classifications, paired, repair_attempts,
            )
            transport_only_ids = set(transport_class["transport_only_row_ids"])
            repair_overrides: dict[str, str] = transport_class["repair_overrides"]
            transport_only_total += transport_class["transport_only_count"]
            for k, v in transport_class["transport_only_by_provider"].items():
                transport_only_by_provider[k] = transport_only_by_provider.get(k, 0) + int(v)
            for k, v in transport_class["transport_only_by_status"].items():
                transport_only_by_status[k] = transport_only_by_status.get(k, 0) + int(v)
            repaired_to_green += int(transport_class["repaired_to_green_count"])
            repaired_to_amber += int(transport_class["repaired_to_amber_count"])
            repeated_transport_failure += int(transport_class["repeated_transport_failure_count"])
            if isinstance(classifications, list):
                for c in classifications:
                    if not isinstance(c, Mapping):
                        continue
                    gate = str(c.get("gate_class") or "")
                    rj = str(c.get("row_job_id") or "")
                    # Wave 19: a repair attempt may override a row's
                    # effective gate (e.g. amber → green when a swap
                    # provider succeeds).
                    if rj and rj in repair_overrides:
                        gate = repair_overrides[rj]
                    if gate == "green":
                        live_green_since += 1
                        live_eligible_since += 1
                    elif gate in {"amber", "red"}:
                        # Wave 18: exclude transport-only rows from the
                        # quality denominator. They never produced a
                        # model-quality signal and would otherwise
                        # mask the lane's true blocker as a quality
                        # problem when it is a transport problem.
                        if rj in transport_only_ids:
                            continue
                        live_eligible_since += 1
    live_quality_green_rate_since = (
        live_green_since / live_eligible_since if live_eligible_since > 0 else None
    )
    return {
        "milestone_at": milestone_at,
        "runs_since_last_milestone": counted_runs,
        "rollback_count_since_last_milestone": rollback_since,
        "auto_rolled_back_count_since_last_milestone": auto_rolled_back_since,
        "live_quality_green_rate_since_last_milestone": live_quality_green_rate_since,
        "live_quality_green_count_since_last_milestone": live_green_since,
        "live_quality_eligible_since_last_milestone": live_eligible_since,
        "projection_consumption_verified_count_since_last_milestone": projection_verified_since,
        # Wave 18 surfaces:
        "transport_only_count_since_last_milestone": transport_only_total,
        "transport_only_by_provider_since_last_milestone": transport_only_by_provider,
        "transport_only_by_status_since_last_milestone": transport_only_by_status,
        "missing_run_at_count_since_last_milestone": missing_run_at,
        "missing_committed_at_count_since_last_milestone": missing_committed_at,
        # Wave 19 surfaces: repair-aware counters.
        "repaired_to_green_count_since_last_milestone": repaired_to_green,
        "repaired_to_amber_count_since_last_milestone": repaired_to_amber,
        "repeated_transport_failure_count_since_last_milestone": repeated_transport_failure,
    }


def _accepted_provider_counts_from_runs(runs: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for run_dir in runs:
        classifications = _safe_load(run_dir / "classifications.json")
        if not isinstance(classifications, list):
            continue
        for c in classifications:
            if isinstance(c, Mapping) and c.get("gate_class") == "green":
                pid = str(c.get("provider_id") or "unknown")
                counts[pid] = counts.get(pid, 0) + 1
    return counts


def _projection_consumption_verified_count(runs: list[Path]) -> int:
    total = 0
    for run_dir in runs:
        commit_packet = _safe_load(run_dir / "apply_green_commit.json")
        if isinstance(commit_packet, Mapping):
            total += int(commit_packet.get("projection_consumption_verified_count") or 0)
    return total


def _fallback_used_count(runs: list[Path]) -> int:
    """Count applied row_patches whose Escalates-to consisted only of stable
    doctrine fallback paths (no related-paths or symbol-paths chosen)."""
    try:
        from system.lib.python_navigation_population import STABLE_ESCALATES_TO_FALLBACKS
        fallback_set = set(STABLE_ESCALATES_TO_FALLBACKS)
    except Exception:
        return 0
    count = 0
    for run_dir in runs:
        applied_rows = _safe_load(run_dir / "applied_rows.json")
        augmented = _safe_load(run_dir / "augmented_row_patches.json")
        if not isinstance(applied_rows, list) or not isinstance(augmented, list):
            continue
        applied_ids = {str(e.get("row_job_id") or "") for e in applied_rows if isinstance(e, Mapping)}
        for entry in augmented:
            if not isinstance(entry, Mapping):
                continue
            if str(entry.get("row_job_id") or "") not in applied_ids:
                continue
            rp = entry.get("augmented_row_patch") or {}
            proposed = rp.get("proposed_value") if isinstance(rp, Mapping) else None
            if not isinstance(proposed, Mapping):
                continue
            escalates = list(proposed.get("escalates_to") or [])
            if escalates and all(t in fallback_set for t in escalates):
                count += 1
    return count


def _promotion_readiness(
    *,
    quality_green_rate: float | None,
    red_rate: float,
    rollback_count: int,
    applied_count: int,
    failure_class_counts: Mapping[str, int],
    promotion_eligible_run_count: int = 0,
    live_quality_green_rate_since_last_milestone: float | None = None,
    projection_consumption_verified_count_since_last_milestone: int = 0,
    transport_only_count_since_last_milestone: int = 0,
    missing_run_at_count_since_last_milestone: int = 0,
    missing_committed_at_count_since_last_milestone: int = 0,
    transport_repair_capacity_missing: bool = False,
) -> dict[str, Any]:
    """Wave 10 doctrine: promotion uses live + milestone-relative metrics
    only. Synthetic green never promotes the lane. Historical rollbacks
    are archaeological — only those since the latest milestone gate
    promotion.

    Wave 18 additions:
    - `transport_only_count_since_last_milestone` adds an explicit
      provider-health blocker. cohort_apply CANNOT become true while
      provider transport is unhealthy, even if the (Wave-18-corrected)
      quality rate hits 1.0 because transport-only rows were excluded.
    - `missing_run_at` / `missing_committed_at` counts surface untimed
      evidence as blockers rather than letting it silently pass.
    """
    blocking: list[str] = []
    if promotion_eligible_run_count == 0:
        blocking.append("no_live_runs_observed_since_last_milestone")
    if live_quality_green_rate_since_last_milestone is None:
        blocking.append("no_live_quality_eligible_rows_since_last_milestone")
    elif live_quality_green_rate_since_last_milestone < 1.0:
        blocking.append(
            f"live_quality_green_rate_since_last_milestone_below_1.0_({live_quality_green_rate_since_last_milestone:.3f})"
        )
    if red_rate > 0:
        blocking.append(f"live_red_rate_above_zero_({red_rate:.3f})")
    if rollback_count > 0:
        blocking.append(f"rollback_count_since_last_milestone_above_zero_({rollback_count})")
    if projection_consumption_verified_count_since_last_milestone == 0:
        blocking.append("projection_consumption_verified_count_since_last_milestone_is_zero")
    # Wave 18: provider-health blocker. Transport-only rows are excluded
    # from the quality denominator so they cannot mask as a quality
    # problem; instead they raise this dedicated blocker. The lane is
    # explicit that it is blocked by transport, not model quality.
    if transport_only_count_since_last_milestone > 0:
        blocking.append(
            f"provider_transport_unhealthy_since_last_milestone_({transport_only_count_since_last_milestone})"
        )
    # Wave 20: hard blocker when transport repair has no actionable
    # provider lane (all configured lanes unhealthy / suppressed /
    # structurally unavailable). cohort_apply MUST stay false until
    # provider capacity is restored.
    if transport_repair_capacity_missing and transport_only_count_since_last_milestone > 0:
        blocking.append("provider_capacity_missing_for_transport_repair")
    # Wave 18: missing-time evidence becomes an explicit blocker rather
    # than silently counting as post-milestone. The operator should fix
    # the missing timestamp or re-run the artifact.
    if missing_run_at_count_since_last_milestone > 0:
        blocking.append(
            f"missing_run_at_count_since_last_milestone_({missing_run_at_count_since_last_milestone})"
        )
    if missing_committed_at_count_since_last_milestone > 0:
        blocking.append(
            f"missing_committed_at_count_since_last_milestone_({missing_committed_at_count_since_last_milestone})"
        )
    # Any LIVE quality/substrate failure class with non-zero count blocks promotion.
    try:
        from system.lib.population_skill_evolution import failure_domain_for_class
        for klass, n in failure_class_counts.items():
            if int(n) > 0 and failure_domain_for_class(klass) in {"quality", "substrate"}:
                blocking.append(f"unresolved_live_{klass}_({int(n)})")
    except Exception:
        pass
    return {
        "cohort_apply": not blocking and applied_count >= 3,
        "blocking_reasons": blocking,
        "applied_count_lifetime": applied_count,
        "promotion_eligible_run_count": promotion_eligible_run_count,
        "rollback_count_since_last_milestone": rollback_count,
        "live_quality_green_rate_since_last_milestone": live_quality_green_rate_since_last_milestone,
        "projection_consumption_verified_count_since_last_milestone": projection_consumption_verified_count_since_last_milestone,
        "transport_only_count_since_last_milestone": transport_only_count_since_last_milestone,
        "missing_run_at_count_since_last_milestone": missing_run_at_count_since_last_milestone,
        "missing_committed_at_count_since_last_milestone": missing_committed_at_count_since_last_milestone,
    }


def simulate_milestone(
    repo_root: Path | str,
    *,
    lane_id: str,
    candidate_milestone_at: str,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    """Wave 16.1: read-only what-if simulator. Compute metrics as if
    `candidate_milestone_at` were the latest milestone. Returns a
    diagnostic packet showing whether the canary apply proof would
    survive, whether the live-quality numerator/denominator change,
    and whether cohort_apply would flip.

    Pure read-only. Does NOT persist any milestone or registry edit.
    """
    repo_root = Path(repo_root)
    m = compute_lane_metrics(
        repo_root,
        lane_id=lane_id,
        milestone_at_override=candidate_milestone_at,
    )
    mm = m["milestone_metrics"]
    pr = m["promotion_readiness"]

    # Per-run survival diagnostic: which runs / apply commits would
    # cross the candidate milestone?
    runs = _runs_for_lane(repo_root, lane_id)
    runs_post_milestone: list[str] = []
    apply_commits_post_milestone: list[dict[str, Any]] = []
    for run_dir in runs:
        run_meta = _safe_load(run_dir / "run_meta.json")
        digest = _safe_load(run_dir / "operator_digest.json")
        run_at = ""
        if isinstance(run_meta, Mapping):
            run_at = str(run_meta.get("created_at") or "")
        if not run_at and isinstance(digest, Mapping):
            run_at = str(digest.get("generated_at") or "")
        # Wave 18: aware-UTC datetime comparison; missing-time evidence
        # does NOT silently pass.
        if _is_post_milestone(run_at, candidate_milestone_at):
            runs_post_milestone.append(run_dir.name)
        commit = _safe_load(run_dir / "apply_green_commit.json")
        if isinstance(commit, Mapping):
            committed_at = str(commit.get("committed_at") or "")
            if _is_post_milestone(committed_at, candidate_milestone_at):
                apply_commits_post_milestone.append({
                    "run_id": run_dir.name,
                    "committed_at": committed_at,
                    "applied_count": int(commit.get("applied_count") or 0),
                    "auto_rolled_back_count": int(commit.get("auto_rolled_back_count") or 0),
                    "projection_consumption_verified_count": int(
                        commit.get("projection_consumption_verified_count") or 0
                    ),
                })

    return {
        "kind": "population_lane_milestone_whatif",
        "schema_version": "population_lane_milestone_whatif_v1",
        "lane_id": lane_id,
        "candidate_milestone_id": candidate_id,
        "candidate_milestone_at": candidate_milestone_at,
        "runs_counted_since_milestone": mm["runs_since_last_milestone"],
        "apply_commits_counted_since_milestone": len(apply_commits_post_milestone),
        "projection_consumption_verified_count_since_last_milestone": (
            mm["projection_consumption_verified_count_since_last_milestone"]
        ),
        "live_quality_green_count_since_last_milestone": (
            mm["live_quality_green_count_since_last_milestone"]
        ),
        "live_quality_eligible_since_last_milestone": (
            mm["live_quality_eligible_since_last_milestone"]
        ),
        "live_quality_green_rate_since_last_milestone": (
            mm["live_quality_green_rate_since_last_milestone"]
        ),
        "rollback_count_since_last_milestone": mm["rollback_count_since_last_milestone"],
        "promotion_blocking_failure_class_distribution": (
            m.get("promotion_blocking_failure_class_distribution") or {}
        ),
        "promotion_readiness_blocking_reasons": pr.get("blocking_reasons", []),
        "cohort_apply": pr.get("cohort_apply", False),
        "runs_post_milestone": runs_post_milestone,
        "apply_commits_post_milestone": apply_commits_post_milestone,
        "diagnostics": _whatif_diagnostics(
            runs_post_milestone=runs_post_milestone,
            apply_commits_post_milestone=apply_commits_post_milestone,
            milestone_metrics=mm,
            promotion_readiness=pr,
        ),
    }


def _whatif_diagnostics(
    *,
    runs_post_milestone: list[str],
    apply_commits_post_milestone: list[dict[str, Any]],
    milestone_metrics: Mapping[str, Any],
    promotion_readiness: Mapping[str, Any],
) -> dict[str, Any]:
    """Produce the explicit yes/no diagnostics the operator asked for:
    - canary apply proof preserved or lost
    - canary utility_green proof preserved or lost
    - failure archaeology still excluded from blockers
    - cohort_apply outcome (true / false / undefined)
    """
    canary_run_id = "race_20260429T031720Z_891b263084"
    canary_committed_at = "2026-04-29T06:36:39.808923+00:00"
    apply_proof_preserved = any(
        c["run_id"] == canary_run_id
        and c.get("projection_consumption_verified_count", 0) >= 1
        for c in apply_commits_post_milestone
    )
    canary_run_classification_preserved = canary_run_id in runs_post_milestone
    cohort_outcome: str
    cohort_apply = bool(promotion_readiness.get("cohort_apply"))
    has_quality = milestone_metrics.get("live_quality_green_rate_since_last_milestone") is not None
    if cohort_apply:
        cohort_outcome = "true"
    elif not has_quality:
        cohort_outcome = "undefined_no_live_quality_evidence"
    else:
        cohort_outcome = "false"
    return {
        "canary_apply_projection_proof_preserved": apply_proof_preserved,
        "canary_run_quality_classifications_preserved": canary_run_classification_preserved,
        "cohort_apply_outcome": cohort_outcome,
        "would_be_metrics_fraud": (
            cohort_apply and not has_quality
        ),
        "summary": (
            "apply_proof_preserved="
            + ("yes" if apply_proof_preserved else "NO_LOST")
            + "; canary_run_classifications_preserved="
            + ("yes" if canary_run_classification_preserved else "NO_LOST")
            + f"; cohort_apply={cohort_outcome}"
        ),
    }


def find_lane_transport_only_rows(
    repo_root: Path | str,
    *,
    lane_id: str,
    milestone_at_override: str | None = None,
) -> list[dict[str, Any]]:
    """Wave 19: enumerate the lane's CURRENT transport-only rows. A row
    qualifies when (a) it appears in a post-milestone live promotion-role
    run's classifications.json with gate=amber/red, (b) its winning
    paired_comparison attempt has receipt_status in
    TRANSPORT_RECEIPT_STATUSES, (c) no alternate-provider attempt is
    green, AND (d) no successful repair attempt in
    transport_repair_attempts.json has converted it to a quality result.

    Returns one entry per remaining transport-only row, with enough
    metadata for repair-transport to build a retry plan without rerunning
    the whole cohort.
    """
    repo_root = Path(repo_root)
    runs = _runs_for_lane(repo_root, lane_id)
    milestone = _resolve_latest_milestone(repo_root, lane_id)
    effective_milestone_at = (
        milestone_at_override
        if milestone_at_override is not None
        else (milestone.get("entered_at") if milestone else None)
    )
    out: list[dict[str, Any]] = []
    for run_dir in runs:
        run_meta = _safe_load(run_dir / "run_meta.json")
        digest = _safe_load(run_dir / "operator_digest.json")
        run_at = ""
        run_mode = "fixture"
        evidence_role = "promotion"
        if isinstance(run_meta, Mapping):
            run_mode = str(run_meta.get("source_mode") or "fixture")
            evidence_role = str(run_meta.get("evidence_role") or "promotion")
            run_at = str(run_meta.get("created_at") or "")
        if not run_at and isinstance(digest, Mapping):
            run_at = str(digest.get("generated_at") or "")
            if run_mode == "fixture":
                run_mode = str(digest.get("source_mode") or "fixture")
        if run_mode != "live" or evidence_role != "promotion":
            continue
        if not _is_post_milestone(run_at, effective_milestone_at):
            continue
        classifications = _safe_load(run_dir / "classifications.json")
        paired = _safe_load(run_dir / "paired_comparison.json")
        repair_attempts = _safe_load(run_dir / "transport_repair_attempts.json")
        transport_class = _classify_transport_only(classifications, paired, repair_attempts)
        if not transport_class["transport_only_row_ids"]:
            continue
        # Index paired and classifications for per-row enrichment.
        paired_index: dict[str, Mapping[str, Any]] = {}
        if isinstance(paired, list):
            for p in paired:
                if isinstance(p, Mapping):
                    rj = str(p.get("row_job_id") or "")
                    if rj:
                        paired_index[rj] = p
        cls_index: dict[str, Mapping[str, Any]] = {}
        if isinstance(classifications, list):
            for c in classifications:
                if isinstance(c, Mapping):
                    rj = str(c.get("row_job_id") or "")
                    if rj:
                        cls_index[rj] = c
        # Selected packet maps row_job_id → original row_job (needed for retry).
        selected = _safe_load(run_dir / "selected_packet.json")
        rj_packet_index: dict[str, Mapping[str, Any]] = {}
        if isinstance(selected, Mapping):
            for rj_pkt in (selected.get("row_jobs") or []):
                if isinstance(rj_pkt, Mapping):
                    jid = str(rj_pkt.get("job_id") or "")
                    if jid:
                        rj_packet_index[jid] = rj_pkt
        prior_repair_by_row: dict[str, list[Any]] = {}
        if isinstance(repair_attempts, Mapping):
            for a in (repair_attempts.get("attempts") or []):
                if isinstance(a, Mapping):
                    rj = str(a.get("row_job_id") or "")
                    if rj:
                        prior_repair_by_row.setdefault(rj, []).append(a)
        for rj in transport_class["transport_only_row_ids"]:
            prow = paired_index.get(rj) or {}
            crow = cls_index.get(rj) or {}
            target_path = ""
            target_row_id = str(crow.get("target_row_id") or "")
            if target_row_id and ":" in target_row_id:
                # python_navigation_population:<path>::<symbol>
                _, _, rest = target_row_id.partition(":")
                if "::" in rest:
                    target_path = rest.split("::", 1)[0]
                else:
                    target_path = rest
            attempts_seen: list[dict[str, Any]] = []
            for att in (prow.get("attempts") or []):
                if isinstance(att, Mapping):
                    attempts_seen.append({
                        "provider_id": str(att.get("provider_id") or ""),
                        "model_id": str(att.get("model_id") or ""),
                        "gate_class": str(att.get("gate_class") or ""),
                        "receipt_status": str(att.get("receipt_status") or ""),
                    })
            # Wave 24: merge prior repair-attempt failures into the
            # attempts_seen evidence so the NEXT discovery walk's
            # scoped-failure aggregator sees them and suppresses the
            # exact (provider, model) lane that just failed. Without
            # this, the scheduler would keep selecting the swap model
            # that timed out moments ago.
            for prior in prior_repair_by_row.get(rj, []):
                if not isinstance(prior, Mapping):
                    continue
                pst = str(prior.get("receipt_status") or "")
                if pst in {"429", "5xx", "timeout", "worker_error", "blocked_duplicate"}:
                    attempts_seen.append({
                        "provider_id": str(prior.get("swap_provider_id") or ""),
                        "model_id": str(prior.get("swap_model_id") or ""),
                        "gate_class": str(prior.get("gate_class") or ""),
                        "receipt_status": pst,
                        "from_prior_repair_attempt": True,
                    })
            out.append({
                "run_id": run_dir.name,
                "row_job_id": rj,
                "target_row_id": target_row_id,
                "target_path": target_path,
                "winner_provider_id": str(prow.get("winner_provider_id") or ""),
                "winner_model_id": _winning_attempt_model(prow) or "",  # Wave 22
                "winner_status": _winning_attempt_status(prow) or "",
                "attempts_seen": attempts_seen,
                "prior_repair_attempt_count": len(prior_repair_by_row.get(rj, [])),
                "row_job_packet_present": rj in rj_packet_index,
            })
    return out


def build_repair_plan(
    repo_root: Path | str,
    *,
    lane_id: str,
    transport_rows: list[dict[str, Any]] | None = None,
    available_providers: list[Mapping[str, Any]] | None = None,
    suppress_threshold: int = 1,
) -> dict[str, Any]:
    """Wave 19/22: build a dry-run repair plan from the lane's current
    transport-only rows.

    Wave 22 changes from Wave 19:
    - Suppression is scoped via `transport_suppression_scope`: 429/5xx
      suppress provider-wide; timeout/worker_error suppress only
      (provider, model); blocked_duplicate does NOT suppress capacity.
    - Fallback selection allows same-provider different-model swaps
      when only a model-scoped failure exists.
    - The exact failed (provider, model) lane is NEVER reselected,
      even when no other lane is available — the row is left
      unactionable in that case.
    """
    if transport_rows is None:
        transport_rows = find_lane_transport_only_rows(repo_root, lane_id=lane_id)

    # Wave 22: scoped failure aggregation (delegate to recovery module).
    try:
        from system.lib.population_lane_provider_recovery import (
            _aggregate_scoped_failures, transport_suppression_scope,
        )
    except Exception:
        _aggregate_scoped_failures = None  # type: ignore[assignment]
        transport_suppression_scope = None  # type: ignore[assignment]

    if _aggregate_scoped_failures is not None:
        provider_wide_fresh, provider_model_fresh, _row_blocks = _aggregate_scoped_failures(
            transport_rows
        )
    else:  # pragma: no cover — defensive fallback
        provider_wide_fresh = {}
        provider_model_fresh = {}

    suppressed: list[dict[str, Any]] = []
    for pid, n in provider_wide_fresh.items():
        suppressed.append({
            "scope": "provider",
            "provider_id": pid,
            "model_id": None,
            "suppression_reason": "provider_wide_transport_failure_in_current_transport_only_set",
            "count": n,
        })
    for (pid, mid), n in provider_model_fresh.items():
        suppressed.append({
            "scope": "provider_model",
            "provider_id": pid,
            "model_id": mid,
            "suppression_reason": "provider_model_transport_failure_in_current_transport_only_set",
            "count": n,
        })
    suppressed_provider_ids = {
        s["provider_id"] for s in suppressed if s["scope"] == "provider"
    }
    suppressed_provider_models = {
        (s["provider_id"], s["model_id"]) for s in suppressed if s["scope"] == "provider_model"
    }

    if available_providers is None:
        available_providers = []
    fallback_candidates: list[dict[str, Any]] = []
    for lane in available_providers:
        pid = str(lane.get("provider_id") or "")
        mid = str(lane.get("model_id") or "")
        if not pid:
            continue
        # Wave 22: skip if provider is provider-wide suppressed OR if
        # this exact (provider, model) is suppressed.
        if pid in suppressed_provider_ids:
            continue
        if (pid, mid) in suppressed_provider_models:
            continue
        fallback_candidates.append({"provider_id": pid, "model_id": mid})

    rows_to_retry: list[dict[str, Any]] = []
    for r in transport_rows:
        wp = str(r.get("winner_provider_id") or "")
        wm = str(r.get("winner_model_id") or "")
        # Wave 22: a fallback is acceptable if it is a DIFFERENT
        # (provider, model) than the original winner. Same-provider
        # different-model is now allowed; same-(provider, model) is
        # NEVER selected.
        chosen_swap: dict[str, Any] | None = None
        for fb in fallback_candidates:
            if fb["provider_id"] == wp and (fb.get("model_id") or "") == wm:
                continue  # never reselect the exact failed lane
            chosen_swap = fb
            break
        rows_to_retry.append({
            "run_id": r["run_id"],
            "row_job_id": r["row_job_id"],
            "target_path": r["target_path"],
            "original_winner_provider_id": wp,
            "original_winner_model_id": wm,
            "original_winner_status": r["winner_status"],
            "swap_provider_id": (chosen_swap or {}).get("provider_id"),
            "swap_model_id": (chosen_swap or {}).get("model_id"),
            "swap_is_same_provider_different_model": bool(
                chosen_swap
                and chosen_swap.get("provider_id") == wp
                and (chosen_swap.get("model_id") or "") != wm
            ),
            "row_job_packet_present": bool(r.get("row_job_packet_present")),
            "prior_repair_attempt_count": int(r.get("prior_repair_attempt_count", 0)),
            "skip_reason": (
                None
                if chosen_swap and r.get("row_job_packet_present")
                else (
                    "no_unsuppressed_alternate_provider_or_model"
                    if not chosen_swap
                    else "row_job_packet_missing_in_selected_packet"
                )
            ),
        })

    actionable = [r for r in rows_to_retry if r["skip_reason"] is None]
    expected_effect = {
        "max_transport_only_clearance_if_all_retries_succeed_with_ok": len(actionable),
        "rows_planned_for_retry": len(actionable),
        "rows_skipped_with_reason": len(rows_to_retry) - len(actionable),
        "transport_only_count_unchanged_if_all_retries_fail_transport_again": len(transport_rows),
    }
    return {
        "kind": "population_lane_transport_repair_plan",
        "schema_version": "population_lane_transport_repair_plan_v1",
        "lane_id": lane_id,
        "transport_only_rows_in_scope": transport_rows,
        "rows_to_retry": rows_to_retry,
        "providers_suppressed": suppressed,
        "fallback_candidates": fallback_candidates,
        "expected_effect_on_transport_only_count": expected_effect,
    }


def classify_blockers_and_next_action(
    metrics: Mapping[str, Any],
) -> dict[str, Any]:
    """Wave 18: collapse promotion_readiness.blocking_reasons into a
    typed breakdown (transport / quality / timestamp / projection /
    rollback / other) and emit ONE next runnable action — not a recap.

    Decision precedence (highest first):
      1. timestamp blockers     → repair missing-time evidence
      2. transport blockers     → provider routing/capacity repair
      3. rollback blockers      → triage rollbacks since milestone
      4. projection blockers    → run a utility-gated canary apply
      5. quality blockers       → add promotion-role live evidence
      6. cohort_apply unlocked  → run read-only promotion audit first
      7. otherwise              → hold at current stage

    The point is for the lane to say "I am blocked by X; here's the exact
    next runnable command" so each wave doesn't require an external
    synthesis pass.
    """
    pr = metrics.get("promotion_readiness") or {}
    mm = metrics.get("milestone_metrics") or {}
    blockers = list(pr.get("blocking_reasons") or [])
    by_class: dict[str, list[str]] = {
        "transport": [],
        "quality": [],
        "timestamp": [],
        "projection": [],
        "rollback": [],
        "provider_capacity": [],  # Wave 20
        "other": [],
    }
    for b in blockers:
        if "provider_capacity_missing_for_transport_repair" in b:
            # Wave 20: a separate, harder bucket so the next-action
            # branch can route to provider-recovery-plan rather than
            # to repair-transport (which would be a self-loop here).
            by_class.setdefault("provider_capacity", []).append(b)
        elif "provider_transport_unhealthy" in b:
            by_class["transport"].append(b)
        elif "missing_run_at" in b or "missing_committed_at" in b:
            by_class["timestamp"].append(b)
        elif (
            "live_quality_green_rate" in b
            or "live_red_rate" in b
            or "no_live_quality_eligible" in b
            or "no_live_runs_observed" in b
            or "unresolved_live_" in b
        ):
            by_class["quality"].append(b)
        elif "projection_consumption_verified" in b:
            by_class["projection"].append(b)
        elif "rollback_count" in b:
            by_class["rollback"].append(b)
        else:
            by_class["other"].append(b)

    if by_class["timestamp"]:
        next_action = {
            "decision": "hold_pending_timestamp_repair",
            "reason": (
                "Missing event-time evidence cannot silently count as "
                "post-milestone. Backfill the timestamps or re-run the "
                "missing artifacts."
            ),
            "command": (
                "./repo-python tools/meta/control/python_navigation_population_lane.py "
                "stabilize --diagnose-timestamps"
            ),
        }
    elif by_class["provider_capacity"]:
        # Wave 20+21: provider pool has zero actionable lanes — repair-
        # transport would self-loop. Wave 21 routes to capacity
        # DISCOVERY (which walks the provider registry) rather than
        # the older recovery-plan (which only inspects current
        # configured lanes). Discovery is the surface that can find
        # NEW safe capacity instead of merely explaining the absence.
        next_action = {
            "decision": "provider_capacity_missing_for_transport_repair",
            "reason": (
                "All configured providers are unhealthy or suppressed; "
                "no actionable provider lane exists for transport repair. "
                "Run provider-capacity-discovery to walk the provider "
                "registry for new safe candidates."
            ),
            "command": (
                "./repo-python tools/meta/control/python_navigation_population_lane.py "
                "provider-capacity-discovery"
            ),
        }
    elif by_class["transport"]:
        # Wave 24: stabilize at the metrics-library layer keeps the
        # repair-transport pointer for transport blockers. The CLI
        # layer (cmd_stabilize) UPGRADES this to `metabolize --dry-run`
        # when the scheduler reports actionable metabolic capacity,
        # since the scheduler can rotate across NVIDIA siblings rather
        # than repeatedly retrying the same swap model.
        next_action = {
            "decision": "provider_repair_required",
            "reason": (
                "The lane is blocked by provider transport health, not "
                "model quality. Run the targeted transport-only repair "
                "plan; do NOT rerun the whole cohort."
            ),
            "command": (
                "./repo-python tools/meta/control/python_navigation_population_lane.py "
                "repair-transport --dry-run"
            ),
        }
    elif by_class["rollback"]:
        next_action = {
            "decision": "rollback_required_repair",
            "reason": (
                "Rollbacks since milestone must be triaged before any "
                "further apply."
            ),
            "command": (
                "./repo-python tools/meta/control/python_navigation_population_lane.py "
                "stabilize --diagnose-rollbacks"
            ),
        }
    elif by_class["projection"]:
        next_action = {
            "decision": "canary_apply_required",
            "reason": (
                "No projection-consumption proof since milestone. Run "
                "an apply-green canary on a utility_green target."
            ),
            "command": (
                "./repo-python tools/meta/control/python_navigation_population_lane.py "
                "apply-green --max-count 1"
            ),
        }
    elif by_class["quality"]:
        next_action = {
            "decision": "promotion_role_live_evidence",
            "reason": (
                "Quality denominator is short; transport is healthy. "
                "Add more promotion-role live evidence."
            ),
            "command": (
                "./repo-python tools/meta/control/python_navigation_population_lane.py "
                "race --evidence-role promotion --prompt-variant no_examples"
            ),
        }
    elif pr.get("cohort_apply"):
        next_action = {
            "decision": "cohort_apply_unlocked_run_audit_first",
            "reason": (
                "All gates are clean. Before cohort promotion, run the "
                "read-only promotion audit and confirm what-if matrix."
            ),
            "command": (
                "./repo-python tools/meta/control/python_navigation_population_lane.py "
                "milestone-whatif --candidate current=now"
            ),
        }
    else:
        next_action = {
            "decision": "hold_at_current_stage",
            "reason": "No actionable blockers; lane is in steady state.",
            "command": "(no action)",
        }

    return {
        "blockers_by_class": by_class,
        "transport_diagnostics": {
            "transport_only_count_since_last_milestone": int(
                mm.get("transport_only_count_since_last_milestone", 0) or 0
            ),
            "transport_only_by_provider_since_last_milestone": dict(
                mm.get("transport_only_by_provider_since_last_milestone") or {}
            ),
            "transport_only_by_status_since_last_milestone": dict(
                mm.get("transport_only_by_status_since_last_milestone") or {}
            ),
        },
        "timestamp_diagnostics": {
            "missing_run_at_count_since_last_milestone": int(
                mm.get("missing_run_at_count_since_last_milestone", 0) or 0
            ),
            "missing_committed_at_count_since_last_milestone": int(
                mm.get("missing_committed_at_count_since_last_milestone", 0) or 0
            ),
        },
        "next_action": next_action,
    }


def recommend_promotion(
    *,
    counts_by_gate: Mapping[str, int],
    applied_count: int,
    rollback_count: int,
    cohort_count: int,
    quality_green_rate: float | None = None,
    failure_class_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Pure-deterministic promotion recommender per the Wave 8 doctrine.

    Promotion to cohort_apply REQUIRES quality_green_rate == 1.0 — provider
    transport failures are tolerated and do not gate skill promotion, but
    every quality-eligible row must reach green. Loose green-rate
    thresholds (e.g. >= 0.20) only support canary_apply, not cohort_apply.
    """
    total = max(1, sum(counts_by_gate.values()))
    green_rate = counts_by_gate.get("green", 0) / total
    red_rate = counts_by_gate.get("red", 0) / total

    quality_failures_present = False
    if failure_class_counts:
        try:
            from system.lib.population_skill_evolution import failure_domain_for_class
            for klass, n in failure_class_counts.items():
                if int(n) > 0 and failure_domain_for_class(klass) in {"quality", "substrate"}:
                    quality_failures_present = True
                    break
        except Exception:
            quality_failures_present = True

    cohort_apply_eligible = (
        applied_count >= 3
        and rollback_count == 0
        and red_rate == 0.0
        and quality_green_rate == 1.0
        and not quality_failures_present
    )
    if cohort_apply_eligible:
        return {
            "recommended_stage": "cohort_apply",
            "rationale": "quality_green_rate == 1.0 AND red_rate == 0 AND rollback_count == 0 AND applied_count >= 3 AND no quality/substrate failures",
            "evidence": {
                "applied_count": applied_count,
                "rollback_count": rollback_count,
                "quality_green_rate": quality_green_rate,
                "red_rate": red_rate,
            },
        }
    if green_rate >= 0.20 and red_rate == 0.0:
        return {
            "recommended_stage": "canary_apply",
            "rationale": "live_green_rate >= 0.20 AND red_rate == 0.0 (cohort_apply blocked on quality)",
            "evidence": {
                "green_rate": green_rate,
                "quality_green_rate": quality_green_rate,
                "red_rate": red_rate,
                "quality_failures_present": quality_failures_present,
            },
        }
    if cohort_count >= 1:
        return {
            "recommended_stage": "live_shadow",
            "rationale": "at least one live cohort observed; awaiting green threshold",
            "evidence": {"cohort_count": cohort_count, "green_rate": green_rate},
        }
    return {
        "recommended_stage": "fixture_only",
        "rationale": "no cohort runs observed yet",
        "evidence": {},
    }


def persist_lane_metrics(repo_root: Path | str, *, lane_id: str) -> dict[str, Any]:
    """Compute then atomic-write metrics to state/population/metrics/<lane_id>.json."""
    repo_root = Path(repo_root)
    metrics = compute_lane_metrics(repo_root, lane_id=lane_id)
    out_dir = repo_root / METRICS_ROOT
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{lane_id}.json"
    with tempfile.NamedTemporaryFile("w", dir=out_dir, delete=False, encoding="utf-8") as tmp:
        json.dump(metrics, tmp, indent=2, sort_keys=True)
        tmp_name = tmp.name
    os.replace(tmp_name, target)
    return metrics


def load_lane_metrics(repo_root: Path | str, *, lane_id: str) -> dict[str, Any] | None:
    """Read the persisted metrics file; returns None if absent."""
    path = Path(repo_root) / METRICS_ROOT / f"{lane_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
