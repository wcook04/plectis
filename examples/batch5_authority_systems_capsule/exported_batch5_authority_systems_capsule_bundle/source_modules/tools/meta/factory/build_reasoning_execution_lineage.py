#!/usr/bin/env python3
"""Build dry-run execution lineage over verified reasoning execution plans."""
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

import build_reasoning_contract_packet as packet_builder  # noqa: E402
import build_reasoning_execution_plan as plan_builder  # noqa: E402
import verify_reasoning_execution_plan as plan_verifier  # noqa: E402


SCHEMA_VERSION = "reasoning_execution_lineage_v0"
LINEAGE_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_lineage.json"
)
PLAN_SCHEMA_PATH = REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_plan.json"
PLAN_REPORT_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_plan_verification_report.json"
)
PACKET_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_contract_packet_manifest.json"
)
STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_node_reasoning.json"
EXECUTION_LINEAGE_DISTILLATION_PATH = REPO_ROOT / "annexes" / "arxiv-2605-06365" / "distillation.json"
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


def _file_hash(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return None
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _source_refs(repo_root: Path) -> list[str]:
    refs = [
        STANDARD_PATH,
        PACKET_SCHEMA_PATH,
        PLAN_SCHEMA_PATH,
        PLAN_REPORT_SCHEMA_PATH,
        LINEAGE_SCHEMA_PATH,
        REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_contract_packet.py",
        REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_plan.py",
        REPO_ROOT / "tools" / "meta" / "factory" / "verify_reasoning_execution_plan.py",
        REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_lineage.py",
    ]
    if EXECUTION_LINEAGE_DISTILLATION_PATH.exists():
        refs.append(EXECUTION_LINEAGE_DISTILLATION_PATH)
    return [_display_path(path, repo_root) for path in refs]


def validate_lineage(lineage: Mapping[str, Any], repo_root: Path = REPO_ROOT) -> list[dict[str, str]]:
    """Validate an execution lineage record against the durable schema."""
    repo_root = Path(repo_root)
    schema_path = repo_root / LINEAGE_SCHEMA_PATH.relative_to(REPO_ROOT)
    schema = loads_json_strict(schema_path.read_text(encoding="utf-8"), source=_display_path(schema_path, repo_root))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(lineage),
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


def _plan_schema_issues(plan: Mapping[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    return [
        _issue(
            code="plan_schema_validation_error",
            severity="error",
            path=str(row.get("path") or "$.plan"),
            message=str(row.get("message") or "Execution plan failed schema validation."),
            witness={"schema_issue": dict(row)},
        )
        for row in plan_builder.validate_plan(plan, repo_root)
    ]


def _report_schema_issues(report: Mapping[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    return [
        _issue(
            code="verification_report_schema_validation_error",
            severity="error",
            path=str(row.get("path") or "$.verification_report"),
            message=str(row.get("message") or "Verification report failed schema validation."),
            witness={"schema_issue": dict(row)},
        )
        for row in plan_verifier.validate_report(report, repo_root)
    ]


def _report_issues(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in _as_list(report.get("issues")):
        if not isinstance(item, Mapping):
            continue
        result.append(
            _issue(
                code=str(item.get("code") or "verification_issue"),
                severity=str(item.get("severity") or "warning"),
                path=str(item.get("path") or "$.verification_report"),
                message=str(item.get("message") or "Static verification emitted an issue."),
                witness=_as_mapping(item.get("witness")),
            )
        )
    return result


def _verification_status(node: Mapping[str, Any], repo_root: Path) -> str:
    manifest = _as_mapping(node.get("manifest"))
    manifest_status = str(node.get("manifest_status") or manifest.get("status") or "")
    if manifest_status in TERMINAL_MANIFEST_STATUSES:
        return "invalid"
    if packet_builder.validate_manifest(manifest, repo_root):
        return "invalid"
    if manifest_status in {"ready", "blocked", "incomplete"}:
        return manifest_status
    return "invalid"


def _context_lineage(manifest: Mapping[str, Any]) -> dict[str, list[str]]:
    context = _as_mapping(manifest.get("context_policy"))
    artifact = _as_mapping(manifest.get("artifact_policy"))
    evaluation = _as_mapping(manifest.get("evaluation"))
    available_context = _as_str_list(evaluation.get("available_context"))
    available_artifacts = _as_str_list(evaluation.get("available_artifacts"))
    material_context_classes = {
        *(_as_str_list(context.get("inject"))),
        *(_as_str_list(context.get("reference_only"))),
        *(_as_str_list(context.get("withhold"))),
        *(_as_str_list(context.get("forbidden"))),
    }
    material_artifacts = {
        *(_as_str_list(artifact.get("required_artifacts"))),
        *(_as_str_list(artifact.get("optional_artifacts"))),
        *(_as_str_list(artifact.get("forbidden_artifacts"))),
    }
    return {
        "inject": _as_str_list(context.get("inject")),
        "reference_only": _as_str_list(context.get("reference_only")),
        "withhold": _as_str_list(context.get("withhold")),
        "forbidden": _as_str_list(context.get("forbidden")),
        "available_context": available_context,
        "available_artifacts": available_artifacts,
        "effective_context": [item for item in available_context if item in material_context_classes],
        "effective_artifacts": [item for item in available_artifacts if item in material_artifacts],
    }


def _manifest_contract_payload(manifest: Mapping[str, Any], context_lineage: Mapping[str, Any]) -> dict[str, Any]:
    """Return the manifest material that can affect replay apart from effective inputs.

    The raw packet manifest is still preserved through ``manifest_hash`` for
    provenance. Replay identity uses this availability-normalized contract
    payload so an unrelated globally available context class does not invalidate
    a node that neither consumes nor forbids it.
    """
    payload = json.loads(json.dumps(manifest, sort_keys=True))
    evaluation = payload.get("evaluation")
    if isinstance(evaluation, dict):
        evaluation["available_context"] = _as_str_list(context_lineage.get("effective_context"))
        evaluation["available_artifacts"] = _as_str_list(context_lineage.get("effective_artifacts"))
    artifact_policy = payload.get("artifact_policy")
    if isinstance(artifact_policy, dict):
        artifact_policy["available_artifacts"] = _as_str_list(context_lineage.get("effective_artifacts"))
        artifact_policy.pop("required_present", None)
        artifact_policy.pop("required_missing", None)
        artifact_policy.pop("artifact_presence_mode", None)
    payload.pop("blocked_by", None)
    return payload


def _node_path_hash(repo_root: Path, node_path: str | None) -> str | None:
    if not isinstance(node_path, str) or not node_path:
        return None
    return _file_hash(repo_root / node_path)


def _lineage_nodes(plan: Mapping[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    plan_nodes = [node for node in _as_list(plan.get("nodes")) if isinstance(node, Mapping)]
    manifest_hash_by_node_id = {
        str(node.get("node_id") or ""): _stable_hash(_as_mapping(node.get("manifest")))
        for node in plan_nodes
    }
    lineage_nodes: list[dict[str, Any]] = []
    for node in plan_nodes:
        node_id = str(node.get("node_id") or "")
        node_path = node.get("node_path") if isinstance(node.get("node_path"), str) else None
        manifest = _as_mapping(node.get("manifest"))
        node_hash = _node_path_hash(repo_root, node_path)
        manifest_hash = _stable_hash(manifest)
        upstream_manifest_hashes = [
            manifest_hash_by_node_id[upstream_id]
            for upstream_id in _as_str_list(node.get("upstream_node_ids"))
            if upstream_id in manifest_hash_by_node_id
        ]
        context_lineage = _context_lineage(manifest)
        manifest_contract_hash = _stable_hash(_manifest_contract_payload(manifest, context_lineage))
        identity_payload = {
            "node_hash": node_hash,
            "manifest_contract_hash": manifest_contract_hash,
            "upstream_manifest_hashes": upstream_manifest_hashes,
            "effective_context": context_lineage["effective_context"],
            "effective_artifacts": context_lineage["effective_artifacts"],
        }
        identity_material = [
            f"node_hash={node_hash}",
            f"manifest_contract_hash={manifest_contract_hash}",
            "upstream_manifest_hashes=" + ",".join(upstream_manifest_hashes),
            "effective_context=" + ",".join(context_lineage["effective_context"]),
            "effective_artifacts=" + ",".join(context_lineage["effective_artifacts"]),
        ]
        lineage_nodes.append(
            {
                "node_id": node_id,
                "node_path": node_path,
                "node_hash": node_hash,
                "manifest_hash": manifest_hash,
                "manifest_status": str(node.get("manifest_status") or manifest.get("status") or ""),
                "verification_status": _verification_status(node, repo_root),
                "dependencies": _as_str_list(node.get("dependencies")),
                "upstream_node_ids": _as_str_list(node.get("upstream_node_ids")),
                "output_artifact_kind": node.get("output_artifact_kind"),
                "schema_or_standard": node.get("schema_or_standard"),
                "context_lineage": context_lineage,
                "side_effect_level": str(node.get("side_effect_level") or "read_only"),
                "replay_identity": {
                    "identity_material": identity_material,
                    "replay_hash": _stable_hash(identity_payload),
                },
            }
        )
    return lineage_nodes


def _verification_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    issues = [item for item in _as_list(report.get("issues")) if isinstance(item, Mapping)]
    return {
        "ok": report.get("ok") is True,
        "error_count": sum(1 for item in issues if item.get("severity") == "error"),
        "warning_count": sum(1 for item in issues if item.get("severity") == "warning"),
        "checks": dict(_as_mapping(report.get("checks"))),
    }


def _dry_run_evaluation(plan: Mapping[str, Any]) -> dict[str, Any]:
    evaluation = _as_mapping(plan.get("evaluation"))
    return {
        "available_context": _as_str_list(evaluation.get("available_context")),
        "available_artifacts": _as_str_list(evaluation.get("available_artifacts")),
        "model_dispatch": False,
        "provider_dispatch": False,
        "runtime_execution": False,
        "writes": False,
    }


def _lineage_status(plan: Mapping[str, Any], report: Mapping[str, Any], issues: Sequence[Mapping[str, Any]]) -> str:
    if any(issue.get("severity") == "error" for issue in issues):
        return "invalid_lineage"
    plan_status = plan.get("status")
    if report.get("ok") is not True:
        return "invalid_lineage"
    if plan_status == "invalid_plan":
        return "invalid_lineage"
    if plan_status == "blocked":
        return "blocked"
    if plan_status == "incomplete":
        return "incomplete"
    return "ready"


def build_lineage(
    repo_root: Path = REPO_ROOT,
    *,
    node_ids: Sequence[str],
    plan_id: str | None = None,
    source_work_item: str | None = None,
    available_context: Sequence[str] = (),
    available_artifacts: Sequence[str] = (),
) -> dict[str, Any]:
    """Build dry-run execution lineage from a plan and static verifier report."""
    repo_root = Path(repo_root)
    plan = plan_builder.build_plan(
        repo_root,
        node_ids=node_ids,
        plan_id=plan_id,
        source_work_item=source_work_item,
        available_context=available_context,
        available_artifacts=available_artifacts,
    )
    verifier_report = plan_verifier.build_report(plan, repo_root)
    plan_hash = _stable_hash(plan)
    verifier_report_hash = _stable_hash(verifier_report)
    lineage_nodes = _lineage_nodes(plan, repo_root)
    issues = [
        *_plan_schema_issues(plan, repo_root),
        *_report_schema_issues(verifier_report, repo_root),
        *_report_issues(verifier_report),
    ]
    if plan.get("status") == "invalid_plan":
        issues.append(
            _issue(
                code="plan_invalid",
                severity="error",
                path="$.plan.plan_status",
                message="Execution lineage cannot be ready for an invalid execution plan.",
                witness={"plan_status": plan.get("status"), "plan_issues": plan.get("issues")},
            )
        )
    identity_hash = _stable_hash(
        {
            "plan_hash": plan_hash,
            "verifier_report_hash": verifier_report_hash,
            "node_replay_hashes": [
                node["replay_identity"]["replay_hash"] for node in lineage_nodes
            ],
        }
    )
    lineage = {
        "schema_version": SCHEMA_VERSION,
        "lineage_id": f"lineage_{plan.get('plan_id')}_{identity_hash.removeprefix('sha256:')[:12]}",
        "source_work_item": source_work_item,
        "source_refs": _source_refs(repo_root),
        "plan": {
            "plan_id": str(plan.get("plan_id") or ""),
            "plan_version": str(plan.get("plan_version") or ""),
            "plan_hash": plan_hash,
            "plan_status": str(plan.get("status") or ""),
            "verifier_ok": verifier_report.get("ok") is True,
            "verifier_report_hash": verifier_report_hash,
        },
        "nodes": lineage_nodes,
        "edges": [dict(edge) for edge in _as_list(plan.get("edges")) if isinstance(edge, Mapping)],
        "replay_policy": {
            "identity_based_replay": True,
            "replay_scope_mode": "downstream_of_changed_identity",
            "blocked_plan_replayable": False,
            "incomplete_plan_replayable": False,
        },
        "verification_summary": _verification_summary(verifier_report),
        "evaluation": _dry_run_evaluation(plan),
        "dry_run": True,
        "status": "ready",
        "issues": issues,
    }
    lineage["status"] = _lineage_status(plan, verifier_report, issues)
    return lineage


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build dry-run reasoning execution lineage from verified plan IR.")
    parser.add_argument("--node-id", action="append", required=True, help="Node id to include. Repeatable.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root.")
    parser.add_argument("--plan-id", default=None, help="Optional stable plan id.")
    parser.add_argument("--source-work-item", default=None, help="Optional WorkItem/cap id grounding this lineage.")
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
        help="Validate the generated lineage against its schema and emit a compact check report.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    lineage = build_lineage(
        repo_root,
        node_ids=args.node_id,
        plan_id=args.plan_id,
        source_work_item=args.source_work_item,
        available_context=args.available_context,
        available_artifacts=args.available_artifact,
    )
    schema_issues = validate_lineage(lineage, repo_root)
    if args.check:
        print(
            json.dumps(
                {
                    "ok": not schema_issues and lineage.get("status") != "invalid_lineage",
                    "schema_version": "reasoning_execution_lineage_check_v0",
                    "lineage_schema": _display_path(
                        repo_root / LINEAGE_SCHEMA_PATH.relative_to(REPO_ROOT),
                        repo_root,
                    ),
                    "lineage_id": lineage.get("lineage_id"),
                    "lineage_status": lineage.get("status"),
                    "verification_ok": _as_mapping(lineage.get("verification_summary")).get("ok"),
                    "issues": schema_issues,
                },
                indent=2,
                sort_keys=False,
            )
        )
        return 0 if not schema_issues and lineage.get("status") != "invalid_lineage" else 2
    if schema_issues:
        print(
            json.dumps(
                {
                    "ok": False,
                    "schema_version": "reasoning_execution_lineage_check_v0",
                    "lineage_schema": _display_path(
                        repo_root / LINEAGE_SCHEMA_PATH.relative_to(REPO_ROOT),
                        repo_root,
                    ),
                    "lineage_id": lineage.get("lineage_id"),
                    "lineage_status": lineage.get("status"),
                    "issues": schema_issues,
                },
                indent=2,
                sort_keys=False,
            )
        )
        return 2
    print(json.dumps(lineage, indent=2, sort_keys=False))
    return 1 if lineage.get("status") == "invalid_lineage" else 0


if __name__ == "__main__":
    raise SystemExit(main())
