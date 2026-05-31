from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from microcosm_core.schemas import StrictJsonError, read_json_strict


AUTHORITY_CEILING = "command_receipt_evidence_not_runtime_product_completeness"
ANTI_CLAIM = (
    "This receipt records the named public command output over real public inputs, "
    "source-faithful fixtures, or explicit negative cases; synthetic receipts are "
    "not product progress or substitutes for available real substrate."
)
FALSE_ENV_VALUES = {"0", "false", "no", "off"}
TRUE_ENV_VALUES = {"1", "true", "yes", "on"}
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
TRACKED_RECEIPTS_ROOT = (PACKAGE_ROOT / "receipts").resolve(strict=False)


def _normalize_env_flag(value: str) -> str:
    return value.strip().lower()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def receipt_writes_enabled() -> bool:
    value = os.environ.get("MICROCOSM_RECEIPT_WRITES")
    if value is None:
        value = os.environ.get("MICROCOSM_RUNTIME_RECEIPT_WRITES", "1")
    return _normalize_env_flag(value) not in FALSE_ENV_VALUES


def _env_flag_true(name: str) -> bool:
    value = os.environ.get(name)
    return value is not None and _normalize_env_flag(value) in TRUE_ENV_VALUES


def tracked_receipt_writes_enabled() -> bool:
    return _env_flag_true("MICROCOSM_TRACKED_RECEIPT_WRITES")


def _lexical_absolute(path: str | Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def is_tracked_receipt_path(path: str | Path) -> bool:
    tracked_root = _lexical_absolute(TRACKED_RECEIPTS_ROOT)
    candidate = _lexical_absolute(path)
    if _path_is_relative_to(candidate, tracked_root):
        return True

    raw_path = Path(path).expanduser()
    parent_resolved_candidate = raw_path.parent.resolve(strict=False) / raw_path.name
    return _path_is_relative_to(
        parent_resolved_candidate,
        Path(TRACKED_RECEIPTS_ROOT).resolve(strict=False),
    )


def tracked_receipt_write_blocked_under_pytest(path: str | Path) -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ and is_tracked_receipt_path(path)


def tracked_receipt_write_blocked(path: str | Path) -> bool:
    return is_tracked_receipt_path(path) and not tracked_receipt_writes_enabled()


def _read_json_object_if_exists(path: Path) -> dict[str, Any]:
    try:
        data = read_json_strict(path)
    except (FileNotFoundError, StrictJsonError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _payload_with_stable_created_at(
    path: Path, payload: dict[str, Any]
) -> dict[str, Any]:
    created_at = payload.get("created_at")
    if not isinstance(created_at, str):
        return payload

    previous = _read_json_object_if_exists(path)
    previous_created_at = previous.get("created_at")
    if not isinstance(previous_created_at, str):
        return payload

    previous_without_created_at = dict(previous)
    previous_without_created_at.pop("created_at", None)
    payload_without_created_at = dict(payload)
    payload_without_created_at.pop("created_at", None)
    if previous_without_created_at != payload_without_created_at:
        return payload

    stable_payload = dict(payload)
    stable_payload["created_at"] = previous_created_at
    return stable_payload


def _write_json_atomic_unchecked(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    payload_to_write = _payload_with_stable_created_at(target, payload)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f"{target.name}.", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload_to_write, fh, ensure_ascii=True, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def write_json_atomic(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    if not receipt_writes_enabled() or tracked_receipt_write_blocked(target):
        return
    _write_json_atomic_unchecked(target, payload)


def write_local_state_json_atomic(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    if tracked_receipt_write_blocked(target):
        return
    _write_json_atomic_unchecked(target, payload)


def base_receipt(organ_id: str, fixture_id: str, command: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": f"{organ_id}_receipt_v1",
        "receipt_id": f"{organ_id}_receipt_v1",
        "organ_id": organ_id,
        "fixture_id": fixture_id,
        "created_at": utc_now(),
        "status": "pending",
        "command": command,
        "anti_claim": ANTI_CLAIM,
        "secret_exclusion_scan": {"status": "not_run"},
        "authority_ceiling": AUTHORITY_CEILING,
        "receipt_paths": [],
    }


def write_receipt(path: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    write_json_atomic(path, payload)
    return payload
