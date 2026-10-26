#!/usr/bin/env python3
"""Build dry-run reasoning execution grant leases over authority envelopes."""
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

import build_reasoning_execution_authority_envelope as authority_builder  # noqa: E402


SCHEMA_VERSION = "reasoning_execution_grant_lease_v0"
CHECK_SCHEMA_VERSION = "reasoning_execution_grant_lease_check_v0"
GRANT_LEASE_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_grant_lease.json"
)
AUTHORITY_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_authority_envelope.json"
)
STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_node_reasoning.json"
AUTHORITY_ENVELOPE_BUILDER_PATH = (
    REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_authority_envelope.py"
)
GRANT_LEASE_BUILDER_PATH = (
    REPO_ROOT / "tools" / "meta" / "factory" / "build_reasoning_execution_grant_lease.py"
)
MACAROONS_REF = (
    "https://www.ndss-symposium.org/ndss2014/ndss-2014-programme/"
    "macaroons-cookies-contextual-caveats-decentralized-authorization-cloud/"
)
UCAN_REF = "https://ucan.xyz/"
DISPATCH_FLAGS = ("model_dispatch", "provider_dispatch", "runtime_execution", "writes")
SIDE_EFFECT_CAPABILITIES = {"local_write", "commit", "external_action"}


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


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


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
        if not isinstance(item, str) or not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _load_json_object(path: Path) -> Mapping[str, Any]:
    value = loads_json_strict(path.read_text(encoding="utf-8"), source=str(path))
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


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


def _source_refs(repo_root: Path) -> list[str]:
    refs: list[Path | str] = [
        STANDARD_PATH,
        AUTHORITY_SCHEMA_PATH,
        GRANT_LEASE_SCHEMA_PATH,
        AUTHORITY_ENVELOPE_BUILDER_PATH,
        GRANT_LEASE_BUILDER_PATH,
        MACAROONS_REF,
        UCAN_REF,
    ]
    return [_display_path(path, repo_root) if isinstance(path, Path) else path for path in refs]


def _dry_run_evaluation() -> dict[str, bool]:
    return {
        "model_dispatch": False,
        "provider_dispatch": False,
        "runtime_execution": False,
        "writes": False,
    }


def validate_grant_lease(lease: Mapping[str, Any], repo_root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    """Validate a grant lease against the durable schema."""
    repo_root = Path(repo_root)
    schema_path = repo_root / GRANT_LEASE_SCHEMA_PATH.relative_to(REPO_ROOT)
    schema = loads_json_strict(schema_path.read_text(encoding="utf-8"), source=_display_path(schema_path, repo_root))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(lease),
        key=lambda error: (list(error.path), list(error.schema_path), error.message),
    )
    return [
        _issue(
            code="grant_lease_schema_validation_error",
            severity="error",
            path=_json_path(error.path),
            message=error.message,
            witness={"schema_path": _json_path(error.schema_path)},
        )
        for error in errors
    ]


def _node_authority(authority_envelope: Mapping[str, Any], node_id: str) -> Mapping[str, Any] | None:
    for node in _as_list(authority_envelope.get("node_authorities")):
        if isinstance(node, Mapping) and node.get("node_id") == node_id:
            return node
    return None


def _single_node_id(authority_envelope: Mapping[str, Any]) -> str | None:
    nodes = [node for node in _as_list(authority_envelope.get("node_authorities")) if isinstance(node, Mapping)]
    if len(nodes) != 1:
        return None
    node_id = nodes[0].get("node_id")
    return node_id if isinstance(node_id, str) and node_id else None


def _allowed_context(context_egress: Mapping[str, Any]) -> list[str]:
    return _dedupe(_as_str_list(context_egress.get("inject")) + _as_str_list(context_egress.get("reference_only")))


def _forbidden_effective_context(context_egress: Mapping[str, Any]) -> list[str]:
    forbidden = set(_as_str_list(context_egress.get("forbidden")))
    return sorted(item for item in _as_str_list(context_egress.get("effective_context")) if item in forbidden)


def _lease_status_and_issues(
    *,
    authority_envelope: Mapping[str, Any],
    node_authority: Mapping[str, Any],
    input_issues: Sequence[Mapping[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    issues = [dict(issue) for issue in input_issues]
    envelope_status = authority_envelope.get("status")
    node_decision = node_authority.get("authority_decision")
    requested = set(_as_str_list(node_authority.get("requested_capabilities")))
    context_egress = _as_mapping(node_authority.get("context_egress"))
    artifact_contract = _as_mapping(node_authority.get("artifact_contract"))

    if input_issues:
        return "invalid_grant_lease", issues
    if envelope_status == "invalid_authority_envelope":
        issues.append(
            _issue(
                code="authority_envelope_invalid",
                severity="error",
                path="$.authority_envelope_hash",
                message="Cannot issue or mark eligible a grant lease from an invalid authority envelope.",
                witness={"authority_envelope_status": envelope_status},
            )
        )
        return "invalid_grant_lease", issues
    if envelope_status != "ready":
        return "denied", issues
    if node_decision != "grantable":
        return "denied", issues
    if sorted(requested & SIDE_EFFECT_CAPABILITIES):
        issues.append(
            _issue(
                code="side_effect_capability_denied_in_v0",
                severity="error",
                path="$.capabilities.requested",
                message="Grant lease v0 denies local write, commit, and external action capabilities.",
                witness={"requested": sorted(requested)},
            )
        )
        return "denied", issues
    forbidden_effective = _forbidden_effective_context(context_egress)
    if forbidden_effective:
        issues.append(
            _issue(
                code="forbidden_effective_context",
                severity="error",
                path="$.caveats.effective_context_bound",
                message="Grant lease cannot be eligible when effective context intersects forbidden context.",
                witness={"forbidden_effective_context": forbidden_effective},
            )
        )
        return "denied", issues
    if not artifact_contract.get("output_artifact_kind") or not artifact_contract.get("schema_or_standard"):
        issues.append(
            _issue(
                code="output_contract_missing",
                severity="error",
                path="$.caveats",
                message="Grant lease cannot be eligible without output artifact kind and schema or standard.",
                witness={"artifact_contract": dict(artifact_contract)},
            )
        )
        return "denied", issues
    return "eligible_unissued", issues


def build_grant_lease(
    repo_root: Path = REPO_ROOT,
    *,
    authority_envelope: Mapping[str, Any],
    node_id: str,
) -> dict[str, Any]:
    """Build a dry-run grant lease from an authority envelope node decision."""
    repo_root = Path(repo_root)
    authority_hash = _stable_hash(authority_envelope)
    input_issues: list[dict[str, Any]] = []
    for row in authority_builder.validate_authority_envelope(authority_envelope, repo_root):
        input_issues.append(
            _issue(
                code="authority_envelope_schema_validation_error",
                severity="error",
                path=f"$.authority_envelope{str(row.get('path') or '$')[1:]}",
                message=str(row.get("message") or "Authority envelope failed schema validation."),
                witness={"schema_issue": dict(row)},
            )
        )

    node_authority = _node_authority(authority_envelope, node_id)
    if node_authority is None:
        input_issues.append(
            _issue(
                code="node_authority_not_found",
                severity="error",
                path="$.node_id",
                message="Grant lease node_id is absent from the authority envelope.",
                witness={"node_id": node_id},
            )
        )
        node_authority = {
            "node_id": node_id,
            "authority_decision": "invalid",
            "requested_capabilities": [],
            "denied_capabilities": [],
            "context_egress": {
                "inject": [],
                "reference_only": [],
                "withhold": [],
                "forbidden": [],
                "effective_context": [],
                "redaction_required": [],
            },
            "artifact_contract": {
                "output_artifact_kind": None,
                "schema_or_standard": None,
            },
            "side_effect_ceiling": {
                "read_only": True,
                "writes_allowed": [],
                "commit_allowed": False,
                "external_action_allowed": False,
            },
            "provenance_materials": {},
        }

    context_egress = _as_mapping(node_authority.get("context_egress"))
    artifact_contract = _as_mapping(node_authority.get("artifact_contract"))
    provenance = _as_mapping(node_authority.get("provenance_materials"))
    requested = _as_str_list(node_authority.get("requested_capabilities"))
    denied = _as_str_list(node_authority.get("denied_capabilities"))
    status, issues = _lease_status_and_issues(
        authority_envelope=authority_envelope,
        node_authority=node_authority,
        input_issues=input_issues,
    )
    grantable = requested if status == "eligible_unissued" else []
    denied_capabilities = _dedupe(denied + ([] if status == "eligible_unissued" else requested))
    grant_id = "grant_" + node_id + "_" + _stable_hash({"authority": authority_hash, "node_id": node_id})[-12:]
    schedule = _as_mapping(authority_envelope.get("schedule_preflight"))
    lineage = _as_mapping(authority_envelope.get("candidate_lineage"))
    return {
        "schema_version": SCHEMA_VERSION,
        "source_refs": _source_refs(repo_root),
        "grant_id": grant_id,
        "node_id": node_id,
        "authority_envelope_hash": authority_hash,
        "node_authority_decision": str(node_authority.get("authority_decision") or "invalid"),
        "lease_posture": {
            "mode": "dry_run_grant_lease_preflight",
            "grant_materialized": False,
            "launch_authorized": False,
            "reason": "contract_only_no_runtime_authority",
        },
        "capabilities": {
            "requested": requested,
            "grantable": grantable,
            "denied": denied_capabilities,
        },
        "caveats": {
            "allowed_context_classes": _allowed_context(context_egress),
            "forbidden_context_classes": _as_str_list(context_egress.get("forbidden")),
            "effective_context_bound": _as_str_list(context_egress.get("effective_context")),
            "output_artifact_kind": artifact_contract.get("output_artifact_kind"),
            "schema_or_standard": artifact_contract.get("schema_or_standard"),
            "side_effect_ceiling": dict(_as_mapping(node_authority.get("side_effect_ceiling"))),
            "receipt_required": True,
            "receipt_schema": "reasoning_execution_receipt_v0",
            "single_use": True,
            "expires_at": None,
        },
        "provenance_materials": {
            "authority_envelope_hash": authority_hash,
            "schedule_preflight_hash": schedule.get("schedule_preflight_hash"),
            "candidate_lineage_hash": lineage.get("lineage_hash"),
            "replay_scope_hash": provenance.get("replay_scope_hash"),
            "execution_plan_hash": provenance.get("execution_plan_hash"),
            "packet_manifest_hash": provenance.get("packet_manifest_hash"),
            "authority_envelope_input_hash": provenance.get("authority_envelope_input_hash"),
        },
        "evaluation": _dry_run_evaluation(),
        "dry_run": True,
        "status": status,
        "issues": issues,
    }


def _build_authority_envelope(args: argparse.Namespace, repo_root: Path) -> Mapping[str, Any]:
    if args.authority_envelope:
        return _load_json_object(Path(args.authority_envelope))
    candidate_lineage, replay_scope, schedule_preflight = authority_builder._build_inputs(args, repo_root)
    return authority_builder.build_authority_envelope(
        repo_root,
        candidate_lineage=candidate_lineage,
        replay_scope=replay_scope,
        schedule_preflight=schedule_preflight,
    )


def _resolve_node_id(args: argparse.Namespace, authority_envelope: Mapping[str, Any]) -> str:
    if args.lease_node_id:
        return str(args.lease_node_id)
    single = _single_node_id(authority_envelope)
    if single:
        return single
    if args.target_node_id:
        return str(args.target_node_id[0])
    if args.node_id:
        return str(args.node_id[0])
    raise ValueError("--lease-node-id is required when the authority envelope has multiple or zero nodes.")


def _error_lease(repo_root: Path, exc: Exception) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source_refs": _source_refs(repo_root),
        "grant_id": "grant_invalid_input",
        "node_id": "invalid_input",
        "authority_envelope_hash": "sha256:" + "0" * 64,
        "node_authority_decision": "invalid",
        "lease_posture": {
            "mode": "dry_run_grant_lease_preflight",
            "grant_materialized": False,
            "launch_authorized": False,
            "reason": "contract_only_no_runtime_authority",
        },
        "capabilities": {"requested": [], "grantable": [], "denied": []},
        "caveats": {
            "allowed_context_classes": [],
            "forbidden_context_classes": [],
            "effective_context_bound": [],
            "output_artifact_kind": None,
            "schema_or_standard": None,
            "side_effect_ceiling": {
                "read_only": True,
                "writes_allowed": [],
                "commit_allowed": False,
                "external_action_allowed": False,
            },
            "receipt_required": True,
            "receipt_schema": "reasoning_execution_receipt_v0",
            "single_use": True,
            "expires_at": None,
        },
        "provenance_materials": {
            "authority_envelope_hash": "sha256:" + "0" * 64,
            "schedule_preflight_hash": None,
            "candidate_lineage_hash": None,
            "replay_scope_hash": None,
            "execution_plan_hash": None,
            "packet_manifest_hash": None,
            "authority_envelope_input_hash": None,
        },
        "evaluation": _dry_run_evaluation(),
        "dry_run": True,
        "status": "invalid_grant_lease",
        "issues": [
            _issue(
                code="grant_lease_input_error",
                severity="error",
                path="$",
                message=str(exc),
                witness={"exception_type": type(exc).__name__},
            )
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a dry-run reasoning execution grant lease.")
    parser.add_argument("--node-id", action="append", default=[], help="Node id to include when building lineages. Repeatable.")
    parser.add_argument("--lease-node-id", default=None, help="Node id to lease from the authority envelope.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root.")
    parser.add_argument("--plan-id", default=None, help="Optional stable plan id when building lineages.")
    parser.add_argument("--source-work-item", default=None, help="Optional WorkItem/cap id grounding built lineages.")
    parser.add_argument("--base-lineage", default=None, help="Existing base lineage JSON file.")
    parser.add_argument("--candidate-lineage", default=None, help="Existing candidate lineage JSON file.")
    parser.add_argument("--replay-scope", default=None, help="Existing replay-scope JSON file.")
    parser.add_argument("--schedule-preflight", default=None, help="Existing schedule-preflight JSON file. Requires --candidate-lineage.")
    parser.add_argument("--authority-envelope", default=None, help="Existing authority envelope JSON file.")
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
        authority_envelope = _build_authority_envelope(args, repo_root)
        node_id = _resolve_node_id(args, authority_envelope)
        lease = build_grant_lease(repo_root, authority_envelope=authority_envelope, node_id=node_id)
    except Exception as exc:
        lease = _error_lease(repo_root, exc)
    schema_issues = validate_grant_lease(lease, repo_root)
    if args.check:
        print(
            json.dumps(
                {
                    "ok": not schema_issues and lease.get("status") != "invalid_grant_lease",
                    "schema_version": CHECK_SCHEMA_VERSION,
                    "grant_lease_schema": _display_path(
                        repo_root / GRANT_LEASE_SCHEMA_PATH.relative_to(REPO_ROOT),
                        repo_root,
                    ),
                    "grant_id": lease.get("grant_id"),
                    "node_id": lease.get("node_id"),
                    "status": lease.get("status"),
                    "grant_materialized": _as_mapping(lease.get("lease_posture")).get("grant_materialized"),
                    "launch_authorized": _as_mapping(lease.get("lease_posture")).get("launch_authorized"),
                    "issues": schema_issues,
                },
                indent=2,
                sort_keys=False,
            )
        )
        return 0 if not schema_issues and lease.get("status") != "invalid_grant_lease" else 2
    if schema_issues:
        print(
            json.dumps(
                {
                    "ok": False,
                    "schema_version": CHECK_SCHEMA_VERSION,
                    "status": lease.get("status"),
                    "issues": schema_issues,
                },
                indent=2,
                sort_keys=False,
            )
        )
        return 2
    print(json.dumps(lease, indent=2, sort_keys=False))
    return 1 if lease.get("status") == "invalid_grant_lease" else 0


if __name__ == "__main__":
    raise SystemExit(main())
