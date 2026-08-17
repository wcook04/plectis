from __future__ import annotations

from pathlib import Path

from microcosm_core import release_export


ROOT = Path(__file__).resolve().parents[1]
COMPACT_ENTRY = ROOT / "AGENTS.override.md"

# Every provider entry file a coding agent may auto-load. Copilot loads
# `.github/copilot-instructions.md` AND the agent files (`AGENTS.md`,
# `CLAUDE.md`, `GEMINI.md`) with no documented precedence between them, so an
# adapter that restated a rule could contradict its siblings inside one
# session. The convergence contract is therefore: every adapter names
# `AGENTS.override.md` as the compact owner, routes deep reads through
# `AGENTS.md`, and adds no authority of its own.
PROVIDER_ADAPTERS = (
    "CLAUDE.md",
    "CODEX.md",
    "CURSOR.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
)

# Byte ceiling per adapter. Tighter than the 4_096-byte boot-sector ceiling in
# `test_agent_entry_bootloader_budget.py` on purpose: these files exist to name
# one owner and one first command, so growth means an adapter started carrying
# rules that belong in `AGENTS.override.md`.
ADAPTER_BYTE_CEILING = 1_200


def test_compact_agent_entry_is_bounded_and_machine_first() -> None:
    text = COMPACT_ENTRY.read_text(encoding="utf-8")

    assert len(text.encode("utf-8")) < 8_000
    for required in (
        '--first-action "<your goal>" --format text',
        "agent-entry-composition",
        "--viewer type_a_agent --card",
        "comprehend --self-model",
        "comprehend --slice mechanism",
        "comprehend --slice papers",
        "docs/papers/README.md",
        "docs/papers/corpus.json",
        "plectis-lean-erdos249-257",
        "python3 scripts/query_corpus.py --ask",
        "Do not absorb the full file",
    ):
        assert required in text


def test_provider_adapters_converge_on_compact_entry() -> None:
    for rel in PROVIDER_ADAPTERS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "AGENTS.override.md" in text, rel
        assert "First read `AGENTS.md` only after" in text, rel


def test_provider_adapters_stay_under_their_byte_ceiling() -> None:
    oversized = {
        rel: size
        for rel in PROVIDER_ADAPTERS
        if (size := len((ROOT / rel).read_bytes())) > ADAPTER_BYTE_CEILING
    }
    assert oversized == {}, (
        f"provider adapters exceeded {ADAPTER_BYTE_CEILING} bytes: {oversized}. "
        "An adapter names the compact owner and the first command; rules belong "
        "in AGENTS.override.md, where they cannot contradict a sibling adapter "
        "loaded in the same session."
    )


def test_compact_entry_ships_in_packages_and_standalone_exports() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert '"AGENTS.override.md"' in pyproject
    assert "include AGENTS.override.md" in manifest
    assert "AGENTS.override.md" in release_export.DEFAULT_INCLUDE_REFS
    assert "AGENTS.override.md" in release_export.STANDALONE_REQUIRED_PUBLIC_REFS

    # A provider adapter that never ships is an entry surface only the dev tree
    # has: the installed share tree and the standalone export must carry it too.
    for rel in PROVIDER_ADAPTERS:
        assert f'"{rel}"' in pyproject, rel
        assert f"include {rel}" in manifest, rel
        assert rel in release_export.STANDALONE_REQUIRED_PUBLIC_REFS, rel
