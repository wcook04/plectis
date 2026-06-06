#!/usr/bin/env python3
"""Build dry-run demand-scoped schedule preflight reports over replay scope IR."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from system.lib.strict_json import loads_json_strict  # noqa: E402

import build_reasoning_execution_lineage as lineage_builder  # noqa: E402
import build_reasoning_execution_replay_scope as replay_scope_builder  # noqa: E402


SCHEMA_VERSION = "reasoning_execution_schedule_preflight_v0"
SCHEDULE_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_schedule_preflight.json"
)
LINEAGE_SCHEMA_PATH = REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_lineage.json"
REPLAY_SCOPE_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_replay_scope.json"
)
STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_node_reasoning.json"
LINEAGE_BUILDER_PATH = REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_lineage.py"
REPLAY_SCOPE_BUILDER_PATH = (
    REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_replay_scope.py"
)
SCHEDULE_PREFLIGHT_BUILDER_PATH = (
    REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_schedule_preflight.py"
)
BUILD_SYSTEMS_DISTILLATION_PATH = REPO_ROOT / "annexes" / "build-systems-a-la-carte" / "distillation.json"
FORWARD_BUILD_DISTILLATION_PATH = REPO_ROOT / "annexes" / "arxiv-2202-05328" / "distillation.json"
DRY_RUN_EVALUATION_FLAGS = ("model_dispatch", "provider_dispatch", "runtime_execution", "writes")


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _json_path(error_path: Iterable[Any]) -> str:
    parts = list(error_path)
    if not parts:
        return "$"
    rendered = "$"
    for part in parts:
        if isinstance(part, int):
            rendered += f"[{part}]"
        else:
            rendered += f".{part}"
    return rendered


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_str_list(value: Any) -> list[str]:
    return [item for item in _as_list(value) if isinstance(item, str)]


def _dedupe(items: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not isinstance(item, str) or not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _source_refs(repo_root: Path) -> list[str]:
    refs: list[Path | str] = [
        STANDARD_PATH,
        LINEAGE_SCHEMA_PATH,
        REPLAY_SCOPE_SCHEMA_PATH,
        SCHEDULE_SCHEMA_PATH,
        LINEAGE_BUILDER_PATH,
        REPLAY_SCOPE_BUILDER_PATH,
        SCHEDULE_PREFLIGHT_BUILDER_PATH,
    ]
    if BUILD_SYSTEMS_DISTILLATION_PATH.exists():
        refs.append(BUILD_SYSTEMS_DISTILLATION_PATH)
    if FORWARD_BUILD_DISTILLATION_PATH.exists():
        refs.append(FORWARD_BUILD_DISTILLATION_PATH)
    refs.append("https://plum-umd.github.io/adapton/")
    return [_display_path(path, repo_root) if isinstance(path, Path) else path for path in refs]


def validate_schedule_preflight(report: Mapping[str, Any], repo_root: Path = REPO_ROOT) -> list[dict[str, str]]:
    """Validate a schedule-preflight report against the durable schema."""
    repo_root = Path(repo_root)
    schema_path = repo_root / SCHEDULE_SCHEMA_PATH.relative_to(REPO_ROOT)
    schema = loads_json_strict(schema_path.read_text(encoding="utf-8"), source=_display_path(schema_path, repo_root))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(report),
        key=lambda error: (list(error.path), list(error.schema_path), error.message),
    )
    return [
        {
            "path": _json_path(error.path),
            "code": "schema_validation_error",
            "message": error.message,
        }
        for error in errors
    ]


def _issue(
    *,
    code: str,
    severity: str,
    path: str,
    message: str,
    witness: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "path": path,
        "message": message,
        "witness": dict(witness or {}),
    }


def _dry_run_evaluation() -> dict[str, bool]:
    return {
        "model_dispatch": False,
        "provider_dispatch": False,
        "runtime_execution": False,
        "writes": False,
    }


def _lineage_ref(lineage: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "lineage_id": lineage.get("lineage_id") if isinstance(lineage.get("lineage_id"), str) else None,
        "lineage_hash": _stable_hash(lineage) if lineage else None,
        "status": lineage.get("status") if isinstance(lineage.get("status"), str) else None,
    }


def _node_map(lineage: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for node in _as_list(lineage.get("nodes")):
        if not isinstance(node, Mapping):
            continue
        node_id = node.get("node_id")
        if isinstance(node_id, str) and node_id:
            result[node_id] = node
    return result


def _edge_pairs(lineage: Mapping[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for edge in _as_list(lineage.get("edges")):
        if not isinstance(edge, Mapping):
            continue
        from_id = edge.get("from")
        to_id = edge.get("to")
        if isinstance(from_id, str) and isinstance(to_id, str):
            pairs.append((from_id, to_id))
    for node in _as_list(lineage.get("nodes")):
        if not isinstance(node, Mapping) or not isinstance(node.get("node_id"), str):
            continue
        to_id = str(node["node_id"])
        for upstream_id in _as_str_list(node.get("upstream_node_ids")):
            pairs.append((upstream_id, to_id))
    return sorted(set(pairs))


def _reverse_adjacency(edges: Sequence[tuple[str, str]]) -> dict[str, list[str]]:
    reverse: dict[str, list[str]] = {}
    for from_id, to_id in edges:
        reverse.setdefault(to_id, []).append(from_id)
    return {key: sorted(values) for key, values in reverse.items()}


def _demand_closure(edges: Sequence[tuple[str, str]], roots: Iterable[str]) -> list[str]:
    reverse = _reverse_adjacency(edges)
    seen: set[str] = set()
    queue = list(roots)
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        queue.extend(reverse.get(current, []))
    return sorted(seen)


def _plan_output_targets(nodes: Mapping[str, Mapping[str, Any]], edges: Sequence[tuple[str, str]]) -> list[str]:
    node_ids = set(nodes)
    non_sinks = {from_id for from_id, to_id in edges if from_id in node_ids and to_id in node_ids}
    sinks = sorted(node_id for node_id in node_ids if node_id not in non_sinks)
    return sinks or sorted(node_ids)


def _target_nodes(
    lineage: Mapping[str, Any],
    *,
    target_node_ids: Sequence[str],
    target_artifact_kinds: Sequence[str],
) -> tuple[list[str], str, list[dict[str, Any]]]:
    nodes = _node_map(lineage)
    issues: list[dict[str, Any]] = []
    if target_node_ids:
        missing = [node_id for node_id in target_node_ids if node_id not in nodes]
        if missing:
            issues.append(
                _issue(
                    code="target_node_not_found",
                    severity="error",
                    path="$.demand.target_node_ids",
                    message="One or more requested target nodes are not present in the candidate lineage.",
                    witness={"missing_target_node_ids": missing},
                )
            )
        return _dedupe(target_node_ids), "explicit_target_nodes", issues
    if target_artifact_kinds:
        matched = [
            node_id
            for node_id, node in nodes.items()
            if isinstance(node.get("output_artifact_kind"), str)
            and str(node.get("output_artifact_kind")) in set(target_artifact_kinds)
        ]
        missing_kinds = sorted(set(target_artifact_kinds) - {str(nodes[node_id].get("output_artifact_kind")) for node_id in matched})
        if missing_kinds:
            issues.append(
                _issue(
                    code="target_artifact_kind_not_found",
                    severity="error",
                    path="$.demand.target_artifact_kinds",
                    message="One or more requested artifact kinds are not emitted by candidate lineage nodes.",
                    witness={"missing_target_artifact_kinds": missing_kinds},
                )
            )
        return sorted(matched), "explicit_artifact_kinds", issues
    return _plan_output_targets(nodes, _edge_pairs(lineage)), "all_plan_outputs_default", issues


def _replay_order(edges: Sequence[tuple[str, str]], replay_set: Iterable[str]) -> tuple[list[str], list[dict[str, Any]]]:
    replay_nodes = set(replay_set)
    if not replay_nodes:
        return [], []
    indegree = {node_id: 0 for node_id in replay_nodes}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in replay_nodes}
    for from_id, to_id in edges:
        if from_id not in replay_nodes or to_id not in replay_nodes:
            continue
        adjacency[from_id].append(to_id)
        indegree[to_id] += 1
    ready = sorted(node_id for node_id, count in indegree.items() if count == 0)
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for downstream in sorted(adjacency.get(current, [])):
            indegree[downstream] -= 1
            if indegree[downstream] == 0:
                ready.append(downstream)
                ready.sort()
    if len(order) == len(replay_nodes):
        return order, []
    cycle_nodes = sorted(replay_nodes - set(order))
    return order, [
        _issue(
            code="schedule_replay_cycle",
            severity="error",
            path="$.schedule.replay_order_node_ids",
            message="Replay set could not be topologically ordered.",
            witness={"cycle_or_unordered_node_ids": cycle_nodes},
        )
    ]


def _replay_scope_ref(replay_scope: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "replay_decision": _as_mapping(replay_scope.get("replay_decision")).get("mode")
        if isinstance(_as_mapping(replay_scope.get("replay_decision")).get("mode"), str)
        else None,
        "status": replay_scope.get("status") if isinstance(replay_scope.get("status"), str) else None,
    }


def _schedule_issue_inputs(
    *,
    candidate_lineage: Mapping[str, Any],
    replay_scope: Mapping[str, Any],
    repo_root: Path,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for row in lineage_builder.validate_lineage(candidate_lineage, repo_root):
        issues.append(
            _issue(
                code="candidate_lineage_schema_validation_error",
                severity="error",
                path=f"$.candidate_lineage{str(row.get('path') or '$')[1:]}",
                message=str(row.get("message") or "Candidate lineage failed schema validation."),
                witness={"schema_issue": dict(row)},
            )
        )
    for row in replay_scope_builder.validate_replay_scope(replay_scope, repo_root):
        issues.append(
            _issue(
                code="replay_scope_schema_validation_error",
                severity="error",
                path=f"$.replay_scope{str(row.get('path') or '$')[1:]}",
                message=str(row.get("message") or "Replay-scope report failed schema validation."),
                witness={"schema_issue": dict(row)},
            )
        )
    if candidate_lineage.get("status") == "invalid_lineage":
        issues.append(
            _issue(
                code="candidate_lineage_invalid",
                severity="error",
                path="$.candidate_lineage.status",
                message="Invalid candidate lineage cannot be scheduled.",
                witness={"lineage_issues": candidate_lineage.get("issues")},
            )
        )
    if candidate_lineage.get("status") == "incomplete":
        issues.append(
            _issue(
                code="candidate_lineage_incomplete",
                severity="error",
                path="$.candidate_lineage.status",
                message="Incomplete candidate lineage cannot be scheduled by dry-run preflight.",
                witness={"lineage_status": candidate_lineage.get("status")},
            )
        )
    if replay_scope.get("status") == "invalid_replay_scope":
        issues.append(
            _issue(
                code="replay_scope_invalid",
                severity="error",
                path="$.replay_scope.status",
                message="Invalid replay scope cannot be converted into a schedule preflight.",
                witness={"replay_scope_issues": replay_scope.get("issues")},
            )
        )
    return issues


def _context_lineage(node: Mapping[str, Any]) -> dict[str, list[str]]:
    context = _as_mapping(node.get("context_lineage"))
    return {
        "inject": _as_str_list(context.get("inject")),
        "reference_only": _as_str_list(context.get("reference_only")),
        "withhold": _as_str_list(context.get("withhold")),
        "forbidden": _as_str_list(context.get("forbidden")),
        "available_context": _as_str_list(context.get("available_context")),
        "available_artifacts": _as_str_list(context.get("available_artifacts")),
        "effective_context": _as_str_list(context.get("effective_context")),
        "effective_artifacts": _as_str_list(context.get("effective_artifacts")),
    }


def _node_actions(
    *,
    nodes: Mapping[str, Mapping[str, Any]],
    demand_closure: set[str],
    replay_set: set[str],
    blocked_nodes: set[str],
    invalid_nodes: set[str],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for node_id in sorted(nodes):
        node = nodes[node_id]
        if node_id in invalid_nodes:
            action = "invalid"
            reason = "candidate_or_replay_scope_invalid"
        elif node_id in blocked_nodes:
            action = "blocked"
            reason = "candidate_or_replay_scope_blocked"
        elif node_id not in demand_closure:
            action = "skip_not_demanded"
            reason = "outside_demand_closure"
        elif node_id in replay_set:
            action = "replay"
            reason = "demanded_and_replay_required"
        else:
            action = "reuse"
            reason = "demanded_and_replay_identity_unchanged_or_outside_replay_scope"
        actions.append(
            {
                "node_id": node_id,
                "action": action,
                "reason": reason,
                "upstream_node_ids": _as_str_list(node.get("upstream_node_ids")),
                "context_lineage": _context_lineage(node),
                "side_effect_level": str(node.get("side_effect_level") or "read_only"),
            }
        )
    return actions


def _preflight_status(
    *,
    issues: Sequence[Mapping[str, Any]],
    blocked_nodes: Sequence[str],
    replay_order: Sequence[str],
    replay_scope: Mapping[str, Any],
    candidate_lineage: Mapping[str, Any],
) -> str:
    if any(issue.get("severity") == "error" for issue in issues):
        return "invalid_schedule"
    if replay_scope.get("status") == "blocked" or candidate_lineage.get("status") == "blocked" or blocked_nodes:
        return "blocked"
    if not replay_order:
        return "no_op"
    return "ready"


def build_schedule_preflight(
    repo_root: Path = REPO_ROOT,
    *,
    candidate_lineage: Mapping[str, Any],
    replay_scope: Mapping[str, Any],
    target_node_ids: Sequence[str] = (),
    target_artifact_kinds: Sequence[str] = (),
) -> dict[str, Any]:
    """Build a dry-run demand-scoped preflight report from lineage and replay-scope IR."""
    repo_root = Path(repo_root)
    nodes = _node_map(candidate_lineage)
    edges = _edge_pairs(candidate_lineage)
    target_nodes, demand_basis, target_issues = _target_nodes(
        candidate_lineage,
        target_node_ids=target_node_ids,
        target_artifact_kinds=target_artifact_kinds,
    )
    demand_closure = _demand_closure(edges, target_nodes)
    graph_impact = _as_mapping(replay_scope.get("graph_impact"))
    replay_required = set(_as_str_list(graph_impact.get("replay_required_node_ids")))
    blocked_nodes = set(_as_str_list(graph_impact.get("blocked_node_ids")))
    invalid_nodes = set(_as_str_list(graph_impact.get("invalid_node_ids")))
    schedule_replay_set = replay_required & set(demand_closure) - blocked_nodes - invalid_nodes
    replay_order, order_issues = _replay_order(edges, schedule_replay_set)
    reuse_nodes = sorted(set(demand_closure) - set(schedule_replay_set) - blocked_nodes - invalid_nodes)
    skipped_nodes = sorted(set(nodes) - set(demand_closure))
    issues = [
        *_schedule_issue_inputs(
            candidate_lineage=candidate_lineage,
            replay_scope=replay_scope,
            repo_root=repo_root,
        ),
        *target_issues,
        *order_issues,
    ]
    status = _preflight_status(
        issues=issues,
        blocked_nodes=sorted(blocked_nodes & set(demand_closure) or blocked_nodes),
        replay_order=replay_order,
        replay_scope=replay_scope,
        candidate_lineage=candidate_lineage,
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "source_refs": _source_refs(repo_root),
        "candidate_lineage": _lineage_ref(candidate_lineage),
        "replay_scope": _replay_scope_ref(replay_scope),
        "demand": {
            "target_node_ids": _dedupe(target_node_ids) if target_node_ids else target_nodes,
            "target_artifact_kinds": _dedupe(target_artifact_kinds),
            "demand_closure_node_ids": demand_closure,
            "demand_basis": demand_basis,
        },
        "node_actions": _node_actions(
            nodes=nodes,
            demand_closure=set(demand_closure),
            replay_set=set(schedule_replay_set),
            blocked_nodes=blocked_nodes,
            invalid_nodes=invalid_nodes,
        ),
        "schedule": {
            "policy": "deterministic_topological",
            "replay_order_node_ids": replay_order,
            "reuse_node_ids": reuse_nodes,
            "skipped_node_ids": skipped_nodes,
            "blocked_node_ids": sorted(blocked_nodes),
            "invalid_node_ids": sorted(invalid_nodes),
        },
        "authorization": {
            "launch_authorized": False,
            "reason": "dry_run_preflight_only",
            "future_runner_requirements": [
                "verified_plan",
                "replay_scope_ready",
                "node_scoped_context_lineage",
                "no_forbidden_context",
                "side_effect_policy_checked",
            ],
        },
        "evaluation": _dry_run_evaluation(),
        "dry_run": True,
        "status": status,
        "issues": issues,
    }
    return report


def _load_json_object(path: Path) -> Mapping[str, Any]:
    value = loads_json_strict(path.read_text(encoding="utf-8"), source=str(path))
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def _build_inputs(args: argparse.Namespace, repo_root: Path) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    candidate_lineage: Mapping[str, Any] | None = None
    replay_scope: Mapping[str, Any] | None = None
    if args.candidate_lineage:
        candidate_lineage = _load_json_object(Path(args.candidate_lineage))
    if args.replay_scope:
        replay_scope = _load_json_object(Path(args.replay_scope))
    if replay_scope is not None and candidate_lineage is None:
        raise ValueError("--candidate-lineage is required when --replay-scope is provided.")
    if candidate_lineage is not None and replay_scope is not None:
        return candidate_lineage, replay_scope
    if args.base_lineage or args.candidate_lineage:
        if not args.base_lineage or not args.candidate_lineage:
            raise ValueError("Provide both --base-lineage and --candidate-lineage, or neither.")
        base_lineage = _load_json_object(Path(args.base_lineage))
        candidate_lineage = _load_json_object(Path(args.candidate_lineage))
    else:
        if not args.node_id:
            raise ValueError("Provide --node-id at least once or existing lineage files.")
        base_lineage = lineage_builder.build_lineage(
            repo_root,
            node_ids=args.node_id,
            plan_id=args.plan_id,
            source_work_item=args.source_work_item,
            available_context=args.base_context,
            available_artifacts=args.base_artifact,
        )
        candidate_lineage = lineage_builder.build_lineage(
            repo_root,
            node_ids=args.node_id,
            plan_id=args.plan_id,
            source_work_item=args.source_work_item,
            available_context=args.candidate_context,
            available_artifacts=args.candidate_artifact,
        )
    replay_scope = replay_scope_builder.build_replay_scope(
        repo_root,
        base_lineage=base_lineage,
        candidate_lineage=candidate_lineage,
    )
    return candidate_lineage, replay_scope


def _empty_context_lineage() -> dict[str, list[str]]:
    return {
        "inject": [],
        "reference_only": [],
        "withhold": [],
        "forbidden": [],
        "available_context": [],
        "available_artifacts": [],
        "effective_context": [],
        "effective_artifacts": [],
    }


def _error_report(repo_root: Path, exc: Exception) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source_refs": _source_refs(repo_root),
        "candidate_lineage": {"lineage_id": None, "lineage_hash": None, "status": None},
        "replay_scope": {"replay_decision": None, "status": None},
        "demand": {
            "target_node_ids": [],
            "target_artifact_kinds": [],
            "demand_closure_node_ids": [],
            "demand_basis": "all_plan_outputs_default",
        },
        "node_actions": [],
        "schedule": {
            "policy": "deterministic_topological",
            "replay_order_node_ids": [],
            "reuse_node_ids": [],
            "skipped_node_ids": [],
            "blocked_node_ids": [],
            "invalid_node_ids": [],
        },
        "authorization": {
            "launch_authorized": False,
            "reason": "dry_run_preflight_only",
            "future_runner_requirements": ["valid_lineage_inputs", "valid_replay_scope_inputs"],
        },
        "evaluation": _dry_run_evaluation(),
        "dry_run": True,
        "status": "invalid_schedule",
        "issues": [
            _issue(
                code="schedule_preflight_input_error",
                severity="error",
                path="$",
                message=str(exc),
                witness={"exception_type": type(exc).__name__, "empty_context_lineage": _empty_context_lineage()},
            )
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a dry-run demand-scoped schedule preflight report.")
    parser.add_argument("--node-id", action="append", default=[], help="Node id to include when building lineages. Repeatable.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root.")
    parser.add_argument("--plan-id", default=None, help="Optional stable plan id when building lineages.")
    parser.add_argument("--source-work-item", default=None, help="Optional WorkItem/cap id grounding built lineages.")
    parser.add_argument("--base-lineage", default=None, help="Existing base lineage JSON file.")
    parser.add_argument("--candidate-lineage", default=None, help="Existing candidate lineage JSON file.")
    parser.add_argument("--replay-scope", default=None, help="Existing replay-scope JSON file. Requires --candidate-lineage.")
    parser.add_argument("--base-context", action="append", default=[], help="Base available context class. Repeatable.")
    parser.add_argument("--candidate-context", action="append", default=[], help="Candidate available context class. Repeatable.")
    parser.add_argument("--base-artifact", action="append", default=[], help="Base available artifact id. Repeatable.")
    parser.add_argument("--candidate-artifact", action="append", default=[], help="Candidate available artifact id. Repeatable.")
    parser.add_argument("--target-node-id", action="append", default=[], help="Demand target node id. Repeatable.")
    parser.add_argument("--target-artifact-kind", action="append", default=[], help="Demand target artifact kind. Repeatable.")
    parser.add_argument("--json", action="store_true", help="Emit JSON. Currently always true.")
    parser.add_argument("--check", action="store_true", help="Validate and emit a compact check report.")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    try:
        candidate_lineage, replay_scope = _build_inputs(args, repo_root)
        report = build_schedule_preflight(
            repo_root,
            candidate_lineage=candidate_lineage,
            replay_scope=replay_scope,
            target_node_ids=args.target_node_id,
            target_artifact_kinds=args.target_artifact_kind,
        )
    except Exception as exc:
        report = _error_report(repo_root, exc)
    schema_issues = validate_schedule_preflight(report, repo_root)
    if args.check:
        print(
            json.dumps(
                {
                    "ok": not schema_issues and report.get("status") != "invalid_schedule",
                    "schema_version": "reasoning_execution_schedule_preflight_check_v0",
                    "schedule_preflight_schema": _display_path(
                        repo_root / SCHEDULE_SCHEMA_PATH.relative_to(REPO_ROOT),
                        repo_root,
                    ),
                    "candidate_lineage_id": _as_mapping(report.get("candidate_lineage")).get("lineage_id"),
                    "replay_decision": _as_mapping(report.get("replay_scope")).get("replay_decision"),
                    "status": report.get("status"),
                    "replay_order_node_ids": _as_mapping(report.get("schedule")).get("replay_order_node_ids"),
                    "issues": schema_issues,
                },
                indent=2,
                sort_keys=False,
            )
        )
        return 0 if not schema_issues and report.get("status") != "invalid_schedule" else 2
    if schema_issues:
        print(
            json.dumps(
                {
                    "ok": False,
                    "schema_version": "reasoning_execution_schedule_preflight_check_v0",
                    "status": report.get("status"),
                    "issues": schema_issues,
                },
                indent=2,
                sort_keys=False,
            )
        )
        return 2
    print(json.dumps(report, indent=2, sort_keys=False))
    return 1 if report.get("status") == "invalid_schedule" else 0


if __name__ == "__main__":
    raise SystemExit(main())
