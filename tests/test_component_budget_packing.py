from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from plectis.components.budget_packing import pack
from microcosm_core.organs import provider_context_recipe_budget_policy as policy


def test_ordered_budget_packing_and_negative_budget():
    assert pack({"sizes": [6, 6, 4, 0], "budget": 10}) == {
        "decisions": [True, False, True, True], "total": 10
    }
    assert pack({"sizes": [0, 1], "budget": -1}) == {
        "decisions": [False, False], "total": 0
    }
    assert pack({"sizes": [], "budget": 0}) == {"decisions": [], "total": 0}


def test_projection_uses_compiled_decision_for_real_accounting(monkeypatch):
    original = policy._pack_budget
    seen = []

    def capture(payload):
        seen.append(payload)
        return original(payload)

    monkeypatch.setattr(policy, "_pack_budget", capture)
    result = policy._recipe_projection(
        {"recipe_id": "test", "byte_budget": "10", "sections": ["a", "b", "c", "a", "missing"]},
        sections_by_id={
            "a": {"text": "ééé"},  # six UTF-8 bytes
            "b": {"declared_byte_size": 6},
            "c": {"declared_byte_size": 4},
        },
        real_section_bodies={},
    )
    assert seen == [{"sizes": [6, 6, 4, 6, 0], "budget": 10}]
    assert result["included_section_ids"] == ["a", "c", "missing"]
    assert result["omitted_section_ids"] == ["b", "a"]
    assert result["included_byte_count"] == 10
    assert result["included_sections"][-1]["byte_size_source"] == "missing_byte_size"


def test_projection_preserves_negative_budgets_and_fallbacks():
    r = policy._recipe_projection(
        {"byte_budget": -1, "sections": ["a", "missing"]},
        sections_by_id={"a": {"declared_byte_size": True}},
        real_section_bodies={},
    )
    assert r["included_section_ids"] == []
    assert r["omitted_section_ids"] == ["a", "missing"]
    assert r["included_byte_count"] == 0
    assert r["omitted_sections"][0]["accounted_byte_size"] == 1


def test_strict_adapter_rejects_invalid_types_without_coercion():
    path = Path(__file__).resolve().parents[1] / "src/plectis/components/budget_packing/_adapter.py"
    spec = importlib.util.spec_from_file_location("budget_packing_adapter_test", path)
    adapter = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(adapter)
    for bad in (
        {"sizes_hex": [True], "budget_hex": "a"},
        {"sizes_hex": ["-1"], "budget_hex": "a"},
        {"sizes_hex": ["01"], "budget_hex": "a"},
        {"sizes_hex": ["1"], "budget_hex": "-0"},
        {"sizes_hex": ["1"], "budget_hex": "a", "extra": 0},
    ):
        with pytest.raises(ValueError):
            adapter.evaluate(bad, None, None)


def test_large_input_crosses_worker_batch_without_resetting_budget():
    result = pack({"sizes": [1] * 130, "budget": 129})
    assert result == {"decisions": [True] * 129 + [False], "total": 129}


def test_projection_preserves_integer_coercion_and_large_declared_size():
    result = policy._recipe_projection(
        {"byte_budget": 3.9, "sections": ["small", "huge", "flag"]},
        sections_by_id={
            "small": {"text": "é"},
            "huge": {"declared_byte_size": 10**1000},
            "flag": {"declared_byte_size": True},
        },
        real_section_bodies={},
    )
    assert result["byte_budget"] == 3
    assert result["included_section_ids"] == ["small", "flag"]
    assert result["omitted_section_ids"] == ["huge"]
    assert result["included_byte_count"] == 3


@pytest.mark.parametrize(
    ("sizes", "budget"),
    [([], -10), ([0, 0, 1], 0), ([2, 8, 1], 3),
     ([9, 4, 5], 9), ([4, 4, 4], 8), ([6, 0, 6], 12)],
)
def test_against_previous_ordered_loop(sizes, budget):
    decisions = []
    total = 0
    for size in sizes:
        fits = total + size <= budget
        decisions.append(fits)
        if fits:
            total += size
    assert pack({"sizes": sizes, "budget": budget}) == {
        "decisions": decisions, "total": total,
    }


def test_projection_accepts_size_beyond_decimal_json_digit_limit():
    huge = 10**5000
    result = policy._recipe_projection(
        {"byte_budget": 1, "sections": ["huge", "small"]},
        sections_by_id={"huge": {"declared_byte_size": huge}, "small": {"declared_byte_size": 1}},
        real_section_bodies={},
    )
    assert result["omitted_section_ids"] == ["huge"]
    assert result["included_section_ids"] == ["small"]
    assert result["included_byte_count"] == 1


def test_size_above_previous_wire_cap_remains_accepted():
    huge = 1 << 4_000_004  # More than one million hexadecimal digits.
    assert pack({"sizes": [huge], "budget": 0}) == {"decisions": [False], "total": 0}


def test_included_total_beyond_decimal_json_limit_crosses_batches():
    huge = 10**5000
    sizes = [huge] + [0] * 127 + [1, 2]
    assert pack({"sizes": sizes, "budget": huge + 1}) == {
        "decisions": [True] * 129 + [False], "total": huge + 1,
    }
    assert pack({"sizes": [0, huge], "budget": -huge}) == {
        "decisions": [False, False], "total": 0,
    }


def test_projection_uses_exact_integer_token_ceiling_for_large_included_size():
    huge = 10**5000 + 1
    result = policy._recipe_projection(
        {"byte_budget": huge, "sections": ["large"]},
        sections_by_id={"large": {"declared_byte_size": huge}},
        real_section_bodies={},
    )
    assert result["included_byte_count"] == huge
    assert result["approximate_tokens"] == (huge + 3) // 4


@pytest.mark.parametrize("budget", [-1, 0, 133, 1024])
def test_zero_and_nonzero_sizes_agree_across_multiple_batches(budget):
    sizes = [3, 0, 7, 2, 0] * 53
    decisions = []
    total = 0
    for size in sizes:
        fits = total + size <= budget
        decisions.append(fits)
        if fits:
            total += size
    assert pack({"sizes": sizes, "budget": budget}) == {
        "decisions": decisions, "total": total,
    }
