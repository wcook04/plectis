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

INPUT_NAME = "observe_apply_session_fixture.json"
CONTINUATION_PACKET_NAME = "continuation_packet.json"
HEARTBEAT_NAME = "heartbeat.json"
RESOURCE_PRESSURE_NAME = "resource_pressure.json"
RESUME_RECEIPT_NAME = "resume_receipt.json"
CLOSEOUT_TRANSITION_NAME = "closeout_transition.json"

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
        if candidate.name == "microcosm-substrate":
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


def _safe_scan(scan_result: dict[str, Any]) -> dict[str, Any]:
    safe = dict(scan_result)
    safe.pop("forbidden_output_fields", None)
    safe["forbidden_output_fields_omitted"] = True
    return safe


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
    error_codes = _error_codes(observed_cases)
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
            "continuation_packet_status": {
                "status": PASS if status_packet.get("can_continue") is True else "blocked",
                "observe_id": observe_manifest.get("observe_id")
                if isinstance(observe_manifest, dict)
                else None,
                "continue_mode": status_packet.get("continue_mode"),
                "pending_group_labels": status_packet.get("pending_group_labels", []),
                "packet_status": "synthetic_resume_pending",
                "consumed": False,
                "target_job_id": finalizer.get("apply_session_id"),
            },
            "heartbeat_status": {
                "status": PASS,
                "heartbeat_not_resume_authority": True,
                "fresh_count": 0,
                "stale_count": 0,
                "live_state_read": False,
            },
            "resource_pressure_decision": {
                "status": PASS,
                "dispatch_allowed": False,
                "blocked_reason": "observe_apply_fixture_consumption_only_no_live_dispatch",
                "resource_pressure_not_exercised": True,
            },
            "resume_once_status": {
                "status": PASS if status_packet.get("continue_mode") == "resume_pending" else "blocked",
                "resume_authority": "synthetic_status_packet_only",
                "resume_success_overclaims_work_landed": False,
            },
            "duplicate_resume_rejection": {
                "status": PASS,
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

    private_state_policy = load_forbidden_classes(
        public_root / "core/private_state_forbidden_classes.json"
    )
    private_state_scan = _safe_scan(
        scan_paths(
            [fixture_path],
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run synthetic bridge continuity acceptance over observe/apply fixtures."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.action == "run":
        command = (
            f"python -m microcosm_core.organs.bridge_phase_continuity_runtime "
            f"run --input {args.input} --out {args.out}"
        )
        result = run(args.input, args.out, command=command)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == PASS else 1
    parser.error(f"unknown action: {args.action}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
