"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.fixture_registry` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: PATTERN_BINDING_OPTIONAL_INPUTS, PATTERN_BINDING_SUBSTRATE_BUNDLE_REQUIRED_INPUTS, load_pattern_binding_fixture, load_pattern_binding_substrate_bundle, load_first_wave_fixture
- Reads: call arguments, module constants, imported helpers.
- Writes: return values and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: schemas
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .schemas import read_json_strict, read_jsonl_strict


PATTERN_BINDING_OPTIONAL_INPUTS = {
    "authority_chain_handles": "authority_chain_handles.json",
    "duplicate_patterns": "duplicate_pattern_id_conflict.jsonl",
    "generated_projection_authority_upgrade": "generated_projection_authority_upgrade.json",
    "reference_capsules": "reference_capsules.json",
    "source_capsule_with_private_body": "source_capsule_with_private_body.json",
    "valid_binding_overclaim_public_leaf": "valid_binding_overclaim_public_leaf.json",
}

PATTERN_BINDING_SUBSTRATE_BUNDLE_REQUIRED_INPUTS = {
    "bundle_manifest": "bundle_manifest.json",
    "patterns": "pattern_rows.jsonl",
    "source_capsules": "source_capsules.json",
    "forbidden_terms": "private_state_forbidden_terms.json",
    "authority_chain_handles": "authority_chain_handles.json",
    "reference_capsules": "reference_capsules.json",
    "omission_receipts": "omission_receipts.json",
}


def _path_is_file(path: Path) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_path_is_file` for `microcosm_core.fixture_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return path.is_file()
    except OSError:
        return False


def load_pattern_binding_fixture(input_dir: str | Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `load_pattern_binding_fixture` for `microcosm_core.fixture_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    root = Path(input_dir)
    required = {
        "patterns": root / "patterns.jsonl",
        "source_capsules": root / "source_capsules.json",
        "forbidden_terms": root / "private_state_forbidden_terms.json",
    }
    missing = [path.as_posix() for path in required.values() if not _path_is_file(path)]
    if missing:
        raise FileNotFoundError(f"missing pattern-binding fixture input(s): {', '.join(missing)}")

    payload: dict[str, Any] = {
        "patterns": read_jsonl_strict(required["patterns"]),
        "source_capsules": read_json_strict(required["source_capsules"]),
        "forbidden_terms": read_json_strict(required["forbidden_terms"]),
        "input_paths": {key: path.as_posix() for key, path in required.items()},
    }
    for key, filename in PATTERN_BINDING_OPTIONAL_INPUTS.items():
        path = root / filename
        if not _path_is_file(path):
            continue
        payload["input_paths"][key] = path.as_posix()
        payload[key] = read_jsonl_strict(path) if filename.endswith(".jsonl") else read_json_strict(path)
    return payload


def load_pattern_binding_substrate_bundle(input_dir: str | Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `load_pattern_binding_substrate_bundle` for `microcosm_core.fixture_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    root = Path(input_dir)
    required = {
        key: root / filename
        for key, filename in PATTERN_BINDING_SUBSTRATE_BUNDLE_REQUIRED_INPUTS.items()
    }
    missing = [path.as_posix() for path in required.values() if not _path_is_file(path)]
    if missing:
        raise FileNotFoundError(f"missing pattern-binding substrate bundle input(s): {', '.join(missing)}")

    payload: dict[str, Any] = {
        "input_mode": "exported_substrate_bundle",
        "bundle_manifest": read_json_strict(required["bundle_manifest"]),
        "patterns": read_jsonl_strict(required["patterns"]),
        "source_capsules": read_json_strict(required["source_capsules"]),
        "forbidden_terms": read_json_strict(required["forbidden_terms"]),
        "authority_chain_handles": read_json_strict(required["authority_chain_handles"]),
        "reference_capsules": read_json_strict(required["reference_capsules"]),
        "omission_receipts": read_json_strict(required["omission_receipts"]),
        "input_paths": {key: path.as_posix() for key, path in required.items()},
    }
    return payload


def load_first_wave_fixture(organ_id: str, input_dir: str | Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `load_first_wave_fixture` for `microcosm_core.fixture_registry` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if organ_id != "pattern_binding_contract":
        raise ValueError(f"unsupported first-wave organ in this slice: {organ_id}")
    return load_pattern_binding_fixture(input_dir)
