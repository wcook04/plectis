from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.workstream_driver_recency_coalescer import (
    AUTHORITY_CEILING,
    AUTHORITY_FALSE_FLAGS,
    ENGINE_ID,
    EXPECTED_NEGATIVE_CASES,
    GROUPING_NEGATIVE_CASES,
    group_by_driver,
    result_card,
    run,
    run_workstream_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
ORGAN_ID = "workstream_driver_recency_coalescer"
FIXTURE_INPUT = MICROCOSM_ROOT / f"fixtures/first_wave/{ORGAN_ID}/input"
EXPORTED_BUNDLE = MICROCOSM_ROOT / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle"
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"


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


def _copy_public_workstream_fixture(tmp_path: Path) -> tuple[Path, Path]:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/workstream_driver_recency_coalescer",
        public_root / "examples/workstream_driver_recency_coalescer",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/workstream_driver_recency_coalescer",
        public_root / "fixtures/first_wave/workstream_driver_recency_coalescer",
    )
    return public_root, public_root / f"fixtures/first_wave/{ORGAN_ID}/input"


def test_group_by_driver_matches_workstream_board_semantics() -> None:
    rows = group_by_driver(
        [
            {
                "event_id": "old-codex",
                "recorded_at": "2026-05-31T10:00:00Z",
                "summary": "older codex",
                "gate_reason": "gate_old",
                "active_driver": " Codex ",
            },
            {
                "event_id": "bridge",
                "recorded_at": "2026-05-31T11:00:00Z",
                "summary": "bridge move",
                "active_driver": "bridge",
            },
            {
                "event_id": "new-codex",
                "recorded_at": "2026-05-31T12:00:00Z",
                "summary": "newer codex",
                "gate_reason": "gate_new",
                "active_driver": "codex",
            },
            {
                "event_id": "missing-driver",
                "recorded_at": "2026-05-31T13:00:00Z",
                "summary": "newest but unclassified",
                "active_driver": None,
            },
        ]
    )

    assert [row["key"] for row in rows] == ["codex", "bridge", "unclassified"]
    assert rows[0]["driver"] == "Codex"
    assert rows[0]["count"] == 2
    assert rows[0]["latestIso"] == "2026-05-31T12:00:00Z"
    assert rows[0]["latestSummary"] == "newer codex"
    assert rows[0]["gateReason"] == "gate_new"
    assert rows[-1]["key"] == "unclassified"


def test_group_by_driver_canonicalizes_unclassified_sentinel_case() -> None:
    rows = group_by_driver(
        [
            {
                "event_id": "casey-unclassified",
                "recorded_at": "2026-05-31T14:00:00Z",
                "summary": "newest but still sentinel",
                "active_driver": " Unclassified ",
            },
            {
                "event_id": "codex",
                "recorded_at": "2026-05-31T13:00:00Z",
                "summary": "older classified driver",
                "active_driver": "codex",
            },
        ]
    )

    assert [row["key"] for row in rows] == ["codex", "unclassified"]
    assert rows[-1]["driver"] == "unclassified"
    assert rows[-1]["latestSummary"] == "newest but still sentinel"


def test_group_by_driver_moves_when_driver_input_changes_r2_to_r4() -> None:
    base_changes = [
        {
            "event_id": "r2-old",
            "recorded_at": "2026-05-31T10:00:00Z",
            "summary": "older r2",
            "active_driver": "R2",
        },
        {
            "event_id": "r2-new",
            "recorded_at": "2026-05-31T12:00:00Z",
            "summary": "r2 event",
            "active_driver": "r2",
        },
        {
            "event_id": "r4",
            "recorded_at": "2026-05-31T11:00:00Z",
            "summary": "r4 event",
            "active_driver": "R4",
        },
        {
            "event_id": "missing-driver",
            "recorded_at": "2026-05-31T13:00:00Z",
            "summary": "unclassified event",
            "active_driver": None,
        },
    ]
    mutated_changes = [dict(row) for row in base_changes]
    mutated_changes[1]["active_driver"] = "R4"
    mutated_changes[1]["summary"] = "r2 event moved to r4"

    base_rows = group_by_driver(base_changes)
    mutated_rows = group_by_driver(mutated_changes)

    assert [row["key"] for row in base_rows] == ["r2", "r4", "unclassified"]
    assert [row["key"] for row in mutated_rows] == ["r4", "r2", "unclassified"]
    assert base_rows != mutated_rows
    assert mutated_rows[0]["count"] == 2
    assert mutated_rows[0]["latestSummary"] == "r2 event moved to r4"
    assert mutated_rows[1]["count"] == 1


def test_workstream_driver_recency_coalescer_runs_public_exercise(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / f"receipts/first_wave/{ORGAN_ID}",
        acceptance_out=tmp_path
        / f"receipts/acceptance/first_wave/{ORGAN_ID}_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_module_manifest"]["module_count"] == 1
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True
    exercise = result["exercise"]["runtime_exercises"][ENGINE_ID]
    assert exercise["driver_fold_count"] == 2
    assert exercise["newest_summary"] == "newer codex"
    assert exercise["newest_gate_reason"] == "gate_new"
    assert exercise["order_keys"] == ["codex", "bridge", "unclassified"]
    assert exercise["unclassified_pinned_last"] is True
    assert result["exercise"]["semantic_negative_case_status"] == "pass"
    assert result["exercise"]["semantic_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert {
        case["case_id"] for case in result["exercise"]["semantic_negative_cases"]
    } == set(EXPECTED_NEGATIVE_CASES)
    assert all(
        case["status"] == "rejected"
        for case in result["exercise"]["semantic_negative_cases"]
    )
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert result["exercise"]["authority_claims"] == {
        flag: False for flag in AUTHORITY_FALSE_FLAGS
    }
    assert result["body_in_receipt"] is False


def test_workstream_driver_public_exercise_rejects_stale_positive_projection(
    tmp_path: Path,
) -> None:
    public_root, fixture = _copy_public_workstream_fixture(tmp_path)
    manifest_path = fixture / "workstream_driver_recency_coalescer_probe_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["positive_fixture"]["recent_changes"].append(
        {
            "event_id": "newer-bridge",
            "recorded_at": "2026-05-31T12:30:00Z",
            "summary": "newer bridge move",
            "gate_reason": "gate_bridge_new",
            "active_driver": "bridge",
            "immediate_mode": None,
        }
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(fixture, public_root / f"receipts/first_wave/{ORGAN_ID}")

    assert result["status"] == "blocked"
    assert "WDRC_PUBLIC_EXERCISE_MISMATCH" in result["error_codes"]


def test_workstream_driver_public_exercise_rejects_wrong_shaped_recent_change(
    tmp_path: Path,
) -> None:
    public_root, fixture = _copy_public_workstream_fixture(tmp_path)
    manifest_path = fixture / "workstream_driver_recency_coalescer_probe_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed_row = manifest["positive_fixture"]["recent_changes"][0]
    changed_row["activeDriver"] = changed_row.pop("active_driver")
    changed_row["recordedAt"] = changed_row.pop("recorded_at")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(fixture, public_root / f"receipts/first_wave/{ORGAN_ID}")
    exercise = result["exercise"]["runtime_exercises"][ENGINE_ID]
    rows_by_key = {row["key"]: row for row in exercise["rows"]}

    assert result["status"] == "blocked"
    assert "WDRC_PUBLIC_EXERCISE_MISMATCH" in result["error_codes"]
    assert exercise["driver_fold_count"] == 1
    assert rows_by_key["codex"]["count"] == 1
    assert rows_by_key["unclassified"]["count"] == 2
    assert rows_by_key["unclassified"]["latestIso"] == "2026-05-31T13:00:00Z"


def test_workstream_driver_common_negative_cases_ignore_declared_codes(
    tmp_path: Path,
) -> None:
    public_root, fixture = _copy_public_workstream_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        negative_path = fixture / f"{case_id}.json"
        payload = json.loads(negative_path.read_text(encoding="utf-8"))
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        negative_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(fixture, public_root / f"receipts/first_wave/{ORGAN_ID}")

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_workstream_driver_recency_coalescer_rejects_authority_overclaim(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/workstream_driver_recency_coalescer",
        public_root / "examples/workstream_driver_recency_coalescer",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/workstream_driver_recency_coalescer",
        public_root / "fixtures/first_wave/workstream_driver_recency_coalescer",
    )
    fixture = public_root / f"fixtures/first_wave/{ORGAN_ID}/input"
    manifest_path = fixture / "workstream_driver_recency_coalescer_probe_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["authority_claims"]["frontend_release_authorized"] = True
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    result = run(fixture, public_root / f"receipts/first_wave/{ORGAN_ID}")

    assert result["status"] == "blocked"
    assert "WDRC_AUTHORITY_OVERCLAIM" in result["error_codes"]


def test_workstream_driver_static_negative_codes_are_not_enough(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/workstream_driver_recency_coalescer",
        public_root / "examples/workstream_driver_recency_coalescer",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/workstream_driver_recency_coalescer",
        public_root / "fixtures/first_wave/workstream_driver_recency_coalescer",
    )
    fixture = public_root / f"fixtures/first_wave/{ORGAN_ID}/input"
    negative_path = fixture / "recency_sort_wrong.json"
    payload = json.loads(negative_path.read_text(encoding="utf-8"))
    payload.pop("recent_changes", None)
    payload.pop("declared_rows", None)
    negative_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(fixture, public_root / f"receipts/first_wave/{ORGAN_ID}")

    assert result["status"] == "blocked"
    assert "WDRC_SEMANTIC_NEGATIVE_DATA_MISSING" in result["error_codes"]
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in result["error_codes"]
    assert "CROWN_JEWEL_NEGATIVE_CASE_CODE_MISSING" in result["error_codes"]
    assert "WDRC_RECENCY_SORT_DESC_REQUIRED" not in result["error_codes"]


def test_workstream_driver_negative_projection_must_disagree_with_recompute(
    tmp_path: Path,
) -> None:
    for case_id in GROUPING_NEGATIVE_CASES:
        case_root = tmp_path / case_id
        public_root, fixture = _copy_public_workstream_fixture(case_root)
        negative_path = fixture / f"{case_id}.json"
        payload = json.loads(negative_path.read_text(encoding="utf-8"))
        payload["declared_rows"] = group_by_driver(payload["recent_changes"])
        negative_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = run(fixture, public_root / f"receipts/first_wave/{ORGAN_ID}")
        semantic_case = next(
            case
            for case in result["exercise"]["semantic_negative_cases"]
            if case["case_id"] == case_id
        )

        assert result["status"] == "blocked"
        assert semantic_case["status"] == "not_rejected"
        assert "WDRC_SEMANTIC_NEGATIVE_NOT_REJECTED" in result["error_codes"]


def test_workstream_driver_recency_coalescer_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_workstream_bundle(
        EXPORTED_BUNDLE,
        tmp_path / f"receipts/runtime_shell/demo_project/organs/{ORGAN_ID}",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == f"exported_{ORGAN_ID}_bundle"
    assert result["source_module_manifest"]["module_count"] == 1
    assert result["exercise"]["copied_macro_source_module_count"] == 1
    assert result["exercise"]["semantic_negative_case_status"] == "pass"
    assert result["exercise"]["semantic_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_workstream_driver_bundle_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = public_root / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle"
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_workstream_bundle(
        bundle,
        public_root / f"receipts/runtime_shell/demo_project/organs/{ORGAN_ID}",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False


def test_workstream_driver_source_module_is_exact_macro_body_import() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["module_count"] == 1
    assert manifest["body_in_receipt"] is False
    assert {row["module_id"] for row in manifest["modules"]} == {ENGINE_ID}

    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = EXPORTED_BUNDLE / row["path"]
        assert source.is_file(), row["source_ref"]
        assert target.is_file(), row["path"]
        assert source.read_bytes() == target.read_bytes(), row["source_ref"]
        assert row["sha256"] == _sha256(source)
        assert row["source_sha256"] == row["sha256"]
        assert row["target_sha256"] == row["sha256"]
        assert row["sha256_match"] is True
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])


def test_workstream_driver_card_omits_private_bodies(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / f"receipts/first_wave/{ORGAN_ID}",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["semantic_negative_case_evaluator_used"] is True
    assert card["source_module_count"] == 1
    assert card["observed_negative_case_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "assistant_raw_text" not in _walk_keys(result)
    assert "raw_text" not in _walk_keys(result)
    assert "body" not in _walk_keys(result)
