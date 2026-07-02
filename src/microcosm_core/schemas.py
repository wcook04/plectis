"""Provides strict JSON loaders that reject duplicate keys and non-object payloads where required."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StrictJsonError(ValueError):
    """
    [ROLE]
    Raised when strict JSON parsing fails.
    - Teleology: Groups `StrictJsonError` data or behavior for `microcosm_core.schemas` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.schemas`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """


class DuplicateJsonKeyError(StrictJsonError):
    """
    [ROLE]
    Raised when a JSON object repeats a key.
    - Teleology: Groups `DuplicateJsonKeyError` data or behavior for `microcosm_core.schemas` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.schemas`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """


class StrictJsonObjectError(StrictJsonError):
    """
    [ROLE]
    Raised when a JSONL row must be an object but is not.
    - Teleology: Groups `StrictJsonObjectError` data or behavior for `microcosm_core.schemas` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.schemas`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """


def _reject_duplicate_keys(source: str):
    """
    [ACTION]
    - Teleology: Implements `_reject_duplicate_keys` for `microcosm_core.schemas` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Implements `_reject_duplicate_keys.hook` for `microcosm_core.schemas` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        seen: dict[str, Any] = {}
        for key, value in pairs:
            if key in seen:
                raise DuplicateJsonKeyError(f"{source}: duplicate JSON key {key!r}")
            seen[key] = value
        return seen

    return hook


def loads_json_strict(text: str, source: str = "<memory>") -> Any:
    """
    [ACTION]
    - Teleology: Implements `loads_json_strict` for `microcosm_core.schemas` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys(source))
    except DuplicateJsonKeyError:
        raise
    except json.JSONDecodeError as exc:
        raise StrictJsonError(f"{source}: invalid JSON: {exc}") from exc


def read_json_strict(path: str | Path) -> Any:
    """
    [ACTION]
    - Teleology: Implements `read_json_strict` for `microcosm_core.schemas` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    source = Path(path)
    return loads_json_strict(source.read_text(encoding="utf-8"), str(source))


def read_jsonl_strict(path: str | Path) -> list[object]:
    """
    [ACTION]
    - Teleology: Implements `read_jsonl_strict` for `microcosm_core.schemas` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    source = Path(path)
    rows: list[object] = []
    with source.open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            row = loads_json_strict(line, f"{source}:{line_number}")
            if not isinstance(row, dict):
                raise StrictJsonObjectError(
                    f"{source}:{line_number} is not a JSON object"
                )
            rows.append(row)
    return rows
