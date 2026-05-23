from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.cold_reader_route_map import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_route_map_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/cold_reader_route_map/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle"
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


def test_cold_reader_route_map_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/cold_reader_route_map",
        command="pytest",
        acceptance_out=(
            tmp_path
            / "receipts/acceptance/first_wave/cold_reader_route_map_fixture_acceptance.json"
        ),
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["route_count"] == 7
    assert result["command_count"] == 7
    assert result["receipt_ref_count"] >= 7
    assert result["first_run_sequence"][0] == "compile_project"
    assert result["authority_ceiling"]["route_registry_authority"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_cold_reader_exported_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_route_map_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/cold_reader_route_map",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_cold_reader_route_map_bundle"
    assert result["bundle_id"] == "public_cold_reader_route_map_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["covered_route_ids"] == [
        "compile_project",
        "inspect_cold_reader_route_map",
        "inspect_public_spine",
        "inspect_route",
        "open_import_bridge",
        "open_observatory",
        "open_reveal_board",
    ]
    assert "microcosm-substrate/src/microcosm_core/runtime_shell.py" in result["source_refs"]
    assert "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle" in result[
        "public_runtime_refs"
    ]
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in _walk_keys(result)


def test_cold_reader_receipts_are_public_relative_with_secret_exclusion(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/cold_reader_route_map",
        public_root / "fixtures/first_wave/cold_reader_route_map",
    )
    result = run(
        public_root / "fixtures/first_wave/cold_reader_route_map/input",
        public_root / "receipts/first_wave/cold_reader_route_map",
        command="pytest",
        acceptance_out=(
            public_root
            / "receipts/acceptance/first_wave/cold_reader_route_map_fixture_acceptance.json"
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
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["real_runtime_receipt"] is True
        assert payload["synthetic_receipt_standin_allowed"] is False
        assert "private_state_scan" not in payload
        assert "body_redacted" not in _walk_keys(payload)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
