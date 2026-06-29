"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.batch7_demo_take_console_capsule` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, BUNDLE_INPUT_MODE, EXERCISE_MANIFEST_NAME, EXPECTED_ENGINES, EXPECTED_NEGATIVE_CASES, NEGATIVE_CASE_CODES, AUTHORITY_CEILING, ANTI_CLAIM, SOURCE_REQUIRED_ANCHORS, SPEC, evaluate_negative_case, run, run_batch7_demo_take_bundle, result_card, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs, declared subprocess results, environment variables.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, subprocess side effects requested by the caller and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.organs._crown_jewel_common
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
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
)


ORGAN_ID = "batch7_demo_take_console_capsule"
FIXTURE_ID = "first_wave.batch7_demo_take_console_capsule"
VALIDATOR_ID = "validator.microcosm.organs.batch7_demo_take_console_capsule"

RESULT_NAME = "batch7_demo_take_console_capsule_result.json"
BOARD_NAME = "batch7_demo_take_console_capsule_board.json"
VALIDATION_RECEIPT_NAME = "batch7_demo_take_console_capsule_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_batch7_demo_take_console_capsule_validation_result.json"
CARD_SCHEMA_VERSION = "batch7_demo_take_console_capsule_command_card_v1"
BUNDLE_INPUT_MODE = "exported_batch7_demo_take_console_capsule_bundle"
EXERCISE_MANIFEST_NAME = "batch7_demo_take_console_exercise_manifest.json"

EXPECTED_ENGINES: tuple[str, ...] = (
    "demo_take_swiftpm_build_witness",
    "recording_state_control_model",
    "capture_helper_bridge_contract",
    "recorder_store_capture_fsm",
    "hotkey_audio_meter_contract",
    "transcribe_payload_builder",
)

EXPECTED_NEGATIVE_CASES = {
    "missing_helper_bridge": ("BATCH7_DEMO_TAKE_HELPER_BRIDGE_REQUIRED",),
    "start_without_screen": ("BATCH7_DEMO_TAKE_START_SCREEN_GATE_REQUIRED",),
    "hotkey_wrong_modifier": ("BATCH7_DEMO_TAKE_HOTKEY_MODIFIERS_REQUIRED",),
    "audio_meter_unclamped": ("BATCH7_DEMO_TAKE_AUDIO_LEVEL_CLAMP_REQUIRED",),
    "transcribe_missing_audio": ("BATCH7_DEMO_TAKE_TRANSCRIBE_AUDIO_REQUIRED",),
    "missing_swift_build_witness": ("BATCH7_DEMO_TAKE_SWIFT_BUILD_WITNESS_REQUIRED",),
}

NEGATIVE_CASE_CODES = {
    case_id: codes[0] for case_id, codes in EXPECTED_NEGATIVE_CASES.items()
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch7_demo_take_console_capsule_not_app_launch_or_recording_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "release_authorized": False,
    "publication_authorized": False,
    "provider_dispatch": False,
    "model_dispatch": False,
    "native_app_launch_authorized": False,
    "recording_session_export_authorized": False,
    "screen_capture_authorized": False,
    "microphone_capture_authorized": False,
    "source_mutation_authorized": False,
    "operator_thread_authority": False,
    "test_completeness_proof": False,
}

ANTI_CLAIM = (
    "Batch 7 Demo Take Console imports public-safe Swift source bodies for the "
    "local capture console, helper bridge, hotkey/audio monitor, host "
    "environment, and transcribe payload builder, plus a SwiftPM build witness. "
    "It is not an app launch, not screen or microphone capture authority, not "
    "operator recording-session export, not model dispatch, not release "
    "approval, and not proof that every UI path is covered."
)

SOURCE_REQUIRED_ANCHORS = {
    "apps/demo-take-console/Package.swift": (
        '.executable(name: "DemoTakeConsoleApp"',
        '.executable(name: "demo-take-transcribe"',
        "WhisperKit",
    ),
    "apps/demo-take-console/Sources/DemoTakeConsoleApp/Models.swift": (
        "enum RecordingState",
        'case reviewReady = "review_ready"',
        "struct RunMapScheduleState",
        'wallTSeconds = "wall_t_seconds"',
    ),
    "apps/demo-take-console/Sources/DemoTakeConsoleApp/CaptureHelperClient.swift": (
        "enum CaptureHelperClient",
        "JSONSerialization.data(withJSONObject: config, options: [.sortedKeys])",
        "private static func repoPythonURL()",
        "private static func helperScriptURL()",
    ),
    "apps/demo-take-console/Sources/DemoTakeConsoleApp/RecorderStore.swift": (
        "final class RecorderStore",
        "var startBlockers: [String]",
        "func startRecording() async",
        "func togglePause()",
        "func stopRecording() async",
    ),
    "apps/demo-take-console/Sources/DemoTakeConsoleApp/HotkeyMonitor.swift": (
        "static let defaultModifiers: NSEvent.ModifierFlags = [.control, .option, .command]",
        "NSEvent.addGlobalMonitorForEvents",
        "NSEvent.addLocalMonitorForEvents",
        "return consumed ? nil : event",
    ),
    "apps/demo-take-console/Sources/DemoTakeConsoleApp/AudioLevelMonitor.swift": (
        "final class AudioLevelMonitor",
        "kAudioFormatFlagIsFloat",
        "Int16.max",
        "return min(max(rms * 8, 0), 1)",
    ),
    "apps/demo-take-console/Sources/DemoTakeConsoleApp/HostEnvironment.swift": (
        "AIWorkflowRepoRoot",
        "static var outputRoot: URL",
        "static func findTranscribeBinary()",
        "static func displayMetadata(forFFmpegScreenIndex index: Int)",
    ),
    "apps/demo-take-console/Sources/DemoTakeTranscribe/main.swift": (
        "import WhisperKit",
        "wordTimestamps: true",
        '"schema": "demo_take_transcript_v0"',
        "RuntimeError.audioNotFound",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 7 Demo Take Console Capsule",
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
        "microcosm-substrate/examples/batch7_demo_take_console_capsule/"
        "exported_batch7_demo_take_console_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _repo_root(public_root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_repo_root` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_root.parent


def _copied_source(public_root: Path, source_ref: str) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_copied_source` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (
        public_root
        / "examples/batch7_demo_take_console_capsule/"
        "exported_batch7_demo_take_console_capsule_bundle/source_modules"
        / source_ref
    )


def _read(public_root: Path, source_ref: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_read` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    return _copied_source(public_root, source_ref).read_text(encoding="utf-8")


def _copy_public_bundle(public_root: Path, temp_public_root: Path) -> None:
    """
    [ACTION]
    - Teleology: Implements `_copy_public_bundle` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    shutil.copytree(
        public_root / "examples/batch7_demo_take_console_capsule",
        temp_public_root / "examples/batch7_demo_take_console_capsule",
    )


def _replace_copied_source_token(
    public_root: Path,
    source_ref: str,
    old: str,
    new: str,
) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_replace_copied_source_token` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values, declared filesystem outputs.
    """
    source_path = _copied_source(public_root, source_ref)
    text = source_path.read_text(encoding="utf-8")
    if old not in text:
        return False
    source_path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def _run_public_witness(
    command: list[str],
    *,
    cwd: Path,
    timeout: int = 240,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_run_public_witness` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
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
            "error_code": "BATCH7_DEMO_TAKE_WITNESS_COMMAND_MISSING",
            "error_type": type(exc).__name__,
            "body_in_receipt": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH7_DEMO_TAKE_WITNESS_TIMEOUT",
            "body_in_receipt": False,
        }
    combined = f"{completed.stdout}\n{completed.stderr}"
    return {
        "status": "pass" if completed.returncode == 0 else "blocked",
        "returncode": completed.returncode,
        "stdout_byte_count": len(completed.stdout.encode("utf-8")),
        "stderr_byte_count": len(completed.stderr.encode("utf-8")),
        "observed_build_complete_marker": "Build complete!" in combined,
        "body_in_receipt": False,
    }


def _mutated_source_negative(
    public_root: Path,
    *,
    case_id: str,
    source_ref: str,
    old: str,
    new: str,
    engine: Any,
    observed_flag: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_mutated_source_negative` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_{case_id}_") as tmp:
        temp_public_root = Path(tmp) / "microcosm-substrate"
        _copy_public_bundle(public_root, temp_public_root)
        mutation_applied = _replace_copied_source_token(
            temp_public_root,
            source_ref,
            old,
            new,
        )
        result = engine(temp_public_root)
    observed = (
        mutation_applied
        and result.get("status") == "blocked"
        and result.get(observed_flag) is False
    )
    return {
        "status": "blocked" if observed else "pass",
        "case_id": case_id,
        "engine_id": result.get("engine_id"),
        "mutation_applied": mutation_applied,
        observed_flag: result.get(observed_flag),
        "body_in_receipt": False,
    }


def _missing_helper_bridge_negative(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_missing_helper_bridge_negative` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _mutated_source_negative(
        public_root,
        case_id="missing_helper_bridge",
        source_ref=(
            "apps/demo-take-console/Sources/DemoTakeConsoleApp/"
            "CaptureHelperClient.swift"
        ),
        old='appendingPathComponent("demo_take_capture.py")',
        new='appendingPathComponent("demo_take_capture_missing.py")',
        engine=_capture_helper_bridge_contract,
        observed_flag="helper_script_bound_to_repo",
    )


def _start_without_screen_negative(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_start_without_screen_negative` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _mutated_source_negative(
        public_root,
        case_id="start_without_screen",
        source_ref="apps/demo-take-console/Sources/DemoTakeConsoleApp/RecorderStore.swift",
        old='blockers.append("Select at least one display")',
        new='statusMessages.append("Screen selection optional")',
        engine=_recorder_store_capture_fsm,
        observed_flag="start_gate_requires_screen_and_disk",
    )


def _hotkey_wrong_modifier_negative(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_hotkey_wrong_modifier_negative` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _mutated_source_negative(
        public_root,
        case_id="hotkey_wrong_modifier",
        source_ref="apps/demo-take-console/Sources/DemoTakeConsoleApp/HotkeyMonitor.swift",
        old=(
            "static let defaultModifiers: NSEvent.ModifierFlags = "
            "[.control, .option, .command]"
        ),
        new="static let defaultModifiers: NSEvent.ModifierFlags = [.control, .command]",
        engine=_hotkey_audio_meter_contract,
        observed_flag="hotkey_requires_control_option_command_m",
    )


def _audio_meter_unclamped_negative(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_audio_meter_unclamped_negative` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _mutated_source_negative(
        public_root,
        case_id="audio_meter_unclamped",
        source_ref="apps/demo-take-console/Sources/DemoTakeConsoleApp/AudioLevelMonitor.swift",
        old="return min(max(rms * 8, 0), 1)",
        new="return rms * 8",
        engine=_hotkey_audio_meter_contract,
        observed_flag="audio_meter_permission_device_and_clamp_present",
    )


def _transcribe_missing_audio_negative(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_transcribe_missing_audio_negative` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _mutated_source_negative(
        public_root,
        case_id="transcribe_missing_audio",
        source_ref="apps/demo-take-console/Sources/DemoTakeTranscribe/main.swift",
        old="RuntimeError.audioNotFound(absAudio)",
        new='RuntimeError.transcriptionFailed("missing audio")',
        engine=_transcribe_payload_builder,
        observed_flag="missing_audio_guard_present",
    )


def _missing_swift_build_witness_negative() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_missing_swift_build_witness_negative` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_missing_swift_build_") as tmp:
        witness = _run_public_witness(
            ["swift", "build", "--product", "DemoTakeConsoleApp"],
            cwd=Path(tmp) / "apps/demo-take-console",
            timeout=30,
        )
    observed = witness.get("status") != "pass"
    return {
        "status": "blocked" if observed else "pass",
        "case_id": "missing_swift_build_witness",
        "witness_status": witness.get("status"),
        "witness_error_code": witness.get("error_code"),
        "swift_build_witness_required": observed,
        "body_in_receipt": False,
    }


@lru_cache(maxsize=16)
def _semantic_runtime_exercises(input_ref: str) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_semantic_runtime_exercises` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = public_root_for_path(Path(input_ref))
    return {
        "negative_exercises": {
            "missing_helper_bridge": _missing_helper_bridge_negative(public_root),
            "start_without_screen": _start_without_screen_negative(public_root),
            "hotkey_wrong_modifier": _hotkey_wrong_modifier_negative(public_root),
            "audio_meter_unclamped": _audio_meter_unclamped_negative(public_root),
            "transcribe_missing_audio": _transcribe_missing_audio_negative(public_root),
            "missing_swift_build_witness": _missing_swift_build_witness_negative(),
        },
        "body_in_receipt": False,
    }


def _negative_exercise(runtime: Mapping[str, Any], case_id: str) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_negative_exercise` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    cases = (
        runtime.get("negative_exercises")
        if isinstance(runtime.get("negative_exercises"), Mapping)
        else {}
    )
    case = cases.get(case_id)
    return case if isinstance(case, Mapping) else {}


def _observed_negative_case(case_id: str, runtime: Mapping[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_observed_negative_case` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    exercise = _negative_exercise(runtime, case_id)
    if exercise.get("status") != "blocked" or exercise.get("mutation_applied") is False:
        return case_id == "missing_swift_build_witness" and exercise.get(
            "swift_build_witness_required"
        ) is True
    if case_id == "missing_helper_bridge":
        return exercise.get("helper_script_bound_to_repo") is False
    if case_id == "start_without_screen":
        return exercise.get("start_gate_requires_screen_and_disk") is False
    if case_id == "hotkey_wrong_modifier":
        return exercise.get("hotkey_requires_control_option_command_m") is False
    if case_id == "audio_meter_unclamped":
        return exercise.get("audio_meter_permission_device_and_clamp_present") is False
    if case_id == "transcribe_missing_audio":
        return exercise.get("missing_audio_guard_present") is False
    if case_id == "missing_swift_build_witness":
        return exercise.get("swift_build_witness_required") is True
    return False


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_negative_case` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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


@lru_cache(maxsize=4)
def _cached_swiftpm_build_witness(repo_root: str) -> tuple[tuple[str, Any], ...]:
    """
    [ACTION]
    - Teleology: Implements `_cached_swiftpm_build_witness` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    witness = _run_public_witness(
        ["swift", "build", "--product", "DemoTakeConsoleApp"],
        cwd=Path(repo_root) / "apps/demo-take-console",
        timeout=240,
    )
    return tuple(sorted(witness.items()))


def _swiftpm_build_witness(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_swiftpm_build_witness` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    witness = dict(_cached_swiftpm_build_witness(str(_repo_root(public_root))))
    return {
        "status": witness["status"],
        "engine_id": "demo_take_swiftpm_build_witness",
        "command": "swift build --product DemoTakeConsoleApp",
        "original_witness": witness,
        "claim_ceiling": "SwiftPM build of the app target only; no app launch or capture permissions.",
    }


def _recording_state_control_model(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_recording_state_control_model` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    models = _read(public_root, "apps/demo-take-console/Sources/DemoTakeConsoleApp/Models.swift")
    expected_states = (
        "case idle",
        "case setupNeeded",
        "case ready",
        "case countingDown",
        "case recording",
        "case paused",
        "case stopping",
        "case reviewReady",
        "case postprocessing",
        "case packageReady",
        "case packageFailed",
    )
    state_cases_present = all(token in models for token in expected_states)
    marker_time_keys = all(
        token in models
        for token in (
            'wallTSeconds = "wall_t_seconds"',
            'videoTSeconds = "video_t_seconds"',
            'createdAt = "created_at"',
        )
    )
    schedule_public_boundaries = all(
        token in models
        for token in (
            'publicClaimBoundary = "public_claim_boundary"',
            'recordingTreatment = "recording_treatment"',
            "currentFlashSay",
            "operatorCue",
        )
    )
    return {
        "status": "pass" if state_cases_present and marker_time_keys and schedule_public_boundaries else "blocked",
        "engine_id": "recording_state_control_model",
        "state_cases_present": state_cases_present,
        "recording_state_count": len(expected_states),
        "marker_uses_wall_and_video_time": marker_time_keys,
        "run_map_public_boundaries_present": schedule_public_boundaries,
        "claim_ceiling": "Typed capture/review state model only; not a live recording session.",
    }


def _capture_helper_bridge_contract(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_capture_helper_bridge_contract` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    bridge = _read(
        public_root,
        "apps/demo-take-console/Sources/DemoTakeConsoleApp/CaptureHelperClient.swift",
    )
    host = _read(public_root, "apps/demo-take-console/Sources/DemoTakeConsoleApp/HostEnvironment.swift")
    commands = (
        '"devices"',
        '"start"',
        '"pause"',
        '"resume"',
        '"finalize"',
        '"postprocess"',
        '"test-microphone"',
        '"mark"',
        '"import-video"',
        '"export-video"',
        '"schedule-state"',
    )
    helper_commands_present = all(token in bridge for token in commands)
    bridge_uses_sorted_config = "options: [.sortedKeys]" in bridge
    repo_python_fallback = (
        "FileManager.default.isExecutableFile(atPath: repoPython.path)" in bridge
        and 'URL(fileURLWithPath: "/usr/bin/python3")' in bridge
    )
    helper_script_bound_to_repo = all(
        token in bridge
        for token in (
            'appendingPathComponent("apps", isDirectory: true)',
            'appendingPathComponent("demo-take-console", isDirectory: true)',
            'appendingPathComponent("demo_take_capture.py")',
        )
    )
    host_output_bound = all(
        token in host
        for token in (
            "AIWorkflowRepoRoot",
            "state",
            "dissemination",
            "demo_takes",
        )
    )
    return {
        "status": "pass"
        if helper_commands_present
        and bridge_uses_sorted_config
        and repo_python_fallback
        and helper_script_bound_to_repo
        and host_output_bound
        else "blocked",
        "engine_id": "capture_helper_bridge_contract",
        "helper_commands_present": helper_commands_present,
        "helper_command_count": len(commands),
        "bridge_uses_sorted_config_json": bridge_uses_sorted_config,
        "repo_python_fallback_present": repo_python_fallback,
        "helper_script_bound_to_repo": helper_script_bound_to_repo,
        "host_output_bound_to_demo_takes": host_output_bound,
        "claim_ceiling": "Bridge argument/schema contract only; does not invoke helper during this exercise.",
    }


def _recorder_store_capture_fsm(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_recorder_store_capture_fsm` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    store = _read(public_root, "apps/demo-take-console/Sources/DemoTakeConsoleApp/RecorderStore.swift")
    start_gate = all(
        token in store
        for token in (
            "state = startBlockers.isEmpty ? .ready : .setupNeeded",
            "return startBlockers.isEmpty",
            'blockers.append("Select at least one display")',
            "minimumStartDiskBytes",
        )
    )
    start_path = all(
        token in store
        for token in (
            "await refreshPreflight()",
            "state = .countingDown",
            "CaptureHelperClient.start(",
            "state = .recording",
            "recordingStartedAt = Date()",
        )
    )
    pause_resume_path = all(
        token in store
        for token in (
            "CaptureHelperClient.pause(takeRoot: activeTakeURL)",
            "state = .paused",
            "CaptureHelperClient.resume(takeRoot: activeTakeURL)",
            "state = .recording",
        )
    )
    stop_review_path = all(
        token in store
        for token in (
            "CaptureHelperClient.finalize(takeRoot: stoppedTakeURL)",
            "loadPlaybackAsset(from: stoppedTakeURL)",
            "state = hasReviewVideo ? .reviewReady : .packageFailed",
            'appendStatus("Capture finalized for \\(stoppedTakeID).',
        )
    )
    screen_prompt_guard = (
        "Snapshot preview disabled; Start records this display through FFmpeg."
        in store
    )
    return {
        "status": "pass"
        if start_gate and start_path and pause_resume_path and stop_review_path and screen_prompt_guard
        else "blocked",
        "engine_id": "recorder_store_capture_fsm",
        "start_gate_requires_screen_and_disk": start_gate,
        "start_path_transitions_to_recording": start_path,
        "pause_resume_path_present": pause_resume_path,
        "stop_path_moves_to_review": stop_review_path,
        "screen_prompt_guard_present": screen_prompt_guard,
        "claim_ceiling": "RecorderStore state-machine source contract only; no capture process is started.",
    }


def _hotkey_audio_meter_contract(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_hotkey_audio_meter_contract` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    hotkey = _read(
        public_root,
        "apps/demo-take-console/Sources/DemoTakeConsoleApp/HotkeyMonitor.swift",
    )
    audio = _read(
        public_root,
        "apps/demo-take-console/Sources/DemoTakeConsoleApp/AudioLevelMonitor.swift",
    )
    hotkey_guard = all(
        token in hotkey
        for token in (
            "static let defaultKey: UInt16 = 46",
            "static let defaultModifiers: NSEvent.ModifierFlags = [.control, .option, .command]",
            "event.modifierFlags.intersection(.deviceIndependentFlagsMask)",
            "guard event.keyCode == HotkeyMonitor.defaultKey else { return false }",
            "return consumed ? nil : event",
        )
    )
    audio_gate = all(
        token in audio
        for token in (
            "AVCaptureDevice.authorizationStatus(for: .audio) == .authorized",
            "selectAudioDevice(uniqueID: preferredDeviceUniqueID, name: preferredDeviceName)",
            "kAudioFormatFlagIsFloat",
            "Int16.max",
            "return min(max(rms * 8, 0), 1)",
        )
    )
    return {
        "status": "pass" if hotkey_guard and audio_gate else "blocked",
        "engine_id": "hotkey_audio_meter_contract",
        "hotkey_requires_control_option_command_m": hotkey_guard,
        "audio_meter_permission_device_and_clamp_present": audio_gate,
        "claim_ceiling": "Static hotkey/audio-meter contract only; no global monitor or audio session is started.",
    }


def _transcribe_payload_builder(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_transcribe_payload_builder` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    transcribe = _read(public_root, "apps/demo-take-console/Sources/DemoTakeTranscribe/main.swift")
    decode_config = all(
        token in transcribe
        for token in (
            "WhisperKitConfig(model: options.model, verbose: false)",
            "DecodingOptions(",
            "wordTimestamps: true",
            "language: options.language",
            'options.chunking == "vad" ? .vad : nil',
        )
    )
    payload_schema = all(
        token in transcribe
        for token in (
            '"schema": "demo_take_transcript_v0"',
            '"segments": segmentObjects',
            '"words": wordObjects',
            '"segment_count": segmentObjects.count',
            '"word_count": wordObjects.count',
        )
    )
    srt_output = "static func buildSRT(results: [TranscriptionResult]) -> String" in transcribe
    missing_audio_guard = all(
        token in transcribe
        for token in (
            "guard FileManager.default.fileExists(atPath: absAudio) else",
            "RuntimeError.audioNotFound(absAudio)",
            'throw RuntimeError.missingFlag("--audio")',
            'throw RuntimeError.missingFlag("--output-json")',
        )
    )
    return {
        "status": "pass" if decode_config and payload_schema and srt_output and missing_audio_guard else "blocked",
        "engine_id": "transcribe_payload_builder",
        "whisper_decode_config_present": decode_config,
        "public_transcript_payload_schema_present": payload_schema,
        "srt_builder_present": srt_output,
        "missing_audio_guard_present": missing_audio_guard,
        "claim_ceiling": "Transcription payload builder source contract only; does not run WhisperKit or a model.",
    }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_evaluate` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    engines = [
        _swiftpm_build_witness(public_root),
        _recording_state_control_model(public_root),
        _capture_helper_bridge_contract(public_root),
        _recorder_store_capture_fsm(public_root),
        _hotkey_audio_meter_contract(public_root),
        _transcribe_payload_builder(public_root),
    ]
    findings: list[dict[str, Any]] = []
    for engine in engines:
        if engine.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH7_DEMO_TAKE_ENGINE_BLOCKED",
                    "Demo Take Console engine exercise did not pass.",
                    subject_id=str(engine.get("engine_id")),
                    observed=engine.get("status"),
                )
            )
    if source_manifest.get("module_count", 0) < len(SOURCE_REQUIRED_ANCHORS):
        findings.append(
            finding(
                "BATCH7_DEMO_TAKE_SOURCE_MODULE_COUNT_LOW",
                "Demo Take Console capsule must copy every required source body.",
                expected=len(SOURCE_REQUIRED_ANCHORS),
                observed=source_manifest.get("module_count"),
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "input_manifest_schema": input_path.joinpath(EXERCISE_MANIFEST_NAME).name,
        "engine_count": len(engines),
        "engine_ids": [str(engine.get("engine_id")) for engine in engines],
        "engines": engines,
        "copied_macro_source_module_count": source_manifest.get("module_count"),
        "error_codes": [
            str(engine["original_witness"].get("error_code"))
            for engine in engines
            if isinstance(engine.get("original_witness"), Mapping)
            and engine["original_witness"].get("error_code")
        ],
        "findings": findings,
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch7_demo_take_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_batch7_demo_take_bundle` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    card["engine_count"] = exercise.get("engine_count")
    card["engine_ids"] = exercise.get("engine_ids", [])
    return card


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.batch7_demo_take_console_capsule` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "validate-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    result = run_crown_jewel_organ(
        SPEC,
        args.input,
        args.out,
        command=f"{ORGAN_ID} {args.action}",
        acceptance_out=args.acceptance_out,
        input_mode=BUNDLE_INPUT_MODE if args.action == "validate-bundle" else "fixture_input",
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )
    print(json.dumps(result_card(result) if args.card else result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
