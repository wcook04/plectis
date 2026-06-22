from __future__ import annotations

import json
from pathlib import Path

from microcosm_core.validators.readme_front_door import validate_readme_front_door


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _cold_start_text() -> str:
    return (MICROCOSM_ROOT / "skills/cold_start_navigation.md").read_text(
        encoding="utf-8"
    )


def _agents_text() -> str:
    return (MICROCOSM_ROOT / "AGENTS.md").read_text(encoding="utf-8")


def test_readme_is_a_bound_human_front_door() -> None:
    # Assurance-preserving projection migration (2026-06-22): the README is the
    # human front door. Its first-screen contract and its bindings (banner,
    # single H1, recognition promise, route rail, witness command bound to the
    # canonical first command, vertical diagram, resolving links, no hero
    # ontology leak, no overclaim, compatibility note present) are owned by the
    # binding validator (validators/readme_front_door.py), exercised
    # adversarially in tests/test_readme_front_door.py. This test asserts the
    # real README satisfies that contract instead of pinning exact prose, so the
    # human projection can evolve freely while its truth stays bound.
    receipt = validate_readme_front_door(MICROCOSM_ROOT)
    assert receipt["status"] == "pass", receipt["blocking_codes"]
    findings = receipt["findings"]
    assert findings["h1"] == "Plectis"
    assert findings["hero_banned_terms"] == []
    assert findings["witness_command_bound"] is True
    assert findings["vertical_diagram_present"] is True
    assert findings["compatibility_note_present"] is True


def test_microcosm_entry_instructions_separate_hello_from_behavior_proof() -> None:
    cold_start = _cold_start_text()
    agents = _agents_text()
    cold_start_steps = cold_start.split("## Steps", 1)[1].split(
        "## Authority And Evidence Drilldowns",
        1,
    )[0]

    assert "plectis hello <project>" in cold_start
    assert "It does not build\n`.microcosm/`" in cold_start
    assert cold_start.index("plectis hello <project>") < cold_start.index(
        "1. `plectis tour --card <project>`"
    )
    assert "The compact behavioral path is:" in cold_start
    assert "3. Run `plectis hello <project>`" in cold_start_steps
    assert "python3 -m microcosm_core hello <project>" in cold_start_steps
    assert "python3 -m microcosm_core.cli hello <project>" not in cold_start_steps
    assert "4. Run `plectis tour --card <project>`" in cold_start_steps
    assert cold_start_steps.index("plectis hello <project>") < cold_start_steps.index(
        "plectis tour --card <project>"
    )

    assert (
        "The human first-screen text projection is `plectis hello <project>`"
        in agents
    )
    # AGENTS.md routes the agent to the README's human sections; after the
    # assurance migration those are the `Choose a route` table and the
    # `How the result stays honest` section (the old `Public Repo Map` /
    # `Component Map` headings were retired with the README rewrite).
    assert (
        "In that README, use\n   the `Choose a route` table and "
        "`How the result stays honest`"
        in agents
    )
    assert agents.index("`Choose a route` table") < agents.index(
        "## Accepted Public Runtime Spine"
    )
    agent_smoke = agents.split(
        "The smoke target writes ignored receipts under `.microcosm/smoke/`, "
        "validates",
        1,
    )[1].split("Before publishing", 1)[0]
    assert "Plectis smoke check: pass" in agent_smoke
    assert "authority: pass" in agent_smoke
    assert "workingness: clear" in agent_smoke
    assert "served status: pass" in agent_smoke
    assert "plectis first-screen --card ." in agent_smoke
    assert (
        agent_smoke.index("plectis hello .")
        < agent_smoke.index("plectis first-screen --card .")
        < agent_smoke.index("plectis tour --card .")
    )
    assert "`plectis first-screen --card` is the compact JSON reader map" in agent_smoke
    assert "The shared\n   state-writing behavior proof is" in agents
    assert agents.index("plectis hello <project>") < agents.index(
        "plectis tour --card <project>"
    )
    assert agents.index("plectis tour --card <project>") < agents.index(
        "plectis tour <project>"
    )


def test_agent_entry_routes_concepts_and_mechanisms_from_first_screen() -> None:
    agents = _agents_text()
    cold_start = _cold_start_text()
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )

    assert "## Concept And Mechanism Entry" in agents
    assert "plectis first-screen <project>" in agents
    assert "doctrine_effect_frame" in agents
    assert "standards/std_microcosm_concept.json" in agents
    assert "standards/std_microcosm_mechanism.json" in agents
    assert "concept_handle_requires_entry_surface" in agents
    assert "mechanism_handle_requires_runnable_contract" in agents
    assert "concept_mechanism_requires_population_specimen_loop" in agents
    assert "concept_mechanism_entry_route.population_specimens" in agents
    assert "first-screen route shape" in agents
    assert "voice-to-doctrine refinement" in agents

    assert "## Concept And Mechanism Drilldown" in cold_start
    assert "AGENTS.md::Concept And Mechanism Entry" in cold_start
    assert "concept_mechanism_entry_route.population_specimens" in cold_start
    assert "concept_mechanism_requires_population_specimen_loop" in cold_start

    allowed_drilldowns = set(entry_packet["allowed_drilldowns"])
    assert "atlas/entry_packet.json::concept_mechanism_entry_route" in allowed_drilldowns
    assert (
        "atlas/entry_packet.json::concept_mechanism_entry_route.population_specimens"
        in allowed_drilldowns
    )
    assert "plectis first-screen <project>::doctrine_effect_frame" in allowed_drilldowns
    route = entry_packet["concept_mechanism_entry_route"]
    assert route["agent_entry_ref"] == "AGENTS.md::Concept And Mechanism Entry"
    assert route["first_screen_ref"] == (
        "plectis first-screen <project>::doctrine_effect_frame"
    )
    assert {row["kind_id"] for row in route["standards"]} == {
        "concept",
        "mechanism",
    }
    assert route["population_loop"]["composition_root"] == (
        "atlas/entry_packet.json::concept_mechanism_entry_route"
    )
    assert len(route["population_specimens"]) >= 3
    for specimen in route["population_specimens"]:
        assert specimen["concept_binding"]["concept_role"]
        assert specimen["concept_binding"]["payload_shape_ref"]
        assert specimen["mechanism_binding"]["mechanism_role"]
        assert specimen["mechanism_binding"]["transformation_shape"]
        assert specimen["mechanism_binding"]["state_or_proof_effect"]
        assert specimen["mechanism_binding"]["concept_pair_ref"].endswith(
            ".concept_binding"
        )
        assert specimen["validator_refs"]
        assert specimen["anti_claims"]
        assert specimen["omission_receipt"]["omitted"]
