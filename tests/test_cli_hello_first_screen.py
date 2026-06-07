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
    assert "Pre-install probe: ./bootstrap.sh -> .microcosm/cold_clone_probe.json" in output
    assert (
        "Source-only card: PYTHONPATH=src python3 -m microcosm_core hello ."
        in output
    )
    assert "Open card: microcosm hello ." in output
    assert "First run: microcosm tour --card ." in output
    assert (
        "Source-only first run: "
        "PYTHONPATH=src python3 -m microcosm_core tour --card ."
        in output
    )
    assert (
        "Source-only agent entry: "
        "PYTHONPATH=src python3 -m microcosm_core agent-entry-composition "
        "--root . --task agent-entry --viewer {type_a_agent|human} --card --check"
        in output
    )
    assert (
        "Source-only status: "
        "PYTHONPATH=src python3 -m microcosm_core status --card ."
        in output
    )
    assert (
        "microcosm serve . --host 127.0.0.1 --port 8765 --max-requests 7"
        in output
    )
    assert "-> /project/first-screen -> /project/observatory-card" in output
    assert "Counts are receipt-backed handles" in output
    assert (
        "reader aliases: cold-cloner, interesting_parts/interesting-parts, skeptical-reviewer, "
        "reviewer, type-a-agent, domain-specialist"
    ) in output
    assert "No release, hosted publication, provider-call" in output
    assert "reader_routes" not in output
    assert '\"body\":' not in output
    assert "/Users/" not in output
    assert "src/ai_workflow" not in output


def test_cli_hello_and_first_screen_do_not_create_project_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text(
        "# Demo\n\nMicrocosm no-write probe.\n",
        encoding="utf-8",
    )
    (project / "app.py").write_text("print('hello')\n", encoding="utf-8")
    state_dir = project / ".microcosm"

    assert not state_dir.exists()

    assert cli.main(["hello", str(project)]) == 0
    hello_output = capsys.readouterr().out
    assert "Behavior proof after tour --card: front_door_status=pass" in hello_output
    assert "Behavior proof: front_door_status=pass" not in hello_output
    assert not state_dir.exists()

    assert cli.main(["first-screen", str(project)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["state_write_boundary"]["this_card_writes_microcosm_state"] is False
    assert not state_dir.exists()


def test_cli_hello_can_focus_reader_branch(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["hello", "--reader", "peer_developer", "."]) == 0

    output = capsys.readouterr().out

    assert "Reader branch: Peer developer" in output
    assert "First action: Run `microcosm tour --card .`." in output
    assert "Proof: `microcosm observe --card .`" in output
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
    assert "First action: Run `microcosm tour --card .` after this card." in output
    assert "from the repo root" not in output
    assert "Proof: `microcosm tour --card .`" in output
    assert "release, hosting, and private-data claims this repo refuses" in output
    assert "Reader branch: Safety/evals" not in output
    assert "Reader branch: Hiring" not in output
    assert "Reader branch: Peer developer" not in output


def test_cli_hello_can_focus_type_a_agent_branch(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["hello", "--reader", "type_a_agent", "."]) == 0

    output = capsys.readouterr().out

    assert "Reader branch: Type A agent" in output
    assert "Command: microcosm hello --reader type_a_agent ." in output
    assert (
        "First action: Run `microcosm first-screen --card .`. "
        "If you need `doctrine_effect_frame`, run "
        "`microcosm first-screen --full .` before reading it; then run "
        "`microcosm organ-surface-contract --card --root .`."
    ) in output
    assert "Proof: `microcosm organ-surface-contract --card --root .`" in output
    assert (
        "Source-only first action: Run `PYTHONPATH=src python3 -m "
        "microcosm_core first-screen --card .`."
    ) in output
    assert (
        "Source-only proof: `PYTHONPATH=src python3 -m microcosm_core "
        "organ-surface-contract --card --root .`"
    ) in output
    assert "mechanisms from validators/projections" in output
    assert "Reader branch: GitHub visitor" not in output
    assert "Reader branch: Safety/evals" not in output
    assert "Reader branch: Hiring" not in output
    assert "Reader branch: Peer developer" not in output


@pytest.mark.parametrize(
    ("alias", "branch_label", "canonical_reader"),
    [
        ("cold_cloner", "GitHub visitor", "public_github_visitor"),
        ("cold-cloner", "GitHub visitor", "public_github_visitor"),
        ("interesting_parts", "GitHub visitor", "public_github_visitor"),
        ("interesting-parts", "GitHub visitor", "public_github_visitor"),
        ("skeptical_reviewer", "Safety/evals", "safety_evals_engineer"),
        ("skeptical-reviewer", "Safety/evals", "safety_evals_engineer"),
        ("reviewer", "Safety/evals", "safety_evals_engineer"),
        ("agent", "Type A agent", "type_a_agent"),
        ("type-a-agent", "Type A agent", "type_a_agent"),
        ("domain-specialist", "Domain specialist", "domain_specialist"),
    ],
)
def test_cli_hello_accepts_public_reader_aliases_without_new_routes(
    alias: str,
    branch_label: str,
    canonical_reader: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["hello", "--reader", alias, "."]) == 0

    output = capsys.readouterr().out

    assert f"Reader branch: {branch_label}" in output
    assert f"Command: microcosm hello --reader {alias} ." in output
    if alias != canonical_reader:
        assert f"Command: microcosm hello --reader {canonical_reader} ." not in output
    assert output.count("Reader branch:") == 1


def test_cli_first_screen_text_accepts_public_reader_hyphen_alias(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        cli.main(
            ["first-screen", "--format", "text", "--reader", "domain-specialist", "."]
        )
        == 0
    )

    output = capsys.readouterr().out

    assert "Reader branch: Domain specialist" in output
    assert "Command: microcosm hello --reader domain-specialist ." in output
    assert "microcosm hello --reader domain_specialist ." not in output
    assert output.count("Reader branch:") == 1


def test_cli_hello_accepts_text_format_alias(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["hello", "--format", "text", "."]) == 0

    output = capsys.readouterr().out

    assert output.startswith("Microcosm first screen\n")
    assert "Open card: microcosm hello ." in output


def test_cli_hello_accepts_card_alias(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["hello", "--card", "."]) == 0

    output = capsys.readouterr().out

    assert output.startswith("Microcosm first screen\n")
    assert "Open card: microcosm hello ." in output
    assert "First run: microcosm tour --card ." in output


def test_cli_hello_help_documents_card_alias(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["hello", "--help"])

    output = capsys.readouterr().out

    assert excinfo.value.code == 0
    assert "--card" in output
    assert "accepted for first-screen parity" in output
    assert "hello always emits" in output


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
        "microcosm first-screen --card ."
    )
    assert payload["reader_route_menu"]["source_checkout_commands"]["behavior_proof"] == (
        "PYTHONPATH=src python3 -m microcosm_core tour --card ."
    )
    assert payload["reader_route_menu"]["source_checkout_commands"][
        "first_screen_full"
    ] == "PYTHONPATH=src python3 -m microcosm_core first-screen --full ."
    assert payload["reader_route_menu"]["source_checkout_commands"][
        "organ_surface_contract"
    ] == (
        "PYTHONPATH=src python3 -m microcosm_core "
        "organ-surface-contract --card --root ."
    )
    assert payload["reader_route_menu"]["source_checkout_commands"][
        "agent_entry_selector"
    ] == (
        "PYTHONPATH=src python3 -m microcosm_core "
        "agent-entry-composition --root . --task agent-entry "
        "--viewer {type_a_agent|human} --card --check"
    )
    first_run_steps = {
        row["step_id"]: row
        for row in payload["first_run_ladder"]["steps"]
    }
    assert first_run_steps["map"]["source_checkout_command"] == (
        "PYTHONPATH=src python3 -m microcosm_core hello ."
    )
    assert first_run_steps["behavior_proof"]["source_checkout_command"] == (
        "PYTHONPATH=src python3 -m microcosm_core tour --card ."
    )
    assert first_run_steps["status_confirmation"]["source_checkout_command"] == (
        "PYTHONPATH=src python3 -m microcosm_core status --card ."
    )
    assert payload["reader_route_menu"]["default_json_command"] == (
        "microcosm first-screen ."
    )
    route_by_id = {
        route["reader_route_id"]: route
        for route in payload["reader_route_menu"]["routes"]
    }
    assert route_by_id["public_github_visitor"]["first_action"] == (
        "Run `microcosm tour --card .` after this card."
    )
    assert route_by_id["safety_evals_engineer"]["first_action"] == (
        "Run `microcosm tour --card .` first, then `microcosm status --card .`."
    )
    assert route_by_id["hiring_reviewer"]["first_action"] == (
        "Run `microcosm legibility-scorecard`, then `microcosm tour --card .`."
    )
    assert route_by_id["hiring_reviewer"]["proof_surface"] == (
        "`microcosm legibility-scorecard` plus `microcosm tour --card .`"
    )
    assert route_by_id["domain_specialist"]["first_action"] == (
        "Open `ORGANS.md#find-your-specialty`, then run "
        "`microcosm tour --card .`."
    )
    assert route_by_id["domain_specialist"]["proof_surface"] == (
        "`ORGANS.md#find-your-specialty` plus `microcosm tour --card .`"
    )
    assert route_by_id["type_a_agent"]["first_action"] == (
        "Run `microcosm first-screen --card .`. "
        "If you need `doctrine_effect_frame`, run "
        "`microcosm first-screen --full .` before reading it; then run "
        "`microcosm organ-surface-contract --card --root .`."
    )
    assert route_by_id["type_a_agent"]["proof_surface"] == (
        "`microcosm organ-surface-contract --card --root .`"
    )
    assert route_by_id["type_a_agent"]["source_checkout_proof_surface"] == (
        "`PYTHONPATH=src python3 -m microcosm_core "
        "organ-surface-contract --card --root .`"
    )
    assert "video_storyboard_packet" not in payload
    assert payload["state_write_boundary"]["this_card_writes_microcosm_state"] is False


def test_cli_first_screen_accepts_card_alias(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["first-screen", "--card", "."]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema_version"] == "microcosm_first_screen_compact_card_v1"
    assert payload["output_policy"]["full_contract_command"] == (
        "microcosm first-screen --full ."
    )
    assert payload["output_policy"]["full_contract_preserved"] is True
    assert payload["state_write_boundary"]["this_card_writes_microcosm_state"] is False
    assert payload["pre_install_probe"]["command"] == "./bootstrap.sh"
    assert payload["pre_install_probe"]["runs_before_install"] is True
    assert (
        payload["first_run_ladder"]["pre_install_probe"]
        == payload["pre_install_probe"]
    )


def test_cli_first_screen_card_alias_preserves_text_format(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["first-screen", "--card", "--format", "text", "."]) == 0
    output = capsys.readouterr().out

    assert output.startswith("Microcosm first screen\n")
    assert "Open card: microcosm hello ." in output
    assert "microcosm_first_screen_compact_card_v1" not in output


def test_cli_first_screen_full_flag_preserves_full_contract(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["first-screen", "--full", "."]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema_version"] == "microcosm_first_screen_composition_card_v1"
    assert "video_storyboard_packet" in payload
    assert payload["reader_route_menu"]["machine_card_command"] == (
        "microcosm first-screen --card ."
    )
    assert payload["reader_route_menu"]["default_json_command"] == (
        "microcosm first-screen ."
    )


def test_cli_first_screen_card_alias_preserves_full_contract(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["first-screen", "--card", "--full", "."]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema_version"] == "microcosm_first_screen_composition_card_v1"
    assert "video_storyboard_packet" in payload
    assert payload["reader_route_menu"]["machine_card_command"] == (
        "microcosm first-screen --card ."
    )
    assert payload["reader_route_menu"]["default_json_command"] == (
        "microcosm first-screen ."
    )


def test_cli_first_screen_help_documents_card_alias(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["first-screen", "--help"])

    output = capsys.readouterr().out

    assert excinfo.value.code == 0
    assert "--card" in output
    assert "compact JSON card alias" in output


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
    assert (
        "microcosm hello --reader "
        "{cold_cloner|interesting_parts|skeptical_reviewer|reviewer|agent|domain_specialist} "
        "<project> branch by reader"
    ) in output
    assert (
        "reader aliases: cold-cloner, interesting_parts/interesting-parts, skeptical-reviewer, "
        "reviewer, type-a-agent, domain-specialist"
    ) in output
