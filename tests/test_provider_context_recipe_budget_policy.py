from __future__ import annotations

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
