from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Callable

from microcosm_core.organs.mission_transaction_work_spine import (
    EXPORTED_MISSION_TRANSACTION_BUNDLE_RECEIPT_PATH,
    EXPECTED_NEGATIVE_CASES,
    EXPECTED_RECEIPT_PATHS,
    _file_sha256,
    _file_size_bytes,
    ORDERED_CONTROLLER_ACTION_IDS,
    _line_count,
    _load_jsonl,
    run,
    run_mission_transaction_bundle,
    validate_checkpoint_lane_policy,
    validate_claim_preflight,
)
from microcosm_core.macro_tools.mission_transaction_preflight import (
    build_public_mission_transaction_preflight,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
MISSION_FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/mission_transaction_work_spine/input"
MISSION_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/mission_transaction_work_spine/exported_mission_transaction_bundle"
)
REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME = "real_work_ledger_active_claims_snapshot.json"


def _bundle_line_count(target_refs: list[str]) -> int:
    total = 0
    for target_ref in target_refs:
        rel_ref = target_ref.removeprefix("microcosm-substrate/")
        total += len((MICROCOSM_ROOT / rel_ref).read_text(encoding="utf-8").splitlines())
    return total


def _copy_bundle_input(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/mission_transaction_work_spine",
        public_root / "examples/mission_transaction_work_spine",
    )
    bundle_input = (
        public_root
        / "examples/mission_transaction_work_spine/exported_mission_transaction_bundle"
    )
    return bundle_input


def _copy_fixture_input(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/mission_transaction_work_spine",
        public_root / "fixtures/first_wave/mission_transaction_work_spine",
    )
    return public_root / "fixtures/first_wave/mission_transaction_work_spine/input"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _run_fixture_snapshot_case(
    tmp_path: Path,
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    case_root = tmp_path / name
    case_root.mkdir()
    input_dir = _copy_fixture_input(case_root)
    snapshot_path = input_dir / REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME
    snapshot = _read_json(snapshot_path)
    mutate(snapshot)
    _write_json(snapshot_path, snapshot)
    return run(input_dir, case_root / "receipts", command="pytest")


def _first_runtime_path_claim(snapshot: dict[str, Any]) -> dict[str, Any]:
    for session in snapshot["runtime_status"]["sessions"].values():
        for claim in session.get("claims", []):
            if claim.get("scope_kind") == "path" and claim.get("path"):
                return claim
    raise AssertionError("expected at least one runtime path claim in sanitized snapshot")


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
TASK_LEDGER_SOURCE_LINE_COUNT = _bundle_line_count(TASK_LEDGER_SOURCE_TARGET_REFS)
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
WORK_LEDGER_SOURCE_LINE_COUNT = _bundle_line_count(WORK_LEDGER_SOURCE_TARGET_REFS)
WORK_LEDGER_TOOL_COORDINATION_ANCHORS = [
    "session-status --seed-speed",
    "mutation-check",
]
WORK_LEDGER_RUNTIME_CLAIM_ANCHORS = [
    "ACTIVE_CLAIMS_SNAPSHOT_REL",
    "def build_active_claims_snapshot(",
    "def active_claim_collisions_for_paths(",
    "def load_active_claims_snapshot(",
    "session-status --seed-speed --limit 12",
]
WORK_LEDGER_STANDARD_COORDINATION_ANCHORS = [
    "session-status --seed-speed",
]
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
CHECKPOINT_SOURCE_LINE_COUNT = _bundle_line_count(CHECKPOINT_SOURCE_TARGET_REFS)
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
MISSION_CONTROL_SOURCE_LINE_COUNT = _bundle_line_count(MISSION_CONTROL_SOURCE_TARGET_REFS)
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


def test_mission_transaction_jsonl_loader_streams_without_materializing_file(
    tmp_path: Path, monkeypatch: Any
) -> None:
    jsonl_path = tmp_path / "task_ledger_events.jsonl"
    jsonl_path.write_text(
        '{"id": "event_1"}\n\n["skip", "non-dict"]\n{"id": "event_2"}\n',
        encoding="utf-8",
    )
    original_read_text = Path.read_text

    def fail_for_target(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == jsonl_path:
            raise AssertionError("JSONL loader should stream file rows")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_for_target)

    assert _load_jsonl(jsonl_path) == [{"id": "event_1"}, {"id": "event_2"}]


def test_mission_transaction_line_count_streams_without_materializing_file(
    tmp_path: Path, monkeypatch: Any
) -> None:
    source_path = tmp_path / "source_module.py"
    empty_source_path = tmp_path / "empty_source_module.py"
    source_path.write_text("first\nsecond\nthird", encoding="utf-8")
    empty_source_path.write_text("", encoding="utf-8")
    original_read_text = Path.read_text

    def fail_for_target(self: Path, *args: Any, **kwargs: Any) -> str:
        if self in {source_path, empty_source_path}:
            raise AssertionError("line count should stream file rows")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_for_target)

    assert _line_count(source_path) == 3
    assert _line_count(empty_source_path) == 1


def test_mission_transaction_source_module_metadata_helpers_stream_without_read_bytes(
    tmp_path: Path, monkeypatch: Any
) -> None:
    source_bytes = (b"first line\nsecond line\n" * 128) + b"tail"
    source_path = tmp_path / "source_module.py"
    source_path.write_bytes(source_bytes)
    original_read_bytes = Path.read_bytes

    def fail_for_target(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if self == source_path:
            raise AssertionError("source module metadata helpers should avoid read_bytes")
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", fail_for_target)

    assert _file_sha256(source_path) == hashlib.sha256(source_bytes).hexdigest()
    assert _file_size_bytes(source_path) == len(source_bytes)


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
    assert result["claim_preflight_result"]["conflict_claim_ids"] == []
    assert result["claim_preflight_result"]["same_path_conflict_claim_ids"] == []
    assert result["claim_preflight_result"]["expected_parent_status"] == (
        "parent_ok_or_not_declared"
    )
    assert result["claim_preflight_result"]["stale_expected_parent_claim_ids"] == []
    assert result["claim_preflight_result"]["decision_basis"] == (
        "real_active_claims_snapshot_public_preflight"
    )
    assert result["realness_rank"] == 3
    assert result["realness_rung"] == "R3"
    assert result["realness_state"] == (
        "public_safe_real_work_ledger_session_snapshot_replay"
    )
    realness = result["realness_evidence"]
    assert realness["status"] == "pass"
    assert realness["realness_rank"] == 3
    assert realness["realness_rung"] == "R3"
    assert realness["verdict_rederived_from_runtime_evidence"] is True
    assert realness["expected_labels_used_for_verdict"] is False
    assert realness["baked_fixture_label_sufficient"] is False
    assert realness["session_snapshot_bound"] is True
    assert realness["source_session_claim_count"] == 5
    assert realness["source_session_public_line_fields"] == [
        "current_pass_line",
        "last_pass_result_line",
    ]
    assert realness["source_snapshot_ref"] == "state/work_ledger/active_claims_snapshot.json"
    assert realness["source_snapshot_ref_public_safe"] is True
    assert realness["source_snapshot_hash_bound"] is True
    assert realness["mutated_or_stale_snapshot_rejected"] is True
    assert realness["clear_input_perturbation_moves_verdict"] is True
    assert realness["landing_row_mutation_rejected"] is True
    assert realness["body_in_receipt"] is False
    assert result["claim_preflight_result"]["realness_rank"] == 3
    assert result["claim_preflight_result"]["realness_rung"] == "R3"
    assert result["claim_preflight_result"]["accepted_claim_ids"] == [
        "wlc_65546345964947da",
        "wlc_9039e3dbc8934869",
        "wlc_f66601b816984b71",
        "wlc_fb7e1f4568b3403f",
    ]
    assert result["claim_preflight_result"]["real_same_path_conflict_claim_ids"] == [
        "wlc_real_snapshot_same_path_conflict"
    ]
    assert result["claim_preflight_result"][
        "real_expected_parent_mismatch_claim_ids"
    ] == ["wlc_fb7e1f4568b3403f"]
    assert result["claim_preflight_result"]["real_collision_row_source"] == (
        "work_ledger_runtime.active_claim_collisions_for_paths"
    )
    assert result["claim_preflight_result"]["legacy_regression_fixture_decision"] == (
        "blocked_replan_required"
    )
    assert result["claim_preflight_result"][
        "legacy_regression_fixture_same_path_conflict_claim_ids"
    ] == ["claim_a"]
    assert result["claim_preflight_result"][
        "legacy_regression_fixture_stale_expected_parent_claim_ids"
    ] == ["claim_b"]
    assert result["claim_preflight_result"]["real_active_claims_snapshot_status"] == "pass"
    assert result["claim_preflight_result"]["real_good_input_passed"] is True
    assert result["claim_preflight_result"]["real_wrong_input_rejected"] is True
    assert result["public_mission_transaction_preflight"]["status"] == "pass"
    assert result["public_mission_transaction_preflight"]["landing_decision"]["decision"] == (
        "pass_metadata_preflight"
    )
    assert result["public_mission_transaction_preflight"]["target_ref"] == (
        PUBLIC_MISSION_PREFLIGHT_TARGET_REF
    )
    real_snapshot = result["real_active_claims_snapshot_result"]
    assert real_snapshot["status"] == "pass"
    assert real_snapshot["runtime_snapshot_counts"]["active_claims"] == 5
    assert real_snapshot["runtime_snapshot_counts"]["claim_collisions"] == 0
    assert real_snapshot["source_snapshot_hash_check"]["status"] == "pass"
    assert len(real_snapshot["source_snapshot_hash_check"]["declared_source_snapshot_hash"]) == 64
    assert len(real_snapshot["source_snapshot_hash_check"]["recomputed_runtime_snapshot_hash"]) == 64
    assert real_snapshot["real_good_public_preflight"]["status"] == "pass"
    assert real_snapshot["same_path_conflict_public_preflight"]["status"] == "blocked"
    assert real_snapshot["expected_parent_mismatch_public_preflight"]["status"] == "blocked"
    assert real_snapshot["same_path_conflict_public_preflight"]["claim_row_source"] == (
        "rebuilt_work_ledger_active_claims_snapshot"
    )
    assert real_snapshot["expected_parent_mismatch_public_preflight"]["claim_row_source"] == (
        "rebuilt_work_ledger_active_claims_snapshot"
    )
    assert real_snapshot["disjoint_path_mutation_public_preflight"]["status"] == "pass"
    assert real_snapshot["equal_parent_mutation_public_preflight"]["status"] == "pass"
    assert real_snapshot["landing_row_mutation_public_preflight"]["status"] == "blocked"
    assert real_snapshot["landing_row_mutation_check"]["status"] == "pass"
    assert real_snapshot["landing_row_mutation_check"]["mutated_landing_blockers"] == [
        "checkpoint_lane_violation"
    ]
    assert real_snapshot["runtime_collision_check"]["owner_excluded_collision_count"] == 0
    assert real_snapshot["runtime_collision_check"]["mutated_runtime_collision_count"] == 1
    assert real_snapshot["runtime_collision_check"]["disjoint_runtime_collision_count"] == 0
    assert real_snapshot["runtime_collision_check"]["collision_row_source"] == (
        "work_ledger_runtime.active_claim_collisions_for_paths"
    )
    assert real_snapshot["runtime_collision_check"][
        "mutated_runtime_collision_claim_ids"
    ] == ["wlc_real_snapshot_same_path_conflict"]
    assert real_snapshot["same_path_conflict_public_preflight"][
        "runtime_collision_claim_ids"
    ] == ["wlc_real_snapshot_same_path_conflict"]
    assert real_snapshot["baked_expected_label_policy"]["status"] == "ignored"
    assert real_snapshot["source_runtime_symbols"] == [
        "system.lib.work_ledger_runtime::build_active_claims_snapshot",
        "system.lib.work_ledger_runtime::active_claim_collisions_for_paths",
    ]
    assert real_snapshot["body_in_receipt"] is False
    assert "REAL_ACTIVE_CLAIMS_SNAPSHOT_INVALID" not in result["error_codes"]
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


def test_mission_transaction_work_spine_real_snapshot_status_gates_top_level_pass(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path)
    snapshot_path = input_dir / REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["source_session_id"] = "wrong_public_safe_owner_session"
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(input_dir, tmp_path / "receipts", command="pytest")

    assert result["missing_negative_cases"] == []
    assert result["status"] == "blocked"
    real_snapshot = result["real_active_claims_snapshot_result"]
    assert real_snapshot["status"] == "blocked"
    assert real_snapshot["runtime_collision_check"]["owner_excluded_collision_count"] == 1
    assert result["claim_preflight_result"]["real_good_input_passed"] is True
    assert result["claim_preflight_result"]["real_wrong_input_rejected"] is False


def test_mission_transaction_work_spine_real_snapshot_same_path_pair_flips_to_disjoint(
    tmp_path: Path,
) -> None:
    def force_same_path(snapshot: dict[str, Any]) -> None:
        claim = _first_runtime_path_claim(snapshot)
        snapshot["mutation_cases"]["same_path_conflict"]["path"] = claim["path"]
        snapshot["mutation_cases"]["same_path_conflict"]["scope_id"] = claim["path"]

    conflict_result = _run_fixture_snapshot_case(
        tmp_path,
        "same_path_conflict",
        force_same_path,
    )
    conflict_real = conflict_result["real_active_claims_snapshot_result"]

    assert conflict_result["status"] == "pass"
    assert conflict_real["same_path_conflict_public_preflight"]["status"] == "blocked"
    assert conflict_real["same_path_conflict_public_preflight"][
        "runtime_collision_claim_ids"
    ] == ["wlc_real_snapshot_same_path_conflict"]
    assert conflict_real["runtime_collision_check"][
        "mutated_runtime_collision_count"
    ] == 1
    assert conflict_real["real_wrong_input_rejected"] is True

    def force_disjoint_path(snapshot: dict[str, Any]) -> None:
        snapshot["mutation_cases"]["same_path_conflict"]["path"] = (
            "public_safe_disjoint_mutation/outside_requested_scope.txt"
        )
        snapshot["mutation_cases"]["same_path_conflict"]["scope_id"] = (
            "public_safe_disjoint_mutation/outside_requested_scope.txt"
        )

    cleared_result = _run_fixture_snapshot_case(
        tmp_path,
        "same_path_disjoint",
        force_disjoint_path,
    )
    cleared_real = cleared_result["real_active_claims_snapshot_result"]

    assert cleared_result["status"] == "blocked"
    assert cleared_real["same_path_conflict_public_preflight"]["status"] == "pass"
    assert cleared_real["same_path_conflict_public_preflight"][
        "runtime_collision_claim_ids"
    ] == []
    assert cleared_real["runtime_collision_check"][
        "mutated_runtime_collision_count"
    ] == 0
    assert cleared_real["real_wrong_input_rejected"] is False
    assert "real_work_ledger_same_path_claim_conflict" in cleared_result[
        "missing_negative_cases"
    ]


def test_mission_transaction_work_spine_real_snapshot_parent_verdict_uses_runtime_claim_rows(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path)
    snapshot_path = input_dir / REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["expected_parent_by_claim"] = {}
    snapshot["current_parent_by_claim"] = {}
    target_claim_id = "wlc_fb7e1f4568b3403f"
    target_parent = "49ce09d6e870ba0c88a6a2897f3f2d531c891e29"
    for session in snapshot["runtime_status"]["sessions"].values():
        for claim in session.get("claims", []):
            if claim.get("claim_id") == target_claim_id:
                claim["expected_parent_sha"] = target_parent
                claim["current_parent_sha"] = target_parent
    snapshot["mutation_cases"]["expected_parent_mismatch"] = {
        "claim_id": target_claim_id,
        "mutated_expected_parent_sha": "0000000000000000000000000000000000000000",
    }
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(input_dir, tmp_path / "receipts", command="pytest")

    assert result["status"] == "pass"
    real_snapshot = result["real_active_claims_snapshot_result"]
    assert real_snapshot["expected_parent_mismatch_public_preflight"]["status"] == "blocked"
    assert real_snapshot["expected_parent_mismatch_public_preflight"][
        "stale_expected_parent_claim_ids"
    ] == [target_claim_id]
    assert real_snapshot["equal_parent_mutation_public_preflight"]["status"] == "pass"
    assert real_snapshot["real_wrong_input_rejected"] is True
    assert real_snapshot["real_wrong_input_clear_mutation_passed"] is True


def test_mission_transaction_work_spine_real_snapshot_expected_parent_pair_flips_to_match(
    tmp_path: Path,
) -> None:
    target_claim_id = "wlc_fb7e1f4568b3403f"
    target_parent = "49ce09d6e870ba0c88a6a2897f3f2d531c891e29"

    def add_runtime_parent_rows(snapshot: dict[str, Any]) -> None:
        snapshot["expected_parent_by_claim"] = {}
        snapshot["current_parent_by_claim"] = {}
        for session in snapshot["runtime_status"]["sessions"].values():
            for claim in session.get("claims", []):
                if claim.get("claim_id") == target_claim_id:
                    claim["expected_parent_sha"] = target_parent
                    claim["current_parent_sha"] = target_parent

    def force_stale_parent(snapshot: dict[str, Any]) -> None:
        add_runtime_parent_rows(snapshot)
        snapshot["mutation_cases"]["expected_parent_mismatch"] = {
            "claim_id": target_claim_id,
            "mutated_expected_parent_sha": "0" * 40,
        }

    stale_result = _run_fixture_snapshot_case(
        tmp_path,
        "expected_parent_stale",
        force_stale_parent,
    )
    stale_real = stale_result["real_active_claims_snapshot_result"]

    assert stale_result["status"] == "pass"
    assert stale_real["expected_parent_mismatch_public_preflight"]["status"] == "blocked"
    assert stale_real["expected_parent_mismatch_public_preflight"][
        "stale_expected_parent_claim_ids"
    ] == [target_claim_id]
    assert stale_real["equal_parent_mutation_public_preflight"]["status"] == "pass"
    assert stale_real["real_wrong_input_rejected"] is True
    assert stale_real["real_wrong_input_clear_mutation_passed"] is True

    def force_matching_parent(snapshot: dict[str, Any]) -> None:
        add_runtime_parent_rows(snapshot)
        snapshot["mutation_cases"]["expected_parent_mismatch"] = {
            "claim_id": target_claim_id,
            "mutated_expected_parent_sha": target_parent,
        }

    matched_result = _run_fixture_snapshot_case(
        tmp_path,
        "expected_parent_matched",
        force_matching_parent,
    )
    matched_real = matched_result["real_active_claims_snapshot_result"]

    assert matched_result["status"] == "blocked"
    assert matched_real["expected_parent_mismatch_public_preflight"]["status"] == "pass"
    assert matched_real["expected_parent_mismatch_public_preflight"][
        "stale_expected_parent_claim_ids"
    ] == []
    assert matched_real["real_wrong_input_rejected"] is False
    assert matched_real["real_wrong_input_clear_mutation_passed"] is True
    assert "real_work_ledger_expected_parent_mismatch" in matched_result[
        "missing_negative_cases"
    ]


def test_mission_transaction_work_spine_real_snapshot_ignores_baked_expected_labels(
    tmp_path: Path,
) -> None:
    input_dir = _copy_fixture_input(tmp_path)
    snapshot_path = input_dir / REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot.update(
        {
            "active_claim_count": 999,
            "claim_collision_count": 999,
            "expected_negative_cases": {},
            "expected_verdict": "pass_even_if_not_real",
            "real_active_claims_snapshot_status": "pass",
            "runtime_snapshot_counts": {
                "active_claims": 999,
                "claim_collisions": 999,
            },
            "seed_speed_status": "pass",
        }
    )
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(input_dir, tmp_path / "receipts", command="pytest")

    assert result["status"] == "pass"
    real_snapshot = result["real_active_claims_snapshot_result"]
    assert real_snapshot["runtime_snapshot_counts"]["active_claims"] == 5
    assert real_snapshot["runtime_snapshot_counts"]["claim_collisions"] == 0
    assert real_snapshot["runtime_collision_check"]["mutated_runtime_collision_count"] == 1
    assert real_snapshot["runtime_collision_check"]["disjoint_runtime_collision_count"] == 0
    assert set(real_snapshot["baked_expected_label_policy"]["ignored_input_fields"]) == {
        "active_claim_count",
        "claim_collision_count",
        "expected_negative_cases",
        "expected_verdict",
        "real_active_claims_snapshot_status",
        "runtime_snapshot_counts",
        "seed_speed_status",
    }


def test_mission_transaction_claim_preflight_uses_dynamic_conflict_claim_ids() -> None:
    claims = {
        "claims": [
            {
                "claim_id": "renamed_owner",
                "owned_paths": ["microcosm-substrate/src/microcosm_core/organs/example.py"],
                "status": "active",
                "expected_parent_sha": "abc123",
            },
            {
                "claim_id": "renamed_conflict",
                "owned_paths": ["microcosm-substrate/src/microcosm_core/organs/example.py"],
                "status": "active",
                "expected_parent_sha": "abc123",
            },
        ]
    }
    result = validate_claim_preflight(
        claims,
        {
            "current_parent_by_claim": {
                "renamed_owner": "abc123",
                "renamed_conflict": "abc123",
            }
        },
        {"claim_id": "renamed_missing", "owned_paths": ["declared"]},
    )

    assert result["claim_id"] == "renamed_conflict"
    assert result["decision"] == "blocked_replan_required"
    assert result["same_path_conflict_claim_ids"] == ["renamed_owner"]
    assert result["expected_parent_status"] == "parent_ok_or_not_declared"
    assert result["missing_owned_path_claim_ids"] == []


def test_mission_transaction_checkpoint_lane_rejects_selected_lane_mismatch() -> None:
    result = validate_checkpoint_lane_policy(
        {
            "lane_cases": [
                {
                    "case_id": "authorized_broad_but_selected_scoped",
                    "dirty_tree_present": True,
                    "owned_paths_isolated": False,
                    "broad_checkpoint_requested": True,
                    "operator_authorized_broad_checkpoint": True,
                    "suspected_secret": False,
                    "selected_lane": "scoped_commit",
                }
            ]
        }
    )

    assert result["status"] == "blocked"
    assert result["selected_lane_mismatch_case_ids"] == [
        "authorized_broad_but_selected_scoped"
    ]
    assert "CHECKPOINT_SELECTED_LANE_MISMATCH" in [
        finding["error_code"] for finding in result["findings"]
    ]


def test_public_mission_transaction_preflight_status_tracks_landing_blockers() -> None:
    result = build_public_mission_transaction_preflight(
        subject_ids=["cap_real_claim_status_gate"],
        owned_paths=["microcosm-substrate/src/microcosm_core/organs/example.py"],
        claims_payload={
            "claims": [
                {
                    "claim_id": "claim_real_a",
                    "owned_paths": ["microcosm-substrate/src/microcosm_core/organs/example.py"],
                    "status": "active",
                    "expected_parent_sha": "abc123",
                },
                {
                    "claim_id": "claim_real_b",
                    "owned_paths": ["microcosm-substrate/src/microcosm_core/organs/example.py"],
                    "status": "active",
                    "expected_parent_sha": "abc123",
                },
            ]
        },
        repo_state={
            "current_parent_by_claim": {
                "claim_real_a": "abc123",
                "claim_real_b": "abc123",
            }
        },
        checkpoint_lane_policy={
            "lane_cases": [
                {
                    "case_id": "clean_scoped_commit",
                    "selected_lane": "scoped_commit",
                    "dirty_tree_present": True,
                    "owned_paths_isolated": True,
                    "suspected_secret": False,
                    "dirty_tree_blocks_scoped_lane": False,
                }
            ]
        },
        checkpoint_negative_cases=[],
        require_exclusive=True,
    )

    assert result["checkpoint_lane_status"] == "pass"
    assert result["status"] == "blocked"
    assert result["landing_decision"]["status"] == "blocked"
    assert result["landing_decision"]["blockers"] == ["same_path_claim_conflict"]


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


def test_mission_transaction_work_spine_exported_bundle_consumes_real_work_ledger_runtime(
    tmp_path: Path,
) -> None:
    bundle_input = _copy_bundle_input(tmp_path)
    assert (MISSION_BUNDLE_INPUT / REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME).is_file()

    result = run_mission_transaction_bundle(
        bundle_input,
        tmp_path / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["real_active_claims_snapshot_status"] == "pass"
    assert result["realness_rank"] == 3
    assert result["realness_rung"] == "R3"
    assert result["realness_state"] == (
        "public_safe_real_work_ledger_session_snapshot_replay"
    )
    assert result["claim_preflight_result"]["decision_basis"] == (
        "exported_bundle_real_active_claims_snapshot_public_preflight"
    )
    assert result["claim_preflight_result"]["realness_rank"] == 3
    assert result["claim_preflight_result"]["realness_rung"] == "R3"
    assert result["claim_preflight_result"]["real_good_input_passed"] is True
    assert result["claim_preflight_result"]["real_wrong_input_rejected"] is True
    real_snapshot = result["real_active_claims_snapshot_result"]
    assert real_snapshot["realness_rank"] == 3
    assert real_snapshot["realness_rung"] == "R3"
    assert real_snapshot["realness_evidence"]["session_snapshot_bound"] is True
    assert real_snapshot["realness_evidence"]["source_session_claim_count"] == 5
    assert real_snapshot["realness_evidence"][
        "verdict_rederived_from_runtime_evidence"
    ] is True
    assert real_snapshot["realness_evidence"]["expected_labels_used_for_verdict"] is False
    assert real_snapshot["realness_evidence"]["baked_fixture_label_sufficient"] is False
    assert real_snapshot["realness_evidence"]["source_snapshot_ref_public_safe"] is True
    assert real_snapshot["source_runtime_module_ref"] == (
        "examples/mission_transaction_work_spine/exported_mission_transaction_bundle/"
        "source_modules/system/lib/work_ledger_runtime.py"
    )
    assert real_snapshot["runtime_snapshot_counts"]["active_claims"] == 5
    assert real_snapshot["runtime_collision_check"]["owner_excluded_collision_count"] == 0
    assert real_snapshot["runtime_collision_check"]["mutated_runtime_collision_count"] == 1
    assert real_snapshot["source_snapshot_hash_check"]["status"] == "pass"
    assert result["public_mission_transaction_preflight"]["status"] == "pass"


def test_mission_transaction_work_spine_exported_bundle_requires_real_work_ledger_snapshot(
    tmp_path: Path,
) -> None:
    bundle_input = _copy_bundle_input(tmp_path)
    (bundle_input / REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME).unlink()

    result = run_mission_transaction_bundle(
        bundle_input,
        tmp_path / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["real_active_claims_snapshot_status"] == "missing"
    assert "REAL_ACTIVE_CLAIMS_SNAPSHOT_MISSING" in result["error_codes"]


def test_mission_transaction_work_spine_exported_bundle_rejects_mutated_real_runtime_rows(
    tmp_path: Path,
) -> None:
    bundle_input = _copy_bundle_input(tmp_path)
    snapshot_path = bundle_input / REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    source_claim = _first_runtime_path_claim(snapshot)
    signal_at = "2026-06-04T10:26:30+00:00"
    mutated_claim = {
        **source_claim,
        "claim_id": "wlc_public_safe_intruder_same_path",
        "session_id": "public_safe_intruder_session",
        "claimed_at": signal_at,
        "leased_until": "2026-06-04T11:10:38.504743+00:00",
        "released_at": None,
        "expired_at": None,
        "note": "public_safe_same_path_intruder_mutation",
    }
    snapshot["runtime_status"]["sessions"]["public_safe_intruder_session"] = {
        "session_id": "public_safe_intruder_session",
        "actor": "public_safe_intruder",
        "phase_id": "09_54_1",
        "family_id": "09",
        "bootstrapped_at": signal_at,
        "last_activity_at": signal_at,
        "last_activity_action": "session-heartbeat",
        "touched_work": True,
        "ended_at": None,
        "pass_heartbeat": {
            "schema": "runtime_pass_heartbeat_v0",
            "session_id": "public_safe_intruder_session",
            "actor": "public_safe_intruder",
            "phase_id": "09_54_1",
            "family_id": "09",
            "pass_id": "wlp_public_safe_intruder",
            "pass_seq": 1,
            "pass_state": "editing",
            "current_pass_line": "Public-safe same-path intruder mutation.",
            "last_pass_result_line": "Clean runtime snapshot passed before mutation.",
            "scope_refs": [{"kind": "ref", "ref": source_claim["path"]}],
            "updated_at": signal_at,
            "expires_at": "2026-06-04T14:26:30+00:00",
            "current_pass_updated_at": signal_at,
            "last_pass_completed_at": signal_at,
            "source": "manual_cli",
        },
        "claims": [mutated_claim],
    }
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_mission_transaction_bundle(
        bundle_input,
        tmp_path / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["real_active_claims_snapshot_status"] == "blocked"
    assert result["claim_preflight_result"]["decision_basis"] == (
        "exported_bundle_real_active_claims_snapshot_public_preflight"
    )
    assert result["claim_preflight_result"]["real_good_input_passed"] is False
    assert result["public_mission_transaction_preflight"]["status"] == "blocked"
    assert (
        result["real_active_claims_snapshot_result"]["runtime_collision_check"][
            "owner_excluded_collision_count"
        ]
        == 1
    )


def test_mission_transaction_work_spine_exported_bundle_rejects_mutated_snapshot_hash(
    tmp_path: Path,
) -> None:
    bundle_input = _copy_bundle_input(tmp_path)
    snapshot_path = bundle_input / REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["source_snapshot_hash"] = "0" * 64
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_mission_transaction_bundle(
        bundle_input,
        tmp_path / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["real_active_claims_snapshot_status"] == "blocked"
    assert "REAL_ACTIVE_CLAIMS_SNAPSHOT_HASH_MISMATCH" in result["error_codes"]
    real_snapshot = result["real_active_claims_snapshot_result"]
    assert real_snapshot["source_snapshot_hash_check"]["status"] == "blocked"
    assert real_snapshot["source_snapshot_hash_check"][
        "declared_source_snapshot_hash"
    ] == "0" * 64
    assert real_snapshot["source_snapshot_hash_check"][
        "recomputed_runtime_snapshot_hash"
    ] != "0" * 64
    assert {
        finding["error_code"]: finding["subject_kind"]
        for finding in result["findings"]
    }["REAL_ACTIVE_CLAIMS_SNAPSHOT_HASH_MISMATCH"] == (
        "real_work_ledger_snapshot_fixture"
    )


def test_mission_transaction_work_spine_exported_bundle_rejects_stale_valid_snapshot_hash(
    tmp_path: Path,
) -> None:
    bundle_input = _copy_bundle_input(tmp_path)
    snapshot_path = bundle_input / REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["source_snapshot_hash"] = "1" * 64
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_mission_transaction_bundle(
        bundle_input,
        tmp_path / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["real_active_claims_snapshot_status"] == "blocked"
    assert "REAL_ACTIVE_CLAIMS_SNAPSHOT_HASH_MISMATCH" in result["error_codes"]
    real_snapshot = result["real_active_claims_snapshot_result"]
    assert real_snapshot["source_snapshot_hash_check"]["status"] == "blocked"
    assert real_snapshot["source_snapshot_hash_check"][
        "declared_source_snapshot_hash"
    ] == "1" * 64
    assert real_snapshot["source_snapshot_hash_check"][
        "recomputed_runtime_snapshot_hash"
    ] != "1" * 64


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

    runtime_module = modules_by_id["work_ledger_runtime_body_import"]
    assert runtime_module["anchor_count"] >= 11
    runtime_manifest = json.loads(
        (
            MISSION_BUNDLE_INPUT / "work_ledger_source_module_manifest.json"
        ).read_text(encoding="utf-8")
    )
    runtime_row = next(
        row
        for row in runtime_manifest["modules"]
        if row["module_id"] == "work_ledger_runtime_body_import"
    )
    for anchor in WORK_LEDGER_RUNTIME_CLAIM_ANCHORS:
        assert anchor in runtime_row["required_anchors"]
    tool_row = next(
        row
        for row in runtime_manifest["modules"]
        if row["module_id"] == "work_ledger_tool_body_import"
    )
    for anchor in WORK_LEDGER_TOOL_COORDINATION_ANCHORS:
        assert anchor in tool_row["required_anchors"]
    standard_row = next(
        row
        for row in runtime_manifest["modules"]
        if row["module_id"] == "work_ledger_standard_body_import"
    )
    for anchor in WORK_LEDGER_STANDARD_COORDINATION_ANCHORS:
        assert anchor in standard_row["required_anchors"]


def test_mission_transaction_work_spine_blocks_missing_work_ledger_seed_speed_manifest_anchor(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle_input = (
        public_root
        / "examples/mission_transaction_work_spine/exported_mission_transaction_bundle"
    )
    shutil.copytree(MISSION_BUNDLE_INPUT, bundle_input)
    manifest_path = bundle_input / "work_ledger_source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in manifest["modules"]:
        if row["module_id"] == "work_ledger_tool_body_import":
            row["required_anchors"] = [
                anchor
                for anchor in row["required_anchors"]
                if anchor != "session-status --seed-speed"
            ]
            row["anchor_count"] = len(row["required_anchors"])
            break
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_mission_transaction_bundle(
        bundle_input,
        tmp_path / "receipts/first_wave/mission_transaction_work_spine",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert "WORK_LEDGER_SOURCE_MANIFEST_ANCHORS_MISMATCH" in result["error_codes"]
    assert result["authority_ceiling"]["live_work_ledger_mutation_authorized"] is False


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
    action_rows = result["work_landing_reconcile_plan"]["actions"]
    assert [row["sequence"] for row in action_rows] == list(
        range(1, len(ORDERED_CONTROLLER_ACTION_IDS) + 1)
    )
    action_by_id = {row["action_id"]: row for row in action_rows}
    for row in action_rows:
        assert row["mutation_authorized"] is False
        assert row["live_state_mutation_authorized"] is False
        assert all(
            action_by_id[prerequisite]["sequence"] < row["sequence"]
            for prerequisite in row["prerequisite_action_ids"]
        )
    assert action_by_id["release_claims"]["prerequisite_action_ids"] == [
        "finalize_work_ledger_session"
    ]
    assert action_by_id["release_claims"]["order_guard"] == (
        "claim_release_after_work_ledger_session_finalize_only"
    )
    assert action_by_id["recompute_convergence"]["prerequisite_action_ids"] == [
        "release_claims"
    ]
    assert result["body_import_verification"]["source_faithful_controller_action_count"] == len(
        SOURCE_FAITHFUL_WORK_LANDING_ACTION_IDS
    )
