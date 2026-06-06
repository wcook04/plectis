from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.organs.batch7_zenith_macos_capsule import (
    AUTHORITY_CEILING,
    EXPECTED_ENGINES,
    EXPECTED_NEGATIVE_CASES,
    evaluate_negative_case,
    result_card,
    run,
    run_batch7_zenith_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch7_zenith_macos_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch7_zenith_macos_capsule/exported_batch7_zenith_macos_capsule_bundle"
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


def _copy_exported_bundle(tmp_path: Path) -> Path:
    target = tmp_path / "exported_batch7_zenith_macos_capsule_bundle"
    shutil.copytree(EXPORTED_BUNDLE, target)
    return target


@pytest.fixture(scope="module")
def capsule_result(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("batch7_zenith_macos_capsule")
    return run(
        FIXTURE_INPUT,
        root / "receipts/first_wave/batch7_zenith_macos_capsule",
        acceptance_out=root
        / "receipts/acceptance/first_wave/batch7_zenith_macos_capsule_fixture_acceptance.json",
        command="pytest",
    )


def test_batch7_zenith_macos_capsule_runs_swift_substrate(
    capsule_result: dict[str, Any],
) -> None:
    result = capsule_result

    assert result["status"] == "pass"
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["semantic_negative_case_evaluator_used"] is True
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True

    exercise = result["exercise"]
    assert exercise["engine_count"] == len(EXPECTED_ENGINES)
    assert set(exercise["engine_ids"]) == set(EXPECTED_ENGINES)
    assert all(row["status"] == "pass" for row in exercise["engines"])

    by_engine = {row["engine_id"]: row for row in exercise["engines"]}
    assert by_engine["zenith_route_identity_catalog"]["root_defaults_to_station"] is True
    assert by_engine["zenith_backend_boot_policy"]["web_latch_suppresses_boot_overlay"] is True
    assert by_engine["zenith_backend_boot_policy"]["shutdown_policy_gates_external_processes"] is True
    assert by_engine["zenith_recording_telemetry_contract"]["api_encodes_snake_case"] is True
    assert by_engine["zenith_recording_telemetry_contract"]["api_posts_view_event_endpoint"] is True
    assert by_engine["zenith_swiftpm_witness"]["original_witness"]["witness_source"] == (
        "original_swiftpm_package"
    )
    assert by_engine["zenith_swiftpm_witness"]["original_witness"][
        "witness_package_ref"
    ].endswith("apps/zenith-macos")
    assert by_engine["zenith_swiftpm_witness"]["original_witness"]["returncode"] == 0
    assert by_engine["zenith_swiftpm_witness"]["original_witness"]["passed_test_count_observed"] == 17
    assert exercise["negative_case_probe_summary"]["schema_version"] == (
        "batch7_zenith_macos_capsule_negative_probe_v1"
    )
    assert exercise["negative_case_probe_summary"]["computed_probe_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert exercise["negative_case_probe_summary"]["fixture_verdict_echo_risk_count"] == 0
    assert result["body_in_receipt"] is False


def test_batch7_zenith_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch7_zenith_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch7_zenith_macos_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch7_zenith_macos_capsule_bundle"
    assert result["semantic_negative_case_evaluator_used"] is True
    assert result["source_module_manifest"]["module_count"] >= 8
    assert result["exercise"]["copied_macro_source_module_count"] >= 8
    swiftpm = result["exercise"]["swiftpm_witness"]
    copied_probe = result["exercise"]["copied_swiftpm_package_probe"]
    assert swiftpm["witness_source"] == "original_swiftpm_package"
    assert swiftpm["status"] == "pass"
    assert copied_probe["witness_source"] == "copied_exported_swiftpm_source_modules"
    assert copied_probe["status"] == "blocked"
    assert copied_probe["authority_ceiling"] == (
        "copied_package_probe_only_public_safe_entry_body_intentionally_excluded"
    )
    assert copied_probe["witness_package_ref"].endswith(
        "examples/batch7_zenith_macos_capsule/"
        "exported_batch7_zenith_macos_capsule_bundle/source_modules/apps/zenith-macos"
    )
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"
    source_witness = result["exercise"]["source_body_witness_summary"]
    assert source_witness == {
        "schema_version": "batch7_zenith_source_body_witness_summary_v1",
        "module_count": 8,
        "body_copied_count": 8,
        "digest_match_count": 8,
        "line_count_match_count": 8,
        "anchor_complete_count": 8,
        "all_expected_digests_matched": True,
        "all_expected_line_counts_matched": True,
        "all_required_anchors_present": True,
        "digest_mismatch_refs": [],
        "line_count_mismatch_refs": [],
        "anchor_missing_refs": [],
        "witness_authority": "copied_swiftpm_source_module_manifest_and_body_digest_checks",
        "body_in_receipt": False,
    }


def test_batch7_zenith_bundle_validation_moves_with_input_source_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(MICROCOSM_ROOT)
    bundle = _copy_exported_bundle(tmp_path)
    api = (
        bundle
        / "source_modules/apps/zenith-macos/Sources/ZenithApp/ZenithAPIClient.swift"
    )
    api.write_text(
        api.read_text(encoding="utf-8").replace(
            "keyEncodingStrategy = .convertToSnakeCase",
            "keyEncodingStrategy = .useDefaultKeys",
        ),
        encoding="utf-8",
    )

    result = run_batch7_zenith_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch7_zenith_macos_capsule",
        command="pytest",
    )
    telemetry = next(
        row
        for row in result["exercise"]["engines"]
        if row["engine_id"] == "zenith_recording_telemetry_contract"
    )

    assert result["status"] == "blocked"
    assert telemetry["api_encodes_snake_case"] is False
    assert "BATCH7_ZENITH_RECORDING_TELEMETRY_KEYS_REQUIRED" in result["error_codes"]


def test_batch7_zenith_bundle_rejects_copied_swift_body_digest_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(MICROCOSM_ROOT)
    bundle = _copy_exported_bundle(tmp_path)
    runtime_supervisor = (
        bundle
        / "source_modules/apps/zenith-macos/Sources/ZenithApp/RuntimeSupervisor.swift"
    )
    runtime_supervisor.write_text(
        runtime_supervisor.read_text(encoding="utf-8")
        + "\n// public test tamper: body digest must remain load-bearing\n",
        encoding="utf-8",
    )

    result = run_batch7_zenith_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch7_zenith_macos_capsule",
        command="pytest",
    )
    source_witness = result["exercise"]["source_body_witness_summary"]

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert source_witness["digest_match_count"] == 7
    assert source_witness["line_count_match_count"] == 7
    assert source_witness["anchor_complete_count"] == 8
    assert source_witness["all_expected_digests_matched"] is False
    assert source_witness["all_expected_line_counts_matched"] is False
    assert source_witness["all_required_anchors_present"] is True
    assert source_witness["digest_mismatch_refs"] == [
        "apps/zenith-macos/Sources/ZenithApp/RuntimeSupervisor.swift"
    ]
    assert source_witness["line_count_mismatch_refs"] == [
        "apps/zenith-macos/Sources/ZenithApp/RuntimeSupervisor.swift"
    ]
    assert source_witness["anchor_missing_refs"] == []
    assert source_witness["body_in_receipt"] is False


def test_batch7_zenith_bundle_rejects_manifest_digest_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(MICROCOSM_ROOT)
    bundle = _copy_exported_bundle(tmp_path)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module = next(
        row
        for row in manifest["modules"]
        if row["source_ref"] == "apps/zenith-macos/Sources/ZenithApp/ZenithAPIClient.swift"
    )
    module["sha256"] = "0" * 64
    module["target_sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch7_zenith_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch7_zenith_macos_capsule",
        command="pytest",
    )
    source_witness = result["exercise"]["source_body_witness_summary"]

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert source_witness["digest_match_count"] == 7
    assert source_witness["anchor_complete_count"] == 8
    assert source_witness["all_expected_digests_matched"] is False
    assert source_witness["all_required_anchors_present"] is True
    assert source_witness["digest_mismatch_refs"] == [
        "apps/zenith-macos/Sources/ZenithApp/ZenithAPIClient.swift"
    ]
    assert source_witness["anchor_missing_refs"] == []
    assert source_witness["body_in_receipt"] is False


def test_batch7_zenith_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] >= 8
    assert manifest["public_safe_carveouts"][0]["source_ref"].endswith("ZenithApp.swift")

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


def test_batch7_zenith_card_omits_private_bodies(
    capsule_result: dict[str, Any],
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    result = capsule_result
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["engine_count"] == len(EXPECTED_ENGINES)
    assert card["swiftpm_witness_status"] == "pass"
    assert card["source_body_witness_summary"]["digest_match_count"] == 8
    assert card["source_body_witness_summary"]["body_in_receipt"] is False
    assert card["body_in_receipt"] is False
    assert card["authority_floor"] == {
        "authority_ceiling": "batch7_zenith_macos_capsule_not_app_launch_or_host_control_authority",
        "real_substrate_disposition": "real_substrate_capsule",
        "release_authorized": False,
        "publication_authorized": False,
        "provider_dispatch": False,
        "model_dispatch": False,
        "browser_or_wallet_access": False,
        "native_app_launch_authorized": False,
        "source_mutation_authorized": False,
        "operator_thread_authority": False,
        "semantic_truth_authority": False,
        "test_completeness_proof": False,
    }
    assert card["body_floor"] == {
        "body_in_receipt": False,
        "source_module_body_in_receipt": False,
        "receipt_body_scan_status": "pass",
        "swiftpm_stdout_in_receipt": False,
        "swiftpm_stderr_in_receipt": False,
        "source_bodies_in_card": False,
    }
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "matched_excerpt" not in _walk_keys(result)
    assert "source_body" not in _walk_keys(result)

    cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.organs.batch7_zenith_macos_capsule",
            "run",
            "--input",
            str(FIXTURE_INPUT),
            "--out",
            str(tmp_path_factory.mktemp("batch7_zenith_cli_fixture")),
            "--card",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    cli_card = json.loads(cli.stdout)
    assert cli_card["authority_floor"] == card["authority_floor"]
    assert cli_card["body_floor"] == card["body_floor"]

    bundle_cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.organs.batch7_zenith_macos_capsule",
            "validate-bundle",
            "--input",
            str(EXPORTED_BUNDLE),
            "--out",
            str(tmp_path_factory.mktemp("batch7_zenith_cli_bundle")),
            "--card",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    bundle_cli_card = json.loads(bundle_cli.stdout)
    assert bundle_cli_card["authority_floor"] == card["authority_floor"]
    assert bundle_cli_card["body_floor"] == card["body_floor"]


def test_batch7_zenith_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["body_in_receipt"] is False
        assert payload["mutant"]["remove_tokens"]


def test_batch7_zenith_negative_case_evaluator_rejects_each_real_mutation() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        result = evaluate_negative_case(case_id, FIXTURE_INPUT, expected_codes)

        assert result["status"] == "blocked"
        assert result["verdict_authority"] == "semantic_mutation_probe"
        assert result["fixture_role"] == "negative_case_label_not_verdict_authority"
        assert result["mutation"]["removed_token_count"] >= len(
            result["mutation"]["changed_refs"]
        )
        for code in expected_codes:
            assert code in result["error_codes"]


def test_batch7_zenith_negative_case_labels_are_not_verdict_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(MICROCOSM_ROOT)
    bundle = _copy_exported_bundle(tmp_path)
    case_path = bundle / "missing_web_latch.json"
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    payload["error_codes"] = ["BATCH7_ZENITH_RECORDING_TELEMETRY_KEYS_REQUIRED"]
    case_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch7_zenith_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch7_zenith_macos_capsule",
    )
    semantic_row = next(
        row
        for row in result["negative_case_semantics"]
        if row["case_id"] == "missing_web_latch"
    )

    assert result["status"] == "blocked"
    assert "CROWN_JEWEL_RECEIPT_BODY_SCAN_BLOCKED" in result["error_codes"]
    assert semantic_row["status"] == "blocked"
    assert "BATCH7_ZENITH_WEB_LATCH_REQUIRED" in semantic_row["error_codes"]
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)


def test_batch7_zenith_negative_case_mutator_must_break_real_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(MICROCOSM_ROOT)
    bundle = _copy_exported_bundle(tmp_path)
    case_path = bundle / "missing_recording_snake_case.json"
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    payload["mutant"]["remove_tokens"] = ["TOKEN_NOT_PRESENT_IN_PUBLIC_BUNDLE"]
    case_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    direct = evaluate_negative_case(
        "missing_recording_snake_case",
        bundle,
        EXPECTED_NEGATIVE_CASES["missing_recording_snake_case"],
    )
    result = run_batch7_zenith_bundle(
        bundle,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch7_zenith_macos_capsule",
    )
    semantic_row = next(
        row
        for row in result["negative_case_semantics"]
        if row["case_id"] == "missing_recording_snake_case"
    )

    assert direct["status"] == "pass"
    assert result["status"] == "blocked"
    assert semantic_row["status"] == "pass"
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in result["error_codes"]
