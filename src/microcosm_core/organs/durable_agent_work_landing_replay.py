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


ORGAN_ID = "durable_agent_work_landing_replay"
FIXTURE_ID = "first_wave.durable_agent_work_landing_replay"
VALIDATOR_ID = "validator.microcosm.organs.durable_agent_work_landing_replay"

RESULT_NAME = "durable_agent_work_landing_replay_result.json"
BOARD_NAME = "durable_agent_work_landing_replay_board.json"
VALIDATION_RECEIPT_NAME = "durable_agent_work_landing_replay_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "durable_agent_work_landing_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_work_landing_replay_bundle_validation_result.json"

INPUT_NAMES = (
    "projection_protocol.json",
    "landing_policy.json",
    "work_landing_runs.json",
)
NEGATIVE_INPUT_NAMES = (
    "missing_evidence_ref.json",
    "claim_without_work_ledger_closeout.json",
    "commit_claim_without_head_change.json",
    "live_git_mutation_authorized.json",
    "dirty_tree_boundary_missing.json",
    "uncaptured_blocker.json",
    "release_overclaim.json",
    "private_path_leakage.json",
)

EXPECTED_NEGATIVE_CASES = {
    "missing_evidence_ref": ["WORK_LANDING_EVIDENCE_REF_MISSING"],
    "claim_without_work_ledger_closeout": ["WORK_LANDING_LEDGER_CLOSEOUT_MISSING"],
    "commit_claim_without_head_change": ["WORK_LANDING_HEAD_ADVANCE_MISSING"],
    "live_git_mutation_authorized": ["WORK_LANDING_LIVE_GIT_MUTATION_AUTHORITY"],
    "dirty_tree_boundary_missing": ["WORK_LANDING_DIRTY_TREE_BOUNDARY_MISSING"],
    "uncaptured_blocker": ["WORK_LANDING_BLOCKER_CAPTURE_MISSING"],
    "release_overclaim": ["WORK_LANDING_RELEASE_OVERCLAIM"],
    "private_path_leakage": ["WORK_LANDING_PRIVATE_PATH_LEAKAGE"],
}

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "synthetic_work_landing_replay_receipts_only",
    "live_git_mutation_authorized": False,
    "broad_checkpoint_authorized": False,
    "unrelated_dirty_paths_authorized": False,
    "source_mutation_authorized": False,
    "provider_calls_authorized": False,
    "release_authorized": False,
    "commit_landed_claim_authorized_without_head_advance": False,
}
ANTI_CLAIM = (
    "Durable agent work-landing replay validates synthetic transaction evidence "
    "for owned-path claims, validation receipts, scoped commit attempts, Git "
    "metadata blockers, Task Ledger capture, and Work Ledger finalizers. It does "
    "not mutate Git, stage unrelated dirty paths, prove a commit landed, export "
    "private source bodies, run providers, publish, host, or authorize release."
)
REQUIRED_LANE_IDS = {
    "scoped_commit",
    "broad_checkpoint",
    "metadata_blocked_patch_bundle",
    "hard_stop",
}
FORBIDDEN_BODY_KEYS = (
    "private_source_body",
    "raw_diff_body",
    "provider_payload",
    "secret_value",
    "absolute_private_path",
)
PRIVATE_PATH_MARKERS = ("/Users/", "src/ai_workflow", "/private/")


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


def _walk_keys(payload: object) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def _walk_strings(payload: object) -> list[str]:
    if isinstance(payload, str):
        return [payload]
    if isinstance(payload, dict):
        strings: list[str] = []
        for value in payload.values():
            strings.extend(_walk_strings(value))
        return strings
    if isinstance(payload, list):
        strings: list[str] = []
        for item in payload:
            strings.extend(_walk_strings(item))
        return strings
    return []


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    public_replacements = _strings(protocol.get("public_replacement_refs"))
    findings: list[dict[str, Any]] = []
    if (
        "durable_agent_work_landing_replay_compound" not in source_pattern_ids
        or len(source_refs) < 3
        or len(projection_receipts) < 2
        or len(public_replacements) < 3
    ):
        findings.append(
            _finding(
                "WORK_LANDING_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Work-landing replay projection must cite source patterns, receipts, and public replacements.",
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


def validate_landing_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    lanes = _rows(policy, "lane_decision_table")
    lane_ids = {str(row.get("lane_id") or "") for row in lanes}
    findings: list[dict[str, Any]] = []
    if not REQUIRED_LANE_IDS.issubset(lane_ids):
        findings.append(
            _finding(
                "WORK_LANDING_LANE_TABLE_INCOMPLETE",
                "Landing policy must include scoped commit, broad checkpoint, metadata-blocked, and hard-stop lanes.",
                case_id="landing_policy_floor",
                subject_id=str(policy.get("policy_id") or "landing_policy"),
                subject_kind="landing_policy",
            )
        )
    for row in lanes:
        lane_id = str(row.get("lane_id") or "")
        if lane_id == "broad_checkpoint" and row.get("allowed_without_operator_authorization") is not False:
            findings.append(
                _finding(
                    "WORK_LANDING_BROAD_CHECKPOINT_AUTHORITY_MISSING",
                    "Broad checkpoint lane must require explicit operator authorization.",
                    case_id="landing_policy_floor",
                    subject_id=lane_id,
                    subject_kind="lane_decision",
                )
            )
        if row.get("release_authorized") is not False:
            findings.append(
                _finding(
                    "WORK_LANDING_RELEASE_OVERCLAIM",
                    "Landing lanes cannot authorize release.",
                    case_id="release_overclaim",
                    subject_id=lane_id or "landing_policy",
                    subject_kind="lane_decision",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "lane_ids": sorted(lane_ids),
        "lane_decision_table": lanes,
        "findings": findings,
        "observed_negative_cases": {
            "release_overclaim": ["WORK_LANDING_RELEASE_OVERCLAIM"]
        }
        if any(row.get("release_authorized") is not False for row in lanes)
        else {},
    }


def _validate_run_row(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
    findings: list[dict[str, Any]],
) -> None:
    run_id = str(row.get("run_id") or row.get("case_id") or "work_landing_run")
    validation_refs = _strings(row.get("validation_refs"))
    claimed_paths = _strings(row.get("claimed_path_refs"))
    work_ledger_closeout = str(row.get("work_ledger_closeout_ref") or "")
    blocker_ref = str(row.get("blocker_capture_ref") or "")
    if not validation_refs:
        _record(
            findings,
            observed,
            "WORK_LANDING_EVIDENCE_REF_MISSING",
            "Work landing replay row must cite owner-native validation refs.",
            case_id=case_id,
            subject_id=run_id,
            subject_kind="work_landing_run",
        )
    if not claimed_paths:
        _record(
            findings,
            observed,
            "WORK_LANDING_CLAIMED_PATHS_MISSING",
            "Work landing replay row must cite owned claimed paths.",
            case_id=case_id,
            subject_id=run_id,
            subject_kind="work_landing_run",
        )
    if not work_ledger_closeout:
        _record(
            findings,
            observed,
            "WORK_LANDING_LEDGER_CLOSEOUT_MISSING",
            "Work landing replay row must cite Work Ledger progress or append-exempt finalizer evidence.",
            case_id=case_id,
            subject_id=run_id,
            subject_kind="work_landing_run",
        )
    if row.get("commit_claimed_landed") is True and row.get("head_before") == row.get("head_after"):
        _record(
            findings,
            observed,
            "WORK_LANDING_HEAD_ADVANCE_MISSING",
            "A landed-commit claim requires a HEAD advance.",
            case_id=case_id,
            subject_id=run_id,
            subject_kind="work_landing_run",
        )
    if row.get("live_git_mutation_authorized") is not False:
        _record(
            findings,
            observed,
            "WORK_LANDING_LIVE_GIT_MUTATION_AUTHORITY",
            "Public replay cannot authorize live Git mutation.",
            case_id=case_id,
            subject_id=run_id,
            subject_kind="work_landing_run",
        )
    if row.get("unrelated_dirty_paths_staged") is not False:
        _record(
            findings,
            observed,
            "WORK_LANDING_DIRTY_TREE_BOUNDARY_MISSING",
            "Scoped work landing cannot stage unrelated dirty paths.",
            case_id=case_id,
            subject_id=run_id,
            subject_kind="work_landing_run",
        )
    if row.get("landing_status") == "metadata_blocked_patch_bundle" and not blocker_ref:
        _record(
            findings,
            observed,
            "WORK_LANDING_BLOCKER_CAPTURE_MISSING",
            "Metadata-blocked work landing requires a Task Ledger blocker capture ref.",
            case_id=case_id,
            subject_id=run_id,
            subject_kind="work_landing_run",
        )
    if row.get("release_claim_authorized") is not False:
        _record(
            findings,
            observed,
            "WORK_LANDING_RELEASE_OVERCLAIM",
            "Work landing replay cannot authorize release.",
            case_id=case_id,
            subject_id=run_id,
            subject_kind="work_landing_run",
        )
    if any(key in FORBIDDEN_BODY_KEYS for key in _walk_keys(row)) or any(
        marker in value for value in _walk_strings(row) for marker in PRIVATE_PATH_MARKERS
    ):
        _record(
            findings,
            observed,
            "WORK_LANDING_PRIVATE_PATH_LEAKAGE",
            "Work landing replay must keep private paths and source bodies out of public fixtures.",
            case_id=case_id,
            subject_id=run_id,
            subject_kind="work_landing_run",
        )


def validate_work_landing_runs(
    payload: object,
    negative_payloads: dict[str, Any],
) -> dict[str, Any]:
    rows = _rows(payload, "work_landing_runs")
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        _validate_run_row(row, case_id="positive_fixture_floor", observed=observed, findings=findings)
    positive_findings = list(findings)
    positive_status = PASS if rows and not positive_findings else "blocked"
    findings = []
    observed = defaultdict(set)
    for case_id, payload in negative_payloads.items():
        row = payload if isinstance(payload, dict) else {}
        _validate_run_row(row, case_id=case_id, observed=observed, findings=findings)
    return {
        "status": positive_status,
        "run_count": len(rows),
        "landed_commit_count": sum(1 for row in rows if row.get("commit_claimed_landed") is True),
        "metadata_blocked_count": sum(
            1 for row in rows if row.get("landing_status") == "metadata_blocked_patch_bundle"
        ),
        "work_landing_runs": rows,
        "findings": [*positive_findings, *findings],
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
    landing_policy = validate_landing_policy(payloads["landing_policy"])
    negative_payloads = {
        name: payloads[name]
        for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
        if name in payloads
    }
    landing_runs = validate_work_landing_runs(
        payloads["work_landing_runs"],
        negative_payloads,
    )
    observed = _merge_observed(projection, landing_policy, landing_runs)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(projection, landing_policy, landing_runs)
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and private_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and landing_policy["status"] == PASS
        and landing_runs["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "durable_agent_work_landing_replay_result_v1",
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
        "policy_id": landing_policy["policy_id"],
        "lane_ids": landing_policy["lane_ids"],
        "lane_decision_table": landing_policy["lane_decision_table"],
        "run_count": landing_runs["run_count"],
        "landed_commit_count": landing_runs["landed_commit_count"],
        "metadata_blocked_count": landing_runs["metadata_blocked_count"],
        "work_landing_runs": landing_runs["work_landing_runs"],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "durable_agent_work_landing_replay_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "durable_agent_work_landing_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "claim_before_mutation",
                "count": result["run_count"],
                "authority": "claimed_path_refs_and_validation_refs_required",
            },
            {
                "mechanic_id": "head_advance_before_landed_commit_language",
                "count": result["landed_commit_count"],
                "authority": "commit_claim_requires_head_before_after_change",
            },
            {
                "mechanic_id": "metadata_blocked_patch_bundle",
                "count": result["metadata_blocked_count"],
                "authority": "blocker_capture_and_work_ledger_finalizer_required",
            },
        ],
        "lane_ids": result["lane_ids"],
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
        "schema_version": "durable_agent_work_landing_replay_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "durable_agent_work_landing_replay_validation_receipt_v1",
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
        "run_count": result["run_count"],
        "metadata_blocked_count": result["metadata_blocked_count"],
        "landed_commit_count": result["landed_commit_count"],
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "durable_agent_work_landing_replay_fixture_acceptance_v1",
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
    return {**result, "work_landing_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.durable_agent_work_landing_replay run",
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


def run_work_landing_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.durable_agent_work_landing_replay "
        "run-work-landing-bundle"
    ),
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_work_landing_replay_bundle",
        include_negative=False,
    )
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_work_landing_replay_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="durable_agent_work_landing_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    bundle_parser = sub.add_parser("run-work-landing-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
    elif args.action == "run-work-landing-bundle":
        result = run_work_landing_bundle(args.input, args.out)
    else:  # pragma: no cover
        raise ValueError(args.action)
    print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
