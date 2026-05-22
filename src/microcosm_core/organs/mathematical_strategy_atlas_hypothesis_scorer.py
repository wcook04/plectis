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


ORGAN_ID = "mathematical_strategy_atlas_hypothesis_scorer"
FIXTURE_ID = "first_wave.mathematical_strategy_atlas_hypothesis_scorer"
VALIDATOR_ID = "validator.microcosm.organs.mathematical_strategy_atlas_hypothesis_scorer"

RESULT_NAME = "mathematical_strategy_atlas_result.json"
BOARD_NAME = "mathematical_strategy_atlas_board.json"
VALIDATION_RECEIPT_NAME = "mathematical_strategy_atlas_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "mathematical_strategy_atlas_hypothesis_scorer_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_mathematical_strategy_atlas_bundle_validation_result.json"

SOURCE_PATTERN_IDS = [
    "mathematical_strategy_atlas_hypothesis_scorer",
]

SOURCE_REFS = [
    "tools/meta/factory/run_prover_graph_benchmark.py",
    "tools/meta/factory/reduce_prover_provider_receipts.py",
]

UNKNOWN_STRATEGY_ID = "unknown"

FORBIDDEN_BODY_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "lean_source_body",
    "provider_output_body",
)

ORACLE_LABEL_KEYS = (
    "oracle_strategy_id",
    "oracle_label",
    "needed_strategy_id",
    "ground_truth_strategy_id",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "strategy_hypothesis_projection_not_substrate_or_proof_authority",
    "lean_lake_execution_authorized": False,
    "mathlib_dependent_proof_authority": False,
    "formal_proof_authority": False,
    "oracle_label_visibility_authorized": False,
    "provider_calls_authorized": False,
    "test_split_tuning_authorized": False,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Mathematical strategy atlas projection is a drilldown regression surface "
    "for public pre-oracle strategy hypotheses and retrieval lenses only. It is "
    "not a Microcosm product organ, does not import a macro substrate body, does "
    "not run Lean or Lake, prove theorem correctness, expose proof bodies or "
    "oracle labels, tune on test answers, call providers, or authorize release."
)

EXPECTED_NEGATIVE_CASES = {
    "unknown_strategy_id": ["MATH_STRATEGY_UNKNOWN_ID"],
    "proof_body_with_strategy": ["MATH_STRATEGY_PROOF_BODY_FORBIDDEN"],
    "oracle_strategy_label_leakage": ["MATH_STRATEGY_ORACLE_LABEL_FORBIDDEN"],
    "post_oracle_strategy_selection": ["MATH_STRATEGY_POST_ORACLE_SELECTION_FORBIDDEN"],
    "release_overclaim": ["MATH_STRATEGY_RELEASE_OVERCLAIM"],
}

INPUT_NAMES = (
    "strategy_atlas.json",
    "problem_features.json",
    "hypothesis_cases.json",
)

NEGATIVE_INPUT_NAMES = (
    "unknown_strategy_id.json",
    "proof_body_with_strategy.json",
    "oracle_strategy_label_leakage.json",
    "post_oracle_strategy_selection.json",
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
    return findings


def _feature_set(row: dict[str, Any]) -> set[str]:
    values = row.get("feature_tags", [])
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values if isinstance(value, str)}


def _strategy_rows(payload: object) -> list[dict[str, Any]]:
    rows = _rows(payload, "strategies")
    return [row for row in rows if str(row.get("strategy_id") or "")]


def _atlas_by_id(payload: object) -> dict[str, dict[str, Any]]:
    return {str(row["strategy_id"]): row for row in _strategy_rows(payload)}


def _feature_overlap_count(problem_features: set[str], strategy: dict[str, Any]) -> int:
    match_features = {
        str(value)
        for value in strategy.get("match_features", [])
        if isinstance(value, str)
    }
    return len(problem_features & match_features)


def _score_case(
    case: dict[str, Any],
    *,
    problem_by_id: dict[str, dict[str, Any]],
    atlas_by_id: dict[str, dict[str, Any]],
    strategy_order: list[str],
) -> dict[str, Any]:
    case_id = str(case.get("case_id") or "case")
    problem_id = str(case.get("problem_id") or "")
    problem = problem_by_id.get(problem_id, {})
    problem_features = _feature_set(problem)
    candidate_ids = [
        str(value)
        for value in case.get("candidate_strategy_ids", strategy_order)
        if isinstance(value, str)
    ]
    candidate_ids = [strategy_id for strategy_id in candidate_ids if strategy_id != UNKNOWN_STRATEGY_ID]
    scored: list[tuple[int, int, str]] = []
    for strategy_id in candidate_ids:
        strategy = atlas_by_id.get(strategy_id)
        if strategy is None:
            continue
        order = strategy_order.index(strategy_id) if strategy_id in strategy_order else len(strategy_order)
        scored.append((_feature_overlap_count(problem_features, strategy), -order, strategy_id))
    selected_strategy_id = UNKNOWN_STRATEGY_ID
    feature_overlap_count = 0
    if scored:
        feature_overlap_count, _, selected_strategy_id = max(scored)
        if feature_overlap_count <= 0:
            selected_strategy_id = UNKNOWN_STRATEGY_ID
    selected = atlas_by_id.get(selected_strategy_id, {})
    classifier = (
        "matched_strategy"
        if selected_strategy_id != UNKNOWN_STRATEGY_ID
        else "STRATEGY_SELECTION_MISS"
    )
    retrieval_terms = [
        str(value)
        for value in selected.get("retrieval_term_additions", [])
        if isinstance(value, str)
    ]
    expected = str(case.get("expected_strategy_id") or selected_strategy_id)
    return {
        "case_id": case_id,
        "problem_id": problem_id,
        "feature_tags": sorted(problem_features),
        "candidate_strategy_ids": candidate_ids,
        "selected_strategy_id": selected_strategy_id,
        "feature_overlap_count": feature_overlap_count,
        "classifier": classifier,
        "expected_strategy_id": expected,
        "expectation_met": selected_strategy_id == expected,
        "retrieval_term_additions": retrieval_terms,
        "pre_oracle": case.get("pre_oracle") is not False,
        "body_redacted": True,
    }


def validate_strategy_selection(
    atlas_payload: object,
    problems_payload: object,
    cases_payload: object,
    *,
    negative_payloads: dict[str, Any],
) -> dict[str, Any]:
    atlas_by_id = _atlas_by_id(atlas_payload)
    strategy_order = [str(row["strategy_id"]) for row in _strategy_rows(atlas_payload)]
    problem_by_id = {
        str(row.get("problem_id")): row
        for row in _rows(problems_payload, "problems")
        if row.get("problem_id")
    }
    scored_cases = [
        _score_case(
            row,
            problem_by_id=problem_by_id,
            atlas_by_id=atlas_by_id,
            strategy_order=strategy_order,
        )
        for row in _rows(cases_payload, "cases")
    ]

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)

    unknown_negative = negative_payloads.get("unknown_strategy_id")
    if isinstance(unknown_negative, dict):
        case_id = str(
            unknown_negative.get("expected_negative_case_id") or "unknown_strategy_id"
        )
        for row in _rows(unknown_negative, "cases") or [unknown_negative]:
            for strategy_id in row.get("candidate_strategy_ids", []):
                if isinstance(strategy_id, str) and strategy_id not in atlas_by_id:
                    _record(
                        findings,
                        observed,
                        "MATH_STRATEGY_UNKNOWN_ID",
                        "Strategy selection referenced a strategy id outside the public enum.",
                        case_id=case_id,
                        subject_id=strategy_id,
                        subject_kind="strategy_id",
                    )

    proof_negative = negative_payloads.get("proof_body_with_strategy")
    if isinstance(proof_negative, dict):
        case_id = str(
            proof_negative.get("expected_negative_case_id") or "proof_body_with_strategy"
        )
        for row in _rows(proof_negative, "cases") or [proof_negative]:
            forbidden = _forbidden_body_keys(row)
            if forbidden:
                _record(
                    findings,
                    observed,
                    "MATH_STRATEGY_PROOF_BODY_FORBIDDEN",
                    "Strategy classification cannot carry proof, provider, or source body fields.",
                    case_id=case_id,
                    subject_id=str(row.get("case_id") or "strategy_case"),
                    subject_kind="strategy_case",
                )

    oracle_negative = negative_payloads.get("oracle_strategy_label_leakage")
    if isinstance(oracle_negative, dict):
        case_id = str(
            oracle_negative.get("expected_negative_case_id")
            or "oracle_strategy_label_leakage"
        )
        for row in _rows(oracle_negative, "problems") or _rows(oracle_negative, "cases") or [oracle_negative]:
            leaked = sorted(key for key in ORACLE_LABEL_KEYS if key in row)
            if leaked:
                _record(
                    findings,
                    observed,
                    "MATH_STRATEGY_ORACLE_LABEL_FORBIDDEN",
                    "Pre-oracle public strategy fixtures cannot expose oracle strategy labels.",
                    case_id=case_id,
                    subject_id=str(row.get("problem_id") or row.get("case_id") or "strategy_fixture"),
                    subject_kind="oracle_label",
                )

    post_oracle_negative = negative_payloads.get("post_oracle_strategy_selection")
    if isinstance(post_oracle_negative, dict):
        case_id = str(
            post_oracle_negative.get("expected_negative_case_id")
            or "post_oracle_strategy_selection"
        )
        for row in _rows(post_oracle_negative, "cases") or [post_oracle_negative]:
            selection_stage = str(row.get("selection_stage") or "pre_oracle")
            if row.get("pre_oracle") is False or selection_stage.startswith("post"):
                _record(
                    findings,
                    observed,
                    "MATH_STRATEGY_POST_ORACLE_SELECTION_FORBIDDEN",
                    "Strategy must be selected before oracle labels or proof outcomes are visible.",
                    case_id=case_id,
                    subject_id=str(row.get("case_id") or "strategy_case"),
                    subject_kind="selection_stage",
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
                "test_split_tuning_authorized",
            )
            if release_negative.get(field) is True
        ]
        if overclaim_fields:
            _record(
                findings,
                observed,
                "MATH_STRATEGY_RELEASE_OVERCLAIM",
                "Strategy projection attempted to authorize release, proof authority, providers, or test tuning.",
                case_id=case_id,
                subject_id=",".join(sorted(overclaim_fields)),
                subject_kind="authority_ceiling",
            )

    return {
        "strategy_ids": strategy_order,
        "strategy_count": len(strategy_order),
        "problem_count": len(problem_by_id),
        "hypothesis_case_count": len(scored_cases),
        "scored_cases": sorted(scored_cases, key=lambda item: item["case_id"]),
        "selected_strategy_ids": sorted(
            {row["selected_strategy_id"] for row in scored_cases}
        ),
        "strategy_selection_miss_case_ids": sorted(
            row["case_id"]
            for row in scored_cases
            if row["classifier"] == "STRATEGY_SELECTION_MISS"
        ),
        "all_expectations_met": all(row["expectation_met"] for row in scored_cases),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _build_board(*, result: dict[str, Any], private_scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "mathematical_strategy_atlas_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "selected_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "public_contract": {
            "strategy_selected_pre_oracle": True,
            "strategy_is_hypothesis_not_proof": True,
            "drilldown_regression_not_product_organ": True,
            "known_strategy_ids_only": True,
            "unknown_strategy_is_typed_miss": True,
            "proof_bodies_excluded": True,
            "oracle_labels_excluded": True,
            "body_redacted": True,
        },
        "strategy_projection": {
            "strategy_count": result["strategy_count"],
            "strategy_ids": result["strategy_ids"],
            "problem_count": result["problem_count"],
            "hypothesis_case_count": result["hypothesis_case_count"],
            "selected_strategy_ids": result["selected_strategy_ids"],
            "strategy_selection_miss_case_ids": result[
                "strategy_selection_miss_case_ids"
            ],
            "scored_cases": result["scored_cases"],
            "body_redacted": True,
        },
        "private_state_scan": private_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
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

    scoring = validate_strategy_selection(
        payloads["strategy_atlas"],
        payloads["problem_features"],
        payloads["hypothesis_cases"],
        negative_payloads=negative_payloads,
    )
    observed = _merge_observed(scoring)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(scoring)
    error_codes = sorted({finding["error_code"] for finding in findings})
    status = (
        PASS
        if not missing
        and not private_scan["blocking_hit_count"]
        and scoring["all_expectations_met"]
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
        "schema_version": "mathematical_strategy_atlas_hypothesis_scorer_result_v1",
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
        "strategy_ids": scoring["strategy_ids"],
        "strategy_count": scoring["strategy_count"],
        "problem_count": scoring["problem_count"],
        "hypothesis_case_count": scoring["hypothesis_case_count"],
        "scored_cases": scoring["scored_cases"],
        "selected_strategy_ids": scoring["selected_strategy_ids"],
        "strategy_selection_miss_case_ids": scoring["strategy_selection_miss_case_ids"],
        "all_expectations_met": scoring["all_expectations_met"],
        "body_redacted": True,
    }
    result["strategy_board"] = _build_board(result=result, private_scan=private_scan)
    return result


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
        "strategy_ids",
        "strategy_count",
        "problem_count",
        "hypothesis_case_count",
        "selected_strategy_ids",
        "strategy_selection_miss_case_ids",
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
        schema_version="mathematical_strategy_atlas_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    result_receipt.update(
        {
            "scored_cases": result["scored_cases"],
            "strategy_board": result["strategy_board"],
        }
    )
    board_receipt = _common_receipt(
        result,
        schema_version="mathematical_strategy_atlas_board_receipt_v1",
        receipt_paths=receipt_paths,
    )
    board_payload = dict(result["strategy_board"])
    board_receipt["board_schema_version"] = board_payload.pop("schema_version")
    board_receipt.update(board_payload)
    validation = _common_receipt(
        result,
        schema_version="mathematical_strategy_atlas_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "strategy_selected_pre_oracle": True,
            "proof_bodies_excluded": True,
            "oracle_labels_excluded": True,
            "known_strategy_ids_only": True,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="mathematical_strategy_atlas_fixture_acceptance_v1",
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
        "python -m microcosm_core.organs.mathematical_strategy_atlas_hypothesis_scorer run "
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


def run_strategy_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.mathematical_strategy_atlas_hypothesis_scorer "
        f"run-strategy-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_mathematical_strategy_atlas_bundle",
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
        schema_version="mathematical_strategy_atlas_exported_bundle_receipt_v1",
        receipt_paths=[receipt_ref],
    )
    receipt.update(
        {
            "scored_cases": result["scored_cases"],
            "strategy_board": result["strategy_board"],
        }
    )
    write_json_atomic(receipt_path, receipt)
    result["receipt_paths"] = [receipt_ref]
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate mathematical strategy atlas hypothesis scoring"
    )
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("run-strategy-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out)
    elif args.action == "run-strategy-bundle":
        result = run_strategy_bundle(args.input, args.out)
    else:
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
