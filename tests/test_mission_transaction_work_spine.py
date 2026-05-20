from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.mission_transaction_work_spine import (
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    run,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
MISSION_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/mission_transaction_work_spine/input"
PER_OUTPUT_RECEIPT_FIELD_FLOOR = {
    "receipts/first_wave/mission_transaction_work_spine/dependency_blocked.json": [
        "schema_version",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "status",
        "blocked_workitem_ids",
        "dependency_refs",
        "schedulable",
        "schedulability_decision_source",
        "dependency_unlock_resolution_basis",
        "expected_negative_cases",
        "observed_negative_cases",
        "error_codes",
        "anti_claim",
        "private_state_scan",
        "authority_ceiling",
        "receipt_paths",
    ],
    "receipts/first_wave/mission_transaction_work_spine/claim_preflight_result.json": [
        "schema_version",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "status",
        "claim_id",
        "decision",
        "conflict_claim_ids",
        "same_path_conflict_claim_ids",
        "claim_conflict_recheck_status",
        "expected_parent_status",
        "replan_required",
        "expected_negative_cases",
        "observed_negative_cases",
        "error_codes",
        "anti_claim",
        "private_state_scan",
        "authority_ceiling",
        "receipt_paths",
    ],
    "receipts/first_wave/mission_transaction_work_spine/closeout_status_projection.json": [
        "schema_version",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "status",
        "work_item_id",
        "status_before",
        "status_after",
        "receipt_refs_drained",
        "exact_receipt_drain_scope",
        "receipt_drain_exclusivity_status",
        "derived_not_authority",
        "expected_negative_cases",
        "observed_negative_cases",
        "error_codes",
        "anti_claim",
        "private_state_scan",
        "authority_ceiling",
        "receipt_paths",
    ],
    "receipts/first_wave/mission_transaction_work_spine/dependency_unlock_scheduler_receipt.json": [
        "schema_version",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "status",
        "blocked_workitem_ids",
        "ready_but_unsatisfied_workitem_ids",
        "resolved_dependency_refs",
        "dependency_status_by_workitem",
        "dependency_resolution_receipt",
        "unsatisfied_dep_ids",
        "downstream_unlock_edges",
        "unlocks_by_rank",
        "dangling_dependency_refs",
        "schedulable_workitem_ids",
        "downstream_schedulable_before",
        "schedulability_decision_source",
        "dependency_unlock_resolution_basis",
        "anomaly_refs",
        "derived_not_authority",
        "expected_negative_cases",
        "observed_negative_cases",
        "error_codes",
        "anti_claim",
        "private_state_scan",
        "authority_ceiling",
        "receipt_paths",
    ],
    "receipts/first_wave/mission_transaction_work_spine/work_landing_reconcile_plan.json": [
        "schema_version",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "status",
        "mode",
        "recommended_next_action",
        "actions",
        "mutation_policy",
        "apply_result",
        "ordered_controller_action_ids",
        "transaction_id",
        "work_landing_reconcile_status",
        "receipt_drain_prerequisite_status",
        "claim_release_order_status",
        "expected_negative_cases",
        "observed_negative_cases",
        "error_codes",
        "anti_claim",
        "private_state_scan",
        "authority_ceiling",
        "receipt_paths",
    ],
}


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


def test_mission_transaction_work_spine_observes_required_negative_cases(
    tmp_path: Path,
) -> None:
    live_preflight = MICROCOSM_ROOT / "receipts/preflight/mission_transaction_work_spine.json"
    before = live_preflight.read_text(encoding="utf-8") if live_preflight.exists() else None
    result = run(MISSION_FIXTURE_INPUT, tmp_path / "receipts", command="pytest")

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert all(not Path(path).is_absolute() for path in result["receipt_paths"])
    assert (tmp_path / "receipts/preflight/mission_transaction_work_spine.json").is_file()
    after = live_preflight.read_text(encoding="utf-8") if live_preflight.exists() else None
    assert after == before
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]
    assert result["claim_preflight_result"]["same_path_conflict_claim_ids"] == ["claim_a"]
    assert result["claim_preflight_result"]["expected_parent_status"] == "stale_parent_rejected"
    assert result["dependency_unlock_scheduler"]["ready_but_unsatisfied_workitem_ids"] == [
        "cap_ready_with_unsatisfied"
    ]
    assert result["closeout_status_projection"]["receipt_refs_drained"] == [
        "receipt_expected_001"
    ]


def test_mission_transaction_work_spine_receipts_are_public_relative_and_redacted(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/mission_transaction_work_spine",
        public_root / "fixtures/first_wave/mission_transaction_work_spine",
    )

    result = run(
        public_root / "fixtures/first_wave/mission_transaction_work_spine/input",
        public_root / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == EXPECTED_RECEIPT_PATHS
    for receipt_path in EXPECTED_RECEIPT_PATHS:
        receipt_file = public_root / receipt_path
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "/private/var" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert '"body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["private_state_scan"]["blocking_hit_count"] == 0
        assert payload["missing_negative_cases"] == []
        assert set(payload["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
        for hit in payload["private_state_scan"]["hits"]:
            assert hit["body_redacted"] is True
            assert not Path(hit["path"]).is_absolute()


def test_mission_transaction_work_spine_receipts_satisfy_macro_field_floor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/mission_transaction_work_spine",
        public_root / "fixtures/first_wave/mission_transaction_work_spine",
    )
    run(
        public_root / "fixtures/first_wave/mission_transaction_work_spine/input",
        public_root / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    for receipt_path, required_fields in PER_OUTPUT_RECEIPT_FIELD_FLOOR.items():
        payload = json.loads((public_root / receipt_path).read_text(encoding="utf-8"))
        missing = [field for field in required_fields if field not in payload]
        assert missing == []

    reconcile = json.loads(
        (
            public_root
            / "receipts/first_wave/mission_transaction_work_spine/work_landing_reconcile_plan.json"
        ).read_text(encoding="utf-8")
    )
    assert reconcile["ordered_controller_action_ids"] == [
        "record_scoped_commit_landing",
        "intake_exact_receipt_refs",
        "drain_exact_receipts",
        "closeout_landing_attempt",
        "release_claims",
        "recompute_status_projection",
    ]
    assert reconcile["mutation_policy"]["live_state_mutation"] is False
