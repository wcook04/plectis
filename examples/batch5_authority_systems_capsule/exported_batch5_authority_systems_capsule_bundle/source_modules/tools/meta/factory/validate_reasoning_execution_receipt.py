#!/usr/bin/env python3
"""Validate reasoning execution receipts against authority envelopes.

This is a contract/expectation layer only. It does not execute nodes, materialize
grants, dispatch providers or models, invoke tools, write artifacts, or create
runtime receipts.
"""
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
import build_reasoning_execution_grant_lease as grant_lease_builder  # noqa: E402


SCHEMA_VERSION = "reasoning_execution_receipt_v0"
REPORT_SCHEMA_VERSION = "reasoning_execution_receipt_validation_report_v0"
RECEIPT_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_receipt.json"
)
AUTHORITY_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_authority_envelope.json"
)
GRANT_LEASE_SCHEMA_PATH = (
    REPO_ROOT / "codex" / "substrate" / "contracts" / "schema_reasoning_execution_grant_lease.json"
)
STANDARD_PATH = REPO_ROOT / "codex" / "standards" / "std_node_reasoning.json"
VALIDATOR_PATH = REPO_ROOT / "tools" / "meta" / "factory" / "validate_reasoning_execution_receipt.py"
DISPATCH_SIDE_EFFECTS = ("model_dispatch", "provider_dispatch", "tool_invocation")
WRITE_SIDE_EFFECTS = ("local_write", "commit", "external_action")


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


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _load_json_object(path: Path) -> Mapping[str, Any]:
    value = loads_json_strict(path.read_text(encoding="utf-8"), source=str(path))
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def _load_schema(repo_root: Path) -> Mapping[str, Any]:
    schema_path = repo_root / RECEIPT_SCHEMA_PATH.relative_to(REPO_ROOT)
    value = loads_json_strict(schema_path.read_text(encoding="utf-8"), source=_display_path(schema_path, repo_root))
    if not isinstance(value, Mapping):
        raise ValueError(f"{schema_path} must contain a JSON object.")
    return value


def validate_receipt_schema(receipt: Mapping[str, Any], repo_root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    """Validate a receipt against the durable receipt schema."""
    repo_root = Path(repo_root)
    schema = _load_schema(repo_root)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(receipt),
        key=lambda error: (list(error.path), list(error.schema_path), error.message),
    )
    return [
        _issue(
            code="receipt_schema_validation_error",
            severity="error",
            path=_json_path(error.path),
            message=error.message,
            witness={"schema_path": _json_path(error.schema_path)},
        )
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


def _node_authority(authority_envelope: Mapping[str, Any], node_id: str) -> Mapping[str, Any] | None:
    for node in _as_list(authority_envelope.get("node_authorities")):
        if isinstance(node, Mapping) and node.get("node_id") == node_id:
            return node
    return None


def _authority_hashes(
    *,
    authority_envelope: Mapping[str, Any],
    node_authority: Mapping[str, Any],
    grant_lease: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    provenance = _as_mapping(node_authority.get("provenance_materials"))
    schedule = _as_mapping(authority_envelope.get("schedule_preflight"))
    lineage = _as_mapping(authority_envelope.get("candidate_lineage"))
    return {
        "authority_envelope_hash": _stable_hash(authority_envelope),
        "grant_lease_hash": _stable_hash(grant_lease) if grant_lease else None,
        "schedule_preflight_hash": schedule.get("schedule_preflight_hash"),
        "candidate_lineage_hash": lineage.get("lineage_hash"),
        "replay_scope_hash": provenance.get("replay_scope_hash"),
        "execution_plan_hash": provenance.get("execution_plan_hash"),
        "packet_manifest_hash": provenance.get("packet_manifest_hash"),
    }


def _observed_side_effects(receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    return _as_mapping(_as_mapping(receipt.get("side_effects")).get("observed"))


def _any_observed(receipt: Mapping[str, Any], keys: Sequence[str]) -> list[str]:
    observed = _observed_side_effects(receipt)
    return [key for key in keys if observed.get(key) is True]


def _semantic_issues(
    receipt: Mapping[str, Any],
    authority_envelope: Mapping[str, Any],
    grant_lease: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    node_id = receipt.get("node_id")
    if not isinstance(node_id, str) or not node_id:
        return issues
    node_authority = _node_authority(authority_envelope, node_id)
    if node_authority is None:
        return [
            _issue(
                code="node_authority_not_found",
                severity="error",
                path="$.node_id",
                message="Receipt node_id is absent from the authority envelope.",
                witness={"node_id": node_id},
            )
        ]

    receipt_authority = _as_mapping(receipt.get("authority"))
    expected_hashes = _authority_hashes(
        authority_envelope=authority_envelope,
        node_authority=node_authority,
        grant_lease=grant_lease,
    )
    for field, expected in expected_hashes.items():
        actual = receipt_authority.get(field)
        if actual != expected:
            issues.append(
                _issue(
                    code="authority_hash_mismatch",
                    severity="error",
                    path=f"$.authority.{field}",
                    message="Receipt authority hash does not match the authority envelope.",
                    witness={"expected": expected, "actual": actual},
                )
            )

    expected_decision = node_authority.get("authority_decision")
    if receipt_authority.get("authority_decision") != expected_decision:
        issues.append(
            _issue(
                code="authority_decision_mismatch",
                severity="error",
                path="$.authority.authority_decision",
                message="Receipt authority decision does not match node authority decision.",
                witness={"expected": expected_decision, "actual": receipt_authority.get("authority_decision")},
            )
        )

    posture = _as_mapping(authority_envelope.get("authority_posture"))
    for field in ("launch_authorized", "grant_materialized"):
        expected = posture.get(field)
        actual = receipt_authority.get(field)
        if actual != expected:
            issues.append(
                _issue(
                    code="runtime_authority_posture_mismatch",
                    severity="error",
                    path=f"$.authority.{field}",
                    message="Receipt claims runtime authority posture not present in authority envelope.",
                    witness={"expected": expected, "actual": actual},
                )
            )

    grant_lease_hash = receipt_authority.get("grant_lease_hash")
    execution_claimed = (
        receipt.get("receipt_kind") == "node_execution"
        or _as_mapping(receipt.get("evaluation")).get("runtime_execution_recorded") is True
        or receipt_authority.get("launch_authorized") is True
        or receipt_authority.get("grant_materialized") is True
    )
    if grant_lease is None:
        if grant_lease_hash is not None:
            issues.append(
                _issue(
                    code="grant_lease_hash_without_lease",
                    severity="error",
                    path="$.authority.grant_lease_hash",
                    message="Receipt names a grant lease hash but no grant lease was supplied for validation.",
                    witness={"grant_lease_hash": grant_lease_hash},
                )
            )
        if execution_claimed:
            issues.append(
                _issue(
                    code="execution_claim_requires_grant_lease",
                    severity="error",
                    path="$.authority.grant_lease_hash",
                    message="Execution claims require a matching reasoning_execution_grant_lease_v0.",
                    witness={"receipt_kind": receipt.get("receipt_kind")},
                )
            )
    else:
        lease_posture = _as_mapping(grant_lease.get("lease_posture"))
        lease_caveats = _as_mapping(grant_lease.get("caveats"))
        lease_materials = _as_mapping(grant_lease.get("provenance_materials"))
        if grant_lease.get("authority_envelope_hash") != _stable_hash(authority_envelope):
            issues.append(
                _issue(
                    code="grant_lease_authority_envelope_mismatch",
                    severity="error",
                    path="$.authority.grant_lease_hash",
                    message="Grant lease is not bound to the supplied authority envelope.",
                    witness={
                        "expected": _stable_hash(authority_envelope),
                        "actual": grant_lease.get("authority_envelope_hash"),
                    },
                )
            )
        if grant_lease.get("node_id") != node_id:
            issues.append(
                _issue(
                    code="grant_lease_node_mismatch",
                    severity="error",
                    path="$.node_id",
                    message="Grant lease node_id does not match receipt node_id.",
                    witness={"expected": node_id, "actual": grant_lease.get("node_id")},
                )
            )
        if grant_lease.get("node_authority_decision") != expected_decision:
            issues.append(
                _issue(
                    code="grant_lease_decision_mismatch",
                    severity="error",
                    path="$.authority.authority_decision",
                    message="Grant lease node authority decision does not match the authority envelope.",
                    witness={"expected": expected_decision, "actual": grant_lease.get("node_authority_decision")},
                )
            )
        for field in ("schedule_preflight_hash", "candidate_lineage_hash", "replay_scope_hash", "execution_plan_hash", "packet_manifest_hash"):
            receipt_value = receipt_authority.get(field)
            lease_value = lease_materials.get(field)
            if receipt_value != lease_value:
                issues.append(
                    _issue(
                        code="grant_lease_provenance_mismatch",
                        severity="error",
                        path=f"$.authority.{field}",
                        message="Receipt provenance hash does not match the grant lease caveat materials.",
                        witness={"expected": lease_value, "actual": receipt_value},
                    )
                )
        if receipt_authority.get("launch_authorized") is True or receipt_authority.get("grant_materialized") is True:
            if lease_posture.get("launch_authorized") is not True or lease_posture.get("grant_materialized") is not True:
                issues.append(
                    _issue(
                        code="runtime_authority_not_materialized_by_lease",
                        severity="error",
                        path="$.authority.grant_materialized",
                        message="Receipt claims materialized runtime authority, but the supplied grant lease is unissued.",
                        witness={
                            "lease_launch_authorized": lease_posture.get("launch_authorized"),
                            "lease_grant_materialized": lease_posture.get("grant_materialized"),
                        },
                    )
                )
        if execution_claimed and grant_lease.get("status") != "eligible_unissued":
            issues.append(
                _issue(
                    code="execution_claim_requires_eligible_grant_lease",
                    severity="error",
                    path="$.authority.grant_lease_hash",
                    message="Execution claims require an eligible grant lease before any runtime grant can be materialized.",
                    witness={"grant_lease_status": grant_lease.get("status")},
                )
            )
        lease_allowed = set(_as_str_list(lease_caveats.get("allowed_context_classes")))
        lease_forbidden = set(_as_str_list(lease_caveats.get("forbidden_context_classes")))
        sent = set(_as_str_list(_as_mapping(receipt.get("context")).get("context_classes_sent")))
        forbidden_by_lease = sorted(sent & lease_forbidden)
        if forbidden_by_lease:
            issues.append(
                _issue(
                    code="forbidden_context_sent_by_grant_lease",
                    severity="error",
                    path="$.context.context_classes_sent",
                    message="Receipt sent context forbidden by the supplied grant lease caveats.",
                    witness={"forbidden_context_sent": forbidden_by_lease},
                )
            )
        not_allowed_by_lease = sorted(sent - lease_allowed)
        if not_allowed_by_lease:
            issues.append(
                _issue(
                    code="context_not_allowed_by_grant_lease",
                    severity="error",
                    path="$.context.context_classes_sent",
                    message="Receipt sent context outside grant lease allowed context classes.",
                    witness={"not_allowed": not_allowed_by_lease, "allowed": sorted(lease_allowed)},
                )
            )

    context = _as_mapping(receipt.get("context"))
    sent = set(_as_str_list(context.get("context_classes_sent")))
    node_context = _as_mapping(node_authority.get("context_egress"))
    allowed = set(_as_str_list(node_context.get("inject"))) | set(_as_str_list(node_context.get("reference_only")))
    forbidden = set(_as_str_list(node_context.get("forbidden")))
    sent_forbidden = sorted(sent & forbidden)
    if sent_forbidden:
        issues.append(
            _issue(
                code="forbidden_context_sent",
                severity="error",
                path="$.context.context_classes_sent",
                message="Receipt says forbidden node-scoped context left the substrate.",
                witness={"forbidden_context_sent": sent_forbidden},
            )
        )
    sent_not_allowed = sorted(sent - allowed)
    if sent_not_allowed:
        issues.append(
            _issue(
                code="context_not_allowed_by_authority",
                severity="error",
                path="$.context.context_classes_sent",
                message="Receipt sent context not allowed by node-scoped authority egress policy.",
                witness={"not_allowed": sent_not_allowed, "allowed": sorted(allowed)},
            )
        )

    side_effect_ceiling = _as_mapping(node_authority.get("side_effect_ceiling"))
    if grant_lease is not None:
        side_effect_ceiling = _as_mapping(_as_mapping(grant_lease.get("caveats")).get("side_effect_ceiling"))
    write_effects = _any_observed(receipt, WRITE_SIDE_EFFECTS)
    if side_effect_ceiling.get("read_only") is True and write_effects:
        issues.append(
            _issue(
                code="side_effect_exceeds_ceiling",
                severity="error",
                path="$.side_effects.observed",
                message="Receipt reports write/external side effects above read-only authority ceiling.",
                witness={"observed": write_effects},
            )
        )
    if _as_mapping(receipt.get("evaluation")).get("writes_recorded") is True and not write_effects:
        issues.append(
            _issue(
                code="writes_recorded_without_observed_write",
                severity="error",
                path="$.evaluation.writes_recorded",
                message="Receipt evaluation says writes were recorded but no write side effect is observed.",
                witness={},
            )
        )

    dispatch_effects = _any_observed(receipt, DISPATCH_SIDE_EFFECTS)
    if posture.get("launch_authorized") is not True or posture.get("grant_materialized") is not True:
        if dispatch_effects or _as_mapping(receipt.get("evaluation")).get("runtime_execution_recorded") is True:
            issues.append(
                _issue(
                    code="execution_claimed_without_runtime_grant",
                    severity="error",
                    path="$.side_effects.observed",
                    message="Receipt claims execution or dispatch even though no launch authorization or grant was materialized.",
                    witness={
                        "dispatch_effects": dispatch_effects,
                        "runtime_execution_recorded": _as_mapping(receipt.get("evaluation")).get(
                            "runtime_execution_recorded"
                        ),
                    },
                )
            )

    if expected_decision in {"denied", "no_grant_needed"}:
        if dispatch_effects or write_effects:
            issues.append(
                _issue(
                    code="non_executable_authority_claimed_side_effects",
                    severity="error",
                    path="$.side_effects.observed",
                    message="Denied or no-grant node authority cannot claim dispatch or write side effects.",
                    witness={"dispatch_effects": dispatch_effects, "write_effects": write_effects},
                )
            )

    artifact_contract = _as_mapping(node_authority.get("artifact_contract"))
    if grant_lease is not None:
        lease_caveats = _as_mapping(grant_lease.get("caveats"))
        artifact_contract = {
            "output_artifact_kind": lease_caveats.get("output_artifact_kind"),
            "schema_or_standard": lease_caveats.get("schema_or_standard"),
        }
    products = _as_mapping(receipt.get("products"))
    output_kind = products.get("output_artifact_kind")
    schema_or_standard = products.get("schema_or_standard")
    produced = bool(products.get("output_artifact_ref") or products.get("output_artifact_hash"))
    if produced:
        if output_kind != artifact_contract.get("output_artifact_kind"):
            issues.append(
                _issue(
                    code="output_artifact_kind_mismatch",
                    severity="error",
                    path="$.products.output_artifact_kind",
                    message="Receipt output artifact kind does not match authority artifact contract.",
                    witness={"expected": artifact_contract.get("output_artifact_kind"), "actual": output_kind},
                )
            )
        if schema_or_standard != artifact_contract.get("schema_or_standard"):
            issues.append(
                _issue(
                    code="output_schema_mismatch",
                    severity="error",
                    path="$.products.schema_or_standard",
                    message="Receipt output schema or standard does not match authority artifact contract.",
                    witness={"expected": artifact_contract.get("schema_or_standard"), "actual": schema_or_standard},
                )
            )
        schema_result = _as_mapping(products.get("schema_validation_result"))
        if schema_result.get("status") == "not_applicable":
            issues.append(
                _issue(
                    code="produced_artifact_requires_schema_validation",
                    severity="error",
                    path="$.products.schema_validation_result.status",
                    message="Produced artifacts require a pass/fail schema validation result.",
                    witness={},
                )
            )
    elif output_kind is not None and output_kind != artifact_contract.get("output_artifact_kind"):
        issues.append(
            _issue(
                code="output_artifact_kind_mismatch",
                severity="error",
                path="$.products.output_artifact_kind",
                message="Receipt output artifact kind does not match authority artifact contract.",
                witness={"expected": artifact_contract.get("output_artifact_kind"), "actual": output_kind},
            )
        )

    if receipt.get("receipt_kind") == "node_execution" and _as_mapping(receipt.get("evaluation")).get(
        "runtime_execution_recorded"
    ) is not True:
        issues.append(
            _issue(
                code="node_execution_without_runtime_record",
                severity="error",
                path="$.evaluation.runtime_execution_recorded",
                message="node_execution receipts must record runtime execution.",
                witness={},
            )
        )
    if receipt.get("receipt_kind") in {"no_op", "denied"} and produced:
        issues.append(
            _issue(
                code="non_execution_receipt_produced_artifact",
                severity="error",
                path="$.products",
                message="no_op and denied receipts cannot claim produced artifacts.",
                witness={},
            )
        )

    return issues


def validate_receipt_against_authority(
    receipt: Mapping[str, Any],
    authority_envelope: Mapping[str, Any],
    repo_root: Path = REPO_ROOT,
    grant_lease: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Validate receipt schema and semantic consistency with an authority envelope."""
    repo_root = Path(repo_root)
    issues = validate_receipt_schema(receipt, repo_root)
    for row in authority_builder.validate_authority_envelope(authority_envelope, repo_root):
        issues.append(
            _issue(
                code="authority_envelope_schema_validation_error",
                severity="error",
                path=f"$.authority_envelope{str(row.get('path') or '$')[1:]}",
                message=str(row.get("message") or "Authority envelope failed schema validation."),
                witness={"schema_issue": dict(row)},
            )
        )
    if grant_lease is not None:
        for row in grant_lease_builder.validate_grant_lease(grant_lease, repo_root):
            issues.append(
                _issue(
                    code="grant_lease_schema_validation_error",
                    severity="error",
                    path=f"$.grant_lease{str(row.get('path') or '$')[1:]}",
                    message=str(row.get("message") or "Grant lease failed schema validation."),
                    witness={"schema_issue": dict(row)},
                )
            )
    if not any(issue["code"] == "receipt_schema_validation_error" for issue in issues):
        issues.extend(_semantic_issues(receipt, authority_envelope, grant_lease))
    return issues


def build_validation_report(
    *,
    receipt: Mapping[str, Any],
    authority_envelope: Mapping[str, Any],
    repo_root: Path = REPO_ROOT,
    grant_lease: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    issues = validate_receipt_against_authority(receipt, authority_envelope, repo_root, grant_lease)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "ok": not issues,
        "receipt_id": receipt.get("receipt_id"),
        "node_id": receipt.get("node_id"),
        "receipt_status": receipt.get("status"),
        "authority_envelope_hash": _stable_hash(authority_envelope) if authority_envelope else None,
        "grant_lease_hash": _stable_hash(grant_lease) if grant_lease else None,
        "receipt_schema": _display_path(repo_root / RECEIPT_SCHEMA_PATH.relative_to(REPO_ROOT), repo_root),
        "authority_schema": _display_path(repo_root / AUTHORITY_SCHEMA_PATH.relative_to(REPO_ROOT), repo_root),
        "grant_lease_schema": _display_path(repo_root / GRANT_LEASE_SCHEMA_PATH.relative_to(REPO_ROOT), repo_root),
        "validator": _display_path(repo_root / VALIDATOR_PATH.relative_to(REPO_ROOT), repo_root),
        "issues": issues,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a reasoning execution receipt against an authority envelope.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root.")
    parser.add_argument("--authority-envelope", required=True, help="Authority envelope JSON file.")
    parser.add_argument("--grant-lease", default=None, help="Optional grant lease JSON file.")
    parser.add_argument("--receipt", required=True, help="Receipt JSON file.")
    parser.add_argument("--json", action="store_true", help="Emit JSON. Currently always true.")
    parser.add_argument("--check", action="store_true", help="Emit validation report and fail nonzero on issues.")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    try:
        authority_envelope = _load_json_object(Path(args.authority_envelope))
        grant_lease = _load_json_object(Path(args.grant_lease)) if args.grant_lease else None
        receipt = _load_json_object(Path(args.receipt))
        report = build_validation_report(
            receipt=receipt,
            authority_envelope=authority_envelope,
            repo_root=repo_root,
            grant_lease=grant_lease,
        )
    except Exception as exc:
        report = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "ok": False,
            "receipt_id": None,
            "node_id": None,
            "receipt_status": None,
            "authority_envelope_hash": None,
            "receipt_schema": _display_path(repo_root / RECEIPT_SCHEMA_PATH.relative_to(REPO_ROOT), repo_root),
            "authority_schema": _display_path(repo_root / AUTHORITY_SCHEMA_PATH.relative_to(REPO_ROOT), repo_root),
            "validator": _display_path(repo_root / VALIDATOR_PATH.relative_to(REPO_ROOT), repo_root),
            "issues": [
                _issue(
                    code="receipt_validation_input_error",
                    severity="error",
                    path="$",
                    message=str(exc),
                    witness={"exception_type": type(exc).__name__},
                )
            ],
        }
    print(json.dumps(report, indent=2, sort_keys=False))
    return 0 if report.get("ok") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
