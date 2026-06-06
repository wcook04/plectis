from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.batch10_live_source_drift_capsule import (
    AUTHORITY_CEILING,
    EXPECTED_ENGINES,
    EXPECTED_NEGATIVE_CASES,
    evaluate_negative_case,
    result_card,
    run,
    run_batch10_live_source_drift_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch10_live_source_drift_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch10_live_source_drift_capsule/exported_batch10_live_source_drift_capsule_bundle"
)
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


def _copy_exported_bundle(tmp_path: Path) -> tuple[Path, Path]:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/batch10_live_source_drift_capsule/"
        "exported_batch10_live_source_drift_capsule_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    return public_root, bundle


def _copy_public_fixture(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/batch10_live_source_drift_capsule",
        public_root / "examples/batch10_live_source_drift_capsule",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/batch10_live_source_drift_capsule",
        public_root / "fixtures/first_wave/batch10_live_source_drift_capsule",
    )
    return public_root / "fixtures/first_wave/batch10_live_source_drift_capsule/input"


def _refresh_manifest_digest_for_body(
    bundle: Path,
    *,
    row_index: int,
    body: str,
) -> tuple[dict[str, Any], str]:
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = manifest["modules"][row_index]
    target = bundle / row["path"]
    target.write_text(body, encoding="utf-8")
    digest = _sha256(target)
    row["sha256"] = digest
    row["source_sha256"] = digest
    row["target_sha256"] = digest
    row["byte_count"] = target.stat().st_size
    row["line_count"] = len(body.splitlines()) or 1
    row["sha256_match"] = True
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return row, digest


def _run_result(tmp_path: Path) -> dict[str, Any]:
    return run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch10_live_source_drift_capsule",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/batch10_live_source_drift_capsule_fixture_acceptance.json",
        command="pytest",
    )


def test_batch10_live_source_drift_capsule_runs_current_body_audit(tmp_path: Path) -> None:
    result = _run_result(tmp_path)

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_module_manifest"]["module_count"] == 4
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True

    exercise = result["exercise"]
    assert exercise["engine_count"] == len(EXPECTED_ENGINES)
    assert set(exercise["engine_ids"]) == set(EXPECTED_ENGINES)
    assert all(row["status"] == "pass" for row in exercise["engines"])

    by_engine = {row["engine_id"]: row for row in exercise["engines"]}
    digest = by_engine["live_source_drift_digest_refresh_matrix"]
    assert digest["row_count"] == 4
    assert digest["stale_digest_count"] == 4
    assert digest["all_current_digests_match"] is True
    assert digest["all_stale_digests_differ"] is True

    compile_gate = by_engine["copied_python_source_compile_gate"]
    assert compile_gate["module_count"] == 4
    assert compile_gate["compiled_module_count"] == 4
    assert compile_gate["import_executed"] is False

    claim_gate = by_engine["claim_ceiling_gate"]
    assert all(claim_gate["checks"].values())
    assert result["body_in_receipt"] is False


def test_batch10_live_source_drift_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch10_live_source_drift_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch10_live_source_drift_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["input_mode"] == "exported_batch10_live_source_drift_capsule_bundle"
    assert result["source_module_manifest"]["module_count"] == 4
    assert result["exercise"]["copied_macro_source_module_count"] == 4
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_live_source_drift_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 4

    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = EXPORTED_BUNDLE / row["path"]
        assert source.is_file(), row["source_ref"]
        assert target.is_file(), row["path"]
        assert source.read_bytes() == target.read_bytes(), row["source_ref"]
        assert row["sha256"] == _sha256(source)
        assert row["byte_count"] == source.stat().st_size
        assert row["source_sha256"] == row["sha256"]
        assert row["target_sha256"] == row["sha256"]
        assert row["sha256_match"] is True
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])


def test_batch10_live_source_drift_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root, bundle = _copy_exported_bundle(tmp_path)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch10_live_source_drift_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/batch10_live_source_drift_capsule",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_live_source_drift_rejects_partial_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root, bundle = _copy_exported_bundle(tmp_path)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch10_live_source_drift_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/batch10_live_source_drift_capsule",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_live_source_drift_rejects_partial_target_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root, bundle = _copy_exported_bundle(tmp_path)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch10_live_source_drift_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/batch10_live_source_drift_capsule",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_live_source_drift_rejects_source_module_manifest_boundaries(
    tmp_path: Path,
) -> None:
    cases = [
        ("missing_manifest", "CROWN_JEWEL_SOURCE_MANIFEST_MISSING"),
        ("manifest_import_class_invalid", "CROWN_JEWEL_SOURCE_IMPORT_CLASS_INVALID"),
        ("target_missing", "CROWN_JEWEL_SOURCE_TARGET_MISSING"),
        ("line_count_mismatch", "CROWN_JEWEL_SOURCE_LINE_COUNT_MISMATCH"),
        ("anchor_missing", "CROWN_JEWEL_SOURCE_ANCHOR_MISSING"),
        ("body_copy_mismatch", "CROWN_JEWEL_SOURCE_BODY_COPY_MISMATCH"),
    ]

    for case_id, expected_code in cases:
        public_root, bundle = _copy_exported_bundle(tmp_path / case_id)
        manifest_path = bundle / "source_module_manifest.json"
        probe_path = bundle / "batch10_live_source_drift_capsule_probe_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
        row = manifest["modules"][-1]
        assert row["source_ref"] == "tools/meta/factory/work_ledger.py"
        target = bundle / row["path"]

        def refresh_target_digest() -> None:
            digest = _sha256(target)
            row["sha256"] = digest
            row["source_sha256"] = digest
            row["target_sha256"] = digest
            row["byte_count"] = target.stat().st_size
            row["line_count"] = len(target.read_text(encoding="utf-8").splitlines()) or 1
            row["sha256_match"] = True
            for probe_row in probe["digest_drift_rows"]:
                if probe_row["source_ref"] == row["source_ref"]:
                    probe_row["current_sha256"] = digest

        if case_id == "missing_manifest":
            manifest_path.unlink()
        elif case_id == "manifest_import_class_invalid":
            manifest["source_import_class"] = "fixture_only_body"
        elif case_id == "target_missing":
            target.unlink()
        elif case_id == "line_count_mismatch":
            row["line_count"] = row["line_count"] + 1
        elif case_id == "anchor_missing":
            target.write_text(
                target.read_text(encoding="utf-8").replace(
                    "session-preflight", "session_preflight"
                ),
                encoding="utf-8",
            )
            refresh_target_digest()
        elif case_id == "body_copy_mismatch":
            source_copy = public_root.parent / row["source_ref"]
            source_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE_ROOT / row["source_ref"], source_copy)
            target.write_text(
                target.read_text(encoding="utf-8")
                + "\n# copied-body divergence sentinel\n",
                encoding="utf-8",
            )
            refresh_target_digest()

        if manifest_path.exists():
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        probe_path.write_text(
            json.dumps(probe, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = run_batch10_live_source_drift_bundle(
            bundle,
            public_root
            / "receipts/runtime_shell/demo_project/organs/"
            f"batch10_live_source_drift_capsule/{case_id}",
            command="pytest",
        )

        assert result["status"] == "blocked"
        assert result["source_module_manifest"]["status"] == "blocked"
        assert expected_code in result["error_codes"]
        assert any(
            row["error_code"] == expected_code for row in result["findings"]
        )
        assert result["receipt_body_scan"]["status"] == "pass"
        assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
        serialized = json.dumps(result, sort_keys=True)
        assert "def cmd_session_finalize(" not in serialized
        assert "copied-body divergence sentinel" not in serialized


def test_batch10_live_source_drift_rejects_stale_digest_replay(tmp_path: Path) -> None:
    public_root, bundle = _copy_exported_bundle(tmp_path)
    probe_path = bundle / "batch10_live_source_drift_capsule_probe_manifest.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    row = probe["digest_drift_rows"][0]
    row["stale_recorded_sha256"] = row["current_sha256"]
    probe_path.write_text(json.dumps(probe, indent=2, sort_keys=True), encoding="utf-8")

    result = run_batch10_live_source_drift_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/batch10_live_source_drift_capsule",
        command="pytest",
    )
    digest_engine = {
        row["engine_id"]: row for row in result["exercise"]["engines"]
    }["live_source_drift_digest_refresh_matrix"]

    assert result["status"] == "blocked"
    assert digest_engine["all_current_digests_match"] is True
    assert digest_engine["all_stale_digests_differ"] is False
    assert "BATCH10_LIVE_SOURCE_DRIFT_STALE_DIGEST_NOT_DETECTED" in result[
        "error_codes"
    ]
    assert "BATCH10_LIVE_SOURCE_DRIFT_ENGINE_BLOCKED" in result["error_codes"]
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_live_source_drift_rejects_duplicate_digest_rows(tmp_path: Path) -> None:
    public_root, bundle = _copy_exported_bundle(tmp_path)
    probe_path = bundle / "batch10_live_source_drift_capsule_probe_manifest.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    duplicate = dict(probe["digest_drift_rows"][0])
    duplicate["material_id"] = f"{duplicate['material_id']}_duplicate"
    probe["digest_drift_rows"].append(duplicate)
    probe_path.write_text(json.dumps(probe, indent=2, sort_keys=True), encoding="utf-8")

    result = run_batch10_live_source_drift_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/batch10_live_source_drift_capsule",
        command="pytest",
    )
    digest_engine = {
        row["engine_id"]: row for row in result["exercise"]["engines"]
    }["live_source_drift_digest_refresh_matrix"]

    assert result["status"] == "blocked"
    assert digest_engine["row_count"] == 5
    assert digest_engine["all_current_digests_match"] is True
    assert digest_engine["all_stale_digests_differ"] is True
    assert "BATCH10_LIVE_SOURCE_DRIFT_MATRIX_ROW_DUPLICATE" in result["error_codes"]
    assert "BATCH10_LIVE_SOURCE_DRIFT_MATRIX_ROW_COUNT_MISMATCH" in result["error_codes"]
    assert "BATCH10_LIVE_SOURCE_DRIFT_ENGINE_BLOCKED" in result["error_codes"]
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_live_source_drift_rejects_compile_bypass(tmp_path: Path) -> None:
    public_root, bundle = _copy_exported_bundle(tmp_path)
    manifest_row, digest = _refresh_manifest_digest_for_body(
        bundle,
        row_index=2,
        body=(
            "# def build_parser\n"
            "# admission-check\n"
            "# status\n"
            "# reconcile\n"
            "# begin\n"
            "# build_work_landing_attempt_binding\n"
            "# build_work_landing_reconcile_plan\n"
            "def broken_batch10_source(:\n"
            "    return 'not valid python'\n"
        ),
    )
    probe_path = bundle / "batch10_live_source_drift_capsule_probe_manifest.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    for row in probe["digest_drift_rows"]:
        if row["source_ref"] == manifest_row["source_ref"]:
            row["current_sha256"] = digest
    probe_path.write_text(json.dumps(probe, indent=2, sort_keys=True), encoding="utf-8")

    result = run_batch10_live_source_drift_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/batch10_live_source_drift_capsule",
        command="pytest",
    )
    compile_engine = {
        row["engine_id"]: row for row in result["exercise"]["engines"]
    }["copied_python_source_compile_gate"]

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "pass"
    assert compile_engine["compiled_module_count"] == 3
    blocked_modules = [
        row["source_ref"]
        for row in compile_engine["compiled_modules"]
        if not row["compiled_without_import"]
    ]
    assert blocked_modules == [manifest_row["source_ref"]]
    assert "BATCH10_LIVE_SOURCE_DRIFT_COMPILE_FAILED" in result["error_codes"]
    assert "BATCH10_LIVE_SOURCE_DRIFT_ENGINE_BLOCKED" in result["error_codes"]
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch10_live_source_drift_card_omits_private_bodies(tmp_path: Path) -> None:
    result = _run_result(tmp_path)
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["engine_count"] == len(EXPECTED_ENGINES)
    assert card["source_module_count"] == 4
    assert card["stale_digest_count"] == 4
    assert card["compiled_module_count"] == 4
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "source_body" not in _walk_keys(result)
    assert "matched_excerpt" not in _walk_keys(result)


def test_batch10_live_source_drift_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["body_in_receipt"] is False


def test_batch10_live_source_drift_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = fixture / f"{case_id}.json"
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        payload["status"] = "pass"
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture,
        fixture.parents[3] / "receipts/first_wave/batch10_live_source_drift_capsule",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    for expected_codes in EXPECTED_NEGATIVE_CASES.values():
        for code in expected_codes:
            assert code in result["error_codes"]
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_batch10_live_source_drift_negative_case_evaluator_rejects_each_real_case() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        result = evaluate_negative_case(case_id, FIXTURE_INPUT, expected_codes)

        assert result["status"] == "blocked"
        for code in expected_codes:
            assert code in result["error_codes"]
