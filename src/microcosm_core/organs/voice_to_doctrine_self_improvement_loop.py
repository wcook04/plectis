from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)


ORGAN_ID = "voice_to_doctrine_self_improvement_loop"
FIXTURE_ID = "first_wave.voice_to_doctrine_self_improvement_loop"
VALIDATOR_ID = "validator.microcosm.organs.voice_to_doctrine_self_improvement_loop"
MODULE_PATH = "microcosm_core.organs.voice_to_doctrine_self_improvement_loop"
CARD_SCHEMA_VERSION = "voice_to_doctrine_self_improvement_command_card_v1"

RESULT_NAME = "voice_to_doctrine_self_improvement_loop_result.json"
BOARD_NAME = "voice_to_doctrine_self_improvement_loop_board.json"
VALIDATION_RECEIPT_NAME = (
    "voice_to_doctrine_self_improvement_loop_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "voice_to_doctrine_self_improvement_loop_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_voice_to_doctrine_bundle_validation_result.json"

INPUT_NAMES = (
    "projection_protocol.json",
    "propagation_policy.json",
    "owner_surfaces.json",
    "local_lessons.json",
)
NEGATIVE_INPUT_NAMES = (
    "raw_operator_voice_export.json",
    "doctrine_node_hand_edit.json",
    "consume_without_deposit.json",
    "pattern_receipt_only_progress.json",
    "global_promotion_without_owner_validation.json",
    "private_thread_body_export.json",
)

EXPECTED_NEGATIVE_CASES = {
    "raw_operator_voice_export": ["VOICE_DOCTRINE_RAW_OPERATOR_BODY_FORBIDDEN"],
    "doctrine_node_hand_edit": ["VOICE_DOCTRINE_DIRECT_NODE_EDIT_FORBIDDEN"],
    "consume_without_deposit": ["VOICE_DOCTRINE_CONSUME_WITHOUT_DEPOSIT"],
    "pattern_receipt_only_progress": ["VOICE_DOCTRINE_RECEIPT_ONLY_PROGRESS"],
    "global_promotion_without_owner_validation": [
        "VOICE_DOCTRINE_GLOBAL_PROMOTION_WITHOUT_OWNER_VALIDATION"
    ],
    "private_thread_body_export": ["VOICE_DOCTRINE_PRIVATE_THREAD_BODY_FORBIDDEN"],
}

REQUIRED_PATTERN_REFS = {
    "recursive_self_improvement_operating_loop",
    "doctrine_population_loop",
    "local_to_general_propagation",
}
REQUIRED_SEQUENCE = (
    "sense_local_pressure",
    "classify_pressure_shape",
    "select_owner_surface",
    "mutate_or_capture_owner",
    "validate_owner_result",
    "bind_closeout",
    "publish_reentry_condition",
)
REQUIRED_LESSON_FIELDS = (
    "lesson_id",
    "input_signal_class",
    "macro_pattern_refs",
    "selected_owner_surface_id",
    "owner_action",
    "status",
    "evidence_refs",
    "validation_ref",
    "closeout_ref",
)
FORBIDDEN_KEYS = (
    "raw_operator_voice",
    "operator_voice_body",
    "private_thread_body",
    "provider_payload",
    "credential_value",
    "secret_value",
    "raw_seed_body",
)
DOCTRINE_NODE_KINDS = {"principle", "concept", "mechanism", "axiom"}
VALID_OUTCOMES = {
    "refined_existing_surface",
    "workitem_captured",
    "nothing_to_refine",
    "already_propagated_verified",
}

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "public_voice_to_doctrine_self_improvement_fixture_only_with_real_macro_refs"
    ),
    "raw_operator_voice_export_authorized": False,
    "private_thread_body_export_authorized": False,
    "doctrine_node_hand_edit_authorized": False,
    "global_doctrine_promotion_authorized": False,
    "live_task_ledger_mutation_authorized": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Voice-to-doctrine self-improvement validates the public shape of the macro "
    "metabolism: local pressure is classified, routed to an owner surface, "
    "mutated or captured there, validated, and closed with a re-entry condition. "
    "It imports real macro paper-module and skill refs as public substrate, but "
    "it does not export raw operator voice, private thread bodies, provider "
    "payloads, live Task Ledger rows, hand-edited doctrine nodes, global "
    "promotion authority, source mutation, or release authority."
)


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path.resolve(strict=False), display_root=public_root)


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    return paths


def _scan_input_paths(input_dir: Path) -> list[Path]:
    paths = [input_dir / name for name in INPUT_NAMES]
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    return paths


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


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
        "body_in_receipt": False,
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


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[str(case_id)].add(str(code))
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in results:
        findings.extend(result.get("findings", []))
    return sorted(
        findings,
        key=lambda row: (
            str(row.get("negative_case_id") or ""),
            str(row.get("subject_kind") or ""),
            str(row.get("subject_id") or ""),
            str(row.get("error_code") or ""),
        ),
    )


def _blocking_findings(
    findings: list[dict[str, Any]], *, include_negative: bool
) -> list[dict[str, Any]]:
    if not include_negative:
        return findings
    expected_cases = set(EXPECTED_NEGATIVE_CASES)
    return [
        finding
        for finding in findings
        if str(finding.get("negative_case_id") or "") not in expected_cases
    ]


def _has_forbidden_key(row: dict[str, Any]) -> bool:
    return any(key in row for key in FORBIDDEN_KEYS)


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    pattern_refs = set(_strings(protocol.get("source_pattern_refs")))
    missing_refs = sorted(REQUIRED_PATTERN_REFS - pattern_refs)
    if missing_refs:
        _record(
            findings,
            observed,
            "VOICE_DOCTRINE_REQUIRED_MACRO_PATTERN_REF_MISSING",
            "Projection protocol must carry the macro self-improvement refs.",
            case_id="projection_protocol",
            subject_id=",".join(missing_refs),
            subject_kind="projection_protocol",
        )
    verification = protocol.get("body_import_verification", {})
    if not isinstance(verification, dict) or not verification.get("target_ref"):
        _record(
            findings,
            observed,
            "VOICE_DOCTRINE_BODY_IMPORT_VERIFICATION_MISSING",
            "Projection protocol must name the public target body/refactor.",
            case_id="projection_protocol",
            subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
            subject_kind="projection_protocol",
        )
    return {
        "status": PASS if not findings else "fail",
        "findings": findings,
        "observed_negative_cases": {
            case_id: sorted(codes) for case_id, codes in observed.items()
        },
        "source_pattern_refs": sorted(pattern_refs),
        "body_import_verification": verification if isinstance(verification, dict) else {},
    }


def validate_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    sequence = _strings(policy.get("required_sequence"))
    missing_sequence = [step for step in REQUIRED_SEQUENCE if step not in sequence]
    if missing_sequence:
        _record(
            findings,
            observed,
            "VOICE_DOCTRINE_REQUIRED_SEQUENCE_MISSING",
            "Self-improvement loop must carry the full sense-to-reentry sequence.",
            case_id="propagation_policy",
            subject_id=",".join(missing_sequence),
            subject_kind="propagation_policy",
        )
    if policy.get("receipt_only_progress_authorized") is True:
        _record(
            findings,
            observed,
            "VOICE_DOCTRINE_RECEIPT_ONLY_PROGRESS",
            "Receipt-only progress cannot satisfy the self-improvement loop.",
            case_id="pattern_receipt_only_progress",
            subject_id=str(policy.get("policy_id") or "propagation_policy"),
            subject_kind="propagation_policy",
        )
    return {
        "status": PASS if not findings else "fail",
        "findings": findings,
        "observed_negative_cases": {
            case_id: sorted(codes) for case_id, codes in observed.items()
        },
        "required_sequence": sequence,
    }


def validate_owner_surfaces(payload: object) -> dict[str, Any]:
    owner_rows = _rows(payload, "owner_surfaces")
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    owner_map: dict[str, dict[str, Any]] = {}
    for row in owner_rows:
        owner_id = str(row.get("owner_surface_id") or "")
        if not owner_id:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_OWNER_SURFACE_ID_MISSING",
                "Owner surface rows need stable ids.",
                case_id="owner_surfaces",
                subject_id=str(row.get("title") or "missing_owner_id"),
                subject_kind="owner_surface",
            )
            continue
        owner_map[owner_id] = row
        if not row.get("public_ref") or not row.get("mutation_authority"):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_OWNER_SURFACE_CONTRACT_MISSING",
                "Owner surface rows need public refs and mutation authority.",
                case_id="owner_surfaces",
                subject_id=owner_id,
                subject_kind="owner_surface",
            )
    return {
        "status": PASS if not findings else "fail",
        "findings": findings,
        "observed_negative_cases": {
            case_id: sorted(codes) for case_id, codes in observed.items()
        },
        "owner_map": owner_map,
    }


def validate_lessons(payload: object, *, owner_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    lessons = _rows(payload, "lessons")
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    status_counts: dict[str, int] = defaultdict(int)
    owner_counts: dict[str, int] = defaultdict(int)
    for row in lessons:
        lesson_id = str(row.get("lesson_id") or "missing_lesson_id")
        missing = [field for field in REQUIRED_LESSON_FIELDS if field not in row]
        if missing:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_LESSON_FIELD_MISSING",
                "Lesson rows must carry owner, validation, and closeout fields.",
                case_id="local_lessons",
                subject_id=f"{lesson_id}:{','.join(missing)}",
                subject_kind="lesson",
            )
        if _has_forbidden_key(row) or row.get("body_exported") is True:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_RAW_OPERATOR_BODY_FORBIDDEN",
                "Lesson rows must not export raw operator, private, or provider bodies.",
                case_id="raw_operator_voice_export",
                subject_id=lesson_id,
                subject_kind="lesson",
            )
        owner_id = str(row.get("selected_owner_surface_id") or "")
        if owner_id not in owner_map:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_OWNER_SURFACE_UNKNOWN",
                "Lesson selected an owner surface not present in owner_surfaces.",
                case_id="local_lessons",
                subject_id=f"{lesson_id}:{owner_id}",
                subject_kind="lesson",
            )
        else:
            owner_counts[owner_id] += 1
        status = str(row.get("status") or "")
        status_counts[status] += 1
        if status not in VALID_OUTCOMES:
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_OUTCOME_UNKNOWN",
                "Lesson outcome must be one of the accepted propagation outcomes.",
                case_id="local_lessons",
                subject_id=f"{lesson_id}:{status}",
                subject_kind="lesson",
            )
        if row.get("owner_action") == "append_receipt_only" or (
            status == "refined_existing_surface" and not row.get("changed_surface_ref")
        ):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_RECEIPT_ONLY_PROGRESS",
                "Refinement requires an owner surface change, not a receipt-only row.",
                case_id="pattern_receipt_only_progress",
                subject_id=lesson_id,
                subject_kind="lesson",
            )
        if status == "workitem_captured" and not row.get("reentry_condition"):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_CAPTURE_WITHOUT_REENTRY",
                "Residual captures need a concrete re-entry condition.",
                case_id="local_lessons",
                subject_id=lesson_id,
                subject_kind="lesson",
            )
        if status == "nothing_to_refine" and (
            row.get("stewardship_checked") is not True
            or row.get("next_best_lane_checked") is not True
        ):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_NULL_PASS_WITHOUT_STEWARDSHIP",
                "Nothing-to-refine requires stewardship and next-best-lane evidence.",
                case_id="consume_without_deposit",
                subject_id=lesson_id,
                subject_kind="lesson",
            )
        if row.get("global_promotion_requested") is True and (
            row.get("owner_surface_validated") is not True or not row.get("validation_ref")
        ):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_GLOBAL_PROMOTION_WITHOUT_OWNER_VALIDATION",
                "Global promotion is blocked without owner validation.",
                case_id="global_promotion_without_owner_validation",
                subject_id=lesson_id,
                subject_kind="lesson",
            )
    return {
        "status": PASS if not findings else "fail",
        "findings": findings,
        "observed_negative_cases": {
            case_id: sorted(codes) for case_id, codes in observed.items()
        },
        "lesson_count": len(lessons),
        "status_counts": dict(sorted(status_counts.items())),
        "owner_counts": dict(sorted(owner_counts.items())),
        "lessons": lessons,
    }


def validate_negative_cases(payloads: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for case_id in NEGATIVE_INPUT_NAMES:
        stem = Path(case_id).stem
        payload = payloads.get(stem, {})
        row = payload if isinstance(payload, dict) else {}
        if stem == "raw_operator_voice_export" and _has_forbidden_key(row):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_RAW_OPERATOR_BODY_FORBIDDEN",
                "Raw operator voice bodies are excluded from public microcosm.",
                case_id=stem,
                subject_id=stem,
                subject_kind="negative_case",
            )
        elif stem == "doctrine_node_hand_edit" and (
            row.get("target_kind") in DOCTRINE_NODE_KINDS
            and row.get("mutation_route") == "direct_file_edit"
        ):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_DIRECT_NODE_EDIT_FORBIDDEN",
                "Doctrine nodes must route through apply lanes, not hand edits.",
                case_id=stem,
                subject_id=stem,
                subject_kind="negative_case",
            )
        elif stem == "consume_without_deposit" and not row.get("deposit_outcome"):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_CONSUME_WITHOUT_DEPOSIT",
                "Consumed surfaces require an owner mutation, capture, or typed no-op.",
                case_id=stem,
                subject_id=stem,
                subject_kind="negative_case",
            )
        elif stem == "pattern_receipt_only_progress" and row.get("owner_action") == "append_receipt_only":
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_RECEIPT_ONLY_PROGRESS",
                "Pattern receipts are evidence, not the main progress unit.",
                case_id=stem,
                subject_id=stem,
                subject_kind="negative_case",
            )
        elif stem == "global_promotion_without_owner_validation" and (
            row.get("global_promotion_requested") is True
            and row.get("owner_surface_validated") is not True
        ):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_GLOBAL_PROMOTION_WITHOUT_OWNER_VALIDATION",
                "Global promotion requires owner validation first.",
                case_id=stem,
                subject_id=stem,
                subject_kind="negative_case",
            )
        elif stem == "private_thread_body_export" and _has_forbidden_key(row):
            _record(
                findings,
                observed,
                "VOICE_DOCTRINE_PRIVATE_THREAD_BODY_FORBIDDEN",
                "Private thread bodies must remain out of public fixtures.",
                case_id=stem,
                subject_id=stem,
                subject_kind="negative_case",
            )
    return {
        "status": PASS if not findings else "fail",
        "findings": findings,
        "observed_negative_cases": {
            case_id: sorted(codes) for case_id, codes in observed.items()
        },
    }


def _receipt_paths(out: Path, *, acceptance_out: Path | None, public_root: Path) -> list[str]:
    paths = [
        out / RESULT_NAME,
        out / BOARD_NAME,
        out / VALIDATION_RECEIPT_NAME,
    ]
    if acceptance_out is not None:
        paths.append(acceptance_out)
    return [_display(path, public_root=public_root) for path in paths]


def _build_board(
    *,
    lessons_result: dict[str, Any],
    owner_map: dict[str, dict[str, Any]],
    command: str | None,
) -> dict[str, Any]:
    rows = []
    for row in lessons_result.get("lessons", []):
        owner = owner_map.get(str(row.get("selected_owner_surface_id") or ""), {})
        rows.append(
            {
                "lesson_id": row.get("lesson_id"),
                "input_signal_class": row.get("input_signal_class"),
                "selected_owner_surface_id": row.get("selected_owner_surface_id"),
                "owner_surface_kind": owner.get("surface_kind"),
                "owner_action": row.get("owner_action"),
                "status": row.get("status"),
                "changed_surface_ref": row.get("changed_surface_ref"),
                "validation_ref": row.get("validation_ref"),
                "closeout_ref": row.get("closeout_ref"),
                "reentry_condition": row.get("reentry_condition"),
                "body_in_receipt": False,
            }
        )
    return {
        "schema_version": "voice_to_doctrine_self_improvement_board_v1",
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "created_at": utc_now(),
        "status": PASS,
        "command": command,
        "board_rows": rows,
        "owner_surface_ids": sorted(owner_map),
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out: str | Path,
    *,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
    include_negative: bool = True,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    output_dir = Path(out)
    public_root = _public_root_for_path(input_path)
    payloads = _load_payloads(input_path, include_negative=include_negative)

    protocol_result = validate_projection_protocol(payloads.get("projection_protocol"))
    policy_result = validate_policy(payloads.get("propagation_policy"))
    owner_result = validate_owner_surfaces(payloads.get("owner_surfaces"))
    lessons_result = validate_lessons(
        payloads.get("local_lessons"),
        owner_map=owner_result["owner_map"],
    )
    negative_result = (
        validate_negative_cases(payloads) if include_negative else {"findings": [], "observed_negative_cases": {}}
    )
    secret_scan = scan_paths(
        [path.resolve(strict=False) for path in _scan_input_paths(input_path)],
        forbidden_classes=load_forbidden_classes(
            public_root / "core/private_state_forbidden_classes.json"
        ),
        source_context="target",
        display_root=public_root,
    )
    observed = _merge_observed(
        protocol_result,
        policy_result,
        owner_result,
        lessons_result,
        negative_result,
    )
    missing_negative_cases = (
        [
            case_id
            for case_id, codes in EXPECTED_NEGATIVE_CASES.items()
            if sorted(observed.get(case_id, [])) != sorted(codes)
        ]
        if include_negative
        else []
    )
    findings = _merge_findings(
        protocol_result,
        policy_result,
        owner_result,
        lessons_result,
        negative_result,
    )
    blocking_findings = _blocking_findings(
        findings, include_negative=include_negative
    )
    status = (
        PASS
        if not blocking_findings
        and not missing_negative_cases
        and secret_scan.get("status") == PASS
        else "fail"
    )
    receipt_refs = _receipt_paths(
        output_dir,
        acceptance_out=Path(acceptance_out) if acceptance_out else None,
        public_root=public_root,
    )
    status_counts = lessons_result["status_counts"]
    result = {
        "schema_version": "voice_to_doctrine_self_improvement_loop_result_v1",
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "created_at": utc_now(),
        "status": status,
        "command": command,
        "input_mode": "first_wave_fixture",
        "lesson_count": lessons_result["lesson_count"],
        "owner_surface_count": len(owner_result["owner_map"]),
        "refined_existing_surface_count": status_counts.get(
            "refined_existing_surface", 0
        ),
        "workitem_capture_count": status_counts.get("workitem_captured", 0),
        "nothing_to_refine_count": status_counts.get("nothing_to_refine", 0),
        "already_propagated_verified_count": status_counts.get(
            "already_propagated_verified", 0
        ),
        "status_counts": status_counts,
        "owner_counts": lessons_result["owner_counts"],
        "source_pattern_refs": protocol_result["source_pattern_refs"],
        "body_import_verification": protocol_result["body_import_verification"],
        "required_sequence": policy_result["required_sequence"],
        "observed_negative_cases": observed,
        "expected_negative_cases": EXPECTED_NEGATIVE_CASES if include_negative else {},
        "missing_negative_cases": missing_negative_cases,
        "error_codes": sorted({str(finding.get("error_code")) for finding in findings}),
        "blocking_error_codes": sorted(
            {str(finding.get("error_code")) for finding in blocking_findings}
        ),
        "findings": findings,
        "blocking_findings": blocking_findings,
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
        "metadata_projection_not_live_learning_authority": True,
        "receipt_paths": receipt_refs,
    }
    board = _build_board(
        lessons_result=lessons_result,
        owner_map=owner_result["owner_map"],
        command=command,
    )
    validation_receipt = {
        "schema_version": "voice_to_doctrine_self_improvement_validation_v1",
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "created_at": utc_now(),
        "status": status,
        "command": command,
        "checks": {
            "required_macro_pattern_refs_present": not any(
                finding.get("error_code")
                == "VOICE_DOCTRINE_REQUIRED_MACRO_PATTERN_REF_MISSING"
                for finding in findings
            ),
            "owner_surfaces_present": len(owner_result["owner_map"]) >= 4,
            "lesson_owner_deposits_present": result["lesson_count"] >= 4,
            "negative_cases_observed": missing_negative_cases == [],
            "secret_exclusion_scan_passed": secret_scan.get("status") == PASS,
            "receipt_only_progress_rejected": (
                "VOICE_DOCTRINE_RECEIPT_ONLY_PROGRESS" in result["error_codes"]
                if include_negative
                else True
            ),
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }
    write_json_atomic(output_dir / RESULT_NAME, result)
    write_json_atomic(output_dir / BOARD_NAME, board)
    write_json_atomic(output_dir / VALIDATION_RECEIPT_NAME, validation_receipt)
    if acceptance_out:
        acceptance = dict(result)
        acceptance["schema_version"] = "voice_to_doctrine_self_improvement_acceptance_v1"
        acceptance["receipt_id"] = "voice_to_doctrine_self_improvement_fixture_acceptance"
        write_json_atomic(acceptance_out, acceptance)
    return result


def run_voice_to_doctrine_bundle(
    input_dir: str | Path,
    out: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    result = run(input_dir, out, command=command, include_negative=False)
    bundle_manifest_path = Path(input_dir) / "bundle_manifest.json"
    manifest = read_json_strict(bundle_manifest_path) if bundle_manifest_path.is_file() else {}
    result = dict(result)
    result["schema_version"] = "voice_to_doctrine_exported_bundle_validation_v1"
    result["input_mode"] = "exported_voice_to_doctrine_bundle"
    result["bundle_id"] = manifest.get(
        "bundle_id", "voice_to_doctrine_self_improvement_loop_runtime_example"
    )
    result["expected_negative_cases"] = {}
    result["missing_negative_cases"] = []
    result["error_codes"] = []
    result["findings"] = []
    write_json_atomic(Path(out) / BUNDLE_RESULT_NAME, result)
    return result


def _scan_card(scan: object) -> dict[str, Any]:
    scan_row = scan if isinstance(scan, dict) else {}
    return {
        "status": scan_row.get("status"),
        "blocking_hit_count": scan_row.get("blocking_hit_count"),
        "hit_count": scan_row.get("hit_count"),
        "scanned_path_count": scan_row.get("scanned_path_count"),
        "body_in_receipt": scan_row.get("body_in_receipt") is True,
        "hits_exported": False,
        "scan_scope_exported": False,
        "source_excerpt_exported": False,
    }


def _authority_ceiling_card(result: dict[str, Any]) -> dict[str, Any]:
    ceiling = result.get("authority_ceiling", {})
    if not isinstance(ceiling, dict):
        ceiling = {}
    return {
        "status": ceiling.get("status"),
        "raw_operator_voice_export_authorized": (
            ceiling.get("raw_operator_voice_export_authorized") is True
        ),
        "private_thread_body_export_authorized": (
            ceiling.get("private_thread_body_export_authorized") is True
        ),
        "doctrine_node_hand_edit_authorized": (
            ceiling.get("doctrine_node_hand_edit_authorized") is True
        ),
        "global_doctrine_promotion_authorized": (
            ceiling.get("global_doctrine_promotion_authorized") is True
        ),
        "live_task_ledger_mutation_authorized": (
            ceiling.get("live_task_ledger_mutation_authorized") is True
        ),
        "provider_calls_authorized": ceiling.get("provider_calls_authorized") is True,
        "source_mutation_authorized": (
            ceiling.get("source_mutation_authorized") is True
        ),
        "release_authorized": ceiling.get("release_authorized") is True,
    }


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    input_mode = result.get("input_mode")
    action = "run-bundle" if input_mode == "exported_voice_to_doctrine_bundle" else "run"
    expected_cases = result.get("expected_negative_cases", {})
    observed_cases = result.get("observed_negative_cases", {})
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": ORGAN_ID,
        "input_mode": input_mode,
        "bundle_id": result.get("bundle_id"),
        "card_id": (
            "voice_to_doctrine_exported_bundle_card"
            if action == "run-bundle"
            else "voice_to_doctrine_fixture_card"
        ),
        "output_profile": "compact_card_no_findings_tables_bodies_or_scan_scope",
        "full_output_available": True,
        "full_output_drilldown": f"rerun {action} without --card",
        "receipt_summary": {
            "receipt_count": len(result.get("receipt_paths", [])),
            "receipt_paths_exported": False,
            "result_receipt_name": (
                BUNDLE_RESULT_NAME if action == "run-bundle" else RESULT_NAME
            ),
            "board_receipt_name": BOARD_NAME,
            "validation_receipt_name": VALIDATION_RECEIPT_NAME,
        },
        "doctrine_loop_summary": {
            "lesson_count": result.get("lesson_count"),
            "owner_surface_count": result.get("owner_surface_count"),
            "refined_existing_surface_count": result.get(
                "refined_existing_surface_count"
            ),
            "workitem_capture_count": result.get("workitem_capture_count"),
            "nothing_to_refine_count": result.get("nothing_to_refine_count"),
            "already_propagated_verified_count": result.get(
                "already_propagated_verified_count"
            ),
            "status_counts": result.get("status_counts", {}),
            "source_pattern_ref_count": len(result.get("source_pattern_refs", [])),
            "required_sequence_count": len(result.get("required_sequence", [])),
            "body_import_verification_mode": (
                result.get("body_import_verification", {}).get("verification_mode")
                if isinstance(result.get("body_import_verification"), dict)
                else None
            ),
        },
        "negative_case_coverage": {
            "expected_case_count": len(expected_cases)
            if isinstance(expected_cases, dict)
            else 0,
            "observed_case_count": len(observed_cases)
            if isinstance(observed_cases, dict)
            else 0,
            "missing_negative_cases": result.get("missing_negative_cases", []),
            "error_code_count": len(result.get("error_codes", [])),
            "blocking_error_code_count": len(result.get("blocking_error_codes", [])),
        },
        "secret_exclusion_scan_summary": _scan_card(
            result.get("secret_exclusion_scan")
        ),
        "authority_ceiling": _authority_ceiling_card(result),
        "runtime_authority": {
            "body_in_receipt": result.get("body_in_receipt") is True,
            "metadata_projection_not_live_learning_authority": (
                result.get("metadata_projection_not_live_learning_authority") is True
            ),
        },
        "no_export_guards": {
            "findings_exported": False,
            "blocking_findings_exported": False,
            "owner_counts_exported": False,
            "observed_negative_cases_exported": False,
            "secret_scan_hits_exported": False,
            "secret_scan_scope_exported": False,
            "anti_claim_exported": False,
            "body_import_source_refs_exported": False,
            "private_bodies_exported": False,
            "provider_payloads_exported": False,
        },
        "output_economy": {
            "stdout_mode": "card",
            "full_payload_drilldown": "rerun without --card",
            "omitted_full_payload_keys": [
                "findings",
                "blocking_findings",
                "owner_counts",
                "observed_negative_cases",
                "source_pattern_refs",
                "required_sequence",
                "body_import_verification.source_refs",
                "secret_exclusion_scan.hits",
                "secret_exclusion_scan.scan_scope",
                "anti_claim",
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact command card; write the full receipt to --out.",
    )
    bundle_parser = subparsers.add_parser("run-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact command card; write the full receipt to --out.",
    )
    args = parser.parse_args(argv)
    if args.command == "run":
        card_suffix = " --card" if args.card else ""
        acceptance_suffix = (
            f" --acceptance-out {args.acceptance_out}" if args.acceptance_out else ""
        )
        result = run(
            args.input,
            args.out,
            command=(
                f"python -m {MODULE_PATH} run --input {args.input} "
                f"--out {args.out}{acceptance_suffix}{card_suffix}"
            ),
            acceptance_out=args.acceptance_out,
        )
    elif args.command == "run-bundle":
        card_suffix = " --card" if args.card else ""
        result = run_voice_to_doctrine_bundle(
            args.input,
            args.out,
            command=(
                f"python -m {MODULE_PATH} run-bundle --input {args.input} "
                f"--out {args.out}{card_suffix}"
            ),
        )
    else:
        parser.error("expected a subcommand")
    output = result_card(result) if args.card else result
    print(json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.get("status") == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
