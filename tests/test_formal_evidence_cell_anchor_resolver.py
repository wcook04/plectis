from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.formal_evidence_cell_anchor_resolver import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_anchor_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/formal_evidence_cell_anchor_resolver/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/formal_evidence_cell_anchor_resolver/exported_evidence_cell_anchor_bundle"
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


def test_formal_evidence_cell_anchor_resolver_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/formal_evidence_cell_anchor_resolver",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/formal_evidence_cell_anchor_resolver_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["claim_count"] == 3
    assert result["resolved_cell_count"] == 3
    assert result["unresolved_cell_count"] == 0
    assert result["evidence_cell_count"] == 3
    assert result["source_anchor_count"] == 6
    assert result["machine_anchor_count"] == 3
    assert result["authority_ceiling"]["theorem_correctness_authority"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_formal_evidence_cell_anchor_receipts_are_public_relative_with_secret_exclusion(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_evidence_cell_anchor_resolver",
        public_root / "fixtures/first_wave/formal_evidence_cell_anchor_resolver",
    )

    result = run(
        public_root / "fixtures/first_wave/formal_evidence_cell_anchor_resolver/input",
        public_root / "receipts/first_wave/formal_evidence_cell_anchor_resolver",
        command="pytest",
        acceptance_out=(
            public_root
            / "receipts/acceptance/first_wave/formal_evidence_cell_anchor_resolver_fixture_acceptance.json"
        ),
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "private://macro-formal-lab" not in text
        assert "synthetic forbidden proof body" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["body_in_receipt"] is False
        assert payload["real_runtime_receipt"] is True
        assert payload["synthetic_receipt_standin_allowed"] is False
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert "private_state_scan" not in payload
        assert "body_redacted" not in _walk_keys(payload)
        assert "proof_body" not in _walk_keys(payload)
        assert "private_source_ref" not in _walk_keys(payload)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_formal_evidence_cell_anchor_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_anchor_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/formal_evidence_cell_anchor_resolver",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_evidence_cell_anchor_bundle"
    assert result["bundle_id"] == "formal_evidence_cell_anchor_resolver_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["claim_count"] == 2
    assert result["resolved_cell_count"] == 2
    assert result["authority_ceiling"]["theorem_correctness_authority"] is False
