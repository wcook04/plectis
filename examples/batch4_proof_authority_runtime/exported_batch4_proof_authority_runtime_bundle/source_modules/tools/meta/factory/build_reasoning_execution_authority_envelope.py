#!/usr/bin/env python3
"""Build dry-run execution authority envelopes over schedule preflight IR."""
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
import build_reasoning_execution_schedule_preflight as schedule_builder  # noqa: E402


SCHEMA_VERSION = "reasoning_execution_authority_envelope_v0"
AUTHORITY_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_authority_envelope.json"
)
SCHEDULE_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_schedule_preflight.json"
)
LINEAGE_SCHEMA_PATH = REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_lineage.json"
REPLAY_SCOPE_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_replay_scope.json"
)
STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_node_reasoning.json"
COMPUTE_PROVIDER_STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_compute_provider.json"
PROVIDER_ADAPTER_STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_provider_adapter.json"
NODE_TOOL_STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_node_tool.json"
LINEAGE_BUILDER_PATH = REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_lineage.py"
REPLAY_SCOPE_BUILDER_PATH = (
    REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_replay_scope.py"
)
SCHEDULE_PREFLIGHT_BUILDER_PATH = (
    REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_schedule_preflight.py"
)
AUTHORITY_ENVELOPE_BUILDER_PATH = (
    REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_authority_envelope.py"
)
DRY_RUN_EVALUATION_FLAGS = ("model_dispatch", "provider_dispatch", "runtime_execution", "writes")
SIDE_EFFECT_LEVELS = {"read_only", "local_write", "commit", "external_action"}
MODEL_REPLAY_CAPABILITIES = ("context_read", "model_dispatch")


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
        COMPUTE_PROVIDER_STANDARD_PATH,
        PROVIDER_ADAPTER_STANDARD_PATH,
        NODE_TOOL_STANDARD_PATH,
        LINEAGE_SCHEMA_PATH,
        REPLAY_SCOPE_SCHEMA_PATH,
        SCHEDULE_SCHEMA_PATH,
        AUTHORITY_SCHEMA_PATH,
        LINEAGE_BUILDER_PATH,
        REPLAY_SCOPE_BUILDER_PATH,
        SCHEDULE_PREFLIGHT_BUILDER_PATH,
        AUTHORITY_ENVELOPE_BUILDER_PATH,
        "https://github.com/in-toto/in-toto",
        "https://slsa.dev/spec/v1.0/provenance",
        "https://papers.agoric.com/assets/pdf/papers/capability-myths-demolished.pdf",
    ]
    return [_display_path(path, repo_root) if isinstance(path, Path) else path for path in refs]


def validate_authority_envelope(envelope: Mapping[str, Any], repo_root: Path = REPO_ROOT) -> list[dict[str, str]]:
    """Validate an authority envelope against the durable schema."""
    repo_root = Path(repo_root)
    schema_path = repo_root / AUTHORITY_SCHEMA_PATH.relative_to(REPO_ROOT)
    schema = loads_json_strict(schema_path.read_text(encoding="utf-8"), source=_display_path(schema_path, repo_root))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(envelope),
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


def _load_json_object(path: Path) -> Mapping[str, Any]:
    value = loads_json_strict(path.read_text(encoding="utf-8"), source=str(path))
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def _lineage_ref(lineage: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "lineage_id": lineage.get("lineage_id") if isinstance(lineage.get("lineage_id"), str) else None,
        "lineage_hash": _stable_hash(lineage) if lineage else None,
        "status": lineage.get("status") if isinstance(lineage.get("status"), str) else None,
    }


def _schedule_ref(schedule_preflight: Mapping[str, Any]) -> dict[str, Any]:
    schedule = _as_mapping(schedule_preflight.get("schedule"))
    return {
        "status": schedule_preflight.get("status") if isinstance(schedule_preflight.get("status"), str) else None,
        "replay_order_node_ids": _as_str_list(schedule.get("replay_order_node_ids")),
        "schedule_preflight_hash": _stable_hash(schedule_preflight) if schedule_preflight else None,
    }


def _node_map(lineage: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    nodes: dict[str, Mapping[str, Any]] = {}
    for node in _as_list(lineage.get("nodes")):
        if not isinstance(node, Mapping):
            continue
        node_id = node.get("node_id")
        if isinstance(node_id, str) and node_id:
            nodes[node_id] = node
    return nodes


def _schedule_action_map(schedule_preflight: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    actions: dict[str, Mapping[str, Any]] = {}
    for action in _as_list(schedule_preflight.get("node_actions")):
        if not isinstance(action, Mapping):
            continue
        node_id = action.get("node_id")
        if isinstance(node_id, str) and node_id:
            actions[node_id] = action
    return actions


def _provider_policy() -> dict[str, Any]:
    return {
        "provider_required": False,
        "candidate_provider_class": None,
        "provider_standard_refs": [
            _display_path(COMPUTE_PROVIDER_STANDARD_PATH, REPO_ROOT),
            _display_path(PROVIDER_ADAPTER_STANDARD_PATH, REPO_ROOT),
        ],
    }


def _side_effect_ceiling(side_effect_level: str) -> dict[str, Any]:
    level = side_effect_level if side_effect_level in SIDE_EFFECT_LEVELS else "read_only"
    return {
        "read_only": level == "read_only",
        "writes_allowed": [] if level == "read_only" else ["future_runtime_grant_required"],
        "commit_allowed": level == "commit",
        "external_action_allowed": level == "external_action",
    }


def _requested_capabilities(action: str, side_effect_level: str) -> list[str]:
    if action not in {"replay", "blocked"}:
        return []
    capabilities = list(MODEL_REPLAY_CAPABILITIES)
    if side_effect_level in {"local_write", "commit", "external_action"}:
        capabilities.append("local_write")
    if side_effect_level == "commit":
        capabilities.append("commit")
    if side_effect_level == "external_action":
        capabilities.append("external_action")
    return _dedupe(capabilities)


def _context_egress(action: Mapping[str, Any]) -> dict[str, list[str]]:
    context = _as_mapping(action.get("context_lineage"))
    forbidden = _as_str_list(context.get("forbidden"))
    effective_context = _as_str_list(context.get("effective_context"))
    redaction_required = [item for item in effective_context if item in _as_str_list(context.get("withhold"))]
    return {
        "inject": _as_str_list(context.get("inject")),
        "reference_only": _as_str_list(context.get("reference_only")),
        "withhold": _as_str_list(context.get("withhold")),
        "forbidden": forbidden,
        "effective_context": effective_context,
        "redaction_required": sorted(set(redaction_required)),
    }


def _forbidden_effective_context(context_egress: Mapping[str, Any]) -> list[str]:
    forbidden = set(_as_str_list(context_egress.get("forbidden")))
    return sorted(item for item in _as_str_list(context_egress.get("effective_context")) if item in forbidden)


def _artifact_contract(lineage_node: Mapping[str, Any]) -> dict[str, Any]:
    output_artifact_kind = lineage_node.get("output_artifact_kind")
    schema_or_standard = lineage_node.get("schema_or_standard")
    return {
        "output_artifact_kind": output_artifact_kind if isinstance(output_artifact_kind, str) else None,
        "schema_or_standard": schema_or_standard if isinstance(schema_or_standard, str) else None,
        "receipt_required": True,
        "receipt_schema": "future_reasoning_execution_receipt_v0",
    }


def _provenance_materials(
    *,
    lineage_node: Mapping[str, Any],
    candidate_lineage: Mapping[str, Any],
    replay_scope: Mapping[str, Any],
    schedule_preflight: Mapping[str, Any],
    action: Mapping[str, Any],
) -> dict[str, Any]:
    plan = _as_mapping(candidate_lineage.get("plan"))
    schedule_hash = _stable_hash(schedule_preflight) if schedule_preflight else None
    lineage_hash = _stable_hash(candidate_lineage) if candidate_lineage else None
    replay_scope_hash = _stable_hash(replay_scope) if replay_scope else None
    return {
        "packet_manifest_hash": lineage_node.get("manifest_hash") if isinstance(lineage_node.get("manifest_hash"), str) else None,
        "execution_plan_hash": plan.get("plan_hash") if isinstance(plan.get("plan_hash"), str) else None,
        "verifier_report_hash": plan.get("verifier_report_hash") if isinstance(plan.get("verifier_report_hash"), str) else None,
        "lineage_hash": lineage_hash,
        "replay_scope_hash": replay_scope_hash,
        "schedule_preflight_hash": schedule_hash,
        "authority_envelope_input_hash": _stable_hash(
            {
                "lineage_node": {
                    "node_id": lineage_node.get("node_id"),
                    "manifest_hash": lineage_node.get("manifest_hash"),
                    "side_effect_level": lineage_node.get("side_effect_level"),
                    "replay_hash": _as_mapping(lineage_node.get("replay_identity")).get("replay_hash"),
                },
                "schedule_action": dict(action),
                "candidate_lineage_hash": lineage_hash,
                "replay_scope_hash": replay_scope_hash,
                "schedule_preflight_hash": schedule_hash,
            }
        ),
    }


def _authority_decision(
    *,
    action: str,
    side_effect_level: str,
    schedule_status: str,
    context_egress: Mapping[str, Any],
    artifact_contract: Mapping[str, Any],
    requested_capabilities: Sequence[str],
) -> tuple[str, str, list[str], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    if action == "invalid" or schedule_status == "invalid_schedule":
        return "invalid", "invalid_schedule_or_node_action", list(requested_capabilities), issues
    if action == "blocked" or schedule_status == "blocked":
        return "denied", "blocked_schedule_or_node_action", list(requested_capabilities), issues
    if action in {"reuse", "skip_not_demanded"}:
        return "no_grant_needed", "action_requires_no_runtime_authority", [], issues
    if action != "replay":
        return "invalid", "unknown_schedule_action", list(requested_capabilities), issues

    forbidden_present = _forbidden_effective_context(context_egress)
    if forbidden_present:
        issues.append(
            _issue(
                code="forbidden_effective_context",
                severity="error",
                path="$.node_authorities",
                message="Replay action carries effective context forbidden by node-scoped context policy.",
                witness={"forbidden_effective_context": forbidden_present},
            )
        )
        return "denied", "forbidden_effective_context", list(requested_capabilities), issues
    if side_effect_level != "read_only":
        issues.append(
            _issue(
                code="side_effect_escalation_requires_runtime_grant",
                severity="error",
                path="$.node_authorities",
                message="Dry-run authority envelope v0 denies replay actions above read_only side-effect level.",
                witness={"side_effect_level": side_effect_level},
            )
        )
        return "denied", "side_effect_escalation_denied_in_v0", list(requested_capabilities), issues
    if not artifact_contract.get("output_artifact_kind") or not artifact_contract.get("schema_or_standard"):
        issues.append(
            _issue(
                code="output_contract_missing",
                severity="error",
                path="$.node_authorities",
                message="Replay action cannot be grantable without an output artifact kind and schema or standard.",
                witness={"artifact_contract": dict(artifact_contract)},
            )
        )
        return "denied", "output_contract_missing", list(requested_capabilities), issues
    return "grantable", "dry_run_replay_action_is_grantable_but_not_launched", [], issues


def _node_authority(
    *,
    action: Mapping[str, Any],
    lineage_node: Mapping[str, Any],
    candidate_lineage: Mapping[str, Any],
    replay_scope: Mapping[str, Any],
    schedule_preflight: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    action_kind = str(action.get("action") or "invalid")
    side_effect_level = str(action.get("side_effect_level") or lineage_node.get("side_effect_level") or "read_only")
    context_egress = _context_egress(action)
    artifact_contract = _artifact_contract(lineage_node)
    requested_capabilities = _requested_capabilities(action_kind, side_effect_level)
    decision, reason, denied_capabilities, issues = _authority_decision(
        action=action_kind,
        side_effect_level=side_effect_level,
        schedule_status=str(schedule_preflight.get("status") or ""),
        context_egress=context_egress,
        artifact_contract=artifact_contract,
        requested_capabilities=requested_capabilities,
    )
    node = {
        "node_id": str(action.get("node_id") or lineage_node.get("node_id") or ""),
        "action": action_kind if action_kind in {"reuse", "replay", "skip_not_demanded", "blocked", "invalid"} else "invalid",
        "authority_decision": decision,
        "decision_reason": reason,
        "requested_capabilities": requested_capabilities,
        "granted_capabilities": [],
        "denied_capabilities": _dedupe(denied_capabilities),
        "context_egress": context_egress,
        "artifact_contract": artifact_contract,
        "side_effect_ceiling": _side_effect_ceiling(side_effect_level),
        "provider_policy": _provider_policy(),
        "provenance_materials": _provenance_materials(
            lineage_node=lineage_node,
            candidate_lineage=candidate_lineage,
            replay_scope=replay_scope,
            schedule_preflight=schedule_preflight,
            action=action,
        ),
    }
    return node, issues


def _input_schema_issues(
    *,
    candidate_lineage: Mapping[str, Any],
    replay_scope: Mapping[str, Any],
    schedule_preflight: Mapping[str, Any],
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
    if replay_scope:
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
    for row in schedule_builder.validate_schedule_preflight(schedule_preflight, repo_root):
        issues.append(
            _issue(
                code="schedule_preflight_schema_validation_error",
                severity="error",
                path=f"$.schedule_preflight{str(row.get('path') or '$')[1:]}",
                message=str(row.get("message") or "Schedule preflight failed schema validation."),
                witness={"schema_issue": dict(row)},
            )
        )
    return issues


def _envelope_status(
    *,
    schedule_status: str,
    issues: Sequence[Mapping[str, Any]],
    node_authorities: Sequence[Mapping[str, Any]],
) -> str:
    if any(issue.get("severity") == "error" for issue in issues if issue.get("code") not in {"side_effect_escalation_requires_runtime_grant", "forbidden_effective_context", "output_contract_missing"}):
        return "invalid_authority_envelope"
    if schedule_status == "invalid_schedule":
        return "invalid_authority_envelope"
    if any(node.get("authority_decision") == "invalid" for node in node_authorities):
        return "invalid_authority_envelope"
    if schedule_status == "blocked" or any(node.get("authority_decision") == "denied" for node in node_authorities):
        return "denied"
    if schedule_status == "no_op":
        return "no_op"
    return "ready"


def build_authority_envelope(
    repo_root: Path = REPO_ROOT,
    *,
    candidate_lineage: Mapping[str, Any],
    replay_scope: Mapping[str, Any],
    schedule_preflight: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a dry-run authority envelope from schedule preflight and lineage IR."""
    repo_root = Path(repo_root)
    lineage_nodes = _node_map(candidate_lineage)
    action_by_node_id = _schedule_action_map(schedule_preflight)
    node_authorities: list[dict[str, Any]] = []
    issues = _input_schema_issues(
        candidate_lineage=candidate_lineage,
        replay_scope=replay_scope,
        schedule_preflight=schedule_preflight,
        repo_root=repo_root,
    )
    for node_id in sorted(action_by_node_id):
        action = action_by_node_id[node_id]
        lineage_node = lineage_nodes.get(node_id)
        if lineage_node is None:
            issues.append(
                _issue(
                    code="node_action_missing_lineage_node",
                    severity="error",
                    path="$.node_authorities",
                    message="Schedule action references a node absent from candidate lineage.",
                    witness={"node_id": node_id},
                )
            )
            lineage_node = {"node_id": node_id}
        node_authority, node_issues = _node_authority(
            action=action,
            lineage_node=lineage_node,
            candidate_lineage=candidate_lineage,
            replay_scope=replay_scope,
            schedule_preflight=schedule_preflight,
        )
        node_authorities.append(node_authority)
        issues.extend(node_issues)

    status = _envelope_status(
        schedule_status=str(schedule_preflight.get("status") or ""),
        issues=issues,
        node_authorities=node_authorities,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "source_refs": _source_refs(repo_root),
        "schedule_preflight": _schedule_ref(schedule_preflight),
        "candidate_lineage": _lineage_ref(candidate_lineage),
        "authority_posture": {
            "mode": "dry_run_authority_preflight",
            "launch_authorized": False,
            "grant_materialized": False,
            "reason": "authority envelope only; runtime grant/signature not issued",
        },
        "node_authorities": node_authorities,
        "receipt_requirements": {
            "required_if_executed": True,
            "future_receipt_kind": "reasoning_execution_receipt_v0",
            "must_include": [
                "authority_envelope_hash",
                "schedule_preflight_hash",
                "candidate_lineage_hash",
                "actual_provider_or_actor",
                "actual_context_classes_sent",
                "output_artifact_hash",
                "schema_validation_result",
                "side_effects_observed",
            ],
        },
        "evaluation": _dry_run_evaluation(),
        "dry_run": True,
        "status": status,
        "issues": issues,
    }


def _build_inputs(
    args: argparse.Namespace,
    repo_root: Path,
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    if args.schedule_preflight:
        schedule_preflight = _load_json_object(Path(args.schedule_preflight))
        if not args.candidate_lineage:
            raise ValueError("--candidate-lineage is required when --schedule-preflight is provided.")
        candidate_lineage = _load_json_object(Path(args.candidate_lineage))
        replay_scope = _load_json_object(Path(args.replay_scope)) if args.replay_scope else {}
        return candidate_lineage, replay_scope, schedule_preflight

    candidate_lineage: Mapping[str, Any] | None = None
    replay_scope: Mapping[str, Any] | None = None
    if args.replay_scope:
        replay_scope = _load_json_object(Path(args.replay_scope))
    if args.candidate_lineage:
        candidate_lineage = _load_json_object(Path(args.candidate_lineage))
    if replay_scope is not None and candidate_lineage is None:
        raise ValueError("--candidate-lineage is required when --replay-scope is provided.")
    if candidate_lineage is not None and replay_scope is not None:
        schedule_preflight = schedule_builder.build_schedule_preflight(
            repo_root,
            candidate_lineage=candidate_lineage,
            replay_scope=replay_scope,
            target_node_ids=args.target_node_id,
            target_artifact_kinds=args.target_artifact_kind,
        )
        return candidate_lineage, replay_scope, schedule_preflight

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
    schedule_preflight = schedule_builder.build_schedule_preflight(
        repo_root,
        candidate_lineage=candidate_lineage,
        replay_scope=replay_scope,
        target_node_ids=args.target_node_id,
        target_artifact_kinds=args.target_artifact_kind,
    )
    return candidate_lineage, replay_scope, schedule_preflight


def _error_envelope(repo_root: Path, exc: Exception) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source_refs": _source_refs(repo_root),
        "schedule_preflight": {
            "status": None,
            "replay_order_node_ids": [],
            "schedule_preflight_hash": None,
        },
        "candidate_lineage": {"lineage_id": None, "lineage_hash": None, "status": None},
        "authority_posture": {
            "mode": "dry_run_authority_preflight",
            "launch_authorized": False,
            "grant_materialized": False,
            "reason": "authority envelope only; runtime grant/signature not issued",
        },
        "node_authorities": [],
        "receipt_requirements": {
            "required_if_executed": True,
            "future_receipt_kind": "reasoning_execution_receipt_v0",
            "must_include": [
                "authority_envelope_hash",
                "schedule_preflight_hash",
                "candidate_lineage_hash",
                "actual_provider_or_actor",
                "actual_context_classes_sent",
                "output_artifact_hash",
                "schema_validation_result",
                "side_effects_observed",
            ],
        },
        "evaluation": _dry_run_evaluation(),
        "dry_run": True,
        "status": "invalid_authority_envelope",
        "issues": [
            _issue(
                code="authority_envelope_input_error",
                severity="error",
                path="$",
                message=str(exc),
                witness={"exception_type": type(exc).__name__},
            )
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a dry-run reasoning execution authority envelope.")
    parser.add_argument("--node-id", action="append", default=[], help="Node id to include when building lineages. Repeatable.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root.")
    parser.add_argument("--plan-id", default=None, help="Optional stable plan id when building lineages.")
    parser.add_argument("--source-work-item", default=None, help="Optional WorkItem/cap id grounding built lineages.")
    parser.add_argument("--base-lineage", default=None, help="Existing base lineage JSON file.")
    parser.add_argument("--candidate-lineage", default=None, help="Existing candidate lineage JSON file.")
    parser.add_argument("--replay-scope", default=None, help="Existing replay-scope JSON file.")
    parser.add_argument("--schedule-preflight", default=None, help="Existing schedule-preflight JSON file. Requires --candidate-lineage.")
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
        candidate_lineage, replay_scope, schedule_preflight = _build_inputs(args, repo_root)
        envelope = build_authority_envelope(
            repo_root,
            candidate_lineage=candidate_lineage,
            replay_scope=replay_scope,
            schedule_preflight=schedule_preflight,
        )
    except Exception as exc:
        envelope = _error_envelope(repo_root, exc)
    schema_issues = validate_authority_envelope(envelope, repo_root)
    if args.check:
        print(
            json.dumps(
                {
                    "ok": not schema_issues and envelope.get("status") != "invalid_authority_envelope",
                    "schema_version": "reasoning_execution_authority_envelope_check_v0",
                    "authority_envelope_schema": _display_path(
                        repo_root / AUTHORITY_SCHEMA_PATH.relative_to(REPO_ROOT),
                        repo_root,
                    ),
                    "candidate_lineage_id": _as_mapping(envelope.get("candidate_lineage")).get("lineage_id"),
                    "schedule_status": _as_mapping(envelope.get("schedule_preflight")).get("status"),
                    "status": envelope.get("status"),
                    "launch_authorized": _as_mapping(envelope.get("authority_posture")).get("launch_authorized"),
                    "grant_materialized": _as_mapping(envelope.get("authority_posture")).get("grant_materialized"),
                    "issues": schema_issues,
                },
                indent=2,
                sort_keys=False,
            )
        )
        return 0 if not schema_issues and envelope.get("status") != "invalid_authority_envelope" else 2
    if schema_issues:
        print(
            json.dumps(
                {
                    "ok": False,
                    "schema_version": "reasoning_execution_authority_envelope_check_v0",
                    "status": envelope.get("status"),
                    "issues": schema_issues,
                },
                indent=2,
                sort_keys=False,
            )
        )
        return 2
    print(json.dumps(envelope, indent=2, sort_keys=False))
    return 1 if envelope.get("status") == "invalid_authority_envelope" else 0


if __name__ == "__main__":
    raise SystemExit(main())
