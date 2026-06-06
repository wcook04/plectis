"""
Small persistent cache for read-mostly command nodes.

This is intentionally narrower than a build system and distinct from
``swr_cache``: ``swr_cache`` is process-local server memory with background
refresh, while this module is a persistent cross-process CLI cache with file
locks. It gives hot command surfaces one reusable primitive: declare a node id,
a key, a small input manifest, and a short stale-ok window, then let concurrent
processes singleflight the rebuild.
"""
from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Hashable, Mapping, Sequence

SCHEMA_VERSION = "command_node_cache_v1"
DISABLE_ENV_VAR = "AIW_COMMAND_CACHE"
REFRESH_ENV_VAR = "AIW_COMMAND_CACHE_REFRESH"
_FALSE_VALUES = {"0", "false", "no", "off", "disable", "disabled"}
_TRUE_VALUES = {"1", "true", "yes", "on", "refresh", "force"}
_MANIFEST_EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _key_hash(key: Hashable | Mapping[str, Any] | Sequence[Any]) -> str:
    return hashlib.sha256(_stable_json(key).encode("utf-8")).hexdigest()[:24]


def _safe_node_id(node_id: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in node_id)


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _env_false(name: str) -> bool:
    value = os.environ.get(name)
    return value is not None and value.strip().lower() in _FALSE_VALUES


def _env_true(name: str) -> bool:
    value = os.environ.get(name)
    return value is not None and value.strip().lower() in _TRUE_VALUES


def _is_command_cache_path(path: Path, root: Path) -> bool:
    rel_parts = Path(_rel(path, root)).parts
    return len(rel_parts) >= 2 and rel_parts[:2] == ("state", "command_cache")


def _directory_manifest(path: Path, root: Path) -> dict[str, Any]:
    child_count = 0
    total_size = 0
    max_mtime_ns = 0
    digest = hashlib.sha256()
    try:
        walker = os.walk(path)
        for current_root, dirnames, filenames in walker:
            current = Path(current_root)
            dirnames[:] = sorted(
                name
                for name in dirnames
                if name not in _MANIFEST_EXCLUDED_DIRS
                and not _is_command_cache_path(current / name, root)
            )
            for filename in sorted(filenames):
                child = current / filename
                if _is_command_cache_path(child, root):
                    continue
                try:
                    stat = child.stat()
                except OSError:
                    continue
                if not child.is_file():
                    continue
                child_count += 1
                total_size += stat.st_size
                max_mtime_ns = max(max_mtime_ns, stat.st_mtime_ns)
                digest.update(_rel(child, root).encode("utf-8"))
                digest.update(b"\0")
                digest.update(str(stat.st_size).encode("ascii"))
                digest.update(b"\0")
                digest.update(str(stat.st_mtime_ns).encode("ascii"))
                digest.update(b"\n")
    except OSError:
        return {
            "path": _rel(path, root),
            "exists": False,
            "manifest_kind": "directory_unreadable",
        }
    return {
        "path": _rel(path, root),
        "exists": True,
        "is_dir": True,
        "manifest_kind": "directory_recursive",
        "child_file_count": child_count,
        "total_size": total_size,
        "max_child_mtime_ns": max_mtime_ns,
        "fingerprint": digest.hexdigest()[:32],
    }


def _manifest(root: Path, input_paths: Sequence[str | Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in input_paths:
        path = Path(raw)
        if not path.is_absolute():
            path = root / path
        try:
            stat = path.stat()
        except OSError:
            rows.append({"path": _rel(path, root), "exists": False})
            continue
        if path.is_dir():
            rows.append(_directory_manifest(path, root))
            continue
        rows.append(
            {
                "path": _rel(path, root),
                "exists": True,
                "is_dir": path.is_dir(),
                "manifest_kind": "file_stat",
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        )
    return rows


def _cache_paths(root: Path, node_id: str, key_hash: str) -> tuple[Path, Path]:
    cache_root = root / "state" / "command_cache" / _safe_node_id(node_id)
    return cache_root / f"{key_hash}.json", cache_root / f"{key_hash}.lock"


def _load_envelope(path: Path) -> dict[str, Any] | None:
    try:
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _cache_status(
    *,
    node_id: str,
    cache_path: Path,
    repo_root: Path,
    status: str,
    reason: str,
    envelope: Mapping[str, Any] | None = None,
    freshness_policy: str = "ttl_plus_input_manifest",
    dynamic_inputs_manifested: bool = True,
) -> dict[str, Any]:
    created = float((envelope or {}).get("created_at_epoch_s") or 0)
    age_s = max(0.0, time.time() - created) if created else None
    return {
        "schema_version": SCHEMA_VERSION,
        "node_id": node_id,
        "status": status,
        "reason": reason,
        "cache_path": _rel(cache_path, repo_root),
        "age_s": round(age_s, 3) if age_s is not None else None,
        "ttl_s": (envelope or {}).get("ttl_s"),
        "freshness_policy": freshness_policy,
        "dynamic_inputs_manifested": dynamic_inputs_manifested,
    }


def _valid_cached_payload(
    *,
    envelope: Mapping[str, Any] | None,
    manifest: Sequence[Mapping[str, Any]],
    ttl_s: float,
) -> tuple[Any | None, str]:
    if not envelope:
        return None, "missing"
    if envelope.get("schema_version") != SCHEMA_VERSION:
        return None, "schema_mismatch"
    created = float(envelope.get("created_at_epoch_s") or 0)
    if ttl_s > 0 and (time.time() - created) > ttl_s:
        return None, "expired"
    if list(envelope.get("input_manifest") or []) != list(manifest):
        return None, "input_manifest_changed"
    if "payload" not in envelope:
        return None, "payload_missing"
    return copy.deepcopy(envelope.get("payload")), "hit"


def _write_envelope(path: Path, envelope: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def cached_command_node(
    repo_root: Path | str,
    *,
    node_id: str,
    key: Hashable | Mapping[str, Any] | Sequence[Any],
    input_paths: Sequence[str | Path] = (),
    ttl_s: float = 60.0,
    builder: Callable[[], Any],
    freshness_policy: str = "ttl_plus_input_manifest",
    dynamic_inputs_manifested: bool = True,
    force_refresh: bool = False,
) -> tuple[Any, dict[str, Any]]:
    """
    Return (payload, cache_status) for one command node.

    The first cache miss computes under an exclusive file lock. Other processes
    asking for the same node/key wait on that lock, then consume the sidecar
    instead of stampeding the same builder.

    `freshness_policy` and `dynamic_inputs_manifested` are honest labels, not
    enforcement: callers whose builder reads dynamic state outside the input
    manifest (session JSONL, event store, runtime telemetry) should pass
    `freshness_policy="ttl_for_dynamic_session_state_plus_static_source_manifest"`
    and `dynamic_inputs_manifested=False`. Cache freshness in that case is
    bounded by `ttl_s`, not by the manifest digest.
    """
    root = Path(repo_root)
    key_hash = _key_hash(key)
    cache_path, lock_path = _cache_paths(root, node_id, key_hash)
    manifest = _manifest(root, input_paths)

    def _status(
        *,
        status: str,
        reason: str,
        envelope: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return _cache_status(
            node_id=node_id,
            cache_path=cache_path,
            repo_root=root,
            status=status,
            reason=reason,
            envelope=envelope,
            freshness_policy=freshness_policy,
            dynamic_inputs_manifested=dynamic_inputs_manifested,
        )

    if _env_false(DISABLE_ENV_VAR):
        payload = builder()
        return copy.deepcopy(payload), _status(
            status="disabled_built",
            reason=f"{DISABLE_ENV_VAR}=0",
            envelope={"created_at_epoch_s": time.time(), "ttl_s": ttl_s},
        )

    env_force_refresh = _env_true(REFRESH_ENV_VAR)
    force_refresh_reason = (
        f"{REFRESH_ENV_VAR}=1"
        if env_force_refresh
        else "force_refresh_requested"
        if force_refresh
        else None
    )

    envelope = _load_envelope(cache_path)
    cached, reason = (
        (None, force_refresh_reason)
        if force_refresh_reason
        else _valid_cached_payload(envelope=envelope, manifest=manifest, ttl_s=ttl_s)
    )
    if cached is not None:
        return cached, _status(status="hit", reason=reason, envelope=envelope)

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        envelope = _load_envelope(cache_path)
        cached, locked_reason = (
            (None, force_refresh_reason)
            if force_refresh_reason
            else _valid_cached_payload(
                envelope=envelope,
                manifest=manifest,
                ttl_s=ttl_s,
            )
        )
        if cached is not None:
            return cached, _status(status="waited_hit", reason=locked_reason, envelope=envelope)
        payload = builder()
        envelope = {
            "schema_version": SCHEMA_VERSION,
            "node_id": node_id,
            "key_hash": key_hash,
            "created_at": _utc_now(),
            "created_at_epoch_s": time.time(),
            "ttl_s": ttl_s,
            "input_manifest": list(manifest),
            "payload": payload,
        }
        _write_envelope(cache_path, envelope)
        return copy.deepcopy(payload), _status(status="miss_built", reason=reason, envelope=envelope)


def peek_cached_command_node(
    repo_root: Path | str,
    *,
    node_id: str,
    key: Hashable | Mapping[str, Any] | Sequence[Any],
    input_paths: Sequence[str | Path] = (),
    ttl_s: float | None = None,
    freshness_policy: str = "stale_ok_cache_peek",
    dynamic_inputs_manifested: bool = False,
    validate_input_manifest: bool = True,
) -> tuple[Any | None, dict[str, Any]]:
    """Read a command-node cache payload without rebuilding or taking a lock.

    This is for first-contact diagnostic packets that must stay fast even when
    their richer evidence node has expired. The status makes the stale/deferred
    posture explicit; authoritative checks should use `cached_command_node`.
    Callers can pass `input_paths` and `ttl_s` when a stale-ok peek should still
    refuse cache entries whose declared static inputs no longer match.
    """
    root = Path(repo_root)
    cache_path, _ = _cache_paths(root, node_id, _key_hash(key))
    envelope = _load_envelope(cache_path)
    if not envelope or "payload" not in envelope:
        return None, _cache_status(
            node_id=node_id,
            cache_path=cache_path,
            repo_root=root,
            status="deferred_missing_cache",
            reason="quick_profile_does_not_rebuild_expensive_node",
            envelope=envelope,
            freshness_policy=freshness_policy,
            dynamic_inputs_manifested=dynamic_inputs_manifested,
        )
    if input_paths or ttl_s is not None:
        if not validate_input_manifest:
            if envelope.get("schema_version") != SCHEMA_VERSION:
                return None, _cache_status(
                    node_id=node_id,
                    cache_path=cache_path,
                    repo_root=root,
                    status="deferred_stale_cache",
                    reason="schema_mismatch",
                    envelope=envelope,
                    freshness_policy=freshness_policy,
                    dynamic_inputs_manifested=dynamic_inputs_manifested,
                )
            created = float(envelope.get("created_at_epoch_s") or 0)
            if ttl_s is not None and ttl_s > 0 and (time.time() - created) > ttl_s:
                return None, _cache_status(
                    node_id=node_id,
                    cache_path=cache_path,
                    repo_root=root,
                    status="deferred_stale_cache",
                    reason="expired",
                    envelope=envelope,
                    freshness_policy=freshness_policy,
                    dynamic_inputs_manifested=dynamic_inputs_manifested,
                )
            return copy.deepcopy(envelope.get("payload")), _cache_status(
                node_id=node_id,
                cache_path=cache_path,
                repo_root=root,
                status="stale_ok_hit",
                reason="cache_valid_for_ttl_manifest_not_checked",
                envelope=envelope,
                freshness_policy=freshness_policy,
                dynamic_inputs_manifested=dynamic_inputs_manifested,
            )
        manifest = _manifest(root, input_paths)
        cached, reason = _valid_cached_payload(
            envelope=envelope,
            manifest=manifest,
            ttl_s=0.0 if ttl_s is None else ttl_s,
        )
        if cached is None:
            return None, _cache_status(
                node_id=node_id,
                cache_path=cache_path,
                repo_root=root,
                status="deferred_stale_cache",
                reason=reason,
                envelope=envelope,
                freshness_policy=freshness_policy,
                dynamic_inputs_manifested=dynamic_inputs_manifested,
            )
        return cached, _cache_status(
            node_id=node_id,
            cache_path=cache_path,
            repo_root=root,
            status="stale_ok_hit",
            reason="cache_valid_for_declared_inputs",
            envelope=envelope,
            freshness_policy=freshness_policy,
            dynamic_inputs_manifested=dynamic_inputs_manifested,
        )
    return copy.deepcopy(envelope.get("payload")), _cache_status(
        node_id=node_id,
        cache_path=cache_path,
        repo_root=root,
        status="stale_ok_hit",
        reason="quick_profile_uses_stale_cache_without_rebuild",
        envelope=envelope,
        freshness_policy=freshness_policy,
        dynamic_inputs_manifested=dynamic_inputs_manifested,
    )


__all__ = ["SCHEMA_VERSION", "cached_command_node", "peek_cached_command_node"]
