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


ORGAN_ID = "agent_benchmark_integrity_anti_gaming_replay"
FIXTURE_ID = "first_wave.agent_benchmark_integrity_anti_gaming_replay"
VALIDATOR_ID = "validator.microcosm.organs.agent_benchmark_integrity_anti_gaming_replay"

RESULT_NAME = "agent_benchmark_integrity_anti_gaming_replay_result.json"
BOARD_NAME = "agent_benchmark_integrity_anti_gaming_replay_board.json"
VALIDATION_RECEIPT_NAME = (
    "agent_benchmark_integrity_anti_gaming_replay_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "agent_benchmark_integrity_anti_gaming_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_benchmark_integrity_bundle_validation_result.json"

INPUT_NAMES = (
    "projection_protocol.json",
    "locked_evaluator_policy.json",
    "benchmark_cases.json",
    "replay_observations.json",
)
NEGATIVE_INPUT_NAMES = (
    "evaluator_edit_attempt.json",
    "train_test_leakage.json",
    "oracle_patch_body_leakage.json",
    "hidden_gold_access.json",
    "final_answer_only_grading.json",
    "provider_payload_leakage.json",
    "score_overclaim.json",
    "pass_k_cherry_picking.json",
    "misleading_test_admitted.json",
    "private_issue_body_leakage.json",
)

EXPECTED_NEGATIVE_CASES = {
    "evaluator_edit_attempt": ["BENCHMARK_INTEGRITY_EVALUATOR_EDIT_FORBIDDEN"],
    "train_test_leakage": ["BENCHMARK_INTEGRITY_TRAIN_TEST_LEAKAGE"],
    "oracle_patch_body_leakage": ["BENCHMARK_INTEGRITY_ORACLE_PATCH_BODY_FORBIDDEN"],
    "hidden_gold_access": ["BENCHMARK_INTEGRITY_HIDDEN_GOLD_ACCESS"],
    "final_answer_only_grading": ["BENCHMARK_INTEGRITY_FINAL_ANSWER_ONLY_GRADING"],
    "provider_payload_leakage": ["BENCHMARK_INTEGRITY_PROVIDER_PAYLOAD_FORBIDDEN"],
    "score_overclaim": ["BENCHMARK_INTEGRITY_SCORE_OVERCLAIM"],
    "pass_k_cherry_picking": ["BENCHMARK_INTEGRITY_PASS_K_CHERRY_PICKING"],
    "misleading_test_admitted": ["BENCHMARK_INTEGRITY_MISLEADING_TEST_ADMITTED"],
    "private_issue_body_leakage": ["BENCHMARK_INTEGRITY_PRIVATE_ISSUE_BODY_FORBIDDEN"],
}

REQUIRED_REPLAY_FIELDS = (
    "case_id",
    "evaluator_id",
    "evaluator_config_hash",
    "file_access_log_ref",
    "contamination_check_ref",
    "trusted_reference_score_ref",
    "output_replay_ref",
    "integrity_verdict",
)
FORBIDDEN_BODY_KEYS = (
    "private_issue_body",
    "oracle_patch_body",
    "hidden_gold_body",
    "provider_payload",
    "raw_patch_body",
    "test_answer_body",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "synthetic_benchmark_integrity_replay_receipts_only",
    "benchmark_score_claim_authorized": False,
    "swe_bench_performance_claim_authorized": False,
    "hidden_gold_access_authorized": False,
    "oracle_patch_body_export_authorized": False,
    "private_issue_body_export_authorized": False,
    "provider_calls_authorized": False,
    "live_repo_mutation_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Agent benchmark integrity anti-gaming replay validates synthetic evaluator "
    "locking, contamination, file-access, held-out guard, and scoring-boundary "
    "receipts. It does not claim a benchmark score, expose private issue or "
    "oracle patch bodies, run providers, mutate live repositories, or authorize release."
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
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


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


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    public_replacements = _strings(protocol.get("public_replacement_refs"))
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 3
        or "agent_benchmark_integrity_anti_gaming_replay_compound"
        not in source_pattern_ids
        or len(projection_receipts) < 2
        or len(public_replacements) < 3
    ):
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Benchmark integrity projection must cite macro patterns, receipts, and public replacements.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "public_replacement_refs": public_replacements,
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_locked_evaluator_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    locked = set(_strings(policy.get("locked_evaluator_ids")))
    required = set(_strings(policy.get("required_replay_fields")))
    findings: list[dict[str, Any]] = []
    if not locked or not set(REQUIRED_REPLAY_FIELDS).issubset(required):
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_LOCKED_EVALUATOR_POLICY_INCOMPLETE",
                "Policy must declare locked evaluator ids and required replay fields.",
                case_id="locked_evaluator_policy_floor",
                subject_id=str(policy.get("policy_id") or "locked_evaluator_policy"),
                subject_kind="locked_evaluator_policy",
            )
        )
    for field in (
        "provider_calls_authorized",
        "benchmark_score_claim_authorized",
        "release_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_POLICY_AUTHORITY_OVERCLAIM",
                    "Benchmark integrity policy cannot authorize providers, score claims, or release.",
                    case_id="locked_evaluator_policy_floor",
                    subject_id=field,
                    subject_kind="locked_evaluator_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "locked_evaluator_ids": sorted(locked),
        "required_replay_fields": sorted(required),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_benchmark_cases(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "benchmark_cases")
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    for row in rows:
        case_id = str(row.get("case_id") or "")
        if not case_id or not row.get("task_hash") or not row.get("held_out_guard_ids"):
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_CASE_FLOOR_MISSING",
                    "Benchmark cases require case id, task hash, and held-out guard ids.",
                    case_id="benchmark_case_floor",
                    subject_id=case_id or "benchmark_case",
                    subject_kind="benchmark_case",
                )
            )
        if any(key in row for key in FORBIDDEN_BODY_KEYS):
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_CASE_BODY_FORBIDDEN",
                    "Benchmark cases may expose hashes and refs, not private body text.",
                    case_id="benchmark_case_floor",
                    subject_id=case_id or "benchmark_case",
                    subject_kind="benchmark_case",
                )
            )
        exported.append(
            {
                "case_id": case_id,
                "split": row.get("split"),
                "task_hash": row.get("task_hash"),
                "patch_hash": row.get("patch_hash"),
                "held_out_guard_ids": _strings(row.get("held_out_guard_ids")),
                "body_redacted": True,
            }
        )
    return {
        "status": PASS if rows and not findings else "blocked",
        "benchmark_case_count": len(rows),
        "held_out_guard_count": sum(len(row["held_out_guard_ids"]) for row in exported),
        "benchmark_cases": exported,
        "findings": findings,
        "observed_negative_cases": {},
    }


def _validate_replay_row(
    row: dict[str, Any],
    *,
    locked_evaluators: set[str],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> dict[str, Any]:
    case_id = str(row.get("expected_negative_case_id") or row.get("case_id") or "replay")
    replay_id = str(row.get("replay_id") or row.get("case_id") or case_id)
    subject_kind = "negative_case" if negative else "replay_observation"

    missing_fields = [field for field in REQUIRED_REPLAY_FIELDS if not row.get(field)]
    evaluator_id = str(row.get("evaluator_id") or "")
    verdict = str(row.get("integrity_verdict") or "")
    reasons: list[str] = []

    if evaluator_id not in locked_evaluators or row.get("evaluator_mutated") is True:
        reasons.append("evaluator_not_locked")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_EVALUATOR_EDIT_FORBIDDEN",
            "Evaluator ids and configs must be locked before replay.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if row.get("training_material_contains_test_case") is True:
        reasons.append("train_test_leakage")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_TRAIN_TEST_LEAKAGE",
            "Benchmark replay must reject train/test contamination.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if "oracle_patch_body" in row or row.get("oracle_patch_body_present") is True:
        reasons.append("oracle_patch_body")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_ORACLE_PATCH_BODY_FORBIDDEN",
            "Oracle patch bodies may not enter public benchmark replay inputs.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if row.get("hidden_gold_accessed") is True or "hidden_gold_body" in row:
        reasons.append("hidden_gold_access")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_HIDDEN_GOLD_ACCESS",
            "Hidden-gold access invalidates benchmark integrity replay.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if row.get("grading_mode") == "final_answer_only":
        reasons.append("final_answer_only")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_FINAL_ANSWER_ONLY_GRADING",
            "Repository repair benchmarks require replayable patch/test evidence, not final-answer-only grading.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if "provider_payload" in row or row.get("provider_payload_ref") == "raw_provider_payload":
        reasons.append("provider_payload")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_PROVIDER_PAYLOAD_FORBIDDEN",
            "Provider payload bodies are outside the public benchmark replay boundary.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if row.get("benchmark_score_claimed") is True or row.get("metric_claim_authorized") is True:
        reasons.append("score_overclaim")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_SCORE_OVERCLAIM",
            "Synthetic replay receipts cannot claim a benchmark score or capability metric.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if int(row.get("attempt_count") or 1) > 1 and row.get("selected_attempt_policy") == "best_only":
        reasons.append("pass_k_cherry_picking")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_PASS_K_CHERRY_PICKING",
            "Pass@k-style cherry-picking must be labeled and cannot promote a single best replay as the score.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if row.get("misleading_test_admitted") is True:
        reasons.append("misleading_test")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_MISLEADING_TEST_ADMITTED",
            "Misleading tests must be denied or quarantined before benchmark scoring.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if "private_issue_body" in row or row.get("private_issue_body_present") is True:
        reasons.append("private_issue_body")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_PRIVATE_ISSUE_BODY_FORBIDDEN",
            "Private issue bodies may not enter public benchmark replay inputs.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if missing_fields:
        reasons.append("replay_field_missing")
    if row.get("quarantine_reason_ref"):
        reasons.append("quarantine_reason_ref")

    computed_verdict = "integrity_pass"
    if missing_fields or reasons:
        computed_verdict = "quarantine"
    return {
        "replay_id": replay_id,
        "case_id": str(row.get("case_id") or ""),
        "expected_negative_case_id": case_id if negative else None,
        "evaluator_id": evaluator_id,
        "integrity_verdict": verdict or computed_verdict,
        "computed_integrity_verdict": computed_verdict,
        "reason_codes": sorted(set(reasons)),
        "required_field_count": len(REQUIRED_REPLAY_FIELDS),
        "missing_required_fields": missing_fields,
        "file_access_log_ref": row.get("file_access_log_ref"),
        "contamination_check_ref": row.get("contamination_check_ref"),
        "trusted_reference_score_ref": row.get("trusted_reference_score_ref"),
        "body_redacted": True,
    }


def validate_replay_observations(
    payload: object,
    policy: object,
    negative_payloads: dict[str, object],
) -> dict[str, Any]:
    policy_rows = policy if isinstance(policy, dict) else {}
    locked = set(_strings(policy_rows.get("locked_evaluator_ids")))
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    rows: list[dict[str, Any]] = []
    for row in _rows(payload, "replay_observations"):
        rows.append(
            _validate_replay_row(
                row,
                locked_evaluators=locked,
                findings=findings,
                observed=observed,
                negative=False,
            )
        )
    for payload in negative_payloads.values():
        negative_rows = _rows(payload, "replay_observations")
        if isinstance(payload, dict) and not negative_rows:
            negative_rows = [payload]
        for row in negative_rows:
            _validate_replay_row(
                row,
                locked_evaluators=locked,
                findings=findings,
                observed=observed,
                negative=True,
            )

    positive_floor_findings = [
        row
        for row in rows
        if row["computed_integrity_verdict"] == "quarantine"
        and row["integrity_verdict"] == "integrity_pass"
    ]
    return {
        "status": PASS if rows and not positive_floor_findings else "blocked",
        "replay_count": len(rows),
        "integrity_pass_count": sum(
            1 for row in rows if row["computed_integrity_verdict"] == "integrity_pass"
        ),
        "quarantine_count": sum(
            1 for row in rows if row["computed_integrity_verdict"] == "quarantine"
        ),
        "replay_rows": sorted(rows, key=lambda row: row["replay_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
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
    evaluator_policy = validate_locked_evaluator_policy(payloads["locked_evaluator_policy"])
    benchmark_cases = validate_benchmark_cases(payloads["benchmark_cases"])
    observations = validate_replay_observations(
        payloads["replay_observations"],
        payloads["locked_evaluator_policy"],
        {
            name: payloads[name]
            for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
            if name in payloads
        },
    )
    observed = _merge_observed(projection, evaluator_policy, benchmark_cases, observations)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(projection, evaluator_policy, benchmark_cases, observations)
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and private_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and evaluator_policy["status"] == PASS
        and benchmark_cases["status"] == PASS
        and observations["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "agent_benchmark_integrity_anti_gaming_replay_result_v1",
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
        "locked_evaluator_ids": evaluator_policy["locked_evaluator_ids"],
        "benchmark_case_count": benchmark_cases["benchmark_case_count"],
        "held_out_guard_count": benchmark_cases["held_out_guard_count"],
        "replay_count": observations["replay_count"],
        "integrity_pass_count": observations["integrity_pass_count"],
        "quarantine_count": observations["quarantine_count"],
        "benchmark_cases": benchmark_cases["benchmark_cases"],
        "replay_rows": observations["replay_rows"],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "agent_benchmark_integrity_anti_gaming_replay_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "agent_benchmark_integrity_anti_gaming_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "locked_evaluator_before_score",
                "count": len(result["locked_evaluator_ids"]),
                "authority": "evaluator_identity_config_and_file_access_log_required",
            },
            {
                "mechanic_id": "contamination_quarantine",
                "count": result["quarantine_count"],
                "authority": "hidden_gold_oracle_patch_and_train_test_leakage_reject_score_claim",
            },
            {
                "mechanic_id": "no_score_from_replay",
                "count": result["replay_count"],
                "authority": "synthetic_replay_is_integrity_evidence_not_benchmark_metric",
            },
        ],
        "benchmark_cases": result["benchmark_cases"],
        "replay_rows": result["replay_rows"],
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
        "schema_version": "agent_benchmark_integrity_anti_gaming_replay_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "agent_benchmark_integrity_anti_gaming_replay_validation_receipt_v1",
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
        "benchmark_case_count": result["benchmark_case_count"],
        "replay_count": result["replay_count"],
        "integrity_pass_count": result["integrity_pass_count"],
        "quarantine_count": result["quarantine_count"],
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "agent_benchmark_integrity_anti_gaming_replay_fixture_acceptance_v1",
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
    return {**result, "benchmark_integrity_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.agent_benchmark_integrity_anti_gaming_replay run",
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


def run_benchmark_integrity_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.agent_benchmark_integrity_anti_gaming_replay "
        "run-benchmark-integrity-bundle"
    ),
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_benchmark_integrity_bundle",
        include_negative=False,
    )
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_benchmark_integrity_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent_benchmark_integrity_anti_gaming_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    bundle_parser = sub.add_parser("run-benchmark-integrity-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
    elif args.action == "run-benchmark-integrity-bundle":
        result = run_benchmark_integrity_bundle(args.input, args.out)
    else:  # pragma: no cover
        raise ValueError(args.action)
    print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
