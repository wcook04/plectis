from __future__ import annotations

import hashlib
import importlib.util
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
RUNTIME_DRIFT_RECEIPT = (
    MICROCOSM_ROOT / "receipts/runtime_shell/public_projection_drift_control_lens.json"
)
EXTRACTED_PATTERNS_LEDGER = (
    MICROCOSM_ROOT.parent / "state/microcosm_portfolio/extracted_patterns_ledger.jsonl"
)
SOURCE_MODULE_IDS = [
    "world_model_drift_aggregate_source_body_import",
    "world_model_drift_endpoint_source_body_import",
    "view_quality_action_map_source_body_import",
    "view_quality_action_map_test_body_import",
]
VIEW_QUALITY_SOURCE_MODULE = (
    BUNDLE_INPUT
    / "source_modules/tools/meta/observability/view_quality_census.py"
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


def _load_copied_view_quality_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_microcosm_copied_view_quality_census",
        VIEW_QUALITY_SOURCE_MODULE,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy_runtime_drift_receipt(public_root: Path) -> None:
    target = public_root / "receipts/runtime_shell/public_projection_drift_control_lens.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RUNTIME_DRIFT_RECEIPT, target)
    view_quality_target = (
        public_root / "receipts/runtime_shell/public_view_quality_action_map_lens.json"
    )
    shutil.copy2(
        MICROCOSM_ROOT / "receipts/runtime_shell/public_view_quality_action_map_lens.json",
        view_quality_target,
    )
    source_target = (
        public_root.parent
        / "state/microcosm_portfolio/extracted_patterns_ledger.jsonl"
    )
    source_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EXTRACTED_PATTERNS_LEDGER, source_target)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _drift_rows_recompute_digest(
    *,
    selected_pattern_ids: list[str],
    drift_rows: list[dict[str, Any]],
) -> str:
    digest = hashlib.sha256(
        json.dumps(
            {
                "selected_pattern_ids": selected_pattern_ids,
                "runtime_receipt_refs": [
                    "receipts/runtime_shell/public_projection_drift_control_lens.json"
                ],
                "drift_rows": drift_rows,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def _geometry_summary(
    module: Any,
    *,
    dominant_area: float | None,
    rail_area: float | None = None,
    inspector_area: float | None = None,
    node_count: int | None = 4,
    edge_count: int | None = 3,
    label_coverage: float | None = 0.65,
) -> dict[str, Any]:
    regions: dict[str, Any] = {}
    if dominant_area is not None:
        regions["dominant_artifact"] = {"area_ratio": dominant_area}
    if rail_area is not None:
        regions["rails"] = [{"area_ratio": rail_area}]
    if inspector_area is not None:
        regions["inspector"] = {"area_ratio": inspector_area}

    graph_metrics: dict[str, Any] = {}
    if node_count is not None:
        graph_metrics["node_rect_count"] = node_count
    if edge_count is not None:
        graph_metrics["edge_path_count"] = edge_count
    if label_coverage is not None:
        graph_metrics["visible_label_coverage"] = label_coverage

    return {
        "schema": module.VIEW_GEOMETRY_CAPTURE_SUMMARY_SCHEMA_V1,
        "evidence_kind": "live_dom_capture",
        "regions": regions,
        "graph_metrics": graph_metrics,
    }


def _geometry_review(module: Any, summary: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    vector = module._geometry_vector_from_summary(summary, mode="graph_first")
    assert vector is not None
    review = module._geometry_calibration_review(
        row={
            "view_id": "graph",
            "view_family": "graph_surface",
            "mode": "graph_first",
        },
        geometry_vector=vector,
        screenshot_ledger={"status": "fresh"},
    )
    assert review is not None
    return vector, review


def _write_view_quality_geometry_probe(
    bundle: Path,
    *,
    dominant_area: float = 0.55,
    rail_area: float = 0.08,
    inspector_area: float = 0.06,
    node_count: int = 6,
    edge_count: int = 5,
    label_coverage: float = 0.74,
) -> Path:
    path = bundle / "view_quality_geometry_probe.json"
    _write_json(
        path,
        {
            "schema_version": "world_model_projection_drift_view_quality_geometry_probe_v1",
            "view_id": "graph_geometry",
            "view_family": "graph_surface",
            "mode": "graph_first",
            "source_module_ref": "source_modules/tools/meta/observability/view_quality_census.py",
            "projection_role": "public_safe_geometry_probe_for_copied_view_quality_grader",
            "body_in_receipt": False,
            "screenshot_ledger": {
                "status": "fresh",
            },
            "geometry_summary": {
                "schema": "view_geometry_capture_summary_v1",
                "evidence_kind": "live_dom_capture",
                "regions": {
                    "dominant_artifact": {
                        "area_ratio": dominant_area,
                    },
                    "rails": [
                        {
                            "area_ratio": rail_area,
                        }
                    ],
                    "inspector": {
                        "area_ratio": inspector_area,
                    },
                },
                "graph_metrics": {
                    "node_rect_count": node_count,
                    "edge_path_count": edge_count,
                    "visible_label_coverage": label_coverage,
                },
            },
        },
    )
    return path


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
    assert result["drift_summary"]["fact_authority_row_count"] == 8
    assert result["drift_summary"]["guarded_projection_treatment_count"] == 8
    assert result["drift_summary"]["unguarded_duplicate_count"] == 0
    assert result["runtime_receipt_witness"]["status"] == "pass"
    assert result["runtime_receipt_witness"]["witnessed_drift_row_count"] == 8
    assert result["source_state_diff"]["status"] == "pass"
    assert result["source_state_diff"]["source_row_count"] == 2
    assert {
        row["source_check"]
        for row in result["source_state_diff"]["evidence_rows"]
    } == {
        "extracted_pattern_ledger_row_diff",
        "view_quality_action_map_summary_diff",
    }
    assert result["negative_case_summary"]["expected_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["observed_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["authority_ceiling"]["source_authority_claim"] is False
    assert result["drift_control_board"]["fact_authority_mesh"]["status"] == "pass"
    assert result["drift_control_board"]["fact_authority_mesh"][
        "authority_ref_policy"
    ] == "authority_ref_equals_source_ref"
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
    _copy_runtime_drift_receipt(public_root)
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
    assert result["runtime_receipt_witness_status"] == "pass"
    assert result["runtime_receipt_witness"]["runtime_receipt_row_count"] == 8
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


def test_world_model_projection_drift_rejects_unwitnessed_runtime_receipt_row(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/world_model_projection_drift_control_room",
        public_root / "fixtures/first_wave/world_model_projection_drift_control_room",
    )
    drift_rows_path = (
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input/drift_rows.json"
    )
    drift_rows = json.loads(drift_rows_path.read_text(encoding="utf-8"))
    drift_rows["drift_rows"][0][
        "drift_row_id"
    ] = "unwitnessed_public_runtime_receipt_row"
    drift_rows_path.write_text(
        json.dumps(drift_rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input",
        public_root / "receipts/first_wave/world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["runtime_receipt_witness"]["status"] == "pass"
    assert result["projection_recompute"]["status"] == "pass"
    assert result["supplied_drift_rows_snapshot"]["status"] == "blocked"
    assert result["supplied_drift_rows_snapshot"]["extra_drift_row_ids"] == [
        "unwitnessed_public_runtime_receipt_row"
    ]
    assert "DRIFT_SUPPLIED_ROW_SNAPSHOT_MISMATCH" in {
        finding["error_code"] for finding in result["positive_findings"]
    }


def test_world_model_projection_drift_rejects_stale_supplied_drift_rows_snapshot(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/world_model_projection_drift_control_room",
        public_root / "fixtures/first_wave/world_model_projection_drift_control_room",
    )
    drift_rows_path = (
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input/drift_rows.json"
    )
    stale_snapshot = json.loads(drift_rows_path.read_text(encoding="utf-8"))
    stale_snapshot["drift_rows"][0]["source_ref"] = "synthetic_stale_source_ref"
    drift_rows_path.write_text(
        json.dumps(stale_snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input",
        public_root / "receipts/first_wave/world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["projection_recompute"]["status"] == "pass"
    assert result["drift_rows"][0]["source_ref"] != "synthetic_stale_source_ref"
    snapshot = result["supplied_drift_rows_snapshot"]
    assert snapshot["status"] == "blocked"
    assert snapshot["role"] == "expected_snapshot_not_source_authority"
    assert snapshot["changed_drift_row_ids"] == [
        "world_model_cross_plane_drift_aggregate"
    ]
    assert "DRIFT_SUPPLIED_ROW_SNAPSHOT_MISMATCH" in {
        finding["error_code"] for finding in result["positive_findings"]
    }


def test_world_model_projection_drift_receipt_mutation_moves_recomputed_rows(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/world_model_projection_drift_control_room",
        public_root / "fixtures/first_wave/world_model_projection_drift_control_room",
    )
    receipt_path = public_root / "receipts/runtime_shell/public_projection_drift_control_lens.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["drift_rows"][0]["source_ref"] = "mutated_public_runtime_source_ref"
    _write_json(receipt_path, receipt)

    result = run(
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input",
        public_root / "receipts/first_wave/world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["projection_recompute"]["status"] == "pass"
    assert result["drift_rows"][0]["source_ref"] == "mutated_public_runtime_source_ref"
    assert result["source_ref_evidence"]["status"] == "blocked"
    assert result["supplied_drift_rows_snapshot"]["changed_drift_row_ids"] == [
        "world_model_cross_plane_drift_aggregate"
    ]
    assert "DRIFT_SOURCE_REF_UNSUPPORTED" in {
        finding["error_code"] for finding in result["positive_findings"]
    }


def test_world_model_projection_drift_source_ledger_mutation_moves_verdict_and_count(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/world_model_projection_drift_control_room",
        public_root / "fixtures/first_wave/world_model_projection_drift_control_room",
    )
    ledger_path = (
        public_root.parent
        / "state/microcosm_portfolio/extracted_patterns_ledger.jsonl"
    )
    ledger_rows = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in ledger_rows:
        if row.get("pattern_id") == "world_model_cross_plane_drift_aggregate":
            row["pattern_id"] = "mutated_world_model_cross_plane_drift_aggregate"
            break
    ledger_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in ledger_rows) + "\n",
        encoding="utf-8",
    )

    result = run(
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input",
        public_root / "receipts/first_wave/world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["projection_recompute"]["status"] == "pass"
    source_state = result["source_state_diff"]
    assert source_state["status"] == "blocked"
    assert source_state["source_row_count"] == 1
    assert "DRIFT_SOURCE_ROW_MISSING" in {
        finding["error_code"] for finding in result["positive_findings"]
    }


def test_world_model_projection_drift_source_ledger_without_source_refs_blocks(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/world_model_projection_drift_control_room",
        public_root / "fixtures/first_wave/world_model_projection_drift_control_room",
    )
    ledger_path = (
        public_root.parent
        / "state/microcosm_portfolio/extracted_patterns_ledger.jsonl"
    )
    ledger_rows = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in ledger_rows:
        if row.get("pattern_id") == "world_model_cross_plane_drift_aggregate":
            row["source_refs"] = []
            break
    ledger_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in ledger_rows) + "\n",
        encoding="utf-8",
    )

    result = run(
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input",
        public_root / "receipts/first_wave/world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    source_state = result["source_state_diff"]
    assert source_state["status"] == "blocked"
    ledger_evidence = [
        row
        for row in source_state["evidence_rows"]
        if row["source_check"] == "extracted_pattern_ledger_row_diff"
    ]
    assert ledger_evidence[0]["source_ref_count"] == 0
    assert "DRIFT_SOURCE_ROW_REFS_REQUIRED" in {
        finding["error_code"] for finding in result["positive_findings"]
    }


def test_world_model_projection_drift_view_quality_source_mutation_moves_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/world_model_projection_drift_control_room",
        public_root / "fixtures/first_wave/world_model_projection_drift_control_room",
    )
    action_map_path = (
        public_root / "receipts/runtime_shell/public_view_quality_action_map_lens.json"
    )
    action_map = json.loads(action_map_path.read_text(encoding="utf-8"))
    action_map["action_summary"]["hot_action_count"] += 1
    _write_json(action_map_path, action_map)

    result = run(
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input",
        public_root / "receipts/first_wave/world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    source_state = result["source_state_diff"]
    assert source_state["status"] == "blocked"
    assert source_state["source_row_count"] == 2
    assert "DRIFT_VIEW_QUALITY_ACTION_SUMMARY_MISMATCH" in {
        finding["error_code"] for finding in result["positive_findings"]
    }


def test_world_model_projection_drift_rejects_internally_consistent_fake_source_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/world_model_projection_drift_control_room",
        public_root / "fixtures/first_wave/world_model_projection_drift_control_room",
    )
    receipt_path = public_root / "receipts/runtime_shell/public_projection_drift_control_lens.json"
    rows_path = (
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input/drift_rows.json"
    )
    fake_source_ref = "fake/source/ref.json::world_model_cross_plane_drift_aggregate"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["drift_rows"][0]["source_ref"] = fake_source_ref
    _write_json(receipt_path, receipt)

    rows_payload = json.loads(rows_path.read_text(encoding="utf-8"))
    protocol = json.loads(
        (
            public_root
            / "fixtures/first_wave/world_model_projection_drift_control_room/input/projection_protocol.json"
        ).read_text(encoding="utf-8")
    )
    rows_payload["drift_rows"][0]["source_ref"] = fake_source_ref
    rows_payload["drift_rows"][0]["fact_authority"]["authority_ref"] = fake_source_ref
    rows_payload["recompute_digest"] = _drift_rows_recompute_digest(
        selected_pattern_ids=protocol["selected_pattern_ids"],
        drift_rows=rows_payload["drift_rows"],
    )
    _write_json(rows_path, rows_payload)

    result = run(
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input",
        public_root / "receipts/first_wave/world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["projection_recompute"]["status"] == "pass"
    assert result["supplied_drift_rows_snapshot"]["status"] == "pass"
    assert result["source_ref_evidence"]["status"] == "blocked"
    assert result["source_ref_evidence"]["unsupported_source_ref_count"] == 1
    assert "DRIFT_SOURCE_REF_UNSUPPORTED" in {
        finding["error_code"] for finding in result["positive_findings"]
    }


def test_world_model_projection_drift_selected_row_order_moves_snapshot_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/world_model_projection_drift_control_room",
        public_root / "fixtures/first_wave/world_model_projection_drift_control_room",
    )
    protocol_path = (
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input/projection_protocol.json"
    )
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["selected_pattern_ids"][:2] = list(reversed(protocol["selected_pattern_ids"][:2]))
    _write_json(protocol_path, protocol)

    result = run(
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input",
        public_root / "receipts/first_wave/world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["projection_recompute"]["status"] == "pass"
    assert result["projection_recompute"]["selected_pattern_ids"][:2] == [
        "view_quality_all_view_action_map",
        "world_model_cross_plane_drift_aggregate",
    ]
    assert result["selected_pattern_ids"][:2] == [
        "view_quality_all_view_action_map",
        "world_model_cross_plane_drift_aggregate",
    ]
    snapshot = result["supplied_drift_rows_snapshot"]
    assert snapshot["status"] == "blocked"
    assert snapshot["missing_drift_row_ids"] == []
    assert snapshot["extra_drift_row_ids"] == []
    assert snapshot["changed_drift_row_ids"] == []
    assert snapshot["metadata_mismatch_fields"] == ["recompute_digest"]
    assert "DRIFT_SUPPLIED_ROW_SNAPSHOT_MISMATCH" in {
        finding["error_code"] for finding in result["positive_findings"]
    }


def test_world_model_projection_drift_runtime_policy_flag_moves_verdict_and_finding(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/world_model_projection_drift_control_room",
        public_root / "fixtures/first_wave/world_model_projection_drift_control_room",
    )
    receipt_path = public_root / "receipts/runtime_shell/public_projection_drift_control_lens.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["drift_rows"][0]["live_repair_authorized"] = True
    _write_json(receipt_path, receipt)

    result = run(
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input",
        public_root / "receipts/first_wave/world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["projection_recompute"]["status"] == "pass"
    assert result["runtime_receipt_witness"]["status"] == "pass"
    assert result["drift_rows"][0]["live_repair_authorized"] is True
    assert result["drift_summary"]["live_repair_authorized_count"] == 1
    assert "DRIFT_LIVE_REPAIR_FORBIDDEN" in {
        finding["error_code"] for finding in result["positive_findings"]
    }


def test_world_model_projection_drift_rejects_selected_row_missing_from_receipt(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/world_model_projection_drift_control_room",
        public_root / "fixtures/first_wave/world_model_projection_drift_control_room",
    )
    protocol_path = (
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input/projection_protocol.json"
    )
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["selected_pattern_ids"].append("missing_runtime_receipt_row")
    protocol_path.write_text(
        json.dumps(protocol, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        public_root
        / "fixtures/first_wave/world_model_projection_drift_control_room/input",
        public_root / "receipts/first_wave/world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["projection_recompute"]["status"] == "blocked"
    assert result["projection_recompute"]["missing_selected_pattern_ids"] == [
        "missing_runtime_receipt_row"
    ]
    assert "DRIFT_SOURCE_PROJECTION_ROW_MISSING" in {
        finding["error_code"] for finding in result["positive_findings"]
    }


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


def test_world_model_projection_drift_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "examples/world_model_projection_drift_control_room",
        public_root / "examples/world_model_projection_drift_control_room",
    )
    bundle = (
        public_root
        / "examples/world_model_projection_drift_control_room/"
        "exported_projection_drift_control_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    corrupted_module = manifest["modules"][0]
    corrupted_module_id = corrupted_module["module_id"]
    corrupted_module["source_sha256"] = "0" * 64
    corrupted_module["target_sha256"] = "0" * 64
    _write_json(manifest_path, manifest)

    result = run_drift_control_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_import_status"] == "blocked"
    summary = result["source_module_summary"]
    assert summary["status"] == "blocked"
    assert summary["module_ids"] == SOURCE_MODULE_IDS
    assert summary["verified_module_count"] == len(SOURCE_MODULE_IDS) - 1
    assert summary["body_in_receipt"] is False
    assert summary["findings"] == [
        {
            "error_code": "DRIFT_SOURCE_MODULE_DIGEST_MISMATCH",
            "message": (
                "source module digest declarations must match the copied target body"
            ),
            "negative_case_id": "source_module_manifest",
            "subject_id": corrupted_module_id,
            "subject_kind": "source_module",
            "body_in_receipt": False,
        }
    ]
    assert result["source_open_body_imports"]["status"] == "blocked"
    assert result["source_open_body_imports"]["body_material_count"] == 0
    assert result["secret_exclusion_scan"]["status"] == "pass"


def test_world_model_projection_drift_rejects_source_module_anchor_missing_after_digest_refresh(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "examples/world_model_projection_drift_control_room",
        public_root / "examples/world_model_projection_drift_control_room",
    )
    bundle = (
        public_root
        / "examples/world_model_projection_drift_control_room/"
        "exported_projection_drift_control_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = manifest["modules"][0]
    target = public_root / row["target_ref"].removeprefix("microcosm-substrate/")
    text = target.read_text(encoding="utf-8")
    target.write_text(
        text.replace("def load_world_model_snapshot(", "def load_world_model_snapshot_removed(", 1),
        encoding="utf-8",
    )
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    row["source_sha256"] = digest
    row["target_sha256"] = digest
    _write_json(manifest_path, manifest)

    result = run_drift_control_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "world_model_projection_drift_control_room",
        command="pytest",
    )

    summary = result["source_module_summary"]
    assert result["status"] == "blocked"
    assert summary["status"] == "blocked"
    assert summary["findings"] == [
        {
            "error_code": "DRIFT_SOURCE_MODULE_ANCHOR_MISSING",
            "message": "source module must carry the declared macro mechanism anchors",
            "negative_case_id": "source_module_manifest",
            "subject_id": row["module_id"],
            "subject_kind": "source_module",
            "body_in_receipt": False,
            "missing_anchors": ["def load_world_model_snapshot("],
        }
    ]
    assert result["secret_exclusion_scan"]["status"] == "pass"


def test_world_model_projection_drift_rejects_source_module_fake_source_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "examples/world_model_projection_drift_control_room",
        public_root / "examples/world_model_projection_drift_control_room",
    )
    bundle = (
        public_root
        / "examples/world_model_projection_drift_control_room/"
        "exported_projection_drift_control_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = manifest["modules"][0]
    row["source_ref"] = "fake/source_module.py"
    _write_json(manifest_path, manifest)

    result = run_drift_control_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "world_model_projection_drift_control_room",
        command="pytest",
    )

    summary = result["source_module_summary"]
    assert result["status"] == "blocked"
    assert summary["status"] == "blocked"
    assert summary["findings"] == [
        {
            "error_code": "DRIFT_SOURCE_MODULE_SOURCE_REF_UNSUPPORTED",
            "message": "source module source_ref must name a supported copied macro source body",
            "negative_case_id": "source_module_manifest",
            "subject_id": row["module_id"],
            "subject_kind": "source_module",
            "body_in_receipt": False,
        }
    ]
    assert result["secret_exclusion_scan"]["status"] == "pass"


def test_world_model_projection_drift_view_quality_geometry_grader_computes_synthetic_verdicts(
) -> None:
    module = _load_copied_view_quality_module()

    passing_vector, passing_review = _geometry_review(
        module,
        _geometry_summary(
            module,
            dominant_area=0.55,
            rail_area=0.08,
            inspector_area=0.06,
            node_count=6,
            edge_count=5,
            label_coverage=0.74,
        ),
    )
    assert passing_review["status"] == "calibrated_pass"
    assert passing_review["failed_gates"] == []
    assert passing_review["watch_gates"] == []
    assert passing_vector["hard_gates"]["node_geometry_available"] == "pass"
    assert passing_review["selection_reason"].startswith(
        "Rendered geometry was interpreted through a calibration profile"
    )

    low_graph_vector, low_graph_review = _geometry_review(
        module,
        _geometry_summary(
            module,
            dominant_area=0.21,
            rail_area=0.04,
            inspector_area=0.03,
            node_count=4,
            edge_count=2,
            label_coverage=0.7,
        ),
    )
    assert low_graph_review["status"] == "calibrated_watch"
    assert low_graph_review["hard_gates"]["dominant_artifact_visible"] == "watch"
    assert low_graph_vector["graph_region_area_ratio"] == 0.21

    rail_dominates_vector, rail_dominates_review = _geometry_review(
        module,
        _geometry_summary(
            module,
            dominant_area=0.4,
            rail_area=0.48,
            inspector_area=0.08,
            node_count=5,
            edge_count=4,
            label_coverage=0.8,
        ),
    )
    assert rail_dominates_review["status"] == "calibrated_watch"
    assert rail_dominates_review["hard_gates"][
        "graph_region_not_subordinate_to_competing_regions"
    ] == "fail"
    assert "competing_regions_rival_dominant_artifact" in rail_dominates_review[
        "violations"
    ]
    assert rail_dominates_vector["rail_or_inspector_area_ratio"] == 0.56

    missing_node_vector, missing_node_review = _geometry_review(
        module,
        _geometry_summary(
            module,
            dominant_area=0.44,
            rail_area=0.08,
            inspector_area=0.06,
            node_count=None,
            edge_count=2,
            label_coverage=0.75,
        ),
    )
    assert missing_node_review["status"] == "calibrated_watch"
    assert missing_node_review["hard_gates"]["node_geometry_plausible"] == "fail"
    assert "node_geometry_plausible" in missing_node_review["failed_gates"]
    assert missing_node_vector["hard_gates"]["node_geometry_available"] == "fail"

    missing_contract_vector, missing_contract_review = _geometry_review(
        module,
        _geometry_summary(
            module,
            dominant_area=None,
            rail_area=0.12,
            inspector_area=0.1,
            node_count=3,
            edge_count=2,
            label_coverage=0.7,
        ),
    )
    assert missing_contract_review["status"] == "calibrated_watch"
    assert missing_contract_review["hard_gates"]["dominant_artifact_visible"] == "fail"
    assert missing_contract_review["evidence"]["graph_region_area_ratio"] is None
    assert missing_contract_vector["graph_region_area_ratio"] is None


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
    assert result["drift_summary"]["fact_authority_row_count"] == 8
    assert result["drift_summary"]["unguarded_duplicate_count"] == 0
    assert result["source_ref_evidence"]["status"] == "pass"
    assert result["source_ref_evidence"]["validated_source_ref_count"] == 8
    assert result["source_state_diff"]["status"] == "pass"
    assert result["source_state_diff"]["source_row_count"] == 2
    assert result["negative_case_summary"]["expected_negative_case_count"] == 0
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["finding_count"] == 0
    exported_rows = json.loads((BUNDLE_INPUT / "drift_rows.json").read_text(encoding="utf-8"))
    assert result["projection_recompute"]["status"] == "pass"
    assert exported_rows["generation_basis"] == result["projection_recompute"]["basis"]
    assert exported_rows["drift_rows"] == result["projection_recompute"]["drift_rows"]
    assert exported_rows["drift_rows_count"] == result["projection_recompute"][
        "derived_row_count"
    ]
    assert exported_rows["recompute_digest"] == result["projection_recompute"][
        "recompute_digest"
    ]
    assert result["supplied_drift_rows_snapshot"]["status"] == "pass"
    assert result["supplied_drift_rows_snapshot"]["role"] == (
        "expected_snapshot_not_source_authority"
    )
    assert result["supplied_drift_rows_snapshot"]["changed_drift_row_ids"] == []
    assert result["supplied_drift_rows_snapshot"]["metadata_mismatch_fields"] == []
    assert result["runtime_receipt_witness"]["status"] == "pass"
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
    assert result["view_quality_geometry_grade"]["status"] == "not_present"
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


def test_world_model_projection_drift_view_quality_probe_runs_copied_grader(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "examples/world_model_projection_drift_control_room",
        public_root / "examples/world_model_projection_drift_control_room",
    )
    bundle = (
        public_root
        / "examples/world_model_projection_drift_control_room/"
        "exported_projection_drift_control_bundle"
    )
    _write_view_quality_geometry_probe(bundle)

    result = run_drift_control_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "pass"
    geometry = result["view_quality_geometry_grade"]
    assert geometry["status"] == "pass"
    assert geometry["basis"] == (
        "view_quality_geometry_probe.json + copied view_quality_census.py geometry grader"
    )
    assert geometry["source_module_ref"].endswith(
        "source_modules/tools/meta/observability/view_quality_census.py"
    )
    assert geometry["calibration_status"] == "calibrated_pass"
    assert geometry["failed_gates"] == []
    assert geometry["watch_gates"] == []
    assert geometry["body_in_receipt"] is False


def test_world_model_projection_drift_view_quality_probe_perturbation_moves_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "examples/world_model_projection_drift_control_room",
        public_root / "examples/world_model_projection_drift_control_room",
    )
    bundle = (
        public_root
        / "examples/world_model_projection_drift_control_room/"
        "exported_projection_drift_control_bundle"
    )
    _write_view_quality_geometry_probe(
        bundle,
        dominant_area=0.18,
        rail_area=0.42,
    )

    result = run_drift_control_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    geometry = result["view_quality_geometry_grade"]
    assert geometry["status"] == "blocked"
    assert geometry["calibration_status"] == "calibrated_watch"
    assert geometry["hard_gates"]["dominant_artifact_visible"] == "fail"
    assert geometry["hard_gates"][
        "graph_region_not_subordinate_to_competing_regions"
    ] == "fail"
    assert geometry["failed_gates"] == [
        "dominant_artifact_visible",
        "graph_region_not_subordinate_to_competing_regions",
    ]
    assert "DRIFT_VIEW_QUALITY_GEOMETRY_CALIBRATION_NOT_PASSING" in {
        finding["error_code"] for finding in result["positive_findings"]
    }


def test_world_model_projection_drift_rejects_stale_exported_bundle_snapshot(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "examples/world_model_projection_drift_control_room",
        public_root / "examples/world_model_projection_drift_control_room",
    )
    bundle = (
        public_root
        / "examples/world_model_projection_drift_control_room/"
        "exported_projection_drift_control_bundle"
    )
    rows_path = bundle / "drift_rows.json"
    payload = json.loads(rows_path.read_text(encoding="utf-8"))
    payload["drift_rows"][0]["source_ref"] = "mutated_exported_bundle_source_ref"
    _write_json(rows_path, payload)

    result = run_drift_control_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["projection_recompute"]["status"] == "pass"
    assert result["drift_rows"][0]["source_ref"] != "mutated_exported_bundle_source_ref"
    assert result["supplied_drift_rows_snapshot"]["status"] == "blocked"
    assert result["supplied_drift_rows_snapshot"]["changed_drift_row_ids"] == [
        "world_model_cross_plane_drift_aggregate"
    ]
    assert "DRIFT_SUPPLIED_ROW_SNAPSHOT_MISMATCH" in {
        finding["error_code"] for finding in result["positive_findings"]
    }


def test_world_model_projection_drift_rejects_exported_bundle_metadata_drift(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    _copy_runtime_drift_receipt(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "examples/world_model_projection_drift_control_room",
        public_root / "examples/world_model_projection_drift_control_room",
    )
    bundle = (
        public_root
        / "examples/world_model_projection_drift_control_room/"
        "exported_projection_drift_control_bundle"
    )
    rows_path = bundle / "drift_rows.json"
    payload = json.loads(rows_path.read_text(encoding="utf-8"))
    payload["recompute_digest"] = "sha256:" + ("0" * 64)
    _write_json(rows_path, payload)

    result = run_drift_control_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "world_model_projection_drift_control_room",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["projection_recompute"]["status"] == "pass"
    snapshot = result["supplied_drift_rows_snapshot"]
    assert snapshot["status"] == "blocked"
    assert snapshot["changed_drift_row_ids"] == []
    assert snapshot["metadata_mismatch_fields"] == ["recompute_digest"]
    assert "DRIFT_SUPPLIED_ROW_METADATA_MISMATCH" in {
        finding["error_code"] for finding in result["positive_findings"]
    }


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
    assert first_card["command_speed"]["freshness_input_count"] >= 13
    drift = first_card["projection_drift_control"]
    assert drift["row_count"] == 8
    assert drift["source_ref_count"] == 8
    assert drift["target_ref_count"] == 8
    assert drift["repair_route_count"] == 8
    assert drift["validation_ref_count"] == 8
    assert drift["fact_authority_row_count"] == 8
    assert drift["guarded_projection_treatment_count"] == 8
    assert drift["unguarded_duplicate_count"] == 0
    assert drift["source_authority_claim_count"] == 0
    assert drift["live_repair_authorized_count"] == 0
    assert drift["source_mutation_authorized_count"] == 0
    assert drift["automatic_doctrine_promotion_count"] == 0
    assert drift["runtime_receipt_witnessed_row_count"] == 8
    assert drift["runtime_receipt_missing_row_count"] == 0
    assert first_card["runtime_receipt_witness"]["status"] == "pass"
    assert first_card["source_modules"]["module_count"] == len(SOURCE_MODULE_IDS)
    assert first_card["source_modules"]["verified_module_count"] == len(
        SOURCE_MODULE_IDS
    )
    assert first_card["source_open_body_imports"]["body_material_count"] == len(
        SOURCE_MODULE_IDS
    )
    assert first_card["view_quality_geometry_grade"]["status"] == "not_present"
    assert first_card["view_quality_geometry_grade"]["calibration_status"] is None
    assert first_card["view_quality_geometry_grade"]["failed_gate_count"] == 0
    assert first_card["view_quality_geometry_grade"]["watch_gate_count"] == 0
    assert (
        first_card["source_open_body_imports"]["body_text_exported_in_receipts"]
        is False
    )
    assert first_card["negative_case_coverage"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["fact_authority_mesh_guarded"] is True
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

    assert manifest["validator_contract_ratchet_v1"][
        "required_negative_case_count"
    ] == len(EXPECTED_NEGATIVE_CASES)
    assert "drift_row_without_fact_authority" in manifest["expected_negative_cases"]
    assert "DRIFT_FACT_AUTHORITY_REQUIRED" in manifest["stable_error_codes"]
    assert "fact_authority_mesh" in manifest["validator_contract_ratchet_v1"][
        "per_output_receipt_field_floor"
    ][
        "receipts/first_wave/world_model_projection_drift_control_room/world_model_projection_drift_control_room_result.json"
    ]
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
