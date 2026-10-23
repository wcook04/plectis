"""Small JSON boundary; no candidate Python code is imported or evaluated."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

_WORKER = Path(__file__).with_name("_worker.py")
_MAX_REQUEST = 2_000_000
_MAX_JSON_NODES = 300_000


class InvalidInput(ValueError):
    """Malformed or unsupported host input. Values are not echoed."""


class RejectedPlan(ValueError):
    """The plan does not satisfy the static public-flow contract."""


def _canonical(value: Any) -> str:
    visited = 0

    def check_json(node: Any, depth: int = 0) -> None:
        nonlocal visited
        # Count expanded visits, including repeated references to a shared
        # subtree. Otherwise a small Python object graph can expand without
        # bound before the worker's AST checks or timeout are reached.
        visited += 1
        if visited > _MAX_JSON_NODES:
            raise InvalidInput("Input exceeds the JSON node limit")
        if depth > 128:
            raise InvalidInput("JSON nesting is too deep")
        if node is None or type(node) in (str, bool, int):
            return
        if type(node) is float and math.isfinite(node):
            return
        if type(node) is list:
            for item in node:
                check_json(item, depth + 1)
            return
        if type(node) is dict and all(type(key) is str for key in node):
            for item in node.values():
                check_json(item, depth + 1)
            return
        raise InvalidInput("Input must use exact JSON types and string object keys")
    check_json(value)
    try:
        result = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise InvalidInput("Input must be finite JSON data") from exc
    if len(result.encode("utf-8")) > _MAX_REQUEST:
        raise InvalidInput("Input exceeds the documented JSON size limit")
    return result


def _unique_reply_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate worker response key")
        result[key] = value
    return result


def _reject_constant(_):
    raise ValueError("Non-finite worker response number")


def _has_scalar_strings(value):
    if type(value) is str:
        return all(not 0xD800 <= ord(character) <= 0xDFFF for character in value)
    if type(value) is list:
        return all(_has_scalar_strings(item) for item in value)
    if type(value) is dict:
        return all(_has_scalar_strings(key) and _has_scalar_strings(item)
                   for key, item in value.items())
    return True


def _call(message: dict[str, Any]) -> dict[str, Any]:
    request = _canonical(message)
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-B", str(_WORKER)], input=request,
            text=True, encoding="utf-8", capture_output=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InvalidInput("The local generated-core worker did not complete") from exc
    if proc.returncode != 0:
        raise InvalidInput("The local generated-core worker failed")
    try:
        result = json.loads(proc.stdout, object_pairs_hook=_unique_reply_object,
                            parse_constant=_reject_constant)
        if not _has_scalar_strings(result):
            raise ValueError("Non-scalar worker response text")
    except (ValueError, RecursionError) as exc:
        raise InvalidInput("The local generated-core worker returned invalid output") from exc
    if type(result) is not dict or type(result.get("ok")) is not bool:
        raise InvalidInput("The local generated-core worker returned invalid output")
    if not result["ok"]:
        if (set(result) != {"ok", "kind", "reason"}
                or result["kind"] not in ("rejected", "invalid")
                or type(result["reason"]) is not str):
            raise InvalidInput("The local generated-core worker returned invalid output")
        if result["kind"] == "rejected":
            raise RejectedPlan(result["reason"])
        raise InvalidInput(result["reason"])
    if message["action"] == "compile":
        valid = (set(result) == {"ok", "public_plan", "public_fields", "read_fields"}
                 and type(result["public_plan"]) is dict
                 and all(type(result[key]) is list
                         and all(type(field) is str for field in result[key])
                         and len(result[key]) == len(set(result[key]))
                         for key in ("public_fields", "read_fields")))
        valid = valid and set(result["read_fields"]).issubset(result["public_fields"])
    else:
        valid = (set(result) == {"ok", "traces"} and type(result["traces"]) is list
                 and len(result["traces"]) == len(message["rows"])
                 and all(type(trace) is list and all(type(item) is str for item in trace)
                         for trace in result["traces"]))
    if not valid:
        raise InvalidInput("The local generated-core worker returned invalid output")
    return result


@dataclass(frozen=True)
class CompiledPlan:
    """Immutable input snapshot. Every run rechecks this exact source and policy.

    The digest is an identity aid, not a signature, certificate or access token.
    Construct with compile_public; manually constructed values are rechecked too.
    """
    _schema_json: str
    _plan_json: str
    _public_plan_json: str
    public_fields: tuple[str, ...]
    read_fields: tuple[str, ...]
    digest: str

    @property
    def public_plan(self) -> dict[str, Any]:
        """Return a detached JSON view, never the internal mutable state."""
        return json.loads(self._public_plan_json)

    @property
    def schema(self) -> dict[str, Any]:
        return json.loads(self._schema_json)


def compile_public(plan: dict[str, Any], schema: dict[str, Any]) -> CompiledPlan:
    """Check a fixed plan against an independently owned schema, then slice it.

    No records or private values are accepted by this operation.
    """
    schema_json, plan_json = _canonical(schema), _canonical(plan)
    result = _call({"action": "compile", "schema": json.loads(schema_json), "plan": json.loads(plan_json)})
    identity = hashlib.sha256((schema_json + "\n" + plan_json).encode("utf-8")).hexdigest()
    return CompiledPlan(schema_json, plan_json, _canonical(result["public_plan"]),
                        tuple(result["public_fields"]), tuple(result["read_fields"]), identity)


def run_public_batch(compiled: CompiledPlan, rows: list[dict[str, Any]]) -> tuple[tuple[str, ...], ...]:
    """Execute on public-only records; high fields and unknown keys are refused.

    All public schema fields are required. Row count/order are public inputs.
    No SQL, filesystem, network, clocks, callbacks or model calls occur in plans.
    """
    if type(compiled) is not CompiledPlan:
        raise InvalidInput("Expected a compiled plan")
    try:
        schema, plan = json.loads(compiled._schema_json), json.loads(compiled._plan_json)
    except (ValueError, TypeError, RecursionError) as exc:
        raise InvalidInput("Invalid compiled input snapshot") from exc
    # Re-derive the allowed keys from the actual checked policy, never from
    # caller-editable cached metadata. Refuse extras before serialising values
    # or crossing the worker boundary, including accidentally supplied secrets.
    checked = _call({"action": "compile", "schema": schema, "plan": plan})
    allowed = set(checked["public_fields"])
    public_types = {field["name"]: field["type"] for field in schema["fields"] if field["visibility"] == "public"}
    if type(rows) is not list or len(rows) > 2000:
        raise InvalidInput("Expected at most 2000 public rows")
    public_rows = []
    for row in tuple(rows):
        if type(row) is not dict or set(row) != allowed:
            raise InvalidInput("Supply exactly the public fields; private and unknown fields are refused")
        # Copy only named public scalars. If the caller mutates a row after the
        # key check, a newly added private key cannot enter the wire message.
        snapshot = {}
        for name in checked["public_fields"]:
            try:
                item = row[name]
            except KeyError as exc:
                raise InvalidInput("Public row changed during input preparation") from exc
            expected_type = str if public_types[name] == "text" else bool
            if type(item) is not expected_type:
                raise InvalidInput("Public fields must use their declared scalar types")
            snapshot[name] = item
        public_rows.append(snapshot)
    result = _call({"action": "run", "schema": schema, "plan": plan, "rows": public_rows})
    return tuple(tuple(trace) for trace in result["traces"])


def run_public(compiled: CompiledPlan, row: dict[str, Any]) -> tuple[str, ...]:
    """Execute one public-only record. See run_public_batch for the boundary."""
    return run_public_batch(compiled, [row])[0]
