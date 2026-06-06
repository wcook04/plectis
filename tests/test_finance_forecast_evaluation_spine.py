from __future__ import annotations

import json
import shutil
from pathlib import Path

import microcosm_core.organs.finance_forecast_evaluation_spine as finance_spine
from microcosm_core.organs.finance_forecast_evaluation_spine import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_finance_forecast_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/finance_forecast_evaluation_spine/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/finance_forecast_evaluation_spine/exported_finance_eval_bundle"
)


def _copy_public_fixture(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/finance_forecast_evaluation_spine",
        public_root / "examples/finance_forecast_evaluation_spine",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/finance_forecast_evaluation_spine",
        public_root / "fixtures/first_wave/finance_forecast_evaluation_spine",
    )
    return public_root / "fixtures/first_wave/finance_forecast_evaluation_spine/input"


def test_finance_forecast_evaluation_spine_runs_statistical_fixture(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/finance_forecast_evaluation_spine",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["semantic_negative_case_evaluator_used"] is True
    exercise = result["exercise"]
    assert exercise["sample_size"] == 40
    assert exercise["reality_check"]["status"] == "computed_bootstrap"
    assert exercise["spa"]["status"] == "computed_bootstrap"
    assert exercise["mcs"]["implemented"] is True
    assert exercise["paired_loss"]["diebold_mariano"]["status"] == "computed_hac_normal_approximation"
    assert exercise["hln_dependency_refusal"]["status"] == "refused"
    assert exercise["hln_dependency_refusal"]["reason"] == "scipy_unavailable_for_t_distribution"
    assert exercise["stationary_bootstrap"]["replicate_count"] == 5
    assert exercise["investment_advice_authorized"] is False
    assert exercise["live_market_data_used"] is False
    assert result["source_module_manifest"]["module_count"] == 13


def test_finance_forecast_evaluation_spine_rejects_no_advice_overclaim(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    policy_path = fixture / "finance_boundary_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["investment_advice_authorized"] = True
    policy_path.write_text(json.dumps(policy, sort_keys=True), encoding="utf-8")

    result = run(
        fixture,
        tmp_path / "microcosm-substrate/receipts/first_wave/finance_forecast_evaluation_spine",
    )

    assert result["status"] == "blocked"
    assert "FINANCE_NO_ADVICE_OVERCLAIM" in result["error_codes"]


def test_finance_forecast_evaluation_spine_rejects_live_market_data_overclaim(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    policy_path = fixture / "finance_boundary_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["live_market_data_authorized"] = True
    policy_path.write_text(json.dumps(policy, sort_keys=True), encoding="utf-8")

    result = run(
        fixture,
        tmp_path / "microcosm-substrate/receipts/first_wave/finance_forecast_evaluation_spine",
    )

    assert result["status"] == "blocked"
    assert "FINANCE_NO_ADVICE_OVERCLAIM" in result["error_codes"]


def test_finance_forecast_evaluation_spine_rejects_lookahead_split(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    paired_path = fixture / "paired_loss_series.json"
    paired = json.loads(paired_path.read_text(encoding="utf-8"))
    paired["rows"][0]["subject_as_of"] = paired["rows"][0]["event_start"]
    paired_path.write_text(json.dumps(paired, sort_keys=True), encoding="utf-8")

    result = run(
        fixture,
        tmp_path / "microcosm-substrate/receipts/first_wave/finance_forecast_evaluation_spine",
    )

    assert result["status"] == "blocked"
    assert "FINANCE_LOOKAHEAD_SPLIT_FORBIDDEN" in result["error_codes"]


def test_finance_forecast_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        path = fixture / f"{case_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["status"] = "pass"
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture,
        tmp_path / "microcosm-substrate/receipts/first_wave/finance_forecast_evaluation_spine",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["semantic_negative_case_evaluator_used"] is True
    assert all(
        row["semantic_evaluator_used"] for row in result["negative_case_semantics"]
    )
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    assert "FINANCE_LOOKAHEAD_SPLIT_FORBIDDEN" in result["error_codes"]
    assert "FINANCE_NO_ADVICE_OVERCLAIM" in result["error_codes"]
    assert "FINANCE_HLN_TYPED_REFUSAL_REQUIRED" in result["error_codes"]


def test_finance_forecast_bundle_runs(tmp_path: Path) -> None:
    result = run_finance_forecast_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/finance_forecast_evaluation_spine",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_finance_eval_bundle"


def test_finance_forecast_bundle_uses_standalone_statistics_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fail_subprocess(**_kwargs):
        raise AssertionError("exported bundle must not spawn the finance statistics subprocess")

    monkeypatch.setattr(finance_spine, "_run_stats_subprocess", fail_subprocess)

    result = run_finance_forecast_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/finance_forecast_evaluation_spine",
        command="pytest",
    )

    assert result["status"] == "pass"
    exercise = result["exercise"]
    assert exercise["statistics_witness_mode"] == "standalone_exported_statistics_contract"
    assert exercise["external_witness"]["skipped"] is True
    assert exercise["reality_check"]["status"] == "computed_bootstrap"
    assert exercise["spa"]["status"] == "computed_bootstrap"
    assert exercise["mcs"]["implemented"] is True
    assert exercise["hln_dependency_refusal"]["reason"] == "scipy_unavailable_for_t_distribution"


def test_finance_forecast_bundle_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/finance_forecast_evaluation_spine/exported_finance_eval_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_finance_forecast_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/finance_forecast_evaluation_spine",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
