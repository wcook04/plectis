"""
[PURPOSE]
- Teleology: Define the server-facing API contracts (enums + Pydantic models) used by the UI client and server routes.
- Mechanism: Declarative schemas (BaseModel/Enum) that stabilize JSON shapes and Literal/Enum value sets across the boundary.
- Non-goal: Business logic, IO, orchestration, or runtime side effects.

[INTERFACE]
- Exports:
  - Enums: RunMode, ExecutionMode, MissionStatus, LaneEnum, CodexNodeStatus
  - Lobby: CandidateRun, Mission, BridgeStatus, LobbyState
  - Ignite: IgnitePayload, IgnitionResponse, StopRunResponse
  - Topology: TopologyError, NodeView, EdgeView, GraphSnapshot
  - Runtime: RunStatusVector, LogLine, RunSummary, ToolRunTelemetry
  - Config: RunRequest, UIConfig
  - Inspector: CodexTreeNodeSchema, CodexTreeStatsSchema, CodexTreeResponse, TreeSnapshotModeSchema, CodexFileDetailSchema, BatchReadRequest, BatchReadResponse, PruneRequest, PruneResponse
  - Meta: MetaEnvelope, MetaApplyRequest, MetaObserveRequest, MetaPatchRequest, MetaBuildRequest
  - Meta Result Payloads: ApplyResultData, PatchRecord, MetaPatchResultData and BuildSummarySchema
  - Build: BuildPhaseSchema, BuildSummarySchema
- Schema: Pydantic v2 models (BaseModel) with Field metadata; enums are str-backed for JSON stability.

[FLOW]
- Reads: HTTP JSON payloads (request bodies) validated into these models by server routing layers.
- Writes: None (definitions only).
- Couples: Client TypeScript and server routes assume these field names and Enum/Literal values.

[DEPENDENCIES]
- pypi.pydantic: BaseModel, Field, model_validator, ConfigDict (API contracts)

[CONSTRAINTS]
- Guarantee: Enum member string values and Literal spellings remain stable API identifiers.
- Forbid: Import-time side effects, filesystem/network IO, or runtime service coupling inside this module.
- Orders: Any rename/removal of fields or Enum values requires coordinated client update.
- Fails: Validation surfaces as Pydantic validation errors and/or ValueError raised by validators.
- When-needed: Open when a server-backend change needs the canonical request/response schema surface before touching routes, controllers, or client payload handling.
- Escalates-to: system/server/main.py; system/server/meta_service.py; system/server/session.py
- Navigation-group: server_backend
"""
# system/server/schemas.py

from enum import Enum
from typing import List, Optional, Dict, Literal, Any, Generic, TypeVar, Annotated, Union
from pydantic import BaseModel, Field, model_validator, ConfigDict, AliasChoices, field_validator
from system.lib.types import RunMode, ExecutionMode, VALID_LANES as _VALID_LANES

# =============================================================================
# 1. CORE ENUMS
# =============================================================================
# RunMode and ExecutionMode are imported from system.lib.types (canonical source).

class MissionStatus(str, Enum):
    """
    [ROLE]
    - Teleology: Communicate mission topology health to the client lobby.
    - Mechanism: str-backed Enum mapped to UI health states.
    - Guarantee: Stable identifiers: "READY", "BROKEN", "REQUIRES_BRIDGE".
    - Forbid: Renaming values without coordinating UI expectations.
    """
    READY = "READY"
    BROKEN = "BROKEN" 
    REQUIRES_BRIDGE = "REQUIRES_BRIDGE"

# LaneEnum is generated from VALID_LANES in system/lib/types.py — that is the single
# source of truth. To add a lane: add it to VALID_LANES there; nowhere else in Python.
LaneEnum: type = Enum(  # type: ignore[assignment]
    "LaneEnum",
    {lane: lane for lane in _VALID_LANES},
    type=str,
)

# =============================================================================
# 2. LOBBY STATE (Server -> Client)
# =============================================================================

class MarketSessionContext(BaseModel):
    """
    [ROLE]
    - Teleology: Carry exchange and session-phase context for market-aware lobby display.
    - Ownership: Session-phase flags, price regime label, and open/extended-hours booleans.
    - Mutability: Immutable once constructed from server-side computation.
    - Concurrency: Read-only value object; no shared mutable state.
    """
    exchange: Literal["NYSE"] = "NYSE"
    anchor_time_iso: Optional[str] = None
    session_phase: Literal["pre", "regular", "after", "closed", "weekend", "unknown"] = "unknown"
    is_market_open: bool = False
    is_extended_hours: bool = False
    price_regime: Literal["live", "extended", "reference", "unknown"] = "unknown"
    label: Optional[str] = None


class DataRootContext(BaseModel):
    """
    [ROLE]
    - Teleology: Describe the canonical source-data snapshot that a run is derived from.
    - Ownership: Root run id, lineage depth, lineage run ids, and associated market context.
    - Mutability: Immutable once constructed.
    - Concurrency: Read-only value object; no shared mutable state.
    """
    root_run_id: Optional[str] = None
    immediate_parent_run_id: Optional[str] = None
    root_run_timestamp_iso: Optional[str] = None
    root_data_as_of_iso: Optional[str] = None
    canonical_time_iso: Optional[str] = None
    lineage_depth: int = 0
    lineage_run_ids: List[str] = Field(default_factory=list)
    relation: Literal["self", "source_run", "feed_source", "truth_run"] = "self"
    is_reused: bool = False
    market: MarketSessionContext = Field(default_factory=MarketSessionContext)


class RunLineageContext(BaseModel):
    """
    [ROLE]
    - Teleology: Bundle the primary and truth data-root contexts for a run's lineage display.
    - Ownership: Primary DataRootContext and optional truth DataRootContext.
    - Mutability: Immutable once constructed.
    - Concurrency: Read-only value object; no shared mutable state.
    """
    primary: DataRootContext = Field(default_factory=DataRootContext)
    truth: Optional[DataRootContext] = None


class TemporalContext(BaseModel):
    """
    [ROLE]
    - Teleology: Carry temporal/provenance metadata needed for run pairing and display.
    - Mechanism: Embedded as CandidateRun.temporal.
    - Guarantee: Optional additive fields only; safe for backward-compatible client reads.
    """
    horizon_policy: Optional[str] = None
    horizon_label: Optional[str] = None
    target_time_iso: Optional[str] = None
    source_run_id: Optional[str] = None
    feed_source_run_id: Optional[str] = None
    run_timestamp_iso: Optional[str] = None
    data_as_of_iso: Optional[str] = None
    original_run_timestamp_iso: Optional[str] = None
    last_ignited_at_iso: Optional[str] = None
    lineage: RunLineageContext = Field(default_factory=RunLineageContext)


class DataRootSummary(BaseModel):
    """
    [ROLE]
    - Teleology: Summarize one canonical source-data snapshot shared by one or more runs.
    - Mechanism: Lobby-level grouped view derived from CandidateRun.temporal.lineage.primary.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: str
    root_run_id: str
    canonical_time_iso: Optional[str] = None
    canonical_timestamp: Optional[float] = None
    data_as_of_iso: Optional[str] = None
    run_timestamp_iso: Optional[str] = None
    market: MarketSessionContext = Field(default_factory=MarketSessionContext)
    member_run_ids: List[str] = Field(default_factory=list)
    member_count: int = 0
    derived_run_count: int = 0
    mission_names: List[str] = Field(default_factory=list)
    latest_member_run_id: Optional[str] = None
    usable_for_feeds: bool = False
    feed_run_id: Optional[str] = None
    status: Literal["green", "amber", "red"] = Field(default="amber")
    has_green_run: bool = False
    future_root_ids: List[str] = Field(default_factory=list)
    future_root_count: int = 0

class CandidateRun(BaseModel):
    """
    [ROLE]
    - Teleology: Summarize a historical run for lobby selection (resume/fork/oracle inputs).
    - Mechanism: Pydantic model used in LobbyState.candidates.
    - Guarantee: Provides run identifiers plus lightweight counts/flags for UI filtering.
    - Fails: Pydantic validation errors on malformed payloads.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: str
    timestamp: float
    mission_name: str = Field(default="unknown")
    time_label: str = Field(default="")
    status: Literal["green", "amber", "red"] = Field(default="amber")
    
    valid_for_oracle: bool = Field(default=False)
    valid_for_feeds: bool = Field(default=False)
    valid_for_resume: bool = Field(default=True)
    
    feed_count: int = 0
    feeds_present: List[str] = Field(default_factory=list)
    artifact_count: int = 0
    tool_artifact_count: int = 0
    reasoning_artifact_count: int = 0
    data_timestamp: Optional[float] = None

    # [PHASE 3 ENRICHMENT]
    tier: str = Field(default="Unknown")
    era: str = Field(default="Unknown")
    is_pinned: bool = Field(default=False)
    pinned_by: List[str] = Field(default_factory=list)
    # [REGRADE] Whether status comes from original run_summary or regrade_summary
    status_source: Literal["original", "regraded"] = Field(default="original")
    original_status: Optional[str] = Field(default=None)
    grade_reason: Optional[str] = Field(default=None)
    sink_id: Optional[str] = Field(default=None)
    closure_proof: Optional[bool] = Field(default=None)
    temporal: TemporalContext = Field(default_factory=TemporalContext)

class Mission(BaseModel):
    """
    [ROLE]
    - Teleology: Represent a mission (graph target) plus its readiness and requirements.
    - Mechanism: Pydantic model used in LobbyState.missions.
    - Guarantee: Carries the resolved target sink id and topology health status.
    - Fails: Pydantic validation errors on malformed payloads.
    - Config: serialization-required keeps the requirements default and the
      Optional last_run_id / error fields required on the wire so the
      generated TS narrows correctly.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    name: str = Field(description="Display name (e.g., 'lab', 'surveillance').")
    target_id: str = Field(description="The calculated Sink Node ID (e.g., 'decide_v2').")
    status: MissionStatus = Field(description="Health status of the mission topology.")
    
    requirements: List[str] = Field(default_factory=list)
    last_run_id: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)

class BridgeStatus(BaseModel):
    """
    [ROLE]
    - Teleology: Report Bridge configuration + liveness to gate REQUIRES_BRIDGE flows.
    - Mechanism: Pydantic model embedded in LobbyState.
    - Guarantee: Exposes boolean status flags only (no runtime control).
    - Non-goal: Performing Bridge checks (computed elsewhere).
    """
    configured: bool
    alive: bool

class LobbyState(BaseModel):
    """
    [ROLE]
    - Teleology: Aggregate lobby hydration payload (missions, candidate runs, bridge status).
    - Mechanism: Pydantic model returned by server->client lobby endpoint(s).
    - Guarantee: Single snapshot object sufficient for initial UI render.
    - Fails: Pydantic validation errors on malformed payloads.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    missions: List[Mission]
    candidates: List[CandidateRun]
    data_roots: List[DataRootSummary] = Field(default_factory=list)
    bridge_status: BridgeStatus


class BridgeTabState(BaseModel):
    """
    [ROLE]
    - Teleology: Describe one live browser tab as seen by the bridge debug surface.
    """
    id: str = ""
    title: str = ""
    url: str = ""
    phase: Literal["idle", "ready", "composing", "submitted", "running", "done", "cancelled", "inspect_error"] = "idle"
    active: bool = False
    visibility: str = ""
    started: bool = False
    done: bool = False
    cancelled: bool = False
    editor_exists: bool = False
    editor_length: int = 0
    editor_preview: str = ""
    body_preview: str = ""
    response_count: int = 0
    response_preview: str = ""
    wait_state: Dict[str, Any] = Field(default_factory=dict)
    inspect_error: Optional[str] = None


class BridgeInteractionOwner(BaseModel):
    """
    [ROLE]
    - Teleology: Identify the caller that currently holds a provider's bridge
      interaction lock so the UI can show *who* is blocking the queue, not a
      bare flag. The shape mirrors what BridgeManager._provider_interaction_
      snapshot emits — a dict of {node_id, lock_path, process_id, ...}.
    """
    node_id: Optional[str] = None
    lock_path: Optional[str] = None
    process_id: Optional[int] = None
    # Keep forward compat for any additional keys (e.g. claim_ts) the bridge
    # may start emitting without breaking the schema.
    model_config = ConfigDict(extra="allow")


class BridgeProviderDiagnostics(BaseModel):
    """
    [ROLE]
    - Teleology: Carry one provider's runtime bridge health plus live tab states.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    provider: str
    target_url: Optional[str] = None
    stale: Optional[bool] = None
    stale_reason: Optional[str] = None
    last_success_age_s: Optional[float] = None
    interaction_active: bool = False
    interaction_waiters: int = 0
    interaction_owner: Optional[BridgeInteractionOwner] = None
    tab_count: int = 0
    phase_counts: Dict[str, int] = Field(default_factory=dict)
    tabs: List[BridgeTabState] = Field(default_factory=list)
    provider_state: Dict[str, Any] = Field(default_factory=dict)
    live_error: Optional[str] = None


class BridgeDiagnosticsResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Return the bridge observability packet shared by kernel/server/UI.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    captured_at: str
    configured: bool
    browser_running: bool
    cdp_reachable: bool
    debug_url: Optional[str] = None
    providers: Dict[str, BridgeProviderDiagnostics] = Field(default_factory=dict)
    error: Optional[str] = None


class BridgePreflightResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Return the full preflight run logs plus a structured bridge diagnostics snapshot.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    status: Literal["success", "error"]
    command: str
    returncode: int
    logs: str
    diagnostics: BridgeDiagnosticsResponse


class StationLauncherAlert(BaseModel):
    """
    [ROLE]
    - Teleology: One compact signal row for the station launcher's alert rail.
    - Mechanism: Minimal additive shape so the launcher can render operational
      signals without coupling to the full underlying source payload.
    """
    id: str
    tone: Literal["ok", "warn", "block", "info"] = "info"
    label: str
    detail: Optional[str] = None
    command: Optional[str] = None


class StationLauncherOperation(BaseModel):
    """
    [ROLE]
    - Teleology: One quick action surfaced on the station launcher.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    operation_id: str
    label: str
    kicker: str
    description_short: str
    command: Optional[str] = None
    parameters_schema: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    dispatch_policy: Dict[str, Any] = Field(default_factory=dict)
    ui_group: Optional[str] = None
    execution_mode: Literal["sync", "detached"] = "sync"
    principle_refs: List[str] = Field(default_factory=list)
    runtime_attention: Dict[str, Any] = Field(default_factory=dict)
    # Present when the operation maps to a registered meta-mission career. The
    # server enriches this from meta_mission_registry.json + the workspace so the
    # cockpit can render last-run status next to the launcher tile.
    meta_mission: Dict[str, Any] = Field(default_factory=dict)


class StationRawSeedPipelineSnapshot(BaseModel):
    """
    [ROLE]
    - Teleology: Compact queue/accounting view for the family raw-seed atomize ->
      route loop so the Station home surface can expose backlog pressure and
      provider-safe dispatch settings without reading multiple artifacts.
    """
    family_dir: Optional[str] = None
    family_number: Optional[str] = None
    extracted_shards_path: Optional[str] = None
    raw_seed_shards_path: Optional[str] = None
    raw_seed_coverage_path: Optional[str] = None
    raw_seed_coverage_enriched_path: Optional[str] = None
    raw_seed_routing_review_path: Optional[str] = None
    codex_surface_queue_path: Optional[str] = None
    total_paragraphs: int = 0
    total_bins: int = 0
    paragraph_level_shards: int = 0
    atomized_shards: int = 0
    paragraphs_without_atoms: int = 0
    atomization_success_paragraphs: int = 0
    atomization_retryable_paragraphs: int = 0
    atomization_failed_paragraphs: int = 0
    atomization_pending_paragraphs: int = 0
    pending_routing_shards: int = 0
    pending_routing_bins: int = 0
    review_queue_entries: int = 0
    review_queue_bins: int = 0
    fresh_pending_bins: int = 0
    surface_queue_entries: int = 0
    doctrine_with_no_provenance: int = 0
    merge_candidate_count: int = 0
    orphan_cluster_count: int = 0
    provider: Optional[str] = None
    cohort_size: int = 0
    wave_width_requested: Optional[Any] = None
    wave_width_effective: int = 0
    provider_ceiling: int = 0
    queue_depth: int = 0
    effective_active_workers: int = 0
    safe_parallelism: int = 0
    last_updated: Optional[str] = None


class StationOvernightChainProgress(BaseModel):
    completed_steps: int = 0
    total_steps: int = 0
    current_step_id: Optional[str] = None
    current_step_index: Optional[int] = None


class StationOvernightChainResumeSeam(BaseModel):
    step_id: Optional[str] = None
    step_index: Optional[int] = None


class StationProviderWait(BaseModel):
    status: Literal["waiting_provider"] = "waiting_provider"
    source: Optional[str] = None
    provider: Optional[str] = None
    kind: Optional[str] = None
    reason: Optional[str] = None
    recorded_at: Optional[str] = None
    wait_seconds: Optional[int] = None
    cooldown_until: Optional[str] = None
    attempt: Optional[int] = None
    chain_id: Optional[str] = None
    step_id: Optional[str] = None
    step_index: Optional[int] = None
    item_id: Optional[str] = None
    item_index: Optional[int] = None


class StationOvernightChainSnapshot(BaseModel):
    chain_id: Optional[str] = None
    chain_run_id: Optional[str] = None
    terminal_status: Optional[str] = None
    is_running: bool = False
    pid: Optional[int] = None
    log_path: Optional[str] = None
    state_path: Optional[str] = None
    ledger_path: Optional[str] = None
    stop_flag_path: Optional[str] = None
    last_updated: Optional[str] = None
    progress: StationOvernightChainProgress = Field(default_factory=StationOvernightChainProgress)
    next_resume_seam: Optional[StationOvernightChainResumeSeam] = None
    provider_wait: Optional[StationProviderWait] = None
    last_error: Optional[str] = None


class StationOvernightQueueProgress(BaseModel):
    completed_items: int = 0
    total_items: int = 0
    current_item_id: Optional[str] = None
    current_item_index: Optional[int] = None


class StationOvernightQueueResumeSeam(BaseModel):
    item_id: Optional[str] = None
    item_index: Optional[int] = None


class StationOvernightQueueSnapshot(BaseModel):
    queue_id: Optional[str] = None
    queue_run_id: Optional[str] = None
    manifest_path: Optional[str] = None
    terminal_status: Optional[str] = None
    is_running: bool = False
    pid: Optional[int] = None
    log_path: Optional[str] = None
    state_path: Optional[str] = None
    ledger_path: Optional[str] = None
    stop_flag_path: Optional[str] = None
    last_updated: Optional[str] = None
    progress: StationOvernightQueueProgress = Field(default_factory=StationOvernightQueueProgress)
    current_item_id: Optional[str] = None
    current_item_index: Optional[int] = None
    total_items: Optional[int] = None
    next_resume_item_id: Optional[str] = None
    next_resume_item_index: Optional[int] = None
    next_resume_seam: Optional[StationOvernightQueueResumeSeam] = None
    artifact_refs: List[str] = Field(default_factory=list)
    provider_wait: Optional[StationProviderWait] = None
    last_error: Optional[str] = None


class HostAgentRecentThread(BaseModel):
    """
    [ROLE]
    - Teleology: Compact thread row for the host-agent external-surface snapshot.
    - Mechanism: Mirrors the bounded thread preview emitted by the operational
      record miner so Station and other operator surfaces can show recent Codex
      activity without opening host-agent artifacts directly.
    """

    thread_id: Optional[str] = None
    title: Optional[str] = None
    model: Optional[str] = None
    reasoning_effort: Optional[str] = None
    tokens_used: int = 0
    updated_at: Optional[str] = None


class HostAgentWindowSnapshot(BaseModel):
    """
    [ROLE]
    - Teleology: Summary of one mined host-agent observation window (for example
      the 30d or 90d operational-record view).
    - Mechanism: Condenses the report + projection sidecars into counts,
      freshness, and a short recent-thread preview.
    """

    label: str = ""
    days: Optional[int] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    available: bool = False
    since: Optional[str] = None
    scope: Optional[str] = None
    host_dir: Optional[str] = None
    report_path: Optional[str] = None
    projection_path: Optional[str] = None
    report_generated_at: Optional[str] = None
    report_freshness: Dict[str, Any] = Field(default_factory=dict)
    projection_status: Optional[str] = None
    projection_freshness: Dict[str, Any] = Field(default_factory=dict)
    codex_threads: int = 0
    codex_tokens: int = 0
    total_spawn_edges: int = 0
    open_spawn_edges: int = 0
    projection_nodes: int = 0
    projection_edges: int = 0
    cross_scope_edges: int = 0
    log_rows: int = 0
    log_error_rows: int = 0
    queued_follow_ups_count: int = 0
    repo_primary_sessions: int = 0
    repo_worktree_slugs: int = 0
    ide_live_instance_locks: int = 0
    recent_threads: List[HostAgentRecentThread] = Field(default_factory=list)


class HostAgentFindingCard(BaseModel):
    """
    [ROLE]
    - Teleology: One condensed operational-record finding for controller-visible
      handoff and validation.
    - Mechanism: Preserves the routing/promotion semantics without dragging the
      full miner traceability payload into the Station home packet.
    """

    finding_id: str
    signal_class: Optional[str] = None
    promotion_status: Optional[str] = None
    suggested_destination: Optional[str] = None
    paper_module_slug: Optional[str] = None
    instances: int = 0
    affected_surface_count: int = 0
    latest_occurrence_at: Optional[str] = None
    shape_claim: Optional[str] = None
    behaviour_status: Optional[str] = None
    substrate_status: Optional[str] = None


class HostAgentExternalSnapshot(BaseModel):
    """
    [ROLE]
    - Teleology: Read-only projection of the mined Claude/Codex host-agent plane
      so Station and world-model consumers can see deployment/runtime pressure
      from one typed payload.
    - Mechanism: Mirrors the latest operational-record mining run, then exposes
      only the compact counts, paths, freshness, windows, and ranked handoff
      rows that matter for operator navigation.
    """

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["host_agent_external_snapshot_v1"] = Field(
        default="host_agent_external_snapshot_v1",
        alias="schema",
    )
    generated_at: Optional[str] = None
    available: bool = False
    campaign_id: Optional[str] = None
    authored_at: Optional[str] = None
    authored_freshness: Dict[str, Any] = Field(default_factory=dict)
    mining_run_path: Optional[str] = None
    current_window: HostAgentWindowSnapshot = Field(default_factory=HostAgentWindowSnapshot)
    extended_window: HostAgentWindowSnapshot = Field(default_factory=HostAgentWindowSnapshot)
    curate_count: int = 0
    deferred_count: int = 0
    curate: List[HostAgentFindingCard] = Field(default_factory=list)
    deferred: List[HostAgentFindingCard] = Field(default_factory=list)


class MetaDiagnosticsConsoleSummary(BaseModel):
    """
    [ROLE]
    - Teleology: Top-line counts for the read-only meta diagnostics console.
    - Mechanism: Keeps the frontend trust strip typed while allowing future
      read-model counters to flow through without another client-only contract.
    """
    model_config = ConfigDict(extra="allow")

    panel_count: int = 0
    source_count: int = 0
    unavailable_source_count: int = 0
    agent_telemetry_available: bool = False
    agenttrace_monitoring_available: bool = False
    trace_observatory_row_count: Optional[int] = None
    command_efficiency_saved_s: Optional[float] = None
    work_item_count: Optional[int] = None
    route_health_attention_count: Optional[int] = None
    annex_attention_count: Optional[int] = None


class MetaDiagnosticsFrontendContract(BaseModel):
    """Frontend layout and boundary hints carried by the read model."""
    model_config = ConfigDict(extra="allow")

    default_route_suggestion: str
    endpoint: str
    payload_class: str
    recommended_layout: str
    avoid: List[str] = Field(default_factory=list)


class MetaDiagnosticsPanelManifestEntry(BaseModel):
    """One panel advertised by `panel_manifest`."""
    model_config = ConfigDict(extra="allow")

    panel_id: str
    title: str
    data_ref: str
    recommended_visual: str
    why_useful: str
    source_refs: List[str] = Field(default_factory=list)


class MetaDiagnosticsSourceHealthEntry(BaseModel):
    """Source availability row for one backing projection."""
    model_config = ConfigDict(extra="allow")

    source_path: str
    available: bool
    generated_at: Optional[str] = None
    freshness: Dict[str, Any] = Field(default_factory=dict)
    record_count: Optional[int] = None


class MetaDiagnosticsVisualNode(BaseModel):
    """Graph node for the visual proof topology scene."""
    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    kind: str
    group: str
    status: str = "neutral"
    magnitude: Optional[Any] = None
    confidence: float = 1.0
    source_refs: List[str] = Field(default_factory=list)
    action_refs: List[str] = Field(default_factory=list)
    layout: Dict[str, Any] = Field(default_factory=dict)


class MetaDiagnosticsVisualEdge(BaseModel):
    """Graph edge for the visual proof topology scene."""
    model_config = ConfigDict(extra="allow")

    id: str
    source: str
    target: str
    relation: str
    weight: float = 1.0
    status: str = "neutral"
    evidence_refs: List[str] = Field(default_factory=list)
    drilldown_refs: List[str] = Field(default_factory=list)


class MetaDiagnosticsVisualLane(BaseModel):
    """Semantic lane used by the visual proof topology scene."""
    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    semantic_role: str
    ordered_node_ids: List[str] = Field(default_factory=list)


class MetaDiagnosticsVisualSeries(BaseModel):
    """Timeline or series primitive for the visual scene."""
    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    values: List[Dict[str, Any]] = Field(default_factory=list)
    x_field: Optional[str] = None
    y_field: Optional[str] = None


class MetaDiagnosticsVisualMatrix(BaseModel):
    """Heatmap primitive for the visual scene."""
    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    rows: List[str] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    cells: List[Dict[str, Any]] = Field(default_factory=list)
    legend: Dict[str, Any] = Field(default_factory=dict)


class MetaDiagnosticsVisualDistribution(BaseModel):
    """Distribution primitive for bucketed pressure views."""
    model_config = ConfigDict(extra="allow")

    id: str
    label: str
    buckets: List[Dict[str, Any]] = Field(default_factory=list)
    highlight_bucket: Optional[str] = None
    total: Optional[float] = None
    source_ref: Optional[str] = None


class MetaDiagnosticsVisualAnnotation(BaseModel):
    """Annotation tying visual claims back to evidence."""
    model_config = ConfigDict(extra="allow")

    id: str
    claim: str
    evidence_ref: Optional[str] = None
    severity: str = "neutral"
    target_id: Optional[str] = None


class MetaDiagnosticsVisualGrammar(BaseModel):
    """
    [ROLE]
    - Teleology: Declare the semantic encoding rules a frontend renderer must
      honor when drawing the visual scene. Without this, primitive presence
      passes DOM checks but the result is diagram theatre — backend data
      structures wearing SVG costumes. Source: std_station_aesthetic
      P14_visual_instrument_over_diagram_theatre.
    - Mechanism: mark_types name which shapes carry which semantic role
      (ports for sources, hubs for claims, pressure regions for evidence);
      channel_encodings tell the renderer which visual channel (size,
      opacity, stroke_width, color, position) carries which datum
      (magnitude, freshness, edge weight, status, causal stage);
      salience_order orders node groups by primacy; story_beats give the
      reader an ordered narrative path; label_priority controls which
      labels are always visible vs hover-only vs elided; inspector_payloads
      defines what details surface per node kind; failure_state_contract
      defines what to render when the scene is degraded.
    """
    model_config = ConfigDict(extra="allow")

    mark_types: List[Dict[str, Any]] = Field(default_factory=list)
    channel_encodings: List[Dict[str, Any]] = Field(default_factory=list)
    salience_order: List[Dict[str, Any]] = Field(default_factory=list)
    story_beats: List[Dict[str, Any]] = Field(default_factory=list)
    label_priority: Dict[str, Any] = Field(default_factory=dict)
    inspector_payloads: Dict[str, Any] = Field(default_factory=dict)
    failure_state_contract: Dict[str, Any] = Field(default_factory=dict)


class MetaDiagnosticsVisualInstrument(BaseModel):
    """
    [ROLE]
    - Teleology: Compact thesis carried into render: what the human should
      perceive at a glance, what canvas region dominates, which secondary
      regions are demoted, and what is forbidden. Distinct from
      scene_manifest which lists primitives; instrument names the proof
      object the operator is meant to read.
    - Mechanism: thesis is one-sentence operator vision; dominant_question
      is the operator question the canvas answers; dominant_canvas_role
      identifies the scene root that owns the upper viewport; regions
      declare role/posture for each canvas region; forbidden_patterns
      lists diagram-theatre patterns the renderer must refuse.
    """
    model_config = ConfigDict(extra="allow")

    thesis: str = ""
    dominant_question: str = ""
    dominant_canvas_role: str = ""
    regions: List[Dict[str, Any]] = Field(default_factory=list)
    forbidden_patterns: List[str] = Field(default_factory=list)


class MetaDiagnosticsVisualScene(BaseModel):
    """
    [ROLE]
    - Teleology: Normalize the meta diagnostics packet into visual primitives
      AND the visual grammar that governs how those primitives must be
      rendered as a single dominant visual instrument. Primitives alone are
      diagram theatre.
    - Mechanism: visual_grammar declares marks/channels/salience/story
      beats; visual_instrument names the dominant proof object; primitives
      (nodes/edges/lanes/series/matrices/distributions) supply the data.
      Frontend renders to the grammar, not just to the primitives.
    """
    model_config = ConfigDict(extra="allow")

    schema_name: Literal["meta_diagnostics_visual_scene_v0"] = Field(
        default="meta_diagnostics_visual_scene_v0",
        alias="schema",
    )
    generated_at: str
    authority: Dict[str, Any] = Field(default_factory=dict)
    scene_manifest: Dict[str, Any] = Field(default_factory=dict)
    visual_grammar: MetaDiagnosticsVisualGrammar = Field(default_factory=MetaDiagnosticsVisualGrammar)
    visual_instrument: MetaDiagnosticsVisualInstrument = Field(default_factory=MetaDiagnosticsVisualInstrument)
    nodes: List[MetaDiagnosticsVisualNode] = Field(default_factory=list)
    edges: List[MetaDiagnosticsVisualEdge] = Field(default_factory=list)
    lanes: List[MetaDiagnosticsVisualLane] = Field(default_factory=list)
    series: List[MetaDiagnosticsVisualSeries] = Field(default_factory=list)
    matrices: List[MetaDiagnosticsVisualMatrix] = Field(default_factory=list)
    distributions: List[MetaDiagnosticsVisualDistribution] = Field(default_factory=list)
    annotations: List[MetaDiagnosticsVisualAnnotation] = Field(default_factory=list)
    interaction_contract: Dict[str, Any] = Field(default_factory=dict)


class MetaDiagnosticsAtlasOverlay(BaseModel):
    """
    [ROLE]
    - Teleology: Map the Meta Diagnostics read model onto the existing System
      Atlas substrate as observability overlay semantics. The atlas renderer
      reads this block to surface diagnostic pressure on existing atlas
      entities/edges/clusters instead of building a standalone hero
      infographic. Lessons: std_station_aesthetic
      P15_observability_overlays_on_atlas_not_hero_diagrams.
    - Mechanism: target_surface names the atlas mount; layers[] enumerate
      toggleable diagnostic layers (trust / route_pressure / work_evidence /
      annex_pressure / proof / freshness); kind_overlays maps atlas kinds to
      per-layer pressure metrics; gaps lists expected substrate that does not
      yet exist; inspector_payloads tells the renderer what shows on
      selection. NOT a new source of truth.
    """
    model_config = ConfigDict(extra="allow")

    target_surface: str = "system_atlas"
    target_route_preset: str = "/station/meta-diagnostics"
    default_layer: str = "trust"
    layers: List[Dict[str, Any]] = Field(default_factory=list)
    kind_overlays: Dict[str, Any] = Field(default_factory=dict)
    cluster_overlays: Dict[str, Any] = Field(default_factory=dict)
    entity_decorations: List[Dict[str, Any]] = Field(default_factory=list)
    gaps: List[Dict[str, Any]] = Field(default_factory=list)
    inspector_payloads: Dict[str, Any] = Field(default_factory=dict)
    lod_policy: Dict[str, Any] = Field(default_factory=dict)


class MetaDiagnosticsConsoleProjectionResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Typed contract for `GET /api/world-model/meta-diagnostics/console`.
    - Mechanism: Stabilizes the visual-scene topology, trust strip, source
      health, atlas overlay semantics, and drilldown-bearing read-model
      sections while preserving each panel's dynamic nested evidence shape as
      `Dict[str, Any]`.
    - Authority: The endpoint remains read-only glue over existing generated
      artifacts; this schema does not make the console a mutation authority.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    schema_name: Literal["meta_diagnostics_console_projection_v1"] = Field(
        default="meta_diagnostics_console_projection_v1",
        alias="schema",
    )
    generated_at: str
    available: bool
    authority: Dict[str, Any] = Field(default_factory=dict)
    summary: MetaDiagnosticsConsoleSummary = Field(default_factory=MetaDiagnosticsConsoleSummary)
    frontend_contract: MetaDiagnosticsFrontendContract
    panel_manifest: List[MetaDiagnosticsPanelManifestEntry] = Field(default_factory=list)
    visual_scene: MetaDiagnosticsVisualScene
    atlas_overlay: MetaDiagnosticsAtlasOverlay = Field(default_factory=MetaDiagnosticsAtlasOverlay)
    source_health: Dict[str, MetaDiagnosticsSourceHealthEntry] = Field(default_factory=dict)
    trust_strip: Dict[str, Any] = Field(default_factory=dict)
    agent_behavior: Dict[str, Any] = Field(default_factory=dict)
    work_evidence: Dict[str, Any] = Field(default_factory=dict)
    doctrine_health: Dict[str, Any] = Field(default_factory=dict)
    external_intake: Dict[str, Any] = Field(default_factory=dict)
    prompt_learning: Dict[str, Any] = Field(default_factory=dict)
    proof_constellation: Dict[str, Any] = Field(default_factory=dict)
    omission_receipt: Dict[str, Any] = Field(default_factory=dict)


class MetaMissionRunSummary(BaseModel):
    """
    [ROLE]
    - Teleology: Compact view of one meta-mission run for list surfaces.
    - Mechanism: Snapshot of the canonical run.json plus run_dir path.
    """
    run_id: str
    mission_id: str
    status: str
    trigger: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    parent_run_id: Optional[str] = None
    chain_ref: Optional[Dict[str, Any]] = None
    provider: Optional[str] = None
    phase_ref: Optional[str] = None
    template_version: Optional[str] = None
    inputs_digest: Optional[str] = None
    error: Optional[str] = None
    run_dir: Optional[str] = None
    run_json_path: Optional[str] = None
    artifact_refs: List[str] = Field(default_factory=list)


class MetaMissionCareerMetrics(BaseModel):
    """Per-career totals used on the /meta-missions list and Station tile."""
    total_runs: int = 0
    running_total: int = 0
    terminal_total: int = 0
    succeeded_total: int = 0
    failed_total: int = 0
    success_rate: Optional[float] = None
    by_status: Dict[str, int] = Field(default_factory=dict)
    last_run: Optional[MetaMissionRunSummary] = None


class MetaMissionSummaryRow(BaseModel):
    """One row on the /meta-missions list and the Station meta_missions slice."""
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    mission_id: str
    title: str
    kind: Optional[str] = None
    status: str = "active"
    runtime_surface: Optional[str] = None
    supports_resume: bool = False
    launcher_operation_ids: List[str] = Field(default_factory=list)
    launcher_operations: List[StationLauncherOperation] = Field(default_factory=list)
    workspace_root: str
    metrics: MetaMissionCareerMetrics = Field(default_factory=MetaMissionCareerMetrics)
    recent_runs: List[MetaMissionRunSummary] = Field(default_factory=list)


class MetaMissionUrgentRow(BaseModel):
    """Compact alert row for failed / graceful_stop missions on Station."""
    mission_id: str
    title: str
    status: str
    run_id: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    supports_resume: bool = False


class StationMetaMissionsSlice(BaseModel):
    """
    [ROLE]
    - Teleology: Per-Station compact summary of all active meta-mission careers
      so /station can render a 'missions at a glance' block without a second
      fetch against the /api/meta-missions list endpoint.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    generated_at: Optional[str] = None
    totals: Dict[str, int] = Field(default_factory=dict)
    missions: List[MetaMissionSummaryRow] = Field(default_factory=list)
    urgent: List[MetaMissionUrgentRow] = Field(default_factory=list)


class MetaMissionRegistryEntry(BaseModel):
    """Mirror of one meta_mission_registry.json entry."""
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    mission_id: str
    status: str
    kind: Optional[str] = None
    pack_dir: Optional[str] = None
    template_version: Optional[str] = None
    title: str
    summary: Optional[str] = None
    skill_bundle_refs: List[str] = Field(default_factory=list)
    dispatch_policy_source: Optional[str] = None
    launcher_operation_ids: List[str] = Field(default_factory=list)
    launcher_operations: List[StationLauncherOperation] = Field(default_factory=list)
    workspace_root: Optional[str] = None
    runtime_root: Optional[str] = None
    input_unit_label: Optional[str] = None
    supports_resume: bool = False
    runtime_surface: Optional[str] = None
    chain_children: Optional[List[str]] = None
    planned_pack_formalization: Optional[str] = None


class MetaMissionsIndexResponse(BaseModel):
    """`GET /api/meta-missions` response shape."""
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    generated_at: str
    registry_version: Optional[str] = None
    authority_anchor_std: Optional[str] = None
    entries: List[MetaMissionRegistryEntry] = Field(default_factory=list)
    summaries: List[MetaMissionSummaryRow] = Field(default_factory=list)


class MetaMissionDetailResponse(BaseModel):
    """`GET /api/meta-missions/{mission_id}` response shape."""
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    generated_at: str
    entry: MetaMissionRegistryEntry
    summary: MetaMissionSummaryRow
    recent_runs: List[MetaMissionRunSummary] = Field(default_factory=list)


class MetaMissionRunsResponse(BaseModel):
    """`GET /api/meta-missions/{mission_id}/runs` response shape."""
    generated_at: str
    mission_id: str
    total_runs: int
    runs: List[MetaMissionRunSummary] = Field(default_factory=list)


class MetaMissionRunDetailResponse(BaseModel):
    """`GET /api/meta-missions/{mission_id}/runs/{run_id}` response shape.

    Carries the full run shape (including events/artifacts paths) plus inline
    trails so the UI can render a single run without a second fetch.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    generated_at: str
    mission_id: str
    run: MetaMissionRunSummary
    events: List[Dict[str, Any]] = Field(default_factory=list)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)


class ApprovalOperationRef(BaseModel):
    """Launcher operation reference embedded on projected approval rows."""

    operation_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ApprovalRecord(BaseModel):
    """Unified approval inbox row projected from one native source."""
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


    approval_id: str
    source_kind: str
    source_ref: str
    title: str
    detail: str
    status: Literal["pending", "claimed", "approved", "rejected"]
    action_kind: Literal["decide", "review_only"]
    severity: Optional[str] = None
    owner_driver: Optional[str] = None
    artifacts: List[str] = Field(default_factory=list)
    command: Optional[str] = None
    operation: Optional[ApprovalOperationRef] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_state_hash: str
    opened_at: Optional[str] = None
    updated_at: Optional[str] = None
    surface_route: Optional[str] = None
    surface_label: Optional[str] = None
    age_seconds: Optional[int] = None
    detail_excerpt: Optional[str] = None
    unblocks: List[str] = Field(default_factory=list)
    unblocks_count: int = 0
    evidence_refs: List[Dict[str, str]] = Field(default_factory=list)


class ApprovalSummary(BaseModel):
    """Compact aggregate used by Station home and world-model snapshot."""

    total_pending: int = 0
    source_kind_counts: Dict[str, int] = Field(default_factory=dict)
    action_kind_counts: Dict[str, int] = Field(default_factory=dict)
    status_counts: Dict[str, int] = Field(default_factory=dict)
    top_records: List[ApprovalRecord] = Field(default_factory=list)


class ApprovalListResponse(BaseModel):
    """`GET /api/approvals` response envelope."""

    model_config = ConfigDict(

        populate_by_name=True,

        json_schema_serialization_defaults_required=True,

    )

    schema_name: Literal["approval_list_v1"] = Field(
        default="approval_list_v1",
        alias="schema",
    )
    generated_at: str
    records: List[ApprovalRecord] = Field(default_factory=list)
    summary: ApprovalSummary = Field(default_factory=ApprovalSummary)


class ApprovalDecisionRequest(BaseModel):
    """POST body for one approval decision."""

    decision: Literal["approve", "reject"]
    actor_id: str
    reason: Optional[str] = None


class ApprovalDecisionResponse(BaseModel):
    """Successful decision envelope for `POST /api/approvals/{id}/decide`."""
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


    ok: bool = True
    decision_event: Dict[str, Any] = Field(default_factory=dict)
    records: List[ApprovalRecord] = Field(default_factory=list)
    summary: ApprovalSummary = Field(default_factory=ApprovalSummary)
    generated_at: Optional[str] = None


class StationLauncherSnapshot(BaseModel):
    """
    [ROLE]
    - Teleology: Unified home-screen payload for the operator launcher surface.
    - Mechanism: Aggregates compact status slices from the world model, lobby,
      bridge, observe runtime, and current run so `/station` can render from
      one read-friendly packet instead of stitching multiple APIs ad hoc.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_serialization_defaults_required=True,
    )

    schema_name: Literal["station_launcher_v1"] = Field(
        default="station_launcher_v1",
        alias="schema",
    )
    generated_at: str
    family: Dict[str, Any] = Field(default_factory=dict)
    active_phase: Dict[str, Any] = Field(default_factory=dict)
    current_driver: Dict[str, Any] = Field(default_factory=dict)
    next_handoff: Dict[str, Any] = Field(default_factory=dict)
    orchestration: Dict[str, Any] = Field(default_factory=dict)
    missions: Dict[str, Any] = Field(default_factory=dict)
    bridge: Dict[str, Any] = Field(default_factory=dict)
    observe_runtime: Dict[str, Any] = Field(default_factory=dict)
    raw_seed_pipeline: StationRawSeedPipelineSnapshot = Field(
        default_factory=StationRawSeedPipelineSnapshot
    )
    navigation_freshness: Dict[str, Any] = Field(default_factory=dict)
    system_facts: Dict[str, Any] = Field(default_factory=dict)
    host_agents: HostAgentExternalSnapshot = Field(default_factory=HostAgentExternalSnapshot)
    overnight_chain: StationOvernightChainSnapshot = Field(
        default_factory=StationOvernightChainSnapshot
    )
    overnight_queue: StationOvernightQueueSnapshot = Field(
        default_factory=StationOvernightQueueSnapshot
    )
    autonomy_runtime: StationOvernightQueueSnapshot = Field(
        default_factory=StationOvernightQueueSnapshot
    )
    meta_missions: StationMetaMissionsSlice = Field(
        default_factory=StationMetaMissionsSlice
    )
    approvals: ApprovalSummary = Field(default_factory=ApprovalSummary)
    alive_cockpit: Dict[str, Any] = Field(default_factory=dict)
    run: Dict[str, Any] = Field(default_factory=dict)
    alerts: List[StationLauncherAlert] = Field(default_factory=list)
    operations: List[StationLauncherOperation] = Field(default_factory=list)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


class FrontendSurfaceListResponse(BaseModel):
    """List of Station/frontend surfaces with semantic health and evidence."""

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["frontend_surface_list_v1"] = Field(
        default="frontend_surface_list_v1",
        alias="schema",
    )
    generated_at: str
    surfaces: List[Dict[str, Any]] = Field(default_factory=list)
    source_files: Dict[str, Any] = Field(default_factory=dict)


class FrontendSurfaceAgentPacketResponse(BaseModel):
    """Agent-oriented merged packet for one frontend surface."""

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["frontend_surface_agent_packet_v1"] = Field(
        default="frontend_surface_agent_packet_v1",
        alias="schema",
    )
    generated_at: str
    surface: Dict[str, Any] = Field(default_factory=dict)
    health: Dict[str, Any] = Field(default_factory=dict)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    readiness: Optional[Dict[str, Any]] = None
    runtime: Optional[Dict[str, Any]] = None
    valid_actions: List[Dict[str, Any]] = Field(default_factory=list)
    invalid_actions: List[Dict[str, Any]] = Field(default_factory=list)
    outbound_neighbours: List[Dict[str, Any]] = Field(default_factory=list)
    operator_cli_hints: Dict[str, Any] = Field(default_factory=dict)


class FrontendHealthReportResponse(BaseModel):
    """Frontend semantic health report over all known surfaces."""

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["frontend_health_report_v1"] = Field(
        default="frontend_health_report_v1",
        alias="schema",
    )
    generated_at: str
    semantic_check: Dict[str, Any] = Field(default_factory=dict)
    counts: Dict[str, Any] = Field(default_factory=dict)
    readiness_rows: List[Dict[str, Any]] = Field(default_factory=list)
    placeholder_primary_nav: List[Dict[str, Any]] = Field(default_factory=list)
    worst_render_timings: List[Dict[str, Any]] = Field(default_factory=list)
    duplicate_runtime_authority_warnings: List[Dict[str, Any]] = Field(default_factory=list)
    dead_component_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    source_files: Dict[str, Any] = Field(default_factory=dict)


class RuntimeContinuityResponse(BaseModel):
    """Backend-owned runtime continuity counters for frontend diagnostics."""

    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["runtime_continuity_v1"] = Field(
        default="runtime_continuity_v1",
        alias="schema",
    )
    generated_at: str
    backend_boot_id: str
    backend_booted_at: str
    active_socket_count: int = 0
    active_connection_ids: List[str] = Field(default_factory=list)
    total_connects: int = 0
    total_disconnects: int = 0
    last_disconnect: Optional[Dict[str, Any]] = None
    last_broadcast: Optional[Dict[str, Any]] = None
    frontend_boot_id: Optional[str] = None
    hmr_reload_count: Optional[int] = None
    store_reset_count: Optional[int] = None


class LaunchOperationPreview(BaseModel):
    """
    [ROLE]
    - Teleology: Read-only preview packet for a catalogued launcher operation
      after backend validation and parameter resolution.
    - Mechanism: Mirrors the authoritative `prepare_launch_operation(...)`
      output without executing the command.
    """
    operation_id: str
    command: str
    execution_mode: Literal["sync", "detached"] = "sync"
    resolved_parameters: Dict[str, str] = Field(default_factory=dict)


class LaunchOperationPreviewResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Typed response body for `POST /api/world-model/operations/preview`.
    - Mechanism: Matches the launcher failure envelope used by operation launch:
      `{ok, preview?, error?}`.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    ok: bool
    preview: Optional[LaunchOperationPreview] = None
    error: Optional[str] = None


class WorldModelFreshnessSchema(BaseModel):
    """
    [ROLE]
    - Teleology: Typed freshness payload reused by read-only world-model shard surfaces.
    - Wire contract: every field is always emitted by compute_freshness();
      Pydantic defaults are kept for safe Python-side `default_factory=` use,
      but the serialization schema marks them required so the generated TS
      narrows correctly.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    tone: Literal["fresh", "stale", "expired", "unknown"] = "unknown"
    age_seconds: Optional[int] = None
    label: str = "unknown"
    iso: Optional[str] = None


class PaperModuleSourceTargetResponse(BaseModel):
    """
    [ROLE]
    - Teleology: One concrete source target behind a paper-module browse card.
    - Mechanism: Derived from the paper module's resolved Code loci, with the
      markdown module retained as a secondary source target.
    """
    target_id: str
    role: str
    source_field: str
    path: str
    label: str
    target_kind: str
    language: Optional[str] = None
    exists: bool = False
    inspector_supported: bool = False
    evidence_command: Optional[str] = None


class PaperModuleCardResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Compact preview card for one paper module on API/UI browse surfaces.
    - Mechanism: Mirrors the read-only world-model projection from the shared
      paper-module runtime rather than exposing raw builder artifacts directly.
    """
    slug: Optional[str] = None
    title: Optional[str] = None
    file: Optional[str] = None
    projection_class: Optional[str] = None
    status: Optional[str] = None
    recommended_action: Optional[str] = None
    action_cause: Optional[str] = None
    fan_in_inbound: Optional[int] = None
    fan_out_outbound: Optional[int] = None
    boundary_pressure: Optional[str] = None
    boundary_evidence: Dict[str, Any] = Field(default_factory=dict)
    tldr: Optional[str] = None
    deliverables_preview: List[str] = Field(default_factory=list)
    code_loci_preview: List[str] = Field(default_factory=list)
    source_targets: List[PaperModuleSourceTargetResponse] = Field(default_factory=list)
    primary_source_target: Optional[PaperModuleSourceTargetResponse] = None
    doctrine_feed: Dict[str, Any] = Field(default_factory=dict)


class PaperModulesSummaryResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Stabilize the top-level paper-module summary counts for public browse surfaces.
    """
    module_count: Optional[int] = None
    candidate_count: Optional[int] = None
    edge_count: Optional[int] = None
    root_count: Optional[int] = None
    leaf_count: Optional[int] = None
    projection_class_counts: Dict[str, int] = Field(default_factory=dict)
    status_counts: Dict[str, int] = Field(default_factory=dict)
    action_cause_counts: Dict[str, int] = Field(default_factory=dict)


class PaperModulesFreshnessResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Carry the explicit trust/freshness state for paper-module projections.
    - Guarantee: Stale or drifted generated surfaces remain visible as structured
      state instead of degrading into an implicit trust posture.
    """
    status: str = "unknown"
    generated_at: Optional[str] = None
    generated_at_freshness: WorldModelFreshnessSchema = Field(
        default_factory=WorldModelFreshnessSchema
    )
    authored_module_count: Optional[int] = None
    generated_module_count: Optional[int] = None
    missing_from_index: List[str] = Field(default_factory=list)
    missing_from_report: List[str] = Field(default_factory=list)
    drift_findings: List[Dict[str, Any]] = Field(default_factory=list)


class PaperModulesSnapshotResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Typed response for `/api/papers`, the public paper-module browse
      surface backed by the shared world-model projection.
    """
    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["paper_modules_snapshot_v1"] = Field(
        default="paper_modules_snapshot_v1",
        alias="schema",
    )
    generated_at: str
    available: bool
    summary: Optional[PaperModulesSummaryResponse] = None
    freshness: PaperModulesFreshnessResponse = Field(
        default_factory=PaperModulesFreshnessResponse
    )
    queue_counts: Dict[str, int] = Field(default_factory=dict)
    route_coverage: Dict[str, Any] = Field(default_factory=dict)
    cards: List[PaperModuleCardResponse] = Field(default_factory=list)


class ImaginationMigrationRecordResponse(BaseModel):
    """
    [ROLE]
    - Teleology: One row of provenance backref carried inside an imagination's
      `migrated_from[]` frontmatter and projected into the row payload.
    - Source authority: codex/standards/std_imagination.json::field_contracts.migrated_from.
    """
    model_config = ConfigDict(extra="allow")
    axiom_candidate_id: Optional[str] = None
    deliverable_id: Optional[str] = None
    deliverable_status_at_migration: Optional[str] = None
    migration_action: Optional[str] = None
    migration_date: Optional[str] = None
    notes: Optional[str] = None


class ImaginationRowResponse(BaseModel):
    """
    [ROLE]
    - Teleology: One imagination row at flag-band shape used by /api/imaginations.
    - Source authority: codex/doctrine/imaginations/_index.json (builder-generated)
      mediated by tools/meta/factory/build_imagination_index.py.
    """
    model_config = ConfigDict(extra="allow")
    imagination_id: str
    slug: str
    title: str
    status: str
    schema_version: str
    truth_posture: str
    authored_at: str
    authored_by: str
    file: str
    voice_anchor_summary: str
    primary_substrate_seam: str
    retirement_trigger_summary: str
    voice_anchor_count: int = 0
    substrate_count: int = 0
    scene_fixture_count: int = 0
    migrated_from_count: int = 0
    migrated_from_axiom_candidate_ids: List[str] = Field(default_factory=list)
    migrated_from_deliverable_ids: List[str] = Field(default_factory=list)
    migrated_from_action_counts: Dict[str, int] = Field(default_factory=dict)
    is_migrated: bool = False


class ImaginationDetailRowResponse(ImaginationRowResponse):
    """Card-band row with body excerpts and full migration record array."""
    model_config = ConfigDict(extra="allow")
    voice_anchor_checked_counts: Dict[str, int] = Field(default_factory=dict)
    substrate_resolution_status_counts: Dict[str, int] = Field(default_factory=dict)
    scene_fixture_posture_counts: Dict[str, int] = Field(default_factory=dict)
    migrated_from_records: List[ImaginationMigrationRecordResponse] = Field(default_factory=list)
    present_tense_scene_excerpt: Optional[str] = None
    deliverable_shape_excerpt: Optional[str] = None
    what_becomes_easy_excerpt: Optional[str] = None
    what_no_longer_happens_excerpt: Optional[str] = None
    drilldown_command: Optional[str] = None
    convenience_command: Optional[str] = None
    evidence_command: Optional[str] = None
    preservation_note: Optional[str] = None


class ImaginationsSummaryResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Stabilize the top-level imaginations summary counts for
      Station consumers.
    """
    model_config = ConfigDict(extra="allow")
    imagination_count: Optional[int] = None
    migrated_imagination_count: Optional[int] = None
    original_imagination_count: Optional[int] = None
    status_counts: Dict[str, int] = Field(default_factory=dict)
    authored_by_counts: Dict[str, int] = Field(default_factory=dict)
    error_count: Optional[int] = None
    warning_count: Optional[int] = None
    validation_status: Optional[str] = None
    field_set_status: Optional[str] = None


class ImaginationsValidationSummaryInner(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: Optional[str] = None
    error_count: Optional[int] = None
    warning_count: Optional[int] = None
    imagination_count: Optional[int] = None
    recommended_action: Optional[str] = None


class ImaginationsValidationResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Carry the explicit validation posture from
      codex/doctrine/imaginations/_validation_report.json into the snapshot.
    """
    model_config = ConfigDict(extra="allow")
    summary: Optional[ImaginationsValidationSummaryInner] = None
    finding_count: Optional[int] = None
    generated_at: Optional[str] = None


class ImaginationsSnapshotResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Typed response for `/api/imaginations` and
      `/api/world-model/imaginations`, projecting the generated
      `_index.json` + `_validation_report.json` for Station consumers.
    - Source authority: codex/standards/std_imagination.json (v1, field-set frozen).
    - Mechanism: Mirrors the dict shape returned by
      `system.server.world_model.load_imaginations_snapshot`.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    schema_name: Literal["imaginations_snapshot_v1"] = Field(
        default="imaginations_snapshot_v1",
        alias="schema",
    )
    generated_at: str
    available: bool
    authority_dir: Optional[str] = None
    standard_path: Optional[str] = None
    skill_path: Optional[str] = None
    source_axiom_candidates_path: Optional[str] = None
    summary: Optional[ImaginationsSummaryResponse] = None
    validation: Optional[ImaginationsValidationResponse] = None
    migration_coverage: Dict[str, Any] = Field(default_factory=dict)
    rows: List[ImaginationRowResponse] = Field(default_factory=list)
    by_status: Dict[str, List[str]] = Field(default_factory=dict)
    by_authored_by: Dict[str, List[str]] = Field(default_factory=dict)
    by_migrated_from_axiom_candidate: Dict[str, List[str]] = Field(default_factory=dict)
    by_migrated_from_deliverable_id: Dict[str, List[str]] = Field(default_factory=dict)


class ImaginationDetailGoverningStandard(BaseModel):
    model_config = ConfigDict(extra="allow")
    ref: Optional[str] = None
    schema_version: Optional[str] = None
    owned_bands: List[str] = Field(default_factory=list)


class ImaginationDetailResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Typed response for `/api/imaginations/{id_or_slug}` and
      `/api/world-model/imaginations/{id_or_slug}`. Resolves by id or slug;
      carries body excerpts and full migration lineage.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    schema_name: Literal["imagination_detail_v1"] = Field(
        default="imagination_detail_v1",
        alias="schema",
    )
    generated_at: str
    available: bool
    request: str
    missing_ids: List[str] = Field(default_factory=list)
    row: Optional[ImaginationDetailRowResponse] = None
    governing_standard: Optional[ImaginationDetailGoverningStandard] = None
    skill_ref: Optional[str] = None
    source_refs: List[str] = Field(default_factory=list)
    preservation_note: Optional[str] = None


class MarketDashboardReadModelResponse(BaseModel):
    """Typed response for the full backend market intelligence read model."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["market_dashboard_read_model_v0"] = "market_dashboard_read_model_v0"
    run_id: Optional[str] = None
    input_graph_schema_version: Optional[str] = None
    input_graph_fingerprint: Optional[str] = None
    projection_status: Dict[str, Any] = Field(default_factory=dict)
    authority_boundary: Dict[str, Any] = Field(default_factory=dict)
    overview: Dict[str, Any] = Field(default_factory=dict)
    situation_queue: Dict[str, Any] = Field(default_factory=dict)
    situation_detail_index: Dict[str, Any] = Field(default_factory=dict)
    graph_slice: Dict[str, Any] = Field(default_factory=dict)
    facets: Dict[str, Any] = Field(default_factory=dict)
    drilldown_index: Dict[str, Any] = Field(default_factory=dict)
    provenance_index: Dict[str, Any] = Field(default_factory=dict)
    validation_debt: Dict[str, Any] = Field(default_factory=dict)
    display_hints: Dict[str, Any] = Field(default_factory=dict)
    api_contract: Dict[str, Any] = Field(default_factory=dict)


class MarketDashboardOverviewResponse(BaseModel):
    """Compact trust strip for the market intelligence read model."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["market_dashboard_overview_v0"] = "market_dashboard_overview_v0"
    projection_status: Dict[str, Any] = Field(default_factory=dict)
    overview: Dict[str, Any] = Field(default_factory=dict)
    route_manifest_readiness: Dict[str, Any] = Field(default_factory=dict)


class MarketDisplayBundleResponse(BaseModel):
    """Run-pinned display bundle composing read_model + quant_mart + evidence_card.

    Backs the v0.6.1 atomicity fix: when a fresh FEEDS refresh has blanked
    the live `latest_*` aliases, the cockpit fetches this bundle for the
    last-good run id and overlays it onto the world-model snapshot so all
    substrate moves together.
    """

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["market_display_bundle_v0"] = "market_display_bundle_v0"
    run_id: Optional[str] = None
    latest_market_dashboard_read_model: Dict[str, Any] = Field(default_factory=dict)
    latest_quant_presentation_mart: Dict[str, Any] = Field(default_factory=dict)
    latest_evidence_card: Dict[str, Any] = Field(default_factory=dict)
    bundle_consistency: Dict[str, Any] = Field(default_factory=dict)
    bundle_readiness: Dict[str, Any] = Field(default_factory=dict)
    finance_numeric_assurance: Dict[str, Any] = Field(default_factory=dict)
    publication: Dict[str, Any] = Field(default_factory=dict)
    # v0.8: deterministic interpretation slice. Optional because the
    # slice is added only after the bundle is composed.
    human_market_cockpit: Optional[Dict[str, Any]] = None


class MarketBrowsePlaneResponse(BaseModel):
    """v0.10: paged page over one browse plane (equity / etf / macro /
    event / flow / news / data_quality).

    The cockpit fetches this for the active plane; the latest-ready
    bundle carries only a top-25 preview and plane_nav with row
    counts, not the full row universe.
    """

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["market_browse_plane_v0"] = "market_browse_plane_v0"
    run_id: Optional[str] = None
    plane_id: Optional[str] = None
    feed_id: Optional[str] = None
    # v0.10.1: row_count_raw is the row count from extract_feed_table
    # BEFORE filter_plane_rows; row_count_total is after filtering.
    # filtered_out_count = raw - total and filter_status names the rule
    # set. The cockpit uses this to display honest counts and reject a
    # sparse render when raw > 100 but filtered < 25.
    row_count_total: int = 0
    row_count_raw: int = 0
    filtered_out_count: int = 0
    filter_status: Dict[str, Any] = Field(default_factory=dict)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    columns: List[Dict[str, Any]] = Field(default_factory=list)
    sort: Dict[str, Any] = Field(default_factory=dict)
    cursor: Optional[int] = None
    next_cursor: Optional[int] = None
    limit: Optional[int] = None
    extraction_status: Dict[str, Any] = Field(default_factory=dict)


class MarketDisplayBundleLatestReadyResponse(BaseModel):
    """Latest-ready market display bundle pointer.

    v0.7: the backend publishes
    `state/reports/market_feeds/latest_ready_market_display_bundle.json`
    atomically after a FEEDS run finishes AND passes readiness. This
    response wraps that pointer so the cockpit can render an honest
    "no ready bundle yet" state when nothing is published.
    """

    model_config = ConfigDict(extra="allow")

    schema_version: Optional[str] = None
    run_id: Optional[str] = None
    latest_ready_status: Dict[str, Any] = Field(default_factory=dict)


class MarketDashboardSituationQueueResponse(BaseModel):
    """Filterable, cursor-like situation queue response."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["market_dashboard_situation_queue_v0"] = "market_dashboard_situation_queue_v0"
    projection_status: Dict[str, Any] = Field(default_factory=dict)
    situation_queue: Dict[str, Any] = Field(default_factory=dict)
    facets: Dict[str, Any] = Field(default_factory=dict)


class MarketDashboardSituationDetailResponse(BaseModel):
    """Detail response for one backend-ranked market situation."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["market_dashboard_situation_detail_v0"] = "market_dashboard_situation_detail_v0"
    available: bool = False
    situation_id: Optional[str] = None
    detail: Dict[str, Any] = Field(default_factory=dict)
    reason: Optional[str] = None


class MarketDashboardGraphSliceResponse(BaseModel):
    """Node/edge slice over situations, entities, and evidence refs."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["market_dashboard_graph_slice_v0"] = "market_dashboard_graph_slice_v0"
    situation_id: Optional[str] = None
    depth: int = 1
    include_source_refs: bool = False
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)


class MarketDashboardDrilldownResponse(BaseModel):
    """Safe source-ref drilldown metadata; never arbitrary file content."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["market_dashboard_drilldown_v0"] = "market_dashboard_drilldown_v0"
    available: bool = False
    source_ref_id: Optional[str] = None
    source_ref: Dict[str, Any] = Field(default_factory=dict)
    source_row: Dict[str, Any] = Field(default_factory=dict)
    arbitrary_file_read_allowed: bool = False
    reason: Optional[str] = None


class MarketDashboardProvenanceResponse(BaseModel):
    """Provenance slice for read-model lineage and generated entities."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["market_dashboard_provenance_v0"] = "market_dashboard_provenance_v0"
    provenance_index: Dict[str, Any] = Field(default_factory=dict)
    projection_status: Dict[str, Any] = Field(default_factory=dict)


class MarketDashboardValidationDebtResponse(BaseModel):
    """Validation debt slice that keeps salience separate from validated signals."""

    model_config = ConfigDict(extra="allow")

    schema_version: Literal["market_dashboard_validation_debt_v0"] = "market_dashboard_validation_debt_v0"
    validation_debt: Dict[str, Any] = Field(default_factory=dict)
    projection_status: Dict[str, Any] = Field(default_factory=dict)


class ShardFacetCount(BaseModel):
    """
    [ROLE]
    - Teleology: Carry one counted shard facet for compact summary lanes.
    """
    value: str
    count: int = 0


class ShardDoctrineFacet(BaseModel):
    """
    [ROLE]
    - Teleology: Summarize one doctrine target referenced by shard metadata.
    """
    id: str
    kind: str
    title: Optional[str] = None
    count: int = 0


class ShardSurfaceCard(BaseModel):
    """
    [ROLE]
    - Teleology: Describe one candidate shard surface discovered on disk.
    """
    role: str
    source: str
    scope: str
    priority: int = 0
    surface_kind: str
    path: str
    exists: bool = False
    total: int = 0
    pending_count: int = 0
    extracted_at: Optional[str] = None
    freshness: Optional[WorldModelFreshnessSchema] = None


class ShardGroupSummary(BaseModel):
    """
    [ROLE]
    - Teleology: One bounded shard-group summary row for the operator overview.
    """
    group_id: str
    count: int = 0
    pending_count: int = 0
    sample_shard_ids: List[str] = Field(default_factory=list)
    top_gestures: List[str] = Field(default_factory=list)
    top_files: List[str] = Field(default_factory=list)
    top_doctrine_ids: List[str] = Field(default_factory=list)


class ShardGraphNode(BaseModel):
    """
    [ROLE]
    - Teleology: One node in the ephemeral shard graph projection.
    """
    id: str
    kind: Literal["shard", "paragraph", "group", "doctrine_target", "file"]
    label: str
    summary: Optional[str] = None
    shard_id: Optional[str] = None
    source_path: Optional[str] = None
    status: Optional[str] = None


class ShardGraphEdge(BaseModel):
    """
    [ROLE]
    - Teleology: One edge in the ephemeral shard graph projection.
    """
    id: str
    source: str
    target: str
    kind: Literal[
        "same_parent",
        "same_bin",
        "same_source_artifact",
        "shared_group",
        "routes_to",
        "references_file",
    ]
    label: Optional[str] = None


class ShardGraphPayload(BaseModel):
    """
    [ROLE]
    - Teleology: Hold the derived graph payload returned by shard query/detail routes.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    nodes: List[ShardGraphNode] = Field(default_factory=list)
    edges: List[ShardGraphEdge] = Field(default_factory=list)


class ShardQueryAxisMatch(BaseModel):
    """
    [ROLE]
    - Teleology: Preserve one explainability axis from ranked shard retrieval.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    axis: str
    score: int = 0
    detail: Optional[str] = None
    matched_terms: List[str] = Field(default_factory=list)


class ShardQueryResult(BaseModel):
    """
    [ROLE]
    - Teleology: One ranked shard hit or structurally filtered result row.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    shard_id: str
    shard: Dict[str, Any] = Field(default_factory=dict)
    score: int = 0
    matched_terms: List[str] = Field(default_factory=list)
    matched_axes: List[ShardQueryAxisMatch] = Field(default_factory=list)


class ShardRelatedResult(BaseModel):
    """
    [ROLE]
    - Teleology: One expanded related shard from neighborhood traversal.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    shard_id: str
    shard: Dict[str, Any] = Field(default_factory=dict)
    source_shard_ids: List[str] = Field(default_factory=list)
    related_by: List[Dict[str, Any]] = Field(default_factory=list)
    score: int = 0


class ShardSiblingGroup(BaseModel):
    """
    [ROLE]
    - Teleology: Carry one bounded shard sibling bucket keyed by group id.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    group_id: str
    siblings: List[Dict[str, Any]] = Field(default_factory=list)


class ShardLensQueryFilters(BaseModel):
    """
    [ROLE]
    - Teleology: Echo the active shard query filter state back to the UI.
    """
    query: str = ""
    group: Optional[str] = None
    paragraph_id: Optional[str] = None
    status: Optional[str] = None
    limit: int = 20
    related_limit: int = 40


class ShardLensOverviewResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Typed overview payload for the shard lens bootstrap surface.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_serialization_defaults_required=True,
    )

    schema_name: Literal["shard_lens_overview_v1"] = Field(
        default="shard_lens_overview_v1",
        alias="schema",
        serialization_alias="schema",
    )
    generated_at: str
    source: Literal["active", "family", "raw_seed"]
    source_path: Optional[str] = None
    surface_kind: Optional[str] = None
    freshness: WorldModelFreshnessSchema = Field(default_factory=WorldModelFreshnessSchema)
    total_shards: int = 0
    total_groups: int = 0
    pending_count: int = 0
    status_counts: Dict[str, int] = Field(default_factory=dict)
    routing_state_counts: Dict[str, int] = Field(default_factory=dict)
    coverage_state_counts: Dict[str, int] = Field(default_factory=dict)
    surfaces: List[ShardSurfaceCard] = Field(default_factory=list)
    group_summaries: List[ShardGroupSummary] = Field(default_factory=list)
    top_gestures: List[ShardFacetCount] = Field(default_factory=list)
    top_files: List[ShardFacetCount] = Field(default_factory=list)
    top_doctrine_targets: List[ShardDoctrineFacet] = Field(default_factory=list)


class ShardLensQueryResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Typed query payload for ranked or structural shard browsing.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_serialization_defaults_required=True,
    )

    schema_name: Literal["shard_lens_query_v1"] = Field(
        default="shard_lens_query_v1",
        alias="schema",
        serialization_alias="schema",
    )
    generated_at: str
    source: Literal["active", "family", "raw_seed"]
    source_path: Optional[str] = None
    surface_kind: Optional[str] = None
    freshness: WorldModelFreshnessSchema = Field(default_factory=WorldModelFreshnessSchema)
    filters: ShardLensQueryFilters = Field(default_factory=ShardLensQueryFilters)
    matched: int = 0
    total_in_index: int = 0
    total_in_pool: int = 0
    results: List[ShardQueryResult] = Field(default_factory=list)
    related: List[ShardRelatedResult] = Field(default_factory=list)
    graph: ShardGraphPayload = Field(default_factory=ShardGraphPayload)


class ShardLensDetailResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Typed detail payload for one selected shard.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_serialization_defaults_required=True,
    )

    schema_name: Literal["shard_lens_detail_v1"] = Field(
        default="shard_lens_detail_v1",
        alias="schema",
        serialization_alias="schema",
    )
    generated_at: str
    source: Literal["active", "family", "raw_seed"]
    source_path: Optional[str] = None
    surface_kind: Optional[str] = None
    freshness: WorldModelFreshnessSchema = Field(default_factory=WorldModelFreshnessSchema)
    shard_id: str
    authority: Dict[str, str] = Field(default_factory=dict)
    target: Dict[str, Any] = Field(default_factory=dict)
    neighborhood: Dict[str, Any] = Field(default_factory=dict)
    paragraph_siblings: List[Dict[str, Any]] = Field(default_factory=list)
    group_siblings: List[ShardSiblingGroup] = Field(default_factory=list)
    raw_seed_anchor: Optional[Dict[str, Any]] = None
    doctrine_refs: List[ShardDoctrineFacet] = Field(default_factory=list)
    file_refs: List[ShardFacetCount] = Field(default_factory=list)
    graph: ShardGraphPayload = Field(default_factory=ShardGraphPayload)


class WorkLedgerOverviewResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Typed overview payload for the work-ledger Station lens.
    - Wire contract: every field is always emitted by
      world_model.load_work_ledger_overview(); Pydantic defaults stay so
      Python-side construction is ergonomic, and the serialization schema
      marks them required so the generated TS narrows correctly.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_serialization_defaults_required=True,
    )

    schema_name: Literal["work_ledger_overview_v1"] = Field(
        default="work_ledger_overview_v1",
        alias="schema",
        serialization_alias="schema",
    )
    generated_at: str
    phase_id: str
    family_id: str
    raw_path: str
    index_path: str
    freshness: WorldModelFreshnessSchema = Field(default_factory=WorldModelFreshnessSchema)
    counts: Dict[str, Any] = Field(default_factory=dict)
    open_by_actor: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    open_by_family: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    recently_closed: List[Dict[str, Any]] = Field(default_factory=list)
    supersession_chains: List[Dict[str, Any]] = Field(default_factory=list)
    cross_agent_handoffs: List[Dict[str, Any]] = Field(default_factory=list)
    stale_open: List[Dict[str, Any]] = Field(default_factory=list)
    stale_sessions: List[Dict[str, Any]] = Field(default_factory=list)
    handoff_candidates: Dict[str, Any] = Field(default_factory=dict)
    coordination: Dict[str, Any] = Field(default_factory=dict)
    runtime_status: Dict[str, Any] = Field(default_factory=dict)
    top_stale: List["WorkLedgerProjectedRow"] = Field(default_factory=list)
    top_in_progress: List["WorkLedgerProjectedRow"] = Field(default_factory=list)
    top_recent_open: List["WorkLedgerProjectedRow"] = Field(default_factory=list)
    serving: Dict[str, Any] = Field(default_factory=dict)


class WorkLedgerProjectedRow(BaseModel):
    """Typed cockpit row projected from the work-ledger event/index shape."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    td_id: Optional[str] = None
    title: str = ""
    body_excerpt: Optional[str] = None
    status: Optional[str] = None
    actor: Optional[str] = None
    phase_id: Optional[str] = None
    family_id: Optional[str] = None
    opened_at: Optional[str] = None
    last_event_at: Optional[str] = None
    last_event_kind: Optional[str] = None
    age_seconds: Optional[int] = None
    blocker_summary: Optional[str] = None
    surface_route: str = "/station/ledger"


class SystemLensStageError(BaseModel):
    """Actionable failure detail for factory or phase-local pipeline state."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    stage: Optional[str] = None
    summary: Optional[str] = None
    detail: Optional[str] = None
    source_path: Optional[str] = None
    artifact_refs: List[Dict[str, str]] = Field(default_factory=list)
    when: Optional[str] = None
    last_successful_stage: Optional[str] = None


class SystemLensWorkRow(BaseModel):
    """System-lens work row with enough detail to render a real line item."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    td_id: Optional[str] = None
    title: str = ""
    body_excerpt: Optional[str] = None
    status: Optional[str] = None
    actor: Optional[str] = None
    phase_id: Optional[str] = None
    family_id: Optional[str] = None
    opened_at: Optional[str] = None
    last_event_at: Optional[str] = None
    last_event_kind: Optional[str] = None
    age_seconds: Optional[int] = None
    blocker_summary: Optional[str] = None
    surface_route: str = "/station/ledger"


class SystemLensDriftPreview(BaseModel):
    """One concrete drift finding excerpt under an aggregate source."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    severity: str = "info"
    code: Optional[str] = None
    detail: Optional[str] = None
    artifact_path: Optional[str] = None


class SystemLensRecentTransition(BaseModel):
    """Unified recent mutation row for the System cockpit."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    kind: str
    subject_id: Optional[str] = None
    subject_label: Optional[str] = None
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    when: Optional[str] = None
    actor: Optional[str] = None
    surface_route: Optional[str] = None


class SystemLensPhasePipelineState(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    stage: Optional[str] = None
    controller_phase: Optional[str] = None
    cycle: Optional[int] = None
    blocked: bool = False
    gate_reason: Optional[str] = None
    updated_at: Optional[str] = None
    stage_error: Optional[SystemLensStageError] = None


class SystemLensPhaseNarrative(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    headline: Optional[str] = None
    recent_cycle_summaries: List[Dict[str, Any]] = Field(default_factory=list)
    last_routing_decision: Optional[Dict[str, Any]] = None


class SystemLensPhaseSlice(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: Optional[str] = None
    title: Optional[str] = None
    route: str = "/station/phase"
    latest_cycle: Optional[str] = None
    cycle_count: Optional[int] = None
    directive_active: bool = False
    directive_summary: Optional[str] = None
    pipeline_state: SystemLensPhasePipelineState = Field(default_factory=SystemLensPhasePipelineState)
    narrative: SystemLensPhaseNarrative = Field(default_factory=SystemLensPhaseNarrative)
    freshness: WorldModelFreshnessSchema = Field(default_factory=WorldModelFreshnessSchema)


class SystemLensFactorySlice(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    stage: Optional[str] = None
    blocked: bool = False
    gate_reason: Optional[str] = None
    last_run: Optional[str] = None
    last_materialize: Optional[str] = None
    last_stage_apply: Optional[str] = None
    stage_error: Optional[SystemLensStageError] = None
    source_path: str = "tools/meta/factory/factory_state.json"


class SystemLensDriverRuntime(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    current_operation: Optional[Dict[str, Any]] = None
    recent_failures: List[Dict[str, Any]] = Field(default_factory=list)
    awaiting_barriers: List[Dict[str, Any]] = Field(default_factory=list)
    pending_queue_count: int = 0


class SystemLensDriverSlice(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    driver_id: Optional[str] = None
    label: Optional[str] = None
    available: bool = False
    active: bool = False
    stage: Optional[str] = None
    blocked: bool = False
    gate_reason: Optional[str] = None
    phase_ref: Optional[str] = None
    phase_title: Optional[str] = None
    phase_dir: Optional[str] = None
    next_action: Dict[str, Optional[str]] = Field(default_factory=dict)
    last_updated: Optional[str] = None
    state_path: Optional[str] = None
    review_artifacts: List[str] = Field(default_factory=list)
    runtime: SystemLensDriverRuntime = Field(default_factory=SystemLensDriverRuntime)


class SystemLensDecisionSlice(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    immediate_mode: Optional[str] = None
    summary: Optional[str] = None
    command: Optional[str] = None
    launch_recommended_now: bool = False
    reasoning: Optional[str] = None
    considered: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_refs: List[Dict[str, str]] = Field(default_factory=list)
    confidence: Optional[float] = None
    last_changed_at: Optional[str] = None


class SystemLensGateSlice(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    active: bool = False
    gate_reason: Optional[str] = None
    owner_driver: Optional[str] = None
    review_ready: bool = False
    command: Optional[str] = None


class SystemLensOrchestrationSlice(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    active_driver: Optional[str] = None
    decision: SystemLensDecisionSlice = Field(default_factory=SystemLensDecisionSlice)
    gate: SystemLensGateSlice = Field(default_factory=SystemLensGateSlice)
    drivers: List[SystemLensDriverSlice] = Field(default_factory=list)
    active_driver_record: Optional[SystemLensDriverSlice] = None
    reactions: Dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[str] = None
    freshness: WorldModelFreshnessSchema = Field(default_factory=WorldModelFreshnessSchema)


class SystemLensWorkSlice(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    counts: Dict[str, Any] = Field(default_factory=dict)
    current_next: Optional[Dict[str, Any]] = None
    top_stale: List[SystemLensWorkRow] = Field(default_factory=list)
    top_in_progress: List[SystemLensWorkRow] = Field(default_factory=list)
    top_recent_open: List[SystemLensWorkRow] = Field(default_factory=list)
    generated_at: Optional[str] = None
    freshness: WorldModelFreshnessSchema = Field(default_factory=WorldModelFreshnessSchema)


class SystemLensApprovalSlice(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    pending: int = 0
    source_kind_counts: Dict[str, int] = Field(default_factory=dict)
    action_kind_counts: Dict[str, int] = Field(default_factory=dict)
    status_counts: Dict[str, int] = Field(default_factory=dict)
    rows: List[ApprovalRecord] = Field(default_factory=list)
    generated_at: Optional[str] = None


class SystemLensDriftSource(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    plane: str
    label: str
    count: int = 0
    severity_counts: Dict[str, int] = Field(default_factory=dict)
    preview: List[SystemLensDriftPreview] = Field(default_factory=list)
    available: bool = False
    paper_module: Optional[str] = None
    surface_route: Optional[str] = None
    last_seen_at: Optional[str] = None


class SystemLensDriftSlice(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    total: int = 0
    severity_counts: Dict[str, int] = Field(default_factory=dict)
    sources: List[SystemLensDriftSource] = Field(default_factory=list)
    generated_at: Optional[str] = None


class SystemLensProjectionResponse(BaseModel):
    """Backend-composed cockpit payload for the System intelligence lens."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_serialization_defaults_required=True,
    )

    schema_name: Literal["system_lens_projection_v1"] = Field(
        default="system_lens_projection_v1",
        alias="schema",
        serialization_alias="schema",
    )
    generated_at: str
    source_generated_at: Dict[str, Optional[str]] = Field(default_factory=dict)
    freshness: WorldModelFreshnessSchema = Field(default_factory=WorldModelFreshnessSchema)
    phase: SystemLensPhaseSlice = Field(default_factory=SystemLensPhaseSlice)
    factory: SystemLensFactorySlice = Field(default_factory=SystemLensFactorySlice)
    orchestration: SystemLensOrchestrationSlice = Field(default_factory=SystemLensOrchestrationSlice)
    work: SystemLensWorkSlice = Field(default_factory=SystemLensWorkSlice)
    approvals: SystemLensApprovalSlice = Field(default_factory=SystemLensApprovalSlice)
    drift: SystemLensDriftSlice = Field(default_factory=SystemLensDriftSlice)
    recent_transitions: List[SystemLensRecentTransition] = Field(default_factory=list)


class OperationsLensSourceHealth(BaseModel):
    source: str
    status: str
    generated_at: Optional[str] = None
    age_seconds: Optional[int] = None
    label: Optional[str] = None


class OperationsLensSourceError(BaseModel):
    source: str
    status: str = "failed"
    message: str
    path: Optional[str] = None
    exception_type: Optional[str] = None


class OperationsLensSourceTiming(BaseModel):
    source: str
    duration_ms: float
    status: str = "ok"


class OperationsLensCacheDiagnostics(BaseModel):
    status: str = "miss"
    generated_at: Optional[str] = None
    age_seconds: Optional[int] = None
    path: Optional[str] = None


class OperationsLensDiagnostics(BaseModel):
    mode: str = "primary"
    fallback_from: Optional[str] = None
    source_errors: List[OperationsLensSourceError] = Field(default_factory=list)
    source_timings: List[OperationsLensSourceTiming] = Field(default_factory=list)
    cache: Optional[OperationsLensCacheDiagnostics] = None
    notes: List[str] = Field(default_factory=list)


class OperationsLensFreshness(BaseModel):
    status: str = "unknown"
    age_seconds: Optional[int] = None
    stale_sources: List[OperationsLensSourceHealth] = Field(default_factory=list)
    source_count: int = 0


class OperationsLensIdentity(BaseModel):
    family_id: Optional[str] = None
    phase_id: Optional[str] = None
    phase_number: Optional[str] = None
    phase_title: Optional[str] = None
    active_runtime_line: Optional[str] = None
    active_driver: Optional[str] = None
    next_handoff: Optional[str] = None


class OperationsLensSummary(BaseModel):
    headline: str = ""
    status: str = "unknown"
    operator_required: bool = False
    primary_blocker_id: Optional[str] = None
    primary_blocker_label: Optional[str] = None
    changed_since_last_seen: bool = False


class OperationsLensStageNode(BaseModel):
    id: str
    label: str
    kind: str
    status: str
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    blocker_ids: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class OperationsLensGraphNode(BaseModel):
    id: str
    label: str
    kind: str
    status: str
    weight: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OperationsLensGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    kind: str
    status: str = "unknown"
    label: Optional[str] = None


class OperationsLensGraph(BaseModel):
    nodes: List[OperationsLensGraphNode] = Field(default_factory=list)
    edges: List[OperationsLensGraphEdge] = Field(default_factory=list)


class OperationsLensBridge(BaseModel):
    status: str = "unknown"
    nodes: List[OperationsLensGraphNode] = Field(default_factory=list)
    edges: List[OperationsLensGraphEdge] = Field(default_factory=list)
    provider_count: int = 0
    live_provider_count: int = 0
    cdp_reachable: Optional[bool] = None
    browser_running: Optional[bool] = None


class OperationsLensWorkThread(BaseModel):
    td_id: str
    title: str
    state: str
    owner: Optional[str] = None
    phase_id: Optional[str] = None
    claim_ref: Optional[str] = None
    age_seconds: Optional[int] = None
    last_event_at: Optional[str] = None
    last_event_label: Optional[str] = None
    blockers: List[str] = Field(default_factory=list)
    supersedes: List[str] = Field(default_factory=list)
    superseded_by: List[str] = Field(default_factory=list)
    linked_caps: List[str] = Field(default_factory=list)
    linked_attention_items: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class OperationsLensWorkSpine(BaseModel):
    status: str = "unknown"
    counts: Dict[str, int] = Field(default_factory=dict)
    threads: List[OperationsLensWorkThread] = Field(default_factory=list)
    graph: OperationsLensGraph = Field(default_factory=OperationsLensGraph)


class OperationsLensCapNode(BaseModel):
    cap_id: str
    title: str
    state: str
    lane: Optional[str] = None
    priority: Optional[int] = None
    age_seconds: Optional[int] = None
    dependency_ids: List[str] = Field(default_factory=list)
    downstream_unlock_ids: List[str] = Field(default_factory=list)
    linked_work_threads: List[str] = Field(default_factory=list)
    linked_phase_id: Optional[str] = None
    satisfaction_summary: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)


class OperationsLensCapSpine(BaseModel):
    status: str = "unknown"
    caps: List[OperationsLensCapNode] = Field(default_factory=list)
    graph: OperationsLensGraph = Field(default_factory=OperationsLensGraph)


class OperationsLensAttentionItem(BaseModel):
    id: str
    severity: str
    kind: str
    title: str
    symptom: str
    why_it_matters: str
    current_state: str
    required_human_decision: Optional[str] = None
    related_node_ids: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class OperationsLensTimelineEvent(BaseModel):
    id: str
    at: Optional[str] = None
    kind: str
    label: str
    node_ids: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class OperationsLensEvidenceRef(BaseModel):
    id: str
    kind: str
    label: str
    path: Optional[str] = None
    href: Optional[str] = None
    excerpt: Optional[str] = None
    freshness: Optional[str] = None


class OperationsLensDrilldownRef(BaseModel):
    label: Optional[str] = None
    href: Optional[str] = None
    legacy: Optional[bool] = None


class OperationsLensSnapshotResponse(BaseModel):
    """Read-only topology payload for SystemLens operations exposition."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_serialization_defaults_required=True,
    )

    schema_name: Literal["operations_lens_snapshot_v1"] = Field(
        default="operations_lens_snapshot_v1",
        alias="schema",
        serialization_alias="schema",
    )
    generated_at: str
    freshness: OperationsLensFreshness = Field(default_factory=OperationsLensFreshness)
    identity: OperationsLensIdentity = Field(default_factory=OperationsLensIdentity)
    summary: OperationsLensSummary = Field(default_factory=OperationsLensSummary)
    state_chain: Dict[str, List[OperationsLensStageNode]] = Field(default_factory=dict)
    bridge: OperationsLensBridge = Field(default_factory=OperationsLensBridge)
    work_spine: OperationsLensWorkSpine = Field(default_factory=OperationsLensWorkSpine)
    cap_spine: OperationsLensCapSpine = Field(default_factory=OperationsLensCapSpine)
    topology: OperationsLensGraph = Field(default_factory=OperationsLensGraph)
    operator_attention: List[OperationsLensAttentionItem] = Field(default_factory=list)
    recent_events: List[OperationsLensTimelineEvent] = Field(default_factory=list)
    evidence_index: List[OperationsLensEvidenceRef] = Field(default_factory=list)
    diagnostics: OperationsLensDiagnostics = Field(default_factory=OperationsLensDiagnostics)
    drilldowns: Dict[str, OperationsLensDrilldownRef] = Field(default_factory=dict)


class LeanSurfaceOmissionReceipt(BaseModel):
    status: str = "complete"
    issues: List[str] = Field(default_factory=list)
    reason: str = ""


class LeanDeclarationCatalogItem(BaseModel):
    project_id: str
    file: str
    module_id: str
    kind: str
    name: str
    line_start: int
    line_end: int
    signature_excerpt: str
    proof_layer: Optional[Dict[str, Any]] = None
    execution_profile: Optional[Dict[str, Any]] = None


class LeanGraphNode(BaseModel):
    node_id: str
    node_kind: str
    label: Optional[str] = None
    declaration_kind: Optional[str] = None
    project_id: Optional[str] = None
    file: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    signature_excerpt: Optional[str] = None
    cluster_id: Optional[str] = None
    proof_layer_id: Optional[str] = None
    proof_significance: Optional[str] = None
    execution_duration_ms: Optional[float] = None
    execution_dominant_phase: Optional[str] = None
    execution_profile_freshness: Optional[str] = None


class LeanGraphEdge(BaseModel):
    edge_id: str
    from_node_id: str
    to_node_id: str
    edge_kind: str
    confidence: Optional[str] = None


class LeanGraphCluster(BaseModel):
    cluster_id: str
    node_count: int


class LeanViewRegistryEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    view_id: str
    label: str
    layout_policy: str
    default: bool = False
    supports_expand: List[str] = Field(default_factory=list)


class LeanRouteStep(BaseModel):
    model_config = ConfigDict(extra="allow")

    node_id: str
    label: Optional[str] = None
    layer_index: Optional[int] = None
    route_index: int = 0
    family_ids: List[str] = Field(default_factory=list)
    hidden_sibling_count: int = 0
    branch_bundle_count: int = 0
    importance_score: float = 0.0


class LeanExpansionHandleRef(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: str
    key: str


class LeanBranchBundle(BaseModel):
    model_config = ConfigDict(extra="allow")

    bundle_id: str
    anchor_node_id: str
    layer_index: Optional[int] = None
    node_count: int = 0
    edge_count: int = 0
    dominant_edge_kind: Optional[str] = None
    sample_labels: List[str] = Field(default_factory=list)
    node_ids: List[str] = Field(default_factory=list)
    edge_ids: List[str] = Field(default_factory=list)
    expansion_handle: LeanExpansionHandleRef


class LeanFamilyOverlay(BaseModel):
    model_config = ConfigDict(extra="allow")

    family_id: str
    label: str
    color_token: Optional[str] = None
    route_node_ids: List[str] = Field(default_factory=list)
    node_count: int = 0
    anchor_node_id: Optional[str] = None


class LeanExpansionHandle(BaseModel):
    model_config = ConfigDict(extra="allow")

    handle_key: str
    kind: str
    node_ids: List[str] = Field(default_factory=list)
    edge_ids: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    default_limit: int = 12


class LeanLayoutHints(BaseModel):
    model_config = ConfigDict(extra="allow")

    rank_by_node_id: Dict[str, int] = Field(default_factory=dict)
    lane_by_node_id: Dict[str, int] = Field(default_factory=dict)
    family_lane_by_family_id: Dict[str, int] = Field(default_factory=dict)
    route_step_order: List[str] = Field(default_factory=list)


class LeanNodeSalience(BaseModel):
    model_config = ConfigDict(extra="allow")

    node_id: str
    on_primary_route: bool = False
    route_distance: Optional[int] = None
    layer_index: Optional[int] = None
    semantic_family_ids: List[str] = Field(default_factory=list)
    in_degree: int = 0
    out_degree: int = 0
    descendant_count: int = 0
    ancestor_count: int = 0
    terminal_claim_distance: Optional[int] = None
    external_dependency_distance: Optional[int] = None
    importance_score: float = 0.0
    visual_role: str = "other"


class LeanEdgeBundle(BaseModel):
    model_config = ConfigDict(extra="allow")

    bundle_id: str
    from_layer: Optional[int] = None
    to_layer: Optional[int] = None
    from_family: Optional[str] = None
    to_family: Optional[str] = None
    edge_kind_counts: Dict[str, int] = Field(default_factory=dict)
    node_count: int = 0
    edge_count: int = 0
    representative_edge_ids: List[str] = Field(default_factory=list)
    expansion_handle: LeanExpansionHandleRef


class LeanEdgeViews(BaseModel):
    model_config = ConfigDict(extra="allow")

    full_edges: List[str] = Field(default_factory=list)
    transitive_reduction_edges: List[str] = Field(default_factory=list)
    proof_spine_edges: List[str] = Field(default_factory=list)
    bundle_edges: List[LeanEdgeBundle] = Field(default_factory=list)


class LeanCondensedDag(BaseModel):
    model_config = ConfigDict(extra="allow")

    nodes: List[str] = Field(default_factory=list)
    edges: List[str] = Field(default_factory=list)
    family_anchor_node_ids: Dict[str, str] = Field(default_factory=dict)
    layout_hints: Dict[str, Any] = Field(default_factory=dict)


class LeanProofSpineBundle(BaseModel):
    model_config = ConfigDict(extra="allow")

    primary_route_id: Optional[str] = None
    final_label: Optional[str] = None
    route_steps: List[LeanRouteStep] = Field(default_factory=list)
    route_edges: List[str] = Field(default_factory=list)
    branch_bundles: List[LeanBranchBundle] = Field(default_factory=list)
    family_overlays: List[LeanFamilyOverlay] = Field(default_factory=list)
    external_dependency_chips: List[Dict[str, Any]] = Field(default_factory=list)
    terminal_claim_chips: List[Dict[str, Any]] = Field(default_factory=list)


class LeanGraphViews(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str = "lean_mathematics_graph_views_v2"
    legacy_schema_version: Optional[str] = None
    available: bool = False
    source_ref: Optional[str] = None
    source_fingerprint: Optional[str] = None
    inference: Dict[str, Any] = Field(default_factory=dict)
    view_keys: List[str] = Field(default_factory=list)
    view_registry: List[LeanViewRegistryEntry] = Field(default_factory=list)
    capabilities: Dict[str, bool] = Field(default_factory=dict)
    dependency_layers: List[Dict[str, Any]] = Field(default_factory=list)
    semantic_families: List[Dict[str, Any]] = Field(default_factory=list)
    final_theorem_routes: List[Dict[str, Any]] = Field(default_factory=list)
    high_degree_nodes: List[Dict[str, Any]] = Field(default_factory=list)
    terminal_claims: List[Dict[str, Any]] = Field(default_factory=list)
    external_dependencies: List[Dict[str, Any]] = Field(default_factory=list)
    proof_spine_bundle: LeanProofSpineBundle = Field(default_factory=LeanProofSpineBundle)
    layout_hints: LeanLayoutHints = Field(default_factory=LeanLayoutHints)
    expansion_handles: Dict[str, LeanExpansionHandle] = Field(default_factory=dict)
    node_salience: Dict[str, LeanNodeSalience] = Field(default_factory=dict)
    edge_views: LeanEdgeViews = Field(default_factory=LeanEdgeViews)
    condensed_dag: LeanCondensedDag = Field(default_factory=LeanCondensedDag)
    omission_receipt: LeanSurfaceOmissionReceipt = Field(default_factory=LeanSurfaceOmissionReceipt)


class LeanTimelineStep(BaseModel):
    step_id: str
    thread_id: str
    status: str
    artifact_ref: str
    check_id: str
    claim_boundary: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    elapsed_ms: Optional[float] = None
    ordinal: int = 0


class LeanCapabilityCard(BaseModel):
    capability_id: Optional[str] = None
    family: Optional[str] = None
    role: Optional[str] = None
    maturity: Optional[str] = None
    owner_surface: Optional[str] = None
    risk_boundary: Optional[str] = None
    next_action: Optional[str] = None
    source_refs: List[str] = Field(default_factory=list)
    validation_commands: List[str] = Field(default_factory=list)


class LeanValidationCard(BaseModel):
    check_id: str
    command: str
    authority: str
    latest_known_status: str = "unknown"
    source_fingerprint: Optional[str] = None


class LeanBoundaryCard(BaseModel):
    boundary_id: str
    claim_text: str
    boundary_kind: str
    proof_authority: str
    originating_doc: str
    originating_anchor: str


class LeanDisclosurePostureCard(BaseModel):
    posture_id: str
    label: str
    disclosure_scope: str
    carries: List[str] = Field(default_factory=list)
    excludes: List[str] = Field(default_factory=list)
    proof_authority_effect: str
    operator_authorization_required: bool = False
    source_refs: List[str] = Field(default_factory=list)


class LeanProvenanceProject(BaseModel):
    project_id: Optional[str] = None
    root: Optional[str] = None
    lean_toolchain: Optional[str] = None
    lake_manifest: Optional[str] = None
    dependency_count: Optional[int] = None
    build_provenance: Dict[str, Any] = Field(default_factory=dict)
    static_risk_scan: Dict[str, Any] = Field(default_factory=dict)


class LeanDocSection(BaseModel):
    anchor_id: str
    title: str
    byte_offset: int
    byte_length: int
    hash: str


class LeanSurfaceBase(BaseModel):
    surface_id: str
    available: bool
    omission_receipt: LeanSurfaceOmissionReceipt = Field(default_factory=LeanSurfaceOmissionReceipt)


class LeanOverviewSurface(LeanSurfaceBase):
    summary: Dict[str, Any] = Field(default_factory=dict)
    currentness: Dict[str, Any] = Field(default_factory=dict)


class LeanTheoremObservatorySurface(LeanSurfaceBase):
    observatory_id: Optional[str] = None
    route: Dict[str, Any] = Field(default_factory=dict)
    canonical_theorem: Dict[str, Any] = Field(default_factory=dict)
    route_steps: List[Dict[str, Any]] = Field(default_factory=list)
    certificate_objects: List[Dict[str, Any]] = Field(default_factory=list)
    certificate_microscope: Dict[str, Any] = Field(default_factory=dict)
    authority_chain: List[Dict[str, Any]] = Field(default_factory=list)
    receipt_chain: List[Dict[str, Any]] = Field(default_factory=list)
    performance_boundary: Dict[str, Any] = Field(default_factory=dict)
    proof_trace_flight_recorder: Dict[str, Any] = Field(default_factory=dict)
    proof_architecture: Dict[str, Any] = Field(default_factory=dict)
    target_runner_receipts: List[Dict[str, Any]] = Field(default_factory=list)
    anti_claims: List[str] = Field(default_factory=list)
    reviewer_questions: List[Dict[str, Any]] = Field(default_factory=list)
    authority_boundary: Optional[str] = None


class LeanDeclarationCatalogSurface(LeanSurfaceBase):
    declarations: List[LeanDeclarationCatalogItem] = Field(default_factory=list)
    declaration_count: int = 0
    kind_counts: Dict[str, int] = Field(default_factory=dict)
    ordering: str = "file,line_start,name"


class LeanDeclarationGraphSurface(LeanSurfaceBase):
    nodes: List[LeanGraphNode] = Field(default_factory=list)
    edges: List[LeanGraphEdge] = Field(default_factory=list)
    clusters: List[LeanGraphCluster] = Field(default_factory=list)
    edge_kind_counts: Dict[str, int] = Field(default_factory=dict)
    edge_taxonomy: List[str] = Field(default_factory=list)


class LeanObligationNode(BaseModel):
    node_id: str
    thread_id: str
    label: Optional[str] = None
    status: Optional[str] = None
    claim_type: Optional[str] = None
    evidence_kind: Optional[str] = None
    source_ref: Optional[str] = None
    claim_boundary: Optional[str] = None


class LeanObligationEdge(BaseModel):
    edge_id: str
    thread_id: str
    from_node_id: Optional[str] = None
    to_node_id: Optional[str] = None
    edge_kind: str = "depends_on"


class LeanObligationGraphSurface(LeanSurfaceBase):
    nodes: List[LeanObligationNode] = Field(default_factory=list)
    edges: List[LeanObligationEdge] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0


class LeanReceiptTimelineSurface(LeanSurfaceBase):
    steps: List[LeanTimelineStep] = Field(default_factory=list)
    step_count: int = 0


class LeanCapabilityCardsSurface(LeanSurfaceBase):
    cards: List[LeanCapabilityCard] = Field(default_factory=list)
    card_count: int = 0


class LeanValidationCardsSurface(LeanSurfaceBase):
    cards: List[LeanValidationCard] = Field(default_factory=list)
    card_count: int = 0


class LeanFullFidelityPacketCardSurface(LeanSurfaceBase):
    packet_id: Optional[str] = None
    disclosure_posture_id: Optional[str] = None
    packet_ref: Optional[str] = None
    receipt_ref: Optional[str] = None
    markdown_ref: Optional[str] = None
    status: Optional[str] = None
    packet_sha256: Optional[str] = None
    source_file_count: int = 0
    receipt_ref_count: int = 0
    claim_boundary_count: int = 0
    secret_exclusion_status: Optional[str] = None
    secret_exclusion_blocking_hit_count: Optional[int] = None
    latest_diagnostic_status: Optional[str] = None
    latest_diagnostic_environment_status: Optional[str] = None
    body_text_policy: Optional[str] = None
    authority_invariant: Optional[str] = None


class LeanFullFidelityPacketVerifierCardSurface(LeanSurfaceBase):
    verifier_id: Optional[str] = None
    verification_receipt_ref: Optional[str] = None
    verification_markdown_ref: Optional[str] = None
    replay_receipt_ref: Optional[str] = None
    replay_markdown_ref: Optional[str] = None
    capsule_manifest_ref: Optional[str] = None
    capsule_receipt_ref: Optional[str] = None
    capsule_markdown_ref: Optional[str] = None
    handoff_envelope_ref: Optional[str] = None
    handoff_receipt_ref: Optional[str] = None
    handoff_markdown_ref: Optional[str] = None
    packet_ref: Optional[str] = None
    packet_receipt_ref: Optional[str] = None
    status: Optional[str] = None
    verification_receipt_sha256: Optional[str] = None
    replay_receipt_sha256: Optional[str] = None
    capsule_receipt_sha256: Optional[str] = None
    handoff_receipt_sha256: Optional[str] = None
    packet_integrity: Optional[str] = None
    disclosure_boundary: Optional[str] = None
    secret_exclusion: Optional[str] = None
    source_ref_integrity: Optional[str] = None
    receipt_ref_integrity: Optional[str] = None
    claim_boundary_integrity: Optional[str] = None
    station_render_surface: Optional[str] = None
    lake_replay_status: Optional[str] = None
    dependency_hydration_status: Optional[str] = None
    dependency_hydration_mode: Optional[str] = None
    target_replay_status: Optional[str] = None
    target_runner_status: Optional[str] = None
    lake_workspace_status: Dict[str, Any] = Field(default_factory=dict)
    latest_diagnostic_environment_status: Optional[str] = None
    latest_diagnostic_ref: Optional[str] = None
    reviewer_acceptance_status: Optional[str] = None
    capsule_integrity_status: Optional[str] = None
    capsule_secret_exclusion: Optional[str] = None
    capsule_replay_status: Optional[str] = None
    capsule_portability_status: Optional[str] = None
    handoff_integrity_status: Optional[str] = None
    handoff_secret_exclusion: Optional[str] = None
    disclosure_authority_status: Optional[str] = None
    handoff_authority_status: Optional[str] = None
    recipient_binding_status: Optional[str] = None
    handoff_delivery_status: Optional[str] = None
    external_reviewer_replay_status: Optional[str] = None
    public_release_authority: Optional[str] = None
    handoff_reviewer_acceptance_status: Optional[str] = None
    proof_authority_delta: Optional[str] = None
    authority_invariant: Optional[str] = None


class LeanDisclosurePostureCardsSurface(LeanSurfaceBase):
    cards: List[LeanDisclosurePostureCard] = Field(default_factory=list)
    card_count: int = 0
    invariant: str = "Disclosure scope controls what can be shown; proof authority controls what can be claimed."


class LeanBoundaryCardsSurface(LeanSurfaceBase):
    cards: List[LeanBoundaryCard] = Field(default_factory=list)
    card_count: int = 0


class LeanProvenanceCardSurface(LeanSurfaceBase):
    projects: List[LeanProvenanceProject] = Field(default_factory=list)
    project_count: int = 0


class LeanDocSectionIndexSurface(LeanSurfaceBase):
    sections: List[LeanDocSection] = Field(default_factory=list)
    section_count: int = 0
    markdown_ref: Optional[str] = None


class LeanVisualSurfaces(BaseModel):
    schema_version: str = "lean_mathematics_visual_surfaces_v1"
    surface_keys: List[str] = Field(default_factory=list)
    consistency_token: Optional[str] = None
    carve_out_thresholds: Dict[str, int] = Field(default_factory=dict)
    overview: LeanOverviewSurface
    theorem_observatory: LeanTheoremObservatorySurface
    declaration_catalog: LeanDeclarationCatalogSurface
    declaration_graph: LeanDeclarationGraphSurface
    obligation_graph: LeanObligationGraphSurface
    receipt_timeline: LeanReceiptTimelineSurface
    capability_cards: LeanCapabilityCardsSurface
    validation_cards: LeanValidationCardsSurface
    full_fidelity_packet_card: LeanFullFidelityPacketCardSurface
    full_fidelity_packet_verifier_card: LeanFullFidelityPacketVerifierCardSurface
    disclosure_posture_cards: LeanDisclosurePostureCardsSurface
    boundary_cards: LeanBoundaryCardsSurface
    provenance_card: LeanProvenanceCardSurface
    doc_section_index: LeanDocSectionIndexSurface


class LeanMathematicsMicrocosmSnapshotResponse(BaseModel):
    """
    [ROLE]
    - Teleology: One-fetch read-only Lean/formal-math microcosm payload for Station.
    - Wire contract: transport over generated projection artifacts only; no Lean
      execution, provider call, rebuild, or mutation control is exposed.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_serialization_defaults_required=True,
    )

    schema_name: Literal["lean_mathematics_microcosm_snapshot_v1"] = Field(
        default="lean_mathematics_microcosm_snapshot_v1",
        alias="schema",
        serialization_alias="schema",
    )
    available: bool
    projection_ref: str
    receipt_ref: str
    markdown_ref: str
    projection: Dict[str, Any] = Field(default_factory=dict)
    receipt: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)
    currentness: Dict[str, Any] = Field(default_factory=dict)
    lean_projects: List[Dict[str, Any]] = Field(default_factory=list)
    formal_math_threads: List[Dict[str, Any]] = Field(default_factory=list)
    capability_snapshot: Dict[str, Any] = Field(default_factory=dict)
    graph_views: LeanGraphViews = Field(default_factory=LeanGraphViews)
    theorem_observatory: Dict[str, Any] = Field(default_factory=dict)
    validation_surfaces: Dict[str, Any] = Field(default_factory=dict)
    route_cards: List[Dict[str, Any]] = Field(default_factory=list)
    anti_claims: List[str] = Field(default_factory=list)
    disclosure_postures: List[LeanDisclosurePostureCard] = Field(default_factory=list)
    authority_boundary: Dict[str, Any] = Field(default_factory=dict)
    visual_surfaces: LeanVisualSurfaces
    omission_receipt: Dict[str, Any] = Field(default_factory=dict)


class MissionTransactionPreflightResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Read-only landing-safety packet for Station/HUD visibility.
    - Wire contract: mirrors mission_transaction_landing_preflight_v0 while
      allowing additive backend packet fields without breaking the HUD.
    """
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    schema_name: Literal["mission_transaction_landing_preflight_v0"] = Field(
        default="mission_transaction_landing_preflight_v0",
        alias="schema",
        serialization_alias="schema",
    )
    repo_root: str
    mode: Literal["read_only"]
    mutation_policy: Dict[str, bool] = Field(default_factory=dict)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    git: Dict[str, Any] = Field(default_factory=dict)
    path_classifications: List[Dict[str, Any]] = Field(default_factory=list)
    coverage_gaps: List[Dict[str, Any]] = Field(default_factory=list)
    work_ledger: Dict[str, Any] = Field(default_factory=dict)
    generated_projection_registry: Dict[str, Any] = Field(default_factory=dict)
    scoped_commit_capability: Dict[str, Any] = Field(default_factory=dict)
    shared_worktree_guard: Dict[str, Any] = Field(default_factory=dict)
    mission_transaction_card: Dict[str, Any] = Field(default_factory=dict)
    landing_decision: Dict[str, Any] = Field(default_factory=dict)


class WorkLedgerQueryResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Typed recipe-query payload for work-ledger retrieval.
    - Wire contract: phase_id/family_id/filters are absent on the
      supersession_chain early-return path in work_ledger.query_recipe;
      matched and results are always present.
    """
    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["work_ledger_query_v1"] = Field(
        default="work_ledger_query_v1",
        alias="schema",
        serialization_alias="schema",
    )
    generated_at: str
    recipe: str
    phase_id: Optional[str] = None
    family_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    matched: int
    results: List[Dict[str, Any]]


class WorkLedgerThreadResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Typed detail payload for one selected work-ledger thread.
    - Wire contract: every field is always emitted when the route returns
      200; the route returns 404 instead of an empty thread.
    """
    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["work_ledger_thread_v1"] = Field(
        default="work_ledger_thread_v1",
        alias="schema",
        serialization_alias="schema",
    )
    generated_at: str
    td_id: str
    thread: Dict[str, Any]
    supersession_chain: List[Dict[str, Any]]


class ZenithRuntimeServiceStatus(BaseModel):
    """Runtime/service row for the native Zenith shell."""
    id: str
    label: str
    state: str
    detail: str
    tone: Optional[str] = None
    path: Optional[str] = None
    updated_at: Optional[str] = None
    command: Optional[str] = None


class ZenithHealthResponse(BaseModel):
    """Cheap readiness probe for Zenith.app startup polling."""
    ok: bool = True
    generated_at: str


class ZenithRuntimeSnapshot(BaseModel):
    """Backend-owned runtime snapshot consumed by Zenith.app."""
    generated_at: str
    repo_root: str
    start_command: str
    server_log_path: Optional[str] = None
    backend: ZenithRuntimeServiceStatus
    pipeline_signal_watcher: ZenithRuntimeServiceStatus
    controller_surfaces: List[ZenithRuntimeServiceStatus] = Field(default_factory=list)
    launch_agents: List[ZenithRuntimeServiceStatus] = Field(default_factory=list)
    helper_surfaces: List[ZenithRuntimeServiceStatus] = Field(default_factory=list)
    backend_log_lines: List[str] = Field(default_factory=list)


class ZenithBootstrapResponse(BaseModel):
    """Single bootstrap packet for the native Zenith shell."""
    generated_at: str
    attention: Dict[str, Any] = Field(default_factory=dict)
    station_launcher: StationLauncherSnapshot
    runtime: ZenithRuntimeSnapshot


class RawSeedAppendRequest(BaseModel):
    """
    [ROLE]
    - Teleology: Typed request body for app-native raw-seed capture surfaces.
    - Mechanism: Carries the target family token plus the text block to append
      and an optional heading.
    """
    family: str = "__active__"
    text: str
    heading: Optional[str] = None


class RawSeedAppendArtifacts(BaseModel):
    """
    [ROLE]
    - Teleology: Return the refreshed artifact paths after a raw-seed append so
      native and web shells can deep-link into the right authority surfaces.
    """
    family_dir: str
    raw_seed_path: str
    raw_seed_json_path: Optional[str] = None
    raw_seed_index_path: Optional[str] = None
    raw_seed_snapshot_path: Optional[str] = None


class RawSeedAppendResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Structured response for `POST /api/raw-seed/append`.
    - Mechanism: Includes the resolved family, best-effort appended paragraph
      anchors, refreshed artifact paths, and the underlying kernel result.
    """
    ok: Literal[True] = True
    family: str
    heading: Optional[str] = None
    appended_anchor_ids: List[str] = Field(default_factory=list)
    artifacts: RawSeedAppendArtifacts
    kernel_result: Dict[str, Any] = Field(default_factory=dict)


class RawSeedFamilyCard(BaseModel):
    id: str
    title: str
    family_dir: str


class RawSeedFamiliesResponse(BaseModel):
    kind: Literal["raw_seed_families"] = "raw_seed_families"
    families: List[RawSeedFamilyCard] = Field(default_factory=list)


class RawSeedAssimilationGraphNode(BaseModel):
    id: str
    kind: str
    label: str
    title: Optional[str] = None
    summary: Optional[str] = None
    path: Optional[str] = None
    status: Optional[str] = None
    recommended_action: Optional[str] = None
    routing_state: Optional[str] = None


class RawSeedAssimilationGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    kind: str


class RawSeedAssimilationGraph(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    nodes: List[RawSeedAssimilationGraphNode] = Field(default_factory=list)
    edges: List[RawSeedAssimilationGraphEdge] = Field(default_factory=list)


class RawSeedAssimilationRepresentativeShard(BaseModel):
    id: str
    parent_paragraph_id: str
    voice_anchor: str = ""
    clarified_statement: str = ""
    gestures_towards: List[str] = Field(default_factory=list)


class RawSeedAssimilationSlotSummary(BaseModel):
    decision: Optional[str] = None
    target_id: Optional[str] = None
    target_title: Optional[str] = None


class RawSeedAssimilationBundleSlot(BaseModel):
    slot_kind: str
    decision: str
    target_id: Optional[str] = None
    target_title: Optional[str] = None
    target_statement: Optional[str] = None
    rationale: str = ""
    refinement_note: str = ""
    reference_group: Dict[str, Any] = Field(default_factory=dict)
    evidence_preview: List[Dict[str, Any]] = Field(default_factory=list)
    merged_from_ids: List[str] = Field(default_factory=list)
    source_id: Optional[str] = None
    implementation_gap: Optional[Dict[str, Any]] = None
    proposed_node: Optional[Dict[str, Any]] = None


class RawSeedAssimilationClusterCard(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    group_id: str
    title: str
    total_shards: int
    routing_state_counts: Dict[str, int] = Field(default_factory=dict)
    alchemy_form_id: Optional[str] = None
    recipe_status: str
    recommended_action: str
    bundle_id: Optional[str] = None
    signature_tokens: List[str] = Field(default_factory=list)
    signature_phrases: List[str] = Field(default_factory=list)
    representative_shards: List[RawSeedAssimilationRepresentativeShard] = Field(default_factory=list)
    slot_summary: Dict[str, RawSeedAssimilationSlotSummary] = Field(default_factory=dict)


class RawSeedImplementationGap(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    mechanism_id: str
    mechanism_title: str
    phase_seed_slug: str
    summary: str
    candidate_paths: List[str] = Field(default_factory=list)
    paper_module_slugs: List[str] = Field(default_factory=list)
    source_bundle_id: Optional[str] = None
    source_group_id: Optional[str] = None
    status: str
    notes: Optional[str] = None


class RawSeedAssimilationBundleCard(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    bundle_id: str
    form_id: str
    title: str
    status: str
    selection: Dict[str, Any] = Field(default_factory=dict)
    shard_count: int
    parent_paragraph_count: int
    signature_tokens: List[str] = Field(default_factory=list)
    signature_phrases: List[str] = Field(default_factory=list)
    slots: Dict[str, RawSeedAssimilationBundleSlot] = Field(default_factory=dict)
    reference_group: Dict[str, Any] = Field(default_factory=dict)
    phase_seed_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    bundle_hash: str
    last_dry_run_at: Optional[str] = None
    last_dry_run_ok: bool = False
    last_dry_run_bundle_hash: Optional[str] = None
    dry_run_ready: bool = False
    dry_run_required: bool = False
    slot_outcomes: Dict[str, Any] = Field(default_factory=dict)


class RawSeedAssimilationProjectionResponse(BaseModel):
    kind: Literal["raw_seed_assimilation_projection"] = "raw_seed_assimilation_projection"
    schema_version: Literal["raw_seed_assimilation_projection_v1"] = "raw_seed_assimilation_projection_v1"
    family: RawSeedFamilyCard
    counts: Dict[str, int] = Field(default_factory=dict)
    clusters: List[RawSeedAssimilationClusterCard] = Field(default_factory=list)
    bundles: List[RawSeedAssimilationBundleCard] = Field(default_factory=list)
    implementation_gaps: List[RawSeedImplementationGap] = Field(default_factory=list)
    graph: RawSeedAssimilationGraph = Field(default_factory=RawSeedAssimilationGraph)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    diagnostics: List[Dict[str, Any]] = Field(default_factory=list)
    meta_layer: Dict[str, Any] = Field(default_factory=dict)


class RawSeedAssimilationClusterDetailResponse(BaseModel):
    kind: Literal["raw_seed_assimilation_cluster_detail"] = "raw_seed_assimilation_cluster_detail"
    family: RawSeedFamilyCard
    cluster: RawSeedAssimilationClusterCard
    related_bundles: List[RawSeedAssimilationBundleCard] = Field(default_factory=list)
    doctrine_targets: List[Dict[str, Any]] = Field(default_factory=list)
    graph: RawSeedAssimilationGraph = Field(default_factory=RawSeedAssimilationGraph)


class RawSeedAssimilationBundleDetailResponse(BaseModel):
    kind: Literal["raw_seed_assimilation_bundle_detail"] = "raw_seed_assimilation_bundle_detail"
    family: RawSeedFamilyCard
    bundle: RawSeedAssimilationBundleCard
    cluster: Optional[RawSeedAssimilationClusterCard] = None
    graph: RawSeedAssimilationGraph = Field(default_factory=RawSeedAssimilationGraph)


class RawSeedAssimilationCommitRequest(BaseModel):
    confirm: bool = False
    operator_note: Optional[str] = None


class RawSeedAssimilationOperationReceipt(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    kind: Literal["raw_seed_assimilation_operation_receipt"] = "raw_seed_assimilation_operation_receipt"
    operation: str
    family: str
    input: Dict[str, Any] = Field(default_factory=dict)
    command_equivalent: str
    started_at: str
    finished_at: str
    status: Literal["ok", "failed"] = "ok"
    artifacts: List[str] = Field(default_factory=list)
    before_counts: Dict[str, Any] = Field(default_factory=dict)
    after_counts: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    output: Dict[str, Any] = Field(default_factory=dict)


class RawSeedShardSearchRequest(BaseModel):
    query: str
    limit: int = Field(default=40, ge=1, le=200)


class RawSeedShardSearchResponse(BaseModel):
    kind: Literal["raw_seed_shard_search_results"] = "raw_seed_shard_search_results"
    schema_version: Literal["raw_seed_shard_search_results_v1"] = "raw_seed_shard_search_results_v1"
    family: str
    query: str
    matched: int
    results: List[Dict[str, Any]] = Field(default_factory=list)
    related: List[Dict[str, Any]] = Field(default_factory=list)
    total_in_index: int = 0
    total_in_pool: int = 0
    graph: RawSeedAssimilationGraph = Field(default_factory=RawSeedAssimilationGraph)


class RawSeedAssimilationShardDetailResponse(BaseModel):
    kind: Literal["raw_seed_assimilation_shard_detail"] = "raw_seed_assimilation_shard_detail"
    family: RawSeedFamilyCard
    shard: Dict[str, Any] = Field(default_factory=dict)
    paragraph: Optional[Dict[str, Any]] = None
    linked_bundles: List[RawSeedAssimilationBundleCard] = Field(default_factory=list)
    group_ids: List[str] = Field(default_factory=list)
    graph: RawSeedAssimilationGraph = Field(default_factory=RawSeedAssimilationGraph)


class RawSeedAssimilationParagraphDetailResponse(BaseModel):
    kind: Literal["raw_seed_assimilation_paragraph_detail"] = "raw_seed_assimilation_paragraph_detail"
    family: RawSeedFamilyCard
    paragraph_id: str
    section_id: Optional[str] = None
    section_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    text: str
    raw_markdown: Optional[str] = None
    child_shards: List[Dict[str, Any]] = Field(default_factory=list)
    doctrine_links: List[Dict[str, Any]] = Field(default_factory=list)
    graph: RawSeedAssimilationGraph = Field(default_factory=RawSeedAssimilationGraph)


class QueryDrivenHolographicSliceRequest(BaseModel):
    query: str
    family: str = "09"
    focus: List[str] = Field(default_factory=list)
    max_nodes: int = Field(default=80, ge=1, le=500)


class QueryDrivenHolographicSliceResponse(BaseModel):
    kind: Literal["query_driven_holographic_slice"] = "query_driven_holographic_slice"
    query: str
    sentence: str
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_actions: List[Dict[str, Any]] = Field(default_factory=list)
    source_paths: List[str] = Field(default_factory=list)


class SystemSurfaceRegistrySummaryResponse(BaseModel):
    kind: Literal["system_surface_registry"] = "system_surface_registry"
    schema_version: Literal["system_surface_registry_v1"] = "system_surface_registry_v1"
    generated_at: Optional[str] = None
    artifact_path: Optional[str] = None
    node_count: int = 0
    edge_count: int = 0
    kind_counts: Dict[str, int] = Field(default_factory=dict)
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)


class SystemSurfaceRegistrySearchResponse(BaseModel):
    kind: Literal["system_surface_registry_search_results"] = "system_surface_registry_search_results"
    query: str
    matched: int = 0
    results: List[Dict[str, Any]] = Field(default_factory=list)


class SystemSurfaceRegistryNodeDetailResponse(BaseModel):
    kind: Literal["system_surface_registry_node_detail"] = "system_surface_registry_node_detail"
    node: Dict[str, Any] = Field(default_factory=dict)
    related_nodes: List[Dict[str, Any]] = Field(default_factory=list)
    related_edges: List[Dict[str, Any]] = Field(default_factory=list)


class SystemSurfaceRegistryRebuildResponse(BaseModel):
    kind: Literal["system_surface_registry_rebuild_receipt"] = "system_surface_registry_rebuild_receipt"
    generated_at: Optional[str] = None
    artifact_path: str
    node_count: Optional[int] = None
    edge_count: Optional[int] = None


class ConfigSurfaceSummaryResponse(BaseModel):
    kind: Literal["config_authority_registry"] = "config_authority_registry"
    schema_version: Literal["config_authority_registry_v1"] = "config_authority_registry_v1"
    generated_at: Optional[str] = None
    artifact_path: Optional[str] = None
    authority_posture: Optional[str] = None
    governing_standard: Optional[str] = None
    paper_module: Optional[str] = None
    row_count: int = 0
    class_counts: Dict[str, int] = Field(default_factory=dict)
    mutability_counts: Dict[str, int] = Field(default_factory=dict)
    diagnostic_count: int = 0
    diagnostics: List[Dict[str, Any]] = Field(default_factory=list)
    config_ref_index: Dict[str, str] = Field(default_factory=dict)
    api_routes: List[str] = Field(default_factory=list)
    agent_entry_routes: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)


class ConfigSurfaceSearchResponse(BaseModel):
    kind: Literal["config_authority_registry_search_results"] = "config_authority_registry_search_results"
    query: str
    matched: int = 0
    results: List[Dict[str, Any]] = Field(default_factory=list)


class ConfigSurfaceNodeDetailResponse(BaseModel):
    kind: Literal["config_authority_registry_node_detail"] = "config_authority_registry_node_detail"
    node: Dict[str, Any] = Field(default_factory=dict)
    related_rows: List[Dict[str, Any]] = Field(default_factory=list)


class ConfigSurfaceEffectiveResponse(BaseModel):
    kind: Literal["config_authority_effective_trace"] = "config_authority_effective_trace"
    config_id: Optional[str] = None
    canonical_label: Optional[str] = None
    authority_path: Optional[str] = None
    mutability_class: Optional[str] = None
    redaction_policy: Optional[str] = None
    effective_trace: Dict[str, Any] = Field(default_factory=dict)


class ConfigSurfaceDiagnosticsResponse(BaseModel):
    kind: Literal["config_authority_registry_diagnostics"] = "config_authority_registry_diagnostics"
    generated_at: Optional[str] = None
    diagnostic_count: int = 0
    class_counts: Dict[str, int] = Field(default_factory=dict)
    mutability_counts: Dict[str, int] = Field(default_factory=dict)
    diagnostics: List[Dict[str, Any]] = Field(default_factory=list)


class ConfigSurfaceRebuildResponse(BaseModel):
    kind: Literal["config_authority_registry_rebuild_receipt"] = "config_authority_registry_rebuild_receipt"
    generated_at: Optional[str] = None
    artifact_path: str
    row_count: Optional[int] = None
    diagnostic_count: Optional[int] = None

# =============================================================================
# 3. IGNITE PAYLOAD (Client -> Server)
# =============================================================================

class IgnitePayload(BaseModel):
    """
    [ROLE]
    - Teleology: Define the client→server ignition request.
    - Strictness: extra="forbid" prevents typos or ghost arguments.
    """
    model_config = ConfigDict(extra="forbid")

    mission_name: str = Field(..., description="The mission folder name.")
    target_id: str = Field(..., description="The exact node ID to execute.")
    run_mode: RunMode
    execution_mode: ExecutionMode
    subject_group: str = Field(default="lab")
    source_run_id: Optional[str] = None
    feed_source_run_id: Optional[str] = None
    source_data_root_id: Optional[str] = None
    feed_data_root_id: Optional[str] = None
    horizon: Optional[str] = Field(
        default=None,
        description="Prediction horizon policy. Values: 'next_us_close', '24h', '48h', or ISO datetime. Defaults to 'next_us_close' when None."
    )
    # [C6] Bounded failure routing guard fields.
    # These must be present from run start and are passed into child-run ignition
    # payloads by the server route via _next_routing_state().
    subgraph_depth: int = Field(
        default=0,
        description="Reroute recursion depth. Guards against over-depth dispatch (max=2)."
    )
    failed_targets_routed: List[str] = Field(
        default_factory=list,
        description="Targets already attempted in this run lineage. Guards against duplicate routing."
    )
    force_load_stale_feeds: bool = Field(
        default=False,
        description="When true, resume mode can reuse existing feed artifacts even if node_hash mismatches current node definition."
    )

    @model_validator(mode='after')
    def validate_invariants(self) -> 'IgnitePayload':
        """
        [ACTION]
        - Teleology: Enforce cross-field invariants for ignition requests.
        - Preconditions: run_mode and execution_mode are set; source_run_id/feed_source_run_id may be None.
        - Guarantee: Returns self when invariant checks pass.
        - Fails: Raises ValueError when required ids are missing or illegal mode combinations are requested.
        """
        r_mode = self.run_mode
        e_mode = self.execution_mode
        src = self.source_run_id
        feed = self.feed_source_run_id

        if r_mode == RunMode.RESUME:
            if not src:
                raise ValueError("RunMode.RESUME requires 'source_run_id'.")
            if e_mode == ExecutionMode.LAB:
                 raise ValueError("Cannot RESUME in LAB mode. Use FORK to test historical states.")

        if r_mode == RunMode.FORK:
            if not src:
                raise ValueError("RunMode.FORK requires 'source_run_id'.")
            if e_mode == ExecutionMode.LAB and not feed:
                raise ValueError("Lab/Audit execution requires a 'feed_source_run_id'.")

        if r_mode == RunMode.FRESH:
            if e_mode == ExecutionMode.LAB:
                if not feed:
                     raise ValueError("Fresh Lab execution requires a 'feed_source_run_id' to mock inputs.")

        if self.horizon is not None:
            if self.horizon not in ["next_us_close", "24h", "48h"]:
                try:
                    from datetime import datetime
                    datetime.fromisoformat(self.horizon.replace('Z', '+00:00'))
                except ValueError:
                    raise ValueError(f"Invalid horizon format: '{self.horizon}'. Must be 'next_us_close', '24h', '48h', or a valid ISO 8601 datetime.")

        return self

class TemporalContract(BaseModel):
    """
    [ROLE]
    - Teleology: Canonical backend-resolved temporal pairing returned after ignition.
    - Mechanism: Backend computes this from the resolved runtime context; frontend renders it as
      the locked HUD display — frontend selection is preserved, backend is authoritative about
      what that selection resolved to.
    - Guarantee: Always present in IgnitionResponse; truth_run_id is null for live-reality and
      feed-replay Lab runs.
    """
    subject_run_id: Optional[str] = None
    truth_run_id: Optional[str] = None
    replay_source_run_id: Optional[str] = None
    subject_data_root_id: Optional[str] = None
    truth_data_root_id: Optional[str] = None
    replay_source_data_root_id: Optional[str] = None
    target_time_iso: Optional[str] = None
    horizon_label: str
    validation_status: Literal["valid", "live", "unresolved", "feed_replay"]
    delta_s: Optional[float] = None
    subject_run_timestamp_iso: Optional[str] = None
    subject_data_as_of_iso: Optional[str] = None
    replay_source_run_timestamp_iso: Optional[str] = None
    replay_source_data_as_of_iso: Optional[str] = None
    truth_run_timestamp_iso: Optional[str] = None
    truth_data_as_of_iso: Optional[str] = None
    ignition_data_as_of_iso: Optional[str] = None

    @field_validator("validation_status", mode="before")
    @classmethod
    def normalize_validation_status(cls, value: Any) -> str:
        """
        [ACTION]
        - Teleology: Coerce raw validation_status values to one of the four allowed literals.
        - Guarantee: Returns a valid literal string ("valid", "live", "unresolved", or "feed_replay").
        - Fails: None (unknown values are silently coerced to "unresolved").
        """
        if not isinstance(value, str):
            return "unresolved"
        normalized = value.strip().lower()
        if normalized in {"valid", "live", "unresolved", "feed_replay"}:
            return normalized
        return "unresolved"

class ResumeFeedStaleNode(BaseModel):
    """
    [ROLE]
    - Teleology: Describe a feed artifact that exists for resume but has stale node identity.
    """
    node_id: str
    artifact_hash: Optional[str] = None
    current_hash: str
    artifact_status: Optional[str] = None
    config_ref: Optional[str] = None
    artifact_config_ref: Optional[str] = None
    merged_hash: Optional[str] = None
    artifact_merged_hash: Optional[str] = None

class ResumeFeedPreflightPayload(BaseModel):
    """
    [ROLE]
    - Teleology: Request stale-feed diagnostics for a resume ignition candidate.
    """
    source_run_id: str
    target_id: str

class ResumeFeedPreflightResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Return stale-feed diagnostics used by ignition UX warning/override flow.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    source_run_id: str
    target_id: str
    scope_feed_node_count: int
    has_stale_feeds: bool
    reusable_feed_nodes: List[str] = Field(default_factory=list)
    stale_feed_nodes: List[ResumeFeedStaleNode] = Field(default_factory=list)
    missing_feed_nodes: List[str] = Field(default_factory=list)

class IgnitionResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Return explicit status of ignition attempt.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    run_id: str
    status: Literal["ignited", "failed", "busy"]
    topology_changed: bool
    temporal_contract: Optional[TemporalContract] = None

class StopRunResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Return explicit status of stop attempt.
    """
    run_id: Optional[str]
    status: Literal["stopped", "no_active_run", "failed"]

# =============================================================================
# 4. TOPOLOGY & SNAPSHOTS
# =============================================================================

class TopologyError(BaseModel):
    """
    [ROLE]
    - Teleology: Provide a structured topology failure payload (e.g., cycle detection) to the client.
    - Mechanism: Pydantic model embedded in GraphSnapshot.topology_error.
    - Guarantee: Conveys a stable error code plus human-readable details and optional cycle path.
    - Non-goal: Computing the topology error (produced by topology/governance layers).
    """
    error: str = "TOPOLOGY_CYCLE_DETECTED"
    details: str
    cycle_path: List[str] = Field(default_factory=list)
    is_fatal: bool = True

class ProvenanceView(BaseModel):
    """
    [ROLE]
    - Teleology: Carry compact node configuration provenance for HUD display and auditability.
    """
    config_ref: Optional[str] = None
    override_keys: Optional[List[str]] = None
    inline_overrides_preview: Optional[Dict[str, Any]] = None
    preview_truncated: bool = False
    merged_hash: Optional[str] = None

class NodeView(BaseModel):
    """
    [ROLE]
    - Teleology: Provide the UI-facing node projection.
    """
    id: str
    label: str
    type: Literal["node", "tool"] = "node"
    
    # Coordinates (Logical)
    lane: LaneEnum
    wave: int
    
    # HUD Data
    teleology: Optional[str] = "N/A"
    mechanism: Optional[str] = "Standard"
    expectation: Optional[str] = "Any"
    instruction: str = Field(default="")
    dependencies: List[str] = Field(default_factory=list)
    contracts: List[str] = Field(default_factory=list)
    timeout: Optional[float] = None
    
    # Rich Metadata
    platform: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    
    # Metadata
    group: str
    is_artifact: bool = False
    is_upstream: bool = False
    source_group: Optional[str] = None
    provenance: Optional[ProvenanceView] = None
    mission_manifest: Optional[Dict[str, Any]] = None

class EdgeView(BaseModel):
    """
    [ROLE]
    - Teleology: Represent a UI-facing directed edge between nodes.
    - Mechanism: Pydantic model used in GraphSnapshot.edges.
    - Guarantee: Provides source/target ids plus an optional edge type discriminator.
    - Non-goal: Geometry, routing, or rendering decisions.
    """
    id: str
    source: str
    target: str
    type: str = "default"

class GraphSnapshot(BaseModel):
    """
    [ROLE]
    - Teleology: Provide a complete graph snapshot for a run (nodes, edges, and optional topology error).
    - Mechanism: Pydantic model serialized to the client for visualization.
    - Guarantee: Includes run_id/timestamp/root_id plus NodeView/EdgeView collections.
    - Couples: Client rendering assumes NodeView.id/EdgeView.source/EdgeView.target consistency.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    run_id: str
    timestamp: float
    root_id: str
    nodes: List[NodeView]
    edges: List[EdgeView]
    topology_error: Optional[TopologyError] = None

GraphView = GraphSnapshot


class ControlRoomGraphContext(BaseModel):
    """
    [ROLE]
    - Teleology: Describe the graph truth source that caused the Control Room readiness state.
    - Mechanism: Compact read-only context derived from the backend mission graph preview route.
    - Guarantee: Keeps graph presence/counts/provenance explicit for station-render receipts.
    """
    source: str = "backend_mission_graph_preview"
    contract_id: str = "mission_graph_view_v1"
    status: Literal["present", "empty", "missing", "error"] = "missing"
    node_count: int = 0
    edge_count: int = 0
    root_id: Optional[str] = None
    run_id: Optional[str] = None
    error: Optional[str] = None


class ControlRoomRunContext(BaseModel):
    """
    [ROLE]
    - Teleology: Capture active-run truth used by the Control Room operational readiness row.
    - Mechanism: Normalized subset of /api/run/status.
    """
    source: str = "api_run_status"
    status: str = "idle"
    active_run_id: Optional[str] = None
    active_mission: Optional[str] = None
    is_running: bool = False


class ControlRoomBridgeContext(BaseModel):
    """
    [ROLE]
    - Teleology: Capture bridge and preflight truth used by the Control Room operational readiness row.
    - Mechanism: Normalized subset of bridge diagnostics.
    """
    source: str = "api_bridge_status"
    status: Literal["online", "offline", "error", "unknown"] = "unknown"
    preflight_status: Literal["ready", "offline", "error", "unknown"] = "unknown"
    diagnostics_captured_at: Optional[str] = None
    error: Optional[str] = None


class ControlRoomOperationalContextResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Bind Control Room readiness to backend graph/run/bridge/preflight truth.
    - Mechanism: Joins existing backend owners into one compact payload consumed by the cockpit root attrs.
    - Guarantee: Additive response shape; does not create graph truth in the frontend.
    """
    model_config = ConfigDict(populate_by_name=True)

    schema_name: Literal["control_room_operational_context_v1"] = Field(
        default="control_room_operational_context_v1",
        alias="schema",
        serialization_alias="schema",
    )
    generated_at: str
    mission_name: str
    target_id: Optional[str] = None
    route_ready: bool = False
    state: Literal["populated", "resting", "missing", "fallback", "invalid"] = "missing"
    graph: ControlRoomGraphContext = Field(default_factory=ControlRoomGraphContext)
    run: ControlRoomRunContext = Field(default_factory=ControlRoomRunContext)
    bridge: ControlRoomBridgeContext = Field(default_factory=ControlRoomBridgeContext)
    execution_authority: Literal["operator_controlled", "locked"] = "operator_controlled"

# =============================================================================
# 5. LIVE RUNTIME STATE & LOGS
# =============================================================================

class RunStatusVector(BaseModel):
    """
    [ROLE]
    - Teleology: Aggregate current runtime states for polling/initial hydration.
    """
    run_id: str
    status: str
    node_states: Dict[str, str] = Field(default_factory=dict)
    container_states: Dict[str, str] = Field(default_factory=dict)

class LogLine(BaseModel):
    """
    [ROLE]
    - Teleology: Structured log entry for Console Drawer.
    """
    timestamp: str
    source: Literal["system", "engine", "bridge"]
    level: str
    message: str
    node_id: Optional[str] = None

class RunSummary(BaseModel):
    """
    [ROLE]
    - Teleology: Detailed post-run report (persisted as run_summary.json).
    - Note: Grade must be lowercase (green/amber/red) to match Engine output.
    """
    model_config = ConfigDict(extra="ignore")
    
    run_id: str
    timestamp: float
    grade: Literal["green", "amber", "red"]
    grade_reason: str
    node_outcomes: Dict[str, str] # {node_id: status}
    duration_seconds: float

class ToolDiagnosticsSchema(BaseModel):
    """
    [ROLE]
    - Teleology: Canonical diagnostics schema for tool-run metadata.
    - Mechanism: Additive row-accounting and warning fields used by DataView/adapter contracts.
    """
    input_rows: int = 0
    output_rows: int = 0
    dropped_rows: int = 0
    warnings: List[str] = Field(default_factory=list)
    data_available_unused: List[str] = Field(default_factory=list)
    data_available_unused_count: int = 0

class ToolMetadataSchema(BaseModel):
    """
    [ROLE]
    - Teleology: Canonical additive metadata contract for tool artifacts/sidecars.
    - Mechanism: Optional-friendly schema that coexists with legacy metadata keys.
    """
    tool: Optional[str] = None
    status: Optional[str] = None
    items_count: Optional[int] = None
    timestamp: Optional[Any] = None  # Legacy field; may be epoch or ISO by producer
    timestamp_iso: Optional[str] = None
    timestamp_epoch_s: Optional[float] = None
    schema_version: Optional[str] = None
    data_schema_version: Optional[str] = None
    config_ref: Optional[str] = None
    merged_hash: Optional[str] = None
    override_keys: List[str] = Field(default_factory=list)
    diagnostics: ToolDiagnosticsSchema = Field(default_factory=ToolDiagnosticsSchema)
    # [C4] Horizon metadata — required on all is_artifact=True prediction artifacts.
    target_time_iso: Optional[str] = None
    horizon_label: Optional[str] = None

class ToolRunTelemetry(BaseModel):
    """
    [ROLE]
    - Teleology: Typed response for the telemetry endpoint; provides a contract-tested view of a
      single tool-node execution including identity, execution metadata, provenance, and data payload.
    - Mechanism: Pydantic model returned by GET /api/run/{run_id}/telemetry/{node_id}.
    - Guarantee: Missing/legacy artifact fields are backfilled with safe defaults so the schema always
      validates regardless of artifact age.
    - Non-goal: Raw artifact passthrough (use /artifacts endpoint for that).
    """
    run_id: str
    node_id: str
    status: str
    metadata: ToolMetadataSchema
    provenance: ProvenanceView
    data: Optional[Dict[str, Any]] = None

# =============================================================================
# 6. CONFIG
# =============================================================================

class RunRequest(BaseModel):
    """
    [ROLE]
    - Teleology: Define a minimal run request shape for initiating execution.
    - Mechanism: Pydantic model used for request parsing and validation.
    - Guarantee: Carries target plus mode selectors and optional source ids.
    - Fails: Pydantic validation errors on malformed payloads.
    """
    target: str
    run_mode: RunMode = RunMode.FRESH
    execution_mode: ExecutionMode = ExecutionMode.RUNTIME
    source_run_id: Optional[str] = None
    feed_source_run_id: Optional[str] = None

class UIConfig(BaseModel):
    """
    [ROLE]
    - Teleology: Define persisted/tunable UI layout and rendering configuration.
    - Mechanism: Pydantic model with permissive extra fields (extra="allow") for forward compatibility.
    - Guarantee: Provides defaults for layout, physics, toggles, and lane color overrides.
    - Forbid: Treating these values as authoritative server constraints (UI-only intent).
    """
    model_config = ConfigDict(extra="allow")
    
    # Layout (Tuner-Driven)
    orientation: Literal["horizontal", "vertical"] = "horizontal"
    spine_position: Literal["top", "middle", "bottom"] = "middle"
    node_width: int = Field(
        default=220,
        validation_alias=AliasChoices("node_width", "chip_width")
    )
    node_height: int = Field(
        default=90,
        validation_alias=AliasChoices("node_height", "chip_height")
    )
    lane_height: int = Field(
        default=140,
        validation_alias=AliasChoices("lane_height", "lane_spacing")
    )
    wave_spacing: int = 450
    container_padding: int = 40
    
    # Visual Physics
    dim_opacity: float = 0.15
    ghost_opacity: float = 0.75
    edge_width: float = 1.5
    
    # Toggles / Meta
    show_parallel_groups: bool = True
    show_teleology: bool = True
    auto_scroll: bool = True
    theme_variant: str = "cyberpunk_high_contrast"
    
    # System / Sidebar
    refresh_rate_ms: int = 1000
    sidebar_width: int = 360
    window_split_ratio: float = 0.25
    camera_padding: int = 100

    # Colors (Source of Truth)
    lane_colors: Dict[str, str] = Field(default_factory=dict)

# =============================================================================
# 7. INSPECTOR SCHEMAS
# =============================================================================

class CodexNodeStatus(str, Enum):
    """
    [ROLE]
    - Teleology: Enumerate inspector status outcomes for codex tree/files.
    - Mechanism: str-backed Enum used in inspector responses.
    - Guarantee: Stable identifiers: "ok", "warn", "fail", "skip".
    - Couples: UI badge coloring/state assumes these spellings.
    """
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"

class CodexTreeNodeSchema(BaseModel):
    """
    [ROLE]
    - Teleology: Represent a node in the codex filesystem tree for inspector UI.
    - Mechanism: Recursive-ish Pydantic model containing children as a list payload.
    - Guarantee: Provides path/name/type/status/error_count plus child listing.
    - Config: from_attributes=True enables dataclass/ORM coercion;
      serialization-required keeps the children default required on the wire.
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_serialization_defaults_required=True,
    )
    
    path: str
    name: str
    # node_type is closed: inspector.py constructs CodexTreeNode with only
    # 'dir' (lines 241, 259) and 'file' (line 289), never any other value.
    node_type: Literal["file", "dir"]
    status: CodexNodeStatus
    error_count: int
    file_type: str
    # Recursive field: must reference self for Pydantic v2 from_attributes serialization
    children: List['CodexTreeNodeSchema'] = Field(default_factory=list)

CodexTreeNodeSchema.model_rebuild()

class CodexTreeStatsSchema(BaseModel):
    """
    [ROLE]
    - Teleology: Pydantic schema for aggregate scan statistics returned alongside the tree.
    - Config: from_attributes=True enables dataclass coercion;
      serialization-required keeps the files_by_type / status_counts dict
      defaults required on the wire.
    """
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_serialization_defaults_required=True,
    )
    scanned_at: str
    total_files: int
    error_count: int
    files_by_type: Dict[str, int] = Field(default_factory=dict)
    status_counts: Dict[str, int] = Field(default_factory=dict)

class CodexTreeResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Wrapper response for /api/codex/tree combining the tree and stats.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    tree: CodexTreeNodeSchema
    stats: CodexTreeStatsSchema

class TreeSnapshotModeSchema(BaseModel):
    """
    [ROLE]
    - Teleology: Enumerate clipboard tree snapshot options for the toolbar dropdown.
    - Mechanism: Lightweight mode metadata passed from server to UI.
    """
    id: str
    name: str
    desc: str

class CodexFileDetailSchema(BaseModel):
    """
    [ROLE]
    - Teleology: Return detailed inspector view for a single codex file.
    - Mechanism: Pydantic model containing content, extracted tags, compliance errors, and doctrine enrichment.
    - Guarantee: Includes ast_tags, errors, structural summaries, and doctrine envelope for the UI hourglass.
    - Config: from_attributes=True enables dataclass/ORM coercion.
    """
    model_config = ConfigDict(from_attributes=True)

    path: str
    content: str
    ast_tags: Dict[str, str]
    contract_atoms: Dict[str, List[str]] = Field(default_factory=dict)
    errors: List[str]
    is_compliant: bool
    file_type: str
    classes: List[Dict[str, Any]]
    functions: List[Dict[str, Any]]

    # Compliance Gaps
    missing_module_tags: List[str] = Field(default_factory=list)
    classes_missing_role: List[str] = Field(default_factory=list)
    functions_missing_action: List[str] = Field(default_factory=list)

    # Doctrine Enrichment: mechanisms, concepts, principles, related files
    doctrine: Dict[str, Any] = Field(default_factory=lambda: {
        "mechanisms": [],
        "concepts": [],
        "principles": [],
        "related_files": [],
        "counts": {"mechanisms": 0, "concepts": 0, "principles": 0, "related_files": 0},
    })

    # Structural metadata
    internal_imports: List[str] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)


class DoctrineDetailSchema(BaseModel):
    """
    [ROLE]
    - Teleology: Carries the full payload for a single doctrine node (concept, mechanism, or principle)
      so the Inspector can open a drill-down drawer without additional roundtrips.
    - Mechanism: Thin pass-through of the projected dict from DoctrineEnrichmentService.get_doctrine_detail.
    """
    model_config = ConfigDict(extra="allow")

    kind: Literal["concept", "mechanism", "principle"]
    id: str
    title: str = ""
    statement: str = ""
    scope: str = ""
    status: str = ""
    tags: List[Any] = Field(default_factory=list)
    source_file: str = ""

class BatchReadRequest(BaseModel):
    """
    [ROLE]
    - Teleology: Request schema for batch-reading multiple codex file paths.
    - Mechanism: Pydantic request body model.
    - Guarantee: Provides a list of paths to read.
    """
    paths: List[str]

class BatchReadResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Response schema for batch-read inspector endpoint.
    - Mechanism: Pydantic response model wrapping file detail records.
    - Guarantee: files is a list of CodexFileDetailSchema.
    """
    files: List[CodexFileDetailSchema]

class DocSaveRequest(BaseModel):
    """
    [ROLE]
    - Teleology: Request schema for saving edited markdown doc content.
    - Mechanism: Pydantic request body model; server validates path is inside repo_root and ends in .md.
    - Guarantee: Provides repo-relative path and full replacement content.
    """
    path: str
    content: str

class PruneRequest(BaseModel):
    """
    [ROLE]
    - Teleology: Request schema for pruning run directories by id.
    - Mechanism: Pydantic request body model.
    - Guarantee: Provides run_ids list to attempt deletion.
    """
    run_ids: List[str]

class PruneResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Response schema for prune endpoint, separating deleted/protected/errors.
    - Mechanism: Pydantic response body model.
    - Guarantee: Categorizes outcomes into deleted/protected/errors lists.
    """
    deleted: List[str]
    protected: List[str]
    errors: List[str]

# =============================================================================
# 8. META SERVICE SCHEMAS
# =============================================================================

T = TypeVar("T")

class MetaToolMetadata(BaseModel):
    """
    [ROLE]
    - Teleology: Standardized header for all Meta tool responses.
    - Mechanism: Carries execution status, timestamps, and gate/warning signals.
    """
    status: Literal["success", "failure", "info"]
    timestamp: str
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    gate: Optional[str] = None
    message: Optional[str] = None

class MetaEnvelope(BaseModel, Generic[T]):
    """
    [ROLE]
    - Teleology: Generic wrapper for all Meta Service responses.
    - Mechanism: Separates protocol metadata from tool-specific payload (data).
    """
    metadata: MetaToolMetadata
    data: Optional[T] = None

# --- Apply Tool Models ---

class ApplyOperation(BaseModel):
    """
    [ROLE]
    - Teleology: Flexible dictionary container for a single file operation.
    - Note: Validation happens inside the tool via apply logic, not here.
    """
    model_config = ConfigDict(extra="allow") 

class ApplyPlan(BaseModel):
    """
    [ROLE]
    - Teleology: Container for a list of operations in an Apply request.
    """
    operations: List[Dict[str, Any]] # Using Dict to allow flexible op shapes

class MetaApplyRequest(BaseModel):
    """
    [ROLE]
    - Teleology: Request payload for the Apply tool (Preview/Commit).
    - Security: extra="forbid" blocks unknown arguments.
    """
    model_config = ConfigDict(extra="forbid")
    
    dry_run: bool = True
    validate_only: bool = False
    capture_diffs: bool = False
    plan: ApplyPlan

class ApplyFailure(BaseModel):
    """
    [ROLE]
    - Teleology: Structured error container for individual operation failures in a batch apply.
    - Mechanism: Captures the failing op index, payload, error message, and detail for client display.
    """
    op_index: int
    op: Dict[str, Any]
    error: str
    detail: str

class ApplyResultData(BaseModel):
    """
    [ROLE]
    - Teleology: The data payload returned by the Apply tool on success/failure.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    logs: List[str] = Field(default_factory=list)
    diffs: List[str] = Field(default_factory=list)
    failures: List[ApplyFailure] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    dry_run: bool
    patch_id: Optional[str] = None
    snapshot: Dict[str, Any] = Field(default_factory=dict)

MetaApplyResponse = MetaEnvelope[ApplyResultData]

# --- Observe Tool Models ---

class MetaObserveRequest(BaseModel):
    """
    [ROLE]
    - Teleology: Request payload for the Observe tool.
    - Security: Validates plan to prevent illegal write/dump arguments.
    """
    model_config = ConfigDict(extra="forbid")
    
    plan: Dict[str, Any]

    @model_validator(mode='after')
    def validate_security(self) -> 'MetaObserveRequest':
        """
        [ACTION]
        - Teleology: Enforce security boundaries for observe plans (prevent server-side dumps).
        - Fails: Raises ValueError if restricted keys are present.
        """
        if "groups" in self.plan or "dump_dir" in self.plan:
            raise ValueError("Security: 'groups' and 'dump_dir' are not allowed in server-side Observe requests.")
        return self

MetaObserveResponse = MetaEnvelope[Dict[str, Any]]

# --- Observe Session (grouped) API + telemetry contracts ----------------------

class ObserveTargetSchema(BaseModel):
    """
    [ROLE]
    - Teleology: Typed target selector for observe-session plans.
    - Mechanism: Mirrors observe standard target shape, with explicit scope/name rules.
    """
    file: str
    scope: Literal['full', 'function', 'class', 'imports', 'heading', 'line_range', 'outline'] = 'full'
    name: Optional[str] = None
    heading: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    notes: Optional[str] = None

    @model_validator(mode='after')
    def _validate_name_required(self) -> 'ObserveTargetSchema':
        if self.scope == 'heading':
            heading = (self.heading or self.name or "").strip()
            if not heading:
                raise ValueError("ObserveTargetSchema.heading or .name is required when scope is 'heading'.")
            self.heading = heading
            self.name = heading
        elif self.scope == 'line_range':
            if int(self.line_start or 0) <= 0 or int(self.line_end or 0) < int(self.line_start or 0):
                raise ValueError("ObserveTargetSchema.line_range requires positive line_start and line_end values.")
        elif self.scope in ('function', 'class') and not self.name:
            raise ValueError("ObserveTargetSchema.name is required when scope is 'function' or 'class'.")
        return self


class ObservePosture(str, Enum):
    """
    [ROLE]
    - Teleology: Enumerate the named observe postures used to configure bridge reasoning mode.
    - Ownership: Posture literal values consumed by ObserveSessionDraftRequest and plan templates.
    - Mutability: Immutable Enum definition.
    - Concurrency: Stateless enum; safe to read concurrently.
    """
    DIAGNOSTIC_PROBE = 'Diagnostic Probe'
    DECISION_CLOSURE = 'Decision Closure'
    LOGIC_SCAFFOLDING = 'Logic Scaffolding'
    EXPLORATORY_ARCHITECTURE = 'Exploratory Architecture'
    FIX_VALIDATION = 'Fix Validation'
    CURRENT_STATE_REPORT = 'Current State Report'
    AUTO = 'Auto'

class ObserveScope(str, Enum):
    """
    [ROLE]
    - Teleology: Enumerate observe breadth options (Auto/Focused/Broad) for draft requests.
    - Ownership: Scope literal values consumed by ObserveSessionDraftRequest.
    - Mutability: Immutable Enum definition.
    - Concurrency: Stateless enum; safe to read concurrently.
    """
    AUTO = 'Auto'
    FOCUSED = 'Focused'
    BROAD = 'Broad'

class ObserveGroupRole(str, Enum):

    """
    [ROLE]
    - Teleology: Declare join semantics for observe-session groups.
    - Mechanism: 'probe' groups read repo slices; 'synthesis'/'evaluation' consume upstream artifacts.
    """
    PROBE = 'probe'
    SYNTHESIS = 'synthesis'
    EVALUATION = 'evaluation'
    ADVISORY = 'advisory'


class ObserveGroupSchema(BaseModel):
    """
    [ROLE]
    - Teleology: A single node in the observe-session DAG.
    - Mechanism: depends_on expresses gating; role expresses join behavior.
    """
    label: str
    notes: Optional[str] = None
    role: ObserveGroupRole = ObserveGroupRole.PROBE
    situation: Optional[str] = None
    question: Optional[str] = None
    acceptance: Optional[str] = None
    output_contract: List[str] = Field(default_factory=list)
    response_surface: Optional[Union[str, Dict[str, Any]]] = None
    response_schema: Optional[Dict[str, Any]] = None
    json_only: bool = False
    external_research_allowed: bool = False
    provider: Optional[str] = None
    provider_config: Optional[Dict[str, Any]] = None
    standards: Dict[str, Any] = Field(default_factory=dict)
    downstream_consumer: Optional[str] = None
    context_files: List[str] = Field(default_factory=list)
    sibling_scope_roster: List[str] = Field(default_factory=list)
    incoming_queries: List[Dict[str, Any]] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)
    targets: List[ObserveTargetSchema] = Field(default_factory=list)
    raw_seed_refs: List[Union[str, Dict[str, Any]]] = Field(default_factory=list)
    raw_seed_queries: List[Dict[str, Any]] = Field(default_factory=list)
    raw_seed_docs: List[str] = Field(default_factory=list)
    principle_ids: List[str] = Field(default_factory=list)
    principle_slugs: List[str] = Field(default_factory=list)


class ObserveSessionPlan(BaseModel):
    """
    [ROLE]
    - Teleology: Canonical plan payload for observe-session execution.
    - Mechanism: Extends grouped observe shape with depends_on/role for DAG gating.
    - Note: dump_dir is accepted for compatibility but SHOULD be server-owned at runtime.
    """
    schema_version: str = "1.0"
    drafted_at: Optional[str] = None
    template_version: Optional[str] = None
    intended_posture: Optional[str] = None
    dump_dir: Optional[str] = None
    wait_notes: Optional[str] = None
    wait_notes_ref: Optional[str] = None
    prompt: Optional[str] = None
    notes: Optional[str] = None
    goal_question: Optional[str] = None
    success_criteria: Optional[str] = None
    context_files: List[str] = Field(default_factory=list)
    print_format: Literal['raw', 'python', 'json'] = 'python'
    print_shape: Literal['compact', 'preserve_shape'] = 'compact'
    campaign_id: Optional[str] = None
    round_id: Optional[str] = None
    round_index: Optional[int] = Field(default=None, ge=1)
    carry_forward_posture: Optional[str] = None
    parent_observe_id: Optional[str] = None
    cadence_posture_map: Dict[str, str] = Field(default_factory=dict)
    problem_text: Optional[str] = None
    result_note_path: Optional[str] = None
    cycle_dir: Optional[str] = None
    cycle_context_mode: Literal['off', 'minimal', 'full'] = 'minimal'
    raw_seed_family: Optional[str] = None
    standards_refs: List[str] = Field(default_factory=list)
    shard_packet_request: Optional[Dict[str, Any]] = None
    shard_packets: Optional[Dict[str, Any]] = None
    observe_enrichment: Optional[Dict[str, Any]] = None
    compression_profile_id: Optional[str] = None
    groups: List[ObserveGroupSchema]

    @model_validator(mode='after')
    def _validate_dag(self) -> 'ObserveSessionPlan':
        labels = [g.label for g in self.groups]
        if len(set(labels)) != len(labels):
            raise ValueError('ObserveSessionPlan.groups labels must be unique.')
        label_set = set(labels)
        for g in self.groups:
            for dep in g.depends_on:
                if dep not in label_set:
                    raise ValueError(f"ObserveSessionPlan: group '{g.label}' depends_on unknown label '{dep}'.")
                if dep == g.label:
                    raise ValueError(f"ObserveSessionPlan: group '{g.label}' cannot depend_on itself.")
        return self


class ObserveSessionIgniteRequest(BaseModel):
    """
    [ROLE]
    - Teleology: Request payload for igniting an observe-session.
    """
    model_config = ConfigDict(extra='forbid')

    plan_path: Optional[str] = None
    plan: Optional[ObserveSessionPlan] = None

    provider: Optional[str] = None
    timeout_s: float = 60.0
    sentence_count: Optional[int] = Field(default=None, ge=0)
    max_workers: Optional[int] = Field(default=None, ge=1)
    launch_profile: Literal['safe', 'experimental'] = 'experimental'
    problem_text: Optional[str] = None
    parent_observe_id: Optional[str] = None
    bridge_enabled: bool = True

    @model_validator(mode='after')
    def _validate_oneof(self) -> 'ObserveSessionIgniteRequest':
        has_path = self.plan_path is not None
        has_plan = self.plan is not None
        if has_path == has_plan:
            raise ValueError('Provide exactly one of {plan_path, plan}.')
        return self


class ObserveSessionDraftRequest(BaseModel):
    """
    [ROLE]
    - Teleology: Request payload for drafting an observe-session plan.
    """
    model_config = ConfigDict(extra='forbid')
    problem_text: str
    posture: ObservePosture = ObservePosture.DIAGNOSTIC_PROBE
    scope: ObserveScope = ObserveScope.AUTO
    include_tree: bool = True
    include_standards: bool = True
    template_id: Optional[str] = None
    source_paths: List[str] = Field(default_factory=list)
    continue_from: Optional[str] = None
    write_plan_to: Optional[str] = None


class ObserveSessionDraftResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Response payload for drafting an observe-session plan.
    """
    plan: ObserveSessionPlan
    plan_path: Optional[str] = None
    source_paths_loaded: List[str] = Field(default_factory=list)
    continuation_hint: Optional[str] = None


class ObserveSessionIgniteStatus(str, Enum):
    """
    [ROLE]
    - Teleology: Immediate ignition outcome (not the long-running state).
    """
    IGNITED = 'ignited'
    BUSY = 'busy'
    FAILED = 'failed'


class ObserveSessionState(str, Enum):
    """
    [ROLE]
    - Teleology: Long-running lifecycle state for the observe-session controller.
    """
    IDLE = 'idle'
    GENERATING = 'generating'
    DISPATCHING = 'dispatching'
    SYNTHESIZING = 'synthesizing'
    DONE = 'done'
    ERROR = 'error'
    ABORTED = 'aborted'


class ObserveRuntimeState(str, Enum):
    """
    [ROLE]
    - Teleology: Normalized runtime lifecycle state across observe-session and grouped-observe surfaces.
    """
    IDLE = 'idle'
    GENERATING = 'generating'
    DISPATCHING = 'dispatching'
    SYNTHESIZING = 'synthesizing'
    AWAITING_REVIEW = 'awaiting_review'
    COMPLETED = 'completed'
    ERROR = 'error'
    ABORTED = 'aborted'


class ObserveSessionIgniteResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Response body for POST /api/meta/observe/session/ignite.
    - Mechanism: Mirrors mission ignition pattern but for observe-session.
    """
    observe_id: Optional[str] = None
    status: ObserveSessionIgniteStatus
    state: ObserveSessionState
    telemetry_ws_path: str = '/ws/meta/observe/session'
    plan: Optional[ObserveSessionPlan] = None
    error: Optional[str] = None


class ObserveGroupPreview(BaseModel):
    """
    [ROLE]
    - Teleology: Carry per-group context size estimation and staleness indicator for the session preview UI.
    - Ownership: Group label, estimated context chars, file count, and staleness flag.
    - Mutability: Immutable once constructed.
    - Concurrency: Read-only value object; no shared mutable state.
    """
    label: str
    context_estimation_chars: int
    is_stale: bool
    file_count: int

class ObserveSessionPreviewResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Response body for POST /api/meta/observe/session/preview.
    """
    plan: ObserveSessionPlan
    total_groups: int
    is_valid: bool
    error: Optional[str] = None
    group_previews: List[ObserveGroupPreview] = Field(default_factory=list)
    total_context_estimation_chars: int = 0
    provider: Optional[str] = None
    
class ObserveSessionHistoryItem(BaseModel):
    """
    [ROLE]
    - Teleology: Summarize one past observe session for the history list view.
    - Ownership: observe_id, session_slug, timestamps, status, model, plan_hash, and parent linkage.
    - Mutability: Immutable once constructed.
    - Concurrency: Read-only value object; no shared mutable state.
    """
    observe_id: str
    session_slug: str
    generated_at: str
    status: str
    model: str
    plan_hash: str
    parent_observe_id: Optional[str] = None
    
class ObserveSessionHistoryResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Wrap the ordered list of ObserveSessionHistoryItem for the history endpoint.
    - Ownership: sessions list.
    - Mutability: Immutable once constructed.
    - Concurrency: Read-only value object; no shared mutable state.
    """
    sessions: List[ObserveSessionHistoryItem]


class ObserveSessionGroupStatus(BaseModel):
    """
    [ROLE]
    - Teleology: Structured status for one group node in the observe-session.
    """
    label: str
    role: ObserveGroupRole = ObserveGroupRole.PROBE
    depends_on: List[str] = Field(default_factory=list)
    status: Literal['pending', 'running', 'success', 'failure', 'skipped', 'aborted'] = 'pending'
    error: Optional[str] = None
    response_path: Optional[str] = None
    wave_index: int = 0
    retryable: bool = False
    retry_reason: Optional[str] = None
    dependencies_met: bool = True


class ObserveSessionStatusResponse(BaseModel):
    """
    [ROLE]
    - Teleology: Canonical pollable observe-status snapshot for the operator-facing runtime route.
    - Mechanism: Defines the canonical observe-session status shape and the compatibility-alias target for ObserveRuntimeStatusResponse.
    - When-needed: Open when runtime-status work mentions ObserveRuntimeStatusResponse and you need the authoritative field contract or alias migration surface.
    - Escalates-to: system/server/main.py; system/server/session.py
    """
    observe_id: Optional[str] = None
    kind: str = 'observe_session'
    session_slug: Optional[str] = None
    state: ObserveRuntimeState = ObserveRuntimeState.IDLE
    launch_profile: Optional[Literal['safe', 'experimental']] = None
    requested_workers: Optional[str] = None
    effective_workers: Optional[int] = None
    wave_index: int = 0
    wave_total: int = 0
    provider: Optional[str] = None
    provider_transport: Optional[str] = None
    latest_stable_artifact: Optional[str] = None
    status_authority: str = 'session'
    status_manifest: Optional[str] = None
    history_entry: Optional[str] = None
    error: Optional[str] = None
    cancel_requested_at: Optional[str] = None
    pid: Optional[int] = None
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    round_id: Optional[str] = None
    error_count: int = 0
    total_groups: int = 0
    completed_groups: int = 0
    progress: Dict[str, Any] = Field(default_factory=dict)
    can_continue: bool = False
    continue_mode: Optional[str] = None
    continue_reason: Optional[str] = None
    pending_group_labels: List[str] = Field(default_factory=list)
    retryable_group_labels: List[str] = Field(default_factory=list)
    launch_receipt: Dict[str, Any] = Field(default_factory=dict)
    launch_dispatch: Optional[str] = None
    continuation: Dict[str, Any] = Field(default_factory=dict)
    readback_state: Dict[str, Any] = Field(default_factory=dict)
    promoted_surface: Dict[str, Any] = Field(default_factory=dict)
    resume_surface: Dict[str, Any] = Field(default_factory=dict)
    lineage: Dict[str, Any] = Field(default_factory=dict)
    groups: List[ObserveSessionGroupStatus] = Field(default_factory=list)
    artifacts: Dict[str, Any] = Field(default_factory=dict)  # paths plus additive structured runtime metadata

    @field_validator("state", mode="before")
    @classmethod
    def _coerce_legacy_session_state(cls, value: object) -> object:
        if isinstance(value, ObserveSessionState):
            token = value.value
        else:
            token = str(value or "").strip().lower()
        if token == "done":
            return ObserveRuntimeState.COMPLETED
        return token or ObserveRuntimeState.IDLE


# Compatibility aliases while runtime consumers migrate onto the canonical
# observe-session-shaped contract.
ObserveRuntimeGroupStatus = ObserveSessionGroupStatus
ObserveRuntimeStatusResponse = ObserveSessionStatusResponse


# --- Telemetry (WebSocket) ----------------------------------------------------

class ObserveSessionTelemetryBase(BaseModel):
    """
    [ROLE]
    - Teleology: Uniform envelope for observe-session WS events.
    - Mechanism: Discriminated union via 'type' for stable client handling.
    """
    stream: Literal['observe_session'] = 'observe_session'
    observe_id: str
    seq: int
    timestamp_epoch_s: float
    type: str


class ObserveSessionTelemetryState(ObserveSessionTelemetryBase):
    """
    [ROLE]
    - Teleology: Carry observe-session lifecycle state transitions over the WebSocket stream.
    - Ownership: State value and optional human-readable message.
    - Mutability: Immutable once emitted.
    - Concurrency: Read-only WS event payload; no shared mutable state.
    """
    type: Literal['state'] = 'state'
    state: ObserveSessionState
    message: Optional[str] = None


class ObserveSessionTelemetryGroup(ObserveSessionTelemetryBase):
    """
    [ROLE]
    - Teleology: Carry per-group status updates (running/success/failure) over the WebSocket stream.
    - Ownership: Group label, status, response path, and optional error.
    - Mutability: Immutable once emitted.
    - Concurrency: Read-only WS event payload; no shared mutable state.
    """
    type: Literal['group'] = 'group'
    group_label: str
    group_status: Literal['pending', 'running', 'success', 'failure', 'skipped', 'aborted']
    response_path: Optional[str] = None
    error: Optional[str] = None


class ObserveSessionTelemetryArtifact(ObserveSessionTelemetryBase):
    """
    [ROLE]
    - Teleology: Carry artifact availability notifications (dump/response/combined/synthesis) over the WebSocket stream.
    - Ownership: Artifact kind discriminator and path.
    - Mutability: Immutable once emitted.
    - Concurrency: Read-only WS event payload; no shared mutable state.
    """
    type: Literal['artifact'] = 'artifact'
    kind: Literal['dump', 'response', 'combined', 'combined_json', 'synthesis', 'evaluation', 'problem']
    path: str


ObserveSessionTelemetryEvent = Annotated[
    Union[
        ObserveSessionTelemetryState,
        ObserveSessionTelemetryGroup,
        ObserveSessionTelemetryArtifact,
    ],
    Field(discriminator='type'),
]

# --- Builder Tool Models ---

class MetaBuildRequest(BaseModel):
    """
    [ROLE]
    - Teleology: Request payload for the Builder tool (Hologram generation).
    """
    model_config = ConfigDict(extra="forbid")
    
    config: Dict[str, Any] = Field(default_factory=dict)

class BuildPhaseSchema(BaseModel):
    """
    [ROLE]
    - Teleology: Represent a single build phase with its artifact count and stats.
    """
    name: str
    artifacts_written: int
    stats: Dict[str, int] = Field(default_factory=dict)

class BuildSummarySchema(BaseModel):
    """
    [ROLE]
    - Teleology: Typed schema for the builder tool's data payload.
    """
    generated_at: str
    root: str
    artifacts_written: int
    warnings: List[str] = Field(default_factory=list)
    stats: Dict[str, int] = Field(default_factory=dict)
    phases: List[BuildPhaseSchema] = Field(default_factory=list)
    phase_artifacts: Dict[str, List[str]] = Field(default_factory=dict)

MetaBuildResponse = MetaEnvelope[BuildSummarySchema]

# --- Patcher Tool Models ---

class MetaPatchRequest(BaseModel):
    """
    [ROLE]
    - Teleology: Request payload for the Patcher tool.
    """
    model_config = ConfigDict(extra="forbid")
    
    dry_run: bool = True
    plan: Dict[str, Any]

class MetaPatchResultData(BaseModel):
    """
    [ROLE]
    - Teleology: The data payload returned by the Patcher tool.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    logs: str
    dry_run: bool
    touched_files: List[str] = Field(default_factory=list)
    patch_id: Optional[str] = None

MetaPatchResponse = MetaEnvelope[MetaPatchResultData]


class PatchDiff(BaseModel):
    """
    [ROLE]
    - Teleology: Carry a single file's unified diff text for patch record display.
    - Ownership: File path and the unified diff string produced by the patcher tool.
    - Mutability: Immutable once constructed.
    - Concurrency: Read-only value object; no shared mutable state.
    """
    path: str
    unified_diff: str


class PatchRecordListItem(BaseModel):
    """
    [ROLE]
    - Teleology: Provide a lightweight summary of a persisted patch record for list display.
    - Ownership: patch_id, timestamps, tool/mode/status, touched file count, and optional summary.
    - Mutability: Immutable once constructed.
    - Concurrency: Read-only value object; no shared mutable state.
    """
    patch_id: str
    timestamp: str
    tool: str
    mode: str
    status: str
    touched_files_count: int = 0
    summary: Optional[str] = None


class PatchRecord(BaseModel):
    """
    [ROLE]
    - Teleology: Carry the full persisted patch record including plan, diffs, logs, and file touch list.
    - Ownership: patch_id, plan, diffs, touched files, warnings, failures, and truncation flags.
    - Mutability: Immutable once constructed.
    - Concurrency: Read-only value object; no shared mutable state.
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    patch_id: str
    timestamp: str
    tool: str
    mode: str
    status: str
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    failures: List[Dict[str, Any]] = Field(default_factory=list)
    plan: Dict[str, Any] = Field(default_factory=dict)
    touched_files: List[str] = Field(default_factory=list)
    touched_files_source: Optional[str] = None
    diffs: List[PatchDiff] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)
    truncated: Dict[str, bool] = Field(default_factory=dict)
    snapshot: Dict[str, Any] = Field(default_factory=dict)

# ── V2 Run Holographic Schemas ──────────────────────────────────────────────

class LatestRunSchema(BaseModel):
    """
    [ROLE]
    - Teleology: Identify the most recent run for Control Room targeting.
    """
    run_id: str
    timestamp: float
    is_complete: bool
    hologram_v2_exists: bool

class RunHologramStatusSchema(BaseModel):
    """
    [ROLE]
    - Teleology: Report holographic availability and version for a specific run.
    """
    run_id: str
    exists: bool
    schema_version: Optional[str] = None
    generated_at: Optional[str] = None
    tool_file_count: int = 0

class RunHologramBatchStatusRequest(BaseModel):
    """
    [ROLE]
    - Teleology: Request holographic status for multiple runs in a single call.
    """
    run_ids: List[str]

# ── Regrade Schemas ─────────────────────────────────────────────────────────

class RegradeResult(BaseModel):
    """
    [ROLE]
    - Teleology: Return the result of regrading a run under the current grading policy.
    - Mechanism: Contains both old and new grade for transparency.
    """
    run_id: str
    grade: Literal["green", "amber", "red"]
    grade_reason: str
    original_grade: str
    regraded_at: str

class RegradeBatchRequest(BaseModel):
    """
    [ROLE]
    - Teleology: Request regrading for multiple runs in a single call.
    """
    run_ids: List[str]
