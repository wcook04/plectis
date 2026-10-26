from __future__ import annotations

import json
import shutil
import copy
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.validators.standards_registry import _acceptance_status, validate_standards_registry


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOM_STAGED_STANDARD_IDS = {
    "std_microcosm_engine_room_annex_knowledge_router",
    "std_microcosm_engine_room_bridge_campaign_dag",
    "std_microcosm_engine_room_command_run_singleflight",
    "std_microcosm_engine_room_derived_fact_provider_engine",
    "std_microcosm_engine_room_egress_self_compliance_gate",
    "std_microcosm_engine_room_generated_projection_drift_gate",
    "std_microcosm_engine_room_lean_proof_search_lab",
    "std_microcosm_engine_room_metabolism_runtime",
    "std_microcosm_engine_room_navigation_fitness_benchmark",
    "std_microcosm_engine_room_public_projection_leak_gate",
}


def _walk_keys(payload: Any) -> list[str]:
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


def _copy_public_standards_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "standards", public_root / "standards")
    return public_root


def _acceptance_policy():
    organ = {"organ_id": "declared_organ", "status": "accepted_current_authority",
             "evidence_class": "semantic_validator", "evidence_strength_rank": 5,
             "truth_accounting_bucket": "real_import_validation",
             "counts_as_real_substrate_progress": True, "runner": "microcosm_core.organs.declared_organ"}
    return (
        {"accepted_current_authority_organs": [copy.deepcopy(organ)], "deferred_organs": [],
         "lean_lake_authorized": "bounded_public_witness_only", "release_authorized": False},
        {"implemented_organs": [copy.deepcopy(organ)]},
        {"fail_closed_no_default": True,
         "class_profiles": {"semantic_validator": {"evidence_strength_rank": 5,
             "truth_accounting_bucket": "real_import_validation", "counts_as_real_substrate_progress": True}},
         "organ_evidence_classes": [{"organ_id": "declared_organ", "evidence_class": "semantic_validator"}]},
    )


def test_acceptance_membership_requires_current_registry_and_evidence_assignment():
    plan, registry, evidence = _acceptance_policy()
    assert _acceptance_status(plan, registry, evidence)["status"] == "pass"
    future = {**registry["implemented_organs"][0], "organ_id": "unreviewed_future_organ"}
    registry["implemented_organs"].append(future)
    plan["accepted_current_authority_organs"].append(copy.deepcopy(future))
    result = _acceptance_status(plan, registry, evidence)
    assert result["status"] == "blocked_acceptance_mismatch"
    assert {"code": "invalid_organ_evidence_assignment", "organ_id": "unreviewed_future_organ"} in result["errors"]


@pytest.mark.parametrize("mutation,code", [
    ("plan_status", "unaccepted_plan_status"),
    ("registry_status", "unaccepted_registry_status"),
    ("plan_evidence", "accepted_plan_registry_mismatch"),
    ("plan_runner", "accepted_plan_registry_mismatch"),
    ("plan_progress", "accepted_plan_registry_mismatch"),
    ("unknown_evidence", "invalid_organ_evidence_assignment"),
    ("missing_evidence", "invalid_organ_evidence_assignment"),
    ("profile_rank", "organ_evidence_profile_mismatch"),
    ("duplicate_plan", "duplicate_policy_organ"),
    ("duplicate_registry", "duplicate_policy_organ"),
    ("no_fail_closed", "invalid_accepted_evidence_policy"),
    ("release", "acceptance_authority_exceeded"),
    ("lean", "acceptance_authority_exceeded"),
    ("lean_numeric_zero", "acceptance_authority_exceeded"),
    ("also_deferred", "accepted_organ_also_deferred"),
    ("malformed_deferred", "invalid_policy_rows"),
])
def test_acceptance_rejects_invalid_status_evidence_and_authority(mutation, code):
    plan, registry, evidence = _acceptance_policy()
    if mutation == "plan_status":
        plan["accepted_current_authority_organs"][0]["status"] = "planned"
    elif mutation == "registry_status":
        registry["implemented_organs"][0]["status"] = "planned"
    elif mutation == "plan_evidence":
        plan["accepted_current_authority_organs"][0]["evidence_class"] = "external_subprocess_witness"
    elif mutation == "plan_runner":
        plan["accepted_current_authority_organs"][0]["runner"] = "unknown.runner"
    elif mutation == "plan_progress":
        plan["accepted_current_authority_organs"][0]["counts_as_real_substrate_progress"] = False
    elif mutation == "unknown_evidence":
        registry["implemented_organs"][0]["evidence_class"] = "unknown_class"
    elif mutation == "missing_evidence":
        evidence["organ_evidence_classes"] = []
    elif mutation == "profile_rank":
        registry["implemented_organs"][0]["evidence_strength_rank"] = True
    elif mutation == "duplicate_plan":
        plan["accepted_current_authority_organs"] *= 2
    elif mutation == "duplicate_registry":
        registry["implemented_organs"] *= 2
    elif mutation == "no_fail_closed":
        evidence["fail_closed_no_default"] = False
    elif mutation == "release":
        plan["release_authorized"] = True
    elif mutation == "lean":
        plan["lean_lake_authorized"] = True
    elif mutation == "lean_numeric_zero":
        plan["lean_lake_authorized"] = 0
    elif mutation == "also_deferred":
        plan["deferred_organs"] = [{"organ_id": "declared_organ"}]
    elif mutation == "malformed_deferred":
        plan["deferred_organs"] = None
    result = _acceptance_status(plan, registry, evidence)
    assert result["status"] == "blocked_acceptance_mismatch"
    assert code in {error["code"] for error in result["errors"]}


@pytest.mark.parametrize("mutation", ["unknown", "unaccepted", "evidence"])
def test_standards_registry_rejects_unadmitted_or_misclassified_plan_rows(tmp_path, mutation):
    public_root = _copy_public_standards_tree(tmp_path)
    path = public_root / "core/acceptance/first_wave_acceptance.json"
    plan = json.loads(path.read_text())
    row = plan["accepted_current_authority_organs"][0]
    if mutation == "unknown":
        row["organ_id"] = "unknown_future_organ"
    elif mutation == "unaccepted":
        row["status"] = "planned"
    else:
        row["evidence_class"] = "forged_evidence"
    path.write_text(json.dumps(plan), encoding="utf-8")
    receipt = validate_standards_registry(
        public_root / "core/standards_registry.json", public_root / "standards", path,
        public_root / "receipts/standards_registry.json", command="pytest",
    )
    assert receipt["status"] == "blocked"
    assert receipt["acceptance_status"]["status"] == "blocked_acceptance_mismatch"
    assert receipt["authority_ceiling"]["release_authorized"] is False
    if mutation == "unknown":
        assert receipt["acceptance_status"]["unexpected_accepted_organs"] == ["unknown_future_organ"]
    else:
        assert receipt["acceptance_status"]["errors"]


def test_standards_registry_validation_passes_with_secret_exclusion(tmp_path: Path) -> None:
    public_root = _copy_public_standards_tree(tmp_path)
    out = public_root / "receipts/first_wave/standards_registry_validation.json"
    registry = json.loads((public_root / "core/standards_registry.json").read_text(encoding="utf-8"))
    expected_count = len(registry["standards"])
    organ_registry = json.loads((public_root / "core/organ_registry.json").read_text())
    accepted_ids = {row["organ_id"] for row in organ_registry["implemented_organs"]
                    if row["status"] == "accepted_current_authority"}

    receipt = validate_standards_registry(
        public_root / "core/standards_registry.json",
        public_root / "standards",
        public_root / "core/acceptance/first_wave_acceptance.json",
        out,
        command="pytest",
    )

    assert receipt["status"] == "pass"
    assert receipt["standard_count"] == expected_count
    assert receipt["checked_standard_count"] == expected_count
    assert "std_microcosm_corpus_readiness_mathlib_absence_gate" in receipt["checked_standard_ids"]
    assert "std_microcosm_mathematical_strategy_atlas_hypothesis_scorer" in receipt["checked_standard_ids"]
    assert "std_microcosm_target_shape_tactic_routing_gate" in receipt["checked_standard_ids"]
    assert "std_microcosm_lean_std_premise_index" in receipt["checked_standard_ids"]
    assert "std_microcosm_formal_math_verifier_trace_repair_loop" in receipt["checked_standard_ids"]
    assert "std_microcosm_verifier_lab_kernel" in receipt["checked_standard_ids"]
    assert "std_microcosm_verifier_lab_execution_spine" in receipt["checked_standard_ids"]
    assert "std_microcosm_certificate_kernel_execution_lab" in receipt["checked_standard_ids"]
    assert "std_microcosm_formal_evidence_cell_anchor_resolver" in receipt["checked_standard_ids"]
    assert (
        "std_microcosm_undeclared_library_prior_symbol_classifier"
        in receipt["checked_standard_ids"]
    )
    assert (
        "std_microcosm_ring2_premise_retrieval_precision_recall_harness"
        in receipt["checked_standard_ids"]
    )
    assert "std_microcosm_agent_benchmark_integrity_anti_gaming_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_agent_monitor_redteam_falsification_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_agent_sabotage_scheming_monitor_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_agent_sandbox_policy_escape_replay" in receipt["checked_standard_ids"]
    assert (
        "std_microcosm_indirect_prompt_injection_information_flow_policy_replay"
        in receipt["checked_standard_ids"]
    )
    assert (
        "std_microcosm_agentic_vulnerability_discovery_patch_proof_replay"
        in receipt["checked_standard_ids"]
    )
    assert (
        "std_microcosm_materials_chemistry_closed_loop_lab_safety_replay"
        in receipt["checked_standard_ids"]
    )
    assert "std_microcosm_agent_memory_temporal_conflict_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_sleeper_memory_poisoning_quarantine_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_mcp_tool_authority_replay" in receipt["checked_standard_ids"]
    assert (
        "std_microcosm_proof_derived_governed_mutation_authorization"
        in receipt["checked_standard_ids"]
    )
    assert "std_microcosm_belief_state_process_reward_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_durable_agent_work_landing_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_research_replication_rubric_artifact_replay" in receipt["checked_standard_ids"]
    assert "std_microcosm_world_model_projection_drift_control_room" in receipt["checked_standard_ids"]
    assert (
        "std_microcosm_spatial_world_model_counterfactual_simulation_replay"
        in receipt["checked_standard_ids"]
    )
    assert (
        "std_microcosm_mechanistic_interpretability_circuit_attribution_replay"
        in receipt["checked_standard_ids"]
    )
    assert "std_microcosm_tactic_portfolio_availability_probe" in receipt["checked_standard_ids"]
    assert "std_microcosm_standards_meta_diagnostics" in receipt["checked_standard_ids"]
    assert "std_microcosm_cold_reader_route_map" in receipt["checked_standard_ids"]
    assert "std_microcosm_first_screen_composition_root" in receipt["checked_standard_ids"]
    assert "std_microcosm_provider_context_recipe_budget_policy" in receipt["checked_standard_ids"]
    assert "std_microcosm_observatory_legibility" in receipt["checked_standard_ids"]
    assert receipt["duplicate_standard_ids"] == []
    assert receipt["missing_standard_files"] == []
    assert receipt["missing_required_fields_by_standard"] == {}
    assert set(receipt["acceptance_status"]["accepted_current_authority_organs"]) == accepted_ids
    assert receipt["acceptance_status"]["errors"] == []
    alignment = receipt["accepted_organ_standard_contract_alignment"]
    assert alignment["status"] == "pass"
    assert alignment["error_count"] == 0
    assert alignment["checked_standard_count"] >= 32
    assert "std_microcosm_agent_monitor_redteam_falsification_replay" in alignment[
        "checked_standard_ids"
    ]
    assert "std_microcosm_agent_sabotage_scheming_monitor_replay" in alignment[
        "checked_standard_ids"
    ]
    assert (
        "std_microcosm_spatial_world_model_counterfactual_simulation_replay"
        in alignment["checked_standard_ids"]
    )
    activation_gaps = receipt["activation_witness_gap_summary"]
    assert activation_gaps["schema_version"] == (
        "standard_activation_witness_gap_summary_v1"
    )
    assert activation_gaps["status"] == "computed"
    assert {row["standard_id"] for row in activation_gaps["details"]} == ENGINE_ROOM_STAGED_STANDARD_IDS
    assert activation_gaps["detail_count"] == len(ENGINE_ROOM_STAGED_STANDARD_IDS)
    assert activation_gaps["counts_by_gap_id"] == {
        "source_schema_not_public_microcosm_standard_v2": len(ENGINE_ROOM_STAGED_STANDARD_IDS),
        "source_status_not_active": len(ENGINE_ROOM_STAGED_STANDARD_IDS),
    }
    assert activation_gaps["counts_by_registry_status"] == {
        "staged_capsule_pending_shared_registry_integration": len(ENGINE_ROOM_STAGED_STANDARD_IDS),
    }
    assert activation_gaps["counts_by_source_status"] == {
        "staged_capsule_pending_shared_registry_integration": len(ENGINE_ROOM_STAGED_STANDARD_IDS),
    }
    assert "public_microcosm_standard_v1" not in (
        activation_gaps["counts_by_source_schema_version"]
    )
    assert (
        "does_not_activate_standards_or_promote_draft_contracts"
        in activation_gaps["authority_boundary"]
    )
    assert any(
        "does not flip source status" in claim
        for claim in activation_gaps["anti_claims"]
    )
    gaps_by_id = {
        row["standard_id"]: row for row in activation_gaps["details"]
    }
    assert "std_microcosm_axiom" not in gaps_by_id
    assert "std_microcosm_anti_claim" not in gaps_by_id
    assert "std_microcosm_private_fixture" not in gaps_by_id
    assert "std_microcosm_batch5_authority_systems_capsule" not in gaps_by_id
    assert "std_microcosm_batch7_demo_take_console_capsule" not in gaps_by_id
    assert "std_microcosm_batch7_oracle_sibling_capsule" not in gaps_by_id
    assert "std_microcosm_batch7_secondary_runtime_capsule" not in gaps_by_id
    assert "std_microcosm_agent_trace" not in gaps_by_id
    used_by_summary = receipt["used_by_organ_admission_summary"]
    assert used_by_summary["schema_version"] == (
        "standard_used_by_organ_admission_summary_v1"
    )
    assert used_by_summary["status"] == "computed"
    sources = {row["standard_id"]: json.loads((public_root / row["path"]).read_text())
               for row in registry["standards"]}
    declared_pairs = {
        (row["standard_id"], organ_id)
        for row in registry["standards"]
        for organ_id in set(row.get("used_by_organs", [])) | set(
            sources[row["standard_id"]].get("relationships", {}).get("used_by_organs", [])
        )
    }
    unresolved_pairs = {pair for pair in declared_pairs if pair[1] not in accepted_ids}
    resolved_count = len(declared_pairs - unresolved_pairs)
    unresolved_count = len(unresolved_pairs)
    assert {(row["standard_id"], row["target_organ_id"])
            for row in used_by_summary["unresolved_details"]} == unresolved_pairs
    assert used_by_summary["edge_count"] == len(declared_pairs)
    assert used_by_summary["resolved_edge_count"] == resolved_count
    assert used_by_summary["unresolved_edge_count"] == unresolved_count
    assert used_by_summary["detail_count"] == unresolved_count
    assert used_by_summary["unresolved_target_organ_count"] == len({pair[1] for pair in unresolved_pairs})
    assert used_by_summary["counts_by_admission_status"] == {
        "accepted_current_authority": resolved_count,
        "target_organ_not_accepted_current_authority": unresolved_count,
    }
    assert used_by_summary["counts_by_target_status"] == {
        "accepted_current_authority": resolved_count,
        "unresolved_json_instance": unresolved_count,
    }
    assert used_by_summary["unresolved_counts_by_contract_projection_status"] == dict(Counter(
        "active_v2_governed_json" if sources[standard_id]["schema_version"] == "public_microcosm_standard_v2"
        and sources[standard_id]["status"] == "active" else "legacy_or_draft_standard_contract"
        for standard_id, _organ_id in unresolved_pairs
    ))
    registry_by_id = {row["standard_id"]: row for row in registry["standards"]}
    assert used_by_summary["unresolved_counts_by_registry_status"] == dict(Counter(
        registry_by_id[standard_id]["status"] for standard_id, _organ_id in unresolved_pairs
    ))
    assert used_by_summary["unresolved_counts_by_source_status"] == dict(Counter(
        sources[standard_id]["status"] for standard_id, _organ_id in unresolved_pairs
    ))
    assert "std_microcosm_agent_trace" in used_by_summary["unresolved_standard_ids"]
    assert "std_microcosm_compression_band" not in used_by_summary[
        "unresolved_standard_ids"
    ]
    assert "option_surface" not in used_by_summary["unresolved_target_organ_ids"]
    assert "paper_module" not in used_by_summary["unresolved_target_organ_ids"]
    assert (
        "does_not_accept_organs_or_prove_runtime_use"
        in used_by_summary["authority_boundary"]
    )
    assert any(
        "does not accept organs" in claim
        for claim in used_by_summary["anti_claims"]
    )
    used_by_by_pair = {
        (row["standard_id"], row["target_organ_id"]): row
        for row in used_by_summary["unresolved_details"]
    }
    agent_trace_gap = used_by_by_pair[
        (
            "std_microcosm_agent_trace",
            "entry_agent_behavior_governance_suborgan",
        )
    ]
    assert agent_trace_gap["admission_status"] == (
        "target_organ_not_accepted_current_authority"
    )
    assert agent_trace_gap["target_status"] == "unresolved_json_instance"
    assert agent_trace_gap["contract_projection_status"] == (
        "active_v2_governed_json"
    )
    assert agent_trace_gap["claim_ceiling"] == (
        "standard_used_by_organ_admission_summary_is_reentry_metadata_"
        "not_usage_or_acceptance_proof"
    )
    first_screen_gap = used_by_by_pair[
        ("std_microcosm_first_screen_composition_root", "runtime_shell")
    ]
    assert first_screen_gap["contract_projection_status"] == "active_v2_governed_json"
    assert first_screen_gap["source_standard_status"] == "active"
    assert first_screen_gap["registry_status"] == "draft"
    assert receipt["acceptance_status"]["lean_lake_authorized"] == "bounded_public_witness_only"
    assert receipt["acceptance_status"]["release_authorized"] is False
    assert (
        registry["authority_ceiling"]["count_authority"]
        == "inventory_only_not_completeness_readiness_maturity_or_product_progress"
    )
    assert registry["authority_ceiling"]["standard_count_is_completeness_or_readiness"] is False
    assert registry["authority_ceiling"]["first_wave_required_count_is_product_progress"] is False
    assert registry["authority_ceiling"]["score_based_progress_authority"] is False
    assert "Standard counts and first-wave-required rows are inventory fields only" in registry["anti_claim"]
    assert (
        receipt["authority_ceiling"]["count_authority"]
        == "inventory_only_not_completeness_readiness_maturity_or_product_progress"
    )
    assert receipt["authority_ceiling"]["standard_count_is_completeness_or_readiness"] is False
    assert receipt["authority_ceiling"]["first_wave_required_count_is_product_progress"] is False
    assert receipt["authority_ceiling"]["score_based_progress_authority"] is False
    assert "not completeness, readiness, maturity, or score-based progress" in receipt["anti_claim"]
    assert receipt["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert receipt["secret_exclusion_scan"]["body_in_receipt"] is False
    assert "private_state_scan" not in receipt
    text = out.read_text(encoding="utf-8")
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    assert "matched_excerpt" not in _walk_keys(receipt)
    assert "body" not in _walk_keys(receipt)


@pytest.mark.parametrize("component,bundle,retained_count,omission_count,historical_count,classes", [
    ("public_reveal_walkthrough", "exported_public_reveal_bundle", 1, 4, 5, {"public_python_source_body": 1}),
    ("mcp_tool_authority_replay", "exported_mcp_tool_authority_bundle", 2, 5, 6, {"public_macro_standard_body": 2}),
])
def test_standard_source_body_floor_declares_current_manifest_only(
    component, bundle, retained_count, omission_count, historical_count, classes,
):
    from microcosm_core.organs import mcp_tool_authority_replay, public_reveal_walkthrough

    bundle_path = MICROCOSM_ROOT / "examples" / component / bundle
    manifest = json.loads((bundle_path / "source_module_manifest.json").read_text())
    standard = json.loads((MICROCOSM_ROOT / "standards" / f"std_microcosm_{component}.json").read_text())
    declared = standard["source_open_body_imports"]
    retained = {row["module_id"] for row in manifest["modules"]}
    omitted = {row["module_id"] for row in manifest["release_substitution_omissions"]}
    assert manifest["module_count"] == len(retained) == retained_count
    assert declared["status"] == "declared_current_export_inventory"
    assert declared["body_material_count"] == retained_count
    assert set(declared["body_material_ids"]) == retained
    assert declared["body_material_classes"] == classes
    assert declared["material_classes"] == sorted(classes)
    assert declared["release_omission_count"] == len(omitted) == omission_count
    assert set(declared["release_omission_ids"]) == omitted
    assert not retained & omitted
    assert declared["release_omission_ref"] == declared["source_manifest_refs"][0] + "::release_substitution_omissions"
    assert declared["body_in_receipt"] is False
    historical = standard["historical_source_open_body_imports"]
    assert historical["status"] == "historical_provenance_only"
    assert historical["body_material_count"] == len(historical["body_material_ids"]) == historical_count
    for row in manifest["modules"]:
        data = (bundle_path / row["path"]).read_bytes()
        assert "sha256:" + hashlib.sha256(data).hexdigest() == row["sha256"]
        assert row["body_copied"] is True and row["body_in_receipt"] is False
    if component == "mcp_tool_authority_replay":
        result = mcp_tool_authority_replay._source_module_manifest_result(
            bundle_path, public_root=MICROCOSM_ROOT, require_manifest=True, require_public_floor=True
        )
        runtime = mcp_tool_authority_replay._source_open_body_import_summary(result)
        assert standard["body_copied_material_count"] == retained_count
        verification = standard["body_import_verification"]
        assert verification["source_module_count"] == retained_count
        assert verification["verification_status"] == "declared_current_export_inventory"
        assert standard["historical_body_import_verification"]["recorded_verification"]["source_module_count"] == historical_count
    else:
        result = public_reveal_walkthrough._source_module_manifest_result(
            bundle_path, public_root=MICROCOSM_ROOT, require_manifest=True
        )
        runtime = public_reveal_walkthrough._source_open_body_import_summary(result)
    assert result["status"] == "pass", result
    assert runtime["body_material_count"] == declared["body_material_count"]
    assert set(runtime["body_material_ids"]) == retained
    assert runtime["body_material_classes"] == classes


def test_doctrine_roof_validator_ref_has_executable_route() -> None:
    standard = json.loads(
        (MICROCOSM_ROOT / "standards/std_microcosm_doctrine_roof.json").read_text(
            encoding="utf-8"
        )
    )
    routes = standard["validator_contract"]["executable_routes"]
    doctrine_roof_routes = [
        route
        for route in routes
        if route["validator_id"] == "validator.microcosm.doctrine_roof"
    ]

    assert len(doctrine_roof_routes) == 1
    route = doctrine_roof_routes[0]
    assert route["route_kind"] == "focused_pytest"
    assert route["command"] == (
        "PYTHONPATH=microcosm-substrate/src ./repo-pytest "
        "microcosm-substrate/tests/test_standards_registry.py -q"
    )
    assert "microcosm-substrate/src/microcosm_core/validators/standards_registry.py" in (
        route["evidence_refs"]
    )
    assert route["result_contract"] == (
        "pytest_exit_zero_and_standards_registry_receipt_status_pass"
    )
    assert route["authority_ceiling"]["release_authority"] is False
    assert route["authority_ceiling"]["source_body_authority"] is False


def test_engine_room_staged_standard_activation_boundaries_are_source_explicit() -> None:
    for standard_id in ENGINE_ROOM_STAGED_STANDARD_IDS:
        source = json.loads(
            (MICROCOSM_ROOT / "standards" / f"{standard_id}.json").read_text(
                encoding="utf-8"
            )
        )
        boundary = source["activation_boundary"]
        validator_contract = source["validator_contract"]
        receipt_contract = source["receipt_contract"]

        assert source["status"] == "staged_capsule_pending_shared_registry_integration"
        assert source["schema_version"] != "public_microcosm_standard_v2"
        assert source["relationships"]["used_by_organs"] == []
        assert source["relationships"]["registry_integration_status"] == (
            "inventory_only_registered_not_active_v2_promoted"
        )
        assert validator_contract["required"] is True
        assert validator_contract["validator_id"] in source["validator_refs"]
        assert "fixtures/first_wave/" in validator_contract["fixture_command"]
        assert "--json" in validator_contract["fixture_command"]
        assert receipt_contract["required"] is False
        assert receipt_contract["receipt_id"] is None
        assert boundary["status"] == "blocked_until_active_v2_admission"
        assert boundary["residual_pressure_ref"] == (
            "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
        )
        assert "fixture pass is not active v2 standard support" in (
            boundary["non_laundering_rules"]
        )
        assert (
            "empty used_by_organs is intentional until an organ or mechanism "
            "subject is admitted"
        ) in boundary["non_laundering_rules"]
        assert any(
            "aggregate doctrine-lattice projections" in step
            for step in boundary["required_reentry"]
        )
        assert "not active public runtime standard" in boundary["claim_ceiling"]


def test_agent_trace_used_by_organ_residual_boundary_is_source_explicit() -> None:
    source = json.loads(
        (MICROCOSM_ROOT / "standards/std_microcosm_agent_trace.json").read_text(
            encoding="utf-8"
        )
    )
    organ_registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    accepted_organs = {
        row["organ_id"]
        for row in organ_registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    }
    boundary = source["used_by_organ_boundary"]

    assert source["status"] == "active"
    assert source["schema_version"] == "public_microcosm_standard_v2"
    assert source["relationships"]["used_by_organs"] == [
        "agent_route_observability_runtime",
        "entry_agent_behavior_governance_suborgan",
    ]
    assert boundary["status"] == "typed_residual_until_target_organ_admitted"
    assert boundary["resolved_target_organs"] == [
        "agent_route_observability_runtime"
    ]
    assert boundary["unresolved_target_organs"] == [
        "entry_agent_behavior_governance_suborgan"
    ]
    assert "agent_route_observability_runtime" in accepted_organs
    assert "entry_agent_behavior_governance_suborgan" not in accepted_organs
    assert "active v2 standard status does not accept unresolved used_by_organs targets" in (
        boundary["non_laundering_rules"]
    )
    assert any(
        "accepted_current_authority" in step
        for step in boundary["required_reentry"]
    )
    assert any(
        "--check-standard-corpus" in step
        for step in boundary["required_reentry"]
    )
    assert "not usage, acceptance, runtime, release" in boundary["claim_ceiling"]
    assert boundary["residual_pressure_ref"] == (
        "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
    )


def test_active_v2_unresolved_used_by_organs_have_source_boundaries() -> None:
    organ_registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    accepted_organs = {
        row["organ_id"]
        for row in organ_registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    }
    standards_with_unresolved: dict[str, list[str]] = {}

    for standard_path in sorted((MICROCOSM_ROOT / "standards").glob("*.json")):
        source = json.loads(standard_path.read_text(encoding="utf-8"))
        if (
            source.get("schema_version") != "public_microcosm_standard_v2"
            or source.get("status") != "active"
        ):
            continue

        used_by_organs = source.get("relationships", {}).get("used_by_organs") or []
        resolved_targets = [
            organ_id for organ_id in used_by_organs if organ_id in accepted_organs
        ]
        unresolved_targets = [
            organ_id for organ_id in used_by_organs if organ_id not in accepted_organs
        ]
        if not unresolved_targets:
            continue

        standard_id = source["standard_id"]
        boundary = source.get("used_by_organ_boundary")
        assert boundary, standard_id
        standards_with_unresolved[standard_id] = unresolved_targets

        assert boundary["status"] in {
            "typed_residual_until_target_organ_admitted",
            "typed_residual_until_target_organs_admitted",
        }
        assert boundary["resolved_target_organs"] == resolved_targets
        assert boundary["unresolved_target_organs"] == unresolved_targets
        assert any(
            "accepted_current_authority" in step
            for step in boundary["required_reentry"]
        )
        assert any(
            "--check-standard-corpus" in step
            for step in boundary["required_reentry"]
        )
        assert any(
            "does not accept unresolved used_by_organs targets" in rule
            for rule in boundary["non_laundering_rules"]
        )
        assert any(
            "runtime invocation or organ admission proof" in rule
            for rule in boundary["non_laundering_rules"]
        )
        assert "not usage, acceptance, runtime, release" in boundary["claim_ceiling"]
        assert boundary["residual_pressure_ref"] == (
            "cap_quick_doctrine_lattice_full_population_vision_e1fa6d8fd00f"
        )

    assert len(standards_with_unresolved) == 17
    assert sum(len(targets) for targets in standards_with_unresolved.values()) == 23
    assert standards_with_unresolved["std_microcosm_agent_trace"] == [
        "entry_agent_behavior_governance_suborgan"
    ]
    assert standards_with_unresolved["std_microcosm_authority_boundary"] == [
        "external_boundary_anti_corruption_runtime"
    ]


def test_compression_band_used_by_organs_excludes_kind_targets() -> None:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/standards_registry.json").read_text(encoding="utf-8")
    )
    source = json.loads(
        (MICROCOSM_ROOT / "standards/std_microcosm_compression_band.json").read_text(
            encoding="utf-8"
        )
    )
    registry_row = next(
        row
        for row in registry["standards"]
        if row["standard_id"] == "std_microcosm_compression_band"
    )
    expected_organs = ["navigation_hologram_route_plane"]

    assert source["relationships"]["used_by_organs"] == expected_organs
    assert registry_row["used_by_organs"] == expected_organs
    assert source["used_by_organ_boundary"]["status"] == (
        "source_cleaned_no_unresolved_used_by_organs_targets"
    )
    assert source["used_by_organ_boundary"]["resolved_target_organs"] == expected_organs
    assert source["used_by_organ_boundary"]["unresolved_target_organs"] == []
    assert "option_surface and paper_module are kind targets" in (
        source["used_by_organ_boundary"]["source_cleanup_note"]
    )
    assert any(
        "accepted_current_authority organ id rather than a kind id" in step
        for step in source["used_by_organ_boundary"]["required_reentry"]
    )
    assert "option_surface" not in registry_row["used_by_organs"]
    assert "paper_module" not in registry_row["used_by_organs"]


def test_workingness_record_used_by_organs_excludes_cold_clone_probe_route_target() -> None:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/standards_registry.json").read_text(encoding="utf-8")
    )
    source = json.loads(
        (
            MICROCOSM_ROOT / "standards/std_microcosm_workingness_record.json"
        ).read_text(encoding="utf-8")
    )
    registry_row = next(
        row
        for row in registry["standards"]
        if row["standard_id"] == "std_microcosm_workingness_record"
    )
    expected_organs = ["proof_diagnostic_evidence_spine"]

    assert source["relationships"]["used_by_organs"] == expected_organs
    assert registry_row["used_by_organs"] == expected_organs
    assert source["used_by_organ_boundary"]["status"] == (
        "source_cleaned_no_unresolved_used_by_organs_targets"
    )
    assert source["used_by_organ_boundary"]["resolved_target_organs"] == expected_organs
    assert source["used_by_organ_boundary"]["unresolved_target_organs"] == []
    assert "cold_clone_probe is a paper-module, mechanism, and bootstrap route target" in (
        source["used_by_organ_boundary"]["source_cleanup_note"]
    )
    assert any(
        "accepted_current_authority organ id" in step
        for step in source["used_by_organ_boundary"]["required_reentry"]
    )
    assert "cold_clone_probe" not in registry_row["used_by_organs"]


def test_lean_toolchain_receipt_used_by_organs_excludes_cold_clone_probe_route_target() -> None:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/standards_registry.json").read_text(encoding="utf-8")
    )
    source = json.loads(
        (
            MICROCOSM_ROOT / "standards/std_microcosm_lean_toolchain_receipt.json"
        ).read_text(encoding="utf-8")
    )
    registry_row = next(
        row
        for row in registry["standards"]
        if row["standard_id"] == "std_microcosm_lean_toolchain_receipt"
    )
    expected_organs = [
        "formal_math_lean_proof_witness",
        "proof_diagnostic_evidence_spine",
    ]

    assert source["relationships"]["used_by_organs"] == expected_organs
    assert registry_row["used_by_organs"] == expected_organs
    assert source["used_by_organ_boundary"]["status"] == (
        "source_cleaned_no_unresolved_used_by_organs_targets"
    )
    assert source["used_by_organ_boundary"]["resolved_target_organs"] == expected_organs
    assert source["used_by_organ_boundary"]["unresolved_target_organs"] == []
    assert "cold_clone_probe is a paper-module, mechanism, and bootstrap route target" in (
        source["used_by_organ_boundary"]["source_cleanup_note"]
    )
    assert any(
        "accepted_current_authority organ id" in step
        for step in source["used_by_organ_boundary"]["required_reentry"]
    )
    assert "cold_clone_probe" not in registry_row["used_by_organs"]


def test_standard_contract_basis_matches_accepted_organ_evidence_classes() -> None:
    organ_registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    accepted_organs = {
        row["organ_id"]: row
        for row in organ_registry["implemented_organs"]
        if row["status"] == "accepted_current_authority"
    }
    required_basis_keys = {
        "organ_evidence_class": "evidence_class",
        "organ_evidence_strength_rank": "evidence_strength_rank",
        "truth_accounting_bucket": "truth_accounting_bucket",
    }
    checked_standard_ids: set[str] = set()

    for standard_path in sorted((MICROCOSM_ROOT / "standards").glob("*.json")):
        source = json.loads(standard_path.read_text(encoding="utf-8"))
        basis = source.get("standard_payload", {}).get("contract_projection_basis", {})
        if not any(key in basis for key in required_basis_keys):
            continue
        standard_id = source["standard_id"]
        organ = accepted_organs[source["kind_id"]]
        checked_standard_ids.add(standard_id)
        for basis_key, organ_key in required_basis_keys.items():
            assert basis[basis_key] == organ[organ_key], (standard_id, basis_key)

    assert "std_microcosm_agent_monitor_redteam_falsification_replay" in checked_standard_ids
    assert "std_microcosm_agent_sabotage_scheming_monitor_replay" in checked_standard_ids
    assert "std_microcosm_spatial_world_model_counterfactual_simulation_replay" in checked_standard_ids


def test_standards_registry_rejects_accepted_organ_label_drift(tmp_path: Path) -> None:
    public_root = _copy_public_standards_tree(tmp_path)
    registry_path = public_root / "core/standards_registry.json"
    standard_path = (
        public_root
        / "standards/std_microcosm_spatial_world_model_counterfactual_simulation_replay.json"
    )
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    standard = json.loads(standard_path.read_text(encoding="utf-8"))

    for row in registry["standards"]:
        if row["standard_id"] == "std_microcosm_spatial_world_model_counterfactual_simulation_replay":
            row["status"] = "draft"
            break
    standard["source_authority"] = "json_is_contract_markdown_is_projection"
    standard["standard_payload"]["contract_projection_basis"][
        "runtime_acceptance_status"
    ] = "active_source_body_import"
    standard["runtime_acceptance_refs"]["registry_status"] = "draft"
    registry_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    standard_path.write_text(
        json.dumps(standard, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    receipt = validate_standards_registry(
        registry_path,
        public_root / "standards",
        public_root / "core/acceptance/first_wave_acceptance.json",
        public_root / "receipts/first_wave/standards_registry_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    alignment = receipt["accepted_organ_standard_contract_alignment"]
    assert alignment["status"] == "blocked"
    error_codes = {
        row["code"]
        for row in alignment["errors"]
        if row["standard_id"] == "std_microcosm_spatial_world_model_counterfactual_simulation_replay"
    }
    assert {
        "registry_status_not_accepted_for_organ_backed_standard",
        "source_authority_not_organ_registry_backed",
        "basis_runtime_acceptance_status_not_organ_registry_backed",
        "runtime_acceptance_refs_registry_status_not_accepted",
    } <= error_codes


def test_authority_boundary_manifest_demotes_overread_claims() -> None:
    manifest = json.loads(
        (MICROCOSM_ROOT / "core/authority_boundary.json").read_text(encoding="utf-8")
    )
    standard = json.loads(
        (MICROCOSM_ROOT / "standards/std_microcosm_authority_boundary.json").read_text(
            encoding="utf-8"
        )
    )

    payload = manifest["authority_boundary_payload"]
    denied = payload["denied_authority"]

    assert payload["surface_role"] == "root_public_private_boundary_manifest_read_model"
    assert payload["reader_action"].startswith("Use this manifest to reject overbroad")
    assert denied["complete_secret_detection_claim"] is False
    assert denied["private_data_equivalence_claim"] is False
    assert denied["release_authorized"] is False
    assert denied["source_mutation_authorized"] is False
    assert denied["score_based_progress_authority"] is False
    assert denied["whole_system_correctness_claim"] is False
    assert any("passing scan or receipt" in guard for guard in payload["overread_guard"])
    assert "complete secret detection" in manifest["anti_claim"]
    assert "authority_boundary_payload" in standard["required_fields"]
    assert any(
        "authority_boundary_payload.denied_authority" in rule
        for rule in standard["validation_rules"]
    )
    assert any("complete secret audit" in claim for claim in standard["anti_claims"])


def test_first_screen_composition_root_demotes_evidence_counts_to_accounting() -> None:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/standards_registry.json").read_text(encoding="utf-8")
    )
    standard = json.loads(
        (
            MICROCOSM_ROOT
            / "standards/std_microcosm_first_screen_composition_root.json"
        ).read_text(encoding="utf-8")
    )

    rows = {
        str(row.get("standard_id")): row
        for row in registry.get("standards", [])
        if isinstance(row, dict)
    }
    row = rows["std_microcosm_first_screen_composition_root"]

    assert row["kind_id"] == "first_screen_composition_root"
    assert row["path"] == "standards/std_microcosm_first_screen_composition_root.json"
    assert "cold_reader_route_map" in row["used_by_organs"]
    assert "public_reveal_walkthrough" in row["used_by_organs"]
    assert "runtime_shell" in row["used_by_organs"]
    assert "runtime_shell" in standard["relationships"]["used_by_organs"]
    assert standard["authority_ceiling"]["count_authority"] == (
        "evidence_accounting_only_not_maturity_score"
    )
    assert standard["authority_ceiling"]["score_based_progress_authority"] is False
    assert standard["authority_ceiling"]["release_authority"] is False
    assert standard["authority_ceiling"]["reader_success_authority"] is False
    allowed_public_inputs = standard["public_private_boundary"][
        "allowed_public_inputs"
    ]
    source_ref_paths = {row["path"] for row in standard["source_refs"]}
    assert "public organ atlas upstream rows" in allowed_public_inputs
    assert "public agent-task-route organ-glance one-line projection" in (
        allowed_public_inputs
    )
    assert "core/organ_atlas.json" in source_ref_paths
    assert "atlas/agent_task_routes.json" in source_ref_paths
    assert "microcosm tour --card <project>" in standard["validation_rules"][0]
    assert any("accounting" in claim for claim in standard["anti_claims"])
    assert "first_screen_composition_root" in standard["paper_module_contract"]["module_slug"]


def test_concept_and_mechanism_standards_bind_agent_entry() -> None:
    concept = json.loads(
        (MICROCOSM_ROOT / "standards/std_microcosm_concept.json").read_text(
            encoding="utf-8"
        )
    )
    mechanism = json.loads(
        (MICROCOSM_ROOT / "standards/std_microcosm_mechanism.json").read_text(
            encoding="utf-8"
        )
    )
    pressure = json.loads(
        (MICROCOSM_ROOT / "core/public_standard_pressure.json").read_text(
            encoding="utf-8"
        )
    )
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )
    pressure_by_id = {
        row["standard_id"]: row
        for row in pressure["rows"]
        if isinstance(row, dict)
    }
    population_specimens = entry_packet["concept_mechanism_entry_route"][
        "population_specimens"
    ]

    assert concept["entry_surface_contract"]["agent_entry_ref"] == (
        "AGENTS.md::Concept And Mechanism Entry"
    )
    assert concept["entry_surface_contract"]["first_screen_ref"] == (
        "microcosm first-screen <project>::doctrine_effect_frame"
    )
    assert "entry_surface_contract" in concept["required_fields"]
    assert "population_specimen_contract" in concept["required_fields"]
    assert "activation_receipt_contract" in concept["required_fields"]
    assert concept["population_specimen_contract"]["loop_ref"] == (
        "atlas/entry_packet.json::concept_mechanism_entry_route.population_specimens"
    )
    assert concept["activation_receipt_contract"]["loop_ref"] == (
        "atlas/entry_packet.json::concept_mechanism_entry_route.activation_receipts"
    )
    assert concept["population_specimen_contract"]["minimum_specimen_count"] <= len(
        population_specimens
    )
    assert "mechanism_pair_ref" in concept["population_specimen_contract"][
        "row_must_bind"
    ]
    assert any(
        source_ref.get("path") == "AGENTS.md"
        for source_ref in concept["source_refs"]
        if isinstance(source_ref, dict)
    )
    assert (
        "concept_handle_requires_entry_surface"
        in pressure_by_id
    )
    assert pressure_by_id["concept_handle_requires_entry_surface"][
        "runtime_hook"
    ] == "first_screen_composition.doctrine_effect_frame"

    assert mechanism["entry_surface_contract"]["agent_entry_ref"] == (
        "AGENTS.md::Concept And Mechanism Entry"
    )
    assert mechanism["entry_surface_contract"]["first_screen_ref"] == (
        "microcosm first-screen <project>::doctrine_effect_frame"
    )
    assert "entry_surface_contract" in mechanism["required_fields"]
    assert "population_specimen_contract" in mechanism["required_fields"]
    assert "activation_receipt_contract" in mechanism["required_fields"]
    assert mechanism["population_specimen_contract"]["loop_ref"] == (
        "atlas/entry_packet.json::concept_mechanism_entry_route.population_specimens"
    )
    assert mechanism["activation_receipt_contract"]["loop_ref"] == (
        "atlas/entry_packet.json::concept_mechanism_entry_route.activation_receipts"
    )
    assert mechanism["population_specimen_contract"][
        "minimum_specimen_count"
    ] <= len(population_specimens)
    assert "transformation_shape" in mechanism["population_specimen_contract"][
        "row_must_bind"
    ]
    assert any(
        source_ref.get("path") == "AGENTS.md"
        for source_ref in mechanism["source_refs"]
        if isinstance(source_ref, dict)
    )
    assert (
        "mechanism_handle_requires_runnable_contract"
        in pressure_by_id
    )
    assert (
        "microcosm executable-doctrine-grammar validate-standards-bundle"
        in pressure_by_id["mechanism_handle_requires_runnable_contract"][
            "route_refs"
        ]
    )
    assert "concept_mechanism_requires_population_specimen_loop" in pressure_by_id
    assert (
        "atlas/entry_packet.json::concept_mechanism_entry_route.population_specimens"
        in pressure_by_id["concept_mechanism_requires_population_specimen_loop"][
            "route_refs"
        ]
    )
    assert "concept_mechanism_requires_activation_receipt_loop" in pressure_by_id
    assert (
        "atlas/entry_packet.json::concept_mechanism_entry_route.activation_receipts"
        in pressure_by_id["concept_mechanism_requires_activation_receipt_loop"][
            "route_refs"
        ]
    )
    assert "concept_mechanism_projection_consumers_preserve_loop_fields" in pressure_by_id
    projection_pressure = pressure_by_id[
        "concept_mechanism_projection_consumers_preserve_loop_fields"
    ]
    assert (
        "atlas/entry_packet.json::concept_mechanism_entry_route.projection_consumers"
        in projection_pressure["route_refs"]
    )
    assert (
        "python -m microcosm_core.projections.concept_mechanism_read_model"
        in projection_pressure["route_refs"]
    )


def test_concept_mechanism_population_specimens_bind_to_runnable_lanes() -> None:
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )
    route = entry_packet["concept_mechanism_entry_route"]
    specimens = route["population_specimens"]
    activation_receipts = route["activation_receipts"]
    projection_consumers = route["projection_consumers"]
    specimen_by_id = {row["specimen_id"]: row for row in specimens}

    assert set(specimen_by_id) >= {
        "first_screen_doctrine_effect_frame",
        "executable_doctrine_grammar_standard_bundle",
        "standards_meta_diagnostics_bundle",
        "voice_to_doctrine_self_improvement_loop_bundle",
    }
    assert route["population_loop"]["build_new_threshold"].startswith(
        "do not create a parallel concept index"
    )
    assert (
        "core/public_standard_pressure.json::concept_mechanism_requires_activation_receipt_loop"
        in route["population_loop"]["pressure_refs"]
    )
    assert route["population_loop"]["pressure_refs"][-1] == (
        "core/public_standard_pressure.json::concept_mechanism_projection_consumers_preserve_loop_fields"
    )
    assert any(
        command.startswith("microcosm first-screen --full")
        for command in route["validation_commands"]
    )
    assert any(
        "microcosm_core.validators.concept_mechanism_population" in command
        for command in route["validation_commands"]
    )
    assert any(
        "microcosm_core.projections.concept_mechanism_read_model" in command
        for command in route["validation_commands"]
    )

    for specimen in specimens:
        concept_binding = specimen["concept_binding"]
        mechanism_binding = specimen["mechanism_binding"]

        assert concept_binding["concept_role"] != mechanism_binding["mechanism_role"]
        assert concept_binding["payload_shape_ref"]
        assert concept_binding["relationship_shape"]
        assert "glossary" in concept_binding["anti_glossary_rule"]
        assert mechanism_binding["transformation_shape"]
        assert mechanism_binding["state_or_proof_effect"]
        assert "feature prose" in mechanism_binding["anti_feature_prose_rule"]
        assert mechanism_binding["concept_pair_ref"] == (
            f"{specimen['specimen_id']}.concept_binding"
        )
        assert specimen["source_refs"]
        assert specimen["validator_refs"]
        assert specimen["anti_claims"]
        assert specimen["omission_receipt"]["drilldown"]

    assert any(
        "test_executable_doctrine_grammar_accepts_exported_standards_bundle" in ref
        for ref in specimen_by_id[
            "executable_doctrine_grammar_standard_bundle"
        ]["validator_refs"]
    )
    assert any(
        "test_standards_meta_diagnostics_bundle_validates_runtime_shape" in ref
        for ref in specimen_by_id["standards_meta_diagnostics_bundle"][
            "validator_refs"
        ]
    )
    assert any(
        "test_voice_to_doctrine_exported_bundle_validates_runtime_shape" in ref
        for ref in specimen_by_id[
            "voice_to_doctrine_self_improvement_loop_bundle"
        ]["validator_refs"]
    )

    activation_by_id = {row["receipt_id"]: row for row in activation_receipts}
    activation = activation_by_id[
        "concept_index_frontend_view_compiler_projection_guard_2026_05_27"
    ]
    assert activation["pressure_id"] == (
        "cap_quick_concept_index_frontend_view_compiler_sub_d34cd121c080"
    )
    assert activation["selected_specimen_id"] == "voice_to_doctrine_self_improvement_loop_bundle"
    assert activation["residual_disposition"] == "redirected_to_projection_consumer"
    assert "parallel concept index" in activation["authority_boundary"].replace("_", " ")
    assert "population_specimens" in activation["reentry_condition"]
    assert activation["concept_binding"]["mechanism_pair_ref"] == (
        "concept_index_frontend_view_compiler_projection_guard_2026_05_27.mechanism_binding"
    )
    assert activation["mechanism_binding"]["concept_pair_ref"] == (
        "concept_index_frontend_view_compiler_projection_guard_2026_05_27.concept_binding"
    )

    consumer_by_id = {row["consumer_id"]: row for row in projection_consumers}
    consumer = consumer_by_id["frontend_view_compiler_concept_mechanism_read_model"]
    assert consumer["source_route_ref"] == (
        "atlas/entry_packet.json::concept_mechanism_entry_route"
    )
    assert set(consumer["input_refs"]) >= {
        "atlas/entry_packet.json::concept_mechanism_entry_route.population_specimens",
        "atlas/entry_packet.json::concept_mechanism_entry_route.activation_receipts",
    }
    assert "concept_binding" in consumer["preserved_fields"]
    assert "mechanism_binding" in consumer["preserved_fields"]
    assert "validator_refs" in consumer["preserved_fields"]
    assert "receipt_refs" in consumer["preserved_fields"]
    assert "parallel concept index" in consumer["authority_boundary"].replace("_", " ")
    assert "independent concept inventory" in consumer["reentry_condition"]
    assert consumer["consumer_receipt"]["receipt_id"] == (
        "frontend_view_compiler_concept_mechanism_read_model_2026_05_27"
    )
    assert consumer["residual_disposition"] == (
        "consumer_read_model_bound_frontend_implementation_still_bounded"
    )


def test_standards_registry_rejects_duplicate_standard_ids(tmp_path: Path) -> None:
    public_root = _copy_public_standards_tree(tmp_path)
    registry_path = public_root / "core/standards_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["standards"].append(dict(registry["standards"][0]))
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    receipt = validate_standards_registry(
        registry_path,
        public_root / "standards",
        public_root / "core/acceptance/first_wave_acceptance.json",
        public_root / "receipts/first_wave/standards_registry_validation.json",
        command="pytest",
    )

    assert receipt["status"] == "blocked"
    assert registry["standards"][0]["standard_id"] in receipt["duplicate_standard_ids"]
