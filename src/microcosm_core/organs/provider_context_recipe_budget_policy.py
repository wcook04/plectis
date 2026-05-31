from __future__ import annotations

import argparse
import hashlib
import json
import math
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


ORGAN_ID = "provider_context_recipe_budget_policy"
FIXTURE_ID = "first_wave.provider_context_recipe_budget_policy"
VALIDATOR_ID = "validator.microcosm.organs.provider_context_recipe_budget_policy"
CARD_SCHEMA_VERSION = "provider_context_recipe_budget_policy_command_card_v1"

RESULT_NAME = "provider_context_budget_result.json"
BOARD_NAME = "provider_context_budget_board.json"
VALIDATION_RECEIPT_NAME = "provider_context_budget_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "provider_context_recipe_budget_policy_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_provider_context_budget_bundle_validation_result.json"

SOURCE_PATTERN_IDS = ["provider_context_recipe_budget_policy"]
SOURCE_REFS = [
    "codex/standards/std_compute_provider.json",
    "codex/standards/std_provider_adapter.json",
    "codex/standards/std_provider_navigation_transform_receipt.json",
    "codex/standards/std_transform_job.json",
    "tools/meta/factory/build_prover_provider_batch_context_calibration_report.py",
    "tools/meta/factory/reduce_prover_provider_receipts.py",
    "tools/meta/factory/run_prover_graph_benchmark.py",
    "tools/meta/factory/run_prover_formal_problem_ladder_eval.py",
]
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"

EXPECTED_SOURCE_MODULES = {
    "provider_context_batch_calibration_report_body_import": {
        "source_ref": "tools/meta/factory/build_prover_provider_batch_context_calibration_report.py",
        "target_ref": (
            "source_modules/tools/meta/factory/"
            "build_prover_provider_batch_context_calibration_report.py"
        ),
        "required_anchors": [
            "Build aggregate reports for the prover provider batch calibration run.",
            "def build_reports(run_root: Path) -> dict[str, Any]:",
            '"schema_version": "prover_provider_reducer_taxonomy_decision_v0"',
            '"schema_version": "prover_provider_recipe_policy_metrics_v0"',
            '"provider_calls_by_reducer": 0',
            '"fake_provider_results_counted": 0',
        ],
    },
    "provider_context_compute_provider_standard_body_import": {
        "source_ref": "codex/standards/std_compute_provider.json",
        "target_ref": "source_modules/codex/standards/std_compute_provider.json",
        "required_anchors": [
            '"schema_version": "std_compute_provider_v1"',
            '"provider_lane_policy"',
            '"scheduler_shape"',
            "provider_receipts plus draft row_patches",
            "records receipts and row patches",
            '"forbidden_to_low_authority_reason"',
        ],
    },
    "provider_context_transform_job_standard_body_import": {
        "source_ref": "codex/standards/std_transform_job.json",
        "target_ref": "source_modules/codex/standards/std_transform_job.json",
        "required_anchors": [
            '"schema_version": "std_transform_job_v1"',
            "provider_receipt",
            "row_patch",
            "provider_selection_policy",
            "local_evidence_override_policy",
            "authority_ceiling",
        ],
    },
    "provider_context_graph_benchmark_body_import": {
        "source_ref": "tools/meta/factory/run_prover_graph_benchmark.py",
        "target_ref": "source_modules/tools/meta/factory/run_prover_graph_benchmark.py",
        "required_anchors": [
            "PROVIDER_CONTEXT_RECIPES = (",
            "DEFAULT_PROVIDER_CONTEXT_RECIPES =",
            "def _provider_context_recipe(recipe_id: str) -> dict[str, Any]:",
            "def _provider_context_pack(",
            "def run_provider_context_sweep(",
            '"schema_version": "prover_provider_context_sweep_run_v0"',
        ],
    },
    "provider_context_formal_ladder_eval_body_import": {
        "source_ref": "tools/meta/factory/run_prover_formal_problem_ladder_eval.py",
        "target_ref": "source_modules/tools/meta/factory/run_prover_formal_problem_ladder_eval.py",
        "required_anchors": [
            'DEFAULT_RECIPES = ("minimal_4kb", "skill_32kb", "repair_32kb")',
            "def compile_jobs(",
            "harness._provider_context_pack(",
            '"schema_version": "provider_context_pack_manifest_v0"',
            "def reduce_dispatched_receipts(",
            '"schema_version": "prover_formal_problem_ladder_recipe_policy_metrics_v0"',
        ],
    },
    "provider_context_provider_adapter_standard_body_import": {
        "source_ref": "codex/standards/std_provider_adapter.json",
        "target_ref": "source_modules/codex/standards/std_provider_adapter.json",
        "required_anchors": [
            '"schema_version": "std_provider_adapter_v1"',
            '"fallback_policy"',
            '"budget_policy"',
            '"receipt_requirements"',
            '"runtime_refactor_gate"',
            "provider receipts when the adapter is used for governed work",
        ],
    },
    "provider_context_provider_navigation_transform_receipt_standard_body_import": {
        "source_ref": "codex/standards/std_provider_navigation_transform_receipt.json",
        "target_ref": (
            "source_modules/codex/standards/"
            "std_provider_navigation_transform_receipt.json"
        ),
        "required_anchors": [
            '"schema_version": "provider_navigation_transform_receipt_v0"',
            '"mutation_authority"',
            "candidate_only rows",
            "Provider output cannot write Task Ledger",
            '"route_pattern_candidate"',
            '"standard_gap_candidate"',
        ],
    },
    "provider_context_receipt_reducer_body_import": {
        "source_ref": "tools/meta/factory/reduce_prover_provider_receipts.py",
        "target_ref": (
            "source_modules/tools/meta/factory/reduce_prover_provider_receipts.py"
        ),
        "required_anchors": [
            "Reduce prover provider receipts into Lean-checked Oracle/Foundry evidence.",
            "TRUTH_SIDE_FORBIDDEN_MARKERS = (",
            "def _truth_side_leakage_hits(",
            "def _classify_failure(",
            "def reduce_receipt(",
            '"schema_version": "provider_receipt_reducer_run_summary_v0"',
        ],
    },
}

EXPECTED_RECIPE_BUDGETS = {
    "minimal_4kb": 4096,
    "premise_16kb": 16384,
    "skill_32kb": 32768,
    "repair_32kb": 32768,
    "fewshot_64kb": 65536,
    "strategy_classification_4kb": 4096,
}

EXPECTED_DELIVERABLES = {
    "minimal_4kb": "environment_metadata",
    "premise_16kb": "ranked_premise_ids",
    "skill_32kb": "strategy_metadata",
    "repair_32kb": "failure_classification",
    "fewshot_64kb": "redacted_synthesis_advisory",
    "strategy_classification_4kb": "strategy_id_classification",
}

FORBIDDEN_SECTION_IDS = {
    "ground_truth_proof",
    "ideal_body",
    "oracle_needed_premise_ids",
    "proof_body",
    "provider_output_body",
    "test_answer",
}

FORBIDDEN_BODY_KEYS = (
    "ground_truth_proof",
    "ideal_body",
    "oracle_needed_premise_ids",
    "proof_body",
    "provider_output_body",
    "test_answer",
)

EXPECTED_NEGATIVE_CASES = {
    "budget_overflow_recipe": ["PROVIDER_CONTEXT_RECIPE_BUDGET_EXCEEDED"],
    "truth_side_section": ["PROVIDER_CONTEXT_TRUTH_SIDE_SECTION_FORBIDDEN"],
    "proof_body_leakage": ["PROVIDER_CONTEXT_PROOF_BODY_FORBIDDEN"],
    "provider_call_authorized": ["PROVIDER_CONTEXT_CALL_AUTHORITY_FORBIDDEN"],
    "deliverable_type_route_mismatch": ["PROVIDER_CONTEXT_DELIVERABLE_ROUTE_MISMATCH"],
    "omitted_sections_suppressed": ["PROVIDER_CONTEXT_OMITTED_SECTIONS_REQUIRED"],
}

INPUT_NAMES = (
    "provider_context_recipes.json",
    "section_materials.json",
)

NEGATIVE_INPUT_NAMES = (
    "budget_overflow_recipe.json",
    "truth_side_section.json",
    "proof_body_leakage.json",
    "provider_call_authorized.json",
    "deliverable_type_route_mismatch.json",
    "omitted_sections_suppressed.json",
)

NEGATIVE_INPUT_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "provider_context_budget_metadata_not_provider_or_proof_authority",
    "provider_calls_authorized": False,
    "lean_lake_execution_authorized": False,
    "formal_proof_authority": False,
    "truth_side_material_authorized": False,
    "release_authorized": False,
}

CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "anti_claim",
    "authority_ceiling.authority_ceiling",
    "context_packets",
    "expected_negative_cases",
    "findings",
    "observed_negative_cases",
    "private_state_scan.hits",
    "private_state_scan.scan_scope",
    "provider_context_budget_board",
    "receipt_paths",
    "source_module_ids",
    "source_module_imports",
    "source_refs",
)

ANTI_CLAIM = (
    "Provider context recipe budgeting validates public metadata for byte "
    "ceilings, section fill order, omitted-section manifests, graph roles, and "
    "deliverable routing. It does not call providers, expose proof bodies or "
    "oracle material, run Lean/Lake, prove theorem correctness, or authorize "
    "release."
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


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return {Path(name).stem: read_json_strict(input_dir / name) for name in names}


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    source_manifest = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if source_manifest.is_file():
        paths.append(source_manifest)
        for target_ref in _source_module_target_refs(input_dir):
            paths.append(input_dir / target_ref)
    return paths


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _line_count(path: Path) -> int:
    line_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_count, _line in enumerate(handle, start=1):
            pass
    return line_count or 1


def _source_module_target_refs(input_dir: Path) -> list[str]:
    manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    if not manifest_path.is_file():
        return []
    manifest = read_json_strict(manifest_path)
    refs: list[str] = []
    for row in _rows(manifest, "modules"):
        target_ref = row.get("target_ref")
        if isinstance(target_ref, str) and target_ref.startswith("source_modules/"):
            refs.append(target_ref)
    return refs


def _source_module_findings(input_dir: Path) -> dict[str, Any]:
    manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    findings: list[dict[str, Any]] = []
    imports: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        return {
            "status": "blocked",
            "source_module_manifest_ref": SOURCE_MODULE_MANIFEST_NAME,
            "source_module_count": 0,
            "source_module_ids": [],
            "source_module_imports": [],
            "source_module_error_codes": [
                "PROVIDER_CONTEXT_SOURCE_MODULE_MANIFEST_MISSING"
            ],
            "source_module_findings": [
                _finding(
                    "PROVIDER_CONTEXT_SOURCE_MODULE_MANIFEST_MISSING",
                    "Provider context source module imports require a manifest.",
                    case_id="source_module_floor",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
                    subject_kind="source_module_manifest",
                )
            ],
        }

    manifest = read_json_strict(manifest_path)
    module_rows = _rows(manifest, "modules")
    by_id = {str(row.get("module_id") or ""): row for row in module_rows}
    expected_ids = sorted(EXPECTED_SOURCE_MODULES)
    missing_ids = sorted(set(expected_ids) - set(by_id))
    unexpected_ids = sorted(set(by_id) - set(expected_ids) - {""})
    for module_id in missing_ids:
        findings.append(
            _finding(
                "PROVIDER_CONTEXT_SOURCE_MODULE_MISSING",
                "Expected provider context source module is absent from the manifest.",
                case_id="source_module_floor",
                subject_id=module_id,
                subject_kind="source_module",
            )
        )
    for module_id in unexpected_ids:
        findings.append(
            _finding(
                "PROVIDER_CONTEXT_SOURCE_MODULE_UNEXPECTED",
                "Provider context source module manifest contains an unexpected module id.",
                case_id="source_module_floor",
                subject_id=module_id,
                subject_kind="source_module",
            )
        )

    for module_id in expected_ids:
        expected = EXPECTED_SOURCE_MODULES[module_id]
        row = by_id.get(module_id, {})
        target_ref = str(row.get("target_ref") or expected["target_ref"])
        target = input_dir / target_ref
        anchor_results: list[dict[str, Any]] = []
        target_sha256 = None
        line_count = 0
        if not target.is_file():
            findings.append(
                _finding(
                    "PROVIDER_CONTEXT_SOURCE_MODULE_TARGET_MISSING",
                    "Copied provider context source module target file is missing.",
                    case_id="source_module_floor",
                    subject_id=target_ref,
                    subject_kind="source_module",
                )
            )
        else:
            target_text = target.read_text(encoding="utf-8")
            target_sha256 = _sha256(target)
            line_count = _line_count(target)
            if row.get("target_sha256") != target_sha256:
                findings.append(
                    _finding(
                        "PROVIDER_CONTEXT_SOURCE_MODULE_DIGEST_MISMATCH",
                        "Source module manifest digest must match the copied target file.",
                        case_id="source_module_floor",
                        subject_id=module_id,
                        subject_kind="source_module",
                    )
                )
            if row.get("source_sha256") != row.get("target_sha256"):
                findings.append(
                    _finding(
                        "PROVIDER_CONTEXT_SOURCE_MODULE_SOURCE_TARGET_MISMATCH",
                        "Source and target module digests must match for exact macro body imports.",
                        case_id="source_module_floor",
                        subject_id=module_id,
                        subject_kind="source_module",
                    )
                )
            for anchor in expected["required_anchors"]:
                present = anchor in target_text
                anchor_results.append(
                    {
                        "anchor": anchor,
                        "present": present,
                        "body_redacted": True,
                    }
                )
                if not present:
                    findings.append(
                        _finding(
                            "PROVIDER_CONTEXT_SOURCE_MODULE_ANCHOR_MISSING",
                            "Copied source module is missing a required provider-context anchor.",
                            case_id="source_module_floor",
                            subject_id=module_id,
                            subject_kind="source_module",
                        )
                    )

        imports.append(
            {
                "module_id": module_id,
                "source_ref": row.get("source_ref") or expected["source_ref"],
                "target_ref": target_ref,
                "source_sha256": row.get("source_sha256"),
                "target_sha256": target_sha256,
                "sha256_match": bool(target_sha256 and row.get("source_sha256") == target_sha256),
                "line_count": line_count,
                "required_anchor_count": len(expected["required_anchors"]),
                "present_anchor_count": sum(1 for item in anchor_results if item["present"]),
                "anchor_results": anchor_results,
                "body_copied": True,
                "body_in_receipt": False,
            }
        )

    error_codes = sorted({finding["error_code"] for finding in findings})
    return {
        "status": PASS if not findings else "blocked",
        "source_module_manifest_ref": SOURCE_MODULE_MANIFEST_NAME,
        "source_module_count": len(imports),
        "source_module_ids": [row["module_id"] for row in imports],
        "source_module_imports": imports,
        "source_module_error_codes": error_codes,
        "source_module_findings": findings,
    }


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _byte_size(row: dict[str, Any]) -> int:
    declared = row.get("declared_byte_size")
    if isinstance(declared, int) and declared >= 0:
        return declared
    text = row.get("text")
    if isinstance(text, str):
        return len(text.encode("utf-8"))
    return 0


def _forbidden_body_keys(row: dict[str, Any]) -> list[str]:
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


def _recipe_projection(
    recipe: dict[str, Any],
    *,
    sections_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    recipe_id = str(recipe.get("recipe_id") or "")
    budget = int(recipe.get("byte_budget") or 0)
    included: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    total = 0
    for section_id in _strings(recipe.get("sections")):
        section = sections_by_id.get(section_id, {"section_id": section_id})
        size = _byte_size(section)
        target = included if total + size <= budget else omitted
        if target is included:
            total += size
        target.append(
            {
                "section_id": section_id,
                "declared_byte_size": size,
                "body_redacted": True,
            }
        )
    return {
        "recipe_id": recipe_id,
        "byte_budget": budget,
        "kib_budget": budget // 1024 if budget else 0,
        "graph_role": recipe.get("graph_role"),
        "deliverable_type": recipe.get("deliverable_type"),
        "included_sections": included,
        "omitted_sections": omitted,
        "included_section_ids": [row["section_id"] for row in included],
        "omitted_section_ids": [row["section_id"] for row in omitted],
        "included_byte_count": total,
        "approximate_tokens": math.ceil(total / 4) if total else 0,
        "omitted_sections_manifest_emitted": bool(recipe.get("emit_omitted_sections_manifest", True)),
        "provider_calls_authorized": recipe.get("provider_calls_authorized") is True,
        "proof_bodies_allowed": recipe.get("proof_bodies_allowed") is True,
        "body_redacted": True,
    }


def _recipe_findings(
    recipes: list[dict[str, Any]],
    *,
    case_id: str,
    sections_by_id: dict[str, dict[str, Any]],
    observed: dict[str, set[str]] | None = None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    local_observed: dict[str, set[str]] = observed if observed is not None else defaultdict(set)
    for recipe in recipes:
        recipe_id = str(recipe.get("recipe_id") or "recipe")
        budget = int(recipe.get("byte_budget") or 0)
        expected_budget = EXPECTED_RECIPE_BUDGETS.get(recipe_id)
        if budget > 65536 or (expected_budget is not None and budget != expected_budget):
            _record(
                findings,
                local_observed,
                "PROVIDER_CONTEXT_RECIPE_BUDGET_EXCEEDED",
                "Recipe byte budget must match the public bounded recipe contract.",
                case_id=case_id,
                subject_id=recipe_id,
                subject_kind="provider_context_recipe",
            )
        forbidden_sections = sorted(set(_strings(recipe.get("sections"))) & FORBIDDEN_SECTION_IDS)
        if forbidden_sections:
            _record(
                findings,
                local_observed,
                "PROVIDER_CONTEXT_TRUTH_SIDE_SECTION_FORBIDDEN",
                "Provider context recipe attempted to include truth-side or oracle-only sections.",
                case_id=case_id,
                subject_id=",".join(forbidden_sections),
                subject_kind="section_id",
            )
        if recipe.get("proof_bodies_allowed") is True or _forbidden_body_keys(recipe):
            _record(
                findings,
                local_observed,
                "PROVIDER_CONTEXT_PROOF_BODY_FORBIDDEN",
                "Provider context recipe allowed or embedded proof body material.",
                case_id=case_id,
                subject_id=recipe_id,
                subject_kind="provider_context_recipe",
            )
        if recipe.get("provider_calls_authorized") is True:
            _record(
                findings,
                local_observed,
                "PROVIDER_CONTEXT_CALL_AUTHORITY_FORBIDDEN",
                "Public recipe fixtures may describe context shape but cannot authorize provider calls.",
                case_id=case_id,
                subject_id=recipe_id,
                subject_kind="provider_context_recipe",
            )
        expected_deliverable = EXPECTED_DELIVERABLES.get(recipe_id)
        if expected_deliverable and recipe.get("deliverable_type") != expected_deliverable:
            _record(
                findings,
                local_observed,
                "PROVIDER_CONTEXT_DELIVERABLE_ROUTE_MISMATCH",
                "Recipe deliverable type must match the reducer route contract.",
                case_id=case_id,
                subject_id=recipe_id,
                subject_kind="deliverable_type",
            )
        projection = _recipe_projection(recipe, sections_by_id=sections_by_id)
        if projection["omitted_section_ids"] and not projection["omitted_sections_manifest_emitted"]:
            _record(
                findings,
                local_observed,
                "PROVIDER_CONTEXT_OMITTED_SECTIONS_REQUIRED",
                "Over-budget sections require an omitted_sections manifest.",
                case_id=case_id,
                subject_id=recipe_id,
                subject_kind="omitted_sections_manifest",
            )
    return findings


def _section_findings(
    sections: list[dict[str, Any]],
    *,
    case_id: str,
    observed: dict[str, set[str]] | None = None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    local_observed: dict[str, set[str]] = observed if observed is not None else defaultdict(set)
    for section in sections:
        section_id = str(section.get("section_id") or "section")
        if section_id in FORBIDDEN_SECTION_IDS:
            _record(
                findings,
                local_observed,
                "PROVIDER_CONTEXT_TRUTH_SIDE_SECTION_FORBIDDEN",
                "Section material is truth-side or oracle-only and cannot enter provider context.",
                case_id=case_id,
                subject_id=section_id,
                subject_kind="section_id",
            )
        if _forbidden_body_keys(section):
            _record(
                findings,
                local_observed,
                "PROVIDER_CONTEXT_PROOF_BODY_FORBIDDEN",
                "Section material carried forbidden proof, oracle, or provider body fields.",
                case_id=case_id,
                subject_id=section_id,
                subject_kind="section_material",
            )
    return findings


def _negative_findings(payloads: dict[str, Any], sections_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for stem in NEGATIVE_INPUT_STEMS:
        payload = payloads.get(stem)
        if not isinstance(payload, dict):
            continue
        case_id = str(payload.get("expected_negative_case_id") or stem)
        recipes = _rows(payload, "recipes")
        sections = _rows(payload, "sections")
        findings.extend(
            _recipe_findings(
                recipes,
                case_id=case_id,
                sections_by_id=sections_by_id,
                observed=observed,
            )
        )
        findings.extend(
            _section_findings(sections, case_id=case_id, observed=observed)
        )
    return {
        "findings": findings,
        "observed_negative_cases": {
            key: sorted(value) for key, value in observed.items()
        },
    }


def _build_board(*, result: dict[str, Any], private_scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "provider_context_budget_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "selected_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "public_contract": {
            "context_is_budget_not_dump": True,
            "byte_budget_enforced": True,
            "ordered_section_fill": True,
            "omitted_sections_manifest_required": True,
            "truth_side_material_excluded": True,
            "provider_calls_not_authorized": True,
            "body_redacted": True,
        },
        "recipe_projection": {
            "recipe_count": result["recipe_count"],
            "recipe_ids": result["recipe_ids"],
            "context_packets": result["context_packets"],
            "deliverable_routes": result["deliverable_routes"],
            "body_redacted": True,
        },
        "source_module_import": {
            "status": result["source_module_import_status"],
            "source_module_manifest_ref": result["source_module_manifest_ref"],
            "source_module_count": result["source_module_count"],
            "source_module_ids": result["source_module_ids"],
            "source_module_imports": result["source_module_imports"],
            "body_in_receipt": False,
        },
        "private_state_scan": private_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_redacted": True,
    }


def _private_scan_card(scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": scan.get("status"),
        "hit_count": scan.get("hit_count", 0),
        "blocking_hit_count": scan.get("blocking_hit_count", 0),
        "scanned_path_count": scan.get("scanned_path_count", 0),
        "hits_exported": False,
        "scan_scope_exported": False,
        "body_redacted": bool(scan.get("body_redacted")),
        "redacted_output_field_labels_omitted": bool(
            scan.get("redacted_output_field_labels_omitted")
        ),
    }


def _context_packet_card(context_packets: list[dict[str, Any]]) -> dict[str, Any]:
    budgets = [
        int(packet.get("byte_budget") or 0)
        for packet in context_packets
        if isinstance(packet.get("byte_budget"), int)
    ]
    included_bytes = [
        int(packet.get("included_byte_count") or 0)
        for packet in context_packets
        if isinstance(packet.get("included_byte_count"), int)
    ]
    omitted_counts = [
        len(packet.get("omitted_section_ids") or [])
        for packet in context_packets
        if isinstance(packet.get("omitted_section_ids"), list)
    ]
    return {
        "context_packet_count": len(context_packets),
        "min_budget_bytes": min(budgets) if budgets else 0,
        "max_budget_bytes": max(budgets) if budgets else 0,
        "max_included_byte_count": max(included_bytes) if included_bytes else 0,
        "max_omitted_section_count": max(omitted_counts) if omitted_counts else 0,
        "context_packets_exported": False,
    }


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    context_packets = [
        packet
        for packet in result.get("context_packets", [])
        if isinstance(packet, dict)
    ]
    expected_negative_cases = result.get("expected_negative_cases", {})
    observed_negative_cases = result.get("observed_negative_cases", {})
    if not isinstance(expected_negative_cases, dict):
        expected_negative_cases = {}
    if not isinstance(observed_negative_cases, dict):
        observed_negative_cases = {}
    receipt_paths = result.get("receipt_paths", [])
    if not isinstance(receipt_paths, list):
        receipt_paths = []
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "card_id": "provider_context_recipe_budget_policy.command_card",
        "output_profile": "compact_command_card",
        "full_output_available": True,
        "full_output_drilldown": "rerun without --card or inspect written receipts",
        "provider_context_summary": {
            "recipe_count": result.get("recipe_count", 0),
            "recipe_ids": result.get("recipe_ids", []),
            "deliverable_route_count": len(result.get("deliverable_routes", {})),
            "source_module_import_status": result.get("source_module_import_status"),
            "source_module_count": result.get("source_module_count", 0),
            "source_module_ids_exported": False,
            **_context_packet_card(context_packets),
        },
        "negative_case_coverage": {
            "expected_case_count": len(expected_negative_cases),
            "observed_case_count": len(observed_negative_cases),
            "missing_negative_cases": result.get("missing_negative_cases", []),
            "error_code_count": len(result.get("error_codes", [])),
            "observed_negative_cases_exported": False,
        },
        "private_state_scan_summary": _private_scan_card(
            result.get("private_state_scan", {})
        ),
        "authority_ceiling": {
            "provider_calls_authorized": result["authority_ceiling"][
                "provider_calls_authorized"
            ],
            "lean_lake_execution_authorized": result["authority_ceiling"][
                "lean_lake_execution_authorized"
            ],
            "formal_proof_authority": result["authority_ceiling"][
                "formal_proof_authority"
            ],
            "truth_side_material_authorized": result["authority_ceiling"][
                "truth_side_material_authorized"
            ],
            "release_authorized": result["authority_ceiling"]["release_authorized"],
        },
        "receipt_summary": {
            "receipt_count": len(receipt_paths),
            "full_receipts_written": bool(receipt_paths),
            "receipt_paths_exported": False,
        },
        "no_export_guards": {
            "anti_claim_exported": False,
            "context_packets_exported": False,
            "expected_negative_cases_exported": False,
            "findings_exported": False,
            "observed_negative_cases_exported": False,
            "private_scan_hits_exported": False,
            "private_scan_scope_exported": False,
            "provider_payloads_exported": False,
            "proof_bodies_exported": False,
            "receipt_paths_exported": False,
            "section_materials_exported": False,
            "source_module_ids_exported": False,
            "source_module_imports_exported": False,
            "source_refs_exported": False,
        },
        "output_economy": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
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
        "source_pattern_ids",
        "source_refs",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "source_module_import_status",
        "source_module_manifest_ref",
        "source_module_count",
        "source_module_ids",
        "source_module_imports",
        "source_module_error_codes",
        "private_state_scan",
        "authority_ceiling",
        "anti_claim",
        "recipe_count",
        "recipe_ids",
        "deliverable_routes",
        "context_packets",
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

    recipe_rows = _rows(payloads["provider_context_recipes"], "recipes")
    section_rows = _rows(payloads["section_materials"], "sections")
    sections_by_id = {str(row.get("section_id") or ""): row for row in section_rows}
    context_packets = [
        _recipe_projection(recipe, sections_by_id=sections_by_id)
        for recipe in recipe_rows
    ]
    floor_findings = [
        *_recipe_findings(recipe_rows, case_id="recipe_floor", sections_by_id=sections_by_id),
        *_section_findings(section_rows, case_id="section_material_floor"),
    ]
    negative = (
        _negative_findings(payloads, sections_by_id)
        if include_negative
        else {"findings": [], "observed_negative_cases": {}}
    )
    source_modules = _source_module_findings(input_dir)
    observed = negative["observed_negative_cases"]
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = [
        *floor_findings,
        *negative["findings"],
        *source_modules["source_module_findings"],
    ]
    error_codes = sorted({finding["error_code"] for finding in findings})
    recipe_ids = sorted(str(row.get("recipe_id") or "") for row in recipe_rows)
    all_expectations_met = recipe_ids == sorted(EXPECTED_RECIPE_BUDGETS)
    status = (
        PASS
        if not missing
        and not floor_findings
        and source_modules["status"] == PASS
        and all_expectations_met
        and not private_scan["blocking_hit_count"]
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
        "schema_version": "provider_context_budget_result_v1",
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
        "source_module_import_status": source_modules["status"],
        "source_module_manifest_ref": source_modules["source_module_manifest_ref"],
        "source_module_count": source_modules["source_module_count"],
        "source_module_ids": source_modules["source_module_ids"],
        "source_module_imports": source_modules["source_module_imports"],
        "source_module_error_codes": source_modules["source_module_error_codes"],
        "private_state_scan": private_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "recipe_count": len(recipe_rows),
        "recipe_ids": recipe_ids,
        "deliverable_routes": {
            packet["recipe_id"]: packet["deliverable_type"] for packet in context_packets
        },
        "context_packets": context_packets,
        "all_expectations_met": all_expectations_met,
        "body_redacted": True,
    }
    result["provider_context_budget_board"] = _build_board(
        result=result,
        private_scan=private_scan,
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
            schema_version="exported_provider_context_budget_bundle_validation_result_v1",
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
    result_payload.pop("provider_context_budget_board", None)
    result_payload["receipt_paths"] = receipt_paths
    board_payload = result["provider_context_budget_board"]
    board_payload["receipt_paths"] = receipt_paths
    validation_payload = _common_receipt(
        result,
        schema_version="provider_context_budget_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    acceptance_payload = _common_receipt(
        result,
        schema_version="provider_context_budget_fixture_acceptance_v1",
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
    command: str | None = None,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    command = command or (
        "python -m microcosm_core.organs.provider_context_recipe_budget_policy "
        f"run --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture_input",
        include_negative=True,
    )
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out else None,
        bundle_mode=False,
    )


def run_budget_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    command = command or (
        "python -m microcosm_core.organs.provider_context_recipe_budget_policy "
        f"run-budget-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_provider_context_budget_bundle",
        include_negative=False,
    )
    return _write_receipts(result, Path(out_dir), acceptance_out=None, bundle_mode=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate public provider context recipe budgets")
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-budget-bundle"):
        sub = subparsers.add_parser(action)
        sub.add_argument("--input", required=True)
        sub.add_argument("--out", required=True)
        sub.add_argument(
            "--card",
            action="store_true",
            help="print a compact command card while still writing full receipts",
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        result = run(
            args.input,
            args.out,
            command=(
                "python -m microcosm_core.organs.provider_context_recipe_budget_policy "
                f"run --input {args.input} --out {args.out}{card_suffix}"
            ),
        )
    elif args.action == "run-budget-bundle":
        result = run_budget_bundle(
            args.input,
            args.out,
            command=(
                "python -m microcosm_core.organs.provider_context_recipe_budget_policy "
                f"run-budget-bundle --input {args.input} --out {args.out}{card_suffix}"
            ),
        )
    else:  # pragma: no cover
        raise AssertionError(args.action)
    output = result_card(result) if args.card else result
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
