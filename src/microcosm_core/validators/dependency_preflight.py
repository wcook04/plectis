from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.dependency_preflight"
ACCEPTED_ORGAN_IDS = [
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
    "navigation_hologram_route_plane",
    "mission_transaction_work_spine",
    "durable_agent_work_landing_replay",
    "research_replication_rubric_artifact_replay",
    "world_model_projection_drift_control_room",
    "spatial_world_model_counterfactual_simulation_replay",
    "mechanistic_interpretability_circuit_attribution_replay",
    "agent_route_observability_runtime",
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
]
DEFERRED_ORGAN_IDS = ["formal_math_lean_proof_organ"]


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _receipt_safe_scan(scan: dict[str, Any]) -> dict[str, Any]:
    safe = dict(scan)
    safe.pop("forbidden_output_fields", None)
    return safe


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)]


def _organ_registry(public_root: Path) -> dict[str, Any]:
    return read_json_strict(public_root / "core/organ_registry.json")


def _accepted_from_registry(registry: dict[str, Any]) -> list[str]:
    return [
        str(row.get("organ_id"))
        for row in _rows(registry, "implemented_organs")
        if row.get("status") == "accepted_current_authority"
    ]


def _fixture_input_exists(public_root: Path, rel: str) -> bool:
    return (public_root / rel).exists()


def _public_fixture_manifest(public_root: Path, organ_id: str, row: dict[str, Any]) -> Path:
    macro_manifest = Path(str(row.get("fixture_manifest") or ""))
    manifest_name = macro_manifest.name or f"{organ_id}.fixture_manifest.json"
    return public_root / "core/fixture_manifests" / manifest_name


def _public_manifest_inputs(manifest_path: Path) -> list[str]:
    if not manifest_path.is_file():
        return []
    manifest = read_json_strict(manifest_path)
    if not isinstance(manifest, dict):
        return []
    inputs = manifest.get("inputs", [])
    paths: list[str] = []
    if isinstance(inputs, list):
        for row in inputs:
            if isinstance(row, dict) and row.get("path"):
                paths.append(str(row["path"]))
            elif isinstance(row, str):
                paths.append(row)
    return paths


def _negative_case_count(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("negative_cases", "cases", "rows"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return len(rows)
        return sum(1 for value in payload.values() if isinstance(value, (dict, list)))
    return 0


def run_dependency_preflight(
    readiness_path: str | Path,
    negative_matrix_path: str | Path,
    out_path: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    output_file = Path(out_path)
    public_root = _public_root_for_path(output_file)
    readiness_file = Path(readiness_path)
    negative_matrix_file = Path(negative_matrix_path)
    readiness = read_json_strict(readiness_file)
    negative_matrix = read_json_strict(negative_matrix_file)
    registry = _organ_registry(public_root)

    accepted = _accepted_from_registry(registry)
    readiness_by_id = {
        str(row.get("organ_id")): row for row in _rows(readiness, "organ_readiness")
    }
    blocked_codes: list[str] = []
    fixture_checks: list[dict[str, Any]] = []
    dependency_checks: list[dict[str, Any]] = []
    for organ_id in accepted:
        row = readiness_by_id.get(organ_id, {})
        public_manifest = _public_fixture_manifest(public_root, organ_id, row)
        manifest_inputs = _public_manifest_inputs(public_manifest)
        missing_deps = [
            dep
            for dep in row.get("build_dependencies", [])
            if dep not in accepted and dep not in DEFERRED_ORGAN_IDS
        ]
        if missing_deps:
            blocked_codes.append("MISSING_ACCEPTED_BUILD_DEPENDENCY")
        dependency_checks.append(
            {
                "organ_id": organ_id,
                "build_dependencies": row.get("build_dependencies", []),
                "missing_dependencies": missing_deps,
                "status": PASS if not missing_deps else "blocked",
            }
        )
        macro_fixture_inputs = [str(path) for path in row.get("fixture_inputs", [])]
        fixture_inputs = manifest_inputs or macro_fixture_inputs
        missing_inputs = [
            rel for rel in fixture_inputs if not _fixture_input_exists(public_root, rel)
        ]
        if missing_inputs:
            blocked_codes.append("MISSING_FIXTURE_INPUT")
        fixture_checks.append(
            {
                "organ_id": organ_id,
                "fixture_id": row.get("fixture_id"),
                "fixture_manifest": _display(public_manifest, public_root=public_root)
                if public_manifest.is_file()
                else None,
                "input_source": "public_fixture_manifest"
                if manifest_inputs
                else "macro_readiness_fixture_inputs",
                "macro_fixture_input_ref_count": len(macro_fixture_inputs),
                "fixture_input_count": len(fixture_inputs),
                "missing_fixture_inputs": missing_inputs,
                "status": PASS if not missing_inputs else "blocked",
            }
        )

    accepted_order = [organ_id for organ_id in ACCEPTED_ORGAN_IDS if organ_id in accepted]
    wave_order_checks = {
        "status": PASS if accepted_order == accepted else "blocked_wave_order_mismatch",
        "expected_prefix_order": ACCEPTED_ORGAN_IDS,
        "observed_accepted_order": accepted,
    }
    if wave_order_checks["status"] != PASS:
        blocked_codes.append("ACCEPTED_ORGAN_ORDER_MISMATCH")

    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = _receipt_safe_scan(
        scan_paths(
            [readiness_file, negative_matrix_file, public_root / "core/organ_registry.json"],
            forbidden_classes=policy,
            display_root=public_root,
        )
    )
    if scan["blocking_hit_count"]:
        blocked_codes.append("PRIVATE_STATE_SCAN_BLOCKED")

    blocked_codes = sorted(set(blocked_codes))
    status = PASS if not blocked_codes else "blocked"
    receipt = {
        "schema_version": "dependency_preflight_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": status,
        "command": command,
        "checked_organs": accepted,
        "toolchain_checks": {
            "python_validator_runtime": PASS,
            "lean_lake_execution": "bounded_public_witness_only",
            "provider_calls": "not_authorized",
            "trading_or_financial_advice": "not_authorized",
        },
        "fixture_precondition_checks": fixture_checks,
        "wave_order_checks": wave_order_checks,
        "dependency_checks": dependency_checks,
        "negative_matrix_case_count": _negative_case_count(negative_matrix),
        "blocked_dependency_count": len(blocked_codes),
        "blocked_dependency_codes": blocked_codes,
        "anti_claim": "Dependency preflight validates accepted public runtime-spine ordering and fixture presence only; it does not authorize Lean/Lake beyond the bounded public witness fixture, release, provider calls, or private-data equivalence.",
        "private_state_scan": scan,
        "authority_ceiling": {
            "status": PASS,
            "dependency_preflight_authority": "accepted_public_runtime_spine_preflight_only",
            "lean_lake_authorized": "bounded_public_witness_only",
            "trading_or_financial_advice_authorized": False,
            "release_authorized": False,
            "private_data_equivalence_authorized": False,
        },
        "receipt_paths": [_display(output_file, public_root=public_root)],
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run public dependency preflight")
    parser.add_argument("--readiness", required=True)
    parser.add_argument("--negative-matrix", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = (
        "python -m microcosm_core.validators.dependency_preflight "
        f"--readiness {args.readiness} --negative-matrix {args.negative_matrix} --out {args.out}"
    )
    receipt = run_dependency_preflight(
        args.readiness,
        args.negative_matrix,
        args.out,
        command=command,
    )
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
