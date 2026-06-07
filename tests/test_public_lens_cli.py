from __future__ import annotations

import json
from pathlib import Path

import pytest

from microcosm_core import cli
from microcosm_core.runtime_shell import (
    PROOF_LAB_RECEIPT_REF,
    SOURCE_OPEN_BODY_POLICY,
    VERIFIER_EXECUTION_LENS_COMMAND,
    VERIFIER_EXECUTION_RECEIPT_REF,
)

MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "command",
    [command for command, _ in cli.PUBLIC_LENS_COMMAND_HELP],
)
def test_cli_public_lens_commands_accept_card_alias(
    command: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main([command, "--card"])

    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload["schema_version"], str)
    assert payload["schema_version"]
    assert payload["status"] in {"pass", "blocked"}
    if payload["status"] == "pass":
        assert status == 0
    else:
        assert status in {0, 1}


def test_cli_prediction_lens_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["prediction-lens"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_prediction_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm prediction-lens"
    assert payload["endpoint"] == "/prediction"
    assert payload["organ_id"] == "prediction_oracle_reconciliation"
    cp2_rows = next(
        row for row in payload["mechanics"] if row["mechanic_id"] == "cp2_prediction_rows"
    )
    assert cp2_rows["count"] == len(payload["reconciliation_rows"])
    assert payload["authority_ceiling"]["financial_advice_authorized"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_prediction_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload
    assert "public_replacement_refs" not in payload


def test_cli_market_prediction_boundary_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["market-boundary"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert (
        payload["schema_version"]
        == "microcosm_public_market_prediction_evidence_boundary_lens_v1"
    )
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm market-boundary"
    assert payload["endpoint"] == "/market-boundary"
    assert payload["boundary_summary"]["row_count"] == 8
    assert payload["boundary_summary"]["decision_boundary_count"] == 8
    assert payload["boundary_summary"]["trading_advice_authorized_count"] == 0
    assert payload["boundary_summary"]["private_portfolio_export_count"] == 0
    assert payload["authority_ceiling"]["synthetic_fixture_only"] is True
    assert payload["authority_ceiling"]["live_market_data_authorized"] is False
    assert payload["authority_ceiling"]["investment_recommendation_authorized"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert (
        payload["payload_boundary"]["boundary_id"]
        == "public_market_prediction_evidence_boundary_lens"
    )
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in payload["boundary_rows"]
    )
    assert payload["safe_to_show"]["decision_policy_not_trading_advice"] is True
    assert "body_redacted" not in payload


def test_cli_corpus_lens_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["corpus-lens"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_corpus_readiness_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm corpus-lens"
    assert payload["endpoint"] == "/corpus"
    assert payload["organ_id"] == "corpus_readiness_mathlib_absence_gate"
    assert payload["corpus_summary"]["corpus_count"] == 7
    assert payload["corpus_summary"]["mathlib_lake_project_import_available"] is False
    assert payload["consumer_gate"]["allowed_case_ids"] == [
        "miniF2F_lean3_translation_smoke_allowed"
    ]
    assert payload["authority_ceiling"]["mathlib_dependent_proof_authority"] is False


def test_cli_trace_lens_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["trace-lens"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_verifier_trace_repair_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm trace-lens"
    assert payload["endpoint"] == "/trace"
    assert payload["repair_summary"]["attempt_count"] == 4
    assert payload["authority_ceiling"]["formal_proof_authority"] is False
    assert payload["authority_ceiling"]["proof_bodies_exported"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_verifier_trace_repair_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "source-open public payload-boundary read-model" in payload["anti_claim"]
    assert "metadata-only public read-model" not in payload["anti_claim"]
    assert "body_redacted" not in payload


def test_cli_repair_loop_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["repair-loop"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_verifier_repair_loop_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm repair-loop"
    assert payload["endpoint"] == "/repair-loop"
    assert payload["repair_loop_summary"]["stage_count"] == 5
    assert payload["repair_loop_summary"]["transition_count"] == 4
    assert payload["authority_ceiling"]["formal_proof_authority"] is False
    assert payload["authority_ceiling"]["proof_bodies_exported"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_verifier_repair_loop_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload


def test_cli_evidence_cells_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["evidence-cells"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_formal_evidence_cell_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm evidence-cells"
    assert payload["endpoint"] == "/evidence-cells"
    assert payload["resolver_summary"]["cell_count"] == 4
    assert payload["resolver_summary"]["present_cell_count"] == 2
    assert payload["authority_ceiling"]["formal_proof_authority"] is False
    assert payload["authority_ceiling"]["proof_bodies_exported"] is False
    assert payload["authority_ceiling"]["private_source_refs_exported"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_formal_evidence_cell_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload


def test_cli_proof_loop_depth_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["proof-loop-depth"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_proof_loop_depth_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm proof-loop-depth"
    assert payload["endpoint"] == "/proof-loop-depth"
    assert payload["proof_loop_summary"]["gate_count"] == 12
    assert payload["proof_loop_summary"]["proof_lab_route_component_count"] == 9
    assert payload["proof_loop_summary"]["proof_lab_execution_transition_count"] == 6
    assert payload["first_screen_proof_lab"]["receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert payload["proof_loop_summary"]["proof_body_export_count"] == 0
    assert payload["authority_ceiling"]["formal_proof_authority"] is False
    assert payload["authority_ceiling"]["benchmark_score_claim"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_proof_loop_depth_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload


@pytest.mark.parametrize(
    ("command", "example", "boundary_text"),
    [
        (
            "evidence-cells",
            "microcosm evidence-cells --card .",
            "resolves proof-language claims to public evidence-cell metadata",
        ),
        (
            "proof-loop-depth",
            "microcosm proof-loop-depth --card .",
            "maps the public formal-math gate chain and receipt refs as metadata",
        ),
    ],
)
def test_cli_formal_public_lens_help_names_reader_route_and_boundary(
    command: str,
    example: str,
    boundary_text: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main([command, "--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "Formal-methods reader route:" in output
    assert example in output
    assert boundary_text in output
    assert "It does not run Lean/Lake" in output
    assert "authorize" in output
    assert "release" in output


def test_cli_verifier_lab_execution_spine_lens_smoke(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(["verifier-lab-execution-spine-lens"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert (
        payload["schema_version"]
        == "microcosm_public_verifier_lab_execution_spine_lens_v1"
    )
    assert payload["status"] == "pass"
    assert payload["command"] == VERIFIER_EXECUTION_LENS_COMMAND
    assert payload["endpoint"] == "/verifier-lab-execution-spine"
    assert payload["source_receipt_ref"] == VERIFIER_EXECUTION_RECEIPT_REF
    assert payload["execution_summary"]["transition_count"] == 6
    assert payload["execution_summary"]["accepted_transition_count"] == 4
    assert payload["execution_summary"]["cp2_downstream_effect_count"] == 1
    assert payload["execution_summary"]["evolve_accepted_count"] == 1
    assert payload["source_statuses"]["source_open_body_imports"] == "pass"
    assert payload["source_open_body_imports"]["body_material_count"] == 5
    assert payload["source_open_body_imports"]["body_in_receipt"] is False
    assert payload["source_open_body_material_count"] == 5
    assert payload["body_copied_material_count"] == 5
    assert payload["authority_ceiling"]["external_tool_witness_only"] is True
    assert payload["authority_ceiling"]["formal_proof_authority"] is False
    assert payload["payload_boundary"]["boundary_id"] == (
        "public_verifier_lab_execution_spine_lens"
    )
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload


def test_cli_landing_replay_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["landing-replay"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_work_landing_replay_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm landing-replay"
    assert payload["endpoint"] == "/landing-replay"
    assert payload["replay_summary"]["lane_count"] == 4
    assert payload["replay_summary"]["validation_before_commit_attempt_required"] is True
    assert payload["authority_ceiling"]["live_git_mutation_authorized"] is False
    assert payload["authority_ceiling"]["broad_checkpoint_authorized"] is False


def test_cli_view_quality_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["view-quality"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_view_quality_action_map_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm view-quality"
    assert payload["endpoint"] == "/view-quality"
    assert payload["action_summary"]["action_row_count"] == 5
    assert payload["action_summary"]["hot_action_count"] == 4
    assert payload["authority_ceiling"]["private_screenshot_paths_exported"] is False
    assert payload["authority_ceiling"]["live_browser_control_authorized"] is False


def test_cli_projection_safety_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["projection-safety"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_projection_safety_audit_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm projection-safety"
    assert payload["endpoint"] == "/projection-safety"
    assert payload["projection_summary"]["omission_receipt_count"] == 42
    assert payload["projection_summary"]["private_body_export_count"] == 0
    assert payload["projection_summary"]["proof_body_export_count"] == 0
    assert payload["authority_ceiling"]["source_mutation_authorized"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_projection_safety_audit_lens"
    assert payload["payload_boundary"]["source_open_default"] is True


def test_cli_projection_drift_control_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["drift-control"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_projection_drift_control_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm drift-control"
    assert payload["endpoint"] == "/drift-control"
    assert payload["drift_summary"]["row_count"] == 8
    assert payload["drift_summary"]["source_authority_claim_count"] == 0
    assert payload["drift_summary"]["live_repair_authorized_count"] == 0
    assert payload["drift_summary"]["public_drilldown_ref_count"] == 8
    assert payload["drift_summary"]["unsafe_payload_body_export_count"] == 0
    assert payload["authority_ceiling"]["source_open_drilldown_contract"] is True
    assert payload["authority_ceiling"]["live_route_repair_authorized"] is False
    assert payload["safe_to_show"]["repair_is_route_drilldown_only"] is True
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_projection_drift_control_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload
    encoded = json.dumps(payload, sort_keys=True)
    assert "public_replacement_ref" not in encoded


def test_cli_spatial_simulation_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["spatial-simulation"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert (
        payload["schema_version"]
        == "microcosm_public_spatial_world_model_counterfactual_simulation_replay_lens_v1"
    )
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm spatial-simulation"
    assert payload["endpoint"] == "/spatial-simulation"
    assert payload["simulation_summary"]["replay_count"] == 6
    assert payload["simulation_summary"]["private_video_export_count"] == 0
    assert payload["simulation_summary"]["live_operation_authorized_count"] == 0
    assert payload["authority_ceiling"]["private_video_exported"] is False
    assert payload["authority_ceiling"]["release_authorized"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert (
        payload["payload_boundary"]["boundary_id"]
        == "public_spatial_world_model_counterfactual_simulation_replay_lens"
    )
    encoded = json.dumps(payload, sort_keys=True)
    assert "body_redacted" not in encoded
    assert "private_state_scan" not in encoded


def test_cli_route_cleanup_contract_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["route-cleanup"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_route_cleanup_contract_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm route-cleanup"
    assert payload["endpoint"] == "/route-cleanup"
    assert payload["cleanup_summary"]["row_count"] == 8
    assert payload["cleanup_summary"]["owner_route_count"] == 8
    assert payload["cleanup_summary"]["route_deletion_authorized_count"] == 0
    assert payload["cleanup_summary"]["generated_region_hand_edit_authorized_count"] == 0
    assert payload["cleanup_summary"]["public_drilldown_ref_count"] == 8
    assert payload["cleanup_summary"]["unsafe_payload_body_export_count"] == 0
    assert payload["authority_ceiling"]["source_open_drilldown_contract"] is True
    assert payload["authority_ceiling"]["route_deletion_authorized"] is False
    assert payload["safe_to_show"]["route_cleanup_is_source_open_drilldown_contract"] is True
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_route_cleanup_contract_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload
    encoded = json.dumps(payload, sort_keys=True)
    assert "public_replacement_ref" not in encoded


def test_cli_projection_import_map_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    for argv in (["projection-import-map"], ["projection-import-map", "--card"]):
        status = cli.main(argv)

        payload = json.loads(capsys.readouterr().out)
        assert status == 0
        assert payload["schema_version"] == "microcosm_public_projection_import_map_lens_v1"
        assert payload["status"] == "pass"
        assert payload["command"] == "microcosm projection-import-map"
        assert payload["endpoint"] == "/projection-import-map"
        assert payload["map_summary"]["row_count"] == 8
        assert payload["map_summary"]["stage_count"] == 6
        assert payload["map_summary"]["private_body_export_count"] == 0
        assert payload["authority_ceiling"]["automated_import_guarantee"] is False
        assert (
            payload["payload_boundary"]["boundary_id"]
            == "public_projection_import_map_lens"
        )
        assert payload["unsafe_payload_bodies_in_receipt"] is False


def test_cli_import_projector_contract_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    for argv in (["import-projector"], ["import-projector", "--card"]):
        status = cli.main(argv)

        payload = json.loads(capsys.readouterr().out)
        assert status == 0
        assert (
            payload["schema_version"]
            == "microcosm_public_import_projector_contract_lens_v1"
        )
        assert payload["status"] == "pass"
        assert payload["command"] == "microcosm import-projector"
        assert payload["endpoint"] == "/import-projector"
        assert payload["projector_summary"]["row_count"] == 9
        assert payload["projector_summary"]["stage_count"] == 6
        assert payload["projector_summary"]["private_body_export_count"] == 0
        assert payload["authority_ceiling"]["automated_import_execution_authorized"] is False
        assert payload["authority_ceiling"]["lossless_projection_claim"] is False
        assert (
            payload["payload_boundary"]["boundary_id"]
            == "public_import_projector_contract_lens"
        )
        assert payload["unsafe_payload_bodies_in_receipt"] is False


def test_cli_option_surface_lens_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["option-surface-lens"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_compression_profile_option_surface_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm option-surface-lens"
    assert payload["endpoint"] == "/option-surface-lens"
    assert payload["option_surface_summary"]["row_count"] == 6
    assert payload["option_surface_summary"]["stage_count"] == 6
    assert payload["option_surface_summary"]["private_body_export_count"] == 0
    assert payload["authority_ceiling"]["profile_switch_execution_authorized"] is False
    assert payload["authority_ceiling"]["automatic_profile_selection_authorized"] is False
    assert payload["authority_ceiling"]["lossless_projection_claim"] is False
    assert (
        payload["payload_boundary"]["boundary_id"]
        == "public_compression_profile_option_surface_lens"
    )
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in payload["option_rows"]
    )
    encoded = json.dumps(payload, sort_keys=True)
    assert "source_cell_redacted_flag" not in encoded
    assert "body_redacted" not in encoded
    assert "body_copied" not in encoded


def test_cli_stripping_guard_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["stripping-guard"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_private_stripping_guard_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm stripping-guard"
    assert payload["endpoint"] == "/stripping-guard"
    assert payload["guard_summary"]["guard_row_count"] == 8
    assert payload["guard_summary"]["private_body_export_count"] == 0
    assert payload["authority_ceiling"]["secret_detection_completeness_claim"] is False
    assert payload["authority_ceiling"]["financial_advice_authorized"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_stripping_guard_lens"
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in payload["guard_rows"]
    )


def test_cli_smoke_lenses_do_not_rewrite_tracked_receipt_timestamps(
    capsys: pytest.CaptureFixture[str],
) -> None:
    receipt_paths = [
        MICROCOSM_ROOT
        / "receipts/runtime_shell/public_agent_reliability_replay_gauntlet_lens.json",
        MICROCOSM_ROOT
        / "receipts/runtime_shell/public_repository_benchmark_transaction_lab_lens.json",
        MICROCOSM_ROOT
        / "receipts/runtime_shell/public_stripping_guard_lens.json",
        MICROCOSM_ROOT
        / "receipts/runtime_shell/public_cold_reader_legibility_scorecard_lens.json",
    ]
    before = {path: path.read_text(encoding="utf-8") for path in receipt_paths}
    after: dict[Path, str] = {}

    try:
        for command in (
            "replay-gauntlet",
            "benchmark-lab",
            "stripping-guard",
            "legibility-scorecard",
        ):
            status = cli.main([command])
            payload = json.loads(capsys.readouterr().out)
            assert status == 0
            assert payload["status"] == "pass"
        after = {path: path.read_text(encoding="utf-8") for path in receipt_paths}
    finally:
        for path, text in before.items():
            if path.read_text(encoding="utf-8") != text:
                path.write_text(text, encoding="utf-8")

    assert after == before


def test_cli_standards_control_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["standards-control"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_standards_control_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm standards-control"
    assert payload["endpoint"] == "/standards-control"
    assert payload["standards_summary"]["standards_control_row_count"] == 8
    assert payload["standards_summary"]["negative_case_count"] == 8
    assert payload["standards_summary"]["private_body_export_count"] == 0
    assert payload["standards_summary"]["source_authority_claim_count"] == 0
    assert payload["authority_ceiling"]["standards_registry_source_authority"] is False
    assert payload["authority_ceiling"]["standards_completeness_claim"] is False
    assert payload["authority_ceiling"]["release_authorized"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_standards_control_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in payload["standards_rows"]
    )


def test_cli_hook_coverage_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["hook-coverage"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_hook_intervention_coverage_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm hook-coverage"
    assert payload["endpoint"] == "/hook-coverage"
    assert payload["coverage_summary"]["intervention_row_count"] == 5
    assert payload["coverage_summary"]["missing_authority_count"] == 1
    assert payload["coverage_summary"]["hook_shadow_case_count"] == 6
    assert payload["coverage_summary"]["hook_shadow_repair_class_count"] == 6
    assert payload["coverage_summary"]["live_state_read_denial_count"] == 1
    assert payload["authority_ceiling"]["live_operator_state_read"] is False
    assert payload["authority_ceiling"]["provider_payload_read"] is False
    assert payload["authority_ceiling"]["live_task_ledger_mutation_authorized"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_hook_intervention_coverage_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in payload["intervention_rows"]
    )


def test_cli_replay_gauntlet_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["replay-gauntlet"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_agent_reliability_replay_gauntlet_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm replay-gauntlet"
    assert payload["endpoint"] == "/replay-gauntlet"
    assert payload["coverage_summary"]["episode_count"] == 11
    assert payload["coverage_summary"]["blocked_episode_count"] == 9
    assert payload["authority_ceiling"]["live_agent_execution_authorized"] is False
    assert payload["authority_ceiling"]["complete_security_claim"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_agent_reliability_replay_gauntlet_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload


def test_cli_benchmark_lab_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["benchmark-lab"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_repository_benchmark_transaction_lab_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm benchmark-lab"
    assert payload["endpoint"] == "/benchmark-lab"
    assert payload["scorecard"]["task_count"] == 2
    assert payload["scorecard"]["oracle_patch_count"] == 2
    assert payload["scorecard"]["fail_to_pass_count"] == 2
    assert payload["scorecard"]["pass_to_pass_count"] == 2
    assert payload["authority_ceiling"]["live_repo_mutation_authorized"] is False
    assert payload["authority_ceiling"]["swe_bench_performance_claim"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_repository_benchmark_transaction_lab_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload


def test_cli_legibility_scorecard_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["legibility-scorecard"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_cold_reader_legibility_scorecard_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm legibility-scorecard"
    assert payload["endpoint"] == "/legibility-scorecard"
    assert payload["scorecard"]["checkpoint_count"] == 6
    assert payload["scorecard"]["reader_question_count"] == 5
    assert payload["scorecard"]["time_budget_minutes"] == 10
    assert payload["scorecard"]["not_score_based_progress"] is True
    card_first_commands = [
        "microcosm hello <project>",
        "microcosm tour --card <project>",
        "microcosm status --card <project>",
        "microcosm authority --card",
        "microcosm workingness --card",
        "microcosm legibility-scorecard",
    ]
    assert payload["card_first_entry_path"]["commands"] == card_first_commands
    assert payload["required_commands"][:6] == card_first_commands
    pre_install_probe = payload["card_first_entry_path"]["pre_install_probe"]
    assert pre_install_probe["command"] == "./bootstrap.sh"
    assert pre_install_probe["dry_run_command"] == "./bootstrap.sh --dry-run"
    assert pre_install_probe["receipt_ref"] == ".microcosm/cold_clone_probe.json"
    assert pre_install_probe["runs_before_install"] is True
    assert pre_install_probe["writes_ignored_local_state"] is True
    assert "Run ./bootstrap.sh first" in payload["card_first_entry_path"][
        "reader_rule"
    ]
    assert "microcosm tour <project>" not in payload["required_commands"]
    assert "microcosm authority" not in payload["required_commands"]
    bounded_observatory_command = (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 "
        "--max-requests 7"
    )
    assert bounded_observatory_command in payload["required_commands"]
    assert bounded_observatory_command in payload["card_first_entry_path"]["drilldown_after"]
    assert "microcosm serve <project>" not in payload["required_commands"]
    first_run = {
        row["question_id"]: row for row in payload["reader_question_rows"]
    }["first_run"]
    assert first_run["pre_install_probe_command"] == "./bootstrap.sh"
    assert first_run["proof_command"] == "microcosm hello <project>"
    assert first_run["proof_command_sequence"] == [
        "microcosm hello <project>",
        "microcosm tour --card <project>",
    ]
    checkpoint_commands = {
        row["checkpoint_id"]: row["command"] for row in payload["checkpoint_rows"]
    }
    assert checkpoint_commands["entry_path_visible"] == (
        "microcosm tour --card <project>"
    )
    assert checkpoint_commands["authority_ceiling_visible"] == (
        "microcosm authority --card"
    )
    assert checkpoint_commands["observatory_not_decorative"] == bounded_observatory_command
    assert payload["authority_ceiling"]["release_authorized"] is False
    assert payload["authority_ceiling"]["score_based_progress_authority"] is False
    assert payload["authority_ceiling"]["reader_success_guarantee"] is False
