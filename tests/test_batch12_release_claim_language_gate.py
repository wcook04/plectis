from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.batch12_release_claim_language_gate import (
    EXPECTED_NEGATIVE_CASES,
    result_card,
    run,
    run_batch12_release_claim_language_gate_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/batch12_release_claim_language_gate/input"
)
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch12_release_claim_language_gate/"
    "exported_batch12_release_claim_language_gate_bundle"
)
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_input_with_fixture(tmp_path: Path, **updates: Any) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/batch12_release_claim_language_gate/"
        "exported_batch12_release_claim_language_gate_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    input_dir = (
        public_root
        / "fixtures/first_wave/batch12_release_claim_language_gate/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)
    fixture_path = input_dir / "release_gate_fixture.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture.update(updates)
    fixture_path.write_text(
        json.dumps(fixture, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return input_dir


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


def test_batch12_release_claim_language_gate_runs_macro_mechanism(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch12_release_claim_language_gate",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "batch12_release_claim_language_gate_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    exercise = result["exercise"]
    assert exercise["mechanism_count"] == 1
    mechanism = exercise["mechanisms"][0]
    assert mechanism["mechanism_id"] == "release_claim_language_gate"
    assert mechanism["positive_boundary_clear"] is True
    assert all(row["computed"] for row in mechanism["negative_cases"])
    assert exercise["safe_gate_summary"]["boundary_or_negative_context_count"] == 1
    assert exercise["active_gate_summary"]["active_claim_blocker_count"] == 2
    perturbation = exercise["release_claim_perturbation"]
    assert perturbation["body_in_receipt"] is False
    assert perturbation["safe_status"] == "clear_boundary_only"
    assert perturbation["active_status"] == "active_claim_blocked"
    assert perturbation["publication_overclaim_status"] == "active_claim_blocked"
    assert perturbation["verdict_moved"] is True
    assert perturbation["not_release_authority"] is True
    assert set(perturbation["publication_overclaim_phrase_ids"]) >= {
        "publicly_released",
        "release_ready",
        "source_available",
    }
    assert result["body_in_receipt"] is False


def test_batch12_release_claim_language_gate_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_batch12_release_claim_language_gate_bundle(
        EXPORTED_BUNDLE,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "batch12_release_claim_language_gate",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch12_release_claim_language_gate_bundle"
    assert result["source_module_manifest"]["module_count"] == 1
    assert result["exercise"]["mechanism_count"] == 1
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0


def test_batch12_release_claim_language_gate_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/batch12_release_claim_language_gate/"
        "exported_batch12_release_claim_language_gate_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch12_release_claim_language_gate_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/batch12_release_claim_language_gate",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False


def test_batch12_release_claim_language_gate_rejects_fixture_path_traversal(
    tmp_path: Path,
) -> None:
    input_dir = _copy_input_with_fixture(tmp_path, active_file="../escape.md")

    result = run(
        input_dir,
        tmp_path / "receipts/first_wave/batch12_release_claim_language_gate",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "BATCH12_RELEASE_FIXTURE_PATH_UNSAFE" in result["error_codes"]
    assert result["exercise"]["mechanisms"][0]["status"] == "blocked"
    assert not (tmp_path / "escape.md").exists()


def test_batch12_release_claim_language_gate_rejects_control_character_fixture_names(
    tmp_path: Path,
) -> None:
    input_dir = _copy_input_with_fixture(
        tmp_path,
        active_file="affirmative_overclaim.md\ninjected.md",
    )

    result = run(
        input_dir,
        tmp_path / "receipts/first_wave/batch12_release_claim_language_gate",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "BATCH12_RELEASE_FIXTURE_PATH_CONTROL_CHAR" in result["error_codes"]
    assert result["exercise"]["mechanisms"][0]["status"] == "blocked"
    assert not (tmp_path / "injected.md").exists()


def test_batch12_release_claim_language_gate_rejects_duplicate_fixture_keys(
    tmp_path: Path,
) -> None:
    input_dir = _copy_input_with_fixture(tmp_path)
    fixture_path = input_dir / "release_gate_fixture.json"
    fixture_path.write_text(
        '{"safe_text":"Microcosm is not a release approval.",'
        '"safe_text":"Microcosm is open-source production-ready."}',
        encoding="utf-8",
    )

    result = run(
        input_dir,
        tmp_path / "receipts/first_wave/batch12_release_claim_language_gate",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "BATCH12_RELEASE_FIXTURE_INVALID_JSON" in result["error_codes"]
    assert "CROWN_JEWEL_INPUT_INVALID_JSON" in result["error_codes"]
    assert result["exercise"]["mechanisms"][0]["status"] == "blocked"
    assert result["exercise"]["computed_negative_case_count"] == 0


def test_batch12_release_claim_language_gate_rejects_duplicate_fixture_names(
    tmp_path: Path,
) -> None:
    input_dir = _copy_input_with_fixture(
        tmp_path,
        active_file="safe_boundary.md",
    )

    result = run(
        input_dir,
        tmp_path / "receipts/first_wave/batch12_release_claim_language_gate",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "BATCH12_RELEASE_FIXTURE_DUPLICATE_DOC_NAME" in result["error_codes"]
    assert result["exercise"]["mechanisms"][0]["status"] == "blocked"


def test_batch12_release_claim_language_gate_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 1
    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = EXPORTED_BUNDLE / row["path"]
        assert target.is_file()
        assert row["source_to_target_relation"] == "exact_copy"
        assert row["sha256"] == _sha256(target)
        assert row["source_sha256"] == row["target_sha256"] == row["sha256"]
        if source.is_file():
            assert source.read_bytes() == target.read_bytes()
            assert row["sha256"] == _sha256(source)
        assert row["source_sha256"] == row["sha256"]
        assert row["target_sha256"] == row["sha256"]
        assert row["sha256_match"] is True
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])


def test_batch12_release_claim_language_gate_card_omits_bodies(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/batch12_release_claim_language_gate",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["source_module_count"] == 1
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "source_body" not in _walk_keys(result)
    assert "matched_excerpt" not in _walk_keys(result)


def test_batch12_release_claim_language_gate_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["fixture_role"] == "negative_case_label_not_verdict_authority"
        assert payload["body_in_receipt"] is False


def test_batch12_release_claim_language_gate_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    input_dir = _copy_input_with_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        path = input_dir / f"{case_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["status"] = "pass"
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        input_dir,
        tmp_path / "receipts/first_wave/batch12_release_claim_language_gate",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["semantic_negative_case_evaluator_used"] is True
    assert all(
        row["semantic_evaluator_used"] for row in result["negative_case_semantics"]
    )
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    assert "BATCH12_RELEASE_CLAIM_ACTIVE_BLOCKER" in result["error_codes"]
    assert "BATCH12_RELEASE_CLAIM_ASSERT_CLEAR_EXIT_2" in result["error_codes"]


def test_batch12_release_claim_language_gate_bundle_negative_labels_are_not_authority(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/batch12_release_claim_language_gate/"
        "exported_batch12_release_claim_language_gate_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    for case_id in EXPECTED_NEGATIVE_CASES:
        path = bundle / f"{case_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["status"] = "pass"
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run_batch12_release_claim_language_gate_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/batch12_release_claim_language_gate",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    assert "BATCH12_RELEASE_CLAIM_ACTIVE_BLOCKER" in result["error_codes"]
    assert "BATCH12_RELEASE_CLAIM_ASSERT_CLEAR_EXIT_2" in result["error_codes"]


def test_batch12_release_claim_language_gate_publication_overclaim_perturbation_is_computed(
    tmp_path: Path,
) -> None:
    input_dir = _copy_input_with_fixture(
        tmp_path,
        publication_overclaim_text=(
            "This microcosm is publication-ready, publicly released, "
            "and source-available.\n"
        ),
    )

    result = run(
        input_dir,
        tmp_path / "receipts/first_wave/batch12_release_claim_language_gate",
        command="pytest",
    )

    assert result["status"] == "pass"
    perturbation = result["exercise"]["release_claim_perturbation"]
    assert perturbation["publication_overclaim_status"] == "active_claim_blocked"
    assert perturbation["verdict_moved"] is True
    assert set(perturbation["publication_overclaim_phrase_ids"]) >= {
        "publicly_released",
        "release_ready",
        "source_available",
    }
    serialized = json.dumps(result, sort_keys=True)
    assert "publication-ready, publicly released" not in serialized
    assert "source-available" not in serialized


def test_batch12_release_claim_language_gate_active_text_perturbation_moves_verdict(
    tmp_path: Path,
) -> None:
    input_dir = _copy_input_with_fixture(
        tmp_path,
        active_text="This remains a bounded release-gate fixture demonstration only.\n",
    )

    result = run(
        input_dir,
        tmp_path / "receipts/first_wave/batch12_release_claim_language_gate",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["exercise"]["active_gate_summary"]["active_claim_blocker_count"] == 0
    assert "BATCH12_RELEASE_CLAIM_CASE_NOT_OBSERVED" in result["error_codes"]
    assert result["exercise"]["release_claim_perturbation"]["verdict_moved"] is True
