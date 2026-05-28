from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_research_replication_trace,
)
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "research_replication_rubric_artifact_replay"
FIXTURE_ID = "first_wave.research_replication_rubric_artifact_replay"
VALIDATOR_ID = "validator.microcosm.organs.research_replication_rubric_artifact_replay"

RESULT_NAME = "research_replication_rubric_artifact_replay_result.json"
BOARD_NAME = "research_replication_rubric_artifact_replay_board.json"
VALIDATION_RECEIPT_NAME = (
    "research_replication_rubric_artifact_replay_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "research_replication_rubric_artifact_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_research_replication_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "research_replication_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "expected_negative_cases",
    "observed_negative_cases",
    "missing_negative_cases",
    "error_codes",
    "findings",
    "secret_exclusion_scan",
    "public_agent_execution_trace_spans",
    "authority_ceiling",
    "anti_claim",
    "source_module_imports",
    "source_open_body_imports",
    "source_refs",
    "source_pattern_ids",
    "projection_receipt_refs",
    "target_refs",
    "target_symbols",
    "public_runtime_refs",
    "body_import_verification",
    "required_replay_fields",
    "rubric_axes",
    "declared_artifact_hash_refs",
    "research_replays",
    "replication_board",
)
SOURCE_MODULE_MANIFEST_REF = (
    "examples/research_replication_rubric_artifact_replay/"
    "exported_research_replication_bundle/source_module_manifest.json"
)
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_BODY_STATUS = "copied_non_secret_macro_body_with_provenance"
PUBLIC_SAFE_SOURCE_MODULE_CLASSES = {"public_macro_pattern_body"}

INPUT_NAMES = (
    "projection_protocol.json",
    "replication_policy.json",
    "research_replays.json",
)
NEGATIVE_INPUT_NAMES = (
    "original_author_code_reuse_forbidden.json",
    "hidden_rubric_leakage.json",
    "report_only_success.json",
    "benchmark_performance_claim.json",
    "private_paper_body_leakage.json",
    "unbounded_compute_search.json",
    "final_answer_only_grading.json",
    "undeclared_artifact_hash_ref.json",
)

EXPECTED_NEGATIVE_CASES = {
    "original_author_code_reuse_forbidden": [
        "REPLICATION_AUTHOR_CODE_REUSE_FORBIDDEN"
    ],
    "hidden_rubric_leakage": ["REPLICATION_HIDDEN_RUBRIC_LEAKAGE"],
    "report_only_success": ["REPLICATION_REPORT_ONLY_SUCCESS"],
    "benchmark_performance_claim": ["REPLICATION_BENCHMARK_PERFORMANCE_OVERCLAIM"],
    "private_paper_body_leakage": ["REPLICATION_PRIVATE_BODY_LEAKAGE"],
    "unbounded_compute_search": ["REPLICATION_UNBOUNDED_COMPUTE_SEARCH"],
    "final_answer_only_grading": ["REPLICATION_FINAL_ANSWER_ONLY_GRADING"],
    "undeclared_artifact_hash_ref": ["REPLICATION_UNDECLARED_ARTIFACT_HASH_REF"],
}

REQUIRED_REPLAY_FIELDS = {
    "paper_id",
    "contribution_decomposition_ref",
    "rubric_tree_ref",
    "allowed_public_input_refs",
    "scratch_repo_scaffold_ref",
    "experiment_dag_ref",
    "metric_script_refs",
    "artifact_hash_refs",
    "declared_artifact_hash_refs",
    "grader_report_ref",
    "cost_runtime_budget_ref",
    "ablation_diff_ref",
    "failure_taxonomy_ref",
    "cold_rerun_receipt_ref",
}
REQUIRED_RUBRIC_AXES = {
    "contribution_decomposition",
    "artifact_replay",
    "experiment_dag",
    "metric_script",
    "grader_alignment",
    "budget_boundary",
    "failure_taxonomy",
    "cold_rerun",
}
FORBIDDEN_BODY_KEYS = (
    "private_paper_body",
    "private_data_body",
    "raw_dataset_body",
    "hidden_rubric_body",
    "provider_payload",
    "original_author_code_body",
    "raw_paper_body",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_agent_execution_trace_refactor_over_research_replication_replay_fixture",
    "replication_success_claim_authorized_without_artifact_replay": False,
    "undeclared_artifact_hash_ref_authorized": False,
    "benchmark_performance_claim_authorized": False,
    "original_author_code_reuse_authorized": False,
    "hidden_rubric_export_authorized": False,
    "private_paper_or_data_body_export_authorized": False,
    "unbounded_compute_search_authorized": False,
    "final_answer_only_grading_authorized": False,
    "provider_calls_authorized": False,
    "publication_authorized": False,
}
ANTI_CLAIM = (
    "Research replication rubric-artifact replay validates public contribution, "
    "rubric, experiment-DAG, metric-script, declared artifact-hash roster, "
    "grader, budget, ablation, failure-taxonomy, cold-rerun receipts, and "
    "public execution-trace spans. Synthetic rows remain fixture inputs around "
    "that real replay contract. It does not claim benchmark performance, use undeclared artifact hashes, "
    "reuse forbidden original-author code, expose private paper or data bodies, "
    "run providers, perform unbounded compute search, grade final answers alone, "
    "or authorize publication."
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
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _strip_microcosm_prefix(ref: str) -> str:
    prefix = "microcosm-substrate/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


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


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    bundle_manifest = input_dir / "bundle_manifest.json"
    if bundle_manifest.is_file():
        paths.append(bundle_manifest)
    return paths


def _source_module_manifest_path(input_dir: Path, *, public_root: Path) -> Path:
    local_manifest = input_dir / "source_module_manifest.json"
    if local_manifest.is_file():
        return local_manifest
    return public_root / SOURCE_MODULE_MANIFEST_REF


def _source_module_target_path(
    row: dict[str, Any],
    *,
    manifest_path: Path,
    public_root: Path,
) -> tuple[Path, str]:
    target_ref = _strip_microcosm_prefix(str(row.get("target_ref") or ""))
    row_path = str(row.get("path") or "")
    if target_ref:
        return public_root / target_ref, target_ref
    if row_path:
        path = manifest_path.parent / row_path
        return path, _display(path, public_root=public_root)
    return public_root, ""


def _source_artifact_paths(input_dir: Path, *, public_root: Path) -> list[Path]:
    manifest_path = _source_module_manifest_path(input_dir, public_root=public_root)
    if not manifest_path.is_file():
        return []
    manifest = read_json_strict(manifest_path)
    paths = [manifest_path]
    for row in _rows(manifest, "modules"):
        target_path, _target_ref = _source_module_target_path(
            row, manifest_path=manifest_path, public_root=public_root
        )
        if target_path.is_file():
            paths.append(target_path)
    return paths


def _freshness_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    source = Path(input_dir)
    public_root = _public_root_for_path(source)
    return [
        *_input_paths(source, include_negative=include_negative),
        *_source_artifact_paths(source, public_root=public_root),
        public_root / "core/private_state_forbidden_classes.json",
    ]


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    source = Path(input_dir)
    if not source.is_absolute():
        source = Path.cwd() / source
    public_root = _public_root_for_path(source)

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[Path] = set()
    for path in _freshness_paths(source, include_negative=include_negative):
        key = path.resolve(strict=False)
        if key in seen:
            continue
        seen.add(key)
        display = _display(path, public_root=public_root)
        if path.is_file():
            rows.append(
                {
                    "path": display,
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        else:
            missing.append(display)

    validator_schema_version = (
        "research_replication_rubric_artifact_replay_result_v1"
        if include_negative
        else "exported_research_replication_bundle_validation_result_v1"
    )
    basis_digest = hashlib.sha256(
        json.dumps(
            {
                "card_schema_version": CARD_SCHEMA_VERSION,
                "include_negative": include_negative,
                "inputs": rows,
                "missing_inputs": missing,
                "validator_schema_version": validator_schema_version,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "research_replication_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_replication_bundle_receipt(
    input_dir: Path,
    out_dir: Path,
    *,
    command: str,
) -> dict[str, Any] | None:
    path = out_dir / BUNDLE_RESULT_NAME
    if not path.is_file():
        return None
    try:
        payload = read_json_strict(path)
    except (OSError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != (
        "exported_research_replication_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("status") != PASS:
        return None
    if payload.get("input_mode") != "exported_research_replication_bundle":
        return None
    if payload.get("command") != command:
        return None
    basis = _freshness_basis(input_dir, include_negative=False)
    existing_basis = payload.get("freshness_basis")
    if not isinstance(existing_basis, dict):
        return None
    if existing_basis.get("basis_digest") != basis["basis_digest"]:
        return None
    if basis["missing_path_count"]:
        return None
    reused = dict(payload)
    reused["freshness_basis"] = basis
    reused["receipt_reused"] = True
    return reused


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


def validate_source_module_imports(
    input_dir: Path,
    *,
    public_root: Path,
) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(input_dir, public_root=public_root)
    manifest_ref = _display(manifest_path, public_root=public_root)
    findings: list[dict[str, Any]] = []
    modules: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        findings.append(
            _finding(
                "REPLICATION_SOURCE_MODULE_MANIFEST_MISSING",
                "Research replication body floor requires a source_module_manifest.json for copied macro provenance bodies.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
        return {
            "status": "blocked",
            "source_module_manifest_ref": manifest_ref,
            "module_count": 0,
            "copied_source_artifact_count": 0,
            "modules": [],
            "findings": findings,
            "observed_negative_cases": {},
        }

    manifest = read_json_strict(manifest_path)
    if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
        findings.append(
            _finding(
                "REPLICATION_SOURCE_IMPORT_CLASS_MISMATCH",
                "Source module manifest must declare copied_non_secret_macro_body.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_in_receipt") is not False:
        findings.append(
            _finding(
                "REPLICATION_SOURCE_BODY_IN_RECEIPT_FORBIDDEN",
                "Copied macro pattern bodies may live in source_artifacts, not in receipts.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("module_count") != len(_rows(manifest, "modules")):
        findings.append(
            _finding(
                "REPLICATION_SOURCE_MODULE_COUNT_MISMATCH",
                "Source module manifest module_count must equal its module rows.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )

    for row in _rows(manifest, "modules"):
        module_id = str(row.get("module_id") or "")
        target_path, target_ref = _source_module_target_path(
            row, manifest_path=manifest_path, public_root=public_root
        )
        material_class = str(row.get("material_class") or "")
        expected_digest = str(row.get("sha256") or "")
        relation = str(row.get("source_to_target_relation") or "")
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "REPLICATION_SOURCE_MODULE_IMPORT_CLASS_MISMATCH",
                    "Source module rows must declare copied_non_secret_macro_body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_MODULE_CLASSES:
            findings.append(
                _finding(
                    "REPLICATION_SOURCE_MODULE_CLASS_FORBIDDEN",
                    "Research replication may import public macro pattern provenance bodies only.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if row.get("body_copied") is not True or row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "REPLICATION_SOURCE_MODULE_BODY_BOUNDARY_INVALID",
                    "Source module rows must set body_copied=true and body_in_receipt=false.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if relation not in {"exact_copy", "source_faithful_json_slice"}:
            findings.append(
                _finding(
                    "REPLICATION_SOURCE_MODULE_RELATION_UNVERIFIED",
                    "Source module rows must state exact_copy or source_faithful_json_slice.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if not target_path.is_file():
            findings.append(
                _finding(
                    "REPLICATION_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target must exist inside the public bundle.",
                    case_id="source_module_manifest_floor",
                    subject_id=target_ref or module_id or "source_module",
                    subject_kind="source_module",
                )
            )
            continue
        actual_digest = _sha256(target_path)
        if expected_digest != actual_digest:
            findings.append(
                _finding(
                    "REPLICATION_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module target digest must match source_module_manifest.json.",
                    case_id="source_module_manifest_floor",
                    subject_id=target_ref or module_id or "source_module",
                    subject_kind="source_module",
                )
            )
        modules.append(
            {
                "module_id": module_id,
                "source_ref": str(row.get("source_ref") or ""),
                "target_ref": target_ref,
                "material_class": material_class,
                "sha256": expected_digest,
                "actual_sha256": actual_digest,
                "line_count": row.get("line_count"),
                "source_to_target_relation": relation,
                "body_in_receipt": False,
            }
        )

    return {
        "status": PASS if modules and not findings else "blocked",
        "source_module_manifest_ref": manifest_ref,
        "module_count": len(modules),
        "copied_source_artifact_count": len(modules),
        "modules": sorted(modules, key=lambda row: row["module_id"]),
        "findings": findings,
        "observed_negative_cases": {},
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
        "body_in_receipt": False,
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
    target_refs = _strings(protocol.get("target_refs"))
    target_symbols = _strings(protocol.get("target_symbols"))
    public_runtime_refs = _strings(protocol.get("public_runtime_refs"))
    body_import_status = str(protocol.get("body_import_status") or "")
    body_import_verification = protocol.get("body_import_verification", {})
    findings: list[dict[str, Any]] = []
    if (
        "research_replication_rubric_artifact_replay_compound"
        not in source_pattern_ids
        or len(source_refs) < 3
        or len(projection_receipts) < 2
        or "extension_of_existing_public_refactor_landed" != body_import_status
        or not isinstance(body_import_verification, dict)
        or body_import_verification.get("verification_mode")
        != "extension_of_existing_public_refactor"
        or len(target_refs) < 2
        or len(target_symbols) < 2
        or len(public_runtime_refs) < 2
    ):
        findings.append(
            _finding(
                "REPLICATION_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Research replication projection must cite source patterns, receipts, target refs, runtime refs, and public trace import verification.",
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
        "target_refs": target_refs,
        "target_symbols": target_symbols,
        "public_runtime_refs": public_runtime_refs,
        "body_import_status": body_import_status,
        "body_import_verification": body_import_verification,
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_replication_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    required_fields = set(_strings(policy.get("required_replay_fields")))
    rubric_axes = set(_strings(policy.get("rubric_axes")))
    findings: list[dict[str, Any]] = []
    if not REQUIRED_REPLAY_FIELDS.issubset(required_fields):
        findings.append(
            _finding(
                "REPLICATION_POLICY_REPLAY_FIELDS_INCOMPLETE",
                "Replication policy must require every artifact replay evidence field.",
                case_id="replication_policy_floor",
                subject_id=str(policy.get("policy_id") or "replication_policy"),
                subject_kind="replication_policy",
            )
        )
    if not REQUIRED_RUBRIC_AXES.issubset(rubric_axes):
        findings.append(
            _finding(
                "REPLICATION_POLICY_RUBRIC_AXES_INCOMPLETE",
                "Replication policy must include rubric axes for artifact, grader, budget, failure, and cold rerun evidence.",
                case_id="replication_policy_floor",
                subject_id=str(policy.get("policy_id") or "replication_policy"),
                subject_kind="replication_policy",
            )
        )
    for key, code in (
        ("hidden_rubric_export_authorized", "REPLICATION_HIDDEN_RUBRIC_LEAKAGE"),
        (
            "benchmark_performance_claim_authorized",
            "REPLICATION_BENCHMARK_PERFORMANCE_OVERCLAIM",
        ),
        ("unbounded_compute_search_authorized", "REPLICATION_UNBOUNDED_COMPUTE_SEARCH"),
        ("final_answer_only_grading_authorized", "REPLICATION_FINAL_ANSWER_ONLY_GRADING"),
    ):
        if policy.get(key) is not False:
            findings.append(
                _finding(
                    code,
                    f"Replication policy must set {key}=false.",
                    case_id=key.replace("_authorized", ""),
                    subject_id=str(policy.get("policy_id") or "replication_policy"),
                    subject_kind="replication_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "required_replay_fields": sorted(required_fields),
        "rubric_axes": sorted(rubric_axes),
        "findings": findings,
        "observed_negative_cases": {},
    }


def _has_required_replay_fields(row: dict[str, Any]) -> bool:
    return all(row.get(field) for field in REQUIRED_REPLAY_FIELDS)


def _validate_replay_row(
    row: dict[str, Any],
    *,
    case_id: str,
    observed: dict[str, set[str]],
    findings: list[dict[str, Any]],
) -> None:
    paper_id = str(row.get("paper_id") or row.get("case_id") or "research_replay")
    if not _has_required_replay_fields(row):
        _record(
            findings,
            observed,
            "REPLICATION_REPLAY_ARTIFACTS_INCOMPLETE",
            "Replication replay row must cite rubric, artifact, metric, grader, budget, ablation, failure, and cold rerun refs.",
            case_id=case_id,
            subject_id=paper_id,
            subject_kind="research_replay",
        )
    artifact_hash_refs = set(_strings(row.get("artifact_hash_refs")))
    declared_artifact_hash_refs = set(_strings(row.get("declared_artifact_hash_refs")))
    undeclared_artifact_hash_refs = sorted(artifact_hash_refs - declared_artifact_hash_refs)
    if artifact_hash_refs and (
        not declared_artifact_hash_refs or undeclared_artifact_hash_refs
    ):
        _record(
            findings,
            observed,
            "REPLICATION_UNDECLARED_ARTIFACT_HASH_REF",
            "Every artifact hash ref must belong to the declared public artifact-hash roster.",
            case_id=case_id,
            subject_id=paper_id,
            subject_kind="research_replay",
        )
    if (
        row.get("original_author_code_reused") is True
        and row.get("original_author_code_allowed") is False
    ):
        _record(
            findings,
            observed,
            "REPLICATION_AUTHOR_CODE_REUSE_FORBIDDEN",
            "Original-author code reuse is forbidden for this replay row.",
            case_id=case_id,
            subject_id=paper_id,
            subject_kind="research_replay",
        )
    if row.get("hidden_rubric_exported") is not False or "hidden_rubric_body" in _walk_keys(row):
        _record(
            findings,
            observed,
            "REPLICATION_HIDDEN_RUBRIC_LEAKAGE",
            "Hidden rubric bodies or exports are not public replay inputs.",
            case_id=case_id,
            subject_id=paper_id,
            subject_kind="research_replay",
        )
    if row.get("replication_status") == "success" and (
        row.get("report_only_success") is True
        or not row.get("artifact_hash_refs")
        or not row.get("metric_script_refs")
        or not row.get("cold_rerun_receipt_ref")
    ):
        _record(
            findings,
            observed,
            "REPLICATION_REPORT_ONLY_SUCCESS",
            "Replication success must be backed by artifact hashes, metric scripts, and cold rerun evidence.",
            case_id=case_id,
            subject_id=paper_id,
            subject_kind="research_replay",
        )
    if (
        row.get("benchmark_performance_claim_authorized") is not False
        or row.get("benchmark_score_claim") is not None
    ):
        _record(
            findings,
            observed,
            "REPLICATION_BENCHMARK_PERFORMANCE_OVERCLAIM",
            "Synthetic replay cannot claim benchmark performance.",
            case_id=case_id,
            subject_id=paper_id,
            subject_kind="research_replay",
        )
    if any(key in FORBIDDEN_BODY_KEYS for key in _walk_keys(row)):
        _record(
            findings,
            observed,
            "REPLICATION_PRIVATE_BODY_LEAKAGE",
            "Replication replay must keep private paper, data, provider, and code bodies out.",
            case_id=case_id,
            subject_id=paper_id,
            subject_kind="research_replay",
        )
    if row.get("compute_search") == "unbounded" or row.get("compute_budget_capped") is not True:
        _record(
            findings,
            observed,
            "REPLICATION_UNBOUNDED_COMPUTE_SEARCH",
            "Replication replay must cite a capped compute/runtime budget.",
            case_id=case_id,
            subject_id=paper_id,
            subject_kind="research_replay",
        )
    if row.get("grading_mode") == "final_answer_only" or row.get("artifact_replay_required") is not True:
        _record(
            findings,
            observed,
            "REPLICATION_FINAL_ANSWER_ONLY_GRADING",
            "Replication grading requires artifact replay, not final-answer-only grading.",
            case_id=case_id,
            subject_id=paper_id,
            subject_kind="research_replay",
        )


def validate_research_replays(
    payload: object,
    negative_payloads: dict[str, Any],
) -> dict[str, Any]:
    rows = _rows(payload, "research_replays")
    positive_findings: list[dict[str, Any]] = []
    positive_observed: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        _validate_replay_row(
            row,
            case_id="positive_fixture_floor",
            observed=positive_observed,
            findings=positive_findings,
        )
    positive_status = PASS if len(rows) >= 2 and not positive_findings else "blocked"
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for case_id, payload in negative_payloads.items():
        row = payload if isinstance(payload, dict) else {}
        _validate_replay_row(row, case_id=case_id, observed=observed, findings=findings)
    declared_artifact_hash_refs = sorted(
        {
            artifact_ref
            for row in rows
            for artifact_ref in _strings(row.get("declared_artifact_hash_refs"))
        }
    )
    return {
        "status": positive_status,
        "paper_count": len({str(row.get("paper_id") or "") for row in rows}),
        "replay_count": len(rows),
        "artifact_replay_count": sum(1 for row in rows if row.get("artifact_replay_required") is True),
        "cold_rerun_count": sum(1 for row in rows if row.get("cold_rerun_receipt_ref")),
        "ablation_count": sum(1 for row in rows if row.get("ablation_diff_ref")),
        "grader_report_count": sum(1 for row in rows if row.get("grader_report_ref")),
        "failure_taxonomy_count": sum(1 for row in rows if row.get("failure_taxonomy_ref")),
        "declared_artifact_hash_refs": declared_artifact_hash_refs,
        "declared_artifact_hash_ref_count": len(declared_artifact_hash_refs),
        "research_replays": rows,
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
    source_imports = validate_source_module_imports(input_dir, public_root=public_root)
    secret_scan = scan_paths(
        [
            *_input_paths(input_dir, include_negative=include_negative),
            *_source_artifact_paths(input_dir, public_root=public_root),
        ],
        forbidden_classes=policy,
        display_root=public_root,
    )
    public_agent_execution_trace = build_public_research_replication_trace(input_dir)

    projection = validate_projection_protocol(payloads["projection_protocol"])
    replication_policy = validate_replication_policy(payloads["replication_policy"])
    negative_payloads = {
        name: payloads[name]
        for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
        if name in payloads
    }
    research_replays = validate_research_replays(
        payloads["research_replays"],
        negative_payloads,
    )
    observed = _merge_observed(
        projection, replication_policy, research_replays, source_imports
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(
        projection, replication_policy, research_replays, source_imports
    )
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    source_open_body_imports = {
        "schema_version": "research_replication_source_open_body_imports_v1",
        "status": source_imports["status"],
        "body_material_status": SOURCE_BODY_STATUS,
        "body_material_count": source_imports["module_count"],
        "body_material_ids": [
            row["module_id"] for row in source_imports["modules"] if row["module_id"]
        ],
        "material_classes": sorted(
            {
                row["material_class"]
                for row in source_imports["modules"]
                if row["material_class"]
            }
        ),
        "source_manifest_refs": [source_imports["source_module_manifest_ref"]],
        "aggregate_floor_ref": source_imports["source_module_manifest_ref"],
        "body_in_receipt": False,
        "reader_action": (
            "Open source_module_manifest.json and source_artifacts/ for copied "
            "macro pattern provenance bodies; receipts carry digests and status only."
        ),
    }
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and public_agent_execution_trace["status"] == PASS
        and projection["status"] == PASS
        and replication_policy["status"] == PASS
        and research_replays["status"] == PASS
        and source_imports["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "research_replication_rubric_artifact_replay_result_v1",
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
        "public_agent_execution_trace": public_agent_execution_trace,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_material_status": SOURCE_BODY_STATUS,
        "source_module_import_status": source_imports["status"],
        "source_module_manifest_ref": source_imports["source_module_manifest_ref"],
        "source_module_import_count": source_imports["module_count"],
        "copied_source_artifact_count": source_imports["copied_source_artifact_count"],
        "source_modules_pass": source_imports["status"] == PASS,
        "source_module_imports": source_imports["modules"],
        "source_open_body_imports": source_open_body_imports,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "target_refs": projection["target_refs"],
        "target_symbols": projection["target_symbols"],
        "public_runtime_refs": projection["public_runtime_refs"],
        "body_import_status": projection["body_import_status"],
        "body_import_verification": projection["body_import_verification"],
        "policy_id": replication_policy["policy_id"],
        "required_replay_fields": replication_policy["required_replay_fields"],
        "rubric_axes": replication_policy["rubric_axes"],
        "paper_count": research_replays["paper_count"],
        "replay_count": research_replays["replay_count"],
        "artifact_replay_count": research_replays["artifact_replay_count"],
        "cold_rerun_count": research_replays["cold_rerun_count"],
        "ablation_count": research_replays["ablation_count"],
        "grader_report_count": research_replays["grader_report_count"],
        "failure_taxonomy_count": research_replays["failure_taxonomy_count"],
        "declared_artifact_hash_ref_count": research_replays[
            "declared_artifact_hash_ref_count"
        ],
        "declared_artifact_hash_refs": research_replays["declared_artifact_hash_refs"],
        "research_replays": research_replays["research_replays"],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "research_replication_rubric_artifact_replay_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "research_replication_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "rubric_before_replication_claim",
                "count": result["paper_count"],
                "authority": "rubric_tree_ref_and_contribution_decomposition_ref_required",
            },
            {
                "mechanic_id": "declared_artifact_hash_roster_binding",
                "count": result["declared_artifact_hash_ref_count"],
                "authority": "artifact_hash_refs_must_be_declared_before_replication_success",
            },
            {
                "mechanic_id": "artifact_hash_metric_script_replay",
                "count": result["artifact_replay_count"],
                "authority": "success_requires_artifacts_metrics_and_cold_rerun",
            },
            {
                "mechanic_id": "budget_failure_taxonomy_receipt",
                "count": result["failure_taxonomy_count"],
                "authority": "compute_budget_and_failure_taxonomy_are_receipts_not_notes",
            },
        ],
        "body_import_status": result["body_import_status"],
        "body_import_verification": result["body_import_verification"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "body_material_status": result["body_material_status"],
        "source_module_import_status": result["source_module_import_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_module_import_count": result["source_module_import_count"],
        "copied_source_artifact_count": result["copied_source_artifact_count"],
        "source_open_body_imports": result["source_open_body_imports"],
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
        "schema_version": "research_replication_rubric_artifact_replay_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "research_replication_rubric_artifact_replay_validation_receipt_v1",
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
        "paper_count": result["paper_count"],
        "replay_count": result["replay_count"],
        "artifact_replay_count": result["artifact_replay_count"],
        "cold_rerun_count": result["cold_rerun_count"],
        "declared_artifact_hash_ref_count": result["declared_artifact_hash_ref_count"],
        "declared_artifact_hash_refs": result["declared_artifact_hash_refs"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "source_open_body_imports": result["source_open_body_imports"],
        "source_module_import_status": result["source_module_import_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "body_import_verification": result["body_import_verification"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "research_replication_rubric_artifact_replay_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "source_open_body_imports": result["source_open_body_imports"],
        "source_module_import_status": result["source_module_import_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "body_import_verification": result["body_import_verification"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "replication_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.research_replication_rubric_artifact_replay run",
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    result["freshness_basis"] = _freshness_basis(Path(input_dir), include_negative=True)
    result["receipt_reused"] = False
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_replication_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.research_replication_rubric_artifact_replay "
        "run-replication-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    source = Path(input_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if reuse_fresh_receipt:
        cached = _fresh_replication_bundle_receipt(
            source,
            out,
            command=command,
        )
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_research_replication_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_research_replication_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    secret_scan = result.get("secret_exclusion_scan")
    scan = secret_scan if isinstance(secret_scan, dict) else {}
    source_open_body_imports = result.get("source_open_body_imports")
    imports = (
        source_open_body_imports
        if isinstance(source_open_body_imports, dict)
        else {}
    )
    public_trace = result.get("public_agent_execution_trace")
    trace = public_trace if isinstance(public_trace, dict) else {}
    trace_summary = trace.get("summary")
    summary = trace_summary if isinstance(trace_summary, dict) else {}
    trace_audit = trace.get("audit")
    audit = trace_audit if isinstance(trace_audit, dict) else {}
    trace_coverage = audit.get("coverage")
    coverage = trace_coverage if isinstance(trace_coverage, dict) else {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": freshness.get("basis_digest"),
            "freshness_input_count": freshness.get("input_count"),
            "freshness_missing_path_count": freshness.get("missing_path_count"),
        },
        "research_replication": {
            "paper_count": result.get("paper_count"),
            "replay_count": result.get("replay_count"),
            "artifact_replay_count": result.get("artifact_replay_count"),
            "cold_rerun_count": result.get("cold_rerun_count"),
            "ablation_count": result.get("ablation_count"),
            "grader_report_count": result.get("grader_report_count"),
            "failure_taxonomy_count": result.get("failure_taxonomy_count"),
            "declared_artifact_hash_ref_count": result.get(
                "declared_artifact_hash_ref_count"
            ),
        },
        "public_agent_execution_trace": {
            "status": trace.get("status"),
            "span_count": trace.get("span_count"),
            "action_kind_counts": summary.get("action_kind_counts"),
            "outcome_counts": summary.get("outcome_counts"),
            "coverage": coverage,
        },
        "source_body_floor": {
            "status": imports.get("status"),
            "body_material_status": result.get("body_material_status"),
            "body_material_count": imports.get("body_material_count"),
            "body_material_id_count": len(imports.get("body_material_ids") or []),
            "source_module_import_status": result.get("source_module_import_status"),
            "source_module_import_count": result.get("source_module_import_count"),
            "copied_source_artifact_count": result.get(
                "copied_source_artifact_count"
            ),
            "source_modules_pass": result.get("source_modules_pass"),
        },
        "validation": {
            "expected_negative_case_count": len(
                result.get("expected_negative_cases") or []
            ),
            "missing_negative_case_count": len(
                result.get("missing_negative_cases") or []
            ),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
            "secret_exclusion_blocking_hit_count": scan.get("blocking_hit_count"),
        },
        "body_floor": {
            "body_in_receipt": False,
            "secret_exclusion_scan_in_card": False,
            "public_agent_execution_trace_spans_in_card": False,
            "authority_ceiling_in_card": False,
            "anti_claim_in_card": False,
            "source_module_imports_in_card": False,
            "source_open_body_imports_in_card": False,
            "research_replay_rows_in_card": False,
            "declared_artifact_hash_refs_in_card": False,
        },
        "authority_boundary": {
            "replication_success_claim_authorized_without_artifact_replay": False,
            "undeclared_artifact_hash_ref_authorized": False,
            "benchmark_performance_claim_authorized": False,
            "original_author_code_reuse_authorized": False,
            "hidden_rubric_export_authorized": False,
            "private_paper_or_data_body_export_authorized": False,
            "unbounded_compute_search_authorized": False,
            "final_answer_only_grading_authorized": False,
            "provider_calls_authorized": False,
            "publication_authorized": False,
        },
        "receipt_paths": result.get("receipt_paths", []),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": "rerun without --card or inspect the written receipt file",
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research_replication_rubric_artifact_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-replication-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        acceptance_suffix = (
            f" --acceptance-out {args.acceptance_out}" if args.acceptance_out else ""
        )
        command = (
            "python -m microcosm_core.organs."
            "research_replication_rubric_artifact_replay "
            f"run --input {args.input} --out {args.out}{acceptance_suffix}"
            f"{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-replication-bundle":
        command = (
            "python -m microcosm_core.organs."
            "research_replication_rubric_artifact_replay "
            f"run-replication-bundle --input {args.input} --out {args.out}"
            f"{card_suffix}"
        )
        result = run_replication_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    else:  # pragma: no cover
        raise ValueError(args.action)
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
