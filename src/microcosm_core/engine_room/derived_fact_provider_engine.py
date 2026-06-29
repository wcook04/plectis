"""
Public-safe derived fact provider engine capsule.

This is a source-faithful public refactor of
`system/lib/derived_fact_hologram.py` and
`codex/doctrine/facts/fact_registry.json`. It preserves the core provider
shape: authored registry rows resolve through JSON pointer, glob count, and
callable providers; provider failures become error rows with repair hints
instead of crashing the whole ledger.

The capsule evaluates a small public fixture registry. It is the provider
engine, not a doctrine truth auditor: a clean provider receipt means the
registered facts resolved against the supplied root, not that prose claims are
true or that every macro fact family is covered.

[PURPOSE]
- Teleology: Exposes `microcosm_core.engine_room.derived_fact_provider_engine` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: SCHEMA_VERSION, ORGAN_ID, SOURCE_REFS, SOURCE_TO_TARGET_RELATION, CLAIM_CEILING, ANTI_CLAIMS, resolve_json_pointer, evaluate_provider, evaluate_registry, evaluate_case, evaluate_fixture_dir, build_parser, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs, declared subprocess results.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, subprocess side effects requested by the caller and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: None beyond the Python standard library and local package imports.
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
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "engine_room_derived_fact_provider_engine_v1"
ORGAN_ID = "engine_room_derived_fact_provider_engine"
SOURCE_REFS = (
    "system/lib/derived_fact_hologram.py",
    "codex/doctrine/facts/fact_registry.json",
)
SOURCE_TO_TARGET_RELATION = "source_faithful_public_refactor"
CLAIM_CEILING = (
    "Registry-backed derived fact provider engine over public fixture roots. "
    "It resolves JSON-pointer, glob-count, and git-backed callable facts and "
    "turns provider failures into error-as-data rows. It is not a doctrine "
    "truth auditor, not a full macro fact registry export, not semantic claim "
    "validation, and not release authority."
)
ANTI_CLAIMS = (
    "not_doctrine_truth_auditor",
    "not_full_macro_registry_export",
    "not_semantic_claim_validation",
    "not_release_authority",
)


def _utc_now() -> str:
    """
    [ACTION]
    - Teleology: Implements `_utc_now` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256_json(value: Any) -> str:
    """
    [ACTION]
    - Teleology: Implements `_sha256_json` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _string(value: Any) -> str:
    """
    [ACTION]
    - Teleology: Implements `_string` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return str(value or "").strip()


def _read_json(path: Path) -> Any:
    """
    [ACTION]
    - Teleology: Implements `_read_json` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def _json_pointer_tokens(pointer: str) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_json_pointer_tokens` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    raw = str(pointer or "").strip()
    if raw.startswith("#"):
        raw = raw[1:]
    if raw == "":
        return []
    if not raw.startswith("/"):
        raise ValueError(f"JSON pointer must start with '/': {pointer}")
    return [token.replace("~1", "/").replace("~0", "~") for token in raw.split("/")[1:]]


def resolve_json_pointer(payload: Any, pointer: str) -> Any:
    """
    [ACTION]
    - Teleology: Implements `resolve_json_pointer` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    value = payload
    for token in _json_pointer_tokens(pointer):
        if isinstance(value, list):
            try:
                value = value[int(token)]
            except (ValueError, IndexError) as exc:
                raise KeyError(token) from exc
        elif isinstance(value, Mapping):
            if token not in value:
                raise KeyError(token)
            value = value[token]
        else:
            raise KeyError(token)
    return value


def _coerce_scalar(value: Any, value_type: str | None = None) -> Any:
    """
    [ACTION]
    - Teleology: Implements `_coerce_scalar` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    kind = str(value_type or "").strip().lower()
    if kind == "integer":
        return int(value)
    if kind == "number":
        return float(value)
    if kind == "boolean":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
    if kind == "string":
        return str(value)
    return value


def _value_repr(value: Any) -> str:
    """
    [ACTION]
    - Teleology: Implements `_value_repr` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _relpath(root: Path, path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_relpath` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _git_ls_files(root: Path) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_git_ls_files` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _callable_value(name: str, root: Path) -> Any:
    """
    [ACTION]
    - Teleology: Implements `_callable_value` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if name == "git_tracked_file_count":
        return len(_git_ls_files(root))
    if name == "git_tracked_python_count":
        return sum(1 for path in _git_ls_files(root) if path.endswith(".py"))
    if name == "tracked_fact_registry_count":
        path = root / "fact_registry.json"
        payload = _read_json(path)
        rows = payload.get("facts") if isinstance(payload, Mapping) else []
        return len(rows) if isinstance(rows, list) else 0
    raise KeyError(f"unknown callable fact provider: {name}")


def _source_repair_command(source_path: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_source_repair_command` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source = _string(source_path)
    return f"restore_or_rebuild_source_path:{source}" if source else "inspect_fact_provider_source_path"


def evaluate_provider(row: Mapping[str, Any], *, root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_provider` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    fact_id = _string(row.get("id"))
    provider_type = _string(row.get("provider_type"))
    value_type = _string(row.get("value_type")) or None
    base: dict[str, Any] = {
        "id": fact_id,
        "title": _string(row.get("title")) or fact_id,
        "provider_type": provider_type,
        "value_type": value_type,
        "tags": [str(item) for item in (row.get("tags") or []) if str(item).strip()],
        "provider_status": "ok",
        "status": "ok",
        "source_path": _string(row.get("source_path")) or None,
        "pointer": _string(row.get("pointer")) or None,
        "glob": _string(row.get("glob")) or None,
        "callable": _string(row.get("callable")) or None,
    }
    try:
        if not fact_id:
            raise ValueError("missing fact id")
        if provider_type == "json_pointer":
            source_path = _string(row.get("source_path"))
            pointer = _string(row.get("pointer"))
            if not source_path or not pointer:
                raise ValueError("json_pointer provider requires source_path and pointer")
            value = resolve_json_pointer(_read_json(root / source_path), pointer)
        elif provider_type == "glob_count":
            pattern = _string(row.get("glob"))
            if not pattern:
                raise ValueError("glob_count provider requires glob")
            exclude_prefixes = tuple(_string(item) for item in (row.get("exclude_prefixes") or []) if _string(item))
            matches: list[str] = []
            for path in root.glob(pattern):
                rel = _relpath(root, path)
                if any(rel.startswith(prefix) for prefix in exclude_prefixes):
                    continue
                if path.is_file():
                    matches.append(rel)
            matches.sort()
            value = len(matches)
            base["sample_matches"] = matches[:20]
        elif provider_type == "callable":
            callable_name = _string(row.get("callable"))
            if not callable_name:
                raise ValueError("callable provider requires callable")
            value = _callable_value(callable_name, root)
        else:
            raise ValueError(f"unknown provider_type: {provider_type}")
        value = _coerce_scalar(value, value_type)
        base["value"] = value
        base["value_repr"] = _value_repr(value)
    except Exception as exc:  # noqa: BLE001 - provider failures are ledger rows.
        base["provider_status"] = "error"
        base["status"] = "error"
        base["error_class"] = exc.__class__.__name__
        base["value"] = None
        base["value_repr"] = ""
        source_path = _string(row.get("source_path"))
        if isinstance(exc, FileNotFoundError) and source_path:
            base["error"] = f"source path not found: {source_path}"
        else:
            base["error"] = str(exc)
        if source_path:
            base["source_status"] = "missing" if isinstance(exc, FileNotFoundError) else "error"
            base["required_next_action"] = _source_repair_command(source_path)
    return base


def evaluate_registry(registry: Mapping[str, Any], *, root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_registry` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = [dict(item) for item in (registry.get("facts") or []) if isinstance(item, Mapping)]
    facts = [evaluate_provider(row, root=root) for row in rows]
    provider_counts = Counter(str(row.get("provider_type") or "unknown") for row in facts)
    status_counts = Counter(str(row.get("provider_status") or row.get("status") or "unknown") for row in facts)
    generated_at = _utc_now()
    summary = {
        "fact_count": len(facts),
        "provider_type_counts": dict(sorted(provider_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "error_count": int(status_counts.get("error", 0)),
    }
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "generated_at": generated_at,
        "status": "degraded" if summary["error_count"] else "ok",
        "summary": summary,
        "facts": facts,
    }
    provider_findings = [
        {
            "severity": "error",
            "rule": "fact_provider_error",
            "fact_id": fact.get("id"),
            "provider_type": fact.get("provider_type"),
            "source_path": fact.get("source_path"),
            "error_class": fact.get("error_class"),
            "message": fact.get("error"),
            "required_next_action": fact.get("required_next_action"),
        }
        for fact in facts
        if fact.get("provider_status") == "error"
    ]
    navigation_cache = {
        "rows": [
            {
                "id": fact.get("id"),
                "title": fact.get("title"),
                "value": fact.get("value"),
                "provider_status": fact.get("provider_status"),
                "provider_type": fact.get("provider_type"),
                "tags": list(fact.get("tags") or []),
            }
            for fact in facts
        ]
    }
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "status": ledger["status"],
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "ledger": ledger,
        "audit": {
            "provider_findings": provider_findings,
            "provider_error_count": len(provider_findings),
        },
        "navigation_cache": navigation_cache,
    }
    receipt["receipt_sha256"] = _sha256_json(
        {
            "summary": summary,
            "facts": facts,
            "provider_findings": provider_findings,
        }
    )
    return receipt


def _write_case_files(root: Path, files: Mapping[str, Any]) -> None:
    """
    [ACTION]
    - Teleology: Implements `_write_case_files` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    for rel_path, content in files.items():
        path = root / _string(rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, (dict, list)):
            path.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        else:
            path.write_text(str(content), encoding="utf-8")


def _prepare_git_index(root: Path, tracked_paths: Sequence[Any]) -> None:
    """
    [ACTION]
    - Teleology: Implements `_prepare_git_index` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    paths = [_string(path) for path in tracked_paths if _string(path)]
    if paths:
        subprocess.run(["git", "add", "--", *paths], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def evaluate_case(case: Mapping[str, Any], *, path: str = "") -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_case` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    with tempfile.TemporaryDirectory(prefix="microcosm-fact-provider-") as tmp:
        root = Path(tmp)
        files = case.get("files") if isinstance(case.get("files"), Mapping) else {}
        _write_case_files(root, files)
        if isinstance(case.get("git_tracked"), Sequence) and not isinstance(case.get("git_tracked"), (str, bytes)):
            _prepare_git_index(root, case.get("git_tracked") or [])
        registry = case.get("registry") if isinstance(case.get("registry"), Mapping) else {}
        receipt = evaluate_registry(registry, root=root)

    facts_by_id = {str(fact.get("id")): fact for fact in receipt["ledger"]["facts"]}
    expected_values = case.get("expected_values") if isinstance(case.get("expected_values"), Mapping) else {}
    value_checks = [
        {
            "fact_id": fact_id,
            "expected": expected,
            "observed": facts_by_id.get(str(fact_id), {}).get("value"),
            "ok": facts_by_id.get(str(fact_id), {}).get("value") == expected,
        }
        for fact_id, expected in expected_values.items()
    ]
    expected_error_ids = [_string(item) for item in (case.get("expected_error_ids") or []) if _string(item)]
    error_checks = [
        {
            "fact_id": fact_id,
            "provider_status": facts_by_id.get(fact_id, {}).get("provider_status"),
            "error_class": facts_by_id.get(fact_id, {}).get("error_class"),
            "ok": facts_by_id.get(fact_id, {}).get("provider_status") == "error",
        }
        for fact_id in expected_error_ids
    ]
    unexpected_errors = [
        fact.get("id")
        for fact in receipt["ledger"]["facts"]
        if fact.get("provider_status") == "error" and fact.get("id") not in expected_error_ids
    ]
    expected_status = _string(case.get("expected_status")) or ("degraded" if expected_error_ids else "ok")
    expectation_met = (
        receipt["status"] == expected_status
        and all(row["ok"] for row in value_checks)
        and all(row["ok"] for row in error_checks)
        and not unexpected_errors
    )
    return {
        "case_id": _string(case.get("case_id")) or Path(path).stem,
        "path": path,
        "expected_status": expected_status,
        "observed_status": receipt["status"],
        "expectation_met": expectation_met,
        "value_checks": value_checks,
        "error_checks": error_checks,
        "unexpected_error_ids": unexpected_errors,
        "receipt": receipt,
    }


def evaluate_fixture_dir(input_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `evaluate_fixture_dir` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    cases: list[dict[str, Any]] = []
    for path in sorted(input_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError(f"{path} did not contain a JSON object")
        cases.append(evaluate_case(payload, path=str(path)))
    passed = sum(1 for case in cases if case["expectation_met"])
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "case_count": len(cases),
        "passed_case_count": passed,
        "status": "pass" if cases and passed == len(cases) else "fail",
        "cases": cases,
    }


def build_parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `build_parser` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description="Engine Room derived fact provider engine capsule.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate = subparsers.add_parser("evaluate-registry", help="Evaluate a public fact registry against a root.")
    evaluate.add_argument("--root", required=True)
    evaluate.add_argument("--registry", required=True)
    evaluate.add_argument("--json", action="store_true")

    fixtures = subparsers.add_parser("evaluate-fixtures", help="Evaluate public fixture cases.")
    fixtures.add_argument("--input", required=True)
    fixtures.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.engine_room.derived_fact_provider_engine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "evaluate-registry":
        registry = _read_json(Path(args.registry))
        if not isinstance(registry, Mapping):
            print("registry must be a JSON object", file=sys.stderr)
            return 2
        receipt = evaluate_registry(registry, root=Path(args.root))
        if args.json:
            print(json.dumps(receipt, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {receipt['status']} facts={receipt['ledger']['summary']['fact_count']}")
        return 0 if receipt["status"] in {"ok", "degraded"} else 1
    if args.command == "evaluate-fixtures":
        payload = evaluate_fixture_dir(Path(args.input))
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"{payload['organ_id']}: {payload['status']}")
        return 0 if payload["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
