from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import microcosm_core.organs.formal_math_verifier_trace_repair_loop as trace_module
from microcosm_core.organs.formal_math_verifier_trace_repair_loop import (
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_loop_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/formal_math_verifier_trace_repair_loop/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/formal_math_verifier_trace_repair_loop/exported_verifier_trace_repair_bundle"
)


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_formal_math_verifier_trace_repair_loop_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/formal_math_verifier_trace_repair_loop",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/formal_math_verifier_trace_repair_loop_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["attempt_count"] == 5
    assert result["trace_event_count"] == 15
    assert result["repair_action_count"] == 5
    assert result["cold_rerun_promotion_count"] == 3
    assert result["failure_mode_count"] == 3
    assert result["curriculum_edge_count"] == 3
    assert (
        result["macro_run_id"]
        == "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0"
    )
    assert (
        result["body_material_status"]
        == "copied_non_secret_macro_body_with_provenance"
    )
    assert result["body_copied_material_count"] == 3
    assert result["source_modules_pass"] is True
    assert result["source_module_count"] == 0
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert "private_state_scan" not in result
    assert "body_redacted" not in result
    source_digests = result["source_digests"]
    assert (
        source_digests[
            "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
            "premise_retrieval_graph_v0/run_summary.json"
        ]
        == "sha256:93304410f32d40f5cad1c161c1d01a5d6f353ee10b7cf3fecbaaf7b068b43008"
    )
    copied_material_ids = {material["material_id"] for material in result["copied_material"]}
    assert copied_material_ids == {
        "ring2_premise_retrieval_failure_trace_rows",
        "ring2_premise_retrieval_graph_update_candidates",
        "ring2_oracle_repair_cold_rerun_contrast_rows",
    }
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    assert result["authority_ceiling"]["human_approval_as_proof_authority"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_formal_math_verifier_trace_repair_receipts_are_public_relative_and_provenanced(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_math_verifier_trace_repair_loop",
        public_root / "fixtures/first_wave/formal_math_verifier_trace_repair_loop",
    )

    result = run(
        public_root / "fixtures/first_wave/formal_math_verifier_trace_repair_loop/input",
        public_root / "receipts/first_wave/formal_math_verifier_trace_repair_loop",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "synthetic" not in text
        assert "body_redacted" not in text
        assert "private_state_scan" not in text
        assert "public_replacement" not in text
        assert '"proof_body":' not in text
        assert '"provider_payload_body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert (
            payload["body_material_status"]
            == "copied_non_secret_macro_body_with_provenance"
        )
        assert payload["body_copied_material_count"] == 3
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert "private_state_scan" not in _walk_keys(payload)
        assert "body_redacted" not in _walk_keys(payload)
        assert "proof_body" not in _walk_keys(payload)
        assert "provider_payload_body" not in _walk_keys(payload)


def test_formal_math_verifier_trace_repair_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_loop_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/formal_math_verifier_trace_repair_loop",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_verifier_trace_repair_bundle"
    assert result["bundle_id"] == "formal_math_verifier_trace_repair_loop_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["attempt_count"] == 5
    assert result["trace_event_count"] == 15
    assert result["repair_action_count"] == 5
    assert result["cold_rerun_promotion_count"] == 3
    assert (
        result["body_material_status"]
        == "copied_non_secret_macro_body_with_provenance"
    )
    assert result["body_copied_material_count"] == 3
    assert result["source_modules_pass"] is True
    assert result["source_module_count"] == 7
    assert result["source_open_body_imports"]["body_material_count"] == 7
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert result["source_module_manifest"]["verified_module_count"] == 7
    assert result["authority_ceiling"]["formal_proof_authority"] is False


def test_formal_math_verifier_trace_repair_cli_card_compacts_exported_bundle(
    tmp_path: Path,
    capsys: Any,
) -> None:
    status = main(
        [
            "run-loop-bundle",
            "--input",
            str(BUNDLE_INPUT),
            "--out",
            str(
                tmp_path
                / "receipts/runtime_shell/demo_project/organs/formal_math_verifier_trace_repair_loop"
            ),
            "--card",
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(output)

    assert status == 0
    assert len(output.encode("utf-8")) < 3600
    assert payload["schema_version"] == "formal_math_verifier_trace_repair_loop_card_v1"
    assert payload["status"] == "pass"
    assert payload["card_id"] == "formal_math_verifier_trace_repair_loop_bundle_card"
    assert payload["output_profile"] == "compact_card_no_trace_rows_or_source_bodies"
    assert payload["input_mode"] == "exported_verifier_trace_repair_bundle"
    assert payload["receipt_paths"]
    assert payload["receipt_reused"] is False
    assert payload["freshness_status"] == "current"
    assert payload["freshness_digest"].startswith("sha256:")
    assert payload["secret_exclusion_scan_summary"]["scanned_path_count"] == 13
    assert payload["secret_exclusion_scan_summary"]["blocking_hit_count"] == 0
    assert payload["secret_exclusion_scan_summary"]["body_text_exported"] is False
    assert payload["source_open_body_imports_summary"]["body_material_count"] == 7
    assert payload["source_open_body_imports_summary"]["body_in_receipt"] is False
    assert payload["attempt_count"] == 5
    assert payload["trace_event_count"] == 15
    assert payload["repair_action_count"] == 5
    assert payload["cold_rerun_promotion_count"] == 3
    assert payload["source_module_count"] == 7
    assert payload["source_modules_pass"] is True
    assert payload["trace_rows_omitted"] is True
    assert payload["source_module_bodies_omitted"] is True
    assert payload["proof_bodies_exported"] is False
    assert "verifier_attempts" not in payload
    assert "failure_mode_ledger" not in payload
    assert "verifier_attempts" in payload["omitted_full_payload_keys"]
    assert "freshness_basis" in payload["omitted_full_payload_keys"]


def test_formal_math_verifier_trace_repair_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    out_dir = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/formal_math_verifier_trace_repair_loop"
    )

    result = run_loop_bundle(
        BUNDLE_INPUT,
        out_dir,
        command="pytest --card",
        reuse_fresh_receipt=True,
    )
    card = trace_module._result_card(result)

    assert result["status"] == "pass"
    assert result["receipt_reused"] is False
    assert result["card_schema_version"] == "formal_math_verifier_trace_repair_loop_card_v1"
    assert result["freshness_digest"].startswith("sha256:")
    assert card["receipt_reused"] is False
    assert card["freshness_digest"] == result["freshness_digest"]
    assert card["attempt_count"] == 5
    assert card["secret_exclusion_scan_summary"]["scanned_path_count"] == 13
    assert "verifier_attempts" in card["omitted_full_payload_keys"]
    assert "freshness_basis" in card["omitted_full_payload_keys"]
    assert "verifier_attempts" not in card
    assert "secret_exclusion_scan" not in card
    assert str(tmp_path) not in json.dumps(card, sort_keys=True)

    def fail_if_rebuilt(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the verifier trace receipt")

    monkeypatch.setattr(trace_module, "_build_result", fail_if_rebuilt)

    cached = run_loop_bundle(
        BUNDLE_INPUT,
        out_dir,
        command="pytest --card",
        reuse_fresh_receipt=True,
    )
    cached_card = trace_module._result_card(cached)

    assert cached["status"] == "pass"
    assert cached["receipt_reused"] is True
    assert cached["freshness_digest"] == result["freshness_digest"]
    assert cached_card["receipt_reused"] is True
    assert cached_card["attempt_count"] == 5


def test_formal_math_verifier_trace_repair_exported_source_modules_are_exact_copies() -> None:
    manifest = json.loads((BUNDLE_INPUT / "source_module_manifest.json").read_text())

    assert manifest["source_import_class"] == "source_faithful_public_safe_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 7
    assert len(manifest["modules"]) == 7

    repo_root = MICROCOSM_ROOT.parent
    for module in manifest["modules"]:
        source = repo_root / module["source_ref"]
        target = repo_root / module["target_ref"]
        assert source.is_file()
        assert target.is_file()
        assert _sha256(source) == module["source_sha256"].removeprefix("sha256:")
        assert _sha256(target) == module["target_sha256"].removeprefix("sha256:")
        assert _sha256(target) == module["sha256"]
        assert module["body_copied"] is True
        assert module["body_in_receipt"] is False
        assert (
            module["source_to_target_relation"]
            == "source_faithful_public_safe_normalized_copy"
        )
        text = target.read_text(encoding="utf-8")
        assert "/Users/" not in text
        assert "oracle_needed_premise_ids" not in text
        assert "proof_body" not in text
        assert "provider_payload_body" not in text
