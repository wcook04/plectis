from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.batch11_saturation_engines_capsule import (
    AUTHORITY_CEILING,
    CASE_VERDICT_AUTHORITY,
    EXPECTED_MECHANISMS,
    EXPECTED_MODULE_IDS,
    EXPECTED_NEGATIVE_CASES,
    MECHANISM_BINDING_DISPOSITIONS,
    NEGATIVE_CASE_COMPUTED_PATHS,
    NEGATIVE_CASE_PROBE_SCHEMA,
    TIER_B_MECHANISMS,
    evaluate_negative_case,
    result_card,
    run,
    run_batch11_saturation_engines_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch11_saturation_engines_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch11_saturation_engines_capsule/exported_batch11_saturation_engines_capsule_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _copy_public_fixture(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/batch11_saturation_engines_capsule",
        public_root / "examples/batch11_saturation_engines_capsule",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/batch11_saturation_engines_capsule",
        public_root / "fixtures/first_wave/batch11_saturation_engines_capsule",
    )
    return public_root / "fixtures/first_wave/batch11_saturation_engines_capsule/input"


def _public_bundle_for_fixture(fixture: Path) -> Path:
    return (
        fixture.parents[3]
        / "examples/batch11_saturation_engines_capsule/exported_batch11_saturation_engines_capsule_bundle"
    )


def test_batch11_saturation_engines_capsule_runs_all_mechanisms(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch11_saturation_engines_capsule",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/batch11_saturation_engines_capsule_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True

    exercise = result["exercise"]
    assert exercise["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert set(exercise["mechanism_ids"]) == set(EXPECTED_MECHANISMS)
    assert exercise["passed_mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert exercise["tier_b_controller_verification_count"] == len(TIER_B_MECHANISMS)
    assert exercise["copied_macro_source_module_count"] == len(EXPECTED_MODULE_IDS)

    by_mechanism = {row["mechanism_id"]: row for row in exercise["mechanisms"]}
    assert by_mechanism["run_affinity_session_scorer"]["stale_terminal_refused"] is True
    assert by_mechanism["calculator_cluster_insight_derivation"]["zero_bucket_no_fake_share"] is True
    assert by_mechanism["std_python_delta_enforcement_ratchet_gate"]["new_violation_blocks"] is True
    assert by_mechanism["projection_secret_scan"]["token_blocks"] is True
    assert by_mechanism["stockgrid_flow_multisource_merge_unit_normalizer"]["normalized_flow_usd"] == 2_400_000
    assert by_mechanism["stockgrid_flow_multisource_merge_unit_normalizer"]["missing_flow_no_silent_zero"] is True
    assert by_mechanism["macro_regime_board_bucketing_zscore_engine"]["unknown_routes_other"] is True
    assert by_mechanism["macro_regime_board_bucketing_zscore_engine"]["source_body_invoked"] is True
    assert by_mechanism["macro_regime_board_bucketing_zscore_engine"]["source_functions_invoked"] == [
        "system/lib/quant_presentation_mart.py::_macro_lifecycle_by_slug",
        "system/lib/quant_presentation_mart.py::_macro_regime_board",
    ]
    assert by_mechanism["macro_regime_board_bucketing_zscore_engine"]["inflation_vintage_status"] == "available"
    assert by_mechanism["macro_regime_board_bucketing_zscore_engine"]["inflation_release_calendar_status"] == "available"
    assert by_mechanism["macro_regime_board_bucketing_zscore_engine"]["inflation_latest_observation_date"] == "2026-05-15"
    assert by_mechanism["macro_regime_board_bucketing_zscore_engine"]["inflation_realtime_start"] == "2026-05-16"
    assert by_mechanism["macro_regime_board_bucketing_zscore_engine"]["other_vintage_status"] == "missing_from_feed_artifact"
    assert by_mechanism["macro_regime_board_bucketing_zscore_engine"]["other_release_calendar_status"] == "missing_from_feed_artifact"
    assert by_mechanism["macro_regime_board_bucketing_zscore_engine"]["other_latest_observation_date"] is None
    assert by_mechanism["frontend_nav_graph_wayfinding_engine"]["unreachable_returns_blocker"] is True
    assert by_mechanism["agent_session_diagnostic_lens_engine"]["no_nav_verbs_no_false_ladder_skip"] is True
    assert by_mechanism["demo_take_story_coverage_audit"]["missing_anchors_lowers_score"] is True

    assert exercise["integrity_summary"]["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert exercise["integrity_summary"]["computed_negative_case_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert exercise["integrity_summary"]["fixture_probe_computed_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert exercise["integrity_summary"]["fixture_verdict_echo_risk_count"] == 0
    matrix = {row["mechanism_id"]: row for row in exercise["integrity_matrix"]}
    assert set(matrix) == set(EXPECTED_MECHANISMS)
    for mechanism_id, row in matrix.items():
        assert row["binding_disposition"] == MECHANISM_BINDING_DISPOSITIONS[mechanism_id]
        assert row["negative_verdict_authority"] == CASE_VERDICT_AUTHORITY
        assert row["fixture_verdict_echo_risk"] is False
        assert row["negative_result_computed"] is True
        assert row["negative_cases"][0]["mechanism_computed_value"] is True
        assert row["negative_cases"][0]["fixture_computed_value"] is True
        assert row["negative_cases"][0]["fixture_probe_status"] == "pass"
        assert row["negative_cases"][0]["fixture_probe_source"] == "negative_case_fixture_probe_input"
        assert row["negative_cases"][0]["fixture_probe_input_digest"]
        if mechanism_id == "macro_regime_board_bucketing_zscore_engine":
            observed = row["negative_cases"][0]["fixture_probe_observed"]
            assert observed["source_body_invoked"] is True
            assert observed["vintage_status"] == "missing_from_feed_artifact"
            assert observed["release_calendar_status"] == "missing_from_feed_artifact"
        assert row["source_refs"]
        assert row["source_evidence"]
        assert row["body_in_receipt"] is False
    assert result["body_in_receipt"] is False


def test_batch11_saturation_engines_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch11_saturation_engines_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch11_saturation_engines_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch11_saturation_engines_capsule_bundle"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["source_module_manifest"]["module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["exercise"]["copied_macro_source_module_count"] == len(EXPECTED_MODULE_IDS)
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch11_source_modules_are_exact_or_declared_public_refactors() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == len(EXPECTED_MODULE_IDS)
    refactors = {
        row["source_ref"]: row
        for row in manifest["source_faithful_public_refactors"]
    }
    assert set(refactors) == {
        "tools/meta/dissemination/portability_gate.py",
        "tools/meta/dissemination/build_holographic_research_bundle.py",
        "tools/meta/dissemination/projection_secret_scan.py",
    }

    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = EXPORTED_BUNDLE / row["path"]
        assert source.is_file(), row["source_ref"]
        assert target.is_file(), row["path"]
        assert source.read_bytes() == target.read_bytes(), row["source_ref"]
        assert row["sha256"] == _sha256(source)
        assert row["source_sha256"] == row["sha256"]
        assert row["target_sha256"] == row["sha256"]
        assert row["sha256_match"] is True
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])

    for source_ref, row in refactors.items():
        source = SOURCE_ROOT / source_ref
        target = EXPORTED_BUNDLE / row["path"]
        assert source.is_file(), source_ref
        assert target.is_file(), row["path"]
        assert source.read_bytes() != target.read_bytes(), source_ref
        assert row["source_sha256"] == _sha256(source)
        assert row["target_sha256"] == _sha256(target)
        assert row["source_to_target_relation"].startswith("source_faithful_public_refactor")
        text = target.read_text(encoding="utf-8")
        if source_ref != "tools/meta/observability/session_analyzer.py":
            assert "operator_account_alias" in text or "operator_seed_root_placeholder" in text
            assert "williamwkcook" not in text
            assert "willwkcook" not in text
            assert "obsidian/okay lets do this" not in text
        assert all(anchor in text for anchor in row["required_anchors"])


def test_batch11_card_omits_private_bodies(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch11_saturation_engines_capsule",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["mechanism_count"] == len(EXPECTED_MECHANISMS)
    assert card["source_module_count"] == len(EXPECTED_MODULE_IDS)
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "matched_excerpt" not in _walk_keys(result)
    assert "source_body" not in _walk_keys(result)


def test_batch11_negative_cases_are_stable() -> None:
    matrix_mechanisms = set(EXPECTED_MECHANISMS)
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["schema_version"] == NEGATIVE_CASE_PROBE_SCHEMA
        assert payload["error_codes"] == list(expected_codes)
        assert payload["fixture_role"] == "negative_case_label_not_verdict_authority"
        assert payload["verdict_authority"] == CASE_VERDICT_AUTHORITY
        assert payload["mechanism_id"] in matrix_mechanisms
        assert payload["computed_path"] == NEGATIVE_CASE_COMPUTED_PATHS[case_id]["computed_path"]
        assert isinstance(payload["probe_input"], dict)
        assert payload["probe_input"]
        assert payload["body_in_receipt"] is False


def test_batch11_mechanism_outputs_cover_tier_b_and_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch11_saturation_engines_capsule",
        command="pytest",
    )
    exercise = result["exercise"]

    tier_b_rows = {
        row["mechanism_id"]: row for row in exercise["tier_b_controller_verification"]
    }
    assert set(tier_b_rows) == TIER_B_MECHANISMS
    assert tier_b_rows["projection_secret_scan"]["capsule_action"] == "validate_existing_bound_gate"
    assert tier_b_rows["demo_take_story_coverage_audit"]["capsule_action"] == "validate_existing_bound_gate"
    assert tier_b_rows["stockgrid_flow_multisource_merge_unit_normalizer"]["capsule_action"] == (
        "import_under_bound_or_absent_macro_mechanism"
    )

    matrix = {row["mechanism_id"]: row for row in exercise["integrity_matrix"]}
    observed_cases = {
        negative_case["case_id"]
        for row in matrix.values()
        for negative_case in row["negative_cases"]
        if negative_case["computed"] and negative_case["fixture_computed_value"]
    }
    assert observed_cases == set(EXPECTED_NEGATIVE_CASES)


def test_batch11_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = fixture / f"{case_id}.json"
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        payload["computed_path"] = "bogus_declared_computed_path"
        payload["fixture_role"] = "forged_fixture_verdict"
        payload["verdict_authority"] = "declared_label_attempt"
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture,
        fixture.parents[3] / "receipts/first_wave/batch11_saturation_engines_capsule",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    for expected_codes in EXPECTED_NEGATIVE_CASES.values():
        for code in expected_codes:
            assert code in result["error_codes"]
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_batch11_negative_case_evaluator_rejects_each_real_case() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        result = evaluate_negative_case(case_id, FIXTURE_INPUT, expected_codes)

        assert result["status"] == "blocked"
        for code in expected_codes:
            assert code in result["error_codes"]


def test_batch11_negative_case_probe_input_change_blocks_fixture_run(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    case_id = "run_affinity_stale_terminal_rejected"
    case_path = fixture / f"{case_id}.json"
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    payload["probe_input"]["stale_run_id"] = "RUN_CLOSE"
    case_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    direct = evaluate_negative_case(case_id, fixture, EXPECTED_NEGATIVE_CASES[case_id])
    result = run(
        fixture,
        fixture.parents[3] / "receipts/first_wave/batch11_saturation_engines_capsule",
    )
    semantic_row = next(
        row for row in result["negative_case_semantics"] if row["case_id"] == case_id
    )

    assert direct["status"] == "pass"
    assert result["status"] == "blocked"
    assert semantic_row["status"] == "pass"
    assert case_id not in result["observed_negative_cases"]
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in result["error_codes"]


def test_batch11_exported_bundle_rejects_public_refactor_manifest_digest_forgery(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    bundle = _public_bundle_for_fixture(fixture)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = next(
        row
        for row in manifest["source_faithful_public_refactors"]
        if row["source_ref"] == "tools/meta/dissemination/projection_secret_scan.py"
    )
    row["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch11_saturation_engines_bundle(
        bundle,
        fixture.parents[3] / "receipts/runtime_shell/demo_project/organs/batch11_saturation_engines_capsule",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert "BATCH11_PUBLIC_REFACTOR_DIGEST_MISMATCH" in result["error_codes"]


def test_batch11_exported_bundle_source_body_perturbation_moves_verdict(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    bundle = _public_bundle_for_fixture(fixture)
    out_dir = (
        fixture.parents[3]
        / "receipts/runtime_shell/demo_project/organs/batch11_saturation_engines_capsule"
    )
    real_good = run_batch11_saturation_engines_bundle(bundle, out_dir)
    assert real_good["status"] == "pass"

    source_module = (
        bundle
        / "source_modules/ai_workflow/tools/meta/observability/session_analyzer.py"
    )
    source_module.write_text(
        source_module.read_text(encoding="utf-8")
        + "\n# public-copy perturbation should change the source-manifest verdict\n",
        encoding="utf-8",
    )
    mutated = run_batch11_saturation_engines_bundle(bundle, out_dir)

    assert mutated["status"] == "blocked"
    assert mutated["source_module_manifest"]["status"] == "blocked"
    assert mutated["source_module_manifest"]["all_expected_digests_matched"] is False
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in mutated["error_codes"]
