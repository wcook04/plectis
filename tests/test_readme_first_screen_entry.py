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


def test_readme_opening_call_to_action_prefers_hello_over_compile() -> None:
    opening = _readme_text().split("## Choose Your First Screen", 1)[0]

    assert (
        "For a one-page cold-clone path, start with "
        "[QUICKSTART.md](QUICKSTART.md)."
    ) in opening
    assert "## Public Repo Map" in opening
    assert (
        "Use this map before opening the longer reference body or raw receipt trees:"
        in opening
    )
    for row in (
        "| [QUICKSTART.md](QUICKSTART.md) | "
        "One-page cold-clone run path and boundary check. |",
        "| [AGENTS.md](AGENTS.md) | "
        "Agent entry contract and public authority membrane. |",
        "| [CONSTITUTION.md](CONSTITUTION.md) / [AXIOMS.md](AXIOMS.md) / "
        "[PRINCIPLES.md](PRINCIPLES.md) / "
        "[ANTI_PRINCIPLES.md](ANTI_PRINCIPLES.md) | Root doctrine: "
        "authority spine, public-safe source rules, operating principles, "
        "and rejected failure shapes. |",
        "| [CONTRIBUTING.md](CONTRIBUTING.md) | "
        "Public verification floor, standalone export path, and contribution "
        "boundaries. |",
        "| [SECURITY.md](SECURITY.md) | "
        "Secret-exclusion and vulnerability-reporting boundary. |",
        "| [.github/workflows/ci.yml](.github/workflows/ci.yml) / "
        "[Makefile](Makefile) | GitHub Actions and local command surface; "
        "both route through `make ci`, including package install smoke. |",
        "| [pyproject.toml](pyproject.toml) / [MANIFEST.in](MANIFEST.in) | "
        "Package metadata, console entry point, and source distribution inventory. |",
        "| [src/microcosm_core/](src/microcosm_core/) / [tests/](tests/) | "
        "Runnable substrate and regression contracts. |",
        "| [core/](core/) / [standards/](standards/) / "
        "[paper_modules/](paper_modules/) | Public registries, standards, and "
        "bounded organ summaries. |",
        "| [examples/](examples/) / [fixtures/](fixtures/) / "
        "[receipts/](receipts/) | Input bundles, negative cases, and "
        "drilldown evidence. |",
    ):
        assert row in opening
    assert "This map is navigation only." in opening
    for anti_claim in (
        "release",
        "hosting",
        "provider calls",
        "source\nmutation",
        "private-root equivalence",
        "proof authority",
    ):
        assert anti_claim in opening
    assert opening.index("[QUICKSTART.md](QUICKSTART.md)") < opening.index(
        "## Public Repo Map"
    )
    assert opening.index("## Public Repo Map") < opening.index(
        "## Component Map"
    )
    assert opening.index("[CONSTITUTION.md](CONSTITUTION.md)") < opening.index(
        "## Component Map"
    )
    assert opening.index("## Component Map") < opening.index(
        "From an uninstalled source checkout"
    )
    assert "Read the tree as cooperating component families" in opening
    for component_row in (
        "| Runtime package | [src/microcosm_core/](src/microcosm_core/) | "
        "CLI-backed local behavior: first-screen cards, project scan, route "
        "selection, validators, server, and release export. |",
        "| Command cards | `microcosm hello`, `microcosm tour --card`, "
        "`microcosm status --card`, `microcosm authority --card`, "
        "`microcosm workingness --card` | The copyable first screen, "
        "behavior proof, evidence classes, authority ceiling, and failure "
        "envelope. |",
        "| Public doctrine | [core/](core/), [standards/](standards/), "
        "[paper_modules/](paper_modules/), [atlas/](atlas/) | Organ registry, "
        "standards, bounded explanations, and the first-screen entry packet. |",
        "| Evidence fixtures | [examples/](examples/), [fixtures/](fixtures/), "
        "[receipts/](receipts/) | Public-safe input bundles, negative cases, "
        "drilldown receipts, and copied artifact bodies. |",
        "| Source capsules | `source_modules/` plus "
        "`source_module_manifest.json` inside bundles | Non-secret macro "
        "source bodies with target paths, digests, anchors, omissions, and "
        "light-edit receipts. |",
        "| Validation shell | [tests/](tests/), [Makefile](Makefile), "
        "[.github/workflows/ci.yml](.github/workflows/ci.yml) | The public "
        "verification floor that keeps docs, CLI cards, fixtures, "
        "package install, and standalone export honest. |",
    ):
        assert component_row in opening
    assert "This component map is still navigation, not authority." in opening
    assert "From an uninstalled source checkout" in opening
    assert "PYTHONPATH=src python3 -m microcosm_core hello ." in opening
    assert "After `python3 -m pip install -e '.[test]'` or `make install`" in opening
    assert "make package-smoke" in opening
    assert "make ci` includes that package smoke" in opening
    assert "microcosm hello ." in opening
    assert "microcosm compile ." in opening
    assert "full `.microcosm/` rebuild JSON" in opening
    assert opening.index("PYTHONPATH=src python3 -m microcosm_core hello .") < (
        opening.index("microcosm hello .")
    )
    assert opening.index("microcosm hello .") < opening.index("microcosm compile .")
    assert "Try it on your repo with one local command: `microcosm compile .`" not in opening


def test_readme_first_screen_starts_with_hello_then_behavior() -> None:
    section = _readme_text().split("## Choose Your First Screen", 1)[1].split(
        "## Try It On Your Repo",
        1,
    )[0]

    assert "microcosm hello <project>" in section
    assert "microcosm tour --card <project>" in section
    assert "microcosm first-screen --card <project>" in section
    assert "microcosm first-screen <project>" in section
    assert section.index("microcosm hello <project>") < section.index(
        "microcosm tour --card <project>"
    )
    assert section.index("microcosm tour --card <project>") < section.index(
        "microcosm first-screen --card <project>"
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
    assert "microcosm authority --card && microcosm workingness --card" not in section
    assert (
        "| Safety/evals engineer | `microcosm tour --card <project>`, then "
        "`microcosm status --card <project>`, then `microcosm authority --card` / "
        "`microcosm workingness --card` |"
    ) in section
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
    assert "When a bundle includes `source_modules/`" in section
    assert "exact non-secret source capsules" in normalized_section
    assert "source_module_manifest.json" in section
    assert (
        "navigation authority for copied targets, digests, anchors, and omissions"
        in normalized_section
    )


def test_readme_installed_path_and_browser_surface_reuse_first_screen() -> None:
    text = _readme_text()
    try_it = text.split("## Try It On Your Repo", 1)[1].split(
        "## What This Proves",
        1,
    )[0]
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

    direct_hello = "PYTHONPATH=src python3 -m microcosm_core hello ."
    direct_tour_card = "PYTHONPATH=src python3 -m microcosm_core tour --card ."
    direct_first_screen_card = (
        "PYTHONPATH=src python3 -m microcosm_core first-screen --card ."
    )
    assert "./bootstrap.sh" in try_it
    assert "./bootstrap.sh --dry-run" in try_it
    assert ".microcosm/cold_clone_probe.json" in try_it
    assert try_it.index("./bootstrap.sh") < try_it.index("python3 -m pip install .")
    assert direct_hello in direct_path
    assert direct_path.index(direct_hello) < direct_path.index(direct_tour_card)
    assert direct_first_screen_card in direct_path
    assert (
        "PYTHONPATH=src python3 -m microcosm_core evidence list . --limit 25"
        in direct_path
    )
    assert (
        "PYTHONPATH=src python3 -m microcosm_core evidence inspect . .microcosm/evidence/routes.json"
        in direct_path
    )
    assert "python3 -m microcosm_core.cli" not in direct_path
    assert "microcosm hello ." in installed_path
    assert "microcosm first-screen --card ." in installed_path
    assert installed_path.index("microcosm hello .") < installed_path.index(
        "microcosm tour --card ."
    )
    assert installed_path.index("microcosm tour --card .") < installed_path.index(
        "microcosm first-screen --card ."
    )
    assert installed_path.index("microcosm first-screen --card .") < (
        installed_path.index("microcosm status --card .")
    )
    assert "microcosm workingness --card" in installed_path
    assert "microcosm evidence list . --limit 25" in installed_path
    assert "microcosm evidence inspect . .microcosm/evidence/routes.json" in (
        installed_path
    )
    assert "\nmicrocosm workingness\n" not in installed_path
    assert "\nmicrocosm evidence list .\n" not in installed_path
    assert "http://127.0.0.1:8765/project/first-screen" in browser_path
    assert "/project/first-screen-full" in browser_path
    assert "http://127.0.0.1:8765/workingness-card" in browser_path
    assert "/workingness` only when you need the full per-organ failure map" in (
        browser_path
    )
    assert "same compact one-screen\nreader map" in browser_path
    assert "microcosm first-screen --card <project>" in browser_path
    assert browser_path.index("/project/first-screen") < browser_path.index(
        "/project/observatory-card"
    )
    assert browser_path.index("/project/observatory") < browser_path.index(
        "/project/first-screen-full"
    )
    assert browser_path.index("/workingness-card") < browser_path.index(
        "/workingness` only"
    )


def test_microcosm_entry_instructions_separate_hello_from_behavior_proof() -> None:
    cold_start = _cold_start_text()
    agents = _agents_text()
    cold_start_steps = cold_start.split("## Steps", 1)[1].split(
        "## Authority And Evidence Drilldowns",
        1,
    )[0]

    assert "microcosm hello <project>" in cold_start
    assert "It does not build\n`.microcosm/`" in cold_start
    assert cold_start.index("microcosm hello <project>") < cold_start.index(
        "1. `microcosm tour --card <project>`"
    )
    assert "The compact behavioral path is:" in cold_start
    assert "3. Run `microcosm hello <project>`" in cold_start_steps
    assert "python3 -m microcosm_core hello <project>" in cold_start_steps
    assert "python3 -m microcosm_core.cli hello <project>" not in cold_start_steps
    assert "4. Run `microcosm tour --card <project>`" in cold_start_steps
    assert cold_start_steps.index("microcosm hello <project>") < cold_start_steps.index(
        "microcosm tour --card <project>"
    )

    assert (
        "The human first-screen text projection is `microcosm hello <project>`"
        in agents
    )
    assert (
        "In that README, use\n   `Public Repo Map` and `Component Map`"
        in agents
    )
    assert agents.index("`Public Repo Map` and `Component Map`") < agents.index(
        "## Accepted Public Runtime Spine"
    )
    agent_smoke = agents.split(
        "The smoke target writes ignored receipts under `.microcosm/smoke/`, "
        "validates",
        1,
    )[1].split("Before publishing", 1)[0]
    assert "Microcosm smoke check: pass" in agent_smoke
    assert "authority: pass" in agent_smoke
    assert "workingness: clear" in agent_smoke
    assert "served status: pass" in agent_smoke
    assert "microcosm first-screen --card ." in agent_smoke
    assert (
        agent_smoke.index("microcosm hello .")
        < agent_smoke.index("microcosm first-screen --card .")
        < agent_smoke.index("microcosm tour --card .")
    )
    assert "`microcosm first-screen --card` is the compact JSON reader map" in agent_smoke
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
