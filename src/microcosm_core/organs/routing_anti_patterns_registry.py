"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.routing_anti_patterns_registry` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, ACCEPTANCE_RECEIPT_REL, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, CARD_OMITTED_FULL_PAYLOAD_KEYS, HASH_CHUNK_SIZE, SOURCE_PATTERN_IDS, SOURCE_REFS, PUBLIC_RUNTIME_REFS, INPUT_NAMES, SOURCE_MODULE_MANIFEST_NAME, SOURCE_IMPORT_CLASS, SOURCE_MODULE_IMPORT_STATUS, SOURCE_OPEN_BODY_SCHEMA, PUBLIC_SAFE_SOURCE_BODY_CLASSES, NEGATIVE_INPUT_NAMES, NEGATIVE_INPUT_STEMS, EXPECTED_NEGATIVE_CASES, REQUIRED_ANTI_PATTERN_IDS, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.receipts, microcosm_core.schemas, microcosm_core.secret_exclusion_scan
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

from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)


ORGAN_ID = "routing_anti_patterns_registry"
FIXTURE_ID = "first_wave.routing_anti_patterns_registry"
VALIDATOR_ID = "validator.microcosm.organs.routing_anti_patterns_registry"

RESULT_NAME = "routing_anti_patterns_registry_result.json"
BOARD_NAME = "routing_anti_patterns_registry_board.json"
VALIDATION_RECEIPT_NAME = "routing_anti_patterns_registry_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "routing_anti_patterns_registry_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_routing_anti_patterns_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "routing_anti_patterns_registry_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "covered_anti_pattern_ids",
    "findings",
    "route_repair_state_validation",
    "secret_exclusion_scan",
    "expected_negative_cases",
    "observed_negative_cases",
    "source_refs",
    "public_runtime_refs",
    "anti_claim",
    "authority_ceiling",
    "source_module_summary",
)
HASH_CHUNK_SIZE = 1024 * 1024

SOURCE_PATTERN_IDS = [
    "routing_anti_patterns",
    "kernel_before_grep",
    "bridge_before_scope",
    "mode_in_chat_only",
]
SOURCE_REFS = ["codex/doctrine/routing_anti_patterns.json"]
PUBLIC_RUNTIME_REFS = [
    "core/standards_registry.json",
    "core/organ_registry.json",
    "core/acceptance/first_wave_acceptance.json",
    "core/preflight_support/organ_fixture_validator_readiness_v1.json",
    "fixtures/first_wave/routing_anti_patterns_registry/input/routing_anti_patterns.json",
    "examples/routing_anti_patterns_registry/exported_routing_anti_patterns_bundle",
    "paper_modules/routing_anti_patterns_registry.md",
]

INPUT_NAMES = ("routing_anti_patterns.json",)
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_MODULE_IMPORT_STATUS = "copied_non_secret_macro_body_landed"
SOURCE_OPEN_BODY_SCHEMA = "routing_anti_patterns_registry_source_open_body_imports_v1"
PUBLIC_SAFE_SOURCE_BODY_CLASSES = frozenset(
    {
        "public_macro_pattern_body",
        "public_macro_tool_body",
        "public_macro_receipt_body",
        "public_macro_proof_body",
        "public_macro_standard_body",
        "public_standard_body",
    }
)

NEGATIVE_INPUT_NAMES = (
    "missing_kind.json",
    "duplicate_id.json",
    "missing_text.json",
    "authority_overclaim.json",
    "source_authority_masquerade.json",
    "private_source_leakage.json",
)
NEGATIVE_INPUT_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)
EXPECTED_NEGATIVE_CASES = {
    "missing_kind": ["ROUTING_ANTI_PATTERN_KIND_REQUIRED"],
    "duplicate_id": ["ROUTING_ANTI_PATTERN_DUPLICATE_ID"],
    "missing_text": ["ROUTING_ANTI_PATTERN_TEXT_REQUIRED"],
    "authority_overclaim": ["ROUTING_ANTI_PATTERN_AUTHORITY_OVERCLAIM"],
    "source_authority_masquerade": [
        "ROUTING_ANTI_PATTERN_SOURCE_AUTHORITY_FORBIDDEN"
    ],
    "private_source_leakage": ["ROUTING_ANTI_PATTERN_PRIVATE_SOURCE_FORBIDDEN"],
}

REQUIRED_ANTI_PATTERN_IDS = (
    "kernel_before_grep",
    "bridge_before_scope",
    "mode_in_chat_only",
)
OVERCLAIM_KEYS = (
    "release_authorized",
    "publication_authorized",
    "provider_calls_authorized",
    "source_mutation_authorized",
    "route_policy_mutation_authorized",
    "whole_system_correctness_claim",
    "readiness_claim",
    "maturity_claim",
)
FORBIDDEN_PRIVATE_KEYS = (
    "private_source_body",
    "private_source_body_present",
    "raw_seed_body",
    "provider_payload_body",
    "secret_value",
)
AUTHORITY_ROLE_KEYS = (
    "authority_role",
    "surface_role",
    "source_role",
    "route_role",
)
FORBIDDEN_AUTHORITY_ROLES = frozenset(
    {
        "source_authority",
        "route_authority",
        "route_policy_authority",
        "route_source_authority",
        "routing_source_authority",
        "control_plane_authority",
        "canonical_authority",
    }
)
ROUTE_REPAIR_STATE_REQUIREMENTS = {
    "kernel_before_grep": {
        "route_repair_state": "kernel_first_navigation",
        "required_text_anchors": ("grep", "kernel", "route"),
    },
    "bridge_before_scope": {
        "route_repair_state": "scope_before_bridge",
        "required_text_anchors": ("bridge", "selected", "refs"),
    },
    "zero_write_disk": {
        "route_repair_state": "typed_bundle_return_only",
        "required_text_anchors": ("zero-write", "persist", "typed bundles"),
    },
    "ad_hoc_subphase_dirs": {
        "route_repair_state": "governed_phase_scaffold_only",
        "required_text_anchors": ("top-level", "subphase", "directories"),
    },
    "mode_in_chat_only": {
        "route_repair_state": "disk_bound_mode_contract",
        "required_text_anchors": ("execution mode", "synth", "wave contract"),
    },
}
BAKED_ROUTE_REPAIR_LABEL_KEYS = (
    "expected_route_repair_state",
    "route_repair_state",
    "expected_repair_state",
    "baked_expected_label",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "routing_anti_patterns_registry_projection_only_not_route_authority"
    ),
    "route_policy_mutation_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
    "provider_calls_authorized": False,
    "private_data_equivalence_claim": False,
    "whole_system_correctness_claim": False,
}

ANTI_CLAIM = (
    "Routing anti-pattern validation proves only the declared public routing "
    "anti-pattern registry contract and copied non-secret macro body. It does "
    "not become routing source authority, mutate routes, authorize release or "
    "provider calls, expose private state, or prove whole-system correctness."
)


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_display` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_rows` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, dict):
        return []
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names]


def _sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
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
    return digest.hexdigest()


def _strings(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _source_module_manifest_path(input_dir: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_path` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_source_module_target_path` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_source_module_paths` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
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


def _freshness_input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_freshness_input_paths` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    paths = _input_paths(input_dir, include_negative=include_negative)
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    paths.extend(_source_module_paths(input_dir, public_root=public_root))
    paths.append(Path(__file__).resolve())
    return paths


def _scan_paths_for_input(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_scan_paths_for_input` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    return [
        *_input_paths(input_dir, include_negative=include_negative),
        *(
            [input_dir / "bundle_manifest.json"]
            if (input_dir / "bundle_manifest.json").is_file()
            else []
        ),
        *_source_module_paths(input_dir, public_root=public_root),
    ]


def _walk_dicts(value: object) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_walk_dicts` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        rows.append(value)
        for child in value.values():
            rows.extend(_walk_dicts(child))
    elif isinstance(value, list):
        for child in value:
            rows.extend(_walk_dicts(child))
    return rows


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
    - Teleology: Implements `_finding` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_record` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
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
    observed[case_id].add(code)


def _anti_pattern_rows(payload: object) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_anti_pattern_rows` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _rows(payload, "anti_patterns")


def _payload_findings(
    payload: object,
    *,
    case_id: str,
    require_named_ids: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_payload_findings` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if not isinstance(payload, dict):
        _record(
            findings,
            observed,
            "ROUTING_ANTI_PATTERN_KIND_REQUIRED",
            "Routing anti-pattern registry input must be a JSON object.",
            case_id=case_id,
            subject_id="payload",
            subject_kind="kind",
        )
        return {
            "findings": findings,
            "observed_negative_cases": {
                key: sorted(value) for key, value in observed.items()
            },
        }

    if payload.get("kind") != "routing_anti_patterns":
        _record(
            findings,
            observed,
            "ROUTING_ANTI_PATTERN_KIND_REQUIRED",
            "Routing anti-pattern registry must declare kind=routing_anti_patterns.",
            case_id=case_id,
            subject_id="kind",
            subject_kind="kind",
        )
    if not isinstance(payload.get("version"), int) or int(payload.get("version")) < 1:
        _record(
            findings,
            observed,
            "ROUTING_ANTI_PATTERN_VERSION_REQUIRED",
            "Routing anti-pattern registry must declare a positive integer version.",
            case_id=case_id,
            subject_id="version",
            subject_kind="version",
        )

    rows = _anti_pattern_rows(payload)
    if not rows:
        _record(
            findings,
            observed,
            "ROUTING_ANTI_PATTERN_ROWS_REQUIRED",
            "Routing anti-pattern registry must include anti_patterns rows.",
            case_id=case_id,
            subject_id="anti_patterns",
            subject_kind="anti_patterns",
        )

    seen: set[str] = set()
    ids: list[str] = []
    for index, row in enumerate(rows):
        row_id = str(row.get("id") or "")
        text = str(row.get("text") or "")
        subject = row_id or f"anti_patterns[{index}]"
        if not row_id:
            _record(
                findings,
                observed,
                "ROUTING_ANTI_PATTERN_ID_REQUIRED",
                "Every routing anti-pattern row must carry a stable id.",
                case_id=case_id,
                subject_id=subject,
                subject_kind="id",
            )
        elif row_id in seen:
            _record(
                findings,
                observed,
                "ROUTING_ANTI_PATTERN_DUPLICATE_ID",
                "Routing anti-pattern ids must be unique.",
                case_id=case_id,
                subject_id=row_id,
                subject_kind="id",
            )
        else:
            seen.add(row_id)
            ids.append(row_id)
        if not text:
            _record(
                findings,
                observed,
                "ROUTING_ANTI_PATTERN_TEXT_REQUIRED",
                "Every routing anti-pattern row must explain the anti-pattern.",
                case_id=case_id,
                subject_id=subject,
                subject_kind="text",
            )

    if require_named_ids:
        missing_required = sorted(set(REQUIRED_ANTI_PATTERN_IDS) - set(ids))
        if missing_required:
            _record(
                findings,
                observed,
                "ROUTING_ANTI_PATTERN_REQUIRED_ID_MISSING",
                "The public routing anti-pattern fixture must preserve named macro anchors.",
                case_id=case_id,
                subject_id=",".join(missing_required),
                subject_kind="id",
            )

    for row in _walk_dicts(payload):
        overclaims = [field for field in OVERCLAIM_KEYS if row.get(field) is True]
        if overclaims:
            _record(
                findings,
                observed,
                "ROUTING_ANTI_PATTERN_AUTHORITY_OVERCLAIM",
                "Routing anti-pattern validation cannot authorize release, providers, source mutation, route-policy mutation, maturity, or correctness claims.",
                case_id=case_id,
                subject_id=",".join(sorted(overclaims)),
                subject_kind="authority_ceiling",
            )
        forbidden_roles = [
            field
            for field in AUTHORITY_ROLE_KEYS
            if str(row.get(field) or "").strip().lower()
            in FORBIDDEN_AUTHORITY_ROLES
        ]
        if forbidden_roles:
            _record(
                findings,
                observed,
                "ROUTING_ANTI_PATTERN_SOURCE_AUTHORITY_FORBIDDEN",
                "Routing anti-pattern rows can project public anti-patterns but cannot declare source, route, control-plane, or canonical authority.",
                case_id=case_id,
                subject_id=",".join(sorted(forbidden_roles)),
                subject_kind="source_authority_masquerade",
            )
        private_fields = [field for field in FORBIDDEN_PRIVATE_KEYS if row.get(field)]
        if private_fields:
            _record(
                findings,
                observed,
                "ROUTING_ANTI_PATTERN_PRIVATE_SOURCE_FORBIDDEN",
                "Public routing anti-pattern validation must carry public rows and refs, not private bodies or provider payloads.",
                case_id=case_id,
                subject_id=str(row.get("id") or row.get("case_id") or "payload"),
                subject_kind="private_source",
            )

    return {
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(value) for key, value in observed.items()
        },
    }


def _merge_observed(
    left: dict[str, list[str]], right: dict[str, set[str]]
) -> dict[str, list[str]]:
    """
    [ACTION]
    - Teleology: Implements `_merge_observed` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    merged: dict[str, set[str]] = defaultdict(set)
    for key, codes in left.items():
        merged[key].update(codes)
    for key, codes in right.items():
        merged[key].update(codes)
    return {key: sorted(value) for key, value in merged.items()}


def _route_repair_state_for_row(row: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `_route_repair_state_for_row` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    row_id = str(row.get("id") or "")
    text = str(row.get("text") or "").lower()
    requirement = ROUTE_REPAIR_STATE_REQUIREMENTS.get(row_id)
    if not requirement:
        return ""
    anchors = requirement["required_text_anchors"]
    if all(anchor in text for anchor in anchors):
        return str(requirement["route_repair_state"])
    return ""


def validate_copied_macro_registry_rows(
    payload: object,
    *,
    case_id: str = "copied_macro_routing_anti_patterns_registry",
    require_named_ids: bool = True,
) -> dict[str, Any]:
    """
    [ACTION]
    Validate copied macro registry rows from source text, not expected labels.
    - Teleology: Implements `validate_copied_macro_registry_rows` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """

    base = _payload_findings(
        payload,
        case_id=case_id,
        require_named_ids=require_named_ids,
    )
    findings = list(base["findings"])
    observed: dict[str, set[str]] = defaultdict(set)
    rows = _anti_pattern_rows(payload)
    route_repair_states: dict[str, str] = {}
    missing_route_repair_state_ids: list[str] = []
    baked_label_ids: list[str] = []

    for index, row in enumerate(rows):
        row_id = str(row.get("id") or f"anti_patterns[{index}]")
        if any(row.get(key) for key in BAKED_ROUTE_REPAIR_LABEL_KEYS):
            baked_label_ids.append(row_id)
        state = _route_repair_state_for_row(row)
        if state:
            route_repair_states[row_id] = state
            continue
        _record(
            findings,
            observed,
            "ROUTING_ANTI_PATTERN_ROUTE_REPAIR_STATE_REQUIRED",
            "Copied macro routing anti-pattern rows must carry source-backed route repair state derived from their id and text.",
            case_id=case_id,
            subject_id=row_id,
            subject_kind="route_repair_state",
        )
        missing_route_repair_state_ids.append(row_id)

    source_backed = bool(rows) and not findings and len(route_repair_states) == len(rows)
    return {
        "schema_version": "routing_anti_patterns_registry_row_validation_v1",
        "validator_id": f"{VALIDATOR_ID}.row_validator",
        "status": PASS if not findings else "blocked",
        "row_count": len(rows),
        "validated_row_count": len(route_repair_states),
        "route_repair_state_count": len(route_repair_states),
        "route_repair_states": route_repair_states,
        "missing_route_repair_state_count": len(missing_route_repair_state_ids),
        "missing_route_repair_state_ids": missing_route_repair_state_ids,
        "baked_route_repair_label_count": len(baked_label_ids),
        "baked_route_repair_label_ids": baked_label_ids,
        "baked_expected_labels_sufficient": False,
        "source_backed": source_backed,
        "finding_count": len(findings),
        "findings": findings,
        "observed_negative_cases": _merge_observed(
            base["observed_negative_cases"],
            observed,
        ),
    }


def _source_module_manifest_result(
    input_dir: Path,
    *,
    public_root: Path,
    require_manifest: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_result` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        status = "blocked" if require_manifest else "not_present"
        findings = []
        if require_manifest:
            findings.append(
                _finding(
                    "ROUTING_ANTI_PATTERN_SOURCE_MODULE_MANIFEST_REQUIRED",
                    "Exported routing anti-pattern bundle must include a source module manifest for copied macro body material.",
                    case_id="source_module_manifest",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
                    subject_kind="source_module_manifest",
                )
            )
        return {
            "status": status,
            "source_module_import_status": status,
            "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
            "module_count": 0,
            "verified_module_count": 0,
            "module_ids": [],
            "material_classes": [],
            "body_material_classes": {},
            "body_in_receipt": False,
            "source_refs": [],
            "copied_macro_registry_body_validations": [],
            "findings": findings,
        }

    manifest = read_json_strict(manifest_path)
    findings: list[dict[str, Any]] = []
    modules = _rows(manifest, "modules")
    module_ids: list[str] = []
    material_class_counts: dict[str, int] = {}
    source_refs = [_display(manifest_path, public_root=public_root)]
    copied_body_validations: list[dict[str, Any]] = []

    if not isinstance(manifest, dict):
        modules = []
        findings.append(
            _finding(
                "ROUTING_ANTI_PATTERN_SOURCE_MODULE_MANIFEST_REQUIRED",
                "Source module manifest must be a JSON object.",
                case_id="source_module_manifest",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    else:
        if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "ROUTING_ANTI_PATTERN_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module manifest must classify body imports as copied non-secret macro body material.",
                    case_id="source_module_manifest",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
                    subject_kind="source_import_class",
                )
            )
        if manifest.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "ROUTING_ANTI_PATTERN_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must keep body text out of receipts.",
                    case_id="source_module_manifest",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
                    subject_kind="body_in_receipt",
                )
            )
        if int(manifest.get("module_count") or 0) != len(modules):
            findings.append(
                _finding(
                    "ROUTING_ANTI_PATTERN_SOURCE_MODULE_COUNT_MISMATCH",
                    "Source module manifest module_count must match the module row count.",
                    case_id="source_module_manifest",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
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
                    "ROUTING_ANTI_PATTERN_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must classify copied material as non-secret macro body.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_import_class",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_BODY_CLASSES:
            findings.append(
                _finding(
                    "ROUTING_ANTI_PATTERN_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must use a public-safe macro body material class.",
                    case_id="source_module_manifest",
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
                    "ROUTING_ANTI_PATTERN_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module rows must copy body into source_modules while keeping receipt fields body-free.",
                    case_id="source_module_manifest",
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
                    "ROUTING_ANTI_PATTERN_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target body must exist inside the public bundle.",
                    case_id="source_module_manifest",
                    subject_id=target_ref or module_id,
                    subject_kind="source_module",
                )
            )
            continue
        actual = _sha256(target)
        digest_values = {
            name: str(row.get(name) or "")
            for name in ("sha256", "source_sha256", "target_sha256")
        }
        if any(value != actual for value in digest_values.values()):
            findings.append(
                _finding(
                    "ROUTING_ANTI_PATTERN_SOURCE_MODULE_DIGEST_MISMATCH",
                    "All source module digest declarations must match the copied target body.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        text = target.read_text(encoding="utf-8")
        missing_anchors = [
            anchor for anchor in _strings(row.get("required_anchors")) if anchor not in text
        ]
        if missing_anchors:
            findings.append(
                {
                    **_finding(
                        "ROUTING_ANTI_PATTERN_SOURCE_MODULE_ANCHOR_MISSING",
                        "Source module body must carry the declared macro routing anchors.",
                        case_id="source_module_manifest",
                        subject_id=module_id,
                        subject_kind="source_module",
                    ),
                    "missing_anchors": missing_anchors,
                }
            )
        try:
            copied_registry_payload = json.loads(text)
        except json.JSONDecodeError:
            findings.append(
                _finding(
                    "ROUTING_ANTI_PATTERN_SOURCE_MODULE_ROW_VALIDATOR_REJECTED",
                    "Copied source module body must be valid JSON for row validation.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module_row_validator",
                )
            )
        else:
            row_validation = validate_copied_macro_registry_rows(
                copied_registry_payload,
                case_id="source_module_manifest",
                require_named_ids=True,
            )
            if row_validation["status"] != PASS:
                findings.extend(row_validation["findings"])
            copied_body_validations.append(
                {
                    "schema_version": row_validation["schema_version"],
                    "module_id": module_id,
                    "target_ref": _display(target, public_root=public_root),
                    "validator_id": row_validation["validator_id"],
                    "status": row_validation["status"],
                    "source_backed": row_validation["source_backed"],
                    "row_count": row_validation["row_count"],
                    "validated_row_count": row_validation["validated_row_count"],
                    "route_repair_state_count": row_validation[
                        "route_repair_state_count"
                    ],
                    "missing_route_repair_state_count": row_validation[
                        "missing_route_repair_state_count"
                    ],
                    "baked_expected_labels_sufficient": row_validation[
                        "baked_expected_labels_sufficient"
                    ],
                    "finding_count": row_validation["finding_count"],
                    "error_codes": sorted(
                        {
                            str(finding.get("error_code") or "")
                            for finding in row_validation["findings"]
                            if finding.get("error_code")
                        }
                    ),
                    "body_in_receipt": False,
                }
            )
            row["row_validator_status"] = row_validation["status"]
            row["row_validator_id"] = row_validation["validator_id"]
            row["row_validator_source_backed"] = row_validation["source_backed"]
            row["row_validator_finding_count"] = row_validation["finding_count"]
        source_refs.append(_display(target, public_root=public_root))
        if len(findings) == module_findings_start:
            verified_count += 1

    status = PASS if modules and not findings else "blocked"
    return {
        "status": status,
        "source_module_import_status": (
            SOURCE_MODULE_IMPORT_STATUS if status == PASS else "blocked"
        ),
        "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
        "module_count": len(modules),
        "verified_module_count": verified_count,
        "module_ids": module_ids,
        "material_classes": sorted(material_class_counts),
        "body_material_classes": material_class_counts,
        "body_in_receipt": False,
        "source_refs": source_refs,
        "copied_macro_registry_body_validations": copied_body_validations,
        "findings": findings,
    }


def _source_open_body_import_summary(
    source_module_result: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_open_body_import_summary` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
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
        "material_classes": (
            source_module_result.get("material_classes", []) if imported else []
        ),
        "body_material_classes": (
            source_module_result.get("body_material_classes", {}) if imported else {}
        ),
        "source_manifest_refs": (
            [str(manifest_ref)] if imported and manifest_ref else []
        ),
        "aggregate_floor_ref": (
            f"{manifest_ref}::modules" if imported and manifest_ref else ""
        ),
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "body_text_exported_in_workingness": False,
        "authority_ceiling": {
            "body_text_in_receipt": False,
            "provider_payload_exported": False,
            "credential_or_account_bound_payload_exported": False,
            "release_authorized": False,
            "whole_system_correctness_claim": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported routing anti-pattern bundle for the copied macro routing "
            "anti-pattern registry body; receipts carry refs, hashes, counts, "
            "and verdicts only."
        )
        if imported
        else "",
    }


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_freshness_basis` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
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
    for path in _freshness_input_paths(source, include_negative=include_negative):
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
    schema_version = (
        "routing_anti_patterns_registry_result_v1"
        if include_negative
        else "exported_routing_anti_patterns_bundle_validation_result_v1"
    )
    basis_digest = hashlib.sha256(
        json.dumps(
            {
                "card_schema_version": CARD_SCHEMA_VERSION,
                "include_negative": include_negative,
                "inputs": rows,
                "missing_inputs": missing,
                "validator_schema_version": schema_version,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "routing_anti_patterns_registry_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_bundle_receipt(input_dir: Path, out_dir: Path) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Implements `_fresh_bundle_receipt` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
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
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
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
    - Teleology: Implements `_load_payloads` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return {Path(name).stem: read_json_strict(input_dir / name) for name in names}


def _negative_findings(payloads: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_negative_findings` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for stem in NEGATIVE_INPUT_STEMS:
        if stem not in payloads:
            continue
        payload = payloads[stem]
        case_id = (
            str(payload.get("expected_negative_case_id") or stem)
            if isinstance(payload, dict)
            else stem
        )
        result = _payload_findings(
            payload,
            case_id=case_id,
            require_named_ids=False,
        )
        findings.extend(result["findings"])
        for key, codes in result["observed_negative_cases"].items():
            observed[key].update(codes)
    return {
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(value) for key, value in observed.items()
        },
    }


def _build_board(*, result: dict[str, Any], secret_scan: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_board` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "routing_anti_patterns_registry_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "selected_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "public_runtime_refs": PUBLIC_RUNTIME_REFS,
        "routing_anti_pattern_projection": {
            "anti_pattern_count": result["anti_pattern_count"],
            "required_anti_pattern_count": len(REQUIRED_ANTI_PATTERN_IDS),
            "source_open_body_material_count": result["body_copied_material_count"],
            "body_in_receipt": False,
        },
        "public_contract": {
            "kind_required": True,
            "version_required": True,
            "anti_pattern_rows_required": True,
            "stable_unique_ids_required": True,
            "text_required": True,
            "copied_macro_body_source_modules_required_for_exported_bundle": True,
            "private_source_bodies_forbidden": True,
            "authority_overclaims_rejected": True,
            "source_authority_masquerade_rejected": True,
            "body_in_receipt": False,
            "real_runtime_receipt": result["real_runtime_receipt"],
            "synthetic_receipt_standin_allowed": False,
        },
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
        "real_runtime_receipt": result["real_runtime_receipt"],
        "synthetic_receipt_standin_allowed": False,
    }


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_common_receipt` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    keys = (
        "status",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "input_mode",
        "bundle_id",
        "source_pattern_ids",
        "source_refs",
        "public_runtime_refs",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "authority_ceiling",
        "anti_claim",
        "anti_pattern_count",
        "required_anti_pattern_ids",
        "covered_anti_pattern_ids",
        "source_module_manifest_status",
        "source_module_manifest_ref",
        "source_module_import_status",
        "source_module_summary",
        "source_open_body_imports",
        "copied_macro_registry_body_validation",
        "row_validator_id",
        "route_repair_state_validation",
        "body_material_status",
        "body_copied_material_count",
        "body_in_receipt",
        "real_runtime_receipt",
        "synthetic_receipt_standin_allowed",
        "freshness_basis",
        "receipt_reused",
    )
    payload = {
        "schema_version": schema_version,
        "receipt_id": schema_version,
        "created_at": result["created_at"],
        "receipt_paths": receipt_paths,
    }
    for key in keys:
        payload[key] = result.get(key)
    return payload


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_relative_receipt_paths` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [_display(path, public_root=public_root) for path in paths.values()]


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_result` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    source_module_result = _source_module_manifest_result(
        input_dir,
        public_root=public_root,
        require_manifest=not include_negative,
    )
    source_open_body_imports = _source_open_body_import_summary(source_module_result)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _scan_paths_for_input(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )

    registry_payload = payloads["routing_anti_patterns"]
    positive = validate_copied_macro_registry_rows(
        registry_payload,
        case_id="positive_routing_anti_patterns",
        require_named_ids=True,
    )
    negative = _negative_findings(
        {name: payloads[name] for name in NEGATIVE_INPUT_STEMS if name in payloads}
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    observed = negative["observed_negative_cases"]
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = [
        *positive["findings"],
        *negative["findings"],
        *source_module_result["findings"],
    ]
    error_codes = sorted({finding["error_code"] for finding in findings})
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    anti_pattern_rows = _anti_pattern_rows(registry_payload)
    covered_ids = sorted(
        {
            str(row.get("id") or "")
            for row in anti_pattern_rows
            if row.get("id")
        }
    )
    source_module_refs = [
        str(ref)
        for ref in source_module_result.get("source_refs", [])
        if isinstance(ref, str)
    ]
    copied_body_validations = [
        row
        for row in source_module_result.get(
            "copied_macro_registry_body_validations", []
        )
        if isinstance(row, dict)
    ]
    status = (
        PASS
        if not positive["findings"]
        and not missing
        and not secret_scan["blocking_hit_count"]
        and source_module_result["status"] in {PASS, "not_present"}
        else "blocked"
    )
    return {
        "schema_version": "routing_anti_patterns_registry_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "source_refs": [*SOURCE_REFS, *source_module_refs],
        "public_runtime_refs": PUBLIC_RUNTIME_REFS,
        "expected_negative_cases": expected,
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "anti_pattern_count": len(anti_pattern_rows),
        "required_anti_pattern_ids": list(REQUIRED_ANTI_PATTERN_IDS),
        "covered_anti_pattern_ids": covered_ids,
        "source_module_manifest_status": source_module_result["status"],
        "source_module_manifest_ref": source_module_result["source_module_manifest_ref"],
        "source_module_import_status": source_module_result["source_module_import_status"],
        "source_module_summary": source_module_result,
        "source_open_body_imports": source_open_body_imports,
        "copied_macro_registry_body_validation": {
            "schema_version": "routing_anti_patterns_registry_copied_macro_body_validation_v1",
            "status": (
                PASS
                if copied_body_validations
                and all(row.get("status") == PASS for row in copied_body_validations)
                else source_module_result["status"]
            ),
            "body_validation_count": len(copied_body_validations),
            "source_backed_validation_count": sum(
                1 for row in copied_body_validations if row.get("source_backed") is True
            ),
            "validations": copied_body_validations,
            "body_in_receipt": False,
            "body_text_in_receipt": False,
        },
        "row_validator_id": positive["validator_id"],
        "route_repair_state_validation": {
            "schema_version": positive["schema_version"],
            "validator_id": positive["validator_id"],
            "status": positive["status"],
            "row_count": positive["row_count"],
            "validated_row_count": positive["validated_row_count"],
            "route_repair_state_count": positive["route_repair_state_count"],
            "missing_route_repair_state_count": positive[
                "missing_route_repair_state_count"
            ],
            "missing_route_repair_state_ids": positive[
                "missing_route_repair_state_ids"
            ],
            "baked_route_repair_label_count": positive[
                "baked_route_repair_label_count"
            ],
            "baked_expected_labels_sufficient": positive[
                "baked_expected_labels_sufficient"
            ],
            "source_backed": positive["source_backed"],
            "finding_count": positive["finding_count"],
        },
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports["body_material_count"],
        "body_in_receipt": False,
        "real_runtime_receipt": status == PASS,
        "synthetic_receipt_standin_allowed": False,
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_write_receipts` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    public_root = _public_root_for_path(out_dir)
    paths = {
        "result": out_dir / RESULT_NAME,
        "board": out_dir / BOARD_NAME,
        "validation": out_dir / VALIDATION_RECEIPT_NAME,
    }
    if acceptance_out is not None:
        paths["acceptance"] = acceptance_out
    relative_paths = _relative_receipt_paths(paths, public_root)
    board = _build_board(result=result, secret_scan=result["secret_exclusion_scan"])
    result_receipt = _common_receipt(
        result,
        schema_version="routing_anti_patterns_registry_result_receipt_v1",
        receipt_paths=relative_paths,
    )
    board["receipt_paths"] = relative_paths
    validation = _common_receipt(
        result,
        schema_version="routing_anti_patterns_registry_validation_receipt_v1",
        receipt_paths=relative_paths,
    )
    validation["board_ref"] = _display(paths["board"], public_root=public_root)
    validation["result_ref"] = _display(paths["result"], public_root=public_root)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(paths["result"], result_receipt)
    write_json_atomic(paths["board"], board)
    write_json_atomic(paths["validation"], validation)
    if acceptance_out is not None:
        acceptance = _common_receipt(
            result,
            schema_version="routing_anti_patterns_registry_fixture_acceptance_v1",
            receipt_paths=relative_paths,
        )
        write_json_atomic(acceptance_out, acceptance)
    result["receipt_paths"] = relative_paths
    return result


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.routing_anti_patterns_registry run",
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source = Path(input_dir)
    target = Path(out_dir)
    result = _build_result(
        source,
        command=command,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=True)
    result["receipt_reused"] = False
    return _write_receipts(
        result,
        target,
        acceptance_out=Path(acceptance_out) if acceptance_out else None,
    )


def run_routing_anti_patterns_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.routing_anti_patterns_registry run-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_routing_anti_patterns_bundle` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    source = Path(input_dir)
    target = Path(out_dir)
    if reuse_fresh_receipt:
        cached = _fresh_bundle_receipt(source, target)
        if cached is not None:
            return cached
    public_root = _public_root_for_path(target)
    result = _build_result(
        source,
        command=command,
        input_mode="exported_routing_anti_patterns_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    path = target / BUNDLE_RESULT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = _display(path, public_root=public_root)
    receipt = _common_receipt(
        result,
        schema_version="exported_routing_anti_patterns_bundle_validation_result_v1",
        receipt_paths=[receipt_path],
    )
    write_json_atomic(path, receipt)
    result["receipt_paths"] = [receipt_path]
    return result


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": (
                result.get("freshness_basis", {}).get("basis_digest")
                if isinstance(result.get("freshness_basis"), dict)
                else None
            ),
            "freshness_input_count": (
                result.get("freshness_basis", {}).get("input_count")
                if isinstance(result.get("freshness_basis"), dict)
                else None
            ),
            "freshness_missing_path_count": (
                result.get("freshness_basis", {}).get("missing_path_count")
                if isinstance(result.get("freshness_basis"), dict)
                else None
            ),
        },
        "routing_anti_pattern_projection": {
            "anti_pattern_count": result.get("anti_pattern_count"),
            "required_anti_pattern_count": len(REQUIRED_ANTI_PATTERN_IDS),
            "source_open_body_material_count": result.get("body_copied_material_count"),
            "route_repair_state_count": (
                (result.get("route_repair_state_validation") or {}).get(
                    "route_repair_state_count"
                )
                if isinstance(result.get("route_repair_state_validation"), dict)
                else None
            ),
        },
        "source_open_body_imports": {
            "status": (result.get("source_open_body_imports") or {}).get("status")
            if isinstance(result.get("source_open_body_imports"), dict)
            else None,
            "body_material_count": (
                (result.get("source_open_body_imports") or {}).get("body_material_count")
                if isinstance(result.get("source_open_body_imports"), dict)
                else None
            ),
            "source_module_manifest_ref": result.get("source_module_manifest_ref"),
            "body_in_receipt": False,
            "body_text_in_receipt": False,
        },
        "validation": {
            "missing_negative_case_count": len(result.get("missing_negative_cases") or []),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
            "row_validator_source_backed": (
                (result.get("route_repair_state_validation") or {}).get(
                    "source_backed"
                )
                is True
            )
            if isinstance(result.get("route_repair_state_validation"), dict)
            else False,
            "real_runtime_receipt": result.get("real_runtime_receipt") is True,
            "synthetic_receipt_standin_allowed": (
                result.get("synthetic_receipt_standin_allowed") is True
            ),
        },
        "authority_boundary": {
            "route_policy_mutation_authorized": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
            "private_data_equivalence_claim": False,
            "whole_system_correctness_claim": False,
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
    - Teleology: Implements `_parser` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(
        description="Validate public routing anti-pattern registry"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.routing_anti_patterns_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = _parser().parse_args(argv)
    if args.command == "run":
        card_suffix = " --card" if args.card else ""
        command = (
            "python -m microcosm_core.organs.routing_anti_patterns_registry run "
            f"--input {args.input} --out {args.out}{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    else:
        card_suffix = " --card" if args.card else ""
        command = (
            "python -m microcosm_core.organs.routing_anti_patterns_registry "
            f"run-bundle --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run_routing_anti_patterns_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
