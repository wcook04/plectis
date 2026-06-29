"""Contract tests for the gated lean_proof_search_lab_runtime organ.

The organ is a *gated external-tool witness*: it must be honest in both states.

* The locked-state tests run WITHOUT Lean (they force the probe to report the
  binary absent) and assert the organ verifies nothing, never fakes a pass, and
  never reports a Lean-absence as a mechanism failure (no false-green, no
  false-red).
* The live test is skipped unless the ``lean`` binary is actually on PATH; when
  it runs it asserts the real proof-search subprocess closes the toy positive
  and rejects each planted negative by its mechanism.

This module is intentionally NOT listed in the default ``make test`` PUBLIC_TESTS
floor: it can require the Lean toolchain, mirroring the sister organ
``formal_math_lean_proof_witness``. The committed acceptance receipt is the
authority artifact; the default floor validates the registration/contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import microcosm_core.organs.lean_proof_search_lab_runtime as organ
from microcosm_core.organs.lean_proof_search_lab_runtime import (
    EXPECTED_NEGATIVE_CASES,
    build_result,
    lean_available,
    result_card,
    run,
    run_lean_proof_search_lab_runtime_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "fixtures/first_wave/lean_proof_search_lab_runtime/input"
BUNDLE_DIR = (
    ROOT
    / "examples/lean_proof_search_lab_runtime"
    / "exported_lean_proof_search_lab_runtime_bundle"
)


def _force_lean_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(organ.shutil, "which", lambda _name: None)


def test_locked_state_is_honest_when_lean_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    _force_lean_absent(monkeypatch)
    assert lean_available() is False
    result = build_result(INPUT_DIR)
    # Locked is a third terminal state: not a pass, not a fail.
    assert result["status"] == "locked"
    assert result["tool_state"] == organ.TOOL_MISSING
    assert result["execution_witness_mode"] == organ.EXECUTION_LOCKED
    assert result["verification_performed"] is False
    assert result["lean_available"] is False
    assert result["case_count"] == 0
    assert result["unlock_instructions"]


def test_locked_state_is_not_false_green(monkeypatch: pytest.MonkeyPatch) -> None:
    # A consumer reading status must never see "pass" when Lean never ran.
    _force_lean_absent(monkeypatch)
    result = build_result(INPUT_DIR)
    assert result["status"] != "pass"
    assert result.get("tool_state") != organ.TOOL_PRESENT_AND_VERIFIED


def test_locked_state_is_not_false_red(monkeypatch: pytest.MonkeyPatch) -> None:
    # Lean-absence must NOT be reported as a mechanism failure.
    _force_lean_absent(monkeypatch)
    result = build_result(INPUT_DIR)
    assert result["status"] != "fail"
    assert result["status"] == "locked"


def test_locked_run_writes_body_free_receipts_without_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _force_lean_absent(monkeypatch)
    out = tmp_path / "out"
    result = run(INPUT_DIR, out, acceptance_out=tmp_path / "acceptance.json")
    assert result["status"] == "locked"
    for name in (organ.RESULT_NAME, organ.BOARD_NAME, organ.VALIDATION_RECEIPT_NAME):
        payload = json.loads((out / name).read_text(encoding="utf-8"))
        blob = json.dumps(payload)
        assert "/Users/" not in blob  # never disclose the lean binary path
        assert payload.get("body_in_receipt", False) is False


def test_standalone_bundle_runner_never_spawns_lean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The runtime-spine bundle runner must stay Lean-free even when Lean is absent.
    _force_lean_absent(monkeypatch)
    result = run_lean_proof_search_lab_runtime_bundle(BUNDLE_DIR, tmp_path / "out")
    assert result["status"] == "pass"
    assert result["lean_executed"] is False
    assert result["verification_performed"] is False
    assert result["execution_witness_mode"] == organ.EXECUTION_STANDALONE
    assert result["declared_required_files_present"] is True


def test_expected_negative_cases_cover_each_rejection_mechanism() -> None:
    # The negative matrix must exercise all three epistemic-discipline guards.
    kinds = set(EXPECTED_NEGATIVE_CASES.values())
    assert "oracle_firewall_violation" in kinds
    assert "axiom_taint_detected" in kinds
    assert "problem_id_ablation_failure" in kinds


@pytest.mark.skipif(not lean_available(), reason="requires the Lean toolchain on PATH")
def test_live_lean_proof_search_verifies_and_self_falsifies() -> None:
    result = build_result(INPUT_DIR)
    assert result["status"] == "pass"
    assert result["tool_state"] == organ.TOOL_PRESENT_AND_VERIFIED
    assert result["execution_witness_mode"] == organ.EXECUTION_LIVE
    assert result["lean_available"] is True
    assert result["positive_case_count"] >= 1
    assert result["negative_case_count"] >= 1
    by_id = {row["case_id"]: row for row in result["cases"]}
    # The positive case requires real Lean to close the toy theorems.
    assert by_id["positive_symbolic_lab_pass"]["observed_ok"] is True
    assert by_id["positive_symbolic_lab_pass"]["observed_status"] == "pass"
    # Every planted negative is rejected with its expected mechanism marker.
    for case_id, failure_kind in EXPECTED_NEGATIVE_CASES.items():
        row = by_id[case_id]
        assert row["observed_ok"] is True
        assert row["observed_status"] == "fail"
        assert row["observed_failure_kind"] == failure_kind
    card = result_card(result)
    assert card["status"] == "pass"
    assert card["tool_state"] == organ.TOOL_PRESENT_AND_VERIFIED
