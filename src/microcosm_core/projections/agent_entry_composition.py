from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any

from microcosm_core.projections.concept_mechanism_read_model import (
    build_organ_doctrine_rows,
)
from microcosm_core.receipts import write_json_atomic
from microcosm_core.resource_root import microcosm_root
from microcosm_core.schemas import read_json_strict


SCHEMA = "microcosm_agent_entry_composition_projection_v0"
RECEIPT_SCHEMA = "microcosm_agent_entry_composition_receipt_v0"
DEFAULT_TASK = "agent-entry"
CARD_FILENAME = "agent_entry_composition_card.json"
RECEIPT_FILENAME = "agent_entry_composition_receipt.json"
TYPE_A_READER_ID = "type_a_agent"
HUMAN_VIEWER_ID = "human"
ALL_VIEWERS = "all"
VIEWER_IDS = (TYPE_A_READER_ID, HUMAN_VIEWER_ID)
SELECT_VIEWER_COMMAND = (
    "microcosm agent-entry-composition --task agent-entry "
    "--viewer {type_a_agent|human} --card"
)
SOURCE_CHECKOUT_SELECT_VIEWER_COMMAND = (
    "PYTHONPATH=src python3 -m microcosm_core agent-entry-composition "
    "--root . --task agent-entry --viewer {type_a_agent|human} --card"
)
ENTRY_PACKET_REF = "atlas/entry_packet.json"
TASK_ROUTES_REF = "atlas/agent_task_routes.json"
ORGAN_GLANCE_REF = "atlas/agent_task_routes.json::organ_glance_ladder"
ORGAN_REGISTRY_REF = "core/organ_registry.json::implemented_organs"
ORGAN_ATLAS_REF = "core/organ_atlas.json::organs"
EVIDENCE_CLASSES_REF = "core/organ_evidence_classes.json::organ_evidence_classes"
DOCTRINE_ROW_REF = "microcosm_core.projections.concept_mechanism_read_model::build_organ_doctrine_rows"
ORGAN_DISCOVERABILITY_MATRIX_REF = (
    "microcosm_core.projections.organ_discoverability_matrix::"
    "build_organ_discoverability_matrix"
)
ORGAN_DISCOVERABILITY_MATRIX_COMMAND = (
    "microcosm organ-discoverability-matrix --root . --check"
)
MACRO_IMPORT_ROUTE_ORGANS = (
    "cold_reader_route_map",
    "navigation_hologram_route_plane",
    "standards_meta_diagnostics",
    "voice_to_doctrine_self_improvement_loop",
)
REQUIRED_TOP_LEVEL_SOURCE_REFS = (
    ENTRY_PACKET_REF,
    TASK_ROUTES_REF,
    ORGAN_REGISTRY_REF,
    ORGAN_ATLAS_REF,
    EVIDENCE_CLASSES_REF,
    DOCTRINE_ROW_REF,
    ORGAN_DISCOVERABILITY_MATRIX_REF,
)
PROJECTION_AUTHORITY_POSTURE = (
    "derived_projection_not_source_or_release_authority_no_source_mutation_"
    "no_provider_calls_no_private_root_equivalence"
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [item for item in _as_list(value) if isinstance(item, str) and item.strip()]


def _load_json(path: Path) -> dict[str, Any]:
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _rows_by_id(payload: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _as_list(payload.get(key)):
        if not isinstance(row, dict):
            continue
        organ_id = str(row.get("organ_id") or "")
        if organ_id:
            rows[organ_id] = row
    return rows


def _route_rows_by_task(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _as_list(payload.get("routes")):
        if not isinstance(row, dict):
            continue
        task_class = str(row.get("task_class") or "")
        if task_class:
            rows[task_class] = row
    return rows


def _accepted_organ_glance(task_routes: dict[str, Any]) -> dict[str, Any]:
    families = [
        row
        for row in _as_list(task_routes.get("organ_glance_ladder"))
        if isinstance(row, dict)
    ]
    compact_families: list[dict[str, Any]] = []
    join_status_counts: dict[str, int] = {}
    organ_count = 0
    for family in families:
        organs: list[dict[str, Any]] = []
        for row in _as_list(family.get("organs")):
            if not isinstance(row, dict):
                continue
            join_status = str(row.get("capsule_join_status") or "")
            if join_status:
                join_status_counts[join_status] = (
                    join_status_counts.get(join_status, 0) + 1
                )
            authority_ceiling = row.get("authority_ceiling")
            organs.append(
                {
                    "organ_id": row.get("organ_id"),
                    "display_name": row.get("display_name"),
                    "one_line": row.get("one_line"),
                    "card": row.get("card"),
                    "authority_ceiling": authority_ceiling,
                    "claim_ceiling_restated": (
                        row.get("claim_ceiling_restated") or authority_ceiling
                    ),
                    "evidence_class": row.get("evidence_class"),
                    "first_command": row.get("first_command"),
                    "paper_module_ref": row.get("paper_module_ref"),
                    "capsule_id": row.get("capsule_id"),
                    "capsule_join_status": row.get("capsule_join_status"),
                    "card_ref": row.get("card_ref") or row.get("drilldown_target"),
                    "drilldown_target": row.get("drilldown_target"),
                }
            )
        organ_count += len(organs)
        compact_families.append(
            {
                "family_id": family.get("family_id"),
                "label": family.get("label"),
                "organ_count": len(organs),
                "organs": organs,
            }
        )
    capsule_accounting = _as_dict(task_routes.get("capsule_accounting"))
    return {
        "schema": "microcosm_agent_entry_accepted_organ_glance_v0",
        "source_ref": ORGAN_GLANCE_REF,
        "authority_boundary": (
            "Projection/read authority only; organ registry, atlas source rows, "
            "capsule compression, paper modules, receipts, and source files remain "
            "the authority."
        ),
        "family_count": len(compact_families),
        "organ_count": organ_count,
        "capsule_accounting": capsule_accounting,
        "capsule_join_status_counts": dict(sorted(join_status_counts.items())),
        "families": compact_families,
        "first_family_label": compact_families[0].get("label") if compact_families else None,
        "drilldown": "ORGANS.md#microcosm-at-a-glance--every-organ-in-one-line",
        "anti_claim": (
            "This glance is not a release, proof, maturity, source-mutation, "
            "provider-call, private-root-equivalence, or whole-system-correctness "
            "authority."
        ),
    }


def _normalize_task_class(task: str | None) -> str:
    value = (task or "").strip().lower()
    if not value:
        return DEFAULT_TASK
    if value in {
        "agent-entry",
        "agent_entry",
        "type-a-agent",
        "type_a_agent",
        "what is this",
        "what is this?",
        "what-is-this",
        "what_is_this",
    }:
        return "agent-entry"
    if value in {
        "ai-safety",
        "ai_safety",
        "safety",
        "safety-evals",
        "safety_evals",
        "evals",
        "reviewer",
        "skeptical-review",
        "skeptical_reviewer",
        "skeptical-reviewer",
        "ai safety",
        "show me ai safety",
        "show-me-ai-safety",
        "show_me_ai_safety",
        "show me ai-safety",
    }:
        return "ai-safety"
    if value in {
        "evaluate",
        "evaluation",
        "evaluating",
        "how do i evaluate it",
        "how-do-i-evaluate-it",
        "how_do_i_evaluate_it",
        "how do i evaluate this",
        "how-do-i-evaluate-this",
        "how_do_i_evaluate_this",
        "how to evaluate",
        "how-to-evaluate",
        "how_to_evaluate",
        "check",
        "checks",
        "run checks",
        "run-checks",
        "run_checks",
        "run the checks",
        "run-the-checks",
        "run_the_checks",
        "what do receipts mean",
        "what-do-receipts-mean",
        "what_do_receipts_mean",
        "what does this receipt mean",
        "what-does-this-receipt-mean",
        "what_does_this_receipt_mean",
        "what do the receipts mean",
        "what-do-the-receipts-mean",
        "what_do_the_receipts_mean",
        "what does the evidence mean",
        "what-does-the-evidence-mean",
        "what_does_the_evidence_mean",
        "receipt meaning",
        "receipt-meaning",
        "receipt_meaning",
        "evidence meaning",
        "evidence-meaning",
        "evidence_meaning",
    }:
        return "evaluation"
    if value in {
        "interesting",
        "interesting-parts",
        "interesting_parts",
        "show-me-interesting-parts",
        "show_me_interesting_parts",
        "show me interesting parts",
        "show me the interesting parts",
        "show-me-the-interesting-parts",
        "show_me_the_interesting_parts",
        "what is interesting here",
        "what-is-interesting-here",
        "what_is_interesting_here",
        "what's interesting here",
        "whats interesting here",
        "whats-interesting-here",
        "whats_interesting_here",
    }:
        return "interesting-parts"
    if value in {
        "finance",
        "financial",
        "forecasting",
        "market",
        "markets",
        "show me finance",
        "show-me-finance",
        "show_me_finance",
        "show me the finance",
        "show-me-the-finance",
        "show_me_the_finance",
    }:
        return "finance"
    if value in {
        "formal math",
        "math",
        "show me the math",
        "formal",
        "formal-math",
        "formal_math",
        "formal-methods",
        "formal_methods",
        "formal-math-path",
        "formal_math_path",
        "show-me-the-math",
        "show_me_the_math",
        "show me formal methods",
        "show-me-formal-methods",
        "show_me_formal_methods",
    }:
        return "formal-methods"
    if "agent" in value and ("entry" in value or "first" in value or "cold" in value):
        return "agent-entry"
    return value.replace("_", "-").replace(" ", "-")


def _normalize_viewer(viewer: str | None) -> str:
    value = (viewer or ALL_VIEWERS).strip().lower().replace("-", "_")
    if value in {"", ALL_VIEWERS}:
        return ALL_VIEWERS
    if value in {"type_a", "type_a_agent", "agent"}:
        return TYPE_A_READER_ID
    if value in {"human", "human_reader", "operator", "reviewer"}:
        return HUMAN_VIEWER_ID
    return value


def _type_a_reader_row(entry_packet: dict[str, Any]) -> dict[str, Any]:
    selection_card = _as_dict(
        _as_dict(entry_packet.get("reader_first_screen_routes")).get(
            "reader_selection_card"
        )
    )
    for row in _as_list(selection_card.get("selection_rows")):
        if isinstance(row, dict) and row.get("reader_id") == TYPE_A_READER_ID:
            return row
    return {}


def _reader_rows_by_id(entry_packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    selection_card = _as_dict(
        _as_dict(entry_packet.get("reader_first_screen_routes")).get(
            "reader_selection_card"
        )
    )
    rows: dict[str, dict[str, Any]] = {}
    for row in _as_list(selection_card.get("selection_rows")):
        if isinstance(row, dict) and row.get("reader_id"):
            rows[str(row["reader_id"])] = row
    return rows


def _reader_detail_rows_by_id(entry_packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    route_packet = _as_dict(entry_packet.get("reader_first_screen_routes"))
    rows: dict[str, dict[str, Any]] = {}
    for row in _as_list(route_packet.get("routes")):
        if isinstance(row, dict) and row.get("reader_id"):
            rows[str(row["reader_id"])] = row
    return rows


def _source_ref(ref: str, organ_id: str) -> str:
    return f"{ref}[organ_id={organ_id}]"


def _command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return []


def _is_runnable_public_command(command: str, *, allow_project_placeholder: bool = False) -> bool:
    if not command or any(
        banned in command
        for banned in (
            "raw_seed.md",
            "obsidian/",
            "provider payload",
            "operator thread",
            "HUD/browser",
        )
    ):
        return False
    if "<" in command or ">" in command:
        if not allow_project_placeholder:
            return False
        if command.count("<project>") != 1:
            return False
    tokens = _command_tokens(command)
    if not tokens:
        return False
    if tokens[0] == "microcosm":
        return True
    if len(tokens) >= 5 and tokens[0].startswith("PYTHONPATH=") and tokens[1:4] == [
        "python3",
        "-m",
        "microcosm_core.organs.navigation_hologram_route_plane",
    ]:
        return True
    if len(tokens) >= 4 and tokens[0].startswith("PYTHONPATH=") and tokens[1:3] == [
        "python3",
        "-m",
    ]:
        return tokens[3].startswith("microcosm_core.")
    if len(tokens) >= 3 and tokens[0] in {"python", "python3"} and tokens[1] == "-m":
        return tokens[2].startswith("microcosm_core.")
    return False


def _list_has_text(values: Any) -> bool:
    return any(bool(item.strip()) for item in _strings(values))


def _doctrine_rows_by_organ(root: Path) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("organ_id")): row
        for row in build_organ_doctrine_rows(root)
        if isinstance(row, dict) and row.get("organ_id")
    }


def _viewer_mode(
    *,
    viewer_id: str,
    first_action: str,
    next_action: str | None,
    branch_label: str,
    viewer_question: str,
    authority_boundary: str,
    evidence_refs: list[str],
    stop_condition: str,
    reentry_condition: str,
    anti_overread_warning: str,
    drilldown_if_needed: list[str],
    source_refs: list[str],
    task_class: str,
) -> dict[str, Any]:
    return {
        "viewer": viewer_id,
        "viewer_family": viewer_id,
        "task_class": task_class,
        "branch_label": branch_label,
        "viewer_question": viewer_question,
        "first_safe_action": first_action,
        "next_action": next_action,
        "authority_boundary": authority_boundary,
        "evidence_refs": evidence_refs,
        "stop_condition": stop_condition,
        "reentry_condition": reentry_condition,
        "anti_overread_warning": anti_overread_warning,
        "drilldown_if_needed": drilldown_if_needed,
        "source_refs": source_refs,
    }


def _entry_experience_check(mode: dict[str, Any]) -> dict[str, Any]:
    first_action = str(mode.get("first_safe_action") or "")
    authority_boundary = str(mode.get("authority_boundary") or "")
    anti_overread = str(mode.get("anti_overread_warning") or "")
    stop_condition = str(mode.get("stop_condition") or "")
    reentry_condition = str(mode.get("reentry_condition") or "")
    evidence_refs = mode.get("evidence_refs")
    branch_label = str(mode.get("branch_label") or "")
    failure_codes: list[str] = []

    first_action_visible = _is_runnable_public_command(
        first_action, allow_project_placeholder=True
    )
    if not first_action_visible:
        failure_codes.append("missing_viewer_first_action")

    authority_boundary_visible = bool(authority_boundary) and any(
        token in authority_boundary.lower()
        for token in ("not", "no ", "does not", "authority", "boundary")
    )
    if not authority_boundary_visible:
        failure_codes.append("missing_viewer_authority_boundary")

    evidence_ref_visible = _list_has_text(evidence_refs)
    if not evidence_ref_visible:
        failure_codes.append("missing_viewer_evidence_ref")

    stop_condition_visible = bool(stop_condition.strip())
    if not stop_condition_visible:
        failure_codes.append("missing_viewer_stop_condition")

    reentry_condition_visible = bool(reentry_condition.strip()) and "re-entry" in (
        reentry_condition.lower()
    )
    if not reentry_condition_visible:
        failure_codes.append("missing_viewer_reentry_condition")

    anti_overread_warning_visible = bool(anti_overread.strip()) and any(
        token in anti_overread.lower()
        for token in ("not", "do not", "does not", "no ")
    )
    if not anti_overread_warning_visible:
        failure_codes.append("missing_viewer_anti_overread_warning")

    route_scent = "strong"
    if not branch_label.strip() or "reader" in branch_label.lower():
        route_scent = "weak"
        failure_codes.append("weak_viewer_route_label")

    return {
        "schema": "microcosm_entry_experience_check_v0",
        "viewer": mode.get("viewer"),
        "task_class": mode.get("task_class"),
        "status": "pass" if not failure_codes else "blocked",
        "first_action_visible": first_action_visible,
        "authority_boundary_visible": authority_boundary_visible,
        "evidence_ref_visible": evidence_ref_visible,
        "stop_condition_visible": stop_condition_visible,
        "reentry_condition_visible": reentry_condition_visible,
        "anti_overread_warning_visible": anti_overread_warning_visible,
        "route_scent": route_scent,
        "failure_codes": failure_codes,
    }


def _viewer_route_summary(mode: dict[str, Any]) -> dict[str, Any]:
    return {
        "viewer": mode.get("viewer"),
        "branch_label": mode.get("branch_label"),
        "first_safe_action": mode.get("first_safe_action"),
        "next_action": mode.get("next_action"),
        "authority_boundary": mode.get("authority_boundary"),
        "evidence_refs": mode.get("evidence_refs"),
        "stop_condition": mode.get("stop_condition"),
        "reentry_condition": mode.get("reentry_condition"),
        "anti_overread_warning": mode.get("anti_overread_warning"),
        "source_refs": mode.get("source_refs"),
    }


def _selected_viewer_route(
    selected_viewer: str, viewer_modes: list[dict[str, Any]]
) -> dict[str, Any]:
    viewer_by_id = {str(row.get("viewer")): row for row in viewer_modes}
    if selected_viewer != ALL_VIEWERS:
        return _as_dict(viewer_by_id.get(selected_viewer))
    routes = {
        viewer_id: _viewer_route_summary(_as_dict(viewer_by_id.get(viewer_id)))
        for viewer_id in VIEWER_IDS
    }
    return {
        "schema": "microcosm_selected_viewer_route_set_v0",
        "viewer": ALL_VIEWERS,
        "route_kind": "viewer_route_set",
        "viewer_families": list(VIEWER_IDS),
        "requires_viewer_selection": True,
        "selection_command": SELECT_VIEWER_COMMAND,
        "source_checkout_selection_command": SOURCE_CHECKOUT_SELECT_VIEWER_COMMAND,
        "routes": routes,
        "first_safe_actions": {
            viewer_id: route.get("first_safe_action")
            for viewer_id, route in routes.items()
        },
        "authority_boundary": (
            "Route-set projection/read authority only; select one viewer branch "
            "before treating first_action or next_action as an execution plan."
        ),
    }


def _selected_viewer_entry(selected_viewer_route: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "microcosm_selected_viewer_entry_v0",
        "viewer": selected_viewer_route.get("viewer"),
        "route_kind": selected_viewer_route.get("route_kind", "single_viewer_route"),
        "first_safe_action": selected_viewer_route.get("first_safe_action"),
        "first_safe_actions": selected_viewer_route.get("first_safe_actions"),
        "next_action": selected_viewer_route.get("next_action"),
        "authority_boundary": selected_viewer_route.get("authority_boundary"),
        "evidence_refs": selected_viewer_route.get("evidence_refs"),
        "stop_condition": selected_viewer_route.get("stop_condition"),
        "reentry_condition": selected_viewer_route.get("reentry_condition"),
        "salience_rule": (
            "Read this selected viewer entry before the Type A route body floor, "
            "macro curriculum, or broad organ inventory."
        ),
    }


def _build_read_run_order(
    *,
    selected_viewer: str,
    selected_viewer_route: dict[str, Any],
    first_screen_route: dict[str, Any],
    task_route_card: dict[str, Any],
    accepted_organ_glance: dict[str, Any],
    macro_floor: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    viewer_step = {
        "step": 1,
        "kind": "selected_viewer_route",
        "run": selected_viewer_route.get("first_safe_action")
        or selected_viewer_route.get("first_safe_actions"),
        "read": selected_viewer_route.get("source_refs")
        or {
            viewer_id: route.get("source_refs")
            for viewer_id, route in _as_dict(
                selected_viewer_route.get("routes")
            ).items()
        },
        "why": (
            "Start from the selected viewer branch so humans do not wade through "
            "Type A macro curriculum and controllers do not special-case --viewer all."
        ),
    }
    shared_steps = [
        {
            "kind": "first_screen",
            "run": first_screen_route.get("route_command"),
            "read": first_screen_route.get("source_ref"),
            "why": "Establish the Type A first-screen route and claim ceiling before mutation.",
        },
        {
            "kind": "task_route",
            "run": task_route_card.get("first_command"),
            "read": task_route_card.get("source_ref"),
            "why": "Dereference the task class into relevant organs, evidence refs, and stop conditions.",
        },
        {
            "kind": "accepted_organ_glance",
            "run": None,
            "read": [
                accepted_organ_glance.get("source_ref"),
                accepted_organ_glance.get("drilldown"),
            ],
            "why": (
                "Read one line per accepted organ before treating the matrix or "
                "macro floor as the system itself."
            ),
        },
        {
            "kind": "organ_discoverability_matrix",
            "run": ORGAN_DISCOVERABILITY_MATRIX_COMMAND,
            "read": [ORGAN_DISCOVERABILITY_MATRIX_REF],
            "why": (
                "Use the matrix to classify accepted-organ discoverability gaps "
                "before per-organ patching or generated-route work."
            ),
        },
        {
            "kind": "macro_body_floor",
            "run": [row.get("first_command") for row in macro_floor],
            "read": [row.get("standards", {}).get("paper_module_ref") for row in macro_floor],
            "why": "Use imported macro route bodies as the mechanism curriculum before broad inventory.",
        },
    ]
    if selected_viewer == HUMAN_VIEWER_ID:
        task_class = str(task_route_card.get("task_class") or DEFAULT_TASK)
        if task_class == DEFAULT_TASK:
            order = [
                viewer_step,
                {
                    "kind": "optional_drilldown_after_human_first_action",
                    "run": selected_viewer_route.get("next_action"),
                    "read": selected_viewer_route.get("drilldown_if_needed"),
                    "why": (
                        "Human entry stops at hello/tour unless the operator asks for "
                        "evidence or owner-surface drilldown."
                    ),
                },
            ]
        else:
            order = [
                viewer_step,
                {
                    "kind": "selected_task_route_after_human_entry",
                    "run": task_route_card.get("first_command"),
                    "read": [
                        task_route_card.get("source_ref"),
                        task_route_card.get("drilldown_target"),
                    ],
                    "why": (
                        "A task-specific human entry should expose the selected route "
                        "command, card, and authority ceiling before broad inventory."
                    ),
                },
            ]
    else:
        order = [viewer_step, *shared_steps]
    return [{**row, "step": index + 1} for index, row in enumerate(order)]


def _build_viewer_modes(
    *,
    entry_packet: dict[str, Any],
    first_screen_route: dict[str, Any],
    task_route_card: dict[str, Any],
    omission_receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    reader_rows = _reader_rows_by_id(entry_packet)
    reader_detail_rows = _reader_detail_rows_by_id(entry_packet)
    type_a_detail = _as_dict(reader_detail_rows.get(TYPE_A_READER_ID))
    public_reader = _as_dict(reader_rows.get("public_github_visitor"))
    shared_prerequisite = str(
        _as_dict(entry_packet.get("reader_first_screen_routes")).get(
            "shared_prerequisite_command"
        )
        or "microcosm tour --card <project>"
    )
    task_class = str(task_route_card.get("task_class") or DEFAULT_TASK)
    task_evidence = [
        str(task_route_card.get("source_ref") or ""),
        str(task_route_card.get("evidence_ref") or ""),
        str(task_route_card.get("receipt_ref") or ""),
    ]
    task_evidence.extend(
        str(row.get("evidence_refs", {}).get("current_authority_receipt") or "")
        for row in _as_list(task_route_card.get("relevant_organs"))
        if isinstance(row, dict)
    )
    task_evidence = [ref for ref in task_evidence if ref]

    type_a_mode = _viewer_mode(
        viewer_id=TYPE_A_READER_ID,
        task_class=task_class,
        branch_label="Type A agent entry",
        viewer_question=str(first_screen_route.get("cold_question") or ""),
        first_action=str(first_screen_route.get("route_command") or ""),
        next_action=str(
            type_a_detail.get("next_command")
            or task_route_card.get("first_command")
            or ""
        ),
        authority_boundary=(
            f"{first_screen_route.get('authority_ceiling')}. "
            f"{task_route_card.get('authority_boundary')}"
        ),
        evidence_refs=task_evidence,
        stop_condition=str(first_screen_route.get("stop_when") or ""),
        reentry_condition=str(omission_receipt.get("reentry_condition") or ""),
        anti_overread_warning=str(first_screen_route.get("anti_overread") or ""),
        drilldown_if_needed=[
            str(first_screen_route.get("source_ref") or ""),
            str(task_route_card.get("source_ref") or ""),
            str(task_route_card.get("drilldown_target") or ""),
            str(type_a_detail.get("followup_command") or ""),
        ],
        source_refs=[
            str(first_screen_route.get("source_ref") or ""),
            str(task_route_card.get("source_ref") or ""),
        ],
    )

    human_first_action = str(public_reader.get("route_command") or "microcosm hello <project>")
    human_stop = str(
        public_reader.get("stop_when")
        or "You can name what the card proves, what it only projects, and which authority claims it refuses."
    )
    human_anti_overread = str(
        public_reader.get("anti_overread")
        or "Do not treat an entry projection as release, proof, source, provider, or private-root authority."
    )
    human_source_ref = (
        "atlas/entry_packet.json::reader_first_screen_routes."
        "reader_selection_card.selection_rows[reader_id=public_github_visitor]"
    )
    human_next_action = shared_prerequisite
    human_stop_condition = human_stop
    if task_class != DEFAULT_TASK:
        human_next_action = str(task_route_card.get("first_command") or shared_prerequisite)
        human_stop_condition = (
            "You can name the selected task route, primary organ, evidence class, "
            "first command, and authority ceiling without claiming domain correctness."
        )
    human_mode = _viewer_mode(
        viewer_id=HUMAN_VIEWER_ID,
        task_class=task_class,
        branch_label="Human entry",
        viewer_question=(
            "What should a human read or run first, and what trust boundary should they keep?"
        ),
        first_action=human_first_action,
        next_action=human_next_action,
        authority_boundary=(
            "Human entry is interpretive/read authority only; it does not authorize "
            "release, proof correctness, source mutation, provider calls, hosted "
            "deployment, private-root equivalence, or whole-system correctness."
        ),
        evidence_refs=[
            human_source_ref,
            str(task_route_card.get("receipt_ref") or ""),
            str(task_route_card.get("evidence_ref") or ""),
        ],
        stop_condition=human_stop_condition,
        reentry_condition=str(omission_receipt.get("reentry_condition") or ""),
        anti_overread_warning=human_anti_overread,
        drilldown_if_needed=[
            "README.md::Public Repo Map",
            "AGENTS.md::Fast Entry For Cold Agents",
            str(task_route_card.get("source_ref") or ""),
            str(task_route_card.get("drilldown_target") or ""),
        ],
        source_refs=[
            human_source_ref,
            "README.md::Public Repo Map",
            str(task_route_card.get("source_ref") or ""),
        ],
    )
    return [type_a_mode, human_mode]


def _organ_card(
    *,
    organ_id: str,
    registry_by_id: dict[str, dict[str, Any]],
    atlas_by_id: dict[str, dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
    doctrine_by_id: dict[str, dict[str, Any]],
    role: str,
) -> dict[str, Any]:
    registry = _as_dict(registry_by_id.get(organ_id))
    atlas = _as_dict(atlas_by_id.get(organ_id))
    evidence = _as_dict(evidence_by_id.get(organ_id))
    doctrine = _as_dict(doctrine_by_id.get(organ_id))
    surface_refs = _as_dict(doctrine.get("surface_refs"))
    first_command = str(atlas.get("first_command") or registry.get("validator_command") or "")
    receipt_refs = _strings(registry.get("generated_receipts"))
    current_authority = str(registry.get("current_authority_receipt") or "")
    if current_authority and current_authority not in receipt_refs:
        receipt_refs = [current_authority, *receipt_refs]
    return {
        "organ_id": organ_id,
        "role": role,
        "display_name": atlas.get("display_name") or organ_id.replace("_", " ").title(),
        "family": atlas.get("family"),
        "evidence_class": registry.get("evidence_class") or evidence.get("evidence_class"),
        "evidence_strength_rank": registry.get("evidence_strength_rank"),
        "first_command": first_command,
        "command_runnable_shape": _is_runnable_public_command(first_command),
        "claim_ceiling": atlas.get("claim_ceiling_restated") or registry.get("claim_ceiling"),
        "wiring_note": atlas.get("wiring_note"),
        "agent_gloss": atlas.get("agent_gloss"),
        "evidence_refs": {
            "registry": _source_ref(ORGAN_REGISTRY_REF, organ_id),
            "atlas": _source_ref(ORGAN_ATLAS_REF, organ_id),
            "evidence_class": _source_ref(EVIDENCE_CLASSES_REF, organ_id),
            "current_authority_receipt": current_authority,
            "receipt_refs": receipt_refs,
        },
        "standards": {
            "standard_ref": surface_refs.get("standard"),
            "standards_registry_ref": surface_refs.get("standards_registry"),
            "paper_module_ref": surface_refs.get("paper_module") or atlas.get("paper_module_ref"),
            "concept_ref": doctrine.get("concept_binding")
            and f"organ_doctrine_row:{organ_id}.concept_binding",
            "mechanism_ref": doctrine.get("mechanism_binding")
            and f"organ_doctrine_row:{organ_id}.mechanism_binding",
        },
        "authority_boundary": (
            "organ_card_projection_not_source_authority_"
            "read_refs_before_receipt_or_source_drilldown"
        ),
    }


def _add_error(errors: list[dict[str, str]], *, path: str, code: str, message: str) -> None:
    errors.append({"path": path, "code": code, "message": message})


def validate_agent_entry_composition(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    if payload.get("schema") != SCHEMA:
        _add_error(
            errors,
            path="schema",
            code="bad_schema",
            message=f"Agent entry composition must use {SCHEMA}.",
        )
    if payload.get("authority_posture") != PROJECTION_AUTHORITY_POSTURE:
        _add_error(
            errors,
            path="authority_posture",
            code="bad_authority_posture",
            message="Projection must identify itself as non-source, non-release authority.",
        )
    source_refs = set(_strings(payload.get("source_refs")))
    for ref in REQUIRED_TOP_LEVEL_SOURCE_REFS:
        if ref not in source_refs:
            _add_error(
                errors,
                path="source_refs",
                code="missing_source_ref",
                message=f"Projection source refs must include {ref}.",
            )
    first_screen = _as_dict(payload.get("first_screen_type_a_route"))
    if first_screen.get("reader_id") != TYPE_A_READER_ID:
        _add_error(
            errors,
            path="first_screen_type_a_route.reader_id",
            code="missing_type_a_reader_route",
            message="Projection must compose the Type A first-screen reader route.",
        )
    if not _is_runnable_public_command(
        str(first_screen.get("route_command") or ""),
        allow_project_placeholder=True,
    ):
        _add_error(
            errors,
            path="first_screen_type_a_route.route_command",
            code="first_screen_command_not_runnable_shape",
            message="Type A first-screen command must be a runnable public command shape.",
        )

    task_route = _as_dict(payload.get("task_route"))
    if task_route.get("selected_task_route_found") is not True:
        _add_error(
            errors,
            path="task_route.selected_task_class",
            code="missing_selected_task_route",
            message="Projection must dereference the selected task route.",
        )
    if not _is_runnable_public_command(str(task_route.get("first_command") or "")):
        _add_error(
            errors,
            path="task_route.first_command",
            code="task_route_command_not_runnable_shape",
            message="Selected task route must preserve a runnable public command.",
        )
    glance = _as_dict(payload.get("accepted_organ_glance"))
    if glance.get("schema") != "microcosm_agent_entry_accepted_organ_glance_v0":
        _add_error(
            errors,
            path="accepted_organ_glance.schema",
            code="missing_accepted_organ_glance",
            message="Projection must expose the accepted-organ one-line glance.",
        )
    if glance.get("source_ref") != ORGAN_GLANCE_REF:
        _add_error(
            errors,
            path="accepted_organ_glance.source_ref",
            code="accepted_organ_glance_source_ref_missing",
            message="Accepted-organ glance must source from agent_task_routes organ_glance_ladder.",
        )
    if glance.get("first_family_label") != "Entry & Reveal":
        _add_error(
            errors,
            path="accepted_organ_glance.first_family_label",
            code="accepted_organ_glance_wrong_family_order",
            message="Accepted-organ glance must keep Entry & Reveal first.",
        )
    glance_organs = [
        organ
        for family in _as_list(glance.get("families"))
        if isinstance(family, dict)
        for organ in _as_list(family.get("organs"))
        if isinstance(organ, dict)
    ]
    accounting = _as_dict(glance.get("capsule_accounting"))
    accepted_count = accounting.get("accepted_organ_count")
    if accepted_count != len(glance_organs) or glance.get("organ_count") != len(glance_organs):
        _add_error(
            errors,
            path="accepted_organ_glance.organ_count",
            code="accepted_organ_glance_count_mismatch",
            message="Accepted-organ glance must preserve one row per accepted organ.",
        )
    for index, organ in enumerate(glance_organs):
        missing = [
            field
            for field in (
                "organ_id",
                "display_name",
                "one_line",
                "card",
                "authority_ceiling",
                "claim_ceiling_restated",
                "evidence_class",
                "first_command",
                "paper_module_ref",
                "capsule_id",
                "capsule_join_status",
                "card_ref",
                "drilldown_target",
            )
            if not str(organ.get(field) or "").strip()
        ]
        if missing:
            _add_error(
                errors,
                path=f"accepted_organ_glance.organs[{index}]",
                code="accepted_organ_glance_row_incomplete",
                message=f"Accepted-organ glance row is missing: {', '.join(missing)}.",
            )
    discoverability_route = _as_dict(payload.get("organ_discoverability_matrix_route"))
    if not _is_runnable_public_command(str(discoverability_route.get("run") or "")):
        _add_error(
            errors,
            path="organ_discoverability_matrix_route.run",
            code="discoverability_matrix_command_not_runnable_shape",
            message="Entry card must expose the accepted-organ discoverability matrix command.",
        )
    if ORGAN_DISCOVERABILITY_MATRIX_REF not in _strings(discoverability_route.get("read")):
        _add_error(
            errors,
            path="organ_discoverability_matrix_route.read",
            code="discoverability_matrix_source_ref_missing",
            message="Entry card must keep the matrix source projection ref visible.",
        )

    macro_floor = _as_list(payload.get("macro_import_route_body_floor"))
    macro_ids = {str(row.get("organ_id") or "") for row in macro_floor if isinstance(row, dict)}
    for organ_id in MACRO_IMPORT_ROUTE_ORGANS:
        if organ_id not in macro_ids:
            _add_error(
                errors,
                path="macro_import_route_body_floor",
                code="missing_macro_import_route_body",
                message=f"Projection must include macro route body floor organ {organ_id}.",
            )
    for index, row_value in enumerate(macro_floor):
        row = _as_dict(row_value)
        row_path = f"macro_import_route_body_floor[{row.get('organ_id') or index}]"
        if not row.get("command_runnable_shape"):
            _add_error(
                errors,
                path=f"{row_path}.first_command",
                code="macro_body_command_not_runnable_shape",
                message="Macro route body floor rows must preserve runnable public commands.",
            )
        evidence_refs = _as_dict(row.get("evidence_refs"))
        if not evidence_refs.get("current_authority_receipt") and not _strings(
            evidence_refs.get("receipt_refs")
        ):
            _add_error(
                errors,
                path=f"{row_path}.evidence_refs",
                code="macro_body_missing_evidence_refs",
                message="Macro route body floor rows must preserve receipt evidence refs.",
            )
        standards = _as_dict(row.get("standards"))
        if not standards.get("standard_ref") or not standards.get("mechanism_ref"):
            _add_error(
                errors,
                path=f"{row_path}.standards",
                code="macro_body_missing_standard_or_mechanism_ref",
                message="Macro route body floor rows must preserve standard and mechanism refs.",
            )

    omission = _as_dict(payload.get("omission_receipt"))
    if "re-entry" not in str(omission.get("reentry_condition", "")).lower():
        _add_error(
            errors,
            path="omission_receipt.reentry_condition",
            code="missing_reentry_condition",
            message="Projection must include a concrete re-entry condition.",
        )
    viewer_modes = _as_list(payload.get("viewer_modes"))
    viewer_by_id = {
        str(row.get("viewer") or ""): row
        for row in viewer_modes
        if isinstance(row, dict) and row.get("viewer")
    }
    for viewer_id in VIEWER_IDS:
        mode = _as_dict(viewer_by_id.get(viewer_id))
        if not mode:
            _add_error(
                errors,
                path="viewer_modes",
                code="missing_viewer_mode",
                message=f"Projection must include viewer mode {viewer_id}.",
            )
            continue
        check = _entry_experience_check(mode)
        if check["status"] != "pass":
            _add_error(
                errors,
                path=f"viewer_modes[{viewer_id}]",
                code="viewer_entry_experience_blocked",
                message=(
                    f"Viewer mode {viewer_id} lacks route scent fields: "
                    f"{', '.join(check['failure_codes'])}."
                ),
            )
    checks = _as_list(payload.get("entry_experience_checks"))
    check_by_viewer = {
        str(row.get("viewer") or ""): row
        for row in checks
        if isinstance(row, dict) and row.get("viewer")
    }
    for viewer_id in VIEWER_IDS:
        check = _as_dict(check_by_viewer.get(viewer_id))
        if not check or check.get("status") != "pass":
            _add_error(
                errors,
                path=f"entry_experience_checks[{viewer_id}]",
                code="viewer_entry_experience_check_not_passed",
                message=f"Entry experience check must pass for {viewer_id}.",
            )
    router = _as_dict(payload.get("viewer_first_action_router"))
    router_routes = _as_dict(router.get("routes"))
    for viewer_id in VIEWER_IDS:
        route = _as_dict(router_routes.get(viewer_id))
        if not _is_runnable_public_command(
            str(route.get("first_safe_action") or ""),
            allow_project_placeholder=True,
        ):
            _add_error(
                errors,
                path=f"viewer_first_action_router.routes[{viewer_id}]",
                code="viewer_router_missing_first_action",
                message=f"Viewer first-action router must expose {viewer_id}.",
            )
    selected_viewer = _normalize_viewer(str(payload.get("selected_viewer") or ALL_VIEWERS))
    selected_route = _as_dict(payload.get("selected_viewer_route"))
    if selected_viewer == ALL_VIEWERS:
        selected_routes = _as_dict(selected_route.get("routes"))
        if selected_route.get("viewer") != ALL_VIEWERS or not all(
            _as_dict(selected_routes.get(viewer_id)).get("viewer") == viewer_id
            for viewer_id in VIEWER_IDS
        ):
            _add_error(
                errors,
                path="selected_viewer_route.routes",
                code="selected_viewer_route_set_missing",
                message="All-viewer payload must expose a stable selected_viewer_route route set.",
            )
    else:
        if selected_route.get("viewer") != selected_viewer:
            _add_error(
                errors,
                path="selected_viewer_route.viewer",
                code="selected_viewer_route_missing",
                message="Selected viewer route must match selected_viewer.",
            )
    if payload.get("release_authority") is not False or payload.get("source_mutation_authority") is not False:
        _add_error(
            errors,
            path="authority_flags",
            code="projection_overclaims_authority",
            message="Projection must explicitly deny release and source-mutation authority.",
        )
    return {
        "schema": f"{SCHEMA}_validation_v0",
        "status": "pass" if not errors else "blocked",
        "error_count": len(errors),
        "errors": errors,
    }


def build_agent_entry_composition(
    *,
    root: str | Path | None = None,
    task: str | None = None,
    viewer: str | None = None,
    command: str = "agent-entry-composition",
) -> dict[str, Any]:
    resolved_root = Path(root).resolve() if root is not None else microcosm_root()
    entry_packet = _load_json(resolved_root / ENTRY_PACKET_REF)
    task_routes = _load_json(resolved_root / TASK_ROUTES_REF)
    registry = _load_json(resolved_root / "core/organ_registry.json")
    atlas = _load_json(resolved_root / "core/organ_atlas.json")
    evidence = _load_json(resolved_root / "core/organ_evidence_classes.json")

    registry_by_id = _rows_by_id(registry, "implemented_organs")
    atlas_by_id = _rows_by_id(atlas, "organs")
    evidence_by_id = _rows_by_id(evidence, "organ_evidence_classes")
    doctrine_by_id = _doctrine_rows_by_organ(resolved_root)
    route_by_task = _route_rows_by_task(task_routes)
    task_class = _normalize_task_class(task)
    selected_viewer = _normalize_viewer(viewer)
    selected_task_route_found = task_class in route_by_task
    selected_route = _as_dict(route_by_task.get(task_class) or route_by_task.get(DEFAULT_TASK))
    type_a_row = _type_a_reader_row(entry_packet)
    accepted_organ_glance = _accepted_organ_glance(task_routes)

    relevant_organs = [
        _organ_card(
            organ_id=str(row.get("organ_id") or ""),
            registry_by_id=registry_by_id,
            atlas_by_id=atlas_by_id,
            evidence_by_id=evidence_by_id,
            doctrine_by_id=doctrine_by_id,
            role="agent_entry_task_route_relevant_organ",
        )
        for row in _as_list(selected_route.get("relevant_organs"))
        if isinstance(row, dict) and row.get("organ_id")
    ]
    macro_floor = [
        _organ_card(
            organ_id=organ_id,
            registry_by_id=registry_by_id,
            atlas_by_id=atlas_by_id,
            evidence_by_id=evidence_by_id,
            doctrine_by_id=doctrine_by_id,
            role="macro_import_route_body_floor",
        )
        for organ_id in MACRO_IMPORT_ROUTE_ORGANS
    ]
    first_screen_route = {
        "source_ref": (
            "atlas/entry_packet.json::reader_first_screen_routes."
            "reader_selection_card.selection_rows[reader_id=type_a_agent]"
        ),
        "reader_id": type_a_row.get("reader_id"),
        "cold_question": type_a_row.get("cold_question"),
        "route_command": type_a_row.get("route_command"),
        "trust_signal": type_a_row.get("trust_signal"),
        "stop_when": type_a_row.get("stop_when"),
        "anti_overread": type_a_row.get("anti_overread"),
        "shared_prerequisite_command": _as_dict(
            entry_packet.get("reader_first_screen_routes")
        ).get("shared_prerequisite_command"),
        "authority_ceiling": _as_dict(entry_packet.get("local_first_screen_route")).get(
            "authority"
        ),
    }
    task_route_card = {
        "source_ref": (
            f"atlas/agent_task_routes.json::routes[task_class={selected_route.get('task_class')}]"
        ),
        "requested_task": task or DEFAULT_TASK,
        "selected_task_class": task_class,
        "selected_task_route_found": selected_task_route_found,
        "task_class": selected_route.get("task_class"),
        "primary_organ_id": selected_route.get("primary_organ_id"),
        "primary_display_name": selected_route.get("primary_display_name"),
        "first_command": selected_route.get("first_command"),
        "authority_ceiling": selected_route.get("allowed_authority"),
        "authority_boundary": selected_route.get("authority_boundary"),
        "drilldown_target": selected_route.get("drilldown_target"),
        "evidence_ref": selected_route.get("evidence_ref"),
        "receipt_ref": selected_route.get("receipt_ref"),
        "organ_count": selected_route.get("organ_count"),
        "relevant_organs": relevant_organs,
    }
    omission_receipt = {
        "omitted": [
            "full organ source bodies",
            "full generated public docs",
            "raw operator voice or private root state",
            "provider/HUD/browser/account/session payloads",
            "full receipt payload bodies",
        ],
        "reason": (
            "This card composes route handles, commands, evidence refs, standards, "
            "and authority ceilings for cold-agent entry. Detailed proof remains "
            "behind the named source and receipt surfaces."
        ),
        "reentry_condition": (
            "Re-entry when a task route, macro organ row, first-screen Type A row, "
            "viewer-mode route scent, or evidence/standard ref changes; rebuild "
            "this projection from the source JSON rather than editing generated "
            "docs or inventing labels."
        ),
        "drilldown": [
            ENTRY_PACKET_REF,
            TASK_ROUTES_REF,
            ORGAN_REGISTRY_REF,
            ORGAN_ATLAS_REF,
            EVIDENCE_CLASSES_REF,
        ],
    }
    viewer_modes = _build_viewer_modes(
        entry_packet=entry_packet,
        first_screen_route=first_screen_route,
        task_route_card=task_route_card,
        omission_receipt=omission_receipt,
    )
    entry_experience_checks = [_entry_experience_check(mode) for mode in viewer_modes]
    selected_viewer_route = _selected_viewer_route(selected_viewer, viewer_modes)
    selected_viewer_entry = _selected_viewer_entry(selected_viewer_route)
    read_run_order = _build_read_run_order(
        selected_viewer=selected_viewer,
        selected_viewer_route=selected_viewer_route,
        first_screen_route=first_screen_route,
        task_route_card=task_route_card,
        accepted_organ_glance=accepted_organ_glance,
        macro_floor=macro_floor,
    )
    viewer_first_action_router = {
        "schema": "microcosm_viewer_first_action_router_v0",
        "viewer_families": list(VIEWER_IDS),
        "select_viewer_command": SELECT_VIEWER_COMMAND,
        "source_checkout_select_viewer_command": SOURCE_CHECKOUT_SELECT_VIEWER_COMMAND,
        "source_checkout_boundary": (
            "Source-checkout command is a no-install invocation hint only; it "
            "does not add source-mutation, release, provider-call, proof, or "
            "private-root authority."
        ),
        "routes": {
            row["viewer"]: {
                "first_safe_action": row.get("first_safe_action"),
                "next_action": row.get("next_action"),
                "authority_boundary": row.get("authority_boundary"),
                "stop_condition": row.get("stop_condition"),
                "reentry_condition": row.get("reentry_condition"),
            }
            for row in viewer_modes
            if row.get("viewer")
        },
        "anti_overread": (
            "Viewer routing is projection/read authority only; it does not "
            "grant source, proof, release, provider-call, or private-root "
            "authority."
        ),
    }

    payload = {
        "schema": SCHEMA,
        "status": "draft_pending_validation",
        "surface_role": "TASK_CONDITIONED_AGENT_ENTRY_COMPOSITION_CARD",
        "authority_posture": PROJECTION_AUTHORITY_POSTURE,
        "source_refs": list(REQUIRED_TOP_LEVEL_SOURCE_REFS),
        "task": task or DEFAULT_TASK,
        "selected_viewer": selected_viewer,
        "selected_viewer_entry": selected_viewer_entry,
        "selected_viewer_route": selected_viewer_route,
        "viewer_first_action_router": viewer_first_action_router,
        "release_authority": False,
        "source_mutation_authority": False,
        "provider_call_authority": False,
        "private_root_equivalence_authority": False,
        "first_screen_type_a_route": first_screen_route,
        "task_route": task_route_card,
        "accepted_organ_glance": accepted_organ_glance,
        "viewer_modes": viewer_modes,
        "entry_experience_checks": entry_experience_checks,
        "organ_discoverability_matrix_route": {
            "schema": "microcosm_organ_discoverability_matrix_entry_route_v0",
            "run": ORGAN_DISCOVERABILITY_MATRIX_COMMAND,
            "read": [
                ORGAN_DISCOVERABILITY_MATRIX_REF,
                ORGAN_REGISTRY_REF,
                ORGAN_ATLAS_REF,
                TASK_ROUTES_REF,
                EVIDENCE_CLASSES_REF,
            ],
            "authority_boundary": (
                "Projection/read authority only; source rows, receipts, standards, "
                "paper modules, and builders remain authority."
            ),
            "why": (
                "Before choosing an organ-specific repair, inspect the all-organ "
                "matrix for first command, authority ceiling, evidence class, "
                "paper module, proof receipt, owner route, and gap codes."
            ),
        },
        "macro_import_route_body_floor": macro_floor,
        "read_run_order": read_run_order,
        "omission_receipt": omission_receipt,
        "anti_claim": (
            "This is a route-mining and mechanism-curriculum projection. It does not "
            "replace atlas/entry_packet.json, atlas/agent_task_routes.json, organ "
            "registries, source modules, receipts, standards, or release decisions."
        ),
        "command": command,
    }
    validation = validate_agent_entry_composition(payload)
    payload["validation"] = validation
    payload["errors"] = validation["errors"]
    payload["status"] = validation["status"]
    return payload


def compact_agent_entry_card(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the first-entry view without expanding every organ row."""
    def drop_none(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: drop_none(row) for key, row in value.items() if row is not None}
        if isinstance(value, list):
            return [drop_none(row) for row in value]
        return value

    selected_viewer_route = _as_dict(payload.get("selected_viewer_route"))
    first_screen_route = _as_dict(payload.get("first_screen_type_a_route"))
    task_route = _as_dict(payload.get("task_route"))
    accepted_glance = _as_dict(payload.get("accepted_organ_glance"))
    organ_route = _as_dict(payload.get("organ_discoverability_matrix_route"))
    omission_receipt = _as_dict(payload.get("omission_receipt"))
    validation = _as_dict(payload.get("validation"))
    macro_floor = [
        {
            "organ_id": row.get("organ_id"),
            "display_name": row.get("display_name"),
            "first_command": row.get("first_command"),
            "evidence_class": row.get("evidence_class"),
            "claim_ceiling": row.get("claim_ceiling"),
            "receipt_refs": _as_dict(row.get("evidence_refs")).get("receipt_refs", []),
        }
        for row in _as_list(payload.get("macro_import_route_body_floor"))
        if isinstance(row, dict)
    ]

    return drop_none({
        "schema": "microcosm_agent_entry_composition_compact_card_v0",
        "compact_projection_of": SCHEMA,
        "status": payload.get("status"),
        "selected_viewer": payload.get("selected_viewer"),
        "selected_viewer_entry": payload.get("selected_viewer_entry"),
        "selected_viewer_route": {
            "viewer": selected_viewer_route.get("viewer"),
            "route_kind": selected_viewer_route.get("route_kind"),
            "branch_label": selected_viewer_route.get("branch_label"),
            "first_safe_action": selected_viewer_route.get("first_safe_action"),
            "next_action": selected_viewer_route.get("next_action"),
            "stop_condition": selected_viewer_route.get("stop_condition"),
            "authority_boundary": selected_viewer_route.get("authority_boundary"),
            "evidence_refs": selected_viewer_route.get("evidence_refs", []),
        },
        "viewer_first_action_router": payload.get("viewer_first_action_router"),
        "first_screen_type_a_route": {
            "reader_id": first_screen_route.get("reader_id"),
            "route_command": first_screen_route.get("route_command"),
            "source_ref": first_screen_route.get("source_ref"),
            "anti_overread": first_screen_route.get("anti_overread"),
        },
        "task_route": {
            "requested_task": task_route.get("requested_task"),
            "selected_task_class": task_route.get("selected_task_class"),
            "selected_task_route_found": task_route.get("selected_task_route_found"),
            "task_class": task_route.get("task_class"),
            "primary_organ_id": task_route.get("primary_organ_id"),
            "primary_display_name": task_route.get("primary_display_name"),
            "first_command": task_route.get("first_command"),
            "drilldown_target": task_route.get("drilldown_target"),
            "evidence_ref": task_route.get("evidence_ref"),
            "receipt_ref": task_route.get("receipt_ref"),
            "authority_boundary": task_route.get("authority_boundary"),
            "allowed_authority": task_route.get("allowed_authority"),
            "organ_count": task_route.get("organ_count"),
        },
        "accepted_organ_glance": {
            "source_ref": accepted_glance.get("source_ref"),
            "drilldown": accepted_glance.get("drilldown"),
            "family_count": accepted_glance.get("family_count"),
            "organ_count": accepted_glance.get("organ_count"),
            "capsule_join_status_counts": accepted_glance.get(
                "capsule_join_status_counts", {}
            ),
            "authority_boundary": accepted_glance.get("authority_boundary"),
            "anti_claim": accepted_glance.get("anti_claim"),
        },
        "organ_discoverability_matrix_route": organ_route,
        "macro_import_route_body_floor": macro_floor,
        "read_run_order": payload.get("read_run_order", []),
        "authority_ceiling": {
            "release_authority": payload.get("release_authority"),
            "source_mutation_authority": payload.get("source_mutation_authority"),
            "provider_call_authority": payload.get("provider_call_authority"),
            "private_root_equivalence_authority": payload.get(
                "private_root_equivalence_authority"
            ),
        },
        "anti_claim": payload.get("anti_claim"),
        "omission_receipt": omission_receipt,
        "validation": {
            "status": validation.get("status"),
            "error_count": validation.get("error_count"),
            "errors": validation.get("errors", []),
        },
        "drilldowns": {
            "full_json": (
                "microcosm agent-entry-composition "
                f"--task {task_route.get('selected_task_class') or DEFAULT_TASK} "
                "--viewer <viewer>"
            ),
            "source_checkout_full_json": (
                "PYTHONPATH=src python3 -m microcosm_core "
                "agent-entry-composition --root . "
                f"--task {task_route.get('selected_task_class') or DEFAULT_TASK} "
                "--viewer <viewer>"
            ),
            "organ_matrix": ORGAN_DISCOVERABILITY_MATRIX_COMMAND,
        },
    })


def compile_paths(
    *,
    root: str | Path | None = None,
    task: str | None = None,
    viewer: str | None = None,
    out: str | Path | None = None,
    command: str = "agent-entry-composition",
) -> dict[str, Any]:
    payload = build_agent_entry_composition(
        root=root, task=task, viewer=viewer, command=command
    )
    if out is not None:
        out_path = Path(out)
        card_path = out_path / CARD_FILENAME
        receipt_path = out_path / RECEIPT_FILENAME
        payload["artifact_paths"] = {
            "out_dir": str(out_path),
            "card_path": str(card_path),
            "receipt_path": str(receipt_path),
        }
        write_json_atomic(card_path, payload)
        validation = _as_dict(payload.get("validation"))
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "status": payload["status"],
            "artifact_paths": payload["artifact_paths"],
            "card_path": str(card_path),
            "receipt_path": str(receipt_path),
            "source_refs": payload["source_refs"],
            "selected_task_class": payload["task_route"].get("task_class"),
            "selected_viewer": payload["selected_viewer"],
            "selected_viewer_route_kind": _as_dict(
                payload.get("selected_viewer_route")
            ).get("route_kind", "single_viewer_route"),
            "selected_viewer_status": _as_dict(
                payload.get("selected_viewer_route")
            ).get("viewer") or payload["selected_viewer"],
            "viewer_modes": [row.get("viewer") for row in payload["viewer_modes"]],
            "entry_experience_checks": [
                {
                    "viewer": row.get("viewer"),
                    "status": row.get("status"),
                    "failure_codes": row.get("failure_codes"),
                }
                for row in payload["entry_experience_checks"]
            ],
            "validation": {
                "status": validation.get("status"),
                "error_count": validation.get("error_count"),
                "errors": validation.get("errors", []),
            },
            "validation_errors": validation.get("errors", []),
            "accepted_organ_glance": {
                "source_ref": payload["accepted_organ_glance"].get("source_ref"),
                "family_count": payload["accepted_organ_glance"].get("family_count"),
                "organ_count": payload["accepted_organ_glance"].get("organ_count"),
                "capsule_join_status_counts": payload["accepted_organ_glance"].get(
                    "capsule_join_status_counts"
                ),
                "drilldown": payload["accepted_organ_glance"].get("drilldown"),
            },
            "macro_import_route_body_floor": [
                row.get("organ_id") for row in payload["macro_import_route_body_floor"]
            ],
            "authority_posture": payload["authority_posture"],
            "reentry_condition": payload["omission_receipt"]["reentry_condition"],
            "command": command,
        }
        write_json_atomic(receipt_path, receipt)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compose the Microcosm Type A cold-agent entry card."
    )
    parser.add_argument("--root", default=None)
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument("--viewer", choices=(ALL_VIEWERS, *VIEWER_IDS), default=ALL_VIEWERS)
    parser.add_argument("--out", default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    command = "python -m microcosm_core.projections.agent_entry_composition"
    payload = compile_paths(
        root=args.root,
        task=args.task,
        viewer=args.viewer,
        out=args.out,
        command=command,
    )
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" or not args.check else 1


if __name__ == "__main__":
    raise SystemExit(main())
