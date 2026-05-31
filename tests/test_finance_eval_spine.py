from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core import cli
import microcosm_core.macro_tools.finance_eval_spine as finance_eval_spine
from microcosm_core.macro_tools.finance_eval_spine import (
    BUNDLE_RESULT_NAME,
    REQUIRED_MODULES,
    SOURCE_IMPORT_CLASS,
    SOURCE_OPEN_BODY_POLICY,
    SOURCE_TO_TARGET_RELATION,
    validate_finance_eval_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FINANCE_EVAL_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/finance_forecast_evaluation_spine/exported_finance_eval_bundle"
)


def _walk_keys(payload: object) -> list[str]:
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


def test_finance_eval_line_count_streams_source_module_input(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "source_module.py"
    empty_source = tmp_path / "empty_source.py"
    missing_source = tmp_path / "missing_source.py"
    source.write_text("one\n\ntwo", encoding="utf-8")
    empty_source.write_text("", encoding="utf-8")
    guarded_paths = {source, empty_source}
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self in guarded_paths:
            raise AssertionError("line count should stream source-module input")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert finance_eval_spine._line_count(source) == 3
    assert finance_eval_spine._line_count(empty_source) == 1
    assert finance_eval_spine._line_count(missing_source) is None


def test_finance_eval_spine_accepts_copied_real_macro_bundle(tmp_path: Path) -> None:
    out_dir = tmp_path / "receipts"

    result = validate_finance_eval_bundle(FINANCE_EVAL_BUNDLE, out_dir, command="pytest")

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_finance_eval_bundle"
    assert result["source_import_class"] == "copied_non_secret_macro_body"
    assert result["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert result["copied_macro_source_count"] == len(REQUIRED_MODULES)
    assert result["real_macro_receipt_count"] == 1
    assert result["counts_as_real_substrate_progress"] is True
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["body_in_receipt"] is False
    assert result["unsafe_payload_bodies_in_receipt"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["source_manifest"]["all_expected_digests_matched"] is True
    assert result["source_manifest"]["all_expected_line_counts_matched"] is True
    copied_rows = [
        row
        for row in result["source_manifest"]["inputs"]
        if row["source_import_class"] == SOURCE_IMPORT_CLASS
    ]
    assert len(copied_rows) == len(REQUIRED_MODULES)
    for row in copied_rows:
        assert row["target_ref"] == (
            "microcosm-substrate/examples/finance_forecast_evaluation_spine/"
            f"exported_finance_eval_bundle/{row['path']}"
        )
        assert row["source_to_target_relation"] == SOURCE_TO_TARGET_RELATION
        assert row["sha256_match"] is True
        assert row["source_sha256"] == row["expected_sha256"]
        assert row["target_sha256"] == row["expected_sha256"]
    assert result["anchor_summary"]["missing_anchor_count"] == 0
    assert result["contract_summary"]["authority_overclaim_count"] == 0
    assert result["module_coverage_summary"]["total_macro_finance_module_count"] == 19
    assert result["module_coverage_summary"]["covered_source_ref_count"] == 19
    assert result["module_coverage_summary"]["imported_public_body_count"] == len(
        REQUIRED_MODULES
    )
    assert result["module_coverage_summary"]["deferred_public_safe_core_count"] == 1
    assert result["module_coverage_summary"]["deferred_public_safe_statistical_count"] == 6
    assert result["module_coverage_summary"]["operational_receipt_only_count"] == 2
    assert result["module_coverage_summary"]["operational_only_count"] == 1
    assert result["module_coverage_summary"]["silent_omission_count"] == 0
    assert result["finance_research_assurance"]["public_safe_non_empty_fixture"] is True
    assert result["finance_research_assurance"]["feed_freshness_state"] == "stale_green_feed"
    assert result["finance_research_assurance"]["scheduled_shell_count"] == 4
    assert result["finance_research_assurance"]["statistical_discipline_sequence"] == [
        "proper_scoring_rules",
        "pairwise_equal_loss",
        "multiple_comparison_guard",
        "review_gated_evolve_implication",
    ]
    assert result["finance_research_assurance"]["evolve_review_gated"] is True
    assert result["finance_research_assurance"]["evolve_auto_apply_allowed"] is False
    quant = result["finance_research_assurance"]["quant_research_experiment_spine"]
    assert quant["schema_version"] == "finance_quant_research_experiment_spine_v0"
    assert quant["status"] == "public_safe_demo_available"
    assert quant["experiment_id"] == "public_quant_research_demo_shadow_forecast_family_5d"
    assert quant["anti_overfit_status"] == "available"
    assert quant["selection_bias_guard"] == (
        "family_level_loss_matrix_plus_bootstrap_spa_mcs_before_review"
    )
    assert quant["model_comparison_output_state"] == "insufficient_evidence"
    assert quant["review_gated"] is True
    assert quant["auto_apply_allowed"] is False
    assert quant["no_advice_enabled"] is True
    assert quant["registry_count"] == 3
    assert quant["negative_control_count"] == 1
    assert quant["negative_or_insufficient_count"] == 3
    assert quant["lineage_status"] == "stress_validated_public_demo"
    assert quant["agenda_status"] == "compiled_public_safe"
    assert quant["agenda_candidate_count"] == 5
    assert quant["agenda_family_count"] == 5
    assert quant["agenda_selected_for_next_test_count"] == 1
    assert quant["agenda_deferred_data_snooping_count"] == 1
    assert quant["agenda_negative_or_control_candidate_count"] == 1
    assert quant["agenda_needs_more_evidence_count"] == 1
    assert quant["agenda_completed_insufficient_evidence_count"] == 1
    assert quant["cycle_status"] == "executed_public_safe_evaluator"
    assert (
        quant["cycle_selected_candidate_id"]
        == "public_quant_agenda_calibration_drift_cross_family_5d"
    )
    assert (
        quant["cycle_pre_analysis_plan_id"]
        == "public_quant_preanalysis_calibration_drift_cross_family_5d_v1"
    )
    assert quant["cycle_result_state"] == "insufficient_evidence"
    assert quant["cycle_registry_new_count"] == 3
    assert (
        quant["cycle_next_selected_candidate_id"]
        == "public_quant_agenda_public_base_rate_calibration_control_5d"
    )
    assert quant["output_state_counts"] == {
        "insufficient_evidence": 2,
        "rejected": 1,
    }
    assert result["operating_picture_gate_summary"]["comparison_key_authority"] == (
        "tools/finance/event_keys.py"
    )
    operating_quant = result["operating_picture_gate_summary"]["quant_research_experiment_spine"]
    assert operating_quant["schema_version"] == "finance_quant_research_experiment_spine_v0"
    assert operating_quant["status"] == "awaiting_evidence"
    assert operating_quant["model_comparison_output_state"] == "awaiting_evidence"
    assert operating_quant["review_gated"] is True
    assert operating_quant["auto_apply_allowed"] is False
    assert operating_quant["no_advice_enabled"] is True
    assert operating_quant["registry_count"] == 3
    assert operating_quant["negative_control_count"] == 1
    assert operating_quant["negative_or_insufficient_count"] == 2
    assert operating_quant["lineage_status"] == "stress_validated_public_demo"
    assert operating_quant["agenda_status"] == "compiled_public_safe"
    assert operating_quant["agenda_candidate_count"] == 5
    assert operating_quant["agenda_family_count"] == 5
    assert operating_quant["agenda_selected_for_next_test_count"] == 1
    assert operating_quant["agenda_deferred_data_snooping_count"] == 1
    assert operating_quant["agenda_negative_or_control_candidate_count"] == 1
    assert operating_quant["agenda_needs_more_evidence_count"] == 1
    assert operating_quant["agenda_completed_insufficient_evidence_count"] == 1
    assert operating_quant["cycle_status"] == "executed_public_safe_evaluator"
    assert (
        operating_quant["cycle_selected_candidate_id"]
        == "public_quant_agenda_calibration_drift_cross_family_5d"
    )
    assert (
        operating_quant["cycle_pre_analysis_plan_id"]
        == "public_quant_preanalysis_calibration_drift_cross_family_5d_v1"
    )
    assert operating_quant["cycle_result_state"] == "insufficient_evidence"
    assert operating_quant["cycle_registry_new_count"] == 3
    assert (
        operating_quant["cycle_next_selected_candidate_id"]
        == "public_quant_agenda_public_base_rate_calibration_control_5d"
    )
    assert operating_quant["output_state_counts"] == {
        "awaiting_evidence": 1,
        "insufficient_evidence": 1,
        "rejected": 1,
    }
    assert all(
        row["observed"] is False
        for row in result["operating_picture_gate_summary"]["false_gate_rows"]
    )
    assert result["authority_ceiling"]["financial_advice_authorized"] is False
    assert result["authority_ceiling"]["optimizer_mutation_authorized"] is False
    assert result["authority_ceiling"]["calculator_weight_mutation_authorized"] is False
    assert result["error_codes"] == []
    assert len(result["public_runtime_refs"]) == len(REQUIRED_MODULES) + 4

    receipt = json.loads((out_dir / BUNDLE_RESULT_NAME).read_text(encoding="utf-8"))
    assert receipt["status"] == "pass"
    assert receipt["body_in_receipt"] is False
    assert "body" not in _walk_keys(receipt)
    encoded = json.dumps(receipt, sort_keys=True)
    assert "body_redacted" not in encoded
    assert "public_replacement" not in encoded
    assert "metadata_only" not in encoded


def test_finance_eval_spine_rejects_finance_authority_overclaim(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FINANCE_EVAL_BUNDLE, bundle)
    contract_path = bundle / "finance_eval_runtime_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["authority_ceiling"]["financial_advice_authorized"] = True
    contract_path.write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = validate_finance_eval_bundle(bundle, tmp_path / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert "AUTHORITY_CEILING_OVERCLAIM" in result["error_codes"]
    assert result["authority_ceiling"]["financial_advice_authorized"] is True
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False


def test_finance_eval_spine_rejects_silent_module_coverage_gap(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FINANCE_EVAL_BUNDLE, bundle)
    contract_path = bundle / "finance_eval_runtime_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["finance_research_assurance"]["module_coverage"] = [
        row
        for row in contract["finance_research_assurance"]["module_coverage"]
        if row["source_ref"] != "tools/finance/build_effective_evidence.py"
    ]
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = validate_finance_eval_bundle(bundle, tmp_path / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert "MODULE_COVERAGE_GAP" in result["error_codes"]
    assert result["module_coverage_summary"]["silent_omission_count"] == 1


def test_finance_eval_spine_rejects_copied_body_without_target_ref(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FINANCE_EVAL_BUNDLE, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0].pop("target_ref", None)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = validate_finance_eval_bundle(bundle, tmp_path / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert "SOURCE_MANIFEST_TARGET_REF_MISMATCH" in result["error_codes"]


def test_finance_eval_spine_rejects_empty_assurance_demo(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FINANCE_EVAL_BUNDLE, bundle)
    assurance_path = bundle / "finance_research_assurance_surface.json"
    assurance = json.loads(assurance_path.read_text(encoding="utf-8"))
    assurance["demonstration_run"]["public_safe_non_empty_fixture"] = False
    assurance["demonstration_run"]["counts"]["pairwise_comparison_count"] = 0
    assurance_path.write_text(
        json.dumps(assurance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = validate_finance_eval_bundle(bundle, tmp_path / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert "ASSURANCE_DEMO_EMPTY_OR_INCOMPLETE" in result["error_codes"]


def test_finance_eval_spine_rejects_quant_research_advice_or_auto_apply(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FINANCE_EVAL_BUNDLE, bundle)
    assurance_path = bundle / "finance_research_assurance_surface.json"
    assurance = json.loads(assurance_path.read_text(encoding="utf-8"))
    quant = assurance["quant_research_experiment_spine"]
    quant["model_comparison_discipline"]["winner_language_allowed"] = True
    quant["oracle_evolve_bridge"]["auto_apply_allowed"] = True
    quant["experiment_registry"][0]["model_comparison"]["winner_language_allowed"] = True
    quant["experiment_registry"][1]["oracle_evolve_implication"]["auto_apply_allowed"] = True
    assurance_path.write_text(
        json.dumps(assurance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = validate_finance_eval_bundle(bundle, tmp_path / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert "QUANT_RESEARCH_SPINE_INCOMPLETE" in result["error_codes"]
    assert "QUANT_RESEARCH_LINEAGE_INCOMPLETE" in result["error_codes"]


def test_finance_eval_spine_rejects_single_quant_demo_without_stress_case(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FINANCE_EVAL_BUNDLE, bundle)
    assurance_path = bundle / "finance_research_assurance_surface.json"
    assurance = json.loads(assurance_path.read_text(encoding="utf-8"))
    quant = assurance["quant_research_experiment_spine"]
    quant["experiment_registry"] = quant["experiment_registry"][:1]
    quant["lineage_summary"]["registry_count"] = 1
    quant["lineage_summary"]["negative_control_count"] = 0
    quant["lineage_summary"]["negative_or_insufficient_count"] = 1
    quant["lineage_summary"]["lineage_status"] = "single_demo_only"
    assurance_path.write_text(
        json.dumps(assurance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = validate_finance_eval_bundle(bundle, tmp_path / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert "QUANT_RESEARCH_LINEAGE_INCOMPLETE" in result["error_codes"]


def test_finance_eval_spine_rejects_quant_agenda_without_deferred_or_control_candidate(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FINANCE_EVAL_BUNDLE, bundle)
    assurance_path = bundle / "finance_research_assurance_surface.json"
    assurance = json.loads(assurance_path.read_text(encoding="utf-8"))
    agenda = assurance["quant_research_experiment_spine"]["research_agenda"]
    agenda["candidate_agenda"] = [
        row
        for row in agenda["candidate_agenda"]
        if row["agenda_state"] == "selected_for_next_test"
    ]
    agenda["search_budget"]["candidate_count"] = 1
    agenda["search_budget"]["family_count"] = 1
    agenda["search_budget"]["deferred_data_snooping_count"] = 0
    agenda["search_budget"]["negative_or_control_candidate_count"] = 0
    agenda["search_budget"]["needs_more_evidence_count"] = 0
    assurance_path.write_text(
        json.dumps(assurance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = validate_finance_eval_bundle(bundle, tmp_path / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert "QUANT_RESEARCH_AGENDA_INCOMPLETE" in result["error_codes"]


def test_cli_finance_eval_spine_smoke(
    tmp_path: Path, capsys
) -> None:
    out_dir = tmp_path / "receipts"

    status = cli.main(
        [
            "finance-eval-spine",
            "validate-finance-eval-bundle",
            "--input",
            str(FINANCE_EVAL_BUNDLE),
            "--out",
            str(out_dir),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["status"] == "pass"
    assert payload["command"].startswith("microcosm finance-eval-spine")
    assert payload["copied_macro_source_count"] == len(REQUIRED_MODULES)
    assert (out_dir / BUNDLE_RESULT_NAME).is_file()
