from __future__ import annotations

import argparse
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


VALIDATOR_ID = "validator.microcosm.validators.standards_registry"
FIXTURE_ID = "first_wave.standards_registry"
RECEIPT_REL = "receipts/first_wave/standards_registry_validation.json"
REQUIRED_STANDARD_FIELDS = {
    "schema_version",
    "standard_id",
    "kind_id",
    "status",
    "authority_boundary",
    "source_refs",
    "relationships",
    "required_fields",
    "validation_rules",
    "receipt_expectations",
    "validator_contract",
    "receipt_contract",
    "public_private_boundary",
    "authority_ceiling",
    "anti_claim",
}
ACCEPTED_PUBLIC_ORGANS = [
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


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display_path(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _registry_rows(registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = registry.get("standards", [])
    return [row for row in rows if isinstance(row, dict)]


def _standard_file_for(row: dict[str, Any], standards_dir: Path) -> Path:
    path = str(row.get("path") or "").strip()
    if path:
        candidate = Path(path)
        return candidate if candidate.is_absolute() else standards_dir.parent / candidate
    standard_id = str(row.get("standard_id") or "")
    return standards_dir / f"{standard_id}.json"


def _load_standard(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = read_json_strict(path)
    if not isinstance(payload, dict):
        return None
    return payload


def _acceptance_status(acceptance: dict[str, Any]) -> dict[str, Any]:
    accepted = [
        str(row.get("organ_id"))
        for row in acceptance.get("accepted_current_authority_organs", [])
        if isinstance(row, dict) and row.get("organ_id")
    ]
    missing = [organ_id for organ_id in ACCEPTED_PUBLIC_ORGANS if organ_id not in accepted]
    unexpected = [
        organ_id for organ_id in accepted if organ_id not in ACCEPTED_PUBLIC_ORGANS
    ]
    deferred = [
        str(row.get("organ_id"))
        for row in acceptance.get("deferred_organs", [])
        if isinstance(row, dict) and row.get("organ_id")
    ]
    return {
        "status": PASS if not missing and not unexpected else "blocked_acceptance_mismatch",
        "accepted_current_authority_organs": accepted,
        "missing_accepted_organs": missing,
        "unexpected_accepted_organs": unexpected,
        "deferred_organs": deferred,
        "lean_lake_authorized": acceptance.get("lean_lake_authorized", False),
        "release_authorized": bool(acceptance.get("release_authorized", False)),
    }


def _receipt_safe_scan(scan: dict[str, Any]) -> dict[str, Any]:
    safe = dict(scan)
    safe.pop("forbidden_output_fields", None)
    return safe


def validate_standards_registry(
    registry_path: str | Path,
    standards_dir: str | Path,
    acceptance_path: str | Path,
    out_path: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    registry_file = Path(registry_path)
    standards_root = Path(standards_dir)
    acceptance_file = Path(acceptance_path)
    output_file = Path(out_path)
    public_root = _public_root_for_path(registry_file)

    registry = read_json_strict(registry_file)
    acceptance = read_json_strict(acceptance_file)
    if not isinstance(registry, dict):
        raise ValueError(f"{registry_file}: registry must be a JSON object")
    if not isinstance(acceptance, dict):
        raise ValueError(f"{acceptance_file}: acceptance plan must be a JSON object")

    rows = _registry_rows(registry)
    standard_ids = [str(row.get("standard_id") or "") for row in rows]
    duplicate_ids = sorted(
        standard_id
        for standard_id in set(standard_ids)
        if standard_id and standard_ids.count(standard_id) > 1
    )
    missing_standard_files: list[str] = []
    missing_required_fields: dict[str, list[str]] = {}
    checked_standard_ids: list[str] = []
    standard_paths: list[Path] = []

    for row in rows:
        standard_id = str(row.get("standard_id") or "")
        standard_file = _standard_file_for(row, standards_root)
        standard_paths.append(standard_file)
        standard = _load_standard(standard_file)
        if standard is None:
            missing_standard_files.append(_display_path(standard_file, public_root=public_root))
            continue
        checked_standard_ids.append(str(standard.get("standard_id") or standard_id))
        missing = sorted(field for field in REQUIRED_STANDARD_FIELDS if field not in standard)
        if missing:
            missing_required_fields[standard_id] = missing

    registry_declared_count = int(registry.get("standard_count") or len(rows))
    count_mismatch = registry_declared_count != len(rows)
    acceptance = _acceptance_status(acceptance)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = _receipt_safe_scan(
        scan_paths(
        [registry_file, acceptance_file, *standard_paths],
        forbidden_classes=policy,
        display_root=public_root,
        )
    )

    status = PASS
    if (
        duplicate_ids
        or missing_standard_files
        or missing_required_fields
        or count_mismatch
        or acceptance["status"] != PASS
        or scan["blocking_hit_count"]
    ):
        status = "blocked"

    receipt_paths = [
        _display_path(output_file, public_root=public_root),
        _display_path(registry_file, public_root=public_root),
        _display_path(acceptance_file, public_root=public_root),
    ]
    receipt = {
        "schema_version": "standards_registry_validation_receipt_v1",
        "organ_id": "standards_registry",
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "status": status,
        "standard_count": len(rows),
        "registry_declared_standard_count": registry_declared_count,
        "checked_standard_count": len(checked_standard_ids),
        "checked_standard_ids": checked_standard_ids,
        "duplicate_standard_ids": duplicate_ids,
        "missing_standard_files": missing_standard_files,
        "missing_required_fields_by_standard": missing_required_fields,
        "acceptance_status": acceptance,
        "private_state_scan": scan,
        "authority_ceiling": {
            "status": PASS,
            "registry_authority": "public_standards_index_and_acceptance_plan_only",
            "source_authority_above_macro_contracts": False,
            "lean_lake_authorized": "bounded_public_witness_only",
            "trading_or_financial_advice_authorized": False,
            "release_authorized": False,
            "private_data_equivalence_authorized": False,
        },
        "anti_claim": (
            "Standards-registry validation proves only public-safe standard file "
            "shape and first-wave acceptance-plan consistency; it does not "
            "authorize Lean/Lake beyond the bounded public witness fixture, "
            "trading or financial advice, "
            "release, hosted-public readiness, publication, recipient work, "
            "provider calls, or private-data equivalence."
        ),
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate public standards registry")
    parser.add_argument("--registry", required=True)
    parser.add_argument("--standards-dir", required=True)
    parser.add_argument("--acceptance", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    command = (
        "python -m microcosm_core.validators.standards_registry "
        f"--registry {args.registry} --standards-dir {args.standards_dir} "
        f"--acceptance {args.acceptance} --out {args.out}"
    )
    receipt = validate_standards_registry(
        args.registry,
        args.standards_dir,
        args.acceptance,
        args.out,
        command=command,
    )
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
