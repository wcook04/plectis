"""Public-safe command-run singleflight capsule.

This is a source-faithful public refactor of
`system/lib/command_run_singleflight.py`. It keeps the core substrate behavior:
content-addressed command keys, fcntl-backed leader/follower coordination,
completed-run reuse, captured output replay, and scoped dirty/content
fingerprinting. It deliberately does not import or expose the live
`state/command_runs/` tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import fcntl

SCHEMA_VERSION = "engine_room_command_run_singleflight_v1"
ORGAN_ID = "engine_room_command_run_singleflight"
SOURCE_REFS = ("system/lib/command_run_singleflight.py",)
SOURCE_TO_TARGET_RELATION = "source_faithful_public_refactor"
CLAIM_CEILING = (
    "Content-addressed subprocess singleflight capsule. It demonstrates "
    "fcntl-backed leader/follower collapse, completed-run reuse, and scoped "
    "fingerprinting over public fixture commands. It is not a job scheduler, "
    "not a daemon, not a live state/command_runs export, and not a distributed "
    "lock service."
)
ANTI_CLAIMS = (
    "not_a_job_scheduler",
    "not_a_daemon",
    "not_live_command_runs_export",
    "not_distributed_lock_service",
)


@dataclass(frozen=True)
class RunReceipt:
    schema_version: str
    organ_id: str
    role: str
    status: str
    exit_code: int
    key_hash: str
    run_id: str
    stdout: str
    stderr: str
    reused_completed: bool
    duplicate_wait_s: float
    source_refs: tuple[str, ...]
    source_to_target_relation: str
    claim_ceiling: str
    anti_claims: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _short_hash(payload: Any, length: int = 24) -> str:
    return _sha256_text(_stable_json(payload))[:length]


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_event(state_root: Path, payload: Mapping[str, Any]) -> None:
    events = state_root / "events.jsonl"
    lock = state_root / "events.lock"
    events.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        with events.open("a", encoding="utf-8") as events_fh:
            events_fh.write(json.dumps(dict(payload), sort_keys=True) + "\n")


def _paths(state_root: Path, key_hash: str, run_id: str | None = None) -> dict[str, Path]:
    paths = {
        "lock": state_root / "locks" / f"{key_hash}.lock",
        "active": state_root / "active" / f"{key_hash}.json",
        "latest": state_root / "latest_by_key" / f"{key_hash}.json",
    }
    if run_id:
        paths.update(
            {
                "run": state_root / "runs" / f"{run_id}.json",
                "stdout": state_root / "outputs" / f"{run_id}.stdout",
                "stderr": state_root / "outputs" / f"{run_id}.stderr",
            }
        )
    return paths


def _pid_alive(pid: Any) -> bool:
    try:
        pid_value = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_value <= 0:
        return False
    try:
        os.kill(pid_value, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _active_pending(metadata: Mapping[str, Any], *, pending_window_s: float = 5.0) -> bool:
    try:
        started = float(metadata.get("started_at_epoch_s") or 0)
    except (TypeError, ValueError):
        return False
    return bool(started) and (time.time() - started) <= pending_window_s


def _discover_git_root(cwd: Path) -> Path | None:
    proc = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        return None
    root = proc.stdout.strip()
    return Path(root) if root else None


def _git_bytes(root: Path, args: Sequence[str]) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(root), *[str(arg) for arg in args]],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return proc.stdout if proc.returncode == 0 else b""


def _scope_content_fingerprint(cwd: Path, scope_paths: Sequence[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for raw in sorted({str(path).strip() for path in scope_paths if str(path).strip()}):
        path = (cwd / raw).resolve()
        if not path.is_file():
            missing.append(raw)
            continue
        data = path.read_bytes()
        rows.append({"path": raw, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return {
        "row_count": len(rows),
        "missing": missing,
        "rows_sha256": _sha256_text(_stable_json(rows)),
    }


def _git_scope_paths(*, cwd: Path, git_root: Path, scope_paths: Sequence[str]) -> list[str]:
    repo_scope: list[str] = []
    for raw in sorted({str(path).strip() for path in scope_paths if str(path).strip()}):
        resolved = (cwd / raw).resolve()
        try:
            repo_scope.append(resolved.relative_to(git_root).as_posix())
        except ValueError:
            repo_scope.append(raw)
    return repo_scope


def build_command_key(
    *,
    argv: Sequence[str],
    cwd: Path,
    resource_class: str,
    scope_paths: Sequence[str] = (),
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build the public command key used for singleflight collapse.

    The key carries hashes and labels rather than absolute paths so receipts can
    stay public-safe. When `cwd` is inside a Git repository it includes HEAD,
    porcelain status, binary diff, and untracked content hashes for the scoped
    path set. Outside Git it falls back to scoped file-content hashes.
    """

    env = dict(env or os.environ)
    scope = sorted({str(path).strip() for path in scope_paths if str(path).strip()})
    git_root = _discover_git_root(cwd)
    if git_root:
        repo_scope = _git_scope_paths(cwd=cwd, git_root=git_root, scope_paths=scope)
        pathspec = ["--", *repo_scope] if repo_scope else []
        head = _git_bytes(git_root, ["rev-parse", "HEAD"]).decode("utf-8", "replace").strip()
        if repo_scope:
            status = _git_bytes(
                git_root,
                ["status", "--porcelain=v1", "--untracked-files=all", *pathspec],
            )
            diff = _git_bytes(git_root, ["diff", "--full-index", "--binary", *pathspec])
            staged_diff = _git_bytes(
                git_root,
                ["diff", "--cached", "--full-index", "--binary", *pathspec],
            )
        else:
            status = b""
            diff = b""
            staged_diff = b""
        dirty = {
            "mode": "git",
            "head": head or "unknown",
            "status_sha256": hashlib.sha256(status).hexdigest(),
            "diff_sha256": hashlib.sha256(diff).hexdigest(),
            "staged_diff_sha256": hashlib.sha256(staged_diff).hexdigest(),
            "scope_paths_git": repo_scope,
            "scope_content": _scope_content_fingerprint(git_root, repo_scope),
        }
    else:
        dirty = {
            "mode": "file_content",
            "head": "not_git",
            "scope_content": _scope_content_fingerprint(cwd, scope),
        }
    return {
        "schema": "engine_room_command_run_key_v1",
        "argv_sha256": _sha256_text(_stable_json([str(arg) for arg in argv])),
        "argv_preview": [Path(str(arg)).name if index == 0 else str(arg) for index, arg in enumerate(argv[:4])],
        "cwd_label": cwd.name or ".",
        "cwd_sha256": _sha256_text(str(cwd.resolve())),
        "resource_class": resource_class,
        "scope_paths": scope,
        "dirty_fingerprint": dirty,
        "env_fingerprint": {
            "PYTHONPATH": env.get("PYTHONPATH", ""),
            "PYTEST_ADDOPTS": env.get("PYTEST_ADDOPTS", ""),
        },
    }


def _run_id(key_hash: str) -> str:
    return f"cmdrun_{int(time.time() * 1000)}_{os.getpid()}_{key_hash[:12]}"


def _metadata(
    *,
    key_hash: str,
    run_id: str,
    key: Mapping[str, Any],
    resource_class: str,
    owner_surface: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "status": "running",
        "run_id": run_id,
        "key_hash": key_hash,
        "key": dict(key),
        "resource_class": resource_class,
        "owner_surface": owner_surface,
        "started_at_epoch_s": time.time(),
        "pid": None,
    }


def _receipt(
    *,
    role: str,
    status: str,
    exit_code: int,
    key_hash: str,
    run_id: str,
    stdout: str,
    stderr: str,
    reused_completed: bool = False,
    duplicate_wait_s: float = 0.0,
) -> RunReceipt:
    return RunReceipt(
        schema_version=SCHEMA_VERSION,
        organ_id=ORGAN_ID,
        role=role,
        status=status,
        exit_code=int(exit_code),
        key_hash=key_hash,
        run_id=run_id,
        stdout=stdout,
        stderr=stderr,
        reused_completed=reused_completed,
        duplicate_wait_s=round(duplicate_wait_s, 3),
        source_refs=SOURCE_REFS,
        source_to_target_relation=SOURCE_TO_TARGET_RELATION,
        claim_ceiling=CLAIM_CEILING,
        anti_claims=ANTI_CLAIMS,
    )


def _read_outputs(state_root: Path, key_hash: str, run_id: str) -> tuple[str, str]:
    paths = _paths(state_root, key_hash, run_id)
    stdout = paths["stdout"].read_text(encoding="utf-8") if paths["stdout"].is_file() else ""
    stderr = paths["stderr"].read_text(encoding="utf-8") if paths["stderr"].is_file() else ""
    return stdout, stderr


def _run_leader(
    *,
    argv: Sequence[str],
    cwd: Path,
    state_root: Path,
    metadata: dict[str, Any],
    env: Mapping[str, str] | None,
) -> RunReceipt:
    key_hash = str(metadata["key_hash"])
    run_id = str(metadata["run_id"])
    paths = _paths(state_root, key_hash, run_id)
    proc = subprocess.Popen(
        [str(arg) for arg in argv],
        cwd=str(cwd),
        env=dict(env or os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    metadata = {**metadata, "pid": proc.pid}
    _write_json(paths["active"], metadata)
    _write_json(paths["run"], metadata)
    _append_event(
        state_root,
        {
            "event_type": "leader_started",
            "key_hash": key_hash,
            "run_id": run_id,
            "resource_class": metadata["resource_class"],
        },
    )
    stdout, stderr = proc.communicate()
    paths["stdout"].parent.mkdir(parents=True, exist_ok=True)
    paths["stderr"].parent.mkdir(parents=True, exist_ok=True)
    paths["stdout"].write_text(stdout, encoding="utf-8")
    paths["stderr"].write_text(stderr, encoding="utf-8")
    finished = {
        **metadata,
        "status": "completed",
        "exit_code": int(proc.returncode),
        "finished_at_epoch_s": time.time(),
    }
    _write_json(paths["run"], finished)
    _write_json(paths["active"], finished)
    _write_json(paths["latest"], finished)
    _append_event(
        state_root,
        {
            "event_type": "leader_completed",
            "key_hash": key_hash,
            "run_id": run_id,
            "exit_code": int(proc.returncode),
        },
    )
    return _receipt(
        role="leader",
        status="completed",
        exit_code=int(proc.returncode),
        key_hash=key_hash,
        run_id=run_id,
        stdout=stdout,
        stderr=stderr,
    )


def _wait_for_active(
    *,
    state_root: Path,
    active: Mapping[str, Any],
    key_hash: str,
    timeout_s: float,
) -> RunReceipt:
    started = time.time()
    active_path = _paths(state_root, key_hash)["active"]
    run_id = str(active.get("run_id") or "")
    while time.time() - started <= timeout_s:
        current = _read_json(active_path)
        if current and current.get("status") == "completed":
            run_id = str(current.get("run_id") or run_id)
            stdout, stderr = _read_outputs(state_root, key_hash, run_id)
            _append_event(
                state_root,
                {
                    "event_type": "follower_replayed",
                    "key_hash": key_hash,
                    "run_id": run_id,
                    "exit_code": int(current.get("exit_code") or 0),
                },
            )
            return _receipt(
                role="follower",
                status="completed",
                exit_code=int(current.get("exit_code") or 0),
                key_hash=key_hash,
                run_id=run_id,
                stdout=stdout,
                stderr=stderr,
                duplicate_wait_s=time.time() - started,
            )
        if current and current.get("pid") and not _pid_alive(current.get("pid")):
            break
        if current and not current.get("pid") and not _active_pending(current):
            break
        time.sleep(0.05)
    return _receipt(
        role="follower",
        status="stale_or_timeout",
        exit_code=124,
        key_hash=key_hash,
        run_id=run_id,
        stdout="",
        stderr="active run did not complete before timeout",
        duplicate_wait_s=time.time() - started,
    )


def run_command_singleflight(
    argv: Sequence[str],
    *,
    state_root: Path,
    cwd: Path | None = None,
    resource_class: str = "command",
    owner_surface: str = ORGAN_ID,
    scope_paths: Sequence[str] = (),
    reuse_completed: bool = False,
    env: Mapping[str, str] | None = None,
    wait_timeout_s: float = 30.0,
) -> RunReceipt:
    if not argv:
        raise ValueError("argv must not be empty")
    run_cwd = Path(cwd or Path.cwd()).resolve()
    state = Path(state_root).resolve()
    key = build_command_key(
        argv=argv,
        cwd=run_cwd,
        resource_class=resource_class,
        scope_paths=scope_paths,
        env=env,
    )
    key_hash = _short_hash(key)
    run_id = _run_id(key_hash)
    metadata = _metadata(
        key_hash=key_hash,
        run_id=run_id,
        key=key,
        resource_class=resource_class,
        owner_surface=owner_surface,
    )
    paths = _paths(state, key_hash, run_id)
    paths["lock"].parent.mkdir(parents=True, exist_ok=True)
    active_to_wait: dict[str, Any] | None = None
    reusable: dict[str, Any] | None = None
    with paths["lock"].open("a+", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        active = _read_json(paths["active"])
        if active and active.get("status") == "running" and (
            _pid_alive(active.get("pid")) or _active_pending(active)
        ):
            active_to_wait = dict(active)
            _append_event(state, {"event_type": "duplicate_attached", "key_hash": key_hash})
        elif active and active.get("status") == "completed" and reuse_completed:
            reusable = dict(active)
            _append_event(state, {"event_type": "completed_reused", "key_hash": key_hash})
        else:
            _write_json(paths["active"], metadata)
            _write_json(paths["run"], metadata)
    if reusable is not None:
        reused_run_id = str(reusable.get("run_id") or "")
        stdout, stderr = _read_outputs(state, key_hash, reused_run_id)
        return _receipt(
            role="reused",
            status="completed",
            exit_code=int(reusable.get("exit_code") or 0),
            key_hash=key_hash,
            run_id=reused_run_id,
            stdout=stdout,
            stderr=stderr,
            reused_completed=True,
        )
    if active_to_wait is not None:
        return _wait_for_active(
            state_root=state,
            active=active_to_wait,
            key_hash=key_hash,
            timeout_s=wait_timeout_s,
        )
    return _run_leader(argv=argv, cwd=run_cwd, state_root=state, metadata=metadata, env=env)


def _counter_command(counter_path: Path, *, sleep_s: float = 0.0) -> list[str]:
    code = (
        "from pathlib import Path\n"
        "import fcntl, sys, time\n"
        f"path = Path({str(counter_path)!r})\n"
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        "with path.open('a+', encoding='utf-8') as fh:\n"
        "    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)\n"
        "    fh.seek(0)\n"
        "    raw = fh.read().strip()\n"
        "    value = int(raw or '0') + 1\n"
        "    fh.seek(0)\n"
        "    fh.truncate()\n"
        "    fh.write(str(value))\n"
        "    fh.flush()\n"
        f"time.sleep({sleep_s!r})\n"
        "print(f'counter={value}')\n"
    )
    return [sys.executable, "-c", code]


def _simple_command(message: str) -> list[str]:
    return [sys.executable, "-c", f"print({message!r})"]


def _load_cases(input_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    cases: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(input_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            cases.append((path, payload))
    return cases


def _case_status(case: Mapping[str, Any], *, scratch: Path) -> dict[str, Any]:
    exercise = str(case.get("exercise") or "")
    state = scratch / str(case.get("case_id") or exercise) / "state"
    cwd = scratch / str(case.get("case_id") or exercise) / "cwd"
    cwd.mkdir(parents=True, exist_ok=True)
    if exercise == "single_leader":
        receipt = run_command_singleflight(
            _simple_command("singleflight fixture work"),
            state_root=state,
            cwd=cwd,
            resource_class="fixture",
        )
        ok = receipt.role == "leader" and receipt.exit_code == 0 and "fixture work" in receipt.stdout
        return {"ok": ok, "receipt": receipt.to_dict()}
    if exercise == "completed_reuse":
        counter = scratch / "reuse_counter.txt"
        first = run_command_singleflight(_counter_command(counter), state_root=state, cwd=cwd)
        second = run_command_singleflight(
            _counter_command(counter),
            state_root=state,
            cwd=cwd,
            reuse_completed=True,
        )
        counter_value = counter.read_text(encoding="utf-8").strip()
        ok = first.role == "leader" and second.role == "reused" and counter_value == "1"
        return {"ok": ok, "receipt": second.to_dict(), "counter_value": counter_value}
    if exercise == "scope_mutation_changes_key":
        scoped = cwd / "scoped.txt"
        scoped.write_text("before\n", encoding="utf-8")
        key_before = build_command_key(
            argv=_simple_command("scope"),
            cwd=cwd,
            resource_class="fixture",
            scope_paths=["scoped.txt"],
        )
        scoped.write_text("after\n", encoding="utf-8")
        key_after = build_command_key(
            argv=_simple_command("scope"),
            cwd=cwd,
            resource_class="fixture",
            scope_paths=["scoped.txt"],
        )
        ok = _short_hash(key_before) != _short_hash(key_after)
        return {"ok": ok, "key_changed": ok}
    if exercise == "missing_command_rejected":
        try:
            run_command_singleflight([], state_root=state, cwd=cwd)
        except ValueError as exc:
            return {"ok": True, "error": str(exc)}
        return {"ok": False, "error": "missing command was accepted"}
    raise ValueError(f"unknown fixture exercise: {exercise}")


def evaluate_fixture_dir(input_dir: Path) -> dict[str, Any]:
    cases = _load_cases(input_dir)
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_") as tmp:
        scratch = Path(tmp)
        for path, case in cases:
            expected_ok = bool(case.get("expected_ok"))
            observed = _case_status(case, scratch=scratch)
            observed_ok = bool(observed.get("ok"))
            results.append(
                {
                    "case_id": case.get("case_id") or path.stem,
                    "path": str(path),
                    "expected_ok": expected_ok,
                    "observed_ok": observed_ok,
                    "expectation_met": expected_ok == observed_ok,
                    "observed": observed,
                }
            )
    passed = sum(1 for row in results if row["expectation_met"])
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "status": "pass" if passed == len(results) else "fail",
        "case_count": len(results),
        "passed_case_count": passed,
        "cases": results,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Engine Room command-run singleflight capsule.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run one command through singleflight.")
    run.add_argument("--state-root", required=True)
    run.add_argument("--cwd", default=".")
    run.add_argument("--resource-class", default="command")
    run.add_argument("--owner-surface", default=ORGAN_ID)
    run.add_argument("--scope-path", action="append", default=[])
    run.add_argument("--reuse-completed", action="store_true")
    run.add_argument("--json", action="store_true")
    run.add_argument("run_command", nargs=argparse.REMAINDER)

    fixtures = subparsers.add_parser("evaluate-fixtures", help="Evaluate public fixture cases.")
    fixtures.add_argument("--input", required=True)
    fixtures.add_argument("--json", action="store_true")
    return parser


def _strip_remainder(parts: Sequence[str]) -> list[str]:
    values = list(parts)
    if values and values[0] == "--":
        return values[1:]
    return values


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "run":
        command = _strip_remainder(args.run_command)
        try:
            receipt = run_command_singleflight(
                command,
                state_root=Path(args.state_root),
                cwd=Path(args.cwd),
                resource_class=str(args.resource_class),
                owner_surface=str(args.owner_surface),
                scope_paths=list(args.scope_path or []),
                reuse_completed=bool(args.reuse_completed),
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(receipt.to_dict(), indent=2, sort_keys=True))
        else:
            if receipt.stdout:
                print(receipt.stdout, end="")
            if receipt.stderr:
                print(receipt.stderr, end="", file=sys.stderr)
        return int(receipt.exit_code)
    if args.command == "evaluate-fixtures":
        payload = evaluate_fixture_dir(Path(args.input))
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"{payload['organ_id']}: {payload['status']}")
        return 0 if payload["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
