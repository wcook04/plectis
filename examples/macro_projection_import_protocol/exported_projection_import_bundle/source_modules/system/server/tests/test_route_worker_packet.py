from __future__ import annotations

import json
from pathlib import Path

from system.lib import (
    nvidia_route_hints,
    route_candidate_builder,
    route_discovery_edc,
    route_graph_candidate_ranker,
    route_node_card_builder,
    route_verb_correction,
)


def test_authority_plane_classifies_paths_correctly() -> None:
    from system.lib.route_node_card_builder import authority_plane

    assert authority_plane("codex/standards/std_foo.json") == "standard"
    assert authority_plane("codex/doctrine/paper_modules/nav.md") == "paper_module"
    assert authority_plane("codex/doctrine/skills/foo/bar.md") == "skill"
    assert authority_plane("system/lib/nvidia_nim.py") == "runtime"
    assert authority_plane("state/raw_seed_routing_pilot/foo.json") == "state_receipt"
    assert authority_plane("annexes/understand-anything/annex_notes.json") == "annex_review"
    assert authority_plane("annexes/free-claude-code/repo/config/settings.py") == "annex_review"


def test_node_cards_extract_symbols_imports_and_json_keys(tmp_path: Path) -> None:
    (tmp_path / "system/lib").mkdir(parents=True)
    (tmp_path / "codex/standards").mkdir(parents=True)
    (tmp_path / "system/lib/nvidia_nim.py").write_text(
        "DEFAULT_CHAT_MODEL = 'z-ai/glm4.7'\n\ndef chat_completion():\n    return 'ok'\n",
        encoding="utf-8",
    )
    (tmp_path / "system/lib/type_a_worker_harness.py").write_text(
        "from system.lib import nvidia_nim\n\nclass Worker:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "codex/standards/std_navigation_rosetta_grammar.json").write_text(
        json.dumps({"relation_verb_shape": {"base_verbs": ["feeds", "governs"]}}),
        encoding="utf-8",
    )

    cards = route_node_card_builder.build_node_cards(
        tmp_path,
        [
            "system/lib/nvidia_nim.py",
            "system/lib/type_a_worker_harness.py",
            "codex/standards/std_navigation_rosetta_grammar.json",
        ],
    )
    by_path = {card["path"]: card for card in cards}

    assert "chat_completion" in by_path["system/lib/nvidia_nim.py"]["exports_or_symbols"]
    assert "system.lib.nvidia_nim" in by_path["system/lib/type_a_worker_harness.py"]["imports_or_dependencies"]
    assert "relation_verb_shape" in by_path["codex/standards/std_navigation_rosetta_grammar.json"]["json_keys_or_schema_terms"]
    assert by_path["codex/standards/std_navigation_rosetta_grammar.json"]["authority_plane"] == "standard"
    assert "runtime_defaults_may_invalidate_prose" in by_path["system/lib/nvidia_nim.py"]["verb_cues"]


def test_candidate_pairs_surface_import_signal_and_allowlisted_verbs(tmp_path: Path) -> None:
    (tmp_path / "system/lib").mkdir(parents=True)
    (tmp_path / "system/lib/nvidia_nim.py").write_text("def chat_completion():\n    pass\n", encoding="utf-8")
    (tmp_path / "system/lib/type_a_worker_harness.py").write_text(
        "from system.lib import nvidia_nim\n",
        encoding="utf-8",
    )
    cards = route_node_card_builder.build_node_cards(
        tmp_path,
        ["system/lib/type_a_worker_harness.py", "system/lib/nvidia_nim.py"],
    )

    pairs = route_candidate_builder.build_candidate_pairs(cards, max_pairs=4)

    import_pair = next(pair for pair in pairs if pair["target"] == "system/lib/nvidia_nim.py")
    assert "source imports target module" in import_pair["deterministic_signals"]
    assert set(import_pair["possible_verbs_from_signals"]) <= {
        "feeds",
        "blocks",
        "governs",
        "evidences",
        "populates",
        "invalidates",
        "compresses",
        "routes_to",
        "audits",
        "supersedes",
    }


def test_route_hint_passages_are_neutral(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def source():\n    pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def target():\n    pass\n", encoding="utf-8")
    cards = route_node_card_builder.build_node_cards(tmp_path, ["a.py", "b.py"])
    pairs = route_candidate_builder.build_candidate_pairs(
        cards,
        slate_pairs=[{"pair_id": "P_001", "source": "a.py", "target": "b.py"}],
    )

    passages, kept = nvidia_route_hints.pair_passages(cards, pairs)

    assert kept[0]["pair_id"] == "P_001"
    assert "valid edge" not in passages[0].lower()
    assert "semantic relation" not in passages[0].lower()
    assert "source_path=a.py" in passages[0]


def test_graph_candidate_ranker_uses_accepted_edges(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def source():\n    pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def target():\n    pass\n", encoding="utf-8")
    (tmp_path / "accepted.jsonl").write_text(
        json.dumps({"source": "a.py", "target": "b.py", "verb": "feeds"}) + "\n",
        encoding="utf-8",
    )
    cards = route_node_card_builder.build_node_cards(tmp_path, ["a.py", "b.py"])
    ranks = route_graph_candidate_ranker.build_graph_candidate_ranks(
        cards,
        [],
        accepted_edges_path=tmp_path / "accepted.jsonl",
        top_k=3,
    )

    assert ranks["ranked_by_source"]["a.py"][0]["target"] == "b.py"
    assert ranks["ranked_by_source"]["a.py"][0]["rank_source"] == "personalized_pagerank"


def test_verb_correction_prompt_has_no_prior_verb_and_includes_planes(tmp_path: Path) -> None:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from tools.meta.control.routing_pilot_harness import build_verb_correction_prompt

    prior_candidate = {
        "route_edges": [
            {
                "source": "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json",
                "target": "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/09.45 - Phase 09.45 - Routing-First Micro-Metabolism and NVIDIA Type A Harness/synth_seed.json",
                "connector_verb": "populates",
                "evidence_set": ["bridge_evidence", "source_evidence", "target_evidence"],
            }
        ]
    }

    prompt = build_verb_correction_prompt(prior_candidate)
    payload = json.loads(prompt[prompt.find("{"):])

    confirmed = payload.get("confirmed_pairs", [])
    assert len(confirmed) >= 1, "expected at least one confirmed pair"
    for pair in confirmed:
        assert "prior_connector_verb" not in pair, "prior_connector_verb must not be sent (anchoring risk)"
        assert "source_plane" in pair, "source_plane annotation required"
        assert "target_plane" in pair, "target_plane annotation required"
    assert "verb_semantics" in payload, "verb_semantics disambiguation required"
    for ev_item in confirmed[0].get("evidence_set", []):
        assert ev_item not in {"bridge_evidence", "source_evidence", "target_evidence"}, "placeholder evidence must be filtered"


def test_score_verb_correction_returns_perfect_score_for_baseline_verbs() -> None:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from tools.meta.control.routing_pilot_harness import _score_verb_correction

    # Correct verbs from the Phase 09.45 manual baseline
    candidate = {
        "verb_corrections": [
            {
                "source": "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json",
                "target": "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/09.45 - Phase 09.45 - Routing-First Micro-Metabolism and NVIDIA Type A Harness/synth_seed.json",
                "connector_verb": "governs",
            },
            {
                "source": "system/lib/nvidia_nim.py",
                "target": "system/lib/type_a_worker_harness.py",
                "connector_verb": "feeds",
            },
        ]
    }

    score = _score_verb_correction(candidate)

    assert score["correction_count"] == 2
    assert score["pair_match_count"] == 2
    assert score["verb_accuracy_given_pair"] == 1.0


def test_score_verb_correction_penalises_wrong_verbs() -> None:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from tools.meta.control.routing_pilot_harness import _score_verb_correction

    candidate = {
        "verb_corrections": [
            {
                "source": "system/lib/nvidia_nim.py",
                "target": "system/lib/type_a_worker_harness.py",
                "connector_verb": "populates",  # wrong — baseline says feeds
            }
        ]
    }

    score = _score_verb_correction(candidate)

    assert score["pair_match_count"] == 1
    assert score["verb_accuracy_given_pair"] == 0.0


def test_verb_correction_extracts_only_baseline_matching_pairs() -> None:
    prior_edges = [
        {"source": "a.py", "target": "b.py", "connector_verb": "implements"},
        {"source": "b.py", "target": "a.py", "connector_verb": "feeds"},
        {"source": "c.py", "target": "d.py", "connector_verb": "governs"},
    ]
    baseline_edges = [
        {"source": "a.py", "target": "b.py", "connector_verb": "governs"},
        {"source": "b.py", "target": "c.py", "connector_verb": "feeds"},
    ]
    universe = {"a.py", "b.py", "c.py", "d.py"}

    result = route_verb_correction.extract_verb_correction_pairs(prior_edges, baseline_edges, universe)

    assert len(result) == 1
    assert result[0]["source"] == "a.py"
    assert result[0]["target"] == "b.py"
    assert result[0]["connector_verb"] == "implements"


def test_discovery_edc_inflection_alias_resolves_singular_verbs() -> None:
    row = route_discovery_edc.canonicalize_discovery_edge(
        {
            "source": "system/lib/nvidia_nim.py",
            "target": "system/lib/type_a_worker_harness.py",
            "connector_verb": "feed",  # singular — alias should map to "feeds"
            "raw_relation_phrase": "provides runtime input that B consumes",
            "definition": "The NIM client feeds input to the harness.",
        },
        allowed_verbs=["feeds", "governs", "evidences"],
    )

    assert row["nearest_canonical_verb"] == "feeds"
    assert row["canonicalization_status"] == "mapped_to_existing_verb"


def test_discovery_edc_canonicalizes_raw_relation() -> None:
    row = route_discovery_edc.canonicalize_discovery_edge(
        {
            "source": "codex/standards/std_agent_entry_surface.json",
            "target": "tools/meta/factory/check_agent_bootstrap_projection.py",
            "connector_verb": "declares_constraints_for",
            "raw_relation_phrase": "declares constraints enforced by",
            "definition": "The standard declares byte-budget constraints that the checker enforces.",
        },
        allowed_verbs=["governs", "evidences", "audits"],
    )

    assert row["nearest_canonical_verb"] == "governs"
    assert row["canonicalization_status"] == "mapped_to_existing_verb"
    assert row["schema_pattern_cluster"] == "standard_to_checker_enforcement"
