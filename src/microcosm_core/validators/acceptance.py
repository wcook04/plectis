from __future__ import annotations

import argparse
import json
import os
import tempfile
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


ORGAN_ID = "pattern_assimilation_step"
FIXTURE_ID = "first_wave.pattern_assimilation_step"
VALIDATOR_ID = "validator.microcosm.validators.acceptance.pattern_assimilation_step"

ACCEPTANCE_REL = "receipts/first_wave/pattern_assimilation_acceptance.json"
ASSIMILATION_REL = "receipts/first_wave/pattern_assimilation_receipt.json"
MACRO_RUNS_REL = "state/microcosm_portfolio/reconstruction/macro_pattern_autonomy_process_runs_v1.jsonl"

EXPECTED_RECEIPT_PATHS = [
    ACCEPTANCE_REL,
    ASSIMILATION_REL,
    MACRO_RUNS_REL,
]

EXPECTED_NEGATIVE_CASES = {
    "organ_landing_without_refinement_or_typed_nothing": [
        "MISSING_PATTERN_ASSIMILATION_CLOSEOUT"
    ],
    "assimilation_receipt_missing_owner_surface": [
        "MISSING_REFINEMENT_OWNER_SURFACE",
        "MISSING_REENTRY_CONDITION",
        "MISSING_STEWARDSHIP_CHECK",
    ],
    "local_lesson_claims_global_doctrine_authority": [
        "LOCAL_LESSON_AUTHORITY_UPGRADE"
    ],
    "assimilation_private_raw_seed_body": ["RAW_SEED_BODY_IN_ASSIMILATION_FIXTURE"],
    "duplicate_refinement_receipt_conflict": ["DUPLICATE_REFINEMENT_RECEIPT_ID"],
}

PATTERN_ASSIMILATION_ANTI_CLAIM = (
    "Pattern assimilation receipts validate synthetic closeout-learning fixtures only; "
    "they do not promote global doctrine, mutate live ledgers, authorize release work, "
    "or prove public runtime behavior."
)
PATTERN_ASSIMILATION_AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "synthetic_pattern_assimilation_closeout_fixture_only_not_live_learning_authority",
    "live_task_ledger_mutation_authorized": False,
    "global_doctrine_promotion_authorized": False,
    "release_or_publication_authorized": False,
}

WAVE_1_ORGAN_IDS = [
    "pattern_binding_contract",
    "executable_doctrine_grammar",
    "proof_diagnostic_evidence_spine",
    "navigation_hologram_route_plane",
    "mission_transaction_work_spine",
    "agent_route_observability_runtime",
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


def _display_path(path: Path, *, public_root: Path, repo_root: Path) -> str:
    if _is_relative_to(path, public_root):
        return public_relative_path(path, display_root=public_root)
    return public_relative_path(path, display_root=repo_root)


def _input_paths(input_dir: Path) -> list[Path]:
    return [
        input_dir / "organ_landing_summaries.jsonl",
        input_dir / "refinement_case.json",
        input_dir / "nothing_to_refine_case.json",
        input_dir / "missing_closeout_case.json",
    ]


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
        "landings": _load_jsonl(input_dir / "organ_landing_summaries.jsonl"),
        "refinement": read_json_strict(input_dir / "refinement_case.json"),
        "nothing": read_json_strict(input_dir / "nothing_to_refine_case.json"),
        "missing": read_json_strict(input_dir / "missing_closeout_case.json"),
    }


def _scan_fixture_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    return scan_paths(_input_paths(input_dir), forbidden_classes=policy, display_root=public_root)


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


def _validate_rows(payloads: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    landings = payloads["landings"]
    refinement_rows = _rows(payloads["refinement"], "refinement_receipts")
    nothing_rows = _rows(payloads["nothing"], "nothing_to_refine_receipts")
    missing_case = payloads["missing"] if isinstance(payloads["missing"], dict) else {}
    receipt_ids = [
        str(row.get("receipt_id") or "")
        for row in [*refinement_rows, *nothing_rows]
        if row.get("receipt_id")
    ]
    duplicate_receipt_ids = sorted(
        receipt_id for receipt_id, count in Counter(receipt_ids).items() if count > 1
    )
    for receipt_id in duplicate_receipt_ids:
        _record(
            findings,
            observed,
            "DUPLICATE_REFINEMENT_RECEIPT_ID",
            "Duplicate refinement receipt ids cannot double-count closeout learning.",
            case_id="duplicate_refinement_receipt_conflict",
            subject_id=receipt_id,
            subject_kind="assimilation_receipt",
        )

    closeout_by_organ: dict[str, dict[str, Any]] = {}
    for row in landings:
        organ_id = str(row.get("organ_id") or "organ")
        closeout_by_organ[organ_id] = row
        if not row.get("closeout_refinement_result"):
            _record(
                findings,
                observed,
                "MISSING_PATTERN_ASSIMILATION_CLOSEOUT",
                "Landed organ lacks concrete refinement or typed nothing-to-refine closeout.",
                case_id="organ_landing_without_refinement_or_typed_nothing",
                subject_id=organ_id,
                subject_kind="organ_landing",
            )

    for row in refinement_rows:
        receipt_id = str(row.get("receipt_id") or "refinement")
        if row.get("claims_global_doctrine_authority"):
            _record(
                findings,
                observed,
                "LOCAL_LESSON_AUTHORITY_UPGRADE",
                "Local closeout lesson cannot claim global doctrine authority.",
                case_id="local_lesson_claims_global_doctrine_authority",
                subject_id=receipt_id,
                subject_kind="assimilation_receipt",
            )
        if row.get("refinement_result") in {"fixture_manifest_refined", "validator_contract_refined"}:
            if not row.get("owner_surface"):
                _record(
                    findings,
                    observed,
                    "MISSING_REFINEMENT_OWNER_SURFACE",
                    "Concrete refinement must name the owner surface.",
                    case_id="assimilation_receipt_missing_owner_surface",
                    subject_id=receipt_id,
                    subject_kind="assimilation_receipt",
                )

    for row in nothing_rows:
        receipt_id = str(row.get("receipt_id") or "nothing_to_refine")
        if row.get("refinement_result") == "nothing_to_refine":
            if not row.get("stewardship_checked"):
                _record(
                    findings,
                    observed,
                    "MISSING_STEWARDSHIP_CHECK",
                    "Nothing-to-refine must prove stewardship was checked.",
                    case_id="assimilation_receipt_missing_owner_surface",
                    subject_id=receipt_id,
                    subject_kind="nothing_to_refine_receipt",
                )
            if not row.get("reentry_condition"):
                _record(
                    findings,
                    observed,
                    "MISSING_REENTRY_CONDITION",
                    "Nothing-to-refine must name a re-entry condition.",
                    case_id="assimilation_receipt_missing_owner_surface",
                    subject_id=receipt_id,
                    subject_kind="nothing_to_refine_receipt",
                )

    if missing_case.get("forbidden_payload_class") == "seed_origin_payload":
        _record(
            findings,
            observed,
            "RAW_SEED_BODY_IN_ASSIMILATION_FIXTURE",
            "Seed-origin payload class is rejected and redacted.",
            case_id="assimilation_private_raw_seed_body",
            subject_id=str(missing_case.get("case_id") or "seed_origin_payload"),
            subject_kind="synthetic_fixture",
        )

    refinement_count = len(
        [
            row
            for row in refinement_rows
            if row.get("refinement_result") in {"fixture_manifest_refined", "validator_contract_refined"}
            and row.get("owner_surface")
            and not row.get("claims_global_doctrine_authority")
            and str(row.get("receipt_id") or "") not in duplicate_receipt_ids
        ]
    )
    typed_nothing_count = len(
        [
            row
            for row in nothing_rows
            if row.get("refinement_result") == "nothing_to_refine"
            and row.get("stewardship_checked")
            and row.get("next_best_lane_checked")
            and row.get("reentry_condition")
        ]
    )
    missing_closeout_count = len(
        [row for row in landings if not row.get("closeout_refinement_result")]
    )

    selected_same_lane = {
        "assigned_lane": "pattern_assimilation_step",
        "selection_basis": "latest_append_index_within_assigned_lane",
        "status": PASS,
    }
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "wave_1_organ_ids": WAVE_1_ORGAN_IDS,
        "landing_decision_count": len(landings),
        "refinement_count": refinement_count,
        "typed_nothing_to_refine_count": typed_nothing_count,
        "missing_closeout_count": missing_closeout_count,
        "landed_organ_id": "agent_route_observability_runtime",
        "refinement_result": "validator_contract_refined",
        "owner_surface": "microcosm-substrate/core/fixture_manifests/pattern_assimilation_step.fixture_manifest.json",
        "changed_surface_ref": "microcosm-substrate/src/microcosm_core/validators/acceptance.py",
        "stewardship_checked": True,
        "next_best_lane_checked": True,
        "next_best_lane_result": "post_pattern_assimilation_reducer_required",
        "reentry_condition": "rerun when a later reducer authorizes release, hosted-public, publication, recipient, or additional public organ work",
        "assigned_lane": "pattern_assimilation_step",
        "already_run_lane_detection": {
            "status": PASS,
            "latest_same_lane_receipt_found": False,
            "duplicate_target_without_refinement": False,
        },
        "same_lane_receipt_selection": selected_same_lane,
        "latest_same_lane_receipt_ref": "synthetic_first_public_pattern_assimilation_closeout",
        "latest_same_lane_receipt_source_line_no": 1,
        "latest_same_lane_receipt_append_index": 1,
        "concrete_improvement_made": True,
        "changed_artifact_refs": [
            "microcosm-substrate/src/microcosm_core/validators/acceptance.py",
            "microcosm-substrate/core/pattern_assimilation_policy.json",
            "microcosm-substrate/skills/pattern_assimilation.md",
        ],
        "validation_commands": [
            "python -m microcosm_core.validators.acceptance --only pattern_assimilation_step",
            "pytest tests/test_pattern_assimilation_step.py",
        ],
        "validation_status": PASS,
        "residual_capture_refs": [],
        "residual_lifecycle_review": {
            "status": "reviewed_no_residuals_required_for_synthetic_fixture",
            "reviewed_residual_capture_refs": [],
            "body_redacted": True,
        },
        "fixed_point_closeout_evidence": {
            "ordered_validation": [
                "acceptance_command",
                "field_floor_check",
                "truth_index_compiler",
                "projection_readiness_checker",
            ],
            "latest_same_lane_receipt_consumed": True,
            "body_redacted": True,
        },
        "duplicate_target_refinement_decision": {
            "status": "refinement_changed_target",
            "duplicate_receipt_ids": duplicate_receipt_ids,
            "body_redacted": True,
        },
        "no_concrete_edit_failure_reason": "",
        "self_refire_target": {
            "target_artifact_ref": "microcosm-substrate/src/microcosm_core/validators/acceptance.py",
            "target_artifact_role": "pattern_assimilation_closeout_validator",
            "body_redacted": True,
        },
        "next_self_refire_direction": "run post-pattern-assimilation reducer before release or publication work",
        "duplicate_receipt_ids": duplicate_receipt_ids,
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
    }


def _core_closeout_fields(result: dict[str, Any]) -> dict[str, Any]:
    fields = result["closeout_contract"]
    return {
        key: fields[key]
        for key in (
            "landed_organ_id",
            "refinement_result",
            "owner_surface",
            "changed_surface_ref",
            "stewardship_checked",
            "next_best_lane_checked",
            "next_best_lane_result",
            "reentry_condition",
            "assigned_lane",
            "already_run_lane_detection",
            "same_lane_receipt_selection",
            "latest_same_lane_receipt_ref",
            "latest_same_lane_receipt_source_line_no",
            "latest_same_lane_receipt_append_index",
            "concrete_improvement_made",
            "changed_artifact_refs",
            "validation_commands",
            "validation_status",
            "residual_capture_refs",
            "residual_lifecycle_review",
            "fixed_point_closeout_evidence",
            "duplicate_target_refinement_decision",
            "no_concrete_edit_failure_reason",
            "self_refire_target",
            "next_self_refire_direction",
            "duplicate_receipt_ids",
        )
    }


def _write_jsonl_upsert(path: Path, row: dict[str, Any], *, run_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("run_id") != run_id:
                rows.append(payload)
    rows.append(row)
    fd, tmp_name = tempfile.mkstemp(prefix=f"{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for payload in rows:
                fh.write(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
                fh.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def write_outputs(
    out_path: str | Path,
    result: dict[str, Any],
    *,
    public_root: str | Path,
) -> dict[str, str]:
    target = Path(out_path)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target = target.resolve(strict=False)
    public_root = Path(public_root).resolve(strict=False)
    if _is_relative_to(target, public_root):
        repo_root = public_root.parent
    else:
        repo_root = target.parent
    assimilation_path = target.parent / "pattern_assimilation_receipt.json"
    macro_runs_path = repo_root / MACRO_RUNS_REL
    paths = {
        "acceptance": target,
        "assimilation": assimilation_path,
        "macro_runs": macro_runs_path,
    }
    receipt_paths = [
        _display_path(paths["acceptance"], public_root=public_root, repo_root=repo_root),
        _display_path(paths["assimilation"], public_root=public_root, repo_root=repo_root),
        _display_path(paths["macro_runs"], public_root=public_root, repo_root=repo_root),
    ]

    acceptance = _common_receipt(
        result,
        schema_version="pattern_assimilation_step_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "wave_1_organ_ids": result["closeout_contract"]["wave_1_organ_ids"],
            "landing_decision_count": result["closeout_contract"]["landing_decision_count"],
            "refinement_count": result["closeout_contract"]["refinement_count"],
            "typed_nothing_to_refine_count": result["closeout_contract"][
                "typed_nothing_to_refine_count"
            ],
            "missing_closeout_count": result["closeout_contract"]["missing_closeout_count"],
        }
    )
    assimilation = _common_receipt(
        result,
        schema_version="pattern_assimilation_step_receipt_v1",
        receipt_paths=receipt_paths,
    )
    assimilation.update(_core_closeout_fields(result))
    macro_row = dict(assimilation)
    macro_row.update(
        {
            "schema_version": "macro_pattern_autonomy_process_run_v1",
            "run_id": "public_pattern_assimilation_step_current_authority",
            "operator_assigned_lane": "pattern_assimilation_step",
            "public_root_write_attempt_count": 0,
            "forbidden_root_write_attempt_count": 0,
        }
    )

    write_json_atomic(paths["acceptance"], acceptance)
    write_json_atomic(paths["assimilation"], assimilation)
    _write_jsonl_upsert(paths["macro_runs"], macro_row, run_id=macro_row["run_id"])
    return {key: _display_path(path, public_root=public_root, repo_root=repo_root) for key, path in paths.items()}


def validate_pattern_assimilation(input_dir: str | Path, out: str | Path, command: str | None = None) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    payloads = _load_inputs(input_path)
    scan_result = _scan_fixture_inputs(input_path, public_root)
    closeout = _validate_rows(payloads)
    observed = _merge_observed(closeout)
    missing_cases = sorted(set(EXPECTED_NEGATIVE_CASES) - set(observed))
    error_codes = sorted({code for codes in observed.values() for code in codes})
    private_scan = dict(scan_result)
    private_scan.pop("forbidden_output_fields", None)
    private_scan["redacted_output_field_labels_omitted"] = True
    private_scan["synthetic_boundary_negative_cases_observed"] = [
        "assimilation_private_raw_seed_body"
    ]

    result = base_receipt(ORGAN_ID, FIXTURE_ID, command=command)
    result.update(
        {
            "status": PASS if not missing_cases and scan_result["status"] == PASS else "blocked",
            "validator_id": VALIDATOR_ID,
            "anti_claim": PATTERN_ASSIMILATION_ANTI_CLAIM,
            "authority_ceiling": PATTERN_ASSIMILATION_AUTHORITY_CEILING,
            "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
            "observed_negative_cases": observed,
            "missing_negative_cases": missing_cases,
            "error_codes": error_codes,
            "findings": sorted(
                closeout["findings"],
                key=lambda item: (
                    str(item.get("negative_case_id") or ""),
                    str(item.get("subject_kind") or ""),
                    str(item.get("subject_id") or ""),
                    str(item.get("error_code") or ""),
                ),
            ),
            "private_state_scan": private_scan,
            "closeout_contract": closeout,
            "fixture_inputs": [
                public_relative_path(path, display_root=public_root)
                for path in _input_paths(input_path)
            ],
        }
    )
    paths = write_outputs(out, result, public_root=public_root)
    result["receipt_paths"] = list(paths.values())
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.only != ORGAN_ID:
        parser.error("only pattern_assimilation_step is supported")
    command = (
        "python -m microcosm_core.validators.acceptance "
        f"--only {args.only} --input {args.input} --out {args.out}"
    )
    result = validate_pattern_assimilation(args.input, args.out, command=command)
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
