from __future__ import annotations

import json
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
        "Give me the lay of the land.",
        "Walk me through this codebase.",
        "What are the interesting parts?",
        "Explain this project to me.",
        "What has been built?",
        "Give me a comprehensive tour.",
        "What is Plectis?",
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
    assert {
        row["family"] for row in pack["family_highlights"]
    } == {
        row["family"] for row in pack["major_subsystems"]
    }
    assert all(row["mechanism"] for row in pack["family_highlights"])
    assert len(pack["answer_contract"]["required_coverage"]) == 5


def test_text_self_model_does_not_hide_coverage_or_companion() -> None:
    pack = C.comprehend(root=ROOT, mode="self-model")
    card = _render_comprehend_card(pack)

    assert "Complete family coverage:" in card
    for row in pack["major_subsystems"]:
        assert f"{row['family']}: {row['organ_count']} organs" in card
    for row in pack["family_highlights"]:
        assert row["display_name"] in card
    assert "plectis-lean-erdos249-257" in card
    assert "--profile whole_substrate_map" in card


def test_committed_read_pack_builder_is_deterministic_and_complete(
    tmp_path: Path,
) -> None:
    C.build_cached_read_packs(ROOT, out_dir=tmp_path)
    first = (tmp_path / "self_model.json").read_bytes()
    C.build_cached_read_packs(ROOT, out_dir=tmp_path)
    second = (tmp_path / "self_model.json").read_bytes()
    cached = json.loads(second)

    assert first == second
    assert "compile_ms" not in cached
    assert len(cached["family_highlights"]) == 7
    assert cached["companion_repository"]["name"] == (
        "plectis-lean-erdos249-257"
    )


def test_paper_questions_route_to_complete_question_first_guide() -> None:
    inputs = C.load_inputs(ROOT)
    for question in (
        "Which papers should I read, and in what order?",
        "What does each paper establish?",
        "Show me the paper guide.",
        "Where is the paper corpus?",
    ):
        assert C.route_goal(question, inputs)[0] == "papers"

    guide = C.comprehend(root=ROOT, mode="papers")
    assert guide["found"]
    assert len(guide["paper_index"]) == guide["paper_corpus_count"] == 11
    assert guide["default_sequence"]["paper_ids"] == [
        "plectis-public-system",
        "cold-clone-to-proof-receipt",
        "claim-faithful-publication-systems",
    ]
    assert guide["companion_repository"]["name"] == (
        "plectis-lean-erdos249-257"
    )
    assert guide["problem_routes"]["erdos_249"][-1] == (
        "erdos249-totient-reasoning-surface"
    )

    first_action = C.comprehend(
        root=ROOT,
        mode="first_action",
        target="Which papers should I read, and in what order?",
    )
    assert first_action["routing"]["packet_id"] == "papers"
    assert "--slice papers" in first_action["first_action"]["command"]
