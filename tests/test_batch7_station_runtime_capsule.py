from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.organs import batch7_station_runtime_capsule as capsule_module
from microcosm_core.organs._crown_jewel_common import validate_negative_cases
from microcosm_core.organs.batch7_station_runtime_capsule import (
    AUTHORITY_CEILING,
    EXPECTED_ENGINES,
    EXPECTED_NEGATIVE_CASES,
    evaluate_negative_case,
    result_card,
    run,
    run_batch7_station_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/batch7_station_runtime_capsule/input"
EXPORTED_BUNDLE = (
    MICROCOSM_ROOT
    / "examples/batch7_station_runtime_capsule/exported_batch7_station_runtime_capsule_bundle"
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


def _write_negative_case_fixtures(input_dir: Path) -> None:
    input_dir.mkdir(parents=True, exist_ok=True)
    for case_id in EXPECTED_NEGATIVE_CASES:
        (input_dir / f"{case_id}.json").write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "status": "blocked",
                    "error_codes": ["DECLARED_BOGUS_NEGATIVE_CODE"],
                    "body_in_receipt": False,
                }
            ),
            encoding="utf-8",
        )


def _semantic_runtime_fixture(
    overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    negative_exercises: dict[str, dict[str, Any]] = {
        "app_missing_boot_probe": {
            "status": "blocked",
            "mutation_applied": True,
            "engines": [
                {
                    "engine_id": "agent_trace_workbench_host_boot_probe",
                    "status": "blocked",
                    "boot_probe_before_static_import": False,
                }
            ],
        },
        "live_instrument_underfiring_attention": {
            "status": "blocked",
            "mutation_applied": True,
            "engines": [
                {
                    "engine_id": "agent_live_instrument_view_model",
                    "status": "blocked",
                    "attention_underfiring_explicit": False,
                }
            ],
        },
        "live_instrument_unknown_proof": {
            "status": "blocked",
            "mutation_applied": True,
            "engines": [
                {
                    "engine_id": "agent_live_instrument_view_model",
                    "status": "blocked",
                    "unknown_proof_not_collapsed": False,
                }
            ],
        },
        "station_store_stampede": {
            "status": "blocked",
            "mutation_applied": True,
            "engines": [
                {
                    "engine_id": "station_store_resilience_fsm",
                    "status": "blocked",
                    "operation_single_flight": False,
                }
            ],
        },
        "station_warming_no_retry": {
            "status": "blocked",
            "mutation_applied": True,
            "engines": [
                {
                    "engine_id": "station_store_resilience_fsm",
                    "status": "blocked",
                    "warming_retry_enforced": False,
                }
            ],
        },
    }
    for case_id, patch in (overrides or {}).items():
        negative_exercises[case_id].update(patch)
    return {
        "source_manifest": {"module_count": 5},
        "exercise": {"engines": []},
        "negative_exercises": negative_exercises,
    }


def _public_tmp_bundle(tmp_path: Path) -> Path:
    root = MICROCOSM_ROOT / ".microcosm/test-tmp" / f"{tmp_path.name}-{uuid.uuid4().hex}"
    bundle = root / "exported_batch7_station_runtime_capsule_bundle"
    shutil.copytree(EXPORTED_BUNDLE, bundle)
    return bundle


def _public_tmp_receipts(tmp_path: Path, name: str) -> Path:
    return (
        MICROCOSM_ROOT
        / ".microcosm/test-tmp"
        / f"{tmp_path.name}-{uuid.uuid4().hex}"
        / "receipts"
        / name
    )


def _redirect_copied_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    source_ref: str,
    old: str,
    new: str,
    *,
    replace_all: bool = False,
) -> None:
    original_copied_source = capsule_module._copied_source
    source = original_copied_source(MICROCOSM_ROOT, source_ref)
    mutated = tmp_path / "mutated_source_modules" / source_ref
    mutated.parent.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8")
    assert old in text
    mutated_text = text.replace(old, new) if replace_all else text.replace(old, new, 1)
    mutated.write_text(mutated_text, encoding="utf-8")

    def copied_source(
        public_root: Path,
        requested_ref: str,
        *,
        input_path: Path | None = None,
    ) -> Path:
        if requested_ref == source_ref:
            return mutated
        return original_copied_source(public_root, requested_ref, input_path=input_path)

    monkeypatch.setattr(capsule_module, "_copied_source", copied_source)


@pytest.fixture(scope="module")
def capsule_result(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("batch7_station_runtime_capsule")
    return run(
        FIXTURE_INPUT,
        root / "receipts/first_wave/batch7_station_runtime_capsule",
        acceptance_out=root
        / "receipts/acceptance/first_wave/batch7_station_runtime_capsule_fixture_acceptance.json",
        command="pytest",
    )


def test_batch7_station_runtime_capsule_runs_all_engines(
    capsule_result: dict[str, Any],
) -> None:
    result = capsule_result

    assert result["status"] == "pass"
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert result["semantic_negative_case_evaluator_used"] is True
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_module_manifest"]["all_expected_digests_matched"] is True
    assert result["source_module_manifest"]["all_required_anchors_present"] is True

    exercise = result["exercise"]
    assert exercise["engine_count"] == len(EXPECTED_ENGINES)
    assert set(exercise["engine_ids"]) == set(EXPECTED_ENGINES)
    assert all(row["status"] == "pass" for row in exercise["engines"])

    by_engine = {row["engine_id"]: row for row in exercise["engines"]}
    assert by_engine["agent_trace_workbench_host_boot_probe"]["boot_probe_before_static_import"] is True
    assert by_engine["agent_trace_workbench_host_boot_probe"]["active_dropdown_hoisted_before_refresh_logic"] is True
    assert by_engine["agent_trace_workbench_host_boot_probe"]["mission_refresh_timers_present"] is True
    assert by_engine["agent_trace_workbench_host_boot_probe"]["source_body_byte_count"] > 300_000
    assert by_engine["agent_live_instrument_view_model"]["original_witness"]["returncode"] == 0
    assert by_engine["agent_live_instrument_view_model"]["original_witness"]["body_in_receipt"] is False
    assert by_engine["agent_live_instrument_view_model"]["original_witness"][
        "command_executed"
    ] is True
    assert by_engine["agent_live_instrument_view_model"]["original_witness"][
        "witness_workspace_mode"
    ] == "temp_public_safe_copied_ui_workspace"
    assert by_engine["agent_live_instrument_view_model"]["typed_status_bucket_count"] == 6
    assert by_engine["agent_live_instrument_view_model"]["typed_scope_bucket_count"] == 4
    assert by_engine["agent_live_instrument_view_model"]["unknown_proof_not_collapsed"] is True
    assert by_engine["agent_live_instrument_view_model"]["attention_underfiring_explicit"] is True
    assert by_engine["station_store_resilience_fsm"]["live_state_count"] == 4
    assert by_engine["station_store_resilience_fsm"]["bounded_initial_backoff"] is True
    assert by_engine["station_store_resilience_fsm"]["operation_single_flight"] is True
    assert by_engine["station_store_resilience_fsm"]["warming_retry_enforced"] is True
    assert by_engine["station_store_resilience_fsm"]["stale_timer_gate_present"] is True
    assert result["body_in_receipt"] is False


def test_batch7_station_runtime_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch7_station_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch7_station_runtime_capsule",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_batch7_station_runtime_capsule_bundle"
    assert result["source_module_manifest"]["module_count"] >= 5
    assert result["exercise"]["copied_macro_source_module_count"] >= 5
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch7_station_runtime_bundle_runs_public_safe_vitest_witness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}

    def passing_public_witness(
        command: list[str],
        *,
        cwd: Path,
        witness_mode: str,
        timeout: int = 45,
    ) -> dict[str, Any]:
        observed["command"] = command
        observed["cwd"] = cwd
        observed["witness_mode"] = witness_mode
        observed["timeout"] = timeout
        assert cwd.name == "ui"
        assert (cwd / "package.json").is_file()
        assert (cwd / "src/components/world/agentLiveInstrumentViewModel.ts").is_file()
        assert (cwd / "src/stores/useStation.ts").is_file()
        return {
            "status": "pass",
            "returncode": 0,
            "witness_mode": witness_mode,
            "command_executed": True,
            "stdout_byte_count": 0,
            "stderr_byte_count": 0,
            "body_in_receipt": False,
        }

    monkeypatch.setattr(capsule_module, "_run_public_witness", passing_public_witness)

    result = run_batch7_station_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch7_station_runtime_capsule",
        command="pytest",
    )
    by_engine = {row["engine_id"]: row for row in result["exercise"]["engines"]}

    assert result["status"] == "pass"
    assert (
        by_engine["agent_live_instrument_view_model"]["original_witness"][
            "witness_mode"
        ]
        == "public_safe_temp_ui_vitest"
    )
    assert by_engine["agent_live_instrument_view_model"]["original_witness"][
        "command_executed"
    ] is True
    assert observed["command"] == [
        "npm",
        "exec",
        "--",
        "vitest",
        "run",
        "src/components/world/__tests__/agentLiveInstrumentViewModel.test.ts",
        "src/stores/__tests__/useStation.liveUpdates.test.ts",
        "src/stores/__tests__/useStation.launcher.test.ts",
    ]


def test_batch7_station_runtime_bundle_blocks_when_vitest_witness_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def blocked_public_witness(
        command: list[str],
        *,
        cwd: Path,
        witness_mode: str,
        timeout: int = 45,
    ) -> dict[str, Any]:
        return {
            "status": "blocked",
            "returncode": 1,
            "witness_mode": witness_mode,
            "command_executed": True,
            "stdout_byte_count": 0,
            "stderr_byte_count": 120,
            "body_in_receipt": False,
        }

    monkeypatch.setattr(capsule_module, "_run_public_witness", blocked_public_witness)

    result = run_batch7_station_bundle(
        EXPORTED_BUNDLE,
        tmp_path / "receipts/runtime_shell/demo_project/organs/batch7_station_runtime_capsule",
        command="pytest",
    )
    by_engine = {row["engine_id"]: row for row in result["exercise"]["engines"]}

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["exercise"]["status"] == "blocked"
    assert "BATCH7_STATION_ENGINE_EXERCISE_BLOCKED" in result["error_codes"]
    assert by_engine["agent_live_instrument_view_model"]["status"] == "blocked"
    assert by_engine["station_store_resilience_fsm"]["status"] == "blocked"
    assert by_engine["agent_live_instrument_view_model"]["original_witness"][
        "command_executed"
    ] is True


def test_batch7_station_runtime_bundle_rejects_source_digest_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _public_tmp_bundle(tmp_path)
    monkeypatch.chdir(MICROCOSM_ROOT)

    clean = run_batch7_station_bundle(
        bundle,
        _public_tmp_receipts(tmp_path, "clean"),
        command="pytest",
    )
    assert clean["status"] == "pass"
    assert clean["source_module_manifest"]["status"] == "pass"

    copied_source = (
        bundle
        / "source_modules/system/server/ui/src/components/world/"
        "agentLiveInstrumentViewModel.ts"
    )
    copied_source.write_text(
        copied_source.read_text(encoding="utf-8")
        + "\n// mutated source-manifest digest rejection proof\n",
        encoding="utf-8",
    )

    result = run_batch7_station_bundle(
        bundle,
        _public_tmp_receipts(tmp_path, "mutated"),
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert "CROWN_JEWEL_SOURCE_BODY_COPY_MISMATCH" in result["error_codes"]


def test_batch7_station_runtime_rejects_mutated_real_boot_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _redirect_copied_source(
        monkeypatch,
        tmp_path,
        "tools/agent_trace_structurer/app.mjs",
        "window.__aiwBoot.script_started = true",
        "window.__aiwBoot.script_started = false",
    )

    result = run_batch7_station_bundle(
        EXPORTED_BUNDLE,
        _public_tmp_receipts(tmp_path, "mutated_boot_probe"),
        command="pytest",
    )
    by_engine = {row["engine_id"]: row for row in result["exercise"]["engines"]}

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["exercise"]["status"] == "blocked"
    assert "BATCH7_STATION_ENGINE_EXERCISE_BLOCKED" in result["error_codes"]
    assert by_engine["agent_trace_workbench_host_boot_probe"]["status"] == "blocked"
    assert (
        by_engine["agent_trace_workbench_host_boot_probe"][
            "boot_probe_before_static_import"
        ]
        is False
    )


def test_batch7_station_runtime_rejects_mutated_real_station_backoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _redirect_copied_source(
        monkeypatch,
        tmp_path,
        "system/server/ui/src/stores/useStation.ts",
        "[500, 1000, 2000, 4000, 4000]",
        "[500, 1000, 2000]",
    )

    result = run_batch7_station_bundle(
        EXPORTED_BUNDLE,
        _public_tmp_receipts(tmp_path, "mutated_station_backoff"),
        command="pytest",
    )
    by_engine = {row["engine_id"]: row for row in result["exercise"]["engines"]}

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["exercise"]["status"] == "blocked"
    assert "BATCH7_STATION_ENGINE_EXERCISE_BLOCKED" in result["error_codes"]
    assert by_engine["station_store_resilience_fsm"]["status"] == "blocked"
    assert by_engine["station_store_resilience_fsm"]["bounded_initial_backoff"] is False


def test_batch7_station_runtime_rejects_mutated_real_live_instrument_attention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _redirect_copied_source(
        monkeypatch,
        tmp_path,
        "system/server/ui/src/components/world/agentLiveInstrumentViewModel.ts",
        "attentionUnderfiring",
        "attentionSignalMuted",
        replace_all=True,
    )

    result = run_batch7_station_bundle(
        EXPORTED_BUNDLE,
        _public_tmp_receipts(tmp_path, "mutated_live_instrument_attention"),
        command="pytest",
    )
    by_engine = {row["engine_id"]: row for row in result["exercise"]["engines"]}

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["exercise"]["status"] == "blocked"
    assert "BATCH7_STATION_ENGINE_EXERCISE_BLOCKED" in result["error_codes"]
    assert by_engine["agent_live_instrument_view_model"]["status"] == "blocked"
    assert (
        by_engine["agent_live_instrument_view_model"]["attention_underfiring_explicit"]
        is False
    )
    assert by_engine["agent_live_instrument_view_model"]["original_witness"][
        "command_executed"
    ] is True


def test_batch7_station_runtime_rejects_mutated_real_live_instrument_unknown_proof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _redirect_copied_source(
        monkeypatch,
        tmp_path,
        "system/server/ui/src/components/world/agentLiveInstrumentViewModel.ts",
        "return 'unknown';",
        "return 'pass';",
        replace_all=True,
    )

    result = run_batch7_station_bundle(
        EXPORTED_BUNDLE,
        _public_tmp_receipts(tmp_path, "mutated_live_instrument_unknown_proof"),
        command="pytest",
    )
    by_engine = {row["engine_id"]: row for row in result["exercise"]["engines"]}

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "pass"
    assert result["exercise"]["status"] == "blocked"
    assert "BATCH7_STATION_ENGINE_EXERCISE_BLOCKED" in result["error_codes"]
    assert by_engine["agent_live_instrument_view_model"]["status"] == "blocked"
    assert (
        by_engine["agent_live_instrument_view_model"]["unknown_proof_not_collapsed"]
        is False
    )
    assert by_engine["agent_live_instrument_view_model"]["original_witness"][
        "command_executed"
    ] is True
    assert (
        by_engine["agent_live_instrument_view_model"]["original_witness"]["returncode"]
        != 0
    )


def test_batch7_station_runtime_source_modules_are_exact_macro_body_imports() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] >= 5

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


def test_batch7_station_runtime_card_omits_private_bodies(
    capsule_result: dict[str, Any],
) -> None:
    result = capsule_result
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["engine_count"] == len(EXPECTED_ENGINES)
    assert card["copied_macro_source_module_count"] >= 5
    assert card["semantic_negative_case_evaluator_used"] is True
    assert card["body_in_receipt"] is False
    serialized = json.dumps(result, sort_keys=True)
    for forbidden in (
        "/Users/",
        "src/ai_workflow",
        "stdout_body",
        "stderr_body",
        "provider_payload",
        "cookie",
        "browser_profile",
    ):
        assert forbidden not in serialized
    assert "matched_excerpt" not in _walk_keys(result)
    assert "source_body" not in _walk_keys(result)


def test_batch7_station_runtime_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["body_in_receipt"] is False


def test_batch7_common_negative_cases_ignore_declared_codes(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/batch7_station_runtime_capsule",
        public_root / "examples/batch7_station_runtime_capsule",
    )
    input_dir = public_root / "fixtures/first_wave/batch7_station_runtime_capsule/input"
    input_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURE_INPUT, input_dir)
    _write_negative_case_fixtures(input_dir)

    result = validate_negative_cases(
        input_dir,
        EXPECTED_NEGATIVE_CASES,
        negative_case_evaluator=evaluate_negative_case,
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert "DECLARED_BOGUS_NEGATIVE_CODE" not in result["error_codes"]
    assert all(
        row["semantic_evaluator_used"] is True
        for row in result["negative_case_semantics"]
    )


def test_batch7_common_negative_cases_move_with_runtime_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_negative_case_fixtures(tmp_path)
    monkeypatch.setattr(
        capsule_module,
        "_semantic_runtime_exercises",
        lambda _input_ref: _semantic_runtime_fixture(
            {
                "station_store_stampede": {
                    "status": "pass",
                    "engines": [
                        {
                            "engine_id": "station_store_resilience_fsm",
                            "status": "pass",
                            "operation_single_flight": True,
                        }
                    ],
                }
            }
        ),
    )

    result = validate_negative_cases(
        tmp_path,
        EXPECTED_NEGATIVE_CASES,
        negative_case_evaluator=evaluate_negative_case,
    )

    assert result["status"] == "blocked"
    assert "station_store_stampede" in result["missing_negative_cases"]
    assert "BATCH7_STATION_SINGLE_FLIGHT_REQUIRED" not in result["error_codes"]
    observed_errors = {row["error_code"] for row in result["findings"]}
    assert "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED" in observed_errors
    assert "CROWN_JEWEL_NEGATIVE_CASE_CODE_MISSING" in observed_errors
