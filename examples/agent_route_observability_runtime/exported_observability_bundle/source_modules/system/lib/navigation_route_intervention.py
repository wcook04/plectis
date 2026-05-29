"""
Typed route-intervention authority for navigation anti-pattern steering.

This module is intentionally small and pure-Python so both the runtime hook and
navigation metabolism ledger can use the same anti_pattern_id / repair_class
map without inventing parallel suggestion tables.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


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
        preferred_first_surface='./repo-python kernel.py --entry "<task>" --context-budget 12000',
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
        bad_first_contact_shape="paper lattice opened before an existing stable paper-module slug is selected",
        preferred_first_surface=ENTRY_REPLACEMENT_ROUTE,
        fallback_surface="./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
        why=(
            "Paper lattice is a drilldown after slug selection; the repair class routes to the "
            "canonical entry control packet so the kernel can name an existing paper-module slug first."
        ),
        expected_artifacts=("paper_modules:*",),
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


REPAIR_CLASS_ROUTE_SUGGESTIONS: dict[str, RouteRepairSuggestion] = {
    suggestion.repair_class: suggestion for suggestion in ROUTE_REPAIR_SUGGESTIONS.values()
}


PROCESS_PATTERN_ALIASES: dict[str, str] = {
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
    """Resolve route authority by anti-pattern first, then repair class."""
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
    """Counterfactual hook coverage over recent process-audit anti-patterns."""
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
