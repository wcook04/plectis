from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import microcosm_core.organs.cognitive_operator_registry as cognitive_operator_registry
from microcosm_core.organs.cognitive_operator_registry import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    _sha256,
    main,
    run,
    run_registry_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/cognitive_operator_registry/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/cognitive_operator_registry/exported_cognitive_operator_registry_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"
COGNITIVE_OPERATOR_SOURCE_MODULE_IDS = {
    "cognitive_operator_registry_macro_registry_body_import",
    "cognitive_operator_registry_macro_standard_body_import",
    "cognitive_operator_registry_macro_validator_body_import",
}


def _fixture_operator_count(input_dir: Path = FIXTURE_INPUT) -> int:
    payload = json.loads((input_dir / "operator_registry.json").read_text(encoding="utf-8"))
    return len(
        [row for row in payload.get("operators", []) if isinstance(row, dict)]
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


def test_cognitive_operator_registry_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/cognitive_operator_registry",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/cognitive_operator_registry_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    expected_count = _fixture_operator_count()
    assert result["operator_count"] == expected_count
    assert result["active_operator_count"] == expected_count
    assert result["dogfood_receipt_count"] == expected_count
    assert result["required_field_count"] == 11
    assert "cogop_landing_handoff_compiler" in result["covered_operator_ids"]
    assert "cogop_pressure_to_action_reducer" in result["covered_operator_ids"]
    assert "cogop_operator_accretion_governor" in result["covered_operator_ids"]
    assert result["authority_ceiling"]["release_authorized"] is False
    assert (
        result["authority_ceiling"]["cognitive_operator_registry_mutation_authority"]
        is False
    )
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert any(
        ref.endswith("core/organ_registry.json")
        for ref in result["public_runtime_refs"]
    )
    assert "private_state_scan" not in result
    assert "body_redacted" not in _walk_keys(result)
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_cognitive_operator_registry_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_registry_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/cognitive_operator_registry",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_cognitive_operator_registry_bundle"
    assert result["bundle_id"] == "public_cognitive_operator_registry_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["operator_count"] == _fixture_operator_count(EXPORTED_BUNDLE)
    assert result["active_operator_count"] == _fixture_operator_count(EXPORTED_BUNDLE)
    assert "cogop_landing_handoff_compiler" in result["covered_operator_ids"]
    assert "cogop_pressure_to_action_reducer" in result["covered_operator_ids"]
    assert "cogop_operator_accretion_governor" in result["covered_operator_ids"]
    assert result["authority_ceiling"]["whole_system_correctness_claim"] is False
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_manifest_ref"].endswith("source_module_manifest.json")
    assert result["body_copied_material_count"] == 3
    source_imports = result["source_open_body_imports"]
    assert source_imports["status"] == "pass"
    assert source_imports["body_material_count"] == 3
    assert set(source_imports["body_material_ids"]) == COGNITIVE_OPERATOR_SOURCE_MODULE_IDS
    assert source_imports["body_material_classes"] == {
        "public_macro_standard_body": 1,
        "public_macro_tool_body": 2,
    }
    assert source_imports["body_in_receipt"] is False
    assert source_imports["body_text_in_receipt"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in _walk_keys(result)


def test_cognitive_operator_registry_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = tmp_path / "receipts/runtime_shell/demo_project/organs/cognitive_operator_registry"
    args = [
        "run-registry-bundle",
        "--input",
        str(EXPORTED_BUNDLE),
        "--out",
        str(out),
        "--card",
    ]

    assert main(args) == 0
    first_card = json.loads(capsys.readouterr().out)
    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["command_speed"]["receipt_reused"] is False
    assert first_card["command_speed"]["freshness_missing_path_count"] == 0
    assert first_card["operator_projection"]["operator_count"] == (
        _fixture_operator_count(EXPORTED_BUNDLE)
    )
    assert first_card["source_open_body_imports"]["status"] == "pass"
    assert first_card["source_open_body_imports"]["body_material_count"] == 3
    assert "covered_operator_ids" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(cognitive_operator_registry, "_build_result", fail_if_rebuilt)

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]
    assert cached_card["source_open_body_imports"] == first_card["source_open_body_imports"]


def test_cognitive_operator_registry_sha256_streams_source_modules(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "source_module.py"
    payload = b"cognitive operator body\n" * 4096
    source.write_bytes(payload)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path) -> bytes:
        if self == source:
            raise AssertionError("source modules should be hashed without read_bytes")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert _sha256(source) == hashlib.sha256(payload).hexdigest()


def test_cognitive_operator_registry_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    modules = manifest["modules"]

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 3
    assert {row["module_id"] for row in modules} == COGNITIVE_OPERATOR_SOURCE_MODULE_IDS

    for row in modules:
        source_path = MICROCOSM_ROOT.parent / row["source_ref"]
        target_path = MICROCOSM_ROOT.parent / row["target_ref"]
        source_bytes = source_path.read_bytes()
        target_bytes = target_path.read_bytes()
        digest = hashlib.sha256(source_bytes).hexdigest()

        assert source_bytes == target_bytes
        assert row["source_import_class"] == "copied_non_secret_macro_body"
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        assert row["sha256"] == digest
        assert row["source_sha256"] == digest
        assert row["target_sha256"] == digest
        text = target_bytes.decode("utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in text


def test_cognitive_operator_registry_receipts_use_secret_exclusion(tmp_path: Path) -> None:
    out = tmp_path / "receipts/first_wave/cognitive_operator_registry"
    run(FIXTURE_INPUT, out, command="pytest")

    receipt_file = out / "cognitive_operator_registry_validation_receipt.json"
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert payload["status"] == "pass"
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["body_in_receipt"] is False
    assert payload["real_runtime_receipt"] is True
    assert payload["synthetic_receipt_standin_allowed"] is False
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
    assert "private_state_scan" not in payload
    assert "body_redacted" not in _walk_keys(payload)
