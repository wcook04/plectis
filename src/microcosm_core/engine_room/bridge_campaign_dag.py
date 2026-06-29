"""
Public-safe Bridge Campaign DAG validation capsule.

This is a source-faithful refactor of the macro bridge campaign contract layer:
`tools/meta/bridge/bridge_campaign.py` plus the provider ceiling rule from
`tools/meta/bridge/dispatch_validator.py`. It is deliberately a validator, not a
dispatcher. It reads a small public campaign spec, proves the fan-in graph is
well formed, and rejects cycles, dangling synthesis nodes, and provider
over-parallelism.

[PURPOSE]
- Teleology: Exposes `microcosm_core.engine_room.bridge_campaign_dag` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: SCHEMA_VERSION, ORGAN_ID, SOURCE_REFS, SOURCE_TO_TARGET_RELATION, VALID_NODE_ROLES, VALID_INPUT_MODES, VALID_PACKET_SCHEMAS, SAFE_PARALLELISM, CAMPAIGN_ID_RE, CLAIM_CEILING, ANTI_CLAIMS, Decision, ValidationResult, validate_campaign, load_campaign, validate_campaign_file, validate_fixture_dir, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: None beyond the Python standard library and local package imports.
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "engine_room_bridge_campaign_dag_v1"
ORGAN_ID = "engine_room_bridge_campaign_dag"
SOURCE_REFS = (
    "tools/meta/bridge/bridge_campaign.py",
    "tools/meta/bridge/dispatch_validator.py",
    "tools/meta/bridge/provider_capabilities.py",
)
SOURCE_TO_TARGET_RELATION = "source_faithful_public_refactor"
VALID_NODE_ROLES = {"probe", "reducer", "synthesis"}
VALID_INPUT_MODES = {"receipts_only", "receipts_plus_selected_raw", "raw_required"}
VALID_PACKET_SCHEMAS = {"v1_receipts_navigational"}
SAFE_PARALLELISM = {"chatgpt": 8, "claude": 2, "gemini": 3, "local": 4}
CAMPAIGN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")

CLAIM_CEILING = (
    "Contract/preflight DAG validator only. This capsule does not dispatch "
    "agents, execute campaigns, prove provider correctness, authorize release, "
    "or claim full private-root equivalence."
)
ANTI_CLAIMS = (
    "not_a_dispatcher",
    "not_live_multi_agent_execution",
    "not_provider_safety_proof",
    "not_release_authority",
)


@dataclass(frozen=True)
class Decision:
    """
    [ROLE]
    - Teleology: Groups `Decision` data or behavior for `microcosm_core.engine_room.bridge_campaign_dag` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.engine_room.bridge_campaign_dag`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    rule_id: str
    outcome: str
    target: str | None
    message: str


@dataclass
class ValidationResult:
    """
    [ROLE]
    - Teleology: Groups `ValidationResult` data or behavior for `microcosm_core.engine_room.bridge_campaign_dag` behind a documented class contract.
    - Ownership: Owned by `microcosm_core.engine_room.bridge_campaign_dag`; callers should construct or mutate instances only through declared fields, constructors, or methods.
    - Mutability: Follows the dataclass, descriptor, or instance-attribute behavior encoded by the class body; shared mutable instances remain caller-owned unless a method explicitly transfers custody.
    - Concurrency: Provides no implicit cross-thread lock; callers must serialize shared instance access unless the class body explicitly implements locking.
    - Guarantee: Successful construction exposes attributes and methods declared in the class body with invariants enforced by its constructor or dataclass machinery.
    - Fails: Constructor, descriptor, or method validation errors propagate as normal Python exceptions or explicit body-defined envelopes.
    """
    ok: bool = True
    decisions: list[Decision] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add(self, rule_id: str, outcome: str, target: str | None, message: str) -> None:
        """
        [ACTION]
        - Teleology: Implements `ValidationResult.add` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        decision = Decision(rule_id=rule_id, outcome=outcome, target=target, message=message)
        self.decisions.append(decision)
        if outcome == "reject":
            self.ok = False
            self.errors.append(_format_decision(decision))
        elif outcome == "warn":
            self.warnings.append(_format_decision(decision))

    def to_dict(self) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Implements `ValidationResult.to_dict` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "decisions": [asdict(decision) for decision in self.decisions],
        }


def _format_decision(decision: Decision) -> str:
    """
    [ACTION]
    - Teleology: Implements `_format_decision` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    scope = f" target={decision.target!r}" if decision.target else ""
    return f"[{decision.rule_id}]{scope} {decision.message}"


def _string(value: Any) -> str:
    """
    [ACTION]
    - Teleology: Implements `_string` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return str(value or "").strip()


def _as_list(value: Any) -> list[Any]:
    """
    [ACTION]
    - Teleology: Implements `_as_list` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _node_label(node: Mapping[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `_node_label` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _string(node.get("label"))


def _node_role(node: Mapping[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `_node_role` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return _string(node.get("role"))


def _node_dependencies(node: Mapping[str, Any]) -> tuple[str, ...]:
    """
    [ACTION]
    - Teleology: Implements `_node_dependencies` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    raw = node.get("depends_on", [])
    if isinstance(raw, str):
        return tuple(part for part in (p.strip() for p in raw.split(",")) if part)
    return tuple(_string(item) for item in _as_list(raw) if _string(item))


def _nodes_by_label(nodes: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_nodes_by_label` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {_node_label(node): node for node in nodes if _node_label(node)}


def _reachable_dependencies(
    label: str,
    nodes_by_label: Mapping[str, Mapping[str, Any]],
    *,
    seen: set[str] | None = None,
) -> set[str]:
    """
    [ACTION]
    - Teleology: Implements `_reachable_dependencies` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    seen = set() if seen is None else seen
    for dep in _node_dependencies(nodes_by_label.get(label, {})):
        if dep in seen:
            continue
        seen.add(dep)
        if dep in nodes_by_label:
            _reachable_dependencies(dep, nodes_by_label, seen=seen)
    return seen


def _cycle_labels(nodes: Sequence[Mapping[str, Any]]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_cycle_labels` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    nodes_by_label = _nodes_by_label(nodes)
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: set[str] = set()

    def visit(label: str) -> None:
        """
        [ACTION]
        - Teleology: Implements `_cycle_labels.visit` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        if label in visiting:
            cycles.add(label)
            return
        if label in visited:
            return
        visiting.add(label)
        for dep in _node_dependencies(nodes_by_label.get(label, {})):
            if dep in nodes_by_label:
                visit(dep)
        visiting.remove(label)
        visited.add(label)

    for label in nodes_by_label:
        visit(label)
    return sorted(cycles)


def validate_campaign(
    campaign: Mapping[str, Any],
    *,
    provider: str = "chatgpt",
    workers: int = 1,
    require_existing_plan: bool = False,
    repo_root: Path | None = None,
) -> ValidationResult:
    """
    [ACTION]
    Validate one public bridge campaign spec.

    The rule ids intentionally mirror the macro CR/VR rule families where this
    capsule carries their public-safe subset.
    - Teleology: Implements `validate_campaign` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """

    result = ValidationResult()
    schema_version = _string(campaign.get("schema_version"))
    kind = _string(campaign.get("kind"))
    campaign_id = _string(campaign.get("campaign_id"))
    intent = _string(campaign.get("intent"))
    plan_path = _string(campaign.get("plan_path"))
    barrier = campaign.get("barrier") if isinstance(campaign.get("barrier"), Mapping) else {}
    continuation = (
        campaign.get("continuation") if isinstance(campaign.get("continuation"), Mapping) else {}
    )
    nodes = [node for node in _as_list(campaign.get("nodes")) if isinstance(node, Mapping)]

    result.add(
        "CR001",
        "ok" if schema_version == "1.0" else "reject",
        "campaign",
        "schema_version must equal '1.0'",
    )
    result.add(
        "CR002",
        "ok" if kind == "bridge_campaign" else "reject",
        "campaign",
        "kind must be 'bridge_campaign'",
    )
    result.add(
        "CR003",
        "ok" if CAMPAIGN_ID_RE.match(campaign_id) else "reject",
        "campaign_id",
        "campaign_id must be non-empty kebab-case",
    )
    result.add("CR004", "ok" if intent else "reject", "intent", "intent is required")
    plan_ok = bool(plan_path) and (
        plan_path.startswith("tools/meta/apply/observe_plans/")
        or "/cycle_" in plan_path
        or plan_path.startswith("obsidian/")
    )
    result.add(
        "CR005",
        "ok" if plan_ok else "reject",
        "plan_path",
        "plan_path must name a public observe-plan or phase-cycle path",
    )

    labels = [_node_label(node) for node in nodes]
    unique_labels = {label for label in labels if label}
    result.add(
        "CR017",
        "ok" if len(unique_labels) == len(labels) and all(labels) else "reject",
        "nodes",
        "node labels must be unique and non-empty",
    )
    for node in nodes:
        label = _node_label(node)
        role = _node_role(node)
        input_mode = _string(node.get("input_mode") or "receipts_only")
        result.add(
            "CR015",
            "ok" if input_mode in VALID_INPUT_MODES else "reject",
            label,
            "input_mode must be a known public input mode",
        )
        if input_mode != "receipts_only":
            result.add(
                "CR016",
                "ok" if _string(node.get("input_mode_rationale")) else "reject",
                label,
                "non-receipts-only modes require input_mode_rationale",
            )
        result.add(
            "CR020",
            "ok" if role in VALID_NODE_ROLES else "reject",
            label,
            "node role must be probe, reducer, or synthesis",
        )

    nodes_by_label = _nodes_by_label(nodes)
    missing_deps: list[str] = []
    for node in nodes:
        label = _node_label(node)
        deps = _node_dependencies(node)
        missing_deps.extend(f"{label}->{dep}" for dep in deps if dep not in nodes_by_label)
        if _node_role(node) in {"reducer", "synthesis"}:
            result.add(
                "CR011",
                "ok" if deps else "reject",
                label,
                "reducer and synthesis nodes must depend on at least one upstream node",
            )
    result.add(
        "CR010",
        "ok" if not missing_deps else "reject",
        "nodes",
        "every depends_on entry must reference an existing node label",
    )

    cycles = _cycle_labels(nodes)
    result.add(
        "CR012",
        "ok" if not cycles else "reject",
        "nodes",
        "node graph must be acyclic",
    )

    synthesis_nodes = [node for node in nodes if _node_role(node) == "synthesis"]
    result.add(
        "CR013",
        "ok" if len(synthesis_nodes) == 1 else "reject",
        "nodes",
        "exactly one synthesis node is required",
    )
    barrier_label = _string(barrier.get("group_label"))
    result.add(
        "CR006",
        "ok" if len(synthesis_nodes) == 1 and barrier_label == _node_label(synthesis_nodes[0]) else "reject",
        "barrier.group_label",
        "barrier.group_label must match the synthesis node",
    )
    result.add(
        "CR007",
        "ok" if _string(barrier.get("description")) else "reject",
        "barrier.description",
        "barrier.description is required",
    )
    result.add(
        "CR008",
        "ok" if _string(continuation.get("packet_schema")) in VALID_PACKET_SCHEMAS else "reject",
        "continuation.packet_schema",
        "continuation.packet_schema must be a supported public packet schema",
    )
    next_action = _string(continuation.get("next_action"))
    result.add(
        "CR009",
        "ok" if 0 < len(next_action) <= 500 else "reject",
        "continuation.next_action",
        "continuation.next_action must be non-empty and bounded",
    )

    if len(synthesis_nodes) == 1 and not cycles:
        synth_label = _node_label(synthesis_nodes[0])
        reachable = _reachable_dependencies(synth_label, nodes_by_label)
        reaches_probe = any(_node_role(nodes_by_label[label]) == "probe" for label in reachable)
        result.add(
            "CR014",
            "ok" if reaches_probe else "reject",
            synth_label,
            "synthesis node must transitively reach at least one probe node",
        )

    provider_key = provider.strip().lower()
    safe_parallelism = SAFE_PARALLELISM.get(provider_key)
    ceiling_ok = safe_parallelism is not None and workers <= safe_parallelism
    result.add(
        "VR005",
        "ok" if ceiling_ok else "reject",
        provider_key or "provider",
        f"requested workers must not exceed provider safe_parallelism ({safe_parallelism})",
    )

    if require_existing_plan and repo_root is not None:
        result.add(
            "CR019",
            "ok" if (repo_root / plan_path).is_file() else "reject",
            "plan_path",
            "plan_path must exist when filesystem preflight is requested",
        )
    return result


def load_campaign(path: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `load_campaign` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} did not contain a JSON object")
    return payload


def validate_campaign_file(path: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_campaign_file` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payload = load_campaign(path)
    provider = _string(payload.get("provider") or "chatgpt")
    workers = int(payload.get("workers") or 1)
    expected_ok = bool(payload.get("expected_ok", True))
    result = validate_campaign(payload, provider=provider, workers=workers)
    return {
        "case_id": _string(payload.get("case_id") or path.stem),
        "path": str(path),
        "expected_ok": expected_ok,
        "observed_ok": result.ok,
        "expectation_met": expected_ok == result.ok,
        "provider": provider,
        "workers": workers,
        "result": result.to_dict(),
    }


def validate_fixture_dir(input_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_fixture_dir` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = [validate_campaign_file(path) for path in sorted(input_dir.glob("*.json"))]
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "case_count": len(rows),
        "passed_case_count": sum(1 for row in rows if row["expectation_met"]),
        "status": "pass" if rows and all(row["expectation_met"] for row in rows) else "fail",
        "cases": rows,
    }


def _emit(payload: Mapping[str, Any], *, json_output: bool) -> None:
    """
    [ACTION]
    - Teleology: Implements `_emit` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    status = payload.get("status") or ("pass" if payload.get("ok") else "fail")
    print(f"{ORGAN_ID}: {status}")


def main(argv: Sequence[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.engine_room.bridge_campaign_dag` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate one bridge campaign JSON file")
    validate.add_argument("--input", required=True)
    validate.add_argument("--provider", default="chatgpt")
    validate.add_argument("--workers", type=int, default=1)
    validate.add_argument("--json", action="store_true")

    matrix = subparsers.add_parser("validate-fixtures", help="Validate all fixture campaign JSON files")
    matrix.add_argument("--input", required=True)
    matrix.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "validate":
        result = validate_campaign(
            load_campaign(Path(args.input)),
            provider=args.provider,
            workers=args.workers,
        )
        payload = {
            "schema_version": SCHEMA_VERSION,
            "organ_id": ORGAN_ID,
            "ok": result.ok,
            "source_refs": list(SOURCE_REFS),
            "claim_ceiling": CLAIM_CEILING,
            "anti_claims": list(ANTI_CLAIMS),
            "result": result.to_dict(),
        }
        _emit(payload, json_output=args.json)
        return 0 if result.ok else 1
    payload = validate_fixture_dir(Path(args.input))
    _emit(payload, json_output=args.json)
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
