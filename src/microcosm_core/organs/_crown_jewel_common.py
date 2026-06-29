"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs._crown_jewel_common` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: SOURCE_MANIFEST_NAME, SOURCE_IMPORT_CLASS, PUBLIC_SAFE_NORMALIZED_SOURCE_RELATIONS, REAL_SUBSTRATE_DISPOSITION, PRIVATE_PATH_MARKERS, FORBIDDEN_BODY_KEYS, CrownJewelSpec, public_root_for_path, display, strip_microcosm_prefix, file_sha256, file_line_count, rows, strings, finding, load_json_object, manifest_path_for_input, validate_source_manifest, validate_negative_cases, scan_receipt_payload_for_bodies, Evaluator, NegativeCaseEvaluator, run_crown_jewel_organ, card_for_result, ...
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
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from microcosm_core.receipts import (
    normalize_public_receipt_paths,
    utc_now,
    write_json_atomic,
)
from microcosm_core.schemas import read_json_strict
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)


SOURCE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
PUBLIC_SAFE_NORMALIZED_SOURCE_RELATIONS = frozenset(
    {
        "source_faithful_public_safe_normalized_copy",
        "source_faithful_public_safe_path_normalized_copy",
    }
)
REAL_SUBSTRATE_DISPOSITION = "real_substrate_capsule"
PRIVATE_PATH_MARKERS = ("/Users/", "src/ai_workflow")
FORBIDDEN_BODY_KEYS = {
    "body",
    "source_body",
    "source_excerpt",
    "private_source_body",
    "provider_payload",
    "secret_value",
    "raw_diff_body",
}


@dataclass(frozen=True)
class CrownJewelSpec:
    """
    [ROLE]
    - Teleology: Groups `CrownJewelSpec` data or behavior for `microcosm_core.organs._crown_jewel_common` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.organs._crown_jewel_common`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    organ_id: str
    title: str
    fixture_id: str
    validator_id: str
    result_name: str
    board_name: str
    validation_receipt_name: str
    bundle_result_name: str
    card_schema_version: str
    required_inputs: tuple[str, ...]
    expected_negative_cases: Mapping[str, tuple[str, ...]]
    anti_claim: str
    authority_ceiling: Mapping[str, Any]
    source_manifest_ref: str
    source_required_anchors: Mapping[str, tuple[str, ...]]
    bundle_input_mode: str

    @property
    def acceptance_receipt_rel(self) -> str:
        """
        [ACTION]
        - Teleology: Implements `CrownJewelSpec.acceptance_receipt_rel` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        return (
            "receipts/acceptance/first_wave/"
            f"{self.organ_id}_fixture_acceptance.json"
        )


def public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `public_root_for_path` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
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


def display(path: Path, *, public_root: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `display` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_relative_path(path, display_root=public_root)


def strip_microcosm_prefix(ref: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `strip_microcosm_prefix` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    prefix = "microcosm-substrate/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def file_sha256(path: Path) -> str | None:
    """
    [ACTION]
    - Teleology: Implements `file_sha256` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_line_count(path: Path) -> int | None:
    """
    [ACTION]
    - Teleology: Implements `file_line_count` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    if not path.is_file():
        return None
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for count, _line in enumerate(handle, start=1):
            pass
    return count


def rows(payload: object, key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `rows` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, dict):
        return []
    value = payload.get(key)
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def strings(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `strings` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [str(item) for item in value if isinstance(item, str)] if isinstance(value, list) else []


def finding(
    code: str,
    message: str,
    *,
    case_id: str | None = None,
    subject_id: str | None = None,
    expected: Any | None = None,
    observed: Any | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `finding` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payload: dict[str, Any] = {
        "error_code": code,
        "message": message,
        "body_in_receipt": False,
    }
    if case_id:
        payload["case_id"] = case_id
    if subject_id:
        payload["subject_id"] = subject_id
    if expected is not None:
        payload["expected"] = expected
    if observed is not None:
        payload["observed"] = observed
    return payload


def load_json_object(path: Path, findings: list[dict[str, Any]], *, label: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `load_json_object` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not path.is_file():
        findings.append(
            finding("CROWN_JEWEL_INPUT_MISSING", f"Missing {label}.", subject_id=path.name)
        )
        return {}
    try:
        payload = read_json_strict(path)
    except Exception as exc:  # pragma: no cover - strict parser message varies.
        findings.append(
            finding(
                "CROWN_JEWEL_INPUT_INVALID_JSON",
                f"{label} is not strict JSON: {exc}",
                subject_id=path.name,
            )
        )
        return {}
    if not isinstance(payload, dict):
        findings.append(
            finding(
                "CROWN_JEWEL_INPUT_NOT_OBJECT",
                f"{label} must be a JSON object.",
                subject_id=path.name,
            )
        )
        return {}
    return payload


def manifest_path_for_input(
    input_dir: Path,
    *,
    public_root: Path,
    source_manifest_ref: str,
) -> Path:
    """
    [ACTION]
    - Teleology: Implements `manifest_path_for_input` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    local = input_dir / SOURCE_MANIFEST_NAME
    if local.is_file():
        return local
    return public_root / strip_microcosm_prefix(source_manifest_ref)


def _source_path_for_row(row: Mapping[str, Any], *, public_root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_path_for_row` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source_ref = str(row.get("source_ref") or "")
    return public_root.parent / source_ref


def _source_ref_required(*, public_root: Path) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_source_ref_required` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (public_root.parent / ".git").is_dir()


def _active_claimed_source_ref(source_ref: str, *, repo_root: Path) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_active_claimed_source_ref` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    snapshot_path = repo_root / "state/work_ledger/active_claims_snapshot.json"
    if not source_ref or not snapshot_path.is_file():
        return False
    try:
        snapshot = read_json_strict(snapshot_path)
    except Exception:
        return False
    claims = snapshot.get("active_claims") if isinstance(snapshot, dict) else None
    if not isinstance(claims, list):
        return False
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        if claim.get("released_at") or claim.get("expired_at"):
            continue
        claimed_path = str(claim.get("path") or claim.get("scope_id") or "")
        if claim.get("scope_kind") == "path" and claimed_path == source_ref:
            return True
    return False


def _dirty_worktree_source_ref(source_ref: str, *, repo_root: Path) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_dirty_worktree_source_ref` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    if not source_ref or not (repo_root / ".git").exists():
        return False
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain", "--", source_ref],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def _target_path_for_row(
    row: Mapping[str, Any],
    *,
    manifest_path: Path,
    public_root: Path,
) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_target_path_for_row` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    row_path = str(row.get("path") or "")
    if row_path:
        return manifest_path.parent / row_path
    target_ref = strip_microcosm_prefix(str(row.get("target_ref") or ""))
    if target_ref:
        return public_root / target_ref
    return manifest_path.parent


def validate_source_manifest(
    input_dir: str | Path,
    spec: CrownJewelSpec,
    *,
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_source_manifest` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    input_path = Path(input_dir)
    manifest_path = manifest_path_for_input(
        input_path,
        public_root=public_root,
        source_manifest_ref=spec.source_manifest_ref,
    )
    manifest_ref = display(manifest_path, public_root=public_root)
    findings: list[dict[str, Any]] = []
    module_receipts: list[dict[str, Any]] = []
    source_artifact_paths: list[Path] = []
    if not manifest_path.is_file():
        return {
            "status": "blocked",
            "manifest_ref": manifest_ref,
            "module_count": 0,
            "modules": [],
            "source_artifact_paths": [],
            "body_in_receipt": False,
            "all_expected_digests_matched": False,
            "all_expected_line_counts_matched": False,
            "all_required_anchors_present": False,
            "findings": [
                finding(
                    "CROWN_JEWEL_SOURCE_MANIFEST_MISSING",
                    "Crown Jewel organs require a public source_module_manifest.json.",
                    subject_id=manifest_ref,
                )
            ],
        }

    manifest = load_json_object(manifest_path, findings, label="source module manifest")
    module_rows = rows(manifest, "modules")
    source_artifact_paths.append(manifest_path)
    if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
        findings.append(
            finding(
                "CROWN_JEWEL_SOURCE_IMPORT_CLASS_INVALID",
                "source_module_manifest.json must declare copied non-secret macro bodies.",
                expected=SOURCE_IMPORT_CLASS,
                observed=manifest.get("source_import_class"),
            )
        )

    for row in module_rows:
        source_ref = str(row.get("source_ref") or "")
        rel_path = str(row.get("path") or "")
        target_ref = str(row.get("target_ref") or "")
        copied_target_self_ref = bool(row.get("original_source_ref")) and source_ref in {
            target_ref,
            rel_path,
            f"microcosm-substrate/{rel_path}" if rel_path else "",
        }
        relation = str(row.get("source_to_target_relation") or "")
        public_safe_normalized_copy = relation in PUBLIC_SAFE_NORMALIZED_SOURCE_RELATIONS
        source_path = _source_path_for_row(row, public_root=public_root)
        target_path = _target_path_for_row(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        source_sha = file_sha256(source_path)
        target_sha = file_sha256(target_path)
        target_line_count = file_line_count(target_path)
        expected_sha = row.get("sha256")
        expected_line_count = row.get("line_count")
        source_exists = source_path.is_file()
        target_exists = target_path.is_file()
        source_required = _source_ref_required(public_root=public_root)
        source_claimed = _active_claimed_source_ref(
            source_ref,
            repo_root=public_root.parent,
        )
        source_dirty = _dirty_worktree_source_ref(
            source_ref,
            repo_root=public_root.parent,
        )
        target_expected_digest_match = (
            target_sha is not None
            and target_sha == expected_sha
            and row.get("target_sha256") == target_sha
        )
        exact_copy_manifest_digest_match = (
            target_expected_digest_match
            and row.get("source_sha256") == target_sha
        )
        source_manifest_digest_match = source_sha is not None and row.get("source_sha256") == source_sha
        original_source_sha = str(row.get("original_source_sha256") or "")
        original_source_digest_match = (
            not original_source_sha or (source_sha is not None and original_source_sha == source_sha)
        )
        public_safe_transform_present = bool(
            row.get("public_safe_transform")
            or row.get("public_safe_mode")
            or row.get("public_safety_transformations")
        )
        public_safe_normalized_digest_match = (
            public_safe_normalized_copy
            and target_expected_digest_match
            and source_manifest_digest_match
            and original_source_digest_match
            and public_safe_transform_present
        )
        anchors = tuple(spec.source_required_anchors.get(source_ref, ()))
        target_text = target_path.read_text(encoding="utf-8") if target_exists else ""
        missing_anchors = [anchor for anchor in anchors if anchor not in target_text]
        source_verified = "live_source_exact_copy"
        live_source_drift = False
        transient_live_source_drift = False
        if source_exists and target_exists and public_safe_normalized_copy:
            live_source_drift = source_sha != target_sha
            source_verified = (
                "source_faithful_public_safe_normalized_copy"
                if public_safe_normalized_digest_match
                else "public_safe_normalized_copy_unverified"
            )
            exact_copy = public_safe_normalized_digest_match
            digest_match = public_safe_normalized_digest_match
        elif source_exists and target_exists:
            live_source_drift = source_sha != target_sha
            transient_live_source_drift = (
                live_source_drift
                and exact_copy_manifest_digest_match
                and (source_claimed or source_dirty)
            )
            if transient_live_source_drift and source_claimed:
                source_verified = "manifest_target_digest_pass_live_source_claimed_drift"
            elif transient_live_source_drift:
                source_verified = "manifest_target_digest_pass_live_source_dirty_drift"
            elif live_source_drift:
                source_verified = "live_source_copy_mismatch"
            exact_copy = not live_source_drift or transient_live_source_drift
            digest_match = exact_copy_manifest_digest_match
        elif public_safe_normalized_copy and target_exists and not source_required and not source_exists:
            source_verified = "public_safe_normalized_copy_target_digest_only"
            exact_copy = (
                target_expected_digest_match
                and bool(row.get("original_source_sha256") or row.get("source_sha256"))
                and public_safe_transform_present
            )
            digest_match = exact_copy
        else:
            source_verified = "public_copy_target_digest_only"
            exact_copy = not source_required and not source_exists and exact_copy_manifest_digest_match
            digest_match = exact_copy
        line_count_match = target_line_count == expected_line_count
        live_source_digest_status = (
            "source_faithful_public_safe_normalized_copy"
            if public_safe_normalized_digest_match
            else "match"
            if source_exists and target_exists and not live_source_drift
            else "active_claim_drift"
            if transient_live_source_drift and source_claimed
            else "dirty_worktree_drift"
            if transient_live_source_drift
            else "drift"
            if source_exists and target_exists
            else "missing"
            if source_required and not source_exists
            else "not_required"
        )
        if target_exists:
            source_artifact_paths.append(target_path)
        module_receipts.append(
            {
                "module_id": row.get("module_id"),
                "source_ref": source_ref,
                "target_ref": str(row.get("target_ref") or rel_path),
                "original_source_ref": row.get("original_source_ref"),
                "copied_target_self_ref": copied_target_self_ref,
                "path": rel_path,
                "source_exists": source_exists,
                "target_exists": target_exists,
                "source_ref_required": source_required,
                "source_ref_verification": source_verified,
                "live_source_claimed": source_claimed,
                "live_source_dirty": source_dirty,
                "live_source_digest_status": live_source_digest_status,
                "source_to_target_relation": relation,
                "public_safe_mode": row.get("public_safe_mode"),
                "public_safe_transform_present": public_safe_transform_present,
                "body_copied": row.get("body_copied") is True,
                "body_in_receipt": False,
                "sha256": target_sha,
                "expected_sha256": expected_sha,
                "source_sha256": source_sha,
                "expected_source_sha256": row.get("source_sha256"),
                "original_source_sha256": row.get("original_source_sha256"),
                "target_sha256": target_sha,
                "expected_target_sha256": row.get("target_sha256"),
                "source_target_sha256_match": (
                    source_sha is not None and target_sha is not None and source_sha == target_sha
                ),
                "target_expected_digest_match": target_expected_digest_match,
                "digest_status": "match" if digest_match else "mismatch",
                "line_count": target_line_count,
                "expected_line_count": expected_line_count,
                "line_count_status": "match" if line_count_match else "mismatch",
                "required_anchor_count": len(anchors),
                "missing_required_anchors": missing_anchors,
            }
        )
        if source_required and not source_exists:
            findings.append(
                finding(
                    "CROWN_JEWEL_SOURCE_REF_MISSING",
                    "source_ref must exist in the macro repo.",
                    subject_id=source_ref,
                )
            )
        if copied_target_self_ref:
            findings.append(
                finding(
                    "CROWN_JEWEL_SOURCE_SELF_REFERENCE_UNVERIFIED",
                    "source_ref must point at the macro source, not the copied target, when original_source_ref is present.",
                    subject_id=source_ref,
                    expected=row.get("original_source_ref"),
                    observed=source_ref,
                )
            )
        if not target_exists:
            findings.append(
                finding(
                    "CROWN_JEWEL_SOURCE_TARGET_MISSING",
                    "Copied source target must exist in the public bundle.",
                    subject_id=rel_path,
                )
            )
        if public_safe_normalized_copy and not digest_match:
            findings.append(
                finding(
                    "CROWN_JEWEL_SOURCE_SAFE_NORMALIZED_COPY_UNVERIFIED",
                    "Public-safe normalized copied source must bind live source digest, target digest, and sanitization receipt.",
                    subject_id=source_ref,
                    expected={
                        "source_sha256": row.get("source_sha256"),
                        "target_sha256": row.get("target_sha256"),
                        "public_safe_transform_present": True,
                    },
                    observed={
                        "source_sha256": source_sha,
                        "target_sha256": target_sha,
                        "public_safe_transform_present": public_safe_transform_present,
                    },
                )
            )
        elif (source_required or source_exists) and not exact_copy:
            findings.append(
                finding(
                    "CROWN_JEWEL_SOURCE_BODY_COPY_MISMATCH",
                    "Copied source target must exactly match source_ref.",
                    subject_id=source_ref,
                )
            )
        if not digest_match:
            findings.append(
                finding(
                    "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH",
                    "Copied source digest must match source_module_manifest.json.",
                    subject_id=source_ref,
                    expected=expected_sha,
                    observed=target_sha,
                )
            )
        if not line_count_match:
            findings.append(
                finding(
                    "CROWN_JEWEL_SOURCE_LINE_COUNT_MISMATCH",
                    "Copied source line count must match source_module_manifest.json.",
                    subject_id=source_ref,
                    expected=expected_line_count,
                    observed=target_line_count,
                )
            )
        if missing_anchors:
            findings.append(
                finding(
                    "CROWN_JEWEL_SOURCE_ANCHOR_MISSING",
                    "Copied source body is missing required provenance anchors.",
                    subject_id=source_ref,
                    expected=list(anchors),
                    observed={"missing": missing_anchors},
                )
            )

    forbidden_classes = load_forbidden_classes(
        public_root / "core/private_state_forbidden_classes.json"
    )
    secret_scan = scan_paths(
        source_artifact_paths,
        forbidden_classes=forbidden_classes,
        display_root=public_root,
    )
    if secret_scan.get("blocking_hit_count", 0) != 0:
        findings.append(
            finding(
                "CROWN_JEWEL_SOURCE_SECRET_SCAN_BLOCKED",
                "Copied source artifacts must pass secret-exclusion scanning.",
                observed=secret_scan.get("blocking_hit_count"),
            )
        )

    return {
        "status": PASS if not findings else "blocked",
        "manifest_ref": manifest_ref,
        "source_import_class": manifest.get("source_import_class"),
        "module_count": len(module_receipts),
        "modules": module_receipts,
        "source_artifact_paths": [display(path, public_root=public_root) for path in source_artifact_paths],
        "source_manifest_path": str(manifest_path),
        "body_in_receipt": False,
        "all_expected_digests_matched": all(
            row["digest_status"] == "match" for row in module_receipts
        ),
        "all_expected_line_counts_matched": all(
            row["line_count_status"] == "match" for row in module_receipts
        ),
        "all_required_anchors_present": all(
            not row["missing_required_anchors"] for row in module_receipts
        ),
        "all_live_source_refs_current": all(
            row["live_source_digest_status"]
            in {
                "match",
                "not_required",
                "source_faithful_public_safe_normalized_copy",
            }
            for row in module_receipts
        ),
        "active_claimed_live_source_drift_count": sum(
            1
            for row in module_receipts
            if row["live_source_digest_status"] == "active_claim_drift"
        ),
        "dirty_worktree_live_source_drift_count": sum(
            1
            for row in module_receipts
            if row["live_source_digest_status"] == "dirty_worktree_drift"
        ),
        "secret_exclusion_scan": secret_scan,
        "findings": findings,
    }


def validate_negative_cases(
    input_dir: str | Path,
    expected_negative_cases: Mapping[str, tuple[str, ...]],
    *,
    negative_case_evaluator: "NegativeCaseEvaluator | None" = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_negative_cases` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_dir)
    findings: list[dict[str, Any]] = []
    observed_negative_cases: list[str] = []
    observed_codes: list[str] = []
    case_results: list[dict[str, Any]] = []
    for case_id, expected_codes in sorted(expected_negative_cases.items()):
        case_path = input_path / f"{case_id}.json"
        if not case_path.is_file():
            findings.append(
                finding(
                    "CROWN_JEWEL_NEGATIVE_CASE_MISSING",
                    "Expected negative case fixture is missing.",
                    case_id=case_id,
                    subject_id=case_path.name,
                )
            )
            continue
        payload = load_json_object(case_path, findings, label=f"negative case {case_id}")
        if negative_case_evaluator is None:
            case_status = "missing_semantic_evaluator"
            case_codes: list[str] = []
            findings.append(
                finding(
                    "CROWN_JEWEL_NEGATIVE_CASE_SEMANTIC_EVALUATOR_MISSING",
                    "Negative cases require a semantic evaluator; fixture-declared status/error_codes are not proof of rejection.",
                    case_id=case_id,
                    subject_id=case_path.name,
                    expected=["negative_case_evaluator"],
                    observed={
                        "declared_status": payload.get("status"),
                        "declared_error_codes": strings(payload.get("error_codes")),
                    },
                )
            )
        else:
            semantic_result = dict(
                negative_case_evaluator(case_id, input_path, tuple(expected_codes))
            )
            case_status = str(semantic_result.get("status") or "")
            case_codes = strings(semantic_result.get("error_codes"))
            if case_status == PASS:
                findings.append(
                    finding(
                        "CROWN_JEWEL_NEGATIVE_CASE_NOT_REJECTED",
                        "Semantic negative case evaluator accepted a wrong input.",
                        case_id=case_id,
                        expected=["blocked"],
                        observed=case_status,
                    )
                )
            elif case_status != "blocked":
                findings.append(
                    finding(
                        "CROWN_JEWEL_NEGATIVE_CASE_STATUS_UNSUPPORTED",
                        "Semantic negative case evaluator returned an unsupported status.",
                        case_id=case_id,
                        expected=["blocked"],
                        observed=case_status,
                    )
                )
        case_results.append(
            {
                "case_id": case_id,
                "status": case_status,
                "error_codes": case_codes,
                "semantic_evaluator_used": negative_case_evaluator is not None,
                "body_in_receipt": False,
            }
        )
        missing = [code for code in expected_codes if code not in case_codes]
        if missing:
            findings.append(
                finding(
                    "CROWN_JEWEL_NEGATIVE_CASE_CODE_MISSING",
                    "Negative case did not emit its expected stable code.",
                    case_id=case_id,
                    expected=list(expected_codes),
                    observed=case_codes,
                )
            )
            continue
        observed_negative_cases.append(case_id)
        observed_codes.extend(case_codes)
    return {
        "status": PASS if not findings else "blocked",
        "observed_negative_cases": observed_negative_cases,
        "missing_negative_cases": [
            case_id
            for case_id in sorted(expected_negative_cases)
            if case_id not in observed_negative_cases
        ],
        "error_codes": sorted(set(observed_codes)),
        "negative_case_semantics": case_results,
        "semantic_evaluator_used": negative_case_evaluator is not None,
        "findings": findings,
    }


def scan_receipt_payload_for_bodies(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `scan_receipt_payload_for_bodies` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    keys: list[str] = []

    def walk(value: object) -> None:
        """
        [ACTION]
        - Teleology: Implements `scan_receipt_payload_for_bodies.walk` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        if isinstance(value, dict):
            for key, child in value.items():
                keys.append(str(key))
                walk(child)
            return
        if isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    forbidden_keys = sorted(FORBIDDEN_BODY_KEYS.intersection(keys))
    text = json.dumps(payload, sort_keys=True)
    private_markers = [marker for marker in PRIVATE_PATH_MARKERS if marker in text]
    return {
        "status": PASS if not forbidden_keys and not private_markers else "blocked",
        "body_in_receipt": False,
        "forbidden_body_keys": forbidden_keys,
        "private_path_markers": private_markers,
    }


Evaluator = Callable[[Path, Path, dict[str, Any]], dict[str, Any]]
NegativeCaseEvaluator = Callable[[str, Path, tuple[str, ...]], Mapping[str, Any]]


def _receipt_ref(path: Path, *, public_root: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_receipt_ref` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return display(path, public_root=public_root)


def run_crown_jewel_organ(
    spec: CrownJewelSpec,
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
    input_mode: str = "fixture_input",
    evaluator: Evaluator,
    negative_case_evaluator: NegativeCaseEvaluator | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_crown_jewel_organ` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    input_path = Path(input_dir)
    out_path = Path(out_dir)
    public_root = public_root_for_path(input_path)
    findings: list[dict[str, Any]] = []
    input_payloads: dict[str, dict[str, Any]] = {}
    for name in spec.required_inputs:
        input_payloads[name] = load_json_object(
            input_path / name,
            findings,
            label=name,
        )

    source_manifest = validate_source_manifest(input_path, spec, public_root=public_root)
    findings.extend(source_manifest.get("findings", []))
    exercise = evaluator(input_path, public_root, source_manifest)
    findings.extend(exercise.get("findings", []))
    negative_cases = validate_negative_cases(
        input_path,
        spec.expected_negative_cases,
        negative_case_evaluator=negative_case_evaluator,
    )
    findings.extend(negative_cases.get("findings", []))

    forbidden_classes = load_forbidden_classes(
        public_root / "core/private_state_forbidden_classes.json"
    )
    scan_candidates = [input_path / name for name in spec.required_inputs]
    scan_candidates.extend(input_path / f"{case_id}.json" for case_id in spec.expected_negative_cases)
    secret_scan = scan_paths(
        [path for path in scan_candidates if path.is_file()],
        forbidden_classes=forbidden_classes,
        display_root=public_root,
    )
    if secret_scan.get("blocking_hit_count", 0) != 0:
        findings.append(
            finding(
                "CROWN_JEWEL_FIXTURE_SECRET_SCAN_BLOCKED",
                "Fixture inputs must pass secret-exclusion scanning.",
                observed=secret_scan.get("blocking_hit_count"),
            )
        )

    status = PASS if not findings else "blocked"
    out_path.mkdir(parents=True, exist_ok=True)
    result_path = out_path / (
        spec.bundle_result_name if input_mode == spec.bundle_input_mode else spec.result_name
    )
    board_path = out_path / spec.board_name
    validation_path = out_path / spec.validation_receipt_name
    receipt_paths = [
        _receipt_ref(result_path, public_root=public_root),
        _receipt_ref(board_path, public_root=public_root),
        _receipt_ref(validation_path, public_root=public_root),
    ]
    if acceptance_out:
        acceptance_path = Path(acceptance_out)
        receipt_paths.append(_receipt_ref(acceptance_path, public_root=public_root))
    else:
        acceptance_path = None

    payload: dict[str, Any] = {
        "schema_version": f"{spec.organ_id}_receipt_v1",
        "organ_id": spec.organ_id,
        "fixture_id": spec.fixture_id,
        "validator_id": spec.validator_id,
        "created_at": utc_now(),
        "status": status,
        "input_mode": input_mode,
        "input_ref": display(input_path, public_root=public_root),
        "command": command,
        "anti_claim": spec.anti_claim,
        "authority_ceiling": dict(spec.authority_ceiling),
        "real_substrate_disposition": REAL_SUBSTRATE_DISPOSITION,
        "input_count": len(spec.required_inputs),
        "source_module_manifest": {
            key: value
            for key, value in source_manifest.items()
            if key not in {"findings", "source_manifest_path"}
        },
        "exercise": {
            key: value
            for key, value in exercise.items()
            if key not in {"findings"}
        },
        "observed_negative_cases": negative_cases["observed_negative_cases"],
        "missing_negative_cases": negative_cases["missing_negative_cases"],
        "expected_negative_cases": sorted(spec.expected_negative_cases),
        "negative_case_semantics": negative_cases["negative_case_semantics"],
        "semantic_negative_case_evaluator_used": negative_cases["semantic_evaluator_used"],
        "error_codes": sorted(
            {
                *(row.get("error_code") for row in findings if row.get("error_code")),
                *negative_cases["error_codes"],
                *strings(exercise.get("error_codes")),
            }
        ),
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "receipt_paths": receipt_paths,
        "body_in_receipt": False,
    }
    payload["receipt_body_scan"] = scan_receipt_payload_for_bodies(payload)
    if payload["receipt_body_scan"]["status"] != PASS:
        payload["status"] = "blocked"
        payload["error_codes"] = sorted(
            set(payload["error_codes"]) | {"CROWN_JEWEL_RECEIPT_BODY_SCAN_BLOCKED"}
        )

    board_payload = {
        "schema_version": f"{spec.organ_id}_board_v1",
        "organ_id": spec.organ_id,
        "title": spec.title,
        "status": payload["status"],
        "verdict": payload["status"],
        "counts": {
            "input_count": payload["input_count"],
            "source_module_count": source_manifest.get("module_count", 0),
            "observed_negative_case_count": len(payload["observed_negative_cases"]),
            "finding_count": len(payload["findings"]),
        },
        "anti_claim": spec.anti_claim,
        "authority_ceiling": dict(spec.authority_ceiling),
        "body_in_receipt": False,
    }
    validation_payload = {
        "schema_version": f"{spec.organ_id}_validation_receipt_v1",
        "organ_id": spec.organ_id,
        "status": payload["status"],
        "validator_id": spec.validator_id,
        "source_module_manifest_status": source_manifest.get("status"),
        "exercise_status": exercise.get("status"),
        "negative_case_status": negative_cases.get("status"),
        "secret_exclusion_status": secret_scan.get("status"),
        "receipt_body_scan_status": payload["receipt_body_scan"]["status"],
        "anti_claim": spec.anti_claim,
        "body_in_receipt": False,
    }
    write_json_atomic(result_path, payload)
    write_json_atomic(board_path, board_payload)
    write_json_atomic(validation_path, validation_payload)
    if acceptance_path:
        write_json_atomic(
            acceptance_path,
            {
                "schema_version": "microcosm_first_wave_fixture_acceptance_v1",
                "organ_id": spec.organ_id,
                "fixture_id": spec.fixture_id,
                "status": payload["status"],
                "accepted": payload["status"] == PASS,
                "real_substrate_disposition": REAL_SUBSTRATE_DISPOSITION,
                "result_ref": _receipt_ref(result_path, public_root=public_root),
                "validation_ref": _receipt_ref(validation_path, public_root=public_root),
                "anti_claim": spec.anti_claim,
                "body_in_receipt": False,
            },
        )
    return payload


def card_for_result(spec: CrownJewelSpec, result: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `card_for_result` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    source = (
        result.get("source_module_manifest")
        if isinstance(result.get("source_module_manifest"), Mapping)
        else {}
    )
    receipt_paths = result.get("receipt_paths", [])
    normalized = normalize_public_receipt_paths({"receipt_paths": receipt_paths})
    normalized_paths = (
        normalized.get("receipt_paths") if isinstance(normalized, dict) else None
    )
    card_receipt_paths = (
        normalized_paths if isinstance(normalized_paths, list) else receipt_paths
    )
    return {
        "schema_version": spec.card_schema_version,
        "organ_id": spec.organ_id,
        "status": result.get("status"),
        "input_mode": result.get("input_mode"),
        "source_module_status": source.get("status"),
        "source_module_count": source.get("module_count"),
        "exercise_status": exercise.get("status"),
        "observed_negative_case_count": len(result.get("observed_negative_cases", [])),
        "missing_negative_cases": result.get("missing_negative_cases", []),
        "semantic_negative_case_evaluator_used": result.get(
            "semantic_negative_case_evaluator_used"
        )
        is True,
        "error_codes": result.get("error_codes", []),
        "receipt_paths": card_receipt_paths,
        "anti_claim": spec.anti_claim,
        "body_in_receipt": False,
    }


def main_for_spec(
    spec: CrownJewelSpec,
    argv: list[str] | None,
    *,
    evaluator: Evaluator,
    negative_case_evaluator: NegativeCaseEvaluator | None = None,
    bundle_action: str,
) -> int:
    """
    [ACTION]
    - Teleology: Implements `main_for_spec` for `microcosm_core.organs._crown_jewel_common` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog=f"microcosm {spec.organ_id}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", bundle_action):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    command = f"{spec.organ_id} {args.action}"
    result = run_crown_jewel_organ(
        spec,
        args.input,
        args.out,
        command=command,
        acceptance_out=args.acceptance_out,
        input_mode=spec.bundle_input_mode if args.action == bundle_action else "fixture_input",
        evaluator=evaluator,
        negative_case_evaluator=negative_case_evaluator,
    )
    if args.card:
        print(json.dumps(card_for_result(spec, result), indent=2, sort_keys=True))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == PASS else 1
