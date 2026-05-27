from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs import proof_derived_governed_mutation_authorization
from microcosm_core.organs.proof_derived_governed_mutation_authorization import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    main,
    run,
    run_authorization_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input"
)
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/proof_derived_governed_mutation_authorization/"
    "exported_governed_mutation_authorization_bundle"
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


def test_governed_mutation_authorization_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path
        / "receipts/first_wave/proof_derived_governed_mutation_authorization",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/"
        "proof_derived_governed_mutation_authorization_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["proposal_count"] == 3
    assert result["authorized_mutation_count"] == 3
    assert result["write_or_rollback_count"] == 2
    assert result["proof_cell_count"] == 3
    assert result["accepted_proof_cell_count"] == 3
    assert result["policy_verdict_count"] == 6
    assert result["visible_policy_verdict_count"] == 6
    assert result["logged_side_effect_count"] == 2
    assert result["rollback_pass_count"] == 2
    assert result["cold_replay_pass_count"] == 3
    assert result["authority_ceiling"]["live_cloud_account_authorized"] is False
    assert result["authority_ceiling"]["standing_credentials_authorized"] is False
    assert result["authority_ceiling"]["source_mutation_authorized"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_governed_mutation_authorization_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/proof_derived_governed_mutation_authorization",
        public_root / "fixtures/first_wave/proof_derived_governed_mutation_authorization",
    )

    result = run(
        public_root
        / "fixtures/first_wave/proof_derived_governed_mutation_authorization/input",
        public_root
        / "receipts/first_wave/proof_derived_governed_mutation_authorization",
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
        assert "credential_value" not in keys
        assert "secret_value" not in keys
        assert "token_value" not in keys
        assert "provider_payload" not in keys
        assert "private_account_id" not in keys
        assert "raw_policy_vote_body" not in keys
        assert "raw_proof_body" not in keys
        assert "cloud_account_id" not in keys


def test_governed_mutation_authorization_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_authorization_bundle(
        BUNDLE_INPUT,
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "proof_derived_governed_mutation_authorization",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_governed_mutation_authorization_bundle"
    assert (
        result["bundle_id"]
        == "proof_derived_governed_mutation_authorization_runtime_example"
    )
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["authorized_mutation_count"] == 3
    assert result["logged_side_effect_count"] == 2
    assert result["rollback_pass_count"] == 2
    assert result["cold_replay_pass_count"] == 3
    assert result["authority_ceiling"]["live_cloud_account_authorized"] is False


def test_governed_mutation_authorization_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    capsys: Any,
    monkeypatch: Any,
) -> None:
    out = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/"
        "proof_derived_governed_mutation_authorization"
    )
    args = [
        "run-authorization-bundle",
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
    assert first_card["command_speed"]["freshness_input_count"] == 11
    assert (
        first_card["validation"]["bundle_id"]
        == "proof_derived_governed_mutation_authorization_runtime_example"
    )
    auth = first_card["governed_mutation_authorization"]
    assert auth["proposal_count"] == 3
    assert auth["authorized_mutation_count"] == 3
    assert auth["write_or_rollback_count"] == 2
    assert auth["proof_cell_count"] == 3
    assert auth["policy_verdict_count"] == 6
    assert auth["logged_side_effect_count"] == 2
    assert auth["rollback_pass_count"] == 2
    assert auth["cold_replay_pass_count"] == 3
    assert first_card["negative_case_coverage"]["missing_negative_case_count"] == 0
    assert first_card["validation"]["private_state_blocking_hit_count"] == 0
    assert "proof_cell_rows" not in _walk_keys(first_card)
    assert "policy_verdict_rows" not in _walk_keys(first_card)
    assert "proposal_rows" not in _walk_keys(first_card)
    assert "side_effect_rows" not in _walk_keys(first_card)
    assert "rollback_rows" not in _walk_keys(first_card)
    assert "cold_replay_rows" not in _walk_keys(first_card)
    assert "private_state_scan" not in _walk_keys(first_card)
    assert "authority_ceiling" not in _walk_keys(first_card)
    assert "anti_claim" not in _walk_keys(first_card)

    def fail_if_rebuilt(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the existing receipt")

    monkeypatch.setattr(
        proof_derived_governed_mutation_authorization,
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
