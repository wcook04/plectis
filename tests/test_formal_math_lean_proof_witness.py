from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import microcosm_core.organs.formal_math_lean_proof_witness as witness_module
from microcosm_core.organs.formal_math_lean_proof_witness import (
    BUNDLE_RESULT_NAME,
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_witness_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/formal_math_lean_proof_witness/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle"
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


def test_formal_math_lean_proof_witness_builds_and_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/formal_math_lean_proof_witness",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/formal_math_lean_proof_witness_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["lake_build"]["return_code"] == 0
    assert result["compiled_declaration_count"] == 8
    assert result["validator_cache_version"].endswith("source_module_scan")
    assert result["private_state_scan"]["scanned_path_count"] >= 8
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["authority_ceiling"]["lean_lake_execution_authorized"] is True
    assert result["authority_ceiling"]["proof_bodies_allowed_in_receipts"] is False
    assert result["authority_ceiling"]["mathlib_presence_claim_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_formal_math_lean_proof_witness_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_math_lean_proof_witness",
        public_root / "fixtures/first_wave/formal_math_lean_proof_witness",
    )

    result = run(
        public_root / "fixtures/first_wave/formal_math_lean_proof_witness/input",
        public_root / "receipts/first_wave/formal_math_lean_proof_witness",
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
        assert "Mathlib" not in text or "FORBIDDEN_IMPORT" in text
        assert "by rfl" not in text
        assert '"proof_body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["private_state_scan"]["blocking_hit_count"] == 0
        assert "proof_body" not in _walk_keys(payload)


def test_formal_math_lean_proof_witness_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_witness_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/formal_math_lean_proof_witness",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_lean_proof_witness_bundle"
    assert result["bundle_id"] == "formal_math_lean_proof_witness_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["compiled_declaration_count"] == 8
    assert result["validator_cache_version"].endswith("source_module_scan")
    assert result["private_state_scan"]["scanned_path_count"] >= 6
    assert result["source_module_imports"]["status"] == "pass"
    assert result["source_module_imports"]["module_count"] == 4
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 4
    assert result["body_copied_material_count"] == 4
    assert result["source_open_body_imports"]["body_in_receipt"] is False
    assert result["lean_witness_board"]["lean_lake_execution_authorized"] is True
    assert result["lean_witness_board"]["mathlib_authorized"] is False


def test_formal_math_lean_proof_witness_bundle_rejects_body_digest_tamper(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    source_file = bundle / "lake_project/MicrocosmProofWitness/Basic.lean"
    source_file.write_text(
        source_file.read_text(encoding="utf-8") + "\n-- tampered after manifest\n",
        encoding="utf-8",
    )

    result = run_witness_bundle(
        bundle,
        tmp_path / "receipts/formal_math_lean_proof_witness",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_imports"]["status"] == "blocked"
    assert "LEAN_WITNESS_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_formal_math_lean_proof_witness_bundle_reuses_fresh_receipt(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    target = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/formal_math_lean_proof_witness"
    )
    first = run_witness_bundle(BUNDLE_INPUT, target, command="pytest")

    def fail_command(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh bundle cache should avoid Lean command probes")

    monkeypatch.setattr(witness_module, "_run_command", fail_command)
    second = run_witness_bundle(BUNDLE_INPUT, target, command="pytest")

    assert first["status"] == "pass"
    assert second["status"] == "pass"
    assert second["cache_status"] == "fresh_exported_bundle_receipt_reused"
    assert second["receipt_paths"] == first["receipt_paths"]
    assert second["compiled_declaration_count"] == first["compiled_declaration_count"]
    assert second["lean_witness_board"]["lean_lake_execution_authorized"] is True


def test_formal_math_lean_proof_witness_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    target = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/formal_math_lean_proof_witness"
    )
    argv = [
        "run-witness-bundle",
        "--input",
        str(BUNDLE_INPUT),
        "--out",
        str(target),
        "--card",
    ]

    assert main(argv) == 0
    first_stdout = capsys.readouterr().out
    first_card = json.loads(first_stdout)
    receipt_path = target / BUNDLE_RESULT_NAME
    assert receipt_path.is_file()

    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["cache_status"] == "fresh_run_executed"
    assert first_card["execution_summary"]["compiled_declaration_count"] == 8
    assert first_card["runtime_summary"]["lake_return_code"] == 0
    assert first_card["receipt_summary"]["full_receipts_written"] is True
    assert len(first_stdout.encode("utf-8")) < 3600

    def fail_command(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh bundle card should avoid Lean command probes")

    monkeypatch.setattr(witness_module, "_run_command", fail_command)
    assert main(argv) == 0
    second_stdout = capsys.readouterr().out
    second_card = json.loads(second_stdout)

    assert second_card["status"] == "pass"
    assert second_card["cache_status"] == "fresh_exported_bundle_receipt_reused"
    assert second_card["receipt_summary"]["receipt_paths_exported"] is False
    assert len(second_stdout.encode("utf-8")) < 3600

    forbidden_card_keys = {
        "anti_claim",
        "findings",
        "private_state_scan",
        "proof_body",
        "public_replacement_refs",
        "receipt_paths",
        "source_files",
        "source_refs",
    }
    assert forbidden_card_keys.isdisjoint(_walk_keys(second_card))

    full_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert "source_files" in full_receipt
    assert full_receipt["command"].endswith("--card")
    assert full_receipt["source_open_body_imports"]["status"] == "pass"
    assert full_receipt["source_open_body_imports"]["body_material_count"] == 4
    assert full_receipt["body_copied_material_count"] == 4
