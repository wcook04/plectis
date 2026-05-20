from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import base_receipt, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "agent_route_observability_runtime"
FIXTURE_ID = "first_wave.agent_route_observability_runtime"
VALIDATOR_ID = "validator.microcosm.organs.agent_route_observability_runtime"

ROUTE_COMPLIANCE_NAME = "route_compliance_audit.json"
HOOK_SHADOW_NAME = "hook_shadow_coverage.json"
DEBT_RETIREMENT_NAME = "debt_retirement_receipt.json"
ROUTE_LEASE_NAME = "route_lease_mode_control_receipt.json"
OBSERVABILITY_BUNDLE_RESULT_NAME = "exported_observability_bundle_validation_result.json"

EXPECTED_RECEIPT_PATHS = [
    "receipts/first_wave/agent_route_observability_runtime/route_compliance_audit.json",
    "receipts/first_wave/agent_route_observability_runtime/hook_shadow_coverage.json",
    "receipts/first_wave/agent_route_observability_runtime/debt_retirement_receipt.json",
    "receipts/first_wave/agent_route_observability_runtime/route_lease_mode_control_receipt.json",
]
EXPORTED_OBSERVABILITY_BUNDLE_RECEIPT_PATH = (
    "receipts/first_wave/agent_route_observability_runtime/"
    "exported_observability_bundle_validation_result.json"
)

EXPECTED_NEGATIVE_CASES = {
    "wrong_actor_axis_and_evidence_only_telemetry": [
        "ACTOR_AXIS_AUTHORITY_MISMATCH",
        "NO_BEHAVIOR_CHANGE_EVIDENCE",
    ],
    "agent_trace_missing_route_lease": ["MISSING_ROUTE_LEASE"],
    "telemetry_private_transcript_body": ["TELEMETRY_PRIVATE_TRANSCRIPT_BODY"],
    "duplicate_trace_event_conflict": ["DUPLICATE_TRACE_EVENT_ID"],
    "route_compliance_overclaims_behavior_change": [
        "ROUTE_COMPLIANCE_PASS_OVERCLAIMS_BEHAVIOR_CHANGE"
    ],
    "route_lease_broad_kernel_bloat_before_direct_action": [
        "KERNEL_BLOAT_BEFORE_DIRECT_ACTION"
    ],
    "route_lease_static_metadata_without_trace_feedback": ["ROUTE_LEASE_NOT_CONSUMED"],
}

OBSERVABILITY_AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "agent_observability_metadata_not_live_trace_authority",
    "live_operator_state_read": False,
    "provider_payload_read": False,
    "behavior_change_claim_authorized_without_trace": False,
    "later_organs_authorized": False,
}
OBSERVABILITY_ANTI_CLAIM = (
    "Agent observability receipts validate public trace-feedback metadata plus regression "
    "fixtures; they do not inspect live operator state, certify runtime behavior, mutate "
    "Task Ledger, authorize pattern assimilation, or prove whole Wave 1."
)

SOURCE_PATTERN_IDS = [
    "agent_route_observability_runtime",
    "route_lease_mode_control",
    "actor_axis_authority_boundary",
    "anti_pattern_debt_retirement",
    "trace_feedback_behavior_change_gate",
]

VALIDATOR_ASSERTED_FEEDS_PATTERNS = [
    {
        "assertion_id": "route_lease_feedback_requires_consumed_trace",
        "source_pattern_id": "route_lease_mode_control",
        "status": PASS,
    },
    {
        "assertion_id": "actor_axis_mismatch_rejects_mutation_authority",
        "source_pattern_id": "actor_axis_authority_boundary",
        "status": PASS,
    },
    {
        "assertion_id": "debt_retirement_requires_behavior_change_evidence",
        "source_pattern_id": "anti_pattern_debt_retirement",
        "status": PASS,
    },
]


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _input_paths(input_dir: Path) -> list[Path]:
    return [
        input_dir / "agent_trace.jsonl",
        input_dir / "hook_shadow_cases.json",
        input_dir / "anti_pattern_debt.json",
    ]


def _observability_bundle_paths(input_dir: Path) -> list[Path]:
    names = (
        "bundle_manifest.json",
        "route_events.json",
        "agent_path_observations.json",
        "session_diagnostics.json",
        "hook_shadow_coverage.json",
        "actor_axis_checks.json",
        "anti_pattern_debt.json",
        "process_audit_rows.json",
        "observability_policy.json",
    )
    return [input_dir / name for name in names]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _load_inputs(input_dir: Path) -> dict[str, Any]:
    return {
        "trace_rows": _load_jsonl(input_dir / "agent_trace.jsonl"),
        "hook_shadow": read_json_strict(input_dir / "hook_shadow_cases.json"),
        "debt": read_json_strict(input_dir / "anti_pattern_debt.json"),
    }


def _load_observability_bundle(input_dir: Path) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _observability_bundle_paths(input_dir)
    }


def _scan_fixture_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    return scan_paths(_input_paths(input_dir), forbidden_classes=policy, display_root=public_root)


def _scan_bundle_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    return scan_paths(
        _observability_bundle_paths(input_dir),
        forbidden_classes=policy,
        display_root=public_root,
    )


def _stable_hash(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_redacted": True,
    }


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> None:
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    observed[case_id].add(code)


def _bundle_finding(
    code: str,
    message: str,
    *,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_redacted": True,
    }


def validate_exported_route_events(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "route_events")
    event_ids: list[str] = []
    behavior_refs: list[str] = []
    decisions: list[dict[str, Any]] = []

    if not rows:
        findings.append(
            _bundle_finding(
                "OBSERVABILITY_BUNDLE_ROUTE_EVENTS_MISSING",
                "Exported observability bundle has no route event rows.",
                subject_id="route_events",
                subject_kind="route_events",
            )
        )

    for row in rows:
        event_id = str(row.get("event_id") or "")
        event_ids.append(event_id)
        refs = [str(ref) for ref in row.get("behavior_change_evidence_trace_ids", [])]
        behavior_refs.extend(refs)
        row_codes: list[str] = []
        if row.get("projection_not_authority") is not True:
            row_codes.append("OBSERVABILITY_BUNDLE_ROUTE_EVENT_PROJECTION_FLAG_MISSING")
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_ROUTE_EVENT_PROJECTION_FLAG_MISSING",
                    "Route event row must declare projection_not_authority.",
                    subject_id=event_id or "route_event",
                    subject_kind="route_event",
                )
            )
        for field in (
            "live_telemetry_authority",
            "source_authority_allowed",
            "raw_payload_available",
            "provider_payload_read",
            "browser_hud_cockpit_state_read",
        ):
            if row.get(field) is not False:
                row_codes.append("OBSERVABILITY_BUNDLE_ROUTE_EVENT_AUTHORITY_OVERCLAIM")
                findings.append(
                    _bundle_finding(
                        "OBSERVABILITY_BUNDLE_ROUTE_EVENT_AUTHORITY_OVERCLAIM",
                        "Route event metadata cannot claim live telemetry, source authority, provider, or browser/HUD/cockpit access.",
                        subject_id=event_id or field,
                        subject_kind="route_event",
                    )
                )
        if row.get("claims_behavior_change") and not refs:
            row_codes.append("OBSERVABILITY_BUNDLE_BEHAVIOR_CHANGE_OVERCLAIM")
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_BEHAVIOR_CHANGE_OVERCLAIM",
                    "Route event cannot claim behavior change without evidence trace ids.",
                    subject_id=event_id or "route_event",
                    subject_kind="route_event",
                )
            )
        decisions.append(
            {
                "event_id": event_id,
                "route_id": row.get("route_id"),
                "route_lease_id": row.get("route_lease_id"),
                "decision": "accepted" if not row_codes else "blocked",
                "error_codes": sorted(set(row_codes)),
                "body_redacted": True,
            }
        )

    duplicates = sorted(
        event_id for event_id in set(event_ids) if event_id and event_ids.count(event_id) > 1
    )
    for event_id in duplicates:
        findings.append(
            _bundle_finding(
                "OBSERVABILITY_BUNDLE_DUPLICATE_ROUTE_EVENT_ID",
                "Exported observability bundle contains a duplicate route event id.",
                subject_id=event_id,
                subject_kind="route_events",
            )
        )

    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "route_event_ids": sorted(event_id for event_id in event_ids if event_id),
        "route_event_count": len([event_id for event_id in event_ids if event_id]),
        "behavior_change_evidence_trace_ids": sorted(set(behavior_refs)),
        "route_compliance_decisions": decisions,
        "route_events_projection_not_authority": True,
    }


def validate_exported_agent_path_observations(
    payload: object,
    route_event_result: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "agent_path_observations")
    route_event_ids = set(route_event_result["route_event_ids"])
    consumed_route_lease_ids: list[str] = []
    decisions: list[dict[str, Any]] = []

    if not rows:
        findings.append(
            _bundle_finding(
                "OBSERVABILITY_BUNDLE_AGENT_PATH_ROWS_MISSING",
                "Exported observability bundle has no agent path observation rows.",
                subject_id="agent_path_observations",
                subject_kind="agent_path_observations",
            )
        )

    for row in rows:
        observation_id = str(row.get("observation_id") or "")
        event_id = str(row.get("event_id") or "")
        lease_id = str(row.get("route_lease_id") or "")
        row_codes: list[str] = []
        if event_id not in route_event_ids:
            row_codes.append("OBSERVABILITY_BUNDLE_AGENT_PATH_EVENT_REF_MISSING")
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_AGENT_PATH_EVENT_REF_MISSING",
                    "Agent path observation references an unknown route event.",
                    subject_id=observation_id or event_id or "agent_path_observation",
                    subject_kind="agent_path_observation",
                )
            )
        if row.get("projection_not_authority") is not True:
            row_codes.append("OBSERVABILITY_BUNDLE_AGENT_PATH_PROJECTION_FLAG_MISSING")
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_AGENT_PATH_PROJECTION_FLAG_MISSING",
                    "Agent path observation must declare projection_not_authority.",
                    subject_id=observation_id or "agent_path_observation",
                    subject_kind="agent_path_observation",
                )
            )
        for field in (
            "live_operator_state_read",
            "provider_payload_read",
            "browser_hud_cockpit_state_read",
            "source_authority_allowed",
        ):
            if row.get(field) is not False:
                row_codes.append("OBSERVABILITY_BUNDLE_AGENT_PATH_FORBIDDEN_LIVE_ACCESS")
                findings.append(
                    _bundle_finding(
                        "OBSERVABILITY_BUNDLE_AGENT_PATH_FORBIDDEN_LIVE_ACCESS",
                        "Agent path observation cannot read live operator, provider, browser/HUD/cockpit, or source-authority state.",
                        subject_id=observation_id or field,
                        subject_kind="agent_path_observation",
                    )
                )
        if row.get("route_lease_consumed") is not True:
            row_codes.append("OBSERVABILITY_BUNDLE_ROUTE_LEASE_NOT_CONSUMED")
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_ROUTE_LEASE_NOT_CONSUMED",
                    "Agent path observation must record consumed route-lease metadata.",
                    subject_id=observation_id or lease_id or "agent_path_observation",
                    subject_kind="agent_path_observation",
                )
            )
        if lease_id:
            consumed_route_lease_ids.append(lease_id)
        decisions.append(
            {
                "observation_id": observation_id,
                "event_id": event_id,
                "route_lease_id": lease_id,
                "decision": "accepted" if not row_codes else "blocked",
                "error_codes": sorted(set(row_codes)),
                "body_redacted": True,
            }
        )

    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "agent_path_observation_count": len(rows),
        "consumed_route_lease_ids": sorted(set(consumed_route_lease_ids)),
        "agent_path_decisions": decisions,
        "agent_path_observations_projection_not_authority": True,
    }


def validate_exported_session_diagnostics(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "session_diagnostics")
    decisions: list[dict[str, Any]] = []
    if not rows:
        findings.append(
            _bundle_finding(
                "OBSERVABILITY_BUNDLE_SESSION_ROWS_MISSING",
                "Exported observability bundle has no session diagnostic rows.",
                subject_id="session_diagnostics",
                subject_kind="session_diagnostics",
            )
        )
    for row in rows:
        session_id = str(row.get("session_id") or "")
        row_codes: list[str] = []
        if row.get("projection_not_authority") is not True:
            row_codes.append("OBSERVABILITY_BUNDLE_SESSION_PROJECTION_FLAG_MISSING")
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_SESSION_PROJECTION_FLAG_MISSING",
                    "Session diagnostic row must declare projection_not_authority.",
                    subject_id=session_id or "session_diagnostic",
                    subject_kind="session_diagnostic",
                )
            )
        for field in (
            "raw_operator_state_available",
            "live_telemetry_authority",
            "behavior_change_claim_authorized_without_trace",
        ):
            if row.get(field) is not False:
                row_codes.append("OBSERVABILITY_BUNDLE_SESSION_AUTHORITY_OVERCLAIM")
                findings.append(
                    _bundle_finding(
                        "OBSERVABILITY_BUNDLE_SESSION_AUTHORITY_OVERCLAIM",
                        "Session diagnostic row cannot claim raw operator state, live telemetry authority, or behavior-change authority without trace.",
                        subject_id=session_id or field,
                        subject_kind="session_diagnostic",
                    )
                )
        decisions.append(
            {
                "session_id": session_id,
                "diagnostic_status": row.get("diagnostic_status"),
                "decision": "accepted" if not row_codes else "blocked",
                "error_codes": sorted(set(row_codes)),
                "body_redacted": True,
            }
        )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "session_diagnostic_count": len(rows),
        "session_diagnostic_decisions": decisions,
        "session_diagnostics_projection_not_authority": True,
    }


def validate_exported_hook_shadow_coverage(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "hook_shadow_rows")
    covered_hook_ids: list[str] = []
    if not rows:
        findings.append(
            _bundle_finding(
                "OBSERVABILITY_BUNDLE_HOOK_SHADOW_ROWS_MISSING",
                "Exported observability bundle has no hook shadow rows.",
                subject_id="hook_shadow_coverage",
                subject_kind="hook_shadow_coverage",
            )
        )
    for row in rows:
        hook_id = str(row.get("hook_id") or "")
        covered_hook_ids.append(hook_id)
        if row.get("projection_not_authority") is not True or row.get("browser_hud_state_read") is not False:
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_HOOK_SHADOW_AUTHORITY_OVERCLAIM",
                    "Hook shadow row must remain metadata and reject browser/HUD state access.",
                    subject_id=hook_id or "hook_shadow",
                    subject_kind="hook_shadow",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "hook_shadow_coverage_status": "public_metadata_coverage_only",
        "covered_hook_ids": sorted(hook_id for hook_id in covered_hook_ids if hook_id),
        "hook_shadow_projection_not_authority": True,
    }


def validate_exported_actor_axis_checks(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "actor_axis_checks")
    decisions: list[dict[str, Any]] = []
    authority_rejection_count = 0
    if not rows:
        findings.append(
            _bundle_finding(
                "OBSERVABILITY_BUNDLE_ACTOR_AXIS_ROWS_MISSING",
                "Exported observability bundle has no actor-axis check rows.",
                subject_id="actor_axis_checks",
                subject_kind="actor_axis_checks",
            )
        )
    for row in rows:
        check_id = str(row.get("check_id") or "")
        actor_axis = str(row.get("actor_axis") or "unknown")
        rejected = bool(row.get("claims_mutation_authority")) and actor_axis == "type_b_advisory"
        if rejected:
            authority_rejection_count += 1
        if row.get("projection_not_authority") is not True:
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_ACTOR_AXIS_PROJECTION_FLAG_MISSING",
                    "Actor-axis check row must declare projection_not_authority.",
                    subject_id=check_id or actor_axis,
                    subject_kind="actor_axis_check",
                )
            )
        if row.get("live_mutation_authorized") is not False:
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_ACTOR_AXIS_LIVE_MUTATION_OVERCLAIM",
                    "Actor-axis check cannot authorize live mutation.",
                    subject_id=check_id or actor_axis,
                    subject_kind="actor_axis_check",
                )
            )
        decisions.append(
            {
                "check_id": check_id,
                "actor_axis": actor_axis,
                "mutation_authority_claim_rejected": rejected,
                "body_redacted": True,
            }
        )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "actor_axis_check_count": len(rows),
        "actor_axis_decisions": decisions,
        "authority_rejection_count": authority_rejection_count,
        "actor_axis_projection_not_authority": True,
    }


def validate_exported_anti_pattern_debt(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "debt_rows")
    decisions: list[dict[str, Any]] = []
    behavior_refs: list[str] = []
    evidence_only_refs: list[str] = []
    retired_count = 0
    if not rows:
        findings.append(
            _bundle_finding(
                "OBSERVABILITY_BUNDLE_DEBT_ROWS_MISSING",
                "Exported observability bundle has no anti-pattern debt rows.",
                subject_id="anti_pattern_debt",
                subject_kind="anti_pattern_debt",
            )
        )
    for row in rows:
        debt_id = str(row.get("debt_id") or "")
        row_behavior_refs = [str(ref) for ref in row.get("behavior_change_evidence_trace_ids", [])]
        row_evidence_refs = [str(ref) for ref in row.get("evidence_only_trace_ids", [])]
        behavior_refs.extend(row_behavior_refs)
        evidence_only_refs.extend(row_evidence_refs)
        if row.get("projection_not_authority") is not True or row.get("live_debt_authority") is not False:
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_DEBT_AUTHORITY_OVERCLAIM",
                    "Anti-pattern debt row must remain metadata and reject live debt authority.",
                    subject_id=debt_id or "anti_pattern_debt",
                    subject_kind="anti_pattern_debt",
                )
            )
        retired = bool(row_behavior_refs) and not bool(row_evidence_refs)
        if retired:
            retired_count += 1
        decisions.append(
            {
                "debt_id": debt_id,
                "decision": "retired_metadata_projection" if retired else "retained_metadata_projection",
                "behavior_change_evidence_trace_ids": row_behavior_refs,
                "evidence_only_trace_ids": row_evidence_refs,
                "body_redacted": True,
            }
        )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "debt_retirement_count": retired_count,
        "anti_pattern_debt_decisions": decisions,
        "behavior_change_evidence_trace_ids": sorted(set(behavior_refs)),
        "evidence_only_trace_ids": sorted(set(evidence_only_refs)),
        "debt_rows_projection_not_authority": True,
    }


def validate_exported_process_audit_rows(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "process_audit_rows")
    anti_pattern_ids: list[str] = []
    if not rows:
        findings.append(
            _bundle_finding(
                "OBSERVABILITY_BUNDLE_PROCESS_AUDIT_ROWS_MISSING",
                "Exported observability bundle has no process-audit rows.",
                subject_id="process_audit_rows",
                subject_kind="process_audit_rows",
            )
        )
    for row in rows:
        anti_pattern_id = str(row.get("anti_pattern_id") or "")
        anti_pattern_ids.append(anti_pattern_id)
        for field in (
            "projection_not_authority",
        ):
            if row.get(field) is not True:
                findings.append(
                    _bundle_finding(
                        "OBSERVABILITY_BUNDLE_PROCESS_AUDIT_PROJECTION_FLAG_MISSING",
                        "Process-audit row must declare projection_not_authority.",
                        subject_id=anti_pattern_id or "process_audit_row",
                        subject_kind="process_audit_row",
                    )
                )
        for field in (
            "live_process_audit_authority",
            "source_authority_allowed",
            "raw_event_body_available",
        ):
            if row.get(field) is not False:
                findings.append(
                    _bundle_finding(
                        "OBSERVABILITY_BUNDLE_PROCESS_AUDIT_AUTHORITY_OVERCLAIM",
                        "Process-audit row cannot claim live authority, source authority, or raw event bodies.",
                        subject_id=anti_pattern_id or field,
                        subject_kind="process_audit_row",
                    )
                )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "process_audit_row_count": len(rows),
        "process_audit_anti_pattern_ids": sorted(anti_pattern_id for anti_pattern_id in anti_pattern_ids if anti_pattern_id),
        "process_audit_rows_projection_not_authority": True,
    }


def validate_exported_observability_policy(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    policy = payload if isinstance(payload, dict) else {}
    for field in (
        "live_operator_state_read",
        "provider_payload_read",
        "browser_hud_cockpit_state_read",
        "release_authorized",
        "private_data_equivalence_claim",
        "behavior_change_overclaims_allowed",
        "live_telemetry_authority",
    ):
        if policy.get(field) is not False:
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_POLICY_FORBIDDEN_AUTHORITY",
                    "Observability policy must reject live state, provider, browser/HUD/cockpit, release, private-data-equivalence, behavior-overclaim, and telemetry-authority fields.",
                    subject_id=field,
                    subject_kind="observability_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "policy_id": policy.get("policy_id"),
        "forbidden_authority_rejected": True,
        "metadata_projection_not_live_telemetry_authority": True,
        "body_redacted": True,
    }


def validate_route_compliance(rows: list[dict[str, Any]]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    event_ids = [str(row.get("event_id") or "event") for row in rows]
    duplicate_ids = sorted(event_id for event_id, count in Counter(event_ids).items() if count > 1)
    route_compliance_decisions: list[dict[str, Any]] = []
    actor_axis_decisions: list[dict[str, Any]] = []
    actor_axis_mismatch_count = 0
    authority_rejection_count = 0

    for duplicate_id in duplicate_ids:
        _record(
            findings,
            observed,
            "DUPLICATE_TRACE_EVENT_ID",
            "Trace event id must be unique before it can feed behavior evidence.",
            case_id="duplicate_trace_event_conflict",
            subject_id=duplicate_id,
            subject_kind="agent_trace_event",
        )

    for row in rows:
        event_id = str(row.get("event_id") or "event")
        event_codes: list[str] = []
        actor_axis = str(row.get("actor_axis") or "unknown")
        behavior_refs = [str(ref) for ref in row.get("behavior_change_evidence_trace_ids", [])]

        if row.get("requires_route_lease") and not row.get("route_lease_id"):
            event_codes.append("MISSING_ROUTE_LEASE")
            _record(
                findings,
                observed,
                "MISSING_ROUTE_LEASE",
                "Trace feedback row requires a route lease id.",
                case_id="agent_trace_missing_route_lease",
                subject_id=event_id,
                subject_kind="agent_trace_event",
            )

        if row.get("forbidden_payload_class") == "private_transcript_payload":
            event_codes.append("TELEMETRY_PRIVATE_TRANSCRIPT_BODY")
            _record(
                findings,
                observed,
                "TELEMETRY_PRIVATE_TRANSCRIPT_BODY",
                "Private transcript payload class is rejected and redacted.",
                case_id="telemetry_private_transcript_body",
                subject_id=event_id,
                subject_kind="agent_trace_event",
            )

        if actor_axis == "type_b_advisory" and row.get("claims_mutation_authority"):
            actor_axis_mismatch_count += 1
            authority_rejection_count += 1
            event_codes.append("ACTOR_AXIS_AUTHORITY_MISMATCH")
            _record(
                findings,
                observed,
                "ACTOR_AXIS_AUTHORITY_MISMATCH",
                "Advisory trace cannot claim live mutation authority.",
                case_id="wrong_actor_axis_and_evidence_only_telemetry",
                subject_id=event_id,
                subject_kind="agent_trace_event",
            )
            if not behavior_refs:
                event_codes.append("NO_BEHAVIOR_CHANGE_EVIDENCE")
                _record(
                    findings,
                    observed,
                    "NO_BEHAVIOR_CHANGE_EVIDENCE",
                    "Evidence-only telemetry cannot retire behavior debt.",
                    case_id="wrong_actor_axis_and_evidence_only_telemetry",
                    subject_id=event_id,
                    subject_kind="agent_trace_event",
                )

        if row.get("route_compliance_status") == PASS and row.get("claims_behavior_change"):
            if not behavior_refs:
                event_codes.append("ROUTE_COMPLIANCE_PASS_OVERCLAIMS_BEHAVIOR_CHANGE")
                _record(
                    findings,
                    observed,
                    "ROUTE_COMPLIANCE_PASS_OVERCLAIMS_BEHAVIOR_CHANGE",
                    "Route compliance pass cannot claim behavior change without evidence ids.",
                    case_id="route_compliance_overclaims_behavior_change",
                    subject_id=event_id,
                    subject_kind="agent_trace_event",
                )

        route_compliance_decisions.append(
            {
                "event_id": event_id,
                "route_lease_id": row.get("route_lease_id"),
                "decision": "rejected" if event_codes else "accepted",
                "error_codes": sorted(set(event_codes)),
                "body_redacted": True,
            }
        )
        actor_axis_decisions.append(
            {
                "event_id": event_id,
                "actor_axis": actor_axis,
                "mutation_authority_claim_rejected": (
                    actor_axis == "type_b_advisory" and bool(row.get("claims_mutation_authority"))
                ),
                "body_redacted": True,
            }
        )

    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "trace_count": len(rows),
        "route_compliance_decisions": route_compliance_decisions,
        "actor_axis_decisions": actor_axis_decisions,
        "actor_axis_mismatch_count": actor_axis_mismatch_count,
        "authority_rejection_count": authority_rejection_count,
        "duplicate_trace_event_ids": duplicate_ids,
    }


def validate_hook_shadow(payload: object) -> dict[str, Any]:
    cases = _rows(payload, "cases")
    missing_authority = sorted(
        str(row.get("case_id") or "case")
        for row in cases
        if row.get("missing_authority")
    )
    budget_status = "within_synthetic_budget"
    if any(row.get("budget_status") == "over_budget" for row in cases):
        budget_status = "over_budget_red_flag"
    return {
        "findings": [],
        "observed_negative_cases": {},
        "hook_shadow_coverage_status": "advisory_synthetic_coverage_only",
        "intervention": "retain_as_advisory_until_trace_feedback_consumed",
        "missing_authority": missing_authority,
        "budget_status": budget_status,
    }


def validate_debt_retirement(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "debt_rows")
    decisions: list[dict[str, Any]] = []
    behavior_refs: list[str] = []
    evidence_only_refs: list[str] = []
    retired_count = 0
    for row in rows:
        debt_id = str(row.get("debt_id") or "debt")
        row_behavior_refs = [str(ref) for ref in row.get("behavior_change_evidence_trace_ids", [])]
        row_evidence_only_refs = [str(ref) for ref in row.get("evidence_only_trace_ids", [])]
        behavior_refs.extend(row_behavior_refs)
        evidence_only_refs.extend(row_evidence_only_refs)
        retired = bool(row_behavior_refs) and not bool(row_evidence_only_refs)
        if retired:
            retired_count += 1
        decisions.append(
            {
                "debt_id": debt_id,
                "decision": "retired" if retired else "retained",
                "behavior_change_evidence_trace_ids": row_behavior_refs,
                "evidence_only_trace_ids": row_evidence_only_refs,
                "body_redacted": True,
            }
        )
    return {
        "findings": [],
        "observed_negative_cases": {},
        "debt_id": "agent_route_observability_runtime.synthetic_debt_set",
        "debt_retirement_count": retired_count,
        "anti_pattern_debt_decisions": decisions,
        "behavior_change_evidence_status": (
            "behavior_change_evidence_present" if behavior_refs else "missing_behavior_change_evidence"
        ),
        "behavior_change_evidence_trace_ids": sorted(set(behavior_refs)),
        "evidence_only_trace_ids": sorted(set(evidence_only_refs)),
        "advisory_regression_evidence_retained": bool(evidence_only_refs),
    }


def validate_route_lease_mode_control(rows: list[dict[str, Any]]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    feedback_decisions: list[dict[str, Any]] = []
    kernel_bloat_count = 0
    static_metadata_count = 0
    aggregate = Counter()
    selected_lane_id = "direct_local"
    first_action_after_lease = "execute_authorized_public_slice"
    route_lease_id = "lease_trace_behavior_change"
    lease_consumed = True
    mode_control_decision = PASS
    violating_route: str | None = None

    for row in rows:
        event_id = str(row.get("event_id") or "event")
        lease_id = str(row.get("route_lease_id") or "")
        action = str(row.get("first_action_after_lease") or "")
        consumed = bool(row.get("lease_consumed"))
        decision = "accepted" if lease_id and consumed else "retained_for_feedback"
        codes: list[str] = []

        if action == "kernel_context_pack_before_direct_action":
            kernel_bloat_count += 1
            aggregate["kernel_bloat_before_direct_action"] += 1
            codes.append("KERNEL_BLOAT_BEFORE_DIRECT_ACTION")
            violating_route = "kernel_context_pack_before_direct_action"
            _record(
                findings,
                observed,
                "KERNEL_BLOAT_BEFORE_DIRECT_ACTION",
                "Route lease returned to broad kernel context before direct action.",
                case_id="route_lease_broad_kernel_bloat_before_direct_action",
                subject_id=event_id,
                subject_kind="route_lease_feedback",
            )

        if row.get("static_route_metadata_without_trace_feedback"):
            static_metadata_count += 1
            aggregate["static_metadata_without_trace_feedback"] += 1
            codes.append("ROUTE_LEASE_NOT_CONSUMED")
            if not violating_route:
                violating_route = "static_metadata_without_trace_feedback"
            _record(
                findings,
                observed,
                "ROUTE_LEASE_NOT_CONSUMED",
                "Static route metadata cannot count as consumed trace feedback.",
                case_id="route_lease_static_metadata_without_trace_feedback",
                subject_id=event_id,
                subject_kind="route_lease_feedback",
            )

        if lease_id == "lease_trace_behavior_change":
            selected_lane_id = str(row.get("selected_lane_id") or selected_lane_id)
            first_action_after_lease = action or first_action_after_lease
            route_lease_id = lease_id
            lease_consumed = consumed
            mode_control_decision = "behavior_change_evidence_accepted"

        feedback_decisions.append(
            {
                "event_id": event_id,
                "route_lease_id": lease_id or None,
                "lease_consumed": consumed,
                "decision": decision,
                "error_codes": sorted(set(codes)),
                "body_redacted": True,
            }
        )

    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "route_lease_id": route_lease_id,
        "selected_lane_id": selected_lane_id,
        "first_action_after_lease": first_action_after_lease,
        "lease_consumed": lease_consumed,
        "mode_control_decision": mode_control_decision,
        "legitimate_return_reason": "synthetic_trace_requires_direct_action_before_broad_context",
        "legitimate_return_allowed": False,
        "violating_route": violating_route,
        "aggregate_mode_control_counts": dict(sorted(aggregate.items())),
        "route_lease_mode_control_status": PASS,
        "route_lease_session_count": len([row for row in rows if row.get("route_lease_id")]),
        "route_lease_warning_session_count": kernel_bloat_count + static_metadata_count,
        "kernel_bloat_before_direct_action_count": kernel_bloat_count,
        "static_metadata_without_trace_feedback_count": static_metadata_count,
        "route_lease_feedback_decisions": feedback_decisions,
    }


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(code)
    return {key: sorted(value) for key, value in sorted(merged.items())}


def _common_receipt(result: dict[str, Any], *, schema_version: str, receipt_paths: list[str]) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "receipt_id": schema_version,
        "organ_id": result["organ_id"],
        "fixture_id": result["fixture_id"],
        "validator_id": result["validator_id"],
        "command": result["command"],
        "status": result["status"],
        "created_at": result["created_at"],
        "expected_negative_cases": result["expected_negative_cases"],
        "observed_negative_cases": result["observed_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "findings": result["findings"],
        "anti_claim": result["anti_claim"],
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "receipt_paths": receipt_paths,
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "validator_asserted_feeds_patterns": VALIDATOR_ASSERTED_FEEDS_PATTERNS,
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
    }


def _without_common_keys(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"findings", "observed_negative_cases"}
    }


def _relative_receipt_paths(paths: dict[str, Path], display_root: Path) -> list[str]:
    return [public_relative_path(path, display_root=display_root) for path in paths.values()]


def write_receipts(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: str | Path,
) -> dict[str, str]:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    target = target.resolve(strict=False)
    public_root = Path(public_root).resolve(strict=False)
    receipt_root = public_root if _is_relative_to(target, public_root) else target.parent
    paths = {
        "route_compliance": target / ROUTE_COMPLIANCE_NAME,
        "hook_shadow": target / HOOK_SHADOW_NAME,
        "debt_retirement": target / DEBT_RETIREMENT_NAME,
        "route_lease": target / ROUTE_LEASE_NAME,
    }
    receipt_paths = _relative_receipt_paths(paths, receipt_root)

    route_compliance = _common_receipt(
        validation_result,
        schema_version="agent_route_observability_runtime_route_compliance_audit_v1",
        receipt_paths=receipt_paths,
    )
    route_compliance.update(_without_common_keys(validation_result["route_compliance"]))

    hook_shadow = _common_receipt(
        validation_result,
        schema_version="agent_route_observability_runtime_hook_shadow_coverage_v1",
        receipt_paths=receipt_paths,
    )
    hook_shadow.update(_without_common_keys(validation_result["hook_shadow_coverage"]))

    debt_retirement = _common_receipt(
        validation_result,
        schema_version="agent_route_observability_runtime_debt_retirement_v1",
        receipt_paths=receipt_paths,
    )
    debt_retirement.update(_without_common_keys(validation_result["debt_retirement"]))

    route_lease = _common_receipt(
        validation_result,
        schema_version="agent_route_observability_runtime_route_lease_mode_control_v1",
        receipt_paths=receipt_paths,
    )
    route_lease.update(_without_common_keys(validation_result["route_lease_mode_control"]))

    for key, payload in (
        ("route_compliance", route_compliance),
        ("hook_shadow", hook_shadow),
        ("debt_retirement", debt_retirement),
        ("route_lease", route_lease),
    ):
        write_json_atomic(paths[key], payload)

    return {key: public_relative_path(path, display_root=receipt_root) for key, path in paths.items()}


def _write_observability_bundle_receipt(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: str | Path,
) -> str:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = Path(public_root).resolve(strict=False)
    path = target / OBSERVABILITY_BUNDLE_RESULT_NAME
    receipt_path = public_relative_path(path, display_root=public_root)
    if Path(receipt_path).is_absolute() and "receipts" in path.parts:
        receipts_index = len(path.parts) - 1 - list(reversed(path.parts)).index("receipts")
        receipt_path = Path(*path.parts[receipts_index:]).as_posix()
    payload = _common_receipt(
        validation_result,
        schema_version="agent_route_observability_runtime_exported_observability_bundle_validation_v1",
        receipt_paths=[receipt_path],
    )
    payload.update(
        {
            "bundle_manifest_schema_version": validation_result[
                "bundle_manifest_schema_version"
            ],
            "bundle_fingerprint": validation_result["bundle_fingerprint"],
            "route_event_ids": validation_result["route_event_ids"],
            "route_event_count": validation_result["route_event_count"],
            "route_compliance_decisions": validation_result["route_compliance_decisions"],
            "agent_path_observation_count": validation_result[
                "agent_path_observation_count"
            ],
            "agent_path_decisions": validation_result["agent_path_decisions"],
            "consumed_route_lease_ids": validation_result["consumed_route_lease_ids"],
            "session_diagnostic_count": validation_result["session_diagnostic_count"],
            "session_diagnostic_decisions": validation_result[
                "session_diagnostic_decisions"
            ],
            "hook_shadow_coverage": validation_result["hook_shadow_coverage"],
            "actor_axis_checks": validation_result["actor_axis_checks"],
            "debt_retirement": validation_result["debt_retirement"],
            "process_audit_rows": validation_result["process_audit_rows"],
            "observability_policy": validation_result["observability_policy"],
            "metadata_projection_not_live_telemetry_authority": validation_result[
                "metadata_projection_not_live_telemetry_authority"
            ],
            "public_replacement_refs": validation_result["public_replacement_refs"],
            "fixture_regression_required_elsewhere": True,
        }
    )
    write_json_atomic(path, payload)
    return receipt_path


def run_observability_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    payloads = _load_observability_bundle(input_path)
    scan_result = _scan_bundle_inputs(input_path, public_root)
    private_scan = dict(scan_result)
    private_scan.pop("forbidden_output_fields", None)
    private_scan["redacted_output_field_labels_omitted"] = True

    manifest = payloads["bundle_manifest"] if isinstance(payloads["bundle_manifest"], dict) else {}
    route_result = validate_exported_route_events(payloads["route_events"])
    path_result = validate_exported_agent_path_observations(
        payloads["agent_path_observations"],
        route_result,
    )
    session_result = validate_exported_session_diagnostics(payloads["session_diagnostics"])
    hook_result = validate_exported_hook_shadow_coverage(payloads["hook_shadow_coverage"])
    actor_axis_result = validate_exported_actor_axis_checks(payloads["actor_axis_checks"])
    debt_result = validate_exported_anti_pattern_debt(payloads["anti_pattern_debt"])
    process_result = validate_exported_process_audit_rows(payloads["process_audit_rows"])
    policy_result = validate_exported_observability_policy(payloads["observability_policy"])

    all_findings = sorted(
        [
            *route_result["findings"],
            *path_result["findings"],
            *session_result["findings"],
            *hook_result["findings"],
            *actor_axis_result["findings"],
            *debt_result["findings"],
            *process_result["findings"],
            *policy_result["findings"],
        ],
        key=lambda item: (
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )
    bundle_id = str(
        manifest.get("bundle_id")
        or "agent_route_observability_runtime_exported_observability_bundle"
    )
    status = (
        PASS
        if scan_result["status"] == PASS
        and not all_findings
        and route_result["route_event_ids"]
        and path_result["agent_path_observation_count"]
        and session_result["session_diagnostic_count"]
        and hook_result["covered_hook_ids"]
        and actor_axis_result["actor_axis_check_count"]
        and process_result["process_audit_row_count"]
        and policy_result["status"] == PASS
        else "blocked"
    )
    bundle_fingerprint = _stable_hash(
        {
            "route_events": payloads["route_events"],
            "agent_path_observations": payloads["agent_path_observations"],
            "session_diagnostics": payloads["session_diagnostics"],
            "hook_shadow_coverage": payloads["hook_shadow_coverage"],
            "actor_axis_checks": payloads["actor_axis_checks"],
            "anti_pattern_debt": payloads["anti_pattern_debt"],
            "process_audit_rows": payloads["process_audit_rows"],
            "observability_policy": payloads["observability_policy"],
        }
    )

    result = base_receipt(
        ORGAN_ID,
        f"{FIXTURE_ID}.exported_observability_bundle",
        command=command,
    )
    result.update(
        {
            "status": status,
            "input_mode": "exported_observability_bundle",
            "bundle_id": bundle_id,
            "bundle_manifest_schema_version": manifest.get("schema_version"),
            "validator_id": VALIDATOR_ID,
            "anti_claim": (
                "The exported observability bundle validates public route-event, "
                "agent-path, session-diagnostic, hook-shadow, actor-axis, debt, and "
                "process-audit metadata. It does not read live telemetry, provider "
                "payloads, browser/HUD/cockpit state, authorize release, or prove "
                "behavior change outside declared evidence ids."
            ),
            "authority_ceiling": {
                "status": PASS,
                "authority_ceiling": (
                    "agent_observability_bundle_metadata_not_live_telemetry_authority"
                ),
                "live_operator_state_read": False,
                "provider_payload_read": False,
                "browser_hud_cockpit_state_read": False,
                "behavior_change_overclaims_allowed": False,
                "private_data_equivalence_claim": False,
                "release_authorized": False,
                "later_organs_authorized": False,
            },
            "expected_negative_cases": {},
            "observed_negative_cases": {},
            "missing_negative_cases": [],
            "error_codes": sorted({str(finding["error_code"]) for finding in all_findings}),
            "findings": all_findings,
            "private_state_scan": private_scan,
            "source_pattern_ids": SOURCE_PATTERN_IDS,
            "validator_asserted_feeds_patterns": VALIDATOR_ASSERTED_FEEDS_PATTERNS,
            "route_event_ids": route_result["route_event_ids"],
            "route_event_count": route_result["route_event_count"],
            "route_compliance_decisions": route_result["route_compliance_decisions"],
            "behavior_change_evidence_trace_ids": route_result[
                "behavior_change_evidence_trace_ids"
            ],
            "route_events_projection_not_authority": route_result[
                "route_events_projection_not_authority"
            ],
            "agent_path_observation_count": path_result["agent_path_observation_count"],
            "agent_path_decisions": path_result["agent_path_decisions"],
            "consumed_route_lease_ids": path_result["consumed_route_lease_ids"],
            "agent_path_observations_projection_not_authority": path_result[
                "agent_path_observations_projection_not_authority"
            ],
            "session_diagnostic_count": session_result["session_diagnostic_count"],
            "session_diagnostic_decisions": session_result["session_diagnostic_decisions"],
            "session_diagnostics_projection_not_authority": session_result[
                "session_diagnostics_projection_not_authority"
            ],
            "hook_shadow_coverage": hook_result,
            "actor_axis_checks": actor_axis_result,
            "debt_retirement": debt_result,
            "process_audit_rows": process_result,
            "observability_policy": policy_result,
            "metadata_projection_not_live_telemetry_authority": True,
            "bundle_fingerprint": bundle_fingerprint,
            "public_replacement_refs": [
                public_relative_path(path, display_root=public_root)
                for path in _observability_bundle_paths(input_path)
            ],
        }
    )
    receipt_path = _write_observability_bundle_receipt(out_dir, result, public_root=public_root)
    result["receipt_paths"] = [receipt_path]
    return result


def run(input_dir: str | Path, out_dir: str | Path, command: str | None = None) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    payloads = _load_inputs(input_path)
    scan_result = _scan_fixture_inputs(input_path, public_root)

    route_compliance = validate_route_compliance(payloads["trace_rows"])
    hook_shadow = validate_hook_shadow(payloads["hook_shadow"])
    debt_retirement = validate_debt_retirement(payloads["debt"])
    route_lease = validate_route_lease_mode_control(payloads["trace_rows"])
    observed = _merge_observed(route_compliance, hook_shadow, debt_retirement, route_lease)
    missing_cases = sorted(set(EXPECTED_NEGATIVE_CASES) - set(observed))
    error_codes = sorted({code for codes in observed.values() for code in codes})
    findings = sorted(
        [*route_compliance["findings"], *route_lease["findings"]],
        key=lambda item: (
            str(item.get("negative_case_id") or ""),
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )
    private_scan = dict(scan_result)
    private_scan.pop("forbidden_output_fields", None)
    private_scan["redacted_output_field_labels_omitted"] = True
    private_scan["synthetic_boundary_negative_cases_observed"] = [
        "telemetry_private_transcript_body"
    ]

    result = base_receipt(ORGAN_ID, FIXTURE_ID, command=command)
    result.update(
        {
            "status": PASS if not missing_cases and scan_result["status"] == PASS else "blocked",
            "validator_id": VALIDATOR_ID,
            "anti_claim": OBSERVABILITY_ANTI_CLAIM,
            "authority_ceiling": OBSERVABILITY_AUTHORITY_CEILING,
            "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
            "observed_negative_cases": observed,
            "missing_negative_cases": missing_cases,
            "error_codes": error_codes,
            "findings": findings,
            "private_state_scan": private_scan,
            "route_compliance": route_compliance,
            "hook_shadow_coverage": hook_shadow,
            "debt_retirement": debt_retirement,
            "route_lease_mode_control": route_lease,
            "fixture_inputs": [
                public_relative_path(path, display_root=public_root)
                for path in _input_paths(input_path)
            ],
        }
    )
    paths = write_receipts(out_dir, result, public_root=public_root)
    result["receipt_paths"] = list(paths.values())
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("validate-observability-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.action == "run":
        command = (
            "python -m microcosm_core.organs.agent_route_observability_runtime "
            f"run --input {args.input} --out {args.out}"
        )
        result = run(args.input, args.out, command=command)
    elif args.action == "validate-observability-bundle":
        command = (
            "python -m microcosm_core.organs.agent_route_observability_runtime "
            f"validate-observability-bundle --input {args.input} --out {args.out}"
        )
        result = run_observability_bundle(args.input, args.out, command=command)
    else:
        parser.error("expected subcommand: run or validate-observability-bundle")
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
