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
    "pattern_assimilation_acceptance_validator_source_body_import",
    "pattern_assimilation_retracted_adapter_receipt_body_import",
}


def _pattern_registry_row() -> dict[str, Any]:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    return next(
        row
        for row in registry["implemented_organs"]
        if row["organ_id"] == "pattern_assimilation_step"
    )


def _pattern_acceptance_row() -> dict[str, Any]:
    acceptance = json.loads(
        (MICROCOSM_ROOT / "core/acceptance/first_wave_acceptance.json").read_text(
            encoding="utf-8"
        )
    )
    return next(
        row
        for row in acceptance["accepted_current_authority_organs"]
        if row["organ_id"] == "pattern_assimilation_step"
    )


def _copy_public_ref(public_root: Path, ref: str) -> None:
    ref_path = Path(ref)
    if ref.startswith("microcosm-substrate/"):
        source = MICROCOSM_ROOT.parent / ref_path
        target = public_root.parent / ref_path
    elif ref_path.parts[:3] == ("state", "microcosm_portfolio", "reconstruction"):
        source = MICROCOSM_ROOT.parent / ref_path
        target = public_root.parent / ref_path
    else:
        source = MICROCOSM_ROOT / ref_path
        target = public_root / ref_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _copy_fixture_landing_receipts(public_root: Path) -> None:
    for row in _load_jsonl(ASSIMILATION_FIXTURE_INPUT / "organ_landing_summaries.jsonl"):
        ref = str(row.get("landing_receipt_ref") or "")
        if ref:
            _copy_public_ref(public_root, ref)


def _copy_exported_bundle_landing_receipts(public_root: Path, bundle: Path) -> None:
    payload = json.loads((bundle / "organ_landing_summaries.json").read_text(encoding="utf-8"))
    for row in payload["organ_landing_summaries"]:
        ref = str(row.get("landing_receipt_ref") or "")
        if ref:
            _copy_public_ref(public_root, ref)


def _rewrite_jsonl_row(path: Path, *, index: int, **updates: Any) -> None:
    rows = _load_jsonl(path)
    rows[index].update(updates)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
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


def test_pattern_assimilation_private_seed_case_rejects_label_only_fixture(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = public_root / "fixtures/first_wave/pattern_assimilation_step/input"
    shutil.copytree(ASSIMILATION_FIXTURE_INPUT, input_dir)
    missing_case_path = input_dir / "missing_closeout_case.json"
    missing_case = json.loads(missing_case_path.read_text(encoding="utf-8"))
    assert missing_case["forbidden_payload_class"] == "seed_origin_payload"
    missing_case.pop("redacted_private_payload_evidence", None)
    missing_case_path.write_text(json.dumps(missing_case, indent=2, sort_keys=True) + "\n")

    result = validate_pattern_assimilation(
        input_dir,
        tmp_path / "receipts/first_wave/pattern_assimilation_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "assimilation_private_raw_seed_body" in result["missing_negative_cases"]
    assert "assimilation_private_raw_seed_body" not in result["observed_negative_cases"]
    assert "RAW_SEED_BODY_IN_ASSIMILATION_FIXTURE" not in result["error_codes"]


def test_pattern_assimilation_receipts_are_public_relative_and_redacted(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/pattern_assimilation_step",
        public_root / "fixtures/first_wave/pattern_assimilation_step",
    )
    _copy_fixture_landing_receipts(public_root)
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
    _copy_fixture_landing_receipts(public_root)
    shutil.copytree(
        MICROCOSM_ROOT / "examples/pattern_assimilation_step",
        public_root / "examples/pattern_assimilation_step",
    )
    _copy_exported_bundle_landing_receipts(
        public_root,
        public_root / "examples/pattern_assimilation_step/exported_assimilation_bundle",
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


def test_pattern_assimilation_primary_card_uses_exported_bundle_lane() -> None:
    registry = _pattern_registry_row()
    acceptance = _pattern_acceptance_row()

    assert "validate-assimilation-bundle" in registry["validator_command"]
    assert (
        "examples/pattern_assimilation_step/exported_assimilation_bundle"
        in registry["validator_command"]
    )
    assert "fixtures/first_wave/pattern_assimilation_step/input" not in registry[
        "validator_command"
    ]
    assert EXPORTED_ASSIMILATION_BUNDLE_RECEIPT_PATH in registry["generated_receipts"]
    assert acceptance["validator_command"] == registry["validator_command"]
    assert acceptance["generated_receipts"] == registry["generated_receipts"]


def test_pattern_assimilation_checked_in_bundle_receipt_matches_body_imports() -> None:
    receipt = json.loads(
        (MICROCOSM_ROOT / EXPORTED_ASSIMILATION_BUNDLE_RECEIPT_PATH).read_text(
            encoding="utf-8"
        )
    )
    source_open_body_imports = receipt["source_open_body_imports"]
    result = receipt

    assert receipt["status"] == "pass"
    assert receipt["input_mode"] == "exported_assimilation_bundle"
    assert receipt["body_copied_material_count"] == len(PATTERN_SOURCE_MODULE_IDS)
    assert source_open_body_imports["body_material_count"] == len(
        PATTERN_SOURCE_MODULE_IDS
    )
    assert source_open_body_imports["body_in_receipt"] is False
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
    assert result["body_copied_material_count"] == 4
    source_imports = result["source_open_body_imports"]
    assert source_imports["status"] == "pass"
    assert source_imports["body_material_count"] == 4
    assert set(source_imports["body_material_ids"]) == PATTERN_SOURCE_MODULE_IDS
    assert source_imports["body_material_classes"] == {
        "public_macro_pattern_body": 1,
        "public_macro_receipt_body": 1,
        "public_macro_tool_body": 1,
        "public_python_source_body": 1,
    }
    assert source_imports["body_in_receipt"] is False
    assert source_imports["body_text_in_receipt"] is False
    assert all(not Path(path).is_absolute() for path in result["public_replacement_refs"])
    assert any(path.endswith("source_module_manifest.json") for path in result["public_replacement_refs"])


def test_pattern_assimilation_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root / "examples/pattern_assimilation_step/exported_assimilation_bundle"
    )
    shutil.copytree(ASSIMILATION_BUNDLE_INPUT, bundle)
    _copy_exported_bundle_landing_receipts(public_root, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_assimilation_bundle(
        bundle,
        public_root / "receipts/first_wave/pattern_assimilation_step",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "blocked"
    assert result["body_copied_material_count"] == len(PATTERN_SOURCE_MODULE_IDS) - 1
    assert "ASSIMILATION_BUNDLE_SOURCE_MODULE_INVALID" in result["error_codes"]
    invalid_cards = [
        card
        for card in result["source_open_body_imports"]["body_material"]
        if card["status"] == "blocked"
    ]
    assert [card["module_id"] for card in invalid_cards] == [
        "macro_pattern_autonomy_process_contract_body_import"
    ]
    assert invalid_cards[0]["defect_codes"] == ["target_sha256_mismatch"]


def test_pattern_assimilation_exported_bundle_receipt_is_public_safe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/pattern_assimilation_step",
        public_root / "examples/pattern_assimilation_step",
    )
    _copy_exported_bundle_landing_receipts(
        public_root,
        public_root / "examples/pattern_assimilation_step/exported_assimilation_bundle",
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
    assert payload["body_copied_material_count"] == 4
    assert payload["source_open_body_imports"]["body_material_count"] == 4
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


def test_pattern_assimilation_rejects_dead_landing_receipt_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/pattern_assimilation_step"
    shutil.copytree(MICROCOSM_ROOT / "fixtures/first_wave/pattern_assimilation_step", fixture)
    _copy_fixture_landing_receipts(public_root)
    _rewrite_jsonl_row(
        fixture / "input/organ_landing_summaries.jsonl",
        index=0,
        landing_receipt_ref="receipts/first_wave/fabricated/dead_landing_receipt.json",
    )

    result = validate_pattern_assimilation(
        fixture / "input",
        public_root / "receipts/first_wave/pattern_assimilation_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "PATTERN_ASSIMILATION_LANDING_RECEIPT_REF_UNRESOLVED" in result["error_codes"]


def test_pattern_assimilation_rejects_dead_closeout_receipt_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = public_root / "fixtures/first_wave/pattern_assimilation_step"
    shutil.copytree(MICROCOSM_ROOT / "fixtures/first_wave/pattern_assimilation_step", fixture)
    _copy_fixture_landing_receipts(public_root)
    _rewrite_jsonl_row(
        fixture / "input/organ_landing_summaries.jsonl",
        index=3,
        assimilation_receipt_ref="fabricated_closeout_receipt_id",
    )

    result = validate_pattern_assimilation(
        fixture / "input",
        public_root / "receipts/first_wave/pattern_assimilation_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "PATTERN_ASSIMILATION_CLOSEOUT_RECEIPT_REF_UNRESOLVED" in result["error_codes"]


def test_pattern_assimilation_exported_bundle_rejects_dead_landing_receipt_ref(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = public_root / "examples/pattern_assimilation_step/exported_assimilation_bundle"
    shutil.copytree(ASSIMILATION_BUNDLE_INPUT, bundle)
    _copy_exported_bundle_landing_receipts(public_root, bundle)
    payload_path = bundle / "organ_landing_summaries.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["organ_landing_summaries"][0][
        "landing_receipt_ref"
    ] = "receipts/acceptance/first_wave/fabricated_dead_ref.json"
    payload_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_assimilation_bundle(
        bundle,
        public_root / "receipts/first_wave/pattern_assimilation_step",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "ASSIMILATION_BUNDLE_LANDING_RECEIPT_REF_UNRESOLVED" in result["error_codes"]


def test_pattern_assimilation_source_modules_are_exact_macro_body_imports() -> None:
    manifest_path = ASSIMILATION_BUNDLE_INPUT / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    modules = manifest["modules"]

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 4
    assert {row["module_id"] for row in modules} == PATTERN_SOURCE_MODULE_IDS

    for row in modules:
        source_path = MICROCOSM_ROOT.parent / row["source_ref"]
        target_path = MICROCOSM_ROOT.parent / row["target_ref"]
        source_bytes = source_path.read_bytes()
        target_bytes = target_path.read_bytes()
        digest = hashlib.sha256(source_bytes).hexdigest()

        assert source_bytes == target_bytes
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
