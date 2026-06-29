"""Adversarial tests for the README human-front-door binding validator.

A green binding validator is only meaningful if it can detect the regressions
it claims to guard. The positive test proves the real README satisfies the
front-door contract; the negative fixtures each minimally break one promise and
assert the specific blocking code, proving the validator is not decorative.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from microcosm_core.validators.readme_front_door import validate_readme_front_door


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]

# README link destinations that must exist relative to the README directory.
_LINKED_SIBLINGS = (
    "QUICKSTART.md",
    "ARCHITECTURE.md",
    "ORGANS.md",
    "AGENTS.md",
    "RELEASE_REVIEW.md",
    "SOURCE_STATUS.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "LICENSE",
    "NOTICE",
    "PROVENANCE.md",
)


def _front_door_tree(tmp_path: Path) -> Path:
    """Build a minimal public root that resolves every front-door binding."""
    root = tmp_path / "microcosm-substrate"
    (root / "atlas").mkdir(parents=True)
    (root / "assets").mkdir(parents=True)
    (root / "core").mkdir(parents=True)
    shutil.copy2(MICROCOSM_ROOT / "README.md", root / "README.md")
    shutil.copy2(
        MICROCOSM_ROOT / "atlas/entry_packet.json", root / "atlas/entry_packet.json"
    )
    shutil.copy2(
        MICROCOSM_ROOT / "core/organ_registry.json",
        root / "core/organ_registry.json",
    )
    shutil.copy2(
        MICROCOSM_ROOT / "assets/plectis-social-card.png",
        root / "assets/plectis-social-card.png",
    )
    for rel in _LINKED_SIBLINGS:
        (root / rel).write_text("placeholder\n", encoding="utf-8")
    return root


def _mutate(root: Path, old: str, new: str) -> None:
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    assert old in text, f"fixture precondition: {old!r} present in README"
    readme.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_real_readme_satisfies_front_door_contract() -> None:
    receipt = validate_readme_front_door(MICROCOSM_ROOT)
    assert receipt["status"] == "pass", receipt["blocking_codes"]
    assert receipt["blocking_codes"] == []
    findings = receipt["findings"]
    assert findings["h1"] == "Plectis"
    assert findings["witness_command_bound"] is True
    assert findings["hero_banned_terms"] == []
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
    _mutate(
        root,
        "public, executable cross-section",
        "public, executable .microcosm/ cross-section",
    )
    receipt = validate_readme_front_door(root)
    assert "README_HERO_ONTOLOGY_LEAK" in receipt["blocking_codes"]
    assert "compatibility-state-dir" in receipt["findings"]["hero_banned_terms"]


def test_blocks_missing_banner(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    # drop the <p align=center>...<img...></p> banner block
    head, _, rest = text.partition("# Plectis")
    readme.write_text("# Plectis" + rest, encoding="utf-8")
    receipt = validate_readme_front_door(root)
    assert "README_BANNER_MISSING" in receipt["blocking_codes"]


def test_blocks_em_dash_in_banner_alt(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    _mutate(
        root,
        "a public executable atlas",
        "a public executable atlas —",
    )
    receipt = validate_readme_front_door(root)
    assert "README_BANNER_ALT_EM_DASH" in receipt["blocking_codes"]


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
    _mutate(
        root,
        "Plectis is a public, executable cross-section of an AI-native workflow and\nresearch runtime",
        "Run one command inside a code repository and get a local record",
    )
    receipt = validate_readme_front_door(root)
    assert "README_FRONT_DOOR_LOCAL_ONLY_FRAME" in receipt["blocking_codes"]
    assert (
        "run-one-command-local-record-primary-frame"
        in receipt["findings"]["front_door_local_only_frames"]
    )


def test_blocks_missing_claim_grammar_read_order(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    _mutate(
        root,
        "Read Plectis in this order: **mechanisms -> evidence discipline -> local\nruntime**.",
        "Read Plectis by running the tour first.",
    )
    receipt = validate_readme_front_door(root)
    assert "README_FRONT_DOOR_CLAIM_GRAMMAR_MISSING" in receipt["blocking_codes"]
    assert (
        "mechanism-evidence-runtime-read-order"
        in receipt["findings"]["front_door_claim_grammar_missing"]
    )


def test_blocks_missing_family_specific_claim_ceiling(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    _mutate(root, "not theorem-proof authority", "not vague authority")
    receipt = validate_readme_front_door(root)
    assert "README_FRONT_DOOR_FAMILY_CEILING_MISSING" in receipt["blocking_codes"]
    assert (
        "formal-proof-family-ceiling"
        in receipt["findings"]["front_door_family_ceilings_missing"]
    )


def test_blocks_stale_front_door_component_count(tmp_path: Path) -> None:
    root = _front_door_tree(tmp_path)
    _mutate(root, "88 bounded components", "87 bounded components")
    receipt = validate_readme_front_door(root)
    assert "README_FRONT_DOOR_COMPONENT_COUNT_UNBOUND" in receipt["blocking_codes"]
