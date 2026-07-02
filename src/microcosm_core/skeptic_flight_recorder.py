"""
Implements skeptic flight recorder for the public Plectis package.

Callers enter through `CommandSpec`, `RunnerResult`, `utc_now`, `default_out_dir`,
`sha256_bytes`, `sha256_file`, and 12 more; constants such as `SCHEMA_VERSION`,
`CARD_SCHEMA_VERSION`, `VERIFICATION_SCHEMA_VERSION`, `PACKET_FILENAME`, and 13 more pin
local fixture names; dependencies include `argparse`, `hashlib`, `json`, `os`, and 9 more.
Importing it does not authorize release work or hidden private-state access; those effects
live behind explicit calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "microcosm_skeptic_flight_recorder_packet_v2"
CARD_SCHEMA_VERSION = "microcosm_skeptic_flight_recorder_card_v1"
VERIFICATION_SCHEMA_VERSION = "microcosm_skeptic_flight_recorder_verification_v1"
PACKET_FILENAME = "flight-recorder-packet.json"
CARD_FILENAME = "flight-recorder-card.md"
VERIFICATION_FILENAME = "flight-recorder-verification.json"
DEFAULT_OUT_ROOT = Path(".microcosm/skeptic-flight-recorder")
FORBIDDEN_OUTPUT_NEEDLES = (
    ("home_directory_absolute_path", "/Users/"),
    ("home_directory_absolute_path_linux", "/home/"),
    ("macro_repo_path", "src/ai_workflow"),
)
PROVIDER_ENV_MARKERS = (
    "OPENAI",
    "ANTHROPIC",
    "GEMINI",
    "GOOGLE_API",
    "AZURE_OPENAI",
    "COHERE",
    "MISTRAL",
    "TOGETHER",
    "REPLICATE",
    "HF_TOKEN",
    "HUGGINGFACE",
    "LANGCHAIN",
    "API_KEY",
    "ACCESS_TOKEN",
    "AUTH_TOKEN",
    "SECRET",
)
SOURCE_SNAPSHOT_SKIP_DIRS = {
    ".git",
    ".microcosm",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
SOURCE_SNAPSHOT_SKIP_SUFFIXES = {
    ".egg-info",
}
SELECTED_JSON_KEYS = (
    "schema_version",
    "status",
    "card_status",
    "command",
    "full_command",
    "endpoint",
    "full_endpoint",
    "project_ref",
    "release_authorized",
    "provider_calls_authorized",
    "source_mutation_authorized",
    "unsafe_payload_bodies_exported",
    "body_in_receipt",
    "source_open_body_policy",
    "authority_ceiling",
    "authority_summary",
    "safe_to_show",
    "state_write_proof",
    "evidence_class_counts",
    "surface_counts",
    "cache_status",
    "cache_freshness",
    "payload_boundary",
    "output_economy",
    "source_body_material_count_scope",
    "result_ref",
    "trace_ref",
    "event_count",
    "evidence_ref_count",
    "private_path_hit_count",
    "source_files_mutated",
    "found",
    "goal",
    "scenarios",
    "source_body_leaks",
    "contract_completeness_pct",
    "degraded",
)
FIRST_ACTION_PROOF_SCHEMA_VERSION = "microcosm_flight_recorder_first_action_proof_v1"
FIRST_ACTION_HERO_GOAL = "How do I evaluate the finance forecasting system?"
FIRST_ACTION_CLONE_GOAL = "where do I start with this clone?"
FIRST_ACTION_COLD_RUNNABLE_PREFIX = "PYTHONPATH=src python3 -m microcosm_core"
FIRST_ACTION_COMMAND_OUTPUTS = {
    "first_action_contract": "smoke/first-action.json",
    "first_action_hero": "commands/first-action-hero.json",
    "first_action_assay": "commands/first-action-assay.json",
}


@dataclass(frozen=True)
class CommandSpec:
    """
    Record object for Command Spec.

    It keeps `command_id`, `display_argv`, `actual_argv`, `stdout_relpath`,
    `stderr_relpath`, and `timeout_seconds` together for the skeptic flight recorder flow.
    """

    command_id: str
    display_argv: list[str]
    actual_argv: list[str]
    stdout_relpath: str
    stderr_relpath: str
    timeout_seconds: int = 60


@dataclass(frozen=True)
class RunnerResult:
    """
    Record object for Runner Result.

    It keeps `returncode`, `stdout`, `stderr`, and `duration_seconds` together for the
    skeptic flight recorder flow.
    """

    returncode: int
    stdout: bytes
    stderr: bytes
    duration_seconds: float


Runner = Callable[[CommandSpec, Path, dict[str, str]], RunnerResult]
SourceSnapshotter = Callable[[Path], dict[str, str]]


def utc_now() -> str:
    """
    Return utc now for the skeptic flight recorder flow.

    Notable helpers are `isoformat`, `replace`, and `now`.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_out_dir(now: str | None = None) -> Path:
    """
    Return default out dir for the skeptic flight recorder flow.

    Inputs are `now`; notable helpers are `replace` and `utc_now`.
    """
    stamp = (now or utc_now()).replace(":", "").replace("+00:00", "Z")
    return DEFAULT_OUT_ROOT / stamp


def sha256_bytes(data: bytes) -> str:
    """
    Return the stable digest computed by
    `microcosm_core.skeptic_flight_recorder.sha256_bytes`.

    The input is `data`; the body uses deterministic JSON encoding or chunked file reads
    before formatting the hash.
    """
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """
    Return the stable digest computed by
    `microcosm_core.skeptic_flight_recorder.sha256_file`.

    The input is `path`; the body uses deterministic JSON encoding or chunked file reads
    before formatting the hash.
    """
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_text(path: Path, text: str) -> None:
    """
    Write write text for the skeptic flight recorder flow.

    The side effect is the explicit file, receipt, parser, print, or instance-state update
    performed in this function.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """
    Write write JSON for the skeptic flight recorder flow.

    The side effect is the explicit file, receipt, parser, print, or instance-state update
    performed in this function.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _relative_display(path: Path, root: Path) -> str:
    """
    Produce the relative display value used by `microcosm_core.skeptic_flight_recorder`.

    Inputs are `path` and `root`; notable helpers are `as_posix` and `relative_to`.
    """
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _private_needles(root: Path) -> list[tuple[str, str]]:
    """
    Produce the private needles value used by `microcosm_core.skeptic_flight_recorder`.

    Inputs are `root`; notable helpers are `as_posix`, `append`, and `resolve`.
    """
    needles = list(FORBIDDEN_OUTPUT_NEEDLES)
    root_ref = root.resolve(strict=False).as_posix()
    if root_ref:
        needles.append(("package_root_absolute_path", root_ref))
    return needles


def _safe_path_ref(path: Path, root: Path) -> str:
    """
    Return safe path ref for the skeptic flight recorder flow.

    Inputs are `path` and `root`; notable helpers are `_relative_display` and
    `_private_needles`.
    """
    ref = _relative_display(path, root)
    if any(needle and needle in ref for _, needle in _private_needles(root)):
        return f"<private-path:{path.name}>"
    return ref


def _private_needle_classes_in_text(text: str, root: Path) -> list[str]:
    """
    Produce the private needle classes in text value used by
    `microcosm_core.skeptic_flight_recorder`.

    Inputs are `text` and `root`; notable helpers are `_private_needles`.
    """
    return [
        needle_class
        for needle_class, needle in _private_needles(root)
        if needle and needle in text
    ]


def _resolve_packet_ref(value: str, *, root: Path, packet_dir: Path) -> Path:
    """
    Return resolve packet ref for the skeptic flight recorder flow.

    Inputs are `value`, `root`, and `packet_dir`; notable helpers are `expanduser`,
    `is_absolute`, `exists`, and `Path`.
    """
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    root_candidate = root / candidate
    if root_candidate.exists():
        return root_candidate
    packet_candidate = packet_dir / candidate
    if packet_candidate.exists():
        return packet_candidate
    return root_candidate


def _command_display(command: Iterable[str]) -> str:
    """
    Return command display for the skeptic flight recorder flow.

    Inputs are `command`; notable helpers are `join`.
    """
    return " ".join(command)


def _public_subprocess_argv(argv: list[str], root: Path) -> list[str]:
    """
    Produce the public subprocess argv value used by
    `microcosm_core.skeptic_flight_recorder`.

    Inputs are `argv` and `root`; notable helpers are `resolve`, `expanduser`,
    `is_absolute`, `append`, and 4 more.
    """
    public: list[str] = []
    root_resolved = root.resolve(strict=False)
    for value in argv:
        path = Path(value).expanduser()
        if path.is_absolute():
            try:
                public.append(path.resolve(strict=False).relative_to(root_resolved).as_posix())
                continue
            except ValueError:
                if path.name.startswith("python") or path.name == "repo-python":
                    public.append(f"<{path.name}>")
                    continue
        public.append(value)
    return public


def create_disposable_project(project_dir: Path) -> None:
    """
    Create create disposable project for the skeptic flight recorder flow.

    The side effect is the explicit file, receipt, parser, print, or instance-state update
    performed in this function.
    """
    if project_dir.exists():
        shutil.rmtree(project_dir)
    (project_dir / "src/app").mkdir(parents=True)
    (project_dir / "tests").mkdir()
    _write_text(project_dir / "README.md", "# Skeptic Flight Recorder Probe\n")
    _write_text(
        project_dir / "pyproject.toml",
        '[project]\nname = "skeptic-flight-probe"\nversion = "0.1.0"\n',
    )
    _write_text(project_dir / "src/app/__init__.py", "VALUE = 1\n")
    _write_text(
        project_dir / "tests/test_app.py",
        "from app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
    )


def provider_env_key(key: str) -> bool:
    """
    Return whether provider env key holds for the skeptic flight recorder flow.

    The result is derived from `key` with `upper`; failing evidence is returned or raised
    exactly where the body says so.
    """
    upper = key.upper()
    return any(marker in upper for marker in PROVIDER_ENV_MARKERS)


def subprocess_env(root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    """
    Compute subprocess env from `root`.

    Inputs are `root`; notable helpers are `pop`, `get`, and `provider_env_key`.
    """
    env = dict(os.environ)
    removed = sorted(key for key in env if provider_env_key(key))
    for key in removed:
        env.pop(key, None)
    src = str(root / "src")
    env["PYTHONPATH"] = src if not env.get("PYTHONPATH") else f"{src}{os.pathsep}{env['PYTHONPATH']}"
    env["MICROCOSM_RUNTIME_RECEIPT_WRITES"] = "0"
    env["MICROCOSM_RECEIPT_WRITES"] = "0"
    env["NO_COLOR"] = "1"
    return env, {
        "provider_calls_authorized": False,
        "provider_credential_env_removed_count": len(removed),
        "provider_credential_env_keys_available_to_subprocess": False,
        "removed_env_key_names": removed,
    }


def _iter_source_snapshot_paths(root: Path) -> list[Path]:
    """
    Return iter source snapshot paths for the skeptic flight recorder flow.

    Inputs are `root`; notable helpers are `_git_tracked_paths`, `walk`, `Path`, `append`,
    and 1 more.
    """
    git_paths = _git_tracked_paths(root)
    if git_paths:
        return git_paths

    paths: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [
            name
            for name in dirnames
            if name not in SOURCE_SNAPSHOT_SKIP_DIRS
            and not any(name.endswith(suffix) for suffix in SOURCE_SNAPSHOT_SKIP_SUFFIXES)
        ]
        for filename in filenames:
            path = current / filename
            if path.name == ".DS_Store" or path.suffix in {".pyc", ".pyo"}:
                continue
            paths.append(path)
    return sorted(paths)


def _git_tracked_paths(root: Path) -> list[Path]:
    """
    Derive git tracked paths without touching module import state.

    Inputs are `root`; notable helpers are `Path`, `split`, `run`, `strip`, and 6 more.
    """
    try:
        git_root_result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if git_root_result.returncode != 0:
        return []
    git_root = Path(git_root_result.stdout.strip())
    try:
        rel_root = root.resolve(strict=False).relative_to(git_root.resolve(strict=False))
    except ValueError:
        return []
    try:
        ls_result = subprocess.run(
            ["git", "-C", str(git_root), "ls-files", "-z", "--", rel_root.as_posix()],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if ls_result.returncode != 0 or not ls_result.stdout:
        return []
    paths: list[Path] = []
    for raw in ls_result.stdout.split(b"\0"):
        if not raw:
            continue
        path = git_root / raw.decode("utf-8", errors="replace")
        if path.is_file():
            paths.append(path)
    return sorted(paths)


def source_snapshot(root: Path) -> dict[str, str]:
    """
    Derive source snapshot without touching module import state.

    Inputs are `root`; notable helpers are `_iter_source_snapshot_paths`, `sha256_file`, and
    `_relative_display`.
    """
    snapshot: dict[str, str] = {}
    for path in _iter_source_snapshot_paths(root):
        try:
            digest = sha256_file(path)
        except OSError:
            continue
        snapshot[_relative_display(path, root)] = digest
    return snapshot


def source_mutation_check(before: dict[str, str], after: dict[str, str]) -> dict[str, Any]:
    """
    Serialize `microcosm_core.skeptic_flight_recorder.source_mutation_check` into the
    payload shape expected by skeptic flight recorder.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    before_keys = set(before)
    after_keys = set(after)
    changed = sorted(key for key in before_keys & after_keys if before[key] != after[key])
    added = sorted(after_keys - before_keys)
    removed = sorted(before_keys - after_keys)
    return {
        "status": "pass" if not changed and not added and not removed else "blocked",
        "source_files_mutated": bool(changed or added or removed),
        "tracked_file_count_before": len(before),
        "tracked_file_count_after": len(after),
        "changed_count": len(changed),
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_paths": changed[:20],
        "added_paths": added[:20],
        "removed_paths": removed[:20],
        "truncated": len(changed) > 20 or len(added) > 20 or len(removed) > 20,
    }


def command_plan(root: Path, out_dir: Path, python_executable: str) -> list[CommandSpec]:
    """
    Compute command plan from `root`, `out_dir`, and `python_executable`.

    Inputs are `root`, `out_dir`, and `python_executable`; notable helpers are
    `_relative_display`, `CommandSpec`, `py_module`, and `script`.
    """
    project_ref = _relative_display(out_dir / "work/project", root)
    smoke_ref = _relative_display(out_dir / "smoke", root)
    served_status_ref = f"{smoke_ref}/served-status-card.json"
    proof_out_ref = _relative_display(out_dir / "proof-lab", root)

    def py_module(*args: str) -> list[str]:
        """
        Compute py module from `args`.

        Inputs are `args`.
        """
        return [python_executable, "-m", "microcosm_core", *args]

    def script(script_ref: str, *args: str) -> list[str]:
        """
        Return script for the skeptic flight recorder flow.

        Inputs are `script_ref` and `args`.
        """
        return [python_executable, script_ref, *args]

    return [
        CommandSpec(
            "hello",
            ["plectis", "hello", project_ref],
            py_module("hello", project_ref),
            "smoke/hello.txt",
            "commands/hello.stderr.txt",
        ),
        CommandSpec(
            "first_screen_card",
            ["plectis", "first-screen", "--card", project_ref],
            py_module("first-screen", "--card", project_ref),
            "smoke/first-screen-card.json",
            "commands/first-screen-card.stderr.txt",
        ),
        CommandSpec(
            "tour_card",
            ["plectis", "tour", "--card", project_ref],
            py_module("tour", "--card", project_ref),
            "smoke/tour-card.json",
            "commands/tour-card.stderr.txt",
        ),
        CommandSpec(
            "status_card",
            ["plectis", "status", "--card", project_ref],
            py_module("status", "--card", project_ref),
            "smoke/status-card.json",
            "commands/status-card.stderr.txt",
        ),
        CommandSpec(
            "served_status_smoke",
            [
                "python",
                "scripts/served_status_smoke.py",
                "--root",
                ".",
                "--project",
                project_ref,
                "--out",
                served_status_ref,
            ],
            script(
                "scripts/served_status_smoke.py",
                "--root",
                ".",
                "--project",
                project_ref,
                "--out",
                served_status_ref,
            ),
            "commands/served-status-smoke.stdout.txt",
            "commands/served-status-smoke.stderr.txt",
            timeout_seconds=90,
        ),
        CommandSpec(
            "authority_card",
            ["plectis", "authority", "--card"],
            py_module("authority", "--card"),
            "smoke/authority-card.json",
            "commands/authority-card.stderr.txt",
        ),
        CommandSpec(
            "workingness_card",
            ["plectis", "workingness", "--card"],
            py_module("workingness", "--card"),
            "smoke/workingness-card.json",
            "commands/workingness-card.stderr.txt",
        ),
        CommandSpec(
            "legibility_scorecard",
            ["plectis", "legibility-scorecard"],
            py_module("legibility-scorecard"),
            "smoke/legibility-scorecard.json",
            "commands/legibility-scorecard.stderr.txt",
        ),
        CommandSpec(
            "version",
            ["plectis", "--version"],
            py_module("--version"),
            "smoke/version.txt",
            "commands/version.stderr.txt",
        ),
        CommandSpec(
            "stripping_guard",
            ["plectis", "stripping-guard"],
            py_module("stripping-guard"),
            "smoke/stripping-guard.json",
            "commands/stripping-guard.stderr.txt",
        ),
        CommandSpec(
            "observe_card",
            ["plectis", "observe", "--card", project_ref],
            py_module("observe", "--card", project_ref),
            "commands/observe-card.json",
            "commands/observe-card.stderr.txt",
        ),
        CommandSpec(
            "proof_lab_card",
            ["plectis", "proof-lab", "--card", "--out", proof_out_ref],
            py_module("proof-lab", "--card", "--out", proof_out_ref),
            "commands/proof-lab-card.json",
            "commands/proof-lab-card.stderr.txt",
            timeout_seconds=120,
        ),
        CommandSpec(
            "run_card",
            ["plectis", "run", "--card", "examples/runtime_shell/demo_project"],
            py_module("run", "--card", "examples/runtime_shell/demo_project"),
            "commands/run-card.json",
            "commands/run-card.stderr.txt",
            timeout_seconds=120,
        ),
        CommandSpec(
            "first_action_contract",
            ["plectis", "comprehend", "--first-action", FIRST_ACTION_CLONE_GOAL],
            py_module("comprehend", "--first-action", FIRST_ACTION_CLONE_GOAL),
            FIRST_ACTION_COMMAND_OUTPUTS["first_action_contract"],
            "commands/first-action.stderr.txt",
        ),
        CommandSpec(
            "first_action_hero",
            ["plectis", "comprehend", "--first-action", FIRST_ACTION_HERO_GOAL],
            py_module("comprehend", "--first-action", FIRST_ACTION_HERO_GOAL),
            FIRST_ACTION_COMMAND_OUTPUTS["first_action_hero"],
            "commands/first-action-hero.stderr.txt",
        ),
        CommandSpec(
            "first_action_assay",
            ["plectis", "comprehension-assay", "--first-action"],
            py_module("comprehension-assay", "--first-action"),
            FIRST_ACTION_COMMAND_OUTPUTS["first_action_assay"],
            "commands/first-action-assay.stderr.txt",
            timeout_seconds=120,
        ),
        CommandSpec(
            "check_smoke_outputs",
            ["python", "scripts/check_smoke_outputs.py", "--smoke-out", smoke_ref],
            script("scripts/check_smoke_outputs.py", "--smoke-out", smoke_ref),
            "commands/check-smoke-outputs.stdout.txt",
            "commands/check-smoke-outputs.stderr.txt",
        ),
    ]


def default_runner(spec: CommandSpec, cwd: Path, env: dict[str, str]) -> RunnerResult:
    """
    Return default runner for the skeptic flight recorder flow.

    Inputs are `spec`, `cwd`, and `env`; notable helpers are `monotonic`, `run`,
    `RunnerResult`, `encode`, and 1 more.
    """
    start = time.monotonic()
    try:
        completed = subprocess.run(
            spec.actual_argv,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=spec.timeout_seconds,
            check=False,
        )
        return RunnerResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_seconds=round(time.monotonic() - start, 3),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, bytes) else b""
        stderr = exc.stderr if isinstance(exc.stderr, bytes) else b""
        stderr += f"\nTIMEOUT after {spec.timeout_seconds}s\n".encode()
        return RunnerResult(
            returncode=124,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=round(time.monotonic() - start, 3),
        )


def _parse_json_bytes(data: bytes) -> dict[str, Any] | None:
    """
    Parse parse JSON bytes for `microcosm_core.skeptic_flight_recorder`.

    Input comes from `data`; malformed or missing data follows the exceptions and checks
    visible in the body.
    """
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _selected_json_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Return selected JSON fields for the skeptic flight recorder flow.

    Inputs are `payload`.
    """
    return {key: payload[key] for key in SELECTED_JSON_KEYS if key in payload}


def _text_summary(data: bytes) -> dict[str, Any]:
    """
    Serialize `microcosm_core.skeptic_flight_recorder._text_summary` into the payload shape
    expected by skeptic flight recorder.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    text = data.decode("utf-8", errors="replace").strip()
    lines = text.splitlines()
    return {
        "line_count": len(lines),
        "first_line": lines[0] if lines else "",
        "nonempty": bool(text),
    }


def _execute_command(
    spec: CommandSpec,
    *,
    root: Path,
    out_dir: Path,
    env: dict[str, str],
    runner: Runner,
) -> dict[str, Any]:
    """
    Derive execute command without touching module import state.

    Inputs are `spec`, `root`, `out_dir`, `env`, and `runner`; notable helpers are `runner`,
    `mkdir`, `write_bytes`, `_parse_json_bytes`, and 9 more.
    """
    result = runner(spec, root, env)
    stdout_path = out_dir / spec.stdout_relpath
    stderr_path = out_dir / spec.stderr_relpath
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_bytes(result.stdout)
    stderr_path.write_bytes(result.stderr)

    parsed = _parse_json_bytes(result.stdout)
    record: dict[str, Any] = {
        "command_id": spec.command_id,
        "argv": spec.display_argv,
        "subprocess_argv_public": _public_subprocess_argv(spec.actual_argv, root),
        "subprocess_argv_sha256": sha256_bytes(
            "\0".join(spec.actual_argv).encode("utf-8")
        ),
        "display_command": _command_display(spec.display_argv),
        "return_code": result.returncode,
        "duration_seconds": result.duration_seconds,
        "stdout_path": _relative_display(stdout_path, root),
        "stderr_path": _relative_display(stderr_path, root),
        "stdout_sha256": sha256_bytes(result.stdout),
        "stderr_sha256": sha256_bytes(result.stderr),
        "stdout_bytes": len(result.stdout),
        "stderr_bytes": len(result.stderr),
        "json_detected": parsed is not None,
    }
    if parsed is None:
        record["selected_text_fields"] = _text_summary(result.stdout)
    else:
        record["selected_json_fields"] = _selected_json_fields(parsed)
        status = parsed.get("status")
        card_status = parsed.get("card_status")
        if isinstance(status, str):
            record["reported_status"] = status
        if isinstance(card_status, str):
            record["reported_card_status"] = card_status
    return record


def _scan_private_needles(paths: Iterable[Path], root: Path) -> dict[str, Any]:
    """
    Serialize `microcosm_core.skeptic_flight_recorder._scan_private_needles` into the
    payload shape expected by skeptic flight recorder.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    hits: list[dict[str, Any]] = []
    needle_classes = [
        "home_directory_absolute_path",
        "home_directory_absolute_path_linux",
        "macro_repo_path",
        "package_root_absolute_path",
    ]
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for needle_class, needle in _private_needles(root):
            if needle and needle in text:
                hits.append(
                    {
                        "path": _safe_path_ref(path, root),
                        "needle_class": needle_class,
                    }
                )
    return {
        "status": "pass" if not hits else "blocked",
        "private_path_hit_count": len(hits),
        "private_path_hits": hits[:20],
        "truncated": len(hits) > 20,
        "needle_classes": needle_classes,
    }


def _collect_output_paths(command_records: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    """
    Derive collect output paths without touching module import state.

    Inputs are `command_records` and `out_dir`; notable helpers are `get`, `Path`,
    `is_file`, `is_absolute`, and 1 more.
    """
    paths: list[Path] = []
    for record in command_records:
        for key in ("stdout_path", "stderr_path"):
            value = record.get(key)
            if isinstance(value, str):
                path = out_dir.parent / "__never__"
                candidate = Path(value)
                if not candidate.is_absolute():
                    candidate = out_dir.parents[0] / candidate
                path = candidate
                if path.is_file():
                    paths.append(path)
    return paths


def _command_status_summary(command_records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Serialize `microcosm_core.skeptic_flight_recorder._command_status_summary` into the
    payload shape expected by skeptic flight recorder.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    nonzero = [row["command_id"] for row in command_records if row["return_code"] != 0]
    blocked = [
        row["command_id"]
        for row in command_records
        if row.get("reported_status") == "blocked"
        or row.get("reported_card_status") == "blocked"
    ]
    return {
        "command_count": len(command_records),
        "nonzero_return_code_count": len(nonzero),
        "nonzero_return_code_command_ids": nonzero,
        "blocked_reported_status_count": len(blocked),
        "blocked_reported_status_command_ids": blocked,
        "all_commands_executed": len(command_records) > 0,
    }


def _merge_evidence_class_counts(command_records: list[dict[str, Any]]) -> dict[str, int]:
    """
    Produce the merge evidence class counts value used by
    `microcosm_core.skeptic_flight_recorder`.

    Inputs are `command_records`; notable helpers are `get` and `items`.
    """
    counts: dict[str, int] = {}
    for record in command_records:
        selected = record.get("selected_json_fields")
        if not isinstance(selected, dict):
            continue
        evidence_counts = selected.get("evidence_class_counts")
        if not isinstance(evidence_counts, dict):
            continue
        for key, value in evidence_counts.items():
            if isinstance(value, int) and not isinstance(value, bool):
                counts[str(key)] = counts.get(str(key), 0) + value
    return dict(sorted(counts.items()))


def _authority_false_keys(command_records: list[dict[str, Any]]) -> dict[str, list[str]]:
    """
    Derive authority false keys without touching module import state.

    Inputs are `command_records`; notable helpers are `get` and `items`.
    """
    rows: dict[str, list[str]] = {}
    for record in command_records:
        selected = record.get("selected_json_fields")
        if not isinstance(selected, dict):
            continue
        ceiling = selected.get("authority_ceiling")
        if not isinstance(ceiling, dict):
            continue
        false_keys = sorted(key for key, value in ceiling.items() if value is False)
        if false_keys:
            rows[str(record["command_id"])] = false_keys
    return rows


def first_action_contract_fields(payload: dict[str, Any] | None) -> dict[str, Any]:
    """
    Serialize `microcosm_core.skeptic_flight_recorder.first_action_contract_fields` into the
    payload shape expected by skeptic flight recorder.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    hero = payload if isinstance(payload, dict) else {}
    action = hero.get("first_action") if isinstance(hero.get("first_action"), dict) else {}
    proof_path = hero.get("proof_path") if isinstance(hero.get("proof_path"), dict) else {}
    boundary = (
        hero.get("reading_boundary")
        if isinstance(hero.get("reading_boundary"), dict)
        else {}
    )
    ceiling = (
        hero.get("authority_ceiling")
        if isinstance(hero.get("authority_ceiling"), dict)
        else {}
    )
    graph = hero.get("graph_backed") if isinstance(hero.get("graph_backed"), dict) else {}
    owner = hero.get("owner") if isinstance(hero.get("owner"), dict) else {}
    clean_run = action.get("clean_run") if isinstance(action.get("clean_run"), dict) else {}
    receipt_refs = proof_path.get("receipt_refs")
    command = str(action.get("command") or "")
    return {
        "goal": hero.get("goal"),
        "found": hero.get("found"),
        "owner": {
            key: owner.get(key)
            for key in ("organ_id", "display_name", "evidence_class", "task_class")
            if key in owner
        },
        "action_kind": action.get("action_kind"),
        "command": command or None,
        "writes_outputs_under": action.get("writes_outputs_under"),
        "clean_run_command": clean_run.get("command"),
        "validator_command": proof_path.get("validator_command")
        or proof_path.get("runnable_validator"),
        "authority_receipt": proof_path.get("authority_receipt"),
        "receipt_ref_count": len(receipt_refs) if isinstance(receipt_refs, list) else 0,
        "stop_condition": boundary.get("stop_condition"),
        "do_not_claim": hero.get("do_not_claim"),
        "authority_ceiling": ceiling or None,
        "graph_source": graph.get("source"),
        "graph_source_schema": graph.get("source_schema"),
    }


def first_action_contract_checks(
    payload: dict[str, Any] | None,
    return_code: int | None,
) -> dict[str, bool]:
    """
    Serialize `microcosm_core.skeptic_flight_recorder.first_action_contract_checks` into the
    payload shape expected by skeptic flight recorder.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    hero = payload if isinstance(payload, dict) else {}
    action = hero.get("first_action") if isinstance(hero.get("first_action"), dict) else {}
    proof_path = hero.get("proof_path") if isinstance(hero.get("proof_path"), dict) else {}
    boundary = (
        hero.get("reading_boundary")
        if isinstance(hero.get("reading_boundary"), dict)
        else {}
    )
    ceiling = (
        hero.get("authority_ceiling")
        if isinstance(hero.get("authority_ceiling"), dict)
        else {}
    )
    command = str(action.get("command") or "")
    return {
        "command_exit_zero": return_code == 0,
        "goal_resolved": hero.get("found") is True,
        "command_cold_runnable": command.startswith(FIRST_ACTION_COLD_RUNNABLE_PREFIX),
        "command_placeholder_free": bool(command) and "<" not in command,
        "proof_path_present": bool(
            proof_path.get("runnable_validator") or proof_path.get("validation_commands")
        ),
        "stop_condition_present": bool(
            str(
                boundary.get("stop_condition") or boundary.get("fallback_guidance") or ""
            ).strip()
        ),
        "claim_ceiling_present": bool(str(hero.get("do_not_claim") or "").strip()),
        "authority_ceiling_all_false": bool(ceiling)
        and all(value is False for value in ceiling.values()),
    }


def _derive_first_action_proof(
    *,
    hero_payload: dict[str, Any] | None,
    hero_return_code: int | None,
    contract_payload: dict[str, Any] | None,
    contract_return_code: int | None,
    assay_payload: dict[str, Any] | None,
    assay_return_code: int | None,
) -> dict[str, Any]:
    """
    Serialize `microcosm_core.skeptic_flight_recorder._derive_first_action_proof` into the
    payload shape expected by skeptic flight recorder.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    contract = contract_payload if isinstance(contract_payload, dict) else {}
    assay = assay_payload if isinstance(assay_payload, dict) else {}
    fields = first_action_contract_fields(hero_payload)
    hero_checks = first_action_contract_checks(hero_payload, hero_return_code)

    checks = {
        "hero_command_exit_zero": hero_checks["command_exit_zero"],
        "clone_entry_command_exit_zero": contract_return_code == 0,
        "assay_exit_zero": assay_return_code == 0,
        "hero_goal_resolved": hero_checks["goal_resolved"],
        "clone_entry_goal_resolved": contract.get("found") is True,
        "command_cold_runnable": hero_checks["command_cold_runnable"],
        "command_placeholder_free": hero_checks["command_placeholder_free"],
        "proof_path_present": hero_checks["proof_path_present"],
        "stop_condition_present": hero_checks["stop_condition_present"],
        "claim_ceiling_present": hero_checks["claim_ceiling_present"],
        "authority_ceiling_all_false": hero_checks["authority_ceiling_all_false"],
        "assay_source_body_leak_free": assay.get("source_body_leaks") == 0,
        "assay_not_degraded": assay.get("degraded") is not True,
    }
    return {
        "schema_version": FIRST_ACTION_PROOF_SCHEMA_VERSION,
        "status": "pass" if all(checks.values()) else "blocked",
        "hero_goal": fields["goal"],
        "clone_entry_goal": contract.get("goal"),
        "owner": fields["owner"],
        "action_kind": fields["action_kind"],
        "command": fields["command"],
        "writes_outputs_under": fields["writes_outputs_under"],
        "clean_run_command": fields["clean_run_command"],
        "validator_command": fields["validator_command"],
        "authority_receipt": fields["authority_receipt"],
        "receipt_ref_count": fields["receipt_ref_count"],
        "stop_condition": fields["stop_condition"],
        "do_not_claim": fields["do_not_claim"],
        "authority_ceiling": fields["authority_ceiling"],
        "graph_source": fields["graph_source"],
        "graph_source_schema": fields["graph_source_schema"],
        "assay": {
            "return_code": assay_return_code,
            "scenarios": assay.get("scenarios"),
            "source_body_leaks": assay.get("source_body_leaks"),
            "contract_completeness_pct": assay.get("contract_completeness_pct"),
            "degraded": assay.get("degraded"),
        },
        "checks": checks,
        "failed_checks": sorted(key for key, value in checks.items() if not value),
        "proof_boundary": (
            "routes and proves the first-action encounter only; not release "
            "authorization, domain correctness, or whole-system correctness"
        ),
    }


def _first_action_proof_from_disk(
    command_records: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    """
    Return first action proof from disk for the skeptic flight recorder flow.

    Inputs are `command_records` and `out_dir`; notable helpers are
    `_derive_first_action_proof`, `get`, `_parse_json_bytes`, `read_bytes`, and 2 more.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for record in command_records:
        if isinstance(record, dict) and isinstance(record.get("command_id"), str):
            by_id[record["command_id"]] = record

    def return_code(command_id: str) -> int | None:
        """
        Derive return code without touching module import state.

        Inputs are `command_id`; notable helpers are `get`.
        """
        record = by_id.get(command_id)
        value = record.get("return_code") if isinstance(record, dict) else None
        return value if isinstance(value, int) else None

    def payload(command_id: str) -> dict[str, Any] | None:
        """
        Compute payload from `command_id`.

        Inputs are `command_id`; notable helpers are `_parse_json_bytes` and `read_bytes`.
        """
        path = out_dir / FIRST_ACTION_COMMAND_OUTPUTS[command_id]
        try:
            data = path.read_bytes()
        except OSError:
            return None
        return _parse_json_bytes(data)

    return _derive_first_action_proof(
        hero_payload=payload("first_action_hero"),
        hero_return_code=return_code("first_action_hero"),
        contract_payload=payload("first_action_contract"),
        contract_return_code=return_code("first_action_contract"),
        assay_payload=payload("first_action_assay"),
        assay_return_code=return_code("first_action_assay"),
    )


def _human_card(packet: dict[str, Any]) -> str:
    """
    Compute human card from `packet`.

    Inputs are `packet`; notable helpers are `get`, `append`, and `join`.
    """
    verdict = packet["evaluator_verdict"]
    integrity = packet["recorder_integrity"]
    lines = [
        "# Microcosm Skeptic Flight Recorder",
        "",
        f"- Packet status: `{packet['status']}`",
        f"- Evaluator verdict: `{verdict['status']}`",
        f"- Commands run: `{verdict['command_status_summary']['command_count']}`",
        (
            "- Non-zero command receipts: "
            f"`{verdict['command_status_summary']['nonzero_return_code_count']}`"
        ),
        (
            "- Blocked reported statuses preserved: "
            f"`{verdict['command_status_summary']['blocked_reported_status_count']}`"
        ),
        f"- Source files mutated: `{integrity['source_mutation_check']['source_files_mutated']}`",
        f"- Private path hits: `{integrity['private_path_scan']['private_path_hit_count']}`",
        (
            "- Provider credential env available to subprocesses: "
            f"`{integrity['provider_env_policy']['provider_credential_env_keys_available_to_subprocess']}`"
        ),
    ]
    proof = packet.get("first_action_proof")
    if isinstance(proof, dict):
        owner = proof.get("owner") if isinstance(proof.get("owner"), dict) else {}
        assay = proof.get("assay") if isinstance(proof.get("assay"), dict) else {}
        failed = proof.get("failed_checks") or []
        lines += [
            "",
            "## First Action Proof",
            "",
            f"- Status: `{proof.get('status')}`",
            f"- Hero goal: `{proof.get('hero_goal')}`",
            f"- Owner: `{owner.get('organ_id')}` ({owner.get('display_name')})",
            f"- Command: `{proof.get('command')}`",
            f"- Validator: `{proof.get('validator_command')}`",
            f"- Stop condition: {proof.get('stop_condition')}",
            f"- Do not claim: {proof.get('do_not_claim')}",
            (
                f"- Assay: `{assay.get('scenarios')}` scenarios, "
                f"`{assay.get('source_body_leaks')}` source-body leaks, "
                f"contract completeness `{assay.get('contract_completeness_pct')}`"
            ),
            (
                "- Failed checks: " + ", ".join(f"`{name}`" for name in failed)
                if failed
                else "- Failed checks: none"
            ),
            f"- Boundary: {proof.get('proof_boundary')}",
        ]
    lines += [
        "",
        "## Drilldowns",
        "",
        f"- Machine packet: `{packet['packet_ref']}`",
        f"- Command outputs: `{packet['command_output_dir_ref']}`",
        f"- Disposable project: `{packet['disposable_project_ref']}`",
        "",
        "## Refused Claims",
        "",
    ]
    refused = verdict["refused_claims"]
    if not refused:
        lines.append("- No blocked command status was observed.")
    else:
        for row in refused:
            lines.append(f"- `{row['command_id']}`: {row['reason']}")
    lines.append("")
    return "\n".join(lines)


def _packet_payload_sha256(packet: dict[str, Any]) -> str:
    """
    Return a stable SHA-256 digest for `packet`.

    The body uses deterministic encoding or chunked file reads so receipts can compare the
    value across runs.
    """
    payload = dict(packet)
    payload.pop("packet_payload_sha256", None)
    return sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))


def _check_row(check_id: str, status: str, **fields: Any) -> dict[str, Any]:
    """
    Check whether check row holds for the skeptic flight recorder flow.

    The result is derived from `check_id`, `status`, and `fields` with `update`; failing
    evidence is returned or raised exactly where the body says so.
    """
    row: dict[str, Any] = {"check_id": check_id, "status": status}
    row.update(fields)
    return row


def _receipt_status(statuses: set[str]) -> str:
    """
    Derive receipt status without touching module import state.

    Inputs are `statuses`.
    """
    if not statuses:
        return "packet_valid"
    for status in (
        "private_path_leak",
        "source_mutation_seen",
        "digest_mismatch",
        "packet_stale",
        "concurrent_churn_possible",
    ):
        if status in statuses:
            return status
    return sorted(statuses)[0]


def _load_packet(packet_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """
    Load load packet for `microcosm_core.skeptic_flight_recorder`.

    Input comes from `packet_path`; malformed or missing data follows the exceptions and
    checks visible in the body.
    """
    try:
        payload = json.loads(packet_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, f"packet_read_error:{exc.__class__.__name__}"
    except json.JSONDecodeError:
        return None, "packet_json_decode_error"
    if not isinstance(payload, dict):
        return None, "packet_json_not_object"
    return payload, None


def _command_receipt_checks(
    commands: Any,
    *,
    root: Path,
    packet_dir: Path,
) -> tuple[list[dict[str, Any]], list[Path], set[str], dict[str, Any]]:
    """
    Produce the command receipt checks value used by
    `microcosm_core.skeptic_flight_recorder`.

    Inputs are `commands`, `root`, and `packet_dir`; notable helpers are `add`, `append`,
    `_check_row`, `get`, and 6 more.
    """
    checks: list[dict[str, Any]] = []
    raw_paths: list[Path] = []
    statuses: set[str] = set()
    digest_mismatches: list[dict[str, Any]] = []
    missing_outputs: list[dict[str, Any]] = []
    private_argv_hits: list[dict[str, Any]] = []
    command_count = 0

    if not isinstance(commands, list):
        statuses.add("packet_stale")
        checks.append(
            _check_row(
                "command_receipts_shape",
                "blocked",
                reason="packet.commands is not a list",
            )
        )
        return checks, raw_paths, statuses, {
            "command_count": 0,
            "raw_output_count": 0,
            "missing_output_count": 0,
            "digest_mismatch_count": 0,
            "private_argv_hit_count": 0,
            "digest_mismatches": [],
            "missing_outputs": [],
            "private_argv_hits": [],
        }

    for index, record in enumerate(commands):
        if not isinstance(record, dict):
            statuses.add("packet_stale")
            checks.append(
                _check_row(
                    "command_receipt_shape",
                    "blocked",
                    command_index=index,
                    reason="command receipt is not an object",
                )
            )
            continue
        command_count += 1
        command_id = str(record.get("command_id") or f"command_{index}")
        missing_fields = [
            key
            for key in (
                "argv",
                "subprocess_argv_public",
                "subprocess_argv_sha256",
                "return_code",
                "stdout_path",
                "stdout_sha256",
                "stderr_path",
                "stderr_sha256",
            )
            if key not in record
        ]
        if missing_fields:
            statuses.add("packet_stale")
            checks.append(
                _check_row(
                    "command_receipt_required_fields",
                    "blocked",
                    command_id=command_id,
                    missing_fields=missing_fields,
                )
            )
        if "actual_argv" in record:
            statuses.add("private_path_leak")
            private_argv_hits.append(
                {
                    "command_id": command_id,
                    "field": "actual_argv",
                    "reason": "private subprocess argv must not be serialized",
                }
            )
        for field in ("argv", "subprocess_argv_public"):
            value = record.get(field)
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                statuses.add("packet_stale")
                checks.append(
                    _check_row(
                        "command_public_argv_shape",
                        "blocked",
                        command_id=command_id,
                        field=field,
                    )
                )
                continue
            hit_classes = _private_needle_classes_in_text(
                "\n".join(value),
                root,
            )
            if hit_classes:
                statuses.add("private_path_leak")
                private_argv_hits.append(
                    {
                        "command_id": command_id,
                        "field": field,
                        "needle_classes": sorted(set(hit_classes)),
                    }
                )

        for stream in ("stdout", "stderr"):
            path_value = record.get(f"{stream}_path")
            digest_value = record.get(f"{stream}_sha256")
            if not isinstance(path_value, str) or not isinstance(digest_value, str):
                statuses.add("packet_stale")
                missing_outputs.append(
                    {
                        "command_id": command_id,
                        "stream": stream,
                        "reason": "missing_path_or_digest_field",
                    }
                )
                continue
            output_path = _resolve_packet_ref(path_value, root=root, packet_dir=packet_dir)
            if not output_path.is_file():
                statuses.add("packet_stale")
                missing_outputs.append(
                    {
                        "command_id": command_id,
                        "stream": stream,
                        "path": _safe_path_ref(output_path, root),
                        "reason": "referenced_output_missing",
                    }
                )
                continue
            raw_paths.append(output_path)
            actual_digest = sha256_file(output_path)
            if actual_digest != digest_value:
                statuses.add("digest_mismatch")
                digest_mismatches.append(
                    {
                        "command_id": command_id,
                        "stream": stream,
                        "path": _safe_path_ref(output_path, root),
                        "expected_sha256": digest_value,
                        "actual_sha256": actual_digest,
                    }
                )

    if digest_mismatches:
        checks.append(
            _check_row(
                "command_output_sha256",
                "blocked",
                digest_mismatch_count=len(digest_mismatches),
            )
        )
    else:
        checks.append(
            _check_row(
                "command_output_sha256",
                "pass",
                raw_output_count=len(raw_paths),
            )
        )
    if missing_outputs:
        checks.append(
            _check_row(
                "command_output_refs",
                "blocked",
                missing_output_count=len(missing_outputs),
            )
        )
    else:
        checks.append(_check_row("command_output_refs", "pass"))
    if private_argv_hits:
        checks.append(
            _check_row(
                "command_public_argv",
                "blocked",
                private_argv_hit_count=len(private_argv_hits),
            )
        )
    else:
        checks.append(_check_row("command_public_argv", "pass"))

    return checks, raw_paths, statuses, {
        "command_count": command_count,
        "raw_output_count": len(raw_paths),
        "missing_output_count": len(missing_outputs),
        "digest_mismatch_count": len(digest_mismatches),
        "private_argv_hit_count": len(private_argv_hits),
        "digest_mismatches": digest_mismatches[:20],
        "missing_outputs": missing_outputs[:20],
        "private_argv_hits": private_argv_hits[:20],
        "truncated": (
            len(digest_mismatches) > 20
            or len(missing_outputs) > 20
            or len(private_argv_hits) > 20
        ),
    }


def _authority_ceiling_check(packet: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
    """
    Derive authority ceiling check without touching module import state.

    Inputs are `packet`; notable helpers are `get`, `_authority_false_keys`, `add`,
    `_check_row`, and 1 more.
    """
    statuses: set[str] = set()
    commands = packet.get("commands")
    if not isinstance(commands, list):
        statuses.add("packet_stale")
        return (
            _check_row(
                "authority_ceiling_preserved",
                "blocked",
                reason="packet.commands is not a list",
            ),
            statuses,
        )

    policy = packet.get("authority_and_omission_policy")
    policy_ok = isinstance(policy, dict) and all(
        policy.get(key) is False
        for key in (
            "provider_calls_authorized",
            "source_mutation_authorized",
            "release_authorized",
        )
    )
    selected_fields_only = isinstance(policy, dict) and (
        policy.get("selected_fields_only_in_packet") is True
    )
    ceiling_rows = _authority_false_keys(commands)
    safe_to_show_false_rows: dict[str, list[str]] = {}
    for record in commands:
        if not isinstance(record, dict):
            continue
        selected = record.get("selected_json_fields")
        if not isinstance(selected, dict):
            continue
        safe_to_show = selected.get("safe_to_show")
        if isinstance(safe_to_show, dict):
            false_keys = sorted(key for key, value in safe_to_show.items() if value is False)
            if false_keys:
                safe_to_show_false_rows[str(record.get("command_id", "unknown"))] = false_keys

    verdict = packet.get("evaluator_verdict")
    command_summary = verdict.get("command_status_summary") if isinstance(verdict, dict) else None
    preserved_refusals = True
    if isinstance(command_summary, dict):
        blocked_count = command_summary.get("blocked_reported_status_count", 0)
        nonzero_count = command_summary.get("nonzero_return_code_count", 0)
        if (blocked_count or nonzero_count) and isinstance(verdict, dict):
            preserved_refusals = (
                verdict.get("status") == "mixed_claims_preserved"
                and isinstance(verdict.get("refused_claims"), list)
                and len(verdict.get("refused_claims", [])) > 0
            )

    if not (policy_ok and selected_fields_only and (ceiling_rows or safe_to_show_false_rows) and preserved_refusals):
        statuses.add("packet_stale")
        return (
            _check_row(
                "authority_ceiling_preserved",
                "blocked",
                policy_ok=policy_ok,
                selected_fields_only=selected_fields_only,
                authority_ceiling_command_count=len(ceiling_rows),
                safe_to_show_command_count=len(safe_to_show_false_rows),
                blocked_evidence_preserved=preserved_refusals,
            ),
            statuses,
        )
    return (
        _check_row(
            "authority_ceiling_preserved",
            "pass",
            authority_ceiling_command_count=len(ceiling_rows),
            safe_to_show_command_count=len(safe_to_show_false_rows),
            blocked_evidence_preserved=preserved_refusals,
        ),
        statuses,
    )


def _source_mutation_receipt_check(packet: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
    """
    Compute source mutation receipt check from `packet`.

    Inputs are `packet`; notable helpers are `get`, `add`, and `_check_row`.
    """
    statuses: set[str] = set()
    integrity = packet.get("recorder_integrity")
    mutation = (
        integrity.get("source_mutation_check") if isinstance(integrity, dict) else None
    )
    if not isinstance(mutation, dict):
        statuses.add("packet_stale")
        return (
            _check_row(
                "source_mutation_receipt",
                "blocked",
                reason="missing_source_mutation_receipt",
            ),
            statuses,
        )
    source_files_mutated = mutation.get("source_files_mutated") is True
    if source_files_mutated or mutation.get("status") != "pass":
        statuses.add("source_mutation_seen")
        if any(
            mutation.get(key, 0)
            for key in ("changed_count", "added_count", "removed_count")
        ):
            statuses.add("concurrent_churn_possible")
        return (
            _check_row(
                "source_mutation_receipt",
                "blocked",
                source_files_mutated=source_files_mutated,
                mutation_status=mutation.get("status"),
                changed_count=mutation.get("changed_count", 0),
                added_count=mutation.get("added_count", 0),
                removed_count=mutation.get("removed_count", 0),
                concurrent_churn_possible="concurrent_churn_possible" in statuses,
            ),
            statuses,
        )
    return (
        _check_row(
            "source_mutation_receipt",
            "pass",
            source_files_mutated=False,
            mutation_status=mutation.get("status"),
        ),
        statuses,
    )


def _first_action_proof_check(
    packet: dict[str, Any],
    packet_dir: Path,
) -> tuple[dict[str, Any], set[str]]:
    """
    Compute first action proof check from `packet` and `packet_dir`.

    Inputs are `packet` and `packet_dir`; notable helpers are `get`,
    `_first_action_proof_from_disk`, `add`, and `_check_row`.
    """
    statuses: set[str] = set()
    stored = packet.get("first_action_proof")
    if not isinstance(stored, dict):
        statuses.add("packet_stale")
        return (
            _check_row(
                "first_action_proof_present",
                "blocked",
                reason="packet.first_action_proof missing or not an object",
            ),
            statuses,
        )
    if stored.get("status") == "pass" and stored.get("failed_checks"):
        statuses.add("packet_stale")
        return (
            _check_row(
                "first_action_proof_consistent",
                "blocked",
                reason="first_action_proof claims pass while carrying failed checks",
            ),
            statuses,
        )
    commands = packet.get("commands")
    records = [row for row in commands if isinstance(row, dict)] if isinstance(commands, list) else []
    derived = _first_action_proof_from_disk(records, packet_dir)
    if derived != stored:
        statuses.add("digest_mismatch")
        differing = sorted(
            key
            for key in set(stored) | set(derived)
            if stored.get(key) != derived.get(key)
        )
        return (
            _check_row(
                "first_action_proof_rederived",
                "blocked",
                reason="stored first_action_proof does not match re-derivation from digest-bound evidence",
                differing_keys=differing[:10],
            ),
            statuses,
        )
    return (
        _check_row(
            "first_action_proof_rederived",
            "pass",
            proof_status=stored.get("status"),
            failed_check_count=len(stored.get("failed_checks") or []),
        ),
        statuses,
    )


def verify_flight_recorder_packet(
    *,
    packet_dir: Path,
    root: Path,
    write_receipt: bool = True,
    receipt_path: Path | None = None,
    verified_at: str | None = None,
) -> dict[str, Any]:
    """
    Verify whether verify flight recorder packet holds for the skeptic flight recorder flow.

    The result is derived from `packet_dir`, `root`, `write_receipt`, `receipt_path`, and
    `verified_at` with `resolve`, `expanduser`, `_load_packet`, `get`, and 19 more; failing
    evidence is returned or raised exactly where the body says so.
    """
    root = root.expanduser().resolve(strict=False)
    packet_dir = packet_dir.expanduser()
    if not packet_dir.is_absolute():
        packet_dir = root / packet_dir
    packet_dir = packet_dir.resolve(strict=False)
    packet_path = packet_dir / PACKET_FILENAME
    default_card_path = packet_dir / CARD_FILENAME
    receipt_path = receipt_path or packet_dir / VERIFICATION_FILENAME
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path

    checks: list[dict[str, Any]] = []
    statuses: set[str] = set()
    packet, load_error = _load_packet(packet_path)
    if packet is None:
        statuses.add("packet_stale")
        receipt = {
            "schema_version": VERIFICATION_SCHEMA_VERSION,
            "status": _receipt_status(statuses),
            "statuses": sorted(statuses),
            "verified_at": verified_at or utc_now(),
            "no_substrate_rerun": True,
            "provider_calls_authorized": False,
            "packet_ref": _safe_path_ref(packet_path, root),
            "checks": [
                _check_row("packet_json", "blocked", reason=load_error),
            ],
        }
        if write_receipt:
            _write_json(receipt_path, receipt)
        return receipt

    if packet.get("schema_version") == SCHEMA_VERSION:
        checks.append(_check_row("packet_schema", "pass", schema_version=SCHEMA_VERSION))
    else:
        statuses.add("packet_stale")
        checks.append(
            _check_row(
                "packet_schema",
                "blocked",
                expected_schema_version=SCHEMA_VERSION,
                observed_schema_version=packet.get("schema_version"),
            )
        )

    expected_packet_digest = packet.get("packet_payload_sha256")
    actual_packet_digest = _packet_payload_sha256(packet)
    if isinstance(expected_packet_digest, str) and expected_packet_digest == actual_packet_digest:
        checks.append(_check_row("packet_payload_sha256", "pass"))
    else:
        statuses.add("digest_mismatch" if isinstance(expected_packet_digest, str) else "packet_stale")
        checks.append(
            _check_row(
                "packet_payload_sha256",
                "blocked",
                expected_sha256=expected_packet_digest,
                actual_sha256=actual_packet_digest,
            )
        )

    card_ref = packet.get("human_card_ref")
    card_path = (
        _resolve_packet_ref(card_ref, root=root, packet_dir=packet_dir)
        if isinstance(card_ref, str)
        else default_card_path
    )
    expected_card_digest = packet.get("human_card_sha256")
    if card_path.is_file() and isinstance(expected_card_digest, str):
        actual_card_digest = sha256_file(card_path)
        if actual_card_digest == expected_card_digest:
            checks.append(_check_row("human_card_sha256", "pass"))
        else:
            statuses.add("digest_mismatch")
            checks.append(
                _check_row(
                    "human_card_sha256",
                    "blocked",
                    card_ref=_safe_path_ref(card_path, root),
                    expected_sha256=expected_card_digest,
                    actual_sha256=actual_card_digest,
                )
            )
    else:
        statuses.add("packet_stale")
        checks.append(
            _check_row(
                "human_card_sha256",
                "blocked",
                card_ref=_safe_path_ref(card_path, root),
                reason="card_missing_or_digest_absent",
            )
        )

    command_checks, raw_paths, command_statuses, command_receipt = _command_receipt_checks(
        packet.get("commands"),
        root=root,
        packet_dir=packet_dir,
    )
    checks.extend(command_checks)
    statuses.update(command_statuses)

    scan_paths = [packet_path]
    if card_path.is_file():
        scan_paths.append(card_path)
    scan_paths.extend(raw_paths)
    private_scan = _scan_private_needles(scan_paths, root)
    if private_scan["status"] != "pass":
        statuses.add("private_path_leak")
    checks.append(
        _check_row(
            "private_path_leakage",
            private_scan["status"],
            checked_file_count=len(scan_paths),
            private_path_hit_count=private_scan["private_path_hit_count"],
        )
    )

    authority_check, authority_statuses = _authority_ceiling_check(packet)
    checks.append(authority_check)
    statuses.update(authority_statuses)

    mutation_check, mutation_statuses = _source_mutation_receipt_check(packet)
    checks.append(mutation_check)
    statuses.update(mutation_statuses)

    first_action_check, first_action_statuses = _first_action_proof_check(
        packet,
        packet_dir,
    )
    checks.append(first_action_check)
    statuses.update(first_action_statuses)

    integrity = packet.get("recorder_integrity")
    provider_policy = (
        integrity.get("provider_env_policy") if isinstance(integrity, dict) else None
    )
    provider_ok = isinstance(provider_policy, dict) and (
        provider_policy.get("provider_credential_env_keys_available_to_subprocess")
        is False
    )
    if provider_ok:
        checks.append(_check_row("provider_env_policy", "pass"))
    else:
        statuses.add("packet_stale")
        checks.append(_check_row("provider_env_policy", "blocked"))

    receipt_status = _receipt_status(statuses)
    receipt: dict[str, Any] = {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": receipt_status,
        "statuses": sorted(statuses) if statuses else ["packet_valid"],
        "verified_at": verified_at or utc_now(),
        "no_substrate_rerun": True,
        "provider_calls_authorized": False,
        "packet_ref": _safe_path_ref(packet_path, root),
        "human_card_ref": _safe_path_ref(card_path, root),
        "receipt_ref": _safe_path_ref(receipt_path, root),
        "packet_generated_at": packet.get("generated_at"),
        "packet_payload_sha256": {
            "expected": expected_packet_digest,
            "actual": actual_packet_digest,
        },
        "command_receipts": command_receipt,
        "private_path_scan": private_scan,
        "checks": checks,
        "classification_policy": {
            "packet_valid": "all verifier checks passed without rerunning substrate commands",
            "packet_stale": "schema, card, receipt, or referenced output evidence is missing or structurally outdated",
            "digest_mismatch": "packet, card, or raw output digest no longer matches the receipt",
            "private_path_leak": "packet, card, raw output, or public argv contains a forbidden private path needle",
            "source_mutation_seen": "the original recorder source-mutation receipt observed tracked source changes",
            "concurrent_churn_possible": "source mutation evidence cannot distinguish recorder writes from concurrent tracked churn",
        },
    }

    if write_receipt:
        _write_json(receipt_path, receipt)
        final_scan = _scan_private_needles([*scan_paths, receipt_path], root)
        if final_scan["status"] != "pass":
            statuses.add("private_path_leak")
            receipt["status"] = _receipt_status(statuses)
            receipt["statuses"] = sorted(statuses)
        receipt["verifier_integrity"] = {
            "receipt_written": True,
            "final_private_path_scan": final_scan,
        }
        _write_json(receipt_path, receipt)
    else:
        receipt["verifier_integrity"] = {
            "receipt_written": False,
        }
    return receipt


def build_flight_recorder_packet(
    *,
    root: Path,
    out_dir: Path,
    python_executable: str = sys.executable,
    runner: Runner = default_runner,
    snapshotter: SourceSnapshotter = source_snapshot,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """
    Produce the build flight recorder packet value used by
    `microcosm_core.skeptic_flight_recorder`.

    Inputs are `root`, `out_dir`, `python_executable`, `runner`, `snapshotter`, and 1 more;
    notable helpers are `resolve`, `expanduser`, `mkdir`, `create_disposable_project`, and
    25 more.
    """
    root = root.expanduser().resolve(strict=False)
    out_dir = out_dir.expanduser()
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    generated = generated_at or utc_now()
    out_dir.mkdir(parents=True, exist_ok=True)
    project_dir = out_dir / "work/project"
    create_disposable_project(project_dir)

    env, provider_policy = subprocess_env(root)
    before_snapshot = snapshotter(root)
    command_records = [
        _execute_command(
            spec,
            root=root,
            out_dir=out_dir,
            env=env,
            runner=runner,
        )
        for spec in command_plan(root, out_dir, python_executable)
    ]
    after_snapshot = snapshotter(root)

    output_paths = [
        path
        for path in out_dir.rglob("*")
        if path.is_file() and not path.name.endswith(".tmp")
    ]
    private_scan = _scan_private_needles(output_paths, root)
    mutation = source_mutation_check(before_snapshot, after_snapshot)
    command_summary = _command_status_summary(command_records)
    refused_claims = []
    for command_id in command_summary["blocked_reported_status_command_ids"]:
        refused_claims.append(
            {
                "command_id": command_id,
                "reason": "command reported blocked status; preserved as evaluator evidence",
            }
        )
    for command_id in command_summary["nonzero_return_code_command_ids"]:
        if command_id not in {row["command_id"] for row in refused_claims}:
            refused_claims.append(
                {
                    "command_id": command_id,
                    "reason": "command returned non-zero; raw stdout/stderr retained by digest and path",
                }
            )
    first_action_proof = _first_action_proof_from_disk(command_records, out_dir)
    if first_action_proof["status"] != "pass":
        refused_claims.append(
            {
                "command_id": "first_action_proof",
                "reason": (
                    "first-action proof checks failed: "
                    + ", ".join(first_action_proof["failed_checks"])
                ),
            }
        )

    packet_path = out_dir / PACKET_FILENAME
    card_path = out_dir / CARD_FILENAME
    evaluator_status = "clear" if not refused_claims else "mixed_claims_preserved"
    packet: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "pass"
            if private_scan["status"] == "pass" and mutation["status"] == "pass"
            else "blocked"
        ),
        "generated_at": generated,
        "packet_ref": _relative_display(packet_path, root),
        "human_card_ref": _relative_display(card_path, root),
        "command_output_dir_ref": _relative_display(out_dir / "commands", root),
        "smoke_output_dir_ref": _relative_display(out_dir / "smoke", root),
        "disposable_project_ref": _relative_display(project_dir, root),
        "macro_informed_spine": {
            "root": "system_self_comprehension_root",
            "spine": "system_self_comprehension_spine",
            "imported_lesson": (
                "Map what exists, what is generated, what runs, what is private, "
                "what is stale, and what can be safely projected."
            ),
        },
        "authority_and_omission_policy": {
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
            "raw_payload_bodies_are_drilldown_files_not_packet_fields": True,
            "selected_fields_only_in_packet": True,
        },
        "recorder_integrity": {
            "source_mutation_check": mutation,
            "private_path_scan": private_scan,
            "provider_env_policy": provider_policy,
        },
        "evaluator_verdict": {
            "status": evaluator_status,
            "command_status_summary": command_summary,
            "refused_claims": refused_claims,
            "evidence_class_counts": _merge_evidence_class_counts(command_records),
            "authority_ceiling_false_keys_by_command": _authority_false_keys(command_records),
        },
        "first_action_proof": first_action_proof,
        "commands": command_records,
    }
    _write_json(packet_path, packet)
    card = _human_card(packet)
    _write_text(card_path, card)
    final_output_paths = [
        path
        for path in out_dir.rglob("*")
        if path.is_file() and not path.name.endswith(".tmp")
    ]
    packet["recorder_integrity"]["private_path_scan"] = _scan_private_needles(
        final_output_paths,
        root,
    )
    packet["status"] = (
        "pass"
        if packet["recorder_integrity"]["private_path_scan"]["status"] == "pass"
        and mutation["status"] == "pass"
        else "blocked"
    )
    card = _human_card(packet)
    _write_text(card_path, card)
    packet["human_card_sha256"] = sha256_file(card_path)
    packet["packet_payload_sha256"] = sha256_bytes(
        json.dumps(packet, sort_keys=True).encode("utf-8")
    )
    _write_json(packet_path, packet)
    return packet


def _generate_main(argv: list[str] | None = None) -> int:
    """
    Register CLI syntax for `microcosm_core.skeptic_flight_recorder._generate_main`.

    The function mutates the provided argparse object with this module's flags, subcommands,
    or defaults.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Compose Microcosm first-screen/runtime/proof commands into a "
            "skeptical public-safe replay packet."
        ),
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--out")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero when the packet preserves blocked/non-zero command evidence",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    out = Path(args.out) if args.out else default_out_dir()
    packet = build_flight_recorder_packet(
        root=root,
        out_dir=out,
        python_executable=args.python,
    )
    summary = {
        "status": packet["status"],
        "evaluator_status": packet["evaluator_verdict"]["status"],
        "packet_ref": packet["packet_ref"],
        "human_card_ref": packet["human_card_ref"],
        "nonzero_return_code_count": packet["evaluator_verdict"][
            "command_status_summary"
        ]["nonzero_return_code_count"],
        "blocked_reported_status_count": packet["evaluator_verdict"][
            "command_status_summary"
        ]["blocked_reported_status_count"],
        "private_path_hit_count": packet["recorder_integrity"]["private_path_scan"][
            "private_path_hit_count"
        ],
        "source_files_mutated": packet["recorder_integrity"]["source_mutation_check"][
            "source_files_mutated"
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if packet["status"] != "pass":
        return 1
    if args.strict and packet["evaluator_verdict"]["status"] != "clear":
        return 2
    return 0


def _verify_main(argv: list[str] | None = None) -> int:
    """
    Register CLI syntax for `microcosm_core.skeptic_flight_recorder._verify_main`.

    The function mutates the provided argparse object with this module's flags, subcommands,
    or defaults.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Verify an existing Microcosm skeptic flight-recorder packet "
            "without rerunning substrate commands."
        ),
    )
    parser.add_argument("packet_dir")
    parser.add_argument("--root", default=".")
    parser.add_argument("--receipt-out")
    parser.add_argument(
        "--no-write-receipt",
        action="store_true",
        help="only print the verification summary; do not write a receipt file",
    )
    args = parser.parse_args(argv)
    receipt = verify_flight_recorder_packet(
        packet_dir=Path(args.packet_dir),
        root=Path(args.root),
        receipt_path=Path(args.receipt_out) if args.receipt_out else None,
        write_receipt=not args.no_write_receipt,
    )
    summary = {
        "status": receipt["status"],
        "statuses": receipt["statuses"],
        "packet_ref": receipt["packet_ref"],
        "human_card_ref": receipt.get("human_card_ref"),
        "receipt_ref": receipt.get("receipt_ref"),
        "no_substrate_rerun": receipt["no_substrate_rerun"],
        "provider_calls_authorized": receipt["provider_calls_authorized"],
        "digest_mismatch_count": receipt.get("command_receipts", {}).get(
            "digest_mismatch_count",
            0,
        ),
        "private_path_hit_count": receipt.get("private_path_scan", {}).get(
            "private_path_hit_count",
            0,
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "packet_valid" else 1


def main(argv: list[str] | None = None) -> int:
    """
    Run the `microcosm_core.skeptic_flight_recorder` command-line entry point.

    It parses argv, invokes the file-local builders or validators, and returns a
    process-style status code.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"verify", "replay-check"}:
        return _verify_main(args[1:])
    if args and args[0] == "generate":
        return _generate_main(args[1:])
    return _generate_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
