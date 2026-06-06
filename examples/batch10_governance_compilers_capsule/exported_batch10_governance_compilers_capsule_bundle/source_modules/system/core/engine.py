"""
[PURPOSE]
- Teleology: The "God Mode" Run Orchestrator. Executes the Codex DAG.
- Mechanism: Load Universe (PhysicalLoader) -> Compute Waves (Governance) -> Execute Waves (ThreadPoolExecutor) -> Persist artifacts/manifests on disk.
- Strictness: High. Enforces cache hygiene and topology rules.

[INTERFACE]
- Exports: GodModeEngine, LogicalFailure
- Inputs: run_id, targets, execution_mode
- Outputs: Artifacts in `state/runs/<run_id>/artifacts/`

[FLOW]
- Initialization: Resolve paths; create or resume the run directory; attach logger.
- Runtime: Load nodes; resolve execution scope; optional fork seeding; compute waves; execute; emit events; persist artifacts.
- When-needed: Open when a task is about run execution, artifact emission, horizon handling, or lifecycle behavior inside the core runtime loop.
- Escalates-to: system/core/loader.py::PhysicalLoader.load_all_nodes; system/core/governance.py::compute_waves; system/core/forensics.py::reconstruct_run_state
- Navigation-group: system_core

[DEPENDENCIES]
- system.core.loader.PhysicalLoader: hydrate_graph (node loading)
- system.core.bridge.Bridge: ask_ai (LLM queries)
- standard_lib.concurrent.futures: ThreadPoolExecutor (parallel execution)
- standard_lib.importlib: dynamic_module_loading (tool execution)
- config.master_config.json: execution.max_workers (concurrency limit)
- data.state/runs: artifact_io (input/output persistence)

[CONSTRAINTS]
- Atomicity: Artifact and manifest writes are atomic (write temp -> close -> rename). Partial artifacts are forbidden.
- Determinism: Completion identity uses a stable hash over whitelisted logic fields; scheduling must not affect hashes.
- Must not mutate Codex node logic at runtime; only write artifacts/manifests under the run directory.
- Fork semantics must obey seeding intent (ITERATION / LIVE_AUDIT / HISTORICAL_AUDIT).
- Shutdown is non-destructive: close bridge resources without terminating the browser by default.

"""

import json
import logging
import time
import hashlib
import shutil
import concurrent.futures
import importlib
import threading
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dataclasses import replace
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from zoneinfo import ZoneInfo

from system.lib.utils import resolve_value as _rv, resolve_runs_dir as _resolve_runs_dir_canonical
from system.lib.hashing import hash_node
from system.lib import git_client as _git_client

from system.lib.types import (
    CodexNode,
    NodeType,
    RunMode,
    ExecutionMode,
    StepStatus,
    RunStartEvent,
    RunEndEvent,
    WaveStartEvent,
    WaveEndEvent,
    StepStartEvent,
    StepEndEvent,
    StepPendingEvent,
    CompletedAtStartEvent,
    ContainerStateEvent,
    LogEvent,
    BridgeStartEvent,
    BridgeEndEvent,
    TOOL_METADATA_SCHEMA_VERSION,
)
from system.core.loader import PhysicalLoader
from system.core.bridge import Bridge
from system.core.governance import compute_waves
from system.lib.artifacts import load_artifact
from system.lib.observer_report import generate_observation_report
from system.lib.run_compare import combined_prices as _combined_run_prices
from system.lib.bridge_routes import merge_bridge_config_with_route
from system.lib.schema_validator import (
    ValidationResult,
    validate_cp1,
    validate_cp2,
    validate_oracle_cp2_meta,
    validate_cp2_critique,
    validate_cross_corr_v1,
    validate_cross_corr_v2,
    validate_golden_ids,
    validate_prediction_reconciliation,
    validate_realized_hindsight_brief,
)
from system.lib.lab_contract_audit import compute_lab_contract_audit
from system.lib.dossiers import list_dossier_paths
from system.lib.feed_compression import compress_reasoning_feed_envelope
from system.lib.feed_quality import collect_artifact_qualities, quality_grade_override

_COMPACT_RUN_SNAPSHOT_FILE = "run_snapshot_compact.json"
_COMPACT_RUN_SNAPSHOT_TMP = "run_snapshot_compact.tmp"
_INSTRUCTION_CONTRACT_RE = re.compile(r"\[CONTRACT:\s*([^\]]+)\]", re.IGNORECASE)
_CONTRACT_BLOCK_RE = re.compile(
    r"\[CONTRACT:\s*([^\]]+)\]\s*(.*?)\s*\[/CONTRACT\]",
    re.IGNORECASE | re.DOTALL,
)
_RUN_CONTRACTS_DIR = "contracts"
_RUN_CONTRACTS_FILE = "contracts_used_combined.json"
_RUN_CONTRACTS_TMP = "contracts_used_combined.tmp"
_OUTPUT_SCHEMA_CONTRACTS = {
    "isomorphic_cp1": "schema_cp1.json",
    "isomorphic_cp2": "schema_cp2.json",
    "schema_prediction_reconciliation": "schema_prediction_reconciliation.json",
    "schema_realized_hindsight_brief": "schema_realized_hindsight_brief.json",
    "schema_cp2_critique": "schema_cp2_critique.json",
}
_STRUCTURED_JSON_OUTPUT_SCHEMAS = frozenset(_OUTPUT_SCHEMA_CONTRACTS.keys()) | {"json"}
_CANONICAL_ARTIFACT_ALIASES = {
    "oracle_truth_diff_equity": "prediction_reconciliation",
    "oracle_truth_map": "realized_hindsight_brief",
    "oracle_attribution_map": "cp2_critique",
    "oracle_cp2_emitter": "ideal_cp2",
}

class LogicalFailure(Exception):
    """
    [ROLE]
    - Teleology: Signal a semantic/contract failure (logic invalid) even when execution did not crash.
    - Mechanism: Raised when invariants are violated (e.g., required seeded feeds missing).
    - Ownership: Created/raised by the engine; handled by callers as a control-flow exception.
    - Mutability: Immutable exception payload; carries only message/context.
    - Concurrency: Safe to raise from worker threads; does not touch shared state.
    - Scope: Used to fail fast on non-recoverable provenance/history violations.
    
    """
    pass


class NodeExecutionFailure(Exception):
    """
    [ROLE]
    - Teleology: Mark a run-level failure caused by a specific node reaching a terminal error state.
    - Mechanism: Wraps the original node exception so the run loop can distinguish expected node failures
      from actual engine crashes.
    - Ownership: Raised by the engine run loop after worker completion; handled inside GodModeEngine.run().
    - Mutability: Immutable after construction aside from attached cause traceback.
    - Concurrency: Raised on the coordinator thread only.

    """

    def __init__(self, node_id: str, cause: Exception) -> None:
        self.node_id = node_id
        self.cause = cause
        super().__init__(f"Node {node_id} failed: {cause}")

class GodModeEngine:
    """
    [ROLE]
    - Teleology: Runtime Kernel for a single Codex execution run.
    - Mechanism: Loads nodes, computes waves, executes nodes concurrently, writes artifacts, and emits events.
    - Ownership: Owns the run directory, run logger, and per-run in-memory state; does not own the global browser process.
    - Mutability: Mutates run state on disk and internal runtime bookkeeping; does not mutate Codex node definitions.
    - Concurrency: Executes independent nodes concurrently via ThreadPoolExecutor; serializes shared bookkeeping/log emission where required.
    - Guarantees: Deterministic hashing for completion checks; atomic artifact writes; seeding manifest recorded for forks.
    - When-needed: Open when a caller needs the run-level owner for execution, lifecycle, artifact persistence, or stop/shutdown semantics rather than an isolated helper.
    - Escalates-to: system/core/loader.py::PhysicalLoader.load_all_nodes; system/core/governance.py::compute_waves; system/core/bridge.py
    
    """
    
    @staticmethod
    def resolve_horizon(policy: Optional[str] = None, now: Optional[datetime] = None) -> Dict[str, str]:
        """
        [ACTION]
        - Teleology: Resolve a human-friendly horizon policy into a concrete UTC target time.
        - Mechanism: Map policy strings ('next_us_close', '24h', '48h', ISO datetime) to a target timestamp.
        - Guarantee: Returns dict with 'policy', 'target_time' (ISO UTC), 'target_time_et' (ISO ET), 'horizon_label'.
        - Fails: ValueError on unparseable ISO datetime.
        - When-needed: Open when a run or audit path needs to translate `next_us_close`, fixed-hour windows, or ISO timestamps into persisted horizon metadata.
        - Escalates-to: system/core/forensics.py::reconstruct_run_state; system/core/bridge.py
        """
        ET = ZoneInfo("America/New_York")
        if now is None:
            now = datetime.now(timezone.utc)
        now_et = now.astimezone(ET)
        effective = policy or "next_us_close"

        if effective == "next_us_close":
            # Next NYSE close: 16:00 ET on the next business day (Mon-Fri)
            close_today = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
            if now_et < close_today and now_et.weekday() < 5:
                target_et = close_today
            else:
                # Roll forward to next business day
                target_et = close_today + timedelta(days=1)
                while target_et.weekday() >= 5:  # Skip Sat/Sun
                    target_et += timedelta(days=1)
            target_utc = target_et.astimezone(timezone.utc)
            label = target_et.strftime("Next US Market Close (%a %b %d, 4:00 PM ET)")

        elif effective == "24h":
            target_utc = now + timedelta(hours=24)
            target_et = target_utc.astimezone(ET)
            label = target_et.strftime("24h from now (%a %b %d, %I:%M %p ET)")

        elif effective == "48h":
            target_utc = now + timedelta(hours=48)
            target_et = target_utc.astimezone(ET)
            label = target_et.strftime("48h from now (%a %b %d, %I:%M %p ET)")

        else:
            # Assume ISO datetime
            try:
                parsed = datetime.fromisoformat(effective)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                target_utc = parsed.astimezone(timezone.utc)
                target_et = target_utc.astimezone(ET)
                label = target_et.strftime("Custom target (%a %b %d, %I:%M %p ET)")
            except (ValueError, TypeError) as e:
                raise ValueError(f"Cannot parse horizon '{effective}' as ISO datetime: {e}")

        return {
            "policy": effective,
            "target_time": target_utc.isoformat(),
            "target_time_et": target_et.isoformat(),
            "horizon_label": label,
        }

    def __init__(
        self,
        run_id: str,
        run_mode: RunMode = RunMode.FRESH,
        execution_mode: ExecutionMode = ExecutionMode.RUNTIME,
        source_run_id: Optional[str] = None,
        feed_source_run_id: Optional[str] = None,
        subject_group: str = "lab",
        root_dir: str = ".",
        loader: Optional[PhysicalLoader] = None,
        emit: Optional[callable] = None,
        horizon: Optional[str] = None,
        time_anchor: Optional[str] = None,
        oracle_subject_run_dir: Optional[str] = None,
        oracle_truth_run_dir: Optional[str] = None,
        force_load_stale_feeds: bool = False,
    ):
        """
        - When-needed: Open when inspecting how `subject_group` controls topology scoping, mission naming, or universe partitioning inside a GodModeEngine run.
        """
        self.run_id = run_id
        self.run_mode = run_mode
        self.execution_mode = execution_mode
        self.source_run_id = source_run_id
        self.feed_source_run_id = feed_source_run_id
        self.subject_group = subject_group
        self._force_load_stale_feeds = bool(force_load_stale_feeds)

        self._emit_fn = emit
        
        # Thread-safe Kill Switch & Sequencing
        self._stop_event = threading.Event()
        self._seq_lock = threading.Lock()
        self._event_seq = 0
        self._start_time = 0.0
        # Stable per-run tool anchor used for runtime.time_anchor/as_of injection.
        self._run_anchor_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        explicit_anchor_time: Optional[datetime] = None
        if time_anchor:
            explicit_anchor_time = self._parse_iso_utc(str(time_anchor))
            self._run_anchor_iso = explicit_anchor_time.replace(microsecond=0).isoformat()
        # [C6] Routing guard state — carried from parent ignition payload.
        self._subgraph_depth: int = 0
        self._failed_targets_routed: List[str] = []
        
        # 1. Config & Paths
        self.root_dir = Path(root_dir).resolve()
        self.logger = logging.getLogger(f"engine.{run_id}")
        
        # Load Global Config
        try:
            with open(self.root_dir / "master_config.json", "r") as f:
                self.config = json.load(f)
        except Exception:
            self.config = {}

        # Resolve Paths
        runs_dir = _resolve_runs_dir_canonical(
            self.root_dir,
            self.config.get("paths", {}).get("runs_dir"),
        )
        self.run_dir = runs_dir / self.run_id
        self.artifacts_dir = self.run_dir / "artifacts"

        # Resolve temporal horizon
        anchor_time = explicit_anchor_time
        if self.run_mode != RunMode.RESUME:
            ctx_candidates: List[Path] = []
            if oracle_subject_run_dir:
                ctx_candidates.append(Path(oracle_subject_run_dir) / "runtime_context.json")
            elif self.run_mode == RunMode.FORK and self.source_run_id:
                ctx_candidates.append(runs_dir / self.source_run_id / "runtime_context.json")
            elif self.execution_mode == ExecutionMode.LAB and self.feed_source_run_id:
                ctx_candidates.append(runs_dir / self.feed_source_run_id / "runtime_context.json")

            for ctx_file in ctx_candidates:
                try:
                    if not ctx_file.exists():
                        continue
                    with open(ctx_file, "r", encoding="utf-8") as f:
                        sctx = json.load(f)
                    anchor_dt = self._extract_anchor_from_context(sctx)
                    if anchor_dt is not None and explicit_anchor_time is None:
                        anchor_time = anchor_dt
                        self._run_anchor_iso = anchor_dt.replace(microsecond=0).isoformat()
                        break
                except Exception:
                    continue
            
            self._horizon_resolved = self.resolve_horizon(horizon, now=anchor_time)
            self._horizon_label = self._horizon_resolved["horizon_label"]
            self._target_time_iso = self._horizon_resolved["target_time"]
        else:
            self._horizon_resolved = {}
            self._horizon_label = None
            self._target_time_iso = None

        # 2. Components
        self.loader = loader or PhysicalLoader(self.root_dir)
        self.bridge = Bridge(str(self.root_dir))
        
        # 3. State
        self._universe: Dict[str, CodexNode] = {}
        self._execution_scope: Set[str] = set()
        self._manifest: Dict[str, Any] = {}
        self._node_outcomes: Dict[str, str] = {}
        
        # [NEW] Container/Group State Tracking
        self._group_map: Dict[str, List[str]] = {} # group -> [node_ids]
        self._container_states: Dict[str, StepStatus] = {} # group -> aggregate status
        self._active_node_ids: Set[str] = set()    # currently running nodes
        
        # 4. Initialization
        self._init_run_directory()

        # 5. Resolve subject/truth run dirs for CP2 validation + Oracle v1 temporal pairing.
        if oracle_subject_run_dir or oracle_truth_run_dir:
            if not oracle_subject_run_dir or not oracle_truth_run_dir:
                raise LogicalFailure(
                    "Oracle v1 requires both oracle_subject_run_dir and oracle_truth_run_dir."
                )
            self._subject_run_dir = Path(oracle_subject_run_dir)
            self._truth_run_dir = Path(oracle_truth_run_dir)
            if not self._subject_run_dir.exists():
                raise LogicalFailure(
                    f"Oracle subject run directory missing: {self._subject_run_dir}"
                )
            if not self._truth_run_dir.exists():
                raise LogicalFailure(
                    f"Oracle truth run directory missing: {self._truth_run_dir}"
                )
            self._oracle_mode = True
        else:
            self._subject_run_dir = self.run_dir
            self._truth_run_dir = None
            self._oracle_mode = False
        self._assert_temporal_order(source="engine_init")

    def _next_seq(self) -> int:
        """Atomic sequence incrementor."""
        with self._seq_lock:
            self._event_seq += 1
            return self._event_seq

    @staticmethod
    def _parse_iso_utc(raw_value: Any) -> Optional[datetime]:
        """Parse numeric/ISO datetime values into UTC-aware datetimes."""
        if isinstance(raw_value, (int, float)):
            try:
                return datetime.fromtimestamp(float(raw_value), tz=timezone.utc)
            except Exception:
                return None
        if isinstance(raw_value, str):
            token = raw_value.strip()
            if not token:
                return None
            try:
                parsed = datetime.fromisoformat(token.replace("Z", "+00:00"))
            except ValueError:
                return None
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        return None

    @classmethod
    def _extract_anchor_from_context(cls, ctx: Dict[str, Any]) -> Optional[datetime]:
        """Resolve canonical snapshot anchor from runtime_context fields."""
        if not isinstance(ctx, dict):
            return None
        for field in ("as_of", "time_anchor", "data_timestamp", "timestamp"):
            parsed = cls._parse_iso_utc(ctx.get(field))
            if parsed is not None:
                return parsed
        return None

    def _assert_temporal_order(self, source: str) -> None:
        """Ensure snapshot anchor is strictly earlier than target horizon when both are known."""
        if not self._run_anchor_iso or not self._target_time_iso:
            return
        snapshot_dt = self._parse_iso_utc(self._run_anchor_iso)
        target_dt = self._parse_iso_utc(self._target_time_iso)
        if snapshot_dt is None or target_dt is None:
            raise LogicalFailure(
                f"Temporal contract violation ({source}): invalid datetime fields "
                f"snapshot={self._run_anchor_iso!r} target={self._target_time_iso!r}"
            )
        if target_dt <= snapshot_dt:
            raise LogicalFailure(
                f"Temporal contract violation ({source}): target_time_iso must be strictly after snapshot_time "
                f"(snapshot={snapshot_dt.isoformat()} target={target_dt.isoformat()})"
            )

    def _recover_horizon_from_artifacts(self) -> Optional[Dict[str, Optional[str]]]:
        """
        Best-effort recovery for resume runs whose runtime_context lost horizon fields.
        Scans persisted artifact metadata and returns the first valid temporal anchor.
        """
        if not self.artifacts_dir.exists():
            return None

        for artifact_path in sorted(self.artifacts_dir.glob("*.json")):
            if artifact_path.name in {"graph_snapshot.json", "seed_manifest.json"}:
                continue
            try:
                payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            metadata = payload.get("metadata")
            if not isinstance(metadata, dict):
                continue

            target_time_iso = metadata.get("target_time_iso")
            horizon_label = metadata.get("horizon_label")
            if not isinstance(target_time_iso, str) or not target_time_iso.strip():
                continue
            if not isinstance(horizon_label, str) or not horizon_label.strip():
                continue

            horizon_policy = metadata.get("horizon_policy")
            target_time_et = metadata.get("target_time_et")
            return {
                "policy": horizon_policy if isinstance(horizon_policy, str) else None,
                "target_time": target_time_iso,
                "target_time_et": target_time_et if isinstance(target_time_et, str) else None,
                "horizon_label": horizon_label,
            }

        return None

    def _init_run_directory(self):
        """
        Initialize or resume the run directory and attach logging.
        
        Ensures:
        - Logger handlers are attached in both FRESH (write) and RESUME (append) modes.
        - Handlers are explicitly closed on re-init to prevent file-descriptor leaks.
        - Session metadata is preserved when resuming (no destructive overwrite).
        
        """
        mode = 'w'
        
        if self.run_mode == RunMode.RESUME:
            if not self.run_dir.exists():
                raise FileNotFoundError(f"Cannot resume missing run: {self.run_id}")
            mode = 'a'
            
            # Hydrate horizon from existing context
            ctx_path = self.run_dir / "runtime_context.json"
            if ctx_path.exists():
                try:
                    with open(ctx_path, 'r') as f:
                        ctx = json.load(f)
                    hz = ctx.get("horizon", {})
                    self._horizon_resolved = {
                        "policy": hz.get("horizon_policy"),
                        "target_time": hz.get("target_time_iso"),
                        "target_time_et": hz.get("target_time_et"),
                        "horizon_label": hz.get("horizon_label")
                    }
                    self._horizon_label = self._horizon_resolved.get("horizon_label")
                    self._target_time_iso = self._horizon_resolved.get("target_time")
                    anchor_dt = self._extract_anchor_from_context(ctx)
                    if anchor_dt is not None:
                        self._run_anchor_iso = anchor_dt.replace(microsecond=0).isoformat()
                except Exception:
                    pass

            # [C4] Legacy self-resume runs may have had runtime_context horizon fields
            # overwritten by older server code. Recover from artifact metadata.
            if not self._target_time_iso or not self._horizon_label:
                recovered_horizon = self._recover_horizon_from_artifacts()
                if recovered_horizon:
                    self._horizon_resolved = recovered_horizon
                    self._horizon_label = recovered_horizon.get("horizon_label")
                    self._target_time_iso = recovered_horizon.get("target_time")
                    try:
                        ctx_path = self.run_dir / "runtime_context.json"
                        current_ctx: Dict[str, Any] = {}
                        if ctx_path.exists():
                            loaded = json.loads(ctx_path.read_text(encoding="utf-8"))
                            if isinstance(loaded, dict):
                                current_ctx = loaded
                        current_ctx["horizon"] = {
                            "horizon_policy": recovered_horizon.get("policy"),
                            "target_time_iso": recovered_horizon.get("target_time"),
                            "target_time_et": recovered_horizon.get("target_time_et"),
                            "horizon_label": recovered_horizon.get("horizon_label"),
                        }
                        ctx_path.write_text(json.dumps(current_ctx, indent=2), encoding="utf-8")
                    except Exception:
                        pass
        else:
            # Only create dirs for fresh/fork runs
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Logger
        # Remove existing handlers to avoid duplicates during re-init
        # [FIX] Close handlers to release file descriptors
        for h in list(self.logger.handlers):
            h.close()
            self.logger.removeHandler(h)
            
        fh = logging.FileHandler(self.run_dir / "engine.log", mode=mode, encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)
        self.logger.setLevel(logging.INFO)

        # Write Context (only for new runs)
        if self.run_mode != RunMode.RESUME:
            ctx_path = self.run_dir / "runtime_context.json"
            existing_ctx = {}
            
            # [FIX] Merge-Read existing context to preserve session data (like mission_name)
            if ctx_path.exists():
                try:
                    with open(ctx_path, 'r') as f:
                        existing_ctx = json.load(f)
                except Exception:
                    pass

            runtime_data = {
                "run_id": self.run_id,
                "mode": self.run_mode.value,
                "exec_mode": self.execution_mode.value,
                "source_run_id": self.source_run_id,
                "feed_source_run_id": self.feed_source_run_id,
                "subject_group": self.subject_group,
                "timestamp": time.time(),
                # [C2] Authoritative temporal anchor for all downstream tool nodes.
                # All feed tools and the calculator must consume these values
                # and stamp their metadata.as_of to match.
                "as_of": self._run_anchor_iso,
                "time_anchor": self._run_anchor_iso,
                # [C6] Bounded routing guard fields — present from run start.
                "subgraph_depth": getattr(self, "_subgraph_depth", 0),
                "failed_targets_routed": list(getattr(self, "_failed_targets_routed", [])),
                "horizon": {
                    "horizon_policy": self._horizon_resolved.get("policy"),
                    "target_time_iso": self._horizon_resolved.get("target_time"),
                    "target_time_et": self._horizon_resolved.get("target_time_et"),
                    "horizon_label": self._horizon_resolved.get("horizon_label"),
                },
            }
            
            existing_ctx.update(runtime_data)
            # [PATCH] Ensure mission_name exists
            if "mission_name" not in existing_ctx:
                existing_ctx["mission_name"] = self.subject_group

            with open(ctx_path, "w") as f:
                json.dump(existing_ctx, f, indent=2)

            # Write mission_manifest.json before Wave 0 begins.
            # Uses atomic temp->rename pattern to guarantee no partial state.
            commit_hash = _git_client.get_head_hash(self.root_dir)
            mission_manifest = {
                "run_id": self.run_id,
                "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "commit_hash": commit_hash,
                "active_contracts": [],
                "active_dossiers": list_dossier_paths(self.root_dir),
                "topology_scope": self.subject_group,
            }
            manifest_tmp = self.run_dir / "mission_manifest.tmp"
            manifest_final = self.run_dir / "mission_manifest.json"
            with open(manifest_tmp, "w", encoding="utf-8") as f:
                json.dump(mission_manifest, f, indent=2)
            manifest_tmp.replace(manifest_final)

    def emit(self, event: Any):
        """
        [ACTION]
        - Teleology: Emit runtime events to an external sink (UI/observer) and persist structural events to disk.
        - Reads: self._emit_sink (optional), logger configuration.
        - Writes: run structural log file; optionally forwards to sink.
        - Mechanism: Best-effort dispatch to sink; best-effort append of a structural record for observability.
        - Guarantee: Does not raise; attempts to record the event and dispatch it if a sink is configured.
        - Fails: None (errors are swallowed and logged best-effort).
        - When-needed: Open when tracing why runtime events reached `engine.log`, the observer sink, or stopped emitting step chatter after abort.
        - Escalates-to: system/core/bridge.py::snapshot_bridge_events_for_session; system/core/forensics.py::reconstruct_run_state
        
        """
        # [FIX] Event Barrier: Suppress step chatter if run is aborted
        # This prevents UI ghost updates (green checks) for nodes that finished after the stop signal.
        if self._stop_event.is_set() and isinstance(event, (StepStartEvent, StepEndEvent, StepPendingEvent)):
            return

        # 1. Send to WebSocket (Ephemeral)
        if self._emit_fn:
            try:
                self._emit_fn(event)
            except Exception:
                pass # Fail safe if UI is disconnected
        
        # 2. Persist to Disk (Structural Logging)
        try:
            if isinstance(event, LogEvent):
                if event.level == "ERROR":
                    self.logger.error(f"[{event.source}] {event.message}")
                else:
                    self.logger.info(f"[{event.source}] {event.message}")

            elif isinstance(event, StepStartEvent):
                self.logger.info(f"[ENGINE] ▶ START: {event.node_id}")
            
            elif isinstance(event, StepEndEvent):
                symbol = "✔" if event.status == StepStatus.SUCCESS else "✘"
                duration = f"{event.duration:.2f}s" if event.duration is not None else "?"
                self.logger.info(f"[ENGINE] {symbol} END: {event.node_id} ({event.status.value}) [{duration}]")

            elif isinstance(event, RunStartEvent):
                node_count = len(event.structure) if event.structure else 0
                self.logger.info(f"[ENGINE] 🚀 RUN STARTED: {self.run_id} ({self.run_mode.value}) - {node_count} nodes")

            elif isinstance(event, RunEndEvent):
                self.logger.info(f"[ENGINE] 🏁 RUN FINISHED: {event.status.value}")

            elif isinstance(event, WaveStartEvent):
                count = len(event.node_ids) if event.node_ids else 0
                self.logger.info(f"[GOVERNANCE] ~~~ WAVE {event.wave_index} STARTED ({count} nodes) ~~~")

            elif isinstance(event, WaveEndEvent):
                self.logger.info(f"[GOVERNANCE] ~~~ WAVE {event.wave_index} COMPLETE ({event.status.value}) ~~~")
                
            elif isinstance(event, CompletedAtStartEvent):
                self.logger.info(f"[ENGINE] RESUME: Skipped {len(event.completed_ids)} completed nodes, Severed {len(event.severed_ids)} artifact nodes.")

        except Exception:
            # Never let logging crash the actual execution
            pass

    # --- SEEDING & MANIFEST ---

    def _seed_fork_v2(self, scope: Set[str]):
        """
        [ACTION]
        - Teleology: Seed fork artifacts according to intent so iteration and audit runs freeze the correct prior state before execution resumes.
        - Mechanism: Derive ITERATION, LIVE_AUDIT, or HISTORICAL_AUDIT from the source/feed run ids, wipe fork artifacts, copy the allowed subject/feed artifacts for that intent, then persist the seeding manifest.
        - When-needed: Open when tracing why a fork resolved to LIVE_AUDIT, which artifacts LIVE_AUDIT freezes for subject nodes, or how audit seeding differs from ITERATION and HISTORICAL_AUDIT.
        - Escalates-to: system/core/forensics.py::reconstruct_run_state; system/core/bridge.py
        """
        # 1. Derive Intent
        intent = "UNKNOWN"
        if self.run_mode == RunMode.FORK:
            if self.feed_source_run_id == self.source_run_id:
                intent = "ITERATION"
            elif self.feed_source_run_id is None:
                intent = "LIVE_AUDIT"
            else:
                intent = "HISTORICAL_AUDIT"
        
        self.logger.info(f"Seeding Intent: {intent}")

        # 2. Classify Scope
        feed_ids = {nid for nid in scope if self._universe[nid].meta.get("is_feed")}
        subject_ids = {nid for nid in scope if self._universe[nid].group == self.subject_group}
        
        frozen_truth = set()
        frozen_subject = set()

        # 3. Wipe (Fork Only)
        if self.run_mode == RunMode.FORK:
            for p in self.artifacts_dir.glob("*.json"):
                p.unlink()

            src_path = self.run_dir.parent / self.source_run_id / "artifacts"
            feed_src_path = None
            if self.feed_source_run_id:
                feed_src_path = self.run_dir.parent / self.feed_source_run_id / "artifacts"

            def copy_artifact(nid: str, from_dir: Path) -> bool:
                src = from_dir / f"{nid}.json"
                dst = self.artifacts_dir / f"{nid}.json"
                if src.exists():
                    try:
                        with open(src, 'r') as f:
                            data = json.load(f)
                        status = data.get("status") or data.get("metadata", {}).get("status")
                        if status in (StepStatus.SUCCESS.value, StepStatus.LOADED.value):
                            shutil.copy(src, dst)
                            return True
                    except Exception:
                        pass
                return False

            # 4. Copy Logic based on Intent
            if intent == "ITERATION":
                count = 0
                for nid in scope:
                    if copy_artifact(nid, src_path): count += 1
                self.logger.info(f"ITERATION: Copied {count} artifacts from {self.source_run_id}")
                
            elif intent == "LIVE_AUDIT":
                count = 0
                for nid in subject_ids:
                    if copy_artifact(nid, src_path):
                        frozen_subject.add(nid)
                        count += 1
                self.logger.info(f"LIVE_AUDIT: Seeded {count} subjects.")

            elif intent == "HISTORICAL_AUDIT":
                s_count = 0
                for nid in subject_ids:
                    if copy_artifact(nid, src_path):
                        frozen_subject.add(nid)
                        s_count += 1
                
                f_count = 0
                if feed_src_path:
                    for nid in feed_ids:
                        if copy_artifact(nid, feed_src_path):
                            frozen_truth.add(nid)
                            f_count += 1
                
                missing_feed = feed_ids - frozen_truth
                if missing_feed:
                    raise LogicalFailure(f"HISTORICAL_AUDIT: Missing required feeds: {missing_feed}")
                self.logger.info(f"HISTORICAL_AUDIT: Seeded {s_count} subjects, {f_count} feeds.")

        # 5. Write Manifest
        manifest = {
            "intent": intent,
            "frozen_subject_ids": sorted(list(frozen_subject)),
            "frozen_truth_ids": sorted(list(frozen_truth)),
            "timestamp": time.time()
        }
        
        with open(self.artifacts_dir / "seed_manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
            
        self._manifest = manifest

    # --- CORE HASHING ---

    def _is_completed(self, node: CodexNode) -> bool:
        """Strict Freeze Completion Logic."""
        path = self.artifacts_dir / f"{node.id}.json"
        
        frozen_subs = set(self._manifest.get("frozen_subject_ids", []))
        frozen_truth = set(self._manifest.get("frozen_truth_ids", []))
        intent = self._manifest.get("intent", "UNKNOWN")
        
        is_frozen = (node.id in frozen_subs) or (node.id in frozen_truth)
        
        if is_frozen:
            if not path.exists():
                raise LogicalFailure(f"Corruption: Node {node.id} listed as frozen but artifact missing.")
            return True

        execution_cfg = node.execution if isinstance(node.execution, dict) else {}
        cache_policy = str(execution_cfg.get("cache_policy", "standard")).lower()
        if cache_policy == "none":
            return False

        if intent == "ITERATION" and node.meta.get("is_feed"):
            if path.exists():
                return True

        if not path.exists():
            return False
            
        try:
            with open(path, "r") as f:
                data = json.load(f)

            if self._force_load_stale_feeds and node.meta.get("is_feed"):
                status = data.get("status") or data.get("metadata", {}).get("status")
                if status in (StepStatus.SUCCESS.value, StepStatus.LOADED.value):
                    return True
            
            if data.get("node_hash") != hash_node(node):
                return False

            # [C4] For is_artifact=True nodes, cached artifacts missing horizon metadata
            # must be regenerated so they receive the required fields.
            if node.is_artifact:
                cached_meta = data.get("metadata") or {}
                if not cached_meta.get("target_time_iso") or not cached_meta.get("horizon_label"):
                    self.logger.info(
                        "[C4] Forcing regeneration of %s: cached artifact missing horizon metadata.",
                        node.id,
                    )
                    return False

            status = data.get("status")
            return status in (StepStatus.SUCCESS.value, StepStatus.LOADED.value)
        except Exception:
            return False

    def _write_artifact(self, node: CodexNode, status: StepStatus, metadata: Dict, data: Any, error: Optional[str] = None):
        """Atomic Write with Root Provenance fields."""
        # [FIX] Selective Disk Barrier: Block SUCCESS writes for dead runs (zombie prevention),
        # but ALWAYS allow FAILURE writes through so diagnostic artifacts are never lost.
        # This ensures that the most recent failure forensics are always on disk,
        # even when a stop signal races against a retry loop.
        if self._stop_event.is_set() and status != StepStatus.FAILURE:
            return

        end_time = time.time()
        node_hash = hash_node(node)
        
        metadata = dict(metadata) if isinstance(metadata, dict) else {}
        if error:
            metadata["error"] = error
        metadata["status"] = status.value
        metadata["timestamp"] = end_time

        # Additive canonical metadata/provenance injection.
        # Failure to inject should never block artifact persistence.
        try:
            metadata.setdefault("schema_version", TOOL_METADATA_SCHEMA_VERSION)
            metadata.setdefault("timestamp_iso", datetime.fromtimestamp(end_time, tz=timezone.utc).isoformat())
            metadata.setdefault("timestamp_epoch_s", end_time)

            tool_name = metadata.get("tool")
            if isinstance(tool_name, str) and tool_name.strip():
                metadata.setdefault("data_schema_version", f"{tool_name.strip()}.1")
            else:
                metadata.setdefault("data_schema_version", "unknown.1")

            metadata.setdefault("config_ref", node.config_ref)
            metadata.setdefault("merged_hash", node.merged_hash)

            if not isinstance(metadata.get("override_keys"), list):
                if isinstance(node.inline_overrides, dict):
                    metadata["override_keys"] = sorted(str(k) for k in node.inline_overrides.keys())
                else:
                    metadata["override_keys"] = []

            diagnostics = metadata.get("diagnostics")
            if not isinstance(diagnostics, dict):
                diagnostics = {}
            diagnostics.setdefault("input_rows", 0)
            diagnostics.setdefault("output_rows", 0)
            diagnostics.setdefault("dropped_rows", 0)
            diagnostics.setdefault("data_available_unused", [])
            diagnostics.setdefault("data_available_unused_count", 0)
            if isinstance(diagnostics.get("warnings"), list):
                pass
            elif diagnostics.get("warnings") is None:
                diagnostics["warnings"] = []
            else:
                diagnostics["warnings"] = [str(diagnostics.get("warnings"))]
            metadata["diagnostics"] = diagnostics
        except Exception as inject_err:
            self.logger.warning("Metadata/provenance injection failed for %s: %s", node.id, inject_err)
        
        # [C4] Horizon metadata enforcement for is_artifact=True prediction artifacts.
        # Success artifacts must be anchored in time; failure artifacts are diagnostic
        # and should not be blocked by missing temporal context.
        try:
            if node.is_artifact:
                ttime = self._target_time_iso
                hlabel = self._horizon_label
                if status == StepStatus.SUCCESS:
                    if not ttime or not hlabel:
                        raise LogicalFailure(
                            f"[C4] Node {node.id} is is_artifact=True but horizon is unresolved. "
                            f"target_time_iso={ttime!r}, horizon_label={hlabel!r}. "
                            "Cannot write unanchored prediction artifact."
                        )
                    metadata["target_time_iso"] = ttime
                    metadata["horizon_label"] = hlabel
                elif ttime and hlabel:
                    metadata.setdefault("target_time_iso", ttime)
                    metadata.setdefault("horizon_label", hlabel)
        except LogicalFailure:
            raise  # Re-raise C4 failures — do not swallow.
        except Exception as horizon_err:
            self.logger.warning("[C4] Horizon stamp failed for %s: %s", node.id, horizon_err)

        envelope = {
            "id": node.id,
            "status": status.value,
            "timestamp": end_time,
            "node_hash": node_hash,
            "teleology": node.teleology,
            "group": node.group,
            "lane": node.lane,
            "expectation": node.expectation,
            "is_artifact": node.is_artifact,
            "metadata": metadata,
            "data": data
        }
        
        tmp = self.artifacts_dir / f"{node.id}.tmp"
        final = self.artifacts_dir / f"{node.id}.json"
        
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(envelope, f, separators=(',', ':'), ensure_ascii=False)
        
        tmp.replace(final)
        alias_id = _CANONICAL_ARTIFACT_ALIASES.get(node.id)
        if status == StepStatus.SUCCESS and alias_id:
            alias_metadata = dict(metadata)
            alias_metadata["artifact_alias_of"] = node.id
            alias_metadata["canonical_artifact_id"] = alias_id
            alias_envelope = {
                **envelope,
                "id": alias_id,
                "metadata": alias_metadata,
            }
            alias_tmp = self.artifacts_dir / f"{alias_id}.tmp"
            alias_final = self.artifacts_dir / f"{alias_id}.json"
            with open(alias_tmp, "w", encoding="utf-8") as f:
                json.dump(alias_envelope, f, separators=(',', ':'), ensure_ascii=False)
            alias_tmp.replace(alias_final)
        self._node_outcomes[node.id] = status.value

    @staticmethod
    def _guard_routing(
        subgraph_depth: int,
        failed_targets_routed: List[str],
        candidate_target: str,
        max_depth: int = 2,
    ) -> Tuple[bool, str]:
        """
        [ACTION]
        [C6] Guard function for failure rerouting.

        - Returns (True, "") when routing is allowed.
        - Returns (False, reason) when routing must be blocked.
        """
        if subgraph_depth >= max_depth:
            return False, f"Routing blocked: subgraph_depth={subgraph_depth} >= max_depth={max_depth}"
        if candidate_target in failed_targets_routed:
            return False, f"Routing blocked: {candidate_target!r} already in failed lineage {failed_targets_routed}"
        return True, ""

    @staticmethod
    def _next_routing_state(
        subgraph_depth: int,
        failed_targets_routed: List[str],
        candidate_target: str,
    ) -> Tuple[int, List[str]]:
        """
        [ACTION]
        [C6] Produce the child-run routing state after dispatching to candidate_target.

        Returns (new_depth, new_failed_list) for injection into child IgnitePayload.
        """
        return (subgraph_depth + 1, list(failed_targets_routed) + [candidate_target])

    def _read_artifact_data(self, node_id: str) -> Any:
        """Best-effort loader for artifact envelope.data."""
        path = self.artifacts_dir / f"{node_id}.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if isinstance(payload, dict):
            return payload.get("data")
        return None

    def _build_equity_price_map(self, run_dir: Optional[Path] = None) -> Dict[str, float]:
        """
        Build ticker -> snapshot price map from the combined stock + ETF feed baseline.

        Oracle CP2 audits must use the subject (T-n) snapshot, not the truth run.
        """
        source_dir = Path(run_dir) if run_dir is not None else (
            self._subject_run_dir if self._oracle_mode else self.run_dir
        )
        ticker_prices: Dict[str, float] = {}
        for ticker, row in _combined_run_prices(source_dir).items():
            price = row.get("Price") if isinstance(row, dict) else None
            if isinstance(price, (int, float)) and price == price:
                ticker_prices[str(ticker).upper().strip()] = float(price)
        return ticker_prices

    def _build_stock_price_map(self) -> Dict[str, float]:
        """Backward-compatible alias for the equity-wide snapshot price map."""
        return self._build_equity_price_map()

    def _audit_cp2_predictions(self, parsed: Any) -> Any:
        """Inject deterministic temporal fields and audit model-emitted snapshot_price against feed."""
        if not isinstance(parsed, dict):
            return parsed
        predictions = parsed.get("predictions_t")
        if not isinstance(predictions, list):
            return parsed

        price_map = self._build_equity_price_map()
        tolerance = 0.005  # 0.5%
        audit_errors: List[str] = []

        for i, pred in enumerate(predictions):
            if not isinstance(pred, dict):
                continue
            target = str(pred.get("target_id", "")).upper().strip()

            # Engine owns deterministic temporal fields.
            pred["snapshot_time"] = self._run_anchor_iso
            if self._target_time_iso:
                pred["target_time_iso"] = self._target_time_iso

            if not target or target not in price_map:
                continue

            feed_price = price_map[target]
            model_price_raw = pred.get("snapshot_price")
            try:
                model_price = float(model_price_raw)
                if not (model_price == model_price):
                    raise ValueError("nan")
            except Exception:
                continue

            if feed_price == 0.0:
                mismatch_ratio = abs(model_price - feed_price)
            else:
                mismatch_ratio = abs(model_price - feed_price) / abs(feed_price)

            # Quietly normalize small model rounding drift to the feed baseline.
            if mismatch_ratio <= tolerance:
                pred["snapshot_price"] = feed_price
                continue

            audit_errors.append(
                f"SNAPSHOT_PRICE_MISMATCH: predictions_t[{i}] target_id={target} "
                f"snapshot_price={model_price} feed_price={feed_price}"
            )

        if audit_errors:
            parsed["_engine_audit_errors"] = audit_errors
        elif "_engine_audit_errors" in parsed:
            parsed.pop("_engine_audit_errors", None)
        return parsed

    def _enrich_cp2_predictions(self, parsed: Any) -> Any:
        """
        [ACTION]
        - Teleology: Preserve the legacy `_enrich_cp2_predictions` seam while routing all behavior through `_audit_cp2_predictions`.
        - Mechanism: Thin backward-compatible alias that forwards the parsed payload unchanged except for the audit-time normalization performed by `_audit_cp2_predictions`.
        - When-needed: Open when telemetry, routing coverage, or engine callers reference `_enrich_cp2_predictions` and need the exact compatibility seam rather than the canonical audit helper.
        - Escalates-to: system/core/engine.py::GodModeEngine._audit_cp2_predictions
        """
        return self._audit_cp2_predictions(parsed)

    def _extract_cross_corr_v2_targets(self) -> Optional[Set[str]]:
        """Resolve valid prediction targets from current-run artifacts, with Oracle subject-index fallback."""
        cc2_candidates = [
            self.artifacts_dir / "lab_cross_corr_v2.json",
            self.artifacts_dir / "oracle_subject_index.json",
        ]
        cc2_raw: Any = None
        for cc2_path in cc2_candidates:
            if not cc2_path.exists():
                continue
            try:
                cc2_raw = json.loads(cc2_path.read_text(encoding="utf-8"))
                break
            except Exception:
                continue
        if cc2_raw is None:
            return None

        cc2_data: Any = ""
        if isinstance(cc2_raw, dict):
            cc2_data = cc2_raw.get("data", "")
        elif isinstance(cc2_raw, str):
            cc2_data = cc2_raw

        if isinstance(cc2_data, dict):
            targets = set()
            explicit = cc2_data.get("valid_prediction_targets")
            if isinstance(explicit, list):
                for token in explicit:
                    t = str(token).upper().strip()
                    if t and t != "NONE":
                        targets.add(t)
            if targets:
                return targets

            for field in ("target_swarms", "solo_targets"):
                entries = cc2_data.get(field)
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    tickers = entry.get("tickers")
                    if not isinstance(tickers, list):
                        continue
                    for token in tickers:
                        t = str(token).upper().strip()
                        if t and t != "NONE":
                            targets.add(t)
            return targets or None

        if isinstance(cc2_data, str) and cc2_data:
            import re as _re

            def _extract_ticker_tokens(raw: str) -> Set[str]:
                tokens = set()
                for tok in _re.findall(r"[A-Z0-9][A-Z0-9._-]{0,9}", raw.upper()):
                    normalized = tok.strip(" .,)(").upper()
                    if normalized and normalized != "NONE":
                        tokens.add(normalized)
                return tokens

            extracted_targets: Set[str] = set()
            ticker_lines = _re.findall(r"^\s*TICKERS:\s*(.+)$", cc2_data, _re.MULTILINE)
            for line in ticker_lines:
                extracted_targets.update(_extract_ticker_tokens(line))
            paren_tickers = _re.findall(
                r"(?:TARGET_SWARM|SOLO_TARGET):[^\n]*\(([^)]+)\)",
                cc2_data,
            )
            for group in paren_tickers:
                extracted_targets.update(_extract_ticker_tokens(group))
            bare_tickers = _re.findall(
                r"(?:TARGET_SWARM|SOLO_TARGET):\s*([A-Z0-9._-]{1,10})\s*$",
                cc2_data,
                _re.MULTILINE,
            )
            for ticker in bare_tickers:
                extracted_targets.update(_extract_ticker_tokens(ticker))
            return extracted_targets or None
        return None

    def _extract_integrity_override(self) -> Optional[str]:
        """Return GREEN/RED override from lab_integrity artifact when present."""
        integrity_path = self.artifacts_dir / "lab_integrity.json"
        if not integrity_path.exists():
            return None
        try:
            raw = json.loads(integrity_path.read_text(encoding="utf-8"))
        except Exception:
            return None

        data = raw.get("data") if isinstance(raw, dict) else raw
        if isinstance(data, dict):
            grade = data.get("grade_override")
            if isinstance(grade, str):
                token = grade.strip().upper()
                if token in {"GREEN", "RED"}:
                    return token
        if isinstance(data, str):
            m = re.search(r"GRADE_OVERRIDE:\s*(GREEN|RED)", data[:200], flags=re.IGNORECASE)
            if m:
                return m.group(1).upper()
        return None

    def _write_lab_contract_audit(self) -> Dict[str, Any]:
        """Compute and persist deterministic contract audit artifact."""
        audit_data = compute_lab_contract_audit(self.artifacts_dir)
        ts = time.time()
        envelope = {
            "id": "lab_contract_audit",
            "status": "success",
            "timestamp": ts,
            "node_hash": hashlib.sha256(
                json.dumps(audit_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
            "teleology": "Deterministic contract audit over Lab pipeline artifacts.",
            "group": "lab",
            "lane": "SPINE",
            "expectation": "Output machine-checkable hard fails and soft violations.",
            "is_artifact": True,
            "metadata": {
                "model": "deterministic",
                "status": "success",
                "timestamp": ts,
                "timestamp_iso": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                "timestamp_epoch_s": ts,
            },
            "data": audit_data,
        }
        tmp = self.artifacts_dir / "lab_contract_audit.tmp"
        final = self.artifacts_dir / "lab_contract_audit.json"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(envelope, f, separators=(",", ":"), ensure_ascii=False)
        tmp.replace(final)
        return audit_data

    def _maybe_write_oracle_observation_report(self, oracle_cp2: Any) -> None:
        """
        Persist observation_report.json after a successful Oracle CP2 emission.

        Oracle v1 keeps `oracle_cp2_emitter` as the sink id, so the report is emitted
        opportunistically from the engine once the final CP2 artifact exists.
        """
        if not self._oracle_mode or not isinstance(oracle_cp2, dict):
            return

        subject_env = load_artifact(self._subject_run_dir, "lab_director")
        if not isinstance(subject_env, dict):
            self.logger.warning(
                "Skipping observation_report: subject lab_director missing in %s",
                self._subject_run_dir,
            )
            return
        subject_cp2 = subject_env.get("data", {})
        if not isinstance(subject_cp2, dict):
            self.logger.warning(
                "Skipping observation_report: subject lab_director data malformed in %s",
                self._subject_run_dir,
            )
            return
        try:
            oracle_v1 = self._build_oracle_v1_observation_payload()
            report = generate_observation_report(
                subject_cp2,
                oracle_cp2,
                self._subject_run_dir,
                persist=False,
                report_run_id=self.run_id,
                oracle_v1=oracle_v1,
            )
            output_path = self.artifacts_dir / "observation_report.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report.to_json_dict(), f, indent=2, sort_keys=True)
        except Exception as exc:
            self.logger.warning("Failed to generate observation_report.json: %s", exc)

    def _build_oracle_v1_observation_payload(self) -> Optional[Dict[str, Any]]:
        """Build the additive Oracle v1 section for observation_report.json."""
        diff_env = load_artifact(self.run_dir, "prediction_reconciliation")
        attribution_env = load_artifact(self.run_dir, "cp2_critique")
        if not isinstance(diff_env, dict) and not isinstance(attribution_env, dict):
            return None

        diff_data = diff_env.get("data", {}) if isinstance(diff_env, dict) else {}
        attribution_data = attribution_env.get("data", {}) if isinstance(attribution_env, dict) else {}

        if not isinstance(diff_data, dict) and not isinstance(attribution_data, dict):
            return None

        if not isinstance(diff_data, dict):
            diff_data = {}
        if not isinstance(attribution_data, dict):
            attribution_data = {}

        truth_run_id = None
        if self._truth_run_dir is not None:
            truth_run_id = self._truth_run_dir.name

        return {
            "subject_run_id": diff_data.get("subject_run_id") or self._subject_run_dir.name,
            "truth_run_id": diff_data.get("truth_run_id") or truth_run_id,
            "reconciliation_summary": self._oracle_report_reconciliation_summary(diff_data),
            "grading_summary": self._oracle_report_grading_summary(diff_data),
            "largest_miss_targets": self._oracle_report_largest_miss_targets(diff_data),
            "attribution_summary": self._summarize_oracle_attribution(attribution_data),
            "reconstruction_guidance_summary": self._summarize_oracle_guidance(attribution_data),
        }

    @staticmethod
    def _coerce_oracle_report_list(value: Any) -> List[Any]:
        return value if isinstance(value, list) else []

    @staticmethod
    def _oracle_report_realized_target_table(diff_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        legacy_rows = diff_data.get("realized_target_table")
        if isinstance(legacy_rows, list):
            return legacy_rows

        rows = diff_data.get("rows")
        if not isinstance(rows, list):
            return []

        report_rows: List[Dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            report_rows.append(
                {
                    "target_id": row.get("target_id"),
                    "predicted_direction": row.get("prediction_direction"),
                    "snapshot_price": row.get("subject_snapshot_price"),
                    "predicted_price": row.get("predicted_target_price"),
                    "realized_price": row.get("realized_truth_price"),
                    "direction_hit": row.get("directional_correct"),
                    "abs_error": row.get("absolute_delta"),
                    "pred_error_pct": row.get("percent_delta"),
                    "status": "GRADED",
                    "asset_class": row.get("asset_class"),
                    "rank": row.get("rank"),
                }
            )
        return report_rows

    @staticmethod
    def _oracle_report_grading_summary(diff_data: Dict[str, Any]) -> Dict[str, Any]:
        legacy_summary = diff_data.get("grading_summary")
        if isinstance(legacy_summary, dict):
            return legacy_summary

        summary = diff_data.get("summary")
        if not isinstance(summary, dict):
            return {}

        row_count = summary.get("row_count")
        correct = summary.get("directionally_correct_count")
        incorrect = summary.get("directionally_incorrect_count")
        hit_rate = None
        if isinstance(row_count, (int, float)) and row_count:
            if isinstance(correct, (int, float)):
                hit_rate = float(correct) / float(row_count)

        result: Dict[str, Any] = {
            "hit_rate": hit_rate,
        }
        if isinstance(correct, (int, float)):
            result["hits"] = int(correct)
        if isinstance(incorrect, (int, float)):
            result["misses"] = int(incorrect)
        if isinstance(row_count, (int, float)):
            result["graded"] = int(row_count)
            result["ungraded"] = 0
        if summary.get("largest_absolute_miss_target") is not None:
            result["largest_absolute_miss_target"] = summary.get("largest_absolute_miss_target")
        if summary.get("largest_percent_miss_target") is not None:
            result["largest_percent_miss_target"] = summary.get("largest_percent_miss_target")
        return result

    @staticmethod
    def _oracle_report_reconciliation_summary(diff_data: Dict[str, Any]) -> Dict[str, Any]:
        summary = diff_data.get("summary")
        if not isinstance(summary, dict):
            return {}
        return {
            key: summary.get(key)
            for key in (
                "row_count",
                "directionally_correct_count",
                "directionally_incorrect_count",
            )
            if summary.get(key) is not None
        }

    @staticmethod
    def _oracle_report_largest_miss_targets(diff_data: Dict[str, Any]) -> Dict[str, Any]:
        summary = diff_data.get("summary")
        if not isinstance(summary, dict):
            return {}
        result: Dict[str, Any] = {}
        if summary.get("largest_absolute_miss_target") is not None:
            result["absolute"] = summary.get("largest_absolute_miss_target")
        if summary.get("largest_percent_miss_target") is not None:
            result["percent"] = summary.get("largest_percent_miss_target")
        return result

    @staticmethod
    def _summarize_oracle_attribution(attribution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress the attribution artifact into a report-friendly summary block."""
        if not isinstance(attribution_data, dict):
            return {}

        critique_items = attribution_data.get("critique_items")
        if not isinstance(critique_items, list):
            critique_items = []
        valid_critique_items = [item for item in critique_items if isinstance(item, dict)]

        critique_scopes: List[str] = []
        for item in valid_critique_items:
                scope = str(item.get("scope") or "").strip()
                if scope and scope not in critique_scopes:
                    critique_scopes.append(scope)

        summary = {"root_failure_mode": attribution_data.get("root_failure_mode")}
        if valid_critique_items:
            summary["critique_item_count"] = len(valid_critique_items)
            summary["critique_scopes"] = critique_scopes
        return summary

    @staticmethod
    def _summarize_oracle_guidance(attribution_data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(attribution_data, dict):
            return {}

        guidance = attribution_data.get("cp2_reconstruction_guidance")
        if not isinstance(guidance, dict):
            guidance = attribution_data.get("reconstruction_guidance")
        if not isinstance(guidance, dict):
            return {}

        prefer_targets = guidance.get("prefer_targets")
        avoid_targets = guidance.get("avoid_targets")
        eligible_ledger_ids = guidance.get("eligible_ledger_ids")

        summary: Dict[str, Any] = {}
        if isinstance(guidance.get("dominant_force"), str) and guidance.get("dominant_force", "").strip():
            summary["dominant_force"] = guidance.get("dominant_force")
        if isinstance(prefer_targets, list):
            summary["prefer_targets"] = [item for item in prefer_targets if isinstance(item, str) and item.strip()]
        if isinstance(avoid_targets, list):
            summary["avoid_targets"] = [item for item in avoid_targets if isinstance(item, str) and item.strip()]
        if isinstance(eligible_ledger_ids, list):
            summary["eligible_ledger_id_count"] = len(
                [item for item in eligible_ledger_ids if isinstance(item, str) and item.strip()]
            )
        return summary

    def _append_contract_ledger(self, audit_data: Dict[str, Any], final_grade: str) -> None:
        """Append one per-run contract compliance record to contract_ledger.jsonl."""
        ledger_path = self.run_dir / "contract_ledger.jsonl"
        if ledger_path.exists():
            try:
                for line in ledger_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    parsed = json.loads(line)
                    if isinstance(parsed, dict) and parsed.get("run_id") == self.run_id:
                        return
            except Exception:
                pass

        entry = {
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hard_fails": list(audit_data.get("hard_fails", [])) if isinstance(audit_data, dict) else [],
            "soft_violations": dict(audit_data.get("soft_violations", {})) if isinstance(audit_data, dict) else {},
            "integrity_grade": self._extract_integrity_override() or "UNKNOWN",
            "final_grade": str(final_grade).lower(),
        }
        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False))
            f.write("\n")

    def _calculate_run_grade(self) -> Tuple[str, str]:
        """Calculate Traffic Light Grade (Green/Amber/Red)."""
        # [FIX] Return lowercase to match Pydantic schema
        has_failure = any(s == StepStatus.FAILURE.value for s in self._node_outcomes.values())
        if has_failure:
            return "red", "Run contains failed nodes"

        # [FIX] Sorted iteration for deterministic grade_reason
        for nid in sorted(self._execution_scope):
            path = self.artifacts_dir / f"{nid}.json"
            if not path.exists():
                return "red", f"Missing artifact: {nid}"
            # [FIX] 5KB size check applies only to tool nodes (feeds),
            # not reasoning nodes which are naturally small.
            node = self._universe.get(nid)
            if node and node.type == NodeType.TOOL and path.stat().st_size < 5120:
                return "red", f"Artifact too small (<5KB): {nid}"

        # Deterministic audit hard-fails are first-class run failures.
        audit_path = self.artifacts_dir / "lab_contract_audit.json"
        if audit_path.exists():
            try:
                audit_env = json.loads(audit_path.read_text(encoding="utf-8"))
                audit_data = audit_env.get("data", {}) if isinstance(audit_env, dict) else {}
                hard_fails = (
                    audit_data.get("hard_fails", [])
                    if isinstance(audit_data, dict)
                    else []
                )
                if isinstance(hard_fails, list) and hard_fails:
                    first = str(hard_fails[0])
                    return "red", f"Deterministic contract audit hard fail: {first}"
            except Exception:
                pass

        # Honor integrity oracle grade override.
        if self._extract_integrity_override() == "RED":
            return "red", "Integrity oracle override: RED"

        tool_node_ids = [
            nid
            for nid in sorted(self._execution_scope)
            if (self._universe.get(nid) and self._universe[nid].type == NodeType.TOOL)
        ]
        quality_override = quality_grade_override(
            collect_artifact_qualities(self.artifacts_dir, tool_node_ids)
        )
        if quality_override is not None:
            return quality_override

        return "green", "All checks passed"

    def _finalize_node_outcomes(self) -> None:
        """
        Ensure node_outcomes is a full coverage map of the execution scope.

        - If a stop signal was raised, in-flight nodes are marked `cancelled`.
        - Any scoped node without a terminal outcome is marked `not_started`.
        """
        if not self._execution_scope:
            return

        if self._stop_event.is_set():
            for nid in sorted(self._active_node_ids):
                if nid in self._execution_scope and nid not in self._node_outcomes:
                    self._node_outcomes[nid] = StepStatus.CANCELLED.value

        for nid in sorted(self._execution_scope):
            if nid not in self._node_outcomes:
                self._node_outcomes[nid] = StepStatus.NOT_STARTED.value

    def _write_final_summary(self, status_override: Optional[str] = None, reason_override: str = ""):
        """
        Force-write the final run summary to disk.
        
        Used by the `finally` block to ensure every run has a terminal summary artifact even after failure.
        
        """
        try:
            self._finalize_node_outcomes()
            audit_data: Dict[str, Any] = {}
            try:
                audit_data = self._write_lab_contract_audit()
            except Exception as audit_err:
                self.logger.warning("Failed to write lab contract audit artifact: %s", audit_err)

            grade, reason = self._calculate_run_grade()
            
            # Allow overrides for Abort/Crash scenarios
            if status_override:
                grade = status_override # e.g. "amber" or "red"
            if reason_override:
                reason = reason_override

            duration = 0.0
            if self._start_time > 0:
                duration = time.time() - self._start_time

            summary = {
                "run_id": self.run_id,
                "timestamp": time.time(),
                "grade": grade,
                "grade_reason": reason,
                "node_outcomes": self._node_outcomes,
                "duration_seconds": duration
            }
            
            # Atomic Write
            tmp = self.run_dir / "run_summary.tmp"
            final = self.run_dir / "run_summary.json"
            
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(final)
            try:
                self._append_contract_ledger(audit_data, final_grade=grade)
            except Exception as ledger_err:
                self.logger.warning("Failed to append contract ledger: %s", ledger_err)
            self._write_compact_run_snapshot()
            self._write_run_contract_bundle()
        except Exception as e:
            self.logger.error(f"CRITICAL: Failed to write final summary: {e}")

    @staticmethod
    def _stable_json_sha256(value: Any) -> str:
        """
        Return a deterministic SHA256 fingerprint for JSON-like values.

        Falls back to `repr(value)` when canonical JSON serialization fails.
        """
        try:
            blob = json.dumps(
                value,
                separators=(",", ":"),
                sort_keys=True,
                ensure_ascii=False,
            )
        except Exception:
            blob = repr(value)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_lab_oracle_node(node: CodexNode) -> bool:
        """
        Compact snapshot filter:
        - include Lab/Oracle semantic nodes;
        - exclude feed/tool substrate.
        """
        group = str(getattr(node, "group", "") or "").strip().lower()
        node_id = str(getattr(node, "id", "") or "").strip().lower()
        if group in {"lab", "oracle"}:
            return True
        return node_id.startswith("lab_") or node_id.startswith("oracle_")

    @staticmethod
    def _is_global_feed_node(node: CodexNode) -> bool:
        node_id = str(getattr(node, "id", "") or "")
        meta = getattr(node, "meta", {}) or {}
        return node_id.startswith("global_") or bool(meta.get("is_feed"))

    def _collect_compact_contracts(self, node_ids: List[str]) -> Dict[str, List[str]]:
        """Deduplicate contract references once at top-level."""
        output_schemas: Set[str] = set()
        instruction_contracts: Set[str] = set()

        for node_id in node_ids:
            node = self._universe.get(node_id)
            if node is None:
                continue

            schema_name = str(getattr(node, "output_schema", "text") or "text")
            if schema_name and schema_name != "text":
                output_schemas.add(schema_name)

            instruction = str(getattr(node, "instruction", "") or "")
            for match in _INSTRUCTION_CONTRACT_RE.findall(instruction):
                cleaned = str(match).strip()
                if cleaned:
                    instruction_contracts.add(cleaned)

        return {
            "output_schemas": sorted(output_schemas),
            "instruction_contracts": sorted(instruction_contracts),
        }

    def _load_artifact_cache(self) -> Dict[str, Dict[str, Any]]:
        """
        Load artifact envelopes once for compact snapshot assembly.

        Skips structural non-node artifacts and tolerates malformed JSON.
        """
        cache: Dict[str, Dict[str, Any]] = {}
        if not self.artifacts_dir.exists():
            return cache

        skip_names = {
            "graph_snapshot.json",
            "seed_manifest.json",
            "runtime_context.json",
            "run_summary.json",
        }
        for artifact_path in sorted(self.artifacts_dir.glob("*.json")):
            if artifact_path.name in skip_names:
                continue
            try:
                payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(payload, dict):
                cache[artifact_path.stem] = payload
        return cache

    def _compact_runtime_context(self) -> Dict[str, Any]:
        """
        Read and trim runtime context for compact snapshot runtime injections.
        """
        context_path = self.run_dir / "runtime_context.json"
        if not context_path.exists():
            return {}
        try:
            loaded = json.loads(context_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(loaded, dict):
            return {}

        fields = (
            "mission_name",
            "target_id",
            "run_mode",
            "execution_mode",
            "source_run_id",
            "feed_source_run_id",
            "subject_group",
            "as_of",
            "time_anchor",
            "effective_date",
        )
        compact = {k: loaded.get(k) for k in fields if k in loaded}
        horizon = loaded.get("horizon")
        if isinstance(horizon, dict):
            compact["horizon"] = {
                "horizon_policy": horizon.get("horizon_policy"),
                "target_time_iso": horizon.get("target_time_iso"),
                "target_time_et": horizon.get("target_time_et"),
                "horizon_label": horizon.get("horizon_label"),
            }
        return compact

    def _write_compact_run_snapshot(self) -> None:
        """
        Write a compact, deduplicated run snapshot for Lab/Oracle nodes.

        Characteristics:
        - Auto-created on completion/resume via `_write_final_summary`.
        - Deterministic refresh: final snapshot is re-written on each finalize pass.
        - Compact JSON (no pretty indent).
        - Excludes global feed node entries.
        - Includes node responses, dependency lists, and injected dependency summaries.
        - Lifts contract references to top-level deduplicated arrays.
        """
        final = self.run_dir / _COMPACT_RUN_SNAPSHOT_FILE

        try:
            artifact_cache = self._load_artifact_cache()

            if self._execution_scope:
                candidate_node_ids = sorted(self._execution_scope)
            else:
                candidate_node_ids = sorted(self._universe.keys())

            include_node_ids: List[str] = []
            for node_id in candidate_node_ids:
                node = self._universe.get(node_id)
                if node is None:
                    continue
                if self._is_global_feed_node(node):
                    continue
                if not self._is_lab_oracle_node(node):
                    continue
                include_node_ids.append(node_id)

            contracts = self._collect_compact_contracts(include_node_ids)
            nodes_payload: List[Dict[str, Any]] = []

            for node_id in include_node_ids:
                node = self._universe.get(node_id)
                if node is None:
                    continue

                artifact = artifact_cache.get(node_id, {})
                metadata = artifact.get("metadata", {}) if isinstance(artifact.get("metadata"), dict) else {}
                dependencies = [str(dep) for dep in tuple(getattr(node, "dependencies", ()))]

                injected: List[Dict[str, Any]] = []
                missing_dependencies: List[str] = []
                for dep_id in dependencies:
                    dep_artifact = artifact_cache.get(dep_id)
                    if not isinstance(dep_artifact, dict):
                        missing_dependencies.append(dep_id)
                        continue
                    dep_meta = dep_artifact.get("metadata", {}) if isinstance(dep_artifact.get("metadata"), dict) else {}
                    dep_data = dep_artifact.get("data")
                    injected.append(
                        {
                            "id": dep_id,
                            "status": dep_artifact.get("status") or dep_meta.get("status"),
                            "node_hash": dep_artifact.get("node_hash"),
                            "data_sha256": self._stable_json_sha256(dep_data),
                        }
                    )

                node_status = artifact.get("status") if isinstance(artifact, dict) else None
                if not node_status:
                    node_status = self._node_outcomes.get(node_id)

                response_meta_fields = (
                    "status",
                    "error",
                    "model",
                    "tool",
                    "timestamp_iso",
                    "target_time_iso",
                    "horizon_label",
                    "hydrated_from",
                    "hydrated_from_subject",
                )
                response_meta = {k: metadata.get(k) for k in response_meta_fields if k in metadata}

                node_type = getattr(node, "type", None)
                node_type_str = node_type.value if hasattr(node_type, "value") else str(node_type)

                nodes_payload.append(
                    {
                        "id": node_id,
                        "group": node.group,
                        "lane": node.lane,
                        "type": node_type_str,
                        "status": node_status,
                        "dependencies": dependencies,
                        "injected": {
                            "dependencies": injected,
                            "missing_dependencies": missing_dependencies,
                        },
                        "node_hash": artifact.get("node_hash") if isinstance(artifact, dict) else None,
                        "response_meta": response_meta,
                        "response": artifact.get("data") if isinstance(artifact, dict) else None,
                    }
                )

            payload = {
                "run_id": self.run_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "runtime_injection": self._compact_runtime_context(),
                "contracts": contracts,
                "nodes": nodes_payload,
            }

            tmp = self.run_dir / _COMPACT_RUN_SNAPSHOT_TMP
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, separators=(",", ":"), ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(final)
        except Exception as e:
            self.logger.error(f"Failed to write {_COMPACT_RUN_SNAPSHOT_FILE}: {e}")

    @staticmethod
    def _normalize_contract_name(raw_ref: str) -> str:
        """Normalize a contract reference to a stable filename."""
        text = str(raw_ref or "").strip()
        if not text:
            return ""
        return Path(text).name

    def _read_contract_body_from_repo(self, contract_name: str) -> str:
        """
        Best-effort contract body lookup in `codex/contracts/`.

        Returns empty string when the contract file is missing/unreadable.
        """
        name = self._normalize_contract_name(contract_name)
        if not name:
            return ""
        root = getattr(self, "root_dir", None)
        if not root:
            return ""
        try:
            contract_path = (Path(root) / "codex" / "contracts" / name).resolve()
        except Exception:
            return ""
        if not contract_path.exists():
            return ""
        try:
            return contract_path.read_text(encoding="utf-8").strip()
        except Exception:
            return ""

    def _write_run_contract_bundle(self) -> None:
        """
        Persist a per-run combined contract bundle.

        Characteristics:
        - Backend-generated (engine finalization).
        - Create-once idempotent (existing file is preserved).
        - Dedupe by contract filename + content hash.
        - Sources:
          1. Inline `[CONTRACT: ...] ... [/CONTRACT]` blocks from effective node instructions.
          2. Contract markers without inline body (resolved from `codex/contracts/`).
          3. Output schema contracts (`schema_cp1.json` / `schema_cp2.json`) when applicable.
        """
        contracts_dir = self.run_dir / _RUN_CONTRACTS_DIR
        final = contracts_dir / _RUN_CONTRACTS_FILE
        if final.exists():
            return

        try:
            if self._execution_scope:
                node_ids = sorted(self._execution_scope)
            else:
                node_ids = sorted(self._universe.keys())

            # key=(contract_name, sha256(content))
            combined: Dict[Tuple[str, str], Dict[str, Any]] = {}

            def _add(contract_name: str, contract_body: str, node_id: str, source: str) -> None:
                name = self._normalize_contract_name(contract_name)
                body = str(contract_body or "").strip()
                if not name or not body:
                    return
                digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                key = (name, digest)
                if key not in combined:
                    combined[key] = {
                        "contract": name,
                        "sha256": digest,
                        "source_nodes": [],
                        "sources": [],
                        "content": body,
                    }
                entry = combined[key]
                if node_id not in entry["source_nodes"]:
                    entry["source_nodes"].append(node_id)
                if source not in entry["sources"]:
                    entry["sources"].append(source)

            for node_id in node_ids:
                node = self._universe.get(node_id)
                if node is None:
                    continue
                instruction = str(getattr(node, "instruction", "") or "")

                names_with_inline: Set[str] = set()
                for block in _CONTRACT_BLOCK_RE.finditer(instruction):
                    raw_ref = str(block.group(1) or "")
                    body = str(block.group(2) or "").strip()
                    name = self._normalize_contract_name(raw_ref)
                    if not name:
                        continue
                    names_with_inline.add(name)
                    if not body:
                        body = self._read_contract_body_from_repo(name)
                    _add(name, body, node_id, "instruction_inline")

                for raw_ref in _INSTRUCTION_CONTRACT_RE.findall(instruction):
                    name = self._normalize_contract_name(raw_ref)
                    if not name or name in names_with_inline:
                        continue
                    body = self._read_contract_body_from_repo(name)
                    _add(name, body, node_id, "instruction_ref")

                output_schema = str(getattr(node, "output_schema", "text") or "text")
                schema_contract = _OUTPUT_SCHEMA_CONTRACTS.get(output_schema, "")
                if schema_contract:
                    schema_body = self._read_contract_body_from_repo(schema_contract)
                    _add(schema_contract, schema_body, node_id, "output_schema")

            contracts_list = sorted(
                combined.values(),
                key=lambda item: (str(item.get("contract", "")), str(item.get("sha256", ""))),
            )
            for item in contracts_list:
                item["source_nodes"] = sorted(item.get("source_nodes", []))
                item["sources"] = sorted(item.get("sources", []))

            payload = {
                "run_id": self.run_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "node_count": len(node_ids),
                "contract_count": len(contracts_list),
                "contracts": contracts_list,
            }

            contracts_dir.mkdir(parents=True, exist_ok=True)
            tmp = contracts_dir / _RUN_CONTRACTS_TMP
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, separators=(",", ":"), ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(final)
        except Exception as e:
            self.logger.error(f"Failed to write {_RUN_CONTRACTS_FILE}: {e}")

    # --- CONTAINER STATE LOGIC ---

    def _update_container_state(self, group: str):
        """
        Update group container state using worst-offender aggregation and emit when it changes.
        
        Priority order: RUNNING > FAILURE > PENDING > SUCCESS.
        
        """
        if not group or group not in self._group_map:
            return

        node_ids = self._group_map[group]
        # Filter to only relevant nodes in this run
        relevant_ids = [nid for nid in node_ids if nid in self._execution_scope]
        if not relevant_ids:
            return

        # Determine aggregate status
        has_running = any(nid in self._active_node_ids for nid in relevant_ids)
        has_failure = any(self._node_outcomes.get(nid) == StepStatus.FAILURE.value for nid in relevant_ids)
        all_success = all(self._node_outcomes.get(nid) in (StepStatus.SUCCESS.value, StepStatus.LOADED.value) for nid in relevant_ids)
        
        new_status = StepStatus.PENDING
        if has_running:
            new_status = StepStatus.RUNNING
        elif has_failure:
            new_status = StepStatus.FAILURE
        elif all_success:
            new_status = StepStatus.SUCCESS

        # Emit if changed
        current = self._container_states.get(group, StepStatus.PENDING)
        if new_status != current:
            self._container_states[group] = new_status
            self.emit(ContainerStateEvent(time.time(), self.run_id, self._next_seq(), group, new_status))

    # --- EXECUTION LOOP ---

    def run(self, target_id: Optional[str] = None):
        """
        [ACTION]
        - Teleology: Execute the Codex DAG with Flight Recorder safety.
        - Mechanism: Loads nodes, computes waves, and executes concurrently.
        - Fails: Emits failure events and logs errors, but attempts safe shutdown.
        - Guarantee: Artifacts and Run Summary are written to disk.
        - When-needed: Open when diagnosing the top-level run lifecycle from node hydration through wave execution, completion severing, and final summary persistence.
        - Escalates-to: system/core/loader.py::PhysicalLoader.load_all_nodes; system/core/governance.py::compute_waves; system/core/forensics.py::reconstruct_run_state
        """
        self._start_time = time.time() # [INIT TIMER]
        
        try:
            # 1. Load Universe
            self._universe = self.loader.load_all_nodes()
            
            # Map Groups
            for nid, node in self._universe.items():
                if node.group not in self._group_map:
                    self._group_map[node.group] = []
                self._group_map[node.group].append(nid)
            
            # 2. Scope
            if target_id:
                self._resolve_execution_scope(target_id)
            else:
                self._execution_scope = set(self._universe.keys())
                
            if self.run_mode == RunMode.FORK:
                self._seed_fork_v2(self._execution_scope)
            elif self.run_mode == RunMode.RESUME:
                m_path = self.artifacts_dir / "seed_manifest.json"
                if m_path.exists():
                    with open(m_path, "r") as f:
                        self._manifest = json.load(f)

            # Emit DAG Structure
            structure = {n.id: list(n.dependencies) for n in self._universe.values()}
            self.emit(RunStartEvent(time.time(), self.run_id, self._next_seq(), self.run_mode, structure))
            
            # 3. Topology & Severing
            active_nodes = {}
            severed_ids = set()
            completed_ids = set()
            
            for nid in self._execution_scope:
                node = self._universe[nid]
                if self._is_completed(node):
                    completed_ids.add(nid)
                    if node.is_artifact:
                        active_nodes[nid] = self._sever_dependencies(node)
                        severed_ids.add(nid)
                    else:
                        active_nodes[nid] = node
                    self._node_outcomes[nid] = StepStatus.LOADED.value
                else:
                    active_nodes[nid] = node

            # Initial Container Updates (for Loaded nodes)
            touched_groups = {self._universe[nid].group for nid in self._execution_scope}
            for g in touched_groups:
                self._update_container_state(g)

            # Emit Completion Report
            if completed_ids or severed_ids:
                intent = self._manifest.get("intent", "UNKNOWN")
                self.emit(CompletedAtStartEvent(
                    time.time(), self.run_id, self._next_seq(), 
                    list(completed_ids), list(severed_ids), intent
                ))

            # 4. Compute Waves
            try:
                waves = compute_waves(active_nodes)
            except ValueError as e:
                self.emit(LogEvent(time.time(), self.run_id, self._next_seq(), "ERROR", str(e), "GOVERNANCE"))
                # We raise here to trigger the failure handling in the except/finally blocks
                raise e 

            # 5. Execute Waves
            max_workers = int(_rv(self.config.get("execution", {}).get("max_workers", 4), 4))
            
            for wave_idx, wave_ids in enumerate(waves):
                # CHECK ABORT START OF WAVE
                if self._stop_event.is_set():
                    self.logger.warning("Execution interrupted (Start of Wave)")
                    self.emit(LogEvent(time.time(), self.run_id, self._next_seq(), "WARNING", "Execution aborted by user", "ENGINE"))
                    return # Triggers finally block

                wave_exec_ids = [nid for nid in wave_ids if nid in self._execution_scope]
                if not wave_exec_ids:
                    self.emit(WaveEndEvent(time.time(), self.run_id, self._next_seq(), wave_idx, StepStatus.SKIPPED))
                    continue
                
                # Pre-computation Narration & Pending State
                for nid in wave_exec_ids:
                    self.emit(StepPendingEvent(time.time(), self.run_id, self._next_seq(), nid))
                
                self.emit(WaveStartEvent(time.time(), self.run_id, self._next_seq(), wave_idx, wave_exec_ids))
                
                # [FIX] Manual Executor Management to Avoid Zombie Locks
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
                try:
                    futures = {
                        executor.submit(self._execute_node, nid): nid 
                        for nid in wave_exec_ids
                    }
                    
                    # [FIX] Resilient Wave Execution
                    # Let all sibling nodes finish before failing the run.
                    # Previously, the first failure aborted all siblings mid-response.
                    first_error = None
                    for future in concurrent.futures.as_completed(futures):
                        # CHECK ABORT MID-WAVE (user-initiated stop)
                        if self._stop_event.is_set():
                            executor.shutdown(wait=False, cancel_futures=True)
                            self.emit(LogEvent(time.time(), self.run_id, self._next_seq(), "WARNING", "Execution aborted mid-wave", "ENGINE"))
                            return # Triggers finally block

                        nid = futures[future]
                        try:
                            future.result()
                        except Exception as e:
                            self.logger.error(f"Node {nid} failed: {e}")
                            if first_error is None:
                                first_error = e

                    if first_error is not None:
                        failed_node_id = getattr(first_error, "_engine_failed_node_id", None)
                        if not failed_node_id:
                            for future, candidate_node_id in futures.items():
                                if future.done() and future.exception() is first_error:
                                    failed_node_id = candidate_node_id
                                    break
                        if not failed_node_id:
                            failed_node_id = "unknown"
                        self.emit(WaveEndEvent(time.time(), self.run_id, self._next_seq(), wave_idx, StepStatus.FAILURE))
                        raise NodeExecutionFailure(failed_node_id, first_error)
                finally:
                    # Clean up resources without blocking
                    executor.shutdown(wait=False)
                
                # Signal Wave End
                self.emit(WaveEndEvent(time.time(), self.run_id, self._next_seq(), wave_idx, StepStatus.SUCCESS))

            # Finalize
            self.emit(RunEndEvent(time.time(), self.run_id, self._next_seq(), StepStatus.SUCCESS))
            # Normal write is now handled by finally block if not written, or we can explicit call it here.
            # Implicitly, if we finish logic, finally block will see file is missing and write it.
            # But let's write it explicitly for clarity on success.
            self._write_final_summary()

        except NodeExecutionFailure as e:
            self.logger.error("Run failed because node %s failed: %s", e.node_id, e.cause)
            self.emit(
                LogEvent(
                    time.time(),
                    self.run_id,
                    self._next_seq(),
                    "ERROR",
                    f"Run failed because node {e.node_id} failed: {e.cause}",
                    "ENGINE",
                )
            )
            self.emit(RunEndEvent(time.time(), self.run_id, self._next_seq(), StepStatus.FAILURE))
            self._write_final_summary()
        except Exception as e:
            self.logger.exception("Engine Crash")
            self.emit(LogEvent(time.time(), self.run_id, self._next_seq(), "ERROR", f"Engine Crash: {e}", "KERNEL"))
            self.emit(RunEndEvent(time.time(), self.run_id, self._next_seq(), StepStatus.FAILURE))
            
        finally:
            # [FLIGHT RECORDER]
            # If the summary file doesn't exist yet (abort/crash/exception), write it now.
            if not (self.run_dir / "run_summary.json").exists():
                # Determine fallback status
                is_failure = any(s == StepStatus.FAILURE.value for s in self._node_outcomes.values())
                status = "red" if is_failure else "amber"
                reason = "Run terminated abnormally (Abort/Crash)"
                
                self._write_final_summary(status_override=status, reason_override=reason)
            self._snapshot_bridge_log_for_run()
            
            self.shutdown()

    def _resolve_execution_scope(self, target_id: str):
        """
        Calculate execution scope from mission group closure + transitive dependencies.

        Scope policy:
        1. Seed with all nodes in the target's group (captures standalone siblings).
        2. Expand upstream through dependency walk (preserves required ordering/contracts).
        3. Fallback to target-only seed when group metadata is missing/unknown.
        """
        if target_id not in self._universe:
            raise ValueError(f"Target {target_id} not found")

        target_node = self._universe[target_id]
        target_group = getattr(target_node, "group", "unknown")

        scope = set()
        stack: List[str] = []

        if isinstance(target_group, str) and target_group and target_group != "unknown":
            for nid, node in self._universe.items():
                if getattr(node, "group", "unknown") == target_group:
                    scope.add(nid)
                    stack.append(nid)

        if target_id not in scope:
            scope.add(target_id)
            stack.append(target_id)

        while stack:
            curr = stack.pop()
            if curr not in self._universe:
                self.logger.warning(f"Missing dependency: {curr}")
                continue

            node = self._universe[curr]
            for dep in node.dependencies:
                if dep not in scope:
                    scope.add(dep)
                    stack.append(dep)
        self._execution_scope = scope
        self.logger.info(
            "Execution scope resolved for target=%s group=%s nodes=%d ids=%s",
            target_id,
            target_group,
            len(scope),
            ",".join(sorted(scope)),
        )

    def _sever_dependencies(self, node: CodexNode) -> CodexNode:
        """Return a copy of the node with dependencies cleared (Shadow Graph)."""
        return replace(node, dependencies=tuple())

    def _execute_node(self, node_id: str):
        if self._stop_event.is_set():
            return

        node = self._universe[node_id]
        group = node.group
        
        if self._is_completed(node):
            self.emit(StepEndEvent(time.time(), self.run_id, self._next_seq(), node_id, StepStatus.LOADED, 0.0))
            return

        # [UPDATED] Running State & Container Check
        self.emit(StepStartEvent(time.time(), self.run_id, self._next_seq(), node_id))
        self._active_node_ids.add(node_id)
        self._update_container_state(group)

        start_t = time.time()
        
        try:
            inputs = self._gather_inputs(node)
            rt_config = self._merge_runtime_config(node)

            if node.type == NodeType.TOOL:
                meta, data = self._exec_tool(node, inputs, rt_config)
            else:
                meta, data = self._exec_reasoning(node, inputs, rt_config)

            # [FIX] Execution Barrier: If aborted during execution, die silently
            # Prevents a completed zombie thread from reporting success or updating the ledger.
            if self._stop_event.is_set():
                return

            meta_status = str(meta.get("status", "")).lower() if isinstance(meta, dict) else ""
            if meta_status == "failure":
                failure_message = ""
                if isinstance(meta, dict):
                    failure_message = str(meta.get("error") or meta.get("message") or "").strip()
                if not failure_message:
                    failure_message = f"Node {node_id} reported logic failure."
                failure = LogicalFailure(failure_message)
                if isinstance(meta, dict):
                    setattr(failure, "artifact_metadata", dict(meta))
                if data is not None:
                    setattr(failure, "artifact_data", data)
                raise failure
            
            self._write_artifact(node, StepStatus.SUCCESS, meta, data)
            if node.id == "oracle_cp2_emitter":
                self._maybe_write_oracle_observation_report(data)
            duration = time.time() - start_t
            
            # [UPDATED] Success State & Container Check
            self.emit(StepEndEvent(time.time(), self.run_id, self._next_seq(), node_id, StepStatus.SUCCESS, duration))
            self._active_node_ids.discard(node_id)
            self._update_container_state(group)

        except Exception as e:
            duration = time.time() - start_t
            self.emit(LogEvent(time.time(), self.run_id, self._next_seq(), "ERROR", str(e), node_id))
            try:
                failure_meta: Dict[str, Any] = {"error": str(e)}
                failure_data: Any = None
                debug_meta = getattr(e, "artifact_metadata", None)
                debug_data = getattr(e, "artifact_data", None)
                bridge_category = str(getattr(e, "category", "") or "").strip()
                bridge_stage = str(getattr(e, "stage", "") or "").strip()
                bridge_provider = str(getattr(e, "provider", "") or "").strip()
                bridge_details = getattr(e, "details", None)
                if isinstance(debug_meta, dict):
                    failure_meta.update(debug_meta)
                if bridge_category or bridge_stage or bridge_provider or isinstance(bridge_details, dict):
                    bridge_failure: Dict[str, Any] = {"message": str(e)}
                    if bridge_category:
                        bridge_failure["category"] = bridge_category
                    if bridge_stage:
                        bridge_failure["stage"] = bridge_stage
                    if bridge_provider:
                        bridge_failure["provider"] = bridge_provider
                    if isinstance(bridge_details, dict):
                        try:
                            bridge_failure["details"] = json.loads(
                                json.dumps(bridge_details, ensure_ascii=False, default=str)
                            )
                        except Exception:
                            bridge_failure["details"] = {"unserializable": True}
                    failure_meta.setdefault("bridge_failure", bridge_failure)
                if debug_data is not None:
                    failure_data = debug_data
                self._write_artifact(
                    node,
                    StepStatus.FAILURE,
                    failure_meta,
                    failure_data,
                    error=str(e),
                )
            except Exception as artifact_err:
                self.emit(
                    LogEvent(
                        time.time(),
                        self.run_id,
                        self._next_seq(),
                        "ERROR",
                        f"Failure artifact write failed for {node_id}: {artifact_err}",
                        node_id,
                    )
                )
            
            # [UPDATED] Failure State & Container Check
            self.emit(StepEndEvent(time.time(), self.run_id, self._next_seq(), node_id, StepStatus.FAILURE, duration))
            self._active_node_ids.discard(node_id)
            self._update_container_state(group)
            setattr(e, "_engine_node_failure", True)
            setattr(e, "_engine_failed_node_id", node_id)
            raise

    def _exec_tool(self, node: CodexNode, inputs: Dict, config: Dict) -> Tuple[Dict, Any]:
        """Execute Python Tool."""
        is_feed = node.meta.get("is_feed", False)

        if is_feed and self._oracle_mode:
            return self._hydrate_feed_from_truth(node)

        if is_feed and self.execution_mode == ExecutionMode.LAB:
            return self._hydrate_feed(node)
            
        module_path = node.config.get("module")
        if not module_path:
            raise LogicalFailure("Tool missing 'module' config")
            
        mod = importlib.import_module(module_path)
        if not hasattr(mod, "run"):
             raise LogicalFailure(f"Tool module {module_path} missing run() entrypoint")
             
        result = mod.run(config=config, run_dir=str(self.run_dir))

        if isinstance(result, dict):
            metadata = result.get("metadata", {})
            data = result.get("data", result)
        else:
            metadata = {}
            data = result

        output_schema = getattr(node, "output_schema", "text") or "text"
        if output_schema == "isomorphic_v1":
            output_schema = "isomorphic_cp2"
        if output_schema in _STRUCTURED_JSON_OUTPUT_SCHEMAS:
            validation = self._validate_schema_output(node, output_schema, data)
            if not validation.ok:
                failure = LogicalFailure("; ".join(validation.errors))
                if isinstance(metadata, dict):
                    setattr(failure, "artifact_metadata", dict(metadata))
                setattr(failure, "artifact_data", data)
                raise failure
        return metadata, data

    def _exec_reasoning(self, node: CodexNode, inputs: Dict, config: Dict) -> Tuple[Dict, Any]:
        """
        [ACTION]
        - Teleology: Execute reasoning nodes through the bridge while assembling the final prompt, policy contracts, and output-shape guardrails that the model must obey.
        - Mechanism: Layer horizon/context injection, append deterministic audit payloads when needed, enforce Oracle browse limits, load the web-search contract, fall back to the literal SEARCH_REQUIRED system marker when the enabled contract file is missing, then dispatch through the bridge with optional JSON repair.
        - When-needed: Open when tracing why a reasoning prompt picked up SEARCH_REQUIRED, how web_search tool policy is injected into bridge-bound prompts, or where node output_schema starts the JSON guardrail and repair path.
        - Escalates-to: codex/contracts/web_search_enabled.md; codex/contracts/web_search_disabled.md; system/core/bridge.py
        """
        prompt = node.instruction

        # [TEMPORAL] Prompt template substitution — unconditional; no-op for nodes without placeholders
        # Guard: if horizon was never resolved, halt rather than inject a string that will fail ISO validation
        if self._target_time_iso is None and getattr(node, 'output_schema', 'text') in ('isomorphic_cp2',):
            raise LogicalFailure(
                f"Node {node.id} produces CP2 predictions but engine has no resolved target_time_iso. "
                "Set a horizon policy on run config before executing prediction nodes."
            )
        prompt = prompt.replace("{{HORIZON}}", self._horizon_label or "unspecified_horizon")
        prompt = prompt.replace("{{TARGET_TIME}}", self._target_time_iso or "unspecified_target_time")
        prompt = prompt.replace("{{SNAPSHOT_TIME}}", self._run_anchor_iso or "unspecified_snapshot_time")

        if inputs:
            prompt += "\n\n[CONTEXT_INJECTION]\n"
            for dep_id, env in inputs.items():
                env_str = json.dumps(env, separators=(',', ':'), ensure_ascii=False)
                prompt += f"<{dep_id}>\n{env_str}\n</{dep_id}>\n"

        if node.id == "lab_integrity":
            try:
                deterministic_audit = compute_lab_contract_audit(self.artifacts_dir)
                prompt += (
                    "\n\n[DETERMINISTIC_CONTRACT_AUDIT]\n"
                    + json.dumps(deterministic_audit, separators=(",", ":"), ensure_ascii=False)
                )
            except Exception as audit_err:
                self.logger.warning("Failed to compute deterministic contract audit for integrity prompt: %s", audit_err)

        tools = node.execution.get("tools", [])
        # Oracle hard-stop: only the explanatory post-attribution node may browse.
        if self._oracle_mode and "web_search" in tools and node.id != "oracle_explain":
            raise LogicalFailure(
                f"Node {node.id} declares 'web_search' but engine is in Oracle mode. "
                "Only oracle_explain may perform explanatory search after attribution."
            )
        # Inject web search policy contract (toggleable by node.execution.tools)
        _contracts_dir = Path(__file__).parent.parent.parent / "codex" / "contracts"
        _ws_contract_name = "web_search_enabled.md" if "web_search" in tools else "web_search_disabled.md"
        try:
            _ws_contract = (_contracts_dir / _ws_contract_name).read_text(encoding="utf-8")
            prompt += f"\n\n[WEB_SEARCH_POLICY]\n{_ws_contract}"
        except OSError:
            self.logger.warning("Web search contract file missing: %s", _ws_contract_name)
            if "web_search" in tools:
                prompt += "\n[SYSTEM: SEARCH_REQUIRED]\n"
        
        # [NEW] Visual Identity Injection
        lane_colors = self.config.get("ui", {}).get("lane_colors", {})
        color = lane_colors.get(node.lane, "#FFFFFF")
        config["meta"] = {
            "node_id": node.id,
            "lane": node.lane,
            "lane_color": color,
            "session_id": self.run_id,
        }

        # Resolve output_schema with alias coercion
        output_schema = getattr(node, 'output_schema', 'text')
        if output_schema == "isomorphic_v1":
            self.logger.warning("Node %s uses deprecated 'isomorphic_v1'; coercing to 'isomorphic_cp2'", node.id)
            output_schema = "isomorphic_cp2"

        if output_schema != "text":
            prompt = self._inject_json_syntax_guardrail(prompt)

        # --- TEXT MODE: unchanged legacy path ---
        if output_schema == "text":
            self.emit(BridgeStartEvent(time.time(), self.run_id, self._next_seq(), node.id))
            try:
                response_text = self.bridge.manager.ask_ai(
                    prompt, 
                    config=config, 
                    cancel=self._stop_event
                )
            finally:
                self.emit(BridgeEndEvent(time.time(), self.run_id, self._next_seq(), node.id))
            return {"model": config.get("platform", "chatgpt")}, response_text

        # --- JSON MODES: parse, validate, retry ---
        max_attempts = node.execution.get("retries", self.config.get("execution", {}).get("retries", {}).get("value", 1))
        max_attempts = max(1, int(max_attempts))
        errors: List[str] = []
        current_prompt = prompt
        last_invalid_output = ""
        attempt_log: List[Dict[str, Any]] = []
        attempt_sidecars: List[str] = []
        seen_invalid_signatures: Set[Tuple[str, str]] = set()
        base_prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        input_node_ids = sorted(str(k) for k in inputs.keys())

        for attempt in range(max_attempts):
            attempt_idx = attempt + 1
            # Call LLM
            self.emit(BridgeStartEvent(time.time(), self.run_id, self._next_seq(), node.id))
            try:
                response_text = self.bridge.manager.ask_ai(
                    current_prompt,
                    config=config,
                    cancel=self._stop_event
                )
            except Exception as _bridge_err:
                # Bridge was aborted or crashed mid-attempt.
                # Attach whatever forensics have been accumulated from prior attempts
                # so the failure artifact on disk is not an empty "Aborted by Engine Signal".
                _partial_meta: Dict[str, Any] = {
                    "partial_attempt_log": attempt_log,
                    "aborted_on_attempt": attempt_idx,
                    "attempt_sidecars": attempt_sidecars,
                    "output_schema": output_schema,
                    "prompt_sha256": base_prompt_hash,
                    "input_node_ids": input_node_ids,
                }
                _partial_data: Dict[str, Any] = {
                    "attempt_log": attempt_log,
                    "attempt_sidecars": attempt_sidecars,
                }
                bridge_partial = getattr(_bridge_err, "bridge_partial_output", "")
                if isinstance(bridge_partial, str) and bridge_partial.strip():
                    bridge_cleaned = self._strip_json_fences(bridge_partial)
                    bridge_errors = [f"BRIDGE_ABORT: {str(_bridge_err)}"]
                    bridge_sidecar = self._write_json_attempt_sidecar(
                        node_id=node.id,
                        attempt=attempt_idx,
                        prompt=current_prompt,
                        raw_output=bridge_partial,
                        cleaned_output=bridge_cleaned,
                        status="bridge_abort",
                        error_class="BRIDGE_ABORT",
                        errors=bridge_errors,
                    )
                    if bridge_sidecar:
                        attempt_sidecars.append(bridge_sidecar)
                    _partial_meta["bridge_partial_output_sha256"] = hashlib.sha256(
                        bridge_partial.encode("utf-8")
                    ).hexdigest()
                    _partial_meta["bridge_partial_output_snippet"] = self._debug_snippet(bridge_partial)
                    _partial_meta["bridge_partial_output_length"] = len(bridge_partial)
                    _partial_data["bridge_partial_output"] = bridge_partial
                if last_invalid_output:
                    _hash = hashlib.sha256(last_invalid_output.encode("utf-8")).hexdigest()
                    _snippet = self._debug_snippet(last_invalid_output)
                    _partial_meta["last_invalid_output_sha256"] = _hash
                    _partial_meta["last_invalid_output_snippet"] = _snippet
                    _partial_data["last_invalid_output"] = last_invalid_output
                setattr(_bridge_err, "artifact_metadata", _partial_meta)
                setattr(_bridge_err, "artifact_data", _partial_data)
                raise
            finally:
                self.emit(BridgeEndEvent(time.time(), self.run_id, self._next_seq(), node.id))

            # Strip markdown fences
            cleaned = self._strip_json_fences(response_text)
            output_hash = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
            attempt_error_class = ""
            parse_detail: Optional[Dict[str, Any]] = None

            # Bridge extraction placeholder guard.
            # Example failure mode: extraction returns only "Gemini said".
            if self._looks_like_bridge_placeholder(cleaned):
                attempt_error_class = "BRIDGE_EXTRACTION_ERROR"
                errors = [
                    "BRIDGE_EXTRACTION_ERROR: Bridge returned provider label placeholder "
                    f"instead of model output (raw_len={len(response_text)})"
                ]
                last_invalid_output = response_text
                self.logger.warning(
                    "Node %s attempt %d/%d: bridge extraction placeholder detected: %r",
                    node.id, attempt_idx, max_attempts, cleaned,
                )
                sidecar_rel = self._write_json_attempt_sidecar(
                    node_id=node.id,
                    attempt=attempt_idx,
                    prompt=current_prompt,
                    raw_output=response_text,
                    cleaned_output=cleaned,
                    status="failure",
                    error_class=attempt_error_class,
                    errors=errors,
                )
                if sidecar_rel:
                    attempt_sidecars.append(sidecar_rel)
                signature = (attempt_error_class, output_hash)
                stuck_retry = signature in seen_invalid_signatures
                seen_invalid_signatures.add(signature)
                attempt_entry: Dict[str, Any] = {
                    "attempt": attempt_idx,
                    "error_class": attempt_error_class,
                    "output_sha256": output_hash,
                    "output_length": len(response_text),
                    "cleaned_sha256": hashlib.sha256(cleaned.encode("utf-8")).hexdigest(),
                    "cleaned_length": len(cleaned),
                    "errors": errors[:5],
                    "attempt_artifact": sidecar_rel,
                }
                if stuck_retry and attempt_idx < max_attempts:
                    attempt_entry["retry_decision"] = "short_circuit_repeated_failure"
                attempt_log.append(attempt_entry)
                if stuck_retry and attempt_idx < max_attempts:
                    errors = errors + [f"STUCK_RETRY: repeated identical invalid output hash={output_hash}"]
                    self.logger.warning(
                        "Node %s attempt %d/%d: stopping retries early due to repeated extraction placeholder hash=%s",
                        node.id, attempt_idx, max_attempts, output_hash[:12],
                    )
                    break
                if attempt_idx < max_attempts:
                    current_prompt = self._build_correction_prompt(prompt, errors, response_text)
                continue

            # [GUARD] Catch empty bridge extraction before json.loads.
            # Converts opaque "Expecting value ... char 0" into a clear diagnostic.
            if not cleaned.strip():
                attempt_error_class = "EMPTY_EXTRACTION"
                errors = [f"EMPTY_EXTRACTION: Bridge returned empty/whitespace-only response (raw_len={len(response_text)})"]
                last_invalid_output = response_text
                self.logger.warning(
                    "Node %s attempt %d/%d: bridge returned empty extraction (raw_len=%d)",
                    node.id, attempt_idx, max_attempts, len(response_text),
                )
                sidecar_rel = self._write_json_attempt_sidecar(
                    node_id=node.id,
                    attempt=attempt_idx,
                    prompt=current_prompt,
                    raw_output=response_text,
                    cleaned_output=cleaned,
                    status="failure",
                    error_class=attempt_error_class,
                    errors=errors,
                )
                if sidecar_rel:
                    attempt_sidecars.append(sidecar_rel)
                attempt_log.append({
                    "attempt": attempt_idx,
                    "error_class": attempt_error_class,
                    "output_sha256": output_hash,
                    "output_length": len(response_text),
                    "cleaned_sha256": hashlib.sha256(cleaned.encode("utf-8")).hexdigest(),
                    "cleaned_length": len(cleaned),
                    "errors": errors[:5],
                    "attempt_artifact": sidecar_rel,
                })
                if attempt_idx < max_attempts:
                    current_prompt = self._build_correction_prompt(prompt, errors, response_text)
                continue

            # Parse JSON
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError as e:
                attempt_error_class = "JSON_PARSE_ERROR"
                line_raw = getattr(e, "lineno", None)
                col_raw = getattr(e, "colno", None)
                pos_raw = getattr(e, "pos", None)
                line = int(line_raw) if isinstance(line_raw, int) else 0
                column = int(col_raw) if isinstance(col_raw, int) else 0
                char_pos = int(pos_raw) if isinstance(pos_raw, int) else -1
                parse_detail = {
                    "line": line,
                    "column": column,
                    "char": char_pos,
                    "context": self._json_error_context(cleaned, char_pos),
                }
                errors = [f"JSON_PARSE_ERROR: {e} (line={parse_detail['line']}, column={parse_detail['column']}, char={parse_detail['char']})"]
                last_invalid_output = response_text
                self.logger.warning(
                    "Node %s attempt %d/%d: JSON parse failed: %s",
                    node.id, attempt_idx, max_attempts, e
                )
                sidecar_rel = self._write_json_attempt_sidecar(
                    node_id=node.id,
                    attempt=attempt_idx,
                    prompt=current_prompt,
                    raw_output=response_text,
                    cleaned_output=cleaned,
                    status="failure",
                    error_class=attempt_error_class,
                    errors=errors,
                    parse_detail=parse_detail,
                )
                if sidecar_rel:
                    attempt_sidecars.append(sidecar_rel)
                signature = (attempt_error_class, output_hash)
                stuck_retry = signature in seen_invalid_signatures
                seen_invalid_signatures.add(signature)
                attempt_entry: Dict[str, Any] = {
                    "attempt": attempt_idx,
                    "error_class": attempt_error_class,
                    "output_sha256": output_hash,
                    "output_length": len(response_text),
                    "cleaned_sha256": hashlib.sha256(cleaned.encode("utf-8")).hexdigest(),
                    "cleaned_length": len(cleaned),
                    "errors": errors[:5],
                    "json_error": parse_detail,
                    "attempt_artifact": sidecar_rel,
                }
                if stuck_retry and attempt_idx < max_attempts:
                    attempt_entry["retry_decision"] = "short_circuit_repeated_failure"
                attempt_log.append(attempt_entry)
                if stuck_retry and attempt_idx < max_attempts:
                    errors = errors + [f"STUCK_RETRY: repeated identical invalid output hash={output_hash}"]
                    self.logger.warning(
                        "Node %s attempt %d/%d: stopping retries early due to repeated invalid output hash=%s",
                        node.id,
                        attempt_idx,
                        max_attempts,
                        output_hash[:12],
                    )
                    break
                if attempt_idx < max_attempts:
                    current_prompt = self._build_correction_prompt(prompt, errors, response_text)
                continue

            # Schema validation / deterministic JSON contract checks
            if output_schema in _STRUCTURED_JSON_OUTPUT_SCHEMAS:
                if output_schema == "isomorphic_cp2":
                    parsed = self._audit_cp2_predictions(parsed)
                result = self._validate_schema_output(node, output_schema, parsed)
                if not result.ok:
                    attempt_error_class = "SCHEMA_VALIDATION"
                    errors = list(result.errors)
                    last_invalid_output = response_text
                    self.logger.warning(
                        "Node %s attempt %d/%d: schema validation failed: %s",
                        node.id, attempt_idx, max_attempts, errors
                    )
                    sidecar_rel = self._write_json_attempt_sidecar(
                        node_id=node.id,
                        attempt=attempt_idx,
                        prompt=current_prompt,
                        raw_output=response_text,
                        cleaned_output=cleaned,
                        status="failure",
                        error_class=attempt_error_class,
                        errors=errors,
                    )
                    if sidecar_rel:
                        attempt_sidecars.append(sidecar_rel)
                    signature = (attempt_error_class, output_hash)
                    stuck_retry = signature in seen_invalid_signatures
                    seen_invalid_signatures.add(signature)
                    attempt_entry = {
                        "attempt": attempt_idx,
                        "error_class": attempt_error_class,
                        "output_sha256": output_hash,
                        "output_length": len(response_text),
                        "cleaned_sha256": hashlib.sha256(cleaned.encode("utf-8")).hexdigest(),
                        "cleaned_length": len(cleaned),
                        "errors": errors[:5],
                        "attempt_artifact": sidecar_rel,
                    }
                    if stuck_retry and attempt_idx < max_attempts:
                        attempt_entry["retry_decision"] = "short_circuit_repeated_failure"
                    attempt_log.append(attempt_entry)
                    if stuck_retry and attempt_idx < max_attempts:
                        errors = errors + [f"STUCK_RETRY: repeated identical invalid output hash={output_hash}"]
                        self.logger.warning(
                            "Node %s attempt %d/%d: stopping retries early due to repeated schema-failing output hash=%s",
                            node.id,
                            attempt_idx,
                            max_attempts,
                            output_hash[:12],
                        )
                        break
                    if attempt_idx < max_attempts:
                        current_prompt = self._build_correction_prompt(
                            prompt, errors, response_text
                        )
                    continue

            success_sidecar = self._write_json_attempt_sidecar(
                node_id=node.id,
                attempt=attempt_idx,
                prompt=current_prompt,
                raw_output=response_text,
                cleaned_output=cleaned,
                status="success",
                error_class="OK",
                errors=[],
            )
            if success_sidecar:
                attempt_sidecars.append(success_sidecar)

            # Success
            self.logger.info(
                "Node %s: JSON/%s validation passed on attempt %d/%d",
                node.id, output_schema, attempt_idx, max_attempts
            )
            return {"model": config.get("platform", "chatgpt")}, parsed

        # All attempts exhausted — build forensic failure with full audit trail
        attempts_executed = len(attempt_log)
        error_summary = "; ".join(errors[:10])
        failure = LogicalFailure(
            f"Node {node.id} failed JSON/schema validation after "
            f"{attempts_executed}/{max_attempts} attempts: {error_summary}"
        )
        failure_meta: Dict[str, Any] = {
            "validation_errors": errors[:10],
            "validation_attempts_configured": max_attempts,
            "validation_attempts_executed": attempts_executed,
            "attempt_log": attempt_log,
            "attempt_sidecars": attempt_sidecars,
            "prompt_sha256": base_prompt_hash,
            "input_node_ids": input_node_ids,
            "output_schema": output_schema,
        }
        failure_data: Any = {
            "attempt_log": attempt_log,
            "attempt_sidecars": attempt_sidecars,
            "input_node_ids": input_node_ids,
        }
        if last_invalid_output:
            last_output_hash = hashlib.sha256(last_invalid_output.encode("utf-8")).hexdigest()
            last_output_snippet = self._debug_snippet(last_invalid_output)
            failure_meta["last_invalid_output_sha256"] = last_output_hash
            failure_meta["last_invalid_output_snippet"] = last_output_snippet
            failure_data["last_invalid_output"] = last_invalid_output
        setattr(failure, "artifact_metadata", failure_meta)
        setattr(failure, "artifact_data", failure_data)
        raise failure

    # --- Phase 3 Helper Methods ---

    @staticmethod
    def _strip_json_fences(text: str) -> str:
        """Strip markdown JSON fences if the entire response is a single fenced block."""
        text = text.strip()
        if text.startswith("```json") and text.endswith("```"):
            text = re.sub(r'^```json\s*\n?', '', text)
            text = re.sub(r'\n?```\s*$', '', text)
        elif text.startswith("```") and text.endswith("```"):
            text = re.sub(r'^```\s*\n?', '', text)
            text = re.sub(r'\n?```\s*$', '', text)
        return text

    @staticmethod
    def _debug_snippet(text: str, limit: int = 2500) -> str:
        """Return a bounded tail snippet for forensic metadata."""
        if len(text) <= limit:
            return text
        return f"[TRUNCATED len={len(text)}]\n...{text[-limit:]}"

    @staticmethod
    def _json_error_context(text: str, pos: int, window: int = 120) -> str:
        """Extract a small context window around a JSON parse error position."""
        if pos < 0:
            return ""
        start = max(0, pos - window)
        end = min(len(text), pos + window)
        return text[start:end]

    @staticmethod
    def _looks_like_bridge_placeholder(text: str) -> bool:
        """Detect provider-label extraction stubs such as 'Gemini said'."""
        normalized = re.sub(r"\s+", " ", (text or "")).strip().lower()
        return bool(re.fullmatch(r"(gemini|chatgpt)\s+said:?", normalized))

    @staticmethod
    def _inject_json_syntax_guardrail(prompt: str) -> str:
        """Append an engine-level JSON syntax contract to every JSON-mode prompt."""
        marker = "[ENGINE_JSON_SYNTAX_GUARDRAIL]"
        if marker in prompt:
            return prompt
        guardrail = (
            f"{marker}\n"
            "- Return exactly ONE JSON object and nothing else.\n"
            "- Output must parse with json.loads() without preprocessing.\n"
            "- Never use bare double quotes for emphasis inside JSON string values.\n"
            "- Use single quotes for emphasis (example: 'cost-push', 'Whale').\n"
            "- If a literal double quote character is required inside a string, escape it as \\\".\n"
            "- Do not add trailing commas."
        )
        return f"{prompt}\n\n{guardrail}"

    def _write_json_attempt_sidecar(
        self,
        node_id: str,
        attempt: int,
        prompt: str,
        raw_output: str,
        cleaned_output: str,
        status: str,
        error_class: str,
        errors: List[str],
        parse_detail: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Persist a per-attempt JSON forensic payload and return repo-relative path."""
        debug_dir = self.run_dir / "debug" / "json_attempts"
        debug_dir.mkdir(parents=True, exist_ok=True)
        final = debug_dir / f"{node_id}.attempt_{attempt:02d}.json"
        tmp = debug_dir / f"{node_id}.attempt_{attempt:02d}.tmp"
        payload: Dict[str, Any] = {
            "timestamp_iso": datetime.now(timezone.utc).isoformat(),
            "node_id": node_id,
            "attempt": int(attempt),
            "status": status,
            "error_class": error_class,
            "errors": list(errors[:10]),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "prompt_length": len(prompt),
            "prompt_snippet": self._debug_snippet(prompt, limit=4000),
            "output_sha256": hashlib.sha256(raw_output.encode("utf-8")).hexdigest(),
            "output_length": len(raw_output),
            "output_text": raw_output,
            "cleaned_sha256": hashlib.sha256(cleaned_output.encode("utf-8")).hexdigest(),
            "cleaned_length": len(cleaned_output),
            "cleaned_text": cleaned_output,
        }
        if parse_detail:
            payload["json_error"] = parse_detail
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"), ensure_ascii=False)
        tmp.replace(final)
        try:
            return str(final.relative_to(self.run_dir))
        except Exception:
            return str(final)

    def _validate_schema_output(self, node: CodexNode, output_schema: str, parsed: Any) -> ValidationResult:
        """Dispatch CP validation based on output_schema."""
        if output_schema == "isomorphic_cp1":
            return validate_cp1(parsed)
        elif output_schema == "json":
            if node.id == "lab_cross_corr_v1":
                return validate_cross_corr_v1(parsed)
            if node.id == "lab_cross_corr_v2":
                return validate_cross_corr_v2(parsed)
            return ValidationResult.success()
        elif output_schema == "isomorphic_cp2":
            cross_corr_v2_targets = self._extract_cross_corr_v2_targets()
            cp2_result = validate_cp2(
                parsed,
                self._subject_run_dir,
                cross_corr_v2_targets=cross_corr_v2_targets,
                expected_snapshot_time=self._run_anchor_iso,
                expected_target_time_iso=self._target_time_iso,
            )
            if not self._oracle_mode:
                return cp2_result

            evidence = (
                parsed.get("evidence_dictionary", [])
                if isinstance(parsed, dict)
                else []
            )
            golden_result = validate_golden_ids(evidence, self._subject_run_dir)
            oracle_meta_result = ValidationResult.success()
            if node.id == "oracle_cp2_emitter":
                oracle_meta_result = validate_oracle_cp2_meta(parsed)
            if cp2_result.ok and golden_result.ok and oracle_meta_result.ok:
                return ValidationResult.success()
            return ValidationResult.failure(
                cp2_result.errors + golden_result.errors + oracle_meta_result.errors
            )
        elif output_schema == "schema_prediction_reconciliation":
            return validate_prediction_reconciliation(parsed)
        elif output_schema == "schema_realized_hindsight_brief":
            return validate_realized_hindsight_brief(parsed)
        elif output_schema == "schema_cp2_critique":
            return validate_cp2_critique(parsed)
        return ValidationResult.success()

    @staticmethod
    def _build_correction_prompt(original_prompt: str, errors: List[str], invalid_output: str) -> str:
        """Build retry prompt with error list and (possibly truncated) prior output."""
        MAX_OUTPUT_CHARS = 8192
        if len(invalid_output) > MAX_OUTPUT_CHARS:
            truncation_hash = hashlib.sha256(invalid_output.encode()).hexdigest()[:12]
            invalid_output = (
                f"[TRUNCATED — SHA256 prefix: {truncation_hash}]\n"
                f"...{invalid_output[-MAX_OUTPUT_CHARS:]}"
            )

        error_list = "\n".join(f"- {e}" for e in errors)
        return (
            f"{original_prompt}\n\n"
            f"[SYSTEM_CORRECTION]\n"
            f"Your previous response failed validation with these errors:\n{error_list}\n\n"
            f"Your previous (invalid) response was:\n{invalid_output}\n\n"
            f"Fix the errors and return valid JSON only.\n"
            f"CRITICAL: Escape any internal double quotes inside JSON strings as \\\".\n"
            f"CRITICAL: For emphasis inside strings, use single quotes (example: 'cost-push')."
        )

    def _hydrate_feed(self, node: CodexNode) -> Tuple[Dict, Any]:
        """Mock feed from historical artifact."""
        source = self.feed_source_run_id or self.source_run_id
        if not source:
             raise LogicalFailure("LAB mode requires source_run_id or feed_source_run_id")

        src_path = self.run_dir.parent / source / "artifacts" / f"{node.id}.json"
        if not src_path.exists():
            raise LogicalFailure(f"Feed artifact {node.id} missing in source {source}")

        with open(src_path, "r") as f:
            env = json.load(f)

        meta = env.get("metadata", {})
        meta["hydrated_from"] = source
        return meta, env.get("data")

    def _hydrate_feed_from_truth(self, node: CodexNode) -> Tuple[Dict, Any]:
        """
        Oracle-mode feed hydration: read realized truth-side feeds from the paired truth run.
        """
        if not self._truth_run_dir:
            raise LogicalFailure("Oracle v1 feed hydration requires oracle_truth_run_dir")
        src_path = self._truth_run_dir / "artifacts" / f"{node.id}.json"
        if not src_path.exists():
            raise LogicalFailure(
                f"Oracle truth feed artifact '{node.id}' missing in oracle_truth_run_dir={self._truth_run_dir}"
            )
        with open(src_path, "r") as f:
            env = json.load(f)
        meta = env.get("metadata", {})
        meta["hydrated_from_truth"] = str(self._truth_run_dir)
        return meta, env.get("data")

    def _hydrate_feed_from_subject(self, node: CodexNode) -> Tuple[Dict, Any]:
        """
        Backward-compatible subject-side feed loader.

        Oracle v1 does not use this for normal feed hydration; subject-side raw reads must flow
        through dedicated Oracle tools/helpers.
        """
        src_path = self._subject_run_dir / "artifacts" / f"{node.id}.json"
        if not src_path.exists():
            raise LogicalFailure(
                f"Oracle subject feed artifact '{node.id}' missing in subject_run_dir={self._subject_run_dir}"
            )
        with open(src_path, "r", encoding="utf-8") as f:
            env = json.load(f)
        meta = env.get("metadata", {})
        meta["hydrated_from_subject"] = str(self._subject_run_dir)
        return meta, env.get("data")

    def _gather_inputs(self, node: CodexNode) -> Dict[str, Any]:
        inputs = {}
        for dep_id in node.dependencies:
            path = self.artifacts_dir / f"{dep_id}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    envelope = json.load(f)
                if node.type != NodeType.TOOL and not self._oracle_mode and isinstance(envelope, dict):
                    envelope = compress_reasoning_feed_envelope(self.root_dir, dep_id, envelope)
                inputs[dep_id] = envelope
        return inputs

    def _merge_runtime_config(self, node: CodexNode) -> Dict[str, Any]:
        """Merge global bridge config + node config."""
        base = self.config.get("bridge", {}).copy()
        node_cfg = node.config.copy()
        node_cfg.update(node.execution)
        node_cfg["platform"] = node.platform
        base.update(node_cfg)
        if node.type == NodeType.TOOL:
            runtime_cfg = base.get("runtime")
            runtime = dict(runtime_cfg) if isinstance(runtime_cfg, dict) else {}
            runtime.setdefault("run_id", self.run_id)
            runtime.setdefault("time_anchor", self._run_anchor_iso)
            runtime.setdefault("as_of", self._run_anchor_iso)
            runtime.setdefault("effective_date", self._run_anchor_iso)
            if self._target_time_iso:
                runtime.setdefault("target_time_iso", self._target_time_iso)
            if self._horizon_label:
                runtime.setdefault("horizon_label", self._horizon_label)
            if self._oracle_mode:
                runtime.setdefault("oracle_mode", True)
                runtime.setdefault("oracle_subject_run_dir", str(self._subject_run_dir))
                if self._truth_run_dir is not None:
                    runtime.setdefault("oracle_truth_run_dir", str(self._truth_run_dir))
                if self.source_run_id:
                    runtime.setdefault("oracle_subject_run_id", self.source_run_id)
                if self.feed_source_run_id:
                    runtime.setdefault("oracle_truth_run_id", self.feed_source_run_id)
            base["runtime"] = runtime
        merged, _route_name = merge_bridge_config_with_route(base, default_route="engine_node")
        return merged

    def shutdown(self):
        """
        [ACTION]
        - Teleology: Perform non-destructive cleanup of engine resources.
        - Mechanism: Signal stop event and close bridge resources without killing the browser by default.
        - Guarantee: Engine enters a stopped state and bridge resources are released best-effort.
        - Fails: None.
        - When-needed: Open when checking whether teardown stops engine work while preserving the shared browser process.
        - Escalates-to: system/core/bridge.py::close; system/core/bridge.py::snapshot_bridge_events_for_session
        
        """
        self._stop_event.set()
        try:
            self.bridge.close(terminate_browser=False)
        except Exception:
            pass

    def _snapshot_bridge_log_for_run(self) -> None:
        """Persist bridge events for this run next to engine.log."""
        try:
            from system.core.bridge import snapshot_bridge_events_for_session
            out_path = self.run_dir / "observe_bridge_log.jsonl"
            event_count = snapshot_bridge_events_for_session(
                session_id=self.run_id,
                out_path=out_path,
            )
            if event_count > 0:
                self.logger.info("Wrote observe_bridge_log.jsonl (%s events)", event_count)
        except Exception:
            pass
