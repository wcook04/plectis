from __future__ import annotations

import json
from pathlib import Path

import pytest

from microcosm_core import cli


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_cli_intake_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["intake"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_runtime_reveal_import_bridge_v1"
    assert payload["bridge_id"] == "runtime_reveal_import_bridge"
    assert payload["projection_cell_count"] == 78
    by_cell = {row["cell_id"]: row for row in payload["cell_status"]}
    assert by_cell["agent_observability_store_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["projection_protocol_self_host"]["projection_status"] == (
        "self_hosted_status_protocol_landed"
    )
    assert by_cell["runtime_reveal_import_bridge"]["projection_status"] == (
        "runtime_bridge_landed"
    )
    assert by_cell["finance_eval_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["work_landing_control_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["task_ledger_control_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["work_ledger_control_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert payload["open_actionable_cell_count"] == 0
    assert payload["authority_ceiling"]["release_authorized"] is False


def test_cli_formal_math_readiness_plan_smoke(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(
        [
            "formal-math-readiness-gate",
            "plan",
            "--input",
            (
                MICROCOSM_ROOT / "fixtures/first_wave/formal_math_readiness_gate/input"
            ).as_posix(),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "formal_math_readiness_extension_preview_v1"
    assert payload["projection_cell_id"] == "formal_math_readiness_extensions"
    assert payload["readiness_extension_board"]["premise_index_projection"][
        "premise_count"
    ] == 11
    assert payload["readiness_extension_board"]["tactic_portfolio_projection"][
        "available_tactic_count"
    ] == 6
    assert payload["authority_ceiling"]["lean_lake_execution_authorized"] is False
