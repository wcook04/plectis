from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = MICROCOSM_ROOT / "scripts/first_screen_composition_card.py"
EXPECTED_READER_ROUTE_IDS = {
    "public_github_visitor",
    "safety_evals_engineer",
    "hiring_reviewer",
    "peer_developer",
    "domain_specialist",
    "type_a_agent",
}
EXPECTED_READER_ROUTE_ID_LIST = [
    "public_github_visitor",
    "safety_evals_engineer",
    "hiring_reviewer",
    "peer_developer",
    "domain_specialist",
    "type_a_agent",
]


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("first_screen_composition_card", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def _fixture_manifest_source_open_counts() -> tuple[int, int]:
    registry = json.loads((MICROCOSM_ROOT / "core/organ_registry.json").read_text())
    rows = registry.get("implemented_organs", [])
    assert isinstance(rows, list)

    material_count = 0
    rows_with_imports = 0
    for row in rows:
        assert isinstance(row, dict)
        organ_id = row["organ_id"]
        manifest_path = (
            MICROCOSM_ROOT
            / "core/fixture_manifests"
            / f"{organ_id}.fixture_manifest.json"
        )
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text())
        body_imports = manifest.get("source_open_body_imports")
        if isinstance(body_imports, dict):
            raw_count = body_imports.get("body_material_count")
            material_ids = body_imports.get("body_material_ids")
            organ_count = (
                raw_count
                if isinstance(raw_count, int) and not isinstance(raw_count, bool)
                else len(material_ids)
                if isinstance(material_ids, list)
                else 0
            )
        else:
            body_status = manifest.get("body_material_status")
            raw_count = manifest.get("body_copied_material_count")
            organ_count = (
                raw_count
                if body_status
                and isinstance(raw_count, int)
                and not isinstance(raw_count, bool)
                else 0
            )
        if organ_count > 0:
            material_count += organ_count
            rows_with_imports += 1
    return material_count, rows_with_imports


def test_first_screen_composition_card_is_public_one_screen_contract() -> None:
    module = _load_module()

    card = module.first_screen_composition_card(MICROCOSM_ROOT, project_label="<project>")
    route_ids = {route["reader_route_id"] for route in card["reader_routes"]}

    assert card["status"] == "pass"
    assert card["composition_root_id"] == "first_screen_composition_root"
    assert (
        card["source_standard_ref"]
        == "standards/std_microcosm_first_screen_composition_root.json"
    )
    pre_install_probe = card["pre_install_probe"]
    assert pre_install_probe["command"] == "./bootstrap.sh"
    assert pre_install_probe["dry_run_command"] == "./bootstrap.sh --dry-run"
    assert pre_install_probe["receipt_ref"] == ".microcosm/cold_clone_probe.json"
    assert pre_install_probe["runs_before_install"] is True
    assert pre_install_probe["writes_ignored_local_state"] is True
    assert pre_install_probe["safe_to_show"]["release_authorized"] is False
    assert card["human_first_command"] == "microcosm hello <project>"
    assert card["shared_first_command"] == "microcosm tour --card <project>"
    text_projection = card["text_projection"]
    assert text_projection == {
        "command": card["human_first_command"],
        "pre_install_probe_command": "./bootstrap.sh",
        "pre_install_probe_receipt": ".microcosm/cold_clone_probe.json",
        "writes_microcosm_state": False,
        "behavioral_proof_command": card["shared_first_command"],
        "source_checkout_command": (
            "PYTHONPATH=src python3 -m microcosm_core hello <project>"
        ),
        "source_checkout_behavioral_proof_command": (
            "PYTHONPATH=src python3 -m microcosm_core tour --card <project>"
        ),
        "authority": "terminal_text_projection_only_not_behavior_proof",
        "reader_rule": (
            "Use this command to view the first-screen card; run the "
            "behavior proof command to write .microcosm state."
        ),
    }
    assert route_ids == EXPECTED_READER_ROUTE_IDS
    reader_landing_packets = card["reader_landing_packets"]
    packet_by_id = {
        packet["reader_route_id"]: packet
        for packet in reader_landing_packets["packets"]
    }
    reader_route_menu = card["reader_route_menu"]
    menu_by_id = {
        row["reader_route_id"]: row for row in reader_route_menu["routes"]
    }
    assert reader_route_menu["schema_version"] == (
        "microcosm_reader_route_menu_v1"
    )
    assert reader_route_menu["purpose"] == (
        "make_reader_typed_first_screens_copyable_without_separate_entry_"
        "artifacts"
    )
    assert "shared map and behavior proof first" in reader_route_menu["menu_rule"]
    assert reader_route_menu["default_command"] == card["human_first_command"]
    assert reader_route_menu["shared_behavior_command"] == (
        card["shared_first_command"]
    )
    assert reader_route_menu["machine_card_command"] == (
        "microcosm first-screen --card <project>"
    )
    assert reader_route_menu["default_json_command"] == (
        "microcosm first-screen <project>"
    )
    assert set(menu_by_id) == route_ids
    assert menu_by_id["safety_evals_engineer"]["terminal_command"] == (
        "microcosm hello --reader safety_evals_engineer <project>"
    )
    assert menu_by_id["safety_evals_engineer"]["text_projection_command"] == (
        "microcosm first-screen --format text --reader safety_evals_engineer <project>"
    )
    assert menu_by_id["safety_evals_engineer"]["not_a_claim"] == (
        "safety_evaluation_complete"
    )
    assert menu_by_id["public_github_visitor"]["terminal_command"] == (
        "microcosm hello --reader public_github_visitor <project>"
    )
    assert menu_by_id["public_github_visitor"]["text_projection_command"] == (
        "microcosm first-screen --format text --reader public_github_visitor <project>"
    )
    assert menu_by_id["public_github_visitor"]["not_a_claim"] == (
        "publication_or_reader_success_ready"
    )
    assert menu_by_id["public_github_visitor"]["first_action"] == (
        "Run `microcosm tour --card <project>` after this card."
    )
    assert menu_by_id["safety_evals_engineer"]["first_action"] == (
        "Run `microcosm tour --card <project>` first, then "
        "`microcosm status --card <project>`."
    )
    assert menu_by_id["hiring_reviewer"]["first_action"] == (
        "Run `microcosm legibility-scorecard`, then "
        "`microcosm tour --card <project>`."
    )
    assert menu_by_id["hiring_reviewer"]["proof_surface"] == (
        "`microcosm legibility-scorecard` plus "
        "`microcosm tour --card <project>`"
    )
    assert menu_by_id["domain_specialist"]["terminal_command"] == (
        "microcosm hello --reader domain_specialist <project>"
    )
    assert menu_by_id["domain_specialist"]["text_projection_command"] == (
        "microcosm first-screen --format text --reader domain_specialist <project>"
    )
    assert menu_by_id["domain_specialist"]["first_action"] == (
        "Open `ORGANS.md#find-your-specialty`, then run "
        "`microcosm tour --card <project>`."
    )
    assert menu_by_id["domain_specialist"]["proof_surface"] == (
        "`ORGANS.md#find-your-specialty` plus "
        "`microcosm tour --card <project>`"
    )
    assert menu_by_id["domain_specialist"]["not_a_claim"] == (
        "domain_expertise_or_domain_correctness_complete"
    )
    assert menu_by_id["type_a_agent"]["terminal_command"] == (
        "microcosm hello --reader type_a_agent <project>"
    )
    assert menu_by_id["type_a_agent"]["text_projection_command"] == (
        "microcosm first-screen --format text --reader type_a_agent <project>"
    )
    assert menu_by_id["type_a_agent"]["first_action"] == (
        "Run `microcosm first-screen --card <project>`. "
        "If you need `doctrine_effect_frame`, run "
        "`microcosm first-screen --full <project>` before reading it; then run "
        "`microcosm organ-surface-contract --card --root .`."
    )
    assert menu_by_id["type_a_agent"]["proof_surface"] == (
        "`microcosm organ-surface-contract --card --root .`"
    )
    assert menu_by_id["type_a_agent"]["not_a_claim"] == (
        "agent_autonomy_or_source_mutation_ready"
    )
    assert reader_route_menu["safe_to_show"] == {
        "uses_existing_reader_packets": True,
        "creates_new_entry_artifact": False,
        "creates_reader_specific_claim_ceiling": False,
        "exports_private_paths": False,
        "exports_provider_payloads": False,
        "claims_release_or_hosting": False,
        "claims_reader_success": False,
    }
    assert reader_route_menu["authority"] == (
        "reader_route_menu_not_new_entry_artifact_or_reader_success_authority"
    )
    for row in menu_by_id.values():
        assert row["label"]
        assert " --reader " in row["terminal_command"]
        assert " --reader " in row["text_projection_command"]
        assert row["first_action"]
        assert row["proof_surface"]
        assert row["exit_check"]
        assert row["authority"].startswith("focused_projection_only_not_")
    assert reader_landing_packets["purpose"] == (
        "turn_reader_routes_into_first_action_proof_success_packets"
    )
    assert "same authority ceiling" in reader_landing_packets[
        "shared_authority_rule"
    ]
    assert "one first action" in reader_landing_packets["one_screen_rule"]
    assert set(packet_by_id) == route_ids
    for packet in packet_by_id.values():
        assert packet["first_action"]
        assert packet["proof_surface"]
        assert packet["success_criterion"]
        assert packet["next_drilldown"]
        assert packet["authority"].startswith("inspection_order_only_not_")
    assert packet_by_id["safety_evals_engineer"]["next_drilldown"] == (
        "core/organ_evidence_classes.json"
    )
    assert packet_by_id["public_github_visitor"]["next_drilldown"] == (
        "README.md#first-run"
    )
    assert packet_by_id["public_github_visitor"]["first_action"] == (
        "Run `microcosm tour --card <project>` after this card."
    )
    assert "from the repo root" not in packet_by_id["public_github_visitor"][
        "first_action"
    ]
    assert "release, hosting, and private-data claims" in packet_by_id[
        "public_github_visitor"
    ]["success_criterion"]
    assert "maturity or release readiness" in packet_by_id[
        "safety_evals_engineer"
    ]["success_criterion"]
    assert packet_by_id["hiring_reviewer"]["first_action"] == (
        "Run `microcosm legibility-scorecard`, then "
        "`microcosm tour --card <project>`."
    )
    assert packet_by_id["hiring_reviewer"]["proof_surface"] == (
        "`microcosm legibility-scorecard` plus "
        "`microcosm tour --card <project>`"
    )
    assert "provider calls" in packet_by_id["peer_developer"]["success_criterion"]
    assert packet_by_id["domain_specialist"]["next_drilldown"] == (
        "ORGANS.md#find-your-specialty"
    )
    assert "domain correctness" in packet_by_id["domain_specialist"][
        "success_criterion"
    ]
    assert packet_by_id["type_a_agent"]["next_drilldown"] == (
        "AGENTS.md::Concept And Mechanism Entry"
    )
    assert packet_by_id["type_a_agent"]["proof_surface"] == (
        "`microcosm organ-surface-contract --card --root .`"
    )
    assert "mechanisms from validators/projections" in packet_by_id[
        "type_a_agent"
    ]["success_criterion"]
    behavior_proof_packet = card["behavior_proof_packet"]
    behavior_fields = {
        row["field"]: row for row in behavior_proof_packet["proof_fields"]
    }
    assert behavior_proof_packet["purpose"] == (
        "turn_shared_first_run_into_inspectable_success_conditions"
    )
    assert behavior_proof_packet["command"] == card["shared_first_command"]
    assert behavior_proof_packet["writes_state"] is True
    assert behavior_proof_packet["state_dir"] == ".microcosm"
    assert set(behavior_fields) == {
        "front_door_status.status",
        "selected_route_id",
        "state_inspection",
        "source_files_mutated",
    }
    assert behavior_fields["front_door_status.status"]["success_read"] == "pass"
    assert behavior_fields["source_files_mutated"]["success_read"] is False
    assert "not_release_readiness" in behavior_fields[
        "front_door_status.status"
    ]["reader_rule"]
    assert "not_private_root_equivalence" in behavior_fields[
        "state_inspection"
    ]["reader_rule"]
    assert behavior_proof_packet["authority"] == (
        "local_behavior_receipt_not_release_or_proof_authority"
    )
    assert "not a product, release, proof" in behavior_proof_packet[
        "failure_reading"
    ]
    first_run_ladder = card["first_run_ladder"]
    assert first_run_ladder["pre_install_probe"] == pre_install_probe
    ladder_steps = {row["step_id"]: row for row in first_run_ladder["steps"]}
    assert first_run_ladder["purpose"] == (
        "make_first_screen_run_order_copyable_without_long_quickstart"
    )
    assert "copyable run order" in first_run_ladder["one_screen_rule"]
    assert list(ladder_steps) == [
        "map",
        "behavior_proof",
        "status_confirmation",
        "reader_branch",
    ]
    assert ladder_steps["map"]["command"] == card["human_first_command"]
    assert ladder_steps["map"]["writes_microcosm_state"] is False
    assert ladder_steps["map"]["authority"] == (
        "projection_only_not_behavior_proof"
    )
    assert ladder_steps["behavior_proof"]["command"] == card["shared_first_command"]
    assert ladder_steps["behavior_proof"]["writes_microcosm_state"] is True
    assert "selected_route_id" in ladder_steps["behavior_proof"]["success_read"]
    assert ladder_steps["status_confirmation"]["command"] == (
        "microcosm status --card <project>"
    )
    assert ladder_steps["status_confirmation"]["writes_microcosm_state"] is False
    assert ladder_steps["reader_branch"]["command"] == (
        "choose reader route from reader_route_menu"
    )
    assert first_run_ladder["authority"] == (
        "copyable_run_order_not_quickstart_inventory_or_release_authority"
    )
    first_viewport_manifest = card["first_viewport_manifest"]
    viewport_by_id = {
        row["slot_id"]: row for row in first_viewport_manifest["slots"]
    }
    problem_slot_by_id = {
        row["problem_shape_id"]: row["slot_id"]
        for row in first_viewport_manifest["problem_shape_slot_map"]
    }
    assert first_viewport_manifest["schema_version"] == (
        "microcosm_first_viewport_manifest_v1"
    )
    assert first_viewport_manifest["purpose"] == (
        "make_single_screen_cold_entry_composition_explicit_for_cli_readme_"
        "browser_json_and_video"
    )
    assert "before the long command inventory" in first_viewport_manifest[
        "composition_rule"
    ]
    assert list(viewport_by_id) == [
        "identity",
        "first_run",
        "proof_chain",
        "evidence_context",
        "reader_branch",
        "authority_boundary",
    ]
    assert viewport_by_id["identity"]["first_visible_surface"] == (
        card["human_first_command"]
    )
    assert viewport_by_id["identity"]["proof_surface"] == "authority_ceiling"
    assert viewport_by_id["first_run"]["source_packet"] == "first_run_ladder"
    assert viewport_by_id["first_run"]["first_visible_surface"] == (
        card["shared_first_command"]
    )
    assert viewport_by_id["proof_chain"]["proof_surface"] == (
        "first_contact_surface_refs"
    )
    assert viewport_by_id["evidence_context"]["first_visible_surface"] == (
        "core/organ_evidence_classes.json"
    )
    assert viewport_by_id["reader_branch"]["proof_surface"] == (
        "reader_exit_criteria"
    )
    assert viewport_by_id["reader_branch"]["source_packet"] == (
        "reader_route_menu"
    )
    assert viewport_by_id["reader_branch"]["first_visible_surface"] == (
        "focused reader commands"
    )
    assert viewport_by_id["authority_boundary"]["proof_surface"] == (
        "overclaim_tripwire_matrix"
    )
    assert viewport_by_id["authority_boundary"]["source_packet"] == (
        "discipline_comparison_strip"
    )
    assert viewport_by_id["authority_boundary"]["first_visible_surface"] == (
        "discipline_comparison_strip"
    )
    for row in viewport_by_id.values():
        assert row["viewport_copy"]
        assert "authority_ceiling" in row["must_preserve"]
        assert "anti_claim" in row["must_preserve"]
        assert "omission_receipt" in row["must_preserve"]
        assert "discipline_comparison_strip" in row["must_preserve"]
        assert "release_or_hosting_authority" in row["must_not_claim"]
        assert "provider_call_authority" in row["must_not_claim"]
        assert "private_root_equivalence" in row["must_not_claim"]
        assert "whole_system_correctness" in row["must_not_claim"]
        assert "reader_success" in row["must_not_claim"]
    assert set(problem_slot_by_id) == {
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
    assert problem_slot_by_id["first_thing_best_thing_gap"] == "first_run"
    assert problem_slot_by_id["audience_is_not_one_person"] == "reader_branch"
    assert problem_slot_by_id["honest_numbers_without_context"] == (
        "evidence_context"
    )
    assert problem_slot_by_id["runnable_vs_structural_split"] == "proof_chain"
    assert first_viewport_manifest["consumer_surfaces"] == {
        "terminal": "microcosm hello <project>",
        "readme": "README.md::Choose Your First Screen",
        "browser": (
            "microcosm serve <project> --host 127.0.0.1 --port 8765 "
            "--max-requests 7 -> /"
        ),
        "json": "microcosm first-screen --card <project>",
        "video": "video_storyboard_packet",
    }
    assert first_viewport_manifest["safe_to_show"] == {
        "uses_existing_first_screen_packets": True,
        "creates_new_entry_artifact": False,
        "exports_private_paths": False,
        "exports_provider_payloads": False,
        "claims_release_or_hosting": False,
        "claims_reader_success": False,
    }
    assert first_viewport_manifest["authority"] == (
        "viewport_manifest_not_new_claim_or_renderer_authority"
    )
    local_state_receipt_trail = card["local_state_receipt_trail"]
    local_state_rows = {
        row["surface_id"]: row for row in local_state_receipt_trail["trail"]
    }
    assert local_state_receipt_trail["purpose"] == (
        "show_what_the_first_run_writes_without_expanding_raw_state"
    )
    assert local_state_receipt_trail["producer_command"] == (
        card["shared_first_command"]
    )
    assert local_state_receipt_trail["state_dir"] == ".microcosm"
    assert list(local_state_rows) == [
        "catalog",
        "routes",
        "work_events",
        "evidence_index",
        "graph",
    ]
    assert local_state_rows["catalog"]["state_ref"] == ".microcosm/catalog.json"
    assert local_state_rows["routes"]["state_ref"] == ".microcosm/routes.json"
    assert local_state_rows["work_events"]["state_ref"] == (
        ".microcosm/events.jsonl"
    )
    assert local_state_rows["evidence_index"]["state_ref"] == (
        ".microcosm/evidence/index.json"
    )
    assert local_state_rows["graph"]["state_ref"] == ".microcosm/graph.json"
    for row in local_state_rows.values():
        assert row["reader_read"]
        assert row["not_authority_for"]
    assert "not source mutation" in local_state_receipt_trail["reader_rule"]
    assert local_state_receipt_trail["authority"] == (
        "local_state_receipt_trail_not_private_root_equivalence"
    )
    first_contact_surface_refs = card["first_contact_surface_refs"]
    first_contact_surfaces = first_contact_surface_refs["surfaces"]
    assert first_contact_surface_refs["schema_version"] == (
        "microcosm_first_contact_surface_refs_v1"
    )
    assert first_contact_surface_refs["producer_command"] == (
        card["shared_first_command"]
    )
    assert first_contact_surface_refs["required_surface_ids"] == [
        "route",
        "work",
        "events",
        "evidence",
        "graph",
        "observatory",
        "proof_lab",
        "status",
    ]
    assert set(first_contact_surfaces) == set(
        first_contact_surface_refs["required_surface_ids"]
    )
    assert first_contact_surfaces["route"]["state_ref"] == ".microcosm/routes.json"
    assert first_contact_surfaces["work"]["state_ref"] == (
        ".microcosm/work_items.json"
    )
    assert first_contact_surfaces["events"]["state_ref"] == (
        ".microcosm/events.jsonl"
    )
    assert first_contact_surfaces["evidence"]["state_ref"] == ".microcosm/evidence/"
    assert first_contact_surfaces["evidence"]["body_text_exported"] is False
    assert first_contact_surfaces["graph"]["state_ref"] == ".microcosm/graph.json"
    assert first_contact_surfaces["observatory"]["command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765"
    )
    assert first_contact_surfaces["observatory"]["bounded_validation_command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
    )
    assert first_contact_surfaces["observatory"]["compact_endpoint"] == (
        "/project/observatory-card"
    )
    assert first_contact_surfaces["proof_lab"]["command"] == (
        "microcosm proof-lab --out /tmp/microcosm-proof-lab"
    )
    assert first_contact_surfaces["proof_lab"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert first_contact_surfaces["status"]["body_import_floor_ref"] == (
        "microcosm status --card <project>::front_door.source_open_body_import_floor"
    )
    assert first_contact_surfaces["status"]["workingness_command"] == (
        "microcosm workingness --card"
    )
    assert first_contact_surface_refs["safe_to_show"] == {
        "project_local_state_refs_visible": True,
        "receipt_refs_visible": True,
        "body_text_exported": False,
        "source_files_mutated": False,
        "provider_calls_authorized": False,
        "release_authorized": False,
        "proof_correctness_claim": False,
    }
    assert first_contact_surface_refs["authority"] == (
        "first_contact_surface_map_only_not_source_release_provider_"
        "mutation_or_proof_authority"
    )
    overclaim_tripwire_matrix = card["overclaim_tripwire_matrix"]
    tripwire_by_id = {
        row["tripwire_id"]: row for row in overclaim_tripwire_matrix["rows"]
    }
    assert overclaim_tripwire_matrix["purpose"] == (
        "translate_common_cold_reader_overclaims_into_valid_bounded_reads"
    )
    assert overclaim_tripwire_matrix["shared_first_command"] == (
        card["shared_first_command"]
    )
    assert overclaim_tripwire_matrix["authority"] == (
        "overclaim_tripwire_not_marketing_or_release_authority"
    )
    assert set(tripwire_by_id) == {
        "release_ready",
        "organ_count_whole_system",
        "low_body_import_count_fake",
        "local_state_private_root_equivalence",
        "observatory_hosted_release",
    }
    assert "release-ready" in tripwire_by_id["release_ready"]["overclaim"]
    assert tripwire_by_id["release_ready"]["check_surface"] == (
        "microcosm status --card <project>"
    )
    assert "Forty-seven organs" in tripwire_by_id[
        "organ_count_whole_system"
    ]["overclaim"]
    assert tripwire_by_id["organ_count_whole_system"]["check_surface"] == (
        "microcosm workingness"
    )
    assert "low verified body-import count" in tripwire_by_id[
        "low_body_import_count_fake"
    ]["overclaim"]
    assert tripwire_by_id["low_body_import_count_fake"]["check_surface"] == (
        "core/organ_evidence_classes.json"
    )
    assert tripwire_by_id["local_state_private_root_equivalence"][
        "check_surface"
    ] == ".microcosm/"
    assert tripwire_by_id["observatory_hosted_release"]["check_surface"] == (
        "/project/first-screen"
    )
    for row in tripwire_by_id.values():
        assert row["valid_read"]
        assert row["reader_rule"]
    reader_exit_criteria = card["reader_exit_criteria"]
    exit_by_id = {
        row["reader_route_id"]: row for row in reader_exit_criteria["criteria"]
    }
    assert reader_exit_criteria["purpose"] == (
        "tell_cold_readers_when_the_first_screen_has_done_its_job"
    )
    assert reader_exit_criteria["shared_first_command"] == (
        card["shared_first_command"]
    )
    assert "long command inventory" in reader_exit_criteria["shared_stop_rule"]
    assert reader_exit_criteria["authority"] == (
        "exit_criteria_not_reader_success_or_release_authority"
    )
    assert set(exit_by_id) == route_ids
    assert exit_by_id["public_github_visitor"]["next_if_not_met"] == (
        "microcosm hello <project>"
    )
    assert exit_by_id["safety_evals_engineer"]["next_if_not_met"] == (
        "microcosm status --card <project>"
    )
    assert exit_by_id["hiring_reviewer"]["next_if_not_met"] == (
        "microcosm legibility-scorecard"
    )
    assert exit_by_id["peer_developer"]["next_if_not_met"] == (
        "microcosm observe --card <project>"
    )
    assert exit_by_id["domain_specialist"]["next_if_not_met"] == (
        "ORGANS.md#find-your-specialty"
    )
    assert exit_by_id["type_a_agent"]["next_if_not_met"] == (
        "microcosm organ-surface-contract --card --root ."
    )
    assert exit_by_id["safety_evals_engineer"]["not_a_claim"] == (
        "safety_evaluation_complete"
    )
    assert exit_by_id["hiring_reviewer"]["not_a_claim"] == (
        "candidate_assessed_or_interview_ready"
    )
    assert exit_by_id["public_github_visitor"]["not_a_claim"] == (
        "publication_or_reader_success_ready"
    )
    assert exit_by_id["peer_developer"]["not_a_claim"] == "integration_complete"
    assert exit_by_id["domain_specialist"]["not_a_claim"] == (
        "domain_expertise_or_domain_correctness_complete"
    )
    assert exit_by_id["type_a_agent"]["not_a_claim"] == (
        "agent_autonomy_or_source_mutation_ready"
    )
    for row in exit_by_id.values():
        assert row["exit_when"]
    video_storyboard_packet = card["video_storyboard_packet"]
    storyboard_by_id = {
        row["beat_id"]: row for row in video_storyboard_packet["beats"]
    }
    assert video_storyboard_packet["schema_version"] == (
        "microcosm_video_storyboard_packet_v1"
    )
    assert video_storyboard_packet["purpose"] == (
        "make_a_sixty_second_cold_entry_artifact_without_new_claims"
    )
    assert "video, screenshot board, or browser reveal" in video_storyboard_packet[
        "artifact_rule"
    ]
    assert video_storyboard_packet["allowed_artifact_forms"] == [
        "terminal_capture",
        "browser_walkthrough",
        "static_reveal_board",
        "short_video",
    ]
    assert video_storyboard_packet["source_projection"] == (
        "microcosm_core.first_screen_composition.first_screen_composition_card"
    )
    assert video_storyboard_packet["first_run_command"] == (
        card["shared_first_command"]
    )
    assert video_storyboard_packet["bounded_observatory_command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
    )
    assert set(storyboard_by_id) == {
        "open_map",
        "prove_local_behavior",
        "show_route_chain",
        "frame_evidence_counts",
        "open_authority_boundary",
        "choose_reader_branch",
    }
    assert sum(row["timebox_seconds"] for row in storyboard_by_id.values()) <= 60
    assert storyboard_by_id["open_map"]["visible_surface"] == (
        "microcosm hello <project>"
    )
    assert storyboard_by_id["prove_local_behavior"]["visible_surface"] == (
        card["shared_first_command"]
    )
    assert storyboard_by_id["show_route_chain"]["proof_ref"] == (
        ".microcosm/events.jsonl + .microcosm/graph.json"
    )
    assert storyboard_by_id["frame_evidence_counts"]["proof_ref"] == (
        "core/organ_evidence_classes.json"
    )
    assert storyboard_by_id["choose_reader_branch"]["proof_ref"] == (
        "reader_exit_criteria"
    )
    assert video_storyboard_packet["safe_to_show"] == {
        "uses_public_first_screen_card": True,
        "uses_localhost_read_model": True,
        "exports_private_paths": False,
        "exports_provider_payloads": False,
        "uses_live_operator_or_browser_session": False,
        "claims_release_or_hosting": False,
        "claims_reader_success": False,
    }
    assert "not a release artifact" in video_storyboard_packet["anti_claim"]
    assert video_storyboard_packet["authority"] == (
        "presentation_plan_over_existing_first_screen_contract_only"
    )
    artifact_fit_matrix = card["artifact_fit_matrix"]
    artifact_fit_by_id = {
        row["surface_id"]: row for row in artifact_fit_matrix["rows"]
    }
    assert artifact_fit_matrix["schema_version"] == (
        "microcosm_first_screen_artifact_fit_matrix_v1"
    )
    assert artifact_fit_matrix["purpose"] == (
        "keep_all_cold_entry_forms_bound_to_one_source_card"
    )
    assert artifact_fit_matrix["source_of_truth"] == (
        "microcosm_core.first_screen_composition.first_screen_composition_card"
    )
    assert "not independent cold-entry artifacts" in artifact_fit_matrix[
        "matrix_rule"
    ]
    assert set(artifact_fit_by_id) == {
        "terminal_text_projection",
        "local_behavior_card",
        "machine_json_card",
        "readme_first_screen",
        "browser_landing",
        "short_video_storyboard",
    }
    assert artifact_fit_by_id["terminal_text_projection"]["consumer_surface"] == (
        card["human_first_command"]
    )
    assert artifact_fit_by_id["terminal_text_projection"]["source_projection"] == (
        "microcosm_core.first_screen_composition.first_screen_text_card"
    )
    assert artifact_fit_by_id["local_behavior_card"]["consumer_surface"] == (
        card["shared_first_command"]
    )
    assert artifact_fit_by_id["machine_json_card"]["consumer_surface"] == (
        "microcosm first-screen --card <project>"
    )
    assert artifact_fit_by_id["machine_json_card"]["source_projection"] == (
        "microcosm_core.first_screen_composition.first_screen_compact_card"
    )
    assert artifact_fit_by_id["machine_json_card"]["first_job"] == (
        "give_consumers_the_compact_public_card_with_full_drilldown"
    )
    assert artifact_fit_by_id["readme_first_screen"]["consumer_surface"] == (
        "README.md::Choose Your First Screen"
    )
    assert artifact_fit_by_id["browser_landing"]["consumer_surface"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
    )
    assert artifact_fit_by_id["short_video_storyboard"]["consumer_surface"] == (
        "video_storyboard_packet"
    )
    for row in artifact_fit_by_id.values():
        assert row["artifact_form"]
        assert row["first_job"]
        assert "authority_ceiling" in row["must_preserve"]
        assert "anti_claim" in row["must_preserve"]
        assert "omission_receipt" in row["must_preserve"]
        assert "discipline_comparison_strip" in row["must_preserve"]
        assert "release_or_hosting_authority" in row["must_not_claim"]
        assert "provider_call_authority" in row["must_not_claim"]
        assert "private_root_equivalence" in row["must_not_claim"]
        assert "whole_system_correctness" in row["must_not_claim"]
        assert "reader_success" in row["must_not_claim"]
    assert "validation.checks" in artifact_fit_by_id["machine_json_card"][
        "must_preserve"
    ]
    assert "reader_route_menu" in artifact_fit_by_id["terminal_text_projection"][
        "must_preserve"
    ]
    assert "readme_entry_contract.required_markdown_order" in artifact_fit_by_id[
        "readme_first_screen"
    ]["must_preserve"]
    assert "reader_route_menu" in artifact_fit_by_id["readme_first_screen"][
        "must_preserve"
    ]
    assert "observatory_landing_frame.required_visible_handles" in artifact_fit_by_id[
        "browser_landing"
    ]["must_preserve"]
    assert "video_storyboard_packet.safe_to_show" in artifact_fit_by_id[
        "short_video_storyboard"
    ]["must_preserve"]
    assert artifact_fit_matrix["safe_to_show"] == {
        "binds_to_single_source_contract": True,
        "allows_multiple_projection_forms": True,
        "exports_private_paths": False,
        "exports_provider_payloads": False,
        "creates_new_release_artifact": False,
        "creates_reader_specific_claim_ceiling": False,
    }
    assert artifact_fit_matrix["authority"] == (
        "projection_fit_matrix_not_new_artifact_authority"
    )
    cold_entry_problem_map = card["cold_entry_problem_map"]
    problem_by_id = {
        row["problem_shape_id"]: row for row in cold_entry_problem_map["rows"]
    }
    assert cold_entry_problem_map["schema_version"] == (
        "microcosm_cold_entry_problem_map_v1"
    )
    assert cold_entry_problem_map["purpose"] == (
        "bind_cold_entry_problem_shapes_to_existing_first_screen_packets"
    )
    assert "not create a second entry artifact" in cold_entry_problem_map[
        "map_rule"
    ]
    assert set(problem_by_id) == {
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
    assert problem_by_id["first_thing_best_thing_gap"]["primary_packet"] == (
        "first_run_ladder"
    )
    assert problem_by_id["first_thing_best_thing_gap"]["first_surface"] == (
        card["human_first_command"]
    )
    assert problem_by_id["audience_is_not_one_person"]["primary_packet"] == (
        "reader_route_menu"
    )
    assert problem_by_id["audience_is_not_one_person"]["first_surface"] == (
        "focused reader commands"
    )
    assert problem_by_id["honest_numbers_without_context"]["proof_surface"] == (
        "evidence_class_legend"
    )
    assert problem_by_id["discipline_invisible_without_comparison"][
        "primary_packet"
    ] == "discipline_comparison_strip"
    assert problem_by_id["discipline_invisible_without_comparison"][
        "first_surface"
    ] == "discipline_comparison_strip"
    assert problem_by_id["runnable_vs_structural_split"]["proof_surface"] == (
        "first_contact_surface_refs"
    )
    assert problem_by_id["card_discipline_not_default"]["proof_surface"] == (
        "entry_surface_contract"
    )
    for row in problem_by_id.values():
        assert row["reader_risk"]
        assert row["compression_answer"]
        assert row["not_claim"]
    assert cold_entry_problem_map["safe_to_show"] == {
        "uses_existing_first_screen_packets": True,
        "creates_new_entry_artifact": False,
        "exports_private_paths": False,
        "exports_provider_payloads": False,
        "claims_release_or_hosting": False,
        "claims_reader_success": False,
    }
    assert cold_entry_problem_map["authority"] == (
        "problem_shape_map_not_strategy_or_release_authority"
    )
    assert card["evidence_count_frame"]["interpretation"] == "accounting_not_maturity_score"
    assert card["evidence_count_frame"]["legend_ref"] == (
        "core/organ_evidence_classes.json"
    )
    assert "maturity_score" in card["evidence_count_frame"]["forbidden_reads"]
    substrate_glance = card["representative_substrate_glance"]
    glance_examples = substrate_glance["examples"]
    assert substrate_glance["schema_version"] == (
        "microcosm_representative_substrate_glance_v1"
    )
    assert substrate_glance["source_ref"] == (
        "atlas/agent_task_routes.json::organ_glance_ladder"
    )
    assert substrate_glance["one_line_source_ref"] == (
        "atlas/agent_task_routes.json::organ_glance_ladder"
    )
    assert substrate_glance["source_refs"] == ["atlas/agent_task_routes.json"]
    assert substrate_glance["sample_limit"] == 3
    assert len(glance_examples) == substrate_glance["sample_limit"]
    assert substrate_glance["total_organ_count"] >= len(glance_examples)
    assert len({row["family"] for row in glance_examples}) == len(glance_examples)
    assert all(row["glance_excerpt"] for row in glance_examples)
    assert all(row["one_line_excerpt"] for row in glance_examples)
    assert all(
        row["glance_source"] == "organ_glance_ladder_one_line"
        for row in glance_examples
    )
    assert all("one_line" in row["source_fields"] for row in glance_examples)
    assert substrate_glance["safe_to_show"] == {
        "uses_public_organ_glance_ladder": True,
        "uses_public_route_projection_one_lines": True,
        "exports_private_paths": False,
        "exports_provider_payloads": False,
        "claims_release_or_hosting": False,
        "claims_reader_success": False,
        "claims_whole_system_correctness": False,
    }
    assert substrate_glance["authority"] == (
        "representative_glance_not_inventory_score_or_readiness_claim"
    )
    evidence_class_legend = card["evidence_class_legend"]
    legend_by_id = {
        row["evidence_class"]: row for row in evidence_class_legend["classes"]
    }
    assert evidence_class_legend["source_ref"] == "core/organ_evidence_classes.json"
    assert evidence_class_legend["interpretation"] == (
        "claim_boundary_legend_not_score"
    )
    assert evidence_class_legend["missing_profiles"] == []
    assert set(legend_by_id) == {
        "verified_macro_body_import",
        "external_subprocess_witness",
        "semantic_validator",
        "algorithmic_projection",
        "fixture_schema_replay",
        "fixture_echo_smoke",
    }
    assert "release" in evidence_class_legend["authority_boundary"]
    assert "maturity score" in evidence_class_legend["reader_rule"]
    assert "verified non-secret macro body import only" in legend_by_id[
        "verified_macro_body_import"
    ]["claim_ceiling"]
    assert "tool witness only" in legend_by_id["external_subprocess_witness"][
        "claim_ceiling"
    ]
    assert legend_by_id["semantic_validator"]["evidence_strength_rank"] == 5
    assert legend_by_id["fixture_echo_smoke"][
        "counts_as_real_substrate_progress"
    ] is False
    assert card["comparison_frame"]["purpose"] == (
        "make_rigor_visible_without_claim_inflation"
    )
    assert "one shared local behavior command before reader branching" in card[
        "comparison_frame"
    ]["microcosm_entry_discipline"]
    discipline_comparison_strip = card["discipline_comparison_strip"]
    comparison_by_id = {
        row["comparison_id"]: row for row in discipline_comparison_strip["rows"]
    }
    assert discipline_comparison_strip["schema_version"] == (
        "microcosm_discipline_comparison_strip_v1"
    )
    assert discipline_comparison_strip["purpose"] == (
        "make_microcosm_rigor_visible_as_operational_differences"
    )
    assert "not as superiority" in discipline_comparison_strip["strip_rule"]
    assert set(comparison_by_id) == {
        "failure_modes_declared",
        "evidence_counts_contextualized",
        "body_copy_boundaries",
        "reader_branch_authority_shared",
        "local_behavior_before_claims",
    }
    for row in comparison_by_id.values():
        assert row["ordinary_entry_pattern"]
        assert row["microcosm_discipline"]
        assert row["visible_check_surface"]
        assert row["reader_rule"]
        assert row["not_claim"]
    assert comparison_by_id["failure_modes_declared"][
        "visible_check_surface"
    ] == "authority_ceiling"
    assert comparison_by_id["evidence_counts_contextualized"][
        "visible_check_surface"
    ] == "evidence_class_legend"
    assert comparison_by_id["body_copy_boundaries"]["visible_check_surface"] == (
        "core/organ_evidence_classes.json"
    )
    assert comparison_by_id["reader_branch_authority_shared"][
        "visible_check_surface"
    ] == "reader_route_menu"
    assert comparison_by_id["local_behavior_before_claims"][
        "visible_check_surface"
    ] == "behavior_proof_packet"
    assert discipline_comparison_strip["safe_to_show"] == {
        "uses_existing_first_screen_packets": True,
        "exports_private_paths": False,
        "exports_provider_payloads": False,
        "claims_external_benchmark": False,
        "claims_superiority": False,
        "claims_release_or_hosting": False,
        "claims_whole_system_correctness": False,
    }
    assert discipline_comparison_strip["authority"] == (
        "comparison_strip_not_benchmark_or_superiority_claim"
    )
    doctrine_effect_frame = card["doctrine_effect_frame"]
    doctrine_rows = doctrine_effect_frame["effect_rows"]
    doctrine_by_handle = {row["doctrine_handle"]: row for row in doctrine_rows}
    assert doctrine_effect_frame["purpose"] == (
        "show_doctrine_as_mistake_prevention_not_ceremony"
    )
    assert doctrine_effect_frame["authority"] == (
        "first_screen_interpretation_frame_not_doctrine_source"
    )
    assert set(doctrine_by_handle) == {
        "CONSTITUTION",
        "AXIOMS",
        "PRINCIPLES",
        "CONCEPTS",
        "MECHANISMS",
        "ANTI_PRINCIPLES",
    }
    for row in doctrine_rows:
        assert row["prevents"]
        assert row["visible_effect"]
        assert row["first_screen_surface"]
    assert doctrine_by_handle["CONCEPTS"]["standard_ref"] == (
        "standards/std_microcosm_concept.json"
    )
    assert doctrine_by_handle["CONCEPTS"]["agent_entry_ref"] == (
        "AGENTS.md::Concept And Mechanism Entry"
    )
    assert doctrine_by_handle["CONCEPTS"]["specimen_route_ref"] == (
        "atlas/entry_packet.json::"
        "concept_mechanism_entry_route.population_specimens"
    )
    assert doctrine_by_handle["MECHANISMS"]["standard_ref"] == (
        "standards/std_microcosm_mechanism.json"
    )
    assert doctrine_by_handle["MECHANISMS"]["agent_entry_ref"] == (
        "AGENTS.md::Concept And Mechanism Entry"
    )
    assert doctrine_by_handle["MECHANISMS"]["specimen_route_ref"] == (
        "atlas/entry_packet.json::"
        "concept_mechanism_entry_route.population_specimens"
    )
    assert doctrine_by_handle["CONSTITUTION"]["first_screen_surface"] == (
        "authority_ceiling"
    )
    assert doctrine_by_handle["AXIOMS"]["first_screen_surface"] == (
        "evidence_count_frame"
    )
    assert "local demo into release" in doctrine_by_handle["ANTI_PRINCIPLES"][
        "prevents"
    ]
    readme_entry_contract = card["readme_entry_contract"]
    readme_order = readme_entry_contract["required_markdown_order"]
    readme_order_pairs = {
        (row.get("surface") or row.get("command"), row["must_precede"])
        for row in readme_order
    }
    assert readme_entry_contract["purpose"] == (
        "make_package_backed_first_screen_card_the_readme_entry_surface"
    )
    assert readme_entry_contract["inventory_policy"] == (
        "quickstart_command_inventory_is_a_drilldown_after_the_first_screen_card"
    )
    assert readme_entry_contract["authority"] == (
        "documentation_order_contract_not_runtime_proof"
    )
    assert (
        "README.md::Choose Your First Screen",
        "README.md::Try It On Your Repo",
    ) in readme_order_pairs
    assert (
        card["human_first_command"],
        card["shared_first_command"],
    ) in readme_order_pairs
    assert (
        card["shared_first_command"],
        "microcosm first-screen --card <project>",
    ) in readme_order_pairs
    assert ("reader_route_menu", "quickstart_command_inventory") in readme_order_pairs
    assert ("reader_routes", "quickstart_command_inventory") in readme_order_pairs
    assert (
        "first_viewport_manifest",
        "quickstart_command_inventory",
    ) in readme_order_pairs
    for row in readme_order:
        assert row["reason"]
    assert card["entry_surface_contract"]["shared_behavior_surface"] == (
        card["shared_first_command"]
    )
    assert card["entry_surface_contract"]["package_surface"] == (
        "microcosm_core.first_screen_composition.first_screen_composition_card"
    )
    assert "README, CLI, and observatory consumers" in card[
        "entry_surface_contract"
    ]["consumer_rule"]
    assert "evidence-class legend" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    assert "doctrine-effect frame" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    assert "observatory landing frame" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    assert "README-entry contract" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    assert "reader landing packets" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    assert "reader route menu" in card["entry_surface_contract"]["consumer_rule"]
    assert "behavior-proof packet" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    assert "first-run ladder" in card["entry_surface_contract"]["consumer_rule"]
    assert "local state receipt trail" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    assert "first-viewport manifest" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    assert "overclaim tripwire matrix" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    assert "reader exit criteria" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    assert "video-storyboard packet" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    assert "artifact-fit matrix" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    assert "cold-entry problem map" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    assert "discipline comparison strip" in card["entry_surface_contract"][
        "consumer_rule"
    ]
    state_write_boundary = card["state_write_boundary"]
    assert state_write_boundary["schema_version"] == (
        "microcosm_first_screen_state_write_boundary_v1"
    )
    assert state_write_boundary["this_card_writes_microcosm_state"] is False
    assert state_write_boundary["shared_first_command_writes_state"] is True
    assert state_write_boundary["behavioral_proof_command"] == (
        card["shared_first_command"]
    )
    assert state_write_boundary["front_door_status_ref"] == (
        "microcosm tour --card <project>::front_door_status"
    )
    assert state_write_boundary["safe_to_show"] == {
        "source_files_mutated": False,
        "provider_calls_authorized": False,
        "release_or_hosting_authorized": False,
        "proof_correctness_claim": False,
    }
    scale_counts = card["scale_frame"]["public_scale_counts"]
    assert card["scale_frame"]["count_interpretation"] == (
        "receipt_backed_handles_not_scores"
    )
    organ_registry = json.loads((MICROCOSM_ROOT / "core/organ_registry.json").read_text())
    standards_registry = json.loads(
        (MICROCOSM_ROOT / "core/standards_registry.json").read_text()
    )
    assert scale_counts["implemented_organs"]["source_ref"] == "core/organ_registry.json"
    assert scale_counts["implemented_organs"]["count"] == len(
        organ_registry["implemented_organs"]
    )
    assert scale_counts["public_standards"]["source_ref"] == (
        "core/standards_registry.json"
    )
    assert scale_counts["public_standards"]["count"] == standards_registry[
        "standard_count"
    ]
    expected_materials, expected_rows = _fixture_manifest_source_open_counts()
    assert scale_counts["source_open_materials"]["source_ref"] == (
        "core/fixture_manifests/*.fixture_manifest.json"
    )
    assert scale_counts["source_open_materials"]["fallback_ref"] == (
        "receipts/runtime_shell/workingness_failure_map.json"
    )
    assert scale_counts["source_open_materials"]["count"] == expected_materials
    assert scale_counts["source_open_materials"]["read_as"] == (
        "copy_boundary_accounting_not_maturity_score"
    )
    assert scale_counts["rows_with_source_imports"]["source_ref"] == (
        "core/fixture_manifests/*.fixture_manifest.json"
    )
    assert scale_counts["rows_with_source_imports"]["count"] == expected_rows
    observatory_landing_frame = card["observatory_landing_frame"]
    assert observatory_landing_frame["schema_version"] == (
        "microcosm_observatory_landing_frame_v1"
    )
    assert observatory_landing_frame["role"] == (
        "make_the_hello_first_screen_card_the_browser_landing_frame"
    )
    assert observatory_landing_frame["human_first_command"] == (
        card["human_first_command"]
    )
    assert observatory_landing_frame["text_projection_command"] == (
        card["human_first_command"]
    )
    assert observatory_landing_frame["shared_first_command"] == (
        card["shared_first_command"]
    )
    assert observatory_landing_frame["behavioral_proof_command"] == (
        card["shared_first_command"]
    )
    assert observatory_landing_frame["serve_command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765"
    )
    assert observatory_landing_frame["bounded_validation_command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
    )
    assert observatory_landing_frame["bounded_validation_request_count"] == 7
    assert "route smokes" in observatory_landing_frame["bounded_validation_rule"]
    assert observatory_landing_frame["browser_landing_reuse"] == {
        "source_projection": (
            "microcosm_core.first_screen_composition.first_screen_text_card"
        ),
        "serve_command": "microcosm serve <project> --host 127.0.0.1 --port 8765",
        "bounded_validation_command": (
            "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
        ),
        "default_endpoint": "/",
        "card_endpoint": "/project/first-screen",
        "authority": "browser_projection_over_same_card_not_json_first_lens_inventory",
    }
    assert observatory_landing_frame["endpoints"] == {
        "html_landing": "/",
        "first_screen_card": "/project/first-screen",
        "compact_observatory_card": "/project/observatory-card",
        "full_observatory_model": "/project/observatory",
        "project_observe": "/project/observe",
    }
    assert observatory_landing_frame["drilldown_order"] == [
        "html_landing",
        "first_screen_card",
        "compact_observatory_card",
        "full_observatory_model",
        "project_observe",
    ]
    assert "human_first_command" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "text_projection" in observatory_landing_frame["required_visible_handles"]
    assert "behavioral_proof_command" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "serve_command" in observatory_landing_frame["required_visible_handles"]
    assert "bounded_validation_command" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "reader_landing_packets" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "reader_route_menu" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "behavior_proof_packet" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "first_run_ladder" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "first_viewport_manifest" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "local_state_receipt_trail" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "first_contact_surface_refs" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "overclaim_tripwire_matrix" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "discipline_comparison_strip" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "reader_exit_criteria" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "video_storyboard_packet" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "artifact_fit_matrix" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "cold_entry_problem_map" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "public_scale_counts" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "representative_substrate_glance" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "evidence_class_legend" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "doctrine_effect_frame" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "release, hosting, provider calls" in observatory_landing_frame[
        "authority_boundary"
    ]
    assert card["authority_ceiling"]["release_authority"] is False
    assert card["authority_ceiling"]["source_mutation_authority"] is False
    assert card["authority_ceiling"]["private_data_equivalence_authority"] is False
    assert card["authority_ceiling"]["provider_call_authority"] is False
    assert card["authority_ceiling"]["score_based_progress_authority"] is False
    assert card["authority_ceiling"]["whole_system_correctness_authority"] is False
    assert card["omission_receipt"]["drilldown"] == "paper_modules/first_screen_composition_root.md"
    assert any(
        drilldown.get("command")
        == "microcosm serve <project> --host 127.0.0.1 --port 8765"
        and drilldown.get("endpoint") == "/"
        for drilldown in card["drilldowns"]
    )
    assert any(
        drilldown.get("command")
        == "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
        and drilldown.get("endpoint") == "/"
        for drilldown in card["drilldowns"]
    )
    assert any(
        drilldown.get("command") == "microcosm workingness"
        for drilldown in card["drilldowns"]
    )
    assert card["validation"]["checks"]["workingness_drilldown"] is True
    assert card["validation"]["checks"]["comparison_frame"] is True
    assert card["validation"]["checks"]["discipline_comparison_strip"] is True
    assert card["validation"]["checks"]["reader_route_menu"] is True
    assert card["validation"]["checks"]["reader_landing_packets"] is True
    assert card["validation"]["checks"]["behavior_proof_packet"] is True
    assert card["validation"]["checks"]["first_run_ladder"] is True
    assert card["validation"]["checks"]["first_viewport_manifest"] is True
    assert card["validation"]["checks"]["local_state_receipt_trail"] is True
    assert card["validation"]["checks"]["first_contact_surface_refs"] is True
    assert card["validation"]["checks"]["overclaim_tripwire_matrix"] is True
    assert card["validation"]["checks"]["reader_exit_criteria"] is True
    assert card["validation"]["checks"]["video_storyboard_packet"] is True
    assert card["validation"]["checks"]["artifact_fit_matrix"] is True
    assert card["validation"]["checks"]["cold_entry_problem_map"] is True
    assert card["validation"]["checks"]["doctrine_effect_frame"] is True
    assert card["validation"]["checks"]["readme_entry_contract"] is True
    assert card["validation"]["checks"]["entry_surface_contract"] is True
    assert card["validation"]["checks"]["human_first_command"] is True
    assert card["validation"]["checks"]["text_projection"] is True
    assert card["validation"]["checks"]["representative_substrate_glance"] is True
    assert card["validation"]["checks"]["evidence_class_legend"] is True
    assert card["validation"]["checks"]["scale_frame"] is True
    assert card["validation"]["checks"]["state_write_boundary"] is True
    assert card["validation"]["checks"]["observatory_landing_frame"] is True
    assert "body" not in _walk_keys(card)
    assert (
        module.first_screen_composition_card.__module__
        == "microcosm_core.first_screen_composition"
    )


def test_first_screen_standard_scan_binds_card_to_standard_contract() -> None:
    module = _load_module()

    card = module.first_screen_composition_card(MICROCOSM_ROOT, project_label=".")
    scan = card["standard_backed_first_screen_scan"]

    assert card["validation"]["checks"]["standard_backed_first_screen_scan"] is True
    assert scan["status"] == "pass"
    assert scan["schema_version"] == "microcosm_standard_backed_first_screen_scan_v1"
    assert scan["standard_id"] == "std_microcosm_first_screen_composition_root"
    assert (
        scan["standard_ref"]
        == "standards/std_microcosm_first_screen_composition_root.json"
    )
    assert scan["expected_reader_route_ids"] == EXPECTED_READER_ROUTE_ID_LIST
    assert scan["missing"] == {
        "required_fields": [],
        "validator_minimum_checks": [],
        "receipt_must_record": [],
    }
    assert all(scan["checks"].values())
    assert {row["surface"] for row in scan["route_parity"]} == {
        "reader_routes",
        "reader_route_menu.routes",
        "reader_landing_packets.packets",
        "reader_exit_criteria.criteria",
    }
    assert all(row["status"] == "pass" for row in scan["route_parity"])
    assert all(row["status"] == "pass" for row in scan["reader_command_parity"])
    assert all(row["status"] == "pass" for row in scan["denied_authority_flags"])
    assert (
        scan["authority"]
        == "scanner_contract_only_not_release_or_reader_success_authority"
    )


def test_first_screen_static_json_loads_are_cached_between_cards() -> None:
    from microcosm_core import first_screen_composition

    first_screen_composition._load_json_object.cache_clear()

    first_card = first_screen_composition.first_screen_composition_card(
        MICROCOSM_ROOT,
        project_label=".",
    )
    after_first = first_screen_composition._load_json_object.cache_info()

    second_card = first_screen_composition.first_screen_composition_card(
        MICROCOSM_ROOT,
        project_label=".",
    )
    after_second = first_screen_composition._load_json_object.cache_info()

    assert first_card["status"] == "pass"
    assert second_card["status"] == "pass"
    assert after_first.misses > 0
    assert after_second.misses == after_first.misses
    assert after_second.hits > after_first.hits


def test_first_screen_static_json_cache_rejects_duplicate_keys(tmp_path: Path) -> None:
    from microcosm_core import first_screen_composition
    from microcosm_core.schemas import DuplicateJsonKeyError

    payload_path = tmp_path / "first_screen.json"
    payload_path.write_text(
        '{"reader_routes": [], "reader_routes": [{"reader_route_id": "shadow"}]}',
        encoding="utf-8",
    )
    stat = payload_path.stat()
    first_screen_composition._load_json_object.cache_clear()

    with pytest.raises(DuplicateJsonKeyError, match="duplicate JSON key 'reader_routes'"):
        first_screen_composition._load_json_object(
            str(payload_path),
            stat.st_mtime_ns,
            stat.st_size,
        )


def test_first_screen_composition_card_cli_emits_ascii_public_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/first_screen_composition_card.py",
            "--project-label",
            ".",
        ],
        cwd=MICROCOSM_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    result.stdout.encode("ascii")
    card = json.loads(result.stdout)

    assert card["status"] == "pass"
    assert card["human_first_command"] == "microcosm hello ."
    assert card["shared_first_command"] == "microcosm tour --card ."
    assert card["source_checkout_commands"] == {
        "schema_version": "microcosm_source_checkout_commands_v1",
        "purpose": "keep_the_no_install_entry_path_copyable_after_hello",
        "hello": "PYTHONPATH=src python3 -m microcosm_core hello .",
        "behavior_proof": "PYTHONPATH=src python3 -m microcosm_core tour --card .",
        "status_card": "PYTHONPATH=src python3 -m microcosm_core status --card .",
        "first_screen_card": (
            "PYTHONPATH=src python3 -m microcosm_core first-screen --card ."
        ),
        "agent_entry_selector": (
            "PYTHONPATH=src python3 -m microcosm_core "
            "agent-entry-composition --root . --task agent-entry "
            "--viewer {type_a_agent|human} --card --check"
        ),
        "authority": "source_checkout_fallback_not_package_install_or_release_claim",
    }
    assert card["text_projection"]["command"] == "microcosm hello ."
    assert card["text_projection"]["source_checkout_command"] == (
        "PYTHONPATH=src python3 -m microcosm_core hello ."
    )
    assert card["text_projection"]["behavioral_proof_command"] == (
        "microcosm tour --card ."
    )
    assert card["text_projection"]["source_checkout_behavioral_proof_command"] == (
        "PYTHONPATH=src python3 -m microcosm_core tour --card ."
    )
    assert card["text_projection"]["writes_microcosm_state"] is False
    assert [
        row["slot_id"] for row in card["first_viewport_manifest"]["slots"]
    ] == [
        "identity",
        "first_run",
        "proof_chain",
        "evidence_context",
        "reader_branch",
        "authority_boundary",
    ]
    assert card["first_viewport_manifest"]["consumer_surfaces"]["terminal"] == (
        "microcosm hello ."
    )
    assert card["first_viewport_manifest"]["consumer_surfaces"]["json"] == (
        "microcosm first-screen --card ."
    )
    assert card["first_viewport_manifest"]["authority"] == (
        "viewport_manifest_not_new_claim_or_renderer_authority"
    )
    assert card["entry_surface_contract"]["script_surface"] == (
        "python3 scripts/first_screen_composition_card.py --project-label ."
    )
    assert card["doctrine_effect_frame"]["purpose"] == (
        "show_doctrine_as_mistake_prevention_not_ceremony"
    )
    assert card["readme_entry_contract"]["inventory_policy"] == (
        "quickstart_command_inventory_is_a_drilldown_after_the_first_screen_card"
    )
    assert card["evidence_class_legend"]["source_ref"] == (
        "core/organ_evidence_classes.json"
    )
    assert any(
        row["evidence_class"] == "verified_macro_body_import"
        and "private-root equivalence" in row["claim_ceiling"]
        for row in card["evidence_class_legend"]["classes"]
    )
    assert card["state_write_boundary"]["this_card_status_scope"] == (
        "composition_contract_only_not_local_run_result"
    )
    assert card["state_write_boundary"]["behavioral_proof_command"] == (
        "microcosm tour --card ."
    )
    assert card["state_write_boundary"]["front_door_status_ref"] == (
        "microcosm tour --card .::front_door_status"
    )
    assert [
        row["command"] for row in card["first_run_ladder"]["steps"][:3]
    ] == [
        "microcosm hello .",
        "microcosm tour --card .",
        "microcosm status --card .",
    ]
    assert [
        row["source_checkout_command"]
        for row in card["first_run_ladder"]["steps"][:3]
    ] == [
        "PYTHONPATH=src python3 -m microcosm_core hello .",
        "PYTHONPATH=src python3 -m microcosm_core tour --card .",
        "PYTHONPATH=src python3 -m microcosm_core status --card .",
    ]
    assert card["reader_route_menu"]["default_command"] == "microcosm hello ."
    assert card["reader_route_menu"]["alias_hint"] == (
        "reader aliases: cold-cloner, interesting-parts, skeptical-reviewer, "
        "reviewer, type-a-agent, domain-specialist"
    )
    assert card["reader_route_menu"]["shared_behavior_command"] == (
        "microcosm tour --card ."
    )
    assert card["reader_route_menu"]["machine_card_command"] == (
        "microcosm first-screen --card ."
    )
    assert card["reader_route_menu"]["default_json_command"] == (
        "microcosm first-screen ."
    )
    assert {
        row["reader_route_id"]: row["terminal_command"]
        for row in card["reader_route_menu"]["routes"]
    } == {
        "public_github_visitor": (
            "microcosm hello --reader public_github_visitor ."
        ),
        "safety_evals_engineer": (
            "microcosm hello --reader safety_evals_engineer ."
        ),
        "hiring_reviewer": "microcosm hello --reader hiring_reviewer .",
        "peer_developer": "microcosm hello --reader peer_developer .",
        "domain_specialist": "microcosm hello --reader domain_specialist .",
        "type_a_agent": "microcosm hello --reader type_a_agent .",
    }
    assert [
        row["state_ref"] for row in card["local_state_receipt_trail"]["trail"]
    ] == [
        ".microcosm/catalog.json",
        ".microcosm/routes.json",
        ".microcosm/events.jsonl",
        ".microcosm/evidence/index.json",
        ".microcosm/graph.json",
    ]
    assert card["first_contact_surface_refs"]["surfaces"]["observatory"][
        "bounded_validation_command"
    ] == "microcosm serve . --host 127.0.0.1 --port 8765 --max-requests 7"
    assert card["first_contact_surface_refs"]["surfaces"]["proof_lab"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert card["validation"]["checks"]["first_run_ladder"] is True
    assert card["validation"]["checks"]["local_state_receipt_trail"] is True
    assert card["validation"]["checks"]["first_contact_surface_refs"] is True
    assert card["validation"]["checks"]["overclaim_tripwire_matrix"] is True
    assert card["validation"]["checks"]["reader_exit_criteria"] is True
    assert card["validation"]["checks"]["reader_route_menu"] is True
    assert card["validation"]["checks"]["video_storyboard_packet"] is True
    assert card["validation"]["checks"]["artifact_fit_matrix"] is True
    assert {route["reader_route_id"] for route in card["reader_routes"]} == (
        EXPECTED_READER_ROUTE_IDS
    )
    packet_ids = {
        packet["reader_route_id"]
        for packet in card["reader_landing_packets"]["packets"]
    }
    assert packet_ids == EXPECTED_READER_ROUTE_IDS
    assert card["validation"]["checks"]["reader_landing_packets"] is True
    assert card["validation"]["checks"]["behavior_proof_packet"] is True
    assert "/Users/" not in result.stdout
    assert "src/ai_workflow" not in result.stdout
    assert '"body":' not in result.stdout


def test_first_screen_compact_card_is_summary_first_json_projection() -> None:
    module = _load_module()
    card = module.first_screen_composition_card(MICROCOSM_ROOT, project_label=".")
    compact = module.first_screen_compact_card(card)

    compact_json = json.dumps(compact, sort_keys=True)
    assert len(compact_json) < module.COMPACT_JSON_CARD_MAX_CHARS
    assert compact["schema_version"] == "microcosm_first_screen_compact_card_v1"
    assert compact["compact_projection_of"] == (
        "microcosm_first_screen_composition_card_v1"
    )
    assert compact["output_policy"] == {
        "default_json_is_first_screen_projection": True,
        "default_json_command": "microcosm first-screen .",
        "compact_card_command": "microcosm first-screen --card .",
        "stdout_budget_chars": module.COMPACT_JSON_CARD_MAX_CHARS,
        "full_contract_command": "microcosm first-screen --full .",
        "text_projection_command": "microcosm first-screen --format text .",
        "full_contract_preserved": True,
    }
    assert compact["reader_route_menu"]["machine_card_command"] == (
        "microcosm first-screen --card ."
    )
    assert compact["reader_route_menu"]["default_json_command"] == (
        "microcosm first-screen ."
    )
    assert {
        row["reader_route_id"] for row in compact["reader_route_menu"]["routes"]
    } == EXPECTED_READER_ROUTE_IDS
    assert compact["state_write_boundary"]["this_card_writes_microcosm_state"] is False
    compact_glance = compact["evidence_context"]["representative_substrate_glance"]
    assert compact_glance["source_ref"] == (
        "atlas/agent_task_routes.json::organ_glance_ladder"
    )
    assert compact_glance["one_line_source_ref"] == (
        "atlas/agent_task_routes.json::organ_glance_ladder"
    )
    assert compact_glance["source_refs"] == ["atlas/agent_task_routes.json"]
    assert compact_glance["sample_limit"] == 3
    assert compact_glance["total_organ_count"] == (
        card["representative_substrate_glance"]["total_organ_count"]
    )
    assert compact_glance["example_display_names"] == [
        row["display_name"]
        for row in card["representative_substrate_glance"]["examples"]
    ]
    assert compact_glance["examples"] == [
        {
            "organ_id": row["organ_id"],
            "display_name": row["display_name"],
            "family": row["family"],
            "glance_excerpt": row["glance_excerpt"],
            "glance_source": row["glance_source"],
            "one_line_excerpt": row["one_line_excerpt"],
        }
        for row in card["representative_substrate_glance"]["examples"]
    ]
    assert compact_glance["authority"] == (
        "representative_glance_not_inventory_score_or_readiness_claim"
    )
    assert compact["drilldowns"]["full_json"] == "microcosm first-screen --full ."
    assert "video_storyboard_packet" not in compact
    assert compact["omission_receipt"]["summary_first_projection"] is True


def test_first_screen_text_card_is_terminal_sized_and_honest() -> None:
    module = _load_module()
    card = module.first_screen_composition_card(MICROCOSM_ROOT, project_label=".")

    text = module.first_screen_text_card(card)
    scale_counts = card["scale_frame"]["public_scale_counts"]
    expected_public_handles = (
        f"  Public handles: {scale_counts['implemented_organs']['count']} "
        f"organ-registry rows, {scale_counts['public_standards']['count']} "
        f"standard-registry rows, "
        f"{scale_counts['source_open_materials']['count']} fixture/workingness "
        "source-open material handles."
    )

    text.encode("ascii")
    assert text.startswith("Microcosm first screen\n")
    assert (
        "Source-only card: PYTHONPATH=src python3 -m microcosm_core hello ."
        in text
    )
    assert "Open card: microcosm hello ." in text
    assert "First run: microcosm tour --card ." in text
    assert (
        "First run: microcosm tour --card . | Source-only first run: "
        "PYTHONPATH=src python3 -m microcosm_core tour --card ."
        in text
    )
    assert (
        "Check state: microcosm status --card . | Source-only status: "
        "PYTHONPATH=src python3 -m microcosm_core status --card . | "
        "Trail: catalog -> routes -> events -> evidence -> graph."
        in text
    )
    assert "A local evidence router" in text
    assert "doctrine names boundaries" in text
    assert "exit when you can choose a drilldown" in text
    assert "without the command inventory" in text
    assert "Substrate glance:" in text
    assert "atlas/agent_task_routes.json organ_glance_ladder.one_line" in text
    assert "fallbacks use route cards" in text
    assert "examples are handles, not readiness claims" in text
    for row in card["representative_substrate_glance"]["examples"]:
        assert row["display_name"] in text
        assert row["glance_excerpt"][:24] in text
    assert expected_public_handles in text
    assert "organ-registry rows" in text
    assert "standard-registry rows" in text
    assert "fixture/workingness source-open material handles" in text
    assert "Counts are receipt-backed handles" in text
    assert "registries and fixture manifests" in text
    assert "status --card shows the stricter body-import floor" in text
    assert "Evidence classes: body import, subprocess witness" in text
    assert "fixture smoke/schema" in text
    assert (
        "Behavior proof after tour --card: front_door_status=pass, "
        "selected_route_id, state refs, source_files_mutated=false"
    ) in text
    assert (
        "reader aliases: cold-cloner, interesting-parts, skeptical-reviewer, "
        "reviewer, type-a-agent, domain-specialist"
    ) in text
    assert (
        "GitHub visitor: microcosm hello --reader public_github_visitor . | Proof: "
        "`microcosm tour --card .`"
    ) in text
    assert (
        "Safety/evals: microcosm hello --reader safety_evals_engineer . | Proof: "
        "`microcosm authority --card` plus `microcosm workingness --card`"
    ) in text
    assert (
        "Hiring: microcosm hello --reader hiring_reviewer . | Proof: "
        "`microcosm legibility-scorecard` plus `microcosm tour --card .`"
    ) in text
    assert (
        "Peer developer: microcosm hello --reader peer_developer . | Proof: "
        "`microcosm observe --card .`"
    ) in text
    assert (
        "Domain specialist: microcosm hello --reader domain_specialist . | Proof: "
        "`ORGANS.md#find-your-specialty` plus `microcosm tour --card .`"
    ) in text
    assert (
        "Type A agent: microcosm hello --reader type_a_agent . | Proof: "
        "`microcosm organ-surface-contract --card --root .`"
    ) in text
    assert (
        "observatory: microcosm serve . --host 127.0.0.1 --port 8765 --max-requests 7"
        in text
    )
    assert "-> /project/first-screen -> /project/observatory-card" in text
    assert (
        "artifact fit: terminal, README, browser, JSON, and video reuse this card; "
        "problem map names the gaps."
        in text
    )
    assert (
        "This card is the map; the first run writes .microcosm and exercises "
        "the larger public substrate:"
    ) in text
    assert "No release, hosted publication, provider-call" in text
    assert "paper_modules/first_screen_composition_root.md" in text
    assert len(text.splitlines()) <= module.TEXT_CARD_MAX_LINES
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert '"body":' not in text


def test_first_screen_text_card_can_focus_each_reader_branch() -> None:
    module = _load_module()
    card = module.first_screen_composition_card(MICROCOSM_ROOT, project_label=".")
    expected = {
        "public_github_visitor": {
            "label": "GitHub visitor",
            "first_action": "Run `microcosm tour --card .` after this card.",
            "proof": "`microcosm tour --card .`",
            "success": "release, hosting, and private-data claims",
            "absent": [
                "Reader branch: Safety/evals",
                "Reader branch: Hiring",
                "Reader branch: Peer developer",
                "Reader branch: Domain specialist",
                "Reader branch: Type A agent",
            ],
        },
        "safety_evals_engineer": {
            "label": "Safety/evals",
            "first_action": (
                "Run `microcosm tour --card .` first, then "
                "`microcosm status --card .`."
            ),
            "proof": "`microcosm authority --card` plus `microcosm workingness --card`",
            "success": "maturity or release readiness",
            "absent": [
                "Reader branch: GitHub visitor",
                "Reader branch: Hiring",
                "Reader branch: Peer developer",
                "Reader branch: Domain specialist",
                "Reader branch: Type A agent",
            ],
        },
        "hiring_reviewer": {
            "label": "Hiring",
            "first_action": (
                "Run `microcosm legibility-scorecard`, then "
                "`microcosm tour --card .`."
            ),
            "proof": "`microcosm legibility-scorecard` plus `microcosm tour --card .`",
            "success": "public card explicitly refuses to make",
            "absent": [
                "Reader branch: GitHub visitor",
                "Reader branch: Safety/evals",
                "Reader branch: Peer developer",
                "Reader branch: Domain specialist",
                "Reader branch: Type A agent",
            ],
        },
        "peer_developer": {
            "label": "Peer developer",
            "first_action": "Run `microcosm tour --card .`.",
            "proof": "`microcosm observe --card .`",
            "success": "without provider calls",
            "absent": [
                "Reader branch: GitHub visitor",
                "Reader branch: Safety/evals",
                "Reader branch: Hiring",
                "Reader branch: Domain specialist",
                "Reader branch: Type A agent",
            ],
        },
        "domain_specialist": {
            "label": "Domain specialist",
            "first_action": (
                "Open `ORGANS.md#find-your-specialty`, then run "
                "`microcosm tour --card .`."
            ),
            "proof": "`ORGANS.md#find-your-specialty` plus `microcosm tour --card .`",
            "success": "domain correctness",
            "absent": [
                "Reader branch: GitHub visitor",
                "Reader branch: Safety/evals",
                "Reader branch: Hiring",
                "Reader branch: Peer developer",
                "Reader branch: Type A agent",
            ],
        },
        "type_a_agent": {
            "label": "Type A agent",
            "first_action": (
                "Run `microcosm first-screen --card .`. "
                "If you need `doctrine_effect_frame`, run "
                "`microcosm first-screen --full .` before reading it; then run "
                "`microcosm organ-surface-contract --card --root .`."
            ),
            "proof": "`microcosm organ-surface-contract --card --root .`",
            "success": "mechanisms from validators/projections",
            "absent": [
                "Reader branch: GitHub visitor",
                "Reader branch: Safety/evals",
                "Reader branch: Hiring",
                "Reader branch: Peer developer",
                "Reader branch: Domain specialist",
            ],
        },
    }

    for reader_id, assertions in expected.items():
        text = module.first_screen_text_card(card, reader_id=reader_id)

        text.encode("ascii")
        assert text.startswith("Microcosm first screen\n")
        assert (
            "Source-only card: PYTHONPATH=src python3 -m microcosm_core hello ."
            in text
        )
        assert "Open card: microcosm hello ." in text
        assert "First run: microcosm tour --card ." in text
        assert (
            "First run: microcosm tour --card . | Source-only first run: "
            "PYTHONPATH=src python3 -m microcosm_core tour --card ."
            in text
        )
        assert (
            "Check state: microcosm status --card . | Source-only status: "
            "PYTHONPATH=src python3 -m microcosm_core status --card . | "
            "Trail: catalog -> routes -> events -> evidence -> graph."
            in text
        )
        assert f"Reader branch: {assertions['label']}" in text
        assert f"  Command: microcosm hello --reader {reader_id} ." in text
        assert (
            "Text card: microcosm first-screen --format text "
            f"--reader {reader_id} ."
        ) in text
        assert "  Question: " in text
        assert f"  First action: {assertions['first_action']}" in text
        assert f"  Proof: {assertions['proof']}" in text
        assert assertions["success"] in text
        assert "Authority ceiling:" in text
        assert "Public handles:" in text
        assert "Counts are receipt-backed handles" in text
        assert "registries and fixture manifests" in text
        assert "status --card shows the stricter body-import floor" in text
        assert "Evidence classes: body import, subprocess witness" in text
        assert "Behavior proof after tour --card: front_door_status=pass" in text
        assert "problem map names the gaps" in text
        assert "doctrine names boundaries" in text
        assert "exit when you can choose a drilldown" in text
        assert "without the command inventory" in text
        assert "Substrate glance:" in text
        assert "atlas/agent_task_routes.json organ_glance_ladder.one_line" in text
        assert "fallbacks use route cards" in text
        for row in card["representative_substrate_glance"]["examples"]:
            assert row["display_name"] in text
        assert len(text.splitlines()) <= module.TEXT_CARD_MAX_LINES
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        for absent in assertions["absent"]:
            assert absent not in text


def test_first_screen_composition_card_cli_emits_text_projection() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/first_screen_composition_card.py",
            "--project-label",
            ".",
            "--format",
            "text",
        ],
        cwd=MICROCOSM_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    result.stdout.encode("ascii")
    assert result.stdout.startswith("Microcosm first screen\n")
    assert "Open card: microcosm hello ." in result.stdout
    assert "First run: microcosm tour --card ." in result.stdout
    assert "doctrine names boundaries" in result.stdout
    assert "exit when you can choose a drilldown" in result.stdout
    assert "without the command inventory" in result.stdout
    assert "Substrate glance:" in result.stdout
    assert "atlas/agent_task_routes.json organ_glance_ladder.one_line" in result.stdout
    assert "fallbacks use route cards" in result.stdout
    assert "registries and fixture manifests" in result.stdout
    assert "status --card shows the stricter body-import floor" in result.stdout
    assert "Evidence classes: body import, subprocess witness" in result.stdout
    assert "Behavior proof after tour --card: front_door_status=pass" in result.stdout
    assert "reader_routes" not in result.stdout
    assert "/Users/" not in result.stdout
    assert "src/ai_workflow" not in result.stdout


def test_first_screen_composition_card_cli_can_focus_text_projection() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/first_screen_composition_card.py",
            "--project-label",
            ".",
            "--format",
            "text",
            "--reader",
            "safety_evals_engineer",
        ],
        cwd=MICROCOSM_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    result.stdout.encode("ascii")
    assert result.stdout.startswith("Microcosm first screen\n")
    assert "Open card: microcosm hello ." in result.stdout
    assert "First run: microcosm tour --card ." in result.stdout
    assert "doctrine names boundaries" in result.stdout
    assert "exit when you can choose a drilldown" in result.stdout
    assert "without the command inventory" in result.stdout
    assert "Substrate glance:" in result.stdout
    assert "atlas/agent_task_routes.json organ_glance_ladder.one_line" in result.stdout
    assert "fallbacks use route cards" in result.stdout
    assert "registries and fixture manifests" in result.stdout
    assert "status --card shows the stricter body-import floor" in result.stdout
    assert "Evidence classes: body import, subprocess witness" in result.stdout
    assert "Behavior proof after tour --card: front_door_status=pass" in result.stdout
    assert "Reader branch: Safety/evals" in result.stdout
    assert (
        "  Command: microcosm hello --reader safety_evals_engineer ."
        in result.stdout
    )
    assert (
        "Text card: microcosm first-screen --format text --reader "
        "safety_evals_engineer ."
        in result.stdout
    )
    assert (
        "  First action: Run `microcosm tour --card .` first, then "
        "`microcosm status --card .`."
    ) in result.stdout
    assert (
        "  Proof: `microcosm authority --card` plus `microcosm workingness --card`"
        in result.stdout
    )
    assert "maturity or release readiness" in result.stdout
    assert "Reader branches:" not in result.stdout
    assert "Reader branch: Hiring" not in result.stdout
    assert "reader_routes" not in result.stdout
    assert "/Users/" not in result.stdout
    assert "src/ai_workflow" not in result.stdout
