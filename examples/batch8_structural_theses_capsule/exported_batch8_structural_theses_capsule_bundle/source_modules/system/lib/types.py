"""
[PURPOSE]
- Teleology: Provide the canonical, shared type contracts for the AI Workflow runtime (nodes, events, and validation).
- Mechanism: Define Enums, TypedDict contracts, and dataclasses used across system/core, system/server, and tools.

[INTERFACE]
- Reads: Imported by runtime components (e.g., system.core.*, system.server.*, tools.*).
- Writes: No direct I/O; exposes type definitions only.
- Fails: Import-time errors only (e.g., missing typing_extensions on older Python).

[FLOW]
- Define core enums and lane laws.
- Define configuration and artifact envelope contracts.
- Define canonical dataclasses for nodes, issues, and event stream payloads.

[DEPENDENCIES]
- Python stdlib: dataclasses, enum, typing, copy.
- Optional: typing_extensions.NotRequired for Python versions lacking typing.NotRequired.

[CONSTRAINTS]
- Must remain side-effect free (no runtime I/O).
- Types must be stable and broadly compatible across Python versions in this repo.
- When-needed: Open when a caller needs the canonical runtime type contracts for nodes, artifact envelopes, or event payloads instead of inferring shape from downstream consumers.
- Escalates-to: system/lib/utils.py::to_jsonable; codex/standards/std_python.py; system/lib/workstream_scaffold.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations
import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union, Literal

try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired

# --- ENUMS ---

class NodeType(str, Enum):
    """
    [ROLE]
    - Teleology: Define the canonical node "type" discriminator for the codex.
    - Mechanism: Enum values constrain node.type to a small legal set.
    """
    TOOL = "tool"
    REASONING = "reasoning"

class NodeRole(str, Enum):
    """
    [ROLE]
    - Teleology: Provide UI-facing role labels for nodes (coloring/icons), not filesystem grouping.
    - Mechanism: Enum values constrain node.meta.role (or derived role) to a stable set.
    """
    # Used purely for UI coloring/icons, NOT grouping.
    EXECUTIVE = "executive"
    DIRECTOR = "director"
    INTEGRITY = "integrity"
    DECIDE = "decide"
    MINER = "miner"
    CRITIC = "critic"
    WORKER = "worker"
    PREDICT = "predict"
    ORIENT = "orient"
    SOURCE = "source"
    TOOL = "tool"
    GHOST = "ghost"

class RunMode(str, Enum):
    """
    [ROLE]
    - Teleology: Describe how an execution run was initiated.
    - Mechanism: Enum values constrain run.mode in runtime contexts and logs.
    """
    FRESH = "fresh"
    RESUME = "resume"
    FORK = "fork"

class ExecutionMode(str, Enum):
    """
    [ROLE]
    - Teleology: Distinguish execution contexts (e.g., live runtime vs laboratory runs).
    - Mechanism: Enum values constrain execution_mode where used by engine/governance.
    """
    RUNTIME = "runtime"
    LAB = "lab"

class StepStatus(str, Enum):
    """
    [ROLE]
    - Teleology: Standardize step lifecycle states for execution and artifact metadata.
    - Mechanism: Enum values constrain status fields across events and artifact envelopes.
    """
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    NOT_STARTED = "not_started"
    SKIPPED = "skipped"
    LOADED = "loaded"

# --- LAWS ---

VALID_LANES = frozenset({
    "SPINE",
    "MACRO",
    "STOCK",
    "ETF",
    "POLYMARKET",
    "NEWS",
    "STOCKGRID",
    "CALCULATOR"
})

# --- CONTRACTS ---

TOOL_METADATA_SCHEMA_VERSION = "1.0"

class ExecutionConfig(TypedDict):
    """
    [ROLE]
    - Teleology: Specify execution parameters for a node run (timeouts, retries, caching, tool allowlist).
    - Mechanism: TypedDict constrains the expected keys and value types for node.execution.
    """
    timeout: float
    retries: int
    cache_policy: str
    tools: NotRequired[List[str]]

class DiagnosticsBlock(TypedDict, total=False):
    """
    [ROLE]
    - Teleology: Canonical diagnostics block for tool metadata.
    - Mechanism: TypedDict contract for consistent row accounting and warning emission.
    """
    input_rows: int
    output_rows: int
    dropped_rows: int
    warnings: List[str]

class ToolMetadataContract(TypedDict, total=False):
    """
    [ROLE]
    - Teleology: Define canonical additive metadata keys for tool artifacts.
    - Mechanism: TypedDict contract consumed by tool emitters and engine injection.
    """
    tool: str
    schema_version: str
    data_schema_version: str
    config_ref: Optional[str]
    merged_hash: Optional[str]
    override_keys: List[str]
    timestamp_iso: str
    timestamp_epoch_s: float
    status: str
    items_count: int
    diagnostics: DiagnosticsBlock

class ArtifactMetadata(TypedDict, total=False):
    """
    [ROLE]
    - Teleology: Provide standard metadata describing an artifact's generation and provenance.
    - Mechanism: TypedDict (total=False) allows optional fields while constraining their types.
    """
    status: StepStatus
    error: Optional[str]
    items_count: int
    timestamp: Union[float, str]
    timestamp_iso: str
    timestamp_epoch_s: float
    schema_version: str
    data_schema_version: str
    config_ref: Optional[str]
    merged_hash: Optional[str]
    override_keys: List[str]
    legend: Optional[Dict[str, Any]]
    as_of: Optional[str]
    run_id: Optional[str]
    diagnostics: DiagnosticsBlock

class ArtifactEnvelope(TypedDict):
    """
    [ROLE]
    - Teleology: Standardize the JSON envelope used to persist artifacts (metadata + payload).
    - Mechanism: TypedDict constrains artifact storage shape across lanes.
    """
    metadata: ArtifactMetadata
    data: Any

class RunSummary(TypedDict):
    """
    [ROLE]
    - Teleology: Provide a finalized 'report card' for a completed run.
    - Mechanism: Generated by Engine at end of run; consumed by API for history.
    """
    run_id: str
    timestamp: float
    grade: str  # 'GREEN', 'AMBER', 'RED'
    grade_reason: Optional[str]
    node_outcomes: Dict[str, str]
    duration_seconds: float

DEFAULT_EXECUTION_CONFIG: ExecutionConfig = {
    "timeout": 300.0,
    "retries": 1,
    "cache_policy": "standard",
    "tools": [],
}

# --- DATACLASSES ---

@dataclass(frozen=True)
class CodexNode:
    """
    [ROLE]
    - Teleology: Represent a fully-parsed, canonical node instance used by governance and execution.
    - Mechanism: Frozen dataclass with explicit fields for identity, metadata, config, and execution policy.
    - When-needed: Open when a runtime or governance surface needs the canonical in-memory node contract rather than a serialized artifact or UI projection.
    - Escalates-to: system/lib/utils.py::to_jsonable; codex/standards/std_python.py
    """
    id: str
    type: NodeType

    # Provenance & Grouping (New Physics)
    group: str = field(default="", hash=False)
    lane: str = field(default="SPINE", hash=False)

    # Logic (Identity Affecting)
    instruction: str = ""
    dependencies: Tuple[str, ...] = field(default_factory=tuple, hash=False)

    # Metadata (Inert)
    teleology: str = ""
    mechanism: str = ""
    expectation: str = field(default="", hash=False)

    # Data Contracts
    meta: Dict[str, Any] = field(default_factory=dict, hash=False)

    # Execution Ontology (Phase 2 — hash=False; semantic hash is handled by system.lib.hashing)
    output_schema: Literal[
        "text",
        "json",
        "isomorphic_cp1",
        "isomorphic_cp2",
        "schema_realized_hindsight_brief",
        "schema_cp2_critique",
    ] = field(
        default="text", hash=False
    )
    boundary: str = field(default="", hash=False)
    routing_class: str = field(default="", hash=False)

    # Architecture
    is_artifact: bool = field(default=False, hash=False)
    platform: str = "chatgpt"

    # Config
    config: Dict[str, Any] = field(default_factory=dict, hash=False)
    config_ref: Optional[str] = field(default=None, hash=False)
    inline_overrides: Optional[Dict[str, Any]] = field(default=None, hash=False)
    merged_hash: Optional[str] = field(default=None, hash=False)

    # Use deepcopy to ensure isolation of mutable lists (like tools)
    execution: ExecutionConfig = field(
        default_factory=lambda: copy.deepcopy(DEFAULT_EXECUTION_CONFIG),
        hash=False,
    )

    def __post_init__(self):
        """
        [ACTION]
        - Teleology: Normalize mutable dependency input into the frozen `CodexNode` contract.
        - Mechanism: Converts list-valued `dependencies` into an immutable tuple after dataclass initialization.
        - Reads: The just-initialized `dependencies` field.
        - Guarantee: Stored dependencies are tuple-backed when callers passed a list.
        - Fails: None.
        - When-needed: Open when a caller passes mutable dependency lists into `CodexNode` and you need to confirm how the frozen contract normalizes them.
        - Escalates-to: system/lib/types.py::CodexNode; system/lib/utils.py::to_jsonable
        """
        if isinstance(self.dependencies, list):
            object.__setattr__(self, "dependencies", tuple(self.dependencies))

@dataclass
class ValidationIssue:
    """
    [ROLE]
    - Teleology: Represent a single validation finding produced by governance or tooling.
    - Mechanism: Simple dataclass to carry node context, severity, message, and optional field.
    """
    node_id: str
    severity: str
    message: str
    field: Optional[str] = None

# --- EVENTS ---

@dataclass(frozen=True)
class CanonicalEvent:
    """
    [ROLE]
    - Teleology: Provide a base type for all event stream payloads emitted by the system.
    - Mechanism: Frozen dataclass carrying identity and ordering.
    """
    timestamp: float
    run_id: str
    seq: int

@dataclass(frozen=True)
class RunStartEvent(CanonicalEvent):
    """
    [ROLE]
    - Teleology: Signal the start of a run and capture its initial DAG structure and mode.
    - Mechanism: Event payload used by logging/observability and downstream consumers.
    """
    # run_id inherited
    mode: RunMode
    dag_structure: Dict[str, List[str]]

@dataclass(frozen=True)
class WaveStartEvent(CanonicalEvent):
    """
    [ROLE]
    - Teleology: Signal the start of a wave (parallelizable batch) within a run.
    - Mechanism: Carries wave index and the node IDs scheduled in that wave.
    """
    wave_index: int
    node_ids: List[str]

@dataclass(frozen=True)
class WaveEndEvent(CanonicalEvent):
    """
    [ROLE]
    - Teleology: Signal the completion of a wave.
    - Mechanism: Used by Frontend to trigger auto-pan logic.
    """
    wave_index: int
    status: StepStatus

@dataclass(frozen=True)
class StepPendingEvent(CanonicalEvent):
    """
    [ROLE]
    - Teleology: Signal that a node is scheduled for execution in the current wave but hasn't started threads yet.
    - Mechanism: Emitted before task submission.
    """
    node_id: str

@dataclass(frozen=True)
class StepStartEvent(CanonicalEvent):
    """
    [ROLE]
    - Teleology: Signal the start of execution for a specific node step.
    - Mechanism: Minimal event payload keyed by node_id.
    """
    node_id: str

@dataclass(frozen=True)
class StepEndEvent(CanonicalEvent):
    """
    [ROLE]
    - Teleology: Signal the end of execution for a specific node step, including outcome and duration.
    - Mechanism: Event payload keyed by node_id with status and timing information.
    """
    node_id: str
    status: StepStatus
    duration: float

@dataclass(frozen=True)
class RunEndEvent(CanonicalEvent):
    """
    [ROLE]
    - Teleology: Signal completion of a run with its final status.
    - Mechanism: Event payload for run-level observability.
    """
    status: StepStatus

@dataclass(frozen=True)
class LogEvent(CanonicalEvent):
    """
    [ROLE]
    - Teleology: Standardize structured log emission for UI and diagnostics.
    - Mechanism: Carries level, message, and source attribution.
    """
    level: str
    message: str
    source: str

@dataclass(frozen=True)
class BridgeStartEvent(CanonicalEvent):
    """
    [ROLE]
    - Teleology: Mark the beginning of a bridge-gated action for a node (e.g., browser automation).
    - Mechanism: Event payload keyed by node_id for sequencing and UI status.
    """
    node_id: str

@dataclass(frozen=True)
class BridgeEndEvent(CanonicalEvent):
    """
    [ROLE]
    - Teleology: Mark the end of a bridge-gated action for a node.
    - Mechanism: Event payload keyed by node_id for sequencing and UI status.
    """
    node_id: str

@dataclass(frozen=True)
class CompletedAtStartEvent(CanonicalEvent):
    """
    [ROLE]
    - Teleology: Signal nodes that were skipped/loaded immediately upon Resume/Fork ignition.
    - Mechanism: Allows UI to paint 'Green' state instantly without replaying history.
    - When-needed: Open when a Resume or Fork ignition sequence needs the canonical event contract for `CompletedAtStartEvent` to understand how pre-completed nodes are communicated to the UI.
    - Escalates-to: system/lib/types.py::CanonicalEvent; system/server/session.py
    """
    completed_ids: List[str]
    severed_ids: List[str]
    intent: str

@dataclass(frozen=True)
class ContainerStateEvent(CanonicalEvent):
    """
    [ROLE]
    - Teleology: Signal aggregate status change for a group (container).
    - Mechanism: Used by UI to style container borders (dotted/solid/color).
    """
    group: str
    status: StepStatus

class DuplicateIDError(Exception):
    """
    [ROLE]
    - Teleology: Provide a dedicated exception type for duplicate node ID declarations.
    - Mechanism: Raised by loaders/validators when two nodes declare the same ID.
    """
    pass
