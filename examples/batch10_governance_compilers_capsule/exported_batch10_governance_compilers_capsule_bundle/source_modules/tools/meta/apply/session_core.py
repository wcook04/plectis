"""
[PURPOSE]
- Teleology: Provide the shared dependency-wave scheduler used by observe/apply session runtimes so node execution semantics live in one minimal core.
- Mechanism: Define session node/result data carriers, normalize node maps, compute dependency waves, dispatch one wave with thread-pool execution, and aggregate final run state.

[INTERFACE]
- Exports: SessionNodeStatus, DependencyFailurePolicy, SessionNodeSpec, SessionWave, SessionNodeResult, SessionRunResult, build_nodes, compute_waves, initialize_states, dispatch_wave, run.
- Reads: Caller-supplied SessionNodeSpec mappings, dependency ids, executor results, stop events, and checkpoint callbacks.
- Writes: Mutates caller-owned node_states mappings during dispatch and returns a SessionRunResult snapshot at the end of run().

[FLOW]
- Orders: build_nodes() validates and keys the node roster -> compute_waves() derives dependency-ready batches -> run() initializes state and records per-node results -> dispatch_wave() advances one ready wave and checkpoints transitions.
- When-needed: Open when an observe/apply runtime needs the underlying dependency-wave execution semantics, not the higher artifact-writing orchestration layer.
- Escalates-to: tools/meta/apply/observe_session.py::MetaSessionOrchestratorImpl.run; tools/meta/apply/observe_session_runner.py::run_session_once.
- Navigation-group: observe_apply.

[DEPENDENCIES]
- Couples: tools/meta/apply/observe_session.py materializes these node and wave semantics into observe-session checkpointing, artifact persistence, and continuation state.
- Couples: tools/meta/apply/observe_session_runner.py is the common CLI/runtime entrypoint that feeds plan-derived node graphs into this scheduler through the orchestrator.

[CONSTRAINTS]
- Guarantee: Ready-node ordering is deterministic within each wave because compute_waves() sorts node ids before dispatch.
- Orders: Dependency failures only change downstream handling through DependencyFailurePolicy; this core does not invent higher-level recovery paths.
- Non-goal: This module does not build prompts, persist artifacts, or interpret observe-plan semantics beyond generic dependency execution.
"""
from __future__ import annotations

import concurrent.futures
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Sequence, Tuple


class SessionNodeStatus(str, Enum):
    """[ROLE]
    - Teleology: Represent the lifecycle states a session node can occupy during scheduler execution.
    - Ownership: Owned by the scheduler; callers read values but do not mutate the enum.
    - Mutability: Immutable enum members.
    - Concurrency: Safe to read from any thread; enum members are module-level constants.
    """
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    ABORTED = "aborted"


class DependencyFailurePolicy(str, Enum):
    """[ROLE]
    - Teleology: Express what the scheduler should do with downstream nodes when an upstream node fails.
    - Ownership: Owned by the caller; passed into dispatch_wave and run to govern abort/skip/continue behavior.
    - Mutability: Immutable enum members.
    - Concurrency: Safe to read from any thread; enum members are module-level constants.
    """
    ABORT_SESSION = "abort_session"
    SKIP_DOWNSTREAM = "skip_downstream"
    CONTINUE_ANYWAY = "continue_anyway"


@dataclass(init=False)
class SessionNodeSpec:
    """[ROLE]
    - Teleology: Carry the identity, role, dependency edges, and mutable work-tracking references for one session node.
    - Ownership: Created by callers and handed to the scheduler; the scheduler mutates work_ref, response_ref, output_ref, next_action, and quality_meta during execution.
    - Mutability: Mutable; the scheduler populates ref fields as execution progresses.
    - Concurrency: Not thread-safe for concurrent field mutation; the scheduler controls write ordering per node.
    """
    node_id: str
    role: Any
    depends_on: Tuple[str, ...]
    payload: Dict[str, Any]
    work_ref: Optional[str] = None
    response_ref: Optional[str] = None
    output_ref: Optional[str] = None
    next_action: Optional[str] = None
    quality_meta: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        *,
        node_id: str,
        role: Any,
        depends_on: Tuple[str, ...],
        payload: Optional[Dict[str, Any]] = None,
        group_dict: Optional[Dict[str, Any]] = None,
        work_ref: Optional[str] = None,
        dump_ref: Optional[str] = None,
        response_ref: Optional[str] = None,
        output_ref: Optional[str] = None,
        next_action: Optional[str] = None,
        quality_meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """[ACTION]
        - Teleology: Initialize a SessionNodeSpec from named keyword arguments, normalizing payload vs group_dict and work_ref vs dump_ref aliases.
        - Guarantee: After return, self.payload is a fresh dict and self.work_ref/self.depends_on are set from the canonical argument names.
        - Fails: None.
        """
        self.node_id = node_id
        self.role = role
        self.depends_on = tuple(depends_on)
        self.payload = dict(payload if payload is not None else group_dict or {})
        self.work_ref = work_ref if work_ref is not None else dump_ref
        self.response_ref = response_ref
        self.output_ref = output_ref
        self.next_action = next_action
        self.quality_meta = quality_meta

    @property
    def group_dict(self) -> Dict[str, Any]:
        """[ACTION]
        - Teleology: Expose the payload dict under the legacy group_dict alias so existing call sites do not need to be migrated.
        - Guarantee: Returns self.payload.
        - Fails: None.
        """
        return self.payload

    @group_dict.setter
    def group_dict(self, value: Dict[str, Any]) -> None:
        """[ACTION]
        - Teleology: Accept writes to the group_dict alias by routing them to self.payload.
        - Guarantee: self.payload equals value after assignment.
        - Fails: None.
        """
        self.payload = value

    @property
    def dump_ref(self) -> Optional[str]:
        """[ACTION]
        - Teleology: Expose work_ref under the legacy dump_ref alias so existing probe code does not need migration.
        - Guarantee: Returns self.work_ref.
        - Fails: None.
        """
        return self.work_ref

    @dump_ref.setter
    def dump_ref(self, value: Optional[str]) -> None:
        """[ACTION]
        - Teleology: Accept writes to the dump_ref alias by routing them to self.work_ref.
        - Guarantee: self.work_ref equals value after assignment.
        - Fails: None.
        """
        self.work_ref = value


@dataclass(frozen=True)
class SessionWave:
    """[ROLE]
    - Teleology: Represent one dependency-ready batch of nodes that can execute concurrently within a session run.
    - Ownership: Produced by compute_waves() and consumed by dispatch_wave() and run().
    - Mutability: Immutable frozen dataclass.
    - Concurrency: Safe to share across threads because it is frozen.
    """
    wave_index: int
    node_ids: Tuple[str, ...]


@dataclass(frozen=True)
class SessionNodeResult:
    """[ROLE]
    - Teleology: Carry the terminal outcome, artifact paths, and next-action hint for one executed session node.
    - Ownership: Produced by the executor callable and stored in node_results by run().
    - Mutability: Immutable frozen dataclass.
    - Concurrency: Safe to share across threads because it is frozen.
    """
    node_id: str
    status: SessionNodeStatus
    response_path: Optional[str] = None
    output_path: Optional[str] = None
    next_action: Optional[str] = None
    detail: Optional[str] = None


@dataclass(frozen=True)
class SessionRunResult:
    """[ROLE]
    - Teleology: Aggregate the waves, terminal node states, and per-node results produced by a complete session run.
    - Ownership: Produced by run() and returned to the caller as the authoritative run summary.
    - Mutability: Immutable frozen dataclass; the inner dicts are shallow copies.
    - Concurrency: Safe to read from any thread after run() returns.
    """
    waves: Tuple[SessionWave, ...]
    node_states: Dict[str, SessionNodeStatus]
    node_results: Dict[str, SessionNodeResult]


SessionNodeExecutor = Callable[[SessionNodeSpec], SessionNodeResult]


def build_nodes(*, specs: Sequence[SessionNodeSpec]) -> dict[str, SessionNodeSpec]:
    """
    [ACTION]
    - Teleology: Normalize a session-node roster into an id-addressable execution map before wave planning or dispatch.
    - Mechanism: Strip each node_id, reject empties and duplicates, and return a dict keyed by the canonical node id.
    - Reads: specs.
    - Guarantee: Returns one SessionNodeSpec per unique non-empty node id, keyed by that id.
    - Fails: Raises ValueError when a node id is empty or duplicated.
    - When-needed: Open when a caller needs the validation boundary that turns a list of SessionNodeSpec records into the scheduler's canonical node map.
    - Escalates-to: tools/meta/apply/observe_session.py::MetaSessionOrchestratorImpl.run; tools/meta/apply/observe_session_runner.py::run_session_once.
    - Navigation-group: observe_apply.
    """
    nodes: dict[str, SessionNodeSpec] = {}
    for spec in specs:
        node_id = str(spec.node_id or "").strip()
        if not node_id:
            raise ValueError("Session node ids must be non-empty.")
        if node_id in nodes:
            raise ValueError(f"Duplicate session node id: {node_id}")
        nodes[node_id] = spec
    return nodes


def compute_waves(*, nodes: Mapping[str, SessionNodeSpec]) -> tuple[SessionWave, ...]:
    """
    [ACTION]
    - Teleology: Derive deterministic dependency waves so callers know which session nodes can execute in parallel.
    - Mechanism: Repeatedly collect sorted nodes whose dependencies are all completed, emit one SessionWave per pass, and fail if no progress is possible.
    - Reads: nodes and each spec's depends_on tuple.
    - Guarantee: Returns waves in dependency order with lexicographically sorted node ids inside each wave.
    - Fails: Raises ValueError when dependencies are cyclic or reference nodes that can never become ready.
    - When-needed: Open when debugging dependency cycles, missing prerequisites, or unexpected wave fan-out in an observe/apply session DAG.
    - Escalates-to: tools/meta/apply/observe_session.py::MetaSessionOrchestratorImpl.run; tools/meta/apply/observe_session_runner.py::run_session_once.
    - Navigation-group: observe_apply.
    """
    waves: list[SessionWave] = []
    remaining = set(nodes.keys())
    completed: set[str] = set()
    wave_index = 0

    while remaining:
        wave_nodes = sorted(
            node_id
            for node_id in remaining
            if all(dependency in completed for dependency in nodes[node_id].depends_on)
        )
        if not wave_nodes:
            raise ValueError("Dependency cycle or missing dependencies detected.")
        waves.append(SessionWave(wave_index=wave_index, node_ids=tuple(wave_nodes)))
        remaining.difference_update(wave_nodes)
        completed.update(wave_nodes)
        wave_index += 1

    return tuple(waves)


def initialize_states(*, nodes: Mapping[str, SessionNodeSpec]) -> dict[str, SessionNodeStatus]:
    """[ACTION]
    - Teleology: Seed the mutable node-state map used by dispatch_wave() with PENDING for every node before any wave executes.
    - Guarantee: Returns a fresh dict mapping every node id in nodes to SessionNodeStatus.PENDING.
    - Fails: None.
    """
    return {node_id: SessionNodeStatus.PENDING for node_id in nodes}


def dispatch_wave(
    *,
    wave: SessionWave,
    nodes: Mapping[str, SessionNodeSpec],
    node_states: MutableMapping[str, SessionNodeStatus],
    executor: SessionNodeExecutor,
    checkpoint: Callable[[str], None],
    stop_event: threading.Event,
    max_workers: int,
    dep_failure_policy: DependencyFailurePolicy,
) -> None:
    """
    [ACTION]
    - Teleology: Execute one dependency-ready wave and project executor outcomes back onto shared node state.
    - Mechanism: Checkpoint dispatch start, skip or abort nodes whose dependencies or stop policy block them, submit ready nodes to a ThreadPoolExecutor, fold results/exceptions into node_states, and checkpoint completion.
    - Reads: wave, nodes, node_states, executor, stop_event, and dep_failure_policy.
    - Writes: Mutates node_states in place and calls checkpoint() for wave and node transitions.
    - Guarantee: Every node in the wave reaches a terminal state or running/result transition consistent with dependency and abort policy before the wave completes.
    - Fails: None — executor exceptions are converted into SessionNodeResult failure or aborted status.
    - When-needed: Open when tracing per-wave state transitions, dependency-failure handling, or abort propagation inside the shared session scheduler.
    - Escalates-to: tools/meta/apply/observe_session.py::MetaSessionOrchestratorImpl.run; tools/meta/apply/observe_session_runner.py::run_session_once.
    - Navigation-group: observe_apply.
    """
    checkpoint(f"wave:{wave.wave_index}:dispatch")

    futures: dict[concurrent.futures.Future[SessionNodeResult], str] = {}
    should_abort_session = False
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        for node_id in wave.node_ids:
            if stop_event.is_set() and dep_failure_policy == DependencyFailurePolicy.ABORT_SESSION:
                node_states[node_id] = SessionNodeStatus.ABORTED
                checkpoint(node_id)
                continue

            spec = nodes[node_id]
            dependencies_satisfied = all(
                node_states.get(dependency) == SessionNodeStatus.SUCCESS
                for dependency in spec.depends_on
            )
            if not dependencies_satisfied:
                node_states[node_id] = SessionNodeStatus.SKIPPED
                checkpoint(node_id)
                continue

            node_states[node_id] = SessionNodeStatus.RUNNING
            futures[pool.submit(executor, spec)] = node_id

        for future in concurrent.futures.as_completed(futures):
            node_id = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = SessionNodeResult(
                    node_id=node_id,
                    status=(
                        SessionNodeStatus.ABORTED
                        if stop_event.is_set()
                        else SessionNodeStatus.FAILURE
                    ),
                    detail=str(exc),
                )

            node_states[node_id] = result.status
            if result.status == SessionNodeStatus.FAILURE and dep_failure_policy == DependencyFailurePolicy.ABORT_SESSION:
                should_abort_session = True
            checkpoint(node_id)

    if should_abort_session and dep_failure_policy == DependencyFailurePolicy.ABORT_SESSION:
        stop_event.set()

    checkpoint(f"wave:{wave.wave_index}:complete")


def run(
    *,
    nodes: Mapping[str, SessionNodeSpec],
    executor: SessionNodeExecutor,
    checkpoint: Callable[[str], None],
    stop_event: threading.Event,
    max_workers: int,
    dep_failure_policy: DependencyFailurePolicy,
) -> SessionRunResult:
    """
    [ACTION]
    - Teleology: Run the full session-core scheduler from wave computation through aggregated node results.
    - Mechanism: Compute dependency waves, initialize node states, wrap the executor to capture SessionNodeResult records, dispatch each wave until completion or abort, then finalize pending nodes when abort policy stops the session.
    - Reads: nodes, executor, checkpoint, stop_event, max_workers, and dep_failure_policy.
    - Guarantee: Returns SessionRunResult containing the computed waves, final node states, and every recorded node result produced by the wrapped executor.
    - Fails: Propagates compute_waves() validation failures before any dispatch occurs.
    - When-needed: Open when a caller needs the authoritative session-core execution loop before stepping up to observe-session artifact orchestration.
    - Escalates-to: tools/meta/apply/observe_session.py::MetaSessionOrchestratorImpl.run; tools/meta/apply/observe_session_runner.py::run_session_once.
    - Navigation-group: observe_apply.
    """
    waves = compute_waves(nodes=nodes)
    node_states = initialize_states(nodes=nodes)
    node_results: dict[str, SessionNodeResult] = {}
    results_lock = threading.Lock()

    def _recording_executor(spec: SessionNodeSpec) -> SessionNodeResult:
        result = executor(spec)
        with results_lock:
            node_results[spec.node_id] = result
        return result

    for wave in waves:
        if stop_event.is_set() and dep_failure_policy == DependencyFailurePolicy.ABORT_SESSION:
            break
        dispatch_wave(
            wave=wave,
            nodes=nodes,
            node_states=node_states,
            executor=_recording_executor,
            checkpoint=checkpoint,
            stop_event=stop_event,
            max_workers=max_workers,
            dep_failure_policy=dep_failure_policy,
        )

    if stop_event.is_set() and dep_failure_policy == DependencyFailurePolicy.ABORT_SESSION:
        for node_id, status in list(node_states.items()):
            if status == SessionNodeStatus.PENDING:
                node_states[node_id] = SessionNodeStatus.ABORTED
                checkpoint(node_id)

    return SessionRunResult(
        waves=waves,
        node_states=dict(node_states),
        node_results=dict(node_results),
    )
