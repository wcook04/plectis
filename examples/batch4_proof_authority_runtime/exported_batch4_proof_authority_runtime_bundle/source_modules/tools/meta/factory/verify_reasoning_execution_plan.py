#!/usr/bin/env python3
"""Statically verify dry-run reasoning execution plans.

The verifier is a lint over ``reasoning_execution_plan_v0``. It validates plan
shape and semantic consistency, but does not execute nodes, dispatch providers,
write artifacts, or mutate runtime state.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
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

import build_reasoning_contract_packet as packet_builder  # noqa: E402
import build_reasoning_execution_plan as plan_builder  # noqa: E402


SCHEMA_VERSION = "reasoning_execution_plan_verification_report_v0"
REPORT_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_plan_verification_report.json"
)
PLAN_SCHEMA_PATH = REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_plan.json"
PACKET_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_contract_packet_manifest.json"
)
STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_node_reasoning.json"
AGENTPROOF_DISTILLATION_PATH = REPO_ROOT / "annexes" / "arxiv-2603-20356" / "distillation.json"
CHECK_NAMES = (
    "plan_schema_valid",
    "embedded_packet_manifests_valid",
    "node_ids_unique",
    "edge_endpoints_exist",
    "acyclic",
    "upstream_dependency_consistency",
    "ready_set_consistency",
    "status_derivation_consistency",
    "context_policy_scope",
    "dry_run_side_effect_consistency",
    "recovery_protocol_present",
)
TERMINAL_MANIFEST_STATUSES = {"not_found", "invalid_json", "no_reasoning_contract", "invalid_contract"}
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


def _source_refs(repo_root: Path) -> list[str]:
    refs = [
        STANDARD_PATH,
        PLAN_SCHEMA_PATH,
        PACKET_SCHEMA_PATH,
        REPORT_SCHEMA_PATH,
        REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_contract_packet.py",
        REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_plan.py",
        REPO_ROOT / "tools" / "meta" / "factory" / "verify_reasoning_execution_plan.py",
    ]
    if AGENTPROOF_DISTILLATION_PATH.exists():
        refs.append(AGENTPROOF_DISTILLATION_PATH)
    return [_display_path(path, repo_root) for path in refs]


def validate_report(report: Mapping[str, Any], repo_root: Path = REPO_ROOT) -> list[dict[str, str]]:
    """Validate a verifier report against the durable report schema."""
    repo_root = Path(repo_root)
    schema_path = repo_root / REPORT_SCHEMA_PATH.relative_to(REPO_ROOT)
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


class ReportBuilder:
    def __init__(self, plan: Mapping[str, Any], repo_root: Path) -> None:
        self.plan = plan
        self.repo_root = repo_root
        self.checks: dict[str, str] = {name: "pass" for name in CHECK_NAMES}
        self.issues: list[dict[str, Any]] = []

    def add_issue(
        self,
        *,
        check: str,
        code: str,
        severity: str,
        path: str,
        message: str,
        witness: Mapping[str, Any] | None = None,
    ) -> None:
        if severity not in {"warning", "error"}:
            raise ValueError(f"unknown severity: {severity}")
        issue = {
            "code": code,
            "severity": severity,
            "path": path,
            "message": message,
            "witness": dict(witness or {}),
        }
        self.issues.append(issue)
        current = self.checks.get(check, "pass")
        if severity == "error":
            self.checks[check] = "fail"
        elif current == "pass":
            self.checks[check] = "warn"

    def build(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "plan_id": self.plan.get("plan_id") if isinstance(self.plan.get("plan_id"), str) else None,
            "plan_status": self.plan.get("status") if isinstance(self.plan.get("status"), str) else None,
            "source_refs": _source_refs(self.repo_root),
            "ok": not any(issue["severity"] == "error" for issue in self.issues),
            "checks": self.checks,
            "issues": self.issues,
            "witnesses": [issue["witness"] for issue in self.issues],
        }


def _nodes(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [node for node in _as_list(plan.get("nodes")) if isinstance(node, Mapping)]


def _edges(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [edge for edge in _as_list(plan.get("edges")) if isinstance(edge, Mapping)]


def _node_id(node: Mapping[str, Any]) -> str:
    return str(node.get("node_id") or "")


def _manifest_status(node: Mapping[str, Any]) -> str:
    status = node.get("manifest_status")
    if isinstance(status, str):
        return status
    manifest = _as_mapping(node.get("manifest"))
    return str(manifest.get("status") or "")


def _manifest_schema_invalid(node: Mapping[str, Any], repo_root: Path) -> bool:
    manifest = node.get("manifest")
    if not isinstance(manifest, Mapping):
        return True
    return bool(packet_builder.validate_manifest(manifest, repo_root))


def _expected_ready_sets(plan: Mapping[str, Any], repo_root: Path) -> dict[str, set[str]]:
    ready: set[str] = set()
    blocked: set[str] = set()
    incomplete: set[str] = set()
    invalid: set[str] = set()
    for node in _nodes(plan):
        node_id = _node_id(node)
        status = _manifest_status(node)
        if status in TERMINAL_MANIFEST_STATUSES or _manifest_schema_invalid(node, repo_root):
            invalid.add(node_id)
        elif status == "blocked":
            blocked.add(node_id)
        elif status == "incomplete":
            incomplete.add(node_id)
        elif status == "ready" and not _as_str_list(node.get("upstream_node_ids")):
            ready.add(node_id)
    return {
        "ready_node_ids": ready,
        "blocked_node_ids": blocked,
        "incomplete_node_ids": incomplete,
        "invalid_node_ids": invalid,
        "all_node_ids": {_node_id(node) for node in _nodes(plan)},
    }


def _expected_status(expected_sets: Mapping[str, set[str]]) -> str:
    if expected_sets["invalid_node_ids"]:
        return "invalid_plan"
    if expected_sets["blocked_node_ids"]:
        return "blocked"
    if expected_sets["incomplete_node_ids"]:
        return "incomplete"
    return "ready"


def _check_plan_schema(builder: ReportBuilder) -> None:
    for issue in plan_builder.validate_plan(builder.plan, builder.repo_root):
        builder.add_issue(
            check="plan_schema_valid",
            code="plan_schema_validation_error",
            severity="error",
            path=str(issue.get("path") or "$"),
            message=str(issue.get("message") or "Plan schema validation failed."),
            witness={"schema_issue": dict(issue)},
        )


def _check_embedded_manifests(builder: ReportBuilder) -> None:
    for index, node in enumerate(_nodes(builder.plan)):
        manifest = node.get("manifest")
        node_id = _node_id(node)
        if not isinstance(manifest, Mapping):
            builder.add_issue(
                check="embedded_packet_manifests_valid",
                code="embedded_manifest_not_object",
                severity="error",
                path=f"$.nodes[{index}].manifest",
                message="Embedded packet manifest must be an object.",
                witness={"node_id": node_id, "node_index": index},
            )
            continue
        for issue in packet_builder.validate_manifest(manifest, builder.repo_root):
            builder.add_issue(
                check="embedded_packet_manifests_valid",
                code="embedded_manifest_schema_error",
                severity="error",
                path=f"$.nodes[{index}].manifest{str(issue.get('path') or '$')[1:]}",
                message=str(issue.get("message") or "Embedded packet manifest failed schema validation."),
                witness={"node_id": node_id, "node_index": index, "schema_issue": dict(issue)},
            )


def _check_node_ids(builder: ReportBuilder) -> None:
    ids = [_node_id(node) for node in _nodes(builder.plan)]
    counts = Counter(ids)
    for node_id, count in sorted(counts.items()):
        if count > 1:
            indexes = [index for index, value in enumerate(ids) if value == node_id]
            builder.add_issue(
                check="node_ids_unique",
                code="duplicate_node_id",
                severity="error",
                path="$.nodes",
                message=f"Node id {node_id!r} appears {count} times.",
                witness={"node_id": node_id, "node_indexes": indexes},
            )


def _check_edge_endpoints(builder: ReportBuilder) -> None:
    node_ids = {_node_id(node) for node in _nodes(builder.plan)}
    for index, edge in enumerate(_edges(builder.plan)):
        from_id = edge.get("from")
        to_id = edge.get("to")
        if from_id not in node_ids:
            builder.add_issue(
                check="edge_endpoints_exist",
                code="edge_endpoint_missing",
                severity="error",
                path=f"$.edges[{index}].from",
                message="Edge source references a node not present in plan.nodes.",
                witness={"edge_index": index, "missing_node_id": from_id, "known_node_ids": sorted(node_ids)},
            )
        if to_id not in node_ids:
            builder.add_issue(
                check="edge_endpoints_exist",
                code="edge_endpoint_missing",
                severity="error",
                path=f"$.edges[{index}].to",
                message="Edge target references a node not present in plan.nodes.",
                witness={"edge_index": index, "missing_node_id": to_id, "known_node_ids": sorted(node_ids)},
            )


def _cycle_path(adjacency: Mapping[str, list[str]]) -> list[str] | None:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def dfs(node_id: str) -> list[str] | None:
        visiting.add(node_id)
        stack.append(node_id)
        for target in adjacency.get(node_id, []):
            if target in visiting:
                cycle_start = stack.index(target)
                return [*stack[cycle_start:], target]
            if target not in visited:
                found = dfs(target)
                if found:
                    return found
        visiting.remove(node_id)
        visited.add(node_id)
        stack.pop()
        return None

    for node_id in sorted(adjacency):
        if node_id not in visited:
            found = dfs(node_id)
            if found:
                return found
    return None


def _check_acyclic(builder: ReportBuilder) -> None:
    node_ids = {_node_id(node) for node in _nodes(builder.plan)}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in _edges(builder.plan):
        from_id = edge.get("from")
        to_id = edge.get("to")
        if isinstance(from_id, str) and isinstance(to_id, str) and from_id in node_ids and to_id in node_ids:
            adjacency.setdefault(from_id, []).append(to_id)
    found = _cycle_path(adjacency)
    if found:
        builder.add_issue(
            check="acyclic",
            code="cycle_detected",
            severity="error",
            path="$.edges",
            message="Execution plan edges contain a cycle.",
            witness={"cycle_path": found},
        )


def _check_upstream_dependencies(builder: ReportBuilder) -> None:
    node_ids = {_node_id(node) for node in _nodes(builder.plan)}
    edge_pairs = {
        (str(edge.get("from")), str(edge.get("to")))
        for edge in _edges(builder.plan)
        if isinstance(edge.get("from"), str) and isinstance(edge.get("to"), str)
    }
    for index, node in enumerate(_nodes(builder.plan)):
        node_id = _node_id(node)
        upstream_ids = set(_as_str_list(node.get("upstream_node_ids")))
        missing_upstream_nodes = sorted(upstream_ids - node_ids)
        if missing_upstream_nodes:
            builder.add_issue(
                check="upstream_dependency_consistency",
                code="upstream_node_missing",
                severity="error",
                path=f"$.nodes[{index}].upstream_node_ids",
                message="upstream_node_ids contains node ids not present in plan.nodes.",
                witness={"node_id": node_id, "missing_upstream_node_ids": missing_upstream_nodes},
            )
        missing_edges = sorted(upstream_id for upstream_id in upstream_ids if (upstream_id, node_id) not in edge_pairs)
        if missing_edges:
            builder.add_issue(
                check="upstream_dependency_consistency",
                code="upstream_edge_missing",
                severity="error",
                path=f"$.nodes[{index}].upstream_node_ids",
                message="upstream_node_ids must be represented by plan edges.",
                witness={"node_id": node_id, "upstream_without_edge": missing_edges},
            )
        edge_upstreams = {from_id for from_id, to_id in edge_pairs if to_id == node_id}
        extra_edges = sorted(edge_upstreams - upstream_ids)
        if extra_edges:
            builder.add_issue(
                check="upstream_dependency_consistency",
                code="edge_not_declared_upstream",
                severity="error",
                path="$.edges",
                message="Plan edges must correspond to each target node's upstream_node_ids.",
                witness={"node_id": node_id, "edge_sources_not_in_upstream_node_ids": extra_edges},
            )


def _check_ready_set(builder: ReportBuilder) -> dict[str, set[str]]:
    expected = _expected_ready_sets(builder.plan, builder.repo_root)
    ready_set = _as_mapping(builder.plan.get("ready_set"))
    for field_name, expected_ids in expected.items():
        actual_ids = set(_as_str_list(ready_set.get(field_name)))
        if actual_ids != expected_ids:
            builder.add_issue(
                check="ready_set_consistency",
                code="ready_set_mismatch",
                severity="error",
                path=f"$.ready_set.{field_name}",
                message=f"ready_set.{field_name} does not match manifest statuses and selected dependencies.",
                witness={
                    "field": field_name,
                    "expected": sorted(expected_ids),
                    "actual": sorted(actual_ids),
                },
            )
    return expected


def _check_status_derivation(builder: ReportBuilder, expected_sets: Mapping[str, set[str]]) -> None:
    expected_status = _expected_status(expected_sets)
    actual_status = builder.plan.get("status")
    if actual_status != expected_status:
        builder.add_issue(
            check="status_derivation_consistency",
            code="plan_status_mismatch",
            severity="error",
            path="$.status",
            message="Plan status must derive from invalid > blocked > incomplete > ready priority.",
            witness={"expected": expected_status, "actual": actual_status},
        )
    if actual_status == "blocked" and builder.plan.get("blocked_by"):
        builder.add_issue(
            check="status_derivation_consistency",
            code="plan_blocked",
            severity="warning",
            path="$.blocked_by",
            message="Plan is blocked by declared context or artifact contamination.",
            witness={"blocked_by": builder.plan.get("blocked_by")},
        )


def _check_context_policy_scope(builder: ReportBuilder) -> None:
    class_to_nodes_by_policy: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for node in _nodes(builder.plan):
        node_id = _node_id(node)
        manifest = _as_mapping(node.get("manifest"))
        context = _as_mapping(manifest.get("context_policy"))
        for policy_name in ("inject", "reference_only", "withhold", "forbidden"):
            for context_class in _as_str_list(context.get(policy_name)):
                class_to_nodes_by_policy[context_class][policy_name].append(node_id)

    for context_class, policy_nodes in sorted(class_to_nodes_by_policy.items()):
        active_policies = {policy for policy, nodes in policy_nodes.items() if nodes}
        permissive = active_policies & {"inject", "reference_only"}
        restrictive = active_policies & {"withhold", "forbidden"}
        if permissive and restrictive:
            builder.add_issue(
                check="context_policy_scope",
                code="context_policy_requires_node_scope",
                severity="warning",
                path="$.context_partition",
                message=(
                    "The same context class has permissive and restrictive policies across nodes; "
                    "future launchers must interpret context policy per node, not from aggregate partition alone."
                ),
                witness={
                    "context_class": context_class,
                    "nodes_by_policy": {policy: sorted(nodes) for policy, nodes in policy_nodes.items()},
                },
            )


def _check_dry_run_side_effects(builder: ReportBuilder) -> None:
    if builder.plan.get("dry_run") is not True:
        builder.add_issue(
            check="dry_run_side_effect_consistency",
            code="dry_run_not_true",
            severity="error",
            path="$.dry_run",
            message="Static verifier only accepts dry-run execution plans.",
            witness={"dry_run": builder.plan.get("dry_run")},
        )
    evaluation = _as_mapping(builder.plan.get("evaluation"))
    for flag in DRY_RUN_EVALUATION_FLAGS:
        if evaluation.get(flag) is not False:
            builder.add_issue(
                check="dry_run_side_effect_consistency",
                code="dry_run_dispatch_enabled",
                severity="error",
                path=f"$.evaluation.{flag}",
                message="Dry-run plan must not dispatch, execute, or write.",
                witness={"flag": flag, "value": evaluation.get(flag)},
            )
    for index, node in enumerate(_nodes(builder.plan)):
        level = node.get("side_effect_level")
        if level != "read_only":
            builder.add_issue(
                check="dry_run_side_effect_consistency",
                code="dry_run_node_side_effect_level_non_read_only",
                severity="warning",
                path=f"$.nodes[{index}].side_effect_level",
                message="Dry-run plan includes a node whose manifest implies non-read-only side effects.",
                witness={"node_id": _node_id(node), "side_effect_level": level},
            )


def _check_recovery_protocol(builder: ReportBuilder) -> None:
    recovery = _as_mapping(builder.plan.get("recovery_protocol"))
    required = ("local_retry", "local_patch", "request_replan", "escalation_order")
    for field in required:
        value = recovery.get(field)
        if field == "escalation_order":
            if not _as_str_list(value):
                builder.add_issue(
                    check="recovery_protocol_present",
                    code="recovery_protocol_missing_field",
                    severity="error",
                    path=f"$.recovery_protocol.{field}",
                    message="Recovery protocol must declare a non-empty escalation order.",
                    witness={"field": field, "value": value},
                )
        elif not isinstance(value, str) or not value:
            builder.add_issue(
                check="recovery_protocol_present",
                code="recovery_protocol_missing_field",
                severity="error",
                path=f"$.recovery_protocol.{field}",
                message="Recovery protocol must declare local retry, patch, and replan behavior.",
                witness={"field": field, "value": value},
            )


def build_report(plan: Mapping[str, Any], repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Build a static semantic verification report for a plan object."""
    repo_root = Path(repo_root)
    builder = ReportBuilder(plan, repo_root)
    _check_plan_schema(builder)
    _check_embedded_manifests(builder)
    _check_node_ids(builder)
    _check_edge_endpoints(builder)
    _check_acyclic(builder)
    _check_upstream_dependencies(builder)
    expected_sets = _check_ready_set(builder)
    _check_status_derivation(builder, expected_sets)
    _check_context_policy_scope(builder)
    _check_dry_run_side_effects(builder)
    _check_recovery_protocol(builder)
    return builder.build()


def _load_plan_file(path: Path) -> Mapping[str, Any]:
    value = loads_json_strict(path.read_text(encoding="utf-8"), source=str(path))
    if not isinstance(value, Mapping):
        raise ValueError("Plan file must contain a JSON object.")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Statically verify a dry-run reasoning execution plan.")
    parser.add_argument("--node-id", action="append", default=[], help="Node id to include when building a plan.")
    parser.add_argument("--plan-file", default=None, help="Existing plan JSON file to verify.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root.")
    parser.add_argument("--plan-id", default=None, help="Optional stable plan id when building a plan.")
    parser.add_argument("--source-work-item", default=None, help="Optional WorkItem/cap id grounding a built plan.")
    parser.add_argument(
        "--available-context",
        action="append",
        default=[],
        help="Context class present in a simulated launch packet. Repeatable.",
    )
    parser.add_argument(
        "--available-artifact",
        action="append",
        default=[],
        help="Artifact id present in a simulated launch packet. Repeatable.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON. Currently always true.")
    parser.add_argument("--check", action="store_true", help="Exit nonzero when semantic errors are found.")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    if args.plan_file:
        plan = _load_plan_file(Path(args.plan_file))
    else:
        if not args.node_id:
            parser.error("Provide --node-id at least once or --plan-file.")
        plan = plan_builder.build_plan(
            repo_root,
            node_ids=args.node_id,
            plan_id=args.plan_id,
            source_work_item=args.source_work_item,
            available_context=args.available_context,
            available_artifacts=args.available_artifact,
        )
    report = build_report(plan, repo_root)
    report_schema_issues = validate_report(report, repo_root)
    if report_schema_issues:
        print(
            json.dumps(
                {
                    "ok": False,
                    "schema_version": "reasoning_execution_plan_verification_report_check_v0",
                    "report_schema": _display_path(
                        repo_root / REPORT_SCHEMA_PATH.relative_to(REPO_ROOT),
                        repo_root,
                    ),
                    "plan_id": report.get("plan_id"),
                    "issues": report_schema_issues,
                },
                indent=2,
                sort_keys=False,
            )
        )
        return 2

    print(json.dumps(report, indent=2, sort_keys=False))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
