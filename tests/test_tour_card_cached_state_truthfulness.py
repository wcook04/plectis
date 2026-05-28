from __future__ import annotations

from pathlib import Path

from microcosm_core.runtime_shell import RuntimeShell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "scratch_project"
    (project / "src/scratch_app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text(
        "# Scratch Project\n\nLocal proof project.\n",
        encoding="utf-8",
    )
    (project / "pyproject.toml").write_text(
        "[project]\nname = \"scratch-project\"\nversion = \"0.1.0\"\n",
        encoding="utf-8",
    )
    (project / "src/scratch_app/__init__.py").write_text(
        "VALUE = 1\n",
        encoding="utf-8",
    )
    (project / "tests/test_smoke.py").write_text(
        "from scratch_app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    return project


def test_tour_card_distinguishes_cached_read_from_write_contract(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    shell = RuntimeShell(MICROCOSM_ROOT)

    first = shell.tour_card(project)
    second = shell.tour_card(project)

    first_write = first["state_write_result"]
    second_write = second["state_write_result"]

    assert first_write["current_invocation_wrote_microcosm_state"] is True
    assert first_write["cached_state_reused"] is False
    assert second_write["writes_microcosm_state"] is False
    assert second_write["writes_microcosm_state_semantics"] == (
        "current_invocation_only"
    )
    assert second_write["current_invocation_wrote_microcosm_state"] is False
    assert second_write["cached_state_reused"] is True
    assert second_write["command_writes_microcosm_state_when_needed"] is True
    assert "current-invocation only" in second_write["reader_action"]
