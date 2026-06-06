#!/usr/bin/env python3
"""Build a dry-run execution plan from reasoning contract packet manifests."""
from __future__ import annotations

import argparse
import json
import re
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

from system.lib.strict_json import StrictJsonError, loads_json_strict  # noqa: E402

import build_reasoning_contract_packet as packet_builder  # noqa: E402


SCHEMA_VERSION = "reasoning_execution_plan_v0"
PLAN_VERSION = "0.1"
PLAN_SCHEMA_PATH = REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_plan.json"
PACKET_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_contract_packet_manifest.json"
)
STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_node_reasoning.json"
AGENTSPEX_DISTILLATION_PATH = REPO_ROOT / "annexes" / "arxiv-2604-13346" / "distillation.json"
TERMINAL_MANIFEST_STATUSES = {"not_found", "invalid_json", "no_reasoning_contract", "invalid_contract"}


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


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


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


def _plan_id_for(node_ids: Sequence[str]) -> str:
    slug = "_".join(re.sub(r"[^A-Za-z0-9_]+", "_", node_id).strip("_") for node_id in node_ids)
    return f"plan_{slug or 'empty'}"


def _source_refs(repo_root: Path) -> list[str]:
    refs = [
        STANDARD_PATH,
        PACKET_SCHEMA_PATH,
        PLAN_SCHEMA_PATH,
        REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_contract_packet.py",
        REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_plan.py",
    ]
    if AGENTSPEX_DISTILLATION_PATH.exists():
        refs.append(AGENTSPEX_DISTILLATION_PATH)
    return [_display_path(path, repo_root) for path in refs]


def validate_plan(plan: Mapping[str, Any], repo_root: Path = REPO_ROOT) -> list[dict[str, str]]:
    """Validate a dry-run execution plan against the durable plan schema."""
    repo_root = Path(repo_root)
    schema_path = repo_root / PLAN_SCHEMA_PATH.relative_to(REPO_ROOT)
    schema = loads_json_strict(schema_path.read_text(encoding="utf-8"), source=_display_path(schema_path, repo_root))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(plan),
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


def _load_node_json(node_path: str | None, repo_root: Path) -> Mapping[str, Any]:
    if not node_path:
        return {}
    path = repo_root / node_path
    try:
        raw = loads_json_strict(path.read_text(encoding="utf-8"), source=node_path)
    except (FileNotFoundError, StrictJsonError):
        return {}
    return raw if isinstance(raw, Mapping) else {}


def _retry_policy(node_json: Mapping[str, Any]) -> dict[str, Any]:
    execution = _as_mapping(node_json.get("execution"))
    retries = execution.get("retries")
    if isinstance(retries, int) and retries >= 0:
        return {"max_attempts": retries + 1, "source": "node.execution.retries"}
    return {"max_attempts": 1, "source": "default_no_retry"}


def _side_effect_level(manifest: Mapping[str, Any]) -> str:
    side_effect = _as_mapping(manifest.get("side_effect_policy"))
    if side_effect.get("external_action_allowed") is True:
        return "external_action"
    if side_effect.get("commit_allowed") is True:
        return "commit"
    writes_allowed = side_effect.get("writes_allowed")
    if isinstance(writes_allowed, list) and writes_allowed:
        return "local_write"
    return "read_only"


def _plan_node(
    *,
    repo_root: Path,
    manifest: Mapping[str, Any],
    selected_node_ids: set[str],
) -> dict[str, Any]:
    node_json = _load_node_json(manifest.get("node_path"), repo_root)
    dependencies = _as_str_list(node_json.get("dependencies"))
    upstream_node_ids = [node_id for node_id in dependencies if node_id in selected_node_ids]
    artifact_policy = _as_mapping(manifest.get("artifact_policy"))
    return {
        "node_id": str(manifest.get("node_id") or ""),
        "node_path": manifest.get("node_path"),
        "manifest_status": str(manifest.get("status") or ""),
        "manifest": dict(manifest),
        "dependencies": dependencies,
        "upstream_node_ids": upstream_node_ids,
        "join_mode": "all_upstream_ready",
        "retry_policy": _retry_policy(node_json),
        "side_effect_level": _side_effect_level(manifest),
        "output_artifact_kind": artifact_policy.get("output_artifact_kind"),
        "schema_or_standard": artifact_policy.get("schema_or_standard"),
    }


def _manifest_issues(
    *,
    repo_root: Path,
    manifest: Mapping[str, Any],
) -> list[dict[str, str | None]]:
    node_id = manifest.get("node_id")
    result: list[dict[str, str | None]] = []
    status = manifest.get("status")
    if status in TERMINAL_MANIFEST_STATUSES:
        issues = manifest.get("issues")
        if isinstance(issues, list) and issues:
            for issue in issues:
                if not isinstance(issue, Mapping):
                    continue
                result.append(
                    {
                        "node_id": str(node_id) if isinstance(node_id, str) else None,
                        "path": str(issue.get("path") or "manifest"),
                        "code": str(issue.get("code") or status),
                        "message": str(issue.get("message") or f"Manifest status is {status}."),
                    }
                )
        else:
            result.append(
                {
                    "node_id": str(node_id) if isinstance(node_id, str) else None,
                    "path": "manifest.status",
                    "code": str(status),
                    "message": f"Manifest status is {status}.",
                }
            )
    for issue in packet_builder.validate_manifest(manifest, repo_root):
        result.append(
            {
                "node_id": str(node_id) if isinstance(node_id, str) else None,
                "path": str(issue.get("path") or "manifest"),
                "code": str(issue.get("code") or "packet_manifest_schema_validation_error"),
                "message": str(issue.get("message") or "Packet manifest failed schema validation."),
            }
        )
    return result


def _blocked_items(manifest: Mapping[str, Any]) -> list[dict[str, str]]:
    node_id = manifest.get("node_id")
    blocked = manifest.get("blocked_by")
    if not isinstance(blocked, list) or not isinstance(node_id, str):
        return []
    result: list[dict[str, str]] = []
    for item in blocked:
        if not isinstance(item, Mapping):
            continue
        row = {
            "node_id": node_id,
            "kind": str(item.get("kind") or ""),
            "source_field": str(item.get("source_field") or ""),
            "reason": str(item.get("reason") or ""),
        }
        if isinstance(item.get("class"), str):
            row["class"] = str(item["class"])
        if isinstance(item.get("artifact"), str):
            row["artifact"] = str(item["artifact"])
        result.append(row)
    return result


def _context_partition(manifests: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    inject: list[str] = []
    reference_only: list[str] = []
    withhold: list[str] = []
    forbidden: list[str] = []
    for manifest in manifests:
        context = _as_mapping(manifest.get("context_policy"))
        inject.extend(_as_str_list(context.get("inject")))
        reference_only.extend(_as_str_list(context.get("reference_only")))
        withhold.extend(_as_str_list(context.get("withhold")))
        forbidden.extend(_as_str_list(context.get("forbidden")))
    return {
        "execution_context_classes": _dedupe(inject),
        "reference_only_context_classes": _dedupe(reference_only),
        "withheld_context_classes": _dedupe(withhold),
        "forbidden_context_classes": _dedupe(forbidden),
        "diagnostic_context_classes": _dedupe([*reference_only, *withhold]),
    }


def _dry_run_evaluation(
    *,
    available_context: Sequence[str],
    available_artifacts: Sequence[str],
) -> dict[str, Any]:
    return {
        "available_context": [item for item in available_context if isinstance(item, str)],
        "available_artifacts": [item for item in available_artifacts if isinstance(item, str)],
        "model_dispatch": False,
        "provider_dispatch": False,
        "runtime_execution": False,
        "writes": False,
    }


def build_plan(
    repo_root: Path = REPO_ROOT,
    *,
    node_ids: Sequence[str],
    plan_id: str | None = None,
    source_work_item: str | None = None,
    available_context: Sequence[str] = (),
    available_artifacts: Sequence[str] = (),
) -> dict[str, Any]:
    """Build a dry-run plan by composing node-local reasoning packet manifests."""
    repo_root = Path(repo_root)
    node_id_list = [node_id for node_id in node_ids if isinstance(node_id, str) and node_id]
    selected_node_ids = set(node_id_list)
    manifests = [
        packet_builder.build_manifest(
            repo_root,
            node_id=node_id,
            available_context=available_context,
            available_artifacts=available_artifacts,
        )
        for node_id in node_id_list
    ]
    plan_nodes = [
        _plan_node(repo_root=repo_root, manifest=manifest, selected_node_ids=selected_node_ids)
        for manifest in manifests
    ]
    edges = [
        {"from": upstream, "to": node["node_id"], "dependency_type": "node_dependency"}
        for node in plan_nodes
        for upstream in node["upstream_node_ids"]
    ]

    invalid_node_ids = [
        node["node_id"]
        for node, manifest in zip(plan_nodes, manifests)
        if manifest.get("status") in TERMINAL_MANIFEST_STATUSES
        or packet_builder.validate_manifest(manifest, repo_root)
    ]
    blocked_node_ids = [node["node_id"] for node, manifest in zip(plan_nodes, manifests) if manifest.get("status") == "blocked"]
    incomplete_node_ids = [
        node["node_id"] for node, manifest in zip(plan_nodes, manifests) if manifest.get("status") == "incomplete"
    ]
    ready_node_ids = [
        node["node_id"]
        for node, manifest in zip(plan_nodes, manifests)
        if manifest.get("status") == "ready" and not node["upstream_node_ids"]
    ]

    if invalid_node_ids:
        status = "invalid_plan"
    elif blocked_node_ids:
        status = "blocked"
    elif incomplete_node_ids:
        status = "incomplete"
    else:
        status = "ready"

    blocked_by = [item for manifest in manifests for item in _blocked_items(manifest)]
    issues = [
        issue
        for manifest in manifests
        for issue in _manifest_issues(repo_root=repo_root, manifest=manifest)
        if isinstance(issue.get("path"), str)
        and isinstance(issue.get("code"), str)
        and isinstance(issue.get("message"), str)
    ]
    artifact_kinds = _dedupe(node.get("output_artifact_kind") for node in plan_nodes)
    schemas_or_standards = _dedupe(node.get("schema_or_standard") for node in plan_nodes)
    residual_routing = _dedupe(
        _as_mapping(manifest.get("trace_policy")).get("residual_routing") for manifest in manifests
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "plan_id": plan_id or _plan_id_for(node_id_list),
        "plan_version": PLAN_VERSION,
        "source_work_item": source_work_item,
        "source_refs": _source_refs(repo_root),
        "nodes": plan_nodes,
        "edges": edges,
        "ready_set": {
            "policy": "deterministic_topological",
            "ready_node_ids": ready_node_ids,
            "blocked_node_ids": blocked_node_ids,
            "incomplete_node_ids": incomplete_node_ids,
            "invalid_node_ids": invalid_node_ids,
            "all_node_ids": [node["node_id"] for node in plan_nodes],
        },
        "context_partition": _context_partition(manifests),
        "recovery_protocol": {
            "local_retry": "node_retry_policy_only_no_provider_dispatch_in_dry_run",
            "local_patch": "patch_node_overlay_or_packet_builder_after_validation_failure",
            "request_replan": "emit_task_ledger_residual_when_plan_invalid_or_context_forbidden",
            "escalation_order": ["local_retry", "local_patch", "request_replan"],
        },
        "plan_output_contract": {
            "artifact_kinds": artifact_kinds,
            "schemas_or_standards": schemas_or_standards,
        },
        "residual_routing": residual_routing,
        "blocked_by": blocked_by,
        "issues": issues,
        "evaluation": _dry_run_evaluation(
            available_context=available_context,
            available_artifacts=available_artifacts,
        ),
        "dry_run": True,
        "status": status,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a dry-run reasoning execution plan from node packet manifests."
    )
    parser.add_argument("--node-id", action="append", required=True, help="Node id to include. Repeatable.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root.")
    parser.add_argument("--plan-id", default=None, help="Optional stable plan id.")
    parser.add_argument("--source-work-item", default=None, help="Optional WorkItem/cap id grounding this plan.")
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
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the generated plan against its schema and emit a compact check report.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    plan = build_plan(
        repo_root,
        node_ids=args.node_id,
        plan_id=args.plan_id,
        source_work_item=args.source_work_item,
        available_context=args.available_context,
        available_artifacts=args.available_artifact,
    )
    schema_issues = validate_plan(plan, repo_root)
    if args.check:
        print(
            json.dumps(
                {
                    "ok": not schema_issues,
                    "schema_version": "reasoning_execution_plan_check_v0",
                    "plan_schema": _display_path(
                        repo_root / PLAN_SCHEMA_PATH.relative_to(REPO_ROOT),
                        repo_root,
                    ),
                    "plan_id": plan.get("plan_id"),
                    "plan_status": plan.get("status"),
                    "issues": schema_issues,
                },
                indent=2,
                sort_keys=False,
            )
        )
        return 0 if not schema_issues else 2
    if schema_issues:
        print(
            json.dumps(
                {
                    "ok": False,
                    "schema_version": "reasoning_execution_plan_check_v0",
                    "plan_schema": _display_path(
                        repo_root / PLAN_SCHEMA_PATH.relative_to(REPO_ROOT),
                        repo_root,
                    ),
                    "plan_id": plan.get("plan_id"),
                    "plan_status": plan.get("status"),
                    "issues": schema_issues,
                },
                indent=2,
                sort_keys=False,
            )
        )
        return 2
    print(json.dumps(plan, indent=2, sort_keys=False))
    return 1 if plan.get("status") == "invalid_plan" else 0


if __name__ == "__main__":
    raise SystemExit(main())
