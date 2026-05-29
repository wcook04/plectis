"""Contract for the generated organ atlas (ORGANS.md + ARCHITECTURE.md).

This is the drift gate that replaces the old hand-maintained 47-id wall in
README/AGENTS. The canonical per-organ inventory is now generated from
substrate; this test proves it stays complete, in sync, and non-overclaiming.
"""

from __future__ import annotations

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


def test_generated_files_are_in_sync_with_substrate() -> None:
    """ORGANS.md and ARCHITECTURE.md must match `--write` output exactly."""
    result = build(MICROCOSM_ROOT, write=False)
    assert result["status"] == "pass", result["blocking_reasons"]
    assert result["drift"] == [], (
        "ORGANS.md/ARCHITECTURE.md drifted from substrate; run "
        "`PYTHONPATH=src python3 scripts/build_organ_atlas.py --write`"
    )
    assert (MICROCOSM_ROOT / "ORGANS.md").is_file()
    assert (MICROCOSM_ROOT / "ARCHITECTURE.md").is_file()


def test_every_organ_and_a_first_command_appears_in_organs_md() -> None:
    text = (MICROCOSM_ROOT / "ORGANS.md").read_text(encoding="utf-8")
    for organ_id in _accepted_registry_ids():
        assert f"`{organ_id}`" in text, f"{organ_id} missing from ORGANS.md"
    # cards expose runnable commands and claim ceilings, not just names
    assert text.count("**First command:**") == len(_accepted_registry_ids())
    assert text.count("**Does not authorize:**") == len(_accepted_registry_ids())


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
    assert "core/organ_evidence_classes.json" in text
    assert "core/organ_registry.json" in text
    assert "[ORGANS.md](ORGANS.md)" in text
    # kernel primitives are projected from the kernel, not hand-listed
    kernel = read_json_strict(MICROCOSM_ROOT / "core/architecture_kernel.json")
    for prim in kernel.get("primitives", []):
        assert str(prim.get("public_name")) in text
    # every family is linked from the architecture map
    families = read_json_strict(MICROCOSM_ROOT / "core/organ_families.json")
    for fam in families.get("families", []):
        assert str(fam.get("label")) in text
