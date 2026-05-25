from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.mechanistic_interpretability_circuit_attribution_replay import (
    EXPECTED_NEGATIVE_CASES,
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
ORACLE_ATTRIBUTION_SOURCE_BODY_MATERIAL_IDS = [
    "oracle_attribution_legacy_node_body_import",
    "oracle_attribution_substrate_node_body_import",
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
        ORACLE_ATTRIBUTION_SOURCE_BODY_MATERIAL_IDS
    )
    for case_id, codes in EXPECTED_NEGATIVE_CASES.items():
        assert result["negative_case_summary"]["observed_codes"][case_id] == codes


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
        ORACLE_ATTRIBUTION_SOURCE_BODY_MATERIAL_IDS
    )
    assert result["body_in_receipt"] is False
    assert result["secret_exclusion_scan"]["status"] == "pass"


def test_mechanistic_interpretability_oracle_attribution_source_modules_are_exact_imports(
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
    assert set(modules) == set(ORACLE_ATTRIBUTION_SOURCE_BODY_MATERIAL_IDS)
    for material_id in ORACLE_ATTRIBUTION_SOURCE_BODY_MATERIAL_IDS:
        row = modules[material_id]
        target = MICROCOSM_ROOT / row["target_ref"].removeprefix("microcosm-substrate/")
        source = MICROCOSM_ROOT.parent / row["source_ref"]
        assert source.is_file()
        assert target.is_file()
        assert row["status"] == "pass"
        assert row["material_class"] == "public_macro_pattern_body"
        assert row["classification"] == "copied_non_secret_macro_body"
        assert row["body_copied"] is True
        assert row["body_in_receipt"] is False
        assert row["target_body_digest"] == _sha256_ref(target)
        assert _sha256_ref(source) == _sha256_ref(target)
