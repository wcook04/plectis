from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from microcosm_core import cli


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_cli_hello_prints_shared_first_screen_card(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["hello", "."]) == 0

    output = capsys.readouterr().out

    output.encode("ascii")
    assert output.startswith("Microcosm first screen\n")
    assert "Open card: microcosm hello ." in output
    assert "First run: microcosm tour --card ." in output
    assert (
        "microcosm serve . --host 127.0.0.1 --port 8765 --max-requests 6"
        in output
    )
    assert "-> /project/first-screen -> /project/observatory-card" in output
    assert "Counts are receipt-backed handles" in output
    assert "No release, hosted publication, provider-call" in output
    assert "reader_routes" not in output
    assert '\"body\":' not in output
    assert "/Users/" not in output
    assert "src/ai_workflow" not in output


def test_cli_hello_can_focus_reader_branch(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["hello", "--reader", "peer_developer", "."]) == 0

    output = capsys.readouterr().out

    assert "Reader branch: Peer developer" in output
    assert "First action: Run `microcosm tour --card .`." in output
    assert "Proof: `microcosm observe .`" in output
    assert "Reader branch: GitHub visitor" not in output
    assert "Reader branch: Safety/evals" not in output
    assert "Reader branch: Hiring" not in output


def test_cli_hello_can_focus_public_github_visitor_branch(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["hello", "--reader", "public_github_visitor", "."]) == 0

    output = capsys.readouterr().out

    assert "Reader branch: GitHub visitor" in output
    assert "Command: microcosm hello --reader public_github_visitor ." in output
    assert "First action: Run `microcosm hello .` from the repo root." in output
    assert "Proof: `microcosm tour --card .`" in output
    assert "release, hosting, and private-data claims this repo refuses" in output
    assert "Reader branch: Safety/evals" not in output
    assert "Reader branch: Hiring" not in output
    assert "Reader branch: Peer developer" not in output


def test_cli_first_screen_json_is_compact_by_default(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["first-screen", "."]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema_version"] == "microcosm_first_screen_compact_card_v1"
    assert len(json.dumps(payload, sort_keys=True)) < 16000
    assert payload["output_policy"]["full_contract_command"] == (
        "microcosm first-screen --full ."
    )
    assert payload["output_policy"]["full_contract_preserved"] is True
    assert payload["reader_route_menu"]["machine_card_command"] == (
        "microcosm first-screen ."
    )
    assert "video_storyboard_packet" not in payload
    assert payload["state_write_boundary"]["this_card_writes_microcosm_state"] is False


def test_cli_first_screen_full_flag_preserves_full_contract(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["first-screen", "--full", "."]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema_version"] == "microcosm_first_screen_composition_card_v1"
    assert "video_storyboard_packet" in payload
    assert payload["reader_route_menu"]["machine_card_command"] == (
        "microcosm first-screen ."
    )


def test_cli_first_screen_fast_path_avoids_runtime_shell_import() -> None:
    script = """
import json
import sys
from microcosm_core import cli
hello_rc = cli.main(["hello", "."])
first_screen_rc = cli.main(["first-screen", "."])
payload = {
    "hello_rc": hello_rc,
    "first_screen_rc": first_screen_rc,
    "runtime_shell_imported": "microcosm_core.runtime_shell" in sys.modules,
    "organ_import_count": sum(
        1 for name in sys.modules if name.startswith("microcosm_core.organs")
    ),
}
print("FAST_IMPORT_STATUS=" + json.dumps(payload, sort_keys=True))
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(MICROCOSM_ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=MICROCOSM_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    marker = "FAST_IMPORT_STATUS="
    status_line = next(
        line for line in result.stdout.splitlines() if line.startswith(marker)
    )
    payload = json.loads(status_line.removeprefix(marker))

    assert payload == {
        "first_screen_rc": 0,
        "hello_rc": 0,
        "organ_import_count": 0,
        "runtime_shell_imported": False,
    }


def test_cli_help_names_hello_as_first_screen_route(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])

    output = capsys.readouterr().out

    assert excinfo.value.code == 0
    assert "microcosm hello <project>" in output
    assert "print the cold-entry one-screen card" in output
