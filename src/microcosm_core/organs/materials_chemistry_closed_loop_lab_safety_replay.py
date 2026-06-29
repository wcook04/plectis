"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, PUBLIC_SURFACE_NAME, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, ACCEPTANCE_RECEIPT_REL, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, SAFETY_VERDICT_SCHEMA_VERSION, CARD_OMITTED_FULL_PAYLOAD_KEYS, BODY_IMPORT_STATUS, BODY_IMPORT_CLASSIFICATION, PRODUCT_PATH_ROLE, SOURCE_MODULE_MANIFEST_NAME, SOURCE_IMPORT_CLASS, SOURCE_MODULE_IMPORT_STATUS, SOURCE_OPEN_BODY_SCHEMA, HASH_CHUNK_SIZE, NUMERIC_REPLAY_SCORE_FIELD, NUMERIC_REPLAY_ASSAY_VALUE_FIELD, NUMERIC_REPLAY_ACTIVE_LEARNING_FIELD, NUMERIC_REPLAY_SAFETY_GATE_FIELD, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.macro_tools.lab_evolve_replay, microcosm_core.private_state_scan, microcosm_core.receipts, microcosm_core.schemas
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.lab_evolve_replay import (
    SOURCE_REFS as LAB_EVOLVE_SOURCE_REFS,
)
from microcosm_core.macro_tools.lab_evolve_replay import (
    TARGET_REFS as LAB_EVOLVE_TARGET_REFS,
)
from microcosm_core.macro_tools.lab_evolve_replay import (
    TARGET_SYMBOL_REFS as LAB_EVOLVE_TARGET_SYMBOL_REFS,
)
from microcosm_core.macro_tools.lab_evolve_replay import (
    build_materials_lab_evolve_replay,
)
from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "materials_chemistry_closed_loop_lab_safety_replay"
PUBLIC_SURFACE_NAME = "materials_chemistry_artifact_safety_refusal_validator"
FIXTURE_ID = "first_wave.materials_chemistry_closed_loop_lab_safety_replay"
VALIDATOR_ID = "validator.microcosm.organs.materials_chemistry_closed_loop_lab_safety_replay"

RESULT_NAME = "materials_chemistry_closed_loop_lab_safety_replay_result.json"
BOARD_NAME = "materials_chemistry_closed_loop_lab_safety_replay_board.json"
VALIDATION_RECEIPT_NAME = (
    "materials_chemistry_closed_loop_lab_safety_replay_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "materials_chemistry_closed_loop_lab_safety_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_materials_lab_safety_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "materials_lab_safety_command_card_v1"
SAFETY_VERDICT_SCHEMA_VERSION = "materials_lab_safety_verdict_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "candidate_materials",
    "experiments",
    "simulator_assays",
    "active_learning_decisions",
    "positive_findings",
    "negative_case_findings",
    "public_lab_evolve_replay_rows",
    "secret_exclusion_scan",
    "authority_ceiling",
    "anti_claim",
    "body_import_verification",
    "source_module_imports",
    "source_open_body_imports",
    "safe_to_show",
    "materials_lab_safety_board",
)
BODY_IMPORT_STATUS = "source_faithful_refactor_landed"
BODY_IMPORT_CLASSIFICATION = "source_faithful_refactor"
PRODUCT_PATH_ROLE = "artifact_safety_refusal_validator"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_MODULE_IMPORT_STATUS = "copied_non_secret_materials_lab_macro_body_landed"
SOURCE_OPEN_BODY_SCHEMA = (
    "materials_chemistry_closed_loop_lab_safety_replay_"
    "source_open_body_imports_v1"
)
HASH_CHUNK_SIZE = 1024 * 1024
NUMERIC_REPLAY_SCORE_FIELD = "public_numeric_replay_score"
NUMERIC_REPLAY_ASSAY_VALUE_FIELD = "public_assay_proxy_value"
NUMERIC_REPLAY_ACTIVE_LEARNING_FIELD = "public_active_learning_score"
NUMERIC_REPLAY_SAFETY_GATE_FIELD = "public_safety_gate_score"
NUMERIC_REPLAY_SELECTION_RULE = (
    "max_weighted_public_assay_active_learning_and_safety_gate_score"
)
NUMERIC_REPLAY_VERDICT_BASIS = (
    "recomputed_from_public_assay_active_learning_and_safety_gate_fixture_numbers"
)
NUMERIC_REPLAY_REALNESS_SCHEMA_VERSION = "materials_lab_numeric_replay_realness_v1"
NUMERIC_REPLAY_MIN_SAFETY_GATE = 0.70
NUMERIC_REPLAY_SCORE_WEIGHTS = {
    "assay_proxy_value": 0.45,
    "active_learning_score": 0.35,
    "safety_gate_score": 0.20,
}
NUMERIC_REPLAY_TOLERANCE = 1e-9
NUMERIC_REPLAY_EXPECTED_SELECTED_FIELDS = (
    "expected_selected_candidate_material_id",
    "expected_next_pick_candidate_material_id",
    "baked_expected_selected_candidate_material_id",
)
EXPECTED_SOURCE_MODULE_DIGESTS = {
    "materials_lab_evolve_failure_replay_specimen_body_import": (
        "sha256:d615e3cc9491a58d4f094148378d5a155056e527afb57a0b6d2f823eb7143179"
    ),
    "materials_lab_evolve_replay_graph_body_import": (
        "sha256:cedbcfcccd7bca3afb8b98745558d6fc1328c893c4d96a39a9f5e19c8edab7df"
    ),
    "materials_lab_evolve_receipt_body_import": (
        "sha256:3eada5145a7b91d08b566bbb5f76f2ffab27eaf41ae680e9a987228252b699b5"
    ),
    "laboratory_standard_body_import": (
        "sha256:f51a81b1004b6fd8b58b69b720c8670d4aced7f2605437494d26a3897582557d"
    ),
}
PUBLIC_SAFE_SOURCE_BODY_CLASSES = frozenset(
    {
        "public_macro_control_plane_body",
        "public_macro_pattern_body",
        "public_macro_receipt_body",
        "public_macro_standard_body",
        "public_macro_tool_body",
        "public_standard_body",
    }
)

INPUT_NAMES = (
    "lab_safety_protocol.json",
    "replay_policy.json",
    "candidate_materials.json",
    "experiment_dag.json",
    "simulator_assays.json",
    "active_learning_decisions.json",
)
NEGATIVE_INPUT_NAMES = (
    "wetlab_protocol_steps.json",
    "hazardous_synthesis_steps.json",
    "reagent_amounts.json",
    "controlled_or_bioactive_target.json",
    "live_lab_credentials.json",
    "robot_command_execution.json",
    "private_lab_notebook_export.json",
    "discovery_claim.json",
)
EXPECTED_NEGATIVE_CASES = {
    "wetlab_protocol_steps": ["MATERIALS_WETLAB_PROTOCOL_FORBIDDEN"],
    "hazardous_synthesis_steps": ["MATERIALS_HAZARDOUS_SYNTHESIS_FORBIDDEN"],
    "reagent_amounts": ["MATERIALS_REAGENT_AMOUNT_FORBIDDEN"],
    "controlled_or_bioactive_target": [
        "MATERIALS_CONTROLLED_OR_BIOACTIVE_TARGET_FORBIDDEN"
    ],
    "live_lab_credentials": ["MATERIALS_LIVE_LAB_CREDENTIAL_FORBIDDEN"],
    "robot_command_execution": ["MATERIALS_ROBOT_COMMAND_FORBIDDEN"],
    "private_lab_notebook_export": ["MATERIALS_PRIVATE_LAB_NOTEBOOK_FORBIDDEN"],
    "discovery_claim": ["MATERIALS_DISCOVERY_CLAIM_FORBIDDEN"],
}

REQUIRED_CANDIDATE_FIELDS = (
    "candidate_material_id",
    "target_property_label",
    "literature_capsule_ref",
    "safety_screen_ref",
    "non_actionable_literature_capsule",
    "controlled_substance_target",
    "bioactivity_target",
    "discovery_claim",
    "body_in_receipt",
)
REQUIRED_EXPERIMENT_FIELDS = (
    "experiment_id",
    "candidate_material_ref",
    "safety_screen_ref",
    "action_class",
    "assay_ref",
    "result_table_ref",
    "failure_taxonomy_ref",
    "budget_ref",
    "cold_replay_ref",
    "simulator_only",
    "wetlab_protocol_exported",
    "hazardous_synthesis_steps_exported",
    "reagent_amounts_included",
    "robot_command_authorized",
    "live_lab_credentials_present",
    "private_lab_notebook_exported",
    "release_authorized",
    "body_in_receipt",
)
REQUIRED_ASSAY_FIELDS = (
    "assay_id",
    "experiment_ref",
    "candidate_material_ref",
    "simulator_only",
    "property_proxy",
    "result_table_ref",
    "uncertainty_label",
    "live_assay_data_exported",
    "discovery_claim",
    "body_in_receipt",
)
REQUIRED_DECISION_FIELDS = (
    "decision_id",
    "experiment_ref",
    "candidate_material_ref",
    "next_action_class",
    "decision_rationale_ref",
    "uncertainty_label",
    "cold_replay_ref",
    "simulator_only",
    "live_robot_command_emitted",
    "discovery_claim",
    "body_in_receipt",
)
REQUIRED_PROJECTION_PROTOCOL_FIELDS = (
    "copied",
    "reimplemented",
    "cleaned",
    "omitted",
    "public_refactor",
    "authority_ceiling",
    "validation_proves",
)
ALLOWED_ACTION_CLASSES = {
    "screen_candidate",
    "simulate_assay",
    "update_surrogate_model",
    "choose_next_simulation",
}
PRIVATE_NEEDLES = (
    "/Users/",
    "src/ai_workflow",
    "sk-",
    "PRIVATE_LAB_NOTEBOOK",
    "wetlab_step_body",
    "reagent_quantity_body",
    "robot_command_payload",
    "credential_secret",
)
AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "materials_chemistry_artifact_safety_refusal_validator",
    "metadata_projection_only": True,
    "simulator_only": True,
    "wetlab_protocol_authorized": False,
    "hazardous_synthesis_authorized": False,
    "reagent_amounts_authorized": False,
    "controlled_substance_target_authorized": False,
    "bioactivity_target_authorized": False,
    "live_lab_credentials_authorized": False,
    "robot_command_authorized": False,
    "private_lab_notebook_exported": False,
    "live_assay_data_exported": False,
    "discovery_claim_authorized": False,
    "benchmark_score_claim_authorized": False,
    "release_authorized": False,
    "hosted_public_authorized": False,
    "publication_authorized": False,
    "provider_calls_authorized": False,
}
ANTI_CLAIM = (
    "Materials chemistry artifact safety/refusal validator exposes a "
    "source-faithful public Lab/Evolve failure-replay graph over body-free "
    "simulator rows: candidate materials, safety screens, simulated assays, "
    "active-learning decisions, cold replay refs, failure classes, restart "
    "points, source capsule hashes, and teachings. It is a safety/refusal "
    "validator, not a wetlab loop or discovery lab: it does not export wetlab "
    "protocols, hazardous synthesis steps, reagent amounts, controlled or "
    "bioactive targets, live lab credentials, robot commands, private lab "
    "notebooks, live assay data, discovery claims, benchmark scores, or "
    "release authority."
)

SURFACE_REFRAME = {
    "stable_organ_id": ORGAN_ID,
    "public_surface_name": PUBLIC_SURFACE_NAME,
    "renamed_from_public_promise": "materials_chemistry_closed_loop_lab_safety_replay",
    "reframe_reason": "no_wetlab_loop_authorized_artifact_safety_refusal_validation_only",
    "forbidden_name_promises": [
        "closed_loop_wetlab_execution",
        "materials_discovery_lab",
        "robot_command_execution",
    ],
    "compatibility_note": "stable organ id remains for registry, fixture, CLI, and receipt compatibility",
    "body_in_receipt": False,
}


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_display` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_rows` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_strings` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    return paths


def _code_freshness_paths() -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_code_freshness_paths` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    core_root = Path(__file__).resolve().parents[1]
    return [
        Path(__file__).resolve(),
        core_root / "macro_tools/lab_evolve_replay.py",
    ]


def _sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _stable_digest(payload: object) -> str:
    """
    [ACTION]
    - Teleology: Implements `_stable_digest` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _source_module_manifest_path(input_dir: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_path` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return input_dir / SOURCE_MODULE_MANIFEST_NAME


def _source_module_target_path(
    target_ref: str,
    *,
    input_dir: Path,
    public_root: Path,
) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_target_path` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    normalized = target_ref.removeprefix("microcosm-substrate/")
    if normalized.startswith("source_modules/"):
        return input_dir / normalized
    return public_root / normalized


def _source_module_paths(input_dir: Path, *, public_root: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_paths` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return []
    paths = [manifest_path]
    try:
        manifest = read_json_strict(manifest_path)
    except Exception:
        return paths
    for row in _rows(manifest, "modules"):
        target_ref = str(row.get("target_ref") or row.get("path") or "")
        if target_ref:
            paths.append(
                _source_module_target_path(
                    target_ref,
                    input_dir=input_dir,
                    public_root=public_root,
                )
            )
    return paths


def _scan_paths_for_input(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_scan_paths_for_input` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    return [
        *_input_paths(input_dir, include_negative=include_negative),
        *_source_module_paths(input_dir, public_root=public_root),
    ]


def _freshness_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_freshness_paths` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source = Path(input_dir)
    public_root = _public_root_for_path(source)
    return [
        *_scan_paths_for_input(source, include_negative=include_negative),
        *_code_freshness_paths(),
        public_root / "core/private_state_forbidden_classes.json",
    ]


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_freshness_basis` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source = Path(input_dir)
    if not source.is_absolute():
        source = Path.cwd() / source
    public_root = _public_root_for_path(source)

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[Path] = set()
    for path in _freshness_paths(source, include_negative=include_negative):
        key = path.resolve(strict=False)
        if key in seen:
            continue
        seen.add(key)
        display = _display(path, public_root=public_root)
        if path.is_file():
            rows.append(
                {
                    "path": display,
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        else:
            missing.append(display)

    validator_schema_version = (
        "materials_chemistry_closed_loop_lab_safety_replay_result_v1"
        if include_negative
        else "exported_materials_lab_safety_bundle_validation_result_v1"
    )
    basis_digest = hashlib.sha256(
        json.dumps(
            {
                "card_schema_version": CARD_SCHEMA_VERSION,
                "include_negative": include_negative,
                "inputs": rows,
                "missing_inputs": missing,
                "validator_schema_version": validator_schema_version,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "materials_lab_safety_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_lab_bundle_receipt(
    input_dir: Path,
    out_dir: Path,
    *,
    command: str,
) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Implements `_fresh_lab_bundle_receipt` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    path = out_dir / BUNDLE_RESULT_NAME
    if not path.is_file():
        return None
    try:
        payload = read_json_strict(path)
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != (
        "exported_materials_lab_safety_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("status") != PASS:
        return None
    if payload.get("input_mode") != "exported_materials_lab_safety_bundle":
        return None
    if payload.get("command") != command:
        return None
    basis = _freshness_basis(input_dir, include_negative=False)
    existing_basis = payload.get("freshness_basis")
    if not isinstance(existing_basis, dict):
        return None
    if existing_basis.get("basis_digest") != basis["basis_digest"]:
        return None
    if basis["missing_path_count"]:
        return None
    reused = dict(payload)
    reused["freshness_basis"] = basis
    reused["receipt_reused"] = True
    return reused


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_payloads` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_finding` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
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
        "body_in_receipt": False,
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
    - Teleology: Implements `_record` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
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


def _missing_fields(
    row: dict[str, Any],
    fields: tuple[str, ...],
    *,
    code: str,
    kind: str,
    row_id: str,
    case_id: str,
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_missing_fields` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    for field in fields:
        if field not in row:
            _record(
                findings,
                observed,
                code,
                f"{kind} row is missing required field {field}",
                case_id=case_id,
                subject_id=row_id,
                subject_kind=kind,
            )
    return findings


def _has_private_body(row: dict[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_has_private_body` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    encoded = json.dumps(row, sort_keys=True)
    return any(needle in encoded for needle in PRIVATE_NEEDLES)


def _secret_exclusion_scan(scan: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_secret_exclusion_scan` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_scan = dict(scan)
    legacy_body_free = public_scan.pop("body_" "redacted", None)
    if "body_in_receipt" not in public_scan:
        public_scan["body_in_receipt"] = False if legacy_body_free is True else None
    return public_scan


def _source_module_manifest_result(
    input_dir: Path,
    *,
    public_root: Path,
    require_manifest: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_result` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    manifest_ref = _display(manifest_path, public_root=public_root)
    if not manifest_path.is_file():
        findings = []
        status = "blocked" if require_manifest else "not_present"
        if require_manifest:
            findings.append(
                _finding(
                    "MATERIALS_SOURCE_MODULE_MANIFEST_REQUIRED",
                    "Exported materials lab bundle must include copied non-secret macro source modules.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="source_module_manifest",
                )
            )
        return {
            "status": status,
            "source_module_import_status": status,
            "source_module_manifest_ref": manifest_ref,
            "module_count": 0,
            "verified_module_count": 0,
            "module_ids": [],
            "material_classes": [],
            "body_material_classes": {},
            "source_refs": [],
            "blocked_source_refs": [],
            "omitted_material": [],
            "findings": findings,
            "body_in_receipt": False,
            "body_text_in_receipt": False,
        }

    manifest = read_json_strict(manifest_path)
    findings: list[dict[str, Any]] = []
    modules = _rows(manifest, "modules")
    module_ids: list[str] = []
    material_class_counts: dict[str, int] = {}
    source_refs = [manifest_ref]
    blocked_source_refs = (
        manifest.get("blocked_source_refs", []) if isinstance(manifest, dict) else []
    )
    omitted_material = _strings(
        manifest.get("omitted_material") if isinstance(manifest, dict) else []
    )
    live_source_checked_count = 0
    live_source_missing: list[str] = []

    if not isinstance(manifest, dict):
        modules = []
        findings.append(
            _finding(
                "MATERIALS_SOURCE_MODULE_MANIFEST_REQUIRED",
                "Source module manifest must be a JSON object.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    else:
        if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "MATERIALS_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module manifest must classify imports as copied non-secret macro body material.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="source_import_class",
                )
            )
        if manifest.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "MATERIALS_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must keep body text out of receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="body_in_receipt",
                )
            )
        if manifest.get("body_text_in_receipt") is not False:
            findings.append(
                _finding(
                    "MATERIALS_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must keep body text out of receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="body_text_in_receipt",
                )
            )
        if int(manifest.get("module_count") or 0) != len(modules):
            findings.append(
                _finding(
                    "MATERIALS_SOURCE_MODULE_COUNT_MISMATCH",
                    "Source module manifest module_count must match the module row count.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="module_count",
                )
            )

    verified_count = 0
    for row in modules:
        module_id = str(row.get("module_id") or "source_module")
        module_ids.append(module_id)
        material_class = str(row.get("material_class") or "")
        if material_class:
            material_class_counts[material_class] = (
                material_class_counts.get(material_class, 0) + 1
            )
        module_findings_start = len(findings)
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "MATERIALS_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must classify copied material as non-secret macro body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_import_class",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_BODY_CLASSES:
            findings.append(
                _finding(
                    "MATERIALS_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must use a public-safe macro body material class.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="material_class",
                )
            )
        if (
            row.get("body_copied") is not True
            or row.get("body_in_receipt") is not False
            or row.get("body_text_in_receipt") is not False
        ):
            findings.append(
                _finding(
                    "MATERIALS_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module rows must copy body into source_modules while receipts remain body-free.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        target_ref = str(row.get("target_ref") or row.get("path") or "")
        target = _source_module_target_path(
            target_ref,
            input_dir=input_dir,
            public_root=public_root,
        )
        if not target.is_file():
            findings.append(
                _finding(
                    "MATERIALS_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target body must exist inside the public bundle.",
                    case_id="source_module_manifest_floor",
                    subject_id=target_ref or module_id,
                    subject_kind="source_module",
                )
            )
            continue
        actual = _sha256(target)
        expected_values = {
            "sha256": str(row.get("sha256") or ""),
            "source_sha256": str(row.get("source_sha256") or ""),
            "target_sha256": str(row.get("target_sha256") or ""),
        }
        if any(value != actual for value in expected_values.values()):
            findings.append(
                _finding(
                    "MATERIALS_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module digest declarations must match the copied target body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        expected_source_digest = EXPECTED_SOURCE_MODULE_DIGESTS.get(module_id)
        if not expected_source_digest:
            findings.append(
                _finding(
                    "MATERIALS_SOURCE_MODULE_AUTHORITY_UNKNOWN",
                    "Source module row must resolve to a validator-owned source body digest authority.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_module_authority_digest",
                )
            )
        elif (
            actual != expected_source_digest
            or expected_values["sha256"] != expected_source_digest
            or expected_values["source_sha256"] != expected_source_digest
            or expected_values["target_sha256"] != expected_source_digest
        ):
            findings.append(
                _finding(
                    "MATERIALS_SOURCE_MODULE_AUTHORITY_DIGEST_MISMATCH",
                    "Source module digest declarations must bind the copied target body to the validator-owned source body digest authority.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_module_authority_digest",
                )
            )
        source_ref = str(row.get("source_ref") or "")
        if source_ref:
            source = public_root.parent / source_ref
            source_display = _display(source, public_root=public_root)
            if source.is_file():
                live_source_checked_count += 1
                source_actual = _sha256(source)
                if row.get("source_sha256") != source_actual or source_actual != actual:
                    findings.append(
                        _finding(
                            "MATERIALS_SOURCE_MODULE_LIVE_SOURCE_DIGEST_MISMATCH",
                            "Source module digest declarations must bind the copied target body to the live source_ref body when that source is available.",
                            case_id="source_module_manifest_floor",
                            subject_id=module_id,
                            subject_kind="source_module_live_source",
                        )
                    )
            else:
                live_source_missing.append(source_display)
        text = target.read_text(encoding="utf-8")
        missing_anchors = [
            anchor
            for anchor in _strings(row.get("required_anchors"))
            if anchor not in text
        ]
        if missing_anchors:
            findings.append(
                {
                    **_finding(
                        "MATERIALS_SOURCE_MODULE_ANCHOR_MISSING",
                        "Source module body must carry the declared materials Lab/Evolve macro anchors.",
                        case_id="source_module_manifest_floor",
                        subject_id=module_id,
                        subject_kind="source_module",
                    ),
                    "missing_anchors": missing_anchors,
                }
            )
        source_refs.append(_display(target, public_root=public_root))
        if len(findings) == module_findings_start:
            verified_count += 1

    status = PASS if modules and not findings else "blocked"
    return {
        "status": status,
        "source_module_import_status": (
            SOURCE_MODULE_IMPORT_STATUS if status == PASS else "blocked"
        ),
        "source_module_manifest_ref": manifest_ref,
        "module_count": len(modules),
        "verified_module_count": verified_count,
        "module_ids": module_ids,
        "material_classes": sorted(material_class_counts),
        "body_material_classes": material_class_counts,
        "source_refs": source_refs,
        "live_source_checked_count": live_source_checked_count,
        "live_source_missing": live_source_missing,
        "blocked_source_refs": blocked_source_refs
        if isinstance(blocked_source_refs, list)
        else [],
        "omitted_material": omitted_material,
        "findings": findings,
        "body_in_receipt": False,
        "body_text_in_receipt": False,
    }


def _numeric_value(row: dict[str, Any], field: str) -> float | None:
    """
    [ACTION]
    - Teleology: Implements `_numeric_value` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    value = row.get(field)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        number = float(value)
        if math.isfinite(number) and 0 <= number <= 1:
            return number
    return None


def _numeric_score_error_code(row: dict[str, Any], field: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_numeric_score_error_code` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    value = row.get(field)
    if isinstance(value, bool) or value is None:
        return "MATERIALS_NUMERIC_REPLAY_SCORE_REQUIRED"
    if not isinstance(value, int | float):
        return "MATERIALS_NUMERIC_REPLAY_SCORE_REQUIRED"
    number = float(value)
    if not math.isfinite(number) or number < 0 or number > 1:
        return "MATERIALS_NUMERIC_REPLAY_SCORE_OUT_OF_RANGE"
    return "MATERIALS_NUMERIC_REPLAY_SCORE_REQUIRED"


def _numeric_replay_policy_settings(
    replay_policy: dict[str, Any],
) -> tuple[bool, str, float, list[dict[str, Any]]]:
    """
    [ACTION]
    - Teleology: Implements `_numeric_replay_policy_settings` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    numeric_policy = replay_policy.get("numeric_replay")
    policy_declared = isinstance(numeric_policy, dict) and bool(numeric_policy)
    if not isinstance(numeric_policy, dict):
        return (
            False,
            NUMERIC_REPLAY_SELECTION_RULE,
            NUMERIC_REPLAY_MIN_SAFETY_GATE,
            findings,
        )

    selection_rule = str(
        numeric_policy.get("selection_rule") or NUMERIC_REPLAY_SELECTION_RULE
    )
    if selection_rule != NUMERIC_REPLAY_SELECTION_RULE:
        findings.append(
            _finding(
                "MATERIALS_NUMERIC_REPLAY_SELECTION_RULE_UNSUPPORTED",
                "Materials numeric replay only supports the weighted public assay, active-learning, and safety-gate selection rule.",
                case_id="positive_fixture",
                subject_id=selection_rule,
                subject_kind="numeric_replay_policy",
            )
        )

    minimum_safety_gate_value = numeric_policy.get("minimum_safety_gate_score")
    minimum_safety_gate = NUMERIC_REPLAY_MIN_SAFETY_GATE
    if minimum_safety_gate_value is not None:
        if isinstance(minimum_safety_gate_value, bool):
            findings.append(
                _finding(
                    "MATERIALS_NUMERIC_REPLAY_MINIMUM_SAFETY_GATE_INVALID",
                    "Materials numeric replay minimum_safety_gate_score must be a finite number between 0 and 1.",
                    case_id="positive_fixture",
                    subject_id="minimum_safety_gate_score",
                    subject_kind="numeric_replay_policy",
                )
            )
        elif isinstance(minimum_safety_gate_value, int | float):
            parsed_minimum = float(minimum_safety_gate_value)
            if math.isfinite(parsed_minimum) and 0 <= parsed_minimum <= 1:
                minimum_safety_gate = parsed_minimum
            else:
                findings.append(
                    _finding(
                        "MATERIALS_NUMERIC_REPLAY_MINIMUM_SAFETY_GATE_INVALID",
                        "Materials numeric replay minimum_safety_gate_score must be a finite number between 0 and 1.",
                        case_id="positive_fixture",
                        subject_id="minimum_safety_gate_score",
                        subject_kind="numeric_replay_policy",
                    )
                )
        else:
            findings.append(
                _finding(
                    "MATERIALS_NUMERIC_REPLAY_MINIMUM_SAFETY_GATE_INVALID",
                    "Materials numeric replay minimum_safety_gate_score must be a finite number between 0 and 1.",
                    case_id="positive_fixture",
                    subject_id="minimum_safety_gate_score",
                    subject_kind="numeric_replay_policy",
                )
            )

    return policy_declared, selection_rule, minimum_safety_gate, findings


def _numeric_replay_result(
    candidates: list[dict[str, Any]],
    assays: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    replay_policy: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_numeric_replay_result` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    (
        policy_declared,
        selection_rule,
        minimum_safety_gate,
        policy_findings,
    ) = _numeric_replay_policy_settings(replay_policy)
    declared_expected_selected = _expected_numeric_selected_candidate(replay_policy)
    numeric_present = any(
        NUMERIC_REPLAY_SCORE_FIELD in row
        or NUMERIC_REPLAY_ASSAY_VALUE_FIELD in row
        or NUMERIC_REPLAY_ACTIVE_LEARNING_FIELD in row
        or NUMERIC_REPLAY_SAFETY_GATE_FIELD in row
        for row in [*candidates, *assays, *decisions]
    )
    if not numeric_present:
        error_code = (
            "MATERIALS_NUMERIC_REPLAY_POLICY_REQUIRES_SCORE_BACKED_ROWS"
            if policy_declared
            else "MATERIALS_NUMERIC_REPLAY_REQUIRED"
        )
        findings = [
            *policy_findings,
            _finding(
                error_code,
                "Materials lab safety replay requires public score-backed candidate, assay, and decision rows.",
                case_id="positive_fixture",
                subject_id=declared_expected_selected or "numeric_replay_policy",
                subject_kind="numeric_replay_policy",
            ),
        ]
        finding_codes = sorted(
            {str(row.get("error_code")) for row in findings if row.get("error_code")}
        )
        evidence = {
            "score_fields": {
                "legacy_score": NUMERIC_REPLAY_SCORE_FIELD,
                "assay_proxy_value": NUMERIC_REPLAY_ASSAY_VALUE_FIELD,
                "active_learning_score": NUMERIC_REPLAY_ACTIVE_LEARNING_FIELD,
                "safety_gate_score": NUMERIC_REPLAY_SAFETY_GATE_FIELD,
            },
            "selection_rule": selection_rule,
            "minimum_safety_gate_score": minimum_safety_gate,
            "declared_expected_selected_candidate_material_id": declared_expected_selected,
            "finding_codes": finding_codes,
        }
        return {
            "status": "blocked",
            "schema_version": "materials_lab_numeric_replay_v1",
            "score_fields": evidence["score_fields"],
            "selection_rule": selection_rule,
            "minimum_safety_gate_score": minimum_safety_gate,
            "candidate_score_count": 0,
            "assay_score_count": 0,
            "decision_score_count": 0,
            "verified_numeric_row_count": 0,
            "selected_candidate_material_id": "",
            "selected_decision_id": "",
            "selected_next_action_class": "",
            "selected_computed_numeric_score": None,
            "selected_score_components": {},
            "verdict_basis": NUMERIC_REPLAY_VERDICT_BASIS,
            "declared_expected_selected_candidate_material_id": declared_expected_selected,
            "finding_codes": finding_codes,
            "findings": findings,
            "evidence_digest": _stable_digest(evidence),
            "body_in_receipt": False,
        }

    findings: list[dict[str, Any]] = list(policy_findings)
    safety_gate_scores: dict[str, float] = {}
    assay_proxy_values: dict[str, float] = {}
    active_learning_scores: dict[str, float] = {}
    for row in candidates:
        candidate_id = str(row.get("candidate_material_id") or "")
        safety_gate_score = _numeric_value(row, NUMERIC_REPLAY_SAFETY_GATE_FIELD)
        if not candidate_id or safety_gate_score is None:
            error_code = _numeric_score_error_code(
                row, NUMERIC_REPLAY_SAFETY_GATE_FIELD
            )
            findings.append(
                _finding(
                    error_code,
                    (
                        "Candidate rows must carry a public safety-gate score "
                        "between 0 and 1 when numeric replay is active."
                    ),
                    case_id="positive_fixture",
                    subject_id=candidate_id or "candidate_material",
                    subject_kind="candidate_material",
                )
            )
            continue
        safety_gate_scores[candidate_id] = safety_gate_score
    for row in assays:
        candidate_id = str(row.get("candidate_material_ref") or "")
        assay_proxy_value = _numeric_value(row, NUMERIC_REPLAY_ASSAY_VALUE_FIELD)
        if not candidate_id or assay_proxy_value is None:
            error_code = _numeric_score_error_code(
                row, NUMERIC_REPLAY_ASSAY_VALUE_FIELD
            )
            findings.append(
                _finding(
                    error_code,
                    (
                        "Simulator assay rows must carry a public assay proxy value "
                        "between 0 and 1 when numeric replay is active."
                    ),
                    case_id="positive_fixture",
                    subject_id=str(row.get("assay_id") or "simulator_assay"),
                    subject_kind="simulator_assay",
                )
            )
            continue
        assay_proxy_values[candidate_id] = assay_proxy_value
    for row in decisions:
        candidate_id = str(row.get("candidate_material_ref") or "")
        active_learning_score = _numeric_value(row, NUMERIC_REPLAY_ACTIVE_LEARNING_FIELD)
        if not candidate_id or active_learning_score is None:
            error_code = _numeric_score_error_code(
                row, NUMERIC_REPLAY_ACTIVE_LEARNING_FIELD
            )
            findings.append(
                _finding(
                    error_code,
                    (
                        "Active-learning decision rows must carry a public "
                        "active-learning score between 0 and 1 when numeric "
                        "replay is active."
                    ),
                    case_id="positive_fixture",
                    subject_id=str(row.get("decision_id") or "active_learning_decision"),
                    subject_kind="active_learning_decision",
                )
            )
            continue
        active_learning_scores[candidate_id] = active_learning_score

    verified_rows: list[dict[str, Any]] = []
    for candidate_id, safety_gate_score in sorted(safety_gate_scores.items()):
        assay_proxy_value = assay_proxy_values.get(candidate_id)
        active_learning_score = active_learning_scores.get(candidate_id)
        if assay_proxy_value is None or active_learning_score is None:
            findings.append(
                _finding(
                    "MATERIALS_NUMERIC_REPLAY_LINKAGE_REQUIRED",
                    "Candidate safety gate, simulator assay, and active-learning scores must share one candidate id.",
                    case_id="positive_fixture",
                    subject_id=candidate_id,
                    subject_kind="numeric_replay",
                )
            )
            continue
        if safety_gate_score < minimum_safety_gate:
            findings.append(
                _finding(
                    "MATERIALS_NUMERIC_REPLAY_SAFETY_GATE_FAILED",
                    "Public numeric replay safety gate score fell below the accepted simulator-only threshold.",
                    case_id="positive_fixture",
                    subject_id=candidate_id,
                    subject_kind="numeric_replay",
                )
            )
        computed_numeric_score = (
            assay_proxy_value * NUMERIC_REPLAY_SCORE_WEIGHTS["assay_proxy_value"]
            + active_learning_score
            * NUMERIC_REPLAY_SCORE_WEIGHTS["active_learning_score"]
            + safety_gate_score * NUMERIC_REPLAY_SCORE_WEIGHTS["safety_gate_score"]
        )
        verified_rows.append(
            {
                "candidate_material_id": candidate_id,
                "assay_proxy_value": assay_proxy_value,
                "active_learning_score": active_learning_score,
                "safety_gate_score": safety_gate_score,
                "computed_numeric_score": computed_numeric_score,
            }
        )
    decision_by_candidate = {
        str(row.get("candidate_material_ref") or ""): row
        for row in decisions
        if row.get("candidate_material_ref")
    }
    selected_candidate = ""
    selected_decision_id = ""
    selected_next_action_class = ""
    selected_computed_numeric_score: float | None = None
    selected_score_components: dict[str, float] = {}
    if verified_rows:
        selected_row = max(
            verified_rows,
            key=lambda row: (
                row["computed_numeric_score"],
                row["candidate_material_id"],
            ),
        )
        selected_candidate = selected_row["candidate_material_id"]
        selected_computed_numeric_score = selected_row["computed_numeric_score"]
        selected_score_components = {
            "assay_proxy_value": selected_row["assay_proxy_value"],
            "active_learning_score": selected_row["active_learning_score"],
            "safety_gate_score": selected_row["safety_gate_score"],
        }
        selected_decision = decision_by_candidate.get(selected_candidate, {})
        selected_decision_id = str(selected_decision.get("decision_id") or "")
        selected_next_action_class = str(selected_decision.get("next_action_class") or "")
    if (
        declared_expected_selected
        and selected_candidate
        and declared_expected_selected != selected_candidate
    ):
        findings.append(
            _finding(
                "MATERIALS_NUMERIC_REPLAY_EXPECTED_LABEL_STALE",
                "Declared numeric replay expected label does not match the recomputed public score ranking.",
                case_id="positive_fixture",
                subject_id=declared_expected_selected,
                subject_kind="numeric_replay_expected_label",
            )
        )
    finding_codes = sorted(
        str(row.get("error_code")) for row in findings if row.get("error_code")
    )
    evidence = {
        "score_fields": {
            "legacy_score": NUMERIC_REPLAY_SCORE_FIELD,
            "assay_proxy_value": NUMERIC_REPLAY_ASSAY_VALUE_FIELD,
            "active_learning_score": NUMERIC_REPLAY_ACTIVE_LEARNING_FIELD,
            "safety_gate_score": NUMERIC_REPLAY_SAFETY_GATE_FIELD,
        },
        "score_weights": NUMERIC_REPLAY_SCORE_WEIGHTS,
        "selection_rule": selection_rule,
        "minimum_safety_gate_score": minimum_safety_gate,
        "tolerance": NUMERIC_REPLAY_TOLERANCE,
        "verified_rows": verified_rows,
        "selected_candidate_material_id": selected_candidate,
        "selected_decision_id": selected_decision_id,
        "selected_next_action_class": selected_next_action_class,
        "selected_computed_numeric_score": selected_computed_numeric_score,
        "selected_score_components": selected_score_components,
        "verdict_basis": NUMERIC_REPLAY_VERDICT_BASIS,
        "declared_expected_selected_candidate_material_id": declared_expected_selected,
        "finding_codes": finding_codes,
    }
    return {
        "status": PASS if not findings and verified_rows else "blocked",
        "schema_version": "materials_lab_numeric_replay_v1",
        "score_fields": evidence["score_fields"],
        "score_weights": NUMERIC_REPLAY_SCORE_WEIGHTS,
        "selection_rule": selection_rule,
        "minimum_safety_gate_score": minimum_safety_gate,
        "candidate_score_count": len(safety_gate_scores),
        "assay_score_count": len(assay_proxy_values),
        "decision_score_count": len(active_learning_scores),
        "verified_numeric_row_count": len(verified_rows),
        "selected_candidate_material_id": selected_candidate,
        "selected_decision_id": selected_decision_id,
        "selected_next_action_class": selected_next_action_class,
        "selected_computed_numeric_score": selected_computed_numeric_score,
        "selected_score_components": selected_score_components,
        "verdict_basis": NUMERIC_REPLAY_VERDICT_BASIS,
        "declared_expected_selected_candidate_material_id": declared_expected_selected,
        "finding_codes": finding_codes,
        "findings": findings,
        "evidence_digest": _stable_digest(evidence),
        "body_in_receipt": False,
    }


def _expected_numeric_selected_candidate(replay_policy: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `_expected_numeric_selected_candidate` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for field in NUMERIC_REPLAY_EXPECTED_SELECTED_FIELDS:
        value = replay_policy.get(field)
        if isinstance(value, str) and value:
            return value
    numeric_policy = replay_policy.get("numeric_replay")
    if isinstance(numeric_policy, dict):
        for field in NUMERIC_REPLAY_EXPECTED_SELECTED_FIELDS:
            value = numeric_policy.get(field)
            if isinstance(value, str) and value:
                return value
    return ""


def _numeric_replay_graph_projection(numeric_replay: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_numeric_replay_graph_projection` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "materials_lab_numeric_replay_graph_projection_v1",
        "status": numeric_replay["status"],
        "selection_rule": numeric_replay["selection_rule"],
        "minimum_safety_gate_score": numeric_replay["minimum_safety_gate_score"],
        "candidate_score_count": numeric_replay["candidate_score_count"],
        "assay_score_count": numeric_replay["assay_score_count"],
        "decision_score_count": numeric_replay["decision_score_count"],
        "verified_numeric_row_count": numeric_replay["verified_numeric_row_count"],
        "selected_candidate_material_id": numeric_replay[
            "selected_candidate_material_id"
        ],
        "selected_decision_id": numeric_replay["selected_decision_id"],
        "selected_next_action_class": numeric_replay[
            "selected_next_action_class"
        ],
        "selected_computed_numeric_score": numeric_replay.get(
            "selected_computed_numeric_score"
        ),
        "selected_score_components": numeric_replay.get("selected_score_components", {}),
        "verdict_basis": numeric_replay.get("verdict_basis", ""),
        "declared_expected_selected_candidate_material_id": numeric_replay[
            "declared_expected_selected_candidate_material_id"
        ],
        "finding_codes": numeric_replay["finding_codes"],
        "evidence_digest": numeric_replay["evidence_digest"],
        "body_in_receipt": False,
    }


def _numeric_replay_realness_evidence(
    *,
    status: str,
    numeric_replay: dict[str, Any],
    candidate_count: int,
    assay_count: int,
    decision_count: int,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_numeric_replay_realness_evidence` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    verified_count = int(numeric_replay.get("verified_numeric_row_count") or 0)
    expected_row_count = min(candidate_count, assay_count, decision_count)
    selected_candidate = str(numeric_replay.get("selected_candidate_material_id") or "")
    selected_score = numeric_replay.get("selected_computed_numeric_score")
    components = numeric_replay.get("selected_score_components")
    score_components = components if isinstance(components, dict) else {}
    score_backed_rows = (
        verified_count > 0
        and verified_count == expected_row_count
        and selected_candidate
        and isinstance(selected_score, int | float)
        and len(score_components) == 3
    )
    numeric_verdict_bound = (
        status == PASS
        and numeric_replay.get("status") == PASS
        and numeric_replay.get("verdict_basis") == NUMERIC_REPLAY_VERDICT_BASIS
        and score_backed_rows
        and not numeric_replay.get("finding_codes")
    )
    realness_rank = 3 if numeric_verdict_bound else 2 if score_backed_rows else 1
    realness_rung = f"R{realness_rank}" if numeric_verdict_bound else "blocked"
    return {
        "schema_version": NUMERIC_REPLAY_REALNESS_SCHEMA_VERSION,
        "status": PASS if numeric_verdict_bound else "blocked",
        "realness_rank": realness_rank,
        "realness_rung": realness_rung,
        "realness_state": (
            "public_safe_numeric_verdict_replay"
            if numeric_verdict_bound
            else "numeric_rows_present_but_verdict_blocked"
            if score_backed_rows
            else "metadata_or_missing_numeric_replay"
        ),
        "rank_derivation": (
            "recomputed_weighted_public_assay_active_learning_and_safety_gate_scores"
        ),
        "verdict_rederived_from_numeric_fixture_content": (
            numeric_replay.get("verdict_basis") == NUMERIC_REPLAY_VERDICT_BASIS
        ),
        "score_backed_rows_bound": score_backed_rows,
        "expected_numeric_row_count": expected_row_count,
        "verified_numeric_row_count": verified_count,
        "selected_candidate_material_id": selected_candidate,
        "selected_decision_id": numeric_replay.get("selected_decision_id"),
        "selected_next_action_class": numeric_replay.get("selected_next_action_class"),
        "selected_computed_numeric_score": selected_score,
        "selected_score_components": score_components,
        "numeric_replay_evidence_digest": numeric_replay.get("evidence_digest"),
        "numeric_replay_finding_codes": numeric_replay.get("finding_codes", []),
        "expected_labels_used_for_selection": False,
        "declared_expected_label_checked_only": True,
        "baked_fixture_label_sufficient": False,
        "authority_ceiling_bound": True,
        "release_authorized": False,
        "body_in_receipt": False,
    }


def _source_open_body_import_summary(
    source_module_result: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_open_body_import_summary` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    module_ids = _strings(source_module_result.get("module_ids"))
    manifest_ref = source_module_result.get("source_module_manifest_ref")
    imported = source_module_result.get("status") == PASS and bool(module_ids)
    return {
        "schema_version": SOURCE_OPEN_BODY_SCHEMA,
        "status": PASS if imported else str(source_module_result.get("status") or ""),
        "source_import_class": SOURCE_IMPORT_CLASS if imported else "",
        "body_material_status": SOURCE_MODULE_IMPORT_STATUS if imported else "",
        "body_material_count": len(module_ids) if imported else 0,
        "body_material_ids": module_ids if imported else [],
        "material_classes": source_module_result.get("material_classes", [])
        if imported
        else [],
        "body_material_classes": source_module_result.get("body_material_classes", {})
        if imported
        else {},
        "source_manifest_refs": [str(manifest_ref)]
        if imported and manifest_ref
        else [],
        "aggregate_floor_ref": f"{manifest_ref}::modules"
        if imported and manifest_ref
        else "",
        "blocked_source_refs": source_module_result.get("blocked_source_refs", []),
        "omitted_material": source_module_result.get("omitted_material", []),
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "body_text_exported_in_workingness": False,
        "authority_ceiling": {
            "wetlab_protocol_authorized": False,
            "hazardous_synthesis_authorized": False,
            "reagent_amounts_authorized": False,
            "live_lab_credentials_authorized": False,
            "robot_command_authorized": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported materials lab-safety bundle for copied Lab/Evolve replay "
            "specimen, replay graph, replay receipt, and laboratory standard "
            "bodies; receipts carry refs, hashes, counts, and verdicts only."
        )
        if imported
        else "",
    }


def _candidate_findings(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_candidate_findings` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    subject_id = str(row.get("candidate_material_id") or case_id)
    findings.extend(
        _missing_fields(
            row,
            REQUIRED_CANDIDATE_FIELDS,
            code="MATERIALS_CANDIDATE_FIELD_REQUIRED",
            kind="candidate_material",
            row_id=subject_id,
            case_id=case_id,
            observed=observed,
        )
    )
    if not row.get("literature_capsule_ref") or not row.get("safety_screen_ref"):
        _record(
            findings,
            observed,
            "MATERIALS_CANDIDATE_LINEAGE_REQUIRED",
            "candidate rows must bind literature-capsule and safety-screen refs",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="candidate_material",
        )
    if row.get("controlled_substance_target") is True or row.get("bioactivity_target") is True:
        _record(
            findings,
            observed,
            "MATERIALS_CONTROLLED_OR_BIOACTIVE_TARGET_FORBIDDEN",
            "controlled-substance and bioactivity targets are outside this public contract",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="candidate_material",
        )
    if row.get("discovery_claim") is True:
        _record(
            findings,
            observed,
            "MATERIALS_DISCOVERY_CLAIM_FORBIDDEN",
            "candidate rows cannot claim discovery",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="candidate_material",
        )
    if row.get("private_lab_notebook_exported") is True:
        _record(
            findings,
            observed,
            "MATERIALS_PRIVATE_LAB_NOTEBOOK_FORBIDDEN",
            "private lab notebooks cannot enter public candidate rows",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="candidate_material",
        )
    if row.get("body_in_receipt") is not False or _has_private_body(row):
        _record(
            findings,
            observed,
            "MATERIALS_BODY_FREE_PUBLIC_ROW_REQUIRED",
            "candidate rows must be body-free public metadata",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="candidate_material",
        )
    return findings


def _experiment_findings(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
    candidate_by_id: dict[str, dict[str, Any]],
    candidate_ids: set[str],
    assay_ids: set[str],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_experiment_findings` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    subject_id = str(row.get("experiment_id") or case_id)
    findings.extend(
        _missing_fields(
            row,
            REQUIRED_EXPERIMENT_FIELDS,
            code="MATERIALS_EXPERIMENT_FIELD_REQUIRED",
            kind="experiment",
            row_id=subject_id,
            case_id=case_id,
            observed=observed,
        )
    )
    if row.get("candidate_material_ref") not in candidate_ids:
        _record(
            findings,
            observed,
            "MATERIALS_CANDIDATE_REF_REQUIRED",
            "experiment rows must reference a known candidate material",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="experiment",
        )
    else:
        candidate = candidate_by_id.get(str(row.get("candidate_material_ref")), {})
        candidate_safety_ref = candidate.get("safety_screen_ref")
        if candidate_safety_ref and row.get("safety_screen_ref") != candidate_safety_ref:
            _record(
                findings,
                observed,
                "MATERIALS_SAFETY_SCREEN_REF_MISMATCH",
                "experiment safety-screen refs must match the candidate safety-screen gate",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="experiment",
            )
    if assay_ids and row.get("assay_ref") not in assay_ids:
        _record(
            findings,
            observed,
            "MATERIALS_ASSAY_REF_REQUIRED",
            "experiment rows must reference a known simulator assay",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="experiment",
        )
    if row.get("action_class") not in ALLOWED_ACTION_CLASSES:
        _record(
            findings,
            observed,
            "MATERIALS_ACTION_CLASS_REQUIRED",
            "experiment rows must use an allowed non-actionable action class",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="experiment",
        )
    if row.get("simulator_only") is not True:
        _record(
            findings,
            observed,
            "MATERIALS_SIMULATOR_ONLY_REQUIRED",
            "experiment rows must be simulator-only",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="experiment",
        )
    forbidden_fields = {
        "wetlab_protocol_exported": "MATERIALS_WETLAB_PROTOCOL_FORBIDDEN",
        "hazardous_synthesis_steps_exported": "MATERIALS_HAZARDOUS_SYNTHESIS_FORBIDDEN",
        "reagent_amounts_included": "MATERIALS_REAGENT_AMOUNT_FORBIDDEN",
        "live_lab_credentials_present": "MATERIALS_LIVE_LAB_CREDENTIAL_FORBIDDEN",
        "private_lab_notebook_exported": "MATERIALS_PRIVATE_LAB_NOTEBOOK_FORBIDDEN",
        "release_authorized": "MATERIALS_RELEASE_AUTHORITY_FORBIDDEN",
    }
    for field, code in forbidden_fields.items():
        if row.get(field) is True:
            _record(
                findings,
                observed,
                code,
                f"{field} must be false for public lab-safety replay rows",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="experiment",
            )
    if row.get("robot_command_authorized") is True:
        _record(
            findings,
            observed,
            "MATERIALS_ROBOT_COMMAND_FORBIDDEN",
            "experiment rows cannot authorize live robot commands",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="experiment",
        )
    if row.get("body_in_receipt") is not False or _has_private_body(row):
        _record(
            findings,
            observed,
            "MATERIALS_BODY_FREE_PUBLIC_ROW_REQUIRED",
            "experiment rows must be body-free public metadata",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="experiment",
        )
    return findings


def _assay_findings(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
    candidate_ids: set[str],
    experiment_ids: set[str],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_assay_findings` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    subject_id = str(row.get("assay_id") or case_id)
    findings.extend(
        _missing_fields(
            row,
            REQUIRED_ASSAY_FIELDS,
            code="MATERIALS_ASSAY_FIELD_REQUIRED",
            kind="simulator_assay",
            row_id=subject_id,
            case_id=case_id,
            observed=observed,
        )
    )
    if row.get("experiment_ref") not in experiment_ids:
        _record(
            findings,
            observed,
            "MATERIALS_EXPERIMENT_REF_REQUIRED",
            "assay rows must reference a known experiment",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="simulator_assay",
        )
    if row.get("candidate_material_ref") not in candidate_ids:
        _record(
            findings,
            observed,
            "MATERIALS_CANDIDATE_REF_REQUIRED",
            "assay rows must reference a known candidate material",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="simulator_assay",
        )
    if row.get("simulator_only") is not True:
        _record(
            findings,
            observed,
            "MATERIALS_SIMULATOR_ONLY_REQUIRED",
            "assay rows must be simulator-only",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="simulator_assay",
        )
    if row.get("live_assay_data_exported") is True:
        _record(
            findings,
            observed,
            "MATERIALS_LIVE_ASSAY_DATA_FORBIDDEN",
            "live assay data cannot enter public simulator assay rows",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="simulator_assay",
        )
    if row.get("discovery_claim") is True:
        _record(
            findings,
            observed,
            "MATERIALS_DISCOVERY_CLAIM_FORBIDDEN",
            "assay rows cannot claim discovery",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="simulator_assay",
        )
    if row.get("body_in_receipt") is not False or _has_private_body(row):
        _record(
            findings,
            observed,
            "MATERIALS_BODY_FREE_PUBLIC_ROW_REQUIRED",
            "assay rows must be body-free public metadata",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="simulator_assay",
        )
    return findings


def _decision_findings(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
    candidate_ids: set[str],
    experiment_ids: set[str],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_decision_findings` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    subject_id = str(row.get("decision_id") or case_id)
    findings.extend(
        _missing_fields(
            row,
            REQUIRED_DECISION_FIELDS,
            code="MATERIALS_DECISION_FIELD_REQUIRED",
            kind="active_learning_decision",
            row_id=subject_id,
            case_id=case_id,
            observed=observed,
        )
    )
    if row.get("experiment_ref") not in experiment_ids:
        _record(
            findings,
            observed,
            "MATERIALS_EXPERIMENT_REF_REQUIRED",
            "decision rows must reference a known experiment",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    if row.get("candidate_material_ref") not in candidate_ids:
        _record(
            findings,
            observed,
            "MATERIALS_CANDIDATE_REF_REQUIRED",
            "decision rows must reference a known candidate material",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    if row.get("next_action_class") not in ALLOWED_ACTION_CLASSES:
        _record(
            findings,
            observed,
            "MATERIALS_ACTION_CLASS_REQUIRED",
            "decision rows must use an allowed non-actionable action class",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    if row.get("simulator_only") is not True:
        _record(
            findings,
            observed,
            "MATERIALS_SIMULATOR_ONLY_REQUIRED",
            "decision rows must be simulator-only",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    if row.get("live_robot_command_emitted") is True:
        _record(
            findings,
            observed,
            "MATERIALS_ROBOT_COMMAND_FORBIDDEN",
            "decision rows cannot emit live robot commands",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    if row.get("discovery_claim") is True:
        _record(
            findings,
            observed,
            "MATERIALS_DISCOVERY_CLAIM_FORBIDDEN",
            "decision rows cannot claim discovery",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    if row.get("body_in_receipt") is not False or _has_private_body(row):
        _record(
            findings,
            observed,
            "MATERIALS_BODY_FREE_PUBLIC_ROW_REQUIRED",
            "decision rows must be body-free public metadata",
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="active_learning_decision",
        )
    return findings


def _required_policy_ok(policy: dict[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_required_policy_ok` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    ceiling = policy.get("authority_ceiling")
    if not isinstance(ceiling, dict):
        return False
    expected_false = (
        "wetlab_protocol_authorized",
        "hazardous_synthesis_authorized",
        "reagent_amounts_authorized",
        "controlled_substance_target_authorized",
        "bioactivity_target_authorized",
        "live_lab_credentials_authorized",
        "robot_command_authorized",
        "private_lab_notebook_exported",
        "live_assay_data_exported",
        "discovery_claim_authorized",
        "benchmark_score_claim_authorized",
        "release_authorized",
        "hosted_public_authorized",
        "publication_authorized",
        "provider_calls_authorized",
    )
    return (
        ceiling.get("metadata_projection_only") is True
        and ceiling.get("simulator_only") is True
        and all(ceiling.get(key) is False for key in expected_false)
    )


def _projection_protocol_ok(protocol: dict[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_projection_protocol_ok` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    projection = protocol.get("projection_protocol")
    if not isinstance(projection, dict):
        return False
    return all(field in projection for field in REQUIRED_PROJECTION_PROTOCOL_FIELDS)


def _negative_rows(payload: object) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    [ACTION]
    - Teleology: Implements `_negative_rows` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, dict):
        return [], [], [], []
    candidates = _rows(payload, "candidate_materials")
    experiments = _rows(payload, "experiments")
    assays = _rows(payload, "simulator_assays")
    decisions = _rows(payload, "active_learning_decisions")
    for key, target in (
        ("candidate_material", candidates),
        ("experiment", experiments),
        ("simulator_assay", assays),
        ("active_learning_decision", decisions),
    ):
        row = payload.get(key)
        if isinstance(row, dict):
            target.append(row)
    return candidates, experiments, assays, decisions


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_result` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    public_root = _public_root_for_path(input_dir)
    lab_safety_protocol = payloads.get("lab_safety_protocol", {})
    replay_policy = payloads.get("replay_policy", {})
    candidates = _rows(payloads.get("candidate_materials", {}), "candidate_materials")
    experiments = _rows(payloads.get("experiment_dag", {}), "experiments")
    assays = _rows(payloads.get("simulator_assays", {}), "simulator_assays")
    decisions = _rows(payloads.get("active_learning_decisions", {}), "active_learning_decisions")
    candidate_by_id = {
        str(row["candidate_material_id"]): row
        for row in candidates
        if row.get("candidate_material_id")
    }
    candidate_ids = {
        str(row.get("candidate_material_id"))
        for row in candidates
        if row.get("candidate_material_id")
    }
    experiment_ids = {
        str(row.get("experiment_id")) for row in experiments if row.get("experiment_id")
    }
    assay_ids = {str(row.get("assay_id")) for row in assays if row.get("assay_id")}
    observed_negative_codes: dict[str, set[str]] = defaultdict(set)
    positive_findings: list[dict[str, Any]] = []

    if (
        not isinstance(lab_safety_protocol, dict)
        or lab_safety_protocol.get("selected_route_id") != ORGAN_ID
    ):
        positive_findings.append(
            _finding(
                "MATERIALS_PROTOCOL_ROUTE_REQUIRED",
                f"lab safety protocol must select {ORGAN_ID}",
                case_id="positive_fixture",
                subject_id="lab_safety_protocol",
                subject_kind="protocol",
            )
        )
    if not _projection_protocol_ok(
        lab_safety_protocol if isinstance(lab_safety_protocol, dict) else {}
    ):
        positive_findings.append(
            _finding(
                "MATERIALS_PROJECTION_PROTOCOL_REQUIRED",
                "lab safety protocol must declare projection copied/reimplemented/omitted controls",
                case_id="positive_fixture",
                subject_id="lab_safety_protocol",
                subject_kind="protocol",
            )
        )
    if not _required_policy_ok(replay_policy if isinstance(replay_policy, dict) else {}):
        positive_findings.append(
            _finding(
                "MATERIALS_AUTHORITY_CEILING_REQUIRED",
                "replay policy must declare simulator-only authority ceiling",
                case_id="positive_fixture",
                subject_id="replay_policy",
                subject_kind="policy",
            )
        )
    for row in candidates:
        positive_findings.extend(
            _candidate_findings(row, case_id="positive_fixture", observed=observed_negative_codes)
        )
    for row in experiments:
        positive_findings.extend(
            _experiment_findings(
                row,
                case_id="positive_fixture",
                observed=observed_negative_codes,
                candidate_by_id=candidate_by_id,
                candidate_ids=candidate_ids,
                assay_ids=assay_ids,
            )
        )
    for row in assays:
        positive_findings.extend(
            _assay_findings(
                row,
                case_id="positive_fixture",
                observed=observed_negative_codes,
                candidate_ids=candidate_ids,
                experiment_ids=experiment_ids,
            )
        )
    for row in decisions:
        positive_findings.extend(
            _decision_findings(
                row,
                case_id="positive_fixture",
                observed=observed_negative_codes,
                candidate_ids=candidate_ids,
                experiment_ids=experiment_ids,
            )
        )
    numeric_replay = _numeric_replay_result(
        candidates,
        assays,
        decisions,
        replay_policy if isinstance(replay_policy, dict) else {},
    )
    positive_findings.extend(numeric_replay["findings"])
    selected_pattern_ids = _strings(
        lab_safety_protocol.get("selected_pattern_ids")
        if isinstance(lab_safety_protocol, dict)
        else []
    )
    experiment_id_list = [
        str(row.get("experiment_id")) for row in experiments if row.get("experiment_id")
    ]
    if selected_pattern_ids and selected_pattern_ids != experiment_id_list:
        positive_findings.append(
            _finding(
                "MATERIALS_SELECTED_PATTERN_IDS_MISMATCH",
                "selected_pattern_ids must exactly match validated experiment ids",
                case_id="positive_fixture",
                subject_id="lab_safety_protocol",
                subject_kind="protocol",
            )
        )

    negative_findings: list[dict[str, Any]] = []
    if include_negative:
        for name in NEGATIVE_INPUT_NAMES:
            case_id = Path(name).stem
            neg_candidates, neg_experiments, neg_assays, neg_decisions = _negative_rows(
                payloads.get(case_id, {})
            )
            for row in neg_candidates:
                negative_findings.extend(
                    _candidate_findings(row, case_id=case_id, observed=observed_negative_codes)
                )
            for row in neg_experiments:
                neg_candidate_by_id = {
                    **candidate_by_id,
                    **{
                        str(candidate["candidate_material_id"]): candidate
                        for candidate in neg_candidates
                        if candidate.get("candidate_material_id")
                    },
                }
                negative_findings.extend(
                    _experiment_findings(
                        row,
                        case_id=case_id,
                        observed=observed_negative_codes,
                        candidate_by_id=neg_candidate_by_id,
                        candidate_ids=candidate_ids | {
                            str(candidate.get("candidate_material_id"))
                            for candidate in neg_candidates
                            if candidate.get("candidate_material_id")
                        },
                        assay_ids=assay_ids | {
                            str(assay.get("assay_id"))
                            for assay in neg_assays
                            if assay.get("assay_id")
                        },
                    )
                )
            neg_experiment_ids = experiment_ids | {
                str(experiment.get("experiment_id"))
                for experiment in neg_experiments
                if experiment.get("experiment_id")
            }
            neg_candidate_ids = candidate_ids | {
                str(candidate.get("candidate_material_id"))
                for candidate in neg_candidates
                if candidate.get("candidate_material_id")
            }
            for row in neg_assays:
                negative_findings.extend(
                    _assay_findings(
                        row,
                        case_id=case_id,
                        observed=observed_negative_codes,
                        candidate_ids=neg_candidate_ids,
                        experiment_ids=neg_experiment_ids,
                    )
                )
            for row in neg_decisions:
                negative_findings.extend(
                    _decision_findings(
                        row,
                        case_id=case_id,
                        observed=observed_negative_codes,
                        candidate_ids=neg_candidate_ids,
                        experiment_ids=neg_experiment_ids,
                    )
                )

    expected_cases = EXPECTED_NEGATIVE_CASES if include_negative else {}
    expected_missing = {
        case_id: sorted(set(codes) - observed_negative_codes.get(case_id, set()))
        for case_id, codes in expected_cases.items()
    }
    expected_missing = {case_id: codes for case_id, codes in expected_missing.items() if codes}
    encoded_positive = json.dumps(
        [candidates, experiments, assays, decisions], sort_keys=True
    )
    body_in_receipt = any(needle in encoded_positive for needle in PRIVATE_NEEDLES)
    policy_passed = (
        bool(candidates)
        and bool(experiments)
        and bool(assays)
        and bool(decisions)
        and not positive_findings
        and not body_in_receipt
        and not expected_missing
        and all(row.get("body_in_receipt") is False for row in candidates)
        and all(row.get("body_in_receipt") is False for row in experiments)
        and all(row.get("body_in_receipt") is False for row in assays)
        and all(row.get("body_in_receipt") is False for row in decisions)
        and all(row.get("simulator_only") is True for row in experiments)
        and all(row.get("simulator_only") is True for row in assays)
        and all(row.get("simulator_only") is True for row in decisions)
        and all(row.get("controlled_substance_target") is False for row in candidates)
        and all(row.get("bioactivity_target") is False for row in candidates)
        and all(row.get("discovery_claim") is False for row in candidates)
        and all(row.get("wetlab_protocol_exported") is False for row in experiments)
        and all(row.get("hazardous_synthesis_steps_exported") is False for row in experiments)
        and all(row.get("reagent_amounts_included") is False for row in experiments)
        and all(row.get("robot_command_authorized") is False for row in experiments)
        and all(row.get("live_lab_credentials_present") is False for row in experiments)
        and all(row.get("private_lab_notebook_exported") is False for row in experiments)
        and all(row.get("live_assay_data_exported") is False for row in assays)
        and all(row.get("discovery_claim") is False for row in assays)
        and all(row.get("live_robot_command_emitted") is False for row in decisions)
        and all(row.get("discovery_claim") is False for row in decisions)
        and numeric_replay["status"] == PASS
    )
    source_modules = _source_module_manifest_result(
        input_dir,
        public_root=public_root,
        require_manifest=input_mode == "exported_materials_lab_safety_bundle",
    )
    source_open_body_imports = _source_open_body_import_summary(source_modules)
    scan = _secret_exclusion_scan(
        scan_paths(
            _scan_paths_for_input(input_dir, include_negative=include_negative),
            forbidden_classes=load_forbidden_classes(
                public_root / "core/private_state_forbidden_classes.json"
            ),
            display_root=public_root,
        )
    )
    public_lab_evolve_replay = build_materials_lab_evolve_replay(
        payloads,
        [*positive_findings, *negative_findings],
    )
    public_lab_evolve_replay["numeric_replay"] = _numeric_replay_graph_projection(
        numeric_replay
    )
    public_lab_evolve_replay["summary"].update(
        {
            "numeric_replay_status": numeric_replay["status"],
            "numeric_replay_verified_row_count": numeric_replay[
                "verified_numeric_row_count"
            ],
            "numeric_replay_selected_candidate_material_id": numeric_replay[
                "selected_candidate_material_id"
            ],
            "numeric_replay_selected_decision_id": numeric_replay[
                "selected_decision_id"
            ],
            "numeric_replay_selected_next_action_class": numeric_replay[
                "selected_next_action_class"
            ],
            "numeric_replay_selected_computed_numeric_score": numeric_replay.get(
                "selected_computed_numeric_score"
            ),
            "numeric_replay_verdict_basis": numeric_replay.get("verdict_basis", ""),
        }
    )
    if numeric_replay["status"] == "blocked":
        public_lab_evolve_replay["status"] = "blocked"
    status = (
        PASS
        if policy_passed
        and scan.get("status") == PASS
        and public_lab_evolve_replay.get("status") == PASS
        and (
            input_mode != "exported_materials_lab_safety_bundle"
            or source_modules["status"] == PASS
        )
        else "blocked"
    )
    summary = {
        "candidate_material_count": len(candidates),
        "experiment_count": len(experiments),
        "simulator_assay_count": len(assays),
        "active_learning_decision_count": len(decisions),
        "safety_screen_count": len(
            {
                str(row.get("safety_screen_ref"))
                for row in candidates + experiments
                if row.get("safety_screen_ref")
            }
        ),
        "simulator_only_experiment_count": sum(
            1 for row in experiments if row.get("simulator_only") is True
        ),
        "simulator_only_assay_count": sum(
            1 for row in assays if row.get("simulator_only") is True
        ),
        "cold_replay_count": sum(
            1 for row in experiments + decisions if row.get("cold_replay_ref")
        ),
        "wetlab_protocol_export_count": sum(
            1 for row in experiments if row.get("wetlab_protocol_exported") is True
        ),
        "hazardous_synthesis_export_count": sum(
            1
            for row in experiments
            if row.get("hazardous_synthesis_steps_exported") is True
        ),
        "reagent_amount_export_count": sum(
            1 for row in experiments if row.get("reagent_amounts_included") is True
        ),
        "controlled_or_bioactive_target_count": sum(
            1
            for row in candidates
            if row.get("controlled_substance_target") is True
            or row.get("bioactivity_target") is True
        ),
        "live_lab_credential_count": sum(
            1 for row in experiments if row.get("live_lab_credentials_present") is True
        ),
        "robot_command_count": sum(
            1
            for row in experiments + decisions
            if row.get("robot_command_authorized") is True
            or row.get("live_robot_command_emitted") is True
        ),
        "discovery_claim_count": sum(
            1
            for row in candidates + assays + decisions
            if row.get("discovery_claim") is True
        ),
        "numeric_replay_status": numeric_replay["status"],
        "numeric_replay_verified_row_count": numeric_replay[
            "verified_numeric_row_count"
        ],
        "numeric_replay_selected_candidate_material_id": numeric_replay[
            "selected_candidate_material_id"
        ],
        "numeric_replay_selected_decision_id": numeric_replay["selected_decision_id"],
        "numeric_replay_selected_next_action_class": numeric_replay[
            "selected_next_action_class"
        ],
        "numeric_replay_selected_computed_numeric_score": numeric_replay.get(
            "selected_computed_numeric_score"
        ),
        "numeric_replay_verdict_basis": numeric_replay.get("verdict_basis", ""),
    }
    realness_evidence = _numeric_replay_realness_evidence(
        status=status,
        numeric_replay=numeric_replay,
        candidate_count=len(candidates),
        assay_count=len(assays),
        decision_count=len(decisions),
    )
    body_import_verification = {
        "status": PASS,
        "body_import_status": BODY_IMPORT_STATUS,
        "classification": BODY_IMPORT_CLASSIFICATION,
        "body_import_classification": BODY_IMPORT_CLASSIFICATION,
        "verification_status": "verified",
        "verification_mode": "source_faithful_public_refactor",
        "source_refs": list(LAB_EVOLVE_SOURCE_REFS),
        "target_refs": list(LAB_EVOLVE_TARGET_REFS),
        "target_symbols": list(LAB_EVOLVE_TARGET_SYMBOL_REFS),
        "validation_refs": [
            "microcosm-substrate/tests/test_materials_chemistry_closed_loop_lab_safety_replay.py",
            (
                "python -m microcosm_core.macro_tools.lab_evolve_replay "
                "<materials-input-dir>"
            ),
        ],
        "replay_graph_status": public_lab_evolve_replay["status"],
        "replay_case_count": public_lab_evolve_replay["summary"]["replay_case_count"],
        "boundary_case_count": public_lab_evolve_replay["summary"]["boundary_case_count"],
        "source_capsule_count": public_lab_evolve_replay["summary"]["source_capsule_count"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_open_body_import_count": source_open_body_imports[
            "body_material_count"
        ],
        "body_in_receipt": False,
    }
    verdict_basis = {
        "input_mode": input_mode,
        "policy_passed": policy_passed,
        "positive_finding_codes": sorted(
            str(row.get("error_code"))
            for row in positive_findings
            if row.get("error_code")
        ),
        "source_module_finding_codes": sorted(
            str(row.get("error_code"))
            for row in source_modules["findings"]
            if row.get("error_code")
        ),
        "negative_case_expected_missing": expected_missing,
        "secret_exclusion_status": scan.get("status"),
        "secret_exclusion_blocking_hit_count": scan.get("blocking_hit_count"),
        "replay_status": public_lab_evolve_replay.get("status"),
        "replay_case_count": public_lab_evolve_replay["summary"]["replay_case_count"],
        "boundary_case_count": public_lab_evolve_replay["summary"]["boundary_case_count"],
        "source_capsule_count": public_lab_evolve_replay["summary"]["source_capsule_count"],
        "source_module_manifest_status": source_modules["status"],
        "source_open_body_import_count": source_open_body_imports[
            "body_material_count"
        ],
        "numeric_replay_status": numeric_replay["status"],
        "numeric_replay_finding_codes": numeric_replay["finding_codes"],
        "numeric_replay_verified_row_count": numeric_replay[
            "verified_numeric_row_count"
        ],
        "numeric_replay_evidence_digest": numeric_replay["evidence_digest"],
        "numeric_replay_verdict_basis": numeric_replay.get("verdict_basis", ""),
        "authority_ceiling_false_fields": sorted(
            key
            for key, value in AUTHORITY_CEILING.items()
            if key.endswith("_authorized") and value is False
        ),
        "materials_lab_safety_summary": summary,
        "numeric_replay": {
            "status": numeric_replay["status"],
            "verified_numeric_row_count": numeric_replay[
                "verified_numeric_row_count"
            ],
            "selected_candidate_material_id": numeric_replay[
                "selected_candidate_material_id"
            ],
            "selected_decision_id": numeric_replay["selected_decision_id"],
            "selected_next_action_class": numeric_replay[
                "selected_next_action_class"
            ],
            "selected_computed_numeric_score": numeric_replay.get(
                "selected_computed_numeric_score"
            ),
            "selected_score_components": numeric_replay.get(
                "selected_score_components", {}
            ),
            "verdict_basis": numeric_replay.get("verdict_basis", ""),
            "declared_expected_selected_candidate_material_id": numeric_replay[
                "declared_expected_selected_candidate_material_id"
            ],
            "finding_codes": numeric_replay["finding_codes"],
            "evidence_digest": numeric_replay["evidence_digest"],
        },
        "realness_evidence": {
            "status": realness_evidence["status"],
            "realness_rank": realness_evidence["realness_rank"],
            "realness_rung": realness_evidence["realness_rung"],
            "realness_state": realness_evidence["realness_state"],
            "rank_derivation": realness_evidence["rank_derivation"],
            "verdict_rederived_from_numeric_fixture_content": realness_evidence[
                "verdict_rederived_from_numeric_fixture_content"
            ],
            "score_backed_rows_bound": realness_evidence["score_backed_rows_bound"],
            "baked_fixture_label_sufficient": realness_evidence[
                "baked_fixture_label_sufficient"
            ],
            "authority_ceiling_bound": realness_evidence["authority_ceiling_bound"],
        },
    }
    safety_verdict = {
        "schema_version": SAFETY_VERDICT_SCHEMA_VERSION,
        "status": status,
        "verdict": (
            "public_safe_simulator_replay_accepted"
            if status == PASS
            else "blocked_public_safety_boundary"
        ),
        "evidence_digest": _stable_digest(verdict_basis),
        "derived_from": verdict_basis,
        "body_in_receipt": False,
        "authority_boundary": (
            "Verdict is computed from public simulator rows, safety/refusal "
            "fields, source-module manifest verdicts, replay graph status, "
            "negative-case coverage, and sentinel scan results; it is not wetlab, "
            "chemical-domain, discovery, release, or publication authority."
        ),
    }
    return {
        "schema_version": "materials_chemistry_closed_loop_lab_safety_replay_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "public_surface_name": PUBLIC_SURFACE_NAME,
        "surface_reframe": SURFACE_REFRAME,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "input_ref": _display(input_dir, public_root=public_root),
        "selected_route_id": ORGAN_ID,
        "selected_pattern_ids": experiment_id_list,
        "candidate_materials": candidates,
        "experiments": experiments,
        "simulator_assays": assays,
        "active_learning_decisions": decisions,
        "materials_lab_safety_summary": summary,
        "numeric_replay": numeric_replay,
        "realness_evidence": realness_evidence,
        "realness_rank": realness_evidence["realness_rank"],
        "realness_rung": realness_evidence["realness_rung"],
        "realness_state": realness_evidence["realness_state"],
        "safety_verdict": safety_verdict,
        "public_lab_evolve_replay": public_lab_evolve_replay,
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
        "finding_count": len(positive_findings) + len(source_modules["findings"]),
        "positive_findings": positive_findings,
        "negative_case_findings": negative_findings,
        "source_module_findings": source_modules["findings"],
        "source_module_manifest_status": source_modules["status"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_imports": source_modules,
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports[
            "body_material_count"
        ],
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_classification": BODY_IMPORT_CLASSIFICATION,
        "product_path_role": PRODUCT_PATH_ROLE,
        "body_import_verification": body_import_verification,
        "body_in_receipt": False,
        "safe_to_show": {
            "body_in_receipt": body_in_receipt,
            "body_free_public_metadata": True,
            "simulator_only": True,
            "wetlab_protocols_omitted": True,
            "hazardous_synthesis_steps_omitted": True,
            "reagent_amounts_omitted": True,
            "live_lab_credentials_omitted": True,
            "robot_commands_omitted": True,
            "private_lab_notebooks_omitted": True,
        },
        "release_authorized": False,
        "secret_exclusion_scan": scan,
    }


def _board(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_board` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    summary = result.get("materials_lab_safety_summary", {})
    negatives = result.get("negative_case_summary", {})
    return {
        "schema_version": "materials_chemistry_closed_loop_lab_safety_replay_board_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "public_surface_name": result.get("public_surface_name"),
        "board_id": "materials_chemistry_lab_safety_public_board",
        "route": ORGAN_ID,
        "surface_reframe": result.get("surface_reframe"),
        "candidate_material_count": summary.get("candidate_material_count", 0)
        if isinstance(summary, dict)
        else 0,
        "experiment_count": summary.get("experiment_count", 0)
        if isinstance(summary, dict)
        else 0,
        "simulator_assay_count": summary.get("simulator_assay_count", 0)
        if isinstance(summary, dict)
        else 0,
        "active_learning_decision_count": summary.get("active_learning_decision_count", 0)
        if isinstance(summary, dict)
        else 0,
        "negative_case_count": negatives.get("expected_negative_case_count", 0)
        if isinstance(negatives, dict)
        else 0,
        "observed_negative_case_count": negatives.get("observed_negative_case_count", 0)
        if isinstance(negatives, dict)
        else 0,
        "body_import_status": result["body_import_status"],
        "body_import_classification": result["body_import_classification"],
        "product_path_role": result["product_path_role"],
        "body_import_verification": result["body_import_verification"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "numeric_replay": result["numeric_replay"],
        "realness_evidence": result["realness_evidence"],
        "realness_rank": result["realness_rank"],
        "realness_rung": result["realness_rung"],
        "realness_state": result["realness_state"],
        "safety_verdict": result["safety_verdict"],
        "public_lab_evolve_replay": result["public_lab_evolve_replay"],
        "body_in_receipt": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_write_receipts` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
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
    summary = result.get("materials_lab_safety_summary") or {}
    negatives = result.get("negative_case_summary") or {}
    validation = {
        "schema_version": (
            "materials_chemistry_closed_loop_lab_safety_replay_validation_receipt_v1"
        ),
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "public_surface_name": result.get("public_surface_name"),
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "result_ref": receipt_paths[0],
        "board_ref": receipt_paths[1],
        "receipt_paths": receipt_paths,
        "candidate_material_count": summary.get("candidate_material_count"),
        "experiment_count": summary.get("experiment_count"),
        "simulator_assay_count": summary.get("simulator_assay_count"),
        "active_learning_decision_count": summary.get("active_learning_decision_count"),
        "expected_negative_case_count": negatives.get("expected_negative_case_count"),
        "observed_negative_case_count": negatives.get("observed_negative_case_count"),
        "public_lab_evolve_replay_summary": result["public_lab_evolve_replay"][
            "summary"
        ],
        "surface_reframe": result.get("surface_reframe"),
        "body_import_status": result["body_import_status"],
        "body_import_classification": result["body_import_classification"],
        "body_import_verification": result["body_import_verification"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "numeric_replay": result["numeric_replay"],
        "realness_evidence": result["realness_evidence"],
        "realness_rank": result["realness_rank"],
        "realness_rung": result["realness_rung"],
        "realness_state": result["realness_state"],
        "safety_verdict": result["safety_verdict"],
        "body_in_receipt": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
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
            "materials_chemistry_closed_loop_lab_safety_replay_fixture_acceptance_v1"
        ),
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "public_surface_name": result.get("public_surface_name"),
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "result_ref": receipt_paths[0],
        "board_ref": receipt_paths[1],
        "validation_ref": receipt_paths[2],
        "public_lab_evolve_replay_summary": result["public_lab_evolve_replay"][
            "summary"
        ],
        "surface_reframe": result.get("surface_reframe"),
        "body_import_status": result["body_import_status"],
        "body_import_classification": result["body_import_classification"],
        "body_import_verification": result["body_import_verification"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "numeric_replay": result["numeric_replay"],
        "realness_evidence": result["realness_evidence"],
        "realness_rank": result["realness_rank"],
        "realness_rung": result["realness_rung"],
        "realness_state": result["realness_state"],
        "safety_verdict": result["safety_verdict"],
        "body_in_receipt": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "release_authorized": False,
    }
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "materials_lab_safety_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = (
        "python -m microcosm_core.organs."
        "materials_chemistry_closed_loop_lab_safety_replay run"
    ),
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
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
    result["freshness_basis"] = _freshness_basis(Path(input_dir), include_negative=True)
    result["receipt_reused"] = False
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_lab_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs."
        "materials_chemistry_closed_loop_lab_safety_replay run-lab-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_lab_bundle` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    source = Path(input_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if reuse_fresh_receipt:
        cached = _fresh_lab_bundle_receipt(source, out, command=command)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_materials_lab_safety_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_materials_lab_safety_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    summary = result.get("materials_lab_safety_summary")
    lab_summary = summary if isinstance(summary, dict) else {}
    replay = result.get("public_lab_evolve_replay")
    replay_payload = replay if isinstance(replay, dict) else {}
    replay_summary = replay_payload.get("summary")
    replay_counts = replay_summary if isinstance(replay_summary, dict) else {}
    negatives = result.get("negative_case_summary")
    negative_summary = negatives if isinstance(negatives, dict) else {}
    scan = result.get("secret_exclusion_scan")
    secret_scan = scan if isinstance(scan, dict) else {}
    source_body = result.get("source_open_body_imports")
    source_body_imports = source_body if isinstance(source_body, dict) else {}
    numeric = result.get("numeric_replay")
    numeric_replay = numeric if isinstance(numeric, dict) else {}
    realness = result.get("realness_evidence")
    realness_evidence = realness if isinstance(realness, dict) else {}
    verdict = result.get("safety_verdict")
    safety_verdict = verdict if isinstance(verdict, dict) else {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "public_surface_name": result.get("public_surface_name"),
        "input_mode": result.get("input_mode"),
        "surface_reframe": {
            "public_surface_name": result.get("public_surface_name"),
            "reframe_reason": (
                result.get("surface_reframe", {}).get("reframe_reason")
                if isinstance(result.get("surface_reframe"), dict)
                else None
            ),
        },
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": freshness.get("basis_digest"),
            "freshness_input_count": freshness.get("input_count"),
            "freshness_missing_path_count": freshness.get("missing_path_count"),
        },
        "materials_lab_safety": {
            "candidate_material_count": lab_summary.get("candidate_material_count"),
            "experiment_count": lab_summary.get("experiment_count"),
            "simulator_assay_count": lab_summary.get("simulator_assay_count"),
            "active_learning_decision_count": lab_summary.get(
                "active_learning_decision_count"
            ),
            "simulator_only_experiment_count": lab_summary.get(
                "simulator_only_experiment_count"
            ),
            "wetlab_protocol_export_count": lab_summary.get(
                "wetlab_protocol_export_count"
            ),
            "robot_command_count": lab_summary.get("robot_command_count"),
            "discovery_claim_count": lab_summary.get("discovery_claim_count"),
            "numeric_replay_status": lab_summary.get("numeric_replay_status"),
            "numeric_replay_verified_row_count": lab_summary.get(
                "numeric_replay_verified_row_count"
            ),
        },
        "public_lab_evolve_replay": {
            "status": replay_payload.get("status"),
            "replay_case_count": replay_counts.get("replay_case_count"),
            "boundary_case_count": replay_counts.get("boundary_case_count"),
            "source_capsule_count": replay_counts.get("source_capsule_count"),
        },
        "validation": {
            "expected_negative_case_count": negative_summary.get(
                "expected_negative_case_count"
            ),
            "observed_negative_case_count": negative_summary.get(
                "observed_negative_case_count"
            ),
            "missing_negative_case_count": len(
                negative_summary.get("expected_missing") or {}
            ),
            "finding_count": result.get("finding_count"),
            "numeric_replay_status": numeric_replay.get("status"),
            "numeric_replay_verified_row_count": numeric_replay.get(
                "verified_numeric_row_count"
            ),
            "secret_exclusion_blocking_hit_count": secret_scan.get(
                "blocking_hit_count"
            ),
        },
        "safety_verdict": {
            "status": safety_verdict.get("status"),
            "verdict": safety_verdict.get("verdict"),
            "evidence_digest": safety_verdict.get("evidence_digest"),
            "derived_from_in_card": False,
            "body_in_receipt": False,
        },
        "realness": {
            "status": realness_evidence.get("status"),
            "rank": result.get("realness_rank"),
            "rung": result.get("realness_rung"),
            "state": result.get("realness_state"),
            "rank_derivation": realness_evidence.get("rank_derivation"),
            "verdict_rederived_from_numeric_fixture_content": realness_evidence.get(
                "verdict_rederived_from_numeric_fixture_content"
            ),
            "score_backed_rows_bound": realness_evidence.get(
                "score_backed_rows_bound"
            ),
            "verified_numeric_row_count": realness_evidence.get(
                "verified_numeric_row_count"
            ),
            "selected_candidate_material_id": realness_evidence.get(
                "selected_candidate_material_id"
            ),
            "selected_computed_numeric_score": realness_evidence.get(
                "selected_computed_numeric_score"
            ),
            "numeric_replay_evidence_digest": realness_evidence.get(
                "numeric_replay_evidence_digest"
            ),
            "expected_labels_used_for_selection": realness_evidence.get(
                "expected_labels_used_for_selection"
            ),
            "baked_fixture_label_sufficient": realness_evidence.get(
                "baked_fixture_label_sufficient"
            ),
            "body_in_receipt": False,
        },
        "body_floor": {
            "body_in_receipt": False,
            "body_material_status": result.get("body_material_status"),
            "body_copied_material_count": result.get("body_copied_material_count"),
            "source_module_manifest_status": result.get(
                "source_module_manifest_status"
            ),
            "source_module_manifest_ref": result.get("source_module_manifest_ref"),
            "source_open_body_import_status": source_body_imports.get("status"),
            "source_open_body_import_count": source_body_imports.get(
                "body_material_count"
            ),
            "public_lab_evolve_replay_rows_in_card": False,
            "secret_exclusion_scan_in_card": False,
            "authority_ceiling_in_card": False,
            "anti_claim_in_card": False,
            "body_import_verification_in_card": False,
            "source_module_imports_in_card": False,
            "source_open_body_imports_in_card": False,
            "materials_rows_in_card": False,
        },
        "authority_boundary": {
            "simulator_only": True,
            "wetlab_protocol_authorized": False,
            "hazardous_synthesis_authorized": False,
            "reagent_amounts_authorized": False,
            "controlled_or_bioactive_target_authorized": False,
            "live_lab_credentials_authorized": False,
            "robot_command_authorized": False,
            "private_lab_notebook_exported": False,
            "discovery_claim_authorized": False,
            "release_authorized": False,
            "provider_calls_authorized": False,
            "publication_authorized": False,
        },
        "receipt_paths": result.get("receipt_paths", []),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": "rerun without --card or inspect the written receipt file",
        },
    }


def _parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `_parser` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog="materials_chemistry_closed_loop_lab_safety_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-lab-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        command = (
            "materials_chemistry_closed_loop_lab_safety_replay run"
            f"{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-lab-bundle":
        command = (
            "materials_chemistry_closed_loop_lab_safety_replay run-lab-bundle"
            f"{card_suffix}"
        )
        result = run_lab_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    else:  # pragma: no cover
        raise ValueError(args.action)
    output = result_card(result) if args.card else result["status"]
    print(json.dumps(output, indent=2, sort_keys=True) if args.card else output)
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
