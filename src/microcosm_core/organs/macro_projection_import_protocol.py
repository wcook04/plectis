from __future__ import annotations

import argparse
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
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "macro_projection_import_protocol"
FIXTURE_ID = "first_wave.macro_projection_import_protocol"
VALIDATOR_ID = "validator.microcosm.organs.macro_projection_import_protocol"

RESULT_NAME = "macro_projection_import_protocol_result.json"
BOARD_NAME = "projection_import_board.json"
INTAKE_BOARD_NAME = "projection_import_intake_board.json"
VALIDATION_RECEIPT_NAME = "projection_import_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "macro_projection_import_protocol_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_projection_import_bundle_validation_result.json"

INPUT_NAMES = (
    "projection_protocol.json",
    "cleaning_policy.json",
    "import_plan.json",
)
NEGATIVE_INPUT_NAMES = (
    "private_body_import_overclaim.json",
    "missing_omission_receipt.json",
    "authority_upgrade_overclaim.json",
    "missing_validation_ref.json",
    "release_or_private_equivalence_overclaim.json",
)

EXPECTED_NEGATIVE_CASES = {
    "private_body_import_overclaim": ["MACRO_PROJECTION_PRIVATE_BODY_FORBIDDEN"],
    "missing_omission_receipt": ["MACRO_PROJECTION_OMISSION_RECEIPT_MISSING"],
    "authority_upgrade_overclaim": ["MACRO_PROJECTION_AUTHORITY_UPGRADE"],
    "missing_validation_ref": ["MACRO_PROJECTION_VALIDATION_REF_MISSING"],
    "release_or_private_equivalence_overclaim": [
        "MACRO_PROJECTION_RELEASE_OR_EQUIVALENCE_OVERCLAIM"
    ],
}

FORBIDDEN_MATERIAL_CLASSES = {
    "raw_seed_body",
    "operator_thread_body",
    "provider_payload_body",
    "private_source_body",
    "credential",
    "secret",
    "recipient_packet_body",
    "release_packet_body",
}
FORBIDDEN_AUTHORITY_FLAGS = (
    "source_authority_above_macro_contracts",
    "live_macro_source_authority",
    "private_root_equivalence_authorized",
    "whole_system_correctness_claim",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "macro_projection_protocol_metadata_fixture_and_receipt_refs_only",
    "private_source_bodies_exported": False,
    "raw_seed_body_read": False,
    "operator_thread_body_read": False,
    "provider_payload_body_read": False,
    "release_authorized": False,
    "publication_authorized": False,
    "recipient_work_authorized": False,
    "private_data_equivalence_claim": False,
    "source_authority_above_macro_contracts": False,
    "live_macro_source_authority": False,
    "whole_system_correctness_claim": False,
}
ANTI_CLAIM = (
    "The macro projection import protocol validates public-safe projection "
    "metadata, omission receipts, replacement refs, authority ceilings, and "
    "validation refs. It does not copy private bodies, authorize release or "
    "publication, claim private-root equivalence, elevate Microcosm above its "
    "public receipts, run provider calls, or make macro source authority public."
)
CELL_STATUS_PROTOCOL = {
    "schema_version": "macro_projection_cell_status_protocol_v1",
    "status_field": "projection_status",
    "cell_state_field": "cell_state",
    "open_action_field": "action_required",
    "closed_statuses": [
        "public_replacement_landed",
        "self_hosted_status_protocol_landed",
        "runtime_bridge_landed",
    ],
    "open_statuses": [
        "ready_for_projection",
        "blocked",
    ],
    "authority_ceiling": "metadata_fixture_receipt_ref_status_only",
    "anti_claim": (
        "Cell status is a public intake state machine over metadata and receipt refs. "
        "It is not private source authority, release readiness, or proof of whole-system correctness."
    ),
}
LANDING_PROJECTION_STATUSES = set(CELL_STATUS_PROTOCOL["closed_statuses"])
CELL_STATUS_OVERRIDES: dict[str, dict[str, Any]] = {
    "formal_math_readiness_extensions": {
        "projection_status": "public_replacement_landed",
        "cell_state": "consumed_public_replacement",
        "action_required": False,
        "status_reason": (
            "The formal-math readiness extension cell has a public replacement board "
            "with premise, tactic, routing, provider-context, source-intake, and validation refs."
        ),
        "landed_evidence_refs": [
            "receipts/first_wave/formal_math_readiness_gate/formal_math_readiness_extension_board.json",
            "receipts/first_wave/formal_math_readiness_gate/formal_math_readiness_validation_receipt.json",
            "paper_modules/formal_math_readiness_gate.md",
        ],
        "next_runtime_surface": (
            "microcosm formal-math-readiness-gate plan --input "
            "fixtures/first_wave/formal_math_readiness_gate/input"
        ),
    },
    "projection_protocol_self_host": {
        "projection_status": "self_hosted_status_protocol_landed",
        "cell_state": "consumed_protocol_self_host",
        "action_required": False,
        "status_reason": (
            "The macro projection protocol now emits this cell-status state machine "
            "directly in plan, run, receipts, and runtime intake views."
        ),
        "landed_evidence_refs": [
            "standards/std_microcosm_macro_projection_import_protocol.json",
            "paper_modules/macro_projection_import_protocol.md",
            "receipts/first_wave/macro_projection_import_protocol/projection_import_intake_board.json",
            "receipts/first_wave/macro_projection_import_protocol/projection_import_validation_receipt.json",
        ],
        "next_runtime_surface": (
            "microcosm macro-projection-import-protocol plan --input "
            "examples/macro_projection_import_protocol/exported_projection_import_bundle"
        ),
    },
    "runtime_reveal_import_bridge": {
        "projection_status": "runtime_bridge_landed",
        "cell_state": "bridged_runtime_surface",
        "action_required": False,
        "status_reason": (
            "The reveal/import bridge is landed as microcosm intake with a runtime receipt "
            "and first-run path through spine, intake, reveal, and evidence."
        ),
        "landed_evidence_refs": [
            "receipts/runtime_shell/intake_bridge/runtime_reveal_import_bridge.json",
            "receipts/runtime_shell/intake_bridge/organs/public_reveal_walkthrough/exported_public_reveal_bundle_validation_result.json",
            "paper_modules/public_reveal_walkthrough.md",
        ],
        "next_runtime_surface": "microcosm intake",
    },
}


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names]


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


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


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(str(code))
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


def _authority_upgrade(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    ceiling = payload.get("authority_ceiling", payload)
    if not isinstance(ceiling, dict):
        return False
    return any(ceiling.get(flag) is True for flag in FORBIDDEN_AUTHORITY_FLAGS)


def _release_or_equivalence_overclaim(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    ceiling = payload.get("authority_ceiling", payload)
    if not isinstance(ceiling, dict):
        return False
    return any(
        ceiling.get(flag) is True
        for flag in (
            "release_authorized",
            "hosted_public_authorized",
            "publication_authorized",
            "recipient_work_authorized",
            "private_data_equivalence_claim",
            "private_root_equivalence_authorized",
        )
    )


def _private_body_request(payload: object) -> list[str]:
    subjects: list[str] = []
    for key in ("copied_material", "material_requests", "source_refs"):
        for row in _rows(payload, key):
            material_id = str(row.get("material_id") or row.get("source_ref") or key)
            material_class = str(row.get("material_class") or "")
            if (
                row.get("body_copied") is True
                or row.get("body_included") is True
                or row.get("private_body_requested") is True
                or material_class in FORBIDDEN_MATERIAL_CLASSES
            ):
                subjects.append(material_id)
    if isinstance(payload, dict):
        material_class = str(payload.get("material_class") or "")
        if (
            payload.get("body_copied") is True
            or payload.get("body_included") is True
            or payload.get("private_body_requested") is True
            or material_class in FORBIDDEN_MATERIAL_CLASSES
        ):
            subjects.append(str(payload.get("material_id") or payload.get("case_id") or "material"))
    return sorted(set(subjects))


def validate_projection_protocol(
    payload: object,
    private_negative: object | None = None,
    omission_negative: object | None = None,
    authority_negative: object | None = None,
    release_negative: object | None = None,
) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    public_replacements = _strings(protocol.get("public_replacement_refs"))
    validation_refs = _strings(protocol.get("validation_refs"))
    copied_material = _rows(protocol, "copied_material")
    omitted_material = _rows(protocol, "omitted_material")
    cleaned_material = _rows(protocol, "cleaned_material")
    steps = _rows(protocol, "steps")

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if len(source_refs) < 2 or len(public_replacements) < 2 or len(validation_refs) < 2:
        findings.append(
            _finding(
                "MACRO_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Projection protocol must cite source refs, public replacements, and validation refs.",
                case_id="density_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    for row in copied_material:
        material_id = str(row.get("material_id") or "copied_material")
        material_class = str(row.get("material_class") or "")
        if material_class in FORBIDDEN_MATERIAL_CLASSES or row.get("body_copied") is True:
            findings.append(
                _finding(
                    "MACRO_PROJECTION_PRIVATE_BODY_FORBIDDEN",
                    "Copied material may carry metadata or fixture shape only, never private bodies.",
                    case_id="protocol_floor",
                    subject_id=material_id,
                    subject_kind="copied_material",
                )
            )
    for row in omitted_material:
        if not row.get("omission_receipt_ref"):
            findings.append(
                _finding(
                    "MACRO_PROJECTION_OMISSION_RECEIPT_MISSING",
                    "Omitted macro material must carry an omission receipt ref.",
                    case_id="protocol_floor",
                    subject_id=str(row.get("material_id") or "omitted_material"),
                    subject_kind="omitted_material",
                )
            )
    for negative in (private_negative,):
        for subject in _private_body_request(negative):
            _record(
                findings,
                observed,
                "MACRO_PROJECTION_PRIVATE_BODY_FORBIDDEN",
                "Projection import rejects private body import requests.",
                case_id="private_body_import_overclaim",
                subject_id=subject,
                subject_kind="negative_case",
            )
    if isinstance(omission_negative, dict):
        rows = _rows(omission_negative, "omitted_material")
        if not rows:
            rows = [omission_negative]
        for row in rows:
            if not row.get("omission_receipt_ref"):
                _record(
                    findings,
                    observed,
                    "MACRO_PROJECTION_OMISSION_RECEIPT_MISSING",
                    "Projection import rejects omitted material without omission receipts.",
                    case_id="missing_omission_receipt",
                    subject_id=str(row.get("material_id") or "omitted_material"),
                    subject_kind="negative_case",
                )
    if _authority_upgrade(authority_negative):
        _record(
            findings,
            observed,
            "MACRO_PROJECTION_AUTHORITY_UPGRADE",
            "Projection import cannot upgrade public metadata into live macro source authority.",
            case_id="authority_upgrade_overclaim",
            subject_id=str(
                authority_negative.get("case_id") if isinstance(authority_negative, dict) else "authority"
            ),
            subject_kind="negative_case",
        )
    if _release_or_equivalence_overclaim(release_negative):
        _record(
            findings,
            observed,
            "MACRO_PROJECTION_RELEASE_OR_EQUIVALENCE_OVERCLAIM",
            "Projection import rejects release, publication, recipient, and private-equivalence claims.",
            case_id="release_or_private_equivalence_overclaim",
            subject_id=str(
                release_negative.get("case_id") if isinstance(release_negative, dict) else "release"
            ),
            subject_kind="negative_case",
        )

    return {
        "status": PASS
        if len(source_refs) >= 2
        and len(public_replacements) >= 2
        and len(validation_refs) >= 2
        and copied_material
        and omitted_material
        and cleaned_material
        and steps
        else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "public_replacement_refs": public_replacements,
        "validation_refs": validation_refs,
        "copied_material_count": len(copied_material),
        "cleaned_material_count": len(cleaned_material),
        "omitted_material_count": len(omitted_material),
        "step_count": len(steps),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_cleaning_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    forbidden = set(_strings(policy.get("forbidden_material_classes")))
    actions = _strings(policy.get("required_cleaning_actions"))
    required_forbidden = {
        "raw_seed_body",
        "operator_thread_body",
        "provider_payload_body",
        "private_source_body",
        "credential",
    }
    missing_forbidden = sorted(required_forbidden - forbidden)
    findings: list[dict[str, Any]] = []
    if missing_forbidden:
        findings.append(
            _finding(
                "MACRO_PROJECTION_CLEANING_POLICY_INCOMPLETE",
                "Cleaning policy must forbid private body and credential classes.",
                case_id="cleaning_policy_floor",
                subject_id="forbidden_material_classes",
                subject_kind="cleaning_policy",
            )
        )
    if policy.get("requires_omission_receipt") is not True:
        findings.append(
            _finding(
                "MACRO_PROJECTION_CLEANING_POLICY_INCOMPLETE",
                "Cleaning policy must require omission receipts.",
                case_id="cleaning_policy_floor",
                subject_id="requires_omission_receipt",
                subject_kind="cleaning_policy",
            )
        )
    return {
        "status": PASS
        if not findings
        and policy.get("default_copy_mode") == "metadata_or_fixture_shape_only"
        and len(actions) >= 4
        else "blocked",
        "policy_id": policy.get("policy_id"),
        "default_copy_mode": policy.get("default_copy_mode"),
        "forbidden_material_classes": sorted(forbidden),
        "required_cleaning_actions": actions,
        "requires_omission_receipt": policy.get("requires_omission_receipt") is True,
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_import_plan(
    payload: object,
    missing_validation_negative: object | None = None,
) -> dict[str, Any]:
    plan = payload if isinstance(payload, dict) else {}
    cells = _rows(plan, "proposed_cells")
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    cell_ids: list[str] = []
    target_refs: list[str] = []
    validation_refs: list[str] = []
    for row in cells:
        cell_id = str(row.get("cell_id") or "projection_cell")
        cell_ids.append(cell_id)
        target_refs.extend(_strings(row.get("target_refs")))
        validation_refs.extend(_strings(row.get("validation_refs")))
        if not _strings(row.get("source_refs")) or not _strings(row.get("target_refs")):
            findings.append(
                _finding(
                    "MACRO_PROJECTION_CELL_ROUTE_MISSING",
                    "Projection cell must name source and target refs.",
                    case_id="import_plan_floor",
                    subject_id=cell_id,
                    subject_kind="projection_cell",
                )
            )
        if not _strings(row.get("validation_refs")):
            findings.append(
                _finding(
                    "MACRO_PROJECTION_VALIDATION_REF_MISSING",
                    "Projection cell must name validation refs.",
                    case_id="import_plan_floor",
                    subject_id=cell_id,
                    subject_kind="projection_cell",
                )
            )
    if isinstance(missing_validation_negative, dict):
        rows = _rows(missing_validation_negative, "proposed_cells")
        if not rows:
            rows = [missing_validation_negative]
        for row in rows:
            if not _strings(row.get("validation_refs")):
                _record(
                    findings,
                    observed,
                    "MACRO_PROJECTION_VALIDATION_REF_MISSING",
                    "Projection import rejects cells without validation refs.",
                    case_id="missing_validation_ref",
                    subject_id=str(row.get("cell_id") or "projection_cell"),
                    subject_kind="negative_case",
                )
    return {
        "status": PASS if len(cells) >= 3 and target_refs and validation_refs else "blocked",
        "plan_id": plan.get("plan_id"),
        "projection_cell_count": len(cells),
        "projection_cell_ids": sorted(cell_ids),
        "target_refs": sorted(set(target_refs)),
        "validation_refs": sorted(set(validation_refs)),
        "next_best_lane": plan.get("next_best_lane"),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _projection_cell_rows(plan_payload: dict[str, Any]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for row in _rows(plan_payload, "proposed_cells"):
        cell_id = str(row.get("cell_id") or "projection_cell")
        source_refs = _strings(row.get("source_refs"))
        target_refs = _strings(row.get("target_refs"))
        validation_refs = _strings(row.get("validation_refs"))
        selected_pattern_ids = _strings(row.get("selected_pattern_ids"))
        blocking_reasons: list[str] = []
        if not source_refs:
            blocking_reasons.append("source_refs_missing")
        if not target_refs:
            blocking_reasons.append("target_refs_missing")
        if not validation_refs:
            blocking_reasons.append("validation_refs_missing")
        if row.get("body_copied") is True or row.get("body_included") is True:
            blocking_reasons.append("body_copy_requested")
        ready_to_project = not blocking_reasons
        if ready_to_project:
            state = dict(
                CELL_STATUS_OVERRIDES.get(
                    cell_id,
                    {
                        "projection_status": "ready_for_projection",
                        "cell_state": "ready_import_cell",
                        "action_required": True,
                        "status_reason": (
                            "Cell has source, target, and validation refs but has no landed "
                            "public replacement recorded in the projection status protocol."
                        ),
                        "landed_evidence_refs": [],
                        "next_runtime_surface": row.get("next_runtime_surface"),
                    },
                )
            )
        else:
            state = {
                "projection_status": "blocked",
                "cell_state": "blocked_import_cell",
                "action_required": True,
                "status_reason": "Cell cannot enter public projection until blocking reasons clear.",
                "landed_evidence_refs": [],
                "next_runtime_surface": row.get("next_runtime_surface"),
            }
        cells.append(
            {
                "cell_id": cell_id,
                "selected_pattern_ids": selected_pattern_ids,
                "source_refs": source_refs,
                "target_refs": target_refs,
                "validation_refs": validation_refs,
                "source_ref_count": len(source_refs),
                "target_ref_count": len(target_refs),
                "validation_ref_count": len(validation_refs),
                "copy_policy": "metadata_fixture_receipt_ref_only",
                "authority_ceiling": row.get("authority_ceiling"),
                "body_copied": row.get("body_copied") is True,
                "body_redacted": True,
                "ready_to_project": ready_to_project,
                "blocking_reasons": blocking_reasons,
                "projection_status": state["projection_status"],
                "cell_state": state["cell_state"],
                "action_required": state["action_required"] is True,
                "status_reason": state["status_reason"],
                "landed_evidence_refs": _strings(state.get("landed_evidence_refs")),
                "next_runtime_surface": state.get("next_runtime_surface"),
            }
        )
    return cells


def _omitted_material_rows(protocol_payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "material_id": str(row.get("material_id") or "omitted_material"),
            "omitted_class": str(row.get("omitted_class") or ""),
            "public_replacement_ref": row.get("public_replacement_ref"),
            "omission_receipt_ref": row.get("omission_receipt_ref"),
            "body_redacted": True,
        }
        for row in _rows(protocol_payload, "omitted_material")
    ]


def _build_projection_intake_board(
    payloads: dict[str, Any],
    *,
    protocol: dict[str, Any],
    cleaning_policy: dict[str, Any],
    import_plan: dict[str, Any],
    private_scan: dict[str, Any],
    input_mode: str,
    expected_negative_cases: dict[str, list[str]],
    observed_negative_cases: dict[str, list[str]],
    missing_negative_cases: list[str],
) -> dict[str, Any]:
    protocol_payload = (
        payloads.get("projection_protocol")
        if isinstance(payloads.get("projection_protocol"), dict)
        else {}
    )
    plan_payload = (
        payloads.get("import_plan") if isinstance(payloads.get("import_plan"), dict) else {}
    )
    cell_rows = _projection_cell_rows(plan_payload)
    ready_count = sum(1 for row in cell_rows if row["ready_to_project"])
    blocked_count = len(cell_rows) - ready_count
    status_counts = dict(
        sorted(Counter(str(row.get("projection_status") or "unknown") for row in cell_rows).items())
    )
    open_actionable_count = sum(1 for row in cell_rows if row.get("action_required") is True)
    landed_count = sum(
        1 for row in cell_rows if str(row.get("projection_status") or "") in LANDING_PROJECTION_STATUSES
    )
    return {
        "schema_version": "macro_projection_import_intake_board_v1",
        "headline": "Macro source refs become queued public projection cells before any body copy is possible.",
        "input_mode": input_mode,
        "protocol_id": protocol["protocol_id"],
        "policy_id": cleaning_policy["policy_id"],
        "plan_id": import_plan["plan_id"],
        "allowed_material": [
            "metadata",
            "fixture shape",
            "standard schema",
            "receipt summary",
            "public-root replacement ref",
        ],
        "allowed_material_classes": _strings(protocol_payload.get("material_classes")),
        "forbidden_material_classes": cleaning_policy["forbidden_material_classes"],
        "omitted_material": _omitted_material_rows(protocol_payload),
        "omitted_material_count": len(_omitted_material_rows(protocol_payload)),
        "projection_cells": cell_rows,
        "projection_cell_count": len(cell_rows),
        "ready_cell_count": ready_count,
        "blocked_cell_count": blocked_count,
        "projection_status_protocol": CELL_STATUS_PROTOCOL,
        "projection_status_counts": status_counts,
        "open_actionable_cell_count": open_actionable_count,
        "landed_cell_count": landed_count,
        "consumed_cell_count": landed_count,
        "negative_case_coverage_status": PASS if not missing_negative_cases else "blocked",
        "expected_negative_case_count": len(expected_negative_cases),
        "observed_negative_case_count": len(observed_negative_cases),
        "missing_negative_cases": missing_negative_cases,
        "private_state_blocking_hit_count": private_scan.get("blocking_hit_count"),
        "next_best_lane": import_plan["next_best_lane"],
        "authority_ceiling": AUTHORITY_CEILING,
        "release_authorized": False,
        "publication_authorized": False,
        "private_data_equivalence_claim": False,
        "body_redacted": True,
    }


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    private_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    private_scan.pop("forbidden_output_fields", None)
    private_scan["redacted_output_field_labels_omitted"] = True

    protocol = validate_projection_protocol(
        payloads["projection_protocol"],
        payloads.get("private_body_import_overclaim"),
        payloads.get("missing_omission_receipt"),
        payloads.get("authority_upgrade_overclaim"),
        payloads.get("release_or_private_equivalence_overclaim"),
    )
    cleaning_policy = validate_cleaning_policy(payloads["cleaning_policy"])
    import_plan = validate_import_plan(
        payloads["import_plan"],
        payloads.get("missing_validation_ref"),
    )
    observed = _merge_observed(protocol, cleaning_policy, import_plan)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(protocol, cleaning_policy, import_plan)
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    status = (
        PASS
        if not missing
        and private_scan["blocking_hit_count"] == 0
        and protocol["status"] == PASS
        and cleaning_policy["status"] == PASS
        and import_plan["status"] == PASS
        else "blocked"
    )
    projection_intake_board = _build_projection_intake_board(
        payloads,
        protocol=protocol,
        cleaning_policy=cleaning_policy,
        import_plan=import_plan,
        private_scan=private_scan,
        input_mode=input_mode,
        expected_negative_cases=expected,
        observed_negative_cases=observed,
        missing_negative_cases=missing,
    )
    return {
        "schema_version": "macro_projection_import_protocol_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id") if isinstance(bundle_manifest, dict) else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "private_state_scan": private_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "protocol_id": protocol["protocol_id"],
        "policy_id": cleaning_policy["policy_id"],
        "plan_id": import_plan["plan_id"],
        "source_ref_count": len(protocol["source_refs"]),
        "public_replacement_ref_count": len(protocol["public_replacement_refs"]),
        "validation_ref_count": len(set(protocol["validation_refs"] + import_plan["validation_refs"])),
        "projection_cell_count": import_plan["projection_cell_count"],
        "ready_projection_cell_count": projection_intake_board["ready_cell_count"],
        "blocked_projection_cell_count": projection_intake_board["blocked_cell_count"],
        "projection_cell_ids": import_plan["projection_cell_ids"],
        "source_refs": protocol["source_refs"],
        "public_replacement_refs": sorted(
            set(protocol["public_replacement_refs"] + import_plan["target_refs"])
        ),
        "validation_refs": sorted(set(protocol["validation_refs"] + import_plan["validation_refs"])),
        "forbidden_material_classes": cleaning_policy["forbidden_material_classes"],
        "next_best_lane": import_plan["next_best_lane"],
        "projection_board": {
            "headline": "Macro material enters Microcosm through public-safe projection, not body copy.",
            "protocol_id": protocol["protocol_id"],
            "allowed_material": [
                "metadata",
                "fixture shape",
                "standard schema",
                "receipt summary",
                "public-root replacement ref",
            ],
            "forbidden_material_classes": cleaning_policy["forbidden_material_classes"],
            "projection_cell_count": import_plan["projection_cell_count"],
            "next_best_lane": import_plan["next_best_lane"],
            "release_authorized": False,
            "private_data_equivalence_claim": False,
            "body_redacted": True,
            "intake_board_ref": INTAKE_BOARD_NAME,
        },
        "projection_intake_board": projection_intake_board,
        "body_redacted": True,
    }


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    keys = (
        "status",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "input_mode",
        "bundle_id",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "private_state_scan",
        "authority_ceiling",
        "anti_claim",
        "protocol_id",
        "policy_id",
        "plan_id",
        "source_ref_count",
        "public_replacement_ref_count",
        "validation_ref_count",
        "projection_cell_count",
        "ready_projection_cell_count",
        "blocked_projection_cell_count",
        "projection_cell_ids",
        "source_refs",
        "public_replacement_refs",
        "validation_refs",
        "forbidden_material_classes",
        "next_best_lane",
        "body_redacted",
    )
    payload = {
        "schema_version": schema_version,
        "receipt_id": schema_version,
        "created_at": result["created_at"],
        "receipt_paths": receipt_paths,
    }
    for key in keys:
        payload[key] = result.get(key)
    return payload


def write_receipts(
    out_dir: str | Path,
    result: dict[str, Any],
    *,
    public_root: str | Path,
    acceptance_out: str | Path | None = None,
) -> dict[str, str]:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root_path = Path(public_root).resolve(strict=False)
    acceptance_path = (
        Path(acceptance_out)
        if acceptance_out is not None
        else public_root_path / ACCEPTANCE_RECEIPT_REL
    )
    if not acceptance_path.is_absolute():
        acceptance_path = Path.cwd() / acceptance_path
    paths = {
        "macro_projection_import_protocol_result": target / RESULT_NAME,
        "projection_import_board": target / BOARD_NAME,
        "projection_import_intake_board": target / INTAKE_BOARD_NAME,
        "projection_import_validation_receipt": target / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = [_display(path, public_root=public_root_path) for path in paths.values()]

    result_receipt = _common_receipt(
        result,
        schema_version="macro_projection_import_protocol_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    board = _common_receipt(
        result,
        schema_version="macro_projection_import_protocol_board_v1",
        receipt_paths=receipt_paths,
    )
    board.update(result["projection_board"])
    intake_board = _common_receipt(
        result,
        schema_version="macro_projection_import_protocol_intake_board_v1",
        receipt_paths=receipt_paths,
    )
    intake_board.update(result["projection_intake_board"])
    validation = _common_receipt(
        result,
        schema_version="macro_projection_import_protocol_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "private_body_import_rejected": "private_body_import_overclaim"
            in result["observed_negative_cases"],
            "omission_receipts_required": "missing_omission_receipt"
            in result["observed_negative_cases"],
            "authority_upgrades_rejected": "authority_upgrade_overclaim"
            in result["observed_negative_cases"],
            "validation_refs_required": "missing_validation_ref"
            in result["observed_negative_cases"],
            "release_and_equivalence_overclaims_rejected": "release_or_private_equivalence_overclaim"
            in result["observed_negative_cases"],
            "projection_intake_board_ref": _display(
                paths["projection_import_intake_board"], public_root=public_root_path
            ),
            "ready_projection_cell_count": result["ready_projection_cell_count"],
            "blocked_projection_cell_count": result["blocked_projection_cell_count"],
            "release_authorized": False,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="macro_projection_import_protocol_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "projection_import_boundary": "metadata_fixture_receipt_ref_import_only",
        }
    )

    write_json_atomic(paths["macro_projection_import_protocol_result"], result_receipt)
    write_json_atomic(paths["projection_import_board"], board)
    write_json_atomic(paths["projection_import_intake_board"], intake_board)
    write_json_atomic(paths["projection_import_validation_receipt"], validation)
    write_json_atomic(paths["fixture_acceptance"], acceptance)
    return {name: _display(path, public_root=public_root_path) for name, path in paths.items()}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.macro_projection_import_protocol run "
        f"--input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    result["receipt_paths"] = list(
        write_receipts(
            out_dir,
            result,
            public_root=_public_root_for_path(input_path),
            acceptance_out=acceptance_out,
        ).values()
    )
    return result


def run_projection_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.macro_projection_import_protocol "
        f"run-projection-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_projection_import_bundle",
        include_negative=False,
    )
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(input_path)
    receipt_path = target / BUNDLE_RESULT_NAME
    result["receipt_paths"] = [_display(receipt_path, public_root=public_root)]
    write_json_atomic(receipt_path, result)
    return result


def preview_import_plan(input_dir: str | Path, command: str | None = None) -> dict[str, Any]:
    input_path = Path(input_dir)
    include_negative = all((input_path / name).is_file() for name in NEGATIVE_INPUT_NAMES)
    command_text = command or (
        "python -m microcosm_core.organs.macro_projection_import_protocol "
        f"plan --input {input_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="first_wave_fixture" if include_negative else "exported_projection_import_bundle",
        include_negative=include_negative,
    )
    return {
        "schema_version": "macro_projection_import_intake_preview_v1",
        "created_at": result["created_at"],
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "validator_id": VALIDATOR_ID,
        "command": command_text,
        "input_mode": result["input_mode"],
        "projection_intake_board": result["projection_intake_board"],
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "release_authorized": False,
        "publication_authorized": False,
        "private_data_equivalence_claim": False,
        "body_redacted": True,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate macro projection import protocol")
    subparsers = parser.add_subparsers(dest="action", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("run-projection-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--input", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out)
    elif args.action == "plan":
        result = preview_import_plan(args.input)
    else:
        result = run_projection_bundle(args.input, args.out)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
