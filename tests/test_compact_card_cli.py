from __future__ import annotations

import json
from pathlib import Path

import pytest

from microcosm_core import cli
from microcosm_core.runtime_shell import PRODUCT_PATH_DEMOTED_ORGAN_IDS


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _adapter_backed_organ_count() -> int:
    registry = json.loads(
        (MICROCOSM_ROOT / "core/organ_registry.json").read_text(encoding="utf-8")
    )
    accepted_count = len(
        [
            row
            for row in registry["implemented_organs"]
            if row.get("status") == "accepted_current_authority"
        ]
    )
    return accepted_count - len(PRODUCT_PATH_DEMOTED_ORGAN_IDS)


def test_cli_spine_card_is_compact_first_screen_lens(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["spine", "--card"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert len(json.dumps(payload, sort_keys=True)) < 10000
    assert payload["status"] == "pass"
    assert payload["schema_version"] == "microcosm_public_runtime_spine_card_v1"
    assert payload["command"] == "microcosm spine --card"
    assert payload["full_command"] == "microcosm spine"
    assert payload["endpoint"] == "/spine-card"
    assert payload["surface_counts"]["adapter_backed_organ_count"] == (
        _adapter_backed_organ_count()
    )
    assert payload["runtime_spine_summary"]["accepted_organ_count"] == (
        _adapter_backed_organ_count()
    )
    assert payload["payload_boundary"]["omits_full_accepted_runtime_spine"] is True
    assert "accepted_runtime_spine" not in payload
    assert "first_run_path" not in payload


def test_cli_authority_card_is_compact_first_screen_lens(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["authority", "--card"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert len(json.dumps(payload, sort_keys=True)) < 12000
    assert payload["status"] == "pass"
    assert payload["schema_version"] == "microcosm_public_authority_card_v1"
    assert payload["command"] == "microcosm authority --card"
    assert payload["full_command"] == "microcosm authority"
    assert payload["endpoint"] == "/authority-card"
    assert payload["surface_counts"]["organ_authority_count"] == (
        _adapter_backed_organ_count()
    )
    assert payload["surface_counts"]["surface_authority_count"] >= 40
    assert payload["payload_boundary"]["omits_full_surface_authority"] is True
    assert payload["payload_boundary"]["omits_full_organ_authority"] is True
    assert "surface_authority" not in payload
    assert "organ_authority" not in payload


def test_cli_intake_card_is_compact_first_screen_lens(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["intake", "--card"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert len(json.dumps(payload, sort_keys=True)) < 14000
    assert payload["status"] == "pass"
    assert payload["schema_version"] == "microcosm_runtime_reveal_import_bridge_card_v1"
    assert payload["command"] == "microcosm intake --card"
    assert payload["full_command"] == "microcosm intake"
    assert payload["endpoint"] == "/intake-card"
    assert payload["full_endpoint"] == "/intake"
    assert payload["surface_counts"]["projection_cell_count"] >= 15
    assert payload["surface_counts"]["open_actionable_cell_count"] == 0
    assert 1 <= payload["surface_counts"]["cell_status_preview_count"] <= 8
    assert payload["payload_boundary"]["omits_full_cell_status"] is True
    assert payload["payload_boundary"]["omits_full_projection_cells"] is True
    assert payload["payload_boundary"]["omits_full_runtime_bridge_evidence_refs"] is True
    assert "cell_status" not in payload
    assert "first_run_bridge" not in payload
    assert "runtime_bridge_evidence_refs" not in payload
