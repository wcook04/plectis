from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
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
ACCEPTED_ORGAN_BACKED_STANDARD_STATUS = "accepted_public_runtime_standard"
ACCEPTED_ORGAN_BACKED_SOURCE_AUTHORITY = (
    "json_standard_contract_backed_by_accepted_organ_registry_receipt"
)
ACCEPTED_ORGAN_BACKED_RUNTIME_STATUS = "accepted_current_authority_organ_registry_backed"
ACCEPTED_ORGAN_BACKED_RUNTIME_STATUSES = {
    ACCEPTED_ORGAN_BACKED_RUNTIME_STATUS,
    ACCEPTED_ORGAN_BACKED_STANDARD_STATUS,
}
ACTIVE_STANDARD_SCHEMA_VERSION = "public_microcosm_standard_v2"
ACTIVE_STANDARD_STATUS = "active"
ORGAN_EVIDENCE_BASIS_KEYS = {
    "organ_evidence_class": "evidence_class",
    "organ_evidence_strength_rank": "evidence_strength_rank",
    "truth_accounting_bucket": "truth_accounting_bucket",
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
    "verifier_lab_kernel",
    "verifier_lab_execution_spine",
    "navigation_hologram_route_plane",
    "mission_transaction_work_spine",
    "durable_agent_work_landing_replay",
    "research_replication_rubric_artifact_replay",
    "world_model_projection_drift_control_room",
    "spatial_world_model_counterfactual_simulation_replay",
    "mechanistic_interpretability_circuit_attribution_replay",
    "agent_route_observability_runtime",
    "bridge_phase_continuity_runtime",
    "pattern_assimilation_step",
    "public_reveal_walkthrough",
    "macro_projection_import_protocol",
    "voice_to_doctrine_self_improvement_loop",
    "cognitive_operator_registry",
    "routing_anti_patterns_registry",
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
    "materials_chemistry_closed_loop_lab_safety_replay",
    "certificate_kernel_execution_lab",
    "voice_to_doctrine_self_improvement_loop",
    "cognitive_operator_registry",
    "routing_anti_patterns_registry",
    "agent_closeout_faithfulness_audit",
    "doctrine_fact_claim_audit",
    "self_ignorance_coverage_ledger",
    "bounded_autonomy_campaign_packet",
    "finance_forecast_evaluation_spine",
    "batch4_proof_authority_runtime",
    "batch5_authority_systems_capsule",
    "batch6_unsurfaced_primitives_capsule",
    "batch7_oracle_sibling_capsule",
    "batch7_demo_take_console_capsule",
    "batch7_secondary_runtime_capsule",
    "batch7_macro_engines_capsule",
    "batch7_station_runtime_capsule",
    "batch8_tools_tail_primitives_capsule",
    "batch8_policy_engines_capsule",
    "batch8_audio_level_rms_port",
    "batch8_station_surface_atlas_layout_port",
    "batch8_structural_theses_capsule",
    "engine_room_demo",
    "batch9_macro_engines_capsule",
    "batch10_governance_compilers_capsule",
    "batch10_frontend_work_market_cockpit_capsule",
    "batch11_saturation_engines_capsule",
    "tool_server_pressure_inventory",
    "workstream_driver_recency_coalescer",
    "batch8_compliance_pipeline_capsule",
    "batch10_live_source_drift_capsule",
    "batch10_cold_eval_honesty_capsule",
    "batch8_validator_checker_capsule",
    "concurrency_mission_control",
    "batch12_market_dashboard_read_model_capsule",
    "batch12_prediction_market_board_capsule",
    "batch12_release_claim_language_gate",
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


def _accepted_organ_standard_contract_alignment(
    loaded_standards: list[tuple[dict[str, Any], str, dict[str, Any]]],
    organ_registry: dict[str, Any],
) -> dict[str, Any]:
    accepted_organs = {
        str(row.get("organ_id")): row
        for row in organ_registry.get("implemented_organs", [])
        if isinstance(row, dict)
        and row.get("organ_id")
        and row.get("status") == "accepted_current_authority"
    }
    checked_standard_ids: list[str] = []
    errors: list[dict[str, Any]] = []

    def add_error(
        standard_id: str,
        code: str,
        *,
        expected: Any,
        actual: Any,
        path: str,
    ) -> None:
        errors.append(
            {
                "standard_id": standard_id,
                "code": code,
                "expected": expected,
                "actual": actual,
                "path": path,
            }
        )

    for row, standard_id, standard in loaded_standards:
        payload = standard.get("standard_payload", {})
        basis = (
            payload.get("contract_projection_basis", {})
            if isinstance(payload, dict)
            else {}
        )
        if not isinstance(basis, dict):
            continue
        if not any(key in basis for key in ORGAN_EVIDENCE_BASIS_KEYS):
            continue

        checked_standard_ids.append(standard_id)
        kind_id = str(standard.get("kind_id") or row.get("kind_id") or "")
        organ = accepted_organs.get(kind_id)
        if organ is None:
            add_error(
                standard_id,
                "organ_evidence_basis_without_accepted_organ_registry_row",
                expected="core/organ_registry.json::implemented_organs.status=accepted_current_authority",
                actual=kind_id or None,
                path="kind_id",
            )
            continue

        if row.get("status") != ACCEPTED_ORGAN_BACKED_STANDARD_STATUS:
            add_error(
                standard_id,
                "registry_status_not_accepted_for_organ_backed_standard",
                expected=ACCEPTED_ORGAN_BACKED_STANDARD_STATUS,
                actual=row.get("status"),
                path="core/standards_registry.json::standards[].status",
            )
        if standard.get("source_authority") != ACCEPTED_ORGAN_BACKED_SOURCE_AUTHORITY:
            add_error(
                standard_id,
                "source_authority_not_organ_registry_backed",
                expected=ACCEPTED_ORGAN_BACKED_SOURCE_AUTHORITY,
                actual=standard.get("source_authority"),
                path="source_authority",
            )
        if basis.get("runtime_acceptance_status") not in ACCEPTED_ORGAN_BACKED_RUNTIME_STATUSES:
            add_error(
                standard_id,
                "basis_runtime_acceptance_status_not_organ_registry_backed",
                expected=sorted(ACCEPTED_ORGAN_BACKED_RUNTIME_STATUSES),
                actual=basis.get("runtime_acceptance_status"),
                path="standard_payload.contract_projection_basis.runtime_acceptance_status",
            )

        top_runtime_status = standard.get("runtime_acceptance_status")
        if (
            top_runtime_status is not None
            and top_runtime_status not in ACCEPTED_ORGAN_BACKED_RUNTIME_STATUSES
        ):
            add_error(
                standard_id,
                "top_level_runtime_acceptance_status_not_organ_registry_backed",
                expected=sorted(ACCEPTED_ORGAN_BACKED_RUNTIME_STATUSES),
                actual=top_runtime_status,
                path="runtime_acceptance_status",
            )

        refs = standard.get("runtime_acceptance_refs", {})
        if isinstance(refs, dict) and "registry_status" in refs:
            if refs.get("registry_status") != ACCEPTED_ORGAN_BACKED_STANDARD_STATUS:
                add_error(
                    standard_id,
                    "runtime_acceptance_refs_registry_status_not_accepted",
                    expected=ACCEPTED_ORGAN_BACKED_STANDARD_STATUS,
                    actual=refs.get("registry_status"),
                    path="runtime_acceptance_refs.registry_status",
                )

        for basis_key, organ_key in ORGAN_EVIDENCE_BASIS_KEYS.items():
            if basis.get(basis_key) != organ.get(organ_key):
                add_error(
                    standard_id,
                    "organ_evidence_basis_mismatch",
                    expected=organ.get(organ_key),
                    actual=basis.get(basis_key),
                    path=f"standard_payload.contract_projection_basis.{basis_key}",
                )

    return {
        "status": PASS if not errors else "blocked",
        "checked_standard_count": len(checked_standard_ids),
        "checked_standard_ids": checked_standard_ids,
        "error_count": len(errors),
        "errors": errors,
        "authority_boundary": (
            "checks only standards that explicitly claim accepted-organ evidence fields; "
            "draft standards without those fields are not promoted by this validator"
        ),
    }


def _increment(counter: dict[str, int], key: object) -> None:
    label = str(key if key is not None else "unspecified")
    counter[label] = counter.get(label, 0) + 1


def _unique_strings(*values: Any) -> list[str]:
    strings: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, str):
            candidates: list[Any] = [value]
        elif isinstance(value, list):
            candidates = value
        else:
            continue
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            normalized = candidate.strip()
            if normalized and normalized not in seen:
                strings.append(normalized)
                seen.add(normalized)
    return strings


def _relationships(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        relationships = payload.get("relationships")
        if isinstance(relationships, dict):
            return relationships
    return {}


def _contract_projection_status(standard: dict[str, Any]) -> str:
    if (
        standard.get("schema_version") == ACTIVE_STANDARD_SCHEMA_VERSION
        and standard.get("status") == ACTIVE_STANDARD_STATUS
    ):
        return "active_v2_governed_json"
    return "legacy_or_draft_standard_contract"


def _used_by_organ_admission_summary(
    loaded_standards: list[tuple[dict[str, Any], str, dict[str, Any]]],
    organ_registry: dict[str, Any],
) -> dict[str, Any]:
    """Classify source-declared standard.used_by.organ pressure without accepting it."""
    organ_rows = {
        str(row.get("organ_id")): row
        for row in organ_registry.get("implemented_organs", [])
        if isinstance(row, dict) and row.get("organ_id")
    }
    accepted_organs = {
        organ_id
        for organ_id, row in organ_rows.items()
        if row.get("status") == "accepted_current_authority"
    }
    edge_count = 0
    resolved_edge_count = 0
    unresolved_details: list[dict[str, Any]] = []
    counts_by_admission_status: dict[str, int] = {}
    counts_by_target_status: dict[str, int] = {}
    unresolved_counts_by_contract_projection_status: dict[str, int] = {}
    unresolved_counts_by_registry_status: dict[str, int] = {}
    unresolved_counts_by_source_status: dict[str, int] = {}
    unresolved_counts_by_source_schema_version: dict[str, int] = {}
    unresolved_standard_ids: set[str] = set()
    unresolved_target_organ_ids: set[str] = set()

    for row, standard_id, standard in loaded_standards:
        standard_relationships = _relationships(standard)
        payload = standard.get("standard_payload", {})
        payload_relationships = _relationships(payload)
        source_ref = str(row.get("path") or f"standards/{standard_id}.json")
        if "used_by_organs" in standard_relationships:
            source_used_by = standard_relationships.get("used_by_organs")
            edge_source_base = f"{source_ref}::relationships.used_by_organs"
        elif "used_by_organs" in payload_relationships:
            source_used_by = payload_relationships.get("used_by_organs")
            edge_source_base = (
                f"{source_ref}::standard_payload.relationships.used_by_organs"
            )
        else:
            source_used_by = None
            edge_source_base = (
                "core/standards_registry.json::standards[].used_by_organs"
            )
        used_by_organs = _unique_strings(source_used_by, row.get("used_by_organs"))
        contract_projection_status = _contract_projection_status(standard)
        for edge_index, organ_id in enumerate(used_by_organs):
            edge_count += 1
            target_row = organ_rows.get(organ_id)
            target_status = (
                str(target_row.get("status"))
                if isinstance(target_row, dict) and target_row.get("status")
                else "unresolved_json_instance"
            )
            if organ_id in accepted_organs:
                admission_status = "accepted_current_authority"
                resolved_edge_count += 1
            else:
                admission_status = "target_organ_not_accepted_current_authority"
            _increment(counts_by_admission_status, admission_status)
            _increment(counts_by_target_status, target_status)
            if admission_status == "accepted_current_authority":
                continue

            unresolved_standard_ids.add(standard_id)
            unresolved_target_organ_ids.add(organ_id)
            _increment(
                unresolved_counts_by_contract_projection_status,
                contract_projection_status,
            )
            _increment(unresolved_counts_by_registry_status, row.get("status"))
            _increment(unresolved_counts_by_source_status, standard.get("status"))
            _increment(
                unresolved_counts_by_source_schema_version,
                standard.get("schema_version"),
            )
            unresolved_details.append(
                {
                    "standard_id": standard_id,
                    "target_organ_id": organ_id,
                    "admission_status": admission_status,
                    "target_status": target_status,
                    "source_standard_schema_version": standard.get("schema_version"),
                    "source_standard_status": standard.get("status"),
                    "registry_status": row.get("status"),
                    "contract_projection_status": contract_projection_status,
                    "source_ref": source_ref,
                    "registry_ref": (
                        "core/standards_registry.json::standards[]"
                    ),
                    "edge_source_ref": f"{edge_source_base}[{edge_index}]",
                    "claim_ceiling": (
                        "standard_used_by_organ_admission_summary_is_reentry_metadata_"
                        "not_usage_or_acceptance_proof"
                    ),
                    "authority_boundary": (
                        "computed_from_standard_relationships_used_by_organs_and_"
                        "organ_registry_status_not_organ_admission_or_runtime_use"
                    ),
                    "reentry_condition": (
                        "When the target organ is accepted_current_authority, or the "
                        "standard source renames/removes the target, rerun the "
                        "standards-registry validator and the standard corpus check."
                    ),
                }
            )

    unresolved_details = sorted(
        unresolved_details,
        key=lambda item: (item["standard_id"], item["target_organ_id"]),
    )
    return {
        "schema_version": "standard_used_by_organ_admission_summary_v1",
        "status": "computed",
        "edge_count": edge_count,
        "resolved_edge_count": resolved_edge_count,
        "unresolved_edge_count": len(unresolved_details),
        "detail_count": len(unresolved_details),
        "unresolved_standard_count": len(unresolved_standard_ids),
        "unresolved_standard_ids": sorted(unresolved_standard_ids),
        "unresolved_target_organ_count": len(unresolved_target_organ_ids),
        "unresolved_target_organ_ids": sorted(unresolved_target_organ_ids),
        "counts_by_admission_status": dict(
            sorted(counts_by_admission_status.items())
        ),
        "counts_by_target_status": dict(sorted(counts_by_target_status.items())),
        "unresolved_counts_by_contract_projection_status": dict(
            sorted(unresolved_counts_by_contract_projection_status.items())
        ),
        "unresolved_counts_by_registry_status": dict(
            sorted(unresolved_counts_by_registry_status.items())
        ),
        "unresolved_counts_by_source_status": dict(
            sorted(unresolved_counts_by_source_status.items())
        ),
        "unresolved_counts_by_source_schema_version": dict(
            sorted(unresolved_counts_by_source_schema_version.items())
        ),
        "unresolved_details": unresolved_details,
        "authority_boundary": (
            "read_only_gap_classification_from_standard_json_registry_rows_and_"
            "organ_registry_status; does_not_accept_organs_or_prove_runtime_use"
        ),
        "anti_claims": [
            "A resolved used_by_organs target means only that the named organ is accepted in the public organ registry.",
            "An unresolved target is re-entry metadata, not a failed standard or evidence of runtime use.",
            "The standards-registry validator does not accept organs, activate standards, or authorize release.",
        ],
    }


def _activation_witness_gap_summary(
    loaded_standards: list[tuple[dict[str, Any], str, dict[str, Any]]],
) -> dict[str, Any]:
    """Classify standard activation gaps without activating any standard."""
    details: list[dict[str, Any]] = []
    counts_by_gap_id: dict[str, int] = {}
    counts_by_registry_status: dict[str, int] = {}
    counts_by_source_status: dict[str, int] = {}
    counts_by_source_schema_version: dict[str, int] = {}

    for row, standard_id, standard in loaded_standards:
        source_schema = standard.get("schema_version")
        source_status = standard.get("status")
        registry_status = row.get("status")
        gap_ids: list[str] = []
        if source_schema != ACTIVE_STANDARD_SCHEMA_VERSION:
            gap_ids.append("source_schema_not_public_microcosm_standard_v2")
        if source_status != ACTIVE_STANDARD_STATUS:
            gap_ids.append("source_status_not_active")
        if not gap_ids:
            continue

        for gap_id in gap_ids:
            _increment(counts_by_gap_id, gap_id)
        _increment(counts_by_registry_status, registry_status)
        _increment(counts_by_source_status, source_status)
        _increment(counts_by_source_schema_version, source_schema)
        details.append(
            {
                "standard_id": standard_id,
                "source_schema_version": source_schema,
                "source_status": source_status,
                "registry_status": registry_status,
                "gap_ids": gap_ids,
                "gap_count": len(gap_ids),
                "source_ref": str(row.get("path") or f"standards/{standard_id}.json"),
                "registry_ref": "core/standards_registry.json::standards[]",
                "claim_ceiling": (
                    "activation_gap_summary_only_not_activation_or_release_authority"
                ),
            }
        )

    return {
        "schema_version": "standard_activation_witness_gap_summary_v1",
        "status": "computed",
        "detail_count": len(details),
        "counts_by_gap_id": dict(sorted(counts_by_gap_id.items())),
        "counts_by_registry_status": dict(sorted(counts_by_registry_status.items())),
        "counts_by_source_status": dict(sorted(counts_by_source_status.items())),
        "counts_by_source_schema_version": dict(
            sorted(counts_by_source_schema_version.items())
        ),
        "details": sorted(details, key=lambda item: item["standard_id"]),
        "authority_boundary": (
            "read_only_gap_classification_from_registry_and_standard_json; "
            "does_not_activate_standards_or_promote_draft_contracts"
        ),
        "anti_claims": [
            "A listed activation gap is re-entry metadata, not a failed validation.",
            "The standards-registry validator does not flip source status or schema authority.",
            "Passing registry validation does not authorize release, completeness, or runtime use.",
        ],
    }


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
    loaded_standards: list[tuple[dict[str, Any], str, dict[str, Any]]] = []

    for row in rows:
        standard_id = str(row.get("standard_id") or "")
        standard_file = _standard_file_for(row, standards_root)
        standard_paths.append(standard_file)
        standard = _load_standard(standard_file)
        if standard is None:
            missing_standard_files.append(_display_path(standard_file, public_root=public_root))
            continue
        checked_standard_ids.append(str(standard.get("standard_id") or standard_id))
        loaded_standards.append(
            (row, str(standard.get("standard_id") or standard_id), standard)
        )
        missing = sorted(field for field in REQUIRED_STANDARD_FIELDS if field not in standard)
        if missing:
            missing_required_fields[standard_id] = missing

    registry_declared_count = int(registry.get("standard_count") or len(rows))
    count_mismatch = registry_declared_count != len(rows)
    acceptance = _acceptance_status(acceptance)
    organ_registry_file = public_root / "core/organ_registry.json"
    organ_registry = read_json_strict(organ_registry_file) if organ_registry_file.is_file() else {}
    organ_standard_alignment = _accepted_organ_standard_contract_alignment(
        loaded_standards,
        organ_registry if isinstance(organ_registry, dict) else {},
    )
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan_paths_to_check = [registry_file, acceptance_file, *standard_paths]
    if organ_registry_file.is_file():
        scan_paths_to_check.append(organ_registry_file)
    scan = _receipt_safe_scan(
        scan_paths(
            scan_paths_to_check,
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
        or organ_standard_alignment["status"] != PASS
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
        "accepted_organ_standard_contract_alignment": organ_standard_alignment,
        "activation_witness_gap_summary": _activation_witness_gap_summary(
            loaded_standards
        ),
        "used_by_organ_admission_summary": _used_by_organ_admission_summary(
            loaded_standards,
            organ_registry if isinstance(organ_registry, dict) else {},
        ),
        "secret_exclusion_scan": scan,
        "authority_ceiling": {
            "status": PASS,
            "registry_authority": "public_standards_index_and_acceptance_plan_only",
            "count_authority": (
                "inventory_only_not_completeness_readiness_maturity_or_product_progress"
            ),
            "source_authority_above_macro_contracts": False,
            "lean_lake_authorized": "bounded_public_witness_only",
            "standard_count_is_completeness_or_readiness": False,
            "first_wave_required_count_is_product_progress": False,
            "score_based_progress_authority": False,
            "trading_or_financial_advice_authorized": False,
            "release_authorized": False,
            "private_data_equivalence_authorized": False,
        },
        "anti_claim": (
            "Standards-registry validation proves only source-available standard file "
            "shape and first-wave acceptance-plan consistency. Standard counts "
            "and first-wave-required rows are inventory fields only, not "
            "completeness, readiness, maturity, or score-based progress; it does not "
            "authorize Lean/Lake beyond the bounded public witness fixture, "
            "trading or financial advice, "
            "release, hosted deployment, publication, recipient work, "
            "credentialed provider calls, or secret export."
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
