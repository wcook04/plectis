from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import wave
from pathlib import Path
from typing import Any, Mapping, Sequence

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    load_json_object,
    run_crown_jewel_organ,
)


ORGAN_ID = "batch8_audio_level_rms_port"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"
PROBE_MANIFEST_NAME = f"{ORGAN_ID}_probe_manifest.json"

SWIFT_SOURCE_REF = "apps/demo-take-console/Sources/DemoTakeConsoleApp/AudioLevelMonitor.swift"

EXPECTED_CASES: tuple[str, ...] = (
    "float32_reference_buffer",
    "int16_reference_buffer",
    "clamp_over_one_buffer",
)

EXPECTED_NEGATIVE_CASES = {
    "audio_level_empty_buffer_zero": ("BATCH8_AUDIO_LEVEL_EMPTY_BUFFER_ZERO",),
    "audio_level_unknown_format_refused": ("BATCH8_AUDIO_LEVEL_UNKNOWN_FORMAT_REFUSED",),
    "audio_level_clamps_over_one": ("BATCH8_AUDIO_LEVEL_CLAMP_REQUIRED",),
}

BYTE_REFERENCE_CASES_KEY = "byte_reference_cases"

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch8_audio_level_rms_python_port_not_audio_session_or_capture_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "python_port": True,
    "microphone_permission_required": False,
    "audio_session_started": False,
    "device_capture_authorized": False,
    "provider_dispatch": False,
    "repo_mutation_authorized": False,
    "source_mutation_authorized": False,
    "publication_authorized": False,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Batch 8 audio-level RMS port validates the pure normalizedLevel math from "
    "AudioLevelMonitor.swift over public synthetic sample arrays. It is not a "
    "macOS audio-session witness, not microphone permission authority, not "
    "device capture, not UI readiness, not repository mutation authority, not "
    "publication authority, and not release approval."
)

SOURCE_REQUIRED_ANCHORS = {
    SWIFT_SOURCE_REF: (
        "private static func normalizedLevel(from sampleBuffer: CMSampleBuffer) -> Float",
        "kAudioFormatFlagIsFloat",
        "Int16.max",
        "return min(max(rms * 8, 0), 1)",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 8 Audio Level RMS Port",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(PROBE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def normalized_level(samples: Sequence[float | int], sample_format: str) -> float:
    """Python port of AudioLevelMonitor.normalizedLevel's pure RMS scaling."""
    if sample_format not in {"float32", "int16"}:
        raise ValueError(f"unsupported audio sample format: {sample_format}")
    if not samples:
        return 0.0

    total = 0.0
    count = 0
    if sample_format == "float32":
        for sample in samples:
            value = float(sample)
            total += value * value
            count += 1
    else:
        for sample in samples:
            value = float(int(sample)) / 32767.0
            total += value * value
            count += 1

    if count == 0:
        return 0.0
    rms = math.sqrt(total / count)
    return min(max(rms * 8.0, 0.0), 1.0)


def _case_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("cases")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _byte_case_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get(BYTE_REFERENCE_CASES_KEY)
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _decode_int16_wav(path: Path) -> tuple[list[int], dict[str, Any]]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        frame_count = handle.getnframes()
        compression = handle.getcomptype()
        frame_bytes = handle.readframes(frame_count)
    if channels != 1 or sample_width != 2 or compression != "NONE":
        raise ValueError(
            "only mono uncompressed 16-bit PCM WAV byte cases are supported"
        )
    expected_byte_count = frame_count * channels * sample_width
    if len(frame_bytes) != expected_byte_count:
        raise ValueError("WAV frame payload length does not match header metadata")
    samples = list(struct.unpack(f"<{frame_count * channels}h", frame_bytes))
    return samples, {
        "container": "wav",
        "sample_format": "int16",
        "channels": channels,
        "sample_width_bytes": sample_width,
        "frame_count": frame_count,
        "decoded_sample_count": len(samples),
        "byte_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _evaluate_reference_cases(probe: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    case_results: list[dict[str, Any]] = []
    observed_ids: list[str] = []
    for row in _case_rows(probe):
        case_id = str(row.get("case_id") or "")
        sample_format = str(row.get("sample_format") or "")
        samples = row.get("samples")
        expected_level = row.get("expected_level")
        tolerance_raw = row.get("tolerance", 1e-6)
        if tolerance_raw is None:
            tolerance_raw = 1e-6
        if (
            not isinstance(samples, list)
            or not _is_finite_number(expected_level)
            or not _is_finite_number(tolerance_raw)
            or float(tolerance_raw) < 0
        ):
            findings.append(
                finding(
                    "BATCH8_AUDIO_LEVEL_CASE_INVALID",
                    "Audio RMS probe cases require samples, finite numeric expected_level, and non-negative finite tolerance.",
                    case_id=case_id,
                )
            )
            continue
        tolerance = float(tolerance_raw)
        try:
            observed = normalized_level(samples, sample_format)
        except Exception as exc:
            findings.append(
                finding(
                    "BATCH8_AUDIO_LEVEL_CASE_EXCEPTION",
                    "Audio RMS probe case raised unexpectedly.",
                    case_id=case_id,
                    observed=str(exc),
                )
            )
            continue
        delta = abs(observed - float(expected_level))
        status = "pass" if delta <= tolerance else "blocked"
        if status != "pass":
            findings.append(
                finding(
                    "BATCH8_AUDIO_LEVEL_PARITY_MISMATCH",
                    "Python port result must match the fixture expectation.",
                    case_id=case_id,
                    expected=expected_level,
                    observed=observed,
                )
            )
        observed_ids.append(case_id)
        case_results.append(
            {
                "case_id": case_id,
                "sample_format": sample_format,
                "sample_count": len(samples),
                "expected_level": float(expected_level),
                "observed_level": observed,
                "delta": delta,
                "tolerance": tolerance,
                "status": status,
                "body_in_receipt": False,
            }
        )

    missing = sorted(set(EXPECTED_CASES) - set(observed_ids))
    for case_id in missing:
        findings.append(
            finding(
                "BATCH8_AUDIO_LEVEL_REFERENCE_CASE_MISSING",
                "Audio RMS probe manifest is missing an expected reference case.",
                case_id=case_id,
            )
        )
    return case_results, findings


def _evaluate_byte_reference_cases(
    probe: Mapping[str, Any],
    input_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    case_results: list[dict[str, Any]] = []
    for row in _byte_case_rows(probe):
        case_id = str(row.get("case_id") or "")
        audio_ref = str(row.get("audio_ref") or "")
        sample_format = str(row.get("sample_format") or "")
        container = str(row.get("container") or "")
        expected_level = row.get("expected_level")
        tolerance_raw = row.get("tolerance", 1e-6)
        if tolerance_raw is None:
            tolerance_raw = 1e-6
        if (
            not case_id
            or not audio_ref
            or container != "wav"
            or sample_format != "int16"
            or not _is_finite_number(expected_level)
            or not _is_finite_number(tolerance_raw)
            or float(tolerance_raw) < 0
        ):
            findings.append(
                finding(
                    "BATCH8_AUDIO_LEVEL_BYTE_CASE_INVALID",
                    "Audio byte cases require case_id, WAV audio_ref, int16 format, finite expected_level, and non-negative finite tolerance.",
                    case_id=case_id,
                )
            )
            continue
        audio_path = input_path / audio_ref
        if not audio_path.is_file():
            findings.append(
                finding(
                    "BATCH8_AUDIO_LEVEL_WAV_MISSING",
                    "Audio byte case references a missing WAV file.",
                    case_id=case_id,
                    subject_id=audio_ref,
                )
            )
            continue
        try:
            samples, audio_meta = _decode_int16_wav(audio_path)
        except wave.Error as exc:
            findings.append(
                finding(
                    "BATCH8_AUDIO_LEVEL_WAV_DECODE_FAILED",
                    "Audio byte case WAV decoding failed.",
                    case_id=case_id,
                    observed=str(exc),
                )
            )
            continue
        except ValueError as exc:
            findings.append(
                finding(
                    "BATCH8_AUDIO_LEVEL_UNSUPPORTED_WAV_FORMAT",
                    "Audio byte case WAV format is outside the public proof contract.",
                    case_id=case_id,
                    observed=str(exc),
                )
            )
            continue
        observed = normalized_level(samples, "int16")
        tolerance = float(tolerance_raw)
        delta = abs(observed - float(expected_level))
        status = "pass" if delta <= tolerance else "blocked"
        if status != "pass":
            findings.append(
                finding(
                    "BATCH8_AUDIO_LEVEL_PARITY_MISMATCH",
                    "Decoded WAV bytes must recompute to the manifest expectation.",
                    case_id=case_id,
                    expected=expected_level,
                    observed=observed,
                )
            )
        case_results.append(
            {
                "case_id": case_id,
                "audio_ref": audio_ref,
                **audio_meta,
                "expected_level": float(expected_level),
                "observed_level": observed,
                "delta": delta,
                "tolerance": tolerance,
                "status": status,
                "body_in_receipt": False,
            }
        )
    return case_results, findings


def _evaluate_negative_exercises(input_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    empty_level = normalized_level([], "float32")
    clamp_level = normalized_level([1.0, -1.0, 0.5], "float32")
    unknown_refused = False
    unknown_message = ""
    try:
        normalized_level([1, 2, 3], "pcm24")
    except ValueError as exc:
        unknown_refused = True
        unknown_message = str(exc)

    empty_payload = load_json_object(
        input_path / "audio_level_empty_buffer_zero.json",
        findings,
        label="empty buffer negative",
    )
    clamp_payload = load_json_object(
        input_path / "audio_level_clamps_over_one.json",
        findings,
        label="clamp negative",
    )
    unknown_payload = load_json_object(
        input_path / "audio_level_unknown_format_refused.json",
        findings,
        label="unknown format negative",
    )
    if empty_level != 0.0 or empty_payload.get("expected_level") != 0:
        findings.append(
            finding(
                "BATCH8_AUDIO_LEVEL_EMPTY_BUFFER_ZERO",
                "Empty buffers must return zero level.",
                observed=empty_level,
            )
        )
    if clamp_level != 1.0 or clamp_payload.get("expected_level") != 1:
        findings.append(
            finding(
                "BATCH8_AUDIO_LEVEL_CLAMP_REQUIRED",
                "Over-one RMS-scaled buffers must clamp to one.",
                observed=clamp_level,
            )
        )
    if not unknown_refused or unknown_payload.get("expected_decision") != "raise ValueError":
        findings.append(
            finding(
                "BATCH8_AUDIO_LEVEL_UNKNOWN_FORMAT_REFUSED",
                "Unsupported formats must be refused.",
                observed=unknown_message,
            )
        )
    return (
        {
            "empty_buffer_level": empty_level,
            "clamp_over_one_level": clamp_level,
            "unknown_format_refused": unknown_refused,
            "unknown_format_message": unknown_message,
            "status": "pass" if not findings else "blocked",
            "body_in_receipt": False,
        },
        findings,
    )


def evaluate_negative_case(
    case_id: str,
    _input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    if case_id == "audio_level_empty_buffer_zero":
        observed = normalized_level([], "float32")
        return {
            "status": "blocked" if observed == 0.0 else "pass",
            "case_id": case_id,
            "error_codes": (
                ["BATCH8_AUDIO_LEVEL_EMPTY_BUFFER_ZERO"] if observed == 0.0 else []
            ),
            "observed": {"empty_buffer_level": observed},
            "derived_from": "normalized_level_python_port",
            "body_in_receipt": False,
        }
    if case_id == "audio_level_clamps_over_one":
        observed = normalized_level([1.0, -1.0, 0.5], "float32")
        return {
            "status": "blocked" if observed == 1.0 else "pass",
            "case_id": case_id,
            "error_codes": (
                ["BATCH8_AUDIO_LEVEL_CLAMP_REQUIRED"] if observed == 1.0 else []
            ),
            "observed": {"clamp_over_one_level": observed},
            "derived_from": "normalized_level_python_port",
            "body_in_receipt": False,
        }
    if case_id == "audio_level_unknown_format_refused":
        refused = False
        message = ""
        try:
            normalized_level([1, 2, 3], "pcm24")
        except ValueError as exc:
            refused = True
            message = str(exc)
        return {
            "status": "blocked" if refused else "pass",
            "case_id": case_id,
            "error_codes": (
                ["BATCH8_AUDIO_LEVEL_UNKNOWN_FORMAT_REFUSED"] if refused else []
            ),
            "observed": {"unknown_format_refused": refused, "message": message},
            "derived_from": "normalized_level_python_port",
            "body_in_receipt": False,
        }
    return {
        "status": "pass",
        "case_id": case_id,
        "error_codes": [],
        "body_in_receipt": False,
    }


def _audio_evaluator(
    input_path: Path,
    public_root: Path,
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    del public_root
    probe = load_json_object(input_path / PROBE_MANIFEST_NAME, [], label=PROBE_MANIFEST_NAME)
    case_results, case_findings = _evaluate_reference_cases(probe)
    byte_case_results, byte_case_findings = _evaluate_byte_reference_cases(
        probe,
        input_path,
    )
    negative_results, negative_findings = _evaluate_negative_exercises(input_path)
    findings = [*case_findings, *byte_case_findings, *negative_findings]
    passed_case_count = sum(1 for row in case_results if row.get("status") == "pass")
    passed_byte_case_count = sum(
        1 for row in byte_case_results if row.get("status") == "pass"
    )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_id": "audio_level_rms_dsp_python_port",
        "source_language": "Swift",
        "port_language": "Python",
        "source_ref": SWIFT_SOURCE_REF,
        "reference_case_count": len(case_results),
        "passed_reference_case_count": passed_case_count,
        "expected_reference_cases": list(EXPECTED_CASES),
        "reference_cases": case_results,
        "byte_reference_case_count": len(byte_case_results),
        "passed_byte_reference_case_count": passed_byte_case_count,
        "byte_reference_cases": byte_case_results,
        "negative_exercises": negative_results,
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "error_codes": sorted(
            {
                "BATCH8_AUDIO_LEVEL_EMPTY_BUFFER_ZERO",
                "BATCH8_AUDIO_LEVEL_UNKNOWN_FORMAT_REFUSED",
                "BATCH8_AUDIO_LEVEL_CLAMP_REQUIRED",
            }
        ),
        "claim_ceiling": "Pure RMS normalization parity only; no sample-buffer, permission, device, or session authority.",
        "body_in_receipt": False,
        "findings": findings,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_audio_evaluator,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch8_audio_level_rms_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_audio_evaluator,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    source = (
        result.get("source_module_manifest")
        if isinstance(result.get("source_module_manifest"), Mapping)
        else {}
    )
    ceiling = (
        result.get("authority_ceiling")
        if isinstance(result.get("authority_ceiling"), Mapping)
        else {}
    )
    card["reference_case_count"] = exercise.get("reference_case_count")
    card["passed_reference_case_count"] = exercise.get("passed_reference_case_count")
    card["authority_floor"] = {
        "authority_ceiling": ceiling.get("authority_ceiling"),
        "real_substrate_disposition": ceiling.get("real_substrate_disposition"),
        "python_port": ceiling.get("python_port"),
        "microphone_permission_required": ceiling.get(
            "microphone_permission_required"
        ),
        "audio_session_started": ceiling.get("audio_session_started"),
        "device_capture_authorized": ceiling.get("device_capture_authorized"),
        "provider_dispatch": ceiling.get("provider_dispatch"),
        "repo_mutation_authorized": ceiling.get("repo_mutation_authorized"),
        "source_mutation_authorized": ceiling.get("source_mutation_authorized"),
        "publication_authorized": ceiling.get("publication_authorized"),
        "release_authorized": ceiling.get("release_authorized"),
    }
    card["body_floor"] = {
        "body_in_receipt": result.get("body_in_receipt"),
        "source_module_body_in_receipt": source.get("body_in_receipt"),
        "receipt_body_scan_status": (
            result.get("receipt_body_scan", {}).get("status")
            if isinstance(result.get("receipt_body_scan"), Mapping)
            else None
        ),
        "source_bodies_in_card": False,
        "secret_scan_scope_in_card": False,
    }
    return card


def main(argv: list[str] | None = None) -> int:
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
        input_mode=(
            BUNDLE_INPUT_MODE
            if args.action == "validate-bundle"
            else "fixture_input"
        ),
        evaluator=_audio_evaluator,
        negative_case_evaluator=evaluate_negative_case,
    )
    print(
        json.dumps(
            result_card(result) if args.card else result,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
