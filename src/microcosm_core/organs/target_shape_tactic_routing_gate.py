from __future__ import annotations

import argparse
import json
from collections import defaultdict
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


ORGAN_ID = "target_shape_tactic_routing_gate"
FIXTURE_ID = "first_wave.target_shape_tactic_routing_gate"
VALIDATOR_ID = "validator.microcosm.organs.target_shape_tactic_routing_gate"

RESULT_NAME = "target_shape_tactic_routing_result.json"
BOARD_NAME = "target_shape_tactic_routing_board.json"
VALIDATION_RECEIPT_NAME = "target_shape_tactic_routing_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "target_shape_tactic_routing_gate_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_target_shape_tactic_routing_bundle_validation_result.json"

SOURCE_PATTERN_IDS = ["target_shape_tactic_routing_gate"]
SOURCE_REFS = [
    "state/runs/PROVER_STATEMENT_ONLY_HAMMER_BANDIT_20260511_v0/hammer_action_manifest.json",
    "state/runs/PROVER_STATEMENT_ONLY_HAMMER_BANDIT_20260511_v0/hammer_action_value_table.json",
]

FORBIDDEN_BODY_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "lean_source_body",
    "provider_output_body",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "target_shape_admissibility_metadata_not_proof_authority",
    "lean_lake_execution_authorized": False,
    "mathlib_dependent_proof_authority": False,
    "formal_proof_authority": False,
    "provider_calls_authorized": False,
    "post_execution_routing_authorized": False,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Target-shape tactic routing validates public pre-execution admissibility "
    "metadata only. It rejects unavailable, unprobed, or shape-inadmissible "
    "tactics before any Lean call; it does not run Lean/Lake, prove the goal, "
    "emit proof bodies, call providers, or authorize release."
)

EXPECTED_NEGATIVE_CASES = {
    "unavailable_tactic_admitted": ["TARGET_SHAPE_UNAVAILABLE_TACTIC_ADMITTED"],
    "unprobed_tactic_allowed": ["TARGET_SHAPE_UNPROBED_TACTIC_ALLOWED"],
    "proof_body_leakage": ["TARGET_SHAPE_PROOF_BODY_FORBIDDEN"],
    "post_execution_route": ["TARGET_SHAPE_POST_EXECUTION_ROUTE_FORBIDDEN"],
    "release_overclaim": ["TARGET_SHAPE_RELEASE_OVERCLAIM"],
}

INPUT_NAMES = (
    "tactic_portfolio_availability.json",
    "target_shape_routes.json",
)

NEGATIVE_INPUT_NAMES = (
    "unavailable_tactic_admitted.json",
    "unprobed_tactic_allowed.json",
    "proof_body_leakage.json",
    "post_execution_route.json",
    "release_overclaim.json",
)

NEGATIVE_INPUT_NAMES_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return {Path(name).stem: read_json_strict(input_dir / name) for name in names}


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names]


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _availability_status(row: dict[str, Any]) -> str:
    for key in ("availability_status", "compile_status", "status"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return "unknown"


def _tactic_rows(payload: object) -> list[dict[str, Any]]:
    rows = _rows(payload, "tactics")
    if rows:
        return rows
    return _rows(payload, "rows")


def _portfolio(payload: object) -> dict[str, Any]:
    rows = _tactic_rows(payload)
    available: list[str] = []
    unavailable: list[str] = []
    known: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        tactic_id = str(row.get("tactic_id") or "")
        if not tactic_id:
            continue
        known.append(tactic_id)
        by_id[tactic_id] = row
        status = _availability_status(row)
        if status in {"available", "pass", "compiled", "compile_pass"}:
            available.append(tactic_id)
        else:
            unavailable.append(tactic_id)
    return {
        "tactic_count": len(known),
        "known_tactic_ids": sorted(known),
        "available_tactic_ids": sorted(available),
        "unavailable_tactic_ids": sorted(unavailable),
        "tactics_by_id": by_id,
    }


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


def _forbidden_body_keys(row: dict[str, Any]) -> list[str]:
    return sorted(key for key in FORBIDDEN_BODY_KEYS if key in row)


def _route_cases(payload: object) -> list[dict[str, Any]]:
    return _rows(payload, "route_cases")


def _decision_for_tactic(
    tactic_id: str,
    *,
    allowed: set[str],
    known: set[str],
    available: set[str],
) -> dict[str, Any]:
    if tactic_id not in known:
        return {
            "tactic_id": tactic_id,
            "decision": "reject",
            "classifier": "UNPROBED_TACTIC",
            "reason": "tactic is not present in the declared public probe portfolio",
        }
    if tactic_id not in available:
        return {
            "tactic_id": tactic_id,
            "decision": "reject",
            "classifier": "UNAVAILABLE_TACTIC",
            "reason": "tactic is known but unavailable in the declared environment",
        }
    if tactic_id not in allowed:
        return {
            "tactic_id": tactic_id,
            "decision": "reject",
            "classifier": "TARGET_SHAPE_ADMISSIBILITY_REJECTED",
            "reason": "tactic is available but not admissible for this target shape",
        }
    return {
        "tactic_id": tactic_id,
        "decision": "allow",
        "classifier": "TARGET_SHAPE_ADMISSIBLE",
        "reason": "tactic is probed, available, and listed for this target shape",
    }


def _score_case(
    row: dict[str, Any],
    *,
    known: set[str],
    available: set[str],
    unavailable: set[str],
) -> dict[str, Any]:
    route_case_id = str(row.get("route_case_id") or "route_case")
    allowed = set(_strings(row.get("allowed_tactic_ids")))
    candidates = _strings(row.get("candidate_tactic_ids"))
    if not candidates:
        candidates = sorted(allowed | set(_strings(row.get("rejected_tactic_ids"))))
    decisions = [
        _decision_for_tactic(
            tactic_id,
            allowed=allowed,
            known=known,
            available=available,
        )
        for tactic_id in candidates
    ]
    selected = str(row.get("selected_tactic_id") or row.get("expected_tactic_id") or "")
    if not selected:
        selected = next(
            (
                decision["tactic_id"]
                for decision in decisions
                if decision["decision"] == "allow"
            ),
            "",
        )
    expected = str(row.get("expected_tactic_id") or selected)
    blocked_unavailable = sorted(allowed & unavailable)
    unprobed_allowed = sorted(allowed - known)
    route_stage = str(row.get("route_stage") or "pre_execution")
    integrity_codes: list[str] = []
    if blocked_unavailable:
        integrity_codes.append("TARGET_SHAPE_UNAVAILABLE_TACTIC_ADMITTED")
    if unprobed_allowed:
        integrity_codes.append("TARGET_SHAPE_UNPROBED_TACTIC_ALLOWED")
    if route_stage.startswith("post") or row.get("post_execution") is True:
        integrity_codes.append("TARGET_SHAPE_POST_EXECUTION_ROUTE_FORBIDDEN")
    return {
        "route_case_id": route_case_id,
        "target_shape": str(row.get("target_shape") or ""),
        "allowed_tactic_ids": sorted(allowed),
        "candidate_tactic_ids": sorted(candidates),
        "selected_tactic_id": selected,
        "expected_tactic_id": expected,
        "expectation_met": selected == expected and not integrity_codes,
        "decisions": decisions,
        "blocked_unavailable_tactic_ids": blocked_unavailable,
        "unprobed_allowed_tactic_ids": unprobed_allowed,
        "integrity_codes": sorted(integrity_codes),
        "pre_execution": not integrity_codes
        or "TARGET_SHAPE_POST_EXECUTION_ROUTE_FORBIDDEN" not in integrity_codes,
        "body_redacted": True,
    }


def _route_integrity_findings(scored_cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for case in scored_cases:
        case_id = str(case["route_case_id"])
        for tactic_id in case["blocked_unavailable_tactic_ids"]:
            findings.append(
                _finding(
                    "TARGET_SHAPE_UNAVAILABLE_TACTIC_ADMITTED",
                    "Route admitted a tactic marked unavailable by the public probe.",
                    case_id=case_id,
                    subject_id=tactic_id,
                    subject_kind="tactic_id",
                )
            )
        for tactic_id in case["unprobed_allowed_tactic_ids"]:
            findings.append(
                _finding(
                    "TARGET_SHAPE_UNPROBED_TACTIC_ALLOWED",
                    "Route admitted a tactic that is absent from the public probe portfolio.",
                    case_id=case_id,
                    subject_id=tactic_id,
                    subject_kind="tactic_id",
                )
            )
        if "TARGET_SHAPE_POST_EXECUTION_ROUTE_FORBIDDEN" in case["integrity_codes"]:
            findings.append(
                _finding(
                    "TARGET_SHAPE_POST_EXECUTION_ROUTE_FORBIDDEN",
                    "Target-shape routing must happen before Lean/proof execution evidence.",
                    case_id=case_id,
                    subject_id=case_id,
                    subject_kind="route_stage",
                )
            )
    return findings


def _negative_findings(
    negative_payloads: dict[str, Any],
    *,
    known: set[str],
    unavailable: set[str],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)

    unavailable_negative = negative_payloads.get("unavailable_tactic_admitted")
    if isinstance(unavailable_negative, dict):
        case_id = str(
            unavailable_negative.get("expected_negative_case_id")
            or "unavailable_tactic_admitted"
        )
        for row in _route_cases(unavailable_negative) or [unavailable_negative]:
            for tactic_id in _strings(row.get("allowed_tactic_ids")):
                if tactic_id in unavailable:
                    _record(
                        findings,
                        observed,
                        "TARGET_SHAPE_UNAVAILABLE_TACTIC_ADMITTED",
                        "Route admitted an unavailable tactic before execution.",
                        case_id=case_id,
                        subject_id=tactic_id,
                        subject_kind="tactic_id",
                    )

    unprobed_negative = negative_payloads.get("unprobed_tactic_allowed")
    if isinstance(unprobed_negative, dict):
        case_id = str(
            unprobed_negative.get("expected_negative_case_id")
            or "unprobed_tactic_allowed"
        )
        for row in _route_cases(unprobed_negative) or [unprobed_negative]:
            for tactic_id in _strings(row.get("allowed_tactic_ids")):
                if tactic_id not in known:
                    _record(
                        findings,
                        observed,
                        "TARGET_SHAPE_UNPROBED_TACTIC_ALLOWED",
                        "Route admitted a tactic absent from the public probe portfolio.",
                        case_id=case_id,
                        subject_id=tactic_id,
                        subject_kind="tactic_id",
                    )

    proof_negative = negative_payloads.get("proof_body_leakage")
    if isinstance(proof_negative, dict):
        case_id = str(
            proof_negative.get("expected_negative_case_id") or "proof_body_leakage"
        )
        for row in _route_cases(proof_negative) or [proof_negative]:
            if _forbidden_body_keys(row):
                _record(
                    findings,
                    observed,
                    "TARGET_SHAPE_PROOF_BODY_FORBIDDEN",
                    "Routing fixtures cannot carry proof, provider, or Lean body fields.",
                    case_id=case_id,
                    subject_id=str(row.get("route_case_id") or "route_case"),
                    subject_kind="route_case",
                )

    post_negative = negative_payloads.get("post_execution_route")
    if isinstance(post_negative, dict):
        case_id = str(
            post_negative.get("expected_negative_case_id") or "post_execution_route"
        )
        for row in _route_cases(post_negative) or [post_negative]:
            route_stage = str(row.get("route_stage") or "pre_execution")
            post_markers = (
                route_stage.startswith("post")
                or row.get("post_execution") is True
                or "lean_receipt_ref" in row
                or "execution_result" in row
            )
            if post_markers:
                _record(
                    findings,
                    observed,
                    "TARGET_SHAPE_POST_EXECUTION_ROUTE_FORBIDDEN",
                    "Routing must be selected before proof execution evidence exists.",
                    case_id=case_id,
                    subject_id=str(row.get("route_case_id") or "route_case"),
                    subject_kind="route_stage",
                )

    release_negative = negative_payloads.get("release_overclaim")
    if isinstance(release_negative, dict):
        case_id = str(
            release_negative.get("expected_negative_case_id") or "release_overclaim"
        )
        overclaim_fields = [
            field
            for field in (
                "release_authorized",
                "publication_authorized",
                "formal_proof_authority",
                "provider_calls_authorized",
                "lean_lake_execution_authorized",
            )
            if release_negative.get(field) is True
        ]
        if overclaim_fields:
            _record(
                findings,
                observed,
                "TARGET_SHAPE_RELEASE_OVERCLAIM",
                "Target-shape routing attempted to authorize release, proof authority, providers, or Lean execution.",
                case_id=case_id,
                subject_id=",".join(sorted(overclaim_fields)),
                subject_kind="authority_ceiling",
            )

    return {
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(value) for key, value in observed.items()
        },
    }


def _build_board(*, result: dict[str, Any], private_scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "target_shape_tactic_routing_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "selected_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "public_contract": {
            "routing_pre_execution": True,
            "shape_admissibility_before_search": True,
            "unavailable_tactics_rejected": True,
            "unprobed_tactics_rejected": True,
            "proof_bodies_excluded": True,
            "lean_lake_not_run": True,
            "body_redacted": True,
        },
        "routing_projection": {
            "tactic_count": result["tactic_count"],
            "available_tactic_ids": result["available_tactic_ids"],
            "unavailable_tactic_ids": result["unavailable_tactic_ids"],
            "route_case_count": result["route_case_count"],
            "target_shapes": result["target_shapes"],
            "selected_tactic_ids": result["selected_tactic_ids"],
            "shape_decisions": result["scored_route_cases"],
            "body_redacted": True,
        },
        "private_state_scan": private_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
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
        "source_pattern_ids",
        "source_refs",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "private_state_scan",
        "authority_ceiling",
        "anti_claim",
        "tactic_count",
        "available_tactic_ids",
        "unavailable_tactic_ids",
        "route_case_count",
        "target_shapes",
        "selected_tactic_ids",
        "all_expectations_met",
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


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    return [_display(path, public_root=public_root) for path in paths.values()]


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    negative_payloads = {
        name: payloads[name] for name in NEGATIVE_INPUT_NAMES_STEMS if name in payloads
    }
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    private_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    private_scan.pop("forbidden_output_fields", None)
    private_scan["redacted_output_field_labels_omitted"] = True

    portfolio = _portfolio(payloads["tactic_portfolio_availability"])
    known = set(portfolio["known_tactic_ids"])
    available = set(portfolio["available_tactic_ids"])
    unavailable = set(portfolio["unavailable_tactic_ids"])
    scored_cases = [
        _score_case(
            row,
            known=known,
            available=available,
            unavailable=unavailable,
        )
        for row in _route_cases(payloads["target_shape_routes"])
    ]
    route_findings = _route_integrity_findings(scored_cases)
    negative = _negative_findings(
        negative_payloads,
        known=known,
        unavailable=unavailable,
    )
    observed = negative["observed_negative_cases"]
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = [*route_findings, *negative["findings"]]
    error_codes = sorted({finding["error_code"] for finding in findings})
    all_expectations_met = all(row["expectation_met"] for row in scored_cases)
    status = (
        PASS
        if not missing
        and not route_findings
        and all_expectations_met
        and not private_scan["blocking_hit_count"]
        else "blocked"
    )
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    result = {
        "schema_version": "target_shape_tactic_routing_gate_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "source_refs": SOURCE_REFS,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "private_state_scan": private_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "tactic_count": portfolio["tactic_count"],
        "known_tactic_ids": portfolio["known_tactic_ids"],
        "available_tactic_ids": portfolio["available_tactic_ids"],
        "unavailable_tactic_ids": portfolio["unavailable_tactic_ids"],
        "route_case_count": len(scored_cases),
        "target_shapes": sorted({row["target_shape"] for row in scored_cases}),
        "selected_tactic_ids": sorted(
            {row["selected_tactic_id"] for row in scored_cases if row["selected_tactic_id"]}
        ),
        "scored_route_cases": sorted(
            scored_cases,
            key=lambda item: item["route_case_id"],
        ),
        "all_expectations_met": all_expectations_met,
        "body_redacted": True,
    }
    result["routing_board"] = _build_board(result=result, private_scan=private_scan)
    return result


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
        "result": target / RESULT_NAME,
        "board": target / BOARD_NAME,
        "validation_receipt": target / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = _relative_receipt_paths(paths, public_root_path)

    result_receipt = _common_receipt(
        result,
        schema_version="target_shape_tactic_routing_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    result_receipt.update(
        {
            "scored_route_cases": result["scored_route_cases"],
            "routing_board": result["routing_board"],
        }
    )
    board_receipt = _common_receipt(
        result,
        schema_version="target_shape_tactic_routing_board_receipt_v1",
        receipt_paths=receipt_paths,
    )
    board_payload = dict(result["routing_board"])
    board_receipt["board_schema_version"] = board_payload.pop("schema_version")
    board_receipt.update(board_payload)
    validation = _common_receipt(
        result,
        schema_version="target_shape_tactic_routing_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "routing_pre_execution": True,
            "unavailable_tactics_rejected": True,
            "unprobed_tactics_rejected": True,
            "proof_bodies_excluded": True,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="target_shape_tactic_routing_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "projection_status": "public_replacement_landed"
            if result["status"] == PASS
            else "blocked",
            "authority_boundary_retained": True,
        }
    )

    write_json_atomic(paths["result"], result_receipt)
    write_json_atomic(paths["board"], board_receipt)
    write_json_atomic(paths["validation_receipt"], validation)
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
        "python -m microcosm_core.organs.target_shape_tactic_routing_gate run "
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


def run_routing_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.target_shape_tactic_routing_gate "
        f"run-routing-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_target_shape_tactic_routing_bundle",
        include_negative=False,
    )
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(input_path)
    receipt_path = target / BUNDLE_RESULT_NAME
    receipt_ref = _display(receipt_path, public_root=public_root)
    if Path(receipt_ref).is_absolute() and "receipts" in receipt_path.parts:
        receipts_index = len(receipt_path.parts) - 1 - list(reversed(receipt_path.parts)).index("receipts")
        receipt_ref = Path(*receipt_path.parts[receipts_index:]).as_posix()
    receipt = _common_receipt(
        result,
        schema_version="target_shape_tactic_routing_exported_bundle_receipt_v1",
        receipt_paths=[receipt_ref],
    )
    receipt.update(
        {
            "scored_route_cases": result["scored_route_cases"],
            "routing_board": result["routing_board"],
        }
    )
    write_json_atomic(receipt_path, receipt)
    result["receipt_paths"] = [receipt_ref]
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate target-shape tactic routing before proof execution"
    )
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("run-routing-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out)
    elif args.action == "run-routing-bundle":
        result = run_routing_bundle(args.input, args.out)
    else:
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
