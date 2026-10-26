"""
Shared dirty-worktree guardrails for repo-local agents.

The work ledger can make other sessions visible, but the sharp edge that caused
recent source-loss incidents was broader: raw git commands such as stash/apply
and reset/restore mutate the whole shared checkout without respecting path
claims. This module keeps the detector used by preflight and the blocker used by
repo-git on one implementation.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "shared_worktree_git_guard_v1"
PUBLICATION_GATE_SCHEMA = "shared_worktree_publication_gate_v1"
RECOVERY_BUNDLE_SCHEMA = "shared_worktree_recovery_bundle_requirement_v1"
TRACE_BUNDLE_SCHEMA = "shared_worktree_transaction_trace_v1"
DIRTY_PATH_PREVIEW_LIMIT = 25
PUBLICATION_PREVIEW_LIMIT = 8
RISK_ADVICE = (
    "Do not use broad git stash/reset/restore/clean in a shared dirty or "
    "artifact-bearing worktree with active agents. git clean can delete ignored "
    "dependency installs and render receipts even when tracked status is clean. "
    "Snapshot dirty state first, claim paths, use a separate worktree for "
    "isolation, or create an explicit patch artifact."
)
PUBLICATION_GATE_ADVICE = (
    "Publication / remote sync boundary blocked before git push. Inspect the "
    "push-range bloat gate and use the detached clean publication lane for "
    "selected commits, or run an operator-owned sanitation pass before publishing."
)
_SHELL_SEPARATORS = {"&&", "||", ";", "|"}
_RISK_REGEXES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"\bgit\s+stash\b"), "shared_git_stash", "stash"),
    (re.compile(r"\bgit\s+commit-tree\b"), "shared_git_commit_tree", "commit-tree"),
    (re.compile(r"\bgit\s+update-ref\b"), "shared_git_update_ref", "update-ref"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "shared_git_reset_hard", "reset --hard"),
    (re.compile(r"\bgit\s+reset\s+--soft\b"), "shared_git_reset_soft", "reset --soft"),
    (re.compile(r"\bgit\s+checkout\s+--\b"), "shared_git_checkout_path", "checkout --"),
    (re.compile(r"\bgit\s+restore\b"), "shared_git_restore", "restore"),
    (re.compile(r"\bgit\s+clean\s+-[A-Za-z]*f[A-Za-z]*\b"), "shared_git_clean", "clean"),
    (
        re.compile(r"\bgit\s+push\b[^\n;&|]*\b[0-9a-f]{7,40}:refs/heads/[^\s;&|]+"),
        "shared_git_direct_ref_push",
        "push direct ref",
    ),
)


def _compact_command(value: Any, *, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return f"{text[: limit - 3]}..."
    return text


def _risk(risk: str, verb: str, command: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "risk": risk,
        "verb": verb,
        "command": _compact_command(command),
        "severity": "blocker",
        "advice": RISK_ADVICE,
    }


def _strip_git_global_options(tokens: Sequence[str]) -> list[str]:
    args = list(tokens)
    idx = 0
    while idx < len(args):
        token = args[idx]
        if token in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}:
            idx += 2
            continue
        if token.startswith(("--git-dir=", "--work-tree=", "--namespace=", "--exec-path=")):
            idx += 1
            continue
        if token in {"--no-pager", "--bare", "--version"}:
            idx += 1
            continue
        break
    return args[idx:]


def _normalized_git_argv(argv: Sequence[str]) -> list[str]:
    tokens = [str(item) for item in argv if str(item)]
    if tokens and Path(tokens[0]).name == "git":
        tokens = tokens[1:]
    return _strip_git_global_options(tokens)


def _is_git_push(argv: Sequence[str]) -> bool:
    tokens = _normalized_git_argv(argv)
    return bool(tokens and tokens[0] == "push")


def _is_direct_ref_push(tokens: Sequence[str]) -> bool:
    if not tokens or tokens[0] != "push":
        return False
    for token in tokens[1:]:
        if ":" not in token or token.startswith("-"):
            continue
        local_ref, remote_ref = token.split(":", 1)
        if not local_ref or not remote_ref:
            continue
        remote_is_branch = remote_ref.startswith("refs/heads/") or remote_ref in {
            "main",
            "master",
        }
        local_is_objectish = bool(re.fullmatch(r"[0-9a-fA-F]{7,40}", local_ref))
        local_is_detached_ref = local_ref in {"HEAD", "FETCH_HEAD"} or local_ref.startswith(
            ("refs/", "rescue/", "aiw/")
        )
        if remote_is_branch and (local_is_objectish or local_is_detached_ref):
            return True
    return False


def classify_git_argv(argv: Sequence[str], *, command_text: str | None = None) -> list[dict[str, Any]]:
    """Return shared-worktree risks for a single git invocation."""
    tokens = [str(item) for item in argv if str(item)]
    if not tokens:
        return []
    tokens = _normalized_git_argv(tokens)
    if not tokens:
        return []
    verb = tokens[0]
    rendered = command_text or "git " + shlex.join(tokens)

    if verb == "stash":
        subcommand = tokens[1] if len(tokens) > 1 else "push"
        if subcommand in {"list", "show"}:
            return []
        return [_risk("shared_git_stash", "stash", rendered)]
    if verb == "commit-tree":
        return [_risk("shared_git_commit_tree", "commit-tree", rendered)]
    if verb == "update-ref":
        return [_risk("shared_git_update_ref", "update-ref", rendered)]
    if verb == "reset" and "--hard" in tokens[1:]:
        return [_risk("shared_git_reset_hard", "reset --hard", rendered)]
    if verb == "reset" and "--soft" in tokens[1:]:
        return [_risk("shared_git_reset_soft", "reset --soft", rendered)]
    if verb == "restore":
        return [_risk("shared_git_restore", "restore", rendered)]
    if verb == "checkout" and "--" in tokens[1:]:
        return [_risk("shared_git_checkout_path", "checkout --", rendered)]
    if verb == "clean":
        flags = "".join(token for token in tokens[1:] if token.startswith("-"))
        if "f" in flags:
            return [_risk("shared_git_clean", "clean", rendered)]
    if _is_direct_ref_push(tokens):
        return [_risk("shared_git_direct_ref_push", "push direct ref", rendered)]
    return []


def _push_publication_gate(repo_root: Path, *, dirty_path_count: int) -> dict[str, Any]:
    command = "./repo-python tools/meta/control/mission_transaction_preflight.py --github-push-bloat-gate"
    try:
        from system.lib import mission_transaction_landing_preflight as preflight

        gate = preflight._github_push_bloat_gate(  # type: ignore[attr-defined]
            repo_root,
            dirty_tree={"dirty_path_count": dirty_path_count, "by_class": {}},
            workspace_pressure={
                "schema": "workspace_bloat_pressure_v0",
                "status": "unknown",
                "primary_class": None,
                "primary_count": None,
            },
        )
    except Exception as exc:  # pragma: no cover - defensive around Git/preflight drift.
        return {
            "schema": PUBLICATION_GATE_SCHEMA,
            "surface": "github_push_bloat_gate_v1",
            "status": "watch",
            "mode": "preflight_unavailable",
            "blocked": False,
            "error_class": type(exc).__name__,
            "error": str(exc),
            "safe_next_command": command,
            "proof_route": command,
            "advice": None,
        }

    status = str(gate.get("status") or "watch")
    blocked = status == "blocked"
    publication_recovery = (
        gate.get("publication_recovery")
        if isinstance(gate.get("publication_recovery"), Mapping)
        else {}
    )
    recovery_next = str(publication_recovery.get("safe_next_command") or "").strip()

    def _compact_blob_row(row: Any) -> dict[str, Any]:
        if not isinstance(row, Mapping):
            return {}
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
            "manifest_or_pointer": row.get("manifest_or_pointer"),
            "artifact_class": artifact_policy.get("artifact_class"),
            "push_gate_disposition": artifact_policy.get("push_gate_disposition"),
            "reason": artifact_policy.get("reason"),
        }

    return {
        "schema": PUBLICATION_GATE_SCHEMA,
        "surface": gate.get("schema") or "github_push_bloat_gate_v1",
        "status": status,
        "blocked": blocked,
        "mode": gate.get("mode"),
        "base_ref": gate.get("base_ref"),
        "push_range": gate.get("push_range"),
        "workspace_dirty_is_push_gate": gate.get("workspace_dirty_is_push_gate"),
        "blocked_reasons": gate.get("blocked_reasons", []),
        "watch_reasons": gate.get("watch_reasons", []),
        "generated_push_class_counts": gate.get("generated_push_class_counts", {}),
        "changed_path_count": gate.get("changed_path_count", 0),
        "new_blob_count": gate.get("new_blob_count", 0),
        "large_blob_count": gate.get("large_blob_count", 0),
        "generated_paths_preview": [
            row
            for row in (
                _compact_blob_row(item)
                for item in (gate.get("generated_paths") or [])[:PUBLICATION_PREVIEW_LIMIT]
            )
            if row
        ],
        "large_blobs_preview": [
            row
            for row in (
                _compact_blob_row(item)
                for item in (gate.get("large_blobs") or [])[:PUBLICATION_PREVIEW_LIMIT]
            )
            if row
        ],
        "publication_recovery": publication_recovery,
        "recommended_lane": publication_recovery.get("recommended_lane"),
        "safe_next_command": recovery_next if blocked and recovery_next else command,
        "proof_route": command,
        "advice": PUBLICATION_GATE_ADVICE if blocked else None,
    }


def _git_invocations_from_shell_text(command: str) -> list[list[str]]:
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = command.split()
    invocations: list[list[str]] = []
    idx = 0
    while idx < len(tokens):
        token = tokens[idx].strip()
        cleaned = token.strip("()")
        if Path(cleaned).name != "git":
            idx += 1
            continue
        invocation = [cleaned]
        idx += 1
        while idx < len(tokens):
            part = tokens[idx].strip()
            trimmed = part.strip()
            if trimmed in _SHELL_SEPARATORS:
                break
            separator_suffix = next((sep for sep in (";", "|") if trimmed.endswith(sep)), "")
            invocation.append(trimmed[: -len(separator_suffix)] if separator_suffix else trimmed)
            idx += 1
            if separator_suffix:
                break
        invocations.append([part for part in invocation if part])
    return invocations


def detect_git_risks_in_text(command: str) -> list[dict[str, Any]]:
    """Detect risky git commands inside a shell command line or rollout snippet."""
    text = str(command or "")
    risks: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for invocation in _git_invocations_from_shell_text(text):
        for risk in classify_git_argv(invocation, command_text=text):
            key = (str(risk.get("risk") or ""), str(risk.get("command") or ""))
            if key not in seen:
                risks.append(risk)
                seen.add(key)
    if risks:
        return risks
    for pattern, risk_name, verb in _RISK_REGEXES:
        if pattern.search(text):
            risk = _risk(risk_name, verb, text)
            key = (risk_name, str(risk.get("command") or ""))
            if key not in seen:
                risks.append(risk)
                seen.add(key)
    return risks


def read_dirty_paths(repo_root: Path, *, git_bin: str | None = None) -> list[str]:
    git = git_bin or shutil.which("git") or "git"
    proc = subprocess.run(
        [git, "-C", str(repo_root), "status", "--porcelain=v1"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    paths: list[str] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path:
            paths.append(path)
    return paths


def _recovery_bundle_requirement(
    *,
    blocked: bool,
    risks: Sequence[Mapping[str, Any]],
    dirty_paths: Sequence[str],
    publication_gate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    risk_names = [str(row.get("risk") or "") for row in risks if row.get("risk")]
    publication_blocked = bool(
        isinstance(publication_gate, Mapping)
        and publication_gate.get("status") == "blocked"
    )
    required = bool(blocked and (risk_names or publication_blocked or dirty_paths))
    return {
        "schema": RECOVERY_BUNDLE_SCHEMA,
        "status": "required" if required else "not_required",
        "required": required,
        "reason": (
            "destructive_or_normalizing_git_operation"
            if required
            else "no_destructive_or_normalizing_operation_blocked"
        ),
        "risk_names": risk_names,
        "dirty_path_count": len(dirty_paths),
        "dirty_paths_preview": list(dirty_paths)[:DIRTY_PATH_PREVIEW_LIMIT],
        "minimum_contents": [
            "git status --porcelain=v1 -z --branch",
            "git diff --binary",
            "git diff --cached --binary",
            "git ls-files --others --exclude-standard -z",
            "HEAD, branch, actor/session id, command, timestamp, claim ids, and validation refs",
        ],
        "safe_snapshot_commands": [
            "git status --porcelain=v1 -z --branch",
            "git diff --binary",
            "git diff --cached --binary",
            "git ls-files --others --exclude-standard -z",
            "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --compact",
        ],
        "trace_section": "WORKTREE_TRANSACTION_BUNDLE",
        "storage_guidance": (
            "Store the status/diff/untracked manifest under the existing "
            "Task/Work Ledger or transaction receipt path for the owning lane; "
            "do not use an anonymous stash as the only savepoint."
        ),
    }


def _transaction_trace(
    *,
    risks: Sequence[Mapping[str, Any]],
    publication_gate: Mapping[str, Any] | None,
    recovery_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": TRACE_BUNDLE_SCHEMA,
        "section": "WORKTREE_TRANSACTION_BUNDLE",
        "status": "required" if recovery_bundle.get("required") else "not_required",
        "required_fields": [
            "actor",
            "session_id",
            "command",
            "branch",
            "head",
            "lease_or_claim_ids",
            "dirty_paths",
            "decision",
            "recovery_bundle_ref",
        ],
        "risk_count": len(risks),
        "publication_gate_status": (
            publication_gate.get("status")
            if isinstance(publication_gate, Mapping)
            else None
        ),
        "recovery_bundle_required": bool(recovery_bundle.get("required")),
    }


def assess_git_argv(
    argv: Sequence[str],
    *,
    repo_root: Path,
    dirty_paths: Sequence[str] | None = None,
    allow_unsafe: bool = False,
    include_publication_gate: bool = True,
) -> dict[str, Any]:
    risks = classify_git_argv(["git", *[str(item) for item in argv]])
    dirty = list(dirty_paths) if dirty_paths is not None else read_dirty_paths(repo_root)
    publication_gate = (
        _push_publication_gate(repo_root, dirty_path_count=len(dirty))
        if include_publication_gate and _is_git_push(["git", *[str(item) for item in argv]])
        else None
    )
    publication_blocked = bool(
        isinstance(publication_gate, Mapping)
        and publication_gate.get("status") == "blocked"
    )
    shared_worktree_blocked = bool(risks and not allow_unsafe)
    blocked = shared_worktree_blocked or publication_blocked
    recovery_bundle = _recovery_bundle_requirement(
        blocked=blocked,
        risks=risks,
        dirty_paths=dirty,
        publication_gate=publication_gate,
    )
    return {
        "schema": SCHEMA,
        "allowed": not blocked,
        "blocked": blocked,
        "shared_worktree_blocked": shared_worktree_blocked,
        "publication_gate_blocked": publication_blocked,
        "risk_count": len(risks),
        "risks": risks,
        "publication_gate": publication_gate,
        "dirty_path_count": len(dirty),
        "dirty_paths_preview": dirty[:DIRTY_PATH_PREVIEW_LIMIT],
        "recovery_bundle_requirement": recovery_bundle,
        "transaction_trace": _transaction_trace(
            risks=risks,
            publication_gate=publication_gate,
            recovery_bundle=recovery_bundle,
        ),
        "allow_unsafe": bool(allow_unsafe),
        "include_publication_gate": bool(include_publication_gate),
        "allow_unsafe_bypasses_publication_gate": False,
        "advice": (
            PUBLICATION_GATE_ADVICE
            if publication_blocked
            else (RISK_ADVICE if shared_worktree_blocked else None)
        ),
    }


def decision_json(decision: Mapping[str, Any]) -> str:
    return json.dumps(dict(decision), indent=2, ensure_ascii=False)


def unsafe_allowed_from_env() -> bool:
    return os.environ.get("AI_WORKFLOW_ALLOW_UNSAFE_GIT", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
