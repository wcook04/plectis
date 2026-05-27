from __future__ import annotations

import json
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _readme_text() -> str:
    return (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")


def _cold_start_text() -> str:
    return (MICROCOSM_ROOT / "skills/cold_start_navigation.md").read_text(
        encoding="utf-8"
    )


def _agents_text() -> str:
    return (MICROCOSM_ROOT / "AGENTS.md").read_text(encoding="utf-8")


def test_readme_first_screen_starts_with_hello_then_behavior() -> None:
    section = _readme_text().split("## Choose Your First Screen", 1)[1].split(
        "## Try It On Your Repo",
        1,
    )[0]

    assert "microcosm hello <project>" in section
    assert "microcosm tour --card <project>" in section
    assert "microcosm first-screen <project>" in section
    assert section.index("microcosm hello <project>") < section.index(
        "microcosm tour --card <project>"
    )
    assert section.index("microcosm tour --card <project>") < section.index(
        "microcosm first-screen <project>"
    )
    normalized_section = " ".join(section.split())
    assert (
        "`hello` is the text projection of the first-screen card."
        in normalized_section
    )
    assert "It is not a separate proof surface." in normalized_section
    assert "Evidence counts are accounting, not maturity scores." in section
    assert "Most projects do not publish that boundary" in section
    assert "Read the evidence class counters as a claim-boundary legend:" in section
    for evidence_class in (
        "verified_macro_body_import",
        "external_subprocess_witness",
        "algorithmic_projection",
        "semantic_validator",
        "fixture_schema_replay",
        "fixture_echo_smoke",
    ):
        assert evidence_class in section
    assert "Private-root equivalence" in section
    assert "General proof authority" in section
    assert "Product completeness" in section


def test_readme_installed_path_and_browser_surface_reuse_first_screen() -> None:
    text = _readme_text()
    direct_path = text.split(
        "Or run the same product CLI directly from the checkout without installing the\n"
        "entry point:",
        1,
    )[1].split("After the console command is installed, the first-screen path is:", 1)[
        0
    ]
    installed_path = text.split(
        "After the console command is installed, the first-screen path is:",
        1,
    )[1].split("The quickest human first screen is", 1)[0]
    browser_path = text.split(
        "`http://127.0.0.1:8765/project/status` for the same compact status-card lens",
        1,
    )[1].split("Use `microcosm status --card <project>`", 1)[0]

    direct_hello = "PYTHONPATH=src python3 -m microcosm_core.cli hello ."
    direct_tour_card = "PYTHONPATH=src python3 -m microcosm_core.cli tour --card ."
    assert direct_hello in direct_path
    assert direct_path.index(direct_hello) < direct_path.index(direct_tour_card)
    assert "microcosm hello ." in installed_path
    assert "microcosm first-screen ." in installed_path
    assert installed_path.index("microcosm hello .") < installed_path.index(
        "microcosm tour --card ."
    )
    assert installed_path.index("microcosm tour --card .") < installed_path.index(
        "microcosm first-screen ."
    )
    assert installed_path.index("microcosm first-screen .") < installed_path.index(
        "microcosm status --card ."
    )
    assert "http://127.0.0.1:8765/project/first-screen" in browser_path
    assert browser_path.index("/project/first-screen") < browser_path.index(
        "/project/observatory-card"
    )


def test_microcosm_entry_instructions_separate_hello_from_behavior_proof() -> None:
    cold_start = _cold_start_text()
    agents = _agents_text()

    assert "microcosm hello <project>" in cold_start
    assert "It does not build\n`.microcosm/`" in cold_start
    assert cold_start.index("microcosm hello <project>") < cold_start.index(
        "1. `microcosm tour --card <project>`"
    )
    assert "The compact behavioral path is:" in cold_start

    assert (
        "The human first-screen text projection is `microcosm hello <project>`"
        in agents
    )
    assert "The shared\n   state-writing behavior proof is" in agents
    assert agents.index("microcosm hello <project>") < agents.index(
        "microcosm tour --card <project>"
    )
    assert agents.index("microcosm tour --card <project>") < agents.index(
        "microcosm tour <project>"
    )


def test_agent_entry_routes_concepts_and_mechanisms_from_first_screen() -> None:
    agents = _agents_text()
    cold_start = _cold_start_text()
    entry_packet = json.loads(
        (MICROCOSM_ROOT / "atlas/entry_packet.json").read_text(encoding="utf-8")
    )

    assert "## Concept And Mechanism Entry" in agents
    assert "microcosm first-screen <project>" in agents
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
    assert "microcosm first-screen <project>::doctrine_effect_frame" in allowed_drilldowns
    route = entry_packet["concept_mechanism_entry_route"]
    assert route["agent_entry_ref"] == "AGENTS.md::Concept And Mechanism Entry"
    assert route["first_screen_ref"] == (
        "microcosm first-screen <project>::doctrine_effect_frame"
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
