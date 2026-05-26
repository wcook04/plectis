from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = MICROCOSM_ROOT / "scripts/first_screen_composition_card.py"


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
    assert card["human_first_command"] == "microcosm hello <project>"
    assert card["shared_first_command"] == "microcosm tour --card <project>"
    text_projection = card["text_projection"]
    assert text_projection == {
        "command": card["human_first_command"],
        "writes_microcosm_state": False,
        "behavioral_proof_command": card["shared_first_command"],
        "authority": "terminal_text_projection_only_not_behavior_proof",
        "reader_rule": (
            "Use this command to view the first-screen card; run the "
            "behavior proof command to write .microcosm state."
        ),
    }
    assert route_ids == {
        "safety_evals_engineer",
        "hiring_reviewer",
        "peer_developer",
    }
    reader_landing_packets = card["reader_landing_packets"]
    packet_by_id = {
        packet["reader_route_id"]: packet
        for packet in reader_landing_packets["packets"]
    }
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
    assert "maturity or release readiness" in packet_by_id[
        "safety_evals_engineer"
    ]["success_criterion"]
    assert "provider calls" in packet_by_id["peer_developer"]["success_criterion"]
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
    assert card["evidence_count_frame"]["interpretation"] == "accounting_not_maturity_score"
    assert card["evidence_count_frame"]["legend_ref"] == (
        "core/organ_evidence_classes.json"
    )
    assert "maturity_score" in card["evidence_count_frame"]["forbidden_reads"]
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
        "ANTI_PRINCIPLES",
    }
    for row in doctrine_rows:
        assert row["prevents"]
        assert row["visible_effect"]
        assert row["first_screen_surface"]
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
        "microcosm first-screen <project>",
    ) in readme_order_pairs
    assert ("reader_routes", "quickstart_command_inventory") in readme_order_pairs
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
    assert "behavior-proof packet" in card["entry_surface_contract"][
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
    assert scale_counts["implemented_organs"]["source_ref"] == "core/organ_registry.json"
    assert scale_counts["implemented_organs"]["count"] > 0
    assert scale_counts["public_standards"]["source_ref"] == (
        "core/standards_registry.json"
    )
    assert scale_counts["public_standards"]["count"] > 0
    assert scale_counts["source_open_materials"]["source_ref"] == (
        "receipts/runtime_shell/workingness_failure_map.json"
    )
    assert scale_counts["source_open_materials"]["count"] > 0
    assert scale_counts["source_open_materials"]["read_as"] == (
        "copy_boundary_accounting_not_maturity_score"
    )
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
    assert observatory_landing_frame["browser_landing_reuse"] == {
        "source_projection": (
            "microcosm_core.first_screen_composition.first_screen_text_card"
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
    assert "reader_landing_packets" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "behavior_proof_packet" in observatory_landing_frame[
        "required_visible_handles"
    ]
    assert "public_scale_counts" in observatory_landing_frame[
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
        drilldown.get("command") == "microcosm workingness"
        for drilldown in card["drilldowns"]
    )
    assert card["validation"]["checks"]["workingness_drilldown"] is True
    assert card["validation"]["checks"]["comparison_frame"] is True
    assert card["validation"]["checks"]["reader_landing_packets"] is True
    assert card["validation"]["checks"]["behavior_proof_packet"] is True
    assert card["validation"]["checks"]["doctrine_effect_frame"] is True
    assert card["validation"]["checks"]["readme_entry_contract"] is True
    assert card["validation"]["checks"]["entry_surface_contract"] is True
    assert card["validation"]["checks"]["human_first_command"] is True
    assert card["validation"]["checks"]["text_projection"] is True
    assert card["validation"]["checks"]["evidence_class_legend"] is True
    assert card["validation"]["checks"]["scale_frame"] is True
    assert card["validation"]["checks"]["state_write_boundary"] is True
    assert card["validation"]["checks"]["observatory_landing_frame"] is True
    assert "body" not in _walk_keys(card)
    assert (
        module.first_screen_composition_card.__module__
        == "microcosm_core.first_screen_composition"
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
    assert card["text_projection"]["command"] == "microcosm hello ."
    assert card["text_projection"]["behavioral_proof_command"] == (
        "microcosm tour --card ."
    )
    assert card["text_projection"]["writes_microcosm_state"] is False
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
    assert {route["reader_route_id"] for route in card["reader_routes"]} == {
        "safety_evals_engineer",
        "hiring_reviewer",
        "peer_developer",
    }
    packet_ids = {
        packet["reader_route_id"]
        for packet in card["reader_landing_packets"]["packets"]
    }
    assert packet_ids == {
        "safety_evals_engineer",
        "hiring_reviewer",
        "peer_developer",
    }
    assert card["validation"]["checks"]["reader_landing_packets"] is True
    assert card["validation"]["checks"]["behavior_proof_packet"] is True
    assert "/Users/" not in result.stdout
    assert "src/ai_workflow" not in result.stdout
    assert '"body":' not in result.stdout


def test_first_screen_text_card_is_terminal_sized_and_honest() -> None:
    module = _load_module()
    card = module.first_screen_composition_card(MICROCOSM_ROOT, project_label=".")

    text = module.first_screen_text_card(card)

    text.encode("ascii")
    assert text.startswith("Microcosm first screen\n")
    assert "Open card: microcosm hello ." in text
    assert "First run: microcosm tour --card ." in text
    assert "A local evidence router, not a maturity brochure" in text
    assert "doctrine appears as prevented mistakes" in text
    assert "README inventory waits" in text
    assert "Public scale:" in text
    assert "source-open materials" in text
    assert "Counts are receipt-backed handles" in text
    assert "Evidence classes: body import, subprocess witness" in text
    assert "fixture smoke/schema" in text
    assert (
        "Behavior proof: front_door_status=pass, selected_route_id, state refs, "
        "source_files_mutated=false"
    ) in text
    assert (
        "Safety/evals: Run `microcosm status --card .`. Proof: "
        "`microcosm authority` plus `microcosm workingness`"
    ) in text
    assert (
        "Hiring: Run `microcosm hello .` before the longer tour. "
        "Proof: `microcosm tour --card .`"
    ) in text
    assert (
        "Peer developer: Run `microcosm tour --card .`. "
        "Proof: `microcosm observe .`"
    ) in text
    assert (
        "browser landing: / -> /project/first-screen -> /project/observatory-card"
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
        "safety_evals_engineer": {
            "label": "Safety/evals",
            "first_action": "Run `microcosm status --card .`.",
            "proof": "`microcosm authority` plus `microcosm workingness`",
            "success": "maturity or release readiness",
            "absent": ["Reader branch: Hiring", "Reader branch: Peer developer"],
        },
        "hiring_reviewer": {
            "label": "Hiring",
            "first_action": "Run `microcosm hello .` before the longer tour.",
            "proof": "`microcosm tour --card .`",
            "success": "public card explicitly refuses to make",
            "absent": ["Reader branch: Safety/evals", "Reader branch: Peer developer"],
        },
        "peer_developer": {
            "label": "Peer developer",
            "first_action": "Run `microcosm tour --card .`.",
            "proof": "`microcosm observe .`",
            "success": "without provider calls",
            "absent": ["Reader branch: Safety/evals", "Reader branch: Hiring"],
        },
    }

    for reader_id, assertions in expected.items():
        text = module.first_screen_text_card(card, reader_id=reader_id)

        text.encode("ascii")
        assert text.startswith("Microcosm first screen\n")
        assert "Open card: microcosm hello ." in text
        assert "First run: microcosm tour --card ." in text
        assert f"Reader branch: {assertions['label']}" in text
        assert "  Question: " in text
        assert f"  First action: {assertions['first_action']}" in text
        assert f"  Proof: {assertions['proof']}" in text
        assert assertions["success"] in text
        assert "Authority ceiling:" in text
        assert "Counts are receipt-backed handles" in text
        assert "Evidence classes: body import, subprocess witness" in text
        assert "Behavior proof: front_door_status=pass" in text
        assert "doctrine appears as prevented mistakes" in text
        assert "README inventory waits" in text
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
    assert "doctrine appears as prevented mistakes" in result.stdout
    assert "README inventory waits" in result.stdout
    assert "Evidence classes: body import, subprocess witness" in result.stdout
    assert "Behavior proof: front_door_status=pass" in result.stdout
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
    assert "doctrine appears as prevented mistakes" in result.stdout
    assert "README inventory waits" in result.stdout
    assert "Evidence classes: body import, subprocess witness" in result.stdout
    assert "Behavior proof: front_door_status=pass" in result.stdout
    assert "Reader branch: Safety/evals" in result.stdout
    assert "  First action: Run `microcosm status --card .`." in result.stdout
    assert (
        "  Proof: `microcosm authority` plus `microcosm workingness`"
        in result.stdout
    )
    assert "maturity or release readiness" in result.stdout
    assert "Reader branches:" not in result.stdout
    assert "Reader branch: Hiring" not in result.stdout
    assert "reader_routes" not in result.stdout
    assert "/Users/" not in result.stdout
    assert "src/ai_workflow" not in result.stdout
