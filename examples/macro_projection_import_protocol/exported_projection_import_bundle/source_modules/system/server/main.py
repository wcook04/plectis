"""
[PURPOSE]
- Teleology: Serve Zenith's HTTP API (REST + WebSocket) and static frontend.
- Mechanism: FastAPI app with lifespan startup/shutdown; session orchestration via SessionManager; filesystem translation via Translator; code inspection via InspectorService; secure mutation via MetaService.
- Updates: master_config writes create a .bak backup and a one-time base truth (master_config.base.json); UI config endpoint relies on its Pydantic schema.

[INTERFACE]
- Inputs: HTTP requests under /api/*; WebSocket connections at /ws/telemetry; filesystem repo root at REPO_ROOT.
- Outputs: JSON responses (Pydantic schemas); static files served from /static; logs written to state/server_debug.log.
- Exports: app (FastAPI), REPO_ROOT (Path), endpoint functions registered via decorators.

[FLOW]
- Ingest: Resolve REPO_ROOT; configure file+stdout logging.
- Start: lifespan() validates master_config.json if present; starts broadcaster(session_manager).
- Serve: Endpoints delegate to Translator/SessionManager/InspectorService/MetaService and graph compilers.
- Shutdown: lifespan cancels broadcaster and calls session_manager.shutdown().

[DEPENDENCIES]
- pypi.fastapi: FastAPI, HTTPException, WebSocket, routing/middleware, FileResponse.
- pypi.uvicorn: server runtime/loggers.
- pypi.python-dotenv: env loading (process-level).
- system.server.session: SessionManager (run orchestration, telemetry/log access).
- system.server.translator: Translator, TranslationError (lobby/candidate generation).
- system.server.graph: compile_physics_graph, compile_mission_view.
- system.server.inspector: InspectorService (codex tree/file inspection).
- system.server.meta_service: MetaService (secure mutation/observation tools).
- system.server.schemas: API schemas (Pydantic).
- system.core.forensics: reconstruct_run_state (post-run reconstruction).
- system.lib.utils: resolve_value, deep_merge (config path unwrapping, merging).
- Files: master_config.json; master_config.json.bak; master_config.base.json; state/server_debug.log; state/runs/<run_id>/...

[CONSTRAINTS]
- Locks: config_lock serializes master_config reads/writes; connected_websockets is mutated within the event loop.
- Writes: master_config writes are atomic (temp + fsync + os.replace) and create backups opportunistically.
- Security: Artifact fetch blocks path traversal (".." or "/" in filename); SPA serve only serves files under static/ and otherwise falls back to index.html.
- Orders: Run listing sorted descending; artifact list sorted by timestamp descending.
- Non-goal: This module does not execute model calls directly; it exposes API surfaces that delegate execution to SessionManager/Bridge layers.
- When-needed: Open when you need the concrete FastAPI routing surface that wires session, translator, inspector, graph, and meta services together for the server backend, or when `StaticFiles` mount wiring is the seam under inspection for `/static` frontend assets.
- Escalates-to: system/server/session.py::SessionManager; system/server/translator.py::Translator; system/server/meta_service.py::MetaService; system/server/schemas.py
- Navigation-group: server_backend
"""

import asyncio
import copy
import html
import inspect
import json
import os
import re
import sys
import threading
import subprocess
import logging
import signal
import time
import shutil  # Added for backup operations
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Set, List, Dict, Any, Optional, Mapping, Callable

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, Body, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from system.server.session import SessionManager
from system.server.graph import compile_physics_graph, compile_mission_view
from system.server.translator import Translator, TranslationError
from system.core.loader import PhysicalLoader
from system.core.bridge import bridge_diagnostics
from system.lib.kernel import preflight_cache as _preflight_cache
from system.lib.kernel.commands.comprehension_snapshot import build_vantage
from system.lib.standard_option_surface import build_option_surface
from system.lib.utils import resolve_value as _rv, deep_merge as _deep_merge, resolve_runs_dir as _resolve_runs_dir_canonical
from system.lib.feed_quality import collect_artifact_qualities, quality_grade_override
from system.lib.hashing import hash_node
from system.lib import library_catalog as library_catalog_loader
from system.lib import work_admission
from system.lib import frontend_surface_contracts
from system.lib.swr_cache import swr_get, swr_peek, swr_prewarm
from system.lib.observe_runtime import (
    grouped_runtime_status_payload,
    load_grouped_runtime_manifest,
    request_grouped_runtime_cancel,
    resolve_grouped_runtime_manifest_path,
)
from system.lib.agent_observability import (
    AgentObservabilitySampler,
    AgentTraceStore,
    discover_claude_code_app_sessions,
    ingest_recent_claude_transcripts,
    ingest_recent_codex_rollouts,
    snapshot_codex_app,
)
from system.lib.agent_observability_animation import (
    build_agent_observability_animation_delta,
    build_agent_observability_animation_scene,
)
from system.server.live_projection import LiveProjectionResponseCache
from system.lib.host_pressure import build_progress_pressure_packet_from_store
from system.lib.agent_mission_status import build_agent_mission_status
from system.lib.work_ledger_runtime import (
    RUNTIME_STATUS_REL as _WORK_LEDGER_RUNTIME_STATUS_REL,
    build_session_message_inbox_surface,
    load_runtime_status as _load_work_ledger_runtime_status,
)
from system.core.forensics import reconstruct_run_state
from system.server.inspector import InspectorService
from system.server.meta_service import MetaService
from system.server.schemas import (
    CodexTreeNodeSchema, CodexTreeStatsSchema, CodexTreeResponse, TreeSnapshotModeSchema,
    CodexFileDetailSchema, DoctrineDetailSchema,
    BatchReadRequest, BatchReadResponse,
    DocSaveRequest,
    PruneRequest, PruneResponse,
    MetaApplyRequest, MetaApplyResponse,
    MetaObserveRequest, MetaObserveResponse,
    MetaBuildRequest, MetaBuildResponse,
    MetaPatchRequest, MetaPatchResponse,
    PatchRecordListItem, PatchRecord,
    MetaToolMetadata, MetaEnvelope,
    LatestRunSchema, RunHologramStatusSchema, RunHologramBatchStatusRequest,
    RegradeResult, RegradeBatchRequest,
    ToolRunTelemetry, ToolMetadataSchema, ProvenanceView, ToolDiagnosticsSchema,
    ObserveSessionIgniteRequest, ObserveSessionIgniteResponse, ObserveSessionStatusResponse,
    ObserveSessionDraftRequest, ObserveSessionDraftResponse, ObserveSessionPreviewResponse,
    ObserveGroupPreview, ObserveSessionHistoryItem, ObserveSessionHistoryResponse
)
from system.server.observe_session import MetaSessionController
from system.server import world_model as world_model_loader
from system.server import zenith_runtime as zenith_runtime_loader
from system.lib import meta_mission_workspace as _mmw
from system.lib.launchable_operations import prepare_launch_operation as _prepare_launch_operation
from system.lib.query_driven_holographic_slice import build_query_driven_holographic_slice
from system.lib.raw_seed_alchemy import (
    family_raw_seed_alchemy_review_path as _family_raw_seed_alchemy_review_path,
    plan_raw_seed_alchemy,
    run_raw_seed_alchemy,
)
from system.lib.raw_seed_alchemy_apply import apply_alchemy_review
from system.lib.raw_seed_assimilation_view import (
    build_raw_seed_assimilation_bundle_detail,
    build_raw_seed_assimilation_cluster_detail,
    build_raw_seed_assimilation_graph_slice,
    build_raw_seed_assimilation_projection,
    build_raw_seed_paragraph_detail,
    build_raw_seed_shard_detail,
    compute_bundle_hash,
    load_raw_seed_families,
    search_raw_seed_shards,
)
from system.lib.raw_seed_coverage_enrich import write_enriched_coverage
from system.lib.system_surface_registry import (
    load_system_surface_registry,
    resolve_system_surface_registry_node,
    search_system_surface_registry,
    write_system_surface_registry,
)
from system.lib.config_authority_registry import (
    config_authority_diagnostics,
    load_config_authority_registry,
    resolve_config_authority_effective,
    resolve_config_authority_node,
    search_config_authority_registry,
    write_config_authority_registry,
)
from system.lib.market_dashboard_read_model import (
    filter_situation_queue as _filter_market_dashboard_situation_queue,
    load_latest_market_dashboard_read_model as _load_latest_market_dashboard_read_model,
    load_market_dashboard_read_model as _load_market_dashboard_read_model,
    resolve_drilldown as _resolve_market_dashboard_drilldown,
    resolve_graph_slice as _resolve_market_dashboard_graph_slice,
    resolve_provenance as _resolve_market_dashboard_provenance,
    resolve_situation_detail as _resolve_market_dashboard_situation_detail,
    resolve_validation_debt as _resolve_market_dashboard_validation_debt,
)
from system.lib.market_display_bundle import (
    build_market_display_bundle as _build_market_display_bundle,
    load_latest_ready_market_display_bundle as _load_latest_ready_market_display_bundle,
)
from system.lib.feed_artifact_tables import (
    PLANE_SPECS as _MARKET_PLANE_SPECS,
    extract_feed_table as _extract_feed_table,
    filter_plane_rows as _filter_plane_rows,
)
from system.lib.human_market_cockpit import (
    build_market_workspace as _build_market_workspace,
)
from system.lib.mission_transaction_landing_preflight import build_mission_transaction_landing_preflight
from system.server.schemas import (
    UIConfig,
    LobbyState, CandidateRun,
    DataRootSummary,
    PaperModulesSnapshotResponse,
    ImaginationsSnapshotResponse,
    ImaginationDetailResponse,
    MarketDashboardDrilldownResponse,
    MarketDashboardGraphSliceResponse,
    MarketDashboardOverviewResponse,
    MarketDashboardProvenanceResponse,
    MarketDashboardReadModelResponse,
    MarketDashboardSituationDetailResponse,
    MarketDashboardSituationQueueResponse,
    MarketDashboardValidationDebtResponse,
    MarketBrowsePlaneResponse,
    MarketDisplayBundleLatestReadyResponse,
    MarketDisplayBundleResponse,
    BridgeDiagnosticsResponse,
    BridgePreflightResponse,
    HostAgentExternalSnapshot,
    LaunchOperationPreviewResponse,
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalListResponse,
    FrontendHealthReportResponse,
    FrontendSurfaceAgentPacketResponse,
    FrontendSurfaceListResponse,
    RawSeedAppendArtifacts,
    RawSeedAppendRequest,
    RawSeedAppendResponse,
    ShardLensDetailResponse,
    ShardLensOverviewResponse,
    ShardLensQueryResponse,
    StationLauncherSnapshot,
    SystemLensProjectionResponse,
    OperationsLensSnapshotResponse,
    LeanMathematicsMicrocosmSnapshotResponse,
    MetaDiagnosticsConsoleProjectionResponse,
    MissionTransactionPreflightResponse,
    WorkLedgerOverviewResponse,
    WorkLedgerQueryResponse,
    WorkLedgerThreadResponse,
    MetaMissionsIndexResponse,
    MetaMissionDetailResponse,
    MetaMissionRunsResponse,
    MetaMissionRunDetailResponse,
    MetaMissionRegistryEntry,
    MetaMissionSummaryRow,
    MetaMissionRunSummary,
    MetaMissionCareerMetrics,
    StationMetaMissionsSlice,
    IgnitePayload,
    IgnitionResponse,
    TemporalContract,
    StopRunResponse,
    RunSummary,
    GraphView,
    ControlRoomOperationalContextResponse,
    ControlRoomGraphContext,
    ControlRoomRunContext,
    ControlRoomBridgeContext,
    RunRequest,
    ResumeFeedPreflightPayload,
    ResumeFeedPreflightResponse,
    ResumeFeedStaleNode,
    ZenithBootstrapResponse,
    ZenithHealthResponse,
    ZenithRuntimeSnapshot,
    QueryDrivenHolographicSliceRequest,
    QueryDrivenHolographicSliceResponse,
    RawSeedAssimilationBundleDetailResponse,
    RawSeedAssimilationBundleCard,
    RawSeedAssimilationClusterCard,
    RawSeedAssimilationClusterDetailResponse,
    RawSeedAssimilationCommitRequest,
    RawSeedAssimilationGraph,
    RawSeedAssimilationOperationReceipt,
    RawSeedAssimilationParagraphDetailResponse,
    RawSeedAssimilationProjectionResponse,
    RawSeedAssimilationShardDetailResponse,
    RawSeedFamiliesResponse,
    RawSeedImplementationGap,
    RawSeedShardSearchRequest,
    RawSeedShardSearchResponse,
    SystemSurfaceRegistryNodeDetailResponse,
    SystemSurfaceRegistryRebuildResponse,
    SystemSurfaceRegistrySearchResponse,
    SystemSurfaceRegistrySummaryResponse,
    ConfigSurfaceDiagnosticsResponse,
    ConfigSurfaceEffectiveResponse,
    ConfigSurfaceNodeDetailResponse,
    ConfigSurfaceRebuildResponse,
    ConfigSurfaceSearchResponse,
    ConfigSurfaceSummaryResponse,
    RuntimeContinuityResponse,
)

# =============================================================================
# Repo Root + Logging
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_DIR = REPO_ROOT / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = STATE_DIR / "server_debug.log"
SESSION_YIELD_REQUESTS_PATH = STATE_DIR / "performance" / "session_yield_requests.jsonl"
SESSION_YIELD_RESULTS_PATH = STATE_DIR / "performance" / "session_yield_results.jsonl"
SESSION_MESSAGES_PATH = STATE_DIR / "work_ledger" / "session_messages.jsonl"
BACKGROUND_DOWNSHIFT_STATE_PATH = STATE_DIR / "performance" / "background_loop_downshift.json"

_FILE_HANDLER = logging.FileHandler(str(LOG_PATH), encoding="utf-8")
_STREAM_HANDLER = logging.StreamHandler(sys.stdout)
_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT, handlers=[_FILE_HANDLER, _STREAM_HANDLER], force=True)
logger = logging.getLogger("server")

_STATION_LAUNCHER_CACHE_TTL_S = 10.0
_STATION_LAUNCHER_CACHE: dict[str, tuple[float, Dict[str, Any]]] = {}
_STATION_LAUNCHER_CACHE_LOCK = threading.Lock()
_STATION_LAUNCHER_REFRESH_IN_FLIGHT: dict[str, threading.Event] = {}
_STATION_LAUNCHER_BACKGROUND_START_DELAY_S = 0.02
_STATION_LAUNCHER_AUX_CACHE_TTL_S = 30.0
_STATION_LAUNCHER_OPERATIONS_PREWARM_WAIT_S = 0.25
_STATION_LAUNCHER_OPERATIONS_CACHE: dict[str, tuple[float, Dict[str, Any]]] = {}
_STATION_LAUNCHER_OPERATIONS_CACHE_LOCK = threading.Lock()
_STATION_LAUNCHER_OPERATIONS_REFRESH_IN_FLIGHT: dict[str, threading.Event] = {}
_ROOT_NAVIGATOR_HANDOFF_CACHE: dict[str, tuple[float, Dict[str, Any]]] = {}
_ROOT_NAVIGATOR_HANDOFF_CACHE_LOCK = threading.Lock()
_ROOT_NAVIGATOR_HANDOFF_REFRESH_IN_FLIGHT: dict[str, threading.Event] = {}
_ROOT_NAVIGATOR_HANDOFF_CACHE_TTL_S = 600.0
_ROOT_NAVIGATOR_HANDOFF_PREWARM_WAIT_S = 0.25
_ROOT_NAVIGATOR_HANDOFF_BACKGROUND_START_DELAY_S = 0.02
_WORLD_MODEL_SNAPSHOT_CACHE_NAME = "world_model_snapshot"
_WORLD_MODEL_SNAPSHOT_PREWARM_WAIT_S = 0.25
_ATTENTION_SNAPSHOT_CACHE_TTL_S = 10.0
_ATTENTION_SNAPSHOT_PREWARM_WAIT_S = 0.25
_ATTENTION_SNAPSHOT_CACHE: dict[str, tuple[float, Dict[str, Any]]] = {}
_ATTENTION_SNAPSHOT_CACHE_LOCK = threading.Lock()
_ATTENTION_SNAPSHOT_REFRESH_IN_FLIGHT: dict[str, threading.Event] = {}
_BLAST_RADIUS_CACHE_TTL_S = 60.0
_BLAST_RADIUS_BACKGROUND_START_DELAY_S = 0.02
_BLAST_RADIUS_CACHE: dict[tuple[str, int], tuple[float, Dict[str, Any]]] = {}
_BLAST_RADIUS_CACHE_LOCK = threading.Lock()
_BLAST_RADIUS_REFRESH_IN_FLIGHT: dict[tuple[str, int], threading.Event] = {}
_MISSION_TRANSACTION_DEFAULT_SUBJECT_ID = "cap_parallel_mission_transactions_git_safe_wave_landing"
_MISSION_TRANSACTION_DEFAULT_OWNED_PATHS = (
    "system/lib/mission_transaction_landing_preflight.py",
    "tools/meta/control/mission_transaction_preflight.py",
    "system/server/tests/test_mission_transaction_landing_preflight.py",
    "system/lib/generated_projection_registry.py",
    "system/lib/work_ledger.py",
    "tools/meta/factory/work_ledger.py",
    "system/server/tests/test_work_ledger_core.py",
)

def _ensure_uvicorn_logs_to_file() -> None:
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        lg = logging.getLogger(name)
        if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == str(LOG_PATH) for h in lg.handlers):
            lg.addHandler(_FILE_HANDLER)
        lg.setLevel(logging.INFO)
        lg.propagate = False


def _station_cache_key() -> str:
    return str(REPO_ROOT.resolve())


def _peek_station_cache(
    cache: dict[str, tuple[float, Dict[str, Any]]],
    lock: threading.Lock,
    *,
    ttl_s: float,
) -> Optional[Dict[str, Any]]:
    cache_key = _station_cache_key()
    now = time.monotonic()
    with lock:
        cached = cache.get(cache_key)
        if not cached or now - cached[0] > ttl_s:
            return None
        return copy.deepcopy(cached[1])


def _store_station_cache(
    cache: dict[str, tuple[float, Dict[str, Any]]],
    lock: threading.Lock,
    payload: Dict[str, Any],
) -> None:
    with lock:
        cache[_station_cache_key()] = (time.monotonic(), copy.deepcopy(payload))


def _root_navigator_handoff_cache_key() -> str:
    return str(REPO_ROOT.resolve())


def _world_model_snapshot_cache_key() -> object:
    return (str(REPO_ROOT.resolve()), "first_paint")


def _hot_surface_prewarm_specs() -> list[tuple[str, object, Callable[[], Any]]]:
    repo_key = str(REPO_ROOT.resolve())
    return [
        # Order matters: world_model_snapshot + paper_modules first because
        # they're the heaviest and unblock the launcher/bootstrap surfaces.
        (
            "paper_modules_snapshot",
            repo_key,
            lambda: world_model_loader._uncached_load_paper_modules_snapshot(REPO_ROOT),
        ),
        (
            "world_model_snapshot",
            _world_model_snapshot_cache_key(),
            _world_model_snapshot_uncached_payload,
        ),
        (
            "work_ledger_overview",
            world_model_loader.work_ledger_overview_cache_key(REPO_ROOT),
            lambda: world_model_loader._uncached_load_work_ledger_overview(REPO_ROOT),
        ),
        ("shard_overview", (repo_key, "family"), lambda: world_model_loader.load_shard_overview(REPO_ROOT, source="family")),
        ("annex_catalog", repo_key, lambda: library_catalog_loader.build_annex_catalog(REPO_ROOT)),
        ("codex_tree", repo_key, _build_codex_tree_payload),
        ("meta_missions_index", repo_key, _build_meta_missions_index),
        ("wake_barriers", repo_key, lambda: world_model_loader.load_wake_barriers(REPO_ROOT)),
        ("library_tools", repo_key, lambda: library_catalog_loader.list_tools(repo_root=REPO_ROOT)),
        # The three new swr-wrapped snapshot leaves landed alongside the
        # Patch A/B/C snapshot cold-path pass. Adding them to the serial
        # prewarm chain populates their caches at startup so the first
        # /api/world-model/snapshot HTTP request doesn't pay the cold
        # walls inside _uncached_load_world_model_snapshot for autonomy
        # diagnostics, lab/oracle/evolve runs, or market feeds runs.
        ("autonomy_diagnostics", repo_key, lambda: world_model_loader.load_autonomy_diagnostics(REPO_ROOT)),
        ("market_feeds_snapshot", (repo_key, 24), lambda: world_model_loader.load_market_feeds_snapshot(REPO_ROOT)),
        ("lab_oracle_evolve_snapshot", (repo_key, 24), lambda: world_model_loader.load_lab_oracle_evolve_snapshot(REPO_ROOT)),
        # `reactions` and `attention` use world_model._cached_mapping, not
        # swr_get directly, so we prewarm by calling the loader instead.
    ]


def _attention_snapshot_cache_key() -> str:
    return str(REPO_ROOT.resolve())


def _warming_root_navigator_scene_domain_explainers(
    axes: list[Mapping[str, Any]],
) -> Dict[str, Any]:
    rows: list[Dict[str, Any]] = []
    for axis in axes:
        axis_id = str(axis.get("axis_id") or "unknown")
        kind_ids = [str(kind) for kind in axis.get("candidate_kinds") or [] if str(kind)]
        if not kind_ids:
            continue
        title = str(axis.get("label") or axis_id.replace("_", " ").title())
        role = str(axis.get("projection_role") or "Full scene-domain explanation is warming.")
        rows.append(
            {
                "scene_role_id": f"warming:{axis_id}",
                "title": title,
                "primary_kind": kind_ids[0],
                "domain_kind_ids": kind_ids,
                "headline": "Full Root Navigator scene-domain explanation is warming.",
                "contains": [role],
                "relation_summary": "Static warming row from the constitutional atlas; source-backed relation and domain evidence is still prewarming.",
                "paper_module_refs": [],
                "kind_rows": [
                    {
                        "kind_id": kind_id,
                        "title": kind_id.replace("_", " ").title(),
                        "support_status": "warming",
                        "row_count": None,
                    }
                    for kind_id in kind_ids
                ],
            }
        )
    return {
        "schema": "root_navigator_scene_domain_explainers_v0",
        "authority_posture": "warming_shell_not_source_authority",
        "status": "warming",
        "rows": rows,
    }


def _warming_root_navigator_handoff_payload() -> Dict[str, Any]:
    atlas_rel = frontend_surface_contracts.ROOT_NAVIGATOR_CONSTITUTIONAL_ATLAS_PATH
    atlas_path = REPO_ROOT / atlas_rel
    atlas_payload: Mapping[str, Any] = {}
    try:
        raw = json.loads(atlas_path.read_text(encoding="utf-8"))
        if isinstance(raw, Mapping):
            atlas_payload = raw
    except Exception:
        atlas_payload = {}
    atlas = atlas_payload.get("constitutional_atlas")
    axes = []
    if isinstance(atlas, Mapping) and isinstance(atlas.get("primitive_axes"), list):
        axes = [row for row in atlas.get("primitive_axes", []) if isinstance(row, Mapping)]

    rows: list[Dict[str, Any]] = []
    for axis in axes:
        axis_id = str(axis.get("axis_id") or "unknown")
        role = str(axis.get("projection_role") or "Full source-backed role is warming.")
        for kind in axis.get("candidate_kinds") or []:
            kind_id = str(kind)
            rows.append(
                {
                    "candidate_primitive": kind_id,
                    "title": kind_id.replace("_", " ").title(),
                    "status": "warming",
                    "axis": axis_id,
                    "role_in_root_navigator": role,
                    "projection_rule": "Full source-backed Root Navigator handoff is still warming.",
                    "support_status": "warming",
                }
            )

    try:
        root_coverage = frontend_surface_contracts.build_root_coverage_state_summary(REPO_ROOT)
    except Exception as exc:
        root_coverage = {
            "status": "warming_unavailable",
            "source_ref": "state/system_atlas/root_coverage_state.json",
            "load_warning": str(exc),
        }
    scene_domain_explainers = _warming_root_navigator_scene_domain_explainers(axes)

    return {
        "schema": "root_navigator_claude_frontend_handoff_packet_v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "warming",
        "verdict": {
            "state": "warming",
            "reason": "Full Root Navigator handoff is prewarming; serving static primitive axes so the atlas does not render hollow.",
        },
        "authority_posture": "warming_shell_not_source_authority",
        "view": {
            "view_id": frontend_surface_contracts.ROOT_NAVIGATOR_VIEW_ID,
            "route": "/station/root-navigator",
            "purpose": "Root Navigator is warming its full source-backed handoff packet.",
        },
        "current_screenshot": {"status": "warming"},
        "constitutional_atlas": {
            "status": "warming",
            "direction_id": atlas_payload.get("direction_id"),
            "authority_posture": atlas_payload.get("authority_posture"),
            "purpose_one_line": atlas_payload.get("purpose_one_line"),
            "inspector_tabs": (atlas or {}).get("inspector_tabs") if isinstance(atlas, Mapping) else [],
            "relation_authority_sources": (atlas or {}).get("relation_authority_sources") if isinstance(atlas, Mapping) else [],
            "container_receipt_fields": (atlas or {}).get("container_receipt_fields") if isinstance(atlas, Mapping) else [],
            "primitive_axes": [dict(row) for row in axes],
        },
        "frontend_surface_agent_packet": {
            "command": "./repo-python kernel.py --view-agent-packet rootNavigator",
            "operator_cli_hints": {
                "jump_ai": "./repo-python kernel.py --view rootNavigator",
                "capture": "./repo-python kernel.py --view-capture rootNavigator",
            },
        },
        "semantic_primitive_matrix": {
            "schema": "root_navigator_semantic_primitive_matrix_v0",
            "status": "warming",
            "matrix_rule": "Static warming shell; full source-backed matrix is still prewarming.",
            "missing_kind_ids": [],
            "rows": rows,
        },
        "scene_domain_explainers": scene_domain_explainers,
        "root_coverage_state": root_coverage,
        "relation_manifest": {
            "schema": "root_navigator_relation_manifest_v0",
            "status": "warming",
            "edges": [],
        },
        "container_receipts": {
            "schema": "root_navigator_container_receipts_v0",
            "status": "warming",
            "receipts": [],
        },
        "freshness_receipts": {
            "schema": "root_navigator_freshness_receipts_v0",
            "status": "warming",
            "receipts": {},
        },
        "known_ui_defects": [],
        "backend_caveats": ["Full source-backed handoff is still prewarming."],
        "acceptance_checks": [],
        "source_refs": [
            str(atlas_rel),
            "system/server/main.py::_warming_root_navigator_handoff_payload",
        ],
    }

# =============================================================================
# Global State
# =============================================================================

session_manager = SessionManager(REPO_ROOT)
translator = Translator(REPO_ROOT)
inspector_service = InspectorService(REPO_ROOT)
meta_service = MetaService(REPO_ROOT)
meta_session_controller = MetaSessionController(REPO_ROOT)
agent_trace_store = AgentTraceStore(REPO_ROOT)
agent_observability_sampler = AgentObservabilitySampler(agent_trace_store, REPO_ROOT)
connected_websockets: Set[WebSocket] = set()
meta_session_websockets: Set[WebSocket] = set()
agent_observability_websockets: Set[WebSocket] = set()
config_lock = threading.Lock()
_AGENT_OBSERVABILITY_WORK_LEDGER_CACHE_TTL_S = 5.0
_AGENT_OBSERVABILITY_ANIMATION_DEFAULT_LIMIT = 200
_AGENT_OBSERVABILITY_WORK_LEDGER_CACHE_LOCK = threading.Lock()
_AGENT_OBSERVABILITY_WORK_LEDGER_CACHE: Dict[str, Any] = {
    "signature": None,
    "loaded_at": 0.0,
    "payload": None,
}
_AGENT_OBSERVABILITY_HOST_PRESSURE_CACHE_TTL_S = 1.0
_AGENT_OBSERVABILITY_HOST_PRESSURE_CACHE_LOCK = threading.Lock()
_AGENT_OBSERVABILITY_HOST_PRESSURE_CACHE: Dict[str, Any] = {
    "signature": None,
    "loaded_at": 0.0,
    "payload": None,
}
_AGENT_OBSERVABILITY_EVENTS_CACHE_TTL_S = 1.0
_AGENT_OBSERVABILITY_EVENTS_PROJECTION_CACHE = LiveProjectionResponseCache(
    "agent_observability.events",
    ttl_s=_AGENT_OBSERVABILITY_EVENTS_CACHE_TTL_S,
    max_entries=64,
)
_AGENT_OBSERVABILITY_MISSION_STATUS_CACHE_TTL_S = 1.0
_AGENT_OBSERVABILITY_MISSION_STATUS_PROJECTION_CACHE = LiveProjectionResponseCache(
    "agent_observability.mission_status",
    ttl_s=_AGENT_OBSERVABILITY_MISSION_STATUS_CACHE_TTL_S,
    max_entries=64,
)
_AGENT_OBSERVABILITY_ANIMATION_DELTA_CACHE_TTL_S = 0.5
_AGENT_OBSERVABILITY_ANIMATION_DELTA_PROJECTION_CACHE = LiveProjectionResponseCache(
    "agent_observability.animation_delta",
    ttl_s=_AGENT_OBSERVABILITY_ANIMATION_DELTA_CACHE_TTL_S,
    max_entries=64,
)


def _agent_observability_work_ledger_signature(
    repo_root: Path,
) -> tuple[str, Optional[int], Optional[int], int]:
    path = repo_root / _WORK_LEDGER_RUNTIME_STATUS_REL
    try:
        stat = path.stat()
    except OSError:
        return (str(path), None, None, id(_load_work_ledger_runtime_status))
    return (
        str(path),
        stat.st_mtime_ns,
        stat.st_size,
        id(_load_work_ledger_runtime_status),
    )


def _load_agent_observability_work_ledger_status(repo_root: Path) -> Dict[str, Any]:
    signature = _agent_observability_work_ledger_signature(repo_root)
    now = time.monotonic()
    with _AGENT_OBSERVABILITY_WORK_LEDGER_CACHE_LOCK:
        cached = _AGENT_OBSERVABILITY_WORK_LEDGER_CACHE.get("payload")
        if (
            isinstance(cached, dict)
            and _AGENT_OBSERVABILITY_WORK_LEDGER_CACHE.get("signature") == signature
            and now - float(_AGENT_OBSERVABILITY_WORK_LEDGER_CACHE.get("loaded_at") or 0.0)
            <= _AGENT_OBSERVABILITY_WORK_LEDGER_CACHE_TTL_S
        ):
            return cached
        payload = _load_work_ledger_runtime_status(repo_root)
        if not isinstance(payload, dict):
            payload = {}
        _AGENT_OBSERVABILITY_WORK_LEDGER_CACHE.update({
            "signature": signature,
            "loaded_at": now,
            "payload": payload,
        })
        return payload


def _clear_agent_observability_work_ledger_cache_for_tests() -> None:
    with _AGENT_OBSERVABILITY_WORK_LEDGER_CACHE_LOCK:
        _AGENT_OBSERVABILITY_WORK_LEDGER_CACHE.update({
            "signature": None,
            "loaded_at": 0.0,
            "payload": None,
        })


def _agent_observability_host_pressure_signature(
    status: Mapping[str, Any],
    *,
    window_s: int,
    requested_workload_class: Optional[str],
    operator_override: bool,
    request_path: str,
) -> tuple[Any, ...]:
    return (
        request_path,
        int(window_s),
        requested_workload_class or "",
        bool(operator_override),
        status.get("seq"),
        status.get("history_size"),
        status.get("dropped_count"),
        status.get("gap_count"),
        id(build_progress_pressure_packet_from_store),
    )


def _load_agent_observability_host_pressure_packet(
    *,
    request_path: str,
    window_s: int,
    requested_workload_class: Optional[str],
    operator_override: bool,
) -> Dict[str, Any]:
    status = agent_trace_store.status()
    signature = _agent_observability_host_pressure_signature(
        status,
        window_s=window_s,
        requested_workload_class=requested_workload_class,
        operator_override=operator_override,
        request_path=request_path,
    )
    now = time.monotonic()
    with _AGENT_OBSERVABILITY_HOST_PRESSURE_CACHE_LOCK:
        cached = _AGENT_OBSERVABILITY_HOST_PRESSURE_CACHE.get("payload")
        if (
            isinstance(cached, dict)
            and _AGENT_OBSERVABILITY_HOST_PRESSURE_CACHE.get("signature") == signature
            and now - float(_AGENT_OBSERVABILITY_HOST_PRESSURE_CACHE.get("loaded_at") or 0.0)
            <= _AGENT_OBSERVABILITY_HOST_PRESSURE_CACHE_TTL_S
        ):
            return cached
        payload = build_progress_pressure_packet_from_store(
            agent_trace_store,
            REPO_ROOT,
            window_s=window_s,
            requested_workload_class=requested_workload_class,
            operator_override=operator_override,
            activation_endpoint_probe={
                "status": "route_available",
                "url": request_path,
                "http_status": 200,
                "schema_detected": True,
                "probe_source": "serving_endpoint",
            },
        )
        if not isinstance(payload, dict):
            payload = {}
        _AGENT_OBSERVABILITY_HOST_PRESSURE_CACHE.update({
            "signature": signature,
            "loaded_at": now,
            "payload": payload,
        })
        return payload


def _clear_agent_observability_host_pressure_cache_for_tests() -> None:
    with _AGENT_OBSERVABILITY_HOST_PRESSURE_CACHE_LOCK:
        _AGENT_OBSERVABILITY_HOST_PRESSURE_CACHE.update({
            "signature": None,
            "loaded_at": 0.0,
            "payload": None,
        })


def _agent_observability_events_signature(
    status: Mapping[str, Any],
    *,
    since_seq: int,
    session_id: Optional[str],
    source_runtime: Optional[str],
    canonical_type: Optional[str],
    limit: int,
) -> tuple[Any, ...]:
    return (
        int(since_seq),
        session_id or "",
        source_runtime or "",
        canonical_type or "",
        int(limit),
        status.get("seq"),
        status.get("history_size"),
        status.get("dropped_count"),
        status.get("gap_count"),
        id(agent_trace_store),
    )


def _agent_observability_events_response(
    *,
    since_seq: int,
    session_id: Optional[str],
    source_runtime: Optional[str],
    canonical_type: Optional[str],
    limit: int,
    request_headers: Optional[Mapping[str, str]] = None,
) -> Response:
    status = agent_trace_store.status()
    signature = _agent_observability_events_signature(
        status,
        since_seq=since_seq,
        session_id=session_id,
        source_runtime=source_runtime,
        canonical_type=canonical_type,
        limit=limit,
    )

    def _build_payload() -> Mapping[str, Any]:
        return {
            "events": agent_trace_store.replay(
                since_seq=since_seq,
                session_id=session_id,
                source_runtime=source_runtime,
                canonical_type=canonical_type,
                limit=limit,
            ),
            "status": status,
        }

    return _AGENT_OBSERVABILITY_EVENTS_PROJECTION_CACHE.response(
        signature=signature,
        build_payload=_build_payload,
        request_headers=request_headers,
        json_bytes=_agent_trace_json_response_bytes,
        source_seq=status.get("seq"),
        extra_headers={
            "X-Agent-Trace-Seq": str(status.get("seq") or ""),
            "X-Agent-Trace-History-Size": str(status.get("history_size") or ""),
        },
    )


def _clear_agent_observability_events_cache_for_tests() -> None:
    _AGENT_OBSERVABILITY_EVENTS_PROJECTION_CACHE.clear()


def _agent_observability_mission_status_signature(
    trace_status: Mapping[str, Any],
    *,
    history_limit: int,
    work_ledger_signature: tuple[str, Optional[int], Optional[int], int],
) -> tuple[Any, ...]:
    return (
        int(history_limit),
        trace_status.get("seq"),
        trace_status.get("history_size"),
        trace_status.get("dropped_count"),
        trace_status.get("gap_count"),
        work_ledger_signature,
        id(agent_trace_store),
        id(build_agent_mission_status),
    )


def _agent_observability_mission_status_response(
    *,
    history_limit: int,
    request_headers: Optional[Mapping[str, str]] = None,
) -> Response:
    trace_status = agent_trace_store.status()
    work_ledger_signature = _agent_observability_work_ledger_signature(REPO_ROOT)
    signature = _agent_observability_mission_status_signature(
        trace_status,
        history_limit=history_limit,
        work_ledger_signature=work_ledger_signature,
    )

    def _build_payload() -> Mapping[str, Any]:
        try:
            work_ledger_status = _load_agent_observability_work_ledger_status(REPO_ROOT)
        except Exception:  # noqa: BLE001 - reducer must degrade, not fail
            logger.exception("mission-status work-ledger load failed")
            work_ledger_status = {}
        return build_agent_mission_status(
            store=agent_trace_store,
            work_ledger_status=work_ledger_status,
            repo_root=REPO_ROOT,
            history_limit=history_limit,
        )

    return _AGENT_OBSERVABILITY_MISSION_STATUS_PROJECTION_CACHE.response(
        signature=signature,
        build_payload=_build_payload,
        request_headers=request_headers,
        json_bytes=_agent_trace_json_response_bytes,
        source_seq=trace_status.get("seq"),
        extra_headers={
            "X-Agent-Trace-Seq": str(trace_status.get("seq") or ""),
            "X-Agent-Trace-History-Size": str(trace_status.get("history_size") or ""),
        },
    )


def _clear_agent_observability_mission_status_cache_for_tests() -> None:
    _AGENT_OBSERVABILITY_MISSION_STATUS_PROJECTION_CACHE.clear()


def _agent_observability_animation_delta_signature(
    trace_status: Mapping[str, Any],
    *,
    since_seq: int,
    session_id: Optional[str],
    source_runtime: Optional[str],
    limit: int,
    window_ms: int,
    include_infrastructure: bool,
    max_ops: int,
    work_ledger_signature: tuple[str, Optional[int], Optional[int], int],
) -> tuple[Any, ...]:
    return (
        int(since_seq),
        session_id or "",
        source_runtime or "",
        int(limit),
        int(window_ms),
        bool(include_infrastructure),
        int(max_ops),
        trace_status.get("seq"),
        trace_status.get("history_size"),
        trace_status.get("dropped_count"),
        trace_status.get("gap_count"),
        work_ledger_signature,
        id(agent_trace_store),
        id(build_agent_mission_status),
        id(build_agent_observability_animation_delta),
    )


def _agent_observability_animation_delta_response(
    *,
    since_seq: int,
    session_id: Optional[str],
    source_runtime: Optional[str],
    limit: int,
    window_ms: int,
    include_infrastructure: bool,
    max_ops: int,
    request_headers: Optional[Mapping[str, str]] = None,
) -> Response:
    trace_status = agent_trace_store.status()
    work_ledger_signature = _agent_observability_work_ledger_signature(REPO_ROOT)
    signature = _agent_observability_animation_delta_signature(
        trace_status,
        since_seq=since_seq,
        session_id=session_id,
        source_runtime=source_runtime,
        limit=limit,
        window_ms=window_ms,
        include_infrastructure=include_infrastructure,
        max_ops=max_ops,
        work_ledger_signature=work_ledger_signature,
    )

    def _build_payload() -> Mapping[str, Any]:
        try:
            work_ledger_status = _load_agent_observability_work_ledger_status(REPO_ROOT)
        except Exception:  # noqa: BLE001 - animation projection must degrade
            logger.exception("animation delta work-ledger load failed")
            work_ledger_status = {}
        mission_status = build_agent_mission_status(
            store=agent_trace_store,
            work_ledger_status=work_ledger_status,
            repo_root=REPO_ROOT,
            history_limit=limit,
        )
        return build_agent_observability_animation_delta(
            events=agent_trace_store.replay(
                since_seq=since_seq,
                session_id=session_id,
                source_runtime=source_runtime,
                limit=limit,
            ),
            status=trace_status,
            mission_status=mission_status,
            window_ms=window_ms,
            include_infrastructure=include_infrastructure,
            session_id=session_id,
            source_runtime=source_runtime,
            since_seq=since_seq,
            limit=limit,
            max_ops=max_ops,
        )

    return _AGENT_OBSERVABILITY_ANIMATION_DELTA_PROJECTION_CACHE.response(
        signature=signature,
        build_payload=_build_payload,
        request_headers=request_headers,
        json_bytes=_agent_trace_json_response_bytes,
        source_seq=trace_status.get("seq"),
        extra_headers={
            "X-Agent-Trace-Seq": str(trace_status.get("seq") or ""),
            "X-Agent-Trace-History-Size": str(trace_status.get("history_size") or ""),
        },
    )


def _clear_agent_observability_animation_delta_cache_for_tests() -> None:
    _AGENT_OBSERVABILITY_ANIMATION_DELTA_PROJECTION_CACHE.clear()


_AGENT_TRACE_MISSION_INDEX_CACHE_TTL_S = 5.0
_AGENT_TRACE_MISSION_INDEX_CACHE_LOCK = threading.Lock()
_AGENT_TRACE_MISSION_INDEX_CACHE: Dict[str, Any] = {
    "signature": None,
    "loaded_at": 0.0,
    "payload": None,
    "content": None,
}


def _agent_trace_structurer_support_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "Agent Trace Structurer"


def _agent_trace_file_signature(path: Path) -> tuple[str, Optional[int], Optional[int]]:
    try:
        stat = path.stat()
    except OSError:
        return (str(path), None, None)
    return (str(path), stat.st_mtime_ns, stat.st_size)


def _agent_trace_missing_mission_index_payload(mission_path: Path) -> Dict[str, Any]:
    return {
        "available": False,
        "reason": "mission_index_not_present",
        "source_path": str(mission_path),
        "hint": (
            "Run the macOS Agent Trace Structurer app (or "
            "`./repo-python tools/meta/observability/cli_prompt_trace.py "
            f"--mission-index -o {mission_path}`) to materialize it."
        ),
    }


def _build_agent_trace_mission_index_payload(
    mission_path: Path,
    variant_path: Path,
) -> Dict[str, Any]:
    try:
        index_blob = json.loads(mission_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.exception("Failed to read mission_index.json")
        raise HTTPException(status_code=500, detail=f"mission_index.json unreadable: {exc}")
    variant_artifact_index: Dict[str, Any] = {}
    if variant_path.exists():
        try:
            variant_blob = json.loads(variant_path.read_text(encoding="utf-8"))
            sessions = variant_blob.get("sessions")
            if isinstance(sessions, dict):
                variant_artifact_index = sessions
        except Exception:
            logger.exception("Failed to read variant_artifact_index.json")
            variant_artifact_index = {}
    return {
        "available": True,
        "source_path": str(mission_path),
        "schema": index_blob.get("schema"),
        "generated_at": index_blob.get("generated_at"),
        "cwd": index_blob.get("cwd"),
        "ambiguity_window_seconds": index_blob.get("ambiguity_window_seconds"),
        "sort_mode": index_blob.get("sort_mode"),
        "row_count": index_blob.get("row_count"),
        "active_count": index_blob.get("active_count"),
        "inactive_count": index_blob.get("inactive_count"),
        "hidden_old_count": index_blob.get("hidden_old_count"),
        "rows": index_blob.get("rows", []),
        "active_rows": index_blob.get("active_rows", []),
        "inactive_rows": index_blob.get("inactive_rows", []),
        "variant_artifact_index": variant_artifact_index,
    }


def _agent_trace_json_response_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _load_agent_trace_mission_index_cache_entry() -> Dict[str, Any]:
    support_dir = _agent_trace_structurer_support_dir()
    mission_path = support_dir / "mission_index.json"
    variant_path = support_dir / "variant_artifact_index.json"
    if not mission_path.exists():
        return {
            "payload": _agent_trace_missing_mission_index_payload(mission_path),
            "content": None,
        }

    signature = (
        _agent_trace_file_signature(mission_path),
        _agent_trace_file_signature(variant_path),
    )
    now = time.monotonic()
    with _AGENT_TRACE_MISSION_INDEX_CACHE_LOCK:
        cached = _AGENT_TRACE_MISSION_INDEX_CACHE.get("payload")
        cached_content = _AGENT_TRACE_MISSION_INDEX_CACHE.get("content")
        if (
            isinstance(cached, dict)
            and isinstance(cached_content, bytes)
            and _AGENT_TRACE_MISSION_INDEX_CACHE.get("signature") == signature
            and now - float(_AGENT_TRACE_MISSION_INDEX_CACHE.get("loaded_at") or 0.0)
            <= _AGENT_TRACE_MISSION_INDEX_CACHE_TTL_S
        ):
            return {"payload": cached, "content": cached_content}
        payload = _build_agent_trace_mission_index_payload(mission_path, variant_path)
        content = _agent_trace_json_response_bytes(payload)
        _AGENT_TRACE_MISSION_INDEX_CACHE.update({
            "signature": signature,
            "loaded_at": now,
            "payload": payload,
            "content": content,
        })
        return {"payload": payload, "content": content}


def _load_agent_trace_mission_index_bundle() -> Dict[str, Any]:
    entry = _load_agent_trace_mission_index_cache_entry()
    payload = entry.get("payload")
    if isinstance(payload, dict):
        return payload
    return {}


def _agent_trace_mission_index_response() -> Response:
    entry = _load_agent_trace_mission_index_cache_entry()
    content = entry.get("content")
    if isinstance(content, bytes):
        return Response(content=content, media_type="application/json")
    payload = entry.get("payload")
    if isinstance(payload, Mapping):
        return JSONResponse(payload)
    return JSONResponse({})


def _clear_agent_trace_mission_index_cache_for_tests() -> None:
    with _AGENT_TRACE_MISSION_INDEX_CACHE_LOCK:
        _AGENT_TRACE_MISSION_INDEX_CACHE.update({
            "signature": None,
            "loaded_at": 0.0,
            "payload": None,
            "content": None,
        })


_BACKEND_BOOT_ID = f"backend_{uuid.uuid4().hex[:12]}"
_BACKEND_BOOTED_AT = datetime.now(timezone.utc).isoformat()
_TELEMETRY_CONTINUITY_LOCK = threading.Lock()
_TELEMETRY_CONNECTION_IDS: dict[int, str] = {}
_TELEMETRY_CONTINUITY: dict[str, Any] = {
    "total_connects": 0,
    "total_disconnects": 0,
    "last_disconnect": None,
    "last_broadcast": None,
}


def _telemetry_event_identifier(event: Any) -> str | None:
    if not isinstance(event, Mapping):
        return None
    for key in ("event_id", "id", "seq", "sequence", "type"):
        value = event.get(key)
        if value is not None:
            return str(value)
    return None


def _record_telemetry_connect(websocket: WebSocket) -> str:
    connection_id = f"telemetry_{uuid.uuid4().hex[:12]}"
    with _TELEMETRY_CONTINUITY_LOCK:
        _TELEMETRY_CONNECTION_IDS[id(websocket)] = connection_id
        _TELEMETRY_CONTINUITY["total_connects"] = int(_TELEMETRY_CONTINUITY["total_connects"]) + 1
    return connection_id


def _record_telemetry_disconnect(
    websocket: WebSocket,
    *,
    code: int | None = None,
    reason: str | None = None,
    error: str | None = None,
) -> None:
    with _TELEMETRY_CONTINUITY_LOCK:
        connection_id = _TELEMETRY_CONNECTION_IDS.pop(id(websocket), None)
        if connection_id is None:
            return
        _TELEMETRY_CONTINUITY["total_disconnects"] = int(_TELEMETRY_CONTINUITY["total_disconnects"]) + 1
        _TELEMETRY_CONTINUITY["last_disconnect"] = {
            "connection_id": connection_id,
            "disconnected_at": datetime.now(timezone.utc).isoformat(),
            "code": code,
            "reason": reason,
            "error": error,
        }


def _record_telemetry_broadcast(
    event: Any,
    *,
    client_count: int,
    failure_count: int,
) -> None:
    with _TELEMETRY_CONTINUITY_LOCK:
        _TELEMETRY_CONTINUITY["last_broadcast"] = {
            "broadcast_at": datetime.now(timezone.utc).isoformat(),
            "event_id": _telemetry_event_identifier(event),
            "event_type": event.get("type") if isinstance(event, Mapping) else None,
            "client_count": client_count,
            "failure_count": failure_count,
        }


def runtime_continuity_payload() -> Dict[str, Any]:
    with _TELEMETRY_CONTINUITY_LOCK:
        connection_ids = sorted(_TELEMETRY_CONNECTION_IDS.values())
        total_connects = int(_TELEMETRY_CONTINUITY["total_connects"])
        total_disconnects = int(_TELEMETRY_CONTINUITY["total_disconnects"])
        last_disconnect = copy.deepcopy(_TELEMETRY_CONTINUITY.get("last_disconnect"))
        last_broadcast = copy.deepcopy(_TELEMETRY_CONTINUITY.get("last_broadcast"))
    return {
        "schema": "runtime_continuity_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "backend_boot_id": _BACKEND_BOOT_ID,
        "backend_booted_at": _BACKEND_BOOTED_AT,
        "active_socket_count": len(connection_ids),
        "active_connection_ids": connection_ids,
        "total_connects": total_connects,
        "total_disconnects": total_disconnects,
        "last_disconnect": last_disconnect,
        "last_broadcast": last_broadcast,
        "frontend_boot_id": None,
        "hmr_reload_count": None,
        "store_reset_count": None,
    }

async def broadcaster(session: SessionManager) -> None:
    """
    [ACTION]
    - Teleology: Broadcast telemetry events from the active SessionManager to all connected WebSocket clients.
    - Mechanism: Polls session.get_telemetry_nowait(); uses asyncio.gather to send concurrently; removes dead sockets.
    - Reads: session.get_telemetry_nowait(); global connected_websockets.
    - Writes: ws.send_json(event); mutates connected_websockets via discard on failures.
    - Locks: None (assumes single event-loop mutation of connected_websockets).
    - Fails: asyncio.CancelledError -> exit loop cleanly; any other Exception -> logged, loop continues after backoff.
    - Guarantee: When an event is available, an attempted send is made to each currently connected client; failing clients are removed.
    """
    logger.info("Broadcaster started.")
    while True:
        try:
            event = session.get_telemetry_nowait()
            if event is None:
                await asyncio.sleep(0.05)
                continue
            
            # Create a snapshot of clients to iterate safely
            clients = list(connected_websockets)
            if not clients:
                continue

            # Fire and forget - send to all simultaneously
            tasks = [ws.send_json(event) for ws in clients]
            
            # Wait for all sends to complete (or fail) without raising
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Cleanup dead connections
            failure_count = 0
            for ws, result in zip(clients, results):
                if isinstance(result, Exception):
                    failure_count += 1
                    connected_websockets.discard(ws)
                    _record_telemetry_disconnect(
                        ws,
                        error=f"{type(result).__name__}: {result}",
                    )
            _record_telemetry_broadcast(
                event,
                client_count=len(clients),
                failure_count=failure_count,
            )

        except asyncio.CancelledError:
            logger.info("Broadcaster cancelled.")
            break
        except Exception:
            logger.exception("Broadcaster error")
            await asyncio.sleep(0.2)

async def meta_session_broadcaster(controller: MetaSessionController) -> None:
    """
    [ACTION]
    - Teleology: Broadcast observe-session telemetry events to all connected meta-session WebSocket clients.
    - Guarantee: While running, every available event is attempted to all registered clients; failing clients are removed.
    - Fails: asyncio.CancelledError -> exits loop cleanly; other exceptions are logged and the loop resumes after backoff.
    """
    logger.info("Meta session broadcaster started.")
    while True:
        try:
            event = controller.get_telemetry_nowait()
            if event is None:
                await asyncio.sleep(0.05)
                continue
            
            clients = list(meta_session_websockets)
            if not clients:
                continue

            tasks = [ws.send_json(event) for ws in clients]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for ws, result in zip(clients, results):
                if isinstance(result, Exception):
                    meta_session_websockets.discard(ws)

        except asyncio.CancelledError:
            logger.info("Meta session broadcaster cancelled.")
            break
        except Exception:
            logger.exception("Meta session broadcaster error")
            await asyncio.sleep(0.2)


async def agent_observability_broadcaster(store: AgentTraceStore) -> None:
    """
    [ACTION]
    - Teleology: Broadcast typed agent trace events to all Station observability clients.
    - Mechanism: Mirrors the run/meta broadcaster queue pattern; failures drop dead sockets only.
    """
    logger.info("Agent observability broadcaster started.")
    while True:
        try:
            event = store.get_telemetry_nowait()
            if event is None:
                await asyncio.sleep(0.05)
                continue

            clients = list(agent_observability_websockets)
            if not clients:
                continue
            results = await asyncio.gather(
                *[ws.send_json(event) for ws in clients],
                return_exceptions=True,
            )
            for ws, result in zip(clients, results):
                if isinstance(result, Exception):
                    agent_observability_websockets.discard(ws)
        except asyncio.CancelledError:
            logger.info("Agent observability broadcaster cancelled.")
            break
        except Exception:
            logger.exception("Agent observability broadcaster error")
            await asyncio.sleep(0.2)


async def agent_observability_sampler_loop(sampler: AgentObservabilitySampler) -> None:
    """
    [ACTION]
    - Teleology: Keep the AgentTrace plane warm with low-cost local evidence even when no UI buttons are pressed.
    - Mechanism: Polls cheap substrate files every few seconds and probes Codex CDP at a slower cadence.
    """
    logger.info("Agent observability sampler started.")
    try:
        while True:
            try:
                await asyncio.to_thread(sampler.poll_once)
            except Exception as exc:
                sampler.mark_error(str(exc))
                logger.exception("Agent observability sampler poll failed")
            await asyncio.sleep(sampler.poll_interval_s)
    except asyncio.CancelledError:
        sampler.mark_stopped()
        logger.info("Agent observability sampler cancelled.")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    [ACTION]
    - Teleology: Own server startup/shutdown side-effects (logging wiring, config integrity check, broadcaster lifecycle).
    - Mechanism: Ensures uvicorn logs route to the file handler; validates master_config.json if present; starts broadcaster task; cancels task and shuts down SessionManager on exit.
    - Reads: master_config.json (if present).
    - Writes: state/server_debug.log; starts/cancels broadcaster task; calls session_manager.shutdown().
    - Locks: None (startup/shutdown serialization is handled by FastAPI lifespan).
    - Fails: Invalid JSON in master_config.json -> raises RuntimeError (startup abort).
    - Guarantee: During app lifetime, broadcaster is running; on shutdown, broadcaster is cancelled and SessionManager shutdown is invoked.
    - When-needed: Open when debugging server startup, shutdown, or broadcaster lifecycle wiring rather than individual route handlers.
    - Escalates-to: system/server/session.py::SessionManager; system/server/observe_session.py::MetaSessionController
    """
    _ensure_uvicorn_logs_to_file()
    cfg_path = REPO_ROOT / "master_config.json"
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"CRITICAL: master_config.json corrupt. {e}")

    logger.info("Server lifespan startup complete.")
    # Prewarm the station launcher cache so the first UI request does not pay
    # the ~5s cold-build cost (world-model snapshot + paper-module validation).
    # Runs in a daemon thread so it never blocks uvicorn lifespan.
    try:
        _start_station_launcher_refresh(
            _station_cache_key(),
            thread_name="station-launcher-prewarm",
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("station launcher prewarm failed to schedule: %s", exc)

    # Root Navigator's full handoff builds relation/container/freshness packets
    # and can take tens of seconds under startup contention. Prewarm it in a
    # dedicated thread; the route serves a non-hollow warming shell if the UI
    # arrives before this finishes.
    try:
        _start_root_navigator_handoff_refresh(
            _root_navigator_handoff_cache_key(),
            thread_name="root-navigator-handoff-prewarm",
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("root navigator handoff prewarm failed to schedule: %s", exc)

    # CodeMap is demo-visible and the cold global packet can take tens of
    # seconds. Start the SWR warmup early so `/station/codemap` does not sit on
    # a minute-long skeleton while the projection packet is rebuilt.
    try:
        world_model_loader.prewarm_code_map_snapshot(
            REPO_ROOT,
            max_files=world_model_loader.CODE_MAP_DEFAULT_MAX_FILES,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("code map packet prewarm failed to schedule: %s", exc)

    # Inspector's tree view is visible in recording takes and its cold scan can
    # exceed the frontend capture budget. Prewarm it in the background; the
    # route also has a schema-clean warming shell if the first request wins the
    # race.
    try:
        _schedule_codex_tree_prewarm()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("codex tree prewarm failed to schedule: %s", exc)

    # Prewarm the rest of the hot read-only surfaces sequentially on a single
    # daemon thread. Spawning one-thread-per-surface thrashes the GIL against
    # any inbound request that arrives during prewarm (uvicorn runs workers=1
    # under `run_server.py`), so we serialize here and let subsequent requests
    # hit the warm caches one by one.
    try:
        _hot_prewarms = _hot_surface_prewarm_specs()

        def _prewarm_cached_mapping_loaders() -> None:
            try:
                world_model_loader.load_reactions_snapshot(REPO_ROOT)
            except Exception as exc:
                logger.warning("prewarm reactions failed: %s", exc)
            try:
                _prewarm_attention_snapshot_inline()
            except Exception as exc:
                logger.warning("prewarm attention failed: %s", exc)
            try:
                world_model_loader.prewarm_operations_lens_snapshot(REPO_ROOT)
            except Exception as exc:
                logger.warning("prewarm operations lens failed: %s", exc)

        # Operations catalog gates the QuickLaunch panel on the home page and
        # walks the launchable-ops tree (~30-50s cold). Run it in its own
        # thread in parallel with the serial hot-surface chain instead of
        # tacking it onto the end, so the browser sees a hot cache as soon as
        # possible after backend startup rather than after every other surface
        # has been built.
        _start_operations_catalog_refresh(thread_name="operations-catalog-prewarm")

        def _run_sequential_prewarm() -> None:
            for name, key, builder in _hot_prewarms:
                try:
                    from system.lib.swr_cache import swr_get as _prewarm_get
                    _prewarm_get(name, key, builder, ttl_s=600.0)
                except Exception as inner_exc:  # pragma: no cover - defensive
                    logger.warning("prewarm %s failed: %s", name, inner_exc)
            _prewarm_cached_mapping_loaders()

        threading.Thread(
            target=_run_sequential_prewarm,
            name="hot-surface-prewarm",
            daemon=True,
        ).start()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("hot-surface prewarm failed to schedule: %s", exc)
    broadcast_task = asyncio.create_task(broadcaster(session_manager))
    meta_broadcast_task = asyncio.create_task(meta_session_broadcaster(meta_session_controller))
    agent_observability_task = asyncio.create_task(agent_observability_broadcaster(agent_trace_store))
    agent_observability_sampler_task = asyncio.create_task(
        agent_observability_sampler_loop(agent_observability_sampler)
    )
    try:
        yield
    finally:
        logger.info("Server shutdown requested.")
        broadcast_task.cancel()
        meta_broadcast_task.cancel()
        agent_observability_task.cancel()
        agent_observability_sampler_task.cancel()
        session_manager.shutdown()
        if meta_session_controller._stop_event:
            meta_session_controller._stop_event.set()
        try: await broadcast_task
        except asyncio.CancelledError: pass
        try: await meta_broadcast_task
        except asyncio.CancelledError: pass
        try: await agent_observability_task
        except asyncio.CancelledError: pass
        try: await agent_observability_sampler_task
        except asyncio.CancelledError: pass
        logger.info("Server shutdown complete.")

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
        "zenith://localhost",
        "zenith://app",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=2048, compresslevel=5)

static_dir = REPO_ROOT / "system" / "server" / "static"
if not static_dir.exists(): static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

_SPA_ASSET_PREFIXES = ("assets/",)
_SPA_ASSET_ROOT_FILES = {
    "asset-manifest.json",
    "favicon.ico",
    "manifest.json",
    "manifest.webmanifest",
    "robots.txt",
    "site.webmanifest",
    "vite.svg",
}


def _static_asset_request(full_path: str) -> bool:
    normalized = full_path.strip("/")
    if not normalized:
        return False
    if normalized.startswith(_SPA_ASSET_PREFIXES):
        return True
    return "/" not in normalized and normalized in _SPA_ASSET_ROOT_FILES


def _static_file_under_root(full_path: str) -> Path:
    root = static_dir.resolve()
    candidate = (root / full_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Not Found") from exc
    return candidate


def _frontend_bundle_missing_response(full_path: str) -> HTMLResponse:
    route = "/" + full_path.strip("/")
    escaped_route = html.escape(route if route != "/" else "/station", quote=True)
    body = f"""<!doctype html>
<html lang="en" data-zenith-static-fallback="frontend_bundle_missing">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="2">
    <title>Frontend bundle not ready</title>
    <style>
      :root {{
        color-scheme: dark;
        background: #050805;
        color: #d8ded2;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      }}
      body {{
        min-height: 100vh;
        margin: 0;
        display: grid;
        place-items: start;
        padding: 32px;
        background: #050805;
      }}
      main {{
        max-width: 720px;
        border-top: 1px solid rgba(199, 176, 106, 0.45);
        padding-top: 18px;
      }}
      p {{
        margin: 10px 0 0;
        color: #8f9a88;
        line-height: 1.55;
      }}
      code {{
        color: #c7b06a;
      }}
    </style>
  </head>
  <body data-zenith-static-state="missing" data-zenith-requested-route="{escaped_route}">
    <main>
      <h1>Frontend bundle not ready</h1>
      <p>The backend is running, but <code>system/server/static/index.html</code> is not available yet.</p>
      <p>This page will retry automatically so browser opens and render captures do not land on a raw JSON response.</p>
    </main>
  </body>
</html>
"""
    return HTMLResponse(
        content=body,
        status_code=200,
        headers={
            "Cache-Control": "no-store",
            "X-Zenith-Static-Fallback": "frontend_bundle_missing",
        },
    )

# =============================================================================
# Configuration Helpers
# =============================================================================

def _read_master_config() -> Dict[str, Any]:
    # Delegate to the kernel canonical loader so server runtime reads share
    # tolerant semantics with the other read loaders (parity matrix verified
    # in system/server/tests/test_master_config_loader_parity.py). The
    # lifespan() startup validator above still raises on corrupt JSON at
    # boot; this runtime reader returns {} on transient corruption.
    from system.lib.kernel.config import load_master_config_at
    return load_master_config_at(REPO_ROOT)

def _read_runs_dir_value() -> Any:
    """Best-effort read of configured runs_dir from master_config."""
    try:
        return (_read_master_config().get("paths") or {}).get("runs_dir")
    except Exception:
        return None


def _bridge_runtime_config() -> Dict[str, Any]:
    try:
        return _read_master_config()
    except Exception:
        return {}


def _bridge_diagnostics_payload(provider: Optional[str] = None, *, limit: int = 6) -> Dict[str, Any]:
    config = _bridge_runtime_config()
    providers = [provider] if provider else None
    try:
        payload = bridge_diagnostics(config=config, providers=providers, limit_per_provider=limit)
    except Exception as exc:
        return {
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "configured": False,
            "browser_running": False,
            "cdp_reachable": False,
            "debug_url": None,
            "providers": {},
            "error": str(exc),
        }
    if not isinstance(payload, dict):
        return {
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "configured": False,
            "browser_running": False,
            "cdp_reachable": False,
            "debug_url": None,
            "providers": {},
            "error": "bridge diagnostics returned a non-dict payload",
        }
    return payload


def _resolve_raw_seed_family_entry(family_token: str) -> Dict[str, Any]:
    from system.lib.kernel.commands.navigate import _resolve_family_entry_for_raw_seed

    return _resolve_family_entry_for_raw_seed(family_token)


def _invoke_kernel_append_raw_seed(
    family_token: str,
    text: str,
    *,
    heading: Optional[str] = None,
) -> Dict[str, Any]:
    import io
    from system.lib.kernel.commands.navigate import cmd_append_raw_seed

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            returncode = cmd_append_raw_seed(
                family_token,
                text,
                heading=heading,
                auto_sync=True,
                live=True,
            )
    except Exception as exc:
        return {
            "returncode": 1,
            "stderr": str(exc),
        }

    output = stdout_buffer.getvalue().strip()
    stderr = stderr_buffer.getvalue().strip()

    payload: Dict[str, Any] = {}
    if output:
        lines = [line for line in output.splitlines() if line.strip()]
        if lines:
            try:
                payload = json.loads(lines[-1])
            except json.JSONDecodeError:
                payload = {"stdout": output}
    payload.setdefault("returncode", returncode)
    if output and "stdout" not in payload:
        payload["stdout"] = output
    if stderr:
        payload["stderr"] = stderr
    return payload


def _read_json_if_exists(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl_tail_if_exists(path: Path, *, limit: int = 20) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()[-max(1, int(limit or 1)) :]
        if line.strip()
    ]
    records: List[Dict[str, Any]] = []
    for line in rows:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _write_json_pretty(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _raw_seed_assimilation_counts(family: str) -> Dict[str, Any]:
    try:
        projection = build_raw_seed_assimilation_projection(
            family=family,
            repo_root=REPO_ROOT,
            include_graph=False,
        )
    except Exception:
        return {}
    counts = projection.get("counts")
    return dict(counts) if isinstance(counts, Mapping) else {}


def _load_alchemy_review_bundle(
    family: str,
    bundle_id: str,
) -> tuple[str, Path, Dict[str, Any], Dict[str, Any] | None]:
    family_dir = _resolve_raw_seed_family_entry(family).get("family_dir") or ""
    if not family_dir:
        family_dir = build_raw_seed_assimilation_projection(
            family=family,
            repo_root=REPO_ROOT,
            include_graph=False,
        )["family"]["family_dir"]
    review_path = REPO_ROOT / _family_raw_seed_alchemy_review_path(family_dir)
    review_payload = _read_json_if_exists(review_path)
    bundle = next(
        (
            dict(item)
            for item in (review_payload.get("bundles") or [])
            if isinstance(item, Mapping) and _string(item.get("bundle_id")) == _string(bundle_id)
        ),
        None,
    )
    return family_dir, review_path, review_payload, bundle


def _persist_alchemy_dry_run_metadata(
    *,
    family: str,
    bundle_id: str,
    ok: bool,
    receipt: Mapping[str, Any],
    started_at: str,
    finished_at: str,
) -> None:
    family_dir, review_path, review_payload, bundle = _load_alchemy_review_bundle(family, bundle_id)
    if not family_dir or bundle is None:
        return
    bundles = [dict(item) for item in (review_payload.get("bundles") or []) if isinstance(item, Mapping)]
    bundle_hash = compute_bundle_hash(bundle)
    for item in bundles:
        if _string(item.get("bundle_id")) != _string(bundle_id):
            continue
        item["last_dry_run_at"] = finished_at
        item["last_dry_run_ok"] = bool(ok)
        item["last_dry_run_bundle_hash"] = bundle_hash
        item["last_dry_run_receipt"] = {
            "started_at": started_at,
            "finished_at": finished_at,
            "status": "ok" if ok else "failed",
            "artifacts": list(receipt.get("artifacts") or []),
            "warnings": list(receipt.get("warnings") or []),
            "errors": list(receipt.get("errors") or []),
        }
        break
    review_payload["bundles"] = bundles
    review_payload["generated_at"] = finished_at
    _write_json_pretty(review_path, review_payload)


def _raw_seed_operation_receipt(
    *,
    operation: str,
    family: str,
    command_equivalent: str,
    started_at: str,
    finished_at: str,
    status: str,
    artifacts: List[str],
    before_counts: Mapping[str, Any],
    after_counts: Mapping[str, Any],
    output: Mapping[str, Any] | None = None,
    input_payload: Mapping[str, Any] | None = None,
    warnings: List[str] | None = None,
    errors: List[str] | None = None,
) -> Dict[str, Any]:
    return {
        "kind": "raw_seed_assimilation_operation_receipt",
        "operation": operation,
        "family": family,
        "input": dict(input_payload or {}),
        "command_equivalent": command_equivalent,
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "artifacts": list(artifacts),
        "before_counts": dict(before_counts),
        "after_counts": dict(after_counts),
        "warnings": list(warnings or []),
        "errors": list(errors or []),
        "output": dict(output or {}),
    }


def _raw_seed_artifacts_for_family(family_dir: str) -> Dict[str, Optional[str]]:
    from system.lib.raw_seed_registry import (
        raw_seed_index_path_for_family,
        raw_seed_json_path_for_family,
        raw_seed_markdown_path_for_family,
        raw_seed_snapshot_path_for_family,
    )

    return {
        "family_dir": family_dir,
        "raw_seed_path": raw_seed_markdown_path_for_family(family_dir),
        "raw_seed_json_path": raw_seed_json_path_for_family(family_dir),
        "raw_seed_index_path": raw_seed_index_path_for_family(family_dir),
        "raw_seed_snapshot_path": raw_seed_snapshot_path_for_family(family_dir),
    }


def _paragraph_fingerprint_set(raw_seed_json_path: Path) -> set[str]:
    payload = _read_json_if_exists(raw_seed_json_path)
    return {
        str(item.get("fingerprint") or "").strip()
        for item in (payload.get("paragraphs") or [])
        if isinstance(item, Mapping) and str(item.get("fingerprint") or "").strip()
    }


def _appended_anchor_ids(raw_seed_json_path: Path, before_fingerprints: set[str]) -> List[str]:
    payload = _read_json_if_exists(raw_seed_json_path)
    anchor_ids: List[str] = []
    for item in payload.get("paragraphs") or []:
        if not isinstance(item, Mapping):
            continue
        fingerprint = str(item.get("fingerprint") or "").strip()
        paragraph_id = str(item.get("id") or "").strip()
        if fingerprint and fingerprint not in before_fingerprints and paragraph_id:
            anchor_ids.append(paragraph_id)
    return anchor_ids

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

def _validate_run_id(run_id: str) -> str:
    """
    Validate run_id shape to block traversal/control characters before filesystem access.
    """
    if not isinstance(run_id, str):
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    if len(run_id) == 0 or len(run_id) > 128:
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    if ".." in run_id or "/" in run_id or "\\" in run_id:
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    if any(ord(ch) < 32 for ch in run_id):
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    if not _RUN_ID_RE.fullmatch(run_id):
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    return run_id

def _resolve_run_dir(runs_dir: Path, run_id: str) -> Path:
    safe_run_id = _validate_run_id(run_id)
    root = runs_dir.resolve()
    run_dir = (root / safe_run_id).resolve()
    try:
        run_dir.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    return run_dir

def _resolve_scope_ids(universe: Dict[str, Any], target_id: str) -> Set[str]:
    """
    Resolve execution scope using the same policy as GodModeEngine:
    group closure + upstream dependency walk.
    """
    if target_id not in universe:
        raise HTTPException(status_code=404, detail=f"Target node '{target_id}' not found.")

    target_node = universe[target_id]
    target_group = getattr(target_node, "group", "unknown")

    scope: Set[str] = set()
    stack: List[str] = []

    if isinstance(target_group, str) and target_group and target_group != "unknown":
        for nid, node in universe.items():
            if getattr(node, "group", "unknown") == target_group:
                scope.add(nid)
                stack.append(nid)

    if target_id not in scope:
        scope.add(target_id)
        stack.append(target_id)

    while stack:
        curr = stack.pop()
        node = universe.get(curr)
        if node is None:
            continue
        for dep in getattr(node, "dependencies", ()) or ():
            if dep not in scope:
                scope.add(dep)
                stack.append(dep)

    return scope

def _artifact_status_ok(payload: Dict[str, Any]) -> bool:
    status = str(payload.get("status") or (payload.get("metadata") or {}).get("status") or "").lower()
    return status in {"success", "loaded"}


def _normalize_codex_path(path: str) -> str:
    """
    Normalize short codex-relative paths used by inspector endpoints.

    Supported shorthand prefixes:
    - contracts/*
    - configs/*
    """
    if not isinstance(path, str):
        return path
    normalized = path.strip().replace("\\", "/").lstrip("/")
    if normalized.startswith("codex/"):
        return normalized
    if normalized.startswith("contracts/") or normalized.startswith("configs/"):
        return f"codex/{normalized}"
    return normalized

def _write_master_config(data: Dict[str, Any]) -> None:
    cfg_path = REPO_ROOT / "master_config.json"
    bak_path = cfg_path.with_suffix(".json.bak")
    base_path = REPO_ROOT / "master_config.base.json"

    # 1. Backup current state before overwrite
    if cfg_path.exists():
        try:
            shutil.copy2(cfg_path, bak_path)
        except Exception as e:
            logger.warning(f"Failed to create config backup: {e}")

    # 2. Save base truth on first ever write (never overwritten automatically)
    if not base_path.exists() and cfg_path.exists():
        try:
            shutil.copy2(cfg_path, base_path)
        except Exception as e:
            logger.warning(f"Failed to create base config backup: {e}")

    # 3. Atomic write
    temp_path = cfg_path.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, cfg_path)
    except Exception as e:
        if temp_path.exists():
            try: os.remove(temp_path)
            except OSError: pass
        raise IOError(f"Atomic write failed: {e}")

# =============================================================================
# NEW API SURFACE
# =============================================================================

@app.get("/api/lobby", response_model=LobbyState)
def get_lobby_state():
    """
    [ACTION]
    - Teleology: Serve the lobby view used by the UI (missions + candidate runs).
    - Mechanism: Delegates to translator.scan_lobby() and returns the resulting LobbyState.
    - Reads: Filesystem state as required by Translator (repo/codex/state inputs).
    - Writes: None.
    - Fails: TranslationError -> HTTP 500 with detail.
    - Guarantee: On success, returns a LobbyState conforming to the response_model.
    - When-needed: Open when the lobby page or an operator needs the exact backend entrypoint for mission and candidate-run hydration.
    - Escalates-to: system/server/translator.py::Translator.scan_lobby; system/server/schemas.py::LobbyState
    """
    try:
        return translator.scan_lobby()
    except TranslationError as e:
        logger.error(f"Lobby generation failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/api/data-roots", response_model=List[DataRootSummary])
def get_data_roots():
    """
    [ACTION]
    - Teleology: Serve the canonical reusable data-root inventory without requiring full lobby hydration.
    - Mechanism: Delegates to translator.scan_data_roots() and returns the grouped root summaries.
    - Reads: Filesystem run state as required by Translator.
    - Writes: None.
    - Fails: TranslationError -> HTTP 500 with detail.
    - Guarantee: On success, returns the same canonical root model published through LobbyState.data_roots.
    - When-needed: Open when the UI needs grouped reusable source snapshots without paying for full lobby translation.
    - Escalates-to: system/server/translator.py::Translator.scan_data_roots; system/server/schemas.py::DataRootSummary
    """
    try:
        return translator.scan_data_roots()
    except TranslationError as e:
        logger.error(f"Data-root generation failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/api/mission/{mission_name}/graph", response_model=GraphView)
def get_mission_graph(mission_name: str):
    """
    [ACTION]
    - Teleology: Serve the graph view for a specific mission name.
    - Mechanism: Scans lobby to resolve mission_name -> target_id; calls compile_mission_view(REPO_ROOT, target_id).
    - Reads: Translator lobby inputs; mission definitions required by compile_mission_view.
    - Writes: None.
    - Forbid: Unknown mission_name -> HTTP 404.
    - Fails: Any unexpected Exception -> HTTP 500 with detail.
    - Guarantee: On success, returns a GraphView for the resolved mission.
    - When-needed: Open when a route or UI trace needs the exact mission-name-to-graph resolution path used by the backend.
    - Escalates-to: system/server/translator.py::Translator.scan_lobby; system/server/graph.py::compile_mission_view; system/server/schemas.py::GraphView
    """
    try:
        lobby = translator.scan_lobby()
        target_id = None
        for m in lobby.missions:
            if m.name == mission_name:
                target_id = m.target_id
                break
        if not target_id:
            raise HTTPException(status_code=404, detail=f"Mission '{mission_name}' not found.")
        return compile_mission_view(REPO_ROOT, target_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _control_room_bridge_context() -> ControlRoomBridgeContext:
    payload = _bridge_diagnostics_payload(limit=6)
    error = payload.get("error") if isinstance(payload.get("error"), str) else None
    if error:
        status_value = "error"
        preflight_status = "error"
    elif bool(payload.get("browser_running")) or bool(payload.get("cdp_reachable")):
        status_value = "online"
        preflight_status = "ready"
    else:
        status_value = "offline"
        preflight_status = "offline"
    return ControlRoomBridgeContext(
        status=status_value,
        preflight_status=preflight_status,
        diagnostics_captured_at=payload.get("captured_at")
        if isinstance(payload.get("captured_at"), str)
        else None,
        error=error,
    )


def _control_room_run_context() -> ControlRoomRunContext:
    payload = session_manager.get_active_run_status()
    if not isinstance(payload, Mapping):
        payload = {}
    vector = payload.get("vector") if isinstance(payload.get("vector"), Mapping) else {}
    status_value = vector.get("status") if isinstance(vector.get("status"), str) else None
    if status_value is None:
        status_value = "running" if bool(payload.get("is_running")) else "idle"
    return ControlRoomRunContext(
        status=status_value,
        active_run_id=payload.get("active_run_id")
        if isinstance(payload.get("active_run_id"), str)
        else None,
        active_mission=payload.get("active_mission")
        if isinstance(payload.get("active_mission"), str)
        else None,
        is_running=bool(payload.get("is_running")),
    )


def _build_control_room_operational_context(mission_name: str) -> ControlRoomOperationalContextResponse:
    lobby = translator.scan_lobby()
    target_id = None
    for mission in lobby.missions:
        if mission.name == mission_name:
            target_id = mission.target_id
            break
    if not target_id:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_name}' not found.")

    graph_context = ControlRoomGraphContext()
    try:
        graph = compile_mission_view(REPO_ROOT, target_id)
        node_count = len(graph.nodes)
        edge_count = len(graph.edges)
        graph_context = ControlRoomGraphContext(
            status="present" if node_count > 0 else "empty",
            node_count=node_count,
            edge_count=edge_count,
            root_id=graph.root_id,
            run_id=graph.run_id,
            error=graph.topology_error.details if graph.topology_error else None,
        )
    except Exception as exc:
        logger.warning("Control Room graph context failed for %s: %s", mission_name, exc)
        graph_context = ControlRoomGraphContext(
            status="error",
            error=str(exc),
        )

    run_context = _control_room_run_context()
    bridge_context = _control_room_bridge_context()
    if graph_context.status == "present":
        state_value = "populated"
    elif graph_context.status == "empty":
        state_value = "resting"
    elif graph_context.status == "error":
        state_value = "invalid"
    else:
        state_value = "missing"

    return ControlRoomOperationalContextResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        mission_name=mission_name,
        target_id=target_id,
        route_ready=True,
        state=state_value,
        graph=graph_context,
        run=run_context,
        bridge=bridge_context,
        execution_authority="locked" if run_context.is_running else "operator_controlled",
    )


@app.get(
    "/api/control-room/{mission_name}/operational-context",
    response_model=ControlRoomOperationalContextResponse,
)
def get_control_room_operational_context(mission_name: str):
    """
    [ACTION]
    - Teleology: Serve the backend truth packet that causes Control Room readiness.
    - Mechanism: Joins mission graph preview, active-run status, and bridge diagnostics.
    - Reads: Translator lobby, graph compiler inputs, SessionManager state, bridge diagnostics.
    - Writes: None.
    - Guarantee: Unknown mission remains 404; graph failures stay explicit as invalid graph context.
    """
    try:
        return _build_control_room_operational_context(mission_name)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Control Room operational context failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/ignite", response_model=IgnitionResponse, status_code=status.HTTP_202_ACCEPTED)
def ignite_mission(payload: IgnitePayload):
    """
    [ACTION]
    - Teleology: Start (ignite) a run for a mission/target_id.
    - Mechanism: Calls session_manager.ignite_run(...) and maps internal status to the IgnitionResponse schema.
    - Reads: SessionManager state; run orchestration inputs from IgnitePayload.
    - Writes: Creates/updates run state via SessionManager; emits log lines.
    - Fails: ValueError -> HTTP 400; HTTPException -> re-raised (preserve 4xx); other Exception -> HTTP 500.
    - Guarantee: Returns IgnitionResponse with run_id and a schema-valid status (ignited|failed|busy).
    - When-needed: Open when run-launch debugging needs the HTTP-to-session handoff, temporal-contract mapping, or status normalization for ignite responses.
    - Escalates-to: system/server/session.py::SessionManager.ignite_run; system/server/schemas.py::IgnitionResponse
    """
    try:
        result = session_manager.ignite_run(
            target_id=payload.target_id,
            mission_name=payload.mission_name,
            run_mode=payload.run_mode,
            execution_mode=payload.execution_mode,
            subject_group=payload.subject_group,
            source_run_id=payload.source_run_id,
            feed_source_run_id=payload.feed_source_run_id,
            source_data_root_id=payload.source_data_root_id,
            feed_data_root_id=payload.feed_data_root_id,
            horizon=payload.horizon,
            force_load_stale_feeds=payload.force_load_stale_feeds,
        )
        logger.info(f"Ignited Mission: {payload.mission_name} -> {result['run_id']}")
        
        raw_status = result.get("status", "ignited")
        
        # Map internal status 'accepted' (from session) to schema status 'ignited'
        valid_status = "ignited"
        if raw_status in ["failed", "error"]:
            valid_status = "failed"
        elif raw_status in ["busy", "running"]:
            valid_status = "busy"
        
        tc_raw = result.get("temporal_contract")
        temporal_contract = TemporalContract(**tc_raw) if tc_raw else None

        return IgnitionResponse(
            run_id=result["run_id"],
            status=valid_status,
            topology_changed=result.get("topology_changed", False),
            temporal_contract=temporal_contract,
        )

    except HTTPException:
        # [FIX] Allow 400/409 errors to pass through to the client
        raise
    except ValueError as e:
        logger.warning(f"Ignite rejected: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Ignite failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/api/ignite/resume_preflight", response_model=ResumeFeedPreflightResponse)
def ignite_resume_preflight(payload: ResumeFeedPreflightPayload):
    """
    [ACTION]
    - Teleology: Preview whether resume would reuse or re-fetch feed artifacts for a target scope.
    - Mechanism: Load current node universe, compute execution scope, compare feed node artifact hashes against current node hashes.
    - Reads: state/runs/<source_run_id>/artifacts/*.json and codex node definitions.
    - Writes: None.
    - Forbid: Missing source run directory or unknown target node.
    - Guarantee: Returns stale/reusable/missing feed node sets so UI can offer an explicit override.
    """
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_source_run_id = _validate_run_id(payload.source_run_id)
    source_run_dir = _resolve_run_dir(runs_dir, safe_source_run_id)
    if not source_run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Source run not found: {safe_source_run_id}")

    artifacts_dir = source_run_dir / "artifacts"
    if not artifacts_dir.exists():
        raise HTTPException(status_code=404, detail=f"Source run has no artifacts directory: {safe_source_run_id}")

    try:
        loader = PhysicalLoader(root_dir=REPO_ROOT, inject_sys_path=False)
    except Exception:
        loader = PhysicalLoader(root_dir=REPO_ROOT)
    universe = loader.load_all_nodes()
    scope = _resolve_scope_ids(universe, payload.target_id)
    feed_node_ids = sorted(
        nid for nid in scope
        if nid in universe
        if bool((getattr(universe[nid], "meta", {}) or {}).get("is_feed"))
    )

    reusable_feed_nodes: List[str] = []
    stale_feed_nodes: List[ResumeFeedStaleNode] = []
    missing_feed_nodes: List[str] = []

    for node_id in feed_node_ids:
        node = universe[node_id]
        artifact_path = artifacts_dir / f"{node_id}.json"
        if not artifact_path.exists():
            missing_feed_nodes.append(node_id)
            continue

        try:
            with open(artifact_path, "r", encoding="utf-8") as f:
                artifact = json.load(f)
        except Exception:
            missing_feed_nodes.append(node_id)
            continue

        if not isinstance(artifact, dict) or not _artifact_status_ok(artifact):
            missing_feed_nodes.append(node_id)
            continue

        current_hash = hash_node(node)
        artifact_hash_raw = artifact.get("node_hash")
        artifact_hash = artifact_hash_raw if isinstance(artifact_hash_raw, str) else None
        artifact_status = str(artifact.get("status") or (artifact.get("metadata") or {}).get("status") or "") or None

        if artifact_hash == current_hash:
            reusable_feed_nodes.append(node_id)
            continue

        metadata = artifact.get("metadata") or {}
        stale_feed_nodes.append(
            ResumeFeedStaleNode(
                node_id=node_id,
                artifact_hash=artifact_hash,
                current_hash=current_hash,
                artifact_status=artifact_status,
                config_ref=getattr(node, "config_ref", None),
                artifact_config_ref=metadata.get("config_ref") if isinstance(metadata, dict) else None,
                merged_hash=getattr(node, "merged_hash", None),
                artifact_merged_hash=metadata.get("merged_hash") if isinstance(metadata, dict) else None,
            )
        )

    return ResumeFeedPreflightResponse(
        source_run_id=safe_source_run_id,
        target_id=payload.target_id,
        scope_feed_node_count=len(feed_node_ids),
        has_stale_feeds=len(stale_feed_nodes) > 0,
        reusable_feed_nodes=reusable_feed_nodes,
        stale_feed_nodes=stale_feed_nodes,
        missing_feed_nodes=missing_feed_nodes,
    )

@app.delete("/api/run", response_model=StopRunResponse)
def stop_run(run_id: Optional[str] = None):
    """
    [ACTION]
    - Teleology: Stop the active run via SessionManager.
    - Guarantee: Returns StopRunResponse with status "stopped", "no_active_run", or "failed"; maps internal "stopping" to "stopped".
    - Fails: HTTPException is re-raised (allows 404 "no active run" to reach client); other exceptions -> HTTP 500.
    """
    try:
        result = session_manager.kill_run()
        
        # Enforce contract strictness
        # session.kill_run should return "stopped", but if it returns "stopping", we map it.
        raw_status = result.get("status", "stopped")
        if raw_status == "stopping":
            raw_status = "stopped"
            
        return StopRunResponse(
            run_id=result.get("run_id"),
            status=raw_status
        )
    except HTTPException:
        # [FIX] Allow 404 "No active run" to pass through
        # This allows the UI to treat 404 as "Job Done"
        raise
    except Exception as e:
        logger.exception("Stop run failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/run/{run_id}/final_state", response_model=RunSummary)
def get_run_final_state(run_id: str):
    """
    [ACTION]
    - Teleology: Serve the finalized RunSummary, with forensic reconstruction overlay for crashed/dead runs.
    - Guarantee: Always returns a RunSummary; active runs get a synthetic amber; dead runs get forensic red reconstruction.
    - Fails: HTTP 404 if the run directory does not exist.
    """
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_id = _validate_run_id(run_id)
    run_root = _resolve_run_dir(runs_dir, safe_run_id)
    summary_path = run_root / "run_summary.json"
    
    # 1. Forensic Reconstruction (Always run this for truth)
    reconstructed_outcomes = reconstruct_run_state(run_root)
    
    # 2. Merge Strategy (Overlay onto Summary if exists)
    if summary_path.exists():
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Overlay reconstruction onto summary
            # We trust the file scan more than the engine's memory dump at crash time
            if "node_outcomes" not in data: data["node_outcomes"] = {}
            data["node_outcomes"].update(reconstructed_outcomes)
            
            # If frontier detected (failure), ensure grade is red
            if any(v == "failure" for v in reconstructed_outcomes.values()):
                data["grade"] = "red"
                if "Frontier" not in data.get("grade_reason", ""):
                     data["grade_reason"] = (data.get("grade_reason", "") + " (Frontier Detected)").strip()
            
            return RunSummary(**data)
        except Exception as e:
            logger.warning(f"Failed to merge summary for {safe_run_id}, falling back to synthesis: {e}")
            pass

    # 3. Synthesis (Sudden Death / Missing Summary)
    if not run_root.exists():
        raise HTTPException(status_code=404, detail="Run not found")
        
    # Check if run is currently active (synthetic amber)
    active_status = session_manager.get_active_run_status()
    if active_status.get("active_run_id") == safe_run_id and active_status.get("is_running"):
         return RunSummary(
            run_id=safe_run_id,
            timestamp=time.time(),
            grade="amber",
            grade_reason="Run initializing or active...",
            node_outcomes=reconstructed_outcomes, # Partial progress
            duration_seconds=0.0
        )

    # Dead run logic
    timestamp = 0.0
    try:
        timestamp = (run_root / "runtime_context.json").stat().st_mtime
    except Exception:
        timestamp = time.time()

    return RunSummary(
        run_id=safe_run_id,
        timestamp=timestamp,
        grade="red",
        grade_reason="Run Terminated Abnormally (Forensic Reconstruction)",
        node_outcomes=reconstructed_outcomes,
        duration_seconds=0.0
    )

# =============================================================================

@app.get("/api/candidates", response_model=List[CandidateRun])
def get_candidates(
    mission: Optional[str] = None,
    has_feeds: bool = False,
    sort_by: str = "timestamp",
    limit: int = 100
):
    """
    [ACTION]
    - Teleology: List candidate runs for UI selection (optionally filtered/sorted).
    - Mechanism: Uses translator.scan_lobby().candidates; applies mission/has_feeds filters; sorts by timestamp or data_timestamp; applies limit.
    - Reads: Translator lobby inputs and derived candidate metadata.
    - Writes: None.
    - Orders: Sorting is deterministic given identical candidate lists and requested sort_by.
    - Fails: Unexpected exceptions from translator/processing -> propagate as server error.
    - Guarantee: Returns a list of CandidateRun up to the requested limit.
    """
    lobby = translator.scan_lobby()
    results = lobby.candidates
    
    if mission:
        results = [r for r in results if r.mission_name.lower() == mission.lower()]
    
    if has_feeds:
        # Strict feed check (approx 6 feeds)
        results = [r for r in results if r.feed_count >= 6]
        
    # Sort
    if sort_by == "data_timestamp":
        results.sort(key=lambda x: x.data_timestamp or 0, reverse=True)
    else:
        results.sort(key=lambda x: x.timestamp, reverse=True)
        
    return results[:limit]

# STANDARD ENDPOINTS
# =============================================================================

@app.get("/api/config/ui", response_model=UIConfig)
def get_ui_config():
    """
    [ACTION]
    - Teleology: Return the UI-specific config subtree for frontend rendering.
    - Mechanism: Reads master_config.json under config_lock and returns UIConfig(**cfg['ui']).
    - Reads: master_config.json.
    - Writes: None.
    - Locks: Acquires config_lock for read consistency.
    - Fails: Config read/parse failure -> HTTP 500.
    - Guarantee: Returns a UIConfig instance conforming to the response_model.
    """
    with config_lock:
        try:
            cfg = _read_master_config()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Config Corruption: {e}")
    return UIConfig(**cfg.get("ui", {}))

@app.put("/api/config/ui")
def update_ui_config(payload: UIConfig = Body(...)):
    """
    [ACTION]
    - Teleology: Patch/update the UI config subtree.
    - Mechanism: Takes a UIConfig payload; model_dump(exclude_unset=True) to produce patch; deep-merges into cfg['ui']; writes via _write_master_config.
    - Reads: master_config.json.
    - Writes: master_config.json (atomic replace); may create master_config.json.bak and master_config.base.json.
    - Locks: Acquires config_lock to serialize config mutation.
    - Fails: Any exception during merge/write -> HTTP 500.
    - Guarantee: On success, persisted config contains the patched ui keys and the endpoint returns the payload.
    """
    patch_data = payload.model_dump(exclude_unset=True)
    
    # [FIX] Governance Audit Removed
    # The audit_config_purity check was incorrectly flagging valid UI config keys 
    # (like 'theme', 'orientation') as unknown node properties.
    # UI Config validation is already handled by Pydantic schema above.

    with config_lock:
        try:
            cfg = _read_master_config()
            cfg["ui"] = _deep_merge(cfg.get("ui", {}), patch_data)
            _write_master_config(cfg)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return payload

@app.post("/api/config/ui/reset")
def reset_ui_config():
    """
    [ACTION]
    - Teleology: Reset all UI config to schema defaults.
    - Mechanism: Replaces cfg['ui'] with UIConfig() defaults; writes via _write_master_config.
    - Writes: master_config.json.
    - Guarantee: On success, persisted UI config matches UIConfig schema defaults.
    """
    defaults = UIConfig().model_dump()
    with config_lock:
        try:
            cfg = _read_master_config()
            cfg["ui"] = defaults
            _write_master_config(cfg)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return UIConfig(**defaults)

@app.get("/api/config/system")
def get_system_config():
    """
    [ACTION]
    - Teleology: Return the full enriched system config (including {value, desc} objects) for UI tooltips.
    - Mechanism: Reads master_config.json under config_lock; removes '__doc__' key if present; returns the dict.
    - Reads: master_config.json.
    - Writes: None.
    - Locks: Acquires config_lock for read consistency.
    - Fails: Config read/parse failure -> HTTP 500.
    - Guarantee: Returns a JSON-serializable dict representing the current system configuration.
    """
    with config_lock:
        try:
            cfg = _read_master_config()
            if "__doc__" in cfg:
                del cfg["__doc__"]
            return cfg
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Config Error: {e}")


@app.get("/api/system/root-coverage-state")
def get_root_coverage_state():
    """
    [ACTION]
    - Teleology: Return the measured self-comprehension root coverage state for the operator navigation frontend.
    - Mechanism: Reads the builder-owned System Atlas sidecar, with an in-memory fallback when the gitignored sidecar is absent.
    - Reads: state/system_atlas/root_coverage_state.json plus root coverage builder fallback inputs.
    - Writes: None.
    - Guarantee: Returns a JSON object with frontend_graph, branches, and doctrine_layers keys.
    """
    return _load_root_coverage_state()


@app.get("/api/system/navigation-surface")
def get_navigation_surface(
    kind: str = Query(..., min_length=2, max_length=80),
    band: str = Query("flag", min_length=3, max_length=40),
    id: Optional[str] = Query(default=None, max_length=240),
):
    """
    [ACTION]
    - Teleology: Return an allowlisted kernel option-surface packet for Root Navigator substrate drilldown.
    - Mechanism: Calls the standard option-surface builder directly for the requested kind/band/id.
    - Reads: The governing substrate for the requested artifact kind.
    - Writes: None.
    - Guarantee: Does not expose release/readiness/dissemination drilldowns through this operator-navigation route.
    """
    return _load_navigation_surface(kind, band, id)


@app.get("/api/system/root-navigator-handoff")
def get_root_navigator_handoff():
    """
    [ACTION]
    - Teleology: Return the AI-native Root Navigator Claude frontend handoff packet so the UI consumes packet authority instead of hardcoding ontology in TSX.
    - Mechanism: Serves a stale-while-revalidate cached handoff packet, with a non-hollow warming shell while startup prewarm is in flight.
    - Reads: docs/dissemination/station_view_direction_specs/root_navigator_constitutional_atlas.json plus state/system_atlas/root_coverage_state.json plus state/frontend_navigation/* plus state/observability/render_load_index.json.
    - Writes: None.
    - Guarantee: Returns the same root_navigator_claude_frontend_handoff_packet_v0 schema as `./repo-python kernel.py --root-navigator-handoff`.
    """
    return _root_navigator_handoff_payload()


@app.put("/api/config/system")
def update_system_config(payload: Dict[str, Any] = Body(...)):
    """
    [ACTION]
    - Teleology: Patch/update the full system config and report whether bridge settings changed.
    - Mechanism: Reads old config; deep-merges payload; compares old_bridge vs new_bridge (JSON canonical compare); writes new config.
    - Reads: master_config.json.
    - Writes: master_config.json (atomic replace); may create backup/base-truth files.
    - Locks: Acquires config_lock to serialize config mutation.
    - Fails: Any exception during merge/write -> HTTP 500.
    - Guarantee: Returns {status:'updated', bridge_changed:<bool>} reflecting whether the 'bridge' subtree changed.
    """
    with config_lock:
        try:
            old_cfg = _read_master_config()
            # [FIX] Isolate write domains: strip 'ui' from system config payload
            # to prevent Settings page stale snapshot from overwriting Tuner autosaves.
            payload.pop("ui", None)
            # [v2] Compute compat-writer warnings + effective row ids touched
            # before mutating, so the response self-describes the patch's
            # registry footprint without hard-failing.
            warnings, effective_row_ids_touched = _compat_writer_warnings(payload)
            new_cfg = _deep_merge(old_cfg, payload)

            old_bridge = old_cfg.get("bridge", {})
            new_bridge = new_cfg.get("bridge", {})
            bridge_changed = json.dumps(old_bridge, sort_keys=True) != json.dumps(new_bridge, sort_keys=True)

            _write_master_config(new_cfg)
            return {
                "status": "updated",
                "bridge_changed": bridge_changed,
                "warnings": warnings,
                "effective_row_ids_touched": effective_row_ids_touched,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


def _compat_writer_warnings(payload: Dict[str, Any]) -> tuple[list[str], list[str]]:
    """[ACTION]
    - Teleology: Surface registry-bypass conditions on PUT /api/config/system without hard-failing — observability before enforcement per v2 child slice 6.
    - Mechanism: Look up master_config.<key> for each top-level key in the patch; classify by field_manager.field_manager_class; emit human-readable warning per class-1..class-4 condition.
    - Reads: payload top-level keys; live federated config authority registry under REPO_ROOT.
    - Writes: None.
    - Guarantee: Returns (warnings, effective_row_ids_touched). Never raises — registry lookup failure yields empty results so writes are not blocked.
    - When-needed: Called from update_system_config before _write_master_config so the response payload can self-describe the patch.
    """
    try:
        registry = load_config_authority_registry(repo_root=REPO_ROOT)
    except Exception:
        return ([], [])
    rows_by_id = {row["config_id"]: row for row in registry.get("rows", [])}
    warnings: list[str] = []
    effective_row_ids_touched: list[str] = []
    for top_key in payload.keys():
        config_id = f"master_config.{top_key}"
        row = rows_by_id.get(config_id)
        if row is None:
            warnings.append(
                f"unregistered top-level section: {top_key!r} (config_id {config_id} not in registry)"
            )
            continue
        effective_row_ids_touched.append(config_id)
        field_manager = row.get("field_manager") or {}
        field_manager_class = field_manager.get("field_manager_class")
        if field_manager_class != "compatibility_edit":
            warnings.append(
                f"non-compatibility-edit row touched: {config_id} field_manager_class="
                f"{field_manager_class!r}; PUT /api/config/system is the compatibility writer "
                f"surface and is not the recommended path for this row"
            )
        if row.get("class") == "secret_or_private_config":
            warnings.append(
                f"secret-or-private row touched: {config_id}; secret/private config rows are "
                f"explicitly outside read/write exposure for v1"
            )
        writer = row.get("writer")
        if not writer:
            warnings.append(
                f"row touched but no writer recorded: {config_id}"
            )
    return (warnings, sorted(effective_row_ids_touched))


@app.get("/api/config/surface", response_model=ConfigSurfaceSummaryResponse)
def config_surface_summary():
    return load_config_authority_registry(repo_root=REPO_ROOT)


@app.get("/api/config/surface/search", response_model=ConfigSurfaceSearchResponse)
def config_surface_search(q: str = Query(..., min_length=1, max_length=240)):
    return search_config_authority_registry(query=q, repo_root=REPO_ROOT)


@app.get(
    "/api/config/surface/node/{config_id}",
    response_model=ConfigSurfaceNodeDetailResponse,
)
def config_surface_node_detail(config_id: str):
    payload = resolve_config_authority_node(config_id=config_id, repo_root=REPO_ROOT)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Config authority row '{config_id}' not found")
    return payload


@app.get(
    "/api/config/surface/effective/{config_id}",
    response_model=ConfigSurfaceEffectiveResponse,
)
def config_surface_effective(config_id: str):
    payload = resolve_config_authority_effective(config_id=config_id, repo_root=REPO_ROOT)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Config authority row '{config_id}' not found")
    return payload


@app.get("/api/config/surface/diagnostics", response_model=ConfigSurfaceDiagnosticsResponse)
def config_surface_diagnostics():
    return config_authority_diagnostics(repo_root=REPO_ROOT)


@app.post("/api/config/surface/rebuild", response_model=ConfigSurfaceRebuildResponse)
def config_surface_rebuild():
    return write_config_authority_registry(repo_root=REPO_ROOT)


@app.get("/api/runs")
def get_runs() -> List[str]:
    """
    [ACTION]
    - Teleology: List known run IDs for UI browsing.
    - Mechanism: Resolves runs_dir from master_config paths (fallback to state/runs); returns directory names matching RUN_* sorted descending.
    - Reads: master_config.json; filesystem under runs_dir.
    - Writes: None.
    - Orders: Returns run IDs sorted reverse-lexicographic (most recent by naming convention).
    - Fails: Unexpected filesystem errors may propagate.
    - Guarantee: Returns a list of run_id strings (possibly empty).
    """
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    if not runs_dir.exists(): return []
    return sorted([p.name for p in runs_dir.iterdir() if p.is_dir() and p.name.startswith("RUN_")], reverse=True)

def _hologram_status_for_run(runs_dir: Path, run_id: str) -> RunHologramStatusSchema:
    """Shared helper: inspect holographic availability for a single run."""
    holo_path = runs_dir / run_id / "holographic" / "run_hologram.json"
    if not holo_path.exists():
        return RunHologramStatusSchema(run_id=run_id, exists=False)
    try:
        with open(holo_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        meta = data.get("__meta", {})
        tool_dir = runs_dir / run_id / "holographic" / "tool_runs"
        tool_count = len(list(tool_dir.glob("*.json"))) if tool_dir.exists() else 0
        return RunHologramStatusSchema(
            run_id=run_id,
            exists=True,
            schema_version=meta.get("schema_version"),
            generated_at=meta.get("generated_at"),
            tool_file_count=tool_count,
        )
    except Exception:
        return RunHologramStatusSchema(run_id=run_id, exists=False)

def _is_supported_run_hologram(schema_version: Any) -> bool:
    """Accept run hologram schema versions with major >= 2."""
    if not isinstance(schema_version, str):
        return False
    try:
        major = int(schema_version.split(".", 1)[0])
        return major >= 2
    except Exception:
        return False

@app.get("/api/runs/latest")
def get_latest_run() -> LatestRunSchema:
    """
    [ACTION]
    - Teleology: Identify the most recent run for Control Room targeting.
    - Mechanism: Filters RUN_* directories by mtime descending; checks run_summary.json for completion and holographic dir for v2 availability.
    - Reads: Filesystem under runs_dir.
    - Writes: None.
    - Fails: HTTP 404 if no RUN_* directories exist.
    - Guarantee: Returns a single LatestRunSchema.
    """
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    if not runs_dir.exists():
        raise HTTPException(status_code=404, detail="No runs directory")
    # [FIX] Sort by name (encodes timestamp) instead of mtime
    # so builder writes don't reshuffle which run is "latest"
    run_dirs = sorted(
        [p for p in runs_dir.iterdir() if p.is_dir() and p.name.startswith("RUN_")],
        key=lambda p: p.name,
        reverse=True,
    )
    if not run_dirs:
        raise HTTPException(status_code=404, detail="No runs found")
    latest = run_dirs[0]
    run_id = latest.name
    # Completion: run_summary.json exists
    summary_path = latest / "run_summary.json"
    is_complete = summary_path.exists()
    timestamp = latest.stat().st_mtime
    if is_complete:
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)
            timestamp = summary.get("timestamp", timestamp)
        except Exception:
            pass
    # Run hologram compatibility check (major >= 2)
    holo_path = latest / "holographic" / "run_hologram.json"
    hologram_v2 = False
    if holo_path.exists():
        try:
            with open(holo_path, "r", encoding="utf-8") as f:
                meta = json.load(f).get("__meta", {})
            hologram_v2 = _is_supported_run_hologram(meta.get("schema_version"))
        except Exception:
            pass
    return LatestRunSchema(
        run_id=run_id,
        timestamp=timestamp,
        is_complete=is_complete,
        hologram_v2_exists=hologram_v2,
    )

@app.get("/api/run/{run_id}/holographic/status")
def get_run_holographic_status(run_id: str) -> RunHologramStatusSchema:
    """
    [ACTION]
    - Teleology: Report holographic availability and version for a specific run.
    - Reads: Filesystem under runs_dir/<run_id>/holographic/.
    - Guarantee: Returns RunHologramStatusSchema (never 404).
    """
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_id = _validate_run_id(run_id)
    _resolve_run_dir(runs_dir, safe_run_id)
    return _hologram_status_for_run(runs_dir, safe_run_id)

@app.get("/api/run/{run_id}/holographic/run")
def get_run_hologram(run_id: str):
    """
    [ACTION]
    - Teleology: Serve run_hologram.json for a given run, overlaying latest regrade truth when available.
    - Reads: Filesystem holographic/run_hologram.json.
    - Fails: HTTP 404 if not found.
    - When-needed: Open when a route or debugging session needs the exact HTTP entrypoint that reads and serves `run_hologram` JSON for a completed run, including regrade overlay logic.
    - Escalates-to: system/server/main.py::get_run_holographic_status; system/server/schemas.py
    """
    from datetime import datetime

    def _parse_iso_epoch(ts_raw: Any) -> Optional[float]:
        if not isinstance(ts_raw, str):
            return None
        ts = ts_raw.strip()
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except Exception:
            return None

    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_id = _validate_run_id(run_id)
    run_dir = _resolve_run_dir(runs_dir, safe_run_id)
    holo_path = run_dir / "holographic" / "run_hologram.json"
    if not holo_path.exists():
        raise HTTPException(status_code=404, detail="Run hologram not found")

    try:
        with open(holo_path, "r", encoding="utf-8") as f:
            run_hologram = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read run hologram: {e}")

    if not isinstance(run_hologram, dict):
        raise HTTPException(status_code=500, detail="Run hologram is not a JSON object")

    grade_overlay: Dict[str, Any] = {"applied": False}
    run_section = run_hologram.get("run")
    if not isinstance(run_section, dict):
        run_section = {}
        run_hologram["run"] = run_section

    regrade_path = run_dir / "regrade_summary.json"
    if regrade_path.exists():
        try:
            with open(regrade_path, "r", encoding="utf-8") as f:
                regrade = json.load(f)
            if isinstance(regrade, dict):
                latest_grade = regrade.get("grade")
                latest_reason = regrade.get("grade_reason")
                latest_original = regrade.get("original_grade")
                latest_regraded_at = regrade.get("regraded_at")

                if isinstance(latest_grade, str) and latest_grade.strip():
                    run_section["grade"] = latest_grade.strip()
                    grade_overlay["applied"] = True
                if isinstance(latest_reason, str) and latest_reason.strip():
                    run_section["grade_reason"] = latest_reason.strip()
                    grade_overlay["applied"] = True
                if isinstance(latest_original, str) and latest_original.strip():
                    run_section["original_grade"] = latest_original.strip()
                run_section["grade_source"] = "regraded"
                if isinstance(latest_regraded_at, str) and latest_regraded_at.strip():
                    run_section["regraded_at"] = latest_regraded_at.strip()
                    grade_overlay["regraded_at"] = latest_regraded_at.strip()

                    generated_at = None
                    meta = run_hologram.get("__meta")
                    if isinstance(meta, dict):
                        generated_at = meta.get("generated_at")
                    generated_epoch = _parse_iso_epoch(generated_at)
                    regraded_epoch = _parse_iso_epoch(latest_regraded_at)
                    if generated_epoch is not None and regraded_epoch is not None:
                        grade_overlay["was_stale_before_overlay"] = regraded_epoch > generated_epoch
        except Exception as e:
            grade_overlay["error"] = f"Failed to overlay regrade summary: {e}"

    meta_section = run_hologram.get("__meta")
    if not isinstance(meta_section, dict):
        meta_section = {}
        run_hologram["__meta"] = meta_section
    meta_section["grade_overlay"] = grade_overlay

    return run_hologram

@app.get("/api/run/{run_id}/holographic/tool/{node_id}")
def get_run_hologram_tool(run_id: str, node_id: str):
    """
    [ACTION]
    - Teleology: Serve a specific tool run file from the holographic output.
    - Reads: Filesystem holographic/tool_runs/<node_id>.json.
    - Forbid: node_id containing '..' or '/'.
    - Fails: HTTP 404 if not found.
    """
    if ".." in node_id or "/" in node_id or "\\" in node_id:
        raise HTTPException(status_code=400, detail="Invalid node_id")
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_id = _validate_run_id(run_id)
    run_dir = _resolve_run_dir(runs_dir, safe_run_id)
    tool_path = run_dir / "holographic" / "tool_runs" / f"{node_id}.json"
    if not tool_path.exists():
        raise HTTPException(status_code=404, detail="Tool run not found")
    return FileResponse(str(tool_path), media_type="application/json")

@app.get("/api/run/{run_id}/telemetry/{node_id}", response_model=ToolRunTelemetry)
def get_run_telemetry_node(run_id: str, node_id: str) -> ToolRunTelemetry:
    """
    [ACTION]
    - Teleology: Serve a strongly-typed, contract-tested view of a single tool-node execution.
    - Mechanism: Reads the tool sidecar from holographic/tool_runs/<node_id>.json; falls back to
      the raw artifact at artifacts/<node_id>.json; backfills any missing provenance/diagnostics
      fields so the ToolRunTelemetry schema always validates regardless of artifact age.
    - Reads: holographic/tool_runs/<node_id>.json (preferred) or artifacts/<node_id>.json (fallback).
    - Writes: None.
    - Forbid: node_id containing '..' or '/'.
    - Fails: HTTP 404 if neither sidecar nor artifact exists. HTTP 400 on bad ids.
    - Guarantee: Returns ToolRunTelemetry; legacy artifacts are backfilled with safe defaults.
    """
    if ".." in node_id or "/" in node_id or "\\" in node_id:
        raise HTTPException(status_code=400, detail="Invalid node_id")

    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_id = _validate_run_id(run_id)
    run_dir = _resolve_run_dir(runs_dir, safe_run_id)

    # Prefer the holographic sidecar (richer: includes provenance backfill done by builder)
    sidecar_path = run_dir / "holographic" / "tool_runs" / f"{node_id}.json"
    artifact_path = run_dir / "artifacts" / f"{node_id}.json"

    raw: Dict[str, Any] = {}
    if sidecar_path.exists():
        try:
            with open(sidecar_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read tool sidecar: {e}")
    elif artifact_path.exists():
        try:
            with open(artifact_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read artifact: {e}")
    else:
        raise HTTPException(status_code=404, detail=f"No telemetry found for node '{node_id}'")

    if not isinstance(raw, dict):
        raise HTTPException(status_code=500, detail="Telemetry payload is not a JSON object")

    # --- Build ToolMetadataSchema (backfill missing fields for legacy artifacts) ---
    raw_meta = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    diag_raw = raw_meta.get("diagnostics") if isinstance(raw_meta.get("diagnostics"), dict) else {}
    diagnostics = ToolDiagnosticsSchema(
        input_rows=int(diag_raw.get("input_rows", 0)),
        output_rows=int(diag_raw.get("output_rows", 0)),
        dropped_rows=int(diag_raw.get("dropped_rows", 0)),
        warnings=list(diag_raw.get("warnings", [])) if isinstance(diag_raw.get("warnings"), list) else [],
    )
    metadata = ToolMetadataSchema(
        tool=raw_meta.get("tool") or raw.get("node_id") or node_id,
        status=raw_meta.get("status") or raw.get("status") or "unknown",
        items_count=raw_meta.get("items_count"),
        timestamp=raw_meta.get("timestamp"),
        timestamp_iso=raw_meta.get("timestamp_iso"),
        timestamp_epoch_s=raw_meta.get("timestamp_epoch_s"),
        schema_version=raw_meta.get("schema_version"),
        data_schema_version=raw_meta.get("data_schema_version"),
        config_ref=raw_meta.get("config_ref"),
        merged_hash=raw_meta.get("merged_hash"),
        override_keys=list(raw_meta.get("override_keys", [])) if isinstance(raw_meta.get("override_keys"), list) else [],
        diagnostics=diagnostics,
    )

    # --- Build ProvenanceView (from metadata or top-level provenance field) ---
    raw_prov = raw.get("provenance") if isinstance(raw.get("provenance"), dict) else {}
    provenance = ProvenanceView(
        config_ref=raw_meta.get("config_ref") or raw_prov.get("config_ref"),
        merged_hash=raw_meta.get("merged_hash") or raw_prov.get("merged_hash"),
        override_keys=metadata.override_keys or raw_prov.get("override_keys"),
        inline_overrides_preview=raw_prov.get("inline_overrides_preview"),
        preview_truncated=bool(raw_prov.get("preview_truncated", False)),
    )

    return ToolRunTelemetry(
        run_id=safe_run_id,
        node_id=node_id,
        status=raw.get("status") or raw_meta.get("status") or "unknown",
        metadata=metadata,
        provenance=provenance,
        data=raw.get("data") if isinstance(raw.get("data"), dict) else None,
    )


@app.post("/api/runs/holographic/batch-status")
def get_holographic_batch_status(req: RunHologramBatchStatusRequest) -> List[RunHologramStatusSchema]:
    """
    [ACTION]
    - Teleology: Batch holographic status check to avoid N+1 requests from the History page.
    - Reads: Filesystem under runs_dir for each requested run_id.
    - Guarantee: Returns one RunHologramStatusSchema per requested run_id.
    """
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_ids = [_validate_run_id(rid) for rid in req.run_ids]
    return [_hologram_status_for_run(runs_dir, rid) for rid in safe_run_ids]

# ── Regrade Endpoints ────────────────────────────────────────────────────────

def _regrade_single_run(runs_dir: Path, run_id: str) -> RegradeResult:
    """
    [ACTION]
    - Teleology: Recompute run grade using current grading policy and persist as regrade_summary.json.
    - Mechanism: Reads graph_snapshot.json for node types, checks artifact sizes with 5KB rule for tool nodes only.
    - Reads: run_summary.json, graph_snapshot.json, artifact files.
    - Writes: regrade_summary.json (preserves original run_summary.json).
    - Fails: Raises HTTPException if run directory or required files don't exist.
    """
    safe_run_id = _validate_run_id(run_id)
    run_dir = _resolve_run_dir(runs_dir, safe_run_id)
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Run not found: {safe_run_id}")

    # Read original grade
    summary_path = run_dir / "run_summary.json"
    original_grade = "amber"
    node_outcomes: Dict[str, str] = {}
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text())
            original_grade = summary.get("grade", "amber")
            raw_outcomes = summary.get("node_outcomes", {})
            if isinstance(raw_outcomes, dict):
                node_outcomes = raw_outcomes
        except Exception:
            pass

    # Read node types from graph_snapshot
    snap_path = run_dir / "artifacts" / "graph_snapshot.json"
    tool_node_ids: set = set()
    all_node_ids: set = set()
    snapshot_scope_reason: Optional[str] = None
    snapshot_universe_usable = False
    if snap_path.exists():
        try:
            snap = json.loads(snap_path.read_text())
            for n in snap.get("nodes", []):
                nid = n.get("id", "")
                if not nid:
                    continue
                all_node_ids.add(nid)
                if str(n.get("type", "")).lower() == "tool":
                    tool_node_ids.add(nid)
            if all_node_ids:
                snapshot_universe_usable = True
            else:
                snapshot_scope_reason = "Forensic snapshot empty; completeness unverifiable"
        except Exception:
            snapshot_scope_reason = "Forensic snapshot unreadable; completeness unverifiable"
    else:
        snapshot_scope_reason = "Forensic snapshot missing; completeness unverifiable"

    # Apply current grading policy
    grade = "green"
    grade_reason = "All checks passed"
    art_dir = run_dir / "artifacts"

    # Check for failed nodes
    failure_vocab = {"failure", "failed", "error", "exception"}
    has_failure = any(str(s).strip().lower() in failure_vocab for s in node_outcomes.values())
    if has_failure:
        grade = "red"
        grade_reason = "Run contains failed nodes"
    else:
        # Deterministic contract audit hard-fails are first-class grading inputs.
        audit_path = art_dir / "lab_contract_audit.json"
        if audit_path.exists():
            try:
                audit_env = json.loads(audit_path.read_text(encoding="utf-8"))
                audit_data = audit_env.get("data", {}) if isinstance(audit_env, dict) else {}
                hard_fails = audit_data.get("hard_fails", []) if isinstance(audit_data, dict) else []
                if isinstance(hard_fails, list) and hard_fails:
                    grade = "red"
                    grade_reason = f"Deterministic contract audit hard fail: {hard_fails[0]}"
            except Exception:
                pass

        # Integrity override stays authoritative in regrade too.
        if grade != "red":
            integrity_path = art_dir / "lab_integrity.json"
            if integrity_path.exists():
                try:
                    integrity_env = json.loads(integrity_path.read_text(encoding="utf-8"))
                    integrity_data = integrity_env.get("data") if isinstance(integrity_env, dict) else integrity_env
                    text = integrity_data if isinstance(integrity_data, str) else ""
                    if "GRADE_OVERRIDE: RED" in text[:200]:
                        grade = "red"
                        grade_reason = "Integrity oracle override: RED"
                except Exception:
                    pass

    if grade != "red":
        # Evaluate the full intended universe whenever graph snapshot exists.
        execution_nodes = set(all_node_ids) if snapshot_universe_usable else set(node_outcomes.keys())
        execution_nodes.update(node_outcomes.keys())

        missing_tool_nodes: List[str] = []
        missing_reasoning_nodes: List[str] = []
        undersized_tool_nodes: List[str] = []

        # Check artifacts (sorted for determinism)
        for nid in sorted(execution_nodes):
            artifact_path = art_dir / f"{nid}.json"
            if nid == "graph_snapshot" or nid == "seed_manifest" or nid == "runtime_context" or nid == "run_summary":
                continue
            if not artifact_path.exists():
                if nid in tool_node_ids:
                    missing_tool_nodes.append(nid)
                else:
                    missing_reasoning_nodes.append(nid)
                continue
            # 5KB check only for tool nodes
            if nid in tool_node_ids and artifact_path.stat().st_size < 5120:
                undersized_tool_nodes.append(nid)

        def format_missing(label: str, node_ids: List[str]) -> str:
            """
            [ACTION]
            - Teleology: Format a missing-artifact summary string with count and up to 3 sample ids.
            - Guarantee: Returns a human-readable label string.
            - Fails: None.
            """
            sample = ", ".join(node_ids[:3])
            more = len(node_ids) - 3
            suffix = f" (+{more} more)" if more > 0 else ""
            return f"{label} ({len(node_ids)}): {sample}{suffix}"

        if missing_tool_nodes:
            grade = "red"
            grade_reason = format_missing("Missing tool artifacts", missing_tool_nodes)
        elif undersized_tool_nodes:
            grade = "red"
            grade_reason = format_missing("Tool artifacts too small (<5KB)", undersized_tool_nodes)
        elif missing_reasoning_nodes:
            grade = "amber"
            grade_reason = format_missing("Missing reasoning artifacts", missing_reasoning_nodes)
        elif snapshot_scope_reason:
            grade = "amber"
            grade_reason = snapshot_scope_reason

    quality_override = quality_grade_override(
        collect_artifact_qualities(art_dir, sorted(tool_node_ids))
    )
    if quality_override is not None:
        override_grade, override_reason = quality_override
        if override_grade == "red" or grade == "green":
            grade = override_grade
            grade_reason = override_reason

    # Write regrade_summary.json (preserve original)
    from datetime import datetime, timezone
    regraded_at = datetime.now(timezone.utc).isoformat()
    regrade_data = {
        "run_id": safe_run_id,
        "grade": grade,
        "grade_reason": grade_reason,
        "original_grade": original_grade,
        "regraded_at": regraded_at,
    }
    regrade_path = run_dir / "regrade_summary.json"
    with open(regrade_path, "w", encoding="utf-8") as f:
        json.dump(regrade_data, f, indent=2)

    return RegradeResult(
        run_id=safe_run_id,
        grade=grade,
        grade_reason=grade_reason,
        original_grade=original_grade,
        regraded_at=regraded_at,
    )

@app.post("/api/run/{run_id}/regrade")
def regrade_run(run_id: str) -> RegradeResult:
    """
    [ACTION]
    - Teleology: Recompute a single run's grade under the current grading policy.
    - Reads: Run artifacts and graph_snapshot.
    - Writes: regrade_summary.json in run directory.
    - Fails: HTTP 404 if run not found.
    """
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_id = _validate_run_id(run_id)
    return _regrade_single_run(runs_dir, safe_run_id)

@app.post("/api/runs/regrade-batch")
def regrade_batch(req: RegradeBatchRequest) -> List[RegradeResult]:
    """
    [ACTION]
    - Teleology: Batch-regrade multiple runs under the current grading policy.
    - Reads: Run artifacts and graph snapshots for each run_id.
    - Writes: regrade_summary.json in each run directory.
    - Fails: Individual failures are caught and returned as amber with error reason.
    """
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_ids = [_validate_run_id(rid) for rid in req.run_ids]
    results = []
    for rid in safe_run_ids:
        try:
            results.append(_regrade_single_run(runs_dir, rid))
        except HTTPException:
            results.append(RegradeResult(
                run_id=rid, grade="amber",
                grade_reason="Regrade failed: run not found",
                original_grade="unknown", regraded_at="",
            ))
    return results

@app.get("/api/run/log")
def get_run_log(run_id: str, limit: int = 200):
    """
    [ACTION]
    - Teleology: Serve a recent snapshot of the server-side run log for a given run.
    - Mechanism: Delegates to session_manager.get_log_snapshot(run_id, limit).
    - Reads: SessionManager run log storage.
    - Writes: None.
    - Fails: Unexpected errors may propagate.
    - Guarantee: Returns a log snapshot payload as produced by SessionManager.
    """
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_id = _validate_run_id(run_id)
    _resolve_run_dir(runs_dir, safe_run_id)
    return session_manager.get_log_snapshot(safe_run_id, limit=limit)

@app.get("/api/run/{run_id}/engine_log")
def get_engine_log_snapshot(run_id: str, limit: int = 1000):
    """
    [ACTION]
    - Teleology: Serve a structured forensic snapshot of engine.log with truncation metadata.
    - Mechanism: Validates run_id, tails up to `limit` lines, and returns total line count.
    """
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_id = _validate_run_id(run_id)
    _resolve_run_dir(runs_dir, safe_run_id)

    safe_limit = max(1, min(int(limit), 10000))
    lines, total_lines = session_manager.get_log_snapshot_with_meta(safe_run_id, limit=safe_limit)
    return {
        "lines": lines,
        "truncated": total_lines > len(lines),
        "limit": safe_limit,
        "total_lines": total_lines,
    }

@app.get("/api/run/{run_id}/engine_log/download")
def download_engine_log(run_id: str):
    """
    [ACTION]
    - Teleology: Download the full raw engine.log for offline forensics.
    """
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_id = _validate_run_id(run_id)
    run_dir = _resolve_run_dir(runs_dir, safe_run_id)
    log_path = run_dir / "engine.log"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="engine.log not found")
    return FileResponse(
        str(log_path),
        media_type="text/plain",
        filename=f"{safe_run_id}_engine.log",
    )

@app.get("/api/run/status")
def get_run_status(run_id: Optional[str] = None):
    """
    [ACTION]
    - Teleology: Return the current active-run status (and optionally a specific run_id status view).
    - Mechanism: Delegates to session_manager.get_active_run_status().
    - Reads: SessionManager in-memory state.
    - Writes: None.
    - Fails: Unexpected errors may propagate.
    - Guarantee: Returns a JSON-serializable status dict representing the active run state.
    """
    return session_manager.get_active_run_status()

@app.get("/api/run/telemetry")
def get_run_telemetry(run_id: str, since_seq: int = -1):
    """
    [ACTION]
    - Teleology: Serve telemetry events for a run since a given sequence number.
    - Mechanism: Delegates to session_manager.replay_telemetry(run_id, since_seq).
    - Reads: SessionManager telemetry storage.
    - Writes: None.
    - Fails: Unexpected errors may propagate.
    - Guarantee: Returns a telemetry replay payload for the requested run.
    """
    return session_manager.replay_telemetry(run_id, since_seq)

@app.get("/api/graph")
def get_graph(run_id: Optional[str] = None):
    """
    [ACTION]
    - Teleology: Serve the current physics graph view for the repo.
    - Mechanism: Delegates to compile_physics_graph(REPO_ROOT).
    - Reads: Codex graph inputs as required by the compiler.
    - Writes: None.
    - Fails: Unexpected exceptions -> HTTP 500 (via FastAPI default handling if not caught).
    - Guarantee: Returns a graph representation as produced by the compiler.
    """
    return compile_physics_graph(REPO_ROOT)

@app.get("/api/run/{run_id}/artifacts")
def list_artifacts(run_id: str):
    """
    [ACTION]
    - Teleology: List artifacts for a run for UI selection.
    - Mechanism: Resolves runs_dir; scans runs/<run_id>/artifacts/*.json; skips seed_manifest.json; returns basic metadata sorted by timestamp.
    - Reads: Filesystem under state/runs/<run_id>/artifacts; JSON artifact files.
    - Writes: None.
    - Orders: Results sorted by artifact timestamp descending.
    - Fails: Per-file JSON/read errors are skipped; unexpected directory errors may propagate.
    - Guarantee: Returns a list of artifact metadata dicts (possibly empty).
    """
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_id = _validate_run_id(run_id)
    run_dir = _resolve_run_dir(runs_dir, safe_run_id)
    artifacts_dir = run_dir / "artifacts"
    if not artifacts_dir.exists(): return []

    results = []
    for path in artifacts_dir.glob("*.json"):
        if path.name == "seed_manifest.json": continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            results.append({
                "name": path.name,
                "size": path.stat().st_size,
                "id": data.get("id", path.stem),
                "type": "artifact",
                "status": data.get("status", "unknown"),
                "timestamp": data.get("timestamp", 0),
            })
        except Exception: continue
    return sorted(results, key=lambda x: x.get("timestamp", 0), reverse=True)

@app.get("/api/run/{run_id}/artifacts/{filename}")
def get_artifact_content(run_id: str, filename: str):
    """
    [ACTION]
    - Teleology: Serve the raw artifact file text content for a run.
    - Mechanism: Resolves runs_dir; validates run_id + filename; reads runs/<run_id>/artifacts/<filename>.
    - Reads: Filesystem artifact file.
    - Writes: None.
    - Forbid: Filenames containing '..' or '/' -> HTTP 400.
    - Fails: Missing file -> HTTP 404; read failures -> HTTP 500.
    - Guarantee: On success, returns `{\"content\": <file_text>}`.
    """
    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_id = _validate_run_id(run_id)
    run_dir = _resolve_run_dir(runs_dir, safe_run_id)

    # Security: Prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = (run_dir / "artifacts" / filename).resolve()
    try:
        file_path.relative_to((run_dir / "artifacts").resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read artifact: {e}")
    return {"content": content}

@app.post("/api/preflight", response_model=BridgePreflightResponse)
def trigger_preflight(
    force: bool = Query(
        default=False,
        description="Retained for compatibility; full preflight already bypasses the shared cache.",
    )
):
    """
    [ACTION]
    - Teleology: Run the Bridge full preflight script and return captured logs. Full preflight
      always executes fresh so the browser surface is revalidated on every call.
    - Mechanism: Spawn `run_bridge_preflight.py --force` and return its captured stdout/stderr
      plus current bridge diagnostics. The query param is retained for backward compatibility,
      but full preflight is already forced regardless.
    - Reads: run_bridge_preflight.py.
    - Writes: Preflight subprocess side-effects as defined by the script.
    - Fails: Subprocess spawn/exec failure -> HTTP 500.
    - Guarantee: Returns full preflight logs plus a structured bridge diagnostics packet.
    """
    try:
        _ = force  # Back-compat query flag; full preflight is always forced now.
        command = [sys.executable, "run_bridge_preflight.py", "--force"]

        result = subprocess.run(
            command,
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        status_code = "success" if result.returncode == 0 else "error"
        diagnostics = _bridge_diagnostics_payload(limit=6)
        return BridgePreflightResponse(
            status=status_code,
            command=" ".join(command),
            returncode=result.returncode,
            logs=f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
            diagnostics=BridgeDiagnosticsResponse(**diagnostics),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bridge/status", response_model=BridgeDiagnosticsResponse)
def get_bridge_status(provider: Optional[str] = Query(default=None), limit: int = Query(default=6, ge=1, le=12)):
    """
    [ACTION]
    - Teleology: Expose structured bridge diagnostics for operator and frontend observability surfaces.
    - Mechanism: Reads current master_config, collects bridge diagnostics, and returns one normalized packet.
    - Reads: master_config.json and live bridge/browser tab state.
    - Writes: None.
    - Guarantee: Returns additive diagnostics even when CDP is offline.
    """
    try:
        payload = _bridge_diagnostics_payload(provider, limit=limit)
        return BridgeDiagnosticsResponse(**payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/agent-observability/status")
def get_agent_observability_status():
    """
    [ACTION]
    - Teleology: Expose source health, active sessions, queue drops, and trace counts for the Agent lens.
    - Guarantee: Returns the append-only trace store's current projection without mutating providers.
    """
    try:
        return agent_trace_store.status()
    except Exception as exc:
        logger.exception("Agent observability status failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/agent-observability/events")
def get_agent_observability_events(
    request: Request,
    since_seq: int = Query(default=0, ge=0),
    session_id: Optional[str] = Query(default=None),
    source_runtime: Optional[str] = Query(default=None),
    canonical_type: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
):
    """
    [ACTION]
    - Teleology: Replay typed agent events for historical browse or reconnect hydration.
    - Guarantee: Filtered by monotonic sequence and stable trace fields; raw payloads remain attached.
    """
    try:
        return _agent_observability_events_response(
            since_seq=since_seq,
            session_id=session_id,
            source_runtime=source_runtime,
            canonical_type=canonical_type,
            limit=limit,
            request_headers=request.headers,
        )
    except Exception as exc:
        logger.exception("Agent observability replay failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/agent-observability/hook")
def post_agent_observability_hook(payload: Dict[str, Any] = Body(default_factory=dict)):
    """
    [ACTION]
    - Teleology: Receive Claude Code hook payloads from the local runtime and materialize them into the trace plane.
    - Guarantee: Best-effort ingestion only; provider payload is retained as evidence.
    """
    try:
        action = str(payload.get("hook_event_name") or payload.get("action") or "ClaudeHook")
        return agent_trace_store.ingest_claude_hook(action, payload)
    except Exception as exc:
        logger.exception("Agent observability hook ingestion failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/agent-observability/event")
def post_agent_observability_event(payload: Dict[str, Any] = Body(default_factory=dict)):
    """
    [ACTION]
    - Teleology: Let backend processors append normalized events without importing server globals.
    - Guarantee: Requires canonical/source fields and otherwise preserves payload as evidence.
    """
    try:
        source_runtime = str(payload.get("source_runtime") or "").strip()
        canonical_type = str(payload.get("canonical_type") or "").strip()
        if not source_runtime or not canonical_type:
            raise HTTPException(status_code=422, detail="source_runtime and canonical_type are required")
        return agent_trace_store.emit(
            source_runtime=source_runtime,
            source_event_name=str(payload.get("source_event_name") or canonical_type),
            canonical_type=canonical_type,
            payload=payload.get("payload") if isinstance(payload.get("payload"), dict) else payload,
            session_id=payload.get("session_id"),
            trace_id=payload.get("trace_id"),
            parent_id=payload.get("parent_id"),
            turn_id=payload.get("turn_id"),
            tool_use_id=payload.get("tool_use_id"),
            subagent_id=payload.get("subagent_id"),
            cwd=payload.get("cwd"),
            transcript_path=payload.get("transcript_path"),
            artifact_refs=payload.get("artifact_refs") if isinstance(payload.get("artifact_refs"), list) else None,
            occurred_at=payload.get("occurred_at"),
            summary=payload.get("summary"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Agent observability event ingestion failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/agent-observability/codex/snapshot")
def post_agent_observability_codex_snapshot(
    port: int = Query(default=9224, ge=1, le=65535),
    connect: bool = Query(default=False),
):
    """
    [ACTION]
    - Teleology: Sample the Codex desktop app as an Electron/CDP target, not as a CLI replacement.
    - Guarantee: Defaults to read-only probe mode and emits one snapshot event into the trace store.
    """
    try:
        snapshot = snapshot_codex_app(port=port, connect=connect)
        event = agent_trace_store.ingest_codex_app_snapshot(snapshot)
        return {"event": event, "snapshot": snapshot}
    except Exception as exc:
        agent_trace_store.emit_gap(
            source_runtime="codex_app",
            reason="codex_app_snapshot_failed",
            payload={"port": port, "connect": connect, "error": str(exc)},
        )
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/agent-observability/codex/replay")
def post_agent_observability_codex_replay(
    file_limit: int = Query(default=5, ge=1, le=50),
    tail_lines: int = Query(default=40, ge=1, le=500),
):
    """
    [ACTION]
    - Teleology: Reconcile recent Codex app rollout JSONL into the canonical trace plane.
    - Guarantee: Reads the app's authoritative rollout files; does not launch or drive the CLI.
    """
    try:
        return ingest_recent_codex_rollouts(
            agent_trace_store,
            file_limit=file_limit,
            tail_lines=tail_lines,
        )
    except Exception as exc:
        logger.exception("Agent observability Codex replay failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/agent-observability/claude/replay")
def post_agent_observability_claude_replay(
    file_limit: int = Query(default=5, ge=1, le=50),
    tail_lines: int = Query(default=40, ge=1, le=500),
):
    """
    [ACTION]
    - Teleology: Reconcile recent Claude transcript JSONL into the canonical trace plane.
    - Guarantee: Replay appends evidence and correction context; it never overwrites live hook events.
    """
    try:
        return ingest_recent_claude_transcripts(
            agent_trace_store,
            file_limit=file_limit,
            tail_lines=tail_lines,
        )
    except Exception as exc:
        logger.exception("Agent observability Claude replay failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/agent-observability/mission-status")
def get_agent_observability_mission_status(
    request: Request,
    history_limit: int = Query(default=200, ge=10, le=2000),
):
    """
    [ACTION]
    - Teleology: Project the live agent observability plane into a typed
      mission-control reducer with health, missions, and telemetry-quality
      classification (auth_failure_loop demotion, stale source warnings,
      golden-signal rates) while preserving raw drilldown into the canonical
      JSONL trace.
    - Guarantee: Read-only. Composes ``AgentTraceStore`` plus the work-ledger
      runtime status plus pure attribution and classification builders. The
      append-only trace is never mutated by this surface.
    """
    try:
        return _agent_observability_mission_status_response(
            history_limit=history_limit,
            request_headers=request.headers,
        )
    except Exception as exc:
        logger.exception("Agent observability mission-status failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/agent-observability/host-pressure")
def get_agent_observability_host_pressure(
    request: Request,
    window_s: int = Query(default=900, ge=30, le=7200),
    requested_workload_class: Optional[str] = Query(default=None),
    operator_override: bool = Query(default=False),
):
    """
    [ACTION]
    - Teleology: Correlate recent agent progress with low-overhead host pressure
      so parallel Codex/Claude work is judged by useful progress per pressure.
    - Guarantee: Read-only. Emits bounded counts/classes and governor advice;
      deep profilers remain trigger-only outside this endpoint.
    """
    try:
        return _load_agent_observability_host_pressure_packet(
            request_path=str(request.url.path),
            window_s=window_s,
            requested_workload_class=requested_workload_class,
            operator_override=operator_override,
        )
    except Exception as exc:
        logger.exception("Agent observability host-pressure failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/agent-observability/session-yield-control")
def get_agent_observability_session_yield_control(
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    [ACTION]
    - Teleology: Surface resident-pressure yield requests as a closeable control loop:
      pending request, owner result, applied actuator, and recovery readiness.
    - Guarantee: Read-only. This endpoint never signals processes or terminates sessions.
    """
    try:
        return work_admission.build_session_yield_control_surface(
            request_events=_read_jsonl_tail_if_exists(SESSION_YIELD_REQUESTS_PATH, limit=limit),
            result_events=_read_jsonl_tail_if_exists(SESSION_YIELD_RESULTS_PATH, limit=limit),
            background_loop_downshift=_read_json_if_exists(BACKGROUND_DOWNSHIFT_STATE_PATH),
            limit=limit,
        )
    except Exception as exc:
        logger.exception("Agent observability session-yield-control failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/agent-observability/session-message-inbox")
def get_agent_observability_session_message_inbox(
    session_id: str = Query(..., min_length=1, max_length=240),
    limit: int = Query(default=12, ge=1, le=100),
    scan_limit: int = Query(default=400, ge=1, le=2000),
    include_sent: bool = Query(default=False),
):
    """
    [ACTION]
    - Teleology: Surface the disk-backed Work Ledger session-message bus as a
      session-local inbox, including pending acknowledgements and paste-ready
      reply commands for Codex-to-Codex and Claude-visible coordination.
    - Guarantee: Read-only. This endpoint never interrupts, signals, or
      terminates another agent process.
    """
    try:
        return build_session_message_inbox_surface(
            session_id=session_id,
            message_events=_read_jsonl_tail_if_exists(SESSION_MESSAGES_PATH, limit=scan_limit),
            limit=limit,
            include_sent=include_sent,
        )
    except Exception as exc:
        logger.exception("Agent observability session-message-inbox failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/agent-observability/animation")
def get_agent_observability_animation(
    since_seq: int = Query(default=0, ge=0),
    session_id: Optional[str] = Query(default=None),
    source_runtime: Optional[str] = Query(default=None),
    limit: int = Query(default=_AGENT_OBSERVABILITY_ANIMATION_DEFAULT_LIMIT, ge=1, le=2000),
    window_ms: int = Query(default=900000, ge=1000, le=86400000),
    include_infrastructure: bool = Query(default=False),
):
    """
    [ACTION]
    - Teleology: Shape the live trace plane into animation-ready actors,
      tracks, pulses, nodes, edges, attention items, and data-quality
      receipts for the Agent Trace frontend.
    - Guarantee: Read-only projection. Every graphic primitive points back
      to canonical event ids/sequences or status rows; hidden reasoning is
      not inferred.
    """
    try:
        try:
            work_ledger_status = _load_agent_observability_work_ledger_status(REPO_ROOT)
        except Exception:  # noqa: BLE001 - animation projection must degrade
            logger.exception("animation work-ledger load failed")
            work_ledger_status = {}
        mission_status = build_agent_mission_status(
            store=agent_trace_store,
            work_ledger_status=work_ledger_status,
            repo_root=REPO_ROOT,
            history_limit=limit,
        )
        return build_agent_observability_animation_scene(
            events=agent_trace_store.replay(
                since_seq=since_seq,
                session_id=session_id,
                source_runtime=source_runtime,
                limit=limit,
            ),
            status=agent_trace_store.status(),
            mission_status=mission_status,
            window_ms=window_ms,
            include_infrastructure=include_infrastructure,
            session_id=session_id,
            source_runtime=source_runtime,
            since_seq=since_seq,
            limit=limit,
        )
    except Exception as exc:
        logger.exception("Agent observability animation projection failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/agent-observability/animation/delta")
def get_agent_observability_animation_delta(
    request: Request,
    since_seq: int = Query(default=0, ge=0),
    session_id: Optional[str] = Query(default=None),
    source_runtime: Optional[str] = Query(default=None),
    limit: int = Query(default=300, ge=1, le=1000),
    window_ms: int = Query(default=900000, ge=1000, le=86400000),
    include_infrastructure: bool = Query(default=False),
    max_ops: int = Query(default=700, ge=50, le=2000),
):
    """
    [ACTION]
    - Teleology: Return a bounded replay delta over the animation projection
      so high-frequency live views can append/upsert real trace-driven
      graphics without rehydrating the whole scene.
    - Guarantee: Read-only. Deltas carry cursor, snapshot-required, channel,
      coalescing, and backpressure metadata; every operation is tied back to
      canonical trace ids/sequences where available.
    """
    try:
        return _agent_observability_animation_delta_response(
            since_seq=since_seq,
            session_id=session_id,
            source_runtime=source_runtime,
            limit=limit,
            window_ms=window_ms,
            include_infrastructure=include_infrastructure,
            max_ops=max_ops,
            request_headers=request.headers,
        )
    except Exception as exc:
        logger.exception("Agent observability animation delta failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/agent-observability/claude/live-sessions")
def get_agent_observability_claude_live_sessions():
    """
    [ACTION]
    - Teleology: Expose the Claude Code app pid/session sidecar discovery layer for debugging the live plane.
    - Guarantee: Read-only; returns only running PIDs from ~/.claude/sessions/*.json.
    """
    try:
        return {"sessions": discover_claude_code_app_sessions()}
    except Exception as exc:
        logger.exception("Agent observability Claude live-session discovery failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/agent-trace/mission-index")
def get_agent_trace_mission_index():
    """
    [ACTION]
    - Teleology: Expose the macOS Agent Trace Structurer's ``mission_index.json``
      (and the sibling ``variant_artifact_index.json`` keyed by session_id) so the
      Zenith Agent Trace Workbench can render the same dense mission rows the
      native HUD shows, without round-tripping through the Swift bridge.
    - Guarantee: Read-only. Reads ``~/Library/Application Support/Agent Trace
      Structurer/{mission_index,variant_artifact_index}.json`` and returns
      ``{available, source_path, generated_at, row_count, active_count,
      inactive_count, hidden_old_count, rows[], active_rows[], inactive_rows[],
      variant_artifact_index}``. When the support dir is missing (e.g. native
      app never run), returns ``available=False`` plus a hint, never 500.
    """
    return _agent_trace_mission_index_response()


_SESSION_PROJECTION_CACHE: Dict[str, Dict[str, Any]] = {}


def _find_agent_trace_session_row(
    session_id: str,
    index_blob: Optional[Mapping[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    if index_blob is None:
        index_blob = _load_agent_trace_mission_index_bundle()
    if not index_blob.get("available"):
        return None
    rows = index_blob.get("rows", []) or []
    for row in rows:
        if isinstance(row, Mapping) and row.get("session_id") == session_id:
            return dict(row)
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        sid = row.get("session_id") or ""
        if sid.startswith(session_id) or session_id.startswith(sid):
            return dict(row)
    return None


def _clear_agent_trace_session_projection_cache_for_tests() -> None:
    _SESSION_PROJECTION_CACHE.clear()


@app.get("/api/agent-trace/session-projection")
def get_agent_trace_session_projection(session_id: str = Query(..., min_length=4)):
    """
    [ACTION]
    - Teleology: Provide a compact multi-turn projection for a session by
      subprocess-calling ``cli_prompt_trace.py --session <id> --list``. This is
      the second fallback in the lens cascade: the in-memory event store ages
      out, mission_index has only latest_completed_turn + active_turn, but
      ``--list`` walks the whole session_file and emits every turn.
    - Guarantee: Read-only. Resolves session_id -> row via mission_index.json,
      then shells out to the existing CLI parser. Cached by (path, mtime).
      Returns ``available=false`` when session_file is missing or the CLI fails.
    """
    mission_index = _load_agent_trace_mission_index_bundle()
    if not mission_index.get("available"):
        return {"available": False, "session_id": session_id, "reason": "mission_index_not_present"}
    row = _find_agent_trace_session_row(session_id, mission_index)
    if row is None:
        return {"available": False, "session_id": session_id, "reason": "session_not_in_mission_index"}
    session_file = row.get("session_file")
    if not session_file or not Path(session_file).exists():
        return {"available": False, "session_id": session_id, "reason": "session_file_missing"}
    path = Path(session_file)
    try:
        stat = path.stat()
    except OSError as exc:
        return {"available": False, "session_id": session_id, "reason": f"stat_failed: {exc}"}
    cache_key = f"{path}:{stat.st_mtime_ns}:{stat.st_size}"
    cached = _SESSION_PROJECTION_CACHE.get(session_id)
    if cached and cached.get("__cache_key") == cache_key:
        return {k: v for k, v in cached.items() if k != "__cache_key"}
    cli_path = REPO_ROOT / "tools" / "meta" / "observability" / "cli_prompt_trace.py"
    if not cli_path.exists():
        return {"available": False, "session_id": session_id, "reason": "cli_prompt_trace_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(cli_path), "--session", session_id, "--list"],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"available": False, "session_id": session_id, "reason": "cli_timeout"}
    except Exception as exc:
        return {"available": False, "session_id": session_id, "reason": f"cli_failed: {exc}"}
    output = (proc.stderr or "") + "\n" + (proc.stdout or "")
    turn_pattern = re.compile(
        r"^\s*(\d+)\.\s+\[([^\]]+)\]\s+(\w+)(?:\s+tools=(\d+))?(?:\s+err=(\d+))?\s*(.*)$",
    )
    turns: List[Dict[str, Any]] = []
    for line in output.splitlines():
        m = turn_pattern.match(line)
        if not m:
            continue
        status = m.group(3).strip().lower()
        turns.append({
            "turn_index": int(m.group(1)),
            "started_at": m.group(2).strip(),
            "completed_at": None,
            "status": status,
            "tool_count": int(m.group(4)) if m.group(4) else 0,
            "error_count": int(m.group(5)) if m.group(5) else 0,
            "prompt_preview": (m.group(6) or "").strip()[:240],
            "is_complete": status == "complete",
        })
    payload = {
        "available": bool(turns),
        "session_id": session_id,
        "provider": row.get("provider"),
        "turns": turns,
        "source": {
            "path": session_file,
            "size_bytes": stat.st_size,
            "mtime_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        },
        "reason": None if turns else "cli_returned_no_turns",
    }
    _SESSION_PROJECTION_CACHE[session_id] = {**payload, "__cache_key": cache_key}
    return payload


@app.post("/api/agent-observability/poll")
def post_agent_observability_poll():
    """
    [ACTION]
    - Teleology: Force one low-cost sampler tick so the UI/operator can prove discovery without waiting for the interval.
    - Guarantee: Does not launch or drive provider apps.
    """
    try:
        agent_observability_sampler.poll_once()
        return agent_trace_store.status()
    except Exception as exc:
        logger.exception("Agent observability forced poll failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.websocket("/ws/agent-observability")
async def agent_observability_ws(websocket: WebSocket):
    """
    [ACTION]
    - Teleology: Stream live AgentTrace events to the Station lens with history hydration on connect.
    - Guarantee: Sends bounded replay first, then live queue events through agent_observability_broadcaster().
    """
    await websocket.accept()
    agent_observability_websockets.add(websocket)
    try:
        for evt in agent_trace_store.replay(limit=500):
            await websocket.send_json(evt)
        while True:
            try: await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError: pass
    except (WebSocketDisconnect, Exception):
        agent_observability_websockets.discard(websocket)
    finally:
        agent_observability_websockets.discard(websocket)

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    """
    [ACTION]
    - Teleology: Maintain a WebSocket connection for telemetry broadcasting.
    - Mechanism: Accepts the socket; adds to connected_websockets; loops receiving with a timeout to keep the connection alive; removes socket on disconnect/error.
    - Reads: Incoming WebSocket frames (ignored except for keepalive).
    - Writes: Mutates connected_websockets; sends telemetry indirectly via broadcaster().
    - Locks: None (assumes event-loop serialized access to connected_websockets).
    - Fails: WebSocketDisconnect/Exception -> connection removed and handler exits.
    - Guarantee: While connected, the socket remains registered for broadcaster-driven event pushes.
    """
    await websocket.accept()
    connected_websockets.add(websocket)
    _record_telemetry_connect(websocket)
    disconnect_code: int | None = None
    disconnect_reason: str | None = None
    disconnect_error: str | None = None
    try:
        while True:
            try: await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError: pass
    except WebSocketDisconnect as exc:
        disconnect_code = getattr(exc, "code", None)
        disconnect_reason = getattr(exc, "reason", None)
    except Exception as exc:
        disconnect_error = f"{type(exc).__name__}: {exc}"
    finally:
        connected_websockets.discard(websocket)
        _record_telemetry_disconnect(
            websocket,
            code=disconnect_code,
            reason=disconnect_reason,
            error=disconnect_error,
        )

# --- INSPECTOR ENDPOINTS ---

_CODEX_TREE_CACHE_NAME = "codex_tree"
_CODEX_TREE_PREWARM_WAIT_S = 0.20


def _codex_tree_cache_key() -> str:
    return str(REPO_ROOT.resolve())


def _build_codex_tree_payload() -> Dict[str, Any]:
    tree, stats = inspector_service.scan_tree(include_compliance=False)
    return {"tree": tree, "stats": stats}


def _schedule_codex_tree_prewarm() -> None:
    swr_prewarm(
        _CODEX_TREE_CACHE_NAME,
        _codex_tree_cache_key(),
        _build_codex_tree_payload,
    )


def _warming_codex_tree_payload(reason: str) -> Dict[str, Any]:
    return {
        "tree": {
            "path": ".",
            "name": REPO_ROOT.name,
            "node_type": "dir",
            "status": "skip",
            "error_count": 0,
            "file_type": "",
            "children": [],
        },
        "stats": {
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "total_files": 0,
            "error_count": 0,
            "files_by_type": {},
            "status_counts": {"ok": 0, "warn": 0, "fail": 0, "skip": 0},
        },
    }


@app.get("/api/codex/tree", response_model=CodexTreeResponse)
def get_codex_tree():
    """
    [ACTION]
    - Teleology: Return the codex file tree with scan stats for inspector UI browsing.
    - Mechanism: SWR-cached wrapper over `inspector_service.scan_tree()`; a cold
      scan walks most of the repo (5s+), so every endpoint that hits this path
      would otherwise re-do the full filesystem walk.
    - Guarantee: Returns {tree, stats} structure conforming to CodexTreeResponse.
    """
    try:
        key = _codex_tree_cache_key()
        cached = swr_peek(_CODEX_TREE_CACHE_NAME, key)
        if isinstance(cached, dict):
            return cached
        _schedule_codex_tree_prewarm()
        if _CODEX_TREE_PREWARM_WAIT_S > 0:
            time.sleep(_CODEX_TREE_PREWARM_WAIT_S)
            cached = swr_peek(_CODEX_TREE_CACHE_NAME, key)
            if isinstance(cached, dict):
                return cached
        logger.info("Inspector tree returned warming shell (prewarm in flight)")
        return _warming_codex_tree_payload("miss")
    except Exception as e:
        logger.exception("Inspector tree scan failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/codex/tree-snapshot/modes", response_model=List[TreeSnapshotModeSchema])
def get_tree_snapshot_modes():
    """
    [ACTION]
    - Teleology: Return the available tree snapshot modes for toolbar dropdown rendering.
    - Mechanism: Delegates to inspector_service.get_tree_snapshot_modes().
    - Reads: In-memory mode metadata.
    - Writes: None.
    - Fails: Unexpected exceptions -> HTTP 500.
    - Guarantee: Returns ordered mode entries as `{id, name, desc}`.
    """
    try:
        return inspector_service.get_tree_snapshot_modes()
    except Exception as e:
        logger.exception("Inspector tree snapshot modes failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/codex/tree-snapshot/text", response_class=PlainTextResponse)
def get_tree_snapshot_text(mode: str = Query("1")):
    """
    [ACTION]
    - Teleology: Generate a plain-text tree snapshot for clipboard copy.
    - Mechanism: Delegates to inspector_service.render_tree_snapshot(mode) and returns raw text.
    - Reads: Filesystem under repo root according to selected mode.
    - Writes: None.
    - Fails: Unexpected exceptions -> HTTP 500.
    - Guarantee: Returns text/plain content suitable for direct clipboard writes.
    """
    try:
        content = inspector_service.render_tree_snapshot(mode)
        return PlainTextResponse(content)
    except Exception as e:
        logger.exception("Inspector tree snapshot render failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/codex/hologram-info")
def get_hologram_info(path: str):
    """
    [ACTION]
    - Teleology: Return metadata and source file list for a hologram artifact.
    - Mechanism: Reads the hologram JSON, prefers semantic hologram structures, and falls back to legacy tree/module extraction.
    - Reads: Single hologram JSON under codex/hologram/.
    - Writes: None.
    - Fails: File not found -> HTTP 404. Bad JSON -> HTTP 500.
    - Guarantee: Returns {artifact, domains, files_scanned, source_files}.
    """
    import json as _json
    hologram_root = inspector_service.root / "codex" / "hologram"
    target = hologram_root / path
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Hologram artifact not found: {path}")
    try:
        data = _json.loads(target.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse hologram JSON: {e}")

    meta = data.get("__meta", {})
    domains = [str(value).strip() for value in meta.get("domains", []) if str(value).strip()]
    if not domains:
        semantic_tags = [
            meta.get("projection_kind"),
            meta.get("scope_level"),
            meta.get("fidelity_level"),
        ]
        domains = sorted({str(value).strip() for value in semantic_tags if str(value).strip()})
    files_scanned: int = meta.get("files_scanned", meta.get("file_count", meta.get("total_files", 0)))
    source_paths: set[str] = set()
    artifact_paths: set[str] = set()

    def _add_source_path(raw_path: Any, *, artifact_hint: bool = False) -> None:
        if not isinstance(raw_path, str):
            return
        normalized = raw_path.strip().lstrip("./")
        if not normalized:
            return
        if normalized.startswith("codex/hologram/"):
            artifact_paths.add(normalized)
            return
        if artifact_hint:
            artifact_paths.add(normalized)
            return
        source_paths.add(normalized)

    def _collect_semantic_paths(node: Any, parent_key: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                normalized_key = str(key).strip().lower()
                if normalized_key in {
                    "path",
                    "file_path",
                    "repo_path",
                    "source_path",
                    "module_path",
                    "owner_path",
                    "test_path",
                    "implementation_path",
                    "importer_path",
                    "imported_path",
                    "from_path",
                    "to_path",
                }:
                    _add_source_path(value, artifact_hint=parent_key == "artifacts")
                    continue
                if normalized_key in {"artifacts", "authority_refs", "composes_from"}:
                    if isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                _add_source_path(item, artifact_hint=True)
                            else:
                                _collect_semantic_paths(item, normalized_key)
                    elif isinstance(value, dict):
                        _collect_semantic_paths(value, normalized_key)
                    continue
                if isinstance(value, (dict, list)):
                    _collect_semantic_paths(value, normalized_key)
        elif isinstance(node, list):
            for item in node:
                _collect_semantic_paths(item, parent_key)

    _collect_semantic_paths(data)

    # Legacy tree/module extraction remains for older hologram shapes and the UI index.
    tree = data.get("tree")
    if tree and isinstance(tree, dict) and domains:
        for d1, v1 in tree.items():
            if isinstance(v1, dict):
                for d2, v2 in v1.items():
                    if isinstance(v2, dict):
                        for fname in v2:
                            if "." in fname:
                                source_paths.add(f"{d1}/{d2}/{fname}")

    file_list = data.get("files")
    if file_list and isinstance(file_list, list):
        for entry in file_list:
            if isinstance(entry, dict) and "path" in entry:
                _add_source_path(entry["path"])

    if tree and isinstance(tree, dict) and not domains:
        for d1, v1 in tree.items():
            if isinstance(v1, dict):
                for fname in v1:
                    if "." in fname:
                        source_paths.add(f"{d1}/{fname}")

    modules = data.get("modules")
    if modules and isinstance(modules, list):
        for m in modules:
            if isinstance(m, dict) and "path" in m:
                _add_source_path(m["path"])

    source_files = sorted(source_paths or artifact_paths)

    return {
        "artifact": path,
        "domains": domains,
        "files_scanned": files_scanned or len(source_files),
        "source_files": source_files,
    }

@app.get("/api/codex/file", response_model=CodexFileDetailSchema)
def get_codex_file(path: str):
    """
    [ACTION]
    - Teleology: Return detailed inspector output for a single codex file path.
    - Mechanism: Delegates to inspector_service.inspect_file(path).
    - Reads: Filesystem content for the requested path.
    - Writes: None.
    - Fails: Unexpected exceptions -> HTTP 500.
    - Guarantee: Returns an inspected file detail payload for the requested path.
    - When-needed: Open when the inspector drawer or an operator needs the exact route that normalizes shorthand paths and delegates to file inspection.
    - Escalates-to: system/server/inspector.py::InspectorService.inspect_file; system/server/schemas.py::CodexFileDetailSchema
    """
    normalized_path = _normalize_codex_path(path)
    try:
        return inspector_service.inspect_file(normalized_path)
    except Exception as e:
        logger.exception(f"File inspection failed: {normalized_path}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/codex/doctrine/{doctrine_id}", response_model=DoctrineDetailSchema)
def get_codex_doctrine_detail(doctrine_id: str):
    """
    [ACTION]
    - Teleology: Return the full projected payload for a single doctrine node (concept, mechanism, or principle)
      so the Inspector drawer can drill down from a file enrichment card without extra roundtrips.
    - Mechanism: Delegates to DoctrineEnrichmentService; id prefix (`mech_`, `con_`, `pri_`) selects the kind.
    - Reads: In-memory doctrine cache (built once at service init).
    - Writes: None.
    - Fails: Unknown id -> HTTP 404; service unavailable -> HTTP 503; unexpected -> HTTP 500.
    - Guarantee: Returns a DoctrineDetailSchema-compatible payload for known doctrine ids.
    """
    doctrine_svc = inspector_service.get_doctrine_service()
    if doctrine_svc is None:
        raise HTTPException(status_code=503, detail="Doctrine enrichment service unavailable")
    try:
        detail = doctrine_svc.get_doctrine_detail(doctrine_id)
    except Exception as e:
        logger.exception(f"Doctrine detail failed for {doctrine_id}")
        raise HTTPException(status_code=500, detail=str(e))
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Doctrine id not found: {doctrine_id}")
    return detail


@app.get("/api/codex/doctrine")
def get_codex_doctrine_summary():
    """
    [ACTION]
    - Teleology: Return service health summary + counts for the doctrine enrichment cache.
    - Mechanism: Delegates to DoctrineEnrichmentService.get_summary().
    - Reads: In-memory cache.
    - Writes: None.
    - Fails: Service unavailable -> HTTP 503.
    - Guarantee: Returns a compact dict describing mechanism/concept/principle counts and active family.
    """
    doctrine_svc = inspector_service.get_doctrine_service()
    if doctrine_svc is None:
        raise HTTPException(status_code=503, detail="Doctrine enrichment service unavailable")
    return doctrine_svc.get_summary()


@app.get("/api/library/annexes")
def library_annexes(q: str | None = Query(default=None)):
    return {"annexes": library_catalog_loader.list_annexes(repo_root=REPO_ROOT, query=q)}


@app.get("/api/library/annexes/{slug}")
def library_annex_detail(slug: str):
    payload = library_catalog_loader.get_annex_detail(repo_root=REPO_ROOT, slug=slug)
    if not payload:
        raise HTTPException(status_code=404, detail=f"Annex not found: {slug}")
    return payload


@app.get("/api/library/concepts")
def library_concepts():
    return {"concepts": library_catalog_loader.list_concepts(repo_root=REPO_ROOT)}


@app.get("/api/library/concepts/{concept_id}")
def library_concept_detail(concept_id: str):
    payload = library_catalog_loader.get_concept(repo_root=REPO_ROOT, concept_id=concept_id)
    if not payload:
        raise HTTPException(status_code=404, detail=f"Concept not found: {concept_id}")
    return payload


@app.get("/api/library/mechanisms")
def library_mechanisms():
    return {"mechanisms": library_catalog_loader.list_mechanisms(repo_root=REPO_ROOT)}


@app.get("/api/library/mechanisms/{mechanism_id}")
def library_mechanism_detail(mechanism_id: str):
    payload = library_catalog_loader.get_mechanism(
        repo_root=REPO_ROOT,
        mechanism_id=mechanism_id,
    )
    if not payload:
        raise HTTPException(status_code=404, detail=f"Mechanism not found: {mechanism_id}")
    return payload


@app.get("/api/library/standards")
def library_standards():
    return {"standards": library_catalog_loader.list_standards(repo_root=REPO_ROOT)}


@app.get("/api/library/standards/{standard_id}")
def library_standard_detail(standard_id: str):
    payload = library_catalog_loader.get_standard(repo_root=REPO_ROOT, standard_id=standard_id)
    if not payload:
        raise HTTPException(status_code=404, detail=f"Standard not found: {standard_id}")
    return payload


@app.get("/api/library/system-map")
def library_system_map():
    return library_catalog_loader.get_system_map(repo_root=REPO_ROOT)


@app.get("/api/library/docs")
def library_docs():
    return {"docs": library_catalog_loader.list_docs(repo_root=REPO_ROOT)}


@app.get("/api/library/docs/content")
def library_doc_content(path: str = Query(...)):
    try:
        content = library_catalog_loader.get_doc_content(repo_root=REPO_ROOT, path=path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {path}") from None
    return {"content": content}


@app.post("/api/library/docs/content/save")
def library_doc_content_save(payload: DocSaveRequest):
    try:
        result = library_catalog_loader.save_doc_content(
            repo_root=REPO_ROOT,
            path=payload.path,
            content=payload.content,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document not found: {payload.path}") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"ok": True, **result}


@app.get("/api/library/tools")
def library_tools():
    return {"tools": library_catalog_loader.list_tools(repo_root=REPO_ROOT)}


@app.post("/api/codex/batch-read", response_model=BatchReadResponse)
def batch_read_files(payload: BatchReadRequest):
    """
    [ACTION]
    - Teleology: Batch-inspect multiple codex file paths for efficient UI loading.
    - Mechanism: Delegates to inspector_service.batch_inspect(payload.paths) and wraps results in BatchReadResponse.
    - Reads: Filesystem content for requested paths.
    - Writes: None.
    - Fails: Unexpected exceptions -> HTTP 500.
    - Guarantee: Returns BatchReadResponse(files=<results>) aligned to the response_model.
    """
    normalized_paths = [_normalize_codex_path(path) for path in payload.paths]
    try:
        results = inspector_service.batch_inspect(normalized_paths)
        return BatchReadResponse(files=results)
    except Exception as e:
        logger.exception("Batch read failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/runs/prune", response_model=PruneResponse)
def prune_runs(payload: PruneRequest):
    """
    [ACTION]
    - Teleology: Delete selected run directories, protecting pinned candidates.
    - Mechanism: Re-scans lobby to determine pinned run IDs; for each requested run_id, deletes its directory unless pinned; returns deleted/protected/errors.
    - Reads: Translator lobby (pin state); filesystem under state/runs.
    - Writes: Deletes directories under state/runs via shutil.rmtree.
    - Forbid: Attempting to delete a pinned run -> recorded as protected, not deleted.
    - Fails: Missing run dir or rmtree failure -> recorded in errors (best-effort batch).
    - Guarantee: Returns PruneResponse summarizing deletions, protections, and failures.
    """
    import shutil
    deleted = []
    protected = []
    errors = []
    
    try:
        # Re-scan to get fresh pin state
        lobby = translator.scan_lobby()
        pinned_ids = {c.id for c in lobby.candidates if c.is_pinned}
    except Exception: pinned_ids = set()

    runs_dir = _resolve_runs_dir_canonical(REPO_ROOT, _read_runs_dir_value())
    safe_run_ids = [_validate_run_id(rid) for rid in payload.run_ids]

    for rid in safe_run_ids:
        if rid in pinned_ids:
            protected.append(rid)
            continue
        
        rp = _resolve_run_dir(runs_dir, rid)
        if not rp.exists():
            errors.append(f"Not found: {rid}")
            continue
            
        try:
            shutil.rmtree(rp)
            deleted.append(rid)
        except Exception as e:
            errors.append(f"Failed to delete {rid}: {e}")
            
    return PruneResponse(deleted=deleted, protected=protected, errors=errors)

# --- META SERVICE ENDPOINTS ---

def _ts() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

@app.post("/api/meta/observe", response_model=MetaObserveResponse)
def meta_observe(payload: MetaObserveRequest):
    """
    [ACTION]
    - Teleology: Securely execute 'observe' tools (read context).
    - Mechanism: Delegates to meta_service.run_observe().
    - Fails: Returns failure envelope on exception (HTTP 200).
    - When-needed: Open when tracing the API surface that exposes meta observe runs while preserving failure envelopes instead of raising HTTP errors.
    - Escalates-to: system/server/meta_service.py::MetaService.run_observe; system/server/schemas.py::MetaObserveResponse
    """
    try:
        return meta_service.run_observe(payload)
    except Exception as e:
        logger.exception("Meta Observe Endpoint Error")
        return MetaObserveResponse(
            metadata=MetaToolMetadata(status="failure", timestamp=_ts(), error=str(e))
        )

@app.post("/api/meta/apply", response_model=MetaApplyResponse)
def meta_apply(payload: MetaApplyRequest):
    """
    [ACTION]
    - Teleology: Securely execute 'apply' tools (write/edit source).
    - Mechanism: Delegates to meta_service.run_apply().
    - Fails: Returns failure envelope on exception (HTTP 200).
    """
    try:
        return meta_service.run_apply(payload)
    except Exception as e:
        logger.exception("Meta Apply Endpoint Error")
        return MetaApplyResponse(
            metadata=MetaToolMetadata(status="failure", timestamp=_ts(), error=str(e))
        )

@app.post("/api/meta/patch", response_model=MetaPatchResponse)
def meta_patch(payload: MetaPatchRequest):
    """
    [ACTION]
    - Teleology: Securely execute 'patcher' tools (transactional JSON patch).
    - Mechanism: Delegates to meta_service.run_patch().
    - Fails: Returns failure envelope on exception (HTTP 200).
    """
    try:
        return meta_service.run_patch(payload)
    except Exception as e:
        logger.exception("Meta Patch Endpoint Error")
        return MetaPatchResponse(
            metadata=MetaToolMetadata(status="failure", timestamp=_ts(), error=str(e))
        )

@app.post("/api/meta/build-hologram", response_model=MetaBuildResponse)
def meta_build_hologram(payload: MetaBuildRequest):
    """
    [ACTION]
    - Teleology: Securely execute 'builder' tools (recompile hologram).
    - Mechanism: Delegates to meta_service.run_build_hologram().
    - Fails: Returns failure envelope on exception (HTTP 200).
    """
    try:
        return meta_service.run_build_hologram(payload)
    except Exception as e:
        logger.exception("Meta Builder Endpoint Error")
        return MetaBuildResponse(
            metadata=MetaToolMetadata(status="failure", timestamp=_ts(), error=str(e))
        )


@app.get("/api/patches", response_model=List[PatchRecordListItem])
def list_patch_records(limit: int = Query(50, ge=1, le=200), cursor: Optional[str] = None):
    """
    [ACTION]
    - Teleology: Return persisted patch records as lightweight summaries (newest first).
    - Mechanism: Delegates to meta_service.list_patch_records(limit, cursor).
    - Reads: state/patches/*.json
    - Writes: None.
    - Fails: Invalid cursor -> HTTP 400.
    """
    try:
        return meta_service.list_patch_records(limit=limit, cursor=cursor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/patches/{patch_id}", response_model=PatchRecord)
def get_patch_record(patch_id: str):
    """
    [ACTION]
    - Teleology: Return a full persisted patch record by ID.
    - Mechanism: Delegates to meta_service.get_patch_record(patch_id).
    - Reads: state/patches/<patch_id>.json
    - Writes: None.
    - Fails: Invalid patch_id -> HTTP 400, missing record -> HTTP 404.
    """
    try:
        return meta_service.get_patch_record(patch_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Patch record not found")

# --- META OBSERVE SESSION ENDPOINTS ---

@app.get("/api/meta/observe/templates", response_model=List[str])
def list_observe_templates():
    """
    [ACTION]
    - Teleology: List available observe session template IDs for the UI template picker.
    - Guarantee: Returns a sorted list of template stem names (possibly empty if directory missing).
    - Fails: None.
    """
    templates_dir = REPO_ROOT / "codex" / "standards" / "observe" / "templates"
    if not templates_dir.exists():
        return []
    return sorted([p.stem for p in templates_dir.glob("*.json")])

@app.post("/api/meta/observe/session/draft_plan", response_model=MetaEnvelope[ObserveSessionDraftResponse])
def meta_observe_session_draft_plan(payload: ObserveSessionDraftRequest):
    """
    [ACTION]
    - Teleology: Draft an observe-session plan from a problem description and posture.
    - Guarantee: Returns a MetaEnvelope wrapping ObserveSessionDraftResponse on success; returns failure envelope on exception.
    - Fails: Returns failure envelope (HTTP 200) on any exception.
    """
    try:
        return meta_service.draft_observe_session_plan(payload)
    except Exception as e:
        logger.exception("Meta Observe Session Draft Plan Endpoint Error")
        return MetaEnvelope(
            metadata=MetaToolMetadata(status="failure", timestamp=_ts(), error=str(e)),
            data=None
        )

@app.post("/api/meta/observe/session/ignite", response_model=ObserveSessionIgniteResponse)
def meta_observe_session_ignite(payload: ObserveSessionIgniteRequest):
    """
    [ACTION]
    - Teleology: Ignite an observe session from a plan or plan_path, generating a unique observe_id.
    - Guarantee: Returns ObserveSessionIgniteResponse with status "ignited", "busy", or "failed".
    - Fails: Delegates to MetaSessionController; errors propagate as ObserveSessionIgniteResponse with failed status.
    """
    import uuid
    obs_id = f"OBS_{_ts().replace(':', '-')}_{uuid.uuid4().hex[:8]}"
    return meta_session_controller.ignite_session(payload, obs_id)

@app.post("/api/meta/observe/session/abort", response_model=ObserveSessionStatusResponse)
def meta_observe_session_abort(observe_id: str = Query(...)):
    """
    [ACTION]
    - Teleology: Abort an in-progress observe session by observe_id.
    - Guarantee: Returns the updated ObserveSessionStatusResponse after requesting abort.
    - Fails: Delegates to MetaSessionController; errors may propagate.
    """
    return meta_session_controller.abort_session(observe_id)


def _grouped_runtime_status(ref: str | None = None) -> ObserveSessionStatusResponse:
    history_dir = REPO_ROOT / "tools" / "meta" / "apply" / "observe_history"
    payload = grouped_runtime_status_payload(REPO_ROOT, history_dir, ref)
    return ObserveSessionStatusResponse.model_validate(payload)


@app.get("/api/meta/observe/runtime/status", response_model=ObserveSessionStatusResponse)
def meta_observe_runtime_status():
    """
    [ACTION]
    - Teleology: Return the current observe runtime status, preferring the active session controller over the grouped observe runtime.
    - Guarantee: Returns ObserveSessionStatusResponse; falls back to grouped runtime status when session is idle.
    - Fails: None (errors in grouped runtime status may propagate).
    """
    session_status = meta_session_controller.get_status()
    session_state = session_status.state.value if hasattr(session_status.state, "value") else str(session_status.state)
    if session_state not in {"idle"}:
        return session_status
    return _grouped_runtime_status()


@app.post("/api/meta/observe/runtime/abort", response_model=ObserveSessionStatusResponse)
def meta_observe_runtime_abort(observe_id: str = Query(...), force: bool = Query(False)):
    """
    [ACTION]
    - Teleology: Abort an observe runtime (session controller or grouped runtime) by observe_id.
    - Guarantee: Returns updated ObserveSessionStatusResponse after requesting cancel on the matching runtime.
    - Fails: HTTP 404 if no matching observe runtime found for the given observe_id.
    """
    session_status = meta_session_controller.get_status()
    if session_status.observe_id == observe_id and (session_status.state.value if hasattr(session_status.state, "value") else str(session_status.state)) not in {"idle", "awaiting_review", "completed", "error", "aborted"}:
        return meta_session_controller.abort_session(observe_id)

    history_dir = REPO_ROOT / "tools" / "meta" / "apply" / "observe_history"
    manifest_path = resolve_grouped_runtime_manifest_path(REPO_ROOT, history_dir, observe_id)
    runtime = load_grouped_runtime_manifest(REPO_ROOT, history_dir, observe_id)
    if manifest_path is None or not runtime:
        raise HTTPException(status_code=404, detail="Observe runtime not found")
    request_grouped_runtime_cancel(
        repo_root=REPO_ROOT,
        history_dir=history_dir,
        ref=observe_id,
        force=force,
        wait_timeout_s=15.0,
        poll_interval_s=0.5,
    )
    return _grouped_runtime_status(observe_id)


@app.post("/api/meta/observe/runtime/continue", response_model=ObserveSessionStatusResponse)
def meta_observe_runtime_continue(observe_id: str = Query(...)):
    """
    [ACTION]
    - Teleology: Resume a pausable grouped observe runtime by spawning a continuation subprocess.
    - Guarantee: Launches subprocess and returns the current grouped runtime status after scheduling continuation.
    - Fails: HTTP 409 if the runtime is not a grouped_observe kind or is not resumable; HTTP 400 if plan_file is missing.
    """
    runtime = _grouped_runtime_status(observe_id)
    if runtime.kind != "grouped_observe":
        raise HTTPException(status_code=409, detail=f"Observe runtime is not a grouped runtime: {runtime.kind}")
    if not runtime.can_continue:
        raise HTTPException(
            status_code=409,
            detail=f"Observe runtime is not resumable: {runtime.state} ({runtime.continue_reason or 'unknown_reason'})",
        )
    plan_file = runtime.artifacts.get("plan_file")
    if not plan_file:
        raise HTTPException(status_code=400, detail="Observe runtime is missing plan_file")
    history_entry_payload: dict[str, Any] = {}
    history_entry = runtime.artifacts.get("history_entry")
    if history_entry:
        history_path = (REPO_ROOT / history_entry).resolve()
        try:
            history_path.relative_to(REPO_ROOT.resolve())
            history_entry_payload = json.loads(history_path.read_text(encoding="utf-8"))
        except Exception:
            history_entry_payload = {}
    sticky_summary = history_entry_payload.get("sticky_dump_dir") if isinstance(history_entry_payload.get("sticky_dump_dir"), dict) else {}
    bridge_summary = history_entry_payload.get("bridge") if isinstance(history_entry_payload.get("bridge"), dict) else {}
    command = [
        sys.executable,
        "-m",
        "tools.meta.apply.run_observe_plan",
        "--plan",
        plan_file,
        "--result",
        "tools/meta/apply/observe_result.json",
        "--history-dir",
        "tools/meta/apply/observe_history",
        "--bridge",
        "--provider",
        runtime.provider or "chatgpt",
        "--bridge-workers",
        runtime.requested_workers or "auto",
        "--bridge-timeout-s",
        str(bridge_summary.get("timeout_s") or 1500.0),
        "--launch-profile",
        runtime.launch_profile or "experimental",
        "--resume-observe",
        observe_id,
    ]
    retry_group_labels = [str(label).strip() for label in runtime.retryable_group_labels if str(label).strip()]
    for label in retry_group_labels:
        command.extend(["--retry-label", label])
    bridge_max_chars = int(bridge_summary.get("max_dump_chars") or 0)
    if bridge_max_chars > 0:
        command.extend(["--bridge-max-chars", str(bridge_max_chars)])
    if not bool(sticky_summary.get("enabled")):
        command.append("--no-sticky-dump-dir")
    subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return _grouped_runtime_status(observe_id)

@app.post("/api/meta/observe/session/preview", response_model=ObserveSessionPreviewResponse)
def meta_observe_session_preview(payload: ObserveSessionIgniteRequest):
    """
    [ACTION]
    - Teleology: Preview an observe session plan (context size estimates, staleness, DAG wave counts) without dispatching.
    - Guarantee: Returns ObserveSessionPreviewResponse with is_valid=False on any error rather than raising.
    - Fails: None (errors are captured into is_valid/error fields in the response).
    """
    plan = payload.plan
    if not plan and payload.plan_path:
        try:
            from tools.meta.apply.observe_session import _read_json
            from system.server.schemas import ObserveSessionPlan
            path_to_read = (meta_service.root / payload.plan_path).resolve()
            path_to_read.relative_to(meta_service.root.resolve())
            if path_to_read.exists():
                plan = ObserveSessionPlan(**_read_json(path_to_read))
        except Exception:
            pass

    if not plan:
        from system.server.schemas import ObserveSessionPlan
        return ObserveSessionPreviewResponse(
            plan=ObserveSessionPlan(groups=[]),
            total_groups=0,
            is_valid=False,
            error="Could not resolve plan"
        )
        
    try:
        from dateutil import parser
        import os
        drafted_dt = None
        if plan.drafted_at:
            try:
                drafted_dt = parser.parse(plan.drafted_at)
            except Exception:
                pass
                
        group_previews = []
        total_chars = 0
        from tools.meta.apply.observe_session import MetaSessionOrchestratorImpl
        
        for g in plan.groups:
            g_chars = 0
            g_stale = False
            g_files = 0
            for t in g.targets:
                g_files += 1
                try:
                    p = (meta_service.root / t.file).resolve()
                    if p.exists() and p.is_file():
                        g_chars += p.stat().st_size
                        if drafted_dt:
                            mtime = os.path.getmtime(p)
                            if mtime > drafted_dt.timestamp():
                                g_stale = True
                except Exception:
                    pass
            group_previews.append(ObserveGroupPreview(
                label=g.label,
                context_estimation_chars=g_chars,
                is_stale=g_stale,
                file_count=g_files
            ))
            total_chars += g_chars
            
        orch = MetaSessionOrchestratorImpl(meta_service.root)
        nodes = orch.build_nodes(plan=plan)
        orch.compute_waves(nodes=nodes)
        
        return ObserveSessionPreviewResponse(
            plan=plan,
            total_groups=len(plan.groups),
            is_valid=True,
            error=None,
            group_previews=group_previews,
            total_context_estimation_chars=total_chars,
            provider=payload.provider
        )
    except Exception as e:
        return ObserveSessionPreviewResponse(
            plan=plan,
            total_groups=len(plan.groups),
            is_valid=False,
            error=str(e),
            provider=payload.provider
        )

@app.get("/api/meta/observe/session/history", response_model=ObserveSessionHistoryResponse)
def meta_observe_session_history():
    """
    [ACTION]
    - Teleology: Return the most recent observe session manifests for the history panel.
    - Guarantee: Returns up to 5 sessions sorted by generated_at descending; returns empty list if directory missing.
    - Fails: Per-manifest JSON parse errors are silently skipped.
    """
    sessions_dir = meta_service.root / "obsidian" / "meta" / "observe_sessions"
    items = []
    if sessions_dir.exists():
        manifests = []
        for d in sessions_dir.iterdir():
            if d.is_dir():
                manifest_path = d / "_session_manifest.json"
                if manifest_path.exists():
                    try:
                        import json
                        data = json.loads(manifest_path.read_text(encoding="utf-8"))
                        manifests.append(data)
                    except Exception:
                        pass
        
        manifests.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
        for m in manifests[:5]:
            items.append(ObserveSessionHistoryItem(
                observe_id=m.get("observe_id", ""),
                session_slug=m.get("session_slug", ""),
                generated_at=m.get("generated_at", ""),
                status=m.get("status", "unknown"),
                model=m.get("model", ""),
                plan_hash=m.get("plan_hash", ""),
                parent_observe_id=m.get("parent_observe_id")
            ))
    return ObserveSessionHistoryResponse(sessions=items)

from fastapi.responses import FileResponse

@app.get("/api/meta/observe/artifact")
def meta_observe_artifact(path: str = Query(...)):
    """
    [ACTION]
    - Teleology: Serve a jailed observe artifact file (plan, response dump, session mirror, or promoted plan).
    - Guarantee: Returns FileResponse for allowed paths within the observe-artifact jail.
    - Fails: HTTP 403 if path escapes the jail or is not under an allowed prefix; HTTP 404 if file missing; HTTP 500 on unexpected errors.
    """
    def _observe_artifact_path_allowed(rel_path: str) -> bool:
        token = str(rel_path or "").strip().replace("\\", "/")
        if not token:
            return False
        if token.startswith("tools/meta/apply/observe_dumps/"):
            return True
        if token.startswith("obsidian/meta/observe_sessions/"):
            return True
        if token.startswith("codex/substrate/plan/"):
            return True
        if token.startswith("obsidian/") and token.endswith("/plan.md"):
            return True
        return False

    try:
        req_path = (meta_service.root / path).resolve()
        rel_path = str(req_path.relative_to(meta_service.root.resolve())).replace('\\', '/')
        if not _observe_artifact_path_allowed(rel_path):
            raise HTTPException(
                status_code=403,
                detail="Artifact path strictly jailed to observe dumps/session mirrors/promoted plan surfaces",
            )
        if not req_path.is_file():
            raise HTTPException(status_code=404, detail="Artifact not found")
        return FileResponse(req_path)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid path escape")
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# WORLD MODEL — projection of the holographic authority graph
# (con_024 holographic_world_model_and_projection_graph,
#  mech_023 zenith_frontend_world_model_projection,
#  pri_057..pri_063 frontend principles)
# =============================================================================

def _station_attention_brief(world: Dict[str, Any]) -> Dict[str, Any]:
    orchestration = dict(world.get("orchestration") or {})
    orchestration_gate = dict(orchestration.get("gate") or {})
    active_driver = str(orchestration.get("active_driver") or "").strip() or None
    current_owner = orchestration.get("current_owner")
    current_owner_actor = (
        current_owner.get("actor_id")
        if isinstance(current_owner, Mapping)
        else current_owner
    )
    next_handoff: Dict[str, Any] = {}
    try:
        events = world_model_loader.load_orchestration_events(REPO_ROOT, 1)
    except Exception as exc:
        logger.warning("station launcher handoff probe failed: %s", exc)
        events = []
    if events:
        latest = events[0] if isinstance(events[0], Mapping) else {}
        next_handoff_raw = latest.get("next_handoff") if isinstance(latest, Mapping) else {}
        if isinstance(next_handoff_raw, Mapping):
            next_handoff = {
                "actor_id": next_handoff_raw.get("actor_id"),
                "mode": next_handoff_raw.get("mode"),
                "command": next_handoff_raw.get("command"),
                "review_surface": next_handoff_raw.get("review_surface"),
            }

    active_phase_raw = dict(world.get("active_phase") or {})
    pipeline_state = dict(active_phase_raw.get("pipeline_state") or {})
    updated_at = pipeline_state.get("updated_at") or active_phase_raw.get("updated_at")
    active_phase = {
        "phase_id": active_phase_raw.get("phase_id"),
        "title": active_phase_raw.get("title"),
        "stage": pipeline_state.get("stage") or active_phase_raw.get("stage"),
        "controller_phase": pipeline_state.get("controller_phase") or active_phase_raw.get("controller_phase"),
        "cycle": pipeline_state.get("cycle") if pipeline_state.get("cycle") is not None else active_phase_raw.get("cycle"),
        "blocked": bool(pipeline_state.get("blocked") if pipeline_state else active_phase_raw.get("blocked")),
        "gate_reason": (
            pipeline_state.get("gate_reason")
            or active_phase_raw.get("gate_reason")
            or orchestration_gate.get("gate_reason")
            or orchestration.get("gate_reason")
        ),
        "updated_at": updated_at,
        "freshness": world_model_loader.compute_freshness(updated_at),
    }

    work_ledger: Dict[str, Any] = {}
    try:
        work_ledger_status = world_model_loader.work_ledger_runtime.load_runtime_status(REPO_ROOT) or {}
        work_ledger = {
            "generated_at": work_ledger_status.get("generated_at"),
            "counts": dict(work_ledger_status.get("counts") or {}),
            "stale_sessions": list(work_ledger_status.get("stale_sessions") or [])[:10],
        }
    except Exception as exc:
        logger.warning("station launcher work-ledger load failed: %s", exc)

    return {
        "current_driver": {
            "actor_id": orchestration_gate.get("owner_driver") or current_owner_actor or active_driver,
            "driver_id": active_driver,
        },
        "next_handoff": next_handoff,
        "active_phase": active_phase,
        "work_ledger": work_ledger,
    }


_STATION_LAUNCHER_PREWARM_WAIT_S = 0.25


def _warming_station_launcher_payload(reason: str) -> Dict[str, Any]:
    """Schema-clean degraded launcher shell returned while prewarm is in flight.

    Every field on `StationLauncherSnapshot` has a default factory except
    `generated_at`, so the operator UI tolerates an otherwise-empty packet and
    can immediately retry once prewarm lands the cache. Avoids racing a
    duplicate compute on top of an already-running prewarm thread.
    """
    detail = (
        f"station launcher {reason}; background refresh is in flight"
        if reason == "miss"
        else "station launcher unavailable; retry will start another background refresh"
    )
    return {
        "schema": "station_launcher_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operations": [],
        "alerts": [
            {
                "id": "station_launcher:warming",
                "tone": "info",
                "label": "Station launcher warming",
                "detail": detail,
                "command": None,
            }
        ],
        "diagnostics": {
            "cache": {"status": "warming", "reason": reason},
            "notes": [
                "Served a schema-clean warming launcher payload instead of blocking the UI on launcher composition."
            ],
        },
    }


def _warming_operations_catalog_payload(reason: str) -> Dict[str, Any]:
    generated = datetime.now(timezone.utc).isoformat()
    detail = f"operations catalog {reason}; background refresh is in flight"
    return {
        "schema": "ops_launcher_snapshot_v1",
        "generated_at": generated,
        "operations": [],
        "operation_groups": [],
        "navigation_freshness": {
            "schema": "navigation_freshness_v1",
            "generated_at": generated,
            "available": False,
            "refresh_operation_id": "navigator_refresh",
            "route_refresh_operation_id": "semantic_route_refresh",
            "stale_source_count": 0,
            "stale_or_missing_row_count": 0,
            "has_estimates": False,
            "top_source_kind": None,
            "queue": [],
        },
        "raw_seed_pipeline": {
            "available": False,
            "next_actions": [],
            "warnings": [detail],
            "source_paths": {},
        },
        "quick_actions": [],
        "alerts": [
            {
                "id": "operations_catalog:warming",
                "tone": "info",
                "label": "Operations catalog warming",
                "detail": detail,
                "operation_id": None,
                "parameters": {},
                "command": None,
            }
        ],
        "errors": [],
        "diagnostics": {
            "cache": {"status": "warming", "reason": reason},
            "notes": [
                "Served a schema-clean warming operations payload instead of blocking the UI on catalog composition."
            ],
        },
    }


def _warming_world_model_snapshot_payload(reason: str) -> Dict[str, Any]:
    generated = datetime.now(timezone.utc).isoformat()
    detail = f"world-model snapshot {reason}; background refresh is in flight"
    return {
        "schema": "world_model_snapshot_v1",
        "generated_at": generated,
        "family": None,
        "phases": [],
        "active_phase": None,
        "orchestration": None,
        "docs_focus": {
            "path": "tools/meta/control/documentation_route_focus.json",
            "active_preset_id": "neutral",
            "label": "Neutral",
            "presets": [],
            "updated_at": None,
        },
        "doctrine_runtime": {
            "schema_version": None,
            "purpose": None,
            "control_plane": {
                "emit_self": None,
                "docs_route": None,
                "docs_route_focus_list": None,
                "docs_route_focus_set": None,
                "agent_bootstrap": None,
                "orchestration_state": None,
                "orchestration_event_log": None,
            },
            "operator_quickstart": [],
            "freshness": None,
        },
        "agent_bootstrap_live": {
            "schema_version": None,
            "generated_at": None,
            "live_bindings": {},
            "situation_routes": [],
            "actor_context_surfaces": [],
            "freshness": None,
        },
        "navigation_graph": None,
        "frontend_navigation_mission_control": None,
        "navigation_freshness": {
            "schema": "navigation_freshness_v1",
            "generated_at": generated,
            "available": False,
            "refresh_operation_id": "navigator_refresh",
            "route_refresh_operation_id": "semantic_route_refresh",
            "stale_source_count": 0,
            "stale_or_missing_row_count": 0,
            "has_estimates": False,
            "top_source_kind": None,
            "queue": [],
        },
        "catalog": {
            "system_map_generated_at": None,
            "concepts": [],
            "mechanisms": [],
            "principles": [],
        },
        "principles_family": {
            "path": None,
            "family_id": None,
            "family_number": None,
            "family_title": None,
            "generated_at": None,
            "principles": [],
        },
        "host_agents": {
            "schema": "host_agent_external_snapshot_v1",
            "generated_at": generated,
            "available": False,
            "campaign_id": None,
            "authored_at": None,
            "authored_freshness": {
                "tone": "unknown",
                "age_seconds": None,
                "label": "warming",
                "iso": None,
            },
            "mining_run_path": None,
            "current_window": {"label": "30d", "days": 30, "findings": [], "finding_count": 0},
            "extended_window": {"label": "90d", "days": 90, "findings": [], "finding_count": 0},
            "curate_count": 0,
            "deferred_count": 0,
            "curate": [],
            "deferred": [],
        },
        "host_agent_dotfiles": None,
        "drift_aggregate": None,
        "approvals": {
            "total_pending": 0,
            "source_kind_counts": {},
            "action_kind_counts": {},
            "status_counts": {},
            "top_records": [],
        },
        "freshness": {
            "orchestration": None,
            "doctrine_runtime": None,
            "agent_bootstrap_live": None,
            "host_agents": {"tone": "unknown", "age_seconds": None, "label": "warming", "iso": None},
            "host_agent_dotfiles": None,
            "system_map_generated_at": None,
            "autonomy_diagnostics": None,
        },
        "diagnostics": {
            "cache": {"status": "warming", "reason": reason},
            "notes": [
                "Served a schema-clean warming world-model snapshot instead of blocking first paint on snapshot composition.",
                detail,
            ],
        },
    }


def _world_model_snapshot_uncached_payload() -> Dict[str, Any]:
    builder = getattr(world_model_loader, "_uncached_load_world_model_snapshot", None)
    if callable(builder):
        try:
            params = inspect.signature(builder).parameters
        except (TypeError, ValueError):
            params = {}
        if "navigation_graph_payload" in params:
            return builder(REPO_ROOT, navigation_graph_payload="first_paint")
        return builder(REPO_ROOT)
    return world_model_loader.load_world_model_snapshot(
        REPO_ROOT,
        navigation_graph_payload="first_paint",
    )


def _schedule_world_model_snapshot_prewarm() -> None:
    swr_prewarm(
        _WORLD_MODEL_SNAPSHOT_CACHE_NAME,
        _world_model_snapshot_cache_key(),
        _world_model_snapshot_uncached_payload,
    )


def _world_model_snapshot_payload() -> Dict[str, Any]:
    cached = swr_peek(_WORLD_MODEL_SNAPSHOT_CACHE_NAME, _world_model_snapshot_cache_key())
    if isinstance(cached, dict):
        return cached

    try:
        _schedule_world_model_snapshot_prewarm()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("world-model snapshot prewarm failed to schedule: %s", exc)
        return _warming_world_model_snapshot_payload("unavailable")

    if _WORLD_MODEL_SNAPSHOT_PREWARM_WAIT_S > 0:
        time.sleep(_WORLD_MODEL_SNAPSHOT_PREWARM_WAIT_S)
        cached = swr_peek(_WORLD_MODEL_SNAPSHOT_CACHE_NAME, _world_model_snapshot_cache_key())
        if isinstance(cached, dict):
            return cached

    logger.info("world-model snapshot returned warming shell (prewarm in flight)")
    return _warming_world_model_snapshot_payload("miss")


def _warming_attention_snapshot_payload(reason: str) -> Dict[str, Any]:
    generated = datetime.now(timezone.utc).isoformat()
    detail = f"attention snapshot {reason}; background refresh is in flight"
    return {
        "schema": "attention_snapshot_v1",
        "generated_at": generated,
        "banner": {
            "tone": "warn",
            "title": "Attention snapshot warming",
            "summary": detail,
            "gate_reason": None,
            "command": None,
            "target": {"kind": "none"},
        },
        "current_driver": {"actor_id": None, "driver_id": None},
        "next_handoff": None,
        "active_phase": None,
        "active_cycle": None,
        "attention_items": [
            {
                "id": "attention:warming",
                "kind": "info",
                "title": "Attention snapshot warming",
                "detail": detail,
                "owner": "server",
                "command": None,
                "target": {"kind": "none"},
                "score": 0,
            }
        ],
        "recent_changes": [],
        "next_moves": [],
        "bridge_health": {
            "alive": None,
            "providers": [],
            "stale_reason": "attention snapshot is warming",
        },
        "drift": {
            "hologram": {
                "generated_at": None,
                "freshness": {
                    "tone": "unknown",
                    "age_seconds": None,
                    "label": "warming",
                    "iso": None,
                },
            },
            "system_view_file_count": None,
            "doctrine_runtime_mtime": None,
        },
        "work_ledger": {
            "generated_at": None,
            "counts": {},
            "triggers": {},
            "cohort_overview": {},
            "stale_sessions": [],
            "handoff_candidates": {
                "candidate_count": 0,
                "unimported_count": 0,
                "candidates": [],
            },
        },
        "reactions": None,
        "diagnostics": {
            "cache": {"status": "warming", "reason": reason},
            "notes": [
                "Served a schema-clean warming attention payload instead of blocking first paint on attention composition.",
                detail,
            ],
        },
    }


def _start_attention_snapshot_refresh(
    cache_key: str | None = None,
    *,
    thread_name: str = "attention-snapshot-refresh",
) -> threading.Event:
    if cache_key is None:
        cache_key = _attention_snapshot_cache_key()
    with _ATTENTION_SNAPSHOT_CACHE_LOCK:
        event = _ATTENTION_SNAPSHOT_REFRESH_IN_FLIGHT.get(cache_key)
        if event is not None:
            return event
        event = threading.Event()
        _ATTENTION_SNAPSHOT_REFRESH_IN_FLIGHT[cache_key] = event
    threading.Thread(
        target=_attention_snapshot_background_refresh,
        args=(cache_key, event),
        name=thread_name,
        daemon=True,
    ).start()
    return event


def _prewarm_attention_snapshot_inline() -> None:
    cache_key = _attention_snapshot_cache_key()
    now = time.monotonic()
    with _ATTENTION_SNAPSHOT_CACHE_LOCK:
        cached = _ATTENTION_SNAPSHOT_CACHE.get(cache_key)
        if cached and now - cached[0] <= _ATTENTION_SNAPSHOT_CACHE_TTL_S:
            return
        if cache_key in _ATTENTION_SNAPSHOT_REFRESH_IN_FLIGHT:
            return
        event = threading.Event()
        _ATTENTION_SNAPSHOT_REFRESH_IN_FLIGHT[cache_key] = event
    _attention_snapshot_background_refresh(cache_key, event)


def _attention_snapshot_payload() -> Dict[str, Any]:
    cache_key = _attention_snapshot_cache_key()
    now = time.monotonic()
    wait_event: threading.Event | None = None
    with _ATTENTION_SNAPSHOT_CACHE_LOCK:
        cached = _ATTENTION_SNAPSHOT_CACHE.get(cache_key)
        if cached:
            payload = copy.deepcopy(cached[1])
            if now - cached[0] <= _ATTENTION_SNAPSHOT_CACHE_TTL_S:
                return payload
            if cache_key not in _ATTENTION_SNAPSHOT_REFRESH_IN_FLIGHT:
                event = threading.Event()
                _ATTENTION_SNAPSHOT_REFRESH_IN_FLIGHT[cache_key] = event
                threading.Thread(
                    target=_attention_snapshot_background_refresh,
                    args=(cache_key, event),
                    name="attention-snapshot-refresh",
                    daemon=True,
                ).start()
            return payload
        wait_event = _ATTENTION_SNAPSHOT_REFRESH_IN_FLIGHT.get(cache_key)

    if wait_event is None:
        wait_event = _start_attention_snapshot_refresh(cache_key)
    if wait_event is not None:
        started = time.monotonic()
        wait_event.wait(timeout=_ATTENTION_SNAPSHOT_PREWARM_WAIT_S)
        with _ATTENTION_SNAPSHOT_CACHE_LOCK:
            cached = _ATTENTION_SNAPSHOT_CACHE.get(cache_key)
            if cached:
                return copy.deepcopy(cached[1])
            still_in_flight = cache_key in _ATTENTION_SNAPSHOT_REFRESH_IN_FLIGHT
        if still_in_flight:
            elapsed = time.monotonic() - started
            logger.info(
                "attention snapshot returned warming shell after %.2fs (prewarm in flight)",
                elapsed,
            )
            return _warming_attention_snapshot_payload("miss")
        logger.info("attention snapshot returned warming shell after failed refresh")
        return _warming_attention_snapshot_payload("unavailable")

    return _warming_attention_snapshot_payload("unavailable")


def _attention_snapshot_background_refresh(cache_key: str, event: threading.Event) -> None:
    try:
        _compute_attention_snapshot_payload(cache_key=cache_key)
    except Exception as exc:
        logger.warning("attention snapshot background refresh failed: %s", exc)
    finally:
        with _ATTENTION_SNAPSHOT_CACHE_LOCK:
            _ATTENTION_SNAPSHOT_REFRESH_IN_FLIGHT.pop(cache_key, None)
        event.set()


def _compute_attention_snapshot_payload(*, cache_key: str | None = None) -> Dict[str, Any]:
    if cache_key is None:
        cache_key = _attention_snapshot_cache_key()
    payload = world_model_loader.load_attention_snapshot(REPO_ROOT)
    if not isinstance(payload, dict):
        payload = {}
    with _ATTENTION_SNAPSHOT_CACHE_LOCK:
        _ATTENTION_SNAPSHOT_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(payload))
    return copy.deepcopy(payload)


def _normalize_blast_radius_request(path: str | None, max_depth: int) -> tuple[str, int]:
    normalized_path = world_model_loader._normalize_projection_path(path)
    if not normalized_path:
        raise ValueError("path is required")
    clamped_max_depth = max(
        1,
        min(int(max_depth or 4), world_model_loader.BLAST_RADIUS_MAX_DEPTH_CAP),
    )
    return normalized_path, clamped_max_depth


def _warming_blast_radius_payload(
    *,
    path: str,
    max_depth: int,
    reason: str,
    refresh_in_flight: bool = True,
) -> Dict[str, Any]:
    return {
        "kind": "kernel.blast_radius",
        "schema_version": "blast_radius_packet_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_path": path,
        "source": {
            "graph": str(world_model_loader.HOLOGRAM_GRAPH_PATH),
            "ui_index": str(world_model_loader.HOLOGRAM_UI_INDEX_PATH),
            "scope_index": str(world_model_loader.PYTHON_SCOPE_INDEX_PATH),
            "paper_modules": str(world_model_loader.PAPER_MODULE_INDEX_PATH),
            "annex_distillation": str(world_model_loader.ANNEX_DISTILLATION_INDEX_PATH),
            "frontend_navigation": str(world_model_loader.FRONTEND_NAVIGATION_GRAPH_PATH),
            "source_fingerprint": f"warming:{reason}",
        },
        "file_impact": {
            "direct_dependents": [],
            "transitive_dependents": [],
            "depth_buckets": {"1": [], "2": [], "3+": []},
        },
        "system_impact": {
            "paper_modules": [],
            "frontend_views": [],
            "standards": [],
            "skills": [],
            "annex_patterns": [],
            "routes": [],
            "tests": [],
            "render_checks": [],
        },
        "risk": {
            "impact_score": 0,
            "confidence": "warming",
            "risk_reasons": [f"blast_radius_cache_{reason}"],
        },
        "edge_sources": [],
        "suggested_verification": {
            "schema_version": "suggested_verification_v1",
            "commands": [],
            "omission_receipt": {"omitted_commands": 0, "reason": f"blast_radius_cache_{reason}"},
        },
        "omission_receipt": {
            "omitted_files": 0,
            "omitted_edges": 0,
            "omitted_overlays": 0,
            "reason": f"blast_radius_cache_{reason}",
        },
        "known_limits": [f"blast_radius_cache_{reason}", f"requested_max_depth:{max_depth}"],
        "projection_state": {
            "schema": "blast_radius_projection_state_v1",
            "state": "warming",
            "render_ready": False,
            "refresh_in_flight": bool(refresh_in_flight),
            "reason": reason,
            "retry_after_ms": 750,
        },
        "diagnostics": {
            "cache": {"status": "warming", "reason": reason},
            "notes": [
                "Served a schema-clean blast-radius warming packet instead of blocking the selected-node drawer on reverse-BFS composition.",
            ],
        },
    }


def _start_blast_radius_refresh(
    cache_key: tuple[str, int],
    *,
    thread_name: str = "blast-radius-refresh",
) -> threading.Event:
    with _BLAST_RADIUS_CACHE_LOCK:
        event = _BLAST_RADIUS_REFRESH_IN_FLIGHT.get(cache_key)
        if event is not None:
            return event
        event = threading.Event()
        _BLAST_RADIUS_REFRESH_IN_FLIGHT[cache_key] = event
    timer = threading.Timer(
        _BLAST_RADIUS_BACKGROUND_START_DELAY_S,
        _blast_radius_background_refresh,
        args=(cache_key, event),
    )
    timer.name = thread_name
    timer.daemon = True
    timer.start()
    return event


def _blast_radius_payload(*, path: str, max_depth: int) -> Dict[str, Any]:
    normalized_path, clamped_max_depth = _normalize_blast_radius_request(path, max_depth)
    cache_key = (normalized_path, clamped_max_depth)
    now = time.monotonic()
    wait_event: threading.Event | None = None
    with _BLAST_RADIUS_CACHE_LOCK:
        cached = _BLAST_RADIUS_CACHE.get(cache_key)
        if cached:
            payload = copy.deepcopy(cached[1])
            if now - cached[0] <= _BLAST_RADIUS_CACHE_TTL_S:
                return payload
            if cache_key not in _BLAST_RADIUS_REFRESH_IN_FLIGHT:
                event = threading.Event()
                _BLAST_RADIUS_REFRESH_IN_FLIGHT[cache_key] = event
                threading.Thread(
                    target=_blast_radius_background_refresh,
                    args=(cache_key, event),
                    name="blast-radius-refresh",
                    daemon=True,
                ).start()
            return payload
        wait_event = _BLAST_RADIUS_REFRESH_IN_FLIGHT.get(cache_key)

    if wait_event is None:
        wait_event = _start_blast_radius_refresh(cache_key)
    with _BLAST_RADIUS_CACHE_LOCK:
        cached = _BLAST_RADIUS_CACHE.get(cache_key)
        if cached:
            return copy.deepcopy(cached[1])
        still_in_flight = cache_key in _BLAST_RADIUS_REFRESH_IN_FLIGHT
    if still_in_flight:
        logger.info(
            "blast radius returned warming shell immediately for %s",
            normalized_path,
        )
        return _warming_blast_radius_payload(
            path=normalized_path,
            max_depth=clamped_max_depth,
            reason="miss",
        )
    return _warming_blast_radius_payload(
        path=normalized_path,
        max_depth=clamped_max_depth,
        reason="unavailable",
        refresh_in_flight=False,
    )


def _blast_radius_background_refresh(
    cache_key: tuple[str, int],
    event: threading.Event,
) -> None:
    normalized_path, clamped_max_depth = cache_key
    try:
        payload = world_model_loader.load_blast_radius_snapshot(
            REPO_ROOT,
            path=normalized_path,
            max_depth=clamped_max_depth,
        )
        if not isinstance(payload, dict):
            payload = {}
        with _BLAST_RADIUS_CACHE_LOCK:
            _BLAST_RADIUS_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(payload))
    except Exception as exc:
        logger.warning("blast radius background refresh failed for %s: %s", normalized_path, exc)
    finally:
        with _BLAST_RADIUS_CACHE_LOCK:
            _BLAST_RADIUS_REFRESH_IN_FLIGHT.pop(cache_key, None)
        event.set()


def _operations_catalog_background_refresh(event: threading.Event) -> None:
    try:
        payload = world_model_loader.list_launchable_operations(REPO_ROOT)
        if isinstance(payload, dict):
            _store_station_cache(
                _STATION_LAUNCHER_OPERATIONS_CACHE,
                _STATION_LAUNCHER_OPERATIONS_CACHE_LOCK,
                payload,
            )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("operations catalog refresh failed: %s", exc)
    finally:
        with _STATION_LAUNCHER_OPERATIONS_CACHE_LOCK:
            _STATION_LAUNCHER_OPERATIONS_REFRESH_IN_FLIGHT.pop(_station_cache_key(), None)
        event.set()


def _start_operations_catalog_refresh(*, thread_name: str = "operations-catalog-refresh") -> threading.Event:
    cache_key = _station_cache_key()
    with _STATION_LAUNCHER_OPERATIONS_CACHE_LOCK:
        event = _STATION_LAUNCHER_OPERATIONS_REFRESH_IN_FLIGHT.get(cache_key)
        if event is not None:
            return event
        event = threading.Event()
        _STATION_LAUNCHER_OPERATIONS_REFRESH_IN_FLIGHT[cache_key] = event
    threading.Thread(
        target=_operations_catalog_background_refresh,
        args=(event,),
        name=thread_name,
        daemon=True,
    ).start()
    return event


def _operations_catalog_payload() -> Dict[str, Any]:
    cache_key = _station_cache_key()
    now = time.monotonic()
    with _STATION_LAUNCHER_OPERATIONS_CACHE_LOCK:
        cached = _STATION_LAUNCHER_OPERATIONS_CACHE.get(cache_key)
        if cached:
            payload = copy.deepcopy(cached[1])
            if now - cached[0] <= _STATION_LAUNCHER_AUX_CACHE_TTL_S:
                return payload
            event = _STATION_LAUNCHER_OPERATIONS_REFRESH_IN_FLIGHT.get(cache_key)
            if event is None:
                event = threading.Event()
                _STATION_LAUNCHER_OPERATIONS_REFRESH_IN_FLIGHT[cache_key] = event
                threading.Thread(
                    target=_operations_catalog_background_refresh,
                    args=(event,),
                    name="operations-catalog-refresh",
                    daemon=True,
                ).start()
            return payload

    event = _start_operations_catalog_refresh()
    event.wait(timeout=_STATION_LAUNCHER_OPERATIONS_PREWARM_WAIT_S)
    with _STATION_LAUNCHER_OPERATIONS_CACHE_LOCK:
        cached = _STATION_LAUNCHER_OPERATIONS_CACHE.get(cache_key)
        if cached:
            return copy.deepcopy(cached[1])
        still_in_flight = cache_key in _STATION_LAUNCHER_OPERATIONS_REFRESH_IN_FLIGHT
    return _warming_operations_catalog_payload("miss" if still_in_flight else "unavailable")


def _start_root_navigator_handoff_refresh(
    cache_key: str,
    *,
    thread_name: str,
    delay_s: float = 0.0,
) -> threading.Event:
    with _ROOT_NAVIGATOR_HANDOFF_CACHE_LOCK:
        event = _ROOT_NAVIGATOR_HANDOFF_REFRESH_IN_FLIGHT.get(cache_key)
        if event is not None:
            return event
        event = threading.Event()
        _ROOT_NAVIGATOR_HANDOFF_REFRESH_IN_FLIGHT[cache_key] = event
    if delay_s > 0:
        timer = threading.Timer(
            delay_s,
            _root_navigator_handoff_background_refresh,
            args=(cache_key, event),
        )
        timer.name = f"{thread_name}-starter"
        timer.daemon = True
        timer.start()
    else:
        threading.Thread(
            target=_root_navigator_handoff_background_refresh,
            args=(cache_key, event),
            name=thread_name,
            daemon=True,
        ).start()
    return event


def _root_navigator_handoff_payload() -> Dict[str, Any]:
    cache_key = _root_navigator_handoff_cache_key()
    now = time.monotonic()
    wait_event: threading.Event | None = None
    with _ROOT_NAVIGATOR_HANDOFF_CACHE_LOCK:
        cached = _ROOT_NAVIGATOR_HANDOFF_CACHE.get(cache_key)
        if cached:
            payload = copy.deepcopy(cached[1])
            if now - cached[0] <= _ROOT_NAVIGATOR_HANDOFF_CACHE_TTL_S:
                return payload
            if cache_key not in _ROOT_NAVIGATOR_HANDOFF_REFRESH_IN_FLIGHT:
                event = threading.Event()
                _ROOT_NAVIGATOR_HANDOFF_REFRESH_IN_FLIGHT[cache_key] = event
                threading.Thread(
                    target=_root_navigator_handoff_background_refresh,
                    args=(cache_key, event),
                    name="root-navigator-handoff-refresh",
                    daemon=True,
                ).start()
            return payload
        wait_event = _ROOT_NAVIGATOR_HANDOFF_REFRESH_IN_FLIGHT.get(cache_key)

    if wait_event is None:
        # No prewarm exists in this process. Return the non-hollow static
        # packet before the full handoff builder can contend with response
        # serialization under uvicorn's single worker.
        _start_root_navigator_handoff_refresh(
            cache_key,
            thread_name="root-navigator-handoff-refresh",
            delay_s=_ROOT_NAVIGATOR_HANDOFF_BACKGROUND_START_DELAY_S,
        )
        return _warming_root_navigator_handoff_payload()
    if wait_event is not None:
        started = time.monotonic()
        wait_event.wait(timeout=_ROOT_NAVIGATOR_HANDOFF_PREWARM_WAIT_S)
        with _ROOT_NAVIGATOR_HANDOFF_CACHE_LOCK:
            cached = _ROOT_NAVIGATOR_HANDOFF_CACHE.get(cache_key)
            if cached:
                return copy.deepcopy(cached[1])
            still_in_flight = cache_key in _ROOT_NAVIGATOR_HANDOFF_REFRESH_IN_FLIGHT
        if still_in_flight:
            elapsed = time.monotonic() - started
            logger.info(
                "root navigator handoff returned warming shell after %.1fs (prewarm in flight)",
                elapsed,
            )
            return _warming_root_navigator_handoff_payload()

        logger.info("root navigator handoff returned warming shell after failed refresh")
        return _warming_root_navigator_handoff_payload()


def _root_navigator_handoff_background_refresh(cache_key: str, event: threading.Event) -> None:
    try:
        _compute_root_navigator_handoff_payload(cache_key=cache_key)
    except Exception as exc:
        logger.warning("root navigator handoff background refresh failed: %s", exc)
    finally:
        with _ROOT_NAVIGATOR_HANDOFF_CACHE_LOCK:
            _ROOT_NAVIGATOR_HANDOFF_REFRESH_IN_FLIGHT.pop(cache_key, None)
        event.set()


def _compute_root_navigator_handoff_payload(*, cache_key: str | None = None) -> Dict[str, Any]:
    if cache_key is None:
        cache_key = _root_navigator_handoff_cache_key()
    payload = frontend_surface_contracts.build_root_navigator_frontend_handoff_packet(REPO_ROOT)
    with _ROOT_NAVIGATOR_HANDOFF_CACHE_LOCK:
        _ROOT_NAVIGATOR_HANDOFF_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(payload))
    return copy.deepcopy(payload)


def _start_station_launcher_refresh(
    cache_key: str | None = None,
    *,
    thread_name: str = "station-launcher-refresh",
    delay_s: float = 0.0,
) -> threading.Event:
    if cache_key is None:
        cache_key = str(REPO_ROOT.resolve())
    with _STATION_LAUNCHER_CACHE_LOCK:
        event = _STATION_LAUNCHER_REFRESH_IN_FLIGHT.get(cache_key)
        if event is not None:
            return event
        event = threading.Event()
        _STATION_LAUNCHER_REFRESH_IN_FLIGHT[cache_key] = event
    if delay_s > 0:
        timer = threading.Timer(
            delay_s,
            _station_launcher_background_refresh,
            args=(cache_key, event),
        )
        timer.name = f"{thread_name}-starter"
        timer.daemon = True
        timer.start()
    else:
        threading.Thread(
            target=_station_launcher_background_refresh,
            args=(cache_key, event),
            name=thread_name,
            daemon=True,
        ).start()
    return event


def _station_launcher_payload() -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Serve the compact launcher/home packet used by `/station` with
      human-interactive latency even when the underlying world-model build is
      slow (`load_paper_modules_snapshot` walks the repo subtree).
    - Mechanism: Stale-while-revalidate over the payload cache. On cache hit,
      return instantly. If the hit is stale, spawn a single-flight background
      refresh. A request that arrives while startup prewarm is already in
      flight waits briefly for that cache to land; a true cold request starts a
      delayed background refresh and returns a degraded warming shell
      immediately.
    - Guarantee: Missing subsystems degrade inside `_compute_station_launcher_payload`.
      A failed background refresh is logged and does not evict the stale copy,
      so the surface stays usable even when a subsystem is misbehaving.
    """
    cache_key = str(REPO_ROOT.resolve())
    now = time.monotonic()
    wait_event: threading.Event | None = None
    with _STATION_LAUNCHER_CACHE_LOCK:
        cached = _STATION_LAUNCHER_CACHE.get(cache_key)
        if cached:
            fresh = now - cached[0] <= _STATION_LAUNCHER_CACHE_TTL_S
            payload_copy = copy.deepcopy(cached[1])
            if fresh:
                return payload_copy
            # Stale: single-flight background refresh, return stale copy now.
            if cache_key not in _STATION_LAUNCHER_REFRESH_IN_FLIGHT:
                event = threading.Event()
                _STATION_LAUNCHER_REFRESH_IN_FLIGHT[cache_key] = event
                threading.Thread(
                    target=_station_launcher_background_refresh,
                    args=(cache_key, event),
                    name="station-launcher-refresh",
                    daemon=True,
                ).start()
            return payload_copy
        # Cache empty. If a prewarm/refresh is already building it, wait on
        # that one build rather than racing a duplicate compute.
        wait_event = _STATION_LAUNCHER_REFRESH_IN_FLIGHT.get(cache_key)
    if wait_event is None:
        # No prewarm exists in this process. Yield a warming response before
        # the heavy builder can grab the GIL under uvicorn's single worker.
        _start_station_launcher_refresh(
            cache_key,
            delay_s=_STATION_LAUNCHER_BACKGROUND_START_DELAY_S,
        )
        return _warming_station_launcher_payload("miss")
    if wait_event is not None:
        # Bounded wait — first request blocks briefly for the prewarm thread
        # to land the cache. If it doesn't, fall back to a warming shell so
        # the operator UI gets a fast 200 instead of a stalled fetch and a
        # `LAUNCHER UNAVAILABLE` banner.
        started = time.monotonic()
        wait_event.wait(timeout=_STATION_LAUNCHER_PREWARM_WAIT_S)
        with _STATION_LAUNCHER_CACHE_LOCK:
            cached = _STATION_LAUNCHER_CACHE.get(cache_key)
            if cached:
                return copy.deepcopy(cached[1])
            still_in_flight = cache_key in _STATION_LAUNCHER_REFRESH_IN_FLIGHT
        if still_in_flight:
            elapsed = time.monotonic() - started
            logger.info(
                "station launcher returned warming shell after %.1fs (prewarm in flight)",
                elapsed,
            )
            return _warming_station_launcher_payload("miss")
        logger.info("station launcher returned warming shell after failed refresh")
        return _warming_station_launcher_payload("unavailable")


def _load_system_facts_at_a_glance() -> Dict[str, Any]:
    facts_path = REPO_ROOT / "state" / "system_atlas" / "system_facts_at_a_glance.json"
    markdown_path = REPO_ROOT / "docs" / "system_atlas" / "generated_system_facts_at_a_glance.md"
    source_refs = [
        str(facts_path.relative_to(REPO_ROOT)),
        str(markdown_path.relative_to(REPO_ROOT)),
    ]
    try:
        payload = json.loads(facts_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "schema_version": "system_facts_at_a_glance_v1",
            "status": "missing",
            "generated_at": None,
            "authority_posture": "generated_control_plane_projection_not_source_authority",
            "source_refs": source_refs,
            "summary": {},
            "facts": [],
            "error": str(exc),
        }
    if not isinstance(payload, dict):
        return {
            "schema_version": "system_facts_at_a_glance_v1",
            "status": "invalid",
            "generated_at": None,
            "authority_posture": "generated_control_plane_projection_not_source_authority",
            "source_refs": source_refs,
            "summary": {},
            "facts": [],
        }
    payload.setdefault("source_refs", source_refs)
    return payload


def _load_root_coverage_state() -> Dict[str, Any]:
    coverage_path = REPO_ROOT / "state" / "system_atlas" / "root_coverage_state.json"
    source_refs = [str(coverage_path.relative_to(REPO_ROOT))]
    try:
        payload = json.loads(coverage_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("root coverage state is not a JSON object")
        payload.setdefault("source_refs", source_refs)
        return payload
    except Exception as exc:
        try:
            from tools.meta.factory.build_root_coverage_state import build_root_coverage_state

            payload = build_root_coverage_state(REPO_ROOT, run_route_probes=False)
            payload["source_refs"] = source_refs
            payload["load_warning"] = f"served in-memory fallback after sidecar load failed: {exc}"
            return payload
        except Exception as fallback_exc:
            return {
                "schema_version": "root_coverage_state_v0",
                "status": "missing",
                "generated_at": None,
                "authority_posture": "generated_control_plane_projection_not_source_authority",
                "source_refs": source_refs,
                "branches": [],
                "doctrine_layers": [],
                "frontend_graph": {"nodes": [], "edges": []},
                "route_conflicts": [],
                "missing_branches": [],
                "evidence_gaps": [],
                "error": str(fallback_exc),
            }


_NAVIGATION_SURFACE_ALLOWLIST: dict[str, set[str]] = {
    "axiom_candidates": {"flag", "card"},
    "principles": {"cluster_flag", "flag", "card"},
    "standards": {"cluster_flag", "flag", "card"},
    "concepts": {"flag", "card"},
    "mechanisms": {"flag", "card"},
    "paper_modules": {"cluster_flag", "flag", "card"},
    "python_files": {"cluster_flag", "flag", "card"},
    "skills": {"cluster_flag", "flag", "card"},
    "task_ledger": {"cluster_flag", "flag", "card"},
}


def _load_navigation_surface(kind: str, band: str, ids: str | None = None) -> Dict[str, Any]:
    normalized_kind = str(kind or "").strip().lower().replace("-", "_").replace(" ", "_")
    normalized_band = str(band or "flag").strip().lower()
    allowed_bands = _NAVIGATION_SURFACE_ALLOWLIST.get(normalized_kind)
    if not allowed_bands:
        raise HTTPException(status_code=400, detail=f"Unsupported navigation surface kind: {kind}")
    if normalized_band not in allowed_bands:
        allowed = ", ".join(sorted(allowed_bands))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported band '{band}' for navigation surface '{normalized_kind}'. Allowed: {allowed}",
        )

    payload = build_option_surface(REPO_ROOT, normalized_kind, band=normalized_band, ids=ids)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="navigation surface builder did not return a JSON object")
    payload.setdefault("source_refs", [])
    payload["navigation_surface_request"] = {
        "kind": normalized_kind,
        "band": normalized_band,
        "ids": ids,
        "command": f"./repo-python kernel.py --option-surface {normalized_kind} --band {normalized_band}"
        + (f" --ids {ids}" if ids else ""),
        "allowed_surface": True,
    }
    return payload


def _station_launcher_background_refresh(cache_key: str, event: threading.Event) -> None:
    try:
        _compute_station_launcher_payload(cache_key=cache_key)
    except Exception as exc:
        logger.warning("station launcher background refresh failed: %s", exc)
    finally:
        with _STATION_LAUNCHER_CACHE_LOCK:
            _STATION_LAUNCHER_REFRESH_IN_FLIGHT.pop(cache_key, None)
        event.set()


def _station_alive_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _station_alive_state_label(state: str) -> str:
    labels = {
        "populated": "Populated",
        "correctly_empty": "Correctly empty",
        "blocked": "Blocked",
        "dormant": "Dormant",
        "loading": "Loading",
        "error": "Error",
    }
    return labels.get(state, state.replace("_", " ").title())


def _station_alive_state_class(state: str) -> str:
    classes = {
        "populated": "populated",
        "correctly_empty": "positive_empty",
        "blocked": "blocked",
        "dormant": "low_signal",
        "loading": "transient",
    }
    return classes.get(state, "unknown")


def _station_alive_surface(
    *,
    surface_id: str,
    label: str,
    route: str,
    state: str,
    reason: str,
    api_refs: List[str],
    metrics: Optional[Mapping[str, Any]] = None,
    summary_label: Optional[str] = None,
    command: Optional[str] = None,
    reentry_condition: Optional[str] = None,
    source_mode: str = "summary",
    payload_route: Optional[str] = None,
    what_populates: Optional[str] = None,
    action_label: Optional[str] = None,
    neighbor_routes: Optional[List[Mapping[str, str]]] = None,
) -> Dict[str, Any]:
    primary_action = None
    if action_label or command:
        primary_action = {
            "label": action_label or "Open action",
            "route": route,
            "command": command,
            "payload_route": payload_route,
        }
        if command:
            primary_action["cwd"] = str(REPO_ROOT)
    state_detail = {
        "state": state,
        "state_label": _station_alive_state_label(state),
        "state_class": _station_alive_state_class(state),
        "plain_reason": reason,
        "what_populates": what_populates,
        "primary_action": primary_action,
        "reentry_condition": reentry_condition,
        "source_mode": source_mode,
        "payload_route": payload_route,
        "api_refs": list(api_refs),
        "neighbor_routes": list(neighbor_routes or []),
    }
    row = {
        "surface_id": surface_id,
        "label": label,
        "route": route,
        "state": state,
        "reason": reason,
        "api_refs": api_refs,
        "metrics": dict(metrics or {}),
        "summary_label": summary_label,
        "command": command,
        "reentry_condition": reentry_condition,
        "source_mode": source_mode,
        "payload_route": payload_route,
        "state_detail": state_detail,
    }
    return row


def _station_alive_cockpit_payload(
    *,
    world: Mapping[str, Any],
    active_phase: Mapping[str, Any],
    approvals: Mapping[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []

    try:
        demo_projection = _demo_take_projection_module()
        build_summary = getattr(demo_projection, "build_take_summary", None)
        if callable(build_summary):
            demo_payload = build_summary(repo_root=REPO_ROOT, mode="calibration")
            demo_source_mode = "count_and_latest_only"
        else:
            demo_payload = demo_projection.build_take_cards(
                repo_root=REPO_ROOT,
                mode="calibration",
                limit=1,
            )
            demo_source_mode = "legacy_card_fallback"
        demo_count = _station_alive_int(
            demo_payload.get("count"),
            default=len(demo_payload.get("rows") or []),
        )
        demo_latest = demo_payload.get("latest") if isinstance(demo_payload.get("latest"), Mapping) else {}
        demo_metrics: Dict[str, Any] = {"take_count": demo_count}
        if demo_latest:
            demo_metrics["latest_take_id"] = demo_latest.get("take_id")
            demo_metrics["latest_status"] = demo_latest.get("status")
        rows.append(
            _station_alive_surface(
                surface_id="demo_takes",
                label="Demo takes",
                route="/station/demo-takes",
                state="populated" if demo_count > 0 else "dormant",
                reason=(
                    "Backend has indexed take packages."
                    if demo_count > 0
                    else "No take packages are indexed by the demo-take projection."
                ),
                api_refs=["GET /api/demo-takes", "GET /api/demo-takes/frontend-snapshot"],
                metrics=demo_metrics,
                summary_label=f"takes {demo_count}",
                command=(
                    None
                    if demo_count > 0
                    else "POST /api/demo-takes/actions/fake-lifecycle"
                ),
                reentry_condition=(
                    None
                    if demo_count > 0
                    else "take_count becomes greater than zero or an explicit demo lifecycle receipt exists"
                ),
                source_mode=demo_source_mode,
                payload_route="/api/demo-takes/frontend-snapshot",
                what_populates="Take packages under state/dissemination/demo_takes or the demo lifecycle action.",
                action_label=None if demo_count > 0 else "Generate demo lifecycle",
                neighbor_routes=[
                    {"label": "Editor snapshot", "route": "/api/demo-takes/editor-snapshot"},
                ],
            )
        )
    except Exception as exc:
        logger.debug("station alive-cockpit demo-takes summary failed: %s", exc)
        rows.append(
            _station_alive_surface(
                surface_id="demo_takes",
                label="Demo takes",
                route="/station/demo-takes",
                state="blocked",
                reason=f"Demo-take projection failed: {type(exc).__name__}",
                api_refs=["GET /api/demo-takes"],
                summary_label="blocked",
                reentry_condition="demo-take projection route returns a 200 summary",
                source_mode="count_and_latest_only",
                payload_route="/api/demo-takes/frontend-snapshot",
                what_populates="The demo-take projection must return its count/latest summary.",
                action_label="Retry demo-take summary",
            )
        )

    try:
        imaginations = world_model_loader.load_imaginations_snapshot(REPO_ROOT)
        imagination_summary = imaginations.get("summary") if isinstance(imaginations, Mapping) else {}
        imagination_count = _station_alive_int(
            (imagination_summary or {}).get("imagination_count"),
            default=len(imaginations.get("rows") or []) if isinstance(imaginations, Mapping) else 0,
        )
        rows.append(
            _station_alive_surface(
                surface_id="imaginations",
                label="Imaginations",
                route="/station/imaginations",
                state="populated" if imagination_count > 0 else "dormant",
                reason=(
                    "Doctrine imagination index is populated."
                    if imagination_count > 0
                    else "Imagination index returned no rows."
                ),
                api_refs=["GET /api/imaginations"],
                metrics={"imagination_count": imagination_count},
                summary_label=f"items {imagination_count}",
                reentry_condition=(
                    None
                    if imagination_count > 0
                    else "imaginations index contains at least one row"
                ),
                source_mode="summary_snapshot",
                payload_route="/api/imaginations",
                what_populates="Rows in the doctrine imagination index.",
                action_label=None if imagination_count > 0 else "Populate imaginations index",
            )
        )
    except Exception as exc:
        logger.debug("station alive-cockpit imaginations summary failed: %s", exc)
        rows.append(
            _station_alive_surface(
                surface_id="imaginations",
                label="Imaginations",
                route="/station/imaginations",
                state="blocked",
                reason=f"Imaginations snapshot failed: {type(exc).__name__}",
                api_refs=["GET /api/imaginations"],
                summary_label="blocked",
                reentry_condition="imaginations snapshot route returns a 200 summary",
                source_mode="summary_snapshot",
                payload_route="/api/imaginations",
                what_populates="The imagination snapshot loader must return its summary rows.",
                action_label="Retry imaginations summary",
            )
        )

    market_feeds = world.get("market_feeds") if isinstance(world.get("market_feeds"), Mapping) else {}
    market_summary = market_feeds.get("summary") if isinstance(market_feeds, Mapping) else {}
    market_ready_runs = _station_alive_int((market_summary or {}).get("ready_runs"))
    market_latest_ready = _station_alive_int((market_summary or {}).get("latest_ready_count"))
    market_feed_runs = _station_alive_int((market_summary or {}).get("feed_runs"))
    market_blockers = _station_alive_int((market_summary or {}).get("latest_blocker_count"))
    if market_ready_runs > 0 or market_latest_ready > 0:
        market_state = "populated"
        market_reason = "Latest market/finance feed read model is ready."
    elif market_blockers > 0 or market_feed_runs > 0:
        market_state = "blocked"
        market_reason = "Market/finance feed runs exist but no ready feed read model is projected."
    else:
        market_state = "dormant"
        market_reason = "No market/finance feed runs are projected yet."
    rows.append(
        _station_alive_surface(
            surface_id="finance_data",
            label="Finance data",
            route="/station/data",
            state=market_state,
            reason=market_reason,
            api_refs=["GET /api/lobby", "GET /api/candidates?has_feeds=true", "GET /api/market/intelligence/latest"],
            metrics={
                "feed_runs": market_feed_runs,
                "ready_runs": market_ready_runs,
                "latest_ready_count": market_latest_ready,
                "latest_blocker_count": market_blockers,
            },
            summary_label=f"ready {market_ready_runs}/{market_feed_runs}",
            reentry_condition=(
                None
                if market_state == "populated"
                else "market feed summary reports ready_runs or latest_ready_count greater than zero"
            ),
            source_mode="world_model_summary_reused",
            payload_route="/api/market/intelligence/latest",
            what_populates="A market feed bundle and ready finance read model in the world-model snapshot.",
            action_label=None if market_state == "populated" else "Run market feed pipeline",
            neighbor_routes=[
                {"label": "Launchpad", "route": "/launchpad"},
                {"label": "Market intelligence", "route": "/station/market-intelligence"},
            ],
        )
    )

    phase_ref = (
        str(active_phase.get("phase_id") or active_phase.get("phase_number") or "").strip()
        or "__active__"
    )
    try:
        phase_cycles = world_model_loader.list_phase_cycles(REPO_ROOT, phase_ref)
    except Exception as exc:
        logger.debug("station alive-cockpit phase cycle summary failed: %s", exc)
        phase_cycles = []
    phase_cycle_count = len(phase_cycles or [])
    rows.append(
        _station_alive_surface(
            surface_id="phase_cycles",
            label="Phase cycles",
            route=f"/station/phase/{phase_ref}",
            state="populated" if phase_cycle_count > 0 else "dormant",
            reason=(
                "Active phase has recorded cycle artifacts."
                if phase_cycle_count > 0
                else "Active phase has no recorded cycle artifacts yet."
            ),
            api_refs=[f"GET /api/world-model/phase/{phase_ref}/cycles"],
            metrics={"phase_ref": phase_ref, "cycle_count": phase_cycle_count},
            summary_label=f"{phase_ref} · cycles {phase_cycle_count}",
            command="python3 pipeline_advance.py --check-responses",
            reentry_condition=(
                None
                if phase_cycle_count > 0
                else "cycle_count becomes greater than zero for the active phase"
            ),
            source_mode="cycle_index_count",
            payload_route=f"/api/world-model/phase/{phase_ref}/cycles",
            what_populates="Cycle artifacts written by the active phase controller.",
            action_label="Check phase responses",
            neighbor_routes=[
                {"label": "Timeline", "route": "/station/timeline"},
                {"label": "Launchpad", "route": "/launchpad"},
            ],
        )
    )

    lab = world.get("lab_oracle_evolve") if isinstance(world.get("lab_oracle_evolve"), Mapping) else {}
    lab_summary = lab.get("summary") if isinstance(lab, Mapping) else {}
    lab_total_runs = _station_alive_int((lab_summary or {}).get("total_runs"))
    lab_feed_runs = _station_alive_int((lab_summary or {}).get("feed_runs"))
    lab_feed_ready = _station_alive_int((lab_summary or {}).get("feed_ready_runs"))
    lab_oracle_runs = _station_alive_int((lab_summary or {}).get("oracle_runs"))
    lab_evolve_ready = _station_alive_int((lab_summary or {}).get("evolve_ready_runs"))
    lab_evolve_blocked = _station_alive_int((lab_summary or {}).get("evolve_blocked_runs"))
    lab_pair_ready = _station_alive_int((lab_summary or {}).get("pair_ready"))
    lab_pair_blocked = _station_alive_int((lab_summary or {}).get("pair_blocked"))
    if lab_pair_ready > 0 or lab_evolve_ready > 0 or lab_oracle_runs > 0:
        lab_state = "populated"
        lab_reason = "Lab/Oracle/Evolve has oracle or ready evolve artifacts."
    elif lab_evolve_blocked > 0 or lab_pair_blocked > 0 or (lab_feed_runs > 0 and lab_feed_ready == 0):
        lab_state = "blocked"
        lab_reason = "Lab/Oracle/Evolve has feed or evolve artifacts but readiness is blocked."
    elif lab_total_runs > 0:
        lab_state = "dormant"
        lab_reason = "Lab/Oracle/Evolve has runs but no ready oracle/evolve pair yet."
    else:
        lab_state = "dormant"
        lab_reason = "No Lab/Oracle/Evolve runs are projected yet."
    rows.append(
        _station_alive_surface(
            surface_id="lab_oracle_evolve",
            label="Lab / Oracle / Evolve",
            route="/station/lab-oracle-evolve",
            state=lab_state,
            reason=lab_reason,
            api_refs=["GET /api/world-model/snapshot"],
            metrics={
                "total_runs": lab_total_runs,
                "feed_runs": lab_feed_runs,
                "feed_ready_runs": lab_feed_ready,
                "oracle_runs": lab_oracle_runs,
                "evolve_ready_runs": lab_evolve_ready,
                "evolve_blocked_runs": lab_evolve_blocked,
                "pair_ready": lab_pair_ready,
                "pair_blocked": lab_pair_blocked,
            },
            summary_label=f"oracle {lab_oracle_runs} · pair {lab_pair_ready}/{lab_pair_blocked}",
            reentry_condition=(
                None
                if lab_state == "populated"
                else "lab_oracle_evolve summary reports oracle_runs, pair_ready, or evolve_ready_runs greater than zero"
            ),
            source_mode="world_model_summary_reused",
            payload_route="/api/world-model/snapshot",
            what_populates="A market-feed bundle, CP2 prediction artifact, Oracle run, and Evolve readiness pair.",
            action_label=None if lab_state == "populated" else "Open Lab / Oracle operations",
            neighbor_routes=[
                {"label": "Launchpad", "route": "/launchpad"},
                {"label": "Finance data", "route": "/station/data"},
            ],
        )
    )

    approval_count = _station_alive_int(approvals.get("total_pending"))
    rows.append(
        _station_alive_surface(
            surface_id="approvals",
            label="Approvals",
            route="/station/approvals",
            state="correctly_empty" if approval_count == 0 else "populated",
            reason=(
                "Approval inbox is clear."
                if approval_count == 0
                else "Approval inbox has pending operator rows."
            ),
            api_refs=["GET /api/approvals"],
            metrics={"total_pending": approval_count},
            summary_label=f"pending {approval_count}",
            reentry_condition=(
                None
                if approval_count == 0
                else "pending approvals are decided or intentionally deferred"
            ),
            source_mode="world_model_summary_reused",
            payload_route="/api/approvals",
            what_populates="Pending approval rows from campaigns, orchestration gates, Type A seats, or factory apply review.",
            action_label=None if approval_count == 0 else "Open approval inbox",
        )
    )

    state_counts: Dict[str, int] = {}
    for row in rows:
        state = str(row.get("state") or "unknown")
        state_counts[state] = state_counts.get(state, 0) + 1
    status = "ready"
    if state_counts.get("blocked"):
        status = "blocked"
    elif state_counts.get("dormant"):
        status = "mixed"

    return {
        "schema": "station_alive_cockpit_v1",
        "generated_at": generated_at,
        "status": status,
        "state_counts": state_counts,
        "rows": rows,
        "source_refs": [
            "tools/meta/dissemination/demo_take_projection.py::build_take_summary",
            "codex/doctrine/imaginations/_index.json",
            "system/server/world_model.py::load_lab_oracle_evolve_snapshot",
            "system/server/world_model.py::list_phase_cycles",
            "system.server.world_model.list_approvals",
        ],
    }


def _compute_station_launcher_payload(*, cache_key: str | None = None) -> Dict[str, Any]:
    if cache_key is None:
        cache_key = str(REPO_ROOT.resolve())
    generated_at = datetime.now(timezone.utc).isoformat()

    world: Dict[str, Any] = {}
    lobby_payload: Dict[str, Any] = {}
    bridge_diag: Dict[str, Any] = {}
    run_status: Dict[str, Any] = {}
    observe_runtime: Dict[str, Any] = {}
    raw_seed_pipeline: Dict[str, Any] = {}
    host_agents: Dict[str, Any] = {}
    navigation_freshness: Dict[str, Any] = {}
    system_facts: Dict[str, Any] = {}
    overnight_chain: Dict[str, Any] = {}
    overnight_queue: Dict[str, Any] = {}
    operations_payload: Dict[str, Any] = {}
    approvals: Dict[str, Any] = {}

    try:
        world = world_model_loader.load_world_model_snapshot(REPO_ROOT) or {}
    except Exception as exc:
        logger.warning("station launcher world-model load failed: %s", exc)
    approvals = dict(world.get("approvals") or {})
    host_agents = dict(world.get("host_agents") or {})
    navigation_freshness = dict(world.get("navigation_freshness") or {})
    attention = _station_attention_brief(world)
    try:
        lobby = translator.scan_lobby()
        lobby_payload = lobby.model_dump(mode="json") if hasattr(lobby, "model_dump") else dict(lobby or {})
    except Exception as exc:
        logger.warning("station launcher lobby load failed: %s", exc)
    try:
        bridge_diag = _bridge_diagnostics_payload(limit=4) or {}
    except Exception as exc:
        logger.warning("station launcher bridge diagnostics failed: %s", exc)
    try:
        run_status = dict(session_manager.get_active_run_status() or {})
    except Exception as exc:
        logger.warning("station launcher run-status load failed: %s", exc)
    try:
        session_status = meta_session_controller.get_status()
        session_state = (
            session_status.state.value
            if hasattr(session_status.state, "value")
            else str(session_status.state)
        )
        runtime_status = session_status if session_state not in {"idle"} else _grouped_runtime_status()
        observe_runtime = runtime_status.model_dump(mode="json")
    except Exception as exc:
        logger.warning("station launcher observe-runtime load failed: %s", exc)
    try:
        raw_seed_pipeline = world_model_loader.load_raw_seed_pipeline_snapshot(
            REPO_ROOT,
            family_dir=(world.get("family") or {}).get("family_dir"),
            family_number=(world.get("family") or {}).get("family_number"),
        ) or {}
    except Exception as exc:
        logger.warning("station launcher raw-seed pipeline load failed: %s", exc)
    try:
        system_facts = _load_system_facts_at_a_glance()
    except Exception as exc:
        logger.warning("station launcher system-facts load failed: %s", exc)
    if not host_agents:
        try:
            host_agents = world_model_loader.load_host_agent_external_snapshot(REPO_ROOT) or {}
        except Exception as exc:
            logger.warning("station launcher host-agent load failed: %s", exc)
    try:
        overnight_chain = world_model_loader.load_overnight_chain_snapshot(
            REPO_ROOT,
            family_number=(world.get("family") or {}).get("family_number"),
        ) or {}
    except Exception as exc:
        logger.warning("station launcher overnight-chain load failed: %s", exc)
    try:
        overnight_queue = world_model_loader.load_overnight_queue_snapshot(REPO_ROOT) or {}
    except Exception as exc:
        logger.warning("station launcher overnight-queue load failed: %s", exc)
    operations_payload = _peek_station_cache(
        _STATION_LAUNCHER_OPERATIONS_CACHE,
        _STATION_LAUNCHER_OPERATIONS_CACHE_LOCK,
        ttl_s=_STATION_LAUNCHER_AUX_CACHE_TTL_S,
    ) or {"operations": []}

    family = dict(world.get("family") or {})
    active_phase = dict(attention.get("active_phase") or world.get("active_phase") or {})
    orchestration = dict(world.get("orchestration") or {})
    orchestration_freshness = dict(
        (world.get("freshness") or {}).get("orchestration")
        or world_model_loader.compute_freshness(orchestration.get("updated_at"))
    )
    current_driver = dict(attention.get("current_driver") or {})
    next_handoff = dict(attention.get("next_handoff") or {})
    family_number = str(raw_seed_pipeline.get("family_number") or family.get("family_number") or "09")

    missions = list(lobby_payload.get("missions") or [])
    bridge_gate_alive = bool((lobby_payload.get("bridge_status") or {}).get("alive"))
    blocked_missions = [
        m for m in missions
        if str(m.get("status") or "") == "BROKEN"
        or (str(m.get("status") or "") == "REQUIRES_BRIDGE" and not bridge_gate_alive)
    ]

    bridge_providers = bridge_diag.get("providers") if isinstance(bridge_diag.get("providers"), dict) else {}
    live_provider_count = sum(
        1
        for provider in bridge_providers.values()
        if isinstance(provider, dict) and provider.get("stale") is not True
    )

    observe_state = str(observe_runtime.get("state") or "idle")
    observe_hot = observe_state not in {"idle", "completed", "error", "aborted"}
    gate_reason = (
        str(orchestration.get("gate_reason") or active_phase.get("gate_reason") or "").strip()
        or None
    )
    approval_count = int(approvals.get("total_pending") or 0)
    approval_top_records = [
        record
        for record in list(approvals.get("top_records") or [])
        if isinstance(record, Mapping)
    ]
    stale_navigation_sources = int(navigation_freshness.get("stale_source_count") or 0)
    stale_navigation_rows = int(navigation_freshness.get("stale_or_missing_row_count") or 0)
    navigation_top_source = str(navigation_freshness.get("top_source_kind") or "").strip()

    alerts: List[Dict[str, Any]] = []
    if approval_count > 0:
        top_record = approval_top_records[0] if approval_top_records else {}
        top_action_kind = str(top_record.get("action_kind") or "").strip()
        top_severity = str(top_record.get("severity") or "").strip().upper()
        alerts.append(
            {
                "id": "approval_inbox",
                "tone": "block" if top_action_kind == "decide" and top_severity in {"P0", "P1"} else "warn",
                "label": "Approvals pending",
                "detail": (
                    str(top_record.get("title") or "").strip()
                    or f"{approval_count} approval row(s) need operator attention"
                ),
                "command": None,
            }
        )
    if gate_reason:
        gate_detail = gate_reason.replace("_", " ")
        if not approval_count:
            alerts.append(
                {
                    "id": "gate",
                    "tone": "block",
                    "label": "Gate active",
                    "detail": gate_detail,
                    "command": str(orchestration.get("command") or "").strip() or None,
                }
            )
        elif not any(
            str(record.get("source_kind") or "").strip() == "orchestration_gate"
            for record in approval_top_records
        ):
            alerts.append(
                {
                    "id": "gate",
                    "tone": "block",
                    "label": "Gate active",
                    "detail": gate_detail,
                    "command": str(orchestration.get("command") or "").strip() or None,
                }
            )

    if orchestration_freshness.get("tone") == "expired":
        alerts.append(
            {
                "id": "orchestration_stale",
                "tone": "warn",
                "label": "Control plane stale",
                "detail": orchestration_freshness.get("label") or "unknown age",
                "command": str(orchestration.get("next_command") or "").strip() or None,
            }
        )
    if blocked_missions:
        alerts.append(
            {
                "id": "missions_blocked",
                "tone": "warn",
                "label": "Blocked missions",
                "detail": f"{len(blocked_missions)} blocked",
                "command": None,
            }
        )
    if not bool(bridge_diag.get("browser_running")) or not bool(bridge_diag.get("cdp_reachable")):
        alerts.append(
            {
                "id": "bridge",
                "tone": "warn",
                "label": "Bridge degraded",
                "detail": str(bridge_diag.get("error") or "CDP unreachable"),
                "command": None,
            }
        )
    work_ledger_attention = dict((attention.get("work_ledger") or {}))
    work_ledger_counts = work_ledger_attention.get("counts") or {}
    if int(work_ledger_counts.get("stale_sessions") or 0) > 0:
        alerts.append(
            {
                "id": "work_ledger_stale",
                "tone": "warn",
                "label": "Work ledger append missing",
                "detail": (
                    f"{work_ledger_counts.get('stale_sessions')} stale session(s) "
                    "ended without a work-ledger append"
                ),
                "command": "./repo-python tools/meta/factory/work_ledger.py project --all",
            }
        )
    if observe_hot:
        alerts.append(
            {
                "id": "observe_runtime",
                "tone": "info",
                "label": "Observe runtime active",
                "detail": f"{observe_runtime.get('completed_groups') or 0}/{observe_runtime.get('total_groups') or 0} groups",
                "command": None,
            }
        )
    if stale_navigation_sources > 0:
        alerts.append(
            {
                "id": "navigation_freshness",
                "tone": "warn",
                "label": "Navigation embeddings stale",
                "detail": (
                    f"{stale_navigation_sources} source kind(s) / "
                    f"{stale_navigation_rows} stale or missing row(s)"
                ),
                "command": _render_launchable_command(
                    "navigator_refresh",
                    parameters={"kind": navigation_top_source or "all"},
                ),
            }
        )
    if int(raw_seed_pipeline.get("fresh_pending_bins") or 0) > 0:
        alerts.append(
            {
                "id": "raw_seed_sync_handoff",
                "tone": "warn",
                "label": "Fresh raw-seed handoff ready",
                "detail": f"{raw_seed_pipeline.get('fresh_pending_bins')} fresh bin(s) are ready for post-sync handoff",
                "command": _render_launchable_command(
                    "raw_seed_sync_handoff_launch",
                    parameters={"family": family_number, "provider": "chatgpt"},
                ),
            }
        )
    elif int(raw_seed_pipeline.get("atomization_pending_paragraphs") or 0) > 0:
        alerts.append(
            {
                "id": "raw_seed_atomization_backlog",
                "tone": "warn",
                "label": "Raw-seed atomization pending",
                "detail": (
                    f"{raw_seed_pipeline.get('atomization_pending_paragraphs')} paragraphs remain pending or invalidated "
                    "for atomization"
                ),
                "command": _render_launchable_command(
                    "raw_seed_atomize_cycle",
                    parameters={
                        "family": family_number,
                        "provider": "chatgpt",
                        "cohort_size": 12,
                        "wave_width": 3,
                        "selection_mode": "fresh_first",
                    },
                ),
            }
        )
    if int(raw_seed_pipeline.get("review_queue_entries") or 0) > 0:
        alerts.append(
            {
                "id": "raw_seed_routing_review",
                "tone": "info",
                "label": "Routing review queued",
                "detail": (
                    f"{raw_seed_pipeline.get('review_queue_bins') or 0} bin envelope(s) / "
                    f"{raw_seed_pipeline.get('review_queue_entries')} doctrine proposal(s) await controller review"
                ),
                "command": _render_launchable_command(
                    "raw_seed_route_review",
                    parameters={
                        "family": family_number,
                        "provider": "chatgpt",
                        "cohort_size": 10,
                        "wave_width": 3,
                        "selection_mode": "fresh_first",
                    },
                ),
            }
        )
    overnight_status = str(overnight_chain.get("terminal_status") or "").strip()
    overnight_chain_provider_wait = (
        dict(overnight_chain.get("provider_wait"))
        if isinstance(overnight_chain.get("provider_wait"), dict)
        else None
    )
    overnight_queue_provider_wait = (
        dict(overnight_queue.get("provider_wait"))
        if isinstance(overnight_queue.get("provider_wait"), dict)
        else None
    )
    queue_wait_tracks_active_chain = (
        bool(overnight_queue_provider_wait)
        and str(overnight_queue_provider_wait.get("source") or "").strip() == "child_chain"
        and str(overnight_queue_provider_wait.get("chain_id") or "").strip()
        == str(overnight_chain.get("chain_id") or "").strip()
    )
    if overnight_chain_provider_wait and overnight_status == "running" and not queue_wait_tracks_active_chain:
        chain_wait_target = (
            overnight_chain_provider_wait.get("step_id")
            or (overnight_chain.get("progress") or {}).get("current_step_id")
            or "current step"
        )
        chain_wait_reason = (
            overnight_chain_provider_wait.get("reason")
            or overnight_chain_provider_wait.get("kind")
            or "provider budget wait"
        )
        chain_wait_seconds = overnight_chain_provider_wait.get("wait_seconds")
        chain_wait_detail = f"{chain_wait_target}: {chain_wait_reason}"
        if chain_wait_seconds not in (None, ""):
            chain_wait_detail += f" ({chain_wait_seconds}s)"
        alerts.append(
            {
                "id": "overnight_chain_waiting_provider",
                "tone": "warn",
                "label": "Overnight chain waiting on provider budget",
                "detail": chain_wait_detail,
                "command": "./repo-python tools/meta/factory/overnight_chain_runner.py status --chain overnight_raw_seed_chain --family "
                + family_number,
            }
        )
    if overnight_status == "failed":
        alerts.append(
            {
                "id": "overnight_chain_failed",
                "tone": "block",
                "label": "Overnight chain failed",
                "detail": overnight_chain.get("last_error") or "Read the latest overnight-chain ledger entry.",
                "command": "./repo-python tools/meta/factory/overnight_chain_runner.py status --chain overnight_raw_seed_chain --family "
                + family_number,
            }
        )
    elif overnight_status == "graceful_stop":
        alerts.append(
            {
                "id": "overnight_chain_paused",
                "tone": "warn",
                "label": "Overnight chain paused at a seam",
                "detail": (
                    (overnight_chain.get("next_resume_seam") or {}).get("step_id")
                    or "resume available"
                ),
                "command": "./repo-python tools/meta/factory/overnight_chain_runner.py run --chain overnight_raw_seed_chain --family "
                + family_number
                + " --provider chatgpt --resume",
            }
        )
    overnight_queue_manifest = str(overnight_queue.get("manifest_path") or "").strip()
    overnight_queue_status = str(overnight_queue.get("terminal_status") or "").strip()
    if overnight_queue_status == "failed":
        alerts.append(
            {
                "id": "overnight_queue_failed",
                "tone": "block",
                "label": "Autonomy runtime failed",
                "detail": overnight_queue.get("last_error") or "Read the latest autonomy-runtime ledger entry.",
                "command": "./repo-python tools/meta/factory/overnight_chain_runner.py status --manifest "
                + overnight_queue_manifest,
            }
        )
    elif overnight_queue_status == "graceful_stop":
        alerts.append(
            {
                "id": "overnight_queue_paused",
                "tone": "warn",
                "label": "Autonomy runtime paused at an item seam",
                "detail": (
                    (overnight_queue.get("next_resume_seam") or {}).get("item_id")
                    or overnight_queue.get("next_resume_item_id")
                    or "resume available"
                ),
                "command": "./repo-python tools/meta/factory/overnight_chain_runner.py run --manifest "
                + overnight_queue_manifest
                + " --resume",
            }
        )
    if overnight_queue_provider_wait and overnight_queue_status == "running":
        queue_wait_target = (
            overnight_queue_provider_wait.get("item_id")
            or overnight_queue.get("current_item_id")
            or "current item"
        )
        queue_wait_reason = (
            overnight_queue_provider_wait.get("reason")
            or overnight_queue_provider_wait.get("kind")
            or "provider budget wait"
        )
        queue_wait_seconds = overnight_queue_provider_wait.get("wait_seconds")
        queue_wait_detail = f"{queue_wait_target}: {queue_wait_reason}"
        if overnight_queue_provider_wait.get("source") == "child_chain":
            chain_id = str(overnight_queue_provider_wait.get("chain_id") or "").strip()
            if chain_id:
                queue_wait_detail += f" via {chain_id}"
        if queue_wait_seconds not in (None, ""):
            queue_wait_detail += f" ({queue_wait_seconds}s)"
        alerts.append(
            {
                "id": "overnight_queue_waiting_provider",
                "tone": "warn",
                "label": "Autonomy runtime waiting on provider budget",
                "detail": queue_wait_detail,
                "command": "./repo-python tools/meta/factory/overnight_chain_runner.py status --manifest "
                + overnight_queue_manifest,
            }
        )

    try:
        alive_cockpit = _station_alive_cockpit_payload(
            world=world,
            active_phase=active_phase,
            approvals=approvals,
            generated_at=generated_at,
        )
    except Exception as exc:
        logger.warning("station launcher alive-cockpit summary failed: %s", exc)
        alive_cockpit = {
            "schema": "station_alive_cockpit_v1",
            "generated_at": generated_at,
            "status": "blocked",
            "state_counts": {"blocked": 1},
            "rows": [
                _station_alive_surface(
                    surface_id="alive_cockpit",
                    label="Alive cockpit",
                    route="/station",
                    state="blocked",
                    reason=f"Alive-cockpit summary failed: {type(exc).__name__}",
                    api_refs=["GET /api/station/launcher"],
                    reentry_condition="station launcher alive-cockpit helper returns without exception",
                )
            ],
        }

    payload = {
        "schema": "station_launcher_v1",
        "generated_at": generated_at,
        "family": {
            "family_id": family.get("family_id"),
            "family_number": family.get("family_number"),
            "title": family.get("title"),
        },
        "active_phase": {
            "phase_id": active_phase.get("phase_id"),
            "title": active_phase.get("title"),
            "stage": active_phase.get("stage"),
            "cycle": active_phase.get("cycle"),
            "gate_reason": active_phase.get("gate_reason"),
            "freshness": active_phase.get("freshness") or world_model_loader.compute_freshness(active_phase.get("updated_at")),
        },
        "current_driver": {
            "actor_id": current_driver.get("actor_id"),
            "driver_id": current_driver.get("driver_id"),
        },
        "next_handoff": (
            {
                "actor_id": next_handoff.get("actor_id"),
                "mode": next_handoff.get("mode"),
                "command": next_handoff.get("command"),
                "review_surface": next_handoff.get("review_surface"),
            }
            if next_handoff
            else {}
        ),
        "orchestration": {
            "gate_reason": gate_reason,
            "updated_at": orchestration.get("updated_at"),
            "freshness": orchestration_freshness,
            "active_driver": orchestration.get("active_driver"),
            "current_owner": (orchestration.get("current_owner") or {}).get("actor_id"),
            "next_command": orchestration.get("next_command"),
        },
        "missions": {
            "total": len(missions),
            "ready": len(missions) - len(blocked_missions),
            "blocked": len(blocked_missions),
            "candidates": len(lobby_payload.get("candidates") or []),
        },
        "bridge": {
            "configured": bool(bridge_diag.get("configured")),
            "browser_running": bool(bridge_diag.get("browser_running")),
            "cdp_reachable": bool(bridge_diag.get("cdp_reachable")),
            "provider_count": len(bridge_providers),
            "live_provider_count": live_provider_count,
            "debug_url": bridge_diag.get("debug_url"),
            "error": bridge_diag.get("error"),
        },
        "observe_runtime": {
            "observe_id": observe_runtime.get("observe_id"),
            "session_slug": observe_runtime.get("session_slug"),
            "state": observe_state,
            "completed_groups": observe_runtime.get("completed_groups") or 0,
            "total_groups": observe_runtime.get("total_groups") or 0,
            "provider": observe_runtime.get("provider"),
            "can_continue": bool(observe_runtime.get("can_continue")),
            "retryable_group_labels": list(observe_runtime.get("retryable_group_labels") or []),
            "latest_stable_artifact": observe_runtime.get("latest_stable_artifact"),
        },
        "raw_seed_pipeline": {
            "family_dir": raw_seed_pipeline.get("family_dir"),
            "family_number": raw_seed_pipeline.get("family_number"),
            "extracted_shards_path": raw_seed_pipeline.get("extracted_shards_path"),
            "raw_seed_shards_path": raw_seed_pipeline.get("raw_seed_shards_path"),
            "raw_seed_coverage_path": raw_seed_pipeline.get("raw_seed_coverage_path"),
            "raw_seed_coverage_enriched_path": raw_seed_pipeline.get("raw_seed_coverage_enriched_path"),
            "raw_seed_routing_review_path": raw_seed_pipeline.get("raw_seed_routing_review_path"),
            "codex_surface_queue_path": raw_seed_pipeline.get("codex_surface_queue_path"),
            "total_paragraphs": raw_seed_pipeline.get("total_paragraphs") or 0,
            "total_bins": raw_seed_pipeline.get("total_bins") or 0,
            "paragraph_level_shards": raw_seed_pipeline.get("paragraph_level_shards") or 0,
            "atomized_shards": raw_seed_pipeline.get("atomized_shards") or 0,
            "paragraphs_without_atoms": raw_seed_pipeline.get("paragraphs_without_atoms") or 0,
            "atomization_success_paragraphs": raw_seed_pipeline.get("atomization_success_paragraphs") or 0,
            "atomization_retryable_paragraphs": raw_seed_pipeline.get("atomization_retryable_paragraphs") or 0,
            "atomization_failed_paragraphs": raw_seed_pipeline.get("atomization_failed_paragraphs") or 0,
            "atomization_pending_paragraphs": raw_seed_pipeline.get("atomization_pending_paragraphs") or 0,
            "pending_routing_shards": raw_seed_pipeline.get("pending_routing_shards") or 0,
            "pending_routing_bins": raw_seed_pipeline.get("pending_routing_bins") or 0,
            "review_queue_entries": raw_seed_pipeline.get("review_queue_entries") or 0,
            "review_queue_bins": raw_seed_pipeline.get("review_queue_bins") or 0,
            "fresh_pending_bins": raw_seed_pipeline.get("fresh_pending_bins") or 0,
            "surface_queue_entries": raw_seed_pipeline.get("surface_queue_entries") or 0,
            "doctrine_with_no_provenance": raw_seed_pipeline.get("doctrine_with_no_provenance") or 0,
            "merge_candidate_count": raw_seed_pipeline.get("merge_candidate_count") or 0,
            "orphan_cluster_count": raw_seed_pipeline.get("orphan_cluster_count") or 0,
            "provider": raw_seed_pipeline.get("provider"),
            "cohort_size": raw_seed_pipeline.get("cohort_size") or 0,
            "wave_width_requested": raw_seed_pipeline.get("wave_width_requested"),
            "wave_width_effective": raw_seed_pipeline.get("wave_width_effective") or 0,
            "provider_ceiling": raw_seed_pipeline.get("provider_ceiling") or 0,
            "queue_depth": raw_seed_pipeline.get("queue_depth") or 0,
            "effective_active_workers": raw_seed_pipeline.get("effective_active_workers") or 0,
            "safe_parallelism": raw_seed_pipeline.get("safe_parallelism") or 0,
            "last_updated": raw_seed_pipeline.get("last_updated"),
        },
        "navigation_freshness": navigation_freshness,
        "system_facts": system_facts,
        "host_agents": host_agents,
        "meta_missions": {
            "generated_at": generated_at,
            "totals": {},
            "missions": [],
            "urgent": [],
        },
        "approvals": {
            "total_pending": approval_count,
            "source_kind_counts": dict(approvals.get("source_kind_counts") or {}),
            "action_kind_counts": dict(approvals.get("action_kind_counts") or {}),
            "status_counts": dict(approvals.get("status_counts") or {}),
            "top_records": approval_top_records[:3],
        },
        "alive_cockpit": alive_cockpit,
        "overnight_chain": {
            "chain_id": overnight_chain.get("chain_id"),
            "chain_run_id": overnight_chain.get("chain_run_id"),
            "terminal_status": overnight_chain.get("terminal_status"),
            "is_running": bool(overnight_chain.get("is_running")),
            "pid": overnight_chain.get("pid"),
            "log_path": overnight_chain.get("log_path"),
            "state_path": overnight_chain.get("state_path"),
            "ledger_path": overnight_chain.get("ledger_path"),
            "stop_flag_path": overnight_chain.get("stop_flag_path"),
            "last_updated": overnight_chain.get("last_updated"),
            "progress": dict(overnight_chain.get("progress") or {}),
            "next_resume_seam": dict(overnight_chain.get("next_resume_seam") or {}) or None,
            "provider_wait": overnight_chain_provider_wait,
            "last_error": overnight_chain.get("last_error"),
        },
        "overnight_queue": {
            "queue_id": overnight_queue.get("queue_id"),
            "queue_run_id": overnight_queue.get("queue_run_id"),
            "manifest_path": overnight_queue.get("manifest_path"),
            "terminal_status": overnight_queue.get("terminal_status"),
            "is_running": bool(overnight_queue.get("is_running")),
            "pid": overnight_queue.get("pid"),
            "log_path": overnight_queue.get("log_path"),
            "state_path": overnight_queue.get("state_path"),
            "ledger_path": overnight_queue.get("ledger_path"),
            "stop_flag_path": overnight_queue.get("stop_flag_path"),
            "last_updated": overnight_queue.get("last_updated"),
            "progress": dict(overnight_queue.get("progress") or {}),
            "current_item_id": overnight_queue.get("current_item_id"),
            "current_item_index": overnight_queue.get("current_item_index"),
            "total_items": overnight_queue.get("total_items"),
            "next_resume_item_id": overnight_queue.get("next_resume_item_id"),
            "next_resume_item_index": overnight_queue.get("next_resume_item_index"),
            "next_resume_seam": dict(overnight_queue.get("next_resume_seam") or {}) or None,
            "artifact_refs": list(overnight_queue.get("artifact_refs") or []),
            "provider_wait": overnight_queue_provider_wait,
            "last_error": overnight_queue.get("last_error"),
        },
        "autonomy_runtime": {
            "queue_id": overnight_queue.get("queue_id"),
            "queue_run_id": overnight_queue.get("queue_run_id"),
            "manifest_path": overnight_queue.get("manifest_path"),
            "terminal_status": overnight_queue.get("terminal_status"),
            "is_running": bool(overnight_queue.get("is_running")),
            "pid": overnight_queue.get("pid"),
            "log_path": overnight_queue.get("log_path"),
            "state_path": overnight_queue.get("state_path"),
            "ledger_path": overnight_queue.get("ledger_path"),
            "stop_flag_path": overnight_queue.get("stop_flag_path"),
            "last_updated": overnight_queue.get("last_updated"),
            "progress": dict(overnight_queue.get("progress") or {}),
            "current_item_id": overnight_queue.get("current_item_id"),
            "current_item_index": overnight_queue.get("current_item_index"),
            "total_items": overnight_queue.get("total_items"),
            "next_resume_item_id": overnight_queue.get("next_resume_item_id"),
            "next_resume_item_index": overnight_queue.get("next_resume_item_index"),
            "next_resume_seam": dict(overnight_queue.get("next_resume_seam") or {}) or None,
            "artifact_refs": list(overnight_queue.get("artifact_refs") or []),
            "provider_wait": overnight_queue_provider_wait,
            "last_error": overnight_queue.get("last_error"),
        },
        "run": {
            "is_running": bool(run_status.get("is_running")),
            "active_run_id": run_status.get("active_run_id"),
            "active_mission": run_status.get("active_mission"),
            "recovered_from_disk": bool(run_status.get("recovered_from_disk")),
            "recovered_run_id": run_status.get("recovered_run_id"),
            "status": run_status.get("status"),
        },
        "alerts": alerts,
        "operations": [
            {
                "operation_id": op.get("operation_id"),
                "label": op.get("label"),
                "kicker": op.get("kicker"),
                "description_short": op.get("description_short"),
                "command": op.get("command"),
                "parameters_schema": dict(op.get("parameters_schema") or {}),
                "dispatch_policy": dict(op.get("dispatch_policy") or {}),
                "ui_group": op.get("ui_group"),
                "execution_mode": op.get("execution_mode") or "sync",
                "principle_refs": list(op.get("principle_refs") or []),
                "runtime_attention": dict(op.get("runtime_attention") or {}),
            }
            for op in [
                op
                for op in list(operations_payload.get("operations") or [])
                if isinstance(op, dict)
            ]
        ],
    }
    with _STATION_LAUNCHER_CACHE_LOCK:
        _STATION_LAUNCHER_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(payload))
    return payload


def _zenith_runtime_payload() -> Dict[str, Any]:
    try:
        server_log_rel = str(LOG_PATH.relative_to(REPO_ROOT))
    except ValueError:
        server_log_rel = str(LOG_PATH)
    return zenith_runtime_loader.load_runtime_snapshot(
        REPO_ROOT,
        server_log_rel=server_log_rel,
    )


@app.get("/api/zenith/health", response_model=ZenithHealthResponse)
def zenith_health():
    """
    [ACTION]
    - Teleology: Give Zenith.app a cheap readiness check so startup polling
      does not repeatedly build the full runtime snapshot.
    """
    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/zenith/runtime", response_model=ZenithRuntimeSnapshot)
def zenith_runtime_snapshot():
    """
    [ACTION]
    - Teleology: Expose the backend-owned runtime snapshot for Zenith.app so the
      macOS shell can render backend/helper/controller status without probing the
      repo directly from the app process.
    """
    try:
        return _zenith_runtime_payload()
    except Exception as exc:
        logger.exception("zenith runtime snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/zenith/bootstrap", response_model=ZenithBootstrapResponse)
def zenith_bootstrap_snapshot():
    """
    [ACTION]
    - Teleology: Give Zenith.app one additive bootstrap packet instead of
      multiple startup fetches, reducing client-side drift and refresh churn.
    """
    try:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "attention": _attention_snapshot_payload(),
            "station_launcher": _station_launcher_payload(),
            "runtime": _zenith_runtime_payload(),
        }
    except Exception as exc:
        logger.exception("zenith bootstrap snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/station/launcher", response_model=StationLauncherSnapshot)
def station_launcher_snapshot():
    """
    [ACTION]
    - Teleology: Serve the compact launcher/home payload for `/station`.
    - Guarantee: Returns one additive station-launcher packet that keeps the
      default home surface phase-light and operationally dense.
    """
    try:
        return _station_launcher_payload()
    except Exception as exc:
        logger.exception("station launcher snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/raw-seed/append", response_model=RawSeedAppendResponse)
def raw_seed_append(payload: RawSeedAppendRequest):
    """
    [ACTION]
    - Teleology: Give native and web operator surfaces one safe append route for
      fast raw-seed capture that still uses the kernel-owned mutation contract.
    - Mechanism: Resolve the family, snapshot existing paragraph fingerprints,
      invoke `cmd_append_raw_seed`, then infer newly added paragraph anchors from
      the refreshed raw_seed.json payload.
    - Guarantee: Returns refreshed artifact paths plus best-effort appended
      anchor ids on success; validation failures surface as HTTP 400.
    """
    family_token = str(payload.family or "__active__").strip() or "__active__"
    text = str(payload.text or "").strip()
    heading = str(payload.heading or "").strip() or None

    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    try:
        family_entry = _resolve_raw_seed_family_entry(family_token)
        family_dir = str(family_entry.get("family_dir") or "").strip()
        if not family_dir:
            raise ValueError("resolved family is missing family_dir")
        artifact_paths = _raw_seed_artifacts_for_family(family_dir)
        raw_seed_json_rel = str(artifact_paths.get("raw_seed_json_path") or "").strip()
        raw_seed_json_path = REPO_ROOT / raw_seed_json_rel if raw_seed_json_rel else None
        before_fingerprints = (
            _paragraph_fingerprint_set(raw_seed_json_path)
            if raw_seed_json_path is not None
            else set()
        )
        kernel_result = _invoke_kernel_append_raw_seed(
            family_token,
            text,
            heading=heading,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("raw-seed append failed during setup: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    if int(kernel_result.get("returncode") or 0) != 0:
        detail = (
            str(kernel_result.get("stderr") or "").strip()
            or str(kernel_result.get("error") or "").strip()
            or "raw-seed append failed"
        )
        raise HTTPException(status_code=400, detail=detail)

    appended_anchor_ids = (
        _appended_anchor_ids(raw_seed_json_path, before_fingerprints)
        if raw_seed_json_path is not None
        else []
    )

    return {
        "ok": True,
        "family": family_token,
        "heading": heading,
        "appended_anchor_ids": appended_anchor_ids,
        "artifacts": RawSeedAppendArtifacts(**artifact_paths),
        "kernel_result": kernel_result,
    }


@app.get("/api/raw-seed/families", response_model=RawSeedFamiliesResponse)
def raw_seed_families():
    return {
        "kind": "raw_seed_families",
        "families": load_raw_seed_families(repo_root=REPO_ROOT),
    }


@app.get("/api/raw-seed/{family}/assimilation", response_model=RawSeedAssimilationProjectionResponse)
def raw_seed_assimilation_projection(
    family: str,
    focus: Optional[str] = Query(None, max_length=240),
    include_graph: bool = Query(
        True,
        description="When false, return projection metadata with an empty graph so route-critical renders can fetch focused graph slices separately.",
    ),
):
    try:
        projection = build_raw_seed_assimilation_projection(
            family=family,
            repo_root=REPO_ROOT,
            include_graph=include_graph or bool(focus),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("raw-seed assimilation projection failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    if focus:
        projection["graph"] = build_raw_seed_assimilation_graph_slice(projection, focus=focus)
    return projection


@app.get(
    "/api/raw-seed/{family}/assimilation/clusters",
    response_model=List[RawSeedAssimilationClusterCard],
)
def raw_seed_assimilation_clusters(family: str):
    projection = build_raw_seed_assimilation_projection(
        family=family,
        repo_root=REPO_ROOT,
        include_graph=False,
    )
    return projection.get("clusters") or []


@app.get(
    "/api/raw-seed/{family}/assimilation/clusters/{group_id}",
    response_model=RawSeedAssimilationClusterDetailResponse,
)
def raw_seed_assimilation_cluster_detail(family: str, group_id: str):
    payload = build_raw_seed_assimilation_cluster_detail(
        family=family,
        group_id=group_id,
        repo_root=REPO_ROOT,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Cluster '{group_id}' not found")
    return payload


@app.get(
    "/api/raw-seed/{family}/assimilation/bundles",
    response_model=List[RawSeedAssimilationBundleCard],
)
def raw_seed_assimilation_bundles(family: str):
    projection = build_raw_seed_assimilation_projection(
        family=family,
        repo_root=REPO_ROOT,
        include_graph=False,
    )
    return projection.get("bundles") or []


@app.get(
    "/api/raw-seed/{family}/assimilation/bundles/{bundle_id}",
    response_model=RawSeedAssimilationBundleDetailResponse,
)
def raw_seed_assimilation_bundle_detail_route(family: str, bundle_id: str):
    payload = build_raw_seed_assimilation_bundle_detail(
        family=family,
        bundle_id=bundle_id,
        repo_root=REPO_ROOT,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Bundle '{bundle_id}' not found")
    return payload


@app.get(
    "/api/raw-seed/{family}/assimilation/implementation-gaps",
    response_model=List[RawSeedImplementationGap],
)
def raw_seed_assimilation_implementation_gaps(family: str):
    projection = build_raw_seed_assimilation_projection(
        family=family,
        repo_root=REPO_ROOT,
        include_graph=False,
    )
    return projection.get("implementation_gaps") or []


@app.get("/api/raw-seed/{family}/assimilation/graph", response_model=RawSeedAssimilationGraph)
def raw_seed_assimilation_graph(
    family: str,
    focus: Optional[str] = Query(None, max_length=240),
):
    projection = build_raw_seed_assimilation_projection(family=family, repo_root=REPO_ROOT)
    return build_raw_seed_assimilation_graph_slice(projection, focus=focus)


@app.get(
    "/api/raw-seed/{family}/shards/{shard_id}",
    response_model=RawSeedAssimilationShardDetailResponse,
)
def raw_seed_assimilation_shard_detail_route(family: str, shard_id: str):
    payload = build_raw_seed_shard_detail(family=family, shard_id=shard_id, repo_root=REPO_ROOT)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Shard '{shard_id}' not found")
    return payload


@app.get(
    "/api/raw-seed/{family}/paragraphs/{paragraph_id}",
    response_model=RawSeedAssimilationParagraphDetailResponse,
)
def raw_seed_assimilation_paragraph_detail_route(family: str, paragraph_id: str):
    payload = build_raw_seed_paragraph_detail(
        family=family,
        paragraph_id=paragraph_id,
        repo_root=REPO_ROOT,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Paragraph '{paragraph_id}' not found")
    return payload


@app.post(
    "/api/raw-seed/{family}/shards/search",
    response_model=RawSeedShardSearchResponse,
)
def raw_seed_assimilation_shard_search(
    family: str,
    payload: RawSeedShardSearchRequest,
):
    return search_raw_seed_shards(
        family=family,
        query=payload.query,
        limit=payload.limit,
        repo_root=REPO_ROOT,
    )


@app.get(
    "/api/raw-seed/{family}/assimilation/clusters/{group_id}/plan",
    response_model=RawSeedAssimilationOperationReceipt,
)
def raw_seed_assimilation_cluster_plan(family: str, group_id: str):
    started_at = datetime.now(timezone.utc).isoformat()
    before_counts = _raw_seed_assimilation_counts(family)
    command = (
        "./repo-python tools/meta/factory/raw_seed_pipeline.py "
        f"alchemy-plan --family {family} --shards-group {group_id}"
    )
    try:
        output = plan_raw_seed_alchemy(family=family, repo_root=REPO_ROOT, shards_group=group_id)
    except Exception as exc:
        finished_at = datetime.now(timezone.utc).isoformat()
        return _raw_seed_operation_receipt(
            operation="alchemy_plan",
            family=family,
            command_equivalent=command,
            started_at=started_at,
            finished_at=finished_at,
            status="failed",
            artifacts=[],
            before_counts=before_counts,
            after_counts=before_counts,
            input_payload={"group_id": group_id},
            errors=[str(exc)],
        )
    finished_at = datetime.now(timezone.utc).isoformat()
    validation_errors = list(output.get("validation_errors") or [])
    return _raw_seed_operation_receipt(
        operation="alchemy_plan",
        family=family,
        command_equivalent=command,
        started_at=started_at,
        finished_at=finished_at,
        status="failed" if validation_errors else "ok",
        artifacts=[],
        before_counts=before_counts,
        after_counts=before_counts,
        input_payload={"group_id": group_id},
        warnings=[],
        errors=validation_errors,
        output=output,
    )


@app.post(
    "/api/raw-seed/{family}/assimilation/clusters/{group_id}/run",
    response_model=RawSeedAssimilationOperationReceipt,
)
def raw_seed_assimilation_cluster_run(family: str, group_id: str):
    started_at = datetime.now(timezone.utc).isoformat()
    before_counts = _raw_seed_assimilation_counts(family)
    command = (
        "./repo-python tools/meta/factory/raw_seed_pipeline.py "
        f"alchemy-run --family {family} --shards-group {group_id}"
    )
    try:
        output = run_raw_seed_alchemy(family=family, repo_root=REPO_ROOT, shards_group=group_id)
    except Exception as exc:
        finished_at = datetime.now(timezone.utc).isoformat()
        return _raw_seed_operation_receipt(
            operation="alchemy_run",
            family=family,
            command_equivalent=command,
            started_at=started_at,
            finished_at=finished_at,
            status="failed",
            artifacts=[],
            before_counts=before_counts,
            after_counts=before_counts,
            input_payload={"group_id": group_id},
            errors=[str(exc)],
        )
    finished_at = datetime.now(timezone.utc).isoformat()
    artifacts = []
    review_path = _string(output.get("raw_seed_alchemy_review_path"))
    if review_path:
        artifacts.append(review_path)
    status_value = "ok" if bool(output.get("ok", True)) and _string(output.get("status")) != "rejected" else "failed"
    warnings = list(output.get("validation_errors") or [])
    return _raw_seed_operation_receipt(
        operation="alchemy_run",
        family=family,
        command_equivalent=command,
        started_at=started_at,
        finished_at=finished_at,
        status=status_value,
        artifacts=artifacts,
        before_counts=before_counts,
        after_counts=_raw_seed_assimilation_counts(family),
        input_payload={"group_id": group_id},
        warnings=warnings if status_value == "ok" else [],
        errors=warnings if status_value == "failed" else [],
        output=output,
    )


@app.post(
    "/api/raw-seed/{family}/assimilation/bundles/{bundle_id}/dry-run",
    response_model=RawSeedAssimilationOperationReceipt,
)
def raw_seed_assimilation_bundle_dry_run(family: str, bundle_id: str):
    started_at = datetime.now(timezone.utc).isoformat()
    before_counts = _raw_seed_assimilation_counts(family)
    command = (
        "./repo-python tools/meta/factory/raw_seed_apply_loop.py "
        f"alchemy-apply --family {family} --bundle-id {bundle_id}"
    )
    family_dir, _review_path, _review_payload, bundle = _load_alchemy_review_bundle(family, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Bundle '{bundle_id}' not found")
    output = apply_alchemy_review(
        family=family,
        repo_root=REPO_ROOT,
        bundle_id=bundle_id,
        commit=False,
    )
    finished_at = datetime.now(timezone.utc).isoformat()
    warnings = [f"Skipped {item.get('bundle_id')}: {item.get('reason')}" for item in output.get("skipped") or [] if isinstance(item, Mapping)]
    status_value = "ok" if int((output.get("summary") or {}).get("applied_bundle_count") or 0) > 0 and not warnings else "failed"
    receipt = _raw_seed_operation_receipt(
        operation="apply_alchemy_dry_run",
        family=family,
        command_equivalent=command,
        started_at=started_at,
        finished_at=finished_at,
        status=status_value,
        artifacts=[_family_raw_seed_alchemy_review_path(family_dir)],
        before_counts=before_counts,
        after_counts=before_counts,
        input_payload={"bundle_id": bundle_id},
        warnings=[] if status_value == "ok" else warnings,
        errors=[] if status_value == "ok" else warnings,
        output=output,
    )
    _persist_alchemy_dry_run_metadata(
        family=family,
        bundle_id=bundle_id,
        ok=status_value == "ok",
        receipt=receipt,
        started_at=started_at,
        finished_at=finished_at,
    )
    return receipt


@app.post(
    "/api/raw-seed/{family}/assimilation/bundles/{bundle_id}/commit",
    response_model=RawSeedAssimilationOperationReceipt,
)
def raw_seed_assimilation_bundle_commit(
    family: str,
    bundle_id: str,
    payload: RawSeedAssimilationCommitRequest,
):
    if payload.confirm is not True:
        raise HTTPException(status_code=400, detail="confirm=true is required before commit")
    family_dir, _review_path, _review_payload, bundle = _load_alchemy_review_bundle(family, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"Bundle '{bundle_id}' not found")
    current_hash = compute_bundle_hash(bundle)
    if not bool(bundle.get("last_dry_run_ok")):
        raise HTTPException(status_code=400, detail="Bundle has no successful dry-run stamp")
    if _string(bundle.get("last_dry_run_bundle_hash")) != current_hash:
        raise HTTPException(status_code=400, detail="Bundle changed since the last successful dry-run")

    started_at = datetime.now(timezone.utc).isoformat()
    before_counts = _raw_seed_assimilation_counts(family)
    command = (
        "./repo-python tools/meta/factory/raw_seed_apply_loop.py "
        f"alchemy-apply --family {family} --bundle-id {bundle_id} --commit"
    )
    output = apply_alchemy_review(
        family=family,
        repo_root=REPO_ROOT,
        bundle_id=bundle_id,
        commit=True,
    )
    finished_at = datetime.now(timezone.utc).isoformat()
    warnings = [f"Skipped {item.get('bundle_id')}: {item.get('reason')}" for item in output.get("skipped") or [] if isinstance(item, Mapping)]
    artifacts = []
    principles_path = _string(output.get("principles_path"))
    if principles_path:
        artifacts.append(principles_path)
    for item in output.get("doctrine_files_touched") or []:
        path = _string(item)
        if path and path not in artifacts:
            artifacts.append(path)
    for key in (
        "extracted_shards_path",
        "raw_seed_alchemy_review_path",
        "raw_seed_alchemy_phase_seeds_path",
        "raw_seed_coverage_path",
        "raw_seed_coverage_enriched_path",
    ):
        path = _string(output.get(key))
        if path and path not in artifacts:
            artifacts.append(path)
    status_value = "ok" if int((output.get("summary") or {}).get("applied_bundle_count") or 0) > 0 else "failed"
    return _raw_seed_operation_receipt(
        operation="apply_alchemy_commit",
        family=family,
        command_equivalent=command,
        started_at=started_at,
        finished_at=finished_at,
        status=status_value,
        artifacts=artifacts,
        before_counts=before_counts,
        after_counts=_raw_seed_assimilation_counts(family),
        input_payload={"bundle_id": bundle_id, "operator_note": payload.operator_note},
        warnings=warnings if status_value == "ok" else [],
        errors=warnings if status_value == "failed" else [],
        output=output,
    )


@app.post(
    "/api/raw-seed/{family}/assimilation/coverage/refresh",
    response_model=RawSeedAssimilationOperationReceipt,
)
def raw_seed_assimilation_coverage_refresh(family: str):
    started_at = datetime.now(timezone.utc).isoformat()
    before_counts = _raw_seed_assimilation_counts(family)
    command = (
        "./repo-python tools/meta/factory/raw_seed_apply_loop.py "
        f"coverage-enrich --family {family} --commit"
    )
    output = write_enriched_coverage(family=family, repo_root=REPO_ROOT, commit=True)
    finished_at = datetime.now(timezone.utc).isoformat()
    return _raw_seed_operation_receipt(
        operation="coverage_refresh",
        family=family,
        command_equivalent=command,
        started_at=started_at,
        finished_at=finished_at,
        status="ok",
        artifacts=[_string(output.get("enriched_coverage_path"))] if _string(output.get("enriched_coverage_path")) else [],
        before_counts=before_counts,
        after_counts=_raw_seed_assimilation_counts(family),
        output=output,
    )


@app.post("/api/hologram/slice", response_model=QueryDrivenHolographicSliceResponse)
def hologram_slice(payload: QueryDrivenHolographicSliceRequest):
    return build_query_driven_holographic_slice(
        query=payload.query,
        family=payload.family,
        focus=payload.focus,
        max_nodes=payload.max_nodes,
        repo_root=REPO_ROOT,
    )


@app.get("/api/system/registry", response_model=SystemSurfaceRegistrySummaryResponse)
def system_surface_registry_summary():
    return load_system_surface_registry(repo_root=REPO_ROOT)


@app.get("/api/system/registry/search", response_model=SystemSurfaceRegistrySearchResponse)
def system_surface_registry_search(q: str = Query(..., min_length=1, max_length=240)):
    return search_system_surface_registry(query=q, repo_root=REPO_ROOT)


@app.get(
    "/api/system/registry/node/{node_id}",
    response_model=SystemSurfaceRegistryNodeDetailResponse,
)
def system_surface_registry_node_detail_route(node_id: str):
    payload = resolve_system_surface_registry_node(node_id=node_id, repo_root=REPO_ROOT)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Registry node '{node_id}' not found")
    return payload


@app.post("/api/system/registry/rebuild", response_model=SystemSurfaceRegistryRebuildResponse)
def system_surface_registry_rebuild():
    return write_system_surface_registry(repo_root=REPO_ROOT)


# =============================================================================
# Meta-missions surface
# =============================================================================


def _launchable_operations_by_id() -> Dict[str, Dict[str, Any]]:
    try:
        payload = world_model_loader.list_launchable_operations(REPO_ROOT) or {}
    except Exception:
        return {}
    operations = payload.get("operations") if isinstance(payload.get("operations"), list) else []
    result: Dict[str, Dict[str, Any]] = {}
    for op in operations:
        if not isinstance(op, Mapping):
            continue
        operation_id = str(op.get("operation_id") or "").strip()
        if operation_id:
            result[operation_id] = dict(op)
    return result


def _render_launchable_command(
    operation_id: str,
    *,
    parameters: Optional[Mapping[str, Any]] = None,
) -> Optional[str]:
    try:
        prepared = _prepare_launch_operation(
            REPO_ROOT,
            operation_id=operation_id,
            parameters=parameters or {},
        )
    except Exception:
        return None
    return prepared.command


def _resolve_launcher_operations(
    entry: Mapping[str, Any],
    operations_by_id: Mapping[str, Mapping[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    resolved: List[Dict[str, Any]] = []
    lookup = operations_by_id or {}
    for operation_id in list(entry.get("launcher_operation_ids") or []):
        token = str(operation_id or "").strip()
        if token and isinstance(lookup.get(token), Mapping):
            resolved.append(dict(lookup[token]))
    return resolved


def _registry_entry_payload(
    entry: Mapping[str, Any],
    *,
    operations_by_id: Mapping[str, Mapping[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Coerce one raw registry entry into the MetaMissionRegistryEntry shape."""
    mission_id = str(entry.get("mission_id") or "").strip()
    title = str(entry.get("title") or mission_id).strip() or mission_id
    return {
        "mission_id": mission_id,
        "status": str(entry.get("status") or "planned"),
        "kind": entry.get("kind"),
        "pack_dir": entry.get("pack_dir"),
        "template_version": entry.get("template_version"),
        "title": title,
        "summary": entry.get("summary"),
        "skill_bundle_refs": list(entry.get("skill_bundle_refs") or []),
        "dispatch_policy_source": entry.get("dispatch_policy_source"),
        "launcher_operation_ids": list(entry.get("launcher_operation_ids") or []),
        "launcher_operations": _resolve_launcher_operations(entry, operations_by_id),
        "workspace_root": entry.get("workspace_root"),
        "runtime_root": entry.get("runtime_root"),
        "input_unit_label": entry.get("input_unit_label"),
        "supports_resume": bool(entry.get("supports_resume")),
        "runtime_surface": entry.get("runtime_surface"),
        "chain_children": list(entry.get("chain_children") or []) or None,
        "planned_pack_formalization": entry.get("planned_pack_formalization"),
    }


def _summary_row_for_entry(
    entry: Mapping[str, Any],
    *,
    operations_by_id: Mapping[str, Mapping[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Build a MetaMissionSummaryRow for one registry entry."""
    mission_id = str(entry.get("mission_id") or "").strip()
    title = str(entry.get("title") or mission_id).strip() or mission_id
    workspace_root = (
        str(entry.get("workspace_root") or "").strip()
        or f"state/meta_missions/{mission_id}"
    )
    metrics = _mmw.aggregate_metrics(REPO_ROOT, mission_id) if mission_id else {}
    recent = (
        _mmw.list_runs(REPO_ROOT, mission_id, limit=6) if mission_id else []
    )
    return {
        "mission_id": mission_id,
        "title": title,
        "kind": entry.get("kind"),
        "status": str(entry.get("status") or "planned"),
        "runtime_surface": entry.get("runtime_surface"),
        "supports_resume": bool(entry.get("supports_resume")),
        "launcher_operation_ids": list(entry.get("launcher_operation_ids") or []),
        "launcher_operations": _resolve_launcher_operations(entry, operations_by_id),
        "workspace_root": workspace_root,
        "metrics": metrics or {},
        "recent_runs": recent or [],
    }


def _build_meta_missions_index() -> Dict[str, Any]:
    try:
        payload = _mmw.load_registry(REPO_ROOT)
    except FileNotFoundError as exc:
        logger.warning("meta-mission registry missing: %s", exc)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "registry_version": None,
            "authority_anchor_std": None,
            "entries": [],
            "summaries": [],
        }
    raw_entries = [
        entry for entry in (payload.get("entries") or []) if isinstance(entry, dict)
    ]
    operations_by_id = _launchable_operations_by_id()
    entries = [
        _registry_entry_payload(entry, operations_by_id=operations_by_id)
        for entry in raw_entries
    ]
    summaries = [
        _summary_row_for_entry(entry, operations_by_id=operations_by_id)
        for entry in raw_entries
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registry_version": payload.get("registry_version"),
        "authority_anchor_std": payload.get("authority_anchor_std"),
        "entries": entries,
        "summaries": summaries,
    }


@app.get("/api/meta-missions", response_model=MetaMissionsIndexResponse)
def meta_missions_index():
    """
    [ACTION]
    - Teleology: Serve the /meta-missions list surface — registry-backed catalog
      plus per-career summaries.
    - Mechanism: SWR-cached projection over the mission registry plus launchable
      operations; per-entry payload synthesis is O(entries) and would otherwise
      run on every poll.
    - Guarantee: 200 with an envelope the UI can render even when no missions
      have runs yet; 500 only if the registry itself is unreadable.
    """
    try:
        return swr_get(
            "meta_missions_index",
            str(REPO_ROOT.resolve()),
            _build_meta_missions_index,
            ttl_s=30.0,
        )
    except Exception as exc:
        logger.exception("meta-mission registry load failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get(
    "/api/meta-missions/{mission_id}",
    response_model=MetaMissionDetailResponse,
)
def meta_mission_detail(mission_id: str):
    """
    [ACTION]
    - Teleology: Serve a single meta-mission detail packet for the /meta-missions
      detail pane.
    - Mechanism: Read the registry entry + career metrics + recent runs.
    - Guarantee: 404 when mission_id is not registered; 200 with a full detail
      envelope otherwise.
    """
    try:
        entry = _mmw.resolve_mission_entry(REPO_ROOT, mission_id)
    except Exception as exc:
        logger.exception("meta-mission detail registry read failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"mission_id {mission_id!r} is not registered",
        )

    try:
        operations_by_id = _launchable_operations_by_id()
        summary_row = _summary_row_for_entry(entry, operations_by_id=operations_by_id)
        recent = _mmw.list_runs(REPO_ROOT, mission_id, limit=20)
    except Exception as exc:
        logger.exception("meta-mission detail aggregation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entry": _registry_entry_payload(entry, operations_by_id=operations_by_id),
        "summary": summary_row,
        "recent_runs": recent or [],
    }


@app.get(
    "/api/meta-missions/{mission_id}/runs",
    response_model=MetaMissionRunsResponse,
)
def meta_mission_runs(
    mission_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_running: bool = Query(True),
):
    """
    [ACTION]
    - Teleology: Serve the paginated runs list for one meta-mission career.
    - Mechanism: Delegate to workspace_library.list_runs.
    - Guarantee: 404 when the mission_id is not registered; 200 with the
      paginated list (and the workspace-wide total count) otherwise.
    """
    try:
        entry = _mmw.resolve_mission_entry(REPO_ROOT, mission_id)
    except Exception as exc:
        logger.exception("meta-mission runs registry read failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"mission_id {mission_id!r} is not registered",
        )

    try:
        all_runs = _mmw.list_runs(
            REPO_ROOT,
            mission_id,
            include_running=include_running,
        )
        total = len(all_runs)
        sliced = all_runs[offset : offset + limit] if limit else all_runs[offset:]
    except Exception as exc:
        logger.exception("meta-mission runs list failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mission_id": mission_id,
        "total_runs": total,
        "runs": sliced,
    }


@app.get(
    "/api/meta-missions/{mission_id}/runs/{run_id}",
    response_model=MetaMissionRunDetailResponse,
)
def meta_mission_run_detail(mission_id: str, run_id: str):
    """
    [ACTION]
    - Teleology: Serve the full detail for one run (events + artifact refs).
    - Mechanism: Load run.json and read events.jsonl / artifacts.jsonl.
    - Guarantee: 404 when the mission_id is unregistered or the run is absent;
      200 with the full detail packet otherwise.
    """
    try:
        entry = _mmw.resolve_mission_entry(REPO_ROOT, mission_id)
    except Exception as exc:
        logger.exception("meta-mission run detail registry read failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"mission_id {mission_id!r} is not registered",
        )

    try:
        shape = _mmw.load_run(REPO_ROOT, mission_id, run_id)
    except Exception as exc:
        logger.exception("meta-mission run detail load failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    if shape is None:
        raise HTTPException(
            status_code=404,
            detail=f"run_id {run_id!r} not found for mission_id {mission_id!r}",
        )

    try:
        events = _mmw.read_run_events(REPO_ROOT, mission_id, run_id)
    except Exception:
        events = []
    try:
        artifacts = _mmw.read_run_artifacts(REPO_ROOT, mission_id, run_id)
    except Exception:
        artifacts = []

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mission_id": mission_id,
        "run": shape,
        "events": events,
        "artifacts": artifacts,
    }


@app.get("/api/papers", response_model=PaperModulesSnapshotResponse)
def paper_modules_snapshot():
    """
    [ACTION]
    - Teleology: Expose the freshness-aware paper-module browse surface as one
      public API payload for Station and other read-only consumers.
    - Mechanism: Delegates directly to
      `system.server.world_model.load_paper_modules_snapshot` so the shared
      paper-module runtime remains the only implementation authority.
    - Guarantee: Returns the typed projection on success; stale sidecars remain
      visible in the payload rather than being masked by the route.
    """
    try:
        return world_model_loader.load_paper_modules_snapshot(REPO_ROOT)
    except Exception as exc:
        logger.exception("Paper modules snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/world-model/papers", response_model=PaperModulesSnapshotResponse)
def world_model_papers_snapshot():
    """
    [ACTION]
    - Teleology: Expose the paper-module browse payload on the world-model route
      family so Station clients can stay grouped around one read-only namespace.
    - Mechanism: Thin alias to `/api/papers`; shared loader remains authoritative.
    - Guarantee: Returns the same payload as `/api/papers`.
    """
    return paper_modules_snapshot()


@app.get("/api/imaginations", response_model=ImaginationsSnapshotResponse)
def imaginations_snapshot():
    """
    [ACTION]
    - Teleology: Expose codex/doctrine/imaginations/_index.json + _validation_report.json
      as one read-only browse payload for `/station/imaginations` and other Station
      consumers without duplicating builder logic in the server.
    - Mechanism: Delegates to `system.server.world_model.load_imaginations_snapshot`.
      The generated index remains the only producer; this route is transport.
    - Guarantee: Returns the snapshot even when the index is missing
      (`available: false`); does not 5xx on stale or absent sidecars.
    """
    try:
        return world_model_loader.load_imaginations_snapshot(REPO_ROOT)
    except Exception as exc:
        logger.exception("Imaginations snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/world-model/imaginations", response_model=ImaginationsSnapshotResponse)
def world_model_imaginations_snapshot():
    """Thin alias for `/api/imaginations` on the world-model namespace."""
    return imaginations_snapshot()


@app.get("/api/imaginations/{id_or_slug}", response_model=ImaginationDetailResponse)
def imagination_detail(id_or_slug: str):
    """
    [ACTION]
    - Teleology: Resolve one imagination by id or slug for Station detail
      drawers and deep-link routes (`/station/imaginations/<id_or_slug>`).
    - Mechanism: Delegates to `system.server.world_model.load_imagination_detail`,
      which uses the standard option-surface adapter at band=card. Frontmatter
      projection plus body excerpts; markdown body remains on disk.
    - Guarantee: Returns 200 with `available=true` on resolution; returns 404
      with `available=false`, `missing_ids`, and a structured
      `available_imaginations` recovery list when the request does not resolve.
    """
    try:
        payload = world_model_loader.load_imagination_detail(REPO_ROOT, id_or_slug)
    except Exception as exc:
        logger.exception("Imagination detail failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    if not payload.get("available"):
        raise HTTPException(status_code=404, detail=payload)
    return payload


@app.get(
    "/api/world-model/imaginations/{id_or_slug}",
    response_model=ImaginationDetailResponse,
)
def world_model_imagination_detail(id_or_slug: str):
    """Thin alias for `/api/imaginations/{id_or_slug}` on the world-model namespace."""
    return imagination_detail(id_or_slug)


def _market_read_model_status(payload: Mapping[str, Any] | None) -> str:
    if not isinstance(payload, Mapping):
        return ""
    status = payload.get("projection_status")
    if isinstance(status, Mapping):
        return str(status.get("status") or "")
    return ""


def _market_read_model_situation_count(payload: Mapping[str, Any] | None) -> int:
    if not isinstance(payload, Mapping):
        return 0
    queue = payload.get("situation_queue")
    if not isinstance(queue, Mapping):
        return 0
    items = queue.get("items")
    return len(items) if isinstance(items, list) else 0


def _market_read_model_populated(payload: Mapping[str, Any] | None) -> bool:
    return (
        isinstance(payload, Mapping)
        and payload.get("schema_version") == "market_dashboard_read_model_v0"
        and _market_read_model_status(payload) == "in_sync"
        and _market_read_model_situation_count(payload) > 0
    )


def _latest_market_dashboard_read_model_payload() -> Dict[str, Any]:
    direct_payload = _load_latest_market_dashboard_read_model(REPO_ROOT)
    if _market_read_model_populated(direct_payload):
        return direct_payload
    try:
        snapshot = world_model_loader.load_market_feeds_snapshot(REPO_ROOT)
        payload = snapshot.get("latest_market_dashboard_read_model")
        if isinstance(payload, dict):
            return payload
    except Exception:
        logger.exception("Market feeds snapshot failed while loading market intelligence read model")
    return direct_payload


@app.get("/api/market/intelligence/latest", response_model=MarketDashboardReadModelResponse)
def market_intelligence_latest():
    """
    [ACTION]
    - Teleology: Serve the backend-owned market dashboard read model as the
      stable contract a future frontend can consume without inventing finance
      semantics.
    - Mechanism: Reads the generated sidecar through the market-feeds
      world-model path when available; missing/stale projections return
      structured status instead of crashing.
    - Guarantee: No frontend layout and no trading recommendation action is
      computed by the route.
    """
    return _latest_market_dashboard_read_model_payload()


@app.get("/api/market/intelligence/runs/{run_id}", response_model=MarketDashboardReadModelResponse)
def market_intelligence_run(run_id: str):
    """
    [ACTION]
    - Teleology: Serve a backend-owned market dashboard read model pinned to
      an explicit run id so cockpit URLs can reproduce temporal selection.
    - Mechanism: Validates the run id shape, then reads the run-specific
      generated sidecar/artifact rather than letting React inspect files.
    - Guarantee: Missing historical read models return structured projection
      status, not frontend-authored fallback data.
    """
    safe_run_id = _validate_run_id(run_id)
    return _load_market_dashboard_read_model(REPO_ROOT, safe_run_id)


@app.get(
    "/api/market/intelligence/workspace/planes/{plane_id}",
    response_model=MarketBrowsePlaneResponse,
)
def market_intelligence_workspace_plane(
    plane_id: str,
    run_id: str | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=500),
    cursor: int = Query(default=0, ge=0),
    sort: str | None = Query(default=None),
    direction: str = Query(default="desc"),
):
    """
    [ACTION]
    - Teleology: Serve one page of one v0.10 market browse plane so the
      cockpit can render a dense workspace (hundreds of rows) without
      bloating the latest-ready bundle. The bundle carries only a
      top-25 preview + plane_nav row counts; this route paginates the
      full universe.
    - Mechanism: Resolves the run_id (defaults to latest-ready),
      normalizes the feed artifact through
      `system.lib.feed_artifact_tables.extract_feed_table`, applies
      sort + cursor + limit, and returns a typed page.
    - Guarantee: Missing artifacts return an extraction_status payload,
      not a 500. The cockpit can render an honest "no rows" state.
    """
    if plane_id not in _MARKET_PLANE_SPECS:
        raise HTTPException(status_code=404, detail={
            "error": "unknown_plane_id",
            "plane_id": plane_id,
            "known_planes": list(_MARKET_PLANE_SPECS.keys()),
        })
    spec = _MARKET_PLANE_SPECS[plane_id]
    if run_id:
        safe_run_id = _validate_run_id(run_id)
    else:
        # Default to latest-ready run id if available; else latest snapshot run id.
        latest_ready = _load_latest_ready_market_display_bundle(REPO_ROOT)
        safe_run_id = (
            (latest_ready or {}).get("run_id")
            or (_load_latest_market_dashboard_read_model(REPO_ROOT) or {}).get("run_id")
        )
        if not safe_run_id:
            return {
                "schema_version": "market_browse_plane_v0",
                "run_id": None,
                "plane_id": plane_id,
                "feed_id": spec.get("feed_id"),
                "row_count_total": 0,
                "row_count_raw": 0,
                "filtered_out_count": 0,
                "filter_status": {"status": "no_run_id_resolved"},
                "rows": [],
                "columns": spec.get("display_columns") or [],
                "sort": spec.get("default_sort") or {},
                "cursor": cursor,
                "next_cursor": None,
                "limit": limit,
                "extraction_status": {"status": "no_run_id_resolved"},
            }
    table = _extract_feed_table(REPO_ROOT, safe_run_id, spec["feed_id"])
    raw_rows = list(table.get("rows") or [])
    row_count_raw = len(raw_rows)

    # v0.10.1: filter heterogeneous rows down to the plane's schema
    # before sort + paginate so the visible page can only contain rows
    # the active plane knows how to render.
    rows, filtered_out = _filter_plane_rows(raw_rows, spec)
    filter_status = {
        "status": "filtered" if filtered_out else ("clean" if rows else "empty"),
        "required_columns": list(spec.get("required_columns") or []),
        "required_nonempty_columns": list(spec.get("required_nonempty_columns") or []),
        "required_any_metric": list(spec.get("required_any_metric") or []),
        "row_count_raw": row_count_raw,
        "row_count_filtered": len(rows),
        "filtered_out_count": filtered_out,
    }

    # Apply sort. The default sort comes from PLANE_SPECS; the caller
    # may override via ?sort=&direction=.
    effective_sort = {
        "column": sort or (spec.get("default_sort") or {}).get("column"),
        "direction": direction or (spec.get("default_sort") or {}).get("direction") or "desc",
    }

    col = effective_sort.get("column")
    rev = effective_sort.get("direction") == "desc"
    if col:
        def _key(r: dict[str, Any]) -> tuple[int, float]:
            v = r.get(col)
            if isinstance(v, (int, float)):
                return (1, float(v)) if rev else (0, float(v))
            # Non-numeric / None values sort to the tail regardless of
            # direction so a desc sort never opens with all-None rows.
            return (0, 0.0) if rev else (1, 0.0)
        try:
            rows = sorted(rows, key=_key, reverse=rev)
        except Exception:  # pragma: no cover - defensive
            pass

    page = rows[cursor : cursor + limit]
    next_cursor = cursor + limit if cursor + limit < len(rows) else None

    return {
        "schema_version": "market_browse_plane_v0",
        "run_id": safe_run_id,
        "plane_id": plane_id,
        "feed_id": spec.get("feed_id"),
        "row_count_total": len(rows),
        "row_count_raw": row_count_raw,
        "filtered_out_count": filtered_out,
        "filter_status": filter_status,
        "rows": page,
        "columns": spec.get("display_columns") or [],
        "sort": effective_sort,
        "cursor": cursor,
        "next_cursor": next_cursor,
        "limit": limit,
        "extraction_status": {
            "status": table.get("status"),
            "source_shape": table.get("source_shape"),
            "extraction_reason": table.get("extraction_reason"),
            "table_path": table.get("table_path"),
        },
    }


@app.get(
    "/api/market/intelligence/display-bundle/latest-ready",
    response_model=MarketDisplayBundleLatestReadyResponse,
)
def market_intelligence_latest_ready_display_bundle():
    """
    [ACTION]
    - Teleology: Serve the backend-published `latest_ready_market_display_bundle`
      pointer so the cockpit can consume one backend-owned market display
      product instead of doing last-good selection in React.
    - Mechanism: Reads `state/reports/market_feeds/latest_ready_market_display_bundle.json`
      written by `system.lib.market_display_bundle.write_market_display_bundle`
      after each FEEDS run that passes the readiness predicate.
    - Guarantee: Missing or unreadable pointer returns a structured
      `latest_ready_status` payload, not a 404. The cockpit then falls
      back to the v0.6.1 run-pinned bundle path.
    """
    return _load_latest_ready_market_display_bundle(REPO_ROOT)


@app.get(
    "/api/market/intelligence/runs/{run_id}/bundle",
    response_model=MarketDisplayBundleResponse,
)
def market_intelligence_run_bundle(run_id: str):
    """
    [ACTION]
    - Teleology: Serve a run-pinned `market_display_bundle` composing
      read_model + quant_presentation_mart + evidence_card so the cockpit
      can render a *consistent* substrate even when the live `latest_*`
      aliases have been temporarily blanked by a fresh FEEDS refresh.
    - Mechanism: Validates the run id shape, then composes the three
      per-run artifacts from disk through their owning loaders (no new
      builder is added; no React file access).
    - Guarantee: Each component carries its own `projection_status`; the
      bundle adds a `bundle_consistency` descriptor (`all_in_sync`,
      `consistent_run_ids`, per-component run ids and statuses) so the
      cockpit can render honestly when some parts are missing.
    """
    safe_run_id = _validate_run_id(run_id)
    return _build_market_display_bundle(REPO_ROOT, safe_run_id)


_MARKET_INTELLIGENCE_ROUTE_PATHS = {
    "latest": "/api/market/intelligence/latest",
    "run": "/api/market/intelligence/runs/{run_id}",
    "overview": "/api/market/intelligence/overview",
    "situations": "/api/market/intelligence/situations",
    "situation_detail": "/api/market/intelligence/situations/{situation_id}",
    "graph": "/api/market/intelligence/graph",
    "drilldown": "/api/market/intelligence/drilldown/{source_ref_id}",
    "provenance": "/api/market/intelligence/provenance",
    "validation_debt": "/api/market/intelligence/validation-debt",
}


def _market_intelligence_route_manifest_readiness(read_model: Mapping[str, Any]) -> Dict[str, Any]:
    route_paths = {str(getattr(route, "path", "")) for route in app.routes}
    registered = {
        route_id: route_path in route_paths
        for route_id, route_path in _MARKET_INTELLIGENCE_ROUTE_PATHS.items()
    }
    page_meta = frontend_surface_contracts.load_page_meta(REPO_ROOT)
    page_surfaces = page_meta.get("surfaces") if isinstance(page_meta, Mapping) else {}
    intelligence_meta = (
        page_surfaces.get("intelligence")
        if isinstance(page_surfaces, Mapping)
        else None
    )
    contracts = {
        "read_model_schema": read_model.get("schema_version") == "market_dashboard_read_model_v0",
        "projection_status": isinstance(read_model.get("projection_status"), Mapping),
        "overview": isinstance(read_model.get("overview"), Mapping),
        "situation_queue": isinstance(read_model.get("situation_queue"), Mapping),
        "graph_slice": isinstance(read_model.get("graph_slice"), Mapping),
        "drilldown_index": isinstance(read_model.get("drilldown_index"), Mapping),
        "provenance_index": isinstance(read_model.get("provenance_index"), Mapping),
        "validation_debt": isinstance(read_model.get("validation_debt"), Mapping),
        "api_contract": isinstance(read_model.get("api_contract"), Mapping),
    }
    return {
        "schema_version": "market_intelligence_route_manifest_readiness_v0",
        "process_alive": True,
        "route_registered": registered,
        "all_routes_registered": all(registered.values()),
        "page_meta_projected": {
            "surface_id": "intelligence",
            "projected": isinstance(intelligence_meta, Mapping),
            "page_meta_schema_version": page_meta.get("schema_version"),
        },
        "active_cockpit_data_contracts_loaded": {
            "ready": all(contracts.values()),
            "contracts": contracts,
        },
    }


@app.get("/api/market/intelligence/overview", response_model=MarketDashboardOverviewResponse)
def market_intelligence_overview():
    read_model = _latest_market_dashboard_read_model_payload()
    return {
        "schema_version": "market_dashboard_overview_v0",
        "projection_status": read_model.get("projection_status") or {},
        "overview": read_model.get("overview") or {},
        "route_manifest_readiness": _market_intelligence_route_manifest_readiness(read_model),
    }


@app.get("/api/market/intelligence/situations", response_model=MarketDashboardSituationQueueResponse)
def market_intelligence_situations(
    situation_type: str | None = Query(default=None, alias="type"),
    horizon: str | None = Query(default=None),
    claim_level: str | None = Query(default=None),
    validation_state: str | None = Query(default=None),
    display_state: str | None = Query(default=None),
    entity: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
):
    read_model = _latest_market_dashboard_read_model_payload()
    queue = _filter_market_dashboard_situation_queue(
        read_model,
        type=situation_type,
        horizon=horizon,
        claim_level=claim_level,
        validation_state=validation_state,
        display_state=display_state,
        entity=entity,
        provider=provider,
        limit=limit,
        cursor=cursor,
    )
    return {
        "schema_version": "market_dashboard_situation_queue_v0",
        "projection_status": read_model.get("projection_status") or {},
        "situation_queue": queue,
        "facets": read_model.get("facets") or {},
    }


@app.get(
    "/api/market/intelligence/situations/{situation_id}",
    response_model=MarketDashboardSituationDetailResponse,
)
def market_intelligence_situation_detail(situation_id: str):
    read_model = _latest_market_dashboard_read_model_payload()
    payload = _resolve_market_dashboard_situation_detail(read_model, situation_id)
    if not payload.get("available"):
        raise HTTPException(status_code=404, detail=payload)
    return payload


@app.get("/api/market/intelligence/graph", response_model=MarketDashboardGraphSliceResponse)
def market_intelligence_graph(
    situation_id: str | None = Query(default=None),
    depth: int = Query(default=1, ge=1, le=3),
    include_source_refs: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=500),
):
    read_model = _latest_market_dashboard_read_model_payload()
    return _resolve_market_dashboard_graph_slice(
        read_model,
        situation_id=situation_id,
        depth=depth,
        include_source_refs=include_source_refs,
        limit=limit,
    )


@app.get(
    "/api/market/intelligence/drilldown/{source_ref_id}",
    response_model=MarketDashboardDrilldownResponse,
)
def market_intelligence_drilldown(source_ref_id: str):
    read_model = _latest_market_dashboard_read_model_payload()
    payload = _resolve_market_dashboard_drilldown(read_model, source_ref_id)
    if not payload.get("available"):
        raise HTTPException(status_code=404, detail=payload)
    return payload


@app.get("/api/market/intelligence/provenance", response_model=MarketDashboardProvenanceResponse)
def market_intelligence_provenance():
    read_model = _latest_market_dashboard_read_model_payload()
    return _resolve_market_dashboard_provenance(read_model)


@app.get(
    "/api/market/intelligence/validation-debt",
    response_model=MarketDashboardValidationDebtResponse,
)
def market_intelligence_validation_debt():
    read_model = _latest_market_dashboard_read_model_payload()
    return _resolve_market_dashboard_validation_debt(read_model)


@app.get("/api/code-map")
def code_map_endpoint(
    focus: str | None = Query(default=None, description="Repo-relative focus path; narrows the packet to the focus file plus its direct neighbors. Optional."),
    max_files: int = Query(default=world_model_loader.CODE_MAP_DEFAULT_MAX_FILES, ge=1, description="Maximum file rows in the packet; clamped to the world_model code-map cap."),
):
    """
    [ACTION]
    - Teleology: Expose `code_map_packet_v1` over HTTP so Station and other read-only consumers can render the Code Architecture Projection Plane without re-running the kernel CLI. This endpoint is *transport*, not a second packet producer (per `codeflow_assimilation.md::Ontology invariants::One packet, many renderers`).
    - Mechanism: Normalize `focus` and clamp `max_files` via `system.server.world_model.load_code_map_snapshot`, which delegates to `system.lib.code_architecture_projection.build_code_map_packet`. The endpoint itself does not read hologram files, build overlays, or own any packet schema.
    - Guarantee: Returns the same `code_map_packet_v1` dict the kernel `--code-map` command emits, including `source.source_fingerprint`, `omission_receipt`, and `known_limits`.
    - Fails: 400 on path syntax violations (NUL, absolute, parent-traversal). Missing substrate degrades the packet through `omission_receipt`, never through 5xx.
    """
    try:
        return world_model_loader.load_code_map_snapshot(REPO_ROOT, focus=focus, max_files=max_files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Code map snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/system-atlas/graph")
def system_atlas_graph_endpoint(
    focus: str | None = Query(default=None, description="System Atlas entity id; narrows the packet to the focus entity plus its semantic neighbors."),
    kinds: str | None = Query(default=None, description="Comma-delimited entity-kind filter, for example Principle,Standard,PaperModule."),
    relations: str | None = Query(default=None, description="Comma-delimited relation filter, for example governed_by,covered_by_standard."),
    max_entities: int = Query(default=400, ge=1, description="Maximum entity rows in the packet; clamped to the world_model system-atlas cap."),
    max_depth: int = Query(default=2, ge=0, description="Maximum undirected ego-graph depth for focus expansion; clamped to the world_model system-atlas cap."),
):
    """
    [ACTION]
    - Teleology: Expose `system_atlas_packet_v1` over HTTP so Station can render one unified semantic graph instead of rebuilding per-kind inventories from `/api/system/navigation-surface`.
    - Mechanism: Normalize query params and clamp caps via `system.server.world_model.load_system_atlas_graph_snapshot`, which delegates to `system.lib.system_atlas_projection.build_system_atlas_packet`. The endpoint itself does not read `system_atlas.graph.json` or own the packet schema.
    - Guarantee: Returns a graph packet with normalized entities, typed edges, clusters, counts, source fingerprint, omission receipt, and known limits. Missing generated graph degrades through the packet, not through 5xx.
    - Fails: 400 on invalid query syntax. Unexpected loader failures are 500 with logging.
    """
    try:
        return world_model_loader.load_system_atlas_graph_snapshot(
            REPO_ROOT,
            focus=focus,
            kinds=kinds,
            relations=relations,
            max_entities=max_entities,
            max_depth=max_depth,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("System Atlas graph snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/blast-radius")
def blast_radius_endpoint(
    path: str = Query(..., description="Repo-relative target path for reverse-BFS impact; required."),
    max_depth: int = Query(default=4, ge=1, description="Maximum reverse-BFS depth; clamped to the world_model blast-radius cap."),
):
    """
    [ACTION]
    - Teleology: Expose `blast_radius_packet_v1` over HTTP so Station and other read-only consumers can render system-radius impact without re-running the kernel CLI. This endpoint is *transport*, not a second BFS owner.
    - Mechanism: Normalize `path`, serve a route-local stale-while-revalidate packet when warm, and on a cold miss return a warming packet immediately while a delayed background `system.server.world_model.load_blast_radius_snapshot` build starts. The endpoint never walks the graph itself.
    - Guarantee: Returns the same `blast_radius_packet_v1` dict the kernel `--blast-radius` command emits when ready, or a schema-clean `risk.confidence='warming'` packet while the builder is in flight. Valid-but-unknown targets return 200 with `risk.confidence='low'` and `risk_reasons=['target_not_in_hologram']`, never 5xx.
    - Fails: 400 on missing or syntactically invalid path.
    """
    try:
        return _blast_radius_payload(path=path, max_depth=max_depth)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Blast radius snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/world-model/snapshot")
def world_model_snapshot():
    """
    [ACTION]
    - Teleology: Project the repo's machine-readable world model into a single
      compact JSON payload so the cockpit can render orchestration, active phase
      family, doctrine catalog, docs focus, and freshness indicators in one
      bounded fetch.
    - Mechanism: Serves the existing SWR snapshot when warm; on a cold miss,
      schedules one background build and returns a schema-clean warming packet
      instead of blocking first paint on snapshot composition.
    - Reads: control plane + doctrine + active phase family JSON files.
    - Writes: None.
    - Guarantee: Always returns 200 with a snapshot dict; missing slices appear
      as None instead of raising.
    """
    try:
        return _world_model_snapshot_payload()
    except Exception as exc:
        logger.exception("World model snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/world-model/navigation-edges")
def world_model_navigation_edges():
    """
    [ACTION]
    - Teleology: Serve the TYPED per-edge navigation graph (mechanism, role,
      label, evidence refs) for PROGRESSIVE Surface Atlas hydration. The default
      /api/world-model/snapshot is served in first_paint mode and omits this
      `edges` array for cold-start payload budget, so the shared navigation_graph
      store carries only untyped adjacency. The Atlas fetches this slice lazily
      AFTER first paint so selected-node edges can render real relation classes
      (GROUP / LENS / SHELL / ROUTE / OPEN / overlay) instead of generic fallback
      adjacency — without rebuilding the whole snapshot or fattening first paint.
    - Mechanism: Runs the cheap single-file navigation-graph condense in `full`
      mode behind SWR so repeat fetches are warm.
    - Reads: state/frontend_navigation/navigation_graph.json.
    - Writes: None.
    - Guarantee: Always 200 with {edges:[...], available:bool}; on any failure
      returns an empty typed slice so the Atlas keeps its first_paint adjacency.
    """
    try:
        return swr_get(
            "world_model_navigation_edges",
            str(REPO_ROOT.resolve()),
            lambda: world_model_loader.load_navigation_graph_edges(REPO_ROOT),
            ttl_s=60.0,
        )
    except Exception as exc:
        logger.exception("Navigation edges snapshot failed: %s", exc)
        return {"edges": [], "available": False, "error": str(exc)}


@app.get("/api/world-model/ux-responsiveness")
def world_model_ux_responsiveness():
    """
    [ACTION]
    - Teleology: Make the UX-responsiveness goal's own progress visible in the
      cockpit, as the first proof of that goal (the `ux_responsiveness_conductor`
      autonomous seed). This backs a read-only progress strip — never a scheduler,
      poller, live command streamer, or fake progress bar.
    - Mechanism: Read the authored seed JSON and project its non-secret progress
      fields (goal status, telos, current focus, current wave, last change, proof
      surface, next-wave objective).
    - Reads: state/meta_missions/type_a_autonomous_seed_loop/seeds/
      ux_responsiveness_conductor_autonomous_seed.json
    - Writes: None.
    - Guarantee: Always returns 200 with `available` True/False; a missing seed
      yields `available=False` instead of raising.
    """
    from system.lib.ux_responsiveness_goal_projection import (
        build_ux_responsiveness_goal_projection,
    )

    return build_ux_responsiveness_goal_projection(REPO_ROOT)


@app.get("/api/world-model/system-lens", response_model=SystemLensProjectionResponse)
def world_model_system_lens():
    """
    [ACTION]
    - Teleology: Serve the System intelligence lens from one backend-composed
      cockpit projection instead of making the browser stitch multiple sparse
      snapshots with different freshness boundaries.
    - Mechanism: Delegates to world_model.load_system_lens_projection, which
      joins active phase, factory stage, orchestration, work, approvals, drift,
      and recent transitions under one generated_at.
    - Writes: None.
    """
    try:
        return JSONResponse(content=world_model_loader.load_system_lens_projection(REPO_ROOT))
    except Exception as exc:
        logger.exception("System lens projection failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/world-model/operations-lens", response_model=OperationsLensSnapshotResponse)
def world_model_operations_lens(refresh: bool = Query(default=False)):
    """
    [ACTION]
    - Teleology: Serve the SystemLens operations exposition as one read-only
      topology snapshot instead of letting the browser stitch Cockpit-era alert,
      launcher, and command surfaces together.
    - Mechanism: Default GET serves the hot last-known-good cache and schedules
      background refresh when stale; `refresh=1` recomposes and materializes the
      snapshot. This keeps ordinary page load off the expensive live topology
      composition path.
    - Writes: `refresh=1` and background prewarm update
      state/world_model/operations_lens_snapshot.json.
    """
    try:
        return JSONResponse(content=world_model_loader.load_operations_lens_snapshot_cached(REPO_ROOT, refresh=refresh))
    except Exception as exc:
        logger.exception("Operations lens snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get(
    "/api/world-model/lean-mathematics",
    response_model=LeanMathematicsMicrocosmSnapshotResponse,
)
def world_model_lean_mathematics_microcosm():
    """
    [ACTION]
    - Teleology: Expose the generated Lean/formal-math microcosm and its
      visual_surfaces envelope for Station demo views as a single read-only
      fetch.
    - Mechanism: Delegates to system.server.world_model.load_lean_mathematics_microcosm_snapshot.
    - Writes: None.
    - Guarantee: Missing or malformed projection artifacts degrade through
      available=false and omission_receipt instead of raising.
    """
    try:
        return world_model_loader.load_lean_mathematics_microcosm_snapshot(REPO_ROOT)
    except Exception as exc:
        logger.exception("Lean mathematics microcosm snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get(
    "/api/world-model/frontend/health-report",
    response_model=FrontendHealthReportResponse,
)
def frontend_health_report():
    """
    [ACTION]
    - Teleology: Expose the backend-owned frontend semantic health report.
    - Mechanism: Merges navigation graph, semantic layer, capture manifest, and render timing evidence.
    - Writes: None.
    """
    return frontend_surface_contracts.build_health_report(REPO_ROOT)


@app.get(
    "/api/world-model/frontend/surfaces",
    response_model=FrontendSurfaceListResponse,
)
def frontend_surfaces():
    """
    [ACTION]
    - Teleology: Return all known frontend surfaces with semantic health and evidence.
    - Writes: None.
    """
    return frontend_surface_contracts.build_surface_list(REPO_ROOT)


@app.get(
    "/api/world-model/frontend/surfaces/{view_id}/agent-packet",
    response_model=FrontendSurfaceAgentPacketResponse,
)
def frontend_surface_agent_packet(view_id: str):
    """
    [ACTION]
    - Teleology: Return one agent-readable surface packet for live UI comprehension.
    - Writes: None.
    """
    try:
        return frontend_surface_contracts.build_surface_agent_packet(REPO_ROOT, view_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown frontend surface: {view_id}")


@app.get(
    "/api/world-model/runtime/continuity",
    response_model=RuntimeContinuityResponse,
)
def world_model_runtime_continuity():
    """
    [ACTION]
    - Teleology: Expose backend-owned continuity counters so UI reset/reconnect symptoms can be classified.
    - Writes: None.
    """
    return runtime_continuity_payload()


@app.get("/api/world-model/vantage")
def world_model_vantage(
    band: str = Query(
        "card",
        pattern="^(flag|card|context)$",
        description="Vantage compression band.",
    ),
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Expose the kernel vantage composer as a read-only Station lens.
    - Writes: None.
    """
    return build_vantage(REPO_ROOT, band=band)


@app.get(
    "/api/world-model/host-agent-external-surfaces",
    response_model=HostAgentExternalSnapshot,
)
def world_model_host_agent_external_surfaces():
    """
    [ACTION]
    - Teleology: Expose the mined Claude/Codex host-agent runtime slice on the
      world-model route family so Station and future operator lenses can read
      deployment/runtime pressure from one typed API packet.
    - Mechanism: Thin route over
      `system.server.world_model.load_host_agent_external_snapshot`.
    - Guarantee: Returns the compact snapshot on success.
    """
    try:
        return world_model_loader.load_host_agent_external_snapshot(REPO_ROOT)
    except Exception as exc:
        logger.exception("Host-agent external snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/world-model/principle/{principle_id}")
def world_model_principle(principle_id: str):
    """
    [ACTION]
    - Teleology: Resolve and return a single principle record by id for the doctrine drawer.
    - Guarantee: Returns the principle dict on success.
    - Fails: HTTP 404 if principle_id not found.
    """
    record = world_model_loader.resolve_principle(REPO_ROOT, principle_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Principle '{principle_id}' not found")
    return record


@app.get("/api/world-model/concept/{concept_id}")
def world_model_concept(concept_id: str):
    """
    [ACTION]
    - Teleology: Resolve and return a single concept record by id for the doctrine drawer.
    - Guarantee: Returns the concept dict on success.
    - Fails: HTTP 404 if concept_id not found.
    """
    record = world_model_loader.resolve_concept(REPO_ROOT, concept_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Concept '{concept_id}' not found")
    return record


@app.get("/api/world-model/mechanism/{mechanism_id}")
def world_model_mechanism(mechanism_id: str):
    """
    [ACTION]
    - Teleology: Resolve and return a single mechanism record by id for the doctrine drawer.
    - Guarantee: Returns the mechanism dict on success.
    - Fails: HTTP 404 if mechanism_id not found.
    """
    record = world_model_loader.resolve_mechanism(REPO_ROOT, mechanism_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Mechanism '{mechanism_id}' not found")
    return record


@app.get("/api/world-model/raw-seed/anchor")
def world_model_raw_seed_anchor(ref: str = Query(..., min_length=2)):
    """
    [ACTION]
    - Teleology: Resolve and return a raw-seed anchor record by ref for the doctrine drawer.
    - Guarantee: Returns the anchor dict on success.
    - Fails: HTTP 404 if ref not found.
    """
    record = world_model_loader.resolve_raw_seed_anchor(REPO_ROOT, ref)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Raw seed anchor '{ref}' not found")
    return record


@app.get("/api/world-model/shards/overview", response_model=ShardLensOverviewResponse)
def world_model_shards_overview(
    source: str = Query("family", pattern="^(active|family|raw_seed)$"),
):
    """
    [ACTION]
    - Teleology: Return the bounded overview projection for the shard operator lens.
    - Guarantee: Returns the typed overview payload on success.
    - Fails: HTTP 404 when no shard surface can be resolved for the requested source.
    """
    record = world_model_loader.load_shard_overview(REPO_ROOT, source=source)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No shard surface found for source '{source}'",
        )
    return record


@app.get("/api/world-model/shards/query", response_model=ShardLensQueryResponse)
def world_model_shards_query(
    source: str = Query("family", pattern="^(active|family|raw_seed)$"),
    query: str = Query("", max_length=240),
    group: Optional[str] = Query(None, max_length=200),
    paragraph_id: Optional[str] = Query(None, max_length=200),
    shard_status: Optional[str] = Query(None, alias="status", max_length=120),
    limit: int = Query(20, ge=1, le=200),
    related_limit: int = Query(40, ge=0, le=200),
):
    """
    [ACTION]
    - Teleology: Return ranked or structurally filtered shard results plus derived graph context.
    - Guarantee: Returns the typed query payload on success.
    - Fails: HTTP 404 when no shard surface can be resolved for the requested source.
    """
    record = world_model_loader.query_shards(
        REPO_ROOT,
        source=source,
        query=query,
        group=group,
        paragraph_id=paragraph_id,
        status=shard_status,
        limit=limit,
        related_limit=related_limit,
    )
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No shard surface found for source '{source}'",
        )
    return record


@app.get("/api/world-model/shards/{shard_id}", response_model=ShardLensDetailResponse)
def world_model_shard_detail(
    shard_id: str,
    source: str = Query("family", pattern="^(active|family|raw_seed)$"),
    neighbors: int = Query(3, ge=0, le=25),
):
    """
    [ACTION]
    - Teleology: Return one selected shard with neighborhood, sibling, and provenance context.
    - Guarantee: Returns the typed detail payload on success.
    - Fails: HTTP 404 when the shard or requested source surface cannot be resolved.
    """
    record = world_model_loader.load_shard_detail(
        REPO_ROOT,
        shard_id,
        source=source,
        neighbors=neighbors,
    )
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Shard '{shard_id}' not found for source '{source}'",
        )
    return record


@app.get("/api/world-model/work-ledger/overview", response_model=WorkLedgerOverviewResponse)
def world_model_work_ledger_overview(
    phase_id: Optional[str] = Query(None, max_length=120),
    family_id: Optional[str] = Query(None, max_length=120),
):
    record = world_model_loader.load_work_ledger_overview(
        REPO_ROOT,
        phase_id=phase_id,
        family_id=family_id,
        allow_warming_shell=True,
    )
    return record


@app.get(
    "/api/world-model/mission-transaction/preflight",
    response_model=MissionTransactionPreflightResponse,
)
def world_model_mission_transaction_preflight(
    subject_id: Optional[str] = Query(_MISSION_TRANSACTION_DEFAULT_SUBJECT_ID, max_length=180),
    owned_path: Optional[List[str]] = Query(None),
    session_id: Optional[str] = Query(None, max_length=240),
    require_exclusive: bool = Query(False),
):
    target_ids = [subject_id] if subject_id else []
    owned_paths = tuple(owned_path or _MISSION_TRANSACTION_DEFAULT_OWNED_PATHS)
    return build_mission_transaction_landing_preflight(
        REPO_ROOT,
        owned_paths=owned_paths,
        target_ids=target_ids,
        session_id=session_id,
        require_exclusive=require_exclusive,
    )


@app.get("/api/world-model/work-ledger/query", response_model=WorkLedgerQueryResponse)
def world_model_work_ledger_query(
    recipe: str = Query(..., min_length=3, max_length=120),
    phase_id: Optional[str] = Query(None, max_length=120),
    family_id: Optional[str] = Query(None, max_length=120),
    actor: Optional[str] = Query(None, max_length=120),
    actor_session_id: Optional[str] = Query(None, max_length=240),
    td_id: Optional[str] = Query(None, max_length=120),
    limit: int = Query(20, ge=1, le=200),
):
    try:
        return world_model_loader.query_work_ledger(
            REPO_ROOT,
            recipe=recipe,
            phase_id=phase_id,
            family_id=family_id,
            actor=actor,
            actor_session_id=actor_session_id,
            td_id=td_id,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/world-model/work-ledger/thread/{td_id}", response_model=WorkLedgerThreadResponse)
def world_model_work_ledger_thread(td_id: str):
    record = world_model_loader.load_work_ledger_thread(REPO_ROOT, td_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Work-ledger thread '{td_id}' not found")
    return record


@app.get("/api/world-model/task-ledger/projection")
def world_model_task_ledger_projection(
    limit: int = Query(8, ge=1, le=40),
):
    return world_model_loader.load_task_ledger_projection(REPO_ROOT, limit=limit)


@app.get("/api/world-model/task-ledger/cartography/{view_id}")
def world_model_task_ledger_cartography(
    view_id: str,
    include: str | None = Query(
        default=None,
        description=(
            "Comma-separated subset of fields to include in the payload. "
            "Available: summary, atlas_marks, clusters, nodes, edges, "
            "lineage_index, legend, levels, overflow_index, overflow_policy, "
            "drilldown_index, unclassified_index, warnings, omission_receipt, "
            "source_refs. Omit to include all of them."
        ),
    ),
):
    """
    Read-only payload-transport route for Task Ledger cartography views.

    `view_id` aliases:
      - `workitem` or `workitem_cartography` -> workitem_cartography_v0
      - `cap` or `cap_cartography` -> cap_cartography_v0

    Returns the full generated cartography packet (atlas_marks + bounded
    graph + readiness contract) so the Atlas renderer can fetch the
    row-grain mark universe without polling the heavy payload through the
    lightweight `task-ledger/projection` envelope.
    """
    include_list: list[str] | None = None
    if include is not None:
        include_list = [chunk.strip() for chunk in include.split(",") if chunk.strip()]
    return world_model_loader.load_task_ledger_cartography_payload(
        REPO_ROOT, view_id, include=include_list
    )


@app.get("/api/world-model/task-ledger/neighborhood/{work_item_id}")
def world_model_task_ledger_neighborhood(work_item_id: str):
    """
    Wave 1F — full one-hop dependency / unlock neighborhood for a single
    Task Ledger WorkItem. Unconstrained by the bounded cartography
    overview's top-N node cap; reads ledger.work_items[].depends_on
    outbound and reverse-scans for inbound edges so the
    NeighborhoodInspector stops showing "outside bounded overview · 0
    neighbors" for most real WorkItems.

    Response shape: workitem_neighborhood_v0 with focus / neighbors /
    edges / counts / omission_receipt (complete_one_hop=True when
    available=True). Read-only.
    """
    return world_model_loader.load_workitem_neighborhood_payload(
        REPO_ROOT, work_item_id
    )


@app.get("/api/world-model/task-ledger/dossier/{work_item_id}")
def world_model_task_ledger_dossier(
    work_item_id: str,
    event_limit: int = Query(12, ge=1, le=50),
):
    """
    Read-only rich drilldown for one Task Ledger WorkItem.

    Composes ledger.json, events.jsonl, source-view membership,
    workitem_cartography mark metadata, execution receipts, and full one-hop
    neighborhood data into a bounded dossier. Intended as the backend contract
    for Work lens list/Atlas clicks; mutation still routes through
    task_ledger_apply.py.
    """
    return world_model_loader.load_workitem_dossier_payload(
        REPO_ROOT, work_item_id, event_limit=event_limit
    )


@app.get("/api/world-model/frontend/workitem-diagnostics/projection")
def world_model_frontend_workitem_diagnostics_projection(
    limit: int = Query(12, ge=1, le=40),
):
    return world_model_loader.load_frontend_workitem_diagnostics_projection(REPO_ROOT, limit=limit)


@app.get("/api/world-model/workitem/control-picture")
def world_model_workitem_control_picture_projection(
    subject_id: str | None = Query(None),
    domain: str | None = Query(None),
    selector_mode: str = Query("agent", pattern="^(agent|operator)$"),
    include_signoff: bool = Query(False),
    include_transaction: bool = Query(True),
    limit: int = Query(5, ge=1, le=20),
):
    return world_model_loader.load_workitem_control_picture_projection(
        REPO_ROOT,
        subject_id=subject_id,
        domain=domain,
        selector_mode=selector_mode,
        include_signoff=include_signoff,
        include_transaction=include_transaction,
        limit=limit,
    )


@app.get(
    "/api/world-model/meta-diagnostics/console",
    response_model=MetaDiagnosticsConsoleProjectionResponse,
)
def world_model_meta_diagnostics_console(
    limit: int = Query(
        8,
        ge=1,
        le=40,
        description="Per-panel sample limit for bounded rows, counters, and graph excerpts.",
    ),
):
    """
    Read-only backend packet for a System Proof / Meta Diagnostics console.

    This endpoint composes existing generated artifacts only: agent telemetry,
    Task Ledger cartography, prompt-learning posture, paper-module route health,
    annex intake pressure, capability lanes, facts, and proof-constellation
    samples. It is transport/read-model glue, not a new authority or mutation
    lane.
    """
    return world_model_loader.load_meta_diagnostics_console_projection(
        REPO_ROOT,
        limit=limit,
    )


# --- Phase 08.12 world-model extensions ------------------------------------
# Doctrine refs: mech_025 (authority chain contract), mech_026 (unified runtime
# graph lens). All routes below are read-only projections.


@app.get("/api/world-model/phase/{phase_ref}/cycles")
def world_model_phase_cycles(phase_ref: str):
    """
    [ACTION]
    - Teleology: Return the cycle index entries for a phase family.
    - Guarantee: Returns {entries: [...]} on success.
    - Fails: HTTP 500 on unexpected errors.
    """
    try:
        return {"entries": world_model_loader.list_phase_cycles(REPO_ROOT, phase_ref)}
    except Exception as exc:
        logger.exception("world-model cycle index failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/world-model/phase/{phase_ref}/cycle/{cycle_number}")
def world_model_cycle_summary(phase_ref: str, cycle_number: int):
    """
    [ACTION]
    - Teleology: Return the cycle summary for a specific cycle within a phase family.
    - Guarantee: Returns the cycle summary dict on success.
    - Fails: HTTP 404 if the cycle is not found for the given phase_ref.
    """
    record = world_model_loader.load_cycle_summary(REPO_ROOT, phase_ref, cycle_number)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cycle {cycle_number} not found for phase '{phase_ref}'",
        )
    return record


@app.get("/api/world-model/phase/{phase_ref}/system-view")
def world_model_system_view(phase_ref: str, sample: int = Query(80, ge=1, le=500)):
    """
    [ACTION]
    - Teleology: Return the system view projection for a phase, sampled to the given limit.
    - Guarantee: Returns the system view dict on success.
    - Fails: HTTP 404 if system_view.json not found for the given phase_ref.
    """
    record = world_model_loader.load_system_view_projection(
        REPO_ROOT, phase_ref, sample_limit=sample
    )
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"system_view.json not found for phase '{phase_ref}'",
        )
    return record


@app.get("/api/world-model/unified-graph")
def world_model_unified_graph(
    mission: Optional[str] = None,
    phase: Optional[str] = None,
    cycle: Optional[int] = None,
    include: str = Query("meta,factory"),
):
    """
    [ACTION]
    - Teleology: Compose and return the unified runtime graph projection across mission, meta, and factory slices.
    - Guarantee: Returns the composed graph dict on success; unrecognized include tokens are silently filtered.
    - Fails: HTTP 500 on unexpected composition errors.
    """
    include_tokens = tuple(
        t.strip()
        for t in include.split(",")
        if t.strip() in {"mission", "meta", "factory", "provider"}
    )
    if not include_tokens:
        include_tokens = ("meta",)
    try:
        return world_model_loader.load_unified_runtime_graph(
            REPO_ROOT,
            mission_name=mission,
            phase_ref=phase,
            cycle=cycle,
            include=include_tokens,
        )
    except Exception as exc:
        logger.exception("unified-graph composition failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/world-model/orchestration/events")
def world_model_orchestration_events(limit: int = Query(20, ge=1, le=200)):
    """
    [ACTION]
    - Teleology: Return recent orchestration events from the control plane for the cockpit event feed.
    - Guarantee: Returns {events: [...]} with at most `limit` entries.
    - Fails: None.
    """
    return {"events": world_model_loader.load_orchestration_events(REPO_ROOT, limit)}


@app.post("/api/world-model/orchestration/refresh")
def world_model_orchestration_refresh():
    """
    [ACTION]
    - Teleology: Re-read the control plane from disk and return the freshest orchestration snapshot.
    - Guarantee: Returns the refreshed orchestration snapshot dict on success.
    - Fails: HTTP 500 on unexpected errors.
    """
    try:
        return world_model_loader.refresh_orchestration_snapshot(REPO_ROOT)
    except Exception as exc:
        logger.exception("orchestration refresh failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/world-model/orchestration/acknowledge")
def world_model_orchestration_acknowledge(payload: Dict[str, Any] = Body(...)):
    """
    [ACTION]
    - Teleology: Record a typed `gate_acknowledged` operator decision in the
      orchestration event log so the orchestration loop can clear the gate on its
      next cycle (apply-gate discipline preserved).
    - Mechanism: Delegate to world_model_loader.acknowledge_orchestration_gate.
    - Guarantee: Returns the helper's structured result; validation failures
      surface as `{ok: False, error: "..."}` with HTTP 400, not a 500 traceback.
    - Fails: HTTP 400 on validation. Never raises 500.
    """
    from fastapi.responses import JSONResponse

    try:
        actor_id = str(payload.get("actor_id") or "").strip()
        reason = payload.get("reason")
        reason_str: Optional[str] = None
        if reason is not None:
            if not isinstance(reason, str):
                return JSONResponse(
                    status_code=400,
                    content={"ok": False, "error": "reason must be a string if provided"},
                )
            reason_str = reason
        if not actor_id:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "actor_id is required"},
            )
        result = world_model_loader.acknowledge_orchestration_gate(
            REPO_ROOT, actor_id=actor_id, reason=reason_str
        )
        if not result.get("ok"):
            return JSONResponse(status_code=400, content=result)
        return result
    except Exception as exc:
        logger.exception("orchestration acknowledge failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"internal: {type(exc).__name__}"},
        )


def _approval_error_status(error_code: str) -> int:
    if error_code == "approval_not_found":
        return 404
    if error_code in {
        "decision_not_supported",
        "claim_conflict",
        "stale_source_state",
        "callback_failed",
    }:
        return 409
    return 400


@app.get("/api/approvals", response_model=ApprovalListResponse)
def approvals_list(
    source_kind: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    action_kind: Optional[str] = Query(None),
):
    """
    [ACTION]
    - Teleology: Serve the unified approval inbox projection to Station and any
      operator surface that needs the current pending approval rows.
    - Guarantee: Returns `{records, summary, generated_at}` with optional
      filtering by source kind, projected status, or action kind.
    - Fails: HTTP 500 only for unexpected backend errors.
    """
    try:
        return world_model_loader.list_approvals(
            REPO_ROOT,
            source_kind=source_kind,
            status=status,
            action_kind=action_kind,
        )
    except Exception as exc:
        logger.exception("approvals list failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/approvals/{approval_id}/decide", response_model=ApprovalDecisionResponse)
def approvals_decide(approval_id: str, payload: ApprovalDecisionRequest):
    """
    [ACTION]
    - Teleology: Apply one operator approval decision through the source-safe
      mutation callback for the projected approval row.
    - Guarantee: Returns refreshed approval rows on success. Review-only rows,
      stale-source conflicts, and duplicate claims surface as structured 4xx
      responses instead of traceback noise.
    - Fails: HTTP 404 for unknown approval ids, HTTP 409 for unsupported or
      conflicting decisions, HTTP 400 for invalid payloads, HTTP 500 otherwise.
    """
    try:
        result = world_model_loader.decide_approval(
            REPO_ROOT,
            approval_id=approval_id,
            decision=payload.decision,
            actor_id=payload.actor_id,
            reason=payload.reason,
        )
        if not result.get("ok"):
            return JSONResponse(
                status_code=_approval_error_status(str(result.get("error_code") or "")),
                content=result,
            )
        return result
    except Exception as exc:
        logger.exception("approval decision failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"internal: {type(exc).__name__}"},
        )


@app.get("/api/world-model/operations")
def world_model_operations():
    """
    [ACTION]
    - Teleology: Publish the catalog of operations the cockpit can launch from the
      operator surface (Phase 09.17 gap #10). Safe/introspection-only.
    - Mechanism: Delegate to world_model_loader.list_launchable_operations.
    - Guarantee: Returns `{operations: [...], generated_at: <iso>}` on success.
      On any internal error, returns HTTP 500 with a structured body.
    - Fails: Never raises.
    """
    from fastapi.responses import JSONResponse

    try:
        return _operations_catalog_payload()
    except Exception as exc:
        logger.exception("list launchable operations failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"internal: {type(exc).__name__}"},
        )


@app.post("/api/world-model/operations/preview", response_model=LaunchOperationPreviewResponse)
def world_model_operations_preview(payload: Dict[str, Any] = Body(...)):
    """
    [ACTION]
    - Teleology: Validate and render a catalogued SAFE operation without
      executing it so the cockpit can show an authoritative backend preview.
    - Mechanism: Delegate to world_model_loader.preview_launch_operation.
    - Guarantee: Returns `{ok: True, preview: {...}}` on success. Validation or
      policy rejections return HTTP 400 with `{ok: False, error: "..."}`.
    - Fails: Unexpected failures return HTTP 500 with the standard launcher
      envelope `{ok: False, error: "internal: <type>"}`.
    """
    from fastapi.responses import JSONResponse

    try:
        operation_id = str(payload.get("operation_id") or "").strip()
        parameters = payload.get("parameters") or {}
        if not operation_id:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "operation_id is required"},
            )
        if not isinstance(parameters, dict):
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "parameters must be an object"},
            )
        result = world_model_loader.preview_launch_operation(
            REPO_ROOT,
            operation_id=operation_id,
            parameters=parameters,
        )
        if not result.get("ok"):
            return JSONResponse(status_code=400, content=result)
        return result
    except Exception as exc:
        logger.exception("preview operation failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"internal: {type(exc).__name__}"},
        )


@app.post("/api/world-model/operations/launch")
def world_model_operations_launch(payload: Dict[str, Any] = Body(...)):
    """
    [ACTION]
    - Teleology: Launch a catalogued SAFE operation on behalf of the operator and
      return its captured output plus a recorded traceability event.
    - Mechanism: Delegate to world_model_loader.launch_operation.
    - Guarantee: Returns `{ok: True, result: {...}}` on success. Validation or
      apply-gate rejections return HTTP 400 with `{ok: False, error: "..."}`.
    - Fails: Never raises.
    """
    from fastapi.responses import JSONResponse

    try:
        operation_id = str(payload.get("operation_id") or "").strip()
        actor_id = str(payload.get("actor_id") or "").strip()
        parameters = payload.get("parameters") or {}
        if not operation_id:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "operation_id is required"},
            )
        if not actor_id:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "actor_id is required"},
            )
        if not isinstance(parameters, dict):
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "parameters must be an object"},
            )
        result = world_model_loader.launch_operation(
            REPO_ROOT,
            operation_id=operation_id,
            parameters=parameters,
            actor_id=actor_id,
        )
        if not result.get("ok"):
            return JSONResponse(status_code=400, content=result)
        return result
    except Exception as exc:
        logger.exception("launch operation failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"internal: {type(exc).__name__}"},
        )


def _pid_running(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _ensure_reactions_engine_running() -> None:
    snapshot = world_model_loader.load_reactions_snapshot(REPO_ROOT) or {}
    pid = snapshot.get("pid")
    if _pid_running(pid):
        return
    log_dir = REPO_ROOT / "state" / "launcher_ops"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ').lower()}_reactions_engine.log"
    handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            str(REPO_ROOT / "repo-python"),
            "tools/meta/control/reactions_engine.py",
            "run",
        ],
        cwd=str(REPO_ROOT),
        stdout=handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    handle.close()
    logger.info("Started reactions engine pid=%s log=%s", process.pid, log_path)


@app.get("/api/world-model/reactions")
def world_model_reactions():
    try:
        return world_model_loader.load_reactions_snapshot(REPO_ROOT)
    except Exception as exc:
        logger.exception("reactions snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/world-model/wake-barriers")
def world_model_wake_barriers():
    try:
        return swr_get(
            "wake_barriers",
            str(REPO_ROOT.resolve()),
            lambda: world_model_loader.load_wake_barriers(REPO_ROOT),
            ttl_s=10.0,
        )
    except Exception as exc:
        logger.exception("wake barriers snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/world-model/reconciliation")
def world_model_reconciliation():
    """pri_119 cold-start reconciliation projection.

    Read-only projection over the latest `metabolism_reconciliation_v1`
    event in the metabolism events table. Never runs a fresh
    reconciliation pass — fresh passes happen at metabolismd boot, on
    the `metabolismd reconcile` CLI, and in `metabolismd doctor`. The
    cockpit reads what the daemon last witnessed; staleness becomes a
    pri_110 alarm at the lens layer (default threshold: 900s).
    """
    try:
        return world_model_loader.load_reconciliation_snapshot(REPO_ROOT)
    except Exception as exc:
        logger.exception("reconciliation snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/world-model/reactions/state")
def world_model_reactions_state(payload: Dict[str, Any] = Body(...)):
    from fastapi.responses import JSONResponse

    try:
        target = str(payload.get("target") or "").strip()
        armed = payload.get("armed")
        reaction_id = payload.get("reaction_id")
        if target not in {"engine", "reaction"}:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "target must be 'engine' or 'reaction'"},
            )
        if not isinstance(armed, bool):
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "armed must be a boolean"},
            )
        if target == "reaction" and (not isinstance(reaction_id, str) or not reaction_id.strip()):
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "reaction_id is required when target='reaction'"},
            )
        snapshot = world_model_loader.set_reaction_armed_state(
            REPO_ROOT,
            target=target,
            armed=armed,
            reaction_id=str(reaction_id).strip() if isinstance(reaction_id, str) else None,
        )
        if target == "engine" and armed:
            _ensure_reactions_engine_running()
            snapshot = world_model_loader.refresh_reactions_snapshot(REPO_ROOT)
        return snapshot
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    except Exception as exc:
        logger.exception("reactions state update failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"internal: {type(exc).__name__}"},
        )


@app.get("/api/world-model/attention")
def world_model_attention():
    """
    [ACTION]
    - Teleology: Return the current attention snapshot for the cockpit focus surface.
    - Guarantee: Returns the attention snapshot dict on success.
    - Fails: HTTP 500 on unexpected errors.
    """
    try:
        return _attention_snapshot_payload()
    except Exception as exc:
        logger.exception("attention snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/world-model/phase/{phase_ref}/topology")
def world_model_phase_topology(phase_ref: str):
    """
    [ACTION]
    - Teleology: Return the topology index for a phase family.
    - Guarantee: Returns the topology index dict on success.
    - Fails: HTTP 404 if system_view.json not found for the given phase_ref.
    """
    record = world_model_loader.load_topology_index(REPO_ROOT, phase_ref)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"system_view.json not found for phase '{phase_ref}'",
        )
    return record


@app.get("/api/world-model/phase/{phase_ref}/topology/search")
def world_model_phase_topology_search(
    phase_ref: str,
    query: str = Query("", max_length=200),
    group: Optional[str] = None,
    cluster: Optional[str] = None,
    kind: Optional[str] = None,
    limit: int = Query(60, ge=1, le=500),
):
    """
    [ACTION]
    - Teleology: Search the topology index for a phase using text, group, cluster, or kind filters.
    - Guarantee: Returns filtered topology search results on success.
    - Fails: HTTP 404 if system_view.json not found for the given phase_ref.
    """
    record = world_model_loader.search_topology(
        REPO_ROOT,
        phase_ref,
        query=query,
        group=group,
        cluster=cluster,
        kind=kind,
        limit=limit,
    )
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"system_view.json not found for phase '{phase_ref}'",
        )
    return record


@app.get("/api/world-model/reference-acquisitions")
def world_model_reference_acquisitions():
    """
    [ACTION]
    - Teleology: Return the reference acquisition records for the annex/ledger display.
    - Guarantee: Returns {acquisitions: [...]} on success.
    - Fails: None.
    """
    return {"acquisitions": world_model_loader.load_reference_acquisitions(REPO_ROOT)}


@app.get("/api/agent-dotfiles")
def agent_dotfile_snapshot():
    """
    [ACTION]
    - Teleology: Expose the in-repo `.claude/` and `.codex/` host-agent
      configuration planes as one read-only snapshot so Station can render
      a diagnostics view without the frontend re-parsing dotfiles itself.
    - Mechanism: Delegates to
      `system.server.world_model.load_host_agent_dotfile_snapshot` — the
      world-model projection wrapper carries the cached, freshness-tagged
      shape that `/api/world` also ships under `host_agent_dotfiles`.
    - Reads: `.claude/settings.local.json`, `.claude/launch.json`,
      `.claude/hooks/runtime_hook.py`, `.claude/agents/`, `.claude/follow_on/`,
      `.codex/config.toml`, `.codex/roles/*.toml`, `.codex/follow_on/`.
    - Writes: None.
    - Guarantee: Always returns 200 with a snapshot dict; missing sections
      degrade to empty / exists=false instead of raising.
    - Escalates-to: codex/doctrine/paper_modules/host_agent_dotfile_surfaces.md
    """
    try:
        return world_model_loader.load_host_agent_dotfile_snapshot(REPO_ROOT)
    except Exception as exc:
        logger.exception("Agent dotfile snapshot failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/drift")
def drift_aggregate_endpoint():
    """
    [ACTION]
    - Teleology: Return the unified cross-plane drift roll-up so Station
      headers and agent-diagnostics can surface one "what needs attention"
      counter without each lens re-summing the dotfile / navigation / paper-
      module planes.
    - Mechanism: Load the fresh `world_model_snapshot_v1` and extract its
      `drift_aggregate` slice — the aggregator composition lives alongside
      the snapshot builder so every consumer sees the same numbers.
    - Reads: world_model.load_world_model_snapshot (cached loaders underneath).
    - Writes: None.
    - Guarantee: Always returns 200 with a `drift_aggregate_v1` payload even
      when individual planes degrade to empty shapes.
    - Escalates-to: system/server/world_model.py::_build_drift_aggregate;
      codex/doctrine/paper_modules/host_agent_dotfile_surfaces.md
    """
    try:
        snapshot = world_model_loader.load_world_model_snapshot(REPO_ROOT)
        aggregate = snapshot.get("drift_aggregate") or {
            "schema": "drift_aggregate_v1",
            "generated_at": None,
            "total": 0,
            "severity_counts": {"error": 0, "warning": 0, "info": 0},
            "sources": [],
        }
        return aggregate
    except Exception as exc:
        logger.exception("Drift aggregate load failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/authority/{kind}/{id_:path}")
def world_model_authority_chain(kind: str, id_: str):
    """
    [ACTION]
    - Teleology: Resolve and return a typed AuthorityChain for a UI handle (mech_025).
    - Guarantee: Returns the authority chain dict on success.
    - Fails: HTTP 404 if no authority chain found for the given kind/id.
    """
    chain = world_model_loader.resolve_authority_chain(REPO_ROOT, kind, id_)
    if chain is None:
        raise HTTPException(
            status_code=404,
            detail=f"Authority chain not found for {kind}/{id_}",
        )
    return chain


@app.websocket("/ws/meta/observe/session")
async def meta_observe_session_ws(websocket: WebSocket):
    """
    [ACTION]
    - Teleology: Maintain a WebSocket connection for observe-session telemetry, replaying history to late-joining clients.
    - Guarantee: While connected, client receives both replayed history events and live telemetry from meta_session_broadcaster.
    - Fails: WebSocketDisconnect or any exception -> connection removed and handler exits cleanly.
    """
    await websocket.accept()
    meta_session_websockets.add(websocket)
    try:
        # Hydrate late-joining clients with existing events
        history = meta_session_controller.get_history()
        for evt in history:
            await websocket.send_json(evt)
            
        while True:
            try: await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError: pass
    except (WebSocketDisconnect, Exception):
        meta_session_websockets.discard(websocket)
    finally:
        meta_session_websockets.discard(websocket)


# --- RECORDING VIEW TELEMETRY ---
# Live view telemetry from the FE during demo-take-console recording. The FE
# posts a view-event on every route change. When an active recording take is
# registered, every event is also appended to <take_root>/view_telemetry.jsonl
# so post-production can map narration timestamps to which view was open.

_recording_lock = threading.Lock()
_recording_state: Dict[str, Any] = {
    "active_take": None,
    "recent_events": [],
    "current_surface": None,
}
_RECORDING_RECENT_EVENT_CAP = 200
_RECORDING_OPTIONAL_EVENT_FIELDS = (
    "source",
    "runtime_mode",
    "host_app",
    "window_id",
    "workspace_id",
    "surface_kind",
    "surface_id",
    "native_lens",
    "client_at_iso",
    "route",
    "view_id",
    "view_label",
    "pathname",
    "search",
    "hash",
)


def _recording_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _recording_take_root_from_payload(take_root: str) -> Path:
    path = Path(take_root).expanduser().resolve()
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="take_root must be inside this repository",
        ) from exc
    return path


def _recording_video_t_seconds(session: Dict[str, Any], at_iso: str) -> float:
    started = session.get("created_at")
    if not started:
        return 0.0
    try:
        started_dt = datetime.fromisoformat(started)
        at_dt = datetime.fromisoformat(at_iso)
    except ValueError:
        return 0.0
    wall = max(0.0, (at_dt - started_dt).total_seconds())
    paused = 0.0
    last_pause: Optional[datetime] = None
    for event in session.get("pause_events", []):
        kind = event.get("kind")
        ts = event.get("at_iso")
        if not kind or not ts:
            continue
        try:
            event_dt = datetime.fromisoformat(ts)
        except ValueError:
            continue
        if event_dt > at_dt:
            break
        if kind == "pause" and last_pause is None:
            last_pause = event_dt
        elif kind == "resume" and last_pause is not None:
            paused += (event_dt - last_pause).total_seconds()
            last_pause = None
    if last_pause is not None:
        paused += (at_dt - last_pause).total_seconds()
    return max(0.0, wall - paused)


def _normalize_recording_view_event(payload: Mapping[str, Any] | None) -> Dict[str, Any]:
    body = payload or {}
    event: Dict[str, Any] = {
        "schema": "recording_view_event_v1",
        "at_iso": datetime.now(timezone.utc).isoformat(),
    }
    for field in _RECORDING_OPTIONAL_EVENT_FIELDS:
        event[field] = body.get(field)

    event["is_key_window"] = _recording_bool(body.get("is_key_window"))
    event["is_operator_active"] = _recording_bool(body.get("is_operator_active"))

    if not event.get("surface_id"):
        event["surface_id"] = event.get("view_id") or event.get("native_lens") or event.get("window_id")
    if not event.get("view_id") and event.get("surface_id"):
        event["view_id"] = event.get("surface_id")
    if not event.get("surface_kind"):
        event["surface_kind"] = "native" if event.get("native_lens") else "web"
    return event


def _recording_event_is_operator_active(event: Mapping[str, Any]) -> bool:
    source = str(event.get("source") or "").strip().lower()
    runtime_mode = str(event.get("runtime_mode") or "").strip().lower()

    if source == "zenith_host":
        return bool(event.get("is_key_window") or event.get("is_operator_active"))

    if runtime_mode == "embedded" or source == "embedded_spa":
        return False

    # Legacy browser telemetry had no source/runtime metadata. Preserve it as
    # the browser-mode active fallback so existing recording flows still work.
    if not runtime_mode or runtime_mode in {"web", "browser"}:
        return True

    return bool(event.get("is_operator_active"))


def _recording_event_is_browser_fallback(event: Mapping[str, Any]) -> bool:
    source = str(event.get("source") or "").strip().lower()
    runtime_mode = str(event.get("runtime_mode") or "").strip().lower()
    return source in {"", "browser_spa"} and (not runtime_mode or runtime_mode in {"web", "browser"})


def _recording_event_with_session_time(
    event: Dict[str, Any],
    active: Mapping[str, Any],
) -> tuple[Dict[str, Any], Optional[str]]:
    take_root = Path(str(active["take_root"]))
    session_path = take_root / "session.json"
    if session_path.exists():
        try:
            session = json.loads(session_path.read_text(encoding="utf-8"))
            wall = (
                datetime.fromisoformat(event["at_iso"])
                - datetime.fromisoformat(session["created_at"])
            ).total_seconds()
            event["wall_t_seconds"] = round(max(0.0, wall), 3)
            event["video_t_seconds"] = round(
                _recording_video_t_seconds(session, event["at_iso"]), 3
            )
        except (KeyError, ValueError):
            pass

        jsonl_path = take_root / "view_telemetry.jsonl"
        try:
            jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            with jsonl_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True) + "\n")
            return event, str(jsonl_path)
        except OSError as exc:
            logger.warning(f"Failed to append view_telemetry event: {exc}")
    return event, None


def _recording_replay_current_surface_to_take(
    current: Mapping[str, Any] | None,
    active: Mapping[str, Any],
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not current or not _recording_event_is_operator_active(current):
        return None, None

    event = copy.deepcopy(dict(current))
    source_at_iso = event.get("at_iso")
    event["at_iso"] = datetime.now(timezone.utc).isoformat()
    event["replayed_to_take"] = True
    if source_at_iso:
        event["replay_source_at_iso"] = source_at_iso
    event.pop("wall_t_seconds", None)
    event.pop("video_t_seconds", None)
    return _recording_event_with_session_time(event, active)


def _recording_clean_take_title(value: Any) -> Optional[str]:
    text = re.sub(r"\s+", " ", str(value or "").strip())[:120]
    return text or None


@app.put("/api/recording/active-take")
def recording_set_active_take(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Register a demo-take-console take as the active recording target.

    Body: {"take_id": "take_...", "take_root": "/abs/path/to/take"}
    Returns the registered active take or clears it when both are missing.
    """
    take_id = (payload or {}).get("take_id")
    take_root = (payload or {}).get("take_root")
    take_title = _recording_clean_take_title((payload or {}).get("title") or (payload or {}).get("take_title"))
    resolved_take_root: Optional[Path] = None
    if take_root:
        resolved_take_root = _recording_take_root_from_payload(str(take_root))
    with _recording_lock:
        if not take_id or not take_root:
            _recording_state["active_take"] = None
            return {
                "active_take": None,
                "replayed_current_surface_to_take": False,
                "replayed_to": None,
            }
        record = {
            "take_id": take_id,
            "take_root": str(resolved_take_root),
            "title": take_title,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        _recording_state["active_take"] = record
        current = copy.deepcopy(_recording_state.get("current_surface"))

    replayed_event, replayed_to = _recording_replay_current_surface_to_take(current, record)
    if replayed_to and replayed_event:
        with _recording_lock:
            recent: list = _recording_state["recent_events"]
            recent.append(replayed_event)
            if len(recent) > _RECORDING_RECENT_EVENT_CAP:
                del recent[: len(recent) - _RECORDING_RECENT_EVENT_CAP]

    return {
        "active_take": record,
        "replayed_current_surface_to_take": replayed_to is not None,
        "replayed_to": replayed_to,
        "replayed_event": replayed_event,
    }


@app.delete("/api/recording/active-take")
def recording_clear_active_take() -> Dict[str, Any]:
    with _recording_lock:
        previous = _recording_state.get("active_take")
        _recording_state["active_take"] = None
        return {"cleared": previous}


@app.get("/api/recording/active-take")
def recording_get_active_take() -> Dict[str, Any]:
    with _recording_lock:
        return {"active_take": _recording_state.get("active_take")}


@app.post("/api/recording/view-event")
def recording_view_event(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Record a single view event for demo-take active-surface telemetry.

    Body: {"route": "/station/intelligence", "view_id": "intelligence",
           "view_label": "Intelligence", "pathname": "...", "search": "...",
           "hash": "..."} plus optional host/window activity fields.
    The server adds at_iso server-side. When an active recording take is set,
    operator-active events also land as JSONL lines in <take_root>/view_telemetry.jsonl
    with derived wall_t_seconds and video_t_seconds. Raw recent events remain diagnostic.
    """
    event = _normalize_recording_view_event(payload)
    operator_active = _recording_event_is_operator_active(event)
    suppressed_by_host_surface = False

    with _recording_lock:
        active = dict(_recording_state["active_take"]) if _recording_state.get("active_take") else None
        current_surface = copy.deepcopy(_recording_state.get("current_surface"))

    if (
        operator_active
        and _recording_event_is_browser_fallback(event)
        and isinstance(current_surface, Mapping)
        and str(current_surface.get("source") or "").strip().lower() == "zenith_host"
    ):
        operator_active = False
        suppressed_by_host_surface = True

    persisted_to: Optional[str] = None
    state_event = copy.deepcopy(event)
    if active and operator_active:
        event, persisted_to = _recording_event_with_session_time(event, active)

    with _recording_lock:
        recent: list = _recording_state["recent_events"]
        recent.append(event)
        if len(recent) > _RECORDING_RECENT_EVENT_CAP:
            del recent[: len(recent) - _RECORDING_RECENT_EVENT_CAP]
        if operator_active:
            _recording_state["current_surface"] = state_event
    return {
        "event": event,
        "operator_active": operator_active,
        "persisted_to": persisted_to,
        "suppressed_by_host_surface": suppressed_by_host_surface,
    }


@app.get("/api/recording/current-surface")
def recording_current_surface() -> Dict[str, Any]:
    with _recording_lock:
        current = copy.deepcopy(_recording_state.get("current_surface"))
        active_take = copy.deepcopy(_recording_state.get("active_take"))
        recent_count = len(_recording_state.get("recent_events") or [])
    return {
        "current_surface": current,
        "has_active_take": active_take is not None,
        "recent_event_count": recent_count,
    }


@app.get("/api/recording/recent-view-events")
def recording_recent_view_events(limit: int = Query(20, ge=1, le=200)) -> Dict[str, Any]:
    with _recording_lock:
        recent = list(_recording_state["recent_events"])
    return {"count": len(recent), "events": recent[-limit:]}


# --- DEMO TAKE FRONTEND PROJECTION ---
# Read-only view models for a future recorder frontend. Keep projection logic in
# tools/meta/dissemination/demo_take_projection.py so the server surface remains
# a thin transport layer and tests can exercise the JSON model without FastAPI.

def _demo_take_recording_state_snapshot() -> Dict[str, Any]:
    with _recording_lock:
        return copy.deepcopy(_recording_state)


def _demo_take_bind_active_from_receipt(receipt: Mapping[str, Any]) -> None:
    if receipt.get("status") != "pass":
        return
    result = receipt.get("result") if isinstance(receipt.get("result"), Mapping) else {}
    take_id = result.get("take_id")
    take_root = result.get("take_root")
    support_result = result.get("support_result") if isinstance(result.get("support_result"), Mapping) else {}
    take_id = take_id or support_result.get("takeID")
    take_root = take_root or support_result.get("rootPath")
    take_title = _recording_clean_take_title(result.get("title") or support_result.get("title"))
    if not take_id or not take_root:
        return
    with _recording_lock:
        current = _recording_state.get("active_take")
        if isinstance(current, Mapping) and current.get("take_id") == str(take_id):
            current_root = current.get("take_root")
            if current_root and Path(str(current_root)).exists():
                return
    if isinstance(take_root, str) and take_root.startswith("repo://"):
        take_root = str((REPO_ROOT / take_root.removeprefix("repo://")).resolve())
    try:
        resolved = _recording_take_root_from_payload(str(take_root))
    except HTTPException:
        return
    with _recording_lock:
        _recording_state["active_take"] = {
            "take_id": str(take_id),
            "take_root": str(resolved),
            "title": take_title,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }


def _demo_take_clear_active_if_receipt_passed(receipt: Mapping[str, Any], take_id: str) -> None:
    if receipt.get("status") != "pass":
        return
    with _recording_lock:
        active = _recording_state.get("active_take")
        if isinstance(active, Mapping) and active.get("take_id") == take_id:
            _recording_state["active_take"] = None


def _demo_take_projection_module():
    from tools.meta.dissemination import demo_take_projection

    return demo_take_projection


@app.get("/api/demo-takes/frontend-snapshot")
def demo_takes_frontend_snapshot(mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    try:
        return projection.build_frontend_snapshot(
            mode=mode,
            repo_root=REPO_ROOT,
            active_take=recording_state.get("active_take"),
            recent_events=recording_state.get("recent_events", []),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/demo-takes/editor-snapshot")
def demo_takes_editor_snapshot(
    take_id: Optional[str] = Query(default=None),
    mode: str = Query("calibration", pattern="^(calibration|production)$"),
) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    try:
        return projection.build_editor_snapshot(
            take_id=take_id,
            mode=mode,
            repo_root=REPO_ROOT,
            active_take=recording_state.get("active_take"),
            recent_events=recording_state.get("recent_events", []),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/demo-takes/sources")
def demo_takes_sources(mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    snapshot = projection.build_frontend_snapshot(mode=mode, repo_root=REPO_ROOT)
    return snapshot["sources"]


@app.get("/api/demo-takes/mic-levels")
def demo_takes_mic_levels(mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    doctor = projection.cached_doctor_report(mode=mode, repo_root=REPO_ROOT)
    config = projection.load_config(repo_root=REPO_ROOT)
    return projection.build_mic_levels(doctor, config=config, repo_root=REPO_ROOT)


@app.get("/api/demo-takes/config")
def demo_takes_config(mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    doctor = projection.cached_doctor_report(mode=mode, repo_root=REPO_ROOT)
    config = projection.load_config(repo_root=REPO_ROOT)
    sources = projection.build_sources_from_doctor(doctor, config=config, repo_root=REPO_ROOT)
    return projection.build_config_projection(config=config, sources=sources, repo_root=REPO_ROOT)


@app.put("/api/demo-takes/config")
def demo_takes_update_config(payload: Dict[str, Any] = Body(...), mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    try:
        config = projection.save_config(payload, repo_root=REPO_ROOT)
        doctor = projection.cached_doctor_report(mode=mode, repo_root=REPO_ROOT)
        sources = projection.build_sources_from_doctor(doctor, config=config, repo_root=REPO_ROOT)
        return projection.build_config_projection(config=config, sources=sources, repo_root=REPO_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/demo-takes/actions/doctor")
def demo_takes_action_doctor(mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    return projection.refresh_doctor_operation(mode=mode, repo_root=REPO_ROOT)


@app.post("/api/demo-takes/actions/refresh-source-snapshots")
def demo_takes_action_refresh_source_snapshots(mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    return projection.refresh_source_snapshots_operation(mode=mode, repo_root=REPO_ROOT)


@app.post("/api/demo-takes/actions/start")
def demo_takes_action_start(payload: Optional[Dict[str, Any]] = Body(default=None), mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    try:
        receipt = projection.start_recording_operation(payload=payload or {}, mode=mode, repo_root=REPO_ROOT, active_take=recording_state.get("active_take"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _demo_take_bind_active_from_receipt(receipt)
    return receipt


@app.post("/api/demo-takes/actions/import-video")
def demo_takes_action_import_video(payload: Dict[str, Any] = Body(...), mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    try:
        return projection.import_video_operation(payload=payload or {}, mode=mode, repo_root=REPO_ROOT, active_take=recording_state.get("active_take"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/demo-takes/actions/fake-lifecycle")
def demo_takes_action_fake_lifecycle(payload: Optional[Dict[str, Any]] = Body(default=None), mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    body = payload or {}
    try:
        return projection.fake_lifecycle_operation(take_id=body.get("take_id"), mode=mode, repo_root=REPO_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/demo-takes/actions/calibration-live")
def demo_takes_action_calibration_live(payload: Optional[Dict[str, Any]] = Body(default=None)) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    try:
        return projection.calibration_live_operation(payload=payload or {}, repo_root=REPO_ROOT, active_take=recording_state.get("active_take"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/demo-takes/operations")
def demo_takes_operations(limit: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    return projection.list_operations(repo_root=REPO_ROOT, limit=limit)


@app.get("/api/demo-takes/operations/{operation_id}")
def demo_takes_operation(operation_id: str) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    try:
        return projection.load_operation(operation_id, repo_root=REPO_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/demo-takes/{take_id}/actions/pause")
def demo_take_action_pause(take_id: str, mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    try:
        return projection.pause_recording_operation(take_id, mode=mode, repo_root=REPO_ROOT, active_take=recording_state.get("active_take"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/demo-takes/{take_id}/actions/resume")
def demo_take_action_resume(take_id: str, mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    try:
        return projection.resume_recording_operation(take_id, mode=mode, repo_root=REPO_ROOT, active_take=recording_state.get("active_take"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/demo-takes/{take_id}/actions/stop")
def demo_take_action_stop(take_id: str, mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    try:
        receipt = projection.stop_recording_operation(take_id, mode=mode, repo_root=REPO_ROOT, active_take=recording_state.get("active_take"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _demo_take_clear_active_if_receipt_passed(receipt, take_id)
    return receipt


@app.post("/api/demo-takes/{take_id}/actions/mark")
def demo_take_action_mark(take_id: str, payload: Optional[Dict[str, Any]] = Body(default=None), mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    label = (payload or {}).get("label")
    try:
        return projection.mark_recording_operation(take_id, label=str(label) if label is not None else None, mode=mode, repo_root=REPO_ROOT, active_take=recording_state.get("active_take"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/demo-takes/{take_id}/actions/set-title")
def demo_take_action_set_title(take_id: str, payload: Dict[str, Any] = Body(...), mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    try:
        return projection.set_take_title_operation(take_id, payload=payload or {}, mode=mode, repo_root=REPO_ROOT, active_take=recording_state.get("active_take"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/demo-takes/{take_id}/actions/audit")
def demo_take_action_audit(take_id: str, mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    try:
        return projection.audit_operation(take_id, mode=mode, repo_root=REPO_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/demo-takes/{take_id}/actions/repair")
def demo_take_action_repair(take_id: str, mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    try:
        return projection.repair_operation(take_id, mode=mode, repo_root=REPO_ROOT, active_take=recording_state.get("active_take"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/demo-takes/{take_id}/actions/rebuild-intent-events")
def demo_take_action_rebuild_intent_events(take_id: str, mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    try:
        return projection.rebuild_intent_events_operation(take_id, mode=mode, repo_root=REPO_ROOT, active_take=recording_state.get("active_take"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/demo-takes/{take_id}/actions/export-video")
def demo_take_action_export_video(take_id: str, mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    try:
        return projection.export_video_operation(take_id, mode=mode, repo_root=REPO_ROOT, active_take=recording_state.get("active_take"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/demo-takes/{take_id}/actions/archive-originals")
def demo_take_action_archive_originals(
    take_id: str,
    payload: Optional[Dict[str, Any]] = Body(default=None),
    mode: str = Query("calibration", pattern="^(calibration|production)$"),
) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    recording_state = _demo_take_recording_state_snapshot()
    try:
        return projection.archive_originals_operation(
            take_id,
            payload=payload or {},
            mode=mode,
            repo_root=REPO_ROOT,
            active_take=recording_state.get("active_take"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/demo-takes")
def demo_takes_list(mode: str = Query("calibration", pattern="^(calibration|production)$"), limit: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    return projection.build_take_cards(repo_root=REPO_ROOT, mode=mode, limit=limit)


@app.get("/api/demo-takes/exports")
def demo_take_exports(limit: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    return projection.build_export_index(repo_root=REPO_ROOT, limit=limit)


@app.get("/api/demo-takes/exports/publication-gate")
def demo_take_export_publication_gate(
    asset_path: Optional[str] = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    try:
        return projection.build_export_publication_gate(repo_root=REPO_ROOT, asset_path=asset_path, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/demo-takes/exports/asset/{relative_path:path}")
def demo_take_export_asset(relative_path: str):
    projection = _demo_take_projection_module()
    try:
        target = projection.resolve_export_asset(relative_path, repo_root=REPO_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="export asset not found")
    return FileResponse(
        target,
        media_type=projection.export_asset_mime_type(relative_path),
        stat_result=target.stat(),
        content_disposition_type="inline",
        headers={"Accept-Ranges": "bytes", "X-Content-Type-Options": "nosniff"},
    )


@app.get("/api/demo-takes/{take_id}/asset/{relative_path:path}")
def demo_take_asset(take_id: str, relative_path: str):
    projection = _demo_take_projection_module()
    try:
        target = projection.resolve_take_asset(take_id, relative_path, repo_root=REPO_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="asset not found")
    return FileResponse(
        target,
        media_type=None,
        stat_result=target.stat(),
        content_disposition_type="inline",
        headers={"Accept-Ranges": "bytes"},
    )


@app.get("/api/demo-takes/source-assets/{relative_path:path}")
def demo_take_source_asset(relative_path: str):
    projection = _demo_take_projection_module()
    try:
        target = projection.resolve_source_asset(relative_path, repo_root=REPO_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="source asset not found")
    return FileResponse(
        target,
        media_type=None,
        stat_result=target.stat(),
        content_disposition_type="inline",
        headers={"Accept-Ranges": "bytes"},
    )


@app.get("/api/demo-takes/scene-plans/{plan_id}/asset/{relative_path:path}")
def demo_take_scene_plan_asset(plan_id: str, relative_path: str):
    projection = _demo_take_projection_module()
    try:
        target = projection.resolve_scene_plan_asset(plan_id, relative_path, repo_root=REPO_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="scene-plan asset not found")
    return FileResponse(
        target,
        media_type=None,
        stat_result=target.stat(),
        content_disposition_type="inline",
        headers={"Accept-Ranges": "bytes"},
    )


@app.get("/api/demo-takes/{take_id}")
def demo_take_detail(take_id: str, mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    try:
        return projection.build_take_detail(take_id, repo_root=REPO_ROOT, mode=mode)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/demo-takes/{take_id}/audit")
def demo_take_audit(take_id: str, mode: str = Query("calibration", pattern="^(calibration|production)$")) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    try:
        return projection.build_take_audit(take_id, repo_root=REPO_ROOT, mode=mode)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/demo-takes/{take_id}/postprocess")
def demo_take_postprocess(take_id: str) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    try:
        return projection.build_take_postprocess(take_id, repo_root=REPO_ROOT)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/demo-takes/{take_id}/timeline")
def demo_take_timeline(take_id: str) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    try:
        return projection.build_take_timeline(take_id, repo_root=REPO_ROOT)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/demo-takes/{take_id}/intent-events")
def demo_take_intent_events(take_id: str) -> Dict[str, Any]:
    projection = _demo_take_projection_module()
    try:
        return projection.build_take_intent_events(take_id, repo_root=REPO_ROOT)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- FRONTEND CATCH-ALL ---
# MUST be registered last to avoid capturing API routes.

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """
    [ACTION]
    - Teleology: Serve the frontend SPA assets or fallback to index.html for client-side routing.
    - Mechanism: Rejects unknown backend API paths; otherwise checks if requested path exists in static dir and falls back to index.html for client-side routing.
    - Reads: Filesystem under static directory.
    - Writes: None.
    - Fails: File access errors -> propagate.
    - Guarantee: Returns a FileResponse, an HTML static-bundle fallback, or an API/asset error.
    """
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    possible_static = _static_file_under_root(full_path)
    if possible_static.exists() and possible_static.is_file():
        return FileResponse(str(possible_static))
    if _static_asset_request(full_path):
        raise HTTPException(status_code=404, detail="Static frontend asset not found")
    index = static_dir / "index.html"
    if not index.exists():
        return _frontend_bundle_missing_response(full_path)
    return FileResponse(str(index))
