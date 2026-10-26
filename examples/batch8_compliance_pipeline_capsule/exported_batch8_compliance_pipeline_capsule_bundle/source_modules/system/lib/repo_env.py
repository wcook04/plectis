"""
[PURPOSE]
- Teleology: Resolve the repository-authoritative Python environment and expose deterministic helpers for re-exec, wrapper alignment, and subprocess environment shaping.
- Mechanism: Walk upward to the repo marker, rank repo-local environment candidates, derive repo-python/site-packages targets, and project a compact environment contract for callers.

[INTERFACE]
- Exports: resolve_repo_root, iter_repo_env_candidates, resolve_repo_env_root, resolve_repo_python, resolve_repo_site_packages, repo_python_reexec_command, maybe_reexec_into_repo_python, add_repo_site_packages, repo_process_env, build_env_contract.
- Reads: cwd/start paths, environment variables, repo-local venv layout, sys.executable/sys.argv/sys.path, and master_config.json as the repo-root marker.
- Writes: maybe_reexec_into_repo_python() replaces the current process image via os.execv(); add_repo_site_packages() mutates sys.path through site.addsitedir(); repo_process_env() returns a derived mapping without mutating os.environ.

[FLOW]
- resolve_repo_root() finds the repo boundary -> resolve_repo_env_root() applies candidate precedence -> repo_python_reexec_command() and maybe_reexec_into_repo_python() align entrypoints to the repo interpreter -> repo_process_env() and build_env_contract() project wrapper-facing environment facts.
- When-needed: Open when a launcher, kernel surface, or subprocess helper must use the repo-authoritative Python environment instead of ambient `python3` or arbitrary `VIRTUAL_ENV` state.
- Escalates-to: system/lib/kernel/state.py; master_config.json; repo-env
- Navigation-group: kernel_lib

[DEPENDENCIES]
- os, site, sys, pathlib.Path: Inspect the live interpreter/process state and shape wrapper-compatible process environments.
- master_config.json: Repo-root marker used by resolve_repo_root().

[CONSTRAINTS]
- Candidate precedence is deterministic: AI_WORKFLOW_ENV_ROOT -> repo-local venv/.venv -> VIRTUAL_ENV only when it resolves inside the repo.
- These helpers never create or repair environments; they only discover and project existing ones.
- Missing repo env state degrades to None/unchanged mappings rather than raising.
"""
from __future__ import annotations

import os
import site
import sys
from pathlib import Path
from typing import Any

DEFAULT_ENV_DIR_NAMES = ("venv", ".venv")
DEFAULT_SKIP_ENVVAR = "AI_WORKFLOW_SKIP_ENV_REEXEC"


def _path_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, FileNotFoundError):
        return False


def _relative_to_repo(path: Path | None, repo_root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _env_root_if_valid(path_like: str | Path | None) -> Path | None:
    token = str(path_like or "").strip()
    if not token:
        return None
    candidate = Path(token).expanduser()
    try:
        resolved = candidate.resolve()
    except FileNotFoundError:
        resolved = candidate
    python_bin = resolved / "bin" / "python"
    return resolved if python_bin.exists() else None


def resolve_repo_root(start: Path | None = None, *, marker: str = "master_config.json", max_hops: int = 8) -> Path:
    """[ACTION]
    - Teleology: Resolve the bounded repository root from an arbitrary starting path.
    - Mechanism: Walk parent directories until the marker file is found or max_hops is exhausted.
    - Guarantee: Returns a resolved Path; falls back to the resolved starting path when the marker is not discovered.
    - Fails: None.
    - When-needed: Open when a caller starts from an arbitrary cwd or file path and needs the repo boundary before resolving repo-local wrappers or environment contracts.
    - Escalates-to: master_config.json; system/lib/kernel/state.py
    """
    current = (start or Path.cwd()).resolve()
    for _ in range(max_hops):
        if (current / marker).exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return (start or Path.cwd()).resolve()


def iter_repo_env_candidates(repo_root: Path) -> list[tuple[str, Path]]:
    """
    [ACTION]
    - Teleology: Enumerate all valid repo environment candidates in declared precedence order without selecting one.
    - Guarantee: Returns a list of (label, env_root) pairs for every valid candidate found; empty list when none exist.
    - Fails: None.
    """
    candidates: list[tuple[str, Path]] = []
    seen: set[Path] = set()

    def register(label: str, path_like: str | Path | None, *, require_within_repo: bool = False) -> None:
        env_root = _env_root_if_valid(path_like)
        if env_root is None:
            return
        if require_within_repo and not _path_within(env_root, repo_root):
            return
        key = env_root.resolve()
        if key in seen:
            return
        seen.add(key)
        candidates.append((label, env_root))

    register("AI_WORKFLOW_ENV_ROOT", os.environ.get("AI_WORKFLOW_ENV_ROOT"))
    for name in DEFAULT_ENV_DIR_NAMES:
        register(name, repo_root / name)
    register("VIRTUAL_ENV", os.environ.get("VIRTUAL_ENV"), require_within_repo=True)
    return candidates


def resolve_repo_env_root(repo_root: Path) -> tuple[Path | None, str | None]:
    """[ACTION]
    - Teleology: Choose the authoritative repo environment root and record which discovery path won.
    - Mechanism: Read iter_repo_env_candidates() in declared precedence order and return the first valid pair.
    - Guarantee: Returns (env_root, source_label) or (None, None) when no acceptable repo environment exists.
    - Fails: None.
    - When-needed: Open when environment discovery needs the exact repo candidate precedence instead of ad hoc `VIRTUAL_ENV` checks.
    - Escalates-to: repo-env; system/lib/kernel/state.py; master_config.json
    - Navigation-group: kernel_lib
    """
    candidates = iter_repo_env_candidates(repo_root)
    if not candidates:
        return None, None
    label, root = candidates[0]
    return root, label


def resolve_repo_python(repo_root: Path) -> Path | None:
    """
    [ACTION]
    - Teleology: Resolve the path to the repo-authoritative Python interpreter binary.
    - Guarantee: Returns an absolute Path to `bin/python` when the repo env root exists and contains that binary; otherwise None.
    - Fails: None.
    """
    env_root, _source = resolve_repo_env_root(repo_root)
    if env_root is None:
        return None
    python_bin = env_root / "bin" / "python"
    return python_bin if python_bin.exists() else None


def resolve_repo_site_packages(repo_root: Path) -> Path | None:
    """
    [ACTION]
    - Teleology: Resolve the path to the repo environment's site-packages directory.
    - Guarantee: Returns an absolute Path to the first `python*/site-packages` directory found under the env root's lib; otherwise None.
    - Fails: None.
    """
    env_root, _source = resolve_repo_env_root(repo_root)
    if env_root is None:
        return None
    lib_dir = env_root / "lib"
    for candidate in sorted(lib_dir.glob("python*/site-packages")):
        if candidate.exists():
            return candidate
    return None


def repo_python_reexec_command(
    *,
    repo_root: Path,
    argv: list[str] | tuple[str, ...] | None = None,
    script_path: str | Path | None = None,
    current_executable: str | None = None,
    current_prefix: str | None = None,
    skip_env_var: str = DEFAULT_SKIP_ENVVAR,
) -> list[str] | None:
    """[ACTION]
    - Teleology: Decide whether the current process should hop into the repo interpreter and, if so, return the exact exec command.
    - Mechanism: Honor the skip env var, resolve the repo python, detect whether the current executable/prefix already lives under that env root, and build `[repo_python, script, *argv]`.
    - Guarantee: Returns None when no re-exec is needed or possible; otherwise returns the exact command vector suitable for os.execv().
    - Fails: None.
    - When-needed: Open when a top-level launcher must decide whether to re-exec into `./repo-python` without mutating the process yet.
    - Escalates-to: repo-python; repo-env; system/lib/kernel/state.py
    """
    if os.environ.get(skip_env_var) == "1":
        return None
    repo_python = resolve_repo_python(repo_root)
    if repo_python is None:
        return None

    env_root = repo_python.parent.parent.resolve()
    current_exec = Path(current_executable or sys.executable).resolve()
    if current_prefix:
        try:
            Path(current_prefix).resolve().relative_to(env_root)
            return None
        except (ValueError, FileNotFoundError):
            pass
    try:
        current_exec.relative_to(env_root)
        return None
    except ValueError:
        pass

    target_script = Path(script_path or sys.argv[0]).resolve()
    target_argv = list(argv if argv is not None else sys.argv[1:])
    return [str(repo_python), str(target_script), *target_argv]


def maybe_reexec_into_repo_python(
    repo_root: Path,
    *,
    argv: list[str] | tuple[str, ...] | None = None,
    script_path: str | Path | None = None,
    current_executable: str | None = None,
    current_prefix: str | None = None,
    skip_env_var: str = DEFAULT_SKIP_ENVVAR,
) -> None:
    """[ACTION]
    - Teleology: Enforce repo-interpreter execution for the current process when the ambient interpreter is not the repo one.
    - Mechanism: Delegate command selection to repo_python_reexec_command(), set the skip guard, then replace the process image via os.execv().
    - Guarantee: Returns normally only when no re-exec is needed; successful re-exec does not return.
    - Fails: os.execv() errors propagate from the operating system.
    - When-needed: Open when an entrypoint should immediately enforce repo-Python execution instead of only computing the possible command.
    - Escalates-to: repo-python; repo-env; system/lib/kernel/state.py
    """
    command = repo_python_reexec_command(
        repo_root=repo_root,
        argv=argv,
        script_path=script_path,
        current_executable=current_executable,
        current_prefix=current_prefix,
        skip_env_var=skip_env_var,
    )
    if not command:
        return
    os.environ[skip_env_var] = "1"
    os.execv(command[0], command)


def add_repo_site_packages(repo_root: Path) -> Path | None:
    """
    [ACTION]
    - Teleology: Register the repo environment's site-packages directory with the current interpreter via site.addsitedir().
    - Guarantee: Returns the site-packages Path when registration succeeds; None when no repo site-packages are discoverable.
    - Fails: None.
    """
    site_packages = resolve_repo_site_packages(repo_root)
    if site_packages is None:
        return None
    resolved = str(site_packages.resolve())
    if resolved not in sys.path:
        site.addsitedir(resolved)
    return site_packages


def repo_process_env(repo_root: Path, *, base_env: dict[str, str] | None = None) -> dict[str, str]:
    """[ACTION]
    - Teleology: Build a subprocess environment that carries the repo wrapper contract and preferred PATH/VIRTUAL_ENV settings.
    - Mechanism: Copy base_env or os.environ, stamp AI_WORKFLOW_REPO_* variables, and prepend the resolved env's `bin` directory when available.
    - Guarantee: Returns a derived env mapping without mutating the caller's input mapping or os.environ.
    - Fails: None.
    - When-needed: Open when spawning a subprocess or shell that must inherit repo-local PATH, `VIRTUAL_ENV`, and wrapper locations.
    - Escalates-to: repo-env; system/lib/kernel/state.py; master_config.json
    - Navigation-group: kernel_lib
    """
    env = dict(base_env or os.environ)
    env_root, source = resolve_repo_env_root(repo_root)
    env["AI_WORKFLOW_REPO_ROOT"] = str(repo_root.resolve())
    env["AI_WORKFLOW_REPO_PYTHON"] = str((repo_root / "repo-python").resolve())
    env["AI_WORKFLOW_REPO_PYTEST"] = str((repo_root / "repo-pytest").resolve())
    env["AI_WORKFLOW_REPO_ENV"] = str((repo_root / "repo-env").resolve())
    if env_root is not None:
        env["AI_WORKFLOW_ENV_ROOT"] = str(env_root.resolve())
        env["AI_WORKFLOW_ENV_SOURCE"] = str(source or "repo")
        env["VIRTUAL_ENV"] = str(env_root.resolve())
        bin_dir = str((env_root / "bin").resolve())
        current_path = env.get("PATH", "")
        path_parts = [part for part in current_path.split(os.pathsep) if part]
        if bin_dir not in path_parts:
            env["PATH"] = os.pathsep.join([bin_dir, *path_parts]) if path_parts else bin_dir
    return env


def build_env_contract(repo_root: Path) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Emit a compact, operator-facing contract describing which repo environment and wrapper commands are in effect.
    - Mechanism: Resolve env root and python target, then project repo-relative paths, wrapper names, selection order, and usage rules into one dict.
    - Guarantee: Returns a deterministic mapping shaped for diagnostics and CLI/status output.
    - Fails: None.
    - When-needed: Open when CLI or diagnostics output needs the stable repo-environment contract instead of inspecting live process state ad hoc.
    - Escalates-to: repo-python; repo-env; master_config.json
    - Navigation-group: kernel_lib
    """
    env_root, source = resolve_repo_env_root(repo_root)
    repo_python = resolve_repo_python(repo_root)
    python_target = repo_python or Path(sys.executable)
    return {
        "resolved_env_root": _relative_to_repo(env_root, repo_root),
        "resolved_from": source,
        "resolved_python": _relative_to_repo(python_target, repo_root),
        "commands": {
            "repo_python": "./repo-python",
            "repo_pytest": "./repo-pytest",
            "repo_env": "./repo-env",
        },
        "selection_order": [
            "AI_WORKFLOW_ENV_ROOT",
            "venv",
            ".venv",
            "VIRTUAL_ENV (only if it lives inside the repo)",
        ],
        "rules": [
            "Use ./repo-python for ad hoc Python so commands land in the repo environment.",
            "Use ./repo-pytest for tests instead of bare python3 -m pytest.",
            "Use ./repo-env <command> when launching shells or CLIs that should inherit the repo PATH and VIRTUAL_ENV.",
            "Top-level repo entrypoints re-exec into the repo environment when possible, but test commands should still call the wrappers directly.",
        ],
    }
