"""
Read-only mission transaction landing preflight.

This module composes existing repo substrates into one packet before a Type A
agent stages or commits: Git index state, Work Ledger claim pressure, generated
projection ownership, scoped-commit capability, and shared-worktree guardrails.
It does not mutate Git, Task Ledger, Work Ledger, or generated projections.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import errno
from fnmatch import fnmatch
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from system.lib import (
    autonomy_subphase,
    generated_state_drainer,
    generated_projection_registry,
    shared_worktree_guard,
    task_ledger_events,
    work_ledger_runtime,
)
from system.lib.forward_integration_policy import (
    normalize_repo_path,
    owner_tool_entries_for_path,
    path_scope_overlaps,
)

try:
    from tools.meta.factory.work_ledger import WRITE_PROFILE_PATHS
except Exception:  # pragma: no cover - defensive fallback for import-time CLI drift.
    WRITE_PROFILE_PATHS = {}  # type: ignore[assignment]


SCHEMA = "mission_transaction_landing_preflight_v0"
TRANSACTION_CANDIDATE_SCHEMA = "transaction_candidate_v0"
TRANSACTION_CONVERGENCE_SCHEMA = "transaction_convergence_v0"
TRANSACTION_CONVERGENCE_RECONCILE_SCHEMA = "transaction_convergence_reconcile_v0"
TRANSACTION_CLOSEOUT_SETTLEMENT_SCHEMA = "transaction_closeout_settlement_v0"
GENERATED_PROJECTION_SETTLEMENT_DEFERRED_SCHEMA = "generated_projection_settlement_deferred_v0"
EXPLORE_EXECUTE_REVIEW_CLOSEOUT_SCHEMA = "explore_execute_review_runtime_closeout_v0"
WORKITEM_LANDING_ATTEMPT_STATE_SCHEMA = "workitem_landing_attempt_state_v0"
DERIVED_STATE_BLOAT_GOVERNOR_SCHEMA = "derived_state_bloat_governor_v0"
DERIVED_ARTIFACT_POLICY_SCHEMA = "derived_artifact_policy_v1"
WORKSPACE_BLOAT_PRESSURE_SCHEMA = "workspace_bloat_pressure_v0"
RUNTIME_ARTIFACT_LIFECYCLE_SCHEMA = "runtime_artifact_lifecycle_v0"
GITHUB_PUSH_BLOAT_GATE_SCHEMA = "github_push_bloat_gate_v1"
PUBLICATION_RECOVERY_SCHEMA = "publication_recovery_v1"
AUTONOMOUS_EDIT_GATE_SCHEMA = "autonomous_edit_gate_v0"
PATCH_BUNDLE_MODE_SCHEMA = "patch_bundle_mode_v0"
RECONCILIATION_MODE_SCHEMA = "reconciliation_mode_v0"
DIRTY_TREE_CLASSIFICATION_SCHEMA = "dirty_tree_classification_v0"
SHARED_INDEX_QUARANTINE_SCHEMA = "shared_index_quarantine_v0"
SHARED_INDEX_ENTRY_STATE_SCHEMA = "shared_index_entry_state_v0"
WORK_ITEM_BINDING_SCHEMA = "work_item_binding_v0"
SUBPHASE_BINDING_SCHEMA = "subphase_binding_v0"
TASK_LEDGER_EVENTS = "state/task_ledger/events.jsonl"
TASK_LEDGER_PROJECTION_PREFIXES = (
    "state/task_ledger/ledger.json",
    "state/task_ledger/sign_offs.json",
    "state/task_ledger/views",
)
TASK_LEDGER_RECEIPT_WRITE_SET = (
    TASK_LEDGER_EVENTS,
    "state/task_ledger/ledger.json",
    "state/task_ledger/views",
)
TASK_LEDGER_PROJECTION_SETTLE_DRY_RUN_COMMAND = (
    "./repo-python tools/meta/control/generated_state_drainer.py settle "
    "--owner-id task_ledger_projection --dry-run"
)
CONTROL_SUMMARY_FULL_PREFLIGHT_COMMAND = (
    "./repo-python tools/meta/control/mission_transaction_preflight.py --control-summary --full"
)
FULL_PREFLIGHT_COMMAND = "./repo-python tools/meta/control/mission_transaction_preflight.py --full"
BLOAT_GOVERNOR_COMMAND = "./repo-python tools/meta/control/mission_transaction_preflight.py --bloat-governor"
GENERATED_SETTLEMENT_PLAN_COMMAND = (
    "./repo-python tools/meta/control/generated_state_drainer.py settlement-plan"
)
RUNTIME_ARTIFACT_LIFECYCLE_DRY_RUN_COMMAND = (
    "./repo-python tools/meta/control/mission_transaction_preflight.py "
    "--runtime-artifact-lifecycle"
)
PHASE_PIPELINE_RUNTIME_COMMAND = (
    "./repo-python tools/meta/control/phase_convergence_doctor.py --compact"
)
MICROCOSM_RUNTIME_RECEIPT_COMMAND = (
    "cd microcosm-substrate && PYTHONPATH=src .venv/bin/python -m microcosm_core runtime-shell --help"
)
RECEIPT_ARTIFACT_OWNER_COMMAND = (
    "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --compact"
)
LOCAL_OWNED_PATH_SETTLEMENT_DEFERRED_REASON = (
    "local_owned_path_preflight_defers_generated_projection_settlement"
)
CONTROL_SUMMARY_SETTLEMENT_DEFERRED_REASON = (
    "control_summary_defers_generated_projection_settlement"
)
WORKSPACE_BLOAT_PRESSURE_SETTLEMENT_DEFERRED_REASON = (
    "workspace_bloat_pressure_defers_generated_projection_settlement"
)
DEFAULT_COMPACT_SETTLEMENT_DEFERRED_REASON = (
    "default_compact_preflight_defers_generated_projection_settlement"
)
DEFAULT_CONTROL_SUMMARY_SUBJECT_ID = "cap_live_concurrency_transactional_workitems"
EVENTFUL_CLOSEOUT_FINALIZER_IDS = (
    "task_ledger_execution_receipt",
    "work_ledger_append_or_exempt",
    "claims_released",
    "session_not_stale_or_exempt",
)
KNOWN_GENERATED_PREFIXES = (
    "codex/derived",
    "state/frontend_navigation",
    "state/projection_drift",
)
RUNTIME_RUN_PREFIXES = (
    "state/runs/",
)
STATION_RENDER_LOAD_INDEX = "state/observability/render_load_index.json"
STATION_RENDER_RECEIPT_PREFIXES = (
    "state/observability/renders/",
)
PHASE_PIPELINE_RUNTIME_FILENAMES = {
    "continuation_packet.json",
    "pipeline_attention.json",
    "pipeline_attention.md",
    "pipeline_resume.json",
    "pipeline_resume.md",
    "pipeline_state.json",
    "raw_seed_digest.json",
    "system_view.json",
    "task_backlog.json",
}
MICROCOSM_RUNTIME_RECEIPT_PREFIX = "microcosm-substrate/receipts/runtime_shell/"
RECEIPT_ARTIFACT_PREFIX = "receipts/"
KNOWN_GENERATED_SUFFIXES = (
    "/openapi.json",
    "/generated/types.ts",
    "_index.json",
    "_registry.json",
    "_projection.json",
)
KNOWN_SOURCE_INDEXES = {
    "codex/doctrine/documentation_theory_index.json",
    "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
    "codex/doctrine/facts/fact_registry.json",
    "codex/doctrine/system_vocabulary/term_registry.json",
    "microcosm-substrate/core/organ_registry.json",
    "microcosm-substrate/core/standards_registry.json",
    "state/frontend_navigation/semantic_layer.v1.json",
}
MICROCOSM_PUBLIC_FIXTURE_SOURCE_INDEX_PATTERNS = (
    "microcosm-substrate/fixtures/first_wave/*/input/premise_index.json",
    "microcosm-substrate/examples/*/exported_*/premise_index.json",
    "microcosm-substrate/examples/*/exported_*/source_modules/*",
)
INDEX_MUTATING_COMMANDS = (
    ("add",),
    ("restore", "--staged"),
    ("reset",),
    ("commit",),
    ("merge",),
    ("cherry-pick",),
)
RISKY_COMMANDS = (
    ("stash",),
    ("reset", "--hard"),
    ("restore", "."),
    ("checkout", "--", "README.md"),
    ("clean", "-fd"),
)
RISK_BANDS = ("clear", "watch", "review", "blocked", "hard_stop")
RISK_BAND_SEVERITY = {band: index for index, band in enumerate(RISK_BANDS)}
GIT_METADATA_WRITE_OK = "git_metadata_write_ok"
GIT_METADATA_PROTECTED_SANDBOX = "protected_git_metadata_sandbox_or_approval_required"
GIT_METADATA_UNIX_PERMISSION_DENIED = "unix_or_repo_permission_denied"
GIT_METADATA_STALE_LOCK_OR_CONTENTION = "stale_lock_or_git_process_contention"
GIT_COMMAND_DIAGNOSTIC_SCHEMA = "git_command_diagnostic_v0"
GIT_COMMAND_TIMEOUT_RETURN_CODE = 124
GIT_COMMAND_ERROR_RETURN_CODE = 127
DEFAULT_GIT_COMMAND_TIMEOUT_SECONDS = 15.0
COMPACT_PREVIEW_LIMIT = 25
SHARED_INDEX_ENTRY_STATE_SCAN_LIMIT = COMPACT_PREVIEW_LIMIT
GIT_LS_TREE_CHUNK_SIZE = 200
AUTONOMOUS_EDIT_DIRTY_PATH_THRESHOLD = 50
BLOCKED_PRIMARY_RECEIPT_REQUIREMENT_SCHEMA = (
    "blocked_primary_ambition_receipt_requirement_v0"
)
BLOCKED_PRIMARY_RECEIPT_VALIDATION_SCHEMA = (
    "blocked_primary_ambition_receipt_validation_v0"
)
BLOCKED_PRIMARY_STANDARD_REF = (
    "codex/standards/std_task_ledger.json::metacontrol_contract."
    "blocked_primary_ambition_preservation"
)
BLOCKED_PRIMARY_LEGAL_CONTINUATIONS = (
    "finish_when_claimable",
    "adopt_or_coordinate_blocker",
    "uncontended_sibling",
    "residual_then_ranked_independent",
)
BLOCKED_PRIMARY_BLOCKER_CLASSIFICATIONS = (
    "active_path_claim",
    "stale_claim",
    "unsafe_dirty_tree",
    "unclaimable_generated_inputs",
    "claim_cleared",
    "other",
)
BLOCKED_PRIMARY_REQUIRED_RECEIPT_FIELDS = (
    "primary_target",
    "blocker_classification",
    "claim_or_collision_evidence",
    "selected_legal_continuation",
    "why_highest_yield_legal_move",
    "reentry_condition",
)
GITHUB_BLOB_RECOMMENDED_LIMIT_BYTES = 1_000_000
GITHUB_BLOB_HARD_LIMIT_BYTES = 100_000_000
PUSH_RANGE_CONTAMINATION_COMMIT_THRESHOLD = 25
ANNEX_ARTIFACT_POLICY_OWNER = "annex_navigation_artifacts"
ANNEX_DURABLE_AUTHORITY_FILES = {
    "annex_family.json",
    "annex_notes.json",
    "distillation.json",
}
ANNEX_DURABLE_GENERATED_FILES = {
    "annex_index.json",
    "extracted.md",
}
ANNEX_RECONSTRUCTABLE_LOCAL_FILES = {
    "annex_contents.json",
    "annex_catalog.json",
}
ANNEX_RUNTIME_DIAGNOSTIC_FILES = {
    "annex_sync_report.json",
    "extraction_quality_report.json",
}
ANNEX_SYNC_DIGEST_FILES = {
    "annex_sync_digest.json",
    "annex_sync_digest.md",
    "annex_sync_digest_run_state.json",
}
ANNEX_EXTERNAL_SOURCE_NAMES = {
    "source.pdf",
    "source.epub",
    "source.html",
}
ANNEX_EXTERNAL_SOURCE_SUFFIXES = (
    ".zip",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".gz",
    ".xz",
    ".bz2",
    ".7z",
    ".whl",
)
PUSH_BLOAT_BLOCKER_CLASSES = {
    "annex_external_payload",
    "annex_reconstructable_local_projection",
    "annex_runtime_diagnostic",
    "annex_unclassified_payload",
    "distribution_packet",
    "generated_projection_unknown_owner",
    "tracked_build_output",
}
LIVE_CONCURRENCY_CAP_PREFIX = "cap_live_concurrency_"
GOVERNANCE_PREFIXES = (
    "AGENTS.md",
    "AGENTS.override.md",
    "CLAUDE.md",
    "CODEX.md",
    "codex/standards",
    "codex/doctrine/skills",
)
WORK_LEDGER_PREFIXES = (
    "codex/ledger",
    "state/work_ledger",
)
RAW_OR_OPERATOR_STATE_MARKERS = (
    "raw_seed",
    "operator",
)
RECONSTRUCTABLE_BUILD_OUTPUT_SEGMENTS = {
    ".build",
    "DerivedData",
}
PHASE_STATE_MARKERS = (
    "synth_seed",
    "phase_scaffold",
    "phase_family",
    "meta_ledger",
    "pipeline_attention",
    "pipeline_resume",
)
DIRTY_TREE_CLASS_OWNERS = {
    "ambient_dirty": "scoped_owner_or_manual_classification",
    "annex_projection_or_digest": "annex_assimilation",
    "distribution_packet": "distribution_packet_builder",
    "raw_seed_or_operator_state": "raw_seed_lane",
    "tracked_build_output": "build_output_quarantine",
    "task_ledger_event_or_projection": "task_ledger_projection",
    "work_ledger_event_or_projection": "work_ledger_projection",
    "runtime_run_artifact": "runtime_artifact_lifecycle",
    "station_render_latest_projection": "station_render_receipt_promotion",
    "station_render_receipt_artifact": "station_render_receipt_promotion",
    "phase_pipeline_runtime_state": "phase_pipeline_runtime",
    "microcosm_runtime_receipt_state": "microcosm_runtime_shell",
    "receipt_artifact_state": "mission_receipt_artifacts",
    "current_transaction_owned": "current_transaction",
    "unowned_staged": "git_index_owner",
}
DERIVED_STATE_BLOAT_POLICIES = {
    "annex_projection_or_digest": {
        "budget": 100,
        "owner_hint": "annex_assimilation",
        "allowed_git_policy": "manifest_or_artifact_store_unless_declared_durable_projection",
        "drain_or_manifest_command": "./repo-python annex_import.py validate && ./repo-python tools/meta/factory/build_annex_distillation_projection.py --write",
        "push_block_threshold": 250,
    },
    "task_ledger_event_or_projection": {
        "budget": 25,
        "owner_hint": "task_ledger_projection",
        "allowed_git_policy": "append_exempt_drainer_lands_valid_event_log_and_projection_bundle",
        "drain_or_manifest_command": TASK_LEDGER_PROJECTION_SETTLE_DRY_RUN_COMMAND,
        "push_block_threshold": 100,
    },
    "work_ledger_event_or_projection": {
        "budget": 25,
        "owner_hint": "work_ledger_projection",
        "allowed_git_policy": "work_ledger_drainer_commits_event_log_and_indexes",
        "drain_or_manifest_command": "./repo-python tools/meta/factory/work_ledger.py project --check --all",
        "push_block_threshold": 100,
    },
    "runtime_run_artifact": {
        "budget": 50,
        "owner_hint": "runtime_artifact_lifecycle",
        "allowed_git_policy": "runtime_receipts_preserved_unless_claimed_or_promoted",
        "drain_or_manifest_command": RUNTIME_ARTIFACT_LIFECYCLE_DRY_RUN_COMMAND,
        "push_block_threshold": None,
    },
    "station_render_latest_projection": {
        "budget": 1,
        "owner_hint": "station_render_receipt_promotion",
        "allowed_git_policy": "generated_latest_projection_do_not_commit_as_source",
        "drain_or_manifest_command": RUNTIME_ARTIFACT_LIFECYCLE_DRY_RUN_COMMAND,
        "push_block_threshold": None,
    },
    "station_render_receipt_artifact": {
        "budget": 25,
        "owner_hint": "station_render_receipt_promotion",
        "allowed_git_policy": "per_run_manifest_preserved_unless_explicitly_promoted",
        "drain_or_manifest_command": RUNTIME_ARTIFACT_LIFECYCLE_DRY_RUN_COMMAND,
        "push_block_threshold": None,
    },
    "phase_pipeline_runtime_state": {
        "budget": 25,
        "owner_hint": "phase_pipeline_runtime",
        "allowed_git_policy": "phase_runtime_state_preserved_or_settled_by_phase_owner",
        "drain_or_manifest_command": PHASE_PIPELINE_RUNTIME_COMMAND,
        "push_block_threshold": None,
    },
    "microcosm_runtime_receipt_state": {
        "budget": 50,
        "owner_hint": "microcosm_runtime_shell",
        "allowed_git_policy": "runtime_shell_receipts_preserved_unless_claimed_or_promoted",
        "drain_or_manifest_command": MICROCOSM_RUNTIME_RECEIPT_COMMAND,
        "push_block_threshold": None,
    },
    "receipt_artifact_state": {
        "budget": 25,
        "owner_hint": "mission_receipt_artifacts",
        "allowed_git_policy": "receipt_artifacts_preserved_until_owner_promotion",
        "drain_or_manifest_command": RECEIPT_ARTIFACT_OWNER_COMMAND,
        "push_block_threshold": None,
    },
    "distribution_packet": {
        "budget": 10,
        "owner_hint": "distribution_packet_builder",
        "allowed_git_policy": "manifested_distribution_packet_only",
        "drain_or_manifest_command": "./repo-python tools/meta/dissemination/portability_gate.py --help",
        "push_block_threshold": 25,
    },
    "raw_seed_or_operator_state": {
        "budget": 5,
        "owner_hint": "raw_seed_lane",
        "allowed_git_policy": "source_lane_only",
        "drain_or_manifest_command": "route through raw-seed lane owner",
        "push_block_threshold": 10,
    },
    "tracked_build_output": {
        "budget": 0,
        "owner_hint": "build_output_quarantine",
        "allowed_git_policy": "never_commit_reconstructable_build_cache",
        "drain_or_manifest_command": "./repo-python tools/meta/control/scoped_commit.py tracked-removals --remove-path <build-output-path> --path <ignore-file> --message \"chore: stop tracking build output\"",
        "push_block_threshold": None,
    },
    "ambient_dirty": {
        "budget": 25,
        "owner_hint": "scoped_owner_or_manual_classification",
        "allowed_git_policy": "owner_classified_or_excluded",
        "drain_or_manifest_command": "./repo-python tools/meta/control/mission_transaction_preflight.py --owned-path <path>",
        "push_block_threshold": 100,
    },
}


@dataclass(frozen=True)
class GitStatusRow:
    index_status: str
    worktree_status: str
    path: str
    original_path: str | None = None

    @property
    def is_staged(self) -> bool:
        return self.index_status not in {"", " ", "?"}

    @property
    def is_worktree_dirty(self) -> bool:
        return self.worktree_status not in {"", " "}

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "original_path": self.original_path,
            "index_status": self.index_status,
            "worktree_status": self.worktree_status,
            "staged": self.is_staged,
            "worktree_dirty": self.is_worktree_dirty,
        }


def _git_command_timeout_seconds() -> float:
    try:
        return max(float(os.environ.get("AIW_MISSION_PREFLIGHT_GIT_TIMEOUT_SECONDS", "")), 0.1)
    except ValueError:
        return DEFAULT_GIT_COMMAND_TIMEOUT_SECONDS


def _process_output_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _run_git(repo_root: Path, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    command = ["git", *args]
    timeout_seconds = _git_command_timeout_seconds()
    try:
        return subprocess.run(
            command,
            cwd=repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stderr = _process_output_text(exc.stderr)
        timeout_message = (
            f"git command timed out after {timeout_seconds:g}s: "
            + " ".join(command)
        )
        return subprocess.CompletedProcess(
            command,
            GIT_COMMAND_TIMEOUT_RETURN_CODE,
            stdout=_process_output_text(exc.output),
            stderr=(stderr + "\n" + timeout_message).strip(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(
            command,
            GIT_COMMAND_ERROR_RETURN_CODE,
            stdout="",
            stderr=str(exc),
        )


def _git_command_diagnostic(
    *,
    purpose: str,
    args: Sequence[str],
    proc: subprocess.CompletedProcess[str],
) -> dict[str, Any] | None:
    if proc.returncode == 0:
        return None
    status = "timeout" if proc.returncode == GIT_COMMAND_TIMEOUT_RETURN_CODE else "error"
    return {
        "schema": GIT_COMMAND_DIAGNOSTIC_SCHEMA,
        "status": status,
        "purpose": purpose,
        "returncode": proc.returncode,
        "argv": ["git", *args],
        "timeout_seconds": _git_command_timeout_seconds()
        if proc.returncode == GIT_COMMAND_TIMEOUT_RETURN_CODE
        else None,
        "stdout_preview": str(proc.stdout or "")[:500],
        "stderr_preview": str(proc.stderr or "")[:500],
        "repair_hint": (
            "Git subprocess timed out inside mission transaction preflight; inspect the child process and rerun after resolving repository/Git contention."
            if status == "timeout"
            else "Git subprocess failed during mission transaction preflight; inspect stderr and repository state."
        ),
    }


def _json_digest(value: Any) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except TypeError:
        raw = json.dumps(str(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _git_stdout(repo_root: Path, args: Sequence[str]) -> str | None:
    proc = _run_git(repo_root, args)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _git_ref_blob(repo_root: Path, refspec: str) -> str | None:
    return _git_stdout(repo_root, ["rev-parse", "--verify", refspec])


def _worktree_blob(repo_root: Path, path: str) -> str | None:
    target = repo_root / path
    if not target.is_file():
        return None
    return _git_stdout(repo_root, ["hash-object", "--", path])


def _shared_index_entry_state(repo_root: Path, path: str) -> dict[str, Any]:
    head_blob = _git_ref_blob(repo_root, f"HEAD:{path}")
    index_blob = _git_ref_blob(repo_root, f":{path}")
    worktree_blob = _worktree_blob(repo_root, path)
    return _shared_index_entry_state_from_blobs(
        path,
        head_blob=head_blob,
        index_blob=index_blob,
        worktree_blob=worktree_blob,
    )


def _shared_index_entry_state_from_blobs(
    path: str,
    *,
    head_blob: str | None,
    index_blob: str | None,
    worktree_blob: str | None,
) -> dict[str, Any]:
    index_matches_head = bool(index_blob and head_blob and index_blob == head_blob)
    worktree_matches_head = bool(worktree_blob and head_blob and worktree_blob == head_blob)
    worktree_matches_index = bool(worktree_blob and index_blob and worktree_blob == index_blob)

    if index_blob and head_blob and worktree_blob and not index_matches_head and worktree_matches_head:
        status = "stale_reverse_index_entry"
    elif index_matches_head:
        status = "index_matches_head"
    elif index_blob and head_blob and worktree_matches_index and not index_matches_head:
        status = "intentional_staged_change"
    elif index_blob and head_blob and not index_matches_head:
        status = "staged_change_with_worktree_delta"
    else:
        status = "unclassified_index_entry"

    return {
        "schema": SHARED_INDEX_ENTRY_STATE_SCHEMA,
        "path": path,
        "status": status,
        "head_blob": head_blob,
        "index_blob": index_blob,
        "worktree_blob": worktree_blob,
        "index_matches_head": index_matches_head,
        "worktree_matches_head": worktree_matches_head,
        "worktree_matches_index": worktree_matches_index,
    }


def _index_blob_info_for_paths(repo_root: Path, paths: Sequence[str]) -> dict[str, str]:
    blobs: dict[str, str] = {}
    path_list = [str(path or "").strip("/") for path in paths if str(path or "").strip("/")]
    for index in range(0, len(path_list), GIT_LS_TREE_CHUNK_SIZE):
        chunk = path_list[index:index + GIT_LS_TREE_CHUNK_SIZE]
        proc = _run_git(repo_root, ["ls-files", "--stage", "--", *chunk])
        if proc.returncode != 0:
            continue
        for line in proc.stdout.splitlines():
            meta, separator, path = line.partition("\t")
            if not separator or not path:
                continue
            parts = meta.split()
            if len(parts) < 3 or parts[2] != "0":
                continue
            blobs[_normalize_path(repo_root, path)] = parts[1]
    return blobs


def _worktree_blobs_for_paths(repo_root: Path, paths: Sequence[str]) -> dict[str, str]:
    blobs: dict[str, str] = {}
    path_list = [
        str(path or "").strip("/")
        for path in paths
        if str(path or "").strip("/") and (repo_root / str(path or "").strip("/")).is_file()
    ]
    for index in range(0, len(path_list), GIT_LS_TREE_CHUNK_SIZE):
        chunk = path_list[index:index + GIT_LS_TREE_CHUNK_SIZE]
        proc = _run_git(repo_root, ["hash-object", "--", *chunk])
        if proc.returncode != 0:
            continue
        for path, blob in zip(chunk, proc.stdout.splitlines()):
            if blob.strip():
                blobs[path] = blob.strip()
    return blobs


def _shared_index_entry_states(repo_root: Path, paths: Sequence[str]) -> dict[str, dict[str, Any]]:
    path_list = list(
        dict.fromkeys(
            str(path or "").strip("/")
            for path in paths
            if str(path or "").strip("/")
        )
    )
    head_infos, _errors = _head_blob_info_for_paths(repo_root, path_list)
    head_blobs = {
        path: str(info.get("object") or "")
        for path, info in head_infos.items()
        if isinstance(info, Mapping) and info.get("object")
    }
    index_blobs = _index_blob_info_for_paths(repo_root, path_list)
    worktree_blobs = _worktree_blobs_for_paths(repo_root, path_list)
    return {
        path: _shared_index_entry_state_from_blobs(
            path,
            head_blob=head_blobs.get(path),
            index_blob=index_blobs.get(path),
            worktree_blob=worktree_blobs.get(path),
        )
        for path in path_list
    }


def _current_head(repo_root: Path) -> str | None:
    return _git_stdout(repo_root, ["rev-parse", "HEAD"])


def _task_ledger_tail_hash(repo_root: Path) -> str | None:
    path = repo_root / TASK_LEDGER_EVENTS
    if not path.is_file():
        return None
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return None
        return str(row.get("event_hash") or "").strip() or None
    return None


def _task_ledger_subject_rows(repo_root: Path, target_ids: Sequence[str]) -> list[dict[str, Any]]:
    targets = {str(item or "").strip() for item in target_ids if str(item or "").strip()}
    if not targets:
        return []
    path = repo_root / "state/task_ledger/ledger.json"
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    rows = payload.get("work_items") if isinstance(payload, Mapping) else None
    if not isinstance(rows, list):
        ledger = payload.get("ledger") if isinstance(payload, Mapping) else {}
        rows = ledger.get("work_items") if isinstance(ledger, Mapping) else []
    return [
        dict(row)
        for row in rows
        if isinstance(row, Mapping) and str(row.get("id") or "").strip() in targets
    ]


def _phase_work_ledger_event_path(repo_root: Path, phase_id: str | None) -> Path | None:
    token = str(phase_id or "").strip()
    if not token:
        return None
    path = repo_root / "codex" / "ledger" / token / "work_ledger.jsonl"
    return path if path.is_file() else None


def _load_work_ledger_events(repo_root: Path, phase_id: str | None) -> list[dict[str, Any]]:
    path = _phase_work_ledger_event_path(repo_root, phase_id)
    if path is None:
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, Mapping):
            rows.append(dict(row))
    return rows


def _append_unique(items: list[str], value: Any) -> None:
    token = str(value or "").strip()
    if token and token not in items:
        items.append(token)


def _event_subject_refs(event: Mapping[str, Any]) -> list[str]:
    metadata = event.get("metadata") if isinstance(event.get("metadata"), Mapping) else {}
    refs: list[str] = []
    for key in (
        "subject_id",
        "task_ledger_subject",
        "task_ledger_work_item_id",
        "receipt_target_id",
        "cap_id",
    ):
        _append_unique(refs, metadata.get(key))
    bridge = (
        metadata.get("task_ledger_work_item_bridge")
        if isinstance(metadata.get("task_ledger_work_item_bridge"), Mapping)
        else {}
    )
    _append_unique(refs, bridge.get("task_ledger_work_item_id"))
    _append_unique(refs, bridge.get("requested_work_ledger_td_id"))
    return refs


def _commit_refs_from_event(event: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    metadata = event.get("metadata") if isinstance(event.get("metadata"), Mapping) else {}
    _append_unique(refs, metadata.get("commit_hash"))
    resolution = event.get("resolution_episode") if isinstance(event.get("resolution_episode"), Mapping) else {}
    if str(resolution.get("kind") or "") == "git_commit":
        _append_unique(refs, resolution.get("ref"))
    for ref in event.get("evidence_refs") or []:
        token = str(ref or "").strip()
        if token.startswith("commit:"):
            token = token.split(":", 1)[1].strip()
        if re.fullmatch(r"[0-9a-f]{7,40}", token):
            _append_unique(refs, token)
    return refs


def _recover_transaction_id_from_event_context(
    grouped: Mapping[str, Mapping[str, Any]],
    event: Mapping[str, Any],
) -> str:
    """Recover a transaction id for close events that omitted direct metadata.

    Work Ledger close events can carry the commit/blocker evidence but omit the
    original transaction id. Only recover when td/session/read-receipt context
    points at exactly one already-seen transaction row.
    """
    td_id = str(event.get("td_id") or "").strip()
    session_id = str(event.get("actor_session_id") or "").strip()
    read_receipt_id = str(event.get("read_receipt_id") or "").strip()
    if not td_id and not session_id and not read_receipt_id:
        return ""

    matches: list[str] = []
    for transaction_id, row in grouped.items():
        td_ids = {str(item or "").strip() for item in row.get("work_ledger_td_ids") or []}
        session_ids = {str(item or "").strip() for item in row.get("actor_session_ids") or []}
        read_receipt_ids = {str(item or "").strip() for item in row.get("read_receipt_ids") or []}
        if (
            (td_id and td_id in td_ids)
            or (session_id and session_id in session_ids)
            or (read_receipt_id and read_receipt_id in read_receipt_ids)
        ):
            matches.append(str(transaction_id))
    return matches[0] if len(matches) == 1 else ""


def _work_ledger_transaction_rows(
    *,
    repo_root: Path,
    phase_id: str | None,
    target_ids: Sequence[str],
) -> list[dict[str, Any]]:
    targets = {str(item or "").strip() for item in target_ids if str(item or "").strip()}
    grouped: dict[str, dict[str, Any]] = {}
    for event in _load_work_ledger_events(repo_root, phase_id):
        metadata = event.get("metadata") if isinstance(event.get("metadata"), Mapping) else {}
        transaction_id = str(metadata.get("transaction_id") or "").strip()
        subject_refs = _event_subject_refs(event)
        if not transaction_id:
            transaction_id = _recover_transaction_id_from_event_context(grouped, event)
        if not transaction_id:
            continue
        if targets and not (targets & set(subject_refs)) and transaction_id not in grouped:
            continue
        row = grouped.setdefault(
            transaction_id,
            {
                "transaction_id": transaction_id,
                "phase_id": phase_id,
                "task_ledger_subjects": [],
                "work_ledger_td_ids": [],
                "work_ledger_event_ids": [],
                "work_ledger_event_kinds": [],
                "actor_session_ids": [],
                "read_receipt_ids": [],
                "commit_refs": [],
                "read_set_hash": None,
                "write_set_hash": None,
                "title": None,
                "last_event_at": None,
                "work_ledger_closed": False,
            },
        )
        for ref in subject_refs:
            _append_unique(row["task_ledger_subjects"], ref)
        _append_unique(row["work_ledger_td_ids"], event.get("td_id"))
        _append_unique(row["work_ledger_event_ids"], event.get("event_id"))
        _append_unique(row["work_ledger_event_kinds"], event.get("event_kind"))
        _append_unique(row["actor_session_ids"], event.get("actor_session_id"))
        _append_unique(row["read_receipt_ids"], event.get("read_receipt_id"))
        for commit_ref in _commit_refs_from_event(event):
            _append_unique(row["commit_refs"], commit_ref)
        row["read_set_hash"] = row.get("read_set_hash") or metadata.get("read_set_hash")
        row["write_set_hash"] = row.get("write_set_hash") or metadata.get("write_set_hash")
        row["title"] = row.get("title") or event.get("title")
        row["last_event_at"] = event.get("created_at") or row.get("last_event_at")
        if str(event.get("event_kind") or "") == "todo_close":
            row["work_ledger_closed"] = True
    return sorted(
        grouped.values(),
        key=lambda row: str(row.get("last_event_at") or ""),
        reverse=True,
    )


def _closed_work_ledger_session_ids(repo_root: Path, phase_id: str | None) -> set[str]:
    closed: set[str] = set()
    for event in _load_work_ledger_events(repo_root, phase_id):
        if str(event.get("event_kind") or "") != "todo_close":
            continue
        session_id = str(event.get("actor_session_id") or "").strip()
        if session_id:
            closed.add(session_id)
    return closed


def _append_exempt_work_ledger_session_ids(
    repo_root: Path,
    phase_id: str | None,
    target_ids: Sequence[str],
) -> set[str]:
    targets = {str(item or "").strip() for item in target_ids if str(item or "").strip()}
    exempt: set[str] = set()
    for event in _load_work_ledger_events(repo_root, phase_id):
        metadata = event.get("metadata") if isinstance(event.get("metadata"), Mapping) else {}
        source_session_id = str(metadata.get("source_session_id") or "").strip()
        if not source_session_id:
            continue
        subject_refs = set(_event_subject_refs(event))
        if targets and not (targets & subject_refs):
            continue
        exempt.add(source_session_id)
    return exempt


def _task_ledger_receipt_refs(subject_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    receipt_ids: list[str] = []
    commit_refs: list[str] = []
    work_ledger_refs: list[str] = []
    receipt_refs: list[str] = []
    receipts: list[dict[str, Any]] = []
    for row in subject_rows:
        for ref in row.get("receipt_refs") or []:
            _append_unique(receipt_refs, ref)
        for ref in row.get("commit_refs") or []:
            _append_unique(commit_refs, ref)
        for ref in row.get("work_ledger_refs") or []:
            _append_unique(work_ledger_refs, ref)
        for receipt in row.get("execution_receipts") or []:
            if not isinstance(receipt, Mapping):
                continue
            receipt_row = dict(receipt)
            receipts.append(receipt_row)
            _append_unique(receipt_ids, receipt_row.get("id"))
            _append_unique(receipt_ids, receipt_row.get("transaction_id"))
            _append_unique(receipt_refs, receipt_row.get("transaction_id"))
            _append_unique(commit_refs, receipt_row.get("commit_hash"))
            for ref in receipt_row.get("commit_refs") or []:
                _append_unique(commit_refs, ref)
            for ref in receipt_row.get("work_ledger_refs") or []:
                _append_unique(work_ledger_refs, ref)
    return {
        "receipt_ids": receipt_ids,
        "commit_refs": commit_refs,
        "work_ledger_refs": work_ledger_refs,
        "receipt_refs": receipt_refs,
        "execution_receipts": receipts,
    }


def _receipt_context_commit_refs(
    transaction: Mapping[str, Any],
    receipt_refs: Mapping[str, Any],
) -> list[str]:
    session_ids = {
        str(item or "").strip()
        for item in transaction.get("actor_session_ids") or []
        if str(item or "").strip()
    }
    read_receipt_ids = {
        str(item or "").strip()
        for item in transaction.get("read_receipt_ids") or []
        if str(item or "").strip()
    }
    if not session_ids and not read_receipt_ids:
        return []

    refs: list[str] = []
    for receipt in receipt_refs.get("execution_receipts") or []:
        if not isinstance(receipt, Mapping):
            continue
        receipt_session = str(receipt.get("work_ledger_session_id") or "").strip()
        receipt_read = str(receipt.get("read_receipt_id") or "").strip()
        if not (
            (receipt_session and receipt_session in session_ids)
            or (receipt_read and receipt_read in read_receipt_ids)
        ):
            continue
        _append_unique(refs, receipt.get("commit_hash"))
        for ref in receipt.get("commit_refs") or []:
            _append_unique(refs, ref)
    return refs


def _work_ledger_session_state_for_receipt(
    runtime_status: Mapping[str, Any],
    receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    receipt = _mapping_value(receipt)
    session_id = str(receipt.get("work_ledger_session_id") or "").strip()
    read_receipt_id = str(receipt.get("read_receipt_id") or "").strip()
    if not session_id and not read_receipt_id:
        return {}
    sessions = runtime_status.get("sessions") if isinstance(runtime_status.get("sessions"), Mapping) else {}
    session = _mapping_value(sessions.get(session_id)) if session_id else {}
    return {
        "session_id": session_id or session.get("session_id"),
        "read_receipt_id": session.get("read_receipt_id") or read_receipt_id or None,
        "phase_id": session.get("phase_id"),
        "ended_at": session.get("ended_at"),
        "session_had_ledger_append": session.get("session_had_ledger_append")
        if session
        else None,
        "stale": session.get("stale") if session else None,
        "stale_reason": session.get("stale_reason") if session else None,
        "source": "runtime_status" if session else "receipt_reference_only",
    }


def _receipt_status_for_transaction(
    transaction: Mapping[str, Any],
    receipt_refs: Mapping[str, Any],
) -> dict[str, Any]:
    transaction_id = str(transaction.get("transaction_id") or "").strip()
    commit_refs = {str(ref) for ref in transaction.get("commit_refs") or [] if str(ref).strip()}
    recorded_by_transaction = transaction_id and (
        transaction_id in set(receipt_refs.get("receipt_refs") or [])
        or transaction_id in set(receipt_refs.get("receipt_ids") or [])
    )
    recorded_by_commit = bool(commit_refs & set(receipt_refs.get("commit_refs") or []))
    recorded = bool(recorded_by_transaction or recorded_by_commit)
    return {
        "status": "recorded" if recorded else "missing",
        "matched_by": (
            "transaction_id"
            if recorded_by_transaction
            else ("commit_ref" if recorded_by_commit else None)
        ),
    }


def _session_finalizer_status(
    transaction: Mapping[str, Any],
    runtime_status: Mapping[str, Any],
    append_exempt_session_ids: Iterable[str] = (),
) -> dict[str, Any]:
    sessions = runtime_status.get("sessions") if isinstance(runtime_status.get("sessions"), Mapping) else {}
    append_exempt_ids = {str(item or "").strip() for item in append_exempt_session_ids if str(item).strip()}
    session_rows: list[dict[str, Any]] = []
    stale_ids: list[str] = []
    for session_id in transaction.get("actor_session_ids") or []:
        session = sessions.get(str(session_id))
        if not isinstance(session, Mapping):
            continue
        session_rows.append(
            {
                "session_id": session_id,
                "ended_at": session.get("ended_at"),
                "stale": bool(session.get("stale")),
                "stale_reason": session.get("stale_reason"),
                "session_had_ledger_append": bool(session.get("session_had_ledger_append")),
            }
        )
        if session.get("stale"):
            stale_ids.append(str(session_id))
    stale_ids_append_exempt = bool(stale_ids and all(session_id in append_exempt_ids for session_id in stale_ids))
    if stale_ids and (transaction.get("work_ledger_closed") or stale_ids_append_exempt):
        status = "append_exempt"
    elif stale_ids:
        status = "stale_requires_drain"
    elif transaction.get("work_ledger_closed"):
        status = "closed_clean"
    elif session_rows:
        status = "open_or_unfinalized"
    else:
        status = "unknown_session"
    return {
        "status": status,
        "sessions": session_rows,
        "stale_session_ids": stale_ids,
    }


def _receipt_recorded_for_current_transaction(
    current_transaction: Mapping[str, Any],
    receipt_refs: Mapping[str, Any],
) -> bool:
    return bool(_receipt_for_current_transaction(current_transaction, receipt_refs))


def _receipt_for_current_transaction(
    current_transaction: Mapping[str, Any],
    receipt_refs: Mapping[str, Any],
) -> dict[str, Any] | None:
    transaction_id = str(current_transaction.get("transaction_id") or "").strip()
    commit_hash = str(current_transaction.get("base_head") or "").strip()
    for receipt in receipt_refs.get("execution_receipts") or []:
        if not isinstance(receipt, Mapping):
            continue
        receipt_transaction_id = str(receipt.get("transaction_id") or receipt.get("id") or "").strip()
        receipt_commit_refs = {
            str(ref).strip()
            for ref in [receipt.get("commit_hash"), *(receipt.get("commit_refs") or [])]
            if str(ref or "").strip()
        }
        if transaction_id and receipt_transaction_id == transaction_id:
            return dict(receipt)
        if commit_hash and commit_hash in receipt_commit_refs:
            return dict(receipt)
    recorded_by_transaction = bool(
        transaction_id
        and (
            transaction_id in set(receipt_refs.get("receipt_refs") or [])
            or transaction_id in set(receipt_refs.get("receipt_ids") or [])
        )
    )
    recorded_by_commit = bool(commit_hash and commit_hash in set(receipt_refs.get("commit_refs") or []))
    if recorded_by_transaction or recorded_by_commit:
        return {
            "transaction_id": transaction_id or None,
            "commit_hash": commit_hash or None,
        }
    return None


def _receipt_for_current_transaction_or_session(
    current_transaction: Mapping[str, Any],
    receipt_refs: Mapping[str, Any],
    *,
    session_id: str | None,
    read_receipt_id: str | None,
) -> dict[str, Any] | None:
    current_receipt = _receipt_for_current_transaction(current_transaction, receipt_refs)
    if current_receipt:
        return current_receipt
    session_token = str(session_id or "").strip()
    read_receipt_token = str(read_receipt_id or "").strip()
    if not session_token and not read_receipt_token:
        return None
    receipts = [
        receipt
        for receipt in receipt_refs.get("execution_receipts") or []
        if isinstance(receipt, Mapping)
    ]
    for receipt in reversed(receipts):
        receipt_session = str(receipt.get("work_ledger_session_id") or "").strip()
        receipt_read = str(receipt.get("read_receipt_id") or "").strip()
        if session_token and receipt_session == session_token:
            return dict(receipt)
        if read_receipt_token and receipt_read == read_receipt_token:
            return dict(receipt)
    return None


def _matching_transaction_row(
    transaction_rows: Sequence[Mapping[str, Any]],
    transaction_id: str,
) -> Mapping[str, Any] | None:
    if not transaction_id:
        return None
    for row in transaction_rows:
        if str(row.get("transaction_id") or "").strip() == transaction_id:
            return row
    return None


def _transaction_row_has_session(row: Mapping[str, Any], session_id: str | None) -> bool:
    token = str(session_id or "").strip()
    if not token:
        return False
    return token in {str(item or "").strip() for item in row.get("actor_session_ids") or []}


def _transaction_context_tokens(row: Mapping[str, Any], key: str) -> set[str]:
    return {str(item or "").strip() for item in row.get(key) or [] if str(item or "").strip()}


def _same_attempt_context(left: Mapping[str, Any], right: Mapping[str, Any] | None) -> bool:
    if not isinstance(right, Mapping):
        return False
    return bool(
        _transaction_context_tokens(left, "actor_session_ids")
        & _transaction_context_tokens(right, "actor_session_ids")
    ) or bool(
        _transaction_context_tokens(left, "read_receipt_ids")
        & _transaction_context_tokens(right, "read_receipt_ids")
    )


def _superseded_by_canonical_convergence(
    row: Mapping[str, Any],
    *,
    canonical_transaction_id: str,
    canonical_row: Mapping[str, Any] | None,
) -> bool:
    if not canonical_transaction_id:
        return False
    transaction_id = str(row.get("transaction_id") or "").strip()
    if not transaction_id or transaction_id == canonical_transaction_id:
        return False
    return _same_attempt_context(row, canonical_row)


def _compact_transaction_attempt(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(row, Mapping):
        return None
    return {
        "transaction_id": row.get("transaction_id"),
        "phase_id": row.get("phase_id"),
        "work_ledger_td_ids": list(row.get("work_ledger_td_ids") or []),
        "actor_session_ids": list(row.get("actor_session_ids") or []),
        "read_receipt_ids": list(row.get("read_receipt_ids") or []),
        "commit_refs": list(row.get("commit_refs") or []),
        "work_ledger_closed": bool(row.get("work_ledger_closed")),
        "task_ledger_execution_receipt": row.get("task_ledger_execution_receipt"),
        "work_ledger_session_finalizer": row.get("work_ledger_session_finalizer"),
        "converged": bool(row.get("converged")),
        "last_event_at": row.get("last_event_at"),
    }


def _workitem_landing_attempt_state(
    *,
    target_ids: Sequence[str],
    query_session_id: str | None,
    current_transaction: Mapping[str, Any],
    transaction_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify real WorkItem landing attempts vs advisory preflight candidates."""
    session_key = str(query_session_id or "").strip() or None
    current_transaction_id = str(current_transaction.get("transaction_id") or "").strip()
    closed_rows = [row for row in transaction_rows if row.get("converged")]
    active_rows = [
        row
        for row in transaction_rows
        if not row.get("converged") and not row.get("work_ledger_closed")
    ]
    session_rows = [
        row for row in transaction_rows if _transaction_row_has_session(row, session_key)
    ] if session_key else []
    session_closed = [row for row in session_rows if row.get("converged")]
    session_active = [
        row
        for row in session_rows
        if not row.get("converged") and not row.get("work_ledger_closed")
    ]
    latest_closed = session_closed[0] if session_closed else (closed_rows[0] if closed_rows else None)
    active_attempt = session_active[0] if session_active else (active_rows[0] if active_rows else None)

    if session_key and session_closed:
        role = "closed_attempt"
        canonical_row = session_closed[0]
        canonical_state = "converged"
        canonical_source = "closed_work_landing_attempt_converged"
        mutation_requires_begin = True
    elif session_key and session_active:
        role = "active_attempt"
        canonical_row = session_active[0]
        canonical_state = "active"
        canonical_source = "active_work_landing_attempt"
        mutation_requires_begin = False
    elif not session_key and closed_rows:
        role = "sessionless_latest_closed_attempt"
        canonical_row = closed_rows[0]
        canonical_state = "converged"
        canonical_source = "latest_work_landing_attempt_converged"
        mutation_requires_begin = True
    else:
        role = "advisory_candidate"
        canonical_row = None
        canonical_state = "active"
        canonical_source = "current_candidate"
        mutation_requires_begin = True

    return {
        "schema": WORKITEM_LANDING_ATTEMPT_STATE_SCHEMA,
        "subject_ids": [str(item) for item in target_ids if str(item).strip()],
        "query_session_id": session_key,
        "active_attempt": _compact_transaction_attempt(active_attempt),
        "latest_closed_attempt": _compact_transaction_attempt(latest_closed),
        "candidate_role": role,
        "transaction_candidate_role": role,
        "canonical_transaction_id": (
            canonical_row.get("transaction_id") if isinstance(canonical_row, Mapping) else current_transaction_id or None
        ),
        "canonical_transaction_state": canonical_state,
        "canonical_transaction_source": canonical_source,
        "mutation_requires_begin": mutation_requires_begin,
        "advisory_transaction_id": current_transaction_id or None,
        "recommended_next_action": (
            "work_landing.py begin before mutation"
            if mutation_requires_begin
            else "continue bound WorkItem landing attempt"
        ),
    }


def _attempt_state_overrides_current(
    current_transaction: Mapping[str, Any],
    attempt_state: Mapping[str, Any],
) -> bool:
    if str(attempt_state.get("candidate_role") or "") not in {
        "closed_attempt",
        "sessionless_latest_closed_attempt",
    }:
        return False
    latest_closed = attempt_state.get("latest_closed_attempt")
    if not isinstance(latest_closed, Mapping):
        return False
    current_id = str(current_transaction.get("transaction_id") or "").strip()
    latest_id = str(latest_closed.get("transaction_id") or "").strip()
    return bool(latest_id and current_id != latest_id)


def _current_finalizer_classes(
    *,
    raw_finalizers: Sequence[Mapping[str, Any]],
    current_transaction: Mapping[str, Any],
    current_execution_receipt: Mapping[str, Any] | None,
    transaction_rows: Sequence[Mapping[str, Any]],
    receipt_refs: Mapping[str, Any],
    receipt_bound_session_state: Mapping[str, Any],
    shared_index_quarantine: Mapping[str, Any],
    attempt_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    transaction_id = str(current_transaction.get("transaction_id") or "").strip()
    matching_recent = _matching_transaction_row(transaction_rows, transaction_id)
    recent_converged = bool(matching_recent and matching_recent.get("converged"))
    current_receipt = _mapping_value(current_execution_receipt) or _receipt_for_current_transaction(
        current_transaction,
        receipt_refs,
    )
    receipt_recorded = bool(current_receipt)
    receipt_transaction_id = str(
        (current_receipt or {}).get("transaction_id")
        or (current_receipt or {}).get("id")
        or ""
    ).strip()
    receipt_recent = (
        _matching_transaction_row(transaction_rows, receipt_transaction_id)
        if receipt_transaction_id
        else None
    )
    session_clean = bool(
        matching_recent
        and matching_recent.get("work_ledger_closed")
        and (
            (matching_recent.get("work_ledger_session_finalizer") or {}).get("status")
            in {"append_exempt", "closed_clean", "unknown_session"}
        )
    )
    receipt_bound_session_clean = _session_closed_clean(receipt_bound_session_state)
    session_clean = bool(session_clean or (receipt_recorded and receipt_bound_session_clean))
    transaction_local: list[dict[str, Any]] = []
    ambient_pressure: list[dict[str, Any]] = []
    compatibility_finalizers: list[dict[str, Any]] = [dict(row) for row in raw_finalizers]
    attempt_state = dict(attempt_state or {})
    advisory_requires_begin = (
        str(attempt_state.get("candidate_role") or "") == "advisory_candidate"
        and bool(attempt_state.get("mutation_requires_begin"))
        and not isinstance(attempt_state.get("active_attempt"), Mapping)
    )
    for index, finalizer in enumerate(raw_finalizers):
        finalizer_id = str(finalizer.get("id") or "").strip()
        row = dict(finalizer)
        compatibility_row = compatibility_finalizers[index]
        if finalizer_id == "staged_index_empty":
            if (
                shared_index_quarantine.get("private_index_scoped_commit_allowed")
                and not _int_value(shared_index_quarantine.get("overlap_count"))
            ):
                row["pressure_class"] = "ambient_shared_index_pressure"
                row["local_to_transaction"] = False
                row["reason"] = "unrelated_staged_paths_do_not_block_private_index_transaction_convergence"
                ambient_pressure.append(row)
                continue
        if advisory_requires_begin:
            row["compatibility_status"] = "advisory_candidate_requires_work_landing_begin"
            row["local_to_transaction"] = False
            compatibility_row["compatibility_status"] = row["compatibility_status"]
            compatibility_row["local_to_transaction"] = False
            continue
        if recent_converged:
            row["compatibility_status"] = "superseded_by_recent_converged"
            compatibility_row["compatibility_status"] = row["compatibility_status"]
            continue
        if finalizer_id == "task_ledger_execution_receipt" and receipt_recorded:
            row["compatibility_status"] = "satisfied_by_exact_receipt_evidence"
            compatibility_row["compatibility_status"] = row["compatibility_status"]
            continue
        if finalizer_id in {"claims_released", "session_not_stale_or_exempt", "work_ledger_append_or_exempt"} and session_clean:
            row["compatibility_status"] = "satisfied_by_closed_work_ledger_transaction"
            compatibility_row["compatibility_status"] = row["compatibility_status"]
            continue
        transaction_local.append(row)
    if _attempt_state_overrides_current(current_transaction, attempt_state):
        latest_closed = dict(attempt_state.get("latest_closed_attempt") or {})
        for row in compatibility_finalizers:
            row["compatibility_status"] = "superseded_by_workitem_landing_attempt"
        transaction_local = []
        canonical_state = "converged"
        canonical_source = str(
            attempt_state.get("canonical_transaction_source")
            or "latest_work_landing_attempt_converged"
        )
        shadow_state = "advisory_candidate_superseded_by_workitem_landing_attempt"
        canonical_transaction_id = str(latest_closed.get("transaction_id") or "").strip() or transaction_id
        canonical_recent = latest_closed
        canonical_recent_converged = True
        canonical_receipt_recorded = True
        canonical_session_clean = True
    elif matching_recent and recent_converged:
        canonical_state = "converged"
        canonical_source = "recent_transaction_converged"
        shadow_state = "superseded_by_recent_converged"
        canonical_transaction_id = transaction_id or None
        canonical_recent = dict(matching_recent)
        canonical_recent_converged = recent_converged
        canonical_receipt_recorded = receipt_recorded
        canonical_session_clean = session_clean
    elif advisory_requires_begin:
        canonical_state = "advisory_requires_begin"
        canonical_source = "advisory_candidate_requires_work_landing_begin"
        shadow_state = "advisory_candidate_requires_work_landing_begin"
        canonical_transaction_id = transaction_id or None
        canonical_recent = dict(matching_recent) if isinstance(matching_recent, Mapping) else None
        canonical_recent_converged = recent_converged
        canonical_receipt_recorded = receipt_recorded
        canonical_session_clean = session_clean
    elif receipt_recorded and receipt_bound_session_clean:
        canonical_state = "converged"
        canonical_source = "receipt_bound_work_ledger_session_closed_clean"
        shadow_state = "superseded_by_receipt_bound_work_ledger_session"
        canonical_transaction_id = receipt_transaction_id or transaction_id or None
        canonical_recent = (
            dict(receipt_recent)
            if isinstance(receipt_recent, Mapping)
            else (dict(matching_recent) if isinstance(matching_recent, Mapping) else None)
        )
        canonical_recent_converged = True
        canonical_receipt_recorded = True
        canonical_session_clean = True
    elif receipt_recorded or session_clean:
        canonical_state = "partially_reconciled"
        canonical_source = "stronger_receipt_or_work_ledger_evidence"
        shadow_state = "partially_superseded_by_stronger_evidence"
        canonical_transaction_id = transaction_id or None
        canonical_recent = dict(matching_recent) if isinstance(matching_recent, Mapping) else None
        canonical_recent_converged = recent_converged
        canonical_receipt_recorded = receipt_recorded
        canonical_session_clean = session_clean
    else:
        canonical_state = "active"
        canonical_source = "current_candidate"
        shadow_state = "active"
        canonical_transaction_id = transaction_id or None
        canonical_recent = dict(matching_recent) if isinstance(matching_recent, Mapping) else None
        canonical_recent_converged = recent_converged
        canonical_receipt_recorded = receipt_recorded
        canonical_session_clean = session_clean
    return {
        "transaction_local_finalizers": transaction_local,
        "ambient_pressure": ambient_pressure,
        "compatibility_finalizers": compatibility_finalizers,
        "current_transaction_shadow_state": shadow_state,
        "canonical_transaction_state": {
            "transaction_id": canonical_transaction_id,
            "state": canonical_state,
            "source": canonical_source,
            "recent_transaction_converged": canonical_recent_converged,
            "receipt_recorded": canonical_receipt_recorded,
            "work_ledger_closed_clean": canonical_session_clean,
            "matched_recent_transaction": canonical_recent,
        },
    }


def _target_claim_scope_id(claim: Mapping[str, Any]) -> str:
    scope_kind = str(claim.get("scope_kind") or "").strip()
    if scope_kind == "work_item_id":
        return str(claim.get("work_item_id") or claim.get("scope_id") or "").strip()
    if scope_kind == "td_id":
        return str(claim.get("td_id") or claim.get("scope_id") or "").strip()
    return str(claim.get("scope_id") or "").strip()


def _target_claim_scope_kind(target_id: str) -> str:
    return "td_id" if str(target_id or "").startswith("td_") else "work_item_id"


def _target_stale_sessions(
    runtime_status: Mapping[str, Any],
    *,
    target_ids: Sequence[str],
    phase_id: str | None,
    closed_work_ledger_session_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    targets = {str(item or "").strip() for item in target_ids if str(item or "").strip()}
    closed_sessions = {str(item or "").strip() for item in closed_work_ledger_session_ids if str(item).strip()}
    sessions = runtime_status.get("sessions") if isinstance(runtime_status.get("sessions"), Mapping) else {}
    rows: list[dict[str, Any]] = []
    for session_id, session in sessions.items():
        if not isinstance(session, Mapping) or not session.get("stale"):
            continue
        if str(session_id) in closed_sessions:
            continue
        touched_td_ids = {
            str(item).strip() for item in session.get("touched_td_ids") or [] if str(item).strip()
        }
        touched_work_item_ids = {
            str(item).strip()
            for item in session.get("touched_work_item_ids") or []
            if str(item).strip()
        }
        claim_scopes = {
            _target_claim_scope_id(claim)
            for claim in session.get("claims") or []
            if isinstance(claim, Mapping)
        }
        phase_matches = not phase_id or str(session.get("phase_id") or "") == str(phase_id)
        target_matches = not targets or bool(targets & (touched_td_ids | touched_work_item_ids | claim_scopes))
        if not (phase_matches and target_matches):
            continue
        rows.append(
            {
                "session_id": str(session_id),
                "phase_id": session.get("phase_id"),
                "touched_td_ids": sorted(touched_td_ids),
                "touched_work_item_ids": sorted(touched_work_item_ids),
                "stale_reason": session.get("stale_reason"),
                "ended_at": session.get("ended_at"),
                "finalizer_status": "stale_requires_drain",
            }
        )
    return sorted(rows, key=lambda row: str(row.get("ended_at") or ""), reverse=True)


def _target_append_exempt_sessions(
    runtime_status: Mapping[str, Any],
    *,
    target_ids: Sequence[str],
    phase_id: str | None,
    closed_work_ledger_session_ids: Iterable[str],
) -> list[dict[str, Any]]:
    targets = {str(item or "").strip() for item in target_ids if str(item or "").strip()}
    closed_sessions = {str(item or "").strip() for item in closed_work_ledger_session_ids if str(item).strip()}
    sessions = runtime_status.get("sessions") if isinstance(runtime_status.get("sessions"), Mapping) else {}
    rows: list[dict[str, Any]] = []
    for session_id, session in sessions.items():
        if str(session_id) not in closed_sessions:
            continue
        if not isinstance(session, Mapping) or not session.get("stale"):
            continue
        touched_td_ids = {
            str(item).strip() for item in session.get("touched_td_ids") or [] if str(item).strip()
        }
        touched_work_item_ids = {
            str(item).strip()
            for item in session.get("touched_work_item_ids") or []
            if str(item).strip()
        }
        claim_scopes = {
            _target_claim_scope_id(claim)
            for claim in session.get("claims") or []
            if isinstance(claim, Mapping)
        }
        phase_matches = not phase_id or str(session.get("phase_id") or "") == str(phase_id)
        target_matches = not targets or bool(targets & (touched_td_ids | touched_work_item_ids | claim_scopes))
        if not (phase_matches and target_matches):
            continue
        rows.append(
            {
                "session_id": str(session_id),
                "phase_id": session.get("phase_id"),
                "touched_td_ids": sorted(touched_td_ids),
                "touched_work_item_ids": sorted(touched_work_item_ids),
                "stale_reason": session.get("stale_reason"),
                "ended_at": session.get("ended_at"),
                "finalizer_status": "append_exempt_by_work_ledger_closeout",
            }
        )
    return sorted(rows, key=lambda row: str(row.get("ended_at") or ""), reverse=True)


def _dirty_tree_class_budget_rows(dirty_tree: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for class_id, count in sorted((dirty_tree.get("by_class") or {}).items()):
        policy = DERIVED_STATE_BLOAT_POLICIES.get(str(class_id), {})
        budget = policy.get("budget")
        rows.append(
            {
                "class_id": class_id,
                "count": int(count or 0),
                "budget": budget,
                "budget_status": (
                    "over_budget"
                    if budget is not None and int(count or 0) > int(budget)
                    else ("within_budget" if budget is not None else "unconfigured_observed")
                ),
                "owner_hint": policy.get("owner_hint")
                or DIRTY_TREE_CLASS_OWNERS.get(str(class_id), "classification_owner_unmapped"),
                "blocks_landing": False,
            }
        )
    return rows


def _git_capture(repo_root: Path, *args: str) -> tuple[int, str, str]:
    result = _run_git(repo_root, list(args))
    return result.returncode, result.stdout, result.stderr


def _resolve_github_push_range(repo_root: Path) -> dict[str, Any]:
    code, head_out, head_err = _git_capture(repo_root, "rev-parse", "HEAD")
    if code != 0:
        return {
            "mode": "not_git_repo",
            "status": "watch",
            "head": None,
            "base": None,
            "base_ref": None,
            "reason": "git_head_unavailable",
            "error": head_err.strip() or head_out.strip(),
        }
    head = head_out.strip()

    upstream_code, upstream_out, _ = _git_capture(
        repo_root,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
    )
    if upstream_code == 0 and upstream_out.strip():
        upstream = upstream_out.strip()
        base_code, base_out, base_err = _git_capture(repo_root, "merge-base", "HEAD", upstream)
        if base_code == 0 and base_out.strip():
            base = base_out.strip()
            return {
                "mode": "push_range",
                "status": "clear",
                "head": head,
                "base": base,
                "base_ref": upstream,
                "push_range": f"{base}..HEAD",
                "base_resolution": "upstream",
            }
        return {
            "mode": "no_merge_base",
            "status": "watch",
            "head": head,
            "base": None,
            "base_ref": upstream,
            "reason": "upstream_merge_base_unavailable",
            "error": base_err.strip() or base_out.strip(),
        }

    origin_code, _, _ = _git_capture(repo_root, "rev-parse", "--verify", "origin/main")
    if origin_code == 0:
        base_code, base_out, base_err = _git_capture(repo_root, "merge-base", "HEAD", "origin/main")
        if base_code == 0 and base_out.strip():
            base = base_out.strip()
            return {
                "mode": "push_range",
                "status": "clear",
                "head": head,
                "base": base,
                "base_ref": "origin/main",
                "push_range": f"{base}..HEAD",
                "base_resolution": "origin_main_fallback_no_upstream",
            }
        return {
            "mode": "no_merge_base",
            "status": "watch",
            "head": head,
            "base": None,
            "base_ref": "origin/main",
            "reason": "origin_main_merge_base_unavailable",
            "error": base_err.strip() or base_out.strip(),
        }

    return {
        "mode": "no_upstream",
        "status": "watch",
        "head": head,
        "base": None,
        "base_ref": None,
        "reason": "no_upstream_or_origin_main_push_base",
    }


def _changed_paths_in_push_range(repo_root: Path, base: str) -> list[dict[str, Any]]:
    code, out, err = _git_capture(repo_root, "diff", "--name-status", "-z", f"{base}..HEAD")
    if code != 0:
        return [{"status": "error", "path": "", "error": err.strip() or out.strip()}]
    tokens = out.split("\0")
    rows: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if not status:
            continue
        if status[0] in {"R", "C"}:
            if index + 1 >= len(tokens):
                break
            old_path = tokens[index]
            new_path = tokens[index + 1]
            index += 2
            rows.append({"status": status, "path": new_path, "old_path": old_path})
            continue
        if index >= len(tokens):
            break
        path = tokens[index]
        index += 1
        if path:
            rows.append({"status": status, "path": path})
    return rows


def _annex_artifact_policy_for_path(path: str) -> dict[str, Any] | None:
    token = str(path or "").strip("/")
    if not token.startswith("annexes/"):
        return None
    rel = token.removeprefix("annexes/").strip("/")
    if not rel:
        return {
            "schema": DERIVED_ARTIFACT_POLICY_SCHEMA,
            "path": token,
            "owner_id": ANNEX_ARTIFACT_POLICY_OWNER,
            "artifact_class": "annex_root",
            "bloat_class": "annex_unclassified_payload",
            "git_policy": "directory_scope_requires_specific_annex_artifact_policy",
            "push_gate_disposition": "blocked",
            "reason": "annex_root_without_specific_artifact",
            "owner_check_command": "./repo-python annex_import.py validate --all --read-only",
            "owner_repair_command": "./repo-python annex_import.py catalog --write",
        }

    parts = rel.split("/")
    name = parts[-1].lower()
    in_repo_checkout = len(parts) >= 2 and parts[1] == "repo"
    is_external_source = (
        name in ANNEX_EXTERNAL_SOURCE_NAMES
        or name.startswith("source.")
        or any(name.endswith(suffix) for suffix in ANNEX_EXTERNAL_SOURCE_SUFFIXES)
    )
    if rel == "annex_distillation_index.json":
        artifact_class = "annex_distillation_rollup_projection"
        bloat_class = "annex_durable_generated_projection"
        git_policy = "durable_repo_wide_read_model_with_annex_owner_tool"
        disposition = "watch"
        reason = "repo_wide_distillation_projection_is_committable_only_with_owner_builder"
    elif name in ANNEX_SYNC_DIGEST_FILES and len(parts) == 1:
        artifact_class = "annex_sync_digest_projection"
        bloat_class = "annex_durable_generated_projection"
        git_policy = "durable_sync_digest_read_model_with_annex_digest_owner_tool"
        disposition = "watch"
        reason = "annex_sync_digest_surfaces_are_committable_only_from_annex_import_digest"
    elif rel == "annex_catalog.json" or name in ANNEX_RECONSTRUCTABLE_LOCAL_FILES:
        artifact_class = "annex_reconstructable_local_projection"
        bloat_class = "annex_reconstructable_local_projection"
        git_policy = "ignored_or_manifest_only_unless_owner_explicitly_claims_durable_read_model"
        disposition = "blocked"
        reason = "reconstructable_annex_projection_should_not_enter_push_range_unmanifested"
    elif name in ANNEX_RUNTIME_DIAGNOSTIC_FILES:
        artifact_class = "annex_runtime_diagnostic"
        bloat_class = "annex_runtime_diagnostic"
        git_policy = "local_validate_or_sync_diagnostic_never_push"
        disposition = "blocked"
        reason = "annex_runtime_diagnostic_should_not_enter_push_range"
    elif in_repo_checkout:
        artifact_class = "annex_external_checkout_tree"
        bloat_class = "annex_external_payload"
        git_policy = "local_only_external_checkout_never_push_raw_payload"
        disposition = "blocked"
        reason = "annex_source_checkout_is_external_payload"
    elif is_external_source:
        artifact_class = "annex_external_source_payload"
        bloat_class = "annex_external_payload"
        git_policy = "manifest_or_pointer_only_for_external_source_payload"
        disposition = "blocked"
        reason = "annex_source_payload_requires_manifest_or_external_artifact_store"
    elif name in ANNEX_DURABLE_AUTHORITY_FILES:
        artifact_class = "annex_durable_authority"
        bloat_class = "annex_durable_metadata"
        git_policy = "durable_annex_metadata_authority"
        disposition = "allowed"
        reason = "annex_metadata_or_distillation_authority_is_source_like"
    elif name in ANNEX_DURABLE_GENERATED_FILES:
        artifact_class = "annex_durable_generated_read_model"
        bloat_class = "annex_durable_generated_projection"
        git_policy = "durable_read_model_only_with_annex_owner_tool_and_source_fingerprints"
        disposition = "watch"
        reason = "annex_navigation_projection_is_committable_but_must_stay_owner_tool_bound"
    elif _is_manifest_or_pointer_path(token):
        artifact_class = "annex_manifest_or_pointer"
        bloat_class = "annex_manifest_or_pointer"
        git_policy = "manifest_or_pointer_allowed_for_artifact_payload"
        disposition = "allowed"
        reason = "manifest_or_pointer_represents_payload_without_raw_artifact_blob"
    else:
        artifact_class = "annex_unclassified_payload"
        bloat_class = "annex_unclassified_payload"
        git_policy = "owner_classification_required_before_push"
        disposition = "blocked"
        reason = "annex_path_lacks_known_artifact_policy"

    return {
        "schema": DERIVED_ARTIFACT_POLICY_SCHEMA,
        "path": token,
        "owner_id": ANNEX_ARTIFACT_POLICY_OWNER,
        "artifact_class": artifact_class,
        "bloat_class": bloat_class,
        "git_policy": git_policy,
        "push_gate_disposition": disposition,
        "reason": reason,
        "owner_check_command": "./repo-python annex_import.py validate --all --read-only",
        "owner_repair_command": "./repo-python annex_import.py catalog --write",
    }


def _push_bloat_class_for_path(path: str) -> str | None:
    token = str(path or "").strip("/")
    if not token:
        return None
    if _is_reconstructable_build_output_path(token):
        return "tracked_build_output"
    annex_policy = _annex_artifact_policy_for_path(token)
    if annex_policy is not None:
        return str(annex_policy.get("bloat_class") or "annex_unclassified_payload")
    if token == TASK_LEDGER_EVENTS or _is_task_ledger_projection(token):
        return "task_ledger_event_or_projection"
    if "/annex" in token:
        return "annex_projection_or_digest"
    if token.startswith(WORK_LEDGER_PREFIXES) or classify_path(token).get("generation_class") == "work_ledger_write_profile_surface":
        return "work_ledger_event_or_projection"
    if any(marker in token for marker in RAW_OR_OPERATOR_STATE_MARKERS):
        return "raw_seed_or_operator_state"
    if token.startswith("dist/"):
        return "distribution_packet"
    classification = classify_path(token)
    if classification.get("coverage_gap"):
        return "generated_projection_unknown_owner"
    if classification.get("generation_class") == "registered_generated_projection":
        return "generated_projection_expected"
    return None


def _path_segments(path: str) -> list[str]:
    return [segment for segment in str(path or "").strip("/").split("/") if segment]


def _is_reconstructable_build_output_path(path: str) -> bool:
    segments = _path_segments(path)
    return any(segment in RECONSTRUCTABLE_BUILD_OUTPUT_SEGMENTS for segment in segments)


def _build_output_root_for_path(path: str) -> str | None:
    segments = _path_segments(path)
    for index, segment in enumerate(segments):
        if segment in RECONSTRUCTABLE_BUILD_OUTPUT_SEGMENTS:
            return "/".join(segments[: index + 1])
    return None


def _build_output_ignore_file_for_root(root: str) -> str:
    segments = _path_segments(root)
    if ".build" in segments:
        build_index = segments.index(".build")
        if build_index > 0:
            return "/".join([*segments[:build_index], ".gitignore"])
    if "DerivedData" in segments:
        return ".gitignore"
    return ".gitignore"


def _build_output_repair_command(root: str | None) -> str:
    build_root = str(root or "<build-output-path>").strip("/") or "<build-output-path>"
    ignore_file = _build_output_ignore_file_for_root(build_root) if root else "<ignore-file>"
    return (
        "./repo-python tools/meta/control/scoped_commit.py tracked-removals "
        f"--remove-path {shlex.quote(build_root)} "
        f"--path {shlex.quote(ignore_file)} "
        "--message \"chore: stop tracking build output\""
    )


def _format_commit_ref_line(line: str) -> dict[str, Any] | None:
    parts = str(line or "").split("\t", 2)
    if not parts or not parts[0].strip():
        return None
    commit = parts[0].strip()
    date = parts[1].strip() if len(parts) > 1 else None
    subject = parts[2].strip() if len(parts) > 2 else ""
    return {
        "commit": commit,
        "short": commit[:12],
        "date": date,
        "subject": subject,
    }


def _tracked_build_output_origin(repo_root: Path, paths: Sequence[str]) -> dict[str, Any]:
    roots = sorted(
        {
            root
            for path in paths
            if (root := _build_output_root_for_path(path))
        }
    )
    if not roots:
        return {
            "roots": [],
            "first_introducing_commit": None,
            "recent_touching_commits": [],
            "status": "no_tracked_build_output_paths",
        }

    root_rows: list[dict[str, Any]] = []
    recent_by_commit: dict[str, dict[str, Any]] = {}
    first_introducing: dict[str, Any] | None = None
    for root in roots[:3]:
        first_proc = _run_git(
            repo_root,
            ["log", "--reverse", "--diff-filter=A", "--format=%H%x09%cs%x09%s", "--", root],
        )
        first_rows = [
            row
            for line in first_proc.stdout.splitlines()
            if (row := _format_commit_ref_line(line)) is not None
        ] if first_proc.returncode == 0 else []
        recent_proc = _run_git(
            repo_root,
            ["log", "--max-count=5", "--format=%H%x09%cs%x09%s", "--", root],
        )
        recent_rows = [
            row
            for line in recent_proc.stdout.splitlines()
            if (row := _format_commit_ref_line(line)) is not None
        ] if recent_proc.returncode == 0 else []
        if first_rows and first_introducing is None:
            first_introducing = dict(first_rows[0])
            first_introducing["path_root"] = root
        for row in recent_rows:
            commit = str(row.get("commit") or "")
            if commit and commit not in recent_by_commit:
                copied = dict(row)
                copied["path_root"] = root
                recent_by_commit[commit] = copied
        root_rows.append(
            {
                "path_root": root,
                "first_introducing_commit": first_rows[0] if first_rows else None,
                "recent_touching_commits": recent_rows,
                "diagnostic_status": "ok"
                if first_proc.returncode == 0 and recent_proc.returncode == 0
                else "git_log_unavailable",
            }
        )

    return {
        "roots": root_rows,
        "first_introducing_commit": first_introducing,
        "recent_touching_commits": list(recent_by_commit.values())[:5],
        "status": "ok",
    }


def _is_manifest_or_pointer_path(path: str) -> bool:
    token = str(path or "").strip("/").lower()
    name = Path(token).name
    return (
        token == ".gitattributes"
        or token.endswith(".dvc")
        or token.endswith(".pointer")
        or token.endswith(".manifest.json")
        or name in {"manifest.json", "artifacts.json", "artifact_manifest.json"}
        or "manifest" in name
    )


def _head_blob_info_for_paths(
    repo_root: Path,
    paths: Sequence[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    blobs: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    path_list = [str(path or "").strip("/") for path in paths if str(path or "").strip("/")]
    timeout_seconds = _git_command_timeout_seconds()
    for index in range(0, len(path_list), GIT_LS_TREE_CHUNK_SIZE):
        chunk = path_list[index:index + GIT_LS_TREE_CHUNK_SIZE]
        command = ["git", "ls-tree", "-rz", "-l", "HEAD", "--", *chunk]
        try:
            result = subprocess.run(
                command,
                cwd=repo_root,
                text=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            errors.append(
                f"git command timed out after {timeout_seconds:g}s: git ls-tree for {len(chunk)} paths"
            )
            stderr = _process_output_text(exc.stderr).strip()
            if stderr:
                errors.append(stderr)
            continue
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(str(exc))
            continue
        if result.returncode != 0:
            stderr = _process_output_text(result.stderr).strip()
            errors.append(stderr or f"git ls-tree exited {result.returncode}")
            continue
        for raw_entry in result.stdout.split(b"\0"):
            if not raw_entry:
                continue
            entry = raw_entry.decode("utf-8", errors="surrogateescape")
            meta, separator, path = entry.partition("\t")
            if not separator or not path:
                continue
            parts = meta.split()
            if len(parts) < 4:
                continue
            _mode, object_type, object_name, size_text = parts[:4]
            if object_type != "blob":
                continue
            try:
                size = int(size_text)
            except ValueError:
                continue
            blobs[path] = {
                "object": object_name,
                "object_type": object_type,
                "bytes": size,
            }
    return blobs, [error for error in errors if error]


def _push_range_blob_rows(repo_root: Path, changed_paths: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    candidate_changes: list[Mapping[str, Any]] = []
    for changed in changed_paths:
        status = str(changed.get("status") or "")
        path = str(changed.get("path") or "").strip("/")
        if not path or status.startswith("D") or status == "error" or path in seen:
            continue
        seen.add(path)
        candidate_changes.append(changed)
    blob_info, errors = _head_blob_info_for_paths(
        repo_root,
        [str(changed.get("path") or "") for changed in candidate_changes],
    )
    if errors:
        rows.append({"status": "error", "path": "", "error": "; ".join(errors)})
    for changed in candidate_changes:
        status = str(changed.get("status") or "")
        path = str(changed.get("path") or "").strip("/")
        info = blob_info.get(path)
        if not info:
            continue
        size = int(info.get("bytes") or 0)
        class_id = _push_bloat_class_for_path(path)
        rows.append(
            {
                "path": path,
                "status": status,
                "object": info.get("object"),
                "bytes": size,
                "bloat_class": class_id,
                "artifact_policy": _annex_artifact_policy_for_path(path),
                "manifest_or_pointer": _is_manifest_or_pointer_path(path),
            }
        )
    return rows


def _git_int_stdout(repo_root: Path, *args: str) -> int | None:
    value = _git_stdout(repo_root, list(args))
    if value is None:
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None


def _git_commit_summary(repo_root: Path, rev: str) -> dict[str, Any] | None:
    value = _git_stdout(repo_root, ["show", "-s", "--format=%H%x09%cs%x09%s", rev])
    if not value:
        return None
    return _format_commit_ref_line(value)


def _recent_push_range_commits(
    repo_root: Path,
    push_range: str | None,
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    token = str(push_range or "").strip()
    if not token:
        return []
    value = _git_stdout(
        repo_root,
        ["log", f"--max-count={int(limit)}", "--format=%H%x09%cs%x09%s", token],
    )
    if not value:
        return []
    return [
        row
        for line in value.splitlines()
        if (row := _format_commit_ref_line(line)) is not None
    ]


def _push_blob_row_is_blocking(row: Mapping[str, Any]) -> bool:
    size = int(row.get("bytes") or 0)
    manifest_or_pointer = bool(row.get("manifest_or_pointer"))
    artifact_policy = (
        row.get("artifact_policy")
        if isinstance(row.get("artifact_policy"), Mapping)
        else {}
    )
    class_id = str(row.get("bloat_class") or "").strip()
    push_disposition = str(artifact_policy.get("push_gate_disposition") or "").strip()
    return (
        not manifest_or_pointer
        and (
            push_disposition == "blocked"
            or class_id in PUSH_BLOAT_BLOCKER_CLASSES
            or size >= GITHUB_BLOB_HARD_LIMIT_BYTES
        )
    )


def _compact_push_blob_row(row: Mapping[str, Any]) -> dict[str, Any]:
    artifact_policy = (
        row.get("artifact_policy")
        if isinstance(row.get("artifact_policy"), Mapping)
        else {}
    )
    return {
        "path": row.get("path"),
        "status": row.get("status"),
        "bytes": row.get("bytes"),
        "bloat_class": row.get("bloat_class"),
        "artifact_class": artifact_policy.get("artifact_class") or row.get("artifact_class"),
        "push_gate_disposition": artifact_policy.get("push_gate_disposition") or row.get("push_gate_disposition"),
        "reason": artifact_policy.get("reason") or row.get("reason"),
        "manifest_or_pointer": row.get("manifest_or_pointer"),
    }


def _publication_recovery_packet(
    repo_root: Path,
    *,
    range_info: Mapping[str, Any],
    blob_rows: Sequence[Mapping[str, Any]],
    status: str,
    blocked_reasons: Sequence[str],
    watch_reasons: Sequence[str],
) -> dict[str, Any]:
    push_range = str(range_info.get("push_range") or "").strip()
    base_ref = str(range_info.get("base_ref") or "").strip() or None
    commit_count = _git_int_stdout(repo_root, "rev-list", "--count", push_range) if push_range else None
    remote_ahead_count = (
        _git_int_stdout(repo_root, "rev-list", "--count", f"HEAD..{base_ref}")
        if base_ref
        else None
    )
    blocking_rows = [row for row in blob_rows if _push_blob_row_is_blocking(row)]
    blocking_class_counts: dict[str, int] = {}
    for row in blocking_rows:
        class_id = str(row.get("bloat_class") or "unclassified").strip() or "unclassified"
        blocking_class_counts[class_id] = blocking_class_counts.get(class_id, 0) + 1

    blocked = str(status or "") == "blocked"
    long_range = bool(
        commit_count is not None
        and commit_count >= PUSH_RANGE_CONTAMINATION_COMMIT_THRESHOLD
        and blocking_rows
    )
    failure_class = (
        "contaminated_local_publication_range"
        if long_range
        else ("blocked_push_range" if blocked else ("review_push_range" if watch_reasons else "clear"))
    )
    safe_next_command = "./repo-python tools/meta/control/publication_lane.py plan --repo-root ."
    return {
        "schema": PUBLICATION_RECOVERY_SCHEMA,
        "status": "required" if blocked else ("review" if watch_reasons else "not_required"),
        "failure_class": failure_class,
        "direct_push_allowed": not blocked,
        "base_ref": base_ref,
        "push_range": push_range or None,
        "push_range_commit_count": commit_count,
        "remote_ahead_count": remote_ahead_count,
        "blocked_reason_count": len(blocked_reasons),
        "watch_reason_count": len(watch_reasons),
        "blocked_path_count": len(blocking_rows),
        "blocking_class_counts": dict(sorted(blocking_class_counts.items())),
        "blocking_paths_preview": [
            _compact_push_blob_row(row)
            for row in blocking_rows[:COMPACT_PREVIEW_LIMIT]
        ],
        "recent_local_commits": _recent_push_range_commits(repo_root, push_range),
        "head_commit": _git_commit_summary(repo_root, "HEAD"),
        "recommended_lane": "detached_clean_ref_publish" if blocked else None,
        "safe_next_command": safe_next_command if blocked else None,
        "proof_route": "./repo-python tools/meta/control/mission_transaction_preflight.py --github-push-bloat-gate",
        "operator_boundary": (
            "This packet is read-only. Applying the clean lane creates or updates git refs "
            "and requires an explicit selected commit list and publication target."
        ),
        "history_rewrite_allowed_by_this_packet": False,
        "force_push_allowed_by_this_packet": False,
        "why": (
            "Direct push scans every object in the local push range. When earlier local-only commits "
            "contain forbidden runtime or annex artifacts, later clean commits cannot publish through "
            "that same range; move the intended clean commit set onto a clean base or run an operator-owned sanitation pass."
        ),
    }


def _github_push_bloat_gate(
    repo_root: Path,
    *,
    dirty_tree: Mapping[str, Any],
    workspace_pressure: Mapping[str, Any],
) -> dict[str, Any]:
    range_info = _resolve_github_push_range(repo_root)
    base = range_info.get("base")
    head = range_info.get("head")
    gate: dict[str, Any] = {
        "schema": GITHUB_PUSH_BLOAT_GATE_SCHEMA,
        "mode": range_info.get("mode"),
        "base_ref": range_info.get("base_ref"),
        "base": base,
        "head": head,
        "push_range": range_info.get("push_range"),
        "workspace_dirty_count": int(dirty_tree.get("dirty_path_count") or 0),
        "workspace_dirty_is_push_gate": False,
        "workspace_pressure": {
            "schema": workspace_pressure.get("schema"),
            "status": workspace_pressure.get("status"),
            "primary_class": workspace_pressure.get("primary_class"),
            "primary_count": workspace_pressure.get("primary_count"),
        },
        "git_sizer_available": shutil.which("git-sizer") is not None,
        "new_blob_count": 0,
        "changed_path_count": 0,
        "large_blob_count": 0,
        "generated_push_class_counts": {},
        "blocked_reasons": [],
        "watch_reasons": [],
        "large_blobs": [],
        "generated_paths": [],
        "policy": "GitHub push is gated by push-range blobs and generated classes; dirty worktree pressure is reported separately.",
    }
    if range_info.get("mode") != "push_range" or not base:
        gate["status"] = "watch"
        gate["watch_reasons"] = [str(range_info.get("reason") or range_info.get("mode") or "push_range_unavailable")]
        if range_info.get("error"):
            gate["error"] = range_info.get("error")
        gate["publication_recovery"] = _publication_recovery_packet(
            repo_root,
            range_info=range_info,
            blob_rows=[],
            status=str(gate["status"]),
            blocked_reasons=gate["blocked_reasons"],
            watch_reasons=gate["watch_reasons"],
        )
        return gate

    changed_paths = _changed_paths_in_push_range(repo_root, str(base))
    if any(row.get("status") == "error" for row in changed_paths):
        gate["status"] = "watch"
        gate["watch_reasons"] = ["push_range_diff_unavailable"]
        gate["errors"] = [row.get("error") for row in changed_paths if row.get("error")]
        gate["publication_recovery"] = _publication_recovery_packet(
            repo_root,
            range_info=range_info,
            blob_rows=[],
            status=str(gate["status"]),
            blocked_reasons=gate["blocked_reasons"],
            watch_reasons=gate["watch_reasons"],
        )
        return gate

    blob_rows = _push_range_blob_rows(repo_root, changed_paths)
    if any(row.get("status") == "error" for row in blob_rows):
        gate["changed_path_count"] = len(changed_paths)
        gate["status"] = "watch"
        gate["watch_reasons"] = ["push_range_blob_scan_unavailable"]
        gate["errors"] = [row.get("error") for row in blob_rows if row.get("error")]
        gate["publication_recovery"] = _publication_recovery_packet(
            repo_root,
            range_info=range_info,
            blob_rows=[],
            status=str(gate["status"]),
            blocked_reasons=gate["blocked_reasons"],
            watch_reasons=gate["watch_reasons"],
        )
        return gate
    generated_counts: dict[str, int] = {}
    generated_paths: list[dict[str, Any]] = []
    large_blobs: list[dict[str, Any]] = []
    blocked_reasons: set[str] = set()
    watch_reasons: set[str] = set()
    for row in blob_rows:
        class_id = row.get("bloat_class")
        size = int(row.get("bytes") or 0)
        manifest_or_pointer = bool(row.get("manifest_or_pointer"))
        artifact_policy = (
            row.get("artifact_policy")
            if isinstance(row.get("artifact_policy"), Mapping)
            else {}
        )
        push_disposition = str(artifact_policy.get("push_gate_disposition") or "").strip()
        if class_id:
            generated_counts[str(class_id)] = generated_counts.get(str(class_id), 0) + 1
            generated_paths.append(row)
            if (
                push_disposition == "blocked"
                or class_id in PUSH_BLOAT_BLOCKER_CLASSES
            ) and not manifest_or_pointer:
                blocked_reasons.add("generated_artifact_without_owner_policy")
                if artifact_policy:
                    blocked_reasons.add("annex_artifact_policy_blocks_push")
            elif push_disposition == "watch":
                watch_reasons.add("durable_annex_artifact_requires_owner_review")
        if size >= GITHUB_BLOB_RECOMMENDED_LIMIT_BYTES:
            large_blobs.append(row)
            if size >= GITHUB_BLOB_HARD_LIMIT_BYTES and not manifest_or_pointer:
                blocked_reasons.add("github_hard_blob_limit_exceeded")
            elif (
                push_disposition == "blocked"
                or class_id in PUSH_BLOAT_BLOCKER_CLASSES
            ) and not manifest_or_pointer:
                blocked_reasons.add("large_unmanifested_blob_in_push_range")
            else:
                watch_reasons.add("large_blob_in_push_range_requires_review")
        elif class_id and class_id not in PUSH_BLOAT_BLOCKER_CLASSES:
            watch_reasons.add("durable_generated_or_ledger_blob_in_push_range")

    gate.update(
        {
            "changed_path_count": len(changed_paths),
            "new_blob_count": len(blob_rows),
            "large_blob_count": len(large_blobs),
            "generated_push_class_counts": dict(sorted(generated_counts.items())),
            "blocked_reasons": sorted(blocked_reasons),
            "watch_reasons": sorted(watch_reasons),
            "large_blobs": sorted(large_blobs, key=lambda item: int(item.get("bytes") or 0), reverse=True)[
                :COMPACT_PREVIEW_LIMIT
            ],
            "generated_paths": generated_paths[:COMPACT_PREVIEW_LIMIT],
        }
    )
    if blocked_reasons:
        gate["status"] = "blocked"
    elif watch_reasons:
        gate["status"] = "watch"
    else:
        gate["status"] = "clear"
    gate["publication_recovery"] = _publication_recovery_packet(
        repo_root,
        range_info=range_info,
        blob_rows=blob_rows,
        status=str(gate["status"]),
        blocked_reasons=gate["blocked_reasons"],
        watch_reasons=gate["watch_reasons"],
    )
    return gate


def _omitted_github_push_bloat_gate(
    *,
    dirty_tree: Mapping[str, Any],
    workspace_pressure: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": GITHUB_PUSH_BLOAT_GATE_SCHEMA,
        "status": "clear",
        "mode": "local_preflight_fast_path",
        "omitted": True,
        "omit_reason": (
            "Cheap local/control-summary preflight omits the push-range blob scan; "
            "open the push gate drilldown when the mission is at a publication boundary."
        ),
        "base_ref": None,
        "base": None,
        "head": None,
        "push_range": None,
        "workspace_dirty_count": int(dirty_tree.get("dirty_path_count") or 0),
        "workspace_dirty_is_push_gate": False,
        "workspace_pressure": {
            "schema": workspace_pressure.get("schema"),
            "status": workspace_pressure.get("status"),
            "primary_class": workspace_pressure.get("primary_class"),
            "primary_count": workspace_pressure.get("primary_count"),
        },
        "git_sizer_available": shutil.which("git-sizer") is not None,
        "new_blob_count": None,
        "changed_path_count": None,
        "large_blob_count": None,
        "generated_push_class_counts": {},
        "blocked_reasons": [],
        "watch_reasons": [],
        "large_blobs": [],
        "generated_paths": [],
        "publication_recovery": {
            "schema": PUBLICATION_RECOVERY_SCHEMA,
            "status": "not_required",
            "failure_class": "local_preflight_not_publication_boundary",
            "direct_push_allowed": None,
            "base_ref": None,
            "push_range": None,
            "push_range_commit_count": None,
            "remote_ahead_count": None,
            "blocked_reason_count": 0,
            "watch_reason_count": 0,
            "blocked_path_count": 0,
            "blocking_class_counts": {},
            "blocking_paths_preview": [],
            "recent_local_commits": [],
            "head_commit": None,
            "recommended_lane": None,
            "safe_next_command": "./repo-python tools/meta/control/mission_transaction_preflight.py --github-push-bloat-gate",
            "proof_route": "./repo-python tools/meta/control/mission_transaction_preflight.py --github-push-bloat-gate",
            "operator_boundary": "This local preflight did not evaluate publication readiness.",
            "history_rewrite_allowed_by_this_packet": False,
            "force_push_allowed_by_this_packet": False,
            "why": "Local/control-summary landing checks should not pay for a push-range object scan.",
        },
        "policy": (
            "GitHub push is gated only by the explicit push bloat drilldown or full bloat governor; "
            "this local packet is not push proof."
        ),
    }


def _derived_artifact_policy(
    *,
    status_rows: Sequence[GitStatusRow],
) -> dict[str, Any]:
    static_examples = [
        "annexes/<slug>/annex_family.json",
        "annexes/<slug>/annex_notes.json",
        "annexes/<slug>/distillation.json",
        "annexes/<slug>/annex_index.json",
        "annexes/<slug>/annex_contents.json",
        "annexes/annex_distillation_index.json",
        "annexes/annex_sync_digest.json",
        "annexes/annex_sync_digest.md",
        "annexes/annex_sync_digest_run_state.json",
        "annexes/<slug>/repo/<path>",
        "annexes/<slug>/source.pdf",
        "annexes/<slug>/source.tar.gz",
        "annexes/<slug>/manifest.json",
    ]
    policy_rows = [
        _annex_artifact_policy_for_path(example.replace("<slug>", "example").replace("<path>", "README.md"))
        for example in static_examples
    ]
    policy_rows = [row for row in policy_rows if row is not None]

    observed: dict[str, dict[str, Any]] = {}
    staged_blocking_paths: list[str] = []
    dirty_blocking_paths: list[str] = []
    for status_row in status_rows:
        policy = _annex_artifact_policy_for_path(status_row.path)
        if policy is None:
            continue
        artifact_class = str(policy.get("artifact_class") or "annex_unclassified_payload")
        summary = observed.setdefault(
            artifact_class,
            {
                "artifact_class": artifact_class,
                "count": 0,
                "staged_count": 0,
                "push_gate_disposition": policy.get("push_gate_disposition"),
                "git_policy": policy.get("git_policy"),
                "example_paths": [],
            },
        )
        summary["count"] = int(summary.get("count") or 0) + 1
        if status_row.is_staged:
            summary["staged_count"] = int(summary.get("staged_count") or 0) + 1
        examples = summary.setdefault("example_paths", [])
        if isinstance(examples, list) and len(examples) < COMPACT_PREVIEW_LIMIT:
            examples.append(status_row.path)
        if policy.get("push_gate_disposition") == "blocked":
            dirty_blocking_paths.append(status_row.path)
            if status_row.is_staged:
                staged_blocking_paths.append(status_row.path)

    status = "blocked" if staged_blocking_paths else ("watch" if observed else "clear")
    return {
        "schema": DERIVED_ARTIFACT_POLICY_SCHEMA,
        "status": status,
        "owner_id": ANNEX_ARTIFACT_POLICY_OWNER,
        "authority": {
            "policy_owner": "system/lib/mission_transaction_landing_preflight.py",
            "annex_owner_tool": "annex_import.py",
            "annex_registry": "system/lib/annex_registry.py",
            "generated_projection_registry_owner": ANNEX_ARTIFACT_POLICY_OWNER,
        },
        "rules": [
            "annex metadata and distillation files are durable source-like authority",
            "annex_index.json and annex_distillation_index.json are durable read-model projections only with owner-tool provenance",
            "external source payloads, checkout trees, reconstructable contents, and unknown annex payloads are push-blocked unless represented by manifest or pointer",
            "workspace dirty annex pressure is local WIP pressure; push blocking is decided from push-range blobs",
        ],
        "policy_rows": policy_rows,
        "observed_annex_dirty_count": sum(int(row.get("count") or 0) for row in observed.values()),
        "observed_by_artifact_class": sorted(
            observed.values(),
            key=lambda row: str(row.get("artifact_class") or ""),
        ),
        "dirty_blocking_paths_preview": dirty_blocking_paths[:COMPACT_PREVIEW_LIMIT],
        "staged_blocking_paths_preview": staged_blocking_paths[:COMPACT_PREVIEW_LIMIT],
        "local_landing_policy": "annex dirty total does not block scoped local landing unless staged/unowned hard gates overlap the transaction",
        "push_policy": "github_push_bloat_gate_v1 blocks push-range raw external or unclassified annex payloads, not dirty worktree pressure alone",
    }


def _runtime_artifact_root(path: str) -> str:
    token = str(path or "").strip("/")
    parts = token.split("/")
    if token == STATION_RENDER_LOAD_INDEX:
        return token
    if (
        len(parts) >= 4
        and parts[0] == "state"
        and parts[1] == "observability"
        and parts[2] == "renders"
    ):
        return "/".join(parts[:4])
    if len(parts) >= 3 and parts[0] == "state" and parts[1] == "runs":
        return "/".join(parts[:3])
    return token


def _runtime_artifact_family(path: str) -> str:
    token = str(path or "").strip("/")
    if token == STATION_RENDER_LOAD_INDEX:
        return "station_render_latest_projection"
    if _is_station_render_receipt_artifact(token):
        return "station_render_receipt_artifact"
    return "runtime_run_artifact"


def _runtime_artifact_lifecycle(
    repo_root: Path,
    *,
    status_rows: Sequence[GitStatusRow],
) -> dict[str, Any]:
    """Read-only dry-run classifier for dirty state/runs artifacts.

    Runtime artifacts are receipts until an owner promotes or prunes them. This
    packet intentionally reports preservation/ownership facts and never deletes.
    """
    roots: dict[str, dict[str, Any]] = {}
    for row in status_rows:
        if not _is_runtime_artifact_lifecycle_path(row.path):
            continue
        root = _runtime_artifact_root(row.path)
        owner_family = _runtime_artifact_family(row.path)
        item = roots.setdefault(
            root,
            {
                "root": root,
                "run_id": root.split("/", 2)[2] if root.startswith("state/runs/") else root,
                "owner_family": owner_family,
                "artifact_kind": owner_family,
                "dirty_path_count": 0,
                "staged_path_count": 0,
                "file_count": 0,
                "total_size_bytes": 0,
                "oldest_mtime_epoch": None,
                "newest_mtime_epoch": None,
                "paths_sample": [],
                "has_runtime_context": False,
                "has_run_summary": False,
                "has_mission_manifest": False,
                "has_render_manifest": False,
                "cleanup_eligible": False,
                "safe_action": "preserve_or_claim_run_artifact"
                if owner_family == "runtime_run_artifact"
                else "preserve_latest_projection_or_promote_receipt_ref",
            },
        )
        item["dirty_path_count"] = int(item["dirty_path_count"]) + 1
        if row.is_staged:
            item["staged_path_count"] = int(item["staged_path_count"]) + 1
        if len(item["paths_sample"]) < COMPACT_PREVIEW_LIMIT:
            item["paths_sample"].append(row.path)
        path = repo_root / row.path
        if path.is_file():
            try:
                stat = path.stat()
            except OSError:
                stat = None
            if stat is not None:
                item["file_count"] = int(item["file_count"]) + 1
                item["total_size_bytes"] = int(item["total_size_bytes"]) + int(stat.st_size)
                mtime = float(stat.st_mtime)
                oldest = item.get("oldest_mtime_epoch")
                newest = item.get("newest_mtime_epoch")
                item["oldest_mtime_epoch"] = mtime if oldest is None else min(float(oldest), mtime)
                item["newest_mtime_epoch"] = mtime if newest is None else max(float(newest), mtime)
        rel_tail = row.path.removeprefix(f"{root}/")
        if rel_tail == "runtime_context.json":
            item["has_runtime_context"] = True
        elif rel_tail == "run_summary.json":
            item["has_run_summary"] = True
        elif rel_tail == "mission_manifest.json":
            item["has_mission_manifest"] = True
        elif rel_tail == "manifest.json":
            item["has_render_manifest"] = True

    root_rows = sorted(
        roots.values(),
        key=lambda item: (-int(item.get("dirty_path_count") or 0), str(item.get("root") or "")),
    )
    dirty_path_count = sum(int(item.get("dirty_path_count") or 0) for item in root_rows)
    staged_path_count = sum(int(item.get("staged_path_count") or 0) for item in root_rows)
    total_size_bytes = sum(int(item.get("total_size_bytes") or 0) for item in root_rows)
    return {
        "schema": RUNTIME_ARTIFACT_LIFECYCLE_SCHEMA,
        "status": "watch" if root_rows else "clear",
        "mode": "dry_run",
        "owner_family": "runtime_artifact_lifecycle",
        "artifact_root_count": len(root_rows),
        "dirty_path_count": dirty_path_count,
        "staged_path_count": staged_path_count,
        "total_size_bytes": total_size_bytes,
        "cleanup_eligible_count": 0,
        "cleanup_attempted": False,
        "apply_available": False,
        "dry_run_available": True,
        "retention_policy": "preserve_by_default_until_owner_claim_or_promotion",
        "live_process_check": "not_available",
        "roots": root_rows[:COMPACT_PREVIEW_LIMIT],
        "next_safe_action": "preserve_or_claim_run_artifact",
        "dry_run_command": RUNTIME_ARTIFACT_LIFECYCLE_DRY_RUN_COMMAND,
    }


def _derived_state_bloat_governor(
    repo_root: Path,
    *,
    dirty_tree: Mapping[str, Any],
    status_rows: Sequence[GitStatusRow],
    include_push_bloat_gate: bool = True,
) -> dict[str, Any]:
    derived_artifact_policy = _derived_artifact_policy(status_rows=status_rows)
    class_rows: list[dict[str, Any]] = []
    blocked_classes: list[str] = []
    watch_classes: list[str] = []
    by_class = dirty_tree.get("by_class") if isinstance(dirty_tree.get("by_class"), Mapping) else {}
    for class_id, raw_count in sorted(by_class.items()):
        count = int(raw_count or 0)
        policy = DERIVED_STATE_BLOAT_POLICIES.get(
            str(class_id),
            {
                "budget": None,
                "owner_hint": DIRTY_TREE_CLASS_OWNERS.get(str(class_id), "classification_owner_unmapped"),
                "allowed_git_policy": "unconfigured_class_requires_owner_review",
                "drain_or_manifest_command": "./repo-python tools/meta/control/mission_transaction_preflight.py --full <same args>",
                "push_block_threshold": None,
            },
        )
        budget = policy.get("budget")
        push_block_threshold = policy.get("push_block_threshold")
        if budget is not None and count > int(budget):
            budget_status = "over_budget"
        elif count:
            budget_status = "within_budget" if budget is not None else "unconfigured_observed"
        else:
            budget_status = "clear"
        if push_block_threshold is not None and count > int(push_block_threshold):
            push_risk = "blocked"
            blocked_classes.append(str(class_id))
        elif budget_status == "over_budget" or count:
            push_risk = "watch"
            watch_classes.append(str(class_id))
        else:
            push_risk = "clear"
        class_rows.append(
            {
                "class_id": class_id,
                "count": count,
                "budget": budget,
                "budget_status": budget_status,
                "owner_hint": policy.get("owner_hint"),
                "allowed_git_policy": policy.get("allowed_git_policy"),
                "push_risk": push_risk,
                "drain_or_manifest_command": policy.get("drain_or_manifest_command"),
                "blocks_local_landing": False,
            }
        )

    largest_dirty_files: list[dict[str, Any]] = []
    for row in status_rows:
        path = repo_root / row.path
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size >= 1_000_000:
            largest_dirty_files.append({"path": row.path, "bytes": size})
    largest_dirty_files.sort(key=lambda item: int(item["bytes"]), reverse=True)

    tracked_build_output_examples = [
        row.path
        for row in status_rows
        if _is_reconstructable_build_output_path(row.path)
    ][:COMPACT_PREVIEW_LIMIT]
    tracked_build_output_count = int(by_class.get("tracked_build_output") or 0)
    tracked_build_output_origin = _tracked_build_output_origin(
        repo_root,
        tracked_build_output_examples,
    ) if tracked_build_output_examples else {
        "roots": [],
        "first_introducing_commit": None,
        "recent_touching_commits": [],
        "status": "no_tracked_build_output_paths",
    }
    primary_build_output_root = (
        str((tracked_build_output_origin.get("roots") or [{}])[0].get("path_root") or "")
        if isinstance(tracked_build_output_origin.get("roots"), list)
        and tracked_build_output_origin.get("roots")
        else None
    )

    workspace_status = "blocked" if blocked_classes else ("watch" if watch_classes or largest_dirty_files else "clear")
    workspace_reasons: list[str] = []
    if blocked_classes:
        workspace_reasons.append("generated_or_derived_class_over_workspace_threshold")
    if largest_dirty_files:
        workspace_reasons.append("large_dirty_file_candidates_present")
    if watch_classes and not blocked_classes:
        workspace_reasons.append("derived_class_budget_watch")
    if tracked_build_output_count:
        workspace_reasons.append("tracked_build_output_quarantine")
    primary_class = (
        max(class_rows, key=lambda row: int(row.get("count") or 0)).get("class_id")
        if class_rows
        else None
    )
    primary_row = (
        next((row for row in class_rows if row.get("class_id") == primary_class), {})
        if primary_class is not None
        else {}
    )
    primary_count = 0
    if primary_class is not None:
        primary_count = int(primary_row.get("count") or 0)
    primary_next_action = None
    primary_command = str(primary_row.get("drain_or_manifest_command") or "").strip()
    if primary_command.startswith("./repo-python "):
        primary_next_action = primary_command
    workspace_pressure = {
        "schema": WORKSPACE_BLOAT_PRESSURE_SCHEMA,
        "status": workspace_status,
        "reasons": workspace_reasons,
        "owner_hint": primary_row.get("owner_hint"),
        "allowed_git_policy": primary_row.get("allowed_git_policy"),
        "drain_or_manifest_command": primary_row.get("drain_or_manifest_command"),
        "next_action": primary_next_action,
        "workspace_dirty_count": dirty_tree.get("dirty_path_count", 0),
        "workspace_dirty_is_push_gate": False,
        "blocked_classes": blocked_classes,
        "watch_classes": sorted(set(watch_classes)),
        "primary_class": primary_class,
        "primary_count": primary_count,
        "large_dirty_file_candidates": largest_dirty_files[:COMPACT_PREVIEW_LIMIT],
        "tracked_build_output_count": tracked_build_output_count,
        "tracked_build_output_examples": tracked_build_output_examples,
        "first_introducing_commit": tracked_build_output_origin.get("first_introducing_commit"),
        "recent_touching_commits": tracked_build_output_origin.get("recent_touching_commits", []),
        "tracked_build_output_origin": tracked_build_output_origin,
        "recommended_repair": _build_output_repair_command(primary_build_output_root)
        if tracked_build_output_count
        else None,
        "policy": "workspace dirty bloat is local pressure and owner-drain signal, not a GitHub push proof",
    }

    github_push_bloat_gate = (
        _github_push_bloat_gate(
            repo_root,
            dirty_tree=dirty_tree,
            workspace_pressure=workspace_pressure,
        )
        if include_push_bloat_gate
        else _omitted_github_push_bloat_gate(
            dirty_tree=dirty_tree,
            workspace_pressure=workspace_pressure,
        )
    )

    return {
        "schema": DERIVED_STATE_BLOAT_GOVERNOR_SCHEMA,
        "status": workspace_status,
        "total_dirty_count": dirty_tree.get("dirty_path_count", 0),
        "dirty_tree_total_is_local_landing_gate": False,
        "workspace_dirty_is_push_gate": False,
        "class_rows": class_rows,
        "primary_bloat_class": primary_class,
        "derived_artifact_policy": derived_artifact_policy,
        "workspace_bloat_pressure": workspace_pressure,
        "github_push_bloat_gate": github_push_bloat_gate,
    }


def _open_current_finalizers(finalizers: Mapping[str, Any]) -> list[dict[str, Any]]:
    satisfied = {"satisfied", "not_required", "recorded", "closed_clean", "append_exempt"}
    rows: list[dict[str, Any]] = []
    for name, finalizer in finalizers.items():
        if name == "schema" or not isinstance(finalizer, Mapping):
            continue
        status = str(finalizer.get("status") or "unknown")
        if status in satisfied:
            continue
        rows.append({"id": name, "status": status})
    return rows


def _deferred_generated_projection_required_next_command(reason: str) -> str:
    if reason == CONTROL_SUMMARY_SETTLEMENT_DEFERRED_REASON:
        return CONTROL_SUMMARY_FULL_PREFLIGHT_COMMAND
    if reason == WORKSPACE_BLOAT_PRESSURE_SETTLEMENT_DEFERRED_REASON:
        return BLOAT_GOVERNOR_COMMAND
    if reason == DEFAULT_COMPACT_SETTLEMENT_DEFERRED_REASON:
        return FULL_PREFLIGHT_COMMAND
    if reason == LOCAL_OWNED_PATH_SETTLEMENT_DEFERRED_REASON:
        return FULL_PREFLIGHT_COMMAND
    return GENERATED_SETTLEMENT_PLAN_COMMAND


def _deferred_generated_projection_settlement_plan(*, reason: str) -> dict[str, Any]:
    return {
        "schema": GENERATED_PROJECTION_SETTLEMENT_DEFERRED_SCHEMA,
        "status": "deferred",
        "reason": reason,
        "can_settle": True,
        "dirty_owner_count": 0,
        "refresh_required_owner_count": 0,
        "blocked_owner_count": 0,
        "supported_owner_ids": [],
        "owners": [],
        "blocked_by": [],
        "required_next_command": _deferred_generated_projection_required_next_command(reason),
        "eventful_closeout_allowed_after_settlement": False,
        "read_only": True,
    }


def _transaction_closeout_settlement(
    *,
    transaction_candidate: Mapping[str, Any],
    transaction_convergence: Mapping[str, Any],
    generated_projection_settlement: Mapping[str, Any],
) -> dict[str, Any]:
    """Join eventful closeout state with the final non-eventful settlement boundary."""
    current_transaction = (
        transaction_convergence.get("current_transaction")
        if isinstance(transaction_convergence.get("current_transaction"), Mapping)
        else {}
    )
    candidate_finalizers = (
        transaction_candidate.get("finalizers")
        if isinstance(transaction_candidate.get("finalizers"), Mapping)
        else {}
    )
    if "open_finalizers" in current_transaction:
        open_finalizers = [
            dict(row)
            for row in current_transaction.get("open_finalizers") or []
            if isinstance(row, Mapping)
        ]
    else:
        open_finalizers = _open_current_finalizers(candidate_finalizers)

    eventful_finalizer_details = [
        {
            "id": str(row.get("id") or ""),
            "status": str(row.get("status") or "unknown"),
        }
        for row in open_finalizers
        if str(row.get("id") or "") in EVENTFUL_CLOSEOUT_FINALIZER_IDS
    ]
    eventful_finalizers_pending = [row["id"] for row in eventful_finalizer_details]

    settlement_status = str(generated_projection_settlement.get("status") or "unknown")
    dirty_owner_count = _int_value(generated_projection_settlement.get("dirty_owner_count"))
    refresh_required_owner_count = _int_value(
        generated_projection_settlement.get("refresh_required_owner_count")
    )
    blocked_owner_count = _int_value(generated_projection_settlement.get("blocked_owner_count"))
    can_settle = bool(generated_projection_settlement.get("can_settle"))
    if settlement_status == "deferred":
        projection_settlement_status = "deferred"
    elif settlement_status == "clean":
        projection_settlement_status = "clean"
    elif settlement_status == "settlement_required" and can_settle and not blocked_owner_count:
        projection_settlement_status = "settlement_required"
    elif dirty_owner_count and can_settle and not blocked_owner_count and not refresh_required_owner_count:
        projection_settlement_status = "settlement_required"
    else:
        projection_settlement_status = "blocked"

    if eventful_finalizers_pending:
        status = "eventful_closeout_pending"
        required_next_command = "complete eventful Task/Work Ledger closeout before generated projection settlement"
    elif projection_settlement_status == "clean":
        status = "settled_final"
        required_next_command = None
    elif projection_settlement_status == "settlement_required":
        status = "settlement_required"
        required_next_command = (
            generated_projection_settlement.get("required_next_command")
            or "./repo-python tools/meta/control/generated_state_drainer.py settle --dry-run"
        )
    elif projection_settlement_status == "deferred":
        status = "deferred"
        required_next_command = generated_projection_settlement.get("required_next_command")
    else:
        status = "blocked"
        required_next_command = (
            generated_projection_settlement.get("required_next_command")
            or "./repo-python tools/meta/control/generated_state_drainer.py settlement-plan"
        )

    return {
        "schema": TRANSACTION_CLOSEOUT_SETTLEMENT_SCHEMA,
        "status": status,
        "eventful_finalizers_pending": eventful_finalizers_pending,
        "eventful_finalizer_details": eventful_finalizer_details,
        "projection_settlement_status": projection_settlement_status,
        "projection_settlement_plan_status": settlement_status,
        "projection_settlement_deferred_reason": generated_projection_settlement.get("reason"),
        "projection_dirty_owner_count": dirty_owner_count,
        "projection_refresh_required_owner_count": refresh_required_owner_count,
        "projection_blocked_owner_count": blocked_owner_count,
        "eventful_closeout_allowed_now": bool(eventful_finalizers_pending),
        "eventful_closeout_allowed_after_settlement": False,
        "required_next_command": required_next_command,
        "ordering_rule": "complete eventful Task/Work Ledger closeout before final generated projection settlement",
        "read_only": True,
        "settlement_actor": "./repo-python tools/meta/control/generated_state_drainer.py settle",
    }


def _path_status(path: str, status_rows: Sequence[GitStatusRow]) -> str:
    token = str(path or "").strip("/")
    matches = [
        row.to_dict()
        for row in status_rows
        if row.path == token or path_scope_overlaps(row.path, token) or path_scope_overlaps(token, row.path)
    ]
    if not matches:
        return "clean_or_untracked_not_in_status"
    if any(row.get("staged") for row in matches):
        return "staged"
    if any(row.get("worktree_dirty") for row in matches):
        return "modified"
    return "status_known"


def _path_fingerprint(repo_root: Path, path: str, status_rows: Sequence[GitStatusRow]) -> dict[str, Any]:
    token = str(path or "").strip("/")
    absolute = repo_root / token
    row: dict[str, Any] = {
        "path": token,
        "status": _path_status(token, status_rows),
    }
    if absolute.is_file():
        row["path_kind"] = "file"
        row["worktree_blob_hash"] = _git_stdout(repo_root, ["hash-object", "--", token])
    elif absolute.is_dir():
        tracked = (_git_stdout(repo_root, ["ls-files", "--", token]) or "").splitlines()
        row["path_kind"] = "directory"
        row["tracked_entry_count"] = len([item for item in tracked if item.strip()])
        row["tracked_entries_digest"] = _json_digest(sorted(item for item in tracked if item.strip()))
    elif absolute.exists():
        row["path_kind"] = "other"
    else:
        row["path_kind"] = "missing"
    return row


def _slug_token(value: str, *, fallback: str, limit: int = 48) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "_", str(value or "").strip()).strip("_")
    return (token or fallback)[:limit]


def _normalize_path(repo_root: Path, path: str) -> str:
    return normalize_repo_path(repo_root, path)


def _parse_porcelain_line(repo_root: Path, line: str) -> GitStatusRow | None:
    if not line:
        return None
    if len(line) < 3:
        return None
    index_status = line[0]
    worktree_status = line[1]
    raw_path = line[3:].strip()
    if not raw_path:
        return None
    original_path = None
    if " -> " in raw_path:
        original_path, raw_path = raw_path.split(" -> ", 1)
    return GitStatusRow(
        index_status=index_status,
        worktree_status=worktree_status,
        path=_normalize_path(repo_root, raw_path),
        original_path=_normalize_path(repo_root, original_path) if original_path else None,
    )


def _read_git_status_rows_with_diagnostics(
    repo_root: Path,
) -> tuple[list[GitStatusRow], list[dict[str, Any]]]:
    args = ["status", "--porcelain=v1"]
    proc = _run_git(repo_root, args)
    diagnostic = _git_command_diagnostic(
        purpose="git_status_porcelain",
        args=args,
        proc=proc,
    )
    if proc.returncode != 0:
        return [], [diagnostic] if diagnostic else []
    rows: list[GitStatusRow] = []
    for line in proc.stdout.splitlines():
        row = _parse_porcelain_line(repo_root, line)
        if row is not None:
            rows.append(row)
    return rows, []


def read_git_status_rows(repo_root: Path) -> list[GitStatusRow]:
    rows, _ = _read_git_status_rows_with_diagnostics(repo_root)
    return rows


def _read_cached_path_names_with_diagnostics(
    repo_root: Path,
) -> tuple[list[str], list[dict[str, Any]]]:
    args = ["diff", "--cached", "--name-only"]
    proc = _run_git(repo_root, args)
    diagnostic = _git_command_diagnostic(
        purpose="git_cached_path_names",
        args=args,
        proc=proc,
    )
    if proc.returncode != 0:
        return [], [diagnostic] if diagnostic else []
    return [
        _normalize_path(repo_root, line)
        for line in proc.stdout.splitlines()
        if line.strip()
    ], []


def read_cached_path_names(repo_root: Path) -> list[str]:
    paths, _ = _read_cached_path_names_with_diagnostics(repo_root)
    return paths


def _read_cached_stat_with_diagnostics(repo_root: Path) -> tuple[str, list[dict[str, Any]]]:
    args = ["diff", "--cached", "--stat"]
    proc = _run_git(repo_root, args)
    diagnostic = _git_command_diagnostic(
        purpose="git_cached_stat",
        args=args,
        proc=proc,
    )
    if proc.returncode != 0:
        return "", [diagnostic] if diagnostic else []
    return proc.stdout, []


def read_cached_stat(repo_root: Path) -> str:
    stat, _ = _read_cached_stat_with_diagnostics(repo_root)
    return stat


def _scope_contains_path(path: str, scopes: Iterable[str]) -> bool:
    token = str(path or "").strip("/")
    for scope in scopes:
        candidate = str(scope or "").strip("/")
        if candidate and (path_scope_overlaps(token, candidate) or path_scope_overlaps(candidate, token)):
            return True
    return False


def _registry_owners_for_path(path: str) -> list[dict[str, Any]]:
    owners: list[dict[str, Any]] = []
    for owner in generated_projection_registry.iter_projection_owners():
        if any(
            _scope_contains_path(path, (artifact,)) or fnmatch(path, artifact)
            for artifact in owner.artifacts
        ):
            owners.append(owner.to_dict())
    return owners


def _write_profiles_for_path(path: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for profile, profile_paths in sorted(WRITE_PROFILE_PATHS.items()):
        if _scope_contains_path(path, profile_paths):
            matches.append(
                {
                    "profile": profile,
                    "paths": list(profile_paths),
                }
            )
    return matches


def _is_task_ledger_projection(path: str) -> bool:
    return any(path_scope_overlaps(path, prefix) for prefix in TASK_LEDGER_PROJECTION_PREFIXES)


def _is_microcosm_public_fixture_source_index(path: str) -> bool:
    token = str(path or "").strip("/")
    return any(
        fnmatch(token, pattern)
        for pattern in MICROCOSM_PUBLIC_FIXTURE_SOURCE_INDEX_PATTERNS
    )


def _is_generated_like(path: str) -> bool:
    token = str(path or "").strip("/")
    if _is_runtime_run_artifact(token):
        return False
    if token.startswith("codex/standards/"):
        return False
    if token.startswith("microcosm-substrate/standards/"):
        return False
    if token in KNOWN_SOURCE_INDEXES:
        return False
    if _is_microcosm_public_fixture_source_index(token):
        return False
    if _is_task_ledger_projection(token):
        return True
    if any(path_scope_overlaps(token, prefix) for prefix in KNOWN_GENERATED_PREFIXES):
        return True
    if any(token.endswith(suffix) for suffix in KNOWN_GENERATED_SUFFIXES):
        return True
    if "/generated/" in token:
        return True
    return False


def _is_runtime_run_artifact(path: str) -> bool:
    token = str(path or "").strip("/")
    return any(token.startswith(prefix) for prefix in RUNTIME_RUN_PREFIXES)


def _is_station_render_latest_projection(path: str) -> bool:
    return str(path or "").strip("/") == STATION_RENDER_LOAD_INDEX


def _is_station_render_receipt_artifact(path: str) -> bool:
    token = str(path or "").strip("/")
    return any(token.startswith(prefix) for prefix in STATION_RENDER_RECEIPT_PREFIXES)


def _is_phase_pipeline_runtime_path(path: str) -> bool:
    token = str(path or "").strip("/")
    if not token.startswith("obsidian/okay lets do this/"):
        return False
    name = token.rsplit("/", 1)[-1]
    return (
        name in PHASE_PIPELINE_RUNTIME_FILENAMES
        or "/.pipeline_recovery/" in token
        or "/cycle_" in token
    )


def _is_microcosm_runtime_receipt_path(path: str) -> bool:
    return str(path or "").strip("/").startswith(MICROCOSM_RUNTIME_RECEIPT_PREFIX)


def _is_receipt_artifact_path(path: str) -> bool:
    return str(path or "").strip("/").startswith(RECEIPT_ARTIFACT_PREFIX)


def _is_runtime_artifact_lifecycle_path(path: str) -> bool:
    return (
        _is_runtime_run_artifact(path)
        or _is_station_render_latest_projection(path)
        or _is_station_render_receipt_artifact(path)
    )


def _declared_owned_paths(owned_paths: Sequence[str], write_profiles: Sequence[str]) -> list[str]:
    declared: list[str] = []
    for path in owned_paths:
        token = str(path or "").strip("/")
        if token and token not in declared:
            declared.append(token)
    for profile in write_profiles:
        for path in WRITE_PROFILE_PATHS.get(profile, ()):
            token = str(path or "").strip("/")
            if token and token not in declared:
                declared.append(token)
    return declared


def classify_path(
    path: str,
    *,
    owned_paths: Sequence[str] = (),
    write_profiles: Sequence[str] = (),
) -> dict[str, Any]:
    token = str(path or "").strip("/")
    registry_owners = _registry_owners_for_path(token)
    profile_matches = _write_profiles_for_path(token)
    owner_tool_entries = owner_tool_entries_for_path(token)
    declared_paths = _declared_owned_paths(owned_paths, write_profiles)
    owned = _scope_contains_path(token, declared_paths)

    if token == TASK_LEDGER_EVENTS:
        generation_class = "source_authority_append_log"
        source_authority = TASK_LEDGER_EVENTS
        stageability_class = "append_only_authority_requires_event_order_validation"
    elif _is_task_ledger_projection(token):
        generation_class = "read_projection"
        source_authority = TASK_LEDGER_EVENTS
        stageability_class = "stage_with_owned_task_ledger_event_or_ledger_consolidation_lane"
    elif _is_station_render_latest_projection(token):
        generation_class = "station_render_latest_projection"
        source_authority = "state/observability/renders/<run_stamp>/manifest.json"
        stageability_class = "do_not_stage_latest_projection_as_source"
    elif _is_station_render_receipt_artifact(token):
        generation_class = "station_render_receipt_artifact"
        source_authority = "station_render per-run manifest"
        stageability_class = "preserve_unless_explicitly_promoted"
    elif _is_phase_pipeline_runtime_path(token):
        generation_class = "phase_pipeline_runtime_state"
        source_authority = "pipeline_advance.py / system/lib/pipeline_recovery.py"
        stageability_class = "route_through_phase_pipeline_owner"
    elif _is_microcosm_runtime_receipt_path(token):
        generation_class = "microcosm_runtime_receipt_state"
        source_authority = "microcosm-substrate/src/microcosm_core/runtime_shell.py"
        stageability_class = "preserve_unless_claimed_or_promoted"
    elif _is_receipt_artifact_path(token):
        generation_class = "receipt_artifact_state"
        source_authority = "mission receipt artifact lane"
        stageability_class = "preserve_unless_claimed_or_promoted"
    elif registry_owners:
        generation_class = "registered_generated_projection"
        source_authority = "generated_projection_registry"
        stageability_class = "stage_only_with_owner_tool_or_owned_source_change"
    elif profile_matches:
        generation_class = "work_ledger_write_profile_surface"
        source_authority = "tools/meta/factory/work_ledger.py::WRITE_PROFILE_PATHS"
        stageability_class = "claim_profile_before_mutation"
    elif _is_reconstructable_build_output_path(token):
        generation_class = "reconstructable_build_output"
        source_authority = None
        stageability_class = "never_stage_reconstructable_build_cache_de_track_and_ignore"
    elif _is_runtime_run_artifact(token):
        generation_class = "runtime_run_artifact"
        source_authority = "state/runs runtime artifact lane"
        stageability_class = "preserve_unless_claimed_or_promoted"
    elif _is_generated_like(token):
        generation_class = "generated_like_unknown_owner"
        source_authority = None
        stageability_class = "coverage_gap_requires_owner_classification"
    else:
        generation_class = "source_or_unclassified"
        source_authority = None
        stageability_class = "normal_scoped_ownership_required"

    coverage_gap = generation_class == "generated_like_unknown_owner"
    return {
        "path": token,
        "ownership_class": "owned_declared" if owned else "unowned_or_undeclared",
        "generation_class": generation_class,
        "stageability_class": stageability_class,
        "source_authority": source_authority,
        "generated_projection_owners": registry_owners,
        "work_ledger_write_profiles": profile_matches,
        "owner_tool_entries": owner_tool_entries,
        "coverage_gap": coverage_gap,
    }


def _path_claim_collisions(
    paths: Sequence[str],
    overview: Mapping[str, Any],
    *,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    owner_session_id = str(session_id or "").strip()
    active_claims = [
        claim
        for claim in overview.get("active_claims") or []
        if isinstance(claim, Mapping) and claim.get("scope_kind") == "path"
    ]
    collisions: list[dict[str, Any]] = []
    for requested in paths:
        for claim in active_claims:
            if owner_session_id and str(claim.get("session_id") or "") == owner_session_id:
                continue
            claim_path = str(claim.get("path") or claim.get("scope_id") or "").strip("/")
            if not claim_path:
                continue
            if not (path_scope_overlaps(requested, claim_path) or path_scope_overlaps(claim_path, requested)):
                continue
            collisions.append(
                {
                    "requested_path": requested,
                    "claim_path": claim_path,
                    "session_id": claim.get("session_id"),
                    "actor": claim.get("actor"),
                    "claim_id": claim.get("claim_id"),
                    "leased_until": claim.get("leased_until"),
                }
            )
    return collisions


def _subject_or_td_claim_collisions(
    target_ids: Sequence[str],
    overview: Mapping[str, Any],
    *,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    owner_session_id = str(session_id or "").strip()
    targets = {str(item or "").strip() for item in target_ids if str(item or "").strip()}
    active_claims = [
        claim
        for claim in overview.get("active_claims") or []
        if isinstance(claim, Mapping) and claim.get("scope_kind") in {"td_id", "work_item_id"}
    ]
    collisions: list[dict[str, Any]] = []
    for claim in active_claims:
        if owner_session_id and str(claim.get("session_id") or "") == owner_session_id:
            continue
        claimed = _target_claim_scope_id(claim)
        if not claimed or claimed not in targets:
            continue
        collisions.append(
            {
                "target_id": claimed,
                "scope_kind": claim.get("scope_kind"),
                "session_id": claim.get("session_id"),
                "actor": claim.get("actor"),
                "claim_id": claim.get("claim_id"),
                "leased_until": claim.get("leased_until"),
            }
        )
    return collisions


def _other_active_claim_count(overview: Mapping[str, Any], *, session_id: str | None = None) -> int:
    owner_session_id = str(session_id or "").strip()
    claims = [claim for claim in overview.get("active_claims") or [] if isinstance(claim, Mapping)]
    if not owner_session_id:
        return len(claims)
    return sum(1 for claim in claims if str(claim.get("session_id") or "") != owner_session_id)


def _claim_summary(claim: Mapping[str, Any]) -> dict[str, Any]:
    scope_kind = str(claim.get("scope_kind") or "").strip()
    return {
        "claim_id": claim.get("claim_id"),
        "session_id": claim.get("session_id"),
        "actor": claim.get("actor"),
        "scope_kind": scope_kind,
        "scope_id": claim.get("scope_id"),
        "path": claim.get("path"),
        "td_id": claim.get("td_id"),
        "work_item_id": claim.get("work_item_id"),
        "leased_until": claim.get("leased_until"),
    }


def _matching_request_claims(
    overview: Mapping[str, Any],
    requested_paths: Sequence[str],
    target_ids: Sequence[str],
    *,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    owner_session_id = str(session_id or "").strip()
    targets = {str(item or "").strip() for item in target_ids if str(item or "").strip()}
    matches: list[dict[str, Any]] = []
    for claim in overview.get("active_claims") or []:
        if not isinstance(claim, Mapping):
            continue
        if owner_session_id and str(claim.get("session_id") or "") != owner_session_id:
            continue
        scope_kind = str(claim.get("scope_kind") or "").strip()
        if scope_kind in {"td_id", "work_item_id"}:
            claimed = _target_claim_scope_id(claim)
            if claimed and claimed in targets:
                matches.append(dict(claim))
        elif scope_kind == "path":
            claimed = str(claim.get("path") or claim.get("scope_id") or "").strip("/")
            if claimed and any(
                path_scope_overlaps(requested, claimed) or path_scope_overlaps(claimed, requested)
                for requested in requested_paths
            ):
                matches.append(dict(claim))
    return matches


def _sessionless_claim_identity_hint(
    collisions: Sequence[Mapping[str, Any]],
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    if str(session_id or "").strip():
        return {"status": "session_id_supplied"}
    collision_sessions = sorted(
        {
            str(collision.get("session_id") or "").strip()
            for collision in collisions
            if str(collision.get("session_id") or "").strip()
        }
    )
    if not collision_sessions:
        return {
            "status": "no_candidate_session",
            "reason": "no session id was supplied and colliding claims do not expose a session id",
        }
    if len(collision_sessions) == 1:
        candidate = collision_sessions[0]
        return {
            "status": "candidate_session_id_available",
            "candidate_session_ids": collision_sessions,
            "recommended_arg": f"--session-id {candidate}",
            "recommended_args": ["--session-id", candidate],
            "reason": (
                "no session id was supplied and all relevant claim collisions share one "
                "active session; rerun the same preflight with this session id if these "
                "are the current agent's claims"
            ),
        }
    return {
        "status": "multiple_candidate_sessions",
        "candidate_session_ids": collision_sessions,
        "reason": (
            "no session id was supplied and relevant claim collisions span multiple "
            "active sessions; choose the owning session or release conflicting claims"
        ),
    }


def _auto_session_id_resolution(
    *,
    requested_session_id: str,
    path_collisions: Sequence[Mapping[str, Any]],
    target_collisions: Sequence[Mapping[str, Any]],
) -> tuple[str, dict[str, Any]]:
    requested = str(requested_session_id or "").strip()
    if requested.lower() != "auto":
        if requested:
            return requested, {"status": "explicit_session_id", "session_id": requested}
        return "", {"status": "missing_session_id"}

    collisions = [*path_collisions, *target_collisions]
    hint = _sessionless_claim_identity_hint(collisions, session_id=None)
    candidates = [
        str(item or "").strip()
        for item in hint.get("candidate_session_ids") or []
        if str(item or "").strip()
    ]
    if len(candidates) == 1:
        candidate = candidates[0]
        return candidate, {
            "status": "auto_bound_unique_relevant_claim_session",
            "session_id": candidate,
            "source": "unique_relevant_active_claim_session",
            "path_collision_count_before_bind": len(path_collisions),
            "subject_or_td_collision_count_before_bind": len(target_collisions),
        }
    return "", {
        "status": "auto_bind_failed",
        "reason": hint.get("reason") or "unique relevant active claim session not available",
        "candidate_session_ids": candidates,
        "path_collision_count_before_bind": len(path_collisions),
        "subject_or_td_collision_count_before_bind": len(target_collisions),
    }


def _work_ledger_packet(
    repo_root: Path,
    requested_paths: Sequence[str],
    *,
    target_ids: Sequence[str] = (),
    session_id: str | None = None,
    require_exclusive: bool,
) -> dict[str, Any]:
    runtime_status = work_ledger_runtime.load_runtime_status(repo_root)
    overview = work_ledger_runtime.build_session_cohort_overview(runtime_status)
    claim_overview = dict(overview)
    full_active_claims = _runtime_active_claim_rows(runtime_status)
    if full_active_claims:
        claim_overview["active_claims"] = full_active_claims
    counts = overview.get("counts") if isinstance(overview.get("counts"), Mapping) else {}
    requested_session_id = str(session_id or "").strip()
    initial_path_collisions = _path_claim_collisions(requested_paths, claim_overview, session_id=None)
    initial_target_collisions = _subject_or_td_claim_collisions(target_ids, claim_overview, session_id=None)
    session_key, session_id_resolution = _auto_session_id_resolution(
        requested_session_id=requested_session_id,
        path_collisions=initial_path_collisions,
        target_collisions=initial_target_collisions,
    )
    sessions = runtime_status.get("sessions") if isinstance(runtime_status.get("sessions"), Mapping) else {}
    session_row = sessions.get(session_key) if session_key else None
    session_payload = {
        "session_id": session_key or None,
        "phase_id": session_row.get("phase_id") if isinstance(session_row, Mapping) else None,
        "family_id": session_row.get("family_id") if isinstance(session_row, Mapping) else None,
        "read_receipt_id": session_row.get("read_receipt_id") if isinstance(session_row, Mapping) else None,
        "ended_at": session_row.get("ended_at") if isinstance(session_row, Mapping) else None,
        "session_had_ledger_append": bool(session_row.get("session_had_ledger_append"))
        if isinstance(session_row, Mapping)
        else None,
        "stale": bool(session_row.get("stale")) if isinstance(session_row, Mapping) else None,
        "stale_reason": session_row.get("stale_reason") if isinstance(session_row, Mapping) else None,
    }
    path_collisions = _path_claim_collisions(requested_paths, claim_overview, session_id=session_key)
    target_collisions = _subject_or_td_claim_collisions(target_ids, claim_overview, session_id=session_key)
    collisions = [*path_collisions, *target_collisions]
    sessionless_claim_identity_hint = _sessionless_claim_identity_hint(
        collisions,
        session_id=session_key,
    )
    matching_claims = _matching_request_claims(
        claim_overview,
        requested_paths,
        target_ids,
        session_id=session_key,
    )
    status = "blocked" if collisions and require_exclusive else ("watch" if collisions else "clear")
    return {
        "status": status,
        "require_exclusive": bool(require_exclusive),
        "session_id": session_key or None,
        "requested_session_id": requested_session_id or None,
        "session_id_resolution": session_id_resolution,
        "session": session_payload,
        "counts": {
            "active_sessions": counts.get("active_sessions", 0),
            "effective_active_sessions": counts.get("effective_active_sessions", 0),
            "orphaned_active_sessions": counts.get("orphaned_active_sessions", 0),
            "active_claims": counts.get("active_claims", 0),
            "other_active_claims": _other_active_claim_count(claim_overview, session_id=session_id),
            "claim_collisions": counts.get("claim_collisions", 0),
            "stale_sessions": counts.get("stale_sessions", 0),
        },
        "requested_paths": list(requested_paths),
        "subject_or_td_targets": list(target_ids),
        "collision_count": len(collisions),
        "collisions": collisions,
        "sessionless_claim_identity_hint": sessionless_claim_identity_hint,
        "matching_active_claim_count": len(matching_claims),
        "matching_active_claims": matching_claims,
        "active_claims": [
            _claim_summary(claim)
            for claim in claim_overview.get("active_claims") or []
            if isinstance(claim, Mapping)
        ],
        "path_collision_count": len(path_collisions),
        "path_collisions": path_collisions,
        "subject_or_td_collision_count": len(target_collisions),
        "subject_or_td_collisions": target_collisions,
        "contention": overview.get("contention", {}),
    }


def _parse_claim_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _runtime_active_claim_rows(runtime_status: Mapping[str, Any]) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    sessions = runtime_status.get("sessions") if isinstance(runtime_status.get("sessions"), Mapping) else {}
    rows: list[dict[str, Any]] = []
    for session_id, session in sessions.items():
        if not isinstance(session, Mapping) or session.get("ended_at"):
            continue
        for claim in session.get("claims") or []:
            if not isinstance(claim, Mapping):
                continue
            if claim.get("released_at") or claim.get("expired_at"):
                continue
            leased_until = _parse_claim_datetime(claim.get("leased_until"))
            if leased_until is not None and leased_until < now:
                continue
            row = dict(claim)
            row["session_id"] = str(session_id)
            row["actor"] = session.get("actor")
            row["phase_id"] = session.get("phase_id")
            rows.append(row)
    rows.sort(key=lambda claim: str(claim.get("leased_until") or ""), reverse=True)
    return rows


def _scoped_commit_capability(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "tools/meta/control/scoped_commit.py"
    git_metadata_write = _git_metadata_write_capability(repo_root)
    metadata_writable = bool(git_metadata_write.get("writable"))
    surface_exists = path.exists()
    usable = bool(surface_exists and metadata_writable)
    return {
        "available": usable,
        "surface_exists": surface_exists,
        "surface": "tools/meta/control/scoped_commit.py",
        "private_index": usable,
        "head_cas": usable,
        "git_metadata_write": git_metadata_write,
        "modes": ["full-paths", "patch"] if surface_exists else [],
        "notes": [
            "Uses GIT_INDEX_FILE and git commit-tree/update-ref HEAD CAS when available.",
            "full-paths mode refreshes the shared index for committed paths; "
            "patch mode refreshes committed paths only when they had no "
            "pre-existing shared-index entry.",
        ] if surface_exists else [],
    }


def _git_metadata_write_capability(repo_root: Path) -> dict[str, Any]:
    git_dir = _resolved_git_dir(repo_root)
    if git_dir is None:
        return {
            "schema": "git_metadata_write_capability_v0",
            "status": "unknown",
            "writable": False,
            "reason": "git_dir_unresolved",
            "failure_class": "git_dir_unresolved",
            "authority_boundary": "git_metadata_history_authority",
            "probe_context": "current_process_execution_context",
            "same_context_required": True,
            "owner_repair_commands": [
                "git rev-parse --git-dir",
                "inspect repository checkout before retrying the commit lane",
            ],
            "probes": [],
        }
    git_common_dir = _resolved_git_common_dir(repo_root, git_dir)
    git_objects_dir = git_common_dir / "objects"
    worktree_probe = _git_metadata_write_probe(repo_root, purpose="repo_worktree_control")
    probes = [
        _git_metadata_write_probe(git_dir, purpose="git_dir_index_lock_parent"),
        _git_metadata_write_probe(git_objects_dir, purpose="git_object_database"),
    ]
    blocked = [row for row in probes if row.get("status") != "ok"]
    lockfiles = _git_metadata_lockfiles(repo_root, git_dir)
    failure_class = _classify_git_metadata_write_failure(
        repo_root=repo_root,
        git_dir=git_dir,
        probes=probes,
        worktree_probe=worktree_probe,
        lockfiles=lockfiles,
    )
    return {
        "schema": "git_metadata_write_capability_v0",
        "status": "blocked" if blocked else "ok",
        "writable": not blocked,
        "reason": "metadata_write_probe_failed" if blocked else "metadata_write_probe_passed",
        "failure_class": failure_class,
        "authority_boundary": "git_metadata_history_authority",
        "probe_context": "current_process_execution_context",
        "same_context_required": True,
        "worktree_write_probe": worktree_probe,
        "git_dir": _normalize_path(repo_root, str(git_dir)),
        "git_common_dir": _normalize_path(repo_root, str(git_common_dir)),
        "git_objects_dir": _normalize_path(repo_root, str(git_objects_dir)),
        "protected_metadata_path": _is_protected_git_metadata_path(repo_root, git_dir),
        "git_dir_permissions": _directory_permission_summary(git_dir),
        "git_common_dir_permissions": _directory_permission_summary(git_common_dir),
        "git_objects_permissions": _directory_permission_summary(git_objects_dir),
        "lockfiles": lockfiles,
        "git_gc_maintenance": _git_gc_maintenance_advisory(repo_root, git_dir),
        "owner_repair_commands": _git_metadata_owner_repair_commands(failure_class),
        "probes": probes,
    }


def _resolved_git_dir(repo_root: Path) -> Path | None:
    proc = _run_git(repo_root, ["rev-parse", "--git-dir"])
    if proc.returncode != 0:
        return None
    raw = proc.stdout.strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root / path
    return path


def _resolved_git_common_dir(repo_root: Path, git_dir: Path) -> Path:
    proc = _run_git(repo_root, ["rev-parse", "--git-common-dir"])
    raw = proc.stdout.strip() if proc.returncode == 0 else ""
    if not raw:
        return git_dir
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root / path
    return path


def _git_metadata_lockfiles(repo_root: Path, git_dir: Path) -> list[str]:
    candidates = [
        git_dir / "index.lock",
        git_dir / "HEAD.lock",
        git_dir / "packed-refs.lock",
    ]
    refs_dir = git_dir / "refs"
    if refs_dir.is_dir():
        try:
            candidates.extend(sorted(refs_dir.rglob("*.lock"))[:20])
        except OSError:
            pass
    return [
        _normalize_path(repo_root, str(path))
        for path in candidates
        if path.exists()
    ]


def _git_gc_maintenance_advisory(repo_root: Path, git_dir: Path) -> dict[str, Any]:
    gc_log = git_dir / "gc.log"
    preview = None
    if gc_log.exists():
        try:
            preview = gc_log.read_text(encoding="utf-8", errors="replace")[:500]
        except OSError:
            preview = None
    exists = gc_log.exists()
    return {
        "schema": "git_gc_maintenance_advisory_v0",
        "status": "attention" if exists else "ok",
        "gc_log_exists": exists,
        "gc_log_path": _normalize_path(repo_root, str(gc_log)),
        "gc_log_preview": preview,
        "check_command": "./repo-python tools/meta/control/git_gc_maintenance.py --check",
        "repair_command": "./repo-python tools/meta/control/git_gc_maintenance.py --repair",
        "owner": "tools/meta/control/git_gc_maintenance.py",
    }


def _is_protected_git_metadata_path(repo_root: Path, git_dir: Path) -> bool:
    normalized = _normalize_path(repo_root, str(git_dir)).replace("\\", "/")
    if (
        normalized == ".git"
        or normalized.startswith(".git/")
        or normalized.endswith("/.git")
        or "/.git/" in normalized
    ):
        return True
    pointer_target = _git_pointer_file_target(repo_root)
    if pointer_target is None:
        return git_dir.name.endswith(".git")
    try:
        return pointer_target.resolve() == git_dir.resolve()
    except OSError:
        return pointer_target.absolute() == git_dir.absolute()


def _git_pointer_file_target(repo_root: Path) -> Path | None:
    pointer = repo_root / ".git"
    if not pointer.is_file():
        return None
    try:
        first_line = pointer.read_text(encoding="utf-8").splitlines()[0]
    except (IndexError, OSError, UnicodeDecodeError):
        return None
    prefix = "gitdir:"
    if not first_line.lower().startswith(prefix):
        return None
    raw = first_line[len(prefix):].strip()
    if not raw:
        return None
    target = Path(raw)
    if not target.is_absolute():
        target = pointer.parent / target
    return target


def _directory_permission_summary(directory: Path) -> dict[str, Any]:
    try:
        stat_result = directory.stat()
    except OSError as exc:
        return {
            "path": str(directory),
            "exists": False,
            "is_dir": False,
            "error_class": exc.__class__.__name__,
            "error": str(exc),
        }
    return {
        "path": str(directory),
        "exists": True,
        "is_dir": directory.is_dir(),
        "mode_octal": oct(stat_result.st_mode & 0o777),
        "uid": stat_result.st_uid,
        "gid": stat_result.st_gid,
        "os_access_w": os.access(directory, os.W_OK),
    }


def _probe_error_text(probe: Mapping[str, Any]) -> str:
    return " ".join(
        str(probe.get(key) or "")
        for key in ("error_class", "errno", "strerror", "error", "reason")
    )


def _probe_is_permission_denial(probe: Mapping[str, Any]) -> bool:
    text = _probe_error_text(probe).lower()
    return (
        str(probe.get("error_class") or "") == "PermissionError"
        or "operation not permitted" in text
        or "permission denied" in text
        or probe.get("errno") in {errno.EPERM, errno.EACCES}
    )


def _classify_git_metadata_write_failure(
    *,
    repo_root: Path,
    git_dir: Path,
    probes: Sequence[Mapping[str, Any]],
    worktree_probe: Mapping[str, Any],
    lockfiles: Sequence[str],
) -> str:
    blocked = [row for row in probes if row.get("status") != "ok"]
    if not blocked:
        return GIT_METADATA_WRITE_OK
    if any(str(row.get("reason") or "") == "probe_directory_missing" for row in blocked):
        return GIT_METADATA_UNIX_PERMISSION_DENIED
    if any(_probe_is_permission_denial(row) for row in blocked):
        errno_values = {row.get("errno") for row in blocked}
        protected_path = _is_protected_git_metadata_path(repo_root, git_dir)
        operation_not_permitted = any(
            "operation not permitted" in _probe_error_text(row).lower()
            for row in blocked
        )
        if worktree_probe.get("status") == "ok" and protected_path and (
            errno.EPERM in errno_values or operation_not_permitted
        ):
            return GIT_METADATA_PROTECTED_SANDBOX
        return GIT_METADATA_UNIX_PERMISSION_DENIED
    if lockfiles:
        return GIT_METADATA_STALE_LOCK_OR_CONTENTION
    return GIT_METADATA_UNIX_PERMISSION_DENIED


def _git_metadata_owner_repair_commands(failure_class: str) -> list[str]:
    if failure_class == GIT_METADATA_WRITE_OK:
        return []
    if failure_class == GIT_METADATA_PROTECTED_SANDBOX:
        return [
            "for exact full-path scopes with stable --expected-parent, rerun scoped_commit.py full-paths with --remote-fallback-on-metadata-block; otherwise rerun with explicit Git metadata authority, full-access, or operator local Git",
            "enable a verified limited Git writes policy only if the installed Codex surface supports it",
            "do not use chmod/chown as the first repair when worktree writes pass and same-context .git writes fail with EPERM",
        ]
    if failure_class == GIT_METADATA_STALE_LOCK_OR_CONTENTION:
        return [
            "./repo-python tools/meta/control/git_gc_maintenance.py --check",
            "find .git -maxdepth 2 \\( -name '*.lock' -o -name 'gc.log' \\) -print",
            "verify no Git process owns the lock before removing stale lock files",
        ]
    return [
        "ls -ldeO@ .git .git/objects",
        "restore repository metadata ownership and mode only when same-context probes show ordinary Unix permission denial",
    ]


def _git_metadata_write_probe(directory: Path, *, purpose: str) -> dict[str, Any]:
    if not directory.is_dir():
        return {
            "purpose": purpose,
            "path": str(directory),
            "status": "blocked",
            "reason": "probe_directory_missing",
        }
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".aiw-preflight-write-probe-",
            dir=directory,
            delete=True,
        ) as handle:
            handle.write(b"")
            handle.flush()
    except OSError as exc:
        return {
            "purpose": purpose,
            "path": str(directory),
            "status": "blocked",
            "reason": "metadata_write_denied",
            "error_class": exc.__class__.__name__,
            "errno": exc.errno,
            "strerror": exc.strerror,
            "error": str(exc),
        }
    return {
        "purpose": purpose,
        "path": str(directory),
        "status": "ok",
        "reason": "metadata_write_probe_passed",
    }


def _scoped_commit_usable(scoped_commit: Mapping[str, Any]) -> bool:
    return bool(
        scoped_commit.get("available")
        and scoped_commit.get("private_index")
        and scoped_commit.get("head_cas")
        and _git_metadata_writable(scoped_commit)
    )


def _git_metadata_write_payload(scoped_commit: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = scoped_commit.get("git_metadata_write")
    if isinstance(payload, Mapping):
        return payload
    return {}


def _git_metadata_writable(scoped_commit: Mapping[str, Any]) -> bool:
    payload = _git_metadata_write_payload(scoped_commit)
    if not payload:
        return True
    return bool(payload.get("writable"))


def _git_metadata_unavailable_landing_decision(scoped_commit: Mapping[str, Any]) -> dict[str, Any]:
    git_metadata_write = _git_metadata_write_payload(scoped_commit)
    failure_class = str(git_metadata_write.get("failure_class") or "git_metadata_write_unavailable")
    if failure_class == GIT_METADATA_WRITE_OK:
        failure_class = "git_metadata_write_unavailable"
    recommended_lane = {
        GIT_METADATA_PROTECTED_SANDBOX: "remote_full_paths_fallback_or_authorized_git_metadata",
        GIT_METADATA_UNIX_PERMISSION_DENIED: "repair_repo_metadata_permissions",
        GIT_METADATA_STALE_LOCK_OR_CONTENTION: "clear_git_lock_or_wait_for_git_process",
    }.get(failure_class, "inspect_git_metadata_write_capability")
    decision = {
        "status": "blocked",
        "reason": failure_class,
        "legacy_reason": "git_metadata_write_unavailable",
        "recommended_lane": recommended_lane,
        "private_index_scoped_commit_allowed": False,
        "git_metadata_write": git_metadata_write,
        "owner_repair_commands": git_metadata_write.get("owner_repair_commands") or [],
    }
    if failure_class == GIT_METADATA_PROTECTED_SANDBOX:
        decision.update(
            {
                "authorized_git_lane": "rerun_commit_with_git_metadata_authority",
                "remote_fallback_lane": "scoped_commit_remote_full_paths_fallback",
                "remote_fallback_flag": "--remote-fallback-on-metadata-block",
                "remote_fallback_requires": [
                    "full-paths mode",
                    "exact owned path set",
                    "stable --expected-parent",
                    "remote target CAS still matches the intended base",
                    "remote push authority",
                ],
                "remote_fallback_warning": (
                    "The remote fallback publishes the target ref from a temporary "
                    "checkout and leaves the live repo HEAD unchanged; use the "
                    "authorized local Git lane when the remote base does not match "
                    "the intended parent."
                ),
            }
        )
    return decision


def _blocked_primary_primary_target(
    *,
    declared_paths: Sequence[str],
    staged_paths: Sequence[str],
    work_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    requested_paths = work_ledger.get("requested_paths")
    if not isinstance(requested_paths, (list, tuple)):
        requested_paths = ()
    collision_paths = [
        str(row.get("path") or row.get("scope_id") or "").strip("/")
        for row in work_ledger.get("path_collisions")
        or work_ledger.get("collisions")
        or []
        if isinstance(row, Mapping)
    ]
    source_paths = (
        list(declared_paths)
        or collision_paths
        or list(requested_paths)
        or list(staged_paths)
    )
    paths = sorted({str(path) for path in source_paths if str(path or "").strip()})
    targets = work_ledger.get("subject_or_td_targets")
    if not isinstance(targets, (list, tuple)):
        targets = ()
    target_ids = [str(target) for target in targets if str(target or "").strip()]
    return {
        "paths": paths,
        "path_count": len(paths),
        "target_ids": target_ids,
        "target_count": len(target_ids),
    }


def _work_ledger_claim_collision_evidence(work_ledger: Mapping[str, Any]) -> dict[str, Any]:
    hint = work_ledger.get("sessionless_claim_identity_hint")
    session_id_resolution = work_ledger.get("session_id_resolution")
    return {
        "source": "mission_transaction_landing_preflight.work_ledger",
        "reason": "work_ledger_claim_collision",
        "status": work_ledger.get("status"),
        "require_exclusive": bool(work_ledger.get("require_exclusive")),
        "collision_count": _int_value(work_ledger.get("collision_count")),
        "path_collision_count": _int_value(work_ledger.get("path_collision_count")),
        "subject_or_td_collision_count": _int_value(
            work_ledger.get("subject_or_td_collision_count")
        ),
        "collisions_preview": [
            dict(row)
            for row in work_ledger.get("collisions") or []
            if isinstance(row, Mapping)
        ][:COMPACT_PREVIEW_LIMIT],
        "sessionless_claim_identity_hint": dict(hint) if isinstance(hint, Mapping) else {},
        "session_id_resolution": dict(session_id_resolution)
        if isinstance(session_id_resolution, Mapping)
        else {},
    }


def _staged_only_claim_pressure(
    *,
    work_ledger: Mapping[str, Any],
    declared_paths: Sequence[str],
    staged_paths: Sequence[str],
) -> dict[str, Any]:
    path_collisions = [
        row for row in work_ledger.get("path_collisions") or [] if isinstance(row, Mapping)
    ]
    if not path_collisions or _int_value(work_ledger.get("subject_or_td_collision_count")):
        return {}

    declared = {str(path).strip("/") for path in declared_paths if str(path).strip()}
    staged = {str(path).strip("/") for path in staged_paths if str(path).strip()}
    if not staged:
        return {}

    for row in path_collisions:
        requested = str(
            row.get("requested_path")
            or row.get("path")
            or row.get("claim_path")
            or row.get("scope_id")
            or ""
        ).strip("/")
        if not requested or requested in declared or requested not in staged:
            return {}

    return {
        "schema": "staged_index_claim_pressure_v0",
        "status": "staged_only",
        "collision_count": len(path_collisions),
        "policy": "normal_commit_blocked_private_index_scoped_commit_may_proceed",
        "normal_commit_still_blocked": True,
        "collisions_preview": [dict(row) for row in path_collisions[:COMPACT_PREVIEW_LIMIT]],
    }


def _sessionless_binding_hint(work_ledger: Mapping[str, Any]) -> dict[str, Any] | None:
    if str(work_ledger.get("session_id") or "").strip():
        return None
    if not _int_value(work_ledger.get("collision_count")):
        return None
    hint = work_ledger.get("sessionless_claim_identity_hint")
    if not isinstance(hint, Mapping):
        return None
    if hint.get("status") != "candidate_session_id_available":
        return None
    return dict(hint)


def _blocked_primary_receipt_requirement(
    *,
    primary_target: Mapping[str, Any],
    blocker_classification: str,
    claim_or_collision_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": BLOCKED_PRIMARY_RECEIPT_REQUIREMENT_SCHEMA,
        "status": "required",
        "failure_kind": "blocked_primary_receipt_missing",
        "standard_ref": BLOCKED_PRIMARY_STANDARD_REF,
        "required_by": "mission_transaction_landing_decision",
        "primary_target": dict(primary_target),
        "blocker_classification": blocker_classification,
        "claim_or_collision_evidence": dict(claim_or_collision_evidence),
        "required_receipt_fields": list(BLOCKED_PRIMARY_REQUIRED_RECEIPT_FIELDS),
        "valid_selected_legal_continuations": list(BLOCKED_PRIMARY_LEGAL_CONTINUATIONS),
        "valid_blocker_classifications": list(BLOCKED_PRIMARY_BLOCKER_CLASSIFICATIONS),
        "receipt_policy": (
            "A blocked-primary closeout must either carry these fields or leave a "
            "durable residual/re-entry receipt before landing lower-yield adjacent work."
        ),
    }


def _blocked_primary_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (dict, list, tuple, set)):
        return not bool(value)
    return False


def validate_blocked_primary_continuation_receipt(
    receipt: Mapping[str, Any] | None,
    requirement: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate the legal-continuation receipt required after primary-path blocks."""
    requirement = requirement if isinstance(requirement, Mapping) else {}
    payload = receipt if isinstance(receipt, Mapping) else {}
    required = requirement.get("required_receipt_fields")
    if not isinstance(required, (list, tuple)):
        required = BLOCKED_PRIMARY_REQUIRED_RECEIPT_FIELDS
    required_fields = [str(field) for field in required]
    legal = requirement.get("valid_selected_legal_continuations")
    if not isinstance(legal, (list, tuple)):
        legal = BLOCKED_PRIMARY_LEGAL_CONTINUATIONS
    legal_values = [str(value) for value in legal]
    classifications = requirement.get("valid_blocker_classifications")
    if not isinstance(classifications, (list, tuple)):
        classifications = BLOCKED_PRIMARY_BLOCKER_CLASSIFICATIONS
    valid_classifications = [str(value) for value in classifications]

    missing = [
        field
        for field in required_fields
        if _blocked_primary_missing_value(payload.get(field))
    ]
    invalid: list[dict[str, Any]] = []
    selected = str(payload.get("selected_legal_continuation") or "").strip()
    if selected and selected not in legal_values:
        invalid.append({
            "field": "selected_legal_continuation",
            "value": selected,
            "allowed": legal_values,
        })
    blocker = str(payload.get("blocker_classification") or "").strip()
    if blocker and blocker not in valid_classifications:
        invalid.append({
            "field": "blocker_classification",
            "value": blocker,
            "allowed": valid_classifications,
        })
    complete = not missing and not invalid
    return {
        "schema": BLOCKED_PRIMARY_RECEIPT_VALIDATION_SCHEMA,
        "status": "complete" if complete else "blocked_primary_receipt_missing",
        "receipt_complete": complete,
        "failure_kind": None if complete else "blocked_primary_receipt_missing",
        "missing_fields": missing,
        "invalid_fields": invalid,
        "required_receipt_fields": required_fields,
        "valid_selected_legal_continuations": legal_values,
        "standard_ref": str(requirement.get("standard_ref") or BLOCKED_PRIMARY_STANDARD_REF),
    }


def _blocked_primary_receipt_metadata(
    receipt: Mapping[str, Any] | None,
    requirement: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = receipt if isinstance(receipt, Mapping) else {}
    requirement = requirement if isinstance(requirement, Mapping) else {}
    fields = requirement.get("required_receipt_fields")
    if not isinstance(fields, (list, tuple)):
        fields = BLOCKED_PRIMARY_REQUIRED_RECEIPT_FIELDS
    allowed = [
        *(str(field) for field in fields),
        "standard_ref",
        "receipt_id",
        "residual_id",
        "evidence_refs",
        "created_at",
        "source",
    ]
    return {
        field: payload.get(field)
        for field in allowed
        if field in payload and not _blocked_primary_missing_value(payload.get(field))
    }


def _blocked_primary_continuation_receipt_payload(
    *,
    packet: Mapping[str, Any],
    seed_payload: Mapping[str, Any],
    proof_loop_report: Mapping[str, Any],
    explicit_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    landing = _mapping_value(packet.get("landing_decision"))
    requirement = _mapping_value(landing.get("blocked_primary_receipt_requirement"))
    if str(requirement.get("status") or "") != "required":
        return {
            "schema": "blocked_primary_continuation_receipt_consumer_v0",
            "status": "not_required",
            "required": False,
            "standard_ref": BLOCKED_PRIMARY_STANDARD_REF,
        }
    receipt = (
        explicit_receipt
        if isinstance(explicit_receipt, Mapping)
        else seed_payload.get("blocked_primary_continuation_receipt")
    )
    if not isinstance(receipt, Mapping):
        receipt = proof_loop_report.get("blocked_primary_continuation_receipt")
    if not isinstance(receipt, Mapping):
        receipt = packet.get("blocked_primary_continuation_receipt")
    receipt_payload = receipt if isinstance(receipt, Mapping) else {}
    validation = validate_blocked_primary_continuation_receipt(receipt_payload, requirement)
    complete = bool(validation.get("receipt_complete"))
    return {
        "schema": "blocked_primary_continuation_receipt_consumer_v0",
        "status": "complete" if complete else "blocked_primary_receipt_missing",
        "required": True,
        "requirement": dict(requirement),
        "receipt": _blocked_primary_receipt_metadata(receipt_payload, requirement),
        "validation": validation,
        "standard_ref": validation.get("standard_ref") or BLOCKED_PRIMARY_STANDARD_REF,
    }


def _shared_worktree_guard_packet(repo_root: Path, dirty_paths: Sequence[str]) -> dict[str, Any]:
    return {
        "surface": "system/lib/shared_worktree_guard.py",
        "dirty_path_count": len(dirty_paths),
        "risky_git_operations": [
            {
                "argv": ["git", *argv],
                "decision": shared_worktree_guard.assess_git_argv(argv, repo_root=repo_root, dirty_paths=dirty_paths),
            }
            for argv in RISKY_COMMANDS
        ],
        "index_mutating_commands_need_serialization": [
            "git " + " ".join(argv)
            for argv in INDEX_MUTATING_COMMANDS
        ],
    }


def _path_has_claim(path: str, claims: Sequence[Mapping[str, Any]], *, session_id: str | None = None) -> dict[str, Any] | None:
    owner_session_id = str(session_id or "").strip()
    for claim in claims:
        if str(claim.get("scope_kind") or "").strip() != "path":
            continue
        if owner_session_id and str(claim.get("session_id") or "") != owner_session_id:
            continue
        claim_path = str(claim.get("path") or claim.get("scope_id") or "").strip("/")
        if claim_path and (
            path_scope_overlaps(path, claim_path) or path_scope_overlaps(claim_path, path)
        ):
            return dict(claim)
    return None


def _dirty_category_for_path(
    path: str,
    *,
    status_row: GitStatusRow,
    classification: Mapping[str, Any],
    declared_paths: Sequence[str],
    work_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    session_id = str(work_ledger.get("session_id") or "").strip()
    active_claims = [
        claim
        for claim in work_ledger.get("active_claims") or []
        if isinstance(claim, Mapping)
    ]
    owned = _scope_contains_path(path, declared_paths)
    current_claim = _path_has_claim(path, active_claims, session_id=session_id)
    other_claim = _path_has_claim(path, active_claims, session_id=None)
    if current_claim and str(current_claim.get("session_id") or "") == session_id:
        other_claim = None

    generation_class = str(classification.get("generation_class") or "")
    if owned and classification.get("coverage_gap"):
        return {
            "class": "generated_authority_unknown",
            "severity": "hard_gate",
            "reason": "declared_write_set_path_has_generated_owner_coverage_gap",
            "owner_session_id": session_id or None,
            "claim_id": current_claim.get("claim_id") if current_claim else None,
        }
    if _is_reconstructable_build_output_path(path) or generation_class == "reconstructable_build_output":
        return {
            "class": "tracked_build_output",
            "severity": "hard_gate" if status_row.is_staged else "watch",
            "reason": (
                "staged_reconstructable_build_output_not_in_transaction_write_set"
                if status_row.is_staged
                else "reconstructable_build_output_dirty_outside_current_write_set"
            ),
            "owner_session_id": None,
            "claim_id": None,
            "build_output_root": _build_output_root_for_path(path),
            "build_output_kind": "swiftpm_build_output"
            if ".build" in _path_segments(path)
            else "derived_data_build_output",
        }
    if status_row.is_staged and not owned:
        return {
            "class": "unowned_dirty_hard",
            "severity": "hard_gate",
            "reason": "staged_path_not_in_transaction_write_set",
            "owner_session_id": None,
            "claim_id": None,
        }
    if owned:
        return {
            "class": "current_transaction_owned",
            "severity": "watch",
            "reason": "path_is_inside_declared_transaction_write_set",
            "owner_session_id": session_id or None,
            "claim_id": current_claim.get("claim_id") if current_claim else None,
        }
    if current_claim:
        return {
            "class": "current_session_claimed_extra",
            "severity": "watch",
            "reason": "path_has_active_claim_for_current_session_but_is_not_in_declared_write_set",
            "owner_session_id": current_claim.get("session_id"),
            "claim_id": current_claim.get("claim_id"),
        }
    if other_claim:
        return {
            "class": "other_active_session_owned",
            "severity": "watch",
            "reason": "path_overlaps_an_active_work_ledger_path_claim",
            "owner_session_id": other_claim.get("session_id"),
            "claim_id": other_claim.get("claim_id"),
        }
    if path == TASK_LEDGER_EVENTS or _is_task_ledger_projection(path):
        return {
            "class": "task_ledger_event_or_projection",
            "severity": "watch",
            "reason": "task_ledger_authority_or_projection_dirty_outside_current_write_set",
            "owner_session_id": None,
            "claim_id": None,
        }
    if path.startswith("annexes/") or "/annex" in path:
        return {
            "class": "annex_projection_or_digest",
            "severity": "advisory",
            "reason": "annex_generated_or_digest_surface_dirty_outside_current_write_set",
            "owner_session_id": None,
            "claim_id": None,
        }
    if path.startswith(WORK_LEDGER_PREFIXES) or generation_class == "work_ledger_write_profile_surface":
        return {
            "class": "work_ledger_event_or_projection",
            "severity": "watch",
            "reason": "work_ledger_runtime_or_projection_dirty_outside_current_write_set",
            "owner_session_id": None,
            "claim_id": None,
        }
    if generation_class == "station_render_latest_projection":
        return {
            "class": "station_render_latest_projection",
            "severity": "watch",
            "reason": "station_render_latest_index_is_generated_runtime_projection_not_source_evidence",
            "owner_session_id": None,
            "claim_id": None,
        }
    if generation_class == "station_render_receipt_artifact":
        return {
            "class": "station_render_receipt_artifact",
            "severity": "watch",
            "reason": "station_render_per_run_receipt_preserved_until_explicit_promotion",
            "owner_session_id": None,
            "claim_id": None,
        }
    if generation_class == "phase_pipeline_runtime_state":
        return {
            "class": "phase_pipeline_runtime_state",
            "severity": "watch",
            "reason": "phase_pipeline_runtime_state_dirty_outside_current_write_set",
            "owner_session_id": None,
            "claim_id": None,
        }
    if generation_class == "microcosm_runtime_receipt_state":
        return {
            "class": "microcosm_runtime_receipt_state",
            "severity": "watch",
            "reason": "microcosm_runtime_shell_receipt_dirty_outside_current_write_set",
            "owner_session_id": None,
            "claim_id": None,
        }
    if generation_class == "receipt_artifact_state":
        return {
            "class": "receipt_artifact_state",
            "severity": "watch",
            "reason": "mission_receipt_artifact_dirty_outside_current_write_set",
            "owner_session_id": None,
            "claim_id": None,
        }
    if generation_class == "registered_generated_projection":
        return {
            "class": "generated_projection_expected",
            "severity": "watch",
            "reason": "registered_generated_projection_dirty_outside_current_write_set",
            "owner_session_id": None,
            "claim_id": None,
        }
    if generation_class == "runtime_run_artifact":
        return {
            "class": "runtime_run_artifact",
            "severity": "watch",
            "reason": "state_runs_runtime_artifact_dirty_outside_current_write_set",
            "owner_session_id": None,
            "claim_id": None,
        }
    if classification.get("coverage_gap"):
        return {
            "class": "generated_projection_unknown_owner",
            "severity": "watch",
            "reason": "generated_like_path_needs_owner_classification_but_is_not_in_write_set",
            "owner_session_id": None,
            "claim_id": None,
        }
    if path.startswith("obsidian/") and any(marker in path for marker in PHASE_STATE_MARKERS):
        return {
            "class": "phase_state_current_wave",
            "severity": "watch",
            "reason": "phase_or_wave_state_dirty_outside_current_write_set",
            "owner_session_id": None,
            "claim_id": None,
        }
    if any(marker in path for marker in RAW_OR_OPERATOR_STATE_MARKERS):
        return {
            "class": "raw_seed_or_operator_state",
            "severity": "watch",
            "reason": "operator_voice_or_runtime_operator_state_dirty_outside_current_write_set",
            "owner_session_id": None,
            "claim_id": None,
        }
    if path.startswith("dist/"):
        return {
            "class": "distribution_packet",
            "severity": "advisory",
            "reason": "distribution_packet_dirty_outside_current_write_set",
            "owner_session_id": None,
            "claim_id": None,
        }
    return {
        "class": "ambient_dirty",
        "severity": "watch",
        "reason": "ordinary_unstaged_or_unowned_worktree_dirt_visible_but_not_a_hard_gate",
        "owner_session_id": None,
        "claim_id": None,
    }


def _dirty_tree_classification(
    *,
    status_rows: Sequence[GitStatusRow],
    declared_paths: Sequence[str],
    classifications: Sequence[Mapping[str, Any]],
    work_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    classification_by_path = {
        str(row.get("path") or ""): row
        for row in classifications
        if isinstance(row, Mapping)
    }
    rows: list[dict[str, Any]] = []
    by_class: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    hard_gate_paths: list[str] = []
    hard_unowned_paths: list[str] = []
    for status_row in status_rows:
        classification = classification_by_path.get(status_row.path, {})
        category = _dirty_category_for_path(
            status_row.path,
            status_row=status_row,
            classification=classification,
            declared_paths=declared_paths,
            work_ledger=work_ledger,
        )
        class_name = str(category.get("class") or "unknown")
        severity = str(category.get("severity") or "watch")
        by_class[class_name] = by_class.get(class_name, 0) + 1
        by_severity[severity] = by_severity.get(severity, 0) + 1
        if severity == "hard_gate":
            hard_gate_paths.append(status_row.path)
        if class_name == "unowned_dirty_hard":
            hard_unowned_paths.append(status_row.path)
        rows.append(
            {
                "path": status_row.path,
                "status": status_row.to_dict(),
                "class": class_name,
                "severity": severity,
                "reason": category.get("reason"),
                "build_output_root": category.get("build_output_root"),
                "build_output_kind": category.get("build_output_kind"),
                "generation_class": classification.get("generation_class"),
                "ownership_class": classification.get("ownership_class"),
                "owner_session_id": category.get("owner_session_id"),
                "claim_id": category.get("claim_id"),
            }
        )
    status = "clear"
    next_action = "no_dirty_paths"
    if hard_gate_paths:
        status = "blocked"
        next_action = "inspect_hard_gate_dirty_paths"
    elif rows:
        status = "watch"
        next_action = "continue_scoped_landing_if_owned_paths_and_staged_index_are_clean"
    return {
        "schema": DIRTY_TREE_CLASSIFICATION_SCHEMA,
        "dirty_path_count": len(rows),
        "classified_count": len(rows),
        "unclassified_count": by_class.get("unknown", 0),
        "hard_gate_count": len(hard_gate_paths),
        "hard_unowned_count": len(hard_unowned_paths),
        "by_class": dict(sorted(by_class.items())),
        "by_severity": dict(sorted(by_severity.items())),
        "hard_gate_paths_preview": hard_gate_paths[:COMPACT_PREVIEW_LIMIT],
        "hard_unowned_paths_preview": hard_unowned_paths[:COMPACT_PREVIEW_LIMIT],
        "status": status,
        "next_action": next_action,
        "rows": rows,
    }


def _dirty_tree_with_scoped_landing_policy(
    dirty_tree: Mapping[str, Any],
    *,
    staged_count: int,
    shared_index_quarantine: Mapping[str, Any],
) -> dict[str, Any]:
    result = dict(dirty_tree)
    if (
        str(result.get("status") or "") == "blocked"
        and _staged_quarantine_explains_dirty_hard_gates(
            staged_count=staged_count,
            dirty_tree=result,
            shared_index_quarantine=shared_index_quarantine,
        )
    ):
        result["raw_status"] = result.get("status")
        result["status"] = "watch"
        result["scope_gate_status"] = "pressure_only"
        result["hard_gate_policy"] = (
            "shared_index_quarantine_explains_hard_gates_and_private_index_scoped_commit_allowed"
        )
        result["next_action"] = "continue_scoped_landing_with_private_index"
        result["private_index_scoped_commit_allowed"] = True
        result["global_dirty_tree_blocks_scoped_work"] = False
    return result


def _probable_lane_for_path(path: str, classification: Mapping[str, Any]) -> str:
    token = str(path or "").strip("/")
    generation_class = str(classification.get("generation_class") or "")
    if token == TASK_LEDGER_EVENTS or _is_task_ledger_projection(token):
        return "task_ledger_projection_drainer"
    if token.startswith(WORK_LEDGER_PREFIXES) or generation_class == "work_ledger_write_profile_surface":
        return "work_ledger_projection_drainer"
    if token.startswith("annexes/") or "/annex" in token:
        return "annex_derived_artifact_policy"
    if token.startswith("dist/"):
        return "distribution_packet_builder"
    if generation_class == "registered_generated_projection":
        owners = classification.get("generated_projection_owners") or []
        if owners and isinstance(owners[0], Mapping):
            return str(owners[0].get("owner_id") or "generated_projection_owner")
        return "generated_projection_owner"
    if token.startswith("codex/doctrine/skills") or token.startswith("codex/standards"):
        return "doctrine_or_standard_lane"
    if any(marker in token for marker in RAW_OR_OPERATOR_STATE_MARKERS):
        return "raw_seed_or_operator_state_lane"
    return "unknown_shared_index_owner"


def _shared_index_quarantine(
    *,
    repo_root: Path,
    staged_paths: Sequence[str],
    status_rows: Sequence[GitStatusRow],
    declared_paths: Sequence[str],
    classifications: Sequence[Mapping[str, Any]],
    work_ledger: Mapping[str, Any],
    scoped_commit: Mapping[str, Any],
) -> dict[str, Any]:
    classification_by_path = {
        str(row.get("path") or ""): row
        for row in classifications
        if isinstance(row, Mapping)
    }
    status_by_path = {row.path: row for row in status_rows}
    active_claims = [
        claim
        for claim in work_ledger.get("active_claims") or []
        if isinstance(claim, Mapping)
    ]
    git_metadata_writable = _git_metadata_writable(scoped_commit)
    git_metadata_write = _git_metadata_write_payload(scoped_commit)
    declared = [str(path or "").strip("/") for path in declared_paths if str(path or "").strip()]
    rows: list[dict[str, Any]] = []
    unowned_count = 0
    owned_count = 0
    overlap_count = 0
    unowned_overlap_count = 0
    stale_reverse_paths: list[str] = []
    scan_truncated = len(staged_paths) > SHARED_INDEX_ENTRY_STATE_SCAN_LIMIT
    scanned_staged_paths = [
        str(path or "").strip("/")
        for path in staged_paths[:SHARED_INDEX_ENTRY_STATE_SCAN_LIMIT]
        if str(path or "").strip("/")
    ]
    scanned_entry_states = _shared_index_entry_states(repo_root, scanned_staged_paths)
    for index, path in enumerate(staged_paths):
        token = str(path or "").strip("/")
        classification = classification_by_path.get(token, {})
        status_row = status_by_path.get(token)
        if index < SHARED_INDEX_ENTRY_STATE_SCAN_LIMIT:
            entry_state = scanned_entry_states.get(token) or _shared_index_entry_state_from_blobs(
                token,
                head_blob=None,
                index_blob=None,
                worktree_blob=None,
            )
            if entry_state.get("status") == "stale_reverse_index_entry":
                stale_reverse_paths.append(token)
        else:
            entry_state = {
                "schema": SHARED_INDEX_ENTRY_STATE_SCHEMA,
                "path": token,
                "status": "not_scanned",
                "reason": "shared_index_entry_state_scan_limit_exceeded",
            }
        overlaps_current_write_set = _scope_contains_path(token, declared)
        owned = str(classification.get("ownership_class") or "") == "owned_declared"
        if owned:
            owned_count += 1
        else:
            unowned_count += 1
        if overlaps_current_write_set:
            overlap_count += 1
            if not owned:
                unowned_overlap_count += 1
        claim = _path_has_claim(token, active_claims, session_id=None)
        rows.append(
            {
                "path": token,
                "index_status": status_row.index_status if status_row else None,
                "worktree_status": status_row.worktree_status if status_row else None,
                "ownership_class": classification.get("ownership_class"),
                "generation_class": classification.get("generation_class"),
                "probable_lane": _probable_lane_for_path(token, classification),
                "owner_session_id": claim.get("session_id") if claim else None,
                "claim_id": claim.get("claim_id") if claim else None,
                "age": None,
                "age_reason": "git_index_entry_age_not_available_from_porcelain_status",
                "index_entry_state": entry_state,
                "overlaps_current_write_set": overlaps_current_write_set,
                "normal_git_commit_allowed": False,
                "private_index_scoped_commit_allowed": bool(
                    scoped_commit.get("private_index")
                    and scoped_commit.get("head_cas")
                    and git_metadata_writable
                    and (owned or not overlaps_current_write_set)
                ),
            }
        )

    normal_allowed = unowned_count == 0 and git_metadata_writable
    private_allowed = bool(
        scoped_commit.get("private_index")
        and scoped_commit.get("head_cas")
        and git_metadata_writable
        and unowned_overlap_count == 0
    )
    if not staged_paths:
        status = "clear"
        next_action = "none"
        recommended_action = (
            "staged_index_clean"
            if git_metadata_writable
            else "staged_index_clean_but_git_metadata_write_blocked"
        )
    elif unowned_overlap_count:
        status = "blocked"
        next_action = "resolve_or_claim_overlapping_staged_paths"
        recommended_action = "do_not_private-index_commit_until_unowned_staged_overlap_is_quarantined_or_owned"
    elif overlap_count:
        status = "review"
        next_action = "review_owned_staged_index_overlap"
        recommended_action = "normal_commit_allowed_only_after_index_hunk_review; private_index_remains_available_for_exact_owned_paths"
    elif unowned_count:
        status = "watch"
        next_action = (
            "review_stale_reverse_shared_index_entries"
            if stale_reverse_paths
            else "staged_index_quarantine_required"
        )
        recommended_action = (
            "normal_commit_blocked; stale_reverse_index_entries_detected_review_or_unstage_before_normal_commit; "
            "private_index_scoped_commit_allowed_for_exact_non_overlapping_owned_paths"
            if stale_reverse_paths
            else "normal_commit_blocked; private_index_scoped_commit_allowed_for_exact_non_overlapping_owned_paths"
        )
    else:
        status = "review"
        next_action = "review_owned_staged_index"
        recommended_action = "normal_commit_allowed_only_after_index_hunk_review; private_index_remains_available"

    return {
        "schema": SHARED_INDEX_QUARANTINE_SCHEMA,
        "status": status,
        "next_action": next_action,
        "staged_path_count": len(staged_paths),
        "unowned_staged_path_count": unowned_count,
        "owned_staged_path_count": owned_count,
        "overlap_count": overlap_count,
        "unowned_overlap_count": unowned_overlap_count,
        "stale_reverse_index_entry_count": len(stale_reverse_paths),
        "stale_reverse_paths_preview": stale_reverse_paths[:COMPACT_PREVIEW_LIMIT],
        "index_entry_state_scan_limit": SHARED_INDEX_ENTRY_STATE_SCAN_LIMIT,
        "index_entry_state_scan_truncated": scan_truncated,
        "normal_git_commit_allowed": bool(normal_allowed),
        "shared_index_normal_commit_blocked": bool(staged_paths and not normal_allowed),
        "private_index_scoped_commit_allowed": private_allowed,
        "private_index_scoped_commit_allowed_reason": (
            "private_index_and_head_cas_available_no_staged_overlap"
            if private_allowed
            else (
                "git_metadata_write_blocked"
                if not git_metadata_writable
                else "private_index_unavailable_or_unowned_staged_overlap"
            )
        ),
        "git_metadata_write_status": str(git_metadata_write.get("status") or "unknown"),
        "git_metadata_write_failure_class": str(git_metadata_write.get("failure_class") or ""),
        "recommended_action": recommended_action,
        "rows": rows,
        "paths_preview": [row["path"] for row in rows[:COMPACT_PREVIEW_LIMIT]],
        "policy": (
            "Unowned staged paths block normal shared-index commits. They do not block "
            "private-index scoped commits when the owned path set is exact and non-overlapping."
        ),
    }


def build_shared_index_quarantine_fast(
    repo_root: Path,
    *,
    owned_paths: Sequence[str] = (),
    write_profiles: Sequence[str] = (),
) -> dict[str, Any]:
    """Return the staged-index quarantine packet without building full preflight."""
    repo_root = repo_root.resolve()
    status_rows, git_command_diagnostics = _read_git_status_rows_with_diagnostics(repo_root)
    staged_paths, staged_path_diagnostics = _read_cached_path_names_with_diagnostics(repo_root)
    git_command_diagnostics.extend(staged_path_diagnostics)

    declared_paths = _declared_owned_paths(
        [_normalize_path(repo_root, path) for path in owned_paths],
        write_profiles,
    )
    classification_targets = sorted({*staged_paths, *declared_paths})
    classifications = [
        classify_path(path, owned_paths=owned_paths, write_profiles=write_profiles)
        for path in classification_targets
    ]
    payload = _shared_index_quarantine(
        repo_root=repo_root,
        staged_paths=staged_paths,
        status_rows=status_rows,
        declared_paths=declared_paths,
        classifications=classifications,
        work_ledger={"active_claims": []},
        scoped_commit=_scoped_commit_capability(repo_root),
    )
    payload["output_profile"] = "staged_index_quarantine_fast_path"
    payload["fast_path"] = True
    payload["git_command_diagnostics"] = git_command_diagnostics
    payload["work_ledger_claim_scan"] = {
        "status": "deferred_for_staged_index_fast_path",
        "reason": "The staged-index quarantine proof route only needs staged path state; use the full preflight when owner-session attribution is required.",
    }
    return payload


def _landing_decision(
    *,
    staged_paths: Sequence[str],
    dirty_paths: Sequence[str],
    declared_paths: Sequence[str],
    classified: Sequence[Mapping[str, Any]],
    dirty_tree: Mapping[str, Any],
    work_ledger: Mapping[str, Any],
    shared_index_quarantine: Mapping[str, Any],
    scoped_commit: Mapping[str, Any],
) -> dict[str, Any]:
    staged_classified = [row for row in classified if row.get("path") in staged_paths]
    unowned_staged = [
        row
        for row in staged_classified
        if row.get("ownership_class") != "owned_declared"
    ]
    write_set_paths = set(declared_paths) | set(staged_paths)
    write_set_coverage_gaps = [
        row
        for row in classified
        if row.get("coverage_gap") and str(row.get("path") or "") in write_set_paths
    ]
    coverage_gaps = [row for row in classified if row.get("coverage_gap")]
    counts = work_ledger.get("counts") if isinstance(work_ledger.get("counts"), Mapping) else {}
    effective_active = int(counts.get("effective_active_sessions") or 0)
    active_claims = int(counts.get("other_active_claims") or counts.get("active_claims") or 0)
    mission_claim_collisions = int(work_ledger.get("collision_count") or 0)
    staged_only_claim_pressure = _staged_only_claim_pressure(
        work_ledger=work_ledger,
        declared_paths=declared_paths,
        staged_paths=staged_paths,
    )
    staged_only_private_index_allowed = (
        bool(staged_only_claim_pressure)
        and bool(shared_index_quarantine.get("private_index_scoped_commit_allowed"))
        and not _int_value(shared_index_quarantine.get("overlap_count"))
    )

    if (
        work_ledger.get("status") == "blocked" or mission_claim_collisions
    ) and not staged_only_private_index_allowed:
        binding_hint = _sessionless_binding_hint(work_ledger)
        if binding_hint:
            return {
                "status": "blocked",
                "reason": "session_id_binding_required",
                "legacy_reason": "work_ledger_claim_collision",
                "recommended_lane": "rerun_preflight_with_candidate_session_id",
                "session_id_hint": binding_hint,
                "claim_or_collision_evidence": _work_ledger_claim_collision_evidence(work_ledger),
                "blocker_classification": "missing_session_binding",
            }
        receipt_requirement = _blocked_primary_receipt_requirement(
            primary_target=_blocked_primary_primary_target(
                declared_paths=declared_paths,
                staged_paths=staged_paths,
                work_ledger=work_ledger,
            ),
            blocker_classification="active_path_claim",
            claim_or_collision_evidence=_work_ledger_claim_collision_evidence(work_ledger),
        )
        decision = {
            "status": "blocked",
            "reason": "work_ledger_claim_collision",
            "recommended_lane": "release_or_wait_for_conflicting_claim",
            "blocked_primary_receipt_requirement": receipt_requirement,
            "blocked_primary_receipt_validation": validate_blocked_primary_continuation_receipt(
                {},
                receipt_requirement,
            ),
        }
        hint = work_ledger.get("sessionless_claim_identity_hint")
        if isinstance(hint, Mapping) and hint.get("status") == "candidate_session_id_available":
            decision["session_id_hint"] = dict(hint)
        return decision
    if unowned_staged:
        if (
            shared_index_quarantine.get("private_index_scoped_commit_allowed")
            and not _int_value(shared_index_quarantine.get("overlap_count"))
        ):
            decision = {
                "status": "review",
                "reason": "shared_index_normal_commit_blocked_private_index_allowed",
                "recommended_lane": "scoped_commit_private_index",
                "shared_index_normal_commit_blocked": True,
                "private_index_scoped_commit_allowed": True,
            }
            if staged_only_claim_pressure:
                decision["staged_index_claim_pressure"] = staged_only_claim_pressure
            return decision
        return {
            "status": "hard_stop",
            "reason": "unowned_staged_index_paths",
            "recommended_lane": "hard_stop_unowned_staged_index",
            "shared_index_normal_commit_blocked": True,
            "private_index_scoped_commit_allowed": False,
        }
    if dirty_tree.get("status") == "blocked":
        return {
            "status": "blocked",
            "reason": "dirty_tree_hard_gate",
            "recommended_lane": "inspect_hard_gate_dirty_paths",
        }
    if staged_paths:
        if not _scoped_commit_usable(scoped_commit):
            return _git_metadata_unavailable_landing_decision(scoped_commit)
        return {
            "status": "review",
            "reason": "staged_index_nonempty_requires_full_index_review",
            "recommended_lane": "scoped_commit_private_index",
        }
    if write_set_coverage_gaps:
        return {
            "status": "blocked",
            "reason": "generated_authority_unknown_for_write_set",
            "recommended_lane": "generated_owner_classification",
        }
    if coverage_gaps:
        return {
            "status": "watch",
            "reason": "generated_like_paths_without_owner_coverage",
            "recommended_lane": "generated_owner_classification",
        }
    if dirty_paths and not _scoped_commit_usable(scoped_commit):
        return _git_metadata_unavailable_landing_decision(scoped_commit)
    if effective_active or active_claims:
        return {
            "status": "watch",
            "reason": "live_work_ledger_pressure",
            "recommended_lane": "claim_then_mutate",
        }
    if dirty_paths:
        if not _scoped_commit_usable(scoped_commit):
            return _git_metadata_unavailable_landing_decision(scoped_commit)
        return {
            "status": "watch",
            "reason": "working_tree_dirty_but_index_empty",
            "recommended_lane": "scoped_commit_private_index",
        }
    return {
            "status": "clear",
            "reason": "clean_index_and_no_dirty_paths",
            "recommended_lane": "direct_local",
        }


def _autonomous_edit_dirty_threshold() -> int:
    raw = os.environ.get("AIW_AUTONOMOUS_EDIT_DIRTY_PATH_THRESHOLD", "").strip()
    if not raw:
        return AUTONOMOUS_EDIT_DIRTY_PATH_THRESHOLD
    try:
        return max(int(raw), 0)
    except ValueError:
        return AUTONOMOUS_EDIT_DIRTY_PATH_THRESHOLD


def _claimed_dirty_paths_for_other_sessions(
    status_rows: Sequence[GitStatusRow],
    work_ledger: Mapping[str, Any],
    *,
    limit: int = COMPACT_PREVIEW_LIMIT,
) -> tuple[int, list[str]]:
    current_session_id = str(work_ledger.get("session_id") or "").strip()
    active_claims = [
        claim
        for claim in work_ledger.get("active_claims") or []
        if isinstance(claim, Mapping)
        and str(claim.get("scope_kind") or "").strip() == "path"
    ]
    count = 0
    preview: list[str] = []
    for row in status_rows:
        for claim in active_claims:
            claim_session_id = str(claim.get("session_id") or "").strip()
            if current_session_id and claim_session_id == current_session_id:
                continue
            claim_path = str(claim.get("path") or claim.get("scope_id") or "").strip("/")
            if not claim_path:
                continue
            if path_scope_overlaps(row.path, claim_path) or path_scope_overlaps(claim_path, row.path):
                count += 1
                if len(preview) < limit:
                    preview.append(row.path)
                break
    return count, preview


def _git_status_ok(git_command_diagnostics: Sequence[Mapping[str, Any]]) -> bool:
    return not any(
        str(row.get("purpose") or "") == "git_status_porcelain"
        and str(row.get("status") or "") in {"error", "timeout"}
        for row in git_command_diagnostics
        if isinstance(row, Mapping)
    )


def _autonomous_edit_gate(
    *,
    status_rows: Sequence[GitStatusRow],
    dirty_tree: Mapping[str, Any],
    shared_index_quarantine: Mapping[str, Any],
    staged_paths: Sequence[str],
    work_ledger: Mapping[str, Any],
    scoped_commit: Mapping[str, Any],
    git_command_diagnostics: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    dirty_path_count = _int_value(dirty_tree.get("dirty_path_count"))
    dirty_threshold = _autonomous_edit_dirty_threshold()
    git_status_ok = _git_status_ok(git_command_diagnostics)
    git_metadata_writable_ok = _git_metadata_writable(scoped_commit)
    scoped_commit_dry_run_ok = bool(
        scoped_commit.get("surface_exists")
        and scoped_commit.get("private_index")
        and scoped_commit.get("head_cas")
        and git_metadata_writable_ok
    )
    other_claim_dirty_count, other_claim_dirty_preview = _claimed_dirty_paths_for_other_sessions(
        status_rows,
        work_ledger,
    )
    dirty_tree_threshold_ok = dirty_path_count <= dirty_threshold
    prior_wave_uncommitted = other_claim_dirty_count > 0
    staged_quarantine_explains_hard_gates = _staged_quarantine_explains_dirty_hard_gates(
        staged_count=len(staged_paths),
        dirty_tree=dirty_tree,
        shared_index_quarantine=shared_index_quarantine,
    )
    dirty_tree_hard_gate = str(dirty_tree.get("status") or "clear") == "blocked"
    unisolated_hard_gate = dirty_tree_hard_gate and not staged_quarantine_explains_hard_gates
    worktree_dirty_policy_ok = not unisolated_hard_gate
    dirty_tree_pressure_only = bool(
        (not dirty_tree_threshold_ok or prior_wave_uncommitted or staged_quarantine_explains_hard_gates)
        and worktree_dirty_policy_ok
    )
    checks = {
        "git_status_ok": git_status_ok,
        "git_metadata_writable_ok": git_metadata_writable_ok,
        "scoped_commit_dry_run_ok": scoped_commit_dry_run_ok,
        "worktree_dirty_policy_ok": worktree_dirty_policy_ok,
    }
    failed_checks = [name for name, ok in checks.items() if not ok]
    if not git_metadata_writable_ok or not scoped_commit_dry_run_ok:
        status = "blocked"
        required_mode = "patch_bundle_only"
        next_action = "package_patch_bundle_before_any_feature_mutation"
    elif not git_status_ok:
        status = "blocked"
        required_mode = "git_status_repair"
        next_action = "repair_git_status_preflight_before_mutation"
    elif unisolated_hard_gate:
        status = "blocked"
        required_mode = "dirty_tree_hard_gate_repair"
        next_action = "inspect_unisolated_hard_gate_dirty_paths_before_feature_mutation"
    else:
        status = "clear"
        required_mode = "claim_scope_then_mutate"
        next_action = "claim_scope_then_mutate"

    return {
        "schema": AUTONOMOUS_EDIT_GATE_SCHEMA,
        "status": status,
        "required_mode": required_mode,
        "next_action": next_action,
        "autonomous_feature_mutation_allowed": status == "clear",
        "checks": checks,
        "failed_checks": failed_checks,
        "dirty_tree_policy": {
            "dirty_path_count": dirty_path_count,
            "threshold": dirty_threshold,
            "threshold_ok": dirty_tree_threshold_ok,
            "prior_wave_uncommitted": prior_wave_uncommitted,
            "other_active_claim_dirty_path_count": other_claim_dirty_count,
            "other_active_claim_dirty_paths_preview": other_claim_dirty_preview,
            "dirty_tree_status": dirty_tree.get("status"),
            "hard_gate_count": dirty_tree.get("hard_gate_count", 0),
            "staged_quarantine_explains_hard_gates": staged_quarantine_explains_hard_gates,
            "unisolated_hard_gate_blocks_feature_mutation": unisolated_hard_gate,
            "dirty_tree_pressure_only": dirty_tree_pressure_only,
            "global_dirty_tree_is_feature_gate": False,
            "unrelated_active_claim_dirty_paths_are_feature_gate": False,
            "policy": (
                "Dirty-path volume, ambient bloat, unrelated active-session dirt, and "
                "unrelated staged-index quarantine are coordination pressure only. "
                "Feature mutation is blocked by git metadata failure, git status failure, "
                "Work Ledger claim collision, or an unisolated hard gate in the intended write set."
            ),
        },
        "patch_bundle_mode": {
            "schema": PATCH_BUNDLE_MODE_SCHEMA,
            "enabled": required_mode == "patch_bundle_only",
            "allowed_outputs": [
                "unified_diff",
                "validation_transcript",
                "recovery_manifest",
            ],
            "forbidden_actions": [
                "feature_wave_mutation",
                "new_organ_or_standard_expansion",
                "landed_closeout_language",
            ],
            "required_artifact": "named_patch_artifact",
        },
        "reconciliation_mode": {
            "schema": RECONCILIATION_MODE_SCHEMA,
            "enabled": required_mode == "dirty_tree_hard_gate_repair",
            "allowed_actions": [
                "inspect_unisolated_hard_gate_dirty_paths",
                "claim_or_remove_from_write_set",
                "route_generated_owner_classification",
                "quarantine_tracked_build_output",
            ],
            "forbidden_actions": [
                "new_feature_work",
                "new_organ",
                "new_standard",
                "new_fixture",
                "seed_rewrite",
            ],
        },
        "closeout_vocabulary": {
            "allowed_statuses": [
                "drafted_on_disk",
                "validated_on_dirty_tree",
                "patch_packaged",
                "committed",
                "released",
            ],
            "landed_requires": [
                "HEAD_after != HEAD_before",
                "or explicitly accepted named patch artifact exists",
            ],
            "release_status_floor_when_blocked": "not_releasable",
        },
    }


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _staged_quarantine_explains_dirty_hard_gates(
    *,
    staged_count: int,
    dirty_tree: Mapping[str, Any],
    shared_index_quarantine: Mapping[str, Any],
) -> bool:
    unowned_staged_count = _int_value(
        shared_index_quarantine.get("unowned_staged_path_count")
    )
    return bool(
        staged_count
        and shared_index_quarantine.get("private_index_scoped_commit_allowed")
        and not _int_value(shared_index_quarantine.get("overlap_count"))
        and _int_value(dirty_tree.get("hard_gate_count")) == unowned_staged_count
        and _int_value(dirty_tree.get("hard_unowned_count")) == unowned_staged_count
    )


def _transaction_candidate_has_mutation_scope(transaction_candidate: Mapping[str, Any]) -> bool:
    write_set = (
        transaction_candidate.get("write_set")
        if isinstance(transaction_candidate.get("write_set"), Mapping)
        else {}
    )
    return any(
        bool(write_set.get(key))
        for key in ("repo_paths", "generated_write_profiles", "projection_outputs")
    )


def _risk_band(status: Any) -> str:
    token = str(status or "").strip()
    return token if token in RISK_BAND_SEVERITY else "watch"


def _path_preview(paths: Sequence[Any], *, limit: int = 25) -> dict[str, Any]:
    items = [str(path) for path in paths]
    return {
        "path_count": len(items),
        "paths_preview": items[:limit],
        "truncated": len(items) > limit,
        "preview_limit": limit,
    }


def _compact_monitor_cards(cards: Any, *, preview_limit: int = 12) -> list[dict[str, Any]]:
    rows = [row for row in cards or [] if isinstance(row, Mapping)]
    compact: list[dict[str, Any]] = []
    for row in rows[:preview_limit]:
        details = row.get("details") if isinstance(row.get("details"), Mapping) else {}
        scalar_details = {
            str(key): value
            for key, value in details.items()
            if isinstance(value, (str, int, float, bool)) or value is None
        }
        compact.append(
            {
                "card_id": row.get("card_id"),
                "status": row.get("status"),
                "severity": row.get("severity"),
                "next_action": row.get("next_action"),
                "detail_count": len(details),
                "details": scalar_details,
            }
        )
    return compact


def _compact_transaction_candidate(row: Any, *, preview_limit: int = 8) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    claim_requirements = (
        row.get("claim_requirements")
        if isinstance(row.get("claim_requirements"), Mapping)
        else {}
    )
    dirty_tree = row.get("dirty_tree") if isinstance(row.get("dirty_tree"), Mapping) else {}
    write_set = row.get("write_set") if isinstance(row.get("write_set"), Mapping) else {}
    finalizers = row.get("finalizers") if isinstance(row.get("finalizers"), Mapping) else {}
    work_item_binding = (
        row.get("work_item_binding")
        if isinstance(row.get("work_item_binding"), Mapping)
        else {}
    )
    subphase_binding = (
        row.get("subphase_binding")
        if isinstance(row.get("subphase_binding"), Mapping)
        else {}
    )
    repo_paths = [item for item in write_set.get("repo_paths") or [] if isinstance(item, Mapping)]
    finalizer_rows = [
        value
        for key, value in finalizers.items()
        if key != "schema" and isinstance(value, Mapping)
    ]
    non_pending_finalizer_statuses = {
        "clear",
        "complete",
        "satisfied",
        "not_required",
        "not_started",
        "recorded",
        "closed_clean",
        "append_exempt",
        "ambient_pressure",
    }
    return {
        "schema": row.get("schema"),
        "status": row.get("status"),
        "transaction_id": row.get("transaction_id"),
        "transaction_candidate_role": row.get("transaction_candidate_role"),
        "base_head": row.get("base_head"),
        "read_set_hash": row.get("read_set_hash"),
        "write_set_hash": row.get("write_set_hash"),
        "work_ledger_session_id": row.get("work_ledger_session_id"),
        "task_ledger_subjects": list(row.get("task_ledger_subjects") or [])[:preview_limit],
        "claim_requirements": {
            "status": claim_requirements.get("status"),
            "claim_required": claim_requirements.get("claim_required"),
            "exclusive_required": claim_requirements.get("exclusive_required"),
            "claimed": claim_requirements.get("claimed"),
            "collision_count": claim_requirements.get("collision_count"),
        },
        "write_set_summary": {
            "repo_path_count": len(repo_paths),
            "repo_paths_preview": [
                {
                    "path": item.get("path"),
                    "ownership": item.get("ownership"),
                    "claim_mode": item.get("claim_mode"),
                }
                for item in repo_paths[:preview_limit]
            ],
            "generated_write_profile_count": len(write_set.get("generated_write_profiles") or []),
            "projection_output_count": len(write_set.get("projection_outputs") or []),
        },
        "dirty_tree": {
            "schema": dirty_tree.get("schema"),
            "status": dirty_tree.get("status"),
            "raw_status": dirty_tree.get("raw_status"),
            "scope_gate_status": dirty_tree.get("scope_gate_status"),
            "dirty_path_count": dirty_tree.get("dirty_path_count", 0),
            "hard_gate_count": dirty_tree.get("hard_gate_count", 0),
            "hard_unowned_count": dirty_tree.get("hard_unowned_count", 0),
            "private_index_scoped_commit_allowed": dirty_tree.get("private_index_scoped_commit_allowed"),
            "global_dirty_tree_blocks_scoped_work": dirty_tree.get("global_dirty_tree_blocks_scoped_work"),
            "by_class": dirty_tree.get("by_class", {}),
        } if dirty_tree else {},
        "finalizers": {
            "schema": finalizers.get("schema"),
            "finalizer_count": len(finalizer_rows),
            "pending_count": sum(
                1
                for item in finalizer_rows
                if item.get("status") not in non_pending_finalizer_statuses
            ),
            "statuses": {
                str(key): value.get("status")
                for key, value in finalizers.items()
                if key != "schema" and isinstance(value, Mapping)
            },
        } if finalizers else {},
        "work_item_binding": {
            "schema": work_item_binding.get("schema"),
            "subject_id": work_item_binding.get("subject_id"),
            "relation": work_item_binding.get("relation"),
            "requires_child_phase": work_item_binding.get("requires_child_phase"),
        } if work_item_binding else {},
        "subphase_binding": {
            "schema": subphase_binding.get("schema"),
            "subject_id": subphase_binding.get("subject_id"),
            "relation": subphase_binding.get("relation"),
            "requires_child_phase": subphase_binding.get("requires_child_phase"),
        } if subphase_binding else {},
        "receipt_destination": row.get("receipt_destination"),
        "full_drilldown": "./repo-python tools/meta/control/mission_transaction_preflight.py --full <same args>",
    }


def _compact_publication_recovery(
    row: Mapping[str, Any],
    *,
    preview_limit: int = COMPACT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    return {
        "schema": row.get("schema"),
        "status": row.get("status"),
        "failure_class": row.get("failure_class"),
        "direct_push_allowed": row.get("direct_push_allowed"),
        "base_ref": row.get("base_ref"),
        "push_range": row.get("push_range"),
        "push_range_commit_count": row.get("push_range_commit_count"),
        "remote_ahead_count": row.get("remote_ahead_count"),
        "blocked_reason_count": row.get("blocked_reason_count"),
        "watch_reason_count": row.get("watch_reason_count"),
        "blocked_path_count": row.get("blocked_path_count"),
        "blocking_class_counts": row.get("blocking_class_counts", {}),
        "blocking_paths_preview": [
            _compact_push_blob_row(item)
            for item in row.get("blocking_paths_preview") or []
            if isinstance(item, Mapping)
        ][:preview_limit],
        "recent_local_commits": list(row.get("recent_local_commits") or [])[:preview_limit],
        "head_commit": row.get("head_commit"),
        "recommended_lane": row.get("recommended_lane"),
        "safe_next_command": row.get("safe_next_command"),
        "proof_route": row.get("proof_route"),
        "operator_boundary": row.get("operator_boundary"),
        "history_rewrite_allowed_by_this_packet": row.get("history_rewrite_allowed_by_this_packet"),
        "force_push_allowed_by_this_packet": row.get("force_push_allowed_by_this_packet"),
    }


def _compact_publication_recovery_summary(
    row: Mapping[str, Any],
    *,
    include_previews: bool,
    preview_limit: int = COMPACT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    blocking_paths = [
        item for item in row.get("blocking_paths_preview") or [] if isinstance(item, Mapping)
    ]
    recent_commits = list(row.get("recent_local_commits") or [])
    payload: dict[str, Any] = {
        "schema": row.get("schema"),
        "status": row.get("status"),
        "failure_class": row.get("failure_class"),
        "direct_push_allowed": row.get("direct_push_allowed"),
        "base_ref": row.get("base_ref"),
        "push_range_commit_count": row.get("push_range_commit_count"),
        "remote_ahead_count": row.get("remote_ahead_count"),
        "blocked_reason_count": row.get("blocked_reason_count"),
        "watch_reason_count": row.get("watch_reason_count"),
        "blocked_path_count": row.get("blocked_path_count"),
        "blocking_path_preview_count": len(blocking_paths),
        "recent_local_commit_count": len(recent_commits),
        "recommended_lane": row.get("recommended_lane"),
        "safe_next_command": row.get("safe_next_command"),
        "proof_route": row.get("proof_route"),
        "history_rewrite_allowed_by_this_packet": row.get("history_rewrite_allowed_by_this_packet"),
        "force_push_allowed_by_this_packet": row.get("force_push_allowed_by_this_packet"),
    }
    if include_previews:
        bounded = min(preview_limit, 3)
        payload["blocking_paths_preview"] = [
            _compact_push_blob_row(item) for item in blocking_paths[:bounded]
        ]
        payload["recent_local_commits"] = recent_commits[:bounded]
        payload["head_commit"] = row.get("head_commit")
    return payload


def _compact_github_push_bloat_gate(
    row: Mapping[str, Any],
    *,
    preview_limit: int = COMPACT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    return {
        "schema": row.get("schema"),
        "status": row.get("status"),
        "mode": row.get("mode"),
        "omitted": row.get("omitted"),
        "omit_reason": row.get("omit_reason"),
        "base_ref": row.get("base_ref"),
        "base": row.get("base"),
        "head": row.get("head"),
        "push_range": row.get("push_range"),
        "workspace_dirty_count": row.get("workspace_dirty_count"),
        "workspace_dirty_is_push_gate": row.get("workspace_dirty_is_push_gate"),
        "workspace_pressure": row.get("workspace_pressure", {}),
        "git_sizer_available": row.get("git_sizer_available"),
        "new_blob_count": row.get("new_blob_count"),
        "changed_path_count": row.get("changed_path_count"),
        "large_blob_count": row.get("large_blob_count"),
        "generated_push_class_counts": row.get("generated_push_class_counts", {}),
        "blocked_reasons": row.get("blocked_reasons", []),
        "watch_reasons": row.get("watch_reasons", []),
        "large_blobs": [
            _compact_push_blob_row(item)
            for item in row.get("large_blobs") or []
            if isinstance(item, Mapping)
        ][:preview_limit],
        "generated_paths": [
            _compact_push_blob_row(item)
            for item in row.get("generated_paths") or []
            if isinstance(item, Mapping)
        ][:preview_limit],
        "publication_recovery": _compact_publication_recovery(
            row.get("publication_recovery") if isinstance(row.get("publication_recovery"), Mapping) else {},
            preview_limit=preview_limit,
        ),
        "policy": row.get("policy"),
    }


def _compact_policy_row_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "path": row.get("path"),
        "owner_id": row.get("owner_id"),
        "artifact_class": row.get("artifact_class"),
        "bloat_class": row.get("bloat_class"),
        "git_policy": row.get("git_policy"),
        "push_gate_disposition": row.get("push_gate_disposition"),
    }


def _compact_workspace_bloat_pressure(
    row: Mapping[str, Any],
    *,
    preview_limit: int = COMPACT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    return {
        "schema": row.get("schema"),
        "status": row.get("status"),
        "reasons": row.get("reasons", []),
        "owner_hint": row.get("owner_hint"),
        "allowed_git_policy": row.get("allowed_git_policy"),
        "drain_or_manifest_command": row.get("drain_or_manifest_command"),
        "next_action": row.get("next_action"),
        "workspace_dirty_count": row.get("workspace_dirty_count"),
        "workspace_dirty_is_push_gate": row.get("workspace_dirty_is_push_gate"),
        "blocked_classes": row.get("blocked_classes", {}),
        "watch_classes": row.get("watch_classes", {}),
        "primary_class": row.get("primary_class"),
        "primary_count": row.get("primary_count"),
        "large_dirty_file_candidates": list(row.get("large_dirty_file_candidates") or [])[:preview_limit],
        "tracked_build_output_count": row.get("tracked_build_output_count"),
        "tracked_build_output_examples": list(row.get("tracked_build_output_examples") or [])[:preview_limit],
        "first_introducing_commit": row.get("first_introducing_commit"),
        "recommended_repair": row.get("recommended_repair"),
        "policy": row.get("policy"),
    }


def _compact_derived_artifact_policy(
    row: Mapping[str, Any],
    *,
    preview_limit: int = COMPACT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    policy_rows = [item for item in row.get("policy_rows") or [] if isinstance(item, Mapping)]
    bloat_preview_limit = min(preview_limit, 5)
    return {
        "schema": row.get("schema"),
        "status": row.get("status"),
        "owner_id": row.get("owner_id"),
        "authority": row.get("authority"),
        "rules": row.get("rules", {}),
        "policy_row_count": len(policy_rows),
        "policy_rows_preview": policy_rows[:bloat_preview_limit],
        "observed_annex_dirty_count": row.get("observed_annex_dirty_count"),
        "observed_by_artifact_class": row.get("observed_by_artifact_class", {}),
        "dirty_blocking_paths_preview": list(row.get("dirty_blocking_paths_preview") or [])[:bloat_preview_limit],
        "staged_blocking_paths_preview": list(row.get("staged_blocking_paths_preview") or [])[:bloat_preview_limit],
        "local_landing_policy": row.get("local_landing_policy"),
        "push_policy": row.get("push_policy"),
    }


def _compact_derived_state_bloat_governor(
    row: Mapping[str, Any],
    *,
    preview_limit: int = COMPACT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    return {
        "schema": row.get("schema"),
        "status": row.get("status"),
        "primary_bloat_class": row.get("primary_bloat_class"),
        "total_dirty_count": row.get("total_dirty_count"),
        "dirty_tree_total_is_local_landing_gate": row.get("dirty_tree_total_is_local_landing_gate"),
        "workspace_dirty_is_push_gate": row.get("workspace_dirty_is_push_gate"),
        "class_rows": list(row.get("class_rows") or [])[:preview_limit],
        "workspace_bloat_pressure": _compact_workspace_bloat_pressure(
            row.get("workspace_bloat_pressure")
            if isinstance(row.get("workspace_bloat_pressure"), Mapping)
            else {},
            preview_limit=preview_limit,
        ),
        "github_push_bloat_gate": _compact_github_push_bloat_gate(
            row.get("github_push_bloat_gate")
            if isinstance(row.get("github_push_bloat_gate"), Mapping)
            else {},
            preview_limit=preview_limit,
        ),
        "derived_artifact_policy": _compact_derived_artifact_policy(
            row.get("derived_artifact_policy")
            if isinstance(row.get("derived_artifact_policy"), Mapping)
            else {},
            preview_limit=preview_limit,
        ),
    }


def _compact_derived_state_bloat_governor_summary(
    row: Mapping[str, Any],
    *,
    preview_limit: int = COMPACT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    workspace = row.get("workspace_bloat_pressure") if isinstance(row.get("workspace_bloat_pressure"), Mapping) else {}
    push_gate = row.get("github_push_bloat_gate") if isinstance(row.get("github_push_bloat_gate"), Mapping) else {}
    artifact_policy = row.get("derived_artifact_policy") if isinstance(row.get("derived_artifact_policy"), Mapping) else {}
    policy_rows = [item for item in artifact_policy.get("policy_rows") or [] if isinstance(item, Mapping)]
    bloat_preview_limit = min(preview_limit, 3)
    push_gate_omitted = bool(push_gate.get("omitted")) or str(push_gate.get("mode") or "") == "local_preflight_fast_path"
    push_preview_limit = 0 if push_gate_omitted else min(preview_limit, 3)
    large_blob_rows = [
        item for item in push_gate.get("large_blobs") or [] if isinstance(item, Mapping)
    ]
    generated_path_rows = [
        item for item in push_gate.get("generated_paths") or [] if isinstance(item, Mapping)
    ]
    compact_push_gate: dict[str, Any] = {
        "schema": push_gate.get("schema"),
        "status": push_gate.get("status"),
        "mode": push_gate.get("mode"),
        "omitted": push_gate.get("omitted"),
        "changed_path_count": push_gate.get("changed_path_count"),
        "new_blob_count": push_gate.get("new_blob_count"),
        "large_blob_count": push_gate.get("large_blob_count"),
        "large_blob_preview_count": len(large_blob_rows),
        "generated_path_preview_count": len(generated_path_rows),
        "publication_recovery": _compact_publication_recovery_summary(
            push_gate.get("publication_recovery")
            if isinstance(push_gate.get("publication_recovery"), Mapping)
            else {},
            include_previews=not push_gate_omitted,
            preview_limit=preview_limit,
        ),
    }
    if push_preview_limit:
        compact_push_gate["large_blobs"] = [
            _compact_push_blob_row(item) for item in large_blob_rows[:push_preview_limit]
        ]
        compact_push_gate["generated_paths"] = [
            _compact_push_blob_row(item) for item in generated_path_rows[:push_preview_limit]
        ]
    return {
        "schema": row.get("schema"),
        "status": row.get("status"),
        "primary_bloat_class": row.get("primary_bloat_class"),
        "total_dirty_count": row.get("total_dirty_count"),
        "workspace_bloat_pressure": {
            "schema": workspace.get("schema"),
            "status": workspace.get("status"),
            "primary_class": workspace.get("primary_class"),
            "primary_count": workspace.get("primary_count"),
        },
        "github_push_bloat_gate": compact_push_gate,
        "derived_artifact_policy": {
            "schema": artifact_policy.get("schema"),
            "status": artifact_policy.get("status"),
            "policy_row_count": len(policy_rows),
            "policy_rows_preview": [
                _compact_policy_row_summary(item) for item in policy_rows[:bloat_preview_limit]
            ],
            "observed_annex_dirty_count": artifact_policy.get("observed_annex_dirty_count"),
        },
    }


def _compact_shared_index_quarantine_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    return {
        "schema": row.get("schema"),
        "status": row.get("status"),
        "next_action": row.get("next_action"),
        "staged_path_count": row.get("staged_path_count", 0),
        "unowned_staged_path_count": row.get("unowned_staged_path_count", 0),
        "owned_staged_path_count": row.get("owned_staged_path_count", 0),
        "overlap_count": row.get("overlap_count", 0),
        "stale_reverse_index_entry_count": row.get("stale_reverse_index_entry_count", 0),
        "normal_git_commit_allowed": row.get("normal_git_commit_allowed"),
        "shared_index_normal_commit_blocked": row.get("shared_index_normal_commit_blocked"),
        "private_index_scoped_commit_allowed": row.get("private_index_scoped_commit_allowed"),
        "git_metadata_write_status": row.get("git_metadata_write_status"),
        "git_metadata_write_failure_class": row.get("git_metadata_write_failure_class"),
        "recommended_action": row.get("recommended_action"),
    }


def _compact_derived_state_bloat_governor_status(row: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    workspace = row.get("workspace_bloat_pressure") if isinstance(row.get("workspace_bloat_pressure"), Mapping) else {}
    push_gate = row.get("github_push_bloat_gate") if isinstance(row.get("github_push_bloat_gate"), Mapping) else {}
    artifact_policy = row.get("derived_artifact_policy") if isinstance(row.get("derived_artifact_policy"), Mapping) else {}
    return {
        "schema": row.get("schema"),
        "status": row.get("status"),
        "primary_bloat_class": row.get("primary_bloat_class"),
        "total_dirty_count": row.get("total_dirty_count"),
        "workspace_bloat_pressure": {
            "status": workspace.get("status"),
            "primary_class": workspace.get("primary_class"),
            "primary_count": workspace.get("primary_count"),
        },
        "github_push_bloat_gate": {
            "status": push_gate.get("status"),
            "mode": push_gate.get("mode"),
            "omitted": push_gate.get("omitted"),
            "large_blob_count": push_gate.get("large_blob_count"),
            "generated_path_preview_count": len(push_gate.get("generated_paths") or []),
        },
        "derived_artifact_policy": {
            "status": artifact_policy.get("status"),
            "policy_row_count": len(artifact_policy.get("policy_rows") or []),
            "observed_annex_dirty_count": artifact_policy.get("observed_annex_dirty_count"),
        },
        "full_drilldown": "./repo-python tools/meta/control/mission_transaction_preflight.py --bloat-governor <same args>",
    }


def _compact_transaction_convergence_reconcile(
    row: Mapping[str, Any],
    *,
    preview_limit: int = COMPACT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    write_set_preflight = (
        row.get("receipt_write_set_preflight")
        if isinstance(row.get("receipt_write_set_preflight"), Mapping)
        else {}
    )
    actions = [item for item in row.get("actions") or [] if isinstance(item, Mapping)]
    return {
        "schema": row.get("schema"),
        "mode": row.get("mode"),
        "status": row.get("status"),
        "next_action": row.get("next_action"),
        "target_ids": list(row.get("target_ids") or [])[:preview_limit],
        "counts": row.get("counts", {}),
        "receipt_write_set_preflight": {
            "status": write_set_preflight.get("status"),
            "require_exclusive": write_set_preflight.get("require_exclusive"),
            "collision_count": write_set_preflight.get("collision_count", 0),
            "same_file_entanglement_count": len(write_set_preflight.get("same_file_entanglement_paths") or []),
            "blocking_claim_count": len(write_set_preflight.get("blocking_claims") or []),
        } if write_set_preflight else {},
        "action_count": len(actions),
        "actions_preview": [
            {
                "subject_id": item.get("subject_id"),
                "transaction_id": item.get("transaction_id"),
                "commit_hash": item.get("commit_hash"),
                "closeout_state": item.get("closeout_state"),
                "status": item.get("status"),
            }
            for item in actions[: min(preview_limit, 3)]
        ],
        "mutation_policy": row.get("mutation_policy"),
        "full_drilldown": "./repo-python tools/meta/control/mission_transaction_preflight.py --reconcile-plan <same args>",
    }


def _compact_scoped_commit_capability(row: Any) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    git_metadata_write = (
        row.get("git_metadata_write")
        if isinstance(row.get("git_metadata_write"), Mapping)
        else {}
    )
    return {
        "available": row.get("available"),
        "surface_exists": row.get("surface_exists"),
        "surface": row.get("surface"),
        "private_index": row.get("private_index"),
        "head_cas": row.get("head_cas"),
        "modes": row.get("modes", []),
        "git_metadata_write": {
            "schema": git_metadata_write.get("schema"),
            "status": git_metadata_write.get("status"),
            "writable": git_metadata_write.get("writable"),
            "reason": git_metadata_write.get("reason"),
            "failure_class": git_metadata_write.get("failure_class"),
            "owner_repair_commands": list(git_metadata_write.get("owner_repair_commands") or [])[:3],
        } if git_metadata_write else {},
    }


def _compact_transaction_convergence(
    row: Mapping[str, Any],
    *,
    preview_limit: int = COMPACT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    current = row.get("current_transaction") if isinstance(row.get("current_transaction"), Mapping) else {}
    receipt_state = row.get("task_ledger_receipt_state") if isinstance(row.get("task_ledger_receipt_state"), Mapping) else {}
    finalizer_classes = row.get("finalizer_classes") if isinstance(row.get("finalizer_classes"), Mapping) else {}
    recent_transactions = [
        item for item in row.get("recent_transactions") or [] if isinstance(item, Mapping)
    ]
    dirty_budgets = (
        row.get("dirty_tree_class_budgets")
        if isinstance(row.get("dirty_tree_class_budgets"), Mapping)
        else {}
    )
    budget_rows = [item for item in dirty_budgets.get("class_rows") or [] if isinstance(item, Mapping)]
    workitem_state = (
        row.get("workitem_landing_attempt_state")
        if isinstance(row.get("workitem_landing_attempt_state"), Mapping)
        else {}
    )
    subphase_rollup = (
        row.get("subphase_rollup")
        if isinstance(row.get("subphase_rollup"), Mapping)
        else {}
    )
    return {
        "schema": row.get("schema"),
        "phase_id": row.get("phase_id"),
        "wave_id": row.get("wave_id"),
        "status": row.get("status"),
        "next_action": row.get("next_action"),
        "authority": row.get("authority", {}),
        "current_transaction": {
            "transaction_id": current.get("transaction_id"),
            "status": current.get("status"),
            "transaction_candidate_role": current.get("transaction_candidate_role"),
            "mutation_requires_begin": current.get("mutation_requires_begin"),
            "shadow_state": current.get("shadow_state"),
            "canonical_transaction_id": current.get("canonical_transaction_id"),
            "finalizer_count": current.get("finalizer_count"),
                "compatibility_finalizer_count": current.get("compatibility_finalizer_count"),
                "ambient_pressure_count": len(current.get("ambient_pressure") or []),
                "base_head": current.get("base_head"),
                "read_set_hash": current.get("read_set_hash"),
                "write_set_hash": current.get("write_set_hash"),
            },
        "workitem_landing_attempt_state": {
            "schema": workitem_state.get("schema"),
            "status": workitem_state.get("status"),
            "subject_id": workitem_state.get("subject_id"),
            "attempt_count": workitem_state.get("attempt_count"),
            "open_attempt_count": workitem_state.get("open_attempt_count"),
            "latest_attempt_status": workitem_state.get("latest_attempt_status"),
        } if workitem_state else {},
        "canonical_transaction_state": row.get("canonical_transaction_state", {}),
        "finalizer_classes": {
            "transaction_local_finalizers": list(finalizer_classes.get("transaction_local_finalizers") or [])[:preview_limit],
            "ambient_pressure_count": len(finalizer_classes.get("ambient_pressure") or []),
            "compatibility_finalizer_count": len(finalizer_classes.get("compatibility_finalizers") or []),
        },
        "recent_transaction_count": len(recent_transactions),
        "recent_transactions_preview": [
            {
                "transaction_id": item.get("transaction_id"),
                "status": item.get("status"),
                "task_ledger_receipt_status": (
                    item.get("task_ledger_execution_receipt") or {}
                ).get("status") if isinstance(item.get("task_ledger_execution_receipt"), Mapping) else None,
                "commit_ref_count": len(item.get("commit_refs") or []),
                "work_ledger_closed": item.get("work_ledger_closed"),
            }
            for item in recent_transactions[:preview_limit]
        ],
        "summary": row.get("summary", {}),
        "task_ledger_receipt_state": {
            "subject_ids": receipt_state.get("subject_ids", []),
            "receipt_ref_count": len(receipt_state.get("receipt_refs") or []),
            "commit_refs": list(receipt_state.get("commit_refs") or [])[:preview_limit],
            "work_ledger_refs": list(receipt_state.get("work_ledger_refs") or [])[:preview_limit],
            "latest_execution_receipt": receipt_state.get("latest_execution_receipt"),
            "latest_execution_receipt_work_ledger_session_state": receipt_state.get(
                "latest_execution_receipt_work_ledger_session_state"
            ),
        },
        "work_ledger_stale_session_count": len(row.get("work_ledger_stale_sessions") or []),
        "work_ledger_stale_sessions_preview": list(row.get("work_ledger_stale_sessions") or [])[:preview_limit],
        "work_ledger_append_exempt_session_count": len(row.get("work_ledger_append_exempt_sessions") or []),
        "shared_index_quarantine": _compact_shared_index_quarantine_summary(
            row.get("shared_index_quarantine")
            if isinstance(row.get("shared_index_quarantine"), Mapping)
            else {},
        ),
        "dirty_tree_class_budgets": {
            "schema": dirty_budgets.get("schema"),
            "total_dirty_count": dirty_budgets.get("total_dirty_count"),
            "class_count": len(budget_rows),
            "class_rows_preview": [
                {
                    "class_id": item.get("class_id"),
                    "count": item.get("count"),
                    "budget_status": item.get("budget_status"),
                    "blocks_local_landing": item.get("blocks_local_landing"),
                }
                for item in budget_rows[:preview_limit]
            ],
        } if dirty_budgets else {},
        "derived_state_bloat_governor": _compact_derived_state_bloat_governor_status(
            row.get("derived_state_bloat_governor")
            if isinstance(row.get("derived_state_bloat_governor"), Mapping)
            else {},
        ),
        "subphase_rollup": {
            "schema": subphase_rollup.get("schema"),
            "status": subphase_rollup.get("status"),
            "child_transaction_count": subphase_rollup.get("child_transaction_count"),
            "open_finalizer_count": subphase_rollup.get("open_finalizer_count"),
            "pending_intake_count": subphase_rollup.get("pending_intake_count"),
            "stale_session_count": subphase_rollup.get("stale_session_count"),
        } if subphase_rollup else {},
    }


PATH_CLASSIFICATION_SIGNATURE_KEYS = (
    "ownership_class",
    "generation_class",
    "stageability_class",
    "source_authority",
    "coverage_gap",
)


def _path_classification_signature(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in PATH_CLASSIFICATION_SIGNATURE_KEYS}


def _compact_path_classifications(
    rows: Sequence[Mapping[str, Any]],
    *,
    owned_paths: Sequence[str],
    staged_paths: Sequence[str],
    coverage_gap_paths: Sequence[str],
    full_count: int,
    preview_limit: int,
) -> dict[str, Any]:
    path_values = [str(row.get("path") or "") for row in rows if row.get("path")]
    owned_path_set = set(owned_paths)
    signatures = {
        json.dumps(_path_classification_signature(row), sort_keys=True)
        for row in rows
    }
    homogeneous_collapse_threshold = min(preview_limit, 8)
    homogeneous_owned = (
        len(rows) > homogeneous_collapse_threshold
        and bool(rows)
        and not staged_paths
        and not coverage_gap_paths
        and all(path in owned_path_set for path in path_values)
        and len(signatures) == 1
    )
    if homogeneous_owned:
        signature = _path_classification_signature(rows[0])
        return {
            "rows": [],
            "summary": {
                "status": "homogeneous_owned_rows_omitted",
                "row_count": len(rows),
                "path_preview": _path_preview(
                    path_values,
                    limit=homogeneous_collapse_threshold,
                ),
                **signature,
            },
            "omission": {
                "returned_count": 0,
                "full_count": full_count,
                "homogeneous_omitted_count": len(rows),
                "rule": (
                    "compact profile collapses homogeneous owned path classifications; "
                    "staged, coverage-gap, mixed, or short path rows remain explicit"
                ),
            },
        }
    return {
        "rows": list(rows),
        "summary": {
            "status": "explicit_rows",
            "row_count": len(rows),
            "mixed_signature_count": len(signatures),
            "homogeneous_omitted_count": 0,
        },
        "omission": {
            "returned_count": len(rows),
            "full_count": full_count,
            "homogeneous_omitted_count": 0,
            "rule": "compact profile returns owned, staged, and coverage-gap paths only",
        },
    }


def compact_mission_transaction_landing_preflight(
    packet: Mapping[str, Any],
    *,
    preview_limit: int = COMPACT_PREVIEW_LIMIT,
) -> dict[str, Any]:
    """Return the decision-sufficient preflight packet for CLI defaults."""
    git = packet.get("git") if isinstance(packet.get("git"), Mapping) else {}
    work_ledger = packet.get("work_ledger") if isinstance(packet.get("work_ledger"), Mapping) else {}
    shared_guard = packet.get("shared_worktree_guard") if isinstance(packet.get("shared_worktree_guard"), Mapping) else {}
    registry = packet.get("generated_projection_registry") if isinstance(packet.get("generated_projection_registry"), Mapping) else {}
    projection_settlement = (
        packet.get("generated_projection_settlement")
        if isinstance(packet.get("generated_projection_settlement"), Mapping)
        else {}
    )
    closeout_settlement = (
        packet.get("transaction_closeout_settlement")
        if isinstance(packet.get("transaction_closeout_settlement"), Mapping)
        else {}
    )
    dirty_tree = packet.get("dirty_tree_classification") if isinstance(packet.get("dirty_tree_classification"), Mapping) else {}
    autonomous_edit_gate = (
        packet.get("autonomous_edit_gate")
        if isinstance(packet.get("autonomous_edit_gate"), Mapping)
        else {}
    )
    shared_index_quarantine = (
        packet.get("shared_index_quarantine")
        if isinstance(packet.get("shared_index_quarantine"), Mapping)
        else {}
    )
    coverage_gaps = [row for row in packet.get("coverage_gaps") or [] if isinstance(row, Mapping)]
    inputs = packet.get("inputs") if isinstance(packet.get("inputs"), Mapping) else {}
    owned_paths = [str(path) for path in inputs.get("owned_paths") or []]
    staged_paths = [str(path) for path in git.get("staged_paths") or []]
    coverage_gap_paths = [str(row.get("path") or "") for row in coverage_gaps if row.get("path")]
    requested_path_set = set(owned_paths) | set(staged_paths) | set(coverage_gap_paths)
    requested_classifications = [
        row
        for row in packet.get("path_classifications") or []
        if isinstance(row, Mapping) and str(row.get("path") or "") in requested_path_set
    ]
    compact_classifications = _compact_path_classifications(
        requested_classifications,
        owned_paths=owned_paths,
        staged_paths=staged_paths,
        coverage_gap_paths=coverage_gap_paths,
        full_count=len(packet.get("path_classifications") or []),
        preview_limit=preview_limit,
    )

    risky_operations = [
        row
        for row in shared_guard.get("risky_git_operations") or []
        if isinstance(row, Mapping)
    ]
    blocked_risky_operations = [
        {
            "argv": row.get("argv"),
            "risk_count": ((row.get("decision") or {}).get("risk_count") if isinstance(row.get("decision"), Mapping) else None),
            "blocked": ((row.get("decision") or {}).get("blocked") if isinstance(row.get("decision"), Mapping) else None),
        }
        for row in risky_operations
        if isinstance(row.get("decision"), Mapping) and row["decision"].get("blocked")
    ]

    return {
        "schema": packet.get("schema") or SCHEMA,
        "repo_root": packet.get("repo_root"),
        "mode": packet.get("mode") or "read_only",
        "output_profile": "compact",
        "compact_contract": {
            "safe_decision_supported": "Decide whether scoped landing may proceed and which full drilldowns to inspect.",
            "full_profile_command": "./repo-python tools/meta/control/mission_transaction_preflight.py --full <same args>",
            "omits": [
                "full dirty path list",
                "full git status rows",
                "full path classifications for unrelated dirty paths",
                "full work ledger contention payload",
                "full generated projection registry",
                "full shared-worktree risk decisions",
                "full transaction convergence drilldown",
                "full derived-state bloat governor drilldown",
                "push-range blob scan unless explicitly requested",
            ],
        },
        "monitor_summary": packet.get("monitor_summary"),
        "monitor_cards": _compact_monitor_cards(packet.get("monitor_cards"), preview_limit=preview_limit),
        "monitor_card_omission": {
            "returned_count": min(len(packet.get("monitor_cards") or []), preview_limit),
            "full_count": len(packet.get("monitor_cards") or []),
            "rule": "compact profile returns card status handles and scalar detail counts only",
            "full_profile_command": "./repo-python tools/meta/control/mission_transaction_preflight.py --full <same args>",
        },
        "transaction_candidate": _compact_transaction_candidate(
            packet.get("transaction_candidate"),
            preview_limit=preview_limit,
        ),
        "transaction_convergence": _compact_transaction_convergence(
            packet.get("transaction_convergence")
            if isinstance(packet.get("transaction_convergence"), Mapping)
            else {},
            preview_limit=preview_limit,
        ),
        "transaction_convergence_reconcile": _compact_transaction_convergence_reconcile(
            packet.get("transaction_convergence_reconcile")
            if isinstance(packet.get("transaction_convergence_reconcile"), Mapping)
            else {},
            preview_limit=preview_limit,
        ),
        "shared_index_quarantine": {
            "schema": shared_index_quarantine.get("schema"),
            "status": shared_index_quarantine.get("status"),
            "next_action": shared_index_quarantine.get("next_action"),
            "staged_path_count": shared_index_quarantine.get("staged_path_count", 0),
            "unowned_staged_path_count": shared_index_quarantine.get("unowned_staged_path_count", 0),
            "owned_staged_path_count": shared_index_quarantine.get("owned_staged_path_count", 0),
            "overlap_count": shared_index_quarantine.get("overlap_count", 0),
            "stale_reverse_index_entry_count": shared_index_quarantine.get("stale_reverse_index_entry_count", 0),
            "stale_reverse_paths_preview": shared_index_quarantine.get("stale_reverse_paths_preview", []),
            "index_entry_state_scan_truncated": shared_index_quarantine.get("index_entry_state_scan_truncated"),
            "normal_git_commit_allowed": shared_index_quarantine.get("normal_git_commit_allowed"),
            "shared_index_normal_commit_blocked": shared_index_quarantine.get("shared_index_normal_commit_blocked"),
            "private_index_scoped_commit_allowed": shared_index_quarantine.get("private_index_scoped_commit_allowed"),
            "recommended_action": shared_index_quarantine.get("recommended_action"),
            "paths_preview": shared_index_quarantine.get("paths_preview", []),
        } if shared_index_quarantine else {},
        "derived_state_bloat_governor": _compact_derived_state_bloat_governor_summary(
            packet.get("derived_state_bloat_governor")
            if isinstance(packet.get("derived_state_bloat_governor"), Mapping)
            else {},
            preview_limit=preview_limit,
        ),
        "dirty_tree_classification": {
            "schema": dirty_tree.get("schema"),
            "status": dirty_tree.get("status"),
            "raw_status": dirty_tree.get("raw_status"),
            "scope_gate_status": dirty_tree.get("scope_gate_status"),
            "dirty_path_count": dirty_tree.get("dirty_path_count", 0),
            "classified_count": dirty_tree.get("classified_count", 0),
            "hard_gate_count": dirty_tree.get("hard_gate_count", 0),
            "hard_unowned_count": dirty_tree.get("hard_unowned_count", 0),
            "private_index_scoped_commit_allowed": dirty_tree.get("private_index_scoped_commit_allowed"),
            "global_dirty_tree_blocks_scoped_work": dirty_tree.get("global_dirty_tree_blocks_scoped_work"),
            "by_class": dirty_tree.get("by_class", {}),
            "by_severity": dirty_tree.get("by_severity", {}),
            "hard_unowned_paths_preview": dirty_tree.get("hard_unowned_paths_preview", []),
            "next_action": dirty_tree.get("next_action"),
        } if dirty_tree else {},
        "autonomous_edit_gate": {
            "schema": autonomous_edit_gate.get("schema"),
            "status": autonomous_edit_gate.get("status"),
            "required_mode": autonomous_edit_gate.get("required_mode"),
            "next_action": autonomous_edit_gate.get("next_action"),
            "autonomous_feature_mutation_allowed": autonomous_edit_gate.get(
                "autonomous_feature_mutation_allowed"
            ),
            "checks": autonomous_edit_gate.get("checks", {}),
            "failed_checks": autonomous_edit_gate.get("failed_checks", []),
            "dirty_tree_policy": autonomous_edit_gate.get("dirty_tree_policy", {}),
            "patch_bundle_mode": autonomous_edit_gate.get("patch_bundle_mode", {}),
            "reconciliation_mode": autonomous_edit_gate.get("reconciliation_mode", {}),
            "closeout_vocabulary": autonomous_edit_gate.get("closeout_vocabulary", {}),
        } if autonomous_edit_gate else {},
        "recommended_landing_lane": packet.get("recommended_landing_lane"),
        "mutation_policy": packet.get("mutation_policy"),
        "inputs": dict(inputs),
        "git": {
            "staged_path_count": git.get("staged_path_count", 0),
            "staged_paths": staged_paths,
            "cached_stat": git.get("cached_stat", ""),
            "dirty_path_count": git.get("dirty_path_count", 0),
            "dirty_path_preview": _path_preview(git.get("dirty_paths") or [], limit=min(preview_limit, 12)),
            "status_row_count": len(git.get("status_rows") or []),
            "command_diagnostics": git.get("command_diagnostics", []),
            "full_status_drilldown": "git status --short",
        },
        "path_classifications": compact_classifications["rows"],
        "path_classification_summary": compact_classifications["summary"],
        "path_classification_omission": compact_classifications["omission"],
        "coverage_gaps": coverage_gaps,
        "work_ledger": {
            "status": work_ledger.get("status"),
            "require_exclusive": work_ledger.get("require_exclusive"),
            "session_id": work_ledger.get("session_id"),
            "requested_session_id": work_ledger.get("requested_session_id"),
            "session_id_resolution": work_ledger.get("session_id_resolution", {}),
            "counts": work_ledger.get("counts", {}),
            "collision_count": work_ledger.get("collision_count", 0),
            "collisions": work_ledger.get("collisions", []),
            "sessionless_claim_identity_hint": work_ledger.get("sessionless_claim_identity_hint", {}),
            "path_collision_count": work_ledger.get("path_collision_count", 0),
            "subject_or_td_collision_count": work_ledger.get("subject_or_td_collision_count", 0),
        },
        "generated_projection_registry": {
            "kind": registry.get("kind"),
            "schema_version": registry.get("schema_version"),
            "owner_count": len(registry.get("owners") or []),
            "full_drilldown": "./repo-python tools/meta/control/mission_transaction_preflight.py --full <same args>",
        },
        "generated_projection_settlement": {
            "schema": projection_settlement.get("schema"),
            "status": projection_settlement.get("status"),
            "reason": projection_settlement.get("reason"),
            "can_settle": projection_settlement.get("can_settle"),
            "dirty_owner_count": projection_settlement.get("dirty_owner_count", 0),
            "refresh_required_owner_count": projection_settlement.get("refresh_required_owner_count", 0),
            "blocked_owner_count": projection_settlement.get("blocked_owner_count", 0),
            "supported_owner_ids": projection_settlement.get("supported_owner_ids", []),
            "required_next_command": projection_settlement.get("required_next_command"),
            "eventful_closeout_allowed_after_settlement": projection_settlement.get(
                "eventful_closeout_allowed_after_settlement"
            ),
            "owners": [
                {
                    "owner_id": row.get("owner_id"),
                    "status": row.get("status"),
                    "required_action": row.get("required_action"),
                    "can_apply": row.get("can_apply"),
                }
                for row in projection_settlement.get("owners") or []
                if isinstance(row, Mapping)
            ],
        } if projection_settlement else {},
        "transaction_closeout_settlement": {
            "schema": closeout_settlement.get("schema"),
            "status": closeout_settlement.get("status"),
            "eventful_finalizers_pending": closeout_settlement.get("eventful_finalizers_pending", []),
            "projection_settlement_status": closeout_settlement.get("projection_settlement_status"),
            "projection_settlement_deferred_reason": closeout_settlement.get(
                "projection_settlement_deferred_reason"
            ),
            "projection_dirty_owner_count": closeout_settlement.get("projection_dirty_owner_count", 0),
            "projection_blocked_owner_count": closeout_settlement.get("projection_blocked_owner_count", 0),
            "eventful_closeout_allowed_now": closeout_settlement.get("eventful_closeout_allowed_now"),
            "eventful_closeout_allowed_after_settlement": closeout_settlement.get(
                "eventful_closeout_allowed_after_settlement"
            ),
            "required_next_command": closeout_settlement.get("required_next_command"),
            "ordering_rule": closeout_settlement.get("ordering_rule"),
        } if closeout_settlement else {},
        "scoped_commit_capability": _compact_scoped_commit_capability(packet.get("scoped_commit_capability")),
        "shared_worktree_guard": {
            "surface": shared_guard.get("surface"),
            "dirty_path_count": shared_guard.get("dirty_path_count", 0),
            "blocked_risky_operation_count": len(blocked_risky_operations),
            "blocked_risky_operations": blocked_risky_operations,
            "index_mutating_commands_need_serialization": shared_guard.get("index_mutating_commands_need_serialization", []),
        },
        "mission_transaction_card": packet.get("mission_transaction_card"),
        "landing_decision": packet.get("landing_decision"),
    }


def _repair_packet_status(*packets: Mapping[str, Any]) -> str:
    status = "clear"
    for packet in packets:
        candidate = _risk_band(str(packet.get("status") or "clear"))
        if RISK_BAND_SEVERITY[candidate] > RISK_BAND_SEVERITY[status]:
            status = candidate
    return status


def _workitem_child_transaction_rollup(
    *,
    rollup: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = (
        packet.get("transaction_candidate")
        if isinstance(packet.get("transaction_candidate"), Mapping)
        else {}
    )
    binding = (
        candidate.get("work_item_binding")
        if isinstance(candidate.get("work_item_binding"), Mapping)
        else {}
    )
    return {
        "schema": "workitem_child_transaction_rollup_v1",
        "subject_id": binding.get("subject_id") or _control_summary_subject_id(packet),
        "subject_kind": binding.get("subject_kind"),
        "child_transaction_count": rollup.get("child_transaction_count"),
        "open_finalizer_count": rollup.get("open_finalizer_count"),
        "pending_intake_count": rollup.get("pending_intake_count"),
        "stale_session_count": rollup.get("stale_session_count"),
        "push_gate_status": rollup.get("push_gate_status"),
        "workspace_bloat_status": rollup.get("workspace_bloat_status"),
        "staged_quarantine_status": rollup.get("staged_quarantine_status"),
        "private_index_scoped_commit_allowed": rollup.get("private_index_scoped_commit_allowed"),
        "compat_phase_context": {
            "phase_id": rollup.get("phase_id"),
            "wave_id": rollup.get("wave_id"),
            "legacy_rollup_schema": rollup.get("schema"),
            "compatibility_only": True,
        },
        "rollup_home": "workitem_control_picture.transaction_control_plane",
    }


def _first_reason(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            text = str(item).strip()
            if text:
                return text
    return fallback


def _action_text(*values: Any, fallback: str) -> str:
    for value in values:
        text = str(value or "").strip()
        if text and text != "none":
            return text
    return fallback


def _control_summary_subject_id(packet: Mapping[str, Any]) -> str:
    inputs = packet.get("inputs") if isinstance(packet.get("inputs"), Mapping) else {}
    target_ids_value = inputs.get("target_ids")
    target_ids = (
        target_ids_value
        if isinstance(target_ids_value, Sequence) and not isinstance(target_ids_value, (str, bytes))
        else []
    )
    for target_id in target_ids:
        text = str(target_id or "").strip()
        if text:
            return text
    return DEFAULT_CONTROL_SUMMARY_SUBJECT_ID


def _preflight_drilldown_command(subject_id: str, flag: str) -> str:
    return (
        "./repo-python tools/meta/control/mission_transaction_preflight.py "
        f"--subject-id {subject_id} {flag}"
    )


def _repair_packet_row(
    *,
    row_id: str,
    owner: str,
    failure_class: str,
    source_status: str,
    summary: str,
    safe_next_command: str,
    proof_route: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "row_id": row_id,
        "owner": owner,
        "failure_class": failure_class,
        "status": _risk_band(source_status),
        "summary": summary,
        "safe_next_command": safe_next_command,
        "proof_route": proof_route,
        "details": dict(details or {}),
    }


def _workspace_pressure_safe_next_command(
    *,
    subject_id: str,
    workspace_pressure: Mapping[str, Any],
) -> str:
    command = str(
        workspace_pressure.get("next_action")
        or workspace_pressure.get("drain_or_manifest_command")
        or ""
    ).strip()
    if command.startswith("./repo-python "):
        return command
    return _preflight_drilldown_command(subject_id, "--workspace-bloat-pressure")


def _runtime_artifact_watch_actionability(
    *,
    workspace_pressure: Mapping[str, Any],
    runtime_artifact_lifecycle: Mapping[str, Any],
) -> dict[str, Any]:
    if str(workspace_pressure.get("primary_class") or "").strip() != "runtime_run_artifact":
        return {
            "schema": "watch_actionability_contract_v0",
            "status": "not_runtime_artifact_primary",
            "blocks_transaction": str(workspace_pressure.get("status") or "") == "blocked",
            "blocks_closeout": False,
        }
    owner_routed = str(workspace_pressure.get("owner_hint") or "").strip() == "runtime_artifact_lifecycle"
    cleanup_eligible_count = _int_value(runtime_artifact_lifecycle.get("cleanup_eligible_count"))
    apply_available = bool(runtime_artifact_lifecycle.get("apply_available"))
    lifecycle_present = (
        str(runtime_artifact_lifecycle.get("schema") or "").strip()
        == RUNTIME_ARTIFACT_LIFECYCLE_SCHEMA
    )
    if not owner_routed or not lifecycle_present:
        status = "owner_route_missing"
        blocks_transaction = True
        blocks_closeout = True
        next_safe_action = "capture_runtime_artifact_owner_gap"
    elif cleanup_eligible_count > 0 and apply_available:
        status = "actionable_cleanup"
        blocks_transaction = True
        blocks_closeout = True
        next_safe_action = "run_runtime_artifact_lifecycle_apply"
    elif cleanup_eligible_count == 0 and not apply_available:
        status = "nonblocking_preserve"
        blocks_transaction = False
        blocks_closeout = False
        next_safe_action = "preserve_and_resume_closeout"
    else:
        status = "lifecycle_review_required"
        blocks_transaction = True
        blocks_closeout = True
        next_safe_action = "inspect_runtime_artifact_lifecycle"
    return {
        "schema": "watch_actionability_contract_v0",
        "status": status,
        "raw_presence_count": _int_value(workspace_pressure.get("primary_count")),
        "owner_routed": owner_routed,
        "lifecycle_route": "runtime_artifact_lifecycle" if owner_routed else None,
        "cleanup_eligible_count": cleanup_eligible_count,
        "apply_available": apply_available,
        "deletion_authorized": False,
        "blocks_transaction": blocks_transaction,
        "blocks_closeout": blocks_closeout,
        "next_safe_action": next_safe_action,
    }


def _convergence_status_for_repair_packet(
    convergence: Mapping[str, Any],
    reconcile: Mapping[str, Any],
    shared_index: Mapping[str, Any],
) -> str:
    next_action = str(convergence.get("next_action") or "").strip()
    summary = convergence.get("summary") if isinstance(convergence.get("summary"), Mapping) else {}
    delegated_to_shared_index = (
        next_action == "staged_index_quarantine_required"
        and str(shared_index.get("next_action") or "").strip() == next_action
        and not _int_value(summary.get("open_current_finalizers"))
        and not _int_value(summary.get("landed_without_task_ledger_receipt"))
        and not _int_value(summary.get("stale_work_ledger_sessions"))
        and not bool(summary.get("advisory_begin_required"))
    )
    if delegated_to_shared_index:
        return "clear"
    return _repair_packet_status(convergence, reconcile)


def _agent_repair_packet(
    *,
    subject_id: str,
    consumer_surface: str | None,
    convergence: Mapping[str, Any],
    reconcile: Mapping[str, Any],
    autonomous_edit_gate: Mapping[str, Any],
    shared_index: Mapping[str, Any],
    workspace_pressure: Mapping[str, Any],
    runtime_artifact_lifecycle: Mapping[str, Any],
    push_gate: Mapping[str, Any],
    git_command_diagnostics: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    publication_recovery = (
        push_gate.get("publication_recovery")
        if isinstance(push_gate.get("publication_recovery"), Mapping)
        else {}
    )
    push_gate_safe_next = _preflight_drilldown_command(subject_id, "--github-push-bloat-gate")
    if (
        str(push_gate.get("status") or "") == "blocked"
        and str(publication_recovery.get("safe_next_command") or "").strip()
    ):
        push_gate_safe_next = str(publication_recovery.get("safe_next_command") or "").strip()
    workspace_actionability = _runtime_artifact_watch_actionability(
        workspace_pressure=workspace_pressure,
        runtime_artifact_lifecycle=runtime_artifact_lifecycle,
    )
    workspace_repair_status = str(workspace_pressure.get("status") or "clear")
    workspace_summary = str(
        workspace_pressure.get("next_action")
        or workspace_pressure.get("primary_class")
        or "workspace bloat pressure clear"
    )
    if workspace_actionability.get("status") == "nonblocking_preserve":
        workspace_repair_status = "clear"
        workspace_summary = "runtime artifacts preserved; no cleanup eligible"
    rows = [
        _repair_packet_row(
            row_id="transaction_convergence",
            owner="mission_transaction_control",
            failure_class="transaction_convergence",
            source_status=_convergence_status_for_repair_packet(
                convergence,
                reconcile,
                shared_index,
            ),
            summary=_action_text(
                reconcile.get("next_action"),
                convergence.get("next_action"),
                fallback="transaction receipts converged",
            ),
            safe_next_command=_preflight_drilldown_command(subject_id, "--reconcile-plan"),
            proof_route=_preflight_drilldown_command(subject_id, "--convergence"),
            details={
                "convergence_status": convergence.get("status"),
                "reconcile_status": reconcile.get("status"),
                "counts": reconcile.get("counts", {}),
                "delegated_authority_row": (
                    "shared_index_quarantine"
                    if str(convergence.get("next_action") or "").strip()
                    == "staged_index_quarantine_required"
                    else None
                ),
            },
        ),
        _repair_packet_row(
            row_id="shared_index_quarantine",
            owner="git_index_owner",
            failure_class="shared_index_quarantine",
            source_status=str(shared_index.get("status") or "clear"),
            summary=str(shared_index.get("next_action") or "shared index clear"),
            safe_next_command=_preflight_drilldown_command(subject_id, "--staged-index-quarantine"),
            proof_route="git diff --cached --name-only",
            details={
                "staged_path_count": shared_index.get("staged_path_count", 0),
                "unowned_staged_path_count": shared_index.get("unowned_staged_path_count", 0),
                "normal_git_commit_allowed": shared_index.get("normal_git_commit_allowed"),
                "private_index_scoped_commit_allowed": shared_index.get("private_index_scoped_commit_allowed"),
            },
        ),
        _repair_packet_row(
            row_id="workspace_bloat_pressure",
            owner=str(workspace_pressure.get("owner_hint") or "derived_state_bloat_governor"),
            failure_class="workspace_bloat_pressure",
            source_status=workspace_repair_status,
            summary=workspace_summary,
            safe_next_command=_workspace_pressure_safe_next_command(
                subject_id=subject_id,
                workspace_pressure=workspace_pressure,
            ),
            proof_route=_preflight_drilldown_command(subject_id, "--bloat-governor"),
            details={
                "primary_class": workspace_pressure.get("primary_class"),
                "primary_count": workspace_pressure.get("primary_count"),
                "blocked_classes": workspace_pressure.get("blocked_classes", []),
                "drain_or_manifest_command": workspace_pressure.get("drain_or_manifest_command"),
                "actionability": workspace_actionability,
            },
        ),
        _repair_packet_row(
            row_id="github_push_bloat_gate",
            owner="github_push_bloat_gate",
            failure_class="github_push_bloat_gate",
            source_status=str(push_gate.get("status") or "clear"),
            summary=_first_reason(
                push_gate.get("blocked_reasons") or push_gate.get("watch_reasons"),
                "push gate clear",
            ),
            safe_next_command=push_gate_safe_next,
            proof_route=_preflight_drilldown_command(subject_id, "--github-push-bloat-gate"),
            details={
                "mode": push_gate.get("mode"),
                "base_ref": push_gate.get("base_ref"),
                "workspace_dirty_is_push_gate": push_gate.get("workspace_dirty_is_push_gate"),
                "blocked_reasons": push_gate.get("blocked_reasons", []),
                "watch_reasons": push_gate.get("watch_reasons", []),
                "publication_recovery": publication_recovery,
            },
        ),
    ]
    if autonomous_edit_gate:
        rows.append(
            _repair_packet_row(
                row_id="autonomous_edit_gate",
                owner="mission_transaction_control",
                failure_class="autonomous_edit_gate",
                source_status=str(autonomous_edit_gate.get("status") or "clear"),
                summary=str(
                    autonomous_edit_gate.get("next_action")
                    or autonomous_edit_gate.get("required_mode")
                    or "autonomous edit gate clear"
                ),
                safe_next_command=_preflight_drilldown_command(subject_id, "--autonomous-edit-gate"),
                proof_route=_preflight_drilldown_command(subject_id, "--autonomous-edit-gate"),
                details={
                    "required_mode": autonomous_edit_gate.get("required_mode"),
                    "failed_checks": autonomous_edit_gate.get("failed_checks", []),
                    "checks": autonomous_edit_gate.get("checks", {}),
                    "dirty_tree_policy": autonomous_edit_gate.get("dirty_tree_policy", {}),
                    "autonomous_feature_mutation_allowed": autonomous_edit_gate.get(
                        "autonomous_feature_mutation_allowed"
                    ),
                },
            )
        )
    timeout_diagnostics = [
        row
        for row in git_command_diagnostics
        if isinstance(row, Mapping) and str(row.get("status") or "") == "timeout"
    ]
    if timeout_diagnostics:
        first_timeout = timeout_diagnostics[0]
        rows.append(
            _repair_packet_row(
                row_id="git_command_timeout",
                owner="mission_transaction_preflight",
                failure_class="git_command_timeout",
                source_status="blocked",
                summary=str(first_timeout.get("purpose") or "git command timeout"),
                safe_next_command="inspect mission_transaction_preflight Git child process and rerun after resolving timeout",
                proof_route="ps -axo pid,ppid,stat,etime,command | rg 'mission_transaction_preflight|git status|git rev-parse'",
                details={
                    "timeout_count": len(timeout_diagnostics),
                    "diagnostics": [dict(row) for row in timeout_diagnostics],
                },
            )
        )
    actionable = [row for row in rows if row["status"] != "clear"]
    return {
        "schema": "agent_repair_packet_v0",
        "consumer_surface": consumer_surface,
        "status": _repair_packet_status(*rows),
        "row_count": len(rows),
        "actionable_count": len(actionable),
        "rows": rows,
        "selection_rule": "bounded typed repair rows only; open proof_route for raw detail",
    }


def _first_actionable_repair_row(agent_repair_packet: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for row in agent_repair_packet.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        if _risk_band(row.get("status")) != "clear":
            return row
    return None


def _control_summary_next_action(
    *,
    convergence: Mapping[str, Any],
    reconcile: Mapping[str, Any],
    agent_repair_packet: Mapping[str, Any],
) -> str:
    reconcile_next_action = str(reconcile.get("next_action") or "").strip()
    if reconcile_next_action and reconcile_next_action != "none":
        return reconcile_next_action
    convergence_next_action = str(convergence.get("next_action") or "").strip()
    if convergence_next_action and convergence_next_action != "safe_to_continue_sibling_agents":
        return convergence_next_action
    repair_row = _first_actionable_repair_row(agent_repair_packet)
    if repair_row is not None:
        return str(repair_row.get("safe_next_command") or repair_row.get("summary") or "inspect_repair_packet")
    return convergence_next_action or "safe_to_continue_sibling_agents"


def mission_transaction_control_summary(
    packet: Mapping[str, Any],
    *,
    consumer_surface: str | None = None,
) -> dict[str, Any]:
    """Return the compact control-plane row safe for entry, phase, and HUD surfaces."""
    convergence = (
        packet.get("transaction_convergence")
        if isinstance(packet.get("transaction_convergence"), Mapping)
        else {}
    )
    reconcile = (
        packet.get("transaction_convergence_reconcile")
        if isinstance(packet.get("transaction_convergence_reconcile"), Mapping)
        else {}
    )
    closeout_settlement = (
        packet.get("transaction_closeout_settlement")
        if isinstance(packet.get("transaction_closeout_settlement"), Mapping)
        else {}
    )
    shared_index = (
        packet.get("shared_index_quarantine")
        if isinstance(packet.get("shared_index_quarantine"), Mapping)
        else {}
    )
    governor = (
        packet.get("derived_state_bloat_governor")
        if isinstance(packet.get("derived_state_bloat_governor"), Mapping)
        else {}
    )
    workspace_pressure = (
        governor.get("workspace_bloat_pressure")
        if isinstance(governor.get("workspace_bloat_pressure"), Mapping)
        else {}
    )
    push_gate = (
        governor.get("github_push_bloat_gate")
        if isinstance(governor.get("github_push_bloat_gate"), Mapping)
        else {}
    )
    runtime_artifact_lifecycle = (
        packet.get("runtime_artifact_lifecycle")
        if isinstance(packet.get("runtime_artifact_lifecycle"), Mapping)
        else {}
    )
    autonomous_edit_gate = (
        packet.get("autonomous_edit_gate")
        if isinstance(packet.get("autonomous_edit_gate"), Mapping)
        else {}
    )
    workspace_actionability = _runtime_artifact_watch_actionability(
        workspace_pressure=workspace_pressure,
        runtime_artifact_lifecycle=runtime_artifact_lifecycle,
    )
    git = packet.get("git") if isinstance(packet.get("git"), Mapping) else {}
    git_command_diagnostics = [
        row
        for row in git.get("command_diagnostics") or []
        if isinstance(row, Mapping)
    ]
    rollup = (
        convergence.get("subphase_rollup")
        if isinstance(convergence.get("subphase_rollup"), Mapping)
        else {}
    )
    rollup_row = dict(rollup)
    if consumer_surface == "kernel.phase" and rollup_row:
        rollup_row["phase_packet_consumes_rollup"] = True
        rollup_row["rollup_home"] = "kernel.phase.transaction_control_plane"
    workitem_rollup = (
        _workitem_child_transaction_rollup(rollup=rollup_row, packet=packet)
        if rollup_row
        else {}
    )
    subject_id = _control_summary_subject_id(packet)
    agent_repair_packet = _agent_repair_packet(
        subject_id=subject_id,
        consumer_surface=consumer_surface,
        convergence=convergence,
        reconcile=reconcile,
        autonomous_edit_gate=autonomous_edit_gate,
        shared_index=shared_index,
        workspace_pressure=workspace_pressure,
        runtime_artifact_lifecycle=runtime_artifact_lifecycle,
        push_gate=push_gate,
        git_command_diagnostics=git_command_diagnostics,
    )
    next_action = _control_summary_next_action(
        convergence=convergence,
        reconcile=reconcile,
        agent_repair_packet=agent_repair_packet,
    )
    return {
        "schema": "transaction_control_plane_summary_v0",
        "consumer_surface": consumer_surface,
        "status": _repair_packet_status(convergence, reconcile, agent_repair_packet),
        "next_action": next_action,
        "agent_repair_packet": agent_repair_packet,
        "transaction_convergence": {
            "schema": convergence.get("schema"),
            "status": convergence.get("status"),
            "next_action": convergence.get("next_action"),
            "summary": convergence.get("summary", {}),
        },
        "transaction_convergence_reconcile": {
            "schema": reconcile.get("schema"),
            "status": reconcile.get("status"),
            "next_action": reconcile.get("next_action"),
            "counts": reconcile.get("counts", {}),
        },
        "transaction_closeout_settlement": {
            "schema": closeout_settlement.get("schema"),
            "status": closeout_settlement.get("status"),
            "projection_settlement_status": closeout_settlement.get("projection_settlement_status"),
            "eventful_finalizers_pending": closeout_settlement.get("eventful_finalizers_pending", []),
            "required_next_command": closeout_settlement.get("required_next_command"),
            "eventful_closeout_allowed_after_settlement": closeout_settlement.get(
                "eventful_closeout_allowed_after_settlement"
            ),
        } if closeout_settlement else {},
        "autonomous_edit_gate": {
            "schema": autonomous_edit_gate.get("schema"),
            "status": autonomous_edit_gate.get("status"),
            "required_mode": autonomous_edit_gate.get("required_mode"),
            "next_action": autonomous_edit_gate.get("next_action"),
            "autonomous_feature_mutation_allowed": autonomous_edit_gate.get(
                "autonomous_feature_mutation_allowed"
            ),
            "checks": autonomous_edit_gate.get("checks", {}),
            "failed_checks": autonomous_edit_gate.get("failed_checks", []),
            "dirty_tree_policy": autonomous_edit_gate.get("dirty_tree_policy", {}),
            "patch_bundle_mode": autonomous_edit_gate.get("patch_bundle_mode", {}),
            "reconciliation_mode": autonomous_edit_gate.get("reconciliation_mode", {}),
            "closeout_vocabulary": autonomous_edit_gate.get("closeout_vocabulary", {}),
        } if autonomous_edit_gate else {},
        "shared_index_quarantine": {
            "schema": shared_index.get("schema"),
            "status": shared_index.get("status"),
            "next_action": shared_index.get("next_action"),
            "staged_path_count": shared_index.get("staged_path_count", 0),
            "unowned_staged_path_count": shared_index.get("unowned_staged_path_count", 0),
            "stale_reverse_index_entry_count": shared_index.get("stale_reverse_index_entry_count", 0),
            "stale_reverse_paths_preview": shared_index.get("stale_reverse_paths_preview", []),
            "index_entry_state_scan_truncated": shared_index.get("index_entry_state_scan_truncated"),
            "normal_git_commit_allowed": shared_index.get("normal_git_commit_allowed"),
            "shared_index_normal_commit_blocked": shared_index.get("shared_index_normal_commit_blocked"),
            "private_index_scoped_commit_allowed": shared_index.get("private_index_scoped_commit_allowed"),
        },
        "workspace_bloat_pressure": {
            "schema": workspace_pressure.get("schema"),
            "status": workspace_pressure.get("status"),
            "primary_class": workspace_pressure.get("primary_class"),
            "primary_count": workspace_pressure.get("primary_count"),
            "next_action": workspace_pressure.get("next_action"),
            "actionability_status": workspace_actionability.get("status"),
            "owner_routed": workspace_actionability.get("owner_routed"),
            "cleanup_eligible_count": workspace_actionability.get("cleanup_eligible_count"),
            "apply_available": workspace_actionability.get("apply_available"),
            "blocks_transaction": workspace_actionability.get("blocks_transaction"),
            "blocks_closeout": workspace_actionability.get("blocks_closeout"),
            "next_safe_action": workspace_actionability.get("next_safe_action"),
        },
        "runtime_artifact_lifecycle": {
            "schema": runtime_artifact_lifecycle.get("schema"),
            "status": runtime_artifact_lifecycle.get("status"),
            "artifact_root_count": runtime_artifact_lifecycle.get("artifact_root_count", 0),
            "dirty_path_count": runtime_artifact_lifecycle.get("dirty_path_count", 0),
            "cleanup_eligible_count": runtime_artifact_lifecycle.get("cleanup_eligible_count", 0),
            "apply_available": runtime_artifact_lifecycle.get("apply_available"),
            "dry_run_command": runtime_artifact_lifecycle.get("dry_run_command"),
        } if runtime_artifact_lifecycle else {},
        "github_push_bloat_gate": {
            "schema": push_gate.get("schema"),
            "status": push_gate.get("status"),
            "mode": push_gate.get("mode"),
            "base_ref": push_gate.get("base_ref"),
            "push_range": push_gate.get("push_range"),
            "workspace_dirty_is_push_gate": push_gate.get("workspace_dirty_is_push_gate"),
            "blocked_reasons": push_gate.get("blocked_reasons", []),
            "watch_reasons": push_gate.get("watch_reasons", []),
            "publication_recovery": push_gate.get("publication_recovery", {}),
        },
        "git_command_diagnostics": git_command_diagnostics,
        "workitem_child_transaction_rollup": workitem_rollup,
        "subphase_child_transaction_rollup": rollup_row,
        "drilldown_commands": [
            _preflight_drilldown_command(subject_id, "--control-summary"),
            _preflight_drilldown_command(subject_id, "--reconcile-plan"),
            _preflight_drilldown_command(subject_id, "--autonomous-edit-gate"),
            _preflight_drilldown_command(subject_id, "--staged-index-quarantine"),
            _preflight_drilldown_command(subject_id, "--runtime-artifact-lifecycle"),
            _preflight_drilldown_command(subject_id, "--github-push-bloat-gate"),
        ],
    }


def _monitor_card(
    *,
    card_id: str,
    label: str,
    status: str,
    count: int,
    summary: str,
    authority: str,
    drilldown: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    band = _risk_band(status)
    return {
        "card_id": card_id,
        "label": label,
        "status": band,
        "risk_band": band,
        "count": int(count),
        "summary": summary,
        "authority": authority,
        "drilldown": drilldown,
        "details": dict(details or {}),
    }


def _build_monitor_cards(
    *,
    staged_paths: Sequence[str],
    dirty_paths: Sequence[str],
    dirty_tree: Mapping[str, Any],
    shared_index_quarantine: Mapping[str, Any],
    coverage_gaps: Sequence[Mapping[str, Any]],
    work_ledger: Mapping[str, Any],
    scoped_commit: Mapping[str, Any],
    landing_decision: Mapping[str, Any],
) -> list[dict[str, Any]]:
    work_counts = work_ledger.get("counts") if isinstance(work_ledger.get("counts"), Mapping) else {}
    staged_count = len(staged_paths)
    dirty_count = len(dirty_paths)
    coverage_gap_count = len(coverage_gaps)
    claim_collision_count = _int_value(work_ledger.get("collision_count"))
    effective_sessions = _int_value(work_counts.get("effective_active_sessions"))
    other_active_claims = (
        _int_value(work_counts.get("other_active_claims"))
        if "other_active_claims" in work_counts
        else _int_value(work_counts.get("active_claims"))
    )
    orphaned_active_sessions = _int_value(work_counts.get("orphaned_active_sessions"))
    stale_sessions = _int_value(work_counts.get("stale_sessions"))

    index_status = "clear"
    index_summary = "staged index is clean"
    if staged_count:
        index_status = "review"
        index_summary = f"{staged_count} staged paths require full-index review before landing"
    if (
        staged_count
        and _int_value(shared_index_quarantine.get("unowned_staged_path_count"))
        and shared_index_quarantine.get("private_index_scoped_commit_allowed")
    ):
        index_status = "watch"
        index_summary = (
            f"{staged_count} staged paths block normal commits; private-index scoped commits remain allowed for non-overlap"
        )
    if (
        landing_decision.get("status") == "hard_stop"
        and landing_decision.get("reason") == "unowned_staged_index_paths"
    ):
        index_status = "hard_stop"
        index_summary = f"{staged_count} staged paths include unowned index entries"

    change_status = "watch" if dirty_count else "clear"
    change_summary = (
        f"{dirty_count} changed paths in git status; use scoped landing for owned paths"
        if dirty_count
        else "git status has no changed paths"
    )
    staged_quarantine_explains_hard_gates = _staged_quarantine_explains_dirty_hard_gates(
        staged_count=staged_count,
        dirty_tree=dirty_tree,
        shared_index_quarantine=shared_index_quarantine,
    )
    dirty_tree_status = "blocked" if dirty_tree.get("status") == "blocked" else change_status
    if dirty_tree_status == "blocked" and staged_quarantine_explains_hard_gates:
        dirty_tree_status = "watch"
    dirty_tree_summary = (
        f"{dirty_tree.get('dirty_path_count', dirty_count)} dirty paths classified; "
        f"{dirty_tree.get('hard_unowned_count', 0)} unowned hard, "
        f"{dirty_tree.get('hard_gate_count', 0)} hard gates"
    )

    work_status = _risk_band(work_ledger.get("status") or "clear")
    if work_status == "clear" and (effective_sessions or other_active_claims):
        work_status = "watch"
    staged_only_claim_pressure = (
        landing_decision.get("staged_index_claim_pressure")
        if isinstance(landing_decision.get("staged_index_claim_pressure"), Mapping)
        else {}
    )
    if (
        work_status == "blocked"
        and staged_only_claim_pressure
        and landing_decision.get("reason") == "shared_index_normal_commit_blocked_private_index_allowed"
        and shared_index_quarantine.get("private_index_scoped_commit_allowed")
    ):
        work_status = "review"
    work_summary = (
        f"{effective_sessions} effective active sessions, "
        f"{other_active_claims} other active claims, "
        f"{claim_collision_count} collisions"
    )

    generated_status = "watch" if coverage_gap_count else "clear"
    generated_summary = (
        f"{coverage_gap_count} generated-like paths need owner classification"
        if coverage_gap_count
        else "no generated ownership gaps among classified paths"
    )

    git_metadata_write = _git_metadata_write_payload(scoped_commit)
    git_metadata_status = str(git_metadata_write.get("status") or "unknown")
    git_metadata_failure = str(git_metadata_write.get("failure_class") or "")
    if _git_metadata_writable(scoped_commit):
        git_metadata_card_status = "clear"
        git_metadata_summary = "git metadata writes available for scoped commits"
    else:
        git_metadata_card_status = "blocked"
        git_metadata_summary = f"git metadata writes blocked: {git_metadata_failure or git_metadata_status}"

    landing_status = _risk_band(landing_decision.get("status") or "clear")
    if (
        landing_status == "clear"
        and not (scoped_commit.get("private_index") and scoped_commit.get("head_cas"))
    ):
        landing_status = "review"
    lane = str(landing_decision.get("recommended_lane") or "unknown")
    landing_summary = f"{lane}: {landing_decision.get('reason') or 'no_reason'}"

    return [
        _monitor_card(
            card_id="staged_index",
            label="Full Staged Index",
            status=index_status,
            count=staged_count,
            summary=index_summary,
            authority="git_index",
            drilldown="git diff --cached --name-only",
            details=_path_preview(staged_paths),
        ),
        _monitor_card(
            card_id="shared_index_quarantine",
            label="Shared Index Quarantine",
            status=str(shared_index_quarantine.get("status") or "clear"),
            count=_int_value(shared_index_quarantine.get("unowned_staged_path_count")),
            summary=str(shared_index_quarantine.get("recommended_action") or "staged index clean"),
            authority=SHARED_INDEX_QUARANTINE_SCHEMA,
            drilldown="git diff --cached --name-only",
            details={
                "normal_git_commit_allowed": shared_index_quarantine.get("normal_git_commit_allowed"),
                "shared_index_normal_commit_blocked": shared_index_quarantine.get("shared_index_normal_commit_blocked"),
                "private_index_scoped_commit_allowed": shared_index_quarantine.get("private_index_scoped_commit_allowed"),
                "git_metadata_write_status": shared_index_quarantine.get("git_metadata_write_status"),
                "git_metadata_write_failure_class": shared_index_quarantine.get("git_metadata_write_failure_class"),
                "overlap_count": shared_index_quarantine.get("overlap_count", 0),
                "stale_reverse_index_entry_count": shared_index_quarantine.get("stale_reverse_index_entry_count", 0),
                "stale_reverse_paths_preview": shared_index_quarantine.get("stale_reverse_paths_preview", []),
                "index_entry_state_scan_truncated": shared_index_quarantine.get("index_entry_state_scan_truncated"),
                "paths_preview": shared_index_quarantine.get("paths_preview", []),
            },
        ),
        _monitor_card(
            card_id="git_status_paths",
            label="Git Status Paths",
            status=change_status,
            count=dirty_count,
            summary=change_summary,
            authority="git_status",
            drilldown="git status --short",
            details=_path_preview(dirty_paths),
        ),
        _monitor_card(
            card_id="dirty_tree_classification",
            label="Dirty Tree Classification",
            status=dirty_tree_status,
            count=_int_value(dirty_tree.get("hard_unowned_count")),
            summary=dirty_tree_summary,
            authority=DIRTY_TREE_CLASSIFICATION_SCHEMA,
            drilldown="./repo-python tools/meta/control/mission_transaction_preflight.py --full <same args>",
            details={
                "by_class": dirty_tree.get("by_class", {}),
                "by_severity": dirty_tree.get("by_severity", {}),
                "hard_unowned_paths_preview": dirty_tree.get("hard_unowned_paths_preview", []),
            },
        ),
        _monitor_card(
            card_id="work_ledger_claims",
            label="Work Ledger Claims",
            status=work_status,
            count=other_active_claims,
            summary=work_summary,
            authority="work_ledger_runtime",
            drilldown="./repo-python tools/meta/factory/work_ledger.py session-status --overview",
            details={
                "effective_active_sessions": effective_sessions,
                "other_active_claims": other_active_claims,
                "orphaned_active_sessions": orphaned_active_sessions,
                "stale_sessions": stale_sessions,
                "collision_count": claim_collision_count,
            },
        ),
        _monitor_card(
            card_id="generated_ownership",
            label="Generated Ownership",
            status=generated_status,
            count=coverage_gap_count,
            summary=generated_summary,
            authority="generated_projection_registry",
            drilldown="./repo-python tools/meta/control/mission_transaction_preflight.py --owned-path <path>",
            details=_path_preview([row.get("path") for row in coverage_gaps]),
        ),
        _monitor_card(
            card_id="git_metadata_write",
            label="Git Metadata Write",
            status=git_metadata_card_status,
            count=0 if git_metadata_card_status == "clear" else 1,
            summary=git_metadata_summary,
            authority="git_metadata_history_authority",
            drilldown="./repo-python tools/meta/control/git_state_snapshot.py --path-limit 40 --recent-limit 3",
            details={
                "status": git_metadata_status,
                "writable": bool(git_metadata_write.get("writable", True)),
                "failure_class": git_metadata_failure,
                "owner_repair_commands": git_metadata_write.get("owner_repair_commands") or [],
                "worktree_write_probe_status": (
                    git_metadata_write.get("worktree_write_probe", {}).get("status")
                    if isinstance(git_metadata_write.get("worktree_write_probe"), Mapping)
                    else None
                ),
            },
        ),
        _monitor_card(
            card_id="landing_lane",
            label="Recommended Landing Lane",
            status=landing_status,
            count=0 if landing_status == "clear" else 1,
            summary=landing_summary,
            authority="mission_transaction_landing_decision",
            drilldown="./repo-python tools/meta/control/scoped_commit.py full-paths --help",
            details=dict(landing_decision),
        ),
    ]


def _monitor_summary(
    monitor_cards: Sequence[Mapping[str, Any]],
    landing_decision: Mapping[str, Any],
) -> dict[str, Any]:
    band_counts = {band: 0 for band in RISK_BANDS}
    highest_band = "clear"
    for card in monitor_cards:
        band = _risk_band(card.get("risk_band") or card.get("status"))
        band_counts[band] += 1
        if RISK_BAND_SEVERITY[band] > RISK_BAND_SEVERITY[highest_band]:
            highest_band = band
    return {
        "status": landing_decision.get("status"),
        "highest_risk_band": highest_band,
        "risk_band_counts": band_counts,
        "recommended_landing_lane": landing_decision.get("recommended_lane"),
        "reason": landing_decision.get("reason"),
        "card_count": len(monitor_cards),
    }


def _mission_transaction_card(
    *,
    target_ids: Sequence[str],
    declared_paths: Sequence[str],
    write_profiles: Sequence[str],
    staged_paths: Sequence[str],
    dirty_paths: Sequence[str],
    coverage_gaps: Sequence[Mapping[str, Any]],
    work_ledger: Mapping[str, Any],
    scoped_commit: Mapping[str, Any],
    landing_decision: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "target_ids": list(target_ids),
        "declared_owned_paths": list(declared_paths),
        "write_profiles": list(write_profiles),
        "staged_path_count": len(staged_paths),
        "dirty_path_count": len(dirty_paths),
        "coverage_gap_count": len(coverage_gaps),
        "coverage_gap_paths": [row.get("path") for row in coverage_gaps],
        "work_ledger_status": work_ledger.get("status"),
        "work_ledger_counts": work_ledger.get("counts", {}),
        "claim_collision_count": work_ledger.get("collision_count", 0),
        "scoped_commit_private_index": bool(scoped_commit.get("private_index")),
        "scoped_commit_head_cas": bool(scoped_commit.get("head_cas")),
        "landing_decision": dict(landing_decision),
    }


def _claim_mode_for_path(path: str, classification: Mapping[str, Any], *, require_exclusive: bool) -> str:
    token = str(path or "").strip("/")
    generation_class = str(classification.get("generation_class") or "")
    if require_exclusive:
        return "required_exclusive"
    if generation_class in {
        "registered_generated_projection",
        "work_ledger_write_profile_surface",
        "read_projection",
        "source_authority_append_log",
    }:
        return "required_exclusive"
    if any(path_scope_overlaps(token, prefix) or path_scope_overlaps(prefix, token) for prefix in GOVERNANCE_PREFIXES):
        return "required_exclusive"
    return "required"


def _generated_projection_fingerprints(classifications: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in classifications:
        generation_class = str(row.get("generation_class") or "")
        if generation_class in {"source_or_unclassified", "runtime_run_artifact"}:
            continue
        owners = [
            {
                "owner_id": owner.get("owner_id"),
                "source_authorities": list(owner.get("source_authorities") or []),
                "check_command": owner.get("check_command"),
                "repair_command": owner.get("repair_command"),
                "manual_edit_boundary": owner.get("manual_edit_boundary"),
                "deterministic_regeneration_expectation": owner.get(
                    "deterministic_regeneration_expectation"
                ),
                "stale_drift_handling": owner.get("stale_drift_handling"),
            }
            for owner in row.get("generated_projection_owners") or []
            if isinstance(owner, Mapping)
        ]
        source_authorities = sorted(
            {
                str(authority)
                for owner in owners
                for authority in owner.get("source_authorities") or []
                if str(authority).strip()
            }
        )
        profiles = [
            {
                "profile": profile.get("profile"),
                "path_count": len(profile.get("paths") or []),
            }
            for profile in row.get("work_ledger_write_profiles") or []
            if isinstance(profile, Mapping)
        ]
        rows.append(
            {
                "path": row.get("path"),
                "generation_class": generation_class,
                "source_authority": row.get("source_authority"),
                "source_authorities": source_authorities,
                "owner_ids": [owner.get("owner_id") for owner in owners],
                "write_profiles": [profile.get("profile") for profile in profiles],
                "freshness": "check_command_required_before_landing",
                "severity": "hard_gate" if row.get("coverage_gap") else "watch",
                "manual_edit_boundary": sorted(
                    {
                        str(owner.get("manual_edit_boundary") or "")
                        for owner in owners
                        if str(owner.get("manual_edit_boundary") or "").strip()
                    }
                ),
                "deterministic_regeneration_expectation": sorted(
                    {
                        str(owner.get("deterministic_regeneration_expectation") or "")
                        for owner in owners
                        if str(owner.get("deterministic_regeneration_expectation") or "").strip()
                    }
                ),
                "stale_drift_handling": sorted(
                    {
                        str(owner.get("stale_drift_handling") or "")
                        for owner in owners
                        if str(owner.get("stale_drift_handling") or "").strip()
                    }
                ),
                "owners": owners,
            }
        )
    return rows


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _subphase_binding(
    repo_root: Path,
    *,
    target_ids: Sequence[str],
    declared_paths: Sequence[str],
    work_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    session = work_ledger.get("session") if isinstance(work_ledger.get("session"), Mapping) else {}
    phase_id = str(session.get("phase_id") or "").strip()
    family_id = str(session.get("family_id") or "").strip()
    try:
        context = autonomy_subphase.resolve_autonomy_subphase_context(
            repo_root,
            parameters={"phase_id": phase_id} if phase_id else None,
            family=family_id or None,
        )
    except Exception:
        context = {"source": "unresolved", "subphase_id": phase_id or "unbound"}
    synth_path = str(context.get("synth_seed_path") or "").strip()
    synth_payload = _load_json_object(repo_root / synth_path) if synth_path else {}
    current_wave = synth_payload.get("current_wave") if isinstance(synth_payload.get("current_wave"), Mapping) else {}
    subject = next((str(item) for item in target_ids if str(item).strip()), "")
    local_lane_source = subject or next((str(path) for path in declared_paths if str(path).strip()), "")
    return {
        "schema": SUBPHASE_BINDING_SCHEMA,
        "parent_phase": context.get("subphase_id") or phase_id or "unbound",
        "parent_phase_dir": context.get("subphase_dir"),
        "parent_wave": current_wave.get("wave_id"),
        "parent_wave_mode": current_wave.get("mode"),
        "parent_wave_stage_kind": current_wave.get("stage_kind"),
        "local_lane": _slug_token(local_lane_source, fallback="unscoped_transaction", limit=64),
        "relation": "child_transaction",
        "requires_child_phase": False,
        "authority_boundary": "local_patch_under_global_concurrency_hardening",
        "binding_source": context.get("source"),
    }


def _work_item_binding(
    *,
    target_ids: Sequence[str],
    declared_paths: Sequence[str],
    subphase_binding: Mapping[str, Any],
) -> dict[str, Any]:
    subject = next((str(item).strip() for item in target_ids if str(item).strip()), "")
    local_lane_source = subject or next((str(path).strip() for path in declared_paths if str(path).strip()), "")
    return {
        "schema": WORK_ITEM_BINDING_SCHEMA,
        "subject_id": subject or None,
        "subject_kind": _target_claim_scope_kind(subject) if subject else "unscoped",
        "declared_path_count": len([path for path in declared_paths if str(path).strip()]),
        "local_lane": _slug_token(local_lane_source, fallback="unscoped_transaction", limit=64),
        "relation": "child_transaction",
        "requires_child_phase": False,
        "authority_boundary": "work_item_event_ledger_first",
        "receipt_authority": TASK_LEDGER_EVENTS,
        "runtime_claim_authority": "Work Ledger",
        "compat_phase_context": {
            "schema": subphase_binding.get("schema"),
            "parent_phase": subphase_binding.get("parent_phase"),
            "parent_phase_dir": subphase_binding.get("parent_phase_dir"),
            "parent_wave": subphase_binding.get("parent_wave"),
            "parent_wave_mode": subphase_binding.get("parent_wave_mode"),
            "binding_source": subphase_binding.get("binding_source"),
            "compatibility_only": True,
        },
    }


def _transaction_finalizers(
    *,
    claim_requirements: Mapping[str, Any],
    staged_paths: Sequence[str],
    shared_index_quarantine: Mapping[str, Any],
    freshness_gates: Mapping[str, Any],
    work_ledger: Mapping[str, Any],
    transaction_id: str,
) -> dict[str, Any]:
    session_id = str(work_ledger.get("session_id") or "").strip()
    claim_status = str(claim_requirements.get("status") or "")
    work_ledger_status = "not_required"
    if claim_requirements.get("claim_required") and not session_id:
        work_ledger_status = "blocked_missing_session"
    elif claim_requirements.get("claim_required") and claim_status != "satisfied":
        work_ledger_status = "pending_claim_satisfaction"
    elif session_id:
        work_ledger_status = "pending_closeout_or_append_exempt"
    receipt_command = (
        "./repo-python tools/meta/factory/task_ledger_apply.py record-execution-receipt "
        "--subject-id <subject_id> "
        f"--transaction-id {transaction_id} "
        "--commit-hash <commit_hash> --rebuild"
    )
    staged_index_status = "satisfied"
    staged_index_reason = "index_empty"
    if staged_paths:
        if (
            shared_index_quarantine.get("private_index_scoped_commit_allowed")
            and not _int_value(shared_index_quarantine.get("overlap_count"))
        ):
            staged_index_status = "ambient_pressure"
            staged_index_reason = "unrelated_staged_paths_do_not_block_private_index_scoped_commit"
        else:
            staged_index_status = "blocked"
            staged_index_reason = "staged_index_blocks_private_scoped_commit"
    return {
        "schema": "transaction_finalizers_v0",
        "work_ledger_append_or_exempt": {
            "status": work_ledger_status,
            "session_id": session_id or None,
        },
        "task_ledger_execution_receipt": {
            "status": "pending",
            "event_type": "work_item.execution_receipt_recorded",
            "command": receipt_command,
        },
        "claims_released": {
            "status": "pending" if session_id else "not_started",
            "session_id": session_id or None,
        },
        "staged_index_empty": {
            "status": staged_index_status,
            "staged_path_count": len(staged_paths),
            "reason": staged_index_reason,
            "normal_git_commit_allowed": not staged_paths,
            "private_index_scoped_commit_allowed": bool(
                shared_index_quarantine.get("private_index_scoped_commit_allowed")
            ),
        },
        "generated_outputs_fresh": {
            "status": "satisfied" if not _int_value(freshness_gates.get("hard_gate_count")) else "blocked",
            "hard_gate_count": freshness_gates.get("hard_gate_count", 0),
        },
        "session_not_stale_or_exempt": {
            "status": "pending_finalizer" if session_id else "not_started",
            "policy": "commit_only_sessions_must_record_append_exempt_or_closeout_receipt",
        },
    }


def _transaction_id(
    *,
    target_ids: Sequence[str],
    session_id: str | None,
    base_head: str | None,
    phase_id: str | None,
) -> str:
    subject = next((str(item) for item in target_ids if str(item).strip()), "no_subject")
    session = str(session_id or "no_session")
    head = str(base_head or "nohead")[:8]
    phase = _slug_token(str(phase_id or "no_phase"), fallback="no_phase", limit=24)
    subject_short = _slug_token(subject, fallback="subject", limit=48)
    session_short = hashlib.sha256(session.encode("utf-8")).hexdigest()[:8]
    return f"mtx_{phase}_{subject_short}_{session_short}_{head}"


def _claim_requirements(
    *,
    target_ids: Sequence[str],
    declared_paths: Sequence[str],
    write_profiles: Sequence[str],
    classifications: Sequence[Mapping[str, Any]],
    work_ledger: Mapping[str, Any],
    require_exclusive: bool,
) -> dict[str, Any]:
    target_list = [str(item or "").strip() for item in target_ids if str(item or "").strip()]
    live_concurrency_target = any(item.startswith(LIVE_CONCURRENCY_CAP_PREFIX) for item in target_list)
    mutation_scope_present = bool(declared_paths or write_profiles)
    claim_required = live_concurrency_target or mutation_scope_present
    exclusive_required = bool(require_exclusive or live_concurrency_target)
    exclusive_required = exclusive_required or any(
        _claim_mode_for_path(str(row.get("path") or ""), row, require_exclusive=require_exclusive)
        == "required_exclusive"
        for row in classifications
        if str(row.get("path") or "") in set(declared_paths)
    )
    matching_claims = [
        claim
        for claim in work_ledger.get("matching_active_claims") or []
        if isinstance(claim, Mapping)
    ]
    missing_claims: list[dict[str, Any]] = []
    if live_concurrency_target:
        for target_id in target_list:
            if not any(
                str(claim.get("scope_kind") or "") in {"td_id", "work_item_id"}
                and _target_claim_scope_id(claim) == target_id
                for claim in matching_claims
            ):
                missing_claims.append(
                    {"scope_kind": _target_claim_scope_kind(target_id), "scope_id": target_id}
                )
    for path in declared_paths:
        token = str(path or "").strip("/")
        if token and not any(
            str(claim.get("scope_kind") or "") == "path"
            and (
                path_scope_overlaps(token, str(claim.get("path") or claim.get("scope_id") or "").strip("/"))
                or path_scope_overlaps(str(claim.get("path") or claim.get("scope_id") or "").strip("/"), token)
            )
            for claim in matching_claims
        ):
            missing_claims.append({"scope_kind": "path", "scope_id": token})
    if not claim_required:
        status = "not_required"
    elif work_ledger.get("status") == "blocked":
        status = "blocked"
    elif not work_ledger.get("session_id"):
        status = "required_missing_session"
    elif missing_claims:
        status = "required_missing_claim"
    else:
        status = "satisfied"
    return {
        "claim_required": claim_required,
        "exclusive_required": exclusive_required,
        "status": status,
        "reason": "ranked_live_concurrency_or_declared_mutation_scope"
        if claim_required
        else "read_only_or_unscoped_preflight",
        "matching_active_claim_count": len(matching_claims),
        "matching_claim_ids": [claim.get("claim_id") for claim in matching_claims],
        "required_claim_count": len(target_list if live_concurrency_target else []) + len(declared_paths),
        "missing_claim_count": len(missing_claims),
        "missing_claims": missing_claims,
        "live_concurrency_target": live_concurrency_target,
    }


def _transaction_candidate(
    repo_root: Path,
    *,
    target_ids: Sequence[str],
    declared_paths: Sequence[str],
    write_profiles: Sequence[str],
    status_rows: Sequence[GitStatusRow],
    staged_paths: Sequence[str],
    classifications: Sequence[Mapping[str, Any]],
    coverage_gaps: Sequence[Mapping[str, Any]],
    dirty_tree: Mapping[str, Any],
    work_ledger: Mapping[str, Any],
    shared_index_quarantine: Mapping[str, Any],
    landing_decision: Mapping[str, Any],
    generated_registry: Mapping[str, Any],
    require_exclusive: bool,
) -> dict[str, Any]:
    base_head = _current_head(repo_root)
    subject_rows = _task_ledger_subject_rows(repo_root, target_ids)
    generated_fingerprints = _generated_projection_fingerprints(
        [
            row
            for row in classifications
            if str(row.get("path") or "") in set(declared_paths) or row.get("coverage_gap")
        ]
    )
    dirty_tree_read_model = {
        "schema": dirty_tree.get("schema"),
        "status": dirty_tree.get("status"),
        "raw_status": dirty_tree.get("raw_status"),
        "scope_gate_status": dirty_tree.get("scope_gate_status"),
        "dirty_path_count": dirty_tree.get("dirty_path_count", 0),
        "hard_gate_count": dirty_tree.get("hard_gate_count", 0),
        "hard_unowned_count": dirty_tree.get("hard_unowned_count", 0),
        "private_index_scoped_commit_allowed": dirty_tree.get("private_index_scoped_commit_allowed"),
        "global_dirty_tree_blocks_scoped_work": dirty_tree.get("global_dirty_tree_blocks_scoped_work"),
        "by_class": dirty_tree.get("by_class", {}),
        "by_severity": dirty_tree.get("by_severity", {}),
    }
    read_set = {
        "base_head": base_head,
        "staged_index": {
            "state": "clean" if not staged_paths else "nonempty",
            "staged_paths": list(staged_paths),
            "cached_stat_hash": _json_digest(read_cached_stat(repo_root)),
        },
        "task_ledger_tail_hash": _task_ledger_tail_hash(repo_root),
        "work_ledger_snapshot_hash": _json_digest(work_ledger),
        "subject_card_hash": _json_digest(subject_rows),
        "owned_path_blobs": [
            _path_fingerprint(repo_root, path, status_rows)
            for path in declared_paths
        ],
        "generated_projection_fingerprints": generated_fingerprints,
        "dirty_tree_classification_hash": _json_digest(dirty_tree_read_model),
    }
    classified_by_path = {
        str(row.get("path") or ""): row
        for row in classifications
        if isinstance(row, Mapping)
    }
    write_set = {
        "repo_paths": [
            {
                "path": path,
                "ownership": classified_by_path.get(path, {}).get("generation_class", "unknown"),
                "claim_mode": _claim_mode_for_path(
                    path,
                    classified_by_path.get(path, {}),
                    require_exclusive=require_exclusive,
                ),
            }
            for path in declared_paths
        ],
        "generated_write_profiles": [
            {
                "profile": profile,
                "output_paths": list(WRITE_PROFILE_PATHS.get(profile, ())),
            }
            for profile in write_profiles
        ],
        "task_ledger_event_intents": [
            {
                "subject": target_id,
                "event_type": "work_item.execution_receipt_recorded",
            }
            for target_id in target_ids
        ],
        "work_ledger_mutations": [
            {
                "session_id": work_ledger.get("session_id"),
                "required": True,
                "kind": "claim_or_finalize",
            }
        ] if (target_ids or declared_paths) else [],
        "projection_outputs": [
            {
                "path": row.get("path"),
                "freshness_required": row.get("severity") == "hard_gate",
                "generation_class": row.get("generation_class"),
            }
            for row in generated_fingerprints
        ],
    }
    claim_requirements = _claim_requirements(
        target_ids=target_ids,
        declared_paths=declared_paths,
        write_profiles=write_profiles,
        classifications=classifications,
        work_ledger=work_ledger,
        require_exclusive=require_exclusive,
    )
    write_set_paths = set(declared_paths) | set(staged_paths)
    hard_coverage_gaps = [
        row
        for row in coverage_gaps
        if str(row.get("path") or "") in write_set_paths
    ]
    freshness_gates = {
        "status": "hard_gate" if hard_coverage_gaps else ("watch" if coverage_gaps else "clear"),
        "hard_gate_count": len(hard_coverage_gaps),
        "hard_gate_paths": [row.get("path") for row in hard_coverage_gaps],
        "watch_count": len(coverage_gaps) - len(hard_coverage_gaps),
        "watch_paths_preview": [
            row.get("path")
            for row in coverage_gaps
            if str(row.get("path") or "") not in write_set_paths
        ][:COMPACT_PREVIEW_LIMIT],
        "generated_registry_owner_count": len(generated_registry.get("owners") or []),
    }
    session = work_ledger.get("session") if isinstance(work_ledger.get("session"), Mapping) else {}
    read_set_hash = _json_digest(read_set)
    write_set_hash = _json_digest(write_set)
    status = "blocked" if landing_decision.get("status") in {"blocked", "hard_stop"} else "candidate_ready"
    if claim_requirements.get("status") in {"required_missing_session", "required_missing_claim"}:
        status = "claim_required"
    transaction_id = _transaction_id(
        target_ids=target_ids,
        session_id=str(work_ledger.get("session_id") or ""),
        base_head=base_head,
        phase_id=str(session.get("phase_id") or ""),
    )
    subphase_binding = _subphase_binding(
        repo_root,
        target_ids=target_ids,
        declared_paths=declared_paths,
        work_ledger=work_ledger,
    )
    work_item_binding = _work_item_binding(
        target_ids=target_ids,
        declared_paths=declared_paths,
        subphase_binding=subphase_binding,
    )
    finalizers = _transaction_finalizers(
        claim_requirements=claim_requirements,
        staged_paths=staged_paths,
        shared_index_quarantine=shared_index_quarantine,
        freshness_gates=freshness_gates,
        work_ledger=work_ledger,
        transaction_id=transaction_id,
    )
    causal_links = [
        {"kind": "observed", "surface": "git_head", "hash": base_head},
        {"kind": "observed", "surface": "task_ledger_tail", "hash": read_set.get("task_ledger_tail_hash")},
        {"kind": "observed", "surface": "work_ledger_snapshot", "hash": read_set.get("work_ledger_snapshot_hash")},
        {"kind": "classified", "surface": DIRTY_TREE_CLASSIFICATION_SCHEMA, "hash": read_set["dirty_tree_classification_hash"]},
    ]
    if work_ledger.get("session_id"):
        causal_links.append({"kind": "bound", "surface": "work_ledger_session", "id": work_ledger.get("session_id")})
    return {
        "schema": TRANSACTION_CANDIDATE_SCHEMA,
        "transaction_id": transaction_id,
        "status": status,
        "task_ledger_subjects": list(target_ids),
        "work_ledger_session_id": work_ledger.get("session_id"),
        "work_ledger_read_receipt_id": session.get("read_receipt_id"),
        "phase_id": session.get("phase_id"),
        "base_head": base_head,
        "read_set_hash": read_set_hash,
        "write_set_hash": write_set_hash,
        "read_set": read_set,
        "write_set": write_set,
        "claim_requirements": claim_requirements,
        "dirty_tree": dirty_tree_read_model,
        "freshness_gates": freshness_gates,
        "finalizers": finalizers,
        "work_item_binding": work_item_binding,
        "subphase_binding": subphase_binding,
        "causal_links": causal_links,
        "landing_lane": landing_decision.get("recommended_lane"),
        "receipt_destination": {
            "authority": TASK_LEDGER_EVENTS,
            "event_type": "work_item.execution_receipt_recorded",
        },
        "next_action": "claim_required_before_mutation"
        if status == "claim_required"
        else landing_decision.get("recommended_lane"),
    }


def _transaction_convergence(
    repo_root: Path,
    *,
    target_ids: Sequence[str],
    transaction_candidate: Mapping[str, Any],
    dirty_tree: Mapping[str, Any],
    shared_index_quarantine: Mapping[str, Any],
    derived_state_bloat_governor: Mapping[str, Any],
    staged_paths: Sequence[str],
    freshness_gates: Mapping[str, Any],
    work_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    binding = (
        transaction_candidate.get("subphase_binding")
        if isinstance(transaction_candidate.get("subphase_binding"), Mapping)
        else {}
    )
    finalizers = (
        transaction_candidate.get("finalizers")
        if isinstance(transaction_candidate.get("finalizers"), Mapping)
        else {}
    )
    phase_id = str(transaction_candidate.get("phase_id") or binding.get("parent_phase") or "").strip() or None
    runtime_status = work_ledger_runtime.load_runtime_status(repo_root)
    subject_rows = _task_ledger_subject_rows(repo_root, target_ids)
    task_receipts = _task_ledger_receipt_refs(subject_rows)
    latest_execution_receipt = (
        subject_rows[0].get("latest_execution_receipt")
        if subject_rows and isinstance(subject_rows[0], Mapping)
        else None
    )
    latest_receipt_session_state = _work_ledger_session_state_for_receipt(
        runtime_status,
        _mapping_value(latest_execution_receipt),
    )
    work_transactions = _work_ledger_transaction_rows(
        repo_root=repo_root,
        phase_id=phase_id,
        target_ids=target_ids,
    )
    closed_session_ids = _closed_work_ledger_session_ids(repo_root, phase_id)
    append_exempt_session_ids = _append_exempt_work_ledger_session_ids(
        repo_root,
        phase_id,
        target_ids,
    )
    drained_session_ids = closed_session_ids | append_exempt_session_ids
    transaction_rows: list[dict[str, Any]] = []
    missing_receipts = 0
    pending_intake_count = 0
    stale_transaction_sessions = 0
    target_fallback = _first_nonempty(target_ids)
    drilldown_subject_id = target_fallback or "cap_live_concurrency_transactional_workitems"
    for transaction in work_transactions:
        receipt_status = _receipt_status_for_transaction(transaction, task_receipts)
        session_status = _session_finalizer_status(
            transaction,
            runtime_status,
            append_exempt_session_ids=append_exempt_session_ids,
        )
        if receipt_status["status"] == "missing":
            missing_receipts += 1
            subject_id = _first_nonempty(transaction.get("task_ledger_subjects") or []) or target_fallback
            commit_hash = _first_nonempty(transaction.get("commit_refs") or [])
            transaction_id = str(transaction.get("transaction_id") or "").strip()
            if subject_id and transaction_id and commit_hash:
                key = task_ledger_events.execution_receipt_idempotency_key(
                    subject_id=str(subject_id),
                    transaction_id=transaction_id,
                    commit_hash=str(commit_hash),
                )
                intake_request = task_ledger_events.task_ledger_intake_request_for_key(repo_root, key)
                if intake_request and str(intake_request.get("_intake_status") or "") == "pending":
                    pending_intake_count += 1
        if session_status["status"] == "stale_requires_drain":
            stale_transaction_sessions += 1
        transaction_rows.append(
            {
                **transaction,
                "task_ledger_execution_receipt": receipt_status,
                "work_ledger_session_finalizer": session_status,
                "converged": (
                    receipt_status["status"] == "recorded"
                    and session_status["status"] in {"append_exempt", "closed_clean", "unknown_session"}
                    and bool(transaction.get("work_ledger_closed"))
                ),
            }
        )

    target_stale_sessions = _target_stale_sessions(
        runtime_status,
        target_ids=target_ids,
        phase_id=phase_id,
        closed_work_ledger_session_ids=drained_session_ids,
    )
    append_exempt_sessions = _target_append_exempt_sessions(
        runtime_status,
        target_ids=target_ids,
        phase_id=phase_id,
        closed_work_ledger_session_ids=drained_session_ids,
    )
    raw_current_finalizers = _open_current_finalizers(finalizers)
    current_transaction_row = {
        "transaction_id": transaction_candidate.get("transaction_id"),
        "status": transaction_candidate.get("status"),
        "open_finalizers": raw_current_finalizers,
        "finalizer_count": len(raw_current_finalizers),
        "base_head": transaction_candidate.get("base_head"),
        "read_set_hash": transaction_candidate.get("read_set_hash"),
        "write_set_hash": transaction_candidate.get("write_set_hash"),
    }
    current_execution_receipt = _receipt_for_current_transaction_or_session(
        current_transaction_row,
        task_receipts,
        session_id=str(work_ledger.get("session_id") or "").strip() or None,
        read_receipt_id=str(
            (work_ledger.get("session") or {}).get("read_receipt_id")
            if isinstance(work_ledger.get("session"), Mapping)
            else ""
        ).strip()
        or None,
    )
    current_receipt_session_state = _work_ledger_session_state_for_receipt(
        runtime_status,
        _mapping_value(current_execution_receipt),
    )
    attempt_state = _workitem_landing_attempt_state(
        target_ids=target_ids,
        query_session_id=str(work_ledger.get("session_id") or "").strip() or None,
        current_transaction=current_transaction_row,
        transaction_rows=transaction_rows,
    )
    finalizer_classes = _current_finalizer_classes(
        raw_finalizers=raw_current_finalizers,
        current_transaction=current_transaction_row,
        current_execution_receipt=current_execution_receipt,
        transaction_rows=transaction_rows,
        receipt_refs=task_receipts,
        receipt_bound_session_state=current_receipt_session_state,
        shared_index_quarantine=shared_index_quarantine,
        attempt_state=attempt_state,
    )
    canonical_state = _mapping_value(finalizer_classes.get("canonical_transaction_state"))
    canonical_transaction_id = (
        str(canonical_state.get("transaction_id") or "").strip()
        if str(canonical_state.get("state") or "") == "converged"
        else ""
    )
    canonical_row = _matching_transaction_row(transaction_rows, canonical_transaction_id)
    missing_receipts = 0
    pending_intake_count = 0
    for transaction in transaction_rows:
        if _superseded_by_canonical_convergence(
            transaction,
            canonical_transaction_id=canonical_transaction_id,
            canonical_row=canonical_row,
        ):
            continue
        receipt_status = (
            transaction.get("task_ledger_execution_receipt")
            if isinstance(transaction.get("task_ledger_execution_receipt"), Mapping)
            else {}
        )
        if receipt_status.get("status") != "missing":
            continue
        missing_receipts += 1
        subject_id = _first_nonempty(transaction.get("task_ledger_subjects") or []) or target_fallback
        commit_hash = _first_nonempty(transaction.get("commit_refs") or [])
        transaction_id = str(transaction.get("transaction_id") or "").strip()
        if subject_id and transaction_id and commit_hash:
            key = task_ledger_events.execution_receipt_idempotency_key(
                subject_id=str(subject_id),
                transaction_id=transaction_id,
                commit_hash=str(commit_hash),
            )
            intake_request = task_ledger_events.task_ledger_intake_request_for_key(repo_root, key)
            if intake_request and str(intake_request.get("_intake_status") or "") == "pending":
                pending_intake_count += 1
    open_current_finalizers = list(finalizer_classes.get("transaction_local_finalizers") or [])
    advisory_begin_required = bool(
        attempt_state.get("candidate_role") == "advisory_candidate"
        and attempt_state.get("mutation_requires_begin")
        and _transaction_candidate_has_mutation_scope(transaction_candidate)
    )
    hard_gate_count = _int_value(dirty_tree.get("hard_gate_count"))
    hard_unowned_count = _int_value(dirty_tree.get("hard_unowned_count"))
    staged_count = len(staged_paths)
    generated_hard_count = _int_value(freshness_gates.get("hard_gate_count"))
    staged_quarantine_allows_private = bool(
        staged_count
        and shared_index_quarantine.get("private_index_scoped_commit_allowed")
        and not _int_value(shared_index_quarantine.get("overlap_count"))
    )
    staged_quarantine_explains_hard_gates = _staged_quarantine_explains_dirty_hard_gates(
        staged_count=staged_count,
        dirty_tree=dirty_tree,
        shared_index_quarantine=shared_index_quarantine,
    )
    hard_gate_blocks_convergence = bool(
        generated_hard_count
        or (
            (hard_gate_count or hard_unowned_count)
            and not staged_quarantine_explains_hard_gates
        )
    )
    staged_index_blocks_private_landing = bool(staged_count and not staged_quarantine_allows_private)
    if hard_gate_blocks_convergence or staged_index_blocks_private_landing:
        status = "blocked"
    elif (
        missing_receipts
        or target_stale_sessions
        or stale_transaction_sessions
        or open_current_finalizers
        or advisory_begin_required
        or staged_quarantine_allows_private
    ):
        status = "watch"
    else:
        status = "clear"
    if missing_receipts:
        next_action = "record_task_ledger_execution_receipt"
    elif target_stale_sessions or stale_transaction_sessions:
        next_action = "drain_stale_work_ledger_sessions"
    elif open_current_finalizers:
        next_action = "complete_current_transaction_finalizers"
    elif advisory_begin_required:
        next_action = (
            "claim_required_before_mutation"
            if str(transaction_candidate.get("status") or "") == "claim_required"
            else "work_landing_begin_required"
        )
    elif staged_quarantine_allows_private:
        next_action = "staged_index_quarantine_required"
    elif status == "blocked":
        next_action = "clear_hard_landing_gates"
    else:
        next_action = "safe_to_continue_sibling_agents"
    return {
        "schema": TRANSACTION_CONVERGENCE_SCHEMA,
        "phase_id": phase_id,
        "wave_id": binding.get("parent_wave"),
        "status": status,
        "next_action": next_action,
        "authority": {
            "projection_owner": "system/lib/mission_transaction_landing_preflight.py",
            "task_ledger_authority": TASK_LEDGER_EVENTS,
            "work_ledger_authority": f"codex/ledger/{phase_id}/work_ledger.jsonl" if phase_id else None,
            "runtime_authority": str(work_ledger_runtime.RUNTIME_STATUS_REL),
        },
        "current_transaction": {
            "transaction_id": transaction_candidate.get("transaction_id"),
            "status": transaction_candidate.get("status"),
            "transaction_candidate_role": attempt_state.get("candidate_role"),
            "mutation_requires_begin": attempt_state.get("mutation_requires_begin"),
            "shadow_state": finalizer_classes.get("current_transaction_shadow_state"),
            "canonical_transaction_id": (
                (finalizer_classes.get("canonical_transaction_state") or {}).get("transaction_id")
                if isinstance(finalizer_classes.get("canonical_transaction_state"), Mapping)
                else None
            ),
            "open_finalizers": open_current_finalizers,
            "finalizer_count": len(open_current_finalizers),
            "compatibility_finalizers": finalizer_classes.get("compatibility_finalizers", []),
            "compatibility_finalizer_count": len(finalizer_classes.get("compatibility_finalizers", [])),
            "ambient_pressure": finalizer_classes.get("ambient_pressure", []),
            "base_head": transaction_candidate.get("base_head"),
            "read_set_hash": transaction_candidate.get("read_set_hash"),
            "write_set_hash": transaction_candidate.get("write_set_hash"),
        },
        "workitem_landing_attempt_state": attempt_state,
        "canonical_transaction_state": finalizer_classes.get("canonical_transaction_state"),
        "finalizer_classes": {
            "transaction_local_finalizers": open_current_finalizers,
            "ambient_pressure": finalizer_classes.get("ambient_pressure", []),
            "compatibility_finalizers": finalizer_classes.get("compatibility_finalizers", []),
        },
        "recent_transactions": transaction_rows,
        "summary": {
            "recent_transaction_count": len(transaction_rows),
            "landed_without_task_ledger_receipt": missing_receipts,
            "stale_work_ledger_sessions": len(target_stale_sessions) + stale_transaction_sessions,
            "open_current_finalizers": len(open_current_finalizers),
            "ambient_pressure_count": len(finalizer_classes.get("ambient_pressure", [])),
            "compatibility_finalizer_count": len(finalizer_classes.get("compatibility_finalizers", [])),
            "receipt_pending_in_intake": pending_intake_count,
            "advisory_begin_required": advisory_begin_required,
            "dirty_tree_hard_gates": hard_gate_count,
            "dirty_tree_hard_unowned": hard_unowned_count,
            "staged_index_paths": staged_count,
            "staged_index_quarantine_status": shared_index_quarantine.get("status"),
            "private_index_scoped_commit_allowed": shared_index_quarantine.get("private_index_scoped_commit_allowed"),
            "generated_output_hard_gates": generated_hard_count,
            "dirty_tree_total_is_gate": False,
        },
        "task_ledger_receipt_state": {
            "subject_ids": list(target_ids),
            "receipt_refs": task_receipts.get("receipt_refs", []),
            "commit_refs": task_receipts.get("commit_refs", []),
            "work_ledger_refs": task_receipts.get("work_ledger_refs", []),
            "execution_receipts": task_receipts.get("execution_receipts", []),
            "latest_execution_receipt": latest_execution_receipt,
            "latest_execution_receipt_work_ledger_session_state": latest_receipt_session_state,
        },
        "work_ledger_stale_sessions": target_stale_sessions,
        "work_ledger_append_exempt_sessions": append_exempt_sessions,
        "shared_index_quarantine": shared_index_quarantine,
        "dirty_tree_class_budgets": {
            "schema": "dirty_tree_class_budgets_v0",
            "mode": "observed_unconfigured_not_a_hard_gate",
            "total_dirty_count": dirty_tree.get("dirty_path_count", 0),
            "class_rows": _dirty_tree_class_budget_rows(dirty_tree),
            "hard_gate_count": hard_gate_count,
            "hard_unowned_count": hard_unowned_count,
        },
        "derived_state_bloat_governor": derived_state_bloat_governor,
        "subphase_rollup": {
            "schema": "subphase_child_transaction_rollup_v1",
            "phase_id": phase_id,
            "wave_id": binding.get("parent_wave"),
            "child_transaction_count": len(transaction_rows) + 1,
            "open_finalizer_count": len(open_current_finalizers) + missing_receipts + len(target_stale_sessions),
            "pending_intake_count": pending_intake_count,
            "stale_session_count": len(target_stale_sessions) + stale_transaction_sessions,
            "push_gate_status": (
                (derived_state_bloat_governor.get("github_push_bloat_gate") or {}).get("status")
                if isinstance(derived_state_bloat_governor.get("github_push_bloat_gate"), Mapping)
                else None
            ),
            "workspace_bloat_status": (
                (derived_state_bloat_governor.get("workspace_bloat_pressure") or {}).get("status")
                if isinstance(derived_state_bloat_governor.get("workspace_bloat_pressure"), Mapping)
                else None
            ),
            "staged_quarantine_status": shared_index_quarantine.get("status"),
            "private_index_scoped_commit_allowed": shared_index_quarantine.get("private_index_scoped_commit_allowed"),
            "phase_packet_consumes_rollup": False,
            "rollup_home": "mission_transaction_preflight_until_wave_assimilation",
            "drilldown_commands": [
                _preflight_drilldown_command(drilldown_subject_id, "--convergence"),
                _preflight_drilldown_command(drilldown_subject_id, "--reconcile-plan"),
                _preflight_drilldown_command(drilldown_subject_id, "--staged-index-quarantine"),
                _preflight_drilldown_command(drilldown_subject_id, "--runtime-artifact-lifecycle"),
                _preflight_drilldown_command(drilldown_subject_id, "--github-push-bloat-gate"),
            ],
        },
    }


def _first_nonempty(values: Iterable[Any]) -> str | None:
    for value in values:
        token = str(value or "").strip()
        if token:
            return token
    return None


def _receipt_command_argv(
    *,
    subject_id: str,
    transaction: Mapping[str, Any],
    command_name: str = "record-execution-receipt",
) -> list[str]:
    argv = [
        "./repo-python",
        "tools/meta/factory/task_ledger_apply.py",
        command_name,
        "--subject-id",
        subject_id,
        "--transaction-id",
        str(transaction.get("transaction_id") or ""),
    ]
    optional_fields = (
        ("--commit-hash", _first_nonempty(transaction.get("commit_refs") or [])),
        ("--work-ledger-session-id", _first_nonempty(transaction.get("actor_session_ids") or [])),
        ("--read-receipt-id", _first_nonempty(transaction.get("read_receipt_ids") or [])),
        ("--read-set-hash", transaction.get("read_set_hash")),
        ("--write-set-hash", transaction.get("write_set_hash")),
    )
    for flag, value in optional_fields:
        token = str(value or "").strip()
        if token:
            argv.extend([flag, token])
    argv.extend(
        [
            "--validation-ref",
            "transaction_convergence_reconcile_v0",
            "--projection-ref",
            "transaction_convergence_v0",
            "--projection-ref",
            "work_ledger_project_check_all",
            "--closeout-state",
            "landed",
            "--rebuild",
        ]
    )
    return argv


def _transaction_reconcile_plan(
    repo_root: Path,
    *,
    target_ids: Sequence[str],
    transaction_convergence: Mapping[str, Any],
    session_id: str | None,
    status_rows: Sequence[GitStatusRow],
) -> dict[str, Any]:
    receipt_write_set = list(TASK_LEDGER_RECEIPT_WRITE_SET)
    receipt_preflight = _work_ledger_packet(
        repo_root,
        receipt_write_set,
        target_ids=(),
        session_id=session_id,
        require_exclusive=True,
    )
    receipt_blockers = list(receipt_preflight.get("collisions") or [])
    receipt_dirty_paths = sorted(
        {
            row.path
            for row in status_rows
            for receipt_path in receipt_write_set
            if row.path == receipt_path
            or path_scope_overlaps(row.path, receipt_path)
            or path_scope_overlaps(receipt_path, row.path)
        }
    )
    actions: list[dict[str, Any]] = []
    canonical_state = _mapping_value(transaction_convergence.get("canonical_transaction_state"))
    canonical_transaction_id = (
        str(canonical_state.get("transaction_id") or "").strip()
        if str(canonical_state.get("state") or "") == "converged"
        else ""
    )
    canonical_row = None
    if canonical_transaction_id:
        for row in transaction_convergence.get("recent_transactions") or []:
            if (
                isinstance(row, Mapping)
                and str(row.get("transaction_id") or "").strip() == canonical_transaction_id
            ):
                canonical_row = row
                break
    task_receipt_state = _mapping_value(transaction_convergence.get("task_ledger_receipt_state"))
    counts = {
        "receipt_recorded": 0,
        "receipt_already_recorded": 0,
        "receipt_ready_to_record": 0,
        "receipt_pending_in_intake": 0,
        "receipt_blocked_claim_collision": 0,
        "receipt_blocked_same_file_entanglement": 0,
        "receipt_blocked_missing_fields": 0,
        "receipt_deferred_with_work_ledger_evidence": 0,
        "receipt_superseded_by_canonical_convergence": 0,
        "operator_required": 0,
    }
    target_fallback = _first_nonempty(target_ids)
    for transaction in transaction_convergence.get("recent_transactions") or []:
        if not isinstance(transaction, Mapping):
            continue
        receipt_status = (
            transaction.get("task_ledger_execution_receipt")
            if isinstance(transaction.get("task_ledger_execution_receipt"), Mapping)
            else {}
        )
        subject_id = _first_nonempty(transaction.get("task_ledger_subjects") or []) or target_fallback
        transaction_id = str(transaction.get("transaction_id") or "").strip()
        is_superseded = _superseded_by_canonical_convergence(
            transaction,
            canonical_transaction_id=canonical_transaction_id,
            canonical_row=canonical_row,
        )
        commit_hash = _first_nonempty(transaction.get("commit_refs") or [])
        recovered_commit_refs: list[str] = []
        receipt_command_transaction = transaction
        commit_hash_source = "work_ledger"
        if not commit_hash and not is_superseded:
            recovered_commit_refs = _receipt_context_commit_refs(transaction, task_receipt_state)
            commit_hash = _first_nonempty(recovered_commit_refs) or ""
            if recovered_commit_refs:
                receipt_command_transaction = {
                    **dict(transaction),
                    "commit_refs": recovered_commit_refs,
                }
                commit_hash_source = "task_ledger_receipt_context"
        missing_fields = [
            field
            for field, value in (
                ("subject_id", subject_id),
                ("transaction_id", transaction_id),
                ("commit_hash", commit_hash),
            )
            if not value
        ]
        intake_request = None
        if not missing_fields:
            key = task_ledger_events.execution_receipt_idempotency_key(
                subject_id=str(subject_id),
                transaction_id=transaction_id,
                commit_hash=str(commit_hash),
            )
            intake_request = task_ledger_events.task_ledger_intake_request_for_key(repo_root, key)
        if receipt_status.get("status") == "recorded":
            outcome = "receipt_already_recorded"
        elif intake_request and str(intake_request.get("_intake_status") or "") == "pending":
            outcome = "receipt_pending_in_intake"
        elif missing_fields:
            outcome = "receipt_blocked_missing_fields"
        elif receipt_blockers:
            outcome = "receipt_blocked_claim_collision"
        elif receipt_dirty_paths:
            outcome = "receipt_blocked_same_file_entanglement"
        elif not transaction.get("work_ledger_closed") and not recovered_commit_refs:
            outcome = "receipt_deferred_with_work_ledger_evidence"
        else:
            outcome = "receipt_ready_to_record"
        if is_superseded:
            outcome = "receipt_superseded_by_canonical_convergence"
        counts[outcome] = counts.get(outcome, 0) + 1
        action = {
            "transaction_id": transaction_id or None,
            "subject_id": subject_id,
            "commit_hash": commit_hash,
            "outcome": outcome,
            "work_ledger_closed": bool(transaction.get("work_ledger_closed")),
            "work_ledger_session_ids": list(transaction.get("actor_session_ids") or []),
            "read_receipt_ids": list(transaction.get("read_receipt_ids") or []),
            "work_ledger_event_ids": list(transaction.get("work_ledger_event_ids") or []),
            "missing_fields": missing_fields,
        }
        if commit_hash:
            action["commit_hash_source"] = commit_hash_source
        if recovered_commit_refs:
            action["recovered_commit_refs"] = recovered_commit_refs
        if outcome == "receipt_superseded_by_canonical_convergence":
            action["superseded_by_transaction_id"] = canonical_transaction_id
            action["superseded_reason"] = "canonical_converged_transaction_shares_session_or_read_receipt"
        if intake_request:
            action["intake_request"] = {
                "request_id": intake_request.get("request_id"),
                "status": intake_request.get("_intake_status"),
                "path": intake_request.get("_intake_path"),
                "idempotency_key": intake_request.get("idempotency_key"),
            }
        if outcome == "receipt_blocked_claim_collision":
            action["blocking_claims"] = receipt_blockers
            if subject_id:
                action["intake_enqueue_argv"] = _receipt_command_argv(
                    subject_id=str(subject_id),
                    transaction=receipt_command_transaction,
                    command_name="enqueue-execution-receipt",
                )
        if outcome == "receipt_blocked_same_file_entanglement":
            action["same_file_entanglement_paths"] = receipt_dirty_paths
            if subject_id:
                action["intake_enqueue_argv"] = _receipt_command_argv(
                    subject_id=str(subject_id),
                    transaction=receipt_command_transaction,
                    command_name="enqueue-execution-receipt",
                )
        if outcome == "receipt_ready_to_record" and subject_id:
            action["command_argv"] = _receipt_command_argv(
                subject_id=str(subject_id),
                transaction=receipt_command_transaction,
            )
        actions.append(action)

    if counts["receipt_blocked_missing_fields"] or counts["operator_required"]:
        status = "blocked"
        next_action = "operator_required"
    elif counts["receipt_blocked_claim_collision"]:
        status = "blocked"
        next_action = "enqueue_task_ledger_intake_request"
    elif counts["receipt_blocked_same_file_entanglement"]:
        status = "blocked"
        next_action = "enqueue_task_ledger_intake_request"
    elif counts["receipt_pending_in_intake"]:
        status = "watch"
        next_action = "drain_task_ledger_intake"
    elif counts["receipt_deferred_with_work_ledger_evidence"]:
        status = "watch"
        next_action = "complete_work_ledger_closeout_before_receipt"
    elif counts["receipt_ready_to_record"]:
        status = "ready"
        next_action = "record_task_ledger_execution_receipt"
    else:
        status = "clear"
        next_action = "none"

    return {
        "schema": TRANSACTION_CONVERGENCE_RECONCILE_SCHEMA,
        "mode": "read_only_reconcile_plan",
        "status": status,
        "next_action": next_action,
        "authority": {
            "status_source": TRANSACTION_CONVERGENCE_SCHEMA,
            "receipt_authority": TASK_LEDGER_EVENTS,
            "receipt_command": "tools/meta/factory/task_ledger_apply.py record-execution-receipt",
            "claim_authority": "state/work_ledger/runtime_status.json",
        },
        "target_ids": list(target_ids),
        "receipt_write_set": receipt_write_set,
        "receipt_write_set_preflight": {
            "status": receipt_preflight.get("status"),
            "require_exclusive": receipt_preflight.get("require_exclusive"),
            "collision_count": receipt_preflight.get("collision_count", 0),
            "blocking_claim_ids": [
                row.get("claim_id")
                for row in receipt_blockers
                if isinstance(row, Mapping) and row.get("claim_id")
            ],
            "blocking_claims": receipt_blockers,
            "same_file_entanglement_paths": receipt_dirty_paths,
        },
        "counts": counts,
        "actions": actions,
        "mutation_policy": {
            "auto_mutation_allowed": status == "ready",
            "signoff_allowed": False,
            "dirty_tree_total_is_gate": False,
        },
    }


def build_mission_transaction_landing_preflight(
    repo_root: Path,
    *,
    owned_paths: Sequence[str] = (),
    write_profiles: Sequence[str] = (),
    target_ids: Sequence[str] = (),
    session_id: str | None = None,
    require_exclusive: bool = False,
    include_push_bloat_gate: bool = True,
    include_generated_projection_settlement: bool = True,
    generated_projection_settlement_deferred_reason: str = (
        LOCAL_OWNED_PATH_SETTLEMENT_DEFERRED_REASON
    ),
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    status_rows, git_command_diagnostics = _read_git_status_rows_with_diagnostics(repo_root)
    dirty_paths = sorted({row.path for row in status_rows})
    staged_paths, staged_path_diagnostics = _read_cached_path_names_with_diagnostics(repo_root)
    cached_stat, cached_stat_diagnostics = _read_cached_stat_with_diagnostics(repo_root)
    git_command_diagnostics.extend(staged_path_diagnostics)
    git_command_diagnostics.extend(cached_stat_diagnostics)
    declared_paths = _declared_owned_paths(
        [_normalize_path(repo_root, path) for path in owned_paths],
        write_profiles,
    )
    requested_paths = sorted({*declared_paths, *staged_paths})
    classification_targets = sorted({*dirty_paths, *staged_paths, *requested_paths})
    classifications = [
        classify_path(path, owned_paths=owned_paths, write_profiles=write_profiles)
        for path in classification_targets
    ]
    coverage_gaps = [row for row in classifications if row.get("coverage_gap")]
    work_ledger = _work_ledger_packet(
        repo_root,
        requested_paths,
        target_ids=target_ids,
        session_id=session_id,
        require_exclusive=require_exclusive,
    )
    scoped_commit = _scoped_commit_capability(repo_root)
    dirty_tree = _dirty_tree_classification(
        status_rows=status_rows,
        declared_paths=declared_paths,
        classifications=classifications,
        work_ledger=work_ledger,
    )
    shared_index_quarantine = _shared_index_quarantine(
        repo_root=repo_root,
        staged_paths=staged_paths,
        status_rows=status_rows,
        declared_paths=declared_paths,
        classifications=classifications,
        work_ledger=work_ledger,
        scoped_commit=scoped_commit,
    )
    dirty_tree = _dirty_tree_with_scoped_landing_policy(
        dirty_tree,
        staged_count=len(staged_paths),
        shared_index_quarantine=shared_index_quarantine,
    )
    derived_state_bloat_governor = _derived_state_bloat_governor(
        repo_root,
        dirty_tree=dirty_tree,
        status_rows=status_rows,
        include_push_bloat_gate=include_push_bloat_gate,
    )
    runtime_artifact_lifecycle = _runtime_artifact_lifecycle(
        repo_root,
        status_rows=status_rows,
    )
    landing_decision = _landing_decision(
        staged_paths=staged_paths,
        dirty_paths=dirty_paths,
        declared_paths=declared_paths,
        classified=classifications,
        dirty_tree=dirty_tree,
        work_ledger=work_ledger,
        shared_index_quarantine=shared_index_quarantine,
        scoped_commit=scoped_commit,
    )
    autonomous_edit_gate = _autonomous_edit_gate(
        status_rows=status_rows,
        dirty_tree=dirty_tree,
        shared_index_quarantine=shared_index_quarantine,
        staged_paths=staged_paths,
        work_ledger=work_ledger,
        scoped_commit=scoped_commit,
        git_command_diagnostics=git_command_diagnostics,
    )
    generated_registry = generated_projection_registry.projection_registry_payload()
    if include_generated_projection_settlement:
        generated_projection_settlement = generated_state_drainer.build_generated_projection_settlement_plan(repo_root)
    else:
        generated_projection_settlement = _deferred_generated_projection_settlement_plan(
            reason=generated_projection_settlement_deferred_reason
            or LOCAL_OWNED_PATH_SETTLEMENT_DEFERRED_REASON,
        )
    monitor_cards = _build_monitor_cards(
        staged_paths=staged_paths,
        dirty_paths=dirty_paths,
        dirty_tree=dirty_tree,
        shared_index_quarantine=shared_index_quarantine,
        coverage_gaps=coverage_gaps,
        work_ledger=work_ledger,
        scoped_commit=scoped_commit,
        landing_decision=landing_decision,
    )
    monitor_summary = _monitor_summary(monitor_cards, landing_decision)
    transaction_candidate = _transaction_candidate(
        repo_root,
        target_ids=target_ids,
        declared_paths=declared_paths,
        write_profiles=write_profiles,
        status_rows=status_rows,
        staged_paths=staged_paths,
        classifications=classifications,
        coverage_gaps=coverage_gaps,
        dirty_tree=dirty_tree,
        work_ledger=work_ledger,
        shared_index_quarantine=shared_index_quarantine,
        landing_decision=landing_decision,
        generated_registry=generated_registry,
        require_exclusive=require_exclusive,
    )
    transaction_convergence = _transaction_convergence(
        repo_root,
        target_ids=target_ids,
        transaction_candidate=transaction_candidate,
        dirty_tree=dirty_tree,
        shared_index_quarantine=shared_index_quarantine,
        derived_state_bloat_governor=derived_state_bloat_governor,
        staged_paths=staged_paths,
        freshness_gates=transaction_candidate.get("freshness_gates", {}),
        work_ledger=work_ledger,
    )
    transaction_closeout_settlement = _transaction_closeout_settlement(
        transaction_candidate=transaction_candidate,
        transaction_convergence=transaction_convergence,
        generated_projection_settlement=generated_projection_settlement,
    )
    transaction_convergence_reconcile = _transaction_reconcile_plan(
        repo_root,
        target_ids=target_ids,
        transaction_convergence=transaction_convergence,
        session_id=session_id,
        status_rows=status_rows,
    )
    return {
        "schema": SCHEMA,
        "repo_root": str(repo_root),
        "mode": "read_only",
        "monitor_summary": monitor_summary,
        "monitor_cards": monitor_cards,
        "transaction_candidate": transaction_candidate,
        "transaction_convergence": transaction_convergence,
        "transaction_closeout_settlement": transaction_closeout_settlement,
        "transaction_convergence_reconcile": transaction_convergence_reconcile,
        "autonomous_edit_gate": autonomous_edit_gate,
        "shared_index_quarantine": shared_index_quarantine,
        "derived_state_bloat_governor": derived_state_bloat_governor,
        "runtime_artifact_lifecycle": runtime_artifact_lifecycle,
        "recommended_landing_lane": landing_decision.get("recommended_lane"),
        "mutation_policy": {
            "git_index_mutated": False,
            "task_ledger_mutated": False,
            "work_ledger_mutated": False,
            "projection_rebuilt": False,
            "autonomous_feature_mutation_allowed": autonomous_edit_gate.get(
                "autonomous_feature_mutation_allowed"
            ),
            "required_mode_before_feature_mutation": autonomous_edit_gate.get("required_mode"),
        },
        "inputs": {
            "owned_paths": list(owned_paths),
            "write_profiles": list(write_profiles),
            "target_ids": list(target_ids),
            "session_id": str(session_id or "").strip() or None,
            "require_exclusive": bool(require_exclusive),
            "include_generated_projection_settlement": bool(include_generated_projection_settlement),
        },
        "git": {
            "staged_path_count": len(staged_paths),
            "staged_paths": staged_paths,
            "cached_stat": cached_stat,
            "dirty_path_count": len(dirty_paths),
            "dirty_paths": dirty_paths,
            "status_rows": [row.to_dict() for row in status_rows],
            "command_diagnostics": git_command_diagnostics,
        },
        "path_classifications": classifications,
        "dirty_tree_classification": dirty_tree,
        "coverage_gaps": coverage_gaps,
        "work_ledger": work_ledger,
        "generated_projection_registry": generated_registry,
        "generated_projection_settlement": generated_projection_settlement,
        "scoped_commit_capability": scoped_commit,
        "shared_worktree_guard": _shared_worktree_guard_packet(repo_root, dirty_paths),
        "mission_transaction_card": _mission_transaction_card(
            target_ids=target_ids,
            declared_paths=declared_paths,
            write_profiles=write_profiles,
            staged_paths=staged_paths,
            dirty_paths=dirty_paths,
            coverage_gaps=coverage_gaps,
            work_ledger=work_ledger,
            scoped_commit=scoped_commit,
            landing_decision=landing_decision,
        ),
        "landing_decision": landing_decision,
    }


def _mapping_value(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    result: list[str] = []
    for value in values:
        token = str(value or "").strip()
        if token:
            result.append(token)
    return result


def _preview_strings(values: Iterable[Any], *, limit: int = COMPACT_PREVIEW_LIMIT) -> dict[str, Any]:
    rows = [str(value) for value in values if str(value or "").strip()]
    return {
        "items": rows[:limit],
        "count": len(rows),
        "truncated": len(rows) > limit,
        "preview_limit": limit,
    }


def _load_autonomous_seed_payload(repo_root: Path, seed_ref: str | None) -> dict[str, Any]:
    token = str(seed_ref or "").strip()
    if not token:
        return {}
    candidate = Path(token)
    if not candidate.is_absolute():
        if candidate.exists() or "/" in token:
            candidate = repo_root / candidate
        else:
            candidate = (
                repo_root
                / "state/meta_missions/type_a_autonomous_seed_loop/seeds"
                / f"{token}_autonomous_seed.json"
            )
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "seed_id": token,
            "_load_error": "unavailable_or_invalid_json",
            "_path": str(candidate),
        }
    if isinstance(payload, Mapping):
        row = dict(payload)
        row["_path"] = str(candidate)
        return row
    return {
        "seed_id": token,
        "_load_error": "payload_not_mapping",
        "_path": str(candidate),
    }


def load_autonomous_seed_payload(repo_root: Path, seed_ref: str | None) -> dict[str, Any]:
    """Load an autonomous seed by id or path for read-only preflight reporting."""
    return _load_autonomous_seed_payload(repo_root, seed_ref)


def _selected_seam_from_seed(seed_payload: Mapping[str, Any]) -> dict[str, Any]:
    selected = seed_payload.get("selected_seam")
    if isinstance(selected, Mapping):
        return dict(selected)
    next_candidate = seed_payload.get("next_candidate_seam")
    if isinstance(next_candidate, Mapping):
        return dict(next_candidate)
    return {}


def _candidate_count(seed_payload: Mapping[str, Any]) -> int:
    candidates = seed_payload.get("candidate_seams")
    return len(candidates) if isinstance(candidates, Sequence) and not isinstance(candidates, (str, bytes)) else 0


def _rejection_reasons_present(seed_payload: Mapping[str, Any]) -> bool:
    reasons = seed_payload.get("rejection_reasons")
    return bool(reasons) if isinstance(reasons, Sequence) and not isinstance(reasons, (str, bytes)) else False


def _workitem_or_capture_owner(
    *,
    packet: Mapping[str, Any],
    seed_payload: Mapping[str, Any],
    selected_seam: Mapping[str, Any],
) -> dict[str, Any]:
    inputs = _mapping_value(packet.get("inputs"))
    candidate = _mapping_value(packet.get("transaction_candidate"))
    target_ids = [
        *_string_list(inputs.get("target_ids")),
        *_string_list(candidate.get("task_ledger_subjects")),
    ]
    owner_id = _first_nonempty(target_ids)
    candidate_owner = selected_seam.get("existing_workitem_or_capture_candidate")
    capture_id = ""
    if isinstance(candidate_owner, Mapping):
        capture_id = str(candidate_owner.get("candidate_id") or "").strip()
    if owner_id:
        return {
            "status": "bound",
            "id": owner_id,
            "source": "mission_transaction_target",
        }
    if capture_id:
        return {
            "status": "capture_candidate",
            "id": capture_id,
            "source": "selected_seam",
            "reason": candidate_owner.get("reason") if isinstance(candidate_owner, Mapping) else None,
        }
    seed_owner = str(seed_payload.get("workitem_or_cap_owner") or "").strip()
    if seed_owner:
        return {
            "status": "seed_declared",
            "id": seed_owner,
            "source": "seed_payload",
        }
    return {
        "status": "missing",
        "id": None,
        "source": None,
    }


def _owned_and_mutated_paths(packet: Mapping[str, Any]) -> tuple[list[str], list[str], list[str]]:
    inputs = _mapping_value(packet.get("inputs"))
    owned_paths = sorted(set(_string_list(inputs.get("owned_paths"))))
    git = _mapping_value(packet.get("git"))
    status_rows = git.get("status_rows") if isinstance(git.get("status_rows"), list) else []
    dirty_paths = [
        str(row.get("path") or "").strip()
        for row in status_rows
        if isinstance(row, Mapping) and str(row.get("path") or "").strip()
    ]
    owned_set = set(owned_paths)
    mutated = sorted(path for path in dirty_paths if path in owned_set)
    excluded = sorted(path for path in dirty_paths if path not in owned_set)
    return owned_paths, mutated, excluded


def _current_finalizer_ids(convergence: Mapping[str, Any]) -> list[str]:
    current = _mapping_value(convergence.get("current_transaction"))
    finalizers: list[str] = []
    for key in ("open_finalizers", "compatibility_finalizers"):
        for row in current.get(key) or []:
            if isinstance(row, Mapping):
                _append_unique(finalizers, row.get("id"))
    return finalizers


def _latest_commit_ref(convergence: Mapping[str, Any]) -> str | None:
    for transaction in convergence.get("recent_transactions") or []:
        if not isinstance(transaction, Mapping):
            continue
        ref = _first_nonempty(transaction.get("commit_refs") or [])
        if ref:
            return ref
    return None


def _task_receipt_recorded(convergence: Mapping[str, Any]) -> bool:
    canonical = _mapping_value(convergence.get("canonical_transaction_state"))
    if bool(canonical.get("receipt_recorded")):
        return True
    receipt_state = _mapping_value(convergence.get("task_ledger_receipt_state"))
    if receipt_state.get("latest_execution_receipt"):
        return True
    for transaction in convergence.get("recent_transactions") or []:
        if not isinstance(transaction, Mapping):
            continue
        receipt = _mapping_value(transaction.get("task_ledger_execution_receipt"))
        if receipt.get("status") == "recorded":
            return True
    return False


def _latest_execution_receipt(convergence: Mapping[str, Any]) -> dict[str, Any]:
    receipt_state = _mapping_value(convergence.get("task_ledger_receipt_state"))
    return _mapping_value(receipt_state.get("latest_execution_receipt"))


def _receipt_bound_work_ledger_session_state(convergence: Mapping[str, Any]) -> dict[str, Any]:
    receipt_state = _mapping_value(convergence.get("task_ledger_receipt_state"))
    return _mapping_value(receipt_state.get("latest_execution_receipt_work_ledger_session_state"))


def _session_closed_clean(session: Mapping[str, Any] | None) -> bool:
    session = _mapping_value(session)
    return bool(
        session.get("ended_at")
        and bool(session.get("session_had_ledger_append"))
        and not bool(session.get("stale"))
    )


def _work_ledger_closed_clean(
    convergence: Mapping[str, Any],
    session: Mapping[str, Any] | None = None,
) -> bool:
    session = _mapping_value(session)
    if _session_closed_clean(session):
        return True
    receipt_session = _receipt_bound_work_ledger_session_state(convergence)
    if _session_closed_clean(receipt_session):
        return True
    canonical = _mapping_value(convergence.get("canonical_transaction_state"))
    if bool(canonical.get("work_ledger_closed_clean")):
        return True
    for transaction in convergence.get("recent_transactions") or []:
        if not isinstance(transaction, Mapping):
            continue
        session = _mapping_value(transaction.get("work_ledger_session_finalizer"))
        if transaction.get("work_ledger_closed") and session.get("status") in {
            "append_exempt",
            "closed_clean",
            "unknown_session",
        }:
            return True
    return False


def _work_ledger_append_present(
    convergence: Mapping[str, Any],
    session: Mapping[str, Any] | None = None,
) -> bool:
    session = _mapping_value(session)
    receipt_session = _receipt_bound_work_ledger_session_state(convergence)
    return bool(
        session.get("session_had_ledger_append")
        or receipt_session.get("session_had_ledger_append")
        or _latest_commit_ref(convergence)
    )


def _seed_rewritten_from_proof_loop(proof_loop_report: Mapping[str, Any]) -> bool:
    return bool(
        proof_loop_report.get("runtime_closeout_review_command")
        or proof_loop_report.get("runtime_closeout_status")
        or proof_loop_report.get("owned_closeout_status")
        or proof_loop_report.get("continuation_policy")
    )


def _owned_closeout_review(
    *,
    owner: Mapping[str, Any],
    proof_surface: str | None,
    blocked_primary_continuation: Mapping[str, Any] | None = None,
    task_ledger_receipt_recorded: bool,
    work_ledger_append_present: bool,
    work_ledger_closed_clean: bool,
    seed_rewritten: bool,
    owned_paths_committed_clean: bool,
    validators_present: bool,
    commit_ref: str | None,
    latest_execution_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    missing: list[str] = []
    if str(owner.get("status") or "") == "missing":
        blockers.append("owner_or_cap_binding")
    if not proof_surface:
        blockers.append("proof_surface")
    blocked_primary_continuation = _mapping_value(blocked_primary_continuation)
    if (
        blocked_primary_continuation.get("required")
        and blocked_primary_continuation.get("status") != "complete"
    ):
        blockers.append("blocked_primary_receipt_missing")
    if not task_ledger_receipt_recorded:
        missing.append("task_ledger_execution_receipt")
    if not work_ledger_append_present:
        missing.append("work_ledger_append")
    if not work_ledger_closed_clean:
        missing.append("work_ledger_closed_clean")
    if not seed_rewritten:
        missing.append("seed_rewrite_review")
    if not owned_paths_committed_clean:
        missing.append("owned_paths_committed_clean")
    if not validators_present:
        missing.append("validators_run")

    if blockers:
        status = "blocked"
    elif missing:
        status = "settlement_required"
    else:
        status = "clean"
    return {
        "status": status,
        "task_ledger_receipt_recorded": task_ledger_receipt_recorded,
        "latest_execution_receipt_id": latest_execution_receipt.get("id")
        or latest_execution_receipt.get("transaction_id"),
        "work_ledger_append_present": work_ledger_append_present,
        "work_ledger_closed_clean": work_ledger_closed_clean,
        "seed_rewritten": seed_rewritten,
        "owned_paths_committed_clean": owned_paths_committed_clean,
        "validators_present": validators_present,
        "proof_surface_present": bool(proof_surface),
        "blocked_primary_continuation": dict(blocked_primary_continuation),
        "commit_ref": commit_ref,
        "blockers": blockers,
        "missing": missing,
    }


def _ambient_settlement_review(
    *,
    dirty_exclusions: Sequence[str],
    dirty_exclusions_preview: Mapping[str, Any],
    open_finalizer_ids: Sequence[str],
    owned_closeout_status: str,
) -> dict[str, Any]:
    residuals: list[dict[str, Any]] = []
    if dirty_exclusions:
        residuals.append(
            {
                "kind": "dirty_paths_excluded",
                "count": len(dirty_exclusions),
                "preview": dirty_exclusions_preview,
            }
        )
    if open_finalizer_ids:
        residuals.append(
            {
                "kind": "open_or_compatibility_finalizers",
                "count": len(open_finalizer_ids),
                "ids": list(open_finalizer_ids),
            }
        )
    unrelated_shared_tree_residue = bool(residuals)
    if not unrelated_shared_tree_residue:
        status = "clean"
    elif owned_closeout_status == "clean":
        status = "residualized"
    else:
        status = "settlement_required"
    return {
        "status": status,
        "dirty_exclusions": dirty_exclusions_preview,
        "open_finalizer_ids": list(open_finalizer_ids),
        "unrelated_shared_tree_residue": unrelated_shared_tree_residue,
        "residuals_bound_or_excluded": residuals,
    }


def _continuation_policy(
    *,
    owned_closeout: Mapping[str, Any],
    ambient_settlement: Mapping[str, Any],
    phase_id: str | None,
) -> dict[str, Any]:
    owned_status = str(owned_closeout.get("status") or "")
    ambient_status = str(ambient_settlement.get("status") or "")
    may_open = owned_status == "clean" and ambient_status in {
        "clean",
        "residualized",
        "advisory",
    }
    workitem_command = (
        f"./repo-python kernel.py --workitem-entrypoint {shlex.quote(phase_id)}"
        if phase_id
        else "./repo-python kernel.py --workitem-entrypoint <active_phase>"
    )
    if may_open:
        next_menu_source = "workitem-entrypoint"
        required_next_action = f"open the WorkItem entrypoint via `{workitem_command}`"
    else:
        next_menu_source = "runtime-review-self"
        blockers = list(owned_closeout.get("blockers") or owned_closeout.get("missing") or [])
        required_next_action = (
            "continue runtime-closeout-review:self"
            + (f" until {', '.join(str(item) for item in blockers)} is settled" if blockers else "")
        )
    return {
        "may_open_next_workitem": may_open,
        "next_menu_source": next_menu_source,
        "required_next_action": required_next_action,
        "workitem_entrypoint_command": workitem_command if may_open else None,
        "residuals_bound_or_excluded": ambient_settlement.get("residuals_bound_or_excluded") or [],
    }


def _runtime_closeout_status(
    *,
    owner_status: str,
    proof_surface: str | None,
    packet: Mapping[str, Any],
    seed_payload: Mapping[str, Any],
    blocked_primary_continuation: Mapping[str, Any] | None = None,
    mutated_paths: Sequence[str] | None = None,
) -> tuple[str, str]:
    convergence = _mapping_value(packet.get("transaction_convergence"))
    closeout = _mapping_value(packet.get("transaction_closeout_settlement"))
    reconcile = _mapping_value(packet.get("transaction_convergence_reconcile"))
    landing = _mapping_value(packet.get("landing_decision"))
    summary = _mapping_value(convergence.get("summary"))
    current = _mapping_value(convergence.get("current_transaction"))
    seed_was_loaded = bool(seed_payload)
    if owner_status == "missing":
        return "blocked", "bind WorkItem/cap owner or capture candidate before mutation"
    if seed_was_loaded and not proof_surface:
        return "blocked", "selected seam is missing a proof_surface"
    if str(landing.get("status") or "") in {"blocked", "hard_stop"}:
        blocked_primary_continuation = _mapping_value(blocked_primary_continuation)
        if blocked_primary_continuation.get("required"):
            if blocked_primary_continuation.get("status") != "complete":
                return "blocked", "blocked_primary_receipt_missing"
            if str(landing.get("reason") or "") == "work_ledger_claim_collision":
                pass
            else:
                return "blocked", str(landing.get("recommended_lane") or "clear landing blockers")
        else:
            return "blocked", str(landing.get("recommended_lane") or "clear landing blockers")
    if str(convergence.get("status") or "") == "blocked":
        return "blocked", str(convergence.get("next_action") or "clear transaction convergence blockers")
    if str(current.get("status") or "") == "claim_required" and mutated_paths:
        return "blocked", "claim_required_before_mutation"

    receipt_missing = bool(_int_value(summary.get("landed_without_task_ledger_receipt")))
    receipt_pending = bool(_int_value(summary.get("receipt_pending_in_intake")))
    work_ledger_stale = bool(_int_value(summary.get("stale_work_ledger_sessions")))
    open_finalizers = bool(_int_value(summary.get("open_current_finalizers")))
    closeout_pending = str(closeout.get("status") or "") in {
        "eventful_closeout_pending",
        "settlement_required",
        "generated_projection_settlement_required",
    }
    reconcile_needs_action = str(reconcile.get("status") or "") in {"ready", "watch", "blocked"}
    if receipt_missing or receipt_pending or work_ledger_stale or open_finalizers or closeout_pending or reconcile_needs_action:
        return "settlement_required", str(
            convergence.get("next_action")
            or reconcile.get("next_action")
            or closeout.get("required_next_command")
            or "complete runtime closeout finalizers"
        )
    if str(convergence.get("status") or "") == "watch":
        return "advisory", str(convergence.get("next_action") or "inspect transaction convergence")
    return "clean", "none"


def build_explore_execute_review_runtime_closeout(
    packet: Mapping[str, Any],
    *,
    seed_payload: Mapping[str, Any] | None = None,
    seed_id: str | None = None,
    selector_surface: str | None = None,
    blocked_primary_continuation_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose Explore -> Execute -> Review evidence for autonomous seed waves."""
    seed_payload = dict(seed_payload or {})
    selected_seam = _selected_seam_from_seed(seed_payload)
    proof_loop_report = _mapping_value(seed_payload.get("proof_loop_report"))
    blocked_primary_continuation = _blocked_primary_continuation_receipt_payload(
        packet=packet,
        seed_payload=seed_payload,
        proof_loop_report=proof_loop_report,
        explicit_receipt=blocked_primary_continuation_receipt,
    )
    convergence = _mapping_value(packet.get("transaction_convergence"))
    candidate = _mapping_value(packet.get("transaction_candidate"))
    closeout = _mapping_value(packet.get("transaction_closeout_settlement"))
    reconcile = _mapping_value(packet.get("transaction_convergence_reconcile"))
    work_ledger = _mapping_value(packet.get("work_ledger"))
    session = _mapping_value(work_ledger.get("session"))
    owner = _workitem_or_capture_owner(
        packet=packet,
        seed_payload=seed_payload,
        selected_seam=selected_seam,
    )
    owned_paths, mutated_paths, dirty_exclusions = _owned_and_mutated_paths(packet)
    proof_surface = str(selected_seam.get("proof_surface") or seed_payload.get("proof_surface") or "").strip() or None
    status, required_next_action = _runtime_closeout_status(
        owner_status=str(owner.get("status") or "missing"),
        proof_surface=proof_surface,
        packet=packet,
        seed_payload=seed_payload,
        blocked_primary_continuation=blocked_primary_continuation,
        mutated_paths=mutated_paths,
    )
    seed_ref = str(seed_id or seed_payload.get("seed_id") or "").strip() or None
    inputs = _mapping_value(packet.get("inputs"))
    commit_ref = _latest_commit_ref(convergence)
    latest_execution_receipt = _latest_execution_receipt(convergence)
    receipt_bound_session = _receipt_bound_work_ledger_session_state(convergence)
    work_ledger_append_present = _work_ledger_append_present(convergence, session)
    work_ledger_closed_clean = _work_ledger_closed_clean(convergence, session)
    seed_rewritten = _seed_rewritten_from_proof_loop(proof_loop_report)
    validators_run = proof_loop_report.get("validators_run") or []
    dirty_exclusions_preview = _preview_strings(dirty_exclusions)
    open_finalizer_ids = _current_finalizer_ids(convergence)
    owned_closeout = _owned_closeout_review(
        owner=owner,
        proof_surface=proof_surface,
        blocked_primary_continuation=blocked_primary_continuation,
        task_ledger_receipt_recorded=_task_receipt_recorded(convergence),
        work_ledger_append_present=work_ledger_append_present,
        work_ledger_closed_clean=work_ledger_closed_clean,
        seed_rewritten=seed_rewritten,
        owned_paths_committed_clean=not bool(mutated_paths),
        validators_present=bool(validators_run),
        commit_ref=commit_ref,
        latest_execution_receipt=latest_execution_receipt,
    )
    ambient_settlement = _ambient_settlement_review(
        dirty_exclusions=dirty_exclusions,
        dirty_exclusions_preview=dirty_exclusions_preview,
        open_finalizer_ids=open_finalizer_ids,
        owned_closeout_status=str(owned_closeout.get("status") or ""),
    )
    phase_id = str(convergence.get("phase_id") or candidate.get("phase_id") or "").strip() or None
    continuation_policy = _continuation_policy(
        owned_closeout=owned_closeout,
        ambient_settlement=ambient_settlement,
        phase_id=phase_id,
    )
    review_command = (
        "./repo-python tools/meta/control/mission_transaction_preflight.py --explore-execute-review"
        + (f" --external-pattern-seed {shlex.quote(seed_ref)}" if seed_ref else "")
        + "".join(
            f" --subject-id {shlex.quote(target)}"
            for target in _string_list(inputs.get("target_ids"))
        )
    )
    return {
        "schema": EXPLORE_EXECUTE_REVIEW_CLOSEOUT_SCHEMA,
        "kind": "meta_mission_runtime_closeout_review",
        "seed_id": seed_ref,
        "selected_seam": selected_seam,
        "explore": {
            "selector_surface": selector_surface
            or "./repo-python kernel.py --annex-inspiration <query>",
            "selected_external_source": selected_seam.get("external_source"),
            "selected_external_pattern": selected_seam.get("external_pattern"),
            "selected_local_seam": selected_seam.get("owner_surface"),
            "candidate_count": _candidate_count(seed_payload),
            "rejection_reasons_present": _rejection_reasons_present(seed_payload),
        },
        "execute": {
            "workitem_or_cap_owner": owner,
            "claimed_paths": [
                row.get("path") or row.get("scope_id")
                for row in work_ledger.get("matching_active_claims") or []
                if isinstance(row, Mapping)
            ],
            "owned_paths": owned_paths,
            "mutated_paths": mutated_paths,
            "commit_ref": commit_ref,
            "transaction_id": candidate.get("transaction_id"),
            "transaction_status": candidate.get("status"),
            "validators_run": validators_run,
        },
        "review": {
            "proof_surface": proof_surface,
            "runtime_closeout_review_command": review_command,
            "transaction_convergence_status": convergence.get("status"),
            "transaction_convergence_next_action": convergence.get("next_action"),
            "transaction_reconcile_status": reconcile.get("status"),
            "transaction_reconcile_next_action": reconcile.get("next_action"),
            "closeout_settlement_status": closeout.get("status"),
            "blocked_primary_continuation": blocked_primary_continuation,
            "task_ledger_receipt_recorded": _task_receipt_recorded(convergence),
            "latest_execution_receipt": latest_execution_receipt,
            "work_ledger_append_present": work_ledger_append_present,
            "work_ledger_closed_clean": work_ledger_closed_clean,
            "work_ledger_session_state": {
                "session_id": session.get("session_id"),
                "read_receipt_id": session.get("read_receipt_id"),
                "ended_at": session.get("ended_at"),
                "session_had_ledger_append": session.get("session_had_ledger_append"),
                "stale": session.get("stale"),
                "stale_reason": session.get("stale_reason"),
            },
            "receipt_bound_work_ledger_session_state": receipt_bound_session,
            "seed_rewritten": seed_rewritten,
            "dirty_paths_excluded": dirty_exclusions_preview,
            "open_finalizer_ids": open_finalizer_ids,
            "next_candidate_seam": seed_payload.get("next_candidate_seam"),
            "owned_closeout_status": owned_closeout.get("status"),
            "ambient_settlement_status": ambient_settlement.get("status"),
            "continuation_policy_may_open_next_workitem": continuation_policy.get(
                "may_open_next_workitem"
            ),
        },
        "owned_closeout": owned_closeout,
        "ambient_settlement": ambient_settlement,
        "continuation_policy": continuation_policy,
        "status": status,
        "required_next_action": required_next_action,
        "authority": {
            "projection_owner": "system/lib/mission_transaction_landing_preflight.py",
            "task_ledger_authority": TASK_LEDGER_EVENTS,
            "work_ledger_authority": (
                convergence.get("authority") or {}
            ).get("work_ledger_authority")
            if isinstance(convergence.get("authority"), Mapping)
            else None,
            "seed_authority": seed_payload.get("_path"),
        },
        "read_only": True,
    }
