"""Small JSON receipt helpers for the public microcosm root."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, target)
    return target


def make_receipt(
    *,
    receipt_type: str,
    status: str,
    command: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": "microcosm_receipt_v0",
        "receipt_type": receipt_type,
        "status": status,
        "generated_at": utc_now(),
        "command": command,
        "authority_ceiling": "receipt_is_evidence_not_source_authority",
    }
    if payload:
        receipt.update(payload)
    return receipt

