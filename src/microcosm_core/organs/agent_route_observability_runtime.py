from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_computer_use_trace,
)
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
COMPUTER_USE_FIXTURE_RESULT_NAME = "computer_use_action_trace_replay_result.json"
COMPUTER_USE_BUNDLE_RESULT_NAME = (
    "exported_computer_use_action_trace_bundle_validation_result.json"
)

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
COMPUTER_USE_ACTION_TRACE_RECEIPT_PATH = (
    "receipts/first_wave/agent_route_observability_runtime/"
    "computer_use_action_trace_replay_result.json"
)
EXPORTED_COMPUTER_USE_ACTION_TRACE_BUNDLE_RECEIPT_PATH = (
    "receipts/first_wave/agent_route_observability_runtime/"
    "exported_computer_use_action_trace_bundle_validation_result.json"
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
HOOK_SHADOW_EXPECTED_NEGATIVE_CASES = {
    "hook_shadow_missing_authority": ["HOOK_SHADOW_MISSING_AUTHORITY"],
    "hook_shadow_banned_route_attempt": ["HOOK_SHADOW_BANNED_ROUTE_INTERVENTION"],
    "hook_shadow_command_displacement": ["HOOK_SHADOW_COMMAND_DISPLACEMENT"],
    "hook_shadow_live_state_read_attempt": ["HOOK_SHADOW_LIVE_STATE_READ_FORBIDDEN"],
    "hook_shadow_budget_overrun": ["HOOK_SHADOW_OVER_BUDGET"],
}
EXPECTED_NEGATIVE_CASES.update(HOOK_SHADOW_EXPECTED_NEGATIVE_CASES)
COMPUTER_USE_EXPECTED_NEGATIVE_CASES = {
    "live_account_action": ["COMPUTER_USE_LIVE_ACCOUNT_ACTION_FORBIDDEN"],
    "credential_entry": ["COMPUTER_USE_CREDENTIAL_ENTRY_FORBIDDEN"],
    "external_network_mutation": ["COMPUTER_USE_EXTERNAL_NETWORK_MUTATION_FORBIDDEN"],
    "unapproved_purchase_or_send": ["COMPUTER_USE_UNAPPROVED_PURCHASE_OR_SEND"],
    "destructive_file_action": ["COMPUTER_USE_DESTRUCTIVE_ACTION_WITHOUT_REVIEW"],
    "hidden_screen_state_claim": ["COMPUTER_USE_HIDDEN_SCREEN_STATE_CLAIM"],
    "action_without_observation": ["COMPUTER_USE_ACTION_WITHOUT_OBSERVATION"],
    "benchmark_score_claim": ["COMPUTER_USE_BENCHMARK_SCORE_CLAIM"],
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
COMPUTER_USE_AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "public_agent_execution_trace_refactor_over_synthetic_computer_use_fixture"
    ),
    "live_browser_control_authorized": False,
    "live_account_action_authorized": False,
    "credential_entry_authorized": False,
    "external_network_mutation_authorized": False,
    "purchase_or_send_authorized": False,
    "destructive_host_action_authorized": False,
    "raw_screenshot_body_export_authorized": False,
    "hidden_screen_state_claim_authorized": False,
    "benchmark_score_claim_authorized": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
}
COMPUTER_USE_ANTI_CLAIM = (
    "Computer-use action trace replay validates synthetic observation, "
    "affordance, action, pre-action authority verdict, state-transition, "
    "recovery, cold-replay, negative-case, public agent-execution trace "
    "spans, and authority-ceiling receipts. "
    "It does not control a live browser or desktop, use real accounts, enter "
    "credentials, mutate external networks, purchase or send anything, perform "
    "destructive host actions, export raw screenshots, claim hidden screen "
    "state, report benchmark scores, call providers, mutate source, or "
    "authorize release."
)

SOURCE_PATTERN_IDS = [
    "agent_route_observability_runtime",
    "route_lease_mode_control",
    "actor_axis_authority_boundary",
    "anti_pattern_debt_retirement",
    "trace_feedback_behavior_change_gate",
    "runtime_hook_shadow_intervention_coverage",
]
COMPUTER_USE_SOURCE_PATTERN_IDS = [
    "computer_use_action_trace_replay_compound",
    "agent_route_observability_runtime",
    "agent_execution_trace",
    "affordance_before_action_authority",
    "ui_action_is_not_evidence_until_replayable",
]

COMPUTER_USE_INPUT_NAMES = (
    "projection_protocol.json",
    "interaction_policy.json",
    "task_episodes.json",
    "screen_observations.json",
    "action_trace.json",
    "authority_verdicts.json",
    "state_transition_receipts.json",
    "recovery_receipts.json",
    "cold_replay.json",
)
COMPUTER_USE_NEGATIVE_INPUT_NAMES = (
    "live_account_action.json",
    "credential_entry.json",
    "external_network_mutation.json",
    "unapproved_purchase_or_send.json",
    "destructive_file_action.json",
    "hidden_screen_state_claim.json",
    "action_without_observation.json",
    "benchmark_score_claim.json",
)
COMPUTER_USE_ALLOWED_ACTION_KINDS = {
    "observe",
    "click",
    "type",
    "select",
    "navigate",
    "wait",
    "edit_text_record",
}
COMPUTER_USE_FORBIDDEN_KEYS = {
    "raw_screenshot_body",
    "screenshot_pixels",
    "credential_value",
    "password",
    "secret_value",
    "live_account_identifier",
    "real_target_url",
    "provider_payload",
    "hidden_screen_state",
    "payment_token",
}

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
    {
        "assertion_id": "hook_shadow_intervention_requires_mapped_repair_and_ceiling",
        "source_pattern_id": "runtime_hook_shadow_intervention_coverage",
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


def _computer_use_action_trace_paths(
    input_dir: Path,
    *,
    include_negative: bool,
) -> list[Path]:
    names = (
        "bundle_manifest.json",
        *COMPUTER_USE_INPUT_NAMES,
        *(COMPUTER_USE_NEGATIVE_INPUT_NAMES if include_negative else ()),
    )
    return [input_dir / name for name in names if (input_dir / name).is_file()]


def _has_computer_use_negative_inputs(input_dir: Path) -> bool:
    return any((input_dir / name).is_file() for name in COMPUTER_USE_NEGATIVE_INPUT_NAMES)


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


def _load_computer_use_action_trace_bundle(
    input_dir: Path,
    *,
    include_negative: bool,
) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _computer_use_action_trace_paths(
            input_dir,
            include_negative=include_negative,
        )
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


def _scan_computer_use_action_trace_inputs(
    input_dir: Path,
    public_root: Path,
    *,
    include_negative: bool,
) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    return scan_paths(
        _computer_use_action_trace_paths(input_dir, include_negative=include_negative),
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


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _missing(row: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    return [field for field in required if row.get(field) in (None, "", [])]


def _has_computer_use_forbidden_key(row: dict[str, Any]) -> bool:
    return any(key in row for key in COMPUTER_USE_FORBIDDEN_KEYS)


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
    decisions: list[dict[str, Any]] = []
    repair_classes: set[str] = set()
    missing_authority_count = 0
    forbidden_fields = (
        "browser_hud_state_read",
        "browser_hud_cockpit_state_read",
        "live_operator_state_read",
        "provider_payload_read",
        "live_task_ledger_mutation_authorized",
    )
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
        repair_class = str(row.get("repair_class") or "")
        row_codes: list[str] = []
        covered_hook_ids.append(hook_id)
        if repair_class:
            repair_classes.add(repair_class)
        if row.get("missing_authority") is True:
            missing_authority_count += 1
        if _missing(
            row,
            (
                "hook_id",
                "coverage_status",
                "repair_class",
                "expected_intervention",
            ),
        ):
            row_codes.append("OBSERVABILITY_BUNDLE_HOOK_SHADOW_REQUIRED_FIELD_MISSING")
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_HOOK_SHADOW_REQUIRED_FIELD_MISSING",
                    "Hook shadow row must map a hook id to coverage status, repair class, and expected intervention.",
                    subject_id=hook_id or "hook_shadow",
                    subject_kind="hook_shadow",
                )
            )
        if row.get("projection_not_authority") is not True:
            row_codes.append("OBSERVABILITY_BUNDLE_HOOK_SHADOW_PROJECTION_FLAG_MISSING")
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_HOOK_SHADOW_PROJECTION_FLAG_MISSING",
                    "Hook shadow row must declare projection_not_authority.",
                    subject_id=hook_id or "hook_shadow",
                    subject_kind="hook_shadow",
                )
            )
        for field in forbidden_fields:
            if row.get(field) is not False:
                row_codes.append("OBSERVABILITY_BUNDLE_HOOK_SHADOW_AUTHORITY_OVERCLAIM")
                findings.append(
                    _bundle_finding(
                        "OBSERVABILITY_BUNDLE_HOOK_SHADOW_AUTHORITY_OVERCLAIM",
                        "Hook shadow row must reject live operator, provider, browser/HUD/cockpit, and Task Ledger authority.",
                        subject_id=hook_id or field,
                        subject_kind="hook_shadow",
                    )
                )
        if row.get("body_redacted") is not True:
            row_codes.append("OBSERVABILITY_BUNDLE_HOOK_SHADOW_BODY_NOT_REDACTED")
            findings.append(
                _bundle_finding(
                    "OBSERVABILITY_BUNDLE_HOOK_SHADOW_BODY_NOT_REDACTED",
                    "Hook shadow row must be metadata-only and body-redacted.",
                    subject_id=hook_id or "hook_shadow",
                    subject_kind="hook_shadow",
                )
            )
        decisions.append(
            {
                "hook_id": hook_id,
                "repair_class": repair_class,
                "expected_intervention": row.get("expected_intervention"),
                "coverage_status": row.get("coverage_status"),
                "decision": "accepted" if not row_codes else "blocked",
                "error_codes": sorted(set(row_codes)),
                "body_redacted": True,
            }
        )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "hook_shadow_coverage_status": "public_metadata_coverage_only",
        "covered_hook_ids": sorted(hook_id for hook_id in covered_hook_ids if hook_id),
        "hook_shadow_case_count": len(rows),
        "hook_shadow_decisions": decisions,
        "mapped_repair_classes": sorted(repair_classes),
        "hook_shadow_repair_class_count": len(repair_classes),
        "missing_authority_count": missing_authority_count,
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
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    cases = _rows(payload, "cases")
    decisions: list[dict[str, Any]] = []
    repair_classes: set[str] = set()
    missing_authority: list[str] = []
    structural_error_codes: list[str] = []
    forbidden_live_fields = (
        "browser_hud_state_read",
        "browser_hud_cockpit_state_read",
        "live_operator_state_read",
        "provider_payload_read",
        "live_task_ledger_mutation_authorized",
    )
    if not cases:
        findings.append(
            _finding(
                "HOOK_SHADOW_CASES_MISSING",
                "Hook-shadow coverage must include at least one synthetic case.",
                case_id="hook_shadow_cases_missing",
                subject_id="hook_shadow_cases",
                subject_kind="hook_shadow_case",
            )
        )
        structural_error_codes.append("HOOK_SHADOW_CASES_MISSING")

    for row in cases:
        case_id = str(row.get("case_id") or "hook_shadow_case")
        hook_id = str(row.get("hook_id") or "")
        repair_class = str(row.get("repair_class") or "")
        row_codes: list[str] = []
        if repair_class:
            repair_classes.add(repair_class)
        missing_fields = _missing(
            row,
            (
                "case_id",
                "hook_id",
                "coverage_claim",
                "repair_class",
                "expected_intervention",
            ),
        )
        if missing_fields:
            row_codes.append("HOOK_SHADOW_REQUIRED_FIELD_MISSING")
            structural_error_codes.append("HOOK_SHADOW_REQUIRED_FIELD_MISSING")
            findings.append(
                _finding(
                    "HOOK_SHADOW_REQUIRED_FIELD_MISSING",
                    "Hook-shadow case must map case id, hook id, coverage claim, repair class, and expected intervention.",
                    case_id=case_id,
                    subject_id=hook_id or case_id,
                    subject_kind="hook_shadow_case",
                )
            )
        if row.get("projection_not_authority") is not True:
            row_codes.append("HOOK_SHADOW_PROJECTION_FLAG_MISSING")
            structural_error_codes.append("HOOK_SHADOW_PROJECTION_FLAG_MISSING")
            findings.append(
                _finding(
                    "HOOK_SHADOW_PROJECTION_FLAG_MISSING",
                    "Hook-shadow case must declare projection_not_authority.",
                    case_id=case_id,
                    subject_id=hook_id or case_id,
                    subject_kind="hook_shadow_case",
                )
            )
        if row.get("redaction_status") != "metadata_only":
            row_codes.append("HOOK_SHADOW_NON_METADATA_REDACTION")
            structural_error_codes.append("HOOK_SHADOW_NON_METADATA_REDACTION")
            findings.append(
                _finding(
                    "HOOK_SHADOW_NON_METADATA_REDACTION",
                    "Hook-shadow cases must remain metadata-only.",
                    case_id=case_id,
                    subject_id=hook_id or case_id,
                    subject_kind="hook_shadow_case",
                )
            )
        live_field_denied = False
        for field in forbidden_live_fields:
            if row.get(field) is not False:
                live_field_denied = True
                row_codes.append("HOOK_SHADOW_LIVE_STATE_READ_FORBIDDEN")
        if live_field_denied:
            _record(
                findings,
                observed,
                "HOOK_SHADOW_LIVE_STATE_READ_FORBIDDEN",
                "Hook-shadow coverage cannot read live operator, provider, browser/HUD/cockpit, or Task Ledger state.",
                case_id=case_id,
                subject_id=hook_id or case_id,
                subject_kind="hook_shadow_case",
            )
        if row.get("missing_authority") is True:
            missing_authority.append(case_id)
            row_codes.append("HOOK_SHADOW_MISSING_AUTHORITY")
            _record(
                findings,
                observed,
                "HOOK_SHADOW_MISSING_AUTHORITY",
                "Hook-shadow row lacks authority to intervene and must remain advisory.",
                case_id=case_id,
                subject_id=hook_id or case_id,
                subject_kind="hook_shadow_case",
            )
        if row.get("banned_route_attempt"):
            row_codes.append("HOOK_SHADOW_BANNED_ROUTE_INTERVENTION")
            _record(
                findings,
                observed,
                "HOOK_SHADOW_BANNED_ROUTE_INTERVENTION",
                "Hook-shadow row detects a banned first-contact route and must redirect through the kernel entry path.",
                case_id=case_id,
                subject_id=hook_id or case_id,
                subject_kind="hook_shadow_case",
            )
        if row.get("command_displacement") is True:
            row_codes.append("HOOK_SHADOW_COMMAND_DISPLACEMENT")
            _record(
                findings,
                observed,
                "HOOK_SHADOW_COMMAND_DISPLACEMENT",
                "Hook-shadow row detects context gathering displacing direct local action.",
                case_id=case_id,
                subject_id=hook_id or case_id,
                subject_kind="hook_shadow_case",
            )
        if row.get("budget_status") == "over_budget":
            row_codes.append("HOOK_SHADOW_OVER_BUDGET")
            _record(
                findings,
                observed,
                "HOOK_SHADOW_OVER_BUDGET",
                "Hook-shadow row exceeds its public synthetic coverage budget and must be downgraded.",
                case_id=case_id,
                subject_id=hook_id or case_id,
                subject_kind="hook_shadow_case",
            )
        decisions.append(
            {
                "case_id": case_id,
                "hook_id": hook_id,
                "repair_class": repair_class,
                "coverage_claim": row.get("coverage_claim"),
                "expected_intervention": row.get("expected_intervention"),
                "decision": "accepted" if not row_codes else "blocked_or_advisory",
                "error_codes": sorted(set(row_codes)),
                "body_redacted": True,
            }
        )
    budget_status = "within_synthetic_budget"
    if any(row.get("budget_status") == "over_budget" for row in cases):
        budget_status = "over_budget_denied"
    observed_payload = {key: sorted(value) for key, value in observed.items()}
    missing_hook_cases = sorted(
        set(HOOK_SHADOW_EXPECTED_NEGATIVE_CASES) - set(observed_payload)
    )
    return {
        "status": (
            PASS
            if cases
            and not set(structural_error_codes)
            and not missing_hook_cases
            else "blocked"
        ),
        "findings": sorted(
            findings,
            key=lambda item: (
                str(item.get("negative_case_id") or ""),
                str(item.get("subject_id") or ""),
                str(item.get("error_code") or ""),
            ),
        ),
        "observed_negative_cases": observed_payload,
        "hook_shadow_coverage_status": "synthetic_intervention_coverage_contract",
        "intervention": "admit_shadow_rows_only_with_mapped_repair_and_authority_ceiling",
        "hook_shadow_decisions": decisions,
        "hook_shadow_case_count": len(cases),
        "hook_shadow_expected_negative_case_ids": sorted(
            HOOK_SHADOW_EXPECTED_NEGATIVE_CASES
        ),
        "missing_hook_shadow_negative_cases": missing_hook_cases,
        "mapped_repair_classes": sorted(repair_classes),
        "hook_shadow_repair_class_count": len(repair_classes),
        "missing_authority": sorted(missing_authority),
        "missing_authority_count": len(missing_authority),
        "banned_route_intervention_count": sum(
            1 for row in cases if row.get("banned_route_attempt")
        ),
        "command_displacement_count": sum(
            1 for row in cases if row.get("command_displacement") is True
        ),
        "live_state_read_denial_count": sum(
            1
            for row in cases
            if any(row.get(field) is not False for field in forbidden_live_fields)
        ),
        "over_budget_denial_count": sum(
            1 for row in cases if row.get("budget_status") == "over_budget"
        ),
        "structural_error_codes": sorted(set(structural_error_codes)),
        "budget_status": budget_status,
        "projection_not_authority": True,
        "authority_ceiling": {
            "live_operator_state_read": False,
            "provider_payload_read": False,
            "browser_hud_cockpit_state_read": False,
            "live_task_ledger_mutation_authorized": False,
            "pattern_assimilation_authorized": False,
        },
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


def _computer_use_action_ids(rows: list[dict[str, Any]]) -> set[str]:
    return {str(row.get("action_id")) for row in rows if row.get("action_id")}


def _validate_computer_use_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    findings: list[dict[str, Any]] = []
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    source_refs = _strings(protocol.get("source_refs"))
    omitted_material = _strings(protocol.get("omitted_secret_or_live_access_material"))
    target_refs = _strings(protocol.get("target_refs"))
    body_import = protocol.get("body_import_verification")
    body_import = body_import if isinstance(body_import, dict) else {}
    if "computer_use_action_trace_replay_compound" not in source_pattern_ids:
        findings.append(
            _bundle_finding(
                "COMPUTER_USE_PROJECTION_PROTOCOL_PATTERN_MISSING",
                "Projection protocol must cite the computer-use action trace replay pattern.",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    if len(source_refs) < 4 or len(omitted_material) < 7:
        findings.append(
            _bundle_finding(
                "COMPUTER_USE_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Projection protocol must cite source refs and secret/live-access exclusions.",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    if (
        "microcosm-substrate/src/microcosm_core/macro_tools/agent_execution_trace.py"
        not in target_refs
        or body_import.get("verification_mode") != "source_faithful_public_refactor"
    ):
        findings.append(
            _bundle_finding(
                "COMPUTER_USE_AGENT_EXECUTION_TRACE_REFACTOR_MISSING",
                "Projection protocol must bind the macro agent-execution trace source to its public Microcosm refactor.",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    for flag in (
        "copied_credential_or_account_bound_source",
        "exports_secret_or_live_access_material",
        "exports_raw_screenshots",
        "authorizes_live_browser_control",
        "authorizes_account_actions",
        "authorizes_source_mutation",
        "claims_benchmark_score",
    ):
        if protocol.get(flag) is not False:
            findings.append(
                _bundle_finding(
                    "COMPUTER_USE_PROJECTION_PROTOCOL_AUTHORITY_OVERCLAIM",
                    "Projection protocol must deny secret/live-access export, live control, account actions, mutation, and benchmark claims.",
                    subject_id=flag,
                    subject_kind="projection_protocol",
                )
            )
    return {
        "findings": findings,
        "protocol_id": protocol.get("protocol_id"),
        "source_pattern_ids": source_pattern_ids,
        "source_refs": source_refs,
        "target_refs": target_refs,
        "body_import_verification": body_import,
        "projection_receipt_refs": _strings(protocol.get("projection_receipt_refs")),
        "public_runtime_refs": _strings(protocol.get("public_runtime_refs")),
        "omitted_secret_or_live_access_material": omitted_material,
    }


def _validate_computer_use_interaction_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    findings: list[dict[str, Any]] = []
    allowed = set(_strings(policy.get("allowed_action_kinds")))
    if not COMPUTER_USE_ALLOWED_ACTION_KINDS.issubset(allowed):
        findings.append(
            _bundle_finding(
                "COMPUTER_USE_POLICY_ACTION_KIND_COVERAGE_MISSING",
                "Interaction policy must name all allowed synthetic action kinds.",
                subject_id=str(policy.get("policy_id") or "interaction_policy"),
                subject_kind="interaction_policy",
            )
        )
    for field in (
        "live_browser_control_authorized",
        "live_account_action_authorized",
        "credential_entry_authorized",
        "external_network_mutation_authorized",
        "purchase_or_send_authorized",
        "destructive_host_action_authorized",
        "raw_screenshot_body_export_authorized",
        "hidden_screen_state_claim_authorized",
        "benchmark_score_claim_authorized",
        "source_mutation_authorized",
        "release_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _bundle_finding(
                    "COMPUTER_USE_POLICY_AUTHORITY_OVERCLAIM",
                    "Interaction policy must deny live control, accounts, credentials, network mutation, destructive action, raw screenshots, benchmark claims, source mutation, and release.",
                    subject_id=field,
                    subject_kind="interaction_policy",
                )
            )
    return {
        "findings": findings,
        "policy_id": policy.get("policy_id"),
        "allowed_action_kinds": sorted(allowed),
    }


def _validate_computer_use_episodes(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "episodes")
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    required = (
        "episode_id",
        "task_label",
        "target_surface",
        "synthetic_environment",
        "live_account_context",
        "external_network_allowed",
        "authority_ceiling_ref",
        "body_redacted",
    )
    for row in rows:
        episode_id = str(row.get("episode_id") or "")
        if (
            _missing(row, required)
            or _has_computer_use_forbidden_key(row)
            or row.get("synthetic_environment") is not True
            or row.get("live_account_context") is not False
            or row.get("external_network_allowed") is not False
            or row.get("body_redacted") is not True
        ):
            findings.append(
                _bundle_finding(
                    "COMPUTER_USE_EPISODE_INVALID",
                    "Episodes must be synthetic, redacted, local-only, and account-free.",
                    subject_id=episode_id or "episode",
                    subject_kind="episode",
                )
            )
        exported.append(
            {
                "episode_id": episode_id,
                "task_label": row.get("task_label"),
                "target_surface": row.get("target_surface"),
                "synthetic_environment": row.get("synthetic_environment"),
                "live_account_context": row.get("live_account_context"),
                "external_network_allowed": row.get("external_network_allowed"),
                "authority_ceiling_ref": row.get("authority_ceiling_ref"),
                "body_in_receipt": False,
            }
        )
    return {
        "findings": findings,
        "episode_rows": sorted(exported, key=lambda item: item["episode_id"]),
        "episode_count": len(rows),
    }


def _validate_computer_use_observations(
    payload: object,
    episode_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = _rows(payload, "observations")
    episode_ids = {row["episode_id"] for row in episode_rows}
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    required = (
        "observation_id",
        "episode_id",
        "step_index",
        "screenshot_digest",
        "dom_or_accessibility_summary_ref",
        "affordance_refs",
        "visible_state_hash",
        "raw_screenshot_body_exported",
        "hidden_state_claim",
        "live_browser_state",
        "body_redacted",
    )
    for row in rows:
        observation_id = str(row.get("observation_id") or "")
        if (
            _missing(row, required)
            or _has_computer_use_forbidden_key(row)
            or row.get("episode_id") not in episode_ids
            or not _strings(row.get("affordance_refs"))
            or row.get("raw_screenshot_body_exported") is not False
            or row.get("hidden_state_claim") is not False
            or row.get("live_browser_state") is not False
            or row.get("body_redacted") is not True
        ):
            findings.append(
                _bundle_finding(
                    "COMPUTER_USE_OBSERVATION_INVALID",
                    "Observations must be redacted synthetic visible-state rows with affordance refs and screenshot digests.",
                    subject_id=observation_id or "observation",
                    subject_kind="observation",
                )
            )
        exported.append(
            {
                "observation_id": observation_id,
                "episode_id": row.get("episode_id"),
                "step_index": row.get("step_index"),
                "screenshot_digest": row.get("screenshot_digest"),
                "dom_or_accessibility_summary_ref": row.get("dom_or_accessibility_summary_ref"),
                "affordance_refs": _strings(row.get("affordance_refs")),
                "visible_state_hash": row.get("visible_state_hash"),
                "body_in_receipt": False,
            }
        )
    observed_episode_ids = {row["episode_id"] for row in exported}
    if not episode_ids.issubset(observed_episode_ids):
        findings.append(
            _bundle_finding(
                "COMPUTER_USE_EPISODE_OBSERVATION_COVERAGE_MISSING",
                "Every episode must have at least one observation before actions are admitted.",
                subject_id="screen_observations",
                subject_kind="observation",
            )
        )
    return {
        "findings": findings,
        "observation_rows": sorted(exported, key=lambda item: item["observation_id"]),
        "observation_count": len(rows),
    }


def _validate_computer_use_actions(
    payload: object,
    episode_rows: list[dict[str, Any]],
    observation_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = _rows(payload, "actions")
    episode_ids = {row["episode_id"] for row in episode_rows}
    observations = {str(row["observation_id"]): row for row in observation_rows}
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    required = (
        "action_id",
        "episode_id",
        "step_index",
        "observation_ref",
        "affordance_ref",
        "action_kind",
        "target_ref",
        "input_digest",
        "authority_verdict_id",
        "state_transition_ref",
        "execution_status",
        "body_redacted",
    )
    for row in rows:
        action_id = str(row.get("action_id") or "")
        observation_ref = str(row.get("observation_ref") or "")
        observation = observations.get(observation_ref)
        action_kind = str(row.get("action_kind") or "")
        if (
            _missing(row, required)
            or _has_computer_use_forbidden_key(row)
            or row.get("episode_id") not in episode_ids
            or observation is None
            or (
                observation is not None
                and int(row.get("step_index") or 0) < int(observation.get("step_index") or 0)
            )
            or action_kind not in COMPUTER_USE_ALLOWED_ACTION_KINDS
            or row.get("body_redacted") is not True
        ):
            findings.append(
                _bundle_finding(
                    "COMPUTER_USE_ACTION_TRACE_INVALID",
                    "Actions must follow observations, cite affordances, use allowed action kinds, and stay redacted.",
                    subject_id=action_id or "action",
                    subject_kind="action",
                )
            )
        exported.append(
            {
                "action_id": action_id,
                "episode_id": row.get("episode_id"),
                "step_index": row.get("step_index"),
                "observation_ref": observation_ref,
                "affordance_ref": row.get("affordance_ref"),
                "action_kind": action_kind,
                "target_ref": row.get("target_ref"),
                "input_digest": row.get("input_digest"),
                "authority_verdict_id": row.get("authority_verdict_id"),
                "state_transition_ref": row.get("state_transition_ref"),
                "recovery_ref": row.get("recovery_ref"),
                "execution_status": row.get("execution_status"),
                "body_in_receipt": False,
            }
        )
    action_kinds = {row["action_kind"] for row in exported}
    if not {"click", "type", "navigate", "edit_text_record", "wait"}.issubset(action_kinds):
        findings.append(
            _bundle_finding(
                "COMPUTER_USE_ACTION_KIND_COVERAGE_MISSING",
                "Fixture must cover navigation, clicking, typing, waiting, and toy-record editing.",
                subject_id="action_trace",
                subject_kind="action",
            )
        )
    return {
        "findings": findings,
        "action_rows": sorted(exported, key=lambda item: item["action_id"]),
        "action_count": len(rows),
        "action_kinds": sorted(action_kinds),
    }


def _validate_computer_use_authority_verdicts(
    payload: object,
    action_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = _rows(payload, "authority_verdicts")
    action_by_id = {row["action_id"]: row for row in action_rows}
    action_verdict_ids = {str(row.get("authority_verdict_id")) for row in action_rows}
    verdict_by_id: dict[str, dict[str, Any]] = {}
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    required = (
        "verdict_id",
        "action_id",
        "policy_version",
        "verdict",
        "pre_action",
        "rule_refs",
        "live_account_authorized",
        "credential_entry_authorized",
        "external_network_mutation_authorized",
        "destructive_without_review_authorized",
        "purchase_or_send_authorized",
        "body_redacted",
    )
    for row in rows:
        verdict_id = str(row.get("verdict_id") or "")
        action_id = str(row.get("action_id") or "")
        verdict = str(row.get("verdict") or "")
        if (
            _missing(row, required)
            or _has_computer_use_forbidden_key(row)
            or action_id not in action_by_id
            or verdict_id not in action_verdict_ids
            or verdict not in {"allow", "block", "review"}
            or row.get("pre_action") is not True
            or not _strings(row.get("rule_refs"))
            or row.get("live_account_authorized") is not False
            or row.get("credential_entry_authorized") is not False
            or row.get("external_network_mutation_authorized") is not False
            or row.get("destructive_without_review_authorized") is not False
            or row.get("purchase_or_send_authorized") is not False
            or row.get("body_redacted") is not True
        ):
            findings.append(
                _bundle_finding(
                    "COMPUTER_USE_AUTHORITY_VERDICT_INVALID",
                    "Every action must have a pre-action authority verdict that denies live-account, credential, network, destructive, purchase/send, and benchmark authority.",
                    subject_id=verdict_id or "authority_verdict",
                    subject_kind="authority_verdict",
                )
            )
        verdict_by_id[verdict_id] = {"action_id": action_id, "verdict": verdict}
        exported.append(
            {
                "verdict_id": verdict_id,
                "action_id": action_id,
                "policy_version": row.get("policy_version"),
                "verdict": verdict,
                "pre_action": row.get("pre_action"),
                "rule_refs": _strings(row.get("rule_refs")),
                "body_in_receipt": False,
            }
        )
    missing = sorted(action_verdict_ids - set(verdict_by_id))
    if missing:
        findings.append(
            _bundle_finding(
                "COMPUTER_USE_ACTION_VERDICT_COVERAGE_MISSING",
                "Every action must cite a present authority verdict.",
                subject_id=",".join(missing),
                subject_kind="authority_verdict",
            )
        )
    return {
        "findings": findings,
        "authority_verdict_rows": sorted(exported, key=lambda item: item["verdict_id"]),
        "authority_verdict_count": len(rows),
        "allow_count": sum(1 for row in exported if row["verdict"] == "allow"),
        "block_count": sum(1 for row in exported if row["verdict"] == "block"),
        "review_count": sum(1 for row in exported if row["verdict"] == "review"),
        "verdict_by_id": verdict_by_id,
    }


def _validate_computer_use_state_transitions(
    payload: object,
    action_rows: list[dict[str, Any]],
    verdict_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rows = _rows(payload, "state_transitions")
    action_by_id = {row["action_id"]: row for row in action_rows}
    transition_refs = {str(row.get("state_transition_ref")) for row in action_rows}
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    required = (
        "transition_id",
        "action_id",
        "before_state_hash",
        "after_state_hash",
        "execution_attempted",
        "oracle_status",
        "diff_ref",
        "nondeterministic_success_claim",
        "body_redacted",
    )
    for row in rows:
        transition_id = str(row.get("transition_id") or "")
        action_id = str(row.get("action_id") or "")
        action = action_by_id.get(action_id, {})
        verdict_id = str(action.get("authority_verdict_id") or "")
        verdict = verdict_by_id.get(verdict_id, {}).get("verdict")
        oracle_status = str(row.get("oracle_status") or "")
        if (
            _missing(row, required)
            or _has_computer_use_forbidden_key(row)
            or action_id not in action_by_id
            or transition_id not in transition_refs
            or row.get("nondeterministic_success_claim") is not False
            or row.get("body_redacted") is not True
            or (
                verdict == "allow"
                and (
                    row.get("execution_attempted") is not True
                    or oracle_status != "pass"
                )
            )
            or (
                verdict in {"block", "review"}
                and (
                    row.get("execution_attempted") is not False
                    or oracle_status not in {"blocked", "review_required"}
                )
            )
        ):
            findings.append(
                _bundle_finding(
                    "COMPUTER_USE_STATE_TRANSITION_INVALID",
                    "State-transition receipts must match action verdicts and avoid nondeterministic success claims.",
                    subject_id=transition_id or "state_transition",
                    subject_kind="state_transition",
                )
            )
        exported.append(
            {
                "transition_id": transition_id,
                "action_id": action_id,
                "execution_attempted": row.get("execution_attempted"),
                "oracle_status": oracle_status,
                "diff_ref": row.get("diff_ref"),
                "nondeterministic_success_claim": row.get("nondeterministic_success_claim"),
                "body_in_receipt": False,
            }
        )
    missing = sorted(transition_refs - {row["transition_id"] for row in exported})
    if missing:
        findings.append(
            _bundle_finding(
                "COMPUTER_USE_ACTION_TRANSITION_COVERAGE_MISSING",
                "Every action must cite a present state-transition receipt.",
                subject_id=",".join(missing),
                subject_kind="state_transition",
            )
        )
    return {
        "findings": findings,
        "state_transition_rows": sorted(exported, key=lambda item: item["transition_id"]),
        "state_transition_count": len(rows),
        "executed_transition_count": sum(
            1 for row in exported if row["execution_attempted"] is True
        ),
        "blocked_transition_count": sum(
            1 for row in exported if row["oracle_status"] in {"blocked", "review_required"}
        ),
    }


def _validate_computer_use_recovery_receipts(
    payload: object,
    action_rows: list[dict[str, Any]],
    verdict_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rows = _rows(payload, "recovery_receipts")
    recovery_refs = {
        str(row.get("recovery_ref"))
        for row in action_rows
        if verdict_by_id.get(str(row.get("authority_verdict_id")), {}).get("verdict")
        in {"block", "review"}
    }
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    required = (
        "recovery_id",
        "action_id",
        "recovery_status",
        "user_visible_error_ref",
        "state_restored",
        "body_redacted",
    )
    for row in rows:
        recovery_id = str(row.get("recovery_id") or "")
        if (
            _missing(row, required)
            or _has_computer_use_forbidden_key(row)
            or recovery_id not in recovery_refs
            or row.get("recovery_status") != "recovered"
            or row.get("state_restored") is not True
            or row.get("body_redacted") is not True
        ):
            findings.append(
                _bundle_finding(
                    "COMPUTER_USE_RECOVERY_RECEIPT_INVALID",
                    "Blocked or reviewed actions must have redacted recovery receipts.",
                    subject_id=recovery_id or "recovery_receipt",
                    subject_kind="recovery_receipt",
                )
            )
        exported.append(
            {
                "recovery_id": recovery_id,
                "action_id": row.get("action_id"),
                "recovery_status": row.get("recovery_status"),
                "user_visible_error_ref": row.get("user_visible_error_ref"),
                "state_restored": row.get("state_restored"),
                "body_in_receipt": False,
            }
        )
    missing = sorted(recovery_refs - {row["recovery_id"] for row in exported})
    if missing:
        findings.append(
            _bundle_finding(
                "COMPUTER_USE_RECOVERY_COVERAGE_MISSING",
                "Every blocked or reviewed action must cite a present recovery receipt.",
                subject_id=",".join(missing),
                subject_kind="recovery_receipt",
            )
        )
    return {
        "findings": findings,
        "recovery_rows": sorted(exported, key=lambda item: item["recovery_id"]),
        "recovery_receipt_count": len(rows),
        "recovered_action_count": sum(
            1 for row in exported if row["recovery_status"] == "recovered"
        ),
    }


def _validate_computer_use_cold_replay(
    payload: object,
    action_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = _rows(payload, "cold_replay")
    action_ids = _computer_use_action_ids(action_rows)
    replayed: set[str] = set()
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    required = (
        "replay_id",
        "episode_id",
        "action_ids",
        "replay_command",
        "receipt_ref",
        "trace_reproduced",
        "authority_verdicts_reproduced",
        "state_transitions_reproduced",
        "pass_label",
        "body_redacted",
    )
    for row in rows:
        replay_id = str(row.get("replay_id") or "")
        row_action_ids = set(_strings(row.get("action_ids")))
        replayed.update(row_action_ids)
        if (
            _missing(row, required)
            or _has_computer_use_forbidden_key(row)
            or not row_action_ids
            or not row_action_ids.issubset(action_ids)
            or row.get("trace_reproduced") is not True
            or row.get("authority_verdicts_reproduced") is not True
            or row.get("state_transitions_reproduced") is not True
            or row.get("pass_label") not in {"accepted", "blocked_recovered"}
            or row.get("body_redacted") is not True
        ):
            findings.append(
                _bundle_finding(
                    "COMPUTER_USE_COLD_REPLAY_INVALID",
                    "Cold replay must reproduce action traces, authority verdicts, and state transitions.",
                    subject_id=replay_id or "cold_replay",
                    subject_kind="cold_replay",
                )
            )
        exported.append(
            {
                "replay_id": replay_id,
                "episode_id": row.get("episode_id"),
                "action_ids": sorted(row_action_ids),
                "replay_command": row.get("replay_command"),
                "receipt_ref": row.get("receipt_ref"),
                "pass_label": row.get("pass_label"),
                "body_in_receipt": False,
            }
        )
    missing_actions = sorted(action_ids - replayed)
    if missing_actions:
        findings.append(
            _bundle_finding(
                "COMPUTER_USE_COLD_REPLAY_COVERAGE_MISSING",
                "Every action must be covered by a cold-replay row.",
                subject_id=",".join(missing_actions),
                subject_kind="cold_replay",
            )
        )
    return {
        "findings": findings,
        "cold_replay_rows": sorted(exported, key=lambda item: item["replay_id"]),
        "cold_replay_count": len(rows),
        "cold_replay_pass_count": sum(
            1 for row in exported if row["pass_label"] in {"accepted", "blocked_recovered"}
        ),
    }


def _validate_computer_use_negative_cases(
    payloads: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)

    def record(case_id: str, code: str, message: str, subject_id: str) -> None:
        _record(
            findings,
            observed,
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind="computer_use_negative_case",
        )

    for row in _rows(payloads.get("live_account_action"), "actions"):
        if row.get("live_account_context") is True or row.get("live_account_action") is True:
            record(
                "live_account_action",
                "COMPUTER_USE_LIVE_ACCOUNT_ACTION_FORBIDDEN",
                "Live account context cannot be admitted as a public computer-use trace.",
                str(row.get("action_id") or "live_account_action"),
            )
    for row in _rows(payloads.get("credential_entry"), "actions"):
        if row.get("credential_entry_attempted") is True or "credential_value" in row:
            record(
                "credential_entry",
                "COMPUTER_USE_CREDENTIAL_ENTRY_FORBIDDEN",
                "Credential entry is outside the public replay authority ceiling.",
                str(row.get("action_id") or "credential_entry"),
            )
    for row in _rows(payloads.get("external_network_mutation"), "actions"):
        if row.get("external_network_mutation") is True:
            record(
                "external_network_mutation",
                "COMPUTER_USE_EXTERNAL_NETWORK_MUTATION_FORBIDDEN",
                "External network mutation cannot be treated as synthetic local replay.",
                str(row.get("action_id") or "external_network_mutation"),
            )
    for row in _rows(payloads.get("unapproved_purchase_or_send"), "actions"):
        if row.get("purchase_or_send_requested") is True and not row.get("human_approval_ref"):
            record(
                "unapproved_purchase_or_send",
                "COMPUTER_USE_UNAPPROVED_PURCHASE_OR_SEND",
                "Purchases and send actions require explicit human approval and remain outside the public fixture.",
                str(row.get("action_id") or "unapproved_purchase_or_send"),
            )
    for row in _rows(payloads.get("destructive_file_action"), "actions"):
        if row.get("destructive_action") is True and not row.get("human_review_ref"):
            record(
                "destructive_file_action",
                "COMPUTER_USE_DESTRUCTIVE_ACTION_WITHOUT_REVIEW",
                "Destructive host or file actions without review are rejected.",
                str(row.get("action_id") or "destructive_file_action"),
            )
    for row in _rows(payloads.get("hidden_screen_state_claim"), "observations"):
        if row.get("hidden_state_claim") is True or row.get("visible_state_hash") in (None, ""):
            record(
                "hidden_screen_state_claim",
                "COMPUTER_USE_HIDDEN_SCREEN_STATE_CLAIM",
                "A screen claim must be visible-state metadata, not hidden browser or desktop state.",
                str(row.get("observation_id") or "hidden_screen_state_claim"),
            )
    for row in _rows(payloads.get("action_without_observation"), "actions"):
        if not row.get("observation_ref") or not row.get("affordance_ref"):
            record(
                "action_without_observation",
                "COMPUTER_USE_ACTION_WITHOUT_OBSERVATION",
                "Actions are not admissible without a prior observation and affordance reference.",
                str(row.get("action_id") or "action_without_observation"),
            )
    for row in _rows(payloads.get("benchmark_score_claim"), "claims"):
        if row.get("benchmark_score_claim") is True:
            record(
                "benchmark_score_claim",
                "COMPUTER_USE_BENCHMARK_SCORE_CLAIM",
                "Synthetic replay receipts cannot claim benchmark performance.",
                str(row.get("claim_id") or "benchmark_score_claim"),
            )

    return {
        "findings": findings,
        "observed_negative_cases": {
            case_id: sorted(codes) for case_id, codes in sorted(observed.items())
        },
    }


def run_computer_use_action_trace_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    include_negative: bool | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    include_negative = (
        _has_computer_use_negative_inputs(input_path)
        if include_negative is None
        else include_negative
    )
    public_root = _public_root_for_path(input_path)
    payloads = _load_computer_use_action_trace_bundle(
        input_path,
        include_negative=include_negative,
    )
    scan_result = _scan_computer_use_action_trace_inputs(
        input_path,
        public_root,
        include_negative=include_negative,
    )

    projection = _validate_computer_use_projection_protocol(payloads.get("projection_protocol"))
    policy = _validate_computer_use_interaction_policy(payloads.get("interaction_policy"))
    episodes = _validate_computer_use_episodes(payloads.get("task_episodes"))
    observations = _validate_computer_use_observations(
        payloads.get("screen_observations"),
        episodes["episode_rows"],
    )
    actions = _validate_computer_use_actions(
        payloads.get("action_trace"),
        episodes["episode_rows"],
        observations["observation_rows"],
    )
    verdicts = _validate_computer_use_authority_verdicts(
        payloads.get("authority_verdicts"),
        actions["action_rows"],
    )
    transitions = _validate_computer_use_state_transitions(
        payloads.get("state_transition_receipts"),
        actions["action_rows"],
        verdicts["verdict_by_id"],
    )
    recoveries = _validate_computer_use_recovery_receipts(
        payloads.get("recovery_receipts"),
        actions["action_rows"],
        verdicts["verdict_by_id"],
    )
    cold_replay = _validate_computer_use_cold_replay(
        payloads.get("cold_replay"),
        actions["action_rows"],
    )
    negative_cases = (
        _validate_computer_use_negative_cases(payloads)
        if include_negative
        else {"findings": [], "observed_negative_cases": {}}
    )
    public_trace = build_public_computer_use_trace(input_path)

    expected_negative_cases = (
        COMPUTER_USE_EXPECTED_NEGATIVE_CASES if include_negative else {}
    )
    observed_negative_cases = negative_cases["observed_negative_cases"]
    missing_negative_cases = sorted(
        set(expected_negative_cases) - set(observed_negative_cases)
    )
    private_scan = dict(scan_result)
    private_scan.pop("forbidden_output_fields", None)
    private_scan.pop("body_redacted", None)
    private_scan.pop("redacted_output_field_labels_omitted", None)
    private_scan["omitted_output_fields"] = ["source_excerpt", "body"]
    private_scan["body_in_receipt"] = False
    private_scan["real_substrate_default"] = True
    private_scan["scan_purpose"] = (
        "credential_account_bound_and_operator_payload_exclusion"
    )
    private_scan["raw_screenshot_bodies_exported"] = False
    positive_findings = [
            *projection["findings"],
            *policy["findings"],
            *episodes["findings"],
            *observations["findings"],
            *actions["findings"],
            *verdicts["findings"],
            *transitions["findings"],
            *recoveries["findings"],
            *cold_replay["findings"],
            *public_trace["audit"]["findings"],
    ]
    all_findings = sorted(
        [
            *positive_findings,
            *negative_cases["findings"],
        ],
        key=lambda item: (
            str(item.get("negative_case_id") or ""),
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )
    error_codes = sorted({str(finding["error_code"]) for finding in all_findings})
    status = (
        PASS
        if not positive_findings
        and not missing_negative_cases
        and scan_result["status"] == PASS
        else "blocked"
    )
    bundle_fingerprint = _stable_hash(
        {
            name: payloads.get(name)
            for name in (
                "projection_protocol",
                "interaction_policy",
                "task_episodes",
                "screen_observations",
                "action_trace",
                "authority_verdicts",
                "state_transition_receipts",
                "recovery_receipts",
                "cold_replay",
            )
        }
    )
    out = Path(out_dir)
    if not out.is_absolute():
        out = Path.cwd() / out
    out.mkdir(parents=True, exist_ok=True)
    receipt_name = (
        COMPUTER_USE_FIXTURE_RESULT_NAME
        if include_negative
        else COMPUTER_USE_BUNDLE_RESULT_NAME
    )
    receipt_path = out / receipt_name
    public_receipt_path = public_relative_path(receipt_path, display_root=public_root)
    manifest = payloads.get("bundle_manifest")
    manifest = manifest if isinstance(manifest, dict) else {}
    payload = {
        "schema_version": (
            "computer_use_action_trace_replay_result_v1"
            if include_negative
            else "exported_computer_use_action_trace_bundle_validation_result_v1"
        ),
        "receipt_id": (
            "receipt.microcosm.computer_use_action_trace_replay"
            if include_negative
            else "receipt.microcosm.exported_computer_use_action_trace_bundle"
        ),
        "created_at": base_receipt(ORGAN_ID, FIXTURE_ID).get("created_at"),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": f"{FIXTURE_ID}.computer_use_action_trace_replay",
        "validator_id": VALIDATOR_ID,
        "input_mode": (
            "computer_use_action_trace_replay_fixture"
            if include_negative
            else "exported_computer_use_action_trace_bundle"
        ),
        "bundle_id": manifest.get("bundle_id", "computer_use_action_trace_replay"),
        "bundle_manifest_schema_version": manifest.get("schema_version"),
        "command": command,
        "source_pattern_ids": projection["source_pattern_ids"] or COMPUTER_USE_SOURCE_PATTERN_IDS,
        "source_refs": projection["source_refs"],
        "target_refs": projection["target_refs"],
        "body_import_verification": projection["body_import_verification"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "public_runtime_refs": [
            public_relative_path(path, display_root=public_root)
            for path in _computer_use_action_trace_paths(
                input_path,
                include_negative=include_negative,
            )
        ],
        "omitted_secret_or_live_access_material": projection[
            "omitted_secret_or_live_access_material"
        ],
        "interaction_policy_id": policy["policy_id"],
        "allowed_action_kinds": policy["allowed_action_kinds"],
        "episode_count": episodes["episode_count"],
        "observation_count": observations["observation_count"],
        "action_count": actions["action_count"],
        "action_kinds": actions["action_kinds"],
        "authority_verdict_count": verdicts["authority_verdict_count"],
        "allow_count": verdicts["allow_count"],
        "block_count": verdicts["block_count"],
        "review_count": verdicts["review_count"],
        "state_transition_count": transitions["state_transition_count"],
        "executed_transition_count": transitions["executed_transition_count"],
        "blocked_transition_count": transitions["blocked_transition_count"],
        "recovery_receipt_count": recoveries["recovery_receipt_count"],
        "recovered_action_count": recoveries["recovered_action_count"],
        "cold_replay_count": cold_replay["cold_replay_count"],
        "cold_replay_pass_count": cold_replay["cold_replay_pass_count"],
        "episode_rows": episodes["episode_rows"],
        "observation_rows": observations["observation_rows"],
        "action_rows": actions["action_rows"],
        "authority_verdict_rows": verdicts["authority_verdict_rows"],
        "state_transition_rows": transitions["state_transition_rows"],
        "recovery_rows": recoveries["recovery_rows"],
        "cold_replay_rows": cold_replay["cold_replay_rows"],
        "expected_negative_cases": expected_negative_cases,
        "observed_negative_cases": observed_negative_cases,
        "missing_negative_cases": missing_negative_cases,
        "error_codes": error_codes,
        "findings": all_findings,
        "secret_exclusion_scan": private_scan,
        "authority_ceiling": COMPUTER_USE_AUTHORITY_CEILING,
        "anti_claim": COMPUTER_USE_ANTI_CLAIM,
        "public_agent_execution_trace": public_trace,
        "bundle_fingerprint": bundle_fingerprint,
        "receipt_paths": [public_receipt_path],
    }
    write_json_atomic(receipt_path, payload)
    return payload


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
        [
            *route_compliance["findings"],
            *hook_shadow["findings"],
            *route_lease["findings"],
        ],
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
            "status": (
                PASS
                if not missing_cases
                and scan_result["status"] == PASS
                and hook_shadow["status"] == PASS
                else "blocked"
            ),
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
    computer_use_parser = subparsers.add_parser("validate-computer-use-bundle")
    computer_use_parser.add_argument("--input", required=True)
    computer_use_parser.add_argument("--out", required=True)
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
    elif args.action == "validate-computer-use-bundle":
        command = (
            "python -m microcosm_core.organs.agent_route_observability_runtime "
            f"validate-computer-use-bundle --input {args.input} --out {args.out}"
        )
        result = run_computer_use_action_trace_bundle(args.input, args.out, command=command)
    else:
        parser.error(
            "expected subcommand: run, validate-observability-bundle, or "
            "validate-computer-use-bundle"
        )
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
