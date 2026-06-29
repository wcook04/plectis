"""
Sidecar containment for heavy command outputs.

Concurrent agents on first-contact surfaces should never see an unbounded JSON
payload land directly in their tool host. This module defines one reusable
shape: a `command_output_receipt` envelope that records a small summary inline
and points at a sidecar path on disk for the full payload.

Default policy (heavy-surface tier):
- `navigation_metabolism.full` (and any surface registered in DEFAULT_THRESHOLDS)
  emits a sidecar receipt by default once the payload exceeds the surface's
  default cap. This is a safety default for the original concurrent-agent
  buffered-output incident.

Per-call overrides (in priority order):
1. `AIW_COMMAND_OUTPUT_INLINE=1` forces inline emit (never sidecar).
2. `AIW_COMMAND_OUTPUT_SIDECAR_BYTES=N` overrides the threshold for any surface
   (set to `0` to force sidecar regardless of size).
3. Default heavy-surface caps via `DEFAULT_THRESHOLDS`.
4. No threshold set and not a heavy surface → inline.

[PURPOSE]
- Teleology: Exposes `microcosm_core.macro_tools.command_output_sidecar` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: RECEIPT_KIND, RECEIPT_SCHEMA_VERSION, SIDECAR_ROOT, ENV_VAR, INLINE_OVERRIDE_ENV_VAR, DEFAULT_THRESHOLDS, maybe_route_to_sidecar
- Reads: call arguments, module constants, imported helpers, environment variables.
- Writes: return values, declared filesystem outputs and any explicit side effects performed by exported entry points.
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

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

RECEIPT_KIND = "command_output_receipt"
RECEIPT_SCHEMA_VERSION = "command_output_receipt_v0"
SIDECAR_ROOT = Path("state") / "command_outputs"
ENV_VAR = "AIW_COMMAND_OUTPUT_SIDECAR_BYTES"
INLINE_OVERRIDE_ENV_VAR = "AIW_COMMAND_OUTPUT_INLINE"

# Heavy-surface defaults that opt into sidecar containment without env opt-in.
# Keep narrow: only known-rich audit/full surfaces. Quick/control surfaces stay inline.
DEFAULT_THRESHOLDS: Mapping[str, int] = {
    "navigation_metabolism.full": 24 * 1024,
}


def _safe_surface(surface: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_safe_surface` for `microcosm_core.macro_tools.command_output_sidecar` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in surface) or "unknown"


def _payload_bytes(payload: Any) -> int:
    """
    [ACTION]
    - Teleology: Implements `_payload_bytes` for `microcosm_core.macro_tools.command_output_sidecar` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        return len(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8"))
    except TypeError:
        return len(json.dumps(str(payload), ensure_ascii=False).encode("utf-8"))


def _summary_for_payload(payload: Any) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_summary_for_payload` for `microcosm_core.macro_tools.command_output_sidecar` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, Mapping):
        return {"top_keys": [], "kind": None}
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else None
    return {
        "top_keys": sorted(payload.keys())[:24],
        "kind": payload.get("kind"),
        "schema_version": payload.get("schema_version"),
        "summary": dict(summary) if summary is not None else None,
    }


def _read_threshold() -> int | None:
    """
    [ACTION]
    - Teleology: Implements `_read_threshold` for `microcosm_core.macro_tools.command_output_sidecar` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
    - Writes: return values.
    """
    raw = os.environ.get(ENV_VAR)
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return max(0, value)


def _inline_override_active() -> bool:
    """
    [ACTION]
    - Teleology: Implements `_inline_override_active` for `microcosm_core.macro_tools.command_output_sidecar` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, environment variables.
    - Writes: return values.
    """
    raw = os.environ.get(INLINE_OVERRIDE_ENV_VAR)
    return raw is not None and raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_threshold(surface: str) -> tuple[int | None, str]:
    """
    [ACTION]
    - Teleology: Implements `_resolve_threshold` for `microcosm_core.macro_tools.command_output_sidecar` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    explicit = _read_threshold()
    if explicit is not None:
        return explicit, "env_override"
    default_cap = DEFAULT_THRESHOLDS.get(surface)
    if default_cap is not None:
        return default_cap, "heavy_surface_default"
    return None, "inline_default"


def maybe_route_to_sidecar(
    payload: Any,
    *,
    surface: str,
    repo_root: Path | str,
) -> dict[str, Any] | None:
    """
    [ACTION]
    Return a receipt envelope when policy mandates sidecar containment.

    Resolution order (first match wins):
      1. AIW_COMMAND_OUTPUT_INLINE=1 → never sidecar (returns None).
      2. AIW_COMMAND_OUTPUT_SIDECAR_BYTES=N → that threshold for any surface.
      3. DEFAULT_THRESHOLDS[surface] → default cap for known heavy surfaces.
      4. Otherwise → inline (returns None).
    - Teleology: Implements `maybe_route_to_sidecar` for `microcosm_core.macro_tools.command_output_sidecar` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    if _inline_override_active():
        return None
    threshold, threshold_source = _resolve_threshold(surface)
    if threshold is None:
        return None
    payload_bytes = _payload_bytes(payload)
    if payload_bytes <= threshold and threshold > 0:
        return None
    root = Path(repo_root)
    surface_safe = _safe_surface(surface)
    payload_text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n"
    digest = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()[:12]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sidecar_dir = root / SIDECAR_ROOT / surface_safe
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    sidecar_path = sidecar_dir / f"{timestamp}_{digest}.json"
    tmp = sidecar_path.with_name(f".{sidecar_path.name}.tmp")
    tmp.write_text(payload_text, encoding="utf-8")
    tmp.replace(sidecar_path)
    rel_path = sidecar_path.relative_to(root).as_posix()
    return {
        "kind": RECEIPT_KIND,
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "status": "written_to_sidecar",
        "surface": surface,
        "output_path": rel_path,
        "output_bytes": payload_bytes,
        "policy": {
            "trigger_source": threshold_source,
            "threshold_bytes": threshold,
            "inline_override": f"{INLINE_OVERRIDE_ENV_VAR}=1",
            "explicit_threshold_env": ENV_VAR,
        },
        "payload_summary": _summary_for_payload(payload),
        "read_next": [
            f"./repo-python kernel.py --command-output {rel_path} --band summary",
            f"./repo-python kernel.py --command-output {rel_path} --band card",
            f"./repo-python kernel.py --command-output {rel_path} --band full",
        ],
    }


__all__ = [
    "RECEIPT_KIND",
    "RECEIPT_SCHEMA_VERSION",
    "ENV_VAR",
    "SIDECAR_ROOT",
    "maybe_route_to_sidecar",
]
