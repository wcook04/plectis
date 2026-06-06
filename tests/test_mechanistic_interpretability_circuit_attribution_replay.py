from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import (
    mechanistic_interpretability_circuit_attribution_replay as circuit_attribution,
)
from microcosm_core.organs.mechanistic_interpretability_circuit_attribution_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    _line_count,
    main,
    result_card,
    run,
    run_attribution_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/mechanistic_interpretability_circuit_attribution_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/mechanistic_interpretability_circuit_attribution_replay/"
    "exported_circuit_attribution_bundle"
)
MACRO_SOURCE_BODY_MATERIAL_IDS = [
    "oracle_attribution_legacy_node_body_import",
    "oracle_attribution_substrate_node_body_import",
    "pattern_ledger_mechanistic_replay_contract_body_import",
    "high_novelty_interpretability_growth_receipt_body_import",
    "organ_projection_ir_external_boundary_body_import",
    "projection_readiness_checker_control_plane_body_import",
    "mission_transaction_preflight_tool_body_import",
    "agent_execution_trace_tool_body_import",
    "std_agent_execution_trace_standard_body_import",
    "std_extracted_pattern_route_readiness_standard_body_import",
    "strict_json_source_body_import",
]
MACRO_SOURCE_BODY_MATERIAL_CLASSES = {
    "oracle_attribution_legacy_node_body_import": "public_macro_pattern_body",
    "oracle_attribution_substrate_node_body_import": "public_macro_pattern_body",
    "pattern_ledger_mechanistic_replay_contract_body_import": "public_macro_pattern_body",
    "high_novelty_interpretability_growth_receipt_body_import": "public_macro_pattern_body",
    "organ_projection_ir_external_boundary_body_import": "public_macro_pattern_body",
    "projection_readiness_checker_control_plane_body_import": "public_macro_tool_body",
    "mission_transaction_preflight_tool_body_import": "public_macro_tool_body",
    "agent_execution_trace_tool_body_import": "public_macro_tool_body",
    "strict_json_source_body_import": "public_macro_tool_body",
    "std_agent_execution_trace_standard_body_import": "public_macro_proof_body",
    "std_extracted_pattern_route_readiness_standard_body_import": "public_macro_proof_body",
}
MACRO_SOURCE_BODY_CLASS_LIST = [
    "public_macro_pattern_body",
    "public_macro_proof_body",
    "public_macro_tool_body",
]


def _sha256_ref(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


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


def test_mechanistic_interpretability_line_count_streams_without_full_text_read(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "interpretability_source.py"
    empty_source = tmp_path / "empty_interpretability_source.py"
    source.write_text("one\n\ntwo\n", encoding="utf-8")
    empty_source.write_text("", encoding="utf-8")
    guarded_paths = {source, empty_source}
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self in guarded_paths:
            raise AssertionError("line count should stream source-module input")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert _line_count(source) == 3
    assert _line_count(empty_source) == 1


def test_mechanistic_interpretability_sha256_streams_without_read_bytes(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "circuit_source.py"
    body = b"FEATURE_ATTRIBUTION_EDGE = True\n" * 1024
    source.write_bytes(body)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if self == source:
            raise AssertionError("digest should stream circuit attribution input")
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    assert circuit_attribution._sha256_hex(source) == hashlib.sha256(body).hexdigest()
    assert circuit_attribution._sha256_ref(source) == (
        "sha256:" + hashlib.sha256(body).hexdigest()
    )


def test_mechanistic_interpretability_toy_transformer_runtime_computes_attribution() -> None:
    runtime = circuit_attribution._toy_transformer_attribution_runtime()

    assert runtime["status"] == "pass"
    assert (
        runtime["runtime_kind"]
        == "pure_python_two_layer_toy_transformer_forward_gradient_ablation"
    )
    assert runtime["spec_source"] == "internal_default_for_direct_unit_call"
    assert runtime["input_coupled_fixture"] is False
    assert runtime["forward_receipt"]["target_logit"] == 0.044176
    assert len(runtime["gradient_scores"]) == 3
    assert len(runtime["ablation_result"]["rows"]) == 3
    assert runtime["ablation_result"]["top_feature_by_ablation"] == (
        "toy_hidden_feature_1"
    )
    assert runtime["fabrication_guard"]["top_feature_by_attribution"] == (
        "toy_hidden_feature_1"
    )
    assert runtime["fabrication_guard"]["top_feature_by_ablation"] == (
        "toy_hidden_feature_1"
    )
    assert runtime["fabrication_guard"]["verdict_source"] == (
        "fixture_claim_compared_to_recomputed_forward_gradient_ablation"
    )
    assert runtime["fabrication_guard"]["recompute_input_fields"] == [
        "token_ids",
        "embeddings",
        "layer1",
        "layer2",
        "target_logit_index",
    ]
    assert runtime["fabrication_guard"]["claimed_top_feature_fields"] == [
        "expected_top_feature_by_attribution",
        "expected_top_feature_by_ablation",
    ]
    assert runtime["fabrication_guard"]["declared_matches_recompute"] is True
    assert runtime["fabrication_guard"]["input_coupled_verdict"] is True
    assert runtime["fabrication_guard"]["passed"] is True
    assert runtime["private_model_weights_exported"] is False
    assert runtime["raw_activation_dump_exported"] is False
    assert runtime["body_in_receipt"] is False


def test_mechanistic_interpretability_circuit_attribution_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path
        / "receipts/first_wave/mechanistic_interpretability_circuit_attribution_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "mechanistic_interpretability_circuit_attribution_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["selected_route_id"] == (
        "mechanistic_interpretability_circuit_attribution_replay"
    )
    assert result["attribution_summary"]["feature_count"] == 6
    assert result["attribution_summary"]["replay_count"] == 6
    assert result["attribution_summary"]["attribution_edge_count"] == 12
    assert result["attribution_summary"]["attribution_path_count"] >= 6
    assert result["attribution_summary"]["reachable_error_node_count"] == 6
    assert (
        result["attribution_summary"]["decorative_weight_sequence_detected"]
        is False
    )
    assert result["weight_sequence_analysis"]["status"] == "pass"
    assert result["toy_transformer_attribution_runtime"]["status"] == "pass"
    assert (
        result["toy_transformer_attribution_runtime"]["spec_source"]
        == "attribution_replays.toy_transformer_runtime"
    )
    assert (
        result["toy_transformer_attribution_runtime"]["input_coupled_fixture"]
        is True
    )
    assert result["toy_transformer_attribution_runtime"]["fabrication_guard"][
        "passed"
    ] is True
    assert result["toy_transformer_attribution_runtime"]["fabrication_guard"][
        "declared_matches_recompute"
    ] is True
    assert result["toy_transformer_attribution_runtime"]["fabrication_guard"][
        "top_feature_by_attribution"
    ] == "toy_hidden_feature_1"
    assert result["toy_transformer_attribution_runtime"]["fabrication_guard"][
        "top_feature_by_ablation"
    ] == "toy_hidden_feature_1"
    assert result["attribution_summary"]["toy_transformer_runtime_status"] == "pass"
    assert result["attribution_summary"]["toy_transformer_target_logit"] == 0.044176
    assert result["attribution_summary"]["toy_transformer_ablation_count"] == 3
    assert (
        result["attribution_summary"]["toy_transformer_fabrication_guard_passed"]
        is True
    )
    assert (
        result["authority_ceiling"]["public_toy_transformer_runtime_authorized"]
        is True
    )
    assert all(
        row["path_count"] >= 1
        for row in result["attribution_graph_analyses"]
    )
    assert result["attribution_summary"]["causal_intervention_count"] == 6
    assert result["attribution_summary"]["contradiction_case_count"] == 6
    assert result["negative_case_summary"]["expected_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["observed_negative_case_count"] == len(
        EXPECTED_NEGATIVE_CASES
    )
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["authority_ceiling"]["private_model_weights_export_authorized"] is False
    assert result["authority_ceiling"]["raw_activation_dump_export_authorized"] is False
    assert result["authority_ceiling"]["proprietary_prompt_export_authorized"] is False
    assert result["authority_ceiling"]["hidden_chain_of_thought_export_authorized"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["source_module_import_status"] == (
        "copied_non_secret_macro_body_landed"
    )
    assert result["source_module_summary"]["public_safe_body_material_ids"] == (
        MACRO_SOURCE_BODY_MATERIAL_IDS
    )
    assert result["source_open_body_imports"]["status"] == "pass"
    assert (
        result["source_open_body_imports"]["source_import_class"]
        == "copied_non_secret_macro_body"
    )
    assert result["source_open_body_imports"]["body_material_status"] == (
        "copied_non_secret_macro_body_landed"
    )
    assert result["source_open_body_imports"]["body_material_count"] == len(
        MACRO_SOURCE_BODY_MATERIAL_IDS
    )
    assert (
        result["source_open_body_imports"]["body_material_ids"]
        == MACRO_SOURCE_BODY_MATERIAL_IDS
    )
    assert result["source_open_body_imports"]["material_classes"] == (
        MACRO_SOURCE_BODY_CLASS_LIST
    )
    assert result["source_open_body_imports"]["source_manifest_refs"] == [
        "fixtures/first_wave/mechanistic_interpretability_circuit_attribution_replay/input/source_module_manifest.json"
    ]
    assert result["source_open_body_imports"]["aggregate_floor_ref"].endswith(
        "source_module_manifest.json::modules"
    )
    assert result["source_open_body_imports"]["body_text_exported_in_receipts"] is False
    assert (
        result["source_open_body_imports"]["body_text_exported_in_workingness"]
        is False
    )
    assert result["body_copied_material_count"] == len(
        MACRO_SOURCE_BODY_MATERIAL_IDS
    )
    for case_id, codes in EXPECTED_NEGATIVE_CASES.items():
        assert result["negative_case_summary"]["observed_codes"][case_id] == codes


def test_mechanistic_interpretability_rejects_wrong_toy_transformer_top_feature(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    fixture = (
        public_root
        / "fixtures/first_wave/mechanistic_interpretability_circuit_attribution_replay"
    )
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/mechanistic_interpretability_circuit_attribution_replay",
        fixture,
    )
    replay_path = fixture / "input/attribution_replays.json"
    payload = json.loads(replay_path.read_text(encoding="utf-8"))
    payload["toy_transformer_runtime"][
        "expected_top_feature_by_attribution"
    ] = "toy_hidden_feature_0"
    replay_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(
        fixture / "input",
        public_root
        / "receipts/first_wave/mechanistic_interpretability_circuit_attribution_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    guard = result["toy_transformer_attribution_runtime"]["fabrication_guard"]
    assert guard["top_feature_by_attribution"] == "toy_hidden_feature_1"
    assert guard["declared_top_feature_by_attribution"] == "toy_hidden_feature_0"
    assert guard["declared_matches_recompute"] is False
    assert guard["input_coupled_verdict"] is False
    assert (
        "INTERPRETABILITY_TOY_TRANSFORMER_DECLARED_TOP_FEATURE_MISMATCH"
        in guard["failure_codes"]
    )
    assert {
        finding["error_code"] for finding in result["positive_findings"]
    } >= {"INTERPRETABILITY_TOY_TRANSFORMER_DECLARED_TOP_FEATURE_MISMATCH"}


def test_mechanistic_interpretability_rejects_internal_default_toy_runtime(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/mechanistic_interpretability_circuit_attribution_replay",
        public_root / "examples/mechanistic_interpretability_circuit_attribution_replay",
    )
    bundle = (
        public_root
        / "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle"
    )
    replay_path = bundle / "attribution_replays.json"
    payload = json.loads(replay_path.read_text(encoding="utf-8"))
    payload.pop("toy_transformer_runtime")
    replay_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_attribution_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "mechanistic_interpretability_circuit_attribution_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert (
        result["toy_transformer_attribution_runtime"]["spec_source"]
        == "internal_default_for_direct_unit_call"
    )
    assert (
        result["attribution_summary"]["toy_transformer_input_coupled_fixture"]
        is False
    )
    assert {
        finding["error_code"] for finding in result["positive_findings"]
    } >= {"INTERPRETABILITY_TOY_TRANSFORMER_FIXTURE_SPEC_REQUIRED"}


def test_mechanistic_interpretability_toy_transformer_input_perturbation_moves_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/mechanistic_interpretability_circuit_attribution_replay",
        public_root / "examples/mechanistic_interpretability_circuit_attribution_replay",
    )
    bundle = (
        public_root
        / "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle"
    )

    baseline = run_attribution_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "mechanistic_interpretability_circuit_attribution_replay/baseline",
        command="pytest",
    )

    replay_path = bundle / "attribution_replays.json"
    payload = json.loads(replay_path.read_text(encoding="utf-8"))
    toy_runtime = payload["toy_transformer_runtime"]
    toy_runtime["layer2"][0][1] = -0.5
    toy_runtime["expected_top_feature_by_attribution"] = "toy_hidden_feature_0"
    toy_runtime["expected_top_feature_by_ablation"] = "toy_hidden_feature_0"
    replay_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    perturbed = run_attribution_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "mechanistic_interpretability_circuit_attribution_replay/perturbed",
        command="pytest",
    )

    assert baseline["status"] == "pass"
    assert perturbed["status"] == "pass"
    assert (
        baseline["toy_transformer_attribution_runtime"]["weight_digest"]
        != perturbed["toy_transformer_attribution_runtime"]["weight_digest"]
    )
    assert baseline["attribution_summary"]["toy_transformer_target_logit"] == 0.044176
    assert perturbed["attribution_summary"]["toy_transformer_target_logit"] == -0.116939
    assert (
        baseline["attribution_summary"]["toy_transformer_top_feature_by_attribution"]
        == "toy_hidden_feature_1"
    )
    assert (
        perturbed["attribution_summary"]["toy_transformer_top_feature_by_attribution"]
        == "toy_hidden_feature_0"
    )
    assert (
        baseline["attribution_summary"]["toy_transformer_top_feature_by_ablation"]
        == "toy_hidden_feature_1"
    )
    assert (
        perturbed["attribution_summary"]["toy_transformer_top_feature_by_ablation"]
        == "toy_hidden_feature_0"
    )
    assert (
        perturbed["toy_transformer_attribution_runtime"]["fabrication_guard"][
            "declared_matches_recompute"
        ]
        is True
    )
    assert (
        perturbed["toy_transformer_attribution_runtime"]["fabrication_guard"][
            "input_coupled_verdict"
        ]
        is True
    )


def test_mechanistic_interpretability_input_perturbation_rejects_stale_claims(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/mechanistic_interpretability_circuit_attribution_replay",
        public_root / "examples/mechanistic_interpretability_circuit_attribution_replay",
    )
    bundle = (
        public_root
        / "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle"
    )
    replay_path = bundle / "attribution_replays.json"
    payload = json.loads(replay_path.read_text(encoding="utf-8"))
    payload["toy_transformer_runtime"]["layer2"][0][1] = -0.5
    replay_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_attribution_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "mechanistic_interpretability_circuit_attribution_replay/stale_claim",
        command="pytest",
    )

    guard = result["toy_transformer_attribution_runtime"]["fabrication_guard"]
    assert result["status"] == "blocked"
    assert result["attribution_summary"]["toy_transformer_target_logit"] == -0.116939
    assert guard["top_feature_by_attribution"] == "toy_hidden_feature_0"
    assert guard["top_feature_by_ablation"] == "toy_hidden_feature_0"
    assert guard["declared_top_feature_by_attribution"] == "toy_hidden_feature_1"
    assert guard["declared_top_feature_by_ablation"] == "toy_hidden_feature_1"
    assert guard["input_coupled_verdict"] is False
    assert (
        "INTERPRETABILITY_TOY_TRANSFORMER_DECLARED_TOP_FEATURE_MISMATCH"
        in guard["failure_codes"]
    )


def test_mechanistic_interpretability_circuit_attribution_receipts_consume_public_runtime_refs(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "fixtures/first_wave/mechanistic_interpretability_circuit_attribution_replay",
        public_root
        / "fixtures/first_wave/mechanistic_interpretability_circuit_attribution_replay",
    )

    result = run(
        public_root
        / "fixtures/first_wave/mechanistic_interpretability_circuit_attribution_replay/input",
        public_root
        / "receipts/first_wave/mechanistic_interpretability_circuit_attribution_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["body_import_status"] == "real_runtime_receipt_landed"
    assert result["body_in_receipt"] is False
    assert result["body_import_verification"]["classification"] == "real_runtime_receipt"
    assert result["body_import_verification"]["body_in_receipt"] is False
    assert result["toy_transformer_attribution_runtime"]["status"] == "pass"
    assert result["mechanistic_interpretability_board"][
        "toy_transformer_runtime_status"
    ] == "pass"
    assert result["mechanistic_interpretability_board"][
        "toy_transformer_fabrication_guard_passed"
    ] is True
    assert result["source_module_import_status"] == (
        "copied_non_secret_macro_body_landed"
    )
    assert result["source_module_summary"]["status"] == "pass"
    assert result["attribution_summary"]["target_ref_count"] == 6
    assert result["secret_exclusion_scan"]["status"] == "pass"
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    result_keys = _walk_keys(result)
    assert "private_state_scan" not in result_keys
    assert "body_redacted" not in result_keys
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        keys = _walk_keys(json.loads(text))
        assert "model_weights_blob" not in keys
        assert "raw_activation_tensor" not in keys
        assert "proprietary_prompt_body" not in keys
        assert "hidden_chain_of_thought_body" not in keys


def test_mechanistic_interpretability_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_attribution_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "mechanistic_interpretability_circuit_attribution_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_circuit_attribution_bundle"
    assert result["selected_route_id"] == (
        "mechanistic_interpretability_circuit_attribution_replay"
    )
    assert result["attribution_summary"]["replay_count"] == 6
    assert result["attribution_summary"]["attribution_path_count"] >= 6
    assert result["attribution_summary"]["reachable_error_node_count"] == 6
    assert (
        result["attribution_summary"]["decorative_weight_sequence_detected"]
        is False
    )
    assert result["weight_sequence_analysis"]["status"] == "pass"
    assert result["toy_transformer_attribution_runtime"]["status"] == "pass"
    assert (
        result["toy_transformer_attribution_runtime"]["runtime_kind"]
        == "pure_python_two_layer_toy_transformer_forward_gradient_ablation"
    )
    assert result["toy_transformer_attribution_runtime"]["fabrication_guard"][
        "passed"
    ] is True
    assert result["negative_case_summary"]["expected_negative_case_count"] == 0
    assert result["negative_case_summary"]["expected_missing"] == {}
    assert result["finding_count"] == 0
    assert result["authority_ceiling"]["model_transparency_product_claim_authorized"] is False
    assert result["authority_ceiling"]["private_model_internals_claim_authorized"] is False
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["body_import_status"] == "real_runtime_receipt_landed"
    assert result["body_import_verification"]["status"] == "pass"
    assert result["source_module_import_status"] == (
        "copied_non_secret_macro_body_landed"
    )
    assert result["source_module_summary"]["module_count"] == len(
        MACRO_SOURCE_BODY_MATERIAL_IDS
    )
    assert result["source_open_body_imports"]["status"] == "pass"
    assert result["source_open_body_imports"]["body_material_count"] == len(
        MACRO_SOURCE_BODY_MATERIAL_IDS
    )
    assert (
        result["source_open_body_imports"]["body_material_ids"]
        == MACRO_SOURCE_BODY_MATERIAL_IDS
    )
    assert result["source_open_body_imports"]["source_manifest_refs"] == [
        "examples/mechanistic_interpretability_circuit_attribution_replay/exported_circuit_attribution_bundle/source_module_manifest.json"
    ]
    assert result["body_in_receipt"] is False
    assert result["secret_exclusion_scan"]["status"] == "pass"


def test_mechanistic_interpretability_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "mechanistic_interpretability_circuit_attribution_replay"
    )
    command = (
        "python -m microcosm_core.organs."
        "mechanistic_interpretability_circuit_attribution_replay "
        f"run-attribution-bundle --input {BUNDLE_INPUT} --out {out} --card"
    )

    first = run_attribution_bundle(
        BUNDLE_INPUT,
        out,
        command=command,
        reuse_fresh_receipt=True,
    )
    first_card = result_card(first)

    assert first["status"] == "pass"
    assert first["receipt_reused"] is False
    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["command_speed"]["receipt_reused"] is False
    assert first_card["command_speed"]["freshness_input_count"] == 18
    assert first_card["circuit_attribution"]["feature_count"] == 6
    assert first_card["circuit_attribution"]["replay_count"] == 6
    assert first_card["circuit_attribution"]["attribution_path_count"] >= 6
    assert first_card["circuit_attribution"]["toy_transformer_runtime_status"] == "pass"
    assert first_card["circuit_attribution"]["toy_transformer_target_logit"] == 0.044176
    assert first_card["circuit_attribution"]["toy_transformer_ablation_count"] == 3
    assert (
        first_card["circuit_attribution"][
            "toy_transformer_fabrication_guard_passed"
        ]
        is True
    )
    assert (
        first_card["circuit_attribution"]["decorative_weight_sequence_detected"]
        is False
    )
    assert first_card["circuit_attribution"]["source_module_count"] == 11
    assert first_card["circuit_attribution"]["source_open_body_material_count"] == 11
    assert first_card["body_floor"]["features_in_card"] is False
    assert first_card["body_floor"]["attribution_replays_in_card"] is False
    assert first_card["body_floor"]["source_open_body_imports_in_card"] is False
    assert "features" not in first_card
    assert "attribution_replays" not in first_card

    def fail_build_result(*_args, **_kwargs):
        raise AssertionError("fresh --card bundle path should reuse the receipt")

    monkeypatch.setattr(circuit_attribution, "_build_result", fail_build_result)

    assert (
        main(
            [
                "run-attribution-bundle",
                "--input",
                str(BUNDLE_INPUT),
                "--out",
                str(out),
                "--card",
            ]
        )
        == 0
    )
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]


def test_mechanistic_interpretability_bundle_card_rejects_uncoupled_cached_receipt(
    tmp_path: Path,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "mechanistic_interpretability_circuit_attribution_replay"
    )
    command = (
        "python -m microcosm_core.organs."
        "mechanistic_interpretability_circuit_attribution_replay "
        f"run-attribution-bundle --input {BUNDLE_INPUT} --out {out} --card"
    )
    first = run_attribution_bundle(
        BUNDLE_INPUT,
        out,
        command=command,
        reuse_fresh_receipt=True,
    )
    receipt_path = out / "exported_circuit_attribution_bundle_validation_result.json"
    cached = json.loads(receipt_path.read_text(encoding="utf-8"))
    cached["toy_transformer_attribution_runtime"]["input_coupled_fixture"] = False
    cached["toy_transformer_attribution_runtime"]["fabrication_guard"][
        "input_coupled_verdict"
    ] = False
    receipt_path.write_text(
        json.dumps(cached, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    rebuilt = run_attribution_bundle(
        BUNDLE_INPUT,
        out,
        command=command,
        reuse_fresh_receipt=True,
    )

    assert first["status"] == "pass"
    assert rebuilt["status"] == "pass"
    assert rebuilt["receipt_reused"] is False
    assert (
        rebuilt["toy_transformer_attribution_runtime"]["input_coupled_fixture"]
        is True
    )
    assert rebuilt["toy_transformer_attribution_runtime"]["fabrication_guard"][
        "input_coupled_verdict"
    ] is True


def test_mechanistic_interpretability_macro_source_modules_are_exact_imports(
    tmp_path: Path,
) -> None:
    result = run_attribution_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "mechanistic_interpretability_circuit_attribution_replay",
        command="pytest",
    )

    modules = {
        row["module_id"]: row
        for row in result["source_module_summary"]["modules"]
    }
    assert set(modules) == set(MACRO_SOURCE_BODY_MATERIAL_IDS)
    for material_id in MACRO_SOURCE_BODY_MATERIAL_IDS:
        row = modules[material_id]
        target = MICROCOSM_ROOT / row["target_ref"].removeprefix("microcosm-substrate/")
        source = MICROCOSM_ROOT.parent / row["source_ref"]
        assert source.is_file()
        assert target.is_file()
        assert row["status"] == "pass"
        assert row["material_class"] == MACRO_SOURCE_BODY_MATERIAL_CLASSES[material_id]
        assert row["classification"] == "copied_non_secret_macro_body"
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["target_body_digest"] == _sha256_ref(target)
        assert _sha256_ref(source) == _sha256_ref(target)


def test_mechanistic_interpretability_source_modules_reject_body_text_in_receipt(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/mechanistic_interpretability_circuit_attribution_replay",
        public_root / "examples/mechanistic_interpretability_circuit_attribution_replay",
    )
    bundle = (
        public_root
        / "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["body_text_in_receipt"] = True
    manifest["modules"][0]["body_text_in_receipt"] = True
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = run_attribution_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "mechanistic_interpretability_circuit_attribution_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_module_summary"]["status"] == "blocked"
    error_codes = {
        finding["error_code"]
        for finding in result["source_module_summary"]["findings"]
    }
    assert "INTERPRETABILITY_SOURCE_BODY_TEXT_IN_RECEIPT_FORBIDDEN" in error_codes
    assert (
        "INTERPRETABILITY_SOURCE_MODULE_BODY_TEXT_IN_RECEIPT_FORBIDDEN"
        in error_codes
    )


def test_mechanistic_interpretability_fixture_manifest_exports_body_floor() -> None:
    manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "core/fixture_manifests/"
            "mechanistic_interpretability_circuit_attribution_replay.fixture_manifest.json"
        ).read_text(encoding="utf-8")
    )

    body_imports = manifest["source_open_body_imports"]
    assert body_imports["status"] == "pass"
    assert body_imports["body_material_status"] == (
        "copied_non_secret_macro_body_landed"
    )
    assert body_imports["body_material_count"] == len(
        MACRO_SOURCE_BODY_MATERIAL_IDS
    )
    assert (
        body_imports["body_material_ids"]
        == MACRO_SOURCE_BODY_MATERIAL_IDS
    )
    assert body_imports["material_classes"] == MACRO_SOURCE_BODY_CLASS_LIST
    assert body_imports["source_manifest_refs"] == [
        "examples/mechanistic_interpretability_circuit_attribution_replay/exported_circuit_attribution_bundle/source_module_manifest.json"
    ]
    assert body_imports["aggregate_floor_ref"].endswith(
        "source_module_manifest.json::modules"
    )
    assert body_imports["body_text_exported_in_receipts"] is False
    assert body_imports["body_text_exported_in_workingness"] is False
    assert manifest["body_copied_material_count"] == len(
        MACRO_SOURCE_BODY_MATERIAL_IDS
    )
    bundle_manifest = json.loads(
        (BUNDLE_INPUT / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    bundle_body_imports = bundle_manifest["source_open_body_imports"]
    assert bundle_body_imports["body_material_count"] == len(
        MACRO_SOURCE_BODY_MATERIAL_IDS
    )
    assert (
        bundle_body_imports["body_material_ids"]
        == MACRO_SOURCE_BODY_MATERIAL_IDS
    )
    assert bundle_manifest["body_copied_material_count"] == len(
        MACRO_SOURCE_BODY_MATERIAL_IDS
    )


def test_mechanistic_interpretability_rejects_decorative_weight_sequences(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/mechanistic_interpretability_circuit_attribution_replay",
        public_root / "examples/mechanistic_interpretability_circuit_attribution_replay",
    )
    bundle = (
        public_root
        / "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle"
    )
    replay_path = bundle / "attribution_replays.json"
    payload = json.loads(replay_path.read_text(encoding="utf-8"))
    for index, replay in enumerate(payload["attribution_replays"]):
        replay["graph_edges"][0]["weight"] = round(0.45 + (index * 0.03), 2)
        replay["graph_edges"][1]["weight"] = round(0.23 + (index * 0.02), 2)
    replay_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = run_attribution_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "mechanistic_interpretability_circuit_attribution_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["weight_sequence_analysis"]["decorative_sequence_detected"] is True
    assert {
        finding["error_code"] for finding in result["positive_findings"]
    } >= {"INTERPRETABILITY_DECORATIVE_WEIGHT_SEQUENCE"}


def test_mechanistic_interpretability_rejects_disconnected_graph_edges(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT
        / "examples/mechanistic_interpretability_circuit_attribution_replay",
        public_root / "examples/mechanistic_interpretability_circuit_attribution_replay",
    )
    bundle = (
        public_root
        / "examples/mechanistic_interpretability_circuit_attribution_replay/"
        "exported_circuit_attribution_bundle"
    )
    replay_path = bundle / "attribution_replays.json"
    payload = json.loads(replay_path.read_text(encoding="utf-8"))
    payload["attribution_replays"][0]["graph_edges"][1]["target"] = (
        "missing_public_error_node"
    )
    replay_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    result = run_attribution_bundle(
        bundle,
        public_root
        / "receipts/runtime_shell/demo_project/organs/"
        "mechanistic_interpretability_circuit_attribution_replay",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["attribution_graph_analyses"][0]["path_count"] == 0
    assert {
        finding["error_code"] for finding in result["positive_findings"]
    } >= {
        "INTERPRETABILITY_GRAPH_EDGE_ENDPOINT_UNRESOLVED",
        "INTERPRETABILITY_GRAPH_PATH_REQUIRED",
    }
