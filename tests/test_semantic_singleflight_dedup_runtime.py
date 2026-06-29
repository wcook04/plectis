from __future__ import annotations

import json
from pathlib import Path

from microcosm_core.organs.semantic_singleflight_dedup_runtime import (
    ANTI_CLAIM,
    AUTHORITY_CEILING,
    CLAIM_CEILING,
    EXPECTED_NEGATIVE_CASES,
    ORGAN_ID,
    build_result,
    result_card,
    run,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "fixtures/first_wave/semantic_singleflight_dedup_runtime/input"


def test_fixture_matrix_passes_over_all_cases() -> None:
    result = build_result(INPUT_DIR)
    assert result["status"] == "pass"
    assert result["organ_id"] == ORGAN_ID
    assert result["case_count"] == 4
    assert result["positive_case_count"] == 2
    assert result["negative_case_count"] == 2
    assert result["passed_positive_case_count"] == 2
    assert result["observed_negative_case_count"] == 2


def test_every_declared_negative_case_is_present_and_observed() -> None:
    result = build_result(INPUT_DIR)
    negative_ids = {row["case_id"] for row in result["cases"] if row["case_type"] == "negative"}
    assert set(EXPECTED_NEGATIVE_CASES).issubset(negative_ids)
    by_id = {row["case_id"]: row for row in result["cases"]}
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        row = by_id[case_id]
        assert row["observed_ok"] is True
        for code in expected_codes:
            assert code in row["observed_error_codes"]


def test_scope_mutation_flips_the_content_key() -> None:
    result = build_result(INPUT_DIR)
    by_id = {row["case_id"]: row for row in result["cases"]}
    mutated = by_id["scope_mutation_changes_key"]
    assert mutated["key_changed"] is True
    assert "SINGLEFLIGHT_STALE_STATE_CANNOT_DEDUP" in mutated["observed_error_codes"]


def test_completed_run_is_reused_without_rerunning() -> None:
    result = build_result(INPUT_DIR)
    by_id = {row["case_id"]: row for row in result["cases"]}
    reuse = by_id["completed_reuse"]
    assert reuse["observed_ok"] is True
    assert reuse["observed_role"] == "reused"
    assert reuse["counter_value"] == "1"


def test_claim_ceiling_is_negated_and_anti_claim_is_present() -> None:
    low = CLAIM_CEILING.lower()
    assert any(cue in low for cue in ("not ", "does not ", "never", "without", "no "))
    assert "lock service" in low
    assert "global mutual exclusion" in low
    assert ANTI_CLAIM.strip()
    assert AUTHORITY_CEILING["release_authorized"] is False
    assert AUTHORITY_CEILING["distributed_lock_service"] is False


def test_result_card_projects_status_without_bodies() -> None:
    result = build_result(INPUT_DIR)
    card = result_card(result)
    assert card["organ_id"] == ORGAN_ID
    assert card["status"] == "pass"
    assert card["case_count"] == 4
    assert "cases" not in card


def test_run_writes_body_free_receipts(tmp_path: Path) -> None:
    out = tmp_path / "receipts"
    acceptance = tmp_path / "acceptance.json"
    result = run(INPUT_DIR, out, acceptance_out=acceptance)
    assert result["status"] == "pass"
    assert result["body_in_receipt"] is False
    written = json.loads((out / f"{ORGAN_ID}_result.json").read_text(encoding="utf-8"))
    assert written["status"] == "pass"
    acceptance_payload = json.loads(acceptance.read_text(encoding="utf-8"))
    assert acceptance_payload["real_substrate_disposition"] == "real_substrate_capsule"
    assert acceptance_payload["body_in_receipt"] is False
