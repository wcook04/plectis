"""
Public organ: lease-aware tool-server / helper-process pressure inventory.

Source-faithful public refactor of the read-only surface of the macro
`tools/meta/control/orphan_reaper.py`. The macro mechanism walks the live OS
process table, classifies tool-server helper processes (MCP servers, dev
servers, keepalives) by kind, reconstructs each process's owner chain up to 8
levels to tell a launchd-detached ORPHAN (ppid==1) apart from a live agent
session descendant, and emits a typed pressure inventory plus an owner-release
request for over-budget *active* owners.

This public organ keeps the classifier + owner-chain + safety predicate and
DROPS everything that cannot cross the public boundary:

- NO process signalling. There is no `os.kill`, no `SIGTERM`/`SIGKILL`, no
  launchd job. The organ is a read-only validator; the central public claim is
  that an active-owner descendant is NEVER a kill candidate.
- NO live `ps`. Input is injected synthetic `ps_text` from public fixtures.
- NO absolute paths or live command previews. Rows carry a `command_hash`
  only; the private path regexes of the macro become injected synthetic policy
  (`pressure_policy.json`) and owner taxonomy (`owner_classes.json`).

Redaction is a first-class acceptance condition: `_redaction_findings` rejects
any fixture/row that smuggles an absolute path, a `command_preview`-style live
command body, or a process-signal claim through the public surface.

Authority ceiling: projection/validation only. It does not signal processes,
mutate host state, authorize release, call providers, or claim whole-system
correctness.

[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.tool_server_pressure_inventory` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, RESULT_NAME, BOARD_NAME, VALIDATION_RECEIPT_NAME, BUNDLE_RESULT_NAME, INVENTORY_SCHEMA, RELIEF_RECEIPT_SCHEMA, HELPER_OWNER_RELEASE_REQUEST_SCHEMA, CARD_SCHEMA_VERSION, CARD_OMITTED_FULL_PAYLOAD_KEYS, SOURCE_PATTERN_IDS, SOURCE_REFS, PUBLIC_RUNTIME_REFS, INPUT_NAMES, SOURCE_MODULE_MANIFEST_NAME, SOURCE_IMPORT_CLASS, SOURCE_MODULE_IMPORT_STATUS, SOURCE_OPEN_BODY_SCHEMA, PUBLIC_SAFE_SOURCE_BODY_CLASSES, ACCEPTED_SOURCE_RELATIONS, NEGATIVE_INPUT_NAMES, NEGATIVE_INPUT_STEMS, ...
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
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "tool_server_pressure_inventory"
FIXTURE_ID = "first_wave.tool_server_pressure_inventory"
VALIDATOR_ID = "validator.microcosm.organs.tool_server_pressure_inventory"

RESULT_NAME = "tool_server_pressure_inventory_result.json"
BOARD_NAME = "tool_server_pressure_inventory_board.json"
VALIDATION_RECEIPT_NAME = "tool_server_pressure_inventory_validation_receipt.json"
BUNDLE_RESULT_NAME = (
    "exported_tool_server_pressure_inventory_bundle_validation_result.json"
)
INVENTORY_SCHEMA = "tool_server_pressure_inventory_v1"
RELIEF_RECEIPT_SCHEMA = "pressure_hygiene_relief_receipt_v1"
HELPER_OWNER_RELEASE_REQUEST_SCHEMA = "helper_owner_release_request_v1"
CARD_SCHEMA_VERSION = "tool_server_pressure_inventory_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "findings",
    "secret_exclusion_scan",
    "expected_negative_cases",
    "observed_negative_cases",
    "inventory_projection",
    "source_refs",
    "public_runtime_refs",
    "anti_claim",
    "authority_ceiling",
    "source_module_summary",
)

SOURCE_PATTERN_IDS = [
    "tool_server_pressure_inventory",
    "lease_aware_helper_pressure_hygiene",
    "active_owner_release_request",
]
SOURCE_REFS = [
    "tools/meta/control/orphan_reaper.py",
]
PUBLIC_RUNTIME_REFS = [
    "core/standards_registry.json",
    "core/organ_registry.json",
    "core/acceptance/first_wave_acceptance.json",
    "core/preflight_support/organ_fixture_validator_readiness_v1.json",
    "fixtures/first_wave/tool_server_pressure_inventory/input/process_table.json",
    "fixtures/first_wave/tool_server_pressure_inventory/input/pressure_policy.json",
    "fixtures/first_wave/tool_server_pressure_inventory/input/owner_classes.json",
    "examples/tool_server_pressure_inventory/exported_tool_server_pressure_inventory_bundle",
    "paper_modules/tool_server_pressure_inventory.md",
]

INPUT_NAMES = (
    "process_table.json",
    "pressure_policy.json",
    "owner_classes.json",
)
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_MODULE_IMPORT_STATUS = "source_faithful_public_refactor_body_landed"
SOURCE_OPEN_BODY_SCHEMA = "tool_server_pressure_inventory_source_open_body_imports_v1"
PUBLIC_SAFE_SOURCE_BODY_CLASSES = frozenset(
    {
        "public_macro_pattern_body",
        "public_macro_tool_body",
        "public_macro_receipt_body",
        "public_macro_proof_body",
        "public_macro_standard_body",
    }
)
ACCEPTED_SOURCE_RELATIONS = frozenset(
    {
        "exact_copy",
        "verified_public_safe_private_path_rewrite",
        "source_faithful_public_refactor",
    }
)

NEGATIVE_INPUT_NAMES = (
    "active_owner_kill_candidate.json",
    "unknown_owner_kill.json",
    "owner_chain_cycle_safe_close.json",
    "premature_safe_close.json",
    "process_signal_sent.json",
    "command_preview_leak.json",
    "absolute_path_leak.json",
    "owner_release_overclaim.json",
)
NEGATIVE_INPUT_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)

EXPECTED_NEGATIVE_CASES = {
    "active_owner_kill_candidate": ["TSPI_ACTIVE_OWNER_KILL_CANDIDATE"],
    "unknown_owner_kill": ["TSPI_UNKNOWN_OWNER_KILL_FORBIDDEN"],
    "owner_chain_cycle_safe_close": ["TSPI_ACTIVE_OWNER_KILL_CANDIDATE"],
    "premature_safe_close": ["TSPI_PREMATURE_SAFE_CLOSE"],
    "process_signal_sent": ["TSPI_PROCESS_SIGNAL_FORBIDDEN"],
    "command_preview_leak": ["TSPI_COMMAND_PREVIEW_FORBIDDEN"],
    "absolute_path_leak": ["TSPI_ABSOLUTE_PATH_FORBIDDEN"],
    "owner_release_overclaim": ["TSPI_OWNER_RELEASE_OVERCLAIM"],
}

DEFAULT_MIN_AGE_SECONDS = 300
ACTIVE_OWNER_STATUS_VALUES = frozenset(
    {
        "active_session_chain",
        "active_parent_process",
        "active_owner_chain",
    }
)
DETACHED_OWNER_STATUS = "launchd_detached"
SAFE_CLOSE_DECISION = "candidate_safe_close"
OWNER_CHECK_DECISION = "requires_owner_check"
KEEP_DECISION = "keep"

# Redaction guard: these must never appear on the public surface.
ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?:^|[\s\"'=])(?:/Users/|/home/|/Applications/|/private/var/|/var/folders/)"
    r"|[A-Za-z]:\\\\Users\\\\"
)
FORBIDDEN_PREVIEW_KEYS = frozenset(
    {"command_preview", "command_line", "cmdline", "raw_command", "full_command"}
)
FORBIDDEN_SIGNAL_KEYS = frozenset(
    {
        "process_signal_sent",
        "signalled",
        "sigterm_sent",
        "sigkill_sent",
        "killed_pid",
        "kill_signal",
    }
)
FORBIDDEN_OWNER_RELEASE_RESULTS = frozenset(
    {"killed", "terminated", "sigterm", "sigkill", "force_closed"}
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "tool_server_pressure_inventory_projection_only_not_process_control_authority",
    "process_signal_authority": False,
    "live_process_table_read_authorized": False,
    "host_mutation_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
    "provider_calls_authorized": False,
    "private_data_equivalence_claim": False,
    "whole_system_correctness_claim": False,
}

ANTI_CLAIM = (
    "Tool-server pressure inventory validates a public read-only helper-process "
    "pressure contract over synthetic process tables only. It never signals a "
    "process, reads a live process table, mutates host state, or authorizes "
    "release; an active-owner descendant is never a safe-close candidate; "
    "over-budget active owners receive a release REQUEST, not a kill. It does "
    "not prove host correctness, call providers, or claim whole-system "
    "correctness."
)


# --------------------------------------------------------------------------- #
# Shared scaffolding (mirrors the accepted semantic_validator organ shape).
# --------------------------------------------------------------------------- #
def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_display` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_rows` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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


def _strings(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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
    return digest.hexdigest()


def _command_hash(cmd: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_command_hash` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return hashlib.sha256(cmd.encode("utf-8")).hexdigest()[:16]


def _walk_dicts(value: object) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_walk_dicts` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_finding` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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
    - Teleology: Implements `_record` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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


# --------------------------------------------------------------------------- #
# The redacted, actuatorless mechanism (port of orphan_reaper read-only path).
# --------------------------------------------------------------------------- #
def _parse_etime_to_seconds(etime: str) -> int:
    """
    [ACTION]
    - Teleology: Implements `_parse_etime_to_seconds` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    parts = etime.strip().split("-")
    days = 0
    rest = parts[0]
    if len(parts) == 2:
        days = int(parts[0])
        rest = parts[1]
    h, m, s = 0, 0, 0
    segments = rest.split(":")
    if len(segments) == 3:
        h, m, s = int(segments[0]), int(segments[1]), int(segments[2])
    elif len(segments) == 2:
        m, s = int(segments[0]), int(segments[1])
    else:
        s = int(segments[0])
    return days * 86400 + h * 3600 + m * 60 + s


def _parse_int(value: str) -> int | None:
    """
    [ACTION]
    - Teleology: Implements `_parse_int` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_float(value: str) -> float | None:
    """
    [ACTION]
    - Teleology: Implements `_parse_float` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_process_rows(ps_text: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_parse_process_rows` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    processes: list[dict[str, Any]] = []
    for line in ps_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            pid_s, ppid_s, etime, cpu_s, rss_s, cmd = line.split(None, 5)
        except ValueError:
            continue
        pid = _parse_int(pid_s)
        ppid = _parse_int(ppid_s)
        if pid is None or ppid is None:
            continue
        try:
            age_s = _parse_etime_to_seconds(etime)
        except ValueError:
            continue
        processes.append(
            {
                "pid": pid,
                "ppid": ppid,
                "age_s": age_s,
                "cpu_s": cpu_s,
                "rss_s": rss_s,
                "cmd": cmd,
            }
        )
    return processes


def _kind_specs(policy: dict[str, Any]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_kind_specs` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _rows(policy, "kinds")


def _process_kind(cmd: str, kind_specs: list[dict[str, Any]]) -> str | None:
    """
    [ACTION]
    - Teleology: Implements `_process_kind` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for spec in kind_specs:
        tokens = _strings(spec.get("match_substrings"))
        if any(token in cmd for token in tokens):
            return str(spec.get("kind") or "") or None
    return None


def _owner_hint_from_command(cmd: str, owner_classes: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `_owner_hint_from_command` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for hint in _rows(owner_classes, "owner_hints"):
        token = str(hint.get("substring") or "")
        if token and token in cmd:
            return str(hint.get("status") or "active_parent_process")
    return "active_parent_process"


def _owner_status_for_process(
    *,
    kind: str,
    ppid: int,
    process_table: dict[int, dict[str, Any]],
    owner_classes: dict[str, Any],
    keep_status_by_kind: dict[str, str],
) -> str:
    """
    [ACTION]
    - Teleology: Implements `_owner_status_for_process` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if kind in keep_status_by_kind:
        return keep_status_by_kind[kind]
    if ppid == 1:
        return DETACHED_OWNER_STATUS
    current = ppid
    seen: set[int] = set()
    last_status = "unknown_parent_process"
    for _depth in range(8):
        if current in seen:
            return last_status
        seen.add(current)
        parent = process_table.get(current)
        if parent is None:
            return last_status
        cmd = str(parent.get("cmd", ""))
        last_status = _owner_hint_from_command(cmd, owner_classes)
        if last_status != "active_parent_process":
            return last_status
        next_ppid = parent.get("ppid")
        if not isinstance(next_ppid, int) or next_ppid == 1:
            return last_status
        current = next_ppid
    return last_status


def _inventory_owner_and_decision(
    *,
    kind: str,
    ppid: int,
    age_s: int,
    allowlist_matched: bool,
    owner_status: str,
    min_age_seconds: int,
    keep_kinds: set[str],
    active_owner_status_values: frozenset[str],
) -> tuple[str, str, str]:
    """
    [ACTION]
    - Teleology: Implements `_inventory_owner_and_decision` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if kind in keep_kinds:
        return owner_status, KEEP_DECISION, "runtime_not_helper_cleanup"
    if ppid == 1 and allowlist_matched and age_s >= min_age_seconds:
        return (
            DETACHED_OWNER_STATUS,
            SAFE_CLOSE_DECISION,
            "strict_orphan_allowlist_age_threshold_met",
        )
    if ppid == 1:
        return (
            DETACHED_OWNER_STATUS,
            OWNER_CHECK_DECISION,
            "detached_process_not_in_safe_close_predicate",
        )
    if owner_status in active_owner_status_values:
        return (
            owner_status,
            OWNER_CHECK_DECISION,
            "active_parent_chain_requires_owner_check",
        )
    return owner_status, OWNER_CHECK_DECISION, "parent_owner_not_resolved"


def _owner_release_target(owner_status: str, owner_classes: dict[str, Any]) -> str | None:
    """
    [ACTION]
    - Teleology: Implements `_owner_release_target` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    targets = owner_classes.get("owner_release_targets")
    if isinstance(targets, dict) and owner_status in targets:
        return str(targets[owner_status])
    return None


def _owner_release_request_for_group(
    group: dict[str, Any], owner_classes: dict[str, Any]
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_owner_release_request_for_group` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    owner_status = str(group.get("owner_status") or "unknown").strip() or "unknown"
    return {
        "schema": HELPER_OWNER_RELEASE_REQUEST_SCHEMA,
        "process_kind": str(group.get("process_kind") or ""),
        "owner_status": owner_status,
        "target_owner": _owner_release_target(owner_status, owner_classes),
        "pressure_mode": "degraded",
        "process_count": int(group.get("count") or 0),
        "excess_count": int(group.get("excess_count") or 0),
        "permitted_action": "ask_owner_to_release",
        "requested_action": "release_tool_lease",
        "result": "requested",
        "owner_release_route": (
            "Owning session must release or reuse its helper lease; the "
            "inventory must not signal active-owner descendants."
        ),
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
            "owner_must_release_own_helper": True,
        },
    }


def _active_owner_pressure_groups(
    rows: list[dict[str, Any]],
    *,
    budget_by_kind: dict[str, int],
    owner_classes: dict[str, Any],
    active_owner_status_values: frozenset[str],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_active_owner_pressure_groups` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        kind = str(row.get("process_kind") or "")
        owner_status = str(row.get("owner_status") or "")
        budget = budget_by_kind.get(kind)
        if budget is None or owner_status not in active_owner_status_values:
            continue
        key = (kind, owner_status)
        bucket = buckets.setdefault(
            key,
            {
                "process_kind": kind,
                "owner_status": owner_status,
                "budget": budget,
                "count": 0,
                "ages_s": [],
            },
        )
        bucket["count"] += 1
        age_s = row.get("age_s")
        if isinstance(age_s, int):
            bucket["ages_s"].append(age_s)

    groups: list[dict[str, Any]] = []
    for bucket in buckets.values():
        count = int(bucket["count"])
        budget = int(bucket["budget"])
        excess_count = max(0, count - budget)
        if excess_count <= 0:
            continue
        ages = [int(age) for age in bucket.pop("ages_s", [])]
        bucket.update(
            {
                "excess_count": excess_count,
                "oldest_age_s": max(ages) if ages else None,
                "newest_age_s": min(ages) if ages else None,
                "recommended_action": "request_owner_release",
                "safety": {
                    "no_process_signal_sent": True,
                    "owner_must_release_own_helper": True,
                },
            }
        )
        bucket["owner_release_request"] = _owner_release_request_for_group(
            bucket, owner_classes
        )
        groups.append(bucket)
    return sorted(
        groups,
        key=lambda item: (int(item.get("excess_count") or 0), int(item.get("count") or 0)),
        reverse=True,
    )


def build_tool_server_pressure_inventory(
    ps_text: str,
    *,
    policy: dict[str, Any],
    owner_classes: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    Classify a synthetic process table into a typed pressure inventory.

    Pure projection over injected text; never reads a live process table and
    never signals a process. Rows carry a `command_hash`, never a command
    preview.
    - Teleology: Implements `build_tool_server_pressure_inventory` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    kind_specs = _kind_specs(policy)
    min_age_seconds = int(policy.get("min_age_seconds") or DEFAULT_MIN_AGE_SECONDS)
    keep_kinds = set(_strings(policy.get("keep_kinds")))
    keep_status_by_kind = {
        str(spec.get("kind")): str(spec.get("keep_owner_status") or "runtime")
        for spec in kind_specs
        if str(spec.get("kind")) in keep_kinds
    }
    allowlisted_kinds = {
        str(spec.get("kind"))
        for spec in kind_specs
        if spec.get("allowlisted") is True
    }
    budget_by_kind = {
        str(spec.get("kind")): int(spec["budget"])
        for spec in kind_specs
        if isinstance(spec.get("budget"), int)
    }
    active_owner_status_values = frozenset(
        _strings(owner_classes.get("active_owner_status_values"))
    ) or ACTIVE_OWNER_STATUS_VALUES

    processes = _parse_process_rows(ps_text)
    process_table = {int(p["pid"]): p for p in processes}
    rows: list[dict[str, Any]] = []
    for process in processes:
        cmd = str(process["cmd"])
        kind = _process_kind(cmd, kind_specs)
        if kind is None:
            continue
        ppid = int(process["ppid"])
        age_s = int(process["age_s"])
        allowlist_matched = kind in allowlisted_kinds
        owner_status = _owner_status_for_process(
            kind=kind,
            ppid=ppid,
            process_table=process_table,
            owner_classes=owner_classes,
            keep_status_by_kind=keep_status_by_kind,
        )
        owner, decision, reason = _inventory_owner_and_decision(
            kind=kind,
            ppid=ppid,
            age_s=age_s,
            allowlist_matched=allowlist_matched,
            owner_status=owner_status,
            min_age_seconds=min_age_seconds,
            keep_kinds=keep_kinds,
            active_owner_status_values=active_owner_status_values,
        )
        rows.append(
            {
                "pid": int(process["pid"]),
                "ppid": ppid,
                "process_kind": kind,
                "owner": owner,
                "owner_status": owner_status,
                "decision": decision,
                "reason": reason,
                "age_s": age_s,
                "cpu_pct": _parse_float(str(process.get("cpu_s", ""))),
                "allowlist_matched": allowlist_matched,
                "command_hash": _command_hash(cmd),
            }
        )

    decision_counts: dict[str, int] = {}
    kind_counts: dict[str, int] = {}
    owner_status_counts: dict[str, int] = {}
    for row in rows:
        decision_counts[row["decision"]] = decision_counts.get(row["decision"], 0) + 1
        kind_counts[row["process_kind"]] = kind_counts.get(row["process_kind"], 0) + 1
        owner_status_counts[row["owner_status"]] = (
            owner_status_counts.get(row["owner_status"], 0) + 1
        )
    groups = _active_owner_pressure_groups(
        rows,
        budget_by_kind=budget_by_kind,
        owner_classes=owner_classes,
        active_owner_status_values=active_owner_status_values,
    )
    return {
        "schema": INVENTORY_SCHEMA,
        "policy": {
            "no_unknown_owner_killed": True,
            "no_process_signal_sent": True,
            "inventory_is_not_kill_list": True,
            "safe_close_predicate": "ppid==1 and allowlisted kind and age>=min_age_seconds",
            "min_age_seconds": min_age_seconds,
        },
        "summary": {
            "process_count": len(rows),
            "candidate_safe_close_count": decision_counts.get(SAFE_CLOSE_DECISION, 0),
            "requires_owner_check_count": decision_counts.get(OWNER_CHECK_DECISION, 0),
            "keep_count": decision_counts.get(KEEP_DECISION, 0),
            "active_owner_release_request_count": sum(
                int(g.get("excess_count") or 0) for g in groups
            ),
            "active_owner_pressure_group_count": len(groups),
            "active_owner_pressure_groups": groups,
            "kind_counts": kind_counts,
            "decision_counts": decision_counts,
            "owner_status_counts": owner_status_counts,
        },
        "rows": rows,
    }


def build_pressure_hygiene_relief_receipt(
    ps_text: str,
    *,
    policy: dict[str, Any],
    owner_classes: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_pressure_hygiene_relief_receipt` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    inventory = build_tool_server_pressure_inventory(
        ps_text, policy=policy, owner_classes=owner_classes
    )
    summary = inventory["summary"]
    candidate = int(summary.get("candidate_safe_close_count", 0))
    owner_check = int(summary.get("requires_owner_check_count", 0))
    active_release = int(summary.get("active_owner_release_request_count", 0))
    owner_release_requests = [
        dict(group.get("owner_release_request") or {})
        for group in summary.get("active_owner_pressure_groups") or []
        if isinstance(group.get("owner_release_request"), dict)
    ]
    if candidate:
        action_status, verdict = "safe_action_available", "pending_safe_close_action"
    elif active_release:
        action_status, verdict = (
            "owner_release_request_available",
            "pending_owner_release_request",
        )
    elif owner_check:
        action_status, verdict = "owner_check_required", "no_safe_action"
    else:
        action_status, verdict = "no_action", "no_safe_action"
    return {
        "schema": RELIEF_RECEIPT_SCHEMA,
        "before": {
            "tool_server_pressure_inventory_schema": inventory["schema"],
            "inventory_summary": summary,
        },
        "action": {
            "status": action_status,
            "safe_close_action_count": 0,
            "safe_close_candidate_count": candidate,
            "requires_owner_check_count": owner_check,
            "active_owner_release_request_count": active_release,
            "owner_release_requests": owner_release_requests,
            "no_unknown_owner_killed": True,
            "no_process_signal_sent": True,
        },
        "after": None,
        "verdict": verdict,
        "next_actions": [
            "request_active_owner_release_for_over_budget_helper_groups",
            "resolve_owner_state_before_closing_requires_owner_check_rows",
        ],
    }


# --------------------------------------------------------------------------- #
# Redaction guard (the first-class public-safety evaluator).
# --------------------------------------------------------------------------- #
def _redaction_findings(payload: object, *, case_id: str, subject_id: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_redaction_findings` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    for row in _walk_dicts(payload):
        for key, value in row.items():
            if key in FORBIDDEN_PREVIEW_KEYS:
                findings.append(
                    _finding(
                        "TSPI_COMMAND_PREVIEW_FORBIDDEN",
                        "Public pressure rows must carry command_hash only, never a live command preview.",
                        case_id=case_id,
                        subject_id=subject_id,
                        subject_kind=str(key),
                    )
                )
            if key in FORBIDDEN_SIGNAL_KEYS and value:
                findings.append(
                    _finding(
                        "TSPI_PROCESS_SIGNAL_FORBIDDEN",
                        "The public inventory must not record that any process signal was sent.",
                        case_id=case_id,
                        subject_id=subject_id,
                        subject_kind=str(key),
                    )
                )
            if isinstance(value, str) and ABSOLUTE_PATH_PATTERN.search(value):
                findings.append(
                    _finding(
                        "TSPI_ABSOLUTE_PATH_FORBIDDEN",
                        "Public surfaces must not carry absolute host paths.",
                        case_id=case_id,
                        subject_id=subject_id,
                        subject_kind=str(key),
                    )
                )
    return findings


def _audit_inventory_claim(
    claimed: dict[str, Any],
    *,
    case_id: str,
    min_age_seconds: int,
    active_owner_status_values: frozenset[str],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    Audit a PROVIDED pressure inventory against the safety contract.
    - Teleology: Implements `_audit_inventory_claim` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    findings.extend(
        _redaction_findings(claimed, case_id=case_id, subject_id="claimed_inventory")
    )
    rows = _rows(claimed, "rows")
    for row in rows:
        subject = str(row.get("pid") or row.get("command_hash") or "row")
        decision = str(row.get("decision") or "")
        owner_status = str(row.get("owner_status") or "")
        ppid = row.get("ppid")
        age_s = row.get("age_s")
        allowlisted = row.get("allowlist_matched") is True
        if decision != SAFE_CLOSE_DECISION:
            continue
        if owner_status in active_owner_status_values:
            findings.append(
                _finding(
                    "TSPI_ACTIVE_OWNER_KILL_CANDIDATE",
                    "An active-owner descendant must never be a safe-close candidate.",
                    case_id=case_id,
                    subject_id=subject,
                    subject_kind="owner_status",
                )
            )
            continue
        if owner_status != DETACHED_OWNER_STATUS or ppid != 1 or not allowlisted:
            findings.append(
                _finding(
                    "TSPI_UNKNOWN_OWNER_KILL_FORBIDDEN",
                    "Safe-close is reserved for ppid==1 allowlisted detached orphans.",
                    case_id=case_id,
                    subject_id=subject,
                    subject_kind="owner_status",
                )
            )
            continue
        if isinstance(age_s, int) and age_s < min_age_seconds:
            findings.append(
                _finding(
                    "TSPI_PREMATURE_SAFE_CLOSE",
                    "A detached orphan younger than min_age_seconds is not a safe-close candidate.",
                    case_id=case_id,
                    subject_id=subject,
                    subject_kind="age_s",
                )
            )
    for group in _rows(claimed.get("summary"), "active_owner_pressure_groups"):
        request = group.get("owner_release_request")
        if isinstance(request, dict):
            result = str(request.get("result") or "").lower()
            requested = str(request.get("requested_action") or "")
            signalled = request.get("safety", {})
            no_signal = (
                signalled.get("no_process_signal_sent") is True
                if isinstance(signalled, dict)
                else False
            )
            if (
                result in FORBIDDEN_OWNER_RELEASE_RESULTS
                or requested not in {"release_tool_lease", "ask_owner_to_release"}
                or not no_signal
            ):
                findings.append(
                    _finding(
                        "TSPI_OWNER_RELEASE_OVERCLAIM",
                        "Over-budget active owners get a release REQUEST, never a kill/terminate.",
                        case_id=case_id,
                        subject_id=str(group.get("process_kind") or "group"),
                        subject_kind="owner_release_request",
                    )
                )
    for group in _rows(claimed.get("summary"), "active_owner_pressure_groups"):
        if group.get("recommended_action") in {"kill", "sigterm", "sigkill", "force_close"}:
            findings.append(
                _finding(
                    "TSPI_PROCESS_SIGNAL_FORBIDDEN",
                    "An active-owner pressure group must recommend release, not a signal.",
                    case_id=case_id,
                    subject_id=str(group.get("process_kind") or "group"),
                    subject_kind="recommended_action",
                )
            )
    return findings


# --------------------------------------------------------------------------- #
# Positive / negative findings.
# --------------------------------------------------------------------------- #
def _positive_findings(
    *,
    process_table_payload: dict[str, Any],
    policy: dict[str, Any],
    owner_classes: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_positive_findings` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    ps_text = str(process_table_payload.get("ps_text") or "")
    min_age_seconds = int(policy.get("min_age_seconds") or DEFAULT_MIN_AGE_SECONDS)
    active_owner_status_values = frozenset(
        _strings(owner_classes.get("active_owner_status_values"))
    ) or ACTIVE_OWNER_STATUS_VALUES

    # Redaction guard over the raw public inputs.
    for label, payload in (
        ("process_table", process_table_payload),
        ("pressure_policy", policy),
        ("owner_classes", owner_classes),
    ):
        findings.extend(
            _redaction_findings(payload, case_id="positive_redaction", subject_id=label)
        )

    if not ps_text:
        findings.append(
            _finding(
                "TSPI_MISSING_PROCESS_TABLE",
                "process_table.json must carry a synthetic ps_text process table.",
                case_id="positive_inventory",
                subject_id="process_table.json",
                subject_kind="ps_text",
            )
        )
        return findings, {}

    inventory = build_tool_server_pressure_inventory(
        ps_text, policy=policy, owner_classes=owner_classes
    )
    # Defense in depth: the mechanism's own output must satisfy the contract.
    findings.extend(
        _audit_inventory_claim(
            inventory,
            case_id="positive_inventory",
            min_age_seconds=min_age_seconds,
            active_owner_status_values=active_owner_status_values,
        )
    )
    if policy.get("process_signal_authorized") is True:
        findings.append(
            _finding(
                "TSPI_PROCESS_SIGNAL_FORBIDDEN",
                "Pressure policy must not authorize sending a process signal.",
                case_id="positive_policy",
                subject_id="pressure_policy.json",
                subject_kind="process_signal_authorized",
            )
        )
    return findings, inventory


def _negative_findings(payloads: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_negative_findings` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for stem in NEGATIVE_INPUT_STEMS:
        payload = payloads.get(stem)
        if not isinstance(payload, dict):
            continue
        case_id = str(payload.get("expected_negative_case_id") or stem)
        min_age_seconds = int(payload.get("min_age_seconds") or DEFAULT_MIN_AGE_SECONDS)
        active_values = frozenset(
            _strings(payload.get("active_owner_status_values"))
        ) or ACTIVE_OWNER_STATUS_VALUES
        claimed = payload.get("claimed_inventory")
        if not isinstance(claimed, dict):
            continue
        for finding in _audit_inventory_claim(
            claimed,
            case_id=case_id,
            min_age_seconds=min_age_seconds,
            active_owner_status_values=active_values,
        ):
            observed[case_id].add(finding["error_code"])
            findings.append(finding)
    return {
        "findings": findings,
        "observed_negative_cases": {k: sorted(v) for k, v in observed.items()},
    }


# --------------------------------------------------------------------------- #
# Source-module import membrane (source-faithful lane).
# --------------------------------------------------------------------------- #
def _source_module_manifest_path(input_dir: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_path` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return input_dir / SOURCE_MODULE_MANIFEST_NAME


def _source_module_target_path(
    target_ref: str, *, input_dir: Path, public_root: Path
) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_source_module_target_path` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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


def _source_module_manifest_result(
    input_dir: Path, *, public_root: Path, require_manifest: bool
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_manifest_result` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        status = "blocked" if require_manifest else "not_present"
        findings = (
            [
                _finding(
                    "TSPI_SOURCE_MODULE_MANIFEST_REQUIRED",
                    "Exported bundle must include a source module manifest for the source-faithful macro body import.",
                    case_id="source_module_manifest",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
                    subject_kind="source_module_manifest",
                )
            ]
            if require_manifest
            else []
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
            "findings": findings,
        }

    manifest = read_json_strict(manifest_path)
    findings: list[dict[str, Any]] = []
    modules = _rows(manifest, "modules")
    module_ids: list[str] = []
    material_class_counts: dict[str, int] = {}
    source_refs = [_display(manifest_path, public_root=public_root)]
    verified_count = 0
    for row in modules:
        module_id = str(row.get("module_id") or "source_module")
        module_ids.append(module_id)
        material_class = str(row.get("material_class") or "")
        if material_class:
            material_class_counts[material_class] = (
                material_class_counts.get(material_class, 0) + 1
            )
        start = len(findings)
        if str(row.get("source_to_target_relation") or "") not in ACCEPTED_SOURCE_RELATIONS:
            findings.append(
                _finding(
                    "TSPI_SOURCE_MODULE_RELATION_UNVERIFIED",
                    "Source module rows must declare exact_copy or a source-faithful public refactor relation.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_to_target_relation",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_BODY_CLASSES:
            findings.append(
                _finding(
                    "TSPI_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module rows must use a public-safe macro body material class.",
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
                    "TSPI_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module rows must land the body in source_modules while keeping receipts body-free.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        path_ref = str(row.get("path") or "")
        target_ref = str(row.get("target_ref") or "")
        path_target = (
            _source_module_target_path(
                path_ref, input_dir=input_dir, public_root=public_root
            )
            if path_ref
            else None
        )
        target_ref_target = (
            _source_module_target_path(
                target_ref, input_dir=input_dir, public_root=public_root
            )
            if target_ref
            else None
        )
        if (
            path_target is not None
            and target_ref_target is not None
            and path_target.resolve(strict=False)
            != target_ref_target.resolve(strict=False)
        ):
            findings.append(
                _finding(
                    "TSPI_SOURCE_MODULE_TARGET_REF_PATH_MISMATCH",
                    "Source module path and target_ref must resolve to the same copied body.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        target = target_ref_target or path_target
        if target is None or not target.is_file():
            findings.append(
                _finding(
                    "TSPI_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target body must exist inside the public bundle.",
                    case_id="source_module_manifest",
                    subject_id=target_ref or path_ref or module_id,
                    subject_kind="source_module",
                )
            )
            continue
        actual = _sha256(target)
        declared = {
            str(row.get("sha256") or "").removeprefix("sha256:"),
            str(row.get("target_sha256") or "").removeprefix("sha256:"),
        }
        if actual not in declared or "" in declared:
            findings.append(
                _finding(
                    "TSPI_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module target digest must match the declared target_sha256.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        text = target.read_text(encoding="utf-8")
        missing = [a for a in _strings(row.get("required_anchors")) if a not in text]
        if missing:
            findings.append(
                {
                    **_finding(
                        "TSPI_SOURCE_MODULE_ANCHOR_MISSING",
                        "Source module body must carry the declared macro anchors.",
                        case_id="source_module_manifest",
                        subject_id=module_id,
                        subject_kind="source_module",
                    ),
                    "missing_anchors": missing,
                }
            )
        # Redaction guard runs on the imported body text too.
        if ABSOLUTE_PATH_PATTERN.search(text) or any(
            key in text for key in FORBIDDEN_PREVIEW_KEYS
        ):
            findings.append(
                _finding(
                    "TSPI_ABSOLUTE_PATH_FORBIDDEN",
                    "Imported source-faithful body must be redacted of absolute paths and command previews.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="redaction",
                )
            )
        source_refs.append(_display(target, public_root=public_root))
        if len(findings) == start:
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
        "findings": findings,
    }


def _source_open_body_import_summary(source_module_result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_source_open_body_import_summary` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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
        "material_classes": source_module_result.get("material_classes", []) if imported else [],
        "body_material_classes": source_module_result.get("body_material_classes", {})
        if imported
        else {},
        "source_manifest_refs": [str(manifest_ref)] if imported and manifest_ref else [],
        "aggregate_floor_ref": f"{manifest_ref}::modules" if imported and manifest_ref else "",
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "authority_ceiling": {
            "body_text_in_receipt": False,
            "provider_payload_exported": False,
            "credential_or_account_bound_payload_exported": False,
            "release_authorized": False,
            "whole_system_correctness_claim": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ for the "
            "source-faithful public refactor of the macro orphan_reaper read-only "
            "mechanism; receipts carry refs, hashes, counts, and verdicts only."
        )
        if imported
        else "",
    }


# --------------------------------------------------------------------------- #
# Freshness + receipts.
# --------------------------------------------------------------------------- #
def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_input_paths` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names]


def _source_module_paths(input_dir: Path, *, public_root: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_source_module_paths` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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
                    target_ref, input_dir=input_dir, public_root=public_root
                )
            )
    return paths


def _scan_paths_for_input(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_scan_paths_for_input` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    extra = [input_dir / "bundle_manifest.json"] if (input_dir / "bundle_manifest.json").is_file() else []
    return [
        *_input_paths(input_dir, include_negative=include_negative),
        *extra,
        *_source_module_paths(input_dir, public_root=public_root),
    ]


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_freshness_basis` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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
    paths = list(_input_paths(source, include_negative=include_negative))
    manifest = source / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    paths.extend(_source_module_paths(source, public_root=public_root))
    paths.append(Path(__file__).resolve())
    for path in paths:
        display = _display(path, public_root=public_root)
        if path.is_file():
            rows.append({"path": display, "sha256": _sha256(path), "size_bytes": path.stat().st_size})
        else:
            missing.append(display)
    schema = (
        "tool_server_pressure_inventory_result_v1"
        if include_negative
        else "exported_tool_server_pressure_inventory_bundle_validation_result_v1"
    )
    basis_digest = hashlib.sha256(
        json.dumps(
            {
                "card_schema_version": CARD_SCHEMA_VERSION,
                "include_negative": include_negative,
                "inputs": rows,
                "missing_inputs": missing,
                "validator_schema_version": schema,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "tool_server_pressure_inventory_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": schema,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_bundle_receipt(input_dir: Path, out_dir: Path) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Implements `_fresh_bundle_receipt` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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
    existing = payload.get("freshness_basis")
    if not isinstance(existing, dict) or existing.get("basis_digest") != basis["basis_digest"]:
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
    - Teleology: Implements `_load_payloads` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    payloads: dict[str, Any] = {}
    for name in names:
        path = input_dir / name
        payloads[Path(name).stem] = read_json_strict(path) if path.is_file() else {}
    return payloads


def _build_result(
    input_dir: Path, *, command: str, input_mode: str, include_negative: bool
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_result` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    process_table = payloads.get("process_table") if isinstance(payloads.get("process_table"), dict) else {}
    policy = payloads.get("pressure_policy") if isinstance(payloads.get("pressure_policy"), dict) else {}
    owner_classes = payloads.get("owner_classes") if isinstance(payloads.get("owner_classes"), dict) else {}

    source_module_result = _source_module_manifest_result(
        input_dir, public_root=public_root, require_manifest=not include_negative
    )
    source_open_body_imports = _source_open_body_import_summary(source_module_result)
    forbidden_policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _scan_paths_for_input(input_dir, include_negative=include_negative),
        forbidden_classes=forbidden_policy,
        display_root=public_root,
    )

    positive_findings, inventory = _positive_findings(
        process_table_payload=process_table, policy=policy, owner_classes=owner_classes
    )
    negative_payloads = {
        name: payloads[name] for name in NEGATIVE_INPUT_STEMS if name in payloads
    }
    negative = _negative_findings(negative_payloads)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    observed = negative["observed_negative_cases"]
    missing = sorted(case_id for case_id in expected if case_id not in observed)

    findings = [*positive_findings, *negative["findings"], *source_module_result["findings"]]
    error_codes = sorted({f["error_code"] for f in findings})
    inv_summary = inventory.get("summary", {}) if isinstance(inventory, dict) else {}
    status = (
        PASS
        if not positive_findings
        and not missing
        and not secret_scan["blocking_hit_count"]
        and source_module_result["status"] in {PASS, "not_present"}
        else "blocked"
    )
    source_module_refs = [
        str(ref) for ref in source_module_result.get("source_refs", []) if isinstance(ref, str)
    ]
    return {
        "schema_version": "tool_server_pressure_inventory_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
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
        "inventory_projection": {
            "process_count": inv_summary.get("process_count", 0),
            "candidate_safe_close_count": inv_summary.get("candidate_safe_close_count", 0),
            "requires_owner_check_count": inv_summary.get("requires_owner_check_count", 0),
            "keep_count": inv_summary.get("keep_count", 0),
            "active_owner_release_request_count": inv_summary.get(
                "active_owner_release_request_count", 0
            ),
            "active_owner_pressure_group_count": inv_summary.get(
                "active_owner_pressure_group_count", 0
            ),
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "command_preview_in_rows": False,
        },
        "negative_case_count": len(EXPECTED_NEGATIVE_CASES) if include_negative else 0,
        "source_module_manifest_status": source_module_result["status"],
        "source_module_manifest_ref": source_module_result["source_module_manifest_ref"],
        "source_module_import_status": source_module_result["source_module_import_status"],
        "source_module_summary": source_module_result,
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports["body_material_count"],
        "body_in_receipt": False,
        "real_runtime_receipt": status == PASS,
        "synthetic_receipt_standin_allowed": False,
    }


def _build_board(*, result: dict[str, Any], secret_scan: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_build_board` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "tool_server_pressure_inventory_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "selected_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result["input_mode"],
        "public_runtime_refs": PUBLIC_RUNTIME_REFS,
        "inventory_projection": result["inventory_projection"],
        "public_contract": {
            "active_owner_descendant_never_safe_close": True,
            "safe_close_requires_detached_orphan_allowlist_and_age": True,
            "over_budget_active_owner_gets_release_request_not_kill": True,
            "rows_carry_command_hash_not_preview": True,
            "no_process_signal_sent": True,
            "no_live_process_table_read": True,
            "source_faithful_macro_body_import_required_for_exported_bundle": True,
            "absolute_paths_and_command_previews_forbidden": True,
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
    result: dict[str, Any], *, schema_version: str, receipt_paths: list[str]
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_common_receipt` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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
        "inventory_projection",
        "negative_case_count",
        "source_module_manifest_status",
        "source_module_manifest_ref",
        "source_module_import_status",
        "source_module_summary",
        "source_open_body_imports",
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


def _write_receipts(
    result: dict[str, Any], out_dir: Path, *, acceptance_out: Path | None
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_write_receipts` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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
    relative_paths = [_display(path, public_root=public_root) for path in paths.values()]
    board = _build_board(result=result, secret_scan=result["secret_exclusion_scan"])
    board["receipt_paths"] = relative_paths
    result_receipt = _common_receipt(
        result,
        schema_version="tool_server_pressure_inventory_result_receipt_v1",
        receipt_paths=relative_paths,
    )
    validation = _common_receipt(
        result,
        schema_version="tool_server_pressure_inventory_validation_receipt_v1",
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
        write_json_atomic(
            acceptance_out,
            _common_receipt(
                result,
                schema_version="tool_server_pressure_inventory_fixture_acceptance_v1",
                receipt_paths=relative_paths,
            ),
        )
    result["receipt_paths"] = relative_paths
    return result


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.tool_server_pressure_inventory run",
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    result["freshness_basis"] = _freshness_basis(Path(input_dir), include_negative=True)
    result["receipt_reused"] = False
    return _write_receipts(
        result, Path(out_dir), acceptance_out=Path(acceptance_out) if acceptance_out else None
    )


def run_pressure_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.tool_server_pressure_inventory run-pressure-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_pressure_bundle` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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
        input_mode="exported_tool_server_pressure_inventory_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    path = target / BUNDLE_RESULT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = _display(path, public_root=public_root)
    receipt = _common_receipt(
        result,
        schema_version="exported_tool_server_pressure_inventory_bundle_validation_result_v1",
        receipt_paths=[receipt_path],
    )
    write_json_atomic(path, receipt)
    result["receipt_paths"] = [receipt_path]
    return result


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `result_card` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    basis = result.get("freshness_basis") if isinstance(result.get("freshness_basis"), dict) else {}
    sob = result.get("source_open_body_imports") if isinstance(result.get("source_open_body_imports"), dict) else {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": basis.get("basis_digest"),
            "freshness_input_count": basis.get("input_count"),
            "freshness_missing_path_count": basis.get("missing_path_count"),
        },
        "inventory_projection": result.get("inventory_projection"),
        "source_open_body_imports": {
            "status": sob.get("status"),
            "body_material_count": sob.get("body_material_count"),
            "source_module_manifest_ref": result.get("source_module_manifest_ref"),
            "body_in_receipt": False,
        },
        "validation": {
            "missing_negative_case_count": len(result.get("missing_negative_cases") or []),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
            "real_runtime_receipt": result.get("real_runtime_receipt") is True,
            "synthetic_receipt_standin_allowed": result.get("synthetic_receipt_standin_allowed") is True,
        },
        "authority_boundary": {
            "process_signal_authority": False,
            "host_mutation_authorized": False,
            "release_authorized": False,
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
    - Teleology: Implements `_parser` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(
        description="Validate public tool-server / helper-process pressure inventory"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-pressure-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.tool_server_pressure_inventory` while keeping the callable contract visible to source-module readers.
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
            "python -m microcosm_core.organs.tool_server_pressure_inventory run "
            f"--input {args.input} --out {args.out}{card_suffix}"
        )
        result = run(args.input, args.out, command=command, acceptance_out=args.acceptance_out)
    else:
        command = (
            "python -m microcosm_core.organs.tool_server_pressure_inventory "
            f"run-pressure-bundle --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run_pressure_bundle(
            args.input, args.out, command=command, reuse_fresh_receipt=args.card
        )
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
