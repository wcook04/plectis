from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .resource_root import microcosm_root

MICROCOSM_ROOT = microcosm_root()
STANDARD_REF = Path("standards/std_microcosm_first_screen_composition_root.json")
READER_ROUTE_IDS = (
    "public_github_visitor",
    "safety_evals_engineer",
    "hiring_reviewer",
    "peer_developer",
)
REQUIRED_ROUTE_IDS = set(READER_ROUTE_IDS)
READER_LABELS = {
    "public_github_visitor": "GitHub visitor",
    "safety_evals_engineer": "Safety/evals",
    "hiring_reviewer": "Hiring",
    "peer_developer": "Peer developer",
}
DENIED_AUTHORITY_KEYS = (
    "release_authority",
    "source_mutation_authority",
    "private_data_equivalence_authority",
    "provider_call_authority",
    "score_based_progress_authority",
    "whole_system_correctness_authority",
)
STANDARD_SURFACE_ALIASES = {
    "concept_mechanism_entry_route": ("doctrine_effect_frame",),
    "reader_focus_mode": ("reader_route_menu", "text_projection"),
    "reader_route_ids": ("reader_routes",),
    "terminal_text_projection": ("text_projection",),
}
TEXT_CARD_MAX_LINES = 32
COMPACT_JSON_CARD_MAX_CHARS = 16000
TEXT_READER_CHOICES = ("all",) + READER_ROUTE_IDS
ORGAN_REGISTRY_REF = "core/organ_registry.json"
STANDARDS_REGISTRY_REF = "core/standards_registry.json"
EVIDENCE_CLASS_REGISTRY_REF = "core/organ_evidence_classes.json"
WORKINGNESS_MAP_REF = "receipts/runtime_shell/workingness_failure_map.json"
FIXTURE_MANIFESTS_REF = "core/fixture_manifests"
EVIDENCE_CLASS_DISPLAY_ORDER = (
    "verified_macro_body_import",
    "external_subprocess_witness",
    "semantic_validator",
    "algorithmic_projection",
    "fixture_schema_replay",
    "fixture_echo_smoke",
)
EVIDENCE_CLASS_LABELS = {
    "verified_macro_body_import": "macro body import",
    "external_subprocess_witness": "subprocess witness",
    "semantic_validator": "semantic validator",
    "algorithmic_projection": "algorithmic projection",
    "fixture_schema_replay": "fixture schema replay",
    "fixture_echo_smoke": "fixture smoke",
}
OBSERVATORY_LANDING_ENDPOINTS = {
    "html_landing": "/",
    "first_screen_card": "/project/first-screen",
    "compact_observatory_card": "/project/observatory-card",
    "full_observatory_model": "/project/observatory",
    "project_observe": "/project/observe",
}


def _observatory_serve_command(project_label: str) -> str:
    return f"microcosm serve {project_label} --host 127.0.0.1 --port 8765"


def _bounded_observatory_serve_command(project_label: str) -> str:
    return f"{_observatory_serve_command(project_label)} --max-requests 6"


def _load_standard(root: Path) -> dict[str, Any]:
    return json.loads((root / STANDARD_REF).read_text(encoding="utf-8"))


def _string_set(rows: Any) -> set[str]:
    if not isinstance(rows, list):
        return set()
    return {str(row) for row in rows if isinstance(row, str)}


def _reader_route_ids(rows: Any) -> set[str]:
    if not isinstance(rows, list):
        return set()
    return {
        str(row.get("reader_route_id"))
        for row in rows
        if isinstance(row, dict) and row.get("reader_route_id")
    }


def _ordered_reader_route_ids(route_ids: set[str]) -> list[str]:
    known_ids = [route_id for route_id in READER_ROUTE_IDS if route_id in route_ids]
    return known_ids + sorted(route_ids - REQUIRED_ROUTE_IDS)


def _surface_list(payload: dict[str, Any], surface_id: str, list_key: str) -> list[Any]:
    surface = payload.get(surface_id, {})
    if not isinstance(surface, dict):
        return []
    rows = surface.get(list_key, [])
    return rows if isinstance(rows, list) else []


def _standard_surface_present(
    surface_id: str,
    payload: dict[str, Any],
    validation_check_ids: set[str],
) -> bool:
    aliases = {surface_id, *STANDARD_SURFACE_ALIASES.get(surface_id, ())}
    return any(alias in payload for alias in aliases) or any(
        alias in validation_check_ids for alias in aliases
    )


def _standard_backed_first_screen_scan(
    payload: dict[str, Any],
    standard: dict[str, Any],
    validation_check_ids: set[str],
) -> dict[str, Any]:
    validator_contract = standard.get("validator_contract", {})
    receipt_contract = standard.get("receipt_contract", {})
    required_fields = _string_set(standard.get("required_fields", []))
    minimum_checks = (
        _string_set(validator_contract.get("minimum_checks", []))
        if isinstance(validator_contract, dict)
        else set()
    )
    receipt_must_record = (
        _string_set(receipt_contract.get("must_record", []))
        if isinstance(receipt_contract, dict)
        else set()
    )

    route_surfaces = {
        "reader_routes": payload.get("reader_routes", []),
        "reader_route_menu.routes": _surface_list(payload, "reader_route_menu", "routes"),
        "reader_landing_packets.packets": _surface_list(
            payload,
            "reader_landing_packets",
            "packets",
        ),
        "reader_exit_criteria.criteria": _surface_list(
            payload,
            "reader_exit_criteria",
            "criteria",
        ),
    }
    route_parity_rows = []
    for surface_id, rows in route_surfaces.items():
        actual_ids = _reader_route_ids(rows)
        route_parity_rows.append(
            {
                "surface": surface_id,
                "reader_route_ids": _ordered_reader_route_ids(actual_ids),
                "missing_reader_route_ids": [
                    route_id for route_id in READER_ROUTE_IDS if route_id not in actual_ids
                ],
                "extra_reader_route_ids": sorted(actual_ids - REQUIRED_ROUTE_IDS),
                "status": "pass" if actual_ids == REQUIRED_ROUTE_IDS else "blocked",
            }
        )

    project_label = str(payload.get("project_label", ""))
    menu_rows = _surface_list(payload, "reader_route_menu", "routes")
    command_rows = []
    for row in menu_rows:
        if not isinstance(row, dict):
            continue
        route_id = str(row.get("reader_route_id", ""))
        terminal_command = (
            f"microcosm hello --reader {route_id} {project_label}"
        )
        text_projection_command = (
            "microcosm first-screen --format text --reader "
            f"{route_id} {project_label}"
        )
        terminal_ok = row.get("terminal_command") == terminal_command
        text_projection_ok = row.get("text_projection_command") == text_projection_command
        command_rows.append(
            {
                "reader_route_id": route_id,
                "terminal_command_ok": terminal_ok,
                "text_projection_command_ok": text_projection_ok,
                "status": (
                    "pass"
                    if route_id in REQUIRED_ROUTE_IDS
                    and terminal_ok
                    and text_projection_ok
                    else "blocked"
                ),
            }
        )

    standard_authority_ceiling = standard.get("authority_ceiling", {})
    payload_authority_ceiling = payload.get("authority_ceiling", {})
    denied_authority_rows = [
        {
            "authority_key": key,
            "standard_value": standard_authority_ceiling.get(key)
            if isinstance(standard_authority_ceiling, dict)
            else None,
            "payload_value": payload_authority_ceiling.get(key)
            if isinstance(payload_authority_ceiling, dict)
            else None,
            "status": (
                "pass"
                if isinstance(standard_authority_ceiling, dict)
                and isinstance(payload_authority_ceiling, dict)
                and standard_authority_ceiling.get(key) is False
                and payload_authority_ceiling.get(key) is False
                else "blocked"
            ),
        }
        for key in DENIED_AUTHORITY_KEYS
    ]

    missing = {
        "required_fields": sorted(
            field for field in required_fields if field not in payload
        ),
        "validator_minimum_checks": sorted(minimum_checks - validation_check_ids),
        "receipt_must_record": sorted(
            item
            for item in receipt_must_record
            if not _standard_surface_present(item, payload, validation_check_ids)
        ),
    }
    public_private_boundary = payload.get("public_private_boundary", {})
    standard_public_private_boundary = standard.get("public_private_boundary", {})
    checks = {
        "standard_ref_matches": payload.get("source_standard_ref") == str(STANDARD_REF),
        "standard_kind_matches": payload.get("composition_root_id")
        == standard.get("kind_id"),
        "validator_id_matches": payload.get("validator_id")
        == (
            validator_contract.get("validator_id")
            if isinstance(validator_contract, dict)
            else None
        ),
        "required_fields_present": not missing["required_fields"],
        "validator_minimum_checks_executable": not missing[
            "validator_minimum_checks"
        ],
        "receipt_contract_surfaces_present": not missing["receipt_must_record"],
        "reader_route_parity": all(
            row["status"] == "pass" for row in route_parity_rows
        ),
        "copyable_reader_commands": (
            len(command_rows) == len(READER_ROUTE_IDS)
            and all(row["status"] == "pass" for row in command_rows)
        ),
        "authority_ceiling_mirrored": payload_authority_ceiling
        == standard_authority_ceiling,
        "denied_authority_flags_false": all(
            row["status"] == "pass" for row in denied_authority_rows
        ),
        "public_private_boundary_mirrored": public_private_boundary
        == {
            "allowed_public_inputs": standard_public_private_boundary.get(
                "allowed_public_inputs"
            )
            if isinstance(standard_public_private_boundary, dict)
            else None,
            "forbidden_public_inputs": standard_public_private_boundary.get(
                "forbidden_public_inputs"
            )
            if isinstance(standard_public_private_boundary, dict)
            else None,
        },
    }
    return {
        "schema_version": "microcosm_standard_backed_first_screen_scan_v1",
        "status": "pass" if all(checks.values()) else "blocked",
        "standard_id": standard.get("standard_id"),
        "standard_ref": str(STANDARD_REF),
        "validator_id": payload.get("validator_id"),
        "expected_reader_route_ids": list(READER_ROUTE_IDS),
        "checks": checks,
        "missing": missing,
        "route_parity": route_parity_rows,
        "reader_command_parity": command_rows,
        "denied_authority_flags": denied_authority_rows,
        "authority": "scanner_contract_only_not_release_or_reader_success_authority",
    }


def _load_public_json(root: Path, ref: str) -> dict[str, Any]:
    try:
        payload = json.loads((root / ref).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _collection_count(value: Any) -> int | None:
    if isinstance(value, (dict, list, tuple)):
        return len(value)
    return None


def _non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _first_count(*candidates: int | None) -> int | None:
    for candidate in candidates:
        if candidate is not None:
            return candidate
    return None


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _positive_count(row: Any) -> bool:
    return (
        isinstance(row, dict)
        and isinstance(row.get("count"), int)
        and not isinstance(row.get("count"), bool)
        and row["count"] > 0
    )


def _reader_routes(project_label: str) -> list[dict[str, Any]]:
    return [
        {
            "reader_route_id": "public_github_visitor",
            "first_question": "What should I run first from the public repo page?",
            "next_commands": [
                f"microcosm hello {project_label}",
                f"microcosm tour --card {project_label}",
            ],
            "evidence_focus": [
                "copyable first command and no-install fallback",
                "local behavior proof before receipt drilldown",
                "release, hosting, and private-data anti-claims",
            ],
            "branch_authority": "selects_next_inspection_surface_only",
        },
        {
            "reader_route_id": "safety_evals_engineer",
            "first_question": "Does the evidence discipline survive contact with scale?",
            "next_commands": [
                f"microcosm status --card {project_label}",
                "microcosm authority --card",
                "microcosm workingness --card",
            ],
            "evidence_focus": [
                "evidence classes and their authority ceilings",
                "body-copy boundaries and validator refs",
                "anti-claims, failure modes, and omission receipts",
            ],
            "branch_authority": "selects_next_inspection_surface_only",
        },
        {
            "reader_route_id": "hiring_reviewer",
            "first_question": "Is this real, inspectable, and built with the judgment I would interview for?",
            "next_commands": [
                "microcosm legibility-scorecard",
                f"microcosm tour --card {project_label}",
            ],
            "evidence_focus": [
                "local runnable behavior",
                "bounded public claims",
                "honest negatives and unsupported-claim boundaries",
            ],
            "branch_authority": "selects_next_inspection_surface_only",
        },
        {
            "reader_route_id": "peer_developer",
            "first_question": "Can I clone it, run it, and understand the first useful path in an hour?",
            "next_commands": [
                f"microcosm tour --card {project_label}",
                f"microcosm observe {project_label}",
            ],
            "evidence_focus": [
                "folder-local .microcosm state",
                "route/work/event/evidence chain",
                "standards and receipt drilldowns behind the compact card",
            ],
            "branch_authority": "selects_next_inspection_surface_only",
        },
    ]


def _reader_landing_packets(project_label: str) -> dict[str, Any]:
    return {
        "schema_version": "microcosm_reader_landing_packets_v1",
        "purpose": "turn_reader_routes_into_first_action_proof_success_packets",
        "shared_authority_rule": (
            "Reader packets choose inspection order only; every reader inherits the "
            "same authority ceiling, anti-claim, and omission receipt."
        ),
        "one_screen_rule": (
            "Each packet carries one first action, one proof surface, one success "
            "criterion, and one next drilldown."
        ),
        "packets": [
            {
                "reader_route_id": "public_github_visitor",
                "first_action": f"Run `microcosm hello {project_label}`.",
                "proof_surface": f"`microcosm tour --card {project_label}`",
                "success_criterion": (
                    "Can find the first runnable local command and name the "
                    "release, hosting, and private-data claims this repo refuses."
                ),
                "next_drilldown": "README.md#first-run",
                "authority": "inspection_order_only_not_publication_readiness",
            },
            {
                "reader_route_id": "safety_evals_engineer",
                "first_action": f"Run `microcosm status --card {project_label}`.",
                "proof_surface": (
                    "`microcosm authority --card` plus `microcosm workingness --card`"
                ),
                "success_criterion": (
                    "Can cite the evidence-class ceilings and the body-copy validator "
                    "boundary without inferring maturity or release readiness."
                ),
                "next_drilldown": EVIDENCE_CLASS_REGISTRY_REF,
                "authority": "inspection_order_only_not_safety_approval",
            },
            {
                "reader_route_id": "hiring_reviewer",
                "first_action": (
                    f"Run `microcosm hello {project_label}` before the longer tour."
                ),
                "proof_surface": f"`microcosm tour --card {project_label}`",
                "success_criterion": (
                    "Can distinguish runnable local behavior from the claims this "
                    "public card explicitly refuses to make."
                ),
                "next_drilldown": "microcosm legibility-scorecard",
                "authority": "inspection_order_only_not_candidate_assessment",
            },
            {
                "reader_route_id": "peer_developer",
                "first_action": f"Run `microcosm tour --card {project_label}`.",
                "proof_surface": f"`microcosm observe {project_label}`",
                "success_criterion": (
                    "Can inspect folder-local .microcosm state and follow the "
                    "route/work/event/evidence chain without provider calls."
                ),
                "next_drilldown": "paper_modules/cold_reader_route_map.md",
                "authority": "inspection_order_only_not_integration_guarantee",
            },
        ],
    }


def _reader_route_menu(project_label: str) -> dict[str, Any]:
    return {
        "schema_version": "microcosm_reader_route_menu_v1",
        "purpose": (
            "make_reader_typed_first_screens_copyable_without_separate_entry_"
            "artifacts"
        ),
        "menu_rule": (
            "Show the shared map and behavior proof first; focused reader commands "
            "only change the terminal projection, not the authority ceiling."
        ),
        "default_command": f"microcosm hello {project_label}",
        "shared_behavior_command": f"microcosm tour --card {project_label}",
        "machine_card_command": f"microcosm first-screen {project_label}",
        "routes": [
            {
                "reader_route_id": "public_github_visitor",
                "label": READER_LABELS["public_github_visitor"],
                "terminal_command": (
                    f"microcosm hello --reader public_github_visitor {project_label}"
                ),
                "text_projection_command": (
                    "microcosm first-screen --format text "
                    f"--reader public_github_visitor {project_label}"
                ),
                "first_action": f"Run `microcosm hello {project_label}`.",
                "proof_surface": f"`microcosm tour --card {project_label}`",
                "exit_check": "find the first runnable local command and anti-claims",
                "not_a_claim": "publication_or_reader_success_ready",
                "authority": "focused_projection_only_not_publication_readiness",
            },
            {
                "reader_route_id": "safety_evals_engineer",
                "label": READER_LABELS["safety_evals_engineer"],
                "terminal_command": (
                    f"microcosm hello --reader safety_evals_engineer {project_label}"
                ),
                "text_projection_command": (
                    "microcosm first-screen --format text "
                    f"--reader safety_evals_engineer {project_label}"
                ),
                "first_action": f"Run `microcosm status --card {project_label}`.",
                "proof_surface": (
                    "`microcosm authority --card` plus `microcosm workingness --card`"
                ),
                "exit_check": "cite evidence-class ceilings and body-copy boundaries",
                "not_a_claim": "safety_evaluation_complete",
                "authority": "focused_projection_only_not_safety_approval",
            },
            {
                "reader_route_id": "hiring_reviewer",
                "label": READER_LABELS["hiring_reviewer"],
                "terminal_command": (
                    f"microcosm hello --reader hiring_reviewer {project_label}"
                ),
                "text_projection_command": (
                    "microcosm first-screen --format text "
                    f"--reader hiring_reviewer {project_label}"
                ),
                "first_action": (
                    f"Run `microcosm hello {project_label}` before the longer tour."
                ),
                "proof_surface": f"`microcosm tour --card {project_label}`",
                "exit_check": "separate runnable behavior from refused claims",
                "not_a_claim": "candidate_assessed_or_interview_ready",
                "authority": "focused_projection_only_not_candidate_assessment",
            },
            {
                "reader_route_id": "peer_developer",
                "label": READER_LABELS["peer_developer"],
                "terminal_command": (
                    f"microcosm hello --reader peer_developer {project_label}"
                ),
                "text_projection_command": (
                    "microcosm first-screen --format text "
                    f"--reader peer_developer {project_label}"
                ),
                "first_action": f"Run `microcosm tour --card {project_label}`.",
                "proof_surface": f"`microcosm observe {project_label}`",
                "exit_check": "follow the route/work/event/evidence chain locally",
                "not_a_claim": "integration_complete",
                "authority": "focused_projection_only_not_integration_guarantee",
            },
        ],
        "safe_to_show": {
            "uses_existing_reader_packets": True,
            "creates_new_entry_artifact": False,
            "creates_reader_specific_claim_ceiling": False,
            "exports_private_paths": False,
            "exports_provider_payloads": False,
            "claims_release_or_hosting": False,
            "claims_reader_success": False,
        },
        "authority": "reader_route_menu_not_new_entry_artifact_or_reader_success_authority",
    }


def _behavior_proof_packet(project_label: str) -> dict[str, Any]:
    shared_first_command = f"microcosm tour --card {project_label}"
    return {
        "schema_version": "microcosm_behavior_proof_packet_v1",
        "purpose": "turn_shared_first_run_into_inspectable_success_conditions",
        "command": shared_first_command,
        "writes_state": True,
        "state_dir": ".microcosm",
        "proof_fields": [
            {
                "field": "front_door_status.status",
                "success_read": "pass",
                "reader_rule": "first_screen_surfaces_pass_not_release_readiness",
            },
            {
                "field": "selected_route_id",
                "success_read": "non_empty_route_id",
                "reader_rule": "selected_local_route_not_universal_project_truth",
            },
            {
                "field": "state_inspection",
                "success_read": "catalog_routes_work_events_evidence_refs_present",
                "reader_rule": "inspectable_local_state_not_private_root_equivalence",
            },
            {
                "field": "source_files_mutated",
                "success_read": False,
                "reader_rule": "project_source_remains_unchanged_by_first_run",
            },
        ],
        "failure_reading": (
            "A non-pass field names the first blocked or warning surface to inspect; "
            "it is not a product, release, proof, or safety-evaluation verdict."
        ),
        "authority": "local_behavior_receipt_not_release_or_proof_authority",
    }


def _first_run_ladder(project_label: str) -> dict[str, Any]:
    human_first_command = f"microcosm hello {project_label}"
    shared_first_command = f"microcosm tour --card {project_label}"
    status_card_command = f"microcosm status --card {project_label}"
    return {
        "schema_version": "microcosm_first_run_ladder_v1",
        "purpose": "make_first_screen_run_order_copyable_without_long_quickstart",
        "one_screen_rule": (
            "The first screen gives a copyable run order before the long command "
            "inventory: map, behavior proof, state confirmation, then reader branch."
        ),
        "steps": [
            {
                "step_id": "map",
                "command": human_first_command,
                "writes_microcosm_state": False,
                "expected_surface": "terminal_text_projection",
                "success_read": "one_screen_map_visible",
                "authority": "projection_only_not_behavior_proof",
            },
            {
                "step_id": "behavior_proof",
                "command": shared_first_command,
                "writes_microcosm_state": True,
                "expected_surface": ".microcosm state plus compact route card",
                "success_read": (
                    "front_door_status.status=pass and selected_route_id present"
                ),
                "authority": "local_behavior_receipt_not_release_or_proof_authority",
            },
            {
                "step_id": "status_confirmation",
                "command": status_card_command,
                "writes_microcosm_state": False,
                "expected_surface": "front door state, route proof, and gap preview",
                "success_read": "project_state visible and source_files_mutated=false",
                "authority": "status_read_model_not_whole_system_health",
            },
            {
                "step_id": "reader_branch",
                "command": "choose reader route from reader_route_menu",
                "writes_microcosm_state": False,
                "expected_surface": "reader-specific command, first action, and proof surface",
                "success_read": "next inspection surface selected by reader job",
                "authority": "inspection_order_only_not_reader_specific_claim_ceiling",
            },
        ],
        "authority": "copyable_run_order_not_quickstart_inventory_or_release_authority",
    }


def _first_viewport_manifest(project_label: str) -> dict[str, Any]:
    human_first_command = f"microcosm hello {project_label}"
    shared_first_command = f"microcosm tour --card {project_label}"
    bounded_serve_command = _bounded_observatory_serve_command(project_label)
    must_preserve = [
        "authority_ceiling",
        "anti_claim",
        "omission_receipt",
        "discipline_comparison_strip",
    ]
    must_not_claim = [
        "release_or_hosting_authority",
        "provider_call_authority",
        "private_root_equivalence",
        "whole_system_correctness",
        "reader_success",
    ]
    return {
        "schema_version": "microcosm_first_viewport_manifest_v1",
        "purpose": (
            "make_single_screen_cold_entry_composition_explicit_for_cli_readme_"
            "browser_json_and_video"
        ),
        "composition_rule": (
            "Every first-contact projection should render these slots in order before "
            "the long command inventory or full observatory lens list."
        ),
        "slots": [
            {
                "slot_id": "identity",
                "viewport_copy": (
                    "Microcosm is a local evidence router with explicit claim ceilings."
                ),
                "source_packet": "text_projection",
                "first_visible_surface": human_first_command,
                "proof_surface": "authority_ceiling",
                "must_preserve": must_preserve,
                "must_not_claim": must_not_claim,
            },
            {
                "slot_id": "first_run",
                "viewport_copy": "Open the map, then run the behavior-proof card.",
                "source_packet": "first_run_ladder",
                "first_visible_surface": shared_first_command,
                "proof_surface": "behavior_proof_packet",
                "must_preserve": must_preserve,
                "must_not_claim": must_not_claim,
            },
            {
                "slot_id": "proof_chain",
                "viewport_copy": (
                    "The first run writes inspectable .microcosm state, not source "
                    "mutations."
                ),
                "source_packet": "local_state_receipt_trail",
                "first_visible_surface": ".microcosm/",
                "proof_surface": "first_contact_surface_refs",
                "must_preserve": must_preserve,
                "must_not_claim": must_not_claim,
            },
            {
                "slot_id": "evidence_context",
                "viewport_copy": (
                    "Counts are evidence-class accounting, not maturity or readiness scores."
                ),
                "source_packet": "evidence_count_frame",
                "first_visible_surface": EVIDENCE_CLASS_REGISTRY_REF,
                "proof_surface": "evidence_class_legend",
                "must_preserve": must_preserve,
                "must_not_claim": must_not_claim,
            },
            {
                "slot_id": "reader_branch",
                "viewport_copy": (
                    "Reader routes branch only after the shared local behavior proof."
                ),
                "source_packet": "reader_route_menu",
                "first_visible_surface": "focused reader commands",
                "proof_surface": "reader_exit_criteria",
                "must_preserve": must_preserve,
                "must_not_claim": must_not_claim,
            },
            {
                "slot_id": "authority_boundary",
                "viewport_copy": (
                    "Comparison strip and tripwires make rigor visible without claim inflation."
                ),
                "source_packet": "discipline_comparison_strip",
                "first_visible_surface": "discipline_comparison_strip",
                "proof_surface": "overclaim_tripwire_matrix",
                "must_preserve": must_preserve,
                "must_not_claim": must_not_claim,
            },
        ],
        "problem_shape_slot_map": [
            {
                "problem_shape_id": "first_thing_best_thing_gap",
                "slot_id": "first_run",
            },
            {
                "problem_shape_id": "audience_is_not_one_person",
                "slot_id": "reader_branch",
            },
            {
                "problem_shape_id": "honest_numbers_without_context",
                "slot_id": "evidence_context",
            },
            {
                "problem_shape_id": "discipline_invisible_without_comparison",
                "slot_id": "authority_boundary",
            },
            {
                "problem_shape_id": "size_paradox",
                "slot_id": "identity",
            },
            {
                "problem_shape_id": "runnable_vs_structural_split",
                "slot_id": "proof_chain",
            },
            {
                "problem_shape_id": "doctrine_reads_as_ceremony",
                "slot_id": "authority_boundary",
            },
            {
                "problem_shape_id": "frontend_surface_not_seductive",
                "slot_id": "identity",
            },
            {
                "problem_shape_id": "card_discipline_not_default",
                "slot_id": "first_run",
            },
        ],
        "consumer_surfaces": {
            "terminal": human_first_command,
            "readme": "README.md::Choose Your First Screen",
            "browser": f"{bounded_serve_command} -> /",
            "json": f"microcosm first-screen {project_label}",
            "video": "video_storyboard_packet",
        },
        "safe_to_show": {
            "uses_existing_first_screen_packets": True,
            "creates_new_entry_artifact": False,
            "exports_private_paths": False,
            "exports_provider_payloads": False,
            "claims_release_or_hosting": False,
            "claims_reader_success": False,
        },
        "authority": "viewport_manifest_not_new_claim_or_renderer_authority",
    }


def _local_state_receipt_trail(project_label: str) -> dict[str, Any]:
    shared_first_command = f"microcosm tour --card {project_label}"
    return {
        "schema_version": "microcosm_local_state_receipt_trail_v1",
        "purpose": "show_what_the_first_run_writes_without_expanding_raw_state",
        "producer_command": shared_first_command,
        "state_dir": ".microcosm",
        "trail": [
            {
                "surface_id": "catalog",
                "state_ref": ".microcosm/catalog.json",
                "reader_read": "project files became catalog rows",
                "not_authority_for": "source_mutation_or_project_quality",
            },
            {
                "surface_id": "routes",
                "state_ref": ".microcosm/routes.json",
                "reader_read": "one selected route is inspectable",
                "not_authority_for": "universal_project_truth_or_release_readiness",
            },
            {
                "surface_id": "work_events",
                "state_ref": ".microcosm/events.jsonl",
                "reader_read": "work transaction and event receipt chain exists",
                "not_authority_for": "private_root_equivalence_or_provider_action",
            },
            {
                "surface_id": "evidence_index",
                "state_ref": ".microcosm/evidence/index.json",
                "reader_read": "evidence refs can be opened after the card",
                "not_authority_for": "proof_correctness_or_benchmark_score",
            },
            {
                "surface_id": "graph",
                "state_ref": ".microcosm/graph.json",
                "reader_read": "route, work, event, and evidence refs join",
                "not_authority_for": "whole_system_correctness_or_maturity_score",
            },
        ],
        "reader_rule": (
            "State refs are local behavior evidence from the shared first run; "
            "they are not source mutation, release readiness, or private-root "
            "equivalence claims."
        ),
        "authority": "local_state_receipt_trail_not_private_root_equivalence",
    }


def _first_contact_surface_refs(project_label: str) -> dict[str, Any]:
    shared_first_command = f"microcosm tour --card {project_label}"
    status_card_command = f"microcosm status --card {project_label}"
    observe_command = f"microcosm observe {project_label}"
    proof_lab_command = "microcosm proof-lab --out /tmp/microcosm-proof-lab"
    return {
        "schema_version": "microcosm_first_contact_surface_refs_v1",
        "purpose": (
            "compress_route_work_event_evidence_graph_observatory_and_proof_"
            "handles_for_cold_readers"
        ),
        "producer_command": shared_first_command,
        "reader_rule": (
            "Use these refs as the first-screen behavior map after the shared "
            "run; open full receipts only after the compact route/work/evidence "
            "graph and observatory/proof handles are visible."
        ),
        "required_surface_ids": [
            "route",
            "work",
            "events",
            "evidence",
            "graph",
            "observatory",
            "proof_lab",
            "status",
        ],
        "surfaces": {
            "route": {
                "command": shared_first_command,
                "state_ref": ".microcosm/routes.json",
                "selected_route_ref": ".microcosm/routes.json::<selected_route_id>",
                "status_ref": "front_door_status.surface_statuses.state_inspection",
            },
            "work": {
                "command": observe_command,
                "state_ref": ".microcosm/work_items.json",
                "selected_work_ref": ".microcosm/work_items.json::<selected_work_id>",
                "event_ref": ".microcosm/events.jsonl",
            },
            "events": {
                "command": observe_command,
                "state_ref": ".microcosm/events.jsonl",
                "status_ref": "microcosm observe <project>::spans",
            },
            "evidence": {
                "command": observe_command,
                "state_ref": ".microcosm/evidence/",
                "index_ref": ".microcosm/evidence/index.json",
                "body_text_exported": False,
            },
            "graph": {
                "command": observe_command,
                "state_ref": ".microcosm/graph.json",
                "status_ref": "microcosm observe <project>::causal_chain.graph",
            },
            "observatory": {
                "command": _observatory_serve_command(project_label),
                "bounded_validation_command": _bounded_observatory_serve_command(
                    project_label
                ),
                "bounded_validation_request_count": 6,
                "compact_endpoint": OBSERVATORY_LANDING_ENDPOINTS[
                    "compact_observatory_card"
                ],
                "expanded_endpoint": OBSERVATORY_LANDING_ENDPOINTS[
                    "full_observatory_model"
                ],
            },
            "proof_lab": {
                "command": proof_lab_command,
                "endpoint": "/proof-lab",
                "route_id": "formal_prover_context_strategy_gate",
                "receipt_ref": (
                    "receipts/first_wave/verifier_lab_kernel/"
                    "exported_verifier_lab_kernel_bundle_validation_result.json"
                ),
            },
            "status": {
                "command": status_card_command,
                "endpoint": "/project/status",
                "body_import_floor_ref": (
                    "microcosm status --card <project>::front_door."
                    "source_open_body_import_floor"
                ),
                "workingness_command": "microcosm workingness --card",
            },
        },
        "safe_to_show": {
            "project_local_state_refs_visible": True,
            "receipt_refs_visible": True,
            "body_text_exported": False,
            "source_files_mutated": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
            "proof_correctness_claim": False,
        },
        "authority": (
            "first_contact_surface_map_only_not_source_release_provider_"
            "mutation_or_proof_authority"
        ),
    }


def _overclaim_tripwire_matrix(project_label: str) -> dict[str, Any]:
    shared_first_command = f"microcosm tour --card {project_label}"
    return {
        "schema_version": "microcosm_overclaim_tripwire_matrix_v1",
        "purpose": "translate_common_cold_reader_overclaims_into_valid_bounded_reads",
        "shared_first_command": shared_first_command,
        "rows": [
            {
                "tripwire_id": "release_ready",
                "overclaim": "Microcosm is release-ready.",
                "valid_read": (
                    "Microcosm exposes a local first-run evidence card and "
                    "authority ceiling."
                ),
                "check_surface": f"microcosm status --card {project_label}",
                "reader_rule": "release_readiness_not_claimed",
            },
            {
                "tripwire_id": "organ_count_whole_system",
                "overclaim": "Forty-seven organs means every capability works end-to-end.",
                "valid_read": (
                    "Accepted public runtime organs are inventory handles with "
                    "evidence classes and failure envelopes."
                ),
                "check_surface": "microcosm workingness",
                "reader_rule": "organ_inventory_not_whole_system_correctness",
            },
            {
                "tripwire_id": "low_body_import_count_fake",
                "overclaim": "A low verified body-import count means the system is fake.",
                "valid_read": (
                    "Evidence-class counts are claim-boundary accounting; low "
                    "counts narrow claims instead of being hidden."
                ),
                "check_surface": EVIDENCE_CLASS_REGISTRY_REF,
                "reader_rule": "low_count_not_failure_by_itself",
            },
            {
                "tripwire_id": "local_state_private_root_equivalence",
                "overclaim": ".microcosm state proves private-root equivalence.",
                "valid_read": (
                    ".microcosm state proves folder-local behavior refs from the "
                    "shared first run."
                ),
                "check_surface": ".microcosm/",
                "reader_rule": "local_state_not_private_root_equivalence",
            },
            {
                "tripwire_id": "observatory_hosted_release",
                "overclaim": "The observatory is a hosted or public release surface.",
                "valid_read": (
                    "The observatory is a localhost read-model over the same "
                    "first-screen card."
                ),
                "check_surface": OBSERVATORY_LANDING_ENDPOINTS["first_screen_card"],
                "reader_rule": "localhost_read_model_not_hosting_authority",
            },
        ],
        "authority": "overclaim_tripwire_not_marketing_or_release_authority",
    }


def _reader_exit_criteria(project_label: str) -> dict[str, Any]:
    return {
        "schema_version": "microcosm_reader_exit_criteria_v1",
        "purpose": "tell_cold_readers_when_the_first_screen_has_done_its_job",
        "shared_first_command": f"microcosm tour --card {project_label}",
        "shared_stop_rule": (
            "The first screen is complete when the reader can choose the next "
            "drilldown without needing the long command inventory."
        ),
        "criteria": [
            {
                "reader_route_id": "public_github_visitor",
                "exit_when": (
                    "Can run the first command and point to the anti-claims "
                    "before opening deeper receipts."
                ),
                "next_if_not_met": f"microcosm hello {project_label}",
                "not_a_claim": "publication_or_reader_success_ready",
            },
            {
                "reader_route_id": "safety_evals_engineer",
                "exit_when": (
                    "Can name evidence-class ceilings, authority ceiling, and "
                    "first missing or failing surface without inferring readiness."
                ),
                "next_if_not_met": f"microcosm status --card {project_label}",
                "not_a_claim": "safety_evaluation_complete",
            },
            {
                "reader_route_id": "hiring_reviewer",
                "exit_when": (
                    "Can distinguish runnable local behavior from the claims this "
                    "card refuses to make."
                ),
                "next_if_not_met": "microcosm legibility-scorecard",
                "not_a_claim": "candidate_assessed_or_interview_ready",
            },
            {
                "reader_route_id": "peer_developer",
                "exit_when": (
                    "Can find .microcosm state refs and follow the "
                    "route/work/event/evidence chain."
                ),
                "next_if_not_met": f"microcosm observe {project_label}",
                "not_a_claim": "integration_complete",
            },
        ],
        "authority": "exit_criteria_not_reader_success_or_release_authority",
    }


def _video_storyboard_packet(project_label: str) -> dict[str, Any]:
    shared_first_command = f"microcosm tour --card {project_label}"
    status_card_command = f"microcosm status --card {project_label}"
    observatory_command = _bounded_observatory_serve_command(project_label)
    return {
        "schema_version": "microcosm_video_storyboard_packet_v1",
        "purpose": "make_a_sixty_second_cold_entry_artifact_without_new_claims",
        "artifact_rule": (
            "A video, screenshot board, or browser reveal may project these beats, "
            "but every beat must point back to the same package-backed first-screen "
            "commands and authority ceiling."
        ),
        "allowed_artifact_forms": [
            "terminal_capture",
            "browser_walkthrough",
            "static_reveal_board",
            "short_video",
        ],
        "source_projection": (
            "microcosm_core.first_screen_composition.first_screen_composition_card"
        ),
        "first_run_command": shared_first_command,
        "bounded_observatory_command": observatory_command,
        "beats": [
            {
                "beat_id": "open_map",
                "timebox_seconds": 8,
                "visible_surface": f"microcosm hello {project_label}",
                "reader_takeaway": "one screen names the local evidence router",
                "proof_ref": "terminal_text_projection",
            },
            {
                "beat_id": "prove_local_behavior",
                "timebox_seconds": 12,
                "visible_surface": shared_first_command,
                "reader_takeaway": ".microcosm state is written without source mutation",
                "proof_ref": "front_door_status.status + source_files_mutated=false",
            },
            {
                "beat_id": "show_route_chain",
                "timebox_seconds": 10,
                "visible_surface": f"microcosm observe {project_label}",
                "reader_takeaway": "route, work, event, evidence, and graph refs join",
                "proof_ref": ".microcosm/events.jsonl + .microcosm/graph.json",
            },
            {
                "beat_id": "frame_evidence_counts",
                "timebox_seconds": 10,
                "visible_surface": status_card_command,
                "reader_takeaway": "counts are claim-boundary accounting, not maturity scores",
                "proof_ref": EVIDENCE_CLASS_REGISTRY_REF,
            },
            {
                "beat_id": "open_authority_boundary",
                "timebox_seconds": 10,
                "visible_surface": (
                    "microcosm authority --card, then microcosm workingness --card"
                ),
                "reader_takeaway": "authority ceilings and failure envelopes stay visible",
                "proof_ref": WORKINGNESS_MAP_REF,
            },
            {
                "beat_id": "choose_reader_branch",
                "timebox_seconds": 10,
                "visible_surface": "reader_landing_packets",
                "reader_takeaway": "safety, hiring, and developer readers get different next surfaces",
                "proof_ref": "reader_exit_criteria",
            },
        ],
        "safe_to_show": {
            "uses_public_first_screen_card": True,
            "uses_localhost_read_model": True,
            "exports_private_paths": False,
            "exports_provider_payloads": False,
            "uses_live_operator_or_browser_session": False,
            "claims_release_or_hosting": False,
            "claims_reader_success": False,
        },
        "anti_claim": (
            "The storyboard compresses how to look at Microcosm; it is not a "
            "release artifact, benchmark, hiring verdict, safety evaluation, "
            "hosted demo, or private-root equivalence claim."
        ),
        "authority": "presentation_plan_over_existing_first_screen_contract_only",
    }


def _artifact_fit_matrix(project_label: str) -> dict[str, Any]:
    human_first_command = f"microcosm hello {project_label}"
    shared_first_command = f"microcosm tour --card {project_label}"
    first_screen_json_command = f"microcosm first-screen {project_label}"
    bounded_observatory_command = _bounded_observatory_serve_command(project_label)
    shared_must_preserve = [
        "human_first_command",
        "shared_first_command",
        "authority_ceiling",
        "anti_claim",
        "omission_receipt",
        "discipline_comparison_strip",
    ]
    shared_must_not_claim = [
        "release_or_hosting_authority",
        "provider_call_authority",
        "private_root_equivalence",
        "whole_system_correctness",
        "reader_success",
    ]
    return {
        "schema_version": "microcosm_first_screen_artifact_fit_matrix_v1",
        "purpose": "keep_all_cold_entry_forms_bound_to_one_source_card",
        "source_of_truth": (
            "microcosm_core.first_screen_composition.first_screen_composition_card"
        ),
        "matrix_rule": (
            "Terminal text, README order, browser landing, machine JSON, and short-video "
            "forms are projections over one first-screen contract, not independent "
            "cold-entry artifacts."
        ),
        "rows": [
            {
                "surface_id": "terminal_text_projection",
                "artifact_form": "terminal_text",
                "consumer_surface": human_first_command,
                "source_projection": (
                    "microcosm_core.first_screen_composition.first_screen_text_card"
                ),
                "first_job": "show_the_map_before_state_writing",
                "must_preserve": [
                    *shared_must_preserve,
                    "reader_routes",
                    "reader_route_menu",
                    "reader_exit_criteria",
                ],
                "must_not_claim": shared_must_not_claim,
            },
            {
                "surface_id": "local_behavior_card",
                "artifact_form": "terminal_state_writer",
                "consumer_surface": shared_first_command,
                "source_projection": "microcosm tour --card output",
                "first_job": "write_local_state_and_expose_behavior_proof",
                "must_preserve": [
                    *shared_must_preserve,
                    "behavior_proof_packet",
                    "local_state_receipt_trail",
                ],
                "must_not_claim": shared_must_not_claim,
            },
            {
                "surface_id": "machine_json_card",
                "artifact_form": "public_json",
                "consumer_surface": first_screen_json_command,
                "source_projection": (
                    "microcosm_core.first_screen_composition.first_screen_composition_card"
                ),
                "first_job": "give_consumers_the_complete_public_contract",
                "must_preserve": [
                    *shared_must_preserve,
                    "validation.checks",
                    "public_private_boundary",
                ],
                "must_not_claim": shared_must_not_claim,
            },
            {
                "surface_id": "readme_first_screen",
                "artifact_form": "markdown_entry_order",
                "consumer_surface": "README.md::Choose Your First Screen",
                "source_projection": "readme_entry_contract",
                "first_job": "place_the_card_before_the_long_inventory",
                "must_preserve": [
                    *shared_must_preserve,
                    "readme_entry_contract.required_markdown_order",
                    "reader_route_menu",
                    "reader_landing_packets",
                ],
                "must_not_claim": shared_must_not_claim,
            },
            {
                "surface_id": "browser_landing",
                "artifact_form": "localhost_html_read_model",
                "consumer_surface": bounded_observatory_command,
                "source_projection": "observatory_landing_frame",
                "first_job": "reuse_the_card_as_the_first_viewport",
                "must_preserve": [
                    *shared_must_preserve,
                    "observatory_landing_frame.required_visible_handles",
                    "first_contact_surface_refs",
                ],
                "must_not_claim": shared_must_not_claim,
            },
            {
                "surface_id": "short_video_storyboard",
                "artifact_form": "presentation_plan",
                "consumer_surface": "video_storyboard_packet",
                "source_projection": "video_storyboard_packet",
                "first_job": "compress_sixty_seconds_without_new_claims",
                "must_preserve": [
                    *shared_must_preserve,
                    "video_storyboard_packet.beats",
                    "video_storyboard_packet.safe_to_show",
                ],
                "must_not_claim": shared_must_not_claim,
            },
        ],
        "safe_to_show": {
            "binds_to_single_source_contract": True,
            "allows_multiple_projection_forms": True,
            "exports_private_paths": False,
            "exports_provider_payloads": False,
            "creates_new_release_artifact": False,
            "creates_reader_specific_claim_ceiling": False,
        },
        "authority": "projection_fit_matrix_not_new_artifact_authority",
    }


def _cold_entry_problem_map(project_label: str) -> dict[str, Any]:
    human_first_command = f"microcosm hello {project_label}"
    shared_first_command = f"microcosm tour --card {project_label}"
    return {
        "schema_version": "microcosm_cold_entry_problem_map_v1",
        "purpose": "bind_cold_entry_problem_shapes_to_existing_first_screen_packets",
        "map_rule": (
            "Each cold-entry problem shape must resolve to an existing first-screen "
            "packet or drilldown. The map explains why the packet exists; it does "
            "not create a second entry artifact."
        ),
        "rows": [
            {
                "problem_shape_id": "first_thing_best_thing_gap",
                "reader_risk": "long_inventory_before_best_evidence",
                "compression_answer": "open_the_map_then_run_the_shared_behavior_card",
                "primary_packet": "first_run_ladder",
                "first_surface": human_first_command,
                "proof_surface": shared_first_command,
                "not_claim": "quickstart_inventory_complete",
            },
            {
                "problem_shape_id": "audience_is_not_one_person",
                "reader_risk": "one_generic_pitch_overloads_three_jobs",
                "compression_answer": "shared_behavior_first_then_reader_typed_branch",
                "primary_packet": "reader_route_menu",
                "first_surface": "focused reader commands",
                "proof_surface": "reader_exit_criteria",
                "not_claim": "reader_success_or_reader_specific_authority",
            },
            {
                "problem_shape_id": "honest_numbers_without_context",
                "reader_risk": "low_counts_read_as_failure_or_hidden_maturity_score",
                "compression_answer": "make_counts_claim_boundary_accounting",
                "primary_packet": "evidence_count_frame",
                "first_surface": EVIDENCE_CLASS_REGISTRY_REF,
                "proof_surface": "evidence_class_legend",
                "not_claim": "maturity_readiness_or_progress_score",
            },
            {
                "problem_shape_id": "discipline_invisible_without_comparison",
                "reader_risk": "rigor_reads_as_ceremony_or_obviousness",
                "compression_answer": "show_side_by_side_failures_and_microcosm_boundaries",
                "primary_packet": "discipline_comparison_strip",
                "first_surface": "discipline_comparison_strip",
                "proof_surface": "overclaim_tripwire_matrix",
                "not_claim": "external_benchmark_equivalence",
            },
            {
                "problem_shape_id": "size_paradox",
                "reader_risk": "large_public_substrate_reads_as_diffuse",
                "compression_answer": "make_the_first_command_the_composition_root",
                "primary_packet": "scale_frame",
                "first_surface": shared_first_command,
                "proof_surface": WORKINGNESS_MAP_REF,
                "not_claim": "whole_system_correctness",
            },
            {
                "problem_shape_id": "runnable_vs_structural_split",
                "reader_risk": "local_demo_seen_apart_from_public_scale",
                "compression_answer": "join_folder_local_state_to_structural_drilldowns",
                "primary_packet": "runnable_structural_join",
                "first_surface": ".microcosm/",
                "proof_surface": "first_contact_surface_refs",
                "not_claim": "private_root_equivalence",
            },
            {
                "problem_shape_id": "doctrine_reads_as_ceremony",
                "reader_risk": "governance_words_look_like_status_signaling",
                "compression_answer": "translate_doctrine_handles_into_mistakes_prevented",
                "primary_packet": "doctrine_effect_frame",
                "first_surface": "authority_ceiling",
                "proof_surface": "omission_receipt",
                "not_claim": "doctrine_as_credential",
            },
            {
                "problem_shape_id": "frontend_surface_not_seductive",
                "reader_risk": "browser_or_video_viewers_miss_the_real_entry_contract",
                "compression_answer": "make_browser_and_video_forms_project_the_same_card",
                "primary_packet": "artifact_fit_matrix",
                "first_surface": "observatory_landing_frame",
                "proof_surface": "video_storyboard_packet",
                "not_claim": "hosted_release_or_standalone_video_authority",
            },
            {
                "problem_shape_id": "card_discipline_not_default",
                "reader_risk": "compact_card_exists_but_is_not_the_first_loaded_surface",
                "compression_answer": "make_hello_and_readme_order_point_at_the_card_first",
                "primary_packet": "readme_entry_contract",
                "first_surface": "text_projection",
                "proof_surface": "entry_surface_contract",
                "not_claim": "full_surface_removed_or_depth_weakened",
            },
        ],
        "safe_to_show": {
            "uses_existing_first_screen_packets": True,
            "creates_new_entry_artifact": False,
            "exports_private_paths": False,
            "exports_provider_payloads": False,
            "claims_release_or_hosting": False,
            "claims_reader_success": False,
        },
        "authority": "problem_shape_map_not_strategy_or_release_authority",
    }


def _evidence_count_frame() -> dict[str, Any]:
    return {
        "interpretation": "accounting_not_maturity_score",
        "legend_ref": EVIDENCE_CLASS_REGISTRY_REF,
        "why_counts_are_visible": (
            "Microcosm shows evidence-class counts so the reader can see what has crossed a declared "
            "boundary, not so the reader infers readiness, completeness, or product progress."
        ),
        "if_a_count_is_low": (
            "Read it as a precise accounting statement for that evidence class. It is not an implicit "
            "negative claim about the rest of the substrate."
        ),
        "forbidden_reads": [
            "maturity_score",
            "readiness_score",
            "completeness_score",
            "product_progress_score",
        ],
        "authoritative_count_sources": [
            {
                "surface": f"{FIXTURE_MANIFESTS_REF}/*.fixture_manifest.json",
                "role": (
                    "implemented-organ source-open material count input before "
                    "stale workingness receipt fallback"
                ),
            },
            {
                "surface": "microcosm workingness",
                "role": "runtime evidence summary",
            },
            {
                "surface": "core/standards_registry.json",
                "role": "public standards inventory, not readiness scoring",
            },
            {
                "surface": "receipts/first_wave/standards_registry_validation.json",
                "role": "registry validation receipt",
            },
        ],
    }


def _implemented_organ_ids(organ_registry: dict[str, Any]) -> list[str]:
    rows = organ_registry.get("implemented_organs")
    if not isinstance(rows, list):
        return []
    return [
        str(row.get("organ_id"))
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("organ_id"), str)
    ]


def _source_open_body_import_count_from_fixture_manifests(
    root: Path,
    organ_ids: list[str],
) -> dict[str, Any]:
    material_count = 0
    rows_with_imports = 0
    manifest_count = 0

    for organ_id in organ_ids:
        manifest_ref = Path(FIXTURE_MANIFESTS_REF) / f"{organ_id}.fixture_manifest.json"
        manifest = _load_public_json(root, manifest_ref.as_posix())
        if not manifest:
            continue
        manifest_count += 1
        body_imports = manifest.get("source_open_body_imports")
        if isinstance(body_imports, dict):
            material_ids = _strings(body_imports.get("body_material_ids"))
            raw_count = body_imports.get("body_material_count")
            organ_material_count = (
                raw_count
                if isinstance(raw_count, int) and not isinstance(raw_count, bool)
                else len(material_ids)
            )
        else:
            body_status = str(manifest.get("body_material_status") or "")
            raw_count = manifest.get("body_copied_material_count")
            if not body_status:
                continue
            organ_material_count = (
                raw_count
                if isinstance(raw_count, int) and not isinstance(raw_count, bool)
                else 0
            )

        if organ_material_count <= 0:
            continue
        rows_with_imports += 1
        material_count += organ_material_count

    return {
        "material_count": material_count if manifest_count else None,
        "rows_with_imports": rows_with_imports if manifest_count else None,
        "manifest_count": manifest_count,
        "source_ref": f"{FIXTURE_MANIFESTS_REF}/*.fixture_manifest.json",
        "source_field": "source_open_body_imports.body_material_count",
        "fallback_ref": WORKINGNESS_MAP_REF,
    }


def _evidence_class_legend(root: Path) -> dict[str, Any]:
    registry = _load_public_json(root, EVIDENCE_CLASS_REGISTRY_REF)
    class_profiles = registry.get("class_profiles", {})
    if not isinstance(class_profiles, dict):
        class_profiles = {}

    rows: list[dict[str, Any]] = []
    missing_profiles: list[str] = []
    for class_id in EVIDENCE_CLASS_DISPLAY_ORDER:
        profile = class_profiles.get(class_id)
        if not isinstance(profile, dict):
            missing_profiles.append(class_id)
            continue
        rows.append(
            {
                "evidence_class": class_id,
                "label": EVIDENCE_CLASS_LABELS[class_id],
                "claim_ceiling": profile.get("claim_ceiling"),
                "evaluator_basis": profile.get("evaluator_basis"),
                "negative_case_independence": profile.get(
                    "negative_case_independence"
                ),
                "truth_accounting_bucket": profile.get("truth_accounting_bucket"),
                "counts_as_real_substrate_progress": profile.get(
                    "counts_as_real_substrate_progress"
                )
                is True,
                "evidence_strength_rank": profile.get("evidence_strength_rank"),
                "reader_rule": "declared_claim_ceiling_not_maturity_or_release_score",
            }
        )

    return {
        "schema_version": "microcosm_evidence_class_legend_v1",
        "source_ref": EVIDENCE_CLASS_REGISTRY_REF,
        "interpretation": "claim_boundary_legend_not_score",
        "authority_boundary": registry.get("authority_boundary"),
        "anti_claim": registry.get("anti_claim"),
        "reader_rule": (
            "Each evidence class names what a count can claim and what it cannot "
            "claim. It is a public claim-boundary legend, not a benchmark, release "
            "gate, product-completeness signal, or maturity score."
        ),
        "classes": rows,
        "missing_profiles": missing_profiles,
    }


def _scale_frame(root: Path) -> dict[str, Any]:
    organ_registry = _load_public_json(root, ORGAN_REGISTRY_REF)
    standards_registry = _load_public_json(root, STANDARDS_REGISTRY_REF)
    workingness_map = _load_public_json(root, WORKINGNESS_MAP_REF)
    implemented_organ_ids = _implemented_organ_ids(organ_registry)
    fixture_body_counts = _source_open_body_import_count_from_fixture_manifests(
        root,
        implemented_organ_ids,
    )
    implemented_organ_count = _first_count(
        _collection_count(organ_registry.get("implemented_organs")),
        _non_negative_int(workingness_map.get("mapped_organ_count")),
    )
    standard_count = _first_count(
        _non_negative_int(standards_registry.get("standard_count")),
        _collection_count(standards_registry.get("standards")),
    )
    source_open_material_count = _non_negative_int(
        workingness_map.get("source_open_body_material_count")
    )
    fixture_source_open_material_count = _non_negative_int(
        fixture_body_counts.get("material_count")
    )
    fixture_rows_with_source_imports = _non_negative_int(
        fixture_body_counts.get("rows_with_imports")
    )
    return {
        "composition_root": (
            "The shared first command is the landing surface; standards, receipts, organs, and "
            "observatory views are drilldowns."
        ),
        "count_interpretation": "receipt_backed_handles_not_scores",
        "public_scale_counts": {
            "implemented_organs": {
                "count": implemented_organ_count,
                "source_ref": ORGAN_REGISTRY_REF,
                "read_as": "accepted_public_inventory_not_release_readiness",
            },
            "public_standards": {
                "count": standard_count,
                "source_ref": STANDARDS_REGISTRY_REF,
                "read_as": "standard_inventory_not_completeness_score",
            },
            "first_wave_required_standards": {
                "count": _non_negative_int(
                    standards_registry.get("first_wave_required_standard_count")
                ),
                "source_ref": STANDARDS_REGISTRY_REF,
                "read_as": "registry_scope_field_not_product_progress",
            },
            "mapped_organs": {
                "count": _non_negative_int(workingness_map.get("mapped_organ_count")),
                "source_ref": WORKINGNESS_MAP_REF,
                "read_as": "workingness_map_coverage_not_whole_system_correctness",
            },
            "adapter_backed_organs": {
                "count": _non_negative_int(
                    workingness_map.get("adapter_backed_organ_count")
                ),
                "source_ref": WORKINGNESS_MAP_REF,
                "read_as": "adapter_presence_not_completeness_or_release_signal",
            },
            "source_open_materials": {
                "count": _first_count(
                    fixture_source_open_material_count,
                    source_open_material_count,
                ),
                "source_field": fixture_body_counts["source_field"],
                "source_ref": fixture_body_counts["source_ref"],
                "fallback_ref": fixture_body_counts["fallback_ref"],
                "workingness_source_field": "source_open_body_material_count",
                "read_as": "copy_boundary_accounting_not_maturity_score",
            },
            "rows_with_source_imports": {
                "count": _first_count(
                    fixture_rows_with_source_imports,
                    _non_negative_int(
                        workingness_map.get("rows_with_source_body_imports")
                    ),
                ),
                "source_field": "source_open_body_imports.body_material_count",
                "source_ref": fixture_body_counts["source_ref"],
                "fallback_ref": WORKINGNESS_MAP_REF,
                "workingness_source_field": "rows_with_source_body_imports",
                "read_as": "receipt_trace_count_not_claim_strength",
            },
        },
        "count_reader_rule": (
            "Treat each number as a pointer into a public owner receipt. A low or high count "
            "does not by itself claim maturity, readiness, completeness, or correctness."
        ),
        "scale_handles": [
            {
                "handle": "standards registry",
                "ref": STANDARDS_REGISTRY_REF,
            },
            {
                "handle": "organ registry",
                "ref": ORGAN_REGISTRY_REF,
            },
            {
                "handle": "workingness map",
                "command": "microcosm workingness",
                "ref": WORKINGNESS_MAP_REF,
            },
            {
                "handle": "authority boundary",
                "command": "microcosm authority",
            },
            {
                "handle": "localhost observatory",
                "endpoint_ref": "http://localhost:8765/workingness",
            },
        ],
        "scale_rule": (
            "Breadth should appear as a named composition root plus drilldown handles, "
            "not as a long first-screen inventory."
        ),
    }


def _comparison_frame() -> dict[str, Any]:
    return {
        "purpose": "make_rigor_visible_without_claim_inflation",
        "common_entry_failure_modes": [
            "a long command inventory before the reader sees the first useful behavior",
            "honest evidence counts shown without explaining what they do and do not mean",
            "reader-specific pitches before every reader has seen the same local evidence surface",
            "discipline hidden as implementation detail instead of presented as an inspectable boundary",
        ],
        "microcosm_entry_discipline": [
            "one shared local behavior command before reader branching",
            "evidence counts framed as accounting, not readiness or progress scoring",
            "authority ceilings and anti-claims visible before proof, release, or hosted claims",
            "drilldown refs preserve depth instead of copying full bodies into the first screen",
        ],
        "reader_effect": (
            "The card shows what Microcosm refuses to overclaim, then lets each reader choose "
            "the drilldown that matches their job."
        ),
    }


def _discipline_comparison_strip(project_label: str) -> dict[str, Any]:
    shared_first_command = f"microcosm tour --card {project_label}"
    return {
        "schema_version": "microcosm_discipline_comparison_strip_v1",
        "purpose": "make_microcosm_rigor_visible_as_operational_differences",
        "strip_rule": (
            "Show what Microcosm does differently from a typical cold-entry surface "
            "as inspectable boundaries, not as superiority, benchmark, or maturity claims."
        ),
        "rows": [
            {
                "comparison_id": "failure_modes_declared",
                "ordinary_entry_pattern": "polished claims hide failure surfaces",
                "microcosm_discipline": (
                    "first-screen packets expose anti_claim, authority ceiling, omission "
                    "receipt, and explicit failure-mode refs"
                ),
                "visible_check_surface": "authority_ceiling",
                "reader_rule": "Treat refusal fields as part of the product surface.",
                "not_claim": "better_than_other_systems",
            },
            {
                "comparison_id": "evidence_counts_contextualized",
                "ordinary_entry_pattern": "counts read as maturity, readiness, or progress scores",
                "microcosm_discipline": (
                    "counts are evidence-class accounting with named claim ceilings and "
                    "missing-profile disclosure"
                ),
                "visible_check_surface": "evidence_class_legend",
                "reader_rule": "Read low or high counts as boundary accounting.",
                "not_claim": "maturity_or_readiness_score",
            },
            {
                "comparison_id": "body_copy_boundaries",
                "ordinary_entry_pattern": "body copying is implied or hidden behind prose",
                "microcosm_discipline": (
                    "body imports are evidence classes; copied body status must preserve "
                    "validator and source-boundary refs"
                ),
                "visible_check_surface": EVIDENCE_CLASS_REGISTRY_REF,
                "reader_rule": "Ask what crossed a declared copy boundary.",
                "not_claim": "private_body_equivalence",
            },
            {
                "comparison_id": "reader_branch_authority_shared",
                "ordinary_entry_pattern": "audience-specific pitch creates different claim ceilings",
                "microcosm_discipline": (
                    "reader routes change inspection order while inheriting the same "
                    "authority ceiling and omission receipt"
                ),
                "visible_check_surface": "reader_route_menu",
                "reader_rule": "Choose a branch only after the shared behavior proof.",
                "not_claim": "reader_specific_authority",
            },
            {
                "comparison_id": "local_behavior_before_claims",
                "ordinary_entry_pattern": "status claims appear before runnable local evidence",
                "microcosm_discipline": (
                    f"`{shared_first_command}` writes .microcosm state and exposes "
                    "front_door_status, selected_route_id, state refs, and source_files_mutated"
                ),
                "visible_check_surface": "behavior_proof_packet",
                "reader_rule": "Run the local behavior card before trusting the scale story.",
                "not_claim": "release_or_proof_correctness",
            },
        ],
        "safe_to_show": {
            "uses_existing_first_screen_packets": True,
            "exports_private_paths": False,
            "exports_provider_payloads": False,
            "claims_external_benchmark": False,
            "claims_superiority": False,
            "claims_release_or_hosting": False,
            "claims_whole_system_correctness": False,
        },
        "authority": "comparison_strip_not_benchmark_or_superiority_claim",
    }


def _doctrine_effect_frame() -> dict[str, Any]:
    return {
        "schema_version": "microcosm_doctrine_effect_frame_v1",
        "purpose": "show_doctrine_as_mistake_prevention_not_ceremony",
        "reader_rule": (
            "Read each doctrine handle by the failure it blocks and the first-screen "
            "surface where that protection is visible."
        ),
        "effect_rows": [
            {
                "doctrine_handle": "CONSTITUTION",
                "prevents": "shipping a capability story without a claim boundary",
                "visible_effect": (
                    "authority_ceiling and anti_claim appear before proof, release, "
                    "or hosted-publication claims"
                ),
                "first_screen_surface": "authority_ceiling",
            },
            {
                "doctrine_handle": "AXIOMS",
                "prevents": "treating counts or projections as source authority",
                "visible_effect": (
                    "evidence counts are accounting fields, not readiness, maturity, "
                    "or progress scores"
                ),
                "first_screen_surface": "evidence_count_frame",
            },
            {
                "doctrine_handle": "PRINCIPLES",
                "prevents": "hiding a broad substrate behind a vague pitch",
                "visible_effect": (
                    "one shared first command lands before reader-specific drilldowns"
                ),
                "first_screen_surface": "reader_routes",
            },
            {
                "doctrine_handle": "CONCEPTS",
                "prevents": "letting repeated public terms drift into vague labels",
                "visible_effect": (
                    "concept handles must keep source refs, relationships, payload "
                    "shape, public-safe standard boundary, and specimen route visible"
                ),
                "first_screen_surface": "doctrine_effect_frame",
                "standard_ref": "standards/std_microcosm_concept.json",
                "agent_entry_ref": "AGENTS.md::Concept And Mechanism Entry",
                "specimen_route_ref": (
                    "atlas/entry_packet.json::"
                    "concept_mechanism_entry_route.population_specimens"
                ),
            },
            {
                "doctrine_handle": "MECHANISMS",
                "prevents": "describing a feature without the transformation it performs",
                "visible_effect": (
                    "mechanism handles must name the state, proof, routing, or "
                    "doctrine transformation plus validator attachment and specimen"
                ),
                "first_screen_surface": "doctrine_effect_frame",
                "standard_ref": "standards/std_microcosm_mechanism.json",
                "agent_entry_ref": "AGENTS.md::Concept And Mechanism Entry",
                "specimen_route_ref": (
                    "atlas/entry_packet.json::"
                    "concept_mechanism_entry_route.population_specimens"
                ),
            },
            {
                "doctrine_handle": "ANTI_PRINCIPLES",
                "prevents": (
                    "turning a local demo into release, provider-call, private-data, "
                    "or benchmark authority"
                ),
                "visible_effect": (
                    "omission receipt and public/private boundary name what is not "
                    "shown or authorized"
                ),
                "first_screen_surface": "omission_receipt",
            },
        ],
        "forbidden_read": "governance_prose_as_credential",
        "authority": "first_screen_interpretation_frame_not_doctrine_source",
    }


def _readme_entry_contract(project_label: str) -> dict[str, Any]:
    human_first_command = f"microcosm hello {project_label}"
    shared_first_command = f"microcosm tour --card {project_label}"
    first_screen_json_command = f"microcosm first-screen {project_label}"
    return {
        "schema_version": "microcosm_readme_entry_contract_v1",
        "purpose": "make_package_backed_first_screen_card_the_readme_entry_surface",
        "inventory_policy": (
            "quickstart_command_inventory_is_a_drilldown_after_the_first_screen_card"
        ),
        "required_markdown_order": [
            {
                "surface": "README.md::Choose Your First Screen",
                "must_precede": "README.md::Try It On Your Repo",
                "reason": (
                    "Cold readers should see the composition root before install, "
                    "direct-run, and full command inventories."
                ),
            },
            {
                "command": human_first_command,
                "must_precede": shared_first_command,
                "reason": "Text projection opens the card before the state-writing behavior proof.",
            },
            {
                "command": shared_first_command,
                "must_precede": first_screen_json_command,
                "reason": "Local behavior proof precedes the machine-readable reader map.",
            },
            {
                "surface": "reader_route_menu",
                "must_precede": "quickstart_command_inventory",
                "reason": "Focused reader commands are first-screen branches, not inventory rows.",
            },
            {
                "surface": "reader_routes",
                "must_precede": "quickstart_command_inventory",
                "reason": "Reader branching happens before the long command list.",
            },
            {
                "surface": "first_viewport_manifest",
                "must_precede": "quickstart_command_inventory",
                "reason": (
                    "Every entry projection should carry the same ordered slots before "
                    "expanding the inventory."
                ),
            },
        ],
        "consumer_rule": (
            "README and docs consumers must show the package-backed hello/tour card "
            "before any exhaustive quickstart inventory, while preserving full "
            "drilldowns after the first screen."
        ),
        "authority": "documentation_order_contract_not_runtime_proof",
    }


def _entry_surface_contract(project_label: str) -> dict[str, Any]:
    return {
        "shared_behavior_surface": f"microcosm tour --card {project_label}",
        "package_surface": (
            "microcosm_core.first_screen_composition.first_screen_composition_card"
        ),
        "text_projection_surface": (
            "microcosm_core.first_screen_composition.first_screen_text_card"
        ),
        "script_surface": (
            f"python3 scripts/first_screen_composition_card.py --project-label {project_label}"
        ),
        "consumer_rule": (
            "README, CLI, and observatory consumers should reuse this package contract and "
            "preserve the shared first command, reader route ids, reader route menu, "
            "reader landing packets, behavior-proof packet, first-run ladder, local state receipt trail, "
            "first-viewport manifest, overclaim tripwire matrix, reader exit "
            "criteria, evidence-count frame, video-storyboard packet, artifact-fit "
            "matrix, cold-entry problem map, discipline comparison strip, "
            "evidence-class legend, doctrine-effect frame, observatory landing "
            "frame, README-entry contract, omission "
            "receipt, and authority ceiling."
        ),
        "format_contract": {
            "json": "machine-readable public card",
            "text": "terminal-sized projection over the same authority ceiling",
        },
    }


def _runnable_structural_join(project_label: str) -> dict[str, Any]:
    return {
        "local_behavior": (
            f"`microcosm tour --card {project_label}` is the first folder-local behavior surface: "
            "it lets a reader see compact local state before choosing a route."
        ),
        "structural_context": (
            "That local run is one visible exercise of the larger public substrate: standards, "
            "receipts, authority boundaries, workingness, route maps, and observatory endpoints."
        ),
        "join_rule": "The first run must name the larger structure it exercised without copying the deeper bodies.",
    }


def _observatory_landing_frame(project_label: str) -> dict[str, Any]:
    human_first_command = f"microcosm hello {project_label}"
    shared_first_command = f"microcosm tour --card {project_label}"
    serve_command = _observatory_serve_command(project_label)
    bounded_serve_command = _bounded_observatory_serve_command(project_label)
    return {
        "schema_version": "microcosm_observatory_landing_frame_v1",
        "role": "make_the_hello_first_screen_card_the_browser_landing_frame",
        "human_first_command": human_first_command,
        "text_projection_command": human_first_command,
        "shared_first_command": shared_first_command,
        "behavioral_proof_command": shared_first_command,
        "serve_command": serve_command,
        "bounded_validation_command": bounded_serve_command,
        "bounded_validation_request_count": 6,
        "bounded_validation_rule": (
            "Use bounded_validation_command for first-screen route smokes; use "
            "serve_command for an interactive browser session."
        ),
        "endpoints": dict(OBSERVATORY_LANDING_ENDPOINTS),
        "browser_landing_reuse": {
            "source_projection": (
                "microcosm_core.first_screen_composition.first_screen_text_card"
            ),
            "serve_command": serve_command,
            "bounded_validation_command": bounded_serve_command,
            "default_endpoint": OBSERVATORY_LANDING_ENDPOINTS["html_landing"],
            "card_endpoint": OBSERVATORY_LANDING_ENDPOINTS["first_screen_card"],
            "authority": (
                "browser_projection_over_same_card_not_json_first_lens_inventory"
            ),
        },
        "first_viewport_rule": (
            "The browser landing frame should show the hello card command, behavior proof, "
            "first-run ladder, first-viewport manifest, local state receipt trail, "
            "first-contact surface refs, overclaim tripwires, discipline comparison strip, "
            "reader branches, reader route menu, reader landing packets, reader exit criteria, video storyboard packet, "
            "artifact fit matrix, cold-entry problem map, public scale handles, evidence-class "
            "legend, doctrine-effect frame, and authority ceiling before the deeper "
            "observatory lens inventory."
        ),
        "projection_rule": (
            "The observatory landing is a projection over this first-screen card, not a "
            "separate cold-entry artifact with its own claims."
        ),
        "required_visible_handles": [
            "human_first_command",
            "text_projection",
            "shared_first_command",
            "behavioral_proof_command",
            "serve_command",
            "bounded_validation_command",
            "reader_route_ids",
            "reader_route_menu",
            "reader_landing_packets",
            "behavior_proof_packet",
            "first_run_ladder",
            "first_viewport_manifest",
            "local_state_receipt_trail",
            "first_contact_surface_refs",
            "overclaim_tripwire_matrix",
            "discipline_comparison_strip",
            "reader_exit_criteria",
            "video_storyboard_packet",
            "artifact_fit_matrix",
            "cold_entry_problem_map",
            "public_scale_counts",
            "evidence_count_interpretation",
            "evidence_class_legend",
            "doctrine_effect_frame",
            "authority_ceiling",
            "omission_receipt",
        ],
        "drilldown_order": [
            "html_landing",
            "first_screen_card",
            "compact_observatory_card",
            "full_observatory_model",
            "project_observe",
        ],
        "authority_boundary": (
            "Local browser display is a public read-model boundary. It does not authorize "
            "release, hosting, provider calls, source mutation, private-data equivalence, "
            "or whole-system correctness claims."
        ),
    }


def _drilldowns(project_label: str) -> list[dict[str, str]]:
    return [
        {
            "drilldown_id": "observatory_server",
            "command": _observatory_serve_command(project_label),
            "endpoint": OBSERVATORY_LANDING_ENDPOINTS["html_landing"],
        },
        {
            "drilldown_id": "bounded_observatory_validation",
            "command": _bounded_observatory_serve_command(project_label),
            "endpoint": OBSERVATORY_LANDING_ENDPOINTS["html_landing"],
        },
        {
            "drilldown_id": "observatory_landing",
            "endpoint": OBSERVATORY_LANDING_ENDPOINTS["html_landing"],
        },
        {
            "drilldown_id": "first_screen_endpoint",
            "endpoint": OBSERVATORY_LANDING_ENDPOINTS["first_screen_card"],
        },
        {
            "drilldown_id": "shared_first_card",
            "command": f"microcosm tour --card {project_label}",
        },
        {
            "drilldown_id": "status_card",
            "command": f"microcosm status --card {project_label}",
        },
        {
            "drilldown_id": "authority",
            "command": "microcosm authority",
        },
        {
            "drilldown_id": "workingness",
            "command": "microcosm workingness",
        },
        {
            "drilldown_id": "evidence_class_registry",
            "ref": EVIDENCE_CLASS_REGISTRY_REF,
        },
        {
            "drilldown_id": "cold_reader_route_map",
            "ref": "paper_modules/cold_reader_route_map.md",
        },
        {
            "drilldown_id": "public_reveal_walkthrough",
            "ref": "paper_modules/public_reveal_walkthrough.md",
        },
        {
            "drilldown_id": "composition_standard",
            "ref": str(STANDARD_REF),
        },
    ]


def _validation_checks(payload: dict[str, Any]) -> dict[str, bool]:
    route_ids = {
        str(route.get("reader_route_id"))
        for route in payload.get("reader_routes", [])
        if isinstance(route, dict)
    }
    reader_landing_packets = payload.get("reader_landing_packets", {})
    reader_packet_rows = (
        reader_landing_packets.get("packets", [])
        if isinstance(reader_landing_packets, dict)
        else []
    )
    reader_packet_ids = {
        str(packet.get("reader_route_id"))
        for packet in reader_packet_rows
        if isinstance(packet, dict)
    }
    reader_route_menu = payload.get("reader_route_menu", {})
    reader_route_menu_rows = (
        reader_route_menu.get("routes", [])
        if isinstance(reader_route_menu, dict)
        else []
    )
    reader_route_menu_ids = {
        str(row.get("reader_route_id"))
        for row in reader_route_menu_rows
        if isinstance(row, dict)
    }
    reader_route_menu_safe_to_show = (
        reader_route_menu.get("safe_to_show", {})
        if isinstance(reader_route_menu, dict)
        else {}
    )
    human_first_command = payload.get("human_first_command", "")
    shared_first_command = payload.get("shared_first_command", "")
    text_projection = payload.get("text_projection", {})
    authority_ceiling = payload.get("authority_ceiling", {})
    drilldown_text = json.dumps(payload.get("drilldowns", []), sort_keys=True)
    evidence_class_legend = payload.get("evidence_class_legend", {})
    legend_rows = (
        evidence_class_legend.get("classes", [])
        if isinstance(evidence_class_legend, dict)
        else []
    )
    legend_ids = {
        str(row.get("evidence_class"))
        for row in legend_rows
        if isinstance(row, dict)
    }
    scale_frame = payload.get("scale_frame", {})
    scale_counts = scale_frame.get("public_scale_counts", {})
    state_write_boundary = payload.get("state_write_boundary", {})
    behavior_proof_packet = payload.get("behavior_proof_packet", {})
    local_state_receipt_trail = payload.get("local_state_receipt_trail", {})
    first_contact_surface_refs = payload.get("first_contact_surface_refs", {})
    overclaim_tripwire_matrix = payload.get("overclaim_tripwire_matrix", {})
    discipline_comparison_strip = payload.get("discipline_comparison_strip", {})
    first_contact_surfaces = (
        first_contact_surface_refs.get("surfaces", {})
        if isinstance(first_contact_surface_refs, dict)
        else {}
    )
    first_contact_surface_ids = (
        set(first_contact_surfaces)
        if isinstance(first_contact_surfaces, dict)
        else set()
    )
    local_state_trail_rows = (
        local_state_receipt_trail.get("trail", [])
        if isinstance(local_state_receipt_trail, dict)
        else []
    )
    local_state_trail_ids = {
        str(row.get("surface_id"))
        for row in local_state_trail_rows
        if isinstance(row, dict)
    }
    overclaim_rows = (
        overclaim_tripwire_matrix.get("rows", [])
        if isinstance(overclaim_tripwire_matrix, dict)
        else []
    )
    overclaim_ids = {
        str(row.get("tripwire_id")) for row in overclaim_rows if isinstance(row, dict)
    }
    discipline_comparison_rows = (
        discipline_comparison_strip.get("rows", [])
        if isinstance(discipline_comparison_strip, dict)
        else []
    )
    discipline_comparison_ids = {
        str(row.get("comparison_id"))
        for row in discipline_comparison_rows
        if isinstance(row, dict)
    }
    discipline_comparison_safe_to_show = (
        discipline_comparison_strip.get("safe_to_show", {})
        if isinstance(discipline_comparison_strip, dict)
        else {}
    )
    reader_exit_criteria = payload.get("reader_exit_criteria", {})
    reader_exit_rows = (
        reader_exit_criteria.get("criteria", [])
        if isinstance(reader_exit_criteria, dict)
        else []
    )
    reader_exit_ids = {
        str(row.get("reader_route_id"))
        for row in reader_exit_rows
        if isinstance(row, dict)
    }
    video_storyboard_packet = payload.get("video_storyboard_packet", {})
    video_storyboard_beats = (
        video_storyboard_packet.get("beats", [])
        if isinstance(video_storyboard_packet, dict)
        else []
    )
    video_storyboard_beat_ids = {
        str(row.get("beat_id"))
        for row in video_storyboard_beats
        if isinstance(row, dict)
    }
    video_storyboard_safe_to_show = (
        video_storyboard_packet.get("safe_to_show", {})
        if isinstance(video_storyboard_packet, dict)
        else {}
    )
    artifact_fit_matrix = payload.get("artifact_fit_matrix", {})
    artifact_fit_rows = (
        artifact_fit_matrix.get("rows", [])
        if isinstance(artifact_fit_matrix, dict)
        else []
    )
    artifact_fit_ids = {
        str(row.get("surface_id")) for row in artifact_fit_rows if isinstance(row, dict)
    }
    artifact_fit_safe_to_show = (
        artifact_fit_matrix.get("safe_to_show", {})
        if isinstance(artifact_fit_matrix, dict)
        else {}
    )
    cold_entry_problem_map = payload.get("cold_entry_problem_map", {})
    cold_entry_problem_rows = (
        cold_entry_problem_map.get("rows", [])
        if isinstance(cold_entry_problem_map, dict)
        else []
    )
    cold_entry_problem_ids = {
        str(row.get("problem_shape_id"))
        for row in cold_entry_problem_rows
        if isinstance(row, dict)
    }
    cold_entry_problem_safe_to_show = (
        cold_entry_problem_map.get("safe_to_show", {})
        if isinstance(cold_entry_problem_map, dict)
        else {}
    )
    behavior_proof_fields = (
        behavior_proof_packet.get("proof_fields", [])
        if isinstance(behavior_proof_packet, dict)
        else []
    )
    behavior_proof_field_ids = {
        str(row.get("field"))
        for row in behavior_proof_fields
        if isinstance(row, dict)
    }
    first_run_ladder = payload.get("first_run_ladder", {})
    first_run_steps = (
        first_run_ladder.get("steps", [])
        if isinstance(first_run_ladder, dict)
        else []
    )
    first_run_step_ids = {
        str(row.get("step_id")) for row in first_run_steps if isinstance(row, dict)
    }
    first_run_commands = {
        str(row.get("step_id")): row.get("command")
        for row in first_run_steps
        if isinstance(row, dict)
    }
    first_viewport_manifest = payload.get("first_viewport_manifest", {})
    first_viewport_slots = (
        first_viewport_manifest.get("slots", [])
        if isinstance(first_viewport_manifest, dict)
        else []
    )
    first_viewport_slot_ids = [
        str(row.get("slot_id")) for row in first_viewport_slots if isinstance(row, dict)
    ]
    first_viewport_problem_slots = (
        first_viewport_manifest.get("problem_shape_slot_map", [])
        if isinstance(first_viewport_manifest, dict)
        else []
    )
    first_viewport_problem_ids = {
        str(row.get("problem_shape_id"))
        for row in first_viewport_problem_slots
        if isinstance(row, dict)
    }
    first_viewport_problem_slot_ids = {
        str(row.get("slot_id"))
        for row in first_viewport_problem_slots
        if isinstance(row, dict)
    }
    first_viewport_consumer_surfaces = (
        first_viewport_manifest.get("consumer_surfaces", {})
        if isinstance(first_viewport_manifest, dict)
        else {}
    )
    first_viewport_safe_to_show = (
        first_viewport_manifest.get("safe_to_show", {})
        if isinstance(first_viewport_manifest, dict)
        else {}
    )
    observatory_landing_frame = payload.get("observatory_landing_frame", {})
    doctrine_effect_frame = payload.get("doctrine_effect_frame", {})
    readme_entry_contract = payload.get("readme_entry_contract", {})
    doctrine_effect_rows = (
        doctrine_effect_frame.get("effect_rows", [])
        if isinstance(doctrine_effect_frame, dict)
        else []
    )
    doctrine_handles = {
        str(row.get("doctrine_handle"))
        for row in doctrine_effect_rows
        if isinstance(row, dict)
    }
    observatory_endpoints = (
        observatory_landing_frame.get("endpoints", {})
        if isinstance(observatory_landing_frame, dict)
        else {}
    )
    required_visible_handles = (
        observatory_landing_frame.get("required_visible_handles", [])
        if isinstance(observatory_landing_frame, dict)
        else []
    )
    readme_order_rows = (
        readme_entry_contract.get("required_markdown_order", [])
        if isinstance(readme_entry_contract, dict)
        else []
    )
    readme_order_pairs = {
        (str(row.get("surface") or row.get("command")), str(row.get("must_precede")))
        for row in readme_order_rows
        if isinstance(row, dict)
    }
    return {
        "shared_first_command": payload.get("shared_first_command", "").startswith(
            "microcosm tour --card "
        ),
        "human_first_command": (
            isinstance(human_first_command, str)
            and human_first_command.startswith("microcosm hello ")
            and human_first_command != shared_first_command
        ),
        "text_projection": (
            isinstance(text_projection, dict)
            and text_projection.get("command") == human_first_command
            and text_projection.get("writes_microcosm_state") is False
            and text_projection.get("behavioral_proof_command")
            == shared_first_command
            and text_projection.get("authority")
            == "terminal_text_projection_only_not_behavior_proof"
        ),
        "reader_route_ids": route_ids == REQUIRED_ROUTE_IDS,
        "reader_landing_packets": (
            isinstance(reader_landing_packets, dict)
            and reader_landing_packets.get("purpose")
            == "turn_reader_routes_into_first_action_proof_success_packets"
            and reader_landing_packets.get("shared_authority_rule", "").endswith(
                "same authority ceiling, anti-claim, and omission receipt."
            )
            and reader_packet_ids == REQUIRED_ROUTE_IDS
            and all(
                isinstance(packet, dict)
                and isinstance(packet.get("first_action"), str)
                and bool(packet.get("first_action"))
                and isinstance(packet.get("proof_surface"), str)
                and bool(packet.get("proof_surface"))
                and isinstance(packet.get("success_criterion"), str)
                and bool(packet.get("success_criterion"))
                and isinstance(packet.get("next_drilldown"), str)
                and bool(packet.get("next_drilldown"))
                and str(packet.get("authority", "")).startswith(
                    "inspection_order_only_not_"
                )
                for packet in reader_packet_rows
            )
        ),
        "reader_route_menu": (
            isinstance(reader_route_menu, dict)
            and reader_route_menu.get("schema_version")
            == "microcosm_reader_route_menu_v1"
            and reader_route_menu.get("purpose")
            == (
                "make_reader_typed_first_screens_copyable_without_separate_entry_"
                "artifacts"
            )
            and "shared map and behavior proof first"
            in reader_route_menu.get("menu_rule", "")
            and reader_route_menu.get("default_command") == human_first_command
            and reader_route_menu.get("shared_behavior_command")
            == shared_first_command
            and reader_route_menu.get("machine_card_command")
            == f"microcosm first-screen {payload.get('project_label')}"
            and reader_route_menu_ids == REQUIRED_ROUTE_IDS
            and all(
                isinstance(row, dict)
                and row.get("label") == READER_LABELS.get(str(row.get("reader_route_id")))
                and isinstance(row.get("terminal_command"), str)
                and row["terminal_command"]
                == (
                    "microcosm hello --reader "
                    f"{row.get('reader_route_id')} {payload.get('project_label')}"
                )
                and isinstance(row.get("text_projection_command"), str)
                and row["text_projection_command"]
                == (
                    "microcosm first-screen --format text --reader "
                    f"{row.get('reader_route_id')} {payload.get('project_label')}"
                )
                and isinstance(row.get("first_action"), str)
                and bool(row.get("first_action"))
                and isinstance(row.get("proof_surface"), str)
                and bool(row.get("proof_surface"))
                and isinstance(row.get("exit_check"), str)
                and bool(row.get("exit_check"))
                and isinstance(row.get("not_a_claim"), str)
                and bool(row.get("not_a_claim"))
                and str(row.get("authority", "")).startswith(
                    "focused_projection_only_not_"
                )
                for row in reader_route_menu_rows
            )
            and reader_route_menu_safe_to_show.get("uses_existing_reader_packets")
            is True
            and reader_route_menu_safe_to_show.get("creates_new_entry_artifact")
            is False
            and reader_route_menu_safe_to_show.get(
                "creates_reader_specific_claim_ceiling"
            )
            is False
            and reader_route_menu_safe_to_show.get("exports_private_paths") is False
            and reader_route_menu_safe_to_show.get("exports_provider_payloads")
            is False
            and reader_route_menu_safe_to_show.get("claims_release_or_hosting")
            is False
            and reader_route_menu_safe_to_show.get("claims_reader_success") is False
            and reader_route_menu.get("authority")
            == "reader_route_menu_not_new_entry_artifact_or_reader_success_authority"
        ),
        "behavior_proof_packet": (
            isinstance(behavior_proof_packet, dict)
            and behavior_proof_packet.get("purpose")
            == "turn_shared_first_run_into_inspectable_success_conditions"
            and behavior_proof_packet.get("command") == shared_first_command
            and behavior_proof_packet.get("writes_state") is True
            and behavior_proof_packet.get("state_dir") == ".microcosm"
            and behavior_proof_field_ids
            == {
                "front_door_status.status",
                "selected_route_id",
                "state_inspection",
                "source_files_mutated",
            }
            and all(
                isinstance(row, dict)
                and "success_read" in row
                and isinstance(row.get("reader_rule"), str)
                and bool(row.get("reader_rule"))
                for row in behavior_proof_fields
            )
            and behavior_proof_packet.get("authority")
            == "local_behavior_receipt_not_release_or_proof_authority"
        ),
        "first_run_ladder": (
            isinstance(first_run_ladder, dict)
            and first_run_ladder.get("purpose")
            == "make_first_screen_run_order_copyable_without_long_quickstart"
            and first_run_step_ids
            == {
                "map",
                "behavior_proof",
                "status_confirmation",
                "reader_branch",
            }
            and first_run_commands.get("map") == human_first_command
            and first_run_commands.get("behavior_proof") == shared_first_command
            and first_run_commands.get("status_confirmation")
            == f"microcosm status --card {payload.get('project_label', '<project>')}"
            and all(
                isinstance(row, dict)
                and "writes_microcosm_state" in row
                and isinstance(row.get("expected_surface"), str)
                and bool(row.get("expected_surface"))
                and isinstance(row.get("success_read"), str)
                and bool(row.get("success_read"))
                and isinstance(row.get("authority"), str)
                and bool(row.get("authority"))
                for row in first_run_steps
            )
            and first_run_ladder.get("authority")
            == "copyable_run_order_not_quickstart_inventory_or_release_authority"
        ),
        "local_state_receipt_trail": (
            isinstance(local_state_receipt_trail, dict)
            and local_state_receipt_trail.get("purpose")
            == "show_what_the_first_run_writes_without_expanding_raw_state"
            and local_state_receipt_trail.get("producer_command")
            == shared_first_command
            and local_state_receipt_trail.get("state_dir") == ".microcosm"
            and local_state_trail_ids
            == {"catalog", "routes", "work_events", "evidence_index", "graph"}
            and all(
                isinstance(row, dict)
                and isinstance(row.get("state_ref"), str)
                and row["state_ref"].startswith(".microcosm/")
                and isinstance(row.get("reader_read"), str)
                and bool(row.get("reader_read"))
                and isinstance(row.get("not_authority_for"), str)
                and bool(row.get("not_authority_for"))
                for row in local_state_trail_rows
            )
            and local_state_receipt_trail.get("authority")
            == "local_state_receipt_trail_not_private_root_equivalence"
        ),
        "first_viewport_manifest": (
            isinstance(first_viewport_manifest, dict)
            and first_viewport_manifest.get("schema_version")
            == "microcosm_first_viewport_manifest_v1"
            and first_viewport_manifest.get("purpose")
            == (
                "make_single_screen_cold_entry_composition_explicit_for_cli_"
                "readme_browser_json_and_video"
            )
            and "before the long command inventory"
            in first_viewport_manifest.get("composition_rule", "")
            and first_viewport_slot_ids
            == [
                "identity",
                "first_run",
                "proof_chain",
                "evidence_context",
                "reader_branch",
                "authority_boundary",
            ]
            and all(
                isinstance(row, dict)
                and isinstance(row.get("viewport_copy"), str)
                and bool(row.get("viewport_copy"))
                and isinstance(row.get("source_packet"), str)
                and bool(row.get("source_packet"))
                and isinstance(row.get("first_visible_surface"), str)
                and bool(row.get("first_visible_surface"))
                and isinstance(row.get("proof_surface"), str)
                and bool(row.get("proof_surface"))
                and "authority_ceiling" in row.get("must_preserve", [])
                and "anti_claim" in row.get("must_preserve", [])
                and "omission_receipt" in row.get("must_preserve", [])
                and "discipline_comparison_strip" in row.get("must_preserve", [])
                and "release_or_hosting_authority" in row.get("must_not_claim", [])
                and "provider_call_authority" in row.get("must_not_claim", [])
                and "private_root_equivalence" in row.get("must_not_claim", [])
                and "whole_system_correctness" in row.get("must_not_claim", [])
                and "reader_success" in row.get("must_not_claim", [])
                for row in first_viewport_slots
            )
            and first_viewport_problem_ids == cold_entry_problem_ids
            and first_viewport_problem_slot_ids.issubset(set(first_viewport_slot_ids))
            and first_viewport_consumer_surfaces.get("terminal")
            == human_first_command
            and first_viewport_consumer_surfaces.get("readme")
            == "README.md::Choose Your First Screen"
            and first_viewport_consumer_surfaces.get("browser")
            == (
                f"{_bounded_observatory_serve_command(str(payload.get('project_label')))} -> /"
            )
            and first_viewport_consumer_surfaces.get("json")
            == f"microcosm first-screen {payload.get('project_label')}"
            and first_viewport_consumer_surfaces.get("video")
            == "video_storyboard_packet"
            and first_viewport_safe_to_show.get("uses_existing_first_screen_packets")
            is True
            and first_viewport_safe_to_show.get("creates_new_entry_artifact") is False
            and first_viewport_safe_to_show.get("exports_private_paths") is False
            and first_viewport_safe_to_show.get("exports_provider_payloads") is False
            and first_viewport_safe_to_show.get("claims_release_or_hosting") is False
            and first_viewport_safe_to_show.get("claims_reader_success") is False
            and first_viewport_manifest.get("authority")
            == "viewport_manifest_not_new_claim_or_renderer_authority"
        ),
        "first_contact_surface_refs": (
            isinstance(first_contact_surface_refs, dict)
            and first_contact_surface_refs.get("schema_version")
            == "microcosm_first_contact_surface_refs_v1"
            and first_contact_surface_refs.get("producer_command")
            == shared_first_command
            and set(first_contact_surface_refs.get("required_surface_ids", []))
            == {
                "route",
                "work",
                "events",
                "evidence",
                "graph",
                "observatory",
                "proof_lab",
                "status",
            }
            and first_contact_surface_ids
            == {
                "route",
                "work",
                "events",
                "evidence",
                "graph",
                "observatory",
                "proof_lab",
                "status",
            }
            and first_contact_surfaces.get("route", {}).get("state_ref")
            == ".microcosm/routes.json"
            and first_contact_surfaces.get("work", {}).get("state_ref")
            == ".microcosm/work_items.json"
            and first_contact_surfaces.get("events", {}).get("state_ref")
            == ".microcosm/events.jsonl"
            and first_contact_surfaces.get("evidence", {}).get("state_ref")
            == ".microcosm/evidence/"
            and first_contact_surfaces.get("graph", {}).get("state_ref")
            == ".microcosm/graph.json"
            and first_contact_surfaces.get("observatory", {}).get("command")
            == _observatory_serve_command(str(payload.get("project_label")))
            and first_contact_surfaces.get("observatory", {}).get(
                "bounded_validation_command"
            )
            == _bounded_observatory_serve_command(str(payload.get("project_label")))
            and first_contact_surfaces.get("observatory", {}).get(
                "compact_endpoint"
            )
            == OBSERVATORY_LANDING_ENDPOINTS["compact_observatory_card"]
            and first_contact_surfaces.get("proof_lab", {}).get("command")
            == "microcosm proof-lab --out /tmp/microcosm-proof-lab"
            and first_contact_surfaces.get("status", {}).get("command")
            == f"microcosm status --card {payload.get('project_label', '<project>')}"
            and first_contact_surface_refs.get("safe_to_show", {}).get(
                "body_text_exported"
            )
            is False
            and first_contact_surface_refs.get("safe_to_show", {}).get(
                "source_files_mutated"
            )
            is False
            and first_contact_surface_refs.get("safe_to_show", {}).get(
                "provider_calls_authorized"
            )
            is False
            and first_contact_surface_refs.get("safe_to_show", {}).get(
                "release_authorized"
            )
            is False
            and first_contact_surface_refs.get("safe_to_show", {}).get(
                "proof_correctness_claim"
            )
            is False
            and first_contact_surface_refs.get("authority")
            == (
                "first_contact_surface_map_only_not_source_release_provider_"
                "mutation_or_proof_authority"
            )
        ),
        "overclaim_tripwire_matrix": (
            isinstance(overclaim_tripwire_matrix, dict)
            and overclaim_tripwire_matrix.get("schema_version")
            == "microcosm_overclaim_tripwire_matrix_v1"
            and overclaim_tripwire_matrix.get("purpose")
            == "translate_common_cold_reader_overclaims_into_valid_bounded_reads"
            and overclaim_tripwire_matrix.get("shared_first_command")
            == shared_first_command
            and overclaim_ids
            == {
                "release_ready",
                "organ_count_whole_system",
                "low_body_import_count_fake",
                "local_state_private_root_equivalence",
                "observatory_hosted_release",
            }
            and all(
                isinstance(row, dict)
                and isinstance(row.get("overclaim"), str)
                and bool(row.get("overclaim"))
                and isinstance(row.get("valid_read"), str)
                and bool(row.get("valid_read"))
                and isinstance(row.get("check_surface"), str)
                and bool(row.get("check_surface"))
                and isinstance(row.get("reader_rule"), str)
                and bool(row.get("reader_rule"))
                for row in overclaim_rows
            )
            and overclaim_tripwire_matrix.get("authority")
            == "overclaim_tripwire_not_marketing_or_release_authority"
        ),
        "reader_exit_criteria": (
            isinstance(reader_exit_criteria, dict)
            and reader_exit_criteria.get("schema_version")
            == "microcosm_reader_exit_criteria_v1"
            and reader_exit_criteria.get("purpose")
            == "tell_cold_readers_when_the_first_screen_has_done_its_job"
            and reader_exit_criteria.get("shared_first_command")
            == shared_first_command
            and reader_exit_ids == REQUIRED_ROUTE_IDS
            and isinstance(reader_exit_criteria.get("shared_stop_rule"), str)
            and "long command inventory"
            in reader_exit_criteria.get("shared_stop_rule", "")
            and all(
                isinstance(row, dict)
                and isinstance(row.get("exit_when"), str)
                and bool(row.get("exit_when"))
                and isinstance(row.get("next_if_not_met"), str)
                and bool(row.get("next_if_not_met"))
                and isinstance(row.get("not_a_claim"), str)
                and bool(row.get("not_a_claim"))
                for row in reader_exit_rows
            )
            and reader_exit_criteria.get("authority")
            == "exit_criteria_not_reader_success_or_release_authority"
        ),
        "video_storyboard_packet": (
            isinstance(video_storyboard_packet, dict)
            and video_storyboard_packet.get("schema_version")
            == "microcosm_video_storyboard_packet_v1"
            and video_storyboard_packet.get("purpose")
            == "make_a_sixty_second_cold_entry_artifact_without_new_claims"
            and "same package-backed first-screen commands and authority ceiling"
            in video_storyboard_packet.get("artifact_rule", "")
            and video_storyboard_packet.get("allowed_artifact_forms")
            == [
                "terminal_capture",
                "browser_walkthrough",
                "static_reveal_board",
                "short_video",
            ]
            and video_storyboard_packet.get("source_projection")
            == "microcosm_core.first_screen_composition.first_screen_composition_card"
            and video_storyboard_packet.get("first_run_command")
            == shared_first_command
            and video_storyboard_packet.get("bounded_observatory_command")
            == _bounded_observatory_serve_command(str(payload.get("project_label")))
            and len(video_storyboard_beats) == 6
            and video_storyboard_beat_ids
            == {
                "open_map",
                "prove_local_behavior",
                "show_route_chain",
                "frame_evidence_counts",
                "open_authority_boundary",
                "choose_reader_branch",
            }
            and sum(
                row.get("timebox_seconds", 0)
                for row in video_storyboard_beats
                if isinstance(row, dict)
                and isinstance(row.get("timebox_seconds"), int)
                and not isinstance(row.get("timebox_seconds"), bool)
            )
            <= 60
            and all(
                isinstance(row, dict)
                and isinstance(row.get("timebox_seconds"), int)
                and not isinstance(row.get("timebox_seconds"), bool)
                and row.get("timebox_seconds") > 0
                and isinstance(row.get("visible_surface"), str)
                and bool(row.get("visible_surface"))
                and isinstance(row.get("reader_takeaway"), str)
                and bool(row.get("reader_takeaway"))
                and isinstance(row.get("proof_ref"), str)
                and bool(row.get("proof_ref"))
                for row in video_storyboard_beats
            )
            and video_storyboard_safe_to_show.get("uses_public_first_screen_card")
            is True
            and video_storyboard_safe_to_show.get("uses_localhost_read_model")
            is True
            and video_storyboard_safe_to_show.get("exports_private_paths")
            is False
            and video_storyboard_safe_to_show.get("exports_provider_payloads")
            is False
            and video_storyboard_safe_to_show.get(
                "uses_live_operator_or_browser_session"
            )
            is False
            and video_storyboard_safe_to_show.get("claims_release_or_hosting")
            is False
            and video_storyboard_safe_to_show.get("claims_reader_success")
            is False
            and "not a release artifact" in video_storyboard_packet.get("anti_claim", "")
            and video_storyboard_packet.get("authority")
            == "presentation_plan_over_existing_first_screen_contract_only"
        ),
        "artifact_fit_matrix": (
            isinstance(artifact_fit_matrix, dict)
            and artifact_fit_matrix.get("schema_version")
            == "microcosm_first_screen_artifact_fit_matrix_v1"
            and artifact_fit_matrix.get("purpose")
            == "keep_all_cold_entry_forms_bound_to_one_source_card"
            and artifact_fit_matrix.get("source_of_truth")
            == "microcosm_core.first_screen_composition.first_screen_composition_card"
            and "not independent cold-entry artifacts"
            in artifact_fit_matrix.get("matrix_rule", "")
            and len(artifact_fit_rows) == 6
            and artifact_fit_ids
            == {
                "terminal_text_projection",
                "local_behavior_card",
                "machine_json_card",
                "readme_first_screen",
                "browser_landing",
                "short_video_storyboard",
            }
            and all(
                isinstance(row, dict)
                and isinstance(row.get("artifact_form"), str)
                and bool(row.get("artifact_form"))
                and isinstance(row.get("consumer_surface"), str)
                and bool(row.get("consumer_surface"))
                and isinstance(row.get("source_projection"), str)
                and bool(row.get("source_projection"))
                and isinstance(row.get("first_job"), str)
                and bool(row.get("first_job"))
                and isinstance(row.get("must_preserve"), list)
                and "authority_ceiling" in row.get("must_preserve", [])
                and "anti_claim" in row.get("must_preserve", [])
                and "omission_receipt" in row.get("must_preserve", [])
                and "discipline_comparison_strip" in row.get("must_preserve", [])
                and isinstance(row.get("must_not_claim"), list)
                and "release_or_hosting_authority" in row.get("must_not_claim", [])
                and "provider_call_authority" in row.get("must_not_claim", [])
                and "private_root_equivalence" in row.get("must_not_claim", [])
                for row in artifact_fit_rows
            )
            and artifact_fit_safe_to_show.get("binds_to_single_source_contract")
            is True
            and artifact_fit_safe_to_show.get("allows_multiple_projection_forms")
            is True
            and artifact_fit_safe_to_show.get("exports_private_paths") is False
            and artifact_fit_safe_to_show.get("exports_provider_payloads") is False
            and artifact_fit_safe_to_show.get("creates_new_release_artifact") is False
            and artifact_fit_safe_to_show.get("creates_reader_specific_claim_ceiling")
            is False
            and artifact_fit_matrix.get("authority")
            == "projection_fit_matrix_not_new_artifact_authority"
        ),
        "cold_entry_problem_map": (
            isinstance(cold_entry_problem_map, dict)
            and cold_entry_problem_map.get("schema_version")
            == "microcosm_cold_entry_problem_map_v1"
            and cold_entry_problem_map.get("purpose")
            == "bind_cold_entry_problem_shapes_to_existing_first_screen_packets"
            and "not create a second entry artifact"
            in cold_entry_problem_map.get("map_rule", "")
            and cold_entry_problem_ids
            == {
                "first_thing_best_thing_gap",
                "audience_is_not_one_person",
                "honest_numbers_without_context",
                "discipline_invisible_without_comparison",
                "size_paradox",
                "runnable_vs_structural_split",
                "doctrine_reads_as_ceremony",
                "frontend_surface_not_seductive",
                "card_discipline_not_default",
            }
            and all(
                isinstance(row, dict)
                and isinstance(row.get("reader_risk"), str)
                and bool(row.get("reader_risk"))
                and isinstance(row.get("compression_answer"), str)
                and bool(row.get("compression_answer"))
                and isinstance(row.get("primary_packet"), str)
                and bool(row.get("primary_packet"))
                and isinstance(row.get("first_surface"), str)
                and bool(row.get("first_surface"))
                and isinstance(row.get("proof_surface"), str)
                and bool(row.get("proof_surface"))
                and isinstance(row.get("not_claim"), str)
                and bool(row.get("not_claim"))
                for row in cold_entry_problem_rows
            )
            and cold_entry_problem_safe_to_show.get(
                "uses_existing_first_screen_packets"
            )
            is True
            and cold_entry_problem_safe_to_show.get("creates_new_entry_artifact")
            is False
            and cold_entry_problem_safe_to_show.get("exports_private_paths") is False
            and cold_entry_problem_safe_to_show.get("exports_provider_payloads")
            is False
            and cold_entry_problem_safe_to_show.get("claims_release_or_hosting")
            is False
            and cold_entry_problem_safe_to_show.get("claims_reader_success") is False
            and cold_entry_problem_map.get("authority")
            == "problem_shape_map_not_strategy_or_release_authority"
        ),
        "evidence_count_frame": (
            payload.get("evidence_count_frame", {}).get("interpretation")
            == "accounting_not_maturity_score"
            and payload.get("evidence_count_frame", {}).get("legend_ref")
            == EVIDENCE_CLASS_REGISTRY_REF
        ),
        "evidence_class_legend": (
            isinstance(evidence_class_legend, dict)
            and evidence_class_legend.get("source_ref")
            == EVIDENCE_CLASS_REGISTRY_REF
            and evidence_class_legend.get("interpretation")
            == "claim_boundary_legend_not_score"
            and evidence_class_legend.get("missing_profiles") == []
            and legend_ids == set(EVIDENCE_CLASS_DISPLAY_ORDER)
            and all(
                isinstance(row, dict)
                and isinstance(row.get("claim_ceiling"), str)
                and bool(row.get("claim_ceiling"))
                and isinstance(row.get("evaluator_basis"), str)
                and bool(row.get("evaluator_basis"))
                for row in legend_rows
            )
        ),
        "comparison_frame": (
            payload.get("comparison_frame", {}).get("purpose")
            == "make_rigor_visible_without_claim_inflation"
        ),
        "discipline_comparison_strip": (
            isinstance(discipline_comparison_strip, dict)
            and discipline_comparison_strip.get("schema_version")
            == "microcosm_discipline_comparison_strip_v1"
            and discipline_comparison_strip.get("purpose")
            == "make_microcosm_rigor_visible_as_operational_differences"
            and "not as superiority, benchmark, or maturity claims"
            in discipline_comparison_strip.get("strip_rule", "")
            and discipline_comparison_ids
            == {
                "failure_modes_declared",
                "evidence_counts_contextualized",
                "body_copy_boundaries",
                "reader_branch_authority_shared",
                "local_behavior_before_claims",
            }
            and all(
                isinstance(row, dict)
                and isinstance(row.get("ordinary_entry_pattern"), str)
                and bool(row.get("ordinary_entry_pattern"))
                and isinstance(row.get("microcosm_discipline"), str)
                and bool(row.get("microcosm_discipline"))
                and isinstance(row.get("visible_check_surface"), str)
                and bool(row.get("visible_check_surface"))
                and isinstance(row.get("reader_rule"), str)
                and bool(row.get("reader_rule"))
                and isinstance(row.get("not_claim"), str)
                and bool(row.get("not_claim"))
                for row in discipline_comparison_rows
            )
            and discipline_comparison_safe_to_show.get(
                "uses_existing_first_screen_packets"
            )
            is True
            and discipline_comparison_safe_to_show.get("exports_private_paths")
            is False
            and discipline_comparison_safe_to_show.get("exports_provider_payloads")
            is False
            and discipline_comparison_safe_to_show.get("claims_external_benchmark")
            is False
            and discipline_comparison_safe_to_show.get("claims_superiority") is False
            and discipline_comparison_safe_to_show.get("claims_release_or_hosting")
            is False
            and discipline_comparison_safe_to_show.get(
                "claims_whole_system_correctness"
            )
            is False
            and discipline_comparison_strip.get("authority")
            == "comparison_strip_not_benchmark_or_superiority_claim"
        ),
        "doctrine_effect_frame": (
            isinstance(doctrine_effect_frame, dict)
            and doctrine_effect_frame.get("purpose")
            == "show_doctrine_as_mistake_prevention_not_ceremony"
            and doctrine_handles
            == {
                "CONSTITUTION",
                "AXIOMS",
                "PRINCIPLES",
                "CONCEPTS",
                "MECHANISMS",
                "ANTI_PRINCIPLES",
            }
            and all(
                isinstance(row, dict)
                and isinstance(row.get("prevents"), str)
                and bool(row.get("prevents"))
                and isinstance(row.get("visible_effect"), str)
                and bool(row.get("visible_effect"))
                and isinstance(row.get("first_screen_surface"), str)
                and bool(row.get("first_screen_surface"))
                for row in doctrine_effect_rows
            )
        ),
        "readme_entry_contract": (
            isinstance(readme_entry_contract, dict)
            and readme_entry_contract.get("purpose")
            == "make_package_backed_first_screen_card_the_readme_entry_surface"
            and readme_entry_contract.get("inventory_policy")
            == "quickstart_command_inventory_is_a_drilldown_after_the_first_screen_card"
            and readme_entry_contract.get("authority")
            == "documentation_order_contract_not_runtime_proof"
            and (
                "README.md::Choose Your First Screen",
                "README.md::Try It On Your Repo",
            )
            in readme_order_pairs
            and (human_first_command, shared_first_command) in readme_order_pairs
            and (
                shared_first_command,
                f"microcosm first-screen {payload.get('project_label', '<project>')}",
            )
            in readme_order_pairs
            and ("reader_route_menu", "quickstart_command_inventory")
            in readme_order_pairs
            and ("reader_routes", "quickstart_command_inventory") in readme_order_pairs
            and (
                "first_viewport_manifest",
                "quickstart_command_inventory",
            )
            in readme_order_pairs
            and all(
                isinstance(row, dict)
                and isinstance(row.get("reason"), str)
                and bool(row.get("reason"))
                for row in readme_order_rows
            )
        ),
        "entry_surface_contract": (
            payload.get("entry_surface_contract", {}).get("shared_behavior_surface")
            == payload.get("shared_first_command")
        ),
        "scale_frame": (
            bool(scale_frame.get("scale_handles"))
            and scale_frame.get("count_interpretation")
            == "receipt_backed_handles_not_scores"
            and all(
                _positive_count(scale_counts.get(required_count))
                for required_count in (
                    "implemented_organs",
                    "public_standards",
                    "mapped_organs",
                    "source_open_materials",
                )
            )
        ),
        "runnable_structural_join": bool(
            payload.get("runnable_structural_join", {}).get("join_rule")
        ),
        "state_write_boundary": (
            state_write_boundary.get("this_card_writes_microcosm_state") is False
            and state_write_boundary.get("shared_first_command_writes_state") is True
            and state_write_boundary.get("behavioral_proof_command")
            == payload.get("shared_first_command")
            and state_write_boundary.get("front_door_status_ref")
            == f"{payload.get('shared_first_command')}::front_door_status"
        ),
        "observatory_landing_frame": (
            observatory_landing_frame.get("human_first_command")
            == payload.get("human_first_command")
            and observatory_landing_frame.get("text_projection_command")
            == payload.get("human_first_command")
            and observatory_landing_frame.get("shared_first_command")
            == payload.get("shared_first_command")
            and observatory_landing_frame.get("behavioral_proof_command")
            == payload.get("shared_first_command")
            and observatory_landing_frame.get("serve_command")
            == _observatory_serve_command(str(payload.get("project_label")))
            and observatory_landing_frame.get("bounded_validation_command")
            == _bounded_observatory_serve_command(str(payload.get("project_label")))
            and observatory_landing_frame.get("bounded_validation_request_count") == 6
            and observatory_landing_frame.get("browser_landing_reuse", {}).get(
                "serve_command"
            )
            == _observatory_serve_command(str(payload.get("project_label")))
            and observatory_landing_frame.get("browser_landing_reuse", {}).get(
                "bounded_validation_command"
            )
            == _bounded_observatory_serve_command(str(payload.get("project_label")))
            and observatory_endpoints == OBSERVATORY_LANDING_ENDPOINTS
            and observatory_landing_frame.get("browser_landing_reuse", {}).get(
                "authority"
            )
            == "browser_projection_over_same_card_not_json_first_lens_inventory"
            and all(
                handle in required_visible_handles
                for handle in (
                    "human_first_command",
                    "text_projection",
                    "shared_first_command",
                    "behavioral_proof_command",
                    "serve_command",
                    "bounded_validation_command",
                    "reader_route_ids",
                    "reader_route_menu",
                    "reader_landing_packets",
                    "behavior_proof_packet",
                    "first_run_ladder",
                    "first_viewport_manifest",
                    "local_state_receipt_trail",
                    "first_contact_surface_refs",
                    "overclaim_tripwire_matrix",
                    "discipline_comparison_strip",
                    "reader_exit_criteria",
                    "video_storyboard_packet",
                    "artifact_fit_matrix",
                    "cold_entry_problem_map",
                    "public_scale_counts",
                    "evidence_class_legend",
                    "doctrine_effect_frame",
                    "authority_ceiling",
                    "omission_receipt",
                )
            )
        ),
        "authority_ceiling": all(
            authority_ceiling.get(key) is False for key in DENIED_AUTHORITY_KEYS
        ),
        "omission_receipt": bool(payload.get("omission_receipt", {}).get("drilldown")),
        "workingness_drilldown": "microcosm workingness" in drilldown_text,
    }


def _state_write_boundary(project_label: str) -> dict[str, Any]:
    shared_first_command = f"microcosm tour --card {project_label}"
    return {
        "schema_version": "microcosm_first_screen_state_write_boundary_v1",
        "this_card_writes_microcosm_state": False,
        "this_card_status_scope": "composition_contract_only_not_local_run_result",
        "shared_first_command": shared_first_command,
        "shared_first_command_writes_state": True,
        "state_dir": ".microcosm",
        "behavioral_proof_command": shared_first_command,
        "front_door_status_ref": f"{shared_first_command}::front_door_status",
        "reader_action": (
            "Run the shared first command to write .microcosm state and read "
            "front_door_status before treating the first screen as behavior."
        ),
        "safe_to_show": {
            "source_files_mutated": False,
            "provider_calls_authorized": False,
            "release_or_hosting_authorized": False,
            "proof_correctness_claim": False,
        },
    }


def first_screen_composition_card(
    root: Path = MICROCOSM_ROOT,
    *,
    project_label: str = "<project>",
) -> dict[str, Any]:
    root = Path(root)
    standard = _load_standard(root)
    payload: dict[str, Any] = {
        "schema_version": "microcosm_first_screen_composition_card_v1",
        "project_label": project_label,
        "composition_root_id": standard["kind_id"],
        "source_standard_ref": str(STANDARD_REF),
        "human_first_command": f"microcosm hello {project_label}",
        "shared_first_command": f"microcosm tour --card {project_label}",
        "text_projection": {
            "command": f"microcosm hello {project_label}",
            "writes_microcosm_state": False,
            "behavioral_proof_command": f"microcosm tour --card {project_label}",
            "authority": "terminal_text_projection_only_not_behavior_proof",
            "reader_rule": (
                "Use this command to view the first-screen card; run the "
                "behavior proof command to write .microcosm state."
            ),
        },
        "reader_routes": _reader_routes(project_label),
        "reader_route_menu": _reader_route_menu(project_label),
        "reader_landing_packets": _reader_landing_packets(project_label),
        "behavior_proof_packet": _behavior_proof_packet(project_label),
        "first_run_ladder": _first_run_ladder(project_label),
        "first_viewport_manifest": _first_viewport_manifest(project_label),
        "local_state_receipt_trail": _local_state_receipt_trail(project_label),
        "first_contact_surface_refs": _first_contact_surface_refs(project_label),
        "overclaim_tripwire_matrix": _overclaim_tripwire_matrix(project_label),
        "reader_exit_criteria": _reader_exit_criteria(project_label),
        "video_storyboard_packet": _video_storyboard_packet(project_label),
        "artifact_fit_matrix": _artifact_fit_matrix(project_label),
        "cold_entry_problem_map": _cold_entry_problem_map(project_label),
        "evidence_count_frame": _evidence_count_frame(),
        "evidence_class_legend": _evidence_class_legend(root),
        "comparison_frame": _comparison_frame(),
        "discipline_comparison_strip": _discipline_comparison_strip(project_label),
        "doctrine_effect_frame": _doctrine_effect_frame(),
        "readme_entry_contract": _readme_entry_contract(project_label),
        "entry_surface_contract": _entry_surface_contract(project_label),
        "scale_frame": _scale_frame(root),
        "runnable_structural_join": _runnable_structural_join(project_label),
        "state_write_boundary": _state_write_boundary(project_label),
        "observatory_landing_frame": _observatory_landing_frame(project_label),
        "drilldowns": _drilldowns(project_label),
        "omission_receipt": standard["omission_receipt"],
        "authority_ceiling": standard["authority_ceiling"],
        "anti_claim": standard["anti_claim"],
        "public_private_boundary": {
            "allowed_public_inputs": standard["public_private_boundary"][
                "allowed_public_inputs"
            ],
            "forbidden_public_inputs": standard["public_private_boundary"][
                "forbidden_public_inputs"
            ],
        },
        "validator_id": standard["validator_contract"]["validator_id"],
    }
    checks = _validation_checks(payload)
    standard_scan = _standard_backed_first_screen_scan(
        payload,
        standard,
        set(checks),
    )
    payload["standard_backed_first_screen_scan"] = standard_scan
    checks["standard_backed_first_screen_scan"] = standard_scan["status"] == "pass"
    payload["validation"] = {
        "status": "pass" if all(checks.values()) else "blocked",
        "checks": checks,
    }
    payload["status"] = payload["validation"]["status"]
    return payload


def _compact_reader_routes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    route_menu = payload.get("reader_route_menu", {})
    routes = route_menu.get("routes", []) if isinstance(route_menu, dict) else []
    compact_routes: list[dict[str, Any]] = []
    for row in routes:
        if not isinstance(row, dict):
            continue
        compact_routes.append(
            {
                "reader_route_id": row.get("reader_route_id"),
                "label": row.get("label"),
                "terminal_command": row.get("terminal_command"),
                "text_projection_command": row.get("text_projection_command"),
                "first_action": row.get("first_action"),
                "proof_surface": row.get("proof_surface"),
                "exit_check": row.get("exit_check"),
                "not_a_claim": row.get("not_a_claim"),
            }
        )
    return compact_routes


def _compact_first_run_steps(payload: dict[str, Any]) -> list[dict[str, Any]]:
    ladder = payload.get("first_run_ladder", {})
    steps = ladder.get("steps", []) if isinstance(ladder, dict) else []
    compact_steps: list[dict[str, Any]] = []
    for row in steps:
        if not isinstance(row, dict):
            continue
        compact_steps.append(
            {
                key: row.get(key)
                for key in (
                    "step_id",
                    "command",
                    "expected_surface",
                    "writes_microcosm_state",
                    "authority",
                )
                if key in row
            }
        )
    return compact_steps


def _compact_scale_counts(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    scale_frame = payload.get("scale_frame", {})
    counts = (
        scale_frame.get("public_scale_counts", {})
        if isinstance(scale_frame, dict)
        else {}
    )
    compact_counts: dict[str, dict[str, Any]] = {}
    for key in (
        "implemented_organs",
        "public_standards",
        "source_open_materials",
    ):
        row = counts.get(key) if isinstance(counts, dict) else None
        if not isinstance(row, dict):
            continue
        compact_counts[key] = {
            "count": row.get("count"),
            "read_as": row.get("read_as"),
        }
    return compact_counts


def _compact_validation(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload.get("validation", {})
    checks = validation.get("checks", {}) if isinstance(validation, dict) else {}
    failed = [
        check_id
        for check_id, passed in checks.items()
        if passed is not True
    ] if isinstance(checks, dict) else []
    return {
        "source_status": validation.get("status") if isinstance(validation, dict) else None,
        "validator_id": payload.get("validator_id"),
        "checks_passed_count": len(checks) - len(failed) if isinstance(checks, dict) else 0,
        "check_count": len(checks) if isinstance(checks, dict) else 0,
        "failed_checks": failed,
    }


def first_screen_compact_card(payload: dict[str, Any]) -> dict[str, Any]:
    project_label = str(payload.get("project_label") or "<project>")
    route_menu = payload.get("reader_route_menu", {})
    state_boundary = payload.get("state_write_boundary", {})
    full_json_command = f"microcosm first-screen --full {project_label}"
    text_projection_command = f"microcosm first-screen --format text {project_label}"
    return {
        "schema_version": "microcosm_first_screen_compact_card_v1",
        "compact_projection_of": payload.get("schema_version"),
        "status": payload.get("status"),
        "project_label": project_label,
        "human_first_command": payload.get("human_first_command"),
        "shared_first_command": payload.get("shared_first_command"),
        "output_policy": {
            "default_json_is_first_screen_projection": True,
            "stdout_budget_chars": COMPACT_JSON_CARD_MAX_CHARS,
            "full_contract_command": full_json_command,
            "text_projection_command": text_projection_command,
            "full_contract_preserved": True,
        },
        "reader_route_menu": {
            "default_command": route_menu.get("default_command")
            if isinstance(route_menu, dict)
            else None,
            "shared_behavior_command": route_menu.get("shared_behavior_command")
            if isinstance(route_menu, dict)
            else None,
            "machine_card_command": f"microcosm first-screen {project_label}",
            "routes": _compact_reader_routes(payload),
        },
        "first_run_ladder": {
            "purpose": "show_the_first_runnable_path_before_deep_contract_json",
            "steps": _compact_first_run_steps(payload),
        },
        "evidence_context": {
            "scale_counts": _compact_scale_counts(payload),
            "evidence_class_registry_ref": EVIDENCE_CLASS_REGISTRY_REF,
            "counts_are_authority": False,
        },
        "state_write_boundary": {
            "this_card_writes_microcosm_state": False,
            "behavioral_proof_command": state_boundary.get(
                "behavioral_proof_command"
            ) if isinstance(state_boundary, dict) else None,
            "front_door_status_ref": state_boundary.get("front_door_status_ref")
            if isinstance(state_boundary, dict)
            else None,
            "source_files_mutated_by_first_screen": False,
        },
        "authority_ceiling": payload.get("authority_ceiling"),
        "anti_claim": payload.get("anti_claim"),
        "public_private_boundary": payload.get("public_private_boundary"),
        "drilldowns": {
            "full_json": full_json_command,
            "text_projection": text_projection_command,
            "behavior_proof": payload.get("shared_first_command"),
            "observatory": _bounded_observatory_serve_command(project_label),
            "route_contract": "paper_modules/cold_reader_route_map.md",
        },
        "omission_receipt": {
            "summary_first_projection": True,
            "omitted_full_contract_keys": [
                "video_storyboard_packet",
                "artifact_fit_matrix",
                "cold_entry_problem_map",
                "discipline_comparison_strip",
                "doctrine_effect_frame",
            ],
            "drilldown": payload.get("omission_receipt", {}).get("drilldown")
            if isinstance(payload.get("omission_receipt"), dict)
            else None,
            "full_contract_command": full_json_command,
        },
        "validation": _compact_validation(payload),
    }


def _reader_route_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(route.get("reader_route_id")): route
        for route in payload.get("reader_routes", [])
        if isinstance(route, dict)
    }


def _reader_packet_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    landing_packets = payload.get("reader_landing_packets", {})
    if not isinstance(landing_packets, dict):
        return {}
    return {
        str(packet.get("reader_route_id")): packet
        for packet in landing_packets.get("packets", [])
        if isinstance(packet, dict)
    }


def _reader_menu_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    route_menu = payload.get("reader_route_menu", {})
    if not isinstance(route_menu, dict):
        return {}
    return {
        str(row.get("reader_route_id")): row
        for row in route_menu.get("routes", [])
        if isinstance(row, dict)
    }


def _reader_branch_lines(
    route_by_id: dict[str, dict[str, Any]],
    packet_by_id: dict[str, dict[str, Any]],
    menu_by_id: dict[str, dict[str, Any]],
    reader_id: str,
) -> list[str]:
    if reader_id == "all":
        return [
            "Reader branches:",
            *[
                (
                    f"  {READER_LABELS[route_id]}: "
                    f"{menu_by_id[route_id]['terminal_command']} | Proof: "
                    f"{packet_by_id[route_id]['proof_surface']}"
                )
                for route_id in READER_ROUTE_IDS
            ],
        ]

    route = route_by_id[reader_id]
    packet = packet_by_id[reader_id]
    menu = menu_by_id[reader_id]
    return [
        f"Reader branch: {READER_LABELS[reader_id]}",
        (
            f"  Command: {menu['terminal_command']} | "
            f"Text card: {menu['text_projection_command']}"
        ),
        f"  Question: {route['first_question']}",
        f"  First action: {packet['first_action']}",
        f"  Proof: {packet['proof_surface']}",
        f"  Success: {packet['success_criterion']}",
    ]


def _scale_summary_line(payload: dict[str, Any]) -> str:
    counts = payload["scale_frame"]["public_scale_counts"]
    organs = counts["implemented_organs"]["count"]
    standards = counts["public_standards"]["count"]
    source_open_materials = counts["source_open_materials"]["count"]
    return (
        f"  Public handles: {organs} organ-registry rows, {standards} "
        f"standard-registry rows, {source_open_materials} fixture/workingness "
        "source-open material handles."
    )


def _evidence_class_summary_line(payload: dict[str, Any]) -> str:
    class_ids = {
        str(row.get("evidence_class"))
        for row in payload.get("evidence_class_legend", {}).get("classes", [])
        if isinstance(row, dict)
    }
    if set(EVIDENCE_CLASS_DISPLAY_ORDER).issubset(class_ids):
        return (
            "  Evidence classes: body import, subprocess witness, semantic validator, "
            "algorithmic projection, fixture smoke/schema."
        )
    return "  Evidence classes: see core/organ_evidence_classes.json for claim ceilings."


def first_screen_text_card(payload: dict[str, Any], *, reader_id: str = "all") -> str:
    if reader_id not in TEXT_READER_CHOICES:
        raise ValueError(f"unknown first-screen reader route: {reader_id}")
    route_by_id = _reader_route_map(payload)
    packet_by_id = _reader_packet_map(payload)
    menu_by_id = _reader_menu_map(payload)
    human_first_command = payload.get(
        "human_first_command", "microcosm hello <project>"
    )
    lines = [
        "Microcosm first screen",
        (
            f"Open card: {human_first_command} | "
            f"First run: {payload['shared_first_command']}"
        ),
        (
            f"Check state: microcosm status --card {payload['project_label']} | "
            "Trail: catalog -> routes -> events -> evidence -> graph."
        ),
        "",
        "What it is:",
        "  A local evidence router; doctrine names boundaries; exit when you can choose a drilldown without the command inventory.",
        "",
        "Why the counts are honest:",
        _scale_summary_line(payload),
        "  Counts are receipt-backed handles from registries and fixture manifests; status --card shows the stricter body-import floor.",
        _evidence_class_summary_line(payload),
        "  Behavior proof after tour --card: front_door_status=pass, selected_route_id, state refs, source_files_mutated=false.",
        "",
        *_reader_branch_lines(route_by_id, packet_by_id, menu_by_id, reader_id),
        "",
        "Runnable-to-structural join:",
        "  This card is the map; the first run writes .microcosm and exercises the larger public substrate:",
        "  concept/mechanism standards, receipts, authority boundaries, workingness, route maps, and observatory views.",
        "",
        "Drilldowns:",
        (
            "  observatory: "
            f"{_bounded_observatory_serve_command(str(payload['project_label']))} "
            "-> /project/first-screen -> /project/observatory-card; artifact fit: "
            "terminal/README/browser/JSON/video project this card; problem map binds the gaps."
        ),
        "  authority/workingness: microcosm authority --card / microcosm workingness --card",
        f"  route/contract: paper_modules/cold_reader_route_map.md / {payload['source_standard_ref']}",
        "",
        "Authority ceiling: No release, hosted publication, provider-call, source-mutation, private-equivalence, score-progress, or whole-system-correctness authority.",
        "",
        f"Omission receipt: deeper evidence remains behind {payload['omission_receipt']['drilldown']}.",
    ]
    if len(lines) > TEXT_CARD_MAX_LINES:
        raise ValueError("first-screen text card exceeded its line budget")
    return "\n".join(lines) + "\n"
