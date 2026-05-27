"""
[PURPOSE]
- Teleology: Project the repo's holographic world model into a small set of typed
  HTTP-friendly snapshots so the Zenith browser can act as a third honest entrypoint
  into the same authority graph the kernel and bridge already use.
- Mechanism: Read-only loader that consolidates orchestration_state, doctrine_runtime,
  system_map, agent_bootstrap_live, the active phase family, and raw-seed principles
  into a `WorldModelSnapshot` plus per-id resolvers for principles, concepts,
  mechanisms, and raw-seed paragraphs.

[INTERFACE]
- Inputs: Repository root path. No mutation, no external services.
- Outputs: dict payloads ready to be returned by FastAPI endpoints.
- Reads: tools/meta/control/orchestration_state.json,
  tools/meta/control/documentation_route_focus.json,
  codex/doctrine/system_map.json,
  codex/doctrine/doctrine_runtime.json,
  codex/doctrine/agent_bootstrap_live.json,
  codex/doctrine/concepts/*.json,
  codex/doctrine/mechanisms/*.json,
  obsidian/.../raw_seed/raw_seed_principles.json,
  obsidian/.../raw_seed/raw_seed_index.json,
  the active phase family pipeline_state.json / focus_directive.json /
  system_view.json / phase_scaffold.json / synth_seed.json.

[FLOW]
1. `load_world_model_snapshot` collects the small high-coverage projection used by
   the cockpit shell. It must stay cheap (no system_view.json file scan, no shard
   walks) so the launchpad can refresh it on every visit.
2. `resolve_principle`, `resolve_concept`, `resolve_mechanism`, `resolve_raw_seed_anchor`
   deliver fully hydrated single records on drill-down.
3. `compute_freshness` decides red/amber/green age strings against now() for any
   `*_at` ISO timestamps the cockpit needs to surface.

[CONSTRAINTS]
- Atomicity: Read-only. No JSON is rewritten.
- Forbid: Anything that isn't already a stable artifact in the repo. We never
  invent state — we project it.
- Failure: A missing file becomes `None` in the payload, never an exception that
  fails the whole snapshot. The cockpit knows how to render absent slices.
- Non-goal: Executing kernel commands. This module is a JSON view layer over disk.
- When-needed: Open when the server backend needs read-only projections of orchestration, phase, doctrine, topology, or authority-chain artifacts without tracing those JSON files and API routes by hand.
- Escalates-to: system/server/main.py; system/server/schemas.py; system/server/translator.py
- Navigation-group: server_backend
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from system.lib.swr_cache import swr_get, swr_peek, swr_prewarm
from system.lib.raw_seed_atomization import (
    load_raw_seed_pipeline_snapshot,
)
from system.lib import shard_browser
from system.lib.shard_browser import discover_shard_surfaces, load_shards
from system.lib.chain_runtime import latest_chain_run_summary, latest_queue_run_summary
from system.lib.autonomy_diagnostics import load_autonomy_diagnostics
from system.lib.launchable_operations import (
    artifact_refs_from_operation_output as _shared_artifact_refs_from_operation_output,
    finalize_meta_mission_run as _shared_finalize_meta_mission_run,
    launcher_meta_mission_env as _shared_launcher_meta_mission_env,
    list_launchable_operations as _shared_list_launchable_operations,
    operation_event_fields_from_operation_output as _shared_operation_event_fields_from_operation_output,
    prepare_launch_operation as _shared_prepare_launch_operation,
    start_meta_mission_run as _shared_start_meta_mission_run,
)
from system.lib.lab_oracle_evolve_overnight import (
    default_overnight_paths as _lab_oracle_evolve_overnight_paths,
    load_overnight_status as _load_lab_oracle_evolve_overnight_status,
)
from system.lib import metabolism_market_clock as _market_clock
from system.lib import provider_metabolism_signal as _provider_metabolism_signal
from system.lib import metabolism_scheduler as _metabolism_scheduler
from system.lib import metabolism_store as _metabolism_store
from system.lib.market_feed_run_evidence import (
    build_market_feed_run_evidence_card as _build_market_feed_run_evidence_card,
)
from system.lib.quant_presentation_mart import (
    load_latest_quant_presentation_mart as _load_latest_quant_presentation_mart,
)
from system.lib.market_dashboard_read_model import (
    fingerprint_market_situation_graph as _fingerprint_market_situation_graph,
    load_latest_market_dashboard_read_model as _load_latest_market_dashboard_read_model,
)
from system.lib.market_display_bundle import (
    load_latest_ready_market_display_bundle as _load_latest_ready_market_display_bundle,
)
from system.lib.market_situation_graph import (
    load_latest_market_situation_graph as _load_latest_market_situation_graph,
)
from system.lib.dispatch_policy import resolve_dispatch_policy, summarize_dispatch_policy
from system.lib import approval_registry
from system.lib import frontend_surface_contracts
from system.lib import meta_mission_workspace as _mmw
from system.lib.code_architecture_projection import (
    build_blast_radius_packet,
    build_code_map_packet,
)
from system.lib.system_atlas_projection import build_system_atlas_packet
from system.lib import semantic_routing
from system.lib import agent_seed_handoffs as agent_seed_handoff_lib
from system.lib import work_ledger as work_ledger_lib
from system.lib import work_ledger_runtime
from system.lib.observe_mission_templates import load_mission_template
from system.lib.paper_modules import load_paper_module_runtime
from system.lib.doctrine_graph import (
    DOCTRINE_GRAPH_REL,
    DOCTRINE_SECTION_UNITS_REL,
    query_doctrine_graph,
)
from tools.meta.control import reactions_engine as reactions_runtime

logger = logging.getLogger("server.world_model")

_READONLY_SNAPSHOT_CACHE_TTL_S = 10.0
_OPERATIONS_LENS_CACHE_TTL_S = 45.0
_OPERATIONS_LENS_COLD_WAIT_S = 0.75
_OPERATIONS_LENS_SLOW_SOURCE_MS = 750.0
_OPERATIONS_LENS_CACHE_REL = "state/world_model/operations_lens_snapshot.json"
_OPERATIONS_LENS_MEMORY_CACHE: dict[str, tuple[float, Dict[str, Any]]] = {}
_OPERATIONS_LENS_CACHE_LOCK = Lock()
_OPERATIONS_LENS_REFRESH_IN_FLIGHT: dict[str, Event] = {}
_ATTENTION_SNAPSHOT_CACHE: dict[str, tuple[float, Dict[str, Any]]] = {}
_ATTENTION_SNAPSHOT_CACHE_LOCK = Lock()
_REACTIONS_SNAPSHOT_CACHE: dict[str, tuple[float, Dict[str, Any]]] = {}
_REACTIONS_SNAPSHOT_CACHE_LOCK = Lock()
_RECONCILIATION_SNAPSHOT_CACHE: dict[str, tuple[float, Dict[str, Any]]] = {}
_RECONCILIATION_SNAPSHOT_CACHE_LOCK = Lock()
_RECONCILIATION_STALE_THRESHOLD_SECONDS = 900
_HOST_AGENT_EXTERNAL_CACHE_TTL_S = 30.0
_HOST_AGENT_EXTERNAL_CACHE: dict[str, tuple[float, Dict[str, Any]]] = {}
_HOST_AGENT_EXTERNAL_CACHE_LOCK = Lock()
_HOST_AGENT_DOTFILES_CACHE_TTL_S = 30.0
_HOST_AGENT_DOTFILES_CACHE: dict[str, tuple[float, Dict[str, Any]]] = {}
_HOST_AGENT_DOTFILES_CACHE_LOCK = Lock()
_OPERATIONS_CATALOG_CACHE_TTL_S = 15.0
_OPERATIONS_CATALOG_CACHE: dict[str, tuple[float, Dict[str, Any]]] = {}
_OPERATIONS_CATALOG_CACHE_LOCK = Lock()
_DEFAULT_OVERNIGHT_QUEUE_MANIFEST_REL = (
    "codex/standards/observe/mission_templates/autonomy_runtimes/nightly_default.json"
)
_LAB_ORACLE_EVOLVE_OPERATION_IDS = {
    "evolve_input_check",
    "oracle_quartet_plan",
    "oracle_quartet_run_missing",
    "evolve_bridge_dry_run",
    "lab_oracle_evolve_overnight_plan",
}
_LAB_ORACLE_EVOLVE_HISTORY_EVENT_LIMIT = 200
_LAB_ORACLE_EVOLVE_HISTORY_PAIR_LIMIT = 5
_OPERATION_LOG_TAIL_BYTES = 32768
_MARKET_FEED_TARGET_LABELS = {
    "global_stock_feed": "STOCK",
    "global_etf_feed": "ETF",
    "global_macro_feed": "MACRO",
    "global_news_feed": "NEWS",
    "global_polymarket_feed": "POLYMARKET",
    "global_stockgrid_feed": "STOCKGRID",
    "global_calculator_feed": "CALCULATOR",
}
_MARKET_FEED_SPECIMEN_ROW_LIMIT = 4
_MARKET_FEED_SPECIMEN_COLUMN_LIMIT = 9
_MARKET_FEED_TABLE_LIMIT = 8
_MARKET_FEED_METRIC_COLUMNS = {
    "Price",
    "Vol_20d",
    "Chg_5d",
    "Chg_63d",
    "Z_Short",
    "Z_Long",
    "pct_change",
    "z_score",
    "risk_d2",
    "p",
    "c",
    "v",
    "s",
    "last",
    "z",
}


def _snapshot_cache_key(repo_root: Path) -> str:
    return str(repo_root.resolve())


def _cached_mapping(
    *,
    cache: dict[str, tuple[float, Dict[str, Any]]],
    lock: Lock,
    repo_root: Path,
    loader: "callable[[], Dict[str, Any]]",
    ttl_s: float = _READONLY_SNAPSHOT_CACHE_TTL_S,
) -> Dict[str, Any]:
    # Upgraded to stale-while-revalidate: a cache hit that's past its TTL still
    # returns instantly and schedules a background refresh, so polling UIs never
    # pay the cold rebuild cost twice. The first hit in a cold process still
    # blocks, but prewarm_hot_caches() at startup absorbs that too.
    cache_key = _snapshot_cache_key(repo_root)
    now = time.monotonic()
    with lock:
        cached = cache.get(cache_key)
        if cached is not None:
            fresh = now - cached[0] <= ttl_s
            payload_copy = copy.deepcopy(cached[1])
            if fresh:
                return payload_copy
            if cache_key not in _LEGACY_REFRESH_IN_FLIGHT:
                _LEGACY_REFRESH_IN_FLIGHT[cache_key] = True
                import threading as _threading
                _threading.Thread(
                    target=_legacy_background_refresh,
                    args=(cache, lock, cache_key, loader),
                    name="cached-mapping-refresh",
                    daemon=True,
                ).start()
            return payload_copy
    payload = loader()
    with lock:
        cache[cache_key] = (time.monotonic(), copy.deepcopy(payload))
    return payload


_LEGACY_REFRESH_IN_FLIGHT: dict[str, bool] = {}


def _legacy_background_refresh(
    cache: dict[str, tuple[float, Dict[str, Any]]],
    lock: Lock,
    cache_key: str,
    loader: "callable[[], Dict[str, Any]]",
) -> None:
    try:
        payload = loader()
        with lock:
            cache[cache_key] = (time.monotonic(), copy.deepcopy(payload))
    except Exception as exc:
        logger.warning("cached-mapping background refresh failed for %s: %s", cache_key, exc)
    finally:
        _LEGACY_REFRESH_IN_FLIGHT.pop(cache_key, None)

# Stable disk paths the cockpit projects from.
ORCHESTRATION_STATE_PATH = "tools/meta/control/orchestration_state.json"
ORCHESTRATION_BRIEF_PATH = "tools/meta/control/orchestration_brief.json"
DOCS_FOCUS_PATH = "tools/meta/control/documentation_route_focus.json"
SYSTEM_MAP_PATH = "codex/doctrine/system_map.json"
DOCTRINE_RUNTIME_PATH = "codex/doctrine/doctrine_runtime.json"
AGENT_BOOTSTRAP_LIVE_PATH = "codex/doctrine/agent_bootstrap_live.json"
FRONTEND_NAV_GRAPH_PATH = "state/frontend_navigation/navigation_graph.json"
FRONTEND_NAV_MISSION_CONTROL_PATH = "state/frontend_navigation/navigation_mission_control.v1.json"
FRONTEND_COMPONENT_INDEX_PATH = "state/frontend_navigation/component_index.json"
FRONTEND_RENDER_LOAD_INDEX_PATH = "state/observability/render_load_index.json"
META_DIAGNOSTICS_ENDPOINT = "/api/world-model/meta-diagnostics/console"
META_DIAGNOSTICS_CAPABILITY_LANES_PATH = "state/system_atlas/frontend_capability_lanes.json"
META_DIAGNOSTICS_FACT_LEDGER_PATH = "codex/hologram/facts/ledger.json"
META_DIAGNOSTICS_PAPER_ROUTE_COVERAGE_PATH = "codex/doctrine/paper_modules/_route_coverage.json"
META_DIAGNOSTICS_PAPER_VALIDATION_PATH = "codex/doctrine/paper_modules/_validation_report.json"
META_DIAGNOSTICS_ANNEX_SYNC_PATH = "annexes/annex_sync_digest.json"
META_DIAGNOSTICS_ANNEX_DISTILLATION_PATH = "annexes/annex_distillation_index.json"
META_DIAGNOSTICS_MICROCOSM_GRAPH_PATH = "state/system_atlas/microcosm_composition_graph.json"
META_DIAGNOSTICS_DISSEMINATION_GATE_PATH = "state/system_atlas/dissemination_gate_report.json"
META_DIAGNOSTICS_PROMPT_LEDGER_PATH = "state/prompt_ledger/ledger.json"
META_DIAGNOSTICS_PROMPT_ADOPTION_PATH = "state/prompt_ledger/views/adoption_posture.json"
META_DIAGNOSTICS_PROMPT_UNLINKED_PATH = "state/prompt_ledger/views/unlinked_prompt_traces.json"
META_DIAGNOSTICS_TRACE_OBSERVATORY_PATH = "state/session_diagnostics/trace_observatory_projection.json"
META_DIAGNOSTICS_LATENCY_SPEEDBOARD_PATH = "state/performance/latency_speedboard.json"
META_DIAGNOSTICS_PROCESS_SUMMARY_PATH = "codex/hologram/process/summary.json"
NAVIGATION_READ_MODEL_CONTRACT_ID = "navigation_graph_read_model_v1"
NAVIGATION_READ_MODEL_PROJECTION_ID = "frontend_navigation_graph_projection"
FRONTEND_NAV_MISSION_CONTROL_CONTRACT = "frontend_navigation_mission_control_v1"
NAVIGATION_EDGE_GRAMMAR_CONTRACT = "shape_a_plus_unified_v1"
NAVIGATION_EDGE_EXPLAINABILITY_CONTRACT = "station_relation_explainability_v1"
NAVIGATION_EDGE_ADDRESSABILITY_CONTRACT = "station_relation_addressability_v1"
NAVIGATION_EDGE_PRESENTATION_ROLES = frozenset({"pathway", "membership", "fallback"})
NAVIGATION_GROUP_FLOW_LIMIT = 24
NAVIGATION_RELATION_SAMPLE_LIMIT = 5
NAVIGATION_GROUP_FLOW_SAMPLE_LIMIT = 5
DOCTRINE_REGISTRY_PATH = "codex/doctrine/doctrine_registry.json"
CONCEPTS_DIR = "codex/doctrine/concepts"
MECHANISMS_DIR = "codex/doctrine/mechanisms"
PHASE_FAMILY_ROOT = "obsidian/okay lets do this"
AGENT_TELEMETRY_ROOT = "state/agent_telemetry"
LEAN_MATH_PROJECTION_PATH = "state/system_atlas/lean_mathematics_microcosm.json"
LEAN_MATH_RECEIPT_PATH = "state/system_atlas/lean_mathematics_microcosm_receipt.json"
LEAN_MATH_MARKDOWN_PATH = "docs/system_atlas/lean_mathematics_microcosm.generated.md"
LEAN_MATH_VISUAL_SURFACE_KEYS = (
    "overview",
    "declaration_catalog",
    "declaration_graph",
    "obligation_graph",
    "receipt_timeline",
    "capability_cards",
    "validation_cards",
    "boundary_cards",
    "provenance_card",
    "doc_section_index",
)
LEAN_MATH_GRAPH_VIEW_KEYS = (
    "dependency_layers",
    "semantic_families",
    "final_theorem_routes",
    "high_degree_nodes",
    "terminal_claims",
    "external_dependencies",
)
LEAN_MATH_GRAPH_VIEW_SCHEMA_VERSION = "lean_mathematics_graph_views_v2"
LEAN_MATH_GRAPH_VIEW_REGISTRY = (
    {
        "view_id": "proof_spine_bundle",
        "label": "Proof Spine",
        "layout_policy": "layered_spine_with_branch_bundles",
        "default": True,
        "supports_expand": ["route_step", "layer", "semantic_family", "edge_bundle"],
    },
    {
        "view_id": "semantic_family_map",
        "label": "Semantic Families",
        "layout_policy": "family_clusters_with_route_overlay",
        "default": False,
        "supports_expand": ["semantic_family"],
    },
    {
        "view_id": "condensed_dag",
        "label": "Condensed DAG",
        "layout_policy": "transitive_reduced_layered_dag",
        "default": False,
        "supports_expand": ["edge_bundle", "semantic_family"],
    },
    {
        "view_id": "full_debug_dag",
        "label": "Full DAG",
        "layout_policy": "dense_debug",
        "default": False,
        "supports_expand": [],
    },
)

FRESHNESS_GREEN_HOURS = 4
FRESHNESS_AMBER_HOURS = 24


def _safe_read_json(repo_root: Path, rel_path: str) -> Optional[Dict[str, Any]]:
    """Read a repo-relative JSON file. Return None on any failure."""
    try:
        full = repo_root / rel_path
        if not full.exists() or not full.is_file():
            return None
        with full.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
        # Some files are arrays at top-level; wrap so callers always see a dict.
        return {"items": data}
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("world_model read failed for %s: %s", rel_path, exc)
        return None


def _file_mtime(repo_root: Path, rel_path: str) -> Optional[str]:
    try:
        full = repo_root / rel_path
        if not full.exists():
            return None
        return datetime.fromtimestamp(full.stat().st_mtime, tz=timezone.utc).isoformat()
    except Exception:
        return None


def _path_mtime_iso(path: Path) -> Optional[str]:
    try:
        if not path.exists():
            return None
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except Exception:
        return None


def _path_cache_stamp(path: Path) -> Tuple[bool, Optional[int], Optional[int]]:
    try:
        stat = path.stat()
        return True, int(stat.st_mtime_ns), int(stat.st_size)
    except OSError:
        return False, None, None


def _safe_read_json_path(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists() or not path.is_file():
            return None
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
        return {"items": data}
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("world_model read failed for %s: %s", path, exc)
        return None


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        token = str(value).strip()
        if not token:
            return None
        if token.endswith("Z"):
            token = token[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(token)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _age_seconds(value: Any, *, now: Optional[datetime] = None) -> Optional[int]:
    dt = _parse_iso_datetime(value)
    if dt is None:
        return None
    base = now or datetime.now(timezone.utc)
    return max(0, int((base - dt).total_seconds()))


def _excerpt(value: Any, *, limit: int = 180) -> Optional[str]:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _str_list(value: Any) -> List[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item or "").strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _safe_internal_route(value: Any, fallback: str) -> str:
    route = str(value or "").strip()
    if not route:
        return fallback
    if route == "/station" or route.startswith("/station/"):
        return route
    if route == "/world" or route.startswith("/world/"):
        return route
    if route.startswith("/control/") or route == "/launchpad" or route.startswith("/launchpad/"):
        return route
    if route == "/missions" or route.startswith("/missions/"):
        return route
    return fallback


def _intelligence_work_route(td_id: Any, *, fallback: str = "/station/ledger") -> str:
    """Build a deep link into the Intelligence Work lens for a given td_id.

    The Intelligence page already round-trips ?lens=work&object=work_item:<id>
    through its URL params (see system/server/ui/src/pages/Intelligence.tsx),
    so emitting this here lets the System cockpit row click drop the operator
    into the right tab with the row preselected, instead of jumping to the
    legacy /station/ledger surface.
    """
    raw = str(td_id or "").strip()
    if not raw:
        return fallback
    return f"/station/intelligence?lens=work&object=work_item:{raw}"


def _artifact_refs_from_values(values: Sequence[Any]) -> List[Dict[str, str]]:
    refs: List[Dict[str, str]] = []
    for raw in values:
        if isinstance(raw, Mapping):
            path = str(raw.get("path") or raw.get("file") or raw.get("artifact_path") or "").strip()
            label = str(raw.get("label") or raw.get("title") or path or "").strip()
        else:
            path = str(raw or "").strip()
            label = path
        if not path:
            continue
        refs.append({"path": path, "label": label or path})
    return refs


def _stage_error_from_mapping(
    source: Mapping[str, Any],
    *,
    stage: Optional[str] = None,
    source_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Normalize phase-local or factory-local stage failure detail.

    This helper refuses to invent a phase pipeline failure from global factory
    state. Callers must pass the phase-local pipeline artifact when they want a
    phase error, and the factory artifact when they want factory error.
    """
    raw_error = source.get("stage_error")
    if raw_error is None:
        raw_error = source.get("error")
    if raw_error is None and isinstance(source.get("errors"), list) and source.get("errors"):
        raw_error = source.get("errors")[-1]

    if not isinstance(raw_error, Mapping):
        detail = str(raw_error or "").strip()
        if not detail:
            return None
        raw_error = {"detail": detail}

    detail = raw_error.get("detail") or raw_error.get("message") or raw_error.get("error")
    summary = raw_error.get("summary") or raw_error.get("label") or _excerpt(detail, limit=120)
    artifact_refs = _artifact_refs_from_values(
        list(raw_error.get("artifact_refs") or [])
        + list(raw_error.get("artifacts") or [])
        + _str_list(raw_error.get("path"))
    )
    when = (
        raw_error.get("when")
        or raw_error.get("updated_at")
        or raw_error.get("created_at")
        or raw_error.get("timestamp")
        or source.get("last_stage_apply")
        or source.get("updated_at")
    )
    return {
        "stage": raw_error.get("stage") or stage or source.get("stage"),
        "summary": summary,
        "detail": detail,
        "source_path": source_path,
        "artifact_refs": artifact_refs,
        "when": when,
        "last_successful_stage": raw_error.get("last_successful_stage")
        or source.get("last_successful_stage"),
    }


def _normalize_payload_path(repo_root: Path, raw: str | Path | None) -> Optional[str]:
    if raw in (None, ""):
        return None
    try:
        path = Path(raw)
    except TypeError:
        return str(raw)
    if not path.is_absolute():
        path = repo_root / path
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def compute_freshness(updated_at_iso: Optional[str]) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Normalize artifact age into a small freshness payload the server can expose consistently across world-model slices.
    - Mechanism: Parse the ISO-like timestamp, compare it against UTC now, classify the age into fresh/stale/expired, and emit a compact label.
    - Guarantee: Returns a dict with tone, age_seconds, label, and iso keys; malformed or missing timestamps degrade to the unknown shape instead of raising.
    - Fails: None.
    - When-needed: Open when a server snapshot or event payload needs the shared freshness classifier instead of duplicating timestamp math in each loader.
    - Escalates-to: system/server/world_model.py::load_world_model_snapshot; system/server/world_model.py::load_attention_snapshot
    """
    if not updated_at_iso:
        return {"tone": "unknown", "age_seconds": None, "label": "unknown", "iso": None}
    try:
        dt = datetime.fromisoformat(str(updated_at_iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = (datetime.now(timezone.utc) - dt).total_seconds()
        hours = delta / 3600.0
        if hours < FRESHNESS_GREEN_HOURS:
            tone = "fresh"
        elif hours < FRESHNESS_AMBER_HOURS:
            tone = "stale"
        else:
            tone = "expired"

        if delta < 60:
            label = "just now"
        elif delta < 3600:
            label = f"{int(delta / 60)}m ago"
        elif delta < 86_400:
            label = f"{int(delta / 3600)}h ago"
        else:
            label = f"{int(delta / 86_400)}d ago"

        return {"tone": tone, "age_seconds": int(delta), "label": label, "iso": dt.isoformat()}
    except Exception:
        return {"tone": "unknown", "age_seconds": None, "label": "unknown", "iso": str(updated_at_iso)}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _navigation_refresh_command(repo_root: Path, source_kind: str) -> str:
    kind = str(source_kind or "all").strip() or "all"
    try:
        prepared = _shared_prepare_launch_operation(
            repo_root,
            operation_id="navigator_refresh",
            parameters={"kind": kind},
        )
        return prepared.command
    except Exception:
        return f"python3 kernel.py --embed-refresh {kind}"


def load_navigation_freshness_snapshot(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Project semantic-route embedding freshness into one Station-ready
      queue so stale navigation substrate is not stranded inside kernel output.
    - Mechanism: Read the persisted route-status artifact, normalize stale
      embedding source rows, attach the existing `navigator_refresh` launch
      operation as the repair action, and avoid live recomputation in the HTTP
      refresh path.
    - Reads: state/semantic_routing/route_status.json.
    - Guarantee: Returns `navigation_freshness_v1`; missing route status yields
      an available=false empty queue rather than failing the world snapshot.
    - When-needed: Open when Station, launcher operations, or diagnostics need
      the compact "which navigation source kind should be refreshed next" view.
    - Escalates-to: system.lib.semantic_routing; system.lib.launchable_operations
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        status = semantic_routing.load_route_status(repo_root)
    except Exception as exc:
        logger.debug("navigation freshness status load failed: %s", exc)
        status = {}
    if not isinstance(status, Mapping) or not status:
        return {
            "schema": "navigation_freshness_v1",
            "generated_at": generated_at,
            "available": False,
            "status_path": semantic_routing.STATUS_PATH,
            "route_status_generated_at": None,
            "route_graph_fingerprint": None,
            "refresh_operation_id": "navigator_refresh",
            "route_refresh_operation_id": "semantic_route_refresh",
            "stale_source_count": 0,
            "stale_or_missing_row_count": 0,
            "has_estimates": False,
            "top_source_kind": None,
            "queue": [],
        }

    embedding_staleness = status.get("embedding_staleness")
    if not isinstance(embedding_staleness, Mapping):
        embedding_staleness = {}

    queue: List[Dict[str, Any]] = []
    total_rows = 0
    has_estimates = False
    for source_kind, raw_source in sorted(embedding_staleness.items()):
        if not isinstance(raw_source, Mapping):
            continue
        stale_count = _safe_int(raw_source.get("stale_or_missing"), 0)
        record_count = _safe_int(raw_source.get("record_count"), 0)
        is_stale = bool(raw_source.get("stale")) or record_count == 0 or stale_count > 0
        if not is_stale:
            continue
        preview = [
            dict(row)
            for row in list(raw_source.get("stale_preview") or [])[:3]
            if isinstance(row, Mapping)
        ]
        is_estimate = bool(raw_source.get("stale_or_missing_is_estimate"))
        has_estimates = has_estimates or is_estimate
        total_rows += stale_count
        command = _navigation_refresh_command(repo_root, str(source_kind))
        queue.append(
            {
                "source_kind": str(source_kind),
                "stale_or_missing": stale_count,
                "record_count": record_count,
                "total_rows": raw_source.get("total_rows"),
                "missing_rows": raw_source.get("missing_rows"),
                "last_refresh_at": raw_source.get("last_refresh_at"),
                "last_refresh_freshness": compute_freshness(raw_source.get("last_refresh_at")),
                "path": raw_source.get("path"),
                "schema_hash": raw_source.get("schema_hash"),
                "stale_or_missing_is_estimate": is_estimate,
                "stale_reason_counts": dict(raw_source.get("stale_reason_counts") or {}),
                "stale_preview": preview,
                "stale_preview_truncated": bool(raw_source.get("stale_preview_truncated")),
                "recommended_operation": {
                    "operation_id": "navigator_refresh",
                    "parameters": {"kind": str(source_kind)},
                    "command": command,
                },
            }
        )

    queue.sort(
        key=lambda row: (
            -_safe_int(row.get("stale_or_missing"), 0),
            str(row.get("source_kind") or ""),
        )
    )
    top_source_kind = str(queue[0]["source_kind"]) if queue else None
    return {
        "schema": "navigation_freshness_v1",
        "generated_at": generated_at,
        "available": True,
        "status_path": semantic_routing.STATUS_PATH,
        "route_status_generated_at": status.get("generated_at"),
        "route_graph_fingerprint": status.get("route_graph_fingerprint"),
        "route_status_freshness": compute_freshness(status.get("generated_at")),
        "refresh_ledger_path": status.get("refresh_ledger_path") or "state/embeddings/refresh_ledger.jsonl",
        "pending_refresh_path": status.get("pending_refresh_path") or "state/embeddings/pending_refresh.jsonl",
        "refresh_operation_id": "navigator_refresh",
        "route_refresh_operation_id": "semantic_route_refresh",
        "stale_source_count": len(queue),
        "stale_or_missing_row_count": total_rows,
        "has_estimates": has_estimates,
        "top_source_kind": top_source_kind,
        "queue": queue[:12],
    }


def _principles_path_for_active_family(family_dir: Optional[str]) -> Optional[str]:
    if not family_dir:
        return None
    return f"{family_dir.rstrip('/')}/raw_seed/raw_seed_principles.json"


def _raw_seed_index_path_for_active_family(family_dir: Optional[str]) -> Optional[str]:
    if not family_dir:
        return None
    return f"{family_dir.rstrip('/')}/raw_seed/raw_seed_index.json"


def _resolve_active_family_dir(repo_root: Path) -> Optional[str]:
    """Resolve the active family, preferring explicit family activation over numeric recency."""
    root = repo_root / PHASE_FAMILY_ROOT
    if not root.exists() or not root.is_dir():
        return None
    candidates: List[Tuple[Tuple[int, ...], Path]] = []
    explicitly_active: List[Tuple[str, Tuple[int, ...], Path]] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        match = re.match(r"^(\d+)(?:\s|$)", child.name)
        if not match:
            continue
        try:
            number = (int(match.group(1)),)
        except ValueError:
            continue
        candidates.append((number, child))
        phase_family = _safe_read_json(repo_root, str(child.relative_to(repo_root) / "phase_family.json")) or {}
        changed_at = str(phase_family.get("active_phase_changed_at") or "").strip()
        has_explicit_active_phase = bool(
            str(phase_family.get("active_phase_dir") or "").strip()
            or str(phase_family.get("active_phase_number") or "").strip()
            or str(phase_family.get("active_phase_id") or "").strip()
        )
        if has_explicit_active_phase:
            explicitly_active.append((changed_at, number, child))
    if explicitly_active:
        explicitly_active.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return str(explicitly_active[0][2].relative_to(repo_root))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    chosen = candidates[0][1]
    return str(chosen.relative_to(repo_root))


def _phase_sort_key(phase_number: str) -> Tuple[int, ...]:
    parts = []
    for piece in str(phase_number).split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _list_phase_dirs(repo_root: Path, family_dir: str) -> List[Dict[str, Any]]:
    """Enumerate the immediate phase folders inside a family root, sorted naturally.

    Caches the heavy uncached compute (5 JSON reads × N phases, ~80 ms for a
    53-phase family) through the repo's stale-while-revalidate cache. Cache
    key is (repo_root, family_dir, family_dir mtime_ns) so any change to the
    family layout invalidates the entry; swr_get returns a deepcopy so callers
    can mutate the result without poisoning the cache. The 30 s TTL is a
    safety net against mtime granularity edge cases — primary invalidation is
    the mtime-keyed cache miss.
    """
    family = repo_root / family_dir
    if not family.exists() or not family.is_dir():
        return []
    try:
        fam_mtime_ns = family.stat().st_mtime_ns
    except OSError:
        return _list_phase_dirs_uncached(repo_root, family_dir)
    return swr_get(
        cache_name="world_model._list_phase_dirs",
        key=(str(repo_root), family_dir, fam_mtime_ns),
        builder=lambda: _list_phase_dirs_uncached(repo_root, family_dir),
        ttl_s=30.0,
    )


def _list_phase_dirs_uncached(repo_root: Path, family_dir: str) -> List[Dict[str, Any]]:
    """Uncached compute for the phase-dir inventory; see _list_phase_dirs."""
    family = repo_root / family_dir
    if not family.exists() or not family.is_dir():
        return []
    discovered: List[Tuple[Tuple[int, ...], Path, str, str]] = []
    for child in family.iterdir():
        if not child.is_dir():
            continue
        match = re.match(r"^(\d+\.\d+)\s*-\s*(.*)$", child.name)
        if not match:
            continue
        phase_number = match.group(1)
        title = match.group(2).strip()
        discovered.append((_phase_sort_key(phase_number), child, phase_number, title))
    discovered.sort(key=lambda x: x[0])

    phases: List[Dict[str, Any]] = []
    for _, child, phase_number, title in discovered:
        rel_dir = str(child.relative_to(repo_root))
        scaffold = _safe_read_json(repo_root, f"{rel_dir}/phase_scaffold.json") or {}
        synth = _safe_read_json(repo_root, f"{rel_dir}/synth_seed.json") or {}
        focus_directive = _safe_read_json(repo_root, f"{rel_dir}/focus_directive.json") or {}
        pipeline_state = _safe_read_json(repo_root, f"{rel_dir}/pipeline_state.json") or {}
        meta_ledger = _safe_read_json(repo_root, f"{rel_dir}/meta_ledger.json") or {}
        cycle_dirs = sorted(
            (
                p.name
                for p in child.iterdir()
                if p.is_dir() and re.match(r"^cycle_\d+$", p.name)
            ),
            reverse=True,
        )
        phases.append(
            {
                "phase_id": phase_number,
                "title": title or scaffold.get("title") or child.name,
                "phase_dir": rel_dir,
                "scaffold": {
                    "kind": scaffold.get("kind"),
                    "schema_version": scaffold.get("schema_version"),
                    "raw_seed_path": scaffold.get("raw_seed_path"),
                    "synth_seed_path": scaffold.get("synth_seed_path") or scaffold.get("active_seed_path"),
                    "synth_seed_md_path": scaffold.get("synth_seed_md_path"),
                    "meta_ledger_path": scaffold.get("meta_ledger_path"),
                },
                "synth": {
                    "kind": synth.get("kind"),
                    "tranche_label": synth.get("tranche_label") or synth.get("label"),
                    # synth_seed_phase_v1 has no top-level summary; fall back to intent.goal
                    # then current_wave.objective so PhaseDashboard renders a truthful sentence
                    # instead of "No synth summary recorded." Tranche-style synths still win
                    # because their top-level summary is non-empty.
                    "summary": (
                        synth.get("summary")
                        or (synth.get("intent") or {}).get("goal")
                        or (synth.get("current_wave") or {}).get("objective")
                    ),
                    "items_count": (len(synth.get("items", [])) if isinstance(synth.get("items"), list) else None),
                    "shards_count": (len(synth.get("shards", [])) if isinstance(synth.get("shards"), list) else None),
                },
                "focus_directive": {
                    "active": bool(focus_directive.get("active")),
                    "summary": focus_directive.get("summary"),
                    "actor": focus_directive.get("actor"),
                    "intent": focus_directive.get("intent"),
                },
                "pipeline_state": {
                    "stage": pipeline_state.get("stage"),
                    "controller_phase": pipeline_state.get("controller_phase") or pipeline_state.get("phase"),
                    "cycle": pipeline_state.get("cycle"),
                    "blocked": bool(pipeline_state.get("blocked")),
                    "gate_reason": pipeline_state.get("gate_reason"),
                    "updated_at": pipeline_state.get("updated_at"),
                    "stage_error": _stage_error_from_mapping(
                        pipeline_state,
                        stage=pipeline_state.get("stage"),
                        source_path=f"{rel_dir}/pipeline_state.json",
                    ),
                },
                "meta_ledger": {
                    "kind": meta_ledger.get("kind"),
                    "summary": meta_ledger.get("summary") or meta_ledger.get("note"),
                    "cycles": (
                        len(meta_ledger.get("cycles", []))
                        if isinstance(meta_ledger.get("cycles"), list)
                        else None
                    ),
                },
                "latest_cycle": cycle_dirs[0] if cycle_dirs else None,
                "cycle_count": len(cycle_dirs),
                "freshness": compute_freshness(pipeline_state.get("updated_at")),
            }
        )
    return phases


def _match_phase_record(
    phases: Sequence[Dict[str, Any]],
    *,
    phase_dir: Optional[str] = None,
    phase_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    normalized_id = str(phase_id or "").strip().replace("_", ".")
    for phase in phases:
        if phase_dir and phase.get("phase_dir") == phase_dir:
            return phase
    if normalized_id:
        for phase in phases:
            candidate = str(phase.get("phase_id") or "").strip()
            if candidate in {phase_id, normalized_id}:
                return phase
    return None


def _resolve_active_phase_record(
    *,
    phases: Sequence[Dict[str, Any]],
    phase_family: Optional[Dict[str, Any]],
    bootstrap_bindings: Optional[Dict[str, Any]],
    orchestration: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    phase_family = phase_family or {}
    bootstrap_bindings = bootstrap_bindings or {}

    explicit_family_phase = _match_phase_record(
        phases,
        phase_dir=str(phase_family.get("active_phase_dir") or "").strip() or None,
        phase_id=(
            str(phase_family.get("active_phase_number") or "").strip()
            or str(phase_family.get("active_phase_id") or "").strip()
            or None
        ),
    )
    if explicit_family_phase is not None:
        return explicit_family_phase

    bootstrap_phase = _match_phase_record(
        phases,
        phase_dir=str(bootstrap_bindings.get("phase_dir") or "").strip() or None,
        phase_id=str(bootstrap_bindings.get("controller_phase") or "").strip() or None,
    )
    if bootstrap_phase is not None:
        return bootstrap_phase

    if orchestration:
        for driver in orchestration.get("drivers", []) or []:
            if not isinstance(driver, Mapping) or not driver.get("active"):
                continue
            matched = _match_phase_record(
                phases,
                phase_dir=str(driver.get("phase_dir") or "").strip() or None,
                phase_id=str(driver.get("phase_ref") or "").strip() or None,
            )
            if matched is not None:
                return matched

    return phases[-1] if phases else None


def _phase_file_inventory(
    repo_root: Path, phase_dir: str
) -> Tuple[List[Dict[str, Any]], str, Optional[str]]:
    full_rel = f"{phase_dir}/system_view.json"
    raw = _safe_read_json(repo_root, full_rel)
    if raw:
        files = raw.get("files") if isinstance(raw.get("files"), list) else []
        return files, full_rel, raw.get("generated_at")

    phase_root = repo_root / phase_dir
    if not phase_root.exists() or not phase_root.is_dir():
        return [], full_rel, None

    files: List[Dict[str, Any]] = []
    latest_mtime: Optional[float] = None
    for path in sorted(phase_root.rglob("*")):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.relative_to(phase_root).parts):
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        latest_mtime = stat.st_mtime if latest_mtime is None else max(latest_mtime, stat.st_mtime)
        files.append(
            {
                "path": str(path.relative_to(repo_root)),
                "size_bytes": stat.st_size,
            }
        )

    generated_at = (
        datetime.fromtimestamp(latest_mtime, tz=timezone.utc).isoformat()
        if latest_mtime is not None
        else None
    )
    return files, phase_dir, generated_at


def _driver_runtime_slice(
    raw: Mapping[str, Any],
    *,
    reactions: Mapping[str, Any],
    active_driver: Optional[str],
    gate_owner: Optional[str],
) -> Dict[str, Any]:
    runtime = raw.get("runtime") if isinstance(raw.get("runtime"), Mapping) else {}
    current_operation = runtime.get("current_operation")
    if not isinstance(current_operation, Mapping):
        current_operation = raw.get("current_operation") if isinstance(raw.get("current_operation"), Mapping) else None
    recent_failures = runtime.get("recent_failures")
    if not isinstance(recent_failures, list):
        recent_failures = raw.get("recent_failures") if isinstance(raw.get("recent_failures"), list) else []

    driver_id = raw.get("driver_id")
    raw_barriers = reactions.get("awaiting_barriers") if isinstance(reactions.get("awaiting_barriers"), list) else []
    include_barriers = bool(driver_id and (driver_id == active_driver or driver_id == gate_owner))
    awaiting_barriers: List[Dict[str, Any]] = []
    for barrier in raw_barriers:
        if not isinstance(barrier, Mapping):
            continue
        owner = barrier.get("owner_driver") or barrier.get("driver_id")
        if include_barriers or not owner or owner == driver_id:
            awaiting_barriers.append(dict(barrier))

    pending_queue_count = runtime.get("pending_queue_count")
    if pending_queue_count is None:
        queue = raw.get("queue")
        pending_queue_count = len(queue) if isinstance(queue, list) else 0
    try:
        pending_queue_count_int = int(pending_queue_count)
    except (TypeError, ValueError):
        pending_queue_count_int = 0

    return {
        "current_operation": dict(current_operation) if isinstance(current_operation, Mapping) else None,
        "recent_failures": [dict(item) for item in recent_failures if isinstance(item, Mapping)][:5],
        "awaiting_barriers": awaiting_barriers[:5],
        "pending_queue_count": pending_queue_count_int,
    }


def _condense_orchestration_state(state: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not state:
        return None
    drivers = []
    reactions = state.get("reactions") if isinstance(state.get("reactions"), Mapping) else {}
    gate = state.get("gate") or {}
    active_driver = state.get("active_driver")
    gate_owner = gate.get("owner_driver") if isinstance(gate, Mapping) else None
    for raw in state.get("drivers", []) or []:
        if not isinstance(raw, dict):
            continue
        next_action = raw.get("next_action") or {}
        drivers.append(
            {
                "driver_id": raw.get("driver_id"),
                "label": raw.get("label"),
                "available": bool(raw.get("available")),
                "active": bool(raw.get("active")),
                "stage": raw.get("stage"),
                "blocked": bool(raw.get("blocked")),
                "gate_reason": raw.get("gate_reason"),
                "phase_ref": raw.get("phase_ref"),
                "phase_title": raw.get("phase_title"),
                "phase_dir": raw.get("phase_dir"),
                "next_action": {
                    "summary": next_action.get("summary"),
                    "command": next_action.get("command"),
                },
                "last_updated": raw.get("last_updated"),
                "state_path": raw.get("state_path"),
                "review_artifacts": _str_list(raw.get("review_artifacts")),
                "runtime": _driver_runtime_slice(
                    raw,
                    reactions=reactions,
                    active_driver=active_driver,
                    gate_owner=gate_owner,
                ),
            }
        )
    decision = state.get("decision") or {}
    return {
        "kind": state.get("kind"),
        "active_driver": state.get("active_driver"),
        "decision": {
            "immediate_mode": decision.get("immediate_mode"),
            "summary": decision.get("summary"),
            "command": decision.get("command"),
            "launch_recommended_now": bool(decision.get("launch_recommended_now")),
            "reasoning": decision.get("reasoning"),
            "considered": list(decision.get("considered") or []),
            "evidence_refs": _artifact_refs_from_values(decision.get("evidence_refs") or []),
            "confidence": decision.get("confidence"),
            "last_changed_at": decision.get("last_changed_at") or decision.get("updated_at"),
        },
        "gate": {
            "active": bool(gate.get("active")),
            "gate_reason": gate.get("gate_reason"),
            "owner_driver": gate.get("owner_driver"),
            "review_ready": bool(gate.get("review_ready")),
            "command": gate.get("command"),
        },
        "drivers": drivers,
        "reactions": {
            "engine_armed": bool(reactions.get("engine_armed")),
            "engine_status": reactions.get("engine_status"),
            "pid": reactions.get("pid"),
            "cursor_event_id": reactions.get("cursor_event_id"),
            "last_tick_at": reactions.get("last_tick_at"),
            "last_error": reactions.get("last_error"),
            "awaiting_barriers": list(reactions.get("awaiting_barriers") or []),
            "active_reaction_id": reactions.get("active_reaction_id"),
            "last_fired_at": reactions.get("last_fired_at"),
        },
        "updated_at": state.get("updated_at"),
        "freshness": compute_freshness(state.get("updated_at")),
    }


def _condense_doctrine_index(repo_root: Path) -> Dict[str, Any]:
    """Mine the system_map for compact concept/mechanism/principle catalogs."""
    system_map = _safe_read_json(repo_root, SYSTEM_MAP_PATH) or {}
    concepts = []
    for raw in system_map.get("concepts", []) or []:
        if not isinstance(raw, dict):
            continue
        concepts.append(
            {
                "id": raw.get("id"),
                "slug": raw.get("slug"),
                "title": raw.get("title"),
                "tags": raw.get("tags") or [],
                "scope": raw.get("scope"),
                "status": raw.get("status"),
            }
        )
    mechanisms = []
    for raw in system_map.get("mechanisms", []) or []:
        if not isinstance(raw, dict):
            continue
        mechanisms.append(
            {
                "id": raw.get("id"),
                "slug": raw.get("slug"),
                "title": raw.get("title"),
                "tags": raw.get("tags") or [],
                "scope": raw.get("scope"),
                "status": raw.get("status"),
                "drift_sensitivity": raw.get("drift_sensitivity"),
            }
        )
    principles = []
    for raw in system_map.get("principles", []) or []:
        if not isinstance(raw, dict):
            continue
        principles.append(
            {
                "id": raw.get("id"),
                "slug": raw.get("slug"),
                "title": raw.get("title"),
                "tags": raw.get("tags") or [],
                "scope": raw.get("scope"),
                "status": raw.get("status"),
            }
        )
    return {
        "system_map_generated_at": system_map.get("generated_at"),
        "concepts": concepts,
        "mechanisms": mechanisms,
        "principles": principles,
    }


def _condense_principles_for_family(repo_root: Path, family_dir: Optional[str]) -> Dict[str, Any]:
    rel = _principles_path_for_active_family(family_dir)
    raw = _safe_read_json(repo_root, rel) if rel else None
    if not raw:
        return {"path": rel, "principles": [], "family_id": None, "family_title": None}
    pris = raw.get("principles") or []
    out = []
    for entry in pris:
        if not isinstance(entry, dict):
            continue
        out.append(
            {
                "id": entry.get("id"),
                "slug": entry.get("slug"),
                "title": entry.get("title"),
                "statement": entry.get("statement"),
                "kind": entry.get("kind"),
                "scope": entry.get("scope"),
                "scope_profile": entry.get("scope_profile") or {},
                "status": entry.get("status"),
                "primary_subdomain": entry.get("primary_subdomain"),
                "secondary_subdomains": entry.get("secondary_subdomains") or [],
                "tags": entry.get("tags") or [],
            }
        )
    return {
        "path": rel,
        "family_id": raw.get("family_id"),
        "family_number": raw.get("family_number"),
        "family_title": raw.get("family_title"),
        "generated_at": raw.get("generated_at"),
        "principles": out,
    }


def _condense_docs_focus(repo_root: Path) -> Dict[str, Any]:
    raw = _safe_read_json(repo_root, DOCS_FOCUS_PATH) or {}
    return {
        "path": DOCS_FOCUS_PATH,
        "active_preset_id": raw.get("active_preset_id") or "neutral",
        "label": raw.get("label") or "Neutral",
        "presets": raw.get("presets") or [],
        "updated_at": raw.get("updated_at"),
    }


def _condense_doctrine_runtime(repo_root: Path) -> Dict[str, Any]:
    raw = _safe_read_json(repo_root, DOCTRINE_RUNTIME_PATH) or {}
    control_plane = raw.get("control_plane") or {}
    return {
        "schema_version": raw.get("schema_version"),
        "purpose": raw.get("purpose"),
        "control_plane": {
            "emit_self": control_plane.get("emit_self"),
            "docs_route": control_plane.get("docs_route"),
            "docs_route_focus_list": control_plane.get("docs_route_focus_list"),
            "docs_route_focus_set": control_plane.get("docs_route_focus_set"),
            "agent_bootstrap": control_plane.get("agent_bootstrap"),
            "orchestration_state": control_plane.get("orchestration_state"),
            "orchestration_event_log": control_plane.get("orchestration_event_log"),
        },
        "operator_quickstart": raw.get("operator_quickstart") or [],
        "freshness": compute_freshness(_file_mtime(repo_root, DOCTRINE_RUNTIME_PATH)),
    }


def _condense_agent_bootstrap_live(repo_root: Path) -> Dict[str, Any]:
    raw = _safe_read_json(repo_root, AGENT_BOOTSTRAP_LIVE_PATH) or {}
    bindings = raw.get("live_bindings") or {}
    return {
        "schema_version": raw.get("schema_version"),
        "generated_at": raw.get("generated_at"),
        "live_bindings": {
            "phase_dir": bindings.get("phase_dir"),
            "family_dir": bindings.get("family_dir"),
            "controller_phase": bindings.get("controller_phase"),
            "pipeline_stage": bindings.get("pipeline_stage"),
            "cycle": bindings.get("cycle"),
            "factory_stage": bindings.get("factory_stage") if bindings.get("factory_state_live") else None,
            "factory_last_run": bindings.get("factory_last_run"),
            "factory_state_role": bindings.get("factory_state_role"),
            "factory_state_freshness": bindings.get("factory_state_freshness"),
            "factory_state_live": bindings.get("factory_state_live"),
            "orchestration_active_driver": bindings.get("orchestration_active_driver"),
            "orchestration_gate_reason": bindings.get("orchestration_gate_reason"),
            "orchestration_current_owner": bindings.get("orchestration_current_owner"),
            "orchestration_next_handoff": bindings.get("orchestration_next_handoff"),
            "active_directive_path": bindings.get("active_directive_path"),
            "active_directive_summary": bindings.get("active_directive_summary"),
            "system_view_rel": bindings.get("system_view_rel"),
            "system_view_file_count": bindings.get("system_view_file_count"),
            "documentation_route_focus_active_preset": bindings.get("documentation_route_focus_active_preset"),
            "system_map_generated_at": bindings.get("system_map_generated_at"),
            "doctrine_runtime_mtime_iso": bindings.get("doctrine_runtime_mtime_iso"),
            "extracted_shard_count": bindings.get("extracted_shard_count"),
        },
        "situation_routes": raw.get("situation_routes") or [],
        "actor_context_surfaces": raw.get("actor_context_surfaces") or [],
        "freshness": compute_freshness(raw.get("generated_at")),
    }


def _condense_frontend_semantic_row(
    row: Any,
    *,
    view_id: str,
    route: Any = None,
) -> Dict[str, Any]:
    if not isinstance(row, Mapping):
        return {
            "view_id": view_id,
            "route": route if isinstance(route, str) else None,
            "health": "unknown",
            "confidence": None,
            "summary": None,
            "reason": "No semantic_layer.v1.json row exists for this view.",
            "authority_note": None,
            "basis": [],
            "evidence_refs": [],
            "recommended_action": "Add a semantic health row for this surface.",
            "last_reviewed_at": None,
            "related_paper_or_skill": [],
        }
    health = row.get("health")
    if not isinstance(health, str) or health not in frontend_surface_contracts.VALID_HEALTH:
        health = "unknown"
    return {
        "view_id": view_id,
        "station_views_slug": (
            row.get("station_views_slug")
            if isinstance(row.get("station_views_slug"), str) or row.get("station_views_slug") is None
            else None
        ),
        "route": row.get("route") if isinstance(row.get("route"), str) else route if isinstance(route, str) else None,
        "health": health,
        "confidence": row.get("confidence") if isinstance(row.get("confidence"), (int, float)) else None,
        "summary": row.get("summary") if isinstance(row.get("summary"), str) else None,
        "reason": row.get("reason") if isinstance(row.get("reason"), str) else None,
        "authority_note": row.get("authority_note") if isinstance(row.get("authority_note"), str) else None,
        "basis": [item for item in (row.get("basis") or []) if isinstance(item, str)],
        "evidence_refs": [item for item in (row.get("evidence_refs") or []) if isinstance(item, str)],
        "recommended_action": (
            row.get("recommended_action") if isinstance(row.get("recommended_action"), str) else None
        ),
        "last_reviewed_at": row.get("last_reviewed_at") if isinstance(row.get("last_reviewed_at"), str) else None,
        "related_paper_or_skill": [
            item for item in (row.get("related_paper_or_skill") or []) if isinstance(item, str)
        ],
    }


def _condense_surface_audit_row(row: Any) -> Dict[str, Any] | None:
    if not isinstance(row, Mapping):
        return None

    def _str_list(key: str) -> list[str]:
        return [item for item in (row.get(key) or []) if isinstance(item, str)]

    return {
        "surface_id": row.get("surface_id") if isinstance(row.get("surface_id"), str) else None,
        "operator_job": row.get("operator_job") if isinstance(row.get("operator_job"), str) else None,
        "group": row.get("group") if isinstance(row.get("group"), str) else None,
        "posture": row.get("posture") if isinstance(row.get("posture"), str) else None,
        "primary_component": (
            row.get("primary_component")
            if isinstance(row.get("primary_component"), str)
            else None
        ),
        "primary_component_name": (
            row.get("primary_component_name")
            if isinstance(row.get("primary_component_name"), str)
            else None
        ),
        "host_component": (
            row.get("host_component") if isinstance(row.get("host_component"), str) else None
        ),
        "backend_endpoints": _str_list("backend_endpoints"),
        "store_slices": _str_list("store_slices"),
        "shared_components": _str_list("shared_components"),
        "capture_slug": (
            row.get("capture_slug") if isinstance(row.get("capture_slug"), str) else None
        ),
        "substrate_bindings": _str_list("substrate_bindings"),
        "semantic_health": (
            row.get("semantic_health") if isinstance(row.get("semantic_health"), str) else None
        ),
        "semantic_summary": (
            row.get("semantic_summary") if isinstance(row.get("semantic_summary"), str) else None
        ),
        "evidence_refs": _str_list("evidence_refs"),
    }


NAVIGATION_EDGE_MECHANISM_META: Dict[str, Dict[str, Any]] = {
    "explicit": {
        "label": "opens",
        "category": "declared_navigation",
        "description": "Surface registry outboundTo declaration; this is an intentional cross-surface jump.",
        "presentation_role": "pathway",
        "rank": 0,
        "weight": 1.0,
    },
    "outbound_declaration": {
        "label": "opens",
        "category": "declared_navigation",
        "description": "Surface registry outboundTo declaration; this is an intentional cross-surface jump.",
        "presentation_role": "pathway",
        "rank": 0,
        "weight": 1.0,
    },
    "outbound_declared": {
        "label": "opens",
        "category": "declared_navigation",
        "description": "Legacy name for the surface registry outboundTo declaration.",
        "presentation_role": "pathway",
        "rank": 0,
        "weight": 1.0,
    },
    "overlay_anchor": {
        "label": "hosts overlay",
        "category": "hosted_overlay",
        "description": "Overlay, modal, or drawer is hosted by this page surface.",
        "presentation_role": "pathway",
        "rank": 1,
        "weight": 0.86,
    },
    "overlay_of": {
        "label": "overlay",
        "category": "hosted_overlay",
        "description": "Overlay, modal, or drawer is hosted by another page surface.",
        "presentation_role": "pathway",
        "rank": 1,
        "weight": 0.86,
    },
    "route_hierarchy": {
        "label": "route child",
        "category": "route_structure",
        "description": "Child surface is hosted under the selected route prefix in App.tsx.",
        "presentation_role": "pathway",
        "rank": 2,
        "weight": 0.82,
    },
    "legacy_or_workbench_of": {
        "label": "workbench of",
        "category": "surface_lifecycle",
        "description": "Workbench or legacy route is parked behind a canonical surface instead of replacing it.",
        "presentation_role": "pathway",
        "rank": 3,
        "weight": 0.78,
    },
    "shared_backend_api": {
        "label": "shares API",
        "category": "backend_dependency",
        "description": "Both surfaces call the same typed API method from their owning component file.",
        "presentation_role": "pathway",
        "rank": 4,
        "weight": 0.70,
    },
    "shared_component": {
        "label": "shares component",
        "category": "frontend_dependency",
        "description": "Both surfaces render through the same primary component or shared frontend primitive. Folded — high-cardinality implementation-affinity, not a wayfinding pathway.",
        "presentation_role": "membership",
        "rank": 5,
        "weight": 0.64,
    },
    "command_palette": {
        "label": "palette",
        "category": "runtime_navigation",
        "description": "Command palette or runtime action can reach the target surface. Folded — runtime reachability, not a declared pathway.",
        "presentation_role": "membership",
        "rank": 7,
        "weight": 0.46,
    },
    "station_group": {
        "label": "same Station group",
        "category": "station_lens_navigation",
        "description": "Both views are siblings inside the Station lens group.",
        "presentation_role": "membership",
        "rank": 20,
        "weight": 0.40,
    },
    "shell_group": {
        "label": "same shell group",
        "category": "global_shell_navigation",
        "description": "Both views are reachable from the same global shell navigation group.",
        "presentation_role": "membership",
        "rank": 30,
        "weight": 0.30,
    },
    "station_lens_menu": {
        "label": "Station lens menu",
        "category": "station_lens_navigation",
        "description": "Both views are Station lens members reachable through the lens menu.",
        "presentation_role": "membership",
        "rank": 40,
        "weight": 0.26,
    },
    "adjacency": {
        "label": "navigation adjacency",
        "category": "fallback_navigation",
        "description": "Fallback adjacency relation derived when mechanism metadata is unavailable.",
        "presentation_role": "fallback",
        "rank": 80,
        "weight": 0.25,
    },
    "unknown": {
        "label": "navigation relation",
        "category": "unknown",
        "description": "Navigation graph relation with no known mechanism metadata.",
        "presentation_role": "fallback",
        "rank": 99,
        "weight": 0.25,
    },
}


def _navigation_edge_mechanism_meta(mechanism: str) -> Dict[str, Any]:
    return NAVIGATION_EDGE_MECHANISM_META.get(
        mechanism,
        NAVIGATION_EDGE_MECHANISM_META["unknown"],
    )


def _navigation_edge_presentation_role(mechanism: str) -> str:
    role = _navigation_edge_mechanism_meta(mechanism).get("presentation_role")
    if isinstance(role, str) and role in NAVIGATION_EDGE_PRESENTATION_ROLES:
        return role
    return "fallback"


def _navigation_edge_key(
    source: str,
    target: str,
    mechanism: str,
    category: str | None,
) -> str:
    return f"{source}|{target}|{mechanism}|{category or ''}"


def _navigation_group_flow_key(source_group: str, target_group: str) -> str:
    return f"{source_group}->{target_group}"


def _navigation_group_id(view: Mapping[str, Any]) -> str:
    group = view.get("shell_group")
    return group if isinstance(group, str) and group else "unassigned"


def _navigation_view_score(view: Mapping[str, Any]) -> tuple[int, str]:
    fanin = view.get("fanin_count")
    fanout = view.get("fanout_count")
    score = 0
    if isinstance(fanin, (int, float)) and not isinstance(fanin, bool):
        score += int(fanin)
    if isinstance(fanout, (int, float)) and not isinstance(fanout, bool):
        score += int(fanout)
    view_id = view.get("id") if isinstance(view.get("id"), str) else ""
    return score, view_id


def _navigation_dominant_relation(relation_counts: Counter[str]) -> str:
    if not relation_counts:
        return "unknown"

    def _sort_key(item: tuple[str, int]) -> tuple[int, int, str]:
        relation, count = item
        meta = _navigation_edge_mechanism_meta(relation)
        rank = meta.get("rank")
        return (
            -count,
            int(rank) if isinstance(rank, (int, float)) and not isinstance(rank, bool) else 99,
            relation,
        )

    return sorted(relation_counts.items(), key=_sort_key)[0][0]


def _sorted_counter_payload(counter: Counter[str]) -> Dict[str, int]:
    return {
        key: count
        for key, count in sorted(
            counter.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )
    }


def _navigation_edge_sample(
    edge: Mapping[str, Any],
    view_by_id: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any] | None:
    source = edge.get("from")
    target = edge.get("to")
    if not isinstance(source, str) or not isinstance(target, str):
        return None
    source_view = view_by_id.get(source)
    target_view = view_by_id.get(target)
    if source_view is None or target_view is None:
        return None
    mechanism = edge.get("mechanism") if isinstance(edge.get("mechanism"), str) else "unknown"
    meta = _navigation_edge_mechanism_meta(mechanism)
    role = edge.get("presentation_role") if isinstance(edge.get("presentation_role"), str) else None
    if role not in NAVIGATION_EDGE_PRESENTATION_ROLES:
        role = _navigation_edge_presentation_role(mechanism)
    evidence_refs = [
        item for item in (edge.get("evidence_refs") or []) if isinstance(item, str)
    ]
    edge_key = edge.get("edge_key") if isinstance(edge.get("edge_key"), str) else None
    category = edge.get("category") if isinstance(edge.get("category"), str) else None
    if edge_key is None:
        edge_key = _navigation_edge_key(source, target, mechanism, category)
    source_label = (
        source_view.get("label")
        if isinstance(source_view.get("label"), str)
        else source
    )
    target_label = (
        target_view.get("label")
        if isinstance(target_view.get("label"), str)
        else target
    )
    return {
        "edge_key": edge_key,
        "source": source,
        "target": target,
        "source_label": source_label,
        "target_label": target_label,
        "source_group": _navigation_group_id(source_view),
        "target_group": _navigation_group_id(target_view),
        "relation": mechanism,
        "relation_label": (
            edge.get("label") if isinstance(edge.get("label"), str) else meta.get("label")
        ),
        "presentation_role": role,
        "evidence_refs": evidence_refs[:NAVIGATION_RELATION_SAMPLE_LIMIT],
    }


def _build_navigation_relation_summary(
    views: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    view_by_id = {
        str(view.get("id")): view
        for view in views
        if isinstance(view.get("id"), str)
    }
    summaries: Dict[str, Dict[str, Any]] = {}
    for edge in edges:
        source = edge.get("from")
        target = edge.get("to")
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        source_view = view_by_id.get(source)
        target_view = view_by_id.get(target)
        if source_view is None or target_view is None:
            continue
        mechanism = edge.get("mechanism") if isinstance(edge.get("mechanism"), str) else "unknown"
        meta = _navigation_edge_mechanism_meta(mechanism)
        role = edge.get("presentation_role") if isinstance(edge.get("presentation_role"), str) else None
        if role not in NAVIGATION_EDGE_PRESENTATION_ROLES:
            role = _navigation_edge_presentation_role(mechanism)
        record = summaries.get(mechanism)
        if record is None:
            record = {
                "relation_key": mechanism,
                "relation": mechanism,
                "label": edge.get("label") if isinstance(edge.get("label"), str) else meta.get("label"),
                "category": (
                    edge.get("category")
                    if isinstance(edge.get("category"), str)
                    else meta.get("category")
                ),
                "description": (
                    edge.get("description")
                    if isinstance(edge.get("description"), str)
                    else meta.get("description")
                ),
                "presentation_role": role,
                "edge_count": 0,
                "evidence_count": 0,
                "_source_group_counts": Counter(),
                "_target_group_counts": Counter(),
                "sample_edges": [],
                "sample_limit": NAVIGATION_RELATION_SAMPLE_LIMIT,
            }
            summaries[mechanism] = record
        record["edge_count"] += 1
        if edge.get("evidence_refs"):
            record["evidence_count"] += 1
        record["_source_group_counts"][_navigation_group_id(source_view)] += 1
        record["_target_group_counts"][_navigation_group_id(target_view)] += 1
        if len(record["sample_edges"]) < NAVIGATION_RELATION_SAMPLE_LIMIT:
            sample = _navigation_edge_sample(edge, view_by_id)
            if sample is not None:
                record["sample_edges"].append(sample)

    relation_summary: List[Dict[str, Any]] = []
    for record in summaries.values():
        source_counts = record.pop("_source_group_counts")
        target_counts = record.pop("_target_group_counts")
        record["source_group_counts"] = _sorted_counter_payload(source_counts)
        record["target_group_counts"] = _sorted_counter_payload(target_counts)
        record["sample_omitted_count"] = max(
            0,
            int(record.get("edge_count") or 0) - len(record["sample_edges"]),
        )
        relation_summary.append(record)

    def _sort_key(row: Mapping[str, Any]) -> tuple[int, int, str]:
        relation = row.get("relation") if isinstance(row.get("relation"), str) else "unknown"
        meta = _navigation_edge_mechanism_meta(relation)
        rank = meta.get("rank")
        return (
            -int(row.get("edge_count") or 0),
            int(rank) if isinstance(rank, (int, float)) and not isinstance(rank, bool) else 99,
            relation,
        )

    relation_summary.sort(key=_sort_key)
    return relation_summary


def _build_navigation_group_flows(
    views: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    view_by_id = {
        str(view.get("id")): view
        for view in views
        if isinstance(view.get("id"), str)
    }
    anchor_by_group: Dict[str, Mapping[str, Any]] = {}
    for view in views:
        view_id = view.get("id")
        if not isinstance(view_id, str):
            continue
        group = _navigation_group_id(view)
        incumbent = anchor_by_group.get(group)
        score = _navigation_view_score(view)
        incumbent_score = _navigation_view_score(incumbent) if incumbent else (-1, "")
        if (
            incumbent is None
            or score[0] > incumbent_score[0]
            or (score[0] == incumbent_score[0] and score[1] < incumbent_score[1])
        ):
            anchor_by_group[group] = view

    aggregates: Dict[tuple[str, str], Dict[str, Any]] = {}
    for edge in edges:
        source = edge.get("from")
        target = edge.get("to")
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        source_view = view_by_id.get(source)
        target_view = view_by_id.get(target)
        if not source_view or not target_view:
            continue
        source_group = _navigation_group_id(source_view)
        target_group = _navigation_group_id(target_view)
        if source_group == target_group:
            continue
        source_anchor = anchor_by_group.get(source_group)
        target_anchor = anchor_by_group.get(target_group)
        if not source_anchor or not target_anchor:
            continue
        source_anchor_id = source_anchor.get("id")
        target_anchor_id = target_anchor.get("id")
        if not isinstance(source_anchor_id, str) or not isinstance(target_anchor_id, str):
            continue
        key = (source_group, target_group)
        record = aggregates.get(key)
        if record is None:
            record = {
                "group_flow_key": _navigation_group_flow_key(source_group, target_group),
                "source_group": source_group,
                "target_group": target_group,
                "source_anchor_view_id": source_anchor_id,
                "target_anchor_view_id": target_anchor_id,
                "edge_count": 0,
                "evidence_count": 0,
                "presentation_roles": {
                    "pathway": 0,
                    "membership": 0,
                    "fallback": 0,
                },
                "_relation_counts": Counter(),
                "_sample_edges": [],
            }
            aggregates[key] = record
        record["edge_count"] += 1
        if edge.get("evidence_refs"):
            record["evidence_count"] += 1
        mechanism = edge.get("mechanism") if isinstance(edge.get("mechanism"), str) else "unknown"
        role = edge.get("presentation_role") if isinstance(edge.get("presentation_role"), str) else None
        if role not in NAVIGATION_EDGE_PRESENTATION_ROLES:
            role = _navigation_edge_presentation_role(mechanism)
        record["presentation_roles"][role] += 1
        record["_relation_counts"][mechanism] += 1
        if len(record["_sample_edges"]) < NAVIGATION_GROUP_FLOW_SAMPLE_LIMIT:
            sample = _navigation_edge_sample(edge, view_by_id)
            if sample is not None:
                record["_sample_edges"].append(sample)

    flows: List[Dict[str, Any]] = []
    for record in aggregates.values():
        relation_counts = record.pop("_relation_counts")
        sample_edges = record.pop("_sample_edges")
        dominant_relation = _navigation_dominant_relation(relation_counts)
        dominant_meta = _navigation_edge_mechanism_meta(dominant_relation)
        record["dominant_relation"] = dominant_relation
        record["dominant_relation_label"] = dominant_meta.get("label")
        record["relation_counts"] = _sorted_counter_payload(relation_counts)
        record["sample_edges"] = sample_edges
        record["sample_limit"] = NAVIGATION_GROUP_FLOW_SAMPLE_LIMIT
        record["sample_omitted_count"] = max(
            0,
            int(record.get("edge_count") or 0) - len(sample_edges),
        )
        flows.append(record)

    flows.sort(
        key=lambda row: (
            -int(row.get("edge_count") or 0),
            str(row.get("source_group") or ""),
            str(row.get("target_group") or ""),
        )
    )
    return flows[:NAVIGATION_GROUP_FLOW_LIMIT]


def _navigation_edge_evidence_coverage(edge_count: int, edge_evidence_count: int) -> str:
    if edge_count <= 0:
        return "not_applicable"
    if edge_evidence_count <= 0:
        return "none"
    if edge_evidence_count >= edge_count:
        return "full"
    return "partial"


def _navigation_graph_shape_issues(raw: Mapping[str, Any]) -> List[str]:
    issues: List[str] = []
    if not isinstance(raw.get("views"), list):
        issues.append("views_not_array")
    if not isinstance(raw.get("edges"), list):
        issues.append("edges_not_array")
    counts = raw.get("counts")
    if counts is not None and not isinstance(counts, Mapping):
        issues.append("counts_not_object")
    return issues


def _navigation_graph_read_model_contract(
    *,
    repo_root: Path,
    raw: Mapping[str, Any],
    views: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    counts: Mapping[str, Any],
    freshness: Mapping[str, Any],
) -> Dict[str, Any]:
    node_count = len(views)
    edge_count = len(edges)
    capture_count = int(counts.get("capture_rows") or 0)
    overlay_count = int(counts.get("overlays") or 0)
    drift_count = int(counts.get("drift_signals") or 0)
    evidence_ref_count = 0
    edge_evidence_count = 0
    for edge in edges:
        refs = [item for item in (edge.get("evidence_refs") or []) if isinstance(item, str)]
        if refs:
            edge_evidence_count += 1
            evidence_ref_count += len(refs)

    invalid_reasons = _navigation_graph_shape_issues(raw)
    projection_status_raw = (
        raw.get("projection_status")
        if isinstance(raw.get("projection_status"), Mapping)
        else {}
    )
    fallback_reason = (
        str(
            raw.get("fallback_reason")
            or raw.get("fallback_provenance")
            or projection_status_raw.get("fallback_reason")
            or ""
        ).strip()
        or None
    )
    stale_reason = None
    explicit_stale_reason = (
        str(raw.get("stale_reason") or projection_status_raw.get("stale_reason") or "").strip()
        or None
    )
    if explicit_stale_reason:
        stale_reason = explicit_stale_reason
    elif projection_status_raw.get("status") == "stale":
        stale_reason = (
            str(projection_status_raw.get("reason") or "").strip()
            or "navigation_graph_projection_marked_stale"
        )

    if invalid_reasons:
        state = "invalid"
    elif fallback_reason:
        state = "fallback"
    elif stale_reason:
        state = "stale"
    elif node_count == 0 and edge_count == 0:
        state = "resting"
    else:
        state = "populated"

    contract: Dict[str, Any] = {
        "schema_version": "navigation_graph_read_model_contract_v1",
        "contract_id": NAVIGATION_READ_MODEL_CONTRACT_ID,
        "projection_id": NAVIGATION_READ_MODEL_PROJECTION_ID,
        "state": state,
        "generated_at": raw.get("generated_at") if isinstance(raw.get("generated_at"), str) else None,
        "source_mtime": _file_mtime(repo_root, FRONTEND_NAV_GRAPH_PATH),
        "source_path": FRONTEND_NAV_GRAPH_PATH,
        "projection_path": FRONTEND_NAV_GRAPH_PATH,
        "node_count": node_count,
        "view_count": node_count,
        "edge_count": edge_count,
        "capture_count": capture_count,
        "overlay_count": overlay_count,
        "drift_count": drift_count,
        "evidence_ref_count": evidence_ref_count,
        "edge_evidence_count": edge_evidence_count,
        "edge_evidence_coverage": _navigation_edge_evidence_coverage(edge_count, edge_evidence_count),
        "evidence_refs_supported": evidence_ref_count > 0,
        "route_ready": state == "populated",
        "freshness": dict(freshness),
    }
    if invalid_reasons:
        contract["invalid_reasons"] = invalid_reasons
        contract["invalid_reason"] = invalid_reasons[0]
    if fallback_reason:
        contract["fallback_reason"] = fallback_reason
    if stale_reason:
        contract["stale_reason"] = stale_reason
    return contract


def _condense_navigation_graph(repo_root: Path) -> Dict[str, Any] | None:
    raw = _safe_read_json(repo_root, FRONTEND_NAV_GRAPH_PATH)
    if not isinstance(raw, dict):
        return None

    semantic_layer = frontend_surface_contracts.load_semantic_layer(repo_root)
    semantic_by_id = {
        str(row.get("view_id")): row
        for row in (semantic_layer.get("views") or [])
        if isinstance(row, Mapping) and isinstance(row.get("view_id"), str)
    }
    raw_views_value = raw.get("views")
    raw_edges_value = raw.get("edges")
    views_raw = raw_views_value if isinstance(raw_views_value, list) else []
    edges_raw = raw_edges_value if isinstance(raw_edges_value, list) else []
    shell_counts: Counter[str] = Counter()
    station_counts: Counter[str] = Counter()
    adjacency: Dict[str, Dict[str, List[str]]] = {}
    views: List[Dict[str, Any]] = []
    capture_ready = 0
    declared_cul_de_sacs = 0
    effective_cul_de_sacs = 0
    utility_count = 0
    overlay_count = 0

    for entry in views_raw:
        if not isinstance(entry, dict):
            continue
        view_id = entry.get("id")
        if not isinstance(view_id, str) or not view_id:
            continue
        kind = entry.get("kind") if isinstance(entry.get("kind"), str) else "page"
        shell_group = entry.get("shell_group") if isinstance(entry.get("shell_group"), str) else None
        station_group = (
            entry.get("station_group") if isinstance(entry.get("station_group"), str) else None
        )
        route_aliases = [
            alias for alias in (entry.get("route_aliases") or []) if isinstance(alias, str)
        ]
        capture = entry.get("capture") if isinstance(entry.get("capture"), dict) else None
        cul_de_sac = entry.get("cul_de_sac") if isinstance(entry.get("cul_de_sac"), dict) else {}

        if shell_group:
            shell_counts[shell_group] += 1
        if station_group:
            station_counts[station_group] += 1
        if capture:
            capture_ready += 1
        if bool(cul_de_sac.get("declared")):
            declared_cul_de_sacs += 1
        if bool(cul_de_sac.get("effective")):
            effective_cul_de_sacs += 1
        if kind != "page":
            overlay_count += 1
        elif not shell_group:
            utility_count += 1

        adjacency[view_id] = {"outbound_ids": [], "inbound_ids": []}
        views.append(
            {
                "id": view_id,
                "kind": kind,
                "route": entry.get("route") if isinstance(entry.get("route"), str) else None,
                "entry_route": (
                    entry.get("entry_route")
                    if isinstance(entry.get("entry_route"), str)
                    else None
                ),
                "route_aliases": route_aliases,
                "label": entry.get("label") if isinstance(entry.get("label"), str) else view_id,
                "purpose": entry.get("purpose") if isinstance(entry.get("purpose"), str) else None,
                "shell_group": shell_group,
                "station_group": station_group,
                "station_lens_eligible": bool(entry.get("station_lens_eligible")),
                "overlay_of": (
                    entry.get("overlay_of") if isinstance(entry.get("overlay_of"), str) else None
                ),
                "cul_de_sac": {
                    "declared": bool(cul_de_sac.get("declared")),
                    "reason": (
                        cul_de_sac.get("reason")
                        if isinstance(cul_de_sac.get("reason"), str)
                        else None
                    ),
                    "effective": bool(cul_de_sac.get("effective")),
                },
                "capture": (
                    {
                        "slug": (
                            capture.get("slug") if isinstance(capture.get("slug"), str) else None
                        ),
                        "route": (
                            capture.get("route")
                            if isinstance(capture.get("route"), str)
                            else None
                        ),
                        "ready_selector": (
                            capture.get("ready_selector")
                            if isinstance(capture.get("ready_selector"), str)
                            else None
                        ),
                        "stabilize_ms": (
                            int(capture.get("stabilize_ms"))
                            if isinstance(capture.get("stabilize_ms"), (int, float))
                            else None
                        ),
                        "capture_group": (
                            capture.get("capture_group")
                            if isinstance(capture.get("capture_group"), str)
                            else None
                        ),
                        "full_page": (
                            capture.get("full_page")
                            if isinstance(capture.get("full_page"), bool)
                            else None
                        ),
                        "notes": (
                            capture.get("notes")
                            if isinstance(capture.get("notes"), str)
                            else None
                        ),
                        "bound_via": (
                            capture.get("bound_via")
                            if isinstance(capture.get("bound_via"), str)
                            else None
                        ),
                        "load_timing": _condense_capture_load_timing(
                            capture.get("load_timing")
                        ),
                    }
                    if capture
                    else None
                ),
                "semantic_health": _condense_frontend_semantic_row(
                    semantic_by_id.get(view_id),
                    view_id=view_id,
                    route=entry.get("entry_route") or entry.get("route"),
                ),
                "surface_audit": _condense_surface_audit_row(entry.get("surface_audit")),
                "fanout_count": int(entry.get("fanout_count") or 0),
                "fanin_count": int(entry.get("fanin_count") or 0),
                "pathway_count": int(entry.get("pathway_count") or 0),
                "pathway_fanout_count": int(entry.get("pathway_fanout_count") or 0),
                "pathway_fanin_count": int(entry.get("pathway_fanin_count") or 0),
            }
        )

    for edge in edges_raw:
        if not isinstance(edge, dict):
            continue
        source = edge.get("from")
        target = edge.get("to")
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        if source not in adjacency or target not in adjacency:
            continue
        adjacency[source]["outbound_ids"].append(target)
        adjacency[target]["inbound_ids"].append(source)

    for entry in adjacency.values():
        entry["outbound_ids"] = list(dict.fromkeys(entry["outbound_ids"]))
        entry["inbound_ids"] = list(dict.fromkeys(entry["inbound_ids"]))

    # Edge projection: the source navigation_graph.json ships every
    # extractor-derived edge with {from, to, mechanism}; emit them through
    # the world-model projection so frontend wayfinding can color by
    # relation type instead of falling back to group-derived edges.
    # Mechanism vocabulary lives in tools/meta/observability/frontend_nav_graph.py.
    edges: List[Dict[str, Any]] = []
    for edge in edges_raw:
        if not isinstance(edge, dict):
            continue
        source = edge.get("from")
        target = edge.get("to")
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        if source not in adjacency or target not in adjacency:
            continue
        mechanism = (
            edge.get("mechanism")
            if isinstance(edge.get("mechanism"), str)
            else "unknown"
        )
        meta = _navigation_edge_mechanism_meta(mechanism)
        presentation_role = _navigation_edge_presentation_role(mechanism)
        category = (
            edge.get("category") if isinstance(edge.get("category"), str) else meta["category"]
        )
        projected_edge: Dict[str, Any] = {
            "edge_key": _navigation_edge_key(source, target, mechanism, category),
            "from": source,
            "to": target,
            "mechanism": mechanism,
            "label": edge.get("label") if isinstance(edge.get("label"), str) else meta["label"],
            "category": category,
            "description": (
                edge.get("description")
                if isinstance(edge.get("description"), str)
                else meta["description"]
            ),
            "presentation_role": presentation_role,
            "rank": (
                int(edge.get("rank"))
                if isinstance(edge.get("rank"), (int, float)) and not isinstance(edge.get("rank"), bool)
                else meta["rank"]
            ),
            "weight": (
                float(edge.get("weight"))
                if isinstance(edge.get("weight"), (int, float)) and not isinstance(edge.get("weight"), bool)
                else meta["weight"]
            ),
        }
        group = edge.get("group")
        if isinstance(group, str):
            projected_edge["group"] = group
        evidence_refs = [
            item for item in (edge.get("evidence_refs") or []) if isinstance(item, str)
        ]
        if evidence_refs:
            projected_edge["evidence_refs"] = evidence_refs[:12]
        edges.append(projected_edge)

    group_flows = _build_navigation_group_flows(views, edges)
    relation_summary = _build_navigation_relation_summary(views, edges)
    counts = raw.get("counts") if isinstance(raw.get("counts"), dict) else {}
    freshness = compute_freshness(_file_mtime(repo_root, FRONTEND_NAV_GRAPH_PATH))
    read_model_contract = _navigation_graph_read_model_contract(
        repo_root=repo_root,
        raw=raw,
        views=views,
        edges=edges,
        counts=counts,
        freshness=freshness,
    )
    projection_status: Dict[str, Any] = {
        "status": read_model_contract["state"],
        "contract_id": read_model_contract["contract_id"],
        "path": FRONTEND_NAV_GRAPH_PATH,
    }
    for reason_key in ("invalid_reason", "fallback_reason", "stale_reason"):
        reason = read_model_contract.get(reason_key)
        if isinstance(reason, str) and reason:
            projection_status["reason"] = reason
            break
    compression = raw.get("compression") if isinstance(raw.get("compression"), dict) else {}
    surface_relation_audit_raw = (
        raw.get("surface_relation_audit")
        if isinstance(raw.get("surface_relation_audit"), Mapping)
        else {}
    )
    audit_surfaces = (
        surface_relation_audit_raw.get("surfaces")
        if isinstance(surface_relation_audit_raw.get("surfaces"), list)
        else []
    )
    audit_clusters = (
        surface_relation_audit_raw.get("clusters")
        if isinstance(surface_relation_audit_raw.get("clusters"), Mapping)
        else {}
    )
    pathway_audit_raw = raw.get("pathway_audit") if isinstance(raw.get("pathway_audit"), Mapping) else {}
    pathway_audit = {
        "contract": pathway_audit_raw.get("contract"),
        "status": pathway_audit_raw.get("status"),
        "presentation_role": pathway_audit_raw.get("presentation_role"),
        "pathway_edge_count": int(pathway_audit_raw.get("pathway_edge_count") or 0),
        "explicit_pathway_count": int(pathway_audit_raw.get("explicit_pathway_count") or 0),
        "derived_pathway_count": int(pathway_audit_raw.get("derived_pathway_count") or 0),
        "zero_pathway_view_count": int(pathway_audit_raw.get("zero_pathway_view_count") or 0),
        "zero_substantive_pathway_view_count": int(
            pathway_audit_raw.get("zero_substantive_pathway_view_count") or 0
        ),
        "allowed_zero_pathway_view_count": int(
            pathway_audit_raw.get("allowed_zero_pathway_view_count") or 0
        ),
        "allowed_zero_pathway_view_ids": [
            item for item in (pathway_audit_raw.get("allowed_zero_pathway_view_ids") or [])
            if isinstance(item, str)
        ],
        "zero_substantive_pathway_views": [
            row for row in (pathway_audit_raw.get("zero_substantive_pathway_views") or [])
            if isinstance(row, Mapping)
        ],
        "allowed_zero_pathway_views": [
            row for row in (pathway_audit_raw.get("allowed_zero_pathway_views") or [])
            if isinstance(row, Mapping)
        ],
    }
    drift_preview: List[Dict[str, Any]] = []
    for signal in raw.get("drift_signals") or []:
        if not isinstance(signal, dict):
            continue
        evidence = signal.get("evidence") if isinstance(signal.get("evidence"), dict) else None
        drift_preview.append(
            {
                "kind": signal.get("kind") if isinstance(signal.get("kind"), str) else "unknown",
                "surface": (
                    signal.get("surface") if isinstance(signal.get("surface"), str) else None
                ),
                "label": signal.get("label") if isinstance(signal.get("label"), str) else None,
                "pathway_count": (
                    int(signal.get("pathway_count"))
                    if isinstance(signal.get("pathway_count"), (int, float))
                    and not isinstance(signal.get("pathway_count"), bool)
                    else None
                ),
                "contract": (
                    signal.get("contract") if isinstance(signal.get("contract"), str) else None
                ),
                "route": signal.get("route") if isinstance(signal.get("route"), str) else None,
                "slug": signal.get("slug") if isinstance(signal.get("slug"), str) else None,
                "capture_slug": (
                    signal.get("capture_slug")
                    if isinstance(signal.get("capture_slug"), str)
                    else None
                ),
                "declared_route": (
                    signal.get("declared_route")
                    if isinstance(signal.get("declared_route"), str)
                    else None
                ),
                "element": (
                    signal.get("element") if isinstance(signal.get("element"), str) else None
                ),
                "evidence": (
                    {
                        "file": evidence.get("file"),
                        "line": evidence.get("line"),
                    }
                    if isinstance(evidence.get("file"), str)
                    else None
                ),
            }
        )
        if len(drift_preview) >= 5:
            break

    return {
        "schema_version": raw.get("schema_version"),
        "generated_at": raw.get("generated_at"),
        "edge_grammar_contract": NAVIGATION_EDGE_GRAMMAR_CONTRACT,
        "edge_explainability_contract": NAVIGATION_EDGE_EXPLAINABILITY_CONTRACT,
        "edge_addressability_contract": NAVIGATION_EDGE_ADDRESSABILITY_CONTRACT,
        "projection_status": projection_status,
        "read_model_contract": read_model_contract,
        "counts": {
            "pages": int(counts.get("pages") or 0),
            "overlays": int(counts.get("overlays") or 0),
            "edges": int(counts.get("edges") or 0),
            "pathway_edges": int(counts.get("pathway_edges") or 0),
            "explicit_pathway_edges": int(counts.get("explicit_pathway_edges") or 0),
            "derived_pathway_edges": int(counts.get("derived_pathway_edges") or 0),
            "zero_substantive_pathway_views": int(
                counts.get("zero_substantive_pathway_views") or 0
            ),
            "allowed_zero_pathway_views": int(counts.get("allowed_zero_pathway_views") or 0),
            "cul_de_sacs_effective": int(counts.get("cul_de_sacs_effective") or 0),
            "cul_de_sacs_declared": int(counts.get("cul_de_sacs_declared") or 0),
            "routes_declared": int(counts.get("routes_declared") or 0),
            "redirects": int(counts.get("redirects") or 0),
            "capture_rows": int(counts.get("capture_rows") or 0),
            "timed_capture_rows": int(counts.get("timed_capture_rows") or 0),
            "drift_signals": int(counts.get("drift_signals") or 0),
        },
        "compression": {
            "one_line": (
                compression.get("one_line")
                if isinstance(compression.get("one_line"), str)
                else None
            ),
            "five_line": [
                line for line in (compression.get("five_line") or []) if isinstance(line, str)
            ],
        },
        "group_counts": {
            "shell": dict(shell_counts),
            "station": dict(station_counts),
            "capture_ready": capture_ready,
            "declared_cul_de_sacs": declared_cul_de_sacs,
            "effective_cul_de_sacs": effective_cul_de_sacs,
            "utility": utility_count,
            "overlays": overlay_count,
        },
        "semantic_layer": {
            "schema_version": semantic_layer.get("schema_version"),
            "authored_at": semantic_layer.get("authored_at"),
            "row_count": len(semantic_by_id),
            "check": frontend_surface_contracts.semantic_check(repo_root),
        },
        "surface_relation_audit": {
            "schema_version": surface_relation_audit_raw.get("schema_version"),
            "generated_at": (
                surface_relation_audit_raw.get("generated_at")
                if isinstance(surface_relation_audit_raw.get("generated_at"), str)
                else None
            ),
            "surface_count": len([row for row in audit_surfaces if isinstance(row, Mapping)]),
            "clusters": audit_clusters,
        },
        "views": views,
        "adjacency": adjacency,
        "edges": edges,
        "pathway_audit": pathway_audit,
        "relation_summary": relation_summary,
        "group_flows": group_flows,
        "drift_preview": drift_preview,
        "freshness": freshness,
    }


def _load_frontend_navigation_mission_control(repo_root: Path) -> Dict[str, Any]:
    raw = _safe_read_json(repo_root, FRONTEND_NAV_MISSION_CONTROL_PATH)
    freshness = compute_freshness(_file_mtime(repo_root, FRONTEND_NAV_MISSION_CONTROL_PATH))
    if not isinstance(raw, dict):
        return {
            "contract": FRONTEND_NAV_MISSION_CONTROL_CONTRACT,
            "available": False,
            "path": FRONTEND_NAV_MISSION_CONTROL_PATH,
            "freshness": freshness,
            "blocker": "mission_control_packet_missing_or_invalid",
        }
    packet = dict(raw)
    packet["available"] = packet.get("contract") == FRONTEND_NAV_MISSION_CONTROL_CONTRACT
    packet["path"] = FRONTEND_NAV_MISSION_CONTROL_PATH
    packet["freshness"] = freshness
    return packet


def _condense_capture_load_timing(raw: Any) -> Dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None

    def _int_or_none(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return int(value)
        return None

    def _str_or_none(value: Any) -> str | None:
        return value if isinstance(value, str) else None

    return {
        "sample_count": _int_or_none(raw.get("sample_count")),
        "captured_sample_count": _int_or_none(raw.get("captured_sample_count")),
        "latest_status": _str_or_none(raw.get("latest_status")),
        "latest_load_ms": _int_or_none(raw.get("latest_load_ms")),
        "latest_ready_ms": _int_or_none(raw.get("latest_ready_ms")),
        "latest_run_stamp": _str_or_none(raw.get("latest_run_stamp")),
        "latest_engine": _str_or_none(raw.get("latest_engine")),
        "latest_viewport_slug": _str_or_none(raw.get("latest_viewport_slug")),
        "latest_output_path": _str_or_none(raw.get("latest_output_path")),
        "latest_preload_output_path": _str_or_none(raw.get("latest_preload_output_path")),
        "p50_load_ms": _int_or_none(raw.get("p50_load_ms")),
        "p95_load_ms": _int_or_none(raw.get("p95_load_ms")),
        "min_load_ms": _int_or_none(raw.get("min_load_ms")),
        "max_load_ms": _int_or_none(raw.get("max_load_ms")),
        "avg_load_ms": _int_or_none(raw.get("avg_load_ms")),
    }


LAB_ORACLE_EVOLVE_ARTIFACTS: Dict[str, Tuple[str, ...]] = {
    "lab_cp2": ("lab_director", "oracle_subject_lab_director"),
    "prediction_reconciliation": ("prediction_reconciliation", "oracle_truth_diff_equity"),
    "realized_hindsight_brief": ("realized_hindsight_brief", "oracle_truth_map"),
    "cp2_critique": ("cp2_critique", "oracle_attribution_map"),
    "ideal_cp2": ("ideal_cp2", "oracle_cp2_emitter"),
    "subject_index": ("oracle_subject_index",),
    "truth_diff_macro": ("oracle_truth_diff_macro",),
    "evolve_delta_report": ("evolve_delta_report",),
    "evolve_patch_payload": ("evolve_patch_payload",),
    "evolve_input_readiness": ("evolve_input_readiness",),
}


def _artifact_payload_data(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return payload


def _load_lab_oracle_artifact(
    artifacts_dir: Path,
    candidates: Sequence[str],
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[Path]]:
    for artifact_id in candidates:
        path = artifacts_dir / f"{artifact_id}.json"
        payload = _safe_read_json_path(path)
        if isinstance(payload, dict):
            return payload, artifact_id, path
    return None, None, None


def _compact_artifact_presence(artifacts_dir: Path, canonical_id: str) -> Dict[str, Any]:
    payload, source_id, source_path = _load_lab_oracle_artifact(
        artifacts_dir,
        LAB_ORACLE_EVOLVE_ARTIFACTS[canonical_id],
    )
    data = _artifact_payload_data(payload)
    metadata = payload.get("metadata") if isinstance(payload, dict) else None
    return {
        "artifact_id": canonical_id,
        "present": payload is not None,
        "source_artifact_id": source_id,
        "path": str(source_path) if source_path else None,
        "status": str(payload.get("status") or "").strip() if isinstance(payload, dict) else None,
        "data": data,
        "metadata": metadata if isinstance(metadata, dict) else {},
    }


def _run_runtime_context(run_dir: Path | None) -> Dict[str, Any]:
    if run_dir is None:
        return {}
    payload = _safe_read_json_path(run_dir / "runtime_context.json")
    return payload if isinstance(payload, dict) else {}


def _is_feed_runtime(run_dir: Path | None, runtime_context: Mapping[str, Any]) -> bool:
    if run_dir is not None and run_dir.name.startswith("FEEDS_"):
        return True
    return (
        str(runtime_context.get("mission_name") or "").strip() == "feeds"
        or str(runtime_context.get("subject_group") or "").strip() == "feeds"
    )


def _feed_fire_point_from_run_id(run_id: str) -> Optional[str]:
    lowered = run_id.lower()
    for suffix in ("post_close_60", "afternoon_mid", "close", "open"):
        if lowered.endswith(f"_{suffix}"):
            return suffix
    return None


def _feed_schedule_fields(run_dir: Path | None, runtime_context: Mapping[str, Any]) -> Dict[str, Any]:
    schedule = runtime_context.get("schedule") if isinstance(runtime_context.get("schedule"), Mapping) else {}
    horizon = runtime_context.get("horizon") if isinstance(runtime_context.get("horizon"), Mapping) else {}
    run_id = run_dir.name if run_dir is not None else ""
    target_time_utc = (
        schedule.get("target_time_utc")
        or runtime_context.get("time_anchor")
        or runtime_context.get("as_of")
        or horizon.get("target_time_iso")
    )
    return {
        "capture_lag_seconds": runtime_context.get("capture_lag_seconds"),
        "fire_point": schedule.get("fire_point") or _feed_fire_point_from_run_id(run_id),
        "market_date": schedule.get("market_date") or str(target_time_utc or "")[:10] or None,
        "target_time_market": schedule.get("target_time_market") or horizon.get("target_time_et"),
        "target_time_utc": target_time_utc,
    }


def _feed_readiness_compact(artifacts_dir: Path, *, run_dir: Path | None = None) -> Dict[str, Any]:
    path = artifacts_dir / "feed_readiness_summary.json"
    runtime_context = _run_runtime_context(run_dir)
    run_present = _is_feed_runtime(run_dir, runtime_context)
    schedule_fields = _feed_schedule_fields(run_dir, runtime_context)
    payload = _safe_read_json_path(path)
    if not isinstance(payload, dict):
        freshness_anchor = str(schedule_fields.get("target_time_utc") or "") or (
            _path_mtime_iso(run_dir) if run_dir is not None else None
        )
        blockers = (
            [
                {
                    "node_id": "feed_readiness_summary",
                    "status": "missing",
                    "reason": (
                        "Feed run directory exists, but artifacts/feed_readiness_summary.json "
                        "has not materialized."
                    ),
                    "dependencies": [],
                }
            ]
            if run_present
            else []
        )
        return {
            "present": False,
            "run_present": run_present,
            "summary_present": False,
            "ready": False if run_present else None,
            "path": str(path),
            "target_count": 0,
            "status_counts": {"missing_summary": 1} if run_present else {},
            "blocker_count": len(blockers),
            "blockers": blockers,
            "validation": {},
            "runtime_context": runtime_context,
            "freshness": compute_freshness(freshness_anchor),
            **schedule_fields,
        }
    blockers = [item for item in payload.get("blockers") or [] if isinstance(item, dict)]
    payload_runtime_context = (
        payload.get("runtime_context") if isinstance(payload.get("runtime_context"), dict) else {}
    )
    if payload_runtime_context:
        runtime_context = payload_runtime_context
        schedule_fields = _feed_schedule_fields(run_dir, runtime_context)
    freshness_anchor = (
        schedule_fields.get("target_time_utc")
        or payload.get("generated_at")
        or _path_mtime_iso(path)
    )
    return {
        "present": True,
        "run_present": True,
        "summary_present": True,
        "ready": bool(payload.get("ready")),
        "path": str(path),
        "target_count": int(payload.get("target_count") or 0),
        "status_counts": dict(payload.get("status_counts") or {}),
        "blocker_count": len(blockers),
        "blockers": blockers[:5],
        "validation": payload.get("validation") if isinstance(payload.get("validation"), dict) else {},
        "runtime_context": runtime_context,
        "freshness": compute_freshness(str(freshness_anchor) if freshness_anchor else None),
        **schedule_fields,
    }


def _parse_iso_dt(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _latest_market_timeline_row(repo_root: Path) -> Dict[str, Any] | None:
    path = repo_root / "state" / "metabolism" / "market_timeline.jsonl"
    if not path.exists():
        return None
    try:
        with path.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(size - 262144, 0))
            text = fh.read().decode("utf-8", errors="ignore")
    except Exception:
        return None
    for line in reversed([row.strip() for row in text.splitlines() if row.strip()]):
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            tickers = payload.get("tickers") if isinstance(payload.get("tickers"), dict) else {}
            ticker_preview = []
            for symbol in ("SPY", "QQQ", "DIA", "IWM", "^VIX"):
                row = tickers.get(symbol)
                if not isinstance(row, dict):
                    continue
                ticker_preview.append(
                    {
                        "symbol": symbol,
                        "label": row.get("label"),
                        "status": row.get("status"),
                        "price": row.get("price"),
                        "change_pct": row.get("change_pct"),
                    }
                )
            captured = _parse_iso_dt(payload.get("captured_at_utc"))
            target = _parse_iso_dt(payload.get("target_time_utc"))
            lag_seconds = int((captured - target).total_seconds()) if captured and target else None
            return {
                "present": True,
                "path": str(path),
                "snapshot_key": payload.get("snapshot_key"),
                "fire_point": payload.get("fire_point"),
                "market_date": payload.get("market_date"),
                "capture_status": payload.get("capture_status"),
                "captured_at_utc": payload.get("captured_at_utc"),
                "target_time_utc": payload.get("target_time_utc"),
                "target_time_market": payload.get("target_time_market"),
                "capture_lag_seconds": lag_seconds,
                "ticker_success_count": payload.get("ticker_success_count"),
                "ticker_error_count": payload.get("ticker_error_count"),
                "error_summary": payload.get("error_summary") or [],
                "ticker_preview": ticker_preview,
            }
    return None


def _market_feed_table_candidates(data: Any) -> List[Tuple[str, List[Any], List[Any]]]:
    tables: List[Tuple[str, List[Any], List[Any]]] = []

    def visit(value: Any, path: str, depth: int) -> None:
        if depth > 3 or not isinstance(value, Mapping):
            return
        columns = value.get("columns")
        rows = value.get("rows")
        if isinstance(columns, list) and isinstance(rows, list):
            tables.append((path, columns, rows))
        for key, child in value.items():
            if isinstance(child, Mapping):
                child_path = f"{path}.{key}" if path else str(key)
                visit(child, child_path, depth + 1)

    visit(data, "", 0)
    tables.sort(key=lambda item: len(item[2]), reverse=True)
    return tables


def _market_feed_compact_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, str):
        text = value.strip()
        return text if len(text) <= 120 else f"{text[:117]}..."
    return str(value)[:120]


def _market_feed_row_preview(columns: Sequence[Any], rows: Sequence[Any]) -> List[Dict[str, Any]]:
    selected_columns = [str(col) for col in list(columns)[:_MARKET_FEED_SPECIMEN_COLUMN_LIMIT]]
    previews: List[Dict[str, Any]] = []
    for row in list(rows)[:_MARKET_FEED_SPECIMEN_ROW_LIMIT]:
        if isinstance(row, Sequence) and not isinstance(row, (str, bytes, bytearray)):
            previews.append(
                {
                    column: _market_feed_compact_value(row[index] if index < len(row) else None)
                    for index, column in enumerate(selected_columns)
                }
            )
        elif isinstance(row, Mapping):
            previews.append(
                {
                    column: _market_feed_compact_value(row.get(column))
                    for column in selected_columns
                    if column in row
                }
            )
    return previews


def _market_feed_table_shape(
    tables: Sequence[Tuple[str, List[Any], List[Any]]],
) -> Dict[str, Any]:
    total_rows = sum(len(rows) for _path, _columns, rows in tables)
    column_names = sorted({str(column) for _path, columns, _rows in tables for column in columns})
    metric_columns = [column for column in column_names if column in _MARKET_FEED_METRIC_COLUMNS]

    numeric_cells = 0
    observed_cells = 0
    for _path, columns, rows in tables:
        for row in rows[:50]:
            if not isinstance(row, Sequence) or isinstance(row, (str, bytes, bytearray)):
                continue
            for index, _column in enumerate(columns):
                if index >= len(row):
                    continue
                value = row[index]
                if value is None:
                    continue
                observed_cells += 1
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    numeric_cells += 1

    return {
        "table_count": len(tables),
        "row_count": total_rows,
        "column_count": len(column_names),
        "metric_columns": metric_columns[:12],
        "numeric_cell_count_sample": numeric_cells,
        "observed_cell_count_sample": observed_cells,
    }


def _market_feed_diagnostics_summary(diagnostics: Mapping[str, Any]) -> Dict[str, Any]:
    keys = (
        "input_rows",
        "output_rows",
        "dropped_rows",
        "fetch_success_count",
        "fetch_failure_count",
        "fetch_success_rate",
        "batch_download_ok",
        "batch_ticker_count",
        "emitted_rows",
        "emitted_topics",
    )
    summary = {key: diagnostics.get(key) for key in keys if key in diagnostics}
    fred = diagnostics.get("fred")
    if isinstance(fred, Mapping):
        for key in (
            "valid_items",
            "total_series",
            "fetched_count",
            "cached_used",
            "fetch_success_count",
            "fetch_failure_count",
            "fetch_success_rate",
            "network_warn_count",
        ):
            if key in fred:
                summary[f"fred_{key}"] = fred.get(key)
    warnings = diagnostics.get("warnings")
    if isinstance(warnings, list):
        summary["warning_count"] = len(warnings)
        summary["warning_preview"] = [str(item)[:120] for item in warnings[:3]]
    return summary


def _market_feed_sidecar_summary(metadata: Mapping[str, Any]) -> List[Dict[str, Any]]:
    sidecars = metadata.get("sidecars")
    if not isinstance(sidecars, Mapping):
        return []
    rows: List[Dict[str, Any]] = []
    for key, payload in sidecars.items():
        if not isinstance(payload, Mapping):
            rows.append({"key": str(key), "type": type(payload).__name__})
            continue
        row: Dict[str, Any] = {
            "key": str(key),
            "schema_version": payload.get("schema_version"),
            "row_count": payload.get("row_count"),
        }
        distribution = payload.get("state_distribution") or payload.get("lifecycle_distribution")
        if isinstance(distribution, Mapping):
            row["state_distribution"] = dict(distribution)
        diagnostics = payload.get("diagnostics")
        if isinstance(diagnostics, Mapping):
            row["diagnostics"] = {
                key: diagnostics.get(key)
                for key in (
                    "configured_count",
                    "emitted_count",
                    "configured_not_emitted_count",
                    "missing_price_count",
                )
                if key in diagnostics
            }
        rows.append(row)
    return rows


def _compact_market_feed_artifact(
    artifacts_dir: Path,
    *,
    node_id: str,
    artifact_name: Any,
) -> Dict[str, Any]:
    artifact_file = str(artifact_name or f"{node_id}.json").strip()
    artifact_path = artifacts_dir / artifact_file
    payload = _safe_read_json_path(artifact_path)
    if not isinstance(payload, dict):
        return {
            "present": False,
            "path": str(artifact_path),
            "reason": "artifact_missing_or_unreadable",
        }

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
    data = payload.get("data")
    tables = _market_feed_table_candidates(data)
    primary_path, primary_columns, primary_rows = tables[0] if tables else ("", [], [])
    quality = metadata.get("quality") if isinstance(metadata.get("quality"), Mapping) else {}
    diagnostics = metadata.get("diagnostics") if isinstance(metadata.get("diagnostics"), Mapping) else {}
    return {
        "present": True,
        "path": str(artifact_path),
        "status": payload.get("status") or metadata.get("status"),
        "tool": metadata.get("tool"),
        "as_of": metadata.get("as_of") or metadata.get("timestamp_iso"),
        "items_count": metadata.get("items_count"),
        "data_schema_version": metadata.get("data_schema_version"),
        "quality": {
            "tone": quality.get("tone"),
            "reason_count": len(quality.get("reasons") or []) if isinstance(quality.get("reasons"), list) else 0,
            "blocked_metric_count": (
                len(quality.get("blocked_metrics") or [])
                if isinstance(quality.get("blocked_metrics"), list)
                else 0
            ),
        }
        if quality
        else None,
        "diagnostics": _market_feed_diagnostics_summary(diagnostics),
        "sidecar_keys": sorted(str(key) for key in (metadata.get("sidecars") or {}).keys())
        if isinstance(metadata.get("sidecars"), Mapping)
        else [],
        "sidecars": _market_feed_sidecar_summary(metadata),
        "data_shape": _market_feed_table_shape(tables),
        "primary_table_path": primary_path or None,
        "tables": [
            {"path": path or "data", "row_count": len(rows), "column_count": len(columns)}
            for path, columns, rows in list(tables)[:_MARKET_FEED_TABLE_LIMIT]
        ],
        "specimen_rows": _market_feed_row_preview(primary_columns, primary_rows),
    }


def _market_feed_artifact_only_rows(artifacts_dir: Path) -> List[Dict[str, Any]]:
    feeds: List[Dict[str, Any]] = []
    for node_id in _MARKET_FEED_TARGET_LABELS:
        artifact_name = f"{node_id}.json"
        artifact_path = artifacts_dir / artifact_name
        if not artifact_path.exists():
            continue
        artifact_summary = _compact_market_feed_artifact(
            artifacts_dir,
            node_id=node_id,
            artifact_name=artifact_name,
        )
        quality = (
            artifact_summary.get("quality")
            if isinstance(artifact_summary.get("quality"), Mapping)
            else {}
        )
        quality_tone = str(quality.get("tone") or "").strip()
        reason = "feed_readiness_summary_missing; artifact observed"
        if quality_tone:
            reason = f"{reason}; quality_tone={quality_tone}"
        feeds.append(
            {
                "node_id": node_id,
                "lane": _MARKET_FEED_TARGET_LABELS.get(node_id, node_id),
                "status": artifact_summary.get("status") or "artifact_observed",
                "reason": reason,
                "ready": False,
                "artifact": artifact_name,
                "dependencies": [],
                "artifact_summary": artifact_summary,
            }
        )
    return feeds


def _compact_market_feed_run(run_dir: Path) -> Optional[Dict[str, Any]]:
    artifacts_dir = run_dir / "artifacts"
    readiness = _feed_readiness_compact(artifacts_dir, run_dir=run_dir)
    payload = _safe_read_json_path(artifacts_dir / "feed_readiness_summary.json")
    if not isinstance(payload, dict) and not readiness.get("run_present"):
        return None
    feeds = []
    payload_map = payload if isinstance(payload, dict) else {}
    for row in payload_map.get("feeds") or []:
        if not isinstance(row, dict):
            continue
        node_id = str(row.get("node_id") or "").strip()
        feeds.append(
            {
                "node_id": node_id,
                "lane": _MARKET_FEED_TARGET_LABELS.get(node_id, node_id),
                "status": row.get("status") or "unknown",
                "reason": row.get("reason") or "",
                "ready": bool(row.get("ready")),
                "artifact": row.get("artifact"),
                "dependencies": list(row.get("dependencies") or []),
                "artifact_summary": _compact_market_feed_artifact(
                    artifacts_dir,
                    node_id=node_id,
                    artifact_name=row.get("artifact"),
                ),
            }
        )
    if not feeds and not isinstance(payload, dict):
        feeds = _market_feed_artifact_only_rows(artifacts_dir)
    runtime_context = (
        readiness.get("runtime_context") if isinstance(readiness.get("runtime_context"), dict) else {}
    )
    validation = readiness.get("validation") if isinstance(readiness.get("validation"), dict) else {}
    return {
        "run_id": str(payload_map.get("run_id") or run_dir.name),
        "run_dir": str(run_dir),
        "modified_at": _run_modified_at(run_dir),
        "summary_present": bool(readiness.get("summary_present")),
        "ready": bool(readiness.get("ready")),
        "target_count": int(readiness.get("target_count") or len(feeds)),
        "ready_count": sum(1 for row in feeds if row.get("ready")),
        "status_counts": dict(readiness.get("status_counts") or {}),
        "blocker_count": int(readiness.get("blocker_count") or 0),
        "blockers": list(readiness.get("blockers") or [])[:8],
        "feeds": feeds,
        "validation": validation,
        "runtime_context": runtime_context,
        "capture_lag_seconds": readiness.get("capture_lag_seconds"),
        "fire_point": readiness.get("fire_point"),
        "market_date": readiness.get("market_date"),
        "target_time_market": readiness.get("target_time_market"),
        "target_time_utc": readiness.get("target_time_utc"),
        "freshness": readiness.get("freshness"),
        "summary_path": str(artifacts_dir / "feed_readiness_summary.json"),
    }


def _load_market_clock_runtime(repo_root: Path) -> Dict[str, Any]:
    try:
        conn = _metabolism_store.connect(repo_root)
    except Exception as exc:
        return {
            "schema": "market_clock_runtime_v1",
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "next_fire": None,
            "queued_jobs": [],
            "running_jobs": [],
            "latest_snapshot": None,
        }
    try:
        payload = _market_clock.build_market_projection(conn, daemon_running=None)
        payload["available"] = True
        return payload
    except Exception as exc:
        return {
            "schema": "market_clock_runtime_v1",
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "next_fire": None,
            "queued_jobs": [],
            "running_jobs": [],
            "latest_snapshot": None,
        }
    finally:
        conn.close()


def load_market_feeds_snapshot(repo_root: Path, limit: int = 24) -> Dict[str, Any]:
    """Read-only market-feeds snapshot for the cockpit market tile.

    Cold builds walk state/runs/* and stat each subdir (~500 ms).
    Wrapped in swr_get keyed by (repo_root, limit) so the cockpit cold
    path doesn't pay that wall on every snapshot rebuild. ttl_s=10 mirrors
    the world-model snapshot freshness; deepcopy on read keeps the
    cache mutation-safe. Direct callers retain the live path through
    _uncached_load_market_feeds_snapshot if they need an immediate
    rebuild.
    """
    return swr_get(
        "market_feeds_snapshot",
        (str(repo_root.resolve()), int(limit)),
        lambda: _uncached_load_market_feeds_snapshot(repo_root, limit),
        ttl_s=10.0,
    )


def _uncached_load_market_feeds_snapshot(repo_root: Path, limit: int = 24) -> Dict[str, Any]:
    runs_dir = repo_root / "state" / "runs"
    rows: List[Dict[str, Any]] = []
    if runs_dir.exists():
        run_dirs = [path for path in runs_dir.iterdir() if path.is_dir()]
        run_dirs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        for run_dir in run_dirs:
            row = _compact_market_feed_run(run_dir)
            if row:
                rows.append(row)
            if len(rows) >= limit:
                break
    latest = rows[0] if rows else None
    latest_evidence_card: Dict[str, Any] | None = None
    latest_quant_presentation_mart: Dict[str, Any] | None = None
    latest_market_situation_graph: Dict[str, Any] | None = None
    latest_market_dashboard_read_model: Dict[str, Any] | None = None
    if latest and latest.get("run_id"):
        try:
            latest_evidence_card = _build_market_feed_run_evidence_card(
                repo_root,
                run_id=str(latest.get("run_id")),
            )
        except Exception as exc:
            latest_evidence_card = {
                "schema_version": "market_feed_run_evidence_card_v0",
                "run_id": latest.get("run_id"),
                "error": f"{type(exc).__name__}: {exc}",
                "safe_use_level": "evidence_card_unavailable",
                "evidence_use": {
                    "external_market_claims_allowed": False,
                    "trading_or_investment_claims_allowed": False,
                },
            }
        try:
            latest_quant_presentation_mart = _load_latest_quant_presentation_mart(
                repo_root,
                expected_run_id=str(latest.get("run_id")),
            )
        except Exception as exc:
            latest_quant_presentation_mart = {
                "schema_version": "quant_presentation_mart_v0_1",
                "run": {
                    "run_id": latest.get("run_id"),
                    "safe_use_level": "quant_mart_unavailable",
                },
                "projection_status": {
                    "status": "quant_mart_unavailable",
                    "reason": f"{type(exc).__name__}: {exc}",
                },
                "ranked_observations": [],
                "panel_manifest": [],
            }
        try:
            expected_fingerprint = (
                str(latest_quant_presentation_mart.get("source_fingerprint") or "")
                if isinstance(latest_quant_presentation_mart, Mapping)
                else ""
            )
            latest_market_situation_graph = _load_latest_market_situation_graph(
                repo_root,
                expected_run_id=str(latest.get("run_id")),
                expected_mart_fingerprint=expected_fingerprint or None,
            )
        except Exception as exc:
            latest_market_situation_graph = {
                "schema_version": "market_situation_graph_v0",
                "run_id": latest.get("run_id"),
                "projection_status": {
                    "status": "market_situation_graph_unavailable",
                    "reason": f"{type(exc).__name__}: {exc}",
                },
                "situations": [],
                "entities": [],
                "edges": [],
                "validation_summary": {"situation_count": 0},
            }
        try:
            graph_status = (
                ((latest_market_situation_graph.get("projection_status") or {}).get("status"))
                if isinstance(latest_market_situation_graph, Mapping)
                and isinstance(latest_market_situation_graph.get("projection_status"), Mapping)
                else None
            )
            expected_graph_fingerprint = (
                _fingerprint_market_situation_graph(latest_market_situation_graph)
                if graph_status == "in_sync" and isinstance(latest_market_situation_graph, Mapping)
                else None
            )
            latest_market_dashboard_read_model = _load_latest_market_dashboard_read_model(
                repo_root,
                expected_run_id=str(latest.get("run_id")),
                expected_graph_fingerprint=expected_graph_fingerprint,
            )
        except Exception as exc:
            latest_market_dashboard_read_model = {
                "schema_version": "market_dashboard_read_model_v0",
                "run_id": latest.get("run_id"),
                "projection_status": {
                    "status": "market_dashboard_read_model_unavailable",
                    "reason": f"{type(exc).__name__}: {exc}",
                },
                "overview": {"situation_count": 0, "validated_signal_count": 0},
                "situation_queue": {"items": []},
            }
    latest_ticker = _latest_market_timeline_row(repo_root)
    market_clock = _load_market_clock_runtime(repo_root)
    latest_feeds = latest.get("feeds") if isinstance(latest, Mapping) else []
    latest_artifact_summaries = [
        feed.get("artifact_summary")
        for feed in latest_feeds
        if isinstance(feed, Mapping) and isinstance(feed.get("artifact_summary"), Mapping)
    ]
    summary = {
        "feed_runs": len(rows),
        "ready_runs": sum(1 for row in rows if row.get("ready") is True),
        "summary_missing_runs": sum(1 for row in rows if row.get("summary_present") is False),
        "stale_or_expired_runs": sum(
            1
            for row in rows
            if str(((row.get("freshness") or {}).get("tone") if isinstance(row.get("freshness"), Mapping) else "") or "")
            in {"stale", "expired", "unknown"}
        ),
        "latest_run_id": latest.get("run_id") if latest else None,
        "latest_ready_count": latest.get("ready_count") if latest else 0,
        "latest_blocker_count": latest.get("blocker_count") if latest else 0,
        "latest_freshness": latest.get("freshness") if latest else None,
        "latest_summary_present": latest.get("summary_present") if latest else None,
        "latest_ticker_status": latest_ticker.get("capture_status") if latest_ticker else None,
        "next_fire_point": (market_clock.get("next_fire") or {}).get("fire_point") if isinstance(market_clock.get("next_fire"), dict) else None,
        "latest_artifact_summary_count": sum(1 for item in latest_artifact_summaries if item.get("present")),
        "latest_specimen_row_count": sum(
            len(item.get("specimen_rows") or [])
            for item in latest_artifact_summaries
            if item.get("present")
        ),
        "latest_evidence_safe_use_level": (
            latest_evidence_card.get("safe_use_level")
            if isinstance(latest_evidence_card, Mapping)
            else None
        ),
        "latest_evidence_external_claims_allowed": (
            ((latest_evidence_card.get("evidence_use") or {}).get("external_market_claims_allowed"))
            if isinstance(latest_evidence_card, Mapping)
            and isinstance(latest_evidence_card.get("evidence_use"), Mapping)
            else None
        ),
        "latest_quant_mart_safe_use_level": (
            ((latest_quant_presentation_mart.get("run") or {}).get("safe_use_level"))
            if isinstance(latest_quant_presentation_mart, Mapping)
            and isinstance(latest_quant_presentation_mart.get("run"), Mapping)
            else None
        ),
        "latest_quant_mart_observation_count": (
            len(latest_quant_presentation_mart.get("ranked_observations") or [])
            if isinstance(latest_quant_presentation_mart, Mapping)
            else 0
        ),
        "latest_quant_mart_panel_count": (
            len(latest_quant_presentation_mart.get("panel_manifest") or [])
            if isinstance(latest_quant_presentation_mart, Mapping)
            else 0
        ),
        "latest_quant_mart_projection_status": (
            ((latest_quant_presentation_mart.get("projection_status") or {}).get("status"))
            if isinstance(latest_quant_presentation_mart, Mapping)
            and isinstance(latest_quant_presentation_mart.get("projection_status"), Mapping)
            else None
        ),
        "latest_market_situation_graph_projection_status": (
            ((latest_market_situation_graph.get("projection_status") or {}).get("status"))
            if isinstance(latest_market_situation_graph, Mapping)
            and isinstance(latest_market_situation_graph.get("projection_status"), Mapping)
            else None
        ),
        "latest_market_situation_count": (
            len(latest_market_situation_graph.get("situations") or [])
            if isinstance(latest_market_situation_graph, Mapping)
            else 0
        ),
        "latest_market_situation_edge_count": (
            len(latest_market_situation_graph.get("edges") or [])
            if isinstance(latest_market_situation_graph, Mapping)
            else 0
        ),
        "latest_market_dashboard_read_model_projection_status": (
            ((latest_market_dashboard_read_model.get("projection_status") or {}).get("status"))
            if isinstance(latest_market_dashboard_read_model, Mapping)
            and isinstance(latest_market_dashboard_read_model.get("projection_status"), Mapping)
            else None
        ),
        "latest_market_dashboard_situation_count": (
            int(((latest_market_dashboard_read_model.get("overview") or {}).get("situation_count") or 0))
            if isinstance(latest_market_dashboard_read_model, Mapping)
            and isinstance(latest_market_dashboard_read_model.get("overview"), Mapping)
            else 0
        ),
        "latest_market_dashboard_card_count": (
            len(((latest_market_dashboard_read_model.get("situation_queue") or {}).get("items") or []))
            if isinstance(latest_market_dashboard_read_model, Mapping)
            and isinstance(latest_market_dashboard_read_model.get("situation_queue"), Mapping)
            else 0
        ),
        "latest_market_dashboard_route_ready": (
            ((latest_market_dashboard_read_model.get("api_contract") or {}).get("contract_version"))
            == "market_intelligence_api_v0"
            if isinstance(latest_market_dashboard_read_model, Mapping)
            and isinstance(latest_market_dashboard_read_model.get("api_contract"), Mapping)
            else False
        ),
        "latest_market_dashboard_validated_signal_count": (
            int(((latest_market_dashboard_read_model.get("validation_debt") or {}).get("validated_signal_count") or 0))
            if isinstance(latest_market_dashboard_read_model, Mapping)
            and isinstance(latest_market_dashboard_read_model.get("validation_debt"), Mapping)
            else 0
        ),
    }
    # v0.7+v0.9: surface a SMALL status of the backend-published
    # latest-ready display bundle. The full bundle is 1+ MB once
    # human_market_cockpit lands; embedding it in every world-model
    # snapshot makes /api/world-model/snapshot slow and bloated. The
    # cockpit fetches the full bundle through
    # /api/market/intelligence/display-bundle/latest-ready instead.
    latest_ready_display_bundle_status: Dict[str, Any] | None
    try:
        full_bundle = _load_latest_ready_market_display_bundle(repo_root)
        if full_bundle and full_bundle.get("schema_version"):
            status = (full_bundle.get("latest_ready_status") or {}).get("status")
            hmc = full_bundle.get("human_market_cockpit") or {}
            latest_ready_display_bundle_status = {
                "present": status == "present",
                "status": status,
                "run_id": full_bundle.get("run_id"),
                "schema_version": full_bundle.get("schema_version"),
                "has_human_market_cockpit": bool(hmc),
                "hmc_schema_version": hmc.get("schema_version") if hmc else None,
                "hmc_visual_planes_count": len(hmc.get("visual_planes") or []) if hmc else 0,
            }
        else:
            latest_ready_display_bundle_status = {
                "present": False,
                "status": (full_bundle or {}).get("latest_ready_status", {}).get("status"),
            }
    except Exception:  # pragma: no cover - defensive
        latest_ready_display_bundle_status = None

    return {
        "schema": "market_feeds_snapshot_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs_dir": str(runs_dir),
        "summary": summary,
        "market_clock": market_clock,
        "latest_ticker_snapshot": latest_ticker
        or {
            "present": False,
            "path": str(repo_root / "state" / "metabolism" / "market_timeline.jsonl"),
        },
        "latest_evidence_card": latest_evidence_card,
        "latest_quant_presentation_mart": latest_quant_presentation_mart,
        "latest_market_situation_graph": latest_market_situation_graph,
        "latest_market_dashboard_read_model": latest_market_dashboard_read_model,
        "latest_ready_market_display_bundle_status": latest_ready_display_bundle_status,
        "latest_feed_run": latest,
        "feed_runs": rows,
        "paper_module": "codex/doctrine/paper_modules/lab_oracle_evolve_pipeline.md",
        "station_route": "/station/market-feeds",
    }


def _prediction_targets_from_cp2(data: Mapping[str, Any]) -> Tuple[int, List[str]]:
    predictions = data.get("predictions_t")
    if not isinstance(predictions, list):
        return 0, []
    target_ids: List[str] = []
    for prediction in predictions:
        if not isinstance(prediction, dict):
            continue
        target_id = str(prediction.get("target_id") or "").strip()
        if target_id:
            target_ids.append(target_id)
    return len(predictions), target_ids[:10]


def _run_id_from_path_value(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    token = value.strip()
    if "/" in token:
        return Path(token).name
    return token


def _oracle_feed_health(data: Mapping[str, Any]) -> Dict[str, Any]:
    feed_health = data.get("feed_health")
    if not isinstance(feed_health, dict):
        return {"present": False, "status": "UNKNOWN", "diagnostics": []}
    return {
        "present": True,
        "status": str(feed_health.get("status") or "UNKNOWN").upper(),
        "diagnostics": [
            str(item)
            for item in (feed_health.get("diagnostics") or [])
            if str(item).strip()
        ][:6],
    }


def _oracle_target_counts(data: Mapping[str, Any]) -> Dict[str, int]:
    rows = data.get("prediction_targets")
    if not isinstance(rows, list):
        rows = data.get("targets")
    if not isinstance(rows, list):
        rows = data.get("realized_target_table")
    graded = 0
    missing = 0
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            status = str(row.get("status") or row.get("grade_status") or "").upper()
            price_missing = row.get("truth_price") is None and row.get("realized_price") is None
            if "MISSING" in status or price_missing:
                missing += 1
            else:
                graded += 1
    return {"graded": graded, "missing": missing, "total": graded + missing}


def _compact_oracle_quartet_actions(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    actions: List[Dict[str, Any]] = []
    for action in value:
        if not isinstance(action, Mapping):
            continue
        actions.append(
            {
                "action_kind": str(action.get("action_kind") or "").strip(),
                "canonical_artifact_id": str(action.get("canonical_artifact_id") or "").strip(),
                "source_node_id": str(action.get("source_node_id") or "").strip(),
                "runner_target_id": str(action.get("runner_target_id") or "").strip(),
                "command": str(action.get("command") or "").strip(),
            }
        )
    return actions


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _oracle_subject_run_id(artifacts: Mapping[str, Mapping[str, Any]]) -> Optional[str]:
    for artifact_id in ("subject_index", "lab_cp2", "prediction_reconciliation", "truth_diff_macro"):
        entry = artifacts.get(artifact_id, {})
        for payload in (entry.get("data"), entry.get("metadata")):
            if not isinstance(payload, Mapping):
                continue
            subject_run_id = _run_id_from_path_value(payload.get("subject_run_id"))
            if subject_run_id:
                return subject_run_id
            subject_run_id = _run_id_from_path_value(payload.get("subject_run_dir"))
            if subject_run_id:
                return subject_run_id
            subject_run_id = _run_id_from_path_value(payload.get("hydrated_from_subject"))
            if subject_run_id:
                return subject_run_id
            run_pair = payload.get("run_pair")
            if isinstance(run_pair, Mapping):
                subject_run_id = _run_id_from_path_value(run_pair.get("subject_run_id"))
                if subject_run_id:
                    return subject_run_id
    return None


def _compact_oracle_quartet_repair_plan(
    repo_root: Path,
    run_dir: Path,
    artifacts: Mapping[str, Mapping[str, Any]],
    *,
    has_oracle: bool,
) -> Optional[Dict[str, Any]]:
    if not has_oracle:
        return None
    subject_run_id = _oracle_subject_run_id(artifacts)
    if not subject_run_id:
        return None
    subject_run_dir = repo_root / "state" / "runs" / subject_run_id
    if not subject_run_dir.exists():
        return None
    try:
        from tools.oracle.run_quartet import build_quartet_repair_plan

        plan = build_quartet_repair_plan(subject_run_dir, run_dir, repo_root=repo_root)
    except Exception:
        return None
    readiness = plan.get("readiness")
    readiness_map = readiness if isinstance(readiness, Mapping) else {}
    artifacts_rows = plan.get("artifacts")
    status_counts: Dict[str, int] = {}
    if isinstance(artifacts_rows, list):
        for row in artifacts_rows:
            if not isinstance(row, Mapping):
                continue
            status = str(row.get("status") or "unknown").strip()
            status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "schema_version": "oracle_quartet_repair_summary_v1",
        "status": str(readiness_map.get("status") or "UNKNOWN").upper(),
        "subject_run_id": str(plan.get("subject_run_id") or subject_run_id).strip(),
        "truth_run_id": str(plan.get("truth_run_id") or run_dir.name).strip(),
        "result_kind": str(plan.get("kind") or "oracle_quartet_repair_plan").strip(),
        "target": str(readiness_map.get("deepest_missing_target") or "").strip(),
        "deepest_missing_target": str(readiness_map.get("deepest_missing_target") or "").strip(),
        "missing_canonical_artifacts": _string_list(
            readiness_map.get("missing_canonical_artifacts")
        ),
        "aliasable_artifacts": _string_list(readiness_map.get("aliasable_artifacts")),
        "missing_source_nodes": _string_list(readiness_map.get("missing_source_nodes")),
        "status_counts": status_counts,
        "repair_actions": _compact_oracle_quartet_actions(plan.get("repair_actions")),
        "written_paths": [],
    }


def _evolve_delta_summary(entry: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    if not entry.get("present"):
        return None
    data = entry.get("data") if isinstance(entry.get("data"), Mapping) else {}
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), Mapping) else {}
    pattern_summary = data.get("pattern_summary") if isinstance(data.get("pattern_summary"), Mapping) else {}
    run_pair = data.get("run_pair") if isinstance(data.get("run_pair"), Mapping) else {}
    return {
        "status": str(data.get("status") or entry.get("status") or "UNKNOWN").upper(),
        "root_failure_mode": str(pattern_summary.get("root_failure_mode") or "UNKNOWN").strip(),
        "dossier_delta_count": len(data.get("dossier_deltas") or []),
        "doctrine_flag_count": len(data.get("doctrine_flags") or []),
        "learning_entry_count": len(data.get("learning_entries") or []),
        "subject_run_id": _run_id_from_path_value(run_pair.get("subject_run_id"))
        or _run_id_from_path_value(metadata.get("subject_run_id")),
        "truth_run_id": _run_id_from_path_value(run_pair.get("truth_run_id"))
        or _run_id_from_path_value(metadata.get("truth_run_id")),
        "path": entry.get("path"),
    }


def _evolve_patch_summary(entry: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    if not entry.get("present"):
        return None
    data = entry.get("data") if isinstance(entry.get("data"), Mapping) else {}
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), Mapping) else {}
    lanes = data.get("lanes") if isinstance(data.get("lanes"), Mapping) else {}
    apply_results = metadata.get("apply_results") if isinstance(metadata.get("apply_results"), Mapping) else {}
    lane_statuses = (
        apply_results.get("lane_statuses")
        if isinstance(apply_results.get("lane_statuses"), Mapping)
        else {}
    )
    return {
        "total_ops": int(data.get("total_ops") or 0),
        "lane_count": len(lanes),
        "lanes": [str(lane_name) for lane_name in lanes.keys()][:12],
        "summary": str(data.get("summary") or "").strip() or None,
        "apply_mode": str(metadata.get("apply_mode") or "").strip() or None,
        "total_applied": int(apply_results.get("total_applied") or 0),
        "total_skipped": int(apply_results.get("total_skipped") or 0),
        "lane_statuses": {str(key): str(value) for key, value in lane_statuses.items()},
        "path": entry.get("path"),
    }


def _evolve_gate(
    artifacts: Mapping[str, Mapping[str, Any]],
    lab_cp2_present: bool,
) -> Dict[str, Any]:
    missing = [
        artifact_id
        for artifact_id in (
            "prediction_reconciliation",
            "realized_hindsight_brief",
            "ideal_cp2",
            "cp2_critique",
        )
        if not artifacts.get(artifact_id, {}).get("present")
    ]
    prediction_data = artifacts.get("prediction_reconciliation", {}).get("data") or {}
    feed_health = _oracle_feed_health(prediction_data if isinstance(prediction_data, dict) else {})
    blocking_reasons: List[str] = []
    warnings: List[str] = []

    if missing:
        blocking_reasons.append("missing required Oracle artifacts: " + ", ".join(missing))
    if not lab_cp2_present:
        blocking_reasons.append("missing required Lab CP2 artifact: lab_director")

    feed_status = str(feed_health.get("status") or "UNKNOWN").upper()
    diagnostics = [str(item) for item in feed_health.get("diagnostics") or [] if str(item).strip()]
    if feed_health.get("present"):
        if feed_status == "BLOCKED":
            reason = "prediction_reconciliation.feed_health is BLOCKED"
            if diagnostics:
                reason += ": " + "; ".join(diagnostics)
            blocking_reasons.append(reason)
        elif feed_status == "DEGRADED":
            warning = "prediction_reconciliation.feed_health is DEGRADED"
            if diagnostics:
                warning += ": " + "; ".join(diagnostics)
            warnings.append(warning)
        elif feed_status != "READY":
            warnings.append(
                f"prediction_reconciliation.feed_health status is {feed_status}; treat target grading cautiously"
            )
    elif artifacts.get("prediction_reconciliation", {}).get("present"):
        warnings.append(
            "prediction_reconciliation.feed_health is missing; cannot separate feed coverage from target performance"
        )

    for artifact_id in (
        "prediction_reconciliation",
        "realized_hindsight_brief",
        "ideal_cp2",
        "cp2_critique",
    ):
        entry = artifacts.get(artifact_id, {})
        source_id = str(entry.get("source_artifact_id") or artifact_id)
        if entry.get("present") and source_id != artifact_id:
            warnings.append(f"{artifact_id} loaded from legacy alias {source_id}; prefer canonical artifact output")

    if blocking_reasons:
        status = "BLOCKED"
    elif warnings:
        status = "DEGRADED"
    else:
        status = "READY"
    return {"status": status, "blocking_reasons": blocking_reasons, "warnings": warnings}


def _run_modified_at(run_dir: Path) -> str | None:
    candidates = [run_dir]
    artifacts_dir = run_dir / "artifacts"
    if artifacts_dir.exists():
        candidates.extend([path for path in artifacts_dir.glob("*.json") if path.is_file()])
    mtimes = [path.stat().st_mtime for path in candidates if path.exists()]
    if not mtimes:
        return None
    return datetime.fromtimestamp(max(mtimes), tz=timezone.utc).isoformat()


def _lab_oracle_evolve_run_row(repo_root: Path, run_dir: Path) -> Optional[Dict[str, Any]]:
    artifacts_dir = run_dir / "artifacts"

    feed_readiness = _feed_readiness_compact(artifacts_dir, run_dir=run_dir)
    artifacts = {
        artifact_id: _compact_artifact_presence(artifacts_dir, artifact_id)
        for artifact_id in LAB_ORACLE_EVOLVE_ARTIFACTS
    }
    relevant = (
        feed_readiness.get("present")
        or feed_readiness.get("run_present")
        or any(entry.get("present") for entry in artifacts.values())
    )
    if not relevant:
        return None

    lab_cp2_data = artifacts["lab_cp2"].get("data") or {}
    prediction_count, target_ids = _prediction_targets_from_cp2(
        lab_cp2_data if isinstance(lab_cp2_data, dict) else {}
    )
    prediction_reconciliation_data = artifacts["prediction_reconciliation"].get("data") or {}
    feed_health = _oracle_feed_health(
        prediction_reconciliation_data if isinstance(prediction_reconciliation_data, dict) else {}
    )
    target_counts = _oracle_target_counts(
        prediction_reconciliation_data if isinstance(prediction_reconciliation_data, dict) else {}
    )
    quartet = {
        artifact_id: {
            "present": bool(artifacts[artifact_id].get("present")),
            "source_artifact_id": artifacts[artifact_id].get("source_artifact_id"),
            "path": artifacts[artifact_id].get("path"),
        }
        for artifact_id in (
            "prediction_reconciliation",
            "realized_hindsight_brief",
            "ideal_cp2",
            "cp2_critique",
        )
    }
    gate = _evolve_gate(artifacts, bool(artifacts["lab_cp2"].get("present")))
    has_oracle = bool(
        artifacts["subject_index"].get("present")
        or artifacts["prediction_reconciliation"].get("present")
    )
    has_lab = bool(artifacts["lab_cp2"].get("present"))
    has_evolve = bool(
        artifacts["evolve_delta_report"].get("present")
        or artifacts["evolve_patch_payload"].get("present")
        or artifacts["evolve_input_readiness"].get("present")
    )
    run_kind = "mixed"
    if (feed_readiness.get("present") or feed_readiness.get("run_present")) and not (
        has_lab or has_oracle or has_evolve
    ):
        run_kind = "feed_run"
    elif has_oracle:
        run_kind = "oracle_run"
    elif has_lab:
        run_kind = "lab_run"
    elif has_evolve:
        run_kind = "evolve_run"

    return {
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "modified_at": _run_modified_at(run_dir),
        "freshness": feed_readiness.get("freshness") or compute_freshness(_run_modified_at(run_dir)),
        "kind": run_kind,
        "feed_readiness": feed_readiness,
        "lab_cp2": {
            "present": has_lab,
            "source_artifact_id": artifacts["lab_cp2"].get("source_artifact_id"),
            "path": artifacts["lab_cp2"].get("path"),
            "status": artifacts["lab_cp2"].get("status"),
            "prediction_count": prediction_count,
            "target_ids": target_ids,
        },
        "oracle": {
            "present": has_oracle,
            "subject_run_id": _oracle_subject_run_id(artifacts),
            "subject_index_present": bool(artifacts["subject_index"].get("present")),
            "truth_diff_macro_present": bool(artifacts["truth_diff_macro"].get("present")),
            "quartet": quartet,
            "repair_plan": _compact_oracle_quartet_repair_plan(
                repo_root,
                run_dir,
                artifacts,
                has_oracle=has_oracle,
            ),
            "feed_health": feed_health,
            "target_counts": target_counts,
        },
        "evolve": {
            "present": has_evolve,
            "delta_report_present": bool(artifacts["evolve_delta_report"].get("present")),
            "patch_payload_present": bool(artifacts["evolve_patch_payload"].get("present")),
            "input_readiness_present": bool(artifacts["evolve_input_readiness"].get("present")),
            "delta_summary": _evolve_delta_summary(artifacts["evolve_delta_report"]),
            "patch_summary": _evolve_patch_summary(artifacts["evolve_patch_payload"]),
            "gate": gate,
        },
    }


def _pair_gate(
    *,
    subject_run_id: Optional[str],
    subject_present: bool,
    subject_lab_cp2_present: bool,
    truth_row: Mapping[str, Any],
) -> Dict[str, Any]:
    blocking_reasons: List[str] = []
    warnings: List[str] = []
    quartet = truth_row.get("oracle", {}).get("quartet", {})
    missing = [
        artifact_id
        for artifact_id, entry in quartet.items()
        if isinstance(entry, Mapping) and not entry.get("present")
    ]
    if missing:
        blocking_reasons.append("missing required Oracle artifacts: " + ", ".join(missing))
    if not subject_run_id:
        blocking_reasons.append("Oracle subject index does not declare subject_run_id")
    elif not subject_present:
        blocking_reasons.append(f"subject run not found under state/runs: {subject_run_id}")
    elif not subject_lab_cp2_present:
        blocking_reasons.append("subject run is missing required Lab CP2 artifact: lab_director")

    feed_health = truth_row.get("oracle", {}).get("feed_health", {})
    feed_status = str(feed_health.get("status") or "UNKNOWN").upper()
    diagnostics = [str(item) for item in feed_health.get("diagnostics") or [] if str(item).strip()]
    if feed_health.get("present"):
        if feed_status == "BLOCKED":
            reason = "prediction_reconciliation.feed_health is BLOCKED"
            if diagnostics:
                reason += ": " + "; ".join(diagnostics)
            blocking_reasons.append(reason)
        elif feed_status == "DEGRADED":
            warning = "prediction_reconciliation.feed_health is DEGRADED"
            if diagnostics:
                warning += ": " + "; ".join(diagnostics)
            warnings.append(warning)
        elif feed_status != "READY":
            warnings.append(
                f"prediction_reconciliation.feed_health status is {feed_status}; treat target grading cautiously"
            )
    elif quartet.get("prediction_reconciliation", {}).get("present"):
        warnings.append(
            "prediction_reconciliation.feed_health is missing; cannot separate feed coverage from target performance"
        )

    for artifact_id, entry in quartet.items():
        if not isinstance(entry, Mapping) or not entry.get("present"):
            continue
        source_id = str(entry.get("source_artifact_id") or artifact_id)
        if source_id != artifact_id:
            warnings.append(f"{artifact_id} loaded from legacy alias {source_id}; prefer canonical artifact output")

    if blocking_reasons:
        status = "BLOCKED"
    elif warnings:
        status = "DEGRADED"
    else:
        status = "READY"
    return {"status": status, "blocking_reasons": blocking_reasons, "warnings": warnings}


def _raw_orchestration_event_rows(repo_root: Path, limit: int) -> List[Dict[str, Any]]:
    path = repo_root / ORCHESTRATION_EVENTS_PATH
    if not path.exists() or not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: List[Dict[str, Any]] = []
    for raw_line in lines[-max(limit, 1) :]:
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    rows.reverse()
    return rows


def _repo_path_for_event_value(repo_root: Path, value: Any) -> Optional[Path]:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value.strip())
    if not path.is_absolute():
        path = repo_root / path
    return path


def _pid_running(pid: Any) -> bool:
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_int <= 0:
        return False
    try:
        os.kill(pid_int, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _read_tail_text(path: Path, max_bytes: int = _OPERATION_LOG_TAIL_BYTES) -> str:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(-max_bytes, os.SEEK_END)
            data = handle.read()
    except OSError:
        return ""
    return data.decode("utf-8", errors="replace")


def _compact_log_tail(text: str, *, line_limit: int = 10, char_limit: int = 1800) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    tail = "\n".join(lines[-line_limit:])
    return tail[-char_limit:]


def _operation_log_failure_message(text: str) -> Optional[str]:
    if not text:
        return None
    lowered = text.lower()
    if '"ok": false' in lowered:
        match = re.search(r'"error"\s*:\s*"([^"]+)"', text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
        return "operation log reported ok=false"
    if "traceback (most recent call last)" in lowered:
        return "operation log contains a Python traceback"
    return None


def _operation_output_fields_from_event_or_log(
    repo_root: Path,
    event: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Optional[str], Optional[str]]:
    fields = {
        key: event[key]
        for key in (
            "evolve_input_readiness",
            "oracle_quartet_repair",
            "result_summary",
            "stable_signal_digest",
            "route_evidence",
            "lab_oracle_evolve_overnight_plan",
        )
        if key in event
    }
    log_tail: Optional[str] = None
    failure_message: Optional[str] = None
    log_path = _repo_path_for_event_value(repo_root, event.get("log_path"))
    if log_path and log_path.exists():
        text = _read_tail_text(log_path)
        log_fields = _shared_operation_event_fields_from_operation_output(text)
        if log_fields:
            fields.update(log_fields)
        failure_message = _operation_log_failure_message(text)
        log_tail = _compact_log_tail(text)
    return fields, log_tail, failure_message


def _lab_oracle_evolve_operation_history(
    repo_root: Path,
    event_rows: Sequence[Mapping[str, Any]],
    *,
    subject_run_id: Optional[str],
    truth_run_id: str,
    limit: int = _LAB_ORACLE_EVOLVE_HISTORY_PAIR_LIMIT,
) -> List[Dict[str, Any]]:
    if not subject_run_id:
        return []
    history: List[Dict[str, Any]] = []
    for event in event_rows:
        operation_id = str(event.get("operation_id") or "").strip()
        if operation_id not in _LAB_ORACLE_EVOLVE_OPERATION_IDS:
            continue
        params = event.get("resolved_parameters")
        if not isinstance(params, Mapping):
            continue
        if _run_id_from_path_value(params.get("subject_run")) != subject_run_id:
            continue
        if _run_id_from_path_value(params.get("truth_run")) != truth_run_id:
            continue

        detached = bool(event.get("detached"))
        pid = event.get("pid")
        pid_running = _pid_running(pid) if detached else False
        returncode = event.get("returncode")
        output_fields, log_tail, failure_message = _operation_output_fields_from_event_or_log(
            repo_root, event
        )
        if detached:
            if pid_running:
                status = "running"
            elif output_fields:
                status = "completed"
            elif failure_message:
                status = "failed"
            elif event.get("log_path"):
                status = "exited_unknown"
            else:
                status = "unknown"
        elif returncode is None:
            status = "unknown"
        else:
            status = "completed" if int(returncode) == 0 else "failed"

        entry: Dict[str, Any] = {
            "operation_id": operation_id,
            "status": status,
            "detached": detached,
            "recorded_at": event.get("recorded_at"),
            "event_id": event.get("event_id"),
            "returncode": returncode,
            "duration_ms": event.get("duration_ms"),
            "pid": pid,
            "pid_running": pid_running,
            "log_path": event.get("log_path"),
            "resolved_parameters": dict(params),
        }
        if failure_message:
            entry["failure_message"] = failure_message
        if log_tail:
            entry["log_tail"] = log_tail
        entry.update(output_fields)
        history.append(entry)
        if len(history) >= limit:
            break
    return history


def _lab_oracle_evolve_pair_candidates(repo_root: Path, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows_by_id = {row["run_id"]: row for row in rows}
    operation_events = _raw_orchestration_event_rows(
        repo_root,
        _LAB_ORACLE_EVOLVE_HISTORY_EVENT_LIMIT,
    )
    pairs: List[Dict[str, Any]] = []
    for truth_row in rows:
        if not truth_row.get("oracle", {}).get("present"):
            continue
        subject_run_id = _run_id_from_path_value(truth_row.get("oracle", {}).get("subject_run_id"))
        subject_row = rows_by_id.get(subject_run_id or "")
        subject_run_dir = repo_root / "state" / "runs" / str(subject_run_id or "")
        subject_present = bool(subject_run_id and (subject_row is not None or subject_run_dir.exists()))
        subject_lab_cp2_present = bool(subject_row and subject_row.get("lab_cp2", {}).get("present"))
        if not subject_lab_cp2_present and subject_present:
            subject_lab_cp2_present = (subject_run_dir / "artifacts" / "lab_director.json").exists()

        gate = _pair_gate(
            subject_run_id=subject_run_id,
            subject_present=subject_present,
            subject_lab_cp2_present=subject_lab_cp2_present,
            truth_row=truth_row,
        )
        subject_ref = f"state/runs/{subject_run_id}" if subject_run_id else ""
        truth_ref = f"state/runs/{truth_row['run_id']}"
        repair = truth_row.get("oracle", {}).get("repair_plan") or {
            "status": "UNKNOWN",
            "repair_actions": [],
            "missing_canonical_artifacts": [],
            "aliasable_artifacts": [],
            "missing_source_nodes": [],
            "deepest_missing_target": None,
        }
        deepest_target = str(
            repair.get("deepest_missing_target")
            or repair.get("target")
            or "oracle_cp2_emitter"
        ).strip() or "oracle_cp2_emitter"
        operation_parameters = {
            "subject_run": subject_ref,
            "truth_run": truth_ref,
        }
        operation_presets = [
            {
                "operation_id": "evolve_input_check",
                "label": "Check inputs",
                "parameters": dict(operation_parameters),
                "recommended_when": "Always run before learning or repair launch.",
            },
            {
                "operation_id": "oracle_quartet_plan",
                "label": "Plan quartet repair",
                "parameters": dict(operation_parameters),
                "recommended_when": "Use when the pair is blocked on missing canonical Oracle artifacts.",
            },
            {
                "operation_id": "oracle_quartet_run_missing",
                "label": "Run quartet repair",
                "parameters": {
                    **operation_parameters,
                    "target": deepest_target,
                },
                "recommended_when": "Use only after the repair plan confirms the selected missing source node.",
            },
            {
                "operation_id": "evolve_bridge_dry_run",
                "label": "Preview Evolve",
                "parameters": {
                    **operation_parameters,
                    "provider": "chatgpt",
                },
                "recommended_when": "Use after readiness is READY or only DEGRADED by non-blocking warnings.",
            },
        ] if subject_ref else []
        operation_history = _lab_oracle_evolve_operation_history(
            repo_root,
            operation_events,
            subject_run_id=subject_run_id,
            truth_run_id=truth_row["run_id"],
        )
        pairs.append(
            {
                "pair_id": f"{subject_run_id or 'UNKNOWN'}->{truth_row['run_id']}",
                "subject_run_id": subject_run_id,
                "truth_run_id": truth_row["run_id"],
                "subject_present": subject_present,
                "subject_lab_cp2_present": subject_lab_cp2_present,
                "truth_oracle_present": True,
                "evolve_present": bool(truth_row.get("evolve", {}).get("present")),
                "evolve_delta_report_present": bool(
                    truth_row.get("evolve", {}).get("delta_report_present")
                ),
                "evolve_patch_payload_present": bool(
                    truth_row.get("evolve", {}).get("patch_payload_present")
                ),
                "readiness": gate,
                "oracle_repair": repair,
                "target_ids": list((subject_row or truth_row).get("lab_cp2", {}).get("target_ids") or []),
                "target_counts": dict(truth_row.get("oracle", {}).get("target_counts") or {}),
                "commands": {
                    "input_check": (
                        f'./repo-python tools/refinement/run_evolve.py --subject-run "{subject_ref}" '
                        f'--truth-run "{truth_ref}" --input-check'
                    )
                    if subject_ref
                    else None,
                    "oracle_quartet_plan": (
                        f'./repo-python tools/oracle/run_quartet.py --subject-run "{subject_ref}" '
                        f'--truth-run "{truth_ref}" --plan'
                    )
                    if subject_ref
                    else None,
                    "evolve_preview": (
                        f'./repo-python tools/refinement/run_evolve.py --subject-run "{subject_ref}" '
                        f'--truth-run "{truth_ref}" --bridge --provider chatgpt --dry-run'
                    )
                    if subject_ref
                    else None,
                },
                "operation_presets": operation_presets,
                "operation_history": operation_history,
            }
        )

    status_rank = {"READY": 0, "DEGRADED": 1, "BLOCKED": 2}
    pairs.sort(
        key=lambda item: (
            status_rank.get(str(item["readiness"]["status"]), 3),
            item["truth_run_id"],
        )
    )
    return pairs


def _is_feed_shell_row(row: Mapping[str, Any]) -> bool:
    feed_readiness = row.get("feed_readiness") if isinstance(row.get("feed_readiness"), Mapping) else {}
    return (
        row.get("kind") == "feed_run"
        and feed_readiness.get("present") is not True
        and row.get("lab_cp2", {}).get("present") is not True
        and row.get("oracle", {}).get("present") is not True
        and row.get("evolve", {}).get("present") is not True
    )


def _select_lab_oracle_evolve_rows(
    rows: Sequence[Dict[str, Any]],
    *,
    limit: int,
) -> List[Dict[str, Any]]:
    if len(rows) <= limit:
        return list(rows)
    feed_shells = [row for row in rows if _is_feed_shell_row(row)]
    substantive = [row for row in rows if not _is_feed_shell_row(row)]
    feed_shell_budget = min(len(feed_shells), max(1, min(6, limit // 4)))
    selected = [*feed_shells[:feed_shell_budget], *substantive[: max(0, limit - feed_shell_budget)]]
    if len(selected) < limit:
        selected_ids = {id(row) for row in selected}
        selected.extend(row for row in rows if id(row) not in selected_ids)
    selected = selected[:limit]
    selected_ids = {id(row) for row in selected}
    return [row for row in rows if id(row) in selected_ids]


def load_lab_oracle_evolve_snapshot(repo_root: Path, limit: int = 24) -> Dict[str, Any]:
    """Read-only Lab/Oracle/Evolve runs snapshot for the cockpit tile.

    Cold builds walk state/runs/* + per-run row construction (~500 ms).
    Wrapped in swr_get keyed by (repo_root, limit, overnight plan/ledger
    freshness) so a newly materialized Evolve overnight plan is visible
    without waiting for TTL expiry. ttl_s=10 remains a safety net for run-dir
    freshness. Direct callers needing exact run-row liveness go through
    _uncached_load_lab_oracle_evolve_snapshot.
    """
    overnight_plan_path, overnight_ledger_path = _lab_oracle_evolve_overnight_paths(repo_root)
    return swr_get(
        "lab_oracle_evolve_snapshot",
        (
            str(repo_root.resolve()),
            int(limit),
            _path_cache_stamp(overnight_plan_path),
            _path_cache_stamp(overnight_ledger_path),
        ),
        lambda: _uncached_load_lab_oracle_evolve_snapshot(repo_root, limit),
        ttl_s=10.0,
    )


def _uncached_load_lab_oracle_evolve_snapshot(repo_root: Path, limit: int = 24) -> Dict[str, Any]:
    runs_dir = repo_root / "state" / "runs"
    rows: List[Dict[str, Any]] = []
    if runs_dir.exists():
        run_dirs = [path for path in runs_dir.iterdir() if path.is_dir()]
        run_dirs.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        for run_dir in run_dirs:
            row = _lab_oracle_evolve_run_row(repo_root, run_dir)
            if row:
                rows.append(row)
    rows = _select_lab_oracle_evolve_rows(rows, limit=max(1, limit))

    pair_candidates = _lab_oracle_evolve_pair_candidates(repo_root, rows)
    gate_counts = Counter(str(row["evolve"]["gate"]["status"]) for row in rows)
    pair_gate_counts = Counter(str(pair["readiness"]["status"]) for pair in pair_candidates)
    feed_runs = [
        row
        for row in rows
        if row["feed_readiness"]["present"] or row["feed_readiness"].get("run_present")
    ]
    oracle_runs = [row for row in rows if row["oracle"]["present"]]
    summary = {
        "total_runs": len(rows),
        "feed_runs": len(feed_runs),
        "feed_ready_runs": sum(1 for row in feed_runs if row["feed_readiness"].get("ready") is True),
        "feed_summary_missing_runs": sum(
            1 for row in feed_runs if row["feed_readiness"].get("summary_present") is False
        ),
        "oracle_runs": len(oracle_runs),
        "evolve_ready_runs": gate_counts.get("READY", 0),
        "evolve_degraded_runs": gate_counts.get("DEGRADED", 0),
        "evolve_blocked_runs": gate_counts.get("BLOCKED", 0),
        "pair_candidates": len(pair_candidates),
        "pair_ready": pair_gate_counts.get("READY", 0),
        "pair_degraded": pair_gate_counts.get("DEGRADED", 0),
        "pair_blocked": pair_gate_counts.get("BLOCKED", 0),
        "latest_run_id": rows[0]["run_id"] if rows else None,
        "latest_freshness": rows[0].get("freshness") if rows else None,
    }
    return {
        "schema": "lab_oracle_evolve_snapshot_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs_dir": str(runs_dir),
        "summary": summary,
        "runs": rows,
        "pair_candidates": pair_candidates,
        "overnight": _load_lab_oracle_evolve_overnight_status(repo_root),
        "paper_module": "codex/doctrine/paper_modules/lab_oracle_evolve_pipeline.md",
        "station_route": "/station/lab-oracle-evolve",
    }


def load_world_model_snapshot(repo_root: Path) -> Dict[str, Any]:
    # The snapshot is a 150k+-char aggregation over orchestration, doctrine,
    # paper-modules, approvals, and host-agent dotfiles. Nothing in it changes
    # more often than the controller ticks on disk, so serve under SWR and pay
    # the cold compute cost at most once every TTL per process.
    return swr_get(
        "world_model_snapshot",
        str(repo_root.resolve()),
        lambda: _uncached_load_world_model_snapshot(repo_root),
        ttl_s=10.0,
    )


def _lean_surface(surface_id: str, *, available: bool, issues: Sequence[str] = (), **payload: Any) -> Dict[str, Any]:
    return {
        "surface_id": surface_id,
        "available": available,
        **payload,
        "omission_receipt": {
            "status": "complete" if available and not issues else "degraded",
            "issues": list(issues),
            "reason": "Lean visual surface is read-only projection transport; proof authority stays with Lean/Lake checks and owner receipts.",
        },
    }


def _lean_doc_section_index(repo_root: Path) -> Dict[str, Any]:
    markdown_path = repo_root / LEAN_MATH_MARKDOWN_PATH
    if not markdown_path.exists() or not markdown_path.is_file():
        return _lean_surface(
            "doc_section_index",
            available=False,
            issues=[f"missing:{LEAN_MATH_MARKDOWN_PATH}"],
            sections=[],
            section_count=0,
            markdown_ref=LEAN_MATH_MARKDOWN_PATH,
        )
    text = markdown_path.read_text(encoding="utf-8")
    headings = list(re.finditer(r"^##\s+(.+)$", text, flags=re.MULTILINE))
    sections: List[Dict[str, Any]] = []
    for index, match in enumerate(headings):
        title = match.group(1).strip()
        anchor_id = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        start = match.start()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        section_text = text[start:end]
        sections.append(
            {
                "anchor_id": anchor_id,
                "title": title,
                "byte_offset": len(text[:start].encode("utf-8")),
                "byte_length": len(section_text.encode("utf-8")),
                "hash": "sha256:" + hashlib.sha256(section_text.encode("utf-8")).hexdigest(),
            }
        )
    return _lean_surface(
        "doc_section_index",
        available=True,
        sections=sections,
        section_count=len(sections),
        markdown_ref=LEAN_MATH_MARKDOWN_PATH,
    )


def _complete_lean_visual_surfaces(repo_root: Path, projection: Mapping[str, Any], receipt: Mapping[str, Any]) -> Dict[str, Any]:
    visual_surfaces = projection.get("visual_surfaces")
    visual = dict(visual_surfaces) if isinstance(visual_surfaces, Mapping) else {}
    for key in LEAN_MATH_VISUAL_SURFACE_KEYS:
        if not isinstance(visual.get(key), Mapping):
            visual[key] = _lean_surface(key, available=False, issues=[f"missing_surface:{key}"])
    visual["doc_section_index"] = _lean_doc_section_index(repo_root)
    currentness = projection.get("currentness") if isinstance(projection.get("currentness"), Mapping) else {}
    source_fingerprint = str(currentness.get("source_fingerprint") or receipt.get("source_fingerprint") or "")
    generated_at = str(projection.get("generated_at") or currentness.get("generated_at") or "")
    if source_fingerprint or generated_at:
        visual["consistency_token"] = hashlib.sha256(
            f"{source_fingerprint}:{generated_at}".encode("utf-8")
        ).hexdigest()[:16]
    visual["surface_keys"] = list(LEAN_MATH_VISUAL_SURFACE_KEYS)
    visual.setdefault(
        "carve_out_thresholds",
        {"payload_bytes": 100000, "declarations": 2000, "edges": 5000, "timeline_steps": 1000},
    )
    return visual


def _complete_lean_graph_views(projection: Mapping[str, Any], receipt: Mapping[str, Any]) -> Dict[str, Any]:
    graph_views = projection.get("graph_views")
    graph = dict(graph_views) if isinstance(graph_views, Mapping) else {}
    currentness = projection.get("currentness") if isinstance(projection.get("currentness"), Mapping) else {}
    for key in LEAN_MATH_GRAPH_VIEW_KEYS:
        if not isinstance(graph.get(key), list):
            graph[key] = []
    graph.setdefault("schema_version", LEAN_MATH_GRAPH_VIEW_SCHEMA_VERSION)
    graph.setdefault("legacy_schema_version", "lean_mathematics_graph_views_v1")
    graph.setdefault("available", bool(graph_views))
    graph.setdefault("source_ref", "visual_surfaces.declaration_graph")
    graph.setdefault("source_fingerprint", currentness.get("source_fingerprint") or receipt.get("source_fingerprint"))
    graph.setdefault("view_keys", list(LEAN_MATH_GRAPH_VIEW_KEYS))
    if not isinstance(graph.get("view_registry"), list):
        graph["view_registry"] = [dict(row) for row in LEAN_MATH_GRAPH_VIEW_REGISTRY]
    if not isinstance(graph.get("proof_spine_bundle"), Mapping):
        graph["proof_spine_bundle"] = {
            "primary_route_id": None,
            "final_label": None,
            "route_steps": [],
            "route_edges": [],
            "branch_bundles": [],
            "family_overlays": [],
            "external_dependency_chips": [],
            "terminal_claim_chips": [],
        }
    if not isinstance(graph.get("layout_hints"), Mapping):
        graph["layout_hints"] = {
            "rank_by_node_id": {},
            "lane_by_node_id": {},
            "family_lane_by_family_id": {},
            "route_step_order": [],
        }
    if not isinstance(graph.get("expansion_handles"), Mapping):
        graph["expansion_handles"] = {}
    if not isinstance(graph.get("node_salience"), Mapping):
        graph["node_salience"] = {}
    if not isinstance(graph.get("edge_views"), Mapping):
        graph["edge_views"] = {}
    edge_views = dict(graph["edge_views"])
    for key in ("full_edges", "transitive_reduction_edges", "proof_spine_edges", "bundle_edges"):
        if not isinstance(edge_views.get(key), list):
            edge_views[key] = []
    graph["edge_views"] = edge_views
    if not isinstance(graph.get("condensed_dag"), Mapping):
        graph["condensed_dag"] = {
            "nodes": [],
            "edges": [],
            "family_anchor_node_ids": {},
            "layout_hints": {},
        }
    graph.setdefault(
        "capabilities",
        {
            "has_view_registry": bool(graph.get("view_registry")),
            "has_proof_spine_bundle": bool((graph.get("proof_spine_bundle") or {}).get("route_steps")),
            "has_layout_hints": bool((graph.get("layout_hints") or {}).get("route_step_order")),
            "has_expansion_handles": bool(graph.get("expansion_handles")),
            "has_edge_views": bool((graph.get("edge_views") or {}).get("full_edges")),
            "has_salience": bool(graph.get("node_salience")),
            "has_condensed_dag": bool((graph.get("condensed_dag") or {}).get("nodes")),
        },
    )
    graph.setdefault(
        "inference",
        {
            "mode": "static_projection_name_edge_inference",
            "proof_authority": "none; graph views are projection-only and do not run Lean",
            "edge_direction": "from declaration to declaration it lexically references",
        },
    )
    if not isinstance(graph.get("omission_receipt"), Mapping):
        graph["omission_receipt"] = {
            "status": "degraded",
            "issues": ["missing_graph_views"],
            "reason": "graph_views are derived from the generated Lean mathematics projection when available",
        }
    else:
        receipt_payload = dict(graph["omission_receipt"])
        issues = list(receipt_payload.get("issues") or [])
        for key in ("proof_spine_bundle", "layout_hints", "expansion_handles", "node_salience", "edge_views", "condensed_dag"):
            if not graph.get(key):
                issue = f"missing_or_empty:{key}"
                if issue not in issues:
                    issues.append(issue)
        receipt_payload["issues"] = issues
        if issues and receipt_payload.get("status") == "complete":
            receipt_payload["status"] = "degraded"
        graph["omission_receipt"] = receipt_payload
    return graph


def load_lean_mathematics_microcosm_snapshot(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Expose the generated Lean/formal-math microcosm as a read-only
      API payload for Station without turning the server into a proof runner.
    - Mechanism: Read projection, receipt, and markdown from disk; complete the
      typed visual_surfaces envelope for one-fetch rendering.
    - Writes: None.
    - Guarantee: Missing/malformed artifacts return available=false with an
      omission receipt rather than raising.
    """
    projection = _safe_read_json(repo_root, LEAN_MATH_PROJECTION_PATH)
    receipt = _safe_read_json(repo_root, LEAN_MATH_RECEIPT_PATH)
    markdown_path = repo_root / LEAN_MATH_MARKDOWN_PATH
    markdown_present = markdown_path.exists() and markdown_path.is_file()
    issues: List[str] = []
    if projection is None:
        issues.append(f"missing_or_malformed:{LEAN_MATH_PROJECTION_PATH}")
        projection = {}
    if receipt is None:
        issues.append(f"missing_or_malformed:{LEAN_MATH_RECEIPT_PATH}")
        receipt = {}
    if not markdown_present:
        issues.append(f"missing:{LEAN_MATH_MARKDOWN_PATH}")

    def projection_mapping(key: str) -> Dict[str, Any]:
        value = projection.get(key)
        return dict(value) if isinstance(value, Mapping) else {}

    def projection_list(key: str) -> List[Any]:
        value = projection.get(key)
        return list(value) if isinstance(value, list) else []

    capability_snapshot = projection_mapping("capability_snapshot")
    authority_boundary = capability_snapshot.get("authority_boundary")
    if not isinstance(authority_boundary, Mapping):
        authority_boundary = {}

    visual_surfaces = _complete_lean_visual_surfaces(repo_root, projection, receipt)
    graph_views = _complete_lean_graph_views(projection, receipt)
    return {
        "schema": "lean_mathematics_microcosm_snapshot_v1",
        "available": not issues,
        "projection_ref": LEAN_MATH_PROJECTION_PATH,
        "receipt_ref": LEAN_MATH_RECEIPT_PATH,
        "markdown_ref": LEAN_MATH_MARKDOWN_PATH,
        "projection": projection,
        "receipt": receipt,
        "summary": projection_mapping("summary"),
        "currentness": projection_mapping("currentness"),
        "lean_projects": projection_list("lean_projects"),
        "formal_math_threads": projection_list("formal_math_threads"),
        "capability_snapshot": capability_snapshot,
        "graph_views": graph_views,
        "validation_surfaces": projection_mapping("validation_surfaces"),
        "route_cards": projection_list("route_cards"),
        "anti_claims": [str(item) for item in projection_list("anti_claims")],
        "authority_boundary": dict(authority_boundary),
        "visual_surfaces": visual_surfaces,
        "omission_receipt": {
            "status": "complete" if not issues else "degraded",
            "issues": issues,
            "projection_status": "present" if projection else "missing_or_malformed",
            "receipt_status": "present" if receipt else "missing_or_malformed",
            "markdown_status": "present" if markdown_present else "missing",
            "markdown_bytes": markdown_path.stat().st_size if markdown_present else 0,
            "markdown_mtime": _path_mtime_iso(markdown_path),
            "omitted": [
                "markdown_body",
                "Lean stdout/stderr bodies",
                "source file bodies",
                "provider outputs",
            ],
            "reason": "This API is a read-only transport over generated Lean/formal-math projections.",
            "drilldown_paths": [
                LEAN_MATH_PROJECTION_PATH,
                LEAN_MATH_RECEIPT_PATH,
                LEAN_MATH_MARKDOWN_PATH,
            ],
        },
    }


def _uncached_load_world_model_snapshot(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the compact world-model snapshot used by the cockpit shell.
    - Mechanism: Resolve the active family, condense orchestration/docs-focus/doctrine/bootstrap slices, select the active phase, and return one read-only payload.
    - Reads: Active-family phase artifacts plus orchestration, doctrine, and bootstrap JSON surfaces under the repo root.
    - Guarantee: Returns a `world_model_snapshot_v1` payload with family, phases, active_phase, and the condensed doctrine/runtime slices needed by the cockpit.
    - Fails: None — missing artifacts degrade to empty or None substructures.
    - When-needed: Open when an API route or backend debug pass needs the canonical cockpit snapshot assembler rather than each lower-level condense helper.
    - Escalates-to: system/server/main.py; system/server/schemas.py; system/server/translator.py
    - Navigation-group: server_backend
    """
    family_dir = _resolve_active_family_dir(repo_root)
    phase_family_json = _safe_read_json(repo_root, f"{family_dir}/phase_family.json") if family_dir else {}
    if not isinstance(phase_family_json, dict):
        phase_family_json = {}
    family_meta: Dict[str, Any] = {}
    if family_dir:
        family_meta = {
            "family_dir": family_dir,
            "family_id": phase_family_json.get("family_id"),
            "family_number": phase_family_json.get("family_number"),
            "title": phase_family_json.get("family_title") or phase_family_json.get("title"),
            "raw_seed_path": f"{family_dir}/raw_seed.md",
            "raw_seed_meta_path": f"{family_dir}/raw_seed/raw_seed_meta.md",
            "principles_path": _principles_path_for_active_family(family_dir),
            "raw_seed_index_path": _raw_seed_index_path_for_active_family(family_dir),
            "meta_ledger_path": f"{family_dir}/meta_ledger.json",
            "reference_ledger_path": f"{family_dir}/reference_ledger.json",
        }

    phases = _list_phase_dirs(repo_root, family_dir) if family_dir else []
    orchestration = _condense_orchestration_state(_safe_read_json(repo_root, ORCHESTRATION_STATE_PATH))
    docs_focus = _condense_docs_focus(repo_root)
    doctrine_runtime = _condense_doctrine_runtime(repo_root)
    bootstrap = _condense_agent_bootstrap_live(repo_root)
    navigation_graph = _condense_navigation_graph(repo_root)
    frontend_navigation_mission_control = _load_frontend_navigation_mission_control(repo_root)
    try:
        navigation_freshness = load_navigation_freshness_snapshot(repo_root)
    except Exception as exc:
        logger.debug("navigation freshness snapshot load failed: %s", exc)
        navigation_freshness = {
            "schema": "navigation_freshness_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "available": False,
            "stale_source_count": 0,
            "stale_or_missing_row_count": 0,
            "has_estimates": False,
            "top_source_kind": None,
            "queue": [],
        }
    catalog = _condense_doctrine_index(repo_root)
    principles_family = _condense_principles_for_family(repo_root, family_dir)
    try:
        host_agents = load_host_agent_external_snapshot(repo_root)
    except Exception as exc:
        logger.debug("host-agent external snapshot load failed: %s", exc)
        host_agents = {
            "schema": "host_agent_external_snapshot_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "available": False,
            "campaign_id": None,
            "authored_at": None,
            "authored_freshness": {"tone": "unknown", "age_seconds": None, "label": "unknown", "iso": None},
            "mining_run_path": None,
            "current_window": _empty_host_agent_window(label="30d", days=30),
            "extended_window": _empty_host_agent_window(label="90d", days=90),
            "curate_count": 0,
            "deferred_count": 0,
            "curate": [],
            "deferred": [],
        }
    try:
        host_agent_dotfiles = load_host_agent_dotfile_snapshot(repo_root)
    except Exception as exc:
        logger.debug("host-agent dotfile snapshot load failed: %s", exc)
        host_agent_dotfiles = _empty_host_agent_dotfile_snapshot(repo_root)
    try:
        # signal_mode="cached" returns the swr-cached payload if warm or None
        # if the cache is cold. The drift aggregate already tolerates None
        # (see the except branch below). lifespan prewarm at main.py:765
        # populates this cache at startup, so once warm both modes look
        # identical; cold callers no longer pay the ~9.4 s paper-module
        # validation wall here, since /api/world-model/paper-modules and the
        # factory pipelines still pull live via the default signal_mode.
        paper_modules_for_drift = load_paper_modules_snapshot(
            repo_root, signal_mode="cached"
        )
    except Exception as exc:
        logger.debug("paper-modules snapshot for drift aggregate failed: %s", exc)
        paper_modules_for_drift = None
    drift_aggregate = _build_drift_aggregate(
        dotfiles=host_agent_dotfiles,
        navigation_graph=navigation_graph,
        paper_modules=paper_modules_for_drift,
    )
    try:
        approvals = list_approvals(repo_root)
    except Exception as exc:
        logger.debug("approvals snapshot load failed: %s", exc)
        approvals = {
            "summary": {
                "total_pending": 0,
                "source_kind_counts": {},
                "action_kind_counts": {},
                "status_counts": {},
                "top_records": [],
            }
        }
    try:
        lab_oracle_evolve = load_lab_oracle_evolve_snapshot(repo_root)
    except Exception as exc:
        logger.debug("Lab/Oracle/Evolve snapshot load failed: %s", exc)
        lab_oracle_evolve = {
            "schema": "lab_oracle_evolve_snapshot_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "runs_dir": str(repo_root / "state" / "runs"),
            "summary": {
                "total_runs": 0,
                "feed_runs": 0,
                "feed_ready_runs": 0,
                "oracle_runs": 0,
                "evolve_ready_runs": 0,
                "evolve_degraded_runs": 0,
                "evolve_blocked_runs": 0,
                "latest_run_id": None,
            },
            "runs": [],
            "paper_module": "codex/doctrine/paper_modules/lab_oracle_evolve_pipeline.md",
            "station_route": "/station/lab-oracle-evolve",
        }
    try:
        market_feeds = load_market_feeds_snapshot(repo_root)
    except Exception as exc:
        logger.debug("market feeds snapshot load failed: %s", exc)
        market_feeds = {
            "schema": "market_feeds_snapshot_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "runs_dir": str(repo_root / "state" / "runs"),
            "summary": {
                "feed_runs": 0,
                "ready_runs": 0,
                "latest_run_id": None,
                "latest_ready_count": 0,
                "latest_blocker_count": 0,
                "latest_ticker_status": None,
                "next_fire_point": None,
            },
            "market_clock": {"available": False, "next_fire": None, "queued_jobs": [], "running_jobs": []},
            "latest_ticker_snapshot": {
                "present": False,
                "path": str(repo_root / "state" / "metabolism" / "market_timeline.jsonl"),
            },
            "latest_feed_run": None,
            "feed_runs": [],
            "paper_module": "codex/doctrine/paper_modules/lab_oracle_evolve_pipeline.md",
            "station_route": "/station/market-feeds",
        }
    try:
        autonomy_diagnostics = load_autonomy_diagnostics(repo_root)
    except Exception as exc:
        logger.debug("autonomy diagnostics snapshot load failed: %s", exc)
        autonomy_diagnostics = {
            "kind": "autonomy_diagnostics",
            "schema_version": "autonomy_diagnostics_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "active_plans": [],
            "runtime_queues": [],
        }

    active_phase = _resolve_active_phase_record(
        phases=phases,
        phase_family=phase_family_json,
        bootstrap_bindings=(bootstrap.get("live_bindings") if bootstrap else None),
        orchestration=orchestration,
    )

    market_dashboard_aliases = _market_dashboard_world_model_aliases(market_feeds)

    return {
        "schema": "world_model_snapshot_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "family": family_meta or None,
        "phases": phases,
        "active_phase": active_phase,
        "orchestration": orchestration,
        "docs_focus": docs_focus,
        "doctrine_runtime": doctrine_runtime,
        "agent_bootstrap_live": bootstrap,
        "navigation_graph": navigation_graph,
        "frontend_navigation_mission_control": frontend_navigation_mission_control,
        "navigation_freshness": navigation_freshness,
        "catalog": catalog,
        "principles_family": principles_family,
        "host_agents": host_agents,
        "host_agent_dotfiles": host_agent_dotfiles,
        "drift_aggregate": drift_aggregate,
        "approvals": approvals.get("summary") or {
            "total_pending": 0,
            "source_kind_counts": {},
            "action_kind_counts": {},
            "status_counts": {},
            "top_records": [],
        },
        "market_feeds": market_feeds,
        **market_dashboard_aliases,
        "lab_oracle_evolve": lab_oracle_evolve,
        "autonomy_diagnostics": autonomy_diagnostics,
        "freshness": {
            "orchestration": orchestration.get("freshness") if orchestration else None,
            "doctrine_runtime": doctrine_runtime.get("freshness"),
            "agent_bootstrap_live": bootstrap.get("freshness"),
            "host_agents": host_agents.get("authored_freshness"),
            "host_agent_dotfiles": host_agent_dotfiles.get("freshness"),
            "system_map_generated_at": catalog.get("system_map_generated_at"),
            "autonomy_diagnostics": autonomy_diagnostics.get("generated_at"),
        },
    }


def _market_dashboard_world_model_aliases(market_feeds: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(market_feeds, Mapping):
        return {
            "latest_market_dashboard_read_model": None,
            "latest_market_dashboard_situation_count": None,
            "latest_market_dashboard_validated_signal_count": None,
            "latest_market_dashboard_route_ready": None,
        }

    read_model = market_feeds.get("latest_market_dashboard_read_model")
    summary = market_feeds.get("summary")
    summary_map = summary if isinstance(summary, Mapping) else {}

    return {
        "latest_market_dashboard_read_model": read_model if isinstance(read_model, Mapping) else None,
        "latest_market_dashboard_situation_count": summary_map.get(
            "latest_market_dashboard_situation_count"
        ),
        "latest_market_dashboard_validated_signal_count": summary_map.get(
            "latest_market_dashboard_validated_signal_count"
        ),
        "latest_market_dashboard_route_ready": summary_map.get(
            "latest_market_dashboard_route_ready"
        ),
    }


def load_paper_modules_snapshot(
    repo_root: Path,
    *,
    signal_mode: str = "live",
) -> Optional[Dict[str, Any]]:
    """Paper-modules snapshot for cockpit / drift / launcher consumers.

    Paper-module validation walks the repo's code-loci subtrees; caching with
    TTL+SWR turns a multi-second build into a sub-millisecond read for all
    callers that don't care about sub-TTL freshness (which is every endpoint
    except explicit paper-module refresh handlers).

    ``signal_mode="live"`` (default) is the exact path — swr_get inline-builds
    on cache miss (the ~9.4 s cold cost) and serves swr-cached deepcopies on
    hit. This is the right mode for the dedicated paper-modules endpoint and
    factories that genuinely need a complete payload.

    ``signal_mode="cached"`` is the "cheap visibility" path — returns the
    current swr cache value via swr_peek if it is non-empty, otherwise None.
    Callers that consume the snapshot as decorative context (e.g.
    _build_drift_aggregate) can use this mode to avoid waiting on the cold
    build during snapshot construction; the existing prewarm thread in
    main.py::lifespan populates the cache, so once warm both modes look
    identical. Mirrors the reactions_engine.build_reactions_snapshot
    signal_mode contract introduced in 881c8d4316a8.
    """
    if signal_mode == "cached":
        return swr_peek("paper_modules_snapshot", str(repo_root.resolve()))
    return swr_get(
        "paper_modules_snapshot",
        str(repo_root.resolve()),
        lambda: _uncached_load_paper_modules_snapshot(repo_root),
        ttl_s=30.0,
    )


def _uncached_load_paper_modules_snapshot(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Expose one read-only paper-modules snapshot for future backend and Station consumers without duplicating paper-module parsing logic in the server layer.
    - Mechanism: Delegate to the shared paper-module runtime, then condense its index/report/freshness payloads into a compact summary, queue counts, and preview-card list.
    - Guarantee: Returns a `paper_modules_snapshot_v1` payload even when generated sidecars are stale; only missing core authored truth degrades the snapshot to `available=false`.
    - Fails: None. Runtime load errors degrade to an unavailable snapshot rather than raising.
    - When-needed: Open when backend routes or server-side projection surfaces need paper-module cards, freshness, or queue counts without rereading `_index.json` and markdown by hand.
    - Escalates-to: system/lib/paper_modules.py; system/server/main.py
    """
    try:
        runtime = load_paper_module_runtime(repo_root=repo_root, compare_existing=True)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("paper-module snapshot load failed: %s", exc)
        return {
            "schema": "paper_modules_snapshot_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "available": False,
            "summary": None,
            "freshness": {"tone": "unknown", "status": "unavailable"},
            "queue_counts": {},
            "route_coverage": {},
            "cards": [],
        }

    index = runtime.index if isinstance(runtime.index, Mapping) else {}
    report = runtime.report if isinstance(runtime.report, Mapping) else {}
    summary = index.get("summary") if isinstance(index.get("summary"), Mapping) else {}
    queue_counts = ((report.get("summary") or {}).get("queue_counts") or {}) if isinstance(report.get("summary"), Mapping) else {}
    route_coverage = runtime.route_coverage if isinstance(runtime.route_coverage, Mapping) else {}
    route_summary = route_coverage.get("summary") if isinstance(route_coverage.get("summary"), Mapping) else {}
    route_attention = route_coverage.get("attention") if isinstance(route_coverage.get("attention"), Mapping) else {}
    freshness = runtime.current_freshness if isinstance(runtime.current_freshness, Mapping) else {}
    cards: List[Dict[str, Any]] = []
    for item in index.get("modules") or []:
        if not isinstance(item, Mapping):
            continue
        previews = item.get("previews") if isinstance(item.get("previews"), Mapping) else {}
        cards.append(
            {
                "slug": str(item.get("slug") or "").strip() or None,
                "title": str(item.get("title") or "").strip() or None,
                "file": str(item.get("file") or "").strip() or None,
                "projection_class": str(item.get("projection_class") or "").strip() or None,
                "status": str(item.get("status") or "").strip() or None,
                "recommended_action": str(item.get("recommended_action") or "").strip() or None,
                "action_cause": str(item.get("action_cause") or "").strip() or None,
                "fan_in_inbound": item.get("fan_in_inbound"),
                "fan_out_outbound": item.get("fan_out_outbound"),
                "boundary_pressure": str(item.get("boundary_pressure") or "").strip() or None,
                "boundary_evidence": dict(item.get("boundary_evidence") or {}),
                "tldr": str(previews.get("tldr") or "").strip() or None,
                "deliverables_preview": [
                    str(value).strip()
                    for value in (previews.get("deliverables") or [])
                    if str(value).strip()
                ],
                "code_loci_preview": [
                    str(value).strip()
                    for value in (previews.get("code_loci") or [])
                    if str(value).strip()
                ],
            }
        )

    index_generated_at = str(index.get("generated_at") or "").strip() or None
    return {
        "schema": "paper_modules_snapshot_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "available": True,
        "summary": {
            "module_count": summary.get("module_count"),
            "candidate_count": summary.get("candidate_count"),
            "edge_count": summary.get("edge_count"),
            "root_count": summary.get("root_count"),
            "leaf_count": summary.get("leaf_count"),
            "projection_class_counts": dict(summary.get("projection_class_counts") or {}),
            "status_counts": dict(summary.get("status_counts") or {}),
            "action_cause_counts": dict(summary.get("action_cause_counts") or {}),
        },
        "freshness": {
            "status": str(freshness.get("sync_status") or "unknown"),
            "generated_at": index_generated_at,
            "generated_at_freshness": compute_freshness(index_generated_at),
            "authored_module_count": freshness.get("authored_module_count"),
            "generated_module_count": freshness.get("generated_module_count"),
            "missing_from_index": list(freshness.get("missing_from_index") or []),
            "missing_from_report": list(freshness.get("missing_from_report") or []),
            "drift_findings": [
                dict(item) for item in (freshness.get("drift_findings") or []) if isinstance(item, Mapping)
            ],
        },
        "queue_counts": dict(queue_counts),
        "route_coverage": {
            "path": "codex/doctrine/paper_modules/_route_coverage.json",
            "summary": dict(route_summary),
            "fingerprints": dict(route_coverage.get("fingerprints") or {}),
            "attention": {
                "route_saturation_queue": [
                    dict(item)
                    for item in (route_attention.get("route_saturation_queue") or [])[:8]
                    if isinstance(item, Mapping)
                ],
                "thin_route_queue": [
                    dict(item)
                    for item in (route_attention.get("thin_route_queue") or [])[:8]
                    if isinstance(item, Mapping)
                ],
                "split_queue_by_route_pressure": [
                    dict(item)
                    for item in (route_attention.get("split_queue_by_route_pressure") or [])[:8]
                    if isinstance(item, Mapping)
                ],
                "route_health_queue": [
                    dict(item)
                    for item in (route_attention.get("route_health_queue") or [])[:8]
                    if isinstance(item, Mapping)
                ],
                "route_metadata_suggestion_queue": [
                    dict(item)
                    for item in (route_attention.get("route_metadata_suggestion_queue") or [])[:8]
                    if isinstance(item, Mapping)
                ],
            },
        },
        "cards": cards,
    }


def load_imaginations_snapshot(repo_root: Path) -> Dict[str, Any]:
    """Cached read-only snapshot of the imaginations browse surface.

    [ACTION]
    - Teleology: Project codex/doctrine/imaginations/_index.json + _validation_report.json
      into one compact list payload for /api/imaginations and Station consumers without
      duplicating builder logic in the server.
    - Mechanism: SWR-cached delegation to _uncached_load_imaginations_snapshot, which
      reads the generated index and validation surfaces written by
      tools/meta/factory/build_imagination_index.py.
    - Guarantee: Returns an `imaginations_snapshot_v1` payload even when the index is
      missing; missing inputs degrade `available=false` rather than raising.
    """
    return swr_get(
        "imaginations_snapshot",
        str(repo_root.resolve()),
        lambda: _uncached_load_imaginations_snapshot(repo_root),
        ttl_s=30.0,
    )


def _uncached_load_imaginations_snapshot(repo_root: Path) -> Dict[str, Any]:
    """Read-only snapshot loader for the imaginations browse surface.

    Returns the same field set the kernel emits via
    `--option-surface imaginations --band flag`, plus the validation summary
    from `_validation_report.json` and the migration coverage block from
    `_index.json`. Authoritative truth remains the generated sidecars; this is
    transport, not a second producer.
    """
    index_path = repo_root / "codex/doctrine/imaginations/_index.json"
    validation_path = repo_root / "codex/doctrine/imaginations/_validation_report.json"
    now_iso = datetime.now(timezone.utc).isoformat()
    if not index_path.is_file():
        return {
            "schema": "imaginations_snapshot_v1",
            "generated_at": now_iso,
            "available": False,
            "summary": None,
            "validation": None,
            "migration_coverage": None,
            "rows": [],
            "by_status": {},
            "by_migrated_from_axiom_candidate": {},
            "by_migrated_from_deliverable_id": {},
        }
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("imaginations_snapshot index load failed: %s", exc)
        return {
            "schema": "imaginations_snapshot_v1",
            "generated_at": now_iso,
            "available": False,
            "summary": None,
            "validation": None,
            "migration_coverage": None,
            "rows": [],
            "by_status": {},
            "by_migrated_from_axiom_candidate": {},
            "by_migrated_from_deliverable_id": {},
        }
    if not isinstance(index, Mapping):
        index = {}
    validation: Dict[str, Any] = {}
    if validation_path.is_file():
        try:
            v_payload = json.loads(validation_path.read_text(encoding="utf-8"))
            if isinstance(v_payload, Mapping):
                validation = {
                    "summary": dict(v_payload.get("summary") or {}),
                    "finding_count": len(v_payload.get("findings") or []),
                    "generated_at": v_payload.get("generated_at"),
                }
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("imaginations validation report load failed: %s", exc)

    summary = index.get("summary") if isinstance(index.get("summary"), Mapping) else {}
    rows_in = index.get("imaginations") if isinstance(index.get("imaginations"), list) else []
    rows_out: List[Dict[str, Any]] = []
    for item in rows_in:
        if not isinstance(item, Mapping):
            continue
        rows_out.append(
            {
                "imagination_id": str(item.get("imagination_id") or ""),
                "slug": str(item.get("slug") or ""),
                "title": str(item.get("title") or ""),
                "status": str(item.get("status") or ""),
                "schema_version": str(item.get("schema_version") or ""),
                "truth_posture": str(item.get("truth_posture") or ""),
                "authored_at": str(item.get("authored_at") or ""),
                "authored_by": str(item.get("authored_by") or ""),
                "file": str(item.get("file") or ""),
                "voice_anchor_summary": str(item.get("voice_anchor_summary") or ""),
                "primary_substrate_seam": str(item.get("primary_substrate_seam") or ""),
                "retirement_trigger_summary": str(item.get("retirement_trigger_summary") or ""),
                "voice_anchor_count": int(item.get("voice_anchor_count") or 0),
                "substrate_count": int(item.get("substrate_count") or 0),
                "scene_fixture_count": int(item.get("scene_fixture_count") or 0),
                "migrated_from_count": int(item.get("migrated_from_count") or 0),
                "migrated_from_axiom_candidate_ids": list(
                    item.get("migrated_from_axiom_candidate_ids") or []
                ),
                "migrated_from_deliverable_ids": list(
                    item.get("migrated_from_deliverable_ids") or []
                ),
                "migrated_from_action_counts": dict(
                    item.get("migrated_from_action_counts") or {}
                ),
                "is_migrated": int(item.get("migrated_from_count") or 0) > 0,
            }
        )

    return {
        "schema": "imaginations_snapshot_v1",
        "generated_at": now_iso,
        "available": True,
        "authority_dir": index.get("authority_dir") or "codex/doctrine/imaginations",
        "standard_path": index.get("standard_path") or "codex/standards/std_imagination.json",
        "skill_path": index.get("skill_path"),
        "source_axiom_candidates_path": index.get("source_axiom_candidates_path"),
        "summary": dict(summary),
        "validation": validation,
        "migration_coverage": dict(index.get("migration_coverage") or {}),
        "rows": rows_out,
        "by_status": dict(index.get("by_status") or {}),
        "by_authored_by": dict(index.get("by_authored_by") or {}),
        "by_migrated_from_axiom_candidate": dict(
            index.get("by_migrated_from_axiom_candidate") or {}
        ),
        "by_migrated_from_deliverable_id": dict(
            index.get("by_migrated_from_deliverable_id") or {}
        ),
    }


def load_imagination_detail(repo_root: Path, id_or_slug: str) -> Dict[str, Any]:
    """Cached read-only detail for one imagination.

    [ACTION]
    - Teleology: Resolve a single imagination by id or slug and project the
      card-band shape (frontmatter projection + body excerpts) for
      /api/imaginations/{id_or_slug} and Station detail drawers.
    - Mechanism: SWR-cached call into _uncached_load_imagination_detail, which
      delegates to system.lib.standard_option_surface.build_option_surface at
      band="card". The option-surface adapter is the single producer.
    - Guarantee: Returns `available=true` with the detail row when resolution
      succeeds; returns `available=false` with `missing_ids` and the available
      list for structured 404 surfaces. Never raises on missing index.
    """
    request = (id_or_slug or "").strip()
    return swr_get(
        f"imagination_detail::{request}",
        str(repo_root.resolve()),
        lambda: _uncached_load_imagination_detail(repo_root, request),
        ttl_s=30.0,
    )


def _uncached_load_imagination_detail(repo_root: Path, id_or_slug: str) -> Dict[str, Any]:
    from system.lib.standard_option_surface import build_option_surface

    now_iso = datetime.now(timezone.utc).isoformat()
    if not id_or_slug:
        return {
            "schema": "imagination_detail_v1",
            "generated_at": now_iso,
            "available": False,
            "request": id_or_slug,
            "missing_ids": [],
            "row": None,
            "available_imaginations": [],
            "reason": "empty_request",
        }

    try:
        payload = build_option_surface(
            repo_root, "imaginations", band="card", ids=id_or_slug
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("imagination_detail option-surface load failed: %s", exc)
        return {
            "schema": "imagination_detail_v1",
            "generated_at": now_iso,
            "available": False,
            "request": id_or_slug,
            "missing_ids": [],
            "row": None,
            "available_imaginations": [],
            "reason": "option_surface_error",
        }

    if not isinstance(payload, Mapping):
        payload = {}
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    selection = payload.get("selection") if isinstance(payload.get("selection"), Mapping) else {}
    missing_ids = list(selection.get("missing_ids") or [])
    if not rows:
        # Build a structured 404-style packet: include the available list so
        # operators / clients can recover.
        snapshot = load_imaginations_snapshot(repo_root)
        return {
            "schema": "imagination_detail_v1",
            "generated_at": now_iso,
            "available": False,
            "request": id_or_slug,
            "missing_ids": missing_ids or [id_or_slug],
            "row": None,
            "available_imaginations": [
                {
                    "imagination_id": r.get("imagination_id"),
                    "slug": r.get("slug"),
                    "title": r.get("title"),
                }
                for r in (snapshot.get("rows") or [])
            ],
            "reason": "not_found",
            "hint_command": "./repo-python kernel.py --imagination-list",
            "find_command": f'./repo-python kernel.py --imagination-find "{id_or_slug}"',
        }

    row = rows[0] if isinstance(rows[0], Mapping) else {}
    return {
        "schema": "imagination_detail_v1",
        "generated_at": now_iso,
        "available": True,
        "request": id_or_slug,
        "missing_ids": missing_ids,
        "row": dict(row),
        "governing_standard": dict(payload.get("governing_standard") or {}),
        "skill_ref": payload.get("skill_ref"),
        "source_refs": list(payload.get("source_refs") or []),
        "preservation_note": (
            "If migrated_from_count > 0, the source teleological_deliverables[] array "
            "in system_axiom_candidates.json is preserved per std_system_axiom_candidate.json "
            "row contract. This detail lifts the predecessor scaffolds without removing them."
        ),
    }


def _latest_agent_telemetry_mining_run_path(repo_root: Path) -> Optional[Path]:
    telemetry_root = repo_root / AGENT_TELEMETRY_ROOT
    if not telemetry_root.exists():
        return None
    candidates: List[Path] = []
    for path in telemetry_root.glob("*/mining_run.json"):
        if path.is_file():
            candidates.append(path)
    if not candidates:
        return None
    try:
        return max(
            candidates,
            key=lambda candidate: (
                candidate.parent.name,
                candidate.stat().st_mtime,
            ),
        )
    except OSError:
        return sorted(candidates)[-1]


def _empty_host_agent_window(
    *,
    label: str,
    days: Optional[int] = None,
    window_start: Optional[str] = None,
    window_end: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "label": label,
        "days": days,
        "window_start": window_start,
        "window_end": window_end,
        "available": False,
        "since": None,
        "scope": None,
        "host_dir": None,
        "report_path": None,
        "projection_path": None,
        "report_generated_at": None,
        "report_freshness": {"tone": "unknown", "age_seconds": None, "label": "unknown", "iso": None},
        "projection_status": None,
        "projection_freshness": {"tone": "unknown", "age_seconds": None, "label": "unknown", "iso": None},
        "codex_threads": 0,
        "codex_tokens": 0,
        "total_spawn_edges": 0,
        "open_spawn_edges": 0,
        "projection_nodes": 0,
        "projection_edges": 0,
        "cross_scope_edges": 0,
        "log_rows": 0,
        "log_error_rows": 0,
        "queued_follow_ups_count": 0,
        "repo_primary_sessions": 0,
        "repo_worktree_slugs": 0,
        "ide_live_instance_locks": 0,
        "recent_threads": [],
    }


def _condense_host_agent_finding(entry: Mapping[str, Any]) -> Dict[str, Any]:
    traceability = entry.get("traceability") if isinstance(entry.get("traceability"), Mapping) else {}
    guard = entry.get("guard") if isinstance(entry.get("guard"), Mapping) else {}
    return {
        "finding_id": str(entry.get("finding_id") or "").strip(),
        "signal_class": str(entry.get("signal_class") or "").strip() or None,
        "promotion_status": str(entry.get("promotion_status") or "").strip() or None,
        "suggested_destination": str(entry.get("suggested_destination") or "").strip() or None,
        "paper_module_slug": (
            str(entry.get("paper_module_slug") or "").strip()
            or str(traceability.get("paper_module_slug") or "").strip()
            or None
        ),
        "instances": int(entry.get("instances") or 0),
        "affected_surface_count": int(entry.get("affected_surface_count") or 0),
        "latest_occurrence_at": str(entry.get("latest_occurrence_at") or "").strip() or None,
        "shape_claim": str(entry.get("shape_claim") or "").strip() or None,
        "behaviour_status": str(guard.get("behaviour_status") or "").strip() or None,
        "substrate_status": str(guard.get("substrate_status") or "").strip() or None,
    }


def _load_host_agent_window(
    repo_root: Path,
    *,
    host_dir_raw: str | Path | None,
    label: str,
    days: Optional[int],
    window_start: Optional[str],
    window_end: Optional[str],
) -> Dict[str, Any]:
    payload = _empty_host_agent_window(
        label=label,
        days=days,
        window_start=window_start,
        window_end=window_end,
    )
    if not host_dir_raw:
        return payload

    host_dir = Path(host_dir_raw)
    if not host_dir.is_absolute():
        host_dir = repo_root / host_dir
    report_path = host_dir / "external_surface_report.json"
    projection_path = host_dir / "external_surface_projection.json"
    report = _safe_read_json_path(report_path) or {}
    projection = _safe_read_json_path(projection_path) or {}
    codex_state = report.get("codex_state") if isinstance(report.get("codex_state"), Mapping) else {}
    codex_logs = report.get("codex_logs") if isinstance(report.get("codex_logs"), Mapping) else {}
    claude_files = report.get("claude_files") if isinstance(report.get("claude_files"), Mapping) else {}
    codex_files = report.get("codex_files") if isinstance(report.get("codex_files"), Mapping) else {}
    projection_counts = projection.get("counts") if isinstance(projection.get("counts"), Mapping) else {}

    open_spawn_edges = 0
    for row in codex_state.get("thread_spawn_edges_by_status") or []:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("status") or "").strip() == "open":
            open_spawn_edges += int(row.get("edges") or 0)

    log_error_rows = 0
    for row in codex_logs.get("rows_by_level") or []:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("level") or "").strip().upper() == "ERROR":
            log_error_rows += int(row.get("rows") or 0)

    recent_threads: List[Dict[str, Any]] = []
    for row in codex_state.get("recent_threads") or []:
        if not isinstance(row, Mapping):
            continue
        recent_threads.append(
            {
                "thread_id": str(row.get("thread_id") or row.get("id") or "").strip() or None,
                "title": str(row.get("title") or "").strip() or None,
                "model": str(row.get("model") or "").strip() or None,
                "reasoning_effort": str(row.get("reasoning_effort") or "").strip() or None,
                "tokens_used": int(row.get("tokens_used") or 0),
                "updated_at": str(row.get("updated_at") or "").strip() or None,
            }
        )
        if len(recent_threads) >= 5:
            break

    report_generated_at = str(report.get("generated_at") or "").strip() or None
    payload.update(
        {
            "available": bool(report or projection),
            "since": str(report.get("since") or projection.get("since") or "").strip() or window_start,
            "scope": str(codex_state.get("scope") or projection.get("scope") or "").strip() or None,
            "host_dir": _normalize_payload_path(repo_root, host_dir),
            "report_path": _normalize_payload_path(repo_root, report_path),
            "projection_path": _normalize_payload_path(repo_root, projection_path),
            "report_generated_at": report_generated_at,
            "report_freshness": compute_freshness(report_generated_at or _path_mtime_iso(report_path)),
            "projection_status": str(projection.get("projector_status") or "").strip() or None,
            "projection_freshness": compute_freshness(_path_mtime_iso(projection_path)),
            "codex_threads": int(codex_state.get("threads_total_for_scope") or 0),
            "codex_tokens": int(codex_state.get("tokens_total_for_scope") or 0),
            "total_spawn_edges": int(codex_state.get("thread_spawn_edges_total") or 0),
            "open_spawn_edges": open_spawn_edges,
            "projection_nodes": int(projection_counts.get("nodes") or 0),
            "projection_edges": int(projection_counts.get("edges") or 0),
            "cross_scope_edges": int(projection_counts.get("cross_scope_edges") or 0),
            "log_rows": int(codex_logs.get("rows_total") or 0),
            "log_error_rows": log_error_rows,
            "queued_follow_ups_count": int(
                ((codex_files.get("global_state") or {}).get("queued_follow_ups_count") or 0)
            ),
            "repo_primary_sessions": int(claude_files.get("repo_primary_sessions") or 0),
            "repo_worktree_slugs": int(claude_files.get("repo_worktree_slugs") or 0),
            "ide_live_instance_locks": int(claude_files.get("ide_live_instance_locks") or 0),
            "recent_threads": recent_threads,
        }
    )
    return payload


def load_host_agent_external_snapshot(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Expose the mined Claude/Codex host-agent runtime plane as one
      compact read-only snapshot so Station and world-model consumers can see
      deployment pressure, thread activity, and mining handoff from disk alone.
    - Mechanism: Resolve the latest `state/agent_telemetry/*/mining_run.json`,
      load the referenced host report/projection sidecars for the recent and
      extended windows, then condense them into additive counts and ranked
      handoff cards.
    - Guarantee: Returns a `host_agent_external_snapshot_v1` payload even when
      no mining run exists; unavailable state degrades to empty windows and zero
      counts instead of raising.
    - Fails: None. File and parse failures collapse to the unavailable shape.
    - When-needed: Open when backend routes or Station need visibility into the
      external Claude/Codex operational record plane without reopening the miner
      artifacts by hand.
    - Escalates-to: tools/meta/agent_telemetry/operational_record_miner.py;
      tools/meta/agent_telemetry/host_surface_probe.py; system/server/main.py
    """

    def _load() -> Dict[str, Any]:
        generated_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "schema": "host_agent_external_snapshot_v1",
            "generated_at": generated_at,
            "available": False,
            "campaign_id": None,
            "authored_at": None,
            "authored_freshness": {"tone": "unknown", "age_seconds": None, "label": "unknown", "iso": None},
            "mining_run_path": None,
            "current_window": _empty_host_agent_window(label="30d", days=30),
            "extended_window": _empty_host_agent_window(label="90d", days=90),
            "curate_count": 0,
            "deferred_count": 0,
            "curate": [],
            "deferred": [],
        }

        mining_run_path = _latest_agent_telemetry_mining_run_path(repo_root)
        if mining_run_path is None:
            return payload

        mining_run = _safe_read_json_path(mining_run_path) or {}
        probe_artifacts = mining_run.get("probe_artifacts") if isinstance(mining_run.get("probe_artifacts"), Mapping) else {}
        windows = mining_run.get("windows") if isinstance(mining_run.get("windows"), Mapping) else {}
        ranked_handoff = mining_run.get("ranked_handoff") if isinstance(mining_run.get("ranked_handoff"), Mapping) else {}

        run_1_window = windows.get("run_1") if isinstance(windows.get("run_1"), Mapping) else {}
        run_2_window = windows.get("run_2") if isinstance(windows.get("run_2"), Mapping) else {}
        run_1_artifacts = probe_artifacts.get("run_1") if isinstance(probe_artifacts.get("run_1"), Mapping) else {}
        run_2_artifacts = probe_artifacts.get("run_2") if isinstance(probe_artifacts.get("run_2"), Mapping) else {}

        current_window = _load_host_agent_window(
            repo_root,
            host_dir_raw=run_1_artifacts.get("host_dir"),
            label="30d",
            days=int(run_1_window.get("days") or 30) if run_1_window else 30,
            window_start=str(run_1_window.get("window_start") or "").strip() or None,
            window_end=str(run_1_window.get("window_end") or "").strip() or None,
        )
        extended_window = _load_host_agent_window(
            repo_root,
            host_dir_raw=run_2_artifacts.get("host_dir"),
            label="90d",
            days=int(run_2_window.get("days") or 90) if run_2_window else 90,
            window_start=str(run_2_window.get("window_start") or "").strip() or None,
            window_end=str(run_2_window.get("window_end") or "").strip() or None,
        )

        curate = [
            _condense_host_agent_finding(item)
            for item in (ranked_handoff.get("curate") or [])
            if isinstance(item, Mapping)
        ]
        deferred = [
            _condense_host_agent_finding(item)
            for item in (ranked_handoff.get("do_not_promote_yet") or [])
            if isinstance(item, Mapping)
        ]

        payload.update(
            {
                "available": True,
                "campaign_id": str(mining_run.get("campaign_id") or "").strip() or None,
                "authored_at": str(mining_run.get("authored_at") or "").strip() or None,
                "authored_freshness": compute_freshness(mining_run.get("authored_at")),
                "mining_run_path": _normalize_payload_path(repo_root, mining_run_path),
                "current_window": current_window,
                "extended_window": extended_window,
                "curate_count": len(curate),
                "deferred_count": len(deferred),
                "curate": curate[:5],
                "deferred": deferred[:5],
            }
        )
        return payload

    return _cached_mapping(
        cache=_HOST_AGENT_EXTERNAL_CACHE,
        lock=_HOST_AGENT_EXTERNAL_CACHE_LOCK,
        repo_root=repo_root,
        loader=_load,
        ttl_s=_HOST_AGENT_EXTERNAL_CACHE_TTL_S,
    )


def _empty_host_agent_dotfile_snapshot(repo_root: Path) -> Dict[str, Any]:
    return {
        "schema": "agent_dotfile_snapshot_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "paper_module": "codex/doctrine/paper_modules/host_agent_dotfile_surfaces.md",
        "available": False,
        "claude": {
            "hooks": {
                "permissions_allow": [],
                "permissions_count": 0,
                "hooks": [],
                "hook_count": 0,
                "rehydration_count": 0,
                "absolute_path_pinned_count": 0,
                "hook_constants": {"integers": {}, "sets": {}},
            },
            "launch": {"configurations": [], "configuration_count": 0},
            "agents": {"personas": [], "persona_count": 0},
            "follow_on": {"carriers": [], "carrier_count": 0},
            "worktrees": {"mirror_count": 0, "mirrors": []},
        },
        "codex": {
            "roles": {"roles": [], "role_count": 0},
            "follow_on": {"carriers": [], "carrier_count": 0},
        },
        "drift_signals": [],
        "drift_signal_count": 0,
        "freshness": {"tone": "unknown", "age_seconds": None, "label": "unknown", "iso": None},
    }


def load_host_agent_dotfile_snapshot(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Project the in-repo `.claude/` + `.codex/` dotfile plane into the
      world-model layer so the cockpit reads host-agent wiring through the same
      cached, freshness-aware projection surface as every other subsystem.
    - Mechanism: Delegate to `system.server.agent_dotfile_snapshot.load_agent_dotfile_snapshot`
      inside `_cached_mapping`, then layer a freshness classification derived from
      the newest dotfile mtime (hooks entry, settings, codex config) so consumers
      see stale-configuration tone without re-reading disk.
    - Guarantee: Returns an `agent_dotfile_snapshot_v1` payload extended with
      `available` and `freshness` fields; on any loader failure collapses to the
      empty shape instead of raising. Caching TTL matches the external host-agent
      snapshot (30s) so repeated `/api/world` calls amortize the parse cost.
    - Fails: None — loader exceptions degrade to the empty shape.
    - When-needed: Open when a backend route, a composed world snapshot, or the
      drift aggregator needs the dotfile plane without each caller re-parsing
      settings.local.json / config.toml / runtime_hook.py constants.
    - Escalates-to: system/server/agent_dotfile_snapshot.py; system/server/main.py;
      codex/doctrine/paper_modules/host_agent_dotfile_surfaces.md
    """

    def _load() -> Dict[str, Any]:
        try:
            from system.server.agent_dotfile_snapshot import load_agent_dotfile_snapshot
            snapshot = load_agent_dotfile_snapshot(repo_root)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("host-agent dotfile snapshot load failed: %s", exc)
            return _empty_host_agent_dotfile_snapshot(repo_root)

        if not isinstance(snapshot, dict):
            return _empty_host_agent_dotfile_snapshot(repo_root)

        candidate_mtimes: List[Optional[str]] = [
            _file_mtime(repo_root, ".claude/settings.local.json"),
            _file_mtime(repo_root, ".claude/hooks/runtime_hook.py"),
            _file_mtime(repo_root, ".claude/launch.json"),
            _file_mtime(repo_root, ".codex/config.toml"),
        ]
        freshest_iso: Optional[str] = None
        for candidate in candidate_mtimes:
            if not candidate:
                continue
            if freshest_iso is None or candidate > freshest_iso:
                freshest_iso = candidate

        snapshot = dict(snapshot)
        snapshot["available"] = True
        snapshot["freshness"] = compute_freshness(freshest_iso)
        return snapshot

    return _cached_mapping(
        cache=_HOST_AGENT_DOTFILES_CACHE,
        lock=_HOST_AGENT_DOTFILES_CACHE_LOCK,
        repo_root=repo_root,
        loader=_load,
        ttl_s=_HOST_AGENT_DOTFILES_CACHE_TTL_S,
    )


def _summarize_dotfile_drift(snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    signals = snapshot.get("drift_signals") if isinstance(snapshot.get("drift_signals"), list) else []
    severity_counts: Dict[str, int] = {"error": 0, "warning": 0, "info": 0}
    preview: List[Dict[str, Any]] = []
    for entry in signals:
        if not isinstance(entry, Mapping):
            continue
        sev = str(entry.get("severity") or "info").lower()
        if sev not in severity_counts:
            severity_counts[sev] = 0
        severity_counts[sev] += 1
        if len(preview) < 5:
            preview.append(
                {
                    "severity": sev,
                    "code": str(entry.get("code") or "").strip() or None,
                    "detail": str(entry.get("detail") or "").strip() or None,
                    "artifact_path": str(
                        entry.get("artifact_path")
                        or entry.get("path")
                        or entry.get("file")
                        or ""
                    ).strip()
                    or None,
                }
            )
    return {
        "total": int(snapshot.get("drift_signal_count") or len(signals) or 0),
        "severity_counts": severity_counts,
        "preview": preview,
    }


def _build_drift_aggregate(
    *,
    dotfiles: Optional[Mapping[str, Any]],
    navigation_graph: Optional[Mapping[str, Any]],
    paper_modules: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Roll up drift signals across the dotfile / navigation / paper-module planes.

    This is the unified "what needs human attention" surface consumed by Station
    headers and agent-diagnostics — individual planes still expose their own
    detail; this is the cross-cutting counter and top-preview so no cockpit has
    to re-sum every subsystem.
    """
    sources: List[Dict[str, Any]] = []
    total = 0
    severity_counts: Dict[str, int] = {"error": 0, "warning": 0, "info": 0}

    if isinstance(dotfiles, Mapping):
        dot_summary = _summarize_dotfile_drift(dotfiles)
        for sev, count in dot_summary["severity_counts"].items():
            severity_counts[sev] = severity_counts.get(sev, 0) + count
        total += dot_summary["total"]
        sources.append(
            {
                "plane": "host_agent_dotfiles",
                "label": ".claude/ + .codex/ dotfiles",
                "count": dot_summary["total"],
                "severity_counts": dot_summary["severity_counts"],
                "preview": dot_summary["preview"],
                "available": bool(dotfiles.get("available")),
                "paper_module": "host_agent_dotfile_surfaces",
                "surface_route": "/station/host-agents",
                "last_seen_at": dotfiles.get("generated_at")
                or (dotfiles.get("freshness") or {}).get("iso"),
            }
        )

    if isinstance(navigation_graph, Mapping):
        nav_counts = navigation_graph.get("counts") if isinstance(navigation_graph.get("counts"), Mapping) else {}
        nav_preview_raw = navigation_graph.get("drift_preview") if isinstance(navigation_graph.get("drift_preview"), list) else []
        nav_total = int(nav_counts.get("drift_signals") or 0)
        total += nav_total
        severity_counts["warning"] = severity_counts.get("warning", 0) + nav_total  # nav graph treats signals as warnings
        nav_preview: List[Dict[str, Any]] = []
        for entry in nav_preview_raw[:5]:
            if not isinstance(entry, Mapping):
                continue
            nav_preview.append(
                {
                    "severity": "warning",
                    "code": str(entry.get("kind") or "").strip() or None,
                    "detail": (
                        f"{entry.get('surface') or entry.get('route') or entry.get('slug') or 'nav entity'}"
                        f" ({entry.get('kind') or 'drift'})"
                    ),
                    "artifact_path": str(
                        entry.get("path") or entry.get("file") or entry.get("route") or ""
                    ).strip()
                    or None,
                }
            )
        sources.append(
            {
                "plane": "frontend_navigation",
                "label": "frontend navigation graph",
                "count": nav_total,
                "severity_counts": {"warning": nav_total},
                "preview": nav_preview,
                "available": True,
                "paper_module": "frontend_navigation_plane",
                "surface_route": "/station/routes",
                "last_seen_at": navigation_graph.get("generated_at"),
            }
        )

    if isinstance(paper_modules, Mapping):
        freshness = paper_modules.get("freshness") if isinstance(paper_modules.get("freshness"), Mapping) else {}
        status_counts = (
            paper_modules.get("summary", {}).get("status_counts")
            if isinstance(paper_modules.get("summary"), Mapping)
            else {}
        ) or {}
        drift_findings = freshness.get("drift_findings") if isinstance(freshness.get("drift_findings"), list) else []
        pm_total = int(len(drift_findings))
        stale = int(status_counts.get("stale_density") or 0) + int(status_counts.get("stale") or 0)
        total += pm_total + stale
        severity_counts["warning"] = severity_counts.get("warning", 0) + pm_total + stale
        pm_preview: List[Dict[str, Any]] = []
        for entry in drift_findings[:5]:
            if not isinstance(entry, Mapping):
                continue
            pm_preview.append(
                {
                    "severity": "warning",
                    "code": str(entry.get("kind") or entry.get("code") or "").strip() or "paper_module_drift",
                    "detail": str(entry.get("detail") or entry.get("slug") or "").strip() or None,
                    "artifact_path": str(
                        entry.get("path")
                        or entry.get("file")
                        or entry.get("source_ref")
                        or entry.get("slug")
                        or ""
                    ).strip()
                    or None,
                }
            )
        sources.append(
            {
                "plane": "paper_modules",
                "label": "paper-module index",
                "count": pm_total + stale,
                "severity_counts": {"warning": pm_total + stale},
                "preview": pm_preview,
                "available": bool(paper_modules.get("available")),
                "paper_module": "paper_modules",
                "surface_route": "/station/papers",
                "last_seen_at": paper_modules.get("generated_at") or freshness.get("generated_at"),
            }
        )

    sources.sort(key=lambda source: source.get("count") or 0, reverse=True)
    return {
        "schema": "drift_aggregate_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "severity_counts": severity_counts,
        "sources": sources,
    }


def resolve_principle(repo_root: Path, principle_id: str) -> Optional[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Resolve one principle record from the active family's raw-seed principles surface.
    - Mechanism: Find the active family, read `raw_seed_principles.json`, and return the first principle entry whose `id` matches.
    - Guarantee: Returns the matching principle dict or None when the family/principles surface is absent or the id is unknown.
    - Fails: None.
    - When-needed: Open when a server route needs one principle drill-down payload from the current active family.
    - Escalates-to: system/server/world_model.py::resolve_authority_chain; system/server/main.py
    """
    family_dir = _resolve_active_family_dir(repo_root)
    rel = _principles_path_for_active_family(family_dir)
    raw = _safe_read_json(repo_root, rel) if rel else None
    if not raw:
        return None
    for entry in raw.get("principles", []) or []:
        if isinstance(entry, dict) and entry.get("id") == principle_id:
            return entry
    return None


def _resolve_doctrine_record(repo_root: Path, root_dir: str, record_id: str) -> Optional[Dict[str, Any]]:
    folder = repo_root / root_dir
    if not folder.exists():
        return None
    target_prefix = f"{record_id}_"
    for child in folder.iterdir():
        if not child.is_file() or not child.name.endswith(".json"):
            continue
        if child.name.startswith(target_prefix) or child.stem == record_id:
            try:
                with child.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    data["__path__"] = str(child.relative_to(repo_root))
                    return data
            except Exception:
                continue
    return None


def resolve_concept(repo_root: Path, concept_id: str) -> Optional[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Resolve one doctrine concept record for UI drill-down.
    - Mechanism: Delegate to `_resolve_doctrine_record()` against `codex/doctrine/concepts`.
    - Guarantee: Returns the matching concept dict with `__path__` attached when found, else None.
    - Fails: None.
    - When-needed: Open when a backend authority or doctrine view needs a concept record by id without scanning the doctrine directory manually.
    - Escalates-to: system/server/world_model.py::resolve_authority_chain; system/server/main.py
    """
    return _resolve_doctrine_record(repo_root, CONCEPTS_DIR, concept_id)


def resolve_mechanism(repo_root: Path, mechanism_id: str) -> Optional[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Resolve one doctrine mechanism record for UI drill-down.
    - Mechanism: Delegate to `_resolve_doctrine_record()` against `codex/doctrine/mechanisms`.
    - Guarantee: Returns the matching mechanism dict with `__path__` attached when found, else None.
    - Fails: None.
    - When-needed: Open when a backend authority or doctrine view needs a mechanism record by id without scanning the doctrine directory manually.
    - Escalates-to: system/server/world_model.py::resolve_authority_chain; system/server/main.py
    """
    return _resolve_doctrine_record(repo_root, MECHANISMS_DIR, mechanism_id)


def resolve_raw_seed_anchor(repo_root: Path, anchor: str) -> Optional[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Resolve a raw-seed paragraph or section anchor against the active family.
    - Mechanism: Read the active family's `raw_seed_index.json`, search its paragraph/section/item/anchor collections, and return the matching entry augmented with family/index paths.
    - Guarantee: Returns the matching anchor payload plus `__family_dir__` and `__index_path__`, or None when the anchor is absent.
    - Fails: None.
    - When-needed: Open when a server-side doctrine or authority drill-down needs to deep-link a raw-seed anchor from the active family.
    - Escalates-to: system/server/world_model.py::resolve_authority_chain; system/server/main.py
    """
    family_dir = _resolve_active_family_dir(repo_root)
    rel = _raw_seed_index_path_for_active_family(family_dir)
    if not rel:
        return None
    raw = _safe_read_json(repo_root, rel)
    if not raw:
        return None
    candidates = []
    for key in ("paragraphs", "sections", "items", "anchors"):
        block = raw.get(key)
        if isinstance(block, list):
            candidates.extend(block)
        elif isinstance(block, dict):
            candidates.extend(block.values())
    for entry in candidates:
        if not isinstance(entry, dict):
            continue
        if any(entry.get(field) == anchor for field in ("ref", "id", "anchor", "paragraph_id", "section_id")):
            entry = dict(entry)
            entry["__family_dir__"] = family_dir
            entry["__index_path__"] = rel
            return entry
    return None


def resolve_doctrine_query(
    repo_root: Path,
    query: str,
    *,
    limit: int = 12,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Expose the compiled doctrine graph as a query packet for the
      server and cockpit drill-downs.
    - Mechanism: Load the canonical graph + section-unit projection from disk,
      attach the live docs-focus block as runtime_state, and delegate to
      `system.lib.doctrine_graph.query_doctrine_graph`.
    - Guarantee: Always returns a packet dict. Missing artifacts fall through
      to an empty graph which `query_doctrine_graph` handles cleanly.
    - Fails: None.
    - When-needed: Open when the server or tests need a doctrine query packet
      keyed to the compiled graph artifacts on disk.
    - Escalates-to: system/lib/doctrine_graph.py::query_doctrine_graph
    """
    graph = _safe_read_json(repo_root, DOCTRINE_GRAPH_REL) or {}
    section_units = _safe_read_json(repo_root, DOCTRINE_SECTION_UNITS_REL) or {}
    runtime_state = {"docs_focus": _condense_docs_focus(repo_root)}
    return query_doctrine_graph(
        graph,
        query=query,
        section_units=section_units,
        limit=limit,
        runtime_state=runtime_state,
    )


_SHARD_SOURCE_VALUES = {"active", "family", "raw_seed"}


def _normalize_shard_source(source: Optional[str]) -> str:
    token = str(source or "family").strip().lower()
    return token if token in _SHARD_SOURCE_VALUES else "family"


def _shard_text(value: Any) -> str:
    return str(value or "").strip()


def _shard_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    out: List[str] = []
    seen: set[str] = set()
    for value in values:
        token = _shard_text(value)
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _active_family_root(repo_root: Path) -> Optional[Path]:
    family_dir = _resolve_active_family_dir(repo_root)
    if not family_dir:
        return None
    return repo_root / family_dir


_SHARD_INDEX_CACHE: Dict[Tuple[str, str], Tuple[float, float, Any]] = {}
_SHARD_INDEX_CACHE_LOCK = Lock()


def _load_shard_index(
    repo_root: Path,
    *,
    source: str = "family",
):
    # ShardIndex is treated as immutable once loaded; callers only read. Cache
    # by (repo, source) with a mtime check so the cache is invalidated the
    # instant the underlying shard JSON changes on disk.
    normalized_source = _normalize_shard_source(source)
    family_root = _active_family_root(repo_root)
    family_dir_arg: Path | str | None = None
    if family_root is not None:
        family_dir_arg = family_root
    key = (str(repo_root.resolve()), normalized_source)
    shard_path = shard_browser.resolve_shards_path(
        family_dir=family_dir_arg,
        source=normalized_source,
        repo_root=repo_root,
    )
    path_mtime = 0.0
    if shard_path is not None:
        try:
            path_mtime = shard_path.stat().st_mtime
        except OSError:
            path_mtime = 0.0
    now = time.monotonic()
    with _SHARD_INDEX_CACHE_LOCK:
        hit = _SHARD_INDEX_CACHE.get(key)
        if hit is not None:
            cached_at, cached_mtime, cached_index = hit
            # Fresh within TTL and the underlying file hasn't changed.
            if now - cached_at <= 30.0 and cached_mtime == path_mtime:
                return cached_index
    index = load_shards(
        family_dir=family_dir_arg,
        source=normalized_source,
        repo_root=repo_root,
    )
    with _SHARD_INDEX_CACHE_LOCK:
        _SHARD_INDEX_CACHE[key] = (now, path_mtime, index)
    return index


def _shard_surface_kind(index: Any) -> Optional[str]:
    envelope = getattr(index, "envelope", {}) or {}
    return _shard_text(envelope.get("surface_kind") or envelope.get("kind")) or None


def _shard_source_path(index: Any, *, repo_root: Path) -> str:
    try:
        return str(index.path.relative_to(repo_root))
    except Exception:
        return str(index.path)


def _shard_freshness_for_path(path: Path) -> Dict[str, Any]:
    try:
        iso = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        iso = None
    return compute_freshness(iso)


def _counter_from_field(shards: Sequence[Mapping[str, Any]], field: str) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for shard in shards:
        token = _shard_text(shard.get(field))
        if token:
            counter[token] += 1
    return dict(counter)


def _top_facets(values: Sequence[str], *, limit: int = 10) -> List[Dict[str, Any]]:
    counter = Counter(token for token in values if token)
    rows = [
        {"value": value, "count": count}
        for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]
    return rows


def _routing_target_entries(shard: Mapping[str, Any]) -> List[Tuple[str, str, Optional[str]]]:
    entries: List[Tuple[str, str, Optional[str]]] = []
    for concept_id in _shard_list(shard.get("concept_ids")):
        entries.append(("concept", concept_id, None))
    for target in shard.get("routing_targets") or []:
        if not isinstance(target, Mapping):
            continue
        target_id = _shard_text(target.get("id") or target.get("target_id"))
        if not target_id:
            continue
        kind = _shard_text(target.get("kind") or target.get("target_kind")) or "target"
        title = _shard_text(target.get("title")) or None
        entries.append((kind, target_id, title))
    return entries


def _resolve_doctrine_title(repo_root: Path, kind: str, id_: str) -> Optional[str]:
    if kind == "concept":
        record = resolve_concept(repo_root, id_) or {}
        return _shard_text(record.get("title")) or None
    if kind == "mechanism":
        record = resolve_mechanism(repo_root, id_) or {}
        return _shard_text(record.get("title")) or None
    if kind == "principle":
        record = resolve_principle(repo_root, id_) or {}
        return _shard_text(record.get("title")) or None
    return None


def _top_doctrine_targets(
    repo_root: Path,
    shards: Sequence[Mapping[str, Any]],
    *,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    counts: Counter[Tuple[str, str]] = Counter()
    titles: Dict[Tuple[str, str], str] = {}
    for shard in shards:
        for kind, id_, title in _routing_target_entries(shard):
            key = (kind, id_)
            counts[key] += 1
            if title:
                titles[key] = title
    rows: List[Dict[str, Any]] = []
    for (kind, id_), count in sorted(counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))[:limit]:
        rows.append(
            {
                "kind": kind,
                "id": id_,
                "title": titles.get((kind, id_)) or _resolve_doctrine_title(repo_root, kind, id_),
                "count": count,
            }
        )
    return rows


def _group_ids_for_shard(shard: Mapping[str, Any]) -> List[str]:
    group_ids = _shard_list(shard.get("idea_group_ids"))
    concept_group = _shard_text(shard.get("concept_group") or shard.get("group"))
    if concept_group and concept_group not in group_ids:
        group_ids.append(concept_group)
    return group_ids


def _summarize_group(group_id: str, shards: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    group_shards = [dict(shard) for shard in shards if group_id in _group_ids_for_shard(shard)]
    gestures = [gesture for shard in group_shards for gesture in _shard_list(shard.get("gestures_towards"))]
    files = [path for shard in group_shards for path in _shard_list(shard.get("relevant_files"))]
    doctrine_ids = [
        id_
        for shard in group_shards
        for _, id_, _ in _routing_target_entries(shard)
    ]
    return {
        "group_id": group_id,
        "count": len(group_shards),
        "pending_count": sum(1 for shard in group_shards if _shard_text(shard.get("status")) == "pending"),
        "sample_shard_ids": [_shard_text(shard.get("id")) for shard in group_shards[:4] if _shard_text(shard.get("id"))],
        "top_gestures": [row["value"] for row in _top_facets(gestures, limit=3)],
        "top_files": [row["value"] for row in _top_facets(files, limit=3)],
        "top_doctrine_ids": [row["value"] for row in _top_facets(doctrine_ids, limit=3)],
    }


def _dedupe_shards(shards: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for shard in shards:
        shard_id = _shard_text(shard.get("id"))
        if not shard_id or shard_id in seen:
            continue
        seen.add(shard_id)
        out.append(dict(shard))
    return out


def _build_shard_graph(repo_root: Path, shards: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    shard_rows = _dedupe_shards(shards)
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: Dict[str, Dict[str, Any]] = {}

    def add_node(node: Dict[str, Any]) -> None:
        node_id = _shard_text(node.get("id"))
        if not node_id:
            return
        existing = nodes.get(node_id)
        if existing is None:
            nodes[node_id] = node
            return
        for key, value in node.items():
            if value not in (None, "", [], {}) and existing.get(key) in (None, "", [], {}):
                existing[key] = value

    def edge_key(kind: str, source: str, target: str) -> str:
        if kind in {"same_parent", "same_bin", "same_source_artifact", "shared_group"}:
            left, right = sorted((source, target))
            return f"{kind}:{left}<->{right}"
        return f"{kind}:{source}->{target}"

    def add_edge(kind: str, source: str, target: str, *, label: Optional[str] = None) -> None:
        key = edge_key(kind, source, target)
        if key in edges:
            if label and not edges[key].get("label"):
                edges[key]["label"] = label
            return
        edges[key] = {
            "id": key,
            "source": source,
            "target": target,
            "kind": kind,
            "label": label,
        }

    for shard in shard_rows:
        shard_id = _shard_text(shard.get("id"))
        shard_node_id = f"shard:{shard_id}"
        add_node(
            {
                "id": shard_node_id,
                "kind": "shard",
                "label": shard_id,
                "summary": _shard_text(
                    shard.get("clarified_statement")
                    or shard.get("statement")
                    or shard.get("gloss")
                    or shard.get("text")
                ),
                "shard_id": shard_id,
                "source_path": _shard_text(shard.get("source_artifact")) or None,
                "status": _shard_text(shard.get("routing_state") or shard.get("status")) or None,
            }
        )

        parent_paragraph_id = _shard_text(shard.get("parent_paragraph_id"))
        if parent_paragraph_id:
            paragraph_node_id = f"paragraph:{parent_paragraph_id}"
            add_node(
                {
                    "id": paragraph_node_id,
                    "kind": "paragraph",
                    "label": parent_paragraph_id,
                    "summary": None,
                    "source_path": None,
                    "status": None,
                }
            )
            add_edge("same_parent", shard_node_id, paragraph_node_id, label=parent_paragraph_id)

        for group_id in _group_ids_for_shard(shard):
            group_node_id = f"group:{group_id}"
            add_node(
                {
                    "id": group_node_id,
                    "kind": "group",
                    "label": group_id,
                    "summary": None,
                    "source_path": None,
                    "status": None,
                }
            )
            add_edge("shared_group", shard_node_id, group_node_id, label=group_id)

        for kind, target_id, title in _routing_target_entries(shard):
            doctrine_node_id = f"doctrine_target:{kind}:{target_id}"
            add_node(
                {
                    "id": doctrine_node_id,
                    "kind": "doctrine_target",
                    "label": title or target_id,
                    "summary": kind,
                    "source_path": None,
                    "status": None,
                }
            )
            add_edge("routes_to", shard_node_id, doctrine_node_id, label=kind)

        for file_path in _shard_list(shard.get("relevant_files")):
            file_node_id = f"file:{file_path}"
            add_node(
                {
                    "id": file_node_id,
                    "kind": "file",
                    "label": Path(file_path).name or file_path,
                    "summary": file_path,
                    "source_path": file_path,
                    "status": None,
                }
            )
            add_edge("references_file", shard_node_id, file_node_id, label=file_path)

    if shard_rows:
        temp_index = _load_shard_index(repo_root, source="family")
        shard_ids = [_shard_text(shard.get("id")) for shard in shard_rows if _shard_text(shard.get("id"))]
        if temp_index is not None:
            neighbor_map = temp_index.neighbor_map(shard_ids, pool=shard_rows)
            for source_shard_id, relations in neighbor_map.items():
                source_node = f"shard:{source_shard_id}"
                for relation in relations:
                    target_shard_id = _shard_text(relation.get("shard_id"))
                    if not target_shard_id:
                        continue
                    target_node = f"shard:{target_shard_id}"
                    shared_groups = _shard_list(relation.get("shared_groups"))
                    for relation_kind in _shard_list(relation.get("relation_kinds")):
                        label = ", ".join(shared_groups) if relation_kind == "shared_group" and shared_groups else None
                        add_edge(relation_kind, source_node, target_node, label=label)

    return {
        "nodes": list(nodes.values()),
        "edges": list(edges.values()),
    }


def _resolve_shard_anchor(repo_root: Path, shard: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    candidates = []
    parent_paragraph_id = _shard_text(shard.get("parent_paragraph_id"))
    if parent_paragraph_id:
        candidates.append(parent_paragraph_id)
    candidates.extend(_shard_list(shard.get("raw_paragraph_ids")))
    raw_seed_anchor = _shard_text(shard.get("raw_seed_anchor"))
    if raw_seed_anchor:
        candidates.append(raw_seed_anchor)
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        record = resolve_raw_seed_anchor(repo_root, candidate)
        if record is not None:
            return record
    return None


def _resolve_shard_record(repo_root: Path, shard_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    family_root = _active_family_root(repo_root)
    surfaces = discover_shard_surfaces(repo_root=repo_root, family_root=family_root)
    for surface in surfaces:
        if not surface.get("exists"):
            continue
        path = _shard_text(surface.get("path"))
        if not path:
            continue
        index = load_shards(explicit_path=path, repo_root=repo_root)
        if index is None:
            continue
        record = index.get(shard_id)
        if record is not None:
            return dict(record), _shard_source_path(index, repo_root=repo_root)
    return None, None


def load_shard_overview(
    repo_root: Path,
    *,
    source: str = "family",
) -> Optional[Dict[str, Any]]:
    # The overview parses the 700k raw_seed_shards.json envelope, discovers every
    # candidate shard surface (another JSON parse per candidate), and resolves
    # doctrine targets. Cache by (repo, source); no request parameters to key.
    return swr_get(
        "shard_overview",
        (str(repo_root.resolve()), source),
        lambda: _uncached_load_shard_overview(repo_root, source=source),
        ttl_s=15.0,
    )


def _uncached_load_shard_overview(
    repo_root: Path,
    *,
    source: str = "family",
) -> Optional[Dict[str, Any]]:
    normalized_source = _normalize_shard_source(source)
    index = _load_shard_index(repo_root, source=normalized_source)
    if index is None:
        return None
    shards = [dict(shard) for shard in index.list()]
    browser_index = index.browser_index()
    group_ids = sorted(
        (_shard_text(group_id) for group_id in (browser_index.get("group_map") or {}).keys()),
        key=lambda group_id: (-len((browser_index.get("group_map") or {}).get(group_id) or []), group_id),
    )
    surfaces = []
    for surface in discover_shard_surfaces(repo_root=repo_root, family_root=_active_family_root(repo_root)):
        surface_path = _shard_text(surface.get("path"))
        surface_freshness = compute_freshness(_file_mtime(repo_root, surface_path)) if surface_path else compute_freshness(None)
        surfaces.append(
            {
                "role": surface.get("role"),
                "source": surface.get("source"),
                "scope": surface.get("scope"),
                "priority": int(surface.get("priority") or 0),
                "surface_kind": surface.get("surface_kind") or "extracted_shards",
                "path": surface_path,
                "exists": bool(surface.get("exists")),
                "total": int(surface.get("total") or 0),
                "pending_count": int(surface.get("pending_count") or 0),
                "extracted_at": surface.get("extracted_at"),
                "freshness": surface_freshness,
            }
        )

    gestures = [gesture for shard in shards for gesture in _shard_list(shard.get("gestures_towards"))]
    files = [path for shard in shards for path in _shard_list(shard.get("relevant_files"))]
    return {
        "schema": "shard_lens_overview_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": normalized_source,
        "source_path": _shard_source_path(index, repo_root=repo_root),
        "surface_kind": _shard_surface_kind(index),
        "freshness": _shard_freshness_for_path(index.path),
        "total_shards": len(shards),
        "total_groups": len(group_ids),
        "pending_count": int(browser_index.get("pending_count") or 0),
        "status_counts": _counter_from_field(shards, "status"),
        "routing_state_counts": _counter_from_field(shards, "routing_state"),
        "coverage_state_counts": _counter_from_field(shards, "coverage_state"),
        "surfaces": surfaces,
        "group_summaries": [_summarize_group(group_id, shards) for group_id in group_ids[:12]],
        "top_gestures": _top_facets(gestures, limit=10),
        "top_files": _top_facets(files, limit=10),
        "top_doctrine_targets": _top_doctrine_targets(repo_root, shards, limit=10),
    }


def query_shards(
    repo_root: Path,
    *,
    source: str = "family",
    query: Optional[str] = None,
    group: Optional[str] = None,
    paragraph_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    related_limit: int = 40,
) -> Optional[Dict[str, Any]]:
    # Queries are parameter-sensitive, so cache per full arg tuple. TTL is short
    # because query-text searches are what the user is actively typing — but any
    # duplicate/filter click within the TTL is free.
    key = (
        str(repo_root.resolve()),
        source,
        query or "",
        group or "",
        paragraph_id or "",
        status or "",
        int(limit),
        int(related_limit),
    )
    return swr_get(
        "shard_query",
        key,
        lambda: _uncached_query_shards(
            repo_root,
            source=source,
            query=query,
            group=group,
            paragraph_id=paragraph_id,
            status=status,
            limit=limit,
            related_limit=related_limit,
        ),
        ttl_s=10.0,
    )


def _uncached_query_shards(
    repo_root: Path,
    *,
    source: str = "family",
    query: Optional[str] = None,
    group: Optional[str] = None,
    paragraph_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    related_limit: int = 40,
) -> Optional[Dict[str, Any]]:
    normalized_source = _normalize_shard_source(source)
    index = _load_shard_index(repo_root, source=normalized_source)
    if index is None:
        return None
    pool = index.list(
        status=status,
        group=group,
        paragraph_id=paragraph_id,
    )
    query_text = _shard_text(query)
    if query_text:
        payload = index.query_neighborhood(
            query_text,
            limit=limit,
            related_limit=related_limit,
            pool=pool,
        )
        results = payload.get("results") or []
        related = payload.get("related") or []
        graph_shards = [
            *(item.get("shard") for item in results if isinstance(item, Mapping)),
            *(item.get("shard") for item in related if isinstance(item, Mapping)),
        ]
        matched = int(payload.get("matched") or 0)
        total_in_index = int(payload.get("total_in_index") or index.total)
        total_in_pool = int(payload.get("total_in_pool") or len(pool))
    else:
        selected = pool[:limit] if limit > 0 else pool
        results = [
            {
                "shard_id": _shard_text(shard.get("id")),
                "shard": dict(shard),
                "score": 0,
                "matched_terms": [],
                "matched_axes": [],
            }
            for shard in selected
            if _shard_text(shard.get("id"))
        ]
        related = []
        graph_shards = [item.get("shard") for item in results if isinstance(item, Mapping)]
        matched = len(results)
        total_in_index = index.total
        total_in_pool = len(pool)
    return {
        "schema": "shard_lens_query_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": normalized_source,
        "source_path": _shard_source_path(index, repo_root=repo_root),
        "surface_kind": _shard_surface_kind(index),
        "freshness": _shard_freshness_for_path(index.path),
        "filters": {
            "query": query_text,
            "group": _shard_text(group) or None,
            "paragraph_id": _shard_text(paragraph_id) or None,
            "status": _shard_text(status) or None,
            "limit": limit,
            "related_limit": related_limit,
        },
        "matched": matched,
        "total_in_index": total_in_index,
        "total_in_pool": total_in_pool,
        "results": results,
        "related": related,
        "graph": _build_shard_graph(
            repo_root,
            [dict(shard) for shard in graph_shards if isinstance(shard, Mapping)],
        ),
    }


def load_shard_detail(
    repo_root: Path,
    shard_id: str,
    *,
    source: str = "family",
    neighbors: int = 3,
) -> Optional[Dict[str, Any]]:
    normalized_source = _normalize_shard_source(source)
    index = _load_shard_index(repo_root, source=normalized_source)
    if index is None:
        return None
    target = index.get(shard_id)
    if target is None:
        return None
    target = dict(target)
    window = index.neighborhood(shard_id, n=neighbors)
    paragraph_id = _shard_text(target.get("parent_paragraph_id"))
    paragraph_siblings = []
    if paragraph_id:
        paragraph_siblings = [
            dict(shard)
            for shard in index.list(paragraph_id=paragraph_id)
            if _shard_text(shard.get("id")) != shard_id
        ][:12]
    group_siblings = []
    for group_id in _group_ids_for_shard(target)[:6]:
        siblings = [
            dict(shard)
            for shard in index.list(group=group_id)
            if _shard_text(shard.get("id")) != shard_id
        ][:8]
        if siblings:
            group_siblings.append({"group_id": group_id, "siblings": siblings})

    graph_shards = [
        *(window.get("before") or []),
        target,
        *(window.get("after") or []),
        *paragraph_siblings[:6],
        *(sibling for bucket in group_siblings for sibling in bucket.get("siblings", [])[:4]),
    ]
    return {
        "schema": "shard_lens_detail_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": normalized_source,
        "source_path": _shard_source_path(index, repo_root=repo_root),
        "surface_kind": _shard_surface_kind(index),
        "freshness": _shard_freshness_for_path(index.path),
        "shard_id": shard_id,
        "authority": {"kind": "shard", "id": shard_id},
        "target": target,
        "neighborhood": window,
        "paragraph_siblings": paragraph_siblings,
        "group_siblings": group_siblings,
        "raw_seed_anchor": _resolve_shard_anchor(repo_root, target),
        "doctrine_refs": _top_doctrine_targets(repo_root, [target], limit=8),
        "file_refs": _top_facets(_shard_list(target.get("relevant_files")), limit=8),
        "graph": _build_shard_graph(repo_root, graph_shards),
    }


# =============================================================================
# Phase 08.12 — Cycle, System View, Unified Graph, Authority, Orchestration
# =============================================================================
# Doctrine refs: con_024, mech_023, mech_025 (authority chain contract),
# mech_026 (unified runtime graph lens). The loaders below remain read-only;
# every slice degrades to an empty structure when disk data is missing.

ORCHESTRATION_EVENTS_PATH = "tools/meta/control/orchestration_events.jsonl"
FACTORY_STATE_PATH = "tools/meta/factory/factory_state.json"
BRIDGE_DIAGNOSTICS_HINT = "tools/meta/bridge"

# Lifecycle mappings: project the native status vocabularies of mission graphs
# and observe groups into one shared enum so the unified graph lens can render
# them under a single lane chrome (mech_026 test #2).
_MISSION_STATUS_MAP = {
    "idle": "pending",
    "pending": "pending",
    "running": "running",
    "success": "success",
    "failure": "failure",
    "loaded": "success",
    "bridge_active": "running",
}

_OBSERVE_STATUS_MAP = {
    "pending": "pending",
    "running": "running",
    "success": "success",
    "failure": "failure",
    "skipped": "skipped",
    "aborted": "aborted",
}


def _map_mission_status(raw: Any) -> str:
    token = str(raw or "").strip().lower()
    return _MISSION_STATUS_MAP.get(token, "pending" if not token else token)


def _map_observe_status(raw: Any) -> str:
    token = str(raw or "").strip().lower()
    return _OBSERVE_STATUS_MAP.get(token, token or "pending")


# --- Phase reference resolution --------------------------------------------

def _resolve_phase_dir(repo_root: Path, phase_ref: str) -> Optional[str]:
    """Accept either a family-number style ref (`08.5`) or a repo-relative
    phase directory path, and return the repo-relative phase directory."""
    token = (phase_ref or "").strip()
    if not token:
        return None
    # If it's already a directory path, use it directly.
    candidate = repo_root / token
    if candidate.exists() and candidate.is_dir():
        return token
    # Try to interpret as a phase_id (08.5, 07_6) against the active family.
    family_dir = _resolve_active_family_dir(repo_root)
    if not family_dir:
        return None
    phases = _list_phase_dirs(repo_root, family_dir)
    normalized = token.replace("_", ".")
    for phase in phases:
        if phase["phase_id"] == token or phase["phase_id"] == normalized:
            return phase["phase_dir"]
    phase_family = _safe_read_json(repo_root, f"{family_dir}/phase_family.json") or {}
    family_tokens = {
        str(phase_family.get("family_number") or "").replace("_", ".").lstrip("0"),
        str(phase_family.get("family_id") or "").replace("_", ".").lstrip("0"),
    }
    family_token = normalized.lstrip("0")
    if family_token and family_token in family_tokens:
        active = _resolve_active_phase_record(
            phases=phases,
            phase_family=phase_family,
            bootstrap_bindings={},
            orchestration=None,
        )
        if active is not None:
            return str(active.get("phase_dir") or "").strip() or None
    return None


# --- Cycle loaders ---------------------------------------------------------

def _list_cycle_dirs(repo_root: Path, phase_dir: str) -> List[Tuple[int, str]]:
    phase = repo_root / phase_dir
    if not phase.exists() or not phase.is_dir():
        return []
    cycles: List[Tuple[int, str]] = []
    for child in phase.iterdir():
        if not child.is_dir():
            continue
        match = re.match(r"^cycle_(\d+)$", child.name)
        if not match:
            continue
        cycles.append((int(match.group(1)), child.name))
    cycles.sort()
    return cycles


def list_phase_cycles(repo_root: Path, phase_ref: str) -> List[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Return compact `CycleIndexEntry[]` rows for one phase.
    - Mechanism: Resolve the phase directory, walk `cycle_*` folders, summarize each `_cycle_summary.json`, and emit compact authority-tagged entries.
    - Guarantee: Returns newest-known cycle metadata for the requested phase, or [] when the phase cannot be resolved.
    - Fails: None.
    - When-needed: Open when the server needs a phase-local cycle index for UI navigation without loading full cycle payloads.
    - Escalates-to: system/server/world_model.py::load_cycle_summary; system/server/main.py
    """
    phase_dir = _resolve_phase_dir(repo_root, phase_ref)
    if not phase_dir:
        return []
    entries = []
    for cycle_num, cycle_name in _list_cycle_dirs(repo_root, phase_dir):
        summary = _safe_read_json(repo_root, f"{phase_dir}/{cycle_name}/_cycle_summary.json") or {}
        degradation = summary.get("degradation_summary") or {}
        degraded_count = degradation.get("degraded_count") or len(summary.get("degraded_groups") or [])
        probe_count = summary.get("probe_count") or 0
        runtime_state = summary.get("runtime_state") or "unknown"
        summary_line = (
            f"cycle {cycle_num} · {summary.get('phase') or 'probe'} · {probe_count} probes"
            f" · state={runtime_state}"
        )
        if degraded_count:
            summary_line += f" · {degraded_count} degraded"
        phase_id = _phase_id_for_dir(repo_root, phase_dir)
        entries.append(
            {
                "cycle": cycle_num,
                "phase_id": phase_id,
                "dir": f"{phase_dir}/{cycle_name}",
                "runtime_state": runtime_state,
                "timestamp": summary.get("timestamp"),
                "summary": summary_line,
                "authority": {
                    "kind": "cycle",
                    "id": f"{phase_id}/{cycle_num}" if phase_id else f"cycle/{cycle_num}",
                    "label": f"cycle {cycle_num}",
                },
            }
        )
    return entries


def _phase_id_for_dir(repo_root: Path, phase_dir: str) -> Optional[str]:
    name = Path(phase_dir).name
    match = re.match(r"^(\d+\.\d+)\s*-", name)
    return match.group(1) if match else None


def _condense_observe_groups(plan: Dict[str, Any], summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Project observe_plan.json groups + _cycle_summary.json diagnostics into
    unified group descriptors."""
    plan_groups = plan.get("groups") if isinstance(plan.get("groups"), list) else []
    diagnostics_list = summary.get("group_diagnostics") if isinstance(summary.get("group_diagnostics"), list) else []
    diagnostics = {
        str(entry.get("label") or "").strip(): entry
        for entry in diagnostics_list
        if isinstance(entry, dict)
    }
    out: List[Dict[str, Any]] = []
    for raw in plan_groups:
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("label") or "").strip()
        diag = diagnostics.get(label, {})
        status = _map_observe_status(diag.get("status") or "pending")
        targets = raw.get("targets") if isinstance(raw.get("targets"), list) else []
        target_files = [
            str(t.get("file") or "").strip()
            for t in targets
            if isinstance(t, dict) and t.get("file")
        ]
        out.append(
            {
                "label": label,
                "role": raw.get("role") or "probe",
                "status": status,
                "wave_index": raw.get("wave_index"),
                "depends_on": raw.get("depends_on") or [],
                "target_file_count": len(target_files),
                "target_files": target_files[:6],
                "receipt_path": diag.get("receipt_path"),
                "response_path": diag.get("response_path"),
                "error": diag.get("error"),
                "error_category": diag.get("error_category"),
                "error_stage": diag.get("error_stage"),
                "retry_reason": diag.get("retry_reason"),
            }
        )
    if not out and diagnostics_list:
        # Fallback to diagnostics-only when plan didn't load.
        for diag in diagnostics_list:
            if not isinstance(diag, dict):
                continue
            out.append(
                {
                    "label": diag.get("label") or "",
                    "role": diag.get("role") or "probe",
                    "status": _map_observe_status(diag.get("status") or "pending"),
                    "wave_index": diag.get("wave_index"),
                    "depends_on": [],
                    "target_file_count": 0,
                    "target_files": [],
                    "receipt_path": None,
                    "response_path": None,
                    "error": diag.get("error"),
                    "error_category": diag.get("error_category"),
                    "error_stage": diag.get("error_stage"),
                    "retry_reason": diag.get("retry_reason"),
                }
            )
    return out


def _condense_routing_decision(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not raw:
        return {}
    routing = raw.get("routing_decision") if isinstance(raw.get("routing_decision"), dict) else {}
    return {
        "decision": raw.get("decision") or routing.get("decision"),
        "next_phase": raw.get("next_phase") or routing.get("next_layer_kind"),
        "confidence": raw.get("confidence") or routing.get("confidence"),
        "reasoning": raw.get("reasoning"),
        "priority_action": raw.get("priority_action") or {},
        "adopted_shard_ids": routing.get("adopted_shard_ids") or [],
        "artifact_meta": raw.get("artifact_meta") or {},
    }


def _condense_carry_forward(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not raw:
        return {}
    return {
        "active_scope_files": raw.get("active_scope_files") or [],
        "known_relevant_files": raw.get("known_relevant_files") or [],
        "newly_relevant_files": raw.get("newly_relevant_files") or [],
        "files_examined": raw.get("files_examined") or [],
        "widened_files_outside_scope": raw.get("widened_files_outside_scope") or [],
    }


def load_cycle_summary(repo_root: Path, phase_ref: str, cycle_number: int) -> Optional[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Compose the backend's full cycle summary payload from the cycle's observe, routing, and carry-forward artifacts.
    - Mechanism: Resolve the phase and cycle directory, load the cycle JSON artifacts, condense observe groups, and return a single `cycle_summary_v1` mapping.
    - Guarantee: Returns a cycle summary with groups, routing_decision, carry_forward, and freshness metadata when the cycle exists; otherwise returns None.
    - Fails: None.
    - When-needed: Open when a route or debug pass needs the authoritative per-cycle payload instead of the lighter cycle index.
    - Escalates-to: system/server/main.py; system/server/schemas.py
    - Navigation-group: server_backend
    """
    phase_dir = _resolve_phase_dir(repo_root, phase_ref)
    if not phase_dir:
        return None
    cycle_name = f"cycle_{cycle_number}"
    cycle_dir = f"{phase_dir}/{cycle_name}"
    if not (repo_root / cycle_dir).exists():
        return None
    plan = _safe_read_json(repo_root, f"{cycle_dir}/observe_plan.json") or {}
    summary = _safe_read_json(repo_root, f"{cycle_dir}/_cycle_summary.json") or {}
    routing = _safe_read_json(repo_root, f"{cycle_dir}/routing_decision.json") or {}
    carry = _safe_read_json(repo_root, f"{cycle_dir}/carry_forward_context.json") or {}
    assim = _safe_read_json(repo_root, f"{cycle_dir}/cycle_assimilation.json") or {}
    phase_id = _phase_id_for_dir(repo_root, phase_dir)
    groups = _condense_observe_groups(plan, summary)
    runtime_state = summary.get("runtime_state") or "unknown"
    return {
        "schema": "cycle_summary_v1",
        "cycle": cycle_number,
        "phase_id": phase_id,
        "phase_dir": phase_dir,
        "cycle_dir": cycle_dir,
        "runtime_state": runtime_state,
        "timestamp": summary.get("timestamp"),
        "session_id": summary.get("session_id"),
        "observe_plan_path": f"{cycle_dir}/observe_plan.json",
        "observe_manifest_path": summary.get("observe_manifest_path"),
        "groups": groups,
        "degraded_groups": summary.get("degraded_groups") or [],
        "degradation_summary": summary.get("degradation_summary") or {},
        "routing_decision": _condense_routing_decision(routing),
        "carry_forward": _condense_carry_forward(carry),
        "assimilation_path": f"{cycle_dir}/cycle_assimilation.json"
        if (repo_root / f"{cycle_dir}/cycle_assimilation.json").exists()
        else None,
        "assimilation_kind": assim.get("kind"),
        "selected_shard_ids": summary.get("selected_shard_ids") or [],
        "authority": {
            "kind": "cycle",
            "id": f"{phase_id}/{cycle_number}" if phase_id else f"cycle/{cycle_number}",
            "label": f"cycle {cycle_number}",
        },
        "freshness": compute_freshness(summary.get("timestamp")),
    }


# --- System view projection ------------------------------------------------

_SYSTEM_VIEW_KIND_MAP = {
    ".py": "py",
    ".ts": "ts",
    ".tsx": "tsx",
    ".json": "json",
    ".md": "md",
}


def _classify_system_view_file(path: str) -> Tuple[str, str]:
    lower = path.lower()
    suffix = Path(lower).suffix
    kind = _SYSTEM_VIEW_KIND_MAP.get(suffix, "other")
    if lower.startswith("codex/substrate/") or lower.startswith("codex/standards/"):
        group = "substrate"
    elif lower.startswith("codex/doctrine/"):
        group = "doctrine"
    elif lower.startswith("codex/"):
        group = "codex"
    elif lower.startswith("system/server/ui/"):
        group = "ui"
    elif lower.startswith("system/"):
        group = "system"
    elif lower.startswith("tools/"):
        group = "tools"
    elif lower.startswith("obsidian/"):
        group = "obsidian"
    elif lower.startswith("docs/"):
        group = "docs"
    elif lower.startswith("annexes/"):
        group = "annexes"
    elif lower.startswith(".") or "/." in lower:
        group = "config"
    elif "/" not in lower:
        group = "root"
    else:
        # Use the first path segment as the group.
        group = lower.split("/", 1)[0] or "other"
    return kind, group


def load_system_view_projection(
    repo_root: Path, phase_ref: str, sample_limit: int = 80
) -> Optional[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Sample a phase's `system_view.json` into a bounded projection suitable for the browser.
    - Mechanism: Resolve the phase, read `system_view.json`, aggregate file kinds/groups, and capture up to `sample_limit` representative files.
    - Guarantee: Returns a `system_view_projection_v1` payload or None when the phase/system view cannot be loaded.
    - Fails: None.
    - When-needed: Open when the server needs a lightweight projection of a phase system view rather than the full topology index.
    - Escalates-to: system/server/world_model.py::load_topology_index; system/server/main.py
    """
    phase_dir = _resolve_phase_dir(repo_root, phase_ref)
    if not phase_dir:
        return None
    file_entries, full_rel, generated_at = _phase_file_inventory(repo_root, phase_dir)
    if not file_entries:
        return None
    groups: Dict[str, int] = {}
    kinds: Dict[str, int] = {}
    sampled: List[Dict[str, Any]] = []
    for entry in file_entries:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path") or "").strip()
        if not path:
            continue
        kind, group = _classify_system_view_file(path)
        groups[group] = groups.get(group, 0) + 1
        kinds[kind] = kinds.get(kind, 0) + 1
        if len(sampled) < sample_limit:
            sampled.append(
                {
                    "path": path,
                    "size_bytes": entry.get("size_bytes") or entry.get("size"),
                    "kind": kind,
                    "group": group,
                }
            )
    return {
        "schema": "system_view_projection_v1",
        "generated_at": generated_at,
        "phase_id": _phase_id_for_dir(repo_root, phase_dir),
        "phase_dir": phase_dir,
        "file_count": len(file_entries),
        "groups": groups,
        "kinds": kinds,
        "sampled_files": sampled,
        "sample_limit": sample_limit,
        "full_path": full_rel,
        "freshness": compute_freshness(generated_at),
    }


# --- Orchestration event stream --------------------------------------------

def load_orchestration_events(repo_root: Path, limit: int = 20) -> List[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Expose the newest orchestration events as browser-friendly summaries.
    - Mechanism: Tail `orchestration_events.jsonl`, parse dict-shaped rows, and condense each event to the fields the UI needs.
    - Guarantee: Returns newest-first event summaries up to `limit`; unreadable lines or missing files degrade to [].
    - Fails: None.
    - When-needed: Open when an operator-facing route needs recent orchestration activity without loading the whole JSONL event log.
    - Escalates-to: system/server/world_model.py::load_attention_snapshot; system/server/main.py
    """
    path = repo_root / ORCHESTRATION_EVENTS_PATH
    if not path.exists() or not path.is_file():
        return []
    # Tail the jsonl — walk from the end so we avoid loading huge logs.
    try:
        with path.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except Exception:
        return []
    tail = lines[-max(limit, 1):]
    out: List[Dict[str, Any]] = []
    for raw_line in tail:
        line = raw_line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        coordination = data.get("coordination") or {}
        out.append(
            {
                "event_id": data.get("event_id"),
                "kind": data.get("kind") or "orchestration_event",
                "recorded_at": data.get("recorded_at"),
                "active_driver": data.get("active_driver"),
                "immediate_mode": data.get("immediate_mode"),
                "summary": data.get("summary"),
                "gate_reason": data.get("gate_reason"),
                "gate_owner": data.get("gate_owner"),
                "current_owner": coordination.get("current_owner"),
                "next_handoff": coordination.get("next_handoff"),
                "drivers": [
                    {
                        "driver_id": d.get("driver_id"),
                        "stage": d.get("stage"),
                        "blocked": bool(d.get("blocked")),
                        "gate_reason": d.get("gate_reason"),
                        "next_summary": d.get("next_summary"),
                        "next_command": d.get("next_command"),
                        "state_path": d.get("state_path"),
                        "last_updated": d.get("last_updated"),
                    }
                    for d in (data.get("drivers") or [])
                    if isinstance(d, dict)
                ],
                "docs_route_focus": coordination.get("docs_route_focus"),
                "active_directive": coordination.get("active_directive"),
                "system_view": coordination.get("system_view"),
                "freshness": compute_freshness(data.get("recorded_at")),
            }
        )
    # Tail order is oldest-first; reverse so the caller gets newest-first.
    out.reverse()
    return out


# --- Unified runtime graph -------------------------------------------------

def _unified_lane_for_mission(lane: str) -> Dict[str, Any]:
    return {
        "id": f"mission:{lane}",
        "label": str(lane),
        "class": "mission_spine" if str(lane).upper() == "SPINE" else "mission_data",
        "runtime": "mission",
    }


def _collect_meta_slice(
    repo_root: Path, phase_ref: Optional[str], cycle_number: Optional[int]
) -> Dict[str, Any]:
    """Compose observe-apply lanes/nodes for the unified graph."""
    phase_dir = _resolve_phase_dir(repo_root, phase_ref) if phase_ref else None
    if not phase_dir:
        return {"lanes": [], "nodes": [], "edges": []}
    # Pick the requested cycle or the latest one.
    cycles = _list_cycle_dirs(repo_root, phase_dir)
    if not cycles:
        return {"lanes": [], "nodes": [], "edges": []}
    if cycle_number is None:
        cycle_number = cycles[-1][0]
    cycle_dir_name = f"cycle_{cycle_number}"
    if not (repo_root / phase_dir / cycle_dir_name).exists():
        return {"lanes": [], "nodes": [], "edges": []}
    plan = _safe_read_json(repo_root, f"{phase_dir}/{cycle_dir_name}/observe_plan.json") or {}
    summary = _safe_read_json(repo_root, f"{phase_dir}/{cycle_dir_name}/_cycle_summary.json") or {}
    groups = _condense_observe_groups(plan, summary)
    phase_id = _phase_id_for_dir(repo_root, phase_dir)
    lanes_by_role: Dict[str, Dict[str, Any]] = {}
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    for group in groups:
        role = group["role"]
        lane_id = f"observe:{role}"
        if lane_id not in lanes_by_role:
            lanes_by_role[lane_id] = {
                "id": lane_id,
                "label": f"observe · {role}",
                "class": "observe_synthesis" if role == "synthesis" else "observe_group",
                "runtime": "meta",
                "phase_id": phase_id,
                "cycle": str(cycle_number),
            }
        node_id = f"{phase_id}:{cycle_number}:{group['label']}"
        nodes.append(
            {
                "id": node_id,
                "lane_id": lane_id,
                "label": group["label"],
                "kind": "observe_group",
                "status": group["status"],
                "wave": group.get("wave_index"),
                "depends_on": [
                    f"{phase_id}:{cycle_number}:{d}" for d in (group.get("depends_on") or [])
                ],
                "started_at": summary.get("timestamp"),
                "ended_at": summary.get("timestamp"),
                "authority": {
                    "kind": "observe_group",
                    "id": node_id,
                    "label": group["label"],
                },
                "detail": {
                    "error": group.get("error"),
                    "error_category": group.get("error_category"),
                    "error_stage": group.get("error_stage"),
                    "target_file_count": group.get("target_file_count"),
                },
            }
        )
        for dep in group.get("depends_on") or []:
            edges.append(
                {
                    "id": f"edge:{dep}->{group['label']}",
                    "source": f"{phase_id}:{cycle_number}:{dep}",
                    "target": node_id,
                    "kind": "depends_on",
                }
            )
    return {
        "lanes": list(lanes_by_role.values()),
        "nodes": nodes,
        "edges": edges,
    }


def _collect_factory_slice(repo_root: Path) -> Dict[str, Any]:
    factory = _safe_read_json(repo_root, FACTORY_STATE_PATH) or {}
    if not factory:
        return {"lanes": [], "nodes": [], "edges": []}
    stage = factory.get("stage") or "unknown"
    freshness = compute_freshness(factory.get("last_run"))
    live = freshness.get("tone") in {"fresh", "stale"}
    blocked = bool(factory.get("blocked") or stage.endswith("_pending"))
    status = "historical" if not live else ("blocked" if blocked else "running")
    lane = {
        "id": "factory:default",
        "label": "factory lane",
        "class": "factory",
        "runtime": "factory",
    }
    node = {
        "id": f"factory:{stage}",
        "lane_id": lane["id"],
        "label": stage,
        "kind": "factory_stage",
        "status": status,
        "wave": None,
        "depends_on": [],
        "started_at": factory.get("last_run"),
        "ended_at": factory.get("last_run"),
        "authority": {
            "kind": "artifact",
            "id": "factory_state.json",
            "label": "factory state",
        },
        "detail": {
            "gate_reason": factory.get("gate_reason"),
            "freshness": freshness,
            "role": "runtime_signal" if live else "historical_snapshot",
        },
    }
    return {"lanes": [lane], "nodes": [node], "edges": []}


def _collect_mission_slice(repo_root: Path, mission_name: Optional[str]) -> Dict[str, Any]:
    """Render the current mission graph into unified node/lane form.

    We import `compile_mission_view` lazily so world_model stays importable
    even in test contexts that don't build the mission graph pipeline.
    """
    if not mission_name:
        return {"lanes": [], "nodes": [], "edges": []}
    try:
        from system.server.translator import Translator, TranslationError  # type: ignore
        from system.server.graph import compile_mission_view  # type: ignore
    except Exception:
        return {"lanes": [], "nodes": [], "edges": []}
    try:
        translator = Translator(repo_root)
        lobby = translator.scan_lobby()
    except Exception:
        return {"lanes": [], "nodes": [], "edges": []}
    target_id = None
    for mission in lobby.missions:
        if mission.name == mission_name:
            target_id = mission.target_id
            break
    if not target_id:
        return {"lanes": [], "nodes": [], "edges": []}
    try:
        graph_view = compile_mission_view(repo_root, target_id)
    except Exception:
        return {"lanes": [], "nodes": [], "edges": []}
    lanes_seen: Dict[str, Dict[str, Any]] = {}
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    for raw_node in getattr(graph_view, "nodes", []) or []:
        lane = str(getattr(raw_node, "lane", "") or "SPINE")
        lane_id = f"mission:{lane}"
        if lane_id not in lanes_seen:
            lanes_seen[lane_id] = _unified_lane_for_mission(lane)
            lanes_seen[lane_id]["mission_name"] = mission_name
        nodes.append(
            {
                "id": getattr(raw_node, "id", ""),
                "lane_id": lane_id,
                "label": getattr(raw_node, "label", "") or getattr(raw_node, "id", ""),
                "kind": "mission_node",
                "status": _map_mission_status("pending"),
                "wave": getattr(raw_node, "wave", None),
                "depends_on": list(getattr(raw_node, "dependencies", []) or []),
                "started_at": None,
                "ended_at": None,
                "authority": {
                    "kind": "node",
                    "id": getattr(raw_node, "id", ""),
                    "label": getattr(raw_node, "label", "") or getattr(raw_node, "id", ""),
                },
                "detail": {
                    "teleology": getattr(raw_node, "teleology", None),
                    "mechanism": getattr(raw_node, "mechanism", None),
                },
            }
        )
    for raw_edge in getattr(graph_view, "edges", []) or []:
        edges.append(
            {
                "id": getattr(raw_edge, "id", ""),
                "source": getattr(raw_edge, "source", ""),
                "target": getattr(raw_edge, "target", ""),
                "kind": "depends_on",
            }
        )
    return {
        "lanes": list(lanes_seen.values()),
        "nodes": nodes,
        "edges": edges,
    }


def load_unified_runtime_graph(
    repo_root: Path,
    *,
    mission_name: Optional[str] = None,
    phase_ref: Optional[str] = None,
    cycle: Optional[int] = None,
    include: Tuple[str, ...] = ("meta", "factory"),
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Compose the unified runtime graph across the requested runtimes.
    - Mechanism: Collect mission, meta, and factory slices on demand, then merge their lanes, nodes, and edges into one response payload.
    - Guarantee: Returns a `unified_runtime_graph_v1` payload even when one or more requested slices are empty.
    - Fails: None.
    - When-needed: Open when the server backend needs the merged mission/meta/factory runtime graph that powers the cockpit runtime lens.
    - Escalates-to: system/server/main.py; system/server/translator.py; system/server/schemas.py
    - Navigation-group: server_backend
    """
    lanes: List[Dict[str, Any]] = []
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    if "mission" in include:
        slice_ = _collect_mission_slice(repo_root, mission_name)
        lanes.extend(slice_["lanes"])
        nodes.extend(slice_["nodes"])
        edges.extend(slice_["edges"])
    if "meta" in include:
        slice_ = _collect_meta_slice(repo_root, phase_ref, cycle)
        lanes.extend(slice_["lanes"])
        nodes.extend(slice_["nodes"])
        edges.extend(slice_["edges"])
    if "factory" in include:
        slice_ = _collect_factory_slice(repo_root)
        lanes.extend(slice_["lanes"])
        nodes.extend(slice_["nodes"])
        edges.extend(slice_["edges"])

    return {
        "schema": "unified_runtime_graph_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lanes": lanes,
        "nodes": nodes,
        "edges": edges,
        "scope": {
            "runtimes": list(include),
            "mission_name": mission_name,
            "phase_ref": phase_ref,
            "cycle": cycle,
        },
    }


# --- Authority chain resolver (mech_025) -----------------------------------

_RAW_SEED_PARAGRAPH_RE = re.compile(r"par_[\w.]+")
_RAW_SEED_SECTION_RE = re.compile(r"\brs_section_[\w.]+")
_PRINCIPLE_RE = re.compile(r"\bpri_[\w-]+")
_CONCEPT_RE = re.compile(r"\bcon_[\w-]+")
_MECHANISM_RE = re.compile(r"\bmech_[\w-]+")
_STANDARD_RE = re.compile(r"\bstd_[\w-]+")
_SHARD_RE = re.compile(r"\b(?:rg\d+_[\w-]+|shard_[\w-]+)")


def _classify_tokens(text: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: set = set()

    def add(kind: str, token: str) -> None:
        key = (kind, token)
        if key in seen:
            return
        seen.add(key)
        out.append({"kind": kind, "id": token})

    for match in _RAW_SEED_PARAGRAPH_RE.findall(text):
        add("raw_seed_paragraph", match)
    for match in _RAW_SEED_SECTION_RE.findall(text):
        add("raw_seed_section", match)
    for match in _PRINCIPLE_RE.findall(text):
        add("principle", match)
    for match in _CONCEPT_RE.findall(text):
        add("concept", match)
    for match in _MECHANISM_RE.findall(text):
        add("mechanism", match)
    for match in _STANDARD_RE.findall(text):
        add("standard", match)
    for match in _SHARD_RE.findall(text):
        add("shard", match)
    return out


def _make_rung(
    kind: str,
    id_: str,
    *,
    label: Optional[str] = None,
    summary: Optional[str] = None,
    source_path: Optional[str] = None,
    grounds: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "kind": kind,
        "id": id_,
        "label": label,
        "summary": summary,
        "source_path": source_path,
        "grounds": grounds or [],
    }


def _principle_rung(repo_root: Path, principle_id: str) -> Optional[Dict[str, Any]]:
    record = resolve_principle(repo_root, principle_id)
    if not record:
        return None
    return _make_rung(
        "principle",
        principle_id,
        label=record.get("title"),
        summary=record.get("statement"),
        source_path=_principles_path_for_active_family(_resolve_active_family_dir(repo_root)),
    )


def _concept_rung(repo_root: Path, concept_id: str) -> Optional[Dict[str, Any]]:
    record = resolve_concept(repo_root, concept_id)
    if not record:
        return None
    return _make_rung(
        "concept",
        concept_id,
        label=record.get("title"),
        summary=record.get("statement"),
        source_path=record.get("__path__"),
    )


def _mechanism_rung(repo_root: Path, mechanism_id: str) -> Optional[Dict[str, Any]]:
    record = resolve_mechanism(repo_root, mechanism_id)
    if not record:
        return None
    return _make_rung(
        "mechanism",
        mechanism_id,
        label=record.get("title"),
        summary=record.get("statement"),
        source_path=record.get("__path__"),
    )


def _authority_chain_for_principle(repo_root: Path, principle_id: str) -> Dict[str, Any]:
    record = resolve_principle(repo_root, principle_id) or {}
    rungs: List[Dict[str, Any]] = []
    for entry in record.get("evidence") or []:
        if not isinstance(entry, dict):
            continue
        ref = entry.get("ref")
        if not ref:
            continue
        kind = "raw_seed_paragraph" if str(ref).startswith("par_") else "shard"
        rungs.append(_make_rung(kind, str(ref), summary=entry.get("gloss")))
    # Also surface the owning principle rung itself.
    rungs.append(
        _make_rung(
            "principle",
            principle_id,
            label=record.get("title"),
            summary=record.get("statement"),
        )
    )
    return {
        "schema": "authority_chain_v1",
        "handle": {"kind": "principle", "id": principle_id, "label": record.get("title")},
        "title": record.get("title") or principle_id,
        "teleology": record.get("statement"),
        "ontology": f"pri_{principle_id}" if not str(principle_id).startswith("pri_") else None,
        "rungs": rungs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _authority_chain_for_concept(repo_root: Path, concept_id: str) -> Dict[str, Any]:
    record = resolve_concept(repo_root, concept_id) or {}
    rungs: List[Dict[str, Any]] = []
    for edge in record.get("principle_edges") or []:
        if not isinstance(edge, dict):
            continue
        target = edge.get("target")
        if not target:
            continue
        rung = _principle_rung(repo_root, target) or _make_rung(
            "principle", str(target), summary=edge.get("gloss")
        )
        rungs.append(rung)
    for edge in record.get("mechanism_edges") or []:
        if not isinstance(edge, dict):
            continue
        target = edge.get("target")
        if not target:
            continue
        rung = _mechanism_rung(repo_root, target) or _make_rung(
            "mechanism", str(target), summary=edge.get("gloss")
        )
        rungs.append(rung)
    rungs.append(
        _make_rung(
            "concept",
            concept_id,
            label=record.get("title"),
            summary=record.get("statement"),
            source_path=record.get("__path__"),
        )
    )
    return {
        "schema": "authority_chain_v1",
        "handle": {"kind": "concept", "id": concept_id, "label": record.get("title")},
        "title": record.get("title") or concept_id,
        "teleology": record.get("statement"),
        "ontology": None,
        "rungs": rungs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _authority_chain_for_mechanism(repo_root: Path, mechanism_id: str) -> Dict[str, Any]:
    record = resolve_mechanism(repo_root, mechanism_id) or {}
    rungs: List[Dict[str, Any]] = []
    for edge in record.get("concept_edges") or []:
        if not isinstance(edge, dict):
            continue
        target = edge.get("target")
        if not target:
            continue
        rung = _concept_rung(repo_root, target) or _make_rung(
            "concept", str(target), summary=edge.get("gloss")
        )
        rungs.append(rung)
    for locus in record.get("code_loci") or []:
        if not isinstance(locus, dict):
            continue
        path = locus.get("path")
        if not path:
            continue
        rungs.append(
            _make_rung(
                "doc",
                str(path),
                label=str(path).split("/")[-1],
                summary=locus.get("role"),
                source_path=str(path),
            )
        )
    rungs.append(
        _make_rung(
            "mechanism",
            mechanism_id,
            label=record.get("title"),
            summary=record.get("statement"),
            source_path=record.get("__path__"),
        )
    )
    return {
        "schema": "authority_chain_v1",
        "handle": {"kind": "mechanism", "id": mechanism_id, "label": record.get("title")},
        "title": record.get("title") or mechanism_id,
        "teleology": record.get("statement"),
        "ontology": None,
        "rungs": rungs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _authority_chain_for_phase(repo_root: Path, phase_id: str) -> Dict[str, Any]:
    phase_dir = _resolve_phase_dir(repo_root, phase_id)
    rungs: List[Dict[str, Any]] = []
    if phase_dir:
        scaffold = _safe_read_json(repo_root, f"{phase_dir}/phase_scaffold.json") or {}
        synth = _safe_read_json(repo_root, f"{phase_dir}/synth_seed.json") or {}
        if scaffold.get("raw_seed_path"):
            rungs.append(
                _make_rung(
                    "doc",
                    scaffold.get("raw_seed_path"),
                    label="raw_seed.md",
                    source_path=scaffold.get("raw_seed_path"),
                )
            )
        summary = synth.get("summary") or scaffold.get("title")
        rungs.append(
            _make_rung(
                "phase",
                phase_id,
                label=phase_dir.split("/")[-1],
                summary=summary,
                source_path=phase_dir,
            )
        )
    # Add governing doctrine links (hardcoded for now — these are the mechanisms
    # that actually govern phase lifecycle; future work can derive this).
    for mech in ("mech_021", "mech_023"):
        rung = _mechanism_rung(repo_root, mech)
        if rung:
            rungs.append(rung)
    family_dir = _resolve_active_family_dir(repo_root)
    return {
        "schema": "authority_chain_v1",
        "handle": {"kind": "phase", "id": phase_id, "label": phase_id},
        "title": f"Phase {phase_id}",
        "teleology": "Phase-native runtime lifecycle projection" if phase_dir else None,
        "ontology": None,
        "rungs": rungs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "extras": {"family_dir": family_dir, "phase_dir": phase_dir},
    }


def _authority_chain_for_cycle(repo_root: Path, ref_id: str) -> Dict[str, Any]:
    """ref_id is either `<phase_id>/<n>` or `cycle/<n>`."""
    parts = ref_id.split("/")
    phase_id = None
    cycle_number: Optional[int] = None
    if len(parts) == 2:
        phase_id = parts[0] if parts[0] != "cycle" else None
        try:
            cycle_number = int(parts[1])
        except ValueError:
            cycle_number = None
    rungs: List[Dict[str, Any]] = []
    if phase_id and cycle_number is not None:
        cycle_payload = load_cycle_summary(repo_root, phase_id, cycle_number)
        if cycle_payload:
            rungs.append(
                _make_rung(
                    "cycle",
                    ref_id,
                    label=f"cycle {cycle_number}",
                    summary=(cycle_payload.get("routing_decision") or {}).get("reasoning"),
                    source_path=cycle_payload.get("cycle_dir"),
                )
            )
            if cycle_payload.get("observe_plan_path"):
                rungs.append(
                    _make_rung(
                        "doc",
                        cycle_payload["observe_plan_path"],
                        label="observe_plan.json",
                        source_path=cycle_payload["observe_plan_path"],
                    )
                )
            if cycle_payload.get("assimilation_path"):
                rungs.append(
                    _make_rung(
                        "doc",
                        cycle_payload["assimilation_path"],
                        label="cycle_assimilation.json",
                        source_path=cycle_payload["assimilation_path"],
                    )
                )
    # Chain up into the phase chain.
    if phase_id:
        phase_chain = _authority_chain_for_phase(repo_root, phase_id)
        for rung in phase_chain.get("rungs") or []:
            rungs.append(rung)
    return {
        "schema": "authority_chain_v1",
        "handle": {"kind": "cycle", "id": ref_id, "label": ref_id},
        "title": f"Cycle {ref_id}",
        "teleology": "Cycle-native observe-apply projection",
        "ontology": None,
        "rungs": rungs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _authority_chain_for_shard(repo_root: Path, shard_id: str) -> Dict[str, Any]:
    record, source_path = _resolve_shard_record(repo_root, shard_id)
    record = record or {}
    summary = _shard_text(
        record.get("clarified_statement")
        or record.get("statement")
        or record.get("gloss")
        or record.get("text")
    ) or None
    rungs: List[Dict[str, Any]] = [
        _make_rung(
            "shard",
            shard_id,
            label=record.get("id") or shard_id,
            summary=summary,
            source_path=source_path,
        )
    ]

    raw_seed_record = _resolve_shard_anchor(repo_root, record) if record else None
    if raw_seed_record:
        raw_seed_id = _shard_text(
            raw_seed_record.get("id")
            or raw_seed_record.get("paragraph_id")
            or raw_seed_record.get("section_id")
            or raw_seed_record.get("ref")
            or shard_id
        )
        raw_seed_kind = "raw_seed_paragraph" if raw_seed_id.startswith("par_") else "raw_seed_section"
        rungs.append(
            _make_rung(
                raw_seed_kind,
                raw_seed_id,
                label=raw_seed_record.get("label") or raw_seed_id,
                summary=raw_seed_record.get("text") or raw_seed_record.get("excerpt"),
                source_path=raw_seed_record.get("__index_path__"),
            )
        )

    for concept_id in _shard_list(record.get("concept_ids")):
        rung = _concept_rung(repo_root, concept_id) or _make_rung("concept", concept_id)
        rungs.append(rung)

    for mechanism_id in _shard_list(record.get("mechanisms")):
        rung = _mechanism_rung(repo_root, mechanism_id) or _make_rung("mechanism", mechanism_id)
        rungs.append(rung)

    for file_path in _shard_list(record.get("relevant_files"))[:6]:
        rungs.append(
            _make_rung(
                "doc",
                file_path,
                label=Path(file_path).name or file_path,
                source_path=file_path,
            )
        )

    return {
        "schema": "authority_chain_v1",
        "handle": {"kind": "shard", "id": shard_id, "label": record.get("id") or shard_id},
        "title": record.get("id") or shard_id,
        "teleology": summary,
        "ontology": None,
        "rungs": rungs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "extras": {"source_path": source_path},
    }


def _authority_chain_for_free_text(
    repo_root: Path, handle_kind: str, handle_id: str, text: str
) -> Dict[str, Any]:
    """Fallback: mine authority tokens out of a freeform text body."""
    tokens = _classify_tokens(text)
    rungs: List[Dict[str, Any]] = []
    for token in tokens:
        kind = token["kind"]
        value = token["id"]
        if kind == "principle":
            rung = _principle_rung(repo_root, value) or _make_rung(kind, value)
        elif kind == "concept":
            rung = _concept_rung(repo_root, value) or _make_rung(kind, value)
        elif kind == "mechanism":
            rung = _mechanism_rung(repo_root, value) or _make_rung(kind, value)
        else:
            rung = _make_rung(kind, value)
        rungs.append(rung)
    return {
        "schema": "authority_chain_v1",
        "handle": {"kind": handle_kind, "id": handle_id, "label": handle_id},
        "title": handle_id,
        "teleology": None,
        "ontology": None,
        "rungs": rungs,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def resolve_authority_chain(
    repo_root: Path, kind: str, id_: str
) -> Optional[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Resolve a typed AuthorityChain for any UI handle.
    - Mechanism: Normalize the handle kind, route to the corresponding principle/concept/mechanism/phase/cycle/raw-seed resolver, and fall back to free-text token mining for lightweight handles.
    - Guarantee: Returns an `authority_chain_v1` payload for supported handle kinds and known ids; unsupported kinds or empty ids return None.
    - Fails: None.
    - When-needed: Open when a server route needs the canonical authority-chain resolver behind doctrine, phase, cycle, or raw-seed drill-down.
    - Escalates-to: system/server/main.py; system/server/schemas.py
    - Navigation-group: server_backend
    """
    kind_norm = (kind or "").strip().lower()
    if not id_:
        return None
    if kind_norm == "principle":
        return _authority_chain_for_principle(repo_root, id_)
    if kind_norm == "concept":
        return _authority_chain_for_concept(repo_root, id_)
    if kind_norm == "mechanism":
        return _authority_chain_for_mechanism(repo_root, id_)
    if kind_norm == "shard":
        return _authority_chain_for_shard(repo_root, id_)
    if kind_norm == "phase":
        return _authority_chain_for_phase(repo_root, id_)
    if kind_norm == "cycle":
        return _authority_chain_for_cycle(repo_root, id_)
    if kind_norm in ("raw_seed", "raw_seed_paragraph", "raw_seed_section"):
        record = resolve_raw_seed_anchor(repo_root, id_) or {}
        rungs = [
            _make_rung(
                "raw_seed_paragraph" if str(id_).startswith("par_") else "raw_seed_section",
                id_,
                label=str(record.get("label") or id_),
                summary=str(record.get("text") or record.get("excerpt") or ""),
                source_path=record.get("__index_path__"),
            )
        ]
        return {
            "schema": "authority_chain_v1",
            "handle": {"kind": "raw_seed", "id": id_, "label": id_},
            "title": id_,
            "teleology": record.get("text") or record.get("excerpt"),
            "ontology": None,
            "rungs": rungs,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    if kind_norm in ("node", "mission_node", "observe_group", "artifact"):
        # The id for nodes/artifacts typically includes free text teleology +
        # mechanism; without a mission-side resolver we fall back to empty.
        return _authority_chain_for_free_text(repo_root, kind_norm, id_, "")
    return None


# --- Reference acquisitions (pri_071) --------------------------------------

def load_reference_acquisitions(repo_root: Path) -> List[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Expose the most recent bridge-native reference acquisition receipts to the cockpit lens.
    - Mechanism: Scan `tools/meta/apply/observe_history/entries`, keep dict-shaped reference acquisition records, and emit compact summaries for the newest matching entries.
    - Guarantee: Returns up to the newest matching receipt summaries and degrades to [] when the receipt surface is absent.
    - Fails: None.
    - When-needed: Open when the backend needs the reference-acquisition receipt feed without reading raw observe-history entry files directly.
    - Escalates-to: system/server/main.py; system/server/schemas.py
    """
    base = repo_root / "tools/meta/apply/observe_history/entries"
    if not base.exists() or not base.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    for entry in sorted(base.iterdir())[-20:]:
        if not entry.is_file() or entry.suffix != ".json":
            continue
        try:
            with entry.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        kind = str(data.get("kind") or "").strip()
        if "reference_acquisition" not in kind and "reference" not in kind:
            continue
        out.append(
            {
                "id": data.get("id") or entry.stem,
                "kind": kind,
                "target": data.get("target"),
                "source": data.get("source"),
                "summary": data.get("summary"),
                "generated_at": data.get("generated_at"),
                "entry_path": str(entry.relative_to(repo_root)),
            }
        )
    return out


# =============================================================================
# Phase 08.13 — Attention-first, topology, actionable orchestration
# =============================================================================


def _driver_next_action(driver: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(driver, dict):
        return None
    summary = driver.get("next_summary") or ((driver.get("next_action") or {}).get("summary"))
    command = driver.get("next_command") or ((driver.get("next_action") or {}).get("command"))
    if not summary and not command:
        return None
    return {"summary": summary, "command": command}


def _score_attention_item(*, blocked: bool, gate_reason: Optional[str], age_seconds: Optional[int]) -> int:
    score = 0
    if blocked:
        score += 120
    if gate_reason:
        token = gate_reason.lower()
        if "review" in token or "pending" in token or "block" in token:
            score += 80
        elif "lock" in token:
            score += 40
    if age_seconds is None:
        score += 5
    elif age_seconds < 3600:
        score += 30
    elif age_seconds < 24 * 3600:
        score += 15
    return score


def _build_attention_snapshot(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Assemble the home-station attention projection.
    - Mechanism: Read orchestration/bootstrap/system-map state, derive the active phase and cycle, rank operator attention items, and package recent changes, next moves, bridge health, and drift signals.
    - Guarantee: Returns an `attention_snapshot_v1` payload with banner, current_driver, next_handoff, active phase/cycle context, ranked attention items, and drift metadata.
    - Fails: None — missing subordinate surfaces collapse to partial slices instead of aborting the attention snapshot.
    - When-needed: Open when a server route or cockpit bug needs the canonical attention/home-station payload instead of reconstructing it from orchestration and cycle helpers manually.
    - Escalates-to: system/server/main.py; system/server/world_model.py::load_cycle_summary; system/server/schemas.py
    - Navigation-group: server_backend
    """
    generated = datetime.now(timezone.utc).isoformat()
    orchestration = _safe_read_json(repo_root, ORCHESTRATION_STATE_PATH) or {}
    bootstrap = _safe_read_json(repo_root, AGENT_BOOTSTRAP_LIVE_PATH) or {}
    bindings = bootstrap.get("live_bindings") or {}
    events = load_orchestration_events(repo_root, 20)

    gate = orchestration.get("gate") or {}
    decision = orchestration.get("decision") or {}
    coordination: Dict[str, Any] = {}
    if events:
        latest_raw = _safe_read_json_first_line(repo_root, ORCHESTRATION_EVENTS_PATH)
        if latest_raw and isinstance(latest_raw, dict):
            coordination = latest_raw.get("coordination") or {}

    current_owner = {
        "actor_id": bindings.get("orchestration_current_owner") or (gate.get("owner_driver")),
        "driver_id": orchestration.get("active_driver"),
    }
    next_handoff_raw = coordination.get("next_handoff") or {}
    if not next_handoff_raw and events:
        next_handoff_raw = events[0].get("next_handoff") or {}
    next_handoff = {
        "actor_id": next_handoff_raw.get("actor_id") or bindings.get("orchestration_next_handoff"),
        "mode": next_handoff_raw.get("mode"),
        "command": next_handoff_raw.get("command"),
        "review_surface": next_handoff_raw.get("review_surface"),
    }

    family_dir = _resolve_active_family_dir(repo_root)
    phase_family_json = _safe_read_json(repo_root, f"{family_dir}/phase_family.json") if family_dir else {}
    if not isinstance(phase_family_json, dict):
        phase_family_json = {}
    phases = _list_phase_dirs(repo_root, family_dir) if family_dir else []
    phase_record = _resolve_active_phase_record(
        phases=phases,
        phase_family=phase_family_json,
        bootstrap_bindings=bindings,
        orchestration=_condense_orchestration_state(orchestration),
    )
    phase_dir = (
        str(
            (phase_record or {}).get("phase_dir")
            or bindings.get("phase_dir")
            or phase_family_json.get("active_phase_dir")
            or ""
        ).strip()
        or None
    )
    phase_id = (
        str(
            (phase_record or {}).get("phase_id")
            or phase_family_json.get("active_phase_number")
            or phase_family_json.get("active_phase_id")
            or ""
        ).strip().replace("_", ".")
        or None
    )
    pipeline_state = (
        dict((phase_record or {}).get("pipeline_state") or {})
        if phase_record
        else (_safe_read_json(repo_root, f"{phase_dir}/pipeline_state.json") or {})
        if phase_dir
        else {}
    )
    stage = bindings.get("pipeline_stage") or pipeline_state.get("stage")
    controller_phase = (
        bindings.get("controller_phase")
        or pipeline_state.get("controller_phase")
        or pipeline_state.get("phase")
    )
    cycle_num = bindings.get("cycle") if bindings.get("cycle") is not None else pipeline_state.get("cycle")
    phase_title = (
        str(
            (phase_record or {}).get("title")
            or phase_family_json.get("active_phase_title")
            or ""
        ).strip()
        or None
    )
    phase_updated_at = (
        pipeline_state.get("updated_at")
        or phase_family_json.get("active_phase_changed_at")
        or None
    )
    active_phase: Optional[Dict[str, Any]] = None
    if phase_dir:
        phase_id = phase_id or _phase_id_for_dir(repo_root, phase_dir)
        if phase_title is None:
            match = re.match(r"^\d+\.\d+\s*-\s*(.*)$", Path(phase_dir).name)
            phase_title = match.group(1).strip() if match else Path(phase_dir).name
        active_phase = {
            "phase_id": phase_id,
            "title": phase_title,
            "phase_dir": phase_dir,
            "stage": stage,
            "controller_phase": controller_phase,
            "cycle": cycle_num,
            "blocked": bool(pipeline_state.get("blocked")),
            "gate_reason": pipeline_state.get("gate_reason"),
            "updated_at": phase_updated_at,
            "freshness": compute_freshness(phase_updated_at),
        }

    # Compact active cycle summary — just the fields the operator needs on the home screen.
    active_cycle: Optional[Dict[str, Any]] = None
    if phase_id is not None and cycle_num is not None:
        try:
            full = load_cycle_summary(repo_root, phase_id, int(cycle_num))
        except Exception:
            full = None
        if full:
            active_cycle = {
                "cycle": full.get("cycle"),
                "phase_id": full.get("phase_id"),
                "runtime_state": full.get("runtime_state"),
                "timestamp": full.get("timestamp"),
                "routing_decision": {
                    "decision": (full.get("routing_decision") or {}).get("decision"),
                    "next_phase": (full.get("routing_decision") or {}).get("next_phase"),
                    "confidence": (full.get("routing_decision") or {}).get("confidence"),
                },
                "degraded_count": len(full.get("degraded_groups") or []),
                "groups_total": len(full.get("groups") or []),
                "authority": full.get("authority"),
            }

    # Assemble attention items.
    items: List[Dict[str, Any]] = []

    # Orchestration-level gate
    if gate.get("active"):
        items.append(
            {
                "id": f"gate:{gate.get('gate_reason') or 'active'}",
                "kind": "gate",
                "title": (decision.get("summary") or "Orchestration gate is active.")[:140],
                "detail": gate.get("gate_reason") or "Control plane is waiting for human review.",
                "owner": gate.get("owner_driver"),
                "command": gate.get("command") or decision.get("command"),
                "target": {
                    "kind": "phase",
                    "phase_id": phase_id,
                    "cycle": cycle_num,
                },
                "score": _score_attention_item(
                    blocked=True,
                    gate_reason=gate.get("gate_reason"),
                    age_seconds=compute_freshness(orchestration.get("updated_at")).get("age_seconds"),
                ),
            }
        )

    # Driver-level blocks
    for driver in orchestration.get("drivers") or []:
        if not isinstance(driver, dict):
            continue
        if not driver.get("blocked"):
            continue
        driver_phase_dir = driver.get("phase_dir")
        driver_phase_id = _phase_id_for_dir(repo_root, driver_phase_dir) if driver_phase_dir else None
        items.append(
            {
                "id": f"driver:{driver.get('driver_id')}",
                "kind": "driver_block",
                "title": f"{driver.get('label') or driver.get('driver_id')} is blocked.",
                "detail": driver.get("gate_reason") or "Driver is waiting for operator action.",
                "owner": driver.get("driver_id"),
                "command": (driver.get("next_action") or {}).get("command"),
                "target": {
                    "kind": "phase",
                    "phase_id": driver_phase_id,
                    "phase_dir": driver_phase_dir,
                    "cycle": None,
                },
                "score": _score_attention_item(
                    blocked=True,
                    gate_reason=driver.get("gate_reason"),
                    age_seconds=compute_freshness(driver.get("last_updated")).get("age_seconds"),
                ),
            }
        )

    # Degraded cycle groups
    if active_cycle and active_cycle.get("degraded_count"):
        items.append(
            {
                "id": f"cycle:{active_cycle.get('phase_id')}/{active_cycle.get('cycle')}",
                "kind": "cycle_degraded",
                "title": f"Cycle {active_cycle.get('cycle')} in phase {active_cycle.get('phase_id')} degraded.",
                "detail": f"{active_cycle.get('degraded_count')} of {active_cycle.get('groups_total')} groups failed.",
                "owner": "observe",
                "command": None,
                "target": {
                    "kind": "cycle",
                    "phase_id": active_cycle.get("phase_id"),
                    "cycle": active_cycle.get("cycle"),
                },
                "score": 70,
            }
        )

    # Stale hologram
    system_map = _safe_read_json(repo_root, SYSTEM_MAP_PATH) or {}
    hologram_fresh = compute_freshness(system_map.get("generated_at"))
    if hologram_fresh.get("tone") in ("stale", "expired"):
        items.append(
            {
                "id": "hologram:stale",
                "kind": "drift",
                "title": "System map is stale.",
                "detail": f"Generated {hologram_fresh.get('label')} ago. Rebuild before launching new bridge work.",
                "owner": "kernel",
                "command": "python3 kernel.py --build --build-phases BODY,DERIVED,LAW,UI,SERVER,RAW,SELF",
                "target": {"kind": "drift"},
                "score": 45 if hologram_fresh.get("tone") == "stale" else 90,
            }
        )

    work_ledger_status = work_ledger_runtime.load_runtime_status(repo_root)
    stale_sessions = list(work_ledger_status.get("stale_sessions") or [])
    work_ledger_cohort = work_ledger_status.get("cohort_overview") or {}
    work_ledger_contention = work_ledger_cohort.get("contention") or {}
    handoff_candidates = agent_seed_handoff_lib.extract_agent_seed_handoffs(
        repo_root,
        family_id=str(active_phase.get("family_id") or "09"),
        limit=20,
        include_imported=False,
    )
    if stale_sessions:
        counts = work_ledger_status.get("counts") or {}
        items.append(
            {
                "id": "work_ledger:stale",
                "kind": "work_ledger",
                "title": "Work-ledger append missing.",
                "detail": (
                    f"{counts.get('stale_sessions') or len(stale_sessions)} stale session(s) "
                    "touched work and ended without a ledger append."
                ),
                "owner": "work_ledger",
                "command": "./repo-python tools/meta/factory/work_ledger.py project --all",
                "target": {"kind": "ledger"},
                "score": 85,
            }
        )
    if int(handoff_candidates.get("unimported_count") or 0) > 0:
        items.append(
            {
                "id": "work_ledger:agent_seed_handoffs",
                "kind": "work_ledger",
                "title": "Agent-seed handoffs need promotion.",
                "detail": (
                    f"{handoff_candidates.get('unimported_count')} actionable handoff candidate(s) "
                    "are still in agent_seed instead of the work ledger."
                ),
                "owner": "work_ledger",
                "command": "./repo-python tools/meta/factory/work_ledger.py agent-seed-handoffs --family-id 09 --since-date 2026-04-24",
                "target": {"kind": "ledger"},
                "score": 88,
            }
        )
    if work_ledger_contention.get("risk_level") in {"watch", "contention"}:
        items.append(
            {
                "id": "work_ledger:coordination",
                "kind": "work_ledger",
                "title": "Multi-agent coordination pressure is visible.",
                "detail": ", ".join(work_ledger_contention.get("signals") or []) or "Review active claims and sessions.",
                "owner": "work_ledger",
                "command": "./repo-python tools/meta/factory/work_ledger.py session-status --overview",
                "target": {"kind": "ledger"},
                "score": 82,
            }
        )

    # Sort highest-score first and cap.
    items.sort(key=lambda i: i.get("score", 0), reverse=True)
    items = items[:12]

    # Recent changes = orchestration events compact view.
    recent_changes = [
        {
            "event_id": e.get("event_id"),
            "recorded_at": e.get("recorded_at"),
            "summary": e.get("summary"),
            "gate_reason": e.get("gate_reason"),
            "active_driver": e.get("active_driver"),
            "immediate_mode": e.get("immediate_mode"),
        }
        for e in events[:10]
    ]

    # Next moves = dedupe command suggestions from orchestration + drivers + items.
    next_moves: List[Dict[str, Any]] = []
    seen_cmds = set()

    def _push_move(summary: Optional[str], command: Optional[str], owner: Optional[str]):
        if not summary and not command:
            return
        key = (command or "") + "|" + (summary or "")
        if key in seen_cmds:
            return
        seen_cmds.add(key)
        next_moves.append({"summary": summary, "command": command, "owner": owner})

    _push_move(decision.get("summary"), decision.get("command"), orchestration.get("active_driver"))
    for driver in orchestration.get("drivers") or []:
        na = _driver_next_action(driver) if isinstance(driver, dict) else None
        if na:
            _push_move(na["summary"], na["command"], (driver or {}).get("driver_id"))
    for item in items:
        _push_move(item.get("detail"), item.get("command"), item.get("owner"))
    if next_handoff and (next_handoff.get("command") or next_handoff.get("mode")):
        _push_move(
            f"Next handoff: {next_handoff.get('actor_id') or next_handoff.get('mode')}",
            next_handoff.get("command"),
            next_handoff.get("actor_id"),
        )
    next_moves = next_moves[:8]

    # Bridge health compact
    bridge_health = {
        "alive": None,
        "providers": [],
        "stale_reason": None,
    }
    try:
        from system.core.bridge import bridge_diagnostics as _bridge_diag  # type: ignore

        diag = _bridge_diag(repo_root)
        bridge_health = {
            "alive": bool(diag.get("browser_running")) if isinstance(diag, dict) else False,
            "providers": list((diag.get("providers") or {}).keys()) if isinstance(diag, dict) else [],
            "cdp_reachable": bool(diag.get("cdp_reachable")) if isinstance(diag, dict) else False,
            "error": diag.get("error") if isinstance(diag, dict) else None,
        }
    except Exception:
        bridge_health = {
            "alive": None,
            "providers": [],
            "stale_reason": "bridge diagnostics unavailable",
        }

    reactions = load_reactions_snapshot(repo_root)

    # Banner: the one most-important line.
    banner: Dict[str, Any]
    if items:
        top = items[0]
        tone = "block" if top.get("kind") in ("gate", "driver_block") else "warn"
        banner = {
            "tone": tone,
            "title": top.get("title"),
            "summary": top.get("detail"),
            "gate_reason": top.get("owner"),
            "command": top.get("command"),
            "target": top.get("target"),
        }
    else:
        banner = {
            "tone": "ok",
            "title": "System is moving without operator block.",
            "summary": (decision.get("summary") or "No gates active."),
            "gate_reason": None,
            "command": None,
            "target": None,
        }

    return {
        "schema": "attention_snapshot_v1",
        "generated_at": generated,
        "banner": banner,
        "current_driver": current_owner,
        "next_handoff": next_handoff,
        "active_phase": active_phase,
        "active_cycle": active_cycle,
        "attention_items": items,
        "recent_changes": recent_changes,
        "next_moves": next_moves,
        "bridge_health": bridge_health,
        "drift": {
            "hologram": {
                "generated_at": system_map.get("generated_at"),
                "freshness": hologram_fresh,
            },
            "system_view_file_count": bindings.get("system_view_file_count"),
            "doctrine_runtime_mtime": bindings.get("doctrine_runtime_mtime_iso"),
        },
        "work_ledger": {
            "generated_at": work_ledger_status.get("generated_at"),
            "counts": work_ledger_status.get("counts") or {},
            "triggers": work_ledger_status.get("triggers") or {},
            "cohort_overview": work_ledger_cohort,
            "stale_sessions": stale_sessions[:10],
            "handoff_candidates": {
                "candidate_count": handoff_candidates.get("candidate_count"),
                "unimported_count": handoff_candidates.get("unimported_count"),
                "candidates": list(handoff_candidates.get("candidates") or [])[:8],
            },
        },
        "reactions": reactions,
    }


def load_attention_snapshot(repo_root: Path) -> Dict[str, Any]:
    return _cached_mapping(
        cache=_ATTENTION_SNAPSHOT_CACHE,
        lock=_ATTENTION_SNAPSHOT_CACHE_LOCK,
        repo_root=repo_root,
        loader=lambda: _build_attention_snapshot(repo_root),
    )


def _build_reactions_snapshot(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Return the compiled reactions-engine snapshot used by the Station
      lens and the orchestration cockpit.
    - Mechanism: Delegate to the durable reactions runtime helper so the server
      stays read-only with respect to orchestration_state.json.
    - Guarantee: Returns a `reactions_snapshot_v1` payload or an exception-safe
      degraded payload on helper failure.
    """
    # signal_mode="cached" evaluates predicates against each reaction's
    # persisted last_signal from reactions_state.json instead of re-running
    # every signal producer live. The reactions_engine.build_reactions_snapshot
    # docstring explicitly names this mode as "cheap visibility for read-only
    # entry surfaces, not scheduler authority" — exactly the cockpit lens +
    # /attention consumer shape. Without this, cold builds re-ran every
    # producer and the wall climbed to ~116 s, which propagated through
    # _build_attention_snapshot and turned first /api/world-model/attention
    # requests after restart into 47–60 s blockers. Per
    # cap_quick_load_attention_snapshot_cold_build_unbou_5bd4847cd501.
    try:
        return reactions_runtime.build_reactions_snapshot(repo_root, signal_mode="cached")
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("load_reactions_snapshot failed: %s", exc)
        return {
            "schema": "reactions_snapshot_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "desired_armed": False,
            "engine_armed": False,
            "engine_status": "error",
            "pid": None,
            "cursor_event_id": None,
            "last_tick_at": None,
            "last_error": f"{type(exc).__name__}: {exc}",
            "awaiting_barriers": [],
            "active_reaction_id": None,
            "last_fired_at": None,
            "reactions": [],
        }


def load_reactions_snapshot(repo_root: Path) -> Dict[str, Any]:
    return _cached_mapping(
        cache=_REACTIONS_SNAPSHOT_CACHE,
        lock=_REACTIONS_SNAPSHOT_CACHE_LOCK,
        repo_root=repo_root,
        loader=lambda: _build_reactions_snapshot(repo_root),
    )


def _build_reconciliation_snapshot(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Project the latest pri_119 metabolism_reconciliation_v1 event into
      a frontend-consumable envelope so the cockpit can surface daemon health
      without re-running the reconciliation pass (which would create a silent
      observation surface with no audit trail).
    - Mechanism: Open a metabolism store conn, query the events table for the most
      recent event with source='metabolism_reconciliation' and
      kind='metabolism_reconciliation_v1', derive age_seconds from the event's
      payload.summary.generated_at, mark stale when age_seconds >=
      _RECONCILIATION_STALE_THRESHOLD_SECONDS.
    - Guarantee: Always returns a metabolism_reconciliation_projection_v1 envelope
      with a stable shape; latest_event is null when has_event=False; defensive on
      every store/parse error path so the FastAPI surface never raises during a
      poll.
    """
    envelope = {
        "schema": "metabolism_reconciliation_projection_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stale_threshold_seconds": _RECONCILIATION_STALE_THRESHOLD_SECONDS,
        "has_event": False,
        "latest_event": None,
        "age_seconds": None,
        "stale": False,
        "candidate_snapshot": _build_metabolism_candidate_snapshot(repo_root),
    }
    try:
        conn = _metabolism_store.connect(repo_root)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("load_reconciliation_snapshot connect failed: %s", exc)
        envelope["error"] = f"{type(exc).__name__}: {exc}"
        return envelope
    try:
        row = conn.execute(
            """
            SELECT * FROM events
            WHERE source = ? AND kind = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            ("metabolism_reconciliation", "metabolism_reconciliation_v1"),
        ).fetchone()
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("load_reconciliation_snapshot query failed: %s", exc)
        envelope["error"] = f"{type(exc).__name__}: {exc}"
        try:
            conn.close()
        except Exception:
            pass
        return envelope
    finally:
        try:
            conn.close()
        except Exception:
            pass
    if row is None:
        return envelope
    parsed = _metabolism_store.parse_event_row(row)
    payload = parsed.get("payload") or {}
    envelope["has_event"] = True
    envelope["latest_event"] = {
        "event_id": parsed.get("id"),
        "source": parsed.get("source"),
        "kind": parsed.get("kind"),
        "stable_digest": parsed.get("stable_digest"),
        "created_at": parsed.get("created_at"),
        "processed_at": parsed.get("processed_at"),
        "payload": payload,
    }
    summary = payload.get("summary") if isinstance(payload, dict) else None
    generated_at = None
    if isinstance(summary, dict):
        generated_at = summary.get("generated_at") or payload.get("generated_at")
    if not generated_at:
        generated_at = parsed.get("created_at")
    age_seconds = None
    if generated_at:
        try:
            ts = datetime.fromisoformat(str(generated_at))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_seconds = max(
                int((datetime.now(timezone.utc) - ts).total_seconds()), 0
            )
        except Exception:  # pragma: no cover - defensive
            age_seconds = None
    envelope["age_seconds"] = age_seconds
    envelope["stale"] = (
        age_seconds is not None
        and age_seconds >= _RECONCILIATION_STALE_THRESHOLD_SECONDS
    )
    return envelope


def _build_metabolism_candidate_snapshot(repo_root: Path) -> Dict[str, Any] | None:
    try:
        conn = _metabolism_store.connect(repo_root)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("metabolism candidate snapshot connect failed: %s", exc)
        return {
            "schema_version": "metabolism_selector_snapshot_v0",
            "kind": "metabolism_selector_snapshot",
            "error": f"{type(exc).__name__}: {exc}",
        }
    try:
        selector_tick = _metabolism_store.get_setting(conn, "selector_tick_latest", {}) or {}
        snapshot = _metabolism_scheduler.build_selector_snapshot(
            conn,
            repo_root=repo_root,
            limit=20,
            candidate_feed=_provider_metabolism_signal.derive_candidate_job_feed(
                repo_root,
                source="all",
                limit=20,
            ),
        )
        if isinstance(selector_tick, dict):
            snapshot["selector_tick"] = selector_tick
            snapshot["last_selector_tick_at"] = selector_tick.get("generated_at")
            snapshot["selected_candidate_id"] = selector_tick.get("selected_candidate_id")
            snapshot["selected_action_status"] = selector_tick.get("selected_action_status")
            snapshot["receipt_summary"] = selector_tick.get("receipt_summary") or {}
            snapshot["skip_receipt_count"] = int(
                (snapshot["receipt_summary"].get("skip_receipts_written") or 0)
            ) + int((snapshot["receipt_summary"].get("skip_receipts_deduped") or 0))
        return snapshot
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("metabolism candidate snapshot failed: %s", exc)
        return {
            "schema_version": "metabolism_selector_snapshot_v0",
            "kind": "metabolism_selector_snapshot",
            "error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass


def load_reconciliation_snapshot(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Cache the projection envelope behind the same stale-while-revalidate
      contract used by reactions/wake-barriers, so a polling cockpit never pays the
      cold rebuild cost twice within a 10s window.
    - Mechanism: Wrap _build_reconciliation_snapshot in _cached_mapping with the
      shared TTL.
    - Guarantee: Returns the same envelope shape on every call.
    """
    return _cached_mapping(
        cache=_RECONCILIATION_SNAPSHOT_CACHE,
        lock=_RECONCILIATION_SNAPSHOT_CACHE_LOCK,
        repo_root=repo_root,
        loader=lambda: _build_reconciliation_snapshot(repo_root),
    )


def load_wake_barriers(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Publish just the current wake barriers for the control-plane UI.
    - Mechanism: Delegate to the reactions runtime helper.
    - Guarantee: Returns a `wake_barriers_v1` payload on success.
    """
    try:
        return reactions_runtime.build_wake_barriers_snapshot(repo_root)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("load_wake_barriers failed: %s", exc)
        return {
            "schema": "wake_barriers_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine_armed": False,
            "engine_status": "error",
            "items": [],
            "error": f"{type(exc).__name__}: {exc}",
        }


def set_reaction_armed_state(
    repo_root: Path,
    *,
    target: str,
    armed: bool,
    reaction_id: str | None = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Update runtime armed state for the whole engine or one reaction
      without mutating tracked reactions.yaml.
    - Mechanism: Delegate to the durable reactions runtime helper and return the
      refreshed compiled snapshot.
    - Guarantee: Returns the updated `reactions_snapshot_v1` payload.
    """
    target_token = str(target or "").strip().lower()
    if target_token == "engine":
        reactions_runtime.set_engine_armed_state(repo_root, bool(armed))
        return load_reactions_snapshot(repo_root)
    if target_token == "reaction":
        token = str(reaction_id or "").strip()
        if not token:
            raise ValueError("reaction_id is required when target='reaction'")
        reactions_runtime.set_reaction_override_state(repo_root, token, bool(armed))
        return load_reactions_snapshot(repo_root)
    raise ValueError("target must be 'engine' or 'reaction'")


def _work_row_title(row: Mapping[str, Any]) -> str:
    for key in ("title", "statement", "body", "claim", "summary"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    td_id = str(row.get("td_id") or row.get("id") or "").strip()
    return td_id or "untitled work item"


def _work_row_blocker_summary(row: Mapping[str, Any]) -> Optional[str]:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {}
    for key in ("blocker_summary", "blocking_on", "blocked_by", "gate_reason", "stale_reason"):
        value = metadata.get(key) or row.get(key)
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(item) for item in value if str(item or "").strip())
        excerpt = _excerpt(value, limit=150)
        if excerpt:
            return excerpt
    if str(row.get("status") or "").lower() in {"blocked", "stale", "waiting"}:
        return _excerpt(row.get("body") or row.get("detail"), limit=150)
    return None


def _project_work_ledger_row(row: Mapping[str, Any], *, now: Optional[datetime] = None) -> Dict[str, Any]:
    last_event_at = row.get("last_event_at") or row.get("updated_at") or row.get("opened_at")
    td_id = row.get("td_id") or row.get("id")
    return {
        "td_id": td_id,
        "title": _work_row_title(row),
        "body_excerpt": _excerpt(row.get("body") or row.get("detail") or row.get("statement"), limit=180),
        "status": row.get("status") or row.get("state"),
        "actor": row.get("last_actor") or row.get("actor"),
        "phase_id": row.get("phase_id"),
        "family_id": row.get("family_id"),
        "opened_at": row.get("opened_at"),
        "last_event_at": last_event_at,
        "last_event_kind": row.get("last_event_kind") or row.get("event_kind"),
        "age_seconds": _age_seconds(last_event_at, now=now),
        "blocker_summary": _work_row_blocker_summary(row),
        "surface_route": _safe_internal_route(
            row.get("surface_route"),
            _intelligence_work_route(td_id),
        ),
    }


def _flatten_open_work_rows(open_by_actor: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows_by_id: Dict[str, Dict[str, Any]] = {}
    anon_rows: List[Dict[str, Any]] = []
    for actor, rows in open_by_actor.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            materialized = dict(row)
            materialized.setdefault("last_actor", actor)
            key = str(materialized.get("td_id") or materialized.get("id") or "").strip()
            if key:
                rows_by_id[key] = materialized
            else:
                anon_rows.append(materialized)
    return list(rows_by_id.values()) + anon_rows


def _top_recent_work_rows(rows: Sequence[Mapping[str, Any]], *, limit: int = 5) -> List[Mapping[str, Any]]:
    return sorted(
        rows,
        key=lambda row: _parse_iso_datetime(row.get("last_event_at") or row.get("updated_at") or row.get("opened_at"))
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )[:limit]


def _top_in_progress_work_rows(rows: Sequence[Mapping[str, Any]], *, limit: int = 5) -> List[Mapping[str, Any]]:
    active_statuses = {"in_progress", "executing", "claimed", "active", "working"}
    active_event_kinds = {"claim", "progress_note", "todo_progress", "execution_receipt"}
    active_rows = [
        row
        for row in rows
        if str(row.get("status") or row.get("state") or "").lower() in active_statuses
        or str(row.get("last_event_kind") or "").lower() in active_event_kinds
    ]
    return _top_recent_work_rows(active_rows, limit=limit)


def _sort_awareness_cards(cards: Iterable[Any]) -> List[Dict[str, Any]]:
    freshness_rank = {
        "live": 0,
        "idle": 1,
        "unknown": 2,
        "stale": 3,
        "expired": 4,
        "orphaned": 5,
        "ended": 6,
    }

    def sort_key(card: Dict[str, Any]) -> tuple[Any, ...]:
        source = str(card.get("source") or "").strip()
        freshness = str(card.get("freshness_state") or "").strip()
        has_public_line = bool(str(card.get("current_pass_line") or "").strip())
        updated = _parse_iso_datetime(card.get("updated_at"))
        updated_rank = -updated.timestamp() if updated is not None else 0
        return (
            0 if has_public_line and source != "projected_unknown" else 1,
            freshness_rank.get(freshness, 7),
            1 if card.get("orphaned_active") else 0,
            updated_rank,
            str(card.get("session_id") or ""),
        )

    typed_cards = [card for card in cards if isinstance(card, dict)]
    return sorted(typed_cards, key=sort_key)


def load_work_ledger_overview(
    repo_root: Path,
    *,
    phase_id: str | None = None,
    family_id: str | None = None,
) -> Dict[str, Any]:
    context = work_ledger_lib.resolve_phase_context(
        repo_root,
        phase_id=phase_id,
        family_id=family_id,
    )
    projection = work_ledger_lib.load_projection(
        repo_root,
        phase_id=context["phase_id"],
        family_id=context["family_id"],
    )
    runtime_status = work_ledger_runtime.load_runtime_status(repo_root)
    cohort_overview = runtime_status.get("cohort_overview") or {}
    handoff_candidates = agent_seed_handoff_lib.extract_agent_seed_handoffs(
        repo_root,
        family_id=context["family_id"],
        limit=30,
        include_imported=False,
    )
    raw_path = repo_root / "codex" / "ledger" / context["phase_id"] / "work_ledger.jsonl"
    index_path = repo_root / "codex" / "ledger" / context["phase_id"] / "work_ledger_index.json"
    now = datetime.now(timezone.utc)
    open_by_actor = projection.get("open_by_actor") or {}
    stale_open = list(projection.get("stale_open") or [])[:20]
    open_rows = _flatten_open_work_rows(open_by_actor if isinstance(open_by_actor, Mapping) else {})
    top_stale = [
        _project_work_ledger_row(row, now=now)
        for row in _top_recent_work_rows([row for row in stale_open if isinstance(row, Mapping)], limit=5)
    ]
    top_in_progress = [
        _project_work_ledger_row(row, now=now)
        for row in _top_in_progress_work_rows(open_rows, limit=5)
    ]
    top_recent_open = [
        _project_work_ledger_row(row, now=now)
        for row in _top_recent_work_rows(open_rows, limit=5)
    ]
    counts = dict(projection.get("counts") or {})
    counts.setdefault("open", len(open_rows))
    counts.setdefault("stale", len(projection.get("stale_open") or []))
    return {
        "schema": "work_ledger_overview_v1",
        "generated_at": now.isoformat(),
        "phase_id": context["phase_id"],
        "family_id": context["family_id"],
        "raw_path": raw_path.relative_to(repo_root).as_posix(),
        "index_path": index_path.relative_to(repo_root).as_posix(),
        "freshness": compute_freshness(_file_mtime(repo_root, index_path.relative_to(repo_root).as_posix())),
        "counts": counts,
        "open_by_actor": open_by_actor,
        "open_by_family": projection.get("open_by_family") or {},
        "recently_closed": list(projection.get("recently_closed") or [])[:20],
        "supersession_chains": list(projection.get("supersession_chains") or [])[:20],
        "cross_agent_handoffs": list(projection.get("cross_agent_handoffs") or [])[:20],
        "stale_open": stale_open,
        "stale_sessions": list(runtime_status.get("stale_sessions") or [])[:20],
        "handoff_candidates": handoff_candidates,
        "coordination": {
            "risk_level": (cohort_overview.get("contention") or {}).get("risk_level"),
            "signals": list((cohort_overview.get("contention") or {}).get("signals") or []),
            "awareness_cards": _sort_awareness_cards(cohort_overview.get("awareness_cards") or [])[:20],
            "heartbeat_participation": dict(cohort_overview.get("heartbeat_participation") or {}),
            "active_claims": list(cohort_overview.get("active_claims") or [])[:20],
            "effective_active_sessions": list(cohort_overview.get("effective_active_sessions") or [])[:20],
            "orphaned_active_sessions": list(cohort_overview.get("orphaned_active_sessions") or [])[:20],
            "recommended_actions": list(cohort_overview.get("recommended_actions") or [])[:10],
        },
        "runtime_status": {
            "generated_at": runtime_status.get("generated_at"),
            "counts": runtime_status.get("counts") or {},
            "triggers": runtime_status.get("triggers") or {},
            "cohort_overview": cohort_overview,
        },
        "top_stale": top_stale,
        "top_in_progress": top_in_progress,
        "top_recent_open": top_recent_open,
    }


_TASK_LEDGER_VIEW_ROLES: dict[str, str] = {
    "active_wip": "active claimed work",
    "mission_operating_picture": "mission operating picture graph read model",
    "cap_census": "cap universe census read model",
    "cap_cartography": "cap universe cartography read model",
    "workitem_cartography": "WorkItem universe cartography read model (atlas marks + bounded graph)",
    "execution_menu": "committed execution queue",
    "schedulable_by_rank": "dependency-satisfied ready work",
    "promotion_candidates": "review and promotion queue",
    "capture_triage": "capture shaping state",
    "capture_inbox": "fresh captures",
    "missing_contracts_ranked": "contract depth gaps",
    "missing_satisfaction_contract": "satisfaction contract gaps",
    "missing_integration_contract": "integration contract gaps",
    "needs_signoff": "closeout/signoff queue",
    "propagation_needed": "post-signoff propagation queue",
    "operator_needed": "operator decision queue",
    "ready_by_rank": "ready work",
    "blocked": "blocked work",
    "dependency_blocked": "dependency-blocked work",
    "provider_assignable": "background/provider candidates",
    "bridge_assignable": "bridge-assignable candidates",
    "stale_review": "stale rows",
    "legacy_snapshot_unmodeled": "legacy projection adoption gaps",
    "work_ledger_unlinked": "execution linkage gaps",
    "prompt_trace_unlinked": "prompt provenance linkage gaps",
    "recent_events": "recent mutation tape",
}

_TASK_LEDGER_LEGIBILITY_CLUSTERS: tuple[dict[str, Any], ...] = (
    {
        "cluster_id": "now",
        "label": "Now pressure",
        "description": "Current execution, ready, and dependency-satisfied rows.",
        "source_views": ["active_wip", "execution_menu", "schedulable_by_rank", "ready_by_rank"],
        "action_label": "claim_or_continue",
    },
    {
        "cluster_id": "closeout",
        "label": "Closeout pressure",
        "description": "Rows that need signoff or propagation before they stop occupying attention.",
        "source_views": ["needs_signoff", "propagation_needed", "work_ledger_unlinked"],
        "action_label": "signoff_or_record_propagation",
    },
    {
        "cluster_id": "blocked",
        "label": "Blocked pressure",
        "description": "Operator, dependency, and explicit blocked queues.",
        "source_views": ["blocked", "dependency_blocked", "operator_needed"],
        "action_label": "clear_blocker_or_mark_waiting",
    },
    {
        "cluster_id": "quality_gaps",
        "label": "Quality gaps",
        "description": "Contract and legacy-adoption gaps that make WorkItems hard to consume.",
        "source_views": [
            "missing_contracts_ranked",
            "missing_satisfaction_contract",
            "missing_integration_contract",
            "legacy_snapshot_unmodeled",
            "prompt_trace_unlinked",
        ],
        "action_label": "shape_contract_or_link_provenance",
    },
    {
        "cluster_id": "intake",
        "label": "Intake pressure",
        "description": "Captured and shaped rows that need triage before commitment.",
        "source_views": ["capture_inbox", "capture_triage", "promotion_candidates"],
        "action_label": "triage_promote_or_retire",
    },
    {
        "cluster_id": "assignable",
        "label": "Assignable work",
        "description": "Rows suitable for bridge or provider execution lanes.",
        "source_views": ["bridge_assignable", "provider_assignable"],
        "action_label": "assign_or_defer",
    },
    {
        "cluster_id": "stale_or_replay",
        "label": "Stale and replay",
        "description": "Aging rows and recent event tape used for consolidation.",
        "source_views": ["stale_review", "recent_events"],
        "action_label": "replay_refresh_or_retire",
    },
)

_TASK_LEDGER_QUEUE_FALLBACK_REL = (
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and "
    "Fresh Execution Spine/09.51 - Phase 09.51 - Frontend Demo Readiness and "
    "Station Proof Path/frontend_demo_readiness_queue.json"
)
_TASK_LEDGER_QUEUE_REL = _TASK_LEDGER_QUEUE_FALLBACK_REL
_TASK_LEDGER_QUEUE_FILENAME = "frontend_demo_readiness_queue.json"
_PUBLIC_PROJECTION_OUTPUT_ROOT_ENV = "AIW_PUBLIC_PROJECTION_OUTPUT_ROOT"
_PUBLIC_PROJECTION_DEFAULT_OUTPUT_ROOT = Path.home() / ".cache" / "ai_workflow" / "public_projection"
_PUBLIC_GATE_REPORT_NAME = "portability_gate_report.json"
_PUBLIC_GATE_REPORT_PATH = Path("/tmp/ai-workflow-public/portability_gate_report.json")
_FRONTEND_WORKITEM_KEYWORDS = (
    "frontend",
    "front-end",
    "station",
    "/station",
    "tsx",
    "component",
    "render",
    "vitest",
    "demo",
    "diagnostic",
)


def _active_task_ledger_queue_ref(repo_root: Path) -> dict[str, Any]:
    family_dir = _resolve_active_family_dir(repo_root)
    family_payload = (
        _safe_read_json(repo_root, f"{family_dir}/phase_family.json")
        if family_dir
        else None
    ) or {}
    active_phase_dir = str(family_payload.get("active_phase_dir") or "").strip()
    active_phase_id = str(family_payload.get("active_phase_id") or "").strip()
    active_rel = (
        f"{active_phase_dir.rstrip('/')}/{_TASK_LEDGER_QUEUE_FILENAME}"
        if active_phase_dir
        else ""
    )
    active_payload = _safe_read_json(repo_root, active_rel) if active_rel else None
    if active_payload is not None:
        return {
            "path": active_rel,
            "payload": active_payload,
            "phase_id": active_phase_id or active_payload.get("phase_id"),
            "source": "active_phase",
            "fallback_used": False,
        }
    fallback_payload = _safe_read_json(repo_root, _TASK_LEDGER_QUEUE_FALLBACK_REL) or {}
    return {
        "path": _TASK_LEDGER_QUEUE_FALLBACK_REL,
        "payload": fallback_payload,
        "phase_id": fallback_payload.get("phase_id") or active_phase_id,
        "source": "fallback_legacy_phase",
        "fallback_used": bool(active_rel),
        "attempted_active_path": active_rel or None,
    }


def _task_ledger_view_items(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    raw_items = payload.get("items") or payload.get("rows") or payload.get("work_items") or []
    if isinstance(raw_items, Mapping):
        raw_items = list(raw_items.values())
    if not isinstance(raw_items, list):
        return []
    return [dict(item) for item in raw_items if isinstance(item, Mapping)]


def _cap_cartography_rows(payload: Mapping[str, Any] | None, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    rows = payload.get(key) or []
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _cap_cartography_consumption_contract(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    source_view = "state/task_ledger/views/cap_cartography.json"
    if not isinstance(payload, Mapping):
        return {
            "schema_version": "cap_cartography_consumption_contract_v0",
            "source_view": source_view,
            "available": False,
            "frontend_posture": {
                "mode": "observe_only",
                "cap_creation_supported": False,
                "mutation_supported": False,
                "source_route_supported": False,
            },
            "readiness": {
                "strict_json": False,
                "overview_graph_ready": False,
                "overview_complete": False,
                "node_count": 0,
                "edge_count": 0,
                "cluster_count": 0,
                "lineage_index_count": 0,
                "orphan_edge_count": 0,
                "missing_lineage_count": 0,
                "edge_limit_hit": False,
                "support_node_limit_hit": False,
                "overflow_index_available": False,
                "drilldown_index_available": False,
                "unclassified_index_available": False,
                "unclassified_count": 0,
                "omitted_edge_count": 0,
                "warning_count": 1,
            },
            "consumer_notes": ["cap_cartography projection is unavailable; rebuild Task Ledger projections before rendering."],
        }

    clusters = _cap_cartography_rows(payload, "clusters")
    nodes = _cap_cartography_rows(payload, "nodes")
    edges = _cap_cartography_rows(payload, "edges")
    lineage = _cap_cartography_rows(payload, "lineage_index")
    warnings = _cap_cartography_rows(payload, "warnings")
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    legend = payload.get("legend") if isinstance(payload.get("legend"), Mapping) else {}
    levels = _cap_cartography_rows(payload, "levels")
    overflow_policy = payload.get("overflow_policy") if isinstance(payload.get("overflow_policy"), Mapping) else {}
    overflow_index = payload.get("overflow_index") if isinstance(payload.get("overflow_index"), Mapping) else {}
    drilldown_index = _cap_cartography_rows(payload, "drilldown_index")
    unclassified_index = (
        payload.get("unclassified_index")
        if isinstance(payload.get("unclassified_index"), Mapping)
        else {}
    )

    cluster_ids = {str(cluster.get("id") or "") for cluster in clusters if cluster.get("id")}
    node_ids = {str(node.get("id") or "") for node in nodes if node.get("id")}
    resolvable_ids = cluster_ids | node_ids
    orphan_edge_count = sum(
        1
        for edge in edges
        if str(edge.get("source") or "") not in resolvable_ids
        or str(edge.get("target") or "") not in resolvable_ids
    )
    edge_missing_contract_count = sum(
        1
        for edge in edges
        if not edge.get("edge_kind") or not edge.get("confidence") or not edge.get("source_ref")
    )
    cap_nodes = [node for node in nodes if node.get("node_kind") == "cap"]
    lineage_ids = {str(row.get("display_id") or "") for row in lineage if row.get("display_id")}
    missing_lineage_count = sum(1 for node in cap_nodes if str(node.get("id") or "") not in lineage_ids)
    missing_task_card_count = sum(
        1
        for node in cap_nodes
        if not (
            isinstance(node.get("source_route_metadata"), Mapping)
            and node["source_route_metadata"].get("task_ledger_card")
        )
    )
    node_missing_basis_count = sum(
        1
        for node in nodes
        if not node.get("source_refs") and not node.get("cluster_ids") and not node.get("proof_refs")
    )
    cluster_missing_contract_count = sum(
        1
        for cluster in clusters
        if not all(
            key in cluster
            for key in ("cluster_kind", "member_count", "representative_ids", "confidence", "source_evidence")
        )
    )
    edge_confidence_counts = Counter(str(edge.get("confidence") or "unknown") for edge in edges)
    edge_kind_counts = Counter(str(edge.get("edge_kind") or "unknown") for edge in edges)
    warning_names = {str(warning.get("warning") or "") for warning in warnings if warning.get("warning")}
    edge_limit_hit = "edge_limit_hit" in warning_names or bool(overflow_index.get("edge_limit_hit"))
    support_node_limit_hit = "support_node_limit_hit" in warning_names or bool(
        overflow_index.get("support_node_limit_hit")
    )
    omitted_edge_count = int(overflow_index.get("omitted_edge_count") or summary.get("omitted_edge_count") or 0)
    unclassified_count = int(unclassified_index.get("count") or summary.get("unclassified_count") or 0)
    bounded_omission_exists = any(
        [
            edge_limit_hit,
            support_node_limit_hit,
            bool(overflow_index.get("visible_cap_limit_hit")),
            bool(overflow_index.get("cluster_representative_limit_hit")),
            omitted_edge_count > 0,
        ]
    )
    overview_graph_ready = (
        orphan_edge_count == 0
        and missing_lineage_count == 0
        and edge_missing_contract_count == 0
        and cluster_missing_contract_count == 0
    )
    overview_complete = bool(overview_graph_ready and not bounded_omission_exists)

    source_refs = list(payload.get("source_refs") or [])
    authority = payload.get("authority") if isinstance(payload.get("authority"), Mapping) else {}
    source_refs.extend(str(ref) for ref in authority.get("projection_inputs") or [] if ref)
    if authority.get("source"):
        source_refs.append(str(authority["source"]))
    source_refs = list(dict.fromkeys(source_refs))

    consumer_notes: list[str] = []
    if orphan_edge_count:
        consumer_notes.append("Some edges reference ids outside nodes/clusters; renderer must treat the packet as not graph-ready.")
    if missing_lineage_count:
        consumer_notes.append("Some visible cap nodes lack lineage drilldown entries.")
    if edge_missing_contract_count:
        consumer_notes.append("Some edges lack edge_kind/confidence/source_ref.")
    if bounded_omission_exists:
        consumer_notes.append("Overview is graph-ready but bounded; use overflow_index and drilldown_index for expansion.")
    if unclassified_count:
        consumer_notes.append("Some caps lack deterministic semantic_role; use unclassified_index before assigning meaning.")
    if edge_limit_hit and not overflow_index:
        consumer_notes.append("edge_limit_hit is true but no overflow_index is present; rebuild Task Ledger projections.")

    return {
        "schema_version": "cap_cartography_consumption_contract_v0",
        "source_view": source_view,
        "generated_at": payload.get("generated_at"),
        "available": payload.get("schema_version") == "cap_cartography_v0",
        "source_refs": source_refs,
        "frontend_posture": {
            "mode": "observe_only",
            "cap_creation_supported": False,
            "mutation_supported": False,
            "source_route_supported": True,
            "frontend_actionable_cap_mutation_supported": False,
        },
        "readiness": {
            "strict_json": payload.get("schema_version") == "cap_cartography_v0",
            "overview_graph_ready": overview_graph_ready,
            "overview_complete": overview_complete,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "cluster_count": len(clusters),
            "lineage_index_count": len(lineage),
            "orphan_edge_count": orphan_edge_count,
            "missing_lineage_count": missing_lineage_count,
            "edge_missing_contract_count": edge_missing_contract_count,
            "cluster_missing_contract_count": cluster_missing_contract_count,
            "node_missing_basis_count": node_missing_basis_count,
            "missing_task_ledger_card_count": missing_task_card_count,
            "edge_limit_hit": edge_limit_hit,
            "support_node_limit_hit": support_node_limit_hit,
            "overflow_index_available": bool(overflow_index),
            "drilldown_index_available": bool(drilldown_index),
            "unclassified_index_available": bool(unclassified_index),
            "unclassified_count": unclassified_count,
            "omitted_edge_count": omitted_edge_count,
            "overview_edge_limit": overflow_policy.get("overview_edge_limit"),
            "warning_count": len(warnings),
            "summary_warning_count": summary.get("warning_count"),
            "source_evidenced_edge_count": edge_confidence_counts.get("source_evidenced", 0),
            "projection_inferred_edge_count": edge_confidence_counts.get("projection_inferred", 0),
        },
        "visual_semantics": {
            "color_basis_options": list(legend.get("color_basis_options") or []),
            "size_basis_options": list(legend.get("size_basis_options") or []),
            "supported_levels": [str(level.get("id") or "") for level in levels if level.get("id")],
            "edge_kinds": dict(edge_kind_counts.most_common()),
            "confidence_values": list(legend.get("confidence_values") or []),
            "frontend_posture": legend.get("frontend_posture"),
        },
        "drilldown_contract": {
            "every_visible_cap_has_task_ledger_card": missing_task_card_count == 0,
            "every_edge_has_source_ref": edge_missing_contract_count == 0,
            "every_edge_endpoint_resolves": orphan_edge_count == 0,
            "every_node_has_source_or_cluster_basis": node_missing_basis_count == 0,
            "every_cluster_has_source_evidence": cluster_missing_contract_count == 0,
        },
        "consumer_notes": consumer_notes,
    }


def _workitem_cartography_consumption_contract(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """
    [ROLE]
    - Teleology: Sibling of `_cap_cartography_consumption_contract` over the
      WorkItem cartography view (`workitem_cartography_v0`). Mirrors the same
      readiness/visual_semantics/drilldown_contract grammar so renderers can
      treat both packets uniformly, while distinguishing between the bounded
      graph layer (`nodes`/`edges`) and the full row-grain `atlas_marks` layer.
    - Wire contract: Always emitted by `load_task_ledger_projection`; payload
      may be missing if the projection has not been rebuilt yet.
    """
    source_view = "state/task_ledger/views/workitem_cartography.json"
    if not isinstance(payload, Mapping) or payload.get("schema_version") not in {
        "workitem_cartography_v0",
        "workitem_cartography_v1",
    }:
        return {
            "schema_version": "workitem_cartography_consumption_contract_v0",
            "source_view": source_view,
            "available": False,
            "frontend_posture": {
                "mode": "observe_only",
                "workitem_creation_supported": False,
                "mutation_supported": False,
                "source_route_supported": False,
            },
            "readiness": {
                "strict_json": False,
                "atlas_marks_ready": False,
                "overview_graph_ready": False,
                "overview_complete": False,
                "atlas_mark_count": 0,
                "node_count": 0,
                "edge_count": 0,
                "cluster_count": 0,
                "lineage_index_count": 0,
                "orphan_edge_count": 0,
                "missing_lineage_count": 0,
                "edge_limit_hit": False,
                "visible_node_limit_hit": False,
                "overflow_index_available": False,
                "drilldown_index_available": False,
                "unclassified_index_available": False,
                "unclassified_count": 0,
                "omitted_edge_count": 0,
                "warning_count": 1,
                "source_work_item_count": 0,
            },
            "consumer_notes": [
                "workitem_cartography projection is unavailable; rebuild Task Ledger projections before rendering.",
            ],
        }

    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    legend = payload.get("legend") if isinstance(payload.get("legend"), Mapping) else {}
    levels_raw = payload.get("levels") or []
    levels = [row for row in levels_raw if isinstance(row, Mapping)]
    overflow_policy = (
        payload.get("overflow_policy") if isinstance(payload.get("overflow_policy"), Mapping) else {}
    )
    overflow_index = (
        payload.get("overflow_index") if isinstance(payload.get("overflow_index"), Mapping) else {}
    )
    drilldown_index = payload.get("drilldown_index") or []
    unclassified_index = (
        payload.get("unclassified_index")
        if isinstance(payload.get("unclassified_index"), Mapping)
        else {}
    )
    omission_receipt = (
        payload.get("omission_receipt")
        if isinstance(payload.get("omission_receipt"), Mapping)
        else {}
    )
    nodes = [row for row in (payload.get("nodes") or []) if isinstance(row, Mapping)]
    edges = [row for row in (payload.get("edges") or []) if isinstance(row, Mapping)]
    clusters = [row for row in (payload.get("clusters") or []) if isinstance(row, Mapping)]
    lineage = [row for row in (payload.get("lineage_index") or []) if isinstance(row, Mapping)]
    atlas_marks = [row for row in (payload.get("atlas_marks") or []) if isinstance(row, Mapping)]
    warnings_raw = payload.get("warnings") or []
    warnings = [row for row in warnings_raw if isinstance(row, Mapping)]

    resolvable_ids = {str(cluster.get("id") or "") for cluster in clusters if cluster.get("id")}
    resolvable_ids.update(str(node.get("id") or "") for node in nodes if node.get("id"))
    orphan_edge_count = sum(
        1
        for edge in edges
        if str(edge.get("source") or "") not in resolvable_ids
        or str(edge.get("target") or "") not in resolvable_ids
    )
    edge_missing_contract_count = sum(
        1
        for edge in edges
        if not edge.get("edge_kind") or not edge.get("confidence") or not edge.get("source_ref")
    )
    cluster_missing_contract_count = sum(
        1
        for cluster in clusters
        if not all(
            key in cluster
            for key in ("cluster_kind", "member_count", "representative_ids", "confidence", "source_evidence")
        )
    )
    node_missing_basis_count = sum(
        1
        for node in nodes
        if not node.get("source_refs") and not node.get("cluster_ids")
    )
    lineage_ids = {str(row.get("display_id") or "") for row in lineage if row.get("display_id")}
    visible_node_ids = [str(node.get("id") or "") for node in nodes if node.get("id")]
    missing_lineage_count = sum(1 for node_id in visible_node_ids if node_id not in lineage_ids)
    edge_kind_counts = Counter(str(edge.get("edge_kind") or "unknown") for edge in edges)
    edge_confidence_counts = Counter(str(edge.get("confidence") or "unknown") for edge in edges)
    warning_names = {str(warning.get("warning") or "") for warning in warnings if warning.get("warning")}
    edge_limit_hit = "edge_limit_hit" in warning_names or bool(overflow_index.get("edge_limit_hit"))
    visible_node_limit_hit = "visible_node_limit_hit" in warning_names or bool(
        overflow_index.get("visible_node_limit_hit")
    )
    omitted_edge_count = int(overflow_index.get("omitted_edge_count") or summary.get("omitted_edge_count") or 0)
    unclassified_count = int(unclassified_index.get("count") or 0)
    bounded_omission_exists = any(
        [
            edge_limit_hit,
            visible_node_limit_hit,
            bool(overflow_index.get("cluster_representative_limit_hit")),
            omitted_edge_count > 0,
        ]
    )
    source_work_item_count = int(summary.get("source_work_item_count") or 0)
    atlas_mark_count = len(atlas_marks)
    atlas_marks_ready = (
        source_work_item_count > 0
        and atlas_mark_count == source_work_item_count
        and all(mark.get("id") and mark.get("state") and mark.get("work_item_type") for mark in atlas_marks)
    )
    overview_graph_ready = (
        orphan_edge_count == 0
        and missing_lineage_count == 0
        and edge_missing_contract_count == 0
        and cluster_missing_contract_count == 0
        and node_missing_basis_count == 0
    )
    overview_complete = bool(overview_graph_ready and not bounded_omission_exists)

    color_basis_options = list(legend.get("color_basis_options") or [])
    overlay_options = list(legend.get("overlay_options") or [])
    legend_carryover_present = (
        "carryover" in [str(opt).lower() for opt in color_basis_options]
        or "carryover" in [str(opt).lower() for opt in overlay_options]
    )
    legend_unrouted_present = (
        any("unrout" in str(opt).lower() or "no_execution_route" in str(opt).lower()
            for opt in overlay_options + color_basis_options)
    )
    # Wave 2A — route provenance contract gates. The cartography payload
    # carries route_explanation per unrouted atlas_mark and a summary
    # route_provenance block. Wave 2A.1 adds evidence-shape attestation:
    # every unrouted mark must carry evidence_refs OR evidence_fields, and
    # the consumer notes flag a violation if any reason ships without
    # either.
    route_provenance_summary = summary.get("route_provenance") if isinstance(summary.get("route_provenance"), Mapping) else {}
    route_provenance_explained_count = int(route_provenance_summary.get("explained_count") or 0)
    route_provenance_unknown_count = int(route_provenance_summary.get("unknown_count") or 0)
    route_provenance_reason_counts = (
        dict(route_provenance_summary.get("reason_counts") or {})
        if isinstance(route_provenance_summary.get("reason_counts"), Mapping)
        else {}
    )
    route_provenance_reason_kinds = (
        dict(route_provenance_summary.get("reason_kind_counts") or {})
        if isinstance(route_provenance_summary.get("reason_kind_counts"), Mapping)
        else {}
    )
    route_provenance_predicate_kinds = (
        dict(route_provenance_summary.get("predicate_kind_counts") or {})
        if isinstance(route_provenance_summary.get("predicate_kind_counts"), Mapping)
        else {}
    )
    route_provenance_evidence_ok_count = int(
        route_provenance_summary.get("evidence_ok_count") or 0
    )
    route_provenance_evidence_missing_count = int(
        route_provenance_summary.get("evidence_missing_count") or 0
    )
    route_provenance_evidence_missing_by_reason = (
        dict(route_provenance_summary.get("evidence_missing_by_reason") or {})
        if isinstance(route_provenance_summary.get("evidence_missing_by_reason"), Mapping)
        else {}
    )
    route_provenance_predicate_evidence_contract = (
        dict(route_provenance_summary.get("predicate_evidence_contract") or {})
        if isinstance(route_provenance_summary.get("predicate_evidence_contract"), Mapping)
        else {}
    )
    route_provenance_schema_version = str(
        route_provenance_summary.get("schema_version") or ""
    )
    # Wave 2B — Reason → Remedy Map attestation. The projection stamps
    # `resolution_affordances` per reason; the contract surfaces a present
    # flag, a remedy-coverage count, and the disposition histogram so a
    # consumer can render the chips without re-deriving the contract.
    route_provenance_resolution_affordances = (
        dict(route_provenance_summary.get("resolution_affordances") or {})
        if isinstance(route_provenance_summary.get("resolution_affordances"), Mapping)
        else {}
    )
    route_provenance_resolution_summary = (
        dict(route_provenance_summary.get("resolution_summary") or {})
        if isinstance(route_provenance_summary.get("resolution_summary"), Mapping)
        else {}
    )
    route_provenance_resolution_present = (
        bool(route_provenance_resolution_affordances)
        and all(
            isinstance(row, Mapping)
            and row.get("resolution_disposition")
            and row.get("resolution_status")
            for row in route_provenance_resolution_affordances.values()
        )
    )
    route_provenance_resolution_reason_with_remedy_count = int(
        route_provenance_resolution_summary.get("reason_with_remedy_count") or 0
    )
    route_provenance_resolution_reason_without_remedy_count = int(
        route_provenance_resolution_summary.get("reason_without_remedy_count") or 0
    )
    route_provenance_resolution_status_counts = (
        dict(route_provenance_resolution_summary.get("resolution_status_counts") or {})
        if isinstance(
            route_provenance_resolution_summary.get("resolution_status_counts"), Mapping
        )
        else {}
    )
    route_provenance_resolution_disposition_counts = (
        dict(
            route_provenance_resolution_summary.get("resolution_disposition_counts") or {}
        )
        if isinstance(
            route_provenance_resolution_summary.get("resolution_disposition_counts"),
            Mapping,
        )
        else {}
    )
    # Wave 2D — lane_relationship semantics. The projection now stamps
    # each affordance with `lane_relationship` (exact / contains / partial
    # / target / benign / fallback) computed from measured owner_view
    # membership overlap. The contract surfaces a present flag, the
    # relationship-count histogram, and per-reason audit fields so the
    # consumer can choose chip language honestly.
    route_provenance_resolution_lane_audit = (
        dict(route_provenance_summary.get("resolution_lane_audit") or {})
        if isinstance(route_provenance_summary.get("resolution_lane_audit"), Mapping)
        else {}
    )
    route_provenance_resolution_lane_relationship_counts = (
        dict(route_provenance_resolution_lane_audit.get("relationship_counts") or {})
        if isinstance(
            route_provenance_resolution_lane_audit.get("relationship_counts"), Mapping
        )
        else {}
    )
    route_provenance_resolution_lane_semantics_present = (
        bool(route_provenance_resolution_affordances)
        and all(
            isinstance(row, Mapping)
            and row.get("lane_relationship")
            and row.get("lane_relationship_label") is not None
            for row in route_provenance_resolution_affordances.values()
        )
        and bool(route_provenance_resolution_lane_audit)
    )
    # Wave 2F — drillthrough materialization attestation. Every affordance
    # row must carry a drillthrough block with materialized card_route per
    # sample (id substituted into card_route_template); the contract emits
    # a violation note when any row is missing the block or its samples
    # have unmaterialized routes.
    route_provenance_resolution_drillthrough_audit = (
        dict(route_provenance_summary.get("resolution_drillthrough_audit") or {})
        if isinstance(
            route_provenance_summary.get("resolution_drillthrough_audit"), Mapping
        )
        else {}
    )
    route_provenance_resolution_drillthrough_present = bool(
        route_provenance_resolution_affordances
    ) and all(
        isinstance(row, Mapping)
        and isinstance(row.get("drillthrough"), Mapping)
        and row["drillthrough"].get("schema_version")
        == "workitem_route_resolution_drillthrough_v0"
        for row in route_provenance_resolution_affordances.values()
    )
    route_provenance_resolution_drillthrough_all_materialized = bool(
        route_provenance_resolution_drillthrough_audit.get("all_materialized", False)
    )
    route_provenance_unrouted_total = route_provenance_explained_count + route_provenance_unknown_count
    marks_carry_explanation = (
        atlas_mark_count > 0
        and all(isinstance(mark.get("route_explanation"), Mapping) for mark in atlas_marks)
    )
    # Wave 2A.1 — every unrouted mark must carry either evidence_refs or
    # evidence_fields. Routed marks are exempted (they have route_status="known").
    marks_carry_evidence = (
        atlas_mark_count > 0
        and all(
            (not bool((mark.get("overlays") or {}).get("unrouted")))
            or bool(
                (mark.get("route_explanation") or {}).get("evidence_refs")
                or (mark.get("route_explanation") or {}).get("evidence_fields")
            )
            for mark in atlas_marks
        )
    )
    route_provenance_present = (
        marks_carry_explanation
        and bool(route_provenance_summary)
        and (route_provenance_unrouted_total == 0 or route_provenance_explained_count + route_provenance_unknown_count > 0)
    )
    route_provenance_evidence_present = (
        route_provenance_present
        and marks_carry_evidence
        and route_provenance_evidence_missing_count == 0
    )
    route_provenance_carryover_status = str(
        route_provenance_summary.get("carryover_status") or "not_evaluated"
    )

    source_refs = list(payload.get("source_refs") or [])
    authority = payload.get("authority") if isinstance(payload.get("authority"), Mapping) else {}
    source_refs.extend(str(ref) for ref in authority.get("projection_inputs") or [] if ref)
    if authority.get("source"):
        source_refs.append(str(authority["source"]))
    source_refs = list(dict.fromkeys(source_refs))

    consumer_notes: list[str] = []
    if not atlas_marks_ready:
        consumer_notes.append(
            "atlas_marks layer is not ready: row count or basic fields do not reconcile with source_work_item_count."
        )
    if orphan_edge_count:
        consumer_notes.append(
            "Some graph edges reference ids outside nodes/clusters; renderer must treat the graph layer as not graph-ready."
        )
    if missing_lineage_count:
        consumer_notes.append("Some visible graph nodes lack lineage drilldown entries.")
    if edge_missing_contract_count:
        consumer_notes.append("Some graph edges lack edge_kind/confidence/source_ref.")
    if bounded_omission_exists:
        consumer_notes.append(
            "Graph overview is bounded; use overflow_index/drilldown_index for expansion. atlas_marks remains full universe."
        )
    if unclassified_count:
        consumer_notes.append(
            "Some WorkItem rows have unknown work_item_type or state; surface via unclassified_index, not as truth."
        )
    if legend_carryover_present:
        consumer_notes.append(
            "Legend contains a 'carryover' label but origin/current-scope semantics are not in substrate; renderer must reject this label."
        )
    if not legend_unrouted_present:
        consumer_notes.append(
            "Legend is missing the 'unrouted'/'no_execution_route' overlay; route.status='unknown' marks would render unlabelled."
        )
    # Wave 2A — emit a consumer note when route provenance is absent on a
    # v1+ payload. v0 payloads pre-date provenance and emit nothing here.
    if payload.get("schema_version") == "workitem_cartography_v1" and not route_provenance_present:
        consumer_notes.append(
            "Route provenance is missing on a v1 payload; renderer must treat unrouted marks as unexplained "
            "and avoid promoting any reason label until the projection is rebuilt."
        )
    # Wave 2A.1 — evidence-shape contract. A v1 payload that ships
    # route_explanation without evidence_refs or evidence_fields is
    # constitutionally dishonest and the renderer should drop the
    # explanation rather than show an unbacked label.
    if (
        payload.get("schema_version") == "workitem_cartography_v1"
        and route_provenance_present
        and not route_provenance_evidence_present
    ):
        consumer_notes.append(
            "route_provenance evidence layer is incomplete: "
            f"{route_provenance_evidence_missing_count} unrouted mark(s) carry no evidence_refs or evidence_fields. "
            "Renderer must suppress reason labels for affected rows until evidence is supplied."
        )
    # Wave 2B — Reason → Remedy Map contract. Every reason present in the
    # projection must declare a resolution_disposition + resolution_status.
    # A v1 payload that ships a labelled reason without an affordance row
    # is incomplete; the consumer should fall back to "inspect" rather
    # than silently dropping the chip.
    if (
        payload.get("schema_version") == "workitem_cartography_v1"
        and route_provenance_present
        and not route_provenance_resolution_present
    ):
        consumer_notes.append(
            "route_provenance resolution layer is incomplete: at least one reason in the projection "
            "lacks a typed resolution_disposition + resolution_status. Renderer should fall back to "
            "the 'inspect' disposition for affected reasons and surface the gap to the operator."
        )
    # Wave 2D — lane_relationship contract. A v1 payload with the
    # resolution layer present but no lane_relationship stamped on each
    # row implies measurement was skipped; the renderer should refuse the
    # flattened "lane:" chip and fall back to the generic disposition.
    if (
        payload.get("schema_version") == "workitem_cartography_v1"
        and route_provenance_resolution_present
        and not route_provenance_resolution_lane_semantics_present
    ):
        consumer_notes.append(
            "route_provenance lane_relationship layer is incomplete: at least one resolution_affordance "
            "row lacks a typed lane_relationship. Renderer must not imply current membership when only "
            "a target lane is named; fall back to the generic disposition chip until the layer is rebuilt."
        )
    # Wave 2F — drillthrough materialization contract. A v1 payload with
    # the resolution layer present but missing per-row drillthrough blocks
    # (or sample rows whose card_route is not materialized) cannot deliver
    # addressable sample navigation. Renderer should fall back to the
    # non-addressable summary chip until the layer is rebuilt.
    if (
        payload.get("schema_version") == "workitem_cartography_v1"
        and route_provenance_resolution_present
        and not route_provenance_resolution_drillthrough_present
    ):
        consumer_notes.append(
            "route_provenance drillthrough layer is incomplete: at least one resolution_affordance row "
            "lacks the workitem_route_resolution_drillthrough_v0 block. Renderer must avoid presenting "
            "sample-row navigation until materialized routes are supplied."
        )
    if route_provenance_carryover_status != "not_evaluated":
        consumer_notes.append(
            "route_provenance.carryover_status must remain 'not_evaluated' until origin/current-scope fields exist."
        )

    return {
        "schema_version": "workitem_cartography_consumption_contract_v0",
        "source_view": source_view,
        "generated_at": payload.get("generated_at"),
        "available": payload.get("schema_version") in {
            "workitem_cartography_v0",
            "workitem_cartography_v1",
        },
        "source_refs": source_refs,
        "frontend_posture": {
            "mode": "observe_only",
            "workitem_creation_supported": False,
            "mutation_supported": False,
            "source_route_supported": True,
            "frontend_actionable_workitem_mutation_supported": False,
        },
        "readiness": {
            "strict_json": payload.get("schema_version") in {
                "workitem_cartography_v0",
                "workitem_cartography_v1",
            },
            "schema_version": payload.get("schema_version"),
            "atlas_marks_ready": atlas_marks_ready,
            "overview_graph_ready": overview_graph_ready,
            "overview_complete": overview_complete,
            "source_work_item_count": source_work_item_count,
            "atlas_mark_count": atlas_mark_count,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "cluster_count": len(clusters),
            "lineage_index_count": len(lineage),
            "orphan_edge_count": orphan_edge_count,
            "missing_lineage_count": missing_lineage_count,
            "edge_missing_contract_count": edge_missing_contract_count,
            "cluster_missing_contract_count": cluster_missing_contract_count,
            "node_missing_basis_count": node_missing_basis_count,
            "edge_limit_hit": edge_limit_hit,
            "visible_node_limit_hit": visible_node_limit_hit,
            "overflow_index_available": bool(overflow_index),
            "drilldown_index_available": bool(drilldown_index),
            "unclassified_index_available": bool(unclassified_index),
            "unclassified_count": unclassified_count,
            "omitted_edge_count": omitted_edge_count,
            "overview_node_limit": overflow_policy.get("overview_node_limit"),
            "overview_edge_limit": overflow_policy.get("overview_edge_limit"),
            "warning_count": len(warnings),
            "source_evidenced_edge_count": edge_confidence_counts.get("source_evidenced", 0),
            "projection_inferred_edge_count": edge_confidence_counts.get("projection_inferred", 0),
        },
        "visual_semantics": {
            "color_basis_options": color_basis_options,
            "size_basis_options": list(legend.get("size_basis_options") or []),
            "overlay_options": overlay_options,
            "supported_levels": [str(level.get("id") or "") for level in levels if level.get("id")],
            "edge_kinds": dict(edge_kind_counts.most_common()),
            "confidence_values": list(legend.get("confidence_values") or []),
            "frontend_posture": legend.get("frontend_posture"),
            "carryover_label_policy": legend.get("carryover_label_policy"),
            "atlas_marks_layer_present": atlas_mark_count > 0,
        },
        "drilldown_contract": {
            "every_visible_node_has_task_ledger_card": all(
                isinstance(node.get("source_route_metadata"), Mapping)
                and node["source_route_metadata"].get("task_ledger_card")
                for node in nodes
            ),
            "every_edge_has_source_ref": edge_missing_contract_count == 0,
            "every_edge_endpoint_resolves": orphan_edge_count == 0,
            "every_node_has_source_or_cluster_basis": node_missing_basis_count == 0,
            "every_cluster_has_source_evidence": cluster_missing_contract_count == 0,
            "atlas_marks_reconciles_with_source_count": atlas_marks_ready,
            "carryover_label_absent": not legend_carryover_present,
            "unrouted_overlay_present": legend_unrouted_present,
            # Wave 2A — route provenance attestation.
            "route_provenance_present": route_provenance_present,
            "route_provenance_explained_count": route_provenance_explained_count,
            "route_provenance_unknown_count": route_provenance_unknown_count,
            "route_provenance_unrouted_total": route_provenance_unrouted_total,
            "route_provenance_reason_counts": route_provenance_reason_counts,
            "route_provenance_reason_kind_counts": route_provenance_reason_kinds,
            "route_provenance_carryover_status": route_provenance_carryover_status,
            # Wave 2A.1 — evidence-shape attestation.
            "route_provenance_evidence_present": route_provenance_evidence_present,
            "route_provenance_evidence_ok_count": route_provenance_evidence_ok_count,
            "route_provenance_evidence_missing_count": route_provenance_evidence_missing_count,
            "route_provenance_evidence_missing_by_reason": route_provenance_evidence_missing_by_reason,
            "route_provenance_predicate_kind_counts": route_provenance_predicate_kinds,
            "route_provenance_predicate_evidence_contract": route_provenance_predicate_evidence_contract,
            "route_provenance_schema_version": route_provenance_schema_version,
            # Wave 2B — Reason → Remedy Map attestation.
            "route_provenance_resolution_present": route_provenance_resolution_present,
            "route_provenance_resolution_affordances": route_provenance_resolution_affordances,
            "route_provenance_resolution_reason_with_remedy_count": (
                route_provenance_resolution_reason_with_remedy_count
            ),
            "route_provenance_resolution_reason_without_remedy_count": (
                route_provenance_resolution_reason_without_remedy_count
            ),
            "route_provenance_resolution_status_counts": route_provenance_resolution_status_counts,
            "route_provenance_resolution_disposition_counts": route_provenance_resolution_disposition_counts,
            # Wave 2D — lane_relationship semantics attestation.
            "route_provenance_resolution_lane_semantics_present": (
                route_provenance_resolution_lane_semantics_present
            ),
            "route_provenance_resolution_lane_relationship_counts": (
                route_provenance_resolution_lane_relationship_counts
            ),
            "route_provenance_resolution_lane_audit": (
                route_provenance_resolution_lane_audit
            ),
            # Wave 2F — drillthrough materialization attestation.
            "route_provenance_resolution_drillthrough_present": (
                route_provenance_resolution_drillthrough_present
            ),
            "route_provenance_resolution_drillthrough_all_materialized": (
                route_provenance_resolution_drillthrough_all_materialized
            ),
            "route_provenance_resolution_drillthrough_audit": (
                route_provenance_resolution_drillthrough_audit
            ),
        },
        "omission_receipt": dict(omission_receipt),
        "consumer_notes": consumer_notes,
    }


def _cap_cartography_string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [str(entry) for entry in value if entry not in (None, "")]


CAP_CARTOGRAPHY_SPECIMEN_REF_SAMPLE_LIMIT = 8


def _cap_cartography_sampled_string_list(
    value: Any,
    *,
    limit: int = CAP_CARTOGRAPHY_SPECIMEN_REF_SAMPLE_LIMIT,
) -> dict[str, Any]:
    entries = _cap_cartography_string_list(value)
    return {
        "sample": entries[:limit],
        "count": len(entries),
        "truncated": len(entries) > limit,
    }


def _cap_cartography_compact_lineage(lineage: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(lineage, Mapping):
        return {}
    drilldown = lineage.get("drilldown")
    if not isinstance(drilldown, Mapping):
        return {}
    compact: dict[str, Any] = {}
    task_card = drilldown.get("task_ledger_card")
    if task_card:
        compact["task_ledger_card"] = task_card
    for key in ("source_refs", "views", "proof_refs", "missing_refs"):
        sampled = _cap_cartography_sampled_string_list(drilldown.get(key))
        compact[key] = sampled["sample"]
        compact[f"{key}_count"] = sampled["count"]
        compact[f"{key}_truncated"] = sampled["truncated"]
    return compact


def _cap_cartography_element_actions(source_route_metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "inspect_supported": bool(source_route_metadata),
        "source_route_supported": bool(source_route_metadata),
        "cap_creation_supported": False,
        "mutation_supported": False,
        "frontend_actionable_cap_mutation_supported": False,
    }


def _cap_cartography_source_route_metadata(row: Mapping[str, Any]) -> dict[str, Any]:
    route = row.get("source_route_metadata")
    if isinstance(route, Mapping):
        return dict(route)
    drilldown = row.get("drilldown")
    if isinstance(drilldown, Mapping):
        route_fields = {
            key: drilldown.get(key)
            for key in ("task_ledger_card", "source_refs", "views", "proof_refs", "missing_refs")
            if drilldown.get(key) not in (None, "", [])
        }
        if route_fields:
            return route_fields
    return {}


def _cap_cartography_exposition_specimen(
    payload: Mapping[str, Any] | None,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    source_view = "state/task_ledger/views/cap_cartography.json"
    if not isinstance(payload, Mapping):
        return {
            "schema_version": "cap_cartography_exposition_specimen_v0",
            "source_ref": "/api/world-model/task-ledger/projection",
            "source_view": source_view,
            "source_schema_version": None,
            "mode": "observe_only",
            "available": False,
            "status": {
                "graph_ready": False,
                "complete": False,
                "bounded": False,
                "warnings": ["cap_cartography_unavailable"],
            },
            "frontend_posture": dict(contract.get("frontend_posture") or {}),
            "overview_tiles": [],
            "cluster_elements": [],
            "node_elements": [],
            "edge_elements": [],
            "drilldown_elements": [],
            "unclassified_elements": [],
            "legend": {},
            "blocked_actions": ["create_cap", "mutate_cap", "edit_edge", "infer_title_semantics"],
            "integrity": {
                "orphan_renderer_edge_count": 0,
                "omitted_renderer_edge_count": 0,
                "renderer_inferred_semantic_count": 0,
            },
        }

    readiness = contract.get("readiness") if isinstance(contract.get("readiness"), Mapping) else {}
    visual_semantics = (
        contract.get("visual_semantics")
        if isinstance(contract.get("visual_semantics"), Mapping)
        else {}
    )
    frontend_posture = (
        contract.get("frontend_posture")
        if isinstance(contract.get("frontend_posture"), Mapping)
        else {}
    )
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    overflow_index = (
        payload.get("overflow_index")
        if isinstance(payload.get("overflow_index"), Mapping)
        else {}
    )
    unclassified_index = (
        payload.get("unclassified_index")
        if isinstance(payload.get("unclassified_index"), Mapping)
        else {}
    )
    warnings = _cap_cartography_rows(payload, "warnings")
    warning_names = [str(row.get("warning")) for row in warnings if row.get("warning")]
    clusters = _cap_cartography_rows(payload, "clusters")
    nodes = _cap_cartography_rows(payload, "nodes")
    edges = _cap_cartography_rows(payload, "edges")
    drilldown_index = _cap_cartography_rows(payload, "drilldown_index")
    drilldown_by_id = {
        str(row.get("id")): row
        for row in drilldown_index
        if row.get("id")
    }
    lineage_rows = _cap_cartography_rows(payload, "lineage_index")
    lineage_by_display_id = {
        str(row.get("display_id")): row
        for row in lineage_rows
        if row.get("display_id")
    }

    cluster_elements: list[dict[str, Any]] = []
    for cluster in clusters:
        route = _cap_cartography_source_route_metadata(cluster)
        if not route:
            drilldown_row = drilldown_by_id.get(str(cluster.get("id") or ""))
            if isinstance(drilldown_row, Mapping):
                route = _cap_cartography_source_route_metadata(drilldown_row)
        cluster_elements.append(
            {
                "id": cluster.get("id"),
                "kind": "cluster",
                "label": cluster.get("label"),
                "semantic_classes": {
                    "cluster_kind": cluster.get("cluster_kind"),
                    "confidence": cluster.get("confidence"),
                    "color_basis": cluster.get("cluster_kind"),
                    "size_basis": "member_count",
                },
                "member_count": cluster.get("member_count"),
                "representative_ids": _cap_cartography_string_list(cluster.get("representative_ids")),
                "source_evidence": cluster.get("source_evidence"),
                "source_route_metadata": route,
                "actions": _cap_cartography_element_actions(route),
            }
        )

    node_elements: list[dict[str, Any]] = []
    for node in nodes:
        node_id = str(node.get("id") or "")
        overview = {}
        detail = {}
        lod = node.get("lod") if isinstance(node.get("lod"), Mapping) else {}
        if isinstance(lod.get("overview"), Mapping):
            overview = dict(lod["overview"])
        if isinstance(lod.get("detail"), Mapping):
            detail = dict(lod["detail"])
        route = _cap_cartography_source_route_metadata(node)
        lineage = lineage_by_display_id.get(node_id)
        source_refs = _cap_cartography_sampled_string_list(node.get("source_refs"))
        missing_refs = _cap_cartography_sampled_string_list(node.get("missing_refs"))
        node_elements.append(
            {
                "id": node_id,
                "kind": "node",
                "label": node.get("label"),
                "node_kind": node.get("node_kind"),
                "semantic_classes": {
                    "node_kind": node.get("node_kind"),
                    "cluster_ids": _cap_cartography_string_list(node.get("cluster_ids")),
                    "semantic_role": detail.get("semantic_role"),
                    "temporal_role": detail.get("temporal_role"),
                    "state": detail.get("state"),
                    "proof_readiness": detail.get("proof_readiness"),
                    "color_basis": overview.get("color_basis"),
                    "size_basis": overview.get("size_basis"),
                },
                "source_refs": source_refs["sample"],
                "source_ref_count": source_refs["count"],
                "source_refs_truncated": source_refs["truncated"],
                "missing_refs": missing_refs["sample"],
                "missing_ref_count": missing_refs["count"],
                "missing_refs_truncated": missing_refs["truncated"],
                "source_route_metadata": route,
                "lineage": _cap_cartography_compact_lineage(lineage),
                "actions": _cap_cartography_element_actions(route),
            }
        )

    rendered_ids = {
        str(element.get("id"))
        for element in [*cluster_elements, *node_elements]
        if element.get("id")
    }
    edge_elements: list[dict[str, Any]] = []
    omitted_renderer_edge_count = 0
    for edge in edges:
        source_id = str(edge.get("source") or "")
        target_id = str(edge.get("target") or "")
        if source_id not in rendered_ids or target_id not in rendered_ids:
            omitted_renderer_edge_count += 1
            continue
        edge_elements.append(
            {
                "id": edge.get("id"),
                "kind": "edge",
                "source": source_id,
                "target": target_id,
                "semantic_classes": {
                    "edge_kind": edge.get("edge_kind"),
                    "confidence": edge.get("confidence"),
                },
                "edge_kind": edge.get("edge_kind"),
                "confidence": edge.get("confidence"),
                "source_ref": edge.get("source_ref"),
                "actions": _cap_cartography_element_actions(
                    {"source_ref": edge.get("source_ref")} if edge.get("source_ref") else None
                ),
            }
        )

    drilldown_elements: list[dict[str, Any]] = []
    for row in drilldown_index:
        route = _cap_cartography_source_route_metadata(row)
        drilldown_elements.append(
            {
                "id": row.get("id"),
                "kind": row.get("kind") or "drilldown",
                "cluster_kind": row.get("cluster_kind"),
                "value": row.get("value"),
                "member_count": row.get("member_count"),
                "representative_ids": _cap_cartography_string_list(row.get("representative_ids")),
                "member_sample_ids": _cap_cartography_string_list(row.get("member_sample_ids")),
                "overflow_member_count": row.get("overflow_member_count"),
                "missing_counts": dict(row.get("missing_counts") or {}),
                "confidence": row.get("confidence"),
                "source_evidence": row.get("source_evidence"),
                "source_route_metadata": route,
                "actions": _cap_cartography_element_actions(route),
            }
        )

    candidate_fields = _cap_cartography_string_list(unclassified_index.get("candidate_fields_to_check"))
    unclassified_elements: list[dict[str, Any]] = []
    sample_rows = unclassified_index.get("sample_rows") or []
    if isinstance(sample_rows, Sequence) and not isinstance(sample_rows, (str, bytes)):
        for row in sample_rows:
            if not isinstance(row, Mapping):
                continue
            route = _cap_cartography_source_route_metadata(row)
            unclassified_elements.append(
                {
                    "id": row.get("id"),
                    "kind": "unclassified_cap",
                    "classification_status": "unclassified",
                    "title": row.get("title"),
                    "state": row.get("state"),
                    "candidate_fields_to_check": candidate_fields,
                    "source_route_metadata": route,
                    "actions": _cap_cartography_element_actions(route),
                }
            )

    overview_tiles = [
        {"id": "cap_universe_count", "value": summary.get("cap_universe_count")},
        {"id": "cluster_count", "value": readiness.get("cluster_count") or summary.get("cluster_count")},
        {"id": "node_count", "value": readiness.get("node_count") or summary.get("node_count")},
        {"id": "edge_count", "value": readiness.get("edge_count") or summary.get("edge_count")},
        {"id": "omitted_edge_count", "value": readiness.get("omitted_edge_count") or summary.get("omitted_edge_count")},
        {"id": "unclassified_count", "value": readiness.get("unclassified_count") or summary.get("unclassified_count")},
    ]

    graph_ready = bool(readiness.get("overview_graph_ready"))
    complete = bool(readiness.get("overview_complete"))
    bounded = bool(graph_ready and not complete)
    return {
        "schema_version": "cap_cartography_exposition_specimen_v0",
        "source_ref": "/api/world-model/task-ledger/projection",
        "source_view": source_view,
        "source_schema_version": payload.get("schema_version"),
        "mode": "observe_only",
        "available": payload.get("schema_version") == "cap_cartography_v0",
        "status": {
            "graph_ready": graph_ready,
            "complete": complete,
            "bounded": bounded,
            "edge_limit_hit": bool(readiness.get("edge_limit_hit")),
            "overflow_index_available": bool(readiness.get("overflow_index_available")),
            "drilldown_index_available": bool(readiness.get("drilldown_index_available")),
            "unclassified_index_available": bool(readiness.get("unclassified_index_available")),
            "warnings": warning_names,
        },
        "frontend_posture": dict(frontend_posture),
        "overview_tiles": overview_tiles,
        "cluster_elements": cluster_elements,
        "node_elements": node_elements,
        "edge_elements": edge_elements,
        "drilldown_elements": drilldown_elements,
        "unclassified_elements": unclassified_elements,
        "legend": {
            "color_basis_options": list(visual_semantics.get("color_basis_options") or []),
            "size_basis_options": list(visual_semantics.get("size_basis_options") or []),
            "edge_kinds": dict(visual_semantics.get("edge_kinds") or {}),
            "confidence_values": list(visual_semantics.get("confidence_values") or []),
            "levels": list(visual_semantics.get("supported_levels") or []),
        },
        "blocked_actions": ["create_cap", "mutate_cap", "edit_edge", "infer_title_semantics"],
        "overflow_summary": {
            "overview_complete": complete,
            "overview_edge_limit": readiness.get("overview_edge_limit"),
            "omitted_edge_count": readiness.get("omitted_edge_count"),
            "omitted_edge_counts": dict(overflow_index.get("omitted_edge_counts") or {}),
            "omitted_sample": list(overflow_index.get("omitted_sample") or []),
        },
        "integrity": {
            "orphan_renderer_edge_count": 0,
            "omitted_renderer_edge_count": omitted_renderer_edge_count,
            "renderer_inferred_semantic_count": 0,
            "rendered_node_count": len(node_elements),
            "rendered_cluster_count": len(cluster_elements),
            "rendered_edge_count": len(edge_elements),
        },
    }


def _task_ledger_route(item: Mapping[str, Any]) -> dict[str, Any]:
    execution = item.get("execution") if isinstance(item.get("execution"), Mapping) else {}
    route = {
        "phase_id": execution.get("phase_id"),
        "source_queue": execution.get("source_queue"),
        "queue_sequence": execution.get("queue_sequence"),
        "queue_bucket": execution.get("queue_bucket"),
        "route": execution.get("route"),
    }
    known = any(value not in (None, "", []) for value in route.values())
    route["status"] = "known" if known else "unknown"
    if not known:
        route["omission_reason"] = "No phase/subphase route metadata is present on this WorkItem row."
    return route


def _task_ledger_compact_item(item: Mapping[str, Any]) -> dict[str, Any]:
    completion = item.get("completion") if isinstance(item.get("completion"), Mapping) else {}
    projection = (
        item.get("projection_completeness")
        if isinstance(item.get("projection_completeness"), Mapping)
        else {}
    )
    return {
        "id": item.get("id") or item.get("subject_id") or item.get("event_id"),
        "title": item.get("title") or item.get("event_type") or "Untitled row",
        "state": item.get("state") or item.get("status"),
        "status": item.get("status") or item.get("state"),
        "work_item_type": item.get("work_item_type"),
        "candidate_work_item_type": item.get("candidate_work_item_type"),
        "rank": item.get("rank"),
        "updated_at": item.get("updated_at") or item.get("created_at"),
        "recommended_action": item.get("recommended_action"),
        "sign_off_required": bool(completion.get("signoff_required") or projection.get("needs_signoff")),
        "sign_off_id": item.get("sign_off_id"),
        "depends_on": list(item.get("depends_on") or [])[:6],
        "source_event_ids": list(item.get("source_event_ids") or [])[:6],
        "route": _task_ledger_route(item),
    }


def _task_ledger_event_tail(repo_root: Path, limit: int = 5) -> list[dict[str, Any]]:
    path = repo_root / "state/task_ledger/events.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    rows.append(
                        {
                            "event_id": parsed.get("event_id"),
                            "event_type": parsed.get("event_type"),
                            "subject_id": parsed.get("subject_id"),
                            "created_at": parsed.get("created_at"),
                            "created_by": parsed.get("created_by"),
                        }
                    )
        return rows[-limit:][::-1]
    except OSError:
        return []


def _task_ledger_legibility_projection(
    *,
    work_items: list[dict[str, Any]],
    view_payloads: Mapping[str, Mapping[str, Any]],
    view_counts: Mapping[str, int],
    limit: int,
) -> dict[str, Any]:
    clusters: list[dict[str, Any]] = []
    sampled_ids: set[str] = set()
    sample_limit = max(1, min(limit, 4))

    for spec in _TASK_LEDGER_LEGIBILITY_CLUSTERS:
        source_views = [str(view) for view in spec["source_views"]]
        source_view_counts = {view: int(view_counts.get(view, 0)) for view in source_views}
        seen: set[str] = set()
        sample_items: list[dict[str, Any]] = []
        for view in source_views:
            for raw_item in _task_ledger_view_items(view_payloads.get(view)):
                compact = _task_ledger_compact_item(raw_item)
                item_id = str(compact.get("id") or compact.get("title") or "")
                if not item_id or item_id in seen:
                    continue
                seen.add(item_id)
                if len(sample_items) < sample_limit:
                    item_with_source = dict(compact)
                    item_with_source["source_views"] = [view]
                    sample_items.append(item_with_source)
                    sampled_ids.add(item_id)

        count = len(seen) if seen else sum(source_view_counts.values())
        if count == 0:
            severity = "muted"
        elif spec["cluster_id"] in {"closeout", "blocked", "quality_gaps", "intake"}:
            severity = "warn"
        else:
            severity = "ok"

        clusters.append(
            {
                "cluster_id": spec["cluster_id"],
                "label": spec["label"],
                "description": spec["description"],
                "count": count,
                "severity": severity,
                "source_views": source_views,
                "source_view_counts": source_view_counts,
                "action_label": spec["action_label"],
                "sample_items": sample_items,
                "omission_receipt": {
                    "omitted": [
                        "full WorkItem rows",
                        "full raw event payloads",
                        "rows beyond the per-cluster sample limit",
                    ],
                    "reason": "Legibility clusters are navigational compression; source views remain authority for membership.",
                    "drilldown": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
                },
            }
        )

    severity_order = {"warn": 0, "ok": 1, "muted": 2}
    next_action_groups = [
        {
            "cluster_id": cluster["cluster_id"],
            "label": cluster["label"],
            "count": cluster["count"],
            "severity": cluster["severity"],
            "action_label": cluster["action_label"],
            "source_views": cluster["source_views"],
        }
        for cluster in sorted(
            (cluster for cluster in clusters if cluster["count"] > 0),
            key=lambda cluster: (severity_order.get(str(cluster["severity"]), 3), -int(cluster["count"])),
        )[:6]
    ]

    return {
        "kind": "task_ledger_legibility_clusters_v1",
        "cluster_policy": "Group existing Task Ledger source views into pressure buckets; clusters are navigational compression, not scheduler authority.",
        "clusters": clusters,
        "next_action_groups": next_action_groups,
        "compression_honesty": {
            "sample_limit_per_cluster": sample_limit,
            "sampled_item_count": len(sampled_ids),
            "omitted_count": max(0, len(work_items) - len(sampled_ids)),
            "omission_policy": "Rows omitted from cluster samples remain available in state/task_ledger/views/* and kernel task_ledger flag/card drilldowns.",
            "authority": "state/task_ledger/events.jsonl, state/task_ledger/ledger.json, and state/task_ledger/views/*.json",
            "mutation_boundary": "read_only_existing_writers_remain_authority",
        },
        "design_receipt": {
            "owner_surfaces": [
                "state/task_ledger/events.jsonl",
                "state/task_ledger/ledger.json",
                "state/task_ledger/views/*.json",
                "/api/world-model/task-ledger/projection",
                "/station/ledger",
            ],
            "read_model_projection_changes": [
                "Add legibility clusters over existing Task Ledger views inside the existing projection endpoint.",
                "Expose sample rows, source view counts, next-action groups, and omission receipts without changing authority.",
            ],
            "compression_bands": ["now", "closeout", "blocked", "quality_gaps", "intake", "assignable", "stale_or_replay"],
            "dependency_doctrine_join_semantics": {
                "dependency": "depends_on and dependency_* views define blocker neighborhoods; clusters only point to those rows.",
                "doctrine": "satisfaction_contract, integration_contract, evidence_refs, principle_refs, and axiom_refs remain row-level drilldowns until a governed doctrine-graph join is authored.",
            },
            "validation": [
                "./repo-python tools/meta/factory/task_ledger_apply.py validate",
                "./repo-python kernel.py --phase 09_51 --warnings-only",
                "./repo-pytest system/server/tests/test_world_model_frontend_workitem_diagnostics.py system/server/tests/test_kernel_default_invocation.py -q",
                "cd system/server/ui && npm test -- src/pages/__tests__/StationLens.ledger.test.tsx",
                "cd system/server/ui && npm run build",
            ],
            "discoverability_refresh": [
                "./repo-python tools/meta/observability/frontend_nav_graph.py --check",
                "./repo-python tools/meta/observability/frontend_component_index.py --check",
                "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            ],
        },
    }


def _task_ledger_current_next(
    queue: Mapping[str, Any] | None,
    ledger_by_id: Mapping[str, Mapping[str, Any]],
    *,
    queue_path: str = _TASK_LEDGER_QUEUE_FALLBACK_REL,
) -> dict[str, Any]:
    current_id = str((queue or {}).get("current_next") or "").strip()
    queue_row: Mapping[str, Any] | None = None
    if queue and current_id:
        for section in ("ordered_execution_queue", "candidate_inventory"):
            for item in queue.get(section) or []:
                if isinstance(item, Mapping) and item.get("id") == current_id:
                    queue_row = item
                    break
            if queue_row:
                break
    ledger_row = ledger_by_id.get(current_id) if current_id else None
    state = (ledger_row or queue_row or {}).get("state") if (ledger_row or queue_row) else None
    if not current_id:
        label = "No phase-local current_next is published."
        tone = "warn"
    elif state in {"done", "signoff", "retired"}:
        label = "Advance the phase-local queue; current_next already closed."
        tone = "warn"
    elif state in {"active", "claimed", "shaping", "captured", "ready"}:
        label = "Continue the phase-local current_next WorkItem."
        tone = "ok"
    else:
        label = "Inspect current_next before acting; state is unknown."
        tone = "warn"
    return {
        "id": current_id or None,
        "label": label,
        "tone": tone,
        "queue": {
            "path": queue_path,
            "reconciled_at": (queue or {}).get("reconciled_at"),
            "sequence": (queue_row or {}).get("sequence"),
            "bucket": (queue_row or {}).get("bucket"),
            "state": (queue_row or {}).get("state"),
        },
        "work_item": _task_ledger_compact_item(ledger_row or queue_row or {}) if current_id else None,
    }


def _diagnostic_projection_envelope(
    *,
    schema: str,
    authority: Mapping[str, Any],
    freshness: Mapping[str, Any],
    current_next: Mapping[str, Any],
    projection_honesty: Mapping[str, Any],
) -> dict[str, Any]:
    """Shared read-only envelope for Station-facing diagnostic projections."""
    return {
        "schema": schema,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority": dict(authority),
        "freshness": dict(freshness),
        "current_next": dict(current_next),
        "projection_honesty": dict(projection_honesty),
        "projection_contract": {
            "kind": "read_only_diagnostic_projection_envelope_v1",
            "required_fields": [
                "schema",
                "generated_at",
                "authority",
                "freshness",
                "current_next",
                "projection_honesty",
            ],
            "authority_boundary": authority.get("boundary"),
            "mutation_boundary": "read_only_existing_writers_remain_authority",
            "station_consumer": authority.get("station_consumer"),
            "endpoint": authority.get("endpoint"),
            "phase_scope": projection_honesty.get("phase_scope"),
            "unknown_policy": projection_honesty.get("unknown_policy")
            or projection_honesty.get("route_metadata_policy"),
            "public_projection_status": projection_honesty.get("public_projection_status"),
        },
    }


def _meta_top_counter_rows(payload: Any, *, limit: int = 8) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    rows: list[dict[str, Any]] = []
    for key, value in payload.items():
        try:
            count = int(value)
        except (TypeError, ValueError):
            continue
        rows.append({"id": str(key), "label": str(key), "count": count})
    rows.sort(key=lambda row: (-int(row["count"]), str(row["id"])))
    return rows[: max(0, limit)]


def _meta_payload_count(payload: Any) -> int | None:
    if not isinstance(payload, Mapping):
        return None
    for key in (
        "count",
        "event_count",
        "trace_count",
        "node_count",
        "edge_count",
        "work_item_count",
        "pattern_count",
        "annex_count",
    ):
        value = payload.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return int(value)
    for key in ("items", "rows", "traces", "nodes", "edges", "facts", "capability_slices"):
        value = payload.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return len(value)
    summary = payload.get("summary")
    if isinstance(summary, Mapping):
        for key in ("work_item_count", "module_count", "fact_count", "node_count", "edge_count"):
            value = summary.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return int(value)
    return None


def _meta_mapping_or_status(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if value in (None, ""):
        return {}
    return {"status": str(value)}


def _meta_source_health(
    repo_root: Path,
    rel_path: str,
    *,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    full = repo_root / rel_path
    available = full.is_file()
    generated_at = payload.get("generated_at") if isinstance(payload, Mapping) else None
    return {
        "source_path": rel_path,
        "available": available,
        "generated_at": generated_at,
        "freshness": compute_freshness(str(generated_at) if generated_at else _file_mtime(repo_root, rel_path)),
        "record_count": _meta_payload_count(payload),
    }


def _meta_latest_agent_telemetry_dir(repo_root: Path) -> Path | None:
    root = repo_root / AGENT_TELEMETRY_ROOT
    if not root.exists() or not root.is_dir():
        return None
    candidates = [
        path
        for path in root.iterdir()
        if path.is_dir() and (path / "index.json").is_file()
    ]
    if not candidates:
        return None
    timestamped = [
        path for path in candidates if re.match(r"^\d{8}T\d{6}Z$", path.name)
    ]
    pool = timestamped or candidates
    try:
        return max(pool, key=lambda path: (path.name, path.stat().st_mtime))
    except OSError:
        return sorted(pool, key=lambda path: path.name)[-1]


def _meta_agent_telemetry(
    repo_root: Path,
    *,
    limit: int,
) -> dict[str, Any]:
    telemetry_dir = _meta_latest_agent_telemetry_dir(repo_root)
    if telemetry_dir is None:
        return {
            "available": False,
            "source_dir": f"{AGENT_TELEMETRY_ROOT}/<timestamp>",
            "latest_run": None,
            "scorecard": {},
            "top_tools": [],
            "top_shell_verbs": [],
            "top_files": [],
            "top_command_patterns": [],
            "top_tool_chains": [],
            "by_agent": {},
            "omission_receipt": {
                "reason": "No agent telemetry run with index.json is available.",
                "drilldown": "./repo-python tools/meta/agent_telemetry/extract.py",
            },
        }

    rel_dir = telemetry_dir.relative_to(repo_root).as_posix()
    index = _safe_read_json_path(telemetry_dir / "index.json") or {}
    scorecard = _safe_read_json_path(telemetry_dir / "navigation_scorecard.json") or {}
    by_agent = _safe_read_json_path(telemetry_dir / "by_agent.json") or {}
    tool_histogram = _safe_read_json_path(telemetry_dir / "tool_histogram.json") or {}
    bash_verbs = _safe_read_json_path(telemetry_dir / "bash_verbs.json") or {}
    file_heatmap = _safe_read_json_path(telemetry_dir / "file_heatmap.json") or {}
    command_patterns = _safe_read_json_path(telemetry_dir / "command_patterns.json") or {}
    tool_chains = _safe_read_json_path(telemetry_dir / "tool_chains.json") or {}

    return {
        "available": True,
        "source_dir": rel_dir,
        "latest_run": {
            "run_id": telemetry_dir.name,
            "generated_at": index.get("generated_at"),
            "records_emitted": index.get("records_emitted"),
            "claude_sessions_in_repo": index.get("claude_sessions_in_repo"),
            "codex_sessions_in_repo": index.get("codex_sessions_in_repo"),
            "freshness": compute_freshness(_path_mtime_iso(telemetry_dir / "index.json")),
        },
        "scorecard": {
            "sessions_total": scorecard.get("sessions_total"),
            "sessions_with_kernel": scorecard.get("sessions_with_kernel"),
            "sessions_with_shell_navigation": scorecard.get("sessions_with_shell_navigation"),
            "kernel_invocations": scorecard.get("kernel_invocations"),
            "shell_navigation_commands": scorecard.get("shell_navigation_commands"),
            "repo_native_commands": scorecard.get("repo_native_commands"),
            "python_inline_commands": scorecard.get("python_inline_commands"),
            "kernel_navigation_share": scorecard.get("kernel_navigation_share"),
        },
        "top_tools": _meta_top_counter_rows(tool_histogram, limit=limit),
        "top_shell_verbs": _meta_top_counter_rows(bash_verbs, limit=limit),
        "top_files": _meta_top_counter_rows(file_heatmap, limit=limit),
        "top_command_patterns": _meta_top_counter_rows(command_patterns, limit=limit),
        "top_tool_chains": _meta_top_counter_rows(tool_chains, limit=limit),
        "by_agent": {
            str(agent): {
                "session_count": (
                    value.get("session_count")
                    or value.get("sessions_total")
                    or value.get("records_emitted")
                ),
                "tool_counts": dict(value.get("tool_counts") or value.get("tools") or {}),
                "kernel_flag_counts": dict(value.get("kernel_flag_counts") or {}),
                "bash_verbs": dict(value.get("bash_verbs") or {}),
            }
            for agent, value in by_agent.items()
            if isinstance(value, Mapping)
        },
        "omission_receipt": {
            "omitted": [
                "sessions.jsonl raw session rows",
                "raw command spans",
                "full per-agent tool maps beyond top counters",
            ],
            "reason": "Console projection keeps behavior counters and drilldowns; session evidence remains in the telemetry run directory.",
            "drilldown": rel_dir,
        },
    }


def _meta_trace_board_rows(board: Mapping[str, Any], *, limit: int) -> list[dict[str, Any]]:
    rows = board.get("rows") if isinstance(board.get("rows"), list) else []
    compact_rows: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        recurrence = row.get("recurrence") if isinstance(row.get("recurrence"), Mapping) else {}
        owner = row.get("candidate_owner") if isinstance(row.get("candidate_owner"), Mapping) else {}
        action = (
            row.get("command_efficiency_action")
            if isinstance(row.get("command_efficiency_action"), Mapping)
            else {}
        )
        compact_rows.append(
            {
                "row_id": row.get("row_id"),
                "priority": row.get("priority"),
                "severity": row.get("severity"),
                "symptom_family": row.get("symptom_family"),
                "mode": row.get("mode"),
                "title": row.get("title"),
                "recurrence": {
                    "count": recurrence.get("count"),
                    "distinct_sessions": recurrence.get("distinct_sessions"),
                    "basis": recurrence.get("basis"),
                    "window": recurrence.get("window"),
                },
                "impact": list(row.get("impact") or [])[:5],
                "candidate_owner": {
                    "type": owner.get("type"),
                    "surface": owner.get("surface"),
                },
                "candidate_mutation": row.get("candidate_mutation"),
                "next_command": row.get("next_command"),
                "command_efficiency_action": {
                    "action_id": action.get("action_id"),
                    "inefficiency_class": action.get("inefficiency_class"),
                    "old_command_pattern": action.get("old_command_pattern"),
                    "replacement_route": action.get("replacement_route"),
                    "expected_proof": action.get("expected_proof"),
                    "seed_rewrite_clause": action.get("seed_rewrite_clause"),
                } if action else None,
                "cap_refs": list(row.get("cap_refs") or [])[:5],
            }
        )
    return compact_rows


def _meta_command_efficiency_action_rows(rows: Sequence[Any], *, limit: int) -> list[dict[str, Any]]:
    compact_rows: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        evidence = row.get("evidence") if isinstance(row.get("evidence"), Mapping) else {}
        compact_rows.append({
            "action_id": row.get("action_id"),
            "source_row_id": row.get("source_row_id"),
            "rank": row.get("rank"),
            "inefficiency_class": row.get("inefficiency_class"),
            "symptom_family": row.get("symptom_family"),
            "old_command_pattern": row.get("old_command_pattern"),
            "replacement_route": row.get("replacement_route"),
            "replacement_action": row.get("replacement_action"),
            "expected_proof": row.get("expected_proof"),
            "seed_rewrite_clause": row.get("seed_rewrite_clause"),
            "validation_preservation": row.get("validation_preservation"),
            "owner_surface": row.get("owner_surface"),
            "candidate_mutation": row.get("candidate_mutation"),
            "receipt_needed": list(row.get("receipt_needed") or [])[:5],
            "evidence": {
                "mode": evidence.get("mode"),
                "priority": evidence.get("priority"),
                "recurrence_count": evidence.get("recurrence_count"),
                "recurrence_basis": evidence.get("recurrence_basis"),
                "source_window": evidence.get("source_window"),
                "cap_refs": list(evidence.get("cap_refs") or [])[:5],
            },
        })
    return compact_rows


def _meta_compact_speedboard_rows(rows: Sequence[Any], *, limit: int) -> list[dict[str, Any]]:
    compact_rows: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if not isinstance(row, Mapping):
            continue
        compact_rows.append(
            {
                "surface_id": row.get("surface_id"),
                "class_id": row.get("class_id"),
                "change_id": row.get("change_id"),
                "before_real_s": row.get("before_real_s"),
                "after_real_s": row.get("after_real_s"),
                "saved_s_per_run": row.get("saved_s_per_run"),
                "saved_pct": row.get("saved_pct"),
                "cumulative_saved_s": row.get("cumulative_saved_s"),
                "owner_paths": list(row.get("owner_paths") or [])[:5],
                "validation_command": row.get("validation_command"),
            }
        )
    return compact_rows


def _meta_command_efficiency(
    repo_root: Path,
    *,
    limit: int,
) -> dict[str, Any]:
    trace_projection = _safe_read_json(repo_root, META_DIAGNOSTICS_TRACE_OBSERVATORY_PATH) or {}
    latency_speedboard = _safe_read_json(repo_root, META_DIAGNOSTICS_LATENCY_SPEEDBOARD_PATH) or {}
    process_summary = _safe_read_json(repo_root, META_DIAGNOSTICS_PROCESS_SUMMARY_PATH) or {}

    board = trace_projection.get("board") if isinstance(trace_projection.get("board"), Mapping) else {}
    action_packet = (
        trace_projection.get("command_efficiency_actions")
        if isinstance(trace_projection.get("command_efficiency_actions"), Mapping)
        else {}
    )
    source_windows = (
        trace_projection.get("source_windows")
        if isinstance(trace_projection.get("source_windows"), Mapping)
        else {}
    )
    live_window = source_windows.get("live") if isinstance(source_windows.get("live"), Mapping) else {}
    process_window = (
        live_window.get("process_summary")
        if isinstance(live_window.get("process_summary"), Mapping)
        else {}
    )
    bottleneck_window = (
        live_window.get("process_bottlenecks")
        if isinstance(live_window.get("process_bottlenecks"), Mapping)
        else {}
    )
    cap_views = source_windows.get("cap_views") if isinstance(source_windows.get("cap_views"), Mapping) else {}
    work_claims = (
        source_windows.get("work_ledger_claims")
        if isinstance(source_windows.get("work_ledger_claims"), Mapping)
        else {}
    )

    speed_summary = (
        latency_speedboard.get("summary")
        if isinstance(latency_speedboard.get("summary"), Mapping)
        else {}
    )
    pending = (
        latency_speedboard.get("pending_measurements")
        if isinstance(latency_speedboard.get("pending_measurements"), Mapping)
        else {}
    )
    ranked_savings = (
        latency_speedboard.get("ranked_savings")
        if isinstance(latency_speedboard.get("ranked_savings"), list)
        else []
    )
    wait_tax_rows = (
        latency_speedboard.get("ranked_wait_taxes")
        or latency_speedboard.get("ranked_wait_tax")
        or []
    )
    if not isinstance(wait_tax_rows, list):
        wait_tax_rows = []

    process_top_bottlenecks = process_summary.get("top_bottlenecks")
    if not isinstance(process_top_bottlenecks, list):
        process_top_bottlenecks = []
    process_top_outputs = process_summary.get("top_output_producers")
    if not isinstance(process_top_outputs, list):
        process_top_outputs = []

    top_rows = _meta_trace_board_rows(board, limit=limit)
    action_rows = _meta_command_efficiency_action_rows(
        action_packet.get("rows") if isinstance(action_packet.get("rows"), list) else [],
        limit=limit,
    )
    available = bool(trace_projection or latency_speedboard or process_summary)
    top_row = top_rows[0] if top_rows else {}
    next_commands: list[str] = []
    seen_next: set[str] = set()
    for value in [
        *[row.get("replacement_route") for row in action_rows],
        *[
            (top_row.get("command_efficiency_action") or {}).get("replacement_route")
            if isinstance(top_row.get("command_efficiency_action"), Mapping)
            else None
        ],
        top_row.get("next_command"),
        bottleneck_window.get("force_live_command"),
        process_window.get("next_command"),
    ]:
        text = str(value or "").strip()
        if not text or text in seen_next:
            continue
        seen_next.add(text)
        next_commands.append(text)

    return {
        "available": available,
        "source_paths": {
            "trace_observatory": META_DIAGNOSTICS_TRACE_OBSERVATORY_PATH,
            "latency_speedboard": META_DIAGNOSTICS_LATENCY_SPEEDBOARD_PATH,
            "process_summary": META_DIAGNOSTICS_PROCESS_SUMMARY_PATH,
        },
        "trace_observatory": {
            "source_path": META_DIAGNOSTICS_TRACE_OBSERVATORY_PATH,
            "generated_at": trace_projection.get("generated_at"),
            "status": board.get("status") or trace_projection.get("status") or ("available" if trace_projection else "missing"),
            "row_count": board.get("row_count"),
            "emitted_row_count": board.get("emitted_row_count") or len(top_rows),
            "top_symptom_families": list(trace_projection.get("top_symptom_families") or [])[:limit],
            "cap_refs": list(trace_projection.get("cap_refs") or [])[:limit],
            "top_rows": top_rows,
            "quality_gate": dict(trace_projection.get("trace_board_quality_gate") or {}),
            "compactness_metrics": dict(trace_projection.get("compactness_metrics") or {}),
            "drilldown_commands": list(trace_projection.get("drilldown_commands") or [])[:limit],
            "privacy_omission_receipts": list(trace_projection.get("privacy_omission_receipts") or [])[:limit],
        },
        "action_packet": {
            "schema_version": action_packet.get("schema_version"),
            "status": action_packet.get("status") or ("available" if action_rows else "missing"),
            "row_count": action_packet.get("row_count") or len(action_rows),
            "top_inefficiency_classes": list(action_packet.get("top_inefficiency_classes") or [])[:limit],
            "replacement_routes": list(action_packet.get("replacement_routes") or [])[:limit],
            "seed_rewrite_clauses": list(action_packet.get("seed_rewrite_clauses") or [])[:limit],
            "rows": action_rows,
            "before_after_replay": dict(action_packet.get("before_after_replay") or {}),
            "proof_commands": list(action_packet.get("proof_commands") or [])[:limit],
            "privacy_boundary": action_packet.get("privacy_boundary"),
        },
        "process_monitoring": {
            "process_summary_status": process_window.get("status") or ("available" if process_summary else "missing"),
            "process_summary_next_command": process_window.get("next_command"),
            "runtime_scoped_commands": list(process_window.get("runtime_scoped_commands") or [])[:limit],
            "selected_agent": process_window.get("selected_agent"),
            "selected_session_id": process_window.get("selected_session_id"),
            "warning_count": process_window.get("warning_count"),
            "warning_preview": process_window.get("warning_preview"),
            "bottleneck_status": bottleneck_window.get("status") or ("available" if process_top_bottlenecks else "missing"),
            "bottleneck_decision_authority": bottleneck_window.get("decision_authority"),
            "bottleneck_session_count": bottleneck_window.get("session_count"),
            "force_live_command": bottleneck_window.get("force_live_command"),
            "top_bottlenecks": [dict(row) for row in process_top_bottlenecks[:limit] if isinstance(row, Mapping)],
            "top_output_producers": [dict(row) for row in process_top_outputs[:limit] if isinstance(row, Mapping)],
        },
        "latency_speedboard": {
            "source_path": META_DIAGNOSTICS_LATENCY_SPEEDBOARD_PATH,
            "generated_at": latency_speedboard.get("generated_at"),
            "summary": dict(speed_summary),
            "pending": {
                "pending_count": pending.get("pending_count"),
                "session_count": pending.get("session_count"),
                "settlement_command": pending.get("settlement_command"),
                "write_settlement_command": pending.get("write_settlement_command"),
            },
            "top_savings": _meta_compact_speedboard_rows(ranked_savings, limit=limit),
            "top_wait_taxes": [dict(row) for row in wait_tax_rows[:limit] if isinstance(row, Mapping)],
        },
        "cap_alignment": {
            "status": cap_views.get("status"),
            "match_count": cap_views.get("match_count"),
            "top_ids": list(cap_views.get("top_ids") or [])[:limit],
            "next_command": cap_views.get("next_command"),
        },
        "work_ledger_claims": {
            "status": work_claims.get("status"),
            "generated_at": work_claims.get("generated_at"),
            "counts": dict(work_claims.get("counts") or {}),
            "refresh_command": work_claims.get("refresh_command"),
        },
        "recommended_next": next_commands[:limit],
        "omission_receipt": {
            "omitted": [
                "raw session bodies",
                "tool stdout/stderr bodies",
                "raw prompt/operator text",
                "full process spans",
            ],
            "reason": "Command efficiency is read from trace observatory, process-summary, and latency speedboard metadata; raw AgentTrace bodies stay behind owner drilldowns.",
            "drilldowns": next_commands[:limit] or [
                "./repo-python kernel.py --session-diagnostics --lens all --last 10 --store both --json --diagnostics-summary",
                "./repo-python kernel.py --process-bottlenecks",
            ],
        },
    }


def _meta_compact_workitem_evidence(row: Mapping[str, Any]) -> dict[str, Any]:
    compact = _task_ledger_compact_item(row)
    latest_receipt = (
        row.get("latest_execution_receipt")
        if isinstance(row.get("latest_execution_receipt"), Mapping)
        else None
    )
    validation_refs = [
        str(value)
        for value in (
            row.get("validation_refs")
            or row.get("validation")
            or (latest_receipt or {}).get("validation_refs")
            or []
        )
        if str(value).strip()
    ]
    commit_refs = [
        str(value)
        for value in (row.get("commit_refs") or (latest_receipt or {}).get("commit_refs") or [])
        if str(value).strip()
    ]
    return {
        **compact,
        "latest_execution_receipt": dict(latest_receipt) if latest_receipt else None,
        "validation_refs": validation_refs[:8],
        "commit_refs": commit_refs[:8],
        "receipt_refs": [
            str(value) for value in (row.get("receipt_refs") or [])[:8] if str(value).strip()
        ],
    }


def _meta_work_evidence(
    repo_root: Path,
    *,
    limit: int,
) -> dict[str, Any]:
    task_projection = load_task_ledger_projection(repo_root, limit=limit)
    workitem_cartography = _safe_read_json(repo_root, "state/task_ledger/views/workitem_cartography.json") or {}
    cap_cartography = _safe_read_json(repo_root, "state/task_ledger/views/cap_cartography.json") or {}
    mission_picture = _safe_read_json(repo_root, "state/task_ledger/views/mission_operating_picture.json") or {}
    dependency_blocked = _safe_read_json(repo_root, "state/task_ledger/views/dependency_blocked.json") or {}
    active_wip = _safe_read_json(repo_root, "state/task_ledger/views/active_wip.json") or {}
    propagation_needed = _safe_read_json(repo_root, "state/task_ledger/views/propagation_needed.json") or {}

    blocked_rows = []
    for row in _task_ledger_view_items(dependency_blocked)[:limit]:
        blocked_rows.append(
            {
                "id": row.get("id"),
                "title": row.get("title") or row.get("statement"),
                "state": row.get("state"),
                "dependency_status": row.get("dependency_status"),
                "depends_on": list(row.get("depends_on") or [])[:8],
                "downstream_unlock_ids": list(row.get("downstream_unlock_ids") or [])[:8],
            }
        )

    active_rows = [
        _meta_compact_workitem_evidence(row)
        for row in _task_ledger_view_items(active_wip)[:limit]
    ]
    mission_rows = [
        _meta_compact_workitem_evidence(row)
        for row in (
            mission_picture.get("current_mission_set")
            if isinstance(mission_picture.get("current_mission_set"), list)
            else []
        )[:limit]
        if isinstance(row, Mapping)
    ]
    workitem_summary = workitem_cartography.get("summary") if isinstance(workitem_cartography.get("summary"), Mapping) else {}
    cap_summary = cap_cartography.get("summary") if isinstance(cap_cartography.get("summary"), Mapping) else {}

    return {
        "task_ledger": {
            "counts": task_projection.get("counts"),
            "current_next": task_projection.get("current_next"),
            "overload": task_projection.get("overload"),
            "legibility_next_action_groups": (
                (task_projection.get("legibility") or {}).get("next_action_groups")
                if isinstance(task_projection.get("legibility"), Mapping)
                else []
            ),
        },
        "cartography": {
            "workitem": {
                "source_path": "state/task_ledger/views/workitem_cartography.json",
                "summary": dict(workitem_summary),
                "route_provenance": dict(workitem_summary.get("route_provenance") or {}),
                "resolution_summary": dict(workitem_summary.get("resolution_summary") or {}),
            },
            "cap": {
                "source_path": "state/task_ledger/views/cap_cartography.json",
                "summary": dict(cap_summary),
                "readiness": {
                    "proof_backed_count": cap_summary.get("proof_backed_count"),
                    "integration_contract_count": cap_summary.get("integration_contract_count"),
                    "integration_grounded_count": cap_summary.get("integration_grounded_count"),
                    "omitted_edge_count": cap_summary.get("omitted_edge_count"),
                    "overview_complete": cap_summary.get("overview_complete"),
                },
            },
        },
        "mission": {
            "summary": dict(mission_picture.get("summary") or {}),
            "current_mission_rows": mission_rows,
            "mission_trace_current_state": mission_picture.get("mission_trace_current_state"),
        },
        "active_receipts": active_rows,
        "dependency_blockers": {
            "count": dependency_blocked.get("count") or len(_task_ledger_view_items(dependency_blocked)),
            "rows": blocked_rows,
        },
        "propagation": {
            "count": propagation_needed.get("count") or len(_task_ledger_view_items(propagation_needed)),
            "source_path": "state/task_ledger/views/propagation_needed.json",
        },
        "drilldowns": {
            "task_projection": "/api/world-model/task-ledger/projection",
            "workitem_cartography": "/api/world-model/task-ledger/cartography/workitem",
            "cap_cartography": "/api/world-model/task-ledger/cartography/cap",
        },
    }


def _meta_capability_trust(
    repo_root: Path,
    *,
    limit: int,
) -> dict[str, Any]:
    capability = _safe_read_json(repo_root, META_DIAGNOSTICS_CAPABILITY_LANES_PATH) or {}
    facts = _safe_read_json(repo_root, META_DIAGNOSTICS_FACT_LEDGER_PATH) or {}
    navigation = _safe_read_json(repo_root, FRONTEND_NAV_GRAPH_PATH) or {}
    capability_slices = []
    for row in capability.get("capability_slices") or []:
        if not isinstance(row, Mapping):
            continue
        carriers = row.get("carriers") if isinstance(row.get("carriers"), list) else []
        capability_slices.append(
            {
                "slice_id": row.get("slice_id") or row.get("id"),
                "label": row.get("label") or row.get("title"),
                "summary": row.get("summary") or row.get("description"),
                "carrier_count": len(carriers),
                "availability_counts": dict(
                    Counter(
                        str(carrier.get("availability") or carrier.get("status") or "unknown")
                        for carrier in carriers
                        if isinstance(carrier, Mapping)
                    )
                ),
                "top_carriers": [
                    {
                        "id": carrier.get("id") or carrier.get("carrier_id"),
                        "label": carrier.get("label") or carrier.get("title"),
                        "availability": carrier.get("availability") or carrier.get("status"),
                        "source": carrier.get("source") or carrier.get("source_ref"),
                    }
                    for carrier in carriers[:3]
                    if isinstance(carrier, Mapping)
                ],
            }
        )
    nav_counts = navigation.get("counts") if isinstance(navigation.get("counts"), Mapping) else {}
    nav_status = (
        navigation.get("projection_status")
        if isinstance(navigation.get("projection_status"), Mapping)
        else {}
    )
    return {
        "capability_lanes": {
            "source_path": META_DIAGNOSTICS_CAPABILITY_LANES_PATH,
            "generated_at": capability.get("generated_at"),
            "summary_counts": dict(capability.get("summary_counts") or {}),
            "projection_status": _meta_mapping_or_status(capability.get("projection_status")),
            "availability_claim_boundary": capability.get("availability_claim_boundary"),
            "slices": capability_slices[:limit],
        },
        "derived_facts": {
            "source_path": META_DIAGNOSTICS_FACT_LEDGER_PATH,
            "generated_at": facts.get("generated_at"),
            "summary": dict(facts.get("summary") or {}),
        },
        "frontend_navigation": {
            "source_path": FRONTEND_NAV_GRAPH_PATH,
            "generated_at": navigation.get("generated_at"),
            "counts": dict(nav_counts),
            "projection_status": _meta_mapping_or_status(nav_status),
            "route_ready": (
                nav_status.get("status") in {None, "", "populated"}
                and int(nav_counts.get("pages") or 0) > 0
            ),
        },
    }


def _meta_doctrine_health(repo_root: Path, *, limit: int) -> dict[str, Any]:
    route_coverage = _safe_read_json(repo_root, META_DIAGNOSTICS_PAPER_ROUTE_COVERAGE_PATH) or {}
    validation = _safe_read_json(repo_root, META_DIAGNOSTICS_PAPER_VALIDATION_PATH) or {}
    route_summary = route_coverage.get("summary") if isinstance(route_coverage.get("summary"), Mapping) else {}
    validation_summary = validation.get("summary") if isinstance(validation.get("summary"), Mapping) else {}
    attention = route_coverage.get("attention") if isinstance(route_coverage.get("attention"), Mapping) else {}
    attention_samples = {}
    for key in (
        "route_saturation_queue",
        "thin_route_queue",
        "missing_mechanism_queue",
        "route_health_queue",
        "route_metadata_suggestion_queue",
    ):
        rows = attention.get(key) if isinstance(attention.get(key), list) else []
        attention_samples[key] = [dict(row) for row in rows[:limit] if isinstance(row, Mapping)]
    return {
        "route_coverage": {
            "source_path": META_DIAGNOSTICS_PAPER_ROUTE_COVERAGE_PATH,
            "generated_at": route_coverage.get("generated_at"),
            "summary": dict(route_summary),
            "attention_queue_counts": dict(route_summary.get("attention_queue_counts") or {}),
            "attention_samples": attention_samples,
        },
        "validation": {
            "source_path": META_DIAGNOSTICS_PAPER_VALIDATION_PATH,
            "generated_at": validation.get("generated_at"),
            "summary": dict(validation_summary),
            "queue_counts": dict(validation_summary.get("queue_counts") or {}),
            "fact_audit": dict(validation_summary.get("fact_audit") or {}),
        },
    }


def _meta_external_intake(repo_root: Path, *, limit: int) -> dict[str, Any]:
    sync_digest = _safe_read_json(repo_root, META_DIAGNOSTICS_ANNEX_SYNC_PATH) or {}
    distillation = _safe_read_json(repo_root, META_DIAGNOSTICS_ANNEX_DISTILLATION_PATH) or {}
    attention_slugs = [
        str(value)
        for value in (sync_digest.get("attention_slugs") or [])[:limit]
        if str(value).strip()
    ]
    rows_by_slug = {
        str(row.get("slug") or row.get("annex_slug") or ""): row
        for row in (sync_digest.get("rows") or [])
        if isinstance(row, Mapping)
    }
    top_axes = _meta_top_counter_rows(distillation.get("by_axis") or {}, limit=limit)
    return {
        "annex_sync": {
            "source_path": META_DIAGNOSTICS_ANNEX_SYNC_PATH,
            "generated_at": sync_digest.get("generated_at"),
            "annex_count": sync_digest.get("annex_count"),
            "bucket_counts": dict(sync_digest.get("bucket_counts") or {}),
            "attention_count": sync_digest.get("attention_count"),
            "attention_rows": [
                {
                    "slug": slug,
                    "bucket": (rows_by_slug.get(slug) or {}).get("bucket"),
                    "status": (rows_by_slug.get(slug) or {}).get("status"),
                    "stale_days": (rows_by_slug.get(slug) or {}).get("stale_days"),
                }
                for slug in attention_slugs
            ],
        },
        "annex_distillation": {
            "source_path": META_DIAGNOSTICS_ANNEX_DISTILLATION_PATH,
            "generated_at": distillation.get("generated_at"),
            "annex_count": distillation.get("annex_count"),
            "pattern_count": distillation.get("pattern_count"),
            "distillation_status_counts": dict(distillation.get("distillation_status_counts") or {}),
            "adoption_summary": dict(distillation.get("adoption_summary") or {}),
            "top_axes": top_axes,
        },
    }


def _meta_prompt_learning(repo_root: Path, *, limit: int) -> dict[str, Any]:
    ledger = _safe_read_json(repo_root, META_DIAGNOSTICS_PROMPT_LEDGER_PATH) or {}
    adoption = _safe_read_json(repo_root, META_DIAGNOSTICS_PROMPT_ADOPTION_PATH) or {}
    unlinked = _safe_read_json(repo_root, META_DIAGNOSTICS_PROMPT_UNLINKED_PATH) or {}
    candidates = adoption.get("candidates") if isinstance(adoption.get("candidates"), list) else []
    receipts = adoption.get("receipts") if isinstance(adoption.get("receipts"), list) else []
    return {
        "ledger": {
            "source_path": META_DIAGNOSTICS_PROMPT_LEDGER_PATH,
            "event_count": ledger.get("event_count"),
            "trace_count": ledger.get("trace_count"),
            "source_stream_count": ledger.get("source_stream_count"),
            "source_drift_count": ledger.get("source_drift_count"),
        },
        "adoption_posture": {
            "source_path": META_DIAGNOSTICS_PROMPT_ADOPTION_PATH,
            "candidate_count": adoption.get("candidate_count"),
            "receipt_count": adoption.get("receipt_count"),
            "state_counts": dict(adoption.get("state_counts") or {}),
            "candidate_current_state_counts": dict(adoption.get("candidate_current_state_counts") or {}),
            "candidates": [dict(row) for row in candidates[:limit] if isinstance(row, Mapping)],
            "receipts": [dict(row) for row in receipts[:limit] if isinstance(row, Mapping)],
        },
        "unlinked_traces": {
            "source_path": META_DIAGNOSTICS_PROMPT_UNLINKED_PATH,
            "count": unlinked.get("count") or len(_task_ledger_view_items(unlinked)),
        },
    }


def _meta_proof_constellation(repo_root: Path, *, limit: int) -> dict[str, Any]:
    graph = _safe_read_json(repo_root, META_DIAGNOSTICS_MICROCOSM_GRAPH_PATH) or {}
    gate = _safe_read_json(repo_root, META_DIAGNOSTICS_DISSEMINATION_GATE_PATH) or {}
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    edges = graph.get("edges") if isinstance(graph.get("edges"), list) else []
    return {
        "microcosm_composition": {
            "source_path": META_DIAGNOSTICS_MICROCOSM_GRAPH_PATH,
            "generated_at": graph.get("generated_at"),
            "graph_metrics": dict(graph.get("graph_metrics") or {}),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": [dict(row) for row in nodes[:limit] if isinstance(row, Mapping)],
            "edges": [dict(row) for row in edges[:limit] if isinstance(row, Mapping)],
            "omission_receipt": {
                "sample_limit": limit,
                "omitted_node_count": max(0, len(nodes) - limit),
                "omitted_edge_count": max(0, len(edges) - limit),
            },
        },
        "dissemination_gate": {
            "source_path": META_DIAGNOSTICS_DISSEMINATION_GATE_PATH,
            "generated_at": gate.get("generated_at"),
            "summary": dict(gate.get("summary") or {}),
            "blocking_violation_count": (
                (gate.get("summary") or {}).get("blocking_violation_count")
                if isinstance(gate.get("summary"), Mapping)
                else gate.get("blocking_violation_count")
            ),
        },
    }


def _meta_number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip().rstrip("%")
        try:
            return float(normalized)
        except ValueError:
            return default
    return default


def _meta_status_from_source(source_health: Mapping[str, Any], rel_path: str) -> str:
    row = source_health.get(rel_path)
    if not isinstance(row, Mapping):
        return "missing"
    if not row.get("available"):
        return "missing"
    freshness = row.get("freshness") if isinstance(row.get("freshness"), Mapping) else {}
    status = str(freshness.get("status") or "").lower()
    if "expired" in status or "error" in status:
        return "block"
    if "stale" in status or "missing" in status:
        return "warn"
    return "ok"


def _meta_pressure_status(count: Any, *, block_at: float | None = None) -> str:
    value = _meta_number(count)
    if block_at is not None and value >= block_at:
        return "block"
    if value > 0:
        return "warn"
    return "ok"


def _meta_node(
    *,
    node_id: str,
    label: str,
    kind: str,
    group: str,
    status: str = "neutral",
    magnitude: Any = None,
    confidence: float = 1.0,
    source_refs: Sequence[str] = (),
    action_refs: Sequence[str] = (),
    x: float,
    y: float,
    mark_kind: str = "hub",
    salience: str = "secondary",
) -> dict[str, Any]:
    return {
        "id": node_id,
        "label": label,
        "kind": kind,
        "group": group,
        "status": status,
        "magnitude": magnitude,
        "confidence": confidence,
        "source_refs": [str(ref) for ref in source_refs if str(ref).strip()],
        "action_refs": [str(ref) for ref in action_refs if str(ref).strip()],
        "layout": {"x": x, "y": y, "mark_kind": mark_kind, "salience": salience},
    }


def _meta_edge(
    *,
    source: str,
    target: str,
    relation: str,
    weight: Any = 1,
    status: str = "neutral",
    evidence_refs: Sequence[str] = (),
    drilldown_refs: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "id": f"{source}->{target}:{relation}",
        "source": source,
        "target": target,
        "relation": relation,
        "weight": _meta_number(weight, 1.0),
        "status": status,
        "evidence_refs": [str(ref) for ref in evidence_refs if str(ref).strip()],
        "drilldown_refs": [str(ref) for ref in drilldown_refs if str(ref).strip()],
    }


def _meta_diagnostics_visual_scene(
    *,
    generated_at: str,
    source_health: Mapping[str, Mapping[str, Any]],
    trust_strip: Mapping[str, Any],
    agent_behavior: Mapping[str, Any],
    command_efficiency: Mapping[str, Any],
    work_evidence: Mapping[str, Any],
    doctrine_health: Mapping[str, Any],
    external_intake: Mapping[str, Any],
    prompt_learning: Mapping[str, Any],
    proof_constellation: Mapping[str, Any],
    unavailable_sources: Sequence[str],
    limit: int,
) -> dict[str, Any]:
    capability = trust_strip.get("capability_lanes") if isinstance(trust_strip.get("capability_lanes"), Mapping) else {}
    facts = trust_strip.get("derived_facts") if isinstance(trust_strip.get("derived_facts"), Mapping) else {}
    frontend_nav = trust_strip.get("frontend_navigation") if isinstance(trust_strip.get("frontend_navigation"), Mapping) else {}
    nav_counts = frontend_nav.get("counts") if isinstance(frontend_nav.get("counts"), Mapping) else {}
    fact_summary = facts.get("summary") if isinstance(facts.get("summary"), Mapping) else {}

    scorecard = agent_behavior.get("scorecard") if isinstance(agent_behavior.get("scorecard"), Mapping) else {}
    latest_run = agent_behavior.get("latest_run") if isinstance(agent_behavior.get("latest_run"), Mapping) else {}
    trace_observatory = command_efficiency.get("trace_observatory") if isinstance(command_efficiency.get("trace_observatory"), Mapping) else {}
    process_monitoring = command_efficiency.get("process_monitoring") if isinstance(command_efficiency.get("process_monitoring"), Mapping) else {}
    trace_rows = trace_observatory.get("top_rows") if isinstance(trace_observatory.get("top_rows"), list) else []
    top_trace_row = trace_rows[0] if trace_rows and isinstance(trace_rows[0], Mapping) else {}
    trace_row_count = (
        trace_observatory.get("emitted_row_count")
        or trace_observatory.get("row_count")
        or len(trace_rows)
    )
    process_status_token = str(
        process_monitoring.get("bottleneck_status")
        or process_monitoring.get("process_summary_status")
        or ""
    ).lower()
    command_efficiency_status = (
        "warn"
        if trace_rows or "stale" in process_status_token or "missing" in process_status_token
        else ("ok" if command_efficiency.get("available") else "missing")
    )
    task_ledger = work_evidence.get("task_ledger") if isinstance(work_evidence.get("task_ledger"), Mapping) else {}
    task_counts = task_ledger.get("counts") if isinstance(task_ledger.get("counts"), Mapping) else {}
    dependency_blockers = work_evidence.get("dependency_blockers") if isinstance(work_evidence.get("dependency_blockers"), Mapping) else {}
    propagation = work_evidence.get("propagation") if isinstance(work_evidence.get("propagation"), Mapping) else {}
    active_receipts = work_evidence.get("active_receipts") if isinstance(work_evidence.get("active_receipts"), list) else []

    route_coverage = doctrine_health.get("route_coverage") if isinstance(doctrine_health.get("route_coverage"), Mapping) else {}
    route_summary = route_coverage.get("summary") if isinstance(route_coverage.get("summary"), Mapping) else {}
    route_attention = route_summary.get("route_health_attention_count") or route_summary.get("attention_count")
    validation = doctrine_health.get("validation") if isinstance(doctrine_health.get("validation"), Mapping) else {}
    validation_queue_counts = validation.get("queue_counts") if isinstance(validation.get("queue_counts"), Mapping) else {}

    annex_sync = external_intake.get("annex_sync") if isinstance(external_intake.get("annex_sync"), Mapping) else {}
    annex_buckets = annex_sync.get("bucket_counts") if isinstance(annex_sync.get("bucket_counts"), Mapping) else {}
    annex_attention = annex_sync.get("attention_count")
    annex_distillation = external_intake.get("annex_distillation") if isinstance(external_intake.get("annex_distillation"), Mapping) else {}

    prompt_ledger = prompt_learning.get("ledger") if isinstance(prompt_learning.get("ledger"), Mapping) else {}
    prompt_adoption = prompt_learning.get("adoption_posture") if isinstance(prompt_learning.get("adoption_posture"), Mapping) else {}
    microcosm = proof_constellation.get("microcosm_composition") if isinstance(proof_constellation.get("microcosm_composition"), Mapping) else {}
    gate = proof_constellation.get("dissemination_gate") if isinstance(proof_constellation.get("dissemination_gate"), Mapping) else {}
    gate_status = _meta_pressure_status(gate.get("blocking_violation_count"), block_at=1)

    source_nodes = [
        _meta_node(
            node_id="source_capability_lanes",
            label="Capability lanes",
            kind="source_projection",
            group="sources",
            status=_meta_status_from_source(source_health, META_DIAGNOSTICS_CAPABILITY_LANES_PATH),
            magnitude=len(capability.get("summary_counts") or {}),
            source_refs=[META_DIAGNOSTICS_CAPABILITY_LANES_PATH],
            x=8,
            y=14,
            mark_kind="port",
            salience="tertiary",
        ),
        _meta_node(
            node_id="source_fact_ledger",
            label="Fact ledger",
            kind="source_projection",
            group="sources",
            status=_meta_status_from_source(source_health, META_DIAGNOSTICS_FACT_LEDGER_PATH),
            magnitude=fact_summary.get("fact_count"),
            source_refs=[META_DIAGNOSTICS_FACT_LEDGER_PATH],
            x=8,
            y=30,
            mark_kind="port",
            salience="tertiary",
        ),
        _meta_node(
            node_id="source_navigation_graph",
            label="Navigation graph",
            kind="source_projection",
            group="sources",
            status=_meta_status_from_source(source_health, FRONTEND_NAV_GRAPH_PATH),
            magnitude=nav_counts.get("routes_declared") or nav_counts.get("pages"),
            source_refs=[FRONTEND_NAV_GRAPH_PATH],
            x=8,
            y=46,
            mark_kind="port",
            salience="tertiary",
        ),
        _meta_node(
            node_id="source_agent_telemetry",
            label="Agent telemetry",
            kind="source_projection",
            group="sources",
            status="ok" if agent_behavior.get("available") else "missing",
            magnitude=latest_run.get("records_emitted"),
            source_refs=[str(agent_behavior.get("source_dir") or AGENT_TELEMETRY_ROOT)],
            x=8,
            y=62,
            mark_kind="port",
            salience="tertiary",
        ),
        _meta_node(
            node_id="source_agent_trace",
            label="AgentTrace monitor",
            kind="source_projection",
            group="sources",
            status=_meta_status_from_source(source_health, META_DIAGNOSTICS_TRACE_OBSERVATORY_PATH),
            magnitude=trace_row_count,
            source_refs=[META_DIAGNOSTICS_TRACE_OBSERVATORY_PATH, META_DIAGNOSTICS_LATENCY_SPEEDBOARD_PATH],
            action_refs=["/api/world-model/meta-diagnostics/console"],
            x=8,
            y=70,
            mark_kind="port",
            salience="tertiary",
        ),
        _meta_node(
            node_id="source_task_ledger",
            label="Task Ledger",
            kind="source_projection",
            group="sources",
            status="ok",
            magnitude=task_counts.get("work_items") or task_counts.get("total"),
            source_refs=["state/task_ledger/ledger.json", "state/task_ledger/views"],
            action_refs=["/api/world-model/task-ledger/projection"],
            x=8,
            y=78,
            mark_kind="port",
            salience="tertiary",
        ),
        _meta_node(
            node_id="source_doctrine_routes",
            label="Doctrine routes",
            kind="source_projection",
            group="sources",
            status=_meta_status_from_source(source_health, META_DIAGNOSTICS_PAPER_ROUTE_COVERAGE_PATH),
            magnitude=route_summary.get("route_edge_count") or route_summary.get("module_count"),
            source_refs=[META_DIAGNOSTICS_PAPER_ROUTE_COVERAGE_PATH],
            x=8,
            y=94,
            mark_kind="port",
            salience="tertiary",
        ),
        _meta_node(
            node_id="source_annex_intake",
            label="Annex intake",
            kind="source_projection",
            group="sources",
            status=_meta_status_from_source(source_health, META_DIAGNOSTICS_ANNEX_SYNC_PATH),
            magnitude=annex_sync.get("annex_count"),
            source_refs=[META_DIAGNOSTICS_ANNEX_SYNC_PATH, META_DIAGNOSTICS_ANNEX_DISTILLATION_PATH],
            x=8,
            y=110,
            mark_kind="port",
            salience="tertiary",
        ),
        _meta_node(
            node_id="source_prompt_ledger",
            label="Prompt ledger",
            kind="source_projection",
            group="sources",
            status=_meta_status_from_source(source_health, META_DIAGNOSTICS_PROMPT_LEDGER_PATH),
            magnitude=prompt_ledger.get("trace_count"),
            source_refs=[META_DIAGNOSTICS_PROMPT_LEDGER_PATH],
            x=8,
            y=126,
            mark_kind="port",
            salience="tertiary",
        ),
        _meta_node(
            node_id="source_microcosm_graph",
            label="Proof graph",
            kind="source_projection",
            group="sources",
            status=_meta_status_from_source(source_health, META_DIAGNOSTICS_MICROCOSM_GRAPH_PATH),
            magnitude=microcosm.get("node_count"),
            source_refs=[META_DIAGNOSTICS_MICROCOSM_GRAPH_PATH],
            x=8,
            y=142,
            mark_kind="port",
            salience="tertiary",
        ),
    ]

    claim_nodes = [
        _meta_node(node_id="claim_trust", label="Trust", kind="claim", group="claims", status="ok", magnitude=nav_counts.get("routes_declared"), source_refs=[META_DIAGNOSTICS_CAPABILITY_LANES_PATH, META_DIAGNOSTICS_FACT_LEDGER_PATH], x=48, y=24, mark_kind="hub", salience="primary"),
        _meta_node(node_id="claim_behavior", label="Behavior", kind="claim", group="claims", status="ok" if agent_behavior.get("available") else "missing", magnitude=scorecard.get("sessions_total"), source_refs=[str(agent_behavior.get("source_dir") or AGENT_TELEMETRY_ROOT)], x=48, y=44, mark_kind="hub", salience="primary"),
        _meta_node(node_id="claim_command_efficiency", label="Command efficiency", kind="claim", group="claims", status=command_efficiency_status, magnitude=trace_row_count, source_refs=[META_DIAGNOSTICS_TRACE_OBSERVATORY_PATH, META_DIAGNOSTICS_LATENCY_SPEEDBOARD_PATH], action_refs=list(command_efficiency.get("recommended_next") or [])[:3], x=48, y=54, mark_kind="hub", salience="primary"),
        _meta_node(node_id="claim_work", label="Work", kind="claim", group="claims", status=_meta_pressure_status(dependency_blockers.get("count"), block_at=1), magnitude=len(active_receipts), source_refs=["state/task_ledger/views/active_wip.json"], action_refs=["/api/world-model/task-ledger/projection"], x=48, y=64, mark_kind="hub", salience="primary"),
        _meta_node(node_id="claim_doctrine", label="Doctrine", kind="claim", group="claims", status=_meta_pressure_status(route_attention), magnitude=route_attention, source_refs=[META_DIAGNOSTICS_PAPER_ROUTE_COVERAGE_PATH], x=48, y=84, mark_kind="hub", salience="primary"),
        _meta_node(node_id="claim_intake", label="Intake", kind="claim", group="claims", status=_meta_pressure_status(annex_attention), magnitude=annex_attention, source_refs=[META_DIAGNOSTICS_ANNEX_SYNC_PATH], x=48, y=104, mark_kind="hub", salience="primary"),
        _meta_node(node_id="claim_prompt_learning", label="Prompt", kind="claim", group="claims", status=_meta_pressure_status((prompt_learning.get("unlinked_traces") or {}).get("count") if isinstance(prompt_learning.get("unlinked_traces"), Mapping) else 0), magnitude=prompt_adoption.get("candidate_count") or prompt_ledger.get("trace_count"), source_refs=[META_DIAGNOSTICS_PROMPT_LEDGER_PATH], x=48, y=124, mark_kind="hub", salience="primary"),
        _meta_node(node_id="claim_proof", label="Proof", kind="claim", group="claims", status=gate_status, magnitude=microcosm.get("edge_count"), source_refs=[META_DIAGNOSTICS_MICROCOSM_GRAPH_PATH, META_DIAGNOSTICS_DISSEMINATION_GATE_PATH], x=48, y=144, mark_kind="hub", salience="primary"),
    ]

    evidence_nodes = [
        _meta_node(node_id="evidence_source_gaps", label="Source gaps", kind="evidence", group="evidence", status=_meta_pressure_status(len(unavailable_sources)), magnitude=len(unavailable_sources), source_refs=list(unavailable_sources), x=88, y=24, mark_kind="pressure", salience="secondary"),
        _meta_node(node_id="evidence_command_bottlenecks", label=str(top_trace_row.get("symptom_family") or "Command bottlenecks").replace("_", " "), kind="pressure", group="evidence", status=command_efficiency_status, magnitude=trace_row_count, source_refs=[META_DIAGNOSTICS_TRACE_OBSERVATORY_PATH, META_DIAGNOSTICS_PROCESS_SUMMARY_PATH], action_refs=list(command_efficiency.get("recommended_next") or [])[:3], x=88, y=40, mark_kind="pressure", salience="secondary"),
        _meta_node(node_id="evidence_route_pressure", label="Route pressure", kind="pressure", group="evidence", status=_meta_pressure_status(route_attention), magnitude=route_attention, source_refs=[META_DIAGNOSTICS_PAPER_ROUTE_COVERAGE_PATH], x=88, y=52, mark_kind="pressure", salience="secondary"),
        _meta_node(node_id="evidence_work_blockers", label="Work blockers", kind="pressure", group="evidence", status=_meta_pressure_status(dependency_blockers.get("count"), block_at=1), magnitude=dependency_blockers.get("count"), source_refs=["state/task_ledger/views/dependency_blocked.json"], action_refs=["/api/world-model/task-ledger/projection"], x=88, y=80, mark_kind="pressure", salience="secondary"),
        _meta_node(node_id="evidence_annex_pressure", label="Annex pressure", kind="pressure", group="evidence", status=_meta_pressure_status(annex_attention), magnitude=annex_attention, source_refs=[META_DIAGNOSTICS_ANNEX_SYNC_PATH], x=88, y=108, mark_kind="pressure", salience="secondary"),
        _meta_node(node_id="evidence_propagation", label="Propagation", kind="route", group="evidence", status=_meta_pressure_status(propagation.get("count")), magnitude=propagation.get("count"), source_refs=["state/task_ledger/views/propagation_needed.json"], x=88, y=130, mark_kind="pressure", salience="secondary"),
        _meta_node(node_id="evidence_gate", label="Proof gate", kind="gate", group="evidence", status=gate_status, magnitude=gate.get("blocking_violation_count"), source_refs=[META_DIAGNOSTICS_DISSEMINATION_GATE_PATH], x=88, y=150, mark_kind="pressure", salience="primary"),
    ]

    edges = [
        _meta_edge(source="source_capability_lanes", target="claim_trust", relation="supports", weight=len(capability.get("summary_counts") or {}), status="ok", evidence_refs=[META_DIAGNOSTICS_CAPABILITY_LANES_PATH]),
        _meta_edge(source="source_fact_ledger", target="claim_trust", relation="backs", weight=fact_summary.get("fact_count"), status="ok", evidence_refs=[META_DIAGNOSTICS_FACT_LEDGER_PATH]),
        _meta_edge(source="source_navigation_graph", target="claim_trust", relation="routes", weight=nav_counts.get("routes_declared") or nav_counts.get("pages"), status="ok", evidence_refs=[FRONTEND_NAV_GRAPH_PATH]),
        _meta_edge(source="source_agent_telemetry", target="claim_behavior", relation="feeds", weight=latest_run.get("records_emitted"), status="ok" if agent_behavior.get("available") else "missing"),
        _meta_edge(source="source_agent_trace", target="claim_command_efficiency", relation="monitors", weight=trace_row_count, status=command_efficiency_status, evidence_refs=[META_DIAGNOSTICS_TRACE_OBSERVATORY_PATH, META_DIAGNOSTICS_LATENCY_SPEEDBOARD_PATH]),
        _meta_edge(source="source_task_ledger", target="claim_work", relation="backs", weight=len(active_receipts), status=_meta_pressure_status(dependency_blockers.get("count"), block_at=1)),
        _meta_edge(source="source_doctrine_routes", target="claim_doctrine", relation="validates", weight=route_attention, status=_meta_pressure_status(route_attention)),
        _meta_edge(source="source_annex_intake", target="claim_intake", relation="pressurizes", weight=annex_attention, status=_meta_pressure_status(annex_attention)),
        _meta_edge(source="source_prompt_ledger", target="claim_prompt_learning", relation="teaches", weight=prompt_adoption.get("candidate_count") or prompt_ledger.get("trace_count"), status="ok"),
        _meta_edge(source="source_microcosm_graph", target="claim_proof", relation="proves", weight=microcosm.get("edge_count"), status=gate_status),
        _meta_edge(source="claim_trust", target="evidence_source_gaps", relation="exposes", weight=len(unavailable_sources), status=_meta_pressure_status(len(unavailable_sources))),
        _meta_edge(source="claim_command_efficiency", target="evidence_command_bottlenecks", relation="selects_next_speedup", weight=trace_row_count, status=command_efficiency_status, evidence_refs=[META_DIAGNOSTICS_TRACE_OBSERVATORY_PATH], drilldown_refs=list(command_efficiency.get("recommended_next") or [])[:3]),
        _meta_edge(source="claim_doctrine", target="evidence_route_pressure", relation="routes_to", weight=route_attention, status=_meta_pressure_status(route_attention)),
        _meta_edge(source="claim_work", target="evidence_work_blockers", relation="blocks_or_unlocks", weight=dependency_blockers.get("count"), status=_meta_pressure_status(dependency_blockers.get("count"), block_at=1)),
        _meta_edge(source="claim_intake", target="evidence_annex_pressure", relation="stales_or_drifts", weight=annex_attention, status=_meta_pressure_status(annex_attention)),
        _meta_edge(source="claim_work", target="evidence_propagation", relation="propagates", weight=propagation.get("count"), status=_meta_pressure_status(propagation.get("count"))),
        _meta_edge(source="claim_proof", target="evidence_gate", relation="gated_by", weight=gate.get("blocking_violation_count"), status=gate_status),
    ]

    attention_queue_counts = route_coverage.get("attention_queue_counts") if isinstance(route_coverage.get("attention_queue_counts"), Mapping) else {}
    matrix_cells: list[dict[str, Any]] = []
    matrix_sources = [
        ("route_attention", attention_queue_counts),
        ("validation", validation_queue_counts),
    ]
    max_cell = max(
        [_meta_number(value) for _, rows in matrix_sources for value in rows.values()] + [1.0]
    )
    for row_id, rows in matrix_sources:
        for column_id, value in rows.items():
            numeric = _meta_number(value)
            matrix_cells.append(
                {
                    "row": row_id,
                    "column": str(column_id),
                    "value": numeric,
                    "intensity": round(min(1.0, numeric / max_cell), 3),
                    "status": _meta_pressure_status(numeric),
                }
            )

    annex_bucket_rows = [
        {"id": str(bucket), "label": str(bucket).replace("_", " "), "count": _meta_number(count), "status": _meta_pressure_status(count) if bucket != "unchanged" and bucket != "aligned" else "ok"}
        for bucket, count in sorted(annex_buckets.items(), key=lambda item: _meta_number(item[1]), reverse=True)
    ]
    highlight_bucket = next((row["id"] for row in annex_bucket_rows if row["status"] != "ok"), annex_bucket_rows[0]["id"] if annex_bucket_rows else None)

    visual_grammar = {
        "mark_types": [
            {"id": "port", "applies_to_group": "sources", "shape": "circle", "purpose": "Compact signal jack: a source projection feeding into a claim. Magnitude is implied by adjacent edge weight; the port itself stays small so claims dominate."},
            {"id": "hub", "applies_to_group": "claims", "shape": "sized_circle", "purpose": "Claim core. Radius encodes magnitude; status colors the fill; the hub is the dominant identifying mark in the scene."},
            {"id": "pressure", "applies_to_group": "evidence", "shape": "radial_blob", "purpose": "Pressure field. Inner radius is filled; outer ring fades with intensity; rings stack for high-pressure or blocking nodes."},
            {"id": "ribbon", "applies_to_relation": "edge", "shape": "cubic_bezier", "purpose": "Causal/support relation. Thickness encodes weight; opacity encodes freshness; color encodes status."},
        ],
        "channel_encodings": [
            {"channel": "x_position", "encodes": "causal_stage", "domain": "source -> claim -> evidence", "rule": "Sources left, claims center, evidence right; movement across x is the proof direction."},
            {"channel": "y_position", "encodes": "subsystem_family", "domain": "trust, behavior, work, doctrine, intake, prompt, proof", "rule": "Each subsystem family owns a horizontal band; claim hubs and their evidence pressure share a row."},
            {"channel": "size", "encodes": "magnitude", "rule": "Hub radius and pressure-blob radius scale monotonically with node.magnitude (clamped to a readable range)."},
            {"channel": "stroke_width", "encodes": "edge_weight", "rule": "Ribbon thickness is proportional to relation weight; thicker ribbons are stronger causal pressure."},
            {"channel": "opacity", "encodes": "freshness", "rule": "Edges and pressure blobs fade as the underlying data ages; current state is full opacity."},
            {"channel": "color_tone", "encodes": "status", "domain": "ok (signal green), warn (amber), block (rose), neutral (white/30)", "rule": "Status colors carry meaning even when desaturated; pair with shape per accessibility_constraints."},
            {"channel": "salience", "encodes": "narrative_primacy", "rule": "primary marks dominate the canvas; secondary marks support; tertiary marks are visual context."},
        ],
        "salience_order": [
            {"id": "claim_hubs", "rank": 1, "rule": "Claims are the dominant marks — the eye lands here first."},
            {"id": "evidence_pressure", "rank": 2, "rule": "Pressure regions are read after claims to gauge stress."},
            {"id": "ribbons", "rank": 3, "rule": "Ribbons connect claims to evidence and to sources, supporting causality."},
            {"id": "source_ports", "rank": 4, "rule": "Sources are context, not centerpieces."},
            {"id": "lane_headers", "rank": 5, "rule": "Lane labels orient first-time readers without stealing weight."},
            {"id": "secondary_strips", "rank": 6, "rule": "Timeline / heatmap / distribution live below the canvas as thin strips."},
            {"id": "inspector", "rank": 7, "rule": "Inspector surfaces only on selection; not a permanent column."},
        ],
        "story_beats": [
            {"id": "1_status_at_a_glance", "answers": "Can I trust the system right now?", "marks": ["claim_hubs"], "channels": ["color_tone", "size"]},
            {"id": "2_where_is_pressure", "answers": "Where is pressure accumulating?", "marks": ["evidence_pressure"], "channels": ["size", "color_tone"]},
            {"id": "3_what_supports_what", "answers": "What evidence supports each claim?", "marks": ["ribbons"], "channels": ["stroke_width", "opacity"]},
            {"id": "4_what_is_stale_or_missing", "answers": "What is stale, blocked, or missing?", "marks": ["evidence_pressure", "ribbons"], "channels": ["opacity", "color_tone"]},
            {"id": "5_what_path_explains_it", "answers": "What path repairs or explains the pressure?", "marks": ["ribbons", "source_ports"], "channels": ["stroke_width"]},
        ],
        "label_priority": {
            "always_visible": ["claim_hubs", "lane_headers"],
            "hover_or_select_only": ["source_ports", "evidence_pressure", "ribbons"],
            "elide_when_overflowing": ["source_ports"],
            "min_primary_label_px_effective": 11,
            "min_secondary_label_px_effective": 9,
            "no_sub_9_primary_identification": True,
        },
        "inspector_payloads": {
            "default_posture": "closed",
            "open_on": ["node_click", "node_keyboard_enter"],
            "claim_hub": ["status", "magnitude", "source_refs", "action_refs", "related_evidence"],
            "evidence_pressure": ["status", "magnitude", "supporting_claim", "drilldown_refs"],
            "source_port": ["status", "freshness", "source_refs"],
        },
        "failure_state_contract": {
            "missing_visual_grammar": "render must refuse to ship a primitive-only scene; emit an explicit failure receipt naming visual_grammar absence",
            "degraded_sources": "missing source ports fade and a 'source gap' pressure region surfaces on the right",
            "empty_scene": "render a single 'no proof topology available' message, not an empty grid of panels",
        },
    }

    pressure_state = "block" if gate_status == "block" or _meta_pressure_status(dependency_blockers.get("count"), block_at=1) == "block" else (
        "warn" if (route_attention or 0) or (annex_attention or 0) or len(unavailable_sources) or command_efficiency_status == "warn" else "ok"
    )

    visual_instrument = {
        "thesis": "A living evidence circuit: source ports feed claim hubs, ribbons carry magnitude and freshness, and pressure fields gather on the right where receipts, blockers, route stress, and gate state accumulate.",
        "dominant_question": "Can I trust the system right now, where is pressure accumulating, and which sources need attention?",
        "dominant_canvas_role": "evidence_circuit",
        "regions": [
            {"id": "left_source_column", "role": "compact source ports", "weight": "tertiary", "posture": "labels on hover/select"},
            {"id": "center_claim_field", "role": "claim hubs sized by magnitude", "weight": "primary", "posture": "labels always visible"},
            {"id": "right_pressure_field", "role": "evidence pressure regions", "weight": "secondary", "posture": "rings stack for blocking pressure"},
            {"id": "bottom_signal_strip", "role": "behavior timeline + annex distribution as thin ribbons", "weight": "tertiary", "posture": "demoted, not equal-weight panels"},
            {"id": "inspector_overlay", "role": "details-on-demand drawer", "weight": "hidden_until_selection", "posture": "slides in on node click only"},
        ],
        "forbidden_patterns": [
            "diagram_theatre_empty_rectangles_as_nodes",
            "wide_thin_topology_band_with_unused_canvas",
            "equal_weight_secondary_panels_under_the_canvas",
            "permanent_inspector_column_with_no_selection",
            "sub_9px_primary_labels",
            "decorative_grid_pattern_not_encoding_scale_or_lanes",
            "panel_count_as_acceptance_gate",
        ],
        "pressure_state": pressure_state,
    }

    return {
        "schema": "meta_diagnostics_visual_scene_v0",
        "generated_at": generated_at,
        "authority": {
            "source_packet": "meta_diagnostics_console_projection_v1",
            "visual_boundary": "visual_model_over_existing_read_model_not_new_authority",
            "failed_predecessor": "six_panel_card_mosaic_v0",
            "failed_intermediate": "visual_primitive_compliance_without_visual_intelligence",
            "failed_composition_root": "custom_hero_diagram_instead_of_overlay_on_atlas_substrate",
            "owning_standard": "codex/standards/std_station_aesthetic.json::aesthetic_primitives_v1.primitives.P14_visual_instrument_over_diagram_theatre",
            "composition_root_standard": "codex/standards/std_station_aesthetic.json::aesthetic_primitives_v1.primitives.P15_observability_overlays_on_atlas_not_hero_diagrams",
            "migration_target": {
                "surface_class": "observability_overlay_on_atlas_substrate",
                "atlas_anchors": [
                    "system/server/ui/src/components/system-atlas/SystemAtlasGraph.tsx",
                    "system/server/ui/src/components/system-atlas/SystemAtlasKindScene.tsx",
                    "system/server/ui/src/pages/RootNavigator.tsx",
                ],
                "atlas_route": "/station?node=metaDiagnostics",
                "carrying_workitem": "cap_quick_meta_diagnostics_custom_hero_diagram_ins_47f28357c35d",
            },
            "frontend_composition_status": "interim_pre_atlas_overlay_migration",
        },
        "visual_grammar": visual_grammar,
        "visual_instrument": visual_instrument,
        "scene_manifest": {
            "primary_scene": "proof_topology",
            "secondary_scenes": [
                "behavior_timeline",
                "command_efficiency_strip",
                "work_flow",
                "doctrine_heatmap",
                "annex_pressure",
                "source_health",
            ],
            "operator_question": "What is the system claiming, what supports it, what is stale or blocked, and where does evidence flow next?",
            "dominant_visual": "source systems -> claims -> evidence pressure topology",
        },
        "nodes": source_nodes + claim_nodes + evidence_nodes,
        "edges": edges,
        "lanes": [
            {"id": "sources", "label": "Source systems", "semantic_role": "source_artifacts", "ordered_node_ids": [node["id"] for node in source_nodes]},
            {"id": "claims", "label": "Claims", "semantic_role": "system_claims", "ordered_node_ids": [node["id"] for node in claim_nodes]},
            {"id": "evidence", "label": "Evidence / pressure", "semantic_role": "receipts_blockers_routes", "ordered_node_ids": [node["id"] for node in evidence_nodes]},
        ],
        "series": [
            {
                "id": "behavior_timeline",
                "label": "Agent behavior timeline",
                "x_field": "stage",
                "y_field": "value",
                "values": [
                    {"x": "sessions", "label": "Sessions", "value": _meta_number(scorecard.get("sessions_total")), "status": "neutral"},
                    {"x": "kernel", "label": "Kernel use", "value": _meta_number(scorecard.get("kernel_invocations")), "status": "ok"},
                    {"x": "shell", "label": "Shell nav", "value": _meta_number(scorecard.get("shell_navigation_commands")), "status": _meta_pressure_status(scorecard.get("shell_navigation_commands"))},
                    {"x": "trace", "label": "Trace rows", "value": _meta_number(trace_row_count), "status": command_efficiency_status},
                    {"x": "repo", "label": "Repo native", "value": _meta_number(scorecard.get("repo_native_commands")), "status": "ok"},
                    {"x": "records", "label": "Records emitted", "value": _meta_number(latest_run.get("records_emitted")), "status": "neutral"},
                ],
            }
        ],
        "matrices": [
            {
                "id": "doctrine_health_heatmap",
                "label": "Doctrine and validation pressure",
                "rows": ["route_attention", "validation"],
                "columns": sorted({cell["column"] for cell in matrix_cells}),
                "cells": matrix_cells[: max(1, limit * 2)],
                "legend": {"ok": "clear or expected", "warn": "attention queue", "block": "blocking pressure"},
            }
        ],
        "distributions": [
            {
                "id": "annex_pressure_distribution",
                "label": "Annex pressure distribution",
                "buckets": annex_bucket_rows[:limit],
                "highlight_bucket": highlight_bucket,
                "total": _meta_number(annex_sync.get("annex_count")) or sum(row["count"] for row in annex_bucket_rows),
                "source_ref": META_DIAGNOSTICS_ANNEX_SYNC_PATH,
            },
            {
                "id": "capability_carrier_distribution",
                "label": "Capability carrier availability",
                "buckets": [
                    {"id": str(key), "label": str(key).replace("_", " "), "count": _meta_number(value), "status": "ok" if "enabled" in str(key) or "routeable" in str(key) else "warn"}
                    for key, value in (capability.get("summary_counts") or {}).items()
                ][:limit],
                "highlight_bucket": None,
                "total": sum(_meta_number(value) for value in (capability.get("summary_counts") or {}).values()),
                "source_ref": META_DIAGNOSTICS_CAPABILITY_LANES_PATH,
            },
        ],
        "annotations": [
            {
                "id": "visual_contract_correction",
                "claim": "Metrics are labels on visual structure; the primary proof is the topology, timeline, heatmap, and distribution.",
                "severity": "required",
                "target_id": "claim_trust",
                "evidence_ref": "cap_quick_meta_diagnostics_v0_card_mosaic_failed_v_21a069281c9d",
            },
            {
                "id": "source_gap_pressure",
                "claim": f"{len(unavailable_sources)} backing source projection(s) unavailable in the read model.",
                "severity": "warn" if unavailable_sources else "ok",
                "target_id": "evidence_source_gaps",
                "evidence_ref": "source_health",
            },
            {
                "id": "composition_root_correction",
                "claim": "Meta Diagnostics is an observability LAYER over the atlas substrate, not a custom hero infographic. The frontend will migrate to atlas overlay modes (trust / route-pressure / work-evidence / annex / proof / freshness) over SystemAtlasGraph; the current console is an interim layered list pending that migration. Hero diagrams are exceptional, not default.",
                "severity": "required",
                "target_id": None,
                "evidence_ref": "cap_quick_meta_diagnostics_custom_hero_diagram_ins_47f28357c35d",
            },
        ],
        "interaction_contract": {
            "overview": "Render the evidence circuit first; secondary strips below; inspector opens on selection only.",
            "zoom_filter_dimensions": ["group", "status", "kind", "source_ref"],
            "details_on_demand_refs": ["source_refs", "action_refs", "evidence_refs", "drilldown_refs"],
            "anti_goals": [
                "title-number cards as primary layout",
                "equal-weight six-panel mosaic",
                "diagram theatre — primitives without grammar",
                "permanent inspector column",
                "raw JSON before selected evidence",
            ],
        },
    }


def _meta_diagnostics_atlas_overlay(
    *,
    visual_scene: Mapping[str, Any],
    unavailable_sources: Sequence[str],
    source_health: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """
    [ROLE]
    - Teleology: Project the Meta Diagnostics read model onto the System
      Atlas substrate as overlay semantics so the frontend can mount
      SystemAtlasGraph at /station/meta-diagnostics with diagnostic layers
      active, instead of building a hero infographic. Lessons: P15
      observability_overlays_on_atlas_not_hero_diagrams.
    - Mechanism: Read the visual_scene claim hubs as the canonical
      observability layers, attach metric/channel/legend policy per layer,
      and expose source gaps + selected-node inspector payloads.
    """
    nodes = list(visual_scene.get("nodes") or [])
    edges = list(visual_scene.get("edges") or [])
    claims = [n for n in nodes if isinstance(n, Mapping) and n.get("group") == "claims"]
    evidence_by_claim: dict[str, list[Mapping[str, Any]]] = {}
    sources_by_claim: dict[str, list[Mapping[str, Any]]] = {}
    claim_ids = {str(c.get("id")) for c in claims}
    source_ids = {str(n.get("id")) for n in nodes if isinstance(n, Mapping) and n.get("group") == "sources"}
    evidence_ids = {str(n.get("id")) for n in nodes if isinstance(n, Mapping) and n.get("group") == "evidence"}
    for edge in edges:
        if not isinstance(edge, Mapping):
            continue
        src = str(edge.get("source"))
        tgt = str(edge.get("target"))
        if src in source_ids and tgt in claim_ids:
            sources_by_claim.setdefault(tgt, []).append(edge)
        if src in claim_ids and tgt in evidence_ids:
            evidence_by_claim.setdefault(src, []).append(edge)

    # Six canonical diagnostic layers; metric_field names the claim hub each
    # layer reads its top-line pressure from. atlas_kind_field/atlas_kinds
    # bind the layer to actual SystemAtlasGraph kinds so the canvas (not just
    # the rail) reflects the active layer. Lessons:
    # cap_quick_meta_diagnostics_custom_hero_diagram_ins_47f28357c35d
    # acceptance gate "atlas overlay chrome without substrate binding"
    # (2026-05-21 note wie_20260521T015106Z_8cf229f5).
    layer_specs = [
        {
            "id": "trust",
            "label": "Trust",
            "claim_id": "claim_trust",
            "metric_field": "magnitude",
            "channel_policy": {"primary_channel": "node_halo", "secondary_channel": "edge_emphasis"},
            "legend": {"ok": "trust intact", "warn": "trust degraded", "block": "trust broken"},
            "atlas_kind_field": "Standard",
            "atlas_kinds": ["Standard", "Principle"],
            "binding_rationale": "Trust is governed by standards and principles; focusing the atlas on the Standard kind field surfaces the authority entities Meta Diagnostics' trust claim depends on.",
        },
        {
            "id": "route_pressure",
            "label": "Route pressure",
            "claim_id": "claim_doctrine",
            "metric_field": "magnitude",
            "channel_policy": {"primary_channel": "cluster_heat", "secondary_channel": "node_badge"},
            "legend": {"ok": "routes healthy", "warn": "attention queue", "block": "route gaps blocking"},
            "atlas_kind_field": "PaperModule",
            "atlas_kinds": ["PaperModule"],
            "binding_rationale": "Route health and route attention are properties of paper modules and their relations; focusing the atlas on the PaperModule kind field surfaces the entities the route_pressure metric reads.",
        },
        {
            "id": "work_evidence",
            "label": "Work evidence",
            "claim_id": "claim_work",
            "metric_field": "magnitude",
            "channel_policy": {"primary_channel": "node_halo", "secondary_channel": "node_badge"},
            "legend": {"ok": "no dependency blockers", "warn": "blockers present", "block": "blocking dependency chain"},
            "atlas_kind_field": "Mechanism",
            "atlas_kinds": ["Mechanism", "Validator"],
            "binding_rationale": "Work evidence is mechanism execution + validator state; focusing on Mechanism surfaces the carriers Meta Diagnostics' work claim reads pressure from.",
        },
        {
            "id": "command_efficiency",
            "label": "Command efficiency",
            "claim_id": "claim_command_efficiency",
            "metric_field": "magnitude",
            "channel_policy": {"primary_channel": "node_badge", "secondary_channel": "edge_emphasis"},
            "legend": {"ok": "command path efficient", "warn": "trace pressure", "block": "speedup lane blocking"},
            "atlas_kind_field": "Mechanism",
            "atlas_kinds": ["Mechanism", "Validator"],
            "binding_rationale": "Command efficiency is carried by the AgentTrace monitor, process bottleneck classifier, and speedboard validators; focusing on Mechanism surfaces the runtime owners that can change command cost.",
        },
        {
            "id": "annex_pressure",
            "label": "Annex pressure",
            "claim_id": "claim_intake",
            "metric_field": "magnitude",
            "channel_policy": {"primary_channel": "node_glow", "secondary_channel": "edge_dim"},
            "legend": {"ok": "intake aligned", "warn": "intake drift", "block": "intake adoption stalled"},
            "atlas_kind_field": "ArtifactKind",
            "atlas_kinds": ["ArtifactKind"],
            "binding_rationale": "Annex intake adoption surfaces as artifact kinds and their drift/distillation state; focusing on ArtifactKind surfaces the relevant entities.",
        },
        {
            "id": "proof",
            "label": "Proof",
            "claim_id": "claim_proof",
            "metric_field": "magnitude",
            "channel_policy": {"primary_channel": "node_halo", "secondary_channel": "cluster_heat"},
            "legend": {"ok": "proof gate clear", "warn": "proof gate stressed", "block": "proof gate blocking"},
            "atlas_kind_field": "Validator",
            "atlas_kinds": ["Validator", "Concept"],
            "binding_rationale": "Proof state is carried by validators (proof gates) and the concepts they verify; focusing on Validator surfaces the gate posture.",
        },
        {
            "id": "freshness",
            "label": "Freshness",
            "claim_id": None,
            "metric_field": "freshness",
            "channel_policy": {"primary_channel": "node_opacity", "secondary_channel": "node_glow"},
            "legend": {"ok": "fresh", "warn": "stale", "block": "expired"},
            "atlas_kind_field": "PaperModule",
            "atlas_kinds": ["PaperModule", "Standard"],
            "binding_rationale": "Source freshness is most legible at the paper module + standard level where source mtime and projection coupling are tracked.",
        },
    ]

    claims_index = {str(c.get("id")): c for c in claims}

    layers: list[dict[str, Any]] = []
    for spec in layer_specs:
        cid = spec["claim_id"]
        if cid and cid in claims_index:
            backing = claims_index[cid]
            status = backing.get("status") or "neutral"
            magnitude = backing.get("magnitude")
            backing_label = backing.get("label")
        elif cid is None:
            status = "warn" if len(unavailable_sources) else "ok"
            magnitude = len(unavailable_sources)
            backing_label = "Source freshness"
        else:
            status = "missing"
            magnitude = None
            backing_label = None
        layers.append(
            {
                "id": spec["id"],
                "label": spec["label"],
                "metric_field": spec["metric_field"],
                "default_visible": spec["id"] == "trust",
                "channel_policy": spec["channel_policy"],
                "legend": spec["legend"],
                "backing_claim_id": cid,
                "backing_label": backing_label,
                "status": status,
                "magnitude": magnitude,
                "supports_count": len(sources_by_claim.get(str(cid), [])) if cid else 0,
                "pressure_count": len(evidence_by_claim.get(str(cid), [])) if cid else 0,
                "atlas_kind_field": spec["atlas_kind_field"],
                "atlas_kinds": list(spec["atlas_kinds"]),
                "binding_rationale": spec["binding_rationale"],
            }
        )

    # Gaps: substrate the diagnostic claims expect to find but did not.
    gaps: list[dict[str, Any]] = []
    for path in unavailable_sources:
        row = source_health.get(path) if isinstance(source_health, Mapping) else None
        gaps.append(
            {
                "expected_substrate_ref": str(path),
                "reason": "source_projection_unavailable",
                "severity": "warn",
                "freshness_status": (
                    (row.get("freshness") or {}).get("status")
                    if isinstance(row, Mapping) and isinstance(row.get("freshness"), Mapping)
                    else "missing"
                ),
            }
        )

    # Default layer follows pressure: a blocking layer wins over a warning
    # layer; a warning layer with higher magnitude wins over a lower one;
    # otherwise fall back to trust. This satisfies the acceptance gate that
    # the canvas should reflect the highest-pressure diagnostic on rest.
    severity_rank = {"block": 3, "warn": 2, "neutral": 1, "ok": 0}

    def _layer_pressure_key(layer: Mapping[str, Any]) -> tuple[int, float]:
        return (
            severity_rank.get(str(layer.get("status") or "neutral").lower(), 0),
            _meta_number(layer.get("magnitude")),
        )

    pressured_layers = [
        layer for layer in layers
        if str(layer.get("status") or "").lower() in ("block", "warn")
    ]
    if pressured_layers:
        default_layer_id = max(pressured_layers, key=_layer_pressure_key)["id"]
    else:
        default_layer_id = "trust"

    # Entity decorations and kind/cluster overlays are populated by the
    # frontend overlay adapter once it knows which atlas entities are on
    # screen; the backend declares the contract here and leaves the
    # per-entity application to the renderer. This keeps the backend free of
    # render-specific viewBox/radius/coord state.
    return {
        "schema": "meta_diagnostics_atlas_overlay_v0",
        "target_surface": "system_atlas",
        "target_route_preset": "/station/meta-diagnostics",
        "default_layer": default_layer_id,
        "layers": layers,
        "kind_overlays": {
            "channel_policy_note": "Frontend overlay adapter maps active layer status onto atlas kinds via existing display-model channels (halo / badge / glow / edge emphasis / cluster heat / opacity).",
        },
        "cluster_overlays": {
            "channel_policy_note": "Atlas cluster nodes receive cluster_heat from the active layer's pressure.",
        },
        "entity_decorations": [],
        "gaps": gaps,
        "inspector_payloads": {
            "default_posture": "closed",
            "open_on": ["atlas_node_click", "atlas_node_keyboard_enter"],
            "atlas_entity": [
                "diagnostic_layer_active",
                "layer_status",
                "layer_magnitude",
                "claim_hub_supports_count",
                "claim_hub_pressure_count",
                "source_gaps_intersecting_entity",
                "drill_targets",
            ],
        },
        "lod_policy": {
            "max_decorated_entities_for_default_view": 64,
            "label_threshold_zoom_pct": 65,
            "decoration_intensity_floor": 0.35,
        },
        "fallback_drawer_ref": {
            "purpose": "The interim claim-pressure table from the prior wave is preserved as a collapsible details drawer beneath the atlas, not as the primary above-the-fold surface.",
            "drawer_status": "collapsed_by_default",
        },
        "owning_standard": "codex/standards/std_station_aesthetic.json::aesthetic_primitives_v1.primitives.P15_observability_overlays_on_atlas_not_hero_diagrams",
        "carrying_workitem": "cap_quick_meta_diagnostics_custom_hero_diagram_ins_47f28357c35d",
    }


def load_meta_diagnostics_console_projection(
    repo_root: Path,
    *,
    limit: int = 8,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Compose the backend data a System Proof / Meta Diagnostics
      console needs in one bounded read-only payload: capability trust, agent
      behavior, work receipts, route health, prompt-learning posture, annex
      intake, and proof-constellation samples.
    - Mechanism: Read existing generated JSON projections only. This function
      does not run kernel commands, tests, browsers, builders, or git.
    - Guarantee: Missing source files degrade through source_health and empty
      sections rather than failing the endpoint.
    """
    bounded_limit = max(1, min(int(limit), 40))
    trust_strip = _meta_capability_trust(repo_root, limit=bounded_limit)
    agent_behavior = _meta_agent_telemetry(repo_root, limit=bounded_limit)
    command_efficiency = _meta_command_efficiency(repo_root, limit=bounded_limit)
    work_evidence = _meta_work_evidence(repo_root, limit=bounded_limit)
    doctrine_health = _meta_doctrine_health(repo_root, limit=bounded_limit)
    external_intake = _meta_external_intake(repo_root, limit=bounded_limit)
    prompt_learning = _meta_prompt_learning(repo_root, limit=bounded_limit)
    proof_constellation = _meta_proof_constellation(repo_root, limit=bounded_limit)

    source_payloads = {
        META_DIAGNOSTICS_CAPABILITY_LANES_PATH: _safe_read_json(repo_root, META_DIAGNOSTICS_CAPABILITY_LANES_PATH),
        META_DIAGNOSTICS_FACT_LEDGER_PATH: _safe_read_json(repo_root, META_DIAGNOSTICS_FACT_LEDGER_PATH),
        FRONTEND_NAV_GRAPH_PATH: _safe_read_json(repo_root, FRONTEND_NAV_GRAPH_PATH),
        "state/task_ledger/views/workitem_cartography.json": _safe_read_json(repo_root, "state/task_ledger/views/workitem_cartography.json"),
        "state/task_ledger/views/cap_cartography.json": _safe_read_json(repo_root, "state/task_ledger/views/cap_cartography.json"),
        "state/task_ledger/views/mission_operating_picture.json": _safe_read_json(repo_root, "state/task_ledger/views/mission_operating_picture.json"),
        META_DIAGNOSTICS_PAPER_ROUTE_COVERAGE_PATH: _safe_read_json(repo_root, META_DIAGNOSTICS_PAPER_ROUTE_COVERAGE_PATH),
        META_DIAGNOSTICS_PAPER_VALIDATION_PATH: _safe_read_json(repo_root, META_DIAGNOSTICS_PAPER_VALIDATION_PATH),
        META_DIAGNOSTICS_ANNEX_SYNC_PATH: _safe_read_json(repo_root, META_DIAGNOSTICS_ANNEX_SYNC_PATH),
        META_DIAGNOSTICS_ANNEX_DISTILLATION_PATH: _safe_read_json(repo_root, META_DIAGNOSTICS_ANNEX_DISTILLATION_PATH),
        META_DIAGNOSTICS_PROMPT_LEDGER_PATH: _safe_read_json(repo_root, META_DIAGNOSTICS_PROMPT_LEDGER_PATH),
        META_DIAGNOSTICS_PROMPT_ADOPTION_PATH: _safe_read_json(repo_root, META_DIAGNOSTICS_PROMPT_ADOPTION_PATH),
        META_DIAGNOSTICS_MICROCOSM_GRAPH_PATH: _safe_read_json(repo_root, META_DIAGNOSTICS_MICROCOSM_GRAPH_PATH),
        META_DIAGNOSTICS_DISSEMINATION_GATE_PATH: _safe_read_json(repo_root, META_DIAGNOSTICS_DISSEMINATION_GATE_PATH),
        META_DIAGNOSTICS_TRACE_OBSERVATORY_PATH: _safe_read_json(repo_root, META_DIAGNOSTICS_TRACE_OBSERVATORY_PATH),
        META_DIAGNOSTICS_LATENCY_SPEEDBOARD_PATH: _safe_read_json(repo_root, META_DIAGNOSTICS_LATENCY_SPEEDBOARD_PATH),
        META_DIAGNOSTICS_PROCESS_SUMMARY_PATH: _safe_read_json(repo_root, META_DIAGNOSTICS_PROCESS_SUMMARY_PATH),
    }
    source_health = {
        rel_path: _meta_source_health(repo_root, rel_path, payload=payload)
        for rel_path, payload in source_payloads.items()
    }
    if agent_behavior.get("available"):
        rel_dir = str(agent_behavior.get("source_dir") or "")
        source_health[rel_dir] = {
            "source_path": rel_dir,
            "available": True,
            "generated_at": (agent_behavior.get("latest_run") or {}).get("generated_at"),
            "freshness": (agent_behavior.get("latest_run") or {}).get("freshness"),
            "record_count": (agent_behavior.get("latest_run") or {}).get("records_emitted"),
        }

    unavailable_sources = [
        path for path, row in source_health.items() if not row.get("available")
    ]
    panels = [
        {
            "panel_id": "trust_strip",
            "title": "Capability and Projection Trust",
            "data_ref": "trust_strip",
            "recommended_visual": "compact_status_strip",
            "why_useful": "Shows what the frontend can safely claim before showing detailed diagnostics.",
            "source_refs": [
                META_DIAGNOSTICS_CAPABILITY_LANES_PATH,
                META_DIAGNOSTICS_FACT_LEDGER_PATH,
                FRONTEND_NAV_GRAPH_PATH,
            ],
        },
        {
            "panel_id": "agent_behavior",
            "title": "Agent Behavior",
            "data_ref": "agent_behavior",
            "recommended_visual": "timeline_plus_ranked_bars",
            "why_useful": "Shows substrate adoption, shell fallback, hot files, and actor split.",
            "source_refs": [str(agent_behavior.get("source_dir") or AGENT_TELEMETRY_ROOT)],
        },
        {
            "panel_id": "command_efficiency",
            "title": "Command Efficiency",
            "data_ref": "command_efficiency",
            "recommended_visual": "agenttrace_speed_strip",
            "why_useful": "Connects AgentTrace friction, process bottleneck freshness, and latency speedboard evidence without opening raw session bodies.",
            "source_refs": [
                META_DIAGNOSTICS_TRACE_OBSERVATORY_PATH,
                META_DIAGNOSTICS_LATENCY_SPEEDBOARD_PATH,
                META_DIAGNOSTICS_PROCESS_SUMMARY_PATH,
            ],
        },
        {
            "panel_id": "work_evidence",
            "title": "Work Evidence and Blockers",
            "data_ref": "work_evidence",
            "recommended_visual": "receipt_cards_with_dependency_strip",
            "why_useful": "Connects active work, receipts, blockers, route provenance, and propagation pressure.",
            "source_refs": [
                "state/task_ledger/ledger.json",
                "state/task_ledger/views/workitem_cartography.json",
                "state/task_ledger/views/cap_cartography.json",
                "state/task_ledger/views/mission_operating_picture.json",
            ],
        },
        {
            "panel_id": "doctrine_health",
            "title": "Doctrine Route Health",
            "data_ref": "doctrine_health",
            "recommended_visual": "coverage_heatmap",
            "why_useful": "Surfaces paper-module routing pressure without dumping the paper library.",
            "source_refs": [
                META_DIAGNOSTICS_PAPER_ROUTE_COVERAGE_PATH,
                META_DIAGNOSTICS_PAPER_VALIDATION_PATH,
            ],
        },
        {
            "panel_id": "external_intake",
            "title": "Annex Intake Pressure",
            "data_ref": "external_intake",
            "recommended_visual": "bucket_bars",
            "why_useful": "Shows external prior-art intake and adoption landing rate as pressure, not a raw repo list.",
            "source_refs": [
                META_DIAGNOSTICS_ANNEX_SYNC_PATH,
                META_DIAGNOSTICS_ANNEX_DISTILLATION_PATH,
            ],
        },
        {
            "panel_id": "proof_constellation",
            "title": "Proof Constellation",
            "data_ref": "proof_constellation",
            "recommended_visual": "small_evidence_graph",
            "why_useful": "Gives a demo-friendly graph of system proof cells and validation evidence.",
            "source_refs": [
                META_DIAGNOSTICS_MICROCOSM_GRAPH_PATH,
                META_DIAGNOSTICS_DISSEMINATION_GATE_PATH,
            ],
        },
    ]

    generated_at = datetime.now(timezone.utc).isoformat()
    visual_scene = _meta_diagnostics_visual_scene(
        generated_at=generated_at,
        source_health=source_health,
        trust_strip=trust_strip,
        agent_behavior=agent_behavior,
        command_efficiency=command_efficiency,
        work_evidence=work_evidence,
        doctrine_health=doctrine_health,
        external_intake=external_intake,
        prompt_learning=prompt_learning,
        proof_constellation=proof_constellation,
        unavailable_sources=unavailable_sources,
        limit=bounded_limit,
    )
    atlas_overlay = _meta_diagnostics_atlas_overlay(
        visual_scene=visual_scene,
        unavailable_sources=unavailable_sources,
        source_health=source_health,
    )

    return {
        "schema": "meta_diagnostics_console_projection_v1",
        "generated_at": generated_at,
        "available": True,
        "authority": {
            "endpoint": META_DIAGNOSTICS_ENDPOINT,
            "station_consumer": "/station/meta-diagnostics",
            "boundary": "read_only_projection_existing_artifacts_are_authority",
            "mutation_boundary": "read_only_existing_writers_remain_authority",
            "source_authority_policy": "This packet is a frontend read model over generated JSON artifacts; it does not create new source truth.",
        },
        "summary": {
            "panel_count": len(panels),
            "source_count": len(source_health),
            "unavailable_source_count": len(unavailable_sources),
            "agent_telemetry_available": bool(agent_behavior.get("available")),
            "agenttrace_monitoring_available": bool(command_efficiency.get("available")),
            "trace_observatory_row_count": (
                ((command_efficiency.get("trace_observatory") or {}).get("row_count"))
                if isinstance(command_efficiency.get("trace_observatory"), Mapping)
                else None
            ),
            "command_efficiency_saved_s": (
                (((command_efficiency.get("latency_speedboard") or {}).get("summary") or {}).get("total_cumulative_saved_s"))
                if isinstance(command_efficiency.get("latency_speedboard"), Mapping)
                and isinstance((command_efficiency.get("latency_speedboard") or {}).get("summary"), Mapping)
                else None
            ),
            "work_item_count": (
                ((work_evidence.get("task_ledger") or {}).get("counts") or {}).get("work_items")
                if isinstance((work_evidence.get("task_ledger") or {}).get("counts"), Mapping)
                else None
            ),
            "route_health_attention_count": (
                ((doctrine_health.get("route_coverage") or {}).get("summary") or {}).get("route_health_attention_count")
                if isinstance((doctrine_health.get("route_coverage") or {}).get("summary"), Mapping)
                else None
            ),
            "annex_attention_count": (
                (external_intake.get("annex_sync") or {}).get("attention_count")
            ),
        },
        "frontend_contract": {
            "default_route_suggestion": "/station/meta-diagnostics",
            "endpoint": META_DIAGNOSTICS_ENDPOINT,
            "payload_class": "read_only_panel_manifest_with_drilldown_refs",
            "recommended_layout": "trust strip, behavior timeline, work evidence lane, coverage grid, proof graph",
            "avoid": [
                "rendering raw 196k-edge hologram graph as a default scene",
                "listing all WorkItems",
                "treating prompt traces or annex missing-clone rows as primary UX",
                "turning read-only diagnostics into mutation controls",
            ],
        },
        "panel_manifest": panels,
        "visual_scene": visual_scene,
        "atlas_overlay": atlas_overlay,
        "source_health": source_health,
        "trust_strip": trust_strip,
        "agent_behavior": agent_behavior,
        "command_efficiency": command_efficiency,
        "work_evidence": work_evidence,
        "doctrine_health": doctrine_health,
        "external_intake": external_intake,
        "prompt_learning": prompt_learning,
        "proof_constellation": proof_constellation,
        "omission_receipt": {
            "limit": bounded_limit,
            "omitted": [
                "raw task ledger work_items",
                "raw task ledger events.jsonl payloads",
                "raw telemetry sessions.jsonl",
                "full paper module route rows",
                "full annex rows",
                "full prompt trace payloads",
            ],
            "reason": "The console packet is a bounded UI read model. Full evidence remains behind existing drilldown endpoints and source JSON files.",
            "drilldowns": [
                "/api/world-model/task-ledger/projection",
                "/api/world-model/task-ledger/cartography/workitem",
                "/api/world-model/task-ledger/cartography/cap",
                "/api/world-model/frontend/workitem-diagnostics/projection",
                "/api/system-atlas/graph",
            ],
        },
    }


TASK_LEDGER_CARTOGRAPHY_VIEW_IDS: tuple[str, ...] = (
    "cap_cartography",
    "workitem_cartography",
)

_CARTOGRAPHY_PAYLOAD_INCLUDABLE_FIELDS: tuple[str, ...] = (
    "summary",
    "atlas_marks",
    "clusters",
    "nodes",
    "edges",
    "lineage_index",
    "legend",
    "levels",
    "overflow_index",
    "overflow_policy",
    "drilldown_index",
    "unclassified_index",
    "warnings",
    "omission_receipt",
    "source_refs",
    "queue_membership",
)


def _cartography_payload_route_for(view_id: str) -> str:
    """
    Resolve the operator-facing payload route alias for a cartography view id.

    `cap_cartography` -> `/api/world-model/task-ledger/cartography/cap`
    `workitem_cartography` -> `/api/world-model/task-ledger/cartography/workitem`
    """
    if view_id.endswith("_cartography"):
        alias = view_id[: -len("_cartography")]
    else:
        alias = view_id
    return f"/api/world-model/task-ledger/cartography/{alias}"


def _resolve_cartography_view_id(view_id: str) -> str | None:
    """
    Map a frontend-facing alias to a canonical cartography view id, or return
    None if the alias is not a known cartography view.
    """
    candidate = (view_id or "").strip().lower()
    if not candidate:
        return None
    if candidate in TASK_LEDGER_CARTOGRAPHY_VIEW_IDS:
        return candidate
    canonical = f"{candidate}_cartography"
    if canonical in TASK_LEDGER_CARTOGRAPHY_VIEW_IDS:
        return canonical
    return None


def _cartography_consumption_contract_for(
    view_id: str, payload: Mapping[str, Any] | None
) -> dict[str, Any]:
    if view_id == "workitem_cartography":
        return _workitem_cartography_consumption_contract(payload)
    if view_id == "cap_cartography":
        return _cap_cartography_consumption_contract(payload)
    return {
        "schema_version": "task_ledger_cartography_consumption_contract_unknown_v0",
        "available": False,
        "reason": f"No consumption contract registered for cartography view {view_id!r}.",
    }


def load_task_ledger_cartography_payload(
    repo_root: Path,
    view_id: str,
    *,
    include: Sequence[str] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Read-only payload-transport route for cartography views
      (`cap_cartography_v0`, `workitem_cartography_v0`). The frontend Atlas
      renderer fetches the row-grain `atlas_marks` universe + bounded graph
      layer here once on mount; the lightweight projection envelope at
      `/api/world-model/task-ledger/projection` keeps emitting only the
      consumption contract so polling stays cheap.
    - Mechanism: Resolve the alias, read the generated view JSON, attach the
      matching consumption contract, and return only the requested fields.
    - Guarantee: Read-only. Generated view is the only source; this route
      never recomputes cartography. Carryover semantics are not synthesized.
    """
    canonical = _resolve_cartography_view_id(view_id)
    if canonical is None:
        return {
            "schema": "task_ledger_cartography_payload_v1",
            "view_id_requested": view_id,
            "available": False,
            "reason": (
                f"Unknown cartography view alias {view_id!r}. "
                f"Supported aliases: cap, cap_cartography, workitem, workitem_cartography."
            ),
            "supported_view_ids": list(TASK_LEDGER_CARTOGRAPHY_VIEW_IDS),
        }

    rel_path = f"state/task_ledger/views/{canonical}.json"
    payload = _safe_read_json(repo_root, rel_path)

    if not isinstance(payload, Mapping) or not payload:
        return {
            "schema": "task_ledger_cartography_payload_v1",
            "view_id": canonical,
            "view_id_requested": view_id,
            "source_view": rel_path,
            "payload_route": _cartography_payload_route_for(canonical),
            "available": False,
            "reason": (
                "Generated cartography view is missing or empty; rebuild Task Ledger "
                "projections (rebuild_projections / task_ledger_apply --rebuild) "
                "before fetching the payload."
            ),
            "consumption_contract": _cartography_consumption_contract_for(canonical, None),
        }

    if include:
        requested = {str(field).strip() for field in include if field}
        include_set = {field for field in requested if field in _CARTOGRAPHY_PAYLOAD_INCLUDABLE_FIELDS}
        unknown_includes = sorted(requested - set(_CARTOGRAPHY_PAYLOAD_INCLUDABLE_FIELDS))
    else:
        include_set = set(_CARTOGRAPHY_PAYLOAD_INCLUDABLE_FIELDS)
        unknown_includes = []

    response: dict[str, Any] = {
        "schema": "task_ledger_cartography_payload_v1",
        "view_id": canonical,
        "view_id_requested": view_id,
        "source_view": rel_path,
        "payload_route": _cartography_payload_route_for(canonical),
        "available": True,
        "schema_version": payload.get("schema_version"),
        "generated_at": payload.get("generated_at"),
        "authority": payload.get("authority"),
        "consumption_contract": _cartography_consumption_contract_for(canonical, payload),
        "include": sorted(include_set),
        "available_include_fields": list(_CARTOGRAPHY_PAYLOAD_INCLUDABLE_FIELDS),
    }
    if unknown_includes:
        response["unknown_include_fields"] = unknown_includes
    for field in include_set:
        response[field] = payload.get(field)
    return response


def load_workitem_neighborhood_payload(
    repo_root: Path,
    work_item_id: str,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Return the FULL one-hop dependency / unlock neighborhood
      of a single WorkItem — unconstrained by the bounded cartography
      overview's top-N node cap. The Wave 1E NeighborhoodInspector
      shipped against cartography.edges, but the bounded overview
      excludes most cap_quick_*/descriptive WorkItems, so the inspector
      almost always shows "outside bounded overview · 0 neighbors". This
      route closes that gap.
    - Mechanism: Read state/task_ledger/ledger.json, locate the focus
      WorkItem, walk focus.depends_on for outbound upstream edges, and
      reverse-scan all work_items for items whose depends_on includes
      the focus id (inbound / downstream-unlock edges). Each neighbor
      row carries the canonical metadata the inspector renders.
    - Guarantee: Read-only. ledger.json is the only source. NO fuzzy
      matching, NO title/body scanning, NO event-log walk. omission_
      receipt.complete_one_hop=True distinguishes "true leaf" from
      "outside bounded overview" — the exact correctness Wave 1E lacked.
    """
    target_id = str(work_item_id or "").strip()
    if not target_id:
        return {
            "schema": "workitem_neighborhood_v0",
            "available": False,
            "work_item_id": "",
            "reason": "empty work_item_id",
        }
    ledger = _safe_read_json(repo_root, "state/task_ledger/ledger.json") or {}
    work_items = ledger.get("work_items") if isinstance(ledger, Mapping) else None
    if not isinstance(work_items, list):
        return {
            "schema": "workitem_neighborhood_v0",
            "available": False,
            "work_item_id": target_id,
            "reason": "ledger.json missing work_items array; rebuild Task Ledger projections.",
        }
    by_id: dict[str, Mapping[str, Any]] = {}
    for item in work_items:
        if isinstance(item, Mapping):
            iid = str(item.get("id") or "").strip()
            if iid:
                by_id[iid] = item
    focus_item = by_id.get(target_id)
    if focus_item is None:
        return {
            "schema": "workitem_neighborhood_v0",
            "available": False,
            "work_item_id": target_id,
            "reason": (
                f"work_item {target_id!r} not in ledger.work_items. "
                "The id may be from a different namespace (e.g. td_*) or the "
                "item may have been retired before the latest rebuild."
            ),
        }

    def _summary(item: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": str(item.get("id") or ""),
            "title": item.get("title") or item.get("statement") or item.get("id"),
            "state": item.get("state") or item.get("status") or "unknown",
            "work_item_type": item.get("work_item_type") or item.get("candidate_work_item_type") or "unknown",
            "actor": item.get("actor") or item.get("owner"),
            "family": item.get("family_id") or item.get("family"),
        }

    neighbors: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    counts = {
        "depends_on": 0,
        "unlocks": 0,
        "reverse_depends_on": 0,
        "reverse_unlocks": 0,
    }

    # Outbound: focus.depends_on → upstream edges. Each id in depends_on
    # is something the focus needs first; from focus's POV these are the
    # blockers / prerequisites.
    depends_on_list = focus_item.get("depends_on")
    if isinstance(depends_on_list, list):
        for raw in depends_on_list:
            dep_id = str(raw or "").strip()
            if not dep_id:
                continue
            upstream = by_id.get(dep_id)
            edge_id = f"edge:{target_id}->depends_on->{dep_id}"
            edges.append(
                {
                    "id": edge_id,
                    "source": target_id,
                    "target": dep_id,
                    "edge_kind": "depends_on",
                    "confidence": "source_evidenced" if upstream else "missing_source",
                    "source_ref": "state/task_ledger/ledger.json#work_items[].depends_on",
                }
            )
            counts["depends_on"] += 1
            if upstream is not None:
                summary = _summary(upstream)
            else:
                # Reference to a WorkItem that's not in the current ledger
                # — record honestly rather than fabricate fields.
                summary = {
                    "id": dep_id,
                    "title": dep_id,
                    "state": "unknown",
                    "work_item_type": "unknown",
                    "actor": None,
                    "family": None,
                    "missing_from_ledger": True,
                }
            summary["relation_to_focus"] = "depends_on"
            summary["direction"] = "outbound"
            summary["edge_id"] = edge_id
            summary["confidence"] = "source_evidenced" if upstream else "missing_source"
            summary["source_ref"] = "state/task_ledger/ledger.json#work_items[].depends_on"
            neighbors.append(summary)

    # Inbound: scan all items, find those whose depends_on includes the
    # focus id → focus unlocks them once it lands. This is the reverse-
    # depends-on traversal; bounded overview omits these for most ids.
    for other_id, other_item in by_id.items():
        if other_id == target_id:
            continue
        other_deps = other_item.get("depends_on")
        if not isinstance(other_deps, list):
            continue
        if not any(isinstance(d, str) and d.strip() == target_id for d in other_deps):
            continue
        edge_id = f"edge:{other_id}->depends_on->{target_id}"
        edges.append(
            {
                "id": edge_id,
                "source": other_id,
                "target": target_id,
                "edge_kind": "depends_on",
                "confidence": "source_evidenced",
                "source_ref": "state/task_ledger/ledger.json#work_items[].depends_on (reverse scan)",
            }
        )
        counts["reverse_depends_on"] += 1
        counts["unlocks"] += 1
        summary = _summary(other_item)
        # From focus's POV: this neighbor is downstream — focus unlocks it.
        summary["relation_to_focus"] = "unlocks"
        summary["direction"] = "inbound"
        summary["edge_id"] = edge_id
        summary["confidence"] = "source_evidenced"
        summary["source_ref"] = "state/task_ledger/ledger.json#work_items[].depends_on (reverse scan)"
        neighbors.append(summary)

    focus_summary = _summary(focus_item)

    return {
        "schema": "workitem_neighborhood_v0",
        "available": True,
        "work_item_id": target_id,
        "generated_at": ledger.get("generated_at"),
        "source": {
            "authority": "state/task_ledger/ledger.json",
            "edge_views": [
                "ledger.work_items[].depends_on",
                "ledger.work_items[].depends_on (reverse scan)",
            ],
        },
        "focus": focus_summary,
        "neighbors": neighbors,
        "edges": edges,
        "counts": counts,
        "omission_receipt": {
            "complete_one_hop": True,
            "bounded_by_cartography_overview": False,
            "reason": None,
            "note": (
                "One-hop neighborhood from ledger.work_items.depends_on (outbound) "
                "plus reverse-scan (inbound). Supersession / handoff edges are NOT "
                "included in this v0 — extend the loader when those edge_kinds become "
                "first-class fields on work_items."
            ),
        },
    }


def _task_ledger_dossier_text(value: Any, *, limit: int = 1200) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def _task_ledger_dossier_list(value: Any, *, limit: int = 8) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return list(value)[:limit]


def _task_ledger_dossier_mapping(value: Any, *, keys: Sequence[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    if keys is None:
        return {str(key): val for key, val in value.items()}
    return {key: value.get(key) for key in keys if key in value}


def _task_ledger_event_payload_preview(payload: Mapping[str, Any]) -> dict[str, Any]:
    preview_keys = (
        "title",
        "statement",
        "problem",
        "impact",
        "acceptance",
        "note",
        "state",
        "rank",
        "work_item_type",
        "candidate_work_item_type",
        "reason",
    )
    preview: dict[str, Any] = {}
    for key in preview_keys:
        value = payload.get(key)
        if isinstance(value, str):
            text = _task_ledger_dossier_text(value, limit=420)
            if text:
                preview[key] = text
        elif value not in (None, [], {}):
            preview[key] = value
    receipt = payload.get("execution_receipt") or payload.get("receipt")
    if isinstance(receipt, Mapping):
        preview["execution_receipt"] = _task_ledger_dossier_mapping(
            receipt,
            keys=(
                "transaction_id",
                "id",
                "commit_hash",
                "closeout_state",
                "work_ledger_session_id",
            ),
        )
    return preview


def _task_ledger_events_for_item(
    repo_root: Path,
    item: Mapping[str, Any],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    target_id = str(item.get("id") or "").strip()
    source_event_ids = {str(event_id) for event_id in item.get("source_event_ids") or [] if event_id}
    path = repo_root / "state/task_ledger/events.jsonl"
    if not target_id or not path.exists():
        return []
    matches: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, Mapping):
                    continue
                event_id = str(event.get("event_id") or "").strip()
                subject_id = str(event.get("subject_id") or "").strip()
                if subject_id != target_id and event_id not in source_event_ids:
                    continue
                payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
                matches.append(
                    {
                        "event_id": event.get("event_id"),
                        "event_type": event.get("event_type"),
                        "subject_id": event.get("subject_id"),
                        "created_at": event.get("created_at"),
                        "created_by": event.get("created_by"),
                        "payload_preview": _task_ledger_event_payload_preview(payload),
                        "refs": event.get("refs") if isinstance(event.get("refs"), Mapping) else {},
                    }
                )
    except OSError:
        return []
    return matches[-limit:][::-1]


def _task_ledger_dossier_source_views(
    repo_root: Path,
    target_id: str,
) -> list[dict[str, Any]]:
    memberships: list[dict[str, Any]] = []
    for view_id, role in _TASK_LEDGER_VIEW_ROLES.items():
        if view_id in TASK_LEDGER_CARTOGRAPHY_VIEW_IDS:
            continue
        rel_path = f"state/task_ledger/views/{view_id}.json"
        payload = _safe_read_json(repo_root, rel_path) or {}
        for index, row in enumerate(_task_ledger_view_items(payload)):
            row_id = str(row.get("id") or row.get("subject_id") or "").strip()
            if row_id != target_id:
                continue
            membership = {
                "view_id": view_id,
                "role": role,
                "path": rel_path,
                "index": index,
                "generated_at": payload.get("generated_at") if isinstance(payload, Mapping) else None,
                "row_summary": _task_ledger_compact_item(row),
            }
            for key in (
                "why_this_next",
                "why_recommended",
                "required_next_event",
                "commitment_status",
                "commitment_source",
                "dependency_status",
                "selection_factors",
            ):
                value = row.get(key)
                if value not in (None, [], {}):
                    membership[key] = value
            memberships.append(membership)
            break
    return memberships


def _task_ledger_dossier_cartography_mark(
    repo_root: Path,
    target_id: str,
) -> dict[str, Any] | None:
    payload = _safe_read_json(repo_root, "state/task_ledger/views/workitem_cartography.json") or {}
    atlas_marks = payload.get("atlas_marks") if isinstance(payload, Mapping) else None
    if not isinstance(atlas_marks, list):
        return None
    for raw_mark in atlas_marks:
        if not isinstance(raw_mark, Mapping):
            continue
        if str(raw_mark.get("id") or "").strip() != target_id:
            continue
        return {
            "id": raw_mark.get("id"),
            "title": raw_mark.get("title") or raw_mark.get("label"),
            "state": raw_mark.get("state"),
            "work_item_type": raw_mark.get("work_item_type"),
            "actor": raw_mark.get("actor"),
            "family": raw_mark.get("family"),
            "overlays": raw_mark.get("overlays") or {},
            "edge_summary": raw_mark.get("edge_summary") or {},
            "route_explanation": raw_mark.get("route_explanation") or {},
            "source_route_metadata": raw_mark.get("source_route_metadata") or {},
        }
    return None


def _task_ledger_dossier_focus(item: Mapping[str, Any]) -> dict[str, Any]:
    projection = (
        item.get("projection_completeness")
        if isinstance(item.get("projection_completeness"), Mapping)
        else {}
    )
    return {
        **_task_ledger_compact_item(item),
        "statement": _task_ledger_dossier_text(item.get("statement")),
        "problem": _task_ledger_dossier_text(item.get("problem")),
        "impact": _task_ledger_dossier_text(item.get("impact")),
        "acceptance": _task_ledger_dossier_text(item.get("acceptance")),
        "confidence": item.get("confidence"),
        "owner": item.get("owner"),
        "actor": item.get("actor") or item.get("owner") or item.get("created_by"),
        "created_at": item.get("created_at"),
        "created_by": item.get("created_by"),
        "updated_at": item.get("updated_at"),
        "tags": _task_ledger_dossier_list(item.get("tags"), limit=12),
        "notes": _task_ledger_dossier_list(item.get("notes"), limit=6),
        "evidence": _task_ledger_dossier_list(item.get("evidence"), limit=8),
        "evidence_refs": _task_ledger_dossier_list(item.get("evidence_refs"), limit=12),
        "recommended_action": item.get("recommended_action"),
        "source_event_ids": _task_ledger_dossier_list(item.get("source_event_ids"), limit=20),
        "source_event_types": _task_ledger_dossier_list(item.get("source_event_types"), limit=20),
        "projection_completeness": {
            "has_satisfaction_contract": projection.get("has_satisfaction_contract"),
            "has_integration_contract": projection.get("has_integration_contract"),
            "exact_surfaces_grounded": projection.get("exact_surfaces_grounded"),
            "needs_signoff": projection.get("needs_signoff"),
            "has_work_ledger_claim_ref": projection.get("has_work_ledger_claim_ref"),
            "has_prompt_trace_ref": projection.get("has_prompt_trace_ref"),
        },
    }


def load_workitem_dossier_payload(
    repo_root: Path,
    work_item_id: str,
    *,
    event_limit: int = 12,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Give the Work lens a click-worthy per-WorkItem drilldown
      without bloating the global projection or making the cartography view
      pretend to be a dossier. This is the backend contract that both the
      priority list and Atlas marks can call.
    - Mechanism: Compose existing Task Ledger authority/projections:
      ledger.json for the focus row, events.jsonl for recent event lineage,
      views/*.json for queue/source-view membership, workitem_cartography for
      mark metadata, and `load_workitem_neighborhood_payload` for one-hop
      dependency/unlock context.
    - Guarantee: Read-only. No fuzzy matching and no mutation; event payloads
      are summarized, not dumped wholesale.
    """
    target_id = str(work_item_id or "").strip()
    if not target_id:
        return {
            "schema": "workitem_dossier_v0",
            "available": False,
            "work_item_id": "",
            "reason": "empty work_item_id",
        }
    ledger = _safe_read_json(repo_root, "state/task_ledger/ledger.json") or {}
    work_items = ledger.get("work_items") if isinstance(ledger, Mapping) else None
    if not isinstance(work_items, list):
        return {
            "schema": "workitem_dossier_v0",
            "available": False,
            "work_item_id": target_id,
            "reason": "ledger.json missing work_items array; rebuild Task Ledger projections.",
        }
    focus_item: Mapping[str, Any] | None = None
    for raw_item in work_items:
        if isinstance(raw_item, Mapping) and str(raw_item.get("id") or "").strip() == target_id:
            focus_item = raw_item
            break
    if focus_item is None:
        return {
            "schema": "workitem_dossier_v0",
            "available": False,
            "work_item_id": target_id,
            "reason": f"work_item {target_id!r} not in ledger.work_items.",
        }

    source_views = _task_ledger_dossier_source_views(repo_root, target_id)
    ranked_rows = [
        row
        for row in source_views
        if row.get("why_this_next") or row.get("why_recommended") or row.get("selection_factors")
    ]
    latest_receipt = (
        focus_item.get("latest_execution_receipt")
        if isinstance(focus_item.get("latest_execution_receipt"), Mapping)
        else None
    )
    execution_receipts = _task_ledger_dossier_list(
        focus_item.get("execution_receipts"),
        limit=6,
    )

    return {
        "schema": "workitem_dossier_v0",
        "available": True,
        "work_item_id": target_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "authority": "state/task_ledger/events.jsonl",
            "projection": "state/task_ledger/ledger.json",
            "source_views": "state/task_ledger/views/*.json",
            "cartography_view": "state/task_ledger/views/workitem_cartography.json",
            "endpoint": f"/api/world-model/task-ledger/dossier/{target_id}",
            "mutation_boundary": "read_only_existing_writers_remain_authority",
        },
        "focus": _task_ledger_dossier_focus(focus_item),
        "narrative": {
            "statement": _task_ledger_dossier_text(focus_item.get("statement")),
            "problem": _task_ledger_dossier_text(focus_item.get("problem")),
            "impact": _task_ledger_dossier_text(focus_item.get("impact")),
            "acceptance": _task_ledger_dossier_text(focus_item.get("acceptance")),
            "recommended_action": focus_item.get("recommended_action"),
            "evidence": _task_ledger_dossier_list(focus_item.get("evidence"), limit=8),
        },
        "contracts": {
            "satisfaction_contract": _task_ledger_dossier_mapping(focus_item.get("satisfaction_contract")),
            "integration_contract": _task_ledger_dossier_mapping(focus_item.get("integration_contract")),
            "completion": _task_ledger_dossier_mapping(focus_item.get("completion")),
            "authority": _task_ledger_dossier_mapping(focus_item.get("authority")),
        },
        "execution": {
            "route": _task_ledger_route(focus_item),
            "execution": _task_ledger_dossier_mapping(focus_item.get("execution")),
            "transaction_state": focus_item.get("transaction_state"),
            "latest_execution_receipt": dict(latest_receipt) if latest_receipt else None,
            "execution_receipts": execution_receipts,
            "commit_refs": _task_ledger_dossier_list(focus_item.get("commit_refs"), limit=12),
            "receipt_refs": _task_ledger_dossier_list(focus_item.get("receipt_refs"), limit=12),
            "work_ledger_refs": _task_ledger_dossier_list(focus_item.get("work_ledger_refs"), limit=12),
            "closeout_assurance": _task_ledger_dossier_mapping(focus_item.get("closeout_assurance")),
            "propagation": _task_ledger_dossier_mapping(focus_item.get("propagation")),
        },
        "ranking": {
            "rank": focus_item.get("rank"),
            "rank_history": _task_ledger_dossier_list(focus_item.get("rank_history"), limit=8),
            "ranked_source_views": ranked_rows,
        },
        "source_view_membership": source_views,
        "cartography": {
            "mark": _task_ledger_dossier_cartography_mark(repo_root, target_id),
            "payload_route": "/api/world-model/task-ledger/cartography/workitem",
        },
        "neighborhood": load_workitem_neighborhood_payload(repo_root, target_id),
        "recent_events": _task_ledger_events_for_item(
            repo_root,
            focus_item,
            limit=max(1, min(int(event_limit), 50)),
        ),
        "omission_receipt": {
            "raw_event_payloads_omitted": True,
            "raw_work_item_row_omitted": True,
            "event_limit": max(1, min(int(event_limit), 50)),
            "reason": (
                "Dossier exposes bounded fields for UI drilldown; events.jsonl and "
                "ledger.json remain source authority for full rows."
            ),
            "drilldowns": [
                "./repo-python kernel.py --option-surface task_ledger --band card --ids "
                f"{target_id}",
                f"jq '.work_items[] | select(.id==\"{target_id}\")' state/task_ledger/ledger.json",
            ],
        },
    }


def load_task_ledger_projection(repo_root: Path, *, limit: int = 8) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Serve the compact Task Ledger live projection needed by the
      Station ledger lens without creating a second backlog authority.
    - Mechanism: Read state/task_ledger deterministic projections and the
      phase-local demo queue, then label missing phase/subphase route metadata
      explicitly on each compact row.
    - Guarantee: Read-only; events.jsonl and task_ledger_apply.py remain the
      only mutation lane.
    """
    ledger = _safe_read_json(repo_root, "state/task_ledger/ledger.json") or {}
    queue_ref = _active_task_ledger_queue_ref(repo_root)
    queue = queue_ref["payload"]
    work_items = _task_ledger_view_items(ledger)
    ledger_by_id: dict[str, Mapping[str, Any]] = {
        str(item.get("id")): item for item in work_items if item.get("id")
    }
    state_counts = Counter(str(item.get("state") or "unknown") for item in work_items)
    type_counts = Counter(str(item.get("work_item_type") or "unknown") for item in work_items)

    sections: dict[str, Any] = {}
    view_counts: dict[str, int] = {}
    view_generated_at: dict[str, str | None] = {}
    view_payloads: dict[str, Mapping[str, Any]] = {}
    for view_id, role in _TASK_LEDGER_VIEW_ROLES.items():
        rel_path = f"state/task_ledger/views/{view_id}.json"
        payload = _safe_read_json(repo_root, rel_path) or {}
        view_payloads[view_id] = payload
        items = _task_ledger_view_items(payload)
        view_counts[view_id] = len(items)
        view_generated_at[view_id] = payload.get("generated_at") if isinstance(payload, Mapping) else None
        if view_id in TASK_LEDGER_CARTOGRAPHY_VIEW_IDS:
            # Cartography views emit row-grain `atlas_marks` + bounded
            # representative graph; the generic `_task_ledger_compact_item`
            # would compact `view.items` (== clusters) into work-item-shaped
            # junk. Expose the payload route instead and refuse to ship fake
            # WorkItem rows here. Frontend Atlas renderer must use the route.
            sections[view_id] = {
                "view_id": view_id,
                "role": role,
                "path": rel_path,
                "generated_at": view_generated_at[view_id],
                "count": len(items),
                "items": [],
                "items_are_not_work_items": True,
                "item_policy": "cartography_payload_route_required",
                "payload_route": _cartography_payload_route_for(view_id),
                "reason": (
                    "Cartography views ship row-grain marks and a bounded graph via "
                    "the payload route; sections.items would compact clusters into "
                    "fake WorkItem rows."
                ),
            }
            continue
        sections[view_id] = {
            "view_id": view_id,
            "role": role,
            "path": rel_path,
            "generated_at": view_generated_at[view_id],
            "count": len(items),
            "items": [_task_ledger_compact_item(item) for item in items[:limit]],
        }

    events_path = "state/task_ledger/events.jsonl"
    ledger_path = "state/task_ledger/ledger.json"
    authority = {
        "event_log": events_path,
        "deterministic_projection": ledger_path,
        "mutation_lane": "./repo-python tools/meta/factory/task_ledger_apply.py",
        "station_consumer": "/station/ledger",
        "endpoint": "/api/world-model/task-ledger/projection",
        "boundary": "read_only_projection_events_are_authority",
    }
    freshness = {
        "events": compute_freshness(_file_mtime(repo_root, events_path)),
        "ledger": compute_freshness(_file_mtime(repo_root, ledger_path)),
        "views_generated_at": view_generated_at,
    }
    current_next = _task_ledger_current_next(
        queue,
        ledger_by_id,
        queue_path=str(queue_ref["path"]),
    )
    projection_honesty = {
        "phase_scope": f"{queue_ref.get('phase_id') or 'unknown'} phase-local queue is used only to identify current_next.",
        "queue_source": queue_ref.get("source"),
        "queue_path": queue_ref.get("path"),
        "fallback_used": queue_ref.get("fallback_used"),
        "route_metadata_policy": "Rows without execution.phase_id/source_queue/queue_sequence are labeled route.status=unknown.",
        "unknown_policy": "Missing execution phase/source queue metadata is surfaced as unknown instead of synthesized.",
        "unknown_route_count": sum(
            1 for item in work_items if _task_ledger_route(item).get("status") == "unknown"
        ),
        "public_projection_status": "not_asserted",
        "tmp_receipts_policy": "Disposable /tmp publication receipts are not treated as green publication evidence by this endpoint.",
    }
    cap_cartography_payload = view_payloads.get("cap_cartography")
    cap_cartography_contract = _cap_cartography_consumption_contract(cap_cartography_payload)
    workitem_cartography_payload = view_payloads.get("workitem_cartography")
    workitem_cartography_contract = _workitem_cartography_consumption_contract(workitem_cartography_payload)
    return {
        **_diagnostic_projection_envelope(
            schema="task_ledger_projection_v1",
            authority=authority,
            freshness=freshness,
            current_next=current_next,
            projection_honesty=projection_honesty,
        ),
        "counts": {
            "work_items": len(work_items),
            "states": dict(sorted(state_counts.items())),
            "types": dict(sorted(type_counts.items())),
            "views": view_counts,
        },
        "overload": {
            "active_wip": view_counts.get("active_wip", 0),
            "captures": state_counts.get("captured", 0),
            "needs_signoff": view_counts.get("needs_signoff", 0),
            "missing_contracts": view_counts.get("missing_contracts_ranked", 0),
            "stale_review": view_counts.get("stale_review", 0),
        },
        "legibility": _task_ledger_legibility_projection(
            work_items=work_items,
            view_payloads=view_payloads,
            view_counts=view_counts,
            limit=limit,
        ),
        "cap_cartography_consumption_contract": cap_cartography_contract,
        "cap_cartography_exposition_specimen": _cap_cartography_exposition_specimen(
            cap_cartography_payload,
            cap_cartography_contract,
        ),
        "workitem_cartography_consumption_contract": workitem_cartography_contract,
        "sections": sections,
        "recent_event_tail": _task_ledger_event_tail(repo_root, limit=limit),
    }


def _system_lens_factory_slice(repo_root: Path) -> Dict[str, Any]:
    factory = _safe_read_json(repo_root, FACTORY_STATE_PATH) or {}
    stage = factory.get("stage")
    return {
        "stage": stage,
        "blocked": bool(factory.get("blocked") or str(stage or "").endswith("_pending")),
        "gate_reason": factory.get("gate_reason"),
        "last_run": factory.get("last_run"),
        "last_materialize": factory.get("last_materialize"),
        "last_stage_apply": factory.get("last_stage_apply"),
        "stage_error": _stage_error_from_mapping(
            factory,
            stage=stage,
            source_path=FACTORY_STATE_PATH,
        ),
        "source_path": FACTORY_STATE_PATH,
    }


def _system_lens_phase_narrative(phase: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not phase:
        return {"headline": None, "recent_cycle_summaries": [], "last_routing_decision": None}
    synth = phase.get("synth") if isinstance(phase.get("synth"), Mapping) else {}
    meta_ledger = phase.get("meta_ledger") if isinstance(phase.get("meta_ledger"), Mapping) else {}
    focus = phase.get("focus_directive") if isinstance(phase.get("focus_directive"), Mapping) else {}
    headline = (
        synth.get("summary")
        or meta_ledger.get("summary")
        or focus.get("summary")
        or phase.get("title")
    )
    return {
        "headline": _excerpt(headline, limit=260),
        "recent_cycle_summaries": [],
        "last_routing_decision": None,
    }


def _system_lens_phase_slice(phase: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not phase:
        return {
            "id": None,
            "title": None,
            "route": "/station/phase",
            "latest_cycle": None,
            "cycle_count": None,
            "directive_active": False,
            "directive_summary": None,
            "pipeline_state": {},
            "narrative": _system_lens_phase_narrative(None),
            "freshness": compute_freshness(None),
        }
    focus = phase.get("focus_directive") if isinstance(phase.get("focus_directive"), Mapping) else {}
    pipeline = phase.get("pipeline_state") if isinstance(phase.get("pipeline_state"), Mapping) else {}
    phase_id = phase.get("phase_id")
    return {
        "id": phase_id,
        "title": phase.get("title"),
        "route": f"/station/phase/{phase_id}" if phase_id else "/station/phase",
        "latest_cycle": phase.get("latest_cycle"),
        "cycle_count": phase.get("cycle_count"),
        "directive_active": bool(focus.get("active")),
        "directive_summary": focus.get("summary"),
        "pipeline_state": {
            "stage": pipeline.get("stage"),
            "controller_phase": pipeline.get("controller_phase"),
            "cycle": pipeline.get("cycle"),
            "blocked": bool(pipeline.get("blocked")),
            "gate_reason": pipeline.get("gate_reason"),
            "updated_at": pipeline.get("updated_at"),
            # Phase-local only. Factory failures stay in factory.stage_error.
            "stage_error": pipeline.get("stage_error"),
        },
        "narrative": _system_lens_phase_narrative(phase),
        "freshness": phase.get("freshness") or compute_freshness(pipeline.get("updated_at")),
    }


def _system_lens_orchestration_slice(orchestration: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not orchestration:
        return {
            "active_driver": None,
            "decision": {},
            "gate": {},
            "drivers": [],
            "active_driver_record": None,
            "reactions": {},
            "updated_at": None,
            "freshness": compute_freshness(None),
        }
    drivers = [dict(driver) for driver in orchestration.get("drivers") or [] if isinstance(driver, Mapping)]
    active_driver = orchestration.get("active_driver")
    active_record = None
    for driver in drivers:
        if driver.get("driver_id") == active_driver or driver.get("active"):
            active_record = driver
            break
    return {
        "active_driver": active_driver,
        "decision": dict(orchestration.get("decision") or {}),
        "gate": dict(orchestration.get("gate") or {}),
        "drivers": drivers,
        "active_driver_record": active_record,
        "reactions": dict(orchestration.get("reactions") or {}),
        "updated_at": orchestration.get("updated_at"),
        "freshness": orchestration.get("freshness") or compute_freshness(orchestration.get("updated_at")),
    }


def _system_lens_work_slice(work: Mapping[str, Any], task_projection: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "counts": dict(work.get("counts") or {}),
        "current_next": task_projection.get("current_next"),
        "top_stale": list(work.get("top_stale") or []),
        "top_in_progress": list(work.get("top_in_progress") or []),
        "top_recent_open": list(work.get("top_recent_open") or []),
        "generated_at": work.get("generated_at"),
        "freshness": work.get("freshness") or compute_freshness(work.get("generated_at")),
    }


def _system_lens_approvals_slice(approvals: Mapping[str, Any]) -> Dict[str, Any]:
    summary = approvals.get("summary") if isinstance(approvals.get("summary"), Mapping) else {}
    rows = [
        dict(record)
        for record in list(summary.get("top_records") or approvals.get("records") or [])[:6]
        if isinstance(record, Mapping)
    ]
    return {
        "pending": int(summary.get("total_pending") or 0),
        "source_kind_counts": dict(summary.get("source_kind_counts") or {}),
        "action_kind_counts": dict(summary.get("action_kind_counts") or {}),
        "status_counts": dict(summary.get("status_counts") or {}),
        "rows": rows,
        "generated_at": approvals.get("generated_at"),
    }


def _system_lens_drift_slice(drift: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if not drift:
        return {"total": 0, "severity_counts": {}, "sources": [], "generated_at": None}
    sources = []
    for source in list(drift.get("sources") or [])[:8]:
        if not isinstance(source, Mapping):
            continue
        sources.append(
            {
                "plane": source.get("plane"),
                "label": source.get("label"),
                "count": int(source.get("count") or 0),
                "severity_counts": dict(source.get("severity_counts") or {}),
                "preview": list(source.get("preview") or [])[:3],
                "available": bool(source.get("available")),
                "paper_module": source.get("paper_module"),
                "surface_route": _safe_internal_route(source.get("surface_route"), "/station/drift"),
                "last_seen_at": source.get("last_seen_at") or drift.get("generated_at"),
            }
        )
    return {
        "total": int(drift.get("total") or 0),
        "severity_counts": dict(drift.get("severity_counts") or {}),
        "sources": sources,
        "generated_at": drift.get("generated_at"),
    }


def _transition_sort_key(row: Mapping[str, Any]) -> datetime:
    return _parse_iso_datetime(row.get("when")) or datetime.min.replace(tzinfo=timezone.utc)


def _add_recent_transition(rows: List[Dict[str, Any]], row: Dict[str, Any]) -> None:
    if not row.get("when") and not row.get("subject_label"):
        return
    rows.append(
        {
            "kind": str(row.get("kind") or "unknown"),
            "subject_id": row.get("subject_id"),
            "subject_label": row.get("subject_label"),
            "from_state": row.get("from_state"),
            "to_state": row.get("to_state"),
            "when": row.get("when"),
            "actor": row.get("actor"),
            "surface_route": _safe_internal_route(row.get("surface_route"), "/station/timeline"),
        }
    )


def _system_lens_recent_transitions(
    repo_root: Path,
    *,
    work: Mapping[str, Any],
    approvals: Mapping[str, Any],
    orchestration_events: Sequence[Mapping[str, Any]],
    factory: Mapping[str, Any],
    limit: int = 20,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    try:
        events = work_ledger_lib.load_events(
            repo_root,
            phase_id=str(work.get("phase_id") or "") or None,
            family_id=str(work.get("family_id") or "") or None,
        )
    except Exception:
        events = []
    for event in events[-limit:]:
        if not isinstance(event, Mapping):
            continue
        td_id = event.get("td_id")
        _add_recent_transition(
            rows,
            {
                "kind": "work_ledger",
                "subject_id": td_id,
                "subject_label": event.get("title") or event.get("body") or td_id,
                "from_state": event.get("from_status"),
                "to_state": event.get("status") or event.get("event_kind"),
                "when": event.get("created_at"),
                "actor": event.get("actor"),
                "surface_route": _intelligence_work_route(td_id),
            },
        )

    for event in _task_ledger_event_tail(repo_root, limit=limit):
        _add_recent_transition(
            rows,
            {
                "kind": "task_ledger",
                "subject_id": event.get("subject_id") or event.get("event_id"),
                "subject_label": event.get("event_type") or event.get("subject_id"),
                "to_state": event.get("event_type"),
                "when": event.get("created_at"),
                "actor": event.get("created_by"),
                "surface_route": "/station/ledger",
            },
        )

    approval_rows = approvals.get("records") if isinstance(approvals.get("records"), list) else []
    for record in approval_rows[:limit]:
        if not isinstance(record, Mapping):
            continue
        _add_recent_transition(
            rows,
            {
                "kind": "approval",
                "subject_id": record.get("approval_id"),
                "subject_label": record.get("title"),
                "to_state": record.get("status"),
                "when": record.get("updated_at") or record.get("opened_at"),
                "actor": record.get("owner_driver"),
                "surface_route": record.get("surface_route") or "/station/approvals",
            },
        )

    for event in orchestration_events[:limit]:
        _add_recent_transition(
            rows,
            {
                "kind": "orchestration",
                "subject_id": event.get("event_id"),
                "subject_label": event.get("summary") or event.get("immediate_mode"),
                "to_state": event.get("gate_reason") or event.get("immediate_mode") or event.get("kind"),
                "when": event.get("recorded_at"),
                "actor": event.get("active_driver") or event.get("current_owner"),
                "surface_route": "/station/timeline",
            },
        )

    _add_recent_transition(
        rows,
        {
            "kind": "factory",
            "subject_id": FACTORY_STATE_PATH,
            "subject_label": factory.get("stage") or "factory stage",
            "to_state": factory.get("stage"),
            "when": factory.get("last_stage_apply") or factory.get("last_run"),
            "surface_route": "/station/timeline",
        },
    )

    rows.sort(key=_transition_sort_key, reverse=True)
    return rows[:limit]


def load_system_lens_projection(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Compose the System intelligence lens as one rich backend
      projection instead of making the browser stitch sparse snapshots.
    - Mechanism: Joins the world snapshot, work overview, task ledger compact
      projection, approval inbox, factory state, and orchestration event stream
      under a single generated_at boundary.
    - Guarantee: Additive read-only `system_lens_projection_v1` payload.
    """
    generated = datetime.now(timezone.utc).isoformat()
    world = load_world_model_snapshot(repo_root)
    work = load_work_ledger_overview(repo_root)
    task_projection = load_task_ledger_projection(repo_root, limit=8)
    approvals = list_approvals(repo_root)
    factory = _system_lens_factory_slice(repo_root)
    orchestration_events = load_orchestration_events(repo_root, limit=20)

    phase = _system_lens_phase_slice(world.get("active_phase") if isinstance(world.get("active_phase"), Mapping) else None)
    orchestration = _system_lens_orchestration_slice(
        world.get("orchestration") if isinstance(world.get("orchestration"), Mapping) else None
    )
    drift = _system_lens_drift_slice(
        world.get("drift_aggregate") if isinstance(world.get("drift_aggregate"), Mapping) else None
    )
    recent_transitions = _system_lens_recent_transitions(
        repo_root,
        work=work,
        approvals=approvals,
        orchestration_events=orchestration_events,
        factory=factory,
        limit=20,
    )

    return {
        "schema": "system_lens_projection_v1",
        "generated_at": generated,
        "source_generated_at": {
            "world_model": world.get("generated_at"),
            "work_ledger_overview": work.get("generated_at"),
            "task_ledger_projection": task_projection.get("generated_at"),
            "approvals": approvals.get("generated_at"),
            "drift": (world.get("drift_aggregate") or {}).get("generated_at")
            if isinstance(world.get("drift_aggregate"), Mapping)
            else None,
            "factory": factory.get("last_stage_apply") or factory.get("last_run"),
        },
        "freshness": compute_freshness(generated),
        "phase": phase,
        "factory": factory,
        "orchestration": orchestration,
        "work": _system_lens_work_slice(work, task_projection),
        "approvals": _system_lens_approvals_slice(approvals),
        "drift": drift,
        "recent_transitions": recent_transitions,
    }


def _ops_evidence_ref(
    refs: Dict[str, Dict[str, Any]],
    ref_id: str,
    *,
    kind: str,
    label: str,
    path: str | None = None,
    href: str | None = None,
    excerpt: str | None = None,
    freshness: str | None = None,
) -> str:
    refs.setdefault(
        ref_id,
        {
            "id": ref_id,
            "kind": kind,
            "label": label,
            **({"path": path} if path else {}),
            **({"href": href} if href else {}),
            **({"excerpt": excerpt} if excerpt else {}),
            **({"freshness": freshness} if freshness else {}),
        },
    )
    return ref_id


def _ops_status(*, blocked: bool = False, failed: bool = False, stale: bool = False, active: bool = False) -> str:
    if failed:
        return "failed"
    if blocked:
        return "blocked"
    if stale:
        return "stale"
    if active:
        return "active"
    return "ok"


def _ops_graph_status(status: str | None) -> str:
    token = str(status or "").lower()
    if token in {"failed", "error", "block", "blocked"}:
        return "failed" if token in {"failed", "error"} else "blocked"
    if token in {"stale", "expired"}:
        return "stale"
    if token in {"warn", "warning", "watch", "active", "claimed", "open", "in_progress", "shaping"}:
        return "watch"
    if token in {"ok", "clear", "done", "satisfied", "closed"}:
        return "ok"
    return "unknown"


def _ops_node(
    node_id: str,
    *,
    label: str,
    kind: str,
    status: str,
    weight: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "id": node_id,
        "label": label,
        "kind": kind,
        "status": _ops_graph_status(status),
        **({"weight": weight} if weight is not None else {}),
        "metadata": dict(metadata or {}),
    }


def _ops_edge(
    edge_id: str,
    source: str,
    target: str,
    *,
    kind: str,
    status: str = "ok",
    label: str | None = None,
) -> Dict[str, Any]:
    return {
        "id": edge_id,
        "source": source,
        "target": target,
        "kind": kind,
        "status": _ops_graph_status(status),
        **({"label": label} if label else {}),
    }


def _ops_stage_node(
    node_id: str,
    *,
    label: str,
    kind: str,
    status: str,
    evidence_refs: Sequence[str],
    started_at: str | None = None,
    updated_at: str | None = None,
    blocker_ids: Sequence[str] | None = None,
) -> Dict[str, Any]:
    return {
        "id": node_id,
        "label": label,
        "kind": kind,
        "status": status,
        "started_at": started_at,
        "updated_at": updated_at,
        "duration_seconds": None,
        "blocker_ids": list(blocker_ids or []),
        "evidence_refs": list(evidence_refs),
    }


def _ops_stage_graph_node(stage: Mapping[str, Any]) -> Dict[str, Any]:
    return _ops_node(
        str(stage.get("id") or "stage:unknown"),
        label=str(stage.get("label") or stage.get("id") or "Unknown stage"),
        kind=str(stage.get("kind") or "runtime"),
        status=str(stage.get("status") or "unknown"),
        metadata={
            "stage": True,
            "updated_at": stage.get("updated_at"),
            "evidence_refs": list(stage.get("evidence_refs") or []),
        },
    )


def _ops_chain_edges(lane_id: str, stages: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    edges: List[Dict[str, Any]] = []
    previous_id: str | None = None
    for stage in stages:
        stage_id = str(stage.get("id") or "")
        if previous_id and stage_id:
            edges.append(
                _ops_edge(
                    f"{previous_id}->{stage_id}",
                    previous_id,
                    stage_id,
                    kind="handoff_to",
                    label=lane_id,
                    status=str(stage.get("status") or "unknown"),
                )
            )
        for blocker_id in _str_list(stage.get("blocker_ids")):
            if blocker_id and stage_id and blocker_id != stage_id:
                edges.append(
                    _ops_edge(
                        f"{blocker_id}->blocks->{stage_id}",
                        blocker_id,
                        stage_id,
                        kind="blocks",
                        label="blocks",
                        status=str(stage.get("status") or "blocked"),
                    )
                )
        previous_id = stage_id or previous_id
    return edges


def _ops_dedupe_graph(
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    node_by_id: Dict[str, Dict[str, Any]] = {}
    for node in nodes:
        node_id = str(node.get("id") or "").strip()
        if node_id and node_id not in node_by_id:
            node_by_id[node_id] = dict(node)
    edge_by_id: Dict[str, Dict[str, Any]] = {}
    for edge in edges:
        edge_id = str(edge.get("id") or "").strip()
        if edge_id and edge_id not in edge_by_id:
            edge_by_id[edge_id] = dict(edge)
    return {"nodes": list(node_by_id.values()), "edges": list(edge_by_id.values())}


def _ops_source_error(source: str, exc: BaseException, *, path: str | None = None) -> Dict[str, Any]:
    message = str(exc).strip() or exc.__class__.__name__
    return {
        "source": source,
        "status": "failed",
        "message": _excerpt(message, limit=500),
        "path": path,
        "exception_type": exc.__class__.__name__,
    }


def _ops_record_source_error(
    refs: Dict[str, Dict[str, Any]],
    source_errors: List[Dict[str, Any]],
    source: str,
    exc: BaseException,
    *,
    path: str | None = None,
) -> None:
    row = _ops_source_error(source, exc, path=path)
    source_errors.append(row)
    _ops_evidence_ref(
        refs,
        f"diagnostic:{source}",
        kind="runtime_snapshot",
        label=f"{source} source error",
        path=path,
        excerpt=row["message"],
        freshness="stale",
    )


def _ops_record_source_timing(
    source_timings: List[Dict[str, Any]] | None,
    source: str,
    started_at: float,
    status: str,
) -> None:
    if source_timings is None:
        return
    source_timings.append(
        {
            "source": source,
            "duration_ms": round((time.perf_counter() - started_at) * 1000.0, 3),
            "status": status,
        }
    )


def _ops_safe_slice(
    source: str,
    refs: Dict[str, Dict[str, Any]],
    source_errors: List[Dict[str, Any]],
    loader: Any,
    fallback: Any,
    *,
    path: str | None = None,
    source_timings: List[Dict[str, Any]] | None = None,
) -> Any:
    started_at = time.perf_counter()
    try:
        value = loader()
        _ops_record_source_timing(source_timings, source, started_at, "ok")
        return value
    except Exception as exc:  # noqa: BLE001 - operations lens must preserve partial visibility.
        logger.warning("operations lens source failed: %s", source, exc_info=True)
        _ops_record_source_error(refs, source_errors, source, exc, path=path)
        value = fallback() if callable(fallback) else copy.deepcopy(fallback)
        _ops_record_source_timing(source_timings, source, started_at, "failed")
        return value


def _ops_cache_path(repo_root: Path) -> Path:
    return repo_root / _OPERATIONS_LENS_CACHE_REL


def _ops_cache_age_seconds(payload: Mapping[str, Any] | None) -> int | None:
    if not payload:
        return None
    generated_at = payload.get("generated_at")
    parsed = _parse_iso_datetime(generated_at)
    if not parsed:
        return None
    return max(0, int((datetime.now(timezone.utc) - parsed).total_seconds()))


def _ops_cache_diagnostics(
    repo_root: Path,
    status: str,
    payload: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "generated_at": payload.get("generated_at") if isinstance(payload, Mapping) else None,
        "age_seconds": _ops_cache_age_seconds(payload),
        "path": _OPERATIONS_LENS_CACHE_REL if _ops_cache_path(repo_root).exists() else None,
    }


def _ops_slow_source_notes(source_timings: Sequence[Mapping[str, Any]]) -> List[str]:
    notes: List[str] = []
    for row in source_timings:
        duration_ms = row.get("duration_ms")
        if isinstance(duration_ms, (int, float)) and duration_ms >= _OPERATIONS_LENS_SLOW_SOURCE_MS:
            notes.append(f"{row.get('source') or 'unknown'} took {int(duration_ms)}ms.")
    return notes


def _ops_with_cache_diagnostics(
    repo_root: Path,
    payload: Mapping[str, Any],
    *,
    cache_status: str,
    mode: str | None = None,
    notes: Sequence[str] | None = None,
) -> Dict[str, Any]:
    row = copy.deepcopy(dict(payload))
    diagnostics = dict(row.get("diagnostics") or {})
    diagnostics["cache"] = _ops_cache_diagnostics(repo_root, cache_status, row)
    if mode is not None:
        diagnostics["mode"] = mode
    diagnostics.setdefault("source_errors", [])
    diagnostics.setdefault("source_timings", [])
    cache_note_prefixes = (
        "Served stale",
        "Served last-known-good",
        "Served operations lens snapshot after bounded",
        "Served materialized operations lens snapshot",
    )
    existing_notes = [
        str(note)
        for note in diagnostics.get("notes") or []
        if note and not str(note).startswith(cache_note_prefixes)
    ]
    for note in notes or []:
        if note and note not in existing_notes:
            existing_notes.append(str(note))
    diagnostics["notes"] = existing_notes
    row["diagnostics"] = diagnostics
    return row


def _ops_read_materialized_snapshot(repo_root: Path) -> Dict[str, Any] | None:
    path = _ops_cache_path(repo_root)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - cache corruption must not fail the route.
        logger.warning("operations lens materialized cache read failed: %s", exc)
        return None
    if not isinstance(payload, dict) or payload.get("schema") != "operations_lens_snapshot_v1":
        logger.warning("operations lens materialized cache ignored unexpected schema: %s", payload.get("schema") if isinstance(payload, dict) else type(payload).__name__)
        return None
    return payload


def _ops_write_materialized_snapshot(repo_root: Path, payload: Mapping[str, Any]) -> None:
    path = _ops_cache_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)


def _ops_store_memory_snapshot(repo_root: Path, payload: Mapping[str, Any]) -> None:
    cache_key = _snapshot_cache_key(repo_root)
    with _OPERATIONS_LENS_CACHE_LOCK:
        _OPERATIONS_LENS_MEMORY_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(dict(payload)))


def _ops_compute_and_store_snapshot(repo_root: Path) -> Dict[str, Any]:
    payload = load_operations_lens_snapshot(repo_root)
    _ops_store_memory_snapshot(repo_root, payload)
    try:
        _ops_write_materialized_snapshot(repo_root, payload)
    except Exception as exc:  # noqa: BLE001 - persistent cache failure should degrade diagnostics, not the projection.
        logger.warning("operations lens materialized cache write failed: %s", exc)
        diagnostics = dict(payload.get("diagnostics") or {})
        notes = [str(note) for note in diagnostics.get("notes") or [] if note]
        notes.append(f"operations lens materialized cache write failed: {_excerpt(str(exc), limit=180)}")
        diagnostics["notes"] = notes
        payload = {**payload, "diagnostics": diagnostics}
        _ops_store_memory_snapshot(repo_root, payload)
    return _ops_with_cache_diagnostics(repo_root, payload, cache_status="bypass")


def _ops_background_refresh(repo_root: Path, cache_key: str, event: Event) -> None:
    try:
        _ops_compute_and_store_snapshot(repo_root)
    except Exception as exc:  # pragma: no cover - defensive; live composer should self-degrade.
        logger.warning("operations lens background refresh failed: %s", exc)
    finally:
        with _OPERATIONS_LENS_CACHE_LOCK:
            _OPERATIONS_LENS_REFRESH_IN_FLIGHT.pop(cache_key, None)
        event.set()


def _ops_start_refresh(repo_root: Path) -> Event:
    cache_key = _snapshot_cache_key(repo_root)
    with _OPERATIONS_LENS_CACHE_LOCK:
        event = _OPERATIONS_LENS_REFRESH_IN_FLIGHT.get(cache_key)
        if event is not None:
            return event
        event = Event()
        _OPERATIONS_LENS_REFRESH_IN_FLIGHT[cache_key] = event
    Thread(
        target=_ops_background_refresh,
        args=(repo_root, cache_key, event),
        name="operations-lens-refresh",
        daemon=True,
    ).start()
    return event


def _ops_warming_snapshot(repo_root: Path, reason: str) -> Dict[str, Any]:
    generated = datetime.now(timezone.utc).isoformat()
    ref_id = "diagnostic:operations_lens_cache"
    message = f"operations_lens cache {reason}; background refresh is in flight."
    return {
        "schema": "operations_lens_snapshot_v1",
        "generated_at": generated,
        "freshness": {
            "status": "degraded",
            "age_seconds": None,
            "stale_sources": [
                {
                    "source": "operations_lens_cache",
                    "status": "miss",
                    "generated_at": None,
                    "age_seconds": None,
                    "label": message,
                }
            ],
            "source_count": 1,
        },
        "identity": {
            "family_id": None,
            "phase_id": None,
            "phase_number": None,
            "phase_title": None,
            "active_runtime_line": None,
            "active_driver": None,
            "next_handoff": None,
        },
        "summary": {
            "headline": f"DEGRADED / {message}",
            "status": "degraded",
            "operator_required": True,
            "primary_blocker_id": ref_id,
            "primary_blocker_label": message,
            "changed_since_last_seen": False,
        },
        "state_chain": {
            "phase_pipeline": [
                _ops_stage_node(
                    ref_id,
                    label="Operations lens cache warming",
                    kind="phase",
                    status="blocked",
                    evidence_refs=[ref_id],
                )
            ],
            "factory": [],
            "runtime": [],
            "closeout": [],
        },
        "bridge": {
            "status": "unknown",
            "nodes": [],
            "edges": [],
            "provider_count": 0,
            "live_provider_count": 0,
            "cdp_reachable": None,
            "browser_running": None,
        },
        "work_spine": {
            "status": "unknown",
            "counts": {"open": 0, "blocked": 0, "stale": 0, "claimed": 0, "unlinked": 0},
            "threads": [],
            "graph": {"nodes": [], "edges": []},
        },
        "cap_spine": {"status": "unknown", "caps": [], "graph": {"nodes": [], "edges": []}},
        "topology": {
            "nodes": [
                _ops_node(
                    ref_id,
                    label="Operations lens cache warming",
                    kind="source",
                    status="stale",
                    metadata={"evidence_refs": [ref_id]},
                )
            ],
            "edges": [],
        },
        "operator_attention": [
            {
                "id": ref_id,
                "severity": "p1",
                "kind": "freshness",
                "title": "Operations lens cache warming",
                "symptom": message,
                "why_it_matters": "SystemLens served a fast diagnostic snapshot instead of blocking the UI on live recomposition.",
                "current_state": reason,
                "required_human_decision": None,
                "related_node_ids": [ref_id],
                "evidence_refs": [ref_id],
            }
        ],
        "recent_events": [],
        "evidence_index": [
            {
                "id": ref_id,
                "kind": "runtime_snapshot",
                "label": "Operations lens cache",
                "path": _OPERATIONS_LENS_CACHE_REL,
                "excerpt": message,
                "freshness": "stale",
            }
        ],
        "diagnostics": {
            "mode": "failed",
            "fallback_from": None,
            "source_errors": [
                {
                    "source": "operations_lens_cache",
                    "status": "miss",
                    "message": message,
                    "path": _OPERATIONS_LENS_CACHE_REL,
                    "exception_type": "CacheMiss",
                }
            ],
            "source_timings": [
                {"source": "operations_lens_cache", "duration_ms": 0.0, "status": "skipped"}
            ],
            "cache": _ops_cache_diagnostics(repo_root, "miss", None),
            "notes": ["No last-known-good operations lens snapshot was available within the cold wait budget."],
        },
        "drilldowns": {
            "work_ledger": {"label": "Work lens", "href": "/station/intelligence?lens=work"},
            "phase_packet": {"label": "Phase", "href": "/station/phase"},
        },
    }


def _ops_degraded_freshness(
    freshness: Mapping[str, Any],
    source_errors: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    row = dict(freshness or {})
    stale_sources = [dict(source) for source in row.get("stale_sources") or [] if isinstance(source, Mapping)]
    existing = {str(source.get("source")) for source in stale_sources}
    for error in source_errors:
        source = str(error.get("source") or "unknown")
        if source not in existing:
            stale_sources.append(
                {
                    "source": source,
                    "status": str(error.get("status") or "failed"),
                    "generated_at": None,
                    "age_seconds": None,
                    "label": str(error.get("message") or "source failed"),
                }
            )
    if source_errors:
        row["status"] = "degraded"
    row["stale_sources"] = stale_sources
    row["source_count"] = max(int(row.get("source_count") or 0), len(stale_sources))
    row.setdefault("age_seconds", None)
    return row


def _ops_diagnostic_attention(
    refs: Dict[str, Dict[str, Any]],
    source_errors: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for error in source_errors[:4]:
        source = str(error.get("source") or "unknown")
        ref_id = f"diagnostic:{source}"
        if ref_id not in refs:
            _ops_evidence_ref(
                refs,
                ref_id,
                kind="runtime_snapshot",
                label=f"{source} source error",
                path=error.get("path"),
                excerpt=str(error.get("message") or "source failed"),
                freshness="stale",
            )
        items.append(
            {
                "id": ref_id,
                "severity": "p1",
                "kind": "freshness",
                "title": f"{source} unavailable",
                "symptom": f"{source} failed while composing operations lens.",
                "why_it_matters": "SystemLens is rendering a degraded partial observation snapshot from the sources that still loaded.",
                "current_state": str(error.get("message") or "source failed"),
                "required_human_decision": None,
                "related_node_ids": [ref_id],
                "evidence_refs": [ref_id],
            }
        )
    return items


def _ops_normalize_work_ref(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = value.get("td_id") or value.get("id") or value.get("ref")
    token = str(value or "").strip()
    if not token:
        return None
    match = re.search(r"\btd_[a-zA-Z0-9_]+\b", token)
    return match.group(0) if match else token


def _ops_freshness(source_generated_at: Mapping[str, Any]) -> Dict[str, Any]:
    stale_sources: List[Dict[str, Any]] = []
    worst = "live"
    for source, generated_at in source_generated_at.items():
        fresh = compute_freshness(generated_at)
        tone = str(fresh.get("tone") or "unknown")
        if tone in {"stale", "expired", "missing", "unknown"}:
            stale_sources.append(
                {
                    "source": source,
                    "status": tone,
                    "generated_at": generated_at,
                    "age_seconds": fresh.get("age_seconds"),
                    "label": fresh.get("label"),
                }
            )
        if tone in {"expired", "missing"}:
            worst = "degraded"
        elif tone == "stale" and worst == "live":
            worst = "stale"
        elif tone == "unknown" and worst == "live":
            worst = "unknown"
    return {
        "status": worst,
        "age_seconds": None,
        "stale_sources": stale_sources,
        "source_count": len(source_generated_at),
    }


def _ops_state_chain(
    system: Mapping[str, Any],
    refs: Dict[str, Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    phase = system.get("phase") if isinstance(system.get("phase"), Mapping) else {}
    pipeline = phase.get("pipeline_state") if isinstance(phase.get("pipeline_state"), Mapping) else {}
    factory = system.get("factory") if isinstance(system.get("factory"), Mapping) else {}
    orchestration = system.get("orchestration") if isinstance(system.get("orchestration"), Mapping) else {}
    gate = orchestration.get("gate") if isinstance(orchestration.get("gate"), Mapping) else {}
    driver = orchestration.get("active_driver_record") if isinstance(orchestration.get("active_driver_record"), Mapping) else {}
    phase_ref = _ops_evidence_ref(
        refs,
        "phase_packet",
        kind="phase_packet",
        label="Active phase packet",
        href=_safe_internal_route(phase.get("route"), "/station/phase"),
        freshness=str((phase.get("freshness") or {}).get("tone") or "unknown") if isinstance(phase.get("freshness"), Mapping) else None,
    )
    factory_ref = _ops_evidence_ref(
        refs,
        "factory_state",
        kind="runtime_snapshot",
        label="Factory state",
        path=str(factory.get("source_path") or FACTORY_STATE_PATH),
    )
    orchestration_ref = _ops_evidence_ref(
        refs,
        "orchestration_state",
        kind="runtime_snapshot",
        label="Orchestration state",
        path=ORCHESTRATION_STATE_PATH,
    )
    gate_active = bool(gate.get("active"))
    phase_failed = bool(pipeline.get("stage_error"))
    factory_failed = bool(factory.get("stage_error"))
    factory_error = factory.get("stage_error") if isinstance(factory.get("stage_error"), Mapping) else {}
    last_successful_stage = str(factory_error.get("last_successful_stage") or "").strip()
    current_factory_stage = str(factory.get("stage") or factory_error.get("stage") or "factory stage unknown")
    active_driver_id = str(orchestration.get("active_driver") or "none")
    runtime = driver.get("runtime") if isinstance(driver.get("runtime"), Mapping) else {}
    current_operation = runtime.get("current_operation") if isinstance(runtime.get("current_operation"), Mapping) else {}
    awaiting_barriers = runtime.get("awaiting_barriers") if isinstance(runtime.get("awaiting_barriers"), list) else []
    phase_id = str(phase.get("id") or "unknown")

    phase_nodes = [
        _ops_stage_node(
            f"phase:{phase_id}",
            label=str(phase.get("title") or phase.get("id") or "Active phase"),
            kind="phase",
            status=_ops_status(
                blocked=bool(pipeline.get("blocked")),
                failed=phase_failed,
                stale=str((phase.get("freshness") or {}).get("tone") or "") == "stale"
                if isinstance(phase.get("freshness"), Mapping)
                else False,
                active=True,
            ),
            updated_at=pipeline.get("updated_at"),
            blocker_ids=["factory:stage"] if factory_failed else [],
            evidence_refs=[phase_ref],
        ),
        _ops_stage_node(
            f"phase:{phase_id}:pipeline",
            label=str(pipeline.get("stage") or "phase pipeline"),
            kind="phase",
            status=_ops_status(
                blocked=bool(pipeline.get("blocked")),
                failed=phase_failed,
                active=bool(pipeline.get("stage") or phase.get("id")),
            ),
            updated_at=pipeline.get("updated_at"),
            blocker_ids=["factory:stage"] if factory_failed else [],
            evidence_refs=[phase_ref],
        ),
    ]

    factory_nodes: List[Dict[str, Any]] = []
    if last_successful_stage and last_successful_stage != current_factory_stage:
        factory_nodes.append(
            _ops_stage_node(
                f"factory:{last_successful_stage}",
                label=last_successful_stage,
                kind="factory_stage",
                status="done",
                updated_at=factory.get("last_run"),
                evidence_refs=[factory_ref],
            )
        )
    factory_nodes.append(
        _ops_stage_node(
            "factory:stage",
            label=current_factory_stage,
            kind="factory_stage",
            status=_ops_status(
                blocked=bool(factory.get("blocked")),
                failed=factory_failed,
                active=bool(factory.get("stage") or factory_error.get("stage")),
            ),
            updated_at=factory.get("last_stage_apply") or factory.get("last_run"),
            evidence_refs=[factory_ref],
        )
    )

    runtime_nodes = [
        _ops_stage_node(
            f"runtime:{active_driver_id}",
            label=str(driver.get("label") or orchestration.get("active_driver") or "no active runtime"),
            kind="runtime",
            status=_ops_status(
                blocked=bool(driver.get("blocked") or gate_active),
                active=bool(orchestration.get("active_driver")),
            ),
            updated_at=orchestration.get("updated_at"),
            blocker_ids=["orchestration:gate"] if gate_active else [],
            evidence_refs=[orchestration_ref],
        )
    ]
    operation_id = str(current_operation.get("id") or "").strip()
    if operation_id:
        runtime_nodes.append(
            _ops_stage_node(
                f"runtime:{active_driver_id}:operation:{operation_id}",
                label=str(current_operation.get("label") or operation_id),
                kind="runtime",
                status=_ops_status(
                    blocked=bool(driver.get("blocked") or gate_active),
                    active=True,
                ),
                updated_at=orchestration.get("updated_at"),
                blocker_ids=["orchestration:gate"] if gate_active else [],
                evidence_refs=[orchestration_ref],
            )
        )
    for barrier in awaiting_barriers[:2]:
        if not isinstance(barrier, Mapping):
            continue
        barrier_id = str(barrier.get("operation_id") or barrier.get("reaction_id") or len(runtime_nodes)).strip()
        runtime_nodes.append(
            _ops_stage_node(
                f"runtime:{active_driver_id}:barrier:{barrier_id}",
                label=str(barrier.get("label") or barrier_id or "runtime barrier"),
                kind="runtime",
                status=_ops_status(blocked=True, active=True),
                updated_at=orchestration.get("updated_at"),
                blocker_ids=["orchestration:gate"] if gate_active else [],
                evidence_refs=[orchestration_ref],
            )
        )

    return {
        "phase_pipeline": phase_nodes,
        "factory": factory_nodes,
        "runtime": runtime_nodes,
        "closeout": [
            _ops_stage_node(
                "orchestration:gate",
                label=str(gate.get("gate_reason") or ("gate active" if gate_active else "gate open")),
                kind="closeout",
                status=_ops_status(blocked=gate_active, active=gate_active),
                updated_at=orchestration.get("updated_at"),
                evidence_refs=[orchestration_ref],
            )
        ],
    }


def _ops_bridge_slice(attention: Mapping[str, Any], refs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    bridge = attention.get("bridge_health") if isinstance(attention.get("bridge_health"), Mapping) else {}
    providers = [str(provider) for provider in bridge.get("providers") or [] if provider]
    alive = bridge.get("alive")
    cdp_reachable = bridge.get("cdp_reachable")
    browser_status = "ok" if alive is True else "failed" if alive is False else "unknown"
    cdp_status = "ok" if cdp_reachable is True else "failed" if cdp_reachable is False else "unknown"
    overall = "down" if alive is False or cdp_reachable is False else "up" if alive is True else "unknown"
    bridge_ref = _ops_evidence_ref(
        refs,
        "bridge_diagnostics",
        kind="runtime_snapshot",
        label="Bridge diagnostics",
        excerpt=str(bridge.get("error") or bridge.get("stale_reason") or "bridge health projection"),
    )
    nodes = [
        _ops_node(
            "bridge:browser",
            label="Browser bridge",
            kind="bridge",
            status=browser_status,
            metadata={"alive": alive, "evidence_refs": [bridge_ref]},
        ),
        _ops_node(
            "bridge:cdp",
            label="CDP transport",
            kind="bridge",
            status=cdp_status,
            metadata={"cdp_reachable": cdp_reachable, "evidence_refs": [bridge_ref]},
        ),
    ]
    edges = [_ops_edge("bridge:browser->cdp", "bridge:browser", "bridge:cdp", kind="connected_to", status=cdp_status)]
    for provider in providers:
        node_id = f"bridge:provider:{provider}"
        nodes.append(
            _ops_node(
                node_id,
                label=provider,
                kind="bridge",
                status="ok" if overall == "up" else overall,
                metadata={"evidence_refs": [bridge_ref]},
            )
        )
        edges.append(_ops_edge(f"bridge:cdp->{provider}", "bridge:cdp", node_id, kind="connected_to", status=overall))
    return {
        "status": overall,
        "nodes": nodes,
        "edges": edges,
        "provider_count": len(providers),
        "live_provider_count": len(providers) if overall == "up" else 0,
        "cdp_reachable": cdp_reachable,
        "browser_running": alive,
    }


def _ops_work_thread(row: Mapping[str, Any], evidence_refs: Sequence[str]) -> Dict[str, Any]:
    td_id = str(row.get("td_id") or row.get("id") or "").strip()
    status = str(row.get("status") or "unknown")
    return {
        "td_id": td_id,
        "title": str(row.get("title") or td_id or "Untitled work thread"),
        "state": status,
        "owner": row.get("actor"),
        "phase_id": row.get("phase_id"),
        "claim_ref": None,
        "age_seconds": row.get("age_seconds"),
        "last_event_at": row.get("last_event_at"),
        "last_event_label": row.get("last_event_kind"),
        "blockers": [row.get("blocker_summary")] if row.get("blocker_summary") else [],
        "supersedes": [],
        "superseded_by": [],
        "linked_caps": [],
        "linked_attention_items": [],
        "evidence_refs": list(evidence_refs),
    }


def _ops_work_spine(
    work: Mapping[str, Any],
    refs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    work_ref = _ops_evidence_ref(
        refs,
        "work_ledger_projection",
        kind="ledger_event",
        label="Work ledger projection",
        path=str(work.get("index_path") or "codex/ledger/<phase>/work_ledger_index.json"),
        freshness=str((work.get("freshness") or {}).get("tone") or "unknown") if isinstance(work.get("freshness"), Mapping) else None,
    )
    rows: List[Mapping[str, Any]] = []
    seen: set[str] = set()
    for bucket in ("top_stale", "top_in_progress", "top_recent_open"):
        for row in work.get(bucket) or []:
            if not isinstance(row, Mapping):
                continue
            td_id = str(row.get("td_id") or row.get("id") or f"anon:{len(rows)}")
            if td_id in seen:
                continue
            seen.add(td_id)
            rows.append(row)
    threads = [_ops_work_thread(row, [work_ref]) for row in rows[:12]]
    nodes = [
        _ops_node(
            f"work:{thread['td_id']}",
            label=str(thread["title"]),
            kind="work_thread",
            status=str(thread["state"]),
            weight=1,
            metadata={
                "td_id": thread["td_id"],
                "owner": thread.get("owner"),
                "phase_id": thread.get("phase_id"),
                "evidence_refs": thread["evidence_refs"],
            },
        )
        for thread in threads
        if thread.get("td_id")
    ]
    edges: List[Dict[str, Any]] = []
    for thread in threads:
        td_id = thread.get("td_id")
        phase_id = thread.get("phase_id")
        if td_id and phase_id:
            edges.append(
                _ops_edge(
                    f"phase:{phase_id}->work:{td_id}",
                    f"phase:{phase_id}",
                    f"work:{td_id}",
                    kind="produces",
                    label="phase work",
                )
            )
    counts = dict(work.get("counts") or {})
    status = "stale" if int(counts.get("stale") or counts.get("stale_open") or 0) > 0 else "clear"
    return {
        "status": status,
        "counts": {
            "open": int(counts.get("open") or counts.get("open_threads") or 0),
            "blocked": int(counts.get("blocked") or 0),
            "stale": int(counts.get("stale") or counts.get("stale_open") or 0),
            "claimed": int(counts.get("claimed") or counts.get("active_claims") or 0),
            "unlinked": int(counts.get("unlinked") or 0),
        },
        "threads": threads,
        "graph": {"nodes": nodes, "edges": edges},
    }


def _ops_cap_candidates(repo_root: Path, *, limit: int = 14) -> List[Mapping[str, Any]]:
    ledger = _safe_read_json(repo_root, "state/task_ledger/ledger.json") or {}
    work_items = _task_ledger_view_items(ledger)
    wanted_ids = {
        "cap_operations_lens_v1_2_availability_contract",
        "cap_operations_lens_v1_1_topology_closeout",
        "cap_system_lens_operations_absorbs_cockpit_read_only_topology",
    }
    live_states = {
        "active",
        "blocked",
        "captured",
        "claim",
        "claimed",
        "execution",
        "in_progress",
        "open",
        "ready",
        "shaping",
    }

    def score(item: Mapping[str, Any]) -> tuple[int, str]:
        item_id = str(item.get("id") or item.get("subject_id") or "")
        state = str(item.get("state") or item.get("status") or "").lower()
        dep_status = item.get("dependency_status") if isinstance(item.get("dependency_status"), Mapping) else {}
        execution = item.get("execution") if isinstance(item.get("execution"), Mapping) else {}
        dependencies = _str_list(item.get("depends_on")) or _str_list(item.get("dependencies"))
        downstream = _str_list(dep_status.get("downstream_unlock_ids"))
        work_refs = [_ops_normalize_work_ref(ref) for ref in _str_list(item.get("work_ledger_refs"))]
        work_refs = [ref for ref in work_refs if ref]
        points = 0
        if item_id in wanted_ids:
            points += 1000
        if state in live_states:
            points += 90
        if work_refs:
            points += 85
        if execution.get("phase_id"):
            points += 60
        if downstream:
            points += 55
        if dependencies:
            points += 35
        if item_id.startswith(("cap_", "task_")):
            points += 10
        updated_age = _age_seconds(item.get("updated_at") or item.get("created_at"))
        if updated_age is not None and updated_age <= 7 * 24 * 60 * 60:
            points += 25
        rank = item.get("rank")
        if isinstance(rank, (int, float)):
            points += max(0, 80 - int(rank))
        return points, item_id

    scored = [(score(item), item) for item in work_items if isinstance(item, Mapping)]
    filtered = [(s, item) for s, item in scored if s[0] > 0]
    filtered.sort(key=lambda pair: (-pair[0][0], pair[0][1]))
    return [item for _score, item in filtered[:limit]]


def _ops_cap_node(item: Mapping[str, Any], evidence_refs: Sequence[str]) -> Dict[str, Any]:
    item_id = str(item.get("id") or item.get("subject_id") or "").strip()
    contracts = item.get("contracts") if isinstance(item.get("contracts"), Mapping) else {}
    completion = item.get("completion") if isinstance(item.get("completion"), Mapping) else {}
    execution = item.get("execution") if isinstance(item.get("execution"), Mapping) else {}
    dependencies = _str_list(item.get("depends_on")) or _str_list(item.get("dependencies")) or _str_list(contracts.get("dependencies"))
    downstream = []
    dep_status = item.get("dependency_status") if isinstance(item.get("dependency_status"), Mapping) else {}
    downstream.extend(_str_list(dep_status.get("downstream_unlock_ids")))
    linked_work_threads = [
        ref
        for ref in (_ops_normalize_work_ref(raw_ref) for raw_ref in _str_list(item.get("work_ledger_refs")))
        if ref
    ]
    rank = item.get("rank")
    return {
        "cap_id": item_id,
        "title": str(item.get("title") or item_id or "Untitled cap"),
        "state": str(item.get("state") or item.get("status") or "unknown"),
        "lane": item.get("lane") or execution.get("route"),
        "priority": int(rank) if isinstance(rank, (int, float)) else None,
        "age_seconds": _age_seconds(item.get("updated_at") or item.get("created_at")),
        "dependency_ids": dependencies[:12],
        "downstream_unlock_ids": downstream[:12],
        "linked_work_threads": linked_work_threads[:12],
        "linked_phase_id": execution.get("phase_id"),
        "satisfaction_summary": _excerpt(completion.get("closure_condition") or item.get("statement") or item.get("claim"), limit=220),
        "evidence_refs": list(evidence_refs),
    }


def _ops_cap_spine(
    repo_root: Path,
    refs: Dict[str, Dict[str, Any]],
    *,
    work_thread_ids: Sequence[str] | None = None,
) -> Dict[str, Any]:
    task_ref = _ops_evidence_ref(
        refs,
        "task_ledger_projection",
        kind="task_ledger_item",
        label="Task Ledger projection",
        path="state/task_ledger/ledger.json",
        freshness=str(compute_freshness(_file_mtime(repo_root, "state/task_ledger/ledger.json")).get("tone") or "unknown"),
    )
    caps = [_ops_cap_node(item, [task_ref]) for item in _ops_cap_candidates(repo_root)]
    work_ids = {str(td_id) for td_id in (work_thread_ids or []) if str(td_id).strip()}
    nodes = [
        _ops_node(
            f"cap:{cap['cap_id']}",
            label=str(cap["title"]),
            kind="cap",
            status=str(cap["state"]),
            weight=1,
            metadata={
                "cap_id": cap["cap_id"],
                "lane": cap.get("lane"),
                "priority": cap.get("priority"),
                "evidence_refs": cap["evidence_refs"],
            },
        )
        for cap in caps
        if cap.get("cap_id")
    ]
    edges: List[Dict[str, Any]] = []
    cap_ids = {str(cap.get("cap_id")) for cap in caps}
    external_work_nodes: Dict[str, Dict[str, Any]] = {}
    for cap in caps:
        cap_id = str(cap.get("cap_id") or "")
        for dep_id in cap.get("dependency_ids") or []:
            target = f"cap:{dep_id}" if dep_id in cap_ids else f"external:{dep_id}"
            edges.append(_ops_edge(f"cap:{dep_id}->cap:{cap_id}", target, f"cap:{cap_id}", kind="depends_on", label="depends on"))
        for unlock_id in cap.get("downstream_unlock_ids") or []:
            target = f"cap:{unlock_id}" if unlock_id in cap_ids else f"external:{unlock_id}"
            edges.append(_ops_edge(f"cap:{cap_id}->cap:{unlock_id}", f"cap:{cap_id}", target, kind="blocks", label="unlocks"))
        for td_id in cap.get("linked_work_threads") or []:
            if not cap_id or not td_id:
                continue
            target = f"work:{td_id}" if str(td_id) in work_ids else f"external_work:{td_id}"
            if target.startswith("external_work:") and target not in external_work_nodes:
                external_work_nodes[target] = _ops_node(
                    target,
                    label=str(td_id),
                    kind="work_thread",
                    status="unknown",
                    metadata={"external": True, "evidence_refs": cap.get("evidence_refs") or []},
                )
            edges.append(
                _ops_edge(
                    f"cap:{cap_id}->work:{td_id}",
                    f"cap:{cap_id}",
                    target,
                    kind="evidence_for",
                    label="linked work",
                )
            )
    nodes.extend(external_work_nodes.values())
    status = "blocked" if any(str(cap.get("state") or "").lower() == "blocked" for cap in caps) else "watch" if caps else "unknown"
    return {
        "status": status,
        "caps": caps,
        "graph": {"nodes": nodes, "edges": edges},
    }


def _ops_attention(
    attention: Mapping[str, Any],
    refs: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    attention_ref = _ops_evidence_ref(
        refs,
        "attention_snapshot",
        kind="runtime_snapshot",
        label="Attention snapshot",
        href="/api/world-model/attention",
        freshness=str(compute_freshness(attention.get("generated_at")).get("tone") or "unknown"),
    )
    items = []
    for raw in list(attention.get("attention_items") or [])[:8]:
        if not isinstance(raw, Mapping):
            continue
        score = int(raw.get("score") or 0)
        kind = str(raw.get("kind") or "symptom")
        severity = "p0" if score >= 120 else "p1" if score >= 85 else "p2" if score >= 45 else "p3"
        related = [f"attention:{raw.get('id') or kind}"]
        if kind == "work_ledger":
            related.append("work:spine")
        elif kind in {"gate", "driver_block"}:
            related.append("orchestration:gate")
        elif kind == "drift":
            related.append("drift:aggregate")
        items.append(
            {
                "id": str(raw.get("id") or kind),
                "severity": severity,
                "kind": kind if kind in {"blocker", "stale_work", "bridge", "factory", "phase", "cap", "ledger", "freshness"} else "symptom",
                "title": str(raw.get("title") or raw.get("detail") or "Attention item"),
                "symptom": str(raw.get("title") or "Attention item"),
                "why_it_matters": str(raw.get("detail") or "Backend attention snapshot marked this row as operator-relevant."),
                "current_state": str(raw.get("owner") or raw.get("kind") or "unknown"),
                "required_human_decision": "Review the linked evidence." if kind in {"gate", "driver_block"} else None,
                "related_node_ids": related,
                "evidence_refs": [attention_ref],
            }
        )
    return items


def _ops_recent_events(system: Mapping[str, Any], attention: Mapping[str, Any], refs: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    events_ref = _ops_evidence_ref(
        refs,
        "orchestration_events",
        kind="runtime_snapshot",
        label="Orchestration events",
        path=ORCHESTRATION_EVENTS_PATH,
    )
    rows: List[Dict[str, Any]] = []
    for raw in list(system.get("recent_transitions") or [])[:10]:
        if not isinstance(raw, Mapping):
            continue
        rows.append(
            {
                "id": f"{raw.get('kind') or 'event'}:{raw.get('subject_id') or raw.get('when') or len(rows)}",
                "at": raw.get("when"),
                "kind": raw.get("kind") or "handoff",
                "label": str(raw.get("subject_label") or raw.get("to_state") or raw.get("kind") or "state changed"),
                "node_ids": [str(raw.get("subject_id"))] if raw.get("subject_id") else [],
                "evidence_refs": [events_ref],
            }
        )
    for raw in list(attention.get("recent_changes") or [])[:5]:
        if not isinstance(raw, Mapping):
            continue
        rows.append(
            {
                "id": str(raw.get("event_id") or f"attention:{len(rows)}"),
                "at": raw.get("recorded_at"),
                "kind": "attention_change",
                "label": str(raw.get("summary") or raw.get("gate_reason") or "attention changed"),
                "node_ids": [],
                "evidence_refs": [events_ref],
            }
        )
    rows.sort(key=lambda row: _parse_iso_datetime(row.get("at")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return rows[:12]


def _ops_combined_topology(
    state_chain: Mapping[str, Sequence[Mapping[str, Any]]],
    bridge: Mapping[str, Any],
    work_spine: Mapping[str, Any],
    cap_spine: Mapping[str, Any],
    operator_attention: Sequence[Mapping[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    nodes: List[Mapping[str, Any]] = []
    edges: List[Mapping[str, Any]] = []

    for lane_id, stages in state_chain.items():
        stage_rows = [stage for stage in stages if isinstance(stage, Mapping)]
        nodes.extend(_ops_stage_graph_node(stage) for stage in stage_rows)
        edges.extend(_ops_chain_edges(str(lane_id), stage_rows))

    nodes.append(
        _ops_node(
            "work:spine",
            label="Work spine",
            kind="work_thread",
            status=str(work_spine.get("status") or "unknown"),
            metadata={"aggregate": True},
        )
    )
    nodes.append(
        _ops_node(
            "cap:spine",
            label="Cap spine",
            kind="cap",
            status=str(cap_spine.get("status") or "unknown"),
            metadata={"aggregate": True},
        )
    )

    bridge_nodes = bridge.get("nodes") if isinstance(bridge.get("nodes"), list) else []
    bridge_edges = bridge.get("edges") if isinstance(bridge.get("edges"), list) else []
    work_graph = work_spine.get("graph") if isinstance(work_spine.get("graph"), Mapping) else {}
    cap_graph = cap_spine.get("graph") if isinstance(cap_spine.get("graph"), Mapping) else {}
    nodes.extend(node for node in bridge_nodes if isinstance(node, Mapping))
    edges.extend(edge for edge in bridge_edges if isinstance(edge, Mapping))
    nodes.extend(node for node in work_graph.get("nodes") or [] if isinstance(node, Mapping))
    edges.extend(edge for edge in work_graph.get("edges") or [] if isinstance(edge, Mapping))
    nodes.extend(node for node in cap_graph.get("nodes") or [] if isinstance(node, Mapping))
    edges.extend(edge for edge in cap_graph.get("edges") or [] if isinstance(edge, Mapping))

    for item in operator_attention:
        if not isinstance(item, Mapping):
            continue
        attention_id = f"attention:{item.get('id') or len(nodes)}"
        severity = str(item.get("severity") or "unknown")
        nodes.append(
            _ops_node(
                attention_id,
                label=str(item.get("title") or item.get("id") or "Attention item"),
                kind="attention",
                status="failed" if severity in {"p0", "p1"} else "watch",
                metadata={"severity": severity, "evidence_refs": list(item.get("evidence_refs") or [])},
            )
        )
        related_ids = [ref for ref in _str_list(item.get("related_node_ids")) if ref != attention_id]
        if not related_ids:
            edges.append(
                _ops_edge(
                    f"{attention_id}->work:spine",
                    attention_id,
                    "work:spine",
                    kind="evidence_for",
                    label="attention context",
                    status=severity,
                )
            )
            continue
        for related_id in related_ids:
            edges.append(
                _ops_edge(
                    f"{attention_id}->{related_id}",
                    attention_id,
                    related_id,
                    kind="evidence_for",
                    label="attention context",
                    status=severity,
                )
            )

    return _ops_dedupe_graph(nodes, edges)


def load_operations_lens_snapshot(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Compose the read-only operations topology consumed by SystemLens
      after Cockpit's control-oriented Pass-1 surface is demoted.
    - Mechanism: Reuses SystemLens, attention, Work Ledger, and Task Ledger
      projections, then normalizes them into state chains, graph nodes, graph
      edges, attention symptoms, recent events, and evidence refs.
    - Guarantee: Returns additive `operations_lens_snapshot_v1`; individual
      source failures degrade the snapshot with diagnostics instead of blanking
      the read-only observation surface. Primary `operator_attention` rows
      intentionally omit executable command fields.
    """
    generated = datetime.now(timezone.utc).isoformat()
    refs: Dict[str, Dict[str, Any]] = {}
    source_errors: List[Dict[str, Any]] = []
    source_timings: List[Dict[str, Any]] = []

    system = _ops_safe_slice(
        "system_lens_projection",
        refs,
        source_errors,
        lambda: load_system_lens_projection(repo_root),
        {},
        path="system/server/world_model.py::load_system_lens_projection",
        source_timings=source_timings,
    )
    attention = _ops_safe_slice(
        "attention_snapshot",
        refs,
        source_errors,
        lambda: load_attention_snapshot(repo_root),
        {},
        path="/api/world-model/attention",
        source_timings=source_timings,
    )
    work = _ops_safe_slice(
        "work_ledger_overview",
        refs,
        source_errors,
        lambda: load_work_ledger_overview(repo_root),
        {
            "counts": {},
            "top_stale": [],
            "top_in_progress": [],
            "top_recent_open": [],
            "index_path": "codex/ledger/<phase>/work_ledger_index.json",
        },
        path="codex/ledger/<phase>/work_ledger_index.json",
        source_timings=source_timings,
    )

    state_chain = _ops_safe_slice(
        "state_chain",
        refs,
        source_errors,
        lambda: _ops_state_chain(system, refs),
        lambda: _ops_state_chain({}, refs),
        source_timings=source_timings,
    )
    bridge = _ops_safe_slice(
        "bridge",
        refs,
        source_errors,
        lambda: _ops_bridge_slice(attention, refs),
        {
            "status": "unknown",
            "nodes": [],
            "edges": [],
            "provider_count": 0,
            "live_provider_count": 0,
            "cdp_reachable": None,
            "browser_running": None,
        },
        path="/api/world-model/attention::bridge_health",
        source_timings=source_timings,
    )
    work_spine = _ops_safe_slice(
        "work_spine",
        refs,
        source_errors,
        lambda: _ops_work_spine(work, refs),
        {
            "status": "unknown",
            "counts": {"open": 0, "blocked": 0, "stale": 0, "claimed": 0, "unlinked": 0},
            "threads": [],
            "graph": {"nodes": [], "edges": []},
        },
        path="codex/ledger/<phase>/work_ledger_index.json",
        source_timings=source_timings,
    )
    work_thread_ids = [str(thread.get("td_id")) for thread in work_spine.get("threads") or [] if thread.get("td_id")]
    cap_spine = _ops_safe_slice(
        "task_ledger_caps",
        refs,
        source_errors,
        lambda: _ops_cap_spine(repo_root, refs, work_thread_ids=work_thread_ids),
        {"status": "unknown", "caps": [], "graph": {"nodes": [], "edges": []}},
        path="state/task_ledger/ledger.json",
        source_timings=source_timings,
    )
    operator_attention = _ops_safe_slice(
        "operator_attention",
        refs,
        source_errors,
        lambda: _ops_attention(attention, refs),
        [],
        path="/api/world-model/attention::attention_items",
        source_timings=source_timings,
    )
    if source_errors:
        operator_attention = _ops_diagnostic_attention(refs, source_errors) + list(operator_attention or [])
    recent_events = _ops_safe_slice(
        "recent_events",
        refs,
        source_errors,
        lambda: _ops_recent_events(system, attention, refs),
        [],
        path="tools/meta/control/orchestration_events.jsonl",
        source_timings=source_timings,
    )
    topology = _ops_safe_slice(
        "combined_topology",
        refs,
        source_errors,
        lambda: _ops_combined_topology(state_chain, bridge, work_spine, cap_spine, operator_attention),
        {"nodes": [], "edges": []},
        source_timings=source_timings,
    )

    phase = system.get("phase") if isinstance(system.get("phase"), Mapping) else {}
    factory = system.get("factory") if isinstance(system.get("factory"), Mapping) else {}
    orchestration = system.get("orchestration") if isinstance(system.get("orchestration"), Mapping) else {}
    gate = orchestration.get("gate") if isinstance(orchestration.get("gate"), Mapping) else {}
    source_generated_at = system.get("source_generated_at") if isinstance(system.get("source_generated_at"), Mapping) else {}
    source_errors_final = list(source_errors)
    primary_attention = operator_attention[0] if operator_attention else None
    failed_factory = bool(factory.get("stage_error"))
    gate_active = bool(gate.get("active"))
    blocked = failed_factory or gate_active or work_spine.get("status") in {"blocked", "stale"}
    headline = (
        str(primary_attention.get("title"))
        if primary_attention
        else f"DEGRADED / {len(source_errors_final)} operations source failed."
        if source_errors_final
        else "System operations topology is clear."
    )
    primary_blocker = None
    if failed_factory:
        primary_blocker = "factory:stage"
    elif gate_active:
        primary_blocker = "orchestration:gate"
    elif primary_attention:
        primary_blocker = str(primary_attention.get("id"))
    elif source_errors_final:
        primary_blocker = f"diagnostic:{source_errors_final[0].get('source') or 'operations_lens'}"

    freshness = _ops_degraded_freshness(_ops_freshness(source_generated_at), source_errors_final)
    summary_status = "failed" if failed_factory else "blocked" if blocked else "degraded" if source_errors_final else "clear"
    diagnostic_notes = ["Rendered partial operations lens snapshot after source failure."] if source_errors_final else []
    diagnostic_notes.extend(_ops_slow_source_notes(source_timings))

    return {
        "schema": "operations_lens_snapshot_v1",
        "generated_at": generated,
        "freshness": freshness,
        "identity": {
            "family_id": (work.get("family_id") or "09"),
            "phase_id": phase.get("id"),
            "phase_number": str(phase.get("id") or "").replace("_", ".") if phase.get("id") else None,
            "phase_title": phase.get("title"),
            "active_runtime_line": orchestration.get("active_driver"),
            "active_driver": orchestration.get("active_driver"),
            "next_handoff": (attention.get("next_handoff") or {}).get("actor_id")
            if isinstance(attention.get("next_handoff"), Mapping)
            else None,
        },
        "summary": {
            "headline": headline,
            "status": summary_status,
            "operator_required": bool(operator_attention or source_errors_final),
            "primary_blocker_id": primary_blocker,
            "primary_blocker_label": headline if primary_blocker else None,
            "changed_since_last_seen": False,
        },
        "state_chain": state_chain,
        "bridge": bridge,
        "work_spine": work_spine,
        "cap_spine": cap_spine,
        "topology": topology,
        "operator_attention": operator_attention,
        "recent_events": recent_events,
        "evidence_index": list(refs.values()),
        "diagnostics": {
            "mode": "degraded" if source_errors_final else "primary",
            "fallback_from": None,
            "source_errors": source_errors_final,
            "source_timings": source_timings,
            "cache": _ops_cache_diagnostics(repo_root, "bypass"),
            "notes": diagnostic_notes,
        },
        "drilldowns": {
            "raw_trace": {"label": "Legacy raw trace", "href": "/station/agent-observability", "legacy": True},
            "agent_diagnostics": {"label": "Agent observability", "href": "/station/agent-observability"},
            "work_ledger": {"label": "Work lens", "href": "/station/intelligence?lens=work"},
            "task_ledger": {"label": "Task ledger", "href": "/station/ledger"},
            "phase_packet": {"label": "Phase", "href": _safe_internal_route(phase.get("route"), "/station/phase")},
            "vantage": {"label": "Vantage", "href": "/station/vantage"},
        },
    }


def load_operations_lens_snapshot_cached(repo_root: Path, *, refresh: bool = False) -> Dict[str, Any]:
    """
    Serve the hot SystemLens operations route without synchronously rebuilding
    every topology source on ordinary page load.
    """
    if refresh:
        return _ops_compute_and_store_snapshot(repo_root)

    cache_key = _snapshot_cache_key(repo_root)
    now = time.monotonic()
    with _OPERATIONS_LENS_CACHE_LOCK:
        cached = _OPERATIONS_LENS_MEMORY_CACHE.get(cache_key)
        if cached is not None:
            age = now - cached[0]
            payload = copy.deepcopy(cached[1])
            payload_age_seconds = _ops_cache_age_seconds(payload)
            payload_fresh = payload_age_seconds is None or payload_age_seconds <= int(_OPERATIONS_LENS_CACHE_TTL_S)
            if age <= _OPERATIONS_LENS_CACHE_TTL_S and payload_fresh:
                return _ops_with_cache_diagnostics(repo_root, payload, cache_status="fresh", mode="cached")
            return _ops_with_cache_diagnostics(
                repo_root,
                payload,
                cache_status="stale",
                mode="cached",
                notes=["Served stale in-memory operations lens snapshot. Use refresh=1 or startup prewarm to recompute."],
            )

    materialized = _ops_read_materialized_snapshot(repo_root)
    if materialized is not None:
        _ops_store_memory_snapshot(repo_root, materialized)
        age_seconds = _ops_cache_age_seconds(materialized)
        cache_status = "fresh" if age_seconds is not None and age_seconds <= int(_OPERATIONS_LENS_CACHE_TTL_S) else "stale"
        return _ops_with_cache_diagnostics(
            repo_root,
            materialized,
            cache_status=cache_status,
            mode="cached",
            notes=["Served last-known-good materialized operations lens snapshot; refresh=1 recomposes it."]
            if cache_status == "stale"
            else [],
        )

    event = _ops_start_refresh(repo_root)
    event.wait(timeout=_OPERATIONS_LENS_COLD_WAIT_S)
    with _OPERATIONS_LENS_CACHE_LOCK:
        cached = _OPERATIONS_LENS_MEMORY_CACHE.get(cache_key)
        if cached is not None:
            return _ops_with_cache_diagnostics(
                repo_root,
                copy.deepcopy(cached[1]),
                cache_status="fresh",
                mode="cached",
                notes=["Served operations lens snapshot after bounded cold wait."],
            )
    materialized = _ops_read_materialized_snapshot(repo_root)
    if materialized is not None:
        _ops_store_memory_snapshot(repo_root, materialized)
        return _ops_with_cache_diagnostics(
            repo_root,
            materialized,
            cache_status="stale",
            mode="cached",
            notes=["Served materialized operations lens snapshot after bounded cold wait."],
        )
    return _ops_warming_snapshot(repo_root, "miss")


def prewarm_operations_lens_snapshot(repo_root: Path) -> None:
    _ops_start_refresh(repo_root)


def _work_item_search_text(item: Mapping[str, Any]) -> str:
    fields = [
        item.get("id"),
        item.get("title"),
        item.get("statement"),
        item.get("claim"),
        item.get("candidate_work_item_type"),
        item.get("recommended_action"),
    ]
    execution = item.get("execution") if isinstance(item.get("execution"), Mapping) else {}
    fields.extend(str(value) for value in execution.values() if value is not None)
    contracts = item.get("contracts") if isinstance(item.get("contracts"), Mapping) else {}
    for value in contracts.values():
        if isinstance(value, str):
            fields.append(value)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            fields.extend(str(entry) for entry in value[:12])
    return "\n".join(str(value) for value in fields if value is not None).lower()


def _integration_surface_paths(item: Mapping[str, Any]) -> list[str]:
    contracts = item.get("integration_contract") if isinstance(item.get("integration_contract"), Mapping) else {}
    surfaces = contracts.get("exact_surfaces_discovered")
    if not isinstance(surfaces, Sequence) or isinstance(surfaces, (str, bytes)):
        return []
    paths: list[str] = []
    for surface in surfaces:
        if isinstance(surface, Mapping) and isinstance(surface.get("path"), str):
            paths.append(str(surface["path"]))
        elif isinstance(surface, str):
            paths.append(surface)
    return paths


def _work_item_has_frontend_signal(item: Mapping[str, Any]) -> bool:
    if any(path.startswith("system/server/ui/") for path in _integration_surface_paths(item)):
        return True
    text = _work_item_search_text(item)
    for keyword in _FRONTEND_WORKITEM_KEYWORDS:
        if keyword.startswith("/") and keyword in text:
            return True
        if re.search(rf"(?<![a-z0-9_]){re.escape(keyword)}(?![a-z0-9_])", text):
            return True
    return False


def _discover_test_scale(repo_root: Path) -> dict[str, Any]:
    frontend_root = repo_root / "system/server/ui/src"
    frontend_tests: list[str] = []
    if frontend_root.exists():
        for path in frontend_root.rglob("*"):
            if path.is_file() and re.search(r"(\.test|\.spec)\.(ts|tsx)$", path.name):
                frontend_tests.append(str(path.relative_to(repo_root)))
    python_tests: list[str] = []
    for rel_root in ("system/server/tests", "tests", "tools/meta"):
        root = repo_root / rel_root
        if not root.exists():
            continue
        for path in root.rglob("test_*.py"):
            if path.is_file():
                python_tests.append(str(path.relative_to(repo_root)))
    return {
        "frontend": {
            "root": "system/server/ui/src",
            "file_count": len(frontend_tests),
            "files": sorted(frontend_tests),
            "sample_files": sorted(frontend_tests)[:12],
        },
        "python": {
            "roots": ["system/server/tests", "tests", "tools/meta"],
            "file_count": len(python_tests),
            "files": sorted(python_tests),
            "sample_files": sorted(python_tests)[:12],
        },
        "policy": "Discovered test files are scale evidence only; green status comes from explicit command receipts.",
    }


def _public_gate_report_path() -> Path:
    output_root = os.environ.get(_PUBLIC_PROJECTION_OUTPUT_ROOT_ENV)
    if output_root:
        return Path(output_root).expanduser() / _PUBLIC_GATE_REPORT_NAME
    default_path = _PUBLIC_PROJECTION_DEFAULT_OUTPUT_ROOT / _PUBLIC_GATE_REPORT_NAME
    if default_path.exists():
        return default_path
    # Compatibility for receipts emitted before the durable default moved out of
    # macOS /tmp. Explicit --output-root users should set the env var above.
    return _PUBLIC_GATE_REPORT_PATH


def _public_gate_boundary() -> dict[str, Any]:
    report_path = _public_gate_report_path()
    report = _safe_read_json_path(report_path) or {}
    smoke_results = report.get("smoke_results") if isinstance(report.get("smoke_results"), list) else []
    smoke_hard_blockers = [
        item
        for item in smoke_results
        if isinstance(item, Mapping)
        and bool(item.get("hard_blocker"))
        and item.get("status") not in {"pass", "warn"}
    ]
    report_hard_blockers = report.get("hard_blockers") if isinstance(report.get("hard_blockers"), list) else []
    report_status = str(report.get("overall_status") or report.get("publication_status") or "").strip().lower()
    status = "unknown"
    if report:
        if report_status in {"red", "fail", "failed", "blocked"} or smoke_hard_blockers or report_hard_blockers:
            status = "red"
        elif report_status in {"green", "pass", "passed", "ok"}:
            status = "green"
        else:
            status = "green"
    return {
        "status": status,
        "boundary": "portability_gate_report_v0_is_release_authority",
        "report_path": str(report_path),
        "report_exists": bool(report),
        "gate_generated_at": report.get("gate_generated_at"),
        "source_revision": report.get("source_revision"),
        "overall_status": report.get("overall_status"),
        "publication_status": report.get("publication_status"),
        "hard_blocker_count": len(smoke_hard_blockers) + len(report_hard_blockers),
        "hard_blockers": [
            {
                "id": item.get("id"),
                "status": item.get("status"),
                "summary": item.get("summary"),
            }
            for item in smoke_hard_blockers[:8]
        ],
        "report_hard_blockers": report_hard_blockers[:8],
        "sequence_5_policy": "Diagnostic visibility does not assert public projection readiness.",
    }


def _frontend_routes_by_match(navigation_graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    views = navigation_graph.get("views") if isinstance(navigation_graph.get("views"), list) else []
    rows: list[dict[str, Any]] = []
    for view in views:
        if not isinstance(view, Mapping):
            continue
        route_values = [
            view.get("route"),
            view.get("entry_route"),
            *list(view.get("route_aliases") or []),
        ]
        routes = [str(route) for route in route_values if isinstance(route, str) and route]
        if not routes:
            continue
        capture = view.get("capture") if isinstance(view.get("capture"), Mapping) else {}
        rows.append(
            {
                "view_id": view.get("id"),
                "label": view.get("label"),
                "routes": routes,
                "capture_slug": capture.get("slug"),
                "capture_status": (
                    (capture.get("load_timing") or {}).get("latest_status")
                    if isinstance(capture.get("load_timing"), Mapping)
                    else None
                ),
            }
        )
    return rows


def _frontend_workitem_row(
    item: Mapping[str, Any],
    *,
    routes: Sequence[Mapping[str, Any]],
    component_rows: Sequence[Mapping[str, Any]],
    test_files: Sequence[str],
) -> dict[str, Any]:
    text = _work_item_search_text(item)
    surface_paths = _integration_surface_paths(item)
    route_matches = [
        route
        for route in routes
        if any(str(candidate).lower() in text for candidate in route.get("routes") or [])
    ]
    component_matches = [
        component
        for component in component_rows
        if (
            str(component.get("path") or "") in surface_paths
            or str(component.get("path") or "").lower() in text
            or str(component.get("display_name") or "").lower() in text
        )
    ][:6]
    test_matches = [
        path
        for path in test_files
        if path in surface_paths or Path(path).name.lower() in text
    ][:6]
    route_status = "linked" if route_matches else "unknown"
    component_status = "linked" if component_matches else "unknown"
    test_status = "linked" if test_matches else ("candidate_unlinked" if "test" in text else "unknown")
    render_status = "captured" if any(row.get("capture_status") == "captured" for row in route_matches) else (
        "route_without_recent_capture" if route_matches else "unknown"
    )
    return {
        "id": item.get("id"),
        "title": item.get("title") or item.get("statement") or "Untitled WorkItem",
        "state": item.get("state"),
        "candidate_work_item_type": item.get("candidate_work_item_type"),
        "route": {
            "status": route_status,
            "matches": [
                {
                    "view_id": row.get("view_id"),
                    "label": row.get("label"),
                    "routes": row.get("routes"),
                    "capture_slug": row.get("capture_slug"),
                    "capture_status": row.get("capture_status"),
                }
                for row in route_matches[:4]
            ],
        },
        "components": {
            "status": component_status,
            "matches": [
                {
                    "component_id": component.get("component_id"),
                    "path": component.get("path"),
                    "display_name": component.get("display_name"),
                }
                for component in component_matches
            ],
        },
        "tests": {
            "status": test_status,
            "matches": test_matches,
        },
        "render": {
            "status": render_status,
        },
        "honesty": {
            "unknowns": [
                key
                for key, status in {
                    "route": route_status,
                    "components": component_status,
                    "tests": test_status,
                    "render": render_status,
                }.items()
                if status == "unknown"
            ],
            "policy": "Unknown means no explicit route/component/test/render evidence was found in current projections.",
        },
    }


def load_frontend_workitem_diagnostics_projection(
    repo_root: Path,
    *,
    limit: int = 12,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Join Task Ledger WorkItems with frontend route/component/render
      and test-scale evidence so Station can show readiness gaps without
      turning diagnostics into a mutation lane or public-release claim.
    - Mechanism: Read only deterministic Task Ledger projections, frontend
      navigation/component projections, render timing, local test discovery, and
      the public portability gate report as a boundary.
    - Guarantee: Read-only. Unknown mappings are labeled instead of inferred.
    """
    ledger = _safe_read_json(repo_root, "state/task_ledger/ledger.json") or {}
    queue_ref = _active_task_ledger_queue_ref(repo_root)
    queue = queue_ref["payload"]
    navigation_graph = _safe_read_json(repo_root, FRONTEND_NAV_GRAPH_PATH) or {}
    component_index = _safe_read_json(repo_root, FRONTEND_COMPONENT_INDEX_PATH) or {}
    work_items = _task_ledger_view_items(ledger)
    ledger_by_id: dict[str, Mapping[str, Any]] = {
        str(item.get("id")): item for item in work_items if item.get("id")
    }
    routes = _frontend_routes_by_match(navigation_graph)
    component_rows = [
        item
        for item in component_index.get("components", [])
        if isinstance(item, Mapping) and item.get("classification_confidence") in {"high", "medium"}
    ]
    test_scale = _discover_test_scale(repo_root)
    frontend_test_files = list(test_scale["frontend"]["files"])
    candidates = [item for item in work_items if _work_item_has_frontend_signal(item)]
    current_id = str((queue or {}).get("current_next") or "").strip()
    if current_id and current_id in ledger_by_id:
        candidates = [item for item in candidates if item.get("id") != current_id]
        candidates.insert(0, ledger_by_id[current_id])
    diagnostic_rows = [
        _frontend_workitem_row(
            item,
            routes=routes,
            component_rows=component_rows,
            test_files=frontend_test_files,
        )
        for item in candidates[:limit]
    ]
    status_counts = Counter()
    for row in diagnostic_rows:
        for key in ("route", "components", "tests", "render"):
            section = row.get(key) if isinstance(row.get(key), Mapping) else {}
            status_counts[f"{key}:{section.get('status') or 'unknown'}"] += 1
    nav_counts = navigation_graph.get("counts") if isinstance(navigation_graph.get("counts"), Mapping) else {}
    component_meta = component_index.get("__meta") if isinstance(component_index.get("__meta"), Mapping) else {}
    authority = {
        "task_ledger": "state/task_ledger/events.jsonl",
        "frontend_navigation": FRONTEND_NAV_GRAPH_PATH,
        "frontend_components": FRONTEND_COMPONENT_INDEX_PATH,
        "station_render": FRONTEND_RENDER_LOAD_INDEX_PATH,
        "station_consumer": "/station/ledger",
        "endpoint": "/api/world-model/frontend/workitem-diagnostics/projection",
        "boundary": "read_only_projection_no_public_release_claim",
    }
    freshness = {
        "task_ledger": compute_freshness(_file_mtime(repo_root, "state/task_ledger/ledger.json")),
        "navigation_graph": compute_freshness(_file_mtime(repo_root, FRONTEND_NAV_GRAPH_PATH)),
        "component_index": compute_freshness(_file_mtime(repo_root, FRONTEND_COMPONENT_INDEX_PATH)),
        "render_load_index": compute_freshness(_file_mtime(repo_root, FRONTEND_RENDER_LOAD_INDEX_PATH)),
    }
    current_next = _task_ledger_current_next(
        queue,
        ledger_by_id,
        queue_path=str(queue_ref["path"]),
    )
    projection_honesty = {
        "phase_scope": f"{queue_ref.get('phase_id') or 'unknown'} phase-local queue is used only to identify current_next.",
        "queue_source": queue_ref.get("source"),
        "queue_path": queue_ref.get("path"),
        "fallback_used": queue_ref.get("fallback_used"),
        "unknown_policy": "Missing route/component/test/render links are surfaced as unknown instead of synthesized.",
        "public_projection_status": "not_asserted",
        "render_policy": "Render status comes from navigation_graph capture load_timing and render_load_index freshness, not from this endpoint running browsers.",
    }
    return {
        **_diagnostic_projection_envelope(
            schema="frontend_workitem_diagnostics_projection_v1",
            authority=authority,
            freshness=freshness,
            current_next=current_next,
            projection_honesty=projection_honesty,
        ),
        "counts": {
            "work_items": len(work_items),
            "frontend_candidate_work_items": len(candidates),
            "diagnostic_rows": len(diagnostic_rows),
            "frontend_views": int(nav_counts.get("pages") or 0),
            "capture_rows": int(nav_counts.get("capture_rows") or 0),
            "timed_capture_rows": int(nav_counts.get("timed_capture_rows") or 0),
            "drift_signals": int(nav_counts.get("drift_signals") or 0),
            "components": int(component_meta.get("component_count") or len(component_rows)),
            "status": dict(sorted(status_counts.items())),
        },
        "test_scale": test_scale,
        "public_gate": _public_gate_boundary(),
        "diagnostics": diagnostic_rows,
    }


def query_work_ledger(
    repo_root: Path,
    *,
    recipe: str,
    phase_id: str | None = None,
    family_id: str | None = None,
    actor: str | None = None,
    actor_session_id: str | None = None,
    td_id: str | None = None,
    limit: int = 20,
) -> Dict[str, Any]:
    return work_ledger_lib.query_recipe(
        repo_root,
        recipe=recipe,
        phase_id=phase_id,
        family_id=family_id,
        actor=actor,
        actor_session_id=actor_session_id,
        td_id=td_id,
        limit=limit,
    )


def load_work_ledger_thread(repo_root: Path, td_id: str) -> Optional[Dict[str, Any]]:
    token = str(td_id or "").strip()
    if not work_ledger_lib.TD_ID_RE.match(token):
        return None
    projection = work_ledger_lib.build_projection(work_ledger_lib.load_events(repo_root))
    thread = (projection.get("threads") or {}).get(token)
    if not isinstance(thread, dict):
        return None
    chain = work_ledger_lib.query_recipe(
        repo_root,
        recipe="supersession_chain",
        family_id=str(thread.get("family_id") or "").strip() or None,
        td_id=token,
        limit=50,
    )
    return {
        "schema": "work_ledger_thread_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "td_id": token,
        "thread": thread,
        "supersession_chain": list(chain.get("results") or []),
    }


def _safe_read_json_first_line(repo_root: Path, rel_path: str) -> Optional[Dict[str, Any]]:
    """Read the *last* line of a jsonl file — the newest orchestration event."""
    try:
        path = repo_root / rel_path
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            last = None
            for line in fh:
                if line.strip():
                    last = line
            if not last:
                return None
            return json.loads(last)
    except Exception:
        return None


# --- Topology index (replaces the dumb sampled list) ---------------------

_TOPOLOGY_KIND_MAP = {
    ".py": "py",
    ".ts": "ts",
    ".tsx": "tsx",
    ".json": "json",
    ".md": "md",
    ".mdc": "md",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".sh": "sh",
    ".html": "html",
    ".css": "css",
    ".png": "img",
    ".jpg": "img",
    ".jpeg": "img",
    ".svg": "img",
}


def _classify_topology_path(path: str) -> Tuple[str, str, Optional[str]]:
    lower = path.lower()
    suffix = Path(lower).suffix
    kind = _TOPOLOGY_KIND_MAP.get(suffix, "other")
    parts = lower.split("/")
    head = parts[0] if parts else "other"
    is_root_file = len(parts) == 1
    has_children = len(parts) >= 2

    if is_root_file:
        group = "root"
    elif head.startswith(".") or head in {".claude", ".cursor", ".git", ".vscode"}:
        group = "config"
    elif head == "codex" and has_children:
        second = parts[1]
        if second == "doctrine":
            group = "doctrine"
        elif second == "standards":
            group = "standards"
        elif second == "substrate":
            group = "substrate"
        elif second == "hologram":
            group = "hologram"
        elif second == "derived":
            group = "derived"
        else:
            group = "codex"
    elif head == "system" and has_children:
        second = parts[1]
        if second == "server" and len(parts) > 2 and parts[2] == "ui":
            group = "ui"
        elif second == "server":
            group = "server"
        elif second in ("lib", "core"):
            group = "system_lib"
        else:
            group = "system"
    elif head == "tools":
        group = "tools"
    elif head == "obsidian":
        group = "obsidian"
    elif head == "docs":
        group = "docs"
    elif head == "annexes":
        group = "annexes"
    elif head == "external":
        group = "external"
    elif head == "state":
        group = "state"
    else:
        group = "other"

    cluster: Optional[str] = None
    if has_children and group not in {"root", "config"}:
        cluster = "/".join(parts[:2])
    elif is_root_file:
        cluster = "root"

    return kind, group, cluster


def load_topology_index(repo_root: Path, phase_ref: str) -> Optional[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Build a topology index for a phase's `system_view.json`.
    - Mechanism: Resolve the phase, classify each path by group/kind/cluster, aggregate counts, and emit the bounded cluster summary used by the topology lens.
    - Guarantee: Returns a `topology_index_v1` payload or None when the phase/system view cannot be loaded.
    - Fails: None.
    - When-needed: Open when the server needs the authoritative topology lens over a phase system view rather than a sampled file list.
    - Escalates-to: system/server/world_model.py::search_topology; system/server/main.py
    - Navigation-group: server_backend
    """
    phase_dir = _resolve_phase_dir(repo_root, phase_ref)
    if not phase_dir:
        return None
    files, full_rel, generated_at = _phase_file_inventory(repo_root, phase_dir)
    if not files:
        return None

    group_counts: Dict[str, Dict[str, Any]] = {}
    cluster_counts: Dict[str, Dict[str, Any]] = {}
    for entry in files:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path") or "").strip()
        if not path:
            continue
        kind, group, cluster = _classify_topology_path(path)
        grp = group_counts.setdefault(
            group,
            {"group": group, "count": 0, "kinds": {}},
        )
        grp["count"] += 1
        grp["kinds"][kind] = grp["kinds"].get(kind, 0) + 1
        if cluster:
            clust = cluster_counts.setdefault(
                cluster,
                {"id": cluster, "group": group, "count": 0, "kinds": {}, "sample_paths": []},
            )
            clust["count"] += 1
            clust["kinds"][kind] = clust["kinds"].get(kind, 0) + 1
            if len(clust["sample_paths"]) < 4:
                clust["sample_paths"].append(path)

    clusters = sorted(cluster_counts.values(), key=lambda c: c["count"], reverse=True)

    return {
        "schema": "topology_index_v1",
        "phase_id": _phase_id_for_dir(repo_root, phase_dir),
        "phase_dir": phase_dir,
        "file_count": len(files),
        "groups": group_counts,
        "clusters": clusters[:80],
        "generated_at": generated_at,
        "full_path": full_rel,
        "freshness": compute_freshness(generated_at),
    }


def search_topology(
    repo_root: Path,
    phase_ref: str,
    *,
    query: str = "",
    group: Optional[str] = None,
    cluster: Optional[str] = None,
    kind: Optional[str] = None,
    limit: int = 60,
) -> Optional[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Search a phase's `system_view.json` with bounded operator paging.
    - Mechanism: Resolve the phase, filter system-view entries by query/group/cluster/kind, and return up to `limit` compact matches plus the total matched count.
    - Guarantee: Returns a `topology_search_v1` payload or None when the phase/system view cannot be loaded.
    - Fails: None.
    - When-needed: Open when a server route needs filtered topology search results instead of the aggregate topology index.
    - Escalates-to: system/server/world_model.py::load_topology_index; system/server/main.py
    """
    phase_dir = _resolve_phase_dir(repo_root, phase_ref)
    if not phase_dir:
        return None
    files, full_rel, _generated_at = _phase_file_inventory(repo_root, phase_dir)
    if not files:
        return None
    needle = query.strip().lower()
    results: List[Dict[str, Any]] = []
    matched = 0
    for entry in files:
        if not isinstance(entry, dict):
            continue
        path = str(entry.get("path") or "").strip()
        if not path:
            continue
        kind_classified, group_classified, cluster_classified = _classify_topology_path(path)
        if group and group_classified != group:
            continue
        if cluster and cluster_classified != cluster:
            continue
        if kind and kind_classified != kind:
            continue
        if needle and needle not in path.lower():
            continue
        matched += 1
        if len(results) < limit:
            results.append(
                {
                    "path": path,
                    "kind": kind_classified,
                    "group": group_classified,
                    "cluster": cluster_classified,
                    "size_bytes": entry.get("bytes") or entry.get("size_bytes"),
                }
            )
    return {
        "schema": "topology_search_v1",
        "phase_id": _phase_id_for_dir(repo_root, phase_dir),
        "phase_dir": phase_dir,
        "query": query,
        "filter": {"group": group, "cluster": cluster, "kind": kind},
        "results": results,
        "matched": matched,
        "limit": limit,
    }


# --- Actionable orchestration (read-side + safe refresh) -----------------


def refresh_orchestration_snapshot(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Give the browser an explicit read-side refresh surface for orchestration state.
    - Mechanism: Stamp `refreshed_at` and return a newly loaded attention snapshot without mutating kernel-owned runtime state.
    - Guarantee: Returns a dict containing `refreshed_at` and `snapshot`, where `snapshot` is the current `load_attention_snapshot()` payload.
    - Fails: None.
    - When-needed: Open when a server route or UI refresh action needs a safe re-read of the orchestration-attention surface without implying any mutation.
    - Escalates-to: system/server/world_model.py::load_attention_snapshot; system/server/main.py
    """
    return {
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "snapshot": load_attention_snapshot(repo_root),
    }


def _approval_evidence_refs(record: Mapping[str, Any]) -> List[Dict[str, str]]:
    refs = _artifact_refs_from_values(record.get("artifacts") or [])
    metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
    refs.extend(_artifact_refs_from_values(metadata.get("evidence_refs") or []))
    seen: set[str] = set()
    out: List[Dict[str, str]] = []
    for ref in refs:
        path = ref.get("path")
        if not path or path in seen:
            continue
        seen.add(path)
        out.append(ref)
    return out


def _approval_unblocks(record: Mapping[str, Any]) -> List[str]:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
    candidates: List[str] = []
    for key in ("unblocks", "blocked_subjects", "downstream_subjects", "depends_on_clearance_for"):
        candidates.extend(_str_list(metadata.get(key)))
    if not candidates and record.get("source_ref"):
        # The source ref is the minimum honest impact anchor when the native
        # source has not yet projected explicit unblock edges.
        candidates.append(str(record.get("source_ref")))
    seen: set[str] = set()
    out: List[str] = []
    for item in candidates:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _enrich_approval_record(record: Mapping[str, Any], *, now: Optional[datetime] = None) -> Dict[str, Any]:
    enriched = dict(record)
    opened_at = enriched.get("opened_at") or enriched.get("updated_at")
    unblocks = _approval_unblocks(enriched)
    enriched.setdefault("age_seconds", _age_seconds(opened_at, now=now))
    enriched.setdefault("detail_excerpt", _excerpt(enriched.get("detail"), limit=180))
    enriched.setdefault("unblocks", unblocks)
    enriched.setdefault("unblocks_count", len(unblocks))
    enriched.setdefault("evidence_refs", _approval_evidence_refs(enriched))
    if enriched.get("surface_route"):
        enriched["surface_route"] = _safe_internal_route(enriched.get("surface_route"), "/station/approvals")
    return enriched


def list_approvals(
    repo_root: Path,
    *,
    source_kind: str | None = None,
    status: str | None = None,
    action_kind: str | None = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Project the unified approval inbox from native source files plus
      the local approval overlay without inventing a new authority store.
    - Mechanism: Delegate to `system.lib.approval_registry.list_approvals(...)`
      so the HTTP layer and Station snapshot both consume the same projection.
    - Guarantee: Returns `{records, summary, generated_at}` and rewrites the
      approval pending snapshot on read.
    - Fails: Raises only on unexpected registry/runtime errors.
    """
    payload = approval_registry.list_approvals(
        repo_root,
        source_kind=source_kind,
        status=status,
        action_kind=action_kind,
    )
    now = datetime.now(timezone.utc)
    records = [
        _enrich_approval_record(record, now=now)
        for record in list(payload.get("records") or [])
        if isinstance(record, Mapping)
    ]
    summary = dict(payload.get("summary") or {})
    top_records = [
        _enrich_approval_record(record, now=now)
        for record in list(summary.get("top_records") or [])[:10]
        if isinstance(record, Mapping)
    ]
    summary["top_records"] = top_records
    return {
        **payload,
        "records": records,
        "summary": summary,
    }


def decide_approval(
    repo_root: Path,
    *,
    approval_id: str,
    decision: str,
    actor_id: str,
    reason: str | None = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Apply one operator decision against a projected approval row
      using the native mutation surface for that source kind.
    - Mechanism: Route campaign approvals through the launch catalog operation
      and orchestration approvals through `acknowledge_orchestration_gate(...)`,
      while review-only rows remain unsupported in v1.
    - Guarantee: Returns the registry decision envelope with refreshed records.
    - Fails: Validation and claim conflicts are surfaced as structured
      `{ok: False, error_code, error}` payloads.
    """

    def _approve_campaign(record: Dict[str, Any], actor: str, _note: str | None) -> Dict[str, Any]:
        operation = record.get("operation") if isinstance(record.get("operation"), Mapping) else {}
        parameters = dict(operation.get("parameters") or {}) if isinstance(operation, Mapping) else {}
        parameters["campaign_summary"] = str(record.get("source_ref") or parameters.get("campaign_summary") or "").strip()
        parameters["approved_by"] = actor
        return launch_operation(
            repo_root,
            operation_id="python_std_compliance_campaign_approve",
            parameters=parameters,
            actor_id=actor,
        )

    def _approve_orchestration_gate(
        _record: Dict[str, Any],
        actor: str,
        note: str | None,
    ) -> Dict[str, Any]:
        return acknowledge_orchestration_gate(repo_root, actor_id=actor, reason=note)

    def _approve_type_a_seat(
        record: Dict[str, Any],
        actor: str,
        note: str | None,
    ) -> Dict[str, Any]:
        from system.lib import type_a_seat_control

        source_ref = str(record.get("source_ref") or "").split("#", 1)[0]
        if not source_ref:
            return {"ok": False, "error": "type_a_seat request path missing"}
        return type_a_seat_control.approve_seat_request(
            repo_root,
            request_path=source_ref,
            actor_id=actor,
            reason=note,
        )

    def _reject_type_a_seat(
        record: Dict[str, Any],
        actor: str,
        note: str | None,
    ) -> Dict[str, Any]:
        from system.lib import type_a_seat_control

        source_ref = str(record.get("source_ref") or "").split("#", 1)[0]
        if not source_ref:
            return {"ok": False, "error": "type_a_seat request path missing"}
        return type_a_seat_control.reject_seat_request(
            repo_root,
            request_path=source_ref,
            actor_id=actor,
            reason=note,
        )

    return approval_registry.decide_approval(
        repo_root,
        approval_id=approval_id,
        decision=decision,
        actor_id=actor_id,
        reason=reason,
        approve_callbacks={
            "campaign_preview_ready": _approve_campaign,
            "orchestration_gate": _approve_orchestration_gate,
            "type_a_seat_dispatch": _approve_type_a_seat,
        },
        reject_callbacks={
            "type_a_seat_dispatch": _reject_type_a_seat,
        },
    )


# --- Operator-surface actions (Phase 09.17 gap audit breaks #4 and #10) -----
#
# This block implements three additive helpers so the browser cockpit can:
#   - record a typed `gate_acknowledged` event into the orchestration event log
#     without mutating kernel-owned orchestration_state.json directly
#     (apply-gate discipline: the orchestration loop interprets the event next
#     cycle; this module never writes state behind the kernel's back);
#   - enumerate a SAFE catalog of launchable kernel/bridge operations
#     (introspection and browse only — never `--apply` mutations); and
#   - launch one of those catalog operations via subprocess with a bounded
#     timeout, capturing stdout/stderr and recording an `operation_launched`
#     event for traceability.
#
# All three are exception-safe and follow the existing `_safe_read_json`
# pattern: failures degrade into structured `{"ok": False, "error": ...}`
# payloads rather than raising.

_LAUNCHABLE_PARAM_VALUE_RE = re.compile(r"^[A-Za-z0-9_./-]+$")


def _new_event_id(prefix: str, now: datetime) -> str:
    """Generate an event_id in the same shape as existing orchestration rows."""
    import hashlib

    stamp = now.strftime("%Y%m%dT%H%M%S")
    micro = f"{now.microsecond:06d}"
    fingerprint_seed = f"{prefix}:{now.isoformat()}:{os.getpid()}"
    fp = hashlib.sha1(fingerprint_seed.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{stamp}_{micro}_0000_{fp}"


def _append_orchestration_event(repo_root: Path, event: Dict[str, Any]) -> bool:
    """Append a single JSONL event to orchestration_events.jsonl. Return False on failure."""
    try:
        path = repo_root / ORCHESTRATION_EVENTS_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(event, ensure_ascii=False, sort_keys=False)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(payload + "\n")
        return True
    except Exception as exc:
        logger.debug("append orchestration_event failed: %s", exc)
        return False


def acknowledge_orchestration_gate(
    repo_root: Path,
    *,
    actor_id: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Let an operator record a typed `gate_acknowledged` event into the
      orchestration event log without bypassing the kernel apply-gate. The orchestration
      loop reads this event on its next cycle and decides whether to clear the gate.
    - Mechanism: Read the current `orchestration_state.json` (read-only) to capture the
      prior `gate_reason`, build a `gate_acknowledged` event with the existing
      `orch_...` event-id scheme, and append it to `orchestration_events.jsonl`.
      Never mutates `orchestration_state.json`.
    - Guarantee: Returns `{"ok": True, "event": {...}}` on append success,
      `{"ok": False, "error": "..."}` on any failure.
    - Fails: None (exception-safe).
    - When-needed: Open when a cockpit POST needs to record the operator's
      acknowledgement of a gate without violating apply-gate discipline.
    - Escalates-to: system/server/world_model.py::_append_orchestration_event;
      system/server/main.py
    - Navigation-group: server_backend
    """
    actor = (actor_id or "").strip()
    if not actor:
        return {"ok": False, "error": "actor_id is required"}
    try:
        state = _safe_read_json(repo_root, ORCHESTRATION_STATE_PATH) or {}
        gate = state.get("gate") if isinstance(state.get("gate"), dict) else {}
        prev_gate_reason = gate.get("gate_reason") or state.get("gate_reason")
        prev_gate_owner = gate.get("owner_driver") or state.get("gate_owner")

        now = datetime.now(timezone.utc)
        event = {
            "kind": "gate_acknowledged",
            "schema_version": "gate_acknowledged_v1",
            "recorded_at": now.isoformat(),
            "actor_id": actor,
            "reason": (reason or "").strip() or None,
            "prev_gate_reason": prev_gate_reason,
            "prev_gate_owner": prev_gate_owner,
            "event_id": _new_event_id("ack", now),
        }
        ok = _append_orchestration_event(repo_root, event)
        if not ok:
            return {"ok": False, "error": "failed to append orchestration event"}
        return {"ok": True, "event": event}
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("acknowledge_orchestration_gate failed: %s", exc)
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def load_overnight_chain_snapshot(
    repo_root: Path,
    *,
    chain_id: str = "overnight_raw_seed_chain",
    family_number: str | None = None,
) -> dict[str, Any]:
    summary = latest_chain_run_summary(
        repo_root,
        chain_id=chain_id,
        family=str(family_number or "").strip() or None,
    )
    if not summary:
        return {
            "chain_id": chain_id,
            "chain_run_id": None,
            "terminal_status": None,
            "is_running": False,
            "pid": None,
            "log_path": None,
            "state_path": (
                "state/meta_missions/overnight_raw_seed_chain/runtime/"
                "overnight_chain_state.json"
            ),
            "ledger_path": (
                "state/meta_missions/overnight_raw_seed_chain/runtime/"
                "overnight_chain_ledger.jsonl"
            ),
            "stop_flag_path": (
                "state/meta_missions/overnight_raw_seed_chain/runtime/overnight_stop.flag"
            ),
            "last_updated": None,
            "progress": {
                "completed_steps": 0,
                "total_steps": 0,
                "current_step_id": None,
                "current_step_index": None,
            },
            "next_resume_seam": None,
            "provider_wait": None,
            "last_error": None,
        }
    return summary


def load_overnight_queue_snapshot(
    repo_root: Path,
    *,
    manifest_rel: str = _DEFAULT_OVERNIGHT_QUEUE_MANIFEST_REL,
) -> dict[str, Any]:
    manifest = _safe_read_json(repo_root, manifest_rel) or {}
    queue_id = str(manifest.get("queue_id") or "").strip()
    runtime_root = f"state/autonomy_runtime/{queue_id}/runtime" if queue_id else None
    if not queue_id:
        return {
            "queue_id": None,
            "queue_run_id": None,
            "manifest_path": manifest_rel,
            "terminal_status": None,
            "is_running": False,
            "pid": None,
            "log_path": None,
            "state_path": None,
            "ledger_path": None,
            "stop_flag_path": None,
            "last_updated": None,
            "progress": {
                "completed_items": 0,
                "total_items": 0,
                "current_item_id": None,
                "current_item_index": None,
            },
            "current_item_id": None,
            "current_item_index": None,
            "total_items": 0,
            "next_resume_item_id": None,
            "next_resume_item_index": None,
            "next_resume_seam": None,
            "artifact_refs": [],
            "provider_wait": None,
            "last_error": None,
        }
    summary = latest_queue_run_summary(
        repo_root,
        queue_id=queue_id,
        manifest_path=manifest_rel,
        ledger_rel=f"{runtime_root}/queue_ledger.jsonl",
        state_rel=f"{runtime_root}/queue_state.json",
        stop_flag_rel=f"{runtime_root}/queue_stop.flag",
    )
    if not summary:
        legacy_runtime_root = f"state/meta_missions/{queue_id}/runtime"
        legacy_summary = latest_queue_run_summary(
            repo_root,
            queue_id=queue_id,
            manifest_path=manifest_rel,
            ledger_rel=f"{legacy_runtime_root}/queue_ledger.jsonl",
            state_rel=f"{legacy_runtime_root}/queue_state.json",
            stop_flag_rel=f"{legacy_runtime_root}/queue_stop.flag",
        )
        if legacy_summary:
            return {**legacy_summary, "legacy_runtime_state": True}
    if not summary:
        return {
            "queue_id": queue_id,
            "queue_run_id": None,
            "manifest_path": manifest_rel,
            "terminal_status": None,
            "is_running": False,
            "pid": None,
            "log_path": None,
            "state_path": f"{runtime_root}/queue_state.json",
            "ledger_path": f"{runtime_root}/queue_ledger.jsonl",
            "stop_flag_path": f"{runtime_root}/queue_stop.flag",
            "last_updated": None,
            "progress": {
                "completed_items": 0,
                "total_items": len(manifest.get("items") or []),
                "current_item_id": None,
                "current_item_index": None,
            },
            "current_item_id": None,
            "current_item_index": None,
            "total_items": len(manifest.get("items") or []),
            "next_resume_item_id": None,
            "next_resume_item_index": None,
            "next_resume_seam": None,
            "artifact_refs": [],
            "provider_wait": None,
            "last_error": None,
        }
    return summary


_LAUNCHABLE_OPERATIONS_CATALOG: List[Dict[str, Any]] = [
    {
        "operation_id": "kernel_pulse",
        "label": "Kernel pulse",
        "kicker": "pulse",
        "description_short": "Single-shot kernel pulse: reports active phase, gate, routing emphasis.",
        "command": "python3 kernel.py --pulse",
        "parameters_schema": {},
        "principle_refs": ["pri_058", "pri_104"],
    },
    {
        "operation_id": "kernel_info",
        "label": "Kernel info",
        "kicker": "info",
        "description_short": "Top-level kernel info packet: command groups, recent frontier, sources.",
        "command": "python3 kernel.py --info",
        "parameters_schema": {},
        "principle_refs": ["pri_086"],
    },
    {
        "operation_id": "kernel_observe_status",
        "label": "Observe status",
        "kicker": "observe",
        "description_short": "Latest grouped-observe runtime status snapshot for the operator surface.",
        "command": "python3 kernel.py --observe-status latest",
        "parameters_schema": {},
        "principle_refs": ["pri_058"],
    },
    {
        "operation_id": "kernel_build_status",
        "label": "Build status",
        "kicker": "build",
        "description_short": "Per-phase hologram staleness check without triggering a rebuild.",
        "command": "python3 kernel.py --build status",
        "parameters_schema": {},
        "principle_refs": ["pri_058"],
    },
    {
        "operation_id": "kernel_doctrine_query",
        "label": "Doctrine query",
        "kicker": "doctrine",
        "description_short": "Compiled doctrine query packet for a topic across the authority graph.",
        "command": 'python3 kernel.py --doctrine-query "{topic}"',
        "parameters_schema": {
            "topic": {"type": "string", "required": True, "description": "Doctrine topic (e.g. 'bridge dispatch')."}
        },
        "principle_refs": ["pri_086"],
    },
    {
        "operation_id": "kernel_raw_seed_browse",
        "label": "Raw-seed browse",
        "kicker": "raw-seed",
        "description_short": "Browse raw-seed paragraphs in the active family for a query.",
        "command": 'python3 kernel.py --raw-seed-browse {family} --query "{query}"',
        "parameters_schema": {
            "family": {"type": "string", "required": False, "default": "09", "description": "Phase family id."},
            "query": {"type": "string", "required": True, "description": "Search term for raw-seed paragraphs."},
        },
        "principle_refs": ["pri_086", "pri_107"],
    },
    {
        "operation_id": "kernel_sync_raw_seed",
        "label": "Sync raw seed",
        "kicker": "raw-seed",
        "description_short": "Mechanically sync a family raw seed and regenerate its registry projections.",
        "command": "python3 kernel.py --sync-raw-seed {family} --live",
        "parameters_schema": {
            "family": {
                "type": "string",
                "required": False,
                "default": "09",
                "description": "Phase family id, e.g. '09'.",
            },
        },
        "principle_refs": ["pri_086", "pri_107"],
        "meta_mission_id": "raw_seed_sync",
        "meta_mission_run_source": "launcher",
    },
    {
        "operation_id": "raw_seed_atomize",
        "label": "Atomize raw seed",
        "kicker": "raw-seed",
        "description_short": "Turn synced raw-seed paragraphs into atomized extracted-shard rows and refresh family coverage.",
        "command": "./repo-python tools/meta/factory/raw_seed_pipeline.py atomize --family {family} --cohort-size {cohort_size}",
        "parameters_schema": {
            "family": {
                "type": "string",
                "required": False,
                "default": "09",
                "label": "Family",
                "description": "Phase family id, e.g. '09'.",
            },
            "cohort_size": {
                "type": "integer",
                "required": False,
                "default": 12,
                "minimum": 1,
                "label": "Cohort size",
                "description": "How many pending paragraphs are selected into this bounded run.",
            },
        },
        "dispatch_policy_mission_id": "raw_seed_atomization",
        "dispatch_policy_binding": {
            "cohort_param": "cohort_size",
        },
        "principle_refs": ["pri_086", "pri_107"],
        "meta_mission_id": "raw_seed_atomization",
        "meta_mission_run_source": "launcher",
    },
    {
        "operation_id": "raw_seed_distill_ingest",
        "label": "Ingest raw-seed distillation",
        "kicker": "raw-seed",
        "description_short": "Store bridge-authored paragraph distillations with paragraph provenance so later atomization can reuse them.",
        "command": "./repo-python tools/meta/factory/raw_seed_pipeline.py distill-ingest --family {family} --input {input_path} --provider {provider}",
        "parameters_schema": {
            "family": {
                "type": "string",
                "required": False,
                "default": "09",
                "description": "Phase family id, e.g. '09'.",
            },
            "input_path": {
                "type": "string",
                "required": True,
                "description": "Repo-relative or absolute JSON payload path for the distillation batch.",
            },
            "provider": {
                "type": "string",
                "required": False,
                "default": "chatgpt",
                "description": "Bridge provider key used for provenance metadata.",
            },
        },
        "principle_refs": ["pri_072", "pri_086", "pri_107"],
    },
    {
        "operation_id": "raw_seed_distill_cycle",
        "label": "Distill raw seed",
        "kicker": "raw-seed",
        "description_short": "Run one bounded bridge-first raw-seed distillation cycle over pending paragraphs.",
        "command": "./repo-python tools/meta/factory/raw_seed_pipeline.py distill-cycle --family {family} --provider {provider} --cohort-size {cohort_size} --wave-width {wave_width}",
        "parameters_schema": {
            "family": {
                "type": "string",
                "required": False,
                "default": "09",
                "label": "Family",
                "description": "Phase family id, e.g. '09'.",
            },
            "provider": {
                "type": "string",
                "required": False,
                "default": "chatgpt",
                "label": "Provider",
                "description": "Bridge provider key used for distillation dispatch.",
            },
            "cohort_size": {
                "type": "integer",
                "required": False,
                "default": 12,
                "minimum": 1,
                "label": "Cohort size",
                "description": "How many pending paragraphs are selected into this distillation cycle.",
            },
            "wave_width": {
                "type": "integer",
                "required": False,
                "default": 3,
                "minimum": 1,
                "label": "Wave width",
                "description": "How many selected paragraphs dispatch at once. Must stay at or below the provider ceiling.",
            },
        },
        "dispatch_policy_mission_id": "raw_seed_bridge_distillation",
        "dispatch_policy_binding": {
            "provider_param": "provider",
            "cohort_param": "cohort_size",
            "wave_param": "wave_width",
        },
        "validation_policy": {
            "dispatch_policy_mission_id": "raw_seed_bridge_distillation",
            "provider_param": "provider",
            "wave_param": "wave_width",
        },
        "principle_refs": ["pri_072", "pri_086", "pri_107"],
        "meta_mission_id": "raw_seed_bridge_distillation",
        "meta_mission_run_source": "launcher",
    },
    {
        "operation_id": "raw_seed_route_review",
        "label": "Route raw-seed backlog",
        "kicker": "raw-seed",
        "description_short": "Write bounded doctrine-routing proposals for pending atomized shards with provider-safe batching.",
        "command": "./repo-python tools/meta/factory/raw_seed_pipeline.py route-review --family {family} --provider {provider} --cohort-size {cohort_size} --wave-width {wave_width}",
        "parameters_schema": {
            "family": {
                "type": "string",
                "required": False,
                "default": "09",
                "label": "Family",
                "description": "Phase family id, e.g. '09'.",
            },
            "provider": {
                "type": "string",
                "required": False,
                "default": "chatgpt",
                "label": "Provider",
                "description": "Bridge provider key used for batching policy, e.g. 'chatgpt' or 'gemini'.",
            },
            "cohort_size": {
                "type": "integer",
                "required": False,
                "default": 10,
                "minimum": 1,
                "label": "Cohort size",
                "description": "How many pending shards are selected into this review batch.",
            },
            "wave_width": {
                "type": "integer",
                "required": False,
                "default": 3,
                "minimum": 1,
                "label": "Wave width",
                "description": "How many selected shards dispatch at once. Must stay at or below the provider ceiling.",
            },
        },
        "principle_refs": ["pri_072", "pri_086", "pri_107"],
        "dispatch_policy_mission_id": "raw_seed_doctrine_routing",
        "dispatch_policy_binding": {
            "provider_param": "provider",
            "cohort_param": "cohort_size",
            "wave_param": "wave_width",
        },
        "validation_policy": {
            "dispatch_policy_mission_id": "raw_seed_doctrine_routing",
            "provider_param": "provider",
            "wave_param": "wave_width",
        },
        "meta_mission_id": "raw_seed_doctrine_routing",
        "meta_mission_run_source": "launcher",
    },
    {
        "operation_id": "raw_seed_apply_routing",
        "label": "Apply routed doctrine",
        "kicker": "raw-seed",
        "description_short": "Commit bounded routing-review proposals into doctrine and refresh the enriched coverage view.",
        "command": "./repo-python tools/meta/factory/raw_seed_apply_loop.py apply-routing --family {family} --commit",
        "parameters_schema": {
            "family": {
                "type": "string",
                "required": False,
                "default": "09",
                "description": "Phase family id, e.g. '09'.",
            },
        },
        "principle_refs": ["pri_072", "pri_086", "pri_107"],
    },
    {
        "operation_id": "raw_seed_coverage_enrich",
        "label": "Refresh coverage health",
        "kicker": "raw-seed",
        "description_short": "Rebuild the enriched raw-seed coverage surface with density, merge, and orphan-cluster signals.",
        "command": "./repo-python tools/meta/factory/raw_seed_apply_loop.py coverage-enrich --family {family}",
        "parameters_schema": {
            "family": {
                "type": "string",
                "required": False,
                "default": "09",
                "description": "Phase family id, e.g. '09'.",
            },
        },
        "principle_refs": ["pri_086", "pri_107"],
        "meta_mission_id": "raw_seed_coverage_enrich",
        "meta_mission_run_source": "launcher",
    },
    {
        "operation_id": "raw_seed_surface_to_codex",
        "label": "Surface to Codex",
        "kicker": "raw-seed",
        "description_short": "Promote low-confidence routes and proposed-new items into the Codex review queue without mutating doctrine.",
        "command": "./repo-python tools/meta/factory/raw_seed_apply_loop.py surface-to-codex --family {family}",
        "parameters_schema": {
            "family": {
                "type": "string",
                "required": False,
                "default": "09",
                "description": "Phase family id, e.g. '09'.",
            },
        },
        "principle_refs": ["pri_086", "pri_107"],
        "meta_mission_id": "raw_seed_surface_to_codex",
        "meta_mission_run_source": "launcher",
    },
    {
        "operation_id": "overnight_raw_seed_chain_launch",
        "label": "Launch overnight chain",
        "kicker": "overnight",
        "description_short": "Start the detached raw-seed overnight chain (conservative cohort/wave caps) with ledger under state/meta_missions/overnight_raw_seed_chain/runtime/ and graceful-stop via overnight_stop.flag.",
        "command": "./repo-python tools/meta/factory/overnight_chain_runner.py run --chain overnight_raw_seed_chain --family {family} --provider {provider} --cohort-override distill=4 --wave-override distill=1 --cohort-override atomize=8 --wave-override atomize=2 --cohort-override route_review=8 --wave-override route_review=2",
        "parameters_schema": {
            "family": {
                "type": "string",
                "required": False,
                "default": "09",
                "label": "Family",
                "description": "Phase family id, e.g. '09'.",
            },
            "provider": {
                "type": "string",
                "required": False,
                "default": "chatgpt",
                "label": "Provider",
                "description": "Bridge provider key used by the chain's bridge-backed steps.",
            },
        },
        "ui_group": "overnight_chain",
        "execution_mode": "detached",
        "principle_refs": ["pri_072", "pri_086", "pri_107"],
        "meta_mission_id": "overnight_raw_seed_chain",
        "meta_mission_run_source": "runtime",
    },
    {
        "operation_id": "overnight_raw_seed_chain_resume",
        "label": "Resume overnight chain",
        "kicker": "overnight",
        "description_short": "Resume the most recent graceful-stop or failed overnight chain from its next durable seam (same conservative cohort/wave flags as launch).",
        "command": "./repo-python tools/meta/factory/overnight_chain_runner.py run --chain overnight_raw_seed_chain --family {family} --provider {provider} --cohort-override distill=4 --wave-override distill=1 --cohort-override atomize=8 --wave-override atomize=2 --cohort-override route_review=8 --wave-override route_review=2 --resume",
        "parameters_schema": {
            "family": {
                "type": "string",
                "required": False,
                "default": "09",
                "label": "Family",
                "description": "Phase family id, e.g. '09'.",
            },
            "provider": {
                "type": "string",
                "required": False,
                "default": "chatgpt",
                "label": "Provider",
                "description": "Bridge provider key used by the chain's bridge-backed steps.",
            },
        },
        "ui_group": "overnight_chain",
        "execution_mode": "detached",
        "principle_refs": ["pri_072", "pri_086", "pri_107"],
        "meta_mission_id": "overnight_raw_seed_chain",
        "meta_mission_run_source": "runtime",
    },
    {
        "operation_id": "overnight_raw_seed_chain_stop",
        "label": "Stop overnight chain",
        "kicker": "overnight",
        "description_short": "Set overnight_stop.flag for a graceful stop at the next chain seam; also stops drain-distill-raw-seed (same flag).",
        "command": "./repo-python tools/meta/factory/overnight_chain_runner.py stop --chain overnight_raw_seed_chain --family {family}",
        "parameters_schema": {
            "family": {
                "type": "string",
                "required": False,
                "default": "09",
                "label": "Family",
                "description": "Phase family id, e.g. '09'.",
            },
        },
        "ui_group": "overnight_chain",
        "execution_mode": "sync",
        "principle_refs": ["pri_072", "pri_086", "pri_107"],
    },
    {
        "operation_id": "overnight_raw_seed_drain_distill_launch",
        "label": "Drain raw-seed distill (overnight)",
        "kicker": "overnight",
        "description_short": "Loop bridge distill-cycles with conservative defaults until the backlog is empty, max-passes, or stop (ledger: drain_distill_ledger.jsonl; stop: overnight_raw_seed_chain/runtime/overnight_stop.flag).",
        "command": "./repo-python tools/meta/factory/overnight_chain_runner.py drain-distill-raw-seed --family {family} --provider {provider} --max-passes {max_passes} --sleep-seconds {sleep_seconds} --cohort-size {cohort_size} --wave-width {wave_width}",
        "parameters_schema": {
            "family": {
                "type": "string",
                "required": False,
                "default": "09",
                "label": "Family",
                "description": "Phase family id, e.g. '09'.",
            },
            "provider": {
                "type": "string",
                "required": False,
                "default": "chatgpt",
                "label": "Provider",
                "description": "Bridge provider key for distill-cycle.",
            },
            "max_passes": {
                "type": "integer",
                "required": False,
                "default": 2000,
                "label": "Max passes",
                "description": "Upper bound on distill-cycle invocations.",
            },
            "sleep_seconds": {
                "type": "integer",
                "required": False,
                "default": 45,
                "label": "Sleep seconds",
                "description": "Pause between successful passes to limit bridge throughput.",
            },
            "cohort_size": {
                "type": "integer",
                "required": False,
                "default": 4,
                "label": "Cohort size",
                "description": "Paragraphs per distill-cycle (conservative default 4).",
            },
            "wave_width": {
                "type": "integer",
                "required": False,
                "default": 1,
                "label": "Wave width",
                "description": "Concurrent bridge dispatches (conservative default 1).",
            },
        },
        "ui_group": "overnight_chain",
        "execution_mode": "detached",
        "principle_refs": ["pri_072", "pri_086", "pri_107"],
        "meta_mission_id": "raw_seed_bridge_distillation",
        "meta_mission_run_source": "runtime",
    },
    {
        "operation_id": "overnight_meta_mission_queue_launch",
        "label": "Launch autonomy runtime",
        "kicker": "overnight",
        "description_short": "Run a manifest-backed serial autonomy runtime of Type A seed observations, chains, and sync launchable operations.",
        "command": "./repo-python tools/meta/factory/overnight_chain_runner.py run --manifest {manifest}",
        "parameters_schema": {
            "manifest": {
                "type": "string",
                "required": True,
                "label": "Manifest",
                "description": "Repo-relative or absolute path to an autonomy_runtime manifest JSON file; legacy meta_mission_queue manifests are accepted.",
            },
            "family": {
                "type": "string",
                "required": False,
                "label": "Family",
                "description": "Optional family override injected into queue items that do not already set family.",
            },
            "provider": {
                "type": "string",
                "required": False,
                "label": "Provider",
                "description": "Optional provider override injected into queue items that do not already set provider.",
            },
        },
        "optional_cli_flags": {
            "family": "--family {family}",
            "provider": "--provider {provider}",
        },
        "ui_group": "overnight_queue",
        "execution_mode": "detached",
        "principle_refs": ["pri_072", "pri_086", "pri_107", "pri_111"],
    },
    {
        "operation_id": "overnight_meta_mission_queue_resume",
        "label": "Resume autonomy runtime",
        "kicker": "overnight",
        "description_short": "Resume a manifest-backed autonomy runtime from its next durable item seam.",
        "command": "./repo-python tools/meta/factory/overnight_chain_runner.py run --manifest {manifest} --resume",
        "parameters_schema": {
            "manifest": {
                "type": "string",
                "required": True,
                "label": "Manifest",
                "description": "Repo-relative or absolute path to an autonomy_runtime manifest JSON file; legacy meta_mission_queue manifests are accepted.",
            },
            "family": {
                "type": "string",
                "required": False,
                "label": "Family",
                "description": "Optional family override injected into queue items that do not already set family.",
            },
            "provider": {
                "type": "string",
                "required": False,
                "label": "Provider",
                "description": "Optional provider override injected into queue items that do not already set provider.",
            },
        },
        "optional_cli_flags": {
            "family": "--family {family}",
            "provider": "--provider {provider}",
        },
        "ui_group": "overnight_queue",
        "execution_mode": "detached",
        "principle_refs": ["pri_072", "pri_086", "pri_107", "pri_111"],
    },
    {
        "operation_id": "overnight_meta_mission_queue_stop",
        "label": "Stop autonomy runtime",
        "kicker": "overnight",
        "description_short": "Request a graceful stop for a manifest-backed autonomy runtime at the next item seam.",
        "command": "./repo-python tools/meta/factory/overnight_chain_runner.py stop --manifest {manifest}",
        "parameters_schema": {
            "manifest": {
                "type": "string",
                "required": True,
                "label": "Manifest",
                "description": "Repo-relative or absolute path to an autonomy_runtime manifest JSON file; legacy meta_mission_queue manifests are accepted.",
            }
        },
        "ui_group": "overnight_queue",
        "execution_mode": "sync",
        "principle_refs": ["pri_072", "pri_086", "pri_107", "pri_111"],
    },
    {
        "operation_id": "doctrine_edge_validate",
        "label": "Validate doctrine edges",
        "kicker": "doctrine",
        "description_short": "Report doctrine edges still missing forward_gloss or reverse_gloss without mutating the corpus.",
        "command": "./repo-python tools/meta/factory/raw_seed_apply_loop.py edge-validate",
        "parameters_schema": {},
        "principle_refs": ["pri_072", "pri_086"],
    },
    {
        "operation_id": "doctrine_edge_migrate",
        "label": "Normalize doctrine edges",
        "kicker": "doctrine",
        "description_short": "Commit the bounded doctrine-edge migration and reciprocal back-mirror additions.",
        "command": "./repo-python tools/meta/factory/raw_seed_apply_loop.py edge-migrate --commit --apply-back-mirror",
        "parameters_schema": {},
        "principle_refs": ["pri_072", "pri_086"],
    },
    {
        "operation_id": "kernel_phase",
        "label": "Kernel phase",
        "kicker": "phase",
        "description_short": "Phase focus packet for a given phase id.",
        "command": "python3 kernel.py --phase {phase_id}",
        "parameters_schema": {
            "phase_id": {"type": "string", "required": True, "description": "Phase id, e.g. '09.17'."}
        },
        "principle_refs": ["pri_059"],
    },
    {
        "operation_id": "bridge_preflight",
        "label": "Bridge preflight",
        "kicker": "bridge",
        "description_short": "Run the bridge preflight script to validate adapter/route readiness.",
        "command": "./repo-python run_bridge_preflight.py",
        "parameters_schema": {},
        "principle_refs": ["pri_072"],
    },
    {
        "operation_id": "transcript_archaeology_scan",
        "label": "Transcript archaeology scan",
        "kicker": "archaeology",
        "description_short": "Scan local .claude + .codex + bridge transport surfaces and emit a capability fingerprint.",
        "command": "./repo-python -m system.lib.transcript_archaeology scan --scope {scope}",
        "parameters_schema": {
            "scope": {
                "type": "string",
                "required": False,
                "default": "local",
                "label": "Scope",
                "description": "'local' scans only repo-local surfaces. 'full' also samples ~/.claude/projects and ~/.codex/sessions (counts only, never content).",
            },
        },
        "principle_refs": ["pri_086", "pri_107"],
        "meta_mission_id": "transcript_archaeology",
        "meta_mission_run_source": "launcher",
    },
    {
        "operation_id": "session_heartbeat_snapshot",
        "label": "Session heartbeat snapshot",
        "kicker": "heartbeat",
        "description_short": "Snapshot live Claude Code and Codex session heartbeats from the bridge transport artifacts.",
        "command": "./repo-python -m system.lib.session_heartbeat snapshot",
        "parameters_schema": {},
        "principle_refs": ["pri_086"],
        "meta_mission_id": "session_heartbeat_watch",
        "meta_mission_run_source": "launcher",
    },
]


def _operation_dispatch_policy_payload(repo_root: Path, op: Mapping[str, Any]) -> dict[str, Any]:
    mission_id = str(op.get("dispatch_policy_mission_id") or "").strip()
    if not mission_id:
        return {}
    try:
        template = load_mission_template(repo_root, mission_id)
    except ValueError:
        try:
            template = load_mission_template(Path(__file__).resolve().parents[2], mission_id)
        except ValueError:
            return {}
    authored_dispatch_policy = (
        template.get("dispatch_policy")
        if isinstance(template.get("dispatch_policy"), Mapping)
        else {}
    )
    summary = summarize_dispatch_policy(
        mission_dispatch_policy={
            **dict(authored_dispatch_policy or {}),
            "mission_id": mission_id,
        },
        provider_capabilities_path=repo_root / "tools/meta/bridge/provider_capabilities.json",
    )
    binding = dict(op.get("dispatch_policy_binding") or {})
    schema = op.get("parameters_schema") if isinstance(op.get("parameters_schema"), Mapping) else {}
    provider_param = str(binding.get("provider_param") or "").strip() or None
    default_provider = None
    if provider_param and isinstance(schema.get(provider_param), Mapping):
        default_provider = str(schema[provider_param].get("default") or "").strip() or None
    provider_ceilings = (
        summary.get("provider_ceilings")
        if isinstance(summary.get("provider_ceilings"), Mapping)
        else {}
    )
    provider_ceiling = None
    if default_provider and provider_ceilings.get(default_provider) is not None:
        provider_ceiling = int(provider_ceilings.get(default_provider) or 0)
    return {
        **summary,
        **binding,
        "default_provider": default_provider,
        "provider_ceiling": provider_ceiling,
    }


def _operation_meta_mission_payload(repo_root: Path, op: Mapping[str, Any]) -> dict[str, Any]:
    """Return the compact meta-mission career block for one launcher operation.

    - Teleology: Surface just enough registry + workspace info to the Station tile
      and the /meta-missions lens so the operator sees career context without a
      second fetch — mission title, workspace root, last-run status, and totals.
    - Mechanism: Resolve the registry entry by meta_mission_id and call
      aggregate_metrics/list_runs from meta_mission_workspace. Safe on missing
      registry (returns an empty dict and the tile renders without career info).
    """
    mission_id = str(op.get("meta_mission_id") or "").strip()
    if not mission_id:
        return {}
    try:
        entry = _mmw.resolve_mission_entry(repo_root, mission_id)
    except Exception:
        entry = None
    if entry is None:
        return {"mission_id": mission_id}
    try:
        metrics = _mmw.aggregate_metrics(repo_root, mission_id)
    except Exception:
        metrics = {}
    return {
        "mission_id": mission_id,
        "title": str(entry.get("title") or mission_id),
        "kind": str(entry.get("kind") or ""),
        "status": str(entry.get("status") or ""),
        "workspace_root": str(entry.get("workspace_root") or f"state/meta_missions/{mission_id}"),
        "runtime_surface": entry.get("runtime_surface"),
        "supports_resume": bool(entry.get("supports_resume")),
        "input_unit_label": entry.get("input_unit_label"),
        "template_version": entry.get("template_version"),
        "run_source": str(op.get("meta_mission_run_source") or "launcher").strip() or "launcher",
        "metrics": metrics,
        "last_run": metrics.get("last_run") if isinstance(metrics, Mapping) else None,
    }


def _enrich_operations_with_navigation_freshness(
    repo_root: Path,
    payload: Mapping[str, Any],
) -> Dict[str, Any]:
    next_payload = copy.deepcopy(dict(payload))
    operations = [
        dict(op)
        for op in list(next_payload.get("operations") or [])
        if isinstance(op, Mapping)
    ]
    navigation_freshness = load_navigation_freshness_snapshot(repo_root)
    top_source = str(navigation_freshness.get("top_source_kind") or "").strip()
    stale_source_count = _safe_int(navigation_freshness.get("stale_source_count"), 0)
    stale_row_count = _safe_int(navigation_freshness.get("stale_or_missing_row_count"), 0)
    top_queue = (
        navigation_freshness.get("queue", [])[0]
        if isinstance(navigation_freshness.get("queue"), list)
        and navigation_freshness.get("queue")
        else {}
    )
    for op in operations:
        if op.get("operation_id") != "navigator_refresh":
            continue
        params = {
            str(name): dict(spec) if isinstance(spec, Mapping) else spec
            for name, spec in dict(op.get("parameters_schema") or {}).items()
        }
        kind_schema = dict(params.get("kind") or {})
        if top_source:
            kind_schema["default"] = top_source
            kind_schema["description"] = (
                f"Recommended next stale embedding source kind: {top_source}. "
                "Use 'all' only when intentionally refreshing every indexed source."
            )
            op["description_short"] = (
                f"Refresh stale navigation embeddings; {stale_source_count} source kind(s) "
                f"currently report {stale_row_count} stale/missing row(s)."
            )
            op["runtime_attention"] = {
                "kind": "navigation_freshness",
                "tone": "warn",
                "label": "Navigation substrate stale",
                "detail": (
                    f"{top_source}: "
                    f"{_safe_int(top_queue.get('stale_or_missing'), 0)} stale/missing row(s)"
                ),
                "source_kind": top_source,
                "stale_source_count": stale_source_count,
                "stale_or_missing_row_count": stale_row_count,
            }
        params["kind"] = kind_schema
        op["parameters_schema"] = params
    next_payload["operations"] = operations
    next_payload["navigation_freshness"] = navigation_freshness
    return next_payload


_RAW_SEED_PIPELINE_SOURCE_PATH_KEYS = (
    "extracted_shards_path",
    "raw_seed_shards_path",
    "raw_seed_coverage_path",
    "raw_seed_atomization_ledger_path",
    "raw_seed_coverage_enriched_path",
    "raw_seed_routing_review_path",
    "codex_surface_queue_path",
)


def _operation_group_id(operation: Mapping[str, Any]) -> str:
    token = str(operation.get("ui_group") or operation.get("kicker") or "general").strip()
    if not token:
        return "general"
    return token.lower().replace("-", "_").replace(" ", "_")


def _operation_group_label(group_id: str) -> str:
    return " ".join(part for part in group_id.split("_") if part).title() or "General"


def _prepared_quick_action(
    repo_root: Path,
    *,
    operation_id: str,
    label: str,
    detail: str,
    parameters: Mapping[str, Any] | None = None,
    tone: str = "info",
) -> Dict[str, Any]:
    resolved_parameters = dict(parameters or {})
    command: Optional[str] = None
    try:
        prepared = _shared_prepare_launch_operation(
            repo_root,
            operation_id=operation_id,
            parameters=resolved_parameters,
        )
        command = prepared.command
        resolved_parameters = dict(prepared.resolved_parameters or resolved_parameters)
    except Exception as exc:
        logger.debug("ops launcher quick-action render failed for %s: %s", operation_id, exc)
    return {
        "operation_id": operation_id,
        "label": label,
        "detail": detail,
        "tone": tone,
        "parameters": resolved_parameters,
        "command": command,
    }


def _raw_seed_pipeline_family_context(repo_root: Path) -> Tuple[Optional[str], Optional[str]]:
    family_dir = _resolve_active_family_dir(repo_root)
    phase_family_json = (
        _safe_read_json(repo_root, f"{family_dir}/phase_family.json")
        if family_dir
        else {}
    )
    if not isinstance(phase_family_json, Mapping):
        phase_family_json = {}
    family_number = str(phase_family_json.get("family_number") or "").strip() or None
    if family_number is None and family_dir:
        match = re.match(r"^(\d+)", Path(family_dir).name)
        if match:
            family_number = match.group(1)
    return family_dir, family_number


def _compact_raw_seed_pipeline_for_operations(
    repo_root: Path,
    raw_seed_pipeline: Mapping[str, Any],
) -> Dict[str, Any]:
    if not isinstance(raw_seed_pipeline, Mapping) or not raw_seed_pipeline:
        return {
            "available": False,
            "family_dir": None,
            "family_number": None,
            "substrate": "raw_seed",
            "provider": None,
            "provider_ceiling": 0,
            "fresh_pending_bins": 0,
            "pending_routing_bins": 0,
            "pending_routing_shards": 0,
            "review_queue_bins": 0,
            "review_queue_entries": 0,
            "next_actions": [],
            "warnings": ["raw_seed_pipeline_snapshot_unavailable"],
            "source_paths": {},
        }

    provider = str(raw_seed_pipeline.get("provider") or "").strip() or "chatgpt"
    family_number = str(raw_seed_pipeline.get("family_number") or "").strip() or "09"
    cohort_size = _safe_int(raw_seed_pipeline.get("cohort_size"), 10)
    wave_width = _safe_int(
        raw_seed_pipeline.get("wave_width_effective")
        or raw_seed_pipeline.get("effective_active_workers"),
        3,
    )
    source_paths = {
        key: raw_seed_pipeline.get(key)
        for key in _RAW_SEED_PIPELINE_SOURCE_PATH_KEYS
        if raw_seed_pipeline.get(key)
    }
    fresh_pending_bins = _safe_int(raw_seed_pipeline.get("fresh_pending_bins"), 0)
    pending_routing_bins = _safe_int(raw_seed_pipeline.get("pending_routing_bins"), 0)
    pending_routing_shards = _safe_int(raw_seed_pipeline.get("pending_routing_shards"), 0)
    review_queue_bins = _safe_int(raw_seed_pipeline.get("review_queue_bins"), 0)
    review_queue_entries = _safe_int(raw_seed_pipeline.get("review_queue_entries"), 0)
    next_actions: List[Dict[str, Any]] = []

    if fresh_pending_bins > 0:
        next_actions.append(
            _prepared_quick_action(
                repo_root,
                operation_id="raw_seed_sync_handoff_launch",
                label="Process fresh frontier",
                detail=f"{fresh_pending_bins} fresh bin(s) are ready for sync handoff.",
                parameters={"family": family_number, "provider": provider},
                tone="warn",
            )
        )
    if pending_routing_bins > 0 or pending_routing_shards > 0:
        next_actions.append(
            _prepared_quick_action(
                repo_root,
                operation_id="raw_seed_route_review",
                label="Route raw-seed backlog",
                detail=(
                    f"{pending_routing_bins} pending bin(s) / "
                    f"{pending_routing_shards} atom member(s) need route review."
                ),
                parameters={
                    "family": family_number,
                    "substrate": str(raw_seed_pipeline.get("substrate") or "raw_seed"),
                    "provider": provider,
                    "cohort_size": cohort_size,
                    "wave_width": wave_width,
                    "selection_mode": "fresh_first",
                },
                tone="warn" if pending_routing_bins > 0 else "info",
            )
        )
    if review_queue_bins > 0 or review_queue_entries > 0:
        next_actions.append(
            _prepared_quick_action(
                repo_root,
                operation_id="raw_seed_apply_routing",
                label="Apply routed doctrine",
                detail=(
                    f"{review_queue_bins} review bin(s) / "
                    f"{review_queue_entries} member proposal(s) are waiting."
                ),
                parameters={"family": family_number},
                tone="info",
            )
        )

    return {
        "available": True,
        "family_dir": raw_seed_pipeline.get("family_dir"),
        "family_number": family_number,
        "substrate": raw_seed_pipeline.get("substrate") or "raw_seed",
        "provider": provider,
        "provider_ceiling": _safe_int(raw_seed_pipeline.get("provider_ceiling"), 0),
        "cohort_size": cohort_size,
        "wave_width_requested": raw_seed_pipeline.get("wave_width_requested"),
        "wave_width_effective": wave_width,
        "fresh_pending_bins": fresh_pending_bins,
        "pending_routing_bins": pending_routing_bins,
        "pending_routing_shards": pending_routing_shards,
        "review_queue_bins": review_queue_bins,
        "review_queue_entries": review_queue_entries,
        "surface_queue_entries": _safe_int(raw_seed_pipeline.get("surface_queue_entries"), 0),
        "atomization_pending_paragraphs": _safe_int(
            raw_seed_pipeline.get("atomization_pending_paragraphs"),
            0,
        ),
        "last_updated": raw_seed_pipeline.get("last_updated"),
        "top_pending_routing_group": (
            dict(raw_seed_pipeline.get("top_pending_routing_group") or {})
            if isinstance(raw_seed_pipeline.get("top_pending_routing_group"), Mapping)
            else None
        ),
        "pending_routing_groups": [
            dict(item)
            for item in list(raw_seed_pipeline.get("pending_routing_groups") or [])[:5]
            if isinstance(item, Mapping)
        ],
        "next_actions": next_actions,
        "warnings": [],
        "source_paths": source_paths,
    }


def _load_operations_raw_seed_pipeline(repo_root: Path) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    errors: List[Dict[str, str]] = []
    try:
        family_dir, family_number = _raw_seed_pipeline_family_context(repo_root)
        raw_seed_pipeline = load_raw_seed_pipeline_snapshot(
            repo_root,
            family_dir=family_dir,
            family_number=family_number,
        ) or {}
    except Exception as exc:
        logger.debug("ops launcher raw-seed pipeline load failed: %s", exc)
        errors.append(
            {
                "source": "raw_seed_pipeline",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        raw_seed_pipeline = {}
    return _compact_raw_seed_pipeline_for_operations(repo_root, raw_seed_pipeline), errors


def _build_operation_groups(
    operations: Sequence[Mapping[str, Any]],
    *,
    navigation_freshness: Mapping[str, Any],
    raw_seed_pipeline: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    for operation in operations:
        grouped.setdefault(_operation_group_id(operation), []).append(operation)

    groups: List[Dict[str, Any]] = []
    for group_id in sorted(grouped):
        group_operations = grouped[group_id]
        recommended_operation_ids: List[str] = []
        live_status: Dict[str, Any] = {}
        if group_id == "navigation":
            if _safe_int(navigation_freshness.get("stale_source_count"), 0) > 0:
                recommended_operation_ids.append("navigator_refresh")
            live_status = {
                "stale_source_count": _safe_int(
                    navigation_freshness.get("stale_source_count"),
                    0,
                ),
                "stale_or_missing_row_count": _safe_int(
                    navigation_freshness.get("stale_or_missing_row_count"),
                    0,
                ),
                "top_source_kind": navigation_freshness.get("top_source_kind"),
            }
        elif group_id == "raw_seed":
            for action in raw_seed_pipeline.get("next_actions") or []:
                if isinstance(action, Mapping) and action.get("operation_id"):
                    recommended_operation_ids.append(str(action["operation_id"]))
            live_status = {
                "fresh_pending_bins": _safe_int(
                    raw_seed_pipeline.get("fresh_pending_bins"),
                    0,
                ),
                "pending_routing_bins": _safe_int(
                    raw_seed_pipeline.get("pending_routing_bins"),
                    0,
                ),
                "pending_routing_shards": _safe_int(
                    raw_seed_pipeline.get("pending_routing_shards"),
                    0,
                ),
                "review_queue_bins": _safe_int(raw_seed_pipeline.get("review_queue_bins"), 0),
                "review_queue_entries": _safe_int(
                    raw_seed_pipeline.get("review_queue_entries"),
                    0,
                ),
            }
        groups.append(
            {
                "group_id": group_id,
                "label": _operation_group_label(group_id),
                "operation_count": len(group_operations),
                "operation_ids": [
                    str(operation.get("operation_id") or "")
                    for operation in group_operations
                    if operation.get("operation_id")
                ],
                "recommended_operation_ids": list(dict.fromkeys(recommended_operation_ids)),
                "live_status": live_status,
            }
        )
    return groups


def _ops_launcher_alerts(
    *,
    navigation_freshness: Mapping[str, Any],
    raw_seed_pipeline: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    top_nav = (
        navigation_freshness.get("queue", [])[0]
        if isinstance(navigation_freshness.get("queue"), list)
        and navigation_freshness.get("queue")
        else None
    )
    if isinstance(top_nav, Mapping):
        recommended = top_nav.get("recommended_operation")
        alerts.append(
            {
                "id": "navigation_freshness",
                "tone": "warn",
                "label": "Navigation substrate stale",
                "detail": (
                    f"{top_nav.get('source_kind')}: "
                    f"{_safe_int(top_nav.get('stale_or_missing'), 0)} stale/missing row(s)"
                ),
                "operation_id": (
                    recommended.get("operation_id")
                    if isinstance(recommended, Mapping)
                    else "navigator_refresh"
                ),
                "parameters": (
                    dict(recommended.get("parameters") or {})
                    if isinstance(recommended, Mapping)
                    else {"kind": top_nav.get("source_kind")}
                ),
                "command": (
                    recommended.get("command")
                    if isinstance(recommended, Mapping)
                    else None
                ),
            }
        )
    for action in raw_seed_pipeline.get("next_actions") or []:
        if not isinstance(action, Mapping):
            continue
        alerts.append(
            {
                "id": f"raw_seed:{action.get('operation_id')}",
                "tone": action.get("tone") or "info",
                "label": action.get("label"),
                "detail": action.get("detail"),
                "operation_id": action.get("operation_id"),
                "parameters": dict(action.get("parameters") or {}),
                "command": action.get("command"),
            }
        )
    return alerts


def _build_ops_launcher_snapshot(repo_root: Path, payload: Mapping[str, Any]) -> Dict[str, Any]:
    next_payload = _enrich_operations_with_navigation_freshness(repo_root, payload)
    operations = [
        dict(op)
        for op in list(next_payload.get("operations") or [])
        if isinstance(op, Mapping)
    ]
    raw_seed_pipeline, errors = _load_operations_raw_seed_pipeline(repo_root)
    navigation_freshness = (
        dict(next_payload.get("navigation_freshness") or {})
        if isinstance(next_payload.get("navigation_freshness"), Mapping)
        else {}
    )
    next_payload.update(
        {
            "schema": "ops_launcher_snapshot_v1",
            "operations": operations,
            "operation_groups": _build_operation_groups(
                operations,
                navigation_freshness=navigation_freshness,
                raw_seed_pipeline=raw_seed_pipeline,
            ),
            "navigation_freshness": navigation_freshness,
            "raw_seed_pipeline": raw_seed_pipeline,
            "quick_actions": [
                action
                for action in list(raw_seed_pipeline.get("next_actions") or [])
                if isinstance(action, Mapping)
            ],
            "alerts": _ops_launcher_alerts(
                navigation_freshness=navigation_freshness,
                raw_seed_pipeline=raw_seed_pipeline,
            ),
            "errors": errors,
        }
    )
    return next_payload


def list_launchable_operations(repo_root: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Publish a stable, SAFE catalog of operations that the cockpit can
      launch from the operator surface. Gate-bypass and generic command execution
      are explicitly excluded — this catalog is limited to whitelisted browse and
      bounded workflow operations. Operations tagged with `meta_mission_id` carry
      a compact career block so the /meta-missions lens can render last-run status
      inline with the launcher.
    - Mechanism: Return a static copy of the in-module catalog with a UTC timestamp
      and a per-operation meta-mission block when the op maps to a registered
      career.
    - Guarantee: Returns `{"operations": [...], "generated_at": <utc iso>}` on success,
      `{"operations": [], "error": "..."}` on any unexpected failure.
    - Fails: None.
    - When-needed: Open when the cockpit needs to enumerate what operations are safe
      to launch over HTTP without reading the kernel source itself.
    - Escalates-to: system/server/world_model.py::launch_operation; system/server/main.py
    - Navigation-group: server_backend
    """
    return _cached_mapping(
        cache=_OPERATIONS_CATALOG_CACHE,
        lock=_OPERATIONS_CATALOG_CACHE_LOCK,
        repo_root=repo_root,
        loader=lambda: _build_ops_launcher_snapshot(
            repo_root,
            _shared_list_launchable_operations(repo_root),
        ),
        ttl_s=_OPERATIONS_CATALOG_CACHE_TTL_S,
    )


def preview_launch_operation(
    repo_root: Path,
    *,
    operation_id: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Validate and render a catalogued SAFE operation without
      executing it so the cockpit can show the backend-authoritative command
      preview before launch.
    - Mechanism: Delegate to `_shared_prepare_launch_operation(...)` and return
      the rendered command, execution mode, and resolved parameters.
    - Guarantee: Returns `{"ok": True, "preview": {...}}` on success or
      `{"ok": False, "error": "..."}` on validation/policy failure.
    - Fails: None (exception-safe for expected validation errors).
    """
    try:
        prepared = _shared_prepare_launch_operation(
            repo_root,
            operation_id=operation_id,
            parameters=parameters or {},
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    return {
        "ok": True,
        "preview": {
            "operation_id": operation_id,
            "command": prepared.command,
            "execution_mode": prepared.execution_mode,
            "resolved_parameters": dict(prepared.resolved_parameters or {}),
        },
    }


def _find_launchable_op(operation_id: str) -> Optional[Dict[str, Any]]:
    for op in _LAUNCHABLE_OPERATIONS_CATALOG:
        if op["operation_id"] == operation_id:
            return op
    return None


def _validate_and_render_command(
    op: Mapping[str, Any], parameters: Mapping[str, Any]
) -> Tuple[Optional[str], Optional[str]]:
    """Validate parameters against the op schema and render the shell command.

    Returns `(command, None)` on success or `(None, error_string)` on failure.
    """
    schema = op.get("parameters_schema") or {}
    command_template = str(op.get("command") or "")
    resolved: Dict[str, str] = {}
    for name, spec in schema.items():
        required = bool(spec.get("required")) if isinstance(spec, Mapping) else False
        default = spec.get("default") if isinstance(spec, Mapping) else None
        raw_value = parameters.get(name) if parameters else None
        if raw_value is None or raw_value == "":
            if required and default is None:
                return None, f"missing required parameter: {name}"
            if default is not None:
                raw_value = default
            else:
                continue
        if not isinstance(raw_value, (str, int, float)):
            return None, f"parameter '{name}' must be a primitive (str/int/float)"
        str_value = str(raw_value).strip()
        if not str_value:
            if required:
                return None, f"parameter '{name}' cannot be empty"
            continue
        spec_type = str(spec.get("type") or "").strip().lower() if isinstance(spec, Mapping) else ""
        if spec_type == "integer":
            try:
                int_value = int(str_value)
            except ValueError:
                return None, f"parameter '{name}' must be an integer"
            minimum = spec.get("minimum") if isinstance(spec, Mapping) else None
            maximum = spec.get("maximum") if isinstance(spec, Mapping) else None
            if isinstance(minimum, (int, float)) and int_value < int(minimum):
                return None, f"parameter '{name}' must be >= {int(minimum)}"
            if isinstance(maximum, (int, float)) and int_value > int(maximum):
                return None, f"parameter '{name}' must be <= {int(maximum)}"
            resolved[name] = str(int_value)
            continue
        if not _LAUNCHABLE_PARAM_VALUE_RE.match(str_value):
            return (
                None,
                f"parameter '{name}' contains disallowed characters; "
                "only [A-Za-z0-9_./-] are allowed",
            )
        resolved[name] = str_value
    if parameters:
        unknown = [k for k in parameters.keys() if k not in schema]
        if unknown:
            return None, f"unknown parameters: {sorted(unknown)}"
    try:
        rendered = command_template.format(**resolved)
    except KeyError as exc:
        return None, f"missing required parameter: {exc.args[0]}"
    return rendered, None


def _launcher_meta_mission_env(
    *,
    meta_mission_id: str,
    meta_mission_run_id: str | None,
    execution_mode: str,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(base_env or os.environ)
    if meta_mission_id and meta_mission_run_id and execution_mode == "sync":
        env["AIWF_META_MISSION_RUN_ID"] = meta_mission_run_id
        env["AIWF_META_MISSION_LIFECYCLE_OWNER"] = "launcher"
    return env


def launch_operation(
    repo_root: Path,
    *,
    operation_id: str,
    parameters: Optional[Dict[str, Any]] = None,
    actor_id: str,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Execute a catalogued SAFE operation from the cockpit and record the
      launch in the orchestration event log. Refuses anything that smells like an
      apply-gate bypass (`--apply` in the command or payload) and enforces any
      bounded validation policy published on the whitelisted operation.
    - Mechanism: Look up `operation_id` in `_LAUNCHABLE_OPERATIONS_CATALOG`, validate
      parameters against the schema, render the command with sanitized substitutions
      (only `[A-Za-z0-9_./-]`), run via `subprocess.run(timeout=30, capture_output=True,
      cwd=repo_root)`, and append an `operation_launched` event with returncode,
      duration, and first-4KB stdout.
    - Guarantee: Returns `{"ok": True, "result": {...}}` on success or
      `{"ok": False, "error": "..."}` on validation/timeout/apply-gate failure.
    - Fails: None (exception-safe).
    - When-needed: Open when the cockpit needs to trigger a catalog operation over
      HTTP with full traceability.
    - Escalates-to: system/server/world_model.py::list_launchable_operations;
      system/server/world_model.py::_append_orchestration_event; system/server/main.py
    - Navigation-group: server_backend
    """
    import shlex
    import subprocess  # local import — this module is otherwise fully pure

    actor = (actor_id or "").strip()
    if not actor:
        return {"ok": False, "error": "actor_id is required"}
    try:
        prepared = _shared_prepare_launch_operation(
            repo_root,
            operation_id=operation_id,
            parameters=parameters or {},
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    started_at = datetime.now(timezone.utc)
    op = prepared.operation
    execution_mode = prepared.execution_mode
    resolved_parameters = dict(prepared.resolved_parameters or {})

    # Meta-mission workspace run (launcher-owned path only). Detached chain-runner
    # ops write their own parent/child runs from inside the runner, so we skip
    # those here to avoid double-logging. A start_run failure never blocks the
    # op — workspace bookkeeping is additive, the orchestration event log is the
    # hard-truth surface.
    meta_mission_id = str(op.get("meta_mission_id") or "").strip()
    mm_run_id = _shared_start_meta_mission_run(
        repo_root,
        prepared=prepared,
        operation_id=operation_id,
        parameters=parameters or {},
        trigger="operator",
    )

    subprocess_env = _shared_launcher_meta_mission_env(
        meta_mission_id=meta_mission_id,
        meta_mission_run_id=mm_run_id,
        execution_mode=execution_mode,
    )

    try:
        argv = shlex.split(prepared.command)
        if execution_mode == "detached":
            log_dir = repo_root / "state" / "launcher_ops"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"{started_at.strftime('%Y%m%dT%H%M%SZ').lower()}_{operation_id}.log"
            log_handle = log_path.open("w", encoding="utf-8")
            process = subprocess.Popen(
                argv,
                cwd=str(repo_root),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=subprocess_env,
            )
            log_handle.close()
            result = {
                "operation_id": operation_id,
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "duration_ms": 0,
                "detached": True,
                "pid": int(process.pid),
                "log_path": str(log_path.relative_to(repo_root)),
                "resolved_parameters": resolved_parameters,
            }
            event = {
                "kind": "operation_launched",
                "schema_version": "operation_launched_v1",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "operation_id": operation_id,
                "actor_id": actor,
                "command": prepared.command,
                "returncode": None,
                "duration_ms": 0,
                "truncated_stdout": "",
                "detached": True,
                "pid": int(process.pid),
                "log_path": str(log_path.relative_to(repo_root)),
                "resolved_parameters": resolved_parameters,
                "event_id": _new_event_id("op", started_at),
            }
            _append_orchestration_event(repo_root, event)
            return {"ok": True, "result": result}

        proc = subprocess.run(
            argv,
            timeout=30,
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            env=subprocess_env,
        )
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        stdout = (proc.stdout or "")[:4096]
        stderr = (proc.stderr or "")[:1024]
        artifact_refs = _shared_artifact_refs_from_operation_output(proc.stdout or "")
        output_fields = _shared_operation_event_fields_from_operation_output(proc.stdout or "")
        result = {
            "operation_id": operation_id,
            "returncode": int(proc.returncode),
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": duration_ms,
            "artifact_refs": artifact_refs,
            "resolved_parameters": resolved_parameters,
            **output_fields,
        }
        event = {
            "kind": "operation_launched",
            "schema_version": "operation_launched_v1",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "operation_id": operation_id,
            "actor_id": actor,
            "command": prepared.command,
            "returncode": int(proc.returncode),
            "duration_ms": duration_ms,
            "truncated_stdout": stdout,
            "resolved_parameters": resolved_parameters,
            "event_id": _new_event_id("op", started_at),
            "meta_mission_id": meta_mission_id or None,
            "meta_mission_run_id": mm_run_id,
            **output_fields,
        }
        _append_orchestration_event(repo_root, event)
        _shared_finalize_meta_mission_run(
            repo_root,
            prepared=prepared,
            run_id=mm_run_id,
            status="succeeded" if int(proc.returncode) == 0 else "failed",
            error=(stderr or None) if int(proc.returncode) != 0 else None,
            artifact_refs=artifact_refs,
            extra={
                "returncode": int(proc.returncode),
                "duration_ms": duration_ms,
                "command": prepared.command,
                "resolved_parameters": resolved_parameters,
                **output_fields,
            },
        )
        return {"ok": True, "result": result}
    except subprocess.TimeoutExpired:
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        event = {
            "kind": "operation_launched",
            "schema_version": "operation_launched_v1",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "operation_id": operation_id,
            "actor_id": actor,
            "command": prepared.command,
            "returncode": -1,
            "duration_ms": duration_ms,
            "truncated_stdout": "",
            "timed_out": True,
            "resolved_parameters": resolved_parameters,
            "event_id": _new_event_id("op", started_at),
            "meta_mission_id": meta_mission_id or None,
            "meta_mission_run_id": mm_run_id,
        }
        _append_orchestration_event(repo_root, event)
        _shared_finalize_meta_mission_run(
            repo_root,
            prepared=prepared,
            run_id=mm_run_id,
            status="failed",
            error="operation timed out after 30s",
            extra={"duration_ms": duration_ms, "command": prepared.command, "resolved_parameters": resolved_parameters},
        )
        return {"ok": False, "error": f"operation timed out after 30s: {operation_id}"}
    except FileNotFoundError as exc:
        _shared_finalize_meta_mission_run(
            repo_root,
            prepared=prepared,
            run_id=mm_run_id,
            status="failed",
            error=f"executable not found: {exc}",
        )
        return {"ok": False, "error": f"executable not found: {exc}"}
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("launch_operation failed: %s", exc)
        _shared_finalize_meta_mission_run(
            repo_root,
            prepared=prepared,
            run_id=mm_run_id,
            status="failed",
            error=f"{type(exc).__name__}: {exc}",
        )
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


# --- Code Architecture Projection Plane transport (per codeflow_assimilation.md) ---

CODE_MAP_MAX_FILES_CAP = 1000
BLAST_RADIUS_MAX_DEPTH_CAP = 12
SYSTEM_ATLAS_MAX_ENTITIES_CAP = 1000
SYSTEM_ATLAS_MAX_DEPTH_CAP = 4


def _normalize_projection_path(value: str | None) -> str | None:
    """
    [ACTION]
    - Teleology: Normalize a repo-relative path string from an HTTP query param at the endpoint boundary so the shared projection library never sees absolute paths, parent traversal, or NUL bytes.
    - Mechanism: Strip whitespace, convert backslashes to forward slashes, reject NUL bytes / absolute prefixes / parent-traversal segments, collapse repeated separators.
    - Reads: The raw value.
    - Guarantee: Returns the canonicalized repo-relative path, or None when the input is None / empty after stripping.
    - Fails: Raises ValueError with a one-line reason for any normalization rejection (NUL, absolute prefix, parent traversal).
    """
    if value is None:
        return None
    path = str(value).strip().replace("\\", "/")
    if not path:
        return None
    if "\x00" in path:
        raise ValueError("NUL byte is not allowed")
    if path.startswith("/") or path.startswith("~"):
        raise ValueError("path must be repo-relative")
    parts = [part for part in path.split("/") if part]
    if any(part == ".." for part in parts):
        raise ValueError("parent traversal is not allowed")
    return "/".join(parts)


def load_code_map_snapshot(
    repo_root: Path,
    *,
    focus: str | None = None,
    max_files: int = 300,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Endpoint-side wrapper over `system.lib.code_architecture_projection.build_code_map_packet`. Owns input normalization + budget clamping only; never reads hologram artifacts, never builds overlays, never invents schema.
    - Mechanism: Normalize `focus` via `_normalize_projection_path`, clamp `max_files` into `[1, CODE_MAP_MAX_FILES_CAP]`, delegate to `build_code_map_packet`.
    - Reads: Whatever the shared library reads.
    - Guarantee: Returns the same `code_map_packet_v1` dict the kernel `--code-map` command emits.
    - Fails: Raises ValueError on bad path syntax (NUL/absolute/traversal); all other absences degrade gracefully through the packet's `omission_receipt`.
    """
    normalized_focus = _normalize_projection_path(focus)
    clamped_max_files = max(1, min(int(max_files or 300), CODE_MAP_MAX_FILES_CAP))
    return build_code_map_packet(
        root=repo_root,
        focus_path=normalized_focus,
        max_files=clamped_max_files,
        include_overlays=True,
    )


def load_blast_radius_snapshot(
    repo_root: Path,
    *,
    path: str | None,
    max_depth: int = 4,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Endpoint-side wrapper over `system.lib.code_architecture_projection.build_blast_radius_packet`. Owns input normalization + budget clamping only; never walks the graph or computes BFS itself.
    - Mechanism: Normalize `path` via `_normalize_projection_path`, raise ValueError when it normalizes to None, clamp `max_depth` into `[1, BLAST_RADIUS_MAX_DEPTH_CAP]`, delegate to `build_blast_radius_packet`.
    - Reads: Whatever the shared library reads.
    - Guarantee: Returns the same `blast_radius_packet_v1` dict the kernel `--blast-radius` command emits. Valid-but-unknown targets degrade through the packet's `risk.confidence='low'` + `risk_reasons=['target_not_in_hologram']`, never through an exception.
    - Fails: Raises ValueError on missing path or bad path syntax.
    """
    normalized_path = _normalize_projection_path(path)
    if not normalized_path:
        raise ValueError("path is required")
    clamped_max_depth = max(1, min(int(max_depth or 4), BLAST_RADIUS_MAX_DEPTH_CAP))
    return build_blast_radius_packet(
        root=repo_root,
        target_path=normalized_path,
        max_depth=clamped_max_depth,
        include_system_impact=True,
    )


def _projection_csv(value: str | None) -> list[str] | None:
    if value is None:
        return None
    rows = [part.strip() for part in str(value).split(",") if part.strip()]
    return rows or None


def _normalize_projection_id(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "\x00" in text:
        raise ValueError("NUL byte is not allowed")
    return text


def load_system_atlas_graph_snapshot(
    repo_root: Path,
    *,
    focus: str | None = None,
    kinds: str | None = None,
    relations: str | None = None,
    max_entities: int = 400,
    max_depth: int = 2,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Endpoint-side wrapper over `system.lib.system_atlas_projection.build_system_atlas_packet`. Owns query normalization + budget clamping only; never reads the generated graph or invents packet schema.
    - Mechanism: Normalize focus id, split comma-delimited kind/relation filters, clamp max_entities/max_depth, delegate to the shared projection library.
    - Reads: Whatever the shared library reads.
    - Guarantee: Returns one `system_atlas_packet_v1` dict over the generated System Atlas graph.
    - Fails: Raises ValueError for invalid focus syntax; missing graph degrades through the packet's `omission_receipt`.
    """
    normalized_focus = _normalize_projection_id(focus)
    clamped_max_entities = max(1, min(int(max_entities or 400), SYSTEM_ATLAS_MAX_ENTITIES_CAP))
    clamped_max_depth = max(0, min(int(max_depth if max_depth is not None else 2), SYSTEM_ATLAS_MAX_DEPTH_CAP))
    return build_system_atlas_packet(
        repo_root,
        focus_id=normalized_focus,
        kinds=_projection_csv(kinds),
        relations=_projection_csv(relations),
        max_entities=clamped_max_entities,
        max_depth=clamped_max_depth,
    )
