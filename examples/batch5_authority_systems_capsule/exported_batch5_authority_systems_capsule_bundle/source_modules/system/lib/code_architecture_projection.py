"""
[PURPOSE]
- Teleology: Single producer of `code_map_packet_v1` and `blast_radius_packet_v1` for the Code Architecture Projection Plane defined in `codex/doctrine/paper_modules/codeflow_assimilation.md`. Kernel command, world-model endpoint, and Station lens all consume the same packets emitted here; no renderer invents a parallel schema or runs its own builder.
- Mechanism: Load the hologram (graph, quality, symbols) plus four optional overlay sources (paper-module index, route coverage, cross-annex distillation, frontend navigation graph), normalize edges with explicit `confidence` + `edge_sources`, compute reverse-BFS for blast radius, attach per-file overlays, fingerprint the sources for freshness, and emit deterministic JSON packets. Missing or stale overlays degrade gracefully via `omission_receipt`; nothing crashes if an upstream sidecar is absent.
- Non-goal: Build hologram artifacts (`kernel.py --build` owns that), mutate any source, or grant mutation permission downstream (every packet is `projection`/`judgment` evidence per the Workingness posture, never authority).

[INTERFACE]
- build_code_map_packet(*, root, focus_path=None, max_files=300, include_overlays=True) -> dict
- build_blast_radius_packet(*, root, target_path, max_depth=4, include_system_impact=True) -> dict
- load_hologram_sources(root) -> dict
- load_paper_module_index(root) -> dict | None
- load_route_coverage(root) -> dict | None
- load_annex_distillation_index(root) -> dict | None
- load_frontend_navigation_graph(root) -> dict | None
- normalize_graph_edges(graph) -> list[dict]
- compute_reverse_bfs(edges_by_target, target_path, max_depth) -> dict
- compute_source_fingerprint(root, source_rel_paths) -> str
- build_omission_receipt(*, omitted_files=0, omitted_edges=0, omitted_overlays=0, reason=None) -> dict
- build_suggested_verification(*, target_path, file_impact, system_impact) -> dict

[FLOW]
- The kernel `code_map.py` wrapper (in `system/lib/kernel/commands/`) calls `build_code_map_packet` or `build_blast_radius_packet`.
- Each packet builder loads the substrate, normalizes graph edges with confidence bands, attaches missing-safe overlays, and emits a deterministic JSON dict.
- A single `KNOWN_LIMITS` constant is folded into every packet so consumers cannot mistake projection evidence for authority.

[DEPENDENCIES]
- json, hashlib, pathlib: stdlib substrate and fingerprinting.
- collections.deque: reverse-BFS frontier.
- system.lib.paper_modules.extract_code_loci_paths: paper-module overlay path extraction.

[CONSTRAINTS]
- Read-only over `codex/hologram/system/*.json`, `codex/doctrine/paper_modules/_index.json`, `codex/doctrine/paper_modules/_route_coverage.json`, `annexes/annex_distillation_index.json`, and `state/frontend_navigation/navigation_graph.json`. Never mutates these.
- Every packet carries `source_fingerprint`, `omission_receipt`, and `known_limits`. Removing any of those is a contract violation.
- The library is the only producer of `code_map_packet_v1` and `blast_radius_packet_v1`; `code_map.py` is a thin wrapper, the world-model endpoint must call into this library, and the Station lens must only render/filter/layout the packet.
- When-needed: Open when the kernel command, the world-model endpoint, or the Station lens needs the canonical packet shape, or when adding a new overlay source.
- Escalates-to: codex/doctrine/paper_modules/codeflow_assimilation.md (doctrine), system/lib/hologram_index.py (alternative hologram loader), system/lib/paper_modules.py (code_loci extraction).
- Navigation-group: system_lib
"""
from __future__ import annotations

import hashlib
import ast
import json
import os
import posixpath
import re
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from system.lib import graph_scene_core
from system.lib.paper_modules import extract_code_loci_paths


CODE_MAP_SCHEMA_VERSION = "code_map_packet_v1"
BLAST_RADIUS_SCHEMA_VERSION = "blast_radius_packet_v1"
CODE_MAP_RENDER_CONTRACT_VERSION = "code_map_render_contract_v1"
CODE_MAP_PROJECTION_STATE_SCHEMA_VERSION = "code_map_projection_state_v1"
CODE_MAP_GRAPH_PRESENTATION_SCHEMA_VERSION = "code_map_graph_presentation_v1"
CODE_MAP_CAMERA_TARGET_SCHEMA_VERSION = "code_map_camera_target_v1"
SUGGESTED_VERIFICATION_SCHEMA_VERSION = "suggested_verification_v1"
SUGGESTED_VERIFICATION_COMMAND_CAP = 12

# Surfaces whose impact justifies rerunning the projection-plane proof matrix.
PROJECTION_LIBRARY_PATH = "system/lib/code_architecture_projection.py"
PROJECTION_PLANE_ENDPOINT_FILES = frozenset(
    {
        "system/server/world_model.py",
        "system/server/main.py",
        "system/lib/kernel/commands/code_map.py",
    }
)

KNOWN_LIMITS = (
    "dynamic imports may be under-represented",
    "semantic-only edges are advisory unless backed by code evidence",
    "paper-module overlays depend on current code_loci freshness",
)

EDGE_CONFIDENCE_BY_KIND: dict[str, str] = {
    "import": "high",
    "call": "high",
    "semantic": "low",
    "route": "low",
    "paper_module_locus": "medium",
    "frontend_route": "medium",
    "unknown": "low",
}

# Source paths the packet can consume. Missing sources degrade gracefully.
HOLOGRAM_GRAPH_PATH = Path("codex/hologram/system/graph.json")
HOLOGRAM_QUALITY_PATH = Path("codex/hologram/system/quality.json")
HOLOGRAM_SYMBOLS_PATH = Path("codex/hologram/system/symbols.json")
HOLOGRAM_UI_INDEX_PATH = Path("codex/hologram/system/ui_index.json")
PYTHON_SCOPE_INDEX_PATH = Path("codex/standards/std_python_scope_index.json")
PAPER_MODULE_INDEX_PATH = Path("codex/doctrine/paper_modules/_index.json")
PAPER_MODULE_ROUTE_COVERAGE_PATH = Path("codex/doctrine/paper_modules/_route_coverage.json")
ANNEX_DISTILLATION_INDEX_PATH = Path("annexes/annex_distillation_index.json")
FRONTEND_NAVIGATION_GRAPH_PATH = Path("state/frontend_navigation/navigation_graph.json")
PAPER_MODULE_DIR = Path("codex/doctrine/paper_modules")
UI_INDEX_IMPORT_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json")
REPO_PYTHON_EXTENSIONS = (".py",)
REPO_CODE_EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".claude",
        ".codex",
        ".build",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        ".playwright-cli",
        "__pycache__",
        "annexes",
        "build",
        "dist",
        "external",
        "node_modules",
        "output",
        "sandbox",
        "site-packages",
        "state",
        "tmp",
        "venv",
    }
)
REPO_PYTHON_IMPORT_PARSE_CAP = 240
JSON_HEADER_TOKEN_BYTES = 256 * 1024
JSON_HEADER_TOKEN_RE = re.compile(r'"(?P<key>source_fingerprint|generated_at)"\s*:\s*"(?P<value>[^"]+)"')
SOURCE_CACHE_MAX_ENTRIES = 16
DERIVED_CACHE_MAX_ENTRIES = 16

_SOURCE_JSON_CACHE_LOCK = threading.Lock()
_SOURCE_JSON_CACHE: dict[str, tuple[tuple[int, int], Any]] = {}
_DERIVED_CACHE_LOCK = threading.Lock()
_GRAPH_EDGE_CACHE: dict[int, list[dict[str, Any]]] = {}
_UI_INDEX_FILE_ENTRIES_CACHE: dict[int, list[dict[str, Any]]] = {}
_UI_INDEX_SYMBOL_COUNTS_CACHE: dict[int, dict[str, int]] = {}
_UI_INDEX_IMPORT_EDGES_CACHE: dict[int, list[dict[str, Any]]] = {}
_SCOPE_INDEX_FILE_ENTRIES_CACHE: dict[int, list[dict[str, Any]]] = {}
_SCOPE_INDEX_SYMBOL_COUNTS_CACHE: dict[int, dict[str, int]] = {}
_SCOPE_INDEX_CONNECTION_EDGES_CACHE: dict[int, list[dict[str, Any]]] = {}


def _bounded_cache_set(cache: dict[Any, Any], key: Any, value: Any, *, max_entries: int) -> None:
    """[ACTION] Store one process-local cache entry and evict oldest extras."""
    cache[key] = value
    while len(cache) > max_entries:
        cache.pop(next(iter(cache)))


def _now_iso() -> str:
    """[ACTION] Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Any | None:
    """[ACTION] Best-effort JSON load; returns None on absence or parse failure."""
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    except OSError:
        return None
    signature = (int(stat.st_mtime_ns), int(stat.st_size))
    cache_key = str(path)
    with _SOURCE_JSON_CACHE_LOCK:
        cached = _SOURCE_JSON_CACHE.get(cache_key)
        if cached is not None and cached[0] == signature:
            return cached[1]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    with _SOURCE_JSON_CACHE_LOCK:
        _bounded_cache_set(
            _SOURCE_JSON_CACHE,
            cache_key,
            (signature, payload),
            max_entries=SOURCE_CACHE_MAX_ENTRIES,
        )
    return payload


def _read_text(path: Path) -> str | None:
    """[ACTION] Best-effort text load; returns None on absence or read failure."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return None


def _json_header_token_for_path(path: Path) -> str | None:
    """
    [ACTION] Read a bounded JSON header and return an embedded generated/fingerprint token.

    Large generated projections in this repo put `__meta.generated_at` near the
    top of the file. Reading that token is enough for a freshness digest and
    avoids hashing 100MB+ JSON bodies on every CodeMap cold build.
    """
    try:
        with path.open("rb") as handle:
            head = handle.read(JSON_HEADER_TOKEN_BYTES).decode("utf-8", errors="ignore")
    except OSError:
        return None
    match = JSON_HEADER_TOKEN_RE.search(head)
    if not match:
        return None
    return f"{match.group('key')}:{match.group('value')}"


def _source_token_for_path(root: Path, rel: Path) -> str:
    """
    [ACTION]
    - Teleology: Return one fingerprint token for a single substrate source. Folds in the source's own declared `freshness.source_fingerprint` (or `generated_at`) when present so a 5MB index does not need to be re-hashed; falls back to a content-only SHA256 when the source carries no fingerprint of its own.
    - Mechanism: For an existing file, try to JSON-decode and read `freshness.source_fingerprint` first, then `generated_at`; if neither is usable, hash the file's bytes.
    - Reads: `<root>/<rel>` plus optional JSON decoding.
    - Guarantee: Returns a non-empty string token; absent files yield the literal `"absent"`.
    - Fails: Never raises; any decode/read failure falls through to content-hash or `"absent"`.
    """
    path = root / rel
    if not path.exists():
        return "absent"
    try:
        if path.suffix == ".json":
            header_token = _json_header_token_for_path(path)
            if header_token:
                return header_token
            payload = _read_json(path)
            if isinstance(payload, dict):
                freshness = payload.get("freshness")
                if isinstance(freshness, dict):
                    fp = freshness.get("source_fingerprint")
                    if isinstance(fp, str) and fp:
                        return f"upstream:{fp}"
                generated_at = payload.get("generated_at")
                if isinstance(generated_at, str) and generated_at:
                    return f"generated_at:{generated_at}"
    except Exception:
        pass
    try:
        return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()[:16]}"
    except OSError:
        return "absent"


def compute_source_fingerprint(root: Path, source_rel_paths: Iterable[Path]) -> str:
    """
    [ACTION]
    - Teleology: Compute a deterministic, content-based fingerprint over the substrate sources a packet consumed so freshness moves only when content moves (not when mtime ticks). Repo-relative paths participate in the digest so the value is stable across clones.
    - Mechanism: SHA256 over `<repo-relative-path>\0<source-token>\n` lines, where each source token comes from `_source_token_for_path` (upstream fingerprint > generated_at > content SHA256 > "absent").
    - Reads: Each `<root>/<rel>`; JSON-decodes when applicable.
    - Guarantee: Returns a 16-hex-char digest derived from the deterministic input string. Identical content yields identical fingerprint regardless of mtime; absent files contribute `absent` so freshness moves when sources appear/disappear.
    - Fails: Never raises.
    """
    h = hashlib.sha256()
    for rel in sorted(source_rel_paths, key=lambda p: str(p)):
        h.update(str(rel).encode("utf-8"))
        h.update(b"\0")
        h.update(_source_token_for_path(root, rel).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()[:16]


def build_omission_receipt(
    *,
    omitted_files: int = 0,
    omitted_edges: int = 0,
    omitted_overlays: int = 0,
    reason: str | None = None,
) -> dict[str, Any]:
    """[ACTION] Assemble the standard `omission_receipt` block emitted with every packet."""
    return {
        "omitted_files": int(omitted_files),
        "omitted_edges": int(omitted_edges),
        "omitted_overlays": int(omitted_overlays),
        "reason": reason,
    }


def load_hologram_sources(root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Load the three hologram source files the projection consumes: graph, quality, symbols.
    - Mechanism: Resolve each path relative to `root`, read JSON best-effort, and return a dict with each source bound to its payload (or None when absent).
    - Reads: `<root>/codex/hologram/system/{graph,quality,symbols}.json`.
    - Guarantee: Returns a dict with `graph`, `quality`, `symbols` keys; values are payload dicts or None.
    - Fails: Never raises; missing/unreadable sources become None.
    """
    return {
        "graph": _read_json(root / HOLOGRAM_GRAPH_PATH),
        "quality": _read_json(root / HOLOGRAM_QUALITY_PATH),
        "symbols": _read_json(root / HOLOGRAM_SYMBOLS_PATH),
        "ui_index": _read_json(root / HOLOGRAM_UI_INDEX_PATH),
        "scope_index": _read_json(root / PYTHON_SCOPE_INDEX_PATH),
    }


def load_paper_module_index(root: Path) -> dict | None:
    """[ACTION] Load `codex/doctrine/paper_modules/_index.json` or return None when absent."""
    payload = _read_json(root / PAPER_MODULE_INDEX_PATH)
    return payload if isinstance(payload, dict) else None


def load_route_coverage(root: Path) -> dict | None:
    """[ACTION] Load `codex/doctrine/paper_modules/_route_coverage.json` or return None when absent."""
    payload = _read_json(root / PAPER_MODULE_ROUTE_COVERAGE_PATH)
    return payload if isinstance(payload, dict) else None


def load_annex_distillation_index(root: Path) -> dict | None:
    """[ACTION] Load `annexes/annex_distillation_index.json` or return None when absent."""
    payload = _read_json(root / ANNEX_DISTILLATION_INDEX_PATH)
    return payload if isinstance(payload, dict) else None


def load_frontend_navigation_graph(root: Path) -> dict | None:
    """[ACTION] Load `state/frontend_navigation/navigation_graph.json` or return None when absent."""
    payload = _read_json(root / FRONTEND_NAVIGATION_GRAPH_PATH)
    return payload if isinstance(payload, dict) else None


def _files_from_graph(graph: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """[ACTION] Extract the file rows from a hologram graph payload, defaulting to []."""
    if not isinstance(graph, Mapping):
        return []
    files = graph.get("files")
    if isinstance(files, list):
        return [row for row in files if isinstance(row, Mapping)]
    return []


def _file_edges_from_graph(graph: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """[ACTION] Extract the file_edges rows from a hologram graph payload, defaulting to []."""
    if not isinstance(graph, Mapping):
        return []
    edges = graph.get("file_edges")
    if isinstance(edges, list):
        return [row for row in edges if isinstance(row, Mapping)]
    return []


def _quality_by_path(quality: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    """[ACTION] Index the quality payload's file rows by `path` for O(1) lookup."""
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(quality, Mapping):
        return out
    files = quality.get("files")
    if not isinstance(files, list):
        return out
    for row in files:
        if not isinstance(row, Mapping):
            continue
        path = str(row.get("path") or "").strip()
        if path:
            out[path] = dict(row)
    return out


def _symbol_count_by_path(symbols: Mapping[str, Any] | None) -> dict[str, int]:
    """[ACTION] Index the symbols payload's per-file scope/function counts as a quick stat."""
    out: dict[str, int] = {}
    if not isinstance(symbols, Mapping):
        return out
    files = symbols.get("files")
    if not isinstance(files, list):
        return out
    for row in files:
        if not isinstance(row, Mapping):
            continue
        path = str(row.get("path") or "").strip()
        if not path:
            continue
        functions = row.get("functions") if isinstance(row.get("functions"), list) else []
        classes = row.get("classes") if isinstance(row.get("classes"), list) else []
        out[path] = len(functions) + len(classes)
    return out


def _ui_index_root_prefix(ui_index: Mapping[str, Any] | None) -> str:
    """[ACTION] Return the repo-relative root prefix declared by ui_index.json."""
    if not isinstance(ui_index, Mapping):
        return ""
    meta = ui_index.get("__meta")
    if not isinstance(meta, Mapping):
        return ""
    root = str(meta.get("root") or "").strip().replace("\\", "/")
    if not root or root == ".":
        return ""
    return root.strip("/")


def _clean_ui_index_rel_path(raw_path: Any) -> str:
    """[ACTION] Normalize one ui_index path and reject absolute/parent-traversal rows."""
    value = str(raw_path or "").strip().replace("\\", "/")
    if not value or value.startswith("/"):
        return ""
    normalized = posixpath.normpath(value)
    if normalized in {"", "."} or normalized == ".." or normalized.startswith("../"):
        return ""
    return normalized


def _repo_path_from_ui_index_path(raw_path: Any, root_prefix: str) -> str:
    """[ACTION] Convert a ui_index-local file path into a repo-relative path."""
    rel = _clean_ui_index_rel_path(raw_path)
    if not rel:
        return ""
    if root_prefix and rel != root_prefix and not rel.startswith(f"{root_prefix}/"):
        return f"{root_prefix}/{rel}"
    return rel


def _ui_index_file_entries(ui_index: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """[ACTION] Project ui_index file rows into graph-like file entries for fallback packets."""
    if not isinstance(ui_index, Mapping):
        return []
    cache_key = id(ui_index)
    with _DERIVED_CACHE_LOCK:
        cached = _UI_INDEX_FILE_ENTRIES_CACHE.get(cache_key)
        if cached is not None:
            return list(cached)
    files = ui_index.get("files")
    if not isinstance(files, list):
        return []
    root_prefix = _ui_index_root_prefix(ui_index)
    by_path: dict[str, dict[str, Any]] = {}
    for raw in files:
        if not isinstance(raw, Mapping):
            continue
        path = _repo_path_from_ui_index_path(raw.get("path"), root_prefix)
        if not path or path in by_path:
            continue
        imports = raw.get("imports") if isinstance(raw.get("imports"), list) else []
        exports = raw.get("exports") if isinstance(raw.get("exports"), list) else []
        types = raw.get("types") if isinstance(raw.get("types"), list) else []
        props = raw.get("props") if isinstance(raw.get("props"), list) else []
        summary_parts: list[str] = []
        if exports:
            shown = ", ".join(str(item) for item in exports[:3])
            summary_parts.append(f"exports {shown}")
        if imports:
            summary_parts.append(f"{len(imports)} imports")
        if types:
            summary_parts.append(f"{len(types)} types")
        if props:
            summary_parts.append(f"{len(props)} props")
        by_path[path] = {
            "path": path,
            "group_id": _ui_index_layer_for_path(path, root_prefix),
            "summary": "; ".join(summary_parts) if summary_parts else None,
        }
    rows = sorted(by_path.values(), key=lambda row: (_ui_index_sort_key(str(row.get("path") or ""))))
    with _DERIVED_CACHE_LOCK:
        _bounded_cache_set(
            _UI_INDEX_FILE_ENTRIES_CACHE,
            cache_key,
            rows,
            max_entries=DERIVED_CACHE_MAX_ENTRIES,
        )
    return list(rows)


def _ui_index_layer_for_path(path: str, root_prefix: str) -> str | None:
    """[ACTION] Derive a stable layer label for ui_index fallback rows."""
    if not path:
        return None
    if root_prefix and path.startswith(f"{root_prefix}/"):
        local = path[len(root_prefix) + 1:]
        parts = [part for part in local.split("/") if part]
        if len(parts) >= 2 and parts[0] == "src":
            return f"{root_prefix}/{parts[0]}/{parts[1]}"
        if parts:
            return f"{root_prefix}/{parts[0]}"
        return root_prefix
    parts = [part for part in path.split("/") if part]
    return "/".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else None)


def _ui_index_sort_key(path: str) -> tuple[int, str]:
    """[ACTION] Keep demo-facing UI surfaces before lower-signal tool/config files."""
    if "/src/pages/" in path:
        priority = 0
    elif "/src/components/" in path:
        priority = 1
    elif "/src/lib/" in path or "/src/hooks/" in path:
        priority = 2
    elif "/src/" in path:
        priority = 3
    else:
        priority = 4
    return priority, path


def _scope_index_file_entries(scope_index: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """[ACTION] Project the generated Python scope index file rows into graph-like file entries."""
    if not isinstance(scope_index, Mapping):
        return []
    cache_key = id(scope_index)
    with _DERIVED_CACHE_LOCK:
        cached = _SCOPE_INDEX_FILE_ENTRIES_CACHE.get(cache_key)
        if cached is not None:
            return list(cached)
    files = scope_index.get("files")
    if not isinstance(files, list):
        return []
    entries: dict[str, dict[str, Any]] = {}
    for raw in files:
        if not isinstance(raw, Mapping):
            continue
        path = str(raw.get("path") or "").strip()
        if not path:
            continue
        entries[path] = {
            "path": path,
            "group_id": str(raw.get("group_id") or "").strip() or _repo_code_layer_for_path(path),
            "summary": str(raw.get("summary") or "").strip() or None,
        }
    rows = sorted(entries.values(), key=lambda row: _repo_code_sort_key(str(row.get("path") or "")))
    with _DERIVED_CACHE_LOCK:
        _bounded_cache_set(
            _SCOPE_INDEX_FILE_ENTRIES_CACHE,
            cache_key,
            rows,
            max_entries=DERIVED_CACHE_MAX_ENTRIES,
        )
    return list(rows)


def _scope_index_symbol_counts(scope_index: Mapping[str, Any] | None) -> dict[str, int]:
    """[ACTION] Count generated Python scope rows by file path."""
    out: dict[str, int] = {}
    if not isinstance(scope_index, Mapping):
        return out
    cache_key = id(scope_index)
    with _DERIVED_CACHE_LOCK:
        cached = _SCOPE_INDEX_SYMBOL_COUNTS_CACHE.get(cache_key)
        if cached is not None:
            return dict(cached)
    scopes = scope_index.get("scopes")
    if not isinstance(scopes, list):
        return out
    for raw in scopes:
        if not isinstance(raw, Mapping):
            continue
        path = str(raw.get("path") or "").strip()
        if path:
            out[path] = out.get(path, 0) + 1
    with _DERIVED_CACHE_LOCK:
        _bounded_cache_set(
            _SCOPE_INDEX_SYMBOL_COUNTS_CACHE,
            cache_key,
            out,
            max_entries=DERIVED_CACHE_MAX_ENTRIES,
        )
    return out


def _symbol_ref_file_path(ref: Any) -> str | None:
    """[ACTION] Extract the file component from a generated scope symbol reference."""
    text = str(ref or "").strip()
    if not text:
        return None
    path_part = text.split("::", 1)[0].strip()
    if path_part.endswith(".py") and ("/" in path_part or path_part == Path(path_part).name):
        return path_part
    return None


def _scope_index_connection_edges(scope_index: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """[ACTION] Rehydrate file-level dynamic relationships from std_python_scope_index.json."""
    if not isinstance(scope_index, Mapping):
        return []
    cache_key = id(scope_index)
    with _DERIVED_CACHE_LOCK:
        cached = _SCOPE_INDEX_CONNECTION_EDGES_CACHE.get(cache_key)
        if cached is not None:
            return list(cached)
    file_paths = {
        str(raw.get("path") or "").strip()
        for raw in scope_index.get("files", []) or []
        if isinstance(raw, Mapping) and str(raw.get("path") or "").strip()
    }
    edges: list[dict[str, Any]] = []
    for raw in scope_index.get("files", []) or []:
        if not isinstance(raw, Mapping):
            continue
        src = str(raw.get("path") or "").strip()
        if not src:
            continue
        related_paths = raw.get("related_paths")
        if not isinstance(related_paths, list):
            continue
        for rel in related_paths:
            if not isinstance(rel, Mapping):
                continue
            dst = str(rel.get("path") or "").strip()
            kind = str(rel.get("edge") or "related").strip() or "related"
            if not dst or dst == src or dst not in file_paths:
                continue
            edges.append(
                {
                    "from": src,
                    "to": dst,
                    "kind": kind,
                    "confidence": EDGE_CONFIDENCE_BY_KIND.get(kind, "low"),
                    "edge_sources": ["std_python_scope_index.json"],
                    "evidence": "files.related_paths",
                }
            )

    for raw in scope_index.get("scopes", []) or []:
        if not isinstance(raw, Mapping):
            continue
        src = str(raw.get("path") or "").strip()
        if not src:
            continue
        for callee in raw.get("callee_refs", []) or []:
            dst = _symbol_ref_file_path(callee)
            if dst and dst in file_paths and dst != src:
                edges.append(
                    {
                        "from": src,
                        "to": dst,
                        "kind": "call",
                        "confidence": "high",
                        "edge_sources": ["std_python_scope_index.json"],
                        "evidence": str(callee),
                    }
                )
        for inbound in raw.get("inbound_dependents", []) or []:
            dependent = _symbol_ref_file_path(inbound)
            if dependent and dependent in file_paths and dependent != src:
                edges.append(
                    {
                        "from": dependent,
                        "to": src,
                        "kind": "dependent",
                        "confidence": "high",
                        "edge_sources": ["std_python_scope_index.json"],
                        "evidence": str(inbound),
                    }
                )
        for related in raw.get("related_symbols", []) or []:
            dst = _symbol_ref_file_path(related)
            if dst and dst in file_paths and dst != src:
                edges.append(
                    {
                        "from": src,
                        "to": dst,
                        "kind": "related",
                        "confidence": "low",
                        "edge_sources": ["std_python_scope_index.json"],
                        "evidence": str(related),
                    }
                )
    rows = _merge_connections(edges)
    with _DERIVED_CACHE_LOCK:
        _bounded_cache_set(
            _SCOPE_INDEX_CONNECTION_EDGES_CACHE,
            cache_key,
            rows,
            max_entries=DERIVED_CACHE_MAX_ENTRIES,
        )
    return list(rows)


def _repo_code_layer_for_path(path: str) -> str | None:
    """[ACTION] Derive a coarse backend layer label for Python filesystem fallback rows."""
    parts = [part for part in path.split("/") if part]
    if not parts:
        return None
    if len(parts) == 1:
        return "repo_root"
    if parts[0] == "system":
        if len(parts) >= 3 and parts[1] == "lib":
            if parts[2] == "kernel" and len(parts) >= 4:
                return f"system/lib/kernel/{parts[3]}"
            return f"system/lib/{parts[2]}"
        if len(parts) >= 3 and parts[1] == "server":
            if parts[2] == "tests":
                return "system/server/tests"
            if parts[2] == "ui":
                return _ui_index_layer_for_path(path, "system/server/ui")
            return f"system/server/{parts[2]}"
        return "/".join(parts[: min(3, len(parts))])
    if parts[0] == "tools":
        return "/".join(parts[: min(3, len(parts))])
    if parts[0] == "codex":
        return "/".join(parts[: min(3, len(parts))])
    if parts[0] == "tests":
        return "tests"
    if parts[0] == "microcosm-substrate" and len(parts) >= 3:
        return "/".join(parts[:3])
    return "/".join(parts[: min(3, len(parts))])


def _repo_code_sort_key(path: str) -> tuple[int, str]:
    """[ACTION] Prefer backend/Python rows before UI rows when a packet must truncate."""
    if path.endswith(REPO_PYTHON_EXTENSIONS):
        if path.startswith("system/lib/"):
            priority = 0
        elif path.startswith("system/server/"):
            priority = 1
        elif path.startswith("tools/"):
            priority = 2
        elif path.startswith("codex/"):
            priority = 3
        elif path.startswith("tests/") or path.count("/") == 0:
            priority = 4
        elif path.startswith("microcosm-substrate/src/") or path.startswith("microcosm-substrate/tests/"):
            priority = 5
        else:
            priority = 6
        return priority, path
    if path.startswith("system/server/ui/"):
        ui_priority, ui_path = _ui_index_sort_key(path)
        return 20 + ui_priority, ui_path
    return 30, path


def _is_repo_code_path_excluded(rel_path: Path) -> bool:
    """[ACTION] Filter build/vendor/cache paths out of the filesystem fallback."""
    return any(part in REPO_CODE_EXCLUDED_DIRS for part in rel_path.parts)


def _repo_python_file_entries(root: Path) -> list[dict[str, Any]]:
    """[ACTION] Scan repo Python files into graph-like file entries when the hologram is stale or UI-only."""
    by_path: dict[str, dict[str, Any]] = {}
    try:
        walker = os.walk(root)
    except OSError:
        return []
    for dirpath, dirnames, filenames in walker:
        try:
            base = Path(dirpath)
            rel_dir = base.relative_to(root)
        except ValueError:
            continue
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in REPO_CODE_EXCLUDED_DIRS
            and not _is_repo_code_path_excluded(rel_dir / dirname)
        ]
        if _is_repo_code_path_excluded(rel_dir):
            dirnames[:] = []
            continue
        for filename in filenames:
            if not filename.endswith(REPO_PYTHON_EXTENSIONS):
                continue
            rel_path = rel_dir / filename
            if _is_repo_code_path_excluded(rel_path):
                continue
            rel = rel_path.as_posix()
            by_path[rel] = {
                "path": rel,
                "group_id": _repo_code_layer_for_path(rel),
                "summary": None,
            }
    return sorted(by_path.values(), key=lambda row: _repo_code_sort_key(str(row.get("path") or "")))


def _module_name_for_python_path(path: str) -> str | None:
    """[ACTION] Convert a repo-relative .py path into its importable dotted module name."""
    if not path.endswith(".py"):
        return None
    stem = path[:-3]
    parts = [part for part in stem.split("/") if part]
    if not parts:
        return None
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(part for part in parts if part) or None


def _resolve_python_module(module: str, module_to_path: Mapping[str, str]) -> str | None:
    """[ACTION] Resolve the longest import-module prefix present in the fallback module map."""
    parts = [part for part in str(module or "").split(".") if part]
    while parts:
        candidate = ".".join(parts)
        target = module_to_path.get(candidate)
        if target:
            return target
        parts.pop()
    return None


def _absolute_import_candidates(node: ast.AST, current_module: str) -> list[tuple[str, str]]:
    """[ACTION] Extract dotted import candidates plus evidence labels from one Python AST import node."""
    candidates: list[tuple[str, str]] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            name = str(alias.name or "").strip()
            if name:
                candidates.append((name, f"import {name}"))
        return candidates

    if not isinstance(node, ast.ImportFrom):
        return candidates

    base_parts: list[str] = []
    if node.level:
        module_parts = [part for part in current_module.split(".") if part]
        package_parts = module_parts[:-1] if module_parts else []
        keep_count = max(0, len(package_parts) - (int(node.level) - 1))
        base_parts = package_parts[:keep_count]
    module = str(node.module or "").strip()
    if module:
        base_parts.extend(part for part in module.split(".") if part)
    base = ".".join(base_parts)
    if base:
        candidates.append((base, f"from {'.' * int(node.level or 0)}{module} import ..."))
    for alias in node.names:
        name = str(alias.name or "").strip()
        if not name or name == "*":
            continue
        joined = ".".join([part for part in (base, name) if part])
        if joined:
            candidates.append((joined, f"from {'.' * int(node.level or 0)}{module} import {name}"))
    return candidates


def _repo_python_import_edges_and_symbols(
    root: Path,
    file_entries: Iterable[Mapping[str, Any]],
    *,
    parse_paths: Iterable[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """[ACTION] Parse Python fallback files for import edges and a compact symbol count."""
    python_paths = sorted(
        {
            str(row.get("path") or "").strip()
            for row in file_entries
            if str(row.get("path") or "").strip().endswith(REPO_PYTHON_EXTENSIONS)
        }
    )
    module_to_path: dict[str, str] = {}
    for path in python_paths:
        module = _module_name_for_python_path(path)
        if module:
            module_to_path[module] = path

    parse_path_set = {
        str(path or "").strip()
        for path in parse_paths
        if str(path or "").strip()
    } if parse_paths is not None else None
    symbol_counts: dict[str, int] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    for src in python_paths:
        if parse_path_set is not None and src not in parse_path_set:
            continue
        module = _module_name_for_python_path(src) or ""
        body = _read_text(root / src)
        if body is None:
            continue
        try:
            tree = ast.parse(body, filename=src)
        except SyntaxError:
            symbol_counts[src] = 0
            continue

        symbol_counts[src] = sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        )
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for candidate, evidence in _absolute_import_candidates(node, module):
                dst = _resolve_python_module(candidate, module_to_path)
                if not dst or dst == src:
                    continue
                key = (src, dst, "import")
                edges[key] = {
                    "from": src,
                    "to": dst,
                    "kind": "import",
                    "confidence": "high",
                    "edge_sources": ["repo_python_imports"],
                    "evidence": evidence,
                }
    return sorted(edges.values(), key=lambda r: (r["from"], r["to"], r["kind"])), symbol_counts


def _merge_file_entries(*entry_lists: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """[ACTION] Dedupe file entries by path while preserving richer first-seen metadata."""
    by_path: dict[str, dict[str, Any]] = {}
    for entries in entry_lists:
        for raw in entries:
            path = str(raw.get("path") or "").strip()
            if not path:
                continue
            current = by_path.get(path)
            if current is None:
                by_path[path] = dict(raw)
                continue
            if not current.get("group_id") and raw.get("group_id"):
                current["group_id"] = raw.get("group_id")
            if not current.get("layer") and raw.get("layer"):
                current["layer"] = raw.get("layer")
            if not current.get("summary") and raw.get("summary"):
                current["summary"] = raw.get("summary")
    return sorted(by_path.values(), key=lambda row: _repo_code_sort_key(str(row.get("path") or "")))


def _merge_connections(*edge_lists: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """[ACTION] Dedupe connection rows and merge source labels for identical directed relations."""
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for edges in edge_lists:
        for raw in edges:
            src = str(raw.get("from") or "").strip()
            dst = str(raw.get("to") or "").strip()
            kind = str(raw.get("kind") or "unknown").strip() or "unknown"
            if not src or not dst:
                continue
            key = (src, dst, kind)
            sources = raw.get("edge_sources")
            source_list = [str(item) for item in sources] if isinstance(sources, list) else []
            if key not in by_key:
                row = dict(raw)
                row["from"] = src
                row["to"] = dst
                row["kind"] = kind
                row["edge_sources"] = source_list or ["unknown"]
                by_key[key] = row
                continue
            existing = by_key[key]
            existing_sources = list(existing.get("edge_sources") or [])
            existing["edge_sources"] = sorted(set(existing_sources + source_list))
            if not existing.get("evidence") and raw.get("evidence"):
                existing["evidence"] = raw.get("evidence")
    return sorted(by_key.values(), key=lambda r: (r["from"], r["to"], r["kind"]))


def _connection_edge_sources(edges: Iterable[Mapping[str, Any]], fallback: Iterable[str]) -> list[str]:
    """[ACTION] Extract a stable source-label list from normalized connection rows."""
    sources = sorted(
        {
            source
            for edge in edges
            for source in (edge.get("edge_sources") or [])
            if isinstance(source, str) and source
        }
    )
    return sources or list(fallback)


def _path_is_frontend(path: str) -> bool:
    """[ACTION] Return true for repo-relative frontend/UI source rows."""
    return path.startswith("system/server/ui/")


def _packet_composition_stats(
    file_rows: Iterable[Mapping[str, Any]],
    connection_rows: Iterable[Mapping[str, Any]],
) -> dict[str, int]:
    """[ACTION] Count backend/Python vs frontend/UI composition for operator-visible proof."""
    paths = [str(row.get("path") or "").strip() for row in file_rows]
    python_file_count = sum(1 for path in paths if path.endswith(REPO_PYTHON_EXTENSIONS))
    frontend_file_count = sum(1 for path in paths if _path_is_frontend(path))
    python_connection_count = 0
    frontend_connection_count = 0
    for edge in connection_rows:
        src = str(edge.get("from") or "").strip()
        dst = str(edge.get("to") or "").strip()
        if src.endswith(REPO_PYTHON_EXTENSIONS) and dst.endswith(REPO_PYTHON_EXTENSIONS):
            python_connection_count += 1
        if _path_is_frontend(src) or _path_is_frontend(dst):
            frontend_connection_count += 1
    return {
        "python_file_count": python_file_count,
        "frontend_file_count": frontend_file_count,
        "other_file_count": max(0, len(paths) - python_file_count - frontend_file_count),
        "python_connection_count": python_connection_count,
        "frontend_connection_count": frontend_connection_count,
    }


def _path_leaf(path: str) -> str:
    """[ACTION] Return the final path segment for frontend labels."""
    return path.rsplit("/", 1)[-1] if path else ""


def _path_parent(path: str) -> str | None:
    """[ACTION] Return the containing path label for frontend subtitles."""
    if "/" not in path:
        return None
    return path.rsplit("/", 1)[0] or None


def _overlay_count(file_row: Mapping[str, Any], overlay_key: str) -> int:
    overlays = file_row.get("overlays")
    if not isinstance(overlays, Mapping):
        return 0
    values = overlays.get(overlay_key)
    return len(values) if isinstance(values, list) else 0


def _warning_count(file_row: Mapping[str, Any]) -> int:
    health = file_row.get("health")
    if not isinstance(health, Mapping):
        return 0
    warnings = health.get("warnings")
    return len(warnings) if isinstance(warnings, list) else 0


def _file_presentation_score(file_row: Mapping[str, Any]) -> float:
    """[ACTION] Score one file row for backend-owned salience hints."""
    fan_in = int(file_row.get("fan_in") or 0)
    fan_out = int(file_row.get("fan_out") or 0)
    overlays = sum(
        _overlay_count(file_row, key)
        for key in ("paper_modules", "semantic_routes", "annex_patterns", "frontend_views", "workingness")
    )
    warnings = _warning_count(file_row)
    return (fan_in * 1.5) + fan_out + (overlays * 3) + (warnings * 4)


def _salience_band(score: float) -> str:
    if score >= 18:
        return "high"
    if score >= 6:
        return "medium"
    return "low"


def _density_band(score: float, *, is_focus: bool = False) -> str:
    if is_focus or score >= 18:
        return "overview"
    if score >= 6:
        return "focus"
    return "detail"


def _file_node_role(file_row: Mapping[str, Any]) -> str:
    """[ACTION] Classify a file row into a renderer-neutral presentation role."""
    path = str(file_row.get("path") or "")
    if path == PROJECTION_LIBRARY_PATH:
        return "projection_builder"
    if path in PROJECTION_PLANE_ENDPOINT_FILES:
        return "projection_transport"
    if path.startswith("system/server/tests/") or "/tests/" in path or path.rsplit("/", 1)[-1].startswith("test_"):
        return "verification_node"
    if _overlay_count(file_row, "frontend_views") > 0:
        return "frontend_view_host"
    if path.startswith("system/server/ui/src/pages/"):
        return "frontend_page"
    if path.startswith("system/server/ui/src/components/"):
        return "frontend_component"
    if path.startswith("system/server/ui/"):
        return "frontend_support"
    if path.startswith("system/lib/kernel/") or path.startswith("system/lib/kernel_nav"):
        return "kernel_route"
    if path.startswith("system/lib/"):
        return "backend_library"
    if path.startswith("system/server/"):
        return "backend_transport"
    if path.startswith("tools/"):
        return "tooling"
    if path.startswith("codex/"):
        return "doctrine_substrate"
    return "support_file"


def _file_metadata_labels(file_row: Mapping[str, Any], *, node_role: str) -> list[str]:
    labels = [node_role]
    fan_in = int(file_row.get("fan_in") or 0)
    fan_out = int(file_row.get("fan_out") or 0)
    if fan_in:
        labels.append(f"in:{fan_in}")
    if fan_out:
        labels.append(f"out:{fan_out}")
    warnings = _warning_count(file_row)
    if warnings:
        labels.append(f"warnings:{warnings}")
    overlay_total = sum(
        _overlay_count(file_row, key)
        for key in ("paper_modules", "semantic_routes", "annex_patterns", "frontend_views", "workingness")
    )
    if overlay_total:
        labels.append(f"overlays:{overlay_total}")
    return labels


def _attach_file_presentation(file_rows: list[dict[str, Any]], *, focus: str | None) -> None:
    """[ACTION] Mutate file rows with backend-owned graph presentation hints."""
    for row in file_rows:
        path = str(row.get("path") or "")
        score = _file_presentation_score(row)
        role = _file_node_role(row)
        is_focus = bool(focus and path == focus)
        row["presentation"] = {
            "schema": "code_map_file_presentation_v1",
            "node_role": role,
            "salience": _salience_band(score),
            "salience_score": round(score, 3),
            "density_band": _density_band(score, is_focus=is_focus),
            "primary_label": _path_leaf(path) or path,
            "secondary_label": row.get("layer") or _path_parent(path),
            "metadata_labels": _file_metadata_labels(row, node_role=role),
            "selectable_target_type": "file",
            "url_identity": f"file:{path}" if path else None,
            "focus_role": "selected" if is_focus else "normal",
        }


def _edge_role(kind: Any) -> str:
    token = str(kind or "unknown").strip()
    if token in {"import", "internal_import", "call", "dependent"}:
        return "dependency_context"
    if token in {"same_group", "contains"}:
        return "membership"
    if token in {"test_neighbor", "verification"}:
        return "verification"
    if token in {"route", "escalates_to"}:
        return "control_flow"
    if token in {"related", "semantic"}:
        return "affinity"
    return "unknown"


def _edge_strength(confidence: Any) -> str:
    token = str(confidence or "").strip()
    if token == "high":
        return "strong"
    if token == "medium":
        return "medium"
    return "weak"


def _edge_density_band(edge: Mapping[str, Any]) -> str:
    role = _edge_role(edge.get("kind"))
    if role in {"dependency_context", "control_flow"} and edge.get("confidence") in {"high", "medium"}:
        return "overview"
    if role in {"verification", "affinity"}:
        return "focus"
    return "detail"


def _attach_connection_presentation(connections: list[dict[str, Any]]) -> None:
    """[ACTION] Mutate connection rows with renderer-neutral presentation hints."""
    for edge in connections:
        role = _edge_role(edge.get("kind"))
        edge["presentation"] = {
            "schema": "code_map_edge_presentation_v1",
            "edge_role": role,
            "edge_strength": _edge_strength(edge.get("confidence")),
            "density_band": _edge_density_band(edge),
            "hidden_reason": None,
        }


def _count_nested(rows: Iterable[Mapping[str, Any]], field_path: tuple[str, str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    outer, inner = field_path
    for row in rows:
        parent = row.get(outer)
        if not isinstance(parent, Mapping):
            continue
        token = str(parent.get(inner) or "unknown")
        counts[token] = counts.get(token, 0) + 1
    return dict(sorted(counts.items()))


def _build_graph_presentation_summary(
    file_rows: list[dict[str, Any]],
    connections: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": CODE_MAP_GRAPH_PRESENTATION_SCHEMA_VERSION,
        "render_contract_version": CODE_MAP_RENDER_CONTRACT_VERSION,
        "node_role_counts": _count_nested(file_rows, ("presentation", "node_role")),
        "node_salience_counts": _count_nested(file_rows, ("presentation", "salience")),
        "edge_role_counts": _count_nested(connections, ("presentation", "edge_role")),
        "edge_density_counts": _count_nested(connections, ("presentation", "density_band")),
        "grammar": {
            "node_role_field": "files[].presentation.node_role",
            "edge_role_field": "connections[].presentation.edge_role",
            "density_field": "presentation.density_band",
            "labels": [
                "files[].presentation.primary_label",
                "files[].presentation.secondary_label",
                "files[].presentation.metadata_labels",
            ],
        },
    }


def _build_camera_target(file_rows: list[dict[str, Any]], *, focus: str | None) -> dict[str, Any]:
    sorted_rows = sorted(
        file_rows,
        key=lambda row: (
            -float((row.get("presentation") or {}).get("salience_score") or 0),
            str(row.get("path") or ""),
        ),
    )
    paths = [str(row.get("path") or "") for row in sorted_rows if str(row.get("path") or "")][:12]
    if focus:
        paths = [focus] + [path for path in paths if path != focus]
    return {
        "schema": CODE_MAP_CAMERA_TARGET_SCHEMA_VERSION,
        "mode": "focus" if focus else "overview",
        "target_type": "file" if focus else "packet",
        "target_id": f"file:{focus}" if focus else "packet:code_map_overview",
        "target_path": focus,
        "target_paths": paths,
        "recommended_fit": {
            "scope": "selected_neighborhood" if focus else "salient_overview",
            "padding": 0.18 if focus else 0.12,
        },
    }


def _code_map_graph_scene_node_id(path: str) -> str:
    return f"file:{path}"


def _code_map_graph_scene_label(value: str) -> str:
    return value.replace("_", " ").replace("/", " / ").title()


def _code_map_graph_scene_domain(path: str, layer: Any) -> str:
    token = str(layer or "").strip()
    if token:
        return token
    if "/" in path:
        return path.split("/", 1)[0]
    return "repo_root"


def _build_code_map_graph_scene_payload(
    *,
    generated_at: str,
    source_fingerprint: str,
    focus: str | None,
    file_rows: list[dict[str, Any]],
    returned_edges: list[dict[str, Any]],
    camera_target: Mapping[str, Any],
) -> dict[str, Any]:
    """[ACTION] Project returned code_map rows into compact graph_scene_core fields."""
    nodes: list[dict[str, Any]] = []
    inspectors: dict[str, dict[str, Any]] = {}
    lane_ids: set[str] = set()
    domain_counts: dict[str, int] = {}
    paths_by_id: dict[str, str] = {}
    for index, row in enumerate(file_rows):
        path = str(row.get("path") or "").strip()
        if not path:
            continue
        presentation = row.get("presentation") if isinstance(row.get("presentation"), Mapping) else {}
        health = row.get("health") if isinstance(row.get("health"), Mapping) else {}
        warnings = health.get("warnings") if isinstance(health.get("warnings"), list) else []
        role = str(presentation.get("node_role") or _file_node_role(row))
        domain = _code_map_graph_scene_domain(path, row.get("layer"))
        cluster_id = f"domain:{domain}"
        node_id = _code_map_graph_scene_node_id(path)
        paths_by_id[node_id] = path
        lane_ids.add(role)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        tone = "amber" if warnings else ("green" if str(health.get("grade") or "") == "compliant" else "cyan")
        inspector_ref = f"code_map:file:{path}"
        nodes.append(
            {
                "id": node_id,
                "kind": role,
                "label": str(presentation.get("primary_label") or row.get("label") or path),
                "summary": row.get("summary"),
                "lane": role,
                "domain": domain,
                "row_id": cluster_id,
                "parent_cluster_id": cluster_id,
                "rank": index,
                "state": str(health.get("grade") or "fresh"),
                "priority": "high" if warnings else "medium",
                "tone": tone,
                "metrics": {
                    "fan_in": int(row.get("fan_in") or 0),
                    "fan_out": int(row.get("fan_out") or 0),
                    "warning_count": len(warnings),
                },
                "layout_constraints": {
                    "lane_id": role,
                    "row_id": cluster_id,
                    "stable_order": index,
                },
                "refs": [
                    {
                        "kind": "code_map_file",
                        "ref": path,
                    }
                ],
                "inspector_ref": inspector_ref,
            }
        )
        inspectors[inspector_ref] = {
            "kind": role,
            "title": path,
            "tone": tone,
            "state": str(health.get("grade") or "fresh"),
        }

    node_ids = {str(node.get("id")) for node in nodes}
    edges: list[dict[str, Any]] = []
    for index, edge in enumerate(returned_edges):
        source = _code_map_graph_scene_node_id(str(edge.get("from") or "").strip())
        target = _code_map_graph_scene_node_id(str(edge.get("to") or "").strip())
        if source not in node_ids or target not in node_ids:
            continue
        presentation = edge.get("presentation") if isinstance(edge.get("presentation"), Mapping) else {}
        relation = str(edge.get("kind") or "unknown")
        edge_role = str(presentation.get("edge_role") or _edge_role(relation))
        edges.append(
            {
                "id": f"edge:{graph_scene_core.stable_json_hash([source, relation, target, index], length=16)}",
                "source": source,
                "target": target,
                "relation": relation,
                "kind": relation,
                "confidence": edge.get("confidence"),
                "priority": "high" if edge.get("confidence") == "high" else "medium",
                "tone": "green" if edge.get("confidence") == "high" else "cyan",
                "bundle_id": f"edge_role:{edge_role}",
                "layout_constraints": {
                    "bundle_id": f"edge_role:{edge_role}",
                    "line_style_hint": presentation.get("edge_strength"),
                },
                "refs": [
                    {
                        "kind": "code_map_connection",
                        "ref": f"{paths_by_id.get(source, source)}->{paths_by_id.get(target, target)}",
                    }
                ],
            }
        )

    target_paths = [
        str(path)
        for path in (camera_target.get("target_paths") if isinstance(camera_target.get("target_paths"), list) else [])
        if path
    ]
    focus_node_ids = [
        _code_map_graph_scene_node_id(path)
        for path in target_paths
        if _code_map_graph_scene_node_id(path) in node_ids
    ]
    if not focus_node_ids:
        focus_node_ids = [str(node.get("id")) for node in nodes[: min(len(nodes), 12)]]
    focus_node_id_set = set(focus_node_ids)
    focus_edge_ids = [
        str(edge.get("id"))
        for edge in edges
        if str(edge.get("source")) in focus_node_id_set and str(edge.get("target")) in focus_node_id_set
    ]
    default_focus_id = "selected_neighborhood" if focus else "salient_overview"
    scene_source_fingerprint = graph_scene_core.source_fingerprint_for_payload(
        CODE_MAP_SCHEMA_VERSION,
        source_fingerprint,
        focus or "",
        file_rows,
        returned_edges,
    )
    scene = graph_scene_core.build_graph_scene(
        scene_id="code_map",
        source_schema=CODE_MAP_SCHEMA_VERSION,
        source_fingerprint=scene_source_fingerprint,
        generated_at=generated_at,
        nodes=nodes,
        edges=edges,
        lanes=[
            {"id": lane_id, "label": _code_map_graph_scene_label(lane_id), "rank": index}
            for index, lane_id in enumerate(sorted(lane_ids))
        ],
        rows=[
            {"id": f"domain:{domain}", "label": _code_map_graph_scene_label(domain), "rank": index}
            for index, domain in enumerate(sorted(domain_counts))
        ],
        clusters=[
            {
                "id": f"domain:{domain}",
                "kind": "domain",
                "label": _code_map_graph_scene_label(domain),
                "node_count": count,
                "edge_count": 0,
                "collapsed_default": count > 12,
            }
            for domain, count in sorted(domain_counts.items())
        ],
        focus_paths=[
            {
                "id": default_focus_id,
                "kind": "focus" if focus else "overview",
                "node_ids": focus_node_ids,
                "edge_ids": focus_edge_ids,
                "rank": 0,
            }
        ],
        inspectors=inspectors,
        default_projection="focus_context" if focus else "cluster_overview",
        default_focus_id=default_focus_id,
        resolver_refs={
            "manifest": "packet.graph_scene_manifest",
            "default_focus": "packet.graph_scene_default_focus",
            "delta": "packet.graph_scene_delta_manifest",
            "inspect": "packet.files[path]",
            "source_nodes": "packet.files",
            "source_edges": "packet.connections",
        },
        source_ref="code_map_packet_v1.files+connections",
        layout_constraints={
            "rankdir": "LR",
            "group_by": ["lane_id", "row_id"],
        },
    )
    manifest = scene["manifest"]
    return {
        "graph_scene_manifest": manifest,
        "graph_scene_default_focus": graph_scene_core.build_default_focus_excerpt(
            scene,
            focus_id=default_focus_id,
        ),
        "graph_scene_delta_manifest": graph_scene_core.build_graph_scene_delta_manifest(manifest),
        "graph_scene_validation": scene["validation"],
    }


def _build_projection_state(
    *,
    focus: str | None,
    file_rows: list[dict[str, Any]],
    returned_edges: list[dict[str, Any]],
    omitted_files: int,
    omitted_edges: int,
    omitted_overlays: int,
    receipt_reason: str | None,
    source_fingerprint: str,
    source_strategy: Mapping[str, Any],
) -> dict[str, Any]:
    render_ready = bool(file_rows)
    if not render_ready:
        state = "failed"
        readiness_reason = "no_files_returned"
    elif omitted_files or omitted_edges or omitted_overlays or receipt_reason:
        state = "partial_ready"
        readiness_reason = receipt_reason or "bounded_projection"
    else:
        state = "ready"
        readiness_reason = "all_requested_rows_returned"
    return {
        "schema": CODE_MAP_PROJECTION_STATE_SCHEMA_VERSION,
        "render_contract_version": CODE_MAP_RENDER_CONTRACT_VERSION,
        "state": state,
        "readiness_reason": readiness_reason,
        "render_ready": render_ready,
        "focus_path": focus,
        "source_fingerprint": source_fingerprint,
        "source_strategy": dict(source_strategy),
        "omitted": {
            "files": int(omitted_files),
            "edges": int(omitted_edges),
            "overlays": int(omitted_overlays),
        },
        "returned": {
            "files": len(file_rows),
            "edges": len(returned_edges),
        },
    }


def _ui_index_symbol_counts(ui_index: Mapping[str, Any] | None) -> dict[str, int]:
    """[ACTION] Estimate symbol counts from ui_index exports/types/props for fallback stats."""
    if not isinstance(ui_index, Mapping):
        return {}
    cache_key = id(ui_index)
    with _DERIVED_CACHE_LOCK:
        cached = _UI_INDEX_SYMBOL_COUNTS_CACHE.get(cache_key)
        if cached is not None:
            return dict(cached)
    files = ui_index.get("files")
    if not isinstance(files, list):
        return {}
    root_prefix = _ui_index_root_prefix(ui_index)
    out: dict[str, int] = {}
    for raw in files:
        if not isinstance(raw, Mapping):
            continue
        path = _repo_path_from_ui_index_path(raw.get("path"), root_prefix)
        if not path:
            continue
        count = 0
        for key in ("exports", "types", "props"):
            values = raw.get(key)
            if isinstance(values, list):
                count += len(values)
        out[path] = count
    with _DERIVED_CACHE_LOCK:
        _bounded_cache_set(
            _UI_INDEX_SYMBOL_COUNTS_CACHE,
            cache_key,
            out,
            max_entries=DERIVED_CACHE_MAX_ENTRIES,
        )
    return out


def _ui_index_import_edges(ui_index: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """[ACTION] Resolve relative ui_index imports into CodeMap connection rows."""
    if not isinstance(ui_index, Mapping):
        return []
    cache_key = id(ui_index)
    with _DERIVED_CACHE_LOCK:
        cached = _UI_INDEX_IMPORT_EDGES_CACHE.get(cache_key)
        if cached is not None:
            return list(cached)
    files = ui_index.get("files")
    if not isinstance(files, list):
        return []
    root_prefix = _ui_index_root_prefix(ui_index)
    raw_to_repo: dict[str, str] = {}
    for raw in files:
        if not isinstance(raw, Mapping):
            continue
        raw_path = _clean_ui_index_rel_path(raw.get("path"))
        repo_path = _repo_path_from_ui_index_path(raw_path, root_prefix)
        if raw_path and repo_path:
            raw_to_repo[raw_path] = repo_path

    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    for raw in files:
        if not isinstance(raw, Mapping):
            continue
        raw_path = _clean_ui_index_rel_path(raw.get("path"))
        src = raw_to_repo.get(raw_path)
        imports = raw.get("imports")
        if not src or not isinstance(imports, list):
            continue
        for import_spec in imports:
            target_raw = _resolve_ui_index_import(raw_path, str(import_spec or ""), raw_to_repo)
            if not target_raw:
                continue
            target = raw_to_repo.get(target_raw)
            if not target or target == src:
                continue
            key = (src, target, "import")
            edges[key] = {
                "from": src,
                "to": target,
                "kind": "import",
                "confidence": "high",
                "edge_sources": ["ui_index.json"],
                "evidence": str(import_spec or "").strip() or None,
            }
    rows = sorted(edges.values(), key=lambda r: (r["from"], r["to"], r["kind"]))
    with _DERIVED_CACHE_LOCK:
        _bounded_cache_set(
            _UI_INDEX_IMPORT_EDGES_CACHE,
            cache_key,
            rows,
            max_entries=DERIVED_CACHE_MAX_ENTRIES,
        )
    return list(rows)


def _resolve_ui_index_import(source_raw_path: str, import_spec: str, raw_to_repo: Mapping[str, str]) -> str | None:
    """[ACTION] Resolve a relative import specifier against ui_index-local paths."""
    spec = str(import_spec or "").strip().replace("\\", "/")
    if not spec.startswith("."):
        return None
    source_dir = posixpath.dirname(source_raw_path)
    base = posixpath.normpath(posixpath.join(source_dir, spec))
    if not base or base == "." or base == ".." or base.startswith("../"):
        return None
    candidates = [base]
    if not any(base.endswith(ext) for ext in UI_INDEX_IMPORT_EXTENSIONS):
        candidates.extend(f"{base}{ext}" for ext in UI_INDEX_IMPORT_EXTENSIONS)
    candidates.extend(f"{base}/index{ext}" for ext in UI_INDEX_IMPORT_EXTENSIONS)
    for candidate in candidates:
        if candidate in raw_to_repo:
            return candidate
    return None


def normalize_graph_edges(graph: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Project hologram `file_edges` rows into the canonical connection-row shape used by `code_map_packet_v1`.
    - Mechanism: For each row, derive `from`, `to`, `kind`, `confidence` (from `EDGE_CONFIDENCE_BY_KIND`), `edge_sources`, and `evidence`; drop rows that lack a usable `from`/`to`.
    - Reads: graph.file_edges via `_file_edges_from_graph`.
    - Guarantee: Returns a deterministic list sorted by `(from, to, kind)`; every row carries `confidence` in {high|medium|low} and a non-empty `edge_sources` list.
    - Fails: Never raises; malformed rows are skipped.
    """
    if isinstance(graph, Mapping):
        cache_key = id(graph)
        with _DERIVED_CACHE_LOCK:
            cached = _GRAPH_EDGE_CACHE.get(cache_key)
            if cached is not None:
                return list(cached)
    else:
        cache_key = None
    rows: list[dict[str, Any]] = []
    for raw in _file_edges_from_graph(graph):
        src = str(raw.get("source") or raw.get("from") or "").strip()
        dst = str(raw.get("target") or raw.get("to") or "").strip()
        if not src or not dst:
            continue
        kind = str(raw.get("kind") or "unknown").strip() or "unknown"
        confidence = EDGE_CONFIDENCE_BY_KIND.get(kind, "low")
        evidence = raw.get("evidence")
        rows.append(
            {
                "from": src,
                "to": dst,
                "kind": kind,
                "confidence": confidence,
                "edge_sources": ["graph.json"],
                "evidence": evidence if isinstance(evidence, str) else None,
            }
        )
    rows.sort(key=lambda r: (r["from"], r["to"], r["kind"]))
    if cache_key is not None:
        with _DERIVED_CACHE_LOCK:
            _bounded_cache_set(
                _GRAPH_EDGE_CACHE,
                cache_key,
                rows,
                max_entries=DERIVED_CACHE_MAX_ENTRIES,
            )
    return rows


def _index_edges_by_target(edges: Iterable[Mapping[str, Any]]) -> dict[str, list[str]]:
    """[ACTION] Build `target -> [source, ...]` adjacency for reverse-BFS."""
    out: dict[str, list[str]] = {}
    for edge in edges:
        dst = str(edge.get("to") or "").strip()
        src = str(edge.get("from") or "").strip()
        if not dst or not src:
            continue
        out.setdefault(dst, []).append(src)
    return out


def compute_reverse_bfs(
    edges_by_target: Mapping[str, list[str]],
    target_path: str,
    max_depth: int = 4,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Walk reverse dependency edges from `target_path` so blast-radius packets can name direct + transitive dependents bucketed by depth.
    - Mechanism: BFS along the `target -> [source]` adjacency; track first-discovery depth per file; cycles are handled by the visited-set guard.
    - Reads: `edges_by_target` adjacency, target_path, max_depth.
    - Guarantee: Returns a dict with `direct_dependents` (depth==1, sorted), `transitive_dependents` (depth>=2, sorted), and `depth_buckets` keyed `"1"`, `"2"`, `"3+"`. Missing target yields empty lists.
    - Fails: Never raises; non-string/empty inputs are coerced or short-circuit to empty output.
    """
    target = str(target_path or "").strip()
    direct: list[str] = []
    transitive: list[str] = []
    depth_buckets: dict[str, list[str]] = {"1": [], "2": [], "3+": []}
    if not target or target not in edges_by_target:
        return {
            "direct_dependents": direct,
            "transitive_dependents": transitive,
            "depth_buckets": {k: sorted(v) for k, v in depth_buckets.items()},
        }
    visited: set[str] = {target}
    queue: deque[tuple[str, int]] = deque()
    for src in edges_by_target.get(target, []):
        if src in visited:
            continue
        visited.add(src)
        queue.append((src, 1))
    while queue:
        node, depth = queue.popleft()
        if depth == 1:
            direct.append(node)
            depth_buckets["1"].append(node)
        elif depth == 2:
            transitive.append(node)
            depth_buckets["2"].append(node)
        else:
            transitive.append(node)
            depth_buckets["3+"].append(node)
        if depth >= max(1, int(max_depth)):
            continue
        for next_src in edges_by_target.get(node, []):
            if next_src in visited:
                continue
            visited.add(next_src)
            queue.append((next_src, depth + 1))
    return {
        "direct_dependents": sorted(direct),
        "transitive_dependents": sorted(transitive),
        "depth_buckets": {k: sorted(v) for k, v in depth_buckets.items()},
    }


def build_paper_module_overlay_index(root: Path, paper_modules_index: Mapping[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    """
    [ACTION]
    - Teleology: Build a `path -> [{slug, status, relation}]` index so every code-map file row can carry its paper-module overlay without re-scanning markdown per file.
    - Mechanism: Iterate `_index.json::modules`, read each module markdown, run `extract_code_loci_paths` over the `## Code loci` section to find the paths the module cites, and reverse-index path -> module rows.
    - Reads: `<root>/codex/doctrine/paper_modules/<file>.md` for each module.
    - Guarantee: Returns a dict; absent index yields `{}`. The relation is always `"code_locus"` in v1; status carries the module's `status` from the index.
    - Fails: Never raises; markdown read failures are skipped.
    """
    overlay: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(paper_modules_index, Mapping):
        return overlay
    modules = paper_modules_index.get("modules")
    if not isinstance(modules, list):
        return overlay
    for module in modules:
        if not isinstance(module, Mapping):
            continue
        slug = str(module.get("slug") or "").strip()
        file_rel = str(module.get("file") or "").strip()
        status = str(module.get("status") or "").strip() or None
        if not slug or not file_rel:
            continue
        body = _read_text(root / file_rel)
        if not body:
            continue
        loci_section = _extract_code_loci_section(body)
        if not loci_section:
            continue
        for path in extract_code_loci_paths(loci_section):
            overlay.setdefault(path, []).append(
                {"slug": slug, "relation": "code_locus", "status": status}
            )
    return overlay


def _extract_code_loci_section(body: str) -> str:
    """[ACTION] Slice the `## Code loci` section out of a paper-module markdown body."""
    if not body:
        return ""
    needle = "## Code loci"
    start = body.find(needle)
    if start < 0:
        return ""
    rest = body[start + len(needle):]
    next_h2 = rest.find("\n## ")
    if next_h2 < 0:
        return rest
    return rest[:next_h2]


def build_annex_pattern_overlay_index(annex_distillation: Mapping[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    """
    [ACTION]
    - Teleology: Build a `path -> [{annex_slug, pattern_id, axis, lane, status}]` index from `annexes/annex_distillation_index.json::by_local_target` so code-map file rows carry their annex-pattern overlay.
    - Mechanism: Iterate `by_local_target` keys (which are local target paths or path prefixes), copy a compact subset of each row (slug, pattern id, axis, lane, status), and key them under the local target path.
    - Reads: annex_distillation_index payload.
    - Guarantee: Returns a dict; absent payload yields `{}`. The path key is taken verbatim from `by_local_target`; lookup is exact-match in v1.
    - Fails: Never raises; malformed rows are skipped.
    """
    overlay: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(annex_distillation, Mapping):
        return overlay
    by_local_target = annex_distillation.get("by_local_target")
    if not isinstance(by_local_target, Mapping):
        return overlay
    for path_key, rows in by_local_target.items():
        if not isinstance(rows, list):
            continue
        path = str(path_key or "").strip()
        if not path:
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            overlay.setdefault(path, []).append(
                {
                    "annex_slug": str(row.get("annex_slug") or "").strip() or None,
                    "pattern_id": str(row.get("pattern_id") or row.get("id") or "").strip() or None,
                    "axis": str(row.get("axis") or "").strip() or None,
                    "lane": row.get("lane"),
                    "status": str(row.get("status") or row.get("adoption_status") or "").strip() or None,
                }
            )
    return overlay


def build_frontend_view_overlay_index(navigation_graph: Mapping[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    """
    [ACTION]
    - Teleology: Build a `path -> [{view_id, route, kind}]` index so any code file that hosts a frontend view's source carries that overlay.
    - Mechanism: Walk `views[]`, read each view's `evidence.file`, and reverse-index path -> view rows.
    - Reads: navigation_graph payload.
    - Guarantee: Returns a dict; absent payload yields `{}`.
    - Fails: Never raises; malformed rows are skipped.
    """
    overlay: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(navigation_graph, Mapping):
        return overlay
    views = navigation_graph.get("views")
    if not isinstance(views, list):
        return overlay
    for view in views:
        if not isinstance(view, Mapping):
            continue
        evidence = view.get("evidence")
        if not isinstance(evidence, Mapping):
            continue
        path = str(evidence.get("file") or "").strip()
        if not path:
            continue
        overlay.setdefault(path, []).append(
            {
                "view_id": str(view.get("id") or "").strip() or None,
                "route": str(view.get("route") or "").strip() or None,
                "kind": str(view.get("kind") or "").strip() or None,
            }
        )
    return overlay


def _empty_overlays() -> dict[str, list[Any]]:
    """[ACTION] Return the canonical empty `overlays` block shape attached to each file row."""
    return {
        "paper_modules": [],
        "semantic_routes": [],
        "annex_patterns": [],
        "frontend_views": [],
        "workingness": [],
    }


def attach_file_overlays(
    file_row: dict[str, Any],
    *,
    paper_module_overlay: Mapping[str, list[dict[str, Any]]],
    annex_pattern_overlay: Mapping[str, list[dict[str, Any]]],
    frontend_view_overlay: Mapping[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """[ACTION] Mutate a file_row in place to add the overlays block from the three precomputed indexes."""
    path = str(file_row.get("path") or "").strip()
    overlays = _empty_overlays()
    if path:
        overlays["paper_modules"] = list(paper_module_overlay.get(path, []))
        overlays["annex_patterns"] = list(annex_pattern_overlay.get(path, []))
        overlays["frontend_views"] = list(frontend_view_overlay.get(path, []))
    file_row["overlays"] = overlays
    return file_row


def _file_row_from_sources(
    file_entry: Mapping[str, Any],
    *,
    quality_by_path: Mapping[str, dict[str, Any]],
    edges_outbound_count: Mapping[str, int],
    edges_inbound_count: Mapping[str, int],
) -> dict[str, Any]:
    """[ACTION] Build one canonical file row for the code_map packet from graph + quality."""
    path = str(file_entry.get("path") or "").strip()
    quality = quality_by_path.get(path, {})
    return {
        "path": path,
        "layer": str(file_entry.get("group_id") or file_entry.get("layer") or "").strip() or None,
        "summary": str(file_entry.get("summary") or "").strip() or None,
        "fan_in": int(edges_inbound_count.get(path, 0)),
        "fan_out": int(edges_outbound_count.get(path, 0)),
        "health": {
            "grade": str(quality.get("status") or "").strip() or None,
            "warnings": list(quality.get("quality_flags") or []) or list(quality.get("derivation_warnings") or []),
        },
        "overlays": _empty_overlays(),
    }


def _missing_overlay_reason(
    *,
    paper_modules_present: bool,
    route_coverage_present: bool,
    annex_present: bool,
    nav_present: bool,
) -> tuple[int, str | None]:
    """[ACTION] Compute the omitted-overlay count + reason string for the omission_receipt."""
    omitted = 0
    reasons: list[str] = []
    # semantic_routes overlay is not yet wired in v1
    omitted += 1
    reasons.append("semantic_routes_overlay_not_yet_wired")
    # workingness overlay is not yet wired in v1
    omitted += 1
    reasons.append("workingness_overlay_not_yet_wired")
    if not paper_modules_present:
        omitted += 1
        reasons.append("paper_module_index_missing")
    if not route_coverage_present:
        omitted += 1
        reasons.append("route_coverage_missing")
    if not annex_present:
        omitted += 1
        reasons.append("annex_distillation_index_missing")
    if not nav_present:
        omitted += 1
        reasons.append("frontend_navigation_graph_missing")
    return omitted, "; ".join(reasons) if reasons else None


def _route_target_count(route_coverage: Mapping[str, Any] | None) -> int:
    """[ACTION] Pull `summary.route_target_count` from the route-coverage payload, defaulting to 0."""
    if not isinstance(route_coverage, Mapping):
        return 0
    summary = route_coverage.get("summary")
    if not isinstance(summary, Mapping):
        return 0
    try:
        return int(summary.get("route_target_count") or 0)
    except (TypeError, ValueError):
        return 0


def build_code_map_packet(
    *,
    root: Path,
    focus_path: str | None = None,
    max_files: int = 300,
    include_overlays: bool = True,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Emit one `code_map_packet_v1` covering the repo's code-architecture projection — file rows, edges, stats, overlays — sourced only from existing substrate, never re-running any parser.
    - Mechanism: Load hologram + overlay sources, normalize edges, compute fan-in/fan-out, build per-file rows, attach overlays (when `include_overlays`), apply `focus_path` filter (which keeps only the focus file plus its direct neighbors), truncate to `max_files` with an honest omission_receipt.
    - Reads: hologram (`graph.json`, `quality.json`, `symbols.json`), `_index.json`, `annex_distillation_index.json`, `navigation_graph.json` — all best-effort.
    - Guarantee: Returns a dict matching the schema sketched in `codex/doctrine/paper_modules/codeflow_assimilation.md::Packet contract sketch`.
    - Fails: Never raises on absent sources; missing substrate degrades the packet via `omission_receipt`.
    """
    sources = load_hologram_sources(root)
    paper_modules_index = load_paper_module_index(root)
    route_coverage = load_route_coverage(root)
    annex_distillation = load_annex_distillation_index(root)
    navigation_graph = load_frontend_navigation_graph(root)

    file_entries = _files_from_graph(sources["graph"])
    quality_by_path = _quality_by_path(sources["quality"])
    symbol_counts = _symbol_count_by_path(sources["symbols"])
    edges = normalize_graph_edges(sources["graph"])
    ui_index_fallback = False
    ui_index_merged = False
    scope_index_fallback = False
    scope_index_merged = False
    repo_python_merged = False
    repo_python_fallback = False
    repo_python_import_merged = False
    repo_python_import_parse_capped = False
    focus = str(focus_path or "").strip() or None
    ui_file_entries = _ui_index_file_entries(sources.get("ui_index"))
    ui_edges = _ui_index_import_edges(sources.get("ui_index"))
    scope_file_entries = _scope_index_file_entries(sources.get("scope_index"))
    scope_edges = _scope_index_connection_edges(sources.get("scope_index"))
    repo_file_entries: list[dict[str, Any]] = []
    graph_has_python = any(
        str(row.get("path") or "").strip().endswith(REPO_PYTHON_EXTENSIONS)
        for row in file_entries
    )
    if scope_file_entries:
        repo_python_merged = False
        repo_python_import_merged = False
        scope_index_fallback = not file_entries or not graph_has_python
        scope_index_merged = not scope_index_fallback
        # In this branch the generated Python scope index is the fallback/merge
        # authority. The UI index is an overlay source, not the primary packet
        # fallback, even when the hologram graph is absent or UI-only. Do not
        # walk/parse the live repo here; this endpoint is an interactive
        # backend-for-frontend read model, so generated projection sidecars are
        # the latency boundary.
        ui_index_fallback = False
        ui_index_merged = bool(ui_file_entries)
        file_entries = _merge_file_entries(file_entries, scope_file_entries, ui_file_entries)
        symbol_counts = {
            **_scope_index_symbol_counts(sources.get("scope_index")),
            **symbol_counts,
            **_ui_index_symbol_counts(sources.get("ui_index")),
        }
        edges = _merge_connections(edges, scope_edges, ui_edges)
    elif not file_entries or not graph_has_python:
        if ui_file_entries:
            ui_index_fallback = True
            repo_file_entries = _repo_python_file_entries(root)
            repo_paths = {
                str(row.get("path") or "").strip()
                for row in repo_file_entries
                if str(row.get("path") or "").strip()
            }
            repo_parse_paths = set(sorted(repo_paths, key=_repo_code_sort_key)[:REPO_PYTHON_IMPORT_PARSE_CAP])
            if focus and focus in repo_paths:
                repo_parse_paths.add(focus)
            repo_python_import_parse_capped = len(repo_paths) > len(repo_parse_paths)
            repo_edges, repo_symbol_counts = _repo_python_import_edges_and_symbols(
                root,
                repo_file_entries,
                parse_paths=repo_parse_paths,
            ) if repo_parse_paths else ([], {})
            repo_python_fallback = bool(repo_file_entries)
            file_entries = _merge_file_entries(repo_file_entries, ui_file_entries)
            symbol_counts = {
                **repo_symbol_counts,
                **_ui_index_symbol_counts(sources.get("ui_index")),
            }
            edges = _merge_connections(repo_edges, ui_edges)
    elif ui_file_entries:
        ui_index_merged = True
        file_entries = _merge_file_entries(file_entries, ui_file_entries)
        symbol_counts = {
            **symbol_counts,
            **_ui_index_symbol_counts(sources.get("ui_index")),
        }
        edges = _merge_connections(edges, ui_edges)
    edges_outbound_count: dict[str, int] = {}
    edges_inbound_count: dict[str, int] = {}
    for edge in edges:
        edges_outbound_count[edge["from"]] = edges_outbound_count.get(edge["from"], 0) + 1
        edges_inbound_count[edge["to"]] = edges_inbound_count.get(edge["to"], 0) + 1

    if focus:
        keep_paths = {focus}
        for edge in edges:
            if edge["from"] == focus:
                keep_paths.add(edge["to"])
            if edge["to"] == focus:
                keep_paths.add(edge["from"])
        focused_files = [row for row in file_entries if str(row.get("path") or "").strip() in keep_paths]
        # Both endpoints must be in keep_paths — no dangling connections referencing
        # files the packet did not return.
        focused_edges = [edge for edge in edges if edge["from"] in keep_paths and edge["to"] in keep_paths]
        # Pin the focus file first so truncation never elides it.
        focused_files.sort(key=lambda r: (str(r.get("path") or "").strip() != focus, str(r.get("path") or "")))
    else:
        focused_files = list(file_entries)
        focused_edges = list(edges)

    max_files_int = max(1, int(max_files))
    truncated = focused_files[:max_files_int]
    omitted_files = max(0, len(focused_files) - len(truncated))
    returned_paths = {str(row.get("path") or "").strip() for row in truncated}
    # After truncation, drop any edge that references an omitted file. Count the loss.
    returned_edges = [
        edge for edge in focused_edges
        if edge["from"] in returned_paths and edge["to"] in returned_paths
    ]
    omitted_edges = max(0, len(focused_edges) - len(returned_edges))

    if include_overlays:
        paper_module_overlay = build_paper_module_overlay_index(root, paper_modules_index)
        annex_pattern_overlay = build_annex_pattern_overlay_index(annex_distillation)
        frontend_view_overlay = build_frontend_view_overlay_index(navigation_graph)
    else:
        paper_module_overlay = {}
        annex_pattern_overlay = {}
        frontend_view_overlay = {}

    file_rows: list[dict[str, Any]] = []
    for entry in truncated:
        row = _file_row_from_sources(
            entry,
            quality_by_path=quality_by_path,
            edges_outbound_count=edges_outbound_count,
            edges_inbound_count=edges_inbound_count,
        )
        if include_overlays:
            attach_file_overlays(
                row,
                paper_module_overlay=paper_module_overlay,
                annex_pattern_overlay=annex_pattern_overlay,
                frontend_view_overlay=frontend_view_overlay,
            )
        file_rows.append(row)

    omitted_overlays, omission_reason = (0, None)
    if include_overlays:
        omitted_overlays, omission_reason = _missing_overlay_reason(
            paper_modules_present=paper_modules_index is not None,
            route_coverage_present=route_coverage is not None,
            annex_present=annex_distillation is not None,
            nav_present=navigation_graph is not None,
        )

    receipt_reason_parts: list[str] = []
    if omitted_files > 0:
        receipt_reason_parts.append("truncated_to_max_files")
    if omitted_edges > 0 and omitted_files == 0:
        # Edge truncation without file truncation should still surface a reason.
        receipt_reason_parts.append("dropped_edges_to_omitted_files")
    elif omitted_edges > 0:
        receipt_reason_parts.append("dropped_edges_to_omitted_files")
    if omission_reason:
        receipt_reason_parts.append(omission_reason)
    if ui_index_fallback:
        receipt_reason_parts.append("used_ui_index_fallback")
    if scope_index_fallback:
        receipt_reason_parts.append("primary_hologram_graph_missing_or_ui_only; used_std_python_scope_index_fallback")
    if scope_index_merged:
        receipt_reason_parts.append("merged_std_python_scope_index")
    if repo_python_fallback:
        receipt_reason_parts.append("primary_hologram_graph_and_scope_index_missing; used_repo_python_import_fallback")
    if repo_python_merged:
        receipt_reason_parts.append("merged_repo_python_files")
    if repo_python_import_merged:
        receipt_reason_parts.append("merged_repo_python_import_edges")
    if repo_python_import_parse_capped:
        receipt_reason_parts.append("repo_python_import_parse_cap_applied")
    if ui_index_merged:
        receipt_reason_parts.append("merged_ui_index")
    receipt_reason: str | None = "; ".join(receipt_reason_parts) if receipt_reason_parts else None

    fingerprint = compute_source_fingerprint(
        root,
        [
            HOLOGRAM_GRAPH_PATH,
            HOLOGRAM_QUALITY_PATH,
            HOLOGRAM_SYMBOLS_PATH,
            HOLOGRAM_UI_INDEX_PATH,
            PYTHON_SCOPE_INDEX_PATH,
            PAPER_MODULE_INDEX_PATH,
            PAPER_MODULE_ROUTE_COVERAGE_PATH,
            ANNEX_DISTILLATION_INDEX_PATH,
            FRONTEND_NAVIGATION_GRAPH_PATH,
        ],
    )

    paper_module_count = 0
    if isinstance(paper_modules_index, Mapping):
        modules = paper_modules_index.get("modules")
        if isinstance(modules, list):
            paper_module_count = len(modules)
    annex_pattern_count = 0
    if isinstance(annex_distillation, Mapping):
        annex_pattern_count = int(annex_distillation.get("pattern_count") or 0)
    route_target_count = _route_target_count(route_coverage)

    _attach_file_presentation(file_rows, focus=focus)
    _attach_connection_presentation(returned_edges)
    composition_stats = _packet_composition_stats(file_rows, returned_edges)
    generated_at = _now_iso()
    graph_presentation = _build_graph_presentation_summary(file_rows, returned_edges)
    camera_target = _build_camera_target(file_rows, focus=focus)
    source_strategy = {
        "primary": "std_python_scope_index" if scope_index_fallback else "hologram_graph",
        "scope_index_fallback": scope_index_fallback,
        "scope_index_merged": scope_index_merged,
        "ui_index_fallback": ui_index_fallback,
        "ui_index_merged": ui_index_merged,
        "repo_python_fallback": repo_python_fallback,
        "repo_python_merged": repo_python_merged,
        "repo_python_import_merged": repo_python_import_merged,
        "repo_python_import_parse_capped": repo_python_import_parse_capped,
        "runtime_repo_scan": (
            "fallback_only"
            if repo_python_fallback
            else "disabled_when_generated_scope_index_present"
            if scope_file_entries
            else "not_needed"
        ),
    }
    estimated_packet_weight = {
        "schema": "code_map_estimated_packet_weight_v1",
        "source_file_count": len(file_entries),
        "selected_file_count": len(focused_files),
        "returned_file_count": len(file_rows),
        "source_edge_count": len(edges),
        "selected_edge_count": len(focused_edges),
        "returned_edge_count": len(returned_edges),
        "omitted_file_count": omitted_files,
        "omitted_edge_count": omitted_edges,
        "omitted_overlay_count": omitted_overlays,
    }
    projection_state = _build_projection_state(
        focus=focus,
        file_rows=file_rows,
        returned_edges=returned_edges,
        omitted_files=omitted_files,
        omitted_edges=omitted_edges,
        omitted_overlays=omitted_overlays,
        receipt_reason=receipt_reason,
        source_fingerprint=fingerprint,
        source_strategy=source_strategy,
    )
    graph_scene_payload = _build_code_map_graph_scene_payload(
        generated_at=generated_at,
        source_fingerprint=fingerprint,
        focus=focus,
        file_rows=file_rows,
        returned_edges=returned_edges,
        camera_target=camera_target,
    )

    return {
        "kind": "kernel.code_map",
        "schema_version": CODE_MAP_SCHEMA_VERSION,
        "render_contract_version": CODE_MAP_RENDER_CONTRACT_VERSION,
        "generated_at": generated_at,
        "source": {
            "graph": str(HOLOGRAM_GRAPH_PATH),
            "quality": str(HOLOGRAM_QUALITY_PATH),
            "symbols": str(HOLOGRAM_SYMBOLS_PATH),
            "ui_index": str(HOLOGRAM_UI_INDEX_PATH),
            "scope_index": str(PYTHON_SCOPE_INDEX_PATH),
            "paper_modules": str(PAPER_MODULE_INDEX_PATH),
            "route_coverage": str(PAPER_MODULE_ROUTE_COVERAGE_PATH),
            "annex_distillation": str(ANNEX_DISTILLATION_INDEX_PATH),
            "frontend_navigation": str(FRONTEND_NAVIGATION_GRAPH_PATH),
            "source_fingerprint": fingerprint,
        },
        "projection_state": projection_state,
        "estimated_packet_weight": estimated_packet_weight,
        "graph_presentation": graph_presentation,
        "camera_target": camera_target,
        "focus_path": focus,
        "stats": {
            "file_count": len(file_rows),
            "symbol_count": int(sum(symbol_counts.get(row["path"], 0) for row in file_rows)),
            "edge_count": len(returned_edges),
            "paper_module_count": paper_module_count,
            "route_target_count": route_target_count,
            "annex_pattern_count": annex_pattern_count,
            "security_finding_count": 0,
            **composition_stats,
        },
        "files": file_rows,
        "connections": returned_edges,
        "issues": [],
        "patterns": [],
        "security": [],
        "omission_receipt": build_omission_receipt(
            omitted_files=omitted_files,
            omitted_edges=omitted_edges,
            omitted_overlays=omitted_overlays,
            reason=receipt_reason,
        ),
        "known_limits": list(KNOWN_LIMITS),
        **graph_scene_payload,
    }


def _system_impact_paper_modules(
    impacted_paths: set[str],
    paper_module_overlay: Mapping[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """[ACTION] Project the paper-module overlay rows touched by an impact set into a sorted impact list."""
    seen: dict[str, dict[str, Any]] = {}
    for path in impacted_paths:
        for entry in paper_module_overlay.get(path, []):
            slug = entry.get("slug")
            if not slug or slug in seen:
                continue
            seen[slug] = {
                "slug": slug,
                "relation": entry.get("relation"),
                "status": entry.get("status"),
                "via_path": path,
            }
    return sorted(seen.values(), key=lambda r: str(r.get("slug") or ""))


def _system_impact_annex_patterns(
    impacted_paths: set[str],
    annex_pattern_overlay: Mapping[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """[ACTION] Project annex pattern overlay rows touched by an impact set into a sorted impact list."""
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for path in impacted_paths:
        for entry in annex_pattern_overlay.get(path, []):
            slug = str(entry.get("annex_slug") or "")
            pid = str(entry.get("pattern_id") or "")
            key = (slug, pid)
            if not slug or not pid or key in seen:
                continue
            seen[key] = {
                "annex_slug": slug,
                "pattern_id": pid,
                "axis": entry.get("axis"),
                "lane": entry.get("lane"),
                "status": entry.get("status"),
                "via_path": path,
            }
    return sorted(seen.values(), key=lambda r: (str(r.get("annex_slug") or ""), str(r.get("pattern_id") or "")))


def _system_impact_frontend_views(
    impacted_paths: set[str],
    frontend_view_overlay: Mapping[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """[ACTION] Project frontend view overlay rows touched by an impact set into a sorted impact list."""
    seen: dict[str, dict[str, Any]] = {}
    for path in impacted_paths:
        for entry in frontend_view_overlay.get(path, []):
            view_id = entry.get("view_id")
            if not view_id or view_id in seen:
                continue
            seen[view_id] = {
                "view_id": view_id,
                "route": entry.get("route"),
                "kind": entry.get("kind"),
                "via_path": path,
            }
    return sorted(seen.values(), key=lambda r: str(r.get("view_id") or ""))


def _empty_system_impact() -> dict[str, list[Any]]:
    """[ACTION] Return the canonical empty `system_impact` block shape used by blast_radius packets."""
    return {
        "paper_modules": [],
        "frontend_views": [],
        "standards": [],
        "skills": [],
        "annex_patterns": [],
        "routes": [],
        "tests": [],
        "render_checks": [],
    }


def _risk_score(file_impact: Mapping[str, Any]) -> int:
    """[ACTION] Compute a small impact score from depth-bucketed counts (1-weight, 2-weight, 3-weight)."""
    direct = file_impact.get("depth_buckets", {}).get("1", []) or []
    second = file_impact.get("depth_buckets", {}).get("2", []) or []
    deeper = file_impact.get("depth_buckets", {}).get("3+", []) or []
    return 3 * len(direct) + 2 * len(second) + 1 * len(deeper)


def _verification_command(
    *,
    cmd_id: str,
    argv: list[str],
    reason: str,
    source: str,
    effect: str,
    confidence: str,
) -> dict[str, Any]:
    """[ACTION] Build one canonical suggested_verification command row with both `argv` (automation-safe) and `display` (human-readable) keys."""
    return {
        "id": cmd_id,
        "argv": list(argv),
        "display": " ".join(argv),
        "reason": reason,
        "source": source,
        "effect": effect,
        "confidence": confidence,
    }


def build_suggested_verification(
    *,
    target_path: str,
    file_impact: Mapping[str, Any],
    system_impact: Mapping[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Turn a blast-radius packet's impact set into a bounded, deterministic, **read-only** proof plan: "what proof should I run before believing the change is safe?" The plan is evidence the operator can copy and run; nothing here executes.
    - Mechanism: Apply the five derivation rules from `codeflow_assimilation.md::Commit 3.1`: (1) impacted `system/server/tests/test_*.py` files become per-file pytest commands; (2) non-empty paper-module overlay emits a paper-module check; (3) non-empty annex-pattern overlay emits an annex distillation projection refresh; (4) frontend-view overlay or any UI-impacted path emits the views-rebuild + view-graph-check + station_render preflight trio; (5) target or impact set touching the projection library or its endpoint files emits the library + endpoint pytest matrix. Dedupe by `argv`; cap at `SUGGESTED_VERIFICATION_COMMAND_CAP`; emit a `suggested_verification.omission_receipt` when truncated.
    - Reads: target_path, file_impact (direct/transitive/depth_buckets), system_impact (paper_modules, annex_patterns, frontend_views).
    - Guarantee: Returns a dict with `schema_version`, `commands` (each with both `argv` and `display`), and `omission_receipt`. Empty impact yields empty `commands`.
    - Fails: Never raises; missing impact buckets are treated as empty.
    """
    direct_paths: set[str] = set(file_impact.get("direct_dependents") or [])
    second_paths: set[str] = set(file_impact.get("depth_buckets", {}).get("2") or [])
    impacted_paths: set[str] = direct_paths | set(file_impact.get("transitive_dependents") or [])

    target = str(target_path or "").strip()
    paper_modules_hit = bool(system_impact.get("paper_modules"))
    annex_patterns_hit = bool(system_impact.get("annex_patterns"))
    frontend_views_hit = bool(system_impact.get("frontend_views"))
    ui_path_impact = target.startswith("system/server/ui/") or any(
        path.startswith("system/server/ui/") for path in impacted_paths
    )
    target_is_projection_lib = target == PROJECTION_LIBRARY_PATH
    endpoint_impacted = (
        target in PROJECTION_PLANE_ENDPOINT_FILES
        or bool(impacted_paths & PROJECTION_PLANE_ENDPOINT_FILES)
    )

    commands: list[dict[str, Any]] = []

    # Rule 1 — impacted test files become per-file pytest commands.
    test_paths = sorted(
        path for path in impacted_paths
        if path.startswith("system/server/tests/") and path.split("/")[-1].startswith("test_") and path.endswith(".py")
    )
    for path in test_paths:
        if path in direct_paths:
            depth_label, source_tag, conf = "depth==1", "file_impact.depth_buckets.1", "high"
            depth_phrase = "Direct"
        elif path in second_paths:
            depth_label, source_tag, conf = "depth==2", "file_impact.depth_buckets.2", "medium"
            depth_phrase = "Second-hop"
        else:
            depth_label, source_tag, conf = "depth>=3", "file_impact.depth_buckets.3+", "low"
            depth_phrase = "Deep transitive"
        commands.append(
            _verification_command(
                cmd_id=f"pytest:{path}",
                argv=["./repo-python", "-m", "pytest", path, "-v"],
                reason=f"{depth_phrase} ({depth_label}) reverse-dependent test file touches this blast-radius target.",
                source=source_tag,
                effect="read_only",
                confidence=conf,
            )
        )

    # Rule 2 — paper-module overlay non-empty.
    if paper_modules_hit:
        commands.append(
            _verification_command(
                cmd_id="paper_module_check",
                argv=[
                    "./repo-python",
                    "tools/meta/factory/build_paper_module_index.py",
                    "--check",
                    "--report",
                ],
                reason=(
                    f"{len(system_impact['paper_modules'])} paper module(s) cite the impacted file set; "
                    "validate code_loci freshness + sidecar sync before merging."
                ),
                source="system_impact.paper_modules",
                effect="read_only",
                confidence="high",
            )
        )

    # Rule 3 — annex-pattern overlay non-empty.
    if annex_patterns_hit:
        commands.append(
            _verification_command(
                cmd_id="annex_distillation_refresh",
                argv=[
                    "./repo-python",
                    "tools/meta/factory/build_annex_distillation_projection.py",
                    "--write",
                ],
                reason=(
                    f"{len(system_impact['annex_patterns'])} annex pattern row(s) target the impacted file set; "
                    "refresh the cross-annex projection so adoption status counts reflect the change."
                ),
                source="system_impact.annex_patterns",
                effect="derived_refresh",
                confidence="medium",
            )
        )

    # Rule 4 — frontend views or any impacted path under system/server/ui/.
    if frontend_views_hit or ui_path_impact:
        if frontend_views_hit:
            source_tag = "system_impact.frontend_views"
        else:
            source_tag = "file_impact (system/server/ui/ prefix)"
        commands.append(
            _verification_command(
                cmd_id="views_rebuild",
                argv=["./repo-python", "kernel.py", "--views-rebuild"],
                reason="Frontend view substrate is impacted; rebuild the navigation graph projection.",
                source=source_tag,
                effect="derived_refresh",
                confidence="medium",
            )
        )
        commands.append(
            _verification_command(
                cmd_id="view_graph_check",
                argv=["./repo-python", "kernel.py", "--view-graph-check"],
                reason="Frontend view substrate is impacted; verify zero drift in the navigation graph.",
                source=source_tag,
                effect="read_only",
                confidence="high",
            )
        )
        commands.append(
            _verification_command(
                cmd_id="station_render_preflight",
                argv=["./repo-python", "-m", "tools.meta.observability.station_render", "preflight"],
                reason="Frontend view substrate is impacted; preflight Station capture engines before relying on screenshots.",
                source=source_tag,
                effect="read_only",
                confidence="high",
            )
        )

    # Rule 5 — target or impact set touches the projection plane.
    if target_is_projection_lib or endpoint_impacted:
        commands.append(
            _verification_command(
                cmd_id="pytest:projection_plus_endpoint",
                argv=[
                    "./repo-python",
                    "-m",
                    "pytest",
                    "system/server/tests/test_code_architecture_projection.py",
                    "system/server/tests/test_world_model_code_map.py",
                    "-v",
                ],
                reason=(
                    "Target or impact set touches the Code Architecture Projection Plane "
                    "(library or endpoints); rerun the library + endpoint proof matrix."
                ),
                source="target_path or endpoint_impact",
                effect="read_only",
                confidence="high",
            )
        )

    # Dedupe by argv (the user-spec dedupe key); preserve insertion order.
    seen_argv: set[tuple[str, ...]] = set()
    deduped: list[dict[str, Any]] = []
    for cmd in commands:
        key = tuple(cmd["argv"])
        if key in seen_argv:
            continue
        seen_argv.add(key)
        deduped.append(cmd)

    # Sort by confidence (high first) then by id so the cap keeps the most useful
    # commands rather than alphabetically-early low-confidence ones.
    confidence_rank = {"high": 0, "medium": 1, "low": 2}
    deduped.sort(key=lambda c: (confidence_rank.get(str(c.get("confidence")), 3), str(c.get("id") or "")))

    cap = SUGGESTED_VERIFICATION_COMMAND_CAP
    omitted = max(0, len(deduped) - cap)
    truncated = deduped[:cap]

    receipt = {
        "omitted_commands": omitted,
        "reason": f"truncated_to_command_cap_{cap}" if omitted > 0 else None,
    }

    return {
        "schema_version": SUGGESTED_VERIFICATION_SCHEMA_VERSION,
        "commands": truncated,
        "omission_receipt": receipt,
    }


def build_blast_radius_packet(
    *,
    root: Path,
    target_path: str,
    max_depth: int = 4,
    include_system_impact: bool = True,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Emit one `blast_radius_packet_v1` for `target_path` answering "what part of the system's ontology, routing, UI, tests, and external-pattern adoption is affected if I touch this file?" — system-radius, not just file-radius.
    - Mechanism: Load hologram + overlay sources, normalize edges, run `compute_reverse_bfs`, then project overlay overlap into `system_impact.{paper_modules,frontend_views,annex_patterns}` (other system-impact buckets remain empty arrays in v1, honestly emitted).
    - Reads: hologram graph, paper-module index, annex distillation index, frontend navigation graph — all best-effort.
    - Guarantee: Returns a dict matching the schema sketched in `codex/doctrine/paper_modules/codeflow_assimilation.md::Packet contract sketch`. Missing target yields empty file_impact + empty system_impact + low confidence.
    - Fails: Never raises on absent sources or missing target.
    """
    sources = load_hologram_sources(root)
    paper_modules_index = load_paper_module_index(root)
    annex_distillation = load_annex_distillation_index(root)
    navigation_graph = load_frontend_navigation_graph(root)

    target = str(target_path or "").strip()
    file_entries = _files_from_graph(sources["graph"])
    edges = normalize_graph_edges(sources["graph"])
    edge_sources = ["graph.json"]
    ui_index_fallback = False
    ui_index_merged = False
    scope_index_fallback = False
    scope_index_merged = False
    repo_python_merged = False
    repo_python_fallback = False
    repo_python_import_merged = False
    repo_python_import_parse_capped = False
    ui_file_entries = _ui_index_file_entries(sources.get("ui_index"))
    ui_edges = _ui_index_import_edges(sources.get("ui_index"))
    scope_file_entries = _scope_index_file_entries(sources.get("scope_index"))
    scope_edges = _scope_index_connection_edges(sources.get("scope_index"))
    repo_file_entries: list[dict[str, Any]] = []
    graph_has_python = any(
        str(row.get("path") or "").strip().endswith(REPO_PYTHON_EXTENSIONS)
        for row in file_entries
    )
    if scope_file_entries:
        repo_python_merged = False
        repo_python_import_merged = False
        scope_index_fallback = not file_entries or not graph_has_python
        scope_index_merged = not scope_index_fallback
        ui_index_fallback = bool(ui_file_entries) and (not file_entries or not graph_has_python)
        ui_index_merged = bool(ui_file_entries) and not ui_index_fallback
        file_entries = _merge_file_entries(file_entries, scope_file_entries, ui_file_entries)
        edges = _merge_connections(edges, scope_edges, ui_edges)
        edge_sources = _connection_edge_sources(edges, ["std_python_scope_index.json"])
    elif not file_entries or not graph_has_python:
        if ui_file_entries:
            ui_index_fallback = True
            repo_file_entries = _repo_python_file_entries(root)
            repo_paths = {
                str(row.get("path") or "").strip()
                for row in repo_file_entries
                if str(row.get("path") or "").strip()
            }
            repo_parse_paths = set(sorted(repo_paths, key=_repo_code_sort_key)[:REPO_PYTHON_IMPORT_PARSE_CAP])
            if target and target in repo_paths:
                repo_parse_paths.add(target)
            repo_python_import_parse_capped = len(repo_paths) > len(repo_parse_paths)
            repo_edges, _ = _repo_python_import_edges_and_symbols(
                root,
                repo_file_entries,
                parse_paths=repo_parse_paths,
            ) if repo_parse_paths else ([], {})
            repo_python_fallback = bool(repo_file_entries)
            file_entries = _merge_file_entries(repo_file_entries, ui_file_entries)
            edges = _merge_connections(repo_edges, ui_edges)
            edge_sources = _connection_edge_sources(edges, ["repo_python_imports", "ui_index.json"])
    elif ui_file_entries:
        ui_index_merged = True
        file_entries = _merge_file_entries(file_entries, ui_file_entries)
        edges = _merge_connections(edges, ui_edges)
        edge_sources = _connection_edge_sources(edges, ["graph.json", "ui_index.json"])
    edges_by_target = _index_edges_by_target(edges)
    file_impact = compute_reverse_bfs(edges_by_target, target, max_depth=max_depth)

    impacted_paths = set(file_impact["direct_dependents"]) | set(file_impact["transitive_dependents"])
    impacted_paths.add(target)

    if include_system_impact:
        paper_module_overlay = build_paper_module_overlay_index(root, paper_modules_index)
        annex_pattern_overlay = build_annex_pattern_overlay_index(annex_distillation)
        frontend_view_overlay = build_frontend_view_overlay_index(navigation_graph)
        system_impact = {
            "paper_modules": _system_impact_paper_modules(impacted_paths, paper_module_overlay),
            "frontend_views": _system_impact_frontend_views(impacted_paths, frontend_view_overlay),
            "standards": [],
            "skills": [],
            "annex_patterns": _system_impact_annex_patterns(impacted_paths, annex_pattern_overlay),
            "routes": [],
            "tests": [],
            "render_checks": [],
        }
    else:
        system_impact = _empty_system_impact()

    target_present = target in {str(row.get("path") or "").strip() for row in file_entries}
    if not target_present:
        confidence = "low"
        risk_reasons = ["target_not_in_hologram"]
        if ui_index_fallback:
            risk_reasons.append("target_not_in_projection")
    elif not file_impact["direct_dependents"]:
        confidence = "medium"
        risk_reasons = ["no_reverse_dependents_in_projection" if ui_index_fallback else "no_reverse_dependents_in_graph"]
    else:
        confidence = "medium"
        risk_reasons = []

    fingerprint = compute_source_fingerprint(
        root,
        [
            HOLOGRAM_GRAPH_PATH,
            HOLOGRAM_QUALITY_PATH,
            HOLOGRAM_UI_INDEX_PATH,
            PYTHON_SCOPE_INDEX_PATH,
            PAPER_MODULE_INDEX_PATH,
            ANNEX_DISTILLATION_INDEX_PATH,
            FRONTEND_NAVIGATION_GRAPH_PATH,
        ],
    )

    # Build the blast-radius omission receipt: 5 system_impact buckets are intentionally
    # empty placeholders in v1 (standards, skills, routes, tests, render_checks); plus any
    # missing overlay source contributes another omitted bucket with a named reason.
    omitted_overlays = 5  # standards, skills, routes, tests, render_checks always empty in v1
    overlay_reasons: list[str] = ["v1_system_impact_buckets_unwired:standards,skills,routes,tests,render_checks"]
    if include_system_impact:
        if paper_modules_index is None:
            omitted_overlays += 1
            overlay_reasons.append("paper_module_index_missing")
        if annex_distillation is None:
            omitted_overlays += 1
            overlay_reasons.append("annex_distillation_index_missing")
        if navigation_graph is None:
            omitted_overlays += 1
            overlay_reasons.append("frontend_navigation_graph_missing")
    else:
        omitted_overlays += 3
        overlay_reasons.append("include_system_impact_disabled")
    if ui_index_fallback:
        overlay_reasons.append("used_ui_index_fallback")
    if scope_index_fallback:
        overlay_reasons.append("primary_hologram_graph_missing_or_ui_only; used_std_python_scope_index_fallback")
    if scope_index_merged:
        overlay_reasons.append("merged_std_python_scope_index")
    if repo_python_fallback:
        overlay_reasons.append("primary_hologram_graph_and_scope_index_missing; used_repo_python_import_fallback")
    if repo_python_merged:
        overlay_reasons.append("merged_repo_python_files")
    if repo_python_import_merged:
        overlay_reasons.append("merged_repo_python_import_edges")
    if repo_python_import_parse_capped:
        overlay_reasons.append("repo_python_import_parse_cap_applied")
    if ui_index_merged:
        overlay_reasons.append("merged_ui_index")
    receipt_reason = "; ".join(overlay_reasons) if overlay_reasons else None

    suggested_verification = build_suggested_verification(
        target_path=target,
        file_impact=file_impact,
        system_impact=system_impact,
    )

    return {
        "kind": "kernel.blast_radius",
        "schema_version": BLAST_RADIUS_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "target_path": target,
        "source": {
            "graph": str(HOLOGRAM_GRAPH_PATH),
            "ui_index": str(HOLOGRAM_UI_INDEX_PATH),
            "scope_index": str(PYTHON_SCOPE_INDEX_PATH),
            "paper_modules": str(PAPER_MODULE_INDEX_PATH),
            "annex_distillation": str(ANNEX_DISTILLATION_INDEX_PATH),
            "frontend_navigation": str(FRONTEND_NAVIGATION_GRAPH_PATH),
            "source_fingerprint": fingerprint,
        },
        "file_impact": file_impact,
        "system_impact": system_impact,
        "risk": {
            "impact_score": _risk_score(file_impact),
            "confidence": confidence,
            "risk_reasons": risk_reasons,
        },
        "edge_sources": edge_sources,
        "suggested_verification": suggested_verification,
        "omission_receipt": build_omission_receipt(
            omitted_files=0,
            omitted_edges=0,
            omitted_overlays=omitted_overlays,
            reason=receipt_reason,
        ),
        "known_limits": list(KNOWN_LIMITS),
    }
