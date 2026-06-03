from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import microcosm_core.organs.routing_anti_patterns_registry as routing_registry
from microcosm_core.organs.routing_anti_patterns_registry import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_routing_anti_patterns_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT / "fixtures/first_wave/routing_anti_patterns_registry/input"
)
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/routing_anti_patterns_registry/exported_routing_anti_patterns_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"
ROUTING_SOURCE_MODULE_IDS = {
    "routing_anti_patterns_macro_registry_body_import",
}


def _fixture_anti_pattern_count(input_dir: Path = FIXTURE_INPUT) -> int:
    payload = json.loads(
        (input_dir / "routing_anti_patterns.json").read_text(encoding="utf-8")
    )
    return len(
        [row for row in payload.get("anti_patterns", []) if isinstance(row, dict)]
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


def test_routing_anti_patterns_registry_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/routing_anti_patterns_registry",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/routing_anti_patterns_registry_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["observed_negative_cases"]["source_authority_masquerade"] == [
        "ROUTING_ANTI_PATTERN_SOURCE_AUTHORITY_FORBIDDEN"
    ]
    assert result["anti_pattern_count"] == _fixture_anti_pattern_count()
    assert "kernel_before_grep" in result["covered_anti_pattern_ids"]
    assert "bridge_before_scope" in result["covered_anti_pattern_ids"]
    assert "mode_in_chat_only" in result["covered_anti_pattern_ids"]
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["authority_ceiling"]["route_policy_mutation_authorized"] is False
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in _walk_keys(result)
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_routing_anti_patterns_registry_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_routing_anti_patterns_bundle(
        EXPORTED_BUNDLE,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/routing_anti_patterns_registry",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_routing_anti_patterns_bundle"
    assert result["bundle_id"] == "public_routing_anti_patterns_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["anti_pattern_count"] == _fixture_anti_pattern_count(EXPORTED_BUNDLE)
    assert "kernel_before_grep" in result["covered_anti_pattern_ids"]
    assert "bridge_before_scope" in result["covered_anti_pattern_ids"]
    assert "mode_in_chat_only" in result["covered_anti_pattern_ids"]
    assert result["authority_ceiling"]["whole_system_correctness_claim"] is False
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_manifest_ref"].endswith("source_module_manifest.json")
    assert result["body_copied_material_count"] == 1
    source_imports = result["source_open_body_imports"]
    assert source_imports["status"] == "pass"
    assert source_imports["body_material_count"] == 1
    assert set(source_imports["body_material_ids"]) == ROUTING_SOURCE_MODULE_IDS
    assert source_imports["body_material_classes"] == {"public_macro_pattern_body": 1}
    assert source_imports["body_in_receipt"] is False
    assert source_imports["body_text_in_receipt"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in _walk_keys(result)


def test_routing_anti_patterns_registry_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    example_root = public_root / "examples/routing_anti_patterns_registry"
    shutil.copytree(EXPORTED_BUNDLE.parent, example_root)
    bundle = example_root / "exported_routing_anti_patterns_bundle"
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bad_digest = "0" * 64
    manifest["modules"][0]["sha256"] = bad_digest
    manifest["modules"][0]["source_sha256"] = bad_digest
    manifest["modules"][0]["target_sha256"] = bad_digest
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    result = run_routing_anti_patterns_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/routing_anti_patterns_registry",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "ROUTING_ANTI_PATTERN_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_routing_anti_patterns_registry_rejects_partial_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    example_root = public_root / "examples/routing_anti_patterns_registry"
    shutil.copytree(EXPORTED_BUNDLE.parent, example_root)
    bundle = example_root / "exported_routing_anti_patterns_bundle"
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    result = run_routing_anti_patterns_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/routing_anti_patterns_registry",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "ROUTING_ANTI_PATTERN_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_routing_anti_patterns_registry_rejects_partial_target_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    example_root = public_root / "examples/routing_anti_patterns_registry"
    shutil.copytree(EXPORTED_BUNDLE.parent, example_root)
    bundle = example_root / "exported_routing_anti_patterns_bundle"
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    result = run_routing_anti_patterns_bundle(
        bundle,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/routing_anti_patterns_registry",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert "ROUTING_ANTI_PATTERN_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]


def test_routing_anti_patterns_registry_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/routing_anti_patterns_registry"
    )
    args = [
        "run-bundle",
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
    assert first_card["routing_anti_pattern_projection"]["anti_pattern_count"] == (
        _fixture_anti_pattern_count(EXPORTED_BUNDLE)
    )
    assert first_card["source_open_body_imports"]["status"] == "pass"
    assert first_card["source_open_body_imports"]["body_material_count"] == 1
    assert "covered_anti_pattern_ids" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(routing_registry, "_build_result", fail_if_rebuilt)

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]
    assert cached_card["source_open_body_imports"] == first_card["source_open_body_imports"]


def test_routing_anti_patterns_sha256_streams_without_materializing_file(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "routing_anti_patterns.json"
    marker = b'{"anti_pattern_id":"kernel_before_grep"}\n'
    body = (
        marker * (routing_registry.HASH_CHUNK_SIZE // len(marker) + 2)
    ) + b'{"tail":true}\n'
    source.write_bytes(body)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path) -> bytes:
        if self == source:
            raise AssertionError("digest should stream source-module input")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert routing_registry._sha256(source) == hashlib.sha256(body).hexdigest()


def test_routing_anti_patterns_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    modules = manifest["modules"]

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 1
    assert {row["module_id"] for row in modules} == ROUTING_SOURCE_MODULE_IDS

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


def test_routing_anti_patterns_receipts_use_secret_exclusion(
    tmp_path: Path,
) -> None:
    out = tmp_path / "receipts/first_wave/routing_anti_patterns_registry"
    run(FIXTURE_INPUT, out, command="pytest")

    receipt_file = out / "routing_anti_patterns_registry_validation_receipt.json"
    text = receipt_file.read_text(encoding="utf-8")
    payload = json.loads(text)

    assert payload["status"] == "pass"
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["body_in_receipt"] is False
    assert payload["real_runtime_receipt"] is True
