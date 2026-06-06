from __future__ import annotations

import argparse
import hashlib
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
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
CARD_SCHEMA_VERSION = "mathematical_strategy_atlas_hypothesis_scorer_command_card_v1"
BODY_MATERIAL_STATUS = (
    "copied_non_secret_macro_strategy_atlas_body_floor_with_provenance"
)
SOURCE_MODULE_IMPORT_STATUS = "copied_strategy_atlas_macro_body_floor_verified"
PUBLIC_SAFE_BODY_CLASSES = {
    "public_macro_pattern_body",
    "public_macro_tool_body",
    "public_macro_standard_body",
    "public_macro_receipt_body",
    "public_macro_proof_body",
}

SOURCE_PATTERN_IDS = [
    "mathematical_strategy_atlas_hypothesis_scorer",
]
HASH_CHUNK_SIZE = 1024 * 1024

SOURCE_REFS = [
    "tools/meta/factory/run_prover_graph_benchmark.py",
    "tools/meta/factory/reduce_prover_provider_receipts.py",
    "system/server/tests/test_prover_graph_benchmark_harness.py",
    "system/server/tests/test_prover_provider_strategy_classification_reducer.py",
    "codex/standards/std_compute_provider.json",
    (
        "state/runs/PROVER_PROVIDER_CONTEXT_SWEEP_20260510_v0/"
        "local_foundry_baseline/problems/strategy_nat_succ_injective/"
        "artifacts/strategy_cards.json"
    ),
    (
        "state/runs/PROVER_PROVIDER_CONTEXT_SWEEP_20260510_v0/"
        "local_foundry_baseline/problems/strategy_nat_succ_injective/"
        "artifacts/strategy_hypothesis_set.json"
    ),
    (
        "state/runs/PROVER_PROVIDER_CONTEXT_SWEEP_20260510_v0/"
        "local_foundry_baseline/problems/strategy_nat_succ_injective/"
        "artifacts/prover_skill_atlas.json"
    ),
]

SOURCE_STRATEGY_CARDS_REF = (
    "state/runs/PROVER_PROVIDER_CONTEXT_SWEEP_20260510_v0/"
    "local_foundry_baseline/problems/strategy_nat_succ_injective/"
    "artifacts/strategy_cards.json"
)
SOURCE_STRATEGY_HYPOTHESIS_SET_REF = (
    "state/runs/PROVER_PROVIDER_CONTEXT_SWEEP_20260510_v0/"
    "local_foundry_baseline/problems/strategy_nat_succ_injective/"
    "artifacts/strategy_hypothesis_set.json"
)
SOURCE_PROVER_SKILL_ATLAS_REF = (
    "state/runs/PROVER_PROVIDER_CONTEXT_SWEEP_20260510_v0/"
    "local_foundry_baseline/problems/strategy_nat_succ_injective/"
    "artifacts/prover_skill_atlas.json"
)
SOURCE_STRATEGY_ARTIFACT_REFS = (
    SOURCE_STRATEGY_CARDS_REF,
    SOURCE_STRATEGY_HYPOTHESIS_SET_REF,
    SOURCE_PROVER_SKILL_ATLAS_REF,
)
SOURCE_ARTIFACT_CONSISTENCY_STATUS = (
    "copied_strategy_artifacts_opened_and_consistency_checked"
)

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
    "copied_public_tool_bodies_allowed": True,
    "provider_payload_bodies_allowed": False,
}

ANTI_CLAIM = (
    "Mathematical strategy atlas projection is a drilldown regression surface "
    "for public pre-oracle strategy hypotheses, retrieval lenses, and copied "
    "non-secret macro tool bodies only. It does not run Lean or Lake, prove "
    "theorem correctness, expose proof bodies, provider payload bodies, or "
    "oracle labels, tune on test answers, call providers, or authorize release."
)

EXPECTED_NEGATIVE_CASES = {
    "unknown_strategy_id": ["MATH_STRATEGY_UNKNOWN_ID"],
    "proof_body_with_strategy": ["MATH_STRATEGY_PROOF_BODY_FORBIDDEN"],
    "oracle_strategy_label_leakage": ["MATH_STRATEGY_ORACLE_LABEL_FORBIDDEN"],
    "post_oracle_strategy_selection": ["MATH_STRATEGY_POST_ORACLE_SELECTION_FORBIDDEN"],
    "release_overclaim": ["MATH_STRATEGY_RELEASE_OVERCLAIM"],
    "superficial_overlap_only_scoring": [
        "MATH_STRATEGY_OVERLAP_ONLY_SCORING_FORBIDDEN"
    ],
    "missing_rich_strategy_card_fields": [
        "MATH_STRATEGY_RICH_CARD_FIELDS_REQUIRED"
    ],
    "retrieval_bonus_ceiling_overclaim": [
        "MATH_STRATEGY_RETRIEVAL_BONUS_CEILING_REQUIRED"
    ],
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
    "superficial_overlap_only_scoring.json",
    "missing_rich_strategy_card_fields.json",
    "retrieval_bonus_ceiling_overclaim.json",
)

NEGATIVE_INPUT_NAMES_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)

TRIGGER_FEATURE_WEIGHT = 4
NEGATIVE_TRIGGER_PENALTY = 3
RETRIEVAL_TERM_BONUS = 1
RETRIEVAL_BONUS_CAP = 2

DECLARED_OUTCOME_FIELDS = (
    "selected_strategy_id",
    "score",
    "classifier",
    "retrieval_bonus",
    "candidate_scores",
)
DECLARED_OUTCOME_ERROR_SPECS = {
    "selected_strategy_id": (
        "MATH_STRATEGY_DECLARED_SELECTION_STALE",
        "Declared selected_strategy_id must match the recomputed evidence-derived strategy.",
        "strategy_id",
    ),
    "score": (
        "MATH_STRATEGY_DECLARED_SCORE_STALE",
        "Declared score must match the recomputed weighted score.",
        "strategy_score",
    ),
    "classifier": (
        "MATH_STRATEGY_DECLARED_VERDICT_STALE",
        "Declared classifier must match the recomputed verdict.",
        "strategy_classifier",
    ),
    "retrieval_bonus": (
        "MATH_STRATEGY_DECLARED_RETRIEVAL_BONUS_STALE",
        "Declared retrieval bonus must match the recomputed bounded retrieval bonus.",
        "retrieval_bonus",
    ),
    "candidate_scores": (
        "MATH_STRATEGY_DECLARED_RANKING_STALE",
        "Declared candidate ranking must match the recomputed candidate score order.",
        "strategy_ranking",
    ),
}
STRATEGY_DERIVATION_STATUS = "recomputed_from_problem_and_strategy_evidence"
SCORING_DERIVATION_INPUT_FIELDS = [
    "problem_features.problems[].feature_tags",
    "problem_features.problems[].retrieval_query_terms",
    "hypothesis_cases.cases[].candidate_strategy_ids",
    "hypothesis_cases.cases[].retrieval_query_terms",
    "strategy_atlas.strategies[].trigger_features",
    "strategy_atlas.strategies[].negative_triggers",
    "strategy_atlas.strategies[].retrieval_expansion_terms",
]
DECLARED_SELECTION_LABEL_ONLY_ERROR_CODE = (
    "MATH_STRATEGY_DECLARED_SELECTION_LABEL_ONLY_FORBIDDEN"
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
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _file_size_bytes(path: Path) -> int:
    return path.stat().st_size


def _normalize_sha256(value: object) -> str:
    digest = str(value or "")
    if digest and not digest.startswith("sha256:"):
        return f"sha256:{digest}"
    return digest


def _line_count(path: Path) -> int:
    line_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_count, _line in enumerate(handle, start=1):
            pass
    return line_count or 1


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _required_anchors(row: dict[str, Any]) -> list[str]:
    anchors = row.get("required_anchors", [])
    if not isinstance(anchors, list):
        return []
    return [str(anchor) for anchor in anchors if isinstance(anchor, str)]


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
                "MATH_STRATEGY_SOURCE_MODULE_MANIFEST_MISSING",
                "Exported strategy atlas bundle must include a source_module_manifest.json for copied macro tool bodies.",
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
                "MATH_STRATEGY_SOURCE_IMPORT_CLASS_UNSUPPORTED",
                "Strategy atlas source module manifest must declare copied_non_secret_macro_body.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if required and manifest_path.is_file() and not rows:
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_MODULE_ROWS_MISSING",
                "Exported strategy atlas bundle must carry at least one copied source module row.",
                case_id="source_module_floor",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )

    for row in rows:
        module_id = str(row.get("module_id") or "source_module")
        target = _source_module_target_path(input_dir, row)
        expected_digest = _normalize_sha256(row.get("sha256"))
        exists = target.is_file()
        actual_digest = _sha256(target) if exists else None
        actual_line_count = _line_count(target) if exists else None
        actual_byte_count = _file_size_bytes(target) if exists else None
        expected_line_count = _int_or_none(row.get("line_count"))
        expected_byte_count = _int_or_none(row.get("byte_count"))
        required_anchors = _required_anchors(row)
        target_text = target.read_text(encoding="utf-8") if exists else ""
        missing_required_anchors = [
            anchor for anchor in required_anchors if anchor not in target_text
        ]
        material_class = str(row.get("material_class") or "")
        source_ref = str(row.get("source_ref") or "")
        target_ref = _display(target, public_root=public_root)
        digest_match = actual_digest == expected_digest
        import_row = {
            "module_id": module_id,
            "source_ref": source_ref,
            "target_ref": target_ref,
            "material_class": material_class,
            "source_sha256": expected_digest,
            "target_sha256": actual_digest,
            "exists": exists,
            "digest_match": digest_match,
            "source_to_target_relation": str(
                row.get("source_to_target_relation") or "exact_copy"
            ),
            "manifest_line_count": expected_line_count,
            "source_line_count": actual_line_count,
            "target_line_count": actual_line_count,
            "manifest_byte_count": expected_byte_count,
            "target_byte_count": actual_byte_count,
            "required_anchor_count": len(required_anchors),
            "missing_required_anchors": missing_required_anchors,
            "body_in_receipt": False,
            "body_material_status": BODY_MATERIAL_STATUS,
            "source_role": str(row.get("source_role") or ""),
        }
        imports.append(import_row)

        if str(row.get("source_import_class") or "") != "copied_non_secret_macro_body":
            findings.append(
                _finding(
                    "MATH_STRATEGY_SOURCE_MODULE_IMPORT_CLASS_UNSUPPORTED",
                    "Source module rows must declare copied_non_secret_macro_body.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_BODY_CLASSES:
            findings.append(
                _finding(
                    "MATH_STRATEGY_SOURCE_MODULE_CLASS_UNSUPPORTED",
                    "Source module rows must use a public-safe macro body material class.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if row.get("body_in_receipt") is True:
            findings.append(
                _finding(
                    "MATH_STRATEGY_SOURCE_BODY_RECEIPT_EXPORT_FORBIDDEN",
                    "Copied source module bodies may live in bundle source_artifacts, not in generated receipts.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if not exists:
            findings.append(
                _finding(
                    "MATH_STRATEGY_SOURCE_MODULE_TARGET_MISSING",
                    "Copied source module target file is missing from the exported bundle.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        elif not digest_match:
            findings.append(
                _finding(
                    "MATH_STRATEGY_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Copied source module digest must match the source_module_manifest row.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if (
            exists
            and expected_line_count is not None
            and actual_line_count != expected_line_count
        ):
            findings.append(
                _finding(
                    "MATH_STRATEGY_SOURCE_MODULE_LINE_COUNT_MISMATCH",
                    "Copied source module line count must match the source_module_manifest row.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if (
            exists
            and expected_byte_count is not None
            and actual_byte_count != expected_byte_count
        ):
            findings.append(
                _finding(
                    "MATH_STRATEGY_SOURCE_MODULE_BYTE_COUNT_MISMATCH",
                    "Copied source module byte count must match the source_module_manifest row.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        if exists and missing_required_anchors:
            findings.append(
                _finding(
                    "MATH_STRATEGY_SOURCE_MODULE_REQUIRED_ANCHOR_MISSING",
                    "Copied source module must contain every required anchor from the manifest row.",
                    case_id="source_module_floor",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )

    copied_count = sum(1 for row in imports if row["exists"] and row["digest_match"])
    return {
        "source_module_manifest_ref": manifest_ref,
        "source_module_import_status": SOURCE_MODULE_IMPORT_STATUS,
        "body_material_status": BODY_MATERIAL_STATUS,
        "source_module_imports": imports,
        "source_module_import_count": len(imports),
        "copied_source_artifact_count": copied_count,
        "source_modules_pass": not findings,
        "source_refs": sorted({row["source_ref"] for row in imports if row["source_ref"]}),
        "target_refs": [row["target_ref"] for row in imports],
        "material_classes": sorted(
            {row["material_class"] for row in imports if row["material_class"]}
        ),
        "findings": findings,
    }


def _artifact_rows_by_source_ref(input_dir: Path) -> dict[str, dict[str, Any]]:
    manifest = _read_source_module_manifest(input_dir)
    return {
        str(row.get("source_ref") or ""): row
        for row in _source_module_rows(manifest)
        if str(row.get("source_ref") or "")
    }


def _word_tokens(value: object) -> set[str]:
    text = str(value or "").replace("_", " ")
    tokens: set[str] = set()
    for raw in text.split():
        token = raw.strip(".,:;!?()[]{}<>\"'").lower()
        if len(token) >= 3:
            tokens.add(token)
    return tokens


def _source_strategy_artifact_payloads(input_dir: Path) -> tuple[
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
]:
    rows_by_ref = _artifact_rows_by_source_ref(input_dir)
    artifacts: dict[str, dict[str, Any]] = {}
    findings: list[dict[str, Any]] = []
    for source_ref in SOURCE_STRATEGY_ARTIFACT_REFS:
        row = rows_by_ref.get(source_ref)
        if row is None:
            findings.append(
                _finding(
                    "MATH_STRATEGY_SOURCE_ARTIFACT_ROW_MISSING",
                    "Strategy atlas source_module_manifest must name the copied strategy runtime artifact.",
                    case_id="source_artifact_consistency",
                    subject_id=source_ref,
                    subject_kind="source_ref",
                )
            )
            continue
        target = _source_module_target_path(input_dir, row)
        if not target.is_file():
            findings.append(
                _finding(
                    "MATH_STRATEGY_SOURCE_ARTIFACT_TARGET_MISSING",
                    "Copied strategy runtime artifact target is missing.",
                    case_id="source_artifact_consistency",
                    subject_id=source_ref,
                    subject_kind="source_artifact",
                )
            )
            continue
        payload = read_json_strict(target)
        if not isinstance(payload, dict):
            findings.append(
                _finding(
                    "MATH_STRATEGY_SOURCE_ARTIFACT_PAYLOAD_UNSUPPORTED",
                    "Copied strategy runtime artifact must be a JSON object.",
                    case_id="source_artifact_consistency",
                    subject_id=source_ref,
                    subject_kind="source_artifact",
                )
            )
            continue
        artifacts[source_ref] = payload
    return artifacts, findings


def _source_card_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in _rows(payload, "cards")
        if str(row.get("strategy_id") or "")
    ]


def _source_card_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["strategy_id"]): row for row in _source_card_rows(payload)}


def _shared_string_values(
    left: dict[str, Any],
    right: dict[str, Any],
    key: str,
) -> list[str]:
    left_values = {value.lower() for value in _string_values(left, key)}
    right_values = {value.lower() for value in _string_values(right, key)}
    return sorted(left_values & right_values)


def _record_forbidden_payload_keys(
    findings: list[dict[str, Any]],
    *,
    row: dict[str, Any],
    code: str,
    message: str,
    subject_id: str,
    subject_kind: str,
) -> None:
    forbidden = sorted(set(_forbidden_body_keys(row)) | (set(row) & set(ORACLE_LABEL_KEYS)))
    if forbidden:
        findings.append(
            _finding(
                code,
                f"{message} Forbidden keys: {', '.join(forbidden)}.",
                case_id="source_artifact_consistency",
                subject_id=subject_id,
                subject_kind=subject_kind,
            )
        )


def validate_source_artifact_consistency(
    input_dir: Path,
    atlas_payload: object,
) -> dict[str, Any]:
    artifacts, findings = _source_strategy_artifact_payloads(input_dir)
    atlas_by_id = _atlas_by_id(atlas_payload)
    cards_payload = artifacts.get(SOURCE_STRATEGY_CARDS_REF, {})
    hypothesis_payload = artifacts.get(SOURCE_STRATEGY_HYPOTHESIS_SET_REF, {})
    skill_payload = artifacts.get(SOURCE_PROVER_SKILL_ATLAS_REF, {})

    card_by_id = _source_card_by_id(cards_payload)
    source_card_ids = sorted(card_by_id)
    atlas_ids = sorted(atlas_by_id)
    overlapping_strategy_ids = sorted(
        (set(source_card_ids) & set(atlas_ids)) - {UNKNOWN_STRATEGY_ID}
    )

    card_count = _int_or_none(cards_payload.get("card_count"))
    cards = _source_card_rows(cards_payload)
    if cards_payload and card_count is not None and card_count != len(cards):
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_CARD_COUNT_MISMATCH",
                "Copied strategy card artifact card_count must match cards length.",
                case_id="source_artifact_consistency",
                subject_id=SOURCE_STRATEGY_CARDS_REF,
                subject_kind="source_artifact",
            )
        )
    card_policy = cards_payload.get("leakage_policy", {})
    if not isinstance(card_policy, dict):
        card_policy = {}
    if cards_payload and card_policy.get("oracle_expected_strategy_visible_to_lab") is not False:
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_CARD_ORACLE_VISIBILITY_FORBIDDEN",
                "Copied strategy card artifact must keep oracle expected strategy ids hidden.",
                case_id="source_artifact_consistency",
                subject_id=SOURCE_STRATEGY_CARDS_REF,
                subject_kind="leakage_policy",
            )
        )
    if cards_payload and card_policy.get("truth_side_proof_bodies_in_cards") is not False:
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_CARD_PROOF_BODY_VISIBILITY_FORBIDDEN",
                "Copied strategy card artifact must keep truth-side proof bodies out of cards.",
                case_id="source_artifact_consistency",
                subject_id=SOURCE_STRATEGY_CARDS_REF,
                subject_kind="leakage_policy",
            )
        )
    for strategy_id, card in card_by_id.items():
        _record_forbidden_payload_keys(
            findings,
            row=card,
            code="MATH_STRATEGY_SOURCE_CARD_FORBIDDEN_PAYLOAD_KEY",
            message="Copied strategy card cannot carry proof, provider, source, or oracle body fields.",
            subject_id=strategy_id,
            subject_kind="source_strategy_card",
        )
    if cards_payload and not overlapping_strategy_ids:
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_CARD_ATLAS_OVERLAP_MISSING",
                "Fixture strategy atlas must overlap copied source strategy cards before scoring can claim source-grounded projection.",
                case_id="source_artifact_consistency",
                subject_id=SOURCE_STRATEGY_CARDS_REF,
                subject_kind="source_artifact",
            )
        )
    disconnected_strategy_ids: list[str] = []
    for strategy_id in overlapping_strategy_ids:
        card = card_by_id[strategy_id]
        atlas_row = atlas_by_id[strategy_id]
        retrieval_overlap = _shared_string_values(
            card,
            atlas_row,
            "retrieval_expansion_terms",
        )
        tactic_overlap = _shared_string_values(
            card,
            atlas_row,
            "lean_tactic_affordances",
        )
        lens_overlap = sorted(
            _word_tokens(card.get("mathematical_lens"))
            & _word_tokens(atlas_row.get("mathematical_lens"))
        )
        if not retrieval_overlap and not tactic_overlap and len(lens_overlap) < 3:
            disconnected_strategy_ids.append(strategy_id)
    if disconnected_strategy_ids:
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_CARD_ATLAS_DISCONNECTED",
                "Overlapping fixture strategies must preserve retrieval, tactic, or lens material from copied source strategy cards.",
                case_id="source_artifact_consistency",
                subject_id=",".join(disconnected_strategy_ids),
                subject_kind="strategy_id",
            )
        )

    hypotheses = _rows(hypothesis_payload, "strategy_hypotheses")
    hypothesis_ids = sorted(
        {
            str(row.get("strategy_id"))
            for row in hypotheses
            if str(row.get("strategy_id") or "")
        }
    )
    selected_hypothesis_id = str(hypothesis_payload.get("selected_strategy_id") or "")
    if hypothesis_payload.get("proof_body_visible") is not False:
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_HYPOTHESIS_PROOF_BODY_VISIBILITY_FORBIDDEN",
                "Copied strategy hypothesis set must keep proof bodies hidden.",
                case_id="source_artifact_consistency",
                subject_id=SOURCE_STRATEGY_HYPOTHESIS_SET_REF,
                subject_kind="leakage_policy",
            )
        )
    if hypothesis_payload.get("oracle_expected_strategy_ids_visible") is not False:
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_HYPOTHESIS_ORACLE_VISIBILITY_FORBIDDEN",
                "Copied strategy hypothesis set must keep oracle expected strategy ids hidden.",
                case_id="source_artifact_consistency",
                subject_id=SOURCE_STRATEGY_HYPOTHESIS_SET_REF,
                subject_kind="leakage_policy",
            )
        )
    if str(hypothesis_payload.get("strategy_phase") or "") != "pre_oracle":
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_HYPOTHESIS_PHASE_NOT_PRE_ORACLE",
                "Copied strategy hypothesis set must remain pre-oracle.",
                case_id="source_artifact_consistency",
                subject_id=SOURCE_STRATEGY_HYPOTHESIS_SET_REF,
                subject_kind="strategy_phase",
            )
        )
    if selected_hypothesis_id and selected_hypothesis_id not in hypothesis_ids:
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_HYPOTHESIS_SELECTED_ID_NOT_IN_SET",
                "Copied strategy hypothesis selected_strategy_id must be one of its own strategy_hypotheses.",
                case_id="source_artifact_consistency",
                subject_id=selected_hypothesis_id,
                subject_kind="strategy_id",
            )
        )
    hypothesis_ids_missing_cards = sorted(set(hypothesis_ids) - set(source_card_ids))
    if hypothesis_ids_missing_cards:
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_HYPOTHESIS_ID_NOT_IN_CARDS",
                "Copied strategy hypothesis ids must be backed by copied source strategy cards.",
                case_id="source_artifact_consistency",
                subject_id=",".join(hypothesis_ids_missing_cards),
                subject_kind="strategy_id",
            )
        )
    for row in hypotheses:
        _record_forbidden_payload_keys(
            findings,
            row=row,
            code="MATH_STRATEGY_SOURCE_HYPOTHESIS_FORBIDDEN_PAYLOAD_KEY",
            message="Copied strategy hypothesis rows cannot carry proof, provider, source, or oracle body fields.",
            subject_id=str(row.get("strategy_id") or "strategy_hypothesis"),
            subject_kind="strategy_hypothesis",
        )

    skill_policy = skill_payload.get("leakage_policy", {})
    if not isinstance(skill_policy, dict):
        skill_policy = {}
    if skill_payload and skill_policy.get("truth_side_proof_bodies_in_skill_cells") is not False:
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_SKILL_PROOF_BODY_VISIBILITY_FORBIDDEN",
                "Copied prover skill atlas must keep truth-side proof bodies out of skill cells.",
                case_id="source_artifact_consistency",
                subject_id=SOURCE_PROVER_SKILL_ATLAS_REF,
                subject_kind="leakage_policy",
            )
        )
    if skill_payload and skill_policy.get("oracle_needed_premise_ids_visible_before_check") is not False:
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_SKILL_ORACLE_PREMISE_VISIBILITY_FORBIDDEN",
                "Copied prover skill atlas must keep oracle premise ids hidden before check.",
                case_id="source_artifact_consistency",
                subject_id=SOURCE_PROVER_SKILL_ATLAS_REF,
                subject_kind="leakage_policy",
            )
        )
    mappings = _rows(skill_payload, "strategy_card_mapping")
    mapped_strategy_ids = sorted(
        {
            str(row.get("strategy_id"))
            for row in mappings
            if str(row.get("strategy_id") or "")
        }
    )
    mapped_ids_missing_cards = sorted(set(mapped_strategy_ids) - set(source_card_ids))
    if mapped_ids_missing_cards:
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_SKILL_MAPPING_ID_NOT_IN_CARDS",
                "Copied prover skill atlas strategy_card_mapping ids must refer to copied source strategy cards.",
                case_id="source_artifact_consistency",
                subject_id=",".join(mapped_ids_missing_cards),
                subject_kind="strategy_id",
            )
        )
    cells = _rows(skill_payload, "cells")
    skill_cell_count = _int_or_none(skill_payload.get("skill_cell_count"))
    if skill_payload and skill_cell_count is not None and skill_cell_count != len(cells):
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_SKILL_CELL_COUNT_MISMATCH",
                "Copied prover skill atlas skill_cell_count must match cells length.",
                case_id="source_artifact_consistency",
                subject_id=SOURCE_PROVER_SKILL_ATLAS_REF,
                subject_kind="source_artifact",
            )
        )
    skill_source_card_ids: set[str] = set()
    for cell in cells:
        for strategy_id in _string_values(cell.get("provenance", {}), "source_strategy_cards"):
            skill_source_card_ids.add(strategy_id)
        _record_forbidden_payload_keys(
            findings,
            row=cell,
            code="MATH_STRATEGY_SOURCE_SKILL_FORBIDDEN_PAYLOAD_KEY",
            message="Copied prover skill cells cannot carry proof, provider, source, or oracle body fields.",
            subject_id=str(cell.get("skill_id") or "prover_skill_cell"),
            subject_kind="prover_skill_cell",
        )
    skill_source_ids_missing_cards = sorted(skill_source_card_ids - set(source_card_ids))
    if skill_source_ids_missing_cards:
        findings.append(
            _finding(
                "MATH_STRATEGY_SOURCE_SKILL_SOURCE_CARD_ID_NOT_IN_CARDS",
                "Copied prover skill cells must reference copied source strategy cards.",
                case_id="source_artifact_consistency",
                subject_id=",".join(skill_source_ids_missing_cards),
                subject_kind="strategy_id",
            )
        )

    return {
        "source_artifact_consistency_status": SOURCE_ARTIFACT_CONSISTENCY_STATUS,
        "source_artifact_consistency_pass": not findings,
        "source_strategy_card_count": len(cards),
        "source_strategy_card_ids": source_card_ids,
        "atlas_strategy_ids": atlas_ids,
        "overlapping_source_strategy_ids": overlapping_strategy_ids,
        "source_only_strategy_ids": sorted(set(source_card_ids) - set(atlas_ids)),
        "source_strategy_hypothesis_count": len(hypotheses),
        "source_strategy_hypothesis_ids": hypothesis_ids,
        "selected_source_hypothesis_id": selected_hypothesis_id,
        "source_skill_mapping_count": len(mappings),
        "source_skill_cell_count": len(cells),
        "source_skill_source_card_ids": sorted(skill_source_card_ids),
        "checked_source_artifact_refs": sorted(artifacts),
        "findings": findings,
        "body_redacted": True,
    }


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


def _string_values(row: dict[str, Any], key: str) -> list[str]:
    values = row.get(key, [])
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if isinstance(value, str)]


def _strategy_rows(payload: object) -> list[dict[str, Any]]:
    rows = _rows(payload, "strategies")
    return [row for row in rows if str(row.get("strategy_id") or "")]


def _atlas_by_id(payload: object) -> dict[str, dict[str, Any]]:
    return {str(row["strategy_id"]): row for row in _strategy_rows(payload)}


def _strategy_feature_values(strategy: dict[str, Any], primary_key: str) -> set[str]:
    primary = set(_string_values(strategy, primary_key))
    if primary:
        return primary
    if primary_key == "trigger_features":
        return set(_string_values(strategy, "match_features"))
    return set()


def _strategy_retrieval_terms(strategy: dict[str, Any]) -> list[str]:
    terms = _string_values(strategy, "retrieval_expansion_terms")
    if terms:
        return terms
    return _string_values(strategy, "retrieval_term_additions")


def _retrieval_query_terms(
    problem: dict[str, Any],
    case: dict[str, Any],
) -> list[str]:
    terms = _string_values(problem, "retrieval_query_terms")
    terms.extend(_string_values(case, "retrieval_query_terms"))
    seen: set[str] = set()
    deduped: list[str] = []
    for term in terms:
        normalized = term.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(term)
    return deduped


def _feature_overlap_count(problem_features: set[str], strategy: dict[str, Any]) -> int:
    match_features = {
        str(value)
        for value in strategy.get("match_features", [])
        if isinstance(value, str)
    }
    return len(problem_features & match_features)


def _score_strategy(
    *,
    strategy_id: str,
    strategy: dict[str, Any],
    order: int,
    problem_features: set[str],
    retrieval_query_terms: list[str],
) -> dict[str, Any]:
    trigger_features = _strategy_feature_values(strategy, "trigger_features")
    negative_triggers = _strategy_feature_values(strategy, "negative_triggers")
    retrieval_expansion_terms = _strategy_retrieval_terms(strategy)
    retrieval_text = " ".join(retrieval_expansion_terms).lower()
    trigger_hits = sorted(problem_features & trigger_features)
    negative_hits = sorted(problem_features & negative_triggers)
    retrieval_hits = [
        term
        for term in retrieval_query_terms
        if term.lower() in retrieval_text
    ]
    retrieval_bonus = min(len(retrieval_hits) * RETRIEVAL_TERM_BONUS, RETRIEVAL_BONUS_CAP)
    score = (
        len(trigger_hits) * TRIGGER_FEATURE_WEIGHT
        - len(negative_hits) * NEGATIVE_TRIGGER_PENALTY
        + retrieval_bonus
    )
    return {
        "strategy_id": strategy_id,
        "score": score,
        "feature_overlap_count": _feature_overlap_count(problem_features, strategy),
        "trigger_feature_hits": trigger_hits,
        "negative_trigger_hits": negative_hits,
        "retrieval_term_hits": sorted(retrieval_hits),
        "retrieval_bonus": retrieval_bonus,
        "score_components": {
            "trigger_feature_hit_count": len(trigger_hits),
            "trigger_feature_weight": TRIGGER_FEATURE_WEIGHT,
            "negative_trigger_hit_count": len(negative_hits),
            "negative_trigger_penalty": NEGATIVE_TRIGGER_PENALTY,
            "retrieval_term_hit_count": len(retrieval_hits),
            "retrieval_term_bonus": RETRIEVAL_TERM_BONUS,
            "retrieval_bonus_cap": RETRIEVAL_BONUS_CAP,
        },
        "strategy_order": order,
    }


def _normalized_candidate_scores(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    rows: list[dict[str, Any]] = []
    for rank, row in enumerate(payload, start=1):
        if not isinstance(row, dict):
            continue
        strategy_id = str(row.get("strategy_id") or "")
        if not strategy_id:
            continue
        rows.append(
            {
                "strategy_id": strategy_id,
                "score": _int_or_none(row.get("score")),
                "rank": rank,
            }
        )
    return rows


def _verify_declared_case_outcomes(
    case: dict[str, Any],
    derived_case: dict[str, Any],
) -> dict[str, Any]:
    declared_fields_present = [
        field for field in DECLARED_OUTCOME_FIELDS if field in case
    ]
    mismatches: list[dict[str, Any]] = []
    for field in declared_fields_present:
        if field == "candidate_scores":
            declared_value = _normalized_candidate_scores(case.get(field))
            derived_value = _normalized_candidate_scores(
                derived_case.get("candidate_scores")
            )
        elif field in {"score", "retrieval_bonus"}:
            declared_value = _int_or_none(case.get(field))
            derived_value = _int_or_none(derived_case.get(field))
        else:
            declared_value = str(case.get(field) or "")
            derived_value = str(derived_case.get(field) or "")
        if declared_value != derived_value:
            mismatches.append(
                {
                    "field": field,
                    "declared_value": declared_value,
                    "derived_value": derived_value,
                }
            )
    declared_selection_label_only = declared_fields_present == ["selected_strategy_id"]
    return {
        "declared_outcome_fields_present": declared_fields_present,
        "declared_outcome_mismatches": mismatches,
        "declared_selection_label_only": declared_selection_label_only,
        "declared_outcome_verification_pass": (
            not mismatches and not declared_selection_label_only
        ),
        "declared_outcome_status": (
            "declared_selection_label_only_forbidden"
            if declared_selection_label_only
            else (
                "declared_outcomes_match_recomputed_evidence"
                if declared_fields_present and not mismatches
                else (
                    "declared_outcomes_contradict_recomputed_evidence"
                    if mismatches
                    else "no_declared_outcomes_present"
                )
            )
        ),
    }


def _record_declared_selection_label_only(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    *,
    case_id: str,
) -> None:
    _record(
        findings,
        observed,
        DECLARED_SELECTION_LABEL_ONLY_ERROR_CODE,
        "Declared selected_strategy_id alone is a label-only bake surface and cannot count as strategy evidence.",
        case_id=case_id,
        subject_id=f"{case_id}:selected_strategy_id",
        subject_kind="strategy_id",
    )


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
    query_terms = _retrieval_query_terms(problem, case)
    candidate_ids = [
        str(value)
        for value in case.get("candidate_strategy_ids", strategy_order)
        if isinstance(value, str)
    ]
    candidate_ids = [strategy_id for strategy_id in candidate_ids if strategy_id != UNKNOWN_STRATEGY_ID]
    scored: list[dict[str, Any]] = []
    for strategy_id in candidate_ids:
        strategy = atlas_by_id.get(strategy_id)
        if strategy is None:
            continue
        order = strategy_order.index(strategy_id) if strategy_id in strategy_order else len(strategy_order)
        scored.append(
            _score_strategy(
                strategy_id=strategy_id,
                strategy=strategy,
                order=order,
                problem_features=problem_features,
                retrieval_query_terms=query_terms,
            )
        )
    selected_strategy_id = UNKNOWN_STRATEGY_ID
    selected_score = 0
    feature_overlap_count = 0
    trigger_feature_hits: list[str] = []
    negative_trigger_hits: list[str] = []
    retrieval_term_hits: list[str] = []
    retrieval_bonus = 0
    positive_scored = [row for row in scored if row["score"] > 0]
    if positive_scored:
        selected_score_row = sorted(
            positive_scored,
            key=lambda item: (
                -int(item["score"]),
                int(item["strategy_order"]),
                str(item["strategy_id"]),
            ),
        )[0]
        selected_strategy_id = str(selected_score_row["strategy_id"])
        selected_score = int(selected_score_row["score"])
        feature_overlap_count = int(selected_score_row["feature_overlap_count"])
        trigger_feature_hits = list(selected_score_row["trigger_feature_hits"])
        negative_trigger_hits = list(selected_score_row["negative_trigger_hits"])
        retrieval_term_hits = list(selected_score_row["retrieval_term_hits"])
        retrieval_bonus = int(selected_score_row["retrieval_bonus"])
    selected = atlas_by_id.get(selected_strategy_id, {})
    classifier = (
        "matched_strategy"
        if selected_strategy_id != UNKNOWN_STRATEGY_ID
        else "STRATEGY_SELECTION_MISS"
    )
    retrieval_terms = _string_values(selected, "retrieval_term_additions")
    if not retrieval_terms:
        retrieval_terms = _strategy_retrieval_terms(selected)
    expected = str(case.get("expected_strategy_id") or selected_strategy_id)
    expected_classifier = (
        str(case.get("expected_classifier") or "")
        if "expected_classifier" in case
        else None
    )
    expected_score = _int_or_none(case.get("expected_score"))
    result = {
        "case_id": case_id,
        "problem_id": problem_id,
        "feature_tags": sorted(problem_features),
        "retrieval_query_terms": sorted(query_terms),
        "candidate_strategy_ids": candidate_ids,
        "selected_strategy_id": selected_strategy_id,
        "score": selected_score,
        "feature_overlap_count": feature_overlap_count,
        "trigger_feature_hits": trigger_feature_hits,
        "negative_trigger_hits": negative_trigger_hits,
        "retrieval_term_hits": retrieval_term_hits,
        "retrieval_bonus": retrieval_bonus,
        "candidate_scores": sorted(
            scored,
            key=lambda item: (
                -int(item["score"]),
                int(item["strategy_order"]),
                str(item["strategy_id"]),
            ),
        ),
        "scoring_model": {
            "model_id": "weighted_trigger_negative_retrieval_v1",
            "trigger_feature_weight": TRIGGER_FEATURE_WEIGHT,
            "negative_trigger_penalty": NEGATIVE_TRIGGER_PENALTY,
            "retrieval_term_bonus": RETRIEVAL_TERM_BONUS,
            "retrieval_bonus_cap": RETRIEVAL_BONUS_CAP,
            "feature_overlap_is_diagnostic_only": True,
        },
        "classifier": classifier,
        "expected_strategy_id": expected,
        "expected_classifier": expected_classifier,
        "expected_score": expected_score,
        "retrieval_term_additions": retrieval_terms,
        "pre_oracle": case.get("pre_oracle") is not False,
        "derivation_status": STRATEGY_DERIVATION_STATUS,
        "body_redacted": True,
    }
    result["classifier_expectation_met"] = (
        True if expected_classifier is None else classifier == expected_classifier
    )
    result["score_expectation_met"] = (
        True if expected_score is None else selected_score == expected_score
    )
    result["expectation_met"] = (
        selected_strategy_id == expected
        and result["classifier_expectation_met"]
        and result["score_expectation_met"]
    )
    result.update(_verify_declared_case_outcomes(case, result))
    return result


def _validate_input_strategy_cards(
    atlas_payload: object,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    required_fields = (
        "trigger_features",
        "negative_triggers",
        "retrieval_expansion_terms",
        "proof_plan_template",
    )
    for row in _strategy_rows(atlas_payload):
        strategy_id = str(row.get("strategy_id") or "strategy_card")
        if strategy_id == UNKNOWN_STRATEGY_ID:
            continue
        missing_fields = [
            field
            for field in required_fields
            if not _string_values(row, field)
            and not str(row.get(field) or "").strip()
        ]
        if missing_fields:
            findings.append(
                _finding(
                    "MATH_STRATEGY_RICH_CARD_FIELDS_REQUIRED",
                    "Input strategy atlas rows must keep rich scoring fields; label-only or legacy sparse cards are invalid strategy evidence.",
                    case_id="strategy_atlas_input",
                    subject_id=strategy_id,
                    subject_kind="strategy_card",
                )
            )
    return {
        "input_strategy_card_validation_pass": not findings,
        "input_strategy_card_findings": findings,
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
    input_strategy_cards = _validate_input_strategy_cards(atlas_payload)
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

    findings: list[dict[str, Any]] = list(
        input_strategy_cards["input_strategy_card_findings"]
    )
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

    overlap_negative = negative_payloads.get("superficial_overlap_only_scoring")
    if isinstance(overlap_negative, dict):
        case_id = str(
            overlap_negative.get("expected_negative_case_id")
            or "superficial_overlap_only_scoring"
        )
        if overlap_negative.get("legacy_overlap_only_scoring_allowed") is True:
            _record(
                findings,
                observed,
                "MATH_STRATEGY_OVERLAP_ONLY_SCORING_FORBIDDEN",
                "Strategy ranking cannot use legacy unweighted overlap as the decision rule.",
                case_id=case_id,
                subject_id=str(overlap_negative.get("subject_id") or "strategy_score"),
                subject_kind="scoring_model",
            )

    rich_card_negative = negative_payloads.get("missing_rich_strategy_card_fields")
    if isinstance(rich_card_negative, dict):
        case_id = str(
            rich_card_negative.get("expected_negative_case_id")
            or "missing_rich_strategy_card_fields"
        )
        required_fields = (
            "trigger_features",
            "negative_triggers",
            "retrieval_expansion_terms",
            "proof_plan_template",
        )
        for row in _rows(rich_card_negative, "strategies") or [rich_card_negative]:
            missing_fields = [
                field
                for field in required_fields
                if not _string_values(row, field)
                and not str(row.get(field) or "").strip()
            ]
            if missing_fields:
                _record(
                    findings,
                    observed,
                    "MATH_STRATEGY_RICH_CARD_FIELDS_REQUIRED",
                    "Weighted strategy scoring requires rich strategy-card fields, not only legacy match_features.",
                    case_id=case_id,
                    subject_id=str(row.get("strategy_id") or "strategy_card"),
                    subject_kind="strategy_card",
                )

    ceiling_negative = negative_payloads.get("retrieval_bonus_ceiling_overclaim")
    if isinstance(ceiling_negative, dict):
        case_id = str(
            ceiling_negative.get("expected_negative_case_id")
            or "retrieval_bonus_ceiling_overclaim"
        )
        claimed_cap = _int_or_none(ceiling_negative.get("retrieval_bonus_cap"))
        if claimed_cap is None or claimed_cap > RETRIEVAL_BONUS_CAP:
            _record(
                findings,
                observed,
                "MATH_STRATEGY_RETRIEVAL_BONUS_CEILING_REQUIRED",
                "Retrieval-term matches are a bounded bonus and cannot dominate trigger and negative-trigger evidence.",
                case_id=case_id,
                subject_id=str(ceiling_negative.get("subject_id") or "retrieval_bonus"),
                subject_kind="scoring_model",
            )

    for row in scored_cases:
        case_id = str(row.get("case_id") or "strategy_case")
        if row.get("declared_selection_label_only") is True:
            _record_declared_selection_label_only(
                findings,
                observed,
                case_id=case_id,
            )
        for mismatch in row.get("declared_outcome_mismatches", []):
            if not isinstance(mismatch, dict):
                continue
            field = str(mismatch.get("field") or "")
            spec = DECLARED_OUTCOME_ERROR_SPECS.get(field)
            if spec is None:
                continue
            code, message, subject_kind = spec
            _record(
                findings,
                observed,
                code,
                message,
                case_id=case_id,
                subject_id=f"{case_id}:{field}",
                subject_kind=subject_kind,
            )

    declared_case_count = sum(
        1
        for row in scored_cases
        if isinstance(row, dict) and row.get("declared_outcome_fields_present")
    )
    declared_outcome_mismatch_count = sum(
        len(row.get("declared_outcome_mismatches", []))
        for row in scored_cases
        if isinstance(row, dict)
    )
    declared_outcome_verification_pass = all(
        isinstance(row, dict)
        and row.get("declared_outcome_verification_pass") is True
        for row in scored_cases
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
        "input_strategy_card_validation_pass": input_strategy_cards[
            "input_strategy_card_validation_pass"
        ],
        "declared_outcome_verification_pass": declared_outcome_verification_pass,
        "declared_case_count": declared_case_count,
        "declared_outcome_mismatch_count": declared_outcome_mismatch_count,
        "declared_outcome_checked_fields": sorted(
            {
                field
                for row in scored_cases
                if isinstance(row, dict)
                for field in row.get("declared_outcome_fields_present", [])
            }
        ),
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
            "weighted_trigger_scoring": True,
            "negative_triggers_penalized": True,
            "retrieval_bonus_capped": True,
            "feature_overlap_is_diagnostic_only": True,
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
            "scoring_model": {
                "model_id": "weighted_trigger_negative_retrieval_v1",
                "trigger_feature_weight": TRIGGER_FEATURE_WEIGHT,
                "negative_trigger_penalty": NEGATIVE_TRIGGER_PENALTY,
                "retrieval_term_bonus": RETRIEVAL_TERM_BONUS,
                "retrieval_bonus_cap": RETRIEVAL_BONUS_CAP,
                "feature_overlap_is_diagnostic_only": True,
            },
            "scored_cases": result["scored_cases"],
            "body_redacted": True,
        },
        "scoring_derivation": result["scoring_derivation"],
        "source_body_import_projection": {
            "source_module_manifest_ref": result["source_module_manifest_ref"],
            "body_material_status": result["body_material_status"],
            "source_module_import_status": result["source_module_import_status"],
            "source_module_import_count": result["source_module_import_count"],
            "copied_source_artifact_count": result["copied_source_artifact_count"],
            "source_modules_pass": result["source_modules_pass"],
            "source_refs": result["source_refs"],
            "target_refs": result["source_module_target_refs"],
            "material_classes": result["source_module_material_classes"],
            "body_in_receipt": False,
        },
        "source_artifact_consistency_projection": {
            "source_artifact_consistency_status": result[
                "source_artifact_consistency_status"
            ],
            "source_artifact_consistency_pass": result[
                "source_artifact_consistency_pass"
            ],
            "source_strategy_card_count": result["source_strategy_card_count"],
            "overlapping_source_strategy_ids": result[
                "overlapping_source_strategy_ids"
            ],
            "source_only_strategy_ids": result["source_only_strategy_ids"],
            "source_strategy_hypothesis_count": result[
                "source_strategy_hypothesis_count"
            ],
            "selected_source_hypothesis_id": result[
                "selected_source_hypothesis_id"
            ],
            "source_skill_mapping_count": result["source_skill_mapping_count"],
            "source_skill_cell_count": result["source_skill_cell_count"],
            "checked_source_artifact_refs": result["checked_source_artifact_refs"],
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
    source_imports = validate_source_module_imports(
        input_dir,
        required=input_mode == "exported_mathematical_strategy_atlas_bundle",
        public_root=public_root,
    )
    source_artifacts = validate_source_artifact_consistency(
        input_dir,
        payloads["strategy_atlas"],
    )
    observed = _merge_observed(scoring)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(scoring, source_imports, source_artifacts)
    error_codes = sorted({finding["error_code"] for finding in findings})
    status = (
        PASS
        if not missing
        and not private_scan["blocking_hit_count"]
        and scoring["all_expectations_met"]
        and scoring["input_strategy_card_validation_pass"]
        and scoring["declared_outcome_verification_pass"]
        and source_imports["source_modules_pass"]
        and source_artifacts["source_artifact_consistency_pass"]
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
        "body_material_status": source_imports["body_material_status"],
        "source_module_import_status": source_imports["source_module_import_status"],
        "source_module_manifest_ref": source_imports["source_module_manifest_ref"],
        "source_module_imports": source_imports["source_module_imports"],
        "source_module_import_count": source_imports["source_module_import_count"],
        "copied_source_artifact_count": source_imports["copied_source_artifact_count"],
        "source_modules_pass": source_imports["source_modules_pass"],
        "source_module_target_refs": source_imports["target_refs"],
        "source_module_material_classes": source_imports["material_classes"],
        "source_artifact_consistency_status": source_artifacts[
            "source_artifact_consistency_status"
        ],
        "source_artifact_consistency_pass": source_artifacts[
            "source_artifact_consistency_pass"
        ],
        "source_strategy_card_count": source_artifacts["source_strategy_card_count"],
        "source_strategy_card_ids": source_artifacts["source_strategy_card_ids"],
        "overlapping_source_strategy_ids": source_artifacts[
            "overlapping_source_strategy_ids"
        ],
        "source_only_strategy_ids": source_artifacts["source_only_strategy_ids"],
        "source_strategy_hypothesis_count": source_artifacts[
            "source_strategy_hypothesis_count"
        ],
        "source_strategy_hypothesis_ids": source_artifacts[
            "source_strategy_hypothesis_ids"
        ],
        "selected_source_hypothesis_id": source_artifacts[
            "selected_source_hypothesis_id"
        ],
        "source_skill_mapping_count": source_artifacts[
            "source_skill_mapping_count"
        ],
        "source_skill_cell_count": source_artifacts["source_skill_cell_count"],
        "source_skill_source_card_ids": source_artifacts[
            "source_skill_source_card_ids"
        ],
        "checked_source_artifact_refs": source_artifacts[
            "checked_source_artifact_refs"
        ],
        "strategy_ids": scoring["strategy_ids"],
        "strategy_count": scoring["strategy_count"],
        "problem_count": scoring["problem_count"],
        "hypothesis_case_count": scoring["hypothesis_case_count"],
        "scored_cases": scoring["scored_cases"],
        "selected_strategy_ids": scoring["selected_strategy_ids"],
        "strategy_selection_miss_case_ids": scoring["strategy_selection_miss_case_ids"],
        "all_expectations_met": scoring["all_expectations_met"],
        "scoring_derivation": {
            "status": STRATEGY_DERIVATION_STATUS,
            "authoritative_input_fields": SCORING_DERIVATION_INPUT_FIELDS,
            "input_strategy_card_validation_pass": scoring[
                "input_strategy_card_validation_pass"
            ],
            "declared_outcome_checked_fields": scoring[
                "declared_outcome_checked_fields"
            ],
            "declared_case_count": scoring["declared_case_count"],
            "declared_outcome_mismatch_count": scoring[
                "declared_outcome_mismatch_count"
            ],
            "declared_outcome_verification_pass": scoring[
                "declared_outcome_verification_pass"
            ],
        },
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
        "body_material_status",
        "source_module_import_status",
        "source_module_manifest_ref",
        "source_module_import_count",
        "copied_source_artifact_count",
        "source_modules_pass",
        "source_artifact_consistency_status",
        "source_artifact_consistency_pass",
        "source_strategy_card_count",
        "overlapping_source_strategy_ids",
        "source_only_strategy_ids",
        "source_strategy_hypothesis_count",
        "selected_source_hypothesis_id",
        "source_skill_mapping_count",
        "source_skill_cell_count",
        "checked_source_artifact_refs",
        "strategy_ids",
        "strategy_count",
        "problem_count",
        "hypothesis_case_count",
        "selected_strategy_ids",
        "strategy_selection_miss_case_ids",
        "all_expectations_met",
        "scoring_derivation",
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
            "weighted_trigger_scoring": True,
            "negative_triggers_penalized": True,
            "retrieval_bonus_capped": True,
            "feature_overlap_is_diagnostic_only": True,
            "proof_bodies_excluded": True,
            "oracle_labels_excluded": True,
            "known_strategy_ids_only": True,
            "declared_outcomes_recomputed": result["scoring_derivation"][
                "declared_outcome_verification_pass"
            ],
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
            "weighted_strategy_scoring_retained": result["status"] == PASS,
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
    if "receipts" in receipt_path.parts:
        receipts_index = len(receipt_path.parts) - 1 - list(
            reversed(receipt_path.parts)
        ).index("receipts")
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
        "formal_proof_authority": authority.get("formal_proof_authority") is True,
        "oracle_label_visibility_authorized": authority.get(
            "oracle_label_visibility_authorized"
        )
        is True,
        "provider_calls_authorized": authority.get("provider_calls_authorized")
        is True,
        "release_authorized": authority.get("release_authorized") is True,
        "provider_payload_bodies_allowed": authority.get(
            "provider_payload_bodies_allowed"
        )
        is True,
    }


def _private_scan_card(result: dict[str, Any]) -> dict[str, Any]:
    scan = result.get("private_state_scan", {})
    if not isinstance(scan, dict):
        scan = {}
    return {
        "status": scan.get("status"),
        "hit_count": scan.get("hit_count"),
        "blocking_hit_count": scan.get("blocking_hit_count"),
        "scanned_path_count": scan.get("scanned_path_count"),
        "body_redacted": scan.get("body_redacted") is True,
        "redacted_output_field_labels_omitted": scan.get(
            "redacted_output_field_labels_omitted"
        )
        is True,
    }


def _source_module_card(result: dict[str, Any]) -> dict[str, Any]:
    imports = result.get("source_module_imports", [])
    rows = imports if isinstance(imports, list) else []
    digest_match_count = sum(
        1 for row in rows if isinstance(row, dict) and row.get("digest_match") is True
    )
    exists_count = sum(
        1 for row in rows if isinstance(row, dict) and row.get("exists") is True
    )
    return {
        "status": result.get("source_module_import_status"),
        "manifest_ref": result.get("source_module_manifest_ref"),
        "source_modules_pass": result.get("source_modules_pass") is True,
        "source_module_import_count": result.get("source_module_import_count"),
        "copied_source_artifact_count": result.get("copied_source_artifact_count"),
        "exists_count": exists_count,
        "digest_match_count": digest_match_count,
        "material_classes": result.get("source_module_material_classes", []),
        "source_ref_count": len(
            {
                str(row.get("source_ref"))
                for row in rows
                if isinstance(row, dict) and row.get("source_ref")
            }
        ),
        "body_material_status": result.get("body_material_status"),
    }


def _scored_case_card(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": row.get("case_id"),
        "problem_id": row.get("problem_id"),
        "selected_strategy_id": row.get("selected_strategy_id"),
        "classifier": row.get("classifier"),
        "score": row.get("score"),
        "feature_overlap_count": row.get("feature_overlap_count"),
        "retrieval_bonus": row.get("retrieval_bonus"),
        "expectation_met": row.get("expectation_met") is True,
        "pre_oracle": row.get("pre_oracle") is True,
    }


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    scored_cases = result.get("scored_cases", [])
    rows = scored_cases if isinstance(scored_cases, list) else []
    scoring_derivation = result.get("scoring_derivation", {})
    if not isinstance(scoring_derivation, dict):
        scoring_derivation = {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "created_at": result.get("created_at"),
        "status": result.get("status"),
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "counts": {
            "strategy_count": result.get("strategy_count"),
            "problem_count": result.get("problem_count"),
            "hypothesis_case_count": result.get("hypothesis_case_count"),
            "scored_case_count": len(rows),
            "selected_strategy_count": len(result.get("selected_strategy_ids", [])),
            "strategy_selection_miss_count": len(
                result.get("strategy_selection_miss_case_ids", [])
            ),
            "source_module_import_count": result.get("source_module_import_count"),
            "copied_source_artifact_count": result.get("copied_source_artifact_count"),
            "missing_negative_case_count": len(result.get("missing_negative_cases", [])),
            "error_code_count": len(result.get("error_codes", [])),
            "declared_case_count": result.get("scoring_derivation", {}).get(
                "declared_case_count"
            ),
            "declared_outcome_mismatch_count": result.get(
                "scoring_derivation", {}
            ).get("declared_outcome_mismatch_count"),
        },
        "strategy_projection": {
            "selected_strategy_ids": result.get("selected_strategy_ids", []),
            "strategy_selection_miss_case_ids": result.get(
                "strategy_selection_miss_case_ids",
                [],
            ),
            "scoring_model": {
                "model_id": "weighted_trigger_negative_retrieval_v1",
                "trigger_feature_weight": TRIGGER_FEATURE_WEIGHT,
                "negative_trigger_penalty": NEGATIVE_TRIGGER_PENALTY,
                "retrieval_term_bonus": RETRIEVAL_TERM_BONUS,
                "retrieval_bonus_cap": RETRIEVAL_BONUS_CAP,
                "feature_overlap_is_diagnostic_only": True,
            },
            "all_expectations_met": result.get("all_expectations_met") is True,
            "scored_case_cards": [
                _scored_case_card(row) for row in rows if isinstance(row, dict)
            ],
            "body_redacted": result.get("body_redacted") is True,
        },
        "scoring_derivation": {
            "status": scoring_derivation.get("status"),
            "authoritative_input_field_count": len(
                scoring_derivation.get("authoritative_input_fields", [])
            ),
            "input_strategy_card_validation_pass": scoring_derivation.get(
                "input_strategy_card_validation_pass"
            )
            is True,
            "declared_case_count": scoring_derivation.get("declared_case_count"),
            "declared_checked_field_count": len(
                scoring_derivation.get("declared_outcome_checked_fields", [])
            ),
            "declared_outcome_mismatch_count": scoring_derivation.get(
                "declared_outcome_mismatch_count"
            ),
            "declared_outcome_verification_pass": scoring_derivation.get(
                "declared_outcome_verification_pass"
            )
            is True,
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
        "source_artifact_consistency": {
            "pass": result.get("source_artifact_consistency_pass") is True,
            "source_strategy_card_count": result.get("source_strategy_card_count"),
            "overlap_count": len(result.get("overlapping_source_strategy_ids", [])),
            "source_only_strategy_count": len(result.get("source_only_strategy_ids", [])),
            "source_strategy_hypothesis_count": result.get(
                "source_strategy_hypothesis_count"
            ),
            "source_skill_cell_count": result.get("source_skill_cell_count"),
            "checked_ref_count": len(result.get("checked_source_artifact_refs", [])),
            "body_redacted": True,
        },
        "private_state_scan": _private_scan_card(result),
        "authority_ceiling": _authority_ceiling_card(result),
        "body_material_status": result.get("body_material_status"),
        "output_economy": {
            "full_receipt_written": bool(result.get("receipt_paths")),
            "stdout_mode": "card",
            "omitted_field_groups": [
                "detailed_findings_and_receipts",
                "per_candidate_scoring_breakdowns",
                "source_module_body_rows",
                "full_board_projection",
            ],
            "full_payload_drilldown": "rerun without --card",
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate mathematical strategy atlas hypothesis scoring"
    )
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument(
        "--card",
        action="store_true",
        help="Print a compact first-screen card instead of the full result payload.",
    )
    bundle_parser = subparsers.add_parser("run-strategy-bundle")
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
    if args.action == "run":
        command = (
            "python -m microcosm_core.organs.mathematical_strategy_atlas_hypothesis_scorer "
            f"run --input {args.input} --out {args.out}"
            f"{' --card' if args.card else ''}"
        )
        result = run(args.input, args.out, command=command)
    elif args.action == "run-strategy-bundle":
        command = (
            "python -m microcosm_core.organs.mathematical_strategy_atlas_hypothesis_scorer "
            f"run-strategy-bundle --input {args.input} --out {args.out}"
            f"{' --card' if args.card else ''}"
        )
        result = run_strategy_bundle(args.input, args.out, command=command)
    else:
        return 2
    output = result_card(result) if getattr(args, "card", False) else result
    print(json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
