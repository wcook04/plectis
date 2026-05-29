"""
Unified navigation/compression ratchet ledger.

This packet keeps the existing audits useful by making them inputs to one
prioritized queue: authored-rung debt, projection debt, observed route behavior,
annex intake, and route lifecycle cleanup all land in the same comparable
surface.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping, Sequence

from system.lib.annex_currentness import build_annex_currentness
from system.lib.annex_movement_pressure_map import (
    SOURCE_JOB_BLOCKER_STATUS,
    build_annex_movement_pressure_map,
)
from system.lib.command_node_cache import REFRESH_ENV_VAR, cached_command_node, peek_cached_command_node
from system.lib.entrypoint_health import build_entrypoint_health
from system.lib.navigation_clusterability import build_navigation_clusterability_audit
from system.lib.navigation_route_intervention import build_hook_shadow_coverage
from system.lib.navigation_surface_contracts import DEBUG_TRACE, debug_trace_contract
from system.lib.phase_task_alignment import navigation_enforcement_residual_lane
from system.lib.routing_projection import routing_status


TACO_ANNEX = "arxiv-2604-19572"
SENTRUX_ANNEX = "sentrux"
DEFAULT_QUERY = "navigation context compression and agent route behavior"
METABOLISM_PROFILES = {"quick", "full"}
_COMMAND_CACHE_REFRESH_TRUE_VALUES = {"1", "true", "yes", "on", "refresh", "force"}
TACO_NAVIGATION_RATCHET_TARGETS = {
    "system/lib/navigation_metabolism_ledger.py",
    "system/lib/agent_execution_trace.py",
    "codex/doctrine/skills/kernel/navigation_seed.md",
    "codex/doctrine/paper_modules/navigation_hologram_theory.md",
    "codex/doctrine/paper_modules/hologram_substrate_navigation.md",
    "codex/standards/std_agent_entry_surface.json",
}


def _command_cache_refresh_requested() -> bool:
    return os.environ.get(REFRESH_ENV_VAR, "").strip().lower() in _COMMAND_CACHE_REFRESH_TRUE_VALUES
QUICK_COMMAND_CACHE_TTL_SECONDS = 600.0
QUICK_PROFILE_PHASE_WARN_MS = 2500.0
QUICK_PROFILE_TOTAL_WARN_MS = 10000.0
QUICK_CLI_OUTPUT_TARGET_TOKENS = 8000
QUICK_CLI_ROUTE_LIFECYCLE_ROW_LIMIT = 8
_NAVIGATION_MECHANISM_CACHE_INPUT_PATHS: tuple[str, ...] = (
    "system/lib/agent_execution_trace.py",
    "system/lib/navigation_mechanism_factory.py",
    "system/lib/navigation_metabolism_ledger.py",
    "codex/ledger/navigation_mechanism_acceptance/events.jsonl",
    "codex/ledger/navigation_mechanism_acceptance/dossiers",
    "codex/ledger/navigation_mechanism_acceptance/owner_packets",
    "codex/ledger/navigation_mechanism_acceptance/owner_loci",
    "codex/ledger/navigation_mechanism_acceptance/replay_receipts",
)
_ACTOR_DELIVERY_CACHE_INPUT_PATHS: tuple[str, ...] = (
    "AGENTS.override.md",
    "AGENTS.md",
    "CODEX.md",
    "CLAUDE.md",
    "kernel.py",
    "system/lib/agent_bootstrap_projection.py",
    "system/lib/entrypoint_health.py",
    "system/lib/kernel/commands/navigate.py",
    "system/lib/navigation_metabolism_ledger.py",
    "codex/doctrine/agent_bootstrap.json",
    "codex/standards/std_agent_entry_surface.json",
    "tools/meta/factory/check_agent_bootstrap_projection.py",
)
_ROUTING_STATUS_CACHE_INPUT_PATHS: tuple[str, ...] = (
    "AGENTS.md",
    "codex/doctrine/routing_hologram.json",
    "codex/doctrine/skills/skill_registry.json",
    "codex/standards/observe_apply/std_synth_seed.json",
    "codex/doctrine/skills/kernel/wave_conductor.md",
    "codex/doctrine/skills/kernel/delegation_protocol.md",
    "codex/doctrine/routing_anti_patterns.json",
    "state/agent_telemetry/latest_full/routing_candidates.json",
    "state/agent_telemetry/latest_full/grep_targets.json",
    "system/lib/routing_projection.py",
    "tools/meta/agent_telemetry/common.py",
)

# Quality-signal component classes, in stable order. Geometric-mean is taken
# over these and the bottleneck is the class whose component score is lowest
# when there is active debt. A clean active map has no bottleneck.
# The set deliberately matches `_count_by_class` keys; adding a class here
# REQUIRES adding it there too. Sentrux p002 (root-cause bottleneck taxonomy
# with geometric aggregation): independent root causes, normalized, geometric
# mean, lowest = focus. Adopted as a header signal that NEVER replaces the
# per-class debt_rows drilldowns (Sentrux skill local-adaptation rule).
_QUALITY_SIGNAL_CLASSES: tuple[str, ...] = (
    "entrypoint_debt",
    "authoring_debt",
    "projection_debt",
    "sufficiency_debt",
    "latency_debt",
    "timeout_debt",
    "clusterability_debt",
    "routing_coverage_debt",
    "annex_currentness_debt",
    "behavior_debt",
    "actor_delivery_debt",
    "annex_import_debt",
    "layer_sprawl_debt",
)
_ALWAYS_INCLUDE_ROUTE_LIFECYCLE_IDS: tuple[str, ...] = (
    "context_pack",
    "coverage_enforcement_matrix",
    "phase_task_alignment",
    "clusterability_audit",
    "annex_routing_coverage",
    "annex_currentness",
    "annex_movement_pressure_map",
    "annex_navigation_dogfood",
    "paper_lattice",
    "skill_find",
    "paper_modules.row_flag_all",
    "standards.row_flag_all",
    "python_files.row_flag_all",
    "python_scopes.row_flag_all",
    "frontend_components.row_flag_all",
    "principles.row_flag_all",
    "annex_patterns.row_flag_all",
    "annex_distillation_patterns.row_flag_all",
    "phase.summary_default",
    "codex.model_instructions_file",
)
_ROUTE_LIFECYCLE_EXTRA_TRIM_ROWS = 1
_CLI_ROUTE_LIFECYCLE_PRIORITY_IDS: tuple[str, ...] = (
    "context_pack",
    "coverage_enforcement_matrix",
    "phase_task_alignment",
    "annex_currentness",
    "annex_movement_pressure_map",
    "annex_navigation_dogfood",
    "skill_find",
    "phase.summary_default",
)
_BUDGET_TRIM_SENTINEL_DEBT_IDS: tuple[str, ...] = (
    # This row is the acceptance sentinel for proving clusterability debt still
    # exposes the standards/skills map blocker after budget trimming.
    "clusterability:standard_skill_map",
)
_SKILL_FIND_POLICY_GAP_DEBT_ID = "behavior:skill_find_first_contact:policy_gap"


def _skill_find_debug_trace_policy_receipt() -> dict[str, Any]:
    """Summarize whether skill-find is actually hardened as DEBUG_TRACE only."""
    contract = debug_trace_contract(
        surface_id="skill_find",
        command="./repo-python kernel.py --skill-find",
        query="<skill_id>",
    )
    default_policy = contract.get("default_output_policy")
    debug_policy = contract.get("debug_output_policy")
    if not isinstance(default_policy, Mapping):
        default_policy = {}
    if not isinstance(debug_policy, Mapping):
        debug_policy = {}
    hardened = (
        contract.get("surface_role") == DEBUG_TRACE
        and contract.get("first_contact_allowed") is False
        and str(contract.get("replacement") or "").startswith("./repo-python kernel.py --entry")
        and default_policy.get("ranked_matches") == "hidden"
        and debug_policy.get("requires_flag") == "--debug"
    )
    return {
        "status": "hardened_debug_trace_only" if hardened else "policy_gap",
        "route_id": "skill_find",
        "surface_role": contract.get("surface_role"),
        "first_contact_allowed": contract.get("first_contact_allowed"),
        "replacement": contract.get("replacement"),
        "debug_command": contract.get("debug_command"),
        "ranked_matches_default": default_policy.get("ranked_matches"),
        "debug_requires_flag": debug_policy.get("requires_flag"),
        "safe_first_surface": "./repo-python kernel.py --option-surface skills --band cluster_flag",
    }


def _has_skill_find_first_contact_behavior(debt_rows: Sequence[Mapping[str, Any]]) -> bool:
    return any(row.get("debt_id") == "behavior:skill_find_first_contact" for row in debt_rows)


def _compact_repair_hints(value: Any, *, limit: int = 3) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return hints
    for hint in value:
        if not isinstance(hint, Mapping):
            continue
        row: dict[str, Any] = {}
        for key in ("hint_id", "reason", "preferred_next"):
            if hint.get(key):
                row[key] = _trim(hint.get(key), max_chars=220)
        if row:
            hints.append(row)
        if len(hints) >= limit:
            break
    return hints


def _example_command_shape_tags(value: Any, *, limit: int = 8) -> list[str]:
    tags: list[str] = []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return tags
    for span in value:
        if not isinstance(span, Mapping):
            continue
        for tag in span.get("command_shape_tags") or []:
            tag_str = str(tag or "").strip()
            if tag_str and tag_str not in tags:
                tags.append(tag_str)
            if len(tags) >= limit:
                return tags
    return tags


def _append_skill_find_policy_gap_if_needed(
    debt_rows: list[dict[str, Any]],
    *,
    policy_receipt: Mapping[str, Any],
    source_surface: str,
    evidence: str,
) -> None:
    """Emit policy debt only when the route contract itself is not hardened."""
    if _has_skill_find_first_contact_behavior(debt_rows):
        return
    if str(policy_receipt.get("status") or "") == "hardened_debug_trace_only":
        return
    debt_rows.append(
        _debt_row(
            debt_id=_SKILL_FIND_POLICY_GAP_DEBT_ID,
            debt_class="behavior_debt",
            priority=86,
            title="skill-find still exists as a tempting first-contact search route",
            evidence=evidence,
            repair_class="hook_steering_plus_context_pack_first_contact",
            target_files=[
                ".claude/hooks/runtime_hook.py",
                "system/lib/kernel/commands/navigate.py",
                "system/lib/navigation_surface_contracts.py",
            ],
            tests=[
                "hook or route policy steers skill-find first contact to skills.cluster_flag/context-pack",
                "skill-find remains available only as explicit evidence drilldown",
            ],
            source_surface=source_surface,
            extra={
                "anti_pattern": "keyword_search_before_cluster_surface",
                "better_first_surface": "./repo-python kernel.py --option-surface skills --band cluster_flag",
                "policy_receipt": dict(policy_receipt),
            },
        )
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _profile_phase(sink: list[dict[str, Any]] | None, phase: str, fn) -> Any:
    started = perf_counter()
    try:
        return fn()
    finally:
        if sink is not None:
            sink.append({"phase": phase, "ms": round((perf_counter() - started) * 1000, 3)})


def _latency_targets_for_phase(phase: str) -> list[str]:
    if phase == "actor_delivery_receipt":
        return [
            "tools/meta/factory/check_agent_bootstrap_projection.py",
            "system/lib/navigation_metabolism_ledger.py",
        ]
    if phase == "entrypoint_health":
        return ["system/lib/entrypoint_health.py", "system/lib/navigation_metabolism_ledger.py"]
    if phase == "process_audit":
        return ["system/lib/agent_execution_trace.py", "system/lib/navigation_metabolism_ledger.py"]
    return ["system/lib/navigation_metabolism_ledger.py"]


def _latency_profile(
    phase_rows: Sequence[Mapping[str, Any]],
    *,
    total_ms: float,
    phase_warn_ms: float,
    total_warn_ms: float,
) -> dict[str, Any]:
    slow_phases = [
        dict(row)
        for row in phase_rows
        if float(row.get("ms") or 0.0) > phase_warn_ms
    ]
    return {
        "schema_version": "navigation_metabolism_latency_profile_v0",
        "phase_warn_ms": phase_warn_ms,
        "total_warn_ms": total_warn_ms,
        "total_ms": round(total_ms, 3),
        "phase_count": len(phase_rows),
        "slow_phase_count": len(slow_phases),
        "status": "latency_debt" if slow_phases or total_ms > total_warn_ms else "within_budget",
        "phases": [dict(row) for row in phase_rows],
        "slow_phases": slow_phases,
        "profile_command": "./repo-python kernel.py --command-profile navigation-metabolism --metabolism-profile quick --context-budget 12000",
        "process_bottleneck_command": "./repo-python kernel.py --process-bottlenecks",
    }


def _latency_profile_debt_rows(
    phase_rows: Sequence[Mapping[str, Any]],
    *,
    surface: str,
    total_ms: float,
    phase_warn_ms: float,
    total_warn_ms: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in phase_rows:
        phase = str(row.get("phase") or "unknown")
        ms = float(row.get("ms") or 0.0)
        if ms <= phase_warn_ms:
            continue
        safe_phase = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", phase).strip("_") or "unknown"
        rows.append(
            _debt_row(
                debt_id=f"latency:{surface}:{safe_phase}",
                debt_class="latency_debt",
                priority=91 if phase == "actor_delivery_receipt" else 82,
                title="Navigation metabolism phase exceeds quick latency budget",
                evidence=f"{surface} phase {phase!r} took {round(ms, 3)}ms; phase budget is {phase_warn_ms}ms.",
                repair_class="command_latency_budget_repair",
                target_files=_latency_targets_for_phase(phase),
                tests=[
                    "./repo-python kernel.py --command-profile navigation-metabolism --metabolism-profile quick --context-budget 12000",
                    "./repo-python kernel.py --navigation-metabolism \"command latency\" --metabolism-profile quick --context-budget 12000",
                ],
                source_surface=f"{surface}.latency_profile",
                route_id=phase,
                extra={
                    "phase_ms": round(ms, 3),
                    "phase_warn_ms": phase_warn_ms,
                    "profile_command": "./repo-python kernel.py --command-profile navigation-metabolism --metabolism-profile quick --context-budget 12000",
                },
            )
        )
    if total_ms > total_warn_ms:
        rows.append(
            _debt_row(
                debt_id=f"latency:{surface}:total",
                debt_class="latency_debt",
                priority=89,
                title="Navigation metabolism total runtime exceeds quick latency budget",
                evidence=f"{surface} total runtime was {round(total_ms, 3)}ms; total budget is {total_warn_ms}ms.",
                repair_class="command_latency_budget_repair",
                target_files=["system/lib/navigation_metabolism_ledger.py", "system/lib/kernel/commands/navigate.py"],
                tests=[
                    "./repo-python kernel.py --command-profile navigation-metabolism --metabolism-profile quick --context-budget 12000",
                    "./repo-python kernel.py --process-bottlenecks",
                ],
                source_surface=f"{surface}.latency_profile",
                extra={
                    "total_ms": round(total_ms, 3),
                    "total_warn_ms": total_warn_ms,
                },
            )
        )
    return rows


def _json_bytes(value: Any) -> int:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    except TypeError:
        text = json.dumps(str(value), ensure_ascii=False)
    return len(text.encode("utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dict(data) if isinstance(data, dict) else {}


def _trim(text: Any, *, max_chars: int = 220) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."


def _tokens(text: str) -> list[str]:
    return [part for part in re.split(r"\s+", str(text or "").strip()) if part]


def _has_explicit_ids(command: str) -> bool:
    return "--ids" in _tokens(command)


def _debt_row(
    *,
    debt_id: str,
    debt_class: str,
    priority: int,
    title: str,
    evidence: str,
    repair_class: str,
    target_files: Sequence[str] = (),
    tests: Sequence[str] = (),
    source_surface: str | None = None,
    route_id: str | None = None,
    artifact_kind: str | None = None,
    artifact_id: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "debt_id": debt_id,
        "debt_class": debt_class,
        "priority": priority,
        "title": title,
        "evidence": _trim(evidence, max_chars=320),
        "repair_class": repair_class,
        "target_files": list(target_files),
        "tests": list(tests),
    }
    if source_surface:
        row["source_surface"] = source_surface
    if route_id:
        row["route_id"] = route_id
    if artifact_kind:
        row["artifact_kind"] = artifact_kind
    if artifact_id:
        row["artifact_id"] = artifact_id
    if extra:
        row.update(dict(extra))
    return row


def _is_active_debt_row(row: Mapping[str, Any]) -> bool:
    return row.get("active_debt") is not False


def _active_debt_rows(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [row for row in rows if _is_active_debt_row(row)]


def _authoring_debt_rows(surface_audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in surface_audit.get("authoring_debt") or []:
        if not isinstance(source, Mapping):
            continue
        artifact_kind = str(source.get("artifact_kind") or "unknown")
        artifact_id = str(source.get("artifact_id") or source.get("route_id") or "unknown")
        if artifact_kind == "kernel_command_output":
            continue
        rows.append(
            _debt_row(
                debt_id=f"authoring:{artifact_kind}:{artifact_id}",
                debt_class="authoring_debt",
                priority=80 if artifact_kind == "paper_modules" else 70,
                title=f"{artifact_kind}.{artifact_id} lacks authored compressed rungs",
                evidence=(
                    f"authoring_status={source.get('authoring_status')}; "
                    f"missing={source.get('missing_fields') or []}"
                ),
                repair_class=str(source.get("repair_class") or "authoring_contract_migration"),
                target_files=[str(source.get("source_ref") or "")] if source.get("source_ref") else [],
                tests=[
                    "surface-authoring-audit reports no missing compressed rungs for this artifact",
                    "context-pack can select this artifact from cluster/flag surfaces",
                ],
                source_surface="--surface-authoring-audit",
                artifact_kind=artifact_kind,
                artifact_id=artifact_id,
                extra={
                    "standard": source.get("standard_to_update"),
                    "safe_drilldown": source.get("safe_drilldown"),
                },
            )
        )
    return rows


def _projection_debt_rows(surface_audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for route in surface_audit.get("route_map") or []:
        if not isinstance(route, Mapping):
            continue
        status = str(route.get("contract_status") or "")
        if status in {"valid", "valid_large_surface"}:
            continue
        route_id = str(route.get("route_id") or "unknown")
        contract_expectation = str(route.get("contract_expectation") or "")
        library_reference_only = route_id.endswith(".library") and contract_expectation == "known_unsafe_reference"
        priority = 90 if "row_flag_all" in route_id or route_id.startswith("phase.") else 75
        title = f"{route_id} violates its advertised surface role"
        evidence_prefix = f"contract_status={status}"
        if library_reference_only:
            title = f"{route_id} is a library-only unsafe reference; public CLI must redirect"
            evidence_prefix = f"library_reference_only=true; contract_status={status}"
        rows.append(
            _debt_row(
                debt_id=f"projection:{route_id}",
                debt_class="projection_debt",
                priority=priority,
                title=title,
                evidence=(
                    f"{evidence_prefix}; budget_relation={route.get('budget_relation')}; "
                    f"bytes={route.get('pretty_json_bytes')}"
                ),
                repair_class="projection_contract_repair",
                target_files=[
                    "system/lib/kernel/commands/navigate.py",
                    "system/lib/standard_option_surface.py",
                ],
                tests=[
                    "navigation-surface-audit reports the route contract as valid or explicitly unsafe-only",
                    "unsafe route emits a drilldown receipt rather than a large entry packet",
                ],
                source_surface="--navigation-surface-audit",
                route_id=route_id,
                extra={
                    "command": route.get("command"),
                    "safe_alternative": route.get("safe_alternative"),
                    "contract_expectation": route.get("contract_expectation"),
                    "library_reference_only": library_reference_only,
                    "active_debt": False if library_reference_only else True,
                    "advisory_only": True if library_reference_only else None,
                    "compatibility_behavior": "CLI redirects all-row flag calls to cluster_flag unless --ids is explicit"
                    if library_reference_only
                    else None,
                },
            )
        )
    return rows


def _entrypoint_debt_rows(entrypoint_health: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in entrypoint_health.get("instruction_files") or []:
        if not isinstance(source, Mapping):
            continue
        path = str(source.get("path") or "unknown")
        if source.get("budget_status") == "over_budget":
            # The entrypoint_health summary computes over_budget_count from
            # primary entry files only (load_posture != generated_or_doctrine_skill)
            # and generated_or_doctrine_over_budget_count separately. The debt
            # row must use the same partition so a single per-file load_posture
            # is the normalized source of truth for both surfaces. Mixing the
            # two under a single repair_class (entrypoint_shrink_or_split)
            # creates a split-brain metric where the row exists but
            # over_budget_count is 0. The two over-budget categories have
            # different repair owners: primary entry files want shrink/split;
            # generated/doctrine skill files want compaction or projection
            # boundary tightening at the generator owner.
            posture = str(source.get("load_posture") or "")
            if posture == "generated_or_doctrine_skill":
                rows.append(
                    _debt_row(
                        debt_id=f"entrypoint:{path}:generated_or_doctrine_over_budget",
                        debt_class="entrypoint_debt",
                        priority=88,
                        title=f"{path} (generated/doctrine skill) exceeds its instruction-file budget",
                        evidence=f"bytes={source.get('bytes')}; budget={source.get('budget')}; load_posture={posture}",
                        repair_class="generated_or_doctrine_skill_compaction",
                        target_files=[
                            path,
                            "codex/standards/std_agent_entry_surface.json",
                        ],
                        tests=[
                            "entrypoint health reports the generated/doctrine skill within budget",
                        ],
                        source_surface="entrypoint_health",
                        extra={
                            "bytes": source.get("bytes"),
                            "budget": source.get("budget"),
                            "load_posture": posture,
                            "over_budget_subkind": "generated_or_doctrine_skill",
                        },
                    )
                )
            else:
                rows.append(
                    _debt_row(
                        debt_id=f"entrypoint:{path}:over_budget",
                        debt_class="entrypoint_debt",
                        priority=98,
                        title=f"{path} exceeds its instruction-file budget",
                        evidence=f"bytes={source.get('bytes')}; budget={source.get('budget')}; load_posture={posture}",
                        repair_class="entrypoint_shrink_or_split",
                        target_files=[
                            path,
                            "docs/agent_entry_reference.md",
                            "codex/standards/std_agent_entry_surface.json",
                            "codex/doctrine/agent_bootstrap.json",
                        ],
                        tests=[
                            "entrypoint health reports the instruction file within budget",
                            "bootstrap projection checker fails when loaded entry files exceed budget",
                        ],
                        source_surface="entrypoint_health",
                        extra={
                            "bytes": source.get("bytes"),
                            "budget": source.get("budget"),
                            "load_posture": posture,
                            "over_budget_subkind": "primary_entry_file",
                        },
                    )
                )
    for hit in entrypoint_health.get("forbidden_first_contact_hits") or []:
        if not isinstance(hit, Mapping):
            continue
        path = str(hit.get("path") or "unknown")
        kind = str(hit.get("kind") or "unknown")
        line = hit.get("line")
        rows.append(
            _debt_row(
                debt_id=f"entrypoint:{path}:{kind}:{line or 'global'}",
                debt_class="entrypoint_debt",
                priority=92,
                title=f"{path} contains stale first-contact route doctrine",
                evidence=f"kind={kind}; line={line}; text={hit.get('text')}",
                repair_class="stale_first_contact_route_rewrite",
                target_files=[path],
                tests=[
                    "loaded entry regions mention context-pack and navigation-metabolism as first-contact routes",
                    "legacy search/open routes are labeled drilldown-only",
                ],
                source_surface="entrypoint_health",
                extra={"hit_kind": kind, "line": line},
            )
        )
    return rows


def _actor_delivery_receipt(root: Path) -> dict[str, Any]:
    try:
        from tools.meta.factory import check_agent_bootstrap_projection as checker

        previous_root = checker.REPO_ROOT
        checker.REPO_ROOT = root
        try:
            cfg = checker.load_agent_bootstrap_config(root)
            context = checker.build_actor_receipt_context(root, cfg)
            return checker.build_actor_receipt(context, run_smokes=False)
        finally:
            checker.REPO_ROOT = previous_root
    except Exception as exc:  # noqa: BLE001 - metabolism should report, not fail, on missing checker substrate
        return {
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _cached_actor_delivery_receipt(
    root: Path,
    *,
    allow_build: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    kwargs = {
        "node_id": "navigation_metabolism.actor_delivery_receipt.quick",
        "key": {"scope": "quick", "builder": "agent_bootstrap_actor_receipt"},
        "freshness_policy": "ttl_for_actor_delivery_smoke_plus_static_source_manifest",
        "dynamic_inputs_manifested": False,
    }
    if not allow_build:
        payload, status = peek_cached_command_node(
            root,
            **kwargs,
            input_paths=_ACTOR_DELIVERY_CACHE_INPUT_PATHS,
            ttl_s=QUICK_COMMAND_CACHE_TTL_SECONDS,
        )
        if payload is None:
            return {
                "kind": "agent_bootstrap_actor_receipt",
                "status": "deferred_by_quick_profile",
                "reason": (
                    "actor-delivery receipt cache missing or stale; quick metabolism "
                    "does not rebuild the projection checker"
                ),
                "safe_alternative": (
                    "./repo-python tools/meta/factory/check_agent_bootstrap_projection.py --actor-receipt"
                ),
                "blockers": [],
                "warnings": [],
            }, status
        return dict(payload) if isinstance(payload, Mapping) else {"status": "unavailable"}, status
    payload, status = cached_command_node(
        root,
        node_id=kwargs["node_id"],
        key=kwargs["key"],
        input_paths=_ACTOR_DELIVERY_CACHE_INPUT_PATHS,
        ttl_s=QUICK_COMMAND_CACHE_TTL_SECONDS,
        builder=lambda: _actor_delivery_receipt(root),
        freshness_policy=kwargs["freshness_policy"],
        dynamic_inputs_manifested=kwargs["dynamic_inputs_manifested"],
    )
    return dict(payload) if isinstance(payload, Mapping) else {"status": "unavailable"}, status


def _actor_delivery_debt_rows(receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(receipt, Mapping) or receipt.get("status") == "unavailable":
        return []
    rows: list[dict[str, Any]] = []
    shared_targets = [
        "codex/standards/std_agent_entry_surface.json",
        "codex/doctrine/agent_bootstrap.json",
        "tools/meta/factory/check_agent_bootstrap_projection.py",
    ]
    shared_tests = [
        "./repo-python tools/meta/factory/check_agent_bootstrap_projection.py --actor-receipt",
        "./repo-python tools/meta/factory/check_agent_bootstrap_projection.py",
    ]
    summary_extra = {
        "receipt_kind": receipt.get("kind"),
        "required_delivery_route_count": receipt.get("required_delivery_route_count"),
        "total_situation_route_count": receipt.get("total_situation_route_count"),
        "actor_delivery_decision_count": receipt.get("actor_delivery_decision_count"),
        "unknown_delivery_decision_count": receipt.get("unknown_delivery_decision_count"),
        "missing_workitem_ref_count": receipt.get("missing_workitem_ref_count"),
        "missing_non_delivery_reason_count": receipt.get("missing_non_delivery_reason_count"),
        "warning_count": len(receipt.get("warnings") or []),
    }
    for index, blocker in enumerate(receipt.get("blockers") or []):
        label = _trim(blocker, max_chars=120)
        safe_label = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", label).strip("_") or f"blocker_{index}"
        rows.append(
            _debt_row(
                debt_id=f"actor_delivery:{safe_label}",
                debt_class="actor_delivery_debt",
                priority=97,
                title="Actor-delivery receipt blocker",
                evidence=str(blocker),
                repair_class="actor_delivery_receipt_missing",
                target_files=shared_targets,
                tests=shared_tests,
                source_surface="check_agent_bootstrap_projection.py --actor-receipt",
                extra=summary_extra,
            )
        )
    structured_specs = (
        (
            "unknown_delivery_decisions",
            "actor_delivery_decision_missing",
            "Actor-delivery decision missing",
            92,
        ),
        (
            "missing_workitem_refs",
            "actor_delivery_defer_workitem_missing",
            "Deferred actor delivery lacks WorkItem reference",
            88,
        ),
        (
            "missing_non_delivery_reasons",
            "actor_delivery_reason_missing",
            "Actor-delivery non-delivery reason missing",
            70,
        ),
    )
    for list_key, repair_class, title, priority in structured_specs:
        for index, source in enumerate(receipt.get(list_key) or []):
            if not isinstance(source, Mapping):
                continue
            route_id = str(source.get("situation_id") or source.get("route_id") or f"row_{index}")
            safe_route = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", route_id).strip("_") or f"row_{index}"
            evidence = (
                f"route_id={source.get('route_id')}; decision={source.get('decision')}; "
                f"reason={source.get('reason')}; workitem_ref={source.get('workitem_ref')}"
            )
            rows.append(
                _debt_row(
                    debt_id=f"actor_delivery:{repair_class}:{safe_route}",
                    debt_class="actor_delivery_debt",
                    priority=priority,
                    title=title,
                    evidence=evidence,
                    repair_class=repair_class,
                    target_files=shared_targets,
                    tests=shared_tests,
                    source_surface="check_agent_bootstrap_projection.py --actor-receipt",
                    route_id=route_id,
                    extra={**summary_extra, "receipt_list_key": list_key},
                )
            )
    return rows


def _fitness_debt_rows(fitness_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in fitness_payload.get("debt_candidates") or []:
        if not isinstance(source, Mapping):
            continue
        debt_class = str(source.get("debt_class") or "")
        if debt_class not in {"sufficiency_debt", "latency_debt", "timeout_debt"}:
            continue
        rows.append(
            _debt_row(
                debt_id=str(source.get("debt_id") or f"{debt_class}:unknown"),
                debt_class=debt_class,
                priority=int(source.get("priority") or 75),
                title=str(source.get("title") or "Navigation fitness debt"),
                evidence=str(source.get("evidence") or ""),
                repair_class=str(source.get("repair_class") or "navigation_fitness_repair"),
                target_files=[str(item) for item in source.get("target_files") or []],
                tests=[str(item) for item in source.get("tests") or []],
                source_surface="--navigation-fitness",
                route_id=str(source.get("route_type") or ""),
                extra={
                    "task_id": source.get("task_id"),
                    "fitness_suite": fitness_payload.get("suite"),
                    "fitness_mode": source.get("fitness_mode") or (fitness_payload.get("strategy") or {}).get("fitness_mode"),
                    "failure_kind": source.get("failure_kind"),
                    "route_role": source.get("route_role"),
                    "slow_stage": source.get("slow_stage"),
                    "hidden_expected_artifacts": source.get("hidden_expected_artifacts"),
                },
            )
        )
    return rows


def _clusterability_debt_rows(clusterability: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in clusterability.get("debt_rows") or []:
        if not isinstance(source, Mapping):
            continue
        rows.append(
            _debt_row(
                debt_id=str(source.get("debt_id") or "clusterability:unknown"),
                debt_class="clusterability_debt",
                priority=int(source.get("priority") or 76),
                title=str(source.get("title") or "Clusterability debt"),
                evidence=str(source.get("evidence") or ""),
                repair_class=str(source.get("repair_class") or "clusterability_repair"),
                target_files=[str(item) for item in source.get("target_files") or []],
                tests=[str(item) for item in source.get("tests") or []],
                source_surface="--clusterability-audit",
                artifact_kind=str(source.get("artifact_kind") or ""),
                extra={
                    "safe_alternative": source.get("safe_alternative"),
                },
            )
        )
    return rows


def _routing_coverage_debt_rows(coverage: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    summary = coverage.get("summary") if isinstance(coverage.get("summary"), Mapping) else {}
    for source in coverage.get("debt_rows") or []:
        if not isinstance(source, Mapping):
            continue
        rows.append(
            _debt_row(
                debt_id=str(source.get("debt_id") or "routing_coverage:unknown"),
                debt_class="routing_coverage_debt",
                priority=int(source.get("priority") or 76),
                title=str(source.get("title") or "Routing coverage debt"),
                evidence=str(source.get("evidence") or ""),
                repair_class=str(source.get("repair_class") or "routing_coverage_repair"),
                target_files=[str(item) for item in source.get("target_files") or []],
                tests=[str(item) for item in source.get("tests") or []],
                source_surface="--annex-routing-coverage",
                artifact_kind=str(source.get("artifact_kind") or "annex_patterns"),
                extra={
                    "safe_alternative": source.get("safe_alternative"),
                    "unrouted_rate": summary.get("unrouted_rate"),
                    "unrouted_rows": summary.get("unrouted_rows"),
                    "threshold": (coverage.get("budget") or {}).get("unrouted_rate_threshold")
                    if isinstance(coverage.get("budget"), Mapping)
                    else None,
                },
            )
        )
    return rows


def _annex_currentness_debt_rows(currentness: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in currentness.get("debt_rows") or []:
        if not isinstance(source, Mapping):
            continue
        row = dict(source)
        row.setdefault("debt_class", "annex_currentness_debt")
        row.setdefault("source_surface", "annexes/annex_sync_digest.json")
        rows.append(row)
    return rows


def _annex_dogfood_debt_rows(dogfood: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in dogfood.get("protocol_findings") or []:
        if not isinstance(source, Mapping):
            continue
        failure_mode = str(source.get("failure_mode") or "")
        if failure_mode in {"currentness_blind_spot", "row_job_gap"}:
            continue
        rows.append(
            _debt_row(
                debt_id=str(source.get("finding_id") or f"annex_navigation_dogfood:{failure_mode or 'unknown'}"),
                debt_class="behavior_debt",
                priority=78 if source.get("severity") == "high" else 66,
                title=str(source.get("title") or "annex navigation dogfood finding"),
                evidence=str(source.get("evidence") or ""),
                repair_class=str(source.get("repair_route") or "annex_navigation_protocol_repair"),
                target_files=[str(item) for item in source.get("target_files") or []],
                tests=[
                    "annex-navigation-dogfood emits no protocol finding for this failure mode",
                    "navigation metabolism ingests dogfood findings without duplicating currentness/routing/clusterability debt",
                ],
                source_surface="--annex-navigation-dogfood",
                route_id="annex_navigation_dogfood",
                extra={
                    "failure_mode": failure_mode,
                    "next_command": source.get("next_command"),
                    "authority": source.get("authority"),
                },
            )
        )
    return rows


def _annex_movement_pressure_debt_rows(pressure_map: Mapping[str, Any]) -> list[dict[str, Any]]:
    quality = pressure_map.get("quality_signal") if isinstance(pressure_map.get("quality_signal"), Mapping) else {}
    summary = pressure_map.get("summary") if isinstance(pressure_map.get("summary"), Mapping) else {}
    status = str(quality.get("status") or "")
    if status in {"ok", "no_mine_upstream_delta_rows", SOURCE_JOB_BLOCKER_STATUS}:
        return []
    missing = int(summary.get("missing_report_count") or 0)
    unclassified = int(summary.get("unclassified_count") or 0)
    source_blockers = int(summary.get("source_job_blocker_count") or 0)
    source_count = int(summary.get("source_row_job_count") or 0)
    selected_count = int(summary.get("selected_row_job_count") or 0)
    if missing <= 0 and unclassified <= 0 and source_blockers <= 0:
        return []
    if source_blockers > 0:
        title = "annex movement-pressure map has pre-mining source row-job blockers"
        evidence = (
            f"quality_status={status}; source_row_job_count={source_count}; "
            f"selected_row_job_count={selected_count}; source_job_blocker_count={source_blockers}; "
            f"classification_counts={summary.get('source_classification_counts')}"
        )
        tests = [
            "annex movement-pressure map emits blocker status when source row jobs are filtered before mining",
            "navigation metabolism counts hidden source row jobs as annex currentness debt instead of false green",
        ]
    else:
        title = "annex movement-pressure map could not classify selected movement rows"
        evidence = f"quality_status={status}; missing_report_count={missing}; unclassified_count={unclassified}"
        tests = [
            "annex movement-pressure map classifies selected mine_upstream_delta rows",
            "movement-pressure rows include report evidence paths before dogfood consumes them",
        ]
    return [
        _debt_row(
            debt_id="annex_movement_pressure_map:evidence_or_classification_gap",
            debt_class="annex_currentness_debt",
            priority=78 if source_blockers > 0 else 74,
            title=title,
            evidence=evidence,
            repair_class="annex_movement_pressure_route_repair",
            target_files=["system/lib/annex_movement_pressure_map.py", "system/lib/metabolism_row_jobs.py"],
            tests=tests,
            source_surface="--annex-movement-pressure-map",
            route_id="annex_movement_pressure_map",
            extra={
                "safe_alternative": "./repo-python kernel.py --annex-movement-pressure-map \"improve annex navigation protocol\" --context-budget 12000",
                "quality_signal": quality,
            },
        )
    ]


def normalize_agent_route_events(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Classify route events from Claude/Codex/session fixtures into behavior debt."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in events:
        if not isinstance(event, Mapping):
            continue
        command = str(event.get("command") or event.get("input") or "")
        first_contact = bool(event.get("first_contact"))
        lower = command.lower()
        route_family = str(event.get("route_family") or "")
        anti_pattern = ""
        better_surface = ""
        debt_id = ""
        title = ""
        priority = 60
        if "--skill-find" in lower and first_contact:
            debt_id = "behavior:skill_find_first_contact"
            anti_pattern = "keyword_search_before_cluster_surface"
            better_surface = "./repo-python kernel.py --option-surface skills --band cluster_flag"
            title = "skill-find used as first-contact navigation"
            priority = 88
        elif "kernel.py" in lower and "--help" in lower and first_contact:
            debt_id = "behavior:raw_kernel_help_first_contact"
            anti_pattern = "raw_help_before_kind_atlas_or_context_pack"
            better_surface = "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000"
            title = "raw kernel --help used as first-contact navigation"
            priority = 84
        elif "--option-surface" in lower and "--band flag" in lower and not _has_explicit_ids(command):
            if any(
                surface in lower
                for surface in (
                    "paper_modules",
                    "standards",
                    "skills",
                    "python_files",
                    "python_scopes",
                    "frontend_components",
                    "principles",
                    "annex_patterns",
                    "annex_distillation_patterns",
                )
            ):
                if "paper_modules" in lower:
                    surface = "paper_modules"
                elif "frontend_components" in lower:
                    surface = "frontend_components"
                elif "annex_distillation_patterns" in lower:
                    surface = "annex_distillation_patterns"
                elif "principles" in lower:
                    surface = "principles"
                elif "annex_patterns" in lower:
                    surface = "annex_patterns"
                elif "standards" in lower:
                    surface = "standards"
                elif "skills" in lower:
                    surface = "skills"
                elif "python_scopes" in lower:
                    surface = "python_scopes"
                else:
                    surface = "python_files"
                debt_id = f"behavior:{surface}_all_row_flag"
                anti_pattern = "high_cardinality_row_expansion_before_cluster_surface"
                better_surface = f"./repo-python kernel.py --option-surface {surface} --band cluster_flag"
                title = f"{surface} all-row flag requested before cluster surface"
                priority = 82
        elif event.get("persisted_output") or event.get("output_bytes", 0) and int(event.get("output_bytes") or 0) > 48000:
            debt_id = f"behavior:large_output:{route_family or 'unknown'}"
            anti_pattern = "large_output_or_persisted_output_from_navigation_route"
            better_surface = "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000"
            title = "navigation route produced large or persisted output"
            priority = 80
        elif event.get("rerun_after_compressed_output") or event.get("requested_full_output"):
            debt_id = f"behavior:overcompression_complaint:{route_family or 'unknown'}"
            anti_pattern = "compressed_packet_was_insufficient_for_next_drilldown"
            better_surface = "promote similar route/query to card or context band"
            title = "agent behavior complained about over-compression"
            priority = 74
        if not debt_id or debt_id in seen:
            continue
        seen.add(debt_id)
        rows.append(
            _debt_row(
                debt_id=debt_id,
                debt_class="behavior_debt",
                priority=priority,
                title=title,
                evidence=(
                    f"session={event.get('session_id') or 'unknown'}; tool={event.get('tool') or event.get('tool_name') or 'unknown'}; "
                    f"command={_trim(command, max_chars=180)}"
                ),
                repair_class="hook_steering_plus_context_pack_first_contact",
                target_files=[
                    ".claude/hooks/runtime_hook.py",
                    "system/lib/kernel/commands/navigate.py",
                    "system/lib/navigation_context_pack.py",
                ],
                tests=[
                    "runtime hook steers first-contact keyword search to cluster/context surfaces",
                    "context-pack exposes the selected artifact without token-overlap explanation blobs",
                ],
                source_surface="agent_path_event_stream",
                extra={
                    "anti_pattern": anti_pattern,
                    "better_first_surface": better_surface,
                    "agent_runtime": event.get("agent_runtime") or event.get("runtime"),
                    "first_contact": first_contact,
                    "output_bytes": event.get("output_bytes"),
                    "hook_hint_fired": event.get("hook_hint_fired"),
                },
            )
        )
    return rows


def _diagnostics_behavior_rows(summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    metrics = summary.get("metrics") if isinstance(summary.get("metrics"), Mapping) else {}
    rows: list[dict[str, Any]] = []
    ladder = metrics.get("ladder_skip") if isinstance(metrics.get("ladder_skip"), Mapping) else {}
    context = metrics.get("context_pressure") if isinstance(metrics.get("context_pressure"), Mapping) else {}
    discoverability = metrics.get("discoverability") if isinstance(metrics.get("discoverability"), Mapping) else {}
    bad_ratio = ladder.get("ratio_bad_to_good_bash")
    if isinstance(bad_ratio, (int, float)) and bad_ratio > 0:
        rows.append(
            _debt_row(
                debt_id="behavior:session_diagnostics:ladder_skip",
                debt_class="behavior_debt",
                priority=72,
                title="recent sessions still show native-tool ladder skip",
                evidence=f"ratio_bad_to_good_bash={bad_ratio}; top={ladder.get('bash_should_be_native_top') or []}",
                repair_class="hook_steering_or_skill_surface_repair",
                target_files=[".claude/hooks/runtime_hook.py", "codex/doctrine/skills/kernel/navigation_seed.md"],
                tests=["session diagnostics summary records fewer first-contact ladder skips after steering"],
                source_surface="--session-diagnostics --diagnostics-summary",
                extra={"better_first_surface": "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000"},
            )
        )
    if int(context.get("max_compactions") or 0) > 0:
        rows.append(
            _debt_row(
                debt_id="behavior:session_diagnostics:context_pressure",
                debt_class="behavior_debt",
                priority=68,
                title="recent sessions show compaction pressure",
                evidence=(
                    f"sessions_with_compactions={context.get('codex_sessions_with_compactions')}; "
                    f"max_compactions={context.get('max_compactions')}"
                ),
                repair_class="route_output_compression_rule",
                target_files=["system/lib/navigation_surface_audit.py", "system/lib/navigation_context_pack.py"],
                tests=["navigation metabolism ledger keeps session context-pressure evidence compact"],
                source_surface="--session-diagnostics --diagnostics-summary",
            )
        )
    unresolved = int(discoverability.get("route_miss_unresolved") or 0)
    candidates = int(discoverability.get("route_miss_candidates") or 0)
    if unresolved or candidates:
        rows.append(
            _debt_row(
                debt_id="behavior:session_diagnostics:route_misses",
                debt_class="behavior_debt",
                priority=66,
                title="recent prompts generated unresolved route-miss candidates",
                evidence=f"candidate_count={candidates}; unresolved_count={unresolved}",
                repair_class="docs_route_or_context_pack_alias_repair",
                target_files=["system/lib/kernel/commands/navigate.py", "docs/agent_instruction_router.md"],
                tests=["route-miss candidate fixture resolves through docs-route or context-pack"],
                source_surface="--session-diagnostics --diagnostics-summary",
            )
        )
    return rows


def _session_diagnostics_summary(*, last: int = 5) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    try:
        from tools.meta.observability.session_analyzer import build_report, summarize_report

        full = build_report(lens="all", store="both", last=last, limit=10)
        summary = summarize_report(full)
        return summary, {
            "status": "available",
            "command": f"./repo-python kernel.py --session-diagnostics --lens all --last {last} --store both --json --diagnostics-summary",
            "summary_bytes": _json_bytes(summary),
        }
    except Exception as exc:  # noqa: BLE001 - diagnostics are advisory
        return None, {
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
            "fallback": "fixture/policy route-event normalization only",
        }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _taco_pattern_repair_classes(pattern: Mapping[str, Any]) -> list[str]:
    haystack = " ".join(
        [
            str(pattern.get("name") or ""),
            str(pattern.get("one_liner") or ""),
            str(pattern.get("adoption_action") or ""),
            " ".join(_string_list(pattern.get("source_locus"))),
        ]
    ).lower()
    classes: list[str] = []
    if "complaint" in haystack or "over-compression" in haystack or "full output" in haystack:
        classes.append("route_event_overcompression_feedback")
    if "rule pool" in haystack or "global rule" in haystack or "two-timescale" in haystack:
        classes.append("navigation_compression_rule_pool")
    if "critical" in haystack or "exception" in haystack or "failure" in haystack:
        classes.append("critical_output_passthrough_guard")
    if "retention" in haystack or "convergence" in haystack or "top-k" in haystack:
        classes.append("compression_rule_convergence_metric")
    if not classes:
        classes.append("terminal_context_compression_rule")
    return classes


def _taco_ratchet_pattern_rows(patterns: Sequence[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pattern in patterns:
        if not isinstance(pattern, Mapping):
            continue
        local_targets = set(_string_list(pattern.get("local_target")))
        if not (local_targets & TACO_NAVIGATION_RATCHET_TARGETS):
            continue
        rows.append(
            {
                "pattern_id": str(pattern.get("id") or "").strip(),
                "name": str(pattern.get("name") or "").strip(),
                "axis": str(pattern.get("axis") or "").strip(),
                "adoption_status": str(pattern.get("adoption_status") or "").strip(),
                "repair_classes": _taco_pattern_repair_classes(pattern),
                "local_targets": sorted(local_targets & TACO_NAVIGATION_RATCHET_TARGETS),
            }
        )
    return rows


def _annex_intake_rows(repo_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    annex_root = repo_root / "annexes" / TACO_ANNEX
    distillation = _load_json(annex_root / "distillation.json")
    index = _load_json(annex_root / "annex_index.json")
    notes = _load_json(annex_root / "annex_notes.json")
    title = index.get("title") or "A Self-Evolving Framework for Efficient Terminal Agents via Observational Context Compression"
    status = distillation.get("distillation_status") or ("missing" if not distillation else "unknown")
    raw_patterns = distillation.get("patterns")
    patterns = raw_patterns if isinstance(raw_patterns, list) else []
    pattern_count = len(patterns) if isinstance(patterns, list) else 0
    note_count = len(notes.get("notes") or []) if isinstance(notes.get("notes"), list) else 0
    ratchet_patterns = _taco_ratchet_pattern_rows(patterns if isinstance(patterns, list) else [])
    ratchet_pattern_ids = [
        row["pattern_id"]
        for row in ratchet_patterns
        if row.get("pattern_id")
    ]
    repair_classes = sorted(
        {
            repair_class
            for row in ratchet_patterns
            for repair_class in row.get("repair_classes", [])
            if repair_class
        }
    )
    imported = status in {"partial", "complete"} and bool(ratchet_patterns)
    import_status = (
        "mapped"
        if imported
        else "candidate"
        if status == "placeholder" or pattern_count == 0
        else "ready_for_mapping"
    )
    intake = [
        {
            "annex_id": TACO_ANNEX,
            "title": title,
            "distillation_status": status,
            "pattern_count": pattern_count,
            "note_count": note_count,
            "local_mapping": {
                "terminal_observation": "kernel command output and agent route events",
                "rule_pool": "navigation_compression_rule_registry",
                "complaint_signal": "rerun/full-output request/hook correction/persisted-output",
            },
            "ratchet_mapped_pattern_count": len(ratchet_patterns),
            "ratchet_mapped_pattern_ids": ratchet_pattern_ids,
            "mapped_repair_classes": repair_classes,
            "candidate_repairs": [
                "record times_applied/times_complained for route compression rules",
                "promote route-specific compressors only after no over-compression complaints",
                "treat uncovered output and persisted-output as rule-evolution evidence",
            ],
            "import_status": import_status,
        }
    ]
    debt: list[dict[str, Any]] = []
    if not imported:
        debt.append(
            _debt_row(
                debt_id=f"annex:{TACO_ANNEX}:adaptive_terminal_compression_rules",
                debt_class="annex_import_debt",
                priority=76,
                title="TACO annex is indexed but not imported into the navigation ratchet",
                evidence=(
                    f"distillation_status={status}; patterns={pattern_count}; "
                    f"ratchet_mapped_patterns={len(ratchet_patterns)}; notes={note_count}"
                ),
                repair_class="annex_pattern_intake",
                target_files=[
                    f"annexes/{TACO_ANNEX}/distillation.json",
                    "system/lib/navigation_metabolism_ledger.py",
                ],
                tests=["annex intake row maps TACO-like compression patterns to route-event repair classes"],
                source_surface=f"annexes/{TACO_ANNEX}",
                extra={
                    "annex_id": TACO_ANNEX,
                    "import_status": intake[0]["import_status"],
                    "ratchet_mapped_pattern_count": len(ratchet_patterns),
                },
            )
        )
    return intake, debt


def _drop_argv(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _drop_argv(item) for key, item in value.items() if key != "argv"}
    if isinstance(value, list):
        return [_drop_argv(item) for item in value]
    return value


def _route_lifecycle_rows() -> list[dict[str, Any]]:
    navigation_lane = _drop_argv(navigation_enforcement_residual_lane())
    return [
        {
            "route_id": "context_pack",
            "status": "active",
            "purpose": "task-conditioned mixed-band first-contact packet",
            "superseded_by": None,
            "compatibility_behavior": None,
            "last_seen_in_agent_trace": None,
            "removal_condition": None,
        },
        {
            "route_id": "coverage_enforcement_matrix",
            "status": "active",
            "purpose": "per-kind coverage-first enforcement matrix over Kind Atlas, route lifecycle, hook shadow coverage, and process-audit pressure",
            "superseded_by": None,
            "compatibility_behavior": "read-only composer over existing surfaces; not a new registry or source authority",
            "last_seen_in_agent_trace": None,
            "removal_condition": "do not remove while coverage-first behavior still has observed process-audit pressure",
        },
        {
            "route_id": "phase_task_alignment",
            "status": "active",
            "purpose": "task-conditioned arbitration between an active phase primary wave and legal residual lanes",
            "superseded_by": None,
            "compatibility_behavior": "exposes navigation_enforcement as a residual lane inside the active phase instead of treating it as a phase exception",
            "residual_lanes": [navigation_lane],
            "owner_surfaces": navigation_lane.get("owner_surfaces"),
            "write_scope_policy": navigation_lane.get("write_scope_policy"),
            "write_guard": "residual selections block primary-wave live writes unless the classifier returns mixed_lane",
            "last_seen_in_agent_trace": None,
            "removal_condition": "do not remove while phase-scoped navigation repairs need residual-lane arbitration",
        },
        {
            "route_id": "navigation_surface_audit",
            "status": "active_input",
            "purpose": "projection size and contract-fit measurement",
            "superseded_by": "navigation_metabolism_ledger",
            "compatibility_behavior": "keep as a narrow input surface",
            "last_seen_in_agent_trace": None,
            "removal_condition": "do not remove; it remains the projection-debt provider",
        },
        {
            "route_id": "surface_authoring_audit",
            "status": "active_input",
            "purpose": "authored compression-rung debt provider",
            "superseded_by": "navigation_metabolism_ledger",
            "compatibility_behavior": "keep as a narrow input surface",
            "last_seen_in_agent_trace": None,
            "removal_condition": "do not remove; it remains the authoring-debt provider",
        },
        {
            "route_id": "paper_lattice",
            "status": "active_stable_slug_drilldown",
            "purpose": "source-derived paper-module lattice view for stable-slug doctrine exploration",
            "superseded_by": None,
            "supersedes": [
                "raw paper-module markdown as first-contact doctrine reading for selected stable slugs",
                "generated paper-module sidecar authority for source-derived lattice navigation",
            ],
            "supported_slug_source": "existing codex/doctrine/paper_modules/<slug>.md after context-pack or paper_modules row selection",
            "generic_existing_slug_support": True,
            "entry_condition": "stable paper-module slug already selected by context-pack or paper_modules cluster/card surface",
            "compatibility_behavior": "structured invalid_paper_module_slug or unknown_paper_module_slug for unselected or missing slugs",
            "last_seen_in_agent_trace": None,
            "removal_condition": "do not remove while stable-slug paper lattice is an active drilldown path",
        },
        {
            "route_id": "skill_find",
            "status": "active_typed_debug_trace",
            "purpose": "DEBUG_TRACE / exact-id drilldown for skill rows after a stable id or family is selected",
            "superseded_by": "--entry then --option-surface skills --band cluster_flag for first contact",
            "compatibility_behavior": (
                "surface_role enforced as DEBUG_TRACE; default output hides ranked matches; "
                "--debug returns ranked matches for exact-id audits; first_contact_allowed=False"
            ),
            "last_seen_in_agent_trace": None,
            "removal_condition": "do not retire; --skill-find <id> --debug remains the exact-id drilldown after a row is selected",
        },
        {
            "route_id": "clusterability_audit",
            "status": "active_input",
            "purpose": "high-cardinality grouping-key and cluster_flag decision surface",
            "superseded_by": "navigation_metabolism_ledger",
            "compatibility_behavior": "keep as a narrow input surface",
            "last_seen_in_agent_trace": None,
            "removal_condition": "do not remove; it remains the clusterability-debt provider",
        },
        {
            "route_id": "annex_routing_coverage",
            "status": "active_input",
            "purpose": "annex_patterns cluster-key coverage and unrouted bucket quality signal",
            "superseded_by": "navigation_metabolism_ledger",
            "compatibility_behavior": "keep as a narrow input surface after clusterability is satisfied",
            "last_seen_in_agent_trace": None,
            "removal_condition": "do not remove while annex_patterns uses fallback routing buckets",
        },
        {
            "route_id": "annex_currentness",
            "status": "active_input",
            "purpose": "annex sync digest currentness, upstream movement, stale-row, and attention-bucket signal",
            "superseded_by": "navigation_metabolism_ledger",
            "compatibility_behavior": "keep as a narrow read-only input; refresh remains owned by annex_import.py digest",
            "last_seen_in_agent_trace": None,
            "removal_condition": "do not remove while annex pattern transfer depends on live upstream movement checks",
        },
        {
            "route_id": "annex_movement_pressure_map",
            "status": "active_input",
            "purpose": (
                "read-only lane selector over mine_upstream_delta row jobs, annex sync reports, "
                "and owner-review blockers"
            ),
            "superseded_by": "navigation_metabolism_ledger",
            "compatibility_behavior": (
                "quality signal only; emits debt only when report evidence or classification coverage is missing; "
                "routes pre-mining source row-job blockers as owner_review_blocker rows"
            ),
            "last_seen_in_agent_trace": None,
            "removal_condition": "do not remove while annex movement review needs a no-source-mining throttle",
        },
        {
            "route_id": "annex_navigation_dogfood",
            "status": "active_input",
            "purpose": "self-use composer that proves annex navigation can route annex-improvement work from compressed surfaces",
            "superseded_by": "navigation_metabolism_ledger",
            "compatibility_behavior": "keep as a narrow read-only dogfood packet; do not merge it with refresh, routing, or cluster audits",
            "last_seen_in_agent_trace": None,
            "removal_condition": "do not remove while annex route changes require self-use closeout evidence",
        },
        {
            "route_id": "paper_modules.row_flag_all",
            "status": "compatibility_shim",
            "purpose": "legacy all-row paper-module flag browse",
            "superseded_by": "paper_modules.cluster_flag",
            "compatibility_behavior": "CLI redirects unless --ids is explicit",
            "last_seen_in_agent_trace": None,
            "removal_condition": "unsafe all-row library path has no consumers outside explicit audit fixtures",
        },
        {
            "route_id": "standards.row_flag_all",
            "status": "compatibility_shim",
            "purpose": "legacy all-row standards flag browse",
            "superseded_by": "standards.cluster_flag",
            "compatibility_behavior": "CLI redirects unless --ids is explicit",
            "last_seen_in_agent_trace": None,
            "removal_condition": "unsafe all-row library path has no consumers outside explicit audit fixtures",
        },
        {
            "route_id": "python_files.row_flag_all",
            "status": "compatibility_shim",
            "purpose": "legacy all-row Python file flag browse",
            "superseded_by": "python_files.cluster_flag",
            "compatibility_behavior": "CLI redirects unless --ids is explicit",
            "last_seen_in_agent_trace": None,
            "removal_condition": "unsafe all-row library path has no consumers outside explicit audit fixtures",
        },
        {
            "route_id": "python_scopes.row_flag_all",
            "status": "compatibility_shim",
            "purpose": "legacy all-row Python scope flag browse",
            "superseded_by": "python_scopes.cluster_flag",
            "compatibility_behavior": "CLI redirects unless --ids is explicit",
            "last_seen_in_agent_trace": None,
            "removal_condition": "unsafe all-row library path has no consumers outside explicit audit fixtures",
        },
        {
            "route_id": "frontend_components.row_flag_all",
            "status": "compatibility_shim",
            "purpose": "legacy all-row frontend component flag browse",
            "superseded_by": "frontend_components.cluster_flag",
            "compatibility_behavior": "CLI redirects unless --ids is explicit",
            "last_seen_in_agent_trace": None,
            "removal_condition": "unsafe all-row library path has no consumers outside explicit audit fixtures",
        },
        {
            "route_id": "principles.row_flag_all",
            "status": "compatibility_shim",
            "purpose": "legacy all-row principles flag browse",
            "superseded_by": "principles.cluster_flag",
            "compatibility_behavior": "CLI redirects unless --ids is explicit",
            "last_seen_in_agent_trace": None,
            "removal_condition": "unsafe all-row library path has no consumers outside explicit audit fixtures",
        },
        {
            "route_id": "annex_patterns.row_flag_all",
            "status": "compatibility_shim",
            "purpose": "legacy all-row annex pattern flag browse",
            "superseded_by": "annex_patterns.cluster_flag",
            "compatibility_behavior": "CLI redirects unless --ids is explicit",
            "last_seen_in_agent_trace": None,
            "removal_condition": "unsafe all-row library path has no consumers outside explicit audit fixtures",
        },
        {
            "route_id": "annex_distillation_patterns.row_flag_all",
            "status": "compatibility_shim",
            "purpose": "legacy all-row annex distillation pattern flag browse",
            "superseded_by": "annex_distillation_patterns.cluster_flag",
            "compatibility_behavior": "CLI redirects unless --ids is explicit",
            "last_seen_in_agent_trace": None,
            "removal_condition": "unsafe all-row library path has no consumers outside explicit audit fixtures",
        },
        {
            "route_id": "phase.summary_default",
            "status": "active",
            "purpose": "default phase reentry control packet",
            "superseded_by": None,
            "compatibility_behavior": "quick metabolism samples the bounded summary packet; full evidence remains behind --full",
            "last_seen_in_agent_trace": None,
            "removal_condition": "projection debt reappears only if the sampled summary packet violates its bounded-entry contract",
        },
        {
            "route_id": "navigation_context_rosetta",
            "status": "active_reference",
            "purpose": "budget and grammar reference surface",
            "superseded_by": "context_pack for first-contact task routing",
            "compatibility_behavior": "open when changing the math/grammar, not for ordinary task entry",
            "last_seen_in_agent_trace": None,
            "removal_condition": "only after its grammar is fully embedded in executable standards and tests",
        },
        {
            "route_id": "codex.model_instructions_file",
            "status": "experimental_high_blast",
            "purpose": "controlled Codex worker harness instruction-profile override, not normal repo bootstrap",
            "superseded_by": "AGENTS.override.md + workspace skills + hooks for ordinary entrypoint behavior",
            "compatibility_behavior": "documented as deliberate experiment-only control surface",
            "last_seen_in_agent_trace": None,
            "removal_condition": "keep documented if Codex worker experiments rely on it; never promote to default bootstrap",
        },
    ]


def build_route_lifecycle_summary(route_ids: Sequence[str] | None = None) -> list[dict[str, Any]]:
    """Return a compact public route-lifecycle view for downstream composers."""
    selected = {str(route_id) for route_id in route_ids or [] if str(route_id).strip()}
    rows: list[dict[str, Any]] = []
    for row in _route_lifecycle_rows():
        route_id = str(row.get("route_id") or "")
        if selected and route_id not in selected:
            continue
        summary = {
            "route_id": route_id,
            "status": row.get("status"),
            "purpose": row.get("purpose"),
        }
        for key in ("write_guard", "owner_surfaces", "residual_lanes", "superseded_by"):
            if row.get(key) not in (None, [], ""):
                summary[key] = row.get(key)
        rows.append(summary)
    return rows


def _layer_sprawl_rows(route_lifecycle: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for route in route_lifecycle:
        status = str(route.get("status") or "")
        watched_statuses = {"compatibility_shim", "active_with_projection_watch", "active_reference"}
        if status not in watched_statuses:
            continue
        required_fields = ["compatibility_behavior", "removal_condition"]
        if status in {"compatibility_shim", "active_reference"}:
            required_fields.insert(0, "superseded_by")
        missing_fields = [
            field
            for field in required_fields
            if route.get(field) in (None, "", [])
        ]
        if not missing_fields:
            continue
        route_id = str(route.get("route_id") or "unknown")
        rows.append(
            _debt_row(
                debt_id=f"layer_sprawl:{route_id}",
                debt_class="layer_sprawl_debt",
                priority=64 if status == "compatibility_shim" else 52,
                title=f"{route_id} is missing explicit lifecycle handling",
                evidence=(
                    f"status={status}; missing_lifecycle_fields={missing_fields}; "
                    f"superseded_by={route.get('superseded_by')}"
                ),
                repair_class="route_lifecycle_metadata_or_deprecation_guard",
                target_files=["system/lib/navigation_metabolism_ledger.py", "system/lib/kernel/commands/navigate.py"],
                tests=["route lifecycle rows preserve superseded_by and removal_condition for compatibility routes"],
                source_surface="navigation_metabolism_ledger.route_lifecycle",
                route_id=route_id,
                extra={
                    "status": status,
                    "superseded_by": route.get("superseded_by"),
                    "removal_condition": route.get("removal_condition"),
                    "missing_lifecycle_fields": missing_fields,
                },
            )
        )
    return rows


_QUICK_PAPER_MODULE_AUTHORING_TARGETS: tuple[tuple[str, int], ...] = (
    ("navigation_rosetta_math", 80),
    ("holographic_navigation_compression", 78),
)


def _paper_module_compression_record(root: Path, artifact_id: str) -> Mapping[str, Any]:
    index = _load_json(root / "codex" / "doctrine" / "paper_modules" / "_index.json")
    for module in index.get("modules") or []:
        if isinstance(module, Mapping) and module.get("slug") == artifact_id:
            compression = module.get("compression")
            return compression if isinstance(compression, Mapping) else {}
    return {}


def _quick_authoring_debt_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for artifact_id, priority in _QUICK_PAPER_MODULE_AUTHORING_TARGETS:
        compression = _paper_module_compression_record(root, artifact_id)
        compression_status = str(compression.get("compression_status") or "unknown")
        findings = compression.get("findings") if isinstance(compression.get("findings"), list) else []
        if compression_status == "authored" and not findings:
            continue
        rows.append(
            _debt_row(
                debt_id=f"authoring:paper_modules:{artifact_id}",
                debt_class="authoring_debt",
                priority=priority,
                title=f"paper_modules.{artifact_id} lacks authored compressed rungs",
                evidence=(
                    "quick profile priority set checked paper-module index; "
                    f"compression_status={compression_status}; findings={findings}"
                ),
                repair_class="compression_frontmatter_migration",
                target_files=[f"codex/doctrine/paper_modules/{artifact_id}.md"],
                tests=[
                    "paper-module index reports compression_status=authored with no compression findings",
                    "surface-authoring-audit reports no missing compressed rungs for this artifact",
                ],
                source_surface="navigation_metabolism.quick_profile",
                artifact_kind="paper_modules",
                artifact_id=artifact_id,
                extra={
                    "compression_status": compression_status,
                    "compression_findings": findings,
                },
            )
        )
    return rows


PHASE_SUMMARY_BOUNDED_PACKET_BUDGET_TOKENS = 12000
PHASE_SUMMARY_SAFE_ALTERNATIVE = "./repo-python kernel.py --phase --warnings-only"


def _normalize_phase_summary_projection_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    status = dict(payload)
    if status.get("status") == "deferred_by_quick_profile":
        status.setdefault("safe_alternative", PHASE_SUMMARY_SAFE_ALTERNATIVE)
        status.setdefault(
            "reason",
            "phase summary sample is cached/stale in quick profile; run --phase --warnings-only or command-profile for active phase timing",
        )
    return status


def _phase_summary_projection_status(root: Path, *, context_budget: int) -> dict[str, Any]:
    budget_bytes = PHASE_SUMMARY_BOUNDED_PACKET_BUDGET_TOKENS * 4
    try:
        from system.lib.kernel.commands import navigate as _navigate

        try:
            _navigate.state.init(root)
        except Exception:
            pass
        result = _navigate.KernelNavigation(_navigate.state.REPO_ROOT).build_phase(None)
        payload = _navigate._phase_output_mode_packet(result, output_mode="summary")
    except Exception as exc:  # noqa: BLE001 - quick metabolism should keep running
        return {
            "route_id": "phase.summary_default",
            "status": "sample_error",
            "error": f"{type(exc).__name__}: {exc}",
            "contract_status": "sample_error",
            "safe_alternative": PHASE_SUMMARY_SAFE_ALTERNATIVE,
        }

    byte_count = _json_bytes(payload)
    relation = (
        "exceeds_context_budget"
        if byte_count > budget_bytes
        else "large_but_within_budget"
        if byte_count > int(budget_bytes * 0.6)
        else "within_budget"
    )
    payload_body = payload.get("payload") if isinstance(payload.get("payload"), Mapping) else {}
    omitted_sections = payload_body.get("omitted_sections")
    full_payload_hint = payload_body.get("full_payload_hint")
    omitted_long_sections = any(
        key in payload_body
        for key in (
            "phase_card",
            "family",
            "recovery_map",
            "active_synth",
            "derived_index",
            "plan_context",
            "observe_authoring",
            "manifest",
            "closeout",
        )
    )
    drilldown_present = isinstance(full_payload_hint, Mapping) and bool(full_payload_hint.get("command"))
    omission_receipt_present = isinstance(omitted_sections, list) and bool(omitted_sections)
    contract_status = (
        "valid"
        if relation != "exceeds_context_budget"
        and drilldown_present
        and omission_receipt_present
        and not omitted_long_sections
        else "violates_entry_contract"
    )
    return {
        "route_id": "phase.summary_default",
        "status": "retired_from_quick_debt" if contract_status == "valid" else "active_watch",
        "pretty_json_bytes": byte_count,
        "budget_bytes": budget_bytes,
        "budget_relation": relation,
        "contract_status": contract_status,
        "drilldown_present": drilldown_present,
        "omission_receipt_present": omission_receipt_present,
        "omitted_long_sections": omitted_long_sections,
        "safe_alternative": PHASE_SUMMARY_SAFE_ALTERNATIVE,
    }


def _cached_phase_summary_projection_status(
    root: Path,
    *,
    context_budget: int,
    allow_build: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    kwargs = {
        "node_id": "navigation_metabolism.phase_summary_projection_status.quick",
        "key": {"context_budget": max(1000, int(context_budget or 12000))},
        "freshness_policy": "ttl_for_phase_state_plus_static_source_manifest",
        "dynamic_inputs_manifested": False,
    }
    if not allow_build:
        payload, status = peek_cached_command_node(root, **kwargs)
        if payload is None:
            return {
                "route_id": "phase.summary_default",
                "status": "deferred_by_quick_profile",
                "contract_status": "deferred_by_quick_profile",
                "safe_alternative": PHASE_SUMMARY_SAFE_ALTERNATIVE,
                "reason": "phase summary sample is cached/stale in quick profile; run --phase --warnings-only or command-profile for active phase timing",
            }, status
        return (
            _normalize_phase_summary_projection_status(payload)
            if isinstance(payload, Mapping)
            else {"status": "sample_error"}
        ), status
    payload, status = cached_command_node(
        root,
        node_id=kwargs["node_id"],
        key=kwargs["key"],
        input_paths=[
            "kernel.py",
            "system/lib/kernel/commands/navigate.py",
            "system/lib/navigation_metabolism_ledger.py",
        ],
        ttl_s=QUICK_COMMAND_CACHE_TTL_SECONDS,
        builder=lambda: _phase_summary_projection_status(root, context_budget=context_budget),
        freshness_policy=kwargs["freshness_policy"],
        dynamic_inputs_manifested=kwargs["dynamic_inputs_manifested"],
    )
    return (
        _normalize_phase_summary_projection_status(payload)
        if isinstance(payload, Mapping)
        else {"status": "sample_error"}
    ), status


def _quick_projection_debt_rows(phase_summary_status: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = [
        _debt_row(
            debt_id="projection:paper_modules.row_flag_all.library",
            debt_class="projection_debt",
            priority=90,
            title="paper_modules row_flag_all library reference remains unsafe; CLI redirects to cluster_flag",
            evidence=(
                "quick profile tracks the library-only high-cardinality flag reference; "
                "the CLI compatibility path must redirect all-row flag calls to cluster_flag unless --ids is explicit"
            ),
            repair_class="projection_contract_repair",
            target_files=["system/lib/kernel/commands/navigate.py", "system/lib/standard_option_surface.py"],
            tests=[
                "paper_modules global first contact uses cluster_flag before row expansion",
                "quick profile debt text distinguishes library-only unsafe references from live CLI regressions",
            ],
            source_surface="navigation_metabolism.quick_profile",
            route_id="paper_modules.row_flag_all.library",
            extra={
                "safe_alternative": "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
                "compatibility_behavior": "CLI redirects all-row flag calls to cluster_flag unless --ids is explicit",
                "library_reference_only": True,
                "active_debt": False,
                "advisory_only": True,
            },
        ),
    ]
    status = dict(phase_summary_status or {})
    if status.get("contract_status") == "deferred_by_quick_profile":
        return rows
    if status.get("contract_status") != "valid":
        rows.append(
            _debt_row(
                debt_id="projection:phase.summary_default",
                debt_class="projection_debt",
                priority=88,
                title="phase.summary_default violates its bounded control-packet contract",
                evidence=(
                    f"contract_status={status.get('contract_status') or 'unknown'}; "
                    f"budget_relation={status.get('budget_relation') or 'unknown'}; "
                    f"bytes={status.get('pretty_json_bytes') or 'unknown'}; "
                    f"drilldown_present={status.get('drilldown_present')}"
                ),
                repair_class="bounded_entry_packet_rewrite",
                target_files=["system/lib/kernel/commands/navigate.py"],
                tests=["phase summary contains no long evidence/source path lists"],
                source_surface="navigation_metabolism.quick_profile",
                route_id="phase.summary_default",
                extra={
                    "safe_alternative": status.get("safe_alternative")
                    or "./repo-python kernel.py --phase --warnings-only",
                    "contract_status": status.get("contract_status"),
                    "budget_relation": status.get("budget_relation"),
                },
            )
        )
    return rows


_ROUTING_SOURCE_COUPLING_TITLES: dict[str, str] = {
    "artifact_matches_dirty_source_inputs": (
        "routing_hologram matches the worktree renderer but is coupled to dirty source inputs"
    ),
    "dirty_source_inputs_and_artifact_drift": (
        "routing_hologram drifts from the worktree renderer and source inputs are dirty"
    ),
    "artifact_drift_from_clean_sources": (
        "routing_hologram drifts from the worktree renderer with clean source inputs"
    ),
    "source_state_unavailable": (
        "routing_hologram source-coupling state is unavailable; rerun the projection check"
    ),
}


def _routing_source_coupling_debt_rows(routing_projection_status: Mapping[str, Any]) -> list[dict[str, Any]]:
    if routing_projection_status.get("status") == "deferred_by_quick_profile":
        return []
    source_coupling = routing_projection_status.get("source_coupling")
    if not isinstance(source_coupling, Mapping):
        return []
    if source_coupling.get("status") == "deferred_by_quick_profile":
        return []
    if source_coupling.get("safe_to_commit_generated_outputs_without_sources") is True:
        return []
    status = str(source_coupling.get("status") or "").strip()
    if not status or status == "clean_source_inputs_and_artifacts":
        return []

    dirty_source_paths = [
        str(path)
        for path in (source_coupling.get("dirty_source_paths") or [])
        if str(path).strip()
    ]
    evidence_bits = [f"source_coupling_status={status}"]
    if dirty_source_paths:
        evidence_bits.append(f"dirty_source_paths={dirty_source_paths[:6]}")
    reason = str(source_coupling.get("reason") or "").strip()
    if reason:
        evidence_bits.append(reason)

    title = _ROUTING_SOURCE_COUPLING_TITLES.get(
        status,
        f"routing_hologram source-coupling status {status} requires repair",
    )

    return [
        _debt_row(
            debt_id="projection:routing_hologram.source_coupling",
            debt_class="projection_debt",
            priority=94,
            title=title,
            evidence="; ".join(evidence_bits),
            repair_class="projection_source_coupling_landing",
            target_files=[
                "system/lib/routing_projection.py",
                "tools/meta/factory/build_routing_projection.py",
                "codex/doctrine/routing_hologram.json",
                "AGENTS.md",
                *dirty_source_paths[:4],
            ],
            tests=[
                "kernel.py --routing reports clean_source_inputs_and_artifacts, or generated routing targets are excluded from the scoped landing",
                "build_routing_projection.py --check prints source-coupling status when source inputs are dirty",
            ],
            source_surface="kernel.py --routing",
            route_id="routing_hologram",
            extra={
                "source_coupling_status": status,
                "dirty_source_paths": dirty_source_paths,
                "safe_to_commit_generated_outputs_without_sources": False,
                "artifact_path": routing_projection_status.get("artifact_path"),
                "check_command": routing_projection_status.get("check_command"),
                "refresh_command": routing_projection_status.get("refresh_command"),
            },
        )
    ]


def _cached_routing_projection_status(
    root: Path,
    *,
    allow_build: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    kwargs = {
        "node_id": "navigation_metabolism.routing_projection_status.quick",
        "key": {"scope": "quick", "builder": "routing_projection_status"},
        "freshness_policy": "ttl_for_routing_projection_status_plus_static_manifest_and_git_state",
        "dynamic_inputs_manifested": False,
    }
    if not allow_build:
        payload, status = peek_cached_command_node(
            root,
            **kwargs,
            input_paths=_ROUTING_STATUS_CACHE_INPUT_PATHS,
            ttl_s=QUICK_COMMAND_CACHE_TTL_SECONDS,
        )
        if payload is None:
            return {
                "status": "deferred_by_quick_profile",
                "stale": None,
                "artifact_path": "codex/doctrine/routing_hologram.json",
                "source_coupling": {
                    "status": "deferred_by_quick_profile",
                    "safe_to_commit_generated_outputs_without_sources": False,
                },
                "safe_alternative": "./repo-python kernel.py --routing-check",
                "reason": (
                    "routing projection status cache is missing, stale, or expired; "
                    "quick metabolism does not rebuild the projection renderer or git coupling check"
                ),
            }, status
        return dict(payload) if isinstance(payload, Mapping) else {"status": "unavailable"}, status
    payload, status = cached_command_node(
        root,
        node_id=kwargs["node_id"],
        key=kwargs["key"],
        input_paths=_ROUTING_STATUS_CACHE_INPUT_PATHS,
        ttl_s=QUICK_COMMAND_CACHE_TTL_SECONDS,
        builder=lambda: routing_status(root),
        freshness_policy=kwargs["freshness_policy"],
        dynamic_inputs_manifested=kwargs["dynamic_inputs_manifested"],
    )
    return dict(payload) if isinstance(payload, Mapping) else {"status": "unavailable"}, status


def _process_audit_payload(root: Path) -> dict[str, Any]:
    """Build the live agent-execution-trace audit + summary, lazily and tolerantly.

    The metabolism ratchet treats agent path observation as `behavior_debt`
    input (Sentrux p001 sensor loop). The substrate is the same JSONL the
    `--process-audit` kernel command reads; this helper imports the live
    builder without going through the CLI so the ledger composes one packet.
    """
    try:
        from system.lib.agent_execution_trace import build_agent_execution_trace

        payload = build_agent_execution_trace(repo_root=root)
        if not isinstance(payload, Mapping):
            return {"status": "unavailable", "error": "non_mapping_payload"}
        audit = dict(payload.get("audit") or {})
        summary = audit.get("summary") if isinstance(audit.get("summary"), Mapping) else {}
        bottlenecks = audit.get("bottlenecks") if isinstance(audit.get("bottlenecks"), Mapping) else {}
        patterns = list(audit.get("patterns") or [])
        findings = list(audit.get("findings") or [])
        return {
            "status": "available",
            "audit": audit,
            "summary": dict(summary),
            "bottlenecks": dict(bottlenecks),
            "patterns": patterns,
            "findings": findings,
            "session_count": int(summary.get("session_count") or 0),
        }
    except Exception as exc:  # noqa: BLE001 - audit is advisory input
        return {"status": "unavailable", "error": f"{type(exc).__name__}: {exc}"}


def _cached_process_audit_payload(root: Path, *, allow_build: bool = True) -> tuple[dict[str, Any], dict[str, Any]]:
    kwargs = {
        "node_id": "navigation_metabolism.process_audit.quick",
        "key": {"scope": "quick", "builder": "agent_execution_trace"},
        "freshness_policy": "ttl_for_dynamic_session_state_plus_static_source_manifest",
        "dynamic_inputs_manifested": False,
    }
    if not allow_build:
        payload, status = peek_cached_command_node(root, **kwargs)
        if payload is None:
            return {
                "status": "deferred_by_quick_profile",
                "reason": "process-audit cache missing or unavailable; quick metabolism does not rebuild expensive session traces",
                "session_count": 0,
                "summary": {},
                "patterns": [],
                "findings": [],
            }, status
        return dict(payload) if isinstance(payload, Mapping) else {"status": "unavailable"}, status
    payload, status = cached_command_node(
        root,
        node_id=kwargs["node_id"],
        key=kwargs["key"],
        input_paths=[
            "system/lib/agent_execution_trace.py",
            "system/lib/navigation_metabolism_ledger.py",
        ],
        ttl_s=QUICK_COMMAND_CACHE_TTL_SECONDS,
        builder=lambda: _process_audit_payload(root),
        freshness_policy=kwargs["freshness_policy"],
        dynamic_inputs_manifested=kwargs["dynamic_inputs_manifested"],
    )
    return dict(payload) if isinstance(payload, Mapping) else {"status": "unavailable"}, status


def _process_audit_quick_key(process_audit: Mapping[str, Any]) -> dict[str, Any]:
    summary = process_audit.get("summary") if isinstance(process_audit.get("summary"), Mapping) else {}
    patterns = [
        {
            "pattern_id": str(row.get("pattern_id") or ""),
            "instances": int(row.get("instances") or 0),
            "severity": str(row.get("severity") or ""),
        }
        for row in process_audit.get("patterns") or []
        if isinstance(row, Mapping)
    ]
    return {
        "scope": "quick",
        "session_count": int(process_audit.get("session_count") or summary.get("session_count") or 0),
        "finding_count": int(summary.get("finding_count") or 0),
        "pattern_counts": _process_pattern_counts(process_audit),
        "top_patterns": patterns[:8],
    }


def _process_pattern_counts(process_audit: Mapping[str, Any]) -> dict[str, int]:
    summary = process_audit.get("summary") if isinstance(process_audit.get("summary"), Mapping) else {}
    pattern_counts = summary.get("pattern_counts") if isinstance(summary.get("pattern_counts"), Mapping) else {}
    if pattern_counts:
        return {str(key): int(value or 0) for key, value in pattern_counts.items()}
    counts: dict[str, int] = {}
    for pattern in process_audit.get("patterns") or []:
        if isinstance(pattern, Mapping) and pattern.get("pattern_id"):
            counts[str(pattern["pattern_id"])] = int(pattern.get("instances") or 0)
    return counts


def _process_audit_cache_authority(cache_status: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(cache_status, Mapping):
        return {}
    status = str(cache_status.get("status") or "")
    age_s_raw = cache_status.get("age_s")
    ttl_s_raw = cache_status.get("ttl_s")
    try:
        age_s = float(age_s_raw)
    except (TypeError, ValueError):
        age_s = None
    try:
        ttl_s = float(ttl_s_raw)
    except (TypeError, ValueError):
        ttl_s = None
    stale_by_age = age_s is not None and ttl_s is not None and ttl_s > 0 and age_s > ttl_s
    stale_by_status = status in {"stale_ok_hit", "deferred_stale_cache"}
    authority_status = "advisory_only_stale_read_model" if stale_by_age or stale_by_status else "current_cached_read_model"
    return {
        "status": authority_status,
        "cache_status": status,
        "age_s": round(age_s, 3) if age_s is not None else None,
        "ttl_s": round(ttl_s, 3) if ttl_s is not None else None,
        "patch_selection_policy": (
            "refresh_before_selecting_process_audit_source_patch"
            if authority_status == "advisory_only_stale_read_model"
            else "cached_read_model_ok_for_process_audit_patch_selection"
        ),
        "authoritative_decision_command": "./repo-python kernel.py --process-bottlenecks --force",
        "refresh_command": (
            "AIW_COMMAND_CACHE_REFRESH=1 ./repo-python kernel.py --navigation-metabolism "
            '"<task>" --metabolism-profile quick --context-budget 12000'
        ),
    }


def _annotate_process_audit_source_freshness(
    rows: Sequence[Mapping[str, Any]],
    cache_status: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    authority = _process_audit_cache_authority(cache_status)
    if not authority:
        return [dict(row) for row in rows]
    annotated: list[dict[str, Any]] = []
    for row in rows:
        next_row = dict(row)
        if str(next_row.get("source_surface") or "") == "--process-audit":
            next_row["source_freshness"] = dict(authority)
            boundary = dict(next_row.get("source_projection_boundary") or {})
            boundary["process_audit_cache_policy"] = authority["patch_selection_policy"]
            boundary["process_audit_refresh_route"] = authority["refresh_command"]
            next_row["source_projection_boundary"] = boundary
            if authority.get("status") == "advisory_only_stale_read_model":
                next_row["active_debt"] = False
                next_row["advisory_only"] = True
                next_row["active_debt_demoted_by"] = "stale_process_audit_read_model"
        annotated.append(next_row)
    return annotated


def _observed_navigation_mechanism_claims(
    navigation_mechanism_metabolism: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    """Return anti-pattern ids whose mechanism has observed post-projection evidence."""
    observed_ids = {
        str(value)
        for value in (navigation_mechanism_metabolism.get("observed_anti_pattern_ids") or [])
        if value
    }
    observed: dict[str, Mapping[str, Any]] = {}
    claim_sources = list(navigation_mechanism_metabolism.get("observed_claim_refs") or [])
    claim_sources.extend(list(navigation_mechanism_metabolism.get("top_candidate_claims") or []))
    for claim in claim_sources:
        if not isinstance(claim, Mapping):
            continue
        anti_pattern_id = str(claim.get("anti_pattern_id") or "")
        if not anti_pattern_id:
            continue
        future_observation = (
            claim.get("future_observation")
            if isinstance(claim.get("future_observation"), Mapping)
            else {}
        )
        claim_observed = (
            anti_pattern_id in observed_ids
            or str(claim.get("state") or "") == "observed"
            or str(claim.get("latest_acceptance_event_type") or "") == "observation.recorded"
            or str(future_observation.get("status") or "") == "observed"
        )
        if claim_observed:
            observed_ids.add(anti_pattern_id)
            observed[anti_pattern_id] = claim
    for anti_pattern_id in observed_ids:
        observed.setdefault(anti_pattern_id, {})
    return observed


def _observed_navigation_mechanism_claim_refs(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build a compact stable index for observed claims beyond the budget-trimmed top list."""
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        future_observation = (
            row.get("future_observation") if isinstance(row.get("future_observation"), Mapping) else {}
        )
        if str(row.get("state") or "") != "observed" and str(future_observation.get("status") or "") != "observed":
            continue
        claim_id = str(row.get("claim_id") or "")
        anti_pattern_id = str(row.get("anti_pattern_id") or "")
        key = claim_id or anti_pattern_id
        if not key or key in seen:
            continue
        seen.add(key)
        refs.append(
            {
                "claim_id": claim_id,
                "anti_pattern_id": anti_pattern_id,
                "debt_id": f"behavior:process_audit:{anti_pattern_id}" if anti_pattern_id else None,
                "state": row.get("state"),
                "acceptance_event_ref": row.get("acceptance_event_ref"),
                "acceptance_dossier_id": row.get("acceptance_dossier_id"),
                "owner_acceptance_status": row.get("owner_acceptance_status"),
                "future_observation": {
                    "status": future_observation.get("status"),
                    "baseline_count": future_observation.get("baseline_count"),
                    "post_count": future_observation.get("post_count"),
                },
                "drilldown_command": row.get("drilldown_command"),
            }
        )
    return refs


def _retire_observed_navigation_mechanism_debt_rows(
    rows: Sequence[Mapping[str, Any]],
    navigation_mechanism_metabolism: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Demote process-audit debt rows once a matching mechanism is observed.

    Process-audit evidence remains visible as an advisory row, but the repair
    chooser should not keep selecting a route mechanism whose future
    observation window has already been recorded.
    """
    observed_claims = _observed_navigation_mechanism_claims(navigation_mechanism_metabolism)
    retired_ids: list[str] = []
    next_rows: list[dict[str, Any]] = []
    for row in rows:
        mutable = dict(row)
        anti_pattern_id = str(mutable.get("anti_pattern_id") or "")
        if (
            mutable.get("debt_class") == "behavior_debt"
            and mutable.get("source_surface") == "--process-audit"
            and anti_pattern_id in observed_claims
        ):
            claim = observed_claims.get(anti_pattern_id) or {}
            mutable.update(
                {
                    "active_debt": False,
                    "advisory_only": True,
                    "retired_by_navigation_mechanism_observation": True,
                    "retirement_reason": (
                        "A matching navigation mechanism has observation.recorded evidence; "
                        "the process-audit row remains evidence but no longer competes as an active repair."
                    ),
                    "navigation_mechanism_claim_id": claim.get("claim_id"),
                    "navigation_mechanism_acceptance_event_ref": claim.get("acceptance_event_ref"),
                    "navigation_mechanism_future_observation": claim.get("future_observation"),
                }
            )
            retired_ids.append(str(mutable.get("debt_id") or anti_pattern_id))
        next_rows.append(mutable)
    return next_rows, {
        "status": "applied" if retired_ids else "no_matching_observed_mechanism_debt",
        "observed_anti_pattern_ids": sorted(observed_claims),
        "observed_anti_pattern_count": len(observed_claims),
        "retired_debt_count": len(retired_ids),
        "retired_debt_ids": retired_ids,
        "active_debt_policy": (
            "Recorded observation retires the matching process-audit anti-pattern from active "
            "behavior_debt/top_repairs while preserving it as advisory evidence until a later "
            "regression event reopens it."
        ),
        "authority": "codex/standards/std_navigation_mechanism_acceptance.json::observed_state_requires",
    }


def _navigation_mechanism_metabolism(root: Path, process_audit: Mapping[str, Any]) -> dict[str, Any]:
    """Summarize route-learning candidate posture for the metabolism ledger.

    This keeps the full candidate option surface separate while making its
    acceptance blockers visible in the main route-quality ratchet.
    """
    try:
        from system.lib.navigation_mechanism_factory import (
            build_navigation_mechanism_projection,
            load_navigation_mechanism_acceptance_dossiers,
            load_navigation_mechanism_acceptance_events,
            load_navigation_mechanism_owner_loci,
            load_navigation_mechanism_owner_packets,
            load_navigation_mechanism_replay_receipts,
            validate_navigation_mechanism_projection,
        )

        trace_payload = {
            "audit": {
                "patterns": list(process_audit.get("patterns") or []),
            },
            "ledger": {"sessions": []},
            "spans_by_session": {},
        }
        projection = build_navigation_mechanism_projection(
            root,
            event_limit=0,
            trace_payload=trace_payload,
        )
        validation = validate_navigation_mechanism_projection(projection, repo_root=root)
        acceptance_dossiers = {
            str(row.get("claim_id")): row
            for row in load_navigation_mechanism_acceptance_dossiers(root)
            if isinstance(row, Mapping) and row.get("claim_id")
        }
        acceptance_events = {
            str(row.get("claim_id")): row
            for row in load_navigation_mechanism_acceptance_events(root)
            if isinstance(row, Mapping) and row.get("claim_id")
        }
        owner_packets = {
            str(row.get("claim_id")): row
            for row in load_navigation_mechanism_owner_packets(root)
            if isinstance(row, Mapping) and row.get("claim_id")
        }
        owner_loci = {
            str(row.get("claim_id")): row
            for row in load_navigation_mechanism_owner_loci(root)
            if isinstance(row, Mapping) and row.get("claim_id")
        }
        replay_receipts = {
            str(row.get("claim_id")): row
            for row in load_navigation_mechanism_replay_receipts(root)
            if isinstance(row, Mapping) and row.get("claim_id")
        }
    except Exception as exc:  # noqa: BLE001 - advisory metabolism input
        return {
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
            "candidate_count": 0,
            "validated_count": 0,
            "accepted_count": 0,
            "projected_count": 0,
            "observed_count": 0,
            "observed_claim_refs": [],
            "top_candidate_claims": [],
        }

    claims = [row for row in projection.get("projection_claims") or [] if isinstance(row, Mapping)]
    replay_results = [
        row for row in projection.get("route_replay_results") or [] if isinstance(row, Mapping)
    ]
    replay_by_claim = {
        str(row.get("source_claim_id")): row
        for row in replay_results
        if row.get("source_claim_id")
    }
    pattern_counts = _process_pattern_counts(process_audit)

    candidate_count = len(claims)
    validated_count = 0
    accepted_count = 0
    projected_count = 0
    observed_count = 0
    observed_anti_pattern_ids: set[str] = set()
    owner_blockers: dict[str, int] = {}
    top_rows: list[dict[str, Any]] = []
    for claim in claims:
        claim_id = str(claim.get("claim_id") or "")
        payload = claim.get("payload") if isinstance(claim.get("payload"), Mapping) else {}
        route_repair = payload.get("route_repair") if isinstance(payload.get("route_repair"), Mapping) else {}
        anti_pattern_id = str(route_repair.get("anti_pattern_id") or "")
        repair_class = str(route_repair.get("repair_class") or "")
        owner_target = payload.get("owner_target") if isinstance(payload.get("owner_target"), Mapping) else {}
        next_owner_surface = str(owner_target.get("next_owner_surface") or "navigation_metabolism")
        owner_blockers[next_owner_surface] = owner_blockers.get(next_owner_surface, 0) + 1
        replay = replay_by_claim.get(claim_id) or {}
        replay_passed = bool(replay.get("passed") is True)
        validation_status = "valid" if validation.get("ok") and replay_passed else "invalid"
        if validation_status == "valid":
            validated_count += 1
        dossier = acceptance_dossiers.get(claim_id) or {}
        acceptance_event = acceptance_events.get(claim_id) or {}
        owner_packet = owner_packets.get(claim_id) or {}
        owner_locus = owner_loci.get(claim_id) or {}
        replay_receipt = replay_receipts.get(claim_id) or {}
        dossier_projection = (
            dossier.get("read_model_projection")
            if isinstance(dossier.get("read_model_projection"), Mapping)
            else {}
        )
        acceptance_event_ref = (
            f"navigation_mechanism_acceptance_event:{acceptance_event.get('event_id')}"
            if acceptance_event.get("event_id")
            else None
        )
        owner_packet_ref = (
            f"navigation_mechanism_owner_packet:{owner_packet.get('packet_id')}"
            if owner_packet.get("packet_id")
            else None
        )
        owner_locus_ref = (
            f"navigation_mechanism_owner_locus_verification:{owner_locus.get('verification_id')}"
            if owner_locus.get("verification_id")
            else None
        )
        replay_receipt_ref = (
            f"navigation_mechanism_replay_receipt:{replay_receipt.get('receipt_id')}"
            if replay_receipt.get("receipt_id")
            else dossier_projection.get("replay_receipt_ref")
        )
        if claim.get("state") == "accepted" or dossier.get("acceptance_eligibility") == "accepted":
            accepted_count += 1
        if dossier.get("projection_ref"):
            projected_count += 1
        future_observation = (
            dossier.get("future_observation")
            if isinstance(dossier.get("future_observation"), Mapping)
            else {}
        )
        if future_observation.get("status") == "observed":
            observed_count += 1
            if anti_pattern_id:
                observed_anti_pattern_ids.add(anti_pattern_id)
        acceptance_eligibility = str(dossier.get("acceptance_eligibility") or "blocked")
        owner_acceptance_status = (
            "accepted"
            if acceptance_eligibility == "accepted"
            else str(owner_target.get("owner_acceptance_status") or "missing")
        )
        baseline_count = int(pattern_counts.get(anti_pattern_id, payload.get("observed_instances") or 0) or 0)
        top_rows.append(
            {
                "claim_id": claim_id,
                "anti_pattern_id": anti_pattern_id,
                "repair_class": repair_class,
                "observed_instances": int(payload.get("observed_instances") or 0),
                "replay_status": "passed" if replay_passed else "missing_or_failed",
                "validation_status": validation_status,
                "owner_acceptance_status": owner_acceptance_status,
                "state": acceptance_event.get("state_after") or dossier.get("state") or claim.get("state"),
                "claim_state": claim.get("state"),
                "latest_acceptance_event_type": acceptance_event.get("event_type"),
                "acceptance_event_ref": acceptance_event_ref,
                "previous_acceptance_event_ref": acceptance_event.get("previous_event_ref"),
                "blocked_event_ref": (
                    dossier_projection.get("blocked_event_ref")
                    or (
                        acceptance_event.get("previous_event_ref")
                        if acceptance_event.get("event_type") == "owner_packet.created"
                        else (
                            acceptance_event_ref
                            if acceptance_event.get("event_type") == "acceptance.blocked.recorded"
                            else None
                        )
                    )
                ),
                "owner_packet_event_ref": dossier_projection.get("owner_packet_event_ref"),
                "owner_packet_ref": owner_packet_ref,
                "owner_locus_ref": owner_locus_ref,
                "replay_receipt_ref": replay_receipt_ref,
                "acceptance_eligibility": acceptance_eligibility,
                "acceptance_dossier_id": dossier.get("dossier_id"),
                "projection_ref": dossier.get("projection_ref"),
                "missing_refs": list(dossier.get("missing_refs") or []),
                "candidate_owner_loci": list(dossier.get("candidate_owner_loci") or []),
                "no_count_increment_reason": dossier.get("no_count_increment_reason"),
                "next_owner_surface": next_owner_surface,
                "owner_surfaces": list(owner_target.get("owner_surfaces") or []),
                "future_observation": {
                    "baseline_window": (
                        future_observation.get("baseline_window")
                        or "current_process_audit_window"
                    ),
                    "post_projection_window": future_observation.get("post_projection_window"),
                    "metric": (
                        future_observation.get("metric")
                        or "anti_pattern_instances_per_session"
                    ),
                    "baseline_count": future_observation.get("baseline_count", baseline_count),
                    "post_count": future_observation.get("post_count"),
                    "future_observation_window_status": (
                        future_observation.get("future_observation_window_status")
                        or "unresolved"
                    ),
                    "status": future_observation.get("status") or "awaiting_owner_acceptance",
                },
                "drilldown_command": (
                    "./repo-python kernel.py --option-surface navigation_mechanism_candidates "
                    f"--band card --ids {claim_id}"
                ),
            }
        )
    lifecycle_rank = {
        "observed": 5,
        "projected": 4,
        "accepted": 3,
        "owner_acceptance_requested": 2,
    }
    ranked_rows = sorted(
        top_rows,
        key=lambda row: (
            lifecycle_rank.get(str(row.get("state") or ""), 0),
            int(row.get("observed_instances") or 0),
            str(row.get("anti_pattern_id") or ""),
        ),
        reverse=True,
    )
    observed_claim_refs = _observed_navigation_mechanism_claim_refs(ranked_rows)
    top_rows = ranked_rows[:8]
    return {
        "status": "candidate_learning_available" if candidate_count else "no_candidate_learning",
        "authority_posture": "candidate_and_validated_are_not_accepted",
        "candidate_count": candidate_count,
        "validated_count": validated_count,
        "accepted_count": accepted_count,
        "projected_count": projected_count,
        "observed_count": observed_count,
        "observed_anti_pattern_ids": sorted(observed_anti_pattern_ids),
        "observed_claim_refs": observed_claim_refs,
        "validation_status": "valid" if validation.get("ok") else "invalid",
        "validator_command": "./repo-python tools/meta/factory/validate_navigation_mechanism_facets.py --json",
        "factory_command": "./repo-python kernel.py --navigation-mechanism-factory --limit 20",
        "replay_command": "./repo-python kernel.py --navigation-mechanism-replay",
        "option_surface_command": "./repo-python kernel.py --option-surface navigation_mechanism_candidates --band flag",
        "owner_blocker_counts": owner_blockers,
        "top_candidate_claims": top_rows,
        "future_observation": {
            "status": (
                "observed"
                if projected_count and observed_count >= projected_count
                else "awaiting_accepted_projection"
            ),
            "baseline_source": "./repo-python kernel.py --process-audit",
            "post_projection_source": "./repo-python kernel.py --process-audit --after <accepted_projection_iso>; ./repo-python kernel.py --process-patterns --after <accepted_projection_iso>",
            "future_observation_window_status": (
                "recorded"
                if projected_count and observed_count >= projected_count
                else "window_selector_available_unrun"
            ),
            "window_gap": (
                "all projected acceptance claims have recorded post-projection observation windows"
                if projected_count and observed_count >= projected_count
                else "accepted projection timestamp and follow-up run are still required before claiming observed improvement"
            ),
            "metric": "anti_pattern_instances_per_session",
        },
    }


def _navigation_mechanism_acceptance_glance(
    root: Path,
    *,
    reason: str,
    cache_status: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Cheap route-learning posture from the durable acceptance read model.

    Quick metabolism should not rebuild trace-derived candidates on a cache miss,
    but the accepted/projected/observed lifecycle already has a small durable
    ledger. This fallback keeps that lifecycle visible without claiming full
    candidate validation freshness.
    """
    try:
        from system.lib.navigation_mechanism_factory import (
            load_navigation_mechanism_acceptance_dossiers,
            load_navigation_mechanism_acceptance_events,
        )

        dossiers = [
            row
            for row in load_navigation_mechanism_acceptance_dossiers(root)
            if isinstance(row, Mapping) and row.get("claim_id")
        ]
        latest_events: dict[str, Mapping[str, Any]] = {}
        for event in load_navigation_mechanism_acceptance_events(root):
            if isinstance(event, Mapping) and event.get("claim_id"):
                latest_events[str(event["claim_id"])] = event
    except Exception as exc:  # noqa: BLE001 - advisory fallback only
        return {
            "status": "deferred_by_quick_profile",
            "reason": f"{reason}; acceptance read model unavailable: {type(exc).__name__}: {exc}",
            "candidate_count": None,
            "validated_count": None,
            "accepted_count": None,
            "projected_count": None,
            "observed_count": None,
            "observed_claim_refs": [],
        }

    if not dossiers:
        return {
            "status": "deferred_by_quick_profile",
            "reason": f"{reason}; no durable acceptance dossiers are available",
            "candidate_count": None,
            "validated_count": None,
            "accepted_count": None,
            "projected_count": None,
            "observed_count": None,
            "observed_claim_refs": [],
        }

    accepted_count = 0
    projected_count = 0
    observed_count = 0
    observed_anti_pattern_ids: set[str] = set()
    top_rows: list[dict[str, Any]] = []
    for dossier in dossiers:
        claim_id = str(dossier.get("claim_id") or "")
        event = latest_events.get(claim_id) or {}
        read_model = (
            dossier.get("read_model_projection")
            if isinstance(dossier.get("read_model_projection"), Mapping)
            else {}
        )
        state = str(event.get("state_after") or dossier.get("state") or "")
        acceptance_eligibility = str(dossier.get("acceptance_eligibility") or "blocked")
        future_observation = (
            dossier.get("future_observation")
            if isinstance(dossier.get("future_observation"), Mapping)
            else {}
        )
        projection_ref = dossier.get("projection_ref")
        if acceptance_eligibility == "accepted" or state in {"accepted", "projected", "observed"}:
            accepted_count += 1
        if projection_ref or state in {"projected", "observed"}:
            projected_count += 1
        if state == "observed" or future_observation.get("status") == "observed":
            observed_count += 1
            if dossier.get("anti_pattern_id"):
                observed_anti_pattern_ids.add(str(dossier.get("anti_pattern_id")))

        event_ref = (
            f"navigation_mechanism_acceptance_event:{event.get('event_id')}"
            if event.get("event_id")
            else read_model.get("latest_acceptance_event_ref")
        )
        top_rows.append(
            {
                "claim_id": claim_id,
                "anti_pattern_id": dossier.get("anti_pattern_id"),
                "state": state,
                "latest_acceptance_event_type": (
                    event.get("event_type") or read_model.get("latest_acceptance_event_type")
                ),
                "acceptance_event_ref": event_ref,
                "previous_acceptance_event_ref": event.get("previous_event_ref"),
                "blocked_event_ref": read_model.get("blocked_event_ref"),
                "owner_packet_ref": read_model.get("owner_packet_ref") or dossier.get("owner_packet_ref"),
                "owner_locus_ref": (
                    read_model.get("owner_locus_ref") or dossier.get("code_or_tool_loci_ref")
                ),
                "replay_receipt_ref": (
                    read_model.get("replay_receipt_ref") or dossier.get("replay_receipt_ref")
                ),
                "projection_ref": projection_ref,
                "acceptance_eligibility": acceptance_eligibility,
                "acceptance_dossier_id": dossier.get("dossier_id"),
                "owner_acceptance_status": (
                    "accepted" if acceptance_eligibility == "accepted" else "missing"
                ),
                "missing_refs": list(dossier.get("missing_refs") or []),
                "no_count_increment_reason": dossier.get("no_count_increment_reason"),
                "replay_status": "not_rebuilt_in_quick_profile",
                "validation_status": "not_rebuilt_in_quick_profile",
                "future_observation": {
                    "baseline_window": future_observation.get("baseline_window"),
                    "post_projection_window": future_observation.get("post_projection_window"),
                    "metric": future_observation.get("metric"),
                    "baseline_count": future_observation.get("baseline_count"),
                    "post_count": future_observation.get("post_count"),
                    "future_observation_window_status": (
                        future_observation.get("future_observation_window_status")
                        or "unresolved"
                    ),
                    "status": future_observation.get("status") or "awaiting_owner_acceptance",
                },
                "drilldown_command": (
                    "./repo-python kernel.py --option-surface navigation_mechanism_candidates "
                    f"--band card --ids {claim_id}"
                ),
            }
        )

    lifecycle_rank = {"observed": 5, "projected": 4, "accepted": 3, "owner_acceptance_requested": 2}
    ranked_rows = sorted(
        top_rows,
        key=lambda row: (
            lifecycle_rank.get(str(row.get("state") or ""), 0),
            str(row.get("anti_pattern_id") or ""),
        ),
        reverse=True,
    )
    observed_claim_refs = _observed_navigation_mechanism_claim_refs(ranked_rows)
    top_rows = ranked_rows[:8]
    return {
        "status": "acceptance_read_model_available",
        "reason": reason,
        "authority_posture": "acceptance_read_model_not_candidate_factory",
        "candidate_count": None,
        "validated_count": None,
        "accepted_count": accepted_count,
        "projected_count": projected_count,
        "observed_count": observed_count,
        "observed_anti_pattern_ids": sorted(observed_anti_pattern_ids),
        "observed_claim_refs": observed_claim_refs,
        "validation_status": "not_rebuilt_in_quick_profile",
        "validator_command": "./repo-python tools/meta/factory/validate_navigation_mechanism_facets.py --json",
        "factory_command": "./repo-python kernel.py --navigation-mechanism-factory --limit 20",
        "replay_command": "./repo-python kernel.py --navigation-mechanism-replay",
        "option_surface_command": "./repo-python kernel.py --option-surface navigation_mechanism_candidates --band flag",
        "top_candidate_claims": top_rows,
        "cache_fallback": dict(cache_status or {}),
        "future_observation": {
            "status": (
                "observed"
                if projected_count and observed_count >= projected_count
                else "awaiting_accepted_projection_observation"
            ),
            "baseline_source": "./repo-python kernel.py --process-audit",
            "post_projection_source": "./repo-python kernel.py --process-audit --after <accepted_projection_iso>; ./repo-python kernel.py --process-patterns --after <accepted_projection_iso>",
            "future_observation_window_status": (
                "recorded"
                if projected_count and observed_count >= projected_count
                else "window_selector_available_unrun"
            ),
            "window_gap": (
                "quick fallback read model found recorded post-projection observations for all projected claims"
                if projected_count and observed_count >= projected_count
                else "quick fallback uses durable acceptance state; observed improvement still requires a later process-audit window"
            ),
            "metric": "anti_pattern_instances_per_session",
        },
    }


def _cached_navigation_mechanism_metabolism(
    root: Path,
    process_audit: Mapping[str, Any],
    *,
    allow_build: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if str(process_audit.get("status") or "") not in {"available"}:
        return {
            "status": "deferred_by_quick_profile",
            "reason": "navigation mechanism summary needs process-audit input; quick metabolism did not rebuild it",
            "candidate_count": None,
            "validated_count": None,
            "accepted_count": None,
            "projected_count": None,
            "observed_count": None,
        }, {
            "node_id": "navigation_metabolism.navigation_mechanism.quick",
            "status": "deferred_no_process_audit",
            "reason": "quick_profile_does_not_rebuild_expensive_dependency",
            "ttl_s": QUICK_COMMAND_CACHE_TTL_SECONDS,
            "freshness_policy": "stale_ok_cache_peek",
            "dynamic_inputs_manifested": False,
        }
    kwargs = {
        "node_id": "navigation_metabolism.navigation_mechanism.quick",
        "key": _process_audit_quick_key(process_audit),
        "freshness_policy": "stale_ok_cache_peek_with_input_manifest_guard",
        "dynamic_inputs_manifested": False,
    }
    if not allow_build:
        payload, status = peek_cached_command_node(
            root,
            **kwargs,
            input_paths=_NAVIGATION_MECHANISM_CACHE_INPUT_PATHS,
            ttl_s=QUICK_COMMAND_CACHE_TTL_SECONDS,
        )
        if payload is None:
            reason = (
                f"navigation mechanism cache {status.get('reason') or 'unavailable'}; "
                "quick metabolism did not rebuild trace-derived candidates"
            )
            return _navigation_mechanism_acceptance_glance(
                root,
                reason=reason,
                cache_status=status,
            ), status
        return dict(payload) if isinstance(payload, Mapping) else {"status": "unavailable"}, status
    payload, status = cached_command_node(
        root,
        node_id=kwargs["node_id"],
        key=kwargs["key"],
        input_paths=_NAVIGATION_MECHANISM_CACHE_INPUT_PATHS,
        ttl_s=QUICK_COMMAND_CACHE_TTL_SECONDS,
        builder=lambda: _navigation_mechanism_metabolism(root, process_audit),
    )
    return dict(payload) if isinstance(payload, Mapping) else {"status": "unavailable"}, status


def _cached_clusterability_quick(
    root: Path,
    *,
    budget: int,
    allow_build: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not allow_build:
        return {
            "kind": "navigation_clusterability_audit",
            "schema_version": "navigation_clusterability_audit_v0",
            "status": "deferred_by_quick_profile",
            "summary": {
                "high_cardinality_kind_count": None,
                "implemented_count": None,
                "safe_now_count": None,
                "blocked_count": None,
                "missing_cluster_adapter_count": None,
                "debt_count": 0,
            },
            "rows": [],
            "debt_rows": [],
            "defer_reason": "quick navigation metabolism does not measure clusterability payloads; run --clusterability-audit for the full classification",
            "drilldown_command": "./repo-python kernel.py --clusterability-audit --context-budget 12000",
        }, {
            "node_id": "navigation_metabolism.clusterability.quick",
            "status": "deferred_by_quick_profile",
            "reason": "clusterability measurement belongs to explicit drilldown",
            "age_s": None,
            "ttl_s": 0,
            "freshness_policy": "explicit_clusterability_audit_only",
            "dynamic_inputs_manifested": False,
        }
    payload = build_navigation_clusterability_audit(
        root,
        context_budget=budget,
        measure_all_rows=False,
    )
    status = {
        "node_id": "navigation_metabolism.clusterability.quick",
        "status": "uncached_built",
        "reason": "clusterability audit reads dynamic artifact projections outside any stable static manifest",
        "age_s": 0.0,
        "ttl_s": 0,
        "freshness_policy": "uncached_dynamic_artifact_projection",
        "dynamic_inputs_manifested": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return dict(payload) if isinstance(payload, Mapping) else {"kind": "navigation_clusterability_audit"}, status


_PROCESS_PATTERN_REPAIRS: dict[str, dict[str, Any]] = {
    "anti_pattern_stall_detected": {
        "priority": 78,
        "title_template": "process audit: stall detected in recent agent sessions",
        "repair_class": "agent_orientation_or_resume_protocol_repair",
        "target_files": [
            "codex/doctrine/skills/kernel/agent_session_diagnostics.md",
            "codex/doctrine/paper_modules/agent_self_observability_plane.md",
        ],
        "tests": ["process audit reports fewer stall instances after the orientation repair"],
        "anti_pattern_kind": "agent_stalled_mid_session",
    },
    "anti_pattern_loop_detected": {
        "priority": 80,
        "title_template": "process audit: command loop detected in recent agent sessions",
        "repair_class": "loop_break_skill_or_hook_repair",
        "target_files": [
            ".claude/hooks/runtime_hook.py",
            "codex/doctrine/skills/kernel/agent_session_diagnostics.md",
        ],
        "tests": ["process audit reports fewer loop instances after the steering repair"],
        "anti_pattern_kind": "command_loop",
    },
    "anti_pattern_paper_module_skip": {
        "priority": 82,
        "title_template": "process audit: paper-module skip in recent agent sessions",
        "repair_class": "paper_module_lookup_skill_or_router_repair",
        "target_files": [
            "codex/doctrine/skills/kernel/navigation_seed.md",
            "system/lib/navigation_context_pack.py",
        ],
        "tests": [
            "process audit reports fewer paper-module-skip instances after the router repair",
            "context-pack exposes the paper module slug instead of pushing the agent to read+grep",
        ],
        "anti_pattern_kind": "paper_module_skip",
    },
    "anti_pattern_cold_boot_missing_info": {
        "priority": 84,
        "title_template": "process audit: cold-boot missed --info / --preflight / --pulse in recent agent sessions",
        "repair_class": "entrypoint_first_contact_repair",
        "target_files": [
            "CLAUDE.md",
            "AGENTS.md",
            "codex/doctrine/skills/kernel/bootstrap.md",
        ],
        "tests": ["process audit reports fewer cold-boot-missing-info instances after the entrypoint refresh"],
        "anti_pattern_kind": "cold_boot_missing_info",
    },
    "anti_pattern_grep_before_kernel": {
        "priority": 86,
        "title_template": "process audit: grep before kernel in recent agent sessions",
        "repair_class": "hook_steering_plus_context_pack_first_contact",
        "target_files": [
            ".claude/hooks/runtime_hook.py",
            "system/lib/navigation_context_pack.py",
        ],
        "tests": ["process audit reports fewer grep-before-kernel instances after the steering repair"],
        "anti_pattern_kind": "grep_before_kernel",
    },
    "anti_pattern_deep_without_ladder": {
        "priority": 76,
        "title_template": "process audit: deep traversal without ladder climb",
        "repair_class": "navigation_seed_skill_or_kind_atlas_router_repair",
        "target_files": [
            "codex/doctrine/skills/kernel/navigation_seed.md",
            "codex/doctrine/skills/kernel/agent_session_diagnostics.md",
        ],
        "tests": ["process audit reports fewer deep-without-ladder instances after the seed-skill refresh"],
        "anti_pattern_kind": "deep_without_ladder",
        "owner_surface": "navigation_ladder_owner_route",
        "owner_status_command": (
            "./repo-python kernel.py --coverage-enforcement-matrix "
            '"anti_pattern_deep_without_ladder" --context-budget 12000'
        ),
        "authoritative_decision_command": (
            "./repo-python kernel.py --navigation-metabolism "
            '"anti_pattern_deep_without_ladder owner route" '
            "--metabolism-profile quick --context-budget 12000"
        ),
        "source_projection_boundary": {
            "process_audit_policy": "behavior_evidence_not_source_authority",
            "patch_selection_policy": "select_stable_owner_card_before_source_patch",
            "owner_status_route": (
                "./repo-python kernel.py --coverage-enforcement-matrix "
                '"anti_pattern_deep_without_ladder" --context-budget 12000'
            ),
            "authoritative_decision_route": (
                "./repo-python kernel.py --navigation-metabolism "
                '"anti_pattern_deep_without_ladder owner route" '
                "--metabolism-profile quick --context-budget 12000"
            ),
            "owner_card_route": (
                "./repo-python kernel.py --option-surface skills --band card "
                "--ids navigation_seed,agent_session_diagnostics"
            ),
        },
    },
    "anti_pattern_phase_residual_exception_narration": {
        "priority": 88,
        "title_template": "process audit: phase residual lane narrated as an exception",
        "repair_class": "phase_task_alignment_residual_lane",
        "target_files": [
            "system/lib/kernel/commands/navigate.py",
            "system/lib/phase_task_alignment.py",
            "codex/doctrine/skills/kernel/navigation_seed.md",
        ],
        "tests": [
            "phase task alignment emits residual_lane or mixed_lane instead of requiring exception narration",
            "hook shadow coverage maps the old mismatch sentence to --phase <phase> --task",
        ],
        "anti_pattern_kind": "phase_residual_exception_narration",
    },
}


def _process_audit_behavior_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Turn live process-audit anti-patterns and slow-action findings into behavior_debt rows.

    Adopted from Sentrux p001 (continuous structural quality signal loop) and
    p003 (session baseline regression gate): observed agent paths feed into
    the same prioritized debt queue the authoring/projection/clusterability
    audits already use, instead of remaining a parallel post-hoc lens.
    """
    if str(payload.get("status") or "") != "available":
        return []
    rows: list[dict[str, Any]] = []
    session_count = max(1, int(payload.get("session_count") or 0))

    for pattern in payload.get("patterns") or []:
        if not isinstance(pattern, Mapping):
            continue
        pattern_id = str(pattern.get("pattern_id") or "")
        if not pattern_id or pattern_id.startswith("positive_"):
            continue
        spec = _PROCESS_PATTERN_REPAIRS.get(pattern_id)
        if spec is None:
            continue
        instances = int(pattern.get("instances") or 0)
        if instances <= 0:
            continue
        session_hits = list(pattern.get("session_id_hits") or [])
        extra = {
            "anti_pattern_id": pattern_id,
            "anti_pattern": spec["anti_pattern_kind"],
            "instances": instances,
            "sessions_hit": len(session_hits),
            "session_total": session_count,
            "sentrux_provenance": ["p001", "p003"],
        }
        for optional_key in (
            "owner_surface",
            "owner_status_command",
            "authoritative_decision_command",
            "source_projection_boundary",
        ):
            if optional_key in spec:
                extra[optional_key] = spec[optional_key]
        rows.append(
            _debt_row(
                debt_id=f"behavior:process_audit:{pattern_id}",
                debt_class="behavior_debt",
                priority=int(spec["priority"]),
                title=spec["title_template"],
                evidence=(
                    f"pattern_id={pattern_id}; instances={instances}; sessions_hit={len(session_hits)}; "
                    f"session_total={session_count}"
                ),
                repair_class=spec["repair_class"],
                target_files=list(spec["target_files"]),
                tests=list(spec["tests"]),
                source_surface="--process-audit",
                extra=extra,
            )
        )

    # Slow-action-shape findings — one row per action_kind that exceeds its threshold.
    seen_kinds: set[str] = set()
    for finding in payload.get("findings") or []:
        if not isinstance(finding, Mapping):
            continue
        if finding.get("rule") != "slow_action_shape":
            continue
        action_kind = str(finding.get("action_kind") or "")
        if not action_kind or action_kind in seen_kinds:
            continue
        seen_kinds.add(action_kind)
        bottleneck = (payload.get("bottlenecks") or {}).get(action_kind) or {}
        if not isinstance(bottleneck, Mapping):
            bottleneck = {}
        repair_hints = _compact_repair_hints(bottleneck.get("repair_hints"))
        preferred_next = repair_hints[0].get("preferred_next") if repair_hints else ""
        command_shape_tags = _example_command_shape_tags(bottleneck.get("example_spans"))
        rows.append(
            _debt_row(
                debt_id=f"behavior:process_audit:slow_action_shape:{action_kind}",
                debt_class="behavior_debt",
                priority=72,
                title=f"process audit: action kind '{action_kind}' p95 over threshold",
                evidence=(
                    f"action_kind={action_kind}; "
                    f"p50_ms={bottleneck.get('p50_ms')}; p95_ms={bottleneck.get('p95_ms')}; "
                    f"max_ms={bottleneck.get('max_ms')}; threshold_ms={bottleneck.get('threshold_ms')}"
                ),
                repair_class="action_kind_throughput_repair",
                target_files=[
                    "tools/meta/agent_telemetry/extract.py",
                    "codex/doctrine/skills/kernel/",
                ],
                tests=[
                    f"process audit reports {action_kind} p95 below threshold after the throughput repair",
                ],
                source_surface="--process-audit",
                extra={
                    "anti_pattern": "slow_action_shape",
                    "action_kind": action_kind,
                    "p50_ms": bottleneck.get("p50_ms"),
                    "p95_ms": bottleneck.get("p95_ms"),
                    "max_ms": bottleneck.get("max_ms"),
                    "threshold_ms": bottleneck.get("threshold_ms"),
                    "repair_hints": repair_hints,
                    "preferred_next": preferred_next,
                    "example_command_shape_tags": command_shape_tags,
                    "owner_surface": "process_bottlenecks",
                    "owner_status_command": "./repo-python kernel.py --process-bottlenecks",
                    "authoritative_decision_command": "./repo-python kernel.py --process-bottlenecks --force",
                    "process_bottleneck_drilldown": "./repo-python kernel.py --process-bottlenecks",
                    "source_projection_boundary": {
                        "cached_summary_policy": "advisory_only_for_candidate_ranking",
                        "patch_selection_policy": "force_live_before_source_patch",
                        "default_status_route": "./repo-python kernel.py --process-bottlenecks",
                        "authoritative_decision_route": "./repo-python kernel.py --process-bottlenecks --force",
                    },
                    "sentrux_provenance": ["p001"],
                },
            )
        )
    return rows


def _component_score(count: int) -> float:
    """Continuous Sentrux p002 component score: 1 / (1 + count).

    No calibration constants, monotonic, never zero, asymptotic to 1 when the
    debt class is fully clear. The geometric mean over component scores is
    the floating quality_signal; the lowest component is the bottleneck.
    """
    safe = max(0, int(count))
    return 1.0 / (1.0 + float(safe))


def _quality_signal(
    counts: Mapping[str, Any],
    *,
    process_audit_status: str,
) -> dict[str, Any]:
    """Compute the Sentrux-shape quality_signal header without collapsing drilldowns.

    Per the sentrux annex local-adaptation rule, this header is purely
    additive: every per-class debt_row stays in the packet's debt_rows /
    top_repairs / observation_sources fields. The header is ONE number plus
    the bottleneck pointer; readers must drill into the per-class rows for
    repair specifics.
    """
    active_counts: dict[str, int] = {}
    components: dict[str, float] = {}
    for class_name in _QUALITY_SIGNAL_CLASSES:
        active_count = max(0, int(counts.get(class_name) or 0))
        active_counts[class_name] = active_count
        components[class_name] = _component_score(active_count)
    total_active_count = sum(active_counts.values())
    if not components:
        score = 0.0
        bottleneck = None
        status = "no_components"
    else:
        product = 1.0
        for value in components.values():
            product *= max(value, 1e-6)
        score = product ** (1.0 / float(len(components)))
        bottleneck = (
            min(components.items(), key=lambda item: (item[1], item[0]))[0]
            if total_active_count
            else None
        )
        status = "debt" if total_active_count else "clean"
    return {
        "score": round(score, 4),
        "status": status,
        "bottleneck_debt_class": bottleneck,
        "components": {key: round(value, 4) for key, value in components.items()},
        "scoring_model": "geometric_mean_over_inverse_one_plus_count",
        "preserves_drilldowns": True,
        "sentrux_provenance": ["p001", "p002"],
        "source_freshness": {
            "process_audit_status": process_audit_status,
            "computed_at": _utc_now(),
        },
        "drilldown_into_components": {
            class_name: f"filter packet.debt_rows[debt_class=={class_name}]"
            for class_name in _QUALITY_SIGNAL_CLASSES
        },
    }


def _top_repairs(rows: Sequence[Mapping[str, Any]], *, limit: int = 12) -> list[dict[str, Any]]:
    ranked = sorted(_active_debt_rows(rows), key=lambda row: int(row.get("priority") or 0), reverse=True)
    keys = [
        "debt_id",
        "debt_class",
        "priority",
        "title",
        "repair_class",
        "target_files",
        "tests",
        "safe_alternative",
        "better_first_surface",
        "source_coupling_status",
        "dirty_source_paths",
        "safe_to_commit_generated_outputs_without_sources",
        "action_kind",
        "p95_ms",
        "threshold_ms",
        "repair_hints",
        "preferred_next",
        "example_command_shape_tags",
        "owner_surface",
        "owner_status_command",
        "authoritative_decision_command",
        "process_bottleneck_drilldown",
        "source_freshness",
        "source_projection_boundary",
    ]
    repairs: list[dict[str, Any]] = []
    for row in ranked[:limit]:
        repairs.append({key: row[key] for key in keys if key in row})
    return repairs


def _count_by_class(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {
        "entrypoint_debt": 0,
        "authoring_debt": 0,
        "projection_debt": 0,
        "sufficiency_debt": 0,
        "latency_debt": 0,
        "timeout_debt": 0,
        "clusterability_debt": 0,
        "routing_coverage_debt": 0,
        "annex_currentness_debt": 0,
        "behavior_debt": 0,
        "actor_delivery_debt": 0,
        "annex_import_debt": 0,
        "layer_sprawl_debt": 0,
    }
    for row in rows:
        if not _is_active_debt_row(row):
            continue
        cls = str(row.get("debt_class") or "")
        if cls in counts:
            counts[cls] += 1
    return counts


def _packet_bottleneck_debt_class(packet: Mapping[str, Any]) -> str:
    summary = packet.get("summary")
    if isinstance(summary, Mapping):
        bottleneck = str(summary.get("quality_signal_bottleneck") or "")
        if bottleneck:
            return bottleneck
    quality_signal = packet.get("quality_signal")
    if isinstance(quality_signal, Mapping):
        return str(quality_signal.get("bottleneck_debt_class") or "")
    return ""


def _best_debt_row_for_class(
    rows: Sequence[Mapping[str, Any]],
    debt_class: str,
    *,
    active_only: bool,
) -> Mapping[str, Any] | None:
    matching = [
        row
        for row in rows
        if str(row.get("debt_class") or "") == debt_class
        and (not active_only or _is_active_debt_row(row))
    ]
    if not matching:
        return None
    return sorted(matching, key=lambda row: int(row.get("priority") or 0), reverse=True)[0]


def _priority_trim_debt_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int,
    required_active_class: str | None = None,
) -> list[Mapping[str, Any]]:
    if limit <= 0:
        return []
    required_classes = [
        "authoring_debt",
        "projection_debt",
        "sufficiency_debt",
        "latency_debt",
        "timeout_debt",
        "clusterability_debt",
        "routing_coverage_debt",
        "annex_currentness_debt",
        "behavior_debt",
        "actor_delivery_debt",
        "annex_import_debt",
        "layer_sprawl_debt",
    ]
    kept: list[Mapping[str, Any]] = []
    seen_ids: set[str] = set()

    def append_row(row: Mapping[str, Any]) -> bool:
        debt_id = str(row.get("debt_id") or "")
        if debt_id in seen_ids:
            return False
        kept.append(row)
        seen_ids.add(debt_id)
        return True

    if required_active_class:
        required_row = _best_debt_row_for_class(rows, required_active_class, active_only=True)
        if required_row is not None:
            append_row(required_row)

    for sentinel_id in _BUDGET_TRIM_SENTINEL_DEBT_IDS:
        for row in rows:
            debt_id = str(row.get("debt_id") or "")
            if debt_id == sentinel_id:
                append_row(row)
                break
    sentinel_rows = [
        row
        for row in rows
        if _is_active_debt_row(row)
        and (
            str(row.get("repair_class") or "") in {"standard_grouping_key_required", "projection_contract_repair"}
            or str(row.get("source_surface") or "") in {"--clusterability-audit", "navigation_metabolism.quick_profile"}
        )
    ]
    for row in sorted(sentinel_rows, key=lambda item: int(item.get("priority") or 0), reverse=True):
        if append_row(row):
            break
    for debt_class in required_classes:
        row = _best_debt_row_for_class(rows, debt_class, active_only=True)
        if row is None:
            row = _best_debt_row_for_class(rows, debt_class, active_only=False)
        if row is not None:
            append_row(row)
    for row in rows:
        append_row(row)
        if len(kept) >= limit:
            break
    return kept[:limit]


def _budget_trim(packet: dict[str, Any], *, context_budget: int) -> dict[str, Any]:
    # Keep a small serialization margin so the emitted pretty JSON stays inside
    # the advertised token-derived byte budget after budget fields are updated.
    budget_bytes = max(1000, int(context_budget or 12000)) * 4 - 1024
    if _json_bytes(packet) <= budget_bytes:
        packet["budget"]["estimated_tokens"] = max(1, (_json_bytes(packet) + 3) // 4)
        packet["budget"]["budget_contract"] = "fits_within_budget"
        packet["budget"]["over_budget"] = False
        return packet

    packet = dict(packet)
    bottleneck_class = _packet_bottleneck_debt_class(packet)
    packet["debt_rows"] = _priority_trim_debt_rows(
        packet.get("debt_rows", []),
        limit=18,
        required_active_class=bottleneck_class,
    )
    packet["top_repairs"] = packet.get("top_repairs", [])[:6]
    lifecycle = list(packet.get("route_lifecycle", []))
    trim_limit = len(_ALWAYS_INCLUDE_ROUTE_LIFECYCLE_IDS) + _ROUTE_LIFECYCLE_EXTRA_TRIM_ROWS
    kept: list[dict[str, Any]] = []
    seen: set[str] = set()
    for route_id in _ALWAYS_INCLUDE_ROUTE_LIFECYCLE_IDS:
        for row in lifecycle:
            if isinstance(row, Mapping) and row.get("route_id") == route_id and route_id not in seen:
                kept.append(dict(row))
                seen.add(route_id)
                break
    for row in lifecycle:
        if not isinstance(row, Mapping):
            continue
        route_id = str(row.get("route_id") or "")
        if route_id in seen:
            continue
        kept.append(dict(row))
        seen.add(route_id)
        if len(kept) >= trim_limit:
            break
    packet["route_lifecycle"] = kept[:trim_limit]
    if _json_bytes(packet) > budget_bytes:
        compact_lifecycle: list[dict[str, Any]] = []
        for row in packet.get("route_lifecycle", []):
            if not isinstance(row, Mapping):
                continue
            compact: dict[str, Any] = {
                "route_id": row.get("route_id"),
                "status": row.get("status"),
            }
            for key in (
                "superseded_by",
                "purpose",
                "compatibility_behavior",
                "supported_slugs",
                "supported_slug_source",
                "generic_existing_slug_support",
                "entry_condition",
                "residual_lanes",
                "owner_surfaces",
                "write_scope_policy",
                "write_guard",
            ):
                if key in row and row.get(key) not in (None, [], ""):
                    value = row.get(key)
                    if key == "residual_lanes" and isinstance(value, list):
                        compact[key] = [
                            {
                                "lane_id": lane.get("lane_id"),
                                "status": lane.get("status"),
                                "entry_command_template": lane.get("entry_command_template"),
                            }
                            for lane in value
                            if isinstance(lane, Mapping)
                        ]
                    elif key == "owner_surfaces" and isinstance(value, list):
                        compact[key] = [
                            {
                                "surface_id": surface.get("surface_id"),
                                "template": surface.get("template"),
                            }
                            for surface in value
                            if isinstance(surface, Mapping)
                        ]
                    else:
                        compact[key] = _trim(value, max_chars=120) if isinstance(value, str) else value
            compact_lifecycle.append(compact)
        packet["route_lifecycle"] = compact_lifecycle
    if _json_bytes(packet) > budget_bytes:
        packet["top_repairs"] = packet.get("top_repairs", [])[:4]
    if _json_bytes(packet) > budget_bytes:
        packet["source_surfaces"] = packet.get("source_surfaces", [])[:8]
    if _json_bytes(packet) > budget_bytes:
        packet["debt_rows"] = _priority_trim_debt_rows(
            packet.get("debt_rows", []),
            limit=14,
            required_active_class=bottleneck_class,
        )
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("navigation_fitness"), Mapping):
        fitness = packet.get("navigation_fitness") or {}
        packet["navigation_fitness"] = {
            "kind": fitness.get("kind"),
            "suite": fitness.get("suite"),
            "strategy": {
                "fitness_mode": (fitness.get("strategy") or {}).get("fitness_mode")
                if isinstance(fitness.get("strategy"), Mapping)
                else None,
            },
            "summary": fitness.get("summary"),
            "route_type_metrics": fitness.get("route_type_metrics"),
            "debt_candidates": list(fitness.get("debt_candidates") or [])[:6],
            "trimmed_for_metabolism_budget": True,
        }
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("entrypoint_health"), Mapping):
        entrypoint = packet.get("entrypoint_health") or {}
        packet["entrypoint_health"] = {
            "kind": entrypoint.get("kind"),
            "schema_version": entrypoint.get("schema_version"),
            "summary": entrypoint.get("summary"),
            "instruction_files": [
                {
                    "path": row.get("path"),
                    "bytes": row.get("bytes"),
                    "budget_status": row.get("budget_status"),
                    "first_contact_status": row.get("first_contact_status"),
                    "disallowed_stale_route_hit_count": row.get("disallowed_stale_route_hit_count"),
                }
                for row in list(entrypoint.get("instruction_files") or [])[:4]
                if isinstance(row, Mapping)
            ],
            "forbidden_first_contact_hits": entrypoint.get("forbidden_first_contact_hits") or [],
            "trimmed_for_metabolism_budget": True,
        }
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("annex_routing_coverage"), Mapping):
        coverage = packet.get("annex_routing_coverage") or {}
        packet["annex_routing_coverage"] = {
            "kind": coverage.get("kind"),
            "schema_version": coverage.get("schema_version"),
            "summary": coverage.get("summary"),
            "cluster_key": coverage.get("cluster_key"),
            "largest_clusters": list(coverage.get("largest_clusters") or [])[:8],
            "source_kind_counts_for_unrouted": coverage.get("source_kind_counts_for_unrouted"),
            "largest_unrouted_annexes": list(coverage.get("largest_unrouted_annexes") or [])[:8],
            "debt_rows": list(coverage.get("debt_rows") or [])[:2],
            "trimmed_for_metabolism_budget": True,
        }
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("annex_currentness"), Mapping):
        currentness = packet.get("annex_currentness") or {}
        summary = currentness.get("summary") if isinstance(currentness.get("summary"), Mapping) else {}
        source = currentness.get("source") if isinstance(currentness.get("source"), Mapping) else {}
        packet["annex_currentness"] = {
            "kind": currentness.get("kind"),
            "schema_version": currentness.get("schema_version"),
            "summary": {
                "digest_status": summary.get("digest_status"),
                "digest_generated_at": summary.get("digest_generated_at"),
                "mode": summary.get("mode"),
                "annex_count": summary.get("annex_count"),
                "attention_count": summary.get("attention_count"),
                "stale_count": summary.get("stale_count"),
                "max_stale_days": summary.get("max_stale_days"),
                "currentness_debt": summary.get("currentness_debt"),
                "bucket_counts": summary.get("bucket_counts"),
            },
            "source": {
                "digest_json": source.get("digest_json"),
                "digest_markdown": source.get("digest_markdown"),
                "bounded_refresh_command": source.get("bounded_refresh_command"),
            },
            "top_attention_rows": [
                {
                    "slug": row.get("slug"),
                    "bucket": row.get("bucket"),
                    "report_path": row.get("report_path"),
                    "broken_target_count": row.get("broken_target_count"),
                    "high_signal_change_count": row.get("high_signal_change_count"),
                    "stale_days": row.get("stale_days"),
                }
                for row in list(currentness.get("top_attention_rows") or [])[:4]
                if isinstance(row, Mapping)
            ],
            "stale_rows": list(currentness.get("stale_rows") or [])[:4],
            "debt_rows": [
                {
                    "debt_id": row.get("debt_id"),
                    "priority": row.get("priority"),
                    "repair_class": row.get("repair_class"),
                    "safe_alternative": row.get("safe_alternative"),
                }
                for row in list(currentness.get("debt_rows") or [])[:3]
                if isinstance(row, Mapping)
            ],
            "trimmed_for_metabolism_budget": True,
        }
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("annex_movement_pressure_map"), Mapping):
        pressure = packet.get("annex_movement_pressure_map") or {}
        packet["annex_movement_pressure_map"] = {
            "kind": pressure.get("kind"),
            "schema_version": pressure.get("schema_version"),
            "query": pressure.get("query"),
            "summary": pressure.get("summary"),
            "quality_signal": pressure.get("quality_signal"),
            "pressure_rows": [
                {
                    "slug": row.get("slug"),
                    "lane": row.get("lane"),
                    "movement": row.get("movement"),
                    "local_plane_pressure": row.get("local_plane_pressure"),
                    "evidence_paths": list(row.get("evidence_paths") or [])[:4],
                    "next_command": row.get("next_command"),
                }
                for row in list(pressure.get("pressure_rows") or [])[:5]
                if isinstance(row, Mapping)
            ],
            "trimmed_for_metabolism_budget": True,
        }
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("annex_navigation_dogfood"), Mapping):
        dogfood = packet.get("annex_navigation_dogfood") or {}
        packet["annex_navigation_dogfood"] = {
            "kind": dogfood.get("kind"),
            "schema_version": dogfood.get("schema_version"),
            "query": dogfood.get("query"),
            "summary": dogfood.get("summary"),
            "compressed_comprehension": dogfood.get("compressed_comprehension"),
            "surface_health": {
                "currentness": ((dogfood.get("surface_health") or {}).get("currentness") or {}).get("summary")
                if isinstance(dogfood.get("surface_health"), Mapping)
                else {},
                "routing_coverage": ((dogfood.get("surface_health") or {}).get("routing_coverage") or {}).get("summary")
                if isinstance(dogfood.get("surface_health"), Mapping)
                else {},
            },
            "protocol_findings": list(dogfood.get("protocol_findings") or [])[:3],
            "candidate_repairs": list(dogfood.get("candidate_repairs") or [])[:4],
            "trimmed_for_metabolism_budget": True,
        }
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("clusterability"), Mapping):
        clusterability = packet.get("clusterability") or {}
        packet["clusterability"] = {
            "kind": clusterability.get("kind"),
            "schema_version": clusterability.get("schema_version"),
            "summary": clusterability.get("summary"),
            "rows": [
                {
                    "kind_id": row.get("kind_id"),
                    "row_count": row.get("row_count"),
                    "cluster_flag_status": row.get("cluster_flag_status"),
                    "all_row_flag_measured_bytes": row.get("all_row_flag_measured_bytes"),
                    "candidate_cluster_estimated_bytes": row.get("candidate_cluster_estimated_bytes"),
                    "grouping_keys_available": row.get("grouping_keys_available"),
                    "grouping_key_provenance": row.get("grouping_key_provenance"),
                    "repair_class": row.get("repair_class"),
                }
                for row in list(clusterability.get("rows") or [])[:9]
                if isinstance(row, Mapping)
            ],
            "trimmed_for_metabolism_budget": True,
        }
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("path_reference_reading_yield_audit"), Mapping):
        audit = packet.get("path_reference_reading_yield_audit") or {}
        compact_findings: list[dict[str, Any]] = []
        for row in list(audit.get("findings") or [])[:6]:
            if not isinstance(row, Mapping):
                continue
            reading_yield = row.get("reading_yield") if isinstance(row.get("reading_yield"), Mapping) else {}
            compact_findings.append(
                {
                    "surface_id": row.get("surface_id"),
                    "citation_path": row.get("citation_path"),
                    "route_kind": row.get("route_kind"),
                    "target_ref": row.get("target_ref"),
                    "owner_kind": row.get("owner_kind"),
                    "reading_yield": {
                        "band": reading_yield.get("band"),
                        "source_field": reading_yield.get("source_field"),
                        "authority_posture": reading_yield.get("authority_posture"),
                        "drilldown": reading_yield.get("drilldown"),
                    }
                    if reading_yield
                    else None,
                    "debt_class": row.get("debt_class"),
                    "severity": row.get("severity"),
                }
            )
        packet["path_reference_reading_yield_audit"] = {
            "status": audit.get("status"),
            "mode": audit.get("mode"),
            "scanned_surface_count": audit.get("scanned_surface_count"),
            "decision_bearing_route_count": audit.get("decision_bearing_route_count"),
            "resolved_owner_count": audit.get("resolved_owner_count"),
            "resolved_yield_count": audit.get("resolved_yield_count"),
            "mapped_equivalent_count": audit.get("mapped_equivalent_count"),
            "missing_yield_count": audit.get("missing_yield_count"),
            "directory_without_aggregate_count": audit.get("directory_without_aggregate_count"),
            "citation_local_summary_count": audit.get("citation_local_summary_count"),
            "blocking_count": audit.get("blocking_count"),
            "warning_count": audit.get("warning_count"),
            "ignored_non_navigation_literal_count": audit.get("ignored_non_navigation_literal_count"),
            "debt_class_counts": audit.get("debt_class_counts"),
            "field_split": audit.get("field_split"),
            "authority_posture": audit.get("authority_posture"),
            "scanned_surfaces": audit.get("scanned_surfaces"),
            "findings": compact_findings,
            "trimmed_for_metabolism_budget": True,
        }
    if _json_bytes(packet) > budget_bytes:
        packet["debt_rows"] = _priority_trim_debt_rows(
            packet.get("debt_rows", []),
            limit=10,
            required_active_class=bottleneck_class,
        )
        packet["top_repairs"] = packet.get("top_repairs", [])[:3]
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("observation_sources"), Mapping):
        sources = packet.get("observation_sources") or {}
        # Preserve the agent_path_events closure-marker fields the imn_008
        # retirement_trigger and downstream consumers depend on. Generic trim
        # keeps `status` plus a small status-shape; agent_path_events also
        # keeps the explicit observed counts so closure detection survives.
        kept_keys_generic = (
            "status",
            "summary",
            "contract_status",
            "over_budget_count",
            "disallowed_stale_route_hit_count",
            "generated_target_scan_status",
            "debt_count",
            "contract_violation_count",
            "reason",
            "fitness_mode",
            "suite",
            "task_count",
            "debt_candidate_count",
            "route_type_metrics",
            "candidate_count",
            "validated_count",
            "accepted_count",
            "projected_count",
            "observed_count",
            "authority_posture",
            "stale",
            "artifact_path",
            "source_coupling",
            "safe_alternative",
        )
        kept_keys_agent_path = kept_keys_generic + (
            "supplied_event_count",
            "supplied_event_count_semantics",
            "process_audit_status",
            "process_audit_observed_session_count",
            "process_audit_session_count",
            "process_audit_behavior_row_count",
            "process_audit_active_behavior_debt_count",
            "process_audit_retired_behavior_debt_count",
            "process_audit_pattern_classes",
            "sentrux_provenance",
        )
        kept_keys_observed_retirement = kept_keys_generic + (
            "observed_anti_pattern_ids",
            "observed_anti_pattern_count",
            "retired_debt_count",
            "retired_debt_ids",
            "active_debt_policy",
            "authority",
        )
        new_sources: dict[str, Any] = {}
        for key, value in sources.items():
            if not isinstance(value, Mapping):
                continue
            if key == "agent_path_events":
                keep_keys = kept_keys_agent_path
            elif key == "observed_mechanism_debt_retirement":
                keep_keys = kept_keys_observed_retirement
            else:
                keep_keys = kept_keys_generic
            new_sources[key] = {
                keep: value.get(keep)
                for keep in keep_keys
                if keep in value
            }
        packet["observation_sources"] = new_sources
    if _json_bytes(packet) > budget_bytes:
        compact_rows: list[dict[str, Any]] = []
        for row in _priority_trim_debt_rows(
            packet.get("debt_rows", []),
            limit=8,
            required_active_class=bottleneck_class,
        ):
            if not isinstance(row, Mapping):
                continue
            compact = {
                "debt_id": row.get("debt_id"),
                "debt_class": row.get("debt_class"),
                "priority": row.get("priority"),
                "title": row.get("title"),
                "repair_class": row.get("repair_class"),
                "source_surface": row.get("source_surface"),
                "safe_alternative": row.get("safe_alternative"),
                "library_reference_only": row.get("library_reference_only"),
                "active_debt": row.get("active_debt"),
                "advisory_only": row.get("advisory_only"),
                "retired_by_navigation_mechanism_observation": row.get(
                    "retired_by_navigation_mechanism_observation"
                ),
                "navigation_mechanism_claim_id": row.get("navigation_mechanism_claim_id"),
                "compatibility_behavior": row.get("compatibility_behavior"),
                "better_first_surface": row.get("better_first_surface"),
                "anti_pattern": row.get("anti_pattern"),
                "task_id": row.get("task_id"),
                "failure_kind": row.get("failure_kind"),
                "route_role": row.get("route_role"),
                "slow_stage": row.get("slow_stage"),
                "fitness_mode": row.get("fitness_mode"),
                "hidden_expected_artifacts": row.get("hidden_expected_artifacts"),
                "target_files": row.get("target_files"),
                "owner_surface": row.get("owner_surface"),
                "owner_status_command": row.get("owner_status_command"),
                "authoritative_decision_command": row.get("authoritative_decision_command"),
                "source_projection_boundary": row.get("source_projection_boundary"),
                "source_coupling_status": row.get("source_coupling_status"),
                "dirty_source_paths": row.get("dirty_source_paths"),
                "safe_to_commit_generated_outputs_without_sources": row.get(
                    "safe_to_commit_generated_outputs_without_sources"
                ),
            }
            compact_rows.append({key: value for key, value in compact.items() if value not in (None, "", [], {})})
        packet["debt_rows"] = compact_rows
        packet["top_repairs"] = packet.get("top_repairs", [])[:2]
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("annex_movement_pressure_map"), Mapping):
        pressure = packet.get("annex_movement_pressure_map") or {}
        packet["annex_movement_pressure_map"] = {
            "kind": pressure.get("kind"),
            "summary": pressure.get("summary"),
            "quality_signal": pressure.get("quality_signal"),
            "pressure_rows": [
                {
                    "slug": row.get("slug"),
                    "lane": row.get("lane"),
                    "evidence_paths": list(row.get("evidence_paths") or [])[:2],
                }
                for row in list(pressure.get("pressure_rows") or [])[:5]
                if isinstance(row, Mapping)
            ],
            "trimmed_for_metabolism_budget": True,
        }
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("annex_navigation_dogfood"), Mapping):
        dogfood = packet.get("annex_navigation_dogfood") or {}
        packet["annex_navigation_dogfood"] = {
            "kind": dogfood.get("kind"),
            "summary": dogfood.get("summary"),
            "compressed_comprehension": dogfood.get("compressed_comprehension"),
            "trimmed_for_metabolism_budget": True,
        }
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("command_node_cache"), Mapping):
        cache = packet.get("command_node_cache") or {}
        packet["command_node_cache"] = {
            key: {
                "status": value.get("status"),
                "reason": value.get("reason"),
                "age_s": value.get("age_s"),
                "ttl_s": value.get("ttl_s"),
                "freshness_policy": value.get("freshness_policy"),
                "dynamic_inputs_manifested": value.get("dynamic_inputs_manifested"),
            }
            for key, value in cache.items()
            if isinstance(value, Mapping)
        }
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("hook_shadow_coverage"), Mapping):
        hook_shadow = packet.get("hook_shadow_coverage") or {}
        packet["hook_shadow_coverage"] = {
            "status": hook_shadow.get("status"),
            "authority": hook_shadow.get("authority"),
            "hook_shadow_coverage_top_patterns": hook_shadow.get("hook_shadow_coverage_top_patterns"),
            "would_intervene_on_recent_route_failures": hook_shadow.get("would_intervene_on_recent_route_failures"),
            "trimmed_for_metabolism_budget": True,
        }
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("navigation_mechanism_metabolism"), Mapping):
        mechanism = dict(packet.get("navigation_mechanism_metabolism") or {})
        rows = [row for row in mechanism.get("top_candidate_claims") or [] if isinstance(row, Mapping)]
        keep: list[Mapping[str, Any]] = []

        def append_row(row: Mapping[str, Any]) -> None:
            if row not in keep:
                keep.append(row)

        for row in rows:
            if len(keep) >= 1:
                break
            append_row(row)
        for row in rows:
            if row.get("claim_id") == "mpc_9008b18dd3f052e2" and row not in keep:
                append_row(row)
                break
        if int(mechanism.get("projected_count") or 0) > int(mechanism.get("observed_count") or 0):
            for row in rows:
                future_observation = (
                    row.get("future_observation")
                    if isinstance(row.get("future_observation"), Mapping)
                    else {}
                )
                missing_refs = {str(value) for value in row.get("missing_refs") or []}
                if (
                    row.get("state") == "projected"
                    or future_observation.get("status") == "pending"
                    or "future_observation_window_unverified" in missing_refs
                ):
                    append_row(row)
                    break
        mechanism["top_candidate_claims"] = list(keep)[:3]
        mechanism["trimmed_for_metabolism_budget"] = True
        packet["navigation_mechanism_metabolism"] = mechanism
    if _json_bytes(packet) > budget_bytes and isinstance(packet.get("path_reference_reading_yield_audit"), Mapping):
        audit = packet.get("path_reference_reading_yield_audit") or {}
        packet["path_reference_reading_yield_audit"] = {
            "status": audit.get("status"),
            "mode": audit.get("mode"),
            "scanned_surface_count": audit.get("scanned_surface_count"),
            "decision_bearing_route_count": audit.get("decision_bearing_route_count"),
            "resolved_owner_count": audit.get("resolved_owner_count"),
            "resolved_yield_count": audit.get("resolved_yield_count"),
            "mapped_equivalent_count": audit.get("mapped_equivalent_count"),
            "missing_yield_count": audit.get("missing_yield_count"),
            "directory_without_aggregate_count": audit.get("directory_without_aggregate_count"),
            "citation_local_summary_count": audit.get("citation_local_summary_count"),
            "blocking_count": audit.get("blocking_count"),
            "warning_count": audit.get("warning_count"),
            "debt_class_counts": audit.get("debt_class_counts"),
            "field_split": audit.get("field_split"),
            "authority_posture": audit.get("authority_posture"),
            "scanned_surfaces": audit.get("scanned_surfaces"),
            "trimmed_for_metabolism_budget": True,
            "findings_omitted_for_budget": True,
        }
    if _json_bytes(packet) > budget_bytes:
        packet["source_surfaces"] = packet.get("source_surfaces", [])[:4]
        packet["next_commands"] = packet.get("next_commands", [])[:8]
    packet["budget"]["trimmed_for_budget"] = True
    packet["budget"]["trim_note"] = "Rows were priority-trimmed; rerun source audits for full evidence."
    final_bytes = _json_bytes(packet)
    packet["budget"]["estimated_tokens"] = max(1, (final_bytes + 3) // 4)
    # Tell the truth about the budget contract. _budget_trim is a best-effort
    # row-trimmer; it does not bound large diagnostic sub-payloads. Calling
    # the post-trim packet a `hard_ceiling` is a contract lie when the
    # estimated token count remains above the requested budget. Demote
    # hard_ceiling and label the contract honestly so cold agents reading
    # the budget block do not assume the packet sits inside their context
    # window.
    if final_bytes > budget_bytes:
        packet["budget"]["hard_ceiling"] = False
        packet["budget"]["budget_contract"] = "best_effort_trim_target"
        packet["budget"]["over_budget"] = True
        packet["budget"]["over_budget_reason"] = (
            "sub_payloads_preserved_for_diagnostic_drilldown"
        )
    else:
        packet["budget"]["budget_contract"] = "trimmed_within_budget"
        packet["budget"]["over_budget"] = False
    # Bind the summary to what is actually in the packet after trim so the
    # agent does not read summary.<class>=N and find <<N drilldowns. Pre-trim
    # totals stay visible under *_pre_trim keys so operators still see the
    # underlying debt landscape.
    summary = packet.get("summary")
    if isinstance(summary, dict):
        post_trim_rows = [row for row in packet.get("debt_rows", []) if isinstance(row, Mapping)]
        post_trim_active_rows = _active_debt_rows(post_trim_rows)
        summary["total_debt_rows_pre_trim"] = summary.get("total_debt_rows")
        summary["total_debt_rows_after_trim"] = len(post_trim_active_rows)
        summary["advisory_debt_rows_after_trim"] = len(post_trim_rows) - len(post_trim_active_rows)
        bottleneck = str(summary.get("quality_signal_bottleneck") or "")
        summary["bottleneck_drilldowns_in_packet"] = sum(
            1
            for row in post_trim_active_rows
            if str(row.get("debt_class") or "") == bottleneck
        )
        if bottleneck and int(summary.get(bottleneck) or 0) > 0:
            summary["bottleneck_drilldown_status"] = (
                "available_in_packet"
                if int(summary["bottleneck_drilldowns_in_packet"]) > 0
                else "missing_after_trim"
            )
        elif bottleneck:
            summary["bottleneck_drilldown_status"] = "no_active_bottleneck_rows"
    return packet


def _compact_mapping_keys(source: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    return {
        key: source.get(key)
        for key in keys
        if source.get(key) not in (None, "", [], {})
    }


def _compact_navigation_mechanism_for_cli(source: Mapping[str, Any]) -> dict[str, Any]:
    top_claims: list[dict[str, Any]] = []
    for row in list(source.get("top_candidate_claims") or [])[:2]:
        if not isinstance(row, Mapping):
            continue
        future = row.get("future_observation") if isinstance(row.get("future_observation"), Mapping) else {}
        compact = _compact_mapping_keys(
            row,
            (
                "claim_id",
                "anti_pattern_id",
                "state",
                "next_owner_surface",
                "validation_status",
                "replay_status",
                "latest_acceptance_event_type",
            ),
        )
        if future.get("status"):
            compact["future_observation_status"] = future.get("status")
        if compact:
            top_claims.append(compact)

    observed_refs: list[dict[str, Any]] = []
    for row in list(source.get("observed_claim_refs") or [])[:8]:
        if not isinstance(row, Mapping):
            continue
        compact = _compact_mapping_keys(row, ("claim_id", "anti_pattern_id", "state"))
        if compact:
            observed_refs.append(compact)

    compact = _compact_mapping_keys(
        source,
        (
            "status",
            "reason",
            "candidate_count",
            "validated_count",
            "accepted_count",
            "projected_count",
            "observed_count",
            "authority_posture",
            "validation_status",
            "replay_status",
            "option_surface_command",
            "validator_command",
            "factory_command",
            "replay_command",
        ),
    )
    if source.get("observed_anti_pattern_ids"):
        compact["observed_anti_pattern_ids"] = list(source.get("observed_anti_pattern_ids") or [])[:8]
    if top_claims:
        compact["top_candidate_claims"] = top_claims
    if observed_refs:
        compact["observed_claim_refs"] = observed_refs
    compact["cli_compacted"] = True
    return compact


def _compact_route_lifecycle_for_cli(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    selected_rows: list[Mapping[str, Any]]
    if limit is not None and limit > 0:
        by_id: dict[str, Mapping[str, Any]] = {}
        for row in rows:
            if isinstance(row, Mapping):
                route_id = str(row.get("route_id") or "")
                if route_id and route_id not in by_id:
                    by_id[route_id] = row
        selected_rows = []
        seen: set[str] = set()
        for route_id in _CLI_ROUTE_LIFECYCLE_PRIORITY_IDS:
            row = by_id.get(route_id)
            if row is not None:
                selected_rows.append(row)
                seen.add(route_id)
            if len(selected_rows) >= limit:
                break
        if len(selected_rows) < limit:
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                route_id = str(row.get("route_id") or "")
                if route_id in seen:
                    continue
                selected_rows.append(row)
                seen.add(route_id)
                if len(selected_rows) >= limit:
                    break
    else:
        selected_rows = [row for row in rows if isinstance(row, Mapping)]

    compact_rows: list[dict[str, Any]] = []
    for row in selected_rows:
        if not isinstance(row, Mapping):
            continue
        compact = _compact_mapping_keys(
            row,
            (
                "route_id",
                "status",
                "superseded_by",
                "supported_slugs",
                "supported_slug_source",
                "generic_existing_slug_support",
            ),
        )
        if row.get("purpose"):
            compact["purpose"] = _trim(row.get("purpose"), max_chars=90)
        if row.get("compatibility_behavior"):
            compact["compatibility_behavior"] = _trim(row.get("compatibility_behavior"), max_chars=90)
        if row.get("entry_condition"):
            compact["entry_condition"] = _trim(row.get("entry_condition"), max_chars=90)
        residual_lanes = row.get("residual_lanes")
        if isinstance(residual_lanes, Sequence) and not isinstance(residual_lanes, (str, bytes, bytearray)):
            compact["residual_lanes"] = [
                _compact_mapping_keys(lane, ("lane_id", "status", "entry_command_template"))
                for lane in residual_lanes
                if isinstance(lane, Mapping)
            ][:2]
        owner_surfaces = row.get("owner_surfaces")
        if isinstance(owner_surfaces, Sequence) and not isinstance(owner_surfaces, (str, bytes, bytearray)):
            compact["owner_surfaces"] = [
                _compact_mapping_keys(surface, ("surface_id", "template"))
                for surface in owner_surfaces
                if isinstance(surface, Mapping)
            ][:2]
        if row.get("write_guard"):
            compact["write_guard"] = _trim(row.get("write_guard"), max_chars=90)
        compact_rows.append({key: value for key, value in compact.items() if value not in (None, "", [], {})})
    return compact_rows


def _route_lifecycle_cli_summary(
    rows: Sequence[Mapping[str, Any]],
    emitted_rows: Sequence[Mapping[str, Any]],
    *,
    full_evidence_route: str | None,
) -> dict[str, Any]:
    route_ids: list[str] = []
    status_counts: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        route_id = str(row.get("route_id") or "")
        if route_id:
            route_ids.append(route_id)
        status = str(row.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    emitted_ids = {
        str(row.get("route_id") or "")
        for row in emitted_rows
        if isinstance(row, Mapping) and row.get("route_id")
    }
    omitted_ids = [route_id for route_id in route_ids if route_id not in emitted_ids]
    summary: dict[str, Any] = {
        "total_rows": len(route_ids),
        "emitted_rows": len(emitted_ids),
        "omitted_rows": len(omitted_ids),
        "status_counts": dict(sorted(status_counts.items())),
        "compression_policy": "quick_cli_prioritized_slice_static_lifecycle_summary",
    }
    if omitted_ids:
        summary["omitted_route_ids_preview"] = omitted_ids[:8]
    if full_evidence_route:
        summary["full_evidence_route"] = full_evidence_route
    return summary


def _compact_observation_sources_for_cli(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}

    compact: dict[str, Any] = {}
    for key, source in value.items():
        if not isinstance(source, Mapping):
            continue
        if key == "agent_path_events":
            row = _compact_mapping_keys(
                source,
                (
                    "status",
                    "supplied_event_count",
                    "process_audit_status",
                    "process_audit_observed_session_count",
                    "process_audit_behavior_row_count",
                    "process_audit_active_behavior_debt_count",
                    "process_audit_retired_behavior_debt_count",
                ),
            )
            if source.get("process_audit_pattern_classes"):
                row["process_audit_pattern_classes"] = list(source.get("process_audit_pattern_classes") or [])[:6]
            if source.get("sentrux_provenance"):
                row["sentrux_provenance"] = list(source.get("sentrux_provenance") or [])[:3]
            compact[key] = row
            continue
        if key == "observed_mechanism_debt_retirement":
            compact[key] = _compact_mapping_keys(
                source,
                (
                    "status",
                    "observed_anti_pattern_count",
                    "retired_debt_count",
                    "authority",
                ),
            )
            continue
        if key == "annex_currentness":
            summary = source.get("summary")
            row = _compact_mapping_keys(source, ("status",))
            if isinstance(summary, Mapping):
                row["summary"] = _compact_mapping_keys(
                    summary,
                    (
                        "digest_status",
                        "attention_count",
                        "stale_count",
                        "sync_status",
                        "sync_failure_count",
                        "currentness_debt",
                        "projection_freshness_status",
                        "movement_to_row_job_status",
                        "movement_to_row_job_gap_count",
                        "bucket_counts",
                    ),
                )
            compact[key] = row
            continue
        if key == "annex_movement_pressure_map":
            summary = source.get("summary")
            row = _compact_mapping_keys(source, ("status",))
            if isinstance(summary, Mapping):
                row["summary"] = _compact_mapping_keys(
                    summary,
                    (
                        "row_count",
                        "selected_row_job_count",
                        "missing_report_count",
                        "unclassified_count",
                        "source_job_blocker_count",
                        "blocker_routing_count",
                        "source_row_job_count",
                        "source_classification_counts",
                    ),
                )
            compact[key] = row
            continue
        if key == "routing_projection_status":
            row = _compact_mapping_keys(source, ("status", "stale", "artifact_path", "safe_alternative"))
            source_coupling = source.get("source_coupling")
            if isinstance(source_coupling, Mapping):
                row["source_coupling"] = _compact_mapping_keys(
                    source_coupling,
                    ("status", "safe_to_commit_generated_outputs_without_sources"),
                )
            compact[key] = row
            continue
        if key == "clusterability":
            row = _compact_mapping_keys(source, ("status",))
            summary = source.get("summary")
            if isinstance(summary, Mapping):
                row["summary"] = _compact_mapping_keys(summary, ("debt_count",))
            compact[key] = row
            continue
        compact[key] = _compact_mapping_keys(
            source,
            (
                "status",
                "contract_status",
                "reason",
                "safe_alternative",
                "authority",
                "accepted_count",
                "projected_count",
                "observed_count",
                "validated_count",
                "candidate_count",
            ),
        )
    return {key: row for key, row in compact.items() if row}


def _compact_debt_row_for_cli(row: Mapping[str, Any]) -> dict[str, Any]:
    compact = _compact_mapping_keys(
        row,
        (
            "debt_id",
            "debt_class",
            "priority",
            "title",
            "repair_class",
            "source_surface",
            "safe_alternative",
            "library_reference_only",
            "active_debt",
            "advisory_only",
            "retired_by_navigation_mechanism_observation",
            "navigation_mechanism_claim_id",
            "compatibility_behavior",
            "better_first_surface",
            "anti_pattern",
            "task_id",
            "failure_kind",
            "route_role",
            "slow_stage",
            "fitness_mode",
            "owner_surface",
            "owner_status_command",
            "authoritative_decision_command",
            "source_coupling_status",
            "source_freshness",
        ),
    )
    if compact.get("title"):
        compact["title"] = _trim(compact["title"], max_chars=120)
    if compact.get("compatibility_behavior"):
        compact["compatibility_behavior"] = _trim(compact["compatibility_behavior"], max_chars=120)
    if row.get("target_files"):
        compact["target_files"] = list(row.get("target_files") or [])[:3]
    boundary = row.get("source_projection_boundary")
    if isinstance(boundary, Mapping):
        compact["source_projection_boundary"] = _compact_mapping_keys(
            boundary,
            (
                "process_audit_policy",
                "patch_selection_policy",
                "owner_status_route",
                "authoritative_decision_route",
                "owner_card_route",
            ),
        )
    freshness = row.get("source_freshness")
    if isinstance(freshness, Mapping):
        compact["source_freshness"] = _compact_mapping_keys(
            freshness,
            (
                "status",
                "cache_status",
                "age_s",
                "ttl_s",
                "patch_selection_policy",
                "authoritative_decision_command",
            ),
        )
    return {key: value for key, value in compact.items() if value not in (None, "", [], {})}


def _compact_top_repair_for_cli(row: Mapping[str, Any]) -> dict[str, Any]:
    compact = _compact_debt_row_for_cli(row)
    if row.get("tests"):
        compact["tests"] = list(row.get("tests") or [])[:1]
    if row.get("repair_hints"):
        compact["repair_hints"] = _compact_repair_hints(row.get("repair_hints"), limit=2)
    for key in ("preferred_next", "process_bottleneck_drilldown"):
        if row.get(key):
            compact[key] = row.get(key)
    return compact


def compact_quick_navigation_metabolism_packet_for_cli(
    packet: Mapping[str, Any],
    *,
    context_budget: int,
) -> dict[str, Any]:
    """Return the quick metabolism packet shape suitable for CLI first contact.

    The library builder intentionally keeps rich in-memory evidence for tests
    and drilldowns. The CLI default should be a bounded control packet; full
    evidence remains reachable through sidecar/full-profile routes.
    """
    if str(packet.get("metabolism_profile") or "") != "quick":
        return dict(packet)

    target_tokens = min(max(1000, int(context_budget or 12000)), QUICK_CLI_OUTPUT_TARGET_TOKENS)
    target_bytes = target_tokens * 4
    if _json_bytes(packet) <= target_bytes:
        return dict(packet)

    compact = dict(packet)
    compact["debt_rows"] = [
        _compact_debt_row_for_cli(row)
        for row in _priority_trim_debt_rows(
            compact.get("debt_rows", []),
            limit=8,
            required_active_class=_packet_bottleneck_debt_class(compact),
        )
        if isinstance(row, Mapping)
    ]
    compact["top_repairs"] = [
        _compact_top_repair_for_cli(row)
        for row in list(compact.get("top_repairs") or [])[:2]
        if isinstance(row, Mapping)
    ]
    route_lifecycle_rows = [row for row in compact.get("route_lifecycle", []) if isinstance(row, Mapping)]
    compact["route_lifecycle"] = _compact_route_lifecycle_for_cli(
        route_lifecycle_rows,
        limit=QUICK_CLI_ROUTE_LIFECYCLE_ROW_LIMIT,
    )
    full_profile_drilldown = (
        (compact.get("strategy") or {}).get("full_profile_drilldown")
        if isinstance(compact.get("strategy"), Mapping)
        else None
    )
    compact["route_lifecycle_summary"] = _route_lifecycle_cli_summary(
        route_lifecycle_rows,
        [row for row in compact.get("route_lifecycle", []) if isinstance(row, Mapping)],
        full_evidence_route=full_profile_drilldown,
    )
    if isinstance(compact.get("navigation_mechanism_metabolism"), Mapping):
        compact["navigation_mechanism_metabolism"] = _compact_navigation_mechanism_for_cli(
            compact["navigation_mechanism_metabolism"]
        )
    if isinstance(compact.get("entrypoint_health"), Mapping):
        entrypoint = compact.get("entrypoint_health") or {}
        compact["entrypoint_health"] = {
            "kind": entrypoint.get("kind"),
            "schema_version": entrypoint.get("schema_version"),
            "summary": entrypoint.get("summary"),
            "trimmed_for_cli_output": True,
        }
    if isinstance(compact.get("annex_currentness"), Mapping):
        currentness = compact.get("annex_currentness") or {}
        compact["annex_currentness"] = {
            "kind": currentness.get("kind"),
            "schema_version": currentness.get("schema_version"),
            "summary": currentness.get("summary"),
            "source": currentness.get("source"),
            "trimmed_for_cli_output": True,
        }
    if isinstance(compact.get("annex_movement_pressure_map"), Mapping):
        pressure = compact.get("annex_movement_pressure_map") or {}
        compact["annex_movement_pressure_map"] = {
            "kind": pressure.get("kind"),
            "schema_version": pressure.get("schema_version"),
            "summary": pressure.get("summary"),
            "quality_signal": pressure.get("quality_signal"),
            "trimmed_for_cli_output": True,
        }
    if isinstance(compact.get("hook_shadow_coverage"), Mapping):
        hook = compact.get("hook_shadow_coverage") or {}
        compact["hook_shadow_coverage"] = _compact_mapping_keys(
            hook,
            (
                "status",
                "authority",
                "hook_shadow_coverage_top_patterns",
                "would_intervene_on_recent_route_failures",
            ),
        )
    compact["annex_intake"] = [
        _compact_mapping_keys(row, ("annex", "status", "import_status", "ratchet_mapped_pattern_count"))
        for row in list(compact.get("annex_intake") or [])[:3]
        if isinstance(row, Mapping)
    ]
    compact["observation_sources"] = _compact_observation_sources_for_cli(compact.get("observation_sources"))
    compact["next_commands"] = list(compact.get("next_commands") or [])[:7]
    compact["source_surfaces"] = list(compact.get("source_surfaces") or [])[:5]

    budget = dict(compact.get("budget") or {})
    budget["cli_compacted_for_output"] = True
    budget["cli_compaction_target_tokens"] = target_tokens
    budget["cli_compaction_target_bytes"] = target_bytes
    budget["full_evidence_routes"] = [
        full_profile_drilldown,
        "./repo-python kernel.py --command-profile navigation-metabolism --metabolism-profile quick --context-budget 12000",
    ]
    budget["full_evidence_routes"] = [route for route in budget["full_evidence_routes"] if route]
    compact["budget"] = budget

    for limit in (6, 4):
        if _json_bytes(compact) <= target_bytes:
            break
        compact["debt_rows"] = compact.get("debt_rows", [])[:limit]
        compact["top_repairs"] = compact.get("top_repairs", [])[:1]
    if _json_bytes(compact) > target_bytes and isinstance(compact.get("observation_sources"), Mapping):
        sources = compact.get("observation_sources") or {}
        compact["observation_sources"] = {
            key: value
            for key, value in sources.items()
            if key
            in {
                "entrypoint_health",
                "command_latency",
                "agent_path_events",
                "navigation_mechanism_metabolism",
                "observed_mechanism_debt_retirement",
                "clusterability",
                "annex_currentness",
                "annex_movement_pressure_map",
            }
        }
    if _json_bytes(compact) > target_bytes and isinstance(compact.get("navigation_mechanism_metabolism"), Mapping):
        mechanism = dict(compact.get("navigation_mechanism_metabolism") or {})
        mechanism.pop("top_candidate_claims", None)
        mechanism.pop("observed_claim_refs", None)
        compact["navigation_mechanism_metabolism"] = mechanism

    final_bytes = _json_bytes(compact)
    budget = dict(compact.get("budget") or {})
    budget["estimated_tokens"] = max(1, (final_bytes + 3) // 4)
    budget["estimated_output_bytes"] = final_bytes
    budget["cli_compaction_target_bytes"] = target_bytes
    budget["over_budget"] = final_bytes > target_bytes
    budget["over_budget_basis"] = "json_bytes_vs_advertised_token_target"
    budget["budget_contract"] = (
        "cli_compacted_within_budget" if final_bytes <= target_bytes else "cli_compacted_best_effort"
    )
    budget["hard_ceiling"] = final_bytes <= target_bytes
    if final_bytes <= target_bytes:
        budget.pop("over_budget_reason", None)
    compact["budget"] = budget

    summary = compact.get("summary")
    if isinstance(summary, dict):
        rows = [row for row in compact.get("debt_rows", []) if isinstance(row, Mapping)]
        active_rows = _active_debt_rows(rows)
        summary["total_debt_rows_after_cli_compaction"] = len(active_rows)
        bottleneck = str(summary.get("quality_signal_bottleneck") or "")
        if bottleneck:
            summary["bottleneck_drilldowns_in_packet"] = sum(
                1 for row in active_rows if str(row.get("debt_class") or "") == bottleneck
            )
    return compact


def _build_quick_navigation_metabolism_ledger(
    root: Path,
    *,
    query: str,
    context_budget: int,
    behavior_events: Sequence[Mapping[str, Any]] | None = None,
    fitness_payload: Mapping[str, Any] | None = None,
    profile_sink: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    started = perf_counter()
    phase_profile = profile_sink if profile_sink is not None else []
    allow_cache_build = _command_cache_refresh_requested()
    budget = max(1000, int(context_budget or 12000))
    entrypoint_health = _profile_phase(
        phase_profile,
        "entrypoint_health",
        lambda: build_entrypoint_health(root, include_generated_targets=False),
    )
    command_node_cache: dict[str, Any] = {}
    clusterability, command_node_cache["clusterability"] = _profile_phase(
        phase_profile,
        "clusterability",
        lambda: _cached_clusterability_quick(
            root,
            budget=budget,
            allow_build=False,
        ),
    )
    annex_currentness = _profile_phase(
        phase_profile,
        "annex_currentness",
        lambda: build_annex_currentness(
            root,
            context_budget=budget,
            include_projection_freshness=False,
        ),
    )
    annex_movement_pressure = _profile_phase(
        phase_profile,
        "annex_movement_pressure_map",
        lambda: build_annex_movement_pressure_map(
            root,
            query=query,
            context_budget=budget,
        ),
    )
    route_lifecycle = _profile_phase(phase_profile, "route_lifecycle", _route_lifecycle_rows)
    annex_intake, annex_debt = _profile_phase(phase_profile, "annex_intake", lambda: _annex_intake_rows(root))

    process_audit, command_node_cache["process_audit"] = _profile_phase(
        phase_profile,
        "process_audit",
        lambda: _cached_process_audit_payload(root, allow_build=allow_cache_build),
    )
    hook_shadow_coverage = _profile_phase(
        phase_profile,
        "hook_shadow_coverage",
        lambda: build_hook_shadow_coverage(
            process_audit,
            process_repairs=_PROCESS_PATTERN_REPAIRS,
        ),
    )
    (
        navigation_mechanism_metabolism,
        command_node_cache["navigation_mechanism_metabolism"],
    ) = _profile_phase(
        phase_profile,
        "navigation_mechanism_metabolism",
        lambda: _cached_navigation_mechanism_metabolism(root, process_audit, allow_build=allow_cache_build),
    )
    actor_delivery_receipt, command_node_cache["actor_delivery_receipt"] = _profile_phase(
        phase_profile,
        "actor_delivery_receipt",
        lambda: _cached_actor_delivery_receipt(root, allow_build=False),
    )
    phase_summary_projection_status, command_node_cache["phase_summary_projection_status"] = _profile_phase(
        phase_profile,
        "phase_summary_projection_status",
        lambda: _cached_phase_summary_projection_status(root, context_budget=budget, allow_build=False),
    )
    routing_projection_status, command_node_cache["routing_projection_status"] = _profile_phase(
        phase_profile,
        "routing_projection_status",
        lambda: _cached_routing_projection_status(root, allow_build=False),
    )
    profile_total_ms = round((perf_counter() - started) * 1000, 3)
    latency_profile = _latency_profile(
        phase_profile,
        total_ms=profile_total_ms,
        phase_warn_ms=QUICK_PROFILE_PHASE_WARN_MS,
        total_warn_ms=QUICK_PROFILE_TOTAL_WARN_MS,
    )

    debt_rows: list[dict[str, Any]] = []
    debt_started = perf_counter()
    debt_rows.extend(_entrypoint_debt_rows(entrypoint_health))
    debt_rows.extend(_actor_delivery_debt_rows(actor_delivery_receipt))
    debt_rows.extend(_quick_authoring_debt_rows(root))
    debt_rows.extend(_quick_projection_debt_rows(phase_summary_projection_status))
    debt_rows.extend(_routing_source_coupling_debt_rows(routing_projection_status))
    debt_rows.extend(_clusterability_debt_rows(clusterability))
    debt_rows.extend(_annex_currentness_debt_rows(annex_currentness))
    debt_rows.extend(_annex_movement_pressure_debt_rows(annex_movement_pressure))
    if fitness_payload is not None:
        debt_rows.extend(_fitness_debt_rows(fitness_payload))
    debt_rows.extend(
        _latency_profile_debt_rows(
            phase_profile,
            surface="navigation_metabolism.quick",
            total_ms=profile_total_ms,
            phase_warn_ms=QUICK_PROFILE_PHASE_WARN_MS,
            total_warn_ms=QUICK_PROFILE_TOTAL_WARN_MS,
        )
    )
    debt_rows.extend(
        _annotate_process_audit_source_freshness(
            _process_audit_behavior_rows(process_audit),
            command_node_cache.get("process_audit"),
        )
    )
    debt_rows, observed_mechanism_debt_retirement = _retire_observed_navigation_mechanism_debt_rows(
        debt_rows,
        navigation_mechanism_metabolism,
    )
    debt_rows.extend(normalize_agent_route_events(list(behavior_events or [])))
    skill_find_policy = _skill_find_debug_trace_policy_receipt()
    _append_skill_find_policy_gap_if_needed(
        debt_rows,
        policy_receipt=skill_find_policy,
        source_surface="navigation_metabolism.quick_profile",
        evidence="Quick profile keeps route-policy gaps visible only when the DEBUG_TRACE contract is not hardened.",
    )
    debt_rows.extend(annex_debt)
    debt_rows.extend(_layer_sprawl_rows(route_lifecycle))
    debt_rows = sorted(debt_rows, key=lambda row: int(row.get("priority") or 0), reverse=True)
    counts = _count_by_class(debt_rows)
    active_debt_rows = _active_debt_rows(debt_rows)
    top_repairs = _top_repairs(debt_rows, limit=8)
    fitness_source = {
        "status": "deferred_by_quick_profile",
        "reason": "quick profile is first-contact-safe; run --navigation-fitness or --metabolism-profile full for detailed fitness ingestion",
    }
    if fitness_payload is not None:
        fitness_source = {
            "status": "caller_supplied",
            "suite": fitness_payload.get("suite"),
            "fitness_mode": (fitness_payload.get("strategy") or {}).get("fitness_mode"),
            "task_count": (fitness_payload.get("summary") or {}).get("task_count"),
            "debt_candidate_count": (fitness_payload.get("summary") or {}).get("debt_candidate_count"),
            "route_type_metrics": fitness_payload.get("route_type_metrics"),
        }
    quality_signal = _quality_signal(
        counts,
        process_audit_status=str(process_audit.get("status") or "unavailable"),
    )
    quality_signal["source_freshness"]["process_audit_cache"] = _process_audit_cache_authority(
        command_node_cache.get("process_audit")
    )
    if phase_profile is not None:
        phase_profile.append(
            {
                "phase": "quick_debt_row_synthesis",
                "ms": round((perf_counter() - debt_started) * 1000, 3),
                "debt_row_count": len(debt_rows),
                "active_debt_row_count": len(active_debt_rows),
            }
        )
    packet_started = perf_counter()
    packet: dict[str, Any] = {
        "kind": "navigation_metabolism_ledger",
        "schema_version": "navigation_metabolism_ledger_v0",
        "generated_at": _utc_now(),
        "query": query,
        "metabolism_profile": "quick",
        "budget": {
            "context_budget_tokens": budget,
            "hard_ceiling": True,
            "estimated_tokens": 0,
            "trimmed_for_budget": False,
        },
        "quality_signal": quality_signal,
        "summary": {
            **counts,
            "total_debt_rows": len(active_debt_rows),
            "advisory_debt_rows": len(debt_rows) - len(active_debt_rows),
            "total_rows_including_advisory": len(debt_rows),
            "top_repair_count": len(top_repairs),
            "quality_signal_score": quality_signal["score"],
            "quality_signal_bottleneck": quality_signal["bottleneck_debt_class"],
        },
        "strategy": {
            "single_ratchet": True,
            "profile": "quick",
            "first_contact_safe": True,
            "full_profile_drilldown": f"./repo-python kernel.py --navigation-metabolism {json.dumps(query)} --metabolism-profile full --context-budget {budget}",
            "inputs_are_narrow_audits_not_new_authorities": True,
            "command_node_cache": "enabled_for_repeated_quick_substrate_nodes",
            "latency_profile": "enabled",
        },
        "command_node_cache": command_node_cache,
        "latency_profile": latency_profile,
        "observation_sources": {
            "surface_authoring_audit": {"status": "deferred_by_quick_profile"},
            "navigation_surface_audit": {"status": "deferred_by_quick_profile"},
            "phase_summary_projection_status": phase_summary_projection_status,
            "routing_projection_status": {
                "status": routing_projection_status.get("status") or "available",
                "stale": routing_projection_status.get("stale"),
                "artifact_path": routing_projection_status.get("artifact_path"),
                "source_coupling": routing_projection_status.get("source_coupling"),
                "reason": routing_projection_status.get("reason"),
                "safe_alternative": routing_projection_status.get("safe_alternative"),
            },
            "path_reference_reading_yield_audit": {
                "status": "deferred_by_quick_profile",
                "reason": "read-only path-reference proof runs only in full profile",
            },
            "skill_find_debug_trace_policy": skill_find_policy,
            "entrypoint_health": {
                "status": "available",
                "contract_status": (entrypoint_health.get("summary") or {}).get("contract_status"),
                "over_budget_count": (entrypoint_health.get("summary") or {}).get("over_budget_count"),
                "generated_target_scan_status": (
                    entrypoint_health.get("summary") or {}
                ).get("generated_target_scan_status"),
            },
            "actor_delivery_receipt": {
                "status": actor_delivery_receipt.get("status") or "available",
                "ok": actor_delivery_receipt.get("ok"),
                "required_delivery_route_count": actor_delivery_receipt.get("required_delivery_route_count"),
                "total_situation_route_count": actor_delivery_receipt.get("total_situation_route_count"),
                "actor_delivery_decision_count": actor_delivery_receipt.get("actor_delivery_decision_count"),
                "unknown_delivery_decision_count": actor_delivery_receipt.get("unknown_delivery_decision_count"),
                "warning_count": len(actor_delivery_receipt.get("warnings") or []),
                "blocker_count": len(actor_delivery_receipt.get("blockers") or []),
            },
            "agent_path_events": {
                "status": (
                    "process_audit_consumed"
                    if str(process_audit.get("status") or "") == "available"
                    else "fixture_or_caller_supplied"
                    if behavior_events
                    else "policy_gap_only"
                ),
                "supplied_event_count": len(behavior_events or []),
                "supplied_event_count_semantics": "caller_supplied_fixture_events_only",
                "process_audit_status": process_audit.get("status") or "unavailable",
                "process_audit_observed_session_count": int(process_audit.get("session_count") or 0),
                "process_audit_session_count": int(process_audit.get("session_count") or 0),
                "process_audit_behavior_row_count": sum(
                    1
                    for row in debt_rows
                    if isinstance(row, Mapping)
                    and row.get("debt_class") == "behavior_debt"
                    and str(row.get("source_surface") or "") == "--process-audit"
                ),
                "process_audit_active_behavior_debt_count": sum(
                    1
                    for row in debt_rows
                    if isinstance(row, Mapping)
                    and row.get("debt_class") == "behavior_debt"
                    and str(row.get("source_surface") or "") == "--process-audit"
                    and _is_active_debt_row(row)
                ),
                "process_audit_retired_behavior_debt_count": sum(
                    1
                    for row in debt_rows
                    if isinstance(row, Mapping)
                    and row.get("debt_class") == "behavior_debt"
                    and str(row.get("source_surface") or "") == "--process-audit"
                    and row.get("retired_by_navigation_mechanism_observation") is True
                ),
                "process_audit_pattern_classes": [
                    str((pattern or {}).get("pattern_id") or "")
                    for pattern in (process_audit.get("patterns") or [])
                    if isinstance(pattern, Mapping)
                ],
                "sentrux_provenance": ["p001", "p003"],
            },
            "command_latency": {
                "status": latency_profile["status"],
                "slow_phase_count": latency_profile["slow_phase_count"],
                "total_ms": latency_profile["total_ms"],
                "profile_command": latency_profile["profile_command"],
                "process_bottleneck_command": latency_profile["process_bottleneck_command"],
            },
            "hook_shadow_coverage": {
                "status": hook_shadow_coverage.get("status"),
                "hook_shadow_coverage_top_patterns": hook_shadow_coverage.get("hook_shadow_coverage_top_patterns"),
                "would_intervene_on_recent_route_failures": hook_shadow_coverage.get(
                    "would_intervene_on_recent_route_failures"
                ),
                "authority": hook_shadow_coverage.get("authority"),
            },
            "navigation_mechanism_metabolism": {
                "status": navigation_mechanism_metabolism.get("status"),
                "candidate_count": navigation_mechanism_metabolism.get("candidate_count"),
                "validated_count": navigation_mechanism_metabolism.get("validated_count"),
                "accepted_count": navigation_mechanism_metabolism.get("accepted_count"),
                "projected_count": navigation_mechanism_metabolism.get("projected_count"),
                "observed_count": navigation_mechanism_metabolism.get("observed_count"),
                "observed_anti_pattern_ids": navigation_mechanism_metabolism.get("observed_anti_pattern_ids"),
                "authority_posture": navigation_mechanism_metabolism.get("authority_posture"),
            },
            "observed_mechanism_debt_retirement": observed_mechanism_debt_retirement,
            "session_diagnostics_summary": {"status": "deferred_by_quick_profile"},
            "annex_intake": {"status": "available", "annex_count": len(annex_intake)},
            "navigation_fitness": fitness_source,
            "clusterability": {
                "status": clusterability.get("status") or "available",
                "summary": clusterability.get("summary"),
                "measure_all_rows": False,
                "drilldown_command": clusterability.get("drilldown_command"),
            },
            "annex_routing_coverage": {
                "status": "deferred_by_quick_profile",
                "reason": "quick profile keeps first-contact cheap; full profile measures annex_pattern_cluster_key coverage",
            },
            "annex_currentness": {
                "status": "available",
                "summary": annex_currentness.get("summary"),
                "source": annex_currentness.get("source"),
            },
            "annex_movement_pressure_map": {
                "status": "available",
                "summary": annex_movement_pressure.get("summary"),
                "quality_signal": annex_movement_pressure.get("quality_signal"),
            },
            "annex_navigation_dogfood": {
                "status": "deferred_by_quick_profile",
                "reason": "quick profile keeps first-contact cheap; full profile composes annex currentness, routing, row jobs, and distillation priority",
            },
        },
        "debt_rows": debt_rows,
        "top_repairs": top_repairs,
        "entrypoint_health": entrypoint_health,
        "actor_delivery_receipt": {
            "kind": actor_delivery_receipt.get("kind"),
            "ok": actor_delivery_receipt.get("ok"),
            "required_delivery_route_count": actor_delivery_receipt.get("required_delivery_route_count"),
            "total_situation_route_count": actor_delivery_receipt.get("total_situation_route_count"),
            "actor_delivery_decision_count": actor_delivery_receipt.get("actor_delivery_decision_count"),
            "deliver_to_cold_start_count": actor_delivery_receipt.get("deliver_to_cold_start_count"),
            "non_delivery_decision_count": actor_delivery_receipt.get("non_delivery_decision_count"),
            "unknown_delivery_decision_count": actor_delivery_receipt.get("unknown_delivery_decision_count"),
            "warnings": list(actor_delivery_receipt.get("warnings") or [])[:5],
            "blockers": list(actor_delivery_receipt.get("blockers") or [])[:5],
        },
        "clusterability": {
            "kind": clusterability.get("kind"),
            "status": clusterability.get("status") or "available",
            "summary": clusterability.get("summary"),
            "drilldown_command": clusterability.get("drilldown_command"),
            "rows": [
                {
                    "kind_id": row.get("kind_id"),
                    "row_count": row.get("row_count"),
                    "cluster_flag_status": row.get("cluster_flag_status"),
                    "grouping_keys_available": row.get("grouping_keys_available"),
                    "grouping_key_provenance": row.get("grouping_key_provenance"),
                    "repair_class": row.get("repair_class"),
                    "first_safe_repair": row.get("first_safe_repair"),
                }
                for row in clusterability.get("rows", [])
                if isinstance(row, Mapping)
            ],
        },
        "navigation_fitness": fitness_payload if fitness_payload is not None else None,
        "hook_shadow_coverage": hook_shadow_coverage,
        "navigation_mechanism_metabolism": navigation_mechanism_metabolism,
        "annex_currentness": {
            "kind": annex_currentness.get("kind"),
            "schema_version": annex_currentness.get("schema_version"),
            "summary": annex_currentness.get("summary"),
            "source": annex_currentness.get("source"),
            "currentness_contract": annex_currentness.get("currentness_contract"),
            "top_attention_rows": list(annex_currentness.get("top_attention_rows") or [])[:6],
            "debt_rows": list(annex_currentness.get("debt_rows") or [])[:3],
        },
        "annex_movement_pressure_map": {
            "kind": annex_movement_pressure.get("kind"),
            "schema_version": annex_movement_pressure.get("schema_version"),
            "summary": annex_movement_pressure.get("summary"),
            "quality_signal": annex_movement_pressure.get("quality_signal"),
            "pressure_rows": list(annex_movement_pressure.get("pressure_rows") or [])[:5],
        },
        "annex_intake": annex_intake,
        "route_lifecycle": route_lifecycle,
        "next_commands": [
            f"./repo-python kernel.py --navigation-metabolism {json.dumps(query)} --metabolism-profile full --context-budget {budget}",
            f"./repo-python kernel.py --coverage-enforcement-matrix {json.dumps(query)} --context-budget {budget}",
            "./repo-python kernel.py --clusterability-audit --context-budget 12000",
            "./repo-python kernel.py --annex-routing-coverage --context-budget 12000",
            "./repo-python kernel.py --annex-currentness --context-budget 12000",
            "./repo-python kernel.py --annex-movement-pressure-map \"improve annex navigation protocol\" --context-budget 12000",
            "./repo-python kernel.py --annex-navigation-dogfood \"improve annex navigation protocol\" --context-budget 12000",
            "./repo-python kernel.py --metabolism-row-jobs annex-sync-digest --limit 5",
            "./repo-python kernel.py --navigation-fitness smoke --fitness-mode cli --context-budget 12000",
            "./repo-python kernel.py --command-profile navigation-metabolism --metabolism-profile quick --context-budget 12000",
            "./repo-python kernel.py --process-bottlenecks",
            "./repo-python kernel.py --navigation-mechanism-factory --limit 20",
            "./repo-python tools/meta/factory/validate_navigation_mechanism_facets.py --limit 20 --json",
            "./repo-python kernel.py --navigation-mechanism-replay",
            "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
        ],
        "source_surfaces": [
            "system/lib/navigation_metabolism_ledger.py",
            "system/lib/navigation_clusterability.py",
            "system/lib/annex_routing_coverage.py",
            "system/lib/annex_currentness.py",
            "system/lib/annex_movement_pressure_map.py",
            "system/lib/annex_navigation_dogfood.py",
            "system/lib/entrypoint_health.py",
            "system/lib/navigation_mechanism_factory.py",
            f"annexes/{TACO_ANNEX}/distillation.json",
        ],
    }
    if phase_profile is not None:
        phase_profile.append(
            {
                "phase": "quick_packet_assembly",
                "ms": round((perf_counter() - packet_started) * 1000, 3),
            }
        )
    trim_started = perf_counter()
    trimmed_packet = _budget_trim(packet, context_budget=budget)
    if phase_profile is not None:
        try:
            output_bytes = len(json.dumps(trimmed_packet, ensure_ascii=False).encode("utf-8"))
        except TypeError:
            output_bytes = None
        phase_profile.append(
            {
                "phase": "quick_budget_trim",
                "ms": round((perf_counter() - trim_started) * 1000, 3),
                "output_bytes": output_bytes,
            }
        )
    return trimmed_packet


def build_navigation_metabolism_ledger(
    repo_root: Path | str,
    *,
    query: str | None = None,
    context_budget: int = 12000,
    behavior_events: Sequence[Mapping[str, Any]] | None = None,
    include_session_summary: bool = True,
    session_last: int = 5,
    include_fitness: bool = True,
    fitness_payload: Mapping[str, Any] | None = None,
    fitness_suite: str = "smoke",
    metabolism_profile: str = "full",
    profile_sink: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    budget = max(1000, int(context_budget or 12000))
    task_query = str(query or DEFAULT_QUERY)
    profile = str(metabolism_profile or "full").strip().lower()
    if profile not in METABOLISM_PROFILES:
        profile = "full"
    if profile == "quick":
        return _build_quick_navigation_metabolism_ledger(
            root,
            query=task_query,
            context_budget=budget,
            behavior_events=behavior_events,
            fitness_payload=fitness_payload,
            profile_sink=profile_sink,
        )

    from system.lib.annex_navigation_dogfood import build_annex_navigation_dogfood
    from system.lib.annex_routing_coverage import build_annex_routing_coverage
    from system.lib.navigation_surface_audit import build_navigation_surface_audit
    from system.lib.path_reference_reading_yield import build_path_reference_reading_yield_audit
    from system.lib.surface_authoring_audit import build_surface_authoring_audit

    surface_audit = build_surface_authoring_audit(root, context_budget=budget)
    route_audit = build_navigation_surface_audit(root, query=task_query, context_budget=budget)
    clusterability = build_navigation_clusterability_audit(
        root,
        context_budget=budget,
        measure_all_rows=True,
    )
    annex_routing_coverage = build_annex_routing_coverage(
        root,
        context_budget=budget,
    )
    annex_currentness = build_annex_currentness(
        root,
        context_budget=budget,
    )
    annex_movement_pressure = build_annex_movement_pressure_map(
        root,
        query=task_query,
        context_budget=budget,
    )
    annex_navigation_dogfood = build_annex_navigation_dogfood(
        root,
        query=task_query,
        context_budget=budget,
    )
    entrypoint_health = build_entrypoint_health(root)
    routing_projection_status, routing_projection_cache_status = _cached_routing_projection_status(
        root,
        allow_build=True,
    )
    path_reference_reading_yield_audit = build_path_reference_reading_yield_audit(
        root,
        query=task_query,
        entrypoint_health=entrypoint_health,
    )

    process_audit = _process_audit_payload(root)
    hook_shadow_coverage = build_hook_shadow_coverage(
        process_audit,
        process_repairs=_PROCESS_PATTERN_REPAIRS,
    )
    navigation_mechanism_metabolism = _navigation_mechanism_metabolism(root, process_audit)
    actor_delivery_receipt = _actor_delivery_receipt(root)

    debt_rows: list[dict[str, Any]] = []
    debt_rows.extend(_entrypoint_debt_rows(entrypoint_health))
    debt_rows.extend(_actor_delivery_debt_rows(actor_delivery_receipt))
    debt_rows.extend(_authoring_debt_rows(surface_audit))
    debt_rows.extend(_projection_debt_rows(route_audit))
    debt_rows.extend(_routing_source_coupling_debt_rows(routing_projection_status))
    debt_rows.extend(_clusterability_debt_rows(clusterability))
    debt_rows.extend(_routing_coverage_debt_rows(annex_routing_coverage))
    debt_rows.extend(_annex_currentness_debt_rows(annex_currentness))
    debt_rows.extend(_annex_movement_pressure_debt_rows(annex_movement_pressure))
    debt_rows.extend(_annex_dogfood_debt_rows(annex_navigation_dogfood))
    debt_rows.extend(_process_audit_behavior_rows(process_audit))
    debt_rows, observed_mechanism_debt_retirement = _retire_observed_navigation_mechanism_debt_rows(
        debt_rows,
        navigation_mechanism_metabolism,
    )

    fitness_source: dict[str, Any] = {
        "status": "disabled",
        "reason": "include_fitness=false",
    }
    if fitness_payload is not None:
        fitness = dict(fitness_payload)
        fitness_source = {
            "status": "caller_supplied",
            "suite": fitness.get("suite"),
            "fitness_mode": (fitness.get("strategy") or {}).get("fitness_mode"),
            "task_count": (fitness.get("summary") or {}).get("task_count"),
            "debt_candidate_count": (fitness.get("summary") or {}).get("debt_candidate_count"),
            "route_type_metrics": fitness.get("route_type_metrics"),
        }
        debt_rows.extend(_fitness_debt_rows(fitness))
    elif include_fitness:
        try:
            from system.lib.navigation_fitness import build_navigation_fitness

            fitness = build_navigation_fitness(
                root,
                fitness_suite,
                context_budget=budget,
                include_semantic=False,
            )
            fitness_source = {
                "status": "available",
                "suite": fitness.get("suite"),
                "fitness_mode": (fitness.get("strategy") or {}).get("fitness_mode"),
                "task_count": (fitness.get("summary") or {}).get("task_count"),
                "debt_candidate_count": (fitness.get("summary") or {}).get("debt_candidate_count"),
                "sufficiency_fail_count": (fitness.get("summary") or {}).get("sufficiency_fail_count"),
                "latency_fail_count": (fitness.get("summary") or {}).get("latency_fail_count"),
                "route_type_metrics": fitness.get("route_type_metrics"),
            }
            debt_rows.extend(_fitness_debt_rows(fitness))
        except Exception as exc:  # noqa: BLE001 - ratchet should report fitness unavailability
            fitness = None
            fitness_source = {
                "status": "unavailable",
                "error": f"{type(exc).__name__}: {exc}",
            }
    else:
        fitness = None

    supplied_behavior = list(behavior_events or [])
    debt_rows.extend(normalize_agent_route_events(supplied_behavior))

    session_summary: dict[str, Any] | None = None
    session_source: dict[str, Any] = {
        "status": "disabled",
        "reason": "include_session_summary=false",
    }
    if include_session_summary:
        session_summary, session_source = _session_diagnostics_summary(last=session_last)
        if isinstance(session_summary, Mapping):
            debt_rows.extend(_diagnostics_behavior_rows(session_summary))

    skill_find_policy = _skill_find_debug_trace_policy_receipt()
    _append_skill_find_policy_gap_if_needed(
        debt_rows,
        policy_receipt=skill_find_policy,
        source_surface="current_operator_complaint",
        evidence="Operator complaints keep route-policy gaps visible only when the DEBUG_TRACE contract is not hardened.",
    )

    annex_intake, annex_debt = _annex_intake_rows(root)
    debt_rows.extend(annex_debt)

    route_lifecycle = _route_lifecycle_rows()
    debt_rows.extend(_layer_sprawl_rows(route_lifecycle))

    debt_rows = sorted(debt_rows, key=lambda row: int(row.get("priority") or 0), reverse=True)
    counts = _count_by_class(debt_rows)
    active_debt_rows = _active_debt_rows(debt_rows)
    top_repairs = _top_repairs(debt_rows)
    quality_signal = _quality_signal(
        counts,
        process_audit_status=str(process_audit.get("status") or "unavailable"),
    )
    packet = {
        "kind": "navigation_metabolism_ledger",
        "schema_version": "navigation_metabolism_ledger_v0",
        "generated_at": _utc_now(),
        "query": task_query,
        "metabolism_profile": "full",
        "budget": {
            "context_budget_tokens": budget,
            "hard_ceiling": True,
            "estimated_tokens": 0,
            "trimmed_for_budget": False,
        },
        "quality_signal": quality_signal,
        "summary": {
            **counts,
            "total_debt_rows": len(active_debt_rows),
            "advisory_debt_rows": len(debt_rows) - len(active_debt_rows),
            "total_rows_including_advisory": len(debt_rows),
            "top_repair_count": len(top_repairs),
            "quality_signal_score": quality_signal["score"],
            "quality_signal_bottleneck": quality_signal["bottleneck_debt_class"],
        },
        "strategy": {
            "single_ratchet": True,
            "profile": "full",
            "quick_profile_drilldown": f"./repo-python kernel.py --navigation-metabolism {json.dumps(task_query)} --metabolism-profile quick --context-budget {budget}",
            "inputs_are_narrow_audits_not_new_authorities": True,
            "agent_path_observation_is_behavior_debt": True,
            "annex_intake_is_debt_not_paper_module_generation": True,
            "route_cleanup_requires_lifecycle_metadata": True,
            "quality_signal_is_header_not_collapse": True,
            "quality_signal_provenance": [f"annexes/{SENTRUX_ANNEX}/distillation.json::patterns[p001,p002,p003,p005]"],
        },
        "observation_sources": {
            "surface_authoring_audit": {
                "status": "available",
                "debt_count": len(surface_audit.get("authoring_debt") or []),
            },
            "navigation_surface_audit": {
                "status": "available",
                "contract_violation_count": (route_audit.get("summary") or {}).get("contract_violation_count"),
            },
            "path_reference_reading_yield_audit": {
                "status": path_reference_reading_yield_audit.get("status"),
                "mode": path_reference_reading_yield_audit.get("mode"),
                "scanned_surface_count": path_reference_reading_yield_audit.get("scanned_surface_count"),
                "decision_bearing_route_count": path_reference_reading_yield_audit.get("decision_bearing_route_count"),
                "resolved_owner_count": path_reference_reading_yield_audit.get("resolved_owner_count"),
                "resolved_yield_count": path_reference_reading_yield_audit.get("resolved_yield_count"),
                "mapped_equivalent_count": path_reference_reading_yield_audit.get("mapped_equivalent_count"),
                "warning_count": path_reference_reading_yield_audit.get("warning_count"),
                "blocking_count": path_reference_reading_yield_audit.get("blocking_count"),
                "authority_posture": path_reference_reading_yield_audit.get("authority_posture"),
            },
            "clusterability": {
                "status": "available",
                "summary": clusterability.get("summary"),
                "measure_all_rows": True,
            },
            "annex_routing_coverage": {
                "status": "available",
                "summary": annex_routing_coverage.get("summary"),
                "threshold": (annex_routing_coverage.get("budget") or {}).get("unrouted_rate_threshold"),
            },
            "annex_currentness": {
                "status": "available",
                "summary": annex_currentness.get("summary"),
                "source": annex_currentness.get("source"),
            },
            "annex_movement_pressure_map": {
                "status": "available",
                "summary": annex_movement_pressure.get("summary"),
                "quality_signal": annex_movement_pressure.get("quality_signal"),
            },
            "annex_navigation_dogfood": {
                "status": "available",
                "summary": annex_navigation_dogfood.get("summary"),
                "compressed_comprehension": annex_navigation_dogfood.get("compressed_comprehension"),
            },
            "entrypoint_health": {
                "status": "available",
                "contract_status": (entrypoint_health.get("summary") or {}).get("contract_status"),
                "over_budget_count": (entrypoint_health.get("summary") or {}).get("over_budget_count"),
                "disallowed_stale_route_hit_count": (
                    entrypoint_health.get("summary") or {}
                ).get("disallowed_stale_route_hit_count"),
            },
            "skill_find_debug_trace_policy": skill_find_policy,
            "routing_projection_status": {
                "status": "available",
                "stale": routing_projection_status.get("stale"),
                "artifact_path": routing_projection_status.get("artifact_path"),
                "source_coupling": routing_projection_status.get("source_coupling"),
                "cache_status": routing_projection_cache_status.get("status"),
            },
            "actor_delivery_receipt": {
                "status": actor_delivery_receipt.get("status") or "available",
                "ok": actor_delivery_receipt.get("ok"),
                "required_delivery_route_count": actor_delivery_receipt.get("required_delivery_route_count"),
                "total_situation_route_count": actor_delivery_receipt.get("total_situation_route_count"),
                "actor_delivery_decision_count": actor_delivery_receipt.get("actor_delivery_decision_count"),
                "unknown_delivery_decision_count": actor_delivery_receipt.get("unknown_delivery_decision_count"),
                "warning_count": len(actor_delivery_receipt.get("warnings") or []),
                "blocker_count": len(actor_delivery_receipt.get("blockers") or []),
            },
            "agent_path_events": {
                "status": (
                    "process_audit_consumed"
                    if str(process_audit.get("status") or "") == "available"
                    else "fixture_or_caller_supplied"
                    if supplied_behavior
                    else "policy_and_session_summary"
                ),
                "supplied_event_count": len(supplied_behavior),
                "supplied_event_count_semantics": "caller_supplied_fixture_events_only",
                "process_audit_status": process_audit.get("status") or "unavailable",
                "process_audit_observed_session_count": int(process_audit.get("session_count") or 0),
                "process_audit_session_count": int(process_audit.get("session_count") or 0),
                "process_audit_behavior_row_count": sum(
                    1
                    for row in debt_rows
                    if isinstance(row, Mapping)
                    and row.get("debt_class") == "behavior_debt"
                    and str(row.get("source_surface") or "") == "--process-audit"
                ),
                "process_audit_active_behavior_debt_count": sum(
                    1
                    for row in debt_rows
                    if isinstance(row, Mapping)
                    and row.get("debt_class") == "behavior_debt"
                    and str(row.get("source_surface") or "") == "--process-audit"
                    and _is_active_debt_row(row)
                ),
                "process_audit_retired_behavior_debt_count": sum(
                    1
                    for row in debt_rows
                    if isinstance(row, Mapping)
                    and row.get("debt_class") == "behavior_debt"
                    and str(row.get("source_surface") or "") == "--process-audit"
                    and row.get("retired_by_navigation_mechanism_observation") is True
                ),
                "process_audit_pattern_classes": [
                    str((pattern or {}).get("pattern_id") or "")
                    for pattern in (process_audit.get("patterns") or [])
                    if isinstance(pattern, Mapping)
                ],
                "sentrux_provenance": ["p001", "p003"],
            },
            "hook_shadow_coverage": {
                "status": hook_shadow_coverage.get("status"),
                "hook_shadow_coverage_top_patterns": hook_shadow_coverage.get("hook_shadow_coverage_top_patterns"),
                "would_intervene_on_recent_route_failures": hook_shadow_coverage.get(
                    "would_intervene_on_recent_route_failures"
                ),
                "authority": hook_shadow_coverage.get("authority"),
            },
            "navigation_mechanism_metabolism": {
                "status": navigation_mechanism_metabolism.get("status"),
                "candidate_count": navigation_mechanism_metabolism.get("candidate_count"),
                "validated_count": navigation_mechanism_metabolism.get("validated_count"),
                "accepted_count": navigation_mechanism_metabolism.get("accepted_count"),
                "projected_count": navigation_mechanism_metabolism.get("projected_count"),
                "observed_count": navigation_mechanism_metabolism.get("observed_count"),
                "observed_anti_pattern_ids": navigation_mechanism_metabolism.get("observed_anti_pattern_ids"),
                "authority_posture": navigation_mechanism_metabolism.get("authority_posture"),
            },
            "observed_mechanism_debt_retirement": observed_mechanism_debt_retirement,
            "session_diagnostics_summary": session_source,
            "annex_intake": {
                "status": "available",
                "annex_count": len(annex_intake),
            },
            "navigation_fitness": fitness_source,
        },
        "debt_rows": debt_rows,
        "top_repairs": top_repairs,
        "path_reference_reading_yield_audit": path_reference_reading_yield_audit,
        "entrypoint_health": entrypoint_health,
        "actor_delivery_receipt": {
            "kind": actor_delivery_receipt.get("kind"),
            "ok": actor_delivery_receipt.get("ok"),
            "required_delivery_route_count": actor_delivery_receipt.get("required_delivery_route_count"),
            "total_situation_route_count": actor_delivery_receipt.get("total_situation_route_count"),
            "actor_delivery_decision_count": actor_delivery_receipt.get("actor_delivery_decision_count"),
            "deliver_to_cold_start_count": actor_delivery_receipt.get("deliver_to_cold_start_count"),
            "non_delivery_decision_count": actor_delivery_receipt.get("non_delivery_decision_count"),
            "unknown_delivery_decision_count": actor_delivery_receipt.get("unknown_delivery_decision_count"),
            "warnings": list(actor_delivery_receipt.get("warnings") or [])[:5],
            "blockers": list(actor_delivery_receipt.get("blockers") or [])[:5],
        },
        "clusterability": clusterability,
        "annex_routing_coverage": annex_routing_coverage,
        "annex_currentness": annex_currentness,
        "annex_movement_pressure_map": annex_movement_pressure,
        "annex_navigation_dogfood": annex_navigation_dogfood,
        "navigation_fitness": fitness if include_fitness or fitness_payload is not None else None,
        "hook_shadow_coverage": hook_shadow_coverage,
        "navigation_mechanism_metabolism": navigation_mechanism_metabolism,
        "annex_intake": annex_intake,
        "route_lifecycle": route_lifecycle,
        "next_commands": [
            "./repo-python kernel.py --navigation-metabolism \"navigation context compression\" --context-budget 12000",
            "./repo-python kernel.py --coverage-enforcement-matrix \"navigation context compression\" --context-budget 12000",
            "./repo-python kernel.py --clusterability-audit --context-budget 12000",
            "./repo-python kernel.py --annex-routing-coverage --context-budget 12000",
            "./repo-python kernel.py --annex-currentness --context-budget 12000",
            "./repo-python kernel.py --annex-movement-pressure-map \"improve annex navigation protocol\" --context-budget 12000",
            "./repo-python kernel.py --annex-navigation-dogfood \"improve annex navigation protocol\" --context-budget 12000",
            "./repo-python kernel.py --metabolism-row-jobs annex-sync-digest --limit 5",
            "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
            "./repo-python kernel.py --navigation-mechanism-factory --limit 20",
            "./repo-python tools/meta/factory/validate_navigation_mechanism_facets.py --limit 20 --json",
            "./repo-python kernel.py --navigation-mechanism-replay",
            "./repo-python kernel.py --surface-authoring-audit --context-budget 12000",
            "./repo-python kernel.py --session-diagnostics --lens all --last 5 --store both --json --diagnostics-summary",
        ],
        "source_surfaces": [
            "system/lib/surface_authoring_audit.py",
            "system/lib/navigation_surface_audit.py",
            "system/lib/path_reference_reading_yield.py",
            "system/lib/navigation_clusterability.py",
            "system/lib/annex_routing_coverage.py",
            "system/lib/annex_currentness.py",
            "system/lib/annex_movement_pressure_map.py",
            "system/lib/annex_navigation_dogfood.py",
            "system/lib/entrypoint_health.py",
            "system/lib/navigation_fitness.py",
            "system/lib/navigation_mechanism_factory.py",
            "system/lib/agent_execution_trace.py",
            "tools/meta/observability/session_analyzer.py",
            f"annexes/{TACO_ANNEX}/distillation.json",
            f"annexes/{SENTRUX_ANNEX}/distillation.json",
        ],
    }
    return _budget_trim(packet, context_budget=budget)
