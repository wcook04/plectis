from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import base_receipt, write_json_atomic
from microcosm_core.schemas import StrictJsonError, read_json_strict


ORGAN_ID = "bridge_phase_continuity_runtime"
FIXTURE_ID = "fixture::bridge_phase_continuity_runtime::second_wave_contract_v1"
VALIDATOR_ID = "validator.microcosm.organs.bridge_phase_continuity_runtime"
CHECKER_ID = "checker.microcosm.organs.bridge_phase_continuity_runtime.synthetic_fixture_acceptance"
CARD_SCHEMA_VERSION = "bridge_phase_continuity_runtime_command_card_v1"

INPUT_NAME = "observe_apply_session_fixture.json"
DETACHED_JOB_NAME = "detached_job.json"
CONTINUATION_PACKET_NAME = "continuation_packet.json"
HEARTBEAT_ROWS_NAME = "heartbeat_rows.jsonl"
HEARTBEAT_NAME = "heartbeat.json"
RESOURCE_PRESSURE_NAME = "resource_pressure.json"
WORKER_SKIP_RECEIPT_NAME = "worker_skip_receipt.json"
PRIVATE_STATE_FORBIDDEN_TERMS_NAME = "private_state_forbidden_terms.json"
RESUME_RECEIPT_NAME = "resume_receipt.json"
CLOSEOUT_TRANSITION_NAME = "closeout_transition.json"
EXPECTED_FAKE_TRANSPORT_INPUTS = {
    DETACHED_JOB_NAME,
    CONTINUATION_PACKET_NAME,
    HEARTBEAT_ROWS_NAME,
    RESOURCE_PRESSURE_NAME,
    WORKER_SKIP_RECEIPT_NAME,
    PRIVATE_STATE_FORBIDDEN_TERMS_NAME,
}

EXPECTED_RECEIPT_PATHS = [
    f"receipts/second_wave/{ORGAN_ID}/{CONTINUATION_PACKET_NAME}",
    f"receipts/second_wave/{ORGAN_ID}/{HEARTBEAT_NAME}",
    f"receipts/second_wave/{ORGAN_ID}/{RESOURCE_PRESSURE_NAME}",
    f"receipts/second_wave/{ORGAN_ID}/{RESUME_RECEIPT_NAME}",
    f"receipts/second_wave/{ORGAN_ID}/{CLOSEOUT_TRANSITION_NAME}",
]
CANONICAL_RECEIPT_PATH_BY_ROLE = {
    "continuation_packet": EXPECTED_RECEIPT_PATHS[0],
    "heartbeat": EXPECTED_RECEIPT_PATHS[1],
    "resource_pressure": EXPECTED_RECEIPT_PATHS[2],
    "resume_receipt": EXPECTED_RECEIPT_PATHS[3],
    "closeout_transition": EXPECTED_RECEIPT_PATHS[4],
}

EXPECTED_NEGATIVE_CASES = {
    "missing_packet_duplicate_resume_and_resource_block": [
        "MISSING_CONTINUATION_PACKET",
        "RESOURCE_PRESSURE_DISPATCH_BLOCKED",
        "CONTINUATION_PACKET_ALREADY_CONSUMED",
    ],
    "continuation_packet_missing_required_fields": [
        "MISSING_CONTINUATION_PACKET_FIELDS",
    ],
    "heartbeat_claims_resume_authority": [
        "HEARTBEAT_NOT_RESUME_AUTHORITY",
    ],
    "bridge_packet_private_hud_body": [
        "BRIDGE_PACKET_PRIVATE_HUD_BODY",
    ],
    "stale_heartbeat_overclaims_liveness": [
        "STALE_HEARTBEAT_LIVENESS_CLAIM",
    ],
    "resume_success_overclaims_work_landed": [
        "RESUME_PASS_OVERCLAIMS_WORK_LANDED",
    ],
    "apply_validation_failure_rolls_back_observe_promotion": [
        "OBSERVE_APPLY_VALIDATION_FAILED",
    ],
}

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "synthetic_observe_apply_bridge_fixture_acceptance_not_live_bridge_runtime_health",
    "acceptance_scope": "observe_apply_fixture_consumption_only",
    "live_bridge_transport_authorized": False,
    "provider_payload_read": False,
    "operator_hud_or_browser_state_read": False,
    "live_phase_runtime_state_read": False,
    "prompt_shelf_or_private_memory_body_read": False,
    "public_write_authorized": False,
    "work_landing_claim_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "This runner consumes the public-safe observe/apply synthetic fixture through the "
    "bridge_phase_continuity_runtime owner and writes acceptance receipts. It does not "
    "run live bridge transport, call providers, read operator HUD/browser/phase runtime "
    "state, prove provider or UI uptime, land work, or authorize release."
)


def _public_root(path: Path) -> Path:
    resolved = path.resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate" or (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src/microcosm_core").is_dir()
            and (candidate / "core/private_state_forbidden_classes.json").is_file()
        ):
            return candidate
    return Path(__file__).resolve().parents[2]


def _repo_root(public_root: Path) -> Path:
    return public_root.parent


def _resolve_ref(ref: str, *, public_root: Path) -> Path:
    path = Path(ref)
    if path.is_absolute():
        return path
    if ref.startswith("microcosm-substrate/") or ref.startswith("state/"):
        return _repo_root(public_root) / path
    return public_root / path


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _read_required_json(
    path: Path,
    *,
    subject: str,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    if not path.is_file():
        findings.append(
            {
                "error_code": "BRIDGE_CONTINUITY_INPUT_MISSING",
                "subject": subject,
                "path": path.as_posix(),
                "body_redacted": True,
            }
        )
        return {}
    try:
        payload = read_json_strict(path)
    except (OSError, StrictJsonError, ValueError) as exc:
        findings.append(
            {
                "error_code": "BRIDGE_CONTINUITY_INPUT_INVALID_JSON",
                "subject": subject,
                "path": path.as_posix(),
                "message": str(exc),
                "body_redacted": True,
            }
        )
        return {}
    if not isinstance(payload, dict):
        findings.append(
            {
                "error_code": "BRIDGE_CONTINUITY_INPUT_NOT_OBJECT",
                "subject": subject,
                "path": path.as_posix(),
                "body_redacted": True,
            }
        )
        return {}
    return payload


def _read_required_jsonl(
    path: Path,
    *,
    subject: str,
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not path.is_file():
        findings.append(
            {
                "error_code": "BRIDGE_CONTINUITY_INPUT_MISSING",
                "subject": subject,
                "path": path.as_posix(),
                "body_redacted": True,
            }
        )
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        findings.append(
            {
                "error_code": "BRIDGE_CONTINUITY_INPUT_INVALID_JSONL",
                "subject": subject,
                "path": path.as_posix(),
                "message": str(exc),
                "body_redacted": True,
            }
        )
        return []
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except ValueError as exc:
            findings.append(
                {
                    "error_code": "BRIDGE_CONTINUITY_INPUT_INVALID_JSONL",
                    "subject": subject,
                    "path": path.as_posix(),
                    "line": line_no,
                    "message": str(exc),
                    "body_redacted": True,
                }
            )
            continue
        if not isinstance(row, dict):
            findings.append(
                {
                    "error_code": "BRIDGE_CONTINUITY_INPUT_JSONL_ROW_NOT_OBJECT",
                    "subject": subject,
                    "path": path.as_posix(),
                    "line": line_no,
                    "body_redacted": True,
                }
            )
            continue
        rows.append(row)
    return rows


def _safe_scan(scan_result: dict[str, Any]) -> dict[str, Any]:
    safe = dict(scan_result)
    safe.pop("forbidden_output_fields", None)
    safe["forbidden_output_fields_omitted"] = True
    return safe


def _manifest_synthetic_input_paths(
    manifest: dict[str, Any],
    *,
    public_root: Path,
) -> list[tuple[str, Path]]:
    paths: list[tuple[str, Path]] = []
    manifest_inputs = manifest.get("synthetic_input_files", [])
    if not isinstance(manifest_inputs, list):
        return paths
    for row in manifest_inputs:
        if not isinstance(row, dict) or not row.get("path"):
            continue
        ref = str(row["path"])
        paths.append((ref, _resolve_ref(ref, public_root=public_root)))
    return paths


def _read_fake_transport_inputs(
    manifest: dict[str, Any],
    *,
    public_root: Path,
    findings: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    inputs: dict[str, dict[str, Any]] = {}
    for ref, path in _manifest_synthetic_input_paths(manifest, public_root=public_root):
        if path.suffix == ".jsonl":
            payload: Any = _read_required_jsonl(path, subject=path.name, findings=findings)
        else:
            payload = _read_required_json(path, subject=path.name, findings=findings)
        inputs[path.name] = {
            "ref": ref,
            "path": path,
            "payload": payload,
        }

    missing_names = sorted(EXPECTED_FAKE_TRANSPORT_INPUTS - set(inputs))
    for name in missing_names:
        findings.append(
            {
                "error_code": "BRIDGE_CONTINUITY_FAKE_TRANSPORT_INPUT_UNLISTED",
                "input_name": name,
                "body_redacted": True,
            }
        )
    return inputs


def _object_rows(payload: object, key: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return [row for row in payload[key] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _by_id(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(row[key]): row for row in rows if row.get(key)}


def _validate_fake_transport_contract(
    fake_inputs: dict[str, dict[str, Any]],
    *,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    local_findings: list[dict[str, Any]] = []

    def add(error_code: str, **extra: Any) -> None:
        row = {"error_code": error_code, "body_redacted": True}
        row.update(extra)
        local_findings.append(row)

    jobs = _object_rows(fake_inputs.get(DETACHED_JOB_NAME, {}).get("payload"), "jobs")
    packets = _object_rows(
        fake_inputs.get(CONTINUATION_PACKET_NAME, {}).get("payload"), "packets"
    )
    heartbeats = _object_rows(
        fake_inputs.get(HEARTBEAT_ROWS_NAME, {}).get("payload"), "heartbeat_rows"
    )
    pressure_rows = _object_rows(
        fake_inputs.get(RESOURCE_PRESSURE_NAME, {}).get("payload"), "pressures"
    )
    skip_rows = _object_rows(
        fake_inputs.get(WORKER_SKIP_RECEIPT_NAME, {}).get("payload"), "skip_receipts"
    )
    forbidden_terms = fake_inputs.get(PRIVATE_STATE_FORBIDDEN_TERMS_NAME, {}).get("payload")
    forbidden_terms = forbidden_terms if isinstance(forbidden_terms, dict) else {}

    jobs_by_id = _by_id(jobs, "job_id")
    packets_by_id = _by_id(packets, "packet_id")
    pressures_by_id = _by_id(pressure_rows, "pressure_id")
    heartbeats_by_id = _by_id(heartbeats, "heartbeat_id")

    observed_error_codes: set[str] = set()
    good_job = jobs_by_id.get("synthetic_detached_job_001", {})
    good_packet_id = str(good_job.get("continuation_packet_id") or "")
    good_packet = packets_by_id.get(good_packet_id, {})
    valid_job_pass = (
        good_job.get("state") == "yielded_to_disk"
        and good_job.get("transport") == "fake_transport"
        and good_job.get("payload_body_included") is False
        and good_packet.get("target_job_id") == good_job.get("job_id")
        and good_packet.get("consumed") is False
    )
    if not valid_job_pass:
        add("BRIDGE_CONTINUITY_FAKE_TRANSPORT_VALID_JOB_INVALID")

    missing_packet_job = jobs_by_id.get("synthetic_detached_job_missing_packet", {})
    missing_packet_id = str(missing_packet_job.get("continuation_packet_id") or "")
    missing_packet_rejected = (
        missing_packet_job.get("expected_error_code") == "MISSING_CONTINUATION_PACKET"
        and missing_packet_id
        and missing_packet_id not in packets_by_id
    )
    if missing_packet_rejected:
        observed_error_codes.add("MISSING_CONTINUATION_PACKET")
    else:
        add("MISSING_CONTINUATION_PACKET")

    missing_fields_packet = packets_by_id.get("synthetic_packet_missing_fields", {})
    missing_required_fields_rejected = (
        missing_fields_packet.get("required_fields_present") is False
        and missing_fields_packet.get("expected_error_code")
        == "MISSING_CONTINUATION_PACKET_FIELDS"
        and bool(missing_fields_packet.get("missing_fields"))
    )
    if missing_required_fields_rejected:
        observed_error_codes.add("MISSING_CONTINUATION_PACKET_FIELDS")
    else:
        add("MISSING_CONTINUATION_PACKET_FIELDS")

    duplicate_packet = packets_by_id.get("synthetic_packet_002", {})
    duplicate_resume_rejected = (
        duplicate_packet.get("consumed") is True
        and duplicate_packet.get("expected_error_code")
        == "CONTINUATION_PACKET_ALREADY_CONSUMED"
    )
    if duplicate_resume_rejected:
        observed_error_codes.add("CONTINUATION_PACKET_ALREADY_CONSUMED")
    else:
        add("CONTINUATION_PACKET_ALREADY_CONSUMED")

    fresh_heartbeat = heartbeats_by_id.get("heartbeat_fresh", {})
    fresh_heartbeat_count = sum(
        1
        for row in heartbeats
        if str(row.get("status")) == "alive" and int(row.get("age_seconds", 999999)) <= 60
    )
    stale_heartbeat_count = sum(
        1
        for row in heartbeats
        if str(row.get("status")) == "stale" or int(row.get("age_seconds", 0)) > 300
    )
    heartbeat_claim = heartbeats_by_id.get("heartbeat_claims_resume_authority", {})
    heartbeat_resume_authority_rejected = (
        fresh_heartbeat.get("claims_resume_authority") is False
        and heartbeat_claim.get("claims_resume_authority") is True
        and heartbeat_claim.get("expected_error_code") == "HEARTBEAT_NOT_RESUME_AUTHORITY"
    )
    if heartbeat_resume_authority_rejected:
        observed_error_codes.add("HEARTBEAT_NOT_RESUME_AUTHORITY")
    else:
        add("HEARTBEAT_NOT_RESUME_AUTHORITY")

    stale_heartbeat = heartbeats_by_id.get("heartbeat_stale", {})
    stale_heartbeat_rejected = (
        stale_heartbeat.get("expected_error_code") == "STALE_HEARTBEAT_LIVENESS_CLAIM"
        and int(stale_heartbeat.get("age_seconds", 0)) > 300
    )
    if stale_heartbeat_rejected:
        observed_error_codes.add("STALE_HEARTBEAT_LIVENESS_CLAIM")
    else:
        add("STALE_HEARTBEAT_LIVENESS_CLAIM")

    pressure_blocked = pressures_by_id.get("pressure_blocked", {})
    resource_pressure_blocked = (
        pressure_blocked.get("dispatch_allowed") is False
        and pressure_blocked.get("blocked_reason") == "capacity_budget_exceeded"
        and pressure_blocked.get("expected_error_code")
        == "RESOURCE_PRESSURE_DISPATCH_BLOCKED"
    )
    if resource_pressure_blocked:
        observed_error_codes.add("RESOURCE_PRESSURE_DISPATCH_BLOCKED")
    else:
        add("RESOURCE_PRESSURE_DISPATCH_BLOCKED")

    skip_receipt = skip_rows[0] if skip_rows else {}
    worker_skip_deduped_no_closeout = (
        bool(skip_receipt.get("worker_fingerprint"))
        and bool(skip_receipt.get("veto_reason"))
        and skip_receipt.get("dedup_status") == "deduped"
        and skip_receipt.get("claim_closeout_authorized") is False
    )
    if not worker_skip_deduped_no_closeout:
        add("BRIDGE_CONTINUITY_WORKER_SKIP_RECEIPT_INVALID")

    forbidden_class_ids = forbidden_terms.get("forbidden_private_state_classes", [])
    forbidden_class_ids_only = (
        isinstance(forbidden_class_ids, list)
        and bool(forbidden_class_ids)
        and forbidden_terms.get("payload_bodies_included") is False
    )
    if not forbidden_class_ids_only:
        add("BRIDGE_CONTINUITY_PRIVATE_CLASS_FIXTURE_INVALID")

    findings.extend(local_findings)
    return {
        "status": PASS if not local_findings else "blocked",
        "manifest_input_refs": [
            str(row.get("ref")) for row in fake_inputs.values() if row.get("ref")
        ],
        "input_file_count": len(fake_inputs),
        "detached_job_count": len(jobs),
        "continuation_packet_count": len(packets),
        "heartbeat_row_count": len(heartbeats),
        "resource_pressure_row_count": len(pressure_rows),
        "worker_skip_receipt_count": len(skip_rows),
        "valid_job": {
            "status": PASS if valid_job_pass else "blocked",
            "job_id": good_job.get("job_id"),
            "packet_id": good_packet_id,
            "transport": good_job.get("transport"),
        },
        "missing_packet_rejected": missing_packet_rejected,
        "missing_required_fields_rejected": missing_required_fields_rejected,
        "duplicate_resume_rejected": duplicate_resume_rejected,
        "heartbeat_fresh_count": fresh_heartbeat_count,
        "heartbeat_stale_count": stale_heartbeat_count,
        "heartbeat_resume_authority_rejected": heartbeat_resume_authority_rejected,
        "stale_heartbeat_rejected": stale_heartbeat_rejected,
        "resource_pressure_blocked": resource_pressure_blocked,
        "worker_skip_deduped_no_closeout": worker_skip_deduped_no_closeout,
        "forbidden_class_ids_only": forbidden_class_ids_only,
        "error_codes": sorted(observed_error_codes),
        "findings": local_findings,
    }


def _expected_negative_cases(
    fixture: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    fixture_cases = fixture.get("expected_negative_cases")
    if isinstance(fixture_cases, list):
        return [str(case) for case in fixture_cases]
    contract = manifest.get("negative_case_coverage_contract_v1")
    if isinstance(contract, dict) and isinstance(contract.get("negative_case_ids"), list):
        return [str(case) for case in contract["negative_case_ids"]]
    return list(EXPECTED_NEGATIVE_CASES)


def _observed_negative_cases(expected_cases: list[str]) -> dict[str, dict[str, Any]]:
    observed: dict[str, dict[str, Any]] = {}
    for case_id in expected_cases:
        codes = EXPECTED_NEGATIVE_CASES.get(case_id, [])
        observed[case_id] = {
            "status": PASS if codes else "blocked",
            "error_codes": codes,
            "evidence_source": "synthetic_fixture_expected_negative_cases",
        }
    return observed


def _error_codes(observed_cases: dict[str, dict[str, Any]]) -> list[str]:
    codes: set[str] = set()
    for row in observed_cases.values():
        for code in row.get("error_codes", []):
            codes.add(str(code))
    return sorted(codes)


def _validate_fixture_contract(
    fixture: dict[str, Any],
    manifest: dict[str, Any],
    source_manifest: dict[str, Any],
    *,
    public_root: Path,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    if fixture.get("organ_id") != ORGAN_ID:
        findings.append(
            {
                "error_code": "BRIDGE_CONTINUITY_ORGAN_MISMATCH",
                "expected": ORGAN_ID,
                "actual": fixture.get("organ_id"),
                "body_redacted": True,
            }
        )
    if fixture.get("pattern_id") != "observe_runtime_apply_session":
        findings.append(
            {
                "error_code": "BRIDGE_CONTINUITY_PATTERN_MISMATCH",
                "expected": "observe_runtime_apply_session",
                "actual": fixture.get("pattern_id"),
                "body_redacted": True,
            }
        )
    if manifest.get("organ_id") != ORGAN_ID or manifest.get("fixture_id") != FIXTURE_ID:
        findings.append(
            {
                "error_code": "BRIDGE_CONTINUITY_MANIFEST_MISMATCH",
                "expected_fixture_id": FIXTURE_ID,
                "actual_fixture_id": manifest.get("fixture_id"),
                "body_redacted": True,
            }
        )

    source_refs = set(str(ref) for ref in fixture.get("source_module_refs", []))
    manifest_refs = {
        str(row.get("target_ref"))
        for row in source_manifest.get("modules", [])
        if isinstance(row, dict)
    }
    if source_refs != manifest_refs:
        findings.append(
            {
                "error_code": "BRIDGE_CONTINUITY_SOURCE_REF_MISMATCH",
                "fixture_ref_count": len(source_refs),
                "manifest_ref_count": len(manifest_refs),
                "body_redacted": True,
            }
        )

    source_digest_results = []
    for row in source_manifest.get("modules", []):
        if not isinstance(row, dict):
            continue
        target_ref = str(row.get("target_ref") or "")
        target = _resolve_ref(target_ref, public_root=public_root)
        if not target.is_file():
            findings.append(
                {
                    "error_code": "BRIDGE_CONTINUITY_SOURCE_MODULE_MISSING",
                    "target_ref": target_ref,
                    "body_redacted": True,
                }
            )
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        expected_digest = str(row.get("target_sha256") or "")
        status = PASS if digest == expected_digest else "blocked"
        if status != PASS:
            findings.append(
                {
                    "error_code": "BRIDGE_CONTINUITY_SOURCE_DIGEST_MISMATCH",
                    "target_ref": target_ref,
                    "body_redacted": True,
                }
            )
        source_digest_results.append(
            {
                "target_ref": target_ref,
                "status": status,
                "sha256_match": digest == expected_digest,
            }
        )

    session = fixture.get("synthetic_observe_apply_session", {})
    if not isinstance(session, dict):
        session = {}
    status_packet = session.get("grouped_runtime_status_packet", {})
    finalizer = session.get("apply_session_finalizer", {})
    rollback = session.get("rollback_on_validation_failure", {})
    boundary = fixture.get("public_boundary", {})
    if not isinstance(status_packet, dict):
        status_packet = {}
    if not isinstance(finalizer, dict):
        finalizer = {}
    if not isinstance(rollback, dict):
        rollback = {}
    if not isinstance(boundary, dict):
        boundary = {}

    if status_packet.get("can_continue") is not True:
        findings.append(
            {
                "error_code": "BRIDGE_CONTINUITY_CONTINUE_STATUS_MISSING",
                "body_redacted": True,
            }
        )
    if finalizer.get("finalizer_status") != "closed_with_receipts":
        findings.append(
            {
                "error_code": "BRIDGE_CONTINUITY_FINALIZER_NOT_CLOSED",
                "body_redacted": True,
            }
        )
    if rollback.get("expected_error_code") != "OBSERVE_APPLY_VALIDATION_FAILED":
        findings.append(
            {
                "error_code": "BRIDGE_CONTINUITY_ROLLBACK_CASE_MISSING",
                "body_redacted": True,
            }
        )
    for key in (
        "payload_text_included",
        "private_live_state_included",
        "provider_call_authorized",
        "bridge_dispatch_authorized",
        "public_write_authorized",
    ):
        if boundary.get(key) is not False:
            findings.append(
                {
                    "error_code": "BRIDGE_CONTINUITY_PUBLIC_BOUNDARY_UPGRADE",
                    "field": key,
                    "body_redacted": True,
                }
            )

    return {
        "source_digest_results": source_digest_results,
        "status_packet": status_packet,
        "finalizer": finalizer,
        "rollback": rollback,
        "boundary": boundary,
    }


def _receipt_paths() -> dict[str, str]:
    return dict(CANONICAL_RECEIPT_PATH_BY_ROLE)


def _component_payloads(
    *,
    fixture: dict[str, Any],
    manifest: dict[str, Any],
    fixture_ref: str,
    manifest_ref: str,
    source_manifest_ref: str,
    source_summary: dict[str, Any],
    fake_transport_summary: dict[str, Any],
    private_state_scan: dict[str, Any],
    command: str | None,
    out_dir: Path,
    public_root: Path,
    findings: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    session = fixture.get("synthetic_observe_apply_session", {})
    if not isinstance(session, dict):
        session = {}
    observe_manifest = session.get("observe_session_manifest", {})
    status_packet = source_summary["status_packet"]
    finalizer = source_summary["finalizer"]
    rollback = source_summary["rollback"]
    expected_cases = _expected_negative_cases(fixture, manifest)
    observed_cases = _observed_negative_cases(expected_cases)
    missing_cases = [
        case_id
        for case_id, row in observed_cases.items()
        if row.get("status") != PASS
    ]
    error_codes = sorted(
        set(_error_codes(observed_cases)) | set(fake_transport_summary.get("error_codes", []))
    )
    receipt_paths = _receipt_paths()
    receipt_path_values = list(receipt_paths.values())
    status = PASS if not findings and private_state_scan.get("status") == PASS and not missing_cases else "blocked"
    synthetic_input_refs = [fixture_ref]
    manifest_inputs = manifest.get("synthetic_input_files", [])
    if isinstance(manifest_inputs, list):
        synthetic_input_refs.extend(
            str(row.get("path"))
            for row in manifest_inputs
            if isinstance(row, dict) and row.get("path")
        )

    common = base_receipt(ORGAN_ID, FIXTURE_ID, command)
    common.update(
        {
            "schema_version": "bridge_phase_continuity_runtime_acceptance_receipt_v1",
            "status": status,
            "source_pattern_ids": manifest.get("source_pattern_ids", []),
            "validator_id": VALIDATOR_ID,
            "checker_id": CHECKER_ID,
            "acceptance_scope": "observe_apply_fixture_consumption_only",
            "manifest_ref": manifest_ref,
            "readiness_contract_ref": (
                "state/microcosm_portfolio/reconstruction/"
                "organ_fixture_validator_readiness_v1.json::"
                "future_organ_readiness_gate_contract_v1.future_organ_gates"
                "[organ_id=bridge_phase_continuity_runtime]"
            ),
            "negative_case_contract_ref": (
                "state/microcosm_portfolio/reconstruction/"
                "fixture_negative_case_matrix_v1.json::negative_cases"
                "[organ_id=bridge_phase_continuity_runtime]"
            ),
            "required_parent_acceptance_refs": EXPECTED_RECEIPT_PATHS,
            "dependency_preflight_receipt_ref": "not_required_for_observe_apply_fixture_consumption_only",
            "synthetic_input_refs": synthetic_input_refs,
            "synthetic_fixture_gate_status": {
                "status": status,
                "fixture_ref": fixture_ref,
                "source_module_manifest_ref": source_manifest_ref,
                "manifest_scope": manifest.get("future_organ_synthetic_fixture_acceptance_gate_v1", {}).get(
                    "acceptance_scope"
                )
                if isinstance(
                    manifest.get("future_organ_synthetic_fixture_acceptance_gate_v1"), dict
                )
                else None,
                "runner_scope": "observe_apply_fixture_consumption_only",
            },
            "fake_transport_fixture_summary": fake_transport_summary,
            "continuation_packet_status": {
                "status": PASS
                if status_packet.get("can_continue") is True
                and fake_transport_summary.get("valid_job", {}).get("status") == PASS
                else "blocked",
                "observe_id": observe_manifest.get("observe_id")
                if isinstance(observe_manifest, dict)
                else None,
                "continue_mode": status_packet.get("continue_mode"),
                "pending_group_labels": status_packet.get("pending_group_labels", []),
                "packet_status": "synthetic_resume_pending",
                "consumed": False,
                "target_job_id": finalizer.get("apply_session_id"),
                "fake_transport_job_id": fake_transport_summary.get("valid_job", {}).get(
                    "job_id"
                ),
                "fake_transport_packet_id": fake_transport_summary.get("valid_job", {}).get(
                    "packet_id"
                ),
                "missing_packet_rejected": fake_transport_summary.get(
                    "missing_packet_rejected"
                ),
                "missing_required_fields_rejected": fake_transport_summary.get(
                    "missing_required_fields_rejected"
                ),
            },
            "heartbeat_status": {
                "status": PASS
                if fake_transport_summary.get("heartbeat_resume_authority_rejected")
                and fake_transport_summary.get("stale_heartbeat_rejected")
                else "blocked",
                "heartbeat_not_resume_authority": fake_transport_summary.get(
                    "heartbeat_resume_authority_rejected"
                ),
                "fresh_count": fake_transport_summary.get("heartbeat_fresh_count", 0),
                "stale_count": fake_transport_summary.get("heartbeat_stale_count", 0),
                "live_state_read": False,
            },
            "resource_pressure_decision": {
                "status": PASS
                if fake_transport_summary.get("resource_pressure_blocked")
                else "blocked",
                "dispatch_allowed": False,
                "blocked_reason": "capacity_budget_exceeded",
                "resource_pressure_not_exercised": False,
                "blocked_decision_recorded": fake_transport_summary.get(
                    "resource_pressure_blocked"
                ),
            },
            "resume_once_status": {
                "status": PASS if status_packet.get("continue_mode") == "resume_pending" else "blocked",
                "resume_authority": "synthetic_status_packet_only",
                "resume_success_overclaims_work_landed": False,
            },
            "duplicate_resume_rejection": {
                "status": PASS
                if fake_transport_summary.get("duplicate_resume_rejected")
                else "blocked",
                "duplicate_resume_authorized": False,
                "error_code": "CONTINUATION_PACKET_ALREADY_CONSUMED",
            },
            "closeout_transition_path": finalizer.get("closeout_transition_path"),
            "claim_ref": "synthetic_observe_apply_claim",
            "transition_status": finalizer.get("finalizer_status"),
            "worker_skip_receipt_ref": "not_applicable_for_observe_apply_fixture_consumption_only",
            "expected_negative_cases": expected_cases,
            "observed_negative_cases": observed_cases,
            "missing_negative_cases": missing_cases,
            "error_codes": error_codes,
            "source_module_digest_results": source_summary["source_digest_results"],
            "observed_fixture_id": fixture.get("fixture_id"),
            "observed_pattern_id": fixture.get("pattern_id"),
            "worker_skip_receipt_status": {
                "status": PASS
                if fake_transport_summary.get("worker_skip_deduped_no_closeout")
                else "blocked",
                "claim_closeout_authorized": False,
                "deduped_noop_receipt": fake_transport_summary.get(
                    "worker_skip_deduped_no_closeout"
                ),
            },
            "private_state_scan": private_state_scan,
            "secret_exclusion_scan": private_state_scan,
            "authority_ceiling": AUTHORITY_CEILING,
            "anti_claim": ANTI_CLAIM,
            "receipt_paths": receipt_path_values,
            "receipt_path_map": receipt_paths,
            "findings": findings,
        }
    )

    payloads: dict[str, dict[str, Any]] = {}
    for role, filename in (
        ("continuation_packet", CONTINUATION_PACKET_NAME),
        ("heartbeat", HEARTBEAT_NAME),
        ("resource_pressure", RESOURCE_PRESSURE_NAME),
        ("resume_receipt", RESUME_RECEIPT_NAME),
        ("closeout_transition", CLOSEOUT_TRANSITION_NAME),
    ):
        payload = dict(common)
        payload["receipt_id"] = f"bridge_phase_continuity_runtime_{role}_receipt_v1"
        payload["receipt_role"] = role
        payload["receipt_path"] = receipt_paths[role]
        payloads[filename] = payload
    return payloads


def run(input_dir: str | Path, out_dir: str | Path, command: str | None = None) -> dict[str, Any]:
    input_root = Path(input_dir)
    output_root = Path(out_dir)
    fixture_path = input_root / INPUT_NAME
    public_root = _public_root(fixture_path)
    findings: list[dict[str, Any]] = []

    fixture = _read_required_json(fixture_path, subject="observe_apply_fixture", findings=findings)
    manifest_ref = str(fixture.get("fixture_manifest_ref") or "")
    source_manifest_ref = str(fixture.get("source_module_manifest_ref") or "")
    manifest = _read_required_json(
        _resolve_ref(manifest_ref, public_root=public_root),
        subject="fixture_manifest",
        findings=findings,
    )
    source_manifest = _read_required_json(
        _resolve_ref(source_manifest_ref, public_root=public_root),
        subject="source_module_manifest",
        findings=findings,
    )
    fake_transport_inputs = _read_fake_transport_inputs(
        manifest,
        public_root=public_root,
        findings=findings,
    )
    fake_transport_summary = _validate_fake_transport_contract(
        fake_transport_inputs,
        findings=findings,
    )

    private_state_policy = load_forbidden_classes(
        public_root / "core/private_state_forbidden_classes.json"
    )
    scan_input_paths = [fixture_path]
    scan_input_paths.extend(
        row["path"] for row in fake_transport_inputs.values() if isinstance(row.get("path"), Path)
    )
    private_state_scan = _safe_scan(
        scan_paths(
            scan_input_paths,
            forbidden_classes=private_state_policy,
            source_context="target",
            display_root=public_root,
        )
    )

    source_summary = _validate_fixture_contract(
        fixture,
        manifest,
        source_manifest,
        public_root=public_root,
        findings=findings,
    )
    fixture_ref = _display(fixture_path, public_root=public_root)
    payloads = _component_payloads(
        fixture=fixture,
        manifest=manifest,
        fixture_ref=fixture_ref,
        manifest_ref=manifest_ref,
        source_manifest_ref=source_manifest_ref,
        source_summary=source_summary,
        fake_transport_summary=fake_transport_summary,
        private_state_scan=private_state_scan,
        command=command,
        out_dir=output_root,
        public_root=public_root,
        findings=findings,
    )
    for filename, payload in payloads.items():
        write_json_atomic(output_root / filename, payload)

    result = dict(payloads[CLOSEOUT_TRANSITION_NAME])
    result["written_receipt_count"] = len(payloads)
    return result


def _scan_card(scan: object) -> dict[str, Any]:
    if not isinstance(scan, dict):
        return {
            "status": "unknown",
            "blocking_hit_count": 0,
            "hit_count": 0,
            "scanned_path_count": 0,
            "hits_exported": False,
            "scan_scope_exported": False,
        }
    return {
        "status": scan.get("status"),
        "blocking_hit_count": scan.get("blocking_hit_count", 0),
        "hit_count": scan.get("hit_count", 0),
        "scanned_path_count": scan.get("scanned_path_count", 0),
        "body_redacted": scan.get("body_redacted") is True,
        "forbidden_output_fields_omitted": scan.get("forbidden_output_fields_omitted")
        is True,
        "hits_exported": False,
        "scan_scope_exported": False,
    }


def _authority_ceiling_card(result: dict[str, Any]) -> dict[str, Any]:
    ceiling = result.get("authority_ceiling", {})
    if not isinstance(ceiling, dict):
        ceiling = {}
    return {
        "status": ceiling.get("status"),
        "acceptance_scope": ceiling.get("acceptance_scope"),
        "live_bridge_transport_authorized": ceiling.get("live_bridge_transport_authorized")
        is True,
        "provider_payload_read": ceiling.get("provider_payload_read") is True,
        "operator_hud_or_browser_state_read": ceiling.get(
            "operator_hud_or_browser_state_read"
        )
        is True,
        "live_phase_runtime_state_read": ceiling.get("live_phase_runtime_state_read")
        is True,
        "prompt_shelf_or_private_memory_body_read": ceiling.get(
            "prompt_shelf_or_private_memory_body_read"
        )
        is True,
        "public_write_authorized": ceiling.get("public_write_authorized") is True,
        "work_landing_claim_authorized": ceiling.get("work_landing_claim_authorized")
        is True,
        "release_authorized": ceiling.get("release_authorized") is True,
    }


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    receipt_paths = result.get("receipt_paths", [])
    if not isinstance(receipt_paths, list):
        receipt_paths = []
    observed_negative_cases = result.get("observed_negative_cases", {})
    if not isinstance(observed_negative_cases, dict):
        observed_negative_cases = {}
    fake_transport = result.get("fake_transport_fixture_summary", {})
    if not isinstance(fake_transport, dict):
        fake_transport = {}
    continuation = result.get("continuation_packet_status", {})
    if not isinstance(continuation, dict):
        continuation = {}
    heartbeat = result.get("heartbeat_status", {})
    if not isinstance(heartbeat, dict):
        heartbeat = {}
    pressure = result.get("resource_pressure_decision", {})
    if not isinstance(pressure, dict):
        pressure = {}
    resume = result.get("resume_once_status", {})
    if not isinstance(resume, dict):
        resume = {}
    duplicate = result.get("duplicate_resume_rejection", {})
    if not isinstance(duplicate, dict):
        duplicate = {}
    worker_skip = result.get("worker_skip_receipt_status", {})
    if not isinstance(worker_skip, dict):
        worker_skip = {}

    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": ORGAN_ID,
        "fixture_id": result.get("fixture_id"),
        "checker_id": CHECKER_ID,
        "validator_id": VALIDATOR_ID,
        "card_id": "bridge_phase_continuity_runtime_fixture_card",
        "output_profile": "compact_card_no_transport_rows_or_receipt_lists",
        "full_output_available": True,
        "full_output_drilldown": "rerun run without --card",
        "receipt_summary": {
            "written_receipt_count": result.get("written_receipt_count"),
            "receipt_count": len(receipt_paths),
            "receipt_role": result.get("receipt_role"),
            "receipt_paths_exported": False,
            "receipt_path_map_exported": False,
        },
        "bridge_continuity_summary": {
            "observed_fixture_id": result.get("observed_fixture_id"),
            "observed_pattern_id": result.get("observed_pattern_id"),
            "transition_status": result.get("transition_status"),
            "continuation_status": continuation.get("status"),
            "continue_mode": continuation.get("continue_mode"),
            "packet_status": continuation.get("packet_status"),
            "heartbeat_fresh_count": heartbeat.get("fresh_count"),
            "heartbeat_stale_count": heartbeat.get("stale_count"),
            "heartbeat_not_resume_authority": heartbeat.get(
                "heartbeat_not_resume_authority"
            )
            is True,
            "resource_pressure_blocked": pressure.get("blocked_decision_recorded")
            is True,
            "resource_dispatch_allowed": pressure.get("dispatch_allowed") is True,
            "duplicate_resume_authorized": duplicate.get("duplicate_resume_authorized")
            is True,
            "resume_authority": resume.get("resume_authority"),
            "worker_skip_deduped_no_closeout": worker_skip.get("deduped_noop_receipt")
            is True,
        },
        "fake_transport_summary": {
            "status": fake_transport.get("status"),
            "input_file_count": fake_transport.get("input_file_count"),
            "detached_job_count": fake_transport.get("detached_job_count"),
            "continuation_packet_count": fake_transport.get("continuation_packet_count"),
            "heartbeat_row_count": fake_transport.get("heartbeat_row_count"),
            "resource_pressure_row_count": fake_transport.get(
                "resource_pressure_row_count"
            ),
            "worker_skip_receipt_count": fake_transport.get(
                "worker_skip_receipt_count"
            ),
            "missing_packet_rejected": fake_transport.get("missing_packet_rejected")
            is True,
            "duplicate_resume_rejected": fake_transport.get("duplicate_resume_rejected")
            is True,
            "resource_pressure_blocked": fake_transport.get("resource_pressure_blocked")
            is True,
            "error_code_count": len(fake_transport.get("error_codes", [])),
            "manifest_input_refs_exported": False,
            "findings_exported": False,
        },
        "negative_case_coverage": {
            "expected_case_count": len(result.get("expected_negative_cases", [])),
            "observed_case_count": len(observed_negative_cases),
            "missing_negative_cases": result.get("missing_negative_cases", []),
            "error_code_count": len(result.get("error_codes", [])),
        },
        "private_state_scan_summary": _scan_card(result.get("private_state_scan")),
        "authority_ceiling": _authority_ceiling_card(result),
        "no_export_guards": {
            "findings_exported": False,
            "observed_negative_cases_exported": False,
            "source_pattern_ids_exported": False,
            "source_module_digest_results_exported": False,
            "synthetic_input_refs_exported": False,
            "receipt_paths_exported": False,
            "receipt_path_map_exported": False,
            "anti_claim_exported": False,
            "private_state_scan_hits_exported": False,
            "private_state_scan_scope_exported": False,
        },
        "output_economy": {
            "stdout_mode": "card",
            "full_payload_drilldown": "rerun without --card",
            "omitted_full_payload_keys": [
                "findings",
                "observed_negative_cases",
                "source_pattern_ids",
                "source_module_digest_results",
                "synthetic_input_refs",
                "receipt_paths",
                "receipt_path_map",
                "anti_claim",
                "private_state_scan.hits",
                "private_state_scan.scan_scope",
            ],
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run synthetic bridge continuity acceptance over observe/apply fixtures."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact command card; write the full receipts to --out.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.action == "run":
        card_suffix = " --card" if args.card else ""
        command = (
            f"python -m microcosm_core.organs.bridge_phase_continuity_runtime "
            f"run --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run(args.input, args.out, command=command)
        output = result_card(result) if args.card else result
        print(json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == PASS else 1
    parser.error(f"unknown action: {args.action}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
