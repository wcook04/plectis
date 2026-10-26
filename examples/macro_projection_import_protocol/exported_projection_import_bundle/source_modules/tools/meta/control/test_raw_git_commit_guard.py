"""
[PURPOSE]
- Teleology: Pin the two-layer raw-shared-index commit guard. Layer 1 is the
  Claude PreToolUse hook in `.claude/hooks/runtime_hook.py`, which hard-blocks
  dangerous Bash invocations (`git add -A`, `git commit -a`, etc.) before
  staging mutates the shared `.git/index`. Layer 2 is the repo's pre-commit
  hook in `run_git.py`, which refuses any commit reaching it (tools/meta/
  control/scoped_commit.py uses `git commit-tree` and never trips this
  hook) unless `AIW_ALLOW_RAW_GIT_COMMIT=1` is explicitly set.
- Mechanism: For Layer 1, invoke runtime_hook.py with synthetic Bash
  payloads matching each guarded shape and assert the hook output is
  `permissionDecision: deny`. For Layer 2, build a throwaway git repo with
  `.githooks/pre-commit` wired to run_git.py and assert raw `git commit -m`
  is refused, while `AIW_ALLOW_RAW_GIT_COMMIT=1 git commit -m` succeeds.
- Non-goal: Does not exercise concurrent two-agent races. Pins the
  necessary precondition: dangerous shapes are refused in isolation, so
  the multi-agent failure class loses its primary triggers.

[INTERFACE]
- Tests: bypass-token allowlist, each blocked pattern, override env var,
  sanctioned scoped_commit.py invocation passthrough, and the live Layer 2
  pre-commit guard against a temp repo.

[CONSTRAINTS]
- stdlib only.
- Tests stay filesystem-local (tmp_path) and never touch the live repo's
  index, hooks, or push capability.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REAL_ROOT = Path(__file__).resolve().parents[3]
HOOK_PATH = REAL_ROOT / ".claude" / "hooks" / "runtime_hook.py"
RUN_GIT_PATH = REAL_ROOT / "run_git.py"
GITHOOKS_DIR = REAL_ROOT / ".githooks"

sys.path.insert(0, str(REAL_ROOT))

_spec = importlib.util.spec_from_file_location("runtime_hook", HOOK_PATH)
assert _spec and _spec.loader
runtime_hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runtime_hook)


def _invoke_pretool(command: str) -> dict | None:
    """Call the parser-based guard directly and synthesise the JSON shape
    main() would emit.

    Earlier versions subprocessed the full hook script for every test, which
    triggered the runtime hook's identity-capture observability path
    (network probe + fallback file ingest) per invocation. With ~30 tests
    that path-multiplied to multi-minute runs and intermittent timeouts
    that masked guard correctness. The guard logic itself (`_raw_shared_index_git_guard`)
    is pure: it inspects the payload, parses the command, and returns a
    block reason or empty string. Calling it directly gives deterministic,
    fast tests that exercise exactly the parser logic without spawning
    subprocesses or touching the heartbeat path.

    A separate end-to-end integration test (`test_pretool_subprocess_blocks_git_add_dash_A`)
    still subprocess-invokes the hook script once to pin the JSON wire
    shape `main()` produces.
    """
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "test-session",
        "cwd": str(REAL_ROOT),
    }
    block_reason = runtime_hook._raw_shared_index_git_guard(payload)
    if not block_reason:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": block_reason,
        }
    }


def _invoke_pretool_subprocess(command: str) -> dict | None:
    """End-to-end variant that subprocess-spawns the live hook script.

    Used by a single integration test to pin the JSON wire shape main()
    produces. Slower (loads runtime_hook + runs heartbeat path); reserve
    for a single smoke check, not per-test.
    """
    payload_text = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": "test-session",
        "cwd": str(REAL_ROOT),
    })
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH), "pre-tool"],
        input=payload_text,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Layer 1: Claude PreToolUse Bash guard
# ---------------------------------------------------------------------------


def test_pretool_blocks_git_add_dash_A() -> None:
    out = _invoke_pretool("git add -A")
    assert out is not None, "expected hook output for `git add -A`"
    hook_out = out.get("hookSpecificOutput", {})
    assert hook_out.get("permissionDecision") == "deny", out
    reason = hook_out.get("permissionDecisionReason", "")
    # The parser-based guard reports the subcommand, not the specific flag.
    assert "git add" in reason
    assert "scoped_commit.py" in reason
    assert "AIW_ALLOW_RAW_GIT_COMMIT" in reason


def test_pretool_subprocess_blocks_git_add_dash_A() -> None:
    """End-to-end integration: pin the JSON wire shape that main() emits.

    All other tests call the guard function directly for speed; this one
    subprocess-spawns the live hook script to verify the deny shape is
    actually wired into stdout output."""
    out = _invoke_pretool_subprocess("git add -A")
    assert out is not None
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "scoped_commit.py" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_pretool_blocks_git_add_dot() -> None:
    out = _invoke_pretool("git add .")
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "git add" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_pretool_blocks_git_add_dash_dash_all() -> None:
    out = _invoke_pretool("git add --all")
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_pretool_blocks_git_commit_dash_a() -> None:
    out = _invoke_pretool('git commit -a -m "x"')
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "git commit" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_pretool_blocks_git_commit_dash_am() -> None:
    out = _invoke_pretool('git commit -am "x"')
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_pretool_blocks_git_commit_dash_dash_all() -> None:
    out = _invoke_pretool('git commit --all -m "x"')
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_pretool_allows_explicit_override_env_var() -> None:
    out = _invoke_pretool('AIW_ALLOW_RAW_GIT_COMMIT=1 git commit -am "manual"')
    # Either no output at all, or output that is NOT a deny decision.
    if out is None:
        return
    assert out.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"


def test_pretool_allows_scoped_commit_invocation() -> None:
    cmd = (
        './repo-python tools/meta/control/scoped_commit.py full-paths '
        '--path foo.py --message "x"'
    )
    out = _invoke_pretool(cmd)
    if out is None:
        return
    assert out.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"


def test_pretool_allows_checkpoint_invocation() -> None:
    """./checkpoint never uses dangerous patterns in user-visible form."""
    out = _invoke_pretool('./checkpoint "save"')
    if out is None:
        return
    assert out.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"


# Note: an earlier test asserted plain `git commit -m "x"` was allowed at
# PreToolUse and that Layer 2 caught it via the pre-commit hook. The
# parser-hardening wave promotes plain `git commit` to a PreToolUse-blocked
# shape because `--no-verify` skips the pre-commit hook, leaving Layer 2
# gapped — so PreToolUse must block raw `git commit` regardless of flags.
# The replacement test is `test_pretool_blocks_plain_git_commit_dash_m`
# above; the env-override path is `test_pretool_allows_real_env_override`.


# ---------------------------------------------------------------------------
# Parser-based guard: false-positive avoidance + bypass-injection blocking
# ---------------------------------------------------------------------------


def test_pretool_does_not_block_quoted_pattern_in_echo() -> None:
    """A quoted/echoed string containing a banned phrase must NOT trigger the
    guard. The earlier lexical regex fired on documentary text; the parser-
    based replacement only inspects actual command invocations."""
    out = _invoke_pretool('echo "git commit -am test"')
    if out is None:
        return
    assert out.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"


def test_pretool_does_not_block_printf_quoted_pattern() -> None:
    out = _invoke_pretool("printf '%s\\n' 'git add -A'")
    if out is None:
        return
    assert out.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"


def test_pretool_blocks_actual_invocation_after_cosmetic_test_path_mention() -> None:
    """Substring bypass via cosmetic test-path mention must NOT defeat the
    guard. Earlier substring-token bypass let `echo tools/meta/control/test_*
    && git add -A` through; the parser-based guard treats the post-`&&`
    segment independently and refuses the actual `git add -A` invocation."""
    out = _invoke_pretool(
        "echo tools/meta/control/test_throwaway && git add -A"
    )
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_pretool_blocks_echoed_override_token_followed_by_real_invocation() -> None:
    """`echo AIW_ALLOW_RAW_GIT_COMMIT=1 && git commit -m "x"` must deny.
    The override only counts when it is an actual env assignment for the
    same command segment, not a string echoed in a previous segment."""
    out = _invoke_pretool('echo AIW_ALLOW_RAW_GIT_COMMIT=1 && git commit -m "x"')
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_pretool_blocks_plain_git_add_filename() -> None:
    """All raw `git add` is now blocked (not only -A/--all/.). Selective
    `git add` writes through the shared index and is racy under concurrent
    agents."""
    out = _invoke_pretool("git add foo.txt")
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "git add" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_pretool_blocks_plain_git_commit_dash_m() -> None:
    """All raw `git commit` is now blocked at PreToolUse. Plain
    `git commit -m` was previously allowed at this layer; now blocked
    because it can commit a contaminated staged set, and Layer 2's
    `--no-verify` gap means PreToolUse is the only sure stop."""
    out = _invoke_pretool('git commit -m "x"')
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_pretool_blocks_git_commit_no_verify() -> None:
    """`git commit --no-verify -m "x"` must be blocked; --no-verify was the
    Layer 2 gap that motivated promoting plain `git commit` to a
    PreToolUse-blocked shape."""
    out = _invoke_pretool('git commit --no-verify -m "x"')
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_pretool_blocks_env_wrapper_around_git_commit() -> None:
    out = _invoke_pretool('env FOO=1 git commit -m "x"')
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_pretool_blocks_command_wrapper_around_git_add() -> None:
    out = _invoke_pretool('command git add foo.txt')
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_pretool_blocks_git_dash_C_path_subcommand() -> None:
    """Git global option `-C <path>` must not hide the subcommand."""
    out = _invoke_pretool('git -C . add foo.txt')
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_pretool_blocks_git_dash_c_kv_subcommand() -> None:
    """`git -c user.name=x commit -m "x"` must be blocked."""
    out = _invoke_pretool('git -c user.name=x commit -m "x"')
    assert out is not None
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_pretool_allows_real_env_override() -> None:
    """An actual env assignment for the same segment is the sanctioned
    manual override path."""
    out = _invoke_pretool('AIW_ALLOW_RAW_GIT_COMMIT=1 git commit -m "manual"')
    if out is None:
        return
    assert out.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"


def test_pretool_allows_real_env_override_with_no_verify() -> None:
    out = _invoke_pretool(
        'AIW_ALLOW_RAW_GIT_COMMIT=1 git commit --no-verify -m "manual"'
    )
    if out is None:
        return
    assert out.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"


def test_pretool_allows_git_diff() -> None:
    """Read-only `git diff` must not be banned."""
    out = _invoke_pretool("git diff --cached")
    if out is None:
        return
    assert out.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"


def test_pretool_allows_git_commit_tree() -> None:
    """`git commit-tree` is the primitive scoped_commit uses; the parser
    must distinguish it from `git commit` (different subcommand token)."""
    out = _invoke_pretool('git commit-tree abc123 -p def456 -m "x"')
    if out is None:
        return
    assert out.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"


def test_pretool_allows_git_update_ref() -> None:
    out = _invoke_pretool('git update-ref refs/heads/main abc123 def456')
    if out is None:
        return
    assert out.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"


# ---------------------------------------------------------------------------
# Layer 2: pre-commit hook backstop (run_git.py)
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    })
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _setup_temp_repo_with_pre_commit(tmp_path: Path) -> Path:
    """Build a throwaway git repo wired to the live run_git.py pre-commit hook."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git("add", "seed.txt", cwd=repo)
    # Seed commit must bypass the guard so the test repo has a parent.
    _git(
        "commit", "-q", "-m", "seed",
        cwd=repo,
        env_extra={"AIW_ALLOW_RAW_GIT_COMMIT": "1"},
    )
    # Wire up the pre-commit hook by copying the live shim and pointing
    # core.hooksPath at it.
    repo_hooks = repo / ".githooks"
    repo_hooks.mkdir()
    pre_commit_shim = repo_hooks / "pre-commit"
    pre_commit_shim.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        f"exec {sys.executable} {RUN_GIT_PATH} hook pre-commit\n",
        encoding="utf-8",
    )
    pre_commit_shim.chmod(0o755)
    _git("config", "core.hooksPath", str(repo_hooks), cwd=repo)
    return repo


def test_pre_commit_hook_refuses_raw_commit_without_override(tmp_path: Path) -> None:
    repo = _setup_temp_repo_with_pre_commit(tmp_path)
    (repo / "newfile.txt").write_text("hi\n", encoding="utf-8")
    _git("add", "newfile.txt", cwd=repo)
    res = _git("commit", "-m", "raw commit attempt", cwd=repo)
    assert res.returncode != 0, (
        f"raw commit was NOT blocked.\nstdout: {res.stdout}\nstderr: {res.stderr}"
    )
    assert "scoped_commit.py" in res.stderr
    assert "AIW_ALLOW_RAW_GIT_COMMIT" in res.stderr


def test_pre_commit_hook_allows_with_explicit_override(tmp_path: Path) -> None:
    repo = _setup_temp_repo_with_pre_commit(tmp_path)
    (repo / "ok.txt").write_text("hi\n", encoding="utf-8")
    _git("add", "ok.txt", cwd=repo)
    res = _git(
        "commit", "-m", "explicit raw commit",
        cwd=repo,
        env_extra={"AIW_ALLOW_RAW_GIT_COMMIT": "1"},
    )
    assert res.returncode == 0, (
        f"override-permitted commit failed.\nstdout: {res.stdout}\nstderr: {res.stderr}"
    )


def test_pre_commit_hook_allows_scoped_commit_path(tmp_path: Path) -> None:
    """scoped_commit.py uses `git commit-tree`, which does not trigger the
    pre-commit hook. Therefore the substrate-fix actuator is never blocked."""
    repo = _setup_temp_repo_with_pre_commit(tmp_path)
    (repo / "via_scoped.txt").write_text("hello\n", encoding="utf-8")
    res = subprocess.run(
        [
            sys.executable,
            str(REAL_ROOT / "tools/meta/control/scoped_commit.py"),
            "--repo-root", str(repo),
            "full-paths",
            "--path", "via_scoped.txt",
            "--allow-untracked",
            "--message", "via scoped_commit",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )
    assert res.returncode == 0, (
        f"scoped_commit.py path was incorrectly blocked.\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )
    log = _git("log", "--oneline", cwd=repo).stdout
    assert "via scoped_commit" in log


# ---------------------------------------------------------------------------
# Static guard: ban-list completeness
# ---------------------------------------------------------------------------


def test_runtime_hook_banned_subcommand_set() -> None:
    """The parser-based guard bans whole subcommands, not specific flag
    shapes. Both `add` and `commit` must be in the ban-set so every flag
    combination (`-A`, `--all`, `.`, `-am`, `--no-verify`, etc.) is covered."""
    assert "add" in runtime_hook.BANNED_RAW_GIT_SUBCOMMANDS
    assert "commit" in runtime_hook.BANNED_RAW_GIT_SUBCOMMANDS


def test_runtime_hook_no_substring_bypass_token_for_test_paths() -> None:
    """The earlier guard had cosmetic test-path substring bypass tokens
    (`tools/meta/control/test_`, `system/server/tests/test_`). The parser-
    based guard must NOT carry such substring bypasses — they are unsafe
    because a command like `echo tools/meta/control/test_x && git add -A`
    would be allowed despite invoking the dangerous shape. Pin the absence."""
    src = (REAL_ROOT / ".claude/hooks/runtime_hook.py").read_text(encoding="utf-8")
    # The token can appear in commentary / doc strings; check that no
    # active code uses it as a substring bypass for the guard.
    assert "tools/meta/control/test_" not in src or "RAW_GIT_GUARD_BYPASS_TOKENS" not in src, (
        "runtime_hook.py still ships RAW_GIT_GUARD_BYPASS_TOKENS substring "
        "bypass; the parser-based guard must not use raw substring bypass."
    )


# ---------------------------------------------------------------------------
# Layer 2 backstops: pre-commit + prepare-commit-msg
# ---------------------------------------------------------------------------


def _setup_temp_repo_with_both_backstops(tmp_path: Path) -> Path:
    """Build a throwaway git repo wired to BOTH pre-commit and
    prepare-commit-msg hooks via run_git.py."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git("add", "seed.txt", cwd=repo)
    _git(
        "commit", "-q", "-m", "seed",
        cwd=repo,
        env_extra={"AIW_ALLOW_RAW_GIT_COMMIT": "1"},
    )
    repo_hooks = repo / ".githooks"
    repo_hooks.mkdir()
    (repo_hooks / "pre-commit").write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        f"exec {sys.executable} {RUN_GIT_PATH} hook pre-commit\n",
        encoding="utf-8",
    )
    (repo_hooks / "prepare-commit-msg").write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        f'exec {sys.executable} {RUN_GIT_PATH} hook prepare-commit-msg "$@"\n',
        encoding="utf-8",
    )
    (repo_hooks / "pre-commit").chmod(0o755)
    (repo_hooks / "prepare-commit-msg").chmod(0o755)
    _git("config", "core.hooksPath", str(repo_hooks), cwd=repo)
    return repo


def test_prepare_commit_msg_refuses_no_verify_commit_without_override(tmp_path: Path) -> None:
    """`git commit --no-verify -m "..."` bypasses pre-commit but NOT
    prepare-commit-msg. The backstop must catch this path."""
    repo = _setup_temp_repo_with_both_backstops(tmp_path)
    (repo / "novfile.txt").write_text("v\n", encoding="utf-8")
    _git("add", "novfile.txt", cwd=repo)
    res = _git("commit", "--no-verify", "-m", "no-verify attempt", cwd=repo)
    assert res.returncode != 0, (
        f"--no-verify commit was NOT blocked.\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )
    assert "scoped_commit.py" in res.stderr
    assert "AIW_ALLOW_RAW_GIT_COMMIT" in res.stderr


def test_prepare_commit_msg_allows_no_verify_with_explicit_override(tmp_path: Path) -> None:
    repo = _setup_temp_repo_with_both_backstops(tmp_path)
    (repo / "ok.txt").write_text("v\n", encoding="utf-8")
    _git("add", "ok.txt", cwd=repo)
    res = _git(
        "commit", "--no-verify", "-m", "explicit override",
        cwd=repo,
        env_extra={"AIW_ALLOW_RAW_GIT_COMMIT": "1"},
    )
    assert res.returncode == 0, (
        f"override-permitted commit failed.\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr}"
    )
