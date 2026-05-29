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
