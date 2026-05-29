from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.mission_transaction_work_spine import (
    EXPORTED_MISSION_TRANSACTION_BUNDLE_RECEIPT_PATH,
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    ORDERED_CONTROLLER_ACTION_IDS,
    run,
    run_mission_transaction_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
MISSION_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/mission_transaction_work_spine/input"
MISSION_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/mission_transaction_work_spine/exported_mission_transaction_bundle"
)
SOURCE_FAITHFUL_WORK_LANDING_ACTION_IDS = [
    "verify_scoped_commit_landed",
    "ensure_work_ledger_progress_event",
    "record_scoped_commit_landing",
    "ensure_task_ledger_receipt_intake_or_event",
    "drain_task_ledger_intake_if_exclusive",
    "closeout_landing_attempt",
    "rebuild_task_ledger_projection",
    "check_work_ledger_projection",
    "close_work_ledger_transaction_thread",
    "finalize_work_ledger_session",
    "release_claims",
    "recompute_convergence",
]
SOURCE_FAITHFUL_PUBLIC_REFACTOR_STATUS = "source_faithful_public_refactor_landed"
PUBLIC_MISSION_PREFLIGHT_TARGET_REF = (
    "microcosm-substrate/src/microcosm_core/macro_tools/"
    "mission_transaction_preflight.py"
)
TASK_LEDGER_SOURCE_IMPORT_STATUS = "public_runtime_import_landed"
TASK_LEDGER_SOURCE_MODULE_IDS = [
    "task_ledger_events_body_import",
    "task_ledger_apply_tool_body_import",
    "task_ledger_priority_body_import",
    "task_ledger_project_tool_body_import",
]
TASK_LEDGER_SOURCE_REFS = [
    "system/lib/task_ledger_events.py",
    "tools/meta/factory/task_ledger_apply.py",
    "system/lib/task_ledger_priority.py",
    "tools/meta/factory/task_ledger_project.py",
]
TASK_LEDGER_SOURCE_TARGET_REFS = [
    "microcosm-substrate/examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_modules/system/lib/task_ledger_events.py",
    "microcosm-substrate/examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_modules/tools/meta/factory/task_ledger_apply.py",
    "microcosm-substrate/examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_modules/system/lib/task_ledger_priority.py",
    "microcosm-substrate/examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_modules/tools/meta/factory/task_ledger_project.py",
]
TASK_LEDGER_SOURCE_LINE_COUNT = 15200
WORK_LEDGER_SOURCE_IMPORT_STATUS = "public_runtime_import_landed"
WORK_LEDGER_SOURCE_MODULE_IDS = [
    "work_ledger_tool_body_import",
    "work_ledger_event_body_import",
    "work_ledger_runtime_body_import",
    "work_ledger_standard_body_import",
]
WORK_LEDGER_SOURCE_REFS = [
    "tools/meta/factory/work_ledger.py",
    "system/lib/work_ledger.py",
    "system/lib/work_ledger_runtime.py",
    "codex/standards/std_work_ledger.json",
]
WORK_LEDGER_SOURCE_TARGET_REFS = [
    "microcosm-substrate/examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_modules/tools/meta/factory/work_ledger.py",
    "microcosm-substrate/examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_modules/system/lib/work_ledger.py",
    "microcosm-substrate/examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_modules/system/lib/work_ledger_runtime.py",
    "microcosm-substrate/examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_modules/codex/standards/std_work_ledger.json",
]
WORK_LEDGER_SOURCE_LINE_COUNT = 14440
CHECKPOINT_SOURCE_IMPORT_STATUS = "public_runtime_import_landed"
CHECKPOINT_SOURCE_MODULE_IDS = [
    "checkpoint_script_body_import",
    "checkpoint_private_backup_body_import",
]
CHECKPOINT_SOURCE_REFS = [
    "checkpoint",
    "tools/meta/control/checkpoint_private_backup.py",
]
CHECKPOINT_SOURCE_TARGET_REFS = [
    "microcosm-substrate/examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_modules/checkpoint",
    "microcosm-substrate/examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_modules/tools/meta/control/checkpoint_private_backup.py",
]
CHECKPOINT_SOURCE_LINE_COUNT = 1234
MISSION_CONTROL_SOURCE_IMPORT_STATUS = "public_runtime_import_landed"
MISSION_CONTROL_SOURCE_MODULE_IDS = [
    "scoped_commit_tool_body_import",
    "mission_transaction_preflight_tool_body_import",
]
MISSION_CONTROL_SOURCE_REFS = [
    "tools/meta/control/scoped_commit.py",
    "tools/meta/control/mission_transaction_preflight.py",
]
MISSION_CONTROL_SOURCE_TARGET_REFS = [
    "microcosm-substrate/examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_modules/tools/meta/control/scoped_commit.py",
    "microcosm-substrate/examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_modules/tools/meta/control/mission_transaction_preflight.py",
]
MISSION_CONTROL_SOURCE_LINE_COUNT = 1922
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
        "secret_exclusion_scan",
        "public_work_landing_status",
        "public_mission_transaction_preflight",
        "body_import_status",
        "body_import_verification",
        "body_in_receipt",
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
        "secret_exclusion_scan",
        "public_work_landing_status",
        "public_mission_transaction_preflight",
        "body_import_status",
        "body_import_verification",
        "body_in_receipt",
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
        "secret_exclusion_scan",
        "public_work_landing_status",
        "public_mission_transaction_preflight",
        "body_import_status",
        "body_import_verification",
        "body_in_receipt",
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
        "secret_exclusion_scan",
        "public_work_landing_status",
        "public_mission_transaction_preflight",
        "body_import_status",
        "body_import_verification",
        "body_in_receipt",
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
        "secret_exclusion_scan",
        "public_work_landing_status",
        "public_mission_transaction_preflight",
        "body_import_status",
        "body_import_verification",
        "body_in_receipt",
        "authority_ceiling",
        "receipt_paths",
    ],
    "receipts/first_wave/mission_transaction_work_spine/checkpoint_lane_decision.json": [
        "schema_version",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "status",
        "checkpoint_lane_decisions",
        "recommended_lane_by_case",
        "selection_policy",
        "broad_checkpoint_requires_operator_authorization",
        "suspected_secret_requires_hard_stop",
        "dirty_tree_blocks_scoped_commit",
        "expected_negative_cases",
        "observed_negative_cases",
        "error_codes",
        "anti_claim",
        "secret_exclusion_scan",
        "public_work_landing_status",
        "public_mission_transaction_preflight",
        "body_import_status",
        "body_import_verification",
        "body_in_receipt",
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
    assert ORDERED_CONTROLLER_ACTION_IDS == SOURCE_FAITHFUL_WORK_LANDING_ACTION_IDS

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
    assert result["public_mission_transaction_preflight"]["status"] == "blocked"
    assert result["public_mission_transaction_preflight"]["landing_decision"]["decision"] == (
        "blocked_replan_required"
    )
    assert result["public_mission_transaction_preflight"]["target_ref"] == (
        PUBLIC_MISSION_PREFLIGHT_TARGET_REF
    )
    assert result["dependency_unlock_scheduler"]["ready_but_unsatisfied_workitem_ids"] == [
        "cap_ready_with_unsatisfied"
    ]
    assert result["closeout_status_projection"]["receipt_refs_drained"] == [
        "receipt_expected_001"
    ]
    assert result["checkpoint_lane_decision"]["recommended_lane_by_case"][
        "mixed_owned_dirty_tree"
    ] == "scoped_commit"
    assert result["checkpoint_lane_decision"]["recommended_lane_by_case"][
        "operator_requested_broad_checkpoint"
    ] == "broad_checkpoint"
    assert result["checkpoint_lane_decision"]["recommended_lane_by_case"][
        "suspected_secret_without_hard_stop"
    ] == "hard_stop"
    assert result["checkpoint_lane_decision"]["dirty_tree_blocks_scoped_commit"] is False
    assert "CHECKPOINT_BROAD_AUTH_REQUIRED" in result["error_codes"]
    assert "CHECKPOINT_SECRET_REQUIRES_HARD_STOP" in result["error_codes"]
    assert "CHECKPOINT_DIRTY_TREE_NOT_SCOPED_BLOCKER" in result["error_codes"]
    assert "CHECKPOINT_LANE_DECISION_REQUIRED" in result["error_codes"]


def test_mission_transaction_work_spine_receipts_are_public_relative_and_secret_excluded(
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
        assert "private_state_scan" not in payload
        assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["body_import_status"] == SOURCE_FAITHFUL_PUBLIC_REFACTOR_STATUS
        assert payload["public_work_landing_status"]["status"] == "pass"
        assert payload["public_mission_transaction_preflight"]["target_ref"] == (
            PUBLIC_MISSION_PREFLIGHT_TARGET_REF
        )
        assert payload["missing_negative_cases"] == []
        assert set(payload["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
        for hit in payload["secret_exclusion_scan"]["hits"]:
            assert hit["body_in_receipt"] is False
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
    assert reconcile["ordered_controller_action_ids"] == ORDERED_CONTROLLER_ACTION_IDS
    assert reconcile["mutation_policy"]["live_state_mutation"] is False
    assert reconcile["body_in_receipt"] is False


def test_mission_transaction_work_spine_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_mission_transaction_bundle(
        MISSION_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_mission_transaction_bundle"
    assert result["bundle_id"] == "public_mission_transaction_work_spine_runtime_bundle"
    assert result["expected_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["public_work_landing_not_live_ledger_authority"] is True
    assert result["authority_ceiling"]["live_task_ledger_mutation_authorized"] is False
    assert result["authority_ceiling"]["live_work_ledger_mutation_authorized"] is False
    assert result["workitem_rows_projection_not_authority"] is True
    assert result["claim_rows_projection_not_authority"] is True
    assert result["accepted_claim_ids"] == ["claim_public_mission_adapter_runtime"]
    assert result["schedulable_workitem_ids"] == ["cap_public_mission_adapter_runtime"]
    assert result["resolved_dependency_refs"] == ["cap_navigation_adapter_accepted"]
    assert result["claim_preflight_result"]["replan_required"] is False
    assert result["scoped_mutation_receipt"]["broad_stage_used"] is False
    assert result["checkpoint_lane_decision"]["recommended_lane_by_case"][
        "runtime_public_operator_broad_checkpoint"
    ] == "broad_checkpoint"
    assert result["checkpoint_lane_decision"]["recommended_lane_by_case"][
        "runtime_public_secret_suspected"
    ] == "hard_stop"
    assert result["checkpoint_lane_decision"][
        "broad_checkpoint_requires_operator_authorization"
    ] is True
    assert result["checkpoint_lane_decision"]["dirty_tree_blocks_scoped_commit"] is False
    assert result["closeout_status_projection"]["derived_not_authority"] is True
    assert result["receipt_drain_plan"]["receipt_drain_exclusivity_status"] == (
        "only_declared_receipts_drained"
    )
    assert result["work_landing_reconcile_plan"]["ordered_controller_action_ids"] == (
        ORDERED_CONTROLLER_ACTION_IDS
    )
    assert result["work_landing_reconcile_plan"]["controller_action_count"] == len(
        SOURCE_FAITHFUL_WORK_LANDING_ACTION_IDS
    )
    assert result["work_landing_reconcile_plan"]["mutation_policy"]["live_state_mutation"] is False
    assert result["body_import_status"] == SOURCE_FAITHFUL_PUBLIC_REFACTOR_STATUS
    assert result["body_import_verification"]["source_faithful_controller_action_ids"] == (
        SOURCE_FAITHFUL_WORK_LANDING_ACTION_IDS
    )
    assert result["public_work_landing_status"]["status"] == "pass"
    assert result["public_mission_transaction_preflight"]["status"] == "pass"
    assert result["public_mission_transaction_preflight"]["landing_decision"]["recommended_lane"] == (
        "scoped_commit"
    )
    assert result["public_mission_transaction_preflight"]["target_ref"] == (
        PUBLIC_MISSION_PREFLIGHT_TARGET_REF
    )
    assert result["task_ledger_control_source_import_status"] == (
        TASK_LEDGER_SOURCE_IMPORT_STATUS
    )
    assert result["copied_task_ledger_source_count"] == len(TASK_LEDGER_SOURCE_MODULE_IDS)
    assert result["copied_task_ledger_source_line_count"] == (
        TASK_LEDGER_SOURCE_LINE_COUNT
    )
    assert result["task_ledger_control_source_import"]["status"] == "pass"
    assert result["task_ledger_control_source_import"]["module_ids"] == (
        TASK_LEDGER_SOURCE_MODULE_IDS
    )
    assert result["work_ledger_control_source_import_status"] == (
        WORK_LEDGER_SOURCE_IMPORT_STATUS
    )
    assert result["copied_work_ledger_source_count"] == len(WORK_LEDGER_SOURCE_MODULE_IDS)
    assert result["copied_work_ledger_source_line_count"] == (
        WORK_LEDGER_SOURCE_LINE_COUNT
    )
    assert result["work_ledger_control_source_import"]["status"] == "pass"
    assert result["work_ledger_control_source_import"]["module_ids"] == (
        WORK_LEDGER_SOURCE_MODULE_IDS
    )
    assert result["checkpoint_lane_source_import_status"] == (
        CHECKPOINT_SOURCE_IMPORT_STATUS
    )
    assert result["copied_checkpoint_source_count"] == len(CHECKPOINT_SOURCE_MODULE_IDS)
    assert result["copied_checkpoint_source_line_count"] == (
        CHECKPOINT_SOURCE_LINE_COUNT
    )
    assert result["checkpoint_lane_source_import"]["status"] == "pass"
    assert result["checkpoint_lane_source_import"]["module_ids"] == (
        CHECKPOINT_SOURCE_MODULE_IDS
    )
    assert result["mission_control_source_import_status"] == (
        MISSION_CONTROL_SOURCE_IMPORT_STATUS
    )
    assert result["copied_mission_control_source_count"] == len(
        MISSION_CONTROL_SOURCE_MODULE_IDS
    )
    assert result["copied_mission_control_source_line_count"] == (
        MISSION_CONTROL_SOURCE_LINE_COUNT
    )
    assert result["mission_control_source_import"]["status"] == "pass"
    assert result["mission_control_source_import"]["module_ids"] == (
        MISSION_CONTROL_SOURCE_MODULE_IDS
    )
    assert all(not Path(path).is_absolute() for path in result["public_runtime_refs"])


def test_mission_transaction_work_spine_imports_task_ledger_control_source_modules(
    tmp_path: Path,
) -> None:
    result = run_mission_transaction_bundle(
        MISSION_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    source_import = result["task_ledger_control_source_import"]
    assert result["status"] == "pass"
    assert source_import["classification"] == "copied_non_secret_macro_body"
    assert source_import["module_count"] == len(TASK_LEDGER_SOURCE_MODULE_IDS)
    assert source_import["module_ids"] == TASK_LEDGER_SOURCE_MODULE_IDS
    assert source_import["source_refs"] == TASK_LEDGER_SOURCE_REFS
    assert source_import["target_refs"] == TASK_LEDGER_SOURCE_TARGET_REFS
    assert source_import["total_line_count"] == TASK_LEDGER_SOURCE_LINE_COUNT
    assert source_import["manifest_summary"]["body_storage_policy"] == (
        "exact_non_secret_macro_bodies_copied_into_bundle_source_modules"
    )
    assert source_import["manifest_summary"]["receipt_body_policy"] == (
        "receipts_may_report_paths_hashes_counts_and_anchor_results_but_not_duplicate_full_source_bodies"
    )
    assert source_import["contract_summary"]["status"] == TASK_LEDGER_SOURCE_IMPORT_STATUS
    assert all(
        not Path(path).is_absolute()
        for path in result["task_ledger_source_public_runtime_refs"]
    )

    modules_by_id = {
        module["module_id"]: module for module in source_import["source_modules"]
    }
    for module_id in TASK_LEDGER_SOURCE_MODULE_IDS:
        module = modules_by_id[module_id]
        assert module["body_copied"] is True
        assert module["body_in_receipt"] is False
        assert module["missing_anchors"] == []
        assert len(module["sha256"]) == 64
        assert module["line_count"] > 0
        assert module["anchor_count"] >= 5


def test_mission_transaction_work_spine_imports_work_ledger_control_source_modules(
    tmp_path: Path,
) -> None:
    result = run_mission_transaction_bundle(
        MISSION_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    source_import = result["work_ledger_control_source_import"]
    assert result["status"] == "pass"
    assert source_import["classification"] == "copied_non_secret_macro_body"
    assert source_import["module_count"] == len(WORK_LEDGER_SOURCE_MODULE_IDS)
    assert source_import["module_ids"] == WORK_LEDGER_SOURCE_MODULE_IDS
    assert source_import["source_refs"] == WORK_LEDGER_SOURCE_REFS
    assert source_import["target_refs"] == WORK_LEDGER_SOURCE_TARGET_REFS
    assert source_import["total_line_count"] == WORK_LEDGER_SOURCE_LINE_COUNT
    assert source_import["manifest_summary"]["body_storage_policy"] == (
        "exact_non_secret_macro_bodies_copied_into_bundle_source_modules"
    )
    assert source_import["manifest_summary"]["receipt_body_policy"] == (
        "receipts_may_report_paths_hashes_counts_and_anchor_results_but_not_duplicate_full_source_bodies"
    )
    assert source_import["contract_summary"]["status"] == WORK_LEDGER_SOURCE_IMPORT_STATUS
    assert all(
        not Path(path).is_absolute()
        for path in result["work_ledger_source_public_runtime_refs"]
    )

    modules_by_id = {
        module["module_id"]: module for module in source_import["source_modules"]
    }
    for module_id in WORK_LEDGER_SOURCE_MODULE_IDS:
        module = modules_by_id[module_id]
        assert module["body_copied"] is True
        assert module["body_in_receipt"] is False
        assert module["missing_anchors"] == []
        assert len(module["sha256"]) == 64
        assert module["line_count"] > 0
        assert module["anchor_count"] >= 5


def test_mission_transaction_work_spine_imports_checkpoint_lane_source_modules(
    tmp_path: Path,
) -> None:
    result = run_mission_transaction_bundle(
        MISSION_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    source_import = result["checkpoint_lane_source_import"]
    assert result["status"] == "pass"
    assert source_import["classification"] == "copied_non_secret_macro_body"
    assert source_import["module_count"] == len(CHECKPOINT_SOURCE_MODULE_IDS)
    assert source_import["module_ids"] == CHECKPOINT_SOURCE_MODULE_IDS
    assert source_import["source_refs"] == CHECKPOINT_SOURCE_REFS
    assert source_import["target_refs"] == CHECKPOINT_SOURCE_TARGET_REFS
    assert source_import["total_line_count"] == CHECKPOINT_SOURCE_LINE_COUNT
    assert source_import["manifest_summary"]["body_storage_policy"] == (
        "exact_non_secret_macro_bodies_copied_into_bundle_source_modules"
    )
    assert source_import["manifest_summary"]["receipt_body_policy"] == (
        "receipts_may_report_paths_hashes_counts_and_anchor_results_but_not_duplicate_full_source_bodies"
    )
    assert source_import["contract_summary"]["status"] == CHECKPOINT_SOURCE_IMPORT_STATUS
    assert all(
        not Path(path).is_absolute()
        for path in result["checkpoint_source_public_runtime_refs"]
    )

    modules_by_id = {
        module["module_id"]: module for module in source_import["source_modules"]
    }
    for module_id in CHECKPOINT_SOURCE_MODULE_IDS:
        module = modules_by_id[module_id]
        assert module["body_copied"] is True
        assert module["body_in_receipt"] is False
        assert module["missing_anchors"] == []
        assert len(module["sha256"]) == 64
        assert module["line_count"] > 0
        assert module["anchor_count"] >= 5


def test_mission_transaction_work_spine_imports_mission_control_source_modules(
    tmp_path: Path,
) -> None:
    result = run_mission_transaction_bundle(
        MISSION_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    source_import = result["mission_control_source_import"]
    assert result["status"] == "pass"
    assert source_import["classification"] == "copied_non_secret_macro_body"
    assert source_import["module_count"] == len(MISSION_CONTROL_SOURCE_MODULE_IDS)
    assert source_import["module_ids"] == MISSION_CONTROL_SOURCE_MODULE_IDS
    assert source_import["source_refs"] == MISSION_CONTROL_SOURCE_REFS
    assert source_import["target_refs"] == MISSION_CONTROL_SOURCE_TARGET_REFS
    assert source_import["total_line_count"] == MISSION_CONTROL_SOURCE_LINE_COUNT
    assert source_import["manifest_summary"]["body_storage_policy"] == (
        "exact_non_secret_macro_bodies_copied_into_bundle_source_modules"
    )
    assert source_import["manifest_summary"]["receipt_body_policy"] == (
        "receipts_may_report_paths_hashes_counts_and_anchor_results_but_not_duplicate_full_source_bodies"
    )
    assert source_import["contract_summary"]["status"] == (
        MISSION_CONTROL_SOURCE_IMPORT_STATUS
    )
    assert all(
        not Path(path).is_absolute()
        for path in result["mission_control_source_public_runtime_refs"]
    )

    modules_by_id = {
        module["module_id"]: module for module in source_import["source_modules"]
    }
    for module_id in MISSION_CONTROL_SOURCE_MODULE_IDS:
        module = modules_by_id[module_id]
        assert module["body_copied"] is True
        assert module["body_in_receipt"] is False
        assert module["missing_anchors"] == []
        assert len(module["sha256"]) == 64
        assert module["line_count"] > 0
        assert module["anchor_count"] >= 6


def test_mission_transaction_work_spine_exported_bundle_receipt_is_public_safe(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/mission_transaction_work_spine",
        public_root / "examples/mission_transaction_work_spine",
    )

    result = run_mission_transaction_bundle(
        public_root
        / "examples/mission_transaction_work_spine/exported_mission_transaction_bundle",
        public_root / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["receipt_paths"] == [EXPORTED_MISSION_TRANSACTION_BUNDLE_RECEIPT_PATH]
    receipt_file = public_root / EXPORTED_MISSION_TRANSACTION_BUNDLE_RECEIPT_PATH
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
    assert payload["input_mode"] == "exported_mission_transaction_bundle"
    assert payload["fixture_regression_required_elsewhere"] is True
    assert "private_state_scan" not in payload
    assert payload["secret_exclusion_scan"]["body_in_receipt"] is False
    assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert payload["body_import_status"] == SOURCE_FAITHFUL_PUBLIC_REFACTOR_STATUS
    assert payload["public_work_landing_status"]["status"] == "pass"
    assert payload["public_mission_transaction_preflight"]["target_ref"] == (
        PUBLIC_MISSION_PREFLIGHT_TARGET_REF
    )
    assert payload["expected_negative_cases"] == {}
    assert payload["public_work_landing_not_live_ledger_authority"] is True
    assert payload["authority_ceiling"]["release_authorized"] is False
    assert payload["authority_ceiling"]["broad_checkpoint_requires_operator_authorization"] is True
    assert payload["checkpoint_lane_decision"]["dirty_tree_blocks_scoped_commit"] is False
    assert payload["task_ledger_control_source_import_status"] == (
        TASK_LEDGER_SOURCE_IMPORT_STATUS
    )
    assert payload["copied_task_ledger_source_count"] == len(TASK_LEDGER_SOURCE_MODULE_IDS)
    assert payload["copied_task_ledger_source_line_count"] == (
        TASK_LEDGER_SOURCE_LINE_COUNT
    )
    assert payload["task_ledger_control_source_import"]["status"] == "pass"
    assert payload["task_ledger_source_contract"]["required_module_ids"] == (
        TASK_LEDGER_SOURCE_MODULE_IDS
    )
    assert payload["work_ledger_control_source_import_status"] == (
        WORK_LEDGER_SOURCE_IMPORT_STATUS
    )
    assert payload["copied_work_ledger_source_count"] == len(WORK_LEDGER_SOURCE_MODULE_IDS)
    assert payload["copied_work_ledger_source_line_count"] == (
        WORK_LEDGER_SOURCE_LINE_COUNT
    )
    assert payload["work_ledger_control_source_import"]["status"] == "pass"
    assert payload["work_ledger_source_contract"]["required_module_ids"] == (
        WORK_LEDGER_SOURCE_MODULE_IDS
    )
    assert payload["checkpoint_lane_source_import_status"] == (
        CHECKPOINT_SOURCE_IMPORT_STATUS
    )
    assert payload["copied_checkpoint_source_count"] == len(CHECKPOINT_SOURCE_MODULE_IDS)
    assert payload["copied_checkpoint_source_line_count"] == (
        CHECKPOINT_SOURCE_LINE_COUNT
    )
    assert payload["checkpoint_lane_source_import"]["status"] == "pass"
    assert payload["checkpoint_source_contract"]["required_module_ids"] == (
        CHECKPOINT_SOURCE_MODULE_IDS
    )
    assert "matched_excerpt" not in _walk_keys(payload)
    assert "body" not in _walk_keys(payload)
    for hit in payload["secret_exclusion_scan"]["hits"]:
        assert hit["body_in_receipt"] is False
        assert not Path(hit["path"]).is_absolute()


def test_mission_transaction_work_spine_receipts_consume_public_work_landing_refactor(
    tmp_path: Path,
) -> None:
    result = run_mission_transaction_bundle(
        MISSION_BUNDLE_INPUT,
        tmp_path / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["secret_exclusion_scan"]["status"] == "pass"
    assert result["body_import_verification"]["target_ref"] == (
        "microcosm-substrate/src/microcosm_core/macro_tools/work_landing.py"
    )
    assert PUBLIC_MISSION_PREFLIGHT_TARGET_REF in result["body_import_verification"][
        "target_refs"
    ]
    assert result["public_work_landing_status"]["landing_lane"] == "scoped_commit"
    assert result["public_mission_transaction_preflight"]["source_ref"] == (
        "tools/meta/control/mission_transaction_preflight.py"
    )
    assert result["public_mission_transaction_preflight"]["body_in_receipt"] is False
    assert (
        "same_path_claim_conflict_blocks_landing"
        in result["public_mission_transaction_preflight"]["source_faithful_decision_rules"]
    )
    assert result["work_landing_reconcile_plan"]["source_ref"] == (
        "tools/meta/control/work_landing.py"
    )
    assert result["work_landing_reconcile_plan"]["body_in_receipt"] is False
    assert result["work_landing_reconcile_plan"]["ordered_controller_action_ids"] == (
        ORDERED_CONTROLLER_ACTION_IDS
    )
    assert result["work_landing_reconcile_plan"]["controller_action_count"] == len(
        SOURCE_FAITHFUL_WORK_LANDING_ACTION_IDS
    )
    assert result["body_import_verification"]["source_faithful_controller_action_count"] == len(
        SOURCE_FAITHFUL_WORK_LANDING_ACTION_IDS
    )
