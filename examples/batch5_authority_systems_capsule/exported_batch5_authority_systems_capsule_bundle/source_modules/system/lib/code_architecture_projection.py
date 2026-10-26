"""
[PURPOSE]
- Teleology: Single producer of `code_map_packet_v1` and `blast_radius_packet_v1` for the Code Architecture Projection Plane defined in `codex/doctrine/paper_modules/codeflow_assimilation.md`. Kernel command, world-model endpoint, and Station lens all consume the same packets emitted here; no renderer invents a parallel schema or runs its own builder.
- Mechanism: Load the hologram (graph, quality, symbols) plus four optional overlay sources (paper-module index, route coverage, cross-annex distillation, frontend navigation graph), normalize edges with explicit `confidence` + `edge_sources`, attach governed edge semantics, compute reverse-BFS for blast radius, attach per-file overlays, fingerprint the sources for freshness, and emit deterministic JSON packets. Missing or stale overlays degrade gracefully via `omission_receipt`; nothing crashes if an upstream sidecar is absent.
- Non-goal: Build hologram artifacts (`kernel.py --build` owns that), mutate any source, or grant mutation permission downstream (every packet is `projection`/`judgment` evidence per the Workingness posture, never authority).

[INTERFACE]
- build_code_map_packet(*, root, focus_path=None, selection_path=None, projection_scope=None, max_files=300, include_overlays=True) -> dict
- build_code_map_edge_semantics_contract(connections=()) -> dict
- build_file_focus_search_packet(*, root, query, focus_path=None, max_files=300, max_results=50) -> dict
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
import time
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from system.lib import graph_scene_core
from system.lib.paper_modules import extract_code_loci_paths


CODE_MAP_SCHEMA_VERSION = "code_map_packet_v1"
BLAST_RADIUS_SCHEMA_VERSION = "blast_radius_packet_v1"
FILE_FOCUS_SEARCH_SCHEMA_VERSION = "file_focus_search_packet_v1"
FILE_FOCUS_SEARCH_RESULT_SCHEMA_VERSION = "file_focus_search_result_v1"
FILE_FOCUS_RESOLUTION_SCHEMA_VERSION = "file_focus_resolution_v1"
FILE_FOCUS_CANDIDATE_SCHEMA_VERSION = "file_focus_candidate_v1"
FILE_FOCUS_AGGREGATE_CONTEXT_SCHEMA_VERSION = "file_focus_aggregate_context_v1"
FILE_FOCUS_LOCATOR_GENERATION_SCHEMA_VERSION = "file_focus_locator_generation_v1"
CODE_MAP_ARCHITECTURE_LOCATION_SCHEMA_VERSION = "code_map_architecture_location_v1"
CODE_MAP_RENDER_CONTRACT_VERSION = "code_map_render_contract_v1"
CODE_MAP_PROJECTION_STATE_SCHEMA_VERSION = "code_map_projection_state_v1"
CODE_MAP_GRAPH_PRESENTATION_SCHEMA_VERSION = "code_map_graph_presentation_v1"
CODE_MAP_EDGE_SEMANTICS_SCHEMA_VERSION = "code_map_edge_semantics_v1"
CODE_MAP_FILE_SEMANTICS_SCHEMA_VERSION = "code_map_file_semantics_v1"
CODE_MAP_CLUSTER_SEMANTICS_SCHEMA_VERSION = "code_map_cluster_semantics_v1"
CODE_MAP_SEMANTIC_SCENE_SCHEMA_VERSION = "code_map_semantic_scene_v1"
CODE_MAP_BUILD_TIMINGS_SCHEMA_VERSION = "code_map_build_timings_v1"
CODE_MAP_CAMERA_TARGET_SCHEMA_VERSION = "code_map_camera_target_v1"
CODE_MAP_FOCUS_CONTEXT_SCHEMA_VERSION = "code_map_focus_context_v1"
CODE_MAP_SELECTION_CONTEXT_SCHEMA_VERSION = "code_map_selection_context_v1"
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

CODE_MAP_PRIMARY_TEXT_FORBIDDEN_FRAGMENTS = (
    "cluster around",
    "fan in",
    "fan out",
    "fan-in",
    "fan-out",
    "files in ",
    "files out ",
)

# Python documentation-tree quality flags carry mixed semantics. Provenance and
# metadata-completeness markers should stay visible without becoming health
# warnings that promote almost every CodeMap cluster into the warning lane.
ADVISORY_QUALITY_FLAGS = frozenset(
    {
        "composed_summary",
        "composed_when_needed",
        "derived_summary",
        "derived_when_needed",
        "missing_navigation_group",
    }
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

CODE_MAP_EDGE_SEMANTIC_ORDER = (
    "import",
    "internal_import",
    "call",
    "dependent",
    "blast_transitive",
    "escalates_to",
    "route",
    "test_neighbor",
    "verification",
    "related",
    "semantic",
    "same_group",
    "contains",
    "hidden_focus_overflow",
    "hidden_transitive_dependents",
    "unknown",
)

EDGE_SEMANTIC_CONTRACT: dict[str, dict[str, Any]] = {
    "import": {
        "semantic_kind": "import",
        "edge_class": "dependency",
        "meaning_role": "code_dependency",
        "layout_role": "rank_constraint",
        "presentation_role": "pathway",
        "legend_label": "Import",
        "short_label": "import",
        "description": "Source imports or references the target.",
        "rank": 10,
        "weight": 1.0,
        "default_color": "#34d399",
    },
    "internal_import": {
        "semantic_kind": "internal_import",
        "edge_class": "dependency",
        "meaning_role": "code_dependency",
        "layout_role": "rank_constraint",
        "presentation_role": "pathway",
        "legend_label": "Internal import",
        "short_label": "import",
        "description": "Internal repo import or module reference.",
        "rank": 11,
        "weight": 0.95,
        "default_color": "#2dd4bf",
    },
    "call": {
        "semantic_kind": "call",
        "edge_class": "dependency",
        "meaning_role": "runtime_dependency",
        "layout_role": "rank_constraint",
        "presentation_role": "pathway",
        "legend_label": "Call",
        "short_label": "call",
        "description": "Source calls into the target.",
        "rank": 12,
        "weight": 0.92,
        "default_color": "#86efac",
    },
    "dependent": {
        "semantic_kind": "dependent",
        "edge_class": "dependency",
        "meaning_role": "reverse_dependency",
        "layout_role": "rank_constraint",
        "presentation_role": "pathway",
        "legend_label": "Dependent",
        "short_label": "dependent",
        "description": "Source depends on the selected file.",
        "rank": 14,
        "weight": 0.86,
        "default_color": "#60a5fa",
    },
    "blast_transitive": {
        "semantic_kind": "blast_transitive",
        "edge_class": "impact",
        "meaning_role": "impact_cascade",
        "layout_role": "impact_constraint",
        "presentation_role": "impact",
        "legend_label": "Blast cascade",
        "short_label": "cascade",
        "description": "Transitive blast-radius impact beyond the direct edge.",
        "rank": 20,
        "weight": 0.74,
        "default_color": "#22d3ee",
        "dasharray": "5 6",
    },
    "escalates_to": {
        "semantic_kind": "escalates_to",
        "edge_class": "control",
        "meaning_role": "route_control",
        "layout_role": "rank_constraint",
        "presentation_role": "pathway",
        "legend_label": "Route control",
        "short_label": "route",
        "description": "Escalation or route-control edge.",
        "rank": 30,
        "weight": 0.7,
        "default_color": "#f59e0b",
        "dasharray": "7 5",
    },
    "route": {
        "semantic_kind": "escalates_to",
        "edge_class": "control",
        "meaning_role": "route_control",
        "layout_role": "rank_constraint",
        "presentation_role": "pathway",
        "legend_label": "Route control",
        "short_label": "route",
        "description": "Route-control edge.",
        "rank": 31,
        "weight": 0.68,
        "default_color": "#f59e0b",
        "dasharray": "7 5",
    },
    "test_neighbor": {
        "semantic_kind": "test_neighbor",
        "edge_class": "verification",
        "meaning_role": "proof_neighbor",
        "layout_role": "evidence_constraint",
        "presentation_role": "proof",
        "legend_label": "Verification",
        "short_label": "test",
        "description": "Test or proof neighbor.",
        "rank": 40,
        "weight": 0.62,
        "default_color": "#a3e635",
        "dasharray": "2 5",
    },
    "verification": {
        "semantic_kind": "test_neighbor",
        "edge_class": "verification",
        "meaning_role": "proof_neighbor",
        "layout_role": "evidence_constraint",
        "presentation_role": "proof",
        "legend_label": "Verification",
        "short_label": "test",
        "description": "Verification relation.",
        "rank": 41,
        "weight": 0.6,
        "default_color": "#a3e635",
        "dasharray": "2 5",
    },
    "related": {
        "semantic_kind": "related",
        "edge_class": "affinity",
        "meaning_role": "semantic_affinity",
        "layout_role": "non_constraint",
        "presentation_role": "fallback",
        "legend_label": "Related",
        "short_label": "related",
        "description": "Advisory semantic relation.",
        "rank": 60,
        "weight": 0.36,
        "default_color": "#94a3b8",
        "dasharray": "3 6",
    },
    "semantic": {
        "semantic_kind": "related",
        "edge_class": "affinity",
        "meaning_role": "semantic_affinity",
        "layout_role": "non_constraint",
        "presentation_role": "fallback",
        "legend_label": "Related",
        "short_label": "related",
        "description": "Advisory semantic relation.",
        "rank": 61,
        "weight": 0.34,
        "default_color": "#94a3b8",
        "dasharray": "3 6",
    },
    "same_group": {
        "semantic_kind": "same_group",
        "edge_class": "containment",
        "meaning_role": "membership",
        "layout_role": "non_constraint",
        "presentation_role": "membership",
        "legend_label": "Same area",
        "short_label": "same",
        "description": "Same folder or cluster; usually folded out of graph modes.",
        "rank": 70,
        "weight": 0.24,
        "default_color": "#64748b",
        "dasharray": "2 5",
    },
    "contains": {
        "semantic_kind": "same_group",
        "edge_class": "containment",
        "meaning_role": "membership",
        "layout_role": "non_constraint",
        "presentation_role": "membership",
        "legend_label": "Same area",
        "short_label": "same",
        "description": "Containment relation.",
        "rank": 71,
        "weight": 0.22,
        "default_color": "#64748b",
        "dasharray": "2 5",
    },
    "hidden_focus_overflow": {
        "semantic_kind": "hidden_focus_overflow",
        "edge_class": "dependency",
        "meaning_role": "density_control",
        "layout_role": "synthetic_non_constraint",
        "presentation_role": "fallback",
        "legend_label": "Hidden overflow",
        "short_label": "overflow",
        "description": "Collapsed direct focus-neighborhood overflow.",
        "rank": 80,
        "weight": 0.2,
        "default_color": "#fbbf24",
        "dasharray": "4 7",
    },
    "hidden_transitive_dependents": {
        "semantic_kind": "hidden_transitive_dependents",
        "edge_class": "impact",
        "meaning_role": "density_control",
        "layout_role": "synthetic_non_constraint",
        "presentation_role": "impact",
        "legend_label": "Hidden cascade",
        "short_label": "cascade",
        "description": "Collapsed transitive blast-radius overflow.",
        "rank": 81,
        "weight": 0.2,
        "default_color": "#22d3ee",
        "dasharray": "4 7",
    },
    "unknown": {
        "semantic_kind": "unknown",
        "edge_class": "unknown",
        "meaning_role": "unknown",
        "layout_role": "non_constraint",
        "presentation_role": "fallback",
        "legend_label": "Unknown",
        "short_label": "unknown",
        "description": "Unclassified packet edge; visible but non-constraining until the producer contract is extended.",
        "rank": 99,
        "weight": 0.1,
        "default_color": "#64748b",
        "dasharray": "4 6",
    },
}

EDGE_LAYOUT_PARTICIPATION_BY_LAYOUT_ROLE: dict[str, dict[str, str]] = {
    "rank_constraint": {
        "architecture": "constraint_when_high_confidence",
        "focus": "constraint",
        "blast": "constraint",
        "evidence": "rendered_evidence",
        "panorama": "aggregated_corridor",
    },
    "impact_constraint": {
        "architecture": "hidden",
        "focus": "constraint",
        "blast": "constraint",
        "evidence": "rendered_evidence",
        "panorama": "aggregated_corridor",
    },
    "evidence_constraint": {
        "architecture": "hidden",
        "focus": "incident_only",
        "blast": "context",
        "evidence": "rendered_evidence",
        "panorama": "hidden",
    },
    "non_constraint": {
        "architecture": "hidden",
        "focus": "incident_only",
        "blast": "hidden",
        "evidence": "rendered_evidence",
        "panorama": "hidden",
    },
    "synthetic_non_constraint": {
        "architecture": "hidden",
        "focus": "drawn_only",
        "blast": "drawn_only",
        "evidence": "hidden",
        "panorama": "hidden",
    },
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
FILE_FOCUS_SOURCE_PATHS = (
    HOLOGRAM_GRAPH_PATH,
    HOLOGRAM_QUALITY_PATH,
    HOLOGRAM_SYMBOLS_PATH,
    HOLOGRAM_UI_INDEX_PATH,
    PYTHON_SCOPE_INDEX_PATH,
    PAPER_MODULE_INDEX_PATH,
    PAPER_MODULE_ROUTE_COVERAGE_PATH,
    ANNEX_DISTILLATION_INDEX_PATH,
    FRONTEND_NAVIGATION_GRAPH_PATH,
)
CODE_MAP_SOURCE_PATHS = FILE_FOCUS_SOURCE_PATHS
PAPER_MODULE_DIR = Path("codex/doctrine/paper_modules")
UI_INDEX_IMPORT_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json")
REPO_PYTHON_EXTENSIONS = (".py",)
PLECTIS_CODE_MAP_PYTHON_PREFIXES = (
    "microcosm-substrate/src/",
    "microcosm-substrate/tests/",
    "microcosm-substrate/scripts/",
)
PLECTIS_CODE_MAP_IMPORT_PARSE_CAP = 600
REPO_CODE_EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".claude",
        ".codex",
        ".microcosm",
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
        "docs",
        "examples",
        "external",
        "fixtures",
        "node_modules",
        "obsidian",
        "output",
        "receipts",
        "sandbox",
        "screenshots",
        "site-packages",
        "state",
        "tmp",
        "venv",
    }
)
REPO_PYTHON_IMPORT_PARSE_CAP = 240
JSON_HEADER_TOKEN_BYTES = 256 * 1024
FILE_FOCUS_LOCATOR_JSON_MAX_BYTES = 2 * 1024 * 1024
FILE_FOCUS_LOCATOR_REFRESH_TTL_S = 30.0
JSON_HEADER_TOKEN_RE = re.compile(r'"(?P<key>source_fingerprint|generated_at)"\s*:\s*"(?P<value>[^"]+)"')
SOURCE_CACHE_MAX_ENTRIES = 16
DERIVED_CACHE_MAX_ENTRIES = 16

_SOURCE_JSON_CACHE_LOCK = threading.Lock()
_SOURCE_JSON_CACHE: dict[str, tuple[tuple[int, int], Any]] = {}
_DERIVED_CACHE_LOCK = threading.Lock()
_GRAPH_EDGE_CACHE: dict[Any, list[dict[str, Any]]] = {}
_UI_INDEX_FILE_ENTRIES_CACHE: dict[Any, list[dict[str, Any]]] = {}
_UI_INDEX_SYMBOL_COUNTS_CACHE: dict[Any, dict[str, int]] = {}
_UI_INDEX_IMPORT_EDGES_CACHE: dict[Any, list[dict[str, Any]]] = {}
_SCOPE_INDEX_FILE_ENTRIES_CACHE: dict[Any, list[dict[str, Any]]] = {}
_SCOPE_INDEX_FILE_SEMANTICS_CACHE: dict[Any, dict[str, dict[str, Any]]] = {}
_SCOPE_INDEX_SYMBOL_COUNTS_CACHE: dict[Any, dict[str, int]] = {}
_SCOPE_INDEX_CONNECTION_EDGES_CACHE: dict[Any, list[dict[str, Any]]] = {}
_FILE_FOCUS_LOCATOR_CACHE: dict[Any, dict[str, Any]] = {}
_FILE_FOCUS_LOCATOR_INFLIGHT: dict[Any, threading.Event] = {}
_FILE_FOCUS_CATALOGUE_CACHE: dict[Any, dict[str, Any]] = {}
_FILE_FOCUS_CATALOGUE_INFLIGHT: dict[Any, threading.Event] = {}


def _bounded_cache_set(cache: dict[Any, Any], key: Any, value: Any, *, max_entries: int) -> None:
    """[ACTION] Store one process-local cache entry and evict oldest extras."""
    cache[key] = value
    while len(cache) > max_entries:
        cache.pop(next(iter(cache)))


def _derived_cache_row_marker(row: Any) -> Any:
    """[ACTION] Return a compact identity marker for one generated payload row."""
    if not isinstance(row, Mapping):
        return str(row)[:120]
    return tuple(
        (field, str(row.get(field) or "")[:120])
        for field in ("path", "source", "target", "from", "to", "kind", "symbol_id", "name")
        if row.get(field) not in (None, "")
    )


def _derived_payload_cache_key(payload: Mapping[str, Any]) -> tuple[Any, ...]:
    """
    [ACTION] Build a process-cache key that survives Python object-id reuse after source-cache eviction.

    The id remains in the key for the hot path, while generated timestamps/counts
    and first/last row markers prevent stale derived rows when a different JSON
    payload later receives the same object id.
    """
    meta = payload.get("__meta")
    meta = meta if isinstance(meta, Mapping) else {}
    list_markers: list[tuple[str, int, Any, Any]] = []
    for field in ("files", "file_edges", "symbol_edges", "symbols", "scopes"):
        rows = payload.get(field)
        if not isinstance(rows, list):
            continue
        first = _derived_cache_row_marker(rows[0]) if rows else None
        last = _derived_cache_row_marker(rows[-1]) if rows else None
        list_markers.append((field, len(rows), first, last))
    return (
        id(payload),
        str(meta.get("generated_at") or payload.get("generated_at") or ""),
        str(meta.get("source_fingerprint") or payload.get("source_fingerprint") or ""),
        str(meta.get("schema_version") or payload.get("schema_version") or ""),
        str(meta.get("artifact_path") or ""),
        tuple(list_markers),
    )


def _now_iso() -> str:
    """[ACTION] Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _dedupe_strings(values: Iterable[Any]) -> list[str]:
    """[ACTION] Return stable non-empty strings with duplicates removed."""
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _health_from_quality(quality: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION] Convert documentation-tree quality rows into CodeMap health.

    `quality_flags` includes provenance markers such as `composed_summary` and
    `derived_when_needed`; those are useful evidence but not actionable health
    warnings. Keep them under advisory fields so renderers can inspect them
    without treating every file as flagged.
    """
    raw_status = str(quality.get("status") or "").strip()
    quality_flags = _dedupe_strings(quality.get("quality_flags") or [])
    derivation_warnings = _dedupe_strings(quality.get("derivation_warnings") or [])
    advisory_flags = [flag for flag in quality_flags if flag in ADVISORY_QUALITY_FLAGS]
    actionable_flags = [flag for flag in quality_flags if flag not in ADVISORY_QUALITY_FLAGS]
    warnings = _dedupe_strings([*actionable_flags, *derivation_warnings])
    grade = raw_status or None
    if raw_status == "degraded" and advisory_flags and not warnings:
        grade = "advisory"
    return {
        "grade": grade,
        "source_status": raw_status or None,
        "warnings": warnings,
        "quality_flags": quality_flags,
        "advisory_flags": advisory_flags,
        "derivation_warnings": derivation_warnings,
    }


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


def _read_locator_json(root: Path, rel: Path) -> Any | None:
    """[ACTION] Read small locator sidecars only; large sources stay in the full-catalogue fallback."""
    path = root / rel
    try:
        if path.stat().st_size > FILE_FOCUS_LOCATOR_JSON_MAX_BYTES:
            return None
    except (FileNotFoundError, OSError):
        return None
    return _read_json(path)


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
    cache_key = _derived_payload_cache_key(ui_index)
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
    cache_key = _derived_payload_cache_key(scope_index)
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


def _compact_semantic_sentence(value: Any, *, max_chars: int = 190) -> str | None:
    """[ACTION] Normalize generated purpose prose into a compact display sentence."""
    text = " ".join(str(value or "").strip().split())
    if not text:
        return None
    text = text.replace("(Teleology) ", "")
    if len(text) <= max_chars:
        return text
    cutoff = text.rfind(" ", 0, max_chars - 3)
    if cutoff < max_chars // 2:
        cutoff = max_chars - 3
    return text[:cutoff].rstrip(" ,;:") + "..."


def _scope_index_file_semantics(scope_index: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    """[ACTION] Extract file-purpose rows from std_python_scope_index for CodeMap cards/drawers."""
    if not isinstance(scope_index, Mapping):
        return {}
    cache_key = _derived_payload_cache_key(scope_index)
    with _DERIVED_CACHE_LOCK:
        cached = _SCOPE_INDEX_FILE_SEMANTICS_CACHE.get(cache_key)
        if cached is not None:
            return {path: dict(row) for path, row in cached.items()}

    semantics_by_path: dict[str, dict[str, Any]] = {}
    files = scope_index.get("files")
    if isinstance(files, list):
        for raw in files:
            if not isinstance(raw, Mapping):
                continue
            path = str(raw.get("path") or "").strip()
            if not path:
                continue
            purpose = None
            purpose_source = None
            for field in ("when_needed", "browse_summary", "summary"):
                purpose = _compact_semantic_sentence(raw.get(field))
                if purpose:
                    purpose_source = f"std_python_scope_index.{field}"
                    break
            semantics_by_path[path] = {
                "purpose": purpose,
                "purpose_source": purpose_source,
                "navigation_group": str(raw.get("navigation_group") or "").strip() or None,
                "group_label": str(raw.get("group_label") or "").strip() or None,
                "symbol_samples": [],
            }

    scopes = scope_index.get("scopes")
    if isinstance(scopes, list):
        for raw in scopes:
            if not isinstance(raw, Mapping):
                continue
            path = str(raw.get("path") or "").strip()
            if not path:
                continue
            row = semantics_by_path.setdefault(
                path,
                {
                    "purpose": None,
                    "purpose_source": None,
                    "navigation_group": None,
                    "group_label": None,
                    "symbol_samples": [],
                },
            )
            samples = row.setdefault("symbol_samples", [])
            if not isinstance(samples, list) or len(samples) >= 5:
                continue
            name = str(raw.get("name") or _symbol_name_from_id(str(raw.get("symbol_id") or ""))).strip()
            if not name or any(isinstance(sample, Mapping) and sample.get("name") == name for sample in samples):
                continue
            samples.append(
                {
                    "name": name,
                    "kind": str(raw.get("kind") or raw.get("scope_kind") or raw.get("type") or "symbol").strip(),
                    "summary": _compact_semantic_sentence(raw.get("summary"), max_chars=120),
                }
            )

    with _DERIVED_CACHE_LOCK:
        _bounded_cache_set(
            _SCOPE_INDEX_FILE_SEMANTICS_CACHE,
            cache_key,
            semantics_by_path,
            max_entries=DERIVED_CACHE_MAX_ENTRIES,
        )
    return {path: dict(row) for path, row in semantics_by_path.items()}


def _scope_index_symbol_counts(scope_index: Mapping[str, Any] | None) -> dict[str, int]:
    """[ACTION] Count generated Python scope rows by file path."""
    out: dict[str, int] = {}
    if not isinstance(scope_index, Mapping):
        return out
    cache_key = _derived_payload_cache_key(scope_index)
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
    cache_key = _derived_payload_cache_key(scope_index)
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
            if len(parts) == 3 and parts[2].endswith(REPO_PYTHON_EXTENSIONS):
                return "kernel_lib"
            if parts[2] == "kernel" and len(parts) >= 4:
                return f"system/lib/kernel/{parts[3]}"
            return f"system/lib/{parts[2]}"
        if len(parts) >= 3 and parts[1] == "server":
            if parts[2] == "tests":
                return "system/server/tests"
            if parts[2] == "ui":
                return _ui_index_layer_for_path(path, "system/server/ui")
            if len(parts) == 3 and parts[2].endswith(REPO_PYTHON_EXTENSIONS):
                return "server_backend"
            return f"system/server/{parts[2]}"
        return "/".join(parts[: min(3, len(parts))])
    if parts[0] == "tools":
        return "/".join(parts[: min(3, len(parts))])
    if parts[0] == "codex":
        return "/".join(parts[: min(3, len(parts))])
    if parts[0] == "tests":
        return "tests"
    if parts[0] == "microcosm-substrate":
        if len(parts) >= 4 and parts[1] == "src" and parts[2] == "microcosm_core":
            if parts[3] == "organs":
                return "plectis/organs"
            return f"plectis/{parts[3]}"
        if len(parts) >= 2 and parts[1] == "tests":
            return "plectis/tests"
        if len(parts) >= 2 and parts[1] == "scripts":
            return "plectis/scripts"
        return "plectis"
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


def _iter_repo_python_rel_paths(root: Path) -> Iterable[Path]:
    """[ACTION] Yield repo-relative Python paths admitted to the live search catalogue."""
    stack: list[tuple[str, Path]] = [("", root)]
    while stack:
        rel_dir, abs_dir = stack.pop()
        try:
            entries = list(os.scandir(abs_dir))
        except OSError:
            continue
        entries.sort(key=lambda entry: entry.name)
        for entry in entries:
            name = entry.name
            if name in REPO_CODE_EXCLUDED_DIRS:
                continue
            rel = f"{rel_dir}/{name}" if rel_dir else name
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append((rel, Path(entry.path)))
                elif entry.is_file(follow_symlinks=False) and name.endswith(REPO_PYTHON_EXTENSIONS):
                    yield Path(rel)
            except OSError:
                continue


def _scan_repo_python_files(root: Path) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    """[ACTION] Scan live Python membership once for locator refresh and return entries plus a manifest token."""
    h = hashlib.sha256()
    count = 0
    dir_scan_count = 0
    stat_count = 0
    by_path: dict[str, dict[str, Any]] = {}
    stack: list[tuple[str, Path]] = [("", root)]
    started_at = time.perf_counter()
    while stack:
        rel_dir, abs_dir = stack.pop()
        dir_scan_count += 1
        try:
            entries = list(os.scandir(abs_dir))
        except OSError:
            continue
        entries.sort(key=lambda entry: entry.name)
        for entry in entries:
            name = entry.name
            if name in REPO_CODE_EXCLUDED_DIRS:
                continue
            rel = f"{rel_dir}/{name}" if rel_dir else name
            rel_path = Path(rel)
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append((rel, Path(entry.path)))
                    continue
                if not entry.is_file(follow_symlinks=False) or not name.endswith(REPO_PYTHON_EXTENSIONS):
                    continue
            except OSError:
                continue
            try:
                stat = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            rel_posix = rel_path.as_posix()
            h.update(rel_posix.encode("utf-8"))
            h.update(b"\0")
            h.update(f"{int(stat.st_mtime_ns)}:{int(stat.st_size)}".encode("utf-8"))
            h.update(b"\n")
            count += 1
            stat_count += 1
            by_path[rel_posix] = {
                "path": rel_posix,
                "group_id": _repo_code_layer_for_path(rel_posix),
                "summary": None,
            }
    elapsed_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
    return (
        sorted(by_path.values(), key=lambda row: _repo_code_sort_key(str(row.get("path") or ""))),
        f"repo_python:{count}:{h.hexdigest()[:16]}",
        {
            "schema": "repo_python_scan_metrics_v1",
            "repo_walk_count": 1,
            "directory_scan_count": dir_scan_count,
            "file_stat_count": stat_count,
            "python_file_count": count,
            "elapsed_ms": elapsed_ms,
        },
    )


def _scan_repo_python_prefix_files(
    root: Path,
    prefixes: Iterable[str],
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    """[ACTION] Scan bounded repo Python prefixes admitted to CodeMap even when generated indexes exist."""
    h = hashlib.sha256()
    count = 0
    dir_scan_count = 0
    stat_count = 0
    by_path: dict[str, dict[str, Any]] = {}
    started_at = time.perf_counter()
    stack: list[tuple[str, Path]] = []
    for raw_prefix in prefixes:
        prefix = str(raw_prefix or "").strip().strip("/")
        if not prefix:
            continue
        abs_dir = root / prefix
        if abs_dir.is_dir():
            stack.append((prefix, abs_dir))
    while stack:
        rel_dir, abs_dir = stack.pop()
        dir_scan_count += 1
        try:
            entries = list(os.scandir(abs_dir))
        except OSError:
            continue
        entries.sort(key=lambda entry: entry.name)
        for entry in entries:
            name = entry.name
            if name in REPO_CODE_EXCLUDED_DIRS:
                continue
            rel = f"{rel_dir}/{name}" if rel_dir else name
            rel_path = Path(rel)
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append((rel, Path(entry.path)))
                    continue
                if not entry.is_file(follow_symlinks=False) or not name.endswith(REPO_PYTHON_EXTENSIONS):
                    continue
            except OSError:
                continue
            try:
                stat = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            rel_posix = rel_path.as_posix()
            h.update(rel_posix.encode("utf-8"))
            h.update(b"\0")
            h.update(f"{int(stat.st_mtime_ns)}:{int(stat.st_size)}".encode("utf-8"))
            h.update(b"\n")
            count += 1
            stat_count += 1
            by_path[rel_posix] = {
                "path": rel_posix,
                "group_id": _repo_code_layer_for_path(rel_posix),
                "summary": None,
            }
    elapsed_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
    return (
        sorted(by_path.values(), key=lambda row: _repo_code_sort_key(str(row.get("path") or ""))),
        f"repo_python_prefix:{count}:{h.hexdigest()[:16]}",
        {
            "schema": "repo_python_prefix_scan_metrics_v1",
            "prefixes": [str(prefix).strip() for prefix in prefixes if str(prefix).strip()],
            "repo_walk_count": 1,
            "directory_scan_count": dir_scan_count,
            "file_stat_count": stat_count,
            "python_file_count": count,
            "elapsed_ms": elapsed_ms,
        },
    )


def _repo_python_manifest_token(root: Path) -> str:
    """[ACTION] Fingerprint live Python catalogue membership for explicit refresh checks."""
    _entries, token, _metrics = _scan_repo_python_files(root)
    return token


def compute_code_map_live_source_manifest_token(root: Path) -> str:
    """[ACTION] Return a cheap stat token for bounded live Python prefixes consumed by CodeMap."""
    _entries, token, _metrics = _scan_repo_python_prefix_files(root, PLECTIS_CODE_MAP_PYTHON_PREFIXES)
    return token


def _repo_python_code_map_live_file_entries(root: Path) -> list[dict[str, Any]]:
    """[ACTION] Return bounded live Python rows that CodeMap admits beside generated indexes."""
    entries, _token, _metrics = _scan_repo_python_prefix_files(root, PLECTIS_CODE_MAP_PYTHON_PREFIXES)
    return entries


def _live_source_content_token(root: Path, entries: Iterable[Mapping[str, Any]]) -> str:
    """[ACTION] Content fingerprint bounded live Python rows included in the CodeMap packet."""
    h = hashlib.sha256()
    count = 0
    for raw in sorted(entries, key=lambda row: str(row.get("path") or "")):
        path = str(raw.get("path") or "").strip()
        if not path:
            continue
        h.update(path.encode("utf-8"))
        h.update(b"\0")
        h.update(_source_token_for_path(root, Path(path)).encode("utf-8"))
        h.update(b"\n")
        count += 1
    return f"repo_python_live_content:{count}:{h.hexdigest()[:16]}"


def _combine_code_map_source_fingerprint(
    root: Path,
    source_rel_paths: Iterable[Path],
    live_entries: Iterable[Mapping[str, Any]],
) -> str:
    sidecar_fingerprint = compute_source_fingerprint(root, source_rel_paths)
    live_token = _live_source_content_token(root, live_entries)
    h = hashlib.sha256()
    h.update(sidecar_fingerprint.encode("utf-8"))
    h.update(b"\n")
    h.update(live_token.encode("utf-8"))
    return h.hexdigest()[:16]


def _file_focus_source_fingerprint_from_manifest(root: Path, repo_manifest_token: str) -> tuple[str, str]:
    """[ACTION] Combine generated-sidecar freshness with an already-acquired repo manifest token."""
    sidecar_fingerprint = compute_source_fingerprint(root, FILE_FOCUS_SOURCE_PATHS)
    h = hashlib.sha256()
    h.update(sidecar_fingerprint.encode("utf-8"))
    h.update(b"\n")
    h.update(str(repo_manifest_token or "").encode("utf-8"))
    return h.hexdigest()[:16], sidecar_fingerprint


def compute_file_focus_source_fingerprint(root: Path) -> str:
    """[ACTION] Fingerprint every source that can change file-focus catalogue output."""
    repo_manifest_token = _repo_python_manifest_token(root)
    fingerprint, _sidecar_fingerprint = _file_focus_source_fingerprint_from_manifest(root, repo_manifest_token)
    return fingerprint


def _repo_python_file_entries(root: Path) -> list[dict[str, Any]]:
    """[ACTION] Scan repo Python files into graph-like file entries when the hologram is stale or UI-only."""
    entries, _token, _metrics = _scan_repo_python_files(root)
    return entries


def _module_name_for_python_path(path: str) -> str | None:
    """[ACTION] Convert a repo-relative .py path into its importable dotted module name."""
    if not path.endswith(".py"):
        return None
    stem = path[:-3]
    parts = [part for part in stem.split("/") if part]
    if not parts:
        return None
    if len(parts) >= 3 and parts[0] == "microcosm-substrate" and parts[1] == "src":
        parts = parts[2:]
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
    rows = list(file_rows)
    paths = [str(row.get("path") or "").strip() for row in rows]
    python_file_count = sum(1 for path in paths if path.endswith(REPO_PYTHON_EXTENSIONS))
    frontend_file_count = sum(1 for path in paths if _path_is_frontend(path))
    warning_counts: list[int] = []
    advisory_counts: list[int] = []
    for row in rows:
        health = row.get("health") if isinstance(row.get("health"), Mapping) else {}
        warnings = health.get("warnings") if isinstance(health, Mapping) else []
        advisory_flags = health.get("advisory_flags") if isinstance(health, Mapping) else []
        warning_counts.append(len(warnings) if isinstance(warnings, list) else 0)
        advisory_counts.append(len(advisory_flags) if isinstance(advisory_flags, list) else 0)
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
        "health_warning_file_count": sum(1 for count in warning_counts if count > 0),
        "health_warning_count": sum(warning_counts),
        "health_advisory_file_count": sum(1 for count in advisory_counts if count > 0),
        "health_advisory_flag_count": sum(advisory_counts),
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
        labels.append(f"imported_by:{fan_in}")
    if fan_out:
        labels.append(f"calls_imports:{fan_out}")
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
        semantics = row.get("semantics") if isinstance(row.get("semantics"), Mapping) else {}
        row["presentation"] = {
            "schema": "code_map_file_presentation_v1",
            "node_role": role,
            "salience": _salience_band(score),
            "salience_score": round(score, 3),
            "density_band": _density_band(score, is_focus=is_focus),
            "primary_label": _path_leaf(path) or path,
            "secondary_label": row.get("layer") or _path_parent(path),
            "purpose": semantics.get("purpose"),
            "purpose_source": semantics.get("purpose_source"),
            "metadata_labels": _file_metadata_labels(row, node_role=role),
            "selectable_target_type": "file",
            "url_identity": f"file:{path}" if path else None,
            "focus_role": "selected" if is_focus else "normal",
        }


def _edge_contract_row(kind: Any) -> dict[str, Any]:
    token = str(kind or "unknown").strip() or "unknown"
    return EDGE_SEMANTIC_CONTRACT.get(token, EDGE_SEMANTIC_CONTRACT["unknown"])


def _edge_layout_participation(layout_role: Any) -> dict[str, str]:
    role = str(layout_role or "non_constraint").strip() or "non_constraint"
    return dict(
        EDGE_LAYOUT_PARTICIPATION_BY_LAYOUT_ROLE.get(
            role,
            EDGE_LAYOUT_PARTICIPATION_BY_LAYOUT_ROLE["non_constraint"],
        )
    )


def _edge_semantics_payload(kind: Any) -> dict[str, Any]:
    """[ACTION] Return the backend-owned meaning/layout/presentation contract for one edge kind."""
    token = str(kind or "unknown").strip() or "unknown"
    contract = _edge_contract_row(token)
    layout_role = str(contract.get("layout_role") or "non_constraint")
    return {
        "schema": CODE_MAP_EDGE_SEMANTICS_SCHEMA_VERSION,
        "source_kind": token,
        "semantic_kind": contract["semantic_kind"],
        "edge_class": contract["edge_class"],
        "meaning_role": contract["meaning_role"],
        "layout_role": layout_role,
        "layout_participation": _edge_layout_participation(layout_role),
        "presentation_role": contract["presentation_role"],
        "legend_label": contract["legend_label"],
        "short_label": contract["short_label"],
        "description": contract["description"],
        "rank": int(contract["rank"]),
        "weight": float(contract["weight"]),
        "default_color": contract["default_color"],
        "dasharray": contract.get("dasharray"),
    }


def _edge_semantic_style_payload(semantics: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "code_map_edge_semantic_style_v1",
        "semantic_kind": semantics.get("semantic_kind") or "unknown",
        "edge_class": semantics.get("edge_class") or "unknown",
        "meaning_role": semantics.get("meaning_role") or "unknown",
        "layout_role": semantics.get("layout_role") or "non_constraint",
        "presentation_role": semantics.get("presentation_role") or "fallback",
        "short_label": semantics.get("short_label") or semantics.get("semantic_kind") or "unknown",
        "legend_label": semantics.get("legend_label") or semantics.get("short_label") or "Unknown",
        "color": semantics.get("default_color") or EDGE_SEMANTIC_CONTRACT["unknown"]["default_color"],
        "dasharray": semantics.get("dasharray"),
        "source": "code_map.edge_semantics.legend_rows",
    }


def _edge_role(kind: Any) -> str:
    token = str(kind or "unknown").strip()
    edge_class = _edge_contract_row(token).get("edge_class")
    if edge_class == "dependency":
        return "dependency_context"
    if edge_class == "impact":
        return "impact_context"
    if edge_class == "containment":
        return "membership"
    if edge_class == "verification":
        return "verification"
    if edge_class == "control":
        return "control_flow"
    if edge_class == "affinity":
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
    if role in {"dependency_context", "impact_context", "control_flow"} and edge.get("confidence") in {"high", "medium"}:
        return "overview"
    if role in {"verification", "affinity"}:
        return "focus"
    return "detail"


def _attach_connection_presentation(connections: list[dict[str, Any]]) -> None:
    """[ACTION] Mutate connection rows with renderer-neutral presentation hints."""
    for edge in connections:
        role = _edge_role(edge.get("kind"))
        semantics = _edge_semantics_payload(edge.get("kind"))
        edge["semantics"] = semantics
        edge["presentation"] = {
            "schema": "code_map_edge_presentation_v1",
            "edge_role": role,
            "semantic_kind": semantics["semantic_kind"],
            "edge_class": semantics["edge_class"],
            "presentation_role": semantics["presentation_role"],
            "edge_strength": _edge_strength(edge.get("confidence")),
            "density_band": _edge_density_band(edge),
            "short_label": semantics["short_label"],
            "semantic_label": semantics["short_label"],
            "legend_label": semantics["legend_label"],
            "meaning_label": semantics["legend_label"],
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
        "edge_semantic_counts": _count_nested(connections, ("semantics", "semantic_kind")),
        "edge_class_counts": _count_nested(connections, ("semantics", "edge_class")),
        "edge_layout_role_counts": _count_nested(connections, ("semantics", "layout_role")),
        "grammar": {
            "node_role_field": "files[].presentation.node_role",
            "edge_role_field": "connections[].presentation.edge_role",
            "edge_semantic_field": "connections[].semantics.semantic_kind",
            "edge_layout_field": "connections[].semantics.layout_role",
            "density_field": "presentation.density_band",
            "labels": [
                "files[].presentation.primary_label",
                "files[].presentation.secondary_label",
                "files[].presentation.metadata_labels",
                "connections[].semantics.short_label",
                "connections[].semantics.legend_label",
            ],
        },
    }


def _edge_semantics_legend_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for kind in CODE_MAP_EDGE_SEMANTIC_ORDER:
        payload = _edge_semantics_payload(kind)
        semantic_kind = str(payload.get("semantic_kind") or "unknown")
        if semantic_kind in seen:
            continue
        seen.add(semantic_kind)
        rows.append(
            {
                "semantic_kind": semantic_kind,
                "source_kinds": [
                    source_kind
                    for source_kind in CODE_MAP_EDGE_SEMANTIC_ORDER
                    if str(_edge_semantics_payload(source_kind).get("semantic_kind")) == semantic_kind
                ],
                "edge_class": payload["edge_class"],
                "meaning_role": payload["meaning_role"],
                "layout_role": payload["layout_role"],
                "layout_participation": payload["layout_participation"],
                "presentation_role": payload["presentation_role"],
                "legend_label": payload["legend_label"],
                "short_label": payload["short_label"],
                "description": payload["description"],
                "rank": payload["rank"],
                "weight": payload["weight"],
                "default_color": payload["default_color"],
                "dasharray": payload.get("dasharray"),
            }
        )
    return rows


def _build_edge_semantics_summary(connections: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    semantic_counts: dict[str, int] = {}
    class_counts: dict[str, int] = {}
    layout_role_counts: dict[str, int] = {}
    unknown_source_kinds: set[str] = set()
    for edge in connections:
        semantics = edge.get("semantics") if isinstance(edge.get("semantics"), Mapping) else _edge_semantics_payload(edge.get("kind"))
        semantic_kind = str(semantics.get("semantic_kind") or "unknown")
        edge_class = str(semantics.get("edge_class") or "unknown")
        layout_role = str(semantics.get("layout_role") or "non_constraint")
        source_kind = str(edge.get("kind") or "unknown")
        semantic_counts[semantic_kind] = semantic_counts.get(semantic_kind, 0) + 1
        class_counts[edge_class] = class_counts.get(edge_class, 0) + 1
        layout_role_counts[layout_role] = layout_role_counts.get(layout_role, 0) + 1
        if semantic_kind == "unknown" and source_kind != "unknown":
            unknown_source_kinds.add(source_kind)
    return {
        "schema": CODE_MAP_EDGE_SEMANTICS_SCHEMA_VERSION,
        "known_source_kinds": list(CODE_MAP_EDGE_SEMANTIC_ORDER),
        "field_contract": {
            "meaning_plane": "connections[].semantics.semantic_kind + meaning_role",
            "constraint_plane": "connections[].semantics.layout_role + layout_participation",
            "presentation_plane": "connections[].semantics.presentation_role + short_label + legend_label",
            "frontend_fallback": "render unknown source kinds through semantic_kind=unknown until this contract is extended",
        },
        "unknown_policy": {
            "semantic_kind": "unknown",
            "edge_class": "unknown",
            "layout_role": "non_constraint",
            "visible": True,
            "layout_participation": _edge_layout_participation("non_constraint"),
        },
        "legend_rows": _edge_semantics_legend_rows(),
        "sample_counts": {
            "semantic_kind": dict(sorted(semantic_counts.items())),
            "edge_class": dict(sorted(class_counts.items())),
            "layout_role": dict(sorted(layout_role_counts.items())),
        },
        "unknown_source_kinds": sorted(unknown_source_kinds),
        "omission_receipt": {
            "omitted_legend_rows": 0,
            "reason": None,
        },
    }


def build_code_map_edge_semantics_contract(connections: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """[ACTION] Public helper for empty/warming packet shells that must preserve the edge contract."""
    return _build_edge_semantics_summary(connections)


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
    cluster_semantics: Mapping[str, Any],
    camera_target: Mapping[str, Any],
) -> dict[str, Any]:
    """[ACTION] Project returned code_map rows into compact graph_scene_core fields."""
    nodes: list[dict[str, Any]] = []
    inspectors: dict[str, dict[str, Any]] = {}
    lane_ids: set[str] = set()
    domain_counts: dict[str, int] = {}
    paths_by_id: dict[str, str] = {}
    cluster_id_by_path: dict[str, str] = {}
    zone_key_by_cluster: dict[str, str] = {}
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
        architecture_cluster_id = _row_cluster_id(row)
        architecture_zone_key = _row_zone_key(row)
        cluster_id_by_path[path] = architecture_cluster_id
        zone_key_by_cluster.setdefault(architecture_cluster_id, architecture_zone_key)
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
                    "row_id": f"cluster:{architecture_cluster_id}",
                    "stable_order": index,
                    "parent_cluster_id": f"cluster:{architecture_cluster_id}",
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

    clusters_contract = cluster_semantics.get("clusters") if isinstance(cluster_semantics.get("clusters"), Mapping) else {}
    zones_contract = cluster_semantics.get("zones") if isinstance(cluster_semantics.get("zones"), Mapping) else {}
    for zone_index, (zone_key, zone_row_raw) in enumerate(sorted(zones_contract.items())):
        zone_row = zone_row_raw if isinstance(zone_row_raw, Mapping) else {}
        zone_node_id = f"zone:{zone_key}"
        lane_ids.add("architecture_zone")
        nodes.append(
            {
                "id": zone_node_id,
                "kind": "architecture_zone",
                "label": str(zone_row.get("label") or _architecture_zone_label(str(zone_key))),
                "summary": zone_row.get("purpose_sentence") or zone_row.get("purpose"),
                "lane": "architecture_zone",
                "domain": "architecture",
                "row_id": "architecture_zones",
                "rank": zone_index,
                "state": "semantic",
                "priority": "high",
                "tone": "amber",
                "metrics": {
                    "cluster_count": int(zone_row.get("cluster_count") or 0),
                    "file_count": int(zone_row.get("file_count") or 0),
                    "warning_count": int(zone_row.get("warning_count") or 0),
                },
                "layout_constraints": {
                    "lane_id": "architecture_zone",
                    "row_id": "architecture_zones",
                    "stable_order": zone_index,
                },
                "refs": [{"kind": "code_map_zone", "ref": str(zone_key)}],
                "inspector_ref": f"code_map:zone:{zone_key}",
            }
        )
        inspectors[f"code_map:zone:{zone_key}"] = {
            "kind": "architecture_zone",
            "title": str(zone_row.get("label") or zone_key),
            "tone": "amber",
            "state": "semantic",
        }

    for cluster_index, (cluster_id, cluster_row_raw) in enumerate(sorted(clusters_contract.items())):
        cluster_row = cluster_row_raw if isinstance(cluster_row_raw, Mapping) else {}
        zone_key = str(cluster_row.get("architecture_zone") or zone_key_by_cluster.get(str(cluster_id)) or "support")
        cluster_node_id = f"cluster:{cluster_id}"
        lane_ids.add("architecture_cluster")
        nodes.append(
            {
                "id": cluster_node_id,
                "kind": "architecture_cluster",
                "label": str(cluster_row.get("label") or cluster_id),
                "summary": cluster_row.get("purpose_sentence") or cluster_row.get("purpose"),
                "lane": "architecture_cluster",
                "domain": zone_key,
                "row_id": f"zone:{zone_key}",
                "parent_cluster_id": f"zone:{zone_key}",
                "rank": cluster_index,
                "state": "semantic",
                "priority": "high" if int(cluster_row.get("warning_count") or 0) else "medium",
                "tone": "amber" if int(cluster_row.get("warning_count") or 0) else "cyan",
                "metrics": {
                    "file_count": int(cluster_row.get("file_count") or 0),
                    "warning_count": int(cluster_row.get("warning_count") or 0),
                    "overlay_count": int(cluster_row.get("overlay_count") or 0),
                },
                "layout_constraints": {
                    "lane_id": "architecture_cluster",
                    "row_id": f"zone:{zone_key}",
                    "parent_cluster_id": f"zone:{zone_key}",
                    "stable_order": cluster_index,
                },
                "refs": [{"kind": "code_map_cluster", "ref": str(cluster_id)}],
                "inspector_ref": f"code_map:cluster:{cluster_id}",
            }
        )
        inspectors[f"code_map:cluster:{cluster_id}"] = {
            "kind": "architecture_cluster",
            "title": str(cluster_row.get("label") or cluster_id),
            "tone": "amber" if int(cluster_row.get("warning_count") or 0) else "cyan",
            "state": "semantic",
        }

    node_ids = {str(node.get("id")) for node in nodes}
    edges: list[dict[str, Any]] = []
    membership_semantics = _edge_semantics_payload("contains")
    membership_style = _edge_semantic_style_payload(membership_semantics)
    for zone_key, zone_row_raw in sorted(zones_contract.items()):
        zone_row = zone_row_raw if isinstance(zone_row_raw, Mapping) else {}
        cluster_ids = zone_row.get("cluster_ids") if isinstance(zone_row.get("cluster_ids"), list) else []
        for index, cluster_id in enumerate(str(row) for row in cluster_ids if row):
            source = f"zone:{zone_key}"
            target = f"cluster:{cluster_id}"
            if source not in node_ids or target not in node_ids:
                continue
            edges.append(
                {
                    "id": f"zone-edge:{graph_scene_core.stable_json_hash([source, target], length=16)}",
                    "source": source,
                    "target": target,
                    "relation": "contains",
                    "kind": "contains",
                    "semantic_kind": membership_style["semantic_kind"],
                    "semantic_style": membership_style,
                    "label": membership_style["short_label"],
                    "confidence": "high",
                    "priority": "medium",
                    "tone": "amber",
                    "bundle_id": "architecture_membership",
                    "layout_constraints": {
                        "bundle_id": "architecture_membership",
                        "line_style_hint": "membership",
                        "stable_order": index,
                    },
                    "refs": [{"kind": "code_map_zone_membership", "ref": f"{zone_key}->{cluster_id}"}],
                }
            )

    aggregate_counts: Counter[tuple[str, str, str, str]] = Counter()
    for index, edge in enumerate(returned_edges):
        source = _code_map_graph_scene_node_id(str(edge.get("from") or "").strip())
        target = _code_map_graph_scene_node_id(str(edge.get("to") or "").strip())
        if source not in node_ids or target not in node_ids:
            continue
        presentation = edge.get("presentation") if isinstance(edge.get("presentation"), Mapping) else {}
        semantics = edge.get("semantics") if isinstance(edge.get("semantics"), Mapping) else _edge_semantics_payload(edge.get("kind"))
        semantic_style = _edge_semantic_style_payload(semantics)
        relation = str(edge.get("kind") or "unknown")
        edge_role = str(presentation.get("edge_role") or _edge_role(relation))
        edges.append(
            {
                "id": f"edge:{graph_scene_core.stable_json_hash([source, relation, target, index], length=16)}",
                "source": source,
                "target": target,
                "relation": relation,
                "kind": relation,
                "semantic_kind": semantic_style["semantic_kind"],
                "semantic_style": semantic_style,
                "label": semantic_style["short_label"],
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
        source_cluster = cluster_id_by_path.get(str(edge.get("from") or "").strip())
        target_cluster = cluster_id_by_path.get(str(edge.get("to") or "").strip())
        if source_cluster and target_cluster and source_cluster != target_cluster:
            semantic_kind = str(semantics.get("semantic_kind") or edge.get("kind") or "unknown")
            label = str(semantics.get("short_label") or semantic_kind)
            aggregate_counts[(source_cluster, target_cluster, semantic_kind, label)] += 1

    for index, ((source_cluster, target_cluster, semantic_kind, label), count) in enumerate(aggregate_counts.most_common(72)):
        source = f"cluster:{source_cluster}"
        target = f"cluster:{target_cluster}"
        if source not in node_ids or target not in node_ids:
            continue
        aggregate_semantics = _edge_semantics_payload(semantic_kind)
        aggregate_style = _edge_semantic_style_payload(aggregate_semantics)
        edges.append(
            {
                "id": f"cluster-edge:{graph_scene_core.stable_json_hash([source, target, semantic_kind], length=16)}",
                "source": source,
                "target": target,
                "relation": semantic_kind,
                "kind": semantic_kind,
                "semantic_kind": aggregate_style["semantic_kind"],
                "semantic_style": aggregate_style,
                "confidence": "high" if count > 1 else "medium",
                "priority": "high" if count > 1 else "medium",
                "tone": "green" if semantic_kind in {"import", "call"} else "cyan",
                "bundle_id": f"cluster_relation:{semantic_kind}",
                "metrics": {"member_edge_count": count},
                "layout_constraints": {
                    "bundle_id": f"cluster_relation:{semantic_kind}",
                    "line_style_hint": "aggregate",
                    "stable_order": index,
                },
                "refs": [
                    {
                        "kind": "code_map_cluster_connection",
                        "ref": f"{source_cluster}->{target_cluster}",
                    }
                ],
                "label": f"{label} {count}",
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
        cluster_semantics,
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
            *[
                {"id": f"domain:{domain}", "label": _code_map_graph_scene_label(domain), "rank": index}
                for index, domain in enumerate(sorted(domain_counts))
            ],
            *[
                {"id": f"zone:{zone_key}", "label": str((zone_row if isinstance(zone_row, Mapping) else {}).get("label") or zone_key), "rank": index}
                for index, (zone_key, zone_row) in enumerate(sorted(zones_contract.items()))
            ],
        ],
        clusters=[
            *[
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
            *[
                {
                    "id": f"zone:{zone_key}",
                    "kind": "architecture_zone",
                    "label": str((zone_row if isinstance(zone_row, Mapping) else {}).get("label") or zone_key),
                    "node_count": int((zone_row if isinstance(zone_row, Mapping) else {}).get("cluster_count") or 0),
                    "edge_count": 0,
                    "collapsed_default": False,
                }
                for zone_key, zone_row in sorted(zones_contract.items())
            ],
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
    cache_key = _derived_payload_cache_key(ui_index)
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
    cache_key = _derived_payload_cache_key(ui_index)
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
        cache_key = _derived_payload_cache_key(graph)
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
    layer = str(file_entry.get("group_id") or file_entry.get("layer") or "").strip() or None
    return {
        "path": path,
        "layer": layer,
        "architecture_location": _architecture_location_for_file(
            path=path,
            layer=layer,
            graph_presence="code_map_packet",
        ),
        "summary": str(file_entry.get("summary") or "").strip() or None,
        "fan_in": int(edges_inbound_count.get(path, 0)),
        "fan_out": int(edges_outbound_count.get(path, 0)),
        "health": _health_from_quality(quality),
        "overlays": _empty_overlays(),
    }


def _file_semantics_fallback(path: str) -> str:
    leaf = _path_leaf(path) or path or "this file"
    return f"Purpose unavailable; showing {leaf} because it participates in the code map."


def _operator_metric_rows(file_row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """[ACTION] Name graph metrics in operator terms instead of raw fan-in/fan-out jargon."""
    overlays = sum(
        _overlay_count(file_row, key)
        for key in ("paper_modules", "semantic_routes", "annex_patterns", "frontend_views", "workingness")
    )
    warnings = _warning_count(file_row)
    rows = [
        {
            "id": "imported_by",
            "label": "imported by",
            "value": int(file_row.get("fan_in") or 0),
            "source_field": "fan_in",
            "display_scope": "drawer_metric",
        },
        {
            "id": "calls_imports",
            "label": "calls/imports",
            "value": int(file_row.get("fan_out") or 0),
            "source_field": "fan_out",
            "display_scope": "drawer_metric",
        },
    ]
    if overlays:
        rows.append(
            {
                "id": "overlays",
                "label": "overlays",
                "value": overlays,
                "source_field": "overlays",
                "display_scope": "drawer_metric",
            }
        )
    if warnings:
        rows.append(
            {
                "id": "warnings",
                "label": "warnings",
                "value": warnings,
                "source_field": "health.warnings",
                "display_scope": "drawer_metric",
            }
        )
    return rows


def _attach_file_semantics(
    file_row: dict[str, Any],
    *,
    file_entry: Mapping[str, Any],
    scope_file_semantics: Mapping[str, Mapping[str, Any]],
) -> None:
    """[ACTION] Mutate a CodeMap file row with backend-authored purpose semantics."""
    path = str(file_row.get("path") or "").strip()
    scope_row = scope_file_semantics.get(path) if path else None
    scope_row = scope_row if isinstance(scope_row, Mapping) else {}
    purpose = _compact_semantic_sentence(scope_row.get("purpose"))
    purpose_source = str(scope_row.get("purpose_source") or "").strip() or None
    if not purpose:
        purpose = _compact_semantic_sentence(file_entry.get("summary") or file_row.get("summary"))
        purpose_source = "code_map.file.summary" if purpose else None
    if not purpose:
        purpose = _file_semantics_fallback(path)
        purpose_source = "code_map.semantic_fallback"

    location = file_row.get("architecture_location")
    location = location if isinstance(location, Mapping) else {}
    role_tags = [
        value
        for value in (
            location.get("architecture_zone_label"),
            location.get("cluster_label"),
            scope_row.get("navigation_group"),
            scope_row.get("group_label"),
        )
        if isinstance(value, str) and value.strip()
    ]
    symbol_samples = scope_row.get("symbol_samples")
    file_row["semantics"] = {
        "schema": CODE_MAP_FILE_SEMANTICS_SCHEMA_VERSION,
        "path": path,
        "compact_label": _path_leaf(path) or path,
        "purpose": purpose,
        "purpose_source": purpose_source,
        "role_tags": role_tags[:6],
        "navigation_group": scope_row.get("navigation_group"),
        "symbol_samples": symbol_samples if isinstance(symbol_samples, list) else [],
        "operator_metrics": _operator_metric_rows(file_row),
    }


def _file_row_semantics(row: Mapping[str, Any]) -> Mapping[str, Any]:
    semantics = row.get("semantics")
    return semantics if isinstance(semantics, Mapping) else {}


def _file_row_purpose(row: Mapping[str, Any]) -> str | None:
    return _compact_semantic_sentence(_file_row_semantics(row).get("purpose"))


def _file_row_has_authored_purpose(row: Mapping[str, Any]) -> bool:
    source = str(_file_row_semantics(row).get("purpose_source") or "")
    return bool(source and source != "code_map.semantic_fallback")


def _primary_text_has_forbidden_fragment(value: Any) -> bool:
    text = str(value or "").lower()
    return any(fragment in text for fragment in CODE_MAP_PRIMARY_TEXT_FORBIDDEN_FRAGMENTS)


def _cluster_operator_metric_rows(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """[ACTION] Aggregate cluster metrics for drawers without making raw graph counters primary text."""
    file_count = len(rows)
    fan_in = sum(int(row.get("fan_in") or 0) for row in rows)
    fan_out = sum(int(row.get("fan_out") or 0) for row in rows)
    warnings = sum(_warning_count(row) for row in rows)
    overlays = sum(
        _overlay_count(row, key)
        for row in rows
        for key in ("paper_modules", "semantic_routes", "annex_patterns", "frontend_views", "workingness")
    )
    metrics = [
        {"id": "files", "label": "files", "value": file_count, "source_field": "cluster.files", "display_scope": "drawer_metric"},
        {"id": "imported_by", "label": "imported by", "value": fan_in, "source_field": "fan_in", "display_scope": "drawer_metric"},
        {"id": "calls_imports", "label": "calls/imports", "value": fan_out, "source_field": "fan_out", "display_scope": "drawer_metric"},
    ]
    if warnings:
        metrics.append({"id": "warnings", "label": "warnings", "value": warnings, "source_field": "health.warnings", "display_scope": "drawer_metric"})
    if overlays:
        metrics.append({"id": "overlays", "label": "overlays", "value": overlays, "source_field": "overlays", "display_scope": "drawer_metric"})
    return metrics


def _dominant_cluster_roles(rows: list[Mapping[str, Any]], *, max_items: int = 5) -> list[str]:
    values: Counter[str] = Counter()
    for row in rows:
        presentation = row.get("presentation") if isinstance(row.get("presentation"), Mapping) else {}
        node_role = str(presentation.get("node_role") or "").strip()
        if node_role:
            values[node_role] += 1
        semantics = _file_row_semantics(row)
        for tag in semantics.get("role_tags") if isinstance(semantics.get("role_tags"), list) else []:
            tag_text = str(tag or "").strip()
            if tag_text:
                values[tag_text] += 1
        navigation_group = str(semantics.get("navigation_group") or "").strip()
        if navigation_group:
            values[navigation_group] += 1
    return [value for value, _count in values.most_common(max_items)]


def _representative_files_with_purpose(rows: list[Mapping[str, Any]], *, max_items: int = 6) -> list[dict[str, Any]]:
    ordered = sorted(
        rows,
        key=lambda row: (
            0 if _file_row_has_authored_purpose(row) else 1,
            -float((row.get("presentation") if isinstance(row.get("presentation"), Mapping) else {}).get("salience_score") or 0),
            str(row.get("path") or ""),
        ),
    )
    samples: list[dict[str, Any]] = []
    for row in ordered:
        path = str(row.get("path") or "").strip()
        if not path:
            continue
        semantics = _file_row_semantics(row)
        purpose = _file_row_purpose(row)
        samples.append(
            {
                "path": path,
                "label": _path_leaf(path) or path,
                "purpose": purpose,
                "purpose_source": str(semantics.get("purpose_source") or "") or None,
                "display_scope": "drawer_sample",
            }
        )
        if len(samples) >= max_items:
            break
    return samples


def _cluster_purpose_model(cluster_label: str, rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    authored = [row for row in rows if _file_row_has_authored_purpose(row) and _file_row_purpose(row)]
    roles = _dominant_cluster_roles(rows)
    representative_files = _representative_files_with_purpose(rows)
    semantic_basis: list[dict[str, Any]] = []
    if roles:
        semantic_basis.append({"kind": "dominant_roles", "values": roles, "display_scope": "drawer_evidence"})
    if authored:
        primary = sorted(
            authored,
            key=lambda row: (
                -float((row.get("presentation") if isinstance(row.get("presentation"), Mapping) else {}).get("salience_score") or 0),
                str(row.get("path") or ""),
            ),
        )[0]
        purpose = _file_row_purpose(primary) or ""
        source = str(_file_row_semantics(primary).get("purpose_source") or "file_semantics")
        secondary = [
            _file_row_purpose(row)
            for row in authored
            if row is not primary and _file_row_purpose(row) and _file_row_purpose(row) != purpose
        ][:1]
        sentence = purpose if not secondary else f"{purpose} Related evidence: {secondary[0]}"
        semantic_basis.append(
            {
                "kind": "file_purpose",
                "count": len(authored),
                "source": source,
                "display_scope": "drawer_evidence",
            }
        )
        return {
            "purpose_sentence": sentence,
            "purpose_source": source,
            "purpose_provenance": "derived_from_representative_file_purposes",
            "fallback_kind": None,
            "display_scope": "primary_card",
            "semantic_basis": semantic_basis,
            "dominant_roles": roles,
            "representative_files_with_purpose": representative_files,
        }
    semantic_basis.append(
        {
            "kind": "fallback_grouping",
            "reason": "no_authored_file_purpose",
            "display_scope": "drawer_evidence",
        }
    )
    return {
        "purpose_sentence": "Purpose unavailable; grouped by import locality.",
        "purpose_source": "code_map.cluster_semantic_fallback",
        "purpose_provenance": "explicit_fallback_no_authored_file_purpose",
        "fallback_kind": "import_locality",
        "display_scope": "fallback",
        "semantic_basis": semantic_basis,
        "dominant_roles": roles,
        "representative_files_with_purpose": representative_files,
    }


def _row_cluster_id(row: Mapping[str, Any]) -> str:
    location = row.get("architecture_location")
    location = location if isinstance(location, Mapping) else {}
    cluster_id = str(location.get("cluster_id") or "").strip()
    if cluster_id:
        return cluster_id
    return f"{row.get('layer') or 'unknown'}:{location.get('cluster_key') or row.get('path') or 'unknown'}"


def _row_zone_key(row: Mapping[str, Any]) -> str:
    location = row.get("architecture_location")
    location = location if isinstance(location, Mapping) else {}
    return str(location.get("architecture_zone") or "support").strip() or "support"


def _semantic_corridor_id(
    *,
    cluster_id: str,
    direction: str,
    neighbor_cluster_id: str,
    semantic_kind: str,
    label: str,
) -> str:
    def part(value: Any) -> str:
        text = str(value or "unknown").strip() or "unknown"
        text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_")
        return text[:96] or "unknown"

    if direction == "incoming":
        source_cluster = neighbor_cluster_id
        target_cluster = cluster_id
    else:
        source_cluster = cluster_id
        target_cluster = neighbor_cluster_id
    return (
        f"corridor:{part(source_cluster)}->{part(target_cluster)}:"
        f"{part(semantic_kind)}:{part(label)}"
    )


def _relation_summaries_by_cluster(
    connections: Iterable[Mapping[str, Any]],
    *,
    cluster_by_path: Mapping[str, str],
    cluster_labels: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    counters: dict[str, Counter[tuple[str, str, str, str]]] = {}
    confidence: dict[tuple[str, str, str, str, str], Counter[str]] = {}
    for edge in connections:
        source_path = str(edge.get("from") or "").strip()
        target_path = str(edge.get("to") or "").strip()
        source_cluster = cluster_by_path.get(source_path)
        target_cluster = cluster_by_path.get(target_path)
        if not source_cluster or not target_cluster:
            continue
        semantics = edge.get("semantics") if isinstance(edge.get("semantics"), Mapping) else _edge_semantics_payload(edge.get("kind"))
        semantic_kind = str(semantics.get("semantic_kind") or edge.get("kind") or "unknown")
        label = str(semantics.get("short_label") or semantic_kind)
        confidence_value = str(edge.get("confidence") or "low")
        if source_cluster == target_cluster:
            key = ("internal", source_cluster, semantic_kind, label)
            counters.setdefault(source_cluster, Counter())[key] += 1
            confidence.setdefault((source_cluster, *key), Counter())[confidence_value] += 1
            continue
        outgoing_key = ("outgoing", target_cluster, semantic_kind, label)
        incoming_key = ("incoming", source_cluster, semantic_kind, label)
        counters.setdefault(source_cluster, Counter())[outgoing_key] += 1
        counters.setdefault(target_cluster, Counter())[incoming_key] += 1
        confidence.setdefault((source_cluster, *outgoing_key), Counter())[confidence_value] += 1
        confidence.setdefault((target_cluster, *incoming_key), Counter())[confidence_value] += 1

    summaries: dict[str, dict[str, Any]] = {}
    for cluster_id, cluster_counts in counters.items():
        rows: list[dict[str, Any]] = []
        for (direction, neighbor_id, semantic_kind, label), count in cluster_counts.most_common(8):
            confidence_counts = confidence.get((cluster_id, direction, neighbor_id, semantic_kind, label), Counter())
            neighbor_label = "inside cluster" if direction == "internal" else cluster_labels.get(neighbor_id, neighbor_id)
            semantic_style = _edge_semantic_style_payload(_edge_semantics_payload(semantic_kind))
            rows.append(
                {
                    "corridor_id": _semantic_corridor_id(
                        cluster_id=cluster_id,
                        direction=direction,
                        neighbor_cluster_id=neighbor_id if direction != "internal" else cluster_id,
                        semantic_kind=semantic_kind,
                        label=label,
                    ),
                    "direction": direction,
                    "neighbor_cluster_id": neighbor_id if direction != "internal" else cluster_id,
                    "neighbor_label": neighbor_label,
                    "semantic_kind": semantic_kind,
                    "semantic_style": semantic_style,
                    "label": label,
                    "count": count,
                    "confidence_counts": dict(sorted(confidence_counts.items())),
                    "display_scope": "drawer_relation",
                }
            )
        summaries[cluster_id] = {
            "schema": "code_map_cluster_relation_summary_v1",
            "top_corridors": rows,
            "incoming_count": sum(row["count"] for row in rows if row["direction"] == "incoming"),
            "outgoing_count": sum(row["count"] for row in rows if row["direction"] == "outgoing"),
            "internal_count": sum(row["count"] for row in rows if row["direction"] == "internal"),
            "omission_receipt": {
                "omitted_corridors": max(0, len(cluster_counts) - len(rows)),
                "reason": "relation_summary_cap" if len(cluster_counts) > len(rows) else None,
            },
        }
    return summaries


def _cluster_drawer_sections(
    *,
    purpose_model: Mapping[str, Any],
    relation_summary: Mapping[str, Any],
    metrics: list[dict[str, Any]],
    samples: list[dict[str, Any]],
    warning_count: int,
    overlay_count: int,
) -> list[dict[str, Any]]:
    sections = [
        {
            "id": "what_this_is",
            "title": "What this is",
            "display_scope": "drawer",
            "rows": [
                {
                    "kind": "purpose",
                    "label": "Purpose",
                    "value": purpose_model.get("purpose_sentence"),
                    "source": purpose_model.get("purpose_source"),
                    "display_scope": "drawer_primary",
                }
            ],
        },
        {
            "id": "why_it_matters",
            "title": "Why it matters",
            "display_scope": "drawer",
            "rows": [
                {
                    "kind": "basis",
                    "label": "Semantic basis",
                    "value": purpose_model.get("semantic_basis"),
                    "display_scope": "drawer_evidence",
                },
                {
                    "kind": "signals",
                    "label": "Signals",
                    "value": {
                        "warnings": warning_count,
                        "overlays": overlay_count,
                    },
                    "display_scope": "drawer_metric",
                },
            ],
        },
        {
            "id": "what_connects_to_it",
            "title": "What connects to it",
            "display_scope": "drawer",
            "rows": list(relation_summary.get("top_corridors") or []),
        },
        {
            "id": "what_is_inside",
            "title": "What is inside",
            "display_scope": "drawer",
            "rows": samples,
        },
        {
            "id": "operator_metrics",
            "title": "Metrics",
            "display_scope": "drawer_debug",
            "rows": metrics,
        },
    ]
    return sections


def _cluster_drilldown_targets(samples: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    primary_path = str(samples[0].get("path") or "").strip() if samples else ""
    targets = [
        {
            "id": "open_lower_level_map",
            "label": "Open lower-level map",
            "target_type": "cluster_map",
            "display_scope": "drawer_action",
        }
    ]
    if primary_path:
        targets.extend(
            [
                {
                    "id": "open_focus_graph",
                    "label": "Open focus graph",
                    "target_type": "focus",
                    "params": {"path": primary_path},
                    "display_scope": "drawer_action",
                },
                {
                    "id": "open_inspector",
                    "label": "Open inspector",
                    "target_type": "inspector",
                    "params": {"path": primary_path},
                    "display_scope": "drawer_action",
                },
            ]
        )
    return targets


def _build_cluster_semantics_summary(
    file_rows: list[dict[str, Any]],
    connections: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """[ACTION] Summarize backend-authored aggregate purpose for Codemap cluster and zone cards."""
    clusters_by_id: dict[str, list[Mapping[str, Any]]] = {}
    zones_by_key: dict[str, list[Mapping[str, Any]]] = {}
    cluster_by_path: dict[str, str] = {}
    cluster_labels: dict[str, str] = {}
    for row in file_rows:
        location = row.get("architecture_location")
        location = location if isinstance(location, Mapping) else {}
        cluster_id = _row_cluster_id(row)
        zone_key = _row_zone_key(row)
        path = str(row.get("path") or "").strip()
        if path:
            cluster_by_path[path] = cluster_id
        clusters_by_id.setdefault(cluster_id, []).append(row)
        zones_by_key.setdefault(zone_key, []).append(row)
        cluster_labels.setdefault(cluster_id, str(location.get("cluster_label") or cluster_id).strip())

    relation_summaries = _relation_summaries_by_cluster(
        connections,
        cluster_by_path=cluster_by_path,
        cluster_labels=cluster_labels,
    )

    cluster_rows: dict[str, dict[str, Any]] = {}
    for cluster_id, rows in sorted(clusters_by_id.items()):
        first_location = rows[0].get("architecture_location")
        first_location = first_location if isinstance(first_location, Mapping) else {}
        label = str(first_location.get("cluster_label") or cluster_id).strip()
        purpose_model = _cluster_purpose_model(label, list(rows))
        purpose = str(purpose_model.get("purpose_sentence") or "")
        purpose_source = str(purpose_model.get("purpose_source") or "") or None
        sample_paths = [str(row.get("path") or "") for row in rows if str(row.get("path") or "").strip()]
        sample_paths = sorted(sample_paths)[:6]
        samples = list(purpose_model.get("representative_files_with_purpose") or [])
        warning_count = sum(_warning_count(row) for row in rows)
        overlay_count = sum(
            _overlay_count(row, key)
            for row in rows
            for key in ("paper_modules", "semantic_routes", "annex_patterns", "frontend_views", "workingness")
        )
        metrics = _cluster_operator_metric_rows(list(rows))
        relation_summary = relation_summaries.get(
            cluster_id,
            {
                "schema": "code_map_cluster_relation_summary_v1",
                "top_corridors": [],
                "incoming_count": 0,
                "outgoing_count": 0,
                "internal_count": 0,
                "omission_receipt": {"omitted_corridors": 0, "reason": None},
            },
        )
        drawer_sections = _cluster_drawer_sections(
            purpose_model=purpose_model,
            relation_summary=relation_summary,
            metrics=metrics,
            samples=samples,
            warning_count=warning_count,
            overlay_count=overlay_count,
        )
        cluster_rows[cluster_id] = {
            "schema": CODE_MAP_CLUSTER_SEMANTICS_SCHEMA_VERSION,
            "id": cluster_id,
            "label": label,
            "architecture_zone": str(first_location.get("architecture_zone") or "support"),
            "architecture_zone_label": first_location.get("architecture_zone_label") or _architecture_zone_label(
                str(first_location.get("architecture_zone") or "support")
            ),
            "purpose": purpose,
            "purpose_sentence": purpose,
            "purpose_source": purpose_source,
            "purpose_provenance": purpose_model.get("purpose_provenance"),
            "provenance": purpose_model.get("purpose_provenance"),
            "semantic_basis": purpose_model.get("semantic_basis"),
            "fallback_kind": purpose_model.get("fallback_kind"),
            "display_scope": purpose_model.get("display_scope"),
            "dominant_roles": purpose_model.get("dominant_roles"),
            "representative_files_with_purpose": samples,
            "relation_summary": relation_summary,
            "operator_metrics": metrics,
            "drawer_sections": drawer_sections,
            "drilldown_targets": _cluster_drilldown_targets(samples),
            "dominant_subsystem": first_location.get("architecture_zone_label") or _architecture_zone_label(
                str(first_location.get("architecture_zone") or "support")
            ),
            "entry_surfaces": sample_paths,
            "file_sample_ids": sample_paths,
            "warning_count": warning_count,
            "overlay_count": overlay_count,
            "file_count": len(rows),
        }

    zone_rows: dict[str, dict[str, Any]] = {}
    for zone_key, rows in sorted(zones_by_key.items()):
        location_rows = [
            row.get("architecture_location")
            for row in rows
            if isinstance(row.get("architecture_location"), Mapping)
        ]
        cluster_ids = sorted(
            {
                str(location.get("cluster_id") or "").strip()
                for location in location_rows
                if str(location.get("cluster_id") or "").strip()
            }
        )
        metrics = [
            {
                "id": "clusters",
                "label": "clusters",
                "value": len(cluster_ids),
                "source_field": "cluster_ids",
                "display_scope": "drawer_metric",
            },
            {
                "id": "files",
                "label": "files",
                "value": len(rows),
                "source_field": "files.length",
                "display_scope": "drawer_metric",
            },
        ]
        warning_count = sum(_warning_count(row) for row in rows)
        if warning_count:
            metrics.append(
                {
                    "id": "warnings",
                    "label": "warnings",
                    "value": warning_count,
                    "source_field": "health.warnings",
                    "display_scope": "drawer_metric",
                }
            )
        purpose = _architecture_zone_purpose(zone_key)
        zone_rows[zone_key] = {
            "schema": CODE_MAP_CLUSTER_SEMANTICS_SCHEMA_VERSION,
            "key": zone_key,
            "label": _architecture_zone_label(zone_key),
            "purpose": purpose,
            "purpose_sentence": purpose,
            "purpose_source": "code_map.architecture_zone_purpose",
            "purpose_provenance": "architecture_zone_contract",
            "semantic_basis": [
                {
                    "kind": "zone_contract",
                    "source": "system.lib.code_architecture_projection",
                    "display_scope": "drawer_evidence",
                }
            ],
            "fallback_kind": None,
            "display_scope": "primary_card",
            "cluster_ids": cluster_ids,
            "cluster_count": len(cluster_ids),
            "file_count": len(rows),
            "warning_count": warning_count,
            "operator_metrics": metrics,
            "drawer_sections": [
                {
                    "id": "what_this_is",
                    "title": "What this is",
                    "display_scope": "drawer",
                    "rows": [
                        {
                            "kind": "purpose",
                            "label": "Purpose",
                            "value": purpose,
                            "source": "code_map.architecture_zone_purpose",
                            "display_scope": "drawer_primary",
                        }
                    ],
                },
                {
                    "id": "what_is_inside",
                    "title": "What is inside",
                    "display_scope": "drawer",
                    "rows": [
                        {
                            "kind": "cluster",
                            "cluster_id": cluster_id,
                            "label": cluster_labels.get(cluster_id, cluster_id),
                            "display_scope": "drawer_sample",
                        }
                        for cluster_id in cluster_ids[:8]
                    ],
                },
                {
                    "id": "operator_metrics",
                    "title": "Metrics",
                    "display_scope": "drawer_debug",
                    "rows": metrics,
                },
            ],
            "drilldown_targets": [
                {
                    "id": "show_zone_corridors",
                    "label": "Show related corridors",
                    "target_type": "zone_selection",
                    "params": {"zone": zone_key},
                    "display_scope": "drawer_action",
                }
            ],
        }

    primary_text_violations = [
        {"scope": "cluster", "id": cluster_id, "field": "purpose_sentence", "value": row.get("purpose_sentence")}
        for cluster_id, row in cluster_rows.items()
        if _primary_text_has_forbidden_fragment(row.get("purpose_sentence"))
    ] + [
        {"scope": "zone", "id": zone_key, "field": "purpose_sentence", "value": row.get("purpose_sentence")}
        for zone_key, row in zone_rows.items()
        if _primary_text_has_forbidden_fragment(row.get("purpose_sentence"))
    ]

    return {
        "schema": CODE_MAP_CLUSTER_SEMANTICS_SCHEMA_VERSION,
        "anti_formula_contract": {
            "schema": "code_map_primary_text_contract_v1",
            "forbidden_fragments": list(CODE_MAP_PRIMARY_TEXT_FORBIDDEN_FRAGMENTS),
            "primary_text_fields": [
                "cluster_semantics.clusters.*.purpose_sentence",
                "cluster_semantics.zones.*.purpose_sentence",
            ],
            "metric_display_scope": "drawer_metric",
            "primary_text_violation_count": len(primary_text_violations),
            "primary_text_violations": primary_text_violations[:12],
        },
        "clusters": cluster_rows,
        "zones": zone_rows,
        "omission_receipt": {
            "omitted_clusters": 0,
            "omitted_zones": 0,
            "reason": None,
        },
    }


def _scene_file_rows_by_path(file_rows: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("path") or ""): row
        for row in file_rows
        if str(row.get("path") or "").strip()
    }


def _scene_file_purpose_row(path: str | None, file_by_path: Mapping[str, Mapping[str, Any]]) -> dict[str, Any] | None:
    clean_path = str(path or "").strip()
    if not clean_path:
        return None
    file_row = file_by_path.get(clean_path)
    file_row = file_row if isinstance(file_row, Mapping) else {}
    semantics = _file_row_semantics(file_row)
    purpose = _file_row_purpose(file_row) if file_row else None
    purpose_source = str(semantics.get("purpose_source") or "").strip() or None
    if not purpose:
        purpose = _file_semantics_fallback(clean_path)
        purpose_source = "code_map.semantic_fallback"
    return {
        "kind": "purpose",
        "label": _path_leaf(clean_path) or clean_path,
        "value": purpose,
        "source": purpose_source,
        "selected_path": clean_path,
        "display_scope": "drawer_primary",
    }


def _scene_edge_kind_values(row: Mapping[str, Any], *field_names: str) -> list[str]:
    values: set[str] = set()
    for field_name in field_names:
        raw = row.get(field_name)
        if isinstance(raw, list):
            values.update(str(item).strip() for item in raw if str(item).strip())
        elif isinstance(raw, set):
            values.update(str(item).strip() for item in raw if str(item).strip())
        elif isinstance(raw, tuple):
            values.update(str(item).strip() for item in raw if str(item).strip())
    return sorted(
        values,
        key=lambda kind: (int(_edge_semantics_payload(kind).get("rank") or 999), kind),
    )


def _scene_relation_label(edge_kinds: Iterable[str], fallback: str) -> str:
    labels: list[str] = []
    for kind in edge_kinds:
        label = str(_edge_semantics_payload(kind).get("short_label") or kind).strip()
        if label and label not in labels:
            labels.append(label)
    return " / ".join(labels[:3]) if labels else fallback


def _focus_neighbor_purpose(direction: str, label: str) -> str:
    if direction == "incoming":
        return f"This path reaches the selected file through {label} relations."
    if direction == "outgoing":
        return f"The selected file reaches this path through {label} relations."
    if direction == "bidirectional":
        return f"This path has a mutual direct relation with the selected file through {label}."
    return f"This path is directly adjacent through {label} relations."


def _focus_neighbor_drawer_row(row: Mapping[str, Any]) -> dict[str, Any]:
    path = str(row.get("path") or "").strip()
    direction = str(row.get("direction") or "none")
    relation_kinds = _scene_edge_kind_values(row, "relation_kinds", "edge_kinds")
    label = _scene_relation_label(relation_kinds, "direct relation")
    return {
        "kind": "focus_neighbor",
        "path": path,
        "compact_label": row.get("basename") or _path_leaf(path) or path,
        "label": label,
        "purpose": _focus_neighbor_purpose(direction, label),
        "source": "code_map.focus_context.direct_neighbors",
        "direction": direction,
        "semantic_kind": relation_kinds[0] if relation_kinds else None,
        "relation_kinds": relation_kinds,
        "count": int(row.get("edge_count") or 0),
        "display_scope": "drawer_relation",
    }


def _semantic_scene_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            try:
                return int(stripped)
            except ValueError:
                return default
    return default


def _focus_transitive_groups(relations: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {"depth_2": [], "depth_3_plus": []}
    for relation in relations:
        if not isinstance(relation, Mapping):
            continue
        depth = _semantic_scene_int(relation.get("depth"), 0)
        role = str(relation.get("role") or "")
        if depth < 2 and role not in {"blast_depth_n", "blast_depth_2", "blast_depth_3"}:
            continue
        key = "depth_2" if depth == 2 else "depth_3_plus"
        grouped[key].append(relation)

    rows: list[dict[str, Any]] = []
    for key, group_rows in grouped.items():
        if not group_rows:
            continue
        depths = []
        for row in group_rows:
            row_depth = _semantic_scene_int(row.get("depth"), 0)
            if row_depth > 0:
                depths.append(row_depth)
        depth_min = min(depths) if depths else (2 if key == "depth_2" else 3)
        depth_max = max(depths) if depths else depth_min
        sample_rows = [_blast_relation_drawer_row(row) for row in group_rows[:6]]
        label = "Depth 2 impact ring" if key == "depth_2" else "Depth 3+ impact ring"
        rows.append(
            {
                "schema": "code_map_focus_transitive_group_v1",
                "id": key,
                "label": label,
                "purpose": (
                    "Collapsed downstream paths reachable through the selected file; "
                    "open a sample to inspect the exact focus graph."
                ),
                "depth_min": depth_min,
                "depth_max": depth_max,
                "relation_count": len(group_rows),
                "sample_rows": sample_rows,
                "sample_paths": [
                    str(row.get("path") or "")
                    for row in sample_rows
                    if str(row.get("path") or "").strip()
                ],
                "omitted_relations": max(0, len(group_rows) - len(sample_rows)),
                "source": "code_map.selection_context.relations",
                "display_scope": "drawer_collapsed_group",
            }
        )
    return rows


def _focus_transitive_group_drawer_row(group: Mapping[str, Any]) -> dict[str, Any]:
    sample_paths = [
        str(path)
        for path in group.get("sample_paths", [])
        if str(path).strip()
    ] if isinstance(group.get("sample_paths"), list) else []
    relation_count = _semantic_scene_int(group.get("relation_count"), 0)
    omitted_relations = _semantic_scene_int(group.get("omitted_relations"), 0)
    sample_suffix = f"; samples: {', '.join(sample_paths[:3])}" if sample_paths else ""
    omitted_suffix = f"; +{omitted_relations} hidden" if omitted_relations else ""
    depth_min = _semantic_scene_int(group.get("depth_min"), 0)
    depth_max = _semantic_scene_int(group.get("depth_max"), depth_min)
    depth_label = (
        f"depth {depth_min}"
        if depth_min == depth_max
        else f"depth {depth_min}-{depth_max}"
    )
    return {
        "kind": "collapsed_transitive_group",
        "label": str(group.get("label") or "Collapsed transitive group"),
        "value": f"{relation_count} paths in {depth_label}{sample_suffix}{omitted_suffix}",
        "purpose": group.get("purpose"),
        "count": relation_count,
        "depth_min": depth_min,
        "depth_max": depth_max,
        "sample_paths": sample_paths,
        "source": group.get("source") or "code_map.selection_context.relations",
        "display_scope": "drawer_collapsed_group",
    }


def _semantic_scene_file_drilldown_targets(path: str | None) -> list[dict[str, Any]]:
    clean_path = str(path or "").strip()
    if not clean_path:
        return []
    return [
        {
            "id": "open_focus_graph",
            "label": "Open focus graph",
            "target_type": "focus",
            "params": {"path": clean_path},
            "display_scope": "drawer_action",
        },
        {
            "id": "open_inspector",
            "label": "Open inspector",
            "target_type": "inspector",
            "params": {"path": clean_path},
            "display_scope": "drawer_action",
        },
    ]


def _focus_scene_drawer_sections(
    *,
    selected_path: str | None,
    file_by_path: Mapping[str, Mapping[str, Any]],
    direct_dependencies: list[Mapping[str, Any]],
    direct_dependents: list[Mapping[str, Any]],
    route_or_control_neighbors: list[Mapping[str, Any]],
    verification_neighbors: list[Mapping[str, Any]],
    collapsed_transitive_groups: list[Mapping[str, Any]],
    hidden_overflow: Mapping[str, Any],
) -> list[dict[str, Any]]:
    purpose_row = _scene_file_purpose_row(selected_path, file_by_path)
    overflow_reason = str(hidden_overflow.get("reason") or "").strip()
    sections = [
        {
            "id": "what_this_file_is",
            "title": "What this file is",
            "display_scope": "drawer",
            "rows": [purpose_row] if purpose_row else [],
        },
        {
            "id": "direct_dependencies",
            "title": "Direct dependencies",
            "display_scope": "drawer",
            "rows": [_focus_neighbor_drawer_row(row) for row in direct_dependencies[:12]],
        },
        {
            "id": "direct_dependents",
            "title": "Direct dependents",
            "display_scope": "drawer",
            "rows": [_focus_neighbor_drawer_row(row) for row in direct_dependents[:12]],
        },
        {
            "id": "route_control_neighbors",
            "title": "Route/control neighbours",
            "display_scope": "drawer",
            "rows": [_focus_neighbor_drawer_row(row) for row in route_or_control_neighbors[:12]],
        },
        {
            "id": "verification_neighbors",
            "title": "Verification neighbours",
            "display_scope": "drawer",
            "rows": [_focus_neighbor_drawer_row(row) for row in verification_neighbors[:12]],
        },
    ]
    if collapsed_transitive_groups:
        sections.append(
            {
                "id": "collapsed_transitive_groups",
                "title": "Collapsed transitive groups",
                "display_scope": "drawer",
                "rows": [
                    _focus_transitive_group_drawer_row(group)
                    for group in collapsed_transitive_groups[:6]
                ],
            }
        )
    if overflow_reason:
        sections.append(
            {
                "id": "hidden_overflow",
                "title": "Hidden overflow",
                "display_scope": "drawer",
                "rows": [
                    {
                        "kind": "omission_receipt",
                        "label": "Overflow",
                        "value": {"reason": overflow_reason},
                        "source": "code_map.focus_context.omission_receipt",
                        "display_scope": "drawer_evidence",
                    }
                ],
            }
        )
    return sections


def _blast_role_label(role: str, depth: int | None) -> str:
    if role == "dependency":
        return "dependency"
    if role == "dependent":
        return "dependent"
    if role == "mutual":
        return "mutual"
    if role == "blast_depth_1":
        return "direct impact"
    if depth and depth > 1:
        return f"depth {depth} impact"
    return "impact relation"


def _blast_relation_purpose(role: str, depth: int | None, direction: str) -> str:
    if role == "dependency":
        return "The selected file depends on this path directly."
    if role in {"dependent", "blast_depth_1"}:
        return "This path can be affected directly by the selected file."
    if role == "mutual":
        return "This path has a mutual direct relationship with the selected file."
    if depth and depth > 1:
        return f"This path sits in the downstream impact ring at depth {depth}."
    if direction == "incoming":
        return "This path can be affected through an incoming relation."
    return "This path is part of the selected file's blast-radius context."


def _blast_relation_drawer_row(row: Mapping[str, Any]) -> dict[str, Any]:
    path = str(row.get("path") or "").strip()
    role = str(row.get("role") or "impact_relation")
    direction = str(row.get("direction") or "none")
    depth = _semantic_scene_int(row.get("depth"), 0) or None
    edge_kinds = _scene_edge_kind_values(row, "edge_kinds", "relation_kinds")
    label = _scene_relation_label(edge_kinds, _blast_role_label(role, depth))
    return {
        "kind": "blast_relation",
        "path": path,
        "compact_label": _path_leaf(path) or path,
        "label": label,
        "purpose": _blast_relation_purpose(role, depth, direction),
        "source": "code_map.selection_context.relations",
        "direction": direction,
        "role": role,
        "depth": depth,
        "semantic_kind": edge_kinds[0] if edge_kinds else None,
        "edge_kinds": edge_kinds,
        "confidence": row.get("confidence"),
        "display_scope": "drawer_relation",
    }


_BLAST_AUTHORITY_OVERLAY_KEYS = (
    "paper_modules",
    "semantic_routes",
    "annex_patterns",
    "frontend_views",
    "workingness",
)


def _blast_relation_signal_row(
    row: Mapping[str, Any],
    *,
    file_by_path: Mapping[str, Mapping[str, Any]],
    group_id: str,
) -> dict[str, Any]:
    base = _blast_relation_drawer_row(row)
    path = str(row.get("path") or "").strip()
    file_row = file_by_path.get(path) if path else None
    file_row = file_row if isinstance(file_row, Mapping) else {}
    health = file_row.get("health") if isinstance(file_row.get("health"), Mapping) else {}
    health_grade = str(health.get("grade") or "").strip() or None
    warning_count = _warning_count(file_row)
    overlay_counts = {
        key: _overlay_count(file_row, key)
        for key in _BLAST_AUTHORITY_OVERLAY_KEYS
        if _overlay_count(file_row, key)
    }
    edge_kinds = set(_scene_edge_kind_values(row, "edge_kinds", "relation_kinds"))
    risk_signals = []
    if warning_count:
        risk_signals.append(f"warnings:{warning_count}")
    if health_grade and health_grade not in {"compliant", "fresh"}:
        risk_signals.append(f"health:{health_grade}")
    authority_signals = [f"{key}:{count}" for key, count in overlay_counts.items()]
    if edge_kinds & {"route", "escalates_to"}:
        authority_signals.append("route_control_edge")
    proof_signals = []
    if edge_kinds & {"test_neighbor", "verification"}:
        proof_signals.append("verification_edge")
    signal_text = "; ".join([*risk_signals, *authority_signals, *proof_signals])
    purpose_prefix = {
        "risk_surfaces": "Risk grouping",
        "authority_surfaces": "Authority grouping",
        "verification_surfaces": "Proof grouping",
    }.get(group_id, "Blast grouping")
    base.update(
        {
            "kind": f"blast_{group_id}_relation",
            "purpose": f"{purpose_prefix}: {signal_text}." if signal_text else base.get("purpose"),
            "warning_count": warning_count,
            "health_grade": health_grade,
            "overlay_counts": overlay_counts,
            "risk_signals": risk_signals,
            "authority_signals": authority_signals,
            "proof_signals": proof_signals,
            "display_scope": "drawer_risk_authority_relation",
        }
    )
    return base


def _blast_risk_authority_groups(
    relations: list[Mapping[str, Any]],
    *,
    file_by_path: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {
        "risk_surfaces": [],
        "authority_surfaces": [],
        "verification_surfaces": [],
    }
    for relation in relations:
        path = str(relation.get("path") or "").strip()
        file_row = file_by_path.get(path) if path else None
        file_row = file_row if isinstance(file_row, Mapping) else {}
        health = file_row.get("health") if isinstance(file_row.get("health"), Mapping) else {}
        health_grade = str(health.get("grade") or "").strip()
        edge_kinds = set(_scene_edge_kind_values(relation, "edge_kinds", "relation_kinds"))
        has_authority_overlay = any(_overlay_count(file_row, key) for key in _BLAST_AUTHORITY_OVERLAY_KEYS)
        if _warning_count(file_row) or (health_grade and health_grade not in {"compliant", "fresh"}):
            groups["risk_surfaces"].append(
                _blast_relation_signal_row(relation, file_by_path=file_by_path, group_id="risk_surfaces")
            )
        if has_authority_overlay or edge_kinds & {"route", "escalates_to"}:
            groups["authority_surfaces"].append(
                _blast_relation_signal_row(relation, file_by_path=file_by_path, group_id="authority_surfaces")
            )
        if edge_kinds & {"test_neighbor", "verification"}:
            groups["verification_surfaces"].append(
                _blast_relation_signal_row(relation, file_by_path=file_by_path, group_id="verification_surfaces")
            )
    return {key: rows[:12] for key, rows in groups.items()}


def _blast_scene_drawer_sections(
    *,
    blast_groups: Mapping[str, list[Mapping[str, Any]]],
    risk_authority_groups: Mapping[str, list[Mapping[str, Any]]],
    omission_receipt: Mapping[str, Any],
) -> list[dict[str, Any]]:
    omitted_relations = _semantic_scene_int(omission_receipt.get("omitted_relations"), 0)
    omission_reason = str(omission_receipt.get("reason") or "").strip()
    sections = [
        {
            "id": "direct_impact",
            "title": "Direct impact",
            "display_scope": "drawer",
            "rows": [_blast_relation_drawer_row(row) for row in blast_groups.get("direct_impact", [])[:16]],
        },
        {
            "id": "depth_2",
            "title": "Depth 2",
            "display_scope": "drawer",
            "rows": [_blast_relation_drawer_row(row) for row in blast_groups.get("depth_2", [])[:16]],
        },
        {
            "id": "depth_3_plus",
            "title": "Depth 3+",
            "display_scope": "drawer",
            "rows": [_blast_relation_drawer_row(row) for row in blast_groups.get("depth_3_plus", [])[:16]],
        },
        {
            "id": "proof_or_control",
            "title": "Proof/control",
            "display_scope": "drawer",
            "rows": [_blast_relation_drawer_row(row) for row in blast_groups.get("proof_or_control", [])[:16]],
        },
    ]
    for section_id, title in (
        ("risk_surfaces", "Risk surfaces"),
        ("authority_surfaces", "Authority surfaces"),
        ("verification_surfaces", "Verification surfaces"),
    ):
        rows = list(risk_authority_groups.get(section_id, []))
        if rows:
            sections.append(
                {
                    "id": section_id,
                    "title": title,
                    "display_scope": "drawer",
                    "rows": rows,
                }
            )
    if omitted_relations or omission_reason:
        sections.append(
            {
                "id": "omission_receipt",
                "title": "Omission receipt",
                "display_scope": "drawer",
                "rows": [
                    {
                        "kind": "omission_receipt",
                        "label": "Selection context cap",
                        "value": {
                            "omitted_relations": omitted_relations,
                            "reason": omission_reason or None,
                        },
                        "source": "code_map.selection_context.omission_receipt",
                        "display_scope": "drawer_evidence",
                    }
                ],
            }
        )
    return sections


def _build_code_map_semantic_scene(
    *,
    file_rows: list[dict[str, Any]],
    cluster_semantics: Mapping[str, Any],
    focus_context: Mapping[str, Any] | None,
    selection_context: Mapping[str, Any] | None,
    selected_path: str | None,
    projection_scope: str,
) -> dict[str, Any]:
    """[ACTION] Compose backend-authored semantic scenes for Codemap renderers."""
    clusters = cluster_semantics.get("clusters") if isinstance(cluster_semantics.get("clusters"), Mapping) else {}
    zones = cluster_semantics.get("zones") if isinstance(cluster_semantics.get("zones"), Mapping) else {}
    cluster_by_path = {
        str(row.get("path") or ""): _row_cluster_id(row)
        for row in file_rows
        if str(row.get("path") or "").strip()
    }
    file_by_path = _scene_file_rows_by_path(file_rows)
    selected_cluster_id = cluster_by_path.get(selected_path or "")
    selected_cluster = clusters.get(selected_cluster_id) if selected_cluster_id and isinstance(clusters.get(selected_cluster_id), Mapping) else None

    aggregate_corridors: list[dict[str, Any]] = []
    for cluster_id, cluster_row_raw in clusters.items():
        cluster_row = cluster_row_raw if isinstance(cluster_row_raw, Mapping) else {}
        relation_summary = cluster_row.get("relation_summary")
        relation_summary = relation_summary if isinstance(relation_summary, Mapping) else {}
        for corridor in relation_summary.get("top_corridors") if isinstance(relation_summary.get("top_corridors"), list) else []:
            if not isinstance(corridor, Mapping):
                continue
            aggregate_corridors.append(
                {
                    "cluster_id": str(cluster_id),
                    "cluster_label": cluster_row.get("label"),
                    **dict(corridor),
                }
            )
    aggregate_corridors.sort(key=lambda row: (-int(row.get("count") or 0), str(row.get("cluster_id") or "")))

    focus = focus_context if isinstance(focus_context, Mapping) else {}
    direct_neighbors = focus.get("direct_neighbors") if isinstance(focus.get("direct_neighbors"), list) else []
    selection = selection_context if isinstance(selection_context, Mapping) else {}
    relations = selection.get("relations") if isinstance(selection.get("relations"), list) else []
    relation_rows = [relation for relation in relations if isinstance(relation, Mapping)]
    blast_groups: dict[str, list[Mapping[str, Any]]] = {"direct_impact": [], "depth_2": [], "depth_3_plus": [], "proof_or_control": []}
    for relation in relation_rows:
        role = str(relation.get("role") or "")
        depth = _semantic_scene_int(relation.get("depth"), 0)
        edge_kinds = {str(kind) for kind in relation.get("edge_kinds") or []}
        if edge_kinds & {"test_neighbor", "verification", "route"}:
            blast_groups["proof_or_control"].append(relation)
        elif depth <= 1 or role in {"dependency", "dependent", "mutual", "blast_depth_1"}:
            blast_groups["direct_impact"].append(relation)
        elif depth == 2:
            blast_groups["depth_2"].append(relation)
        else:
            blast_groups["depth_3_plus"].append(relation)

    focus_selected_path = str(focus.get("selected_path") or selected_path or "").strip() or None
    direct_dependencies = [
        row for row in direct_neighbors
        if isinstance(row, Mapping) and str(row.get("direction") or "") in {"outgoing", "bidirectional"}
    ]
    direct_dependents = [
        row for row in direct_neighbors
        if isinstance(row, Mapping) and str(row.get("direction") or "") in {"incoming", "bidirectional"}
    ]
    route_or_control_neighbors = [
        row for row in direct_neighbors
        if isinstance(row, Mapping)
        and {"route", "call", "escalates_to"} & set(_scene_edge_kind_values(row, "relation_kinds", "edge_kinds"))
    ]
    verification_neighbors = [
        row for row in direct_neighbors
        if isinstance(row, Mapping)
        and {"test_neighbor", "verification"} & set(_scene_edge_kind_values(row, "relation_kinds", "edge_kinds"))
    ]
    collapsed_transitive_groups = _focus_transitive_groups(relation_rows)
    blast_risk_authority_groups = _blast_risk_authority_groups(relation_rows, file_by_path=file_by_path)
    focus_omission_receipt = focus.get("omission_receipt") if isinstance(focus.get("omission_receipt"), Mapping) else {}
    selection_omission_receipt = selection.get("omission_receipt") if isinstance(selection.get("omission_receipt"), Mapping) else {}
    focus_overflow_reason = (
        str(focus_omission_receipt.get("reason") or selection_omission_receipt.get("reason") or "").strip()
        or None
    )
    focus_hidden_overflow = {
        "reason": focus_overflow_reason,
        "omitted_relations": _semantic_scene_int(selection_omission_receipt.get("omitted_relations"), 0),
    }
    blast_group_rows = {
        key: list(value)[:16]
        for key, value in blast_groups.items()
    }
    blast_omission_receipt = (
        selection.get("omission_receipt")
        if isinstance(selection.get("omission_receipt"), Mapping)
        else {"reason": None}
    )

    selected_drawer_sections = (
        list(selected_cluster.get("drawer_sections") or [])
        if isinstance(selected_cluster, Mapping) and isinstance(selected_cluster.get("drawer_sections"), list)
        else []
    )
    incident_corridors_by_id: dict[str, dict[str, Any]] = {}
    if selected_cluster_id:
        for row in aggregate_corridors:
            if row.get("cluster_id") != selected_cluster_id and row.get("neighbor_cluster_id") != selected_cluster_id:
                continue
            corridor_id = str(row.get("corridor_id") or "").strip()
            if not corridor_id:
                corridor_id = _semantic_corridor_id(
                    cluster_id=str(row.get("cluster_id") or "unknown"),
                    direction=str(row.get("direction") or "unknown"),
                    neighbor_cluster_id=str(row.get("neighbor_cluster_id") or "unknown"),
                    semantic_kind=str(row.get("semantic_kind") or "unknown"),
                    label=str(row.get("label") or "unknown"),
                )
                row = {**row, "corridor_id": corridor_id}
            existing = incident_corridors_by_id.get(corridor_id)
            if existing is None or int(row.get("count") or 0) > int(existing.get("count") or 0):
                incident_corridors_by_id[corridor_id] = dict(row)
    incident_corridors = sorted(
        incident_corridors_by_id.values(),
        key=lambda row: (-int(row.get("count") or 0), str(row.get("corridor_id") or "")),
    )
    incident_cluster_ids: list[str] = []
    if selected_cluster_id:
        incident_cluster_ids.append(selected_cluster_id)
    for row in incident_corridors:
        for candidate in (row.get("cluster_id"), row.get("neighbor_cluster_id")):
            candidate_id = str(candidate or "").strip()
            if candidate_id and candidate_id not in incident_cluster_ids:
                incident_cluster_ids.append(candidate_id)
    all_cluster_ids = sorted(str(cluster_id) for cluster_id in clusters.keys())
    incident_cluster_id_set = set(incident_cluster_ids)
    dim_cluster_ids = [
        cluster_id for cluster_id in all_cluster_ids
        if selected_cluster_id and cluster_id not in incident_cluster_id_set
    ]
    incident_corridor_ids = [str(row.get("corridor_id")) for row in incident_corridors if row.get("corridor_id")]
    incident_corridor_id_set = set(incident_corridor_ids)
    dim_corridor_ids_all = [
        str(row.get("corridor_id"))
        for row in aggregate_corridors
        if selected_cluster_id and row.get("corridor_id") and str(row.get("corridor_id")) not in incident_corridor_id_set
    ]
    dim_corridor_ids = dim_corridor_ids_all[:96]
    selection_salience = {
        "schema": "code_map_selection_salience_v1",
        "selected_cluster_id": selected_cluster_id,
        "highlight_cluster_ids": incident_cluster_ids,
        "incident_cluster_ids": incident_cluster_ids,
        "dim_cluster_ids": dim_cluster_ids,
        "highlight_corridor_ids": incident_corridor_ids,
        "incident_corridor_ids": incident_corridor_ids,
        "dim_corridor_ids": dim_corridor_ids,
        "counts": {
            "highlight_clusters": len(incident_cluster_ids),
            "dim_clusters": len(dim_cluster_ids),
            "incident_corridors": len(incident_corridor_ids),
            "dim_corridors": len(dim_corridor_ids_all),
        },
        "omission_receipt": {
            "omitted_dim_corridor_ids": max(0, len(dim_corridor_ids_all) - len(dim_corridor_ids)),
            "reason": "selection_dim_corridor_cap" if len(dim_corridor_ids_all) > len(dim_corridor_ids) else None,
        },
    }
    return {
        "schema": CODE_MAP_SEMANTIC_SCENE_SCHEMA_VERSION,
        "projection_scope": projection_scope,
        "selected_path": selected_path,
        "architecture_scene": {
            "schema": "code_map_architecture_scene_v1",
            "zones": list(zones.values()),
            "clusters": list(clusters.values()),
            "aggregate_corridors": aggregate_corridors[:48],
            "omission_receipt": {
                "omitted_corridors": max(0, len(aggregate_corridors) - 48),
                "reason": "architecture_corridor_cap" if len(aggregate_corridors) > 48 else None,
            },
        },
        "selection_scene": {
            "schema": "code_map_selection_scene_v1",
            "selected_path": selected_path,
            "selected_cluster_id": selected_cluster_id,
            "highlight_cluster_ids": incident_cluster_ids,
            "dim_cluster_ids": dim_cluster_ids,
            "incident_corridor_ids": incident_corridor_ids,
            "dim_corridor_ids": dim_corridor_ids,
            "incident_corridors": incident_corridors[:16],
            "selection_salience": selection_salience,
            "drawer_sections": selected_drawer_sections,
            "drilldown_targets": list(selected_cluster.get("drilldown_targets") or []) if isinstance(selected_cluster, Mapping) else [],
        },
        "focus_scene": {
            "schema": "code_map_focus_scene_v1",
            "selected_path": focus_selected_path,
            "direct_dependencies": direct_dependencies,
            "direct_dependents": direct_dependents,
            "route_or_control_neighbors": route_or_control_neighbors,
            "verification_neighbors": verification_neighbors,
            "collapsed_transitive_groups": collapsed_transitive_groups,
            "hidden_overflow": focus_hidden_overflow,
            "drawer_sections": _focus_scene_drawer_sections(
                selected_path=focus_selected_path,
                file_by_path=file_by_path,
                direct_dependencies=direct_dependencies,
                direct_dependents=direct_dependents,
                route_or_control_neighbors=route_or_control_neighbors,
                verification_neighbors=verification_neighbors,
                collapsed_transitive_groups=collapsed_transitive_groups,
                hidden_overflow=focus_hidden_overflow,
            ),
            "drilldown_targets": _semantic_scene_file_drilldown_targets(focus_selected_path),
        },
        "blast_scene": {
            "schema": "code_map_blast_scene_v1",
            "selected_path": selected_path,
            "groups": blast_group_rows,
            "risk_authority_groups": blast_risk_authority_groups,
            "drawer_sections": _blast_scene_drawer_sections(
                blast_groups=blast_group_rows,
                risk_authority_groups=blast_risk_authority_groups,
                omission_receipt=blast_omission_receipt,
            ),
            "drilldown_targets": _semantic_scene_file_drilldown_targets(selected_path),
            "omission_receipt": blast_omission_receipt,
        },
        "anti_formula_contract": cluster_semantics.get("anti_formula_contract"),
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


def _file_focus_normalize_query(value: Any) -> str:
    """[ACTION] Normalize one CodeMap file-focus search query without treating it as a filesystem path."""
    return " ".join(str(value or "").strip().replace("\\", "/").split())


def _file_focus_compact_token(value: Any) -> str:
    """[ACTION] Collapse a search value into the generated-index token style."""
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


RECIPIENT_SOURCE_ALIAS_MARKERS = (
    "/source_body_floor/source_modules/",
    "/source_artifacts/macro_source/",
    "/source_artifacts/macro_tool/",
    "/source_modules/",
)


def _canonical_private_code_path(value: Any) -> str | None:
    """[ACTION] Map delivered recipient-package source paths back to their private-system repo path."""
    path = str(value or "").strip().replace("\\", "/").lstrip("/")
    if not path:
        return None
    parts = [part for part in path.split("/") if part]
    if any(part == ".." for part in parts):
        return None
    if path.startswith("plectis/src/"):
        return f"microcosm-substrate/src/{path[len('plectis/src/'):]}"
    if path.startswith("plectis/tests/"):
        return f"microcosm-substrate/tests/{path[len('plectis/tests/'):]}"
    if path.startswith("plectis/scripts/"):
        return f"microcosm-substrate/scripts/{path[len('plectis/scripts/'):]}"

    suffix = ""
    for marker in RECIPIENT_SOURCE_ALIAS_MARKERS:
        if marker in path:
            suffix = path.split(marker, 1)[1]
            break
    if not suffix:
        return path
    if suffix.startswith("ai_workflow/"):
        suffix = suffix[len("ai_workflow/"):]
    if suffix.startswith("microcosm_core/"):
        return f"microcosm-substrate/src/{suffix}"
    if suffix.startswith(("system/", "tools/", "codex/")) or suffix == "kernel.py":
        return suffix
    return path


def _file_focus_query_uses_word_spacing(value: str) -> bool:
    """[ACTION] Return true when the operator typed separate words, not one identifier token."""
    return bool(re.search(r"\s+", str(value or "")))


def _file_focus_module_alias(path: str) -> str | None:
    """[ACTION] Return a dotted Python module alias for repo-relative `.py` paths."""
    if not path.endswith(".py"):
        return None
    without_ext = path[:-3]
    if without_ext.endswith("/__init__"):
        without_ext = without_ext[: -len("/__init__")]
    alias = ".".join(part for part in without_ext.split("/") if part)
    return alias or None


def _file_focus_shortest_unique_suffixes(paths: Iterable[str]) -> dict[str, str]:
    """[ACTION] Compute the shortest path suffix that uniquely names each path."""
    normalized_paths = [path for path in paths if path]
    parts_by_path = {path: [part for part in path.split("/") if part] for path in normalized_paths}
    suffix_counts: dict[tuple[str, ...], int] = {}
    for parts in parts_by_path.values():
        for width in range(1, len(parts) + 1):
            suffix = tuple(parts[-width:])
            suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
    out: dict[str, str] = {}
    for path, parts in parts_by_path.items():
        selected = path
        for width in range(1, len(parts) + 1):
            suffix = tuple(parts[-width:])
            if suffix_counts.get(suffix) == 1:
                selected = "/".join(suffix)
                break
        out[path] = selected
    return out


def _file_focus_catalogue_identity(row: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION] Project a catalogue row into the stable resolver candidate envelope."""
    path = str(row.get("path") or "").strip()
    basename = str(row.get("basename") or posixpath.basename(path))
    return {
        "schema": FILE_FOCUS_CANDIDATE_SCHEMA_VERSION,
        "object_id": path,
        "canonical_path": path,
        "basename": basename,
        "stem": str(row.get("stem") or posixpath.splitext(basename)[0] or ""),
        "module_alias": row.get("module_alias"),
        "shortest_unique_suffix": row.get("shortest_unique_suffix") or path,
        "graph_presence": row.get("graph_presence") or "catalogue_only",
    }


def _architecture_cluster_key_for_path(path: str, layer: str | None = None) -> str:
    """[ACTION] Derive the canonical CodeMap cluster key for one repo file path."""
    parts = [part for part in str(path or "").split("/") if part]
    if len(parts) <= 1:
        return str(layer or "unknown").strip() or "unknown"

    def stem(value: str) -> str:
        return posixpath.splitext(value)[0]

    if parts[0] == "system" and len(parts) > 1 and parts[1] == "lib":
        if len(parts) > 3 and parts[2] == "kernel":
            return "system/lib/kernel/" + parts[3]
        if len(parts) > 2 and parts[2].startswith("kernel_nav"):
            return "system/lib/kernel_navigation"
        if len(parts) > 2 and parts[2].startswith("hologram"):
            return "system/lib/hologram"
        if len(parts) > 2 and parts[2].startswith("paper"):
            return "system/lib/paper_modules"
        if len(parts) > 2:
            return "system/lib/" + stem(parts[2])

    if parts[0] == "system" and len(parts) > 1 and parts[1] == "server":
        if len(parts) > 2 and parts[2] == "ui":
            return _architecture_ui_cluster_key(parts)
        if len(parts) > 2 and parts[2] == "tests":
            return "system/server/tests"
        if len(parts) > 2:
            return "system/server/" + stem(parts[2])

    if parts[0] == "codex" and len(parts) > 1:
        return "codex/" + parts[1]
    if parts[0] == "tools" and len(parts) > 1:
        return "tools/" + parts[1]
    if parts[0] == "annexes" and len(parts) > 1:
        return "annexes/" + parts[1]
    if parts[0] == "microcosm-substrate":
        if len(parts) > 4 and parts[1] == "src" and parts[2] == "microcosm_core":
            if parts[3] == "organs":
                return "plectis/organs/" + stem(parts[4])
            return "plectis/" + parts[3]
        if len(parts) > 2 and parts[1] == "tests":
            return "plectis/tests/" + stem(parts[2])
        if len(parts) > 2 and parts[1] == "scripts":
            return "plectis/scripts/" + stem(parts[2])
        return "plectis"
    return "/".join(parts[: min(3, len(parts) - 1)]) or parts[0]


def _architecture_ui_cluster_key(parts: list[str]) -> str:
    """[ACTION] Derive the canonical UI subcluster key used by CodeMap surfaces."""
    prefix = "system/server/ui"

    def stem(value: str) -> str:
        return posixpath.splitext(value)[0]

    if len(parts) > 3 and parts[3] == "src":
        area = parts[4] if len(parts) > 4 else "src"
        next_part = parts[5] if len(parts) > 5 else None
        if not next_part:
            return f"{prefix}/src/{area}"
        if next_part == "__tests__":
            return f"{prefix}/src/{area}/__tests__"
        if "." in next_part:
            return f"{prefix}/src/{area}/{stem(next_part)}"
        return f"{prefix}/src/{area}/{next_part}"
    if len(parts) > 4 and parts[3] == "remotion" and parts[4] == "src":
        area = parts[5] if len(parts) > 5 else "src"
        next_part = parts[6] if len(parts) > 6 else None
        if not next_part:
            return f"{prefix}/remotion/src/{area}"
        if next_part == "__tests__":
            return f"{prefix}/remotion/src/{area}/__tests__"
        if "." in next_part:
            return f"{prefix}/remotion/src/{area}/{stem(next_part)}"
        return f"{prefix}/remotion/src/{area}/{next_part}"
    if len(parts) > 3:
        return f"{prefix}/{stem(parts[3])}"
    return prefix


def _architecture_cluster_label(key: str) -> str:
    """[ACTION] Humanize a CodeMap cluster key without leaking renderer internals."""
    label = str(key or "")
    replacements = (
        ("system/server/ui/src/components/", ""),
        ("system/server/ui/src/pages/", ""),
        ("system/server/ui/src/lib/", ""),
        ("system/server/ui/src/hooks/", ""),
        ("system/server/ui/src/", "ui / "),
        ("system/server/ui/remotion/src/", "remotion / "),
        ("system/lib/", ""),
        ("system/server/", ""),
        ("codex/", "codex / "),
        ("plectis/", "Plectis / "),
    )
    for prefix, replacement in replacements:
        if label.startswith(prefix):
            label = replacement + label[len(prefix):]
            break
    return label.replace("/", " / ").replace("_", " ")


def _architecture_zone_key(layer: str | None, cluster_key: str, cluster_label: str) -> str:
    """[ACTION] Classify the canonical architecture-board zone for one cluster."""
    text = f"{layer or ''} {cluster_key} {cluster_label}".lower()
    if "server/ui" in text or "frontend" in text or "component" in text or "page" in text:
        return "frontend"
    if "system/lib/kernel" in text or "kernel_commands" in text or "command" in text:
        return "kernel_commands"
    if "pipeline" in text or "stage_" in text:
        return "pipeline"
    if "plectis" in text or "microcosm-substrate" in text:
        return "core_runtime"
    if "agent" in text:
        return "agent_runtime"
    if "navigation" in text or "hologram" in text or "kernel_nav" in text:
        return "navigation"
    if "compliance" in text or "standard" in text or "codex" in text:
        return "standards"
    if "core" in text or "bridge" in text or "controller" in text or "metabolism" in text:
        return "core_runtime"
    if "tools" in text or "annex" in text:
        return "tools_codex_annex"
    return "support"


def _architecture_zone_label(key: str) -> str:
    """[ACTION] Label an architecture-board zone."""
    return {
        "kernel_commands": "Kernel commands",
        "pipeline": "Pipeline",
        "agent_runtime": "Agent runtime",
        "navigation": "Navigation / hologram",
        "standards": "Standards / compliance",
        "core_runtime": "Core runtime",
        "frontend": "Frontend / server UI",
        "tools_codex_annex": "Tools / codex / annex",
        "support": "Support",
    }.get(key, "Support")


def _architecture_zone_purpose(key: str) -> str:
    """[ACTION] Describe an architecture-board zone in operator-purpose language."""
    return {
        "kernel_commands": "Kernel command entrypoints, command caches, and route-facing execution surfaces.",
        "pipeline": "Pipeline stages and extract-transform-load surfaces that move substrate state between forms.",
        "agent_runtime": "Agent runtime, delegation, bridge, and session-control surfaces.",
        "navigation": "Navigation, hologram, search, and routing surfaces used to find the right substrate entrypoint.",
        "standards": "Standards, compliance, doctrine, and generated contract surfaces.",
        "core_runtime": "Core runtime libraries, control helpers, and shared execution mechanisms.",
        "frontend": "Station UI, server UI, lenses, components, and client-side read models.",
        "tools_codex_annex": "Tooling, Codex adapters, annex ingestion, and operator-facing maintenance scripts.",
        "support": "Supporting files grouped by generated architecture locality.",
    }.get(key, "Supporting files grouped by generated architecture locality.")


def _architecture_location_for_file(
    *,
    path: str,
    layer: str | None = None,
    graph_presence: Any = None,
) -> dict[str, Any]:
    """[ACTION] Attach canonical renderer-neutral architecture location to one file."""
    path = str(path or "").strip()
    layer = str(layer or "").strip() or None
    cluster_key = _architecture_cluster_key_for_path(path, layer)
    cluster_label = _architecture_cluster_label(cluster_key)
    zone_key = _architecture_zone_key(layer, cluster_key, cluster_label)
    return {
        "schema": CODE_MAP_ARCHITECTURE_LOCATION_SCHEMA_VERSION,
        "path": path,
        "layer": layer,
        "layer_label": str(layer or "unknown").replace("_", " "),
        "cluster_key": cluster_key,
        "cluster_id": f"{layer or 'unknown'}:{cluster_key}",
        "cluster_label": cluster_label,
        "architecture_zone": zone_key,
        "architecture_zone_label": _architecture_zone_label(zone_key),
        "observation_presence": graph_presence or "catalogue_only",
        "graph_presence": graph_presence or "catalogue_only",
        "location_authority": "system.lib.code_architecture_projection",
    }


def _architecture_location_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION] Return or derive the canonical architecture location for a catalogue row."""
    existing = row.get("architecture_location")
    if isinstance(existing, Mapping):
        return dict(existing)
    return _architecture_location_for_file(
        path=str(row.get("path") or ""),
        layer=str(row.get("layer") or "").strip() or None,
        graph_presence=row.get("graph_presence") or "catalogue_only",
    )


def _file_focus_aggregate_context(row: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION] Compatibility alias for consumers still reading aggregate_context."""
    location = _architecture_location_from_row(row)
    return {
        **location,
        "schema": FILE_FOCUS_AGGREGATE_CONTEXT_SCHEMA_VERSION,
        "canonical_schema": CODE_MAP_ARCHITECTURE_LOCATION_SCHEMA_VERSION,
    }


def _file_focus_match_explanation(match: Mapping[str, Any]) -> str:
    """[ACTION] Compactly explain why a resolver candidate matched."""
    field = str(match.get("field") or "field")
    strength = str(match.get("strength") or "match")
    kind = str(match.get("kind") or field)
    return f"{strength}_{kind}_on_{field}"


def _symbol_name_from_id(symbol_id: str) -> str:
    """[ACTION] Derive a readable symbol name from a generated symbol id."""
    suffix = str(symbol_id or "").split("::", 1)[-1].strip()
    return suffix.rsplit(".", 1)[-1] if suffix else ""


def _append_symbol_record(
    out: dict[str, list[dict[str, Any]]],
    seen: dict[str, set[str]],
    *,
    path: str,
    name: str,
    kind: str,
    source: str,
    symbol_id: str | None = None,
    line_start: Any = None,
    line_end: Any = None,
    summary: Any = None,
    signature: Any = None,
) -> None:
    """[ACTION] Append one deduped file-scoped symbol record for search explanation."""
    path = str(path or "").strip()
    name = str(name or "").strip()
    if not path or not name:
        return
    sid = str(symbol_id or f"{path}::{name}").strip()
    marker = sid or f"{kind}:{name}"
    seen_for_path = seen.setdefault(path, set())
    if marker in seen_for_path:
        for existing in out.get(path, []):
            if existing.get("symbol_id") != sid:
                continue
            for key, raw in (
                ("line_start", line_start),
                ("line_end", line_end),
                ("summary", summary),
                ("signature", signature),
            ):
                if raw not in (None, "") and existing.get(key) in (None, ""):
                    existing[key] = raw
            break
        return
    seen_for_path.add(marker)
    row: dict[str, Any] = {
        "symbol_id": sid,
        "name": name,
        "kind": str(kind or "symbol").strip() or "symbol",
        "source": source,
    }
    for key, raw in (
        ("line_start", line_start),
        ("line_end", line_end),
        ("summary", summary),
        ("signature", signature),
    ):
        if raw not in (None, ""):
            row[key] = raw
    out.setdefault(path, []).append(row)


def _append_symbol_from_raw(
    out: dict[str, list[dict[str, Any]]],
    seen: dict[str, set[str]],
    *,
    path: str,
    raw: Any,
    kind: str,
    source: str,
) -> None:
    """[ACTION] Convert a symbol row or bare name into a normalized search record."""
    if isinstance(raw, Mapping):
        symbol_id = str(raw.get("symbol_id") or "").strip()
        name = str(raw.get("name") or "").strip() or _symbol_name_from_id(symbol_id)
        _append_symbol_record(
            out,
            seen,
            path=path,
            name=name,
            kind=str(raw.get("scope_kind") or kind or "symbol"),
            source=source,
            symbol_id=symbol_id or None,
            line_start=raw.get("line_start"),
            line_end=raw.get("line_end"),
            summary=raw.get("summary"),
            signature=raw.get("signature"),
        )
        return
    name = str(raw or "").strip()
    if name:
        _append_symbol_record(out, seen, path=path, name=name, kind=kind, source=source)


def _file_focus_symbol_records_by_path(sources: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """[ACTION] Collect file-scoped symbol/search-object records from generated symbol surfaces."""
    out: dict[str, list[dict[str, Any]]] = {}
    seen: dict[str, set[str]] = {}

    symbols = sources.get("symbols")
    if isinstance(symbols, Mapping):
        for file_row in symbols.get("files", []) or []:
            if not isinstance(file_row, Mapping):
                continue
            path = str(file_row.get("path") or "").strip()
            if not path:
                continue
            for raw in file_row.get("functions", []) or []:
                _append_symbol_from_raw(out, seen, path=path, raw=raw, kind="function", source="symbols.json")
            for raw in file_row.get("classes", []) or []:
                _append_symbol_from_raw(out, seen, path=path, raw=raw, kind="class", source="symbols.json")
                if isinstance(raw, Mapping):
                    for method in raw.get("methods", []) or []:
                        _append_symbol_from_raw(
                            out,
                            seen,
                            path=path,
                            raw=method,
                            kind="method",
                            source="symbols.json",
                        )

    scope_index = sources.get("scope_index")
    if isinstance(scope_index, Mapping):
        for file_row in scope_index.get("files", []) or []:
            if not isinstance(file_row, Mapping):
                continue
            path = str(file_row.get("path") or "").strip()
            if not path:
                continue
            for symbol_id in file_row.get("public_symbol_ids", []) or []:
                sid = str(symbol_id or "").strip()
                if sid:
                    _append_symbol_record(
                        out,
                        seen,
                        path=path,
                        name=_symbol_name_from_id(sid),
                        kind="public_symbol",
                        source="std_python_scope_index.json",
                        symbol_id=sid,
                    )
        for raw in scope_index.get("scopes", []) or []:
            if not isinstance(raw, Mapping):
                continue
            path = str(raw.get("path") or "").strip()
            if not path:
                continue
            _append_symbol_from_raw(
                out,
                seen,
                path=path,
                raw=raw,
                kind=str(raw.get("scope_kind") or "symbol"),
                source="std_python_scope_index.json",
            )

    ui_index = sources.get("ui_index")
    if isinstance(ui_index, Mapping):
        root_prefix = _ui_index_root_prefix(ui_index)
        for file_row in ui_index.get("files", []) or []:
            if not isinstance(file_row, Mapping):
                continue
            path = _repo_path_from_ui_index_path(file_row.get("path"), root_prefix)
            if not path:
                continue
            for field, kind in (("exports", "export"), ("types", "type"), ("props", "prop")):
                for raw in file_row.get(field, []) or []:
                    _append_symbol_from_raw(
                        out,
                        seen,
                        path=path,
                        raw=raw,
                        kind=kind,
                        source="ui_index.json",
                    )

    for path, rows in list(out.items()):
        out[path] = sorted(
            rows,
            key=lambda row: (
                str(row.get("name") or "").lower(),
                str(row.get("symbol_id") or "").lower(),
            ),
        )
    return out


def _file_focus_catalogue_model(root: Path, *, focus: str | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the broadest generated CodeMap file catalogue for search, before any current-packet focus/truncation is applied.
    - Mechanism: Mirrors `build_code_map_packet` source precedence for the rendered projection and augments the search catalogue with the bounded live Python repo inventory so textual lookup can find otherwise-unprojected source files.
    """
    sources = load_hologram_sources(root)
    file_entries = _files_from_graph(sources["graph"])
    graph_paths = {
        str(row.get("path") or "").strip()
        for row in file_entries
        if str(row.get("path") or "").strip()
    }
    edges = normalize_graph_edges(sources["graph"])
    ui_index_fallback = False
    ui_index_merged = False
    scope_index_fallback = False
    scope_index_merged = False
    repo_python_merged = False
    repo_python_fallback = False
    repo_python_import_merged = False
    repo_python_import_parse_capped = False
    projection_absent_fallback = False
    ui_file_entries = _ui_index_file_entries(sources.get("ui_index"))
    ui_paths = {
        str(row.get("path") or "").strip()
        for row in ui_file_entries
        if str(row.get("path") or "").strip()
    }
    ui_edges = _ui_index_import_edges(sources.get("ui_index"))
    scope_file_entries = _scope_index_file_entries(sources.get("scope_index"))
    scope_paths = {
        str(row.get("path") or "").strip()
        for row in scope_file_entries
        if str(row.get("path") or "").strip()
    }
    scope_edges = _scope_index_connection_edges(sources.get("scope_index"))
    repo_paths_for_presence: set[str] = set()
    graph_has_python = any(
        str(row.get("path") or "").strip().endswith(REPO_PYTHON_EXTENSIONS)
        for row in file_entries
    )

    if scope_file_entries:
        scope_index_fallback = not file_entries or not graph_has_python
        scope_index_merged = not scope_index_fallback
        ui_index_merged = bool(ui_file_entries)
        file_entries = _merge_file_entries(file_entries, scope_file_entries, ui_file_entries)
        edges = _merge_connections(edges, scope_edges, ui_edges)
    elif not file_entries or not graph_has_python:
        repo_file_entries = _repo_python_file_entries(root)
        repo_paths_for_presence = {
            str(row.get("path") or "").strip()
            for row in repo_file_entries
            if str(row.get("path") or "").strip()
        }
        if ui_file_entries:
            ui_index_fallback = True
            repo_paths = set(repo_paths_for_presence)
            repo_parse_paths = set(sorted(repo_paths, key=_repo_code_sort_key)[:REPO_PYTHON_IMPORT_PARSE_CAP])
            if focus and focus in repo_paths:
                repo_parse_paths.add(focus)
            repo_python_import_parse_capped = len(repo_paths) > len(repo_parse_paths)
            repo_edges, _repo_symbol_counts = (
                _repo_python_import_edges_and_symbols(root, repo_file_entries, parse_paths=repo_parse_paths)
                if repo_parse_paths
                else ([], {})
            )
            repo_python_fallback = bool(repo_file_entries)
            file_entries = _merge_file_entries(repo_file_entries, ui_file_entries)
            edges = _merge_connections(repo_edges, ui_edges)
        elif repo_file_entries:
            projection_absent_fallback = True
            repo_python_fallback = True
            repo_paths = set(repo_paths_for_presence)
            repo_parse_paths = set(sorted(repo_paths, key=_repo_code_sort_key)[:REPO_PYTHON_IMPORT_PARSE_CAP])
            if focus and focus in repo_paths:
                repo_parse_paths.add(focus)
            repo_python_import_parse_capped = len(repo_paths) > len(repo_parse_paths)
            repo_edges, _repo_symbol_counts = (
                _repo_python_import_edges_and_symbols(root, repo_file_entries, parse_paths=repo_parse_paths)
                if repo_parse_paths
                else ([], {})
            )
            file_entries = _merge_file_entries(repo_file_entries)
            edges = _merge_connections(repo_edges)
    elif ui_file_entries:
        ui_index_merged = True
        file_entries = _merge_file_entries(file_entries, ui_file_entries)
        edges = _merge_connections(edges, ui_edges)

    projection_file_entries = list(file_entries)
    projection_edges = list(edges)

    if not repo_python_fallback:
        repo_file_entries = _repo_python_file_entries(root)
        repo_paths_for_presence = {
            str(row.get("path") or "").strip()
            for row in repo_file_entries
            if str(row.get("path") or "").strip()
        }
        if repo_file_entries:
            repo_python_merged = True
            file_entries = _merge_file_entries(file_entries, repo_file_entries)

    reason_parts: list[str] = []
    if ui_index_fallback:
        reason_parts.append("used_ui_index_fallback")
    if scope_index_fallback:
        reason_parts.append("primary_hologram_graph_missing_or_ui_only; used_std_python_scope_index_fallback")
    if scope_index_merged:
        reason_parts.append("merged_std_python_scope_index")
    if repo_python_fallback and projection_absent_fallback:
        reason_parts.append("projection_sources_missing; used_repo_python_search_fallback")
    elif repo_python_fallback:
        reason_parts.append("primary_hologram_graph_and_scope_index_missing; used_repo_python_import_fallback")
    if repo_python_merged:
        reason_parts.append("merged_repo_python_files")
    if repo_python_import_merged:
        reason_parts.append("merged_repo_python_import_edges")
    if repo_python_import_parse_capped:
        reason_parts.append("repo_python_import_parse_cap_applied")
    if ui_index_merged:
        reason_parts.append("merged_ui_index")

    return {
        "sources": sources,
        "file_entries": file_entries,
        "projection_file_entries": projection_file_entries,
        "edges": edges,
        "projection_edges": projection_edges,
        "presence_paths": {
            "hologram_graph": graph_paths,
            "std_python_scope_index": scope_paths,
            "ui_index": ui_paths,
            "repo_scan": repo_paths_for_presence,
        },
        "symbol_records_by_path": _file_focus_symbol_records_by_path(sources),
        "source_strategy": {
            "primary": (
                "std_python_scope_index"
                if scope_index_fallback
                else "repo_python_search_fallback"
                if projection_absent_fallback
                else "hologram_graph"
            ),
            "scope_index_fallback": scope_index_fallback,
            "scope_index_merged": scope_index_merged,
            "ui_index_fallback": ui_index_fallback,
            "ui_index_merged": ui_index_merged,
            "repo_python_fallback": repo_python_fallback,
            "repo_python_merged": repo_python_merged,
            "repo_python_import_merged": repo_python_import_merged,
            "repo_python_import_parse_capped": repo_python_import_parse_capped,
            "projection_absent_fallback": projection_absent_fallback,
            "runtime_repo_scan": (
                "projection_absent_search_fallback"
                if projection_absent_fallback
                else "merged_search_catalogue_only"
                if repo_python_merged
                else "fallback_only"
                if repo_python_fallback
                else "disabled_when_generated_scope_index_present"
                if scope_file_entries
                else "not_needed"
            ),
        },
        "catalogue_reason": "; ".join(reason_parts) if reason_parts else None,
        "projection_absent_fallback": projection_absent_fallback,
    }


def _file_focus_locator_model(
    root: Path,
    *,
    focus: str | None = None,
    repo_file_entries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the low-latency file locator used while the operator is typing.
    - Mechanism: Load only small file-list sidecars plus the live Python path inventory, then derive the same architecture location rows as the full catalogue without loading symbol bodies or overlay-heavy packet data.
    """
    sources = {
        "graph": _read_locator_json(root, HOLOGRAM_GRAPH_PATH),
        "ui_index": _read_locator_json(root, HOLOGRAM_UI_INDEX_PATH),
        "scope_index": _read_locator_json(root, PYTHON_SCOPE_INDEX_PATH),
    }
    file_entries = _files_from_graph(sources["graph"])
    graph_paths = {
        str(row.get("path") or "").strip()
        for row in file_entries
        if str(row.get("path") or "").strip()
    }
    ui_index_fallback = False
    ui_index_merged = False
    scope_index_fallback = False
    scope_index_merged = False
    repo_python_merged = False
    repo_python_fallback = False
    projection_absent_fallback = False

    ui_file_entries = _ui_index_file_entries(sources.get("ui_index"))
    ui_paths = {
        str(row.get("path") or "").strip()
        for row in ui_file_entries
        if str(row.get("path") or "").strip()
    }
    scope_file_entries = _scope_index_file_entries(sources.get("scope_index"))
    scope_paths = {
        str(row.get("path") or "").strip()
        for row in scope_file_entries
        if str(row.get("path") or "").strip()
    }
    repo_file_entries = list(repo_file_entries) if repo_file_entries is not None else _repo_python_file_entries(root)
    repo_paths_for_presence = {
        str(row.get("path") or "").strip()
        for row in repo_file_entries
        if str(row.get("path") or "").strip()
    }
    graph_has_python = any(
        str(row.get("path") or "").strip().endswith(REPO_PYTHON_EXTENSIONS)
        for row in file_entries
    )

    if scope_file_entries:
        scope_index_fallback = not file_entries or not graph_has_python
        scope_index_merged = not scope_index_fallback
        ui_index_merged = bool(ui_file_entries)
        file_entries = _merge_file_entries(file_entries, scope_file_entries, ui_file_entries)
    elif not file_entries or not graph_has_python:
        if ui_file_entries:
            ui_index_fallback = True
            file_entries = _merge_file_entries(ui_file_entries)
        elif repo_file_entries:
            projection_absent_fallback = True
            repo_python_fallback = True
            file_entries = _merge_file_entries(repo_file_entries)
    elif ui_file_entries:
        ui_index_merged = True
        file_entries = _merge_file_entries(file_entries, ui_file_entries)

    projection_file_entries = list(file_entries)
    projection_edges: list[dict[str, Any]] = []
    if focus:
        graph_edges = normalize_graph_edges(sources["graph"])
        scope_edges = _scope_index_connection_edges(sources.get("scope_index"))
        ui_edges = _ui_index_import_edges(sources.get("ui_index"))
        projection_edges = _merge_connections(graph_edges, scope_edges, ui_edges)

    if not repo_python_fallback and repo_file_entries:
        repo_python_merged = True
        file_entries = _merge_file_entries(file_entries, repo_file_entries)

    reason_parts: list[str] = []
    if ui_index_fallback:
        reason_parts.append("used_ui_index_fallback")
    if scope_index_fallback:
        reason_parts.append("primary_hologram_graph_missing_or_ui_only; used_std_python_scope_index_fallback")
    if scope_index_merged:
        reason_parts.append("merged_std_python_scope_index")
    if projection_absent_fallback:
        reason_parts.append("projection_sources_missing; used_repo_python_search_fallback")
    elif repo_python_fallback:
        reason_parts.append("primary_hologram_graph_and_scope_index_missing; used_repo_python_import_fallback")
    if repo_python_merged:
        reason_parts.append("merged_repo_python_files")
    if ui_index_merged:
        reason_parts.append("merged_ui_index")

    return {
        "sources": sources,
        "file_entries": file_entries,
        "projection_file_entries": projection_file_entries,
        "edges": projection_edges,
        "projection_edges": projection_edges,
        "presence_paths": {
            "hologram_graph": graph_paths,
            "std_python_scope_index": scope_paths,
            "ui_index": ui_paths,
            "repo_scan": repo_paths_for_presence,
        },
        "symbol_records_by_path": {},
        "source_strategy": {
            "primary": (
                "std_python_scope_index"
                if scope_index_fallback
                else "repo_python_search_fallback"
                if projection_absent_fallback
                else "hologram_graph"
            ),
            "scope_index_fallback": scope_index_fallback,
            "scope_index_merged": scope_index_merged,
            "ui_index_fallback": ui_index_fallback,
            "ui_index_merged": ui_index_merged,
            "repo_python_fallback": repo_python_fallback,
            "repo_python_merged": repo_python_merged,
            "repo_python_import_merged": False,
            "repo_python_import_parse_capped": False,
            "projection_absent_fallback": projection_absent_fallback,
            "runtime_repo_scan": (
                "projection_absent_search_fallback"
                if projection_absent_fallback
                else "merged_search_catalogue_only"
                if repo_python_merged
                else "fallback_only"
                if repo_python_fallback
                else "disabled_when_generated_scope_index_present"
                if scope_file_entries
                else "not_needed"
            ),
        },
        "catalogue_reason": "; ".join(reason_parts) if reason_parts else None,
        "projection_absent_fallback": projection_absent_fallback,
    }


def _file_focus_search_tokens_for_path(
    *,
    path: str,
    entry: Mapping[str, Any],
    scope_file: Mapping[str, Any] | None,
    symbols: Iterable[Mapping[str, Any]],
    module_alias: str | None = None,
    stem: str | None = None,
    shortest_unique_suffix: str | None = None,
) -> list[str]:
    """[ACTION] Build deterministic low-cost search tokens for one file catalogue row."""
    values: list[Any] = [path, posixpath.basename(path), stem, module_alias, shortest_unique_suffix]
    values.extend(part for part in path.split("/") if part)
    values.extend([entry.get("group_id"), entry.get("layer"), entry.get("summary")])
    if isinstance(scope_file, Mapping):
        values.extend(scope_file.get("search_tokens", []) or [])
        values.extend(
            [
                scope_file.get("summary"),
                scope_file.get("browse_summary"),
                scope_file.get("when_needed"),
                scope_file.get("group_label"),
                scope_file.get("navigation_group"),
            ]
        )
    for symbol in symbols:
        values.extend([symbol.get("name"), symbol.get("symbol_id"), symbol.get("summary")])

    tokens: list[str] = []
    seen: set[str] = set()
    for value in values:
        for token in re.split(r"[^A-Za-z0-9_./:-]+", str(value or "")):
            for candidate in (token.strip().lower(), _file_focus_compact_token(token)):
                if candidate and candidate not in seen:
                    seen.add(candidate)
                    tokens.append(candidate)
    return tokens


def _file_focus_catalogue_rows(model: Mapping[str, Any]) -> list[dict[str, Any]]:
    """[ACTION] Convert source-model file entries into normalized searchable catalogue rows."""
    sources = model.get("sources") if isinstance(model.get("sources"), Mapping) else {}
    scope_index = sources.get("scope_index") if isinstance(sources, Mapping) else None
    scope_files_by_path: dict[str, Mapping[str, Any]] = {}
    if isinstance(scope_index, Mapping):
        for raw in scope_index.get("files", []) or []:
            if not isinstance(raw, Mapping):
                continue
            path = str(raw.get("path") or "").strip()
            if path:
                scope_files_by_path[path] = raw

    symbol_records_by_path = model.get("symbol_records_by_path")
    symbol_records_by_path = symbol_records_by_path if isinstance(symbol_records_by_path, Mapping) else {}
    presence_paths = model.get("presence_paths") if isinstance(model.get("presence_paths"), Mapping) else {}
    graph_paths = presence_paths.get("hologram_graph") if isinstance(presence_paths, Mapping) else set()
    graph_paths = graph_paths if isinstance(graph_paths, set) else set()
    scope_paths = presence_paths.get("std_python_scope_index") if isinstance(presence_paths, Mapping) else set()
    scope_paths = scope_paths if isinstance(scope_paths, set) else set()
    ui_paths = presence_paths.get("ui_index") if isinstance(presence_paths, Mapping) else set()
    ui_paths = ui_paths if isinstance(ui_paths, set) else set()
    repo_paths = presence_paths.get("repo_scan") if isinstance(presence_paths, Mapping) else set()
    repo_paths = repo_paths if isinstance(repo_paths, set) else set()
    entries = [entry for entry in model.get("file_entries", []) or [] if isinstance(entry, Mapping)]
    unique_suffix_by_path = _file_focus_shortest_unique_suffixes(
        str(entry.get("path") or "").strip()
        for entry in entries
        if str(entry.get("path") or "").strip()
    )
    rows: list[dict[str, Any]] = []
    for entry in entries:
        path = str(entry.get("path") or "").strip()
        if not path:
            continue
        scope_file = scope_files_by_path.get(path)
        symbols = list(symbol_records_by_path.get(path, []) or [])
        basename = posixpath.basename(path)
        stem = posixpath.splitext(basename)[0]
        module_alias = _file_focus_module_alias(path)
        shortest_unique_suffix = unique_suffix_by_path.get(path, path)
        layer = str(entry.get("group_id") or entry.get("layer") or "").strip() or None
        summary = str(entry.get("summary") or "").strip() or None
        if not summary and isinstance(scope_file, Mapping):
            summary = str(scope_file.get("summary") or scope_file.get("browse_summary") or "").strip() or None
        if path in graph_paths:
            graph_presence = "hologram_graph"
        elif path in scope_paths:
            graph_presence = "std_python_scope_index"
        elif path in ui_paths:
            graph_presence = "ui_index"
        elif path in repo_paths:
            graph_presence = "repo_scan"
        else:
            graph_presence = "catalogue_only"
        architecture_location = _architecture_location_for_file(
            path=path,
            layer=layer,
            graph_presence=graph_presence,
        )
        search_tokens = _file_focus_search_tokens_for_path(
            path=path,
            entry=entry,
            scope_file=scope_file,
            symbols=symbols,
            module_alias=module_alias,
            stem=stem,
            shortest_unique_suffix=shortest_unique_suffix,
        )
        token_pairs: list[dict[str, Any]] = []
        for token in search_tokens:
            token_text = str(token or "").lower()
            token_pairs.append(
                {
                    "text": token_text,
                    "compact": _file_focus_compact_token(token_text),
                    "value": token,
                }
            )
        symbol_haystacks: list[dict[str, Any]] = []
        for symbol in symbols:
            if not isinstance(symbol, Mapping):
                continue
            name = str(symbol.get("name") or "").strip()
            symbol_id = str(symbol.get("symbol_id") or "").strip()
            line_start = symbol.get("line_start")
            line_end = symbol.get("line_end")
            for field, value in (("symbol_name", name), ("symbol_id", symbol_id)):
                lower = value.lower()
                if lower:
                    symbol_haystacks.append(
                        {
                            "field": field,
                            "text": lower,
                            "compact": _file_focus_compact_token(lower),
                            "value": value,
                            "symbol_id": symbol_id or None,
                            "symbol_name": name or None,
                            "line_start": line_start,
                            "line_end": line_end,
                        }
                    )
        index_values = [
            path,
            basename,
            stem,
            module_alias,
            shortest_unique_suffix,
            layer,
            summary,
            *[str(pair.get("text") or "") for pair in token_pairs],
            *[str(row.get("text") or "") for row in symbol_haystacks],
        ]
        rows.append(
            {
                "path": path,
                "basename": basename,
                "stem": stem,
                "module_alias": module_alias,
                "shortest_unique_suffix": shortest_unique_suffix,
                "graph_presence": graph_presence,
                "layer": layer,
                "architecture_location": architecture_location,
                "summary": summary,
                "symbols": symbols,
                "search_tokens": search_tokens,
                "_path_compact": _file_focus_compact_token(path),
                "_basename_compact": _file_focus_compact_token(basename),
                "_stem_compact": _file_focus_compact_token(stem),
                "_module_alias_compact": _file_focus_compact_token(module_alias),
                "_shortest_suffix_compact": _file_focus_compact_token(shortest_unique_suffix),
                "_search_token_pairs": token_pairs,
                "_symbol_haystacks": symbol_haystacks,
                "_search_index_lower": "\n".join(str(value or "").lower() for value in index_values if value),
                "_search_index_compact": "\n".join(_file_focus_compact_token(value) for value in index_values if value),
            }
        )
    return rows


def _file_focus_locator_cache_key(root: Path, *, focus: str | None) -> tuple[str, str, str]:
    """[ACTION] Return the stable active-generation cache key before any freshness work."""
    return (str(root.resolve()), "architecture_locator_generation", focus or "")


def _file_focus_delta_from_paths(
    previous_rows: Iterable[Mapping[str, Any]],
    current_rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """[ACTION] Summarize the live-overlay path delta between locator generations."""
    previous = {str(row.get("path") or "").strip() for row in previous_rows if str(row.get("path") or "").strip()}
    current = {str(row.get("path") or "").strip() for row in current_rows if str(row.get("path") or "").strip()}
    added = sorted(current - previous, key=_repo_code_sort_key)
    removed = sorted(previous - current, key=_repo_code_sort_key)
    return {
        "schema": "file_focus_locator_live_delta_v1",
        "status": "changed" if added or removed else "empty",
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_path_count": len(added) + len(removed),
        "added_paths": added[:25],
        "removed_paths": removed[:25],
        "truncated": len(added) > 25 or len(removed) > 25,
    }


def _build_and_store_file_focus_locator_generation(
    root: Path,
    *,
    focus: str | None,
    force: bool,
) -> dict[str, Any]:
    """[ACTION] Refresh the materialized file-focus locator generation behind one singleflight boundary."""
    cache_key = _file_focus_locator_cache_key(root, focus=focus)
    started_at = time.perf_counter()
    repo_file_entries, repo_manifest_token, repo_scan_metrics = _scan_repo_python_files(root)
    fingerprint, sidecar_fingerprint = _file_focus_source_fingerprint_from_manifest(root, repo_manifest_token)
    with _DERIVED_CACHE_LOCK:
        previous = _FILE_FOCUS_LOCATOR_CACHE.get(cache_key)
    if (
        not force
        and isinstance(previous, Mapping)
        and str(previous.get("fingerprint") or "") == fingerprint
    ):
        reused = dict(previous)
        generation = dict(reused.get("generation") or {})
        generation["refresh_status"] = "reused_existing_generation"
        generation["last_refresh_checked_at"] = _now_iso()
        generation["refresh_ms"] = round((time.perf_counter() - started_at) * 1000.0, 3)
        generation["repo_scan"] = repo_scan_metrics
        reused["generation"] = generation
        return reused

    previous_rows = previous.get("catalogue_rows", []) if isinstance(previous, Mapping) else []
    previous_rows = previous_rows if isinstance(previous_rows, list) else []
    model = _file_focus_locator_model(root, focus=focus, repo_file_entries=repo_file_entries)
    locator_rows = _file_focus_catalogue_rows(model)
    live_delta = _file_focus_delta_from_paths(previous_rows, locator_rows)
    refresh_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
    generated_at = _now_iso()
    bundle = {
        "schema": FILE_FOCUS_LOCATOR_GENERATION_SCHEMA_VERSION,
        "fingerprint": fingerprint,
        "model": model,
        "catalogue_rows": locator_rows,
        "catalogue_kind": "architecture_locator",
        "generation": {
            "schema": FILE_FOCUS_LOCATOR_GENERATION_SCHEMA_VERSION,
            "generation_id": f"file_focus_locator:{fingerprint}",
            "generated_at": generated_at,
            "generated_monotonic": time.monotonic(),
            "refresh_status": "rebuilt",
            "refresh_ms": refresh_ms,
            "source_fingerprint": fingerprint,
            "base_sidecar_fingerprint": sidecar_fingerprint,
            "repo_manifest_token": repo_manifest_token,
            "repo_scan": repo_scan_metrics,
            "live_delta": live_delta,
            "materialization": "process_local_immutable_generation",
            "refresh_owner": "system.lib.code_architecture_projection.refresh_file_focus_locator_generation",
            "hot_path_contract": "search_reads_generation_without_repo_manifest_acquisition",
        },
    }
    with _DERIVED_CACHE_LOCK:
        _bounded_cache_set(
            _FILE_FOCUS_LOCATOR_CACHE,
            cache_key,
            bundle,
            max_entries=DERIVED_CACHE_MAX_ENTRIES,
        )
    return bundle


def refresh_file_focus_locator_generation(
    root: Path,
    *,
    focus: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """[ACTION] Explicitly refresh the materialized architecture locator generation."""
    cache_key = _file_focus_locator_cache_key(root, focus=focus)
    with _DERIVED_CACHE_LOCK:
        event = _FILE_FOCUS_LOCATOR_INFLIGHT.get(cache_key)
        builder = event is None
        if event is None:
            event = threading.Event()
            _FILE_FOCUS_LOCATOR_INFLIGHT[cache_key] = event
    if not builder:
        event.wait()
        with _DERIVED_CACHE_LOCK:
            cached_after_wait = _FILE_FOCUS_LOCATOR_CACHE.get(cache_key)
        if isinstance(cached_after_wait, Mapping):
            return dict(cached_after_wait)

    try:
        return _build_and_store_file_focus_locator_generation(root, focus=focus, force=force)
    except Exception:
        with _DERIVED_CACHE_LOCK:
            stale = _FILE_FOCUS_LOCATOR_CACHE.get(cache_key)
        if isinstance(stale, Mapping):
            degraded = dict(stale)
            generation = dict(degraded.get("generation") or {})
            generation["refresh_status"] = "refresh_failed_serving_stale_generation"
            generation["refresh_failed_at"] = _now_iso()
            degraded["generation"] = generation
            return degraded
        raise
    finally:
        with _DERIVED_CACHE_LOCK:
            inflight = _FILE_FOCUS_LOCATOR_INFLIGHT.pop(cache_key, None)
            if inflight is not None:
                inflight.set()


def _schedule_file_focus_locator_refresh(root: Path, *, focus: str | None) -> bool:
    """[ACTION] Start a non-blocking stale-generation refresh, if one is not already running."""
    cache_key = _file_focus_locator_cache_key(root, focus=focus)
    with _DERIVED_CACHE_LOCK:
        if cache_key in _FILE_FOCUS_LOCATOR_INFLIGHT:
            return False
        event = threading.Event()
        _FILE_FOCUS_LOCATOR_INFLIGHT[cache_key] = event

    def _refresh() -> None:
        try:
            _build_and_store_file_focus_locator_generation(root, focus=focus, force=False)
        finally:
            with _DERIVED_CACHE_LOCK:
                inflight = _FILE_FOCUS_LOCATOR_INFLIGHT.pop(cache_key, None)
                if inflight is not None:
                    inflight.set()

    threading.Thread(
        target=_refresh,
        name="file-focus-locator-refresh",
        daemon=True,
    ).start()
    return True


def _file_focus_locator_bundle(root: Path, *, focus: str | None) -> dict[str, Any]:
    """[ACTION] Return the active low-latency locator generation without foreground repo freshness work."""
    cache_key = _file_focus_locator_cache_key(root, focus=focus)
    with _DERIVED_CACHE_LOCK:
        cached = _FILE_FOCUS_LOCATOR_CACHE.get(cache_key)
    if isinstance(cached, Mapping):
        bundle = dict(cached)
        generation = bundle.get("generation") if isinstance(bundle.get("generation"), Mapping) else {}
        generated_monotonic = float(generation.get("generated_monotonic") or 0.0)
        if generated_monotonic and time.monotonic() - generated_monotonic > FILE_FOCUS_LOCATOR_REFRESH_TTL_S:
            _schedule_file_focus_locator_refresh(root, focus=focus)
        return bundle
    return refresh_file_focus_locator_generation(root, focus=focus, force=False)


def _file_focus_catalogue_bundle(root: Path, *, focus: str | None, fingerprint: str | None = None) -> dict[str, Any]:
    """[ACTION] Return cached file-focus catalogue rows for one source fingerprint/focus context."""
    fingerprint = fingerprint or compute_file_focus_source_fingerprint(root)
    cache_key = (str(root.resolve()), fingerprint, focus or "")
    with _DERIVED_CACHE_LOCK:
        cached = _FILE_FOCUS_CATALOGUE_CACHE.get(cache_key)
        if isinstance(cached, Mapping):
            return dict(cached)
        event = _FILE_FOCUS_CATALOGUE_INFLIGHT.get(cache_key)
        builder = event is None
        if event is None:
            event = threading.Event()
            _FILE_FOCUS_CATALOGUE_INFLIGHT[cache_key] = event
    if not builder:
        event.wait()
        with _DERIVED_CACHE_LOCK:
            cached_after_wait = _FILE_FOCUS_CATALOGUE_CACHE.get(cache_key)
        if isinstance(cached_after_wait, Mapping):
            return dict(cached_after_wait)

    try:
        model = _file_focus_catalogue_model(root, focus=focus)
        catalogue_rows = _file_focus_catalogue_rows(model)
        bundle = {
            "fingerprint": fingerprint,
            "model": model,
            "catalogue_rows": catalogue_rows,
        }
        with _DERIVED_CACHE_LOCK:
            _bounded_cache_set(
                _FILE_FOCUS_CATALOGUE_CACHE,
                cache_key,
                bundle,
                max_entries=DERIVED_CACHE_MAX_ENTRIES,
            )
        return bundle
    finally:
        with _DERIVED_CACHE_LOCK:
            inflight = _FILE_FOCUS_CATALOGUE_INFLIGHT.pop(cache_key, None)
            if inflight is not None:
                inflight.set()

def _file_focus_match_for_row(
    row: Mapping[str, Any],
    *,
    query: str,
    query_lower: str,
    query_path_lower: str,
    query_compact: str,
) -> dict[str, Any] | None:
    """[ACTION] Return the strongest deterministic match reason for one catalogue row."""
    if not query_lower:
        return None
    path = str(row.get("path") or "")
    basename = str(row.get("basename") or posixpath.basename(path))
    stem = str(row.get("stem") or posixpath.splitext(basename)[0] or "")
    module_alias = str(row.get("module_alias") or "")
    shortest_unique_suffix = str(row.get("shortest_unique_suffix") or path)
    path_lower = path.lower()
    basename_lower = basename.lower()
    stem_lower = stem.lower()
    module_alias_lower = module_alias.lower()
    shortest_suffix_lower = shortest_unique_suffix.lower()
    path_compact = str(row.get("_path_compact") or _file_focus_compact_token(path))
    basename_compact = str(row.get("_basename_compact") or _file_focus_compact_token(basename))
    stem_compact = str(row.get("_stem_compact") or _file_focus_compact_token(stem))
    module_alias_compact = str(row.get("_module_alias_compact") or _file_focus_compact_token(module_alias))
    shortest_suffix_compact = str(row.get("_shortest_suffix_compact") or _file_focus_compact_token(shortest_unique_suffix))
    query_uses_word_spacing = _file_focus_query_uses_word_spacing(query_lower)
    if query_path_lower and query_path_lower == path_lower:
        return {
            "kind": "exact_path",
            "field": "path",
            "value": path,
            "rank_bucket": 0,
            "strength": "exact",
        }
    if query_path_lower and query_path_lower == shortest_suffix_lower:
        return {
            "kind": "shortest_unique_suffix",
            "field": "shortest_unique_suffix",
            "value": shortest_unique_suffix,
            "rank_bucket": 5,
            "strength": "exact",
        }
    if query_compact and query_compact == shortest_suffix_compact:
        return {
            "kind": "shortest_unique_suffix",
            "field": "shortest_unique_suffix",
            "value": shortest_unique_suffix,
            "rank_bucket": 5,
            "strength": "exact",
        }
    if query_lower == basename_lower:
        return {
            "kind": "basename",
            "field": "basename",
            "value": basename,
            "rank_bucket": 10,
            "strength": "exact",
        }
    if query_lower == stem_lower:
        return {
            "kind": "stem",
            "field": "stem",
            "value": stem,
            "rank_bucket": 10,
            "strength": "exact",
        }
    if module_alias_lower and query_lower == module_alias_lower:
        return {
            "kind": "module_alias",
            "field": "module_alias",
            "value": module_alias,
            "rank_bucket": 10,
            "strength": "exact",
        }
    if query_compact and query_compact == basename_compact:
        return {
            "kind": "basename",
            "field": "basename",
            "value": basename,
            "rank_bucket": 10,
            "strength": "exact",
        }
    if query_compact and query_compact == stem_compact:
        return {
            "kind": "stem",
            "field": "stem",
            "value": stem,
            "rank_bucket": 10,
            "strength": "exact",
        }
    if module_alias_compact and query_compact == module_alias_compact:
        return {
            "kind": "module_alias",
            "field": "module_alias",
            "value": module_alias,
            "rank_bucket": 10,
            "strength": "exact",
        }
    if basename_lower.startswith(query_lower):
        return {
            "kind": "basename",
            "field": "basename",
            "value": basename,
            "rank_bucket": 11,
            "strength": "prefix",
        }
    if stem_lower and stem_lower.startswith(query_lower):
        return {
            "kind": "stem",
            "field": "stem",
            "value": stem,
            "rank_bucket": 11,
            "strength": "prefix",
        }
    if module_alias_lower and module_alias_lower.startswith(query_lower):
        return {
            "kind": "module_alias",
            "field": "module_alias",
            "value": module_alias,
            "rank_bucket": 11,
            "strength": "prefix",
        }
    if query_compact and basename_compact.startswith(query_compact):
        return {
            "kind": "basename",
            "field": "basename",
            "value": basename,
            "rank_bucket": 11,
            "strength": "prefix",
        }
    if query_compact and stem_compact.startswith(query_compact):
        return {
            "kind": "stem",
            "field": "stem",
            "value": stem,
            "rank_bucket": 11,
            "strength": "prefix",
        }
    if module_alias_compact and query_compact and module_alias_compact.startswith(query_compact):
        return {
            "kind": "module_alias",
            "field": "module_alias",
            "value": module_alias,
            "rank_bucket": 11,
            "strength": "prefix",
        }
    if shortest_suffix_lower and shortest_suffix_lower.startswith(query_path_lower or query_lower):
        return {
            "kind": "shortest_unique_suffix",
            "field": "shortest_unique_suffix",
            "value": shortest_unique_suffix,
            "rank_bucket": 11,
            "strength": "prefix",
        }
    if query_compact and shortest_suffix_compact.startswith(query_compact):
        return {
            "kind": "shortest_unique_suffix",
            "field": "shortest_unique_suffix",
            "value": shortest_unique_suffix,
            "rank_bucket": 11,
            "strength": "prefix",
        }
    for component in (part for part in path_lower.split("/") if part):
        if component.startswith(query_lower):
            return {
                "kind": "path_component",
                "field": "path",
                "value": path,
                "rank_bucket": 18,
                "strength": "prefix",
            }
    if query_lower in basename_lower:
        return {
            "kind": "basename",
            "field": "basename",
            "value": basename,
            "rank_bucket": 12,
            "strength": "fragment",
        }
    if stem_lower and query_lower in stem_lower:
        return {
            "kind": "stem",
            "field": "stem",
            "value": stem,
            "rank_bucket": 12,
            "strength": "fragment",
        }
    if module_alias_lower and query_lower in module_alias_lower:
        return {
            "kind": "module_alias",
            "field": "module_alias",
            "value": module_alias,
            "rank_bucket": 12,
            "strength": "fragment",
        }
    if query_compact and query_compact in basename_compact:
        return {
            "kind": "basename",
            "field": "basename",
            "value": basename,
            "rank_bucket": 12,
            "strength": "fragment",
        }
    if query_compact and query_compact in stem_compact:
        return {
            "kind": "stem",
            "field": "stem",
            "value": stem,
            "rank_bucket": 12,
            "strength": "fragment",
        }
    if module_alias_compact and query_compact and query_compact in module_alias_compact:
        return {
            "kind": "module_alias",
            "field": "module_alias",
            "value": module_alias,
            "rank_bucket": 12,
            "strength": "fragment",
        }
    if query_lower in path_lower or (query_path_lower and query_path_lower in path_lower):
        return {
            "kind": "path_fragment",
            "field": "path",
            "value": path,
            "rank_bucket": 20,
            "strength": "fragment",
        }
    if query_compact and query_compact in path_compact:
        return {
            "kind": "path_fragment",
            "field": "path",
            "value": path,
            "rank_bucket": 20,
            "strength": "fragment",
        }

    search_index_lower = str(row.get("_search_index_lower") or "")
    search_index_compact = str(row.get("_search_index_compact") or "")
    if (
        query_lower
        and query_compact
        and query_lower not in search_index_lower
        and query_compact not in search_index_compact
    ):
        return None

    symbol_haystacks = row.get("_symbol_haystacks")
    if isinstance(symbol_haystacks, list):
        for haystack in symbol_haystacks:
            if not isinstance(haystack, Mapping):
                continue
            field = str(haystack.get("field") or "")
            haystack_text = str(haystack.get("text") or "")
            haystack_compact = str(haystack.get("compact") or _file_focus_compact_token(haystack_text))
            value = str(haystack.get("value") or "")
            if not haystack_text:
                continue
            if query_lower == haystack_text or (query_compact and query_compact == haystack_compact):
                return {
                    "kind": "symbol",
                    "field": field,
                    "value": value,
                    "symbol_id": haystack.get("symbol_id"),
                    "symbol_name": haystack.get("symbol_name"),
                    "line_start": haystack.get("line_start"),
                    "line_end": haystack.get("line_end"),
                    "rank_bucket": 13,
                    "strength": "exact",
                }
            if haystack_text.startswith(query_lower) or (
                query_compact and haystack_compact.startswith(query_compact)
            ):
                return {
                    "kind": "symbol",
                    "field": field,
                    "value": value,
                    "symbol_id": haystack.get("symbol_id"),
                    "symbol_name": haystack.get("symbol_name"),
                    "line_start": haystack.get("line_start"),
                    "line_end": haystack.get("line_end"),
                    "rank_bucket": 31,
                    "strength": "prefix",
                }
            if query_lower in haystack_text:
                return {
                    "kind": "symbol",
                    "field": field,
                    "value": value,
                    "symbol_id": haystack.get("symbol_id"),
                    "symbol_name": haystack.get("symbol_name"),
                    "line_start": haystack.get("line_start"),
                    "line_end": haystack.get("line_end"),
                    "rank_bucket": 32,
                    "strength": "fragment",
                }
    else:
        for symbol in row.get("symbols", []) or []:
            if not isinstance(symbol, Mapping):
                continue
            name = str(symbol.get("name") or "").strip()
            symbol_id = str(symbol.get("symbol_id") or "").strip()
            line_start = symbol.get("line_start")
            line_end = symbol.get("line_end")
            haystacks = [
                ("symbol_name", name.lower(), name),
                ("symbol_id", symbol_id.lower(), symbol_id),
            ]
            for field, haystack_text, value in haystacks:
                if not haystack_text:
                    continue
                haystack_compact = _file_focus_compact_token(haystack_text)
                if query_lower == haystack_text or (query_compact and query_compact == haystack_compact):
                    return {
                        "kind": "symbol",
                        "field": field,
                        "value": value,
                        "symbol_id": symbol_id or None,
                        "symbol_name": name or None,
                        "line_start": line_start,
                        "line_end": line_end,
                        "rank_bucket": 13,
                        "strength": "exact",
                    }
                if haystack_text.startswith(query_lower) or (
                    query_compact and haystack_compact.startswith(query_compact)
                ):
                    return {
                        "kind": "symbol",
                        "field": field,
                        "value": value,
                        "symbol_id": symbol_id or None,
                        "symbol_name": name or None,
                        "line_start": line_start,
                        "line_end": line_end,
                        "rank_bucket": 31,
                        "strength": "prefix",
                    }
                if query_lower in haystack_text:
                    return {
                        "kind": "symbol",
                        "field": field,
                        "value": value,
                        "symbol_id": symbol_id or None,
                        "symbol_name": name or None,
                        "line_start": line_start,
                        "line_end": line_end,
                        "rank_bucket": 32,
                        "strength": "fragment",
                    }

    if query_compact:
        token_pairs = row.get("_search_token_pairs")
        tokens_iterable = token_pairs if isinstance(token_pairs, list) else [
            {
                "text": str(token or "").lower(),
                "compact": _file_focus_compact_token(str(token or "").lower()),
                "value": token,
            }
            for token in row.get("search_tokens", []) or []
        ]
        for token in tokens_iterable:
            if not isinstance(token, Mapping):
                continue
            token_text = str(token.get("text") or "")
            token_compact = str(token.get("compact") or "")
            token_value = token.get("value")
            if not token_text and not token_compact:
                continue
            if query_lower == token_text or query_compact == token_compact:
                return {
                    "kind": "indexed_field",
                    "field": "search_tokens",
                    "value": token_value,
                    "rank_bucket": 40,
                    "strength": "exact",
                }
            if token_text.startswith(query_lower) or (
                not query_uses_word_spacing and token_compact.startswith(query_compact)
            ):
                return {
                    "kind": "indexed_field",
                    "field": "search_tokens",
                    "value": token_value,
                    "rank_bucket": 41,
                    "strength": "prefix",
                }
            if query_lower in token_text or (
                not query_uses_word_spacing and query_compact in token_compact
            ):
                return {
                    "kind": "indexed_field",
                    "field": "search_tokens",
                    "value": token_value,
                    "rank_bucket": 42,
                    "strength": "fragment",
                }

    summary = str(row.get("summary") or "").strip()
    if summary and query_lower in summary.lower():
        return {
            "kind": "indexed_field",
            "field": "summary",
            "value": summary[:160],
            "rank_bucket": 45,
            "strength": "fragment",
        }
    return None


def _file_focus_projection_context(
    *,
    file_entries: Iterable[Mapping[str, Any]],
    edges: Iterable[Mapping[str, Any]],
    focus: str | None,
    max_files: int,
    projection_absent_fallback: bool,
) -> dict[str, Any]:
    """[ACTION] Classify which catalogue rows are visible in the current CodeMap packet."""
    entries = list(file_entries)
    if projection_absent_fallback:
        return {
            "state": "projection_stale_or_absent",
            "visible_paths": set(),
            "selected_paths": set(),
            "selected_file_count": 0,
            "returned_file_count": 0,
            "omitted_file_count": 0,
        }
    if focus:
        keep_paths = {focus}
        for edge in edges:
            src = str(edge.get("from") or "").strip()
            dst = str(edge.get("to") or "").strip()
            if src == focus and dst:
                keep_paths.add(dst)
            if dst == focus and src:
                keep_paths.add(src)
        selected = [row for row in entries if str(row.get("path") or "").strip() in keep_paths]
        selected.sort(key=lambda r: (str(r.get("path") or "").strip() != focus, str(r.get("path") or "")))
    else:
        selected = entries
    max_files_int = max(1, int(max_files))
    returned = selected[:max_files_int]
    selected_paths = {str(row.get("path") or "").strip() for row in selected if str(row.get("path") or "").strip()}
    visible_paths = {str(row.get("path") or "").strip() for row in returned if str(row.get("path") or "").strip()}
    omitted = max(0, len(selected) - len(returned))
    return {
        "state": "ready",
        "visible_paths": visible_paths,
        "selected_paths": selected_paths,
        "selected_file_count": len(selected),
        "returned_file_count": len(returned),
        "omitted_file_count": omitted,
    }


def _file_focus_relationship(path: str, context: Mapping[str, Any]) -> str:
    """[ACTION] Name a match's relationship to the currently rendered CodeMap projection."""
    state = str(context.get("state") or "")
    if state == "projection_stale_or_absent":
        return "projection_stale_or_absent"
    visible_paths = context.get("visible_paths") if isinstance(context.get("visible_paths"), set) else set()
    selected_paths = context.get("selected_paths") if isinstance(context.get("selected_paths"), set) else set()
    if path in visible_paths:
        return "visible_in_packet"
    if path in selected_paths:
        return "known_but_omitted_or_truncated"
    return "known_outside_current_focus"


def _file_focus_actions(path: str, *, max_files: int) -> dict[str, Any]:
    """[ACTION] Emit API-level handoff targets that preserve canonical file identity."""
    return {
        "select_canonical_object": {"type": "file", "path": path},
        "focus_code_map": {"endpoint": "/api/code-map", "params": {"focus": path, "max_files": max_files}},
        "open_in_inspector": {"endpoint": "/api/codex/file", "params": {"path": path}},
        "open_blast_radius": {"endpoint": "/api/blast-radius", "params": {"path": path}},
    }


def _file_focus_resolution_packet(
    *,
    query: str,
    ranked: list[dict[str, Any]],
    returned: list[dict[str, Any]],
    catalogue_fingerprint: str,
) -> dict[str, Any]:
    """[ACTION] Summarize resolver state without choosing an ambiguous candidate."""
    if not query:
        state = "missing"
        reason = "empty_query"
    elif not ranked:
        state = "missing"
        reason = "no_catalogue_candidates_matched"
    else:
        exact_rows = [
            row
            for row in ranked
            if isinstance(row.get("match"), Mapping)
            and str(row["match"].get("strength") or "") == "exact"
            and str(row["match"].get("kind") or "") in {
                "exact_path",
                "shortest_unique_suffix",
                "basename",
                "stem",
                "module_alias",
            }
        ]
        if exact_rows:
            first_match = exact_rows[0].get("match")
            first_rank_bucket = exact_rows[0].get("_rank_bucket")
            peers = [
                row
                for row in exact_rows
                if row.get("_rank_bucket") == first_rank_bucket
                and isinstance(row.get("match"), Mapping)
                and row["match"].get("kind") == first_match.get("kind")  # type: ignore[union-attr]
                and row["match"].get("field") == first_match.get("field")  # type: ignore[union-attr]
            ]
            state = "exact_unique" if len(peers) == 1 else "exact_ambiguous"
            reason = "exact_candidate_unique" if len(peers) == 1 else "exact_candidate_ambiguous"
        else:
            state = "ranked_candidates"
            reason = "ranked_non_exact_candidates"

    selected = None
    if state == "exact_unique" and ranked:
        selected = ranked[0].get("candidate")
    return {
        "schema": FILE_FOCUS_RESOLUTION_SCHEMA_VERSION,
        "resolution_state": state,
        "query": query,
        "catalogue_fingerprint": catalogue_fingerprint,
        "candidate_count": len(ranked),
        "returned_candidate_count": len(returned),
        "active_object_id": selected.get("object_id") if isinstance(selected, Mapping) else None,
        "selected_object": selected if isinstance(selected, Mapping) else None,
        "requires_candidate_choice": state in {"exact_ambiguous", "ranked_candidates"},
        "reason": reason,
        "coherence": {
            "catalogue_fingerprint": catalogue_fingerprint,
            "result_identity": "candidate.object_id",
        },
    }


def _code_map_focus_node(entry: Mapping[str, Any] | None, path: str) -> dict[str, Any]:
    """[ACTION] Project one repo-relative path into the packet's lightweight focus context."""
    row = entry if isinstance(entry, Mapping) else {}
    layer = str(row.get("group_id") or row.get("layer") or "").strip() or None
    return {
        "type": "file",
        "path": path,
        "basename": posixpath.basename(path),
        "layer": layer,
        "present": bool(row),
    }


def _build_code_map_focus_context(
    *,
    file_entries: Iterable[Mapping[str, Any]],
    edges: Iterable[Mapping[str, Any]],
    focus: str | None,
) -> dict[str, Any] | None:
    """
    [ACTION]
    Emit a small backend-owned selection model for aggregate Code Map views.

    The packet still returns file rows and edges as before; this context lets UI
    renderers highlight the selected file's layer/neighborhood without inventing
    separate identity rules per Atlas / Architecture / Panorama surface.
    """
    if not focus:
        return None

    entries_by_path: dict[str, Mapping[str, Any]] = {}
    for entry in file_entries:
        path = str(entry.get("path") or "").strip()
        if path:
            entries_by_path[path] = entry

    neighbor_edges: dict[str, dict[str, Any]] = {}
    for edge in edges:
        src = str(edge.get("from") or "").strip()
        dst = str(edge.get("to") or "").strip()
        if not src or not dst or _edge_role(edge.get("kind")) not in {"dependency_context", "impact_context", "control_flow", "verification"}:
            continue
        other: str | None = None
        direction: str | None = None
        if src == focus and dst != focus:
            other = dst
            direction = "outgoing"
        elif dst == focus and src != focus:
            other = src
            direction = "incoming"
        if not other or not direction:
            continue
        row = neighbor_edges.setdefault(
            other,
            {
                "path": other,
                "directions": set(),
                "relation_kinds": set(),
                "edge_count": 0,
            },
        )
        row["directions"].add(direction)
        row["relation_kinds"].add(str(edge.get("kind") or "unknown"))
        row["edge_count"] += 1

    selected = _code_map_focus_node(entries_by_path.get(focus), focus)
    direct_neighbors: list[dict[str, Any]] = []
    role_by_path: dict[str, str] = {focus: "selected"}
    role_counts: dict[str, int] = {"selected": 1, "neighbor": 0}
    layer_counts: dict[str, dict[str, int]] = {}

    def bump_layer(layer: str | None, role: str) -> None:
        key = layer or "unknown"
        row = layer_counts.setdefault(key, {"selected": 0, "neighbor": 0})
        row[role] = row.get(role, 0) + 1

    bump_layer(selected.get("layer"), "selected")

    for path, raw in sorted(neighbor_edges.items(), key=lambda item: _repo_code_sort_key(item[0])):
        directions = set(raw.get("directions") or set())
        if directions == {"incoming", "outgoing"}:
            direction = "bidirectional"
        elif "incoming" in directions:
            direction = "incoming"
        else:
            direction = "outgoing"
        node = _code_map_focus_node(entries_by_path.get(path), path)
        direct_neighbors.append(
            {
                **node,
                "direction": direction,
                "relation_kinds": sorted(str(kind) for kind in raw.get("relation_kinds") or []),
                "edge_count": int(raw.get("edge_count") or 0),
            }
        )
        role_by_path[path] = "neighbor"
        role_counts["neighbor"] += 1
        bump_layer(node.get("layer"), "neighbor")

    layer_roles = [
        {
            "layer": layer,
            "role": "selected" if counts.get("selected", 0) else "neighbor",
            "selected_count": counts.get("selected", 0),
            "neighbor_count": counts.get("neighbor", 0),
        }
        for layer, counts in sorted(layer_counts.items())
    ]

    return {
        "schema": CODE_MAP_FOCUS_CONTEXT_SCHEMA_VERSION,
        "focus_path": focus,
        "selected_path": focus,
        "selected": selected,
        "direct_neighbors": direct_neighbors,
        "role_by_path": role_by_path,
        "role_counts": role_counts,
        "layer_roles": layer_roles,
    }


def _selection_edge_admissible(edge: Mapping[str, Any]) -> bool:
    """[ACTION] Decide which backend edge kinds can create selection emphasis."""
    return _edge_role(edge.get("kind")) in {"dependency_context", "impact_context", "control_flow", "verification"}


def _selection_confidence(values: Iterable[str]) -> str:
    """[ACTION] Collapse edge confidences into one strongest relation confidence."""
    seen = {str(value or "").strip() for value in values}
    if "high" in seen:
        return "high"
    if "medium" in seen:
        return "medium"
    return "low"


def _selection_interest(role: str, depth: int | None = None) -> float:
    """[ACTION] Score selection relevance for renderer-neutral ordering/pinning."""
    if role == "selected":
        return 1.0
    if role == "mutual":
        return 0.88
    if role == "dependency":
        return 0.8
    if role == "dependent":
        return 0.74
    if role == "blast_depth_1":
        return 0.66
    if role == "blast_depth_n":
        return max(0.28, 0.58 - (max(2, int(depth or 2)) - 2) * 0.1)
    if role == "contextual_landmark":
        return 0.35
    return 0.0


def _selection_relation_payload(
    *,
    path: str,
    role: str,
    directions: Iterable[str],
    depth: int | None,
    edge_kinds: Iterable[str],
    confidences: Iterable[str],
) -> dict[str, Any]:
    """[ACTION] Build one typed relation row for the backend selection envelope."""
    direction_set = {str(item) for item in directions if str(item)}
    if direction_set == {"incoming", "outgoing"}:
        direction = "bidirectional"
    elif "incoming" in direction_set:
        direction = "incoming"
    elif "outgoing" in direction_set:
        direction = "outgoing"
    else:
        direction = "none"
    interest = _selection_interest(role, depth)
    return {
        "path": path,
        "role": role,
        "direction": direction,
        "depth": depth,
        "edge_kinds": sorted({str(kind or "unknown") for kind in edge_kinds}),
        "confidence": _selection_confidence(confidences),
        "interest_score": round(interest, 3),
        "explanation": (
            f"{role}_via_{direction}_edge"
            if role in {"dependency", "dependent", "mutual"}
            else f"{role}_at_depth_{depth}"
            if depth is not None
            else role
        ),
    }


def _build_code_map_selection_context(
    *,
    file_entries: Iterable[Mapping[str, Any]],
    edges: Iterable[Mapping[str, Any]],
    selected_path: str | None,
    projection_scope: str,
    context_depth: int = 3,
    context_budget: int = 300,
    source_fingerprint: str | None = None,
) -> dict[str, Any] | None:
    """
    [ACTION]
    Emit the canonical selected-file envelope used by aggregate, focus, blast,
    and Inspector handoff surfaces. This is selection context, not packet scope.
    """
    selected = str(selected_path or "").strip() or None
    if not selected:
        return None

    entries_by_path: dict[str, Mapping[str, Any]] = {}
    for entry in file_entries:
        path = str(entry.get("path") or "").strip()
        if path:
            entries_by_path[path] = entry

    direct: dict[str, dict[str, Any]] = {}
    reverse: dict[str, set[str]] = {}
    for edge in edges:
        src = str(edge.get("from") or "").strip()
        dst = str(edge.get("to") or "").strip()
        if not src or not dst or not _selection_edge_admissible(edge):
            continue
        reverse.setdefault(dst, set()).add(src)
        other: str | None = None
        direction: str | None = None
        if src == selected and dst != selected:
            other = dst
            direction = "outgoing"
        elif dst == selected and src != selected:
            other = src
            direction = "incoming"
        if not other or not direction:
            continue
        row = direct.setdefault(
            other,
            {
                "directions": set(),
                "edge_kinds": set(),
                "confidences": [],
            },
        )
        row["directions"].add(direction)
        row["edge_kinds"].add(str(edge.get("kind") or "unknown"))
        row["confidences"].append(str(edge.get("confidence") or "low"))

    depth_by_path: dict[str, int] = {}
    queue: deque[tuple[str, int]] = deque([(selected, 0)])
    seen = {selected}
    max_depth = max(1, int(context_depth or 1))
    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for dependent in sorted(reverse.get(current, set()), key=_repo_code_sort_key):
            if dependent == selected:
                continue
            next_depth = depth + 1
            if dependent not in depth_by_path or next_depth < depth_by_path[dependent]:
                depth_by_path[dependent] = next_depth
            if dependent not in seen:
                seen.add(dependent)
                queue.append((dependent, next_depth))

    relations: list[dict[str, Any]] = []
    for path, raw in direct.items():
        directions = set(raw.get("directions") or set())
        if directions == {"incoming", "outgoing"}:
            role = "mutual"
        elif "outgoing" in directions:
            role = "dependency"
        else:
            role = "dependent"
        relations.append(
            _selection_relation_payload(
                path=path,
                role=role,
                directions=directions,
                depth=1 if "incoming" in directions else None,
                edge_kinds=raw.get("edge_kinds") or [],
                confidences=raw.get("confidences") or [],
            )
        )

    for path, depth in depth_by_path.items():
        if path in direct:
            continue
        role = "blast_depth_1" if depth == 1 else "blast_depth_n"
        relations.append(
            _selection_relation_payload(
                path=path,
                role=role,
                directions=["incoming"],
                depth=depth,
                edge_kinds=[],
                confidences=[],
            )
        )

    relations.sort(key=lambda row: (-float(row.get("interest_score") or 0), _repo_code_sort_key(str(row.get("path") or ""))))
    relation_cap = max(1, min(512, int(context_budget or 300)))
    omitted_relations = max(0, len(relations) - relation_cap)
    returned_relations = relations[:relation_cap]

    selected_node = _code_map_focus_node(entries_by_path.get(selected), selected)
    role_by_path: dict[str, str] = {selected: "selected"}
    interest_by_path: dict[str, float] = {selected: 1.0}
    role_counts: dict[str, int] = {"selected": 1}
    for relation in returned_relations:
        path = str(relation.get("path") or "")
        role = str(relation.get("role") or "background")
        if path and path not in role_by_path:
            role_by_path[path] = role
            interest_by_path[path] = float(relation.get("interest_score") or 0.0)
            role_counts[role] = role_counts.get(role, 0) + 1

    aggregate_memberships: list[dict[str, Any]] = []
    for path in [selected, *[str(row.get("path") or "") for row in returned_relations]]:
        entry = entries_by_path.get(path)
        if not isinstance(entry, Mapping):
            continue
        aggregate_memberships.append(
            {
                "path": path,
                "layer": str(entry.get("group_id") or entry.get("layer") or "").strip() or None,
                "basename": posixpath.basename(path),
                "role": role_by_path.get(path, "background"),
            }
        )

    return {
        "schema": CODE_MAP_SELECTION_CONTEXT_SCHEMA_VERSION,
        "snapshot_id": source_fingerprint,
        "catalogue_fingerprint": source_fingerprint,
        "projection_scope": projection_scope,
        "selected_path": selected,
        "selected_object": selected_node,
        "relations": returned_relations,
        "interest_by_path": interest_by_path,
        "role_by_path": role_by_path,
        "role_counts": role_counts,
        "aggregate_memberships": aggregate_memberships,
        "omission_receipt": {
            "omitted_relations": omitted_relations,
            "forced_inclusions": [selected],
            "reason": "selection_context_relation_cap" if omitted_relations else None,
        },
        "coherence": {
            "source_fingerprint": source_fingerprint,
            "edge_admissibility_owner": "system.lib.code_architecture_projection",
            "selection_identity": "repo_relative_path",
        },
    }


def _rank_file_focus_catalogue_rows(
    *,
    catalogue_rows: list[dict[str, Any]],
    projection_context: Mapping[str, Any],
    fingerprint: str,
    normalized_query: str,
    query_lower: str,
    query_path_lower: str,
    query_compact: str,
    max_files: int,
) -> list[dict[str, Any]]:
    """[ACTION] Rank normalized locator/catalogue rows for one file-focus query."""
    duplicate_basename_counts: dict[str, int] = {}
    for row in catalogue_rows:
        basename = str(row.get("basename") or "")
        duplicate_basename_counts[basename] = duplicate_basename_counts.get(basename, 0) + 1

    ranked: list[dict[str, Any]] = []
    for row in catalogue_rows:
        match = _file_focus_match_for_row(
            row,
            query=normalized_query,
            query_lower=query_lower,
            query_path_lower=query_path_lower,
            query_compact=query_compact,
        )
        if match is None:
            continue
        path = str(row.get("path") or "")
        relationship = _file_focus_relationship(path, projection_context)
        duplicate_count = duplicate_basename_counts.get(str(row.get("basename") or ""), 0)
        rank_bucket = int(match.pop("rank_bucket"))
        candidate = _file_focus_catalogue_identity(row)
        architecture_location = _architecture_location_from_row(row)
        candidate.update(
            {
                "match_explanation": _file_focus_match_explanation(match),
                "score_components": {
                    "rank_bucket": rank_bucket,
                    "strength": match.get("strength"),
                    "field": match.get("field"),
                    "kind": match.get("kind"),
                },
                "catalogue_fingerprint": fingerprint,
            }
        )
        ranked.append(
            {
                "schema": FILE_FOCUS_SEARCH_RESULT_SCHEMA_VERSION,
                "path": path,
                "basename": row.get("basename"),
                "candidate": candidate,
                "canonical_object": {
                    "type": "file",
                    "id": path,
                    "object_id": candidate.get("object_id"),
                    "path": path,
                    "identity_kind": "repo_relative_path",
                    "catalogue_fingerprint": fingerprint,
                },
                "layer": row.get("layer"),
                "summary": row.get("summary"),
                "architecture_location": architecture_location,
                "aggregate_context": _file_focus_aggregate_context(row),
                "match": match,
                "match_explanation": candidate.get("match_explanation"),
                "score_components": candidate.get("score_components"),
                "projection_relationship": relationship,
                "availability": {
                    "visible_in_packet": relationship == "visible_in_packet",
                    "requires_focus_load": relationship in {
                        "known_outside_current_focus",
                        "known_but_omitted_or_truncated",
                        "projection_stale_or_absent",
                    },
                    "reason": relationship,
                },
                "disambiguator": {
                    "duplicate_basename_count": duplicate_count,
                    "label": path if duplicate_count > 1 else str(row.get("basename") or path),
                },
                "actions": _file_focus_actions(path, max_files=max_files),
                "_rank_sort": (rank_bucket, _repo_code_sort_key(path), path),
                "_rank_bucket": rank_bucket,
            }
        )

    ranked.sort(key=lambda row: row["_rank_sort"])
    return ranked


def _file_focus_enrichment_needed(
    ranked: list[dict[str, Any]],
    *,
    normalized_query: str,
    query_compact: str,
) -> bool:
    """[ACTION] Decide when the compact locator needs symbol-catalogue arbitration."""
    if not normalized_query or len(query_compact or "") < 4:
        return False
    if _file_focus_query_uses_word_spacing(normalized_query):
        return False
    if not ranked:
        return True
    best = ranked[0]
    best_bucket = int(best.get("_rank_bucket") or 999)
    best_match = best.get("match") if isinstance(best.get("match"), Mapping) else {}
    if str(best_match.get("kind") or "") == "symbol" and str(best_match.get("strength") or "") == "exact":
        return False
    return best_bucket >= 18


def _merge_file_focus_ranked_results(
    primary: list[dict[str, Any]],
    enrichment: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """[ACTION] Merge locator and enrichment candidates, keeping the strongest rank per canonical path."""
    by_path: dict[str, dict[str, Any]] = {}
    for row in [*primary, *enrichment]:
        path = str(row.get("path") or "")
        if not path:
            continue
        existing = by_path.get(path)
        if existing is None or tuple(row.get("_rank_sort") or ()) < tuple(existing.get("_rank_sort") or ()):
            by_path[path] = row
    merged = list(by_path.values())
    merged.sort(key=lambda row: row["_rank_sort"])
    return merged


def build_file_focus_search_packet(
    *,
    root: Path,
    query: str,
    focus_path: str | None = None,
    max_files: int = 300,
    max_results: int = 50,
    refresh_locator_generation: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Resolve a CodeMap find query to canonical file objects once, then project the same object identity into CodeMap focus, Inspector open, and blast-radius handoff actions.
    - Mechanism: Search the broad generated file/object catalogue, rank deterministic path/basename matches before symbols and indexed fields, and classify each match against the current CodeMap packet instead of pretending hidden/truncated files are absent.
    - Reads: Same generated projection sidecars as `build_code_map_packet` plus the bounded live Python repo inventory included in the catalogue fingerprint.
    - Guarantee: Returns no raw source body; canonical identity is the repo-relative file path.
    """
    generated_at = _now_iso()
    raw_normalized_query = _file_focus_normalize_query(query)
    normalized_query = _canonical_private_code_path(raw_normalized_query) or raw_normalized_query
    query_lower = normalized_query.lower()
    query_path_lower = normalized_query.lstrip("/").lower()
    query_compact = _file_focus_compact_token(normalized_query)
    raw_focus = str(focus_path or "").strip() or None
    focus = _canonical_private_code_path(raw_focus) if raw_focus else None
    focus = focus or raw_focus
    max_files_int = max(1, int(max_files))
    max_results_int = max(1, int(max_results))

    catalogue_bundle = (
        refresh_file_focus_locator_generation(root, focus=focus, force=False)
        if refresh_locator_generation
        else _file_focus_locator_bundle(root, focus=focus)
    )
    model = catalogue_bundle.get("model") if isinstance(catalogue_bundle.get("model"), Mapping) else {}
    catalogue_rows = catalogue_bundle.get("catalogue_rows")
    catalogue_rows = catalogue_rows if isinstance(catalogue_rows, list) else []
    projection_context = _file_focus_projection_context(
        file_entries=model.get("projection_file_entries", model.get("file_entries", [])) or [],
        edges=model.get("projection_edges", model.get("edges", [])) or [],
        focus=focus,
        max_files=max_files_int,
        projection_absent_fallback=bool(model.get("projection_absent_fallback")),
    )
    fingerprint = str(catalogue_bundle.get("fingerprint") or "")
    catalogue_kind = str(catalogue_bundle.get("catalogue_kind") or "architecture_locator")
    locator_generation = (
        catalogue_bundle.get("generation")
        if isinstance(catalogue_bundle.get("generation"), Mapping)
        else None
    )

    ranked = _rank_file_focus_catalogue_rows(
        catalogue_rows=catalogue_rows,
        projection_context=projection_context,
        fingerprint=fingerprint,
        normalized_query=normalized_query,
        query_lower=query_lower,
        query_path_lower=query_path_lower,
        query_compact=query_compact,
        max_files=max_files_int,
    )

    had_locator_hits = bool(ranked)
    if _file_focus_enrichment_needed(
        ranked,
        normalized_query=normalized_query,
        query_compact=query_compact,
    ):
        enrichment_bundle = _file_focus_catalogue_bundle(root, focus=focus, fingerprint=fingerprint)
        enrichment_model = (
            enrichment_bundle.get("model")
            if isinstance(enrichment_bundle.get("model"), Mapping)
            else {}
        )
        enrichment_rows = enrichment_bundle.get("catalogue_rows")
        enrichment_rows = enrichment_rows if isinstance(enrichment_rows, list) else []
        enrichment_context = _file_focus_projection_context(
            file_entries=enrichment_model.get(
                "projection_file_entries",
                enrichment_model.get("file_entries", []),
            )
            or [],
            edges=enrichment_model.get("projection_edges", enrichment_model.get("edges", [])) or [],
            focus=focus,
            max_files=max_files_int,
            projection_absent_fallback=bool(enrichment_model.get("projection_absent_fallback")),
        )
        enrichment_ranked = _rank_file_focus_catalogue_rows(
            catalogue_rows=enrichment_rows,
            projection_context=enrichment_context,
            fingerprint=fingerprint,
            normalized_query=normalized_query,
            query_lower=query_lower,
            query_path_lower=query_path_lower,
            query_compact=query_compact,
            max_files=max_files_int,
        )
        if enrichment_ranked:
            ranked = _merge_file_focus_ranked_results(ranked, enrichment_ranked)
            model = enrichment_model
            catalogue_rows = enrichment_rows
            projection_context = enrichment_context
            catalogue_kind = "architecture_locator_plus_symbol_enrichment" if had_locator_hits else "symbol_catalogue_fallback"

    results = ranked[:max_results_int]
    resolution = _file_focus_resolution_packet(
        query=normalized_query,
        ranked=ranked,
        returned=results,
        catalogue_fingerprint=fingerprint,
    )
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
        row.pop("_rank_sort", None)
        row.pop("_rank_bucket", None)
    omitted_results = max(0, len(ranked) - len(results))
    relationship_counts: dict[str, int] = {}
    for row in ranked:
        rel = str(row.get("projection_relationship") or "unknown")
        relationship_counts[rel] = relationship_counts.get(rel, 0) + 1

    reason_parts: list[str] = []
    if model.get("catalogue_reason"):
        reason_parts.append(str(model.get("catalogue_reason")))
    if omitted_results:
        reason_parts.append("truncated_to_max_results")
    receipt_reason = "; ".join(reason_parts) if reason_parts else None
    symbol_record_count = sum(len(row.get("symbols", []) or []) for row in catalogue_rows)

    return {
        "kind": "kernel.file_focus_search",
        "schema_version": FILE_FOCUS_SEARCH_SCHEMA_VERSION,
        "generated_at": generated_at,
        "query": {
            "raw": query,
            "normalized": normalized_query,
            "canonicalized_from": raw_normalized_query if raw_normalized_query != normalized_query else None,
            "empty": not bool(normalized_query),
        },
        "focus_path": focus,
        "max_files": max_files_int,
        "max_results": max_results_int,
        "resolution": resolution,
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
            "locator_generation": (
                {
                    key: value
                    for key, value in locator_generation.items()
                    if key != "generated_monotonic"
                }
                if isinstance(locator_generation, Mapping)
                else None
            ),
        },
        "catalogue": {
            "file_count": len(catalogue_rows),
            "symbol_record_count": symbol_record_count,
            "source_strategy": model.get("source_strategy"),
            "lookup_mode": catalogue_kind,
            "generation": (
                {
                    key: value
                    for key, value in locator_generation.items()
                    if key != "generated_monotonic"
                }
                if isinstance(locator_generation, Mapping)
                else None
            ),
            "status": (
                "projection_stale_or_absent"
                if model.get("projection_absent_fallback")
                else "ready"
                if catalogue_rows
                else "unavailable"
            ),
            "searchable_fields": ["path", "basename", "symbol", "search_tokens", "summary"],
        },
        "projection_context": {
            "state": projection_context.get("state"),
            "focus_path": focus,
            "selected_file_count": projection_context.get("selected_file_count"),
            "returned_file_count": projection_context.get("returned_file_count"),
            "omitted_file_count": projection_context.get("omitted_file_count"),
            "relationship_counts": relationship_counts,
        },
        "stats": {
            "total_result_count": len(ranked),
            "returned_result_count": len(results),
            "omitted_result_count": omitted_results,
        },
        "results": results,
        "omission_receipt": build_omission_receipt(
            omitted_files=omitted_results,
            omitted_edges=0,
            omitted_overlays=0,
            reason=receipt_reason,
        ),
        "known_limits": [
            *KNOWN_LIMITS,
            "file-focus search covers generated catalogue fields, not raw source text",
            "Inspector Ctrl-F remains text search within the currently opened file",
        ],
    }


def build_code_map_packet(
    *,
    root: Path,
    focus_path: str | None = None,
    selection_path: str | None = None,
    projection_scope: str | None = None,
    max_files: int = 300,
    include_overlays: bool = True,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Emit one `code_map_packet_v1` covering the repo's code-architecture projection — file rows, edges, stats, overlays — sourced only from existing substrate, never re-running any parser.
    - Mechanism: Load hologram + overlay sources, normalize edges, compute fan-in/fan-out, build per-file rows, attach overlays (when `include_overlays`), apply `focus_path` filter only for neighborhood scope, preserve `selection_path` as renderer context, truncate to `max_files` with an honest omission_receipt.
    - Reads: hologram (`graph.json`, `quality.json`, `symbols.json`), `_index.json`, `annex_distillation_index.json`, `navigation_graph.json` — all best-effort.
    - Guarantee: Returns a dict matching the schema sketched in `codex/doctrine/paper_modules/codeflow_assimilation.md::Packet contract sketch`.
    - Fails: Never raises on absent sources; missing substrate degrades the packet via `omission_receipt`.
    """
    build_started_at = time.perf_counter()
    stage_started_at = build_started_at
    stage_timings_ms: dict[str, float] = {}

    def mark_stage(stage_id: str) -> None:
        nonlocal stage_started_at
        now = time.perf_counter()
        stage_timings_ms[stage_id] = round((now - stage_started_at) * 1000.0, 3)
        stage_started_at = now

    sources = load_hologram_sources(root)
    paper_modules_index = load_paper_module_index(root)
    route_coverage = load_route_coverage(root)
    annex_distillation = load_annex_distillation_index(root)
    navigation_graph = load_frontend_navigation_graph(root)
    mark_stage("source_load")

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
    raw_focus = str(focus_path or "").strip() or None
    focus = _canonical_private_code_path(raw_focus) if raw_focus else None
    focus = focus or raw_focus
    raw_selected = str(selection_path or focus or "").strip() or None
    selected = _canonical_private_code_path(raw_selected) if raw_selected else None
    selected = selected or raw_selected
    effective_projection_scope = str(projection_scope or "").strip() or ("neighborhood" if focus else "overview")
    if effective_projection_scope not in {"overview", "neighborhood", "blast"}:
        effective_projection_scope = "overview"
    ui_file_entries = _ui_index_file_entries(sources.get("ui_index"))
    ui_edges = _ui_index_import_edges(sources.get("ui_index"))
    scope_file_entries = _scope_index_file_entries(sources.get("scope_index"))
    scope_file_semantics = _scope_index_file_semantics(sources.get("scope_index"))
    scope_edges = _scope_index_connection_edges(sources.get("scope_index"))
    repo_file_entries: list[dict[str, Any]] = []
    code_map_live_file_entries = _repo_python_code_map_live_file_entries(root)
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
        # walk/parse the unbounded live repo here; this endpoint is an
        # interactive backend-for-frontend read model, so generated projection
        # sidecars remain the latency boundary. The bounded Plectis source slice
        # is admitted below because recipient packets link those repo files
        # directly while the generated private scope index does not cover them.
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
    if code_map_live_file_entries and not repo_python_fallback:
        live_paths = {
            str(row.get("path") or "").strip()
            for row in code_map_live_file_entries
            if str(row.get("path") or "").strip()
        }
        live_parse_paths = set(
            sorted(live_paths, key=_repo_code_sort_key)[:PLECTIS_CODE_MAP_IMPORT_PARSE_CAP]
        )
        for pinned in (focus, selected):
            if pinned and pinned in live_paths:
                live_parse_paths.add(pinned)
        live_parse_capped = len(live_paths) > len(live_parse_paths)
        live_edges, live_symbol_counts = _repo_python_import_edges_and_symbols(
            root,
            code_map_live_file_entries,
            parse_paths=live_parse_paths,
        ) if live_parse_paths else ([], {})
        repo_python_merged = True
        repo_python_import_merged = bool(live_edges) or repo_python_import_merged
        repo_python_import_parse_capped = repo_python_import_parse_capped or live_parse_capped
        file_entries = _merge_file_entries(file_entries, code_map_live_file_entries)
        symbol_counts = {
            **live_symbol_counts,
            **symbol_counts,
        }
        edges = _merge_connections(edges, live_edges)
    mark_stage("source_merge")
    edges_outbound_count: dict[str, int] = {}
    edges_inbound_count: dict[str, int] = {}
    for edge in edges:
        edges_outbound_count[edge["from"]] = edges_outbound_count.get(edge["from"], 0) + 1
        edges_inbound_count[edge["to"]] = edges_inbound_count.get(edge["to"], 0) + 1
    fingerprint = _combine_code_map_source_fingerprint(
        root,
        CODE_MAP_SOURCE_PATHS,
        code_map_live_file_entries,
    )
    focus_context = _build_code_map_focus_context(
        file_entries=file_entries,
        edges=edges,
        focus=selected,
    )
    selection_context = _build_code_map_selection_context(
        file_entries=file_entries,
        edges=edges,
        selected_path=selected,
        projection_scope=effective_projection_scope,
        context_depth=3,
        context_budget=max_files,
        source_fingerprint=fingerprint,
    )
    mark_stage("context_selection")

    if focus and effective_projection_scope in {"neighborhood", "blast"}:
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
        if selected and selection_context:
            interest_by_path = selection_context.get("interest_by_path")
            interest_by_path = interest_by_path if isinstance(interest_by_path, Mapping) else {}
            original_index = {
                str(row.get("path") or "").strip(): index
                for index, row in enumerate(focused_files)
                if str(row.get("path") or "").strip()
            }
            focused_files.sort(
                key=lambda row: (
                    0 if str(row.get("path") or "").strip() in interest_by_path else 1,
                    -float(interest_by_path.get(str(row.get("path") or "").strip()) or 0),
                    original_index.get(str(row.get("path") or "").strip(), 0),
                    str(row.get("path") or ""),
                )
            )

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
    mark_stage("scope_filter")

    if include_overlays:
        paper_module_overlay = build_paper_module_overlay_index(root, paper_modules_index)
        annex_pattern_overlay = build_annex_pattern_overlay_index(annex_distillation)
        frontend_view_overlay = build_frontend_view_overlay_index(navigation_graph)
    else:
        paper_module_overlay = {}
        annex_pattern_overlay = {}
        frontend_view_overlay = {}
    mark_stage("overlay_index")

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
        _attach_file_semantics(
            row,
            file_entry=entry,
            scope_file_semantics=scope_file_semantics,
        )
        file_rows.append(row)
    mark_stage("file_rows")

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

    paper_module_count = 0
    if isinstance(paper_modules_index, Mapping):
        modules = paper_modules_index.get("modules")
        if isinstance(modules, list):
            paper_module_count = len(modules)
    annex_pattern_count = 0
    if isinstance(annex_distillation, Mapping):
        annex_pattern_count = int(annex_distillation.get("pattern_count") or 0)
    route_target_count = _route_target_count(route_coverage)

    _attach_file_presentation(file_rows, focus=selected)
    _attach_connection_presentation(returned_edges)
    mark_stage("presentation")
    composition_stats = _packet_composition_stats(file_rows, returned_edges)
    generated_at = _now_iso()
    graph_presentation = _build_graph_presentation_summary(file_rows, returned_edges)
    edge_semantics = _build_edge_semantics_summary(returned_edges)
    cluster_semantics = _build_cluster_semantics_summary(file_rows, returned_edges)
    camera_target = _build_camera_target(file_rows, focus=selected)
    mark_stage("semantic_contracts")
    semantic_scene = _build_code_map_semantic_scene(
        file_rows=file_rows,
        cluster_semantics=cluster_semantics,
        focus_context=focus_context,
        selection_context=selection_context,
        selected_path=selected,
        projection_scope=effective_projection_scope,
    )
    mark_stage("semantic_scene")
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
            else "bounded_plectis_public_slice"
            if code_map_live_file_entries and repo_python_merged
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
    projection_state["selected_path"] = selected
    projection_state["projection_scope"] = effective_projection_scope
    graph_scene_payload = _build_code_map_graph_scene_payload(
        generated_at=generated_at,
        source_fingerprint=fingerprint,
        focus=focus,
        file_rows=file_rows,
        returned_edges=returned_edges,
        cluster_semantics=cluster_semantics,
        camera_target=camera_target,
    )
    mark_stage("graph_scene")
    build_timings = {
        "schema": CODE_MAP_BUILD_TIMINGS_SCHEMA_VERSION,
        "status": "measured",
        "total_ms": round((time.perf_counter() - build_started_at) * 1000.0, 3),
        "stage_timings_ms": stage_timings_ms,
        "counts": {
            "source_files": len(file_entries),
            "selected_files": len(focused_files),
            "returned_files": len(file_rows),
            "source_edges": len(edges),
            "selected_edges": len(focused_edges),
            "returned_edges": len(returned_edges),
            "semantic_scene_sections": sum(
                len(scene.get("drawer_sections") or [])
                for scene in (
                    semantic_scene.get("selection_scene") if isinstance(semantic_scene.get("selection_scene"), Mapping) else {},
                    semantic_scene.get("focus_scene") if isinstance(semantic_scene.get("focus_scene"), Mapping) else {},
                    semantic_scene.get("blast_scene") if isinstance(semantic_scene.get("blast_scene"), Mapping) else {},
                )
                if isinstance(scene, Mapping)
            ),
        },
    }

    return {
        "kind": "kernel.code_map",
        "schema_version": CODE_MAP_SCHEMA_VERSION,
        "render_contract_version": CODE_MAP_RENDER_CONTRACT_VERSION,
        "generated_at": generated_at,
        "build_timings": build_timings,
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
        "edge_semantics": edge_semantics,
        "cluster_semantics": cluster_semantics,
        "semantic_scene": semantic_scene,
        "camera_target": camera_target,
        "focus_path": focus,
        "selected_path": selected,
        "projection_scope": effective_projection_scope,
        "focus_context": focus_context,
        "selection_context": selection_context,
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
