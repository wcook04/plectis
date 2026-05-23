from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.public_reveal_walkthrough import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_reveal_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/public_reveal_walkthrough/input"
BUNDLE_INPUT = MICROCOSM_ROOT / "examples/public_reveal_walkthrough/exported_public_reveal_bundle"


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


def test_public_reveal_walkthrough_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/public_reveal_walkthrough",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/public_reveal_walkthrough_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["step_count"] == 5
    assert result["command_count"] >= 4
    assert result["evidence_ref_count"] >= 4
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["reveal_board"]["primary_loop"].startswith("repo -> .microcosm")
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["public_runtime_refs"]
    assert "private_state_scan" not in result
    assert "body_redacted" not in result


def test_public_reveal_walkthrough_receipts_are_public_relative_and_secret_excluded(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/public_reveal_walkthrough",
        public_root / "fixtures/first_wave/public_reveal_walkthrough",
    )

    result = run(
        public_root / "fixtures/first_wave/public_reveal_walkthrough/input",
        public_root / "receipts/first_wave/public_reveal_walkthrough",
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
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["body_in_receipt"] is False
        assert payload["real_runtime_receipt"] is True
        assert payload["synthetic_receipt_standin_allowed"] is False
        assert payload["public_runtime_refs"]
        assert "private_state_scan" not in payload
        assert "body_redacted" not in payload
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_public_reveal_exported_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_reveal_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/public_reveal_walkthrough",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_public_reveal_bundle"
    assert result["bundle_id"] == "public_reveal_walkthrough_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["reveal_board"]["release_authorized"] is False
    assert result["public_claim"].startswith("Microcosm turns a repo")
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["public_runtime_refs"]
    assert "private_state_scan" not in result
    assert "body_redacted" not in result
