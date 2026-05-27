from __future__ import annotations

import hashlib
import json
import py_compile
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import world_model_projection_drift_control_room
from microcosm_core.organs.world_model_projection_drift_control_room import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_drift_control_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/world_model_projection_drift_control_room/input"
)
FIXTURE_MANIFEST = (
    MICROCOSM_ROOT
    / "core/fixture_manifests/world_model_projection_drift_control_room.fixture_manifest.json"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/world_model_projection_drift_control_room/"
    "exported_projection_drift_control_bundle"
)
SOURCE_MODULE_IDS = [
    "world_model_drift_aggregate_source_body_import",
    "world_model_drift_endpoint_source_body_import",
    "view_quality_action_map_source_body_import",
    "view_quality_action_map_test_body_import",
]


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


def test_world_model_projection_drift_control_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/world_model_projection_drift_control_room",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "world_model_projection_drift_control_room_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["selected_route_id"] == "world_model_projection_drift_control_room"
    assert result["drift_summary"]["row_count"] == 8
    assert result["drift_summary"]["source_ref_count"] == 8
    assert result["drift_summary"]["repair_route_count"] == 8
    assert result["drift_summary"]["validation_ref_count"] == 8
    assert result["negative_case_summary"]["expected_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["observed_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["authority_ceiling"]["source_authority_claim"] is False
    assert result["authority_ceiling"]["live_route_repair_authorized"] is False
    assert result["authority_ceiling"]["automatic_doctrine_promotion_authorized"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    for case_id, codes in EXPECTED_NEGATIVE_CASES.items():
        assert result["negative_case_summary"]["observed_codes"][case_id] == codes


def test_world_model_projection_drift_receipts_consume_public_runtime_refs(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/world_model_projection_drift_control_room",
        public_root / "fixtures/first_wave/world_model_projection_drift_control_room",
    )

    result = run(
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input",
        public_root / "receipts/first_wave/world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["body_import_status"] == "real_runtime_receipt_landed"
    assert result["body_in_receipt"] is False
    assert result["body_import_verification"]["classification"] == "real_runtime_receipt"
    assert result["body_import_verification"]["body_in_receipt"] is False
    assert result["drift_summary"]["target_ref_count"] == 8
    assert result["secret_exclusion_scan"]["status"] == "pass"
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    result_keys = _walk_keys(result)
    assert "private_state_scan" not in result_keys
    assert "public_replacement_refs" not in result_keys
    assert "public_replacement_ref" not in result_keys
    assert "body_redacted" not in result_keys
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        keys = _walk_keys(json.loads(text))
        assert "private_runtime_data" not in keys
        assert "provider_payload" not in keys


def test_world_model_projection_drift_source_modules_are_exact_macro_body_imports(
    tmp_path: Path,
) -> None:
    manifest = json.loads((BUNDLE_INPUT / "source_module_manifest.json").read_text())
    by_module = {row["module_id"]: row for row in manifest["modules"]}

    assert manifest["classification"] == "copied_non_secret_macro_body"
    assert manifest["module_count"] == len(SOURCE_MODULE_IDS)
    assert set(by_module) == set(SOURCE_MODULE_IDS)

    for module_id in SOURCE_MODULE_IDS:
        row = by_module[module_id]
        source = MICROCOSM_ROOT.parent / row["source_ref"]
        target = MICROCOSM_ROOT / row["target_ref"].removeprefix(
            "microcosm-substrate/"
        )
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()

        assert target.is_file()
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == target_digest
        assert source_digest == target_digest
        assert row["sha256_match"] is True
        assert row["line_count"] == len(target.read_text(encoding="utf-8").splitlines())
        py_compile.compile(str(target), doraise=True)

    result = run_drift_control_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "world_model_projection_drift_control_room",
        command="pytest",
    )
    assert result["status"] == "pass"
    assert result["source_module_import_status"] == (
        "copied_non_secret_macro_body_landed"
    )
    assert result["source_module_summary"]["module_ids"] == SOURCE_MODULE_IDS
    assert result["source_module_summary"]["verified_module_count"] == len(
        SOURCE_MODULE_IDS
    )
    assert result["source_module_summary"]["material_classes"] == [
        "public_macro_tool_body"
    ]
    source_open = result["source_open_body_imports"]
    assert source_open["status"] == "pass"
    assert source_open["source_import_class"] == "copied_non_secret_macro_body"
    assert (
        source_open["body_material_status"]
        == "copied_non_secret_macro_body_landed"
    )
    assert source_open["body_material_count"] == len(SOURCE_MODULE_IDS)
    assert source_open["body_material_ids"] == SOURCE_MODULE_IDS
    assert source_open["material_classes"] == ["public_macro_tool_body"]
    assert source_open["source_manifest_refs"] == [
        "examples/world_model_projection_drift_control_room/"
        "exported_projection_drift_control_bundle/source_module_manifest.json"
    ]
    assert source_open["aggregate_floor_ref"].endswith(
        "source_module_manifest.json::modules"
    )
    assert source_open["body_text_exported_in_receipts"] is False
    assert source_open["body_text_exported_in_workingness"] is False
    assert result["body_copied_material_count"] == len(SOURCE_MODULE_IDS)
    assert result["source_module_summary"]["body_in_receipt"] is False


def test_world_model_projection_drift_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_drift_control_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_projection_drift_control_bundle"
    assert result["selected_route_id"] == "world_model_projection_drift_control_room"
    assert result["drift_summary"]["row_count"] == 8
    assert result["negative_case_summary"]["expected_negative_case_count"] == 0
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["finding_count"] == 0
    assert result["authority_ceiling"]["provider_payload_exported"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["body_import_status"] == "real_runtime_receipt_landed"
    assert result["body_import_verification"]["status"] == "pass"
    assert result["source_module_import_status"] == (
        "copied_non_secret_macro_body_landed"
    )
    assert result["source_module_summary"]["module_count"] == len(SOURCE_MODULE_IDS)
    assert result["source_open_body_imports"]["body_material_count"] == len(
        SOURCE_MODULE_IDS
    )
    assert (
        result["source_open_body_imports"]["body_text_exported_in_receipts"] is False
    )
    assert (
        result["source_open_body_imports"]["body_text_exported_in_workingness"]
        is False
    )
    assert result["body_copied_material_count"] == len(SOURCE_MODULE_IDS)
    assert result["body_in_receipt"] is False
    assert result["secret_exclusion_scan"]["status"] == "pass"


def test_world_model_projection_drift_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "world_model_projection_drift_control_room"
    )
    args = [
        "run-drift-control-bundle",
        "--input",
        str(BUNDLE_INPUT),
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
    assert first_card["command_speed"]["freshness_input_count"] == 11
    drift = first_card["projection_drift_control"]
    assert drift["row_count"] == 8
    assert drift["source_ref_count"] == 8
    assert drift["target_ref_count"] == 8
    assert drift["repair_route_count"] == 8
    assert drift["validation_ref_count"] == 8
    assert drift["source_authority_claim_count"] == 0
    assert drift["live_repair_authorized_count"] == 0
    assert drift["source_mutation_authorized_count"] == 0
    assert drift["automatic_doctrine_promotion_count"] == 0
    assert first_card["source_modules"]["module_count"] == len(SOURCE_MODULE_IDS)
    assert first_card["source_modules"]["verified_module_count"] == len(
        SOURCE_MODULE_IDS
    )
    assert first_card["source_open_body_imports"]["body_material_count"] == len(
        SOURCE_MODULE_IDS
    )
    assert (
        first_card["source_open_body_imports"]["body_text_exported_in_receipts"]
        is False
    )
    assert first_card["negative_case_coverage"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["secret_exclusion_blocking_hit_count"] == 0
    assert "drift_rows" not in _walk_keys(first_card)
    assert "positive_findings" not in _walk_keys(first_card)
    assert "negative_case_findings" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "authority_ceiling" not in _walk_keys(first_card)
    assert "anti_claim" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        world_model_projection_drift_control_room,
        "_build_result",
        fail_if_rebuilt,
    )

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]


def test_world_model_projection_drift_fixture_manifest_exports_body_floor_summary(
) -> None:
    manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    body_imports = manifest["source_open_body_imports"]

    assert body_imports["status"] == "pass"
    assert body_imports["body_material_status"] == (
        "copied_non_secret_macro_body_landed"
    )
    assert body_imports["body_material_count"] == len(SOURCE_MODULE_IDS)
    assert body_imports["body_material_ids"] == SOURCE_MODULE_IDS
    assert body_imports["material_classes"] == ["public_macro_tool_body"]
    assert body_imports["body_text_exported_in_receipts"] is False
    assert body_imports["body_text_exported_in_workingness"] is False
    assert manifest["body_copied_material_count"] == len(SOURCE_MODULE_IDS)
