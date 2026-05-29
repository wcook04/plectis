from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import ring2_premise_retrieval_precision_recall_harness
from microcosm_core.organs.ring2_premise_retrieval_precision_recall_harness import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_precision_recall_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/ring2_premise_retrieval_precision_recall_harness/input"
)
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / (
        "examples/ring2_premise_retrieval_precision_recall_harness/"
        "exported_ring2_precision_recall_bundle"
    )
)
SOURCE_ARTIFACT_REFS = [
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/aggregate_report.json",
    (
        "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
        "premise_retrieval_graph_v0/run_summary.json"
    ),
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/graph_variant_comparison.json",
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/problem_source_manifest.json",
]
SOURCE_BODY_MATERIAL_IDS = {
    "ring2_precision_recall_aggregate_report_body_import",
    "ring2_precision_recall_run_summary_body_import",
    "ring2_precision_recall_graph_variant_comparison_body_import",
    "ring2_precision_recall_problem_source_manifest_body_import",
}
PRIVATE_HOME_PREFIX = "/" + "Users" + "/"
OPERATOR_HOME_SAMPLE = PRIVATE_HOME_PREFIX + "willcook"


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


def test_ring2_precision_recall_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/ring2_premise_retrieval_precision_recall_harness",
        acceptance_out=tmp_path
        / (
            "receipts/acceptance/first_wave/"
            "ring2_premise_retrieval_precision_recall_harness_fixture_acceptance.json"
        ),
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["problem_count"] == 10
    assert result["macro_run_id"] == "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0"
    assert result["macro_run_variant_id"] == "premise_retrieval_graph_v0"
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["body_copied_material_count"] == 1
    assert result["source_artifact_status"] == "copied_ring2_source_artifacts_verified"
    assert result["source_artifact_count"] == 4
    assert result["copied_source_artifact_count"] == 4
    assert result["source_artifacts_pass"] is True
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 4
    assert (
        set(result["source_open_body_imports"]["body_material_ids"])
        == SOURCE_BODY_MATERIAL_IDS
    )
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert result["source_open_body_imports"]["body_text_exported_in_receipts"] is False
    assert result["mean_precision_at_k"] == 0.36
    assert result["mean_recall_at_k"] == 0.9
    assert result["metric_aggregation"]["total_hit_count"] == 9
    assert result["metric_aggregation"]["total_retrieval_candidate_count"] == 25
    assert result["failure_mode_counts"] == {
        "proof_failure_despite_hit": 4,
        "retrieval_hit": 5,
        "retrieval_miss": 1,
    }
    assert result["adversarial_decoy_observed"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert "private_state_scan" not in result
    assert "body_redacted" not in result
    copied_material = result["copied_material"][0]
    assert copied_material["source_ref"].endswith(
        "premise_retrieval_graph_v0/run_summary.json"
    )
    assert copied_material["source_sha256"] == (
        "sha256:93304410f32d40f5cad1c161c1d01a5d6f353ee10b7cf3fecbaaf7b068b43008"
    )
    assert result["authority_ceiling"]["labels_allowed_in_provider_context"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    assert result["authority_ceiling"]["benchmark_performance_authority"] is False
    for case_id, codes in EXPECTED_NEGATIVE_CASES.items():
        for code in codes:
            assert code in result["observed_negative_cases"][case_id]
    for row in result["source_artifact_imports"]:
        assert row["exists"] is True
        assert row["digest_match"] is True
        assert row["source_to_target_relation"] in {
            "exact_copy",
            "verified_public_safe_private_path_rewrite",
        }
        if row["source_to_target_relation"] == "exact_copy":
            assert row["source_sha256"] == row["target_sha256"]
            assert row["verification_mode"] == "exact_source_digest_match"
        else:
            assert row["public_safe_sha256"] == row["target_sha256"]
            assert row["source_sha256"] != row["target_sha256"]
            assert row["verification_mode"] == "verified_light_edit_recipe"
            assert row["public_safe_transform"] == "private_absolute_path_rewrite_only"


def test_ring2_precision_recall_receipts_are_public_relative_and_provenanced(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/ring2_premise_retrieval_precision_recall_harness",
        public_root / "fixtures/first_wave/ring2_premise_retrieval_precision_recall_harness",
    )
    result = run(
        public_root
        / "fixtures/first_wave/ring2_premise_retrieval_precision_recall_harness/input",
        public_root / "receipts/first_wave/ring2_premise_retrieval_precision_recall_harness",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_path in result["receipt_paths"]:
        assert not Path(receipt_path).is_absolute()
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert PRIVATE_HOME_PREFIX not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["body_material_status"] == (
            "copied_non_secret_macro_body_with_provenance"
        )
        assert payload["body_copied_material_count"] == 1
        assert payload["copied_source_artifact_count"] == 4
        assert payload["source_artifacts_pass"] is True
        assert payload["source_open_body_imports"]["body_material_count"] == 4
        assert payload["source_open_body_imports"]["body_in_receipt"] is False
        assert "secret_exclusion_scan" in payload
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "private_state_scan" not in _walk_keys(payload)
        assert "body_redacted" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_ring2_precision_recall_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/ring2_premise_retrieval_precision_recall_harness",
        public_root / "examples/ring2_premise_retrieval_precision_recall_harness",
    )
    result = run_precision_recall_bundle(
        public_root
        / (
            "examples/ring2_premise_retrieval_precision_recall_harness/"
            "exported_ring2_precision_recall_bundle"
        ),
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "ring2_premise_retrieval_precision_recall_harness",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_ring2_precision_recall_bundle"
    assert result["bundle_id"] == "ring2_precision_recall_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["problem_count"] == 10
    assert result["body_material_status"] == "copied_non_secret_macro_body_with_provenance"
    assert result["body_copied_material_count"] == 1
    assert result["source_artifact_count"] == 4
    assert result["copied_source_artifact_count"] == 4
    assert result["source_artifacts_pass"] is True
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 4
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert result["mean_precision_at_k"] == 0.36
    assert result["mean_recall_at_k"] == 0.9
    assert result["failure_mode_counts"] == {
        "proof_failure_despite_hit": 4,
        "retrieval_hit": 5,
        "retrieval_miss": 1,
    }
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    assert result["receipt_paths"] == [
        (
            "receipts/runtime_shell/demo_project/organs/"
            "ring2_premise_retrieval_precision_recall_harness/"
            "exported_ring2_precision_recall_bundle_validation_result.json"
        )
    ]


def test_ring2_precision_recall_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "ring2_premise_retrieval_precision_recall_harness"
    )
    args = [
        "run-precision-recall-bundle",
        "--input",
        str(EXPORTED_BUNDLE_INPUT),
        "--out",
        str(out),
        "--card",
    ]

    assert main(args) == 0
    first_card = json.loads(capsys.readouterr().out)
    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["command_speed"]["receipt_reused"] is False
    assert first_card["command_speed"]["freshness_missing_path_count"] == 0
    assert first_card["command_speed"]["freshness_input_count"] == 10
    assert first_card["ring2_precision_recall"]["problem_count"] == 10
    assert first_card["ring2_precision_recall"]["mean_precision_at_k"] == 0.36
    assert first_card["ring2_precision_recall"]["mean_recall_at_k"] == 0.9
    assert first_card["source_body_floor"]["status"] == "pass"
    assert first_card["source_body_floor"]["body_material_count"] == 4
    assert first_card["source_body_floor"]["body_material_id_count"] == 4
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["secret_exclusion_blocking_hit_count"] == 0
    assert "source_artifact_imports" not in _walk_keys(first_card)
    assert "source_open_body_imports" not in _walk_keys(first_card)
    assert "body_material_ids" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "source_digests" not in _walk_keys(first_card)
    assert "evaluations" not in _walk_keys(first_card)
    assert "retrieved_premise_ids" not in _walk_keys(first_card)
    assert "needed_premise_ids" not in _walk_keys(first_card)
    assert "proof_body" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        ring2_premise_retrieval_precision_recall_harness,
        "_build_result",
        fail_if_rebuilt,
    )

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]


def test_ring2_precision_recall_source_artifacts_are_digest_verified(
    tmp_path: Path,
) -> None:
    for input_root in (FIXTURE_INPUT, EXPORTED_BUNDLE_INPUT):
        out_dir = tmp_path / input_root.name
        if input_root == FIXTURE_INPUT:
            result = run(input_root, out_dir, command="pytest")
        else:
            result = run_precision_recall_bundle(input_root, out_dir, command="pytest")
        imports_by_ref = {
            row["source_ref"]: row for row in result["source_artifact_imports"]
        }
        for source_ref in SOURCE_ARTIFACT_REFS:
            source = MICROCOSM_ROOT.parent / source_ref
            target = input_root / "source_artifacts" / source_ref
            assert target.is_file()
            source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
            target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
            row = imports_by_ref[source_ref]
            assert row["digest_match"] is True
            assert row["source_sha256"] == f"sha256:{source_digest}"
            assert row["target_sha256"] == f"sha256:{target_digest}"
            if row["source_to_target_relation"] == "exact_copy":
                assert source_digest == target_digest
                assert source.read_bytes() == target.read_bytes()
            else:
                assert row["source_to_target_relation"] == (
                    "verified_public_safe_private_path_rewrite"
                )
                assert row["public_safe_sha256"] == f"sha256:{target_digest}"
                assert OPERATOR_HOME_SAMPLE not in target.read_text(encoding="utf-8")
