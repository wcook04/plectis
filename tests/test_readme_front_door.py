"""Adversarial tests for the README human-front-door binding validator.

A green binding validator is only meaningful if it can detect the regressions
it claims to guard. The positive test proves the real README satisfies the
front-door contract; the negative fixtures each minimally break one promise and
assert the specific blocking code, proving the validator is not decorative.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from microcosm_core.validators.readme_front_door import validate_readme_front_door


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]

# README link destinations that must exist relative to the README directory.
_LINKED_SIBLINGS = (
    "plectis-public-system.pdf",
    "docs/guides/hypothesis-handoffs.md",
    "QUICKSTART.md",
    "ARCHITECTURE.md",
    "docs/papers/README.md",
    "docs/README.md",
    "docs/UNDERSTANDING_PLECTIS.md",
    "docs/maintainers/validation.md",
    "ORGANS.md",
    "AGENTS.md",
    "AGENTS.override.md",
    "RELEASE_REVIEW.md",
    "SOURCE_STATUS.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "LICENSE",
    "NOTICE",
    "PROVENANCE.md",
    "CITATION.cff",
)


def _front_door_tree(tmp_path: Path) -> Path:
    """Build a minimal public root that resolves every front-door binding."""
    root = tmp_path / "microcosm-substrate"
    (root / "atlas").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    shutil.copy2(MICROCOSM_ROOT / "README.md", root / "README.md")
    shutil.copy2(
        MICROCOSM_ROOT / "atlas/entry_packet.json", root / "atlas/entry_packet.json"
    )
    shutil.copy2(
        MICROCOSM_ROOT / "core/organ_registry.json",
        root / "core/organ_registry.json",
    )
    for rel in _LINKED_SIBLINGS:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("placeholder\n", encoding="utf-8")
    return root


def _mutate(root: Path, old: str, new: str) -> None:
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    assert old in text, f"fixture precondition: {old!r} present in README"
    readme.write_text(text.replace(old, new, 1), encoding="utf-8")


def _replace_hero_promise(root: Path, replacement: str) -> None:
    text = (root / "README.md").read_text(encoding="utf-8")
    promise = re.search(r"\*\*(.+?)\*\*", text, re.DOTALL)
    assert promise is not None
    _mutate(root, promise.group(0), replacement)


def _replace_paragraph(root: Path, marker: str, replacement: str) -> None:
    text = (root / "README.md").read_text(encoding="utf-8")
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if marker in p]
    assert len(paragraphs) == 1, f"one paragraph must contain {marker!r}"
    _mutate(root, paragraphs[0], replacement)


def _replace_section(root: Path, heading: str, replacement: str) -> None:
    text = (root / "README.md").read_text(encoding="utf-8")
    section = re.search(rf"(?ms)^## {re.escape(heading)}\n.*?(?=^## |\Z)", text)
    assert section is not None
    _mutate(root, section.group(0), f"## {heading}\n\n{replacement}\n\n")


def test_real_readme_satisfies_front_door_contract() -> None:
    receipt = validate_readme_front_door(MICROCOSM_ROOT)
    assert receipt["status"] == "pass", receipt["blocking_codes"]
    assert receipt["blocking_codes"] == []
    findings = receipt["findings"]
    assert findings["h1"] == "Plectis"
    assert findings["witness_command_bound"] is True
    assert findings["hero_banned_terms"] == []
    assert findings["hero_first_run_block_present"] is True
    assert findings["hero_unisolated_install_present"] is False
    assert findings["registry_component_count"] >= 80
    assert findings["registry_component_count_bound_in_front_door"] is True
    assert findings["front_door_required_context_missing"] == []
    assert findings["front_door_local_only_frames"] == []
    assert findings["front_door_claim_grammar_missing"] == []
    assert findings["front_door_family_ceilings_missing"] == []
    # The primary human witness is the text projection, not raw JSON.
    assert findings["human_text_witness_present"] is True


def test_baseline_tree_passes(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    receipt = validate_readme_front_door(root)
    assert receipt["status"] == "pass", receipt["blocking_codes"]


def test_blocks_stale_witness_command(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    readme = root / "README.md"
    # The witness command appears in more than one fenced block; replace every
    # occurrence so the canonical first command is genuinely absent.
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "plectis tour --card", "plectis frobnicate"
        ),
        encoding="utf-8",
    )
    receipt = validate_readme_front_door(root)
    assert "README_WITNESS_COMMAND_UNBOUND" in receipt["blocking_codes"]


def test_blocks_missing_first_run_command(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    # Break every runnable command in the hero. A first screen that shows no
    # way to run the tool has failed its one job, however much prose it keeps.
    hero, separator, rest = text.partition("\n## ")
    readme.write_text(
        hero.replace("plectis", "frobnicate") + separator + rest, encoding="utf-8"
    )
    receipt = validate_readme_front_door(root)
    assert "README_FIRST_RUN_COMMAND_MISSING" in receipt["blocking_codes"]


def test_blocks_unisolated_hero_install(tmp_path: Path) -> None:
    """Restore the historical defect verbatim and require it to be named.

    Until 2026-08-16 the front door opened on `python3 -m pip install .`,
    which every Homebrew, Debian, and Ubuntu `python3` refuses under PEP 668.
    The previous version of this validator asked for exactly that string, so
    the front door's own guard held the failure in place. This fixture puts it
    back and proves the guard now points the other way.
    """
    root = _front_door_tree(tmp_path)
    readme = root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "PYTHONPATH=src python3 -m plectis tour --format text .",
            "python3 -m pip install .\nplectis tour --format text .",
            1,
        ),
        encoding="utf-8",
    )
    receipt = validate_readme_front_door(root)
    assert "README_HERO_INSTALL_NOT_ISOLATED" in receipt["blocking_codes"]


def test_blocks_promise_that_leads_with_inventory(tmp_path: Path) -> None:
    """Restore the historical opening and require the count-led framing to fail.

    Until 2026-08-16 the promise read "Plectis is a local Python tool and an
    88-component reference corpus for checking claims made about agent-built
    software". Every word of that is true. It also spends the one sentence a
    stranger reliably reads on how much there is, before saying what any of it
    is for, which is the opposite of the order a cold reader needs.
    """
    root = _front_door_tree(tmp_path)
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    promise = re.search(r"\*\*(.+?)\*\*", text, re.DOTALL)
    assert promise is not None
    readme.write_text(
        text.replace(
            promise.group(0),
            "**Plectis is a local Python tool and an 88-component reference "
            "corpus for checking claims made about agent-built software.**",
            1,
        ),
        encoding="utf-8",
    )
    receipt = validate_readme_front_door(root)
    assert "README_HERO_PROMISE_LEADS_WITH_INVENTORY" in receipt["blocking_codes"]


def test_blocks_attribution_above_the_first_command(tmp_path: Path) -> None:
    """Put the provenance paragraph back above the first command.

    This is where it sat until 2026-08-16: between the promise and anything
    runnable, so the second thing a stranger read was who wrote the code rather
    than what it does. The paragraph itself is not the problem and stays on the
    first screen; only its position ahead of the demonstration is blocked.
    """
    root = _front_door_tree(tmp_path)
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    marker = "**How this was built, and why it is built the way it is.**"
    start = text.find(marker)
    assert start >= 0, "fixture needs the provenance paragraph to relocate"
    end = text.find("\n\n", start)
    paragraph = text[start:end]
    moved = text.replace(paragraph + "\n\n", "", 1)
    anchor = "Two commands, no install"
    moved = moved.replace(anchor, paragraph + "\n\n" + anchor, 1)
    readme.write_text(moved, encoding="utf-8")
    receipt = validate_readme_front_door(root)
    assert "README_HERO_ATTRIBUTION_BEFORE_FIRST_RUN" in receipt["blocking_codes"]


def test_blocks_injected_overclaim(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    readme = root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        + "\n\nPlectis is production-ready and authorized for hosted release; "
        "ship it to PyPI.\n",
        encoding="utf-8",
    )
    receipt = validate_readme_front_door(root)
    assert "README_OVERCLAIM" in receipt["blocking_codes"]


def test_blocks_broken_link(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    _mutate(root, "(ARCHITECTURE.md)", "(ARCHITECTURE_GONE.md)")
    receipt = validate_readme_front_door(root)
    assert "README_BROKEN_LINK" in receipt["blocking_codes"]


def test_blocks_former_name_in_hero(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    # inject the compatibility state dir into the hero promise
    _replace_hero_promise(root, "**Plectis includes runnable programs and writes .microcosm/ records.**")
    receipt = validate_readme_front_door(root)
    assert "README_HERO_ONTOLOGY_LEAK" in receipt["blocking_codes"]
    assert "compatibility-state-dir" in receipt["findings"]["hero_banned_terms"]


def test_banner_is_optional_but_gated_when_present(tmp_path: Path) -> None:
    # The real README carries no hero banner (the social card is a GitHub
    # social-preview asset, not first-screen content). A banner that IS added
    # back must still satisfy the alt-text discipline.
    root = _front_door_tree(tmp_path)
    _mutate(
        root,
        "# Plectis",
        '<p align="center"><img src="assets/gone.png" alt="Plectis — atlas"></p>\n\n# Plectis',
    )
    receipt = validate_readme_front_door(root)
    assert "README_BANNER_ALT_EM_DASH" in receipt["blocking_codes"]
    assert "README_BANNER_FILE_UNRESOLVED" in receipt["blocking_codes"]


def test_blocks_json_only_witness(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    readme = root / "README.md"
    # Regress the witness back to JSON-only by removing every text projection.
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "plectis tour --format text", "plectis tour --card"
        ),
        encoding="utf-8",
    )
    receipt = validate_readme_front_door(root)
    assert "README_HUMAN_WITNESS_MISSING" in receipt["blocking_codes"]


def test_blocks_local_record_primary_frame(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    _replace_hero_promise(root, "**Plectis is a local evidence router.** It publishes runnable programs.")
    receipt = validate_readme_front_door(root)
    assert "README_FRONT_DOOR_LOCAL_ONLY_FRAME" in receipt["blocking_codes"]
    assert (
        "local-evidence-router-primary-frame"
        in receipt["findings"]["front_door_local_only_frames"]
    )


def test_blocks_record_layer_before_mechanisms(tmp_path: Path) -> None:
    # The named-sentence patterns only recognise wordings that were once
    # written. This opens with the record layer in wording none of them match:
    # the front door still leads with what Plectis writes rather than what it
    # publishes, which is the property the read order forbids.
    root = _front_door_tree(tmp_path)
    _replace_hero_promise(
        root,
        "**Plectis writes an inspectable record of any project you point it at.**"
        " It also publishes runnable programs.",
    )
    receipt = validate_readme_front_door(root)
    assert "README_FRONT_DOOR_LOCAL_ONLY_FRAME" in receipt["blocking_codes"]
    assert (
        "record-layer-precedes-mechanisms"
        in receipt["findings"]["front_door_local_only_frames"]
    )


def test_opening_can_call_components_programs(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    _replace_hero_promise(
        root,
        "**Plectis provides programs for comparing forecasts and trying Lean proofs.** "
        "Their output includes an inspectable record.",
    )
    receipt = validate_readme_front_door(root)
    assert receipt["status"] == "pass", receipt["blocking_codes"]


@pytest.mark.parametrize(
    "anchor",
    [
        "entry--reveal",
        "architecture--navigation",
        "formal-math--proof",
        "agent-reliability--safety-replays",
        "research--science-replays",
        "import-projection--drift",
        "work-landing--continuity",
    ],
)
def test_requires_a_link_to_each_family(tmp_path: Path, anchor: str) -> None:
    root = _front_door_tree(tmp_path)
    readme = root / "README.md"
    # Keep all prose and an existing destination. Only access to the selected
    # family is removed, even if its name appears throughout the README.
    text = readme.read_text(encoding="utf-8")
    assert f"ORGANS.md#{anchor}" in text
    readme.write_text(text.replace(f"ORGANS.md#{anchor}", "ORGANS.md"), encoding="utf-8")
    receipt = validate_readme_front_door(root)
    assert anchor in receipt["findings"]["front_door_family_routes_missing"]


def test_blocks_missing_component_inspection_guidance(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    _replace_section(root, "How it works", "Run the tour first, then browse the examples.")
    receipt = validate_readme_front_door(root)
    assert "README_FRONT_DOOR_CLAIM_GRAMMAR_MISSING" in receipt["blocking_codes"]
    assert (
        "component-inspection-guidance"
        in receipt["findings"]["front_door_claim_grammar_missing"]
    )


def test_reading_journey_allows_different_order_and_concrete_verbs(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    _replace_section(
        root,
        "How it works",
        "Start with an example's expected output and its test. Open the input data\n"
        "and the function that produces the output, then compare what you observe.",
    )
    receipt = validate_readme_front_door(root)
    assert receipt["status"] == "pass", receipt["blocking_codes"]


def test_inspection_guidance_requires_a_way_to_evaluate_the_result(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    _replace_section(
        root,
        "How it works",
        "Open the component input and source code. Trust the result it produces.",
    )
    receipt = validate_readme_front_door(root)
    assert "component-inspection-guidance" in receipt["findings"][
        "front_door_claim_grammar_missing"
    ]


def test_scattered_nouns_do_not_replace_component_instructions(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    _replace_section(
        root,
        "How it works",
        "Choose a component.\n\nInput data is included.\n\nThe source is readable.\n\n"
        "There is output.\n\nTests are included.",
    )
    receipt = validate_readme_front_door(root)
    assert "component-inspection-guidance" in receipt["findings"]["front_door_claim_grammar_missing"]


def test_reversed_service_and_affiliation_claims_do_not_satisfy_limits(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    _replace_paragraph(
        root,
        "not a hosted service",
        "Plectis is a hosted service and a production security product. It has\n"
        "model-provider affiliation and endorsement.",
    )
    receipt = validate_readme_front_door(root)
    missing = receipt["findings"]["front_door_claim_grammar_missing"]
    assert "hosted-service-ceiling" in missing
    assert "production-security-ceiling" in missing
    assert "provider-affiliation-ceiling" in missing


def test_reversed_reader_permission_does_not_satisfy_limits(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    assert text.count("do not gain permission") == 2
    readme.write_text(text.replace("do not gain permission", "gain permission"), encoding="utf-8")
    receipt = validate_readme_front_door(root)
    assert "release-authority-ceiling" in receipt["findings"]["front_door_claim_grammar_missing"]
    assert "projection-drift-family-ceiling" in receipt["findings"]["front_door_family_ceilings_missing"]
    assert "work-continuity-family-ceiling" in receipt["findings"]["front_door_family_ceilings_missing"]


@pytest.mark.parametrize(
    ("marker", "missing"),
    [
        ("**Formal proof:**", "formal-proof-family-ceiling"),
        ("**Agent safety:**", "agent-safety-family-ceiling"),
        ("**Research and forecasting:**", "research-family-ceiling"),
        ("**Generated files:**", "projection-drift-family-ceiling"),
        ("**Recording and resuming work:**", "work-continuity-family-ceiling"),
    ],
)
def test_blocks_missing_family_specific_limit(tmp_path: Path, marker: str, missing: str) -> None:
    root = _front_door_tree(tmp_path)
    text = (root / "README.md").read_text(encoding="utf-8")
    item = re.search(rf"(?m)^- {re.escape(marker)}.*(?:\n  .*|\n[^\n-].*)*", text)
    assert item is not None
    _mutate(root, item.group(0), f"- {marker} See the component list for examples.")
    receipt = validate_readme_front_door(root)
    assert "README_FRONT_DOOR_FAMILY_CEILING_MISSING" in receipt["blocking_codes"]
    assert missing in receipt["findings"]["front_door_family_ceilings_missing"]


def test_blocks_stale_front_door_component_count(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    _mutate(root, "88 components", "87 components")
    receipt = validate_readme_front_door(root)
    assert "README_FRONT_DOOR_COMPONENT_COUNT_UNBOUND" in receipt["blocking_codes"]
