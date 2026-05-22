from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.validators.acceptance import (
    EXPORTED_ASSIMILATION_BUNDLE_RECEIPT_PATH,
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    run_assimilation_bundle,
    validate_pattern_assimilation,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
ASSIMILATION_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/pattern_assimilation_step/input"
ASSIMILATION_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/pattern_assimilation_step/exported_assimilation_bundle"
)


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


def _field_floor() -> dict[str, list[str]]:
    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "core/fixture_manifests/pattern_assimilation_step.fixture_manifest.json"
        ).read_text(encoding="utf-8")
    )
    return manifest["validator_contract_ratchet_v1"]["per_output_receipt_field_floor"]


def _read_last_jsonl(path: Path, *, run_id: str) -> dict[str, Any]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    matches = [row for row in rows if row.get("run_id") == run_id]
    assert matches
    return matches[-1]


def test_pattern_assimilation_step_observes_required_negative_cases(tmp_path: Path) -> None:
    live_macro = (
        MICROCOSM_ROOT.parent
        / "state/microcosm_portfolio/reconstruction/macro_pattern_autonomy_process_runs_v1.jsonl"
    )
    before = live_macro.read_text(encoding="utf-8") if live_macro.exists() else None
    result = validate_pattern_assimilation(
        ASSIMILATION_FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/pattern_assimilation_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["closeout_contract"]["missing_closeout_count"] == 1
    assert result["closeout_contract"]["refinement_count"] == 1
    assert result["closeout_contract"]["typed_nothing_to_refine_count"] == 1
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]
    after = live_macro.read_text(encoding="utf-8") if live_macro.exists() else None
    assert after == before


def test_pattern_assimilation_receipts_are_public_relative_and_redacted(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/pattern_assimilation_step",
        public_root / "fixtures/first_wave/pattern_assimilation_step",
    )
    result = validate_pattern_assimilation(
        public_root / "fixtures/first_wave/pattern_assimilation_step/input",
        public_root / "receipts/first_wave/pattern_assimilation_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == EXPECTED_RECEIPT_PATHS
    for receipt_path in EXPECTED_RECEIPT_PATHS[:2]:
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "/private/var" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["private_state_scan"]["blocking_hit_count"] == 0
        assert payload["missing_negative_cases"] == []
        assert set(payload["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
    macro_row = _read_last_jsonl(
        tmp_path / "state/microcosm_portfolio/reconstruction/macro_pattern_autonomy_process_runs_v1.jsonl",
        run_id="public_pattern_assimilation_step_current_authority",
    )
    assert macro_row["status"] == "pass"
    assert macro_row["private_state_scan"]["body_redacted"] is True


def test_pattern_assimilation_receipts_satisfy_macro_field_floor(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/pattern_assimilation_step",
        public_root / "fixtures/first_wave/pattern_assimilation_step",
    )
    validate_pattern_assimilation(
        public_root / "fixtures/first_wave/pattern_assimilation_step/input",
        public_root / "receipts/first_wave/pattern_assimilation_acceptance.json",
        command="pytest",
    )

    for receipt_path, required_fields in _field_floor().items():
        if receipt_path.endswith(".jsonl"):
            payload = _read_last_jsonl(
                tmp_path / receipt_path,
                run_id="public_pattern_assimilation_step_current_authority",
            )
        else:
            payload = json.loads((public_root / receipt_path).read_text(encoding="utf-8"))
        missing = [field for field in required_fields if field not in payload]
        assert missing == []


def test_pattern_assimilation_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_assimilation_bundle(
        ASSIMILATION_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/pattern_assimilation_step",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_assimilation_bundle"
    assert result["bundle_id"] == "public_pattern_assimilation_step_runtime_example"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["metadata_projection_not_live_learning_authority"] is True
    assert result["authority_ceiling"]["raw_seed_body_read"] is False
    assert result["authority_ceiling"]["live_task_ledger_mutation_authorized"] is False
    assert result["authority_ceiling"]["global_doctrine_promotion_authorized"] is False
    assert result["authority_ceiling"]["release_or_publication_authorized"] is False
    assert result["authority_ceiling"]["provider_payload_read"] is False
    assert result["authority_ceiling"]["private_data_equivalence_claim"] is False
    assert result["ordered_adapter_lane_status"] == (
        "complete_with_formal_math_lean_std_premise_index_verifier_trace_repair_evidence_cell_tactic_ring2_benchmark_integrity_durable_work_landing_research_replication_world_model_projection_drift_spatial_world_model_simulation_mechanistic_interpretability_provider_context_prediction_standards_meta_cold_reader_route_map_monitor_redteam_sabotage_monitor_memory_conflict_sleeper_memory_quarantine_mcp_tool_authority_governed_mutation_authorization_belief_state_process_reward_sandbox_policy_escape_indirect_prompt_injection_and_agentic_vulnerability_patch_proof_bound"
    )
    assert result["organ_landing_count"] == 41
    assert result["landed_organ_ids"] == [
        "agent_benchmark_integrity_anti_gaming_replay",
        "agent_memory_temporal_conflict_replay",
        "agent_monitor_redteam_falsification_replay",
        "agent_route_observability_runtime",
        "agent_sabotage_scheming_monitor_replay",
        "agent_sandbox_policy_escape_replay",
        "agentic_vulnerability_discovery_patch_proof_replay",
        "belief_state_process_reward_replay",
        "cold_reader_route_map",
        "corpus_readiness_mathlib_absence_gate",
        "durable_agent_work_landing_replay",
        "executable_doctrine_grammar",
        "formal_evidence_cell_anchor_resolver",
        "formal_math_lean_proof_witness",
        "formal_math_premise_retrieval",
        "formal_math_readiness_gate",
        "formal_math_verifier_trace_repair_loop",
        "indirect_prompt_injection_information_flow_policy_replay",
        "lean_std_premise_index",
        "macro_projection_import_protocol",
        "mathematical_strategy_atlas_hypothesis_scorer",
        "mcp_tool_authority_replay",
        "mechanistic_interpretability_circuit_attribution_replay",
        "mission_transaction_work_spine",
        "navigation_hologram_route_plane",
        "pattern_assimilation_step",
        "pattern_binding_contract",
        "prediction_oracle_reconciliation",
        "proof_derived_governed_mutation_authorization",
        "proof_diagnostic_evidence_spine",
        "provider_context_recipe_budget_policy",
        "public_reveal_walkthrough",
        "research_replication_rubric_artifact_replay",
        "ring2_premise_retrieval_precision_recall_harness",
        "sleeper_memory_poisoning_quarantine_replay",
        "spatial_world_model_counterfactual_simulation_replay",
        "standards_meta_diagnostics",
        "tactic_portfolio_availability_probe",
        "target_shape_tactic_routing_gate",
        "undeclared_library_prior_symbol_classifier",
        "world_model_projection_drift_control_room",
    ]
    assert result["refinement_receipt_count"] == 36
    assert result["nothing_to_refine_receipt_count"] == 2
    assert result["stewardship_check_count"] == 2
    assert result["reentry_condition_count"] == 2
    assert result["next_best_lane_result"] == (
        "computer_use_action_trace_replay_compound"
    )
    assert result["next_seed_paths"] == [
        "state/meta_missions/type_a_autonomous_seed_loop/seeds/microcosm_substrate_flagship_population_autonomous_seed.json"
    ]
    assert result["assimilation_policy"]["forbidden_authority_rejected"] is True
    assert all(not Path(path).is_absolute() for path in result["public_replacement_refs"])


def test_pattern_assimilation_exported_bundle_receipt_is_public_safe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/pattern_assimilation_step",
        public_root / "examples/pattern_assimilation_step",
    )

    result = run_assimilation_bundle(
        public_root / "examples/pattern_assimilation_step/exported_assimilation_bundle",
        public_root / "receipts/first_wave/pattern_assimilation_step",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [EXPORTED_ASSIMILATION_BUNDLE_RECEIPT_PATH]
    receipt_file = public_root / EXPORTED_ASSIMILATION_BUNDLE_RECEIPT_PATH
    assert receipt_file.is_file()
    text = receipt_file.read_text(encoding="utf-8")
    assert str(public_root) not in text
    assert "/Users/" not in text
    assert "/private/var" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
    payload = json.loads(text)
    assert payload["status"] == "pass"
    assert payload["input_mode"] == "exported_assimilation_bundle"
    assert payload["fixture_regression_required_elsewhere"] is True
    assert payload["private_state_scan"]["body_redacted"] is True
    assert payload["private_state_scan"]["blocking_hit_count"] == 0
    assert payload["expected_negative_cases"] == {}
    assert payload["metadata_projection_not_live_learning_authority"] is True
    assert payload["authority_ceiling"]["private_data_equivalence_claim"] is False
    assert payload["authority_ceiling"]["behavior_change_overclaims_allowed"] is False
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
    for hit in payload["private_state_scan"]["hits"]:
        assert hit["body_redacted"] is True
        assert not Path(hit["path"]).is_absolute()
