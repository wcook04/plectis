from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.cold_clone_probe import PATTERN_RECEIPTS, run_probe
from microcosm_core.organs import pattern_binding_contract as pattern_binding
from microcosm_core.organs.pattern_binding_contract import (
    EXPECTED_NEGATIVE_CASES,
    result_card,
    validate,
    validate_substrate_bundle,
)
from microcosm_core.macro_tools.pattern_route_readiness import validate_route_readiness_bundle
from microcosm_core.receipts import write_receipt
from microcosm_core.schemas import DuplicateJsonKeyError, loads_json_strict


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PATTERN_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/pattern_binding_contract/input"
PATTERN_EXPORTED_BUNDLE_INPUT = MICROCOSM_ROOT / "examples/pattern_binding_contract/exported_substrate_bundle"
ROUTE_READINESS_BUNDLE_INPUT = MICROCOSM_ROOT / "examples/pattern_binding_contract/exported_route_readiness_bundle"
MACRO_PATTERN_LEDGER = (
    MICROCOSM_ROOT
    / "examples/macro_projection_import_protocol/exported_projection_import_bundle/pattern_ledger_rows.jsonl"
)
MACRO_PATTERN_BINDINGS = PATTERN_EXPORTED_BUNDLE_INPUT / "extracted_pattern_substrate_bindings.json"


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
    macro_rows = [
        json.loads(line)
        for line in MACRO_PATTERN_LEDGER.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    macro_sha256 = hashlib.sha256(MACRO_PATTERN_LEDGER.read_bytes()).hexdigest()
    bindings = json.loads(MACRO_PATTERN_BINDINGS.read_text(encoding="utf-8"))
    bindings_sha256 = hashlib.sha256(MACRO_PATTERN_BINDINGS.read_bytes()).hexdigest()

    result = validate_substrate_bundle(PATTERN_EXPORTED_BUNDLE_INPUT, out_dir, command="pytest")

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_substrate_bundle"
    assert result["bundle_id"] == "public_pattern_binding_real_pattern_ledger_bundle"
    assert result["accepted_count"] == 373
    assert result["accepted_count"] == len(macro_rows)
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["accepted_count_is_product_progress"] is False
    assert result["counts_as_real_substrate_progress"] is True
    assert result["substrate_import_status"] == "real_pattern_ledger_import"
    assert result["real_substrate_progress_count"] == 373
    assert result["runtime_metadata_only_row_count"] == 0
    assert result["legacy_runtime_metadata_row_count"] == 2
    assert result["legacy_runtime_metadata_only_row_count"] == 2
    assert result["real_pattern_ledger_consumed"] is True
    assert result["real_pattern_ledger_source"] == {
        "status": "pass",
        "source_ref": "examples/macro_projection_import_protocol/exported_projection_import_bundle/pattern_ledger_rows.jsonl",
        "row_count": 373,
        "sha256": macro_sha256,
        "expected_sha256": macro_sha256,
        "expected_row_count": 373,
        "normalized_pattern_row_count": 373,
    }
    assert result["real_pattern_substrate_bindings_consumed"] is True
    assert result["real_pattern_substrate_bindings_source"]["source_ref"] == (
        "examples/pattern_binding_contract/exported_substrate_bundle/extracted_pattern_substrate_bindings.json"
    )
    assert result["real_pattern_substrate_bindings_source"]["source_row_count"] == 373
    assert result["real_pattern_substrate_bindings_source"]["sha256"] == bindings_sha256
    assert result["real_pattern_substrate_bindings_source"]["expected_sha256"] == bindings_sha256
    assert result["real_pattern_substrate_bindings_source"]["detailed_binding_count"] == len(
        bindings["pattern_bindings"]
    )
    assert result["real_pattern_substrate_bindings_source"]["detailed_binding_count"] == 94
    assert result["real_pattern_substrate_bindings_source"]["binding_category_counts"]["standards"] >= 1
    assert result["real_pattern_substrate_bindings_source"]["binding_category_counts"]["paper_modules"] >= 1
    assert result["real_pattern_substrate_bindings_source"]["binding_category_counts"]["tests_validators_proofs"] >= 1
    assert result["real_pattern_route_readiness_consumed"] is True
    assert result["body_copied_material_count"] == 5
    source_imports = result["source_open_body_imports"]
    assert source_imports["status"] == "pass"
    assert source_imports["body_material_count"] == 5
    assert source_imports["body_in_receipt"] is False
    assert set(source_imports["body_material_ids"]) == {
        "pattern_binding_macro_pattern_ledger_body_import",
        "pattern_binding_route_readiness_validator_tool_body_import",
        "pattern_binding_route_readiness_standard_body_import",
        "pattern_binding_public_first_slice_execution_receipt_body_import",
        "pattern_binding_macro_standard_manifest_row_body_import",
    }
    assert source_imports["material_classes"] == [
        "public_macro_pattern_body",
        "public_macro_receipt_body",
        "public_macro_standard_body",
        "public_macro_tool_body",
    ]
    source_modules = result["source_module_imports"]
    assert source_modules["status"] == "pass"
    assert source_modules["module_count"] == 5
    assert all(module["body_in_receipt"] is False for module in source_modules["modules"])
    assert all(module["sha256"] == module["actual_sha256"] for module in source_modules["modules"])
    assert result["route_readiness_error_rules"] == []
    route_readiness = result["real_pattern_route_readiness_source"]
    assert route_readiness["status"] == "pass"
    assert route_readiness["source_import_class"] == "source_faithful_refactor"
    assert route_readiness["route_readiness_summary"]["ledger_pattern_count"] == 373
    assert route_readiness["route_readiness_summary"]["route_card_count"] == 9
    assert route_readiness["route_readiness_summary"]["fixture_spec_count"] == 18
    assert route_readiness["route_readiness_summary"]["standalone_pattern_leaf_candidate_count"] == 0
    assert route_readiness["selection_contract"]["hard_no_standalone_pattern_id_count"] == 118
    assert "row_to_organ_router" in route_readiness["selection_contract"]["selector_must_open"]
    assert result["truth_accounting"]["pattern_row_count"] == 373
    assert result["truth_accounting"]["runtime_example_bundle"] is False
    assert result["truth_accounting"]["runtime_metadata_only_row_count"] == 0
    assert result["truth_accounting"]["real_pattern_ledger_row_count"] == 373
    assert len(result["public_runtime_refs"]) == 373 + len(bindings["pattern_bindings"]) + 13
    assert result["public_runtime_refs"][0].startswith(
        "examples/"
    )
    assert any(
        ref.startswith(
            "examples/pattern_binding_contract/exported_substrate_bundle/extracted_pattern_substrate_bindings.json::"
        )
        for ref in result["public_runtime_refs"]
    )
    assert "examples/pattern_binding_contract/exported_route_readiness_bundle/extracted_pattern_route_readiness_audit.json" in result["public_runtime_refs"]
    assert result["receipt_paths"] == [
        "receipts/exported_substrate_bundle_validation_result.json",
        "receipts/route_readiness/exported_route_readiness_bundle_validation_result.json",
    ]

    receipt = json.loads((out_dir / "exported_substrate_bundle_validation_result.json").read_text(encoding="utf-8"))
    assert receipt["input_mode"] == "exported_substrate_bundle"
    assert receipt["accepted_count_is_product_progress"] is False
    assert receipt["counts_as_real_substrate_progress"] is True
    assert receipt["truth_accounting"]["substrate_import_status"] == "real_pattern_ledger_import"
    assert receipt["real_pattern_ledger_source"]["sha256"] == macro_sha256
    assert receipt["real_pattern_substrate_bindings_source"]["sha256"] == bindings_sha256
    assert receipt["real_pattern_route_readiness_consumed"] is True
    assert receipt["real_pattern_route_readiness_source"]["route_readiness_summary"]["ledger_pattern_count"] == 373
    assert receipt["source_open_body_imports"]["body_material_count"] == 5
    assert receipt["body_copied_material_count"] == 5
    assert all(path.startswith("receipts/") for path in receipt["receipt_paths"])
    assert "matched_excerpt" not in json.dumps(receipt, sort_keys=True)
    assert "body" not in _walk_keys(receipt)
    assert "private_state_scan" not in receipt
    assert "body_redacted" not in receipt


def test_pattern_binding_substrate_bundle_accepts_installed_share_root(tmp_path: Path) -> None:
    public_root = tmp_path / "share/microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/pattern_binding_contract",
        public_root / "examples/pattern_binding_contract",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "examples/macro_projection_import_protocol",
        public_root / "examples/macro_projection_import_protocol",
    )
    input_dir = public_root / "examples/pattern_binding_contract/exported_substrate_bundle"

    result = validate_substrate_bundle(input_dir, tmp_path / "receipts", command="pytest")

    assert result["status"] == "pass"
    assert result["real_pattern_ledger_consumed"] is True
    assert result["real_pattern_substrate_bindings_consumed"] is True
    assert result["real_pattern_route_readiness_consumed"] is True
    assert result["public_runtime_refs"][0].startswith("examples/")
    assert str(public_root) not in json.dumps(result, sort_keys=True)


def test_pattern_binding_substrate_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    out_dir = tmp_path / "receipts"

    result = validate_substrate_bundle(
        PATTERN_EXPORTED_BUNDLE_INPUT,
        out_dir,
        command="pytest --card",
        reuse_fresh_receipt=True,
    )

    assert result["status"] == "pass"
    assert result["receipt_reused"] is False
    assert result["card_schema_version"] == "pattern_binding_contract_card_v1"
    card = result_card(result)
    assert card["receipt_reused"] is False
    assert card["accepted_count"] == 373
    assert card["real_substrate_progress_count"] == 373
    assert card["source_module_count"] == 5
    assert card["body_copied_material_count"] == 5
    assert card["route_readiness_summary"]["ledger_pattern_count"] == 373
    assert card["public_runtime_ref_count"] == 480
    assert card["freshness_digest"] == result["freshness_digest"]
    assert "source_module_imports" in card["omitted_full_payload_keys"]
    assert "accepted_pattern_ids" in card["omitted_full_payload_keys"]
    assert "source_module_imports" not in card
    assert "accepted_pattern_ids" not in card
    assert str(tmp_path) not in json.dumps(card, sort_keys=True)

    def fail_if_rebuilt(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the pattern-binding substrate receipt")

    monkeypatch.setattr(pattern_binding, "validate_source_module_imports", fail_if_rebuilt)
    monkeypatch.setattr(
        pattern_binding.pattern_route_readiness,
        "validate_route_readiness_bundle",
        fail_if_rebuilt,
    )

    cached = validate_substrate_bundle(
        PATTERN_EXPORTED_BUNDLE_INPUT,
        out_dir,
        command="pytest --card",
        reuse_fresh_receipt=True,
    )
    cached_card = result_card(cached)

    assert cached["status"] == "pass"
    assert cached["receipt_reused"] is True
    assert cached["freshness_digest"] == result["freshness_digest"]
    assert cached_card["receipt_reused"] is True
    assert cached_card["source_module_count"] == 5


def test_pattern_binding_source_module_digest_tamper_blocks_bundle(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "exported_substrate_bundle"
    shutil.copytree(PATTERN_EXPORTED_BUNDLE_INPUT, bundle_dir)
    source_body = (
        bundle_dir
        / "source_artifacts/macro_state/microcosm_portfolio/reconstruction/public_first_slice_build_execution_receipt_v1.json"
    )
    source_body.write_text(source_body.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    result = validate_substrate_bundle(bundle_dir, tmp_path / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert result["source_open_body_imports"]["status"] == "blocked"
    assert result["body_copied_material_count"] == 5
    assert "PATTERN_BINDING_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["body_in_receipt"] is False


def test_route_readiness_bundle_validator_rejects_row_level_leaf_authority(tmp_path: Path) -> None:
    out_dir = tmp_path / "receipts"

    result = validate_route_readiness_bundle(ROUTE_READINESS_BUNDLE_INPUT, out_dir, command="pytest")

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_route_readiness_bundle"
    assert result["source_import_class"] == "source_faithful_refactor"
    assert result["route_readiness_summary"]["ledger_pattern_count"] == 373
    assert result["route_readiness_summary"]["standalone_pattern_leaf_candidate_count"] == 0
    assert result["selection_contract"]["hard_no_standalone_pattern_id_count"] == 118
    assert result["selection_contract"]["root_substrate_sequence"] == [
        "root_binding_and_executable_grammar",
        "proof_diagnostic_evidence_spine",
        "navigation_hologram_route_plane",
        "mission_transaction_work_spine",
    ]
    assert set(result["selection_contract"]["selector_must_open"]) >= {
        "row_to_organ_router",
        "organ_route_cards",
        "organ_fixture_specs",
        "route_readiness_audit",
    }
    assert result["route_readiness_report"]["findings"] == []
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert "matched_excerpt" not in json.dumps(result, sort_keys=True)
    assert "body" not in _walk_keys(result)
    assert "private_state_scan" not in result


def test_route_readiness_bundle_validator_accepts_installed_share_root(tmp_path: Path) -> None:
    public_root = tmp_path / "share/microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/pattern_binding_contract",
        public_root / "examples/pattern_binding_contract",
    )
    input_dir = public_root / "examples/pattern_binding_contract/exported_route_readiness_bundle"

    result = validate_route_readiness_bundle(input_dir, tmp_path / "receipts", command="pytest")

    assert result["status"] == "pass"
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["public_runtime_refs"][0].startswith(
        "examples/pattern_binding_contract/exported_route_readiness_bundle/"
    )
    assert str(public_root) not in json.dumps(result, sort_keys=True)


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
        assert "/Users/example" not in text
        assert "src/ai_workflow" not in text


def test_strict_json_duplicate_keys_fail() -> None:
    with pytest.raises(DuplicateJsonKeyError):
        loads_json_strict('{"a": 1, "a": 2}', "duplicate_fixture")
