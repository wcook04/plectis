"""Regression coverage for Wave 044 Rosetta context compression."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from system.lib.navigation_context_rosetta import build_navigation_context_rosetta


REPO_ROOT = Path(__file__).resolve().parents[3]
WAVE_DIR = (
    REPO_ROOT
    / "state/meta_missions/system_microcosm_probe/ledgers/navigation_hologram_microcosm/wave_044"
)
ROSETTA_SCANNER_BUDGET = 12000


def _rows_by_kind(packet: dict) -> dict[str, dict]:
    return {row["kind_id"]: row for row in packet["representative_context_rows"]}


def test_rosetta_packet_covers_all_kind_atlas_rows_before_query() -> None:
    packet = build_navigation_context_rosetta(REPO_ROOT, context_budget=ROSETTA_SCANNER_BUDGET)
    rows = _rows_by_kind(packet)

    assert packet["kind"] == "navigation_context_rosetta_packet"
    assert packet["authority_posture"] == "read_only_rosetta_context_probe_not_production_navigation"
    # The load-bearing invariant is that the packet covers every Kind Atlas row,
    # not the literal kind count (which grows as new kinds are added — e.g. the
    # 14th kind annex_distillation_patterns landed without a corresponding atlas
    # adjustment to this test). Assert the invariant + a sane lower bound.
    assert packet["budget"]["coverage_count"] == packet["budget"]["total_kinds"]
    assert packet["budget"]["total_kinds"] >= 13
    assert packet["budget"]["estimated_cost"] <= packet["budget"]["context_budget"]
    assert set(rows) >= {
        "paper_modules",
        "standards",
        "python_files",
        "python_scopes",
        "frontend_views",
        "frontend_components",
        "skills",
        "system_terms",
        "principles",
        "axiom_candidates",
        "raw_seed_shards",
        "compression_profiles",
        "annex_patterns",
    }


def test_rosetta_semantic_grammar_names_nouns_verbs_and_impacts() -> None:
    packet = build_navigation_context_rosetta(REPO_ROOT, context_budget=ROSETTA_SCANNER_BUDGET)
    grammar = packet["semantic_grammar"]
    math_model = packet["math_model"]

    assert grammar["governing_standard_ref"] == "codex/standards/std_navigation_rosetta_grammar.json"
    assert "source authority" in grammar["context_atom"]
    assert {"row", "scope", "facet", "band"} <= set(grammar["nouns"])
    assert {"feeds", "blocks", "governs", "evidences", "populates", "invalidates"} <= set(
        grammar["verbs"]
    )
    assert "evidences_but_does_not_authorize" in grammar["complex_verbs"]
    assert {"direct_enumeration", "dependency_ordered", "calibrated_slate", "beam_telescope"} <= set(
        grammar["selector_policies"]
    )
    assert {"semantic_flow", "authority_flow", "freshness_risk", "mutation_risk"} <= set(
        grammar["impact_vector"]
    )
    assert "confidence(edge)" in grammar["edge_need_formula"]
    assert "role_prior(edge,task)" in grammar["edge_need_formula"]
    assert math_model["objective_order"][0] == "coverage_floor"
    assert math_model["paper_module_ref"] == "codex/doctrine/paper_modules/navigation_rosetta_math.md"
    assert "distinguishable decisions" in math_model["layer_depth_rule"]
    assert "q_u" in math_model["variables"]


def test_rosetta_rows_preserve_gaps_and_population_honesty() -> None:
    rows = _rows_by_kind(build_navigation_context_rosetta(REPO_ROOT, context_budget=ROSETTA_SCANNER_BUDGET))

    python_scope = rows["python_scopes"]
    assert python_scope["atom_id"] == "context_atom:python_scopes:representative"
    assert python_scope["selector_policy_id"] == "direct_enumeration"
    # python_scopes' gap profile changes as emitters land. The invariant is not
    # a literal stale band id; it is honest population state plus a row_ref or a
    # visible gap signal when a representative row is not available.
    assert python_scope["population_mode"] in {"compiled", "unpopulated"}
    assert python_scope["support_status"] in {"option_surface_supported", "projection_gap"}
    assert isinstance(python_scope["axis_vector"]["unpopulated_units"], list)
    if python_scope["population_mode"] == "compiled" and python_scope["support_status"] == "option_surface_supported":
        # When the option-surface adapter actually populates the kind, confidence
        # may legitimately be high. profile_gap may be None when there is no
        # active row-level projection gap.
        assert python_scope["confidence"]["tier"] in {"high", "medium"}
        assert python_scope["row_ref"]
    else:
        # When the kind is still in projection-gap state, confidence must NOT
        # claim "high" — the scorer must respect population honesty.
        assert python_scope["confidence"]["tier"] != "high"
        assert python_scope["profile_gap"] is not None

    paper = rows["paper_modules"]
    # Representative fixture invariants (stable regardless of budget allocation).
    assert paper["representative"]["source_ref"].endswith("navigation_hologram_theory.md")
    assert paper["confidence"]["tier"] == "high"
    # Budget-dependent invariant: paper_modules is selectable at flag or card
    # bands; if the budget upgraded it to card, the populated_card payload must
    # carry the fixture slug.
    assert paper["selected_band"] in {"flag", "card"}
    if paper["selected_band"] == "card":
        assert paper["populated_card"]["slug"] == "navigation_hologram_theory"

    standards = rows["standards"]
    # Same shape: representative fixture is stable; band depends on budget.
    assert standards["selected_band"] in {"flag", "card"}
    if standards["selected_band"] == "card":
        assert standards["populated_card"]["standard_id"] == "std_navigation_contract"


def test_rosetta_rows_are_context_atoms_with_selector_provenance() -> None:
    rows = _rows_by_kind(build_navigation_context_rosetta(REPO_ROOT, context_budget=ROSETTA_SCANNER_BUDGET))

    for kind_id, row in rows.items():
        assert row["atom_id"] == f"context_atom:{kind_id}:representative"
        assert row["selector_policy_id"] == "direct_enumeration"
        assert row["confidence"]["scorer_status"] == "heuristic_v0"
        assert row["confidence"]["tier"] in {"high", "medium", "low"}
        assert row["extraction_mode"] in {"compiled", "candidate_inference"}
        assert row["population_mode"] in {"compiled", "unpopulated"}
        # row_ref invariant: populated rows must carry a row_ref. A missing /
        # profile-gap row may omit row_ref only when it explicitly exposes
        # missing-substrate metadata so coverage-first navigation still
        # surfaces the kind without claiming false population.
        if row["population_mode"] == "compiled" and not row.get("profile_gap"):
            assert row["row_ref"], (
                f"populated kind {kind_id!r} must carry row_ref; got None/empty"
            )
        else:
            has_gap_signal = bool(
                row.get("profile_gap")
                or (row.get("axis_vector") or {}).get("unpopulated_units")
                or row["population_mode"] == "unpopulated"
            )
            assert has_gap_signal, (
                f"row for kind {kind_id!r} omits row_ref but exposes no gap signal"
            )


def test_navigation_context_rosetta_kernel_command_emits_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--navigation-context-rosetta",
            "--context-budget",
            str(ROSETTA_SCANNER_BUDGET),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    packet = json.loads(result.stdout)
    assert packet["kind"] == "navigation_context_rosetta_packet"
    # Coverage-first invariant (robust to atlas growth): every kind atlas row
    # is represented; coverage_count == total_kinds.
    assert packet["budget"]["coverage_count"] == packet["budget"]["total_kinds"]
    assert packet["budget"]["coverage_count"] >= 13
    assert packet["budget"]["estimated_cost"] <= packet["budget"]["context_budget"]
    assert packet["semantic_grammar"]["rosetta_rule"].startswith("The smallest packet")


def test_wave_044_artifacts_match_rosetta_contract() -> None:
    packet = json.loads((WAVE_DIR / "navigation_context_rosetta_packet_v0.json").read_text(encoding="utf-8"))
    grammar = json.loads((WAVE_DIR / "rosetta_navigation_grammar_v0.json").read_text(encoding="utf-8"))

    assert packet["schema_version"] == "navigation_context_rosetta_packet_v0"
    assert grammar["schema_version"] == "rosetta_navigation_grammar_v0"
    assert grammar["representative_rows_count"] == len(packet["representative_context_rows"])
    assert grammar["governing_standard_ref"] == "codex/standards/std_navigation_rosetta_grammar.json"
    assert grammar["math_model"]["name"] == "coverage_first_information_density_knapsack_v0"
    assert grammar["semantic_grammar"]["governing_standard_ref"] == "codex/standards/std_navigation_rosetta_grammar.json"
    assert grammar["rosetta_grammar"]["holographic_property"].startswith("Every selected row")


def test_rosetta_grammar_standard_defines_write_and_read_shapes() -> None:
    standard = json.loads(
        (REPO_ROOT / "codex/standards/std_navigation_rosetta_grammar.json").read_text(encoding="utf-8")
    )

    assert standard["id"] == "std_navigation_rosetta_grammar"
    assert "noun_shape" in standard
    assert "context_atom_shape" in standard
    assert "relation_verb_shape" in standard
    assert "edge_instance_shape" in standard
    assert "complex_relation_shape" in standard
    assert "selector_policy_shape" in standard
    assert "impact_axis_shape" in standard
    assert {policy["policy_id"] for policy in standard["selector_policies"]} >= {
        "direct_enumeration",
        "dependency_ordered",
        "calibrated_slate",
        "beam_telescope",
        "impact_before_mutation",
    }
    assert {"feeds", "blocks", "governs", "evidences"} <= set(
        standard["relation_verb_shape"]["base_verbs"]
    )
    assert "context atoms" in standard["core_law"]["flag"]
    assert standard["mathematical_model"]["objective_order"][0] == "coverage_floor"
    assert "role_prior(edge,task)" in standard["mathematical_model"]["edge_need_function"]
    assert "system_terms" in standard["layer_depth_policy"]["examples"]
    assert {item["id"] for item in standard["proof_obligations"]} >= {
        "coverage_before_depth",
        "population_honesty",
        "bidirectional_relation_readability",
        "selector_policy_honesty",
        "context_atom_provenance",
        "no_query_dependency",
    }


def test_navigation_contract_edge_rows_carry_currentness_and_proof_fields() -> None:
    standard = json.loads(
        (REPO_ROOT / "codex/standards/std_navigation_contract.json").read_text(encoding="utf-8")
    )
    edge_shape = standard["edge_row_shape"]

    assert {
        "edge_id",
        "source_ref",
        "target_ref",
        "verb",
        "reverse_verb",
        "forward_gloss",
        "reverse_gloss",
        "confidence",
        "reason",
        "extraction_mode",
        "validity",
    } <= set(edge_shape["required_fields"])
    assert {"same_graph_contract", "selector_policy_id", "impact_vector", "role_prior"} <= set(
        edge_shape["optional_fields"]
    )


def test_navigation_rosetta_math_paper_module_names_core_proofs() -> None:
    module = (REPO_ROOT / "codex/doctrine/paper_modules/navigation_rosetta_math.md").read_text(
        encoding="utf-8"
    )

    assert "## Mathematical Core" in module
    assert "## Annex Pressure Refinements" in module
    assert "## Layer Depth Rule" in module
    assert "## Proof Sketch" in module
    assert "selected context atoms" in module
    assert "Coverage before depth" in module
    assert "Layer depth is a function of distinguishable decisions" in module
