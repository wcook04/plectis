#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Build a stable, pytest-nodeid-based inventory of every test in
  system/server/tests/. The inventory is the unit of execution for the impact
  selector — never -k expressions. Per std_test_inventory.json (M1).
- Mechanism: Run pytest with --collect-only via a tiny in-process plugin that
  inspects session.items directly. Writes one canonical projection plus one
  lattice event. Idempotent: same content_digest → operation.skipped.

[INTERFACE]
- Exports: collect_inventory, write_inventory_projection, main.
- Reads: system/server/tests/**/*.py (collection only; no execution).
- Writes: state/testing/test_inventory.json,
  state/lattice/events/ledger.jsonl.

[CLI]
  python3 test_inventory.py --write           # persist only when sources are stale
  python3 test_inventory.py --write --force-refresh  # rebuild and persist
  python3 test_inventory.py --json            # print to stdout, do not write
  python3 test_inventory.py --check           # fast-fail if existing projection is stale
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = REPO_ROOT / "system" / "server" / "tests"
INVENTORY_PATH = REPO_ROOT / "state" / "testing" / "test_inventory.json"
PLUGIN_PATH = Path(__file__).resolve().parent / "_test_inventory_plugin.py"
SOURCE_FINGERPRINT_SCHEMA = "test_inventory_source_fingerprint_v1"

if __package__ in (None, ""):
    sys.path.insert(0, str(REPO_ROOT / "tools" / "meta" / "factory"))

import append_lattice_event as ev_helper  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _elapsed_s(started: float) -> float:
    return round(time.perf_counter() - started, 3)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()[:16]}"


def _sha256_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _inventory_source_paths() -> list[Path]:
    paths: list[Path] = []
    paths.extend(sorted(TEST_ROOT.rglob("test_*.py")))
    paths.extend(sorted(TEST_ROOT.rglob("conftest.py")))
    for path in (
        REPO_ROOT / "pytest.ini",
        Path(__file__).resolve(),
        PLUGIN_PATH,
    ):
        if path.exists():
            paths.append(path)
    return paths


def _fingerprint_row_stats(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def _cached_source_fingerprint_rows() -> dict[str, dict[str, Any]]:
    existing = _load_existing_inventory()
    if not isinstance(existing, dict):
        return {}
    fingerprint = existing.get("source_fingerprint")
    if not isinstance(fingerprint, dict):
        return {}
    rows = fingerprint.get("paths")
    if not isinstance(rows, list):
        return {}
    cached: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        path = row.get("path")
        digest = row.get("digest")
        if isinstance(path, str) and isinstance(digest, str):
            cached[path] = row
    return cached


def build_source_fingerprint() -> dict[str, Any]:
    """Hash inventory inputs so --check can avoid full pytest collection."""
    cached_rows = _cached_source_fingerprint_rows()
    rows: list[dict[str, Any]] = []
    cache_hit_count = 0
    cache_miss_count = 0
    for path in _inventory_source_paths():
        try:
            rel = str(path.resolve().relative_to(REPO_ROOT))
        except ValueError:
            rel = str(path)
        stats = _fingerprint_row_stats(path)
        cached = cached_rows.get(rel)
        if (
            isinstance(cached, dict)
            and cached.get("size") == stats["size"]
            and cached.get("mtime_ns") == stats["mtime_ns"]
            and isinstance(cached.get("digest"), str)
        ):
            digest = cached["digest"]
            cache_hit_count += 1
        else:
            digest = _sha256_file(path)
            cache_miss_count += 1
        rows.append({"path": rel, "digest": digest, **stats})
    canonical_rows = [
        {"path": row["path"], "digest": row["digest"]}
        for row in rows
    ]
    canonical = json.dumps(canonical_rows, sort_keys=True, separators=(",", ":"))
    return {
        "schema": SOURCE_FINGERPRINT_SCHEMA,
        "digest": _sha256_text(canonical),
        "path_count": len(rows),
        "paths": rows,
        "cache": {
            "stat_key": "size_mtime_ns",
            "hit_count": cache_hit_count,
            "miss_count": cache_miss_count,
            "source": str(INVENTORY_PATH.relative_to(REPO_ROOT)),
        },
    }


def _load_existing_inventory() -> dict[str, Any] | None:
    if not INVENTORY_PATH.exists():
        return None
    try:
        return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _fingerprints_match(existing: dict[str, Any] | None, current: dict[str, Any]) -> bool:
    if not isinstance(existing, dict):
        return False
    return (
        existing.get("schema") == current.get("schema")
        and existing.get("digest") == current.get("digest")
        and existing.get("path_count") == current.get("path_count")
    )


def source_fingerprints_match(existing: dict[str, Any] | None, current: dict[str, Any]) -> bool:
    """Public freshness contract for selector consumers."""
    return _fingerprints_match(existing, current)


def _fresh_existing_inventory(source_fingerprint: dict[str, Any]) -> dict[str, Any] | None:
    existing = _load_existing_inventory()
    if existing is None:
        return None
    if not source_fingerprints_match(existing.get("source_fingerprint"), source_fingerprint):
        return None
    return existing


def classify_pytest_collect_result(exit_code: int, collection_errors: list[dict[str, Any]] | None = None) -> str:
    """Classify pytest collection exits for the inventory projection.

    Pytest's code 5 is a stable public "no tests collected" signal; it is not
    the same condition as an import/collection failure. Code 1 during
    collection is treated as collection_failed when explicit errors are
    present, otherwise failed.
    """
    errors = collection_errors or []
    if exit_code == 0:
        return "passed"
    if exit_code == 5:
        return "no_tests_collected"
    if exit_code != 0 and errors:
        return "collection_failed"
    if exit_code in (1, 2, 3, 4):
        return "failed"
    return "unknown"


def _ensure_plugin() -> None:
    if PLUGIN_PATH.exists():
        return
    PLUGIN_PATH.write_text(
        '"""Tiny pytest plugin that dumps session.items as JSON. Loaded via -p."""\n'
        "import json, os, sys\n"
        "_OUT = os.environ.get('LATTICE_TEST_INVENTORY_OUT')\n"
        "def pytest_collection_modifyitems(config, items):\n"
        "    rows = []\n"
        "    for item in items:\n"
        "        try:\n"
        "            markers = sorted({m.name for m in item.iter_markers()})\n"
        "        except Exception:\n"
        "            markers = []\n"
        "        nodeid = item.nodeid\n"
        "        path = str(item.path) if hasattr(item, 'path') else getattr(item, 'fspath', '')\n"
        "        rows.append({'nodeid': nodeid, 'path': str(path), 'name': item.name, 'markers': markers, 'parametrized': '[' in nodeid})\n"
        "    if _OUT:\n"
        "        with open(_OUT, 'w', encoding='utf-8') as f:\n"
        "            json.dump(rows, f)\n",
        encoding="utf-8",
    )


def _pytest_collection_env(plugin_out: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["LATTICE_TEST_INVENTORY_OUT"] = str(plugin_out)
    env["PYTHONPATH"] = (
        str(PLUGIN_PATH.parent) + os.pathsep + env.get("PYTHONPATH", "")
    )
    if not env.get("LATTICE_TEST_INVENTORY_ENABLE_PLUGIN_AUTOLOAD"):
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return env


def _collection_targets(test_paths: Sequence[Path] | None = None) -> list[str]:
    if test_paths is None:
        return [str(TEST_ROOT.relative_to(REPO_ROOT))]
    targets: list[str] = []
    for path in sorted({Path(p).resolve() for p in test_paths}):
        try:
            rel = str(path.relative_to(REPO_ROOT))
        except ValueError as exc:
            raise ValueError(f"inventory collection target outside repo: {path}") from exc
        targets.append(rel)
    return targets


def collect_inventory(
    source_fingerprint: dict[str, Any] | None = None,
    *,
    test_paths: Sequence[Path] | None = None,
) -> dict[str, Any]:
    total_started = time.perf_counter()
    _ensure_plugin()
    plugin_out = REPO_ROOT / "state" / "testing" / "_collect_dump.json"
    plugin_out.parent.mkdir(parents=True, exist_ok=True)
    if plugin_out.exists():
        plugin_out.unlink()
    cmd = [
        sys.executable,
        "-m", "pytest",
        *_collection_targets(test_paths),
        "--collect-only",
        "-q",
        "--no-header",
        "-p", f"no:cacheprovider",
        "-p", f"_test_inventory_plugin",
    ]
    env = _pytest_collection_env(plugin_out)
    collect_started = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    duration_s = _elapsed_s(collect_started)
    postprocess_started = time.perf_counter()

    rows: list[dict[str, Any]] = []
    if plugin_out.exists():
        try:
            rows = json.loads(plugin_out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rows = []

    pytest_version = "unknown"
    for line in (proc.stdout + "\n" + proc.stderr).splitlines():
        if line.startswith("pytest "):
            pytest_version = line.split()[1]
            break

    file_digest_cache: dict[str, str] = {}

    def _path_digest(p: str) -> str:
        if p in file_digest_cache:
            return file_digest_cache[p]
        try:
            digest = _sha256_file(Path(p))
        except OSError:
            digest = "sha256:unreadable"
        file_digest_cache[p] = digest
        return digest

    test_items: list[dict[str, Any]] = []
    file_to_items: dict[str, list[str]] = {}
    for r in rows:
        path_str = r.get("path") or ""
        try:
            rel = str(Path(path_str).resolve().relative_to(REPO_ROOT))
        except ValueError:
            rel = path_str
        digest = _path_digest(path_str) if path_str else "sha256:unreadable"
        test_items.append({
            "nodeid": r["nodeid"],
            "path": rel,
            "name": r.get("name", ""),
            "markers": r.get("markers", []),
            "parametrized": bool(r.get("parametrized", False)),
            "file_digest": digest,
        })
        file_to_items.setdefault(rel, []).append(r["nodeid"])

    test_files: list[dict[str, Any]] = []
    for rel, ids in sorted(file_to_items.items()):
        try:
            digest = _sha256_file(REPO_ROOT / rel)
        except OSError:
            digest = "sha256:unreadable"
        test_files.append({
            "path": rel,
            "digest": digest,
            "item_count": len(ids),
        })

    collection_errors: list[dict[str, Any]] = []
    result_classification = classify_pytest_collect_result(proc.returncode, collection_errors)

    canonical_blob = json.dumps(
        {"test_files": test_files, "test_items": test_items, "collection_errors": collection_errors},
        sort_keys=True,
        separators=(",", ":"),
    )
    inventory_digest = _sha256_text(canonical_blob)
    postprocess_s = _elapsed_s(postprocess_started)

    fingerprint_started = time.perf_counter()
    resolved_source_fingerprint = source_fingerprint or build_source_fingerprint()
    source_fingerprint_s = _elapsed_s(fingerprint_started)

    inventory = {
        "schema_version": 1,
        "generated_at": _now(),
        "pytest": {
            "version": pytest_version,
            "collect_command": cmd[1:],
            "plugin_autoload": (
                "enabled_by_LATTICE_TEST_INVENTORY_ENABLE_PLUGIN_AUTOLOAD"
                if env.get("LATTICE_TEST_INVENTORY_ENABLE_PLUGIN_AUTOLOAD")
                else "disabled"
            ),
            "exit_code": proc.returncode,
            "duration_s": duration_s,
            "result_classification": result_classification,
        },
        "summary": {
            "test_file_count": len(test_files),
            "test_item_count": len(test_items),
            "collection_error_count": len(collection_errors),
            "inventory_digest": inventory_digest,
        },
        "source_fingerprint": resolved_source_fingerprint,
        "timings": {
            "pytest_collection_s": duration_s,
            "postprocess_s": postprocess_s,
            "source_fingerprint_s": source_fingerprint_s,
            "total_s": _elapsed_s(total_started),
        },
        "test_files": test_files,
        "test_items": test_items,
        "collection_errors": collection_errors,
    }
    return inventory


def _fingerprint_path_map(fingerprint: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(fingerprint, dict):
        return {}
    rows = fingerprint.get("paths")
    if not isinstance(rows, list):
        return {}
    mapped: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        path = row.get("path")
        digest = row.get("digest")
        if isinstance(path, str) and isinstance(digest, str):
            mapped[path] = digest
    return mapped


def _is_test_file_source_path(path: str) -> bool:
    posix_path = PurePosixPath(path)
    return (
        len(posix_path.parts) >= 4
        and posix_path.parts[:3] == ("system", "server", "tests")
        and posix_path.name.startswith("test_")
        and posix_path.suffix == ".py"
    )


def _changed_fingerprint_paths(
    existing_fingerprint: dict[str, Any] | None,
    current_fingerprint: dict[str, Any],
) -> list[str] | None:
    existing_paths = _fingerprint_path_map(existing_fingerprint)
    current_paths = _fingerprint_path_map(current_fingerprint)
    if not existing_paths or not current_paths:
        return None
    all_paths = sorted(set(existing_paths) | set(current_paths))
    return [path for path in all_paths if existing_paths.get(path) != current_paths.get(path)]


def _inventory_digest(test_files: list[dict[str, Any]], test_items: list[dict[str, Any]], collection_errors: list[dict[str, Any]]) -> str:
    canonical_blob = json.dumps(
        {"test_files": test_files, "test_items": test_items, "collection_errors": collection_errors},
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_text(canonical_blob)


def _merge_changed_test_file_inventory(
    existing: dict[str, Any],
    partial: dict[str, Any] | None,
    *,
    source_fingerprint: dict[str, Any],
    changed_paths: Sequence[str],
    started: float,
) -> dict[str, Any]:
    changed_path_set = set(changed_paths)
    partial_items = (partial or {}).get("test_items", [])
    partial_files = (partial or {}).get("test_files", [])
    partial_errors = (partial or {}).get("collection_errors", [])

    test_items = [
        item for item in existing.get("test_items", [])
        if item.get("path") not in changed_path_set
    ]
    test_items.extend(partial_items)
    test_items = sorted(test_items, key=lambda item: item.get("nodeid", ""))

    test_files = [
        row for row in existing.get("test_files", [])
        if row.get("path") not in changed_path_set
    ]
    test_files.extend(partial_files)
    test_files = sorted(test_files, key=lambda row: row.get("path", ""))

    collection_errors = [
        row for row in existing.get("collection_errors", [])
        if row.get("path") not in changed_path_set
    ]
    collection_errors.extend(partial_errors)
    collection_errors = sorted(collection_errors, key=lambda row: json.dumps(row, sort_keys=True))

    inventory_digest = _inventory_digest(test_files, test_items, collection_errors)
    partial_pytest = (partial or {}).get("pytest", {})
    duration_s = round(time.time() - started, 3)
    partial_timings = (partial or {}).get("timings", {})
    return {
        "schema_version": 1,
        "generated_at": _now(),
        "pytest": {
            "version": partial_pytest.get("version", existing.get("pytest", {}).get("version", "unknown")),
            "collect_command": partial_pytest.get("collect_command", []),
            "plugin_autoload": partial_pytest.get("plugin_autoload", existing.get("pytest", {}).get("plugin_autoload", "disabled")),
            "exit_code": partial_pytest.get("exit_code", 0),
            "duration_s": duration_s,
            "result_classification": partial_pytest.get("result_classification", "passed"),
            "collection_mode": "incremental_changed_test_files",
            "changed_source_count": len(changed_path_set),
            "full_authority_route": "./repo-python tools/meta/testing/test_inventory.py --write --force-refresh",
        },
        "summary": {
            "test_file_count": len(test_files),
            "test_item_count": len(test_items),
            "collection_error_count": len(collection_errors),
            "inventory_digest": inventory_digest,
        },
        "source_fingerprint": source_fingerprint,
        "timings": {
            "pytest_collection_s": partial_pytest.get(
                "duration_s",
                partial_timings.get("pytest_collection_s", 0.0),
            ),
            "incremental_merge_s": duration_s,
            "changed_source_count": len(changed_path_set),
            "total_s": duration_s,
        },
        "test_files": test_files,
        "test_items": test_items,
        "collection_errors": collection_errors,
    }


def _try_incremental_write_inventory(source_fingerprint: dict[str, Any]) -> dict[str, Any] | None:
    existing = _load_existing_inventory()
    if existing is None:
        return None
    changed_paths = _changed_fingerprint_paths(existing.get("source_fingerprint"), source_fingerprint)
    if not changed_paths:
        return None
    if any(not _is_test_file_source_path(path) for path in changed_paths):
        return None

    collect_paths = [
        REPO_ROOT / path for path in changed_paths
        if (REPO_ROOT / path).exists()
    ]
    started = time.time()
    partial = (
        collect_inventory(source_fingerprint=source_fingerprint, test_paths=collect_paths)
        if collect_paths
        else None
    )
    return _merge_changed_test_file_inventory(
        existing,
        partial,
        source_fingerprint=source_fingerprint,
        changed_paths=changed_paths,
        started=started,
    )


def write_inventory_projection(inventory: dict[str, Any]) -> Path:
    INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    canonical = json.dumps(inventory, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    INVENTORY_PATH.write_text(canonical, encoding="utf-8")
    return INVENTORY_PATH


def emit_event(inventory: dict[str, Any], wrote: Path | None, *, force: bool = False) -> dict:
    inv_digest = inventory["summary"]["inventory_digest"]
    idempotency_key = "test_inventory_refresh:" + ev_helper.sha256_short(
        f"test_inventory_refresh|{inv_digest}|{inventory['pytest']['version']}"
    )
    if not force:
        prior = ev_helper.lookup_idempotent_success("test_inventory_refresh", idempotency_key)
        if prior is not None:
            skipped = ev_helper.build_event(
                event_type="operation.skipped",
                actor={"kind": "validator", "id": "test_inventory.py"},
                trigger={"kind": "manual", "id": "test_inventory_refresh"},
                operation={
                    "name": "test_inventory_refresh",
                    "attempt_id": f"attempt_{int(time.time())}",
                    "idempotency_key": idempotency_key,
                    "mutation_class": "M0R",
                },
                subject={"artifact_kind": "lattice_event", "paths": []},
                result={"status": "skipped", "duration_s": 0.0},
                evidence=[{"kind": "summary", "summary": f"prior success at {prior.get('occurred_at')}"}],
                next_safe_action="none",
            )
            ev_helper.append_event(skipped)
            return skipped
    write_set = []
    if wrote is not None:
        write_set.append({
            "path": str(wrote.relative_to(REPO_ROOT)),
            "digest": inv_digest,
        })
    event = ev_helper.build_event(
        event_type="test_inventory.refreshed",
        actor={"kind": "validator", "id": "test_inventory.py"},
        trigger={"kind": "manual", "id": "test_inventory_refresh"},
        operation={
            "name": "test_inventory_refresh",
            "attempt_id": f"attempt_{int(time.time())}",
            "idempotency_key": idempotency_key,
            "mutation_class": "M1",
        },
        subject={"artifact_kind": "lattice_event", "paths": [str(INVENTORY_PATH.relative_to(REPO_ROOT))]},
        write_set=write_set,
        result={"status": "passed", "duration_s": inventory["pytest"]["duration_s"]},
        evidence=[{
            "kind": "summary",
            "summary": (
                f"files={inventory['summary']['test_file_count']} "
                f"items={inventory['summary']['test_item_count']} "
                f"errors={inventory['summary']['collection_error_count']} "
                f"pytest_exit={inventory['pytest']['exit_code']}"
            ),
        }],
        next_safe_action="./repo-python kernel.py --lattice-status",
    )
    ev_helper.append_event(event)
    return event


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="Print inventory JSON; do not write.")
    ap.add_argument("--write", action="store_true", help="Write projection + emit event when stale.")
    ap.add_argument("--check", action="store_true", help="Exit 1 if existing projection is stale.")
    ap.add_argument("--force", action="store_true", help="Bypass idempotency on event emit.")
    ap.add_argument("--force-refresh", action="store_true", help="Recollect even when the source fingerprint is fresh.")
    args = ap.parse_args(argv)

    if args.json:
        inventory = collect_inventory()
        print(json.dumps(inventory, indent=2, sort_keys=True))
        return 0
    if args.check:
        if not INVENTORY_PATH.exists():
            print("[CHECK] inventory missing", file=sys.stderr)
            return 1
        source_fingerprint = build_source_fingerprint()
        fresh_existing = _fresh_existing_inventory(source_fingerprint)
        if fresh_existing is not None:
            print(json.dumps({
                "check": "fresh",
                "inventory_digest": fresh_existing.get("summary", {}).get("inventory_digest"),
                "source_fingerprint": {
                    "check": "fresh",
                    "digest": source_fingerprint["digest"],
                    "path_count": source_fingerprint["path_count"],
                },
                "pytest_collection": "skipped_source_fingerprint_match",
            }, indent=2))
            return 0
        existing = _load_existing_inventory()
        if existing is None:
            print("[CHECK] inventory invalid; run tools/meta/testing/test_inventory.py --write", file=sys.stderr)
            return 1
        existing_source_fingerprint = existing.get("source_fingerprint") or {}
        print(json.dumps({
            "check": "stale",
            "reason": "source_fingerprint_mismatch",
            "inventory_digest": existing.get("summary", {}).get("inventory_digest"),
            "source_fingerprint": {
                "check": "stale",
                "existing_digest": existing_source_fingerprint.get("digest"),
                "existing_path_count": existing_source_fingerprint.get("path_count"),
                "current_digest": source_fingerprint["digest"],
                "current_path_count": source_fingerprint["path_count"],
            },
            "pytest_collection": "skipped_source_fingerprint_mismatch",
            "next_safe_action": "./repo-python tools/meta/testing/test_inventory.py --write",
            "next_full_authority_route": "./repo-python tools/meta/testing/test_inventory.py --write --force-refresh",
        }, indent=2))
        return 1
    if args.write:
        cli_started = time.perf_counter()
        fingerprint_started = time.perf_counter()
        source_fingerprint = build_source_fingerprint()
        source_fingerprint_s = _elapsed_s(fingerprint_started)
        existing = None if args.force_refresh else _fresh_existing_inventory(source_fingerprint)
        if existing is not None:
            out = {
                "wrote": None,
                "write": "skipped_source_fingerprint_match",
                "summary": existing.get("summary", {}),
                "pytest": existing.get("pytest", {}),
                "source_fingerprint": {
                    "check": "fresh",
                    "digest": source_fingerprint["digest"],
                    "path_count": source_fingerprint["path_count"],
                },
                "pytest_collection": "skipped_source_fingerprint_match",
                "timings": {
                    "source_fingerprint_s": source_fingerprint_s,
                    "pytest_collection_s": 0.0,
                    "projection_write_s": 0.0,
                    "event_emit_s": 0.0,
                    "total_s": _elapsed_s(cli_started),
                },
                "next_full_authority_route": "./repo-python tools/meta/testing/test_inventory.py --write --force-refresh",
            }
            print(json.dumps(out, indent=2, sort_keys=True))
            return 0
        refresh_started = time.perf_counter()
        inventory = None
        if not args.force_refresh:
            inventory = _try_incremental_write_inventory(source_fingerprint)
        if inventory is None:
            inventory = collect_inventory(source_fingerprint=source_fingerprint)
        refresh_s = _elapsed_s(refresh_started)
        write_started = time.perf_counter()
        wrote = write_inventory_projection(inventory)
        projection_write_s = _elapsed_s(write_started)
        event_started = time.perf_counter()
        emitted = emit_event(inventory, wrote, force=args.force)
        event_emit_s = _elapsed_s(event_started)
        inventory_timings = inventory.get("timings", {})
        out = {
            "wrote": _display_path(wrote),
            "write": inventory.get("pytest", {}).get("collection_mode", "full_pytest_collection"),
            "summary": inventory["summary"],
            "pytest": inventory["pytest"],
            "timings": {
                "source_fingerprint_s": source_fingerprint_s,
                "inventory_refresh_s": refresh_s,
                "pytest_collection_s": inventory.get("pytest", {}).get(
                    "duration_s",
                    inventory_timings.get("pytest_collection_s", 0.0),
                ),
                "inventory_internal_s": inventory_timings.get("total_s"),
                "projection_write_s": projection_write_s,
                "event_emit_s": event_emit_s,
                "total_s": _elapsed_s(cli_started),
            },
            "emitted_event": {
                "event_type": emitted["event_type"],
                "result_status": emitted["result"]["status"],
                "event_id": emitted["event_id"],
            },
        }
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
