#!/usr/bin/env python3
"""Build dry-run replay-scope reports over execution lineage records."""
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


SCHEMA_VERSION = "reasoning_execution_replay_scope_v0"
REPLAY_SCOPE_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_replay_scope.json"
)
LINEAGE_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_lineage.json"
)
STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_node_reasoning.json"
BUILD_SYSTEMS_DISTILLATION_PATH = REPO_ROOT / "annexes" / "build-systems-a-la-carte" / "distillation.json"
FORWARD_BUILD_DISTILLATION_PATH = REPO_ROOT / "annexes" / "arxiv-2202-05328" / "distillation.json"
LINEAGE_BUILDER_PATH = REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_lineage.py"
REPLAY_SCOPE_BUILDER_PATH = REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_replay_scope.py"
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
    refs = [
        STANDARD_PATH,
        LINEAGE_SCHEMA_PATH,
        REPLAY_SCOPE_SCHEMA_PATH,
        LINEAGE_BUILDER_PATH,
        REPLAY_SCOPE_BUILDER_PATH,
    ]
    if BUILD_SYSTEMS_DISTILLATION_PATH.exists():
        refs.append(BUILD_SYSTEMS_DISTILLATION_PATH)
    if FORWARD_BUILD_DISTILLATION_PATH.exists():
        refs.append(FORWARD_BUILD_DISTILLATION_PATH)
    return [_display_path(path, repo_root) for path in refs]


def validate_replay_scope(report: Mapping[str, Any], repo_root: Path = REPO_ROOT) -> list[dict[str, str]]:
    """Validate a replay-scope report against the durable schema."""
    repo_root = Path(repo_root)
    schema_path = repo_root / REPLAY_SCOPE_SCHEMA_PATH.relative_to(REPO_ROOT)
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


def _lineage_ref(lineage: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "lineage_id": lineage.get("lineage_id") if isinstance(lineage.get("lineage_id"), str) else None,
        "lineage_hash": _stable_hash(lineage),
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
    return pairs


def _replay_hash(node: Mapping[str, Any]) -> str | None:
    replay = _as_mapping(node.get("replay_identity"))
    value = replay.get("replay_hash")
    if not isinstance(value, str):
        return None
    if not value.startswith("sha256:") or len(value) != len("sha256:") + 64:
        return None
    suffix = value.removeprefix("sha256:")
    if any(char not in "0123456789abcdef" for char in suffix):
        return None
    return value


def _context_lineage(node: Mapping[str, Any]) -> Mapping[str, Any]:
    return _as_mapping(node.get("context_lineage"))


def _node_change_reasons(
    base_node: Mapping[str, Any] | None,
    candidate_node: Mapping[str, Any] | None,
) -> list[str]:
    if base_node is None:
        return ["node_added"]
    if candidate_node is None:
        return ["node_removed"]
    replay_changed = _replay_hash(base_node) != _replay_hash(candidate_node)
    status_changed = (
        base_node.get("verification_status") != candidate_node.get("verification_status")
        or base_node.get("manifest_status") != candidate_node.get("manifest_status")
    )
    if not replay_changed and not status_changed:
        return []
    reasons: list[str] = []
    if replay_changed and base_node.get("node_hash") != candidate_node.get("node_hash"):
        reasons.append("node_hash_changed")
    if replay_changed and base_node.get("manifest_hash") != candidate_node.get("manifest_hash"):
        reasons.append("manifest_hash_changed")
    if replay_changed and _context_lineage(base_node).get("effective_context") != _context_lineage(candidate_node).get("effective_context"):
        reasons.append("effective_context_changed")
    if replay_changed and _context_lineage(base_node).get("effective_artifacts") != _context_lineage(candidate_node).get("effective_artifacts"):
        reasons.append("effective_artifacts_changed")
    if base_node.get("verification_status") != candidate_node.get("verification_status"):
        reasons.append("verification_status_changed")
    if base_node.get("manifest_status") != candidate_node.get("manifest_status"):
        if candidate_node.get("manifest_status") == "blocked" or base_node.get("manifest_status") == "blocked":
            reasons.append("blocked_status_changed")
        else:
            reasons.append("manifest_status_changed")
    if replay_changed and not reasons:
        reasons.append("replay_hash_changed")
    return _dedupe(reasons)


def _node_changes(
    base: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> list[dict[str, Any]]:
    base_nodes = _node_map(base)
    candidate_nodes = _node_map(candidate)
    node_ids = sorted({*base_nodes, *candidate_nodes})
    changes: list[dict[str, Any]] = []
    for node_id in node_ids:
        base_node = base_nodes.get(node_id)
        candidate_node = candidate_nodes.get(node_id)
        reasons = _node_change_reasons(base_node, candidate_node)
        changes.append(
            {
                "node_id": node_id,
                "base_replay_hash": _replay_hash(base_node) if base_node is not None else None,
                "candidate_replay_hash": _replay_hash(candidate_node) if candidate_node is not None else None,
                "changed": bool(reasons),
                "change_reasons": reasons,
            }
        )
    return changes


def _downstream_closure(edges: Sequence[tuple[str, str]], roots: Iterable[str]) -> list[str]:
    adjacency: dict[str, list[str]] = {}
    for from_id, to_id in edges:
        adjacency.setdefault(from_id, []).append(to_id)
    seen: set[str] = set()
    queue = list(roots)
    while queue:
        current = queue.pop(0)
        for downstream in adjacency.get(current, []):
            if downstream in seen:
                continue
            seen.add(downstream)
            queue.append(downstream)
    return sorted(seen)


def _node_status_ids(lineage: Mapping[str, Any], status: str) -> list[str]:
    return sorted(
        str(node.get("node_id"))
        for node in _as_list(lineage.get("nodes"))
        if isinstance(node, Mapping)
        and isinstance(node.get("node_id"), str)
        and (node.get("manifest_status") == status or node.get("verification_status") == status)
    )


def _invalid_node_ids(lineage: Mapping[str, Any]) -> list[str]:
    return sorted(
        str(node.get("node_id"))
        for node in _as_list(lineage.get("nodes"))
        if isinstance(node, Mapping)
        and isinstance(node.get("node_id"), str)
        and (node.get("verification_status") == "invalid" or node.get("manifest_status") in {"not_found", "invalid_json", "no_reasoning_contract", "invalid_contract"})
    )


def _lineage_schema_issues(
    lineage: Mapping[str, Any],
    *,
    label: str,
    repo_root: Path,
) -> list[dict[str, Any]]:
    return [
        _issue(
            code=f"{label}_lineage_schema_validation_error",
            severity="error",
            path=f"$.{label}{str(row.get('path') or '$')[1:]}",
            message=str(row.get("message") or "Lineage schema validation failed."),
            witness={"schema_issue": dict(row)},
        )
        for row in lineage_builder.validate_lineage(lineage, repo_root)
    ]


def _lineage_status_issues(lineage: Mapping[str, Any], *, label: str) -> list[dict[str, Any]]:
    if lineage.get("status") != "invalid_lineage":
        return []
    return [
        _issue(
            code=f"{label}_lineage_invalid",
            severity="error",
            path=f"$.{label}.status",
            message=f"{label} lineage is invalid and cannot participate in replay-scope calculation.",
            witness={"lineage_status": lineage.get("status"), "lineage_issues": lineage.get("issues")},
        )
    ]


def _warnings(
    *,
    base: Mapping[str, Any],
    candidate: Mapping[str, Any],
    direct_changed: Sequence[str],
    replay_required: Sequence[str],
) -> list[str]:
    result: list[str] = []
    if candidate.get("status") == "blocked":
        result.append("candidate_lineage_blocked")
    if base.get("status") == "blocked":
        result.append("base_lineage_blocked")
    base_eval = _as_mapping(base.get("evaluation"))
    candidate_eval = _as_mapping(candidate.get("evaluation"))
    if (
        base_eval.get("available_context") != candidate_eval.get("available_context")
        or base_eval.get("available_artifacts") != candidate_eval.get("available_artifacts")
    ) and not direct_changed:
        result.append("global_availability_changed_without_node_effective_change")
    if direct_changed and len(replay_required) == len(_node_map(candidate)):
        result.append("full_replay_required")
    return _dedupe(result)


def _replay_mode(
    *,
    status: str,
    candidate: Mapping[str, Any],
    replay_required: Sequence[str],
    candidate_node_count: int,
) -> str:
    if status == "invalid_replay_scope":
        return "invalid"
    if candidate.get("status") == "blocked":
        return "blocked"
    if not replay_required:
        return "no_replay"
    if len(replay_required) >= candidate_node_count:
        return "full_replay"
    return "partial_replay"


def _dry_run_evaluation() -> dict[str, bool]:
    return {
        "model_dispatch": False,
        "provider_dispatch": False,
        "runtime_execution": False,
        "writes": False,
    }


def build_replay_scope(
    repo_root: Path = REPO_ROOT,
    *,
    base_lineage: Mapping[str, Any],
    candidate_lineage: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare base and candidate lineage records and emit a dry-run replay scope report."""
    repo_root = Path(repo_root)
    issues = [
        *_lineage_schema_issues(base_lineage, label="base", repo_root=repo_root),
        *_lineage_schema_issues(candidate_lineage, label="candidate", repo_root=repo_root),
        *_lineage_status_issues(base_lineage, label="base"),
        *_lineage_status_issues(candidate_lineage, label="candidate"),
    ]
    node_changes = _node_changes(base_lineage, candidate_lineage)
    direct_changed = sorted(row["node_id"] for row in node_changes if row["changed"])
    downstream = _downstream_closure(_edge_pairs(candidate_lineage), direct_changed)
    replay_required = sorted({*direct_changed, *downstream})
    invalid_node_ids = _invalid_node_ids(candidate_lineage)
    blocked_node_ids = _node_status_ids(candidate_lineage, "blocked")
    candidate_node_ids = sorted(_node_map(candidate_lineage))
    unaffected = sorted(
        node_id
        for node_id in candidate_node_ids
        if node_id not in set(replay_required)
        and node_id not in set(invalid_node_ids)
        and node_id not in set(blocked_node_ids)
    )
    status = "invalid_replay_scope" if issues else "blocked" if candidate_lineage.get("status") == "blocked" else "ready"
    mode = _replay_mode(
        status=status,
        candidate=candidate_lineage,
        replay_required=replay_required,
        candidate_node_count=len(candidate_node_ids),
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "source_refs": _source_refs(repo_root),
        "base": _lineage_ref(base_lineage),
        "candidate": _lineage_ref(candidate_lineage),
        "identity_changes": {
            "plan_changed": _as_mapping(base_lineage.get("plan")).get("plan_hash")
            != _as_mapping(candidate_lineage.get("plan")).get("plan_hash"),
            "verifier_report_changed": _as_mapping(base_lineage.get("plan")).get("verifier_report_hash")
            != _as_mapping(candidate_lineage.get("plan")).get("verifier_report_hash"),
            "nodes": node_changes,
        },
        "graph_impact": {
            "directly_changed_node_ids": direct_changed,
            "downstream_affected_node_ids": [node_id for node_id in downstream if node_id not in set(direct_changed)],
            "replay_required_node_ids": replay_required,
            "unaffected_node_ids": unaffected,
            "invalid_node_ids": invalid_node_ids,
            "blocked_node_ids": blocked_node_ids,
        },
        "replay_decision": {
            "mode": mode,
            "correctness_basis": "affected nodes include direct replay-identity changes and downstream closure over candidate plan edges; invalid or blocked candidate lineages are not schedulable",
            "minimality_basis": "unaffected nodes have unchanged node replay identity and are not downstream of changed nodes",
        },
        "warnings": _warnings(
            base=base_lineage,
            candidate=candidate_lineage,
            direct_changed=direct_changed,
            replay_required=replay_required,
        ),
        "evaluation": _dry_run_evaluation(),
        "dry_run": True,
        "status": status,
        "issues": issues,
    }
    return report


def _load_lineage_file(path: Path) -> Mapping[str, Any]:
    value = loads_json_strict(path.read_text(encoding="utf-8"), source=str(path))
    if not isinstance(value, Mapping):
        raise ValueError("Lineage file must contain a JSON object.")
    return value


def _build_lineage_pair(args: argparse.Namespace, repo_root: Path) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if args.base_lineage or args.candidate_lineage:
        if not args.base_lineage or not args.candidate_lineage:
            raise ValueError("Provide both --base-lineage and --candidate-lineage.")
        return _load_lineage_file(Path(args.base_lineage)), _load_lineage_file(Path(args.candidate_lineage))
    if not args.node_id:
        raise ValueError("Provide --node-id at least once or both lineage files.")
    base = lineage_builder.build_lineage(
        repo_root,
        node_ids=args.node_id,
        plan_id=args.plan_id,
        source_work_item=args.source_work_item,
        available_context=args.base_context,
        available_artifacts=args.base_artifact,
    )
    candidate = lineage_builder.build_lineage(
        repo_root,
        node_ids=args.node_id,
        plan_id=args.plan_id,
        source_work_item=args.source_work_item,
        available_context=args.candidate_context,
        available_artifacts=args.candidate_artifact,
    )
    return base, candidate


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a dry-run replay-scope report from execution lineage IR.")
    parser.add_argument("--node-id", action="append", default=[], help="Node id to include when building lineages. Repeatable.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root.")
    parser.add_argument("--plan-id", default=None, help="Optional stable plan id when building lineages.")
    parser.add_argument("--source-work-item", default=None, help="Optional WorkItem/cap id grounding built lineages.")
    parser.add_argument("--base-lineage", default=None, help="Existing base lineage JSON file.")
    parser.add_argument("--candidate-lineage", default=None, help="Existing candidate lineage JSON file.")
    parser.add_argument("--base-context", action="append", default=[], help="Base available context class. Repeatable.")
    parser.add_argument("--candidate-context", action="append", default=[], help="Candidate available context class. Repeatable.")
    parser.add_argument("--base-artifact", action="append", default=[], help="Base available artifact id. Repeatable.")
    parser.add_argument("--candidate-artifact", action="append", default=[], help="Candidate available artifact id. Repeatable.")
    parser.add_argument("--json", action="store_true", help="Emit JSON. Currently always true.")
    parser.add_argument("--check", action="store_true", help="Validate and emit a compact check report.")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    try:
        base_lineage, candidate_lineage = _build_lineage_pair(args, repo_root)
        report = build_replay_scope(
            repo_root,
            base_lineage=base_lineage,
            candidate_lineage=candidate_lineage,
        )
    except Exception as exc:
        report = {
            "schema_version": SCHEMA_VERSION,
            "source_refs": _source_refs(repo_root),
            "base": {"lineage_id": None, "lineage_hash": None, "status": None},
            "candidate": {"lineage_id": None, "lineage_hash": None, "status": None},
            "identity_changes": {"plan_changed": False, "verifier_report_changed": False, "nodes": []},
            "graph_impact": {
                "directly_changed_node_ids": [],
                "downstream_affected_node_ids": [],
                "replay_required_node_ids": [],
                "unaffected_node_ids": [],
                "invalid_node_ids": [],
                "blocked_node_ids": [],
            },
            "replay_decision": {
                "mode": "invalid",
                "correctness_basis": "lineage inputs could not be built or loaded",
                "minimality_basis": "minimality unavailable because replay-scope inputs are invalid",
            },
            "warnings": [],
            "evaluation": _dry_run_evaluation(),
            "dry_run": True,
            "status": "invalid_replay_scope",
            "issues": [
                _issue(
                    code="replay_scope_input_error",
                    severity="error",
                    path="$",
                    message=str(exc),
                    witness={"exception_type": type(exc).__name__},
                )
            ],
        }
    schema_issues = validate_replay_scope(report, repo_root)
    if args.check:
        print(
            json.dumps(
                {
                    "ok": not schema_issues and report.get("status") != "invalid_replay_scope",
                    "schema_version": "reasoning_execution_replay_scope_check_v0",
                    "replay_scope_schema": _display_path(
                        repo_root / REPLAY_SCOPE_SCHEMA_PATH.relative_to(REPO_ROOT),
                        repo_root,
                    ),
                    "base_lineage_id": _as_mapping(report.get("base")).get("lineage_id"),
                    "candidate_lineage_id": _as_mapping(report.get("candidate")).get("lineage_id"),
                    "replay_decision": _as_mapping(report.get("replay_decision")).get("mode"),
                    "status": report.get("status"),
                    "issues": schema_issues,
                },
                indent=2,
                sort_keys=False,
            )
        )
        return 0 if not schema_issues and report.get("status") != "invalid_replay_scope" else 2
    if schema_issues:
        print(
            json.dumps(
                {
                    "ok": False,
                    "schema_version": "reasoning_execution_replay_scope_check_v0",
                    "status": report.get("status"),
                    "issues": schema_issues,
                },
                indent=2,
                sort_keys=False,
            )
        )
        return 2
    print(json.dumps(report, indent=2, sort_keys=False))
    return 1 if report.get("status") == "invalid_replay_scope" else 0


if __name__ == "__main__":
    raise SystemExit(main())
