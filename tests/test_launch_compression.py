from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import cli
from microcosm_core.validators.launch_compression import validate_launch_compression


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
    return project


def test_launch_compression_validator_proves_one_command_aha(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    out = tmp_path / "launch_compression.json"

    receipt = validate_launch_compression(MICROCOSM_ROOT, project, out, command="pytest")

    assert receipt["status"] == "pass"
    assert receipt["blocking_codes"] == []
    assert all(receipt["assertions"].values())
    assert receipt["one_line_identity"] == "repo -> .microcosm: turn any folder into an inspectable work substrate."
    assert receipt["quickstart_command"] == "microcosm compile ."
    assert receipt["compiled_summary"]["selected_route_id"] == "readme_onboarding_route"
    assert receipt["compiled_summary"]["work_id"] == "work_0001"
    assert receipt["compiled_summary"]["event_count"] > 0
    assert receipt["compiled_summary"]["evidence_count"] > 0
    assert receipt["assertions"]["ten_minute_tour_passes"] is True
    assert receipt["assertions"]["verifier_trace_lens_passes"] is True
    assert receipt["assertions"]["verifier_trace_no_proof_authority"] is True
    assert receipt["assertions"]["verifier_repair_loop_lens_passes"] is True
    assert receipt["assertions"]["verifier_repair_loop_no_proof_authority"] is True
    assert receipt["assertions"]["formal_evidence_cell_lens_passes"] is True
    assert receipt["assertions"]["formal_evidence_cell_no_proof_authority"] is True
    assert receipt["assertions"]["proof_loop_depth_lens_passes"] is True
    assert receipt["assertions"]["proof_loop_depth_no_proof_or_benchmark_authority"] is True
    assert receipt["assertions"]["work_landing_replay_lens_passes"] is True
    assert receipt["assertions"]["work_landing_replay_no_git_authority"] is True
    assert receipt["assertions"]["view_quality_action_map_lens_passes"] is True
    assert receipt["assertions"]["view_quality_action_map_no_private_ui_authority"] is True
    assert receipt["assertions"]["projection_safety_audit_lens_passes"] is True
    assert receipt["assertions"]["projection_safety_audit_no_private_exports"] is True
    assert receipt["assertions"]["projection_drift_control_lens_passes"] is True
    assert receipt["assertions"]["projection_drift_control_no_live_or_source_authority"] is True
    assert receipt["assertions"]["projection_drift_control_rows_validated"] is True
    assert receipt["assertions"]["route_cleanup_contract_lens_passes"] is True
    assert receipt["assertions"]["route_cleanup_contract_no_route_or_source_mutation"] is True
    assert receipt["assertions"]["route_cleanup_contract_rows_validated"] is True
    assert receipt["assertions"]["projection_import_map_lens_passes"] is True
    assert receipt["assertions"]["projection_import_map_no_private_exports_or_auto_import"] is True
    assert receipt["assertions"]["import_projector_contract_lens_passes"] is True
    assert receipt["assertions"]["import_projector_contract_no_private_exports_or_execution"] is True
    assert receipt["assertions"]["import_projector_contract_rows_validated"] is True
    assert receipt["assertions"]["compression_profile_option_surface_lens_passes"] is True
    assert (
        receipt["assertions"][
            "compression_profile_option_surface_no_private_exports_or_execution"
        ]
        is True
    )
    assert receipt["assertions"]["compression_profile_option_surface_rows_validated"] is True
    assert receipt["assertions"]["stripping_guard_lens_passes"] is True
    assert receipt["assertions"]["stripping_guard_no_private_exports_or_release"] is True
    assert receipt["assertions"]["stripping_guard_denies_secret_completeness"] is True
    assert receipt["assertions"]["standards_control_lens_passes"] is True
    assert receipt["assertions"]["standards_control_no_source_or_release_authority"] is True
    assert receipt["assertions"]["standards_control_no_private_exports"] is True
    assert receipt["assertions"]["hook_intervention_coverage_lens_passes"] is True
    assert receipt["assertions"]["hook_intervention_coverage_no_live_authority"] is True
    assert receipt["assertions"]["agent_reliability_replay_gauntlet_lens_passes"] is True
    assert receipt["assertions"]["agent_reliability_replay_gauntlet_no_live_authority"] is True
    assert receipt["assertions"]["repository_benchmark_transaction_lab_lens_passes"] is True
    assert receipt["assertions"]["repository_benchmark_transaction_lab_no_live_authority"] is True
    assert receipt["assertions"]["cold_reader_legibility_scorecard_lens_passes"] is True
    assert (
        receipt["assertions"]["cold_reader_legibility_scorecard_no_release_or_reader_guarantee"]
        is True
    )
    assert receipt["tour_summary"]["time_budget_minutes"] == 10
    assert receipt["tour_summary"]["route_card_count"] == 6
    assert receipt["tour_summary"]["release_authorized"] is False
    assert receipt["trace_summary"]["trace_attempt_count"] == 4
    assert receipt["trace_summary"]["formal_proof_authority"] is False
    assert receipt["repair_loop_summary"]["stage_count"] == 5
    assert receipt["repair_loop_summary"]["transition_count"] == 4
    assert receipt["repair_loop_summary"]["formal_proof_authority"] is False
    assert receipt["formal_evidence_cell_summary"]["cell_count"] == 4
    assert receipt["formal_evidence_cell_summary"]["formal_proof_authority"] is False
    assert receipt["proof_loop_depth_summary"]["gate_count"] == 11
    assert receipt["proof_loop_depth_summary"]["negative_case_count"] == 9
    assert receipt["proof_loop_depth_summary"]["formal_proof_authority"] is False
    assert receipt["proof_loop_depth_summary"]["proof_bodies_exported"] is False
    assert receipt["proof_loop_depth_summary"]["benchmark_score_claim"] is False
    assert receipt["landing_replay_summary"]["lane_count"] == 4
    assert receipt["landing_replay_summary"]["live_git_mutation_authorized"] is False
    assert receipt["view_quality_summary"]["action_row_count"] == 5
    assert receipt["view_quality_summary"]["hot_action_count"] == 4
    assert receipt["view_quality_summary"]["private_screenshot_paths_exported"] is False
    assert receipt["projection_safety_summary"]["projection_row_count"] == 41
    assert receipt["projection_safety_summary"]["omission_receipt_count"] == 41
    assert receipt["projection_safety_summary"]["private_body_export_count"] == 0
    assert receipt["market_prediction_boundary_summary"]["row_count"] == 8
    assert receipt["market_prediction_boundary_summary"]["decision_boundary_count"] == 8
    assert receipt["market_prediction_boundary_summary"]["trading_advice_authorized"] is False
    assert receipt["market_prediction_boundary_summary"]["private_portfolio_exported"] is False
    assert receipt["projection_drift_summary"]["row_count"] == 8
    assert receipt["projection_drift_summary"]["source_ref_count"] == 8
    assert receipt["projection_drift_summary"]["repair_route_count"] == 8
    assert receipt["projection_drift_summary"]["source_authority_claim"] is False
    assert receipt["projection_drift_summary"]["live_route_repair_authorized"] is False
    assert receipt["route_cleanup_summary"]["row_count"] == 8
    assert receipt["route_cleanup_summary"]["owner_route_count"] == 8
    assert receipt["route_cleanup_summary"]["validation_ref_count"] == 8
    assert receipt["route_cleanup_summary"]["route_deletion_authorized"] is False
    assert receipt["route_cleanup_summary"]["generated_region_hand_edit_authorized"] is False
    assert receipt["projection_import_map_summary"]["row_count"] == 6
    assert receipt["projection_import_map_summary"]["stage_count"] == 6
    assert receipt["projection_import_map_summary"]["automated_import_guarantee"] is False
    assert receipt["import_projector_summary"]["row_count"] == 9
    assert receipt["import_projector_summary"]["stage_count"] == 6
    assert receipt["import_projector_summary"]["validation_ref_count"] == 9
    assert receipt["import_projector_summary"]["private_body_export_count"] == 0
    assert receipt["import_projector_summary"]["automated_import_execution_authorized"] is False
    assert receipt["option_surface_summary"]["row_count"] == 6
    assert receipt["option_surface_summary"]["stage_count"] == 6
    assert receipt["option_surface_summary"]["validation_ref_count"] == 6
    assert receipt["option_surface_summary"]["private_body_export_count"] == 0
    assert receipt["option_surface_summary"]["profile_switch_execution_authorized"] is False
    assert receipt["stripping_guard_summary"]["guard_row_count"] == 8
    assert receipt["stripping_guard_summary"]["negative_case_count"] == 8
    assert receipt["stripping_guard_summary"]["private_body_export_count"] == 0
    assert receipt["stripping_guard_summary"]["raw_private_path_export_count"] == 0
    assert receipt["stripping_guard_summary"]["secret_detection_completeness_claim"] is False
    assert receipt["standards_control_summary"]["row_count"] == 8
    assert receipt["standards_control_summary"]["negative_case_count"] == 8
    assert receipt["standards_control_summary"]["validator_receipt_ref_count"] >= 1
    assert receipt["standards_control_summary"]["source_authority_claim_count"] == 0
    assert receipt["standards_control_summary"]["standards_completeness_claim"] is False
    assert receipt["standards_control_summary"]["release_authorized"] is False
    assert receipt["hook_intervention_coverage_summary"]["intervention_row_count"] == 5
    assert receipt["hook_intervention_coverage_summary"]["missing_authority_count"] == 1
    assert receipt["hook_intervention_coverage_summary"]["live_operator_state_read"] is False
    assert receipt["agent_reliability_replay_gauntlet_summary"]["episode_count"] == 11
    assert receipt["agent_reliability_replay_gauntlet_summary"]["blocked_episode_count"] == 9
    assert receipt["agent_reliability_replay_gauntlet_summary"]["live_agent_execution_authorized"] is False
    assert receipt["agent_reliability_replay_gauntlet_summary"]["real_secret_material_exported"] is False
    assert receipt["repository_benchmark_transaction_lab_summary"]["task_count"] == 2
    assert receipt["repository_benchmark_transaction_lab_summary"]["oracle_patch_count"] == 2
    assert receipt["repository_benchmark_transaction_lab_summary"]["fail_to_pass_count"] == 2
    assert receipt["repository_benchmark_transaction_lab_summary"]["pass_to_pass_count"] == 2
    assert (
        receipt["repository_benchmark_transaction_lab_summary"]["live_repo_mutation_authorized"]
        is False
    )
    assert (
        receipt["repository_benchmark_transaction_lab_summary"]["swe_bench_performance_claim"]
        is False
    )
    assert receipt["cold_reader_legibility_scorecard_summary"]["checkpoint_count"] == 6
    assert receipt["cold_reader_legibility_scorecard_summary"]["reader_question_count"] == 5
    assert receipt["cold_reader_legibility_scorecard_summary"]["time_budget_minutes"] == 10
    assert receipt["cold_reader_legibility_scorecard_summary"]["reader_success_guarantee"] is False


def test_cli_launch_compression_command(capsys, tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    out = tmp_path / "launch_compression.json"

    assert cli.main(
        [
            "launch-compression",
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
    assert payload["assertions"]["one_command_quickstart_present"] is True
    assert "pass" not in capsys.readouterr().err
