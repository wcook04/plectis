from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = MICROCOSM_ROOT / "scripts/workingness_card.py"


@pytest.fixture()
def workingness_card_module():
    spec = importlib.util.spec_from_file_location(
        "microcosm_workingness_card_tool",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_workingness_card_omits_full_failure_map(workingness_card_module) -> None:
    card = workingness_card_module.workingness_card(MICROCOSM_ROOT)
    encoded = json.dumps(card, sort_keys=True)

    assert card["schema_version"] == "microcosm_workingness_command_speed_card_v1"
    assert card["status"] == "pass"
    assert card["card_status"] == "clear"
    assert card["source_command"] == "microcosm workingness"
    assert card["drilldown_command"] == "microcosm workingness"
    assert card["surface_counts"]["mapped_organ_count"] == 47
    assert card["surface_counts"]["rows_with_failure_modes"] == 47
    assert card["surface_counts"]["missing_standard_count"] == 0
    assert card["surface_counts"]["missing_failure_modes_count"] == 0
    assert card["output_economy"]["thing_failure_map_exported"] is False
    assert "thing_failure_map" not in card
    assert "known_failure_modes" not in encoded
    assert len(encoded) < 8000


def test_workingness_card_cli_outputs_compact_json(
    workingness_card_module,
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = workingness_card_module.main(["--root", str(MICROCOSM_ROOT)])
    payload = json.loads(capsys.readouterr().out)

    assert status == 0
    assert payload["schema_version"] == "microcosm_workingness_command_speed_card_v1"
    assert payload["status"] == "pass"
    assert payload["output_economy"]["compact_route_for_first_screen"] is True
    assert payload["output_economy"]["receipt_persisted"] is False
