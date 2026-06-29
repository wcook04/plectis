"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, ACCEPTANCE_RECEIPT_REL, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, CARD_OMITTED_FULL_PAYLOAD_KEYS, SOURCE_MODULE_MANIFEST_NAME, PAYLOAD_BOUNDARY_ID, ROW_PAYLOAD_BOUNDARY_REF, INPUT_NAMES, NEGATIVE_INPUT_NAMES, EXPECTED_NEGATIVE_CASES, REQUIRED_REPLAY_FIELDS, PRIVATE_NEEDLES, AUTHORITY_CEILING, ANTI_CLAIM, SOURCE_MODULE_IMPORT_STATUS, BODY_DIGEST_PREFIX, SOURCE_IMPORT_CLASS, SOURCE_BODY_STATUS, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.public_payload_boundary, microcosm_core.receipts, microcosm_core.schemas, microcosm_core.secret_exclusion_scan
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import hashlib
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
from microcosm_core.receipts import (
    normalize_public_receipt_paths,
    utc_now,
    write_json_atomic,
)
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
CARD_SCHEMA_VERSION = "spatial_world_model_simulation_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "scene_states",
    "counterfactual_replays",
    "state_transition_analysis",
    "positive_findings",
    "negative_case_findings",
    "source_module_summary",
    "source_open_body_imports",
    "authority_ceiling",
    "anti_claim",
    "secret_exclusion_scan",
    "spatial_simulation_board",
)
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
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
    "state_transitions.json",
    SOURCE_MODULE_MANIFEST_NAME,
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
SOURCE_MODULE_IMPORT_STATUS = "copied_non_secret_macro_body_landed"
BODY_DIGEST_PREFIX = "sha256:"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_BODY_STATUS = SOURCE_MODULE_IMPORT_STATUS
SOURCE_OPEN_BODY_SCHEMA = (
    "spatial_world_model_counterfactual_simulation_replay_source_open_body_imports_v1"
)
GRIDWORLD_WIDTH = 8
GRIDWORLD_HEIGHT = 8
EVENT_GRIDWORLD_ACTIONS = {
    "occluded_forklift_enters_aisle": {
        "actor_count_delta": 1,
        "spawn_cell": [6, 1],
        "event_delta_label": "new_dynamic_actor",
    },
    "small_pedestrian_enters_crosswalk": {
        "actor_count_delta": 1,
        "spawn_cell": [2, 6],
        "event_delta_label": "new_dynamic_actor",
    },
    "lateral_gust_pushes_vehicle": {
        "actor_count_delta": 1,
        "spawn_cell": [4, 4],
        "event_delta_label": "new_dynamic_actor",
    },
    "specular_floor_false_free_space": {
        "actor_count_delta": 1,
        "spawn_cell": [5, 5],
        "event_delta_label": "new_dynamic_actor",
    },
    "pallet_stack_shifts_into_lane": {
        "actor_count_delta": 1,
        "spawn_cell": [1, 7],
        "event_delta_label": "new_dynamic_actor",
    },
    "oncoming_vehicle_accelerates_late": {
        "actor_count_delta": 1,
        "spawn_cell": [7, 3],
        "event_delta_label": "new_dynamic_actor",
    },
}


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate" or (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src/microcosm_core").is_dir()
            and (candidate / "core/private_state_forbidden_classes.json").is_file()
        ):
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_display` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_relative_path(path, display_root=public_root)


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_rows` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names if (input_dir / name).is_file()]
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    return paths


def _target_path_for_ref(target_ref: str, *, public_root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_target_path_for_ref` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    target = target_ref.removeprefix("microcosm-substrate/")
    return public_root / target


def _source_file_candidates(source_ref: str, *, public_root: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_source_file_candidates` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rel = Path(source_ref.split("::", 1)[0])
    if rel.is_absolute() or ".." in rel.parts:
        return []
    candidates = [public_root / rel, public_root.parent / rel, Path.cwd() / rel]
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve(strict=False))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _first_existing_source(source_ref: str, *, public_root: Path) -> Path | None:
    """
    [ACTION]
    - Teleology: Implements `_first_existing_source` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for candidate in _source_file_candidates(source_ref, public_root=public_root):
        if candidate.is_file():
            return candidate
    return None


def _sha256_hex(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256_hex` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_ref(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256_ref` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return f"{BODY_DIGEST_PREFIX}{_sha256_hex(path)}"


def _json_digest(payload: object) -> str:
    """
    [ACTION]
    - Teleology: Implements `_json_digest` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _line_count(path: Path) -> int:
    """
    [ACTION]
    - Teleology: Implements `_line_count` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    line_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_count, _line in enumerate(handle, start=1):
            pass
    return line_count or 1


def _source_module_paths(manifest_payload: object, *, public_root: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_paths` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(manifest_payload, dict):
        return []
    paths: list[Path] = []
    for row in _rows(manifest_payload, "modules"):
        target_ref = row.get("target_ref")
        if isinstance(target_ref, str) and target_ref:
            target = _target_path_for_ref(target_ref, public_root=public_root)
            if target.is_file():
                paths.append(target)
    return paths


def _freshness_paths(input_dir: Path, *, public_root: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_freshness_paths` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    paths = _input_paths(input_dir, include_negative=False)
    manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    manifest_payload: object = {}
    if manifest_path.is_file():
        manifest_payload = read_json_strict(manifest_path)
    paths.extend(_source_module_paths(manifest_payload, public_root=public_root))
    paths.extend(
        [
            Path(__file__),
            public_root / "core/private_state_forbidden_classes.json",
        ]
    )
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve(strict=False))
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _freshness_basis(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_freshness_basis` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    input_paths = _freshness_paths(input_dir, public_root=public_root)
    path_rows = []
    missing_paths = []
    for path in input_paths:
        display = _display(path, public_root=public_root)
        if path.is_file():
            path_rows.append(
                {
                    "path": display,
                    "sha256": _sha256_ref(path),
                    "bytes": path.stat().st_size,
                }
            )
        else:
            missing_paths.append(display)
    basis = {
        "schema_version": "spatial_world_model_simulation_freshness_basis_v1",
        "organ_id": ORGAN_ID,
        "input_mode": input_mode,
        "command": command,
        "input_ref": _display(input_dir, public_root=public_root),
        "input_count": len(path_rows),
        "missing_input_count": len(missing_paths),
        "missing_paths": missing_paths,
        "inputs": path_rows,
    }
    return {**basis, "digest": _json_digest(basis)}


def _fresh_spatial_simulation_bundle_receipt(
    receipt_path: Path,
    freshness_basis: dict[str, Any],
    *,
    command: str,
) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Implements `_fresh_spatial_simulation_bundle_receipt` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if freshness_basis.get("missing_input_count"):
        return None
    if not receipt_path.is_file():
        return None
    try:
        receipt = read_json_strict(receipt_path)
    except Exception:
        return None
    if not isinstance(receipt, dict):
        return None
    if (
        receipt.get("schema_version")
        != "exported_spatial_world_model_simulation_bundle_validation_result_v1"
        or receipt.get("organ_id") != ORGAN_ID
        or receipt.get("input_mode")
        != "exported_spatial_world_model_simulation_bundle"
        or receipt.get("command") != command
    ):
        return None
    receipt_basis = receipt.get("freshness_basis")
    if not isinstance(receipt_basis, dict):
        return None
    if receipt_basis.get("digest") != freshness_basis.get("digest"):
        return None
    return {**receipt, "receipt_reused": True, "freshness_basis": freshness_basis}


def _source_module_manifest_result(
    manifest_payload: object,
    *,
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_result` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    if not isinstance(manifest_payload, dict):
        return {
            "status": "not_present",
            "body_import_status": "not_present",
            "module_count": 0,
            "verified_module_count": 0,
            "module_ids": [],
            "public_safe_body_material_ids": [],
            "material_classes": [],
            "body_text_in_receipt": False,
            "body_in_receipt": False,
            "findings": [],
        }

    findings: list[dict[str, Any]] = []
    module_results: list[dict[str, Any]] = []
    material_classes: set[str] = set()
    if manifest_payload.get("body_text_in_receipt") is True:
        findings.append(
            {
                "error_code": "SPATIAL_SOURCE_BODY_TEXT_IN_RECEIPT_FORBIDDEN",
                "module_id": SOURCE_MODULE_MANIFEST_NAME,
                "source_ref": "",
                "target_ref": SOURCE_MODULE_MANIFEST_NAME,
                "missing_anchors": [],
                "reasons": ["manifest_body_text_in_receipt_forbidden"],
            }
        )
    for row in _rows(manifest_payload, "modules"):
        module_id = str(row.get("module_id") or "source_module")
        source_ref = str(row.get("source_ref") or "")
        target_ref = str(row.get("target_ref") or "")
        target = _target_path_for_ref(target_ref, public_root=public_root)
        row_findings: list[str] = []
        if row.get("material_class"):
            material_classes.add(str(row["material_class"]))

        if row.get("classification") != "copied_non_secret_macro_body":
            row_findings.append("classification_must_be_copied_non_secret_macro_body")
        if row.get("material_class") != "public_macro_tool_body":
            row_findings.append("material_class_must_be_public_macro_tool_body")
        if row.get("body_copied") is not True or row.get("body_in_receipt") is not False:
            row_findings.append("body_must_be_copied_without_receipt_body_text")
        if row.get("body_text_in_receipt") is True:
            row_findings.append("body_text_in_receipt_forbidden")
            findings.append(
                {
                    "error_code": (
                        "SPATIAL_SOURCE_MODULE_BODY_TEXT_IN_RECEIPT_FORBIDDEN"
                    ),
                    "module_id": module_id,
                    "source_ref": source_ref,
                    "target_ref": target_ref,
                    "missing_anchors": [],
                    "reasons": ["body_text_in_receipt_forbidden"],
                }
            )
        if not target.is_file():
            row_findings.append("target_ref_missing")

        target_digest = _sha256_hex(target) if target.is_file() else ""
        if target_digest and row.get("target_sha256") != target_digest:
            row_findings.append("target_sha256_mismatch")
        if target_digest and row.get("source_sha256") != target_digest:
            row_findings.append("source_target_sha256_mismatch")
        if row.get("sha256_match") is not True:
            row_findings.append("sha256_match_must_be_true")

        required_anchors = _strings(row.get("required_anchors"))
        target_text = target.read_text(encoding="utf-8") if target.is_file() else ""
        missing_anchors = [anchor for anchor in required_anchors if anchor not in target_text]
        if missing_anchors:
            row_findings.append("required_anchor_missing")

        source = _first_existing_source(source_ref, public_root=public_root)
        if source is not None:
            source_digest = _sha256_hex(source)
            if source_digest != target_digest:
                row_findings.append("available_source_digest_mismatch")
            if row.get("line_count") != _line_count(source):
                row_findings.append("source_line_count_mismatch")

        if row_findings:
            findings.append(
                {
                    "error_code": "SPATIAL_SOURCE_MODULE_IMPORT_INVALID",
                    "module_id": module_id,
                    "source_ref": source_ref,
                    "target_ref": target_ref,
                    "missing_anchors": missing_anchors,
                    "reasons": row_findings,
                }
            )
        module_results.append(
            {
                "module_id": module_id,
                "source_ref": source_ref,
                "target_ref": target_ref,
                "material_class": row.get("material_class"),
                "classification": row.get("classification"),
                "body_copied": row.get("body_copied"),
                "body_text_in_receipt": False,
                "body_in_receipt": row.get("body_in_receipt"),
                "source_sha256": row.get("source_sha256"),
                "target_sha256": row.get("target_sha256"),
                "target_body_digest": _sha256_ref(target) if target.is_file() else "",
                "line_count": row.get("line_count"),
                "anchor_count": row.get("anchor_count"),
                "required_anchors": required_anchors,
                "status": PASS if not row_findings else "blocked",
            }
        )

    status = PASS if module_results and not findings else "blocked"
    return {
        "status": status,
        "body_import_status": SOURCE_MODULE_IMPORT_STATUS
        if status == PASS
        else "blocked",
        "manifest_id": manifest_payload.get("manifest_id"),
        "bundle_id": manifest_payload.get("bundle_id"),
        "module_count": len(module_results),
        "verified_module_count": sum(1 for row in module_results if row["status"] == PASS),
        "module_ids": [row["module_id"] for row in module_results],
        "public_safe_body_material_ids": [row["module_id"] for row in module_results],
        "material_classes": sorted(material_classes),
        "modules": module_results,
        "body_text_in_receipt": False,
        "body_in_receipt": False,
        "findings": findings,
    }


def _source_open_body_import_summary(
    source_module_summary: dict[str, Any],
    *,
    manifest_ref: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_open_body_import_summary` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    material_ids = _strings(source_module_summary.get("public_safe_body_material_ids"))
    material_classes = _strings(source_module_summary.get("material_classes"))
    imported = source_module_summary.get("status") == PASS and bool(material_ids)
    return {
        "schema_version": SOURCE_OPEN_BODY_SCHEMA,
        "status": PASS if imported else str(source_module_summary.get("status") or ""),
        "source_import_class": SOURCE_IMPORT_CLASS if imported else "",
        "body_material_status": SOURCE_BODY_STATUS if imported else "",
        "body_material_count": len(material_ids) if imported else 0,
        "body_material_ids": material_ids if imported else [],
        "material_classes": material_classes if imported else [],
        "source_manifest_refs": [manifest_ref] if imported and manifest_ref else [],
        "aggregate_floor_ref": f"{manifest_ref}::modules"
        if imported and manifest_ref
        else "",
        "body_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "body_text_exported_in_workingness": False,
        "authority_ceiling": {
            "body_text_in_receipt": False,
            "private_video_exported": False,
            "raw_sensor_data_exported": False,
            "provider_payload_exported": False,
            "credential_or_account_bound_payload_exported": False,
            "live_robot_operation_authorized": False,
            "live_av_operation_authorized": False,
            "release_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported spatial world-model simulation bundle for copied macro "
            "Station geometry source bodies; receipts carry refs, digests, "
            "counts, and verdicts only."
        )
        if imported
        else "",
    }


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_payloads` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION]
    - Teleology: Implements `_finding` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION]
    - Teleology: Implements `_record` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION]
    - Teleology: Implements `_replay_policy_findings` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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


def _int_value(value: object) -> int | None:
    """
    [ACTION]
    - Teleology: Implements `_int_value` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def _gridworld_initial_state(scene: dict[str, Any], *, replay_id: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_gridworld_initial_state` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    actor_count = _int_value(scene.get("actor_count")) or 0
    actors = []
    for index in range(actor_count):
        actors.append(
            {
                "actor_id": f"{replay_id}::actor::{index}",
                "cell": [index % GRIDWORLD_WIDTH, index // GRIDWORLD_WIDTH],
            }
        )
    return {
        "schema_version": "spatial_toy_gridworld_state_v1",
        "world_id": f"toy_gridworld::{replay_id}",
        "width": GRIDWORLD_WIDTH,
        "height": GRIDWORLD_HEIGHT,
        "scene_state_ref": scene.get("scene_state_id"),
        "topology_ref": scene.get("topology_ref"),
        "actor_count": actor_count,
        "actors": actors,
    }


def _positive_int_field(payload: object, key: str, *, default: int = 1) -> int:
    """
    [ACTION]
    - Teleology: Implements `_positive_int_field` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, dict):
        return default
    value = _int_value(payload.get(key))
    return value if value is not None and value > 0 else default


def _gridworld_actor_count_delta(
    state: dict[str, Any],
    *,
    replay: dict[str, Any],
    action: dict[str, Any],
) -> int:
    """
    [ACTION]
    - Teleology: Implements `_gridworld_actor_count_delta` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    base_event_delta = _positive_int_field(action, "actor_count_delta", default=1)
    sensor_packet_count = len(_strings(replay.get("sensor_packet_refs")))
    consistency_budget = replay.get("consistency_budget")
    timestep_lag = _positive_int_field(
        consistency_budget,
        "max_timestep_lag",
        default=1,
    )
    replay_pressure = max(0, sensor_packet_count - timestep_lag - base_event_delta)
    source_actor_count = _int_value(state.get("actor_count")) or 0
    free_cell_count = max(0, GRIDWORLD_WIDTH * GRIDWORLD_HEIGHT - source_actor_count)
    return min(base_event_delta + replay_pressure, 4, free_cell_count)


def _gridworld_spawn_cells(
    state: dict[str, Any],
    *,
    replay: dict[str, Any],
    action: dict[str, Any],
    event: str,
    actor_count_delta: int,
) -> list[list[int]]:
    """
    [ACTION]
    - Teleology: Implements `_gridworld_spawn_cells` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    seed_payload = {
        "event": event,
        "replay_id": replay.get("replay_id"),
        "scene_state_ref": state.get("scene_state_ref"),
        "topology_ref": state.get("topology_ref"),
        "sensor_packet_refs": _strings(replay.get("sensor_packet_refs")),
        "consistency_budget": replay.get("consistency_budget"),
        "limitation_labels": _strings(replay.get("limitation_labels")),
        "source_actor_count": state.get("actor_count"),
    }
    seed = int(_json_digest(seed_payload).removeprefix("sha256:")[:12], 16)
    area = GRIDWORLD_WIDTH * GRIDWORLD_HEIGHT
    declared_cell = action.get("spawn_cell")
    if (
        isinstance(declared_cell, list)
        and len(declared_cell) == 2
        and all(_int_value(coord) is not None for coord in declared_cell)
    ):
        declared_x = int(declared_cell[0]) % GRIDWORLD_WIDTH
        declared_y = int(declared_cell[1]) % GRIDWORLD_HEIGHT
        base_cursor = declared_y * GRIDWORLD_WIDTH + declared_x
    else:
        base_cursor = 0
    occupied = {
        tuple(actor.get("cell"))
        for actor in _rows({"actors": state.get("actors", [])}, "actors")
        if isinstance(actor.get("cell"), list) and len(actor["cell"]) == 2
    }
    cells: list[list[int]] = []
    cursor = (base_cursor + seed) % area
    while len(cells) < actor_count_delta:
        cell = [cursor % GRIDWORLD_WIDTH, cursor // GRIDWORLD_WIDTH]
        cell_key = tuple(cell)
        if cell_key not in occupied and cell not in cells:
            cells.append(cell)
        cursor = (cursor + 7) % area
    return cells


def _gridworld_step(
    state: dict[str, Any],
    *,
    replay: dict[str, Any],
    event: str,
    replay_id: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_gridworld_step` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    action = EVENT_GRIDWORLD_ACTIONS.get(event)
    actors = [dict(actor) for actor in _rows({"actors": state.get("actors", [])}, "actors")]
    if action is None:
        return {
            "status": "blocked",
            "reason": "unknown_counterfactual_event",
            "event": event,
            "state": state,
            "next_state": state,
            "transition_diff": {"actor_count_delta": 0},
        }
    actor_count_delta = _gridworld_actor_count_delta(
        state,
        replay=replay,
        action=action,
    )
    spawn_cells = _gridworld_spawn_cells(
        state,
        replay=replay,
        action=action,
        event=event,
        actor_count_delta=actor_count_delta,
    )
    new_actor_id = f"{replay_id}::event::{event}"
    for index, cell in enumerate(spawn_cells):
        actors.append(
            {
                "actor_id": f"{new_actor_id}::{index}",
                "cell": cell,
            }
        )
    next_state = {
        **state,
        "state_ref": f"actual_gridworld_state::{replay_id}",
        "actors": actors,
        "actor_count": len(actors),
    }
    transition_diff = {
        "actor_count_delta": len(actors) - int(state.get("actor_count") or 0),
        "event_delta_label": action["event_delta_label"],
        "spawn_cell": spawn_cells[0] if spawn_cells else None,
        "spawn_cells": spawn_cells,
        "input_drivers": {
            "base_event_actor_count_delta": action["actor_count_delta"],
            "sensor_packet_count": len(_strings(replay.get("sensor_packet_refs"))),
            "max_timestep_lag": _positive_int_field(
                replay.get("consistency_budget"),
                "max_timestep_lag",
                default=1,
            ),
            "source_actor_count": _int_value(state.get("actor_count")) or 0,
            "topology_ref": state.get("topology_ref"),
        },
        "within_consistency_budget": True,
    }
    return {
        "status": PASS,
        "event": event,
        "state": state,
        "next_state": next_state,
        "transition_diff": transition_diff,
    }


def _state_transition_analysis(
    *,
    scene_states: list[dict[str, Any]],
    replays: list[dict[str, Any]],
    transitions: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    [ACTION]
    - Teleology: Implements `_state_transition_analysis` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    scene_by_ref = {
        str(row.get("scene_state_id")): row
        for row in scene_states
        if row.get("scene_state_id")
    }
    transitions_by_replay: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in transitions:
        transitions_by_replay[str(row.get("replay_id") or "")].append(row)

    transition_rows: list[dict[str, Any]] = []
    for replay in replays:
        replay_id = str(replay.get("replay_id") or "counterfactual_replay")
        replay_transitions = transitions_by_replay.get(replay_id, [])
        if len(replay_transitions) != 1:
            findings.append(
                _finding(
                    "SPATIAL_STATE_TRANSITION_ROW_REQUIRED",
                    "each counterfactual replay must resolve to exactly one public state-transition row",
                    case_id="positive_fixture",
                    subject_id=replay_id,
                    subject_kind="state_transition",
                )
            )
            continue

        transition = replay_transitions[0]
        scene_ref = str(replay.get("scene_state_ref") or "")
        scene = scene_by_ref.get(scene_ref)
        predicted_state = transition.get("predicted_state")
        transition_diff = transition.get("transition_diff")
        oracle_check = transition.get("oracle_state_check")
        row_findings: list[str] = []

        if scene is None:
            row_findings.append("source_scene_state_unresolved")
        if transition.get("scene_state_ref") != scene_ref:
            row_findings.append("scene_state_ref_mismatch")
        if transition.get("action_trace_ref") != replay.get("action_trace_ref"):
            row_findings.append("action_trace_ref_mismatch")
        if transition.get("counterfactual_event") != replay.get("counterfactual_event"):
            row_findings.append("counterfactual_event_mismatch")
        if not isinstance(predicted_state, dict):
            row_findings.append("predicted_state_body_required")
            predicted_state = {}
        if not isinstance(transition_diff, dict):
            row_findings.append("transition_diff_body_required")
            transition_diff = {}
        if not isinstance(oracle_check, dict):
            row_findings.append("oracle_state_check_body_required")
            oracle_check = {}

        source_actor_count = _int_value(scene.get("actor_count")) if scene else None
        predicted_actor_count = _int_value(predicted_state.get("actor_count"))
        diff_actor_delta = _int_value(transition_diff.get("actor_count_delta"))
        event = str(replay.get("counterfactual_event") or "")
        initial_gridworld = (
            _gridworld_initial_state(scene, replay_id=replay_id)
            if scene is not None
            else {}
        )
        gridworld_step = (
            _gridworld_step(
                initial_gridworld,
                replay=replay,
                event=event,
                replay_id=replay_id,
            )
            if initial_gridworld
            else {"status": "blocked", "reason": "source_scene_state_unresolved"}
        )
        actual_next_state = gridworld_step.get("next_state")
        actual_transition_diff = gridworld_step.get("transition_diff")
        actual_actor_count = (
            _int_value(actual_next_state.get("actor_count"))
            if isinstance(actual_next_state, dict)
            else None
        )
        actual_actor_delta = (
            _int_value(actual_transition_diff.get("actor_count_delta"))
            if isinstance(actual_transition_diff, dict)
            else None
        )
        if predicted_state.get("state_ref") != replay.get("predicted_state_ref"):
            row_findings.append("predicted_state_ref_mismatch")
        if transition_diff.get("diff_ref") != replay.get("transition_diff_ref"):
            row_findings.append("transition_diff_ref_mismatch")
        if oracle_check.get("check_ref") != replay.get("oracle_state_check_ref"):
            row_findings.append("oracle_state_check_ref_mismatch")
        if oracle_check.get("status") != PASS:
            row_findings.append("oracle_state_check_must_pass")
        if transition_diff.get("within_consistency_budget") is not True:
            row_findings.append("transition_diff_must_be_within_consistency_budget")
        if gridworld_step.get("status") != PASS:
            row_findings.append("gridworld_step_must_execute")
        if (
            source_actor_count is None
            or predicted_actor_count is None
            or diff_actor_delta is None
            or actual_actor_count is None
            or actual_actor_delta is None
        ):
            row_findings.append("actor_count_transition_numeric_fields_required")
        else:
            if predicted_actor_count != actual_actor_count:
                row_findings.append("predicted_state_actor_count_mismatch")
            if diff_actor_delta != actual_actor_delta:
                row_findings.append("transition_diff_actor_delta_mismatch")
            if predicted_actor_count - source_actor_count != diff_actor_delta:
                row_findings.append("actor_count_delta_mismatch")
        if (
            isinstance(actual_transition_diff, dict)
            and transition_diff.get("event_delta_label")
            != actual_transition_diff.get("event_delta_label")
        ):
            row_findings.append("transition_diff_event_label_mismatch")
        if (
            isinstance(actual_transition_diff, dict)
            and transition_diff.get("spawn_cell") is not None
            and transition_diff.get("spawn_cell")
            != actual_transition_diff.get("spawn_cell")
        ):
            row_findings.append("transition_diff_spawn_cell_mismatch")
        if (
            isinstance(actual_transition_diff, dict)
            and transition_diff.get("spawn_cells") is not None
            and transition_diff.get("spawn_cells")
            != actual_transition_diff.get("spawn_cells")
        ):
            row_findings.append("transition_diff_spawn_cells_mismatch")
        if transition.get("body_in_receipt") is not False:
            row_findings.append("transition_body_must_stay_out_of_receipt")

        if row_findings:
            findings.append(
                _finding(
                    "SPATIAL_STATE_TRANSITION_SIMULATION_MISMATCH",
                    "state-transition rows must match source scene state, deterministic event delta, transition diff, and oracle check refs",
                    case_id="positive_fixture",
                    subject_id=replay_id,
                    subject_kind="state_transition",
                )
            )
        transition_rows.append(
            {
                "replay_id": replay_id,
                "scene_state_ref": scene_ref,
                "predicted_state_ref": replay.get("predicted_state_ref"),
                "transition_diff_ref": replay.get("transition_diff_ref"),
                "oracle_state_check_ref": replay.get("oracle_state_check_ref"),
                "source_actor_count": source_actor_count,
                "predicted_actor_count": predicted_actor_count,
                "actual_actor_count": actual_actor_count,
                "actor_count_delta": diff_actor_delta,
                "actual_actor_count_delta": actual_actor_delta,
                "gridworld_step_executed": gridworld_step.get("status") == PASS,
                "gridworld_world_ref": initial_gridworld.get("world_id")
                if isinstance(initial_gridworld, dict)
                else "",
                "actual_next_state_ref": actual_next_state.get("state_ref")
                if isinstance(actual_next_state, dict)
                else "",
                "actual_spawn_cell": actual_transition_diff.get("spawn_cell")
                if isinstance(actual_transition_diff, dict)
                else None,
                "actual_spawn_cells": actual_transition_diff.get("spawn_cells")
                if isinstance(actual_transition_diff, dict)
                else [],
                "simulation_passed": not row_findings,
                "findings": row_findings,
                "body_in_receipt": False,
            }
        )

    return (
        {
            "status": PASS if replays and transitions and not findings else "blocked",
            "analysis_kind": "deterministic_public_metadata_state_transition_check",
            "runtime_kind": "deterministic_toy_gridworld_step",
            "gridworld_dimensions": [GRIDWORLD_WIDTH, GRIDWORLD_HEIGHT],
            "transition_count": len(transitions),
            "replay_transition_count": len(transition_rows),
            "predicted_state_body_count": sum(
                1
                for row in transitions
                if isinstance(row.get("predicted_state"), dict)
            ),
            "transition_diff_body_count": sum(
                1
                for row in transitions
                if isinstance(row.get("transition_diff"), dict)
            ),
            "oracle_state_check_body_count": sum(
                1
                for row in transitions
                if isinstance(row.get("oracle_state_check"), dict)
            ),
            "deterministic_simulation_pass_count": sum(
                1 for row in transition_rows if row["simulation_passed"]
            ),
            "gridworld_step_count": sum(
                1 for row in transition_rows if row["gridworld_step_executed"]
            ),
            "predicted_actual_match_count": sum(
                1
                for row in transition_rows
                if row["predicted_actor_count"] == row["actual_actor_count"]
                and row["actor_count_delta"] == row["actual_actor_count_delta"]
            ),
            "actual_actor_count_delta_values": sorted(
                {
                    row["actual_actor_count_delta"]
                    for row in transition_rows
                    if row["actual_actor_count_delta"] is not None
                }
            ),
            "max_actual_actor_count_delta": max(
                [
                    row["actual_actor_count_delta"]
                    for row in transition_rows
                    if row["actual_actor_count_delta"] is not None
                ]
                or [0]
            ),
            "transition_rows": sorted(
                transition_rows,
                key=lambda row: row["replay_id"],
            ),
            "body_in_receipt": False,
        },
        findings,
    )


def _required_policy_ok(policy: dict[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_required_policy_ok` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
    """
    [ACTION]
    - Teleology: Implements `_build_result` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    public_root = _public_root_for_path(input_dir)
    simulation_protocol = payloads.get("simulation_protocol", {})
    replay_policy = payloads.get("replay_policy", {})
    scene_states = _rows(payloads.get("scene_states", {}), "scene_states")
    replays = _rows(payloads.get("counterfactual_replays", {}), "counterfactual_replays")
    state_transitions = _rows(
        payloads.get("state_transitions", {}),
        "state_transitions",
    )
    source_module_summary = _source_module_manifest_result(
        payloads.get("source_module_manifest"),
        public_root=public_root,
    )
    manifest_ref = (
        _display(input_dir / SOURCE_MODULE_MANIFEST_NAME, public_root=public_root)
        if (input_dir / SOURCE_MODULE_MANIFEST_NAME).is_file()
        else ""
    )
    source_open_body_imports = _source_open_body_import_summary(
        source_module_summary,
        manifest_ref=manifest_ref,
    )
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
    state_transition_analysis, state_transition_findings = _state_transition_analysis(
        scene_states=scene_states,
        replays=replays,
        transitions=state_transitions,
    )
    positive_findings.extend(state_transition_findings)
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
        and state_transition_analysis["status"] == PASS
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
        and source_module_summary["status"] != "blocked"
    )

    scan = scan_paths(
        [
            *_input_paths(input_dir, include_negative=include_negative),
            *_source_module_paths(
                payloads.get("source_module_manifest"),
                public_root=public_root,
            ),
        ],
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
        "state_transition_analysis": state_transition_analysis,
        "simulation_summary": {
            "scene_state_count": len(scene_states),
            "replay_count": len(replays),
            "state_transition_count": len(state_transitions),
            "predicted_state_body_count": state_transition_analysis[
                "predicted_state_body_count"
            ],
            "deterministic_simulation_pass_count": state_transition_analysis[
                "deterministic_simulation_pass_count"
            ],
            "gridworld_step_count": state_transition_analysis["gridworld_step_count"],
            "predicted_actual_match_count": state_transition_analysis[
                "predicted_actual_match_count"
            ],
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
        "source_module_import_status": source_module_summary["body_import_status"],
        "source_module_summary": source_module_summary,
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports[
            "body_material_count"
        ],
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
    """
    [ACTION]
    - Teleology: Implements `_board` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
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
        "state_transition_count": summary.get("state_transition_count", 0)
        if isinstance(summary, dict)
        else 0,
        "predicted_state_body_count": summary.get("predicted_state_body_count", 0)
        if isinstance(summary, dict)
        else 0,
        "deterministic_simulation_pass_count": summary.get(
            "deterministic_simulation_pass_count",
            0,
        )
        if isinstance(summary, dict)
        else 0,
        "gridworld_step_count": summary.get("gridworld_step_count", 0)
        if isinstance(summary, dict)
        else 0,
        "predicted_actual_match_count": summary.get(
            "predicted_actual_match_count",
            0,
        )
        if isinstance(summary, dict)
        else 0,
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
        "source_module_import_status": result.get("source_module_import_status"),
        "source_module_count": (result.get("source_module_summary") or {}).get(
            "module_count", 0
        ),
        "source_open_body_imports": result.get("source_open_body_imports"),
        "body_copied_material_count": result.get("body_copied_material_count", 0),
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_write_receipts` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
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
        "source_module_import_status": result.get("source_module_import_status"),
        "source_module_count": (result.get("source_module_summary") or {}).get(
            "module_count", 0
        ),
        "source_open_body_imports": result.get("source_open_body_imports"),
        "body_copied_material_count": result.get("body_copied_material_count", 0),
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
        "source_open_body_imports": result.get("source_open_body_imports"),
        "body_copied_material_count": result.get("body_copied_material_count", 0),
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
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    result["freshness_basis"] = _freshness_basis(
        Path(input_dir),
        command=command,
        input_mode="fixture",
    )
    result["receipt_reused"] = False
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
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_simulation_bundle` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    source_input = Path(input_dir)
    freshness_basis = _freshness_basis(
        source_input,
        command=command,
        input_mode="exported_spatial_world_model_simulation_bundle",
    )
    bundle_path = out / BUNDLE_RESULT_NAME
    if reuse_fresh_receipt:
        cached = _fresh_spatial_simulation_bundle_receipt(
            bundle_path,
            freshness_basis,
            command=command,
        )
        if cached is not None:
            return cached
    result = _build_result(
        source_input,
        command=command,
        input_mode="exported_spatial_world_model_simulation_bundle",
        include_negative=False,
    )
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": (
            "exported_spatial_world_model_simulation_bundle_"
            "validation_result_v1"
        ),
        "freshness_basis": freshness_basis,
        "receipt_reused": False,
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    normalized_payload = normalize_public_receipt_paths(payload)
    write_json_atomic(bundle_path, normalized_payload)
    return normalized_payload


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    summary = result.get("simulation_summary") or {}
    negatives = result.get("negative_case_summary") or {}
    source_summary = result.get("source_module_summary") or {}
    source_open_body = result.get("source_open_body_imports") or {}
    secret_scan = result.get("secret_exclusion_scan") or {}
    freshness = result.get("freshness_basis") or {}
    omitted = [
        key
        for key in CARD_OMITTED_FULL_PAYLOAD_KEYS
        if key in result and result.get(key) not in (None, {}, [])
    ]
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": ORGAN_ID,
        "input_mode": result.get("input_mode"),
        "command": result.get("command"),
        "command_speed": {
            "compact_card": True,
            "receipt_reused": bool(result.get("receipt_reused")),
            "freshness_digest": freshness.get("digest"),
            "freshness_checked_path_count": freshness.get("input_count", 0),
            "freshness_missing_path_count": freshness.get("missing_input_count", 0),
            "full_receipt_stdout_omitted": True,
            "rerun_without_card_for_status_only": True,
        },
        "simulation": {
            "scene_state_count": summary.get("scene_state_count", 0),
            "replay_count": summary.get("replay_count", 0),
            "state_transition_count": summary.get("state_transition_count", 0),
            "predicted_state_body_count": summary.get(
                "predicted_state_body_count",
                0,
            ),
            "deterministic_simulation_pass_count": summary.get(
                "deterministic_simulation_pass_count",
                0,
            ),
            "gridworld_step_count": summary.get("gridworld_step_count", 0),
            "predicted_actual_match_count": summary.get(
                "predicted_actual_match_count",
                0,
            ),
            "transition_diff_count": summary.get("transition_diff_count", 0),
            "oracle_state_check_count": summary.get("oracle_state_check_count", 0),
            "sensor_packet_ref_count": summary.get("sensor_packet_ref_count", 0),
            "rare_event_coverage_count": summary.get("rare_event_coverage_count", 0),
            "fidelity_limit_count": summary.get("fidelity_limit_count", 0),
        },
        "source_modules": {
            "source_module_import_status": result.get("source_module_import_status"),
            "module_count": source_summary.get("module_count", 0),
            "verified_module_count": source_summary.get("verified_module_count", 0),
            "body_material_count": source_open_body.get("body_material_count", 0),
            "body_material_status": source_open_body.get(
                "body_material_status", ""
            ),
            "body_in_receipt": bool(source_open_body.get("body_in_receipt")),
            "body_text_exported_in_receipts": bool(
                source_open_body.get("body_text_exported_in_receipts")
            ),
            "body_text_exported_in_workingness": bool(
                source_open_body.get("body_text_exported_in_workingness")
            ),
        },
        "negative_case_coverage": {
            "expected_negative_case_count": negatives.get(
                "expected_negative_case_count", 0
            ),
            "observed_negative_case_count": negatives.get(
                "observed_negative_case_count", 0
            ),
            "expected_missing_count": len(negatives.get("expected_missing") or {}),
        },
        "validation": {
            "finding_count": result.get("finding_count", 0),
            "secret_exclusion_status": secret_scan.get("status"),
            "secret_exclusion_hit_count": len(secret_scan.get("findings") or []),
            "unsafe_payload_bodies_in_receipt": bool(
                result.get("unsafe_payload_bodies_in_receipt")
            ),
            "release_authorized": bool(result.get("release_authorized")),
        },
        "body_floor": {
            "body_copied_material_count": result.get(
                "body_copied_material_count", 0
            ),
            "source_open_body_policy": result.get("source_open_body_policy"),
            "receipt_exports_body_text": False,
        },
        "authority_boundary": {
            "metadata_projection_only": True,
            "private_video_exported": False,
            "raw_sensor_data_exported": False,
            "live_operation_authorized": False,
            "real_world_location_claim_authorized": False,
            "release_authorized": False,
        },
        "receipt_paths": result.get("receipt_paths", []),
        "omission_receipt": {
            "omitted_full_payload_keys": omitted,
            "reason": (
                "Card output preserves command-speed, count, freshness, and "
                "boundary fields while the full receipt on disk keeps row "
                "detail."
            ),
            "drilldown": (
                "rerun without --card or inspect the written "
                f"{BUNDLE_RESULT_NAME} receipt"
            ),
        },
    }


def _parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `_parser` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog="spatial_world_model_counterfactual_simulation_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-simulation-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        result = run(
            args.input,
            args.out,
            command=(
                "python -m microcosm_core.organs."
                "spatial_world_model_counterfactual_simulation_replay run"
                f"{card_suffix}"
            ),
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-simulation-bundle":
        result = run_simulation_bundle(
            args.input,
            args.out,
            command=(
                "python -m microcosm_core.organs."
                "spatial_world_model_counterfactual_simulation_replay "
                f"run-simulation-bundle{card_suffix}"
            ),
            reuse_fresh_receipt=args.card,
        )
    else:  # pragma: no cover
        raise ValueError(args.action)
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
