from __future__ import annotations

from pathlib import Path

from microcosm_core import release_export


ROOT = Path(__file__).resolve().parents[1]
COMPACT_ENTRY = ROOT / "AGENTS.override.md"


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
    for rel in ("CLAUDE.md", "CODEX.md", "CURSOR.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "AGENTS.override.md" in text
        assert "First read `AGENTS.md` only after" in text


def test_compact_entry_ships_in_packages_and_standalone_exports() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert '"AGENTS.override.md"' in pyproject
    assert "include AGENTS.override.md" in manifest
    assert "AGENTS.override.md" in release_export.DEFAULT_INCLUDE_REFS
    assert "AGENTS.override.md" in release_export.STANDALONE_REQUIRED_PUBLIC_REFS
