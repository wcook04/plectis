"""Tests for the Rosetta Operator Court v1 packet, scoring, and leakage discipline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from system.lib import route_operator_court as oc


REPO_ROOT = Path(__file__).resolve().parents[3]
GRAMMAR_PATH = REPO_ROOT / "codex" / "standards" / "std_navigation_rosetta_grammar.json"


@pytest.fixture()
def grammar() -> dict:
    return json.loads(GRAMMAR_PATH.read_text(encoding="utf-8"))


@pytest.fixture()
def confirmed_pairs() -> list[dict]:
    return [
        {
            "pair_id": "vc_001",
            "source": "raw_seed_principles.json",
            "target": "synth_seed.json",
            "connector_verb": "populates",  # adversarial-only
            "evidence_set": ["principles inform synth seed"],
        },
        {
            "pair_id": "vc_002",
            "source": "navigation_hologram_theory.md",
            "target": "std_navigation_rosetta_grammar.json",
            "connector_verb": "governs",
            "evidence_set": ["theory motivates standard"],
        },
    ]


@pytest.fixture()
def node_cards() -> list[dict]:
    return [
        {
            "path": "raw_seed_principles.json",
            "kind": "json_contract",
            "authority_plane": "raw_seed_principle",
            "compression_role": "principles",
            "domain_tags": ["raw_seed"],
            "verb_cues": [],
            "json_keys_or_schema_terms": ["principles"],
            "exports_or_symbols": [],
            "imports_or_dependencies": [],
            "headings": [],
            "top_terms": ["principle", "raw", "seed"],
            "exact_mentions": [],
            "evidence_snippets": [],
        },
        {
            "path": "synth_seed.json",
            "kind": "json_contract",
            "authority_plane": "synth_seed",
            "compression_role": "synthesis",
            "domain_tags": ["synth"],
            "verb_cues": [],
            "json_keys_or_schema_terms": ["synth"],
            "exports_or_symbols": [],
            "imports_or_dependencies": [],
            "headings": [],
            "top_terms": ["synth", "seed"],
            "exact_mentions": [],
            "evidence_snippets": [],
        },
        {
            "path": "navigation_hologram_theory.md",
            "kind": "paper_or_annex_note",
            "authority_plane": "paper_module",
            "compression_role": "theory",
            "domain_tags": ["navigation"],
            "verb_cues": [],
            "headings": ["Holographic Compression"],
            "top_terms": ["navigation", "hologram"],
            "exact_mentions": [],
            "evidence_snippets": [],
        },
        {
            "path": "std_navigation_rosetta_grammar.json",
            "kind": "json_contract",
            "authority_plane": "standard",
            "compression_role": "grammar",
            "domain_tags": ["standard"],
            "verb_cues": [],
            "json_keys_or_schema_terms": ["relation_verb_shape"],
            "exports_or_symbols": [],
            "imports_or_dependencies": [],
            "headings": [],
            "top_terms": ["rosetta", "grammar"],
            "exact_mentions": [],
            "evidence_snippets": [],
        },
    ]


@pytest.fixture()
def relation_cards() -> list[dict]:
    return [
        {
            "pair_id": "vc_001",
            "source": "raw_seed_principles.json",
            "target": "synth_seed.json",
            "deterministic_signals": ["shared parent directory"],
            "deterministic_score": 0.4,
            "possible_verbs_from_signals": ["populates", "governs"],
            "negative_warnings": [],
        },
        {
            "pair_id": "vc_002",
            "source": "navigation_hologram_theory.md",
            "target": "std_navigation_rosetta_grammar.json",
            "deterministic_signals": ["paper_module supports standard"],
            "deterministic_score": 0.5,
            "possible_verbs_from_signals": ["evidences"],
            "negative_warnings": [],
        },
    ]


@pytest.fixture()
def baseline_decisions() -> list[dict]:
    return [
        {
            "source": "raw_seed_principles.json",
            "target": "synth_seed.json",
            "connector_verb": "governs",
        },
        {
            "source": "navigation_hologram_theory.md",
            "target": "std_navigation_rosetta_grammar.json",
            "connector_verb": "evidences",
        },
    ]


# ---------------------------------------------------------------------------
# packet shape tests
# ---------------------------------------------------------------------------


def _extract_payload_json(prompt_text: str) -> dict:
    """Pull the JSON payload out of an operator-court prompt (header + JSON)."""
    start = prompt_text.find("{")
    end = prompt_text.rfind("}")
    assert start >= 0 and end > start, "no JSON payload found in prompt"
    return json.loads(prompt_text[start : end + 1])


def test_operator_court_packet_hides_prior_connector_by_default(
    grammar, confirmed_pairs, node_cards, relation_cards
):
    cases = oc.build_deterministic_operator_cases(
        confirmed_pairs, node_cards, relation_cards, grammar, include_prior_guess=False
    )
    prompt = oc.build_operator_court_prompt(
        confirmed_pairs,
        grammar=grammar,
        packet_variant="operator_court_deterministic_cards",
        include_prior_guess=False,
        deterministic_cases=cases,
    )
    # The disclaimer string in the header is meta-instruction, not data leakage —
    # what matters is that the JSON payload's adjudication_cases do not carry the
    # prior connector verb under any field.
    payload = _extract_payload_json(prompt)
    for case in payload.get("adjudication_cases") or []:
        assert "previous_model_guess_may_be_wrong" not in case
        assert "prior_connector_verb" not in case
        assert "connector_verb" not in case
    assert "prior_connector_verb" not in prompt


def test_operator_court_packet_adversarial_variant_marks_prior_guess_as_untrusted(
    grammar, confirmed_pairs, node_cards, relation_cards
):
    cases = oc.build_deterministic_operator_cases(
        confirmed_pairs, node_cards, relation_cards, grammar, include_prior_guess=True
    )
    prompt = oc.build_operator_court_prompt(
        confirmed_pairs,
        grammar=grammar,
        packet_variant="prior_guess_adversarial",
        deterministic_cases=cases,
    )
    assert "previous_model_guess_may_be_wrong" in prompt
    assert "Prior model guesses are not evidence" in prompt


def test_operator_court_packet_includes_relation_families(
    grammar, confirmed_pairs, node_cards, relation_cards
):
    cases = oc.build_deterministic_operator_cases(
        confirmed_pairs, node_cards, relation_cards, grammar
    )
    prompt = oc.build_operator_court_prompt(
        confirmed_pairs,
        grammar=grammar,
        packet_variant="definitions_dominance",
    )
    assert "relation_families" in prompt
    assert "authority" in prompt
    assert "material_flow" in prompt
    # Allowlist-only should NOT include relation_families
    bare = oc.build_operator_court_prompt(
        confirmed_pairs, grammar=grammar, packet_variant="allowlist_only"
    )
    assert "relation_families" not in bare


def test_operator_court_packet_includes_dominance_rules(
    grammar, confirmed_pairs, node_cards, relation_cards
):
    cases = oc.build_deterministic_operator_cases(
        confirmed_pairs, node_cards, relation_cards, grammar
    )
    prompt = oc.build_operator_court_prompt(
        confirmed_pairs,
        grammar=grammar,
        packet_variant="operator_court_deterministic_cards",
        deterministic_cases=cases,
    )
    assert "dominance_rules" in prompt
    assert "authority_over_materialization" in prompt
    assert "audit_over_evidence" in prompt


def test_operator_court_packet_uses_deterministic_evidence_not_baseline_evidence(
    grammar, confirmed_pairs, node_cards, relation_cards
):
    cases = oc.build_deterministic_operator_cases(
        confirmed_pairs, node_cards, relation_cards, grammar
    )
    prompt = oc.build_operator_court_prompt(
        confirmed_pairs,
        grammar=grammar,
        packet_variant="operator_court_deterministic_cards",
        deterministic_cases=cases,
    )
    # Deterministic card fields should be present
    assert "source_card" in prompt
    assert "target_card" in prompt
    assert "authority_plane_delta" in prompt
    assert "candidate_dominance_rules" in prompt
    # Baseline-only fields must not appear
    assert "principles inform synth seed" not in prompt  # came from confirmed_pairs.evidence_set
    assert "theory motivates standard" not in prompt


# ---------------------------------------------------------------------------
# output-schema tests
# ---------------------------------------------------------------------------


def test_operator_court_output_schema_requires_latent_and_dominant(grammar):
    shape = oc.build_adjudication_output_shape(grammar)
    required = set(shape.get("decision_required_fields") or [])
    for needed in (
        "latent_plausible_verbs",
        "dominant_rosetta_verb",
        "relation_family",
        "dominance_rule_applied",
        "graph_behavior",
        "runner_up_verbs",
        "evidence_used",
        "confidence",
        "needs_more_evidence",
        "needs_new_rule",
    ):
        assert needed in required, f"adjudication_output_shape is missing {needed}"


# ---------------------------------------------------------------------------
# scoring tests
# ---------------------------------------------------------------------------


def _decision(
    pair_id, source, target, dominant, latent, family,
    rule="authority_over_materialization", runner_ups=None,
):
    return {
        "pair_id": pair_id,
        "source": source,
        "target": target,
        "latent_plausible_verbs": list(latent),
        "relation_family": family,
        "dominant_rosetta_verb": dominant,
        "dominance_rule_applied": rule,
        "runner_up_verbs": list(runner_ups or []),
        "graph_behavior": {},
        "evidence_used": [],
        "confidence": 0.7,
        "needs_more_evidence": False,
        "needs_new_rule": False,
    }


def test_operator_court_score_reports_confusion_matrix(grammar, baseline_decisions):
    output = {
        "relation_label_decisions": [
            _decision(
                "vc_001", "raw_seed_principles.json", "synth_seed.json",
                dominant="populates", latent=["populates", "governs"], family="material_flow",
                rule="none", runner_ups=["governs"],
            ),
            _decision(
                "vc_002", "navigation_hologram_theory.md", "std_navigation_rosetta_grammar.json",
                dominant="evidences", latent=["evidences"], family="support",
                rule="standard_over_theory",
            ),
        ]
    }
    metrics = oc.score_operator_court_output(output, baseline_decisions, grammar)
    assert metrics["pair_match_count"] == 2
    assert metrics["dominant_operator_accuracy"] == 0.5  # 1/2
    confusion = metrics["per_verb_confusion"]
    assert confusion.get("governs", {}).get("populates") == 1
    assert metrics["runner_up_contains_expected_rate"] == 0.5  # vc_001 has governs in runner_ups


def test_operator_court_scores_expected_latent_but_not_dominant_as_level_3(grammar):
    # Right family (material_flow), wrong dominant verb within the family =>
    # level 3: "model perceives the relation but lacks the dominance law".
    decision_family_right = _decision(
        "vc_001", "a", "b",
        dominant="feeds",
        latent=["feeds", "populates"],
        family="material_flow",
        rule="none",
    )
    level = oc.classify_failure_level(
        decision_family_right, expected_verb="populates", grammar=grammar
    )
    assert level == 3, (
        "expected verb latent and same family as dominant should be a dominance failure (level 3)"
    )


def test_operator_court_scores_wrong_family_as_level_2(grammar):
    # expected=governs (authority), dominant=populates (material_flow), expected latent
    decision = _decision(
        "vc_001", "a", "b",
        dominant="populates", latent=["populates", "governs"], family="material_flow",
    )
    level = oc.classify_failure_level(decision, expected_verb="governs", grammar=grammar)
    assert level == 2


def test_operator_court_scores_expected_dominant_as_level_4(grammar):
    decision = _decision(
        "vc_001", "a", "b",
        dominant="governs", latent=["populates", "governs"], family="authority",
        rule="authority_over_materialization",
    )
    level = oc.classify_failure_level(decision, expected_verb="governs", grammar=grammar)
    assert level == 4


def test_operator_court_scores_invalid_verb_as_level_0(grammar):
    decision = _decision(
        "vc_001", "a", "b",
        dominant="implements",  # not in allowlist
        latent=["governs", "populates"], family="authority",
    )
    level = oc.classify_failure_level(decision, expected_verb="governs", grammar=grammar)
    assert level == 0


def test_operator_court_scores_expected_absent_as_level_1(grammar):
    decision = _decision(
        "vc_001", "a", "b",
        dominant="evidences", latent=["evidences", "feeds"], family="support",
    )
    level = oc.classify_failure_level(decision, expected_verb="governs", grammar=grammar)
    assert level == 1


def test_operator_court_rejects_unknown_dominance_rule_ids(grammar, baseline_decisions):
    output = {
        "relation_label_decisions": [
            _decision(
                "vc_002", "navigation_hologram_theory.md", "std_navigation_rosetta_grammar.json",
                dominant="evidences", latent=["evidences"], family="support",
                rule="some_invented_rule_id",
            ),
        ]
    }
    metrics = oc.score_operator_court_output(output, baseline_decisions, grammar)
    assert metrics["unknown_dominance_rule_count"] == 1


def test_operator_court_score_tolerates_non_object_graph_behavior(grammar, baseline_decisions):
    decision = _decision(
        "vc_002", "navigation_hologram_theory.md", "std_navigation_rosetta_grammar.json",
        dominant="evidences", latent=["evidences"], family="support",
        rule="none",
    )
    decision["graph_behavior"] = "default_route_graph_traversal"

    metrics = oc.score_operator_court_output(
        {"relation_label_decisions": [decision]},
        baseline_decisions,
        grammar,
    )

    assert metrics["pair_match_count"] == 1
    assert metrics["valid_verb_rate"] == 1.0


def test_operator_court_accepts_ambiguous_cases_without_counting_as_correct(grammar, baseline_decisions):
    output = {
        "relation_label_decisions": [
            _decision(
                "vc_001", "raw_seed_principles.json", "synth_seed.json",
                dominant="", latent=["governs", "populates"], family="authority",
                rule="none",
            ),
        ],
        "ambiguous_cases": [
            {"pair_id": "vc_001", "reason": "underspecified", "candidate_verbs": ["governs", "populates"]}
        ],
    }
    # Mark needs_more_evidence and empty dominant verb
    output["relation_label_decisions"][0]["needs_more_evidence"] = True
    output["relation_label_decisions"][0]["dominant_rosetta_verb"] = ""
    metrics = oc.score_operator_court_output(output, baseline_decisions, grammar)
    assert metrics["ambiguous_count"] == 1
    assert metrics["abstain_count"] == 1
    assert metrics["dominant_operator_accuracy"] == 0.0
    assert metrics["needs_more_evidence_rate"] == 1.0


def test_score_accepts_legacy_verb_corrections_payload(grammar, baseline_decisions):
    legacy_output = {
        "verb_corrections": [
            {
                "pair_id": "vc_001",
                "source": "raw_seed_principles.json",
                "target": "synth_seed.json",
                "connector_verb": "populates",
                "reasoning": "synth seed populated by principles",
            },
            {
                "pair_id": "vc_002",
                "source": "navigation_hologram_theory.md",
                "target": "std_navigation_rosetta_grammar.json",
                "connector_verb": "evidences",
                "reasoning": "theory evidences standard",
            },
        ]
    }
    metrics = oc.score_operator_court_output(legacy_output, baseline_decisions, grammar)
    assert metrics["pair_match_count"] == 2
    assert metrics["exact_match_count"] == 1
    # vc_002 evidences matches baseline; vc_001 populates does not match governs
    assert metrics["verb_accuracy_given_pair"] == 0.5


# ---------------------------------------------------------------------------
# leakage discipline
# ---------------------------------------------------------------------------


def test_operator_court_does_not_include_manual_baseline_evidence(
    grammar, confirmed_pairs, node_cards, relation_cards
):
    sentinel = "__BASELINE_LEAK_SENTINEL__"
    fake_baseline = {
        "routing_decisions": [
            {
                "source": "raw_seed_principles.json",
                "target": "synth_seed.json",
                "connector_verb": "governs",
                "evidence_set": [sentinel + " — JSON is the contract"],
            },
        ]
    }

    cases = oc.build_deterministic_operator_cases(
        confirmed_pairs, node_cards, relation_cards, grammar, include_prior_guess=True
    )

    for variant in oc.PACKET_VARIANTS:
        prompt = oc.build_operator_court_prompt(
            confirmed_pairs,
            grammar=grammar,
            packet_variant=variant,
            deterministic_cases=cases,
        )
        leakage = oc.detect_baseline_leakage(prompt, fake_baseline, extra_sentinels=[sentinel])
        assert sentinel not in prompt, f"variant={variant} leaked sentinel into prompt"
        assert sentinel not in str(leakage["leaked_evidence"]), (
            f"variant={variant} reported sentinel as leaked, but baseline sentinel was never injected"
        )


def test_baseline_leakage_sentinel_detected_when_present():
    sentinel = "__BASELINE_LEAK_SENTINEL__ phrase to spot leaks"
    polluted_prompt = f"some prompt content\n{sentinel}\n"
    fake_baseline = {
        "routing_decisions": [
            {"source": "a", "target": "b", "connector_verb": "feeds", "evidence_set": [sentinel]},
        ]
    }
    leakage = oc.detect_baseline_leakage(
        polluted_prompt, fake_baseline, extra_sentinels=[sentinel]
    )
    assert sentinel in leakage["leaked_evidence"]


# ---------------------------------------------------------------------------
# variant routing
# ---------------------------------------------------------------------------


def test_unknown_variant_raises(grammar, confirmed_pairs):
    with pytest.raises(ValueError):
        oc.build_operator_court_prompt(
            confirmed_pairs, grammar=grammar, packet_variant="not_a_real_variant"
        )


def test_deterministic_cards_variant_requires_cases(grammar, confirmed_pairs):
    with pytest.raises(ValueError):
        oc.build_operator_court_prompt(
            confirmed_pairs,
            grammar=grammar,
            packet_variant="operator_court_deterministic_cards",
            deterministic_cases=None,
        )


def test_authority_plane_delta_for_paper_module_to_standard(grammar):
    delta = oc.authority_plane_delta("paper_module", "standard", grammar)
    assert delta["default_relation_bias"] == "evidences"
    assert "governs" in delta["forbidden_without_evidence"]


def test_authority_plane_delta_for_raw_seed_projection_to_artifact(grammar):
    """raw_seed_projection -> artifact mirrors the real card-builder planes for
    raw_seed/* -> synth_seed.json (which falls through to ``artifact``)."""
    delta = oc.authority_plane_delta("raw_seed_projection", "artifact", grammar)
    assert delta["default_relation_bias"] == "governs"
    assert set(delta["secondary_biases"]) == {"populates", "evidences"}


def test_authority_plane_delta_for_runtime_to_runtime(grammar):
    delta = oc.authority_plane_delta("runtime", "runtime", grammar)
    assert delta["default_relation_bias"] == "feeds"


def test_candidate_latent_verbs_unions_plane_defaults_and_signals(grammar):
    delta = {
        "default_relation_bias": "governs",
        "secondary_biases": ["populates"],
    }
    relation = {"possible_verbs_from_signals": ["evidences", "feeds"]}
    latent = oc.candidate_latent_verbs(delta, relation, grammar)
    assert latent[:2] == ["governs", "populates"]
    assert "evidences" in latent
    assert "feeds" in latent
    # No duplicates
    assert len(latent) == len(set(latent))


def test_operator_court_builds_appeal_rows_for_failed_dominance(grammar, baseline_decisions):
    output = {
        "relation_label_decisions": [
            _decision(
                "vc_001", "raw_seed_principles.json", "synth_seed.json",
                dominant="populates", latent=["populates", "governs"], family="material_flow",
                rule="none", runner_ups=["governs"],
            )
        ]
    }

    appeals = oc.build_operator_court_appeals(
        output,
        baseline_decisions,
        grammar,
        run_id="rpoc_test",
        packet_variant="operator_court_deterministic_cards",
        provider_model="z-ai/glm4.7",
        evidence_refs={"score_ref": "state/example.json"},
    )

    assert len(appeals) == 1
    row = appeals[0]
    assert row["smell_kind"] == "verb_family_gap"
    assert row["expected_verb"] == "governs"
    assert row["dominant_rosetta_verb"] == "populates"
    assert row["status"] == oc.APPEAL_STATUS_PENDING
    assert row["evidence_refs"]["score_ref"] == "state/example.json"


def test_operator_court_builds_missing_rule_appeal_patch(grammar):
    baseline = [{"source": "a", "target": "b", "connector_verb": "populates"}]
    output = {
        "relation_label_decisions": [
            _decision(
                "vc_001", "a", "b",
                dominant="feeds", latent=["feeds", "populates"], family="material_flow",
                rule="none", runner_ups=["populates"],
            )
        ]
    }

    appeals = oc.build_operator_court_appeals(
        output,
        baseline,
        grammar,
        run_id="rpoc_test",
        packet_variant="operator_court_deterministic_cards",
        provider_model="z-ai/glm4.7",
    )

    assert appeals[0]["smell_kind"] == "missing_dominance_rule"
    assert appeals[0]["candidate_rule_patch"]["prefer"] == "populates"
    assert appeals[0]["candidate_rule_patch"]["over"] == ["feeds"]


def test_leakage_appeal_emits_only_when_leakage_present():
    clean = oc.build_leakage_appeal(
        run_id="rpoc_test",
        packet_variant="allowlist_only",
        provider_model="z-ai/glm4.7",
        leakage_check={"leaked_verbs": [], "leaked_evidence": []},
    )
    assert clean is None

    row = oc.build_leakage_appeal(
        run_id="rpoc_test",
        packet_variant="allowlist_only",
        provider_model="z-ai/glm4.7",
        leakage_check={"leaked_verbs": ["a->b:governs"], "leaked_evidence": []},
    )
    assert row is not None
    assert row["smell_kind"] == "leakage_risk"
