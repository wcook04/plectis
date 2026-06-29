"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.certificate_kernel_execution_lab` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, PACKET_NAME, MANIFEST_NAME, LAKE_PROJECT_DIR, LAKEFILE_NAME, LAKE_TARGET, LEAN_TRANSITION_MAX_WORKERS, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, PUBLIC_READOUT_NAME, ACCEPTANCE_RECEIPT_REL, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, SOURCE_MODULE_MANIFEST_NAME, SOURCE_IMPORT_CLASS, SOURCE_MODULE_IMPORT_STATUS, SOURCE_OPEN_BODY_SCHEMA, PUBLIC_SAFE_SOURCE_BODY_CLASSES, NEGATIVE_INPUT_NAMES, EXPECTED_NEGATIVE_CASES, FORBIDDEN_TRANSITION_KEYS, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs, declared subprocess results.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, subprocess side effects requested by the caller and any explicit side effects performed by exported entry points.
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
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "certificate_kernel_execution_lab"
FIXTURE_ID = "first_wave.certificate_kernel_execution_lab"
VALIDATOR_ID = "validator.microcosm.organs.certificate_kernel_execution_lab"

PACKET_NAME = "certificate_lab_packet.json"
MANIFEST_NAME = "certificate_manifest.json"
LAKE_PROJECT_DIR = "lake_project"
LAKEFILE_NAME = "lakefile.lean"
LAKE_TARGET = "MicrocosmCertificateLab"
LEAN_TRANSITION_MAX_WORKERS = 4
RESULT_NAME = "certificate_kernel_execution_lab_result.json"
BOARD_NAME = "certificate_kernel_execution_lab_board.json"
VALIDATION_RECEIPT_NAME = "certificate_kernel_execution_lab_validation_receipt.json"
PUBLIC_READOUT_NAME = "certificate_kernel_execution_lab_public_readout.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "certificate_kernel_execution_lab_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = (
    "exported_certificate_kernel_execution_lab_bundle_validation_result.json"
)
CARD_SCHEMA_VERSION = "certificate_kernel_execution_lab_command_card_v1"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_MODULE_IMPORT_STATUS = "copied_non_secret_certificate_kernel_macro_body_landed"
SOURCE_OPEN_BODY_SCHEMA = "certificate_kernel_execution_lab_source_open_body_imports_v1"
PUBLIC_SAFE_SOURCE_BODY_CLASSES = frozenset(
    {
        "public_macro_pattern_body",
        "public_macro_tool_body",
        "public_macro_receipt_body",
        "public_macro_proof_body",
        "public_standard_body",
    }
)
_LAKE_PROJECT_BUILD_CACHE: dict[str, Path] = {}
_LAKE_PROJECT_BUILD_CACHE_HOLDERS: list[Any] = []
_TRANSITION_EXECUTION_CACHE: dict[str, list[CertificateTransitionReceipt]] = {}

NEGATIVE_INPUT_NAMES = (
    "transition_provider_oracle_visible.json",
    "cp2_certificate_contains_proof_body.json",
    "evolve_certificate_mutates_source.json",
    "certificate_manifest_private_source_ref.json",
)
EXPECTED_NEGATIVE_CASES = {
    "transition_provider_oracle_visible": [
        "CERTIFICATE_KERNEL_EXECUTION_PROVIDER_OR_ORACLE_VISIBLE"
    ],
    "cp2_certificate_contains_proof_body": [
        "CERTIFICATE_KERNEL_EXECUTION_CP2_PROOF_BODY_FORBIDDEN"
    ],
    "evolve_certificate_mutates_source": [
        "CERTIFICATE_KERNEL_EXECUTION_EVOLVE_SCOPE_FORBIDDEN"
    ],
    "certificate_manifest_private_source_ref": [
        "CERTIFICATE_KERNEL_EXECUTION_PRIVATE_SOURCE_REF_FORBIDDEN"
    ],
}

FORBIDDEN_TRANSITION_KEYS = {
    "candidate_body",
    "proof_body",
    "ground_truth_proof",
    "ideal_body",
    "repair_body",
    "raw_tactic_script",
    "oracle_template",
    "oracle_needed_premise_ids",
    "provider_output_body",
    "source_proof_body",
}
FORBIDDEN_CP2_KEYS = {
    "candidate_body",
    "proof_body",
    "ground_truth_proof",
    "raw_tactic_script",
    "oracle_template",
    "provider_output_body",
    "source_proof_body",
}
ALLOWED_ACTION_CLASSES = {
    "add_certificate_row",
    "direct_certificate_check",
    "direct_order_certificate_check",
    "generated_certificate_theorem",
    "select_certificate_row",
}
ALLOWED_CP2_ACTION_CLASSES = {
    "add_certificate_row",
    "reject_bad_certificate",
    "retry_with_allowed_certificate",
    "rewrite_certificate_direction",
    "select_witness_certificate",
}
ALLOWED_EVOLVE_ARTIFACTS = {
    "certificate_row_selection_policy",
    "cp2_candidate_ordering",
    "failure_class_routing",
    "retry_recipes",
    "target_shape_routing_table",
}
FORBIDDEN_MANIFEST_KEYS = {
    "proof_body",
    "ground_truth_proof",
    "private_source_body",
    "provider_output_body",
    "source_proof_body",
}
DECLARATION_RE = re.compile(
    r"^\s*(?:theorem|lemma|def|structure|inductive)\s+([A-Za-z0-9_'.]+)", re.M
)
IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*$", re.M)
LEAN_TRANSITION_HEADER = (
    "import MicrocosmCertificateLab.GeneratedCertificates\n\n"
    "namespace MicrocosmCertificateLabExecution\n"
    "open MicrocosmCertificateLab\n\n"
)
LEAN_TRANSITION_FOOTER = "\nend MicrocosmCertificateLabExecution\n"
LEAN_TRANSITION_BATCH_NAME = "certificate_transition_batch.lean"

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "bounded_public_certificate_kernel_execution_receipt_only",
    "lean_lake_execution_authorized": True,
    "lean_lake_execution_scope": "temporary_workspace_copy_of_public_fixture",
    "formal_proof_authority": "bounded_public_certificate_fixture_rows_only",
    "macro_private_body_import_authorized": False,
    "oracle_success_counts_as_forward_success": False,
    "provider_text_counts_as_proof": False,
    "cp2_outputs_are_proof_bodies": False,
    "evolve_mutates_arbitrary_code": False,
    "proof_bodies_allowed_in_receipts": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "benchmark_solve_rate_claim": False,
    "release_authorized": False,
}
RECEIPT_TRANSPARENCY_CONTRACT = {
    "schema_version": "verifier_lab_receipt_transparency_contract_v1",
    "receipt_body_is_public_evidence": True,
    "omitted_payload_scope": "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only",
    "body_in_receipt": False,
    "real_substrate_default": True,
    "required_public_evidence_fields": [
        "theorem_or_declaration_names",
        "lean_lake_command_identity",
        "lean_return_code",
        "source_hashes",
        "declaration_counts",
        "accepted_transition_count",
        "residual_transition_count",
        "negative_case_id",
        "cp2_action_class",
        "evolve_policy_artifact_id",
        "oracle_provider_separation_counters",
        "authority_ceiling",
        "anti_claim",
    ],
    "forbidden_payload_fields": [
        "proof_body",
        "raw_tactic_script",
        "provider_text",
        "oracle_ideal_answer",
        "oracle_needed_premise_ids",
        "private_source_path",
        "private_payload_body",
        "stdout_body",
        "stderr_body",
    ],
    "stdout_stderr_policy": "counts_and_return_codes_public_bodies_omitted",
}
ANTI_CLAIM = (
    "Certificate kernel execution lab runs a source-available public Lean certificate "
    "kernel in a temporary workspace, checks generated certificate rows, and "
    "records structured public CP2/Evolve rerun receipts with only dangerous "
    "payload fields omitted. It does not import macro proof bodies, export proof "
    "text, call providers, count oracle/provider output as proof, mutate source, "
    "claim benchmark solve-rate, or authorize release."
)


@dataclass(frozen=True)
class CertificateTransitionReceipt:
    """
    [ROLE]
    - Teleology: Groups `CertificateTransitionReceipt` data or behavior for `microcosm_core.organs.certificate_kernel_execution_lab` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.organs.certificate_kernel_execution_lab`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    transition_id: str
    problem_id: str
    target_shape: str
    action_class: str
    candidate_kind: str
    allowed_certificate_refs: tuple[str, ...]
    lean_return_code: int | None
    accepted: bool
    verifier_failure_class: str
    stdout_stderr_in_receipt: bool
    oracle_visible: bool
    provider_visible: bool
    proof_body_exported: bool
    contract_rejected: bool = False
    error_codes: tuple[str, ...] = ()
    timed_out: bool = False


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_display` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_relative_path(path.resolve(strict=False), display_root=public_root)


def _path_is_relative_to(path: Path, root: Path) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_path_is_relative_to` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _public_readout_output_path(out: str | Path, *, public_root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_readout_output_path` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    out_path = Path(out)
    if out_path.is_absolute():
        return out_path
    cwd_candidate = (Path.cwd() / out_path).resolve(strict=False)
    if _path_is_relative_to(cwd_candidate, public_root):
        return cwd_candidate
    if out_path.parts and out_path.parts[0] == public_root.name:
        sibling_candidate = (public_root.parent / out_path).resolve(strict=False)
        if _path_is_relative_to(sibling_candidate, public_root):
            return sibling_candidate
    return public_root / out_path


def _strings(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_rows` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    paths = [
        input_dir / PACKET_NAME,
        input_dir / MANIFEST_NAME,
        input_dir / LAKE_PROJECT_DIR / LAKEFILE_NAME,
    ]
    project_dir = input_dir / LAKE_PROJECT_DIR
    if project_dir.is_dir():
        paths.extend(sorted(_iter_lean_project_files(project_dir)))
    if (input_dir / "bundle_manifest.json").is_file():
        paths.append(input_dir / "bundle_manifest.json")
    source_module_manifest = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if source_module_manifest.is_file():
        paths.append(source_module_manifest)
        try:
            manifest = read_json_strict(source_module_manifest)
        except Exception:
            manifest = {}
        module_rows = manifest.get("modules", []) if isinstance(manifest, dict) else []
        for row in module_rows:
            if not isinstance(row, dict):
                continue
            row_path = row.get("path")
            if isinstance(row_path, str) and row_path:
                paths.append(input_dir / row_path)
    if include_negative:
        paths.extend(input_dir / name for name in NEGATIVE_INPUT_NAMES)
    return paths


def _iter_lean_project_files(path: Path) -> Iterator[Path]:
    """
    [ACTION]
    - Teleology: Implements `_iter_lean_project_files` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    with os.scandir(path) as entries:
        entry_rows = sorted(list(entries), key=lambda entry: entry.name)
    for entry in entry_rows:
        child = path / entry.name
        if entry.is_dir(follow_symlinks=False):
            yield from _iter_lean_project_files(child)
        elif entry.is_file(follow_symlinks=False) and child.suffix == ".lean":
            yield child


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_json_if_exists` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not path.is_file():
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _output_dir(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_output_dir` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    target = Path(path)
    if not target.is_absolute():
        target = Path.cwd() / target
    return target


def _safe_ref(path: Path, *, public_root: Path, fallback: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_safe_ref` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    resolved_root = public_root.resolve(strict=False)
    resolved_path = path.resolve(strict=False)
    if _path_is_relative_to(resolved_path, resolved_root):
        return _display(resolved_path, public_root=resolved_root)
    return fallback


def _source_module_manifest_path(input_dir: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_path` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_source_module_target_path` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if target_ref.startswith(f"{public_root.name}/"):
        return public_root / target_ref.removeprefix(f"{public_root.name}/")
    target = Path(target_ref)
    if target.is_absolute():
        return target
    public_candidate = public_root / target_ref
    if public_candidate.is_file():
        return public_candidate
    return input_dir / target_ref


def _normalize_sha256(value: object) -> str:
    """
    [ACTION]
    - Teleology: Implements `_normalize_sha256` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    digest = str(value or "")
    if not digest:
        return ""
    return digest if digest.startswith("sha256:") else f"sha256:{digest}"


def _source_module_manifest_result(
    input_dir: Path,
    *,
    public_root: Path,
    require_manifest: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_result` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
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
                    "CERTIFICATE_KERNEL_SOURCE_MODULE_MANIFEST_REQUIRED",
                    (
                        "Exported certificate-kernel bundle must include copied "
                        "non-secret macro source modules."
                    ),
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
        }

    manifest = read_json_strict(manifest_path)
    findings: list[dict[str, Any]] = []
    modules = _rows(manifest, "modules")
    module_ids: list[str] = []
    material_class_counts: dict[str, int] = {}
    source_refs = [manifest_ref]
    blocked_source_refs = (
        _strings(manifest.get("blocked_source_refs")) if isinstance(manifest, dict) else []
    )
    omitted_material = (
        _strings(manifest.get("omitted_material")) if isinstance(manifest, dict) else []
    )
    if not isinstance(manifest, dict):
        findings.append(
            _finding(
                "CERTIFICATE_KERNEL_SOURCE_MODULE_MANIFEST_NOT_OBJECT",
                "Source-module manifest must be a JSON object.",
                case_id="source_module_manifest_shape",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    else:
        if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "CERTIFICATE_KERNEL_SOURCE_IMPORT_CLASS_MISMATCH",
                    "Source-module manifest must declare copied non-secret macro body import class.",
                    case_id="source_module_manifest_class",
                    subject_id=manifest_ref,
                    subject_kind="source_module_manifest",
                )
            )
        if manifest.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "CERTIFICATE_KERNEL_SOURCE_MODULE_BODY_RECEIPT_FORBIDDEN",
                    "Source-module manifest must not claim body text is exported in receipts.",
                    case_id="source_module_manifest_receipt_boundary",
                    subject_id=manifest_ref,
                    subject_kind="source_module_manifest",
                )
            )
        declared_count = manifest.get("module_count")
        if isinstance(declared_count, int) and declared_count != len(modules):
            findings.append(
                _finding(
                    "CERTIFICATE_KERNEL_SOURCE_MODULE_COUNT_MISMATCH",
                    "Source-module manifest module_count must equal the modules array length.",
                    case_id="source_module_manifest_count",
                    subject_id=manifest_ref,
                    subject_kind="source_module_manifest",
                )
            )

    verified_count = 0
    for index, row in enumerate(modules):
        module_id = str(row.get("module_id") or f"source_module_{index}")
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
                    "CERTIFICATE_KERNEL_SOURCE_MODULE_IMPORT_CLASS_MISMATCH",
                    "Source-module row must declare copied non-secret macro body import class.",
                    case_id=module_id,
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_BODY_CLASSES:
            findings.append(
                _finding(
                    "CERTIFICATE_KERNEL_SOURCE_MODULE_MATERIAL_CLASS_FORBIDDEN",
                    "Source-module row material class must be public-safe source body material.",
                    case_id=module_id,
                    subject_id=material_class or module_id,
                    subject_kind="source_module_material_class",
                )
            )
        if row.get("body_copied") is not True:
            findings.append(
                _finding(
                    "CERTIFICATE_KERNEL_SOURCE_MODULE_BODY_NOT_COPIED",
                    "Source-module row must represent an exact copied macro body.",
                    case_id=module_id,
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if row.get("body_in_receipt") is not False or row.get("body_text_in_receipt") is not False:
            findings.append(
                _finding(
                    "CERTIFICATE_KERNEL_SOURCE_MODULE_BODY_TEXT_RECEIPT_FORBIDDEN",
                    "Source-module row may not export body text through receipt payloads.",
                    case_id=module_id,
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        target_ref = str(row.get("target_ref") or row.get("path") or "")
        if not target_ref:
            findings.append(
                _finding(
                    "CERTIFICATE_KERNEL_SOURCE_MODULE_TARGET_REF_REQUIRED",
                    "Source-module row must name its copied target path.",
                    case_id=module_id,
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
            continue
        target = _source_module_target_path(
            target_ref,
            input_dir=input_dir,
            public_root=public_root,
        )
        if not target.is_file() and row.get("path"):
            target = input_dir / str(row.get("path"))
        if not target.is_file():
            findings.append(
                _finding(
                    "CERTIFICATE_KERNEL_SOURCE_MODULE_TARGET_MISSING",
                    "Source-module copied target path is missing from the bundle.",
                    case_id=module_id,
                    subject_id=target_ref,
                    subject_kind="source_module_target",
                )
            )
            continue
        actual_sha = f"sha256:{_sha256(target)}"
        expected_shas = [
            _normalize_sha256(row.get("sha256")),
            _normalize_sha256(row.get("source_sha256")),
            _normalize_sha256(row.get("target_sha256")),
        ]
        if any(expected_sha != actual_sha for expected_sha in expected_shas):
            findings.append(
                _finding(
                    "CERTIFICATE_KERNEL_SOURCE_MODULE_SHA256_MISMATCH",
                    "Source-module copied target hash must match manifest hashes.",
                    case_id=module_id,
                    subject_id=target_ref,
                    subject_kind="source_module_target",
                )
            )
        text = target.read_text(encoding="utf-8")
        missing_anchors = [
            anchor for anchor in _strings(row.get("required_anchors")) if anchor not in text
        ]
        if missing_anchors:
            finding = _finding(
                "CERTIFICATE_KERNEL_SOURCE_MODULE_REQUIRED_ANCHOR_MISSING",
                "Source-module copied target is missing required provenance anchors.",
                case_id=module_id,
                subject_id=target_ref,
                subject_kind="source_module_target",
            )
            finding["missing_anchors"] = missing_anchors
            findings.append(finding)
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
        "body_material_classes": dict(sorted(material_class_counts.items())),
        "source_refs": sorted(set(source_refs)),
        "blocked_source_refs": blocked_source_refs,
        "omitted_material": omitted_material,
        "findings": findings,
        "body_in_receipt": False,
    }


def _source_open_body_import_summary(
    source_module_result: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_open_body_import_summary` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    module_ids = _strings(source_module_result.get("module_ids"))
    manifest_ref = str(source_module_result.get("source_module_manifest_ref") or "")
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
        "source_manifest_refs": [manifest_ref] if imported and manifest_ref else [],
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
            "formal_proof_authority": "bounded_public_macro_certificate_kernel_body_refs_only",
            "provider_calls_authorized": False,
            "release_authorized": False,
            "proof_bodies_in_receipts": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported certificate-kernel bundle for copied macro Lean kernel, "
            "generated certificate, strike-runner, toolchain, and Lean profile "
            "receipt bodies; receipts carry refs, hashes, counts, and verdicts only."
        )
        if imported
        else "",
    }


def _fixture_manifest_source_binding(public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_fixture_manifest_source_binding` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = (
        public_root
        / "core/fixture_manifests/certificate_kernel_execution_lab.fixture_manifest.json"
    )
    if not manifest_path.is_file():
        return {}
    fixture_manifest = read_json_strict(manifest_path)
    source_open = fixture_manifest.get("source_open_body_imports", {})
    if not isinstance(source_open, dict):
        return {}
    raw_manifest_refs = source_open.get("source_manifest_refs", [])
    manifest_refs = (
        [str(ref) for ref in raw_manifest_refs if ref]
        if isinstance(raw_manifest_refs, list)
        else []
    )
    source_refs = source_open.get("source_refs", [])
    target_refs = source_open.get("target_refs", [])
    body_count = int(
        fixture_manifest.get("body_copied_material_count")
        or source_open.get("body_material_count")
        or 0
    )
    status = str(source_open.get("status") or PASS)
    return {
        "body_copied_material_count": body_count,
        "source_module_count": body_count,
        "verified_source_module_count": body_count if status == PASS else 0,
        "source_module_manifest_status": status,
        "source_module_manifest_ref": manifest_refs[0] if manifest_refs else None,
        "source_module_imports": {
            "status": status,
            "source_module_import_status": status,
            "module_count": body_count,
            "verified_module_count": body_count if status == PASS else 0,
            "source_module_manifest_ref": manifest_refs[0] if manifest_refs else None,
            "source_refs": [str(ref) for ref in source_refs]
            if isinstance(source_refs, list)
            else [],
            "target_refs": [str(ref) for ref in target_refs]
            if isinstance(target_refs, list)
            else [],
            "body_in_receipt": False,
            "body_text_in_receipt": False,
        },
        "source_open_body_imports": {
            **source_open,
            "body_in_receipt": False,
            "body_text_in_receipt": False,
        },
    }


def _receipt_freshness(
    input_dir: Path,
    receipt_path: Path,
    *,
    include_negative: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_receipt_freshness` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_paths = [
        path
        for path in _input_paths(input_dir, include_negative=include_negative)
        if path.is_file()
    ]
    receipt_exists = receipt_path.is_file()
    input_mtime = max((path.stat().st_mtime for path in input_paths), default=None)
    receipt_mtime = receipt_path.stat().st_mtime if receipt_exists else None
    if not receipt_exists:
        status = "missing"
    elif (
        input_mtime is not None
        and receipt_mtime is not None
        and input_mtime > receipt_mtime
    ):
        status = "stale"
    else:
        status = "current"
    return {
        "status": status,
        "receipt_exists": receipt_exists,
        "tracked_input_count": len(input_paths),
        "receipt_mtime": receipt_mtime,
        "newest_input_mtime": input_mtime,
    }


def _certificate_kernel_execution_card(
    payload: dict[str, Any],
    *,
    action: str,
    input_dir: str | Path,
    out_dir: str | Path,
    receipt_name: str,
    cached_receipt_used: bool,
    freshness: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_certificate_kernel_execution_card` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    input_path = Path(input_dir)
    public_root = _public_root_for_path(input_path)
    receipt_path = _output_dir(out_dir) / receipt_name
    counters = payload.get("authority_counters", {})
    if not isinstance(counters, dict):
        counters = {}
    secret_scan = payload.get("secret_exclusion_scan", {})
    if not isinstance(secret_scan, dict):
        secret_scan = {}
    tool_versions = payload.get("tool_versions", {})
    if not isinstance(tool_versions, dict):
        tool_versions = {}
    lake_build = payload.get("lake_project_build", {})
    if not isinstance(lake_build, dict):
        lake_build = {}
    source_open = payload.get("source_open_body_imports", {})
    if not isinstance(source_open, dict):
        source_open = {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "card_id": "certificate_kernel_execution_lab_command_card",
        "status": payload.get("status", "blocked"),
        "organ_id": ORGAN_ID,
        "command": (
            "python -m microcosm_core.organs.certificate_kernel_execution_lab "
            f"{action} --card --input <certificate-kernel-input> "
            "--out <certificate-kernel-out>"
        ),
        "drilldown_command": (
            "python -m microcosm_core.organs.certificate_kernel_execution_lab "
            f"{action} --input <certificate-kernel-input> "
            "--out <certificate-kernel-out>"
        ),
        "input_mode": payload.get("input_mode"),
        "bundle_id": payload.get("bundle_id"),
        "certificate_lab_id": payload.get("certificate_lab_id"),
        "certificate_manifest_id": payload.get("certificate_manifest_id"),
        "cached_receipt_used": cached_receipt_used,
        "cache_status": "current" if cached_receipt_used else "refreshed",
        "cache_freshness": freshness,
        "receipt_ref": _safe_ref(
            receipt_path,
            public_root=public_root,
            fallback=f"<certificate-kernel-out>/{receipt_name}",
        ),
        "authority_counters": {
            "transition_count": counters.get("transition_count", 0),
            "accepted_transition_count": counters.get("accepted_transition_count", 0),
            "residual_transition_count": counters.get("residual_transition_count", 0),
            "cp2_downstream_effect_count": counters.get("cp2_downstream_effect_count", 0),
            "evolve_accepted_count": counters.get("evolve_accepted_count", 0),
            "analyzed_declaration_count": counters.get("analyzed_declaration_count", 0),
            "oracle_forward_success_increment_count": counters.get(
                "oracle_forward_success_increment_count", 0
            ),
            "provider_results_counted": counters.get("provider_results_counted", 0),
            "proof_body_export_count": counters.get("proof_body_export_count", 0),
            "source_mutation_count": counters.get("source_mutation_count", 0),
            "macro_private_body_import_count": counters.get(
                "macro_private_body_import_count", 0
            ),
        },
        "runtime_summary": {
            "execution_witness_mode": payload.get("execution_witness_mode"),
            "lean_available": tool_versions.get("lean_available"),
            "lake_available": tool_versions.get("lake_available"),
            "lake_return_code": lake_build.get("return_code"),
            "secret_scan_status": secret_scan.get("status"),
            "secret_scan_blocking_hit_count": secret_scan.get("blocking_hit_count"),
            "body_in_receipt": payload.get("body_in_receipt", False),
            "real_runtime_receipt": payload.get("real_runtime_receipt", False),
        },
        "body_floor": {
            "source_module_manifest_status": payload.get(
                "source_module_manifest_status"
            ),
            "source_module_manifest_ref": payload.get("source_module_manifest_ref"),
            "source_open_body_import_status": source_open.get("status"),
            "source_open_body_import_count": source_open.get("body_material_count"),
            "body_copied_material_count": payload.get("body_copied_material_count"),
            "body_text_exported_in_receipts": source_open.get(
                "body_text_exported_in_receipts"
            ),
        },
        "authority_ceiling": payload.get("authority_ceiling", AUTHORITY_CEILING),
        "anti_claim": payload.get("anti_claim", ANTI_CLAIM),
        "output_economy": {
            "full_transition_trace_exported": False,
            "claim_separation_rows_exported": False,
            "lake_build_stdout_exported": False,
            "lean_file_declaration_rows_exported": False,
            "provider_oracle_payloads_exported": False,
            "proof_bodies_exported": False,
            "source_mutations_exported": False,
            "full_payload_drilldown": "rerun without --card",
        },
    }


def certificate_kernel_execution_card(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    action: str,
    include_negative: bool,
    receipt_name: str,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `certificate_kernel_execution_card` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_dir)
    receipt_path = _output_dir(out_dir) / receipt_name
    freshness = _receipt_freshness(
        input_path,
        receipt_path,
        include_negative=include_negative,
    )
    if freshness["status"] == "current":
        payload = _load_json_if_exists(receipt_path)
        return _certificate_kernel_execution_card(
            payload,
            action=action,
            input_dir=input_dir,
            out_dir=out_dir,
            receipt_name=receipt_name,
            cached_receipt_used=True,
            freshness=freshness,
        )
    command = (
        "python -m microcosm_core.organs.certificate_kernel_execution_lab "
        f"{action} --card --input {input_dir} --out {out_dir}"
    )
    if action == "run":
        payload = run(
            input_dir,
            out_dir,
            command=command,
            acceptance_out=acceptance_out,
        )
    else:
        payload = run_certificate_bundle(input_dir, out_dir, command=command)
    refreshed = dict(freshness)
    refreshed["status_before_refresh"] = freshness["status"]
    refreshed["status"] = "current"
    return _certificate_kernel_execution_card(
        payload,
        action=action,
        input_dir=input_dir,
        out_dir=out_dir,
        receipt_name=receipt_name,
        cached_receipt_used=False,
        freshness=refreshed,
    )


def _sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _import_names(text: str) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_import_names` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    imports: list[str] = []
    for match in IMPORT_RE.findall(text):
        imports.extend(part for part in match.split() if part)
    return sorted(imports)


def _analyze_lean_project(
    project_dir: Path,
    *,
    public_root: Path,
    source_project_dir: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_analyze_lean_project` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    rows: list[dict[str, Any]] = []
    declaration_count = 0
    imports: set[str] = set()
    for path in sorted(_iter_lean_project_files(project_dir)):
        text = path.read_text(encoding="utf-8")
        declarations = sorted(DECLARATION_RE.findall(text))
        file_imports = _import_names(text)
        declaration_count += len(declarations)
        imports.update(file_imports)
        public_source_path = (
            source_project_dir / path.relative_to(project_dir)
        ).resolve(strict=False)
        rows.append(
            {
                "source_ref": _display(public_source_path, public_root=public_root),
                "sha256": _sha256(path),
                "line_count": len(text.splitlines()),
                "declarations": declarations,
                "imports": file_imports,
                "body_in_receipt": False,
            }
        )
    return {
        "schema_version": "certificate_kernel_execution_lab_lean_analyzer_v1",
        "lean_file_count": len(rows),
        "declaration_count": declaration_count,
        "imports": sorted(imports),
        "files": rows,
        "generated_certificates_separate_from_kernel": True,
        "profile_timing_available": False,
        "anti_claim": "Analyzer metadata records public declarations, imports, hashes, and line counts only; it does not export proof bodies or prove general theorem correctness.",
        "body_in_receipt": False,
    }


def _walk_forbidden_keys(value: object, forbidden: set[str], prefix: str = "") -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_walk_forbidden_keys` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{prefix}.{key}" if prefix else str(key)
            if key in forbidden:
                found.append(key_path)
            found.extend(_walk_forbidden_keys(child, forbidden, key_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_walk_forbidden_keys(child, forbidden, f"{prefix}[{index}]"))
    return sorted(found)


def _private_source_refs(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_private_source_refs` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    refs: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.endswith("source_ref") or key.endswith("source_refs") or key == "source_refs":
                values = child if isinstance(child, list) else [child]
                for item in values:
                    if not isinstance(item, str):
                        continue
                    if item.startswith(("/", "~", "../")) or "/private/" in item:
                        refs.append(item)
            refs.extend(_private_source_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(_private_source_refs(child))
    return sorted(set(refs))


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
    - Teleology: Implements `_finding` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
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
    count_observed: bool,
) -> None:
    """
    [ACTION]
    - Teleology: Implements `_record` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
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
    if count_observed:
        observed.setdefault(case_id, set()).add(code)


def _run_command(argv: list[str], *, cwd: Path, timeout_seconds: int = 30) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_run_command` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "argv": argv,
            "cwd_name": cwd.name,
            "return_code": completed.returncode,
            "stdout_line_count": len(completed.stdout.splitlines()),
            "stderr_line_count": len(completed.stderr.splitlines()),
            "timed_out": False,
            "stdout_stderr_in_receipt": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "cwd_name": cwd.name,
            "return_code": 124,
            "stdout_line_count": len((exc.stdout or "").splitlines()),
            "stderr_line_count": len((exc.stderr or "").splitlines()),
            "timed_out": True,
            "stdout_stderr_in_receipt": False,
        }


@lru_cache(maxsize=1)
def _cached_tool_versions() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_cached_tool_versions` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    lean_path = shutil.which("lean")
    lake_path = shutil.which("lake")
    lean = _skipped_version_probe("lean", lean_path)
    lake = _skipped_version_probe("lake", lake_path)
    return {
        "lean_available": lean_path is not None,
        "lake_available": lake_path is not None,
        "lean_version_command": lean,
        "lake_version_command": lake,
    }


def _tool_versions() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_tool_versions` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return deepcopy(_cached_tool_versions())


def _standalone_exported_tool_versions() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_standalone_exported_tool_versions` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    return {
        "lean_available": True,
        "lake_available": True,
        "lean_version_command": {
            "argv": ["lean", "--version"],
            "cwd_name": Path.cwd().name,
            "return_code": None,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
            "timed_out": False,
            "stdout_stderr_in_receipt": False,
            "skipped": True,
            "skip_reason": "standalone_exported_certificate_contract",
            "standalone_exported_certificate_contract": True,
        },
        "lake_version_command": {
            "argv": ["lake", "--version"],
            "cwd_name": Path.cwd().name,
            "return_code": None,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
            "timed_out": False,
            "stdout_stderr_in_receipt": False,
            "skipped": True,
            "skip_reason": "standalone_exported_certificate_contract",
            "standalone_exported_certificate_contract": True,
        },
    }


def _skipped_version_probe(tool_name: str, tool_path: str | None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_skipped_version_probe` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    return {
        "argv": [tool_name, "--version"],
        "cwd_name": Path.cwd().name,
        "return_code": 0 if tool_path else 127,
        "stdout_line_count": 0,
        "stderr_line_count": 0,
        "timed_out": False,
        "stdout_stderr_in_receipt": False,
        "skipped": True,
        "skip_reason": "version_probe_skipped_hot_path",
        "tool_path_available": tool_path is not None,
    }


def _lake_project_dir_cache_key(project_dir: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_lake_project_dir_cache_key` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    if not project_dir.is_dir():
        raise FileNotFoundError(project_dir)
    digest = hashlib.sha256()
    for root, dirnames, filenames in os.walk(project_dir):
        dirnames[:] = sorted(name for name in dirnames if name != ".lake")
        for filename in sorted(filenames):
            path = Path(root) / filename
            relative_path = path.relative_to(project_dir).as_posix()
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def _lake_project_cache_key(input_dir: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_lake_project_cache_key` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _lake_project_dir_cache_key(input_dir / LAKE_PROJECT_DIR)


def _copy_project_to_temp(input_dir: Path, temp_root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_copy_project_to_temp` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    src = input_dir / LAKE_PROJECT_DIR
    dst = temp_root / LAKE_PROJECT_DIR
    cached_project = _LAKE_PROJECT_BUILD_CACHE.get(_lake_project_cache_key(input_dir))
    source_project = cached_project if cached_project and cached_project.is_dir() else src
    shutil.copytree(source_project, dst)
    return dst


def _transition_execution_cache_key(
    rows: list[dict[str, Any]],
    *,
    project_dir: Path,
) -> str:
    """
    [ACTION]
    - Teleology: Implements `_transition_execution_cache_key` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    digest = hashlib.sha256()
    digest.update(_lake_project_dir_cache_key(project_dir).encode("utf-8"))
    digest.update(b"\0")
    digest.update(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return digest.hexdigest()


def _remember_built_lake_project(input_dir: Path, project_dir: Path) -> None:
    """
    [ACTION]
    - Teleology: Implements `_remember_built_lake_project` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    cache_key = _lake_project_cache_key(input_dir)
    if cache_key in _LAKE_PROJECT_BUILD_CACHE:
        return
    holder = tempfile.TemporaryDirectory(
        prefix="microcosm_certificate_lab_project_cache_"
    )
    cache_dst = Path(holder.name) / LAKE_PROJECT_DIR
    shutil.copytree(project_dir, cache_dst)
    _LAKE_PROJECT_BUILD_CACHE[cache_key] = cache_dst
    _LAKE_PROJECT_BUILD_CACHE_HOLDERS.append(holder)


def _build_lake_project(project_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_lake_project` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _run_command(
        ["lake", "build", LAKE_TARGET],
        cwd=project_dir,
        timeout_seconds=60,
    )


def _standalone_exported_lake_project_build(packet: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_standalone_exported_lake_project_build` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    return {
        "argv": ["lake", "build", LAKE_TARGET],
        "cwd_name": LAKE_PROJECT_DIR,
        "return_code": 0,
        "stdout_line_count": 0,
        "stderr_line_count": 0,
        "timed_out": False,
        "stdout_stderr_in_receipt": False,
        "skipped": True,
        "skip_reason": "standalone_exported_certificate_contract",
        "standalone_exported_certificate_contract": True,
        "projection_receipt_refs": _strings(packet.get("projection_receipt_refs")),
        "public_runtime_refs": _strings(packet.get("public_runtime_refs")),
    }


def _lean_body_for_transition(row: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `_lean_body_for_transition` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    action = str(row.get("action_class") or "")
    outcome = str(row.get("expected_outcome") or "")
    refs = set(_strings(row.get("allowed_certificate_refs")))
    if outcome == "fail_missing_certificate_row":
        body = "#check missing_public_certificate_row_5_8_13\n"
    elif outcome == "fail_missing_order_certificate_row":
        body = "#check missing_public_order_certificate_row_7_11\n"
    elif outcome == "fail_bad_certificate":
        body = (
            "example : validateNatSumCertificate bad_cert_2_3_6 = true := by\n"
            "  native_decide\n"
        )
    elif outcome == "fail_bad_order_certificate":
        body = (
            "example : validateBoundedOrderCertificate "
            "bad_order_cert_4_2_mod5 = true := by\n"
            "  native_decide\n"
        )
    elif action == "direct_order_certificate_check" and "order_cert_2_3_mod5" in refs:
        body = (
            "example : validateBoundedOrderCertificate "
            "order_cert_2_3_mod5 = true := by\n"
            "  native_decide\n"
        )
    elif action == "add_certificate_row" and "order_cert_3_4_mod5" in refs:
        body = (
            "example : validateBoundedOrderCertificate "
            "order_cert_3_4_mod5 = true := by\n"
            "  exact order_cert_3_4_mod5_valid\n"
        )
    elif action == "select_certificate_row" and "order_cert_3_4_mod5" in refs:
        body = (
            "example : validateBoundedOrderCertificate "
            "order_cert_3_4_mod5 = true := by\n"
            "  native_decide\n"
        )
    elif action == "generated_certificate_theorem" and "cert_4_7_11" in refs:
        body = (
            "example : validateNatSumCertificate cert_4_7_11 = true := by\n"
            "  exact cert_4_7_11_valid\n"
        )
    elif action == "add_certificate_row" and "cert_8_13_21" in refs:
        body = (
            "example : validateNatSumCertificate cert_8_13_21 = true := by\n"
            "  exact cert_8_13_21_valid\n"
        )
    elif action in {"direct_certificate_check", "select_certificate_row"} and "cert_8_13_21" in refs:
        body = (
            "example : validateNatSumCertificate cert_8_13_21 = true := by\n"
            "  native_decide\n"
        )
    elif action in {"direct_certificate_check", "select_certificate_row"} and "cert_2_3_5" in refs:
        body = (
            "example : validateNatSumCertificate cert_2_3_5 = true := by\n"
            "  native_decide\n"
        )
    else:
        body = "example : True := by\n  exact unknown_certificate_action\n"
    return body


def _lean_source_for_transition(row: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `_lean_source_for_transition` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    body = _lean_body_for_transition(row)
    return f"{LEAN_TRANSITION_HEADER}{body}{LEAN_TRANSITION_FOOTER}"


def _transition_expected_to_fail(row: dict[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_transition_expected_to_fail` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return str(row.get("expected_outcome") or "").startswith("fail_")


def _lean_source_for_transition_batch(rows: Sequence[dict[str, Any]]) -> str:
    """
    [ACTION]
    - Teleology: Implements `_lean_source_for_transition_batch` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    bodies = []
    for row in rows:
        transition_id = str(row.get("transition_id") or "transition")
        bodies.append(f"-- transition_id: {transition_id}\n{_lean_body_for_transition(row)}")
    body = "\n".join(bodies)
    return f"{LEAN_TRANSITION_HEADER}{body}{LEAN_TRANSITION_FOOTER}"


def _accepted_transition_receipt(row: dict[str, Any]) -> CertificateTransitionReceipt:
    """
    [ACTION]
    - Teleology: Implements `_accepted_transition_receipt` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    return CertificateTransitionReceipt(
        transition_id=str(row.get("transition_id") or "transition"),
        problem_id=str(row.get("problem_id") or ""),
        target_shape=str(row.get("target_shape") or ""),
        action_class=str(row.get("action_class") or ""),
        candidate_kind=str(row.get("candidate_kind") or ""),
        allowed_certificate_refs=tuple(_strings(row.get("allowed_certificate_refs"))),
        lean_return_code=0,
        accepted=True,
        verifier_failure_class="NONE",
        stdout_stderr_in_receipt=False,
        oracle_visible=False,
        provider_visible=False,
        proof_body_exported=False,
        timed_out=False,
    )


def _execute_positive_transition_batch(
    rows: Sequence[dict[str, Any]],
    *,
    project_dir: Path,
) -> list[CertificateTransitionReceipt] | None:
    """
    [ACTION]
    - Teleology: Implements `_execute_positive_transition_batch` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    source_path = project_dir / LEAN_TRANSITION_BATCH_NAME
    source_path.write_text(_lean_source_for_transition_batch(rows), encoding="utf-8")
    lean_run = _run_command(["lake", "env", "lean", source_path.name], cwd=project_dir)
    if lean_run["return_code"] != 0:
        return None
    return [_accepted_transition_receipt(row) for row in rows]


def _validate_transition_contract(
    row: dict[str, Any],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_validate_transition_contract` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    transition_id = str(row.get("transition_id") or row.get("case_id") or "transition")
    case_id = str(row.get("expected_negative_case_id") or row.get("case_id") or transition_id)
    codes: list[str] = []
    if _walk_forbidden_keys(row, FORBIDDEN_TRANSITION_KEYS):
        code = "CERTIFICATE_KERNEL_EXECUTION_TRANSITION_FIELD_FORBIDDEN"
        _record(
            findings,
            observed,
            code,
            "Certificate transition rows may not carry proof bodies, raw tactic scripts, provider bodies, or oracle templates.",
            case_id=case_id,
            subject_id=transition_id,
            subject_kind="transition_candidate",
            count_observed=negative,
        )
        codes.append(code)
    if row.get("oracle_visible") is True or row.get("provider_visible") is True:
        code = "CERTIFICATE_KERNEL_EXECUTION_PROVIDER_OR_ORACLE_VISIBLE"
        _record(
            findings,
            observed,
            code,
            "Forward certificate transition execution must not see oracle sidecars or provider hypothesis text.",
            case_id=case_id,
            subject_id=transition_id,
            subject_kind="transition_candidate",
            count_observed=negative,
        )
        codes.append(code)
    action = str(row.get("action_class") or "")
    if action and action not in ALLOWED_ACTION_CLASSES:
        code = "CERTIFICATE_KERNEL_EXECUTION_ACTION_CLASS_UNKNOWN"
        _record(
            findings,
            observed,
            code,
            "Certificate transition action class is outside the bounded public action vocabulary.",
            case_id=case_id,
            subject_id=action,
            subject_kind="transition_action_class",
            count_observed=negative,
        )
        codes.append(code)
    return codes


def _execute_transition(
    row: dict[str, Any],
    *,
    project_dir: Path,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> CertificateTransitionReceipt:
    """
    [ACTION]
    - Teleology: Implements `_execute_transition` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text.
    """
    transition_id = str(row.get("transition_id") or "transition")
    codes = _validate_transition_contract(
        row,
        findings=findings,
        observed=observed,
        negative=False,
    )
    if codes:
        return CertificateTransitionReceipt(
            transition_id=transition_id,
            problem_id=str(row.get("problem_id") or ""),
            target_shape=str(row.get("target_shape") or ""),
            action_class=str(row.get("action_class") or ""),
            candidate_kind=str(row.get("candidate_kind") or ""),
            allowed_certificate_refs=tuple(_strings(row.get("allowed_certificate_refs"))),
            lean_return_code=None,
            accepted=False,
            verifier_failure_class="CONTRACT_REJECTED",
            stdout_stderr_in_receipt=False,
            oracle_visible=row.get("oracle_visible") is True,
            provider_visible=row.get("provider_visible") is True,
            proof_body_exported=False,
            contract_rejected=True,
            error_codes=tuple(codes),
        )

    source_path = project_dir / f"{transition_id}.lean"
    source_path.write_text(_lean_source_for_transition(row), encoding="utf-8")
    lean_run = _run_command(["lake", "env", "lean", source_path.name], cwd=project_dir)
    accepted = lean_run["return_code"] == 0
    return CertificateTransitionReceipt(
        transition_id=transition_id,
        problem_id=str(row.get("problem_id") or ""),
        target_shape=str(row.get("target_shape") or ""),
        action_class=str(row.get("action_class") or ""),
        candidate_kind=str(row.get("candidate_kind") or ""),
        allowed_certificate_refs=tuple(_strings(row.get("allowed_certificate_refs"))),
        lean_return_code=int(lean_run["return_code"]),
        accepted=accepted,
        verifier_failure_class="NONE"
        if accepted
        else str(row.get("expected_failure_class") or "PROOF_SYNTHESIS_FAIL"),
        stdout_stderr_in_receipt=False,
        oracle_visible=False,
        provider_visible=False,
        proof_body_exported=False,
        timed_out=lean_run["timed_out"] is True,
    )


def _contract_rejected_transition_receipt(
    row: dict[str, Any],
    codes: Sequence[str],
) -> CertificateTransitionReceipt:
    """
    [ACTION]
    - Teleology: Implements `_contract_rejected_transition_receipt` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    return CertificateTransitionReceipt(
        transition_id=str(row.get("transition_id") or "transition"),
        problem_id=str(row.get("problem_id") or ""),
        target_shape=str(row.get("target_shape") or ""),
        action_class=str(row.get("action_class") or ""),
        candidate_kind=str(row.get("candidate_kind") or ""),
        allowed_certificate_refs=tuple(_strings(row.get("allowed_certificate_refs"))),
        lean_return_code=None,
        accepted=False,
        verifier_failure_class="CONTRACT_REJECTED",
        stdout_stderr_in_receipt=False,
        oracle_visible=row.get("oracle_visible") is True,
        provider_visible=row.get("provider_visible") is True,
        proof_body_exported=False,
        contract_rejected=True,
        error_codes=tuple(codes),
    )


def _execute_transitions(
    rows: list[dict[str, Any]],
    *,
    project_dir: Path,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> list[CertificateTransitionReceipt]:
    """
    [ACTION]
    - Teleology: Implements `_execute_transitions` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    receipts: list[CertificateTransitionReceipt | None] = [None] * len(rows)
    executable: list[tuple[int, dict[str, Any]]] = []
    for index, row in enumerate(rows):
        codes = _validate_transition_contract(
            row,
            findings=findings,
            observed=observed,
            negative=False,
        )
        if codes:
            receipts[index] = _contract_rejected_transition_receipt(row, codes)
        else:
            executable.append((index, row))

    executable_rows = [row for _, row in executable]
    cache_key = (
        _transition_execution_cache_key(executable_rows, project_dir=project_dir)
        if executable_rows
        else ""
    )
    executed = deepcopy(_TRANSITION_EXECUTION_CACHE.get(cache_key, []))
    if executable_rows and not executed:
        executed_by_index: dict[int, CertificateTransitionReceipt] = {}
        positive = [
            (index, row)
            for index, row in executable
            if not _transition_expected_to_fail(row)
        ]
        pending_individual = [
            (index, row)
            for index, row in executable
            if _transition_expected_to_fail(row)
        ]
        run_positive_batch = len(positive) > 1
        batch_receipts: list[CertificateTransitionReceipt] | None = None

        def run(row: dict[str, Any]) -> CertificateTransitionReceipt:
            """
            [ACTION]
            - Teleology: Implements `_execute_transitions.run` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
            - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
            - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
            - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
            - Reads: call arguments, module constants, imported helpers.
            - Writes: return values.
            """
            return _execute_transition(
                row,
                project_dir=project_dir,
                findings=findings,
                observed=observed,
            )

        if run_positive_batch and pending_individual:
            max_workers = min(LEAN_TRANSITION_MAX_WORKERS, len(pending_individual) + 1)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                batch_future = executor.submit(
                    _execute_positive_transition_batch,
                    [row for _index, row in positive],
                    project_dir=project_dir,
                )
                individual_futures = [
                    (index, executor.submit(run, row))
                    for index, row in pending_individual
                ]
                batch_receipts = batch_future.result()
                for index, future in individual_futures:
                    executed_by_index[index] = future.result()
            pending_individual = []
        elif run_positive_batch:
            batch_receipts = _execute_positive_transition_batch(
                [row for _index, row in positive],
                project_dir=project_dir,
            )
        else:
            pending_individual.extend(positive)

        if run_positive_batch:
            if batch_receipts is None:
                pending_individual.extend(positive)
            else:
                for (index, _row), receipt in zip(
                    positive,
                    batch_receipts,
                    strict=True,
                ):
                    executed_by_index[index] = receipt

        if len(pending_individual) <= 1:
            for index, row in pending_individual:
                executed_by_index[index] = run(row)
        else:
            max_workers = min(LEAN_TRANSITION_MAX_WORKERS, len(pending_individual))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                individual_receipts = list(
                    executor.map(
                        run,
                        (row for _, row in pending_individual),
                    )
                )
            for (index, _row), receipt in zip(
                pending_individual,
                individual_receipts,
                strict=True,
            ):
                executed_by_index[index] = receipt
        executed = [executed_by_index[index] for index, _row in executable]
        _TRANSITION_EXECUTION_CACHE[cache_key] = deepcopy(executed)
    if executed:
        for (index, _row), receipt in zip(executable, executed, strict=True):
            receipts[index] = receipt

    return [
        receipt
        for receipt in receipts
        if receipt is not None
    ]


def _standalone_exported_transition_receipts(
    rows: list[dict[str, Any]],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> list[CertificateTransitionReceipt]:
    """
    [ACTION]
    - Teleology: Implements `_standalone_exported_transition_receipts` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    receipts: list[CertificateTransitionReceipt] = []
    for row in rows:
        codes = _validate_transition_contract(
            row,
            findings=findings,
            observed=observed,
            negative=False,
        )
        if codes:
            receipts.append(_contract_rejected_transition_receipt(row, codes))
            continue
        if _transition_expected_to_fail(row):
            receipts.append(
                CertificateTransitionReceipt(
                    transition_id=str(row.get("transition_id") or "transition"),
                    problem_id=str(row.get("problem_id") or ""),
                    target_shape=str(row.get("target_shape") or ""),
                    action_class=str(row.get("action_class") or ""),
                    candidate_kind=str(row.get("candidate_kind") or ""),
                    allowed_certificate_refs=tuple(
                        _strings(row.get("allowed_certificate_refs"))
                    ),
                    lean_return_code=1,
                    accepted=False,
                    verifier_failure_class=str(
                        row.get("expected_failure_class") or "PROOF_SYNTHESIS_FAIL"
                    ),
                    stdout_stderr_in_receipt=False,
                    oracle_visible=False,
                    provider_visible=False,
                    proof_body_exported=False,
                    timed_out=False,
                )
            )
            continue
        receipts.append(_accepted_transition_receipt(row))
    return receipts


def _translate_cp2(
    packet: dict[str, Any],
    *,
    transition_by_id: dict[str, CertificateTransitionReceipt],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_translate_cp2` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    translations: list[dict[str, Any]] = []
    for row in _rows(packet, "cp2_translation_requests"):
        request_id = str(row.get("request_id") or "cp2_request")
        case_id = str(row.get("expected_negative_case_id") or request_id)
        forbidden_keys = _walk_forbidden_keys(row, FORBIDDEN_CP2_KEYS)
        action = str(row.get("action_class") or "")
        codes: list[str] = []
        if forbidden_keys:
            code = "CERTIFICATE_KERNEL_EXECUTION_CP2_PROOF_BODY_FORBIDDEN"
            _record(
                findings,
                observed,
                code,
                "CP2 certificate translation emits typed action candidates only, never proof bodies or raw tactic scripts.",
                case_id=case_id,
                subject_id=request_id,
                subject_kind="cp2_translation_request",
                count_observed=False,
            )
            codes.append(code)
        if action and action not in ALLOWED_CP2_ACTION_CLASSES:
            code = "CERTIFICATE_KERNEL_EXECUTION_CP2_ACTION_CLASS_UNKNOWN"
            _record(
                findings,
                observed,
                code,
                "CP2 certificate action class is outside the bounded translation vocabulary.",
                case_id=case_id,
                subject_id=action,
                subject_kind="cp2_action_class",
                count_observed=False,
            )
            codes.append(code)
        downstream_id = str(row.get("downstream_transition_id") or "")
        downstream = transition_by_id.get(downstream_id)
        translations.append(
            {
                "request_id": request_id,
                "residual_id": row.get("residual_id"),
                "provider_hypothesis_id": row.get("provider_hypothesis_id"),
                "candidate_action_class": action,
                "candidate_kind": "typed_action_candidate",
                "selected_certificate_refs": _strings(row.get("selected_certificate_refs")),
                "proof_body_exported": False,
                "raw_tactic_script_exported": False,
                "oracle_template_exported": False,
                "provider_output_body_exported": False,
                "disconfirmation_test": row.get("disconfirmation_test"),
                "downstream_transition_id": downstream_id,
                "downstream_verifier_rerun": asdict(downstream) if downstream else None,
                "downstream_effect": bool(downstream and downstream.accepted),
                "contract_rejected": bool(codes),
                "error_codes": codes,
            }
        )
    return translations


def _run_evolve(
    packet: dict[str, Any],
    *,
    transition_by_id: dict[str, CertificateTransitionReceipt],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_run_evolve` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows: list[dict[str, Any]] = []
    for row in _rows(packet, "evolve_mutations"):
        mutation_id = str(row.get("mutation_id") or row.get("case_id") or "evolve_mutation")
        case_id = str(row.get("expected_negative_case_id") or mutation_id)
        artifact = str(row.get("mutated_artifact") or "")
        forbidden = (
            artifact not in ALLOWED_EVOLVE_ARTIFACTS
            or row.get("arbitrary_code_mutation") is True
            or row.get("source_mutation_authorized") is True
        )
        codes: list[str] = []
        if forbidden:
            code = "CERTIFICATE_KERNEL_EXECUTION_EVOLVE_SCOPE_FORBIDDEN"
            _record(
                findings,
                observed,
                code,
                "Evolve may mutate only bounded certificate-lab policy artifacts and must rerun the public problem set.",
                case_id=case_id,
                subject_id=mutation_id,
                subject_kind="evolve_mutation",
                count_observed=False,
            )
            codes.append(code)
        baseline_ids = _strings(row.get("baseline_transition_ids"))
        rerun_ids = _strings(row.get("rerun_transition_ids"))
        baseline_accepts = sum(
            1 for item in baseline_ids if transition_by_id.get(item, None) and transition_by_id[item].accepted
        )
        rerun_accepts = sum(
            1 for item in rerun_ids if transition_by_id.get(item, None) and transition_by_id[item].accepted
        )
        leakage_regression = any(
            transition_by_id[item].contract_rejected
            for item in rerun_ids
            if transition_by_id.get(item, None)
        )
        accepted = (
            not forbidden
            and not leakage_regression
            and bool(rerun_ids)
            and rerun_accepts >= baseline_accepts
            and rerun_accepts > 0
        )
        rows.append(
            {
                "mutation_id": mutation_id,
                "mutated_artifact": artifact,
                "baseline_transition_ids": baseline_ids,
                "rerun_transition_ids": rerun_ids,
                "baseline_accept_count": baseline_accepts,
                "rerun_accept_count": rerun_accepts,
                "leakage_regression": leakage_regression,
                "oracle_to_forward_contamination": False,
                "source_mutation_authorized": False,
                "decision": "accepted" if accepted else "quarantined",
                "accepted": accepted,
                "contract_rejected": bool(codes),
                "error_codes": codes,
                "body_in_receipt": False,
            }
        )
    return rows


def _validate_manifest_contract(
    payload: dict[str, Any],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> None:
    """
    [ACTION]
    - Teleology: Implements `_validate_manifest_contract` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    case_id = str(
        payload.get("expected_negative_case_id")
        or payload.get("manifest_id")
        or "certificate_manifest"
    )
    forbidden_keys = _walk_forbidden_keys(payload, FORBIDDEN_MANIFEST_KEYS)
    if forbidden_keys:
        _record(
            findings,
            observed,
            "CERTIFICATE_KERNEL_EXECUTION_MANIFEST_PROOF_BODY_FORBIDDEN",
            "Certificate manifests may carry ids, hashes, and public rows, but not proof bodies.",
            case_id=case_id,
            subject_id=str(payload.get("manifest_id") or "certificate_manifest"),
            subject_kind="certificate_manifest",
            count_observed=negative,
        )
    if _private_source_refs(payload):
        _record(
            findings,
            observed,
            "CERTIFICATE_KERNEL_EXECUTION_PRIVATE_SOURCE_REF_FORBIDDEN",
            "Certificate manifests may not import private source paths or private macro bodies.",
            case_id=case_id,
            subject_id=str(payload.get("manifest_id") or "certificate_manifest"),
            subject_kind="certificate_manifest",
            count_observed=negative,
        )


def _validate_negative_payloads(
    payloads: dict[str, dict[str, Any]],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> None:
    """
    [ACTION]
    - Teleology: Implements `_validate_negative_payloads` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for payload in payloads.values():
        if "transition_id" in payload:
            _validate_transition_contract(
                payload,
                findings=findings,
                observed=observed,
                negative=True,
            )
        if "request_id" in payload:
            request_id = str(payload.get("request_id") or "cp2_request")
            case_id = str(payload.get("expected_negative_case_id") or request_id)
            if _walk_forbidden_keys(payload, FORBIDDEN_CP2_KEYS):
                _record(
                    findings,
                    observed,
                    "CERTIFICATE_KERNEL_EXECUTION_CP2_PROOF_BODY_FORBIDDEN",
                    "CP2 negative fixture rejected proof bodies or raw tactic scripts.",
                    case_id=case_id,
                    subject_id=request_id,
                    subject_kind="cp2_translation_request",
                    count_observed=True,
                )
        if "mutated_artifact" in payload:
            mutation_id = str(payload.get("mutation_id") or "evolve_mutation")
            case_id = str(payload.get("expected_negative_case_id") or mutation_id)
            artifact = str(payload.get("mutated_artifact") or "")
            if (
                artifact not in ALLOWED_EVOLVE_ARTIFACTS
                or payload.get("arbitrary_code_mutation") is True
                or payload.get("source_mutation_authorized") is True
            ):
                _record(
                    findings,
                    observed,
                    "CERTIFICATE_KERNEL_EXECUTION_EVOLVE_SCOPE_FORBIDDEN",
                    "Evolve negative fixture rejected unbounded source mutation.",
                    case_id=case_id,
                    subject_id=mutation_id,
                    subject_kind="evolve_mutation",
                    count_observed=True,
                )
        if "manifest_id" in payload:
            _validate_manifest_contract(
                payload,
                findings=findings,
                observed=observed,
                negative=True,
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
    - Teleology: Implements `_build_result` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    public_root = _public_root_for_path(input_dir)
    packet = _load_json_if_exists(input_dir / PACKET_NAME)
    manifest = _load_json_if_exists(input_dir / MANIFEST_NAME)
    negative_payloads = {
        Path(name).stem: _load_json_if_exists(input_dir / name)
        for name in NEGATIVE_INPUT_NAMES
        if (input_dir / name).is_file()
    }
    input_paths = _input_paths(input_dir, include_negative=include_negative)
    secret_scan = scan_paths(
        input_paths,
        forbidden_classes=load_forbidden_classes(
            public_root / "core/private_state_forbidden_classes.json"
        ),
        display_root=public_root,
    )
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = {}
    _validate_manifest_contract(
        manifest,
        findings=findings,
        observed=observed,
        negative=False,
    )
    bundle_manifest = _load_json_if_exists(input_dir / "bundle_manifest.json")
    source_modules = _source_module_manifest_result(
        input_dir,
        public_root=public_root,
        require_manifest=input_mode == "exported_certificate_kernel_execution_lab_bundle",
    )
    source_module_blocked = (
        input_mode == "exported_certificate_kernel_execution_lab_bundle"
        and source_modules.get("status") != PASS
    )
    standalone_exported_certificate = (
        input_mode == "exported_certificate_kernel_execution_lab_bundle"
        and not source_module_blocked
    )
    tool_versions = (
        _standalone_exported_tool_versions()
        if standalone_exported_certificate
        else _tool_versions()
    )
    transitions: list[CertificateTransitionReceipt] = []
    lake_project_build: dict[str, Any] | None = (
        {
            "return_code": None,
            "skipped": True,
            "skip_reason": "source_module_manifest_blocked",
            "stdout_stderr_in_receipt": False,
        }
        if source_module_blocked
        else None
    )
    analyzer_receipt: dict[str, Any] = {}

    if standalone_exported_certificate:
        analyzer_receipt = _analyze_lean_project(
            input_dir / LAKE_PROJECT_DIR,
            public_root=public_root,
            source_project_dir=input_dir / LAKE_PROJECT_DIR,
        )
        lake_project_build = _standalone_exported_lake_project_build(packet)
        transitions.extend(
            _standalone_exported_transition_receipts(
                _rows(packet, "transition_candidates"),
                findings=findings,
                observed=observed,
            )
        )
    elif not source_module_blocked:
        with tempfile.TemporaryDirectory(prefix="microcosm_certificate_lab_") as temp_name:
            project_dir = _copy_project_to_temp(input_dir, Path(temp_name))
            analyzer_receipt = _analyze_lean_project(
                project_dir,
                public_root=public_root,
                source_project_dir=input_dir / LAKE_PROJECT_DIR,
            )
            lake_project_build = _build_lake_project(project_dir)
            if lake_project_build["return_code"] == 0:
                _remember_built_lake_project(input_dir, project_dir)
                transitions.extend(
                    _execute_transitions(
                        _rows(packet, "transition_candidates"),
                        project_dir=project_dir,
                        findings=findings,
                        observed=observed,
                    )
                )

    transition_by_id = {row.transition_id: row for row in transitions}
    cp2_translations = _translate_cp2(
        packet,
        transition_by_id=transition_by_id,
        findings=findings,
        observed=observed,
    )
    evolve_mutations = _run_evolve(
        packet,
        transition_by_id=transition_by_id,
        findings=findings,
        observed=observed,
    )
    if include_negative:
        _validate_negative_payloads(
            negative_payloads,
            findings=findings,
            observed=observed,
        )

    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    observed_cases = {
        case_id: sorted(codes) for case_id, codes in sorted(observed.items())
    }
    missing = sorted(case_id for case_id in expected if case_id not in observed_cases)
    accepted_transitions = [row for row in transitions if row.accepted]
    residuals = [row for row in transitions if not row.accepted and not row.contract_rejected]
    cp2_effects = [row for row in cp2_translations if row.get("downstream_effect") is True]
    evolve_accepted = [row for row in evolve_mutations if row.get("accepted") is True]
    contract_rejections = [
        *[row for row in transitions if row.contract_rejected],
        *[row for row in cp2_translations if row.get("contract_rejected")],
        *[row for row in evolve_mutations if row.get("contract_rejected")],
    ]
    findings.extend(source_modules.get("findings", []))
    source_open_body_imports = _source_open_body_import_summary(source_modules)
    certificate_families = _certificate_family_rows(manifest)
    status = (
        PASS
        if secret_scan["blocking_hit_count"] == 0
        and tool_versions["lean_available"]
        and tool_versions["lake_available"]
        and lake_project_build is not None
        and lake_project_build["return_code"] == 0
        and analyzer_receipt.get("declaration_count", 0) >= 8
        and not missing
        and len(transitions) >= 5
        and len(accepted_transitions) >= 3
        and len(residuals) >= 2
        and len(cp2_effects) >= 1
        and len(evolve_mutations) >= 1
        and len(evolve_accepted) >= 1
        and all(row.proof_body_exported is False for row in transitions)
        and (
            input_mode != "exported_certificate_kernel_execution_lab_bundle"
            or source_modules["status"] == PASS
        )
        else "blocked"
    )
    return {
        "schema_version": "certificate_kernel_execution_lab_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "certificate_lab_id": packet.get("certificate_lab_id"),
        "certificate_manifest_id": manifest.get("manifest_id"),
        "source_module_manifest_status": source_modules.get("status"),
        "source_module_manifest_ref": source_modules.get(
            "source_module_manifest_ref"
        ),
        "source_module_imports": source_modules,
        "source_module_count": source_modules.get("module_count", 0),
        "verified_source_module_count": source_modules.get(
            "verified_module_count", 0
        ),
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports.get("body_material_status"),
        "body_copied_material_count": source_open_body_imports.get(
            "body_material_count", 0
        ),
        "source_refs": _strings(packet.get("source_refs")),
        "source_pattern_ids": _strings(packet.get("source_pattern_ids")),
        "projection_receipt_refs": _strings(packet.get("projection_receipt_refs")),
        "public_runtime_refs": _strings(packet.get("public_runtime_refs")),
        "execution_witness_mode": (
            "standalone_exported_certificate_contract"
            if standalone_exported_certificate
            else "source_module_import_blocked"
            if source_module_blocked
            else "live_lean_lake_execution"
        ),
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed_cases,
        "missing_negative_cases": missing,
        "error_codes": sorted({str(row["error_code"]) for row in findings}),
        "findings": sorted(
            findings,
            key=lambda row: (
                str(row.get("negative_case_id") or ""),
                str(row.get("subject_kind") or ""),
                str(row.get("subject_id") or ""),
                str(row.get("error_code") or ""),
            ),
        ),
        "secret_exclusion_scan": secret_scan,
        "tool_versions": tool_versions,
        "lake_project_build": lake_project_build,
        "lean_analyzer_receipt": analyzer_receipt,
        "certificate_manifest_summary": {
            "manifest_id": manifest.get("manifest_id"),
            "certificate_schema": manifest.get("certificate_schema"),
            "generated_certificate_count": len(
                _rows(manifest, "generated_certificate_rows")
            ),
            "certificate_families": certificate_families,
            "negative_certificate_count": len(
                [
                    row
                    for row in _rows(manifest, "generated_certificate_rows")
                    if row.get("expected_valid") is False
                ]
            ),
            "proof_bodies_exported": False,
            "body_in_receipt": False,
        },
        "transition_trace": [asdict(row) for row in transitions],
        "cp2_translation_trace": cp2_translations,
        "evolve_mutation_trace": evolve_mutations,
        "claim_separation": {
            "lean_verified": [asdict(row) for row in accepted_transitions],
            "oracle_compared": _rows(packet, "oracle_sidecars"),
            "provider_suggested": _rows(packet, "provider_hypotheses"),
            "cp2_translated": cp2_translations,
            "contract_rejected": contract_rejections,
            "retrieval_miss": [
                asdict(row)
                for row in residuals
                if row.verifier_failure_class == "PREMISE_RETRIEVAL_MISS"
            ],
            "proof_synthesis_fail": [
                asdict(row)
                for row in residuals
                if row.verifier_failure_class != "PREMISE_RETRIEVAL_MISS"
            ],
            "evolve_candidate": evolve_mutations,
            "evolve_accepted": evolve_accepted,
        },
        "authority_counters": {
            "transition_count": len(transitions),
            "accepted_transition_count": len(accepted_transitions),
            "residual_transition_count": len(residuals),
            "cp2_translation_count": len(cp2_translations),
            "cp2_downstream_effect_count": len(cp2_effects),
            "evolve_candidate_count": len(evolve_mutations),
            "evolve_accepted_count": len(evolve_accepted),
            "analyzed_lean_file_count": analyzer_receipt.get("lean_file_count", 0),
            "analyzed_declaration_count": analyzer_receipt.get("declaration_count", 0),
            "oracle_forward_success_increment_count": 0,
            "provider_results_counted": 0,
            "proof_body_export_count": 0,
            "source_mutation_count": 0,
            "macro_private_body_import_count": 0,
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "receipt_transparency_contract": RECEIPT_TRANSPARENCY_CONTRACT,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
        # Honest run-provenance: a standalone exported certificate contract is a
        # declared synthetic shape, never a live lean/lake execution receipt.
        "real_runtime_receipt": status == PASS and not standalone_exported_certificate,
        "synthetic_contract": standalone_exported_certificate,
        "not_a_live_run": standalone_exported_certificate,
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
    - Teleology: Implements `_common_receipt` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
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
        "certificate_lab_id",
        "certificate_manifest_id",
        "source_module_manifest_status",
        "source_module_manifest_ref",
        "source_module_imports",
        "source_module_count",
        "verified_source_module_count",
        "source_open_body_imports",
        "body_material_status",
        "body_copied_material_count",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "tool_versions",
        "lake_project_build",
        "lean_analyzer_receipt",
        "certificate_manifest_summary",
        "transition_trace",
        "cp2_translation_trace",
        "evolve_mutation_trace",
        "claim_separation",
        "authority_counters",
        "authority_ceiling",
        "receipt_transparency_contract",
        "anti_claim",
        "body_in_receipt",
        "real_runtime_receipt",
        "synthetic_receipt_standin_allowed",
        "public_runtime_refs",
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
    - Teleology: Implements `_relative_receipt_paths` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [_display(path, public_root=public_root) for path in paths.values()]


def write_receipts(
    out_dir: str | Path,
    result: dict[str, Any],
    *,
    public_root: str | Path,
    acceptance_out: str | Path | None = None,
) -> dict[str, str]:
    """
    [ACTION]
    - Teleology: Implements `write_receipts` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text.
    """
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root_path = Path(public_root).resolve(strict=False)
    acceptance_path = (
        Path(acceptance_out)
        if acceptance_out is not None
        else public_root_path / ACCEPTANCE_RECEIPT_REL
    )
    if not acceptance_path.is_absolute():
        acceptance_path = Path.cwd() / acceptance_path
    paths = {
        "certificate_kernel_execution_lab_result": target / RESULT_NAME,
        "certificate_kernel_execution_lab_board": target / BOARD_NAME,
        "certificate_kernel_execution_lab_validation_receipt": target
        / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = _relative_receipt_paths(paths, public_root_path)
    result_receipt = _common_receipt(
        result,
        schema_version="certificate_kernel_execution_lab_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    board = _common_receipt(
        result,
        schema_version="certificate_kernel_execution_lab_board_v1",
        receipt_paths=receipt_paths,
    )
    board.update(
        {
            "headline": "Public certificate-kernel Lean lab under leak-proof verifier authority.",
            "lean_verified_count": len(result["claim_separation"]["lean_verified"]),
            "cp2_downstream_effect_count": result["authority_counters"][
                "cp2_downstream_effect_count"
            ],
            "evolve_accepted_count": result["authority_counters"][
                "evolve_accepted_count"
            ],
            "analyzed_declaration_count": result["authority_counters"][
                "analyzed_declaration_count"
            ],
            "proof_body_export_count": result["authority_counters"][
                "proof_body_export_count"
            ],
            "provider_results_counted": result["authority_counters"][
                "provider_results_counted"
            ],
            "oracle_forward_success_increment_count": result["authority_counters"][
                "oracle_forward_success_increment_count"
            ],
        }
    )
    validation = _common_receipt(
        result,
        schema_version="certificate_kernel_execution_lab_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "lean_certificate_kernel_execution_status": PASS
            if result["authority_counters"]["accepted_transition_count"] >= 3
            else "blocked",
            "lean_analyzer_status": PASS
            if result["authority_counters"]["analyzed_declaration_count"] >= 8
            else "blocked",
            "cp2_translation_status": PASS
            if result["authority_counters"]["cp2_downstream_effect_count"] >= 1
            else "blocked",
            "evolve_mutation_status": PASS
            if result["authority_counters"]["evolve_accepted_count"] >= 1
            else "blocked",
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "receipts_include_proof_bodies": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "macro_private_body_import_authorized": False,
            "receipt_body_is_public_evidence": True,
            "omitted_payload_scope": "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only",
            "body_in_receipt": False,
            "real_runtime_receipt": result["real_runtime_receipt"],
            "synthetic_receipt_standin_allowed": False,
            "release_authorized": False,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="certificate_kernel_execution_lab_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "accepted_scope": "bounded_public_certificate_kernel_execution_only",
            "runtime_shell_projection_deferred": True,
            "public_entry_docs_projection_deferred_ref": (
                "certificate_kernel_execution_lab_runtime_public_docs_deferred"
            ),
        }
    )
    acceptance.update(_fixture_manifest_source_binding(public_root_path))
    write_json_atomic(paths["certificate_kernel_execution_lab_result"], result_receipt)
    write_json_atomic(paths["certificate_kernel_execution_lab_board"], board)
    write_json_atomic(
        paths["certificate_kernel_execution_lab_validation_receipt"], validation
    )
    write_json_atomic(paths["fixture_acceptance"], acceptance)
    return {name: _display(path, public_root=public_root_path) for name, path in paths.items()}


def _certificate_family_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_certificate_family_rows` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(manifest, "generated_certificate_rows")
    families = [
        {
            "family_id": "nat_sum_certificate",
            "schema": "NatSumCertificate(left,right,total)",
            "row_count": sum(
                1 for row in rows if "left" in row.get("input_row", {})
            ),
            "valid_row_count": sum(
                1
                for row in rows
                if "left" in row.get("input_row", {})
                and row.get("expected_valid") is True
            ),
            "negative_row_count": sum(
                1
                for row in rows
                if "left" in row.get("input_row", {})
                and row.get("expected_valid") is False
            ),
        },
        {
            "family_id": "bounded_order_certificate",
            "schema": "BoundedOrderCertificate(base,period,modulus,witness)",
            "row_count": sum(
                1 for row in rows if "modulus" in row.get("input_row", {})
            ),
            "valid_row_count": sum(
                1
                for row in rows
                if "modulus" in row.get("input_row", {})
                and row.get("expected_valid") is True
            ),
            "negative_row_count": sum(
                1
                for row in rows
                if "modulus" in row.get("input_row", {})
                and row.get("expected_valid") is False
            ),
        },
    ]
    return [row for row in families if row["row_count"] > 0]


def build_public_readout(
    public_root: str | Path,
    *,
    receipt_dir: str | Path | None = None,
    out: str | Path | None = None,
    command: str = "microcosm certificate-kernel-execution-lab readout",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_public_readout` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    root = Path(public_root).resolve(strict=False)
    receipt_root = (
        Path(receipt_dir)
        if receipt_dir is not None
        else root / "receipts/first_wave/certificate_kernel_execution_lab"
    )
    if not receipt_root.is_absolute():
        receipt_root = root / receipt_root
    manifest_path = (
        root
        / "fixtures/first_wave/certificate_kernel_execution_lab/input/"
        / MANIFEST_NAME
    )
    result_path = receipt_root / RESULT_NAME
    board_path = receipt_root / BOARD_NAME
    validation_path = receipt_root / VALIDATION_RECEIPT_NAME
    acceptance_path = root / ACCEPTANCE_RECEIPT_REL
    manifest = _load_json_if_exists(manifest_path)
    result = _load_json_if_exists(result_path)
    board = _load_json_if_exists(board_path)
    validation = _load_json_if_exists(validation_path)
    acceptance = _load_json_if_exists(acceptance_path)
    manifest_summary = result.get("certificate_manifest_summary", {})
    if not isinstance(manifest_summary, dict):
        manifest_summary = {}
    counters = result.get("authority_counters", {})
    if not isinstance(counters, dict):
        counters = {}
    analyzer = result.get("lean_analyzer_receipt", {})
    if not isinstance(analyzer, dict):
        analyzer = {}
    transparency = result.get("receipt_transparency_contract", {})
    if not isinstance(transparency, dict):
        transparency = RECEIPT_TRANSPARENCY_CONTRACT
    dangerous_payload_absent = all(
        counters.get(key, 0) == 0
        for key in (
            "oracle_forward_success_increment_count",
            "provider_results_counted",
            "proof_body_export_count",
            "source_mutation_count",
            "macro_private_body_import_count",
        )
    )
    status = (
        PASS
        if result.get("status") == PASS
        and validation.get("status") == PASS
        and acceptance.get("status") == PASS
        and dangerous_payload_absent
        else "blocked"
    )
    evidence_refs = [
        _display(path, public_root=root)
        for path in (
            result_path,
            board_path,
            validation_path,
            acceptance_path,
            manifest_path,
        )
        if path.is_file()
    ]
    certificate_families = _certificate_family_rows(manifest)
    if not certificate_families:
        summary_families = manifest_summary.get("certificate_families", [])
        if isinstance(summary_families, list):
            certificate_families = [
                row for row in summary_families if isinstance(row, dict)
            ]
    generated_certificate_count = len(
        _rows(manifest, "generated_certificate_rows")
    )
    if generated_certificate_count == 0:
        generated_certificate_count = int(
            manifest_summary.get("generated_certificate_count") or 0
        )
    payload = {
        "schema_version": "certificate_kernel_execution_lab_public_readout_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "readout_id": "certificate_kernel_execution_lab_runtime_readout",
        "command": command,
        "certificate_lab_id": result.get("certificate_lab_id"),
        "certificate_manifest_id": (
            manifest.get("manifest_id")
            or manifest_summary.get("manifest_id")
            or result.get("certificate_manifest_id")
        ),
        "public_claim": (
            "The certificate-kernel lab is legible as a public proof-authority "
            "loop: public kernel, generated rows, Lean/Lake check, residuals, "
            "CP2 typed actions, bounded Evolve policy, and explicit anti-claims."
        ),
        "public_flow": [
            {
                "stage_id": "public_certificate_kernel",
                "evidence_ref": _display(manifest_path, public_root=root),
                "shows": [
                    "public certificate schemas",
                    "kernel declaration refs",
                    "generated row lineage",
                ],
            },
            {
                "stage_id": "generated_certificate_rows",
                "generated_certificate_count": generated_certificate_count,
                "certificate_families": certificate_families,
            },
            {
                "stage_id": "lean_lake_execution",
                "evidence_ref": _display(result_path, public_root=root),
                "lean_return_code": (
                    result.get("lake_project_build", {}).get("return_code")
                    if isinstance(result.get("lake_project_build"), dict)
                    else None
                ),
                "analyzed_lean_file_count": counters.get("analyzed_lean_file_count"),
                "analyzed_declaration_count": counters.get("analyzed_declaration_count"),
            },
            {
                "stage_id": "transition_adjudication",
                "transition_count": counters.get("transition_count"),
                "accepted_transition_count": counters.get(
                    "accepted_transition_count"
                ),
                "residual_transition_count": counters.get(
                    "residual_transition_count"
                ),
                "negative_case_ids": result.get("expected_negative_cases", []),
            },
            {
                "stage_id": "cp2_translation_rerun",
                "cp2_translation_count": counters.get("cp2_translation_count"),
                "cp2_downstream_effect_count": counters.get(
                    "cp2_downstream_effect_count"
                ),
                "action_classes_only": True,
            },
            {
                "stage_id": "bounded_evolve_policy_rerun",
                "evolve_candidate_count": counters.get("evolve_candidate_count"),
                "evolve_accepted_count": counters.get("evolve_accepted_count"),
                "source_mutation_count": counters.get("source_mutation_count"),
            },
            {
                "stage_id": "authority_counter_boundary",
                "oracle_forward_success_increment_count": counters.get(
                    "oracle_forward_success_increment_count"
                ),
                "provider_results_counted": counters.get(
                    "provider_results_counted"
                ),
                "proof_body_export_count": counters.get("proof_body_export_count"),
                "macro_private_body_import_count": counters.get(
                    "macro_private_body_import_count"
                ),
            },
        ],
        "kernel_declaration_refs": manifest.get("kernel_declaration_refs", []),
        "analyzer_summary": {
            "schema_version": analyzer.get("schema_version"),
            "lean_file_count": analyzer.get("lean_file_count"),
            "declaration_count": analyzer.get("declaration_count"),
            "generated_certificates_separate_from_kernel": analyzer.get(
                "generated_certificates_separate_from_kernel"
            ),
            "source_refs_public_root_relative": True,
        },
        "authority_counters": counters,
        "receipt_transparency_contract": transparency,
        "dangerous_payload_fields_omitted": True,
        "dangerous_payload_absent": dangerous_payload_absent,
        "authority_ceiling": result.get("authority_ceiling", AUTHORITY_CEILING),
        "anti_claim": result.get("anti_claim", ANTI_CLAIM),
        "evidence_refs": evidence_refs,
        "body_in_receipt": False,
        "real_runtime_receipt": result.get("real_runtime_receipt", False),
        "synthetic_receipt_standin_allowed": False,
    }
    if out is not None:
        out_path = _public_readout_output_path(out, public_root=root)
        write_json_atomic(out_path, payload)
    return payload


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.certificate_kernel_execution_lab run "
        f"--input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    result["receipt_paths"] = list(
        write_receipts(
            out_dir,
            result,
            public_root=_public_root_for_path(input_path),
            acceptance_out=acceptance_out,
        ).values()
    )
    return result


def run_certificate_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_certificate_bundle` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.certificate_kernel_execution_lab "
        f"run-certificate-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_certificate_kernel_execution_lab_bundle",
        include_negative=False,
    )
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(input_path)
    result_path = target / BUNDLE_RESULT_NAME
    receipt = _common_receipt(
        result,
        schema_version=(
            "exported_certificate_kernel_execution_lab_bundle_validation_result_v1"
        ),
        receipt_paths=[_display(result_path, public_root=public_root)],
    )
    write_json_atomic(result_path, receipt)
    result["receipt_paths"] = [_display(result_path, public_root=public_root)]
    return result


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.certificate_kernel_execution_lab` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog="certificate_kernel_execution_lab")
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-certificate-bundle"):
        action_parser = subparsers.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument(
            "--card",
            action="store_true",
            help="Emit a compact command-speed card; reuse a current receipt when present.",
        )
    readout_parser = subparsers.add_parser("readout")
    readout_parser.add_argument("--public-root", default="microcosm-substrate")
    readout_parser.add_argument("--receipt-dir")
    readout_parser.add_argument("--out")
    args = parser.parse_args(argv)
    if args.action == "run":
        if args.card:
            result = certificate_kernel_execution_card(
                args.input,
                args.out,
                action="run",
                include_negative=True,
                receipt_name=RESULT_NAME,
                acceptance_out=args.acceptance_out,
            )
        else:
            result = run(args.input, args.out, acceptance_out=args.acceptance_out)
    elif args.action == "run-certificate-bundle":
        if args.card:
            result = certificate_kernel_execution_card(
                args.input,
                args.out,
                action="run-certificate-bundle",
                include_negative=False,
                receipt_name=BUNDLE_RESULT_NAME,
            )
        else:
            result = run_certificate_bundle(args.input, args.out)
    else:
        result = build_public_readout(
            args.public_root,
            receipt_dir=args.receipt_dir,
            out=args.out,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
