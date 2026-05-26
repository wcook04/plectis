from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import microcosm_core.organs.cold_reader_route_map as cold_reader_route_map
from microcosm_core.organs.cold_reader_route_map import (
    BUNDLE_RESULT_NAME,
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_route_map_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
MACRO_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/cold_reader_route_map/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle"
)
SOURCE_MODULE_MANIFEST = BUNDLE_INPUT / "source_module_manifest.json"
COLD_READER_SOURCE_MODULE_IDS = {
    "agent_instruction_router_body_import",
    "agent_entry_reference_body_import",
    "kernel_bootstrap_skill_body_import",
    "kernel_navigation_seed_skill_body_import",
    "kernel_entry_packet_command_body_import",
}


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
    assert result["route_count"] == 10
    assert result["command_count"] == 10
    assert result["receipt_ref_count"] >= 10
    assert result["first_run_sequence"][:3] == [
        "tour_project",
        "status_card",
        "proof_lab",
    ]
    assert result["front_door_route_ids"] == [
        "tour_project",
        "status_card",
        "proof_lab",
    ]
    assert result["front_door_command_count"] == 3
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
        "proof_lab",
        "status_card",
        "tour_project",
    ]
    assert result["first_run_sequence"][:3] == [
        "tour_project",
        "status_card",
        "proof_lab",
    ]
    assert result["front_door_command_count"] == 3
    assert "microcosm-substrate/src/microcosm_core/runtime_shell.py" in result["source_refs"]
    assert "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle" in result[
        "public_runtime_refs"
    ]
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_count"] == len(COLD_READER_SOURCE_MODULE_IDS)
    assert result["copied_source_module_count"] == len(COLD_READER_SOURCE_MODULE_IDS)
    assert set(row["module_id"] for row in result["source_module_results"]) == (
        COLD_READER_SOURCE_MODULE_IDS
    )
    assert all(row["digest_match"] for row in result["source_module_results"])
    assert all(row["anchor_status"] == "pass" for row in result["source_module_results"])
    assert "docs/agent_instruction_router.md" in result["real_substrate_refs"]
    assert (
        "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle/"
        "source_modules/system/lib/kernel/commands/comprehension_snapshot.py"
    ) in result["real_substrate_refs"]
    assert result["body_import_verification"]["verification_status"] == "pass"
    assert result["real_runtime_receipt"] is True
    assert result["synthetic_receipt_standin_allowed"] is False
    assert "private_state_scan" not in result
    assert "body_redacted" not in _walk_keys(result)


def test_cold_reader_source_manifest_matches_exact_macro_sources() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == len(COLD_READER_SOURCE_MODULE_IDS)
    assert set(row["module_id"] for row in manifest["modules"]) == (
        COLD_READER_SOURCE_MODULE_IDS
    )
    for row in manifest["modules"]:
        source = MACRO_ROOT / row["source_ref"]
        target = MICROCOSM_ROOT / Path(row["target_ref"]).relative_to(
            "microcosm-substrate"
        )
        assert source.is_file(), row["source_ref"]
        assert target.is_file(), row["target_ref"]
        assert source.read_bytes() == target.read_bytes()
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert row["sha256"] == digest
        assert row["source_to_target_relation"] == "exact_copy"
        assert row["body_in_receipt"] is False
        for anchor in row["required_anchors"]:
            assert anchor in target.read_text(encoding="utf-8")


def test_cold_reader_fixture_manifest_counts_source_open_body_floor() -> None:
    manifest = json.loads(
        (MICROCOSM_ROOT / "core/fixture_manifests/cold_reader_route_map.fixture_manifest.json")
        .read_text(encoding="utf-8")
    )

    source_imports = manifest["source_open_body_imports"]
    assert manifest["body_copied_material_count"] == len(COLD_READER_SOURCE_MODULE_IDS)
    assert source_imports["status"] == "pass"
    assert source_imports["source_import_class"] == "copied_non_secret_macro_body"
    assert source_imports["body_material_count"] == len(COLD_READER_SOURCE_MODULE_IDS)
    assert set(source_imports["body_material_ids"]) == COLD_READER_SOURCE_MODULE_IDS
    assert source_imports["body_in_receipt"] is False
    assert (
        source_imports["aggregate_floor_ref"]
        == "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle/source_module_manifest.json::modules"
    )


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


def test_cold_reader_exported_bundle_receipt_omits_source_bodies(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        BUNDLE_INPUT,
        public_root / "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle",
    )
    result = run_route_map_bundle(
        public_root / "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle",
        public_root / "receipts/runtime_shell/demo_project/organs/cold_reader_route_map",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["source_module_manifest_status"] == "pass"
        assert payload["source_module_count"] == len(COLD_READER_SOURCE_MODULE_IDS)
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["body_import_verification"]["body_in_receipt"] is False
        assert "body_redacted" not in _walk_keys(payload)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_cold_reader_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out_dir = tmp_path / "receipts/runtime_shell/demo_project/organs/cold_reader_route_map"
    args = [
        "run-route-map-bundle",
        "--input",
        str(BUNDLE_INPUT),
        "--out",
        str(out_dir),
        "--card",
    ]

    assert main(args) == 0
    first_card = json.loads(capsys.readouterr().out)
    receipt_path = out_dir / BUNDLE_RESULT_NAME
    assert receipt_path.is_file()
    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["cache_status"] == "rebuilt"
    assert first_card["route_map"]["route_count"] == 10
    assert first_card["route_map"]["first_run_sequence_head"] == [
        "tour_project",
        "status_card",
        "proof_lab",
    ]
    assert first_card["source_import_floor"]["source_module_count"] == len(
        COLD_READER_SOURCE_MODULE_IDS
    )
    assert first_card["output_economy"]["source_bodies_exported"] is False
    assert "source_module_results" in first_card["output_economy"]["omitted_payload_keys"]

    def fail_build(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the written receipt")

    monkeypatch.setattr(cold_reader_route_map, "_build_result", fail_build)

    assert main(args) == 0
    cached_stdout = capsys.readouterr().out
    cached_card = json.loads(cached_stdout)
    assert cached_card["cache_status"] == "fresh_exported_bundle_receipt_reused"
    assert cached_card["freshness_basis"]["missing_path_count"] == 0
    assert cached_card["route_map"]["front_door_command_count"] == 3
    assert len(cached_stdout.encode("utf-8")) < receipt_path.stat().st_size
