from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import cli
from microcosm_core.crown_jewel_demo import RECEIPT_NAME, run


def test_crown_jewel_demo_runs_five_organs_and_runtime_safety(tmp_path: Path) -> None:
    result = run(tmp_path / "crown_jewel_demo")

    assert result["status"] == "pass"
    assert result["organ_count"] == 5
    assert result["organ_pass_count"] == 5
    assert result["runtime_safety_check_count"] == 3
    assert {row["organ_id"] for row in result["organs"]} == {
        "agent_closeout_faithfulness_audit",
        "doctrine_fact_claim_audit",
        "self_ignorance_coverage_ledger",
        "bounded_autonomy_campaign_packet",
        "finance_forecast_evaluation_spine",
    }
    checks = {row["check_id"]: row for row in result["runtime_safety_checks"]}
    assert checks["durable_agent_work_landing_replay"]["status"] == "pass"
    assert checks["command_output_sidecar"]["status"] == "written_to_sidecar"
    assert checks["command_output_sidecar"]["digest"]
    assert checks["work_landing_control_spine"]["status"] in {"pass", "blocked"}
    assert result["anti_claim"]
    assert (tmp_path / "crown_jewel_demo" / RECEIPT_NAME).is_file()


def test_cli_crown_jewel_demo_route(tmp_path: Path, capsys) -> None:
    status = cli.main(["crown-jewel-demo", "run", "--out", str(tmp_path / "demo")])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["status"] == "pass"
    assert payload["organ_pass_count"] == 5
    assert payload["receipt_ref"].endswith(RECEIPT_NAME)
