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


ORGAN_ID = "corpus_readiness_mathlib_absence_gate"
FIXTURE_ID = "first_wave.corpus_readiness_mathlib_absence_gate"
VALIDATOR_ID = "validator.microcosm.organs.corpus_readiness_mathlib_absence_gate"

RESULT_NAME = "corpus_readiness_mathlib_absence_gate_result.json"
BOARD_NAME = "corpus_readiness_mathlib_absence_board.json"
VALIDATION_RECEIPT_NAME = "corpus_readiness_mathlib_absence_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "corpus_readiness_mathlib_absence_gate_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_corpus_readiness_bundle_validation_result.json"

SOURCE_PATTERN_IDS = [
    "corpus_readiness_mathlib_absence_gate",
]

SOURCE_REFS = [
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/mathlib_probe.lean",
]

FORBIDDEN_BODY_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "lean_source_body",
    "provider_output_body",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "corpus_readiness_environment_metadata_only_not_mathlib_proof_or_benchmark_authority"
    ),
    "lean_lake_execution_authorized": False,
    "mathlib_lake_project_import_authorized": False,
    "mathlib_dependent_proof_authority": False,
    "formal_proof_authority": False,
    "benchmark_or_corpus_completeness_authority": False,
    "provider_calls_authorized": False,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Corpus readiness Mathlib absence gate validates public fixture metadata only. "
    "It does not run Lean or Lake, prove theorem correctness, claim Mathlib is "
    "available, expose proof bodies, benchmark formal-math corpora, call providers, "
    "or authorize release."
)

EXPECTED_NEGATIVE_CASES = {
    "mathlib_available_without_probe": ["MATHLIB_AVAILABILITY_OVERCLAIM"],
    "consumer_skips_readiness_gate": ["CONSUMER_SKIPS_CORPUS_READINESS_GATE"],
    "private_corpus_source_ref": ["PRIVATE_CORPUS_SOURCE_REF_FORBIDDEN"],
    "proof_body_leakage": ["CORPUS_READINESS_PROOF_BODY_FORBIDDEN"],
    "release_overclaim": ["CORPUS_READINESS_RELEASE_OVERCLAIM"],
}

INPUT_NAMES = (
    "corpus_readiness.json",
    "consumer_gate_cases.json",
)

NEGATIVE_INPUT_NAMES = (
    "mathlib_available_without_probe.json",
    "consumer_skips_readiness_gate.json",
    "private_corpus_source_ref.json",
    "proof_body_leakage.json",
    "release_overclaim.json",
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


def _source_ref_is_private(ref: str) -> bool:
    lowered = ref.lower()
    return (
        ref.startswith("/")
        or ref.startswith("~")
        or "raw_seed" in lowered
        or "operator_thread" in lowered
        or lowered.startswith("private/")
        or "/private/" in lowered
    )


def validate_corpus_readiness(
    payload: object,
    *,
    negative_payloads: dict[str, Any],
) -> dict[str, Any]:
    rows = _rows(payload, "corpora")
    corpus_rows: list[dict[str, Any]] = []
    blocked_capabilities: list[str] = []
    mathlib_import_available = False
    translation_smoke_only_ids: list[str] = []
    absent_corpus_ids: list[str] = []
    source_refs: list[str] = []

    if isinstance(payload, dict):
        source_refs.extend(str(ref) for ref in payload.get("source_refs", []) if isinstance(ref, str))

    for row in rows:
        corpus_id = str(row.get("corpus_id") or "corpus")
        corpus_status = str(row.get("corpus_status") or "available")
        mathlib_probe_status = str(row.get("mathlib_probe_status") or "unknown")
        row_mathlib_available = row.get("mathlib_lake_project_import_available") is True
        if row_mathlib_available and mathlib_probe_status == PASS:
            mathlib_import_available = True
        if not row_mathlib_available:
            blocked_capabilities.append(f"{corpus_id}:mathlib_lake_project_import")
        if row.get("translation_smoke_only") is True:
            translation_smoke_only_ids.append(corpus_id)
        if corpus_status == "absent":
            absent_corpus_ids.append(corpus_id)
            blocked_capabilities.append(f"{corpus_id}:corpus_absent")
        for ref in row.get("source_refs", []):
            if isinstance(ref, str):
                source_refs.append(ref)
        corpus_rows.append(
            {
                "corpus_id": corpus_id,
                "corpus_status": corpus_status,
                "lean_available": row.get("lean_available") is True,
                "mathlib_lake_project_import_available": row_mathlib_available,
                "mathlib_probe_status": mathlib_probe_status,
                "translation_smoke_only": row.get("translation_smoke_only") is True,
                "consumer_rule": row.get("consumer_rule"),
                "body_redacted": True,
            }
        )

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    mathlib_negative = negative_payloads.get("mathlib_available_without_probe")
    if isinstance(mathlib_negative, dict):
        case_id = str(
            mathlib_negative.get("expected_negative_case_id")
            or "mathlib_available_without_probe"
        )
        probe_status = str(mathlib_negative.get("mathlib_probe_status") or "unknown")
        overclaims = (
            mathlib_negative.get("mathlib_lake_project_import_available") is True
            or mathlib_negative.get("claims_mathlib_available") is True
        ) and probe_status != PASS
        if overclaims:
            _record(
                findings,
                observed,
                "MATHLIB_AVAILABILITY_OVERCLAIM",
                "Mathlib availability was claimed without a passing import probe.",
                case_id=case_id,
                subject_id=str(mathlib_negative.get("corpus_id") or "mathlib"),
                subject_kind="corpus_readiness",
            )

    private_ref_negative = negative_payloads.get("private_corpus_source_ref")
    if isinstance(private_ref_negative, dict):
        case_id = str(
            private_ref_negative.get("expected_negative_case_id")
            or "private_corpus_source_ref"
        )
        refs = [
            str(ref)
            for ref in private_ref_negative.get("source_refs", [])
            if isinstance(ref, str)
        ]
        for ref in refs:
            if _source_ref_is_private(ref):
                _record(
                    findings,
                    observed,
                    "PRIVATE_CORPUS_SOURCE_REF_FORBIDDEN",
                    "Corpus readiness source refs must be public-safe metadata refs only.",
                    case_id=case_id,
                    subject_id=ref,
                    subject_kind="source_ref",
                )

    proof_negative = negative_payloads.get("proof_body_leakage")
    if isinstance(proof_negative, dict):
        case_id = str(
            proof_negative.get("expected_negative_case_id") or "proof_body_leakage"
        )
        for row in _rows(proof_negative, "corpora"):
            forbidden = _forbidden_body_keys(row)
            if forbidden:
                _record(
                    findings,
                    observed,
                    "CORPUS_READINESS_PROOF_BODY_FORBIDDEN",
                    "Corpus readiness metadata cannot carry proof or provider body fields.",
                    case_id=case_id,
                    subject_id=str(row.get("corpus_id") or "corpus"),
                    subject_kind="corpus_readiness",
                )

    return {
        "corpora": sorted(corpus_rows, key=lambda item: item["corpus_id"]),
        "corpus_count": len(corpus_rows),
        "blocked_capabilities": sorted(set(blocked_capabilities)),
        "mathlib_lake_project_import_available": mathlib_import_available,
        "translation_smoke_only_ids": sorted(translation_smoke_only_ids),
        "absent_corpus_ids": sorted(absent_corpus_ids),
        "source_refs": sorted(set(source_refs)),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_consumer_gate_cases(
    payload: object,
    *,
    mathlib_available: bool,
    absent_corpus_ids: list[str],
    negative_payloads: dict[str, Any],
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    allowed: list[str] = []
    blocked: list[str] = []
    absent = set(absent_corpus_ids)

    for row in _rows(payload, "cases"):
        case_id = str(row.get("case_id") or "case")
        target_corpus = str(row.get("target_corpus_id") or "")
        requires_mathlib = row.get("requires_mathlib_lake_project_import") is True
        blocked_reasons: list[str] = []
        if requires_mathlib and not mathlib_available:
            blocked_reasons.append("mathlib_lake_project_import_unavailable")
        if target_corpus in absent:
            blocked_reasons.append("corpus_absent")
        decision = "blocked" if blocked_reasons else "allowed"
        if decision == "allowed":
            allowed.append(case_id)
        else:
            blocked.append(case_id)
        cases.append(
            {
                "case_id": case_id,
                "target_corpus_id": target_corpus,
                "requested_capability": row.get("requested_capability"),
                "requires_mathlib_lake_project_import": requires_mathlib,
                "readiness_gate_checked": row.get("readiness_gate_checked") is True,
                "decision": decision,
                "blocked_reasons": blocked_reasons,
                "body_redacted": True,
            }
        )

    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    skip_negative = negative_payloads.get("consumer_skips_readiness_gate")
    if isinstance(skip_negative, dict):
        case_id = str(
            skip_negative.get("expected_negative_case_id")
            or "consumer_skips_readiness_gate"
        )
        if (
            skip_negative.get("attempted_execution") is True
            and skip_negative.get("requires_mathlib_lake_project_import") is True
            and skip_negative.get("readiness_gate_checked") is not True
        ):
            _record(
                findings,
                observed,
                "CONSUMER_SKIPS_CORPUS_READINESS_GATE",
                "A consumer attempted Mathlib-dependent work without checking corpus readiness.",
                case_id=case_id,
                subject_id=str(skip_negative.get("case_id") or "consumer_case"),
                subject_kind="consumer_gate",
            )

    release_negative = negative_payloads.get("release_overclaim")
    if isinstance(release_negative, dict):
        case_id = str(release_negative.get("expected_negative_case_id") or "release_overclaim")
        overclaim_fields = [
            field
            for field in (
                "release_authorized",
                "publication_authorized",
                "formal_proof_authority",
                "mathlib_dependent_proof_authority",
            )
            if release_negative.get(field) is True
        ]
        if overclaim_fields:
            _record(
                findings,
                observed,
                "CORPUS_READINESS_RELEASE_OVERCLAIM",
                "Corpus readiness metadata attempted to authorize release or proof authority.",
                case_id=case_id,
                subject_id=",".join(sorted(overclaim_fields)),
                subject_kind="authority_ceiling",
            )

    return {
        "cases": sorted(cases, key=lambda item: item["case_id"]),
        "case_count": len(cases),
        "allowed_case_ids": sorted(allowed),
        "blocked_case_ids": sorted(blocked),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _build_board(
    *,
    result: dict[str, Any],
    private_scan: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "corpus_readiness_mathlib_absence_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "selected_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "public_contract": {
            "mathlib_probe_required_before_mathlib_proof_work": True,
            "mathlib_lake_project_import_available": result[
                "mathlib_lake_project_import_available"
            ],
            "consumer_gate_required": True,
            "translation_smoke_only_is_not_proof_authority": True,
            "body_redacted": True,
        },
        "corpus_projection": {
            "corpus_count": result["corpus_count"],
            "blocked_capabilities": result["blocked_capabilities"],
            "translation_smoke_only_ids": result["translation_smoke_only_ids"],
            "absent_corpus_ids": result["absent_corpus_ids"],
            "source_refs": result["source_refs"],
            "source_ref_count": len(result["source_refs"]),
            "body_redacted": True,
        },
        "consumer_gate_projection": {
            "case_count": result["consumer_case_count"],
            "allowed_case_ids": result["allowed_case_ids"],
            "blocked_case_ids": result["blocked_case_ids"],
            "decision_rows": result["consumer_gate_cases"],
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
    negative_payloads = {name: payloads[name] for name in NEGATIVE_INPUT_NAMES_STEMS if name in payloads}
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
        negative_payloads=negative_payloads,
    )
    consumer = validate_consumer_gate_cases(
        payloads["consumer_gate_cases"],
        mathlib_available=corpus["mathlib_lake_project_import_available"],
        absent_corpus_ids=corpus["absent_corpus_ids"],
        negative_payloads=negative_payloads,
    )
    observed = _merge_observed(corpus, consumer)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(corpus, consumer)
    error_codes = sorted({finding["error_code"] for finding in findings})
    status = PASS if not missing and not private_scan["blocking_hit_count"] else "blocked"
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    result = {
        "schema_version": "corpus_readiness_mathlib_absence_gate_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "source_refs": sorted(set([*SOURCE_REFS, *corpus["source_refs"]])),
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "private_state_scan": private_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "corpora": corpus["corpora"],
        "corpus_count": corpus["corpus_count"],
        "blocked_capabilities": corpus["blocked_capabilities"],
        "mathlib_lake_project_import_available": corpus[
            "mathlib_lake_project_import_available"
        ],
        "translation_smoke_only_ids": corpus["translation_smoke_only_ids"],
        "absent_corpus_ids": corpus["absent_corpus_ids"],
        "consumer_gate_cases": consumer["cases"],
        "consumer_case_count": consumer["case_count"],
        "allowed_case_ids": consumer["allowed_case_ids"],
        "blocked_case_ids": consumer["blocked_case_ids"],
        "body_redacted": True,
    }
    result["readiness_board"] = _build_board(result=result, private_scan=private_scan)
    return result


NEGATIVE_INPUT_NAMES_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)


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
        "corpus_count",
        "blocked_capabilities",
        "mathlib_lake_project_import_available",
        "translation_smoke_only_ids",
        "absent_corpus_ids",
        "consumer_case_count",
        "allowed_case_ids",
        "blocked_case_ids",
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
        schema_version="corpus_readiness_mathlib_absence_gate_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    result_receipt.update(
        {
            "corpora": result["corpora"],
            "consumer_gate_cases": result["consumer_gate_cases"],
            "readiness_board": result["readiness_board"],
        }
    )
    board_receipt = _common_receipt(
        result,
        schema_version="corpus_readiness_mathlib_absence_board_receipt_v1",
        receipt_paths=receipt_paths,
    )
    board_payload = dict(result["readiness_board"])
    board_receipt["board_schema_version"] = board_payload.pop("schema_version")
    board_receipt.update(board_payload)
    validation = _common_receipt(
        result,
        schema_version="corpus_readiness_mathlib_absence_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "mathlib_absence_gate_retained": True,
            "consumer_gate_required": True,
            "proof_bodies_excluded": True,
            "lean_lake_execution_authorized": False,
            "mathlib_lake_project_import_authorized": False,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="corpus_readiness_mathlib_absence_gate_fixture_acceptance_v1",
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
        "python -m microcosm_core.organs.corpus_readiness_mathlib_absence_gate run "
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
        "python -m microcosm_core.organs.corpus_readiness_mathlib_absence_gate "
        f"run-projection-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_corpus_readiness_bundle",
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
        schema_version="corpus_readiness_mathlib_absence_exported_bundle_receipt_v1",
        receipt_paths=[receipt_ref],
    )
    receipt.update(
        {
            "corpora": result["corpora"],
            "consumer_gate_cases": result["consumer_gate_cases"],
            "readiness_board": result["readiness_board"],
        }
    )
    write_json_atomic(receipt_path, receipt)
    result["receipt_paths"] = [receipt_ref]
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate corpus readiness Mathlib absence metadata")
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("run-projection-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out)
    elif args.action == "run-projection-bundle":
        result = run_projection_bundle(args.input, args.out)
    else:
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
