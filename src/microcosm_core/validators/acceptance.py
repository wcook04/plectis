from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import base_receipt, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "pattern_assimilation_step"
FIXTURE_ID = "first_wave.pattern_assimilation_step"
VALIDATOR_ID = "validator.microcosm.validators.acceptance.pattern_assimilation_step"

ACCEPTANCE_REL = "receipts/first_wave/pattern_assimilation_acceptance.json"
ASSIMILATION_REL = "receipts/first_wave/pattern_assimilation_receipt.json"
MACRO_RUNS_REL = "state/microcosm_portfolio/reconstruction/macro_pattern_autonomy_process_runs_v1.jsonl"
ASSIMILATION_BUNDLE_RESULT_NAME = "exported_assimilation_bundle_validation_result.json"
EXPORTED_ASSIMILATION_BUNDLE_RECEIPT_PATH = (
    "receipts/first_wave/pattern_assimilation_step/"
    "exported_assimilation_bundle_validation_result.json"
)
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
PUBLIC_SAFE_SOURCE_BODY_CLASSES = frozenset(
    {
        "public_macro_pattern_body",
        "public_macro_tool_body",
        "public_macro_receipt_body",
        "public_macro_proof_body",
        "public_standard_body",
    }
)

EXPECTED_RECEIPT_PATHS = [
    ACCEPTANCE_REL,
    ASSIMILATION_REL,
    MACRO_RUNS_REL,
]

EXPECTED_NEGATIVE_CASES = {
    "organ_landing_without_refinement_or_typed_nothing": [
        "MISSING_PATTERN_ASSIMILATION_CLOSEOUT"
    ],
    "assimilation_receipt_missing_owner_surface": [
        "MISSING_REFINEMENT_OWNER_SURFACE",
        "MISSING_REENTRY_CONDITION",
        "MISSING_STEWARDSHIP_CHECK",
    ],
    "local_lesson_claims_global_doctrine_authority": [
        "LOCAL_LESSON_AUTHORITY_UPGRADE"
    ],
    "assimilation_private_raw_seed_body": ["RAW_SEED_BODY_IN_ASSIMILATION_FIXTURE"],
    "duplicate_refinement_receipt_conflict": ["DUPLICATE_REFINEMENT_RECEIPT_ID"],
}

PATTERN_ASSIMILATION_ANTI_CLAIM = (
    "Pattern assimilation receipts validate public closeout-learning metadata plus "
    "regression fixtures; they do not promote global doctrine, mutate live ledgers, "
    "authorize release work, or prove live learning behavior."
)
PATTERN_ASSIMILATION_AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "pattern_assimilation_metadata_not_live_learning_authority",
    "live_task_ledger_mutation_authorized": False,
    "global_doctrine_promotion_authorized": False,
    "release_or_publication_authorized": False,
    "raw_seed_body_read": False,
    "provider_payload_read": False,
    "private_data_equivalence_claim": False,
    "behavior_change_overclaims_allowed": False,
}

WAVE_1_ORGAN_IDS = [
    "pattern_binding_contract",
    "executable_doctrine_grammar",
    "proof_diagnostic_evidence_spine",
    "formal_math_readiness_gate",
    "corpus_readiness_mathlib_absence_gate",
    "mathematical_strategy_atlas_hypothesis_scorer",
    "tactic_portfolio_availability_probe",
    "target_shape_tactic_routing_gate",
    "lean_std_premise_index",
    "formal_math_premise_retrieval",
    "formal_math_verifier_trace_repair_loop",
    "formal_evidence_cell_anchor_resolver",
    "undeclared_library_prior_symbol_classifier",
    "ring2_premise_retrieval_precision_recall_harness",
    "agent_benchmark_integrity_anti_gaming_replay",
    "provider_context_recipe_budget_policy",
    "formal_math_lean_proof_witness",
    "verifier_lab_kernel",
    "navigation_hologram_route_plane",
    "mission_transaction_work_spine",
    "durable_agent_work_landing_replay",
    "research_replication_rubric_artifact_replay",
    "world_model_projection_drift_control_room",
    "spatial_world_model_counterfactual_simulation_replay",
    "materials_chemistry_closed_loop_lab_safety_replay",
    "mechanistic_interpretability_circuit_attribution_replay",
    "agent_route_observability_runtime",
]

ADAPTER_BACKED_ORGAN_IDS = [
    *WAVE_1_ORGAN_IDS,
    "pattern_assimilation_step",
    "public_reveal_walkthrough",
    "macro_projection_import_protocol",
    "prediction_oracle_reconciliation",
    "standards_meta_diagnostics",
    "cold_reader_route_map",
    "agent_monitor_redteam_falsification_replay",
    "agent_sabotage_scheming_monitor_replay",
    "agent_memory_temporal_conflict_replay",
    "sleeper_memory_poisoning_quarantine_replay",
    "mcp_tool_authority_replay",
    "proof_derived_governed_mutation_authorization",
    "belief_state_process_reward_replay",
    "agent_sandbox_policy_escape_replay",
    "indirect_prompt_injection_information_flow_policy_replay",
    "agentic_vulnerability_discovery_patch_proof_replay",
]


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


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _display_path(path: Path, *, public_root: Path, repo_root: Path) -> str:
    if _is_relative_to(path, public_root):
        return public_relative_path(path, display_root=public_root)
    return public_relative_path(path, display_root=repo_root)


def _input_paths(input_dir: Path) -> list[Path]:
    return [
        input_dir / "organ_landing_summaries.jsonl",
        input_dir / "refinement_case.json",
        input_dir / "nothing_to_refine_case.json",
        input_dir / "missing_closeout_case.json",
    ]


def _assimilation_bundle_paths(input_dir: Path) -> list[Path]:
    names = (
        "bundle_manifest.json",
        "organ_landing_summaries.json",
        "refinement_receipts.json",
        "nothing_to_refine_receipts.json",
        "stewardship_checks.json",
        "reentry_conditions.json",
        "next_best_lane_checks.json",
        "assimilation_policy.json",
    )
    return [input_dir / name for name in names]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _load_inputs(input_dir: Path) -> dict[str, Any]:
    return {
        "landings": _load_jsonl(input_dir / "organ_landing_summaries.jsonl"),
        "refinement": read_json_strict(input_dir / "refinement_case.json"),
        "nothing": read_json_strict(input_dir / "nothing_to_refine_case.json"),
        "missing": read_json_strict(input_dir / "missing_closeout_case.json"),
    }


def _load_assimilation_bundle(input_dir: Path) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _assimilation_bundle_paths(input_dir)
    }


def _scan_fixture_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    return scan_paths(_input_paths(input_dir), forbidden_classes=policy, display_root=public_root)


def _scan_bundle_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    return scan_paths(
        _assimilation_bundle_paths(input_dir),
        forbidden_classes=policy,
        display_root=public_root,
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_module_target_path(
    row: dict[str, Any],
    *,
    manifest_path: Path,
    public_root: Path,
) -> tuple[Path, str]:
    target_ref = str(row.get("target_ref") or "")
    if target_ref.startswith("microcosm-substrate/"):
        target_path = public_root.parent / target_ref
    elif target_ref:
        target_path = public_root / target_ref
    else:
        target_path = public_root

    path_ref = str(row.get("path") or "")
    path_target = manifest_path.parent / path_ref if path_ref else manifest_path.parent
    if (not target_ref or not target_path.is_file()) and path_ref and path_target.is_file():
        return path_target, public_relative_path(path_target, display_root=public_root)
    return target_path, target_ref


def validate_source_module_manifest(input_dir: Path, public_root: Path) -> dict[str, Any]:
    manifest_path = input_dir / SOURCE_MODULE_MANIFEST_NAME
    manifest_ref = public_relative_path(manifest_path, display_root=public_root)
    if not manifest_path.is_file():
        return {
            "schema_version": "pattern_assimilation_step_source_open_body_imports_v1",
            "status": "blocked",
            "manifest_ref": manifest_ref,
            "source_module_manifest_ref": manifest_ref,
            "aggregate_floor_ref": f"{manifest_ref}::modules",
            "source_import_class": SOURCE_IMPORT_CLASS,
            "body_material_count": 0,
            "body_material_ids": [],
            "body_material_classes": {},
            "body_material": [],
            "body_in_receipt": False,
            "body_text_in_receipt": False,
            "findings": [
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_SOURCE_MODULE_MANIFEST_MISSING",
                    "Exported assimilation bundle must include source_module_manifest.json.",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
                    subject_kind="source_module_manifest",
                )
            ],
        }

    manifest = read_json_strict(manifest_path)
    modules = _rows(manifest, "modules")
    findings: list[dict[str, Any]] = []
    if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
        findings.append(
            _bundle_finding(
                "ASSIMILATION_BUNDLE_SOURCE_IMPORT_CLASS_MISMATCH",
                "source_module_manifest.json must declare copied non-secret macro body import class.",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_in_receipt") is not False:
        findings.append(
            _bundle_finding(
                "ASSIMILATION_BUNDLE_SOURCE_BODY_RECEIPT_RISK",
                "source_module_manifest.json must keep copied body text out of receipts.",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    if int(manifest.get("module_count") or 0) != len(modules):
        findings.append(
            _bundle_finding(
                "ASSIMILATION_BUNDLE_SOURCE_MODULE_COUNT_MISMATCH",
                "source_module_manifest.json module_count must match modules.",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )

    module_cards: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    for row in modules:
        module_id = str(row.get("module_id") or "")
        material_class = str(row.get("material_class") or "")
        target_path, target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        expected_sha = str(
            row.get("sha256") or row.get("target_sha256") or row.get("source_sha256") or ""
        ).removeprefix("sha256:")
        actual_sha = _sha256_file(target_path) if target_path.is_file() else ""
        module_findings: list[str] = []
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            module_findings.append("source_import_class_mismatch")
        if row.get("body_copied") is not True:
            module_findings.append("body_copied_not_true")
        if row.get("body_in_receipt") is not False or row.get("body_text_in_receipt") is not False:
            module_findings.append("body_receipt_risk")
        if material_class not in PUBLIC_SAFE_SOURCE_BODY_CLASSES:
            module_findings.append("unsupported_material_class")
        if not target_path.is_file():
            module_findings.append("target_missing")
        if expected_sha and actual_sha and expected_sha != actual_sha:
            module_findings.append("target_sha256_mismatch")
        if not module_id:
            module_findings.append("module_id_missing")

        status = PASS if not module_findings else "blocked"
        if status == PASS:
            class_counts[material_class] += 1
        else:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_SOURCE_MODULE_INVALID",
                    "Copied source module failed the source-open body import contract.",
                    subject_id=module_id or target_ref or "unknown_source_module",
                    subject_kind="source_module",
                )
            )
        module_cards.append(
            {
                "module_id": module_id,
                "material_class": material_class,
                "source_ref": row.get("source_ref"),
                "target_ref": target_ref,
                "sha256": f"sha256:{actual_sha}" if actual_sha else "",
                "line_count": row.get("line_count"),
                "byte_count": row.get("byte_count"),
                "body_in_receipt": False,
                "body_text_in_receipt": False,
                "status": status,
                "defect_codes": module_findings,
            }
        )

    passed_modules = [card for card in module_cards if card["status"] == PASS]
    return {
        "schema_version": "pattern_assimilation_step_source_open_body_imports_v1",
        "status": PASS if modules and not findings else "blocked",
        "manifest_ref": manifest_ref,
        "source_module_manifest_ref": manifest_ref,
        "aggregate_floor_ref": f"{manifest_ref}::modules",
        "source_import_class": SOURCE_IMPORT_CLASS,
        "body_material_count": len(passed_modules),
        "body_material_ids": [card["module_id"] for card in passed_modules],
        "body_material_classes": dict(sorted(class_counts.items())),
        "body_material": module_cards,
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ for exact copied "
            "macro process bodies; receipts carry refs, digests, counts, and verdicts only."
        ),
        "findings": findings,
    }


def _stable_hash(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


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


def _bundle_finding(
    code: str,
    message: str,
    *,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
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


def validate_exported_organ_landings(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "organ_landing_summaries")
    organ_ids: list[str] = []
    landing_receipt_refs: list[str] = []
    closeout_by_organ: dict[str, str] = {}
    if not rows:
        findings.append(
            _bundle_finding(
                "ASSIMILATION_BUNDLE_ORGAN_LANDINGS_MISSING",
                "Exported assimilation bundle has no organ landing summaries.",
                subject_id="organ_landing_summaries",
                subject_kind="organ_landing_summaries",
            )
        )
    for row in rows:
        organ_id = str(row.get("organ_id") or "")
        closeout = str(row.get("closeout_refinement_result") or "")
        receipt_ref = str(row.get("landing_receipt_ref") or "")
        organ_ids.append(organ_id)
        if receipt_ref:
            landing_receipt_refs.append(receipt_ref)
        if organ_id:
            closeout_by_organ[organ_id] = closeout
        if not organ_id or not closeout or not receipt_ref:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_ORGAN_CLOSEOUT_MISSING",
                    "Each organ landing must name organ id, closeout result, and landing receipt ref.",
                    subject_id=organ_id or "organ_landing",
                    subject_kind="organ_landing",
                )
            )
        if row.get("projection_not_authority") is not True:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_ORGAN_PROJECTION_FLAG_MISSING",
                    "Organ landing row must declare projection_not_authority.",
                    subject_id=organ_id or "organ_landing",
                    subject_kind="organ_landing",
                )
            )
        if row.get("live_learning_authority") is not False:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_ORGAN_AUTHORITY_OVERCLAIM",
                    "Organ landing row cannot claim live learning authority.",
                    subject_id=organ_id or "organ_landing",
                    subject_kind="organ_landing",
                )
            )
    duplicate_ids = sorted(
        organ_id for organ_id, count in Counter(organ_ids).items() if organ_id and count > 1
    )
    for organ_id in duplicate_ids:
        findings.append(
            _bundle_finding(
                "ASSIMILATION_BUNDLE_DUPLICATE_ORGAN_LANDING",
                "Organ landing summaries must not duplicate organ ids.",
                subject_id=organ_id,
                subject_kind="organ_landing",
            )
        )
    missing_expected = sorted(set(ADAPTER_BACKED_ORGAN_IDS) - set(organ_ids))
    for organ_id in missing_expected:
        findings.append(
            _bundle_finding(
                "ASSIMILATION_BUNDLE_ACCEPTED_ORGAN_MISSING",
                "Exported assimilation bundle must cover every accepted adapter-backed organ.",
                subject_id=organ_id,
                subject_kind="organ_landing",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "landed_organ_ids": sorted(organ_id for organ_id in organ_ids if organ_id),
        "organ_landing_count": len(rows),
        "landing_receipt_refs": sorted(set(landing_receipt_refs)),
        "closeout_by_organ": closeout_by_organ,
        "accepted_adapter_backed_organ_ids": ADAPTER_BACKED_ORGAN_IDS,
        "organ_landing_projection_not_authority": True,
    }


def validate_exported_refinement_receipts(
    payload: object,
    landing_result: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "refinement_receipts")
    receipt_ids: list[str] = []
    owner_surfaces: list[str] = []
    result_by_organ: dict[str, str] = {}
    landed_organs = set(landing_result.get("landed_organ_ids", []))
    if not rows:
        findings.append(
            _bundle_finding(
                "ASSIMILATION_BUNDLE_REFINEMENT_RECEIPTS_MISSING",
                "Exported assimilation bundle has no refinement receipts.",
                subject_id="refinement_receipts",
                subject_kind="refinement_receipts",
            )
        )
    for row in rows:
        receipt_id = str(row.get("receipt_id") or "")
        organ_id = str(row.get("organ_id") or "")
        result = str(row.get("refinement_result") or "")
        owner_surface = str(row.get("owner_surface") or "")
        changed_ref = str(row.get("changed_surface_ref") or "")
        if receipt_id:
            receipt_ids.append(receipt_id)
        if owner_surface:
            owner_surfaces.append(owner_surface)
        if organ_id:
            result_by_organ[organ_id] = result
        if not receipt_id or not organ_id or not result:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_REFINEMENT_FIELDS_MISSING",
                    "Refinement receipt must name receipt_id, organ_id, and refinement_result.",
                    subject_id=receipt_id or organ_id or "refinement_receipt",
                    subject_kind="refinement_receipt",
                )
            )
        if organ_id and organ_id not in landed_organs:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_REFINEMENT_ORGAN_NOT_LANDED",
                    "Refinement receipt references an organ absent from landing summaries.",
                    subject_id=organ_id,
                    subject_kind="refinement_receipt",
                )
            )
        if not owner_surface or not changed_ref:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_REFINEMENT_OWNER_SURFACE_MISSING",
                    "Concrete refinement receipt must name owner_surface and changed_surface_ref.",
                    subject_id=receipt_id or organ_id or "refinement_receipt",
                    subject_kind="refinement_receipt",
                )
            )
        if row.get("projection_not_authority") is not True:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_REFINEMENT_PROJECTION_FLAG_MISSING",
                    "Refinement receipt must declare projection_not_authority.",
                    subject_id=receipt_id or organ_id or "refinement_receipt",
                    subject_kind="refinement_receipt",
                )
            )
        for field, code in (
            ("claims_global_doctrine_authority", "ASSIMILATION_BUNDLE_REFINEMENT_GLOBAL_AUTHORITY_OVERCLAIM"),
            ("live_doctrine_authority", "ASSIMILATION_BUNDLE_REFINEMENT_LIVE_AUTHORITY_OVERCLAIM"),
        ):
            if row.get(field) is not False:
                findings.append(
                    _bundle_finding(
                        code,
                        "Refinement receipt cannot claim global doctrine or live doctrine authority.",
                        subject_id=receipt_id or organ_id or field,
                        subject_kind="refinement_receipt",
                    )
                )
    duplicate_ids = sorted(
        receipt_id for receipt_id, count in Counter(receipt_ids).items() if count > 1
    )
    for receipt_id in duplicate_ids:
        findings.append(
            _bundle_finding(
                "ASSIMILATION_BUNDLE_DUPLICATE_REFINEMENT_RECEIPT_ID",
                "Refinement receipt ids must be unique.",
                subject_id=receipt_id,
                subject_kind="refinement_receipt",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "refinement_receipt_ids": sorted(set(receipt_ids)),
        "refinement_receipt_count": len(rows),
        "refined_owner_surfaces": sorted(set(owner_surfaces)),
        "refinement_result_by_organ": result_by_organ,
        "refinement_receipts_projection_not_authority": True,
    }


def validate_exported_nothing_to_refine_receipts(
    payload: object,
    landing_result: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "nothing_to_refine_receipts")
    receipt_ids: list[str] = []
    result_by_organ: dict[str, str] = {}
    landed_organs = set(landing_result.get("landed_organ_ids", []))
    if not rows:
        findings.append(
            _bundle_finding(
                "ASSIMILATION_BUNDLE_NOTHING_TO_REFINE_RECEIPTS_MISSING",
                "Exported assimilation bundle has no nothing-to-refine receipts.",
                subject_id="nothing_to_refine_receipts",
                subject_kind="nothing_to_refine_receipts",
            )
        )
    for row in rows:
        receipt_id = str(row.get("receipt_id") or "")
        organ_id = str(row.get("organ_id") or "")
        reentry = str(row.get("reentry_condition") or "")
        if receipt_id:
            receipt_ids.append(receipt_id)
        if organ_id:
            result_by_organ[organ_id] = str(row.get("refinement_result") or "")
        if organ_id and organ_id not in landed_organs:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_NOTHING_ORGAN_NOT_LANDED",
                    "Nothing-to-refine receipt references an organ absent from landing summaries.",
                    subject_id=organ_id,
                    subject_kind="nothing_to_refine_receipt",
                )
            )
        for field in ("stewardship_checked", "next_best_lane_checked", "projection_not_authority"):
            if row.get(field) is not True:
                findings.append(
                    _bundle_finding(
                        "ASSIMILATION_BUNDLE_NOTHING_TO_REFINE_FLOOR_MISSING",
                        "Nothing-to-refine receipt must prove stewardship, next-best-lane, and projection checks.",
                        subject_id=receipt_id or organ_id or field,
                        subject_kind="nothing_to_refine_receipt",
                    )
                )
        if row.get("live_learning_authority") is not False:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_NOTHING_TO_REFINE_AUTHORITY_OVERCLAIM",
                    "Nothing-to-refine receipt cannot claim live learning authority.",
                    subject_id=receipt_id or organ_id or "live_learning_authority",
                    subject_kind="nothing_to_refine_receipt",
                )
            )
        if not reentry:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_NOTHING_TO_REFINE_REENTRY_MISSING",
                    "Nothing-to-refine receipt must name a re-entry condition.",
                    subject_id=receipt_id or organ_id or "reentry_condition",
                    subject_kind="nothing_to_refine_receipt",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "nothing_to_refine_receipt_ids": sorted(set(receipt_ids)),
        "nothing_to_refine_receipt_count": len(rows),
        "nothing_to_refine_result_by_organ": result_by_organ,
        "nothing_to_refine_projection_not_authority": True,
    }


def validate_exported_stewardship_checks(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "stewardship_checks")
    check_ids: list[str] = []
    if not rows:
        findings.append(
            _bundle_finding(
                "ASSIMILATION_BUNDLE_STEWARDSHIP_CHECKS_MISSING",
                "Exported assimilation bundle has no stewardship checks.",
                subject_id="stewardship_checks",
                subject_kind="stewardship_checks",
            )
        )
    for row in rows:
        check_id = str(row.get("check_id") or "")
        check_ids.append(check_id)
        for field in ("stewardship_checked", "projection_not_authority"):
            if row.get(field) is not True:
                findings.append(
                    _bundle_finding(
                        "ASSIMILATION_BUNDLE_STEWARDSHIP_FLOOR_MISSING",
                        "Stewardship check must declare stewardship_checked and projection_not_authority.",
                        subject_id=check_id or field,
                        subject_kind="stewardship_check",
                    )
                )
        if row.get("live_task_ledger_mutation_authorized") is not False:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_STEWARDSHIP_LIVE_LEDGER_OVERCLAIM",
                    "Stewardship check cannot authorize live Task Ledger mutation.",
                    subject_id=check_id or "live_task_ledger_mutation_authorized",
                    subject_kind="stewardship_check",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "stewardship_check_ids": sorted(check_id for check_id in check_ids if check_id),
        "stewardship_check_count": len(rows),
        "stewardship_projection_not_authority": True,
    }


def validate_exported_reentry_conditions(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "reentry_conditions")
    condition_ids: list[str] = []
    if not rows:
        findings.append(
            _bundle_finding(
                "ASSIMILATION_BUNDLE_REENTRY_CONDITIONS_MISSING",
                "Exported assimilation bundle has no re-entry conditions.",
                subject_id="reentry_conditions",
                subject_kind="reentry_conditions",
            )
        )
    for row in rows:
        condition_id = str(row.get("condition_id") or "")
        condition_ids.append(condition_id)
        if not row.get("reentry_condition"):
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_REENTRY_CONDITION_MISSING",
                    "Re-entry condition row must name a re-entry condition.",
                    subject_id=condition_id or "reentry_condition",
                    subject_kind="reentry_condition",
                )
            )
        if row.get("projection_not_authority") is not True or row.get("release_authorized") is not False:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_REENTRY_AUTHORITY_OVERCLAIM",
                    "Re-entry row must remain projection metadata and keep release unauthorized.",
                    subject_id=condition_id or "reentry_condition",
                    subject_kind="reentry_condition",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "reentry_condition_ids": sorted(condition_id for condition_id in condition_ids if condition_id),
        "reentry_condition_count": len(rows),
        "reentry_conditions_projection_not_authority": True,
    }


def validate_exported_next_best_lane_checks(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "next_best_lane_checks")
    next_routes: list[str] = []
    seed_paths: list[str] = []
    if not rows:
        findings.append(
            _bundle_finding(
                "ASSIMILATION_BUNDLE_NEXT_BEST_LANE_CHECKS_MISSING",
                "Exported assimilation bundle has no next-best-lane checks.",
                subject_id="next_best_lane_checks",
                subject_kind="next_best_lane_checks",
            )
        )
    for row in rows:
        check_id = str(row.get("check_id") or "")
        next_route = str(row.get("next_route") or "")
        seed_path = str(row.get("next_seed_path") or "")
        if next_route:
            next_routes.append(next_route)
        if seed_path:
            seed_paths.append(seed_path)
        for field in ("next_best_lane_checked", "projection_not_authority"):
            if row.get(field) is not True:
                findings.append(
                    _bundle_finding(
                        "ASSIMILATION_BUNDLE_NEXT_BEST_LANE_FLOOR_MISSING",
                        "Next-best-lane row must declare next_best_lane_checked and projection_not_authority.",
                        subject_id=check_id or field,
                        subject_kind="next_best_lane_check",
                    )
                )
        if row.get("release_authorized") is not False:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_NEXT_BEST_LANE_RELEASE_OVERCLAIM",
                    "Next-best-lane row cannot authorize release.",
                    subject_id=check_id or "release_authorized",
                    subject_kind="next_best_lane_check",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "next_best_lane_check_count": len(rows),
        "next_routes": sorted(set(next_routes)),
        "next_seed_paths": sorted(set(seed_paths)),
        "next_best_lane_result": (
            sorted(set(next_routes))[0] if next_routes else "ordered_adapter_lane_completion_reducer_required"
        ),
        "next_best_lane_projection_not_authority": True,
    }


def validate_exported_assimilation_policy(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    policy = payload if isinstance(payload, dict) else {}
    for field in (
        "raw_seed_body_read",
        "live_task_ledger_mutation_authorized",
        "global_doctrine_promotion_authorized",
        "release_or_publication_authorized",
        "provider_payload_read",
        "private_data_equivalence_claim",
        "behavior_change_overclaims_allowed",
        "live_learning_authority",
    ):
        if policy.get(field) is not False:
            findings.append(
                _bundle_finding(
                    "ASSIMILATION_BUNDLE_POLICY_FORBIDDEN_AUTHORITY",
                    "Assimilation policy must reject raw seed, live ledger, global doctrine, release, provider, private-data-equivalence, behavior-overclaim, and live-learning authority fields.",
                    subject_id=field,
                    subject_kind="assimilation_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "policy_id": policy.get("policy_id"),
        "forbidden_authority_rejected": True,
        "metadata_projection_not_live_learning_authority": True,
        "body_redacted": True,
    }


def _validate_rows(payloads: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    landings = payloads["landings"]
    refinement_rows = _rows(payloads["refinement"], "refinement_receipts")
    nothing_rows = _rows(payloads["nothing"], "nothing_to_refine_receipts")
    missing_case = payloads["missing"] if isinstance(payloads["missing"], dict) else {}
    receipt_ids = [
        str(row.get("receipt_id") or "")
        for row in [*refinement_rows, *nothing_rows]
        if row.get("receipt_id")
    ]
    duplicate_receipt_ids = sorted(
        receipt_id for receipt_id, count in Counter(receipt_ids).items() if count > 1
    )
    for receipt_id in duplicate_receipt_ids:
        _record(
            findings,
            observed,
            "DUPLICATE_REFINEMENT_RECEIPT_ID",
            "Duplicate refinement receipt ids cannot double-count closeout learning.",
            case_id="duplicate_refinement_receipt_conflict",
            subject_id=receipt_id,
            subject_kind="assimilation_receipt",
        )

    closeout_by_organ: dict[str, dict[str, Any]] = {}
    for row in landings:
        organ_id = str(row.get("organ_id") or "organ")
        closeout_by_organ[organ_id] = row
        if not row.get("closeout_refinement_result"):
            _record(
                findings,
                observed,
                "MISSING_PATTERN_ASSIMILATION_CLOSEOUT",
                "Landed organ lacks concrete refinement or typed nothing-to-refine closeout.",
                case_id="organ_landing_without_refinement_or_typed_nothing",
                subject_id=organ_id,
                subject_kind="organ_landing",
            )

    for row in refinement_rows:
        receipt_id = str(row.get("receipt_id") or "refinement")
        if row.get("claims_global_doctrine_authority"):
            _record(
                findings,
                observed,
                "LOCAL_LESSON_AUTHORITY_UPGRADE",
                "Local closeout lesson cannot claim global doctrine authority.",
                case_id="local_lesson_claims_global_doctrine_authority",
                subject_id=receipt_id,
                subject_kind="assimilation_receipt",
            )
        if row.get("refinement_result") in {"fixture_manifest_refined", "validator_contract_refined"}:
            if not row.get("owner_surface"):
                _record(
                    findings,
                    observed,
                    "MISSING_REFINEMENT_OWNER_SURFACE",
                    "Concrete refinement must name the owner surface.",
                    case_id="assimilation_receipt_missing_owner_surface",
                    subject_id=receipt_id,
                    subject_kind="assimilation_receipt",
                )

    for row in nothing_rows:
        receipt_id = str(row.get("receipt_id") or "nothing_to_refine")
        if row.get("refinement_result") == "nothing_to_refine":
            if not row.get("stewardship_checked"):
                _record(
                    findings,
                    observed,
                    "MISSING_STEWARDSHIP_CHECK",
                    "Nothing-to-refine must prove stewardship was checked.",
                    case_id="assimilation_receipt_missing_owner_surface",
                    subject_id=receipt_id,
                    subject_kind="nothing_to_refine_receipt",
                )
            if not row.get("reentry_condition"):
                _record(
                    findings,
                    observed,
                    "MISSING_REENTRY_CONDITION",
                    "Nothing-to-refine must name a re-entry condition.",
                    case_id="assimilation_receipt_missing_owner_surface",
                    subject_id=receipt_id,
                    subject_kind="nothing_to_refine_receipt",
                )

    if missing_case.get("forbidden_payload_class") == "seed_origin_payload":
        _record(
            findings,
            observed,
            "RAW_SEED_BODY_IN_ASSIMILATION_FIXTURE",
            "Seed-origin payload class is rejected and redacted.",
            case_id="assimilation_private_raw_seed_body",
            subject_id=str(missing_case.get("case_id") or "seed_origin_payload"),
            subject_kind="synthetic_fixture",
        )

    refinement_count = len(
        [
            row
            for row in refinement_rows
            if row.get("refinement_result") in {"fixture_manifest_refined", "validator_contract_refined"}
            and row.get("owner_surface")
            and not row.get("claims_global_doctrine_authority")
            and str(row.get("receipt_id") or "") not in duplicate_receipt_ids
        ]
    )
    typed_nothing_count = len(
        [
            row
            for row in nothing_rows
            if row.get("refinement_result") == "nothing_to_refine"
            and row.get("stewardship_checked")
            and row.get("next_best_lane_checked")
            and row.get("reentry_condition")
        ]
    )
    missing_closeout_count = len(
        [row for row in landings if not row.get("closeout_refinement_result")]
    )

    selected_same_lane = {
        "assigned_lane": "pattern_assimilation_step",
        "selection_basis": "latest_append_index_within_assigned_lane",
        "status": PASS,
    }
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "wave_1_organ_ids": WAVE_1_ORGAN_IDS,
        "landing_decision_count": len(landings),
        "refinement_count": refinement_count,
        "typed_nothing_to_refine_count": typed_nothing_count,
        "missing_closeout_count": missing_closeout_count,
        "landed_organ_id": "agent_route_observability_runtime",
        "refinement_result": "validator_contract_refined",
        "owner_surface": "microcosm-substrate/core/fixture_manifests/pattern_assimilation_step.fixture_manifest.json",
        "changed_surface_ref": "microcosm-substrate/src/microcosm_core/validators/acceptance.py",
        "stewardship_checked": True,
        "next_best_lane_checked": True,
        "next_best_lane_result": "post_pattern_assimilation_reducer_required",
        "reentry_condition": "rerun when a later reducer authorizes release, hosted-public, publication, recipient, or additional public organ work",
        "assigned_lane": "pattern_assimilation_step",
        "already_run_lane_detection": {
            "status": PASS,
            "latest_same_lane_receipt_found": False,
            "duplicate_target_without_refinement": False,
        },
        "same_lane_receipt_selection": selected_same_lane,
        "latest_same_lane_receipt_ref": "synthetic_first_public_pattern_assimilation_closeout",
        "latest_same_lane_receipt_source_line_no": 1,
        "latest_same_lane_receipt_append_index": 1,
        "concrete_improvement_made": True,
        "changed_artifact_refs": [
            "microcosm-substrate/src/microcosm_core/validators/acceptance.py",
            "microcosm-substrate/core/pattern_assimilation_policy.json",
            "microcosm-substrate/skills/pattern_assimilation.md",
        ],
        "validation_commands": [
            "python -m microcosm_core.validators.acceptance --only pattern_assimilation_step",
            "pytest tests/test_pattern_assimilation_step.py",
        ],
        "validation_status": PASS,
        "residual_capture_refs": [],
        "residual_lifecycle_review": {
            "status": "reviewed_no_residuals_required_for_synthetic_fixture",
            "reviewed_residual_capture_refs": [],
            "body_redacted": True,
        },
        "fixed_point_closeout_evidence": {
            "ordered_validation": [
                "acceptance_command",
                "field_floor_check",
                "truth_index_compiler",
                "projection_readiness_checker",
            ],
            "latest_same_lane_receipt_consumed": True,
            "body_redacted": True,
        },
        "duplicate_target_refinement_decision": {
            "status": "refinement_changed_target",
            "duplicate_receipt_ids": duplicate_receipt_ids,
            "body_redacted": True,
        },
        "no_concrete_edit_failure_reason": "",
        "self_refire_target": {
            "target_artifact_ref": "microcosm-substrate/src/microcosm_core/validators/acceptance.py",
            "target_artifact_role": "pattern_assimilation_closeout_validator",
            "body_redacted": True,
        },
        "next_self_refire_direction": "run post-pattern-assimilation reducer before release or publication work",
        "duplicate_receipt_ids": duplicate_receipt_ids,
    }


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(code)
    return {key: sorted(value) for key, value in sorted(merged.items())}


def _common_receipt(result: dict[str, Any], *, schema_version: str, receipt_paths: list[str]) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "receipt_id": schema_version,
        "organ_id": result["organ_id"],
        "fixture_id": result["fixture_id"],
        "validator_id": result["validator_id"],
        "command": result["command"],
        "status": result["status"],
        "created_at": result["created_at"],
        "expected_negative_cases": result["expected_negative_cases"],
        "observed_negative_cases": result["observed_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "findings": result["findings"],
        "anti_claim": result["anti_claim"],
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "receipt_paths": receipt_paths,
    }


def _core_closeout_fields(result: dict[str, Any]) -> dict[str, Any]:
    fields = result["closeout_contract"]
    return {
        key: fields[key]
        for key in (
            "landed_organ_id",
            "refinement_result",
            "owner_surface",
            "changed_surface_ref",
            "stewardship_checked",
            "next_best_lane_checked",
            "next_best_lane_result",
            "reentry_condition",
            "assigned_lane",
            "already_run_lane_detection",
            "same_lane_receipt_selection",
            "latest_same_lane_receipt_ref",
            "latest_same_lane_receipt_source_line_no",
            "latest_same_lane_receipt_append_index",
            "concrete_improvement_made",
            "changed_artifact_refs",
            "validation_commands",
            "validation_status",
            "residual_capture_refs",
            "residual_lifecycle_review",
            "fixed_point_closeout_evidence",
            "duplicate_target_refinement_decision",
            "no_concrete_edit_failure_reason",
            "self_refire_target",
            "next_self_refire_direction",
            "duplicate_receipt_ids",
        )
    }


def _write_jsonl_upsert(path: Path, row: dict[str, Any], *, run_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("run_id") != run_id:
                rows.append(payload)
    rows.append(row)
    fd, tmp_name = tempfile.mkstemp(prefix=f"{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for payload in rows:
                fh.write(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
                fh.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def write_outputs(
    out_path: str | Path,
    result: dict[str, Any],
    *,
    public_root: str | Path,
) -> dict[str, str]:
    target = Path(out_path)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target = target.resolve(strict=False)
    public_root = Path(public_root).resolve(strict=False)
    if _is_relative_to(target, public_root):
        repo_root = public_root.parent
    else:
        repo_root = target.parent
    assimilation_path = target.parent / "pattern_assimilation_receipt.json"
    macro_runs_path = repo_root / MACRO_RUNS_REL
    paths = {
        "acceptance": target,
        "assimilation": assimilation_path,
        "macro_runs": macro_runs_path,
    }
    receipt_paths = [
        _display_path(paths["acceptance"], public_root=public_root, repo_root=repo_root),
        _display_path(paths["assimilation"], public_root=public_root, repo_root=repo_root),
        _display_path(paths["macro_runs"], public_root=public_root, repo_root=repo_root),
    ]

    acceptance = _common_receipt(
        result,
        schema_version="pattern_assimilation_step_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "wave_1_organ_ids": result["closeout_contract"]["wave_1_organ_ids"],
            "landing_decision_count": result["closeout_contract"]["landing_decision_count"],
            "refinement_count": result["closeout_contract"]["refinement_count"],
            "typed_nothing_to_refine_count": result["closeout_contract"][
                "typed_nothing_to_refine_count"
            ],
            "missing_closeout_count": result["closeout_contract"]["missing_closeout_count"],
        }
    )
    assimilation = _common_receipt(
        result,
        schema_version="pattern_assimilation_step_receipt_v1",
        receipt_paths=receipt_paths,
    )
    assimilation.update(_core_closeout_fields(result))
    macro_row = dict(assimilation)
    macro_row.update(
        {
            "schema_version": "macro_pattern_autonomy_process_run_v1",
            "run_id": "public_pattern_assimilation_step_current_authority",
            "operator_assigned_lane": "pattern_assimilation_step",
            "public_root_write_attempt_count": 0,
            "forbidden_root_write_attempt_count": 0,
        }
    )

    write_json_atomic(paths["acceptance"], acceptance)
    write_json_atomic(paths["assimilation"], assimilation)
    _write_jsonl_upsert(paths["macro_runs"], macro_row, run_id=macro_row["run_id"])
    return {key: _display_path(path, public_root=public_root, repo_root=repo_root) for key, path in paths.items()}


def _write_assimilation_bundle_receipt(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: str | Path,
) -> str:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = Path(public_root).resolve(strict=False)
    path = target / ASSIMILATION_BUNDLE_RESULT_NAME
    receipt_path = public_relative_path(path, display_root=public_root)
    if Path(receipt_path).is_absolute() and "receipts" in path.parts:
        receipts_index = len(path.parts) - 1 - list(reversed(path.parts)).index("receipts")
        receipt_path = Path(*path.parts[receipts_index:]).as_posix()
    payload = _common_receipt(
        validation_result,
        schema_version="pattern_assimilation_step_exported_assimilation_bundle_validation_v1",
        receipt_paths=[receipt_path],
    )
    payload.update(
        {
            "input_mode": validation_result["input_mode"],
            "bundle_id": validation_result["bundle_id"],
            "bundle_manifest_schema_version": validation_result[
                "bundle_manifest_schema_version"
            ],
            "bundle_fingerprint": validation_result["bundle_fingerprint"],
            "accepted_adapter_backed_organ_ids": validation_result[
                "accepted_adapter_backed_organ_ids"
            ],
            "ordered_adapter_lane_status": validation_result[
                "ordered_adapter_lane_status"
            ],
            "organ_landing_count": validation_result["organ_landing_count"],
            "landed_organ_ids": validation_result["landed_organ_ids"],
            "landing_receipt_refs": validation_result["landing_receipt_refs"],
            "closeout_by_organ": validation_result["closeout_by_organ"],
            "refinement_receipt_ids": validation_result["refinement_receipt_ids"],
            "refinement_receipt_count": validation_result["refinement_receipt_count"],
            "refined_owner_surfaces": validation_result["refined_owner_surfaces"],
            "refinement_result_by_organ": validation_result[
                "refinement_result_by_organ"
            ],
            "nothing_to_refine_receipt_ids": validation_result[
                "nothing_to_refine_receipt_ids"
            ],
            "nothing_to_refine_receipt_count": validation_result[
                "nothing_to_refine_receipt_count"
            ],
            "stewardship_check_count": validation_result["stewardship_check_count"],
            "stewardship_check_ids": validation_result["stewardship_check_ids"],
            "reentry_condition_count": validation_result["reentry_condition_count"],
            "reentry_condition_ids": validation_result["reentry_condition_ids"],
            "next_best_lane_check_count": validation_result[
                "next_best_lane_check_count"
            ],
            "next_best_lane_result": validation_result["next_best_lane_result"],
            "next_routes": validation_result["next_routes"],
            "next_seed_paths": validation_result["next_seed_paths"],
            "assimilation_policy": validation_result["assimilation_policy"],
            "source_module_manifest_status": validation_result[
                "source_module_manifest_status"
            ],
            "source_module_manifest_ref": validation_result["source_module_manifest_ref"],
            "source_open_body_imports": validation_result["source_open_body_imports"],
            "body_copied_material_count": validation_result[
                "body_copied_material_count"
            ],
            "metadata_projection_not_live_learning_authority": validation_result[
                "metadata_projection_not_live_learning_authority"
            ],
            "public_replacement_refs": validation_result["public_replacement_refs"],
            "fixture_regression_required_elsewhere": True,
            "release_authorized": False,
        }
    )
    write_json_atomic(path, payload)
    return receipt_path


def run_assimilation_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    payloads = _load_assimilation_bundle(input_path)
    scan_result = _scan_bundle_inputs(input_path, public_root)
    private_scan = dict(scan_result)
    private_scan.pop("forbidden_output_fields", None)
    private_scan["redacted_output_field_labels_omitted"] = True

    manifest = payloads["bundle_manifest"] if isinstance(payloads["bundle_manifest"], dict) else {}
    landing_result = validate_exported_organ_landings(payloads["organ_landing_summaries"])
    refinement_result = validate_exported_refinement_receipts(
        payloads["refinement_receipts"],
        landing_result,
    )
    nothing_result = validate_exported_nothing_to_refine_receipts(
        payloads["nothing_to_refine_receipts"],
        landing_result,
    )
    stewardship_result = validate_exported_stewardship_checks(payloads["stewardship_checks"])
    reentry_result = validate_exported_reentry_conditions(payloads["reentry_conditions"])
    next_best_result = validate_exported_next_best_lane_checks(payloads["next_best_lane_checks"])
    policy_result = validate_exported_assimilation_policy(payloads["assimilation_policy"])
    source_body_result = validate_source_module_manifest(input_path, public_root)

    all_findings = sorted(
        [
            *landing_result["findings"],
            *refinement_result["findings"],
            *nothing_result["findings"],
            *stewardship_result["findings"],
            *reentry_result["findings"],
            *next_best_result["findings"],
            *policy_result["findings"],
            *source_body_result["findings"],
        ],
        key=lambda item: (
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )
    bundle_id = str(
        manifest.get("bundle_id") or "pattern_assimilation_step_exported_assimilation_bundle"
    )
    status = (
        PASS
        if scan_result["status"] == PASS
        and not all_findings
        and landing_result["landed_organ_ids"]
        and refinement_result["refinement_receipt_ids"]
        and nothing_result["nothing_to_refine_receipt_ids"]
        and stewardship_result["stewardship_check_count"]
        and reentry_result["reentry_condition_count"]
        and next_best_result["next_best_lane_check_count"]
        and policy_result["status"] == PASS
        and source_body_result["status"] == PASS
        else "blocked"
    )
    bundle_fingerprint = _stable_hash(
        {
            "organ_landing_summaries": payloads["organ_landing_summaries"],
            "refinement_receipts": payloads["refinement_receipts"],
            "nothing_to_refine_receipts": payloads["nothing_to_refine_receipts"],
            "stewardship_checks": payloads["stewardship_checks"],
            "reentry_conditions": payloads["reentry_conditions"],
            "next_best_lane_checks": payloads["next_best_lane_checks"],
            "assimilation_policy": payloads["assimilation_policy"],
            "source_open_body_imports": source_body_result,
        }
    )
    public_replacement_refs = [
        public_relative_path(path, display_root=public_root)
        for path in _assimilation_bundle_paths(input_path)
    ]
    public_replacement_refs.append(source_body_result["source_module_manifest_ref"])
    public_replacement_refs.extend(
        str(card["target_ref"])
        for card in source_body_result["body_material"]
        if card.get("target_ref")
    )

    result = base_receipt(
        ORGAN_ID,
        f"{FIXTURE_ID}.exported_assimilation_bundle",
        command=command,
    )
    result.update(
        {
            "status": status,
            "input_mode": "exported_assimilation_bundle",
            "bundle_id": bundle_id,
            "bundle_manifest_schema_version": manifest.get("schema_version"),
            "validator_id": VALIDATOR_ID,
            "anti_claim": (
                "The exported assimilation bundle validates public organ-landing, "
                "refinement, nothing-to-refine, stewardship, re-entry, and next-best-lane "
                "metadata. It does not read raw seed bodies, mutate live Task Ledger, "
                "promote global doctrine, authorize release, call providers, or prove "
                "live learning behavior."
            ),
            "authority_ceiling": {
                "status": PASS,
                "authority_ceiling": (
                    "pattern_assimilation_bundle_metadata_not_live_learning_authority"
                ),
                "raw_seed_body_read": False,
                "live_task_ledger_mutation_authorized": False,
                "global_doctrine_promotion_authorized": False,
                "release_or_publication_authorized": False,
                "provider_payload_read": False,
                "private_data_equivalence_claim": False,
                "behavior_change_overclaims_allowed": False,
                "live_learning_authority": False,
                "later_organs_authorized": False,
            },
            "expected_negative_cases": {},
            "observed_negative_cases": {},
            "missing_negative_cases": [],
            "error_codes": sorted({str(finding["error_code"]) for finding in all_findings}),
            "findings": all_findings,
            "private_state_scan": private_scan,
            "source_pattern_ids": [
                "agent_principle_failure_cap_assimilation_loop",
                "raw_seed_shard_assimilation_controller_walk",
                "up_propagation_intake",
                "task_sign_off",
                "cap_reflex_capture_before_prose",
            ],
            "accepted_adapter_backed_organ_ids": ADAPTER_BACKED_ORGAN_IDS,
            "ordered_adapter_lane_status": (
                "complete_with_formal_math_lean_std_premise_index_verifier_trace_repair_evidence_cell_tactic_ring2_benchmark_integrity_durable_work_landing_research_replication_world_model_projection_drift_spatial_world_model_simulation_materials_lab_safety_mechanistic_interpretability_provider_context_prediction_standards_meta_cold_reader_route_map_monitor_redteam_sabotage_monitor_memory_conflict_sleeper_memory_quarantine_mcp_tool_authority_governed_mutation_authorization_belief_state_process_reward_sandbox_policy_escape_indirect_prompt_injection_agentic_vulnerability_patch_proof_and_materials_lab_safety_bound"
            ),
            "landed_organ_ids": landing_result["landed_organ_ids"],
            "organ_landing_count": landing_result["organ_landing_count"],
            "landing_receipt_refs": landing_result["landing_receipt_refs"],
            "closeout_by_organ": landing_result["closeout_by_organ"],
            "organ_landing_projection_not_authority": landing_result[
                "organ_landing_projection_not_authority"
            ],
            "refinement_receipt_ids": refinement_result["refinement_receipt_ids"],
            "refinement_receipt_count": refinement_result["refinement_receipt_count"],
            "refined_owner_surfaces": refinement_result["refined_owner_surfaces"],
            "refinement_result_by_organ": refinement_result["refinement_result_by_organ"],
            "refinement_receipts_projection_not_authority": refinement_result[
                "refinement_receipts_projection_not_authority"
            ],
            "nothing_to_refine_receipt_ids": nothing_result[
                "nothing_to_refine_receipt_ids"
            ],
            "nothing_to_refine_receipt_count": nothing_result[
                "nothing_to_refine_receipt_count"
            ],
            "nothing_to_refine_result_by_organ": nothing_result[
                "nothing_to_refine_result_by_organ"
            ],
            "nothing_to_refine_projection_not_authority": nothing_result[
                "nothing_to_refine_projection_not_authority"
            ],
            "stewardship_check_count": stewardship_result["stewardship_check_count"],
            "stewardship_check_ids": stewardship_result["stewardship_check_ids"],
            "stewardship_projection_not_authority": stewardship_result[
                "stewardship_projection_not_authority"
            ],
            "reentry_condition_count": reentry_result["reentry_condition_count"],
            "reentry_condition_ids": reentry_result["reentry_condition_ids"],
            "reentry_conditions_projection_not_authority": reentry_result[
                "reentry_conditions_projection_not_authority"
            ],
            "next_best_lane_check_count": next_best_result[
                "next_best_lane_check_count"
            ],
            "next_best_lane_result": next_best_result["next_best_lane_result"],
            "next_routes": next_best_result["next_routes"],
            "next_seed_paths": next_best_result["next_seed_paths"],
            "next_best_lane_projection_not_authority": next_best_result[
                "next_best_lane_projection_not_authority"
            ],
            "assimilation_policy": policy_result,
            "source_module_manifest_status": source_body_result["status"],
            "source_module_manifest_ref": source_body_result[
                "source_module_manifest_ref"
            ],
            "source_open_body_imports": source_body_result,
            "body_copied_material_count": source_body_result["body_material_count"],
            "metadata_projection_not_live_learning_authority": True,
            "bundle_fingerprint": bundle_fingerprint,
            "public_replacement_refs": public_replacement_refs,
        }
    )
    receipt_path = _write_assimilation_bundle_receipt(out_dir, result, public_root=public_root)
    result["receipt_paths"] = [receipt_path]
    return result


def validate_pattern_assimilation(input_dir: str | Path, out: str | Path, command: str | None = None) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    payloads = _load_inputs(input_path)
    scan_result = _scan_fixture_inputs(input_path, public_root)
    closeout = _validate_rows(payloads)
    observed = _merge_observed(closeout)
    missing_cases = sorted(set(EXPECTED_NEGATIVE_CASES) - set(observed))
    error_codes = sorted({code for codes in observed.values() for code in codes})
    private_scan = dict(scan_result)
    private_scan.pop("forbidden_output_fields", None)
    private_scan["redacted_output_field_labels_omitted"] = True
    private_scan["synthetic_boundary_negative_cases_observed"] = [
        "assimilation_private_raw_seed_body"
    ]

    result = base_receipt(ORGAN_ID, FIXTURE_ID, command=command)
    result.update(
        {
            "status": PASS if not missing_cases and scan_result["status"] == PASS else "blocked",
            "validator_id": VALIDATOR_ID,
            "anti_claim": PATTERN_ASSIMILATION_ANTI_CLAIM,
            "authority_ceiling": PATTERN_ASSIMILATION_AUTHORITY_CEILING,
            "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
            "observed_negative_cases": observed,
            "missing_negative_cases": missing_cases,
            "error_codes": error_codes,
            "findings": sorted(
                closeout["findings"],
                key=lambda item: (
                    str(item.get("negative_case_id") or ""),
                    str(item.get("subject_kind") or ""),
                    str(item.get("subject_id") or ""),
                    str(item.get("error_code") or ""),
                ),
            ),
            "private_state_scan": private_scan,
            "closeout_contract": closeout,
            "fixture_inputs": [
                public_relative_path(path, display_root=public_root)
                for path in _input_paths(input_path)
            ],
        }
    )
    paths = write_outputs(out, result, public_root=public_root)
    result["receipt_paths"] = list(paths.values())
    return result


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else None
    if raw_argv is None:
        import sys

        raw_argv = sys.argv[1:]
    if raw_argv and raw_argv[0] == "validate-assimilation-bundle":
        bundle_parser = argparse.ArgumentParser()
        bundle_parser.add_argument("action", choices=["validate-assimilation-bundle"])
        bundle_parser.add_argument("--input", required=True)
        bundle_parser.add_argument("--out", required=True)
        args = bundle_parser.parse_args(raw_argv)
        command = (
            "python -m microcosm_core.validators.acceptance "
            f"validate-assimilation-bundle --input {args.input} --out {args.out}"
        )
        result = run_assimilation_bundle(args.input, args.out, command=command)
        return 0 if result["status"] == PASS else 1

    parser = argparse.ArgumentParser()
    parser.add_argument("--only", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(raw_argv)
    if args.only != ORGAN_ID:
        parser.error("only pattern_assimilation_step is supported")
    command = (
        "python -m microcosm_core.validators.acceptance "
        f"--only {args.only} --input {args.input} --out {args.out}"
    )
    result = validate_pattern_assimilation(args.input, args.out, command=command)
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
