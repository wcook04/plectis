"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.agent_sandbox_policy_escape_replay` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, ACCEPTANCE_RECEIPT_REL, BUNDLE_RESULT_NAME, CARD_SCHEMA_VERSION, CARD_OMITTED_FULL_PAYLOAD_KEYS, BODY_IMPORT_STATUS, BODY_IMPORT_CLASSIFICATION, PRODUCT_PATH_ROLE, SOURCE_MODULE_MANIFEST_NAME, SOURCE_IMPORT_CLASS, SOURCE_MODULE_IMPORT_STATUS, SOURCE_OPEN_BODY_SCHEMA, PUBLIC_SAFE_SOURCE_BODY_CLASSES, INPUT_NAMES, NEGATIVE_INPUT_NAMES, EXPECTED_NEGATIVE_CASES, REQUIRED_ACTION_FIELDS, REQUIRED_VERDICT_FIELDS, REQUIRED_EFFECT_FIELDS, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs, environment variables.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.macro_tools.agent_execution_trace, microcosm_core.receipts, microcosm_core.schemas, microcosm_core.secret_exclusion_scan
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

from microcosm_core.macro_tools.agent_execution_trace import build_public_sandbox_policy_trace
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


ORGAN_ID = "agent_sandbox_policy_escape_replay"
FIXTURE_ID = "first_wave.agent_sandbox_policy_escape_replay"
VALIDATOR_ID = "validator.microcosm.organs.agent_sandbox_policy_escape_replay"

RESULT_NAME = "agent_sandbox_policy_escape_replay_result.json"
BOARD_NAME = "agent_sandbox_policy_escape_replay_board.json"
VALIDATION_RECEIPT_NAME = "agent_sandbox_policy_escape_replay_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "agent_sandbox_policy_escape_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_sandbox_policy_escape_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "agent_sandbox_policy_escape_replay_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "findings",
    "secret_exclusion_scan",
    "public_agent_execution_trace",
    "source_refs",
    "projection_receipt_refs",
    "target_refs",
    "target_symbols",
    "public_runtime_refs",
    "omitted_secret_or_live_access_material",
    "request_rows",
    "policy_verdict_rows",
    "side_effect_rows",
    "rollback_rows",
    "cold_replay_rows",
    "derived_policy_verdict_rows",
    "authority_ceiling",
    "anti_claim",
    "source_module_imports",
    "source_open_body_imports",
)
BODY_IMPORT_STATUS = "extension_of_existing_public_refactor_landed"
BODY_IMPORT_CLASSIFICATION = "extension_of_existing_public_refactor"
PRODUCT_PATH_ROLE = "source_faithful_public_agent_execution_trace_refactor"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_MODULE_IMPORT_STATUS = (
    "copied_non_secret_agent_sandbox_policy_escape_macro_body_landed"
)
SOURCE_OPEN_BODY_SCHEMA = "agent_sandbox_policy_escape_replay_source_open_body_imports_v1"
PUBLIC_SAFE_SOURCE_BODY_CLASSES = frozenset(
    {
        "public_macro_control_plane_body",
        "public_macro_pattern_body",
        "public_macro_receipt_body",
        "public_macro_standard_body",
        "public_macro_tool_body",
    }
)

INPUT_NAMES = (
    "projection_protocol.json",
    "sandbox_policy.json",
    "action_requests.json",
    "policy_verdicts.json",
    "side_effect_receipts.json",
    "rollback_receipts.json",
    "cold_replay.json",
)
NEGATIVE_INPUT_NAMES = (
    "real_secret_material.json",
    "live_network_access.json",
    "raw_environment_export.json",
    "policy_after_execution.json",
    "unlogged_side_effect.json",
    "tool_output_policy_bypass.json",
    "executable_escape_payload.json",
    "security_benchmark_claim.json",
)

EXPECTED_NEGATIVE_CASES = {
    "real_secret_material": ["SANDBOX_POLICY_REAL_SECRET_FORBIDDEN"],
    "live_network_access": ["SANDBOX_POLICY_LIVE_NETWORK_FORBIDDEN"],
    "raw_environment_export": ["SANDBOX_POLICY_RAW_ENV_EXPORT_FORBIDDEN"],
    "policy_after_execution": ["SANDBOX_POLICY_AFTER_EXECUTION"],
    "unlogged_side_effect": ["SANDBOX_POLICY_UNLOGGED_SIDE_EFFECT"],
    "tool_output_policy_bypass": ["SANDBOX_POLICY_TOOL_OUTPUT_AUTHORITY_BYPASS"],
    "executable_escape_payload": ["SANDBOX_POLICY_EXECUTABLE_PAYLOAD_FORBIDDEN"],
    "security_benchmark_claim": ["SANDBOX_POLICY_SECURITY_BENCHMARK_CLAIM"],
}

REQUIRED_ACTION_FIELDS = (
    "request_id",
    "episode_id",
    "action_kind",
    "normalized_action_ref",
    "source_trust_label",
    "untrusted_tool_output_ref",
    "requested_capability",
    "risk_class",
    "intended_side_effect_ref",
    "body_redacted",
)
REQUIRED_VERDICT_FIELDS = (
    "request_id",
    "policy_version",
    "verdict",
    "rule_refs",
    "pre_execution",
    "decision_reason_ref",
    "body_redacted",
)
REQUIRED_EFFECT_FIELDS = (
    "request_id",
    "execution_attempted",
    "filesystem_diff_ref",
    "network_diff_ref",
    "database_diff_ref",
    "side_effect_diff_count",
    "rollback_receipt_ref",
    "body_redacted",
)
FORBIDDEN_KEYS = (
    "credential_value",
    "secret_value",
    "raw_environment",
    "raw_env",
    "raw_tool_output_body",
    "executable_payload",
    "host_absolute_path",
    "provider_payload",
    "real_target_identifier",
)
EXPECTED_ACTION_POLICY = {
    "secret_access": (
        "block",
        "rule:no_secret_or_env_read_from_untrusted_context",
    ),
    "network_exfiltration": (
        "block",
        "rule:no_live_network_from_untrusted_context",
    ),
    "destructive_filesystem_mutation": (
        "block",
        "rule:no_destructive_filesystem_mutation",
    ),
    "escape_payload_obfuscation": (
        "block",
        "rule:no_executable_escape_payload_or_obfuscation",
    ),
    "low_risk_public_fixture_mutation": (
        "allow",
        "rule:public_fixture_write_with_diff_receipt",
    ),
    "review_required_side_effect": (
        "review",
        "rule:side_effect_requires_approval_and_rollback",
    ),
}
EXPECTED_ACTION_POLICY_SHAPES = {
    "secret_access": {
        "action_kinds": {"environment_secret_read"},
        "requested_capabilities": {"environment_read"},
        "source_trust_labels": {"untrusted_tool_output"},
    },
    "network_exfiltration": {
        "action_kinds": {"network_request"},
        "requested_capabilities": {"outbound_network"},
        "source_trust_labels": {"untrusted_tool_output"},
    },
    "destructive_filesystem_mutation": {
        "action_kinds": {"filesystem_delete"},
        "requested_capabilities": {"filesystem_write"},
        "source_trust_labels": {"untrusted_repo_file"},
    },
    "escape_payload_obfuscation": {
        "action_kinds": {"shell_command"},
        "requested_capabilities": {"shell_exec"},
        "source_trust_labels": {"untrusted_tool_output"},
    },
    "low_risk_public_fixture_mutation": {
        "action_kinds": {"filesystem_write"},
        "requested_capabilities": {"public_fixture_write"},
        "source_trust_labels": {"trusted_user_request"},
    },
    "review_required_side_effect": {
        "action_kinds": {"mock_database_update"},
        "requested_capabilities": {"mock_database_write"},
        "source_trust_labels": {"trusted_operator_approval_ref"},
    },
}
FAIL_CLOSED_POLICY_SEMANTICS = (
    "block",
    "rule:sandbox_policy_fail_closed_unrecognized_action",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_agent_execution_trace_refactor_over_synthetic_sandbox_policy_fixture",
    "live_agent_execution_authorized": False,
    "live_sandbox_escape_authorized": False,
    "live_secret_or_credential_handling_authorized": False,
    "live_network_access_authorized": False,
    "host_filesystem_mutation_authorized": False,
    "executable_escape_payload_export_authorized": False,
    "raw_environment_export_authorized": False,
    "tool_output_authority_expansion_authorized": False,
    "security_benchmark_claim_authorized": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Agent sandbox policy-escape replay validates synthetic action, policy "
    "verdict, side-effect diff, rollback, cold-replay, negative-case, and "
    "authority-ceiling receipts, and now emits public agent-execution trace "
    "spans over those public refs. It does not authorize live sandbox escape, "
    "live secret handling, live network access, host filesystem mutation, "
    "executable payload export, raw environment export, provider calls, "
    "security benchmark claims, source mutation, or release."
)


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_display` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_rows` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, dict):
        return []
    rows = payload.get(key, [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _strings(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    bundle_manifest = input_dir / "bundle_manifest.json"
    if bundle_manifest.is_file():
        paths.append(bundle_manifest)
    return paths


def _sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _source_module_manifest_path(input_dir: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_path` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_source_module_target_path` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_source_module_paths` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_scan_paths_for_input` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_freshness_paths` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source = Path(input_dir)
    public_root = _public_root_for_path(source)
    return [
        *_input_paths(source, include_negative=include_negative),
        *_source_module_paths(source, public_root=public_root),
        Path(__file__).resolve(),
        public_root / "core/private_state_forbidden_classes.json",
    ]


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_freshness_basis` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
        "agent_sandbox_policy_escape_replay_result_v1"
        if include_negative
        else "exported_sandbox_policy_escape_bundle_validation_result_v1"
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
        "schema_version": "agent_sandbox_policy_escape_replay_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_bundle_receipt(input_dir: Path, out_dir: Path) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Implements `_fresh_bundle_receipt` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
    if payload.get("schema_version") != (
        "exported_sandbox_policy_escape_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("input_mode") != "exported_sandbox_policy_escape_bundle":
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
    - Teleology: Implements `_load_payloads` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_finding` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
        "body_redacted": True,
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
    - Teleology: Implements `_record` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    """
    [ACTION]
    - Teleology: Implements `_merge_observed` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[str(case_id)].add(str(code))
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_merge_findings` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    for result in results:
        findings.extend(result.get("findings", []))
    return sorted(
        findings,
        key=lambda row: (
            str(row.get("negative_case_id") or ""),
            str(row.get("subject_kind") or ""),
            str(row.get("subject_id") or ""),
            str(row.get("error_code") or ""),
        ),
    )


def _source_module_manifest_result(
    input_dir: Path,
    *,
    public_root: Path,
    require_manifest: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_result` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
                    "SANDBOX_POLICY_SOURCE_MODULE_MANIFEST_REQUIRED",
                    "Exported sandbox-policy bundle must include a source module manifest for copied non-secret macro body material.",
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
            "findings": findings,
            "observed_negative_cases": {},
            "body_in_receipt": False,
            "body_text_in_receipt": False,
        }

    manifest = read_json_strict(manifest_path)
    findings: list[dict[str, Any]] = []
    modules = _rows(manifest, "modules")
    module_ids: list[str] = []
    material_class_counts: dict[str, int] = {}
    source_refs = [manifest_ref]

    if not isinstance(manifest, dict):
        modules = []
        findings.append(
            _finding(
                "SANDBOX_POLICY_SOURCE_MODULE_MANIFEST_REQUIRED",
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
                    "SANDBOX_POLICY_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module manifest must classify imports as copied non-secret macro body material.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="source_import_class",
                )
            )
        if manifest.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "SANDBOX_POLICY_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must keep body text out of receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="body_in_receipt",
                )
            )
        if manifest.get("body_text_in_receipt") is not False:
            findings.append(
                _finding(
                    "SANDBOX_POLICY_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must keep body text out of receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=manifest_ref,
                    subject_kind="body_text_in_receipt",
                )
            )
        if int(manifest.get("module_count") or 0) != len(modules):
            findings.append(
                _finding(
                    "SANDBOX_POLICY_SOURCE_MODULE_COUNT_MISMATCH",
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
                    "SANDBOX_POLICY_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must classify copied material as non-secret macro body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_import_class",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_BODY_CLASSES:
            findings.append(
                _finding(
                    "SANDBOX_POLICY_SOURCE_MODULE_CLASS_REQUIRED",
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
                    "SANDBOX_POLICY_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module rows must copy body into source_modules while keeping receipt fields body-free.",
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
                    "SANDBOX_POLICY_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target body must exist inside the public bundle.",
                    case_id="source_module_manifest_floor",
                    subject_id=target_ref or module_id,
                    subject_kind="source_module",
                )
            )
            continue
        actual = _sha256(target)
        expected_digests = {
            "sha256": str(row.get("sha256") or ""),
            "source_sha256": str(row.get("source_sha256") or ""),
            "target_sha256": str(row.get("target_sha256") or ""),
        }
        if any(value != actual for value in expected_digests.values()):
            findings.append(
                _finding(
                    "SANDBOX_POLICY_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module digest declarations must match the copied target body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
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
                        "SANDBOX_POLICY_SOURCE_MODULE_ANCHOR_MISSING",
                        "Source module body must carry the declared sandbox-policy macro anchors.",
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
        "findings": findings,
        "observed_negative_cases": {},
        "body_in_receipt": False,
        "body_text_in_receipt": False,
    }


def _source_open_body_import_summary(
    source_module_result: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_open_body_import_summary` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
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
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "body_text_exported_in_workingness": False,
        "authority_ceiling": {
            "credential_payload_exported": False,
            "account_session_exported": False,
            "browser_hud_live_access_exported": False,
            "provider_payload_exported": False,
            "raw_environment_payload_exported": False,
            "live_network_payload_exported": False,
            "executable_escape_payload_exported": False,
            "security_benchmark_claim_authorized": False,
            "source_mutation_authorized": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported sandbox-policy escape bundle for copied macro pattern, "
            "reconstruction, canonical-organ, trace-standard, trace runtime, "
            "and route-readiness tool bodies; receipts carry refs, hashes, "
            "counts, and verdicts only."
        )
        if imported
        else "",
    }


def _missing(row: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_missing` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [field for field in required if row.get(field) in (None, "", [])]


def _has_forbidden_key(row: dict[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_has_forbidden_key` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return any(key in row for key in FORBIDDEN_KEYS)


def _policy_shape_mismatches(row: dict[str, Any]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_policy_shape_mismatches` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    risk_class = str(row.get("risk_class") or "")
    shape = EXPECTED_ACTION_POLICY_SHAPES.get(risk_class)
    if not shape:
        return []
    mismatches: list[str] = []
    checks = (
        ("action_kind", "action_kinds"),
        ("requested_capability", "requested_capabilities"),
        ("source_trust_label", "source_trust_labels"),
    )
    for field, shape_key in checks:
        allowed = shape.get(shape_key, set())
        if allowed and str(row.get(field) or "") not in allowed:
            mismatches.append(field)
    return mismatches


def _derived_sandbox_policy_verdict(row: dict[str, Any]) -> tuple[str, str]:
    """
    [ACTION]
    - Teleology: Implements `_derived_sandbox_policy_verdict` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    risk_class = str(row.get("risk_class") or "")
    if risk_class in EXPECTED_ACTION_POLICY and not _policy_shape_mismatches(row):
        return EXPECTED_ACTION_POLICY[risk_class]
    return FAIL_CLOSED_POLICY_SEMANTICS


def _expected_action_policy(row: dict[str, Any]) -> tuple[str, str]:
    """
    [ACTION]
    - Teleology: Implements `_expected_action_policy` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _derived_sandbox_policy_verdict(row)


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_projection_protocol` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    target_refs = _strings(protocol.get("target_refs"))
    target_symbols = _strings(protocol.get("target_symbols"))
    public_runtime_refs = _strings(protocol.get("public_runtime_refs"))
    omitted = _strings(protocol.get("omitted_secret_or_live_access_material"))
    source_open_body_import_refs = _strings(
        protocol.get("source_open_body_import_refs")
    )
    body_import = protocol.get("body_import_verification", {})
    if not isinstance(body_import, dict):
        body_import = {}
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 4
        or "agent_sandbox_policy_escape_replay_compound" not in source_pattern_ids
        or len(projection_receipts) < 2
        or "system/lib/agent_execution_trace.py" not in source_refs
        or "codex/standards/std_agent_execution_trace.json" not in source_refs
        or "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py"
        not in target_refs
        or len(public_runtime_refs) < 1
        or len(source_open_body_import_refs) < 3
        or len(omitted) < 6
        or not any(ref.endswith("build_public_sandbox_policy_trace") for ref in target_symbols)
        or protocol.get("body_import_status") != BODY_IMPORT_STATUS
        or body_import.get("verification_mode") != BODY_IMPORT_CLASSIFICATION
        or body_import.get("verification_status") != "verified"
        or body_import.get("body_import_classification") != BODY_IMPORT_CLASSIFICATION
        or protocol.get("body_in_receipt") is not False
    ):
        findings.append(
            _finding(
                "SANDBOX_POLICY_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Projection protocol must cite trace source refs, target refs, runtime refs, body-import verification, and omitted secret/live-access material.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    for flag in (
        "copied_credential_or_account_bound_source",
        "exports_secret_or_live_access_material",
        "exports_executable_payloads",
        "authorizes_live_network",
        "authorizes_sandbox_escape",
    ):
        if protocol.get(flag) is not False:
            findings.append(
                _finding(
                    "SANDBOX_POLICY_PROJECTION_PROTOCOL_AUTHORITY_OVERCLAIM",
                    "Projection protocol must explicitly deny credential/account-bound copy, secret/live-access export, executable payloads, live network, and sandbox escape authority.",
                    case_id="projection_protocol_floor",
                    subject_id=flag,
                    subject_kind="projection_protocol",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "target_refs": target_refs,
        "target_symbols": target_symbols,
        "public_runtime_refs": public_runtime_refs,
        "source_open_body_import_refs": source_open_body_import_refs,
        "body_import_status": protocol.get("body_import_status"),
        "body_import_verification": body_import if isinstance(body_import, dict) else {},
        "omitted_secret_or_live_access_material": omitted,
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_sandbox_policy(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_sandbox_policy` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    policy = payload if isinstance(payload, dict) else {}
    allowed = set(_strings(policy.get("allowed_verdicts")))
    required_action = set(_strings(policy.get("required_action_fields")))
    required_verdict = set(_strings(policy.get("required_verdict_fields")))
    required_effect = set(_strings(policy.get("required_effect_fields")))
    findings: list[dict[str, Any]] = []
    if not {"allow", "warn", "block", "review"}.issubset(allowed):
        findings.append(
            _finding(
                "SANDBOX_POLICY_VERDICTS_INCOMPLETE",
                "Sandbox policy must define allow, warn, block, and review verdicts.",
                case_id="sandbox_policy_floor",
                subject_id=str(policy.get("policy_id") or "sandbox_policy"),
                subject_kind="sandbox_policy",
            )
        )
    floors = (
        (REQUIRED_ACTION_FIELDS, required_action, "action"),
        (REQUIRED_VERDICT_FIELDS, required_verdict, "verdict"),
        (REQUIRED_EFFECT_FIELDS, required_effect, "effect"),
    )
    for expected, actual, label in floors:
        if not set(expected).issubset(actual):
            findings.append(
                _finding(
                    "SANDBOX_POLICY_REQUIRED_FIELDS_INCOMPLETE",
                    f"Sandbox policy must require complete {label} evidence fields.",
                    case_id="sandbox_policy_floor",
                    subject_id=label,
                    subject_kind="sandbox_policy",
                )
            )
    for field in (
        "live_secret_handling_authorized",
        "live_network_access_authorized",
        "host_filesystem_mutation_authorized",
        "tool_output_expands_authority",
        "executable_payload_export_authorized",
        "security_benchmark_claim_authorized",
        "provider_calls_authorized",
        "release_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _finding(
                    "SANDBOX_POLICY_AUTHORITY_OVERCLAIM",
                    "Sandbox policy cannot authorize secrets, live network, host mutation, tool-output authority expansion, executable payload export, benchmark claims, providers, or release.",
                    case_id="sandbox_policy_floor",
                    subject_id=field,
                    subject_kind="sandbox_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "allowed_verdicts": sorted(allowed),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_action_requests(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_action_requests` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(payload, "action_requests")
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    for row in rows:
        request_id = str(row.get("request_id") or "")
        shape_mismatches = _policy_shape_mismatches(row)
        if (
            _missing(row, REQUIRED_ACTION_FIELDS)
            or _has_forbidden_key(row)
            or row.get("body_redacted") is not True
            or row.get("secret_like_data_synthetic") is not True
            or row.get("raw_payload_exported") is not False
            or row.get("live_network_target") is not False
        ):
            findings.append(
                _finding(
                    "SANDBOX_POLICY_ACTION_REQUEST_INVALID",
                    "Action requests require public refs, synthetic secret labels, no live network target, no raw payload export, and no private bodies.",
                    case_id="action_request_floor",
                    subject_id=request_id or "action_request",
                    subject_kind="action_request",
                )
            )
        if shape_mismatches:
            findings.append(
                {
                    **_finding(
                        "SANDBOX_POLICY_ACTION_POLICY_SHAPE_MISMATCH",
                        "Action request risk class must match the action kind, requested capability, and trust-shape policy derivation inputs.",
                        case_id="action_request_floor",
                        subject_id=request_id or "action_request",
                        subject_kind="action_request",
                    ),
                    "mismatched_fields": shape_mismatches,
                }
            )
        exported.append(
            {
                "request_id": request_id,
                "episode_id": row.get("episode_id"),
                "action_kind": row.get("action_kind"),
                "source_trust_label": row.get("source_trust_label"),
                "requested_capability": row.get("requested_capability"),
                "risk_class": row.get("risk_class"),
                "intended_side_effect_ref": row.get("intended_side_effect_ref"),
                "policy_shape_passed": not shape_mismatches,
                "body_in_receipt": False,
            }
        )
    risk_classes = sorted({str(row.get("risk_class")) for row in exported if row.get("risk_class")})
    return {
        "status": PASS if rows and len(risk_classes) >= 4 and not findings else "blocked",
        "action_request_count": len(rows),
        "risk_classes": risk_classes,
        "request_rows": sorted(exported, key=lambda row: row["request_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_policy_verdicts(
    payload: object,
    policy: object,
    request_ids: set[str],
    actions_by_request: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_policy_verdicts` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(payload, "policy_verdicts")
    policy_rows = policy if isinstance(policy, dict) else {}
    allowed = set(_strings(policy_rows.get("allowed_verdicts")))
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    derived_rows: list[dict[str, Any]] = []
    seen_request_ids: set[str] = set()
    for row in rows:
        request_id = str(row.get("request_id") or "")
        seen_request_ids.add(request_id)
        verdict = str(row.get("verdict") or "")
        derived_verdict, derived_rule_ref = _derived_sandbox_policy_verdict(
            actions_by_request.get(request_id, {})
        )
        declared_rule_refs = _strings(row.get("rule_refs"))
        policy_derivation_passed = (
            request_id in actions_by_request
            and verdict == derived_verdict
            and derived_rule_ref in declared_rule_refs
        )
        if (
            _missing(row, REQUIRED_VERDICT_FIELDS)
            or _has_forbidden_key(row)
            or request_id not in request_ids
            or verdict not in allowed
            or row.get("pre_execution") is not True
            or row.get("body_redacted") is not True
            or not declared_rule_refs
        ):
            findings.append(
                _finding(
                    "SANDBOX_POLICY_VERDICT_INVALID",
                    "Policy verdicts must join to requests, precede execution, cite rules, stay redacted, and use an allowed verdict.",
                    case_id="policy_verdict_floor",
                    subject_id=request_id or "policy_verdict",
                    subject_kind="policy_verdict",
                )
            )
        if request_id in actions_by_request and not policy_derivation_passed:
            findings.append(
                _finding(
                    "SANDBOX_POLICY_VERDICT_SEMANTIC_MISMATCH",
                    "Policy verdicts must match the derived request action/risk semantics and cite the matching policy rule.",
                    case_id="policy_verdict_floor",
                    subject_id=request_id,
                    subject_kind="policy_verdict",
                )
            )
        derived_rows.append(
            {
                "request_id": request_id,
                "action_kind": actions_by_request.get(request_id, {}).get("action_kind"),
                "requested_capability": actions_by_request.get(request_id, {}).get(
                    "requested_capability"
                ),
                "risk_class": actions_by_request.get(request_id, {}).get("risk_class"),
                "derived_policy_verdict": derived_verdict,
                "derived_rule_ref": derived_rule_ref,
                "declared_policy_verdict": verdict,
                "declared_rule_refs": declared_rule_refs,
                "policy_derivation_passed": policy_derivation_passed,
                "body_in_receipt": False,
            }
        )
        exported.append(
            {
                "request_id": request_id,
                "policy_version": row.get("policy_version"),
                "verdict": verdict,
                "rule_refs": declared_rule_refs,
                "derived_policy_verdict": derived_verdict,
                "derived_rule_ref": derived_rule_ref,
                "policy_derivation_passed": policy_derivation_passed,
                "pre_execution": row.get("pre_execution"),
                "approval_ref": row.get("approval_ref"),
                "decision_reason_ref": row.get("decision_reason_ref"),
                "body_in_receipt": False,
            }
        )
    for request_id in sorted(request_ids - seen_request_ids):
        derived_verdict, derived_rule_ref = _derived_sandbox_policy_verdict(
            actions_by_request.get(request_id, {})
        )
        findings.append(
            _finding(
                "SANDBOX_POLICY_VERDICT_MISSING",
                "Every action request must have a policy verdict row before execution.",
                case_id="policy_verdict_floor",
                subject_id=request_id,
                subject_kind="policy_verdict",
            )
        )
        derived_rows.append(
            {
                "request_id": request_id,
                "action_kind": actions_by_request.get(request_id, {}).get("action_kind"),
                "requested_capability": actions_by_request.get(request_id, {}).get(
                    "requested_capability"
                ),
                "risk_class": actions_by_request.get(request_id, {}).get("risk_class"),
                "derived_policy_verdict": derived_verdict,
                "derived_rule_ref": derived_rule_ref,
                "declared_policy_verdict": "",
                "declared_rule_refs": [],
                "policy_derivation_passed": False,
                "body_in_receipt": False,
            }
        )
    verdicts = {row["verdict"] for row in exported}
    derived_verdicts = {row["derived_policy_verdict"] for row in derived_rows}
    return {
        "status": PASS if rows and {"allow", "block", "review"}.issubset(verdicts) and not findings else "blocked",
        "policy_verdict_count": len(rows),
        "allow_count": sum(1 for row in exported if row["verdict"] == "allow"),
        "block_count": sum(1 for row in exported if row["verdict"] == "block"),
        "review_count": sum(1 for row in exported if row["verdict"] == "review"),
        "derived_policy_verdict_count": len(derived_rows),
        "derived_allow_count": sum(
            1 for row in derived_rows if row["derived_policy_verdict"] == "allow"
        ),
        "derived_block_count": sum(
            1 for row in derived_rows if row["derived_policy_verdict"] == "block"
        ),
        "derived_review_count": sum(
            1 for row in derived_rows if row["derived_policy_verdict"] == "review"
        ),
        "derived_policy_verdict_mismatch_count": sum(
            1 for row in derived_rows if row["policy_derivation_passed"] is not True
        ),
        "derived_policy_verdict_rows": sorted(
            derived_rows,
            key=lambda row: row["request_id"],
        ),
        "derived_policy_verdicts": sorted(derived_verdicts),
        "policy_verdict_rows": sorted(exported, key=lambda row: row["request_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_side_effect_receipts(
    payload: object,
    request_ids: set[str],
    verdicts_by_request: dict[str, str],
    expected_verdicts_by_request: dict[str, str],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_side_effect_receipts` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(payload, "side_effect_receipts")
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    for row in rows:
        request_id = str(row.get("request_id") or "")
        verdict = verdicts_by_request.get(request_id, "")
        expected_verdict = expected_verdicts_by_request.get(request_id, "")
        diff_count = row.get("side_effect_diff_count")
        execution_attempted = row.get("execution_attempted")
        if (
            _missing(row, REQUIRED_EFFECT_FIELDS)
            or _has_forbidden_key(row)
            or request_id not in request_ids
            or row.get("body_redacted") is not True
            or not isinstance(diff_count, int)
        ):
            findings.append(
                _finding(
                    "SANDBOX_POLICY_SIDE_EFFECT_RECEIPT_INVALID",
                    "Side-effect receipts must join to requests and expose only diff/rollback refs.",
                    case_id="side_effect_receipt_floor",
                    subject_id=request_id or "side_effect_receipt",
                    subject_kind="side_effect_receipt",
                )
            )
        if expected_verdict == "block" and (
            execution_attempted is not False or diff_count != 0
        ):
            findings.append(
                _finding(
                    "SANDBOX_POLICY_SIDE_EFFECT_SEMANTIC_MISMATCH",
                    "Request semantics that require a block must have no execution and no side-effect diff, independent of the recorded verdict row.",
                    case_id="side_effect_receipt_floor",
                    subject_id=request_id or "side_effect_receipt",
                    subject_kind="side_effect_receipt",
                )
            )
        if expected_verdict in {"allow", "review"} and (
            execution_attempted is not True or diff_count < 1
        ):
            findings.append(
                _finding(
                    "SANDBOX_POLICY_SIDE_EFFECT_SEMANTIC_MISMATCH",
                    "Request semantics that allow or require review must carry an executed side-effect diff receipt.",
                    case_id="side_effect_receipt_floor",
                    subject_id=request_id or "side_effect_receipt",
                    subject_kind="side_effect_receipt",
                )
            )
        if verdict == "block" and (execution_attempted is not False or diff_count != 0):
            findings.append(
                _finding(
                    "SANDBOX_POLICY_BLOCKED_ACTION_EXECUTED",
                    "Blocked sandbox actions must have no execution and no side-effect diff.",
                    case_id="side_effect_receipt_floor",
                    subject_id=request_id or "side_effect_receipt",
                    subject_kind="side_effect_receipt",
                )
            )
        if verdict in {"allow", "review"} and (execution_attempted is not True or diff_count < 1):
            findings.append(
                _finding(
                    "SANDBOX_POLICY_ALLOWED_ACTION_MISSING_DIFF",
                    "Allowed or reviewed sandbox actions must carry a non-empty diff receipt.",
                    case_id="side_effect_receipt_floor",
                    subject_id=request_id or "side_effect_receipt",
                    subject_kind="side_effect_receipt",
                )
            )
        exported.append(
            {
                "request_id": request_id,
                "declared_verdict": verdict,
                "expected_verdict": expected_verdict,
                "verdict": expected_verdict,
                "execution_attempted": execution_attempted,
                "filesystem_diff_ref": row.get("filesystem_diff_ref"),
                "network_diff_ref": row.get("network_diff_ref"),
                "database_diff_ref": row.get("database_diff_ref"),
                "side_effect_diff_count": diff_count,
                "rollback_receipt_ref": row.get("rollback_receipt_ref"),
                "body_in_receipt": False,
            }
        )
    return {
        "status": PASS if rows and not findings else "blocked",
        "side_effect_receipt_count": len(rows),
        "executed_action_count": sum(1 for row in exported if row["execution_attempted"] is True),
        "blocked_without_execution_count": sum(
            1 for row in exported if row["expected_verdict"] == "block" and row["execution_attempted"] is False
        ),
        "side_effect_rows": sorted(exported, key=lambda row: row["request_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_rollback_receipts(payload: object, request_ids: set[str]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_rollback_receipts` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(payload, "rollback_receipts")
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    for row in rows:
        rollback_id = str(row.get("rollback_id") or "")
        request_id = str(row.get("request_id") or "")
        if (
            not rollback_id
            or request_id not in request_ids
            or row.get("rollback_required") is not True
            or row.get("rollback_verified") is not True
            or row.get("body_redacted") is not True
            or not row.get("rollback_command_ref")
            or _has_forbidden_key(row)
        ):
            findings.append(
                _finding(
                    "SANDBOX_POLICY_ROLLBACK_RECEIPT_INVALID",
                    "Rollback receipts must be redacted refs that verify rollback for side-effecting actions.",
                    case_id="rollback_receipt_floor",
                    subject_id=rollback_id or "rollback_receipt",
                    subject_kind="rollback_receipt",
                )
            )
        exported.append(
            {
                "rollback_id": rollback_id,
                "request_id": request_id,
                "rollback_required": row.get("rollback_required"),
                "rollback_command_ref": row.get("rollback_command_ref"),
                "rollback_verified": row.get("rollback_verified"),
                "body_in_receipt": False,
            }
        )
    return {
        "status": PASS if len(rows) >= 2 and not findings else "blocked",
        "rollback_receipt_count": len(rows),
        "rollback_verified_count": sum(1 for row in exported if row["rollback_verified"] is True),
        "rollback_rows": sorted(exported, key=lambda row: row["rollback_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_cold_replay(payload: object, request_ids: set[str]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_cold_replay` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(payload, "cold_replay")
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    for row in rows:
        replay_id = str(row.get("replay_id") or "")
        request_id = str(row.get("request_id") or "")
        if (
            not replay_id
            or request_id not in request_ids
            or not row.get("replay_command")
            or not row.get("receipt_ref")
            or row.get("verdict_reproduced") is not True
            or row.get("side_effect_state_reproduced") is not True
            or row.get("pass_label") is not True
            or row.get("body_redacted") is not True
            or _has_forbidden_key(row)
        ):
            findings.append(
                _finding(
                    "SANDBOX_POLICY_COLD_REPLAY_INVALID",
                    "Cold replay rows require command, receipt ref, reproduced verdict, reproduced side-effect state, pass label, and redacted metadata.",
                    case_id="cold_replay_floor",
                    subject_id=replay_id or "cold_replay",
                    subject_kind="cold_replay",
                )
            )
        exported.append(
            {
                "replay_id": replay_id,
                "request_id": request_id,
                "replay_command": row.get("replay_command"),
                "receipt_ref": row.get("receipt_ref"),
                "verdict_reproduced": row.get("verdict_reproduced"),
                "side_effect_state_reproduced": row.get("side_effect_state_reproduced"),
                "pass_label": row.get("pass_label"),
                "body_in_receipt": False,
            }
        )
    return {
        "status": PASS if rows and not findings else "blocked",
        "cold_replay_count": len(rows),
        "cold_replay_pass_count": sum(1 for row in exported if row["pass_label"] is True),
        "cold_replay_rows": sorted(exported, key=lambda row: row["replay_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_negative_cases(negative_payloads: dict[str, object]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_negative_cases` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for case_id, payload in negative_payloads.items():
        row = payload if isinstance(payload, dict) else {}
        subject_id = str(row.get("case_id") or case_id)
        subject_kind = "negative_case"
        if row.get("real_secret_material_included") is True:
            _record(
                findings,
                observed,
                "SANDBOX_POLICY_REAL_SECRET_FORBIDDEN",
                "Public sandbox fixtures cannot include real secrets or credentials.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("live_network_access_requested") is True:
            _record(
                findings,
                observed,
                "SANDBOX_POLICY_LIVE_NETWORK_FORBIDDEN",
                "Public sandbox replay cannot request live network access.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("raw_environment_export_requested") is True:
            _record(
                findings,
                observed,
                "SANDBOX_POLICY_RAW_ENV_EXPORT_FORBIDDEN",
                "Public sandbox replay cannot export raw environment or process state.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("policy_evaluated_after_execution") is True:
            _record(
                findings,
                observed,
                "SANDBOX_POLICY_AFTER_EXECUTION",
                "Sandbox policy verdicts must be recorded before execution.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("side_effect_without_diff_receipt") is True:
            _record(
                findings,
                observed,
                "SANDBOX_POLICY_UNLOGGED_SIDE_EFFECT",
                "Any allowed side effect requires a diff and rollback receipt.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("tool_output_expands_authority") is True:
            _record(
                findings,
                observed,
                "SANDBOX_POLICY_TOOL_OUTPUT_AUTHORITY_BYPASS",
                "Untrusted tool output cannot expand sandbox authority or policy scope.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("executable_escape_payload_included") is True:
            _record(
                findings,
                observed,
                "SANDBOX_POLICY_EXECUTABLE_PAYLOAD_FORBIDDEN",
                "Public replay may name an escape-risk class but cannot include executable payloads.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        if row.get("security_benchmark_claim_made") is True:
            _record(
                findings,
                observed,
                "SANDBOX_POLICY_SECURITY_BENCHMARK_CLAIM",
                "Synthetic replay receipts cannot claim security benchmark performance.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
    return {
        "status": PASS,
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
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
    - Teleology: Implements `_build_result` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _scan_paths_for_input(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    public_trace = build_public_sandbox_policy_trace(input_dir)

    projection = validate_projection_protocol(payloads["projection_protocol"])
    sandbox_policy = validate_sandbox_policy(payloads["sandbox_policy"])
    actions = validate_action_requests(payloads["action_requests"])
    request_ids = {row["request_id"] for row in actions["request_rows"]}
    actions_by_request = {
        str(row["request_id"]): row
        for row in actions["request_rows"]
        if row.get("request_id")
    }
    verdicts = validate_policy_verdicts(
        payloads["policy_verdicts"],
        payloads["sandbox_policy"],
        request_ids,
        actions_by_request,
    )
    expected_verdicts_by_request = {
        str(row["request_id"]): str(row["derived_policy_verdict"])
        for row in verdicts["derived_policy_verdict_rows"]
        if row.get("request_id")
    }
    verdicts_by_request = {
        str(row["request_id"]): str(row["verdict"])
        for row in verdicts["policy_verdict_rows"]
    }
    effects = validate_side_effect_receipts(
        payloads["side_effect_receipts"],
        request_ids,
        verdicts_by_request,
        expected_verdicts_by_request,
    )
    rollbacks = validate_rollback_receipts(payloads["rollback_receipts"], request_ids)
    cold_replay = validate_cold_replay(payloads["cold_replay"], request_ids)
    negative_payloads = {
        name: payloads[name]
        for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
        if name in payloads
    }
    negatives = validate_negative_cases(negative_payloads)
    source_modules = _source_module_manifest_result(
        input_dir,
        public_root=public_root,
        require_manifest=input_mode == "exported_sandbox_policy_escape_bundle",
    )
    source_open_body_imports = _source_open_body_import_summary(source_modules)
    observed = _merge_observed(
        projection,
        sandbox_policy,
        actions,
        verdicts,
        effects,
        rollbacks,
        cold_replay,
        negatives,
        source_modules,
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        projection,
        sandbox_policy,
        actions,
        verdicts,
        effects,
        rollbacks,
        cold_replay,
        negatives,
        source_modules,
    )
    positive_findings = _merge_findings(
        projection,
        sandbox_policy,
        actions,
        verdicts,
        effects,
        rollbacks,
        cold_replay,
        source_modules,
    )
    positive_statuses = (
        projection["status"],
        sandbox_policy["status"],
        actions["status"],
        verdicts["status"],
        effects["status"],
        rollbacks["status"],
        cold_replay["status"],
        public_trace["status"],
    )
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and all(value == PASS for value in positive_statuses)
        and not positive_findings
        and (
            input_mode != "exported_sandbox_policy_escape_bundle"
            or source_modules["status"] == PASS
        )
        else "blocked"
    )
    body_import_verification = {
        "status": PASS,
        "classification": BODY_IMPORT_CLASSIFICATION,
        "verification_status": "verified",
        "verification_mode": BODY_IMPORT_CLASSIFICATION,
        "body_import_classification": BODY_IMPORT_CLASSIFICATION,
        "public_trace_status": public_trace["status"],
        "public_trace_span_count": public_trace["span_count"],
        "trace_digest": public_trace["summary"]["trace_digest"],
        "source_ref": "system/lib/agent_execution_trace.py",
        "target_ref": (
            "microcosm-substrate/src/microcosm_core/macro_tools/"
            "agent_execution_trace.py::build_public_sandbox_policy_trace"
        ),
        "source_symbols": public_trace["source_symbols"],
        "target_symbols": public_trace["target_symbols"],
        "validation_refs": [
            "microcosm-substrate/tests/test_agent_sandbox_policy_escape_replay.py",
            (
                "python -m microcosm_core.macro_tools.agent_execution_trace "
                "sandbox-policy --input <bundle>"
            ),
        ],
        "body_in_receipt": False,
    }
    return {
        "schema_version": "agent_sandbox_policy_escape_replay_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id") if isinstance(bundle_manifest, dict) else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_classification": BODY_IMPORT_CLASSIFICATION,
        "product_path_role": PRODUCT_PATH_ROLE,
        "body_import_verification": body_import_verification,
        "body_in_receipt": False,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "target_refs": projection["target_refs"],
        "target_symbols": projection["target_symbols"],
        "public_runtime_refs": projection["public_runtime_refs"],
        "source_open_body_import_refs": projection["source_open_body_import_refs"],
        "source_module_manifest_status": source_modules["status"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_imports": source_modules,
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports[
            "body_material_count"
        ],
        "omitted_secret_or_live_access_material": projection[
            "omitted_secret_or_live_access_material"
        ],
        "public_agent_execution_trace": public_trace,
        "sandbox_policy_id": sandbox_policy["policy_id"],
        "allowed_verdicts": sandbox_policy["allowed_verdicts"],
        "action_request_count": actions["action_request_count"],
        "risk_classes": actions["risk_classes"],
        "policy_verdict_count": verdicts["policy_verdict_count"],
        "allow_count": verdicts["allow_count"],
        "block_count": verdicts["block_count"],
        "review_count": verdicts["review_count"],
        "derived_policy_verdict_count": verdicts["derived_policy_verdict_count"],
        "derived_allow_count": verdicts["derived_allow_count"],
        "derived_block_count": verdicts["derived_block_count"],
        "derived_review_count": verdicts["derived_review_count"],
        "derived_policy_verdict_mismatch_count": verdicts[
            "derived_policy_verdict_mismatch_count"
        ],
        "derived_policy_verdicts": verdicts["derived_policy_verdicts"],
        "side_effect_receipt_count": effects["side_effect_receipt_count"],
        "executed_action_count": effects["executed_action_count"],
        "blocked_without_execution_count": effects["blocked_without_execution_count"],
        "rollback_receipt_count": rollbacks["rollback_receipt_count"],
        "rollback_verified_count": rollbacks["rollback_verified_count"],
        "cold_replay_count": cold_replay["cold_replay_count"],
        "cold_replay_pass_count": cold_replay["cold_replay_pass_count"],
        "request_rows": actions["request_rows"],
        "policy_verdict_rows": verdicts["policy_verdict_rows"],
        "derived_policy_verdict_rows": verdicts["derived_policy_verdict_rows"],
        "side_effect_rows": effects["side_effect_rows"],
        "rollback_rows": rollbacks["rollback_rows"],
        "cold_replay_rows": cold_replay["cold_replay_rows"],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_board_from_result` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "agent_sandbox_policy_escape_replay_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "agent_sandbox_policy_escape_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "policy_precedes_execution",
                "count": result["policy_verdict_count"],
                "authority": "every action request must have a pre-execution verdict",
            },
            {
                "mechanic_id": "derived_policy_verdicts",
                "count": result["derived_policy_verdict_count"],
                "authority": "sandbox verdicts are derived from action kind, risk class, capability, and trust shape before recorded verdict rows are accepted",
            },
            {
                "mechanic_id": "blocked_actions_have_zero_side_effects",
                "count": result["blocked_without_execution_count"],
                "authority": "derived blocked secret/network/destructive requests cannot execute",
            },
            {
                "mechanic_id": "side_effects_need_rollback_receipts",
                "count": result["rollback_verified_count"],
                "authority": "allowed side effects require rollback evidence",
            },
            {
                "mechanic_id": "negative_cases_are_admission_boundary",
                "count": len(result["observed_negative_cases"]),
                "authority": "live secrets, network, raw env, payloads, bypasses, and benchmark claims are rejected",
            },
        ],
        "request_rows": result["request_rows"],
        "policy_verdict_rows": result["policy_verdict_rows"],
        "derived_policy_verdict_rows": result["derived_policy_verdict_rows"],
        "side_effect_rows": result["side_effect_rows"],
        "rollback_rows": result["rollback_rows"],
        "cold_replay_rows": result["cold_replay_rows"],
        "body_in_receipt": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "body_import_status": result["body_import_status"],
        "body_import_classification": result["body_import_classification"],
        "product_path_role": result["product_path_role"],
        "body_import_verification": result["body_import_verification"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_write_receipts` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
    acceptance_path = (
        acceptance_out
        if acceptance_out is not None
        else public_root / ACCEPTANCE_RECEIPT_REL
    )
    acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
        _display(acceptance_path, public_root=public_root),
    ]
    result_receipt = {
        **result,
        "schema_version": "agent_sandbox_policy_escape_replay_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "agent_sandbox_policy_escape_replay_validation_receipt_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "negative_case_coverage": {
            "expected": result["expected_negative_cases"],
            "observed": result["observed_negative_cases"],
            "missing": result["missing_negative_cases"],
        },
        "action_request_count": result["action_request_count"],
        "policy_verdict_count": result["policy_verdict_count"],
        "side_effect_receipt_count": result["side_effect_receipt_count"],
        "blocked_without_execution_count": result["blocked_without_execution_count"],
        "rollback_verified_count": result["rollback_verified_count"],
        "cold_replay_pass_count": result["cold_replay_pass_count"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "body_import_status": result["body_import_status"],
        "body_import_classification": result["body_import_classification"],
        "body_import_verification": result["body_import_verification"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_in_receipt": False,
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "agent_sandbox_policy_escape_replay_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "body_import_status": result["body_import_status"],
        "body_import_classification": result["body_import_classification"],
        "body_import_verification": result["body_import_verification"],
        "source_module_manifest_status": result["source_module_manifest_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "body_copied_material_count": result["body_copied_material_count"],
        "body_in_receipt": False,
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "sandbox_policy_escape_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.agent_sandbox_policy_escape_replay run",
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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


def run_sandbox_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.agent_sandbox_policy_escape_replay "
        "run-sandbox-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_sandbox_bundle` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(input_dir)
    if reuse_fresh_receipt:
        cached = _fresh_bundle_receipt(source, out)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_sandbox_policy_escape_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_sandbox_policy_escape_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def _card_receipt_paths(paths: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_card_receipt_paths` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
        return []
    normalized = normalize_public_receipt_paths({"receipt_paths": paths})
    values = normalized.get("receipt_paths") if isinstance(normalized, dict) else paths
    if isinstance(values, list) and all(isinstance(path, str) for path in values):
        return values
    return paths


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
    - Writes: return values.
    """
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    trace = result.get("public_agent_execution_trace")
    trace_summary = trace.get("summary", {}) if isinstance(trace, dict) else {}
    body_verification = result.get("body_import_verification")
    source_body_floor = result.get("source_open_body_imports")
    source_body_floor = source_body_floor if isinstance(source_body_floor, dict) else {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": freshness.get("basis_digest"),
            "freshness_input_count": freshness.get("input_count"),
            "freshness_missing_path_count": freshness.get("missing_path_count"),
        },
        "sandbox_policy": {
            "action_request_count": result.get("action_request_count"),
            "policy_verdict_count": result.get("policy_verdict_count"),
            "allow_count": result.get("allow_count"),
            "block_count": result.get("block_count"),
            "review_count": result.get("review_count"),
            "derived_allow_count": result.get("derived_allow_count"),
            "derived_block_count": result.get("derived_block_count"),
            "derived_review_count": result.get("derived_review_count"),
            "derived_policy_verdict_mismatch_count": result.get(
                "derived_policy_verdict_mismatch_count"
            ),
            "side_effect_receipt_count": result.get("side_effect_receipt_count"),
            "blocked_without_execution_count": result.get(
                "blocked_without_execution_count"
            ),
            "rollback_verified_count": result.get("rollback_verified_count"),
            "cold_replay_pass_count": result.get("cold_replay_pass_count"),
        },
        "validation": {
            "expected_negative_case_count": len(
                result.get("expected_negative_cases") or []
            ),
            "missing_negative_case_count": len(
                result.get("missing_negative_cases") or []
            ),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
            "public_agent_execution_trace_status": (
                trace.get("status") if isinstance(trace, dict) else None
            ),
            "public_agent_execution_trace_span_count": (
                trace.get("span_count") if isinstance(trace, dict) else None
            ),
            "trace_outcome_counts": trace_summary.get("outcome_counts"),
            "source_module_manifest_status": result.get(
                "source_module_manifest_status"
            ),
            "source_module_manifest_ref": result.get("source_module_manifest_ref"),
            "body_material_count": source_body_floor.get("body_material_count", 0),
            "body_material_status": source_body_floor.get("body_material_status", ""),
        },
        "body_floor": {
            "body_import_status": result.get("body_import_status"),
            "body_import_classification": result.get("body_import_classification"),
            "body_import_verification_mode": (
                body_verification.get("verification_mode")
                if isinstance(body_verification, dict)
                else None
            ),
            "body_in_receipt": result.get("body_in_receipt") is True,
            "source_module_imports_in_card": False,
            "source_open_body_imports_in_card": False,
        },
        "authority_boundary": {
            "live_agent_execution_authorized": False,
            "live_sandbox_escape_authorized": False,
            "live_secret_or_credential_handling_authorized": False,
            "live_network_access_authorized": False,
            "host_filesystem_mutation_authorized": False,
            "executable_escape_payload_export_authorized": False,
            "raw_environment_export_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
        },
        "receipt_paths": _card_receipt_paths(result.get("receipt_paths", [])),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": "rerun without --card or inspect the written receipt file",
        },
    }


def _parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `_parser` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog="agent_sandbox_policy_escape_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-sandbox-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.agent_sandbox_policy_escape_replay` while keeping the callable contract visible to source-module readers.
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
            "python -m microcosm_core.organs.agent_sandbox_policy_escape_replay "
            f"run --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-sandbox-bundle":
        command = (
            "python -m microcosm_core.organs.agent_sandbox_policy_escape_replay "
            f"run-sandbox-bundle --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run_sandbox_bundle(
            args.input,
            args.out,
            command=command,
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
