from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
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


ORGAN_ID = "ring2_premise_retrieval_precision_recall_harness"
FIXTURE_ID = "first_wave.ring2_premise_retrieval_precision_recall_harness"
VALIDATOR_ID = "validator.microcosm.organs.ring2_premise_retrieval_precision_recall_harness"

RESULT_NAME = "ring2_precision_recall_result.json"
BOARD_NAME = "ring2_precision_recall_board.json"
VALIDATION_RECEIPT_NAME = "ring2_precision_recall_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "ring2_premise_retrieval_precision_recall_harness_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_ring2_precision_recall_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "ring2_precision_recall_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "expected_negative_cases",
    "observed_negative_cases",
    "missing_negative_cases",
    "error_codes",
    "findings",
    "secret_exclusion_scan",
    "authority_ceiling",
    "anti_claim",
    "source_pattern_ids",
    "source_refs",
    "source_digests",
    "body_material_contract",
    "copied_material",
    "source_artifact_imports",
    "source_open_body_imports",
    "evaluations",
    "ring2_precision_recall_board",
)

SOURCE_PATTERN_IDS = ["ring2_premise_retrieval_precision_recall_harness"]
RUN_ID = "PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0"
RUN_VARIANT_ID = "premise_retrieval_graph_v0"
RUN_SUMMARY_SOURCE_REF = (
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "premise_retrieval_graph_v0/run_summary.json"
)
AGGREGATE_REPORT_SOURCE_REF = (
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "aggregate_report.json"
)
GRAPH_COMPARISON_SOURCE_REF = (
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "graph_variant_comparison.json"
)
PROBLEM_SOURCE_MANIFEST_REF = (
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
    "problem_source_manifest.json"
)
SOURCE_REFS = [
    AGGREGATE_REPORT_SOURCE_REF,
    RUN_SUMMARY_SOURCE_REF,
    GRAPH_COMPARISON_SOURCE_REF,
    PROBLEM_SOURCE_MANIFEST_REF,
]
SOURCE_DIGESTS = {
    AGGREGATE_REPORT_SOURCE_REF: (
        "sha256:0a5024ce5f24e0e04f4e98fb561c8bcb38ce700a5ab7e1a284f05756607334d0"
    ),
    RUN_SUMMARY_SOURCE_REF: (
        "sha256:93304410f32d40f5cad1c161c1d01a5d6f353ee10b7cf3fecbaaf7b068b43008"
    ),
    GRAPH_COMPARISON_SOURCE_REF: (
        "sha256:8bab9c7a0a2a62f2178a550ab2fadf06887ff03cc9bf83f057688597b9e0556f"
    ),
    PROBLEM_SOURCE_MANIFEST_REF: (
        "sha256:d78e433e36788a3e25e0d80f76e959557b5ea8c1b2e180b080cb59a20cdd8a1b"
    ),
}
PUBLIC_SAFE_SOURCE_DIGESTS = {
    RUN_SUMMARY_SOURCE_REF: (
        "sha256:be17ba7aacb24d1a554873c84c2559c8f4b326ba4ff49a7cc73f8753efb3c016"
    ),
    GRAPH_COMPARISON_SOURCE_REF: (
        "sha256:38a1ce15461bca6b6811934ac8fcf4e0e82280bd7435a4f241280c5cadcbd074"
    ),
    PROBLEM_SOURCE_MANIFEST_REF: (
        "sha256:9658b0c79ed8f2ea3bdcf9798147ed6408b5cb40a660272cb2bc3dc40479ba33"
    ),
}
SOURCE_MATERIAL_IDS = {
    AGGREGATE_REPORT_SOURCE_REF: "ring2_precision_recall_aggregate_report_body_import",
    RUN_SUMMARY_SOURCE_REF: "ring2_precision_recall_run_summary_body_import",
    GRAPH_COMPARISON_SOURCE_REF: (
        "ring2_precision_recall_graph_variant_comparison_body_import"
    ),
    PROBLEM_SOURCE_MANIFEST_REF: (
        "ring2_precision_recall_problem_source_manifest_body_import"
    ),
}
BODY_MATERIAL_STATUS = "copied_non_secret_macro_body_with_provenance"
SOURCE_ARTIFACT_STATUS = "copied_ring2_source_artifacts_verified"
SOURCE_OPEN_BODY_MATERIAL_STATUS = (
    "digest_verified_public_safe_ring2_precision_recall_source_artifacts_with_provenance"
)
SOURCE_OPEN_BODY_AGGREGATE_REF = (
    "examples/ring2_premise_retrieval_precision_recall_harness/"
    "exported_ring2_precision_recall_bundle/"
    "bundle_manifest.json::source_open_body_imports"
)
BODY_MATERIAL_CONTRACT = {
    "body_material_status": BODY_MATERIAL_STATUS,
    "macro_run_id": RUN_ID,
    "macro_run_variant_id": RUN_VARIANT_ID,
    "copied_macro_run_rows": True,
    "after_the_fact_metric_labels_only": True,
    "proof_bodies_excluded": True,
    "provider_payloads_excluded": True,
    "oracle_labels_excluded_from_rankings": True,
    "provider_calls_authorized": False,
    "lean_lake_execution_authorized": False,
}

INPUT_NAMES = (
    "retrieval_runs.json",
    "problem_labels.json",
    "retrieval_rankings.json",
    "evaluation_policy.json",
)
NEGATIVE_INPUT_NAMES = (
    "oracle_labels_in_ranking.json",
    "proof_body_leakage.json",
    "test_split_tuning_attempt.json",
    "metric_overclaim.json",
    "missing_adversarial_decoy.json",
)
NEGATIVE_INPUT_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)

EXPECTED_NEGATIVE_CASES = {
    "oracle_labels_in_ranking": ["RING2_RETRIEVAL_ORACLE_LABELS_IN_RANKING"],
    "proof_body_leakage": ["RING2_RETRIEVAL_PROOF_BODY_FORBIDDEN"],
    "test_split_tuning_attempt": ["RING2_RETRIEVAL_TEST_SPLIT_TUNING_FORBIDDEN"],
    "metric_overclaim": ["RING2_RETRIEVAL_METRIC_OVERCLAIM"],
    "missing_adversarial_decoy": ["RING2_RETRIEVAL_ADVERSARIAL_DECOY_REQUIRED"],
}

FORBIDDEN_BODY_KEYS = (
    "ground_truth_proof",
    "ideal_body",
    "oracle_needed_premise_ids",
    "private_source_body",
    "proof_body",
    "provider_output_body",
    "raw_provider_response",
)

OVERCLAIM_KEYS = (
    "benchmark_performance_claimed",
    "general_theorem_proving_success_claimed",
    "lean_proof_authority_claimed",
    "provider_output_authorized",
    "release_authorized",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "ring2_retrieval_metrics_metadata_not_proof_or_benchmark_authority",
    "after_the_fact_labels_allowed_for_metrics": True,
    "labels_allowed_in_provider_context": False,
    "proof_bodies_allowed": False,
    "test_split_tuning_authorized": False,
    "provider_calls_authorized": False,
    "lean_lake_execution_authorized": False,
    "formal_proof_authority": False,
    "benchmark_performance_authority": False,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Ring-2 premise retrieval precision/recall evaluates copied non-secret "
    "macro run rankings against after-the-fact metric labels. It separates "
    "retrieval misses from proof failures despite premise hits, but it does "
    "not run Lean or Lake, call providers, expose proof bodies, tune on test "
    "answers, claim benchmark performance, prove theorem correctness, or "
    "authorize release."
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
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _source_artifact_rel_path(source_ref: str) -> Path:
    return Path("source_artifacts") / source_ref


def _source_artifact_paths(input_dir: Path) -> list[Path]:
    return [
        input_dir / _source_artifact_rel_path(source_ref)
        for source_ref in SOURCE_REFS
    ]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names] + _source_artifact_paths(input_dir)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _freshness_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    source = Path(input_dir)
    public_root = _public_root_for_path(source)
    paths = [*_input_paths(source, include_negative=include_negative)]
    bundle_manifest = source / "bundle_manifest.json"
    if bundle_manifest.is_file():
        paths.append(bundle_manifest)
    paths.append(public_root / "core/private_state_forbidden_classes.json")
    return paths


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
        "ring2_precision_recall_result_v1"
        if include_negative
        else "exported_ring2_precision_recall_bundle_validation_result_v1"
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
        "schema_version": "ring2_precision_recall_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_precision_recall_bundle_receipt(
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
        "exported_ring2_precision_recall_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("status") != PASS:
        return None
    if payload.get("input_mode") != "exported_ring2_precision_recall_bundle":
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


def _line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


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


def _forbidden_keys(row: dict[str, Any]) -> list[str]:
    return sorted(key for key in FORBIDDEN_BODY_KEYS if key in row)


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


def _inspect_forbidden_bodies(
    payload: object,
    *,
    case_id: str,
    observed: dict[str, set[str]],
    findings: list[dict[str, Any]],
    subject_kind: str,
) -> None:
    for row in _walk_dicts(payload):
        forbidden = _forbidden_keys(row)
        if not forbidden:
            continue
        code = (
            "RING2_RETRIEVAL_ORACLE_LABELS_IN_RANKING"
            if "oracle_needed_premise_ids" in forbidden
            else "RING2_RETRIEVAL_PROOF_BODY_FORBIDDEN"
        )
        _record(
            findings,
            observed,
            code,
            "Ring-2 public retrieval fixtures may carry after-the-fact metric labels and rankings, not proof bodies or oracle labels inside rankings.",
            case_id=case_id,
            subject_id=str(row.get("problem_id") or row.get("ranking_id") or "payload"),
            subject_kind=subject_kind,
        )


def _negative_findings(payloads: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for stem in NEGATIVE_INPUT_STEMS:
        payload = payloads.get(stem)
        if not isinstance(payload, dict):
            continue
        case_id = str(payload.get("expected_negative_case_id") or stem)
        if stem == "oracle_labels_in_ranking":
            _inspect_forbidden_bodies(
                payload,
                case_id=case_id,
                observed=observed,
                findings=findings,
                subject_kind="retrieval_ranking",
            )
        elif stem == "proof_body_leakage":
            _inspect_forbidden_bodies(
                payload,
                case_id=case_id,
                observed=observed,
                findings=findings,
                subject_kind="proof_body_leakage",
            )
        elif stem == "test_split_tuning_attempt":
            for row in _walk_dicts(payload):
                if row.get("uses_test_labels_for_tuning") is True:
                    _record(
                        findings,
                        observed,
                        "RING2_RETRIEVAL_TEST_SPLIT_TUNING_FORBIDDEN",
                        "Ring-2 labels may be used for after-the-fact metrics, not retrieval tuning.",
                        case_id=case_id,
                        subject_id=str(row.get("run_id") or row.get("problem_id") or "tuning"),
                        subject_kind="test_split_tuning",
                    )
        elif stem == "metric_overclaim":
            for row in _walk_dicts(payload):
                overclaims = sorted(key for key in OVERCLAIM_KEYS if row.get(key) is True)
                if overclaims:
                    _record(
                        findings,
                        observed,
                        "RING2_RETRIEVAL_METRIC_OVERCLAIM",
                        "Ring-2 metrics cannot claim proof authority, benchmark performance, provider authority, or release readiness.",
                        case_id=case_id,
                        subject_id=",".join(overclaims),
                        subject_kind="metric_claim",
                    )
        elif stem == "missing_adversarial_decoy":
            policy = payload.get("evaluation_policy", payload)
            if isinstance(policy, dict) and not policy.get("adversarial_decoy_case_id"):
                _record(
                    findings,
                    observed,
                    "RING2_RETRIEVAL_ADVERSARIAL_DECOY_REQUIRED",
                    "Ring-2 retrieval quality fixtures must include an adversarial decoy/miss case.",
                    case_id=case_id,
                    subject_id=str(policy.get("policy_id") or "evaluation_policy"),
                    subject_kind="evaluation_policy",
                )
    return {
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(value) for key, value in observed.items()
        },
    }


def _labels_by_problem(payload: object) -> dict[str, dict[str, Any]]:
    labels: dict[str, dict[str, Any]] = {}
    for row in _rows(payload, "problems"):
        problem_id = str(row.get("problem_id") or "")
        if problem_id:
            labels[problem_id] = row
    return labels


def _policy(payload: object) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def _rankings(payload: object) -> list[dict[str, Any]]:
    return _rows(payload, "rankings")


def _copied_material(payloads: dict[str, Any]) -> list[dict[str, Any]]:
    runs_payload = payloads.get("retrieval_runs")
    copied: list[dict[str, Any]] = []
    if isinstance(runs_payload, dict):
        copied.extend(_rows(runs_payload, "copied_material"))
        for run_row in _rows(runs_payload, "runs"):
            copied.extend(_rows(run_row, "copied_material"))
    return copied


def _source_refs_from_payload(payloads: dict[str, Any]) -> list[str]:
    runs_payload = payloads.get("retrieval_runs")
    refs: set[str] = set(SOURCE_REFS)
    if isinstance(runs_payload, dict):
        refs.update(_strings(runs_payload.get("source_refs")))
        for row in _rows(runs_payload, "runs"):
            refs.update(_strings(row.get("source_refs")))
            for material in _rows(row, "copied_material"):
                source_ref = material.get("source_ref")
                if isinstance(source_ref, str) and source_ref:
                    refs.add(source_ref)
        for material in _rows(runs_payload, "copied_material"):
            source_ref = material.get("source_ref")
            if isinstance(source_ref, str) and source_ref:
                refs.add(source_ref)
    return sorted(refs)


def _validate_run_material(payloads: dict[str, Any]) -> dict[str, Any]:
    copied = _copied_material(payloads)
    findings: list[dict[str, Any]] = []
    if not copied:
        findings.append(
            _finding(
                "RING2_RETRIEVAL_COPIED_MATERIAL_REQUIRED",
                "Ring-2 precision/recall fixtures must cite copied non-secret macro run material with source and target provenance.",
                case_id="input_floor",
                subject_id="retrieval_runs",
                subject_kind="copied_material",
            )
        )
    for material in copied:
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
                    "RING2_RETRIEVAL_COPIED_MATERIAL_PROVENANCE_INCOMPLETE",
                    "Copied Ring-2 run material must retain source digest, target refs, validation refs, and copied-material status.",
                    case_id="input_floor",
                    subject_id=str(material.get("material_id") or "copied_material"),
                    subject_kind="copied_material",
                )
            )
    return {
        "copied_material": copied,
        "body_copied_material_count": len(copied),
        "source_refs": _source_refs_from_payload(payloads),
        "findings": findings,
    }


def _validate_source_artifacts(input_dir: Path, *, public_root: Path) -> dict[str, Any]:
    imports: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for source_ref in SOURCE_REFS:
        target = input_dir / _source_artifact_rel_path(source_ref)
        expected_digest = SOURCE_DIGESTS[source_ref]
        public_safe_digest = PUBLIC_SAFE_SOURCE_DIGESTS.get(source_ref)
        exists = target.is_file()
        actual_digest = _sha256(target) if exists else None
        source_digest_match = actual_digest == expected_digest
        public_safe_digest_match = (
            public_safe_digest is not None and actual_digest == public_safe_digest
        )
        digest_match = source_digest_match or public_safe_digest_match
        relation = (
            "exact_copy"
            if source_digest_match
            else "verified_public_safe_private_path_rewrite"
            if public_safe_digest_match
            else "digest_mismatch"
        )
        row = {
            "source_ref": source_ref,
            "target_ref": _display(target, public_root=public_root),
            "source_sha256": expected_digest,
            "public_safe_sha256": public_safe_digest,
            "target_sha256": actual_digest,
            "source_to_target_relation": relation,
            "verification_mode": (
                "exact_source_digest_match"
                if source_digest_match
                else "verified_light_edit_recipe"
                if public_safe_digest_match
                else "unverified"
            ),
            "public_safe_transform": (
                "private_absolute_path_rewrite_only"
                if public_safe_digest_match and not source_digest_match
                else None
            ),
            "exists": exists,
            "digest_match": digest_match,
            "source_digest_matches": source_digest_match,
            "public_safe_digest_matches": public_safe_digest_match,
            "source_line_count": _line_count(target) if exists else None,
            "target_line_count": _line_count(target) if exists else None,
            "body_material_status": SOURCE_ARTIFACT_STATUS,
        }
        imports.append(row)
        if not exists:
            findings.append(
                _finding(
                    "RING2_RETRIEVAL_SOURCE_ARTIFACT_MISSING",
                    "Copied Ring-2 source artifact must be physically present under "
                    "source_artifacts, not only named as a source ref.",
                    case_id="source_artifact_floor",
                    subject_id=source_ref,
                    subject_kind="source_artifact",
                )
            )
        elif not digest_match:
            findings.append(
                _finding(
                    "RING2_RETRIEVAL_SOURCE_ARTIFACT_DIGEST_MISMATCH",
                    (
                        "Copied Ring-2 source artifact digest must match either "
                        "the macro source digest or a verified public-safe rewrite digest."
                    ),
                    case_id="source_artifact_floor",
                    subject_id=source_ref,
                    subject_kind="source_artifact",
                )
            )
    return {
        "source_artifact_status": SOURCE_ARTIFACT_STATUS,
        "source_artifact_imports": imports,
        "source_artifact_count": len(SOURCE_REFS),
        "copied_source_artifact_count": sum(
            1 for row in imports if row["exists"] and row["digest_match"]
        ),
        "source_artifacts_pass": not findings,
        "findings": findings,
    }


def _source_open_body_import_summary(
    source_artifact_imports: list[dict[str, Any]],
) -> dict[str, Any]:
    verified_rows = [
        row for row in source_artifact_imports if row["exists"] and row["digest_match"]
    ]
    verified_ids = [SOURCE_MATERIAL_IDS[row["source_ref"]] for row in verified_rows]
    status = PASS if len(verified_ids) == len(SOURCE_REFS) else "blocked"
    return {
        "status": status,
        "body_material_status": SOURCE_OPEN_BODY_MATERIAL_STATUS,
        "body_material_count": len(verified_ids),
        "body_material_ids": verified_ids,
        "material_classes": ["public_macro_receipt_body"],
        "aggregate_floor_ref": SOURCE_OPEN_BODY_AGGREGATE_REF,
        "source_manifest_refs": [
            (
                "core/fixture_manifests/"
                "ring2_premise_retrieval_precision_recall_harness.fixture_manifest.json"
            ),
            (
                "examples/ring2_premise_retrieval_precision_recall_harness/"
                "exported_ring2_precision_recall_bundle/bundle_manifest.json"
            ),
        ],
        "source_refs": [row["source_ref"] for row in verified_rows],
        "target_refs": [row["target_ref"] for row in verified_rows],
        "body_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "reader_action": (
            "Open source_artifacts/ under the fixture or exported bundle to inspect "
            "copied Ring2 precision-recall macro receipts; validator receipts carry "
            "body import ids, target refs, and digest status only."
        ),
        "authority_ceiling": {
            "body_text_in_receipt": False,
            "proof_body_or_oracle_proof_text_exported": False,
            "provider_payload_exported": False,
            "lean_lake_execution_authorized": False,
            "formal_proof_authority": False,
            "benchmark_performance_authority": False,
            "release_authorized": False,
            "source_authority_above_macro_contracts": False,
        },
    }


def _evaluate(
    *,
    labels_payload: object,
    rankings_payload: object,
    policy_payload: object,
) -> dict[str, Any]:
    labels = _labels_by_problem(labels_payload)
    policy = _policy(policy_payload)
    rows: list[dict[str, Any]] = []
    precision_scores: list[float] = []
    recall_scores: list[float] = []
    total_hit_count = 0
    total_retrieval_candidate_count = 0
    total_needed_premise_count = 0
    failure_modes: Counter[str] = Counter()
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)

    default_top_k = int(policy.get("default_top_k") or 4)
    for ranking in _rankings(rankings_payload):
        problem_id = str(ranking.get("problem_id") or "")
        label = labels.get(problem_id, {})
        declared_top_k = int(ranking.get("top_k") or default_top_k)
        retrieved = _strings(ranking.get("retrieved_premise_ids"))[:declared_top_k]
        needed = _strings(label.get("needed_premise_ids"))
        hits = sorted(set(retrieved) & set(needed))
        precision = len(hits) / declared_top_k if declared_top_k else 0.0
        recall = len(hits) / len(needed) if needed else 0.0
        precision_scores.append(precision)
        recall_scores.append(recall)
        total_hit_count += len(hits)
        total_retrieval_candidate_count += declared_top_k
        total_needed_premise_count += len(needed)
        proof_outcome = str(ranking.get("proof_outcome") or "not_run")
        if recall >= 1.0 and proof_outcome == "pass":
            failure_mode = "retrieval_hit"
        elif recall >= 1.0:
            failure_mode = "proof_failure_despite_hit"
        elif hits:
            failure_mode = "partial_retrieval_miss"
        else:
            failure_mode = "retrieval_miss"
        failure_modes[failure_mode] += 1
        rows.append(
            {
                "problem_id": problem_id,
                "split": label.get("split"),
                "ring": label.get("ring"),
                "target_shape": label.get("target_shape"),
                "top_k": declared_top_k,
                "retrieved_premise_count": len(retrieved),
                "needed_premise_count": len(needed),
                "hit_count": len(hits),
                "precision_at_k": round(precision, 4),
                "recall_at_k": round(recall, 4),
                "failure_mode": failure_mode,
                "adversarial_decoy_expected": label.get("adversarial_decoy_expected") is True,
                "needed_premise_ids_material_status": "after_the_fact_metric_label_only",
                "retrieved_premise_ids": retrieved,
                "hit_premise_ids": hits,
                "body_material_status": "real_run_metric_row",
            }
        )

    required_modes = set(_strings(policy.get("expected_failure_modes")))
    missing_modes = sorted(required_modes - set(failure_modes))
    for missing in missing_modes:
        findings.append(
            _finding(
                "RING2_RETRIEVAL_EXPECTED_FAILURE_MODE_MISSING",
                "Ring-2 evaluation did not observe an expected retrieval/proof attribution mode.",
                case_id="policy_floor",
                subject_id=missing,
                subject_kind="failure_mode",
            )
        )

    adversarial_id = str(policy.get("adversarial_decoy_case_id") or "")
    adversarial_row = next((row for row in rows if row["problem_id"] == adversarial_id), None)
    adversarial_ok = bool(
        adversarial_row
        and adversarial_row["adversarial_decoy_expected"]
        and adversarial_row["recall_at_k"] < 1.0
    )
    if not adversarial_ok:
        findings.append(
            _finding(
                "RING2_RETRIEVAL_ADVERSARIAL_DECOY_REQUIRED",
                "Ring-2 evaluation must include a decoy case whose needed premise is absent or missed.",
                case_id="policy_floor",
                subject_id=adversarial_id or "missing",
                subject_kind="evaluation_policy",
            )
        )

    minimum = int(policy.get("minimum_problem_count") or 1)
    if len(rows) < minimum:
        findings.append(
            _finding(
                "RING2_RETRIEVAL_PROBLEM_COUNT_TOO_LOW",
                "Ring-2 evaluation must include the minimum public problem count.",
                case_id="policy_floor",
                subject_id=str(len(rows)),
                subject_kind="evaluation_policy",
            )
        )

    return {
        "status": PASS if rows and not findings else "blocked",
        "problem_count": len(rows),
        "mean_precision_at_k": round(total_hit_count / total_retrieval_candidate_count, 4)
        if total_retrieval_candidate_count
        else 0.0,
        "mean_recall_at_k": round(total_hit_count / total_needed_premise_count, 4)
        if total_needed_premise_count
        else 0.0,
        "metric_aggregation": {
            "precision": "total_hit_count_over_total_retrieval_candidate_count",
            "recall": "total_hit_count_over_total_needed_premise_count",
            "legacy_row_mean_precision_at_k": round(sum(precision_scores) / len(precision_scores), 4)
            if precision_scores
            else 0.0,
            "legacy_row_mean_recall_at_k": round(sum(recall_scores) / len(recall_scores), 4)
            if recall_scores
            else 0.0,
            "total_hit_count": total_hit_count,
            "total_retrieval_candidate_count": total_retrieval_candidate_count,
            "total_needed_premise_count": total_needed_premise_count,
        },
        "failure_mode_counts": dict(sorted(failure_modes.items())),
        "missing_expected_failure_modes": missing_modes,
        "adversarial_decoy_case_id": adversarial_id,
        "adversarial_decoy_observed": adversarial_ok,
        "evaluations": sorted(rows, key=lambda row: str(row["problem_id"])),
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(value) for key, value in observed.items()
        },
    }


def _build_board(*, result: dict[str, Any], secret_scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "ring2_precision_recall_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "selected_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "public_contract": {
            "after_the_fact_metric_labels_only": True,
            "provider_context_label_leakage_forbidden": True,
            "precision_and_recall_metered": True,
            "retrieval_vs_proof_failure_attribution": True,
            "adversarial_decoy_required": True,
            "proof_bodies_forbidden": True,
            "copied_material_provenance_required": True,
            "source_artifact_digest_or_verified_public_safe_digest_required": True,
            "source_open_body_imports_required": True,
            "body_material_status": BODY_MATERIAL_STATUS,
            "source_artifact_status": SOURCE_ARTIFACT_STATUS,
        },
        "body_material_contract": BODY_MATERIAL_CONTRACT,
        "copied_material": result["copied_material"],
        "body_copied_material_count": result["body_copied_material_count"],
        "source_artifact_imports": result["source_artifact_imports"],
        "copied_source_artifact_count": result["copied_source_artifact_count"],
        "source_artifacts_pass": result["source_artifacts_pass"],
        "source_open_body_imports": result["source_open_body_imports"],
        "metrics": {
            "problem_count": result["problem_count"],
            "mean_precision_at_k": result["mean_precision_at_k"],
            "mean_recall_at_k": result["mean_recall_at_k"],
            "metric_aggregation": result["metric_aggregation"],
            "failure_mode_counts": result["failure_mode_counts"],
            "adversarial_decoy_case_id": result["adversarial_decoy_case_id"],
            "adversarial_decoy_observed": result["adversarial_decoy_observed"],
        },
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_material_status": BODY_MATERIAL_STATUS,
        "source_artifact_status": SOURCE_ARTIFACT_STATUS,
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
        "source_digests",
        "macro_run_id",
        "macro_run_variant_id",
        "body_material_status",
        "body_material_contract",
        "copied_material",
        "body_copied_material_count",
        "source_artifact_status",
        "source_artifact_imports",
        "source_artifact_count",
        "copied_source_artifact_count",
        "source_artifacts_pass",
        "source_open_body_imports",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "authority_ceiling",
        "anti_claim",
        "problem_count",
        "mean_precision_at_k",
        "mean_recall_at_k",
        "metric_aggregation",
        "failure_mode_counts",
        "adversarial_decoy_case_id",
        "adversarial_decoy_observed",
        "evaluations",
        "freshness_basis",
        "receipt_reused",
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
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    secret_scan.pop("forbidden_output_fields", None)
    secret_scan.pop("body_redacted", None)
    secret_scan["forbidden_output_field_labels_omitted"] = True
    secret_scan["body_material_status"] = "secret_exclusion_scan_no_payload_bodies"

    floor_findings: list[dict[str, Any]] = []
    floor_observed: dict[str, set[str]] = defaultdict(set)
    for stem in INPUT_NAMES:
        _inspect_forbidden_bodies(
            payloads[Path(stem).stem],
            case_id="input_floor",
            observed=floor_observed,
            findings=floor_findings,
            subject_kind=Path(stem).stem,
        )

    evaluation = _evaluate(
        labels_payload=payloads["problem_labels"],
        rankings_payload=payloads["retrieval_rankings"],
        policy_payload=payloads["evaluation_policy"],
    )
    run_material = _validate_run_material(payloads)
    source_artifacts = _validate_source_artifacts(input_dir, public_root=public_root)
    source_open_body_imports = _source_open_body_import_summary(
        source_artifacts["source_artifact_imports"]
    )
    negative = (
        _negative_findings(payloads)
        if include_negative
        else {"findings": [], "observed_negative_cases": {}}
    )
    observed = negative["observed_negative_cases"]
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = [
        *floor_findings,
        *run_material["findings"],
        *source_artifacts["findings"],
        *evaluation["findings"],
        *negative["findings"],
    ]
    error_codes = sorted({str(finding["error_code"]) for finding in findings})
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    status = (
        PASS
        if not missing
        and not floor_findings
        and not run_material["findings"]
        and source_artifacts["source_artifacts_pass"]
        and evaluation["status"] == PASS
        and not secret_scan["blocking_hit_count"]
        else "blocked"
    )
    result = {
        "schema_version": "ring2_precision_recall_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "source_refs": run_material["source_refs"],
        "source_digests": SOURCE_DIGESTS,
        "macro_run_id": RUN_ID,
        "macro_run_variant_id": RUN_VARIANT_ID,
        "body_material_status": BODY_MATERIAL_STATUS,
        "body_material_contract": BODY_MATERIAL_CONTRACT,
        "copied_material": run_material["copied_material"],
        "body_copied_material_count": run_material["body_copied_material_count"],
        "source_artifact_status": source_artifacts["source_artifact_status"],
        "source_artifact_imports": source_artifacts["source_artifact_imports"],
        "source_artifact_count": source_artifacts["source_artifact_count"],
        "copied_source_artifact_count": source_artifacts[
            "copied_source_artifact_count"
        ],
        "source_artifacts_pass": source_artifacts["source_artifacts_pass"],
        "source_open_body_imports": source_open_body_imports,
        "expected_negative_cases": expected,
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "problem_count": evaluation["problem_count"],
        "mean_precision_at_k": evaluation["mean_precision_at_k"],
        "mean_recall_at_k": evaluation["mean_recall_at_k"],
        "metric_aggregation": evaluation["metric_aggregation"],
        "failure_mode_counts": evaluation["failure_mode_counts"],
        "adversarial_decoy_case_id": evaluation["adversarial_decoy_case_id"],
        "adversarial_decoy_observed": evaluation["adversarial_decoy_observed"],
        "evaluations": evaluation["evaluations"],
    }
    result["ring2_precision_recall_board"] = _build_board(
        result=result,
        secret_scan=secret_scan,
    )
    return result


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
    bundle_mode: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if bundle_mode:
        bundle_path = out_dir / BUNDLE_RESULT_NAME
        receipt = _common_receipt(
            result,
            schema_version="exported_ring2_precision_recall_bundle_validation_result_v1",
            receipt_paths=[_display(bundle_path, public_root=public_root)],
        )
        write_json_atomic(bundle_path, receipt)
        result["receipt_paths"] = receipt["receipt_paths"]
        return result

    paths = {
        "result": out_dir / RESULT_NAME,
        "board": out_dir / BOARD_NAME,
        "validation": out_dir / VALIDATION_RECEIPT_NAME,
    }
    acceptance_path = (
        acceptance_out
        if acceptance_out is not None
        else public_root / ACCEPTANCE_RECEIPT_REL
    )
    receipt_paths = _relative_receipt_paths(paths, public_root)
    result_payload = dict(result)
    result_payload.pop("ring2_precision_recall_board", None)
    result_payload["receipt_paths"] = receipt_paths
    board_payload = result["ring2_precision_recall_board"]
    board_payload["receipt_paths"] = receipt_paths
    validation_payload = _common_receipt(
        result,
        schema_version="ring2_precision_recall_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    acceptance_payload = _common_receipt(
        result,
        schema_version="ring2_precision_recall_fixture_acceptance_v1",
        receipt_paths=[_display(acceptance_path, public_root=public_root)],
    )
    write_json_atomic(paths["result"], result_payload)
    write_json_atomic(paths["board"], board_payload)
    write_json_atomic(paths["validation"], validation_payload)
    acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(acceptance_path, acceptance_payload)
    result["receipt_paths"] = [*receipt_paths, _display(acceptance_path, public_root=public_root)]
    return result


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str = "run",
) -> dict[str, Any]:
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture_input",
        include_negative=True,
    )
    result["freshness_basis"] = _freshness_basis(Path(input_dir), include_negative=True)
    result["receipt_reused"] = False
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
        bundle_mode=False,
    )


def run_precision_recall_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "run-precision-recall-bundle",
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    source = Path(input_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if reuse_fresh_receipt:
        cached = _fresh_precision_recall_bundle_receipt(
            source,
            out,
            command=command,
        )
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_ring2_precision_recall_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    return _write_receipts(
        result,
        out,
        acceptance_out=None,
        bundle_mode=True,
    )


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    secret_scan = result.get("secret_exclusion_scan")
    scan = secret_scan if isinstance(secret_scan, dict) else {}
    source_imports = result.get("source_open_body_imports")
    imports = source_imports if isinstance(source_imports, dict) else {}
    metric_aggregation = result.get("metric_aggregation")
    metrics = metric_aggregation if isinstance(metric_aggregation, dict) else {}
    failure_modes = result.get("failure_mode_counts")
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
        "ring2_precision_recall": {
            "problem_count": result.get("problem_count"),
            "mean_precision_at_k": result.get("mean_precision_at_k"),
            "mean_recall_at_k": result.get("mean_recall_at_k"),
            "total_hit_count": metrics.get("total_hit_count"),
            "total_retrieval_candidate_count": metrics.get(
                "total_retrieval_candidate_count"
            ),
            "total_needed_premise_count": metrics.get("total_needed_premise_count"),
            "failure_mode_counts": (
                failure_modes if isinstance(failure_modes, dict) else {}
            ),
            "adversarial_decoy_observed": result.get("adversarial_decoy_observed"),
        },
        "source_body_floor": {
            "status": imports.get("status"),
            "body_material_count": imports.get("body_material_count"),
            "body_material_id_count": len(imports.get("body_material_ids") or []),
            "source_artifacts_pass": result.get("source_artifacts_pass"),
            "source_artifact_count": result.get("source_artifact_count"),
            "copied_source_artifact_count": result.get(
                "copied_source_artifact_count"
            ),
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
            "authority_ceiling_in_card": False,
            "anti_claim_in_card": False,
            "source_refs_in_card": False,
            "source_digests_in_card": False,
            "body_material_contract_in_card": False,
            "copied_material_in_card": False,
            "source_artifact_imports_in_card": False,
            "source_open_body_imports_in_card": False,
            "evaluation_rows_in_card": False,
            "ring2_precision_recall_board_in_card": False,
        },
        "authority_boundary": {
            "after_the_fact_labels_allowed_for_metrics": True,
            "labels_allowed_in_provider_context": False,
            "proof_bodies_allowed": False,
            "test_split_tuning_authorized": False,
            "provider_calls_authorized": False,
            "lean_lake_execution_authorized": False,
            "formal_proof_authority": False,
            "benchmark_performance_authority": False,
            "release_authorized": False,
        },
        "receipt_paths": result.get("receipt_paths", []),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": "rerun without --card or inspect the written receipt file",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"microcosm organ {ORGAN_ID}")
    parser.add_argument("action", choices=["run", "run-precision-recall-bundle"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--acceptance-out")
    parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        acceptance_suffix = (
            f" --acceptance-out {args.acceptance_out}" if args.acceptance_out else ""
        )
        command = (
            "python -m microcosm_core.organs."
            "ring2_premise_retrieval_precision_recall_harness "
            f"run --input {args.input} --out {args.out}{acceptance_suffix}"
            f"{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            acceptance_out=args.acceptance_out,
            command=command,
        )
    else:
        command = (
            "python -m microcosm_core.organs."
            "ring2_premise_retrieval_precision_recall_harness "
            f"run-precision-recall-bundle --input {args.input} --out {args.out}"
            f"{card_suffix}"
        )
        result = run_precision_recall_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(f"{ORGAN_ID}: {result['status']} -> {args.out}")
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
