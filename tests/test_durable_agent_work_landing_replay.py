from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import durable_agent_work_landing_replay
from microcosm_core.organs.durable_agent_work_landing_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
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
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["authority_ceiling"]["live_git_mutation_authorized"] is False
    assert result["authority_ceiling"]["broad_checkpoint_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_durable_agent_work_landing_receipts_use_secret_exclusion_and_public_relative(
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
        assert "body_redacted" not in text
        assert "private_state_scan" not in text
        assert "public_replacement_refs" not in text
        assert "private_source_body" not in _walk_keys(json.loads(text))
        assert "raw_diff_body" not in _walk_keys(json.loads(text))
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert "body_redacted" not in _walk_keys(payload)
        assert "private_state_scan" not in _walk_keys(payload)


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
    assert result["secret_exclusion_scan"]["body_in_receipt"] is False
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["authority_ceiling"]["commit_landed_claim_authorized_without_head_advance"] is False


def test_durable_agent_work_landing_card_reuses_fresh_bundle_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "durable_agent_work_landing_replay"
    )
    args = [
        "run-work-landing-bundle",
        "--input",
        str(BUNDLE_INPUT),
        "--out",
        str(out),
        "--card",
    ]

    assert main(args) == 0
    first_card = json.loads(capsys.readouterr().out)
    assert first_card["schema_version"] == CARD_SCHEMA_VERSION
    assert first_card["status"] == "pass"
    assert first_card["command_speed"]["receipt_reused"] is False
    assert first_card["command_speed"]["freshness_missing_path_count"] == 0
    assert first_card["work_landing"]["run_count"] == 3
    assert first_card["work_landing"]["metadata_blocked_count"] == 1
    assert first_card["validation"]["blocking_hit_count"] == 0
    assert "work_landing_runs" not in _walk_keys(first_card)
    assert "secret_exclusion_scan" not in _walk_keys(first_card)
    assert "authority_ceiling" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(durable_agent_work_landing_replay, "_build_result", fail_if_rebuilt)

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]
