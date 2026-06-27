#!/usr/bin/env python3
"""
Scoped-commit actuator using a private index and HEAD CAS.

[PURPOSE]
- Teleology: Author a single bounded commit in a multi-agent shared-index
  repo without ever touching the shared `.git/index`.  This converts the
  three-layer commit discipline encoded in AGENTS.md (exact pathspec add
  -> staged path/hunk equality -> pathspec commit when target-path
  worktree residual is empty) from a behavioral practice into an
  infrastructure invariant.
- Mechanism: Build a temporary `GIT_INDEX_FILE` initialized from HEAD,
  stage either exact paths (from the working tree) or a unified diff
  patch into that private index, verify the changed-path set against
  the caller's declared pathset, write a tree, commit-tree it onto the
  captured parent, and update-ref the current branch with the captured
  parent as the CAS expectation.  Commit selection never depends on the
  shared index.  After a successful CAS, the tool may pathspec-refresh
  shared-index entries for the committed paths only, so the normal worktree
  view does not report stale inverse staged hunks from the old HEAD.
- Non-goal: This tool does not push, does not write doctrine, does not
  resolve merges, does not rewrite history, does not amend, and does
  not bypass repo signing or hooks except by routing through
  `git commit-tree` (which intentionally does not run commit hooks).

[INTERFACE]
- subcommand `full-paths`: scope a commit by exact paths.  Worktree
  contents of the named paths must equal the intended commit content.
  Multi-hunk tracked file diffs are refused unless explicitly allowed;
  use `patch` mode for hunk-only ownership in concurrently dirty files.
- subcommand `patch`: scope a commit by a unified diff.  Use this for
  hunk-only commits into concurrently-dirty target files.  After a
  successful commit it refreshes shared-index entries for committed
  paths only when those paths were not already staged in the shared
  index.
- subcommand `tracked-removals`: remove tracked entries from the commit
  tree through the private index while leaving working-tree files on disk.
  Use this for build caches that were accidentally committed and should be
  de-tracked plus ignored.
- optional `--expected-parent`: bind the commit to a previously captured
  HEAD/read-set parent.  If another actor advanced HEAD before this
  commit lands, the update-ref CAS fails instead of relanding stale
  worktree contents over newer same-path changes.

[CONSTRAINTS]
- stdlib only.
- HEAD must be on a named branch unless `--allow-detached` is set.
- The private-index changed-path set must be non-empty and stay within
  the declared `--path` set; clean declared paths are allowed because
  generated projection bundles often carry stable manifests plus only the
  currently dirty projection subset.
- Full-path mode refuses multi-hunk tracked file diffs by default because
  path-level scoping cannot prove hunk-level ownership.
- Empty messages and no-op commits are refused.
- Never invokes `git commit` against the shared index.
"""
from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[3]
WORK_LEDGER_SESSION_ENV_VARS = (
    "AIW_WORK_LEDGER_SESSION_ID",
    "WORK_LEDGER_SESSION_ID",
    "AIW_ACTOR_SESSION_ID",
    "AIW_SESSION_ID",
)
DRY_RUN_MESSAGE_PLACEHOLDER = "scoped-commit dry-run placeholder"
SCOPED_COMMIT_MIN_FREE_BYTES_ENV = "AIW_SCOPED_COMMIT_MIN_FREE_BYTES"
SCOPED_COMMIT_MIN_FREE_BYTES_DEFAULT = 512 * 1024 * 1024
SCOPED_COMMIT_WRITE_ESTIMATE_FLOOR_BYTES = 64 * 1024 * 1024
SCOPED_COMMIT_WRITE_AMPLIFICATION = 2
SCOPED_COMMIT_HEAD_CAS_MAX_REFRESH_RETRIES = 1
SCOPED_COMMIT_HEAD_CAS_MEMORY_FILE = "aiw_scoped_commit_head_cas_failures.jsonl"
SCOPED_COMMIT_HEAD_CAS_MEMORY_TTL_SECONDS = 12 * 60 * 60
TASK_LEDGER_MONOLITH_COMMIT_OVERRIDE_ENV = "AIW_SCOPED_COMMIT_ALLOW_TASK_LEDGER_MONOLITH"
COMMAND_TEMPLATE_TOKEN_RE = re.compile(r"<([^<>]+)>")
_SUBCOMMANDS = {"full-paths", "patch", "tracked-removals"}
_ROOT_FULL_PATH_FLAGS = {
    "--path",
    "--message",
    "--message-file",
    "--allow-detached",
    "--allow-untracked",
    "--allow-multi-hunk-full-paths",
    "--dry-run",
    "--expected-parent",
    "--cas-retry-attempt",
    "--work-ledger-session-id",
    "--remote-fallback-on-metadata-block",
    "--remote-name",
    "--target-ref",
}


def _command_template_bindings(command: str) -> list[str]:
    bindings: list[str] = []
    for match in COMMAND_TEMPLATE_TOKEN_RE.finditer(command):
        binding = match.group(1).strip()
        if binding and binding not in bindings:
            bindings.append(binding)
    return bindings


def _command_artifact_contract(
    command: str,
    *,
    parser_owner: str,
    unsupported_flags: list[str] | None = None,
) -> dict[str, object]:
    unsupported = sorted(set(unsupported_flags or []))
    required_bindings = _command_template_bindings(command)
    tokenization_error = ""
    try:
        shlex.split(command)
        tokenized = True
    except ValueError as exc:
        tokenized = False
        tokenization_error = str(exc)

    if not command.strip():
        state = "missing"
        runnable = False
        conformance_status = "no_command"
    elif not tokenized:
        state = "invalid"
        runnable = False
        conformance_status = "tokenization_failed"
    elif unsupported:
        state = "invalid"
        runnable = False
        conformance_status = "unsupported_flags_present"
    elif required_bindings:
        state = "template"
        runnable = False
        conformance_status = "template_requires_binding"
    else:
        state = "runnable"
        runnable = True
        conformance_status = "runnable_no_known_placeholders"

    contract: dict[str, object] = {
        "schema": "command_artifact_contract_v0",
        "state": state,
        "runnable": runnable,
        "parser_owner": parser_owner,
        "tokenization": "shlex",
        "required_bindings": required_bindings,
        "unsupported_flags": unsupported,
        "conformance_status": conformance_status,
    }
    if tokenization_error:
        contract["tokenization_error"] = tokenization_error
    return contract


def _command_template_row(
    *,
    row_id: str,
    command: str,
    template: bool,
    required_fields: list[str],
    parser_owner: str,
    owner_help_route: str | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": row_id,
        "command": command,
        "template": template,
        "required_fields": required_fields,
        "command_contract": _command_artifact_contract(
            command,
            parser_owner=parser_owner,
        ),
    }
    if owner_help_route:
        row["owner_help_route"] = owner_help_route
    return row


class GitMetadataBlockedError(RuntimeError):
    """Raised when the live repo cannot write `.git` metadata."""

    def __init__(self, message: str, *, capability: dict[str, object], operation: str) -> None:
        super().__init__(message)
        self.capability = capability
        self.operation = operation


class HeadCasFailureError(RuntimeError):
    """Raised when HEAD advanced before a private-index commit could land."""

    def __init__(self, message: str, *, retry_packet: dict[str, object]) -> None:
        super().__init__(message)
        self.retry_packet = retry_packet


class ScopedCommitMultiHunkFullPathsError(ValueError):
    """Raised when full-path mode would commit ambiguous multi-hunk files."""

    def __init__(self, message: str, *, mode: str, multi_hunk_paths: dict[str, int]) -> None:
        super().__init__(message)
        self.mode = mode
        self.multi_hunk_paths = dict(multi_hunk_paths)


def _run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    input_data: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a subprocess, capturing stdout/stderr as text."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    result = subprocess.run(
        args,
        cwd=str(cwd),
        env=full_env,
        capture_output=True,
        text=True,
        input=input_data,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(args)}\n"
            f"stderr: {result.stderr.strip()}"
        )
    return result


def _configured_scoped_commit_min_free_bytes() -> int:
    raw = os.environ.get(SCOPED_COMMIT_MIN_FREE_BYTES_ENV)
    if not raw:
        return SCOPED_COMMIT_MIN_FREE_BYTES_DEFAULT
    try:
        return max(0, int(raw))
    except ValueError:
        return SCOPED_COMMIT_MIN_FREE_BYTES_DEFAULT


def _path_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return int(path.stat().st_size)
        except OSError:
            return 0
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += int(child.stat().st_size)
            except OSError:
                continue
    return total


def _scoped_commit_disk_headroom(
    repo_root: Path,
    *,
    operation: str,
    paths: list[str],
) -> dict[str, object]:
    usage = shutil.disk_usage(str(repo_root))
    estimated_bytes = sum(_path_size_bytes(repo_root / rel) for rel in paths)
    configured_floor = _configured_scoped_commit_min_free_bytes()
    required_bytes = max(
        configured_floor,
        SCOPED_COMMIT_WRITE_ESTIMATE_FLOOR_BYTES
        + (estimated_bytes * SCOPED_COMMIT_WRITE_AMPLIFICATION),
    )
    return {
        "schema": "scoped_commit_disk_headroom_v0",
        "ok": int(usage.free) >= int(required_bytes),
        "operation": operation,
        "usage_path": str(repo_root),
        "free_bytes": int(usage.free),
        "required_bytes": int(required_bytes),
        "configured_min_free_bytes": int(configured_floor),
        "estimated_declared_path_bytes": int(estimated_bytes),
        "write_amplification": SCOPED_COMMIT_WRITE_AMPLIFICATION,
        "checked_paths": list(paths),
    }


def _assert_scoped_commit_disk_headroom(
    repo_root: Path,
    *,
    operation: str,
    paths: list[str],
) -> None:
    headroom = _scoped_commit_disk_headroom(repo_root, operation=operation, paths=paths)
    if bool(headroom.get("ok")):
        return
    raise RuntimeError(
        "scoped-commit: insufficient disk headroom before "
        f"{operation}; free={headroom.get('free_bytes')}; "
        f"required={headroom.get('required_bytes')}; "
        f"usage_path={headroom.get('usage_path')}; "
        "free disposable scratch space or lower "
        f"{SCOPED_COMMIT_MIN_FREE_BYTES_ENV} only for an explicitly safe emergency write"
    )


def _git(args: list[str], *, cwd: Path, **kwargs) -> subprocess.CompletedProcess:
    return _run(["git", *args], cwd=cwd, **kwargs)


def _recent_commit_preview(repo_root: Path, *, parent_sha: str, limit: int = 5) -> list[str]:
    res = _git(
        ["log", "--oneline", "--decorate", f"--max-count={limit}", f"{parent_sha}..HEAD"],
        cwd=repo_root,
        check=False,
    )
    if res.returncode != 0:
        return []
    return [line for line in res.stdout.splitlines() if line.strip()]


def _repo_git_dir(repo_root: Path) -> Path:
    res = _git(["rev-parse", "--git-dir"], cwd=repo_root, check=False)
    raw = res.stdout.strip() if res.returncode == 0 else ""
    if not raw:
        return repo_root / ".git"
    git_dir = Path(raw)
    return git_dir if git_dir.is_absolute() else (repo_root / git_dir).resolve()


def _head_cas_memory_path(repo_root: Path) -> Path:
    return _repo_git_dir(repo_root) / SCOPED_COMMIT_HEAD_CAS_MEMORY_FILE


def _head_cas_evidence_root(
    *,
    mode: str,
    branch_ref: str,
    scoped_evidence_sha: str,
    changed_paths: list[str],
) -> str:
    payload = {
        "schema": "scoped_commit_head_cas_evidence_root_v0",
        "mode": mode,
        "branch_ref": branch_ref,
        "scoped_evidence_sha": scoped_evidence_sha,
        "changed_paths": sorted(changed_paths),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _private_index_scoped_evidence_sha(
    repo_root: Path,
    changed_paths: list[str],
    *,
    env: dict[str, str],
) -> str:
    entries: list[dict[str, object]] = []
    for rel in sorted(changed_paths):
        res = _git(["ls-files", "-s", "--", rel], cwd=repo_root, env=env, check=False)
        index_entries = [line for line in res.stdout.splitlines() if line.strip()]
        entries.append(
            {
                "path": rel,
                "index_entries": index_entries or ["<absent>"],
            }
        )
    payload = {
        "schema": "scoped_commit_changed_path_evidence_v0",
        "entries": entries,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _head_cas_memory_events(repo_root: Path) -> list[dict[str, object]]:
    path = _head_cas_memory_path(repo_root)
    try:
        rows = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    except OSError:
        return []

    events: list[dict[str, object]] = []
    for line in rows[-500:]:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _head_cas_retry_memory_status(
    repo_root: Path,
    *,
    evidence_root: str,
) -> dict[str, object]:
    path = _head_cas_memory_path(repo_root)
    now = time.time()
    cutoff = now - SCOPED_COMMIT_HEAD_CAS_MEMORY_TTL_SECONDS
    same_root: list[dict[str, object]] = []
    for event in _head_cas_memory_events(repo_root):
        if event.get("evidence_root") != evidence_root:
            continue
        try:
            ts = float(event.get("ts") or 0)
        except (TypeError, ValueError):
            ts = 0
        if ts < cutoff:
            continue
        same_root.append(event)

    last_landed_index = -1
    for index, event in enumerate(same_root):
        if event.get("event") == "landed":
            last_landed_index = index
    active_events = same_root[last_landed_index + 1 :]
    prior_failure_count = sum(
        1 for event in active_events if event.get("event") == "cas_failure"
    )
    return {
        "schema": "scoped_commit_head_cas_retry_memory_v0",
        "status": "available",
        "storage": "repo_git_dir",
        "memory_ref": f"git-dir:{path.name}",
        "evidence_root": evidence_root,
        "ttl_seconds": SCOPED_COMMIT_HEAD_CAS_MEMORY_TTL_SECONDS,
        "prior_failure_count": prior_failure_count,
        "landed_reset_seen": last_landed_index >= 0,
        "event_count_for_root": len(same_root),
        "active_event_count_for_root": len(active_events),
    }


def _record_head_cas_memory_event(
    repo_root: Path,
    *,
    event: str,
    evidence_root: str,
    mode: str,
    branch_ref: str,
    tree_sha: str,
    scoped_evidence_sha: str,
    changed_paths: list[str],
    expected_parent: str = "",
    current_head: str = "",
    attempted_commit: str = "",
    status: str = "",
    effective_retry_attempt: int = 0,
) -> dict[str, object]:
    path = _head_cas_memory_path(repo_root)
    row = {
        "schema": "scoped_commit_head_cas_memory_event_v0",
        "ts": time.time(),
        "event": event,
        "evidence_root": evidence_root,
        "mode": mode,
        "branch_ref": branch_ref,
        "tree_sha": tree_sha,
        "scoped_evidence_sha": scoped_evidence_sha,
        "changed_paths": list(changed_paths),
        "expected_parent": expected_parent,
        "current_head": current_head,
        "attempted_commit": attempted_commit,
        "status": status,
        "effective_retry_attempt": effective_retry_attempt,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    except OSError as exc:
        return {
            "schema": "scoped_commit_head_cas_memory_record_receipt_v0",
            "status": "not_recorded",
            "event": event,
            "evidence_root": evidence_root,
            "error_class": type(exc).__name__,
        }
    return {
        "schema": "scoped_commit_head_cas_memory_record_receipt_v0",
        "status": "recorded",
        "event": event,
        "evidence_root": evidence_root,
        "memory_ref": f"git-dir:{path.name}",
    }


def _build_head_cas_retry_packet(
    repo_root: Path,
    *,
    mode: str,
    branch_ref: str,
    expected_parent: str,
    attempted_commit: str,
    attempted_tree: str,
    scoped_evidence_sha: str,
    changed_paths: list[str],
    update_stderr: str,
    cas_retry_attempt: int = 0,
    retry_memory: dict[str, object] | None = None,
) -> dict[str, object]:
    current_head = _git(["rev-parse", "HEAD"], cwd=repo_root, check=False).stdout.strip()
    refresh_retry_attempt = max(0, int(cas_retry_attempt or 0))
    retry_budget_exhausted = (
        refresh_retry_attempt >= SCOPED_COMMIT_HEAD_CAS_MAX_REFRESH_RETRIES
    )
    selected_option = (
        {
            "lane": "validated_uncommitted_receipt",
            "state": "required",
            "receipt_ref": "validated_uncommitted_git_metadata_blocked",
        }
        if retry_budget_exhausted
        else {
            "lane": "cas_retry",
            "state": "queued",
            "receipt_ref": "scoped-commit-head-cas-retry-packet",
        }
    )
    continuation_state = (
        "validated_uncommitted_receipt_required"
        if retry_budget_exhausted
        else "retry_required_after_refresh"
    )
    return {
        "schema": "scoped_commit_head_cas_retry_packet_v1",
        "status": (
            "blocked_head_advanced_retry_budget_exhausted"
            if retry_budget_exhausted
            else "blocked_head_advanced"
        ),
        "surface": "tools/meta/control/scoped_commit.py",
        "mode": mode,
        "continuation_state": continuation_state,
        "source_failure": "git_update_ref_cas_mismatch",
        "selected_option": selected_option,
        "stale_option_retirement": {
            "retired_expected_parent": expected_parent,
            "reason": "same scoped commit must not be retried against the stale parent",
            "next_expected_parent": current_head,
        },
        "retry_budget": {
            "schema": "scoped_commit_head_cas_retry_budget_v0",
            "max_refresh_retry_attempts": SCOPED_COMMIT_HEAD_CAS_MAX_REFRESH_RETRIES,
            "current_refresh_retry_attempt": refresh_retry_attempt,
            "remaining_refresh_retries_after_failure": (
                0
                if retry_budget_exhausted
                else max(
                    0,
                    SCOPED_COMMIT_HEAD_CAS_MAX_REFRESH_RETRIES - refresh_retry_attempt,
                )
            ),
            "budget_exhausted": retry_budget_exhausted,
            "attempt_count_source": (
                "max_of_caller_retry_attempt_and_repo_git_dir_retry_memory"
            ),
            "rule": (
                "After one refreshed retry for the same evidence root, a second "
                "HEAD-CAS failure must stop the landing loop and bind a residual "
                "or coordination handoff instead of launching another blind retry."
            ),
            "residual_required_when": [
                "same evidence root already consumed the refresh retry",
                "current_head changes again before retry landing",
                "recent commits cannot be proven disjoint from the owned paths",
            ],
        },
        "branch_ref": branch_ref,
        "expected_parent": expected_parent,
        "current_head": current_head,
        "attempted_commit": attempted_commit,
        "attempted_tree": attempted_tree,
        "scoped_evidence_sha": scoped_evidence_sha,
        "changed_path_count": len(changed_paths),
        "changed_paths": list(changed_paths),
        "retry_memory": retry_memory or {},
        "recent_commits_preview": _recent_commit_preview(repo_root, parent_sha=expected_parent),
        "git_stderr": update_stderr.strip()[:500],
        "required_before_retry": [
            "re_read_current_head",
            "inspect_recent_commits_for_owned_path_overlap",
            "confirm_scoped_diff_still_matches_owned_intent",
            "rerun_work_ledger_or_mission_preflight_for_owned_paths",
            "rerun_focused_validation_or_record_a_typed_validation_substitution",
            "confirm_cas_retry_budget_not_exhausted_for_this_evidence_root",
            "retry_scoped_commit_with_expected_parent_equal_to_current_head",
        ],
        "stop_conditions": [
            "same_owned_path_changed_by_new_head",
            "work_ledger_or_mission_preflight_reports_live_collision",
            "focused_validation_no_longer_matches_the_retry_assumption",
            "current_head_changes_again_before_retry_landing",
            "second_head_cas_failure_for_same_evidence_root",
            "cas_retry_budget_exhausted",
        ],
        "command_template_contract": {
            "schema": "scoped_commit_command_template_contract_v0",
            "rule": (
                "Only copy-run command_templates whose command_contract.runnable "
                "is true. Template rows must have every command_contract.required_bindings "
                "value replaced from live HEAD, Work Ledger, Task Ledger, validation, "
                "and original scoped-commit arguments before execution."
            ),
            "owner_help_route_rule": (
                "When a template row parses incorrectly or the agent is unsure which "
                "flags are legal, run owner_help_route before retrying the command."
            ),
            "placeholder_syntax": "<binding-name>",
        },
        "command_templates": [
            _command_template_row(
                row_id="refresh_head",
                command="git rev-parse HEAD",
                template=False,
                required_fields=[],
                parser_owner="git",
            ),
            _command_template_row(
                row_id="inspect_recent_commits",
                command=f"git log --oneline --decorate --max-count=5 {expected_parent}..HEAD",
                template=False,
                required_fields=[],
                parser_owner="git",
            ),
            _command_template_row(
                row_id="mission_preflight_recheck",
                command=(
                    "./repo-python tools/meta/control/mission_transaction_preflight.py "
                    "--subject-id <subject-id> --session-id <work-ledger-session-id> "
                    "--owned-path <owned-path> --fail-on-status blocked"
                ),
                template=True,
                required_fields=[
                    "subject-id",
                    "work-ledger-session-id",
                    "owned-path",
                ],
                parser_owner="mission_transaction_preflight",
                owner_help_route=(
                    "./repo-python tools/meta/control/mission_transaction_preflight.py --help"
                ),
            ),
            _command_template_row(
                row_id="retry_scoped_commit",
                command=(
                    "./repo-python tools/meta/control/scoped_commit.py <mode> "
                    "--expected-parent <current-head> --cas-retry-attempt 1 "
                    "<original-path-and-message-args>"
                ),
                template=True,
                required_fields=[
                    "mode",
                    "current-head",
                    "original-path-and-message-args",
                ],
                parser_owner="scoped_commit",
                owner_help_route="./repo-python tools/meta/control/scoped_commit.py --help",
            ),
            _command_template_row(
                row_id="record_validated_uncommitted_receipt",
                command=(
                    "./repo-python tools/meta/factory/task_ledger_apply.py "
                    "record-execution-receipt --subject-id <subject-id> "
                    "--transaction-id <transaction-id> "
                    "--closeout-state validated_uncommitted_git_metadata_blocked "
                    "--no-commit-reason parent_cas_retry_budget_exhausted "
                    "--validation-ref <validation-ref> "
                    "--commit-blocker-ref scoped-commit-head-cas-retry-packet "
                    "--commit-blocker-ref parent_cas_retry_budget_exhausted"
                ),
                template=True,
                required_fields=[
                    "subject-id",
                    "transaction-id",
                    "validation-ref",
                ],
                parser_owner="task_ledger_apply",
                owner_help_route=(
                    "./repo-python tools/meta/factory/task_ledger_apply.py "
                    "record-execution-receipt --help"
                ),
            ),
        ],
        "receipt_condition": (
            "The continuation is spent by a later scoped_commit success JSON with "
            "new_commit, or by a Task Ledger/Work Ledger residual that names the "
            "failed CAS packet, retry-budget state, and stop condition."
        ),
        "receipt_required": (
            {
                "closeout_state": "validated_uncommitted_git_metadata_blocked",
                "no_commit_reason": "parent_cas_retry_budget_exhausted",
                "required_fields": [
                    "expected_parent",
                    "current_head",
                    "changed_paths",
                    "recent_commits_preview",
                    "validation_refs",
                    "commit_blocker_refs",
                    "reentry_condition",
                ],
                "rule": (
                    "Do not launch a third ref mutation for the same evidence root; "
                    "bind the validated-uncommitted state and re-enter after a fresh "
                    "quiet-window, overlap, preflight, and validation check."
                ),
            }
            if retry_budget_exhausted
            else {}
        ),
    }


def _head_cas_failure(
    repo_root: Path,
    *,
    mode: str,
    branch_ref: str,
    parent_sha: str,
    commit_sha: str,
    tree_sha: str,
    scoped_evidence_sha: str,
    changed_paths: list[str],
    update_stderr: str,
    cas_retry_attempt: int = 0,
) -> HeadCasFailureError:
    evidence_root = _head_cas_evidence_root(
        mode=mode,
        branch_ref=branch_ref,
        scoped_evidence_sha=scoped_evidence_sha,
        changed_paths=changed_paths,
    )
    retry_memory = _head_cas_retry_memory_status(repo_root, evidence_root=evidence_root)
    caller_retry_attempt = max(0, int(cas_retry_attempt or 0))
    prior_failure_count = max(0, int(retry_memory.get("prior_failure_count") or 0))
    effective_retry_attempt = max(caller_retry_attempt, prior_failure_count)
    retry_memory["caller_supplied_retry_attempt"] = caller_retry_attempt
    retry_memory["effective_refresh_retry_attempt"] = effective_retry_attempt
    packet = _build_head_cas_retry_packet(
        repo_root,
        mode=mode,
        branch_ref=branch_ref,
        expected_parent=parent_sha,
        attempted_commit=commit_sha,
        attempted_tree=tree_sha,
        scoped_evidence_sha=scoped_evidence_sha,
        changed_paths=changed_paths,
        update_stderr=update_stderr,
        cas_retry_attempt=effective_retry_attempt,
        retry_memory=retry_memory,
    )
    record_receipt = _record_head_cas_memory_event(
        repo_root,
        event="cas_failure",
        evidence_root=evidence_root,
        mode=mode,
        branch_ref=branch_ref,
        tree_sha=tree_sha,
        scoped_evidence_sha=scoped_evidence_sha,
        changed_paths=changed_paths,
        expected_parent=parent_sha,
        current_head=str(packet.get("current_head") or ""),
        attempted_commit=commit_sha,
        status=str(packet.get("status") or ""),
        effective_retry_attempt=effective_retry_attempt,
    )
    packet["retry_memory"]["record_receipt"] = record_receipt
    return HeadCasFailureError(
        "scoped-commit: HEAD CAS failed; another actor advanced "
        f"{branch_ref} since parent {parent_sha[:8]} was captured. "
        "Retry only after refreshing HEAD, ownership, scoped diff, and validation. "
        f"Stderr: {update_stderr.strip()}",
        retry_packet=packet,
    )


def _record_head_cas_landed(
    repo_root: Path,
    *,
    mode: str,
    branch_ref: str,
    tree_sha: str,
    scoped_evidence_sha: str,
    commit_sha: str,
    changed_paths: list[str],
) -> dict[str, object]:
    evidence_root = _head_cas_evidence_root(
        mode=mode,
        branch_ref=branch_ref,
        scoped_evidence_sha=scoped_evidence_sha,
        changed_paths=changed_paths,
    )
    return _record_head_cas_memory_event(
        repo_root,
        event="landed",
        evidence_root=evidence_root,
        mode=mode,
        branch_ref=branch_ref,
        tree_sha=tree_sha,
        scoped_evidence_sha=scoped_evidence_sha,
        changed_paths=changed_paths,
        current_head=commit_sha,
        attempted_commit=commit_sha,
        status="landed",
    )


def _git_metadata_write_capability_for_commit(repo_root: Path) -> dict[str, object]:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from system.lib.git_state_snapshot import build_git_state_snapshot

    snapshot = build_git_state_snapshot(
        repo_root,
        path_limit=0,
        recent_limit=1,
        include_upstream=False,
        probe_git_metadata_write=True,
    )
    capability = snapshot.get("git_metadata_write")
    return dict(capability) if isinstance(capability, dict) else {}


def _assert_git_metadata_writeable(repo_root: Path, *, operation: str) -> None:
    capability = _git_metadata_write_capability_for_commit(repo_root)
    if capability.get("writable") is True:
        return

    status = capability.get("status") or "unknown"
    failure_class = capability.get("failure_class") or "unknown"
    repairs = capability.get("owner_repair_commands")
    first_repair = ""
    if isinstance(repairs, list) and repairs:
        first_repair = str(repairs[0])
    if not first_repair:
        first_repair = (
            "for exact full-path scopes with a stable --expected-parent, rerun "
            "with --remote-fallback-on-metadata-block; otherwise rerun the "
            "commit lane with explicit Git metadata authority"
        )
    privacy = capability.get("privacy") or "path_metadata_and_error_class_only_no_stdout_stderr_bodies"
    raise GitMetadataBlockedError(
        "scoped-commit: Git metadata writes are blocked before "
        f"{operation}; status={status}; failure_class={failure_class}; "
        "recommended_route=remote_full_paths_fallback_or_authorized_git_metadata; "
        "remote_fallback=full_paths_only_requires_expected_parent_and_push_authority; "
        f"repair={first_repair}; privacy={privacy}",
        capability=capability,
        operation=operation,
    )


def _shell_join(args: list[str]) -> str:
    return " ".join(shlex.quote(str(arg)) for arg in args)


def _remote_oid(repo_root: Path, remote_name: str, target_ref: str) -> str:
    res = _git(["ls-remote", remote_name, target_ref], cwd=repo_root)
    rows = [line.split() for line in res.stdout.splitlines() if line.strip()]
    if not rows:
        raise RuntimeError(
            "scoped-commit: remote fallback could not resolve target ref; "
            f"remote={remote_name}; target_ref={target_ref}"
        )
    return rows[0][0]


def _git_user_identity(repo_root: Path) -> dict[str, str]:
    name = _git(["config", "--get", "user.name"], cwd=repo_root, check=False).stdout.strip()
    email = _git(["config", "--get", "user.email"], cwd=repo_root, check=False).stdout.strip()
    return {
        "GIT_AUTHOR_NAME": name or "codex",
        "GIT_AUTHOR_EMAIL": email or "codex@example.invalid",
        "GIT_COMMITTER_NAME": name or "codex",
        "GIT_COMMITTER_EMAIL": email or "codex@example.invalid",
    }


def _copy_live_path_to_temp_repo(live_root: Path, temp_root: Path, rel: str) -> None:
    src = live_root / rel
    dst = temp_root / rel
    if dst.exists() or dst.is_symlink():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, symlinks=True)
    else:
        shutil.copy2(src, dst, follow_symlinks=False)


def _git_hunk_counts(repo_root: Path, parent: str, paths: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {rel: 0 for rel in paths}
    if not paths:
        return counts
    path_set = set(paths)
    res = _git(
        ["diff", "--cached", "--unified=0", parent, "--", *paths],
        cwd=repo_root,
    )
    current_path: str | None = None
    for line in res.stdout.splitlines():
        if line.startswith("diff --git "):
            current_path = _diff_git_target_path(line, path_set)
            continue
        if current_path and line.startswith("@@ "):
            counts[current_path] = counts.get(current_path, 0) + 1
    return counts


def _validate_patch_hunk_context(patch_path: Path) -> None:
    """Refuse context-free existing-file hunks that Git may apply at the wrong offset."""
    old_path: str | None = None
    new_path: str | None = None
    hunk_line: str | None = None
    hunk_has_context = False
    hunk_requires_context = False

    def finish_hunk() -> None:
        if hunk_line and hunk_requires_context and not hunk_has_context:
            raise ValueError(
                "scoped-commit: patch mode requires at least one context line "
                "for each existing-file hunk; regenerate the patch with "
                f"--unified=1 or higher. Offending hunk: {hunk_line}"
            )

    for raw_line in patch_path.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("diff --git "):
            finish_hunk()
            old_path = None
            new_path = None
            hunk_line = None
            hunk_has_context = False
            hunk_requires_context = False
            continue
        if raw_line.startswith("--- "):
            old_path = raw_line[4:].strip()
            continue
        if raw_line.startswith("+++ "):
            new_path = raw_line[4:].strip()
            continue
        if raw_line.startswith("@@ "):
            finish_hunk()
            hunk_line = raw_line
            hunk_has_context = False
            hunk_requires_context = old_path != "/dev/null" and new_path != "/dev/null"
            continue
        if hunk_line and raw_line.startswith(" "):
            hunk_has_context = True
    finish_hunk()


def _copy_declared_paths_into_remote_checkout(
    *,
    live_root: Path,
    temp_root: Path,
    declared_paths: list[str],
    allow_untracked: bool,
) -> list[str]:
    tracked_res = _git(["ls-files", "--", *declared_paths], cwd=temp_root)
    tracked_entries = _normalize_paths(tracked_res.stdout.splitlines())
    tracked_scope = _PathScopeMatcher(declared_paths)
    untracked_entries_by_path = (
        _untracked_entries_for_paths(live_root, declared_paths)
        if allow_untracked
        else {rel: [] for rel in declared_paths}
    )
    untracked_declared: list[str] = []
    for rel in declared_paths:
        if any(_path_within(entry, rel) for entry in tracked_entries):
            untracked_declared.extend(untracked_entries_by_path.get(rel) or [])
            continue
        if not (live_root / rel).exists():
            raise ValueError(
                f"scoped-commit: declared path does not exist in worktree: {rel}"
            )
        if not allow_untracked:
            raise ValueError(
                f"scoped-commit: path is untracked on remote base, pass --allow-untracked: {rel}"
            )
        untracked_declared.extend(untracked_entries_by_path.get(rel) or [rel])

    for rel in tracked_entries:
        if tracked_scope.contains(rel):
            _copy_live_path_to_temp_repo(live_root, temp_root, rel)
    for rel in untracked_declared:
        _copy_live_path_to_temp_repo(live_root, temp_root, rel)

    paths_to_stage = _normalize_paths([*tracked_entries, *untracked_declared])
    if paths_to_stage:
        for chunk in _git_path_chunks(paths_to_stage):
            _git(["add", "-A", "-f", "--", *chunk], cwd=temp_root)
    return paths_to_stage


def perform_remote_full_paths_landing(
    *,
    repo_root: Path,
    message: str,
    paths: list[str],
    remote_name: str = "origin",
    target_ref: str = "refs/heads/main",
    allow_untracked: bool = False,
    allow_multi_hunk_full_paths: bool = False,
    expected_parent: str | None = None,
    work_ledger_session_id: str | None = None,
    metadata_blocker: str | None = None,
) -> dict[str, object]:
    """Commit selected live worktree paths from a temp checkout and push exactly.

    This is the Git-metadata-blocked escape lane. It never writes the live
    repository's `.git` directory; it creates a temporary checkout, copies only
    the declared path contents from the live worktree, creates a commit on the
    current remote target ref, and pushes that exact object with a remote-ref
    CAS check.
    """
    declared_paths = _normalize_paths(paths)
    if not declared_paths:
        raise ValueError("scoped-commit: remote fallback requires at least one --path")
    if not message or not message.strip():
        raise ValueError("scoped-commit: commit message must be non-empty")
    if not expected_parent:
        raise ValueError(
            "scoped-commit: remote fallback requires --expected-parent. "
            "Use the live repo HEAD captured before the commit attempt; if "
            "the remote target ref does not match that parent, rerun from an "
            "authorized local Git lane instead of publishing a side branch of main."
        )
    _assert_scoped_commit_disk_headroom(
        repo_root,
        operation="remote full-paths fallback",
        paths=declared_paths,
    )

    remote_url = _git(["remote", "get-url", remote_name], cwd=repo_root).stdout.strip()
    if not remote_url:
        raise RuntimeError(f"scoped-commit: remote fallback could not resolve remote {remote_name!r}")
    base_remote_oid = _remote_oid(repo_root, remote_name, target_ref)
    if expected_parent and expected_parent != base_remote_oid:
        raise RuntimeError(
            "scoped-commit: remote fallback expected-parent mismatch; "
            f"expected_parent={expected_parent}; remote_oid={base_remote_oid}; "
            "rerun after auditing the current remote identity"
        )

    with tempfile.TemporaryDirectory(prefix="scoped_commit_remote_", dir="/private/tmp") as tmpdir:
        temp_repo = Path(tmpdir) / "repo"
        temp_repo.mkdir()
        _git(["init", "-q"], cwd=temp_repo)
        _git(["remote", "add", remote_name, remote_url], cwd=temp_repo)
        _git(["fetch", "--depth=1", remote_name, target_ref], cwd=temp_repo)
        _git(["checkout", "-q", "--detach", "FETCH_HEAD"], cwd=temp_repo)

        _copy_declared_paths_into_remote_checkout(
            live_root=repo_root,
            temp_root=temp_repo,
            declared_paths=declared_paths,
            allow_untracked=allow_untracked,
        )
        changed = _normalize_paths(
            _git(["diff", "--cached", "--name-only", base_remote_oid], cwd=temp_repo).stdout.splitlines()
        )
        if not changed:
            raise ValueError("scoped-commit: remote fallback produced no staged changes")
        declared_scope = _PathScopeMatcher(declared_paths)
        disallowed = [path for path in changed if not declared_scope.contains(path)]
        if disallowed:
            raise ValueError(
                "scoped-commit: remote fallback changed paths outside declared "
                f"--path set: changed={changed}, declared={declared_paths}, outside={disallowed}"
            )
        full_path_hunk_counts = _git_hunk_counts(temp_repo, base_remote_oid, changed)
        multi_hunk_paths = {
            path: count
            for path, count in full_path_hunk_counts.items()
            if count > 1
        }
        if multi_hunk_paths and not allow_multi_hunk_full_paths:
            raise ScopedCommitMultiHunkFullPathsError(
                "scoped-commit: remote fallback full-paths mode refuses multi-hunk "
                "file diffs by default because it commits every hunk in each declared "
                "path. Use patch mode in a Git-authorized lane for hunk-only ownership, "
                f"or pass --allow-multi-hunk-full-paths after verifying ownership: {multi_hunk_paths}",
                mode="remote-full-paths",
                multi_hunk_paths=multi_hunk_paths,
            )
        task_ledger_projection_guard = _assert_task_ledger_private_index_consistency(
            temp_repo,
            changed,
        )

        effective_work_ledger_session_id = work_ledger_session_id or _default_work_ledger_session_id()
        mutation_guard = _work_ledger_mutation_guard(
            repo_root,
            changed,
            session_id=effective_work_ledger_session_id,
        )

        tree_sha = _git(["write-tree"], cwd=temp_repo).stdout.strip()
        commit_sha = _git(
            ["commit-tree", tree_sha, "-p", base_remote_oid, "-m", message],
            cwd=temp_repo,
            env=_git_user_identity(repo_root),
        ).stdout.strip()

        remote_before_push = _remote_oid(repo_root, remote_name, target_ref)
        if remote_before_push != base_remote_oid:
            raise RuntimeError(
                "scoped-commit: remote fallback CAS failed before push; "
                f"target_ref={target_ref}; expected_remote={base_remote_oid}; "
                f"current_remote={remote_before_push}"
            )
        push_res = _git(
            ["push", remote_name, f"{commit_sha}:{target_ref}"],
            cwd=temp_repo,
            check=False,
        )
        push_failed_remote_already_at_source = False
        if push_res.returncode != 0:
            post_failure_remote = _remote_oid(repo_root, remote_name, target_ref)
            if post_failure_remote == commit_sha:
                push_failed_remote_already_at_source = True
            else:
                raise RuntimeError(
                    "scoped-commit: remote fallback push failed and remote did not reach source; "
                    f"target_ref={target_ref}; expected_source={commit_sha}; "
                    f"post_failure_remote={post_failure_remote}; stderr={push_res.stderr.strip()}"
                )
        post_push_remote = _remote_oid(repo_root, remote_name, target_ref)
        if post_push_remote != commit_sha:
            raise RuntimeError(
                "scoped-commit: remote fallback postcondition failed; "
                f"target_ref={target_ref}; expected_source={commit_sha}; "
                f"post_push_remote={post_push_remote}"
            )

    return {
        "mode": "remote-full-paths",
        "remote_fallback": True,
        "metadata_blocker": metadata_blocker or "",
        "parent": base_remote_oid,
        "branch_ref": target_ref,
        "changed_paths": changed,
        "full_path_hunk_counts": full_path_hunk_counts,
        "new_commit": commit_sha,
        "tree": tree_sha,
        "dry_run": False,
        "work_ledger_mutation_guard": mutation_guard,
        "work_ledger_closeout_hint": _work_ledger_closeout_hint(
            session_id=effective_work_ledger_session_id,
            commit_sha=commit_sha,
            changed_paths=changed,
            mode="remote-full-paths",
            remote_fallback=True,
            live_repo_head_unchanged=True,
        ),
        "task_ledger_projection_guard": task_ledger_projection_guard,
        "remote_name": remote_name,
        "target_ref": target_ref,
        "remote_sha_before_push": remote_before_push,
        "post_push_remote_sha": post_push_remote,
        "push_failed_remote_already_at_source": push_failed_remote_already_at_source,
        "live_repo_head_unchanged": True,
        "live_repo_git_metadata_written": False,
        "next_local_sync_hint": "Git metadata authority is required to update the live repo HEAD/tracking refs; remote publication is complete.",
    }


def _default_work_ledger_session_id() -> str:
    for name in WORK_LEDGER_SESSION_ENV_VARS:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return ""


def _post_commit_containment_command(
    *,
    commit_sha: str,
    changed_paths: list[str],
) -> str:
    scope_args = " ".join(
        f"--scope {shlex.quote(path)}" for path in _normalize_paths(changed_paths)
    )
    return (
        "./repo-python tools/meta/control/git_state_snapshot.py "
        f"--post-commit-containment --commit {shlex.quote(commit_sha)} "
        f"{scope_args}"
    ).strip()


def _post_commit_containment_finalize_args(
    *,
    commit_sha: str,
    changed_paths: list[str],
) -> str:
    normalized_paths = _normalize_paths(changed_paths)
    if not commit_sha or not normalized_paths:
        return ""
    scope_args = " ".join(
        f"--post-commit-containment-scope {shlex.quote(path)}"
        for path in normalized_paths
    )
    return (
        "--require-post-commit-containment "
        f"--post-commit-containment-commit {shlex.quote(commit_sha)} "
        f"{scope_args}"
    ).strip()


def _post_commit_containment_hint(
    *,
    commit_sha: str,
    changed_paths: list[str],
    remote_fallback: bool,
    live_repo_head_unchanged: bool,
) -> dict[str, object]:
    normalized_paths = _normalize_paths(changed_paths)
    command = _post_commit_containment_command(
        commit_sha=commit_sha,
        changed_paths=normalized_paths,
    )
    base: dict[str, object] = {
        "schema": "scoped_commit_post_commit_containment_hint_v0",
        "path_scope": normalized_paths,
        "expected_safe_fields": {
            "ok": True,
            "closeout_safe": True,
            "commit_contained_in_head": True,
        },
        "safe_statuses": [
            "contained_head_current_paths_clean",
            "contained_head_advanced_paths_unchanged",
        ],
    }
    if remote_fallback:
        status = (
            "deferred_remote_fallback_live_head_not_updated"
            if live_repo_head_unchanged
            else "deferred_remote_fallback"
        )
        return {
            **base,
            "status": status,
            "reason": (
                "remote fallback landed a commit outside the live repo HEAD update path; "
                "run local post-commit containment only after live Git metadata is synced "
                "to the published commit or its descendant"
            ),
            "required_before": "user_facing_closeout_after_local_sync",
            "command_after_local_sync": command,
        }
    return {
        **base,
        "status": "required_before_finalize",
        "reason": (
            "prove the landed commit is contained in current HEAD and declared owned "
            "paths are unchanged and clean before Work Ledger append-exempt finalization"
        ),
        "required_before": "append_exempt_session_finalize_template",
        "command": command,
    }


def _work_ledger_closeout_hint(
    *,
    session_id: str | None,
    commit_sha: str,
    changed_paths: list[str],
    mode: str,
    remote_fallback: bool = False,
    live_repo_head_unchanged: bool = False,
) -> dict[str, object]:
    owner_session_id = str(session_id or "").strip()
    if not owner_session_id:
        return {
            "schema": "scoped_commit_work_ledger_closeout_hint_v0",
            "status": "not_applicable",
            "reason": "no_work_ledger_session_id",
        }
    quoted_session = shlex.quote(owner_session_id)
    quoted_commit = shlex.quote(commit_sha)
    normalized_paths = _normalize_paths(changed_paths)
    owned_path_args = " ".join(
        f"--owned-path {shlex.quote(path)}" for path in normalized_paths
    )
    status = "required_after_remote_commit" if remote_fallback else "required_after_commit"
    work_landing_reconcile_template = (
        "./repo-python tools/meta/control/work_landing.py reconcile "
        "--subject-id <subject-id> "
        f"--session-id {quoted_session} "
        f"--commit-hash {quoted_commit} "
        f"{owned_path_args} "
        "--apply --only commit_and_closeout"
    ).strip()
    append_exempt_finalize_template = (
        "./repo-python tools/meta/factory/work_ledger.py session-finalize "
        f"--session-id {quoted_session} "
        "--action codex-turn-end "
        "--read-receipt-id <wlr_*> "
        "--append-exempt-reason scoped_commit_only_closeout "
        f"--append-exempt-ref {quoted_commit}"
    )
    containment_finalize_args = _post_commit_containment_finalize_args(
        commit_sha=commit_sha,
        changed_paths=normalized_paths,
    )
    if containment_finalize_args:
        append_exempt_finalize_template = (
            f"{append_exempt_finalize_template} {containment_finalize_args}"
        )
    post_commit_containment = _post_commit_containment_hint(
        commit_sha=commit_sha,
        changed_paths=normalized_paths,
        remote_fallback=remote_fallback,
        live_repo_head_unchanged=live_repo_head_unchanged,
    )
    direct_scoped_commit_closeout: dict[str, object] = {
        "requires_attempt_binding": False,
        "use_when": "the commit was landed directly by scoped_commit.py and no Work Landing attempt binding exists",
        "command": append_exempt_finalize_template,
    }
    containment_command = post_commit_containment.get("command")
    if isinstance(containment_command, str) and containment_command:
        direct_scoped_commit_closeout["precheck_command"] = containment_command
    else:
        direct_scoped_commit_closeout["precheck_status"] = post_commit_containment.get("status")
        command_after_sync = post_commit_containment.get("command_after_local_sync")
        if isinstance(command_after_sync, str) and command_after_sync:
            direct_scoped_commit_closeout["precheck_command_after_local_sync"] = command_after_sync

    hint: dict[str, object] = {
        "schema": "scoped_commit_work_ledger_closeout_hint_v0",
        "status": status,
        "reason": (
            "scoped_commit_writes_git_history_only; it does not record Task Ledger "
            "execution receipts, close Work Ledger threads, finalize sessions, or release claims"
        ),
        "session_id": owner_session_id,
        "commit_hash": commit_sha,
        "mode": mode,
        "changed_paths": normalized_paths,
        "live_repo_head_unchanged": live_repo_head_unchanged,
        "preferred_controller": "controller_selection_by_attempt_binding",
        "session_status_command": (
            "./repo-python tools/meta/factory/work_ledger.py session-status "
            f"--session-id {quoted_session} --detail compact"
        ),
        "post_commit_containment": post_commit_containment,
        "work_landing_reconcile_template": work_landing_reconcile_template,
        "append_exempt_session_finalize_template": append_exempt_finalize_template,
        "session_finalize_fallback_command": (
            "./repo-python tools/meta/factory/work_ledger.py session-finalize "
            f"--session-id {quoted_session}"
        ),
        "controller_selection": {
            "work_landing_reconcile": {
                "requires_attempt_binding": True,
                "use_when": "a Work Landing begin/attempt binding already exists for the subject and session",
                "command": work_landing_reconcile_template,
            },
            "direct_scoped_commit_closeout": direct_scoped_commit_closeout,
        },
        "rules": [
            "after a successful scoped commit, run Work Landing reconcile only when a Work Landing begin/attempt binding exists",
            "for direct scoped_commit-only closeout with no attempt binding, use append_exempt_session_finalize_template and do not follow with bare session-finalize",
            "use the session status command to verify active_claim_count reaches 0",
            "do not describe source work as fully closed while the session still has active claims",
            "append_exempt_session_finalize_template carries the post-commit containment guard; standalone post_commit_containment_command receipts remain inspectable proof for user-facing closeout",
        ],
    }
    if isinstance(containment_command, str) and containment_command:
        hint["post_commit_containment_command"] = containment_command
    else:
        command_after_sync = post_commit_containment.get("command_after_local_sync")
        if isinstance(command_after_sync, str) and command_after_sync:
            hint["post_commit_containment_command_after_local_sync"] = command_after_sync
    return hint


def _work_ledger_mutation_guard(
    repo_root: Path,
    paths: list[str],
    *,
    session_id: str | None = None,
) -> dict[str, object]:
    requested_paths = _normalize_paths(paths)
    if not requested_paths:
        return {
            "schema": "scoped_commit_work_ledger_mutation_guard_v0",
            "status": "skipped",
            "reason": "no_changed_paths",
            "paths": [],
            "collision_count": 0,
            "collisions": [],
        }
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from system.lib import work_ledger_runtime

    owner_session_id = str(session_id or "").strip()
    collisions = work_ledger_runtime.active_claim_collisions_for_paths(
        repo_root,
        requested_paths,
        session_id=owner_session_id or None,
    )
    payload: dict[str, object] = {
        "schema": "scoped_commit_work_ledger_mutation_guard_v0",
        "status": "blocked" if collisions else "clear",
        "safety_authority": "work_ledger_active_claims_snapshot",
        "require_exclusive": True,
        "paths": requested_paths,
        "session_id": owner_session_id,
        "collision_count": len(collisions),
        "collisions": collisions,
    }
    if collisions:
        first = collisions[0]
        raise RuntimeError(
            "scoped-commit: Work Ledger active claim overlap; "
            f"requested_path={first.get('requested_path')}; "
            f"claim_path={first.get('claim_path')}; "
            f"claim_id={first.get('claim_id')}; "
            f"owner_session_id={first.get('session_id')}; "
            "rerun with the owning Work Ledger session id only if this "
            "actor owns the active claim, or wait for/release/finalize the owner claim"
        )
    return payload


def _capture_parent(repo_root: Path) -> str:
    return _git(["rev-parse", "HEAD"], cwd=repo_root).stdout.strip()


def _current_branch_ref(repo_root: Path, *, allow_detached: bool) -> str:
    res = _git(
        ["symbolic-ref", "--quiet", "HEAD"],
        cwd=repo_root,
        check=False,
    )
    if res.returncode == 0:
        return res.stdout.strip()
    if allow_detached:
        return "HEAD"
    raise RuntimeError(
        "scoped-commit: HEAD is detached; pass --allow-detached to commit anyway"
    )


@contextmanager
def _scoped_commit_landing_lock(
    repo_root: Path,
    *,
    enabled: bool,
) -> Iterator[dict[str, object]]:
    """Serialize local parent-capture-to-update-ref landing windows."""
    if not enabled:
        yield {
            "schema": "scoped_commit_landing_lock_v0",
            "status": "skipped",
            "reason": "dry_run",
        }
        return

    lock_path_raw = _git(
        ["rev-parse", "--git-path", "aiw_scoped_commit.lock"],
        cwd=repo_root,
    ).stdout.strip()
    lock_path = Path(lock_path_raw)
    if not lock_path.is_absolute():
        lock_path = repo_root / lock_path
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield {
                "schema": "scoped_commit_landing_lock_v0",
                "status": "held",
                "lock_path": str(lock_path),
            }
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _changed_paths_in_private_index(repo_root: Path, index_file: Path, parent: str) -> list[str]:
    res = _git(
        ["diff-index", "--cached", "--name-only", parent],
        cwd=repo_root,
        env={"GIT_INDEX_FILE": str(index_file)},
    )
    return [line for line in res.stdout.splitlines() if line]


def _private_index_hunk_counts(
    repo_root: Path,
    index_file: Path,
    parent: str,
    paths: list[str],
) -> dict[str, int]:
    counts: dict[str, int] = {rel: 0 for rel in paths}
    if not paths:
        return counts
    path_set = set(paths)

    res = _git(
        ["diff-index", "--cached", "--unified=0", parent, "--", *paths],
        cwd=repo_root,
        env={"GIT_INDEX_FILE": str(index_file)},
    )
    current_path: str | None = None
    for line in res.stdout.splitlines():
        if line.startswith("diff --git "):
            current_path = _diff_git_target_path(line, path_set)
            continue
        if current_path and line.startswith("@@ "):
            counts[current_path] = counts.get(current_path, 0) + 1
    return counts


def _index_blob_text(
    repo_root: Path,
    rel: str,
    *,
    env: dict[str, str] | None = None,
) -> str | None:
    res = _git(["show", f":{rel}"], cwd=repo_root, env=env, check=False)
    if res.returncode != 0:
        return None
    return res.stdout


def _task_ledger_event_log_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def _task_ledger_projection_event_count(text: str) -> int:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "scoped-commit: Task Ledger projection guard could not parse "
            "state/task_ledger/ledger.json from the private index"
        ) from exc
    count = payload.get("event_count")
    if not isinstance(count, int):
        raise ValueError(
            "scoped-commit: Task Ledger projection guard requires integer "
            "state/task_ledger/ledger.json::event_count"
        )
    return count


def _assert_task_ledger_private_index_consistency(
    repo_root: Path,
    changed_paths: list[str],
    *,
    env: dict[str, str] | None = None,
) -> dict[str, object]:
    relevant = [
        path for path in changed_paths
        if path == "state/task_ledger/events.jsonl"
        or path == "state/task_ledger/ledger.json"
        or path == "state/task_ledger/sign_offs.json"
        or path.startswith("state/task_ledger/views/")
    ]
    if not relevant:
        return {
            "schema": "scoped_commit_task_ledger_projection_guard_v0",
            "status": "not_applicable",
        }

    events_text = _index_blob_text(
        repo_root,
        "state/task_ledger/events.jsonl",
        env=env,
    )
    ledger_text = _index_blob_text(
        repo_root,
        "state/task_ledger/ledger.json",
        env=env,
    )
    if events_text is None or ledger_text is None:
        raise ValueError(
            "scoped-commit: Task Ledger projection guard requires both "
            "state/task_ledger/events.jsonl and state/task_ledger/ledger.json "
            "in the staged private index"
        )

    authority_event_count = _task_ledger_event_log_count(events_text)
    projection_event_count = _task_ledger_projection_event_count(ledger_text)
    receipt = {
        "schema": "scoped_commit_task_ledger_projection_guard_v0",
        "status": "clean",
        "authority_event_count": authority_event_count,
        "projection_event_count": projection_event_count,
        "checked_path_count": len(relevant),
    }
    if authority_event_count != projection_event_count:
        raise ValueError(
            "scoped-commit: Task Ledger event_count mismatch in private index; "
            f"authority_event_count={authority_event_count}; "
            f"projection_event_count={projection_event_count}; "
            "rerun `./repo-python tools/meta/factory/task_ledger_apply.py rebuild` "
            "after the last Task Ledger append, then rerun the scoped commit"
        )
    return receipt


def _assert_task_ledger_monolith_not_committed(changed_paths: list[str]) -> dict[str, object]:
    if "state/task_ledger/events.jsonl" not in changed_paths:
        return {
            "schema": "scoped_commit_task_ledger_monolith_guard_v0",
            "status": "not_applicable",
        }
    if os.environ.get(TASK_LEDGER_MONOLITH_COMMIT_OVERRIDE_ENV) == "1":
        return {
            "schema": "scoped_commit_task_ledger_monolith_guard_v0",
            "status": "override_allowed",
            "override_env": TASK_LEDGER_MONOLITH_COMMIT_OVERRIDE_ENV,
        }
    raise ValueError(
        "scoped-commit: refusing to commit state/task_ledger/events.jsonl as a "
        "monolithic authority file. Use the Task Ledger authority migration/"
        f"settlement lane, or set {TASK_LEDGER_MONOLITH_COMMIT_OVERRIDE_ENV}=1 "
        "only with an explicit migration/settlement receipt."
    )


def _diff_git_target_path(line: str, path_set: set[str]) -> str | None:
    prefix = "diff --git "
    if not line.startswith(prefix):
        return None
    rest = line[len(prefix):]
    marker = " b/"
    if marker not in rest:
        return None
    candidate = rest.split(marker, 1)[1]
    return candidate if candidate in path_set else None


def _shared_index_changed_paths(repo_root: Path, paths: list[str]) -> set[str]:
    if not paths:
        return set()
    res = _git(
        ["diff", "--cached", "--name-only", "--", *paths],
        cwd=repo_root,
    )
    return {line for line in res.stdout.splitlines() if line}


def _tree_blob_for_path(repo_root: Path, treeish: str, rel: str) -> str | None:
    res = _git(
        ["rev-parse", "-q", "--verify", f"{treeish}:{rel}"],
        cwd=repo_root,
        check=False,
    )
    if res.returncode != 0:
        return None
    return res.stdout.strip() or None


def _shared_index_blob_for_path(repo_root: Path, rel: str) -> tuple[bool, str | None]:
    res = _git(
        ["ls-files", "-s", "--", rel],
        cwd=repo_root,
        check=False,
    )
    if res.returncode != 0:
        return False, None
    entries: list[str | None] = []
    for line in res.stdout.splitlines():
        try:
            head, path = line.split("\t", 1)
            _mode, blob, stage = head.split()
        except ValueError:
            return False, None
        if path != rel or stage != "0":
            return False, None
        entries.append(blob)
    if not entries:
        return True, None
    if len(entries) != 1:
        return False, None
    return True, entries[0]


def _normalize_paths(paths: list[str]) -> list[str]:
    return sorted({Path(p).as_posix() for p in paths if p})


class _PathScopeMatcher:
    """Resolve changed paths to the narrowest declared repo-relative scope."""

    def __init__(self, roots: list[str]) -> None:
        self._roots = {Path(root).as_posix().strip("/") for root in roots if root}

    def owner_for(self, path: str) -> str | None:
        token = Path(path).as_posix().strip("/")
        if not token or token == ".":
            return None
        current = token
        while current and current != ".":
            if current in self._roots:
                return current
            parent = PurePosixPath(current).parent.as_posix()
            if parent == current:
                break
            current = parent
        return None

    def contains(self, path: str) -> bool:
        return self.owner_for(path) is not None


def _tracked_entries_for_path(repo_root: Path, rel: str) -> list[str]:
    res = _git(
        ["ls-files", "--", rel],
        cwd=repo_root,
    )
    return [line for line in res.stdout.splitlines() if line]


def _tracked_entries_for_paths(repo_root: Path, rels: list[str]) -> dict[str, list[str]]:
    if not rels:
        return {}
    res = _git(
        ["ls-files", "--", *rels],
        cwd=repo_root,
    )
    rows = {rel: [] for rel in rels}
    matcher = _PathScopeMatcher(rels)
    for entry in res.stdout.splitlines():
        owner = matcher.owner_for(entry)
        if owner is None:
            continue
        rows[owner].append(entry)
    return rows


def _untracked_entries_for_paths(repo_root: Path, rels: list[str]) -> dict[str, list[str]]:
    rows = {rel: [] for rel in rels}
    if not rels:
        return rows
    res = _git(
        ["ls-files", "--others", "--exclude-standard", "--", *rels],
        cwd=repo_root,
    )
    matcher = _PathScopeMatcher(rels)
    for entry in res.stdout.splitlines():
        owner = matcher.owner_for(entry)
        if owner is None:
            continue
        rows[owner].append(entry)
    return rows


def _changed_tracked_entries_for_paths(
    repo_root: Path,
    parent: str,
    rels: list[str],
) -> dict[str, list[str]]:
    if not rels:
        return {}
    res = _git(
        ["diff", "--name-only", parent, "--", *rels],
        cwd=repo_root,
    )
    rows = {rel: [] for rel in rels}
    matcher = _PathScopeMatcher(rels)
    for entry in res.stdout.splitlines():
        owner = matcher.owner_for(entry)
        if owner is None:
            continue
        rows[owner].append(entry)
    return rows


def _git_path_chunks(paths: list[str], *, chunk_size: int = 500) -> list[list[str]]:
    if not paths:
        return []
    return [paths[index:index + chunk_size] for index in range(0, len(paths), chunk_size)]


def _path_within(path: str, root: str) -> bool:
    token = Path(path).as_posix().strip("/")
    prefix = Path(root).as_posix().strip("/")
    return bool(prefix) and (token == prefix or token.startswith(prefix + "/"))


def _changed_path_allowed_by_scope(
    changed_path: str,
    *,
    declared_paths: list[str],
    removal_paths: list[str],
) -> bool:
    return any(_path_within(changed_path, root) for root in declared_paths) or any(
        _path_within(changed_path, root)
        for root in removal_paths
    )


def _validate_scoped_commit_request(
    *,
    message: str,
    paths: list[str] | None,
    patch_path: Path | None,
) -> None:
    if patch_path is None and not paths:
        raise ValueError(
            "scoped-commit: full-paths mode requires at least one --path "
            "(or supply --patch-file to use patch mode)"
        )
    if not message or not message.strip():
        raise ValueError("scoped-commit: commit message must be non-empty")


def perform_scoped_commit(
    *,
    repo_root: Path,
    message: str,
    paths: list[str] | None = None,
    patch_path: Path | None = None,
    allow_detached: bool = False,
    allow_untracked: bool = False,
    allow_multi_hunk_full_paths: bool = False,
    collect_full_path_hunk_counts: bool = True,
    dry_run: bool = False,
    expected_parent: str | None = None,
    work_ledger_session_id: str | None = None,
    cas_retry_attempt: int = 0,
) -> dict[str, object]:
    _validate_scoped_commit_request(
        message=message,
        paths=paths,
        patch_path=patch_path,
    )
    if not dry_run:
        _assert_git_metadata_writeable(
            repo_root,
            operation="private-index scoped commit",
        )
    with _scoped_commit_landing_lock(repo_root, enabled=not dry_run) as landing_lock:
        return _perform_scoped_commit_locked(
            repo_root=repo_root,
            message=message,
            paths=paths,
            patch_path=patch_path,
            allow_detached=allow_detached,
            allow_untracked=allow_untracked,
            allow_multi_hunk_full_paths=allow_multi_hunk_full_paths,
            collect_full_path_hunk_counts=collect_full_path_hunk_counts,
            dry_run=dry_run,
            expected_parent=expected_parent,
            work_ledger_session_id=work_ledger_session_id,
            cas_retry_attempt=cas_retry_attempt,
            metadata_prechecked=True,
            landing_lock=landing_lock,
        )


def _perform_scoped_commit_locked(
    *,
    repo_root: Path,
    message: str,
    paths: list[str] | None = None,
    patch_path: Path | None = None,
    allow_detached: bool = False,
    allow_untracked: bool = False,
    allow_multi_hunk_full_paths: bool = False,
    collect_full_path_hunk_counts: bool = True,
    dry_run: bool = False,
    expected_parent: str | None = None,
    work_ledger_session_id: str | None = None,
    cas_retry_attempt: int = 0,
    metadata_prechecked: bool = False,
    landing_lock: dict[str, object] | None = None,
) -> dict[str, object]:
    """Perform a single scoped commit through a private index.

    Exactly one of ``paths`` (full-paths mode) or ``patch_path`` (patch
    mode) must be supplied.

    Returns a result dict describing the operation: parent, new_commit
    (or None on dry_run), tree, branch_ref, changed_paths, mode, and
    refresh_count when full-paths mode refreshed the shared index.
    """
    # Mode is determined by whether a patch_path is supplied:
    #   - patch_path is None    -> full-paths mode (paths required)
    #   - patch_path is not None -> patch mode (paths optional, acts as declared filter)
    _validate_scoped_commit_request(
        message=message,
        paths=paths,
        patch_path=patch_path,
    )
    if not dry_run and not metadata_prechecked:
        _assert_git_metadata_writeable(
            repo_root,
            operation="private-index scoped commit",
        )

    branch_ref = _current_branch_ref(repo_root, allow_detached=allow_detached)
    parent_sha = expected_parent or _capture_parent(repo_root)

    declared_paths: list[str] = (
        _normalize_paths(paths) if paths is not None else []
    )
    if not dry_run:
        headroom_paths = declared_paths
        if patch_path is not None:
            headroom_paths = [str(patch_path)]
        _assert_scoped_commit_disk_headroom(
            repo_root,
            operation="private-index scoped commit",
            paths=headroom_paths,
        )

    with tempfile.TemporaryDirectory(prefix="scoped_commit_") as tmpdir:
        index_file = Path(tmpdir) / "private_index"
        env = {"GIT_INDEX_FILE": str(index_file)}

        # Initialize private index from the captured parent.
        _git(["read-tree", parent_sha], cwd=repo_root, env=env)

        if patch_path is None:
            # full-paths mode: stage the exact worktree contents of the
            # declared paths into the private index.
            tracked_entries_by_path = _tracked_entries_for_paths(repo_root, declared_paths)
            changed_tracked_entries_by_path = _changed_tracked_entries_for_paths(
                repo_root,
                parent_sha,
                declared_paths,
            )
            untracked_entries_by_path = (
                _untracked_entries_for_paths(repo_root, declared_paths)
                if allow_untracked
                else {rel: [] for rel in declared_paths}
            )
            tracked_entries_to_stage: list[str] = []
            untracked_paths_to_stage: list[str] = []
            for rel in declared_paths:
                target = repo_root / rel
                if not target.exists():
                    raise ValueError(
                        f"scoped-commit: declared path does not exist in worktree: {rel}"
                    )
                tracked_entries = tracked_entries_by_path.get(rel) or []
                if tracked_entries:
                    # Private indexes do not treat tracked files under ignored
                    # directories as already tracked for `git add`'s ignore
                    # check. Force only the tracked entries so ignored
                    # untracked siblings are not swept into the commit.
                    tracked_entries_to_stage.extend(
                        changed_tracked_entries_by_path.get(rel) or []
                    )
                    untracked_paths_to_stage.extend(
                        untracked_entries_by_path.get(rel) or []
                    )
                else:
                    if not allow_untracked:
                        raise ValueError(
                            f"scoped-commit: path is untracked, pass --allow-untracked: {rel}"
                        )
                    untracked_paths_to_stage.extend(
                        untracked_entries_by_path.get(rel) or [rel]
                    )
            for chunk in _git_path_chunks(_normalize_paths(tracked_entries_to_stage)):
                _git(["add", "-f", "--", *chunk], cwd=repo_root, env=env)
            for chunk in _git_path_chunks(untracked_paths_to_stage):
                _git(["add", "-f", "--", *chunk], cwd=repo_root, env=env)
        else:
            # patch mode: apply the unified diff against the private index.
            assert patch_path is not None
            if not patch_path.is_file():
                raise ValueError(f"scoped-commit: patch file not found: {patch_path}")
            _validate_patch_hunk_context(patch_path)
            # --cached so the patch updates only the private index, never the worktree.
            _git(
                ["apply", "--cached", str(patch_path)],
                cwd=repo_root,
                env=env,
            )

        changed = _normalize_paths(_changed_paths_in_private_index(repo_root, index_file, parent_sha))
        preexisting_shared_staged_paths: set[str] = set()
        if patch_path is not None:
            preexisting_shared_staged_paths = _shared_index_changed_paths(repo_root, changed)

        full_path_hunk_counts: dict[str, int] = {}
        if patch_path is None:
            if not changed:
                raise ValueError("scoped-commit: full-paths produced no staged changes")
            declared_scope = _PathScopeMatcher(declared_paths)
            disallowed = [
                path
                for path in changed
                if not declared_scope.contains(path)
            ]
            if disallowed:
                raise ValueError(
                    "scoped-commit: private-index changed paths outside declared "
                    f"--path set: changed={changed}, declared={declared_paths}, "
                    f"outside={disallowed}"
                )
            if collect_full_path_hunk_counts or not allow_multi_hunk_full_paths:
                full_path_hunk_counts = _private_index_hunk_counts(
                    repo_root,
                    index_file,
                    parent_sha,
                    changed,
                )
            multi_hunk_paths = {
                path: count
                for path, count in full_path_hunk_counts.items()
                if count > 1
            }
            if multi_hunk_paths and not allow_multi_hunk_full_paths:
                raise ScopedCommitMultiHunkFullPathsError(
                    "scoped-commit: full-paths mode refuses multi-hunk "
                    "file diffs by default because it commits every hunk "
                    "in each declared path. Use patch mode for hunk-only "
                    "ownership, or pass --allow-multi-hunk-full-paths only "
                    f"after verifying all hunks are owned: {multi_hunk_paths}",
                    mode="full-paths",
                    multi_hunk_paths=multi_hunk_paths,
                )
        else:
            if not changed:
                raise ValueError("scoped-commit: patch produced no staged changes")
            if declared_paths and changed != declared_paths:
                raise ValueError(
                    "scoped-commit: patch touches paths outside declared --path set: "
                    f"changed={changed}, declared={declared_paths}"
                )

        mode_label = "full-paths" if patch_path is None else "patch"
        task_ledger_projection_guard = _assert_task_ledger_private_index_consistency(
            repo_root,
            changed,
            env=env,
        )
        task_ledger_monolith_guard = _assert_task_ledger_monolith_not_committed(changed)
        effective_work_ledger_session_id = (
            "" if dry_run else work_ledger_session_id or _default_work_ledger_session_id()
        )

        mutation_guard = (
            {
                "schema": "scoped_commit_work_ledger_mutation_guard_v0",
                "status": "skipped",
                "reason": "dry_run",
                "paths": changed,
                "collision_count": 0,
                "collisions": [],
            }
            if dry_run
            else _work_ledger_mutation_guard(
                repo_root,
                changed,
                session_id=effective_work_ledger_session_id,
            )
        )

        if dry_run:
            return {
                "mode": mode_label,
                "parent": parent_sha,
                "branch_ref": branch_ref,
                "changed_paths": changed,
                "full_path_hunk_counts": full_path_hunk_counts if patch_path is None else {},
                "new_commit": None,
                "tree": None,
                "dry_run": True,
                "landing_lock": landing_lock or {},
                "work_ledger_mutation_guard": mutation_guard,
                "task_ledger_projection_guard": task_ledger_projection_guard,
                "task_ledger_monolith_guard": task_ledger_monolith_guard,
            }

        scoped_evidence_sha = _private_index_scoped_evidence_sha(
            repo_root,
            changed,
            env=env,
        )
        tree_sha = _git(["write-tree"], cwd=repo_root, env=env).stdout.strip()
        commit_sha = _git(
            ["commit-tree", tree_sha, "-p", parent_sha, "-m", message],
            cwd=repo_root,
        ).stdout.strip()

        # CAS update: succeeds only if HEAD still points at parent_sha.
        update_res = _git(
            ["update-ref", branch_ref, commit_sha, parent_sha],
            cwd=repo_root,
            check=False,
        )
        if update_res.returncode != 0:
            raise _head_cas_failure(
                repo_root,
                mode=mode_label,
                branch_ref=branch_ref,
                parent_sha=parent_sha,
                commit_sha=commit_sha,
                tree_sha=tree_sha,
                scoped_evidence_sha=scoped_evidence_sha,
                changed_paths=changed,
                update_stderr=update_res.stderr,
                cas_retry_attempt=cas_retry_attempt,
            )

        head_cas_retry_memory = _record_head_cas_landed(
            repo_root,
            mode=mode_label,
            branch_ref=branch_ref,
            tree_sha=tree_sha,
            scoped_evidence_sha=scoped_evidence_sha,
            commit_sha=commit_sha,
            changed_paths=changed,
        )
        refreshed = 0
        skipped_refresh_paths: list[dict[str, str]] = []
        if patch_path is None:
            # In full-paths mode the worktree equals the new HEAD for the
            # committed paths.  Sync the shared index entries for those
            # paths to the new HEAD via `git reset HEAD -- <path>`, which
            # works correctly even for paths that were untracked before
            # this commit (`git update-index -- <path>` silently no-ops on
            # untracked entries, leaving the shared index reporting them as
            # both "deleted" against HEAD and "untracked" against worktree).
            # In patch mode we leave the shared index alone — the worktree
            # may legitimately have additional dirt the operator wants
            # preserved.
            for chunk in _git_path_chunks(changed):
                _git(["reset", "HEAD", "--", *chunk], cwd=repo_root, check=False)
                refreshed += len(chunk)
        else:
            # Patch mode can leave the shared index holding the old parent
            # entry for a committed path.  Once HEAD advances, that stale
            # entry appears as an inverse staged hunk.  Refresh only paths
            # that were not already staged and whose current shared-index
            # entry still matches the captured parent, so we do not erase
            # someone else's intentional same-file staging.
            for rel in changed:
                if rel in preexisting_shared_staged_paths:
                    skipped_refresh_paths.append(
                        {"path": rel, "reason": "preexisting_shared_index_entry"}
                    )
                    continue
                index_safe, index_blob = _shared_index_blob_for_path(repo_root, rel)
                parent_blob = _tree_blob_for_path(repo_root, parent_sha, rel)
                if index_safe and index_blob == parent_blob:
                    _git(["reset", "HEAD", "--", rel], cwd=repo_root, check=False)
                    refreshed += 1
                else:
                    skipped_refresh_paths.append(
                        {
                            "path": rel,
                            "reason": "shared_index_no_longer_matches_parent",
                        }
                    )

    return {
        "mode": mode_label,
        "parent": parent_sha,
        "branch_ref": branch_ref,
        "changed_paths": changed,
        "full_path_hunk_counts": full_path_hunk_counts if patch_path is None else {},
        "new_commit": commit_sha,
        "tree": tree_sha,
        "scoped_evidence_sha": scoped_evidence_sha,
        "dry_run": False,
        "landing_lock": landing_lock or {},
        "work_ledger_mutation_guard": mutation_guard,
        "head_cas_retry_memory": head_cas_retry_memory,
        "work_ledger_closeout_hint": _work_ledger_closeout_hint(
            session_id=effective_work_ledger_session_id,
            commit_sha=commit_sha,
            changed_paths=changed,
            mode=mode_label,
        ),
        "task_ledger_projection_guard": task_ledger_projection_guard,
        "task_ledger_monolith_guard": task_ledger_monolith_guard,
        "refresh_count": refreshed,
        "skipped_refresh_paths": skipped_refresh_paths,
    }


def _validate_tracked_removals_request(
    *,
    message: str,
    remove_paths: list[str],
) -> None:
    if not _normalize_paths(remove_paths or []):
        raise ValueError("scoped-commit: tracked-removals requires at least one --remove-path")
    if not message or not message.strip():
        raise ValueError("scoped-commit: commit message must be non-empty")


def perform_tracked_removals_commit(
    *,
    repo_root: Path,
    message: str,
    remove_paths: list[str],
    paths: list[str] | None = None,
    allow_detached: bool = False,
    allow_untracked: bool = False,
    dry_run: bool = False,
    expected_parent: str | None = None,
    work_ledger_session_id: str | None = None,
    cas_retry_attempt: int = 0,
) -> dict[str, object]:
    _validate_tracked_removals_request(
        message=message,
        remove_paths=remove_paths,
    )
    if not dry_run:
        _assert_git_metadata_writeable(
            repo_root,
            operation="private-index tracked-removals commit",
        )
    with _scoped_commit_landing_lock(repo_root, enabled=not dry_run) as landing_lock:
        return _perform_tracked_removals_commit_locked(
            repo_root=repo_root,
            message=message,
            remove_paths=remove_paths,
            paths=paths,
            allow_detached=allow_detached,
            allow_untracked=allow_untracked,
            dry_run=dry_run,
            expected_parent=expected_parent,
            work_ledger_session_id=work_ledger_session_id,
            cas_retry_attempt=cas_retry_attempt,
            metadata_prechecked=True,
            landing_lock=landing_lock,
        )


def _perform_tracked_removals_commit_locked(
    *,
    repo_root: Path,
    message: str,
    remove_paths: list[str],
    paths: list[str] | None = None,
    allow_detached: bool = False,
    allow_untracked: bool = False,
    dry_run: bool = False,
    expected_parent: str | None = None,
    work_ledger_session_id: str | None = None,
    cas_retry_attempt: int = 0,
    metadata_prechecked: bool = False,
    landing_lock: dict[str, object] | None = None,
) -> dict[str, object]:
    """Commit index-only tracked removals plus optional worktree paths.

    The removal operation is `git rm --cached` in a private index.  It never
    deletes working-tree files, which lets a follow-up ignore rule hide the
    now-untracked build output after HEAD advances.
    """
    declared_paths = _normalize_paths(paths or [])
    removal_paths = _normalize_paths(remove_paths or [])
    _validate_tracked_removals_request(
        message=message,
        remove_paths=removal_paths,
    )
    if not dry_run and not metadata_prechecked:
        _assert_git_metadata_writeable(
            repo_root,
            operation="private-index tracked-removals commit",
        )

    branch_ref = _current_branch_ref(repo_root, allow_detached=allow_detached)
    parent_sha = expected_parent or _capture_parent(repo_root)

    with tempfile.TemporaryDirectory(prefix="scoped_commit_") as tmpdir:
        index_file = Path(tmpdir) / "private_index"
        env = {"GIT_INDEX_FILE": str(index_file)}

        _git(["read-tree", parent_sha], cwd=repo_root, env=env)

        tracked_removed: list[str] = []
        for rel in removal_paths:
            tracked_entries = _tracked_entries_for_path(repo_root, rel)
            tracked_removed.extend(tracked_entries)
            if tracked_entries:
                _git(["rm", "--cached", "-r", "--ignore-unmatch", "--", rel], cwd=repo_root, env=env)

        for rel in declared_paths:
            target = repo_root / rel
            if not target.exists():
                raise ValueError(
                    f"scoped-commit: declared path does not exist in worktree: {rel}"
                )
            tracked_entries = _tracked_entries_for_path(repo_root, rel)
            if tracked_entries:
                _git(["add", "-f", "--", *tracked_entries], cwd=repo_root, env=env)
            else:
                if not allow_untracked:
                    raise ValueError(
                        f"scoped-commit: path is untracked, pass --allow-untracked: {rel}"
                    )
                _git(["add", "-f", "--", rel], cwd=repo_root, env=env)

        changed = _normalize_paths(_changed_paths_in_private_index(repo_root, index_file, parent_sha))
        if not changed:
            raise ValueError("scoped-commit: tracked-removals produced no staged changes")
        disallowed = [
            path for path in changed
            if not _changed_path_allowed_by_scope(
                path,
                declared_paths=declared_paths,
                removal_paths=removal_paths,
            )
        ]
        if disallowed:
            raise ValueError(
                "scoped-commit: tracked-removals touched paths outside declared scope: "
                f"{disallowed[:20]}"
            )
        removed_changed = [
            path for path in changed
            if any(_path_within(path, root) for root in removal_paths)
        ]
        if not removed_changed:
            raise ValueError(
                "scoped-commit: no tracked entries were removed; check --remove-path"
            )

        effective_work_ledger_session_id = (
            "" if dry_run else work_ledger_session_id or _default_work_ledger_session_id()
        )
        mutation_guard = (
            {
                "schema": "scoped_commit_work_ledger_mutation_guard_v0",
                "status": "skipped",
                "reason": "dry_run",
                "paths": changed,
                "collision_count": 0,
                "collisions": [],
            }
            if dry_run
            else _work_ledger_mutation_guard(
                repo_root,
                changed,
                session_id=effective_work_ledger_session_id,
            )
        )

        if dry_run:
            return {
                "mode": "tracked-removals",
                "parent": parent_sha,
                "branch_ref": branch_ref,
                "changed_path_count": len(changed),
                "changed_paths_preview": changed[:25],
                "removed_path_count": len(removed_changed),
                "tracked_entries_matched": len(set(tracked_removed)),
                "new_commit": None,
                "tree": None,
                "dry_run": True,
                "landing_lock": landing_lock or {},
                "work_ledger_mutation_guard": mutation_guard,
            }

        scoped_evidence_sha = _private_index_scoped_evidence_sha(
            repo_root,
            changed,
            env=env,
        )
        tree_sha = _git(["write-tree"], cwd=repo_root, env=env).stdout.strip()
        commit_sha = _git(
            ["commit-tree", tree_sha, "-p", parent_sha, "-m", message],
            cwd=repo_root,
        ).stdout.strip()

        update_res = _git(
            ["update-ref", branch_ref, commit_sha, parent_sha],
            cwd=repo_root,
            check=False,
        )
        if update_res.returncode != 0:
            raise _head_cas_failure(
                repo_root,
                mode="tracked-removals",
                branch_ref=branch_ref,
                parent_sha=parent_sha,
                commit_sha=commit_sha,
                tree_sha=tree_sha,
                scoped_evidence_sha=scoped_evidence_sha,
                changed_paths=changed,
                update_stderr=update_res.stderr,
                cas_retry_attempt=cas_retry_attempt,
            )

        head_cas_retry_memory = _record_head_cas_landed(
            repo_root,
            mode="tracked-removals",
            branch_ref=branch_ref,
            tree_sha=tree_sha,
            scoped_evidence_sha=scoped_evidence_sha,
            commit_sha=commit_sha,
            changed_paths=changed,
        )
        refreshed = 0
        for rel in [*declared_paths, *removal_paths]:
            _git(["reset", "HEAD", "--", rel], cwd=repo_root, check=False)
            refreshed += 1

    return {
        "mode": "tracked-removals",
        "parent": parent_sha,
        "branch_ref": branch_ref,
        "changed_path_count": len(changed),
        "changed_paths_preview": changed[:25],
        "removed_path_count": len(removed_changed),
        "tracked_entries_matched": len(set(tracked_removed)),
        "new_commit": commit_sha,
        "tree": tree_sha,
        "scoped_evidence_sha": scoped_evidence_sha,
        "dry_run": False,
        "landing_lock": landing_lock or {},
        "work_ledger_mutation_guard": mutation_guard,
        "head_cas_retry_memory": head_cas_retry_memory,
        "work_ledger_closeout_hint": _work_ledger_closeout_hint(
            session_id=effective_work_ledger_session_id,
            commit_sha=commit_sha,
            changed_paths=changed,
            mode="tracked-removals",
        ),
        "refresh_count": refreshed,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _read_message(args: argparse.Namespace, *, allow_dry_run_placeholder: bool = False) -> str:
    if args.message_file:
        return Path(args.message_file).read_text(encoding="utf-8").rstrip("\n")
    if args.message:
        return args.message
    if allow_dry_run_placeholder and bool(getattr(args, "dry_run", False)):
        return DRY_RUN_MESSAGE_PLACEHOLDER
    raise ValueError("scoped-commit: --message or --message-file is required")


def _write_head_cas_retry_packet(exc: HeadCasFailureError) -> None:
    sys.stderr.write(f"{exc}\n")
    sys.stderr.write(
        "scoped-commit-head-cas-retry-packet: "
        f"{json.dumps(exc.retry_packet, sort_keys=True, default=str)}\n"
    )


def _current_head_for_retry_packet(repo_root: Path) -> str:
    res = _git(["rev-parse", "HEAD"], cwd=repo_root, check=False)
    return res.stdout.strip() if res.returncode == 0 and res.stdout.strip() else "unknown"


def _argv_with_retry_flags(argv: list[str], *, current_head: str, dry_run: bool) -> list[str]:
    retry_argv = list(argv)
    if not _has_option(retry_argv, "--allow-multi-hunk-full-paths"):
        retry_argv.append("--allow-multi-hunk-full-paths")
    if current_head != "unknown" and not _has_option(retry_argv, "--expected-parent"):
        retry_argv.extend(["--expected-parent", current_head])
    if dry_run and not _has_option(retry_argv, "--dry-run"):
        retry_argv.append("--dry-run")
    return retry_argv


def _write_multi_hunk_retry_packet(exc: ScopedCommitMultiHunkFullPathsError, *, repo_root: Path) -> None:
    current_head = _current_head_for_retry_packet(repo_root)
    dry_run_argv = _argv_with_retry_flags(
        sys.argv,
        current_head=current_head,
        dry_run=True,
    )
    same_mode_argv = _argv_with_retry_flags(
        sys.argv,
        current_head=current_head,
        dry_run=False,
    )
    packet = {
        "schema": "scoped_commit_multi_hunk_retry_packet_v0",
        "status": "blocked_multi_hunk_full_paths",
        "surface": "tools/meta/control/scoped_commit.py",
        "mode": exc.mode,
        "multi_hunk_paths": exc.multi_hunk_paths,
        "current_head": current_head,
        "required_verification": [
            "prove every hunk in each listed path is owned by this run or by the claimed generated builder",
            "use patch mode instead when only some hunks in a listed path are owned",
            "bind the rerun with --expected-parent so concurrent HEAD movement fails explicitly",
        ],
        "suggested_dry_run_command": _shell_join(dry_run_argv),
        "suggested_same_mode_command": _shell_join(same_mode_argv),
    }
    sys.stderr.write(f"{exc}\n")
    sys.stderr.write(
        "scoped-commit-multi-hunk-retry-packet: "
        f"{json.dumps(packet, sort_keys=True, default=str)}\n"
    )


def _has_option(args: list[str], option: str) -> bool:
    return any(arg == option or arg.startswith(f"{option}=") for arg in args)


def _root_command_insert_index(args: list[str]) -> int:
    idx = 0
    while idx < len(args):
        token = args[idx]
        if token in {"-h", "--help"}:
            return -1
        if token == "--repo-root":
            if idx + 1 >= len(args):
                return idx
            idx += 2
            continue
        if token.startswith("--repo-root="):
            idx += 1
            continue
        return idx
    return idx


def _normalize_root_invocation(argv: list[str]) -> list[str]:
    """Treat common root-level mode flags as their scoped-commit subcommand."""
    args = list(argv)
    insert_at = _root_command_insert_index(args)
    if insert_at < 0 or insert_at >= len(args):
        return args

    remaining = args[insert_at:]
    if remaining[0] in _SUBCOMMANDS:
        return args

    mode = None
    if _has_option(remaining, "--patch-file"):
        mode = "patch"
    elif _has_option(remaining, "--remove-path"):
        mode = "tracked-removals"
    elif any(_has_option(remaining, flag) for flag in _ROOT_FULL_PATH_FLAGS):
        mode = "full-paths"

    if mode is None:
        return args
    return [*args[:insert_at], mode, *remaining]


def _add_cas_retry_attempt_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cas-retry-attempt",
        type=int,
        default=0,
        help=(
            "0 for the initial landing attempt; pass 1 on the single refreshed "
            "retry after a HEAD-CAS failure. If that retry also loses the parent "
            "race, the retry packet requires a validated-uncommitted receipt "
            "instead of queuing another ref mutation."
        ),
    )


def cmd_full_paths(args: argparse.Namespace) -> int:
    try:
        message = _read_message(args, allow_dry_run_placeholder=True)
        result = perform_scoped_commit(
            repo_root=Path(args.repo_root).resolve(),
            paths=list(args.path or []),
            message=message,
            allow_detached=bool(args.allow_detached),
            allow_untracked=bool(args.allow_untracked),
            allow_multi_hunk_full_paths=bool(args.allow_multi_hunk_full_paths),
            dry_run=bool(args.dry_run),
            expected_parent=args.expected_parent,
            work_ledger_session_id=args.work_ledger_session_id,
            cas_retry_attempt=max(0, int(args.cas_retry_attempt or 0)),
        )
    except GitMetadataBlockedError as exc:
        if not bool(args.remote_fallback_on_metadata_block):
            fallback_argv = [*sys.argv, "--remote-fallback-on-metadata-block"]
            fallback_command = _shell_join(fallback_argv)
            if not args.expected_parent:
                fallback_command += ' --expected-parent "$(git rev-parse HEAD)"'
            sys.stderr.write(f"{exc}\n")
            sys.stderr.write(
                "scoped-commit: live `.git` metadata is protected in this sandbox. "
                "To land the same declared full-path scope without writing live "
                "Git metadata, rerun with the remote fallback only with "
                "--expected-parent set to the captured live HEAD and only when "
                "the remote target ref still equals that parent; otherwise rerun the "
                "same command in an authorized local Git process:\n"
                f"  {fallback_command}\n"
            )
            return 2
        try:
            result = perform_remote_full_paths_landing(
                repo_root=Path(args.repo_root).resolve(),
                paths=list(args.path or []),
                message=message,
                remote_name=args.remote_name,
                target_ref=args.target_ref,
                allow_untracked=bool(args.allow_untracked),
                allow_multi_hunk_full_paths=bool(args.allow_multi_hunk_full_paths),
                expected_parent=args.expected_parent,
                work_ledger_session_id=args.work_ledger_session_id,
                metadata_blocker=str(exc),
            )
        except ScopedCommitMultiHunkFullPathsError as fallback_exc:
            _write_multi_hunk_retry_packet(
                fallback_exc,
                repo_root=Path(args.repo_root).resolve(),
            )
            return 2
        except (ValueError, RuntimeError) as fallback_exc:
            sys.stderr.write(f"{fallback_exc}\n")
            return 2
    except HeadCasFailureError as exc:
        _write_head_cas_retry_packet(exc)
        return 2
    except ScopedCommitMultiHunkFullPathsError as exc:
        _write_multi_hunk_retry_packet(exc, repo_root=Path(args.repo_root).resolve())
        return 2
    except (ValueError, RuntimeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


def cmd_patch(args: argparse.Namespace) -> int:
    try:
        result = perform_scoped_commit(
            repo_root=Path(args.repo_root).resolve(),
            paths=list(args.path) if args.path else None,
            patch_path=Path(args.patch_file).resolve(),
            message=_read_message(args, allow_dry_run_placeholder=True),
            allow_detached=bool(args.allow_detached),
            dry_run=bool(args.dry_run),
            expected_parent=args.expected_parent,
            work_ledger_session_id=args.work_ledger_session_id,
            cas_retry_attempt=max(0, int(args.cas_retry_attempt or 0)),
        )
    except HeadCasFailureError as exc:
        _write_head_cas_retry_packet(exc)
        return 2
    except (ValueError, RuntimeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


def cmd_tracked_removals(args: argparse.Namespace) -> int:
    try:
        result = perform_tracked_removals_commit(
            repo_root=Path(args.repo_root).resolve(),
            remove_paths=list(args.remove_path or []),
            paths=list(args.path) if args.path else None,
            message=_read_message(args, allow_dry_run_placeholder=True),
            allow_detached=bool(args.allow_detached),
            allow_untracked=bool(args.allow_untracked),
            dry_run=bool(args.dry_run),
            expected_parent=args.expected_parent,
            work_ledger_session_id=args.work_ledger_session_id,
            cas_retry_attempt=max(0, int(args.cas_retry_attempt or 0)),
        )
    except HeadCasFailureError as exc:
        _write_head_cas_retry_packet(exc)
        return 2
    except (ValueError, RuntimeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1].strip() if __doc__ else None)
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[3]),
        help="Repository root. Defaults to the ai_workflow root containing this tool.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fp = sub.add_parser(
        "full-paths",
        help="Commit exact paths from the working tree via a private index + HEAD CAS.",
    )
    fp.add_argument("--path", action="append", required=True, help="Repo-relative path. Repeatable.")
    msg = fp.add_mutually_exclusive_group(required=False)
    msg.add_argument("--message", help="Commit message inline.")
    msg.add_argument("--message-file", help="Read commit message from this file.")
    fp.add_argument("--allow-detached", action="store_true")
    fp.add_argument("--allow-untracked", action="store_true")
    fp.add_argument(
        "--allow-multi-hunk-full-paths",
        action="store_true",
        help=(
            "Acknowledge that full-paths will commit every hunk in each "
            "declared file. Prefer patch mode for hunk-only ownership."
        ),
    )
    fp.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan the private-index scoped commit. Message is optional in dry-run mode.",
    )
    fp.add_argument(
        "--expected-parent",
        help="Previously captured HEAD/base commit. Refuse if HEAD advanced before landing.",
    )
    _add_cas_retry_attempt_arg(fp)
    fp.add_argument(
        "--work-ledger-session-id",
        default=None,
        help=(
            "Current Work Ledger owner session id. Matching active path claims "
            "are treated as owned; other active path claims block the commit."
        ),
    )
    fp.add_argument(
        "--remote-fallback-on-metadata-block",
        action="store_true",
        help=(
            "When live .git metadata writes are sandbox-blocked, create the "
            "scoped commit in a temporary checkout and push that exact commit "
            "object to the remote target without writing live .git metadata. "
            "Only full-paths mode supports this fallback."
        ),
    )
    fp.add_argument(
        "--remote-name",
        default="origin",
        help="Remote name for --remote-fallback-on-metadata-block. Defaults to origin.",
    )
    fp.add_argument(
        "--target-ref",
        default="refs/heads/main",
        help="Remote target ref for --remote-fallback-on-metadata-block.",
    )
    fp.set_defaults(func=cmd_full_paths)

    pt = sub.add_parser(
        "patch",
        help="Commit a unified diff via private-index `git apply --cached` + HEAD CAS.",
    )
    pt.add_argument("--patch-file", required=True)
    pt.add_argument(
        "--path",
        action="append",
        default=[],
        help="Optional declared pathset; if given, the patch must touch exactly these paths.",
    )
    msg2 = pt.add_mutually_exclusive_group(required=False)
    msg2.add_argument("--message")
    msg2.add_argument("--message-file")
    pt.add_argument("--allow-detached", action="store_true")
    pt.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan the private-index patch commit. Message is optional in dry-run mode.",
    )
    pt.add_argument(
        "--expected-parent",
        help="Previously captured HEAD/base commit. Refuse if HEAD advanced before landing.",
    )
    _add_cas_retry_attempt_arg(pt)
    pt.add_argument(
        "--work-ledger-session-id",
        default=None,
        help=(
            "Current Work Ledger owner session id. Matching active path claims "
            "are treated as owned; other active path claims block the commit."
        ),
    )
    pt.set_defaults(func=cmd_patch)

    tr = sub.add_parser(
        "tracked-removals",
        help="Commit private-index git-rm --cached removals while keeping worktree files.",
    )
    tr.add_argument(
        "--remove-path",
        action="append",
        required=True,
        help="Repo-relative tracked path or directory to remove from git tracking. Repeatable.",
    )
    tr.add_argument(
        "--path",
        action="append",
        default=[],
        help="Optional worktree path to include in the same commit, such as a .gitignore update.",
    )
    msg3 = tr.add_mutually_exclusive_group(required=False)
    msg3.add_argument("--message")
    msg3.add_argument("--message-file")
    tr.add_argument("--allow-detached", action="store_true")
    tr.add_argument("--allow-untracked", action="store_true")
    tr.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan the tracked-removals commit. Message is optional in dry-run mode.",
    )
    tr.add_argument(
        "--expected-parent",
        help="Previously captured HEAD/base commit. Refuse if HEAD advanced before landing.",
    )
    _add_cas_retry_attempt_arg(tr)
    tr.add_argument(
        "--work-ledger-session-id",
        default=None,
        help=(
            "Current Work Ledger owner session id. Matching active path claims "
            "are treated as owned; other active path claims block the commit."
        ),
    )
    tr.set_defaults(func=cmd_tracked_removals)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(_normalize_root_invocation(raw_argv))
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
