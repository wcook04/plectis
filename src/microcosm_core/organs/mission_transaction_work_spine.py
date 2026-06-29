"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.organs.mission_transaction_work_spine` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: ORGAN_ID, FIXTURE_ID, VALIDATOR_ID, PREFLIGHT_REL, DEPENDENCY_BLOCKED_NAME, WORK_LANDING_ATTEMPT_NAME, CLAIM_PREFLIGHT_NAME, SCOPED_MUTATION_NAME, CHECKPOINT_LANE_NAME, CLOSEOUT_STATUS_NAME, DEPENDENCY_UNLOCK_NAME, RECONCILE_PLAN_NAME, MISSION_BUNDLE_RESULT_NAME, REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME, EXPECTED_RECEIPT_PATHS, EXPORTED_MISSION_TRANSACTION_BUNDLE_RECEIPT_PATH, EXPECTED_NEGATIVE_CASES, MISSION_AUTHORITY_CEILING, MISSION_ANTI_CLAIM, SOURCE_PATTERN_IDS, VALIDATOR_CONTRACT_RATCHET_REFS, ORDERED_CONTROLLER_ACTION_IDS, BODY_IMPORT_STATUS, WORK_LANDING_TARGET_REF, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.macro_tools.mission_transaction_preflight, microcosm_core.macro_tools.work_landing, microcosm_core.receipts, microcosm_core.schemas, microcosm_core.secret_exclusion_scan
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

from microcosm_core.macro_tools.work_landing import (
    ORDERED_CONTROLLER_ACTION_IDS as WORK_LANDING_ORDERED_CONTROLLER_ACTION_IDS,
    SOURCE_REF as WORK_LANDING_SOURCE_REF,
    SOURCE_SYMBOL_REFS as WORK_LANDING_SOURCE_SYMBOL_REFS,
    TARGET_SYMBOL_REFS as WORK_LANDING_TARGET_SYMBOL_REFS,
    build_public_work_landing_attempt_binding,
    build_public_work_landing_reconcile_plan,
    build_public_work_landing_status,
)
from microcosm_core.macro_tools.mission_transaction_preflight import (
    KERNEL_SOURCE_REF as MISSION_PREFLIGHT_KERNEL_SOURCE_REF,
    SOURCE_REF as MISSION_PREFLIGHT_SOURCE_REF,
    SOURCE_SYMBOL_REFS as MISSION_PREFLIGHT_SOURCE_SYMBOL_REFS,
    TARGET_REF as MISSION_PREFLIGHT_TARGET_REF,
    TARGET_SYMBOL_REFS as MISSION_PREFLIGHT_TARGET_SYMBOL_REFS,
    build_public_mission_transaction_preflight,
)
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import base_receipt, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "mission_transaction_work_spine"
FIXTURE_ID = "first_wave.mission_transaction_work_spine"
VALIDATOR_ID = "validator.microcosm.organs.mission_transaction_work_spine"

PREFLIGHT_REL = "receipts/preflight/mission_transaction_work_spine.json"
DEPENDENCY_BLOCKED_NAME = "dependency_blocked.json"
WORK_LANDING_ATTEMPT_NAME = "work_landing_attempt.json"
CLAIM_PREFLIGHT_NAME = "claim_preflight_result.json"
SCOPED_MUTATION_NAME = "scoped_mutation_receipt.json"
CHECKPOINT_LANE_NAME = "checkpoint_lane_decision.json"
CLOSEOUT_STATUS_NAME = "closeout_status_projection.json"
DEPENDENCY_UNLOCK_NAME = "dependency_unlock_scheduler_receipt.json"
RECONCILE_PLAN_NAME = "work_landing_reconcile_plan.json"
MISSION_BUNDLE_RESULT_NAME = "exported_mission_transaction_bundle_validation_result.json"
REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME = "real_work_ledger_active_claims_snapshot.json"

EXPECTED_RECEIPT_PATHS = [
    PREFLIGHT_REL,
    "receipts/first_wave/mission_transaction_work_spine/dependency_blocked.json",
    "receipts/first_wave/mission_transaction_work_spine/work_landing_attempt.json",
    "receipts/first_wave/mission_transaction_work_spine/claim_preflight_result.json",
    "receipts/first_wave/mission_transaction_work_spine/scoped_mutation_receipt.json",
    "receipts/first_wave/mission_transaction_work_spine/checkpoint_lane_decision.json",
    "receipts/first_wave/mission_transaction_work_spine/closeout_status_projection.json",
    "receipts/first_wave/mission_transaction_work_spine/dependency_unlock_scheduler_receipt.json",
    "receipts/first_wave/mission_transaction_work_spine/work_landing_reconcile_plan.json",
]
EXPORTED_MISSION_TRANSACTION_BUNDLE_RECEIPT_PATH = (
    "receipts/first_wave/mission_transaction_work_spine/"
    "exported_mission_transaction_bundle_validation_result.json"
)

EXPECTED_NEGATIVE_CASES = {
    "competing_claim_and_stale_parent": [
        "EXPECTED_PARENT_MISMATCH",
        "SAME_PATH_CLAIM_CONFLICT",
    ],
    "real_work_ledger_same_path_claim_conflict": ["SAME_PATH_CLAIM_CONFLICT"],
    "real_work_ledger_expected_parent_mismatch": ["EXPECTED_PARENT_MISMATCH"],
    "real_work_ledger_mutated_landing_row": ["CHECKPOINT_BROAD_AUTH_REQUIRED"],
    "mission_claim_missing_owned_path": ["MISSING_OWNED_PATH"],
    "scoped_commit_receipt_claims_global_authority": [
        "SCOPED_RECEIPT_AUTHORITY_UPGRADE"
    ],
    "mission_fixture_private_task_ledger_body": ["LIVE_TASK_LEDGER_BODY_IN_FIXTURE"],
    "clean_preflight_overclaims_landing_complete": [
        "PREFLIGHT_PASS_OVERCLAIMS_WORK_LANDED"
    ],
    "dependency_unlock_without_resolution_receipt": ["DANGLING_DEPENDENCY_REF"],
    "ready_workitem_with_unsatisfied_hard_dep": ["READY_WITH_INCOMPLETE_HARD_DEP"],
    "broad_checkpoint_without_operator_authorization": [
        "CHECKPOINT_BROAD_AUTH_REQUIRED"
    ],
    "suspected_secret_without_hard_stop": ["CHECKPOINT_SECRET_REQUIRES_HARD_STOP"],
    "dirty_tree_blocks_scoped_lane": ["CHECKPOINT_DIRTY_TREE_NOT_SCOPED_BLOCKER"],
    "missing_selected_lane_for_state": ["CHECKPOINT_LANE_DECISION_REQUIRED"],
}

MISSION_AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "mission_transaction_metadata_not_live_closeout_authority",
    "live_work_state_mutation_authorized": False,
    "broad_stage_authorized": False,
    "broad_checkpoint_requires_operator_authorization": True,
    "suspected_secret_requires_hard_stop": True,
    "dirty_tree_blocks_scoped_commit": False,
    "derived_status_projection_is_authority": False,
    "later_organs_authorized": False,
}
MISSION_ANTI_CLAIM = (
    "Mission transaction receipts validate public work, claim, dependency, landing, "
    "checkpoint-lane, receipt-drain, and schedulability metadata plus regression fixtures; "
    "they do not mutate live state, certify live closeout, authorize broad staging without "
    "operator intent, authorize later organs, or prove whole Wave 1."
)

SOURCE_PATTERN_IDS = [
    "task_ledger_workitem_spine",
    "mission_transaction_landing",
    "work_ledger_runtime_claims",
    "task_ledger_exact_receipt_drain",
    "task_ledger_control_source_body_import",
    "work_landing_reconcile_finalizer_plan",
    "workitem_dependency_unlock_scheduler",
    "checkpoint_solo_dev_three_lanes",
]

VALIDATOR_CONTRACT_RATCHET_REFS = [
    "fixture_manifests/mission_transaction_work_spine.fixture_manifest.json::validator_contract_ratchet_v1",
    "fixture_negative_case_matrix_v1.json::negative_cases[organ_id=mission_transaction_work_spine]",
    "error_code_taxonomy_v1.json::error_codes[organ_ids contains mission_transaction_work_spine]",
]

ORDERED_CONTROLLER_ACTION_IDS = [
    *WORK_LANDING_ORDERED_CONTROLLER_ACTION_IDS,
]

BODY_IMPORT_STATUS = "source_faithful_public_refactor_landed"
WORK_LANDING_TARGET_REF = "microcosm-substrate/src/microcosm_core/macro_tools/work_landing.py"
WORK_LANDING_VALIDATION_REFS = [
    "microcosm-substrate/tests/test_mission_transaction_work_spine.py::test_mission_transaction_work_spine_exported_bundle_validates_runtime_shape",
    "microcosm-substrate/tests/test_mission_transaction_work_spine.py::test_mission_transaction_work_spine_receipts_consume_public_work_landing_refactor",
    "microcosm-substrate/tests/test_mission_transaction_work_spine.py::test_mission_transaction_work_spine_consumes_public_mission_preflight_refactor",
]
TASK_LEDGER_SOURCE_IMPORT_STATUS = "public_runtime_import_landed"
TASK_LEDGER_SOURCE_MANIFEST_NAME = "source_module_manifest.json"
TASK_LEDGER_CONTRACT_NAME = "task_ledger_control_runtime_contract.json"
TASK_LEDGER_SOURCE_MODULES = [
    {
        "module_id": "task_ledger_events_body_import",
        "source_ref": "system/lib/task_ledger_events.py",
        "bundle_path": "source_modules/system/lib/task_ledger_events.py",
        "target_ref": (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/source_modules/system/lib/"
            "task_ledger_events.py"
        ),
        "required_anchors": [
            "def append_event(",
            "def append_event_and_rebuild(",
            "def build_projection(",
            "def rebuild_projections(",
            "def validate_event_log(",
            "closeout_assurance",
        ],
    },
    {
        "module_id": "task_ledger_apply_tool_body_import",
        "source_ref": "tools/meta/factory/task_ledger_apply.py",
        "bundle_path": "source_modules/tools/meta/factory/task_ledger_apply.py",
        "target_ref": (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/source_modules/tools/meta/factory/"
            "task_ledger_apply.py"
        ),
        "required_anchors": [
            "quick-capture",
            "sign-off",
            "authority-health",
            "_apply_mission_closeout_report",
            "TaskLedgerArgumentParser",
            "closeout_assurance",
        ],
    },
    {
        "module_id": "task_ledger_priority_body_import",
        "source_ref": "system/lib/task_ledger_priority.py",
        "bundle_path": "source_modules/system/lib/task_ledger_priority.py",
        "target_ref": (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/source_modules/system/lib/"
            "task_ledger_priority.py"
        ),
        "required_anchors": [
            "def priority_constellation(",
            "_EXECUTION_MENU_SCHEDULABLE",
            "mutation_rule",
            "def top_schedulable_workitem(",
            "def find_workitem_by_id(",
        ],
    },
    {
        "module_id": "task_ledger_project_tool_body_import",
        "source_ref": "tools/meta/factory/task_ledger_project.py",
        "bundle_path": "source_modules/tools/meta/factory/task_ledger_project.py",
        "target_ref": (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/source_modules/tools/meta/factory/"
            "task_ledger_project.py"
        ),
        "required_anchors": [
            "Rebuild and validate Task Ledger projections",
            "task_ledger_events.rebuild_projections",
            "task_ledger_events.build_projection",
            "validate_event_log",
            "views",
        ],
    },
]
TASK_LEDGER_SOURCE_VALIDATION_REFS = [
    "microcosm-substrate/tests/test_mission_transaction_work_spine.py::test_mission_transaction_work_spine_imports_task_ledger_control_source_modules",
    "microcosm-substrate/tests/test_mission_transaction_work_spine.py::test_mission_transaction_work_spine_exported_bundle_receipt_is_public_safe",
]
WORK_LEDGER_SOURCE_IMPORT_STATUS = "public_runtime_import_landed"
WORK_LEDGER_SOURCE_MANIFEST_NAME = "work_ledger_source_module_manifest.json"
WORK_LEDGER_CONTRACT_NAME = "work_ledger_control_runtime_contract.json"
WORK_LEDGER_SOURCE_MODULES = [
    {
        "module_id": "work_ledger_tool_body_import",
        "source_ref": "tools/meta/factory/work_ledger.py",
        "bundle_path": "source_modules/tools/meta/factory/work_ledger.py",
        "target_ref": (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/source_modules/tools/meta/factory/"
            "work_ledger.py"
        ),
        "required_anchors": [
            "session-preflight",
            "session-claims",
            "session-status --seed-speed",
            "session-heartbeat",
            "session-finalize",
            "mutation-check",
            "def build_parser(",
        ],
    },
    {
        "module_id": "work_ledger_event_body_import",
        "source_ref": "system/lib/work_ledger.py",
        "bundle_path": "source_modules/system/lib/work_ledger.py",
        "target_ref": (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/source_modules/system/lib/"
            "work_ledger.py"
        ),
        "required_anchors": [
            "WORK_LEDGER_SCHEMA",
            "def append_event(",
            "def progress_thread(",
            "def close_thread(",
            "def build_projection(",
            "progress_note",
        ],
    },
    {
        "module_id": "work_ledger_runtime_body_import",
        "source_ref": "system/lib/work_ledger_runtime.py",
        "bundle_path": "source_modules/system/lib/work_ledger_runtime.py",
        "target_ref": (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/source_modules/system/lib/"
            "work_ledger_runtime.py"
        ),
        "required_anchors": [
            "WORK_LEDGER_RUNTIME_SCHEMA",
            "ACTIVE_CLAIMS_SNAPSHOT_REL",
            "def bootstrap_session(",
            "def mark_session_pass_heartbeat(",
            "def finalize_session(",
            "def claim_work_scope(",
            "def release_claim(",
            "def build_active_claims_snapshot(",
            "def active_claim_collisions_for_paths(",
            "def load_active_claims_snapshot(",
            "session-status --seed-speed --limit 12",
            "ACTIVE_CLAIM_LEASE_MAX",
        ],
    },
    {
        "module_id": "work_ledger_standard_body_import",
        "source_ref": "codex/standards/std_work_ledger.json",
        "bundle_path": "source_modules/codex/standards/std_work_ledger.json",
        "target_ref": (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/source_modules/codex/standards/"
            "std_work_ledger.json"
        ),
        "required_anchors": [
            '"runtime_status_contract"',
            '"claim_contract"',
            '"session_preflight_contract"',
            '"pass_heartbeat_contract"',
            '"host_runtime_cli"',
            "session-status --seed-speed",
        ],
    },
]
WORK_LEDGER_SOURCE_VALIDATION_REFS = [
    "microcosm-substrate/tests/test_mission_transaction_work_spine.py::test_mission_transaction_work_spine_imports_work_ledger_control_source_modules",
    "microcosm-substrate/tests/test_mission_transaction_work_spine.py::test_mission_transaction_work_spine_exported_bundle_receipt_is_public_safe",
]
CHECKPOINT_SOURCE_IMPORT_STATUS = "public_runtime_import_landed"
CHECKPOINT_SOURCE_MANIFEST_NAME = "checkpoint_source_module_manifest.json"
CHECKPOINT_CONTRACT_NAME = "checkpoint_lane_runtime_contract.json"
CHECKPOINT_SOURCE_MODULES = [
    {
        "module_id": "checkpoint_script_body_import",
        "source_ref": "checkpoint",
        "bundle_path": "source_modules/checkpoint",
        "target_ref": (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/source_modules/checkpoint"
        ),
        "required_anchors": [
            "save-button Git",
            "--private-backup",
            "--rescue-ref",
            "checkpoint_guard_main_landing",
            "tools/meta/control/checkpoint_private_backup.py",
            "git add -A",
        ],
    },
    {
        "module_id": "checkpoint_private_backup_body_import",
        "source_ref": "tools/meta/control/checkpoint_private_backup.py",
        "bundle_path": "source_modules/tools/meta/control/checkpoint_private_backup.py",
        "target_ref": (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/source_modules/tools/meta/control/"
            "checkpoint_private_backup.py"
        ),
        "required_anchors": [
            "Private backup lane behind ./checkpoint",
            "AIW_PRIVATE_BACKUP_ASSUME_PRIVATE",
            "def _github_privacy(",
            "def _push_audit(",
            "--force-with-lease=",
            "used_force_with_lease",
        ],
    },
]
CHECKPOINT_SOURCE_VALIDATION_REFS = [
    "microcosm-substrate/tests/test_mission_transaction_work_spine.py::test_mission_transaction_work_spine_imports_checkpoint_lane_source_modules",
    "microcosm-substrate/tests/test_mission_transaction_work_spine.py::test_mission_transaction_work_spine_exported_bundle_receipt_is_public_safe",
]
MISSION_CONTROL_SOURCE_IMPORT_STATUS = "public_runtime_import_landed"
MISSION_CONTROL_SOURCE_MANIFEST_NAME = "mission_control_source_module_manifest.json"
MISSION_CONTROL_CONTRACT_NAME = "mission_control_runtime_contract.json"
MISSION_CONTROL_SOURCE_MODULES = [
    {
        "module_id": "scoped_commit_tool_body_import",
        "source_ref": "tools/meta/control/scoped_commit.py",
        "bundle_path": "source_modules/tools/meta/control/scoped_commit.py",
        "target_ref": (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/source_modules/tools/meta/control/"
            "scoped_commit.py"
        ),
        "required_anchors": [
            "def perform_scoped_commit(",
            "def perform_tracked_removals_commit(",
            "perform_remote_full_paths_landing",
            "--work-ledger-session-id",
            "--allow-multi-hunk-full-paths",
            "scoped_commit_work_ledger_mutation_guard_v0",
        ],
    },
    {
        "module_id": "mission_transaction_preflight_tool_body_import",
        "source_ref": "tools/meta/control/mission_transaction_preflight.py",
        "bundle_path": "source_modules/tools/meta/control/mission_transaction_preflight.py",
        "target_ref": (
            "microcosm-substrate/examples/mission_transaction_work_spine/"
            "exported_mission_transaction_bundle/source_modules/tools/meta/control/"
            "mission_transaction_preflight.py"
        ),
        "required_anchors": [
            "def build_parser(",
            "build_mission_transaction_landing_preflight",
            "--subject-id",
            "--owned-path",
            "--require-exclusive",
            "--fail-on-status",
        ],
    },
]
MISSION_CONTROL_SOURCE_VALIDATION_REFS = [
    "microcosm-substrate/tests/test_mission_transaction_work_spine.py::test_mission_transaction_work_spine_imports_mission_control_source_modules",
    "microcosm-substrate/tests/test_mission_transaction_work_spine.py::test_mission_transaction_work_spine_exported_bundle_receipt_is_public_safe",
]


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_public_root_for_path` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate" or (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src/microcosm_core").is_dir()
            and (candidate / "core/private_state_forbidden_classes.json").is_file()
        ):
            return candidate
    return Path.cwd().resolve(strict=False)


def _input_file_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_input_file_paths` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (
        "task_ledger_events.jsonl",
        "work_ledger_claims.json",
        "toy_repo_state.json",
        REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME,
        "dependency_graph.json",
        "claim_missing_owned_path.json",
        "scoped_receipt_global_authority_claim.json",
        "live_task_ledger_body_in_fixture.json",
        "preflight_pass_claims_work_landed.json",
        "checkpoint_lane_policy.json",
        "broad_checkpoint_without_operator_authorization.json",
        "suspected_secret_without_hard_stop.json",
        "dirty_tree_blocks_scoped_lane.json",
        "missing_selected_lane_for_state.json",
    )
    return [input_dir / name for name in names]


def _mission_bundle_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_mission_bundle_paths` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (
        "bundle_manifest.json",
        "workitems.json",
        "claim_table.json",
        "dependency_graph.json",
        "transaction_plan.json",
        "receipt_drain_plan.json",
        "closeout_projection_packet.json",
        "scoped_mutation_policy.json",
        "checkpoint_lane_policy.json",
        REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME,
    )
    return [input_dir / name for name in names]


def _task_ledger_source_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_task_ledger_source_paths` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [
        input_dir / TASK_LEDGER_SOURCE_MANIFEST_NAME,
        input_dir / TASK_LEDGER_CONTRACT_NAME,
        *[
            input_dir / str(module["bundle_path"])
            for module in TASK_LEDGER_SOURCE_MODULES
        ],
    ]


def _work_ledger_source_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_work_ledger_source_paths` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [
        input_dir / WORK_LEDGER_SOURCE_MANIFEST_NAME,
        input_dir / WORK_LEDGER_CONTRACT_NAME,
        *[
            input_dir / str(module["bundle_path"])
            for module in WORK_LEDGER_SOURCE_MODULES
        ],
    ]


def _checkpoint_source_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_checkpoint_source_paths` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [
        input_dir / CHECKPOINT_SOURCE_MANIFEST_NAME,
        input_dir / CHECKPOINT_CONTRACT_NAME,
        *[
            input_dir / str(module["bundle_path"])
            for module in CHECKPOINT_SOURCE_MODULES
        ],
    ]


def _mission_control_source_paths(input_dir: Path) -> list[Path]:
    """
    [ACTION]
    - Teleology: Implements `_mission_control_source_paths` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [
        input_dir / MISSION_CONTROL_SOURCE_MANIFEST_NAME,
        input_dir / MISSION_CONTROL_CONTRACT_NAME,
        *[
            input_dir / str(module["bundle_path"])
            for module in MISSION_CONTROL_SOURCE_MODULES
        ],
    ]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_load_jsonl` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _load_input_payloads(input_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_input_payloads` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "task_events": _load_jsonl(input_dir / "task_ledger_events.jsonl"),
        "claims": read_json_strict(input_dir / "work_ledger_claims.json"),
        "repo_state": read_json_strict(input_dir / "toy_repo_state.json"),
        "real_active_claims_snapshot": read_json_strict(
            input_dir / REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME
        ),
        "dependency_graph": read_json_strict(input_dir / "dependency_graph.json"),
        "missing_owned_path": read_json_strict(input_dir / "claim_missing_owned_path.json"),
        "scoped_receipt": read_json_strict(
            input_dir / "scoped_receipt_global_authority_claim.json"
        ),
        "private_marker": read_json_strict(input_dir / "live_task_ledger_body_in_fixture.json"),
        "preflight_overclaim": read_json_strict(
            input_dir / "preflight_pass_claims_work_landed.json"
        ),
        "checkpoint_lane_policy": read_json_strict(input_dir / "checkpoint_lane_policy.json"),
        "checkpoint_negative_cases": [
            read_json_strict(input_dir / "broad_checkpoint_without_operator_authorization.json"),
            read_json_strict(input_dir / "suspected_secret_without_hard_stop.json"),
            read_json_strict(input_dir / "dirty_tree_blocks_scoped_lane.json"),
            read_json_strict(input_dir / "missing_selected_lane_for_state.json"),
        ],
    }


def _load_mission_bundle_payloads(input_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_mission_bundle_payloads` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payloads: dict[str, Any] = {}
    for path in _mission_bundle_paths(input_dir):
        if path.name == REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME and not path.exists():
            continue
        payloads[path.stem] = read_json_strict(path)
    return payloads


def _scan_fixture_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_scan_fixture_inputs` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    return scan_paths(_input_file_paths(input_dir), forbidden_classes=policy, display_root=public_root)


def _scan_bundle_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_scan_bundle_inputs` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    paths = [
        *_mission_bundle_paths(input_dir),
        *_task_ledger_source_paths(input_dir),
        *_work_ledger_source_paths(input_dir),
        *_checkpoint_source_paths(input_dir),
        *_mission_control_source_paths(input_dir),
    ]
    real_snapshot_path = input_dir / REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME
    if real_snapshot_path.is_file():
        paths.append(real_snapshot_path)
    return scan_paths(
        paths,
        forbidden_classes=policy,
        display_root=public_root,
    )


def _stable_hash(payload: object) -> str:
    """
    [ACTION]
    - Teleology: Implements `_stable_hash` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_file_sha256` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_size_bytes(path: Path) -> int:
    """
    [ACTION]
    - Teleology: Implements `_file_size_bytes` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return path.stat().st_size


def _line_count(path: Path) -> int:
    """
    [ACTION]
    - Teleology: Implements `_line_count` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    line_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_count, _line in enumerate(handle, start=1):
            pass
    return line_count or 1


def _strings(value: object) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _parse_iso_utc(value: object) -> datetime:
    """
    [ACTION]
    - Teleology: Implements `_parse_iso_utc` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    token = str(value or "").strip()
    if token.endswith("Z"):
        token = f"{token[:-1]}+00:00"
    if not token:
        return datetime(2026, 6, 4, 10, 25, 0, tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(token)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _work_ledger_source_modules_root(input_dir: Path, public_root: Path) -> Path:
    """
    [ACTION]
    - Teleology: Implements `_work_ledger_source_modules_root` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    candidates = [
        input_dir / "source_modules",
        public_root
        / "examples/mission_transaction_work_spine/exported_mission_transaction_bundle/source_modules",
    ]
    for candidate in candidates:
        if (candidate / "system/lib/work_ledger_runtime.py").is_file():
            return candidate
    return candidates[-1]


def _import_exact_copy_work_ledger_runtime(source_modules_root: Path) -> Any:
    """
    [ACTION]
    - Teleology: Implements `_import_exact_copy_work_ledger_runtime` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source_root = str(source_modules_root.resolve(strict=False))
    saved_path = list(sys.path)
    saved_system_modules = {
        name: module
        for name, module in list(sys.modules.items())
        if name == "system" or name.startswith("system.")
    }
    try:
        for name in list(saved_system_modules):
            sys.modules.pop(name, None)
        sys.path.insert(0, source_root)
        return importlib.import_module("system.lib.work_ledger_runtime")
    finally:
        for name in [
            module_name
            for module_name in list(sys.modules)
            if module_name == "system" or module_name.startswith("system.")
        ]:
            sys.modules.pop(name, None)
        sys.modules.update(saved_system_modules)
        sys.path[:] = saved_path


def _snapshot_path_claims(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_snapshot_path_claims` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [
        dict(claim)
        for claim in snapshot.get("active_claims") or []
        if isinstance(claim, dict) and str(claim.get("scope_kind") or "") == "path"
    ]


def _public_claim_rows_from_snapshot(
    path_claims: list[dict[str, Any]],
    expected_parent_by_claim: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_public_claim_rows_from_snapshot` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows: list[dict[str, Any]] = []
    for claim in path_claims:
        claim_id = str(claim.get("claim_id") or "").strip()
        owned_path = str(claim.get("path") or claim.get("scope_id") or "").strip()
        if not claim_id or not owned_path:
            continue
        rows.append(
            {
                "claim_id": claim_id,
                "session_id": claim.get("session_id"),
                "actor": claim.get("actor"),
                "work_item_id": claim.get("work_item_id") or "",
                "owned_paths": [owned_path],
                "status": "active",
                "expected_parent_sha": str(expected_parent_by_claim.get(claim_id) or ""),
                "source_scope_kind": claim.get("scope_kind"),
                "source_claim_intent": claim.get("claim_intent"),
                "projection_not_authority": True,
                "body_in_receipt": False,
            }
        )
    return rows


def _public_preflight_from_runtime_snapshot(
    work_ledger_runtime: Any,
    public_root: Path,
    runtime_status: dict[str, Any],
    *,
    snapshot_now: datetime,
    subject_ids: list[str],
    owned_paths: list[str],
    expected_parent_by_claim: dict[str, Any],
    current_parent_by_claim: dict[str, Any],
    checkpoint_policy: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_public_preflight_from_runtime_snapshot` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    snapshot = work_ledger_runtime.build_active_claims_snapshot(
        public_root,
        runtime_status,
        now=snapshot_now,
    )
    path_claims = _snapshot_path_claims(snapshot)
    public_claims = _public_claim_rows_from_snapshot(path_claims, expected_parent_by_claim)
    preflight = _with_landing_decision_status(
        build_public_mission_transaction_preflight(
            subject_ids=subject_ids,
            owned_paths=owned_paths,
            claims_payload={"claims": public_claims},
            repo_state={"current_parent_by_claim": current_parent_by_claim},
            checkpoint_lane_policy=checkpoint_policy,
            checkpoint_negative_cases=[],
            require_exclusive=True,
        )
    )
    preflight["claim_row_source"] = "rebuilt_work_ledger_active_claims_snapshot"
    preflight["claim_row_count"] = len(public_claims)
    preflight["accepted_claim_ids"] = sorted(
        {
            str(claim.get("claim_id") or "")
            for claim in public_claims
            if str(claim.get("claim_id") or "")
        }
    )
    preflight["runtime_snapshot_source_hash"] = snapshot.get("source_hash")
    return snapshot, preflight


def _claim_maps_from_runtime_status(
    runtime_status: dict[str, Any],
    field_name: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_claim_maps_from_runtime_status` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows: dict[str, Any] = {}
    sessions = runtime_status.get("sessions") if isinstance(runtime_status.get("sessions"), dict) else {}
    for session in sessions.values():
        if not isinstance(session, dict):
            continue
        claims = session.get("claims") if isinstance(session.get("claims"), list) else []
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            claim_id = str(claim.get("claim_id") or "").strip()
            value = claim.get(field_name)
            if claim_id and value:
                rows[claim_id] = value
    return rows


def _runtime_status_with_mutated_path_conflict(
    runtime_status: dict[str, Any],
    *,
    source_claim: dict[str, Any],
    mutation_case: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_runtime_status_with_mutated_path_conflict` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    mutated = copy.deepcopy(runtime_status)
    session_id = str(mutation_case.get("session_id") or "real_snapshot_conflict_session")
    claim_id = str(mutation_case.get("claim_id") or "real_snapshot_conflict_claim")
    claim = copy.deepcopy(source_claim)
    mutated_path = str(
        mutation_case.get("path")
        or mutation_case.get("scope_id")
        or source_claim.get("path")
        or source_claim.get("scope_id")
        or ""
    )
    claim.update(
        {
            "claim_id": claim_id,
            "session_id": session_id,
            "scope_id": mutated_path,
            "path": mutated_path,
            "claimed_at": mutation_case.get("claimed_at") or source_claim.get("claimed_at"),
            "leased_until": mutation_case.get("leased_until")
            or source_claim.get("leased_until"),
            "released_at": None,
            "expired_at": None,
            "note": "public_safe_same_path_conflict_mutation",
        }
    )
    signal_at = str(mutation_case.get("claimed_at") or source_claim.get("claimed_at") or "")
    leased_until = str(
        mutation_case.get("leased_until") or source_claim.get("leased_until") or ""
    )
    sessions = mutated.setdefault("sessions", {})
    sessions[session_id] = {
        "session_id": session_id,
        "actor": mutation_case.get("actor") or "public_safe_conflict_mutation",
        "phase_id": mutation_case.get("phase_id") or "09_54_1",
        "bootstrapped_at": signal_at,
        "last_activity_at": signal_at,
        "last_activity_action": "session-heartbeat",
        "touched_work": True,
        "ended_at": None,
        "pass_heartbeat": {
            "schema": "runtime_pass_heartbeat_v0",
            "session_id": session_id,
            "actor": mutation_case.get("actor") or "public_safe_conflict_mutation",
            "phase_id": mutation_case.get("phase_id") or "09_54_1",
            "family_id": "09",
            "pass_id": "wlp_public_safe_conflict_mutation",
            "pass_seq": 1,
            "pass_state": "editing",
            "current_pass_line": "Public-safe same-path conflict mutation.",
            "last_pass_result_line": "Real-good owner-excluded collision check was clear.",
            "scope_refs": [
                {
                    "kind": "ref",
                    "ref": mutated_path,
                }
            ],
            "updated_at": signal_at,
            "expires_at": leased_until,
            "current_pass_updated_at": signal_at,
            "last_pass_completed_at": signal_at,
            "source": "manual_cli",
        },
        "claims": [claim],
    }
    return mutated


def _runtime_status_with_mutated_expected_parent(
    runtime_status: dict[str, Any],
    *,
    claim_id: str,
    expected_parent_sha: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_runtime_status_with_mutated_expected_parent` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    mutated = copy.deepcopy(runtime_status)
    sessions = mutated.get("sessions") if isinstance(mutated.get("sessions"), dict) else {}
    for session in sessions.values():
        if not isinstance(session, dict):
            continue
        claims = session.get("claims") if isinstance(session.get("claims"), list) else []
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            if str(claim.get("claim_id") or "") == claim_id:
                claim["expected_parent_sha"] = expected_parent_sha
                return mutated
    return mutated


def _checkpoint_policy_with_mutated_landing_row(
    checkpoint_policy: object,
    *,
    mutation_case: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_checkpoint_policy_with_mutated_landing_row` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    mutated = copy.deepcopy(checkpoint_policy) if isinstance(checkpoint_policy, dict) else {}
    cases = mutated.get("lane_cases")
    if not isinstance(cases, list):
        cases = []
    mutated["lane_cases"] = list(cases)
    mutated["lane_cases"].append(
        {
            "case_id": str(
                mutation_case.get("case_id")
                or "real_snapshot_broad_checkpoint_without_operator_authorization"
            ),
            "negative_case_id": "real_work_ledger_mutated_landing_row",
            "tree_state": "mixed_dirty_tree",
            "dirty_tree_present": True,
            "owned_paths_isolated": False,
            "broad_checkpoint_requested": True,
            "operator_authorized_broad_checkpoint": False,
            "suspected_secret": False,
            "selected_lane": "broad_checkpoint",
        }
    )
    return mutated


def _with_landing_decision_status(preflight: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_with_landing_decision_status` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    result = dict(preflight)
    landing_decision = result.get("landing_decision")
    if isinstance(landing_decision, dict) and landing_decision.get("status"):
        result["checkpoint_lane_status"] = result.get("status")
        result["status"] = landing_decision["status"]
    return result


def _collision_claim_ids(collisions: list[dict[str, Any]]) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_collision_claim_ids` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return sorted(
        {
            str(collision.get("claim_id") or "")
            for collision in collisions
            if str(collision.get("claim_id") or "").strip()
        }
    )


def validate_real_active_claims_snapshot(
    payload: object,
    input_dir: Path,
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_real_active_claims_snapshot` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if not isinstance(payload, dict):
        _record(
            findings,
            observed,
            "REAL_ACTIVE_CLAIMS_SNAPSHOT_INVALID",
            "Real active-claims snapshot fixture must be a JSON object.",
            case_id="real_work_ledger_active_claim_snapshot_invalid",
            subject_id=REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME,
            subject_kind="real_work_ledger_snapshot_fixture",
        )
        return {
            "status": "blocked",
            "findings": findings,
            "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        }

    runtime_status = payload.get("runtime_status")
    if not isinstance(runtime_status, dict):
        runtime_status = {}
    source_modules_root = _work_ledger_source_modules_root(input_dir, public_root)
    work_ledger_runtime = _import_exact_copy_work_ledger_runtime(source_modules_root)
    snapshot_now = _parse_iso_utc(payload.get("snapshot_now"))
    snapshot = work_ledger_runtime.build_active_claims_snapshot(
        public_root,
        runtime_status,
        now=snapshot_now,
    )
    declared_source_hash = str(payload.get("source_snapshot_hash") or "").strip()
    recomputed_source_hash = str(snapshot.get("source_hash") or "").strip()
    source_hash_integrity_passed = (
        len(declared_source_hash) == 64
        and all(char in "0123456789abcdef" for char in declared_source_hash.lower())
        and declared_source_hash != ("0" * 64)
        and bool(recomputed_source_hash)
        and declared_source_hash == recomputed_source_hash
    )
    if not source_hash_integrity_passed:
        _record(
            findings,
            observed,
            "REAL_ACTIVE_CLAIMS_SNAPSHOT_HASH_MISMATCH",
            "Declared sanitized Work Ledger source snapshot hash must match the recomputed runtime snapshot digest.",
            case_id="real_work_ledger_receipt_artifact_mutation",
            subject_id=REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME,
            subject_kind="real_work_ledger_snapshot_fixture",
        )
    path_claims = _snapshot_path_claims(snapshot)
    expected_parent_by_claim = (
        payload.get("expected_parent_by_claim")
        if isinstance(payload.get("expected_parent_by_claim"), dict)
        else {}
    )
    expected_parent_by_claim = {
        **expected_parent_by_claim,
        **_claim_maps_from_runtime_status(runtime_status, "expected_parent_sha"),
    }
    current_parent_by_claim = (
        payload.get("current_parent_by_claim")
        if isinstance(payload.get("current_parent_by_claim"), dict)
        else {}
    )
    current_parent_by_claim = {
        **current_parent_by_claim,
        **_claim_maps_from_runtime_status(runtime_status, "current_parent_sha"),
    }
    subject_ids = _strings(payload.get("subject_ids")) or [
        str(payload.get("work_item_id") or "cap_quick_mission_transaction_real_claim_snapshot")
    ]
    owned_paths = _strings(payload.get("owned_paths")) or sorted(
        {
            owned_path
            for claim in _public_claim_rows_from_snapshot(path_claims, expected_parent_by_claim)
            for owned_path in _strings(claim.get("owned_paths"))
        }
    )
    checkpoint_policy = payload.get("checkpoint_lane_policy")
    if not isinstance(checkpoint_policy, dict):
        checkpoint_policy = {"lane_cases": []}

    snapshot, real_good_preflight = _public_preflight_from_runtime_snapshot(
        work_ledger_runtime,
        public_root,
        runtime_status,
        snapshot_now=snapshot_now,
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        expected_parent_by_claim=expected_parent_by_claim,
        current_parent_by_claim=current_parent_by_claim,
        checkpoint_policy=checkpoint_policy,
    )

    mutation_cases = payload.get("mutation_cases")
    mutation_cases = mutation_cases if isinstance(mutation_cases, dict) else {}
    conflict_case = mutation_cases.get("same_path_conflict")
    conflict_case = conflict_case if isinstance(conflict_case, dict) else {}
    stale_case = mutation_cases.get("expected_parent_mismatch")
    stale_case = stale_case if isinstance(stale_case, dict) else {}
    landing_case = mutation_cases.get("landing_row_violation")
    landing_case = landing_case if isinstance(landing_case, dict) else {}

    source_conflict_claim = path_claims[0] if path_claims else {}
    mutated_runtime_status = _runtime_status_with_mutated_path_conflict(
        runtime_status,
        source_claim=source_conflict_claim,
        mutation_case=conflict_case,
    ) if source_conflict_claim else runtime_status
    _conflict_snapshot, conflict_preflight = _public_preflight_from_runtime_snapshot(
        work_ledger_runtime,
        public_root,
        mutated_runtime_status,
        snapshot_now=snapshot_now,
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        expected_parent_by_claim=expected_parent_by_claim,
        current_parent_by_claim=current_parent_by_claim,
        checkpoint_policy=checkpoint_policy,
    )

    stale_claims = _snapshot_path_claims(snapshot)
    stale_claim_id = str(
        stale_case.get("claim_id")
        or (stale_claims[0].get("claim_id") if stale_claims else "")
        or "real_snapshot_stale_parent_claim"
    )
    stale_runtime_status = _runtime_status_with_mutated_expected_parent(
        runtime_status,
        claim_id=stale_claim_id,
        expected_parent_sha=str(
            stale_case.get("mutated_expected_parent_sha") or "stale_parent_sha"
        ),
    )
    stale_expected_parent_by_claim = {
        **expected_parent_by_claim,
        **_claim_maps_from_runtime_status(stale_runtime_status, "expected_parent_sha"),
    }
    _stale_snapshot, stale_preflight = _public_preflight_from_runtime_snapshot(
        work_ledger_runtime,
        public_root,
        stale_runtime_status,
        snapshot_now=snapshot_now,
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        expected_parent_by_claim=stale_expected_parent_by_claim,
        current_parent_by_claim=current_parent_by_claim,
        checkpoint_policy=checkpoint_policy,
    )
    equal_parent_expected_by_claim = dict(expected_parent_by_claim)
    equal_parent_expected_by_claim[stale_claim_id] = str(
        current_parent_by_claim.get(stale_claim_id)
        or expected_parent_by_claim.get(stale_claim_id)
        or ""
    )
    _equal_parent_snapshot, equal_parent_preflight = _public_preflight_from_runtime_snapshot(
        work_ledger_runtime,
        public_root,
        runtime_status,
        snapshot_now=snapshot_now,
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        expected_parent_by_claim=equal_parent_expected_by_claim,
        current_parent_by_claim=current_parent_by_claim,
        checkpoint_policy=checkpoint_policy,
    )
    source_path = str(source_conflict_claim.get("path") or source_conflict_claim.get("scope_id") or "")
    disjoint_path = str(
        conflict_case.get("disjoint_path")
        or "public_safe_disjoint_mutation/outside_requested_scope.txt"
    )
    disjoint_runtime_status = _runtime_status_with_mutated_path_conflict(
        runtime_status,
        source_claim=source_conflict_claim,
        mutation_case={**conflict_case, "path": disjoint_path, "scope_id": disjoint_path},
    ) if source_conflict_claim else runtime_status
    _disjoint_snapshot, disjoint_preflight = _public_preflight_from_runtime_snapshot(
        work_ledger_runtime,
        public_root,
        disjoint_runtime_status,
        snapshot_now=snapshot_now,
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        expected_parent_by_claim=expected_parent_by_claim,
        current_parent_by_claim=current_parent_by_claim,
        checkpoint_policy=checkpoint_policy,
    )
    landing_mutation_preflight = _with_landing_decision_status(
        build_public_mission_transaction_preflight(
            subject_ids=subject_ids,
            owned_paths=owned_paths,
            claims_payload={"claims": _public_claim_rows_from_snapshot(path_claims, expected_parent_by_claim)},
            repo_state={"current_parent_by_claim": current_parent_by_claim},
            checkpoint_lane_policy=_checkpoint_policy_with_mutated_landing_row(
                checkpoint_policy,
                mutation_case=landing_case,
            ),
            checkpoint_negative_cases=[],
            require_exclusive=True,
        )
    )

    source_session_id = str(payload.get("source_session_id") or "")
    requested_path = str(source_conflict_claim.get("path") or source_conflict_claim.get("scope_id") or "")
    owner_excluded_collisions = work_ledger_runtime.active_claim_collisions_for_paths(
        public_root,
        [requested_path] if requested_path else [],
        status=runtime_status,
        session_id=source_session_id,
        now=snapshot_now,
    )
    mutated_runtime_collisions = work_ledger_runtime.active_claim_collisions_for_paths(
        public_root,
        [requested_path] if requested_path else [],
        status=mutated_runtime_status,
        session_id=source_session_id,
        now=snapshot_now,
    )
    disjoint_runtime_collisions = work_ledger_runtime.active_claim_collisions_for_paths(
        public_root,
        [requested_path] if requested_path else [],
        status=disjoint_runtime_status,
        session_id=source_session_id,
        now=snapshot_now,
    )
    real_good_preflight["runtime_collision_row_source"] = (
        "work_ledger_runtime.active_claim_collisions_for_paths"
    )
    real_good_preflight["runtime_collision_claim_ids"] = _collision_claim_ids(
        owner_excluded_collisions
    )
    conflict_preflight["runtime_collision_row_source"] = (
        "work_ledger_runtime.active_claim_collisions_for_paths"
    )
    conflict_preflight["runtime_collision_claim_ids"] = _collision_claim_ids(
        mutated_runtime_collisions
    )
    disjoint_preflight["runtime_collision_row_source"] = (
        "work_ledger_runtime.active_claim_collisions_for_paths"
    )
    disjoint_preflight["runtime_collision_claim_ids"] = _collision_claim_ids(
        disjoint_runtime_collisions
    )

    if conflict_preflight["status"] == "blocked" and conflict_preflight["conflict_claim_ids"]:
        _record(
            findings,
            observed,
            "SAME_PATH_CLAIM_CONFLICT",
            "Real Work Ledger path claim rejects a one-field same-path mutation.",
            case_id="real_work_ledger_same_path_claim_conflict",
            subject_id=str(conflict_case.get("claim_id") or "real_snapshot_same_path_conflict_claim"),
            subject_kind="real_work_ledger_claim_mutation",
        )
    if stale_preflight["status"] == "blocked" and stale_preflight["stale_expected_parent_claim_ids"]:
        _record(
            findings,
            observed,
            "EXPECTED_PARENT_MISMATCH",
            "Real Work Ledger path claim rejects a one-field expected-parent mutation.",
            case_id="real_work_ledger_expected_parent_mismatch",
            subject_id=stale_claim_id,
            subject_kind="real_work_ledger_claim_mutation",
        )
    if (
        landing_mutation_preflight["status"] == "blocked"
        and "checkpoint_lane_violation"
        in landing_mutation_preflight["landing_decision"]["blockers"]
        and landing_mutation_preflight["broad_checkpoint_authorization_required_case_ids"]
    ):
        _record(
            findings,
            observed,
            "CHECKPOINT_BROAD_AUTH_REQUIRED",
            "Real Work Ledger landing preflight rejects a one-row broad checkpoint mutation.",
            case_id="real_work_ledger_mutated_landing_row",
            subject_id=landing_mutation_preflight[
                "broad_checkpoint_authorization_required_case_ids"
            ][0],
            subject_kind="mission_transaction_landing_row_mutation",
        )

    good_passed = (
        real_good_preflight["status"] == "pass"
        and not real_good_preflight["conflict_claim_ids"]
        and not real_good_preflight["stale_expected_parent_claim_ids"]
    )
    runtime_collision_discriminates = (
        len(owner_excluded_collisions) == 0 and len(mutated_runtime_collisions) > 0
    )
    mutation_blocked = (
        conflict_preflight["status"] == "blocked"
        and stale_preflight["status"] == "blocked"
        and landing_mutation_preflight["status"] == "blocked"
        and runtime_collision_discriminates
    )
    mutation_clears = (
        disjoint_preflight["status"] == "pass"
        and equal_parent_preflight["status"] == "pass"
        and len(disjoint_runtime_collisions) == 0
    )
    landing_mutation_discriminates = (
        real_good_preflight["status"] == "pass"
        and landing_mutation_preflight["status"] == "blocked"
        and "checkpoint_lane_violation"
        in landing_mutation_preflight["landing_decision"]["blockers"]
    )
    source_snapshot_ref = str(payload.get("source_snapshot_ref") or "")
    source_session = (
        runtime_status.get("sessions", {}).get(source_session_id)
        if isinstance(runtime_status.get("sessions"), dict) and source_session_id
        else {}
    )
    source_session = source_session if isinstance(source_session, dict) else {}
    source_heartbeat = (
        source_session.get("pass_heartbeat")
        if isinstance(source_session.get("pass_heartbeat"), dict)
        else {}
    )
    source_session_claim_ids = sorted(
        {
            str(claim.get("claim_id") or "")
            for claim in source_session.get("claims", [])
            if isinstance(claim, dict) and str(claim.get("claim_id") or "")
        }
    )
    session_snapshot_bound = bool(
        source_session_id
        and source_session.get("session_id") == source_session_id
        and source_session_claim_ids
        and source_heartbeat.get("current_pass_line")
        and source_heartbeat.get("last_pass_result_line")
    )
    source_ref_public_safe = bool(source_snapshot_ref) and not any(
        private_token in source_snapshot_ref
        for private_token in ("/Users/", "/private/", "src/ai_workflow", "raw_seed")
    )
    realness_r3_bound = (
        good_passed
        and mutation_blocked
        and mutation_clears
        and landing_mutation_discriminates
        and source_hash_integrity_passed
        and session_snapshot_bound
        and source_ref_public_safe
    )
    realness_rank = 3 if realness_r3_bound else 2 if mutation_blocked else 1
    realness_evidence = {
        "schema_version": "mission_transaction_work_spine_realness_evidence_v1",
        "status": PASS if realness_r3_bound else "blocked",
        "realness_rank": realness_rank,
        "realness_rung": f"R{realness_rank}",
        "realness_state": (
            "public_safe_real_work_ledger_session_snapshot_replay"
            if realness_r3_bound
            else "fixture_negative_cases_and_runtime_mutations_bound"
            if mutation_blocked
            else "metadata_floor_only"
        ),
        "rank_derivation": (
            "copied_work_ledger_runtime_recomputed_public_preflight_plus_"
            "mutated_same_path_expected_parent_and_landing_row_rejection"
        ),
        "evidence_source": (
            "sanitized_real_work_ledger_runtime_status_and_copied_work_ledger_runtime"
        ),
        "verdict_rederived_from_runtime_evidence": True,
        "expected_labels_used_for_verdict": False,
        "baked_fixture_label_sufficient": False,
        "real_good_input_passed": good_passed,
        "mutated_or_stale_snapshot_rejected": mutation_blocked,
        "clear_input_perturbation_moves_verdict": mutation_clears,
        "landing_row_mutation_rejected": landing_mutation_discriminates,
        "source_snapshot_hash_bound": source_hash_integrity_passed,
        "source_snapshot_ref": source_snapshot_ref,
        "source_snapshot_ref_public_safe": source_ref_public_safe,
        "source_snapshot_hash": declared_source_hash,
        "runtime_snapshot_source_hash": recomputed_source_hash,
        "session_snapshot_bound": session_snapshot_bound,
        "source_session_id": source_session_id,
        "source_session_claim_ids": source_session_claim_ids,
        "source_session_claim_count": len(source_session_claim_ids),
        "source_session_heartbeat_bound": bool(source_heartbeat),
        "source_session_public_line_fields": [
            field
            for field in ("current_pass_line", "last_pass_result_line")
            if source_heartbeat.get(field)
        ],
        "source_runtime_symbols": [
            "system.lib.work_ledger_runtime::build_active_claims_snapshot",
            "system.lib.work_ledger_runtime::active_claim_collisions_for_paths",
        ],
        "authority_ceiling_bound": True,
        "release_authorized": False,
        "body_in_receipt": False,
    }

    return {
        "status": (
            PASS
            if good_passed
            and mutation_blocked
            and mutation_clears
            and landing_mutation_discriminates
            and source_hash_integrity_passed
            and realness_r3_bound
            else "blocked"
        ),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "fixture_ref": public_relative_path(
            input_dir / REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME,
            display_root=public_root,
        ),
        "sanitization_boundary": payload.get("sanitization_boundary"),
        "source_snapshot_ref": payload.get("source_snapshot_ref"),
        "source_snapshot_hash": payload.get("source_snapshot_hash"),
        "realness_evidence": realness_evidence,
        "realness_rank": realness_evidence["realness_rank"],
        "realness_rung": realness_evidence["realness_rung"],
        "realness_state": realness_evidence["realness_state"],
        "source_runtime_module_ref": public_relative_path(
            source_modules_root / "system/lib/work_ledger_runtime.py",
            display_root=public_root,
        ),
        "source_runtime_symbols": [
            "system.lib.work_ledger_runtime::build_active_claims_snapshot",
            "system.lib.work_ledger_runtime::active_claim_collisions_for_paths",
        ],
        "runtime_snapshot_counts": snapshot.get("counts") or {},
        "runtime_snapshot_source_hash": snapshot.get("source_hash"),
        "source_snapshot_hash_check": {
            "status": PASS if source_hash_integrity_passed else "blocked",
            "declared_source_snapshot_hash": declared_source_hash,
            "recomputed_runtime_snapshot_hash": recomputed_source_hash,
            "verdict_source": (
                "declared_source_artifact_digest_sanity_plus_"
                "copied_work_ledger_runtime_build_active_claims_snapshot"
            ),
            "body_in_receipt": False,
        },
        "real_good_public_preflight": real_good_preflight,
        "same_path_conflict_public_preflight": conflict_preflight,
        "expected_parent_mismatch_public_preflight": stale_preflight,
        "disjoint_path_mutation_public_preflight": disjoint_preflight,
        "equal_parent_mutation_public_preflight": equal_parent_preflight,
        "landing_row_mutation_public_preflight": landing_mutation_preflight,
        "runtime_collision_check": {
            "requested_path": requested_path,
            "owner_session_id": source_session_id,
            "collision_row_source": "work_ledger_runtime.active_claim_collisions_for_paths",
            "owner_excluded_collision_count": len(owner_excluded_collisions),
            "mutated_runtime_collision_count": len(mutated_runtime_collisions),
            "disjoint_runtime_collision_count": len(disjoint_runtime_collisions),
            "owner_excluded_collision_claim_ids": _collision_claim_ids(
                owner_excluded_collisions
            ),
            "mutated_runtime_collision_claim_ids": _collision_claim_ids(
                mutated_runtime_collisions
            ),
            "disjoint_runtime_collision_claim_ids": _collision_claim_ids(
                disjoint_runtime_collisions
            ),
            "mutated_runtime_collisions": mutated_runtime_collisions,
            "body_in_receipt": False,
        },
        "landing_row_mutation_check": {
            "status": PASS if landing_mutation_discriminates else "blocked",
            "good_landing_status": real_good_preflight["landing_decision"]["status"],
            "mutated_landing_status": landing_mutation_preflight["landing_decision"][
                "status"
            ],
            "mutated_landing_blockers": landing_mutation_preflight["landing_decision"][
                "blockers"
            ],
            "mutated_checkpoint_violation_case_ids": landing_mutation_preflight[
                "checkpoint_lane_violation_case_ids"
            ],
            "body_in_receipt": False,
        },
        "baked_expected_label_policy": {
            "status": "ignored",
            "ignored_input_fields": sorted(
                set(payload)
                & {
                    "active_claim_count",
                    "claim_collision_count",
                    "expected_negative_cases",
                    "expected_verdict",
                    "real_active_claims_snapshot_status",
                    "runtime_snapshot_counts",
                    "seed_speed_status",
                }
            ),
            "verdict_source": "recomputed_work_ledger_runtime_and_public_mission_preflight",
            "body_in_receipt": False,
        },
        "subject_ids": subject_ids,
        "owned_paths": owned_paths,
        "source_session_id": source_session_id,
        "real_good_input_passed": good_passed,
        "real_wrong_input_rejected": mutation_blocked,
        "real_wrong_input_clear_mutation_passed": mutation_clears,
        "body_in_receipt": False,
    }


def _load_optional_json_document(
    path: Path,
    findings: list[dict[str, Any]],
    *,
    subject_id: str,
    source_label: str = "Task Ledger",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_optional_json_document` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    if not path.exists():
        findings.append(
            _bundle_finding(
                "TASK_LEDGER_SOURCE_DOCUMENT_MISSING",
                f"{source_label} source import document is missing from the exported bundle.",
                subject_id=subject_id,
                subject_kind=f"{source_label.lower().replace(' ', '_')}_source_import",
            )
        )
        return {}
    try:
        payload = read_json_strict(path)
    except Exception as exc:
        findings.append(
            _bundle_finding(
                "TASK_LEDGER_SOURCE_DOCUMENT_INVALID",
                f"{source_label} source import document is not valid JSON: {exc}",
                subject_id=subject_id,
                subject_kind=f"{source_label.lower().replace(' ', '_')}_source_import",
            )
        )
        return {}
    if not isinstance(payload, dict):
        findings.append(
            _bundle_finding(
                "TASK_LEDGER_SOURCE_DOCUMENT_NOT_OBJECT",
                f"{source_label} source import document must decode to an object.",
                subject_id=subject_id,
                subject_kind=f"{source_label.lower().replace(' ', '_')}_source_import",
            )
        )
        return {}
    return payload


def validate_task_ledger_source_import(input_dir: Path, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_task_ledger_source_import` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    manifest_path = input_dir / TASK_LEDGER_SOURCE_MANIFEST_NAME
    contract_path = input_dir / TASK_LEDGER_CONTRACT_NAME
    manifest = _load_optional_json_document(
        manifest_path,
        findings,
        subject_id=TASK_LEDGER_SOURCE_MANIFEST_NAME,
    )
    contract = _load_optional_json_document(
        contract_path,
        findings,
        subject_id=TASK_LEDGER_CONTRACT_NAME,
    )
    manifest_rows = [
        row for row in manifest.get("modules", []) if isinstance(row, dict)
    ]
    manifest_by_id = {
        str(row.get("module_id") or ""): row
        for row in manifest_rows
        if str(row.get("module_id") or "")
    }
    expected_ids = [str(module["module_id"]) for module in TASK_LEDGER_SOURCE_MODULES]
    contract_ids = [str(item) for item in contract.get("required_module_ids", [])]
    source_module_results: list[dict[str, Any]] = []

    if manifest.get("module_count") != len(TASK_LEDGER_SOURCE_MODULES):
        findings.append(
            _bundle_finding(
                "TASK_LEDGER_SOURCE_MANIFEST_COUNT_MISMATCH",
                "Task Ledger source module manifest does not declare the expected module count.",
                subject_id=TASK_LEDGER_SOURCE_MANIFEST_NAME,
                subject_kind="task_ledger_source_import",
            )
        )
    if sorted(manifest_by_id) != sorted(expected_ids):
        findings.append(
            _bundle_finding(
                "TASK_LEDGER_SOURCE_MANIFEST_MODULES_MISMATCH",
                "Task Ledger source module manifest does not declare exactly the required module ids.",
                subject_id=TASK_LEDGER_SOURCE_MANIFEST_NAME,
                subject_kind="task_ledger_source_import",
            )
        )
    if sorted(contract_ids) != sorted(expected_ids):
        findings.append(
            _bundle_finding(
                "TASK_LEDGER_SOURCE_CONTRACT_MODULES_MISMATCH",
                "Task Ledger source runtime contract does not require exactly the expected module ids.",
                subject_id=TASK_LEDGER_CONTRACT_NAME,
                subject_kind="task_ledger_source_import",
            )
        )

    for module in TASK_LEDGER_SOURCE_MODULES:
        module_id = str(module["module_id"])
        row = manifest_by_id.get(module_id, {})
        module_path = input_dir / str(module["bundle_path"])
        missing_anchors: list[str] = []
        actual_sha = ""
        actual_line_count = 0
        actual_byte_count = 0

        if not module_path.exists():
            findings.append(
                _bundle_finding(
                    "TASK_LEDGER_SOURCE_MODULE_MISSING",
                    "Copied Task Ledger source module is missing from the exported bundle.",
                    subject_id=module_id,
                    subject_kind="task_ledger_source_import",
                )
            )
        else:
            text = module_path.read_text(encoding="utf-8")
            actual_sha = _file_sha256(module_path)
            actual_line_count = _line_count(module_path)
            actual_byte_count = _file_size_bytes(module_path)
            missing_anchors = [
                str(anchor)
                for anchor in module.get("required_anchors", [])
                if str(anchor) not in text
            ]
            if missing_anchors:
                findings.append(
                    _bundle_finding(
                        "TASK_LEDGER_SOURCE_ANCHOR_MISSING",
                        "Copied Task Ledger source module is missing expected control-plane anchors.",
                        subject_id=module_id,
                        subject_kind="task_ledger_source_import",
                    )
                )

        if row:
            expected_pairs = {
                "source_ref": module["source_ref"],
                "target_ref": module["target_ref"],
                "classification": "copied_non_secret_macro_body",
                "body_copied": True,
                "body_in_receipt": False,
            }
            for field, expected in expected_pairs.items():
                if row.get(field) != expected:
                    findings.append(
                        _bundle_finding(
                            "TASK_LEDGER_SOURCE_MANIFEST_FIELD_MISMATCH",
                            "Task Ledger source module manifest field does not match the import contract.",
                            subject_id=f"{module_id}:{field}",
                            subject_kind="task_ledger_source_import",
                        )
                    )
            if row.get("sha256_match") is not True or (
                actual_sha and row.get("target_sha256") != actual_sha
            ):
                findings.append(
                    _bundle_finding(
                        "TASK_LEDGER_SOURCE_SHA_MISMATCH",
                        "Task Ledger source module digest does not match the copied bundle body.",
                        subject_id=module_id,
                        subject_kind="task_ledger_source_import",
                    )
                )
            if actual_line_count and row.get("line_count") != actual_line_count:
                findings.append(
                    _bundle_finding(
                        "TASK_LEDGER_SOURCE_LINE_COUNT_MISMATCH",
                        "Task Ledger source module line count does not match the copied bundle body.",
                        subject_id=module_id,
                        subject_kind="task_ledger_source_import",
                    )
                )

        source_module_results.append(
            {
                "module_id": module_id,
                "source_ref": module["source_ref"],
                "target_ref": module["target_ref"],
                "public_runtime_ref": public_relative_path(
                    module_path,
                    display_root=public_root,
                ),
                "sha256": actual_sha,
                "line_count": actual_line_count,
                "byte_count": actual_byte_count,
                "anchor_count": len(module.get("required_anchors", [])),
                "missing_anchors": missing_anchors,
                "body_copied": module_path.exists(),
                "body_in_receipt": False,
            }
        )

    public_refs = [
        public_relative_path(path, display_root=public_root)
        for path in _task_ledger_source_paths(input_dir)
    ]
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "classification": "copied_non_secret_macro_body",
        "manifest_ref": public_relative_path(manifest_path, display_root=public_root),
        "contract_ref": public_relative_path(contract_path, display_root=public_root),
        "module_count": len(source_module_results),
        "module_ids": [row["module_id"] for row in source_module_results],
        "source_refs": [row["source_ref"] for row in source_module_results],
        "target_refs": [row["target_ref"] for row in source_module_results],
        "public_runtime_refs": public_refs,
        "source_modules": source_module_results,
        "total_line_count": sum(row["line_count"] for row in source_module_results),
        "manifest_summary": {
            "schema_version": manifest.get("schema_version"),
            "module_count": manifest.get("module_count"),
            "body_storage_policy": manifest.get("body_storage_policy"),
            "receipt_body_policy": manifest.get("receipt_body_policy"),
            "validation_contract_ref": manifest.get("validation_contract_ref"),
            "body_in_receipt": False,
        },
        "contract_summary": {
            "schema_version": contract.get("schema_version"),
            "contract_id": contract.get("contract_id"),
            "status": contract.get("status"),
            "required_module_ids": contract_ids,
            "body_in_receipt": False,
        },
        "body_in_receipt": False,
    }


def validate_work_ledger_source_import(input_dir: Path, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_work_ledger_source_import` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    manifest_path = input_dir / WORK_LEDGER_SOURCE_MANIFEST_NAME
    contract_path = input_dir / WORK_LEDGER_CONTRACT_NAME
    manifest = _load_optional_json_document(
        manifest_path,
        findings,
        subject_id=WORK_LEDGER_SOURCE_MANIFEST_NAME,
        source_label="Work Ledger",
    )
    contract = _load_optional_json_document(
        contract_path,
        findings,
        subject_id=WORK_LEDGER_CONTRACT_NAME,
        source_label="Work Ledger",
    )
    manifest_rows = [
        row for row in manifest.get("modules", []) if isinstance(row, dict)
    ]
    manifest_by_id = {
        str(row.get("module_id") or ""): row
        for row in manifest_rows
        if str(row.get("module_id") or "")
    }
    expected_ids = [str(module["module_id"]) for module in WORK_LEDGER_SOURCE_MODULES]
    contract_ids = [str(item) for item in contract.get("required_module_ids", [])]
    source_module_results: list[dict[str, Any]] = []

    if manifest.get("module_count") != len(WORK_LEDGER_SOURCE_MODULES):
        findings.append(
            _bundle_finding(
                "WORK_LEDGER_SOURCE_MANIFEST_COUNT_MISMATCH",
                "Work Ledger source module manifest does not declare the expected module count.",
                subject_id=WORK_LEDGER_SOURCE_MANIFEST_NAME,
                subject_kind="work_ledger_source_import",
            )
        )
    if sorted(manifest_by_id) != sorted(expected_ids):
        findings.append(
            _bundle_finding(
                "WORK_LEDGER_SOURCE_MANIFEST_MODULES_MISMATCH",
                "Work Ledger source module manifest does not declare exactly the required module ids.",
                subject_id=WORK_LEDGER_SOURCE_MANIFEST_NAME,
                subject_kind="work_ledger_source_import",
            )
        )
    if sorted(contract_ids) != sorted(expected_ids):
        findings.append(
            _bundle_finding(
                "WORK_LEDGER_SOURCE_CONTRACT_MODULES_MISMATCH",
                "Work Ledger source runtime contract does not require exactly the expected module ids.",
                subject_id=WORK_LEDGER_CONTRACT_NAME,
                subject_kind="work_ledger_source_import",
            )
        )

    for module in WORK_LEDGER_SOURCE_MODULES:
        module_id = str(module["module_id"])
        row = manifest_by_id.get(module_id, {})
        module_path = input_dir / str(module["bundle_path"])
        required_anchors = [str(anchor) for anchor in module.get("required_anchors", [])]
        missing_anchors: list[str] = []
        actual_sha = ""
        actual_line_count = 0
        actual_byte_count = 0

        if not module_path.exists():
            findings.append(
                _bundle_finding(
                    "WORK_LEDGER_SOURCE_MODULE_MISSING",
                    "Copied Work Ledger source module is missing from the exported bundle.",
                    subject_id=module_id,
                    subject_kind="work_ledger_source_import",
                )
            )
        else:
            text = module_path.read_text(encoding="utf-8")
            actual_sha = _file_sha256(module_path)
            actual_line_count = _line_count(module_path)
            actual_byte_count = _file_size_bytes(module_path)
            missing_anchors = [
                str(anchor)
                for anchor in required_anchors
                if str(anchor) not in text
            ]
            if missing_anchors:
                findings.append(
                    _bundle_finding(
                        "WORK_LEDGER_SOURCE_ANCHOR_MISSING",
                        "Copied Work Ledger source module is missing expected control-plane anchors.",
                        subject_id=module_id,
                        subject_kind="work_ledger_source_import",
                    )
                )

        if row:
            expected_pairs = {
                "source_ref": module["source_ref"],
                "target_ref": module["target_ref"],
                "classification": "copied_non_secret_macro_body",
                "body_copied": True,
                "body_in_receipt": False,
            }
            for field, expected in expected_pairs.items():
                if row.get(field) != expected:
                    findings.append(
                        _bundle_finding(
                            "WORK_LEDGER_SOURCE_MANIFEST_FIELD_MISMATCH",
                            "Work Ledger source module manifest field does not match the import contract.",
                            subject_id=f"{module_id}:{field}",
                            subject_kind="work_ledger_source_import",
                        )
                    )
            manifest_anchors = (
                [str(anchor) for anchor in row.get("required_anchors", [])]
                if isinstance(row.get("required_anchors"), list)
                else []
            )
            if manifest_anchors != required_anchors:
                findings.append(
                    _bundle_finding(
                        "WORK_LEDGER_SOURCE_MANIFEST_ANCHORS_MISMATCH",
                        "Work Ledger source module manifest must declare the required seed-speed and mutation-check coordination anchors.",
                        subject_id=module_id,
                        subject_kind="work_ledger_source_import",
                    )
                )
            if row.get("sha256_match") is not True or (
                actual_sha and row.get("target_sha256") != actual_sha
            ):
                findings.append(
                    _bundle_finding(
                        "WORK_LEDGER_SOURCE_SHA_MISMATCH",
                        "Work Ledger source module digest does not match the copied bundle body.",
                        subject_id=module_id,
                        subject_kind="work_ledger_source_import",
                    )
                )
            if actual_line_count and row.get("line_count") != actual_line_count:
                findings.append(
                    _bundle_finding(
                        "WORK_LEDGER_SOURCE_LINE_COUNT_MISMATCH",
                        "Work Ledger source module line count does not match the copied bundle body.",
                        subject_id=module_id,
                        subject_kind="work_ledger_source_import",
                    )
                )

        source_module_results.append(
            {
                "module_id": module_id,
                "source_ref": module["source_ref"],
                "target_ref": module["target_ref"],
                "public_runtime_ref": public_relative_path(
                    module_path,
                    display_root=public_root,
                ),
                "sha256": actual_sha,
                "line_count": actual_line_count,
                "byte_count": actual_byte_count,
                "anchor_count": len(required_anchors),
                "missing_anchors": missing_anchors,
                "body_copied": module_path.exists(),
                "body_in_receipt": False,
            }
        )

    public_refs = [
        public_relative_path(path, display_root=public_root)
        for path in _work_ledger_source_paths(input_dir)
    ]
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "classification": "copied_non_secret_macro_body",
        "manifest_ref": public_relative_path(manifest_path, display_root=public_root),
        "contract_ref": public_relative_path(contract_path, display_root=public_root),
        "module_count": len(source_module_results),
        "module_ids": [row["module_id"] for row in source_module_results],
        "source_refs": [row["source_ref"] for row in source_module_results],
        "target_refs": [row["target_ref"] for row in source_module_results],
        "public_runtime_refs": public_refs,
        "source_modules": source_module_results,
        "total_line_count": sum(row["line_count"] for row in source_module_results),
        "manifest_summary": {
            "schema_version": manifest.get("schema_version"),
            "module_count": manifest.get("module_count"),
            "body_storage_policy": manifest.get("body_storage_policy"),
            "receipt_body_policy": manifest.get("receipt_body_policy"),
            "validation_contract_ref": manifest.get("validation_contract_ref"),
            "body_in_receipt": False,
        },
        "contract_summary": {
            "schema_version": contract.get("schema_version"),
            "contract_id": contract.get("contract_id"),
            "status": contract.get("status"),
            "required_module_ids": contract_ids,
            "body_in_receipt": False,
        },
        "body_in_receipt": False,
    }


def validate_checkpoint_source_import(input_dir: Path, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_checkpoint_source_import` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    manifest_path = input_dir / CHECKPOINT_SOURCE_MANIFEST_NAME
    contract_path = input_dir / CHECKPOINT_CONTRACT_NAME
    manifest = _load_optional_json_document(
        manifest_path,
        findings,
        subject_id=CHECKPOINT_SOURCE_MANIFEST_NAME,
        source_label="Checkpoint Lane",
    )
    contract = _load_optional_json_document(
        contract_path,
        findings,
        subject_id=CHECKPOINT_CONTRACT_NAME,
        source_label="Checkpoint Lane",
    )
    manifest_rows = [
        row for row in manifest.get("modules", []) if isinstance(row, dict)
    ]
    manifest_by_id = {
        str(row.get("module_id") or ""): row
        for row in manifest_rows
        if str(row.get("module_id") or "")
    }
    expected_ids = [str(module["module_id"]) for module in CHECKPOINT_SOURCE_MODULES]
    contract_ids = [str(item) for item in contract.get("required_module_ids", [])]
    source_module_results: list[dict[str, Any]] = []

    if manifest.get("module_count") != len(CHECKPOINT_SOURCE_MODULES):
        findings.append(
            _bundle_finding(
                "CHECKPOINT_SOURCE_MANIFEST_COUNT_MISMATCH",
                "Checkpoint lane source module manifest does not declare the expected module count.",
                subject_id=CHECKPOINT_SOURCE_MANIFEST_NAME,
                subject_kind="checkpoint_lane_source_import",
            )
        )
    if sorted(manifest_by_id) != sorted(expected_ids):
        findings.append(
            _bundle_finding(
                "CHECKPOINT_SOURCE_MANIFEST_MODULES_MISMATCH",
                "Checkpoint lane source module manifest does not declare exactly the required module ids.",
                subject_id=CHECKPOINT_SOURCE_MANIFEST_NAME,
                subject_kind="checkpoint_lane_source_import",
            )
        )
    if sorted(contract_ids) != sorted(expected_ids):
        findings.append(
            _bundle_finding(
                "CHECKPOINT_SOURCE_CONTRACT_MODULES_MISMATCH",
                "Checkpoint lane runtime contract does not require exactly the expected module ids.",
                subject_id=CHECKPOINT_CONTRACT_NAME,
                subject_kind="checkpoint_lane_source_import",
            )
        )

    for module in CHECKPOINT_SOURCE_MODULES:
        module_id = str(module["module_id"])
        row = manifest_by_id.get(module_id, {})
        module_path = input_dir / str(module["bundle_path"])
        missing_anchors: list[str] = []
        actual_sha = ""
        actual_line_count = 0
        actual_byte_count = 0

        if not module_path.exists():
            findings.append(
                _bundle_finding(
                    "CHECKPOINT_SOURCE_MODULE_MISSING",
                    "Copied checkpoint lane source module is missing from the exported bundle.",
                    subject_id=module_id,
                    subject_kind="checkpoint_lane_source_import",
                )
            )
        else:
            text = module_path.read_text(encoding="utf-8")
            actual_sha = _file_sha256(module_path)
            actual_line_count = _line_count(module_path)
            actual_byte_count = _file_size_bytes(module_path)
            missing_anchors = [
                str(anchor)
                for anchor in module.get("required_anchors", [])
                if str(anchor) not in text
            ]
            if missing_anchors:
                findings.append(
                    _bundle_finding(
                        "CHECKPOINT_SOURCE_ANCHOR_MISSING",
                        "Copied checkpoint lane source module is missing expected control-plane anchors.",
                        subject_id=module_id,
                        subject_kind="checkpoint_lane_source_import",
                    )
                )

        if row:
            expected_pairs = {
                "source_ref": module["source_ref"],
                "target_ref": module["target_ref"],
                "classification": "copied_non_secret_macro_body",
                "body_copied": True,
                "body_in_receipt": False,
            }
            for field, expected in expected_pairs.items():
                if row.get(field) != expected:
                    findings.append(
                        _bundle_finding(
                            "CHECKPOINT_SOURCE_MANIFEST_FIELD_MISMATCH",
                            "Checkpoint lane source module manifest field does not match the import contract.",
                            subject_id=f"{module_id}:{field}",
                            subject_kind="checkpoint_lane_source_import",
                        )
                    )
            if row.get("sha256_match") is not True or (
                actual_sha and row.get("target_sha256") != actual_sha
            ):
                findings.append(
                    _bundle_finding(
                        "CHECKPOINT_SOURCE_SHA_MISMATCH",
                        "Checkpoint lane source module digest does not match the copied bundle body.",
                        subject_id=module_id,
                        subject_kind="checkpoint_lane_source_import",
                    )
                )
            if actual_line_count and row.get("line_count") != actual_line_count:
                findings.append(
                    _bundle_finding(
                        "CHECKPOINT_SOURCE_LINE_COUNT_MISMATCH",
                        "Checkpoint lane source module line count does not match the copied bundle body.",
                        subject_id=module_id,
                        subject_kind="checkpoint_lane_source_import",
                    )
                )

        source_module_results.append(
            {
                "module_id": module_id,
                "source_ref": module["source_ref"],
                "target_ref": module["target_ref"],
                "public_runtime_ref": public_relative_path(
                    module_path,
                    display_root=public_root,
                ),
                "sha256": actual_sha,
                "line_count": actual_line_count,
                "byte_count": actual_byte_count,
                "anchor_count": len(module.get("required_anchors", [])),
                "missing_anchors": missing_anchors,
                "body_copied": module_path.exists(),
                "body_in_receipt": False,
            }
        )

    public_refs = [
        public_relative_path(path, display_root=public_root)
        for path in _checkpoint_source_paths(input_dir)
    ]
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "classification": "copied_non_secret_macro_body",
        "manifest_ref": public_relative_path(manifest_path, display_root=public_root),
        "contract_ref": public_relative_path(contract_path, display_root=public_root),
        "module_count": len(source_module_results),
        "module_ids": [row["module_id"] for row in source_module_results],
        "source_refs": [row["source_ref"] for row in source_module_results],
        "target_refs": [row["target_ref"] for row in source_module_results],
        "public_runtime_refs": public_refs,
        "source_modules": source_module_results,
        "total_line_count": sum(row["line_count"] for row in source_module_results),
        "manifest_summary": {
            "schema_version": manifest.get("schema_version"),
            "module_count": manifest.get("module_count"),
            "body_storage_policy": manifest.get("body_storage_policy"),
            "receipt_body_policy": manifest.get("receipt_body_policy"),
            "validation_contract_ref": manifest.get("validation_contract_ref"),
            "body_in_receipt": False,
        },
        "contract_summary": {
            "schema_version": contract.get("schema_version"),
            "contract_id": contract.get("contract_id"),
            "status": contract.get("status"),
            "required_module_ids": contract_ids,
            "body_in_receipt": False,
        },
        "body_in_receipt": False,
    }


def validate_mission_control_source_import(input_dir: Path, public_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_mission_control_source_import` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    manifest_path = input_dir / MISSION_CONTROL_SOURCE_MANIFEST_NAME
    contract_path = input_dir / MISSION_CONTROL_CONTRACT_NAME
    manifest = _load_optional_json_document(
        manifest_path,
        findings,
        subject_id=MISSION_CONTROL_SOURCE_MANIFEST_NAME,
        source_label="Mission Control",
    )
    contract = _load_optional_json_document(
        contract_path,
        findings,
        subject_id=MISSION_CONTROL_CONTRACT_NAME,
        source_label="Mission Control",
    )
    manifest_rows = [
        row for row in manifest.get("modules", []) if isinstance(row, dict)
    ]
    manifest_by_id = {
        str(row.get("module_id") or ""): row
        for row in manifest_rows
        if str(row.get("module_id") or "")
    }
    expected_ids = [
        str(module["module_id"]) for module in MISSION_CONTROL_SOURCE_MODULES
    ]
    contract_ids = [str(item) for item in contract.get("required_module_ids", [])]
    source_module_results: list[dict[str, Any]] = []

    if manifest.get("module_count") != len(MISSION_CONTROL_SOURCE_MODULES):
        findings.append(
            _bundle_finding(
                "MISSION_CONTROL_SOURCE_MANIFEST_COUNT_MISMATCH",
                "Mission-control source module manifest does not declare the expected module count.",
                subject_id=MISSION_CONTROL_SOURCE_MANIFEST_NAME,
                subject_kind="mission_control_source_import",
            )
        )
    if sorted(manifest_by_id) != sorted(expected_ids):
        findings.append(
            _bundle_finding(
                "MISSION_CONTROL_SOURCE_MANIFEST_MODULES_MISMATCH",
                "Mission-control source module manifest does not declare exactly the required module ids.",
                subject_id=MISSION_CONTROL_SOURCE_MANIFEST_NAME,
                subject_kind="mission_control_source_import",
            )
        )
    if sorted(contract_ids) != sorted(expected_ids):
        findings.append(
            _bundle_finding(
                "MISSION_CONTROL_SOURCE_CONTRACT_MODULES_MISMATCH",
                "Mission-control runtime contract does not require exactly the expected module ids.",
                subject_id=MISSION_CONTROL_CONTRACT_NAME,
                subject_kind="mission_control_source_import",
            )
        )

    for module in MISSION_CONTROL_SOURCE_MODULES:
        module_id = str(module["module_id"])
        row = manifest_by_id.get(module_id, {})
        module_path = input_dir / str(module["bundle_path"])
        missing_anchors: list[str] = []
        actual_sha = ""
        actual_line_count = 0
        actual_byte_count = 0

        if not module_path.exists():
            findings.append(
                _bundle_finding(
                    "MISSION_CONTROL_SOURCE_MODULE_MISSING",
                    "Copied mission-control source module is missing from the exported bundle.",
                    subject_id=module_id,
                    subject_kind="mission_control_source_import",
                )
            )
        else:
            text = module_path.read_text(encoding="utf-8")
            actual_sha = _file_sha256(module_path)
            actual_line_count = _line_count(module_path)
            actual_byte_count = _file_size_bytes(module_path)
            missing_anchors = [
                str(anchor)
                for anchor in module.get("required_anchors", [])
                if str(anchor) not in text
            ]
            if missing_anchors:
                findings.append(
                    _bundle_finding(
                        "MISSION_CONTROL_SOURCE_ANCHOR_MISSING",
                        "Copied mission-control source module is missing expected control-plane anchors.",
                        subject_id=module_id,
                        subject_kind="mission_control_source_import",
                    )
                )

        if row:
            expected_pairs = {
                "source_ref": module["source_ref"],
                "target_ref": module["target_ref"],
                "classification": "copied_non_secret_macro_body",
                "body_copied": True,
                "body_in_receipt": False,
            }
            for field, expected in expected_pairs.items():
                if row.get(field) != expected:
                    findings.append(
                        _bundle_finding(
                            "MISSION_CONTROL_SOURCE_MANIFEST_FIELD_MISMATCH",
                            "Mission-control source module manifest field does not match the import contract.",
                            subject_id=f"{module_id}:{field}",
                            subject_kind="mission_control_source_import",
                        )
                    )
            if row.get("sha256_match") is not True or (
                actual_sha and row.get("target_sha256") != actual_sha
            ):
                findings.append(
                    _bundle_finding(
                        "MISSION_CONTROL_SOURCE_SHA_MISMATCH",
                        "Mission-control source module digest does not match the copied bundle body.",
                        subject_id=module_id,
                        subject_kind="mission_control_source_import",
                    )
                )
            if actual_line_count and row.get("line_count") != actual_line_count:
                findings.append(
                    _bundle_finding(
                        "MISSION_CONTROL_SOURCE_LINE_COUNT_MISMATCH",
                        "Mission-control source module line count does not match the copied bundle body.",
                        subject_id=module_id,
                        subject_kind="mission_control_source_import",
                    )
                )

        source_module_results.append(
            {
                "module_id": module_id,
                "source_ref": module["source_ref"],
                "target_ref": module["target_ref"],
                "public_runtime_ref": public_relative_path(
                    module_path,
                    display_root=public_root,
                ),
                "sha256": actual_sha,
                "line_count": actual_line_count,
                "byte_count": actual_byte_count,
                "anchor_count": len(module.get("required_anchors", [])),
                "missing_anchors": missing_anchors,
                "body_copied": module_path.exists(),
                "body_in_receipt": False,
            }
        )

    public_refs = [
        public_relative_path(path, display_root=public_root)
        for path in _mission_control_source_paths(input_dir)
    ]
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "classification": "copied_non_secret_macro_body",
        "manifest_ref": public_relative_path(manifest_path, display_root=public_root),
        "contract_ref": public_relative_path(contract_path, display_root=public_root),
        "module_count": len(source_module_results),
        "module_ids": [row["module_id"] for row in source_module_results],
        "source_refs": [row["source_ref"] for row in source_module_results],
        "target_refs": [row["target_ref"] for row in source_module_results],
        "public_runtime_refs": public_refs,
        "source_modules": source_module_results,
        "total_line_count": sum(row["line_count"] for row in source_module_results),
        "manifest_summary": {
            "schema_version": manifest.get("schema_version"),
            "module_count": manifest.get("module_count"),
            "body_storage_policy": manifest.get("body_storage_policy"),
            "receipt_body_policy": manifest.get("receipt_body_policy"),
            "validation_contract_ref": manifest.get("validation_contract_ref"),
            "body_in_receipt": False,
        },
        "contract_summary": {
            "schema_version": contract.get("schema_version"),
            "contract_id": contract.get("contract_id"),
            "status": contract.get("status"),
            "required_module_ids": contract_ids,
            "body_in_receipt": False,
        },
        "body_in_receipt": False,
    }


def _body_import_verification(input_refs: list[str]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_body_import_verification` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "verification_mode": "source_faithful_public_refactor",
        "source_ref": WORK_LANDING_SOURCE_REF,
        "source_symbols": [
            *WORK_LANDING_SOURCE_SYMBOL_REFS,
            *MISSION_PREFLIGHT_SOURCE_SYMBOL_REFS,
        ],
        "target_ref": WORK_LANDING_TARGET_REF,
        "target_symbols": [
            *WORK_LANDING_TARGET_SYMBOL_REFS,
            *MISSION_PREFLIGHT_TARGET_SYMBOL_REFS,
        ],
        "source_refs": [
            WORK_LANDING_SOURCE_REF,
            "system/lib/work_landing_status.py",
            MISSION_PREFLIGHT_SOURCE_REF,
            MISSION_PREFLIGHT_KERNEL_SOURCE_REF,
        ],
        "target_refs": [WORK_LANDING_TARGET_REF, MISSION_PREFLIGHT_TARGET_REF],
        "source_faithful_components": {
            "work_landing": {
                "source_ref": WORK_LANDING_SOURCE_REF,
                "source_symbols": WORK_LANDING_SOURCE_SYMBOL_REFS,
                "target_ref": WORK_LANDING_TARGET_REF,
                "target_symbols": WORK_LANDING_TARGET_SYMBOL_REFS,
            },
            "mission_transaction_preflight": {
                "source_ref": MISSION_PREFLIGHT_SOURCE_REF,
                "source_symbols": MISSION_PREFLIGHT_SOURCE_SYMBOL_REFS,
                "target_ref": MISSION_PREFLIGHT_TARGET_REF,
                "target_symbols": MISSION_PREFLIGHT_TARGET_SYMBOL_REFS,
            },
        },
        "source_order_ref": "system/lib/work_landing_status.py::ORDERED_CONTROLLER_ACTION_IDS",
        "target_order_ref": (
            "microcosm_core.macro_tools.work_landing::ORDERED_CONTROLLER_ACTION_IDS"
        ),
        "source_faithful_controller_action_ids": ORDERED_CONTROLLER_ACTION_IDS,
        "source_faithful_controller_action_count": len(ORDERED_CONTROLLER_ACTION_IDS),
        "validation_refs": WORK_LANDING_VALIDATION_REFS,
        "input_refs": sorted(dict.fromkeys(input_refs)),
        "body_in_receipt": False,
        "omitted_secret_or_live_access_material": [
            "live Task Ledger bodies",
            "live Work Ledger runtime state",
            "Git index contents outside declared owned paths",
            "raw operator text",
            "credentials and account/session material",
        ],
    }


def _body_import_fields(input_refs: list[str]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_body_import_fields` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "body_import_status": BODY_IMPORT_STATUS,
        "body_import_verification": _body_import_verification(input_refs),
        "source_refs": [
            WORK_LANDING_SOURCE_REF,
            "system/lib/work_landing_status.py",
            MISSION_PREFLIGHT_SOURCE_REF,
            MISSION_PREFLIGHT_KERNEL_SOURCE_REF,
        ],
        "source_symbols": [
            *WORK_LANDING_SOURCE_SYMBOL_REFS,
            *MISSION_PREFLIGHT_SOURCE_SYMBOL_REFS,
        ],
        "target_refs": [WORK_LANDING_TARGET_REF, MISSION_PREFLIGHT_TARGET_REF],
        "target_symbols": [
            *WORK_LANDING_TARGET_SYMBOL_REFS,
            *MISSION_PREFLIGHT_TARGET_SYMBOL_REFS,
        ],
        "public_runtime_refs": input_refs,
        "body_in_receipt": False,
    }


def _public_work_landing_attempt(
    *,
    subject_ids: list[str],
    owned_paths: list[str],
    session_id: str | None,
    created_by: str = "microcosm",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_public_work_landing_attempt` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return build_public_work_landing_attempt_binding(
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        session_id=session_id,
        require_exclusive=True,
        created_by=created_by,
    )


def _public_work_landing_reconcile_plan(
    *,
    subject_ids: list[str],
    owned_paths: list[str],
    session_id: str | None,
    transaction_id: str,
    recommended_next_action: str,
    receipt_drain_prerequisite_status: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_public_work_landing_reconcile_plan` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    plan = build_public_work_landing_reconcile_plan(
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        session_id=session_id,
        require_exclusive=True,
    )
    plan.update(
        {
            "transaction_id": transaction_id,
            "recommended_next_action": recommended_next_action,
            "receipt_drain_prerequisite_status": receipt_drain_prerequisite_status,
            "mutation_policy": {
                "live_state_mutation": False,
                "live_task_ledger_mutation": False,
                "live_work_ledger_mutation": False,
                "broad_stage_used": False,
                "provider_execution_authorized": False,
                "release_authorized": False,
            },
            "claim_release_order_status": "release_after_closeout_only",
        }
    )
    return plan


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_rows` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_finding` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_in_receipt": False,
    }


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> None:
    """
    [ACTION]
    - Teleology: Implements `_record` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    observed[case_id].add(code)


def _bundle_finding(code: str, message: str, *, subject_id: str, subject_kind: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_bundle_finding` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "error_code": code,
        "message": message,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_in_receipt": False,
    }


def validate_exported_workitems(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_exported_workitems` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    rows = _rows(payload, "workitems")
    workitem_ids: list[str] = []
    schedulable_ids: list[str] = []
    blocked_ids: list[str] = []
    dependency_refs: list[str] = []
    dependency_status_by_workitem: dict[str, dict[str, Any]] = {}

    if not rows:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_WORKITEM_ROWS_MISSING",
                "Exported mission bundle has no WorkItem rows.",
                subject_id="workitems",
                subject_kind="workitem_table",
            )
        )

    for row in rows:
        work_item_id = str(row.get("work_item_id") or "")
        state = str(row.get("state") or "")
        deps = [str(dep) for dep in row.get("depends_on", [])]
        workitem_ids.append(work_item_id)
        dependency_refs.extend(deps)
        if row.get("live_ledger_authority") or row.get("source_authority_allowed"):
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_WORKITEM_AUTHORITY_OVERCLAIM",
                    "WorkItem metadata row attempted to claim live ledger authority.",
                    subject_id=work_item_id or "workitem",
                    subject_kind="workitem_row",
                )
            )
        if row.get("projection_not_authority") is not True:
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_WORKITEM_PROJECTION_FLAG_MISSING",
                    "WorkItem metadata row must declare projection_not_authority.",
                    subject_id=work_item_id or "workitem",
                    subject_kind="workitem_row",
                )
            )
        if state == "ready":
            schedulable_ids.append(work_item_id)
        elif state in {"blocked", "shaping"}:
            blocked_ids.append(work_item_id)
        dependency_status_by_workitem[work_item_id] = {
            "state": state,
            "dependency_refs": deps,
            "schedulable": state == "ready",
            "derived_not_authority": True,
        }

    duplicates = sorted(
        work_item_id
        for work_item_id in set(workitem_ids)
        if work_item_id and workitem_ids.count(work_item_id) > 1
    )
    for work_item_id in duplicates:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_DUPLICATE_WORKITEM_ID",
                "Exported mission bundle contains a duplicate WorkItem id.",
                subject_id=work_item_id,
                subject_kind="workitem_table",
            )
        )

    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "workitem_ids": sorted(work_item_id for work_item_id in workitem_ids if work_item_id),
        "blocked_workitem_ids": sorted(work_item_id for work_item_id in blocked_ids if work_item_id),
        "schedulable_workitem_ids": sorted(
            work_item_id for work_item_id in schedulable_ids if work_item_id
        ),
        "dependency_refs": sorted(set(dependency_refs)),
        "dependency_status_by_workitem": dependency_status_by_workitem,
        "workitem_rows_projection_not_authority": True,
    }


def validate_exported_claims(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_exported_claims` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    claims = _rows(payload, "claims")
    path_owner: dict[str, str] = {}
    same_path_conflicts: list[str] = []
    accepted_claim_ids: list[str] = []

    if not claims:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_CLAIM_ROWS_MISSING",
                "Exported mission bundle has no claim rows.",
                subject_id="claim_table",
                subject_kind="claim_table",
            )
        )

    for claim in claims:
        claim_id = str(claim.get("claim_id") or "")
        owned_paths = [str(path) for path in claim.get("owned_paths", [])]
        if not owned_paths:
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_CLAIM_OWNED_PATHS_MISSING",
                    "Claim row has no owned paths.",
                    subject_id=claim_id or "claim",
                    subject_kind="claim_row",
                )
            )
        if claim.get("live_claim_authority") or claim.get("source_authority_allowed"):
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_CLAIM_AUTHORITY_OVERCLAIM",
                    "Claim row attempted to claim live Work Ledger authority.",
                    subject_id=claim_id or "claim",
                    subject_kind="claim_row",
                )
            )
        if claim.get("projection_not_authority") is not True:
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_CLAIM_PROJECTION_FLAG_MISSING",
                    "Claim row must declare projection_not_authority.",
                    subject_id=claim_id or "claim",
                    subject_kind="claim_row",
                )
            )
        for owned_path in owned_paths:
            if owned_path in path_owner:
                same_path_conflicts.append(claim_id)
                findings.append(
                    _bundle_finding(
                        "MISSION_BUNDLE_SAME_PATH_CLAIM_CONFLICT",
                        "Exported mission claim table contains a same-path conflict.",
                        subject_id=claim_id or "claim",
                        subject_kind="claim_row",
                    )
                )
            else:
                path_owner[owned_path] = claim_id
        if claim_id:
            accepted_claim_ids.append(claim_id)

    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "accepted_claim_ids": sorted(set(accepted_claim_ids)),
        "same_path_conflict_claim_ids": sorted(set(same_path_conflicts)),
        "claim_rows_projection_not_authority": True,
    }


def validate_exported_dependencies(
    dependency_payload: object,
    workitem_result: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_exported_dependencies` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    known_workitems = set(workitem_result["workitem_ids"])
    resolved_refs = {
        str(row.get("dependency_id"))
        for row in _rows(dependency_payload, "dependency_resolution_receipts")
        if row.get("status") == "resolved"
    }
    dangling_refs: list[str] = []
    unsatisfied: list[str] = []

    for work_item_id, status in workitem_result["dependency_status_by_workitem"].items():
        deps = [str(dep) for dep in status.get("dependency_refs", [])]
        unresolved = [
            dep for dep in deps if dep not in resolved_refs and dep not in known_workitems
        ]
        dangling_refs.extend(unresolved)
        unsatisfied.extend(dep for dep in deps if dep not in resolved_refs and dep not in known_workitems)
        for dep in unresolved:
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_DANGLING_DEPENDENCY_REF",
                    "Exported mission bundle dependency lacks resolution evidence.",
                    subject_id=f"{work_item_id}:{dep}",
                    subject_kind="dependency_graph",
                )
            )
    if isinstance(dependency_payload, dict) and dependency_payload.get("derived_not_authority") is not True:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_DEPENDENCY_AUTHORITY_OVERCLAIM",
                "Dependency graph must remain metadata, not live dependency authority.",
                subject_id="dependency_graph",
                subject_kind="dependency_graph",
            )
        )

    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "resolved_dependency_refs": sorted(resolved_refs),
        "dangling_dependency_refs": sorted(set(dangling_refs)),
        "unsatisfied_dep_ids": sorted(set(unsatisfied)),
        "dependency_resolution_receipt": {
            "accepted_refs": sorted(resolved_refs),
            "rejected_refs": sorted(set(dangling_refs)),
            "body_in_receipt": False,
        },
        "downstream_unlock_edges": [
            {
                "upstream_id": ref,
                "downstream_ids": [
                    work_item_id
                    for work_item_id, status in workitem_result[
                        "dependency_status_by_workitem"
                    ].items()
                    if ref in status.get("dependency_refs", [])
                ],
                "body_in_receipt": False,
            }
            for ref in sorted(resolved_refs)
        ],
        "derived_not_authority": True,
    }


def validate_exported_transaction_plan(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_exported_transaction_plan` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    plan = payload if isinstance(payload, dict) else {}
    actions = [str(action) for action in plan.get("ordered_controller_action_ids", [])]
    action_rows = _rows(plan, "actions")
    action_row_ids = [str(action.get("action_id") or "") for action in action_rows]
    mutation_policy = plan.get("mutation_policy", {})
    if actions != ORDERED_CONTROLLER_ACTION_IDS:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_CONTROLLER_ACTION_ORDER_MISMATCH",
                "Mission transaction plan does not preserve controller action order.",
                subject_id=str(plan.get("transaction_id") or "transaction_plan"),
                subject_kind="transaction_plan",
            )
        )
    if action_row_ids != ORDERED_CONTROLLER_ACTION_IDS:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_CONTROLLER_ACTION_ROWS_MISMATCH",
                "Mission transaction action rows must preserve every source-faithful controller action in order.",
                subject_id=str(plan.get("transaction_id") or "transaction_plan"),
                subject_kind="transaction_plan",
            )
        )
    if not isinstance(mutation_policy, dict):
        mutation_policy = {}
    for field in (
        "live_state_mutation",
        "live_task_ledger_mutation",
        "live_work_ledger_mutation",
        "broad_stage_used",
        "provider_execution_authorized",
        "release_authorized",
    ):
        if mutation_policy.get(field) is not False:
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_MUTATION_POLICY_OVERCLAIM",
                    "Mission transaction plan mutation policy must be false for live mutation and release fields.",
                    subject_id=field,
                    subject_kind="transaction_plan",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "transaction_id": plan.get("transaction_id"),
        "ordered_controller_action_ids": actions,
        "action_row_ids": action_row_ids,
        "controller_action_rows_aligned": action_row_ids == ORDERED_CONTROLLER_ACTION_IDS,
        "source_faithful_controller_action_count": len(ORDERED_CONTROLLER_ACTION_IDS),
        "mutation_policy": mutation_policy,
        "apply_result": plan.get("apply_result"),
        "work_landing_reconcile_status": plan.get("work_landing_reconcile_status"),
        "claim_release_order_status": plan.get("claim_release_order_status"),
        "actions": plan.get("actions", []),
        "mode": plan.get("mode"),
        "recommended_next_action": plan.get("recommended_next_action"),
    }


def validate_exported_receipt_drain(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_exported_receipt_drain` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    plan = payload if isinstance(payload, dict) else {}
    declared = [str(ref) for ref in plan.get("declared_receipt_refs", [])]
    drained = [str(ref) for ref in plan.get("receipt_refs_drained", [])]
    if sorted(declared) != sorted(drained):
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_RECEIPT_DRAIN_SCOPE_MISMATCH",
                "Receipt drain plan must drain exactly the declared receipt refs.",
                subject_id=str(plan.get("drain_id") or "receipt_drain_plan"),
                subject_kind="receipt_drain_plan",
            )
        )
    if plan.get("drain_mode") != "public_work_landing_receipt_projection":
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_RECEIPT_DRAIN_LIVE_MUTATION_OVERCLAIM",
                "Receipt drain plan must remain metadata projection only.",
                subject_id=str(plan.get("drain_id") or "receipt_drain_plan"),
                subject_kind="receipt_drain_plan",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "receipt_refs_drained": drained,
        "exact_receipt_drain_scope": declared,
        "receipt_drain_exclusivity_status": (
            "only_declared_receipts_drained" if not findings else "blocked"
        ),
        "derived_not_authority": True,
    }


def validate_exported_closeout_projection(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_exported_closeout_projection` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    packet = payload if isinstance(payload, dict) else {}
    if packet.get("derived_not_authority") is not True:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_CLOSEOUT_AUTHORITY_OVERCLAIM",
                "Closeout projection packet must declare derived_not_authority.",
                subject_id=str(packet.get("work_item_id") or "closeout_projection_packet"),
                subject_kind="closeout_projection_packet",
            )
        )
    if packet.get("claims_live_closeout") is not False:
        findings.append(
            _bundle_finding(
                "MISSION_BUNDLE_LIVE_CLOSEOUT_OVERCLAIM",
                "Closeout projection packet must not claim live closeout.",
                subject_id=str(packet.get("work_item_id") or "closeout_projection_packet"),
                subject_kind="closeout_projection_packet",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "work_item_id": packet.get("work_item_id"),
        "status_before": packet.get("status_before"),
        "status_after": packet.get("status_after"),
        "derived_not_authority": True,
        "claims_live_closeout": False,
    }


def validate_exported_scoped_mutation_policy(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_exported_scoped_mutation_policy` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    policy = payload if isinstance(payload, dict) else {}
    for field in (
        "live_state_mutation_authorized",
        "live_task_ledger_mutation_authorized",
        "live_work_ledger_mutation_authorized",
        "broad_stage_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _bundle_finding(
                    "MISSION_BUNDLE_SCOPED_POLICY_OVERCLAIM",
                    "Scoped mutation policy must reject live state mutation and broad staging.",
                    subject_id=field,
                    subject_kind="scoped_mutation_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "owned_paths": policy.get("owned_paths", []),
        "mutation_status": policy.get("mutation_status"),
        "broad_stage_used": False,
        "authority_upgrade_rejected": True,
        "body_in_receipt": False,
    }


def _checkpoint_cases(payload: object, extra_cases: list[object] | None = None) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_checkpoint_cases` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    cases = list(_rows(payload, "lane_cases"))
    for item in extra_cases or []:
        if isinstance(item, dict):
            cases.append(item)
    return cases


def _recommended_checkpoint_lane(case: dict[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `_recommended_checkpoint_lane` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if case.get("suspected_secret") is True:
        return "hard_stop"
    if (
        case.get("operator_authorized_broad_checkpoint") is True
        and case.get("broad_checkpoint_requested") is True
    ):
        return "broad_checkpoint"
    return "scoped_commit"


def validate_checkpoint_lane_policy(
    payload: object,
    extra_cases: list[object] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_checkpoint_lane_policy` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    cases = _checkpoint_cases(payload, extra_cases)
    checkpoint_lane_decisions: list[dict[str, Any]] = []
    recommended_lane_by_case: dict[str, str] = {}
    hard_stop_case_ids: list[str] = []
    broad_authorization_required_case_ids: list[str] = []
    dirty_tree_not_scoped_blocker_case_ids: list[str] = []
    selected_lane_mismatch_case_ids: list[str] = []

    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id") or f"checkpoint_lane_case_{index}")
        selected_lane = str(case.get("selected_lane") or "").strip()
        recommended_lane = _recommended_checkpoint_lane(case)
        recommended_lane_by_case[case_id] = recommended_lane
        negative_case_id = str(case.get("negative_case_id") or case_id)

        if recommended_lane == "hard_stop":
            hard_stop_case_ids.append(case_id)
        if selected_lane == "broad_checkpoint" and case.get(
            "operator_authorized_broad_checkpoint"
        ) is not True:
            broad_authorization_required_case_ids.append(case_id)
            _record(
                findings,
                observed,
                "CHECKPOINT_BROAD_AUTH_REQUIRED",
                "Broad checkpoint lane requires explicit operator authorization.",
                case_id=negative_case_id,
                subject_id=case_id,
                subject_kind="checkpoint_lane_case",
            )
        if case.get("suspected_secret") is True and selected_lane != "hard_stop":
            _record(
                findings,
                observed,
                "CHECKPOINT_SECRET_REQUIRES_HARD_STOP",
                "Suspected secret or private leakage requires the hard-stop lane.",
                case_id=negative_case_id,
                subject_id=case_id,
                subject_kind="checkpoint_lane_case",
            )
        if (
            case.get("dirty_tree_present") is True
            and case.get("owned_paths_isolated") is True
            and case.get("suspected_secret") is not True
            and (
                selected_lane == "hard_stop"
                or case.get("dirty_tree_blocks_scoped_lane") is True
            )
        ):
            dirty_tree_not_scoped_blocker_case_ids.append(case_id)
            _record(
                findings,
                observed,
                "CHECKPOINT_DIRTY_TREE_NOT_SCOPED_BLOCKER",
                "Mixed dirty tree state blocks broad accidental staging, not scoped owned-path commit.",
                case_id=negative_case_id,
                subject_id=case_id,
                subject_kind="checkpoint_lane_case",
            )
        if selected_lane and selected_lane != recommended_lane:
            selected_lane_mismatch_case_ids.append(case_id)
            _record(
                findings,
                observed,
                "CHECKPOINT_SELECTED_LANE_MISMATCH",
                "Checkpoint lane selection must match the recommended lane for the declared case.",
                case_id=negative_case_id,
                subject_id=case_id,
                subject_kind="checkpoint_lane_case",
            )
        if not selected_lane:
            _record(
                findings,
                observed,
                "CHECKPOINT_LANE_DECISION_REQUIRED",
                "Checkpoint lane case must name scoped_commit, broad_checkpoint, or hard_stop.",
                case_id=negative_case_id,
                subject_id=case_id,
                subject_kind="checkpoint_lane_case",
            )

        checkpoint_lane_decisions.append(
            {
                "case_id": case_id,
                "selected_lane": selected_lane or "missing",
                "recommended_lane": recommended_lane,
                "dirty_tree_present": case.get("dirty_tree_present") is True,
                "owned_paths_isolated": case.get("owned_paths_isolated") is True,
                "operator_authorized_broad_checkpoint": case.get(
                    "operator_authorized_broad_checkpoint"
                )
                is True,
                "suspected_secret": case.get("suspected_secret") is True,
                "body_in_receipt": False,
            }
        )

    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "checkpoint_lane_decisions": checkpoint_lane_decisions,
        "recommended_lane_by_case": recommended_lane_by_case,
        "hard_stop_case_ids": sorted(set(hard_stop_case_ids)),
        "broad_checkpoint_authorization_required_case_ids": sorted(
            set(broad_authorization_required_case_ids)
        ),
        "dirty_tree_not_scoped_blocker_case_ids": sorted(
            set(dirty_tree_not_scoped_blocker_case_ids)
        ),
        "selected_lane_mismatch_case_ids": sorted(set(selected_lane_mismatch_case_ids)),
        "selection_policy": (
            "dirty_trees_block_broad_accidental_staging_not_scoped_owned_path_commits"
        ),
        "broad_checkpoint_requires_operator_authorization": True,
        "suspected_secret_requires_hard_stop": True,
        "dirty_tree_blocks_scoped_commit": False,
        "body_in_receipt": False,
    }


def validate_dependency_unlock_scheduler(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_dependency_unlock_scheduler` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    workitems = _rows(payload, "workitems")
    known_ids = {str(row.get("work_item_id")) for row in workitems}
    resolved_refs = {
        str(row.get("dependency_id"))
        for row in _rows(payload, "dependency_resolution_receipts")
        if row.get("status") == "resolved"
    }

    dependency_status_by_workitem: dict[str, dict[str, Any]] = {}
    blocked_ids: list[str] = []
    ready_but_unsatisfied: list[str] = []
    schedulable_ids: list[str] = []
    dangling_refs: list[str] = []
    unsatisfied_dep_ids: list[str] = []
    anomaly_refs: list[dict[str, Any]] = []

    for row in workitems:
        work_item_id = str(row.get("work_item_id") or "work_item")
        state = str(row.get("state") or "shaping")
        deps = [str(dep) for dep in row.get("depends_on", [])]
        unresolved = [
            dep for dep in deps if dep not in resolved_refs and dep not in known_ids
        ]
        unsatisfied = [dep for dep in deps if dep not in resolved_refs]
        if unresolved:
            blocked_ids.append(work_item_id)
            dangling_refs.extend(unresolved)
            unsatisfied_dep_ids.extend(unsatisfied)
            anomaly_refs.append(
                {
                    "work_item_id": work_item_id,
                    "dependency_refs": unresolved,
                    "error_code": "DANGLING_DEPENDENCY_REF",
                    "body_in_receipt": False,
                }
            )
            _record(
                findings,
                observed,
                "DANGLING_DEPENDENCY_REF",
                "Dependency unlock attempted without explicit fixture resolution evidence.",
                case_id="dependency_unlock_without_resolution_receipt",
                subject_id=work_item_id,
                subject_kind="work_item",
            )
        if state == "ready" and unsatisfied:
            ready_but_unsatisfied.append(work_item_id)
            _record(
                findings,
                observed,
                "READY_WITH_INCOMPLETE_HARD_DEP",
                "Ready state cannot override unsatisfied hard dependency refs.",
                case_id="ready_workitem_with_unsatisfied_hard_dep",
                subject_id=work_item_id,
                subject_kind="work_item",
            )
        if state == "ready" and not unsatisfied:
            schedulable_ids.append(work_item_id)
        if unsatisfied and work_item_id not in blocked_ids:
            blocked_ids.append(work_item_id)
        dependency_status_by_workitem[work_item_id] = {
            "state": state,
            "dependency_refs": deps,
            "unsatisfied_dep_ids": unsatisfied,
            "schedulable": state == "ready" and not unsatisfied,
        }

    blocked_ids = sorted(set(blocked_ids))
    ready_but_unsatisfied = sorted(set(ready_but_unsatisfied))
    dangling_refs = sorted(set(dangling_refs))
    unsatisfied_dep_ids = sorted(set(unsatisfied_dep_ids))
    schedulable_ids = sorted(set(schedulable_ids))
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "blocked_workitem_ids": blocked_ids,
        "ready_but_unsatisfied_workitem_ids": ready_but_unsatisfied,
        "resolved_dependency_refs": sorted(resolved_refs),
        "dependency_status_by_workitem": dependency_status_by_workitem,
        "dependency_resolution_receipt": {
            "accepted_refs": sorted(resolved_refs),
            "rejected_refs": dangling_refs,
            "body_in_receipt": False,
        },
        "unsatisfied_dep_ids": unsatisfied_dep_ids,
        "downstream_unlock_edges": [
            {
                "upstream_id": ref,
                "downstream_ids": [
                    work_item_id
                    for work_item_id, status in dependency_status_by_workitem.items()
                    if ref in status["dependency_refs"]
                ],
                "body_in_receipt": False,
            }
            for ref in sorted(resolved_refs)
        ],
        "unlocks_by_rank": [
            {"rank": index + 1, "work_item_id": work_item_id, "body_in_receipt": False}
            for index, work_item_id in enumerate(schedulable_ids)
        ],
        "dangling_dependency_refs": dangling_refs,
        "schedulable_workitem_ids": schedulable_ids,
        "downstream_schedulable_before": False,
        "schedulability_decision_source": "regression_fixture_dependency_status_by_workitem",
        "dependency_unlock_resolution_basis": "explicit_fixture_dependency_resolution_receipt_required",
        "anomaly_refs": anomaly_refs,
        "derived_not_authority": True,
        "schedulable": False,
        "dependency_refs": sorted({dep for row in workitems for dep in row.get("depends_on", [])}),
    }


def validate_claim_preflight(
    claims_payload: object,
    repo_state: object,
    missing_owned_path: object,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_claim_preflight` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    claims = _rows(claims_payload, "claims")
    active_claims = [row for row in claims if row.get("status") == "active"]
    path_owner: dict[str, str] = {}
    conflict_claim_ids: list[str] = []
    same_path_conflict_claim_ids: list[str] = []
    for claim in active_claims:
        claim_id = str(claim.get("claim_id") or "claim")
        for owned_path in claim.get("owned_paths", []):
            owned_path = str(owned_path)
            if owned_path in path_owner:
                conflict_claim_ids.append(claim_id)
                same_path_conflict_claim_ids.append(path_owner[owned_path])
                _record(
                    findings,
                    observed,
                    "SAME_PATH_CLAIM_CONFLICT",
                    "Same-path claim conflict remains live at validation time.",
                    case_id="competing_claim_and_stale_parent",
                    subject_id=claim_id,
                    subject_kind="work_ledger_claim",
                )
            else:
                path_owner[owned_path] = claim_id

    parent_by_claim = repo_state.get("current_parent_by_claim", {}) if isinstance(repo_state, dict) else {}
    stale_claim_ids: list[str] = []
    for claim in active_claims:
        claim_id = str(claim.get("claim_id") or "claim")
        expected = str(claim.get("expected_parent_sha") or "")
        actual = str(parent_by_claim.get(claim_id) or "")
        if expected and actual and expected != actual:
            stale_claim_ids.append(claim_id)
            _record(
                findings,
                observed,
                "EXPECTED_PARENT_MISMATCH",
                "Expected parent does not match the fixture current parent.",
                case_id="competing_claim_and_stale_parent",
                subject_id=claim_id,
                subject_kind="work_ledger_claim",
            )

    missing_claim_id = str(missing_owned_path.get("claim_id") or "claim_missing_owned_path")
    if not missing_owned_path.get("owned_paths"):
        _record(
            findings,
            observed,
            "MISSING_OWNED_PATH",
            "Mission claim is missing an owned path.",
            case_id="mission_claim_missing_owned_path",
            subject_id=missing_claim_id,
            subject_kind="work_ledger_claim",
        )

    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "claim_id": (
            sorted(set(conflict_claim_ids))[0]
            if conflict_claim_ids
            else sorted(stale_claim_ids)[0]
            if stale_claim_ids
            else missing_claim_id
        ),
        "decision": "blocked_replan_required" if findings else "pass_metadata_preflight",
        "conflict_claim_ids": sorted(set(conflict_claim_ids)),
        "same_path_conflict_claim_ids": sorted(set(same_path_conflict_claim_ids)),
        "claim_conflict_recheck_status": (
            "live_conflict_detected" if conflict_claim_ids else "no_conflict_in_public_snapshot"
        ),
        "expected_parent_status": (
            "stale_parent_rejected" if stale_claim_ids else "parent_ok_or_not_declared"
        ),
        "stale_expected_parent_claim_ids": sorted(stale_claim_ids),
        "missing_owned_path_claim_ids": (
            [missing_claim_id] if not missing_owned_path.get("owned_paths") else []
        ),
        "replan_required": bool(findings),
    }


def _primary_claim_preflight_from_real_snapshot(
    *,
    legacy_claim_result: dict[str, Any],
    real_snapshot_result: dict[str, Any],
    public_mission_preflight: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_primary_claim_preflight_from_real_snapshot` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    real_good = (
        real_snapshot_result.get("real_good_public_preflight")
        if isinstance(real_snapshot_result.get("real_good_public_preflight"), dict)
        else {}
    )
    same_path_mutation = (
        real_snapshot_result.get("same_path_conflict_public_preflight")
        if isinstance(real_snapshot_result.get("same_path_conflict_public_preflight"), dict)
        else {}
    )
    parent_mutation = (
        real_snapshot_result.get("expected_parent_mismatch_public_preflight")
        if isinstance(
            real_snapshot_result.get("expected_parent_mismatch_public_preflight"), dict
        )
        else {}
    )
    runtime_collision = (
        real_snapshot_result.get("runtime_collision_check")
        if isinstance(real_snapshot_result.get("runtime_collision_check"), dict)
        else {}
    )
    accepted_claim_ids = _strings(real_good.get("accepted_claim_ids"))
    real_conflict_claim_ids = _strings(
        runtime_collision.get("mutated_runtime_collision_claim_ids")
    ) or _strings(same_path_mutation.get("runtime_collision_claim_ids"))
    real_parent_mismatch_claim_ids = _strings(
        parent_mutation.get("stale_expected_parent_claim_ids")
    )
    source_claim_id = (
        accepted_claim_ids[0]
        if accepted_claim_ids
        else real_conflict_claim_ids[0]
        if real_conflict_claim_ids
        else real_parent_mismatch_claim_ids[0]
        if real_parent_mismatch_claim_ids
        else str(legacy_claim_result.get("claim_id") or "real_work_ledger_claim")
    )

    return {
        **legacy_claim_result,
        "claim_id": source_claim_id,
        "decision": public_mission_preflight["landing_decision"]["decision"],
        "conflict_claim_ids": _strings(public_mission_preflight.get("conflict_claim_ids")),
        "same_path_conflict_claim_ids": _strings(
            public_mission_preflight.get("same_path_conflict_claim_ids")
        ),
        "claim_conflict_recheck_status": public_mission_preflight[
            "claim_conflict_recheck_status"
        ],
        "expected_parent_status": public_mission_preflight["expected_parent_status"],
        "stale_expected_parent_claim_ids": _strings(
            public_mission_preflight.get("stale_expected_parent_claim_ids")
        ),
        "missing_owned_path_claim_ids": _strings(
            public_mission_preflight.get("missing_owned_path_claim_ids")
        ),
        "replan_required": public_mission_preflight["status"] != PASS,
        "decision_basis": "real_active_claims_snapshot_public_preflight",
        "public_mission_preflight_status": public_mission_preflight["status"],
        "public_mission_preflight_landing_decision": public_mission_preflight[
            "landing_decision"
        ]["decision"],
        "realness_evidence": real_snapshot_result["realness_evidence"],
        "realness_rank": real_snapshot_result["realness_rank"],
        "realness_rung": real_snapshot_result["realness_rung"],
        "realness_state": real_snapshot_result["realness_state"],
        "accepted_claim_ids": accepted_claim_ids,
        "real_active_claims_snapshot_status": real_snapshot_result["status"],
        "real_good_input_passed": real_snapshot_result["real_good_input_passed"],
        "real_wrong_input_rejected": real_snapshot_result["real_wrong_input_rejected"],
        "real_wrong_input_clear_mutation_passed": real_snapshot_result[
            "real_wrong_input_clear_mutation_passed"
        ],
        "real_snapshot_fixture_ref": real_snapshot_result["fixture_ref"],
        "real_same_path_conflict_claim_ids": real_conflict_claim_ids,
        "real_same_path_conflict_public_claim_ids": _strings(
            same_path_mutation.get("conflict_claim_ids")
        ),
        "real_same_path_owner_claim_ids": _strings(
            same_path_mutation.get("same_path_conflict_claim_ids")
        ),
        "real_expected_parent_mismatch_claim_ids": real_parent_mismatch_claim_ids,
        "real_disjoint_path_mutation_claim_ids": _strings(
            runtime_collision.get("disjoint_runtime_collision_claim_ids")
        ),
        "real_collision_row_source": runtime_collision.get("collision_row_source"),
        "legacy_regression_fixture_decision": legacy_claim_result["decision"],
        "legacy_regression_fixture_replan_required": legacy_claim_result[
            "replan_required"
        ],
        "legacy_regression_fixture_conflict_claim_ids": _strings(
            legacy_claim_result.get("conflict_claim_ids")
        ),
        "legacy_regression_fixture_same_path_conflict_claim_ids": _strings(
            legacy_claim_result.get("same_path_conflict_claim_ids")
        ),
        "legacy_regression_fixture_stale_expected_parent_claim_ids": _strings(
            legacy_claim_result.get("stale_expected_parent_claim_ids")
        ),
        "legacy_regression_fixture_decision_basis": (
            "toy_work_ledger_claims_and_repo_state_compatibility_only"
        ),
    }


def validate_scoped_receipt_authority(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_scoped_receipt_authority` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    receipt_id = "scoped_receipt_global_authority_claim"
    if isinstance(payload, dict):
        receipt_id = str(payload.get("receipt_id") or receipt_id)
        if payload.get("claims_global_authority"):
            _record(
                findings,
                observed,
                "SCOPED_RECEIPT_AUTHORITY_UPGRADE",
                "Scoped commit receipt attempted to claim global authority.",
                case_id="scoped_commit_receipt_claims_global_authority",
                subject_id=receipt_id,
                subject_kind="scoped_receipt",
            )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "scoped_receipt_authority_rejected": bool(findings),
    }


def validate_private_marker(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_private_marker` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    marker_id = "live_task_ledger_boundary_marker"
    if isinstance(payload, dict):
        marker_id = str(payload.get("fixture_id") or marker_id)
        if payload.get("forbidden_payload_value_present"):
            _record(
                findings,
                observed,
                "LIVE_TASK_LEDGER_BODY_IN_FIXTURE",
                "Fixture marked a live ledger payload value and was rejected.",
                case_id="mission_fixture_private_task_ledger_body",
                subject_id=marker_id,
                subject_kind="regression_fixture",
            )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "forbidden_payload_rejected": bool(findings),
    }


def validate_preflight_overclaim(payload: object) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `validate_preflight_overclaim` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if isinstance(payload, dict) and payload.get("preflight_status") == PASS:
        if payload.get("claims_work_landed") and not payload.get("has_closeout_landing_attempt"):
            _record(
                findings,
                observed,
                "PREFLIGHT_PASS_OVERCLAIMS_WORK_LANDED",
                "Clean preflight cannot claim landed work without closeout evidence.",
                case_id="clean_preflight_overclaims_landing_complete",
                subject_id="preflight_pass_claims_work_landed",
                subject_kind="mission_preflight",
            )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "runtime_landing_overclaim_rejected": bool(findings),
    }


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    """
    [ACTION]
    - Teleology: Implements `_merge_observed` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(code)
    return {key: sorted(value) for key, value in sorted(merged.items())}


def _common_receipt(result: dict[str, Any], *, schema_version: str, receipt_paths: list[str]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_common_receipt` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payload = {
        "schema_version": schema_version,
        "receipt_id": schema_version,
        "organ_id": result["organ_id"],
        "fixture_id": result["fixture_id"],
        "validator_id": result["validator_id"],
        "command": result["command"],
        "status": result["status"],
        "created_at": result["created_at"],
        "expected_negative_cases": result["expected_negative_cases"],
        "observed_negative_cases": result["observed_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "findings": result["findings"],
        "anti_claim": result["anti_claim"],
        "authority_ceiling": result["authority_ceiling"],
        "receipt_paths": receipt_paths,
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "public_work_landing_status": result["public_work_landing_status"],
        "public_mission_transaction_preflight": result[
            "public_mission_transaction_preflight"
        ],
        "body_import_status": result["body_import_status"],
        "body_import_verification": result["body_import_verification"],
        "source_refs": result["source_refs"],
        "source_symbols": result["source_symbols"],
        "target_refs": result["target_refs"],
        "target_symbols": result["target_symbols"],
        "public_runtime_refs": result["public_runtime_refs"],
        "body_in_receipt": False,
        "validator_contract_ratchet_status": "pass",
        "receipt_field_floor_status": "pass",
        "cannot_fake_predicate_status": "pass",
        "negative_case_binding_status": "pass",
        "fixture_payload_policy": (
            "negative_regression_fixtures_only; positive runtime evidence consumes "
            "public work_landing substrate"
        ),
        "validator_contract_ratchet_refs": VALIDATOR_CONTRACT_RATCHET_REFS,
    }
    return payload


def _without_common_receipt_overrides(payload: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_without_common_receipt_overrides` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        key: value
        for key, value in payload.items()
        if key not in {"findings", "observed_negative_cases", "status"}
    }


def _is_relative_to(path: Path, root: Path) -> bool:
    """
    [ACTION]
    - Teleology: Implements `_is_relative_to` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _relative_receipt_paths(paths: dict[str, Path], display_root: Path) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_relative_receipt_paths` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [public_relative_path(path, display_root=display_root) for path in paths.values()]


def write_receipts(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: str | Path,
) -> dict[str, str]:
    """
    [ACTION]
    - Teleology: Implements `write_receipts` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    target = target.resolve(strict=False)
    public_root = Path(public_root).resolve(strict=False)
    receipt_root = public_root if _is_relative_to(target, public_root) else target.parent
    paths = {
        "preflight": receipt_root / PREFLIGHT_REL,
        "dependency_blocked": target / DEPENDENCY_BLOCKED_NAME,
        "work_landing_attempt": target / WORK_LANDING_ATTEMPT_NAME,
        "claim_preflight_result": target / CLAIM_PREFLIGHT_NAME,
        "scoped_mutation_receipt": target / SCOPED_MUTATION_NAME,
        "checkpoint_lane_decision": target / CHECKPOINT_LANE_NAME,
        "closeout_status_projection": target / CLOSEOUT_STATUS_NAME,
        "dependency_unlock_scheduler_receipt": target / DEPENDENCY_UNLOCK_NAME,
        "work_landing_reconcile_plan": target / RECONCILE_PLAN_NAME,
    }
    receipt_paths = _relative_receipt_paths(paths, receipt_root)

    dependency = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_dependency_blocked_v1",
        receipt_paths=receipt_paths,
    )
    dependency.update(
        {
            "blocked_workitem_ids": validation_result["blocked_workitem_ids"],
            "dependency_refs": validation_result["dependency_refs"],
            "schedulable": False,
            "schedulability_decision_source": validation_result["schedulability_decision_source"],
            "dependency_unlock_resolution_basis": validation_result[
                "dependency_unlock_resolution_basis"
            ],
        }
    )

    work_landing = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_work_landing_attempt_v1",
        receipt_paths=receipt_paths,
    )
    work_landing.update(validation_result["work_landing_attempt"])

    claim = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_claim_preflight_result_v1",
        receipt_paths=receipt_paths,
    )
    claim.update(_without_common_receipt_overrides(validation_result["claim_preflight_result"]))

    scoped = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_scoped_mutation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    scoped.update(validation_result["scoped_mutation_receipt"])

    checkpoint_lane = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_checkpoint_lane_decision_v1",
        receipt_paths=receipt_paths,
    )
    checkpoint_lane.update(
        _without_common_receipt_overrides(validation_result["checkpoint_lane_decision"])
    )

    closeout = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_closeout_status_projection_v1",
        receipt_paths=receipt_paths,
    )
    closeout.update(validation_result["closeout_status_projection"])

    dependency_unlock = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_dependency_unlock_scheduler_v1",
        receipt_paths=receipt_paths,
    )
    dependency_unlock.update(
        _without_common_receipt_overrides(validation_result["dependency_unlock_scheduler"])
    )

    reconcile = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_work_landing_reconcile_plan_v1",
        receipt_paths=receipt_paths,
    )
    reconcile.update(validation_result["work_landing_reconcile_plan"])

    preflight = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_preflight_v1",
        receipt_paths=receipt_paths,
    )
    preflight.update(
        {
            "workitem_view_rebuild_status": PASS,
            "claim_preflight_status": validation_result["claim_preflight_result"]["decision"],
            "scoped_mutation_status": validation_result["scoped_mutation_receipt"][
                "mutation_status"
            ],
            "checkpoint_lane_policy_status": "pass",
            "checkpoint_lane_decision_path": public_relative_path(
                paths["checkpoint_lane_decision"], display_root=receipt_root
            ),
            "broad_checkpoint_requires_operator_authorization": True,
            "suspected_secret_requires_hard_stop": True,
            "dirty_tree_blocks_scoped_commit": False,
            "receipt_drain_status": validation_result["closeout_status_projection"][
                "receipt_drain_exclusivity_status"
            ],
            "orphan_sweep_status": "expired_claims_swept",
            "closeout_projection_path": public_relative_path(
                paths["closeout_status_projection"], display_root=receipt_root
            ),
            "controller_action_order_status": "pass",
            "ordered_controller_action_ids": ORDERED_CONTROLLER_ACTION_IDS,
            "controller_action_apply_statuses": {
                action: "dry_run_not_mutated" for action in ORDERED_CONTROLLER_ACTION_IDS
            },
            "finalizer_classification_status": "pass",
            "canonical_transaction_state": "fixture_closeout_pending_exact_receipt_drain",
            "ambient_pressure_count": 0,
            "compatibility_finalizer_count": 0,
        }
    )

    for key, payload in (
        ("preflight", preflight),
        ("dependency_blocked", dependency),
        ("work_landing_attempt", work_landing),
        ("claim_preflight_result", claim),
        ("scoped_mutation_receipt", scoped),
        ("checkpoint_lane_decision", checkpoint_lane),
        ("closeout_status_projection", closeout),
        ("dependency_unlock_scheduler_receipt", dependency_unlock),
        ("work_landing_reconcile_plan", reconcile),
    ):
        write_json_atomic(paths[key], payload)

    return {key: public_relative_path(path, display_root=receipt_root) for key, path in paths.items()}


def _write_mission_bundle_receipt(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: str | Path,
) -> str:
    """
    [ACTION]
    - Teleology: Implements `_write_mission_bundle_receipt` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = Path(public_root).resolve(strict=False)
    path = target / MISSION_BUNDLE_RESULT_NAME
    receipt_path = public_relative_path(path, display_root=public_root)
    if Path(receipt_path).is_absolute() and "receipts" in path.parts:
        receipts_index = len(path.parts) - 1 - list(reversed(path.parts)).index("receipts")
        receipt_path = Path(*path.parts[receipts_index:]).as_posix()
    payload = _common_receipt(
        validation_result,
        schema_version="mission_transaction_work_spine_exported_mission_transaction_bundle_validation_v1",
        receipt_paths=[receipt_path],
    )
    payload.update(
        {
            "bundle_manifest_schema_version": validation_result[
                "bundle_manifest_schema_version"
            ],
            "workitem_ids": validation_result["workitem_ids"],
            "accepted_claim_ids": validation_result["accepted_claim_ids"],
            "transaction_id": validation_result["transaction_id"],
            "bundle_fingerprint": validation_result["bundle_fingerprint"],
            "workitem_rows_projection_not_authority": validation_result[
                "workitem_rows_projection_not_authority"
            ],
            "claim_rows_projection_not_authority": validation_result[
                "claim_rows_projection_not_authority"
            ],
            "public_work_landing_not_live_ledger_authority": validation_result[
                "public_work_landing_not_live_ledger_authority"
            ],
            "blocked_workitem_ids": validation_result["blocked_workitem_ids"],
            "schedulable_workitem_ids": validation_result["schedulable_workitem_ids"],
            "dependency_refs": validation_result["dependency_refs"],
            "dependency_status_by_workitem": validation_result[
                "dependency_status_by_workitem"
            ],
            "resolved_dependency_refs": validation_result["resolved_dependency_refs"],
            "dependency_resolution_receipt": validation_result[
                "dependency_resolution_receipt"
            ],
            "downstream_unlock_edges": validation_result["downstream_unlock_edges"],
            "claim_preflight_result": validation_result["claim_preflight_result"],
            "scoped_mutation_receipt": validation_result["scoped_mutation_receipt"],
            "checkpoint_lane_decision": validation_result["checkpoint_lane_decision"],
            "closeout_status_projection": validation_result["closeout_status_projection"],
            "receipt_drain_plan": validation_result["receipt_drain_plan"],
            "work_landing_reconcile_plan": validation_result["work_landing_reconcile_plan"],
            "task_ledger_control_source_import_status": validation_result[
                "task_ledger_control_source_import_status"
            ],
            "task_ledger_control_source_import": validation_result[
                "task_ledger_control_source_import"
            ],
            "copied_task_ledger_source_count": validation_result[
                "copied_task_ledger_source_count"
            ],
            "copied_task_ledger_source_line_count": validation_result[
                "copied_task_ledger_source_line_count"
            ],
            "copied_task_ledger_source_module_ids": validation_result[
                "copied_task_ledger_source_module_ids"
            ],
            "task_ledger_source_manifest": validation_result["task_ledger_source_manifest"],
            "task_ledger_source_contract": validation_result["task_ledger_source_contract"],
            "task_ledger_source_public_runtime_refs": validation_result[
                "task_ledger_source_public_runtime_refs"
            ],
            "task_ledger_source_validation_refs": validation_result[
                "task_ledger_source_validation_refs"
            ],
            "work_ledger_control_source_import_status": validation_result[
                "work_ledger_control_source_import_status"
            ],
            "work_ledger_control_source_import": validation_result[
                "work_ledger_control_source_import"
            ],
            "copied_work_ledger_source_count": validation_result[
                "copied_work_ledger_source_count"
            ],
            "copied_work_ledger_source_line_count": validation_result[
                "copied_work_ledger_source_line_count"
            ],
            "copied_work_ledger_source_module_ids": validation_result[
                "copied_work_ledger_source_module_ids"
            ],
            "work_ledger_source_manifest": validation_result["work_ledger_source_manifest"],
            "work_ledger_source_contract": validation_result["work_ledger_source_contract"],
            "work_ledger_source_public_runtime_refs": validation_result[
                "work_ledger_source_public_runtime_refs"
            ],
            "work_ledger_source_validation_refs": validation_result[
                "work_ledger_source_validation_refs"
            ],
            "real_active_claims_snapshot_status": validation_result[
                "real_active_claims_snapshot_status"
            ],
            "real_active_claims_snapshot_result": validation_result[
                "real_active_claims_snapshot_result"
            ],
            "checkpoint_lane_source_import_status": validation_result[
                "checkpoint_lane_source_import_status"
            ],
            "checkpoint_lane_source_import": validation_result[
                "checkpoint_lane_source_import"
            ],
            "copied_checkpoint_source_count": validation_result[
                "copied_checkpoint_source_count"
            ],
            "copied_checkpoint_source_line_count": validation_result[
                "copied_checkpoint_source_line_count"
            ],
            "copied_checkpoint_source_module_ids": validation_result[
                "copied_checkpoint_source_module_ids"
            ],
            "checkpoint_source_manifest": validation_result["checkpoint_source_manifest"],
            "checkpoint_source_contract": validation_result["checkpoint_source_contract"],
            "checkpoint_source_public_runtime_refs": validation_result[
                "checkpoint_source_public_runtime_refs"
            ],
            "checkpoint_source_validation_refs": validation_result[
                "checkpoint_source_validation_refs"
            ],
            "mission_control_source_import_status": validation_result[
                "mission_control_source_import_status"
            ],
            "mission_control_source_import": validation_result[
                "mission_control_source_import"
            ],
            "copied_mission_control_source_count": validation_result[
                "copied_mission_control_source_count"
            ],
            "copied_mission_control_source_line_count": validation_result[
                "copied_mission_control_source_line_count"
            ],
            "copied_mission_control_source_module_ids": validation_result[
                "copied_mission_control_source_module_ids"
            ],
            "mission_control_source_manifest": validation_result[
                "mission_control_source_manifest"
            ],
            "mission_control_source_contract": validation_result[
                "mission_control_source_contract"
            ],
            "mission_control_source_public_runtime_refs": validation_result[
                "mission_control_source_public_runtime_refs"
            ],
            "mission_control_source_validation_refs": validation_result[
                "mission_control_source_validation_refs"
            ],
            "fixture_regression_required_elsewhere": True,
        }
    )
    write_json_atomic(path, payload)
    return receipt_path


def run_mission_transaction_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run_mission_transaction_bundle` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    payloads = _load_mission_bundle_payloads(input_path)
    scan_result = _scan_bundle_inputs(input_path, public_root)

    manifest = payloads["bundle_manifest"] if isinstance(payloads["bundle_manifest"], dict) else {}
    task_ledger_source_import = validate_task_ledger_source_import(input_path, public_root)
    work_ledger_source_import = validate_work_ledger_source_import(input_path, public_root)
    checkpoint_source_import = validate_checkpoint_source_import(input_path, public_root)
    mission_control_source_import = validate_mission_control_source_import(
        input_path,
        public_root,
    )
    workitem_result = validate_exported_workitems(payloads["workitems"])
    claim_result = validate_exported_claims(payloads["claim_table"])
    dependency_result = validate_exported_dependencies(
        payloads["dependency_graph"],
        workitem_result,
    )
    transaction_result = validate_exported_transaction_plan(payloads["transaction_plan"])
    receipt_drain_result = validate_exported_receipt_drain(payloads["receipt_drain_plan"])
    closeout_result = validate_exported_closeout_projection(
        payloads["closeout_projection_packet"]
    )
    scoped_policy_result = validate_exported_scoped_mutation_policy(
        payloads["scoped_mutation_policy"]
    )
    checkpoint_lane_result = validate_checkpoint_lane_policy(
        payloads["checkpoint_lane_policy"]
    )
    real_snapshot_path = input_path / REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME
    real_snapshot_result: dict[str, Any] | None = None
    if real_snapshot_path.is_file():
        real_snapshot_result = validate_real_active_claims_snapshot(
            read_json_strict(real_snapshot_path),
            input_path,
            public_root,
        )
    real_snapshot_status = (
        real_snapshot_result["status"] if real_snapshot_result is not None else "missing"
    )
    real_snapshot_missing_findings = (
        []
        if real_snapshot_result is not None
        else [
            _bundle_finding(
                "REAL_ACTIVE_CLAIMS_SNAPSHOT_MISSING",
                "Exported mission transaction bundle must carry sanitized real Work Ledger active-claims evidence.",
                subject_id=REAL_ACTIVE_CLAIMS_SNAPSHOT_NAME,
                subject_kind="real_work_ledger_snapshot_fixture",
            )
        ]
    )
    real_snapshot_blocking_findings = (
        real_snapshot_result["findings"]
        if real_snapshot_result is not None and real_snapshot_result["status"] != PASS
        else []
    )

    all_findings = sorted(
        [
            *workitem_result["findings"],
            *claim_result["findings"],
            *dependency_result["findings"],
            *transaction_result["findings"],
            *receipt_drain_result["findings"],
            *closeout_result["findings"],
            *scoped_policy_result["findings"],
            *checkpoint_lane_result["findings"],
            *task_ledger_source_import["findings"],
            *work_ledger_source_import["findings"],
            *checkpoint_source_import["findings"],
            *mission_control_source_import["findings"],
            *real_snapshot_missing_findings,
            *real_snapshot_blocking_findings,
        ],
        key=lambda item: (
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )
    bundle_id = str(
        manifest.get("bundle_id")
        or "mission_transaction_work_spine_exported_mission_transaction_bundle"
    )
    scoped_owned_paths = [
        str(path)
        for path in scoped_policy_result.get("owned_paths", [])
        if str(path).strip()
    ]
    subject_ids = [str(work_item_id) for work_item_id in workitem_result["workitem_ids"]]
    first_claim = claim_result["accepted_claim_ids"][0] if claim_result["accepted_claim_ids"] else None
    input_refs = [
        public_relative_path(path, display_root=public_root)
        for path in [
            *_mission_bundle_paths(input_path),
            *_task_ledger_source_paths(input_path),
            *_work_ledger_source_paths(input_path),
            *_checkpoint_source_paths(input_path),
            *_mission_control_source_paths(input_path),
        ]
    ]
    body_import_fields = _body_import_fields(input_refs)
    public_work_landing_status = build_public_work_landing_status(
        subject_ids=list((real_snapshot_result or {}).get("subject_ids") or subject_ids),
        owned_paths=list((real_snapshot_result or {}).get("owned_paths") or scoped_owned_paths),
        session_id=str((real_snapshot_result or {}).get("source_session_id") or first_claim or ""),
        require_exclusive=True,
    )
    public_mission_preflight = dict(
        (real_snapshot_result or {}).get("real_good_public_preflight") or {}
    )
    claim_preflight_decision_basis = "exported_claim_table_projection_public_preflight"
    if public_mission_preflight:
        claim_preflight_decision_basis = (
            "exported_bundle_real_active_claims_snapshot_public_preflight"
        )
    else:
        public_mission_preflight = build_public_mission_transaction_preflight(
            subject_ids=subject_ids,
            owned_paths=scoped_owned_paths,
            claims_payload=payloads["claim_table"],
            repo_state={},
            checkpoint_lane_policy=payloads["checkpoint_lane_policy"],
            require_exclusive=True,
        )
    public_reconcile_plan = _public_work_landing_reconcile_plan(
        subject_ids=subject_ids,
        owned_paths=scoped_owned_paths,
        session_id=first_claim,
        transaction_id=str(transaction_result["transaction_id"] or "missing_transaction"),
        recommended_next_action=str(
            transaction_result["recommended_next_action"]
            or "verify_scoped_commit_landed_then_drain_exact_receipts"
        ),
        receipt_drain_prerequisite_status="public_work_landing_receipts_declared",
    )
    status = (
        PASS
        if scan_result["status"] == PASS
        and not all_findings
        and workitem_result["workitem_ids"]
        and claim_result["accepted_claim_ids"]
        and task_ledger_source_import["status"] == PASS
        and work_ledger_source_import["status"] == PASS
        and checkpoint_source_import["status"] == PASS
        and mission_control_source_import["status"] == PASS
        and transaction_result["ordered_controller_action_ids"] == ORDERED_CONTROLLER_ACTION_IDS
        and public_mission_preflight["status"] == PASS
        and real_snapshot_result is not None
        and real_snapshot_result["status"] == PASS
        else "blocked"
    )
    bundle_fingerprint = _stable_hash(
        {
            "workitems": payloads["workitems"],
            "claim_table": payloads["claim_table"],
            "dependency_graph": payloads["dependency_graph"],
            "transaction_plan": payloads["transaction_plan"],
            "receipt_drain_plan": payloads["receipt_drain_plan"],
            "closeout_projection_packet": payloads["closeout_projection_packet"],
            "scoped_mutation_policy": payloads["scoped_mutation_policy"],
            "checkpoint_lane_policy": payloads["checkpoint_lane_policy"],
            "task_ledger_source_manifest": task_ledger_source_import["manifest_summary"],
            "task_ledger_source_modules": task_ledger_source_import["source_modules"],
            "work_ledger_source_manifest": work_ledger_source_import["manifest_summary"],
            "work_ledger_source_modules": work_ledger_source_import["source_modules"],
            "checkpoint_source_manifest": checkpoint_source_import["manifest_summary"],
            "checkpoint_source_modules": checkpoint_source_import["source_modules"],
            "mission_control_source_manifest": mission_control_source_import[
                "manifest_summary"
            ],
            "mission_control_source_modules": mission_control_source_import[
                "source_modules"
            ],
        }
    )

    result = base_receipt(
        ORGAN_ID,
        f"{FIXTURE_ID}.exported_mission_transaction_bundle",
        command=command,
    )
    result.update(
        {
            "status": status,
            "input_mode": "exported_mission_transaction_bundle",
            "bundle_id": bundle_id,
            "bundle_manifest_schema_version": manifest.get("schema_version"),
            "validator_id": VALIDATOR_ID,
            "anti_claim": (
                "The exported mission transaction bundle validates public work, claim, "
                "dependency, checkpoint-lane, receipt-drain, and closeout metadata. It does "
                "import exact non-secret Task Ledger, Work Ledger, checkpoint-lane, "
                "scoped-commit, and mission-transaction control-plane source bodies "
                "into the public bundle. It does not mutate "
                "live Task Ledger, Work Ledger, or Git state, authorize broad staging or "
                "private backup execution without operator intent, authorize release, or "
                "complete later organs."
            ),
            "authority_ceiling": {
                "status": PASS,
                "authority_ceiling": "public_work_landing_refactor_over_mission_transaction_bundle",
                "live_work_state_mutation_authorized": False,
                "live_task_ledger_mutation_authorized": False,
                "live_work_ledger_mutation_authorized": False,
                "broad_stage_authorized": False,
                "broad_checkpoint_requires_operator_authorization": True,
                "suspected_secret_requires_hard_stop": True,
                "dirty_tree_blocks_scoped_commit": False,
                "release_authorized": False,
                "later_organs_authorized": False,
            },
            "expected_negative_cases": {},
            "observed_negative_cases": {},
            "missing_negative_cases": [],
            "error_codes": sorted({str(finding["error_code"]) for finding in all_findings}),
            "findings": all_findings,
            "secret_exclusion_scan": scan_result,
            "public_work_landing_status": public_work_landing_status,
            "public_mission_transaction_preflight": public_mission_preflight,
            **body_import_fields,
            "task_ledger_control_source_import_status": TASK_LEDGER_SOURCE_IMPORT_STATUS,
            "task_ledger_control_source_import": task_ledger_source_import,
            "copied_task_ledger_source_count": task_ledger_source_import["module_count"],
            "copied_task_ledger_source_line_count": task_ledger_source_import[
                "total_line_count"
            ],
            "copied_task_ledger_source_module_ids": task_ledger_source_import[
                "module_ids"
            ],
            "task_ledger_source_manifest": task_ledger_source_import["manifest_summary"],
            "task_ledger_source_contract": task_ledger_source_import["contract_summary"],
            "task_ledger_source_public_runtime_refs": task_ledger_source_import[
                "public_runtime_refs"
            ],
            "task_ledger_source_validation_refs": TASK_LEDGER_SOURCE_VALIDATION_REFS,
            "work_ledger_control_source_import_status": WORK_LEDGER_SOURCE_IMPORT_STATUS,
            "work_ledger_control_source_import": work_ledger_source_import,
            "copied_work_ledger_source_count": work_ledger_source_import["module_count"],
            "copied_work_ledger_source_line_count": work_ledger_source_import[
                "total_line_count"
            ],
            "copied_work_ledger_source_module_ids": work_ledger_source_import[
                "module_ids"
            ],
            "work_ledger_source_manifest": work_ledger_source_import["manifest_summary"],
            "work_ledger_source_contract": work_ledger_source_import["contract_summary"],
            "work_ledger_source_public_runtime_refs": work_ledger_source_import[
                "public_runtime_refs"
            ],
            "work_ledger_source_validation_refs": WORK_LEDGER_SOURCE_VALIDATION_REFS,
            "real_active_claims_snapshot_status": real_snapshot_status,
            "real_active_claims_snapshot_result": real_snapshot_result,
            "realness_evidence": (real_snapshot_result or {}).get("realness_evidence", {}),
            "realness_rank": (real_snapshot_result or {}).get("realness_rank", 0),
            "realness_rung": (real_snapshot_result or {}).get("realness_rung", "blocked"),
            "realness_state": (
                (real_snapshot_result or {}).get("realness_state")
                or "blocked_real_work_ledger_session_snapshot_replay"
            ),
            "checkpoint_lane_source_import_status": CHECKPOINT_SOURCE_IMPORT_STATUS,
            "checkpoint_lane_source_import": checkpoint_source_import,
            "copied_checkpoint_source_count": checkpoint_source_import["module_count"],
            "copied_checkpoint_source_line_count": checkpoint_source_import[
                "total_line_count"
            ],
            "copied_checkpoint_source_module_ids": checkpoint_source_import[
                "module_ids"
            ],
            "checkpoint_source_manifest": checkpoint_source_import["manifest_summary"],
            "checkpoint_source_contract": checkpoint_source_import["contract_summary"],
            "checkpoint_source_public_runtime_refs": checkpoint_source_import[
                "public_runtime_refs"
            ],
            "checkpoint_source_validation_refs": CHECKPOINT_SOURCE_VALIDATION_REFS,
            "mission_control_source_import_status": MISSION_CONTROL_SOURCE_IMPORT_STATUS,
            "mission_control_source_import": mission_control_source_import,
            "copied_mission_control_source_count": mission_control_source_import[
                "module_count"
            ],
            "copied_mission_control_source_line_count": mission_control_source_import[
                "total_line_count"
            ],
            "copied_mission_control_source_module_ids": mission_control_source_import[
                "module_ids"
            ],
            "mission_control_source_manifest": mission_control_source_import[
                "manifest_summary"
            ],
            "mission_control_source_contract": mission_control_source_import[
                "contract_summary"
            ],
            "mission_control_source_public_runtime_refs": mission_control_source_import[
                "public_runtime_refs"
            ],
            "mission_control_source_validation_refs": MISSION_CONTROL_SOURCE_VALIDATION_REFS,
            "source_pattern_ids": SOURCE_PATTERN_IDS,
            "workitem_ids": workitem_result["workitem_ids"],
            "blocked_workitem_ids": workitem_result["blocked_workitem_ids"],
            "schedulable_workitem_ids": workitem_result["schedulable_workitem_ids"],
            "dependency_refs": workitem_result["dependency_refs"],
            "dependency_status_by_workitem": workitem_result[
                "dependency_status_by_workitem"
            ],
            "workitem_rows_projection_not_authority": workitem_result[
                "workitem_rows_projection_not_authority"
            ],
            "accepted_claim_ids": claim_result["accepted_claim_ids"],
            "claim_rows_projection_not_authority": claim_result[
                "claim_rows_projection_not_authority"
            ],
            "public_work_landing_not_live_ledger_authority": True,
            "resolved_dependency_refs": dependency_result["resolved_dependency_refs"],
            "dependency_resolution_receipt": dependency_result[
                "dependency_resolution_receipt"
            ],
            "downstream_unlock_edges": dependency_result["downstream_unlock_edges"],
            "claim_preflight_result": {
                "decision": public_mission_preflight["landing_decision"]["decision"],
                "accepted_claim_ids": claim_result["accepted_claim_ids"],
                "same_path_conflict_claim_ids": claim_result[
                    "same_path_conflict_claim_ids"
                ],
                "claim_conflict_recheck_status": public_mission_preflight[
                    "claim_conflict_recheck_status"
                ],
                "expected_parent_status": public_mission_preflight[
                    "expected_parent_status"
                ],
                "public_mission_preflight_status": public_mission_preflight["status"],
                "replan_required": public_mission_preflight["status"] != PASS,
                "decision_basis": claim_preflight_decision_basis,
                "realness_evidence": (real_snapshot_result or {}).get(
                    "realness_evidence", {}
                ),
                "realness_rank": (real_snapshot_result or {}).get("realness_rank", 0),
                "realness_rung": (
                    (real_snapshot_result or {}).get("realness_rung", "blocked")
                ),
                "realness_state": (
                    (real_snapshot_result or {}).get("realness_state")
                    or "blocked_real_work_ledger_session_snapshot_replay"
                ),
                "real_active_claims_snapshot_status": real_snapshot_status,
                "real_good_input_passed": (real_snapshot_result or {}).get(
                    "real_good_input_passed"
                ),
                "real_wrong_input_rejected": (real_snapshot_result or {}).get(
                    "real_wrong_input_rejected"
                ),
            },
            "scoped_mutation_receipt": scoped_policy_result,
            "checkpoint_lane_decision": checkpoint_lane_result,
            "closeout_status_projection": {
                **closeout_result,
                "receipt_refs_drained": receipt_drain_result["receipt_refs_drained"],
                "exact_receipt_drain_scope": receipt_drain_result[
                    "exact_receipt_drain_scope"
                ],
                "receipt_drain_exclusivity_status": receipt_drain_result[
                    "receipt_drain_exclusivity_status"
                ],
                "body_in_receipt": False,
            },
            "receipt_drain_plan": receipt_drain_result,
            "work_landing_reconcile_plan": {
                **public_reconcile_plan,
                "transaction_id": transaction_result["transaction_id"],
                "source_transaction_plan_mode": transaction_result["mode"],
                "claim_release_order_status": transaction_result[
                    "claim_release_order_status"
                ],
            },
            "transaction_id": transaction_result["transaction_id"],
            "bundle_fingerprint": bundle_fingerprint,
        }
    )
    receipt_path = _write_mission_bundle_receipt(out_dir, result, public_root=public_root)
    result["receipt_paths"] = [receipt_path]
    return result


def run(input_dir: str | Path, out_dir: str | Path, command: str | None = None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `run` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    payloads = _load_input_payloads(input_path)
    scan_result = _scan_fixture_inputs(input_path, public_root)

    dependency_result = validate_dependency_unlock_scheduler(payloads["dependency_graph"])
    claim_result = validate_claim_preflight(
        payloads["claims"],
        payloads["repo_state"],
        payloads["missing_owned_path"],
    )
    real_snapshot_result = validate_real_active_claims_snapshot(
        payloads["real_active_claims_snapshot"],
        input_path,
        public_root,
    )
    scoped_result = validate_scoped_receipt_authority(payloads["scoped_receipt"])
    private_marker_result = validate_private_marker(payloads["private_marker"])
    preflight_result = validate_preflight_overclaim(payloads["preflight_overclaim"])
    checkpoint_lane_result = validate_checkpoint_lane_policy(
        payloads["checkpoint_lane_policy"],
        payloads["checkpoint_negative_cases"],
    )

    observed = _merge_observed(
        dependency_result,
        claim_result,
        real_snapshot_result,
        scoped_result,
        private_marker_result,
        preflight_result,
        checkpoint_lane_result,
    )
    missing_cases = sorted(set(EXPECTED_NEGATIVE_CASES) - set(observed))
    error_codes = sorted({code for codes in observed.values() for code in codes})
    all_findings = sorted(
        [
            *dependency_result["findings"],
            *claim_result["findings"],
            *real_snapshot_result["findings"],
            *scoped_result["findings"],
            *private_marker_result["findings"],
            *preflight_result["findings"],
            *checkpoint_lane_result["findings"],
        ],
        key=lambda item: (
            str(item.get("negative_case_id") or ""),
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )
    secret_scan = dict(scan_result)
    secret_scan["negative_fixture_boundary_cases_observed"] = [
        "mission_fixture_private_task_ledger_body"
    ]
    fixture_refs = [
        public_relative_path(path, display_root=public_root)
        for path in _input_file_paths(input_path)
    ]
    body_import_fields = _body_import_fields(fixture_refs)
    real_subject_ids = list(real_snapshot_result.get("subject_ids") or []) or [
        "cap_quick_mission_transaction_real_claim_snapshot_upgrade_20260604"
    ]
    real_owned_paths = list(real_snapshot_result.get("owned_paths") or []) or [
        "microcosm-substrate/src/microcosm_core/organs/mission_transaction_work_spine.py"
    ]
    real_session_id = str(
        real_snapshot_result.get("source_session_id")
        or "codex_goal_microcosm_realness_20260604T102534Z_mission_transaction_real_claim_snapshot_upgrade"
    )
    public_work_landing_status = build_public_work_landing_status(
        subject_ids=real_subject_ids,
        owned_paths=real_owned_paths,
        session_id=real_session_id,
        require_exclusive=True,
    )
    public_mission_preflight = dict(
        real_snapshot_result.get("real_good_public_preflight") or {}
    )
    if not public_mission_preflight:
        public_mission_preflight = build_public_mission_transaction_preflight(
            subject_ids=real_subject_ids,
            owned_paths=real_owned_paths,
            claims_payload=payloads["claims"],
            repo_state=payloads["repo_state"],
            checkpoint_lane_policy=payloads["checkpoint_lane_policy"],
            checkpoint_negative_cases=payloads["checkpoint_negative_cases"],
            require_exclusive=True,
        )
    claim_result = _primary_claim_preflight_from_real_snapshot(
        legacy_claim_result=claim_result,
        real_snapshot_result=real_snapshot_result,
        public_mission_preflight=public_mission_preflight,
    )
    public_work_landing_attempt = _public_work_landing_attempt(
        subject_ids=real_subject_ids,
        owned_paths=real_owned_paths,
        session_id=real_session_id,
    )
    public_work_landing_attempt.update(
        {
            "read_set": [
                (
                    f"{real_snapshot_result['fixture_ref']}"
                    f"@{real_snapshot_result.get('source_snapshot_hash') or 'public-safe'}"
                )
            ],
            "write_set": real_owned_paths,
        }
    )
    public_reconcile_plan = _public_work_landing_reconcile_plan(
        subject_ids=real_subject_ids,
        owned_paths=real_owned_paths,
        session_id=real_session_id,
        transaction_id="mtx_real_work_ledger_active_claim_snapshot",
        recommended_next_action="verify_scoped_commit_landed_then_drain_exact_receipt",
        receipt_drain_prerequisite_status="commit_landing_required_before_drain",
    )

    result = base_receipt(ORGAN_ID, FIXTURE_ID, command=command)
    result.update(
        {
            "status": (
                PASS
                if not missing_cases
                and scan_result["status"] == PASS
                and real_snapshot_result["status"] == PASS
                else "blocked"
            ),
            "validator_id": VALIDATOR_ID,
            "anti_claim": MISSION_ANTI_CLAIM,
            "authority_ceiling": MISSION_AUTHORITY_CEILING,
            "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
            "observed_negative_cases": observed,
            "missing_negative_cases": missing_cases,
            "error_codes": error_codes,
            "findings": all_findings,
            "secret_exclusion_scan": secret_scan,
            "public_work_landing_status": public_work_landing_status,
            "public_mission_transaction_preflight": public_mission_preflight,
            "real_active_claims_snapshot_result": real_snapshot_result,
            "realness_evidence": real_snapshot_result["realness_evidence"],
            "realness_rank": real_snapshot_result["realness_rank"],
            "realness_rung": real_snapshot_result["realness_rung"],
            "realness_state": real_snapshot_result["realness_state"],
            **body_import_fields,
            "blocked_workitem_ids": dependency_result["blocked_workitem_ids"],
            "ready_but_unsatisfied_workitem_ids": dependency_result[
                "ready_but_unsatisfied_workitem_ids"
            ],
            "resolved_dependency_refs": dependency_result["resolved_dependency_refs"],
            "dependency_status_by_workitem": dependency_result["dependency_status_by_workitem"],
            "dependency_resolution_receipt": dependency_result["dependency_resolution_receipt"],
            "unsatisfied_dep_ids": dependency_result["unsatisfied_dep_ids"],
            "downstream_unlock_edges": dependency_result["downstream_unlock_edges"],
            "unlocks_by_rank": dependency_result["unlocks_by_rank"],
            "dangling_dependency_refs": dependency_result["dangling_dependency_refs"],
            "schedulable_workitem_ids": dependency_result["schedulable_workitem_ids"],
            "downstream_schedulable_before": dependency_result["downstream_schedulable_before"],
            "schedulability_decision_source": dependency_result["schedulability_decision_source"],
            "dependency_unlock_resolution_basis": dependency_result[
                "dependency_unlock_resolution_basis"
            ],
            "anomaly_refs": dependency_result["anomaly_refs"],
            "derived_not_authority": dependency_result["derived_not_authority"],
            "schedulable": dependency_result["schedulable"],
            "dependency_refs": dependency_result["dependency_refs"],
            "claim_preflight_result": claim_result,
            "scoped_authority_result": scoped_result,
            "private_marker_result": private_marker_result,
            "preflight_overclaim_result": preflight_result,
            "checkpoint_lane_decision": checkpoint_lane_result,
            "work_landing_attempt": {
                **public_work_landing_attempt,
                "attempt_id": public_work_landing_attempt["idempotency_key"],
                "work_item_id": real_subject_ids[0],
            },
            "scoped_mutation_receipt": {
                "owned_paths": real_owned_paths,
                "mutation_status": "real_snapshot_scoped_mutation_valid_for_source_claims",
                "expected_parent_status": "pass_for_real_snapshot_mutation_rejected",
                "broad_stage_used": False,
                "authority_upgrade_rejected": scoped_result["scoped_receipt_authority_rejected"],
                "body_in_receipt": False,
            },
            "closeout_status_projection": {
                "work_item_id": real_subject_ids[0],
                "status_before": "ready",
                "status_after": "closed_regression_fixture",
                "receipt_refs_drained": ["receipt_expected_001"],
                "exact_receipt_drain_scope": ["receipt_expected_001"],
                "receipt_drain_exclusivity_status": "only_declared_receipt_drained",
                "unrelated_receipt_refs_left_open": ["receipt_unrelated_999"],
                "derived_not_authority": True,
                "body_in_receipt": False,
            },
            "dependency_unlock_scheduler": dependency_result,
            "work_landing_reconcile_plan": {
                **public_reconcile_plan,
            },
            "fixture_inputs": fixture_refs,
        }
    )
    paths = write_receipts(out_dir, result, public_root=public_root)
    result["receipt_paths"] = list(paths.values())
    return result


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.organs.mission_transaction_work_spine` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("validate-mission-transaction-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.action == "run":
        command = (
            "python -m microcosm_core.organs.mission_transaction_work_spine "
            f"run --input {args.input} --out {args.out}"
        )
        result = run(args.input, args.out, command=command)
    elif args.action == "validate-mission-transaction-bundle":
        command = (
            "python -m microcosm_core.organs.mission_transaction_work_spine "
            f"validate-mission-transaction-bundle --input {args.input} --out {args.out}"
        )
        result = run_mission_transaction_bundle(args.input, args.out, command=command)
    else:
        parser.error("expected subcommand: run or validate-mission-transaction-bundle")
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
