from __future__ import annotations

import argparse
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


ORGAN_ID = "formal_math_verifier_trace_repair_loop"
FIXTURE_ID = "first_wave.formal_math_verifier_trace_repair_loop"
VALIDATOR_ID = "validator.microcosm.organs.formal_math_verifier_trace_repair_loop"

RESULT_NAME = "formal_math_verifier_trace_repair_loop_result.json"
BOARD_NAME = "verifier_trace_repair_board.json"
VALIDATION_RECEIPT_NAME = "formal_math_verifier_trace_repair_loop_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "formal_math_verifier_trace_repair_loop_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_verifier_trace_repair_bundle_validation_result.json"

INPUT_NAMES = (
    "projection_protocol.json",
    "verifier_attempts.json",
    "repair_curriculum.json",
    "promotion_policy.json",
)
NEGATIVE_INPUT_NAMES = (
    "attempt_with_proof_body.json",
    "attempt_with_oracle_ids.json",
    "trace_grade_without_trace.json",
    "repair_without_verifier_class.json",
    "promotion_without_cold_rerun.json",
    "provider_payload_leakage.json",
    "human_approval_as_proof.json",
)

EXPECTED_NEGATIVE_CASES = {
    "attempt_with_proof_body": ["VERIFIER_TRACE_PROOF_BODY_FORBIDDEN"],
    "attempt_with_oracle_ids": ["VERIFIER_TRACE_ORACLE_IDS_FORBIDDEN"],
    "trace_grade_without_trace": ["VERIFIER_TRACE_GRADE_WITHOUT_TRACE"],
    "repair_without_verifier_class": ["VERIFIER_REPAIR_WITHOUT_VERIFIER_CLASS"],
    "promotion_without_cold_rerun": ["VERIFIER_PROMOTION_WITHOUT_COLD_RERUN"],
    "provider_payload_leakage": ["VERIFIER_PROVIDER_PAYLOAD_FORBIDDEN"],
    "human_approval_as_proof": ["VERIFIER_HUMAN_APPROVAL_NOT_PROOF_AUTHORITY"],
}

FORBIDDEN_PROOF_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "candidate_proof_body",
    "private_source_body",
)
FORBIDDEN_ORACLE_KEYS = (
    "oracle_needed_premise_ids",
    "oracle_premise_ids",
    "ground_truth_premise_ids",
)
FORBIDDEN_PROVIDER_KEYS = (
    "provider_output_body",
    "provider_payload_body",
    "raw_provider_payload",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_synthetic_verifier_trace_repair_metadata_only",
    "lean_lake_execution_authorized": False,
    "formal_proof_authority": False,
    "provider_calls_authorized": False,
    "proof_bodies_allowed": False,
    "oracle_premise_ids_allowed": False,
    "human_approval_as_proof_authority": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Formal math verifier-trace repair loop validates a public synthetic replay "
    "of verifier feedback, trace grading, repair actions, failure-mode ledger "
    "updates, curriculum deltas, and cold rerun promotion gates. It does not run "
    "Lean or Lake, call providers, expose proof bodies or oracle premise ids, "
    "treat human or provider advice as proof correctness, prove theorem "
    "correctness, or authorize release."
)


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


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    bundle_manifest = input_dir / "bundle_manifest.json"
    if bundle_manifest.is_file():
        paths.append(bundle_manifest)
    return paths


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
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


def _forbidden_keys(row: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    return sorted(key for key in keys if key in row)


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    public_replacements = _strings(protocol.get("public_replacement_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    omitted = _rows(protocol, "omitted_material")
    findings: list[dict[str, Any]] = []
    if len(source_refs) < 4 or len(source_pattern_ids) < 3 or len(public_replacements) < 3:
        findings.append(
            _finding(
                "VERIFIER_TRACE_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Verifier trace repair projection must cite macro source refs, pattern ids, and public replacements.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    for row in omitted:
        if not row.get("omission_receipt_ref"):
            findings.append(
                _finding(
                    "VERIFIER_TRACE_OMISSION_RECEIPT_MISSING",
                    "Omitted proof/oracle/provider material must carry an omission receipt.",
                    case_id="projection_protocol_floor",
                    subject_id=str(row.get("material_id") or "omitted_material"),
                    subject_kind="projection_protocol",
                )
            )
    return {
        "status": PASS
        if source_refs
        and source_pattern_ids
        and projection_receipts
        and public_replacements
        and not findings
        else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "public_replacement_refs": public_replacements,
        "omitted_material_count": len(omitted),
        "findings": findings,
        "observed_negative_cases": {},
    }


def _inspect_attempt_row(
    row: dict[str, Any],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> None:
    attempt_id = str(row.get("attempt_id") or row.get("case_id") or "attempt")
    case_id = str(row.get("expected_negative_case_id") or attempt_id)
    subject_kind = "negative_case" if negative else "verifier_attempt"
    if _forbidden_keys(row, FORBIDDEN_PROOF_KEYS):
        _record(
            findings,
            observed,
            "VERIFIER_TRACE_PROOF_BODY_FORBIDDEN",
            "Verifier trace rows may name a failure class but may not expose proof bodies.",
            case_id=case_id,
            subject_id=attempt_id,
            subject_kind=subject_kind,
        )
    if _forbidden_keys(row, FORBIDDEN_ORACLE_KEYS):
        _record(
            findings,
            observed,
            "VERIFIER_TRACE_ORACLE_IDS_FORBIDDEN",
            "Verifier trace rows may not expose oracle-needed premise ids.",
            case_id=case_id,
            subject_id=attempt_id,
            subject_kind=subject_kind,
        )
    if _forbidden_keys(row, FORBIDDEN_PROVIDER_KEYS):
        _record(
            findings,
            observed,
            "VERIFIER_PROVIDER_PAYLOAD_FORBIDDEN",
            "Verifier trace rows may cite provider advice as advisory metadata only, not provider payload bodies.",
            case_id=case_id,
            subject_id=attempt_id,
            subject_kind=subject_kind,
        )
    if row.get("trace_grade") and not _rows(row, "trace_events"):
        _record(
            findings,
            observed,
            "VERIFIER_TRACE_GRADE_WITHOUT_TRACE",
            "Trace grades require public trace event metadata.",
            case_id=case_id,
            subject_id=attempt_id,
            subject_kind=subject_kind,
        )
    if row.get("repair_action_id") and not row.get("verifier_class"):
        _record(
            findings,
            observed,
            "VERIFIER_REPAIR_WITHOUT_VERIFIER_CLASS",
            "Repair actions must be grounded in a verifier failure class.",
            case_id=case_id,
            subject_id=attempt_id,
            subject_kind=subject_kind,
        )
    if row.get("promoted_after_cold_rerun") is True and not row.get("cold_rerun_receipt_ref"):
        _record(
            findings,
            observed,
            "VERIFIER_PROMOTION_WITHOUT_COLD_RERUN",
            "Promotion requires a public cold rerun receipt reference.",
            case_id=case_id,
            subject_id=attempt_id,
            subject_kind=subject_kind,
        )
    if row.get("human_approval_claims_proof_correctness") is True:
        _record(
            findings,
            observed,
            "VERIFIER_HUMAN_APPROVAL_NOT_PROOF_AUTHORITY",
            "Human approval is advisory until a checker receipt exists.",
            case_id=case_id,
            subject_id=attempt_id,
            subject_kind=subject_kind,
        )


def validate_verifier_attempts(
    payload: object,
    negative_payloads: dict[str, object],
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for row in _rows(payload, "attempts"):
        _inspect_attempt_row(row, findings=findings, observed=observed, negative=False)
        trace_events = _rows(row, "trace_events")
        if not row.get("verifier_class") or not trace_events:
            findings.append(
                _finding(
                    "VERIFIER_ATTEMPT_TRACE_INCOMPLETE",
                    "Each public attempt must carry a verifier class and trace event metadata.",
                    case_id="attempt_floor",
                    subject_id=str(row.get("attempt_id") or "attempt"),
                    subject_kind="verifier_attempt",
                )
            )
        attempts.append(
            {
                "attempt_id": str(row.get("attempt_id") or ""),
                "statement_id": row.get("statement_id"),
                "public_input_hash": row.get("public_input_hash"),
                "verifier_class": row.get("verifier_class"),
                "trace_grade": row.get("trace_grade"),
                "repair_action_id": row.get("repair_action_id"),
                "failure_mode_id": row.get("failure_mode_id"),
                "cold_rerun_receipt_ref": row.get("cold_rerun_receipt_ref"),
                "promoted_after_cold_rerun": row.get("promoted_after_cold_rerun") is True,
                "trace_event_count": len(trace_events),
                "body_redacted": True,
            }
        )
    for payload in negative_payloads.values():
        rows = _rows(payload, "attempts")
        if isinstance(payload, dict) and not rows:
            rows = [payload]
        for row in rows:
            _inspect_attempt_row(row, findings=findings, observed=observed, negative=True)
    return {
        "status": PASS if len(attempts) >= 3 and not any(
            row.get("negative_case_id") == "attempt_floor" for row in findings
        ) else "blocked",
        "attempt_count": len(attempts),
        "trace_event_count": sum(int(row["trace_event_count"]) for row in attempts),
        "repair_action_count": sum(1 for row in attempts if row.get("repair_action_id")),
        "cold_rerun_promotion_count": sum(
            1 for row in attempts if row.get("promoted_after_cold_rerun")
        ),
        "attempts": sorted(attempts, key=lambda row: row["attempt_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_repair_curriculum(payload: object) -> dict[str, Any]:
    ledger_rows = _rows(payload, "failure_mode_ledger")
    curriculum_edges = _rows(payload, "curriculum_edges")
    findings: list[dict[str, Any]] = []
    for row in ledger_rows:
        if row.get("accepted_after_cold_rerun") is True and not row.get("cold_rerun_receipt_ref"):
            findings.append(
                _finding(
                    "VERIFIER_LEDGER_APPEND_WITHOUT_COLD_RERUN",
                    "Failure-mode curriculum updates require a cold rerun receipt.",
                    case_id="repair_curriculum_floor",
                    subject_id=str(row.get("failure_mode_id") or "failure_mode"),
                    subject_kind="repair_curriculum",
                )
            )
    return {
        "status": PASS if ledger_rows and curriculum_edges and not findings else "blocked",
        "failure_mode_count": len(ledger_rows),
        "curriculum_edge_count": len(curriculum_edges),
        "failure_mode_ledger": [
            {
                "failure_mode_id": row.get("failure_mode_id"),
                "verifier_class": row.get("verifier_class"),
                "repair_action_id": row.get("repair_action_id"),
                "accepted_after_cold_rerun": row.get("accepted_after_cold_rerun") is True,
                "cold_rerun_receipt_ref": row.get("cold_rerun_receipt_ref"),
                "body_redacted": True,
            }
            for row in ledger_rows
        ],
        "curriculum_edges": [
            {
                "from_failure_mode_id": row.get("from_failure_mode_id"),
                "to_curriculum_node_id": row.get("to_curriculum_node_id"),
                "delta_class": row.get("delta_class"),
                "body_redacted": True,
            }
            for row in curriculum_edges
        ],
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_promotion_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    findings: list[dict[str, Any]] = []
    if policy.get("formal_proof_authority") is True:
        findings.append(
            _finding(
                "VERIFIER_POLICY_PROOF_AUTHORITY_OVERCLAIM",
                "The repair loop policy cannot claim theorem proof authority.",
                case_id="promotion_policy_floor",
                subject_id=str(policy.get("policy_id") or "promotion_policy"),
                subject_kind="promotion_policy",
            )
        )
    required = _strings(policy.get("promotion_requires"))
    return {
        "status": PASS if "cold_rerun_receipt_ref" in required and not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "promotion_requires": required,
        "human_or_provider_advice_authority": policy.get("human_or_provider_advice_authority"),
        "findings": findings,
        "observed_negative_cases": {},
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

    projection = validate_projection_protocol(payloads["projection_protocol"])
    attempts = validate_verifier_attempts(
        payloads["verifier_attempts"],
        {
            name: payloads[name]
            for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
            if name in payloads
        },
    )
    curriculum = validate_repair_curriculum(payloads["repair_curriculum"])
    promotion = validate_promotion_policy(payloads["promotion_policy"])

    observed = _merge_observed(projection, attempts, curriculum, promotion)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(projection, attempts, curriculum, promotion)
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and private_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and attempts["status"] == PASS
        and curriculum["status"] == PASS
        and promotion["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "formal_math_verifier_trace_repair_loop_result_v1",
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
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "public_replacement_refs": projection["public_replacement_refs"],
        "attempt_count": attempts["attempt_count"],
        "trace_event_count": attempts["trace_event_count"],
        "repair_action_count": attempts["repair_action_count"],
        "cold_rerun_promotion_count": attempts["cold_rerun_promotion_count"],
        "failure_mode_count": curriculum["failure_mode_count"],
        "curriculum_edge_count": curriculum["curriculum_edge_count"],
        "verifier_attempts": attempts["attempts"],
        "failure_mode_ledger": curriculum["failure_mode_ledger"],
        "curriculum_edges": curriculum["curriculum_edges"],
        "promotion_policy": {
            "policy_id": promotion["policy_id"],
            "promotion_requires": promotion["promotion_requires"],
            "human_or_provider_advice_authority": promotion[
                "human_or_provider_advice_authority"
            ],
        },
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "formal_math_verifier_trace_repair_loop_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "formal_math_verifier_trace_repair_loop_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "verifier_feedback_trace",
                "count": result["trace_event_count"],
                "authority": "teaching_signal_not_proof_result",
            },
            {
                "mechanic_id": "repair_action_gate",
                "count": result["repair_action_count"],
                "authority": "repair_metadata_requires_verifier_class",
            },
            {
                "mechanic_id": "cold_rerun_promotion",
                "count": result["cold_rerun_promotion_count"],
                "authority": "promotion_requires_cold_rerun_receipt",
            },
            {
                "mechanic_id": "curriculum_delta",
                "count": result["curriculum_edge_count"],
                "authority": "failure_mode_ledger_delta_not_theorem_correctness",
            },
        ],
        "verifier_attempts": result["verifier_attempts"],
        "failure_mode_ledger": result["failure_mode_ledger"],
        "curriculum_edges": result["curriculum_edges"],
        "formal_proof_authority": False,
        "body_redacted": True,
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(out_dir)
    board = _board_from_result(result)
    result_path = out_dir / RESULT_NAME
    board_path = out_dir / BOARD_NAME
    validation_path = out_dir / VALIDATION_RECEIPT_NAME
    acceptance_path = (
        acceptance_out
        if acceptance_out is not None
        else public_root / ACCEPTANCE_RECEIPT_REL
    )
    acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
        _display(acceptance_path, public_root=public_root),
    ]
    result_receipt = {
        **result,
        "schema_version": "formal_math_verifier_trace_repair_loop_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**board, "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "formal_math_verifier_trace_repair_loop_validation_receipt_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "negative_case_coverage": {
            "expected": result["expected_negative_cases"],
            "observed": result["observed_negative_cases"],
            "missing": result["missing_negative_cases"],
        },
        "trace_attempt_count": result["attempt_count"],
        "repair_action_count": result["repair_action_count"],
        "cold_rerun_promotion_count": result["cold_rerun_promotion_count"],
        "formal_proof_authority": False,
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "formal_math_verifier_trace_repair_loop_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "verifier_trace_repair_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.formal_math_verifier_trace_repair_loop run",
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_loop_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.formal_math_verifier_trace_repair_loop "
        "run-loop-bundle"
    ),
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_verifier_trace_repair_bundle",
        include_negative=False,
    )
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_verifier_trace_repair_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="formal_math_verifier_trace_repair_loop")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    bundle_parser = sub.add_parser("run-loop-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(
            args.input,
            args.out,
            command=(
                "python -m microcosm_core.organs.formal_math_verifier_trace_repair_loop "
                f"run --input {args.input} --out {args.out}"
            ),
        )
    elif args.action == "run-loop-bundle":
        result = run_loop_bundle(
            args.input,
            args.out,
            command=(
                "python -m microcosm_core.organs.formal_math_verifier_trace_repair_loop "
                f"run-loop-bundle --input {args.input} --out {args.out}"
            ),
        )
    else:
        return 2
    print_json = __import__("json").dumps
    print(print_json(result, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
