from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.public_payload_boundary import (
    SOURCE_OPEN_BODY_POLICY,
    public_payload_boundary,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "spatial_world_model_counterfactual_simulation_replay"
FIXTURE_ID = "first_wave.spatial_world_model_counterfactual_simulation_replay"
VALIDATOR_ID = (
    "validator.microcosm.organs."
    "spatial_world_model_counterfactual_simulation_replay"
)

RESULT_NAME = "spatial_world_model_counterfactual_simulation_replay_result.json"
BOARD_NAME = "spatial_world_model_counterfactual_simulation_replay_board.json"
VALIDATION_RECEIPT_NAME = (
    "spatial_world_model_counterfactual_simulation_replay_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "spatial_world_model_counterfactual_simulation_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_spatial_world_model_simulation_bundle_validation_result.json"
PAYLOAD_BOUNDARY_ID = (
    "spatial_world_model_counterfactual_simulation_replay_payload_boundary"
)
ROW_PAYLOAD_BOUNDARY_REF = (
    "spatial_world_model_counterfactual_simulation_replay::counterfactual_replay_row"
)

INPUT_NAMES = (
    "simulation_protocol.json",
    "replay_policy.json",
    "scene_states.json",
    "counterfactual_replays.json",
)
NEGATIVE_INPUT_NAMES = (
    "private_video_export.json",
    "real_world_location_claim.json",
    "live_robot_or_av_operation.json",
    "raw_sensor_data_export.json",
    "simulator_product_claim.json",
    "generated_video_only_authority.json",
    "geographic_accuracy_claim.json",
    "benchmark_score_without_state_diff.json",
)

EXPECTED_NEGATIVE_CASES = {
    "private_video_export": ["SPATIAL_PRIVATE_VIDEO_FORBIDDEN"],
    "real_world_location_claim": ["SPATIAL_REAL_LOCATION_CLAIM_FORBIDDEN"],
    "live_robot_or_av_operation": ["SPATIAL_LIVE_OPERATION_FORBIDDEN"],
    "raw_sensor_data_export": ["SPATIAL_RAW_SENSOR_DATA_FORBIDDEN"],
    "simulator_product_claim": ["SPATIAL_SIMULATOR_PRODUCT_CLAIM_FORBIDDEN"],
    "generated_video_only_authority": [
        "SPATIAL_GENERATED_VIDEO_ONLY_AUTHORITY_FORBIDDEN"
    ],
    "geographic_accuracy_claim": ["SPATIAL_GEOGRAPHIC_ACCURACY_FORBIDDEN"],
    "benchmark_score_without_state_diff": [
        "SPATIAL_BENCHMARK_SCORE_REQUIRES_STATE_DIFF"
    ],
}

REQUIRED_REPLAY_FIELDS = (
    "replay_id",
    "scene_state_ref",
    "action_trace_ref",
    "counterfactual_event",
    "predicted_state_ref",
    "transition_diff_ref",
    "oracle_state_check_ref",
    "sensor_packet_refs",
    "rare_event_coverage_label",
    "fidelity_limit_label",
    "consistency_budget",
    "limitation_labels",
    "cold_replay_ref",
    "payload_boundary_ref",
    "source_open_body_policy",
    "unsafe_payload_bodies_exported",
    "private_video_exported",
    "raw_sensor_data_exported",
    "live_robot_operation_authorized",
    "live_av_operation_authorized",
    "real_world_location_claim",
    "simulator_product_claim",
    "generated_video_only_authority",
    "geographic_accuracy_claim",
    "benchmark_score_claim",
    "release_authorized",
)
PRIVATE_NEEDLES = (
    "/Users/",
    "src/ai_workflow",
    "Library/Application Support/Google",
    "sk-",
    "private_video_body",
    "raw_sensor_payload",
    "gps_trace_body",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "synthetic_spatial_counterfactual_replay_metadata_only",
    "metadata_projection_only": True,
    "trained_simulator_claim_authorized": False,
    "generated_video_authority_authorized": False,
    "private_video_exported": False,
    "raw_sensor_data_exported": False,
    "live_robot_operation_authorized": False,
    "live_av_operation_authorized": False,
    "real_world_location_claim_authorized": False,
    "geographic_accuracy_claim_authorized": False,
    "benchmark_score_claim_authorized": False,
    "release_authorized": False,
    "hosted_public_authorized": False,
    "publication_authorized": False,
    "provider_calls_authorized": False,
}
ANTI_CLAIM = (
    "Spatial world-model counterfactual simulation replay validates synthetic "
    "metadata rows that bind scene states, action traces, predicted states, "
    "transition diffs, oracle checks, and limitation labels. It does not export "
    "private video or raw sensor bodies, operate robots or AVs, claim real-world "
    "geographic accuracy, sell a simulator product, use generated video as sole "
    "authority, report benchmark scores, or authorize release."
)


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    return paths


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "payload_boundary_ref": ROW_PAYLOAD_BOUNDARY_REF,
        "source_open_body_policy": SOURCE_OPEN_BODY_POLICY,
        "unsafe_payload_bodies_exported": False,
    }


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> None:
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    if case_id in EXPECTED_NEGATIVE_CASES:
        observed[case_id].add(code)


def _replay_policy_findings(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    subject_id = str(row.get("replay_id") or case_id)
    for field in REQUIRED_REPLAY_FIELDS:
        if field not in row:
            _record(
                findings,
                observed,
                "SPATIAL_REPLAY_FIELD_REQUIRED",
                f"counterfactual replay is missing required field {field}",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="counterfactual_replay",
            )
    if not row.get("scene_state_ref") or not row.get("predicted_state_ref"):
        _record(
            findings,
            observed,
            "SPATIAL_STATE_REF_REQUIRED",
            "counterfactual replay must bind source and predicted scene-state refs",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="counterfactual_replay",
        )
    if not row.get("action_trace_ref") or not row.get("counterfactual_event"):
        _record(
            findings,
            observed,
            "SPATIAL_ACTION_TRACE_REQUIRED",
            "counterfactual replay must bind an action trace and event label",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="counterfactual_replay",
        )
    missing_transition_diff = not row.get("transition_diff_ref")
    if missing_transition_diff and row.get("benchmark_score_claim") is True:
        _record(
            findings,
            observed,
            "SPATIAL_BENCHMARK_SCORE_REQUIRES_STATE_DIFF",
            "benchmark score language is forbidden without a transition diff ref",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="counterfactual_replay",
        )
    elif missing_transition_diff or not row.get("oracle_state_check_ref"):
        _record(
            findings,
            observed,
            "SPATIAL_STATE_DIFF_REQUIRED",
            "counterfactual replay must cite transition diff and oracle check refs",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="counterfactual_replay",
        )
    if not _strings(row.get("sensor_packet_refs")):
        _record(
            findings,
            observed,
            "SPATIAL_SENSOR_PACKET_REFS_REQUIRED",
            "counterfactual replay must cite source-open public sensor packet refs",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="counterfactual_replay",
        )
    if not _strings(row.get("limitation_labels")):
        _record(
            findings,
            observed,
            "SPATIAL_LIMITATION_LABEL_REQUIRED",
            "counterfactual replay must carry limitation labels",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="counterfactual_replay",
        )
    bool_forbidden = {
        "private_video_exported": "SPATIAL_PRIVATE_VIDEO_FORBIDDEN",
        "raw_sensor_data_exported": "SPATIAL_RAW_SENSOR_DATA_FORBIDDEN",
        "real_world_location_claim": "SPATIAL_REAL_LOCATION_CLAIM_FORBIDDEN",
        "simulator_product_claim": "SPATIAL_SIMULATOR_PRODUCT_CLAIM_FORBIDDEN",
        "generated_video_only_authority": (
            "SPATIAL_GENERATED_VIDEO_ONLY_AUTHORITY_FORBIDDEN"
        ),
        "geographic_accuracy_claim": "SPATIAL_GEOGRAPHIC_ACCURACY_FORBIDDEN",
        "release_authorized": "SPATIAL_RELEASE_AUTHORITY_FORBIDDEN",
    }
    for field, code in bool_forbidden.items():
        if row.get(field) is True:
            _record(
                findings,
                observed,
                code,
                f"{field} must be false for public spatial replay rows",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="counterfactual_replay",
            )
    if (
        row.get("live_robot_operation_authorized") is True
        or row.get("live_av_operation_authorized") is True
    ):
        _record(
            findings,
            observed,
            "SPATIAL_LIVE_OPERATION_FORBIDDEN",
            "public spatial replay rows cannot authorize live robot or AV operation",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="counterfactual_replay",
        )
    if (
        row.get("payload_boundary_ref") != ROW_PAYLOAD_BOUNDARY_REF
        or row.get("source_open_body_policy") != SOURCE_OPEN_BODY_POLICY
        or row.get("unsafe_payload_bodies_exported") is not False
    ):
        _record(
            findings,
            observed,
            "SPATIAL_PAYLOAD_BOUNDARY_REQUIRED",
            "spatial replay rows must declare the source-open payload boundary",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="counterfactual_replay",
        )
    if row.get("private_video_body") or row.get("raw_sensor_payload") or any(
        needle in json.dumps(row, sort_keys=True) for needle in PRIVATE_NEEDLES
    ):
        _record(
            findings,
            observed,
            "SPATIAL_PRIVATE_OR_RAW_BODY_FORBIDDEN",
            "private video bodies and raw sensor payloads cannot enter public replay rows",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="counterfactual_replay",
        )
    return findings


def _required_policy_ok(policy: dict[str, Any]) -> bool:
    ceiling = policy.get("authority_ceiling")
    if not isinstance(ceiling, dict):
        return False
    return (
        ceiling.get("metadata_projection_only") is True
        and all(
            value is False
            for key, value in ceiling.items()
            if key != "metadata_projection_only"
        )
    )


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    public_root = _public_root_for_path(input_dir)
    simulation_protocol = payloads.get("simulation_protocol", {})
    replay_policy = payloads.get("replay_policy", {})
    scene_states = _rows(payloads.get("scene_states", {}), "scene_states")
    replays = _rows(payloads.get("counterfactual_replays", {}), "counterfactual_replays")
    observed_negative_codes: dict[str, set[str]] = defaultdict(set)
    positive_findings: list[dict[str, Any]] = []

    if (
        not isinstance(simulation_protocol, dict)
        or simulation_protocol.get("selected_route_id") != ORGAN_ID
    ):
        positive_findings.append(
            _finding(
                "SPATIAL_PROTOCOL_ROUTE_REQUIRED",
                f"simulation protocol must select {ORGAN_ID}",
                case_id="positive_fixture",
                subject_id="simulation_protocol",
                subject_kind="protocol",
            )
        )
    if not _required_policy_ok(replay_policy if isinstance(replay_policy, dict) else {}):
        positive_findings.append(
            _finding(
                "SPATIAL_AUTHORITY_CEILING_REQUIRED",
                "replay policy must declare the payload-boundary authority ceiling",
                case_id="positive_fixture",
                subject_id="replay_policy",
                subject_kind="policy",
            )
        )
    for row in replays:
        positive_findings.extend(
            _replay_policy_findings(
                row,
                case_id="positive_fixture",
                observed=observed_negative_codes,
            )
        )
    selected_pattern_ids = _strings(simulation_protocol.get("selected_pattern_ids"))
    replay_ids = [str(row.get("replay_id")) for row in replays if row.get("replay_id")]
    if selected_pattern_ids and selected_pattern_ids != replay_ids:
        positive_findings.append(
            _finding(
                "SPATIAL_SELECTED_PATTERN_IDS_MISMATCH",
                "selected_pattern_ids must exactly match validated replay ids",
                case_id="positive_fixture",
                subject_id="simulation_protocol",
                subject_kind="protocol",
            )
        )

    negative_findings: list[dict[str, Any]] = []
    if include_negative:
        for name in NEGATIVE_INPUT_NAMES:
            case_id = Path(name).stem
            payload = payloads.get(case_id, {})
            replay_payload = (
                payload.get("counterfactual_replay", payload)
                if isinstance(payload, dict)
                else {}
            )
            if isinstance(replay_payload, dict):
                negative_findings.extend(
                    _replay_policy_findings(
                        replay_payload,
                        case_id=case_id,
                        observed=observed_negative_codes,
                    )
                )

    expected_cases = EXPECTED_NEGATIVE_CASES if include_negative else {}
    expected_missing = {
        case_id: sorted(set(codes) - observed_negative_codes.get(case_id, set()))
        for case_id, codes in expected_cases.items()
    }
    expected_missing = {case_id: codes for case_id, codes in expected_missing.items() if codes}
    encoded_positive = json.dumps(replays, sort_keys=True)
    unsafe_payload_bodies_absent = not any(
        needle in encoded_positive for needle in PRIVATE_NEEDLES
    )
    policy_passed = (
        bool(scene_states)
        and bool(replays)
        and not positive_findings
        and unsafe_payload_bodies_absent
        and not expected_missing
        and all(
            row.get("payload_boundary_ref") == ROW_PAYLOAD_BOUNDARY_REF
            for row in replays
        )
        and all(
            row.get("source_open_body_policy") == SOURCE_OPEN_BODY_POLICY
            for row in replays
        )
        and all(row.get("unsafe_payload_bodies_exported") is False for row in replays)
        and all(row.get("private_video_exported") is False for row in replays)
        and all(row.get("raw_sensor_data_exported") is False for row in replays)
        and all(row.get("live_robot_operation_authorized") is False for row in replays)
        and all(row.get("live_av_operation_authorized") is False for row in replays)
        and all(row.get("real_world_location_claim") is False for row in replays)
        and all(row.get("simulator_product_claim") is False for row in replays)
        and all(row.get("generated_video_only_authority") is False for row in replays)
        and all(row.get("geographic_accuracy_claim") is False for row in replays)
        and all(row.get("release_authorized") is False for row in replays)
    )

    scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=load_forbidden_classes(
            public_root / "core/private_state_forbidden_classes.json"
        ),
        display_root=public_root,
    )
    status = PASS if policy_passed and scan.get("status") == PASS else "blocked"
    return {
        "schema_version": "spatial_world_model_counterfactual_simulation_replay_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "input_ref": _display(input_dir, public_root=public_root),
        "selected_route_id": ORGAN_ID,
        "selected_pattern_ids": replay_ids,
        "scene_states": scene_states,
        "counterfactual_replays": replays,
        "simulation_summary": {
            "scene_state_count": len(scene_states),
            "replay_count": len(replays),
            "transition_diff_count": sum(1 for row in replays if row.get("transition_diff_ref")),
            "oracle_state_check_count": sum(1 for row in replays if row.get("oracle_state_check_ref")),
            "sensor_packet_ref_count": sum(len(_strings(row.get("sensor_packet_refs"))) for row in replays),
            "rare_event_coverage_count": sum(1 for row in replays if row.get("rare_event_coverage_label")),
            "fidelity_limit_count": sum(1 for row in replays if row.get("fidelity_limit_label")),
            "private_video_export_count": sum(1 for row in replays if row.get("private_video_exported") is True),
            "raw_sensor_data_export_count": sum(1 for row in replays if row.get("raw_sensor_data_exported") is True),
            "live_operation_authorized_count": sum(
                1
                for row in replays
                if row.get("live_robot_operation_authorized") is True
                or row.get("live_av_operation_authorized") is True
            ),
            "real_world_location_claim_count": sum(1 for row in replays if row.get("real_world_location_claim") is True),
            "simulator_product_claim_count": sum(1 for row in replays if row.get("simulator_product_claim") is True),
            "generated_video_only_authority_count": sum(1 for row in replays if row.get("generated_video_only_authority") is True),
            "geographic_accuracy_claim_count": sum(1 for row in replays if row.get("geographic_accuracy_claim") is True),
            "benchmark_score_claim_count": sum(1 for row in replays if row.get("benchmark_score_claim") is True),
        },
        "negative_case_summary": {
            "expected_negative_case_count": len(expected_cases),
            "observed_negative_case_count": sum(
                1 for case_id in expected_cases if observed_negative_codes.get(case_id)
            ),
            "expected_missing": expected_missing,
            "observed_codes": {
                case_id: sorted(codes)
                for case_id, codes in sorted(observed_negative_codes.items())
                if case_id in expected_cases
            },
        },
        "finding_count": len(positive_findings),
        "positive_findings": positive_findings,
        "negative_case_findings": negative_findings,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "source_open_body_policy": SOURCE_OPEN_BODY_POLICY,
        "unsafe_payload_bodies_in_receipt": False,
        "payload_boundary": public_payload_boundary(
            boundary_id=PAYLOAD_BOUNDARY_ID,
            command=command,
            surface_ref=_display(input_dir, public_root=public_root),
        ),
        "safe_to_show": {
            "unsafe_payload_bodies_absent": unsafe_payload_bodies_absent,
            "counterfactual_replays_are_public_payload_boundary_rows": True,
            "private_video_bodies_omitted": True,
            "raw_sensor_payloads_omitted": True,
            "live_operation_omitted": True,
            "real_world_location_omitted": True,
        },
        "release_authorized": False,
        "secret_exclusion_scan": scan,
    }


def _board(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("simulation_summary", {})
    negatives = result.get("negative_case_summary", {})
    return {
        "schema_version": "spatial_world_model_counterfactual_simulation_replay_board_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "spatial_world_model_counterfactual_simulation_public_board",
        "route": ORGAN_ID,
        "scene_state_count": summary.get("scene_state_count", 0)
        if isinstance(summary, dict)
        else 0,
        "replay_count": summary.get("replay_count", 0) if isinstance(summary, dict) else 0,
        "transition_diff_count": summary.get("transition_diff_count", 0)
        if isinstance(summary, dict)
        else 0,
        "oracle_state_check_count": summary.get("oracle_state_check_count", 0)
        if isinstance(summary, dict)
        else 0,
        "negative_case_count": negatives.get("expected_negative_case_count", 0)
        if isinstance(negatives, dict)
        else 0,
        "observed_negative_case_count": negatives.get("observed_negative_case_count", 0)
        if isinstance(negatives, dict)
        else 0,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(out_dir)
    result_path = out_dir / RESULT_NAME
    board_path = out_dir / BOARD_NAME
    validation_path = out_dir / VALIDATION_RECEIPT_NAME
    board = _board(result)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
    ]
    validation = {
        "schema_version": (
            "spatial_world_model_counterfactual_simulation_replay_"
            "validation_receipt_v1"
        ),
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "result_ref": receipt_paths[0],
        "board_ref": receipt_paths[1],
        "receipt_paths": receipt_paths,
        "replay_count": (result.get("simulation_summary") or {}).get("replay_count"),
        "expected_negative_case_count": (result.get("negative_case_summary") or {}).get(
            "expected_negative_case_count"
        ),
        "observed_negative_case_count": (result.get("negative_case_summary") or {}).get(
            "observed_negative_case_count"
        ),
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "release_authorized": False,
    }
    write_json_atomic(result_path, result)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    if acceptance_out is not None:
        acceptance_path = acceptance_out
        acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        acceptance_path = public_root / ACCEPTANCE_RECEIPT_REL
    acceptance = {
        "schema_version": (
            "spatial_world_model_counterfactual_simulation_replay_"
            "fixture_acceptance_v1"
        ),
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "result_ref": receipt_paths[0],
        "board_ref": receipt_paths[1],
        "validation_ref": receipt_paths[2],
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "release_authorized": False,
        "source_open_body_policy": SOURCE_OPEN_BODY_POLICY,
        "unsafe_payload_bodies_in_receipt": False,
        "payload_boundary": public_payload_boundary(
            boundary_id=PAYLOAD_BOUNDARY_ID,
            command="microcosm spatial-world-model-counterfactual-simulation-replay run",
            surface_ref=receipt_paths[0],
        ),
    }
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "spatial_simulation_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = (
        "python -m microcosm_core.organs."
        "spatial_world_model_counterfactual_simulation_replay run"
    ),
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_simulation_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs."
        "spatial_world_model_counterfactual_simulation_replay run-simulation-bundle"
    ),
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_spatial_world_model_simulation_bundle",
        include_negative=False,
    )
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": (
            "exported_spatial_world_model_simulation_bundle_"
            "validation_result_v1"
        ),
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="spatial_world_model_counterfactual_simulation_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    bundle_parser = sub.add_parser("run-simulation-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
    elif args.action == "run-simulation-bundle":
        result = run_simulation_bundle(args.input, args.out)
    else:  # pragma: no cover
        raise ValueError(args.action)
    print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
