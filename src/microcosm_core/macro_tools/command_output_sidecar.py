"""
Implements macro tools command output sidecar for the public Plectis package.

Callers enter through `maybe_route_to_sidecar`; constants such as `RECEIPT_KIND`,
`RECEIPT_SCHEMA_VERSION`, `SIDECAR_ROOT`, `ENV_VAR`, and 2 more pin local fixture names;
dependencies include `hashlib`, `json`, `os`, `datetime`, and 2 more. The helpers are
invoked explicitly by CLI or fixture code; importing the module only declares the available
machinery.
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
    Compute safe surface from `surface`.

    Inputs are `surface`; notable helpers are `join` and `isalnum`.
    """
    return "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in surface) or "unknown"


def _payload_bytes(payload: Any) -> int:
    """
    Return payload bytes for the macro tools command output sidecar flow.

    Inputs are `payload`; notable helpers are `encode` and `dumps`.
    """
    try:
        return len(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8"))
    except TypeError:
        return len(json.dumps(str(payload), ensure_ascii=False).encode("utf-8"))


def _summary_for_payload(payload: Any) -> dict[str, Any]:
    """
    Serialize `microcosm_core.macro_tools.command_output_sidecar._summary_for_payload` into
    the payload shape expected by macro tools command output sidecar.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
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
    Read read threshold for `microcosm_core.macro_tools.command_output_sidecar`.

    Input comes from the supplied source; malformed or missing data follows the exceptions
    and checks visible in the body.
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
    Return whether inline override active holds for the macro tools command output sidecar
    flow.

    The result is derived from the caller-supplied state with `get`, `lower`, and `strip`;
    failing evidence is returned or raised exactly where the body says so.
    """
    raw = os.environ.get(INLINE_OVERRIDE_ENV_VAR)
    return raw is not None and raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_threshold(surface: str) -> tuple[int | None, str]:
    """
    Derive resolve threshold without touching module import state.

    Inputs are `surface`; notable helpers are `_read_threshold` and `get`.
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
    Serialize `microcosm_core.macro_tools.command_output_sidecar.maybe_route_to_sidecar`
    into the payload shape expected by macro tools command output sidecar.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
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
