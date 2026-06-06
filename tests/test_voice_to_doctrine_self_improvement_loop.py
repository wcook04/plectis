from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.voice_to_doctrine_self_improvement_loop import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_voice_to_doctrine_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/voice_to_doctrine_self_improvement_loop/"
    "exported_voice_to_doctrine_bundle"
)
SOURCE_MODULE_MANIFEST = BUNDLE_INPUT / "source_module_manifest.json"
FIXTURE_MANIFEST = (
    MICROCOSM_ROOT
    / "core/fixture_manifests/voice_to_doctrine_self_improvement_loop.fixture_manifest.json"
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


def _copy_fixture(public_root: Path) -> Path:
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = (
        public_root
        / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop"
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop",
        fixture,
    )
    return fixture


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_voice_to_doctrine_loop_observes_negative_cases(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/voice_to_doctrine_self_improvement_loop",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "voice_to_doctrine_self_improvement_loop_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["lesson_count"] == 4
    assert result["owner_surface_count"] == 5
    assert result["refined_existing_surface_count"] == 2
    assert result["workitem_capture_count"] == 1
    assert result["nothing_to_refine_count"] == 1
    assert result["lesson_ref_resolution_count"] == 19
    assert result["unresolved_lesson_ref_count"] == 0
    assert result["ignored_expected_label_count"] == 0
    assert all(row["resolved"] for row in result["lesson_ref_resolutions"])
    assert all(row["path_exists"] for row in result["lesson_ref_resolutions"])
    assert all(row["locator_present"] for row in result["lesson_ref_resolutions"])
    assert all(
        not str(row["resolved_ref"]).startswith("/")
        for row in result["lesson_ref_resolutions"]
    )
    assert set(result["source_pattern_refs"]) >= {
        "recursive_self_improvement_operating_loop",
        "doctrine_population_loop",
        "local_to_general_propagation",
    }
    assert result["body_import_verification"]["verification_mode"] == (
        "source_faithful_public_refactor_plus_exact_public_body_copies"
    )
    assert result["body_import_verification"]["source_module_count"] == 8
    assert result["authority_ceiling"]["raw_operator_voice_export_authorized"] is False
    assert result["authority_ceiling"]["doctrine_node_hand_edit_authorized"] is False
    assert result["authority_ceiling"]["global_doctrine_promotion_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_voice_to_doctrine_receipts_are_public_relative_and_body_free(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop",
        public_root / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop",
    )

    result = run(
        public_root / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop/input",
        public_root / "receipts/first_wave/voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        keys = _walk_keys(json.loads(text))
        assert "raw_operator_voice" not in keys
        assert "operator_voice_body" not in keys
        assert "private_thread_body" not in keys
        assert "provider_payload" not in keys
        assert "credential_value" not in keys
        assert "secret_value" not in keys
        assert "raw_seed_body" not in keys
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_voice_to_doctrine_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_voice_to_doctrine_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_voice_to_doctrine_bundle"
    assert (
        result["bundle_id"]
        == "voice_to_doctrine_self_improvement_loop_runtime_example"
    )
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["metadata_projection_not_live_learning_authority"] is True
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_count"] == 8
    assert result["verified_source_module_count"] == 8
    assert result["body_copied_material_count"] == 8
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == 8
    assert (
        result["source_open_body_imports"]["body_text_exported_in_receipts"]
        is False
    )
    assert (
        result["source_open_body_imports"]["source_refs_live_checked"]
        is True
    )
    assert (
        result["source_open_body_imports"]["source_target_exact_copy_count"]
        == 8
    )
    assert result["status_counts"] == {
        "nothing_to_refine": 1,
        "refined_existing_surface": 2,
        "workitem_captured": 1,
    }
    assert result["lesson_ref_resolution_count"] > 0
    assert result["unresolved_lesson_ref_count"] == 0
    copied_macro_resolutions = [
        row
        for row in result["lesson_ref_resolutions"]
        if row["ref"].startswith("codex/")
    ]
    assert {
        row["ref"]
        for row in copied_macro_resolutions
    } >= {
        'codex/standards/std_task_ledger.json::"work_item_spine_contract"',
        'codex/doctrine/skills/task_ledger/task_ledger.md::id: "task_ledger"',
        "codex/doctrine/skills/task_ledger/task_ledger_metacontrol_uppropagation.md::## Entry",
    }
    assert all(row["resolved"] for row in copied_macro_resolutions)
    assert all(
        row["resolution_root"] == "source_module_manifest_target"
        for row in copied_macro_resolutions
    )
    assert all(
        row["resolved_ref"].startswith(
            "examples/voice_to_doctrine_self_improvement_loop/"
            "exported_voice_to_doctrine_bundle/source_modules/"
        )
        for row in copied_macro_resolutions
    )
    assert result["lesson_ref_resolution_count"] == 19
    assert all(row["path_exists"] for row in result["lesson_ref_resolutions"])
    assert all(row["locator_present"] for row in result["lesson_ref_resolutions"])
    assert result["required_sequence"] == [
        "sense_local_pressure",
        "classify_pressure_shape",
        "select_owner_surface",
        "mutate_or_capture_owner",
        "validate_owner_result",
        "bind_closeout",
        "publish_reentry_condition",
    ]


def test_voice_to_doctrine_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/voice_to_doctrine_self_improvement_loop/"
        "exported_voice_to_doctrine_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_sha256"] = "0" * 64
    manifest["modules"][0]["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_voice_to_doctrine_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "fail"
    assert result["source_module_manifest_status"] == "fail"
    assert result["verified_source_module_count"] == 7
    assert result["source_open_body_imports"]["status"] == "fail"
    assert "VOICE_DOCTRINE_SOURCE_MODULE_HASH_MISMATCH" in result["error_codes"]
    assert "VOICE_DOCTRINE_SOURCE_MODULE_HASH_MISMATCH" in result[
        "blocking_error_codes"
    ]


def test_voice_to_doctrine_rejects_rehashed_source_module_body_tamper(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/voice_to_doctrine_self_improvement_loop/"
        "exported_voice_to_doctrine_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    row = manifest["modules"][0]
    target_path = public_root / row["target_ref"]
    tampered_text = (
        target_path.read_text(encoding="utf-8")
        + "\n\n# Tampered copied body with manifest-local hashes refreshed\n"
    )
    target_path.write_text(tampered_text, encoding="utf-8")
    tampered_body = target_path.read_bytes()
    tampered_sha = hashlib.sha256(tampered_body).hexdigest()
    row["target_sha256"] = tampered_sha
    row["source_sha256"] = tampered_sha
    row["byte_count"] = len(tampered_body)
    row["line_count"] = tampered_text.count("\n") + (
        0 if tampered_text.endswith("\n") else 1
    )
    _write_json(manifest_path, manifest)

    result = run_voice_to_doctrine_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "fail"
    assert result["source_module_manifest_status"] == "fail"
    assert result["verified_source_module_count"] == 7
    assert result["source_open_body_imports"]["status"] == "fail"
    assert "VOICE_DOCTRINE_SOURCE_MODULE_HASH_MISMATCH" not in result["error_codes"]
    assert "VOICE_DOCTRINE_SOURCE_MODULE_SOURCE_HASH_MISMATCH" in result[
        "blocking_error_codes"
    ]
    assert "VOICE_DOCTRINE_SOURCE_MODULE_SOURCE_TARGET_COPY_MISMATCH" in result[
        "blocking_error_codes"
    ]
    changed_import = result["source_module_imports"][0]
    assert changed_import["source_path_exists"] is True
    assert changed_import["source_hash_matches"] is False
    assert changed_import["source_target_exact_copy"] is False
    assert changed_import["required_anchors_present"] is True


def test_voice_to_doctrine_rejects_source_module_source_ref_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/voice_to_doctrine_self_improvement_loop/"
        "exported_voice_to_doctrine_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_ref"] = "codex/standards/std_task_ledger.json"
    _write_json(manifest_path, manifest)

    result = run_voice_to_doctrine_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "fail"
    assert "VOICE_DOCTRINE_SOURCE_MODULE_SOURCE_HASH_MISMATCH" in result[
        "blocking_error_codes"
    ]
    assert "VOICE_DOCTRINE_SOURCE_MODULE_SOURCE_TARGET_COPY_MISMATCH" in result[
        "blocking_error_codes"
    ]
    changed_import = result["source_module_imports"][0]
    assert changed_import["source_path_exists"] is True
    assert changed_import["source_hash_matches"] is False
    assert changed_import["source_target_exact_copy"] is False


def test_voice_to_doctrine_rejects_source_module_missing_live_source_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/voice_to_doctrine_self_improvement_loop/"
        "exported_voice_to_doctrine_bundle"
    )
    shutil.copytree(BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["source_ref"] = "codex/definitely_missing_source.md"
    _write_json(manifest_path, manifest)

    result = run_voice_to_doctrine_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "fail"
    assert "VOICE_DOCTRINE_SOURCE_MODULE_SOURCE_MISSING" in result[
        "blocking_error_codes"
    ]
    assert result["source_module_imports"][0]["source_path_exists"] is False


def test_voice_to_doctrine_rejects_dead_lesson_surface_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = (
        public_root
        / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop"
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop",
        fixture,
    )
    lessons_path = fixture / "input/local_lessons.json"
    lessons = json.loads(lessons_path.read_text(encoding="utf-8"))
    lessons["lessons"][0]["changed_surface_ref"] = (
        "public_safe_bundle/fabricated_dead_surface.md::Nope"
    )
    lessons_path.write_text(
        json.dumps(lessons, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "fail"
    assert "VOICE_DOCTRINE_SURFACE_REF_UNRESOLVED" in result["error_codes"]
    assert "VOICE_DOCTRINE_SURFACE_REF_UNRESOLVED" in result[
        "blocking_error_codes"
    ]


def test_voice_to_doctrine_resolves_lesson_ref_paths_and_anchors(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    fixture = _copy_fixture(public_root)
    lessons_path = fixture / "input/local_lessons.json"
    lessons = json.loads(lessons_path.read_text(encoding="utf-8"))
    lessons["lessons"][0]["evidence_ref"] = (
        "paper_modules/voice_to_doctrine_self_improvement_loop.md::Public Mechanics"
    )
    lessons["lessons"][0]["closeout_ref"] = (
        "receipts/first_wave/voice_to_doctrine_self_improvement_loop/"
        "voice_to_doctrine_self_improvement_loop_result.json::workitem_capture_count"
    )
    _write_json(lessons_path, lessons)

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert "VOICE_DOCTRINE_SURFACE_REF_UNRESOLVED" not in result["error_codes"]
    closeout_resolution = next(
        row
        for row in result["lesson_ref_resolutions"]
        if row["lesson_id"] == "microcosm_receipt_theater_rejected"
        and row["field_name"] == "closeout_ref"
    )
    assert closeout_resolution["resolved"] is True
    assert closeout_resolution["locator"] == "workitem_capture_count"
    assert closeout_resolution["resolved_ref"].endswith(
        "voice_to_doctrine_self_improvement_loop_result.json"
    )


def test_voice_to_doctrine_changed_surface_ref_real_target_moves_resolution(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    fixture = _copy_fixture(public_root)
    lessons_path = fixture / "input/local_lessons.json"
    lessons = json.loads(lessons_path.read_text(encoding="utf-8"))
    moved_ref = (
        "src/microcosm_core/organs/voice_to_doctrine_self_improvement_loop.py"
        "::def run("
    )
    lessons["lessons"][0]["changed_surface_ref"] = moved_ref
    _write_json(lessons_path, lessons)

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "pass"
    moved_resolution = next(
        row
        for row in result["lesson_ref_resolutions"]
        if row["lesson_id"] == "microcosm_receipt_theater_rejected"
        and row["field_name"] == "changed_surface_ref"
    )
    assert moved_resolution["ref"] == moved_ref
    assert moved_resolution["resolved"] is True
    assert moved_resolution["locator"] == "def run("
    assert moved_resolution["resolved_ref"].endswith(
        "src/microcosm_core/organs/voice_to_doctrine_self_improvement_loop.py"
    )


def test_voice_to_doctrine_rejects_mutated_lesson_ref_anchors(
    tmp_path: Path,
) -> None:
    ref_cases = (
        (
            "changed_surface_ref",
            "paper_modules/voice_to_doctrine_self_improvement_loop.md::Missing Public Mechanics Anchor",
        ),
        (
            "evidence_ref",
            "paper_modules/voice_to_doctrine_self_improvement_loop.md::Missing Reader Evidence Anchor",
        ),
        (
            "validation_ref",
            "tests/missing_validation_receipt.py::missing_anchor",
        ),
        (
            "closeout_ref",
            "paper_modules/voice_to_doctrine_self_improvement_loop.md::Missing Anti-Claim Anchor",
        ),
    )
    for field_name, mutated_ref in ref_cases:
        public_root = tmp_path / field_name / "microcosm-substrate"
        shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
        fixture = (
            public_root
            / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop"
        )
        shutil.copytree(
            MICROCOSM_ROOT
            / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop",
            fixture,
        )
        lessons_path = fixture / "input/local_lessons.json"
        lessons = json.loads(lessons_path.read_text(encoding="utf-8"))
        lessons["lessons"][0][field_name] = mutated_ref
        lessons_path.write_text(
            json.dumps(lessons, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = run(
            fixture / "input",
            public_root
            / "receipts/first_wave/voice_to_doctrine_self_improvement_loop",
            command="pytest",
        )

        assert result["status"] == "fail"
        assert "VOICE_DOCTRINE_SURFACE_REF_UNRESOLVED" in result["error_codes"]
        assert "VOICE_DOCTRINE_SURFACE_REF_UNRESOLVED" in result[
            "blocking_error_codes"
        ]
        assert any(
            field_name in str(finding.get("subject_id"))
            and mutated_ref in str(finding.get("subject_id"))
            for finding in result["blocking_findings"]
        )


def test_voice_to_doctrine_rejects_json_pointer_when_anchor_text_is_absent(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = (
        public_root
        / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop"
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop",
        fixture,
    )
    lessons_path = fixture / "input/local_lessons.json"
    lessons = json.loads(lessons_path.read_text(encoding="utf-8"))
    mutated_ref = (
        "receipts/first_wave/voice_to_doctrine_self_improvement_loop/"
        "voice_to_doctrine_self_improvement_loop_result.json::/workitem_capture_count"
    )
    lessons["lessons"][2]["closeout_ref"] = mutated_ref
    lessons_path.write_text(
        json.dumps(lessons, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "fail"
    assert "VOICE_DOCTRINE_SURFACE_REF_UNRESOLVED" in result[
        "blocking_error_codes"
    ]
    assert any(
        row["ref"] == mutated_ref
        and row["failure_reason"] == "locator_missing"
        for row in result["lesson_ref_resolutions"]
    )


def test_voice_to_doctrine_rejects_non_public_lesson_ref_paths(
    tmp_path: Path,
) -> None:
    ref_cases = (
        "/tmp/private_voice_to_doctrine.md::Public Mechanics",
        "../AGENTS.md::Microcosm Substrate",
    )
    for ref in ref_cases:
        public_root = tmp_path / ref.replace("/", "_").replace(":", "_")
        public_root = public_root / "microcosm-substrate"
        shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
        fixture = (
            public_root
            / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop"
        )
        shutil.copytree(
            MICROCOSM_ROOT
            / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop",
            fixture,
        )
        lessons_path = fixture / "input/local_lessons.json"
        lessons = json.loads(lessons_path.read_text(encoding="utf-8"))
        lessons["lessons"][0]["changed_surface_ref"] = ref
        lessons_path.write_text(
            json.dumps(lessons, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = run(
            fixture / "input",
            public_root
            / "receipts/first_wave/voice_to_doctrine_self_improvement_loop",
            command="pytest",
        )

        assert result["status"] == "fail"
        assert "VOICE_DOCTRINE_SURFACE_REF_UNRESOLVED" in result[
            "blocking_error_codes"
        ]
        assert any(
            row["ref"] == ref
            and row["failure_reason"] == "unsafe_or_empty_path_ref"
            for row in result["lesson_ref_resolutions"]
        )


def test_voice_to_doctrine_baked_expected_labels_cannot_override_unresolved_refs(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = (
        public_root
        / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop"
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop",
        fixture,
    )
    lessons_path = fixture / "input/local_lessons.json"
    lessons = json.loads(lessons_path.read_text(encoding="utf-8"))
    lessons["lessons"][0]["changed_surface_ref"] = (
        "paper_modules/definitely_missing.md::Nope"
    )
    lessons["lessons"][0]["expected_status"] = "refined_existing_surface"
    lessons["lessons"][0]["expected_label"] = "pass"
    lessons_path.write_text(
        json.dumps(lessons, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "fail"
    assert result["ignored_expected_label_count"] == 2
    assert "VOICE_DOCTRINE_SURFACE_REF_UNRESOLVED" in result[
        "blocking_error_codes"
    ]
    assert "VOICE_DOCTRINE_BAKED_EXPECTED_LABEL_IGNORED" in result[
        "blocking_error_codes"
    ]


def test_voice_to_doctrine_status_counts_ignore_baked_expected_labels(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = (
        public_root
        / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop"
    )
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/voice_to_doctrine_self_improvement_loop",
        fixture,
    )
    lessons_path = fixture / "input/local_lessons.json"
    lessons = json.loads(lessons_path.read_text(encoding="utf-8"))
    lessons["lessons"][0]["status"] = "workitem_captured"
    lessons["lessons"][0]["reentry_condition"] = "Expected labels are ignored."
    lessons["lessons"][0]["expected_status"] = "refined_existing_surface"
    lessons["lessons"][0]["expected_label"] = "pass"
    lessons_path.write_text(
        json.dumps(lessons, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root / "receipts/first_wave/voice_to_doctrine_self_improvement_loop",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["ignored_expected_label_count"] == 2
    assert result["status_counts"] == {
        "nothing_to_refine": 1,
        "refined_existing_surface": 1,
        "workitem_captured": 2,
    }
    assert "VOICE_DOCTRINE_BAKED_EXPECTED_LABEL_IGNORED" not in result[
        "error_codes"
    ]


def test_voice_to_doctrine_exported_bundle_rejects_lesson_ref_mutations(
    tmp_path: Path,
) -> None:
    ref_cases = (
        (
            "changed_surface_ref",
            "paper_modules/fabricated_voice_to_doctrine_surface.md::Nope",
        ),
        (
            "evidence_refs",
            "paper_modules/voice_to_doctrine_self_improvement_loop.md::Inflated Missing Evidence Anchor",
        ),
        (
            "validation_ref",
            "tests/missing_validation_receipt.py::missing_anchor",
        ),
        (
            "closeout_ref",
            "paper_modules/voice_to_doctrine_self_improvement_loop.md::Missing Anti-Claim Anchor",
        ),
    )
    for field_name, mutated_ref in ref_cases:
        public_root = tmp_path / field_name / "microcosm-substrate"
        shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
        bundle = (
            public_root
            / "examples/voice_to_doctrine_self_improvement_loop/"
            "exported_voice_to_doctrine_bundle"
        )
        shutil.copytree(BUNDLE_INPUT, bundle)
        lessons_path = bundle / "local_lessons.json"
        lessons = json.loads(lessons_path.read_text(encoding="utf-8"))
        if field_name == "evidence_refs":
            lessons["lessons"][0][field_name][0] = mutated_ref
        else:
            lessons["lessons"][0][field_name] = mutated_ref
        lessons_path.write_text(
            json.dumps(lessons, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = run_voice_to_doctrine_bundle(
            bundle,
            public_root
            / "receipts/runtime_shell/demo_project/organs/"
            "voice_to_doctrine_self_improvement_loop",
            command="pytest",
        )

        assert result["status"] == "fail"
        assert "VOICE_DOCTRINE_SURFACE_REF_UNRESOLVED" in result["error_codes"]
        assert "VOICE_DOCTRINE_SURFACE_REF_UNRESOLVED" in result[
            "blocking_error_codes"
        ]
        assert any(
            field_name in str(finding.get("subject_id"))
            and mutated_ref in str(finding.get("subject_id"))
            for finding in result["blocking_findings"]
        )


def test_voice_to_doctrine_source_modules_are_exact_macro_body_copies() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))
    fixture_manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_module_import_status"] == "pass"
    assert manifest["module_count"] == 8
    assert fixture_manifest["source_open_body_imports"]["status"] == "pass"
    assert fixture_manifest["source_open_body_imports"]["body_material_count"] == 8
    assert fixture_manifest["source_open_body_imports"]["source_manifest_refs"] == [
        "examples/voice_to_doctrine_self_improvement_loop/"
        "exported_voice_to_doctrine_bundle/source_module_manifest.json"
    ]
    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = MICROCOSM_ROOT / row["target_ref"]
        text = target.read_text(encoding="utf-8")

        assert source.is_file()
        assert target.is_file()
        assert source.read_bytes() == target.read_bytes()
        assert _sha256(source) == row["source_sha256"]
        assert _sha256(target) == row["target_sha256"]
        assert row["source_sha256"] == row["target_sha256"]
        assert row["required_anchors_present"] is True
        for anchor in row["required_anchors"]:
            assert anchor in text


def test_voice_to_doctrine_bundle_card_prints_compact_summary(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "bundle-card"

    rc = main(
        [
            "run-bundle",
            "--input",
            str(BUNDLE_INPUT),
            "--out",
            str(out_dir),
            "--card",
        ]
    )

    captured = capsys.readouterr().out
    card = json.loads(captured)
    full_receipt = out_dir / "exported_voice_to_doctrine_bundle_validation_result.json"

    assert rc == 0
    assert len(captured.encode("utf-8")) < 3500
    assert full_receipt.is_file()
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["status"] == "pass"
    assert card["organ_id"] == "voice_to_doctrine_self_improvement_loop"
    assert card["input_mode"] == "exported_voice_to_doctrine_bundle"
    assert (
        card["bundle_id"]
        == "voice_to_doctrine_self_improvement_loop_runtime_example"
    )
    assert card["doctrine_loop_summary"]["lesson_count"] == 4
    assert card["doctrine_loop_summary"]["owner_surface_count"] == 5
    assert card["doctrine_loop_summary"]["refined_existing_surface_count"] == 2
    assert card["negative_case_coverage"]["expected_case_count"] == 0
    assert card["secret_exclusion_scan_summary"]["blocking_hit_count"] == 0
    assert card["secret_exclusion_scan_summary"]["hits_exported"] is False
    assert card["authority_ceiling"]["release_authorized"] is False
    assert card["source_body_floor"]["source_module_manifest_status"] == "pass"
    assert card["source_body_floor"]["source_module_count"] == 8
    assert card["source_body_floor"]["verified_source_module_count"] == 8
    assert card["source_body_floor"]["body_copied_material_count"] == 8
    assert card["no_export_guards"]["findings_exported"] is False
    assert card["no_export_guards"]["observed_negative_cases_exported"] is False
    assert card["output_economy"]["full_payload_drilldown"] == "rerun without --card"
    assert "findings" not in card
    assert "blocking_findings" not in card
    assert "observed_negative_cases" not in card
    assert "source_open_body_imports" not in card
    assert "source_module_imports" not in card
    assert "anti_claim" not in card


def test_voice_to_doctrine_fixture_card_honors_acceptance_out(
    tmp_path: Path,
    capsys: Any,
) -> None:
    out_dir = tmp_path / "fixture-card"
    acceptance_out = tmp_path / "acceptance.json"

    rc = main(
        [
            "run",
            "--input",
            str(FIXTURE_INPUT),
            "--out",
            str(out_dir),
            "--acceptance-out",
            str(acceptance_out),
            "--card",
        ]
    )

    captured = capsys.readouterr().out
    card = json.loads(captured)

    assert rc == 0
    assert len(captured.encode("utf-8")) < 3500
    assert acceptance_out.is_file()
    assert card["schema_version"] == CARD_SCHEMA_VERSION
    assert card["input_mode"] == "first_wave_fixture"
    assert card["negative_case_coverage"]["expected_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert card["negative_case_coverage"]["observed_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert card["negative_case_coverage"]["missing_negative_cases"] == []
    assert card["no_export_guards"]["private_bodies_exported"] is False
    assert card["no_export_guards"]["provider_payloads_exported"] is False
