"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.cold_reader_route_map` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, ACCEPTANCE_RECEIPT_REL, BUNDLE_RESULT_NAME, SOURCE_MODULE_MANIFEST_NAME, CARD_SCHEMA_VERSION, CARD_OMITTED_FULL_PAYLOAD_KEYS, HASH_CHUNK_SIZE, REAL_BODY_MATERIAL_STATUS, PUBLIC_SAFE_BODY_CLASSES, SOURCE_PATTERN_IDS, SOURCE_REFS, ROUTE_SOURCE_REPLAY_PUBLIC_REFS, PUBLIC_RUNTIME_REFS, INPUT_NAMES, NEGATIVE_INPUT_NAMES, NEGATIVE_INPUT_STEMS, EXPECTED_NEGATIVE_CASES, FRONT_DOOR_ROUTE_COMMANDS, FRONT_DOOR_ROUTE_IDS, ...
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
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import (
    normalize_public_receipt_paths,
    utc_now,
    write_json_atomic,
)
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "cold_reader_route_map"
FIXTURE_ID = "first_wave.cold_reader_route_map"
VALIDATOR_ID = "validator.microcosm.organs.cold_reader_route_map"

RESULT_NAME = "cold_reader_route_map_result.json"
BOARD_NAME = "cold_reader_route_map_board.json"
VALIDATION_RECEIPT_NAME = "cold_reader_route_map_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/cold_reader_route_map_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_cold_reader_route_map_bundle_validation_result.json"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
CARD_SCHEMA_VERSION = "cold_reader_route_map_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "source_module_results",
    "route_source_replay",
    "secret_exclusion_scan",
    "findings",
    "source_module_refs",
    "real_substrate_refs",
    "public_runtime_refs",
    "receipt_paths",
    "anti_claim",
    "authority_ceiling",
)
HASH_CHUNK_SIZE = 1024 * 1024
REAL_BODY_MATERIAL_STATUS = (
    "copied_non_secret_macro_cold_entry_route_substrate_with_provenance"
)
PUBLIC_SAFE_BODY_CLASSES = {
    "public_macro_pattern_body",
    "public_macro_tool_body",
    "public_macro_receipt_body",
    "public_macro_proof_body",
    "public_standard_body",
}

SOURCE_PATTERN_IDS = [
    "navigation_hologram_unified_route_plane",
    "compression_profile_governed_option_surface",
    "entry_agent_behavior_governance_suborgan",
]
SOURCE_REFS = [
    "microcosm-substrate/src/microcosm_core/runtime_shell.py",
    "microcosm-substrate/README.md",
    "microcosm-substrate/AGENTS.md",
]
ROUTE_SOURCE_REPLAY_PUBLIC_REFS = (
    *SOURCE_REFS,
    "microcosm-substrate/src/microcosm_core/cli.py",
    "microcosm-substrate/src/microcosm_core/project_substrate.py",
)
PUBLIC_RUNTIME_REFS = [
    "fixtures/first_wave/cold_reader_route_map/input/route_map.json",
    "fixtures/first_wave/cold_reader_route_map/input/route_receipts.json",
    "fixtures/first_wave/cold_reader_route_map/input/route_policy.json",
    "examples/cold_reader_route_map/exported_cold_reader_route_map_bundle",
    "paper_modules/cold_reader_route_map.md",
]

INPUT_NAMES = ("route_map.json", "route_receipts.json", "route_policy.json")
NEGATIVE_INPUT_NAMES = (
    "missing_command_ref.json",
    "missing_receipt_ref.json",
    "route_sequence_gap.json",
    "release_overclaim.json",
    "private_source_leakage.json",
)
NEGATIVE_INPUT_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)

EXPECTED_NEGATIVE_CASES = {
    "missing_command_ref": ["COLD_ROUTE_MISSING_COMMAND_REF"],
    "missing_receipt_ref": ["COLD_ROUTE_MISSING_RECEIPT_REF"],
    "route_sequence_gap": ["COLD_ROUTE_SEQUENCE_GAP"],
    "release_overclaim": ["COLD_ROUTE_AUTHORITY_OVERCLAIM"],
    "private_source_leakage": ["COLD_ROUTE_PRIVATE_SOURCE_FORBIDDEN"],
}

FRONT_DOOR_ROUTE_COMMANDS = {
    "tour_project": "plectis tour <project>",
    "status_card": "plectis status --card <project>",
    "proof_lab": "plectis proof-lab --out /tmp/microcosm-proof-lab",
}
FRONT_DOOR_ROUTE_IDS = tuple(FRONT_DOOR_ROUTE_COMMANDS)

FORBIDDEN_PRIVATE_KEYS = (
    "private_source_body",
    "raw_seed_body",
    "provider_payload_body",
    "secret_value",
)
OVERCLAIM_KEYS = (
    "release_authorized",
    "publication_authorized",
    "provider_calls_authorized",
    "private_data_equivalence_claim",
    "whole_system_correctness_claim",
    "trading_or_financial_advice_authorized",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "cold_reader_route_map_projection_only_not_route_authority",
    "route_registry_authority": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
    "provider_calls_authorized": False,
    "private_data_equivalence_claim": False,
    "whole_system_correctness_claim": False,
}

SOURCE_REPLAY_STOPWORDS = {
    "and",
    "are",
    "for",
    "from",
    "into",
    "not",
    "only",
    "refs",
    "ref",
    "the",
    "with",
}

ANTI_CLAIM = (
    "The cold-reader route map validates a public ten-minute route projection only. "
    "It does not become route registry authority, expose private macro sources, "
    "authorize release, call providers, mutate source projects, or prove whole-system "
    "correctness."
)


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_display` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_relative_path(path, display_root=public_root)


def _stored_receipt_command(command: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_stored_receipt_command` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    normalized = normalize_public_receipt_paths({"command": command})
    value = normalized.get("command") if isinstance(normalized, dict) else command
    return value if isinstance(value, str) else command


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_rows` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names]


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_payloads` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return {Path(name).stem: read_json_strict(input_dir / name) for name in names}


def _sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
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


def _line_count_from_text(text: str) -> int:
    """
    [ACTION]
    - Teleology: Implements `_line_count_from_text` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _line_count(path: Path) -> int:
    """
    [ACTION]
    - Teleology: Implements `_line_count` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
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


def _source_module_target_path(
    input_dir: Path,
    row: dict[str, Any],
    *,
    public_root: Path,
) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_target_path` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    row_path = str(row.get("path") or "")
    if row_path and not Path(row_path).is_absolute() and ".." not in Path(row_path).parts:
        return input_dir / row_path
    target_ref = str(row.get("target_ref") or "")
    if target_ref.startswith("microcosm-substrate/"):
        target_ref = target_ref.removeprefix("microcosm-substrate/")
    if target_ref and not Path(target_ref).is_absolute() and ".." not in Path(target_ref).parts:
        return public_root / target_ref
    return input_dir / "__invalid_source_module_target__"


def _source_module_paths(input_dir: Path, manifest_payload: object | None = None) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_paths` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    manifest = manifest_payload if isinstance(manifest_payload, dict) else None
    if manifest is None and manifest_path.is_file():
        manifest = read_json_strict(manifest_path)
    if not isinstance(manifest, dict):
        return []
    public_root = _public_root_for_path(input_dir)
    return [
        _source_module_target_path(input_dir, row, public_root=public_root)
        for row in _rows(manifest, "modules")
    ]


def _normalized_text(value: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_normalized_text` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return re.sub(r"\s+", " ", value.lower()).strip()


def _material_terms(value: str) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_material_terms` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    terms = re.findall(r"[a-z0-9][a-z0-9_-]*", value.lower())
    return [
        term
        for term in terms
        if len(term) >= 3 and term not in SOURCE_REPLAY_STOPWORDS
    ]


def _slugify_heading(value: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_slugify_heading` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    text = re.sub(r"[`*_~]", "", value.strip())
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).lower()
    text = re.sub(r"\s+", "-", text.strip())
    return re.sub(r"-+", "-", text)


def _public_ref_path(public_root: Path, ref: str) -> tuple[Path | None, str]:
    """
    [ACTION]
    - Teleology: Implements `_public_ref_path` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    path_ref, _separator, anchor = ref.partition("#")
    path_ref = path_ref.removeprefix("microcosm-substrate/")
    path = Path(path_ref)
    if not path_ref or path.is_absolute() or ".." in path.parts:
        return None, anchor
    return public_root / path, anchor


def _heading_anchors(text: str) -> set[str]:
    """
    [ACTION]
    - Teleology: Implements `_heading_anchors` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    anchors: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            anchors.add(_slugify_heading(stripped.lstrip("#").strip()))
    return anchors


def _document_ref_result(ref: str, *, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_document_ref_result` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    path, anchor = _public_ref_path(public_root, ref)
    if path is None:
        return {
            "ref": ref,
            "status": "blocked",
            "error_code": "COLD_ROUTE_DOC_REF_UNRESOLVED",
            "reason": "invalid_public_ref",
        }
    exists = path.is_file()
    if not exists:
        return {
            "ref": ref,
            "status": "blocked",
            "error_code": "COLD_ROUTE_DOC_REF_UNRESOLVED",
            "reason": "missing_public_doc",
        }
    text = path.read_text(encoding="utf-8")
    anchor_status = PASS
    if anchor and anchor not in _heading_anchors(text):
        anchor_status = "blocked"
    return {
        "ref": ref,
        "path": _display(path, public_root=public_root),
        "anchor": anchor,
        "status": PASS if anchor_status == PASS else "blocked",
        "error_code": None
        if anchor_status == PASS
        else "COLD_ROUTE_DOC_REF_ANCHOR_MISSING",
        "reason": "resolved" if anchor_status == PASS else "missing_heading_anchor",
    }


def _receipt_ref_result(ref: str, *, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_receipt_ref_result` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    path, _anchor = _public_ref_path(public_root, ref)
    if path is None:
        return {
            "ref": ref,
            "status": "blocked",
            "error_code": "COLD_ROUTE_RECEIPT_REF_UNRESOLVED",
            "reason": "invalid_public_ref",
        }
    if not path.is_file():
        return {
            "ref": ref,
            "status": "blocked",
            "error_code": "COLD_ROUTE_RECEIPT_REF_UNRESOLVED",
            "reason": "missing_receipt",
        }
    try:
        payload = read_json_strict(path)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return {
            "ref": ref,
            "path": _display(path, public_root=public_root),
            "status": "blocked",
            "error_code": "COLD_ROUTE_RECEIPT_REF_UNRESOLVED",
            "reason": "receipt_not_json_object",
        }
    receipt_status = payload.get("status") if isinstance(payload, dict) else None
    if receipt_status != PASS:
        return {
            "ref": ref,
            "path": _display(path, public_root=public_root),
            "status": "blocked",
            "receipt_status": receipt_status,
            "error_code": "COLD_ROUTE_RECEIPT_STATUS_UNSUPPORTED",
            "reason": "receipt_status_not_pass",
        }
    return {
        "ref": ref,
        "path": _display(path, public_root=public_root),
        "status": PASS,
        "receipt_status": receipt_status,
        "error_code": None,
        "reason": "resolved_pass_receipt",
    }


def _text_record(
    records: list[dict[str, str]],
    path: Path,
    *,
    public_root: Path,
    source_kind: str,
    seen: set[Path],
) -> None:
    """
    [ACTION]
    - Teleology: Implements `_text_record` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    resolved = path.resolve(strict=False)
    if resolved in seen or not path.is_file():
        return
    seen.add(resolved)
    records.append(
        {
            "ref": _display(path, public_root=public_root),
            "source_kind": source_kind,
            "text": path.read_text(encoding="utf-8"),
        }
    )


def _source_replay_text_records(
    input_dir: Path,
    *,
    public_root: Path,
    source_manifest_payload: object,
    route_rows: list[dict[str, Any]],
    receipt_rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """
    [ACTION]
    - Teleology: Implements `_source_replay_text_records` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    records: list[dict[str, str]] = []
    seen: set[Path] = set()
    for path in _source_module_paths(input_dir, source_manifest_payload):
        _text_record(records, path, public_root=public_root, source_kind="copied_source_module", seen=seen)
    for ref in ROUTE_SOURCE_REPLAY_PUBLIC_REFS:
        path, _anchor = _public_ref_path(public_root, ref)
        if path is not None:
            _text_record(records, path, public_root=public_root, source_kind="public_source_ref", seen=seen)
    for row in route_rows:
        for ref in row.get("docs_refs", []):
            if not isinstance(ref, str):
                continue
            path, _anchor = _public_ref_path(public_root, ref)
            if path is not None:
                _text_record(records, path, public_root=public_root, source_kind="docs_ref", seen=seen)
    for row in receipt_rows:
        for ref in row.get("receipt_refs", []):
            if not isinstance(ref, str):
                continue
            path, _anchor = _public_ref_path(public_root, ref)
            if path is not None:
                _text_record(records, path, public_root=public_root, source_kind="receipt_ref", seen=seen)
    return records


def _command_support(command: str, *, corpus_text: str, corpus_normalized: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_command_support` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    command = command.strip()
    variants = {
        command,
        command.replace("<project>", "."),
        command.replace("<project>", "/tmp/microcosm-scratch"),
        command.replace("<selected_route_id>", "<route_id>"),
        command.replace("<selected_route_id>", "$MICROCOSM_ROUTE_ID"),
    }
    exact_supported = any(
        _normalized_text(variant) in corpus_normalized for variant in variants if variant
    )
    material_tokens = [
        token.strip("'\"")
        for token in re.split(r"\s+", command)
        if token
        and token != "microcosm"
        and not (token.startswith("<") and token.endswith(">"))
    ]
    missing_tokens = [
        token
        for token in material_tokens
        if _normalized_text(token) not in corpus_text
        and _normalized_text(token) not in corpus_normalized
    ]
    return {
        "status": PASS if exact_supported or not missing_tokens else "blocked",
        "exact_command_supported": exact_supported,
        "material_tokens": material_tokens,
        "missing_material_tokens": missing_tokens,
    }


def _mechanism_signal_support(
    row: dict[str, Any],
    *,
    corpus_normalized: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_mechanism_signal_support` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    signals = [signal for signal in row.get("shows", []) if isinstance(signal, str)]
    signal_rows = []
    for signal in signals:
        terms = _material_terms(signal)
        missing_terms = [term for term in terms if term not in corpus_normalized]
        signal_rows.append(
            {
                "signal": signal,
                "status": PASS if not missing_terms else "blocked",
                "material_terms": terms,
                "missing_terms": missing_terms,
            }
        )
    blocked = [signal for signal in signal_rows if signal["status"] != PASS]
    return {
        "status": PASS if signals and not blocked else "blocked",
        "signal_count": len(signal_rows),
        "supported_signal_count": len(signal_rows) - len(blocked),
        "signals": signal_rows,
    }


def _route_source_replay_result(
    input_dir: Path,
    *,
    public_root: Path,
    route_rows: list[dict[str, Any]],
    receipt_rows: list[dict[str, Any]],
    source_manifest_payload: object,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_route_source_replay_result` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    text_records = _source_replay_text_records(
        input_dir,
        public_root=public_root,
        source_manifest_payload=source_manifest_payload,
        route_rows=route_rows,
        receipt_rows=receipt_rows,
    )
    corpus_text = _normalized_text("\n".join(row["text"] for row in text_records))
    receipt_refs_by_id = {
        str(row.get("route_id") or ""): [
            str(ref)
            for ref in row.get("receipt_refs", [])
            if isinstance(ref, str) and ref
        ]
        for row in receipt_rows
        if row.get("route_id")
    }
    findings: list[dict[str, Any]] = []
    replay_rows = []
    for row in route_rows:
        route_id = _route_id(row)
        command = str(row.get("command") or "")
        docs_refs = [
            str(ref) for ref in row.get("docs_refs", []) if isinstance(ref, str) and ref
        ]
        receipt_refs = receipt_refs_by_id.get(route_id, [])
        doc_results = [_document_ref_result(ref, public_root=public_root) for ref in docs_refs]
        receipt_results = [
            _receipt_ref_result(ref, public_root=public_root) for ref in receipt_refs
        ]
        command_result = _command_support(
            command,
            corpus_text=corpus_text,
            corpus_normalized=corpus_text,
        )
        signal_result = _mechanism_signal_support(row, corpus_normalized=corpus_text)
        route_findings: list[dict[str, Any]] = []
        if command_result["status"] != PASS:
            route_findings.append(
                _finding(
                    "COLD_ROUTE_COMMAND_SOURCE_UNSUPPORTED",
                    "Route command must be supported by copied or public source text.",
                    case_id="source_replay",
                    subject_id=route_id,
                    subject_kind="command",
                )
            )
        for result in doc_results:
            if result["status"] != PASS:
                route_findings.append(
                    _finding(
                        str(result["error_code"]),
                        "Route docs refs must resolve to public files and heading anchors.",
                        case_id="source_replay",
                        subject_id=route_id,
                        subject_kind="docs_refs",
                    )
                )
        for result in receipt_results:
            if result["status"] != PASS:
                route_findings.append(
                    _finding(
                        str(result["error_code"]),
                        "Route receipt refs must open public pass-status receipts.",
                        case_id="source_replay",
                        subject_id=route_id,
                        subject_kind="receipt_refs",
                    )
                )
        if signal_result["status"] != PASS:
            route_findings.append(
                _finding(
                    "COLD_ROUTE_MECHANISM_SIGNAL_UNSUPPORTED",
                    "Route mechanism signals must be supported by copied source, public docs, or receipts.",
                    case_id="source_replay",
                    subject_id=route_id,
                    subject_kind="shows",
                )
            )
        findings.extend(route_findings)
        replay_rows.append(
            {
                "route_id": route_id,
                "status": PASS if not route_findings else "blocked",
                "command_support": command_result,
                "docs_ref_results": doc_results,
                "receipt_ref_results": receipt_results,
                "mechanism_signal_support": signal_result,
                "finding_count": len(route_findings),
            }
        )
    supported_routes = [row for row in replay_rows if row["status"] == PASS]
    docs_ref_results = [
        result for row in replay_rows for result in row["docs_ref_results"]
    ]
    receipt_ref_results = [
        result for row in replay_rows for result in row["receipt_ref_results"]
    ]
    return {
        "status": PASS if not findings else "blocked",
        "verification_mode": (
            "route_commands_docs_receipts_and_mechanism_signals_replayed_against_"
            "copied_public_source_docs_and_pass_receipts"
        ),
        "source_record_count": len(text_records),
        "source_refs": [row["ref"] for row in text_records],
        "route_count": len(replay_rows),
        "supported_route_count": len(supported_routes),
        "docs_ref_count": len(docs_ref_results),
        "resolved_docs_ref_count": sum(
            1 for result in docs_ref_results if result["status"] == PASS
        ),
        "receipt_ref_count": len(receipt_ref_results),
        "resolved_pass_receipt_ref_count": sum(
            1 for result in receipt_ref_results if result["status"] == PASS
        ),
        "rows": replay_rows,
        "findings": findings,
    }


def _walk_dicts(value: object) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_walk_dicts` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_finding` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_record` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
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


def _route_rows(payload: object) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_route_rows` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(payload, "routes")
    if rows:
        return rows
    return _rows(payload, "rows")


def _receipt_rows(payload: object) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_receipt_rows` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(payload, "route_receipts")
    if rows:
        return rows
    return _rows(payload, "rows")


def _route_id(row: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `_route_id` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return str(row.get("route_id") or row.get("step_id") or "").strip()


def _positive_findings(
    *,
    route_rows: list[dict[str, Any]],
    receipt_rows: list[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_positive_findings` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    route_by_id = {_route_id(row): row for row in route_rows if _route_id(row)}
    receipts_by_id = {
        str(row.get("route_id") or ""): row
        for row in receipt_rows
        if row.get("route_id")
    }
    required_route_ids = [
        str(route_id)
        for route_id in policy.get("required_route_ids", [])
        if isinstance(route_id, str)
    ]
    for route_id in required_route_ids:
        row = route_by_id.get(route_id)
        if row is None:
            _record(
                findings,
                observed,
                "COLD_ROUTE_SEQUENCE_GAP",
                "Every required cold-reader route must exist in the route map.",
                case_id="positive_route_map",
                subject_id=route_id,
                subject_kind="route_id",
            )
            continue
        if not row.get("command"):
            _record(
                findings,
                observed,
                "COLD_ROUTE_MISSING_COMMAND_REF",
                "Every cold-reader route must name its runnable command.",
                case_id="positive_route_map",
                subject_id=route_id,
                subject_kind="command",
            )
        if not row.get("docs_refs"):
            _record(
                findings,
                observed,
                "COLD_ROUTE_MISSING_DOC_REF",
                "Every cold-reader route must name a public docs reference.",
                case_id="positive_route_map",
                subject_id=route_id,
                subject_kind="docs_refs",
            )
        receipt_row = receipts_by_id.get(route_id)
        receipt_refs = []
        if receipt_row is not None and isinstance(receipt_row.get("receipt_refs"), list):
            receipt_refs = receipt_row["receipt_refs"]
        if not receipt_refs:
            _record(
                findings,
                observed,
                "COLD_ROUTE_MISSING_RECEIPT_REF",
                "Every cold-reader route must point at at least one evidence receipt.",
                case_id="positive_route_map",
                subject_id=route_id,
                subject_kind="receipt_refs",
            )

    sequence = [
        str(route_id)
        for route_id in policy.get("first_run_sequence", [])
        if isinstance(route_id, str)
    ]
    if sequence[: len(FRONT_DOOR_ROUTE_IDS)] != list(FRONT_DOOR_ROUTE_IDS):
        _record(
            findings,
            observed,
            "COLD_ROUTE_SEQUENCE_GAP",
            "The first-run route sequence must start with tour, status card, and proof lab.",
            case_id="positive_route_map",
            subject_id="first_run_sequence",
            subject_kind="sequence",
        )
    for route_id, expected_command in FRONT_DOOR_ROUTE_COMMANDS.items():
        row = route_by_id.get(route_id)
        if row is not None and row.get("command") != expected_command:
            _record(
                findings,
                observed,
                "COLD_ROUTE_FRONT_DOOR_COMMAND_DRIFT",
                "Front-door route commands must match the live first-screen command path.",
                case_id="positive_route_map",
                subject_id=route_id,
                subject_kind="command",
            )
    ordinals = {
        route_id: route_by_id.get(route_id, {}).get("ordinal")
        for route_id in sequence
        if route_id in route_by_id
    }
    if len(ordinals) != len(sequence) or sorted(ordinals.values()) != list(ordinals.values()):
        _record(
            findings,
            observed,
            "COLD_ROUTE_SEQUENCE_GAP",
            "The first-run route sequence must be present and ordinal sorted.",
            case_id="positive_route_map",
            subject_id="first_run_sequence",
            subject_kind="sequence",
        )
    return findings


def _negative_findings(payloads: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_negative_findings` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for case_id, payload in payloads.items():
        if case_id not in NEGATIVE_INPUT_STEMS:
            continue
        for row in _walk_dicts(payload):
            subject_id = str(
                row.get("route_id")
                or row.get("case_id")
                or row.get("id")
                or case_id
            )
            if case_id == "missing_command_ref" and not row.get("command"):
                _record(
                    findings,
                    observed,
                    "COLD_ROUTE_MISSING_COMMAND_REF",
                    "A route card without a command cannot guide a cold reader.",
                    case_id=case_id,
                    subject_id=subject_id,
                    subject_kind="command",
                )
            if case_id == "missing_receipt_ref" and not row.get("receipt_refs"):
                _record(
                    findings,
                    observed,
                    "COLD_ROUTE_MISSING_RECEIPT_REF",
                    "A route card without receipt refs is not evidence-backed.",
                    case_id=case_id,
                    subject_id=subject_id,
                    subject_kind="receipt_refs",
            )
            if case_id == "route_sequence_gap":
                sequence = row.get("first_run_sequence", [])
                if isinstance(sequence, list) and sequence[:1] != ["tour_project"]:
                    _record(
                        findings,
                        observed,
                        "COLD_ROUTE_SEQUENCE_GAP",
                        "The first-run sequence must start from tour_project.",
                        case_id=case_id,
                        subject_id=subject_id,
                        subject_kind="first_run_sequence",
                    )
            if case_id == "private_source_leakage" and any(
                key in row for key in FORBIDDEN_PRIVATE_KEYS
            ):
                _record(
                    findings,
                    observed,
                    "COLD_ROUTE_PRIVATE_SOURCE_FORBIDDEN",
                    "Cold-reader route maps must not carry private source bodies.",
                    case_id=case_id,
                    subject_id=subject_id,
                    subject_kind="private_source",
                )
            if case_id == "release_overclaim":
                for key in OVERCLAIM_KEYS:
                    if row.get(key) is True:
                        _record(
                            findings,
                            observed,
                            "COLD_ROUTE_AUTHORITY_OVERCLAIM",
                            "Cold-reader route maps cannot authorize release or global authority.",
                            case_id=case_id,
                            subject_id=subject_id,
                            subject_kind=key,
                        )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _source_module_import_result(
    input_dir: Path,
    *,
    public_root: Path,
    required: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_import_result` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    manifest = read_json_strict(manifest_path) if manifest_path.is_file() else {}
    rows = _rows(manifest, "modules")
    findings: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []

    if required and not manifest_path.is_file():
        findings.append(
            _finding(
                "COLD_ROUTE_SOURCE_MODULE_MANIFEST_MISSING",
                "Exported cold-reader route-map bundle must include copied source module provenance.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if manifest_path.is_file() and manifest.get("source_import_class") != (
        "copied_non_secret_macro_body"
    ):
        findings.append(
            _finding(
                "COLD_ROUTE_SOURCE_MODULE_IMPORT_CLASS_UNSUPPORTED",
                "Cold-reader source module manifest must declare copied_non_secret_macro_body.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if manifest_path.is_file() and manifest.get("body_in_receipt") is True:
        findings.append(
            _finding(
                "COLD_ROUTE_SOURCE_BODY_RECEIPT_EXPORT_FORBIDDEN",
                "Copied source bodies must live in the bundle source_modules tree, not in receipts.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if required and manifest_path.is_file() and not rows:
        findings.append(
            _finding(
                "COLD_ROUTE_SOURCE_MODULE_ROWS_MISSING",
                "Exported cold-reader route-map bundle must carry copied source module rows.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    expected_count = manifest.get("module_count")
    if manifest_path.is_file() and expected_count != len(rows):
        findings.append(
            _finding(
                "COLD_ROUTE_SOURCE_MODULE_COUNT_MISMATCH",
                "Source module manifest module_count must equal its module rows.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )

    for row in rows:
        module_id = str(row.get("module_id") or "source_module")
        target = _source_module_target_path(input_dir, row, public_root=public_root)
        target_exists = target.is_file()
        expected_digest = str(row.get("sha256") or "")
        actual_digest = _sha256(target) if target_exists else None
        material_class = str(row.get("material_class") or "")
        source_ref = str(row.get("source_ref") or "")
        required_anchors = [
            str(anchor)
            for anchor in row.get("required_anchors", [])
            if isinstance(anchor, str) and anchor
        ]
        text = target.read_text(encoding="utf-8") if target_exists else ""
        target_line_count = _line_count_from_text(text) if target_exists else None
        missing_anchors = [
            anchor for anchor in required_anchors if anchor not in text
        ]
        digest_match = target_exists and actual_digest == expected_digest
        anchor_status = PASS if not missing_anchors else "blocked"
        row_body_in_receipt = row.get("body_in_receipt") is True
        import_row = {
            "module_id": module_id,
            "source_ref": source_ref,
            "target_ref": _display(target, public_root=public_root),
            "material_class": material_class,
            "source_sha256": expected_digest,
            "target_sha256": actual_digest,
            "exists": target_exists,
            "digest_match": digest_match,
            "anchor_status": anchor_status,
            "missing_anchor_count": len(missing_anchors),
            "source_to_target_relation": str(
                row.get("source_to_target_relation") or "exact_copy"
            ),
            "source_line_count": row.get("line_count"),
            "target_line_count": target_line_count,
            "body_in_receipt": False,
            "body_material_status": REAL_BODY_MATERIAL_STATUS,
        }
        imports.append(import_row)

        if str(row.get("source_import_class") or "") != "copied_non_secret_macro_body":
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_MODULE_IMPORT_CLASS_UNSUPPORTED",
                    "Copied source module rows must declare copied_non_secret_macro_body.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_BODY_CLASSES:
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_MODULE_CLASS_UNSUPPORTED",
                    "Copied source module rows must use a public-safe macro body class.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if row_body_in_receipt:
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_BODY_RECEIPT_EXPORT_FORBIDDEN",
                    "Copied source module bodies may be bundled as files, not emitted in receipts.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if import_row["source_to_target_relation"] != "exact_copy":
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_MODULE_RELATION_UNSUPPORTED",
                    "Cold-reader body-floor imports must currently be exact copied source bodies.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if not target_exists:
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_MODULE_TARGET_MISSING",
                    "Copied source module target file is missing from the exported bundle.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        elif not digest_match:
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Copied source module digest must match the source_module_manifest row.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if missing_anchors:
            findings.append(
                _finding(
                    "COLD_ROUTE_SOURCE_MODULE_ANCHOR_MISSING",
                    "Copied source module must preserve every required provenance anchor.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )

    status = PASS if not findings else "blocked"
    if not required and not manifest_path.is_file():
        status = "not_required"
    copied_count = sum(
        1
        for row in imports
        if row["exists"] and row["digest_match"] and row["anchor_status"] == PASS
    )
    return {
        "status": status,
        "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
        "body_material_status": REAL_BODY_MATERIAL_STATUS
        if imports
        else "no_source_module_import_required",
        "source_module_results": imports,
        "source_module_count": len(imports),
        "copied_source_module_count": copied_count,
        "source_module_refs": [row["target_ref"] for row in imports],
        "source_refs": sorted({row["source_ref"] for row in imports if row["source_ref"]}),
        "material_classes": sorted(
            {row["material_class"] for row in imports if row["material_class"]}
        ),
        "findings": findings,
    }


def _scan_inputs(
    input_dir: Path,
    *,
    include_negative: bool,
    public_root: Path,
    extra_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_scan_inputs` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = scan_paths(
        [*_input_paths(input_dir, include_negative=include_negative), *(extra_paths or [])],
        forbidden_classes=policy,
        display_root=public_root,
    )
    scan.pop("forbidden_output_fields", None)
    return scan


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_relative_receipt_paths` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [_display(path, public_root=public_root) for path in paths.values()]


def _freshness_input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_freshness_input_paths` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    paths = _input_paths(input_dir, include_negative=include_negative)
    bundle_manifest_path = input_dir / "bundle_manifest.json"
    if bundle_manifest_path.is_file():
        paths.append(bundle_manifest_path)
    manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if manifest_path.is_file():
        manifest = read_json_strict(manifest_path)
        paths.extend([manifest_path, *_source_module_paths(input_dir, manifest)])
    forbidden_policy_path = (
        _public_root_for_path(input_dir) / "core/private_state_forbidden_classes.json"
    )
    if forbidden_policy_path.is_file():
        paths.append(forbidden_policy_path)
    return paths


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_freshness_basis` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    paths = _freshness_input_paths(input_dir, include_negative=include_negative)
    existing = [path for path in paths if path.is_file()]
    latest_mtime = max((path.stat().st_mtime for path in existing), default=0.0)
    return {
        "mode": "input_file_mtime_guard",
        "checked_path_count": len(paths),
        "existing_path_count": len(existing),
        "missing_path_count": len(paths) - len(existing),
        "latest_input_mtime": latest_mtime,
    }


def _fresh_exported_bundle_receipt(
    input_dir: Path,
    out_dir: Path,
    *,
    command: str,
) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Implements `_fresh_exported_bundle_receipt` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(out_dir)
    receipt_path = out_dir / BUNDLE_RESULT_NAME
    if not receipt_path.is_file():
        return None
    try:
        receipt = read_json_strict(receipt_path)
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(receipt, dict):
        return None
    if receipt.get("schema_version") != (
        "exported_cold_reader_route_map_bundle_validation_result_v1"
    ):
        return None
    if receipt.get("organ_id") != ORGAN_ID:
        return None
    if receipt.get("status") != PASS:
        return None
    if receipt.get("input_mode") != "exported_cold_reader_route_map_bundle":
        return None
    if receipt.get("command") not in {command, _stored_receipt_command(command)}:
        return None
    basis = _freshness_basis(input_dir, include_negative=False)
    if basis["missing_path_count"]:
        return None
    if receipt_path.stat().st_mtime < basis["latest_input_mtime"]:
        return None
    cached = dict(receipt)
    cached["cache_status"] = "fresh_exported_bundle_receipt_reused"
    cached["freshness_basis"] = {
        **basis,
        "receipt_ref": _display(receipt_path, public_root=public_root),
    }
    cached["receipt_paths"] = [_display(receipt_path, public_root=public_root)]
    return cached


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_common_receipt` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": schema_version,
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": result["command"],
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "source_refs": SOURCE_REFS,
        "public_runtime_refs": result["public_runtime_refs"],
        "real_substrate_refs": result["real_substrate_refs"],
        "body_material_status": result["body_material_status"],
        "body_import_verification": result["body_import_verification"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_module_count": result["source_module_count"],
        "copied_source_module_count": result["copied_source_module_count"],
        "source_module_refs": result["source_module_refs"],
        "source_module_results": result["source_module_results"],
        "route_source_replay": result["route_source_replay"],
        "error_codes": result["error_codes"],
        "expected_negative_cases": result["expected_negative_cases"],
        "observed_negative_cases": result["observed_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "finding_count": len(result["findings"]),
        "route_count": result["route_count"],
        "command_count": result["command_count"],
        "receipt_ref_count": result["receipt_ref_count"],
        "first_run_sequence": result["first_run_sequence"],
        "front_door_route_ids": result["front_door_route_ids"],
        "front_door_command_count": result["front_door_command_count"],
        "covered_route_ids": result.get("covered_route_ids", []),
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "receipt_paths": receipt_paths,
        "cache_status": result.get("cache_status", "not_applicable"),
        "freshness_basis": result.get("freshness_basis", {}),
        "body_in_receipt": False,
        "real_runtime_receipt": result["real_runtime_receipt"],
        "synthetic_receipt_standin_allowed": False,
    }


def _build_board(
    *,
    result: dict[str, Any],
    secret_scan: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_board` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "cold_reader_route_map_board_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "cold_reader_route_map_first_run_board",
        "route_map": {
            "route_count": result["route_count"],
            "command_count": result["command_count"],
            "receipt_ref_count": result["receipt_ref_count"],
            "first_run_sequence": result["first_run_sequence"],
            "covered_route_ids": result["covered_route_ids"],
            "front_door_route_ids": result["front_door_route_ids"],
            "front_door_command_count": result["front_door_command_count"],
        },
        "cold_reader_goal": "legible_under_10_minutes_without_private_macro_context",
        "public_runtime_refs": result["public_runtime_refs"],
        "real_substrate_refs": result["real_substrate_refs"],
        "body_material_status": result["body_material_status"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_module_count": result["source_module_count"],
        "copied_source_module_count": result["copied_source_module_count"],
        "route_source_replay": {
            "status": result["route_source_replay"]["status"],
            "verification_mode": result["route_source_replay"]["verification_mode"],
            "route_count": result["route_source_replay"]["route_count"],
            "supported_route_count": result["route_source_replay"][
                "supported_route_count"
            ],
            "resolved_docs_ref_count": result["route_source_replay"][
                "resolved_docs_ref_count"
            ],
            "resolved_pass_receipt_ref_count": result["route_source_replay"][
                "resolved_pass_receipt_ref_count"
            ],
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "secret_exclusion_scan": secret_scan,
        "finding_count": len(result["findings"]),
        "findings": result["findings"],
        "body_in_receipt": False,
        "real_runtime_receipt": result["real_runtime_receipt"],
        "synthetic_receipt_standin_allowed": False,
    }


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_result` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    source_manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    source_manifest_payload = (
        read_json_strict(source_manifest_path) if source_manifest_path.is_file() else {}
    )
    source_module_extra_paths = []
    if source_manifest_path.is_file():
        source_module_extra_paths = [
            source_manifest_path,
            *_source_module_paths(input_dir, source_manifest_payload),
        ]
    secret_scan = _scan_inputs(
        input_dir,
        include_negative=include_negative,
        public_root=public_root,
        extra_paths=source_module_extra_paths,
    )
    route_map = payloads.get("route_map", {})
    route_receipts = payloads.get("route_receipts", {})
    route_policy = payloads.get("route_policy", {})
    if not isinstance(route_policy, dict):
        route_policy = {}
    route_rows = _route_rows(route_map)
    receipt_rows = _receipt_rows(route_receipts)
    route_by_id = {_route_id(row): row for row in route_rows if _route_id(row)}
    positive_findings = _positive_findings(
        route_rows=route_rows,
        receipt_rows=receipt_rows,
        policy=route_policy,
    )
    negative_payloads = {
        key: value for key, value in payloads.items() if key in NEGATIVE_INPUT_STEMS
    }
    negative = _negative_findings(negative_payloads)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    observed = negative["observed_negative_cases"]
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    source_modules = _source_module_import_result(
        input_dir,
        public_root=public_root,
        required=input_mode == "exported_cold_reader_route_map_bundle",
    )
    route_source_replay = _route_source_replay_result(
        input_dir,
        public_root=public_root,
        route_rows=route_rows,
        receipt_rows=receipt_rows,
        source_manifest_payload=source_manifest_payload,
    )
    findings = [
        *positive_findings,
        *negative["findings"],
        *source_modules["findings"],
        *route_source_replay["findings"],
    ]
    error_codes = sorted({finding["error_code"] for finding in findings})
    receipt_ref_count = sum(
        len(row.get("receipt_refs", []))
        for row in receipt_rows
        if isinstance(row.get("receipt_refs", []), list)
    )
    first_run_sequence = [
        str(route_id)
        for route_id in route_policy.get("first_run_sequence", [])
        if isinstance(route_id, str)
    ]
    covered_route_ids = sorted(_route_id(row) for row in route_rows if _route_id(row))
    front_door_command_count = sum(
        1
        for route_id, expected_command in FRONT_DOOR_ROUTE_COMMANDS.items()
        if route_by_id.get(route_id, {}).get("command") == expected_command
    )
    source_modules_pass = source_modules["status"] in (PASS, "not_required")
    route_source_replay_pass = route_source_replay["status"] == PASS
    status = (
        PASS
        if not positive_findings
        and not missing
        and not secret_scan["blocking_hit_count"]
        and source_modules_pass
        and route_source_replay_pass
        else "blocked"
    )
    real_substrate_refs = [
        *PUBLIC_RUNTIME_REFS,
        *source_modules["source_refs"],
        *source_modules["source_module_refs"],
    ]
    source_module_results = source_modules["source_module_results"]
    source_body_digests = sorted(
        f"sha256:{row['source_sha256']}"
        for row in source_module_results
        if row.get("source_sha256")
    )
    target_body_digests = sorted(
        f"sha256:{row['target_sha256']}"
        for row in source_module_results
        if row.get("target_sha256")
    )
    return {
        "schema_version": "cold_reader_route_map_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "source_refs": SOURCE_REFS,
        "public_runtime_refs": PUBLIC_RUNTIME_REFS,
        "real_substrate_refs": real_substrate_refs,
        "body_material_status": source_modules["body_material_status"],
        "body_import_verification": {
            "verification_status": PASS if source_modules_pass else "blocked",
            "verification_mode": "exact_source_digest_match_plus_required_anchor_check",
            "source_module_manifest_ref": source_modules[
                "source_module_manifest_ref"
            ],
            "source_to_target_relation": "exact_copy",
            "digest_relation": "source_target_digest_sets_match"
            if source_body_digests == target_body_digests
            else "source_target_digest_sets_drift",
            "source_module_count": source_modules["source_module_count"],
            "copied_source_module_count": source_modules[
                "copied_source_module_count"
            ],
            "source_body_digests": source_body_digests,
            "target_body_digests": target_body_digests,
            "source_refs": source_modules["source_refs"],
            "target_refs": source_modules["source_module_refs"],
            "body_in_receipt": False,
        },
        "source_module_manifest_status": source_modules["status"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_count": source_modules["source_module_count"],
        "copied_source_module_count": source_modules["copied_source_module_count"],
        "source_module_refs": source_modules["source_module_refs"],
        "source_module_results": source_modules["source_module_results"],
        "route_source_replay": route_source_replay,
        "expected_negative_cases": expected,
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "route_count": len(route_rows),
        "command_count": sum(1 for row in route_rows if row.get("command")),
        "receipt_ref_count": receipt_ref_count,
        "first_run_sequence": first_run_sequence,
        "front_door_route_ids": list(FRONT_DOOR_ROUTE_IDS),
        "front_door_command_count": front_door_command_count,
        "covered_route_ids": covered_route_ids,
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
    - Teleology: Implements `_write_receipts` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
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
        schema_version="cold_reader_route_map_result_receipt_v1",
        receipt_paths=relative_paths,
    )
    board["receipt_paths"] = relative_paths
    validation = _common_receipt(
        result,
        schema_version="cold_reader_route_map_validation_receipt_v1",
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
            schema_version="cold_reader_route_map_fixture_acceptance_v1",
            receipt_paths=relative_paths,
        )
        write_json_atomic(acceptance_out, acceptance)
    result["receipt_paths"] = relative_paths
    return result


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.cold_reader_route_map run",
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    target = Path(out_dir)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    result["cache_status"] = "not_applicable_fixture_run"
    result["freshness_basis"] = _freshness_basis(Path(input_dir), include_negative=True)
    return _write_receipts(
        result,
        target,
        acceptance_out=Path(acceptance_out) if acceptance_out else None,
    )


def run_route_map_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.cold_reader_route_map run-route-map-bundle",
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_route_map_bundle` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    target = Path(out_dir)
    public_root = _public_root_for_path(target)
    source = Path(input_dir)
    if reuse_fresh_receipt:
        cached = _fresh_exported_bundle_receipt(source, target, command=command)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_cold_reader_route_map_bundle",
        include_negative=False,
    )
    result["cache_status"] = "rebuilt"
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    path = target / BUNDLE_RESULT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = _display(path, public_root=public_root)
    receipt = _common_receipt(
        result,
        schema_version="exported_cold_reader_route_map_bundle_validation_result_v1",
        receipt_paths=[receipt_path],
    )
    write_json_atomic(path, receipt)
    result["receipt_paths"] = [receipt_path]
    return result


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "command": result["command"],
        "route_map": {
            "route_count": result["route_count"],
            "command_count": result["command_count"],
            "receipt_ref_count": result["receipt_ref_count"],
            "covered_route_count": len(result.get("covered_route_ids", [])),
            "first_run_sequence_head": result["first_run_sequence"][:3],
            "front_door_route_ids": result["front_door_route_ids"],
            "front_door_command_count": result["front_door_command_count"],
        },
        "source_import_floor": {
            "status": result["source_module_manifest_status"],
            "source_module_count": result["source_module_count"],
            "copied_source_module_count": result["copied_source_module_count"],
            "body_material_status": result["body_material_status"],
            "verification_status": result["body_import_verification"][
                "verification_status"
            ],
            "body_in_receipt": result["body_import_verification"]["body_in_receipt"],
        },
        "route_source_replay": {
            "status": result["route_source_replay"]["status"],
            "route_count": result["route_source_replay"]["route_count"],
            "supported_route_count": result["route_source_replay"][
                "supported_route_count"
            ],
            "resolved_docs_ref_count": result["route_source_replay"][
                "resolved_docs_ref_count"
            ],
            "resolved_pass_receipt_ref_count": result["route_source_replay"][
                "resolved_pass_receipt_ref_count"
            ],
        },
        "negative_case_summary": {
            "expected_negative_case_count": len(result["expected_negative_cases"]),
            "observed_negative_case_count": len(result["observed_negative_cases"]),
            "missing_negative_case_count": len(result["missing_negative_cases"]),
            "error_code_count": len(result["error_codes"]),
        },
        "secret_exclusion_summary": {
            "status": result["secret_exclusion_scan"].get("status"),
            "blocking_hit_count": result["secret_exclusion_scan"].get(
                "blocking_hit_count"
            ),
            "body_in_receipt": result["secret_exclusion_scan"].get("body_in_receipt"),
        },
        "authority_ceiling": {
            "route_registry_authority": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
            "provider_calls_authorized": False,
            "whole_system_correctness_claim": False,
        },
        "runtime_receipt": {
            "real_runtime_receipt": result["real_runtime_receipt"],
            "synthetic_receipt_standin_allowed": result[
                "synthetic_receipt_standin_allowed"
            ],
        },
        "cache_status": result.get("cache_status", "not_applicable"),
        "freshness_basis": result.get("freshness_basis", {}),
        "receipt_paths": result.get("receipt_paths", []),
        "output_economy": {
            "full_payload_drilldown": "rerun without --card or inspect the written receipt files",
            "omitted_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "source_bodies_exported": False,
            "provider_payloads_exported": False,
            "private_state_exported": False,
            "raw_stdout_stderr_bodies_exported": False,
        },
    }


def _parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `_parser` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description="Validate public cold-reader route map")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-route-map-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.cold_reader_route_map` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.command == "run":
        command = (
            "python -m microcosm_core.organs.cold_reader_route_map run "
            f"--input {args.input} --out {args.out}{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    else:
        command = (
            "python -m microcosm_core.organs.cold_reader_route_map "
            f"run-route-map-bundle --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run_route_map_bundle(
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
