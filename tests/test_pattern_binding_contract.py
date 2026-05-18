from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from microcosm_core.cold_clone_probe import PATTERN_RECEIPTS, run_probe
from microcosm_core.organs.pattern_binding_contract import EXPECTED_NEGATIVE_CASES, validate
from microcosm_core.receipts import write_receipt
from microcosm_core.schemas import DuplicateJsonKeyError, loads_json_strict


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PATTERN_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/pattern_binding_contract/input"


def test_pattern_binding_validator_observes_required_negative_cases(tmp_path: Path) -> None:
    out_dir = tmp_path / "receipts"

    result = validate(PATTERN_FIXTURE_INPUT, out_dir, command="pytest")

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["accepted_count"] == 1
    assert "pb_valid_synthetic_binding" in result["accepted_pattern_ids"]
    assert "pb_duplicate_conflict" in result["duplicate_pattern_ids"]
    assert "MISSING_GOVERNING_STANDARD" in result["error_codes"]
    assert "MISSING_ANTI_CLAIM_REF" in result["error_codes"]
    assert "PROJECTION_NOT_SOURCE_AUTHORITY" in result["error_codes"]
    assert "SOURCE_CAPSULE_PRIVATE_BODY_LEAK" in result["error_codes"]
    assert "DUPLICATE_PATTERN_BINDING_CONFLICT" in result["error_codes"]
    assert "BINDING_PASS_OVERCLAIMS_PUBLIC_LEAF" in result["error_codes"]
    assert "UNSUPPORTED_AUTHORITY_HANDLE_IMPLIED_AUTHORITY" in result["error_codes"]


def test_pattern_binding_receipts_are_redacted_and_complete(tmp_path: Path) -> None:
    out_dir = tmp_path / "receipts"

    validate(PATTERN_FIXTURE_INPUT, out_dir, command="pytest")

    result = json.loads((out_dir / "pattern_binding_validation_result.json").read_text(encoding="utf-8"))
    capsules = json.loads((out_dir / "source_capsules.json").read_text(encoding="utf-8"))
    omission = json.loads((out_dir / "omission_receipt.json").read_text(encoding="utf-8"))
    authority = json.loads((out_dir / "authority_chain_handle_resolver_receipt.json").read_text(encoding="utf-8"))

    for key in ("status", "organ_id", "fixture_id", "private_state_scan", "authority_ceiling", "anti_claim", "receipt_paths"):
        assert key in result
    assert result["private_state_scan"]["body_redacted"] is True
    assert all("body" not in row for row in capsules["source_capsules"])
    assert capsules["source_capsules"][0]["body_redacted"] is True
    assert omission["omitted_files"] == capsules["source_capsule_count"]
    assert authority["authority_chain_resolution_status"] == "pass"


def test_cold_clone_receipts_use_public_relative_paths(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "fixtures", public_root / "fixtures")

    cold_clone_receipt = run_probe(public_root)
    write_receipt(public_root / "receipts/cold_clone_probe.json", cold_clone_receipt)

    assert cold_clone_receipt["status"] == "pass"
    for receipt_path in ["receipts/cold_clone_probe.json", *PATTERN_RECEIPTS]:
        assert (public_root / receipt_path).is_file()

    result = json.loads(
        (public_root / "receipts/first_wave/pattern_binding_contract/pattern_binding_validation_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["missing_negative_cases"] == []
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert set(result["expected_negative_cases"]) == set(result["observed_negative_cases"])
    assert all(path.startswith("receipts/") for path in result["receipt_paths"])

    for hit in result["private_state_scan"]["hits"]:
        assert not Path(hit["path"]).is_absolute()
        assert hit["body_redacted"] is True
        assert "matched_excerpt" not in hit
        assert "body" not in hit

    for receipt_file in (public_root / "receipts").rglob("*.json"):
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "/Users/willcook" not in text
        assert "src/ai_workflow" not in text


def test_strict_json_duplicate_keys_fail() -> None:
    with pytest.raises(DuplicateJsonKeyError):
        loads_json_strict('{"a": 1, "a": 2}', "duplicate_fixture")
