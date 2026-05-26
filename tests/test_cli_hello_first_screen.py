from __future__ import annotations

import pytest

from microcosm_core import cli


def test_cli_hello_prints_shared_first_screen_card(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["hello", "."]) == 0

    output = capsys.readouterr().out

    output.encode("ascii")
    assert output.startswith("Microcosm first screen\n")
    assert "First run: microcosm tour --card ." in output
    assert (
        "browser landing: / -> /project/first-screen -> /project/observatory-card"
        in output
    )
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
    assert "Next: microcosm tour --card . -> microcosm observe ." in output
    assert "Reader branch: Safety/evals" not in output
    assert "Reader branch: Hiring" not in output


def test_cli_help_names_hello_as_first_screen_route(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])

    output = capsys.readouterr().out

    assert excinfo.value.code == 0
    assert "microcosm hello <project>" in output
    assert "print the cold-entry one-screen card" in output
