from __future__ import annotations

import argparse
import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "tactic_portfolio_availability_probe"
FIXTURE_ID = "first_wave.tactic_portfolio_availability_probe"
VALIDATOR_ID = "validator.microcosm.organs.tactic_portfolio_availability_probe"

RESULT_NAME = "tactic_portfolio_availability_result.json"
BOARD_NAME = "tactic_portfolio_availability_board.json"
VALIDATION_RECEIPT_NAME = "tactic_portfolio_availability_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "tactic_portfolio_availability_probe_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_tactic_portfolio_availability_bundle_validation_result.json"

SOURCE_PATTERN_IDS = ["tactic_portfolio_availability_probe"]
SOURCE_REFS = [
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe.json",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/portfolio_core_v0/tactic_portfolio_availability.json",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json",
]
REAL_SUBSTRATE_REFS = SOURCE_REFS
RECEIPT_ANCHOR_REFS = [
    "receipts/first_wave/target_shape_tactic_routing_gate/target_shape_tactic_routing_result.json",
    "receipts/first_wave/target_shape_tactic_routing_gate/target_shape_tactic_routing_board.json",
    "receipts/first_wave/target_shape_tactic_routing_gate/target_shape_tactic_routing_validation_receipt.json",
]
SOURCE_TARGET_REFS = [
    "fixtures/first_wave/tactic_portfolio_availability_probe/input/tactic_portfolio_probe.json",
    "fixtures/first_wave/tactic_portfolio_availability_probe/input/environment_probe.json",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/tactic_portfolio_probe.json",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/environment_probe.json",
    "receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_result.json",
    "receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_board.json",
    "receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_validation_receipt.json",
    ACCEPTANCE_RECEIPT_REL,
    "receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle_validation_result.json",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/aesop.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/decide.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/grind.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/native_decide.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/omega.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/rfl.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/simp.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/portfolio_core_v0/simp_all.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/mathlib_probe.lean",
    "examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle/source_artifacts/tactic_affordance_probe/trace_state_probe.lean",
]
SOURCE_DIGESTS = {
    SOURCE_REFS[0]: "sha256:20fdef8a53401f2bb21483002730895ca0295d2170bf148e8c328c041d8524c3",
    SOURCE_REFS[1]: "sha256:405efadd8045057279a4481c05cdea8e1d99fceee253809526fb37675889d712",
    SOURCE_REFS[2]: "sha256:c413608118229bea32062ce9b8b5af393bcd5f63bbf1030983e98ffa6d07778d",
}
PROBE_SOURCE_REL_PATHS = (
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/aesop.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/decide.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/grind.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/native_decide.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/omega.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/rfl.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/simp.lean",
    "source_artifacts/tactic_affordance_probe/portfolio_core_v0/simp_all.lean",
    "source_artifacts/tactic_affordance_probe/mathlib_probe.lean",
    "source_artifacts/tactic_affordance_probe/trace_state_probe.lean",
)
PROBE_SOURCE_REF_BY_REL = {
    rel: (
        "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/"
        f"{rel.removeprefix('source_artifacts/')}"
    )
    for rel in PROBE_SOURCE_REL_PATHS
}
PROBE_SOURCE_DIGESTS = {
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/aesop.lean"
    ]: "sha256:e7580aa35a0a746a518c9b76d20a7df29a8c9898803ffe68a8e08ec92afa9923",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/decide.lean"
    ]: "sha256:0385b2379d3391686132c7795e906ba4642b527328839cb8fca55210b0088668",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/grind.lean"
    ]: "sha256:10458d90f04bfcd8673f949448de6ac9d0600eff750c85bd4e3cbc015eb3586a",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/native_decide.lean"
    ]: "sha256:0969b1ae27f3adc066cc42272d6cefc4d0083e8eec42b53e4d7d6db98e61610d",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/omega.lean"
    ]: "sha256:03567efe4235543feb46e7eb06eb23e61d65cc69b93c05364d55bedf1f9c0548",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/rfl.lean"
    ]: "sha256:2d2b1800deb875c660693bd87af0715752316132da8a747c13487577feddc696",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/simp.lean"
    ]: "sha256:9ab68dcc2905806aac19e8b4e149c2641dc575947a42d45c8eb31491e6478c67",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/portfolio_core_v0/simp_all.lean"
    ]: "sha256:c049906a2d9e9f4583eb5a1f2cd690992650e0a125124cd7e412f5fc7316af52",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/mathlib_probe.lean"
    ]: "sha256:8c020f6884cda37338cb5216ded61722a9993fcd6d69aee1db655885738abbd1",
    PROBE_SOURCE_REF_BY_REL[
        "source_artifacts/tactic_affordance_probe/trace_state_probe.lean"
    ]: "sha256:5a89050bfd0866cbc28f7c64e6115ea94dd690aa40073509bb6c55b7b4f20cf5",
}
BODY_MATERIAL_STATUS = "copied_non_secret_macro_body_with_provenance"
TACTIC_AVAILABILITY_STATUS = "real_lean_std_tactic_affordance_probe_rows"
PROBE_SOURCE_BODY_STATUS = "copied_non_secret_lean_probe_source_bodies_with_digest_verification"
BODY_IN_RECEIPT = False

INPUT_NAMES = (
    "tactic_portfolio_probe.json",
    "environment_probe.json",
    "availability_policy.json",
)
NEGATIVE_INPUT_NAMES = (
    "missing_compile_status.json",
    "mathlib_claim_without_probe.json",
    "unprobed_tactic_referenced.json",
    "proof_body_leakage.json",
    "authority_overclaim.json",
)
NEGATIVE_INPUT_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)

EXPECTED_NEGATIVE_CASES = {
    "missing_compile_status": ["TACTIC_PORTFOLIO_MISSING_COMPILE_STATUS"],
    "mathlib_claim_without_probe": ["TACTIC_PORTFOLIO_MATHLIB_CLAIM_WITHOUT_PROBE"],
    "unprobed_tactic_referenced": ["TACTIC_PORTFOLIO_UNPROBED_TACTIC_REFERENCED"],
    "proof_body_leakage": ["TACTIC_PORTFOLIO_PROOF_BODY_FORBIDDEN"],
    "authority_overclaim": ["TACTIC_PORTFOLIO_AUTHORITY_OVERCLAIM"],
}

PASS_STATUSES = {"compile_pass", "available", "pass"}
FAIL_STATUSES = {"environment_fail", "compile_fail", "unavailable"}
FORBIDDEN_BODY_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "lean_source_body",
    "provider_output_body",
    "raw_provider_response",
)
OVERCLAIM_KEYS = (
    "benchmark_performance_claimed",
    "formal_proof_authority",
    "lean_lake_execution_authorized",
    "provider_calls_authorized",
    "release_authorized",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "real_tactic_affordance_probe_not_proof_authority",
    "availability_is_environment_scoped": True,
    "mathlib_absence_is_probe_result": True,
    "lean_lake_execution_authorized": False,
    "formal_proof_authority": False,
    "provider_calls_authorized": False,
    "benchmark_performance_authority": False,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Tactic portfolio availability validates copied non-secret Lean/Std tactic "
    "affordance probe rows from the 2026-05-11 proof-state curriculum smoke run. "
    "The public organ does not rerun Lean/Lake, prove any goal, authorize "
    "unavailable tactics, emit proof/provider bodies, claim benchmark "
    "performance, or authorize release."
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
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names] + _probe_source_paths(input_dir)


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return {Path(name).stem: read_json_strict(input_dir / name) for name in names}


def _walk_dicts(value: object) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        rows.append(value)
        for child in value.values():
            rows.extend(_walk_dicts(child))
    elif isinstance(value, list):
        for child in value:
            rows.extend(_walk_dicts(child))
    return rows


def _forbidden_body_keys(row: dict[str, Any]) -> list[str]:
    return sorted(key for key in FORBIDDEN_BODY_KEYS if key in row)


def _probe_source_paths(input_dir: Path) -> list[Path]:
    return [input_dir / rel for rel in PROBE_SOURCE_REL_PATHS]


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _probe_source_imports(
    input_dir: Path,
    *,
    public_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    imports: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for rel in PROBE_SOURCE_REL_PATHS:
        source_ref = PROBE_SOURCE_REF_BY_REL[rel]
        expected = PROBE_SOURCE_DIGESTS[source_ref]
        target = input_dir / rel
        target_ref = _display(target, public_root=public_root)
        if not target.is_file():
            imports.append(
                {
                    "source_ref": source_ref,
                    "target_ref": target_ref,
                    "sha256": expected,
                    "actual_sha256": None,
                    "body_copied": False,
                    "copy_policy": "exact_public_safe_lean_probe_source",
                    "body_material_status": "missing_public_probe_source_body",
                }
            )
            findings.append(
                _finding(
                    "TACTIC_PORTFOLIO_SOURCE_ARTIFACT_MISSING",
                    "A copied Lean tactic probe source artifact is missing.",
                    case_id="probe_source_artifacts",
                    subject_id=target_ref,
                    subject_kind="source_artifact",
                )
            )
            continue
        actual = _sha256(target)
        body_copied = actual == expected
        imports.append(
            {
                "source_ref": source_ref,
                "target_ref": target_ref,
                "sha256": expected,
                "actual_sha256": actual,
                "body_copied": body_copied,
                "copy_policy": "exact_public_safe_lean_probe_source",
                "body_material_status": PROBE_SOURCE_BODY_STATUS,
            }
        )
        if not body_copied:
            findings.append(
                _finding(
                    "TACTIC_PORTFOLIO_SOURCE_ARTIFACT_DIGEST_MISMATCH",
                    "A copied Lean tactic probe source artifact digest does not match its macro source.",
                    case_id="probe_source_artifacts",
                    subject_id=target_ref,
                    subject_kind="source_artifact",
                )
            )
    return imports, findings


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
        "body_in_receipt": BODY_IN_RECEIPT,
        "body_material_status": "negative_fixture_forbidden_material_excluded",
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


def _tactic_rows(payload: object) -> list[dict[str, Any]]:
    rows = _rows(payload, "tactics")
    if rows:
        return rows
    return _rows(payload, "rows")


def _status(row: dict[str, Any]) -> str:
    value = row.get("compile_status") or row.get("availability_status") or row.get("status")
    return str(value or "")


def _portfolio_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    known: list[str] = []
    available: list[str] = []
    unavailable: list[str] = []
    mathlib_dependent: list[str] = []
    status_counts: Counter[str] = Counter()
    missing_compile_status: list[str] = []
    unknown_status: list[str] = []
    for row in rows:
        tactic_id = str(row.get("tactic_id") or "")
        if not tactic_id:
            continue
        known.append(tactic_id)
        status = _status(row)
        if not status:
            missing_compile_status.append(tactic_id)
            status = "missing"
        status_counts[status] += 1
        if row.get("requires_mathlib") is True:
            mathlib_dependent.append(tactic_id)
        if status in PASS_STATUSES:
            available.append(tactic_id)
        elif status in FAIL_STATUSES:
            unavailable.append(tactic_id)
        else:
            unknown_status.append(tactic_id)
    return {
        "tactic_count": len(known),
        "known_tactic_ids": sorted(known),
        "available_tactic_ids": sorted(available),
        "unavailable_tactic_ids": sorted(unavailable),
        "mathlib_dependent_tactic_ids": sorted(mathlib_dependent),
        "compile_status_counts": dict(sorted(status_counts.items())),
        "missing_compile_status_tactic_ids": sorted(missing_compile_status),
        "unknown_status_tactic_ids": sorted(unknown_status),
    }


def _positive_findings(
    *,
    rows: list[dict[str, Any]],
    environment_probe: dict[str, Any],
    summary: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for tactic_id in summary["missing_compile_status_tactic_ids"]:
        _record(
            findings,
            observed,
            "TACTIC_PORTFOLIO_MISSING_COMPILE_STATUS",
            "Every tactic row must report a scoped compile/environment status.",
            case_id="positive_portfolio",
            subject_id=tactic_id,
            subject_kind="tactic_id",
        )
    for tactic_id in summary["unknown_status_tactic_ids"]:
        _record(
            findings,
            observed,
            "TACTIC_PORTFOLIO_UNKNOWN_COMPILE_STATUS",
            "Tactic compile status must be a declared pass or fail status.",
            case_id="positive_portfolio",
            subject_id=tactic_id,
            subject_kind="tactic_id",
        )
    mathlib_available = environment_probe.get("mathlib_lake_project_import_available")
    for row in rows:
        tactic_id = str(row.get("tactic_id") or "tactic")
        if (
            row.get("requires_mathlib") is True
            and _status(row) in PASS_STATUSES
            and mathlib_available is not True
        ):
            _record(
                findings,
                observed,
                "TACTIC_PORTFOLIO_MATHLIB_CLAIM_WITHOUT_PROBE",
                "Mathlib-dependent tactics cannot be marked available unless the Mathlib import probe passed.",
                case_id="positive_portfolio",
                subject_id=tactic_id,
                subject_kind="tactic_id",
            )
        forbidden = _forbidden_body_keys(row)
        if forbidden:
            _record(
                findings,
                observed,
                "TACTIC_PORTFOLIO_PROOF_BODY_FORBIDDEN",
                "Availability fixtures may carry tactic metadata, not proof, Lean, or provider bodies.",
                case_id="positive_portfolio",
                subject_id=tactic_id,
                subject_kind="tactic_id",
            )
    return findings


def _negative_findings(payloads: dict[str, Any], *, known: set[str]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for stem in NEGATIVE_INPUT_STEMS:
        payload = payloads.get(stem)
        if not isinstance(payload, dict):
            continue
        case_id = str(payload.get("expected_negative_case_id") or stem)
        if stem == "missing_compile_status":
            for row in _tactic_rows(payload) or _walk_dicts(payload):
                tactic_id = str(row.get("tactic_id") or "tactic")
                if row.get("compile_status") in {None, ""}:
                    _record(
                        findings,
                        observed,
                        "TACTIC_PORTFOLIO_MISSING_COMPILE_STATUS",
                        "A tactic row omitted compile_status.",
                        case_id=case_id,
                        subject_id=tactic_id,
                        subject_kind="tactic_id",
                    )
        elif stem == "mathlib_claim_without_probe":
            mathlib_available = payload.get("mathlib_lake_project_import_available")
            for row in _tactic_rows(payload):
                tactic_id = str(row.get("tactic_id") or "tactic")
                if (
                    row.get("requires_mathlib") is True
                    and _status(row) in PASS_STATUSES
                    and mathlib_available is not True
                ):
                    _record(
                        findings,
                        observed,
                        "TACTIC_PORTFOLIO_MATHLIB_CLAIM_WITHOUT_PROBE",
                        "Mathlib-dependent tactic availability was claimed without a passing Mathlib probe.",
                        case_id=case_id,
                        subject_id=tactic_id,
                        subject_kind="tactic_id",
                    )
        elif stem == "unprobed_tactic_referenced":
            for row in _rows(payload, "consumer_requests") or _walk_dicts(payload):
                tactic_id = str(row.get("tactic_id") or "")
                if tactic_id and tactic_id not in known:
                    _record(
                        findings,
                        observed,
                        "TACTIC_PORTFOLIO_UNPROBED_TACTIC_REFERENCED",
                        "Consumers may only reference tactics present in the declared portfolio probe.",
                        case_id=case_id,
                        subject_id=tactic_id,
                        subject_kind="tactic_id",
                    )
        elif stem == "proof_body_leakage":
            for row in _walk_dicts(payload):
                forbidden = _forbidden_body_keys(row)
                if forbidden:
                    _record(
                        findings,
                        observed,
                        "TACTIC_PORTFOLIO_PROOF_BODY_FORBIDDEN",
                        "Availability probe fixtures cannot carry proof, Lean, or provider bodies.",
                        case_id=case_id,
                        subject_id=str(row.get("tactic_id") or row.get("case_id") or "payload"),
                        subject_kind="payload",
                    )
        elif stem == "authority_overclaim":
            fields = [field for field in OVERCLAIM_KEYS if payload.get(field) is True]
            if fields:
                _record(
                    findings,
                    observed,
                    "TACTIC_PORTFOLIO_AUTHORITY_OVERCLAIM",
                    "Tactic availability cannot authorize proof authority, provider calls, benchmarks, or release.",
                    case_id=case_id,
                    subject_id=",".join(sorted(fields)),
                    subject_kind="authority_ceiling",
                )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _build_board(*, result: dict[str, Any], secret_scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "tactic_portfolio_availability_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "selected_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "public_contract": {
            "availability_probe_scoped_to_environment": True,
            "mathlib_absence_surfaces_as_environment_fail": True,
            "unprobed_tactics_rejected": True,
            "private_theorem_proof_bodies_excluded": True,
            "public_lean_probe_source_bodies_allowed": True,
            "lean_lake_not_run_by_public_organ": True,
            "lean_probe_source_bodies_copied": True,
            "lean_probe_source_bodies_digest_verified": result[
                "source_artifact_count"
            ]
            == result["copied_source_artifact_count"],
            "body_in_receipt": BODY_IN_RECEIPT,
            "body_material_status": BODY_MATERIAL_STATUS,
            "probe_source_body_status": PROBE_SOURCE_BODY_STATUS,
        },
        "portfolio_projection": {
            "portfolio_id": result["portfolio_id"],
            "environment_id": result["environment_id"],
            "tactic_count": result["tactic_count"],
            "available_tactic_ids": result["available_tactic_ids"],
            "unavailable_tactic_ids": result["unavailable_tactic_ids"],
            "mathlib_dependent_tactic_ids": result["mathlib_dependent_tactic_ids"],
            "compile_status_counts": result["compile_status_counts"],
            "mathlib_probe_status": result["mathlib_probe_status"],
            "mathlib_lake_project_import_available": result[
                "mathlib_lake_project_import_available"
            ],
            "body_in_receipt": BODY_IN_RECEIPT,
            "tactic_availability_status": TACTIC_AVAILABILITY_STATUS,
        },
        "secret_exclusion_scan": secret_scan,
        "body_material_status": BODY_MATERIAL_STATUS,
        "tactic_availability_status": TACTIC_AVAILABILITY_STATUS,
        "real_substrate_refs": REAL_SUBSTRATE_REFS,
        "receipt_anchor_refs": RECEIPT_ANCHOR_REFS,
        "source_target_refs": SOURCE_TARGET_REFS,
        "source_digests": SOURCE_DIGESTS,
        "probe_source_digest_refs": PROBE_SOURCE_DIGESTS,
        "source_artifact_imports": result["source_artifact_imports"],
        "source_artifact_count": result["source_artifact_count"],
        "copied_source_artifact_count": result["copied_source_artifact_count"],
        "probe_source_body_status": PROBE_SOURCE_BODY_STATUS,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": BODY_IN_RECEIPT,
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
        "secret_exclusion_scan",
        "body_material_status",
        "tactic_availability_status",
        "body_in_receipt",
        "real_substrate_refs",
        "receipt_anchor_refs",
        "source_target_refs",
        "source_digests",
        "probe_source_digest_refs",
        "source_artifact_imports",
        "source_artifact_count",
        "copied_source_artifact_count",
        "probe_source_body_status",
        "authority_ceiling",
        "anti_claim",
        "portfolio_id",
        "environment_id",
        "tactic_count",
        "available_tactic_ids",
        "unavailable_tactic_ids",
        "mathlib_dependent_tactic_ids",
        "compile_status_counts",
        "mathlib_probe_status",
        "mathlib_lake_project_import_available",
        "mathlib_absence_gate_enforced",
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
        name: payloads[name] for name in NEGATIVE_INPUT_STEMS if name in payloads
    }
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    secret_scan["body_material_status"] = "secret_exclusion_scan_no_payload_body_export"
    source_imports, source_findings = _probe_source_imports(
        input_dir,
        public_root=public_root,
    )

    portfolio_payload = payloads["tactic_portfolio_probe"]
    environment_probe = payloads["environment_probe"]
    if not isinstance(portfolio_payload, dict):
        portfolio_payload = {}
    if not isinstance(environment_probe, dict):
        environment_probe = {}
    rows = _tactic_rows(portfolio_payload)
    summary = _portfolio_summary(rows)
    positive_findings = _positive_findings(
        rows=rows,
        environment_probe=environment_probe,
        summary=summary,
    )
    negative = _negative_findings(negative_payloads, known=set(summary["known_tactic_ids"]))
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    observed = negative["observed_negative_cases"]
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = [*source_findings, *positive_findings, *negative["findings"]]
    error_codes = sorted({finding["error_code"] for finding in findings})
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    mathlib_available = environment_probe.get("mathlib_lake_project_import_available")
    mathlib_failures = [
        tactic_id
        for tactic_id in summary["mathlib_dependent_tactic_ids"]
        if tactic_id in summary["unavailable_tactic_ids"]
    ]
    status = (
        PASS
        if not source_findings
        and not positive_findings
        and not missing
        and not secret_scan["blocking_hit_count"]
        else "blocked"
    )
    return {
        "schema_version": "tactic_portfolio_availability_result_v1",
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
        "expected_negative_cases": expected,
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "body_material_status": BODY_MATERIAL_STATUS,
        "tactic_availability_status": TACTIC_AVAILABILITY_STATUS,
        "body_in_receipt": BODY_IN_RECEIPT,
        "real_substrate_refs": REAL_SUBSTRATE_REFS,
        "receipt_anchor_refs": RECEIPT_ANCHOR_REFS,
        "source_target_refs": SOURCE_TARGET_REFS,
        "source_digests": SOURCE_DIGESTS,
        "probe_source_digest_refs": PROBE_SOURCE_DIGESTS,
        "source_artifact_imports": source_imports,
        "source_artifact_count": len(source_imports),
        "copied_source_artifact_count": sum(
            1 for row in source_imports if row["body_copied"] is True
        ),
        "probe_source_body_status": PROBE_SOURCE_BODY_STATUS,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "portfolio_id": str(portfolio_payload.get("portfolio_id") or ""),
        "environment_id": str(environment_probe.get("environment_id") or ""),
        "tactic_count": summary["tactic_count"],
        "known_tactic_ids": summary["known_tactic_ids"],
        "available_tactic_ids": summary["available_tactic_ids"],
        "unavailable_tactic_ids": summary["unavailable_tactic_ids"],
        "mathlib_dependent_tactic_ids": summary["mathlib_dependent_tactic_ids"],
        "compile_status_counts": summary["compile_status_counts"],
        "mathlib_probe_status": str(environment_probe.get("mathlib_probe_status") or ""),
        "mathlib_lake_project_import_available": bool(mathlib_available),
        "mathlib_absence_gate_enforced": mathlib_available is False
        and bool(mathlib_failures),
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    public_root = _public_root_for_path(out_dir)
    paths = {
        "result": out_dir / RESULT_NAME,
        "board": out_dir / BOARD_NAME,
        "validation": out_dir / VALIDATION_RECEIPT_NAME,
    }
    if acceptance_out is not None:
        paths["acceptance"] = acceptance_out
    relative_paths = _relative_receipt_paths(paths, public_root)
    board = _build_board(result=result, secret_scan=result["secret_exclusion_scan"])
    result_receipt = _common_receipt(
        result,
        schema_version="tactic_portfolio_availability_result_receipt_v1",
        receipt_paths=relative_paths,
    )
    board["receipt_paths"] = relative_paths
    validation = _common_receipt(
        result,
        schema_version="tactic_portfolio_availability_validation_receipt_v1",
        receipt_paths=relative_paths,
    )
    validation["board_ref"] = _display(paths["board"], public_root=public_root)
    validation["result_ref"] = _display(paths["result"], public_root=public_root)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(paths["result"], result_receipt)
    write_json_atomic(paths["board"], board)
    write_json_atomic(paths["validation"], validation)
    if acceptance_out is not None:
        acceptance = _common_receipt(
            result,
            schema_version="tactic_portfolio_availability_fixture_acceptance_v1",
            receipt_paths=relative_paths,
        )
        write_json_atomic(acceptance_out, acceptance)
    result["receipt_paths"] = relative_paths
    return result


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.tactic_portfolio_availability_probe run",
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    target = Path(out_dir)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    return _write_receipts(
        result,
        target,
        acceptance_out=Path(acceptance_out) if acceptance_out else None,
    )


def run_availability_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.tactic_portfolio_availability_probe "
        "run-availability-bundle"
    ),
) -> dict[str, Any]:
    target = Path(out_dir)
    public_root = _public_root_for_path(target)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_tactic_portfolio_availability_bundle",
        include_negative=False,
    )
    path = target / BUNDLE_RESULT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = _display(path, public_root=public_root)
    receipt = _common_receipt(
        result,
        schema_version="exported_tactic_portfolio_availability_bundle_validation_result_v1",
        receipt_paths=[receipt_path],
    )
    write_json_atomic(path, receipt)
    result["receipt_paths"] = [receipt_path]
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate public tactic availability probe fixtures")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    bundle_parser = sub.add_parser("run-availability-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "run":
        command = (
            "python -m microcosm_core.organs.tactic_portfolio_availability_probe run "
            f"--input {args.input} --out {args.out}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    else:
        command = (
            "python -m microcosm_core.organs.tactic_portfolio_availability_probe "
            f"run-availability-bundle --input {args.input} --out {args.out}"
        )
        result = run_availability_bundle(args.input, args.out, command=command)
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
