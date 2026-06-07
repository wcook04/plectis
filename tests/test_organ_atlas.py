"""Contract for the generated organ atlas surfaces.

This is the drift gate that replaces the old hand-maintained 47-id wall in
README/AGENTS. The canonical per-organ inventory is now generated from
substrate; this test proves it stays complete, in sync, and non-overclaiming.
"""

from __future__ import annotations

import shlex
from pathlib import Path

from microcosm_core.projections.organ_atlas import (
    OVERCLAIM_PHRASES,
    build,
    load_model,
)
from microcosm_core.schemas import read_json_strict


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _accepted_registry_ids() -> set[str]:
    registry = read_json_strict(MICROCOSM_ROOT / "core/organ_registry.json")
    return {
        str(row.get("organ_id"))
        for row in registry.get("implemented_organs", [])
        if isinstance(row, dict)
        and row.get("status") == "accepted_current_authority"
    }


def test_families_partition_the_registry() -> None:
    model = load_model(MICROCOSM_ROOT)
    cov = model["coverage"]
    assert cov["missing_from_families"] == []
    assert cov["extra_in_families"] == []
    # every organ lands in exactly one family
    seen: list[str] = []
    for fam in model["families"]:
        for card in fam["cards"]:
            seen.append(card["organ_id"])
    assert sorted(seen) == sorted(_accepted_registry_ids())
    assert len(seen) == len(set(seen))


def test_atlas_model_is_complete_and_non_overclaiming() -> None:
    model = load_model(MICROCOSM_ROOT)
    cov = model["coverage"]
    assert cov["missing_glosses"] == [], (
        "every accepted organ needs a gloss in core/organ_atlas.json; "
        "regenerate with the comprehension pass"
    )
    assert cov["extra_glosses"] == []
    assert cov["empty_gloss_fields"] == []
    assert cov["overclaim_cards"] == []
    assert cov["ceiling_without_negation"] == []
    assert model["status"] == "pass"
    assert model["blocking_reasons"] == []


def test_first_commands_are_copyable_from_package_root() -> None:
    model = load_model(MICROCOSM_ROOT)
    for family in model["families"]:
        for card in family["cards"]:
            first_command = card["first_command"]
            assert " microcosm-substrate/" not in first_command, (
                "first commands are shown to readers already inside the "
                f"package root: {card['organ_id']} -> {first_command}"
            )
            assert not first_command.startswith("python -m "), (
                "source-checkout first commands should use python3 or the "
                f"installed console script: {card['organ_id']} -> {first_command}"
            )


def test_generated_files_are_in_sync_with_substrate() -> None:
    """Generated atlas files must match `--write` output exactly."""
    result = build(MICROCOSM_ROOT, write=False)
    assert result["status"] == "pass", result["blocking_reasons"]
    assert result["drift"] == [], (
        "generated atlas files drifted from substrate; run "
        "`PYTHONPATH=src python3 scripts/build_organ_atlas.py --write`"
    )
    assert (MICROCOSM_ROOT / "ORGANS.md").is_file()
    assert (MICROCOSM_ROOT / "ARCHITECTURE.md").is_file()
    assert (MICROCOSM_ROOT / "AGENT_ROUTES.md").is_file()
    assert (MICROCOSM_ROOT / "atlas/agent_task_routes.json").is_file()


def test_every_organ_and_a_first_command_appears_in_organs_md() -> None:
    text = (MICROCOSM_ROOT / "ORGANS.md").read_text(encoding="utf-8")
    for organ_id in _accepted_registry_ids():
        assert f"`{organ_id}`" in text, f"{organ_id} missing from ORGANS.md"
    # cards expose runnable commands and claim ceilings, not just names
    assert text.count("**First command:**") == len(_accepted_registry_ids())
    assert text.count("**Does not authorize:**") == len(_accepted_registry_ids())
    assert text.count("- **Source relations:**") == len(_accepted_registry_ids())
    assert text.count("standard [`standards/std_microcosm_") == len(
        _accepted_registry_ids()
    )
    assert text.count("concept `organ_doctrine_row:") == len(_accepted_registry_ids())
    assert text.count("mechanism `organ_doctrine_row:") == len(_accepted_registry_ids())
    assert text.count("acceptance `") == len(_accepted_registry_ids())
    assert (
        "handle `organ-surface-contract::coverage.source_module_file_graph."
        "edges_by_organ[organ_id=cold_reader_route_map]`"
    ) in text
    assert "`microcosm organ-topology --organ cold_reader_route_map`" in text


def test_every_organ_resolves_capsule_compression() -> None:
    model = load_model(MICROCOSM_ROOT)
    cov = model["coverage"]
    assert cov["missing_capsule_compression"] == []
    assert cov["missing_capsule_one_line"] == []
    assert cov["missing_capsule_card"] == []
    assert cov["missing_capsule_authority_ceiling"] == []
    assert sum(cov["capsule_join_status_counts"].values()) == len(
        _accepted_registry_ids()
    )

    for family in model["families"]:
        for card in family["cards"]:
            assert card["one_line"]
            assert card["compression_card"]
            assert card["compression_authority_ceiling"]
            assert card["capsule_id"].startswith("paper_module.")
            assert card["capsule_join_status"] in {
                "direct",
                "paper_module_ref_bridge",
            }


def test_organs_md_starts_with_one_line_glance_ladder() -> None:
    text = (MICROCOSM_ROOT / "ORGANS.md").read_text(encoding="utf-8")
    assert "## Microcosm at a glance — every organ in one line" in text
    assert (
        text.index("## Microcosm at a glance — every organ in one line")
        < text.index("## How to read a card")
        < text.index("\n## Entry & Reveal\n")
    )
    glance = text.split(
        "## Microcosm at a glance — every organ in one line",
        1,
    )[1].split("## How to read a card", 1)[0]
    for organ_id in _accepted_registry_ids():
        assert f"`{organ_id}`" in glance, f"{organ_id} missing from glance ladder"
    assert "### Entry & Reveal at a glance" in glance
    assert glance.index("### Entry & Reveal at a glance") < glance.index(
        "### Architecture & Navigation at a glance"
    )
    assert "Why the counts are honest" in glance
    assert "first command `microcosm" in glance
    assert "provenance `paper_module." in glance


def test_every_organ_has_paper_module_drilldown() -> None:
    model = load_model(MICROCOSM_ROOT)
    missing = [
        card["organ_id"]
        for family in model["families"]
        for card in family["cards"]
        if not card.get("paper_module")
    ]
    assert missing == []


def test_every_organ_card_exposes_doctrine_drilldowns() -> None:
    model = load_model(MICROCOSM_ROOT)
    missing = []
    for family in model["families"]:
        for card in family["cards"]:
            if not all(
                card.get(field)
                for field in (
                    "standard",
                    "concept_projection",
                    "mechanism_projection",
                    "acceptance",
                )
            ):
                missing.append(card["organ_id"])
    assert missing == []


def test_non_1_to_1_paper_module_links_are_data_declared() -> None:
    atlas = read_json_strict(MICROCOSM_ROOT / "core/organ_atlas.json")
    declared = {
        str(row.get("organ_id")): str(row.get("paper_module_ref"))
        for row in atlas.get("organs", [])
        if isinstance(row, dict) and row.get("paper_module_ref")
    }
    assert declared["corpus_readiness_mathlib_absence_gate"] == (
        "paper_modules/corpus_readiness_mathlib_absence.md"
    )

    model = load_model(MICROCOSM_ROOT)
    cards = {
        card["organ_id"]: card
        for family in model["families"]
        for card in family["cards"]
    }
    assert cards["corpus_readiness_mathlib_absence_gate"]["paper_module"] == declared[
        "corpus_readiness_mathlib_absence_gate"
    ]


def test_organs_md_carries_evidence_legend_and_no_overclaim() -> None:
    text = (MICROCOSM_ROOT / "ORGANS.md").read_text(encoding="utf-8")
    lowered = text.lower()
    # positive overclaims must never appear; honest anti-claim nouns (e.g.
    # "benchmark score", "whole-system correctness") may appear inside ceilings.
    for phrase in OVERCLAIM_PHRASES:
        assert phrase not in lowered, f"overclaim phrase in ORGANS.md: {phrase}"
    for evidence_class in (
        "semantic_validator",
        "algorithmic_projection",
        "external_subprocess_witness",
        "verified_macro_body_import",
        "fixture_echo_smoke",
        "fixture_schema_replay",
    ):
        assert f"`{evidence_class}`" in text
    assert "navigation metadata" in text
    assert "does not authorize" in lowered


def test_architecture_md_routes_to_commands_and_kernel() -> None:
    text = (MICROCOSM_ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    # diagrams route to real commands/files
    assert "```mermaid" in text
    assert "microcosm hello ." in text
    assert "microcosm tour --card ." in text
    assert "microcosm observe --card PROJECT" in text
    assert "microcosm observe PROJECT (event rows)" in text
    assert "`microcosm observe --card <project>`" in text
    assert "core/organ_evidence_classes.json" in text
    assert "core/organ_registry.json" in text
    assert "[ORGANS.md](ORGANS.md)" in text
    assert "## Level 3 — source-module file and shard routing" in text
    assert "organ-surface-contract::coverage.source_module_file_graph" in text
    assert "Accepted organs with source relations" in text
    assert "Source-module edges" in text
    assert "Validation refs (per-organ aggregate)" in text
    assert "`microcosm organ-topology --organ cold_reader_route_map`" in text
    assert "microcosm organ-topology --relation-type file_to_file" in text
    assert "microcosm organ-topology --relation-type shard_to_shard" in text
    assert "Dynamic edge truth remains in `microcosm organ-topology`" in text
    # kernel primitives are projected from the kernel, not hand-listed
    kernel = read_json_strict(MICROCOSM_ROOT / "core/architecture_kernel.json")
    for prim in kernel.get("primitives", []):
        assert str(prim.get("public_name")) in text
    # every family is linked from the architecture map
    families = read_json_strict(MICROCOSM_ROOT / "core/organ_families.json")
    for fam in families.get("families", []):
        assert str(fam.get("label")) in text


def test_organs_md_is_debatched_in_headings() -> None:
    """Operator contract: import-provenance 'batch' vocabulary must not appear in
    the public organ headings. The stable organ_id still travels as a backticked
    id line under each display-name heading."""
    text = (MICROCOSM_ROOT / "ORGANS.md").read_text(encoding="utf-8")
    batch_headings = [
        ln for ln in text.splitlines() if ln.startswith("### ") and "batch" in ln.lower()
    ]
    assert batch_headings == [], f"batch vocabulary leaked into headings: {batch_headings}"
    assert text.count("- **Organ id:** `") == len(_accepted_registry_ids())


def test_display_name_complete_and_collision_free() -> None:
    model = load_model(MICROCOSM_ROOT)
    names: list[str] = []
    missing: list[str] = []
    for fam in model["families"]:
        for card in fam["cards"]:
            name = card.get("display_name")
            if not name:
                missing.append(card["organ_id"])
            else:
                names.append(name)
    assert missing == [], f"organs without display_name: {missing}"
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert dupes == [], f"display_name collisions: {dupes}"


def test_specialty_index_routes_readers_to_a_subset() -> None:
    """Human entry: a 'Find your specialty' index lets a reader pick a discipline
    instead of reading the whole inventory; every organ carries specialty tags."""
    text = (MICROCOSM_ROOT / "ORGANS.md").read_text(encoding="utf-8")
    assert "## Find your specialty" in text
    assert "then open the linked organ cards" in text
    assert (
        "[Agent Route Observability Runtime](#agent-route-observability-runtime)"
        in text
    )
    assert "[Proof Diagnostic Evidence Spine](#proof-diagnostic-evidence-spine)" in text
    model = load_model(MICROCOSM_ROOT)
    empty = [
        card["organ_id"]
        for fam in model["families"]
        for card in fam["cards"]
        if not (isinstance(card.get("specialty"), list) and card.get("specialty"))
    ]
    assert empty == [], f"organs without specialty tags: {empty}"
    assert model["coverage"]["empty_specialty"] == []


def test_wires_to_edges_resolve_to_accepted_organs() -> None:
    """Diagram edges must be data-backed and dangling-free."""
    model = load_model(MICROCOSM_ROOT)
    accepted = _accepted_registry_ids()
    edges = 0
    for fam in model["families"]:
        for card in fam["cards"]:
            for target in card.get("wires_to") or []:
                assert target in accepted, (
                    f"{card['organ_id']} wires to unknown organ {target}"
                )
                edges += 1
    assert edges > 0, "expected at least the formal-math proof-chain edges"
    assert model["coverage"]["unresolved_wires_to"] == []


def test_architecture_md_has_organ_wiring_map_with_balanced_mermaid() -> None:
    text = (MICROCOSM_ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "## Level 3 — organ wiring map" in text
    families = read_json_strict(MICROCOSM_ROOT / "core/organ_families.json")
    fam_count = len(families.get("families", []))
    section = text.split("## Level 3 — organ wiring map", 1)[1].split("## Level 4", 1)[0]
    assert section.count("  subgraph F") == fam_count
    assert "-->" in section, "wiring map should draw explicit organ-to-organ edges"
    # every fenced code block is closed, so GitHub renders the Mermaid
    assert text.count("```") % 2 == 0


def test_agent_task_routes_project_from_specialty_tags() -> None:
    """Agent entry: route by task class instead of reading the full inventory."""
    result = build(MICROCOSM_ROOT, write=False)
    route_model = result["agent_task_routes"]
    assert route_model["schema_version"] == "microcosm_agent_task_routes_v1"
    assert route_model["surface_role"] == "generated_agent_task_route_projection"
    assert route_model["route_count"] == len(route_model["routes"])
    assert route_model["accepted_organ_count"] == len(_accepted_registry_ids())
    assert "core/organ_atlas.json" in route_model["source_refs"]
    assert (
        "atlas/entry_packet.json::concept_mechanism_entry_route"
        in route_model["source_refs"]
    )
    assert (
        "organ-surface-contract::coverage.source_module_file_graph"
        in route_model["source_refs"]
    )
    assert route_model["source_relation_route_count"] == route_model["route_count"]
    assert route_model["organ_glance_ladder"]
    assert route_model["capsule_accounting"]["accepted_organ_count"] == len(
        _accepted_registry_ids()
    )
    glance_organs = {
        row["organ_id"]
        for family in route_model["organ_glance_ladder"]
        for row in family["organs"]
    }
    assert glance_organs == _accepted_registry_ids()
    cold_reader_glance = {
        row["organ_id"]: row
        for family in route_model["organ_glance_ladder"]
        for row in family["organs"]
    }["cold_reader_route_map"]
    assert cold_reader_glance["one_line"]
    assert cold_reader_glance["card"]
    assert cold_reader_glance["authority_ceiling"]
    assert cold_reader_glance["claim_ceiling_restated"] == (
        cold_reader_glance["authority_ceiling"]
    )
    assert cold_reader_glance["authority_boundary"] == (
        cold_reader_glance["authority_ceiling"]
    )
    assert cold_reader_glance["paper_module_ref"].endswith(".md")
    assert cold_reader_glance["capsule_id"].startswith("paper_module.")
    assert cold_reader_glance["card_ref"] == cold_reader_glance["drilldown_target"]
    source_relation_summary = route_model["source_relation_summary"]
    assert source_relation_summary["source"] == (
        "organ-surface-contract::coverage.source_module_file_graph"
    )
    assert source_relation_summary["output_schema"] == (
        "microcosm_organ_relationship_topology_card_v0"
    )
    assert 0 < source_relation_summary["organ_count"] <= (
        route_model["accepted_organ_count"]
    )
    assert "organ-topology remains dynamic edge authority" in (
        source_relation_summary["authority_boundary"]
    )

    model = load_model(MICROCOSM_ROOT)
    expected_task_classes = sorted(
        {
            tag
            for family in model["families"]
            for card in family["cards"]
            for tag in card.get("specialty", [])
        }
    )
    assert [row["task_class"] for row in route_model["routes"]] == (
        expected_task_classes
    )

    routed_organs: set[str] = set()
    for route in route_model["routes"]:
        assert route["task_class"]
        assert route["primary_organ_id"] in _accepted_registry_ids()
        assert route["relevant_organs"]
        assert route["first_command"]
        assert route["allowed_authority"]
        assert route["evidence_ref"].startswith("core/organ_registry.json::")
        assert route["receipt_ref"]
        source_summary = route["source_relation_summary"]
        assert source_summary["source"] == (
            "organ-surface-contract::coverage.source_module_file_graph"
        )
        assert source_summary["output_schema"] == (
            "microcosm_organ_relationship_topology_card_v0"
        )
        assert source_summary["edge_count"] > 0
        assert source_summary["source_ref_count"] > 0
        assert source_summary["source_shard_ref_count"] > 0
        assert source_summary["relation_type_counts"][
            "source_file.copied_to_public_target"
        ] > 0
        assert source_summary["relation_type_counts"][
            "source_shard.retained_as_public_target_shard"
        ] > 0
        assert source_summary["top_source_refs"]
        assert source_summary["top_source_shard_refs"]
        assert source_summary["query_examples"]
        for example in source_summary["query_examples"]:
            tokens = shlex.split(example)
            assert tokens[:2] == ["microcosm", "organ-topology"], example
            if "--relation-type" in tokens:
                assert len(tokens) == 6, (
                    "relation drilldowns must quote dynamic refs as one shell "
                    f"argument: {example}"
                )
                assert tokens[2] == "--relation-type"
                assert tokens[4] in {"--source-ref", "--shard-ref"}
            elif "--validation-ref" in tokens:
                assert len(tokens) == 4, (
                    "validation drilldowns must quote dynamic refs as one shell "
                    f"argument: {example}"
                )
                assert tokens[2] == "--validation-ref"
            else:
                assert tokens[2] == "--organ"
                assert len(tokens) == 4, example
        assert all(
            "--task-class" not in example
            for example in source_summary["query_examples"]
        )
        assert route["stop_condition"]
        assert route["drilldown_target"].startswith("ORGANS.md#")
        for organ in route["relevant_organs"]:
            routed_organs.add(organ["organ_id"])
            assert organ["first_command"]
            assert organ["claim_ceiling"]
            assert organ["standard_ref"].startswith("standards/std_microcosm_")
            assert organ["concept_ref"] == (
                f"organ_doctrine_row:{organ['organ_id']}.concept_binding"
            )
            assert organ["mechanism_ref"] == (
                f"organ_doctrine_row:{organ['organ_id']}.mechanism_binding"
            )
            assert organ["drilldown_target"].startswith("ORGANS.md#")
    assert routed_organs == _accepted_registry_ids()

    agent_entry = {
        row["task_class"]: row for row in route_model["routes"]
    }["agent-entry"]
    assert agent_entry["primary_organ_id"] == "cold_reader_route_map"
    agent_entry_organs = {
        row["organ_id"] for row in agent_entry["relevant_organs"]
    }
    assert {
        "cold_reader_route_map",
        "navigation_hologram_route_plane",
        "standards_meta_diagnostics",
        "voice_to_doctrine_self_improvement_loop",
    }.issubset(agent_entry_organs)
    agent_entry_source_summary = agent_entry["source_relation_summary"]
    assert agent_entry_source_summary["edge_count"] > 0
    assert (
        "microcosm organ-topology --organ cold_reader_route_map"
        in agent_entry_source_summary["query_examples"]
    )
    cold_reader = {
        row["organ_id"]: row for row in agent_entry["relevant_organs"]
    }["cold_reader_route_map"]
    cold_reader_source_handle = cold_reader["source_relation_handle"]
    assert cold_reader_source_handle["source_relation_ref"] == (
        "organ-surface-contract::coverage.source_module_file_graph."
        "edges_by_organ[organ_id=cold_reader_route_map]"
    )
    assert cold_reader_source_handle["edge_count"] > 0
    assert cold_reader_source_handle["source_ref_count"] > 0
    assert cold_reader_source_handle["source_shard_ref_count"] > 0
    assert cold_reader_source_handle["query"] == (
        "microcosm organ-topology --organ cold_reader_route_map"
    )


def test_agent_concurrency_routes_bind_seed_speed_topology_to_work_spine() -> None:
    result = build(MICROCOSM_ROOT, write=False)
    route_by_task = {
        row["task_class"]: row for row in result["agent_task_routes"]["routes"]
    }
    for task_class in ("agent-concurrency", "work-ledger"):
        route = route_by_task[task_class]
        relevant = {row["organ_id"]: row for row in route["relevant_organs"]}
        assert {
            "concurrency_mission_control",
            "mission_transaction_work_spine",
        }.issubset(relevant)

    model = load_model(MICROCOSM_ROOT)
    cards = {
        card["organ_id"]: card
        for family in model["families"]
        for card in family["cards"]
    }
    concurrency = cards["concurrency_mission_control"]
    work_spine = cards["mission_transaction_work_spine"]

    assert "mission_transaction_work_spine" in concurrency["wires_to"]
    assert "Work Ledger seed-speed topology fixture" in concurrency["agent_gloss"]
    assert "source-import anchor enforcement" in concurrency["wiring_note"]
    assert "Work Ledger seed-speed source-import" in work_spine["agent_gloss"]
    assert "session heartbeat" in work_spine["human_gloss"]
    assert "mutation-check" in work_spine["human_gloss"]


def test_agent_routes_md_exposes_task_table_and_deferral_targets() -> None:
    text = (MICROCOSM_ROOT / "AGENT_ROUTES.md").read_text(encoding="utf-8")
    assert "# Microcosm Agent Task Routes" in text
    assert "## Agent Task Route Table" in text
    assert (
        "| `task_class` | Relevant organ(s) | First command | Source relation handles |"
        in text
    )
    assert "Evidence / doctrine / drilldown" in text
    assert "atlas/agent_task_routes.json" in text
    assert "top-level `routes` as an array of rows keyed by `task_class`" in text
    assert "`source_relation_summary`" in text
    assert "`microcosm organ-topology`" in text
    assert "ORGANS.md#find-your-specialty" in text
    assert "`standard_ref`, `paper_module_ref`, `concept_ref`, `mechanism_ref`" in text
    assert "`source_relation_summary` handles" in text
    assert "Stop when the first command or named receipt is visible" in text
    assert "`agent-entry`" in text
    assert "`organ_doctrine_row:cold_reader_route_map.concept_binding`" in text
    for task_class in ("getting-started", "formal-methods", "ai-safety"):
        assert f"`{task_class}`" in text
