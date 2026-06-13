"""
[PURPOSE]
- Teleology: Provide the repo-aware `run_git` entrypoint for interactive git flows and policy-gated hook execution.
- Mechanism: Wrap git CLI operations with runtime-path policy checks, staging audits, tidy helpers, and optional Rich TUI prompts.
- Updates: Hook installer emits repo-local pre-commit and pre-push scripts that re-enter this module through `./repo-python`.

[INTERFACE]
- Inputs: CLI arguments for interactive flows, hook invocations, staging audits, and push validation.
- Outputs: Terminal prompts, policy violations, tidy summaries, and git subprocess exit codes/stdout/stderr relayed through this runner.
- Exports: `git`, `install_hooks`, `tidy_workspace`, `audit_staged_paths`, and policy dataclasses used by the local git workflow.

[CONSTRAINTS]
- Safety: Runtime-state paths, generated cache surfaces, and oversized blobs are rejected or warned before commit/push flows proceed.
- Scope: This module governs repo-local git policy and hook behavior; it does not own higher-level routing projection or telemetry scoring logic.
- When-needed: Open when you need the authoritative `run_git` entrypoint that enforces repo-aware git policy gates, installs hooks, or audits staged/pushed paths before local history advances.
- Escalates-to: codex/doctrine/skills/kernel/checkpoint.md; .githooks/; git CLI
- Navigation-group: repo_runtime
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    box = None
    Console = None
    Panel = None
    Confirm = None
    Prompt = None
    Table = None
    Text = None
    RICH_AVAILABLE = False

ROOT = Path(__file__).resolve().parent
HOOKS_DIR = ROOT / ".githooks"
HOOKS_PATH_TOKEN = ".githooks"
console = Console() if RICH_AVAILABLE else None

DIFF_LINE_LIMIT = 150
GITHUB_RECOMMENDED_FILE_BYTES = 50 * 1024 * 1024
GITHUB_HARD_FILE_BYTES = 100 * 1024 * 1024
MEMORY_SNAPSHOT_SOFT_LIMIT_BYTES = 5 * 1024 * 1024
PUSH_AUDIT_STATUS_SCHEMA = "push_audit_status_v1"
GUARDED_PUSH_RECEIPT_SCHEMA = "guarded_push_receipt_v1"
MULTI_COMMIT_RANGE_WATCH_REASON = "multi_commit_local_ahead_range"
ZERO_OID = "0" * 40

# ── Substrate-egress control: push remote allowlist ────────────────────────
# The asset worth protecting is the private substrate (this whole repository),
# not any one credential. So the load-bearing rule is: the substrate may only
# ever be pushed to the operator's private backup remote. A push to any other
# remote NAME, or to a NETWORK url that is not the allowlisted private identity,
# is refused. This is the guard against "exfiltrate the entire repo to <foreign
# / attacker remote>" — whether driven by a prompt-injection running
# `git push <somewhere>`, or by accidental misconfiguration.
#
# There is deliberately NO env-var override: an override is exactly what an
# injected instruction would set. To add a genuinely new private backup, edit
# the two constants below. Local/file remotes (used by the test suite and
# `git bundle`) are name-checked but exempt from the network-identity check.
# This is a prompt-injection / accident guard, NOT root-attacker prevention —
# anyone who can edit this file can also edit the allowlist.
ALLOWED_PUSH_REMOTE_NAMES = frozenset({"origin"})
ALLOWED_PUSH_REMOTE_URL_IDENTITY = ("wcook04/zenith",)

# ── Secret-content backstop ────────────────────────────────────────────────
# Defense-in-depth so a live credential committed into a TRACKED file is caught
# before it leaves the machine (the path/size audits never read blob CONTENT,
# and the checkpoint actuator commits via commit-tree, bypassing git hooks; the
# push audit is the one chokepoint every push path traverses). Intentionally
# self-contained — the commit/push critical path takes no extra import — and
# limited to HIGH-CONFIDENCE shapes to keep false positives near zero. The
# canonical, broader public-release scanner lives at
# tools/meta/microcosm_public_safety/public_path_secret_policy.py.
SECRET_CONTENT_SCAN_MAX_BYTES = 1_500_000
_SECRET_BINARY_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".tar", ".tgz", ".bz2", ".7z", ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".mov", ".wav", ".webm", ".so", ".dylib", ".bin", ".wasm",
    ".jar", ".class", ".heic", ".db", ".sqlite", ".sqlite3", ".parquet",
)
# Paths where credential-SHAPED strings are pattern definitions, scanner
# vocabulary, or negative-test fixtures — not live secrets.
_SECRET_PATH_ALLOW_SUBSTRINGS = (
    "test", "fixture", "mock", "example", "sample", "detect-secrets",
    "secret_exclusion_scan", "projection_secret_scan", "public_path_secret_policy",
    "run_git.py",
)
# When a matched token contains one of these, it is a redaction-test fixture or
# placeholder, not a live secret.
_SECRET_SYNTHETIC_MARKERS = (
    "example", "redact", "placeholder", "dummy", "sample", "your_", "xxxx",
    "abcdef", "123456", "fake", "notreal", "aaaaaa", "bbbbbb",
)
_SECRET_CONTENT_PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----")),
    ("anthropic key", re.compile(r"\bsk-ant-api\d{2}-[A-Za-z0-9_-]{20,}")),
    ("openai key", re.compile(r"\bsk-(?:proj-)?(?!ant-api)[A-Za-z0-9]{26,}")),
    ("google api key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("github fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}_[A-Za-z0-9_]{20,}")),
    ("gitlab token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}")),
    ("slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}")),
    ("aws access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("huggingface token", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    ("pypi token", re.compile(r"\bpypi-[A-Za-z0-9_-]{30,}")),
    ("npm token", re.compile(r"\bnpm_[A-Za-z0-9]{30,}")),
    ("sendgrid key", re.compile(r"\bSG\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
)

TRANSIENT_RUNTIME_EXACT_PATHS = {
    "tools/meta/apply/observe_plan.json": (
        "Active observe plan is runtime state, not durable repo knowledge."
    ),
    "tools/meta/apply/observe_result.json": (
        "Latest observe result is runtime state, not durable repo knowledge."
    ),
    "tools/meta/apply/apply_result.json": (
        "Latest apply result is runtime state, not durable repo knowledge."
    ),
    "tools/meta/apply/apply_loop_result.json": (
        "Closed-loop apply receipt is runtime state, not durable repo knowledge."
    ),
    "tools/meta/apply/scratchpad.md": (
        "Scratchpad is a local runtime aid and should not be versioned."
    ),
    "tools/meta/control/orchestration_state.json": (
        "Control-plane snapshot is a runtime authority projection, not a commit target."
    ),
    "tools/meta/control/orchestration_brief.json": (
        "Control-plane brief is a human projection of runtime state, not a commit target."
    ),
    "tools/meta/control/orchestration_brief.md": (
        "Control-plane brief is a human projection of runtime state, not a commit target."
    ),
    "tools/meta/control/orchestration_events.jsonl": (
        "Control-plane event log is append-only runtime state, not a commit target."
    ),
    "tools/meta/control/reactions_state.json": (
        "Reactions engine runtime state is local control-plane truth, not a commit target."
    ),
    "tools/meta/control/reactions_ledger.jsonl": (
        "Reactions engine ledger is append-only runtime state, not a commit target."
    ),
    "tools/meta/control/reactions_stop.flag": (
        "Reactions engine stop flag is runtime control state, not a commit target."
    ),
    "tools/meta/bridge/claude_active_session.json": (
        "Active session heartbeat is hook-stamped runtime identity, not a commit target."
    ),
    "tools/meta/bridge/claude_session_transport.json": (
        "One-shot session launch envelope is per-launch runtime state, not a commit target."
    ),
    "tools/meta/bridge/claude_session_resume.json": (
        "Session resume breadcrumb is runtime state, not a commit target."
    ),
    "tools/meta/bridge/claude_launch_mode.txt": (
        "Launch mode pointer is runtime state, not a commit target."
    ),
    "tools/meta/bridge/experiment_ledger.jsonl": (
        "Bridge experiment ledger is append-only local runtime history, not a commit target."
    ),
    "tools/meta/bridge/resume_ledger.jsonl": (
        "Bridge resume ledger is append-only local runtime history, not a commit target."
    ),
    "annexes/annex_catalog.json": (
        "Annex catalog is regenerated by annex_import.py from the on-disk clones; do not commit."
    ),
}

TRANSIENT_RUNTIME_PREFIXES = {
    "tools/meta/apply/observe_dumps/": (
        "Observe dumps are runtime evidence and should not be committed."
    ),
    "tools/meta/apply/observe_history/": (
        "Observe history is runtime evidence and should not be committed."
    ),
    "tools/meta/apply/snapshots/": (
        "Apply rollback snapshots are a local rollback cache, not shared history."
    ),
    "tools/meta/apply/observe_plans/": (
        "Draft observe plans are per-run scratch; the active plan is runtime state."
    ),
    "tools/meta/bridge/injector_inbox/": (
        "Injector inbox holds live trigger files; runtime, not committed."
    ),
    "tools/meta/bridge/injector_archive/": (
        "Consumed injector triggers are local history, not committed."
    ),
    "tools/meta/bridge/smart_test_runs/": (
        "Smart-test outputs are per-run artifacts, not committed."
    ),
    "tools/meta/bridge/resume_manifests/": (
        "Manual-mode resume manifests are per-run scratch, not committed."
    ),
    "external/": (
        "external/ holds cloned third-party repositories — GitHub is the substrate, do not commit."
    ),
    "obsidian/phases/": (
        "obsidian/phases/ is a phantom phase root — phase scaffolds belong under "
        "'obsidian/okay lets do this/'. If this dir exists, a tool wrote to the wrong parent."
    ),
    "obsidian/workstream/": (
        "obsidian/workstream/ is a phantom workstream root — workstream founders belong under "
        "'obsidian/okay lets do this/'. If this dir exists, a tool wrote to the wrong parent."
    ),
}

# Glob-style patterns (fnmatch) for runtime paths that can't be expressed
# as a simple exact path or prefix (e.g. annex clone subdirs).
TRANSIENT_RUNTIME_GLOBS = {
    "annexes/*/repo/*": (
        "annexes/<slug>/repo/ is a GitHub clone (substrate); do not commit the clone contents."
    ),
    "annexes/*/repo": (
        "annexes/<slug>/repo/ is a GitHub clone (substrate); do not commit the clone directory."
    ),
    "annexes/*/annex_contents.json": (
        "annex_contents.json is regenerated by annex_import.py; do not commit."
    ),
    "annexes/*/annex_sync_report.json": (
        "annex_sync_report.json is a validate/sync runtime diagnostic; do not commit."
    ),
}

REPLACEABLE_GENERATED_EXACT_PATHS = {
    "codex/hologram/system/navigation_cache.json": (
        "Semantic navigation cache is replaceable output and must stay out of normal git history."
    ),
}

GITIGNORE_RUNTIME_LINES = (
    "tools/meta/apply/observe_dumps/",
    "tools/meta/apply/observe_history/",
    "tools/meta/control/orchestration_state.json",
    "tools/meta/control/orchestration_brief.json",
    "tools/meta/control/orchestration_brief.md",
    "tools/meta/control/orchestration_events.jsonl",
    "tools/meta/control/reactions_state.json",
    "tools/meta/control/reactions_ledger.jsonl",
    "tools/meta/control/reactions_stop.flag",
    "codex/hologram/",
    "annexes/*/annex_sync_report.json",
)

PRE_COMMIT_SCRIPT = """#!/bin/sh
set -eu
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
exec ./repo-python run_git.py hook pre-commit
"""

PRE_PUSH_SCRIPT = """#!/bin/sh
set -eu
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
exec ./repo-python run_git.py hook pre-push --remote-name "${1:-origin}" --remote-url "${2:-}"
"""

AUTO_TIDY_EXACT_PATHS = tuple(
    sorted({*TRANSIENT_RUNTIME_EXACT_PATHS.keys(), *REPLACEABLE_GENERATED_EXACT_PATHS.keys()})
)
AUTO_TIDY_PREFIX_PATHS = tuple(sorted(TRANSIENT_RUNTIME_PREFIXES.keys()))
LAST_TIDY_STATUS = "not run"


@dataclass(frozen=True)
class GitPolicyViolation:
    category: str
    path: str
    detail: str
    remediation: str
    source: str
    size_bytes: int | None = None
    severity: str = "error"


@dataclass(frozen=True)
class PushUpdate:
    local_ref: str
    local_oid: str
    remote_ref: str
    remote_oid: str


@dataclass(frozen=True)
class WorkspaceTidyResult:
    unstaged_paths: int
    hidden_paths: int
    errors: tuple[str, ...] = ()


def git(*args: str, input_text: str | None = None) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        input=input_text,
        check=False,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _format_bytes(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "unknown size"
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{int(size_bytes)} B"


def _path_is_runtime(path: str) -> tuple[bool, str | None]:
    exact = TRANSIENT_RUNTIME_EXACT_PATHS.get(path)
    if exact is not None:
        return True, exact
    for prefix, reason in TRANSIENT_RUNTIME_PREFIXES.items():
        if path.startswith(prefix):
            return True, reason
    for pattern, reason in TRANSIENT_RUNTIME_GLOBS.items():
        if fnmatch.fnmatchcase(path, pattern):
            return True, reason
    return False, None


def _path_is_replaceable_generated(path: str) -> tuple[bool, str | None]:
    reason = REPLACEABLE_GENERATED_EXACT_PATHS.get(path)
    return (reason is not None, reason)


def _policy_violation_for_path(
    *,
    path: str,
    size_bytes: int | None,
    source: str,
) -> list[GitPolicyViolation]:
    violations: list[GitPolicyViolation] = []

    is_runtime, runtime_reason = _path_is_runtime(path)
    if is_runtime:
        if source == "push":
            remediation = (
                "A later deletion is not enough because this path is already inside the push range. "
                "Rewrite the local branch history or cherry-pick onto a clean branch before pushing."
            )
        else:
            remediation = (
                "Unstage this path and keep it local. If it is still tracked, remove it from the index "
                "with `git rm --cached -- <path>` after committing the ignore rule."
            )
        violations.append(
            GitPolicyViolation(
                category="runtime_artifact",
                path=path,
                detail=runtime_reason or "Runtime artifact should stay out of commits.",
                remediation=remediation.replace("<path>", path),
                source=source,
                size_bytes=size_bytes,
            )
        )

    is_replaceable, replaceable_reason = _path_is_replaceable_generated(path)
    if is_replaceable:
        if source == "push":
            remediation = (
                "This builder snapshot is already in the commits being pushed. Removing it in a later commit "
                "will not unblock GitHub; rewrite the local history or move the intended changes onto a clean branch."
            )
        else:
            remediation = (
                "Do not stage this file. Keep it ignored locally and remove it from the index with "
                f"`git rm --cached -- {path}` once the ignore rule is committed."
            )
        violations.append(
            GitPolicyViolation(
                category="replaceable_generated_artifact",
                path=path,
                detail=replaceable_reason or "Replaceable generated artifact should stay out of normal git history.",
                remediation=remediation,
                source=source,
                size_bytes=size_bytes,
            )
        )

    if size_bytes is not None and size_bytes > GITHUB_HARD_FILE_BYTES:
        violations.append(
            GitPolicyViolation(
                category="oversize_blob",
                path=path,
                detail=(
                    f"Blob is {_format_bytes(size_bytes)}, which exceeds GitHub's hard limit "
                    f"of {_format_bytes(GITHUB_HARD_FILE_BYTES)}."
                ),
                remediation=(
                    "Remove the blob from the commit range before pushing. If it is already in local history, "
                    "rewrite the local branch or rebuild the work on top of a clean branch."
                ),
                source=source,
                size_bytes=size_bytes,
            )
        )
    elif size_bytes is not None and size_bytes > GITHUB_RECOMMENDED_FILE_BYTES:
        violations.append(
            GitPolicyViolation(
                category="large_blob_warning",
                path=path,
                detail=(
                    f"Blob is {_format_bytes(size_bytes)}, above GitHub's recommended ceiling "
                    f"of {_format_bytes(GITHUB_RECOMMENDED_FILE_BYTES)}."
                ),
                remediation=(
                    "Keep large generated or binary artifacts out of normal git history. Prefer a smaller committed "
                    "projection or keep the artifact local."
                ),
                source=source,
                size_bytes=size_bytes,
                severity="warning",
            )
        )

    if path == "codex/hologram/system/navigation_cache.json" and size_bytes is not None:
        if size_bytes > MEMORY_SNAPSHOT_SOFT_LIMIT_BYTES:
            violations.append(
                GitPolicyViolation(
                    category="navigation_cache_drift",
                    path=path,
                    detail=(
                        f"Navigation cache is {_format_bytes(size_bytes)}, which indicates the builder is folding "
                        "too much semantic detail into a replaceable cache projection."
                    ),
                    remediation=(
                        "Rebuild after the cache denormalization bounds land. This artifact should stay local and "
                        "bounded, not tracked as evolving history."
                    ),
                    source=source,
                    size_bytes=size_bytes,
                    severity="warning" if source == "staged" else "error",
                )
            )

    return violations


def _has_errors(violations: list[GitPolicyViolation]) -> bool:
    return any(item.severity == "error" for item in violations)


def _unique_violations(violations: list[GitPolicyViolation]) -> list[GitPolicyViolation]:
    deduped: dict[tuple[str, str, str, str], GitPolicyViolation] = {}
    for item in violations:
        key = (item.category, item.path, item.detail, item.remediation)
        current = deduped.get(key)
        if current is None:
            deduped[key] = item
            continue
        if (item.size_bytes or 0) > (current.size_bytes or 0):
            deduped[key] = item
    return sorted(
        deduped.values(),
        key=lambda item: (
            0 if item.severity == "error" else 1,
            item.path,
            item.category,
        ),
    )


def _runtime_push_group(path: str) -> str:
    for prefix in TRANSIENT_RUNTIME_PREFIXES:
        if path.startswith(prefix):
            return prefix
    return path


def _compress_push_violations(violations: list[GitPolicyViolation]) -> list[GitPolicyViolation]:
    grouped: dict[tuple[str, str], list[GitPolicyViolation]] = {}
    passthrough: list[GitPolicyViolation] = []

    for item in violations:
        if item.source != "push" or item.category != "runtime_artifact":
            passthrough.append(item)
            continue
        key = ("runtime_artifact", _runtime_push_group(item.path))
        grouped.setdefault(key, []).append(item)

    compressed: list[GitPolicyViolation] = []
    for (_, group_path), items in grouped.items():
        exemplar = items[0]
        if len(items) == 1 and group_path == exemplar.path:
            compressed.append(exemplar)
            continue
        max_size = max((item.size_bytes or 0 for item in items), default=0) or None
        compressed.append(
            GitPolicyViolation(
                category="runtime_artifact",
                path=group_path,
                detail=(
                    f"{exemplar.detail} Outgoing range still contains {len(items)} path(s) under this runtime surface."
                ),
                remediation=exemplar.remediation,
                source="push",
                size_bytes=max_size,
                severity=exemplar.severity,
            )
        )

    return _unique_violations([*passthrough, *compressed])


def _print_violations(
    violations: list[GitPolicyViolation],
    *,
    stream: TextIO,
    heading: str,
) -> None:
    if not violations:
        return
    print(heading, file=stream)
    for item in violations:
        level = "ERROR" if item.severity == "error" else "WARN"
        size_note = f" [{_format_bytes(item.size_bytes)}]" if item.size_bytes is not None else ""
        print(f"  {level} {item.path}{size_note}", file=stream)
        print(f"    {item.detail}", file=stream)
        print(f"    Fix: {item.remediation}", file=stream)


def _tracked_blob_size(object_spec: str) -> int | None:
    code, out, _ = git("cat-file", "-s", object_spec)
    if code != 0 or not out:
        return None
    try:
        return int(out.strip())
    except ValueError:
        return None


def _read_blob_bytes(object_spec: str) -> bytes | None:
    result = subprocess.run(
        ["git", "cat-file", "blob", object_spec],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _is_secret_scan_candidate(path: str, size_bytes: int | None) -> bool:
    """Skip allow-listed paths (tests/fixtures/scanner vocabulary), binary
    suffixes, and oversize blobs so only plausible live-secret text is read."""
    lower_path = path.lower()
    if any(token in lower_path for token in _SECRET_PATH_ALLOW_SUBSTRINGS):
        return False
    if lower_path.endswith(_SECRET_BINARY_SUFFIXES):
        return False
    if size_bytes is not None and size_bytes > SECRET_CONTENT_SCAN_MAX_BYTES:
        return False
    return True


def _match_secret_patterns(
    *, raw: bytes, path: str, source: str, size_bytes: int | None
) -> list[GitPolicyViolation]:
    """Flag high-confidence live-credential shapes in one blob's bytes.

    Binary blobs and tokens carrying synthetic markers (redaction-test
    fixtures / placeholders) are skipped. One violation per credential kind
    per file.
    """
    if not raw or b"\x00" in raw[:8192]:  # empty or binary -> skip
        return []
    text = raw.decode("utf-8", errors="ignore")
    if source == "push":
        remediation = (
            "A live secret is in the commits being pushed. Removing it in a later commit will NOT "
            "un-leak it — ROTATE the credential now, then rewrite the local history (git filter-repo) "
            "to purge the blob before pushing. Keep secrets in a gitignored .env or a secret manager."
        )
    else:
        remediation = (
            "Unstage this file, remove the credential, and ROTATE it immediately. Keep secrets in a "
            "gitignored .env or a secret manager, never in a tracked file. If this is a synthetic test "
            "fixture, mark the value with EXAMPLE/REDACTED or move it under a tests/fixtures path."
        )
    violations: list[GitPolicyViolation] = []
    for kind, pattern in _SECRET_CONTENT_PATTERNS:
        for match in pattern.finditer(text):
            lowered = match.group(0).lower()
            if any(marker in lowered for marker in _SECRET_SYNTHETIC_MARKERS):
                continue
            violations.append(
                GitPolicyViolation(
                    category="secret_content",
                    path=path,
                    detail=f"Possible live {kind} committed in this file.",
                    remediation=remediation,
                    source=source,
                    size_bytes=size_bytes,
                    severity="error",
                )
            )
            break  # first real match for this credential kind is enough
    return violations


def _scan_blob_content_for_secrets(
    *,
    object_spec: str,
    path: str,
    source: str,
    size_bytes: int | None,
) -> list[GitPolicyViolation]:
    """Staged path: read one tracked blob and scan it for live secrets."""
    if not _is_secret_scan_candidate(path, size_bytes):
        return []
    raw = _read_blob_bytes(object_spec)
    if raw is None:
        return []
    return _match_secret_patterns(raw=raw, path=path, source=source, size_bytes=size_bytes)


def _scan_push_objects_for_secrets(
    objects: dict[str, tuple[str, int | None]],
) -> list[GitPolicyViolation]:
    """Push path: scan candidate blobs in the push range for live secrets.

    Reads content via batched `git cat-file --batch` (one subprocess per chunk
    instead of one per blob) so auditing a large local-ahead range stays fast.
    """
    candidates = [
        (object_id, path, size_bytes)
        for path, (object_id, size_bytes) in objects.items()
        if _is_secret_scan_candidate(path, size_bytes)
    ]
    if not candidates:
        return []
    by_oid: dict[str, tuple[str, int | None]] = {
        object_id: (path, size_bytes) for object_id, path, size_bytes in candidates
    }
    violations: list[GitPolicyViolation] = []
    for chunk in _chunked(list(by_oid.keys()), chunk_size=256):
        proc = subprocess.run(
            ["git", "cat-file", "--batch"],
            cwd=ROOT,
            input=("\n".join(chunk) + "\n").encode(),
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            continue
        data = proc.stdout
        pos = 0
        length = len(data)
        while pos < length:
            newline = data.find(b"\n", pos)
            if newline == -1:
                break
            header = data[pos:newline].decode("utf-8", errors="ignore").split()
            pos = newline + 1
            if len(header) != 3:
                # "<oid> missing" (2 tokens) has no body to skip past.
                continue
            object_id, object_type, raw_size = header
            try:
                blob_size = int(raw_size)
            except ValueError:
                break  # malformed stream; stop parsing this chunk safely
            body = data[pos : pos + blob_size]
            pos += blob_size + 1  # skip body and its trailing newline
            if object_type != "blob":
                continue
            path, size_bytes = by_oid.get(object_id, (object_id, blob_size))
            violations.extend(
                _match_secret_patterns(raw=body, path=path, source="push", size_bytes=size_bytes)
            )
    return violations


def _current_hooks_path() -> str | None:
    code, out, _ = git("config", "--get", "core.hooksPath")
    if code != 0 or not out.strip():
        return None
    return out.strip()


def _hook_status_label() -> str:
    current = _current_hooks_path()
    if current == HOOKS_PATH_TOKEN:
        return "installed"
    if current:
        return f"custom ({current})"
    return "not installed"


def _ensure_hook_permissions() -> None:
    for hook_path in (HOOKS_DIR / "pre-commit", HOOKS_DIR / "pre-push"):
        if not hook_path.exists():
            continue
        mode = hook_path.stat().st_mode
        hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_hooks() -> tuple[bool, str]:
    if not HOOKS_DIR.exists():
        return False, f"Missing hooks directory: {HOOKS_DIR}"
    _ensure_hook_permissions()
    code, _, err = git("config", "core.hooksPath", HOOKS_PATH_TOKEN)
    if code != 0:
        return False, err or "git config core.hooksPath failed"
    return True, f"Installed repo hooks via core.hooksPath={HOOKS_PATH_TOKEN}"


def _chunked(values: list[str], chunk_size: int = 200) -> list[list[str]]:
    return [values[index : index + chunk_size] for index in range(0, len(values), chunk_size)]


def _tracked_paths_matching_tidy_policy() -> list[str]:
    tokens = [*AUTO_TIDY_EXACT_PATHS, *AUTO_TIDY_PREFIX_PATHS]
    if not tokens and not TRANSIENT_RUNTIME_GLOBS:
        return []
    code, out, err = git("ls-files")
    if code != 0:
        raise RuntimeError(err or "git ls-files failed")
    tracked = [line.strip() for line in out.splitlines() if line.strip()]
    matched: list[str] = []
    for path in tracked:
        is_runtime, _ = _path_is_runtime(path)
        if is_runtime:
            matched.append(path)
    return matched


def tidy_workspace() -> WorkspaceTidyResult:
    errors: list[str] = []
    unstaged = 0
    hidden = 0

    try:
        staged_paths = _stage_paths()
        staged_tidy = [
            path
            for path in staged_paths
            if _path_is_runtime(path)[0] or _path_is_replaceable_generated(path)[0]
        ]
        for chunk in _chunked(staged_tidy):
            code, _, err = git("restore", "--staged", "--", *chunk)
            if code != 0:
                errors.append(err or "git restore --staged failed")
                break
            unstaged += len(chunk)
    except Exception as exc:
        errors.append(str(exc))

    try:
        tracked_paths = _tracked_paths_matching_tidy_policy()
        for chunk in _chunked(tracked_paths):
            code, _, err = git("update-index", "--skip-worktree", "--", *chunk)
            if code != 0:
                errors.append(err or "git update-index --skip-worktree failed")
                break
            hidden += len(chunk)
    except Exception as exc:
        errors.append(str(exc))

    return WorkspaceTidyResult(
        unstaged_paths=unstaged,
        hidden_paths=hidden,
        errors=tuple(errors),
    )


def _stage_paths() -> list[str]:
    code, out, err = git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    if code != 0:
        raise RuntimeError(err or "git diff --cached failed")
    return [line.strip() for line in out.splitlines() if line.strip()]


def audit_staged_paths() -> list[GitPolicyViolation]:
    violations: list[GitPolicyViolation] = []
    for path in _stage_paths():
        size_bytes = _tracked_blob_size(f":{path}")
        violations.extend(_policy_violation_for_path(path=path, size_bytes=size_bytes, source="staged"))
        violations.extend(
            _scan_blob_content_for_secrets(
                object_spec=f":{path}", path=path, source="staged", size_bytes=size_bytes
            )
        )
    return _unique_violations(violations)


def _parse_push_stdin(stdin_text: str) -> list[PushUpdate]:
    updates: list[PushUpdate] = []
    for raw in stdin_text.splitlines():
        parts = raw.strip().split()
        if len(parts) != 4:
            continue
        updates.append(
            PushUpdate(
                local_ref=parts[0],
                local_oid=parts[1],
                remote_ref=parts[2],
                remote_oid=parts[3],
            )
        )
    return updates


def _zero_oid(value: str) -> bool:
    token = str(value or "").strip()
    return bool(token) and set(token) == {"0"}


def _normalize_expected_oid(value: str | None) -> str:
    token = str(value or "").strip()
    return token if token else ZERO_OID


def _ls_remote_oid(remote_name: str, target_ref: str) -> tuple[str | None, str | None]:
    code, out, err = git("ls-remote", remote_name, target_ref)
    if code != 0:
        return None, err or "git ls-remote failed"
    line = out.splitlines()[0].strip() if out.strip() else ""
    if not line:
        return ZERO_OID, None
    parts = line.split()
    if not parts:
        return ZERO_OID, None
    return parts[0], None


def _current_branch_push_update(remote_name: str) -> list[PushUpdate]:
    local_ref = branch()
    local_oid_code, local_oid, local_oid_err = git("rev-parse", "HEAD")
    if local_oid_code != 0:
        raise RuntimeError(local_oid_err or "git rev-parse HEAD failed")

    upstream_code, upstream_ref, _ = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if upstream_code != 0 or not upstream_ref.strip():
        return [
            PushUpdate(
                local_ref=local_ref,
                local_oid=local_oid.strip(),
                remote_ref=f"refs/heads/{local_ref}",
                remote_oid="0" * 40,
            )
        ]

    remote_ref = upstream_ref.strip()
    remote_oid_code, remote_oid, _ = git("rev-parse", remote_ref)
    normalized_remote_ref = remote_ref
    if remote_ref.startswith(f"refs/remotes/{remote_name}/"):
        normalized_remote_ref = f"refs/heads/{remote_ref.split('/', 3)[-1]}"
    return [
        PushUpdate(
            local_ref=local_ref,
            local_oid=local_oid.strip(),
            remote_ref=normalized_remote_ref,
            remote_oid=remote_oid.strip() if remote_oid_code == 0 else "0" * 40,
        )
    ]


def _collect_push_objects(remote_name: str, updates: list[PushUpdate]) -> dict[str, tuple[str, int | None]]:
    objects: dict[str, tuple[str, int | None]] = {}
    remote_token = remote_name or "origin"

    for update in updates:
        if _zero_oid(update.local_oid):
            continue
        if _zero_oid(update.remote_oid):
            code, out, err = git(
                "rev-list",
                "--objects",
                update.local_oid,
                "--not",
                f"--remotes={remote_token}",
            )
        else:
            code, out, err = git("rev-list", "--objects", f"{update.remote_oid}..{update.local_oid}")
        if code != 0:
            raise RuntimeError(err or "git rev-list --objects failed")

        object_ids: list[str] = []
        object_paths: list[tuple[str, str]] = []
        for line in out.splitlines():
            if " " not in line:
                continue
            object_id, path = line.split(" ", 1)
            clean_path = path.strip()
            if not clean_path:
                continue
            object_ids.append(object_id)
            object_paths.append((object_id, clean_path))

        sizes: dict[str, int | None] = {}
        if object_ids:
            result = subprocess.run(
                ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                input="\n".join(object_ids) + "\n",
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "git cat-file --batch-check failed")
            for line in result.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) != 3:
                    continue
                object_id, object_type, object_size = parts
                if object_type != "blob":
                    continue
                try:
                    sizes[object_id] = int(object_size)
                except ValueError:
                    sizes[object_id] = None

        for object_id, path in object_paths:
            size_bytes = sizes.get(object_id)
            current = objects.get(path)
            if current is None:
                objects[path] = (object_id, size_bytes)
                continue
            _, current_size = current
            if (size_bytes or 0) > (current_size or 0):
                objects[path] = (object_id, size_bytes)

    return objects


def audit_push_updates(remote_name: str, updates: list[PushUpdate]) -> list[GitPolicyViolation]:
    violations: list[GitPolicyViolation] = []
    objects = _collect_push_objects(remote_name, updates)
    for path, (_, size_bytes) in objects.items():
        violations.extend(_policy_violation_for_path(path=path, size_bytes=size_bytes, source="push"))
    violations.extend(_scan_push_objects_for_secrets(objects))
    return _compress_push_violations(violations)


def audit_push(remote_name: str, stdin_text: str | None = None) -> list[GitPolicyViolation]:
    updates = _parse_push_stdin(stdin_text or "")
    if not updates:
        updates = _current_branch_push_update(remote_name)
    return audit_push_updates(remote_name, updates)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _git_int(args: tuple[str, ...] | list[str]) -> int | None:
    code, out, _ = git(*list(args))
    if code != 0 or not out.strip():
        return None
    try:
        return int(out.strip())
    except ValueError:
        return None


def _current_upstream_name() -> str | None:
    code, out, _ = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if code != 0 or not out.strip():
        return None
    return out.strip()


def _tracking_counts(upstream_name: str | None) -> tuple[int | None, int | None]:
    if not upstream_name:
        return None, None
    code, out, _ = git("rev-list", "--left-right", "--count", f"{upstream_name}...HEAD")
    if code != 0 or not out.strip():
        return None, None
    parts = out.split()
    if len(parts) != 2:
        return None, None
    try:
        behind = int(parts[0])
        ahead = int(parts[1])
    except ValueError:
        return None, None
    return ahead, behind


def _push_range_commit_count(remote_oid: str | None, head: str | None) -> int | None:
    remote = _normalize_expected_oid(remote_oid)
    source = _normalize_expected_oid(head)
    if not remote or not source or _zero_oid(remote):
        return None
    return _git_int(("rev-list", "--count", f"{remote}..{source}"))


def _push_violation_rows(violations: list[GitPolicyViolation]) -> list[dict[str, object]]:
    return [
        {
            "category": item.category,
            "path": item.path,
            "detail": item.detail,
            "remediation": item.remediation,
            "source": item.source,
            "size_bytes": item.size_bytes,
            "severity": item.severity,
        }
        for item in violations
    ]


def _push_status_for(
    violations: list[GitPolicyViolation],
    *,
    ahead: int | None,
    behind: int | None,
    update_count: int,
) -> tuple[str, list[str], list[str]]:
    blocked_reasons = sorted({item.category for item in violations if item.severity == "error"})
    watch_reasons = sorted({item.category for item in violations if item.severity != "error"})
    if update_count == 0:
        return "unknown", blocked_reasons, [*watch_reasons, "no_push_updates_resolved"]
    if blocked_reasons:
        return "blocked", blocked_reasons, watch_reasons
    if behind:
        return "watch", blocked_reasons, [*watch_reasons, "local_branch_behind_upstream"]
    if watch_reasons:
        return "watch", blocked_reasons, watch_reasons
    return "clear", blocked_reasons, watch_reasons


def _remote_ref_for_branch(remote_name: str, branch_name: str) -> str:
    upstream_name = _current_upstream_name()
    if upstream_name and upstream_name.startswith(f"{remote_name}/"):
        return f"refs/heads/{upstream_name.split('/', 1)[1]}"
    return f"refs/heads/{branch_name}"


def _normalize_remote_ref(remote_name: str, remote_ref: str, branch_name: str) -> str:
    value = str(remote_ref or "").strip()
    if value.startswith("refs/remotes/"):
        parts = value.split("/", 3)
        if len(parts) == 4:
            return f"refs/heads/{parts[3]}"
    if value.startswith(f"{remote_name}/"):
        return f"refs/heads/{value.split('/', 1)[1]}"
    if value.startswith("refs/heads/"):
        return value
    return _remote_ref_for_branch(remote_name, branch_name)


def build_push_audit_status(
    *,
    remote_name: str,
    stdin_text: str | None = None,
) -> dict[str, object]:
    updates = _parse_push_stdin(stdin_text or "")
    resolved_from_stdin = bool(updates)
    if not updates:
        updates = _current_branch_push_update(remote_name)
    violations = audit_push_updates(remote_name, updates)

    branch_name = branch()
    upstream_name = _current_upstream_name()
    ahead, behind = _tracking_counts(upstream_name)
    head_code, head, _ = git("rev-parse", "HEAD")
    head = head.strip() if head_code == 0 else ""
    target_ref = (
        _normalize_remote_ref(remote_name, updates[0].remote_ref, branch_name)
        if updates
        else _remote_ref_for_branch(remote_name, branch_name)
    )
    remote_oid = updates[0].remote_oid if updates else ZERO_OID
    remote_lookup_oid, remote_lookup_error = _ls_remote_oid(remote_name, target_ref)
    audited_remote_oid = remote_lookup_oid or remote_oid
    remote_ref_verified = bool(audited_remote_oid and not _zero_oid(audited_remote_oid))
    push_range_commit_count = _push_range_commit_count(audited_remote_oid, head)
    if push_range_commit_count is None:
        push_range_commit_count = ahead
    status, blocked_reasons, watch_reasons = _push_status_for(
        violations,
        ahead=ahead,
        behind=behind,
        update_count=len(updates),
    )
    range_widening_risk = bool((push_range_commit_count or 0) > 1)
    if range_widening_risk:
        watch_reasons = sorted({*watch_reasons, MULTI_COMMIT_RANGE_WATCH_REASON})
        if status == "clear":
            status = "watch"
    direct_push_allowed = (
        status in {"clear", "watch"}
        and not blocked_reasons
        and not (behind or 0)
        and not range_widening_risk
    )
    next_safe_command = None
    publication_lane_command = "./repo-python tools/meta/control/publication_lane.py plan --repo-root ."
    guarded_push: dict[str, object] | None = None
    if direct_push_allowed and (ahead or resolved_from_stdin) and head and remote_ref_verified:
        next_safe_command = (
            "./repo-python run_git.py push guarded "
            f"--remote-name {remote_name} "
            "--source-ref HEAD "
            f"--target-ref {target_ref} "
            f"--expected-source {head} "
            f"--expected-remote {audited_remote_oid} "
            "--json"
        )
        guarded_push = {
            "schema": GUARDED_PUSH_RECEIPT_SCHEMA,
            "command": next_safe_command,
            "source_ref": "HEAD",
            "audited_source_sha": head,
            "remote_name": remote_name,
            "target_ref": target_ref,
            "audited_remote_sha": audited_remote_oid,
            "push_refspec": f"{head}:{target_ref}",
        }
    return {
        "kind": "push_audit_status",
        "schema": PUSH_AUDIT_STATUS_SCHEMA,
        "generated_at": _utc_now(),
        "status": status,
        "branch": branch_name,
        "head": head or None,
        "remote_name": remote_name,
        "upstream": upstream_name,
        "target_ref": target_ref,
        "remote_oid": None if _zero_oid(audited_remote_oid) else audited_remote_oid,
        "remote_ref_verified": remote_ref_verified,
        "remote_ref_verification": (
            "ls_remote" if remote_lookup_oid and not remote_lookup_error else (
                "local_tracking_ref" if remote_ref_verified else "not_verified_locally"
            )
        ),
        "remote_ref_lookup_error": remote_lookup_error,
        "audit_identity": {
            "source_ref": "HEAD",
            "audited_source_sha": head or None,
            "remote_name": remote_name,
            "target_ref": target_ref,
            "audited_remote_sha": None if _zero_oid(audited_remote_oid) else audited_remote_oid,
            "remote_ref_verification": (
                "ls_remote" if remote_lookup_oid and not remote_lookup_error else (
                    "local_tracking_ref" if remote_ref_verified else "not_verified_locally"
                )
            ),
        },
        "ahead": ahead,
        "behind": behind,
        "push_range_commit_count": push_range_commit_count,
        "range_widening_risk": range_widening_risk,
        "update_count": len(updates),
        "updates_from_stdin": resolved_from_stdin,
        "blocked_reasons": blocked_reasons,
        "watch_reasons": watch_reasons,
        "violation_count": len(violations),
        "error_count": sum(1 for item in violations if item.severity == "error"),
        "warning_count": sum(1 for item in violations if item.severity != "error"),
        "violations": _push_violation_rows(violations),
        "direct_push_allowed": direct_push_allowed,
        "next_safe_command": next_safe_command,
        "publication_lane_command": publication_lane_command if range_widening_risk else None,
        "guarded_push": guarded_push,
        "evidence": {
            "policy_surface": "run_git.py audit push",
            "object_scan": "git rev-list --objects over resolved push updates",
            "range_width_policy": (
                "direct push is disabled when the audited range contains more than one commit; "
                "use publication_lane for multi-commit local-ahead ranges"
            ),
            "tracking_counts": "git rev-list --left-right --count @{upstream}...HEAD"
            if upstream_name
            else "no_upstream",
            "empty_output_policy": "json mode always emits this positive status object",
            "publication_identity_rule": "guarded push must reuse audited source and remote identities",
        },
    }


def _resolve_remote_url(remote_name: str) -> str:
    name = (remote_name or "").strip()
    if not name:
        return ""
    code, out, _ = git("remote", "get-url", name)
    if code == 0 and out.strip():
        return out.strip()
    return ""


def _is_network_remote_url(url: str) -> bool:
    """True for urls that would carry the substrate off this machine.

    Local/file remotes (absolute paths, file://) are used by the test suite and
    `git bundle`; they are exempt from the network-identity check (but a
    determined local exfil still trips the remote-NAME allowlist).
    """
    token = (url or "").strip()
    if not token:
        return False
    if token.startswith(("http://", "https://", "ssh://", "git://", "ftp://", "ftps://")):
        return True
    # scp-like syntax: user@host:path  (e.g. git@github.com:wcook04/zenith.git)
    if re.match(r"^[^/@\s]+@[^/:\s]+:", token):
        return True
    return False


def _push_remote_policy_violations(
    remote_name: str, remote_url: str | None = None, *, resolve_url: bool = True
) -> list[GitPolicyViolation]:
    """Refuse any push whose destination is not the allowlisted private backup.

    When ``resolve_url`` is False the remote url is NOT looked up via git: this is
    used by the guarded-push actuator, whose own ``git push`` re-fires the
    pre-push hook where the real target url IS validated. The name allowlist
    still applies in both modes.
    """
    name = (remote_name or "").strip()
    url = (remote_url or "").strip()
    if not url and resolve_url:
        url = _resolve_remote_url(name)

    name_allowed = name in ALLOWED_PUSH_REMOTE_NAMES
    # A url-shaped "name" (someone ran `git push <url> ...`) is never an allowed name.
    name_is_rawish_url = _is_network_remote_url(name)
    identity_ok = (not _is_network_remote_url(url)) or any(
        token in url for token in ALLOWED_PUSH_REMOTE_URL_IDENTITY
    )

    if name_allowed and identity_ok and not name_is_rawish_url:
        return []

    return [
        GitPolicyViolation(
            category="disallowed_push_remote",
            path=name or url or "<unknown remote>",
            detail=(
                f"Refusing to push to remote name={name or '?'!r} url={url or '?'!r}. "
                "The private substrate may only be pushed to the allowlisted private "
                "backup (origin -> wcook04/zenith). This blocks exfiltration of the "
                "entire repository to a foreign or attacker-controlled remote."
            ),
            remediation=(
                "If you are intentionally adding a new private backup, add it to "
                "ALLOWED_PUSH_REMOTE_NAMES / ALLOWED_PUSH_REMOTE_URL_IDENTITY in run_git.py. "
                "There is deliberately no env-var override (an override is exactly what a "
                "prompt-injection would set)."
            ),
            source="push",
            severity="error",
        )
    ]


def _guarded_push_base_receipt(
    *,
    remote_name: str,
    source_ref: str,
    target_ref: str,
    expected_source: str,
    expected_remote: str,
    dry_run: bool,
) -> dict[str, object]:
    return {
        "kind": "guarded_push_receipt",
        "schema": GUARDED_PUSH_RECEIPT_SCHEMA,
        "generated_at": _utc_now(),
        "remote_name": remote_name,
        "source_ref": source_ref,
        "target_ref": target_ref,
        "expected_source_sha": expected_source,
        "expected_remote_sha": None if _zero_oid(expected_remote) else expected_remote,
        "dry_run": dry_run,
        "safety_rule": (
            "push audited source identity to target ref only when source and remote still "
            "match the audit identity"
        ),
    }


def guarded_push(
    *,
    remote_name: str,
    source_ref: str,
    target_ref: str,
    expected_source: str,
    expected_remote: str,
    dry_run: bool = False,
) -> dict[str, object]:
    expected_source = _normalize_expected_oid(expected_source)
    expected_remote = _normalize_expected_oid(expected_remote)
    receipt = _guarded_push_base_receipt(
        remote_name=remote_name,
        source_ref=source_ref,
        target_ref=target_ref,
        expected_source=expected_source,
        expected_remote=expected_remote,
        dry_run=dry_run,
    )

    remote_violations = _push_remote_policy_violations(remote_name, resolve_url=False)
    if remote_violations:
        receipt.update(
            {
                "status": "blocked",
                "blocker": "disallowed_push_remote",
                "message": remote_violations[0].detail,
            }
        )
        return receipt

    source_code, current_source, source_err = git("rev-parse", source_ref)
    current_source = current_source.strip()
    receipt["current_source_sha"] = current_source or None
    if source_code != 0 or not current_source:
        receipt.update(
            {
                "status": "blocked",
                "blocker": "source_ref_unresolved",
                "message": source_err or f"could not resolve source ref {source_ref}",
            }
        )
        return receipt
    if current_source != expected_source:
        receipt.update(
            {
                "status": "blocked",
                "blocker": "local_source_changed",
                "message": "source ref no longer matches audited source commit",
                "range_widened": True,
            }
        )
        return receipt

    remote_before, remote_error = _ls_remote_oid(remote_name, target_ref)
    receipt["remote_sha_before_push"] = (
        None if remote_before is None or _zero_oid(remote_before) else remote_before
    )
    if remote_error:
        receipt.update(
            {
                "status": "blocked",
                "blocker": "remote_ref_lookup_failed",
                "message": remote_error,
            }
        )
        return receipt
    normalized_remote_before = _normalize_expected_oid(remote_before)
    if normalized_remote_before != expected_remote:
        if normalized_remote_before == expected_source:
            push_refspec = f"{expected_source}:{target_ref}"
            receipt["push_command"] = ["git", "push", remote_name, push_refspec]
            receipt.update(
                {
                    "status": "pushed",
                    "message": (
                        "remote ref already matches audited source commit; guarded push is "
                        "idempotently complete"
                    ),
                    "remote_already_at_source": True,
                    "push_refspec": push_refspec,
                    "push_returncode": None,
                    "push_stdout": "",
                    "push_stderr": "",
                    "post_push_remote_sha": remote_before,
                }
            )
            return receipt
        receipt.update(
            {
                "status": "blocked",
                "blocker": "remote_ref_changed",
                "message": "remote ref no longer matches audited remote commit",
            }
        )
        return receipt

    policy_updates = [
        PushUpdate(
            local_ref=source_ref,
            local_oid=expected_source,
            remote_ref=target_ref,
            remote_oid=expected_remote,
        )
    ]
    violations = audit_push_updates(remote_name, policy_updates)
    receipt["policy_violation_count"] = len(violations)
    receipt["policy_error_count"] = sum(1 for item in violations if item.severity == "error")
    receipt["policy_warning_count"] = sum(1 for item in violations if item.severity != "error")
    receipt["policy_violations"] = _push_violation_rows(violations)
    if _has_errors(violations):
        receipt.update(
            {
                "status": "blocked",
                "blocker": "push_policy_not_clear",
                "message": "push policy audit blocked the audited commit range",
            }
        )
        return receipt

    push_refspec = f"{expected_source}:{target_ref}"
    receipt["push_refspec"] = push_refspec
    receipt["push_command"] = ["git", "push", remote_name, push_refspec]
    if dry_run:
        receipt.update(
            {
                "status": "planned",
                "message": "guarded push identities verified; push not executed because dry-run is set",
            }
        )
        return receipt

    push_code, push_out, push_err = git("push", remote_name, push_refspec)
    receipt["push_returncode"] = push_code
    receipt["push_stdout"] = push_out
    receipt["push_stderr"] = push_err
    if push_code != 0:
        post_remote, post_error = _ls_remote_oid(remote_name, target_ref)
        receipt["post_push_remote_sha"] = (
            None if post_remote is None or _zero_oid(post_remote) else post_remote
        )
        if post_error:
            receipt["post_push_remote_lookup_error"] = post_error
        if post_remote == expected_source:
            receipt.update(
                {
                    "status": "pushed",
                    "message": (
                        "remote ref reached audited source commit after push attempt; "
                        "guarded push is idempotently complete"
                    ),
                    "remote_already_at_source": True,
                    "push_failed_remote_already_at_source": True,
                    "pushed_commit": expected_source,
                    "remote_verified": True,
                    "range_widened": False,
                }
            )
            return receipt
        receipt.update(
            {
                "status": "blocked",
                "blocker": "git_push_failed",
                "message": push_err or push_out or "git push failed",
            }
        )
        return receipt

    post_remote, post_error = _ls_remote_oid(remote_name, target_ref)
    receipt["post_push_remote_sha"] = (
        None if post_remote is None or _zero_oid(post_remote) else post_remote
    )
    if post_error:
        receipt.update(
            {
                "status": "blocked",
                "blocker": "post_push_remote_lookup_failed",
                "message": post_error,
            }
        )
        return receipt
    if post_remote != expected_source:
        receipt.update(
            {
                "status": "blocked",
                "blocker": "post_push_remote_mismatch",
                "message": "remote ref did not verify to audited source commit after push",
            }
        )
        return receipt

    receipt.update(
        {
            "status": "pushed",
            "message": "pushed audited source commit and verified remote ref",
            "pushed_commit": expected_source,
            "remote_verified": True,
            "range_widened": False,
        }
    )
    return receipt


def _raw_git_commit_guard_message() -> str:
    return (
        "git policy: refusing raw `git commit` against the shared index.\n"
        "  This commit path is the source of the multi-agent commit-boundary\n"
        "  contamination class tracked at\n"
        "  cap_quick_concurrent_broad_sweep_commit_absorbed_i_6cc3039a3fde.\n"
        "  Concrete history: commits b0a857167 (forward-absorption) and\n"
        "  486014a07 (backward-revert) both used raw `git commit` paths.\n"
        "\n"
        "  Use a sanctioned actuator instead:\n"
        "    ./repo-python tools/meta/control/scoped_commit.py full-paths "
        "--path <p1> [--path <p2> ...] --message \"...\"\n"
        "    ./repo-python tools/meta/control/scoped_commit.py patch "
        "--patch-file <hunk.patch> --path <p> --message \"...\"\n"
        "    ./checkpoint \"<message>\"   # bankruptcy lane only "
        "(private-index since 094efe3b4)\n"
        "\n"
        "  Genuine manual override (e.g. interactive solo-dev commit):\n"
        "    AIW_ALLOW_RAW_GIT_COMMIT=1 git commit ...\n"
    )


def run_hook_prepare_commit_msg() -> int:
    """`prepare-commit-msg` backstop for the raw shared-index commit guard.

    Git's `--no-verify` suppresses `pre-commit` and `commit-msg` hooks but
    NOT `prepare-commit-msg`. So a `git commit --no-verify -m "..."` from
    an agent session would skip Layer 2's pre-commit refusal — this hook
    is the second backstop. Same env-var override (AIW_ALLOW_RAW_GIT_COMMIT)
    so the operator's explicit manual flow still works. The PreToolUse
    Bash guard in `.claude/hooks/runtime_hook.py` remains the primary stop
    (refuses BEFORE staging happens); these hooks are defense in depth.

    Note: scoped_commit.py and ./checkpoint commit via `git commit-tree` /
    `git update-ref`, which do NOT trigger any commit hook. So this hook
    only ever fires for raw `git commit` paths.
    """
    if not os.environ.get("AIW_ALLOW_RAW_GIT_COMMIT"):
        sys.stderr.write(_raw_git_commit_guard_message())
        return 1
    return 0


def run_hook_pre_commit() -> int:
    # Raw shared-index commit guard. tools/meta/control/scoped_commit.py and
    # ./checkpoint commit via `git commit-tree` + `git update-ref` (CAS),
    # which DO NOT trigger pre-commit hooks. Therefore: if pre-commit fires,
    # this is necessarily a raw `git commit` path against the shared
    # `.git/index`. Refuse unless the operator has explicitly opted in via
    # `AIW_ALLOW_RAW_GIT_COMMIT=1`. The Claude PreToolUse hook in
    # `.claude/hooks/runtime_hook.py` is the primary stop (it blocks
    # `git add -A` / `git commit -a` shapes BEFORE staging mutates the
    # shared index); this hook is the backstop for non-Claude sessions and
    # bypass attempts. `prepare-commit-msg` is the second backstop for
    # `git commit --no-verify` paths that suppress pre-commit.
    if not os.environ.get("AIW_ALLOW_RAW_GIT_COMMIT"):
        sys.stderr.write(_raw_git_commit_guard_message())
        return 1

    violations = audit_staged_paths()
    if violations:
        _print_violations(
            violations,
            stream=sys.stderr,
            heading="Git policy blocked the commit.",
        )
        return 1 if _has_errors(violations) else 0
    return 0


LOCAL_ONLY_REF_PUSH_OVERRIDE_ENV = "AIW_ALLOW_RESCUE_PUSH"


def _ref_is_local_only(ref: str) -> bool:
    """rescue/* and refs/aiw/* are local-only recovery namespaces.

    `checkpoint --rescue-ref` writes `refs/aiw/rescue/*`, and a clean-slate flush
    leaves `rescue/*` tags pinning the pre-flush history. Pushing either re-uploads
    the exact object graph a clean-slate publish removed, so they must never leave
    the machine without an explicit override.
    """
    token = (ref or "").strip()
    if not token:
        return False
    if "rescue/" in token:
        return True
    if token.startswith("refs/aiw/"):
        return True
    return False


def _local_only_ref_push_violations(updates: list[PushUpdate]) -> list[GitPolicyViolation]:
    violations: list[GitPolicyViolation] = []
    for update in updates:
        # A deletion (zero local oid) sends no objects; allow rescue-ref cleanup.
        if _zero_oid(update.local_oid):
            continue
        matched_ref = next(
            (ref for ref in (update.remote_ref, update.local_ref) if _ref_is_local_only(ref)),
            None,
        )
        if matched_ref is None:
            continue
        violations.append(
            GitPolicyViolation(
                category="local_only_ref_push",
                path=matched_ref,
                detail=(
                    f"Refusing to push local-only ref '{matched_ref}'. rescue/* and "
                    "refs/aiw/* refs preserve pre-flush and dirty-tree-bankruptcy history "
                    "locally; pushing them re-contaminates the remote with the history a "
                    "clean-slate publish removed."
                ),
                remediation=(
                    "Keep rescue/aiw refs local for recovery, or back them up off-repo with "
                    "`git bundle create <file> <ref>`. To override for one intentional push, "
                    f"set {LOCAL_ONLY_REF_PUSH_OVERRIDE_ENV}=1."
                ),
                source="push",
            )
        )
    return violations


def run_hook_pre_push(
    remote_name: str, stdin_text: str | None = None, remote_url: str | None = None
) -> int:
    remote_violations = _push_remote_policy_violations(remote_name, remote_url)
    if remote_violations:
        _print_violations(
            remote_violations,
            stream=sys.stderr,
            heading="Git policy blocked the push.",
        )
        return 1
    if not os.environ.get(LOCAL_ONLY_REF_PUSH_OVERRIDE_ENV):
        local_only_violations = _local_only_ref_push_violations(
            _parse_push_stdin(stdin_text or "")
        )
        if local_only_violations:
            _print_violations(
                local_only_violations,
                stream=sys.stderr,
                heading="Git policy blocked the push.",
            )
            return 1
    violations = audit_push(remote_name=remote_name, stdin_text=stdin_text)
    if violations:
        _print_violations(
            violations,
            stream=sys.stderr,
            heading="Git policy blocked the push.",
        )
        return 1 if _has_errors(violations) else 0
    return 0


def branch() -> str:
    _, out, _ = git("branch", "--show-current")
    return out or "HEAD (detached)"


def tracking_status() -> str:
    _, out, _ = git("status", "-sb")
    first = out.splitlines()[0] if out else ""
    ahead = behind = 0
    if "ahead" in first:
        try:
            ahead = int(first.split("ahead ")[1].split(",")[0].split("]")[0].strip())
        except (IndexError, ValueError):
            pass
    if "behind" in first:
        try:
            behind = int(first.split("behind ")[1].split("]")[0].strip())
        except (IndexError, ValueError):
            pass
    if ahead and behind:
        return f"[yellow]↕ diverged  {ahead}↑  {behind}↓[/]"
    if ahead:
        return f"[green]↑ {ahead} unpushed[/]"
    if behind:
        return f"[red]↓ {behind} to pull[/]"
    return "[dim]synced[/]"


def status_lines() -> list[tuple[str, str]]:
    _, out, _ = git("status", "--short")
    if not out:
        return []
    result = []
    for line in out.splitlines():
        if len(line) >= 4:
            xy = line[:2]
            path = line[3:]
            result.append((xy, path))
    return result


def recent_log(n: int = 20) -> list[tuple[str, str, str]]:
    _, out, _ = git("log", f"-{n}", "--format=%h|%s|%cr")
    entries = []
    for line in out.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            entries.append((parts[0], parts[1], parts[2]))
    return entries


def last_commit_info() -> str:
    _, out, _ = git("log", "-1", "--format=%h %s (%cr)")
    return out or "—"


def remote_url() -> str:
    _, out, _ = git("remote", "get-url", "origin")
    return out or "no remote"


def stash_list() -> list[str]:
    _, out, _ = git("stash", "list")
    return out.splitlines() if out else []


def categorize(lines: list[tuple[str, str]]) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
    staged, unstaged, untracked = [], [], []
    for xy, path in lines:
        if xy == "??":
            untracked.append((xy, path))
        else:
            x, y = xy[0], xy[1]
            if x != " ":
                staged.append((xy, path))
            if y != " ":
                unstaged.append((xy, path))
    return staged, unstaged, untracked


INDEX_COLOR = {"M": "green", "A": "green", "D": "red", "R": "cyan", "C": "cyan", "U": "red"}
TREE_COLOR = {"M": "yellow", "D": "red", "U": "red"}


def xy_display(xy: str) -> str:
    if xy == "??":
        return "[dim]?[/]"
    x, y = xy[0], xy[1]
    xs = f"[{INDEX_COLOR.get(x, 'dim')}]{x}[/]" if x != " " else " "
    ys = f"[{TREE_COLOR.get(y, 'dim')}]{y}[/]" if y != " " else " "
    return xs + ys


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'s' if n != 1 else ''}"


def render_status_table(lines: list[tuple[str, str]]) -> Table:
    t = Table(box=box.SIMPLE, show_header=False, show_edge=False, padding=(0, 1))
    t.add_column("St", width=4)
    t.add_column("File")

    staged, unstaged, untracked = categorize(lines)

    def section(items: list[tuple[str, str]], label: str, color: str) -> None:
        if not items:
            return
        t.add_row(f"[{color} dim]{label}[/]", "")
        for xy, path in items:
            t.add_row(f"  {xy_display(xy)}", path)

    section(staged, f"staged  ·  {_plural(len(staged), 'file')}", "green")
    section(unstaged, f"modified  ·  {_plural(len(unstaged), 'file')}", "yellow")
    section(untracked, f"untracked  ·  {_plural(len(untracked), 'file')}", "white")
    return t


def render_log_table(entries: list[tuple[str, str, str]]) -> Table:
    t = Table(box=box.SIMPLE, show_header=False, show_edge=False, padding=(0, 1))
    t.add_column("Hash", style="dim cyan", width=8)
    t.add_column("Message", ratio=3)
    t.add_column("When", style="dim", no_wrap=True)
    for h, msg, when in entries:
        t.add_row(h, msg, when)
    return t


def header_panel() -> Panel:
    info = Text()
    info.append("  branch  ", style="bold dim")
    info.append(f"{branch()}  ", style="bold white")
    info.append(tracking_status())
    info.append("\n  remote  ", style="bold dim")
    info.append(remote_url(), style="dim")
    info.append("\n  last    ", style="bold dim")
    info.append(last_commit_info(), style="dim")
    info.append("\n  hooks   ", style="bold dim")
    hook_label = _hook_status_label()
    hook_style = "green" if hook_label == "installed" else "yellow"
    info.append(hook_label, style=hook_style)
    info.append("\n  tidy    ", style="bold dim")
    tidy_style = "yellow" if LAST_TIDY_STATUS.startswith("error") else "dim"
    info.append(LAST_TIDY_STATUS, style=tidy_style)

    stashes = stash_list()
    if stashes:
        info.append("\n  stash   ", style="bold dim")
        info.append(f"{_plural(len(stashes), 'entry')} saved  (press 8 to manage)", style="yellow")

    return Panel(info, title="[bold]zenith git[/]", border_style="blue", padding=(0, 2))


def menu_panel() -> Panel:
    items = [
        ("1", "Stage & commit"),
        ("2", "Push"),
        ("3", "Pull"),
        ("4", "Log"),
        ("5", "Diff"),
        ("6", "Undo last commit"),
        ("7", "Amend last message"),
        ("8", "Stash"),
        ("r", "Refresh"),
        ("q", "Quit"),
    ]
    t = Table(box=None, show_header=False, show_edge=False, padding=(0, 2))
    t.add_column("key", style="bold cyan", width=4)
    t.add_column("action")
    for k, v in items:
        t.add_row(k, v)
    return Panel(t, title="[bold]actions[/]", border_style="dim blue", padding=(0, 1))


def pick_files_to_stage(lines: list[tuple[str, str]]) -> list[str] | None:
    _, unstaged, untracked = categorize(lines)
    candidates = unstaged + untracked
    if not candidates:
        console.print("  [dim]Nothing unstaged to pick from.[/]")
        return []

    t = Table(box=box.SIMPLE, show_header=False, show_edge=False, padding=(0, 1))
    t.add_column("#", style="bold cyan", width=4)
    t.add_column("St", width=4)
    t.add_column("File")
    for i, (xy, path) in enumerate(candidates, 1):
        t.add_row(str(i), f"  {xy_display(xy)}", path)
    console.print(Panel(t, title="unstaged files", border_style="dim"))
    console.print()

    raw = Prompt.ask("  File numbers to stage  (e.g. 1,3  or 'a' for all  or Enter to cancel)").strip()
    if not raw:
        return None
    if raw.lower() == "a":
        return [path for _, path in candidates]

    picked = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(candidates):
                picked.append(candidates[idx][1])
    return picked if picked else None


def _render_policy_panel(violations: list[GitPolicyViolation], *, title: str) -> Panel:
    table = Table(box=box.SIMPLE, show_header=False, show_edge=False, padding=(0, 1))
    table.add_column("Level", width=6)
    table.add_column("Path", ratio=2)
    table.add_column("Detail", ratio=4)
    for item in violations:
        level = "[red]error[/]" if item.severity == "error" else "[yellow]warn[/]"
        size_note = f" ({_format_bytes(item.size_bytes)})" if item.size_bytes is not None else ""
        table.add_row(level, item.path, f"{item.detail}{size_note}\nFix: {item.remediation}")
    return Panel(table, title=title, border_style="red")


def action_commit() -> None:
    console.print()
    lines = status_lines()
    if not lines:
        console.print("  [green]Nothing to commit.[/]")
        console.input("\n  [dim]Press Enter...[/]")
        return

    staged, unstaged, untracked = categorize(lines)
    console.print(Panel(render_status_table(lines), title="current changes", border_style="dim"))
    console.print()

    if staged and not unstaged and not untracked:
        console.print(f"  [green]{_plural(len(staged), 'file')} staged[/] — ready to commit.\n")
    elif not staged:
        console.print("  [dim]a[/] stage all    [dim]p[/] pick files    [dim]c[/] cancel\n")
        choice = Prompt.ask("  Stage", choices=["a", "p", "c"], default="a")
        if choice == "c":
            return
        if choice == "a":
            code, _, err = git("add", "-A")
            if code != 0:
                console.print(f"  [red]git add failed:[/] {err}")
                console.input("  [dim]Press Enter...[/]")
                return
            console.print("  [green]✓ All staged.[/]\n")
        else:
            paths = pick_files_to_stage(lines)
            if not paths:
                return
            for p in paths:
                git("add", "--", p)
            console.print(f"  [green]✓ {_plural(len(paths), 'file')} staged.[/]\n")
    else:
        console.print(
            f"  [green]{_plural(len(staged), 'file')} staged[/]  +  "
            f"[yellow]{_plural(len(unstaged) + len(untracked), 'file')} not staged[/]\n"
        )
        console.print(
            "  [dim]a[/] stage rest too    "
            "[dim]p[/] pick more files    "
            "[dim]s[/] commit staged only    "
            "[dim]c[/] cancel\n"
        )
        choice = Prompt.ask("  →", choices=["a", "p", "s", "c"], default="a")
        if choice == "c":
            return
        if choice == "a":
            git("add", "-A")
            console.print("  [green]✓ All staged.[/]\n")
        elif choice == "p":
            paths = pick_files_to_stage(lines)
            if not paths:
                return
            for p in paths:
                git("add", "--", p)
            console.print(f"  [green]✓ {_plural(len(paths), 'file')} added to stage.[/]\n")

    tidy_result = tidy_workspace()
    if tidy_result.errors:
        console.print(
            f"  [yellow]workspace tidy had errors:[/] {'; '.join(tidy_result.errors)}"
        )
    elif tidy_result.unstaged_paths or tidy_result.hidden_paths:
        console.print(
            "  [dim]tidy:[/] "
            f"unstaged {_plural(tidy_result.unstaged_paths, 'runtime path')}, "
            f"hid {_plural(tidy_result.hidden_paths, 'tracked runtime path')}."
        )

    violations = audit_staged_paths()
    if violations:
        console.print(_render_policy_panel(violations, title="git policy"))
        console.input("\n  [dim]Press Enter...[/]")
        return

    msg = Prompt.ask("  Message").strip()
    if not msg:
        console.print("  [yellow]Aborted — empty message.[/]")
        console.input("\n  [dim]Press Enter...[/]")
        return

    code, out, err = git("commit", "-m", msg)
    console.print()
    if code == 0:
        console.print("  [green]✓ Committed.[/]")
        for line in out.splitlines()[:5]:
            console.print(f"    [dim]{line}[/]")
    else:
        console.print(f"  [red]Commit failed:[/] {err or out}")
    console.input("\n  [dim]Press Enter...[/]")


def action_push() -> None:
    console.print()
    ok, message = install_hooks()
    if ok:
        console.print(f"  [dim]{message}[/]")
    else:
        console.print(f"  [yellow]{message}[/]")

    audit_status = build_push_audit_status(remote_name="origin")
    violations = [
        GitPolicyViolation(
            category=str(row.get("category") or "unknown"),
            path=str(row.get("path") or ""),
            detail=str(row.get("detail") or ""),
            remediation=str(row.get("remediation") or ""),
            source=str(row.get("source") or "push"),
            size_bytes=row.get("size_bytes") if isinstance(row.get("size_bytes"), int) else None,
            severity=str(row.get("severity") or "error"),
        )
        for row in audit_status.get("violations") or []
        if isinstance(row, dict)
    ]
    if violations and _has_errors(violations):
        console.print()
        console.print(_render_policy_panel(violations, title="push policy"))
        console.input("\n  [dim]Press Enter...[/]")
        return
    if not audit_status.get("direct_push_allowed") or not audit_status.get("head") or not audit_status.get("remote_oid"):
        console.print("  [yellow]Push audit did not produce a guarded publication identity.[/]")
        console.input("\n  [dim]Press Enter...[/]")
        return

    console.print("  [dim]Pushing...[/]")
    receipt = guarded_push(
        remote_name="origin",
        source_ref="HEAD",
        target_ref=str(audit_status.get("target_ref") or _remote_ref_for_branch("origin", branch())),
        expected_source=str(audit_status.get("head") or ""),
        expected_remote=str(audit_status.get("remote_oid") or ""),
    )
    combined = "\n".join(
        filter(
            None,
            [
                str(receipt.get("message") or ""),
                str(receipt.get("push_stdout") or ""),
                str(receipt.get("push_stderr") or ""),
            ],
        )
    )
    console.print()
    if receipt.get("status") == "pushed":
        for line in combined.splitlines():
            console.print(f"  [dim]{line}[/]")
        console.print("  [green]✓ Pushed.[/]")
    else:
        console.print("  [red]Push failed:[/]")
        console.print(f"  [red]{receipt.get('blocker') or receipt.get('status')}[/]")
        for line in combined.splitlines():
            console.print(f"  [red]{line}[/]")
    console.input("\n  [dim]Press Enter...[/]")


def action_pull() -> None:
    console.print()
    console.print("  [dim]Pulling (rebase)...[/]")
    code, out, err = git("pull", "--rebase")
    console.print()
    if code == 0:
        for line in out.splitlines():
            console.print(f"  [dim]{line}[/]")
        console.print("  [green]✓ Up to date.[/]")
    else:
        console.print("  [red]Pull failed:[/]")
        for line in err.splitlines():
            console.print(f"  [red]{line}[/]")
    console.input("\n  [dim]Press Enter...[/]")


def action_log() -> None:
    console.print()
    entries = recent_log(20)
    if not entries:
        console.print("  [dim]No commits yet.[/]")
    else:
        console.print(Panel(render_log_table(entries), title="recent commits", border_style="dim"))
    console.input("\n  [dim]Press Enter...[/]")


def action_diff() -> None:
    console.print()
    _, out, _ = git("diff", "HEAD")
    if not out:
        _, out, _ = git("diff", "--cached")
    if not out:
        console.print("  [dim]No changes to diff.[/]")
        console.input("\n  [dim]Press Enter...[/]")
        return

    all_lines = out.splitlines()
    truncated = len(all_lines) > DIFF_LINE_LIMIT
    shown = all_lines[:DIFF_LINE_LIMIT]
    for line in shown:
        if line.startswith("+") and not line.startswith("+++"):
            console.print(f"[green]{line}[/]")
        elif line.startswith("-") and not line.startswith("---"):
            console.print(f"[red]{line}[/]")
        elif line.startswith("@@"):
            console.print(f"[cyan]{line}[/]")
        elif line.startswith("diff ") or line.startswith("index "):
            console.print(f"[bold dim]{line}[/]")
        else:
            console.print(f"[dim]{line}[/]")

    if truncated:
        console.print(
            f"\n  [yellow]… {len(all_lines) - DIFF_LINE_LIMIT} more lines — "
            "run 'git diff HEAD' in terminal for full output.[/]"
        )
    console.input("\n  [dim]Press Enter...[/]")


def action_undo() -> None:
    console.print()
    _, last, _ = git("log", "-1", "--format=%h %s (%cr)")
    console.print(f"  Last commit: [dim]{last}[/]\n")
    confirmed = Confirm.ask("  Undo? (files kept, commit removed)", default=False)
    if confirmed:
        code, _, err = git("reset", "--soft", "HEAD~1")
        if code == 0:
            console.print("  [green]✓ Commit undone. Changes are now staged.[/]")
        else:
            console.print(f"  [red]Failed:[/] {err}")
    else:
        console.print("  [dim]Cancelled.[/]")
    console.input("\n  [dim]Press Enter...[/]")


def action_amend() -> None:
    console.print()
    _, last, _ = git("log", "-1", "--format=%s")
    console.print(f"  Current message: [dim]{last}[/]\n")
    new_msg = Prompt.ask("  New message  (Enter to cancel)").strip()
    if not new_msg:
        console.print("  [dim]Unchanged.[/]")
    else:
        violations = audit_staged_paths()
        if violations:
            console.print(_render_policy_panel(violations, title="git policy"))
        else:
            code, _, err = git("commit", "--amend", "-m", new_msg)
            if code == 0:
                console.print("  [green]✓ Message updated.[/]")
            else:
                console.print(f"  [red]Failed:[/] {err}")
    console.input("\n  [dim]Press Enter...[/]")


def action_stash() -> None:
    console.print()
    stashes = stash_list()
    if stashes:
        console.print(f"  [yellow]{_plural(len(stashes), 'stash')} saved:[/]")
        for s in stashes[:5]:
            console.print(f"    [dim]{s}[/]")
        console.print()

    console.print("  [dim]p[/] push (save changes)    [dim]o[/] pop (restore latest)    [dim]c[/] cancel\n")
    choice = Prompt.ask("  →", choices=["p", "o", "c"], default="c").lower()
    if choice == "p":
        msg = Prompt.ask("  Stash label  (optional)").strip()
        args = ["stash", "push"]
        if msg:
            args += ["-m", msg]
        code, out, err = git(*args)
        if code == 0:
            console.print("  [green]✓ Stashed.[/]")
        else:
            console.print(f"  [red]Failed:[/] {err or out}")
    elif choice == "o":
        if not stashes:
            console.print("  [dim]No stashes to pop.[/]")
        else:
            console.print(f"  Will apply: [dim]{stashes[0]}[/]")
            if Confirm.ask("  Pop?", default=True):
                code, _, err = git("stash", "pop")
                if code == 0:
                    console.print("  [green]✓ Applied and removed from stash.[/]")
                else:
                    console.print(f"  [red]Failed:[/] {err}")
    console.input("\n  [dim]Press Enter...[/]")


def draw() -> None:
    console.clear()
    console.print(header_panel())
    console.print()

    lines = status_lines()
    if lines:
        console.print(
            Panel(
                render_status_table(lines),
                title=f"[bold]status[/]  [dim]{_plural(len(lines), 'file')}[/]",
                border_style="dim",
            )
        )
    else:
        console.print(
            Panel(
                "  [green]Working tree clean.[/]",
                title="status",
                border_style="dim green",
            )
        )

    console.print()
    console.print(menu_panel())
    console.print()


def run_ui() -> int:
    global LAST_TIDY_STATUS

    if not RICH_AVAILABLE:
        print("Missing dependency for TUI mode: pip install rich", file=sys.stderr)
        return 1

    ok, message = install_hooks()
    hook_message = message
    tidy_result = tidy_workspace()
    if tidy_result.errors:
        LAST_TIDY_STATUS = "error"
    elif tidy_result.unstaged_paths or tidy_result.hidden_paths:
        LAST_TIDY_STATUS = (
            f"unstaged {tidy_result.unstaged_paths}, hid {tidy_result.hidden_paths}"
        )
    else:
        LAST_TIDY_STATUS = "already tidy"

    os.chdir(ROOT)
    while True:
        draw()
        if hook_message:
            style = "dim" if ok else "yellow"
            console.print(f"[{style}]{hook_message}[/]")
            hook_message = ""
        if tidy_result.errors:
            console.print(f"[yellow]workspace tidy errors:[/] {'; '.join(tidy_result.errors)}")
            tidy_result = WorkspaceTidyResult(0, 0, ())
        choice = Prompt.ask("  choice", default="r").strip().lower()
        console.print()
        match choice:
            case "q":
                console.print("  [dim]bye.[/]\n")
                return 0
            case "1":
                action_commit()
            case "2":
                action_push()
            case "3":
                action_pull()
            case "4":
                action_log()
            case "5":
                action_diff()
            case "6":
                action_undo()
            case "7":
                action_amend()
            case "8":
                action_stash()
            case "r":
                continue
            case _:
                console.print(f"  [dim]Unknown: {choice}[/]")
                console.input("  [dim]Press Enter...[/]")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repo-aware git UI and policy gates.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("ui", help="Launch the interactive git TUI.")
    subparsers.add_parser("install-hooks", help="Install committed git hooks via core.hooksPath.")
    subparsers.add_parser("tidy", help="Auto-hide known runtime churn and unstage runtime junk.")

    audit_parser = subparsers.add_parser("audit", help="Run repo git-policy audits without mutating git state.")
    audit_subparsers = audit_parser.add_subparsers(dest="audit_mode", required=True)
    audit_subparsers.add_parser("staged", help="Audit currently staged paths.")
    push_parser = audit_subparsers.add_parser("push", help="Audit the outgoing push range.")
    push_parser.add_argument("--remote-name", default="origin")
    push_parser.add_argument("--remote-url", default="")
    push_parser.add_argument("--stdin-file", default="")
    push_parser.add_argument("--json", action="store_true")

    push_command_parser = subparsers.add_parser("push", help="Run guarded repo publication actions.")
    push_subparsers = push_command_parser.add_subparsers(dest="push_mode", required=True)
    guarded_parser = push_subparsers.add_parser(
        "guarded",
        help="Push an audited source commit only if local and remote identities still match.",
    )
    guarded_parser.add_argument("--remote-name", default="origin")
    guarded_parser.add_argument("--source-ref", default="HEAD")
    guarded_parser.add_argument("--target-ref", default="")
    guarded_parser.add_argument("--expected-source", required=True)
    guarded_parser.add_argument("--expected-remote", required=True)
    guarded_parser.add_argument("--dry-run", action="store_true")
    guarded_parser.add_argument("--json", action="store_true")

    hook_parser = subparsers.add_parser("hook", help="Entry point used by committed git hooks.")
    hook_parser.add_argument(
        "hook_name", choices=("pre-commit", "pre-push", "prepare-commit-msg")
    )
    hook_parser.add_argument("--remote-name", default="origin")
    hook_parser.add_argument("--remote-url", default="")
    # prepare-commit-msg receives positional args from git: commit-msg path,
    # commit source, and SHA-1. We accept and ignore them here — the hook
    # only inspects the AIW_ALLOW_RAW_GIT_COMMIT env var.
    hook_parser.add_argument("hook_args", nargs="*")

    return parser


def _emit_json_push_audit_status(status: dict[str, object]) -> None:
    print(json.dumps(status, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    os.chdir(ROOT)

    if args.command in (None, "ui"):
        return run_ui()

    if args.command == "install-hooks":
        ok, message = install_hooks()
        stream = sys.stdout if ok else sys.stderr
        print(message, file=stream)
        return 0 if ok else 1

    if args.command == "tidy":
        result = tidy_workspace()
        if result.errors:
            print("; ".join(result.errors), file=sys.stderr)
            return 1
        print(
            f"workspace tidy: unstaged {result.unstaged_paths} path(s), "
            f"hid {result.hidden_paths} tracked runtime path(s)"
        )
        return 0

    if args.command == "audit":
        if args.audit_mode == "staged":
            violations = audit_staged_paths()
            _print_violations(violations, stream=sys.stderr, heading="Staged-path git policy audit:")
            return 1 if _has_errors(violations) else 0
        stdin_text = ""
        if args.stdin_file:
            stdin_text = Path(args.stdin_file).read_text(encoding="utf-8")
        else:
            stdin_text = sys.stdin.read()
        if args.json:
            status = build_push_audit_status(
                remote_name=args.remote_name,
                stdin_text=stdin_text,
            )
            _emit_json_push_audit_status(status)
            return 1 if int(status.get("error_count") or 0) else 0
        violations = audit_push(remote_name=args.remote_name, stdin_text=stdin_text)
        _print_violations(violations, stream=sys.stderr, heading="Push-range git policy audit:")
        return 1 if _has_errors(violations) else 0

    if args.command == "push":
        if args.push_mode == "guarded":
            target_ref = args.target_ref or _remote_ref_for_branch(args.remote_name, branch())
            receipt = guarded_push(
                remote_name=args.remote_name,
                source_ref=args.source_ref,
                target_ref=target_ref,
                expected_source=args.expected_source,
                expected_remote=args.expected_remote,
                dry_run=bool(args.dry_run),
            )
            if args.json:
                print(json.dumps(receipt, indent=2, sort_keys=True))
            else:
                print(f"{receipt.get('status')}: {receipt.get('message') or receipt.get('blocker')}")
            return 0 if receipt.get("status") in {"planned", "pushed"} else 1

    if args.command == "hook":
        if args.hook_name == "pre-commit":
            return run_hook_pre_commit()
        if args.hook_name == "prepare-commit-msg":
            return run_hook_prepare_commit_msg()
        stdin_text = sys.stdin.read()
        return run_hook_pre_push(
            remote_name=args.remote_name,
            stdin_text=stdin_text,
            remote_url=args.remote_url,
        )

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
