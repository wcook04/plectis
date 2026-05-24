"""
Public trace-to-route-repair observability substrate.

This module is a source-faithful public refactor of
`system/lib/navigation_route_intervention.py` around the trace mechanics owned
by `system/lib/agent_execution_trace.py`. It keeps the macro route-repair map
and hook-shadow coverage semantics, while accepting only public process-audit
metadata. It does not parse provider payloads, hidden reasoning, transcript
bodies, browser/HUD state, account/session state, credentials, or live hook
state.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


PASS = "pass"
BLOCKED = "blocked"

KIND = "public_agent_trace_route_repair"
SCHEMA_VERSION = "public_agent_trace_route_repair_v1"
SOURCE_REFS = [
    "system/lib/navigation_route_intervention.py",
    "system/lib/agent_execution_trace.py",
    "codex/standards/std_agent_execution_trace.json",
    "codex/standards/std_navigation_contract.json",
    "codex/doctrine/paper_modules/agent_self_observability_plane.md",
    "state/microcosm_portfolio/extracted_pattern_substrate_bindings.json#agent_trace_to_route_repair_observability_compound",
]
SOURCE_SYMBOL_REFS = [
    "system/lib/navigation_route_intervention.py::RouteRepairSuggestion",
    "system/lib/navigation_route_intervention.py::route_repair_for",
    "system/lib/navigation_route_intervention.py::build_hook_shadow_coverage",
    "system/lib/navigation_route_intervention.py::suggestion_message",
    "system/lib/agent_execution_trace.py::build_agent_execution_trace",
]
TARGET_REF = "microcosm-substrate/src/microcosm_core/macro_tools/agent_trace_route_repair.py"
TARGET_REFS = [TARGET_REF]
TARGET_SYMBOL_REFS = [
    "microcosm_core.macro_tools.agent_trace_route_repair::RouteRepairSuggestion",
    "microcosm_core.macro_tools.agent_trace_route_repair::route_repair_for",
    "microcosm_core.macro_tools.agent_trace_route_repair::build_hook_shadow_coverage",
    "microcosm_core.macro_tools.agent_trace_route_repair::build_public_agent_trace_route_repair_view",
]
AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_trace_route_repair_metadata_not_live_hook_authority",
    "live_hook_install_authorized": False,
    "live_route_repair_authorized": False,
    "live_home_session_logs_read": False,
    "raw_transcript_body_exported": False,
    "provider_payload_read": False,
    "hidden_reasoning_exported": False,
    "browser_hud_live_access": False,
    "account_session_state_exported": False,
    "credential_or_cookie_exported": False,
    "recipient_send_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
    "private_root_equivalence_claim": False,
}
ANTI_CLAIM = (
    "Agent trace route-repair replay validates public process-audit pattern "
    "metadata, route-repair suggestions, hook-shadow coverage rows, and "
    "metadata-only trace digests. It does not read live session logs, export "
    "transcript bodies, provider payloads, hidden reasoning, browser/HUD state, "
    "account/session state, credentials, cookies, recipient-send material, or "
    "install live route hooks."
)
INPUT_NAMES = (
    "bundle_manifest.json",
    "process_audit.json",
    "process_pattern_repairs.json",
    "route_repair_policy.json",
    "expected_route_repair_summary.json",
)
FORBIDDEN_PAYLOAD_KEYS = {
    "raw_transcript_body",
    "transcript_body",
    "tool_result_body",
    "provider_payload",
    "hidden_reasoning",
    "thinking",
    "browser_hud_state",
    "browser_hud_cockpit_state",
    "account_session_state",
    "credential_value",
    "cookie",
    "password",
    "secret_value",
    "api_key",
    "access_token",
    "refresh_token",
    "recipient_send_payload",
    "live_hook_state",
    "live_operator_state",
}

ENTRY_REPLACEMENT_ROUTE = './repo-python kernel.py --entry "<task>" --context-budget 12000'
CONTEXT_PACK_ROUTE = './repo-python kernel.py --context-pack "<task>" --context-budget 12000'
NAV_METABOLISM_ROUTE = (
    './repo-python kernel.py --navigation-metabolism "<task>" '
    "--metabolism-profile quick --context-budget 12000"
)
PHASE_TASK_ALIGNMENT_ROUTE = './repo-python kernel.py --phase <phase> --task "<task>"'


@dataclass(frozen=True)
class RouteRepairSuggestion:
    anti_pattern_id: str
    repair_class: str
    bad_first_contact_shape: str
    preferred_first_surface: str
    fallback_surface: str
    why: str
    expected_artifacts: tuple[str, ...]
    evidence_command: str
    followup_surfaces: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["expected_artifacts"] = list(self.expected_artifacts)
        row["followup_surfaces"] = list(self.followup_surfaces)
        row["suggested_sequence"] = [self.preferred_first_surface, *self.followup_surfaces]
        return row


ROUTE_REPAIR_SUGGESTIONS: dict[str, RouteRepairSuggestion] = {
    "multi_repo_python_batch": RouteRepairSuggestion(
        anti_pattern_id="multi_repo_python_batch",
        repair_class="command_efficiency_guard_plus_context_pack_first_contact",
        bad_first_contact_shape="multiple repo Python/kernel commands batched into one buffered shell turn",
        preferred_first_surface=ENTRY_REPLACEMENT_ROUTE,
        fallback_surface=CONTEXT_PACK_ROUTE,
        why=(
            "The observed failure is command-ladder batching under concurrent agents; the repair "
            "class routes to one control packet first, then one selected bounded drilldown."
        ),
        expected_artifacts=(
            "command_cards:command_efficiency_guard",
            "skills:navigation_metabolism",
            "option_surface:task_ledger.cluster_flag",
        ),
        evidence_command="./repo-python kernel.py --command-card \"command buffering\" --debug",
    ),
    "anti_pattern_grep_before_kernel": RouteRepairSuggestion(
        anti_pattern_id="anti_pattern_grep_before_kernel",
        repair_class="hook_steering_plus_context_pack_first_contact",
        bad_first_contact_shape="grep/rg/find shell discovery before the kernel ladder",
        preferred_first_surface=ENTRY_REPLACEMENT_ROUTE,
        fallback_surface=CONTEXT_PACK_ROUTE,
        why=(
            "The observed failure is route discovery by shell search before typed navigation; "
            "the repair class routes to the canonical entry control packet first; "
            "--context-pack is the downstream cross-kind packet route after entry selects it "
            "(per std_agent_entry_surface.json::canonical_option_surface_routes.first_move_contract)."
        ),
        expected_artifacts=("skills:navigation_metabolism", "skills:agent_session_diagnostics"),
        evidence_command="./repo-python kernel.py --process-audit",
    ),
    "skill_find_first_contact": RouteRepairSuggestion(
        anti_pattern_id="skill_find_first_contact",
        repair_class="hook_steering_plus_context_pack_first_contact",
        bad_first_contact_shape=(
            "--skill-find used as first-contact capability discovery instead of coverage-first "
            "atlas or option-surface navigation"
        ),
        preferred_first_surface=ENTRY_REPLACEMENT_ROUTE,
        fallback_surface="./repo-python kernel.py --option-surface skills --band cluster_flag",
        why=(
            "Coverage-first navigation beats lexical-luck search. Skill-find is a DEBUG_TRACE / "
            "exact-id drilldown after a stable skill id or family is selected; first contact "
            "should run the canonical entry control packet, with the skills cluster option surface "
            "as the explicit browse fallback when entry routes to skill territory."
        ),
        expected_artifacts=(
            "standards:std_agent_entry_surface",
            "standards:std_skill",
            "skills:navigation_metabolism",
            "option_surface:skills.cluster_flag",
        ),
        evidence_command="./repo-python kernel.py --navigation-metabolism \"navigation route behavior\" --metabolism-profile quick --context-budget 12000",
    ),
    "anti_pattern_paper_module_skip": RouteRepairSuggestion(
        anti_pattern_id="anti_pattern_paper_module_skip",
        repair_class="paper_module_lookup_skill_or_router_repair",
        bad_first_contact_shape="paper/doctrine territory explored by raw search or raw file reads",
        preferred_first_surface=ENTRY_REPLACEMENT_ROUTE,
        fallback_surface="./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
        why=(
            "The observed failure is bypassing the paper-module selection surface; the repair "
            "class routes to the canonical entry control packet first, then bounded paper-module "
            "cluster drilldown."
        ),
        expected_artifacts=("paper_modules:navigation_hologram_theory", "skills:navigation_metabolism"),
        evidence_command="./repo-python kernel.py --process-audit",
    ),
    "anti_pattern_cold_boot_missing_info": RouteRepairSuggestion(
        anti_pattern_id="anti_pattern_cold_boot_missing_info",
        repair_class="entrypoint_first_contact_repair",
        bad_first_contact_shape="session starts without the bootstrap info/preflight/pulse ladder",
        preferred_first_surface="./repo-python kernel.py --info",
        fallback_surface=ENTRY_REPLACEMENT_ROUTE,
        why=(
            "Cold boot failures are entrypoint failures; the repair class routes to the cheap "
            "static/router HUD first, then the preflight card, then live pulse, then the canonical entry control packet "
            "before deeper drilldowns (per std_agent_entry_surface.json::canonical_option_surface_routes.first_move_contract)."
        ),
        expected_artifacts=("phase:*", "skills:navigation_metabolism"),
        evidence_command="./repo-python kernel.py --process-audit",
        followup_surfaces=(
            "./repo-python kernel.py --preflight",
            "./repo-python kernel.py --pulse",
            ENTRY_REPLACEMENT_ROUTE,
        ),
    ),
    "anti_pattern_deep_without_ladder": RouteRepairSuggestion(
        anti_pattern_id="anti_pattern_deep_without_ladder",
        repair_class="navigation_seed_skill_or_kind_atlas_router_repair",
        bad_first_contact_shape="deep traversal proceeds without kernel navigation ladder usage",
        preferred_first_surface=ENTRY_REPLACEMENT_ROUTE,
        fallback_surface="./repo-python kernel.py --kind-atlas",
        why=(
            "Deep traversal without ladder is a route-selection failure; the repair class routes "
            "to the canonical entry control packet, then the coverage owner route and navigation "
            "seed/diagnostics owner card before raw exploration continues."
        ),
        expected_artifacts=(
            "skills:navigation_seed",
            "skills:agent_session_diagnostics",
            "skills:navigation_metabolism",
            "option_surface:skills.card",
        ),
        evidence_command="./repo-python kernel.py --process-audit",
        followup_surfaces=(
            './repo-python kernel.py --coverage-enforcement-matrix "anti_pattern_deep_without_ladder" --context-budget 12000',
            "./repo-python kernel.py --option-surface skills --band card --ids navigation_seed,agent_session_diagnostics",
        ),
    ),
    "anti_pattern_loop_detected": RouteRepairSuggestion(
        anti_pattern_id="anti_pattern_loop_detected",
        repair_class="loop_break_skill_or_hook_repair",
        bad_first_contact_shape="same command shape repeats without a route-state change",
        preferred_first_surface=NAV_METABOLISM_ROUTE,
        fallback_surface="./repo-python kernel.py --process-audit",
        why=(
            "Looping is a behavior-state failure; the repair class routes to the metabolism "
            "ledger so the next step is selected from observed debt rather than repeated."
        ),
        expected_artifacts=("skills:agent_session_diagnostics", "skills:navigation_metabolism"),
        evidence_command="./repo-python kernel.py --process-audit",
    ),
    "anti_pattern_stall_detected": RouteRepairSuggestion(
        anti_pattern_id="anti_pattern_stall_detected",
        repair_class="agent_orientation_or_resume_protocol_repair",
        bad_first_contact_shape="session stalls without a useful next navigation action",
        preferred_first_surface=NAV_METABOLISM_ROUTE,
        fallback_surface="./repo-python kernel.py --phase",
        why=(
            "Stalls are orientation failures; the repair class routes to the live quality ledger "
            "or active phase packet instead of another raw search."
        ),
        expected_artifacts=("paper_modules:agent_self_observability_plane", "skills:navigation_metabolism"),
        evidence_command="./repo-python kernel.py --process-audit",
    ),
    "raw_kernel_help_first_contact": RouteRepairSuggestion(
        anti_pattern_id="raw_kernel_help_first_contact",
        repair_class="hook_steering_plus_context_pack_first_contact",
        bad_first_contact_shape="raw kernel.py --help used as first-contact navigation",
        preferred_first_surface=ENTRY_REPLACEMENT_ROUTE,
        fallback_surface="./repo-python kernel.py --kind-atlas",
        why=(
            "Raw help is a keyword surface; the repair class routes first-contact tasks to the "
            "canonical entry control packet, with --kind-atlas as the explicit browse fallback."
        ),
        expected_artifacts=("skills:navigation_metabolism",),
        evidence_command="./repo-python kernel.py --navigation-fitness adversarial_20 --context-budget 12000 --full",
    ),
    "paper_lattice_before_slug_selection": RouteRepairSuggestion(
        anti_pattern_id="paper_lattice_before_slug_selection",
        repair_class="paper_module_lookup_skill_or_router_repair",
        bad_first_contact_shape="paper lattice opened before a supported stable slug is selected",
        preferred_first_surface=ENTRY_REPLACEMENT_ROUTE,
        fallback_surface="./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
        why=(
            "Paper lattice is a drilldown after slug selection; the repair class routes to the "
            "canonical entry control packet so the kernel can name the slug first."
        ),
        expected_artifacts=("paper_modules:navigation_hologram_theory",),
        evidence_command="./repo-python kernel.py --navigation-fitness adversarial_20 --context-budget 12000 --full",
    ),
    "anti_pattern_phase_residual_exception_narration": RouteRepairSuggestion(
        anti_pattern_id="anti_pattern_phase_residual_exception_narration",
        repair_class="phase_task_alignment_residual_lane",
        bad_first_contact_shape=(
            "agent says the active phase is one wave but the request is another, then treats the task as an exception"
        ),
        preferred_first_surface=PHASE_TASK_ALIGNMENT_ROUTE,
        fallback_surface='./repo-python kernel.py --coverage-enforcement-matrix "<task>" --context-budget 12000',
        why=(
            "Phase mismatch is not agent discretion. The repair class routes the query through "
            "--phase <phase> --task so the kernel selects primary_wave, residual_lane, mixed_lane, "
            "or ambiguous_lane with owner surfaces and write guards."
        ),
        expected_artifacts=(
            "route_lifecycle:phase_task_alignment",
            "route_lifecycle:coverage_enforcement_matrix",
            "skills:navigation_seed",
        ),
        evidence_command='./repo-python kernel.py --phase <phase> --task "<task>"',
    ),
}

REPAIR_CLASS_ROUTE_SUGGESTIONS = {
    suggestion.repair_class: suggestion for suggestion in ROUTE_REPAIR_SUGGESTIONS.values()
}

PROCESS_PATTERN_ALIASES = {
    "keyword_search_before_cluster_surface": "skill_find_first_contact",
    "raw_help_before_kind_atlas_or_context_pack": "raw_kernel_help_first_contact",
    "paper_module_skip": "anti_pattern_paper_module_skip",
    "grep_before_kernel": "anti_pattern_grep_before_kernel",
    "buffered_shell_batch": "multi_repo_python_batch",
    "multi_kernel_batch": "multi_repo_python_batch",
    "phase_residual_exception_narration": "anti_pattern_phase_residual_exception_narration",
    "phase_task_alignment_residual_lane": "anti_pattern_phase_residual_exception_narration",
}


def route_repair_for(
    *,
    anti_pattern_id: str | None = None,
    repair_class: str | None = None,
) -> RouteRepairSuggestion | None:
    key = str(anti_pattern_id or "").strip()
    key = PROCESS_PATTERN_ALIASES.get(key, key)
    if key in ROUTE_REPAIR_SUGGESTIONS:
        return ROUTE_REPAIR_SUGGESTIONS[key]
    repair = str(repair_class or "").strip()
    if repair:
        return REPAIR_CLASS_ROUTE_SUGGESTIONS.get(repair)
    return None


def _recent_patterns(process_audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    for pattern in process_audit.get("patterns") or []:
        if not isinstance(pattern, Mapping):
            continue
        pattern_id = str(pattern.get("pattern_id") or "")
        if not pattern_id or pattern_id.startswith("positive_"):
            continue
        patterns.append(
            {
                "anti_pattern_id": pattern_id,
                "instances": int(pattern.get("instances") or 0),
                "sessions_hit": len(list(pattern.get("session_id_hits") or [])),
            }
        )
    return sorted(patterns, key=lambda row: int(row.get("instances") or 0), reverse=True)


def build_hook_shadow_coverage(
    process_audit: Mapping[str, Any],
    *,
    process_repairs: Mapping[str, Mapping[str, Any]] | None = None,
    top_n: int = 4,
) -> dict[str, Any]:
    repairs = process_repairs or {}
    rows: list[dict[str, Any]] = []
    for pattern in _recent_patterns(process_audit)[: max(1, top_n)]:
        anti_pattern_id = str(pattern.get("anti_pattern_id") or "")
        repair_spec = repairs.get(anti_pattern_id) if isinstance(repairs, Mapping) else None
        repair_class = ""
        if isinstance(repair_spec, Mapping):
            repair_class = str(repair_spec.get("repair_class") or "")
        suggestion = route_repair_for(
            anti_pattern_id=anti_pattern_id,
            repair_class=repair_class,
        )
        row = {
            **pattern,
            "repair_class": repair_class,
            "would_intervene": suggestion is not None,
            "confidence": 0.85 if suggestion is not None else 0.0,
            "missing_authority_if_any": None if suggestion is not None else "no route repair suggestion mapped",
        }
        if suggestion is not None:
            row.update(
                {
                    "suggested_route": suggestion.preferred_first_surface,
                    "suggested_sequence": [
                        suggestion.preferred_first_surface,
                        *suggestion.followup_surfaces,
                    ],
                    "fallback_surface": suggestion.fallback_surface,
                    "expected_artifacts": list(suggestion.expected_artifacts),
                    "reason": suggestion.why,
                    "bad_first_contact_shape": suggestion.bad_first_contact_shape,
                    "evidence_command": suggestion.evidence_command,
                }
            )
        rows.append(row)

    covered = sum(1 for row in rows if row.get("would_intervene"))
    return {
        "status": "available" if rows else "no_recent_anti_patterns",
        "top_pattern_count": len(rows),
        "covered_top_pattern_count": covered,
        "hook_shadow_coverage_top_patterns": f"{covered}/{len(rows)}" if rows else "0/0",
        "would_intervene_on_recent_route_failures": covered,
        "rows": rows,
        "authority": "anti_pattern_id_then_repair_class",
    }


def suggestion_message(suggestion: RouteRepairSuggestion) -> str:
    expected = ", ".join(f"`{artifact}`" for artifact in suggestion.expected_artifacts)
    followup = ""
    if suggestion.followup_surfaces:
        followup = "; then " + " -> ".join(f"`{surface}`" for surface in suggestion.followup_surfaces)
    return (
        f"Matches `{suggestion.anti_pattern_id}`; repair_class "
        f"`{suggestion.repair_class}` chooses the route. "
        f"Use `{suggestion.preferred_first_surface}` first"
        f"{followup}"
        f"{f'; fallback `{suggestion.fallback_surface}`' if suggestion.fallback_surface else ''}. "
        f"Expected artifacts: {expected}. {suggestion.why}"
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_public_agent_trace_route_repair_bundle(input_dir: str | Path) -> dict[str, dict[str, Any]]:
    input_path = Path(input_dir)
    return {
        name.removesuffix(".json"): _read_json(input_path / name)
        for name in INPUT_NAMES
    }


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _walk_payload_keys(payload: object) -> set[str]:
    if isinstance(payload, Mapping):
        keys = {str(key) for key in payload}
        for value in payload.values():
            keys.update(_walk_payload_keys(value))
        return keys
    if isinstance(payload, list):
        keys: set[str] = set()
        for item in payload:
            keys.update(_walk_payload_keys(item))
        return keys
    return set()


def _stable_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _bundle_finding(
    error_code: str,
    message: str,
    *,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "status": BLOCKED,
        "error_code": error_code,
        "message": message,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_in_receipt": False,
    }


def _expected_summary_validation(
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
) -> dict[str, Any]:
    keys = (
        "top_pattern_count",
        "covered_top_pattern_count",
        "would_intervene_on_recent_route_failures",
        "suggested_route_count",
    )
    mismatches = [
        {
            "field": key,
            "expected": expected.get(key),
            "actual": actual.get(key),
        }
        for key in keys
        if expected.get(key) is not None and expected.get(key) != actual.get(key)
    ]
    return {
        "status": PASS if not mismatches else BLOCKED,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "actual_summary": dict(actual),
    }


def _validate_policy(payload: Mapping[str, Any]) -> dict[str, Any]:
    required_false_flags = (
        "live_hook_install_authorized",
        "live_route_repair_authorized",
        "provider_payload_read",
        "raw_transcript_body_exported",
        "hidden_reasoning_exported",
    )
    findings = [
        _bundle_finding(
            "AGENT_TRACE_ROUTE_REPAIR_POLICY_OVERCLAIM",
            "Route-repair policy must keep live hook, provider payload, transcript body, and hidden-reasoning authority disabled.",
            subject_id=flag,
            subject_kind="route_repair_policy",
        )
        for flag in required_false_flags
        if payload.get(flag) is not False
    ]
    forbidden_keys = sorted(FORBIDDEN_PAYLOAD_KEYS & _walk_payload_keys(payload))
    findings.extend(
        _bundle_finding(
            "AGENT_TRACE_ROUTE_REPAIR_FORBIDDEN_POLICY_KEY",
            "Route-repair policy contains a forbidden private or live-access payload key.",
            subject_id=key,
            subject_kind="route_repair_policy",
        )
        for key in forbidden_keys
    )
    return {
        "status": PASS if not findings else BLOCKED,
        "policy_id": payload.get("policy_id"),
        "metadata_envelope_only": payload.get("metadata_envelope_only") is True,
        "forbidden_authority_rejected": not findings,
        "findings": findings,
    }


def build_public_agent_trace_route_repair_view(
    payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    manifest = payloads.get("bundle_manifest", {})
    process_audit = payloads.get("process_audit", {})
    repairs_payload = payloads.get("process_pattern_repairs", {})
    repairs = repairs_payload.get("repairs", {}) if isinstance(repairs_payload, Mapping) else {}
    policy = payloads.get("route_repair_policy", {})
    expected = payloads.get("expected_route_repair_summary", {})

    hook_shadow = build_hook_shadow_coverage(
        process_audit,
        process_repairs=repairs if isinstance(repairs, Mapping) else {},
        top_n=int(expected.get("top_n") or 4) if isinstance(expected, Mapping) else 4,
    )
    route_rows = [
        {
            "anti_pattern_id": row["anti_pattern_id"],
            "repair_class": row.get("repair_class") or "",
            "suggested_route": row.get("suggested_route"),
            "suggested_sequence": row.get("suggested_sequence", []),
            "fallback_surface": row.get("fallback_surface"),
            "expected_artifacts": row.get("expected_artifacts", []),
            "confidence": row.get("confidence", 0.0),
            "would_intervene": row.get("would_intervene") is True,
        }
        for row in hook_shadow["rows"]
        if row.get("would_intervene") is True
    ]
    actual_summary = {
        "top_pattern_count": hook_shadow["top_pattern_count"],
        "covered_top_pattern_count": hook_shadow["covered_top_pattern_count"],
        "would_intervene_on_recent_route_failures": hook_shadow[
            "would_intervene_on_recent_route_failures"
        ],
        "suggested_route_count": len(route_rows),
    }
    expected_validation = _expected_summary_validation(
        expected if isinstance(expected, Mapping) else {},
        actual_summary,
    )
    policy_validation = _validate_policy(policy if isinstance(policy, Mapping) else {})
    forbidden_keys = sorted(FORBIDDEN_PAYLOAD_KEYS & _walk_payload_keys(payloads))
    summary_findings = [
        _bundle_finding(
            "AGENT_TRACE_ROUTE_REPAIR_SUMMARY_MISMATCH",
            "Trace route-repair replay summary did not match the declared expected summary.",
            subject_id=str(row["field"]),
            subject_kind="expected_route_repair_summary",
        )
        for row in expected_validation["mismatches"]
    ]
    findings = [
        *summary_findings,
        *policy_validation["findings"],
        *(
            _bundle_finding(
                "AGENT_TRACE_ROUTE_REPAIR_FORBIDDEN_PAYLOAD_KEY",
                "Trace route-repair replay inputs cannot include transcript bodies, provider payloads, hidden reasoning, browser/HUD state, account/session state, credentials, cookies, recipient-send payloads, or live hook state.",
                subject_id=key,
                subject_kind="agent_trace_route_repair_input",
            )
            for key in forbidden_keys
        ),
    ]
    route_ref_count = sum(len(_strings(row.get("public_trace_refs"))) for row in _rows(process_audit, "patterns"))
    status = (
        PASS
        if hook_shadow["status"] == "available"
        and hook_shadow["top_pattern_count"] > 0
        and hook_shadow["covered_top_pattern_count"] == hook_shadow["top_pattern_count"]
        and expected_validation["status"] == PASS
        and policy_validation["status"] == PASS
        and not forbidden_keys
        else BLOCKED
    )
    view_fingerprint = _stable_digest(
        {
            "hook_shadow": hook_shadow,
            "route_rows": route_rows,
            "policy_id": policy_validation.get("policy_id"),
        }
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "status": status,
        "bundle_id": manifest.get("bundle_id"),
        "anti_claim": ANTI_CLAIM,
        "authority_ceiling": AUTHORITY_CEILING,
        "source_refs": _strings(manifest.get("source_refs")) or SOURCE_REFS,
        "target_refs": _strings(manifest.get("target_refs")) or TARGET_REFS,
        "source_symbols": SOURCE_SYMBOL_REFS,
        "target_symbols": TARGET_SYMBOL_REFS,
        "body_import_verification": {
            "verification_mode": "verified_light_edit_recipe",
            "verification_status": "verified",
            "source_ref": "system/lib/navigation_route_intervention.py",
            "target_ref": TARGET_REF,
            "rewrite_recipe_ref": (
                "copy RouteRepairSuggestion, route_repair_for, build_hook_shadow_coverage, "
                "and suggestion_message; add public bundle loader and metadata-only view builder"
            ),
            "source_symbol_refs": SOURCE_SYMBOL_REFS,
            "target_symbol_refs": TARGET_SYMBOL_REFS,
            "runtime_consumed_by": [
                "microcosm agent-route-observability-runtime validate-agent-trace-route-repair-bundle",
                "microcosm-substrate/tests/test_agent_route_observability_runtime.py",
            ],
        },
        "hook_shadow_coverage": hook_shadow,
        "route_repair_rows": route_rows,
        "route_repair_summary": actual_summary,
        "expected_summary_validation": expected_validation,
        "route_repair_policy": policy_validation,
        "metadata_envelope_only": True,
        "process_audit_pattern_count": len(_rows(process_audit, "patterns")),
        "public_trace_ref_count": route_ref_count,
        "forbidden_payload_keys": forbidden_keys,
        "findings": findings,
        "view_fingerprint": view_fingerprint,
        "body_in_receipt": False,
    }
