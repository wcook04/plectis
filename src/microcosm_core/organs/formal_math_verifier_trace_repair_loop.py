from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import microcosm_core.private_state_scan as private_state_scan
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
CARD_SCHEMA_VERSION = "formal_math_verifier_trace_repair_loop_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "authority_ceiling",
    "anti_claim",
    "body_material_contract",
    "copied_material",
    "curriculum_edges",
    "failure_mode_ledger",
    "findings",
    "freshness_basis",
    "observed_negative_cases",
    "projection_receipt_refs",
    "secret_exclusion_scan",
    "source_digests",
    "source_module_manifest",
    "source_open_body_imports",
    "source_pattern_ids",
    "source_refs",
    "target_refs",
    "verifier_attempts",
)

RUN_ID = "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0"
PREMISE_RETRIEVAL_VARIANT_ID = "premise_retrieval_graph_v0"
ORACLE_REPAIR_VARIANT_ID = "oracle_repair_graph_v0"
PREMISE_RUN_SUMMARY_REF = (
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "premise_retrieval_graph_v0/run_summary.json"
)
PREMISE_FAILURE_TAXONOMY_REF = (
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "premise_retrieval_graph_v0/failure_taxonomy_report.json"
)
PREMISE_GRAPH_UPDATE_CANDIDATES_REF = (
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "premise_retrieval_graph_v0/graph_update_candidates.json"
)
ORACLE_REPAIR_RUN_SUMMARY_REF = (
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "oracle_repair_graph_v0/run_summary.json"
)
ORACLE_REPAIR_FAILURE_TAXONOMY_REF = (
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "oracle_repair_graph_v0/failure_taxonomy_report.json"
)
ORACLE_REPAIR_GRAPH_UPDATE_CANDIDATES_REF = (
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "oracle_repair_graph_v0/graph_update_candidates.json"
)
GRAPH_VARIANT_COMPARISON_REF = (
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "graph_variant_comparison.json"
)
SOURCE_REFS = [
    PREMISE_RUN_SUMMARY_REF,
    PREMISE_FAILURE_TAXONOMY_REF,
    PREMISE_GRAPH_UPDATE_CANDIDATES_REF,
    ORACLE_REPAIR_RUN_SUMMARY_REF,
    ORACLE_REPAIR_FAILURE_TAXONOMY_REF,
    ORACLE_REPAIR_GRAPH_UPDATE_CANDIDATES_REF,
    GRAPH_VARIANT_COMPARISON_REF,
]
SOURCE_MODULE_MANIFEST_REF = (
    "examples/formal_math_verifier_trace_repair_loop/"
    "exported_verifier_trace_repair_bundle/source_module_manifest.json"
)
SOURCE_DIGESTS = {
    PREMISE_RUN_SUMMARY_REF: (
        "sha256:93304410f32d40f5cad1c161c1d01a5d6f353ee10b7cf3fecbaaf7b068b43008"
    ),
    PREMISE_FAILURE_TAXONOMY_REF: (
        "sha256:8b054c57001c432942a7ed97cbd4dca2a2e2b174d9cd31d9121c38c5ecc933af"
    ),
    PREMISE_GRAPH_UPDATE_CANDIDATES_REF: (
        "sha256:6c7eb0bc4ebf1c9a2689720ea8cfe9aa72298c136fdfebd6e1a4aae78986890f"
    ),
    ORACLE_REPAIR_RUN_SUMMARY_REF: (
        "sha256:7669c8d91ddf7de75b6a7c7e688e70e4ba211ff3c00ceb9bca32d3202c5739b4"
    ),
    ORACLE_REPAIR_FAILURE_TAXONOMY_REF: (
        "sha256:7d30aa6ba8a5ce77dbdf855229c3e26bba0be7e814e02cdfcbba9fcbfee24ab8"
    ),
    ORACLE_REPAIR_GRAPH_UPDATE_CANDIDATES_REF: (
        "sha256:4e2576708439023a72267f5fab2e609e62813991890c8321ab272a0221a9136a"
    ),
    GRAPH_VARIANT_COMPARISON_REF: (
        "sha256:8bab9c7a0a2a62f2178a550ab2fadf06887ff03cc9bf83f057688597b9e0556f"
    ),
}
SOURCE_MODULE_MATERIAL_IDS = {
    PREMISE_RUN_SUMMARY_REF: "ring2_trace_repair_premise_run_summary_body_import",
    PREMISE_FAILURE_TAXONOMY_REF: (
        "ring2_trace_repair_premise_failure_taxonomy_body_import"
    ),
    PREMISE_GRAPH_UPDATE_CANDIDATES_REF: (
        "ring2_trace_repair_premise_graph_update_candidates_body_import"
    ),
    ORACLE_REPAIR_RUN_SUMMARY_REF: (
        "ring2_trace_repair_oracle_repair_run_summary_body_import"
    ),
    ORACLE_REPAIR_FAILURE_TAXONOMY_REF: (
        "ring2_trace_repair_oracle_repair_failure_taxonomy_body_import"
    ),
    ORACLE_REPAIR_GRAPH_UPDATE_CANDIDATES_REF: (
        "ring2_trace_repair_oracle_repair_graph_update_candidates_body_import"
    ),
    GRAPH_VARIANT_COMPARISON_REF: (
        "ring2_trace_repair_graph_variant_comparison_body_import"
    ),
}
SOURCE_MODULE_MATERIAL_CLASSES = {
    PREMISE_GRAPH_UPDATE_CANDIDATES_REF: "public_macro_pattern_body",
    ORACLE_REPAIR_GRAPH_UPDATE_CANDIDATES_REF: "public_macro_pattern_body",
}
BODY_MATERIAL_STATUS = "copied_non_secret_macro_body_with_provenance"
SOURCE_MODULE_BODY_MATERIAL_STATUS = (
    "source_faithful_public_safe_ring2_verifier_trace_repair_bodies_with_digest_provenance"
)
SOURCE_MODULE_IMPORT_CLASSES = {
    "copied_non_secret_macro_body",
    "source_faithful_public_safe_macro_body",
}
BODY_MATERIAL_CONTRACT = {
    "body_material_status": BODY_MATERIAL_STATUS,
    "macro_run_id": RUN_ID,
    "premise_retrieval_variant_id": PREMISE_RETRIEVAL_VARIANT_ID,
    "oracle_repair_variant_id": ORACLE_REPAIR_VARIANT_ID,
    "copied_failure_trace_rows": True,
    "proof_bodies_excluded": True,
    "oracle_premise_ids_excluded": True,
    "provider_payloads_excluded": True,
    "lean_lake_execution_authorized": False,
    "formal_proof_authority": False,
}

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
    "authority_ceiling": "copied_ring2_verifier_trace_repair_metadata_not_proof_authority",
    "lean_lake_execution_authorized": False,
    "formal_proof_authority": False,
    "provider_calls_authorized": False,
    "proof_bodies_allowed": False,
    "oracle_premise_ids_allowed": False,
    "human_approval_as_proof_authority": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Formal math verifier-trace repair loop validates copied non-secret Ring2 "
    "failure taxonomy, graph-update, and oracle-repair contrast rows as public "
    "repair-loop evidence. It does not run Lean or Lake here, call providers, "
    "expose proof bodies or oracle premise ids, treat human or provider advice "
    "as proof correctness, prove theorem correctness, or authorize release."
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def _source_module_manifest_path(input_dir: Path) -> Path:
    return input_dir / "source_module_manifest.json"


def _source_module_path(input_dir: Path, source_ref: str) -> Path:
    source_path = Path(source_ref)
    try:
        relative_source = source_path.relative_to("state/runs")
    except ValueError:
        relative_source = source_path
    return input_dir / "source_modules/ring2_runs" / relative_source


def _target_path_from_module(input_dir: Path, row: dict[str, Any]) -> Path:
    row_path = str(row.get("path") or "")
    if row_path:
        return input_dir / row_path
    source_ref = str(row.get("source_ref") or "")
    return _source_module_path(input_dir, source_ref)


def _source_module_scan_paths(input_dir: Path) -> list[Path]:
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return []
    manifest = read_json_strict(manifest_path)
    paths = [manifest_path]
    for row in _rows(manifest, "modules"):
        paths.append(_target_path_from_module(input_dir, row))
    return paths


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    bundle_manifest = input_dir / "bundle_manifest.json"
    if bundle_manifest.is_file():
        paths.append(bundle_manifest)
    paths.extend(_source_module_scan_paths(input_dir))
    return paths


def _json_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _file_freshness_entry(path: Path, *, public_root: Path) -> dict[str, Any]:
    public_ref = _display(path, public_root=public_root)
    if not path.exists():
        return {
            "path": public_ref,
            "exists": False,
            "size_bytes": 0,
            "mtime_ns": 0,
        }
    stat = path.stat()
    return {
        "path": public_ref,
        "exists": path.is_file(),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = path.resolve(strict=False).as_posix()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def _loop_bundle_freshness_basis(
    input_dir: Path,
    *,
    public_root: Path,
) -> list[dict[str, Any]]:
    paths = [
        Path(__file__).resolve(strict=False),
        Path(private_state_scan.__file__).resolve(strict=False),
        public_root / "core/private_state_forbidden_classes.json",
        *_input_paths(input_dir, include_negative=False),
    ]
    return sorted(
        (
            _file_freshness_entry(path, public_root=public_root)
            for path in _dedupe_paths(paths)
        ),
        key=lambda item: str(item["path"]),
    )


def _fresh_loop_bundle_receipt(
    out_dir: str | Path,
    *,
    freshness_digest: str,
) -> dict[str, Any] | None:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    receipt_path = target / BUNDLE_RESULT_NAME
    if not receipt_path.is_file():
        return None
    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("card_schema_version") != CARD_SCHEMA_VERSION:
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("input_mode") != "exported_verifier_trace_repair_bundle":
        return None
    if payload.get("freshness_digest") != freshness_digest:
        return None
    result = dict(payload)
    result["receipt_reused"] = True
    result["freshness_status"] = "current"
    return result


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
        "body_material_status": "excluded_forbidden_material",
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
    target_refs = _strings(protocol.get("target_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    copied_material = _rows(protocol, "copied_material")
    omitted = _rows(protocol, "omitted_material")
    findings: list[dict[str, Any]] = []
    if len(source_refs) < 4 or len(source_pattern_ids) < 3 or len(target_refs) < 3:
        findings.append(
            _finding(
                "VERIFIER_TRACE_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Verifier trace repair projection must cite macro source refs, pattern ids, and copied-material target refs.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    if not copied_material:
        findings.append(
            _finding(
                "VERIFIER_TRACE_COPIED_MATERIAL_REQUIRED",
                "Verifier trace repair projection must carry copied non-secret macro material provenance.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="copied_material",
            )
        )
    for material in copied_material:
        missing = [
            field
            for field in (
                "source_ref",
                "source_sha256",
                "target_refs",
                "validation_refs",
            )
            if not material.get(field)
        ]
        if material.get("body_material_status") != BODY_MATERIAL_STATUS:
            missing.append("body_material_status")
        if missing:
            findings.append(
                _finding(
                    "VERIFIER_TRACE_COPIED_MATERIAL_PROVENANCE_INCOMPLETE",
                    "Copied verifier trace material must retain source digest, target refs, validation refs, and copied-material status.",
                    case_id="projection_protocol_floor",
                    subject_id=str(material.get("material_id") or "copied_material"),
                    subject_kind="copied_material",
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
        and target_refs
        and copied_material
        and not findings
        else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "source_digests": protocol.get("source_digests") if isinstance(protocol.get("source_digests"), dict) else SOURCE_DIGESTS,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "target_refs": target_refs,
        "copied_material": copied_material,
        "body_copied_material_count": len(copied_material),
        "omitted_material_count": len(omitted),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_source_module_manifest(
    input_dir: Path,
    *,
    public_root: Path,
    required: bool,
) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return {
            "status": "blocked" if required else "not_present",
            "source_modules_pass": not required,
            "source_module_manifest_ref": "",
            "module_count": 0,
            "verified_module_count": 0,
            "modules": [],
            "findings": []
            if not required
            else [
                _finding(
                    "VERIFIER_TRACE_SOURCE_MODULE_MANIFEST_MISSING",
                    "Exported verifier trace repair bundles must include a source_module_manifest.json for copied macro bodies.",
                    case_id="source_module_manifest_floor",
                    subject_id=SOURCE_MODULE_MANIFEST_REF,
                    subject_kind="source_module_manifest",
                )
            ],
            "source_open_body_imports": {},
        }

    manifest = read_json_strict(manifest_path)
    modules = _rows(manifest, "modules")
    findings: list[dict[str, Any]] = []
    if manifest.get("source_import_class") not in SOURCE_MODULE_IMPORT_CLASSES:
        findings.append(
            _finding(
                "VERIFIER_TRACE_SOURCE_MODULE_IMPORT_CLASS_INVALID",
                "Source-module manifest must classify verifier trace repair bodies as copied or source-faithful public-safe macro bodies.",
                case_id="source_module_manifest_floor",
                subject_id=str(manifest.get("manifest_id") or SOURCE_MODULE_MANIFEST_REF),
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_in_receipt") is not False:
        findings.append(
            _finding(
                "VERIFIER_TRACE_SOURCE_MODULE_BODY_IN_RECEIPT_FORBIDDEN",
                "Copied macro body source modules must stay in source_modules, not receipt bodies.",
                case_id="source_module_manifest_floor",
                subject_id=str(manifest.get("manifest_id") or SOURCE_MODULE_MANIFEST_REF),
                subject_kind="source_module_manifest",
            )
        )
    if required and len(modules) != len(SOURCE_REFS):
        findings.append(
            _finding(
                "VERIFIER_TRACE_SOURCE_MODULE_COUNT_MISMATCH",
                "Verifier trace repair source-module manifest must account for every declared Ring2 source ref.",
                case_id="source_module_manifest_floor",
                subject_id=str(manifest.get("manifest_id") or SOURCE_MODULE_MANIFEST_REF),
                subject_kind="source_module_manifest",
            )
        )

    module_results: list[dict[str, Any]] = []
    verified_ids: list[str] = []
    material_classes: set[str] = set()
    for row in modules:
        source_ref = str(row.get("source_ref") or "")
        target = _target_path_from_module(input_dir, row)
        exists = target.is_file()
        expected_digest = str(
            row.get("target_sha256") or row.get("sha256") or ""
        ).removeprefix("sha256:")
        actual_digest = _sha256_file(target) if exists else ""
        expected_line_count = row.get("target_line_count", row.get("line_count"))
        actual_line_count = _line_count(target) if exists else None
        expected_byte_count = row.get("target_byte_count", row.get("byte_count"))
        actual_byte_count = target.stat().st_size if exists else None
        digest_matches = bool(expected_digest) and actual_digest == expected_digest
        line_count_matches = (
            isinstance(expected_line_count, int)
            and actual_line_count == expected_line_count
        )
        byte_count_matches = (
            isinstance(expected_byte_count, int)
            and actual_byte_count == expected_byte_count
        )
        material_id = str(
            row.get("module_id") or SOURCE_MODULE_MATERIAL_IDS.get(source_ref) or ""
        )
        material_class = str(
            row.get("material_class")
            or SOURCE_MODULE_MATERIAL_CLASSES.get(source_ref)
            or "public_macro_receipt_body"
        )
        material_classes.add(material_class)

        if source_ref not in SOURCE_REFS:
            findings.append(
                _finding(
                    "VERIFIER_TRACE_SOURCE_MODULE_UNKNOWN_SOURCE_REF",
                    "Source-module rows must cite one of the declared Ring2 verifier trace repair source refs.",
                    case_id="source_module_manifest_floor",
                    subject_id=source_ref or material_id or "source_module",
                    subject_kind="source_module",
                )
            )
        if not exists:
            findings.append(
                _finding(
                    "VERIFIER_TRACE_SOURCE_MODULE_TARGET_MISSING",
                    "Declared verifier trace repair source module target is missing.",
                    case_id="source_module_manifest_floor",
                    subject_id=source_ref or material_id or "source_module",
                    subject_kind="source_module",
                )
            )
        elif not digest_matches:
            findings.append(
                _finding(
                    "VERIFIER_TRACE_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Copied verifier trace repair source module digest differs from the macro source digest.",
                    case_id="source_module_manifest_floor",
                    subject_id=source_ref,
                    subject_kind="source_module",
                )
            )
        elif not line_count_matches or not byte_count_matches:
            findings.append(
                _finding(
                    "VERIFIER_TRACE_SOURCE_MODULE_SIZE_MISMATCH",
                    "Copied verifier trace repair source module line or byte count differs from the manifest.",
                    case_id="source_module_manifest_floor",
                    subject_id=source_ref,
                    subject_kind="source_module",
                )
            )
        else:
            verified_ids.append(material_id)

        module_results.append(
            {
                "module_id": material_id,
                "source_ref": source_ref,
                "target_ref": _display(target, public_root=public_root),
                "material_class": material_class,
                "body_copied": exists,
                "body_in_receipt": False,
                "expected_digest": f"sha256:{expected_digest}" if expected_digest else "",
                "source_digest": str(row.get("source_sha256") or ""),
                "actual_digest": f"sha256:{actual_digest}" if actual_digest else "",
                "digest_matches": digest_matches,
                "source_to_target_relation": str(
                    row.get("source_to_target_relation") or ""
                ),
                "line_count": actual_line_count,
                "line_count_matches": line_count_matches,
                "byte_count": actual_byte_count,
                "byte_count_matches": byte_count_matches,
            }
        )

    status = PASS if not findings and len(verified_ids) == len(SOURCE_REFS) else "blocked"
    source_open_body_imports = {
        "status": status,
        "body_material_status": SOURCE_MODULE_BODY_MATERIAL_STATUS,
        "body_material_count": len(verified_ids),
        "body_material_ids": sorted(verified_ids),
        "material_classes": sorted(material_classes),
        "aggregate_floor_ref": (
            "examples/formal_math_verifier_trace_repair_loop/"
            "exported_verifier_trace_repair_bundle/bundle_manifest.json::source_open_body_imports"
        ),
        "source_manifest_refs": [SOURCE_MODULE_MANIFEST_REF],
        "body_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "authority_ceiling": {
            "body_text_in_receipt": False,
            "proof_body_or_oracle_proof_text_exported": False,
            "provider_payload_exported": False,
            "lean_lake_execution_authorized": False,
            "formal_proof_authority": False,
            "runtime_correctness_claim": False,
            "release_authorized": False,
        },
    }
    return {
        "status": status,
        "source_modules_pass": status == PASS,
        "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
        "manifest_id": manifest.get("manifest_id"),
        "module_count": len(modules),
        "verified_module_count": len(verified_ids),
        "modules": module_results,
        "findings": findings,
        "source_open_body_imports": source_open_body_imports,
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
            "Verifier trace rows may cite provider advice as public advisory fields, not provider payload bodies.",
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
                "source_problem_id": row.get("source_problem_id"),
                "source_split": row.get("source_split"),
                "source_domain": row.get("source_domain"),
                "source_run_ref": row.get("source_run_ref"),
                "oracle_repair_contrast_ref": row.get("oracle_repair_contrast_ref"),
                "verifier_class": row.get("verifier_class"),
                "trace_grade": row.get("trace_grade"),
                "repair_action_id": row.get("repair_action_id"),
                "failure_mode_id": row.get("failure_mode_id"),
                "cold_rerun_receipt_ref": row.get("cold_rerun_receipt_ref"),
                "promoted_after_cold_rerun": row.get("promoted_after_cold_rerun") is True,
                "trace_event_count": len(trace_events),
                "body_material_status": row.get("body_material_status") or "real_ring2_trace_row",
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
                "source_problem_ids": _strings(row.get("source_problem_ids")),
                "source_candidate_id": row.get("source_candidate_id"),
                "body_material_status": row.get("body_material_status") or "real_ring2_failure_mode_row",
            }
            for row in ledger_rows
        ],
        "curriculum_edges": [
            {
                "from_failure_mode_id": row.get("from_failure_mode_id"),
                "to_curriculum_node_id": row.get("to_curriculum_node_id"),
                "delta_class": row.get("delta_class"),
                "source_candidate_id": row.get("source_candidate_id"),
                "body_material_status": row.get("body_material_status") or "real_ring2_curriculum_edge",
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
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    secret_scan.pop("forbidden_output_fields", None)
    secret_scan.pop("body_redacted", None)
    secret_scan.pop("scan_scope", None)
    secret_scan["forbidden_output_field_labels_omitted"] = True
    secret_scan["body_material_status"] = "secret_exclusion_scan_no_payload_bodies"

    projection = validate_projection_protocol(payloads["projection_protocol"])
    source_modules = validate_source_module_manifest(
        input_dir,
        public_root=public_root,
        required=input_mode == "exported_verifier_trace_repair_bundle",
    )
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
    findings = _merge_findings(projection, source_modules, attempts, curriculum, promotion)
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and source_modules["source_modules_pass"]
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
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "macro_run_id": RUN_ID,
        "premise_retrieval_variant_id": PREMISE_RETRIEVAL_VARIANT_ID,
        "oracle_repair_variant_id": ORACLE_REPAIR_VARIANT_ID,
        "body_material_status": BODY_MATERIAL_STATUS,
        "body_material_contract": BODY_MATERIAL_CONTRACT,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_digests": projection["source_digests"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "target_refs": projection["target_refs"],
        "copied_material": projection["copied_material"],
        "body_copied_material_count": projection["body_copied_material_count"],
        "source_module_manifest_status": source_modules["status"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_manifest": source_modules,
        "source_modules_pass": source_modules["source_modules_pass"],
        "source_module_count": source_modules["module_count"],
        "source_open_body_imports": source_modules["source_open_body_imports"],
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
        "body_material_status": result["body_material_status"],
        "body_material_contract": result["body_material_contract"],
        "copied_material": result["copied_material"],
        "body_copied_material_count": result["body_copied_material_count"],
        "source_module_manifest": result["source_module_manifest"],
        "source_modules_pass": result["source_modules_pass"],
        "source_open_body_imports": result["source_open_body_imports"],
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
        "secret_exclusion_scan": result["secret_exclusion_scan"],
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
        "body_material_status": result["body_material_status"],
        "body_material_contract": result["body_material_contract"],
        "copied_material": result["copied_material"],
        "body_copied_material_count": result["body_copied_material_count"],
        "source_refs": result["source_refs"],
        "source_digests": result["source_digests"],
        "target_refs": result["target_refs"],
        "source_module_manifest": result["source_module_manifest"],
        "source_modules_pass": result["source_modules_pass"],
        "source_open_body_imports": result["source_open_body_imports"],
        "negative_case_coverage": {
            "expected": result["expected_negative_cases"],
            "observed": result["observed_negative_cases"],
            "missing": result["missing_negative_cases"],
        },
        "trace_attempt_count": result["attempt_count"],
        "repair_action_count": result["repair_action_count"],
        "cold_rerun_promotion_count": result["cold_rerun_promotion_count"],
        "formal_proof_authority": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
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
        "body_material_status": result["body_material_status"],
        "body_copied_material_count": result["body_copied_material_count"],
        "source_refs": result["source_refs"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_open_body_imports": result["source_open_body_imports"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
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
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    out = Path(out_dir)
    if not out.is_absolute():
        out = Path.cwd() / out
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    freshness_basis = _loop_bundle_freshness_basis(input_path, public_root=public_root)
    freshness_digest = _json_digest(freshness_basis)
    if reuse_fresh_receipt:
        cached = _fresh_loop_bundle_receipt(out, freshness_digest=freshness_digest)
        if cached is not None:
            return cached

    out.mkdir(parents=True, exist_ok=True)
    result = _build_result(
        input_path,
        command=command,
        input_mode="exported_verifier_trace_repair_bundle",
        include_negative=False,
    )
    result.update(
        {
            "card_schema_version": CARD_SCHEMA_VERSION,
            "freshness_basis": freshness_basis,
            "freshness_digest": freshness_digest,
            "freshness_status": "current",
            "receipt_reused": False,
        }
    )
    bundle_path = out / BUNDLE_RESULT_NAME
    receipt_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_verifier_trace_repair_bundle_validation_result_v1",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "freshness_basis": freshness_basis,
        "freshness_digest": freshness_digest,
        "freshness_status": "current",
        "receipt_reused": False,
        "receipt_paths": [_display(bundle_path, public_root=receipt_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def _result_card(result: dict[str, Any]) -> dict[str, Any]:
    secret_scan = result.get("secret_exclusion_scan")
    scan_summary = secret_scan if isinstance(secret_scan, dict) else {}
    source_imports = result.get("source_open_body_imports")
    source_import_summary = source_imports if isinstance(source_imports, dict) else {}
    input_mode = result.get("input_mode")
    action = (
        "run-loop-bundle"
        if input_mode == "exported_verifier_trace_repair_bundle"
        else "run"
    )
    card_id = (
        "formal_math_verifier_trace_repair_loop_bundle_card"
        if action == "run-loop-bundle"
        else "formal_math_verifier_trace_repair_loop_fixture_card"
    )
    receipt_paths = [
        Path(str(path)).name if Path(str(path)).is_absolute() else str(path)
        for path in result.get("receipt_paths", [])
    ]
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": ORGAN_ID,
        "command": result.get("command"),
        "input_mode": input_mode,
        "bundle_id": result.get("bundle_id"),
        "card_id": card_id,
        "output_profile": "compact_card_no_trace_rows_or_source_bodies",
        "full_output_available": True,
        "full_output_command": (
            "python -m microcosm_core.organs.formal_math_verifier_trace_repair_loop "
            f"{action} --input <input> --out <out>"
        ),
        "receipt_paths": receipt_paths,
        "receipt_reused": bool(result.get("receipt_reused")),
        "freshness_status": result.get("freshness_status", "rebuilt"),
        "freshness_digest": result.get("freshness_digest"),
        "expected_negative_cases": result.get("expected_negative_cases", []),
        "missing_negative_cases": result.get("missing_negative_cases", []),
        "error_codes": result.get("error_codes", []),
        "secret_exclusion_scan_summary": {
            "status": scan_summary.get("status"),
            "scanned_path_count": scan_summary.get("scanned_path_count"),
            "blocking_hit_count": scan_summary.get("blocking_hit_count"),
            "hit_count": scan_summary.get("hit_count"),
            "body_material_status": scan_summary.get("body_material_status"),
            "body_text_exported": False,
        },
        "source_open_body_imports_summary": {
            "body_material_count": source_import_summary.get("body_material_count"),
            "body_in_receipt": source_import_summary.get("body_in_receipt"),
            "source_module_count": result.get("source_module_count"),
            "source_module_manifest_status": result.get("source_module_manifest_status"),
        },
        "authority_ceiling": {
            "lean_lake_execution_authorized": False,
            "formal_proof_authority": False,
            "provider_calls_authorized": False,
            "proof_bodies_allowed": False,
            "oracle_premise_ids_allowed": False,
            "human_approval_as_proof_authority": False,
            "release_authorized": False,
        },
        "body_material_status": result.get("body_material_status"),
        "body_copied_material_count": result.get("body_copied_material_count"),
        "attempt_count": result.get("attempt_count"),
        "trace_event_count": result.get("trace_event_count"),
        "repair_action_count": result.get("repair_action_count"),
        "cold_rerun_promotion_count": result.get("cold_rerun_promotion_count"),
        "failure_mode_count": result.get("failure_mode_count"),
        "curriculum_edge_count": result.get("curriculum_edge_count"),
        "source_ref_count": len(result.get("source_refs", [])),
        "source_module_count": result.get("source_module_count"),
        "source_modules_pass": result.get("source_modules_pass"),
        "trace_rows_omitted": True,
        "source_module_bodies_omitted": True,
        "proof_bodies_exported": False,
        "oracle_premise_ids_exported": False,
        "provider_payloads_exported": False,
        "omitted_full_payload_keys": [
            key for key in CARD_OMITTED_FULL_PAYLOAD_KEYS if key in result
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="formal_math_verifier_trace_repair_loop")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact first-screen card instead of the full result payload.",
    )
    bundle_parser = sub.add_parser("run-loop-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact first-screen card instead of the full result payload.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = (
        "python -m microcosm_core.organs.formal_math_verifier_trace_repair_loop "
        f"{args.action} --input {args.input} --out {args.out}"
    )
    if args.card:
        command += " --card"
    if args.action == "run":
        result = run(
            args.input,
            args.out,
            command=command,
        )
    elif args.action == "run-loop-bundle":
        result = run_loop_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    else:
        return 2
    output = _result_card(result) if args.card else result
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
