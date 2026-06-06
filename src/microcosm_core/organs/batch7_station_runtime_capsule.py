from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
    validate_source_manifest,
)


ORGAN_ID = "batch7_station_runtime_capsule"
FIXTURE_ID = "first_wave.batch7_station_runtime_capsule"
VALIDATOR_ID = "validator.microcosm.organs.batch7_station_runtime_capsule"

RESULT_NAME = "batch7_station_runtime_capsule_result.json"
BOARD_NAME = "batch7_station_runtime_capsule_board.json"
VALIDATION_RECEIPT_NAME = "batch7_station_runtime_capsule_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_batch7_station_runtime_capsule_validation_result.json"
CARD_SCHEMA_VERSION = "batch7_station_runtime_capsule_command_card_v1"
BUNDLE_INPUT_MODE = "exported_batch7_station_runtime_capsule_bundle"
EXERCISE_MANIFEST_NAME = "batch7_station_exercise_manifest.json"

EXPECTED_ENGINES: tuple[str, ...] = (
    "agent_trace_workbench_host_boot_probe",
    "agent_live_instrument_view_model",
    "station_store_resilience_fsm",
)

EXPECTED_NEGATIVE_CASES = {
    "app_missing_boot_probe": ("BATCH7_STATION_BOOT_PROBE_REQUIRED",),
    "live_instrument_underfiring_attention": (
        "BATCH7_STATION_ATTENTION_UNDERFIRING_EXPLICIT",
    ),
    "live_instrument_unknown_proof": (
        "BATCH7_STATION_UNKNOWN_PROOF_NOT_COLLAPSED",
    ),
    "station_store_stampede": ("BATCH7_STATION_SINGLE_FLIGHT_REQUIRED",),
    "station_warming_no_retry": ("BATCH7_STATION_WARMING_RETRY_REQUIRED",),
}

NEGATIVE_CASE_CODES = {
    case_id: codes[0] for case_id, codes in EXPECTED_NEGATIVE_CASES.items()
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch7_station_runtime_capsule_not_release_or_ui_runtime_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "release_authorized": False,
    "publication_authorized": False,
    "provider_dispatch": False,
    "model_dispatch": False,
    "browser_or_wallet_access": False,
    "source_mutation_authorized": False,
    "operator_thread_authority": False,
    "semantic_truth_authority": False,
    "test_completeness_proof": False,
}

ANTI_CLAIM = (
    "Batch 7 station runtime imports public-safe source bodies for the agent "
    "trace workbench host, live agent instrument view model, and station store "
    "resilience loop. It is not a hosted UI, not browser or operator-thread "
    "authority, not provider access, not release approval, and not proof that "
    "all frontend states are covered."
)

SOURCE_REQUIRED_ANCHORS = {
    "tools/agent_trace_structurer/app.mjs": (
        "window.__aiwBoot.script_started = true",
        "let activeDropdown = null",
        "MISSION_AUTO_REFRESH_TICK_MS",
        "resourceFreshnessPayload",
    ),
    "system/server/ui/src/components/world/agentLiveInstrumentViewModel.ts": (
        "export function applyAnimationDelta",
        "function buildStreamHealth",
        "function buildProofAuthoritySummary",
        "function buildProviderHealth",
    ),
    "system/server/ui/src/stores/useStation.ts": (
        "export type LiveUpdateState",
        "const operationLaunchesInFlight",
        "function scheduleStationLauncherWarmingRetry",
        "function deriveLiveUpdateStatus",
    ),
    "system/server/ui/src/stores/__tests__/useStation.liveUpdates.test.ts": (
        "transitions paused, catching_up, live, and stale correctly",
        "does not stampede launcher requests",
    ),
    "system/server/ui/src/stores/__tests__/useStation.launcher.test.ts": (
        "detects backend warming diagnostics",
        "schedules a forced follow-up refresh",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 7 Station Runtime Capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(EXERCISE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "microcosm-substrate/examples/batch7_station_runtime_capsule/"
        "exported_batch7_station_runtime_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _repo_root(public_root: Path) -> Path:
    return public_root.parent


def _copied_source(
    public_root: Path,
    source_ref: str,
    *,
    input_path: Path | None = None,
) -> Path:
    if input_path is not None:
        local_source = input_path / "source_modules" / source_ref
        if local_source.is_file():
            return local_source
    return (
        public_root
        / "examples/batch7_station_runtime_capsule/"
        "exported_batch7_station_runtime_capsule_bundle/source_modules"
        / source_ref
    )


def _copy_public_bundle(public_root: Path, temp_public_root: Path) -> None:
    shutil.copytree(
        public_root / "examples/batch7_station_runtime_capsule",
        temp_public_root / "examples/batch7_station_runtime_capsule",
    )


def _replace_copied_source_token(
    public_root: Path,
    source_ref: str,
    old: str,
    new: str,
    *,
    replace_all: bool = False,
) -> bool:
    source_path = _copied_source(public_root, source_ref)
    text = source_path.read_text(encoding="utf-8")
    if old not in text:
        return False
    mutated = text.replace(old, new) if replace_all else text.replace(old, new, 1)
    source_path.write_text(mutated, encoding="utf-8")
    return True


def _run_public_witness(
    command: list[str],
    *,
    cwd: Path,
    witness_mode: str,
    timeout: int = 45,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH7_STATION_WITNESS_COMMAND_MISSING",
            "error_type": type(exc).__name__,
            "witness_mode": witness_mode,
            "witness_workspace_mode": "temp_public_safe_copied_ui_workspace",
            "command_executed": True,
            "body_in_receipt": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH7_STATION_WITNESS_TIMEOUT",
            "witness_mode": witness_mode,
            "witness_workspace_mode": "temp_public_safe_copied_ui_workspace",
            "command_executed": True,
            "body_in_receipt": False,
        }
    return {
        "status": "pass" if completed.returncode == 0 else "blocked",
        "returncode": completed.returncode,
        "witness_mode": witness_mode,
        "witness_workspace_mode": "temp_public_safe_copied_ui_workspace",
        "command_executed": True,
        "stdout_byte_count": len(completed.stdout.encode("utf-8")),
        "stderr_byte_count": len(completed.stderr.encode("utf-8")),
        "body_in_receipt": False,
    }


def _copy_public_safe_ui_workspace(
    public_root: Path,
    input_path: Path | None,
    temp_ui_root: Path,
) -> int:
    ui_root = _repo_root(public_root) / "system/server/ui"
    shutil.copytree(
        ui_root,
        temp_ui_root,
        ignore=shutil.ignore_patterns(
            "node_modules",
            "dist",
            "coverage",
            ".vite",
            ".turbo",
            ".cache",
            "*.tsbuildinfo",
        ),
    )
    node_modules = ui_root / "node_modules"
    if node_modules.exists():
        (temp_ui_root / "node_modules").symlink_to(node_modules, target_is_directory=True)

    copied_count = 0
    for source_ref in SOURCE_REQUIRED_ANCHORS:
        prefix = "system/server/ui/"
        if not source_ref.startswith(prefix):
            continue
        source = _copied_source(public_root, source_ref, input_path=input_path)
        target = temp_ui_root / source_ref[len(prefix) :]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied_count += 1
    return copied_count


def _ui_vitest_witness(
    public_root: Path,
    *,
    input_path: Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(public_root)
    ui_root = repo / "system/server/ui"
    if not (ui_root / "package.json").is_file():
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH7_STATION_UI_WORKSPACE_MISSING",
            "witness_mode": "public_safe_temp_ui_vitest",
            "command_executed": False,
            "macro_ui_workspace_present": False,
            "body_in_receipt": False,
        }
    command = [
        "npm",
        "exec",
        "--",
        "vitest",
        "run",
        "src/components/world/__tests__/agentLiveInstrumentViewModel.test.ts",
        "src/stores/__tests__/useStation.liveUpdates.test.ts",
        "src/stores/__tests__/useStation.launcher.test.ts",
    ]
    with tempfile.TemporaryDirectory(prefix="batch7_station_ui_vitest_") as tmp:
        temp_ui_root = Path(tmp) / "ui"
        copied_count = _copy_public_safe_ui_workspace(
            public_root,
            input_path,
            temp_ui_root,
        )
        result = _run_public_witness(
            command,
            cwd=temp_ui_root,
            witness_mode="public_safe_temp_ui_vitest",
            timeout=60,
        )
    result["macro_ui_workspace_present"] = True
    result["copied_ui_module_count"] = copied_count
    result["test_file_count"] = 3
    return result


def _app_host_exercise(
    public_root: Path,
    *,
    input_path: Path | None = None,
) -> dict[str, Any]:
    source = _copied_source(
        public_root,
        "tools/agent_trace_structurer/app.mjs",
        input_path=input_path,
    ).read_text(encoding="utf-8")
    first_import = source.find("import {")
    boot_probe = source.find("window.__aiwBoot.script_started = true")
    active_dropdown = source.find("let activeDropdown = null")
    freshness = source.find("function resourceFreshnessPayload")
    mission_refresh = all(
        token in source
        for token in (
            "MISSION_AUTO_REFRESH_TICK_MS",
            "MISSION_REFRESH_WATCHDOG_MS",
            "MISSION_AUTO_REFRESH_MIN_GAP_MS",
        )
    )
    boot_before_import = boot_probe >= 0 and first_import >= 0 and boot_probe < first_import
    dropdown_before_freshness = active_dropdown >= 0 and freshness >= 0 and active_dropdown < freshness
    return {
        "status": "pass" if boot_before_import and dropdown_before_freshness and mission_refresh else "blocked",
        "engine_id": "agent_trace_workbench_host_boot_probe",
        "boot_probe_before_static_import": boot_before_import,
        "active_dropdown_hoisted_before_refresh_logic": dropdown_before_freshness,
        "mission_refresh_timers_present": mission_refresh,
        "source_body_byte_count": len(source.encode("utf-8")),
        "claim_ceiling": "WKWebView host source body only; no browser session, operator thread, or native app authority.",
    }


def _live_instrument_exercise(
    public_root: Path,
    witness: Mapping[str, Any],
    *,
    input_path: Path | None = None,
) -> dict[str, Any]:
    source = _copied_source(
        public_root,
        "system/server/ui/src/components/world/agentLiveInstrumentViewModel.ts",
        input_path=input_path,
    ).read_text(encoding="utf-8")
    typed_status_buckets = all(
        f"return '{bucket}'" in source
        for bucket in ("pass", "fail", "running", "blocked", "observed", "unknown")
    )
    typed_scope_buckets = all(
        f"return '{bucket}'" in source
        for bucket in ("owned", "unowned", "generated", "unknown")
    )
    stream_health_guards = all(
        token in source
        for token in (
            "attentionUnderfiring",
            "backend_degraded_unspecified",
            "history_saturation_high",
            "delta_op_saturation_high",
        )
    )
    file_impact_grouping = all(
        token in source
        for token in (
            "buildFileImpactGroups",
            "operationCounts",
            "claimState === 'owned_by_other'",
        )
    )
    provider_missingness = "session_lacks_source_runtime_tag_in_ingestion" in source
    return {
        "status": "pass"
        if witness.get("status") == "pass"
        and typed_status_buckets
        and typed_scope_buckets
        and stream_health_guards
        and file_impact_grouping
        and provider_missingness
        else "blocked",
        "engine_id": "agent_live_instrument_view_model",
        "original_witness": {
            "kind": "vitest",
            "command": "npm exec -- vitest run agentLiveInstrumentViewModel and useStation station tests",
            **dict(witness),
        },
        "typed_status_bucket_count": 6,
        "typed_scope_bucket_count": 4,
        "attention_underfiring_explicit": "attentionUnderfiring" in source,
        "unknown_proof_not_collapsed": typed_status_buckets and typed_scope_buckets,
        "claim_ceiling": "frontend view-model projection over backend semantic-camera fields only.",
    }


def _station_store_exercise(
    public_root: Path,
    witness: Mapping[str, Any],
    *,
    input_path: Path | None = None,
) -> dict[str, Any]:
    source = _copied_source(
        public_root,
        "system/server/ui/src/stores/useStation.ts",
        input_path=input_path,
    ).read_text(encoding="utf-8")
    live_states = all(f"'{state}'" in source for state in ("live", "catching_up", "paused", "stale"))
    bounded_backoff = "[500, 1000, 2000, 4000, 4000]" in source
    warming_retry = all(
        token in source
        for token in (
            "scheduleStationLauncherWarmingRetry",
            "clearStationLauncherWarmingRetry",
            "STATION_LAUNCHER_WARMING_RETRY_MS",
        )
    )
    single_flight = all(
        token in source
        for token in (
            "operationLaunchesInFlight",
            "existingLaunch",
            "operationLaunchesInFlight.delete",
        )
    )
    stale_gate = "LIVE_UPDATE_STALE_MS" in source and "return now - state.lastSuccessfulRefreshAt <= LIVE_UPDATE_STALE_MS" in source
    return {
        "status": "pass"
        if witness.get("status") == "pass"
        and live_states
        and bounded_backoff
        and warming_retry
        and single_flight
        and stale_gate
        else "blocked",
        "engine_id": "station_store_resilience_fsm",
        "live_state_count": 4,
        "bounded_initial_backoff": bounded_backoff,
        "warming_retry_enforced": warming_retry,
        "operation_single_flight": single_flight,
        "stale_timer_gate_present": stale_gate,
        "claim_ceiling": "client-side resilience state machine only; no operation launch authority.",
    }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    exported_bundle_input = (input_path / "source_module_manifest.json").is_file() and (
        input_path / "source_modules"
    ).is_dir()
    source_input_path = input_path if exported_bundle_input else None
    witness = _ui_vitest_witness(public_root, input_path=source_input_path)
    exercises = [
        _app_host_exercise(public_root, input_path=source_input_path),
        _live_instrument_exercise(public_root, witness, input_path=source_input_path),
        _station_store_exercise(public_root, witness, input_path=source_input_path),
    ]
    for exercise in exercises:
        if exercise.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH7_STATION_ENGINE_EXERCISE_BLOCKED",
                    "A Batch-7 station runtime engine exercise did not pass.",
                    subject_id=str(exercise.get("engine_id")),
                    observed=exercise.get("status"),
                )
            )
    observed = {str(row.get("engine_id")) for row in exercises}
    missing = sorted(set(EXPECTED_ENGINES) - observed)
    if missing:
        findings.append(
            finding(
                "BATCH7_STATION_ENGINE_EXERCISE_MISSING",
                "A Batch-7 station runtime engine is missing from the exercise result.",
                observed=missing,
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_count": len(exercises),
        "engine_ids": sorted(observed),
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "engines": exercises,
        "error_codes": [],
        "body_in_receipt": False,
        "findings": findings,
    }


def _mutate_app_missing_boot_probe(public_root: Path) -> bool:
    return _replace_copied_source_token(
        public_root,
        "tools/agent_trace_structurer/app.mjs",
        "window.__aiwBoot.script_started = true",
        "window.__aiwBoot.script_started = false",
    )


def _mutate_live_instrument_underfiring_attention(public_root: Path) -> bool:
    return _replace_copied_source_token(
        public_root,
        "system/server/ui/src/components/world/agentLiveInstrumentViewModel.ts",
        "attentionUnderfiring",
        "attentionSignalMuted",
        replace_all=True,
    )


def _mutate_live_instrument_unknown_proof(public_root: Path) -> bool:
    return _replace_copied_source_token(
        public_root,
        "system/server/ui/src/components/world/agentLiveInstrumentViewModel.ts",
        "return 'unknown';",
        "return 'pass';",
        replace_all=True,
    )


def _mutate_station_store_stampede(public_root: Path) -> bool:
    return _replace_copied_source_token(
        public_root,
        "system/server/ui/src/stores/useStation.ts",
        "operationLaunchesInFlight",
        "operationLaunchesDetached",
        replace_all=True,
    )


def _mutate_station_warming_no_retry(public_root: Path) -> bool:
    return _replace_copied_source_token(
        public_root,
        "system/server/ui/src/stores/useStation.ts",
        "scheduleStationLauncherWarmingRetry",
        "scheduleStationLauncherNoRetry",
        replace_all=True,
    )


def _run_negative_perturbation(
    case_id: str,
    input_path: Path,
    public_root: Path,
) -> dict[str, Any]:
    mutators = {
        "app_missing_boot_probe": _mutate_app_missing_boot_probe,
        "live_instrument_underfiring_attention": _mutate_live_instrument_underfiring_attention,
        "live_instrument_unknown_proof": _mutate_live_instrument_unknown_proof,
        "station_store_stampede": _mutate_station_store_stampede,
        "station_warming_no_retry": _mutate_station_warming_no_retry,
    }
    with tempfile.TemporaryDirectory(prefix=f"batch7_station_negative_{case_id}_") as tmp:
        temp_public_root = Path(tmp) / "microcosm-substrate"
        _copy_public_bundle(public_root, temp_public_root)
        mutation_applied = mutators[case_id](temp_public_root)
        temp_input_path = input_path
        if (input_path / "source_module_manifest.json").is_file() and (
            input_path / "source_modules"
        ).is_dir():
            temp_input_path = (
                temp_public_root
                / "examples/batch7_station_runtime_capsule/"
                "exported_batch7_station_runtime_capsule_bundle"
            )
        exercise = _evaluate(
            temp_input_path,
            temp_public_root,
            {"module_count": len(SOURCE_REQUIRED_ANCHORS)},
        )
    return {
        "status": exercise.get("status"),
        "engines": exercise.get("engines", []),
        "findings": exercise.get("findings", []),
        "mutation_applied": mutation_applied,
        "body_in_receipt": False,
    }


@lru_cache(maxsize=8)
def _semantic_runtime_exercises(input_ref: str) -> dict[str, Any]:
    input_path = Path(input_ref)
    public_root = public_root_for_path(input_path)
    source_manifest = validate_source_manifest(input_path, SPEC, public_root=public_root)
    exercise = _evaluate(input_path, public_root, source_manifest)
    return {
        "source_manifest": {
            key: value
            for key, value in source_manifest.items()
            if key not in {"findings", "source_manifest_path"}
        },
        "exercise": exercise,
        "negative_exercises": {
            case_id: _run_negative_perturbation(case_id, input_path, public_root)
            for case_id in EXPECTED_NEGATIVE_CASES
        },
    }


def _engine_map(exercise: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    engines = exercise.get("engines") if isinstance(exercise.get("engines"), list) else []
    return {
        str(row.get("engine_id")): row
        for row in engines
        if isinstance(row, Mapping) and row.get("engine_id")
    }


def _negative_exercise(runtime: Mapping[str, Any], case_id: str) -> Mapping[str, Any]:
    cases = (
        runtime.get("negative_exercises")
        if isinstance(runtime.get("negative_exercises"), Mapping)
        else {}
    )
    case = cases.get(case_id)
    return case if isinstance(case, Mapping) else {}


def _observed_negative_case(case_id: str, runtime: Mapping[str, Any]) -> bool:
    exercise = _negative_exercise(runtime, case_id)
    if exercise.get("mutation_applied") is not True:
        return False
    engines = _engine_map(exercise)
    app = engines.get("agent_trace_workbench_host_boot_probe", {})
    live = engines.get("agent_live_instrument_view_model", {})
    store = engines.get("station_store_resilience_fsm", {})
    if case_id == "app_missing_boot_probe":
        return (
            exercise.get("status") == "blocked"
            and app.get("status") == "blocked"
            and app.get("boot_probe_before_static_import") is False
        )
    if case_id == "live_instrument_underfiring_attention":
        return (
            exercise.get("status") == "blocked"
            and live.get("status") == "blocked"
            and live.get("attention_underfiring_explicit") is False
        )
    if case_id == "live_instrument_unknown_proof":
        return (
            exercise.get("status") == "blocked"
            and live.get("status") == "blocked"
            and live.get("unknown_proof_not_collapsed") is False
        )
    if case_id == "station_store_stampede":
        return (
            exercise.get("status") == "blocked"
            and store.get("status") == "blocked"
            and store.get("operation_single_flight") is False
        )
    if case_id == "station_warming_no_retry":
        return (
            exercise.get("status") == "blocked"
            and store.get("status") == "blocked"
            and store.get("warming_retry_enforced") is False
        )
    return False


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    expected_code = NEGATIVE_CASE_CODES.get(case_id, "")
    observed = _observed_negative_case(
        case_id,
        _semantic_runtime_exercises(str(Path(input_dir))),
    )
    return {
        "status": "blocked" if observed else "pass",
        "error_codes": [expected_code] if observed and expected_code else [],
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch7_station_bundle(
    bundle_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        bundle_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    card["engine_count"] = exercise.get("engine_count")
    card["copied_macro_source_module_count"] = exercise.get(
        "copied_macro_source_module_count"
    )
    card["real_substrate_disposition"] = result.get("real_substrate_disposition")
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="microcosm batch7-station-runtime")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-batch7-station-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    runner = run_batch7_station_bundle if args.action == "run-batch7-station-bundle" else run
    result = runner(
        args.input,
        args.out,
        acceptance_out=args.acceptance_out,
        command=f"{ORGAN_ID} {args.action}",
    )
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
