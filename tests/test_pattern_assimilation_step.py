from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.validators.acceptance import (
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    validate_pattern_assimilation,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
ASSIMILATION_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/pattern_assimilation_step/input"


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


def _field_floor() -> dict[str, list[str]]:
    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "core/fixture_manifests/pattern_assimilation_step.fixture_manifest.json"
        ).read_text(encoding="utf-8")
    )
    return manifest["validator_contract_ratchet_v1"]["per_output_receipt_field_floor"]


def _read_last_jsonl(path: Path, *, run_id: str) -> dict[str, Any]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    matches = [row for row in rows if row.get("run_id") == run_id]
    assert matches
    return matches[-1]


def test_pattern_assimilation_step_observes_required_negative_cases(tmp_path: Path) -> None:
    live_macro = (
        MICROCOSM_ROOT.parent
        / "state/microcosm_portfolio/reconstruction/macro_pattern_autonomy_process_runs_v1.jsonl"
    )
    before = live_macro.read_text(encoding="utf-8") if live_macro.exists() else None
    result = validate_pattern_assimilation(
        ASSIMILATION_FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/pattern_assimilation_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["closeout_contract"]["missing_closeout_count"] == 1
    assert result["closeout_contract"]["refinement_count"] == 1
    assert result["closeout_contract"]["typed_nothing_to_refine_count"] == 1
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]
    after = live_macro.read_text(encoding="utf-8") if live_macro.exists() else None
    assert after == before


def test_pattern_assimilation_receipts_are_public_relative_and_redacted(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/pattern_assimilation_step",
        public_root / "fixtures/first_wave/pattern_assimilation_step",
    )
    result = validate_pattern_assimilation(
        public_root / "fixtures/first_wave/pattern_assimilation_step/input",
        public_root / "receipts/first_wave/pattern_assimilation_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == EXPECTED_RECEIPT_PATHS
    for receipt_path in EXPECTED_RECEIPT_PATHS[:2]:
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "/private/var" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["private_state_scan"]["blocking_hit_count"] == 0
        assert payload["missing_negative_cases"] == []
        assert set(payload["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
    macro_row = _read_last_jsonl(
        tmp_path / "state/microcosm_portfolio/reconstruction/macro_pattern_autonomy_process_runs_v1.jsonl",
        run_id="public_pattern_assimilation_step_current_authority",
    )
    assert macro_row["status"] == "pass"
    assert macro_row["private_state_scan"]["body_redacted"] is True


def test_pattern_assimilation_receipts_satisfy_macro_field_floor(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/pattern_assimilation_step",
        public_root / "fixtures/first_wave/pattern_assimilation_step",
    )
    validate_pattern_assimilation(
        public_root / "fixtures/first_wave/pattern_assimilation_step/input",
        public_root / "receipts/first_wave/pattern_assimilation_acceptance.json",
        command="pytest",
    )

    for receipt_path, required_fields in _field_floor().items():
        if receipt_path.endswith(".jsonl"):
            payload = _read_last_jsonl(
                tmp_path / receipt_path,
                run_id="public_pattern_assimilation_step_current_authority",
            )
        else:
            payload = json.loads((public_root / receipt_path).read_text(encoding="utf-8"))
        missing = [field for field in required_fields if field not in payload]
        assert missing == []
