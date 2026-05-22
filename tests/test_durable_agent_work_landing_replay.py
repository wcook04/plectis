from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.durable_agent_work_landing_replay import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_work_landing_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/durable_agent_work_landing_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/durable_agent_work_landing_replay/"
    "exported_work_landing_replay_bundle"
)


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def test_durable_agent_work_landing_replay_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/durable_agent_work_landing_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "durable_agent_work_landing_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["run_count"] == 3
    assert result["metadata_blocked_count"] == 1
    assert result["landed_commit_count"] == 1
    assert result["validation_order_required_count"] == 2
    assert result["validation_order_pass_count"] == 2
    assert result["authority_ceiling"]["live_git_mutation_authorized"] is False
    assert result["authority_ceiling"]["broad_checkpoint_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_durable_agent_work_landing_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/durable_agent_work_landing_replay",
        public_root / "fixtures/first_wave/durable_agent_work_landing_replay",
    )

    result = run(
        public_root
        / "fixtures/first_wave/durable_agent_work_landing_replay/input",
        public_root / "receipts/first_wave/durable_agent_work_landing_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "private_source_body" not in _walk_keys(json.loads(text))
        assert "raw_diff_body" not in _walk_keys(json.loads(text))


def test_durable_agent_work_landing_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_work_landing_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "durable_agent_work_landing_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_work_landing_replay_bundle"
    assert result["bundle_id"] == "durable_agent_work_landing_replay_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["run_count"] == 3
    assert result["metadata_blocked_count"] == 1
    assert result["validation_order_required_count"] == 2
    assert result["validation_order_pass_count"] == 2
    assert result["authority_ceiling"]["commit_landed_claim_authorized_without_head_advance"] is False
