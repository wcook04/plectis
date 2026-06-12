from __future__ import annotations

import json

import pytest

from microcosm_core import cli


def test_first_screen_cli_defaults_to_compact_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["first-screen", "."]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema_version"] == "microcosm_first_screen_compact_card_v1"
    assert len(json.dumps(payload, sort_keys=True)) < 16000
    assert payload["output_policy"]["full_contract_command"] == (
        "microcosm first-screen --full ."
    )
    assert payload["output_policy"]["compact_card_command"] == (
        "microcosm first-screen --card ."
    )
    assert payload["output_policy"]["default_json_command"] == (
        "microcosm first-screen ."
    )
    assert payload["reader_route_menu"]["machine_card_command"] == (
        "microcosm first-screen --card ."
    )
    assert payload["reader_route_menu"]["default_json_command"] == (
        "microcosm first-screen ."
    )
    assert "video_storyboard_packet" not in payload


def test_first_screen_cli_enforces_stdout_budget_for_long_project_labels(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A cold external reader passes the absolute artifact path as the project
    # label; the label is interpolated into every command string, so an
    # unenforced budget inflates the same card past its own declaration.
    long_label = "/tmp/mc_export_candidate_external_reviewer/microcosm-substrate"
    assert cli.main(["first-screen", long_label]) == 0
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert len(out) < 16000
    degradation = payload["omission_receipt"]["budget_degradation"]
    assert degradation["stdout_budget_chars"] == 16000
    assert degradation["over_budget_after_full_ladder"] is False
    assert degradation["applied_steps"]  # ladder actually fired for this label
    assert degradation["full_contract_command"] == (
        f"microcosm first-screen --full {long_label}"
    )
    # Demoted detail stays reachable behind the explicit full-contract drilldown.
    assert payload["output_policy"]["full_contract_preserved"] is True
    for row in payload["reader_route_menu"]["routes"]:
        assert "proof_surface" not in row


def test_first_screen_cli_short_label_keeps_full_route_detail(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["first-screen", "."]) == 0
    payload = json.loads(capsys.readouterr().out)

    degradation = payload["omission_receipt"]["budget_degradation"]
    assert degradation["applied_steps"] == []
    assert degradation["over_budget_after_full_ladder"] is False
    assert any(
        "proof_surface" in row for row in payload["reader_route_menu"]["routes"]
    )


def test_first_screen_cli_full_flag_preserves_full_contract(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["first-screen", "--full", "."]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema_version"] == "microcosm_first_screen_composition_card_v1"
    assert payload["reader_route_menu"]["machine_card_command"] == (
        "microcosm first-screen --card ."
    )
    assert payload["reader_route_menu"]["default_json_command"] == (
        "microcosm first-screen ."
    )
    assert "video_storyboard_packet" in payload
