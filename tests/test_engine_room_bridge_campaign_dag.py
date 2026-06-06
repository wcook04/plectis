from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from microcosm_core.engine_room.bridge_campaign_dag import (
    ANTI_CLAIMS,
    CLAIM_CEILING,
    validate_campaign,
    validate_fixture_dir,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "fixtures/first_wave/engine_room_bridge_campaign_dag/input"


def _load(name: str) -> dict:
    return json.loads((INPUT_DIR / name).read_text(encoding="utf-8"))


def _rule_ids(result) -> set[str]:
    return {decision.rule_id for decision in result.decisions if decision.outcome == "reject"}


def test_valid_campaign_passes_contract_rules() -> None:
    result = validate_campaign(_load("valid_campaign.json"), provider="chatgpt", workers=3)
    assert result.ok is True
    assert not result.errors


def test_cycle_is_rejected_before_dispatch() -> None:
    result = validate_campaign(_load("cyclic_campaign.json"), provider="chatgpt", workers=2)
    assert result.ok is False
    assert "CR012" in _rule_ids(result)


def test_provider_parallelism_ceiling_is_rejected() -> None:
    result = validate_campaign(_load("over_parallel_campaign.json"), provider="chatgpt", workers=99)
    assert result.ok is False
    assert "VR005" in _rule_ids(result)


def test_dangling_synthesis_is_rejected() -> None:
    result = validate_campaign(_load("dangling_synthesis_campaign.json"), provider="local", workers=1)
    assert result.ok is False
    assert {"CR011", "CR014"} & _rule_ids(result)


def test_fixture_matrix_matches_positive_and_negative_expectations() -> None:
    receipt = validate_fixture_dir(INPUT_DIR)
    assert receipt["status"] == "pass"
    assert receipt["case_count"] == 4
    assert receipt["passed_case_count"] == 4
    assert receipt["source_to_target_relation"] == "source_faithful_public_refactor"
    assert "not_a_dispatcher" in ANTI_CLAIMS
    assert "does not dispatch" in CLAIM_CEILING


def test_module_cli_emits_json_receipt() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core.engine_room.bridge_campaign_dag",
            "validate-fixtures",
            "--input",
            str(INPUT_DIR),
            "--json",
        ],
        cwd=ROOT,
        env={"PYTHONPATH": "src"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["organ_id"] == "engine_room_bridge_campaign_dag"
    assert payload["status"] == "pass"
