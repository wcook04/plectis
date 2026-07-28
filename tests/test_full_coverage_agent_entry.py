from __future__ import annotations

from pathlib import Path

from microcosm_core import comprehension as C
from microcosm_core.cli import _render_comprehend_card


ROOT = Path(__file__).resolve().parents[1]


def test_ordinary_repository_question_routes_to_complete_self_model() -> None:
    inputs = C.load_inputs(ROOT)
    for question in (
        "What is in this repository?",
        "What's in this repo?",
        "What does this repo contain?",
        "Give me a complete repository overview.",
    ):
        assert C.route_goal(question, inputs)[0] == "self-model"


def test_self_model_covers_all_families_and_names_lean_companion() -> None:
    pack = C.comprehend(root=ROOT, mode="self-model")
    family_total = sum(row["organ_count"] for row in pack["major_subsystems"])

    assert family_total == pack["code_lens_health"]["organ_count"]
    assert len(pack["major_subsystems"]) == 7
    assert pack["companion_repository"]["name"] == "plectis-lean-erdos249-257"
    assert "github.com/wcook04/plectis-lean-erdos249-257" in (
        pack["companion_repository"]["repository"]
    )
    assert "companion, not dependency" in (
        pack["companion_repository"]["relationship"]
    )


def test_text_self_model_does_not_hide_coverage_or_companion() -> None:
    pack = C.comprehend(root=ROOT, mode="self-model")
    card = _render_comprehend_card(pack)

    assert "Complete family coverage:" in card
    for row in pack["major_subsystems"]:
        assert f"{row['family']}: {row['organ_count']} organs" in card
    assert "plectis-lean-erdos249-257" in card
    assert "--profile whole_substrate_map" in card
