from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from microcosm_core.cold_clone_probe import PATTERN_RECEIPTS, run_probe
from microcosm_core.organs.pattern_binding_contract import (
    EXPECTED_NEGATIVE_CASES,
    validate,
    validate_substrate_bundle,
)
from microcosm_core.receipts import write_receipt
from microcosm_core.schemas import DuplicateJsonKeyError, loads_json_strict


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PATTERN_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/pattern_binding_contract/input"
PATTERN_EXPORTED_BUNDLE_INPUT = MICROCOSM_ROOT / "examples/pattern_binding_contract/exported_substrate_bundle"


def _walk_keys(payload: object) -> list[str]:
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
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["fixture_role"] == "regression_negative_harness_with_positive_control"
    assert "private_state_scan" not in result
    assert "body_redacted" not in result


def test_pattern_binding_receipts_are_secret_excluded_and_complete(tmp_path: Path) -> None:
    out_dir = tmp_path / "receipts"

    validate(PATTERN_FIXTURE_INPUT, out_dir, command="pytest")

    result = json.loads((out_dir / "pattern_binding_validation_result.json").read_text(encoding="utf-8"))
    capsules = json.loads((out_dir / "source_capsules.json").read_text(encoding="utf-8"))
    omission = json.loads((out_dir / "omission_receipt.json").read_text(encoding="utf-8"))
    authority = json.loads((out_dir / "authority_chain_handle_resolver_receipt.json").read_text(encoding="utf-8"))

    for key in (
        "status",
        "organ_id",
        "fixture_id",
        "secret_exclusion_scan",
        "body_in_receipt",
        "real_runtime_receipt",
        "synthetic_receipt_standin_allowed",
        "authority_ceiling",
        "anti_claim",
        "receipt_paths",
    ):
        assert key in result
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert all("body" not in row for row in capsules["source_capsules"])
    assert capsules["source_capsules"][0]["body_in_receipt"] is False
    assert omission["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert omission["non_inlined_source_ref_count"] == capsules["source_capsule_count"]
    assert omission["synthetic_receipt_standin_allowed"] is False
    assert authority["authority_chain_resolution_status"] == "pass"
    assert authority["body_in_receipt"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in result


def test_pattern_binding_accepts_exported_substrate_bundle(tmp_path: Path) -> None:
    out_dir = tmp_path / "receipts"

    result = validate_substrate_bundle(PATTERN_EXPORTED_BUNDLE_INPUT, out_dir, command="pytest")

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_substrate_bundle"
    assert result["bundle_id"] == "public_pattern_binding_runtime_example"
    assert result["accepted_count"] == 2
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["public_runtime_refs"] == [
        "examples/pattern_binding_contract/exported_substrate_bundle/pattern_rows.jsonl::public_runtime_pattern_deliverables_registry",
        "examples/pattern_binding_contract/exported_substrate_bundle/pattern_rows.jsonl::public_runtime_source_capsule_provenance",
    ]
    assert result["receipt_paths"] == [
        "receipts/exported_substrate_bundle_validation_result.json"
    ]

    receipt = json.loads((out_dir / "exported_substrate_bundle_validation_result.json").read_text(encoding="utf-8"))
    assert receipt["input_mode"] == "exported_substrate_bundle"
    assert all(path.startswith("receipts/") for path in receipt["receipt_paths"])
    assert "matched_excerpt" not in json.dumps(receipt, sort_keys=True)
    assert "body" not in _walk_keys(receipt)
    assert "private_state_scan" not in receipt
    assert "body_redacted" not in receipt


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

    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in result

    for hit in result["secret_exclusion_scan"]["hits"]:
        assert not Path(hit["path"]).is_absolute()
        assert hit["body_in_receipt"] is False
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
