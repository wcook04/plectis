from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from microcosm_core.schemas import StrictJsonError, read_json_strict


AUTHORITY_CEILING = "command_receipt_evidence_not_runtime_product_completeness"
PUBLIC_PATH_POLICY_ID = "microcosm_public_path_secret_policy_v1"
PUBLIC_RECEIPT_PATH_NORMALIZATION_SCHEMA = (
    "microcosm_public_receipt_path_normalization_v1"
)
ANTI_CLAIM = (
    "This receipt records the named public command output over real public inputs, "
    "source-faithful fixtures, or explicit negative cases; synthetic receipts are "
    "not product progress or substitutes for available real substrate."
)
FALSE_ENV_VALUES = {"0", "false", "no", "off"}
TRUE_ENV_VALUES = {"1", "true", "yes", "on"}
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
TRACKED_RECEIPTS_ROOT = (PACKAGE_ROOT / "receipts").resolve(strict=False)
PRIVATE_REPO_HOME_RE = re.compile(
    r"/Users/[^/\s\"']+/src/ai_workflow(?P<suffix>[^\s\"']*)"
)
PRIVATE_HOME_RE = re.compile(r"/Users/[^/\s\"']+(?P<suffix>[^\s\"']*)")
PRIVATE_TMP_RE = re.compile(r"/private/tmp(?P<suffix>[^\s\"']*)")
REPO_ROOT_FRAGMENT_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])src/ai_workflow(?P<suffix>[^\s\"']*)"
)


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


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _replacement_row(
    *,
    original: str,
    replacement: str,
    treatment_class: str,
    field_path: str,
) -> dict[str, str]:
    return {
        "original_sha256": _sha256_text(original),
        "replacement": replacement,
        "treatment_class": treatment_class,
        "field_path": field_path,
    }


def _normalize_public_receipt_string(
    value: str, *, field_path: str, replacements: list[dict[str, str]]
) -> str:
    def repo_home_repl(match: re.Match[str]) -> str:
        suffix = match.group("suffix") or ""
        replacement = f"<repo-root>{suffix}"
        replacements.append(
            _replacement_row(
                original=match.group(0),
                replacement=replacement,
                treatment_class="repo_root_private_home_path_transform",
                field_path=field_path,
            )
        )
        return replacement

    def private_home_repl(match: re.Match[str]) -> str:
        replacement = "<private-home-path>"
        replacements.append(
            _replacement_row(
                original=match.group(0),
                replacement=replacement,
                treatment_class="private_home_path_transform",
                field_path=field_path,
            )
        )
        return replacement

    def private_tmp_repl(match: re.Match[str]) -> str:
        suffix = match.group("suffix") or ""
        replacement = f"<host-temp>{suffix}"
        replacements.append(
            _replacement_row(
                original=match.group(0),
                replacement=replacement,
                treatment_class="host_temp_path_transform",
                field_path=field_path,
            )
        )
        return replacement

    def repo_fragment_repl(match: re.Match[str]) -> str:
        suffix = match.group("suffix") or ""
        replacement = f"<repo-root>{suffix}"
        replacements.append(
            _replacement_row(
                original=match.group(0),
                replacement=replacement,
                treatment_class="repo_root_fragment_transform",
                field_path=field_path,
            )
        )
        return replacement

    normalized = PRIVATE_REPO_HOME_RE.sub(repo_home_repl, value)
    normalized = PRIVATE_HOME_RE.sub(private_home_repl, normalized)
    normalized = PRIVATE_TMP_RE.sub(private_tmp_repl, normalized)
    return REPO_ROOT_FRAGMENT_RE.sub(repo_fragment_repl, normalized)


def _normalize_public_receipt_value(
    value: Any, *, field_path: str, replacements: list[dict[str, str]]
) -> Any:
    if isinstance(value, str):
        return _normalize_public_receipt_string(
            value, field_path=field_path, replacements=replacements
        )
    if isinstance(value, list):
        return [
            _normalize_public_receipt_value(
                item, field_path=f"{field_path}[{index}]", replacements=replacements
            )
            for index, item in enumerate(value)
        ]
    if isinstance(value, tuple):
        return [
            _normalize_public_receipt_value(
                item, field_path=f"{field_path}[{index}]", replacements=replacements
            )
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        return {
            key: _normalize_public_receipt_value(
                item,
                field_path=f"{field_path}.{key}" if field_path else str(key),
                replacements=replacements,
            )
            for key, item in value.items()
            if key != "public_path_sanitization"
        }
    return value


def normalize_public_receipt_paths(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a receipt payload with host-local path strings made portable.

    Public receipts can preserve provenance shape, command intent, and artifact
    names without re-emitting private home roots, private temp roots, or the
    macro repo's host-local path fragment. Original strings are recorded only as
    hashes plus treatment classes so future builders can audit the transform.
    """

    replacements: list[dict[str, str]] = []
    normalized = _normalize_public_receipt_value(
        payload, field_path="", replacements=replacements
    )
    if not isinstance(normalized, dict) or not replacements:
        return normalized

    normalized["public_path_sanitization"] = {
        "schema_version": PUBLIC_RECEIPT_PATH_NORMALIZATION_SCHEMA,
        "policy_id": PUBLIC_PATH_POLICY_ID,
        "status": "transformed",
        "replacement_count": len(replacements),
        "transform_classes": sorted({row["treatment_class"] for row in replacements}),
        "replacements": replacements,
        "body_text_boundary": (
            "Receipt path normalization records hashed originals, replacements, "
            "field paths, and treatment classes only; private host path strings "
            "are not public receipt evidence."
        ),
    }
    return normalized


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
    payload_to_write = _payload_with_stable_created_at(
        target, normalize_public_receipt_paths(payload)
    )
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
