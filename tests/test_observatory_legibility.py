from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import cli
from microcosm_core import project_substrate
from microcosm_core.validators import observatory_legibility as validator_module
from microcosm_core.validators.observatory_legibility import validate_legibility


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "scratch_project"
    (project / "src/app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text("# Scratch\n\nLocal proof project.\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        "[project]\nname = \"scratch-project\"\nversion = \"0.1.0\"\n",
        encoding="utf-8",
    )
    (project / "src/app/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "tests/test_smoke.py").write_text(
        "from app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    project_substrate.init_project(project)
    project_substrate.index_project(project)
    project_substrate.propose_routes(project)
    project_substrate.explain_route(project, "readme_onboarding_route")
    created = project_substrate.create_work(project, "readme_onboarding_route")
    project_substrate.run_work(project, str(created["work_id"]))
    project_substrate.observe_project(project)
    project_substrate.state_graph(project)
    project_substrate.list_evidence(project)
    return project


def test_observatory_legibility_bounded_tour_blocker_contract() -> None:
    body_floor = {
        "status": "blocked",
        "public_safe_body_material_count": 407,
        "body_text_exported_in_status": False,
        "body_text_exported_in_receipts": False,
        "reader_action": "Open the status card for source-open body floor details.",
        "summary_ref": "microcosm status --card::front_door.source_open_body_import_floor",
        "full_status_ref": "microcosm status::macro_body_import_floor",
        "defect_count": 1,
        "defect_preview": [{"material_id": "example"}],
        "full_defects_ref": "microcosm status::macro_body_import_floor.defects",
    }
    base_tour = {
        "status": "blocked",
        "source_open_body_import_floor": body_floor,
        "route_cards": [{"card_id": f"route_{idx}"} for idx in range(10)],
        "endpoint_path": ["/tour"],
        "anti_claim": "Local tour does not authorize release or provider calls.",
        "front_door_status": {
            "blocking_surface_ids": ["macro_body_import_floor", "spine"],
            "blocking_surface_details": {
                "macro_body_import_floor": {"status": "blocked"},
                "spine": {"status": "blocked"},
            },
            "safe_to_show": {"blocking_surface_ids_visible": True},
        },
    }

    assert validator_module._tour_legibility_visible(base_tour) is True

    unbounded = dict(base_tour)
    unbounded["front_door_status"] = {
        **base_tour["front_door_status"],
        "blocking_surface_ids": ["macro_body_import_floor", "unexpected_surface"],
        "blocking_surface_details": {
            "macro_body_import_floor": {"status": "blocked"},
            "unexpected_surface": {"status": "blocked"},
        },
    }
    assert validator_module._tour_legibility_visible(unbounded) is False


def test_observatory_legibility_validator_exposes_causal_chain(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    out = tmp_path / "observatory_legibility.json"

    receipt = validate_legibility(MICROCOSM_ROOT, project, out, command="pytest")

    assert receipt["status"] == "pass"
    assert receipt["blocking_codes"] == []
    assert receipt["html_assertions"]["root_is_not_raw_json_only"] is True
    assert receipt["html_assertions"]["first_screen_card_endpoint_visible"] is True
    assert receipt["html_assertions"]["observatory_card_endpoint_visible"] is True
    assert receipt["html_assertions"]["first_screen_text_card_visible"] is True
    assert receipt["html_assertions"]["first_screen_reader_branches_visible"] is True
    assert receipt["html_assertions"]["first_screen_reader_route_cards_visible"] is True
    assert (
        receipt["html_assertions"]["first_screen_reader_route_questions_visible"]
        is True
    )
    assert receipt["html_assertions"]["first_screen_reader_exit_cards_visible"] is True

    assert (
        receipt["html_assertions"]["first_screen_demo_to_scale_bridge_visible"]
        is True
    )
    assert (
        receipt["html_assertions"]["first_screen_demo_to_scale_boundary_visible"]
        is True
    )
    assert receipt["html_assertions"]["first_screen_exit_rule_visible"] is True
    assert receipt["html_assertions"]["first_screen_hello_command_visible"] is True
    assert receipt["html_assertions"]["first_screen_authority_ceiling_visible"] is True
    assert receipt["html_assertions"]["raw_observatory_model_not_embedded"] is True
    assert receipt["html_assertions"]["observatory_html_under_first_screen_budget"] is True
    assert (
        receipt["html_assertions"]["observable_first_artifact_slots_visible"]
        is True
    )
    assert receipt["html_assertions"]["causal_chain_section_present"] is True
    assert receipt["html_assertions"]["pattern_binding_visible"] is True
    assert receipt["html_assertions"]["standard_binding_visible"] is True
    assert receipt["html_assertions"]["work_state_history_visible"] is True
    assert receipt["html_assertions"]["evidence_marked_drilldown"] is True
    assert receipt["html_assertions"]["ten_minute_tour_section_present"] is True
    assert (
        receipt["html_assertions"][
            "source_open_body_import_floor_section_present"
        ]
        is True
    )
    assert (
        receipt["html_assertions"]["source_open_body_material_count_visible"]
        is True
    )
    assert (
        receipt["html_assertions"]["source_open_body_text_exclusion_visible"]
        is True
    )
    assert receipt["html_assertions"]["runtime_bridge_section_present"] is True
    assert receipt["html_assertions"]["verifier_trace_lens_section_present"] is True
    assert receipt["html_assertions"]["verifier_repair_loop_lens_section_present"] is True
    assert receipt["html_assertions"]["formal_evidence_cell_lens_section_present"] is True
    assert receipt["html_assertions"]["proof_loop_depth_lens_section_present"] is True
    assert receipt["html_assertions"]["work_landing_replay_lens_section_present"] is True
    assert receipt["html_assertions"]["view_quality_action_map_lens_section_present"] is True
    assert receipt["html_assertions"]["projection_safety_audit_lens_section_present"] is True
    assert receipt["html_assertions"]["projection_drift_control_lens_section_present"] is True
    assert receipt["html_assertions"]["route_cleanup_contract_lens_section_present"] is True
    assert receipt["html_assertions"]["projection_import_map_lens_section_present"] is True
    assert receipt["html_assertions"]["import_projector_contract_lens_section_present"] is True
    assert (
        receipt["html_assertions"][
            "compression_profile_option_surface_lens_section_present"
        ]
        is True
    )
    assert receipt["html_assertions"]["stripping_guard_lens_section_present"] is True
    assert receipt["html_assertions"]["standards_control_lens_section_present"] is True
    assert receipt["html_assertions"]["hook_intervention_coverage_lens_section_present"] is True
    assert receipt["html_assertions"]["agent_reliability_replay_gauntlet_lens_section_present"] is True
    assert receipt["html_assertions"]["repository_benchmark_transaction_lab_lens_section_present"] is True
    assert receipt["html_assertions"]["cold_reader_legibility_scorecard_lens_section_present"] is True
    assert receipt["html_assertions"]["runtime_bridge_endpoints_visible"] is True
    assert receipt["html_assertions"]["projection_status_counts_visible"] is True
    assert receipt["html_assertions"]["closed_intake_cells_visible"] is True
    assert receipt["html_assertions"]["release_ceiling_visible"] is True
    assert receipt["html_assertions"]["private_paths_absent"] is True
    assert receipt["model_assertions"]["runtime_bridge_warning_status_bounded"] is True
    assert receipt["model_assertions"]["authority_map_warning_status_bounded"] is True
    assert (
        receipt["model_assertions"][
            "observatory_card_first_screen_endpoint_present"
        ]
        is True
    )
    assert (
        receipt["model_assertions"]["observable_first_artifact_contract_pass"]
        is True
    )
    assert receipt["model_assertions"]["first_screen_composition_status_pass"] is True
    assert (
        receipt["model_assertions"][
            "first_screen_landing_frame_targets_browser_root"
        ]
        is True
    )
    assert receipt["model_assertions"]["first_screen_landing_handles_present"] is True
    assert (
        receipt["model_assertions"]["first_screen_evidence_class_legend_present"]
        is True
    )
    assert receipt["model_assertions"]["ten_minute_tour_status_pass"] is True
    assert receipt["model_assertions"]["ten_minute_tour_legibility_visible"] is True
    assert receipt["model_assertions"]["source_open_body_import_floor_present"] is True
    assert receipt["model_assertions"]["source_open_body_import_floor_legible"] is True
    assert receipt["model_assertions"]["verifier_trace_lens_status_pass"] is True
    assert receipt["model_assertions"]["verifier_trace_lens_no_proof_authority"] is True
    assert receipt["model_assertions"]["verifier_repair_loop_lens_status_pass"] is True
    assert receipt["model_assertions"]["verifier_repair_loop_lens_no_proof_authority"] is True
    assert receipt["model_assertions"]["formal_evidence_cell_lens_status_pass"] is True
    assert receipt["model_assertions"]["formal_evidence_cell_lens_no_proof_authority"] is True
    assert receipt["model_assertions"]["proof_loop_depth_lens_status_pass"] is True
    assert (
        receipt["model_assertions"]["proof_loop_depth_lens_no_proof_or_benchmark_authority"]
        is True
    )
    assert receipt["model_assertions"]["work_landing_replay_lens_status_pass"] is True
    assert receipt["model_assertions"]["work_landing_replay_lens_no_git_authority"] is True
    assert receipt["model_assertions"]["view_quality_action_map_lens_status_pass"] is True
    assert receipt["model_assertions"]["view_quality_action_map_lens_no_private_ui_authority"] is True
    assert receipt["model_assertions"]["projection_safety_audit_lens_status_pass"] is True
    assert receipt["model_assertions"]["projection_safety_audit_lens_no_private_exports"] is True
    assert receipt["model_assertions"]["projection_drift_control_lens_status_pass"] is True
    assert (
        receipt["model_assertions"]["projection_drift_control_lens_no_live_or_source_authority"]
        is True
    )
    assert receipt["model_assertions"]["projection_drift_control_lens_rows_validated"] is True
    assert receipt["model_assertions"]["route_cleanup_contract_lens_status_pass"] is True
    assert (
        receipt["model_assertions"]["route_cleanup_contract_lens_no_route_or_source_mutation"]
        is True
    )
    assert receipt["model_assertions"]["route_cleanup_contract_lens_rows_validated"] is True
    assert receipt["model_assertions"]["projection_import_map_lens_status_pass"] is True
    assert (
        receipt["model_assertions"]["projection_import_map_lens_no_private_exports_or_auto_import"]
        is True
    )
    assert receipt["model_assertions"]["import_projector_contract_lens_status_pass"] is True
    assert (
        receipt["model_assertions"][
            "import_projector_contract_lens_no_private_exports_or_execution"
        ]
        is True
    )
    assert receipt["model_assertions"]["import_projector_contract_lens_rows_validated"] is True
    assert (
        receipt["model_assertions"][
            "compression_profile_option_surface_lens_status_pass"
        ]
        is True
    )
    assert (
        receipt["model_assertions"][
            "compression_profile_option_surface_no_private_exports_or_execution"
        ]
        is True
    )
    assert (
        receipt["model_assertions"][
            "compression_profile_option_surface_rows_validated"
        ]
        is True
    )
    assert receipt["model_assertions"]["stripping_guard_lens_status_pass"] is True
    assert (
        receipt["model_assertions"]["stripping_guard_lens_no_private_exports_or_release"]
        is True
    )
    assert (
        receipt["model_assertions"]["stripping_guard_lens_denies_secret_and_finance_claims"]
        is True
    )
    assert receipt["model_assertions"]["standards_control_lens_status_pass"] is True
    assert (
        receipt["model_assertions"]["standards_control_lens_no_source_or_release_authority"]
        is True
    )
    assert receipt["model_assertions"]["standards_control_lens_no_private_exports"] is True
    assert receipt["model_assertions"]["hook_intervention_coverage_lens_status_pass"] is True
    assert receipt["model_assertions"]["hook_intervention_coverage_lens_no_live_authority"] is True
    assert receipt["model_assertions"]["agent_reliability_replay_gauntlet_lens_status_pass"] is True
    assert receipt["model_assertions"]["agent_reliability_replay_gauntlet_lens_no_live_authority"] is True
    assert receipt["model_assertions"]["repository_benchmark_transaction_lab_lens_status_pass"] is True
    assert (
        receipt["model_assertions"]["repository_benchmark_transaction_lab_lens_no_live_authority"]
        is True
    )
    assert receipt["model_assertions"]["cold_reader_legibility_scorecard_lens_status_pass"] is True
    assert (
        receipt["model_assertions"][
            "cold_reader_legibility_scorecard_lens_no_release_or_reader_guarantee"
        ]
        is True
    )
    assert receipt["model_assertions"]["runtime_bridge_open_actionable_zero"] is True
    assert receipt["tour_proof"]["tour_id"] == "public_ten_minute_tour"
    assert receipt["tour_proof"]["route_card_count"] == 10
    assert receipt["verifier_trace_proof"]["lens_id"] == "public_verifier_trace_repair_lens"
    assert receipt["verifier_trace_proof"]["trace_attempt_count"] == 4
    assert receipt["verifier_trace_proof"]["formal_proof_authority"] is False
    assert receipt["verifier_repair_loop_proof"]["lens_id"] == "public_verifier_repair_loop_lens"
    assert receipt["verifier_repair_loop_proof"]["stage_count"] == 5
    assert receipt["verifier_repair_loop_proof"]["transition_count"] == 4
    assert receipt["verifier_repair_loop_proof"]["formal_proof_authority"] is False
    assert receipt["formal_evidence_cell_proof"]["lens_id"] == "public_formal_evidence_cell_lens"
    assert receipt["formal_evidence_cell_proof"]["cell_count"] == 4
    assert receipt["formal_evidence_cell_proof"]["formal_proof_authority"] is False
    assert receipt["proof_loop_depth_proof"]["lens_id"] == "public_proof_loop_depth_lens"
    assert receipt["proof_loop_depth_proof"]["gate_count"] == 12
    assert receipt["proof_loop_depth_proof"]["negative_case_count"] == 10
    assert receipt["proof_loop_depth_proof"]["formal_proof_authority"] is False
    assert receipt["proof_loop_depth_proof"]["proof_bodies_exported"] is False
    assert receipt["proof_loop_depth_proof"]["oracle_needed_premise_ids_exported"] is False
    assert receipt["proof_loop_depth_proof"]["benchmark_score_claim"] is False
    assert receipt["work_landing_replay_proof"]["lens_id"] == "public_work_landing_replay_lens"
    assert receipt["work_landing_replay_proof"]["lane_count"] == 4
    assert receipt["work_landing_replay_proof"]["live_git_mutation_authorized"] is False
    assert receipt["view_quality_action_map_proof"]["lens_id"] == "public_view_quality_action_map_lens"
    assert receipt["view_quality_action_map_proof"]["action_row_count"] == 5
    assert receipt["view_quality_action_map_proof"]["hot_action_count"] == 4
    assert receipt["view_quality_action_map_proof"]["private_screenshot_paths_exported"] is False
    assert receipt["projection_safety_audit_proof"]["lens_id"] == "public_projection_safety_audit_lens"
    assert receipt["projection_safety_audit_proof"]["projection_row_count"] == 42
    assert receipt["projection_safety_audit_proof"]["omission_receipt_count"] == 42
    assert receipt["projection_safety_audit_proof"]["private_body_export_count"] == 0
    assert receipt["market_prediction_boundary_proof"]["lens_id"] == (
        "public_market_prediction_evidence_boundary_lens"
    )
    assert receipt["market_prediction_boundary_proof"]["row_count"] == 8
    assert receipt["market_prediction_boundary_proof"]["decision_boundary_count"] == 8
    assert receipt["market_prediction_boundary_proof"]["trading_advice_authorized"] is False
    assert receipt["market_prediction_boundary_proof"]["private_portfolio_exported"] is False
    assert receipt["projection_drift_control_proof"]["lens_id"] == "public_projection_drift_control_lens"
    assert receipt["projection_drift_control_proof"]["row_count"] == 8
    assert receipt["projection_drift_control_proof"]["source_ref_count"] == 8
    assert receipt["projection_drift_control_proof"]["repair_route_count"] == 8
    assert receipt["projection_drift_control_proof"]["source_authority_claim"] is False
    assert receipt["projection_drift_control_proof"]["live_route_repair_authorized"] is False
    assert receipt["route_cleanup_contract_proof"]["lens_id"] == "public_route_cleanup_contract_lens"
    assert receipt["route_cleanup_contract_proof"]["row_count"] == 8
    assert receipt["route_cleanup_contract_proof"]["owner_route_count"] == 8
    assert receipt["route_cleanup_contract_proof"]["validation_ref_count"] == 8
    assert receipt["route_cleanup_contract_proof"]["route_deletion_authorized"] is False
    assert (
        receipt["route_cleanup_contract_proof"]["generated_region_hand_edit_authorized"]
        is False
    )
    assert receipt["projection_import_map_proof"]["row_count"] == 6
    assert receipt["projection_import_map_proof"]["stage_count"] == 6
    assert receipt["projection_import_map_proof"]["automated_import_guarantee"] is False
    assert receipt["import_projector_contract_proof"]["row_count"] == 9
    assert receipt["import_projector_contract_proof"]["stage_count"] == 6
    assert receipt["import_projector_contract_proof"]["validation_ref_count"] == 9
    assert receipt["import_projector_contract_proof"]["private_body_export_count"] == 0
    assert (
        receipt["import_projector_contract_proof"]["automated_import_execution_authorized"]
        is False
    )
    assert receipt["import_projector_contract_proof"]["lossless_projection_claim"] is False
    assert receipt["compression_profile_option_surface_proof"]["row_count"] == 6
    assert receipt["compression_profile_option_surface_proof"]["stage_count"] == 6
    assert receipt["compression_profile_option_surface_proof"]["validation_ref_count"] == 6
    assert receipt["compression_profile_option_surface_proof"]["private_body_export_count"] == 0
    assert (
        receipt["compression_profile_option_surface_proof"][
            "profile_switch_execution_authorized"
        ]
        is False
    )
    assert (
        receipt["compression_profile_option_surface_proof"][
            "automatic_profile_selection_authorized"
        ]
        is False
    )
    assert receipt["stripping_guard_proof"]["lens_id"] == "public_stripping_guard_lens"
    assert receipt["stripping_guard_proof"]["guard_row_count"] == 8
    assert receipt["stripping_guard_proof"]["private_body_export_count"] == 0
    assert receipt["stripping_guard_proof"]["raw_private_path_export_count"] == 0
    assert receipt["stripping_guard_proof"]["secret_detection_completeness_claim"] is False
    assert receipt["standards_control_proof"]["lens_id"] == "public_standards_control_lens"
    assert receipt["standards_control_proof"]["row_count"] == 8
    assert receipt["standards_control_proof"]["negative_case_count"] == 8
    assert receipt["standards_control_proof"]["validator_receipt_ref_count"] >= 1
    assert receipt["standards_control_proof"]["source_authority_claim_count"] == 0
    assert receipt["standards_control_proof"]["standards_completeness_claim"] is False
    assert receipt["standards_control_proof"]["release_authorized"] is False
    assert receipt["hook_intervention_coverage_proof"]["lens_id"] == (
        "public_hook_intervention_coverage_lens"
    )
    assert receipt["hook_intervention_coverage_proof"]["intervention_row_count"] == 5
    assert receipt["hook_intervention_coverage_proof"]["missing_authority_count"] == 1
    assert receipt["hook_intervention_coverage_proof"]["live_operator_state_read"] is False
    assert receipt["agent_reliability_replay_gauntlet_proof"]["lens_id"] == (
        "public_agent_reliability_replay_gauntlet_lens"
    )
    assert receipt["agent_reliability_replay_gauntlet_proof"]["episode_count"] == 11
    assert receipt["agent_reliability_replay_gauntlet_proof"]["blocked_episode_count"] == 9
    assert receipt["agent_reliability_replay_gauntlet_proof"]["live_agent_execution_authorized"] is False
    assert receipt["repository_benchmark_transaction_lab_proof"]["lens_id"] == (
        "public_repository_benchmark_transaction_lab_lens"
    )
    assert receipt["repository_benchmark_transaction_lab_proof"]["task_count"] == 2
    assert receipt["repository_benchmark_transaction_lab_proof"]["oracle_patch_count"] == 2
    assert receipt["repository_benchmark_transaction_lab_proof"]["fail_to_pass_count"] == 2
    assert receipt["repository_benchmark_transaction_lab_proof"]["pass_to_pass_count"] == 2
    assert (
        receipt["repository_benchmark_transaction_lab_proof"]["live_repo_mutation_authorized"]
        is False
    )
    assert receipt["cold_reader_legibility_scorecard_proof"]["lens_id"] == (
        "public_cold_reader_legibility_scorecard_lens"
    )
    assert receipt["cold_reader_legibility_scorecard_proof"]["checkpoint_count"] == 6
    assert receipt["cold_reader_legibility_scorecard_proof"]["reader_question_count"] == 5
    assert receipt["cold_reader_legibility_scorecard_proof"]["time_budget_minutes"] == 10
    assert receipt["cold_reader_legibility_scorecard_proof"]["reader_success_guarantee"] is False
    assert receipt["causal_chain_proof"]["route_id"] == "readme_onboarding_route"
    assert "repo_has_readme" in receipt["causal_chain_proof"]["pattern_binding_ids"]
    assert "reversible_work_transaction" in receipt["causal_chain_proof"]["standard_binding_ids"]
    assert receipt["causal_chain_proof"]["work_id"] == "work_0001"
    assert receipt["causal_chain_proof"]["state_history"] == [
        "created",
        "selected",
        "planned",
        "executed_simulation",
        "closed",
    ]
    assert receipt["runtime_bridge_proof"]["bridge_id"] == "intake_observatory_bridge"
    assert receipt["runtime_bridge_proof"]["open_actionable_cell_count"] == 0
    first_screen_landing = receipt["first_screen_landing_proof"]
    assert first_screen_landing["status"] == "pass"
    assert first_screen_landing["html_endpoint"] == "/"
    assert first_screen_landing["first_screen_endpoint"] == "/project/first-screen"
    assert (
        first_screen_landing["observatory_card_endpoint"]
        == "/project/observatory-card"
    )
    assert first_screen_landing["human_first_command"] == "microcosm hello <project>"
    assert (
        first_screen_landing["shared_first_command"]
        == "microcosm tour --card <project>"
    )
    assert first_screen_landing["browser_landing_reuse"]["default_endpoint"] == "/"
    assert (
        first_screen_landing["browser_landing_reuse"]["source_projection"]
        == "microcosm_core.first_screen_composition.first_screen_text_card"
    )
    assert set(first_screen_landing["reader_route_ids"]) == {
        "safety_evals_engineer",
        "hiring_reviewer",
        "peer_developer",
    }
    assert set(first_screen_landing["evidence_class_ids"]) >= {
        "verified_macro_body_import",
        "external_subprocess_witness",
        "semantic_validator",
        "algorithmic_projection",
        "fixture_schema_replay",
        "fixture_echo_smoke",
    }
    assert "first-screen card" in first_screen_landing["projection_rule"]
    observable_first_artifact = receipt["observable_first_artifact_proof"]
    assert observable_first_artifact["status"] == "pass"
    assert observable_first_artifact["contract_ref"] == (
        "paper_modules/agent_route_observability_runtime.md#observable-first-artifact-contract"
    )
    assert observable_first_artifact["blocked_slot_ids"] == []
    assert set(observable_first_artifact["required_slot_ids"]) == {
        "local_action",
        "selected_route",
        "work_transaction",
        "event_and_evidence_chain",
        "authority_boundary",
        "structural_scale_bridge",
    }
    assert all(
        slot["status"] == "pass"
        for slot in observable_first_artifact["slots"].values()
    )
    assert (
        observable_first_artifact["slots"]["selected_route"]["selected_route_id"]
        == "readme_onboarding_route"
    )
    assert (
        observable_first_artifact["slots"]["work_transaction"][
            "source_files_mutated"
        ]
        is False
    )
    assert (
        observable_first_artifact["slots"]["event_and_evidence_chain"][
            "event_count"
        ]
        > 0
    )
    assert (
        "verified_macro_body_import"
        in observable_first_artifact["slots"]["event_and_evidence_chain"][
            "evidence_class_ids"
        ]
    )
    assert (
        observable_first_artifact["slots"]["authority_boundary"]["safe_to_show"][
            "release_authorized"
        ]
        is False
    )
    assert (
        observable_first_artifact["slots"]["structural_scale_bridge"][
            "public_safe_body_material_count"
        ]
        > 0
    )
    assert (
        observable_first_artifact["slots"]["structural_scale_bridge"][
            "source_open_body_import_floor_legible"
        ]
        is True
    )
    assert observable_first_artifact["slots"]["structural_scale_bridge"][
        "source_open_body_import_floor_status"
    ] in {"pass", "blocked"}
    assert observable_first_artifact["presentation_boundary"] == {
        "browser_or_video_projection_allowed": True,
        "raw_json_first_allowed": False,
        "marketing_page_authorized": False,
        "live_provider_or_operator_trace_authorized": False,
    }
    projection_status_counts = receipt["runtime_bridge_proof"][
        "projection_status_counts"
    ]
    assert projection_status_counts["public_runtime_import_landed"] >= 20
    assert projection_status_counts["runtime_bridge_landed"] == 1
    assert projection_status_counts["self_hosted_status_protocol_landed"] == 1
    assert receipt["runtime_bridge_proof"]["endpoints"]["proof_lab"] == "/proof-lab"


def test_cli_observatory_legibility_command(capsys, tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    out = tmp_path / "observatory_legibility.json"

    assert cli.main(
        [
            "observatory-legibility",
            "--root",
            MICROCOSM_ROOT.as_posix(),
            "--project",
            project.as_posix(),
            "--out",
            out.as_posix(),
        ]
    ) == 0

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["html_sections_present"]["causal_chain"] is True
    assert payload["html_sections_present"]["runtime_bridge"] is True
    assert payload["html_sections_present"]["verifier_trace_lens"] is True
    assert payload["html_sections_present"]["verifier_repair_loop_lens"] is True
    assert payload["html_sections_present"]["formal_evidence_cell_lens"] is True
    assert payload["html_sections_present"]["proof_loop_depth_lens"] is True
    assert payload["html_sections_present"]["view_quality_action_map_lens"] is True
    assert payload["html_sections_present"]["projection_safety_audit_lens"] is True
    assert payload["html_sections_present"]["projection_import_map_lens"] is True
    assert payload["html_sections_present"]["stripping_guard_lens"] is True
    assert payload["html_sections_present"]["standards_control_lens"] is True
    assert payload["html_sections_present"]["hook_intervention_coverage_lens"] is True
    assert payload["html_sections_present"]["agent_reliability_replay_gauntlet_lens"] is True
    assert payload["html_sections_present"]["repository_benchmark_transaction_lab_lens"] is True
    assert payload["html_sections_present"]["cold_reader_legibility_scorecard_lens"] is True
    assert "pass" not in capsys.readouterr().err
