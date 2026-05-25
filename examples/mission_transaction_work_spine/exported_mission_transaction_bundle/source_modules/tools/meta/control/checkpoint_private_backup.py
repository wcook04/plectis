#!/usr/bin/env python3
"""Private backup lane behind ./checkpoint.

This helper keeps Git mechanics behind the repo-owned checkpoint command.  It
does not replace publication hygiene; it creates a separate private
preservation lane for "save this machine before loss matters" moments.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


GITHUB_RECOMMENDED_FILE_BYTES = 50 * 1024 * 1024
GITHUB_HARD_FILE_BYTES = 100 * 1024 * 1024
DEFAULT_ALLOWED_BYPASS_CATEGORIES = {
    "runtime_artifact",
    "replaceable_generated_artifact",
    "navigation_cache_drift",
}


def _run(
    repo_root: Path,
    args: list[str],
    *,
    input_text: str | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=repo_root,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        cmd = " ".join(args)
        raise RuntimeError(f"{cmd} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result


def _git(repo_root: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return _run(repo_root, ["git", *args], check=check)


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    return value


def _emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=_json_default))


def _format_bytes(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "unknown"
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size_bytes} B"


def _remote_slug(remote_url: str) -> str | None:
    token = remote_url.strip()
    patterns = (
        r"^git@github\.com:([^/]+/[^/]+?)(?:\.git)?$",
        r"^https://github\.com/([^/]+/[^/]+?)(?:\.git)?$",
        r"^ssh://git@github\.com/([^/]+/[^/]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.match(pattern, token)
        if match:
            return match.group(1)
    return None


def _remote_url(repo_root: Path, remote: str) -> str | None:
    result = _git(repo_root, "remote", "get-url", remote)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _github_privacy(repo_root: Path, remote: str) -> dict[str, Any]:
    remote_url = _remote_url(repo_root, remote)
    slug = _remote_slug(remote_url or "")
    payload: dict[str, Any] = {
        "remote": remote,
        "remote_url": remote_url,
        "slug": slug,
        "status": "unknown",
        "is_private": None,
        "source": "gh repo view",
    }
    if os.environ.get("AIW_PRIVATE_BACKUP_ASSUME_PRIVATE") == "1":
        payload.update(
            {
                "status": "private_assumed_for_test",
                "is_private": True,
                "source": "AIW_PRIVATE_BACKUP_ASSUME_PRIVATE",
            }
        )
        return payload
    if not slug:
        payload["reason"] = "remote is not a recognized GitHub URL"
        return payload
    result = _run(
        repo_root,
        ["gh", "repo", "view", slug, "--json", "isPrivate,nameWithOwner,url,defaultBranchRef"],
    )
    if result.returncode != 0:
        payload["reason"] = result.stderr.strip() or result.stdout.strip() or "gh repo view failed"
        return payload
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        payload["reason"] = f"gh returned non-JSON output: {exc}"
        return payload
    is_private = bool(data.get("isPrivate"))
    payload.update(
        {
            "status": "private" if is_private else "public",
            "is_private": is_private,
            "repo": data,
        }
    )
    return payload


def _branch(repo_root: Path) -> str:
    result = _git(repo_root, "branch", "--show-current", check=True)
    return result.stdout.strip()


def _rev_parse(repo_root: Path, rev: str) -> str | None:
    result = _git(repo_root, "rev-parse", rev)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _count_lines(text: str) -> int:
    return len([line for line in text.splitlines() if line.strip()])


def _worktree_counts(repo_root: Path) -> dict[str, Any]:
    status = _git(repo_root, "status", "--porcelain=v1", "--untracked-files=all").stdout
    ignored = _git(
        repo_root,
        "status",
        "--porcelain=v1",
        "--ignored=matching",
        "--untracked-files=all",
    ).stdout
    untracked = [line[3:] for line in status.splitlines() if line.startswith("?? ")]
    modified = [line[3:] for line in status.splitlines() if line and not line.startswith("?? ")]
    ignored_paths = [line[3:] for line in ignored.splitlines() if line.startswith("!! ")]
    return {
        "dirty_path_count": _count_lines(status),
        "modified_path_count": len(modified),
        "untracked_path_count": len(untracked),
        "ignored_path_count": len(ignored_paths),
        "modified_sample": modified[:12],
        "untracked_sample": untracked[:12],
        "ignored_sample": ignored_paths[:12],
    }


def _tracked_counts(repo_root: Path) -> dict[str, Any]:
    files = _git(repo_root, "ls-files").stdout.splitlines()
    lfs = _run(repo_root, ["git", "lfs", "ls-files"])
    return {
        "tracked_file_count": len([line for line in files if line.strip()]),
        "lfs_file_count": _count_lines(lfs.stdout) if lfs.returncode == 0 else None,
        "lfs_available": lfs.returncode == 0,
    }


def _large_tracked_files(repo_root: Path, *, limit: int = 12) -> list[dict[str, Any]]:
    result = _git(repo_root, "ls-tree", "-r", "-l", "HEAD")
    rows: list[dict[str, Any]] = []
    if result.returncode != 0:
        return rows
    for line in result.stdout.splitlines():
        parts = line.split(None, 4)
        if len(parts) != 5:
            continue
        size_token = parts[3]
        path = parts[4]
        if size_token == "-":
            continue
        try:
            size = int(size_token)
        except ValueError:
            continue
        if size > GITHUB_RECOMMENDED_FILE_BYTES:
            rows.append(
                {
                    "path": path,
                    "size_bytes": size,
                    "size": _format_bytes(size),
                    "hard_limit_exceeded": size > GITHUB_HARD_FILE_BYTES,
                }
            )
    rows.sort(key=lambda row: int(row["size_bytes"]), reverse=True)
    return rows[:limit]


def _ahead_behind(repo_root: Path, upstream_ref: str) -> dict[str, Any]:
    result = _git(repo_root, "rev-list", "--left-right", "--count", f"{upstream_ref}...HEAD")
    if result.returncode != 0:
        return {"ahead": None, "behind": None, "status": "unknown", "reason": result.stderr.strip()}
    parts = result.stdout.split()
    if len(parts) != 2:
        return {"ahead": None, "behind": None, "status": "unknown"}
    behind = int(parts[0])
    ahead = int(parts[1])
    status = "diverged" if ahead and behind else "ahead" if ahead else "behind" if behind else "synced"
    return {"ahead": ahead, "behind": behind, "status": status}


def _fetch_remote_branch(repo_root: Path, remote: str, branch_name: str) -> dict[str, Any]:
    result = _git(repo_root, "fetch", remote, branch_name)
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "remote": remote,
        "branch": branch_name,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _push_audit(repo_root: Path, remote: str) -> dict[str, Any]:
    result = _run(repo_root, ["./repo-python", "run_git.py", "audit", "push", "--remote-name", remote, "--json"])
    if result.returncode not in (0, 1):
        return {
            "status": "unknown",
            "returncode": result.returncode,
            "stderr": result.stderr.strip(),
            "stdout": result.stdout.strip(),
            "violations": [],
        }
    try:
        raw_payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        raw_payload = {}
    if isinstance(raw_payload, dict):
        raw_violations = raw_payload.get("violations") or []
    elif isinstance(raw_payload, list):
        raw_violations = raw_payload
    else:
        raw_violations = []
    violations = [row for row in raw_violations if isinstance(row, dict)]
    errors = [row for row in violations if row.get("severity") == "error"]
    warnings = [row for row in violations if row.get("severity") != "error"]
    return {
        "status": "blocked" if errors else "warn" if warnings else "clear",
        "returncode": result.returncode,
        "violations": violations,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "categories": sorted({str(row.get("category")) for row in violations if row.get("category")}),
    }


def _classify_bypass(push_audit: dict[str, Any]) -> dict[str, Any]:
    violations = list(push_audit.get("violations") or [])
    errors = [row for row in violations if row.get("severity") == "error"]
    error_categories = {str(row.get("category")) for row in errors}
    unknown = sorted(error_categories - DEFAULT_ALLOWED_BYPASS_CATEGORIES)
    hard = sorted(
        {
            str(row.get("category"))
            for row in errors
            if str(row.get("category")) == "oversize_blob"
            or (row.get("size_bytes") is not None and int(row.get("size_bytes") or 0) > GITHUB_HARD_FILE_BYTES)
        }
    )
    allowed = not unknown and not hard
    return {
        "required": bool(errors),
        "allowed": allowed,
        "allowed_categories": sorted(DEFAULT_ALLOWED_BYPASS_CATEGORIES),
        "error_categories": sorted(error_categories),
        "unknown_or_disallowed_categories": sorted(set(unknown) | set(hard)),
        "mode": "no_verify_allowed_for_private_preservation" if errors and allowed else "normal_push",
    }


def build_status(repo_root: Path, *, remote: str = "origin", branch: str | None = None) -> dict[str, Any]:
    branch_name = branch or _branch(repo_root)
    remote_ref = f"{remote}/{branch_name}"
    fetch = _fetch_remote_branch(repo_root, remote, branch_name)
    local_sha = _rev_parse(repo_root, "HEAD")
    remote_sha = _rev_parse(repo_root, remote_ref) if fetch["status"] == "ok" else None
    privacy = _github_privacy(repo_root, remote)
    counts = _worktree_counts(repo_root)
    tracked = _tracked_counts(repo_root)
    large_files = _large_tracked_files(repo_root)
    push_audit = _push_audit(repo_root, remote)
    bypass = _classify_bypass(push_audit)
    if fetch["status"] != "ok":
        divergence = {
            "ahead": None,
            "behind": None,
            "status": "fetch_failed",
            "reason": fetch["stderr"] or fetch["stdout"] or "git fetch failed",
        }
    elif remote_sha:
        divergence = _ahead_behind(repo_root, remote_ref)
    else:
        divergence = {
            "ahead": None,
            "behind": None,
            "status": "no_remote_tracking_ref",
        }

    remote_matches = bool(local_sha and remote_sha and local_sha == remote_sha)
    coverage_gaps = [
        "external databases or browser/provider state outside the repo",
        "local environment secrets not intentionally tracked",
    ]
    if counts["ignored_path_count"]:
        coverage_gaps.append("ignored files")
    if counts["untracked_path_count"]:
        coverage_gaps.append("untracked files")
    if tracked["lfs_available"] is not True:
        coverage_gaps.append("LFS objects unless git-lfs reports and remote storage are verified")

    git_remote_blockers: list[str] = []
    if fetch["status"] != "ok":
        git_remote_blockers.append("remote_fetch_failed")
    if privacy.get("is_private") is not True:
        git_remote_blockers.append("remote_privacy_not_verified")
    if not remote_sha and fetch["status"] == "ok":
        git_remote_blockers.append("remote_branch_not_resolved")

    if git_remote_blockers:
        git_remote_status = "red"
        git_remote_summary = "Git remote backup target is not verified."
    elif not remote_matches:
        git_remote_status = "yellow"
        git_remote_summary = "Private GitHub branch SHA does not match local HEAD."
    elif counts["modified_path_count"]:
        git_remote_status = "yellow"
        git_remote_summary = "Private GitHub has HEAD, but tracked worktree modifications are not committed."
    else:
        git_remote_status = "green"
        git_remote_summary = "Private GitHub has the current commit."

    if git_remote_status == "red":
        whole_system_coverage_status = "red"
    elif coverage_gaps:
        whole_system_coverage_status = "yellow"
    else:
        whole_system_coverage_status = "green"

    repo_health_status = "yellow" if large_files else "green"
    if git_remote_status == "red" or whole_system_coverage_status == "red":
        overall_backup_status = "red"
    elif git_remote_status == "yellow" or whole_system_coverage_status == "yellow":
        overall_backup_status = "yellow"
    else:
        overall_backup_status = "green"

    operator_summary = (
        f"Git-tracked backup is {git_remote_status}; "
        f"whole-system coverage is {whole_system_coverage_status}."
    )
    if repo_health_status == "yellow":
        operator_summary += " Large tracked files remain a repository-health warning."

    return {
        "schema": "checkpoint_private_backup_status_v1",
        "status": overall_backup_status,
        "git_remote_status": git_remote_status,
        "whole_system_coverage_status": whole_system_coverage_status,
        "overall_backup_status": overall_backup_status,
        "repo_health_status": repo_health_status,
        "summary": operator_summary,
        "operator_summary": operator_summary,
        "git_remote_summary": git_remote_summary,
        "git_remote_blockers": git_remote_blockers,
        "repo_root": str(repo_root),
        "remote": remote,
        "branch": branch_name,
        "fetch": fetch,
        "local_sha": local_sha,
        "remote_sha": remote_sha,
        "remote_matches_local": remote_matches,
        "privacy": privacy,
        "divergence": divergence,
        "worktree": counts,
        "tracked": tracked,
        "large_tracked_files": large_files,
        "push_policy": push_audit,
        "hook_bypass": bypass,
        "coverage": {
            "protected_by_git_remote": [
                "tracked files and reachable Git history on pushed refs",
                "tags that have been pushed to the remote",
            ],
            "not_proven_by_git_remote": coverage_gaps,
        },
    }


def _print_status(payload: dict[str, Any]) -> None:
    print(f"Overall backup status: {payload['overall_backup_status'].upper()}")
    print(payload["operator_summary"])
    print(f"Git-tracked remote status: {payload['git_remote_status'].upper()}")
    print(f"Whole-system coverage status: {payload['whole_system_coverage_status'].upper()}")
    print(f"remote: {payload['remote']} | branch: {payload['branch']}")
    print(f"local:  {payload.get('local_sha')}")
    print(f"remote: {payload.get('remote_sha')}")
    privacy = payload.get("privacy") or {}
    print(f"privacy: {privacy.get('status')} ({privacy.get('slug') or privacy.get('remote_url')})")
    divergence = payload.get("divergence") or {}
    print(
        "divergence: "
        f"{divergence.get('status')} "
        f"ahead={divergence.get('ahead')} behind={divergence.get('behind')}"
    )
    worktree = payload.get("worktree") or {}
    print(
        "worktree: "
        f"dirty={worktree.get('dirty_path_count')} "
        f"untracked={worktree.get('untracked_path_count')} "
        f"ignored={worktree.get('ignored_path_count')}"
    )
    push_policy = payload.get("push_policy") or {}
    print(
        "push policy: "
        f"{push_policy.get('status')} "
        f"errors={push_policy.get('error_count')} warnings={push_policy.get('warning_count')}"
    )
    large_files = payload.get("large_tracked_files") or []
    if large_files:
        print("large tracked files:")
        for row in large_files[:5]:
            print(f"  {row['path']} ({row['size']})")
    print("not proven by GitHub remote:")
    for item in (payload.get("coverage") or {}).get("not_proven_by_git_remote", []):
        print(f"  - {item}")


def _checkpoint(repo_root: Path, message: str) -> dict[str, Any]:
    result = _run(repo_root, ["./checkpoint", "--arbiter", "--message", message])
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _make_backup_ref(prefix: str, old_remote_sha: str | None = None) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    clean = prefix.strip("/") or "aiw-backup-origin-main"
    suffix = (old_remote_sha or "unknown")[:12]
    return f"refs/tags/{clean}-{stamp}-{suffix}"


def _push_tag(repo_root: Path, remote: str, backup_ref: str, old_remote_sha: str, *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"status": "dry_run", "remote": remote, "ref": backup_ref, "target": old_remote_sha}
    local_name = backup_ref.removeprefix("refs/tags/")
    create = _git(repo_root, "tag", local_name, old_remote_sha)
    if create.returncode != 0:
        return {"status": "failed", "step": "tag", "remote": remote, "stderr": create.stderr.strip(), "ref": backup_ref}
    push = _git(repo_root, "push", remote, backup_ref)
    return {
        "status": "pushed" if push.returncode == 0 else "failed",
        "remote": remote,
        "ref": backup_ref,
        "target": old_remote_sha,
        "stdout": push.stdout.strip(),
        "stderr": push.stderr.strip(),
        "returncode": push.returncode,
    }


def build_private_backup_plan(
    repo_root: Path,
    *,
    remote: str,
    branch: str | None,
    message: str,
    backup_ref_prefix: str,
) -> dict[str, Any]:
    status = build_status(repo_root, remote=remote, branch=branch)
    old_remote_sha = status.get("remote_sha")
    backup_ref = _make_backup_ref(backup_ref_prefix, str(old_remote_sha or ""))
    force_needed = bool((status.get("divergence") or {}).get("behind"))
    force_with_lease = None
    if force_needed and old_remote_sha:
        force_with_lease = f"--force-with-lease=refs/heads/{status.get('branch')}:{old_remote_sha}"
    return {
        "schema": "checkpoint_private_backup_plan_v1",
        "status": "planned",
        "repo_root": str(repo_root),
        "remote": remote,
        "branch": status.get("branch"),
        "message": message,
        "old_remote_sha": old_remote_sha,
        "local_sha": status.get("local_sha"),
        "backup_ref": backup_ref,
        "force_with_lease": force_with_lease,
        "force_needed": force_needed,
        "privacy": status.get("privacy"),
        "hook_bypass": status.get("hook_bypass"),
        "git_remote_status": status.get("git_remote_status"),
        "whole_system_coverage_status": status.get("whole_system_coverage_status"),
        "overall_backup_status": status.get("overall_backup_status"),
        "operator_summary": status.get("operator_summary"),
        "git_remote_blockers": status.get("git_remote_blockers"),
        "fetch": status.get("fetch"),
        "steps": [
            "verify private GitHub remote",
            "fetch and record old remote SHA",
            "checkpoint dirty tree through ./checkpoint",
            "drain one bounded tail pass if checkpoint creates new dirt",
            "push recovery tag for old remote SHA when replacement is needed",
            "push with exact --force-with-lease if remote history must be replaced",
            "verify remote branch equals local HEAD and backup ref is present",
        ],
        "coverage": status.get("coverage"),
    }


def run_private_backup(
    repo_root: Path,
    *,
    remote: str,
    branch: str | None,
    message: str,
    backup_ref_prefix: str,
    dry_run: bool,
    max_tail_drains: int,
) -> dict[str, Any]:
    plan = build_private_backup_plan(
        repo_root,
        remote=remote,
        branch=branch,
        message=message,
        backup_ref_prefix=backup_ref_prefix,
    )
    privacy = plan.get("privacy") or {}
    fetch = plan.get("fetch") or {}
    if fetch.get("status") != "ok":
        plan.update(
            {
                "status": "blocked",
                "blocker": "remote_fetch_failed",
                "dry_run": dry_run,
            }
        )
        return plan if dry_run else {**plan, "returncode": 1}
    if privacy.get("is_private") is not True:
        plan.update(
            {
                "status": "blocked",
                "blocker": "remote_privacy_not_verified",
                "dry_run": dry_run,
            }
        )
        return plan if dry_run else {**plan, "returncode": 1}
    if dry_run:
        plan["dry_run"] = True
        return plan

    old_remote_sha = str(plan.get("old_remote_sha") or "")
    branch_name = str(plan.get("branch") or branch or _branch(repo_root))
    if not old_remote_sha:
        return {**plan, "status": "blocked", "blocker": "missing_old_remote_sha", "returncode": 1}

    checkpoints: list[dict[str, Any]] = []
    for index in range(max_tail_drains + 1):
        counts = _worktree_counts(repo_root)
        if counts["dirty_path_count"] == 0:
            break
        tail = f" tail {index}" if index else ""
        checkpoints.append(_checkpoint(repo_root, f"{message}{tail}"))
        if checkpoints[-1]["returncode"] != 0:
            return {**plan, "status": "blocked", "blocker": "checkpoint_failed", "checkpoints": checkpoints, "returncode": 1}
    remaining = _worktree_counts(repo_root)
    if remaining["dirty_path_count"]:
        return {
            **plan,
            "status": "blocked",
            "blocker": "tail_did_not_stabilize",
            "checkpoints": checkpoints,
            "remaining_worktree": remaining,
            "returncode": 1,
        }

    local_sha = _rev_parse(repo_root, "HEAD")
    branch_remote = f"refs/heads/{branch_name}"
    backup_result = {"status": "not_needed"}
    if plan.get("force_needed"):
        backup_result = _push_tag(repo_root, remote, str(plan["backup_ref"]), old_remote_sha, dry_run=False)
        if backup_result.get("status") != "pushed":
            return {**plan, "status": "blocked", "blocker": "backup_ref_push_failed", "backup_ref_result": backup_result, "returncode": 1}

    push_audit = _push_audit(repo_root, remote)
    bypass = _classify_bypass(push_audit)
    if bypass["required"] and not bypass["allowed"]:
        return {
            **plan,
            "status": "blocked",
            "blocker": "push_policy_not_private_preservation_bypassable",
            "push_policy": push_audit,
            "hook_bypass": bypass,
            "backup_ref_result": backup_result,
            "returncode": 1,
        }

    push_args = ["git", "push"]
    if bypass["required"]:
        push_args.append("--no-verify")
    if plan.get("force_needed"):
        push_args.append(f"--force-with-lease=refs/heads/{branch_name}:{old_remote_sha}")
    push_args.extend([remote, f"{branch_name}:{branch_name}"])
    push = _run(repo_root, push_args)
    if push.returncode != 0:
        return {
            **plan,
            "status": "failed",
            "blocker": "push_failed",
            "push": {"args": push_args, "stdout": push.stdout.strip(), "stderr": push.stderr.strip()},
            "returncode": push.returncode,
        }

    remote_line = _run(repo_root, ["git", "ls-remote", remote, branch_remote]).stdout.strip()
    remote_sha = remote_line.split()[0] if remote_line else None
    backup_line = ""
    if plan.get("force_needed"):
        backup_line = _run(repo_root, ["git", "ls-remote", remote, str(plan["backup_ref"])]).stdout.strip()
    verified = bool(local_sha and remote_sha == local_sha)
    backup_verified = not plan.get("force_needed") or backup_line.startswith(old_remote_sha)
    return {
        **plan,
        "status": "green" if verified and backup_verified else "yellow",
        "checkpoints": checkpoints,
        "backup_ref_result": backup_result,
        "push": {
            "args": push_args,
            "stdout": push.stdout.strip(),
            "stderr": push.stderr.strip(),
            "used_no_verify": "--no-verify" in push_args,
            "used_force_with_lease": any(arg.startswith("--force-with-lease=") for arg in push_args),
        },
        "verified": {
            "local_sha": local_sha,
            "remote_sha": remote_sha,
            "remote_matches_local": verified,
            "backup_ref_verified": backup_verified,
        },
        "returncode": 0 if verified and backup_verified else 2,
    }


def _print_plan(payload: dict[str, Any]) -> None:
    status = payload.get("status")
    print(f"Private backup lane: {str(status).upper()}")
    privacy = payload.get("privacy") or {}
    print(f"privacy: {privacy.get('status')} ({privacy.get('slug') or privacy.get('remote_url')})")
    print(f"branch: {payload.get('branch')}")
    print(f"local SHA: {payload.get('local_sha')}")
    print(f"old remote SHA: {payload.get('old_remote_sha')}")
    print(f"backup ref: {payload.get('backup_ref')}")
    if payload.get("force_needed"):
        print(f"replacement: {payload.get('force_with_lease')}")
    else:
        print("replacement: not needed unless remote diverges")
    bypass = payload.get("hook_bypass") or {}
    print(f"hook bypass: {bypass.get('mode')} categories={bypass.get('error_categories')}")
    if payload.get("blocker"):
        print(f"blocked: {payload.get('blocker')}")
    print("not proven by GitHub remote:")
    for item in (payload.get("coverage") or {}).get("not_proven_by_git_remote", []):
        print(f"  - {item}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Checkpoint private backup lane.")
    parser.add_argument("mode", choices=("status", "private-backup"))
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="")
    parser.add_argument("--message", default="backup: private emergency preserve")
    parser.add_argument("--backup-ref-prefix", default="aiw-backup-origin-main")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-tail-drains", type=int, default=2)
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).expanduser().resolve()
    branch = args.branch.strip() or None
    try:
        if args.mode == "status":
            payload = build_status(repo_root, remote=args.remote, branch=branch)
            if args.json:
                _emit_json(payload)
            else:
                _print_status(payload)
            return 0 if payload.get("status") != "red" else 1
        payload = run_private_backup(
            repo_root,
            remote=args.remote,
            branch=branch,
            message=args.message,
            backup_ref_prefix=args.backup_ref_prefix,
            dry_run=args.dry_run,
            max_tail_drains=max(0, args.max_tail_drains),
        )
        if args.json:
            _emit_json(payload)
        else:
            _print_plan(payload)
        return int(payload.get("returncode") or (0 if payload.get("status") not in {"blocked", "failed"} else 1))
    except Exception as exc:
        payload = {
            "schema": "checkpoint_private_backup_error_v1",
            "status": "failed",
            "error": str(exc),
        }
        if args.json:
            _emit_json(payload)
        else:
            print(f"Private backup lane failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
