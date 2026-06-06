from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.batch8_station_surface_atlas_layout_port import (
    AUTHORITY_CEILING,
    EXPECTED_CASES,
    EXPECTED_NEGATIVE_CASES,
    layout_nodes,
    main,
    result_card,
    run,
    run_batch8_station_surface_atlas_layout_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
ORGAN_ID = "batch8_station_surface_atlas_layout_port"
FIXTURE_INPUT = MICROCOSM_ROOT / f"fixtures/first_wave/{ORGAN_ID}/input"
EXPORTED_BUNDLE = MICROCOSM_ROOT / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle"
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"
PROBE_MANIFEST_NAME = f"{ORGAN_ID}_probe_manifest.json"
PERTURBATION_CASE_FIXTURE = (
    MICROCOSM_ROOT
    / f"tests/fixtures/{ORGAN_ID}/banded_slack_operate_perturbation_case.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _copy_public_fixture(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / f"examples/{ORGAN_ID}",
        public_root / f"examples/{ORGAN_ID}",
    )
    shutil.copytree(
        MICROCOSM_ROOT / f"fixtures/first_wave/{ORGAN_ID}",
        public_root / f"fixtures/first_wave/{ORGAN_ID}",
    )
    return public_root / f"fixtures/first_wave/{ORGAN_ID}/input"


def _copy_detached_public_bundle(tmp_path: Path) -> Path:
    public_root = tmp_path / "detached" / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / f"examples/{ORGAN_ID}",
        public_root / f"examples/{ORGAN_ID}",
    )
    return public_root / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle"


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _views_from_group_counts(group_counts: dict[str, Any]) -> list[dict[str, Any]]:
    views: list[dict[str, Any]] = []
    for group in (
        "operate",
        "missions",
        "data",
        "inspect",
        "map",
        "library",
        "unassigned",
    ):
        for index in range(int(group_counts.get(group) or 0)):
            views.append(
                {
                    "id": f"{group}_{index:02d}",
                    "label": f"{group.title()} {index:02d}",
                    "shellGroup": group,
                    "captureLatestStatus": "captured",
                    "captureSlug": f"{group}-{index:02d}",
                    "captureSampleCount": 1,
                    "fanout": 1,
                    "fanin": 1,
                }
            )
    return views


def _rewrite_bundle_source_module(
    bundle: Path,
    *,
    source_to_target_relation: str = "exact_copy",
) -> None:
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = manifest["modules"][0]
    target = bundle / row["path"]
    changed_body = "/* detached public bundle perturbation */\n" + target.read_text(
        encoding="utf-8"
    )
    target.write_text(changed_body, encoding="utf-8")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    row["sha256"] = digest
    row["source_sha256"] = digest
    row["target_sha256"] = digest
    row["byte_count"] = target.stat().st_size
    row["line_count"] = len(changed_body.splitlines())
    row["sha256_match"] = True
    row["source_to_target_relation"] = source_to_target_relation
    manifest["modules"][0] = row
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_layout_nodes_banded_slack_reference_geometry() -> None:
    views = []
    for group, count in {
        "operate": 7,
        "missions": 2,
        "data": 5,
        "inspect": 6,
        "map": 15,
        "library": 3,
        "unassigned": 1,
    }.items():
        for index in range(count):
            views.append(
                {
                    "id": f"{group}_{index:02d}",
                    "label": f"{group.title()} {index:02d}",
                    "shellGroup": group,
                    "captureLatestStatus": "captured",
                    "captureSlug": f"{group}-{index:02d}",
                    "captureSampleCount": 1,
                    "fanout": 1,
                    "fanin": 1,
                }
            )

    layout = layout_nodes(views)
    assert [row["group"] for row in layout["columns"]] == [
        "operate",
        "missions",
        "data",
        "inspect",
        "map",
        "library",
        "unassigned",
    ]
    assert next(row for row in layout["columns"] if row["group"] == "map")["laneCount"] == 5
    assert next(row for row in layout["columns"] if row["group"] == "library")["x"] == 1552
    assert layout["positions"]["map_04"] == {"x": 1232, "y": 804}
    assert layout["positions"]["map_05"] == {"x": 0, "y": 936}
    assert layout["layoutReceiptSummary"]["columnGeometry"]["packedBlankSpaceRatio"] == 0.304


def test_layout_nodes_sorting_and_unassigned_fallback() -> None:
    layout = layout_nodes(
        [
            {
                "id": "high_centrality_captured",
                "label": "AAA High",
                "shellGroup": "operate",
                "captureLatestStatus": "captured",
                "captureSlug": "high",
                "captureSampleCount": 1,
                "fanout": 100,
                "fanin": 100,
            },
            {
                "id": "failed_low_centrality",
                "label": "ZZZ Failed",
                "shellGroup": "operate",
                "captureLatestStatus": "failed",
                "captureSlug": "failed",
                "captureSampleCount": 1,
                "fanout": 0,
                "fanin": 0,
            },
            {
                "id": "future_surface",
                "label": "Future",
                "shellGroup": "future_group",
                "captureLatestStatus": None,
                "captureSlug": None,
                "captureSampleCount": 0,
                "fanout": 0,
                "fanin": 0,
            },
        ]
    )

    assert layout["positions"]["failed_low_centrality"]["y"] < layout["positions"]["high_centrality_captured"]["y"]
    assert layout["columns"][-1]["group"] == "unassigned"


def test_batch8_station_layout_port_runs_public_parity_fixtures(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / f"receipts/first_wave/{ORGAN_ID}",
        acceptance_out=tmp_path
        / f"receipts/acceptance/first_wave/{ORGAN_ID}_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_module_manifest"]["module_count"] == 1
    assert result["source_module_manifest"]["all_required_anchors_present"] is True
    assert result["semantic_negative_case_evaluator_used"] is True

    exercise = result["exercise"]
    assert exercise["reference_case_count"] == len(EXPECTED_CASES)
    assert exercise["passed_reference_case_count"] == len(EXPECTED_CASES)
    assert exercise["negative_exercises"]["unknown_group_column"] == "unassigned"
    assert exercise["negative_exercises"]["slack_map_lane_count"] == 5
    assert result["body_in_receipt"] is False


def test_batch8_station_layout_input_perturbation_rejects_stale_expected_positions(
    tmp_path: Path,
) -> None:
    input_dir = _copy_public_fixture(tmp_path)
    manifest_path = input_dir / PROBE_MANIFEST_NAME
    probe = json.loads(manifest_path.read_text(encoding="utf-8"))
    perturbation_case = json.loads(
        PERTURBATION_CASE_FIXTURE.read_text(encoding="utf-8")
    )
    base_case = next(
        row for row in probe["cases"] if row["case_id"] == "banded_slack_reference"
    )

    stale_probe = copy.deepcopy(probe)
    stale_case = copy.deepcopy(perturbation_case)
    stale_case["expected_columns"] = copy.deepcopy(base_case["expected_columns"])
    stale_case["expected_positions"] = copy.deepcopy(base_case["expected_positions"])
    stale_probe["cases"].append(stale_case)
    _write_json(manifest_path, stale_probe)

    stale_result = run(
        input_dir,
        tmp_path / f"receipts/stale_expected/{ORGAN_ID}",
        command="pytest",
    )

    assert stale_result["status"] == "blocked"
    assert "BATCH8_STATION_LAYOUT_COLUMN_MISMATCH" in stale_result["error_codes"]
    assert "BATCH8_STATION_LAYOUT_POSITION_MISMATCH" in stale_result["error_codes"]
    stale_case_result = next(
        row
        for row in stale_result["exercise"]["reference_cases"]
        if row["case_id"] == "banded_slack_operate_perturbation_reference"
    )
    assert stale_case_result["status"] == "blocked"

    layout = layout_nodes(_views_from_group_counts(perturbation_case["group_counts"]))
    repaired_probe = copy.deepcopy(probe)
    repaired_case = copy.deepcopy(perturbation_case)
    repaired_case["expected_columns"] = layout["columns"]
    repaired_case["expected_positions"] = {
        key: layout["positions"][key]
        for key in perturbation_case["expected_positions"]
    }
    repaired_case["expected_receipt_summary"] = {
        "layoutMode": layout["layoutReceiptSummary"]["layoutMode"]
    }
    repaired_probe["cases"].append(repaired_case)
    _write_json(manifest_path, repaired_probe)

    repaired_result = run(
        input_dir,
        tmp_path / f"receipts/repaired_expected/{ORGAN_ID}",
        command="pytest",
    )

    assert repaired_result["status"] == "pass"
    repaired_case_result = next(
        row
        for row in repaired_result["exercise"]["reference_cases"]
        if row["case_id"] == "banded_slack_operate_perturbation_reference"
    )
    assert repaired_case_result["status"] == "pass"
    assert repaired_case_result["node_count"] == 41


def test_batch8_station_layout_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch8_station_surface_atlas_layout_bundle(
        EXPORTED_BUNDLE,
        tmp_path / f"receipts/runtime_shell/demo_project/organs/{ORGAN_ID}",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == f"exported_{ORGAN_ID}_bundle"
    assert result["source_module_manifest"]["module_count"] == 1
    assert result["exercise"]["copied_macro_source_module_count"] == 1
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch8_station_layout_detached_rehashed_exact_copy_source_body_rejects(
    tmp_path: Path,
) -> None:
    bundle = _copy_detached_public_bundle(tmp_path)
    _rewrite_bundle_source_module(bundle)

    result = run_batch8_station_surface_atlas_layout_bundle(
        bundle,
        tmp_path / "detached_receipts",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert (
        "BATCH8_STATION_SOURCE_AUTHORITY_RELATION_REQUIRED"
        in result["error_codes"]
    )
    assert result["exercise"]["source_authority_binding"]["status"] == "blocked"


def test_batch8_station_layout_detached_public_refactor_relation_allows_rehashed_body(
    tmp_path: Path,
) -> None:
    bundle = _copy_detached_public_bundle(tmp_path)
    _rewrite_bundle_source_module(
        bundle,
        source_to_target_relation="source_faithful_public_refactor",
    )

    result = run_batch8_station_surface_atlas_layout_bundle(
        bundle,
        tmp_path / "detached_refactor_receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["exercise"]["source_authority_binding"] == {
        "status": "pass",
        "detached_bundle_exact_copy_requires_live_source": True,
        "allowed_detached_public_refactor_relations": [
            "source_faithful_public_light_edit",
            "source_faithful_public_refactor",
        ],
        "body_in_receipt": False,
    }


def test_batch8_station_layout_source_module_is_exact_tsx_source_ref() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["source_port_class"] == "python_port_from_typescript_layout_function"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 1

    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = EXPORTED_BUNDLE / row["path"]
        assert source.is_file(), row["source_ref"]
        assert target.is_file(), row["path"]
        assert source.read_bytes() == target.read_bytes(), row["source_ref"]
        assert row["sha256"] == _sha256(source)
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])


def test_batch8_station_layout_card_omits_private_bodies(tmp_path: Path, capsys) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / f"receipts/first_wave/{ORGAN_ID}",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["source_module_count"] == 1
    assert card["observed_negative_case_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert card["authority_floor"] == {
        "authority_ceiling": AUTHORITY_CEILING["authority_ceiling"],
        "real_substrate_disposition": AUTHORITY_CEILING["real_substrate_disposition"],
        "python_port": AUTHORITY_CEILING["python_port"],
        "react_runtime_started": AUTHORITY_CEILING["react_runtime_started"],
        "browser_render_authorized": AUTHORITY_CEILING["browser_render_authorized"],
        "navigation_graph_authority": AUTHORITY_CEILING["navigation_graph_authority"],
        "repo_mutation_authorized": AUTHORITY_CEILING["repo_mutation_authorized"],
        "source_mutation_authorized": AUTHORITY_CEILING["source_mutation_authorized"],
        "publication_authorized": AUTHORITY_CEILING["publication_authorized"],
        "release_authorized": AUTHORITY_CEILING["release_authorized"],
    }
    assert card["body_floor"] == {
        "body_in_receipt": False,
        "source_module_body_in_receipt": False,
        "receipt_body_scan_status": "pass",
        "source_bodies_in_card": False,
        "secret_scan_scope_in_card": False,
    }
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "source_body" not in _walk_keys(result)
    assert "body" not in _walk_keys(result)

    assert (
        main(
            [
                "run",
                "--input",
                str(FIXTURE_INPUT),
                "--out",
                str(tmp_path / "cli_card"),
                "--card",
            ]
        )
        == 0
    )
    cli_card = json.loads(capsys.readouterr().out)
    assert cli_card["authority_floor"] == card["authority_floor"]
    assert cli_card["body_floor"] == card["body_floor"]


def test_batch8_station_layout_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["body_in_receipt"] is False


def test_batch8_station_layout_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        path = fixture / f"{case_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture,
        tmp_path / f"microcosm-substrate/receipts/first_wave/{ORGAN_ID}",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["semantic_negative_case_evaluator_used"] is True
    assert all(row["semantic_evaluator_used"] for row in result["negative_case_semantics"])
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    assert "BATCH8_STATION_LAYOUT_ATTENTION_SORT_REQUIRED" in result["error_codes"]
    assert "BATCH8_STATION_LAYOUT_SLACK_LANE_SPEND_REQUIRED" in result["error_codes"]
    assert "BATCH8_STATION_LAYOUT_UNKNOWN_GROUP_ROUTED_UNASSIGNED" in result["error_codes"]
