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


ORGAN_ID = "formal_math_readiness_gate"
FIXTURE_ID = "first_wave.formal_math_readiness_gate"
VALIDATOR_ID = "validator.microcosm.organs.formal_math_readiness_gate"

READINESS_RESULT_NAME = "readiness_gate_result.json"
READINESS_BOARD_NAME = "formal_math_readiness_board.json"
VALIDATION_RECEIPT_NAME = "formal_math_readiness_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/formal_math_readiness_gate_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_formal_math_readiness_bundle_validation_result.json"

FORBIDDEN_BODY_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "provider_output_body",
    "oracle_needed_premise_ids",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "formal_math_readiness_metadata_only_not_lean_or_formal_proof_authority",
    "lean_lake_execution_authorized": False,
    "mathlib_presence_claim_authorized": False,
    "formal_proof_authority": False,
    "provider_calls_authorized": False,
    "proof_bodies_allowed": False,
}
ANTI_CLAIM = (
    "Formal math readiness gate validates public synthetic readiness metadata only. "
    "It does not run Lean or Lake, call providers, expose proof bodies, prove theorem "
    "correctness, authorize Mathlib-dependent proofs, or change the deferred "
    "formal_math_lean_proof_witness boundary."
)

EXPECTED_NEGATIVE_CASES = {
    "corpus_readiness_overclaims_mathlib": ["MATHLIB_AVAILABILITY_OVERCLAIM"],
    "tactic_availability_without_probe": ["TACTIC_AVAILABILITY_UNPROBED"],
    "premise_index_proof_body_forbidden": ["PREMISE_INDEX_PROOF_BODY_FORBIDDEN"],
    "routing_allows_unavailable_tactic": ["ROUTING_ALLOWS_UNAVAILABLE_TACTIC"],
    "provider_context_recipe_overclaim": [
        "PROVIDER_RECIPE_BUDGET_EXCEEDED",
        "PROVIDER_RECIPE_PROOF_BODY_FORBIDDEN",
    ],
}

INPUT_NAMES = (
    "corpus_readiness.json",
    "tactic_portfolio_availability.json",
    "premise_index.json",
    "target_shape_tactic_routing.json",
    "provider_context_recipes.json",
)

NEGATIVE_INPUT_NAMES = (
    "corpus_readiness_overclaims_mathlib.json",
    "tactic_claims_availability_without_probe.json",
    "premise_index_with_proof_body.json",
    "routing_allows_unavailable_tactic.json",
    "provider_context_recipe_overclaim.json",
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


def _forbidden_body_keys(row: dict[str, Any]) -> list[str]:
    return sorted(key for key in FORBIDDEN_BODY_KEYS if key in row)


def validate_corpus_readiness(
    payload: object,
    negative_payload: object | None = None,
) -> dict[str, Any]:
    rows = _rows(payload, "corpora")
    blocked_capabilities: list[str] = []
    corpus_rows: list[dict[str, Any]] = []
    for row in rows:
        corpus_id = str(row.get("corpus_id") or "corpus")
        mathlib_available = row.get("mathlib_available") is True
        mathlib_probe_status = str(row.get("mathlib_probe_status") or "unknown")
        if not mathlib_available:
            blocked_capabilities.append(f"{corpus_id}:mathlib")
        corpus_rows.append(
            {
                "corpus_id": corpus_id,
                "lean_available": row.get("lean_available") is True,
                "mathlib_available": mathlib_available,
                "mathlib_probe_status": mathlib_probe_status,
                "translation_smoke_only": row.get("translation_smoke_only") is True,
                "consumer_rule": row.get("consumer_rule"),
                "body_redacted": True,
            }
        )

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if isinstance(negative_payload, dict):
        subject_id = str(negative_payload.get("corpus_id") or "corpus_readiness")
        case_id = str(
            negative_payload.get("expected_negative_case_id")
            or "corpus_readiness_overclaims_mathlib"
        )
        overclaims = (
            negative_payload.get("claims_mathlib_available") is True
            or (
                negative_payload.get("mathlib_available") is True
                and negative_payload.get("mathlib_probe_status") != "PASS"
            )
        )
        if overclaims:
            _record(
                findings,
                observed,
                "MATHLIB_AVAILABILITY_OVERCLAIM",
                "Corpus readiness attempted to claim Mathlib availability without a passing probe.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="corpus_readiness",
            )
    return {
        "corpora": sorted(corpus_rows, key=lambda item: item["corpus_id"]),
        "blocked_capabilities": sorted(blocked_capabilities),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_tactic_portfolio(
    payload: object,
    negative_payload: object | None = None,
) -> dict[str, Any]:
    tactics: list[dict[str, Any]] = []
    available: list[str] = []
    unavailable: list[str] = []
    for row in _rows(payload, "tactics"):
        tactic_id = str(row.get("tactic_id") or "")
        status = str(row.get("availability_status") or "unknown")
        if status == PASS:
            available.append(tactic_id)
        else:
            unavailable.append(tactic_id)
        tactics.append(
            {
                "tactic_id": tactic_id,
                "availability_status": status,
                "probe_receipt_ref": row.get("probe_receipt_ref"),
                "failure_class": row.get("failure_class"),
                "body_redacted": True,
            }
        )

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if isinstance(negative_payload, dict):
        subject_id = str(negative_payload.get("tactic_id") or "tactic")
        case_id = str(
            negative_payload.get("expected_negative_case_id")
            or "tactic_availability_without_probe"
        )
        if negative_payload.get("claims_available") is True and not negative_payload.get(
            "probe_receipt_ref"
        ):
            _record(
                findings,
                observed,
                "TACTIC_AVAILABILITY_UNPROBED",
                "Tactic availability was claimed without a probe receipt.",
                case_id=case_id,
                subject_id=subject_id,
                subject_kind="tactic_availability",
            )
    return {
        "tactics": sorted(tactics, key=lambda item: item["tactic_id"]),
        "available_tactic_ids": sorted(tactic for tactic in available if tactic),
        "unavailable_tactic_ids": sorted(tactic for tactic in unavailable if tactic),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_premise_index(
    payload: object,
    negative_payload: object | None = None,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for row in _rows(payload, "premises"):
        entries.append(
            {
                "premise_id": row.get("premise_id"),
                "namespace": row.get("namespace"),
                "retrieval_term_count": len(row.get("retrieval_terms", []))
                if isinstance(row.get("retrieval_terms"), list)
                else 0,
                "allowed_for_split": row.get("allowed_for_split", []),
                "source_ref": row.get("source_ref"),
                "body_redacted": True,
            }
        )

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if isinstance(negative_payload, dict):
        case_id = str(
            negative_payload.get("expected_negative_case_id")
            or "premise_index_proof_body_forbidden"
        )
        for row in _rows(negative_payload, "premises"):
            premise_id = str(row.get("premise_id") or "premise")
            forbidden = _forbidden_body_keys(row)
            if forbidden:
                _record(
                    findings,
                    observed,
                    "PREMISE_INDEX_PROOF_BODY_FORBIDDEN",
                    "Premise index included forbidden proof/oracle body fields.",
                    case_id=case_id,
                    subject_id=premise_id,
                    subject_kind="premise_index",
                )
    return {
        "premise_count": len(entries),
        "premises": sorted(entries, key=lambda item: str(item["premise_id"])),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_target_shape_routing(
    payload: object,
    *,
    unavailable_tactic_ids: list[str],
    negative_payload: object | None = None,
) -> dict[str, Any]:
    unavailable = set(unavailable_tactic_ids)
    cases: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)

    def add_case(row: dict[str, Any], *, negative: bool) -> None:
        route_case_id = str(row.get("route_case_id") or "route_case")
        allowed = [str(item) for item in row.get("allowed_tactic_ids", []) if isinstance(item, str)]
        blocked = sorted(set(allowed) & unavailable)
        cases.append(
            {
                "route_case_id": route_case_id,
                "target_shape": row.get("target_shape"),
                "allowed_tactic_ids": allowed,
                "blocked_unavailable_tactic_ids": blocked,
                "body_redacted": True,
            }
        )
        if negative and blocked:
            _record(
                findings,
                observed,
                "ROUTING_ALLOWS_UNAVAILABLE_TACTIC",
                "Target-shape routing allowed a tactic marked unavailable by the portfolio probe.",
                case_id=str(
                    row.get("expected_negative_case_id") or "routing_allows_unavailable_tactic"
                ),
                subject_id=route_case_id,
                subject_kind="target_shape_routing",
            )

    for row in _rows(payload, "route_cases"):
        add_case(row, negative=False)
    if isinstance(negative_payload, dict):
        for row in _rows(negative_payload, "route_cases"):
            add_case(row, negative=True)
    return {
        "route_case_count": len(cases),
        "route_cases": sorted(cases, key=lambda item: item["route_case_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_provider_context_recipes(
    payload: object,
    negative_payload: object | None = None,
) -> dict[str, Any]:
    recipes: list[dict[str, Any]] = []
    for row in _rows(payload, "recipes"):
        recipes.append(
            {
                "recipe_id": row.get("recipe_id"),
                "byte_budget": row.get("byte_budget"),
                "deliverable_type": row.get("deliverable_type"),
                "section_count": len(row.get("sections", []))
                if isinstance(row.get("sections"), list)
                else 0,
                "proof_bodies_allowed": row.get("proof_bodies_allowed") is True,
                "provider_calls_authorized": row.get("provider_calls_authorized") is True,
                "body_redacted": True,
            }
        )

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if isinstance(negative_payload, dict):
        case_id = str(
            negative_payload.get("expected_negative_case_id")
            or "provider_context_recipe_overclaim"
        )
        for row in _rows(negative_payload, "recipes"):
            recipe_id = str(row.get("recipe_id") or "recipe")
            if int(row.get("byte_budget") or 0) > 32768:
                _record(
                    findings,
                    observed,
                    "PROVIDER_RECIPE_BUDGET_EXCEEDED",
                    "Provider context recipe exceeded the public readiness byte ceiling.",
                    case_id=case_id,
                    subject_id=recipe_id,
                    subject_kind="provider_context_recipe",
                )
            if row.get("proof_bodies_allowed") is True or _forbidden_body_keys(row):
                _record(
                    findings,
                    observed,
                    "PROVIDER_RECIPE_PROOF_BODY_FORBIDDEN",
                    "Provider context recipe allowed or embedded proof body material.",
                    case_id=case_id,
                    subject_id=recipe_id,
                    subject_kind="provider_context_recipe",
                )
    return {
        "recipes": sorted(recipes, key=lambda item: str(item["recipe_id"])),
        "recipe_count": len(recipes),
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

    corpus = validate_corpus_readiness(
        payloads["corpus_readiness"],
        payloads.get("corpus_readiness_overclaims_mathlib"),
    )
    tactics = validate_tactic_portfolio(
        payloads["tactic_portfolio_availability"],
        payloads.get("tactic_claims_availability_without_probe"),
    )
    premise_index = validate_premise_index(
        payloads["premise_index"],
        payloads.get("premise_index_with_proof_body"),
    )
    routing = validate_target_shape_routing(
        payloads["target_shape_tactic_routing"],
        unavailable_tactic_ids=tactics["unavailable_tactic_ids"],
        negative_payload=payloads.get("routing_allows_unavailable_tactic"),
    )
    recipes = validate_provider_context_recipes(
        payloads["provider_context_recipes"],
        payloads.get("provider_context_recipe_overclaim"),
    )

    observed = _merge_observed(corpus, tactics, premise_index, routing, recipes)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(corpus, tactics, premise_index, routing, recipes)
    error_codes = sorted({finding["error_code"] for finding in findings})
    status = PASS if not missing and not private_scan["blocking_hit_count"] else "blocked"
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    return {
        "schema_version": "formal_math_readiness_gate_result_v1",
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
        "corpus_readiness": corpus["corpora"],
        "blocked_capabilities": corpus["blocked_capabilities"],
        "available_tactic_ids": tactics["available_tactic_ids"],
        "unavailable_tactic_ids": tactics["unavailable_tactic_ids"],
        "premise_count": premise_index["premise_count"],
        "route_case_count": routing["route_case_count"],
        "recipe_count": recipes["recipe_count"],
        "readiness_board": {
            "mathlib_available": not corpus["blocked_capabilities"],
            "lean_lake_execution_authorized": False,
            "formal_proof_authority": False,
            "provider_calls_authorized": False,
            "blocked_capabilities": corpus["blocked_capabilities"],
            "available_tactic_ids": tactics["available_tactic_ids"],
            "unavailable_tactic_ids": tactics["unavailable_tactic_ids"],
            "route_case_count": routing["route_case_count"],
            "premise_count": premise_index["premise_count"],
            "next_boundary": "formal_math_lean_proof_witness remains deferred until a later witness slice changes the boundary with validation receipts",
            "body_redacted": True,
        },
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
        "blocked_capabilities",
        "available_tactic_ids",
        "unavailable_tactic_ids",
        "premise_count",
        "route_case_count",
        "recipe_count",
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
        "readiness_gate_result": target / READINESS_RESULT_NAME,
        "formal_math_readiness_board": target / READINESS_BOARD_NAME,
        "formal_math_readiness_validation_receipt": target / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = _relative_receipt_paths(paths, public_root_path)

    gate_result = _common_receipt(
        result,
        schema_version="formal_math_readiness_gate_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    gate_result.update(
        {
            "corpus_readiness": result["corpus_readiness"],
            "readiness_board": result["readiness_board"],
        }
    )
    board = _common_receipt(
        result,
        schema_version="formal_math_readiness_gate_board_v1",
        receipt_paths=receipt_paths,
    )
    board.update(result["readiness_board"])
    validation = _common_receipt(
        result,
        schema_version="formal_math_readiness_gate_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "authority_boundary_retained": True,
            "proof_bodies_excluded": True,
            "lean_lake_execution_authorized": False,
            "provider_calls_authorized": False,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="formal_math_readiness_gate_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "deferred_organ_id": "formal_math_lean_proof_witness",
            "lean_witness_deferred": True,
        }
    )

    write_json_atomic(paths["readiness_gate_result"], gate_result)
    write_json_atomic(paths["formal_math_readiness_board"], board)
    write_json_atomic(paths["formal_math_readiness_validation_receipt"], validation)
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
        "python -m microcosm_core.organs.formal_math_readiness_gate run "
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


def run_readiness_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.formal_math_readiness_gate "
        f"run-readiness-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_formal_math_readiness_bundle",
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
        schema_version="formal_math_readiness_gate_exported_bundle_receipt_v1",
        receipt_paths=[receipt_ref],
    )
    receipt.update(
        {
            "readiness_board": result["readiness_board"],
            "corpus_readiness": result["corpus_readiness"],
        }
    )
    write_json_atomic(receipt_path, receipt)
    result["receipt_paths"] = [receipt_ref]
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate formal math readiness metadata")
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("run-readiness-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out)
    elif args.action == "run-readiness-bundle":
        result = run_readiness_bundle(args.input, args.out)
    else:
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
