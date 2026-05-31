from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
AGENTS = MICROCOSM_ROOT / "AGENTS.md"


def _help_output() -> str:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(MICROCOSM_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "microcosm_core", "--help"],
        cwd=MICROCOSM_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    ).stdout


def test_agent_entry_names_first_screen_cli_registry_before_route_labels() -> None:
    agents = AGENTS.read_text(encoding="utf-8")
    help_output = _help_output()

    assert "## Live CLI Registry Boundary" in agents
    assert (
        "Treat `microcosm --help` as the bounded first-screen "
        "console-command registry."
    ) in agents
    assert "PYTHONPATH=src python3 -m microcosm_core --help" in agents
    assert "It is not the full drilldown inventory." in agents
    assert "drilldown commands remain callable by exact name" in agents
    assert "not guaranteed to appear" in agents
    assert "root help" in agents
    assert "microcosm observe --card <project>" in help_output
    assert "microcosm observe <project>" in help_output
    for drilldown_command in (
        "agent-monitor-redteam-falsification-replay",
        "agent-route-observability-runtime",
        "macro-projection-import-protocol",
    ):
        assert drilldown_command in agents
    assert "microcosm evidence list <project> --limit 25" in agents


def test_agent_entry_does_not_advertise_removed_expanded_loop_commands() -> None:
    agents = AGENTS.read_text(encoding="utf-8")

    for removed in (
        "microcosm init <project>",
        "microcosm index <project>",
        "microcosm architecture <project>",
        "microcosm route <project>",
        "microcosm work run <project>",
    ):
        assert removed not in agents

    help_output = _help_output()
    assert "microcosm route <project>" not in help_output
    assert "    route " in help_output
