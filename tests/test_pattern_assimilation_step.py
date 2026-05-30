from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.validators.acceptance import (
    EXPORTED_ASSIMILATION_BUNDLE_RECEIPT_PATH,
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    _load_jsonl,
    _write_jsonl_upsert,
    run_assimilation_bundle,
    validate_pattern_assimilation,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
ASSIMILATION_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/pattern_assimilation_step/input"
ASSIMILATION_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/pattern_assimilation_step/exported_assimilation_bundle"
)
PATTERN_SOURCE_MODULE_IDS = {
    "macro_pattern_autonomy_process_contract_body_import",
    "macro_pattern_assimilation_fixture_manifest_body_import",
    "pattern_assimilation_retracted_adapter_receipt_body_import",
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


def test_pattern_assimilation_jsonl_loader_streams_without_materializing_file(
    tmp_path: Path, monkeypatch
) -> None:
    jsonl_path = tmp_path / "organ_landing_summaries.jsonl"
    jsonl_path.write_text(
        '{"run_id":"run_001","status":"pass"}\n'
        '["skip non-object rows"]\n'
        "\n"
        '{"run_id":"run_002","status":"fail"}\n',
        encoding="utf-8",
    )
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == jsonl_path:
            raise AssertionError("pattern assimilation JSONL loader should stream rows")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert _load_jsonl(jsonl_path) == [
        {"run_id": "run_001", "status": "pass"},
        {"run_id": "run_002", "status": "fail"},
    ]


def test_pattern_assimilation_jsonl_upsert_streams_existing_rows(
    tmp_path: Path, monkeypatch
) -> None:
    jsonl_path = tmp_path / "macro_pattern_autonomy_process_runs_v1.jsonl"
    jsonl_path.write_text(
        '{"run_id":"keep","status":"pass"}\n'
        '{"run_id":"replace","status":"old"}\n'
        "not json\n",
        encoding="utf-8",
    )
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == jsonl_path:
            raise AssertionError("pattern assimilation JSONL upsert should stream rows")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    _write_jsonl_upsert(
        jsonl_path,
        {"run_id": "replace", "status": "new"},
        run_id="replace",
    )

    rows = [
        json.loads(line)
        for line in original_read_text(jsonl_path, encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows == [
        {"run_id": "keep", "status": "pass"},
        {"run_id": "replace", "status": "new"},
    ]


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
    shutil.copytree(
        MICROCOSM_ROOT / "examples/pattern_assimilation_step",
        public_root / "examples/pattern_assimilation_step",
    )
    validate_pattern_assimilation(
        public_root / "fixtures/first_wave/pattern_assimilation_step/input",
        public_root / "receipts/first_wave/pattern_assimilation_acceptance.json",
        command="pytest",
    )
    run_assimilation_bundle(
        public_root / "examples/pattern_assimilation_step/exported_assimilation_bundle",
        public_root / "receipts/first_wave/pattern_assimilation_step",
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
        "complete_with_formal_math_lean_std_premise_index_verifier_trace_repair_evidence_cell_tactic_ring2_benchmark_integrity_durable_work_landing_research_replication_world_model_projection_drift_spatial_world_model_simulation_materials_lab_safety_mechanistic_interpretability_provider_context_prediction_standards_meta_cold_reader_route_map_monitor_redteam_sabotage_monitor_memory_conflict_sleeper_memory_quarantine_mcp_tool_authority_governed_mutation_authorization_belief_state_process_reward_sandbox_policy_escape_indirect_prompt_injection_agentic_vulnerability_patch_proof_and_materials_lab_safety_bound"
    )
    assert result["organ_landing_count"] == len(
        result["accepted_adapter_backed_organ_ids"]
    )
    assert result["current_adapter_backed_coverage_status"] in {
        "pass",
        "snapshot_delta",
    }
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
        "materials_chemistry_closed_loop_lab_safety_replay",
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
        "verifier_lab_kernel",
        "world_model_projection_drift_control_room",
    ]
    assert result["refinement_receipt_count"] == 37
    assert result["nothing_to_refine_receipt_count"] == 2
    assert result["stewardship_check_count"] == 2
    assert result["reentry_condition_count"] == 2
    assert result["next_best_lane_result"] == "runtime_hook_shadow_intervention_coverage"
    assert result["next_seed_paths"] == [
        "state/meta_missions/type_a_autonomous_seed_loop/seeds/microcosm_substrate_import_autonomous_seed.json"
    ]
    assert result["assimilation_policy"]["forbidden_authority_rejected"] is True
    assert result["source_module_manifest_status"] == "pass"
    assert result["source_module_manifest_ref"].endswith("source_module_manifest.json")
    assert result["body_copied_material_count"] == 3
    source_imports = result["source_open_body_imports"]
    assert source_imports["status"] == "pass"
    assert source_imports["body_material_count"] == 3
    assert set(source_imports["body_material_ids"]) == PATTERN_SOURCE_MODULE_IDS
    assert source_imports["body_material_classes"] == {
        "public_macro_pattern_body": 1,
        "public_macro_receipt_body": 1,
        "public_macro_tool_body": 1,
    }
    assert source_imports["body_in_receipt"] is False
    assert source_imports["body_text_in_receipt"] is False
    assert all(not Path(path).is_absolute() for path in result["public_replacement_refs"])
    assert any(path.endswith("source_module_manifest.json") for path in result["public_replacement_refs"])


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
    assert payload["body_copied_material_count"] == 3
    assert payload["source_open_body_imports"]["body_material_count"] == 3
    assert set(payload["source_open_body_imports"]["body_material_ids"]) == (
        PATTERN_SOURCE_MODULE_IDS
    )
    assert payload["source_open_body_imports"]["body_in_receipt"] is False
    assert payload["metadata_projection_not_live_learning_authority"] is True
    assert payload["authority_ceiling"]["private_data_equivalence_claim"] is False
    assert payload["authority_ceiling"]["behavior_change_overclaims_allowed"] is False
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
    for hit in payload["private_state_scan"]["hits"]:
        assert hit["body_redacted"] is True
        assert not Path(hit["path"]).is_absolute()


def test_pattern_assimilation_source_modules_are_exact_macro_body_imports() -> None:
    manifest_path = ASSIMILATION_BUNDLE_INPUT / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    modules = manifest["modules"]

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 3
    assert {row["module_id"] for row in modules} == PATTERN_SOURCE_MODULE_IDS

    for row in modules:
        source_path = MICROCOSM_ROOT.parent / row["source_ref"]
        target_path = MICROCOSM_ROOT.parent / row["target_ref"]
        target_bytes = target_path.read_bytes()
        digest = hashlib.sha256(target_bytes).hexdigest()

        if source_path.is_file():
            assert source_path.read_bytes() == target_bytes
        assert row["source_import_class"] == "copied_non_secret_macro_body"
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["body_text_in_receipt"] is False
        assert row["sha256"] == digest
        assert row["source_sha256"] == digest
        assert row["target_sha256"] == digest
        text = target_bytes.decode("utf-8")
        for anchor in row["required_anchors"]:
            assert anchor in text
