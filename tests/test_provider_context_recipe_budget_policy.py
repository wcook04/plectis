from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.provider_context_recipe_budget_policy import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_budget_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/provider_context_recipe_budget_policy/input"
PROVIDER_CONTEXT_SOURCE_MODULE_IDS = [
    "provider_context_formal_ladder_eval_body_import",
    "provider_context_graph_benchmark_body_import",
]


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


def test_provider_context_recipe_budget_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/provider_context_recipe_budget_policy",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/provider_context_recipe_budget_policy_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["recipe_count"] == 6
    assert result["recipe_ids"] == [
        "fewshot_64kb",
        "minimal_4kb",
        "premise_16kb",
        "repair_32kb",
        "skill_32kb",
        "strategy_classification_4kb",
    ]
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["private_state_scan"]["blocking_hit_count"] == 0
    assert result["source_module_import_status"] == "pass"
    assert result["source_module_count"] == 2
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    assert result["authority_ceiling"]["formal_proof_authority"] is False
    for case_id, codes in EXPECTED_NEGATIVE_CASES.items():
        for code in codes:
            assert code in result["observed_negative_cases"][case_id]


def test_provider_context_budget_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/provider_context_recipe_budget_policy",
        public_root / "fixtures/first_wave/provider_context_recipe_budget_policy",
    )
    result = run(
        public_root / "fixtures/first_wave/provider_context_recipe_budget_policy/input",
        public_root / "receipts/first_wave/provider_context_recipe_budget_policy",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_path in result["receipt_paths"]:
        assert not Path(receipt_path).is_absolute()
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        if "source_module_import_status" in payload:
            assert payload["source_module_import_status"] == "pass"
        if "source_module_import" in payload:
            assert payload["source_module_import"]["status"] == "pass"
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_provider_context_budget_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/provider_context_recipe_budget_policy",
        public_root / "examples/provider_context_recipe_budget_policy",
    )
    result = run_budget_bundle(
        public_root / "examples/provider_context_recipe_budget_policy/exported_provider_context_budget_bundle",
        public_root / "receipts/runtime_shell/demo_project/organs/provider_context_recipe_budget_policy",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_provider_context_budget_bundle"
    assert result["bundle_id"] == "provider_context_budget_runtime_example"
    assert result["source_module_import_status"] == "pass"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["deliverable_routes"]["premise_16kb"] == "ranked_premise_ids"
    assert result["deliverable_routes"]["strategy_classification_4kb"] == (
        "strategy_id_classification"
    )
    assert result["context_packets"][4]["omitted_section_ids"] == ["fewshot_examples"]
    assert result["authority_ceiling"]["provider_calls_authorized"] is False
    assert result["authority_ceiling"]["truth_side_material_authorized"] is False
    assert result["receipt_paths"] == [
        (
            "receipts/runtime_shell/demo_project/organs/"
            "provider_context_recipe_budget_policy/"
            "exported_provider_context_budget_bundle_validation_result.json"
        )
    ]


def test_provider_context_source_modules_are_exact_macro_body_imports(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/provider_context_recipe_budget_policy",
        public_root / "examples/provider_context_recipe_budget_policy",
    )
    result = run_budget_bundle(
        public_root / "examples/provider_context_recipe_budget_policy/exported_provider_context_budget_bundle",
        public_root / "receipts/runtime_shell/demo_project/organs/provider_context_recipe_budget_policy",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["source_module_import_status"] == "pass"
    assert result["source_module_ids"] == PROVIDER_CONTEXT_SOURCE_MODULE_IDS
    by_module = {
        row["module_id"]: row
        for row in result["source_module_imports"]
    }
    for module_id in PROVIDER_CONTEXT_SOURCE_MODULE_IDS:
        row = by_module[module_id]
        source = MICROCOSM_ROOT.parent / row["source_ref"]
        target = (
            public_root
            / "examples/provider_context_recipe_budget_policy/exported_provider_context_budget_bundle"
            / row["target_ref"]
        )
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()

        assert target.is_file()
        assert digest == source_digest
        assert row["source_sha256"] == source_digest
        assert row["target_sha256"] == digest
        assert row["sha256_match"] is True
        assert row["required_anchor_count"] == row["present_anchor_count"]
        assert row["body_in_receipt"] is False
