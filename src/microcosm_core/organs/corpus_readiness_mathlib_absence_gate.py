from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
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
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_MODULE_IMPORT_STATUS = "copied_corpus_readiness_source_modules_verified"
CARD_SCHEMA_VERSION = "corpus_readiness_mathlib_absence_gate_command_card_v1"

SOURCE_PATTERN_IDS = [
    "corpus_readiness_mathlib_absence_gate",
]

SOURCE_REFS = [
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe.json",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/mathlib_probe.lean",
    "state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/portfolio_core_v0/tactic_portfolio_availability.json",
]
REAL_SUBSTRATE_REFS = SOURCE_REFS
RECEIPT_ANCHOR_REFS = [
    "receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_result.json",
    "receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_board.json",
    "receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_validation_receipt.json",
]
SOURCE_TARGET_REFS = [
    "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input/corpus_readiness.json",
    "fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input/consumer_gate_cases.json",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/corpus_readiness.json",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/consumer_gate_cases.json",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/source_module_manifest.json",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/source_artifacts/state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/corpus_readiness.json",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/source_artifacts/state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe.json",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/source_artifacts/state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/mathlib_probe.lean",
    "examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle/source_artifacts/state/runs/PROVER_PROOF_STATE_SEARCH_CURRICULUM_20260511_v0_smoke/tactic_affordance_probe/portfolio_core_v0/tactic_portfolio_availability.json",
    "receipts/first_wave/corpus_readiness_mathlib_absence_gate/corpus_readiness_mathlib_absence_gate_result.json",
    "receipts/first_wave/corpus_readiness_mathlib_absence_gate/corpus_readiness_mathlib_absence_board.json",
    "receipts/first_wave/corpus_readiness_mathlib_absence_gate/corpus_readiness_mathlib_absence_validation_receipt.json",
    ACCEPTANCE_RECEIPT_REL,
    "receipts/runtime_shell/demo_project/organs/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle_validation_result.json",
]
SOURCE_DIGESTS = {
    SOURCE_REFS[0]: "sha256:c413608118229bea32062ce9b8b5af393bcd5f63bbf1030983e98ffa6d07778d",
    SOURCE_REFS[1]: "sha256:20fdef8a53401f2bb21483002730895ca0295d2170bf148e8c328c041d8524c3",
    SOURCE_REFS[2]: "sha256:8c020f6884cda37338cb5216ded61722a9993fcd6d69aee1db655885738abbd1",
    SOURCE_REFS[3]: "sha256:405efadd8045057279a4481c05cdea8e1d99fceee253809526fb37675889d712",
}
BODY_MATERIAL_STATUS = "copied_non_secret_macro_body_with_provenance"
CORPUS_READINESS_STATUS = "real_lean_std_corpus_readiness_and_mathlib_absence_boundary"
TOOLCHAIN_BOUNDARY_STATUS = "real_lean_4_29_1_std_mathlib_absence_probe"
BODY_IN_RECEIPT = False
PUBLIC_SAFE_BODY_CLASSES = {
    "public_macro_pattern_body",
    "public_macro_tool_body",
    "public_macro_receipt_body",
    "public_macro_proof_body",
}

FORBIDDEN_BODY_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "lean_source_body",
    "provider_output_body",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "real_corpus_readiness_boundary_not_mathlib_proof_or_benchmark_authority"
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
    "Corpus readiness Mathlib absence gate validates copied non-secret corpus "
    "readiness and Lean/Std toolchain-boundary rows from the 2026-05-11 "
    "proof-state curriculum smoke run. It does not rerun Lean or Lake, prove "
    "theorem correctness, claim Mathlib is available, expose proof/provider "
    "bodies, benchmark formal-math corpora, call providers, or authorize release."
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
        if candidate.name == "microcosm-substrate" or (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src/microcosm_core").is_dir()
            and (candidate / "core/private_state_forbidden_classes.json").is_file()
        ):
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


def _source_module_manifest_path(input_dir: Path) -> Path:
    return input_dir / SOURCE_MODULE_MANIFEST_NAME


def _read_source_module_manifest(input_dir: Path) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return {}
    payload = read_json_strict(manifest_path)
    return payload if isinstance(payload, dict) else {}


def _source_module_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return _rows(manifest, "modules")


def _strip_microcosm_prefix(ref: str) -> str:
    prefix = "microcosm-substrate/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def _source_module_target_path(input_dir: Path, row: dict[str, Any]) -> Path:
    row_path = str(row.get("path") or "")
    if row_path:
        return input_dir / row_path
    target_ref = _strip_microcosm_prefix(str(row.get("target_ref") or ""))
    public_root = _public_root_for_path(input_dir)
    return public_root / target_ref if target_ref else input_dir


def _source_artifact_paths(input_dir: Path) -> list[Path]:
    manifest = _read_source_module_manifest(input_dir)
    return [
        _source_module_target_path(input_dir, row)
        for row in _source_module_rows(manifest)
    ]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    manifest_path = _source_module_manifest_path(input_dir)
    if manifest_path.is_file():
        paths.append(manifest_path)
    paths.extend(_source_artifact_paths(input_dir))
    return paths


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _normalize_sha256(value: object) -> str:
    digest = str(value or "")
    if digest and not digest.startswith("sha256:"):
        return f"sha256:{digest}"
    return digest


def _line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


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
                "exists": row.get("exists"),
                "has_lake_file": row.get("has_lake_file"),
                "local_path": row.get("local_path"),
                "readiness_status": row.get("readiness_status"),
                "selected_for_this_run": row.get("selected_for_this_run") is True,
                "mathlib_lake_project_import_available": row_mathlib_available,
                "mathlib_probe_status": mathlib_probe_status,
                "translation_smoke_only": row.get("translation_smoke_only") is True,
                "consumer_rule": row.get("consumer_rule"),
                "body_in_receipt": BODY_IN_RECEIPT,
                "body_material_status": BODY_MATERIAL_STATUS,
                "corpus_readiness_status": CORPUS_READINESS_STATUS,
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
                "body_in_receipt": BODY_IN_RECEIPT,
                "body_material_status": BODY_MATERIAL_STATUS,
                "corpus_readiness_status": CORPUS_READINESS_STATUS,
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


def validate_source_module_imports(
    input_dir: Path,
    *,
    required: bool,
    public_root: Path,
) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(input_dir)
    manifest = _read_source_module_manifest(input_dir)
    rows = _source_module_rows(manifest)
    findings: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []
    manifest_ref = _display(manifest_path, public_root=public_root)

    if required and not manifest_path.is_file():
        findings.append(
            _finding(
                "CORPUS_READINESS_SOURCE_MODULE_MANIFEST_MISSING",
                "Exported corpus readiness bundle must include a source_module_manifest.json for copied macro corpus/toolchain bodies.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if manifest_path.is_file() and manifest.get("source_import_class") != (
        "copied_non_secret_macro_body"
    ):
        findings.append(
            _finding(
                "CORPUS_READINESS_SOURCE_IMPORT_CLASS_UNSUPPORTED",
                "Corpus readiness source module manifest must declare copied_non_secret_macro_body.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if required and manifest_path.is_file() and not rows:
        findings.append(
            _finding(
                "CORPUS_READINESS_SOURCE_MODULE_ROWS_MISSING",
                "Exported corpus readiness bundle must carry at least one copied source module row.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )

    for row in rows:
        module_id = str(row.get("module_id") or "source_module")
        target = _source_module_target_path(input_dir, row)
        source_digest = _normalize_sha256(row.get("source_sha256")) or _normalize_sha256(
            row.get("sha256")
        )
        target_digest = _normalize_sha256(row.get("target_sha256")) or _normalize_sha256(
            row.get("sha256")
        )
        exists = target.is_file()
        actual_digest = _sha256(target) if exists else None
        material_class = str(row.get("material_class") or "")
        source_ref = str(row.get("source_ref") or "")
        target_ref = _display(target, public_root=public_root)
        digest_match = actual_digest == target_digest
        import_row = {
            "module_id": module_id,
            "source_ref": source_ref,
            "target_ref": target_ref,
            "material_class": material_class,
            "source_sha256": source_digest,
            "expected_target_sha256": target_digest,
            "target_sha256": actual_digest,
            "exists": exists,
            "digest_match": digest_match,
            "source_to_target_relation": str(
                row.get("source_to_target_relation") or "exact_copy"
            ),
            "verification_mode": str(
                row.get("verification_mode") or "exact_source_digest_match"
            ),
            "public_safe_transform": row.get("public_safe_transform"),
            "source_line_count": _line_count(target) if exists else None,
            "target_line_count": _line_count(target) if exists else None,
            "body_in_receipt": BODY_IN_RECEIPT,
            "body_material_status": BODY_MATERIAL_STATUS,
            "corpus_readiness_status": CORPUS_READINESS_STATUS,
            "toolchain_boundary_status": TOOLCHAIN_BOUNDARY_STATUS,
        }
        imports.append(import_row)

        if str(row.get("source_import_class") or "") != "copied_non_secret_macro_body":
            findings.append(
                _finding(
                    "CORPUS_READINESS_SOURCE_MODULE_IMPORT_CLASS_UNSUPPORTED",
                    "Source module rows must declare copied_non_secret_macro_body.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_BODY_CLASSES:
            findings.append(
                _finding(
                    "CORPUS_READINESS_SOURCE_MODULE_CLASS_UNSUPPORTED",
                    "Source module rows must use a public-safe macro body material class.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if row.get("body_in_receipt") is True:
            findings.append(
                _finding(
                    "CORPUS_READINESS_SOURCE_BODY_RECEIPT_EXPORT_FORBIDDEN",
                    "Copied corpus/toolchain source bodies may live in the bundle source_artifacts tree, not in generated receipts.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if not exists:
            findings.append(
                _finding(
                    "CORPUS_READINESS_SOURCE_MODULE_TARGET_MISSING",
                    "Copied source module target file is missing from the exported bundle.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        elif not digest_match:
            findings.append(
                _finding(
                    "CORPUS_READINESS_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Copied source module digest must match the manifest target digest.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )

    copied_count = sum(1 for row in imports if row["exists"] and row["digest_match"])
    source_modules_pass = not findings
    return {
        "source_module_manifest_ref": manifest_ref,
        "source_module_import_status": SOURCE_MODULE_IMPORT_STATUS,
        "body_material_status": BODY_MATERIAL_STATUS,
        "source_module_imports": imports,
        "source_module_import_count": len(imports),
        "copied_source_artifact_count": copied_count,
        "source_modules_pass": source_modules_pass,
        "source_refs": sorted({row["source_ref"] for row in imports if row["source_ref"]}),
        "target_refs": [row["target_ref"] for row in imports],
        "material_classes": sorted(
            {row["material_class"] for row in imports if row["material_class"]}
        ),
        "findings": findings,
    }


def _build_board(
    *,
    result: dict[str, Any],
    secret_scan: dict[str, Any],
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
            "body_in_receipt": BODY_IN_RECEIPT,
            "body_material_status": BODY_MATERIAL_STATUS,
        },
        "corpus_projection": {
            "corpus_count": result["corpus_count"],
            "blocked_capabilities": result["blocked_capabilities"],
            "translation_smoke_only_ids": result["translation_smoke_only_ids"],
            "absent_corpus_ids": result["absent_corpus_ids"],
            "source_refs": result["source_refs"],
            "source_ref_count": len(result["source_refs"]),
            "body_in_receipt": BODY_IN_RECEIPT,
            "corpus_readiness_status": CORPUS_READINESS_STATUS,
            "toolchain_boundary_status": TOOLCHAIN_BOUNDARY_STATUS,
        },
        "consumer_gate_projection": {
            "case_count": result["consumer_case_count"],
            "allowed_case_ids": result["allowed_case_ids"],
            "blocked_case_ids": result["blocked_case_ids"],
            "decision_rows": result["consumer_gate_cases"],
            "body_in_receipt": BODY_IN_RECEIPT,
            "corpus_readiness_status": CORPUS_READINESS_STATUS,
        },
        "secret_exclusion_scan": secret_scan,
        "body_material_status": BODY_MATERIAL_STATUS,
        "corpus_readiness_status": CORPUS_READINESS_STATUS,
        "toolchain_boundary_status": TOOLCHAIN_BOUNDARY_STATUS,
        "real_substrate_refs": REAL_SUBSTRATE_REFS,
        "receipt_anchor_refs": RECEIPT_ANCHOR_REFS,
        "source_target_refs": SOURCE_TARGET_REFS,
        "source_digests": SOURCE_DIGESTS,
        "source_module_manifest_ref": result.get("source_module_manifest_ref"),
        "source_module_import_status": result.get("source_module_import_status"),
        "source_module_import_count": result.get("source_module_import_count"),
        "copied_source_artifact_count": result.get("copied_source_artifact_count"),
        "source_modules_pass": result.get("source_modules_pass"),
        "source_module_imports": result.get("source_module_imports", []),
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": BODY_IN_RECEIPT,
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
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    secret_scan["body_material_status"] = "secret_exclusion_scan_no_payload_body_export"

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
    source_imports = validate_source_module_imports(
        input_dir,
        required=input_mode == "exported_corpus_readiness_bundle",
        public_root=public_root,
    )
    observed = _merge_observed(corpus, consumer)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(corpus, consumer, source_imports)
    error_codes = sorted({finding["error_code"] for finding in findings})
    status = (
        PASS
        if not missing
        and not secret_scan["blocking_hit_count"]
        and source_imports["source_modules_pass"]
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
        "source_refs": sorted(
            set([*SOURCE_REFS, *corpus["source_refs"], *source_imports["source_refs"]])
        ),
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "body_material_status": BODY_MATERIAL_STATUS,
        "corpus_readiness_status": CORPUS_READINESS_STATUS,
        "toolchain_boundary_status": TOOLCHAIN_BOUNDARY_STATUS,
        "body_in_receipt": BODY_IN_RECEIPT,
        "source_module_import_status": source_imports["source_module_import_status"],
        "source_module_manifest_ref": source_imports["source_module_manifest_ref"],
        "source_module_imports": source_imports["source_module_imports"],
        "source_module_import_count": source_imports["source_module_import_count"],
        "copied_source_artifact_count": source_imports["copied_source_artifact_count"],
        "source_modules_pass": source_imports["source_modules_pass"],
        "real_substrate_refs": REAL_SUBSTRATE_REFS,
        "receipt_anchor_refs": RECEIPT_ANCHOR_REFS,
        "source_target_refs": SOURCE_TARGET_REFS,
        "source_digests": SOURCE_DIGESTS,
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
    }
    result["readiness_board"] = _build_board(result=result, secret_scan=secret_scan)
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
        "secret_exclusion_scan",
        "body_material_status",
        "corpus_readiness_status",
        "toolchain_boundary_status",
        "body_in_receipt",
        "source_module_import_status",
        "source_module_manifest_ref",
        "source_module_imports",
        "source_module_import_count",
        "copied_source_artifact_count",
        "source_modules_pass",
        "real_substrate_refs",
        "receipt_anchor_refs",
        "source_target_refs",
        "source_digests",
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


def _exported_bundle_receipt_ref(
    receipt_path: Path,
    *,
    target: Path,
    public_root: Path,
) -> str:
    try:
        return receipt_path.relative_to(public_root).as_posix()
    except ValueError:
        return receipt_path.relative_to(target.parent).as_posix()


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
            "projection_status": "real_corpus_readiness_boundary_landed"
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
    receipt_ref = _exported_bundle_receipt_ref(
        receipt_path,
        target=target,
        public_root=public_root,
    )
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


def _authority_ceiling_card(result: dict[str, Any]) -> dict[str, Any]:
    authority = result.get("authority_ceiling", {})
    if not isinstance(authority, dict):
        authority = {}
    return {
        "status": authority.get("status"),
        "authority_ceiling": authority.get("authority_ceiling"),
        "lean_lake_execution_authorized": authority.get(
            "lean_lake_execution_authorized"
        )
        is True,
        "mathlib_lake_project_import_authorized": authority.get(
            "mathlib_lake_project_import_authorized"
        )
        is True,
        "mathlib_dependent_proof_authority": authority.get(
            "mathlib_dependent_proof_authority"
        )
        is True,
        "formal_proof_authority": authority.get("formal_proof_authority") is True,
        "provider_calls_authorized": authority.get("provider_calls_authorized")
        is True,
        "release_authorized": authority.get("release_authorized") is True,
    }


def _secret_scan_card(result: dict[str, Any]) -> dict[str, Any]:
    scan = result.get("secret_exclusion_scan", {})
    if not isinstance(scan, dict):
        scan = {}
    return {
        "status": scan.get("status"),
        "hit_count": scan.get("hit_count"),
        "blocking_hit_count": scan.get("blocking_hit_count"),
        "scanned_path_count": scan.get("scanned_path_count"),
        "body_in_receipt": scan.get("body_in_receipt") is True,
        "real_substrate_default": scan.get("real_substrate_default") is True,
        "omitted_output_fields": scan.get("omitted_output_fields", []),
    }


def _source_module_card(result: dict[str, Any]) -> dict[str, Any]:
    imports = result.get("source_module_imports", [])
    import_rows = imports if isinstance(imports, list) else []
    digest_match_count = sum(
        1
        for row in import_rows
        if isinstance(row, dict) and row.get("digest_match") is True
    )
    material_classes = sorted(
        {
            str(row.get("material_class"))
            for row in import_rows
            if isinstance(row, dict) and row.get("material_class")
        }
    )
    return {
        "status": result.get("source_module_import_status"),
        "manifest_ref": result.get("source_module_manifest_ref"),
        "source_modules_pass": result.get("source_modules_pass") is True,
        "source_module_import_count": result.get("source_module_import_count"),
        "copied_source_artifact_count": result.get("copied_source_artifact_count"),
        "digest_match_count": digest_match_count,
        "material_classes": material_classes,
    }


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "created_at": result.get("created_at"),
        "status": result.get("status"),
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": result.get("command"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "receipt_paths": result.get("receipt_paths", []),
        "counts": {
            "corpus_count": result.get("corpus_count"),
            "consumer_case_count": result.get("consumer_case_count"),
            "allowed_case_count": len(result.get("allowed_case_ids", [])),
            "blocked_case_count": len(result.get("blocked_case_ids", [])),
            "blocked_capability_count": len(result.get("blocked_capabilities", [])),
            "absent_corpus_count": len(result.get("absent_corpus_ids", [])),
            "source_ref_count": len(result.get("source_refs", [])),
        },
        "corpus_gate": {
            "mathlib_lake_project_import_available": result.get(
                "mathlib_lake_project_import_available"
            )
            is True,
            "translation_smoke_only_ids": result.get("translation_smoke_only_ids", []),
            "absent_corpus_ids": result.get("absent_corpus_ids", []),
            "allowed_case_ids": result.get("allowed_case_ids", []),
            "blocked_case_ids": result.get("blocked_case_ids", []),
            "corpus_readiness_status": result.get("corpus_readiness_status"),
            "toolchain_boundary_status": result.get("toolchain_boundary_status"),
        },
        "negative_case_coverage": {
            "expected_negative_cases": result.get("expected_negative_cases", []),
            "observed_negative_case_count": len(
                result.get("observed_negative_cases", {})
            ),
            "missing_negative_cases": result.get("missing_negative_cases", []),
            "error_codes": result.get("error_codes", []),
        },
        "source_module_import": _source_module_card(result),
        "secret_exclusion_scan": _secret_scan_card(result),
        "authority_ceiling": _authority_ceiling_card(result),
        "body_material_status": result.get("body_material_status"),
        "body_in_receipt": result.get("body_in_receipt") is True,
        "output_economy": {
            "full_receipt_written": bool(result.get("receipt_paths")),
            "stdout_mode": "card",
            "omitted_fields": [
                "anti_claim",
                "blocked_capabilities",
                "consumer_gate_cases",
                "corpora",
                "findings",
                "readiness_board",
                "real_substrate_refs",
                "receipt_anchor_refs",
                "source_digests",
                "source_module_imports",
                "source_target_refs",
            ],
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate corpus readiness Mathlib absence metadata")
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = subparsers.add_parser("run-projection-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        command = (
            "python -m microcosm_core.organs.corpus_readiness_mathlib_absence_gate "
            f"run --input {args.input} --out {args.out}"
            f"{' --card' if args.card else ''}"
        )
        result = run(args.input, args.out, command=command)
    elif args.action == "run-projection-bundle":
        command = (
            "python -m microcosm_core.organs.corpus_readiness_mathlib_absence_gate "
            f"run-projection-bundle --input {args.input} --out {args.out}"
            f"{' --card' if args.card else ''}"
        )
        result = run_projection_bundle(args.input, args.out, command=command)
    else:
        return 2
    payload = result_card(result) if args.card else result
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
