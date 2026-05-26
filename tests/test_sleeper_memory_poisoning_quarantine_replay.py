from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import sleeper_memory_poisoning_quarantine_replay
from microcosm_core.organs.sleeper_memory_poisoning_quarantine_replay import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_quarantine_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/sleeper_memory_poisoning_quarantine_replay/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/sleeper_memory_poisoning_quarantine_replay/"
    "exported_sleeper_memory_poisoning_bundle"
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


def test_sleeper_memory_poisoning_quarantine_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/sleeper_memory_poisoning_quarantine_replay",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "sleeper_memory_poisoning_quarantine_replay_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["session_count"] == 4
    assert result["session_roles"] == [
        "poisoned_source_seen",
        "memory_write_quarantined",
        "later_retrieval_action_gated",
        "rollback_and_cold_rerun",
    ]
    assert result["proposal_count"] == 2
    assert result["quarantined_write_count"] == 1
    assert result["admitted_control_count"] == 1
    assert result["retrieval_replay_count"] == 1
    assert result["blocked_before_action_count"] == 1
    assert result["rollback_count"] == 1
    assert result["rerun_pass_count"] == 1
    assert result["authority_ceiling"]["private_memory_body_export_authorized"] is False
    assert result["authority_ceiling"]["live_user_memory_claim_authorized"] is False
    assert (
        result["authority_ceiling"][
            "trusted_promotion_from_untrusted_context_authorized"
        ]
        is False
    )
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_sleeper_memory_poisoning_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/sleeper_memory_poisoning_quarantine_replay",
        public_root / "fixtures/first_wave/sleeper_memory_poisoning_quarantine_replay",
    )

    result = run(
        public_root / "fixtures/first_wave/sleeper_memory_poisoning_quarantine_replay/input",
        public_root / "receipts/first_wave/sleeper_memory_poisoning_quarantine_replay",
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
        keys = _walk_keys(json.loads(text))
        assert "private_memory_body" not in keys
        assert "raw_transcript" not in keys
        assert "raw_transcript_body" not in keys
        assert "private_thread_body" not in keys
        assert "provider_payload" not in keys
        assert "credential_value" not in keys
        assert "secret_value" not in keys


def test_sleeper_memory_poisoning_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_quarantine_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "sleeper_memory_poisoning_quarantine_replay",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_sleeper_memory_poisoning_bundle"
    assert result["bundle_id"] == "sleeper_memory_poisoning_quarantine_policy_refactor"
    assert result["body_import_status"] == "public_body_free_policy_refactor_landed"
    assert (
        result["product_path_role"]
        == "algorithmic_projection_public_memory_security_policy_refactor"
    )
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["session_count"] == 4
    assert result["quarantined_write_count"] == 1
    assert result["blocked_before_action_count"] == 1
    assert result["rerun_pass_count"] == 1
    assert result["authority_ceiling"]["live_memory_product_claim_authorized"] is False


def test_sleeper_memory_poisoning_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "sleeper_memory_poisoning_quarantine_replay"
    )
    args = [
        "run-quarantine-bundle",
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
    assert first_card["command_speed"]["freshness_input_count"] == 8
    assert first_card["sleeper_memory"]["session_count"] == 4
    assert first_card["sleeper_memory"]["proposal_count"] == 2
    assert first_card["sleeper_memory"]["quarantined_write_count"] == 1
    assert first_card["sleeper_memory"]["admitted_control_count"] == 1
    assert first_card["sleeper_memory"]["retrieval_replay_count"] == 1
    assert first_card["sleeper_memory"]["blocked_before_action_count"] == 1
    assert first_card["sleeper_memory"]["rollback_count"] == 1
    assert first_card["sleeper_memory"]["rerun_pass_count"] == 1
    assert first_card["validation"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["private_state_blocking_hit_count"] == 0
    assert "session_rows" not in _walk_keys(first_card)
    assert "write_rows" not in _walk_keys(first_card)
    assert "retrieval_rows" not in _walk_keys(first_card)
    assert "rollback_rows" not in _walk_keys(first_card)
    assert "private_state_scan" not in _walk_keys(first_card)
    assert "findings" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        sleeper_memory_poisoning_quarantine_replay,
        "_build_result",
        fail_if_rebuilt,
    )

    assert main(args) == 0
    cached_card = json.loads(capsys.readouterr().out)
    assert cached_card["status"] == "pass"
    assert cached_card["command_speed"]["receipt_reused"] is True
    assert cached_card["command_speed"]["freshness_digest"] == (
        first_card["command_speed"]["freshness_digest"]
    )
    assert cached_card["receipt_paths"] == first_card["receipt_paths"]
