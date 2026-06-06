"""Run the clean-clone baseline for the release microcosm.

[PURPOSE]
Prove that the public-safe root can run from a copied checkout without the
private root, git history, package install, or Python network access.

[INTERFACE]
Exports run_clean_clone_baseline for the CLI and contract tests.

[FLOW]
Copy the checkout to a temporary clone, install a Python socket-blocking
sitecustomize guard, run local validator/probe commands, scan for private
boundary markers, and emit a bounded receipt.

[CONSTRAINTS]
This is local clean-clone evidence, not hosted-public, external clone, or
publication authority.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}

PRIVATE_MARKERS: dict[str, re.Pattern[str]] = {
    "private_home_path": re.compile(r"/Users/[A-Za-z0-9_.-]+"),
    "private_browser_profile": re.compile(re.escape("Library/Application Support/" + "Google/Chrome")),
    "provider_browser_symbol": re.compile(
        r"claude_app_injector|chatgpt_session_inject|claude_session_transport|"
        r"claude-in-chrome|gemini_web_session|browser_provider_session"
    ),
    "secret_literal": re.compile(r"BEGIN (?:RSA |OPENSSH |EC |)?PRIVATE KEY"),
    "openai_key_shape": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "github_token_shape": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
}

POLICY_EXCEPTION_PATHS = {
    "src/idea_microcosm/clean_clone.py",
}

COMMANDS: tuple[tuple[str, ...], ...] = (
    ("build-artifact-manifest", "--root", ".", "--write-receipt"),
    ("run-redaction-scan", "--root", ".", "--write-receipt"),
    ("validate", "--root", ".", "--write-receipt"),
    ("run-cold-sandbox-probe", "--root", ".", "--write-receipt"),
    ("query-entry-routes", "--root", ".", "--band", "cluster_flag"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _redact(text: str, clone_root: Path, source_root: Path) -> str:
    text = text.replace(str(clone_root), "<clean-clone-root>")
    text = text.replace(str(source_root), "<source-root>")
    return re.sub(r"/Users/[A-Za-z0-9_.-]+(?:/[^\s\"']*)?", "<private-path>", text)


def _ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in EXCLUDED_DIR_NAMES}
    ignored.update(name for name in names if name.endswith((".pyc", ".pyo")))
    return ignored


def _write_network_guard(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "sitecustomize.py").write_text(
        """from __future__ import annotations

import socket


class NetworkDisabled(RuntimeError):
    pass


def _blocked(*_args, **_kwargs):
    raise NetworkDisabled("network disabled by clean-clone baseline")


socket.create_connection = _blocked
socket.socket = _blocked
""",
        encoding="utf-8",
    )


def _run_clone_command(clone_root: Path, source_root: Path, guard_dir: Path, args: tuple[str, ...]) -> dict[str, Any]:
    env = {
        "AIW_MICROCOSM_NETWORK_DISABLED": "1",
        "HOME": str(clone_root / ".home"),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": os.pathsep.join([str(guard_dir), str(clone_root / "src")]),
    }
    (clone_root / ".home").mkdir(exist_ok=True)
    command = [sys.executable, "-m", "idea_microcosm.cli", *args]
    completed = subprocess.run(
        command,
        cwd=clone_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    public_command = ["python3" if item == sys.executable else item for item in command]
    return {
        "command": public_command,
        "returncode": completed.returncode,
        "status": "pass" if completed.returncode == 0 else "fail",
        "stdout_head": _redact(completed.stdout[:1200], clone_root, source_root),
        "stderr_head": _redact(completed.stderr[:1200], clone_root, source_root),
    }


def _scan_private_markers(clone_root: Path, source_root: Path) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    skipped_dir_count = 0
    scanned_file_count = 0
    for directory, dirs, files in os.walk(clone_root):
        skipped_dir_count += len([name for name in dirs if name in EXCLUDED_DIR_NAMES])
        dirs[:] = [name for name in dirs if name not in EXCLUDED_DIR_NAMES]
        current = Path(directory)
        for name in files:
            path = current / name
            if path.suffix.lower() in {".pyc", ".pyo"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            scanned_file_count += 1
            rel_path = path.relative_to(clone_root).as_posix()
            if rel_path in POLICY_EXCEPTION_PATHS:
                continue
            public_text = _redact(text, clone_root, source_root)
            for pattern_id, pattern in PRIVATE_MARKERS.items():
                for match in pattern.finditer(public_text):
                    hits.append(
                        {
                            "pattern": pattern_id,
                            "path": rel_path,
                            "line": public_text.count("\n", 0, match.start()) + 1,
                        }
                    )
    return {
        "schema_version": "clean_clone_private_marker_scan_v0",
        "status": "pass" if not hits else "fail",
        "scanned_file_count": scanned_file_count,
        "skipped_dir_count": skipped_dir_count,
        "blocking_hit_count": len(hits),
        "blocking_hits": hits[:50],
    }


def _receipt_path(source_root: Path, output_path: str | None) -> tuple[str, Path]:
    receipt_rel = output_path or "receipts/clean_clone_baseline.json"
    candidate = Path(receipt_rel)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("--output must stay relative to the microcosm root")
    return receipt_rel, source_root / candidate


def run_clean_clone_baseline(
    root: Path,
    *,
    write_receipt: bool = False,
    output_path: str | None = None,
    keep_clone: bool = False,
    at: str | None = None,
) -> dict[str, Any]:
    """Run the local clean-clone/no-network baseline and return a receipt."""
    source_root = root.resolve()
    generated_at = at or _utc_now()
    receipt_target = _receipt_path(source_root, output_path) if write_receipt else None
    temp_root = Path(tempfile.mkdtemp(prefix="idea-microcosm-clean-clone-"))
    clone_root = temp_root / "clone"
    failures: list[dict[str, Any]] = []
    command_results: list[dict[str, Any]] = []
    private_scan: dict[str, Any] = {
        "schema_version": "clean_clone_private_marker_scan_v0",
        "status": "not_run",
        "blocking_hit_count": None,
        "blocking_hits": [],
    }
    try:
        shutil.copytree(source_root, clone_root, ignore=_ignore)
        stale_self_receipt = clone_root / "receipts" / "clean_clone_baseline.json"
        stale_self_receipt_removed = stale_self_receipt.exists()
        if stale_self_receipt_removed:
            stale_self_receipt.unlink()
        guard_dir = temp_root / "no_network"
        _write_network_guard(guard_dir)
        if (clone_root / ".git").exists():
            failures.append({"reason": "git_history_copied", "path": ".git"})

        for args in COMMANDS:
            result = _run_clone_command(clone_root, source_root, guard_dir, args)
            command_results.append(result)
            if result["status"] != "pass":
                failures.append({"reason": "command_failed", "command": result["command"]})

        private_scan = _scan_private_markers(clone_root, source_root)
        if private_scan["status"] != "pass":
            failures.append({"reason": "private_marker_scan_failed", "hit_count": private_scan["blocking_hit_count"]})

        required_clone_outputs = [
            "receipts/cold_sandbox_probe_latest.json",
            "receipts/redaction_scan.json",
            "receipts/validation_run.json",
        ]
        missing_outputs = [path for path in required_clone_outputs if not (clone_root / path).exists()]
        if missing_outputs:
            failures.append({"reason": "missing_clone_outputs", "paths": missing_outputs})

        receipt = {
            "kind": "receipt",
            "schema_version": "clean_clone_baseline_receipt_v0",
            "id": "receipt.clean_clone_baseline",
            "generated_at": generated_at,
            "owner": "idea_microcosm.clean_clone",
            "claim_ref": "release.clean_clone_baseline",
            "claim_tier": "fixture_validated",
            "command": "python -m idea_microcosm.cli run-clean-clone-baseline --root . --write-receipt",
            "status": "ok" if not failures else "fail",
            "result": "ok" if not failures else "fail",
            "evidence_refs": [
                "src/idea_microcosm/clean_clone.py",
                "src/idea_microcosm/redaction_scan.py",
                "src/idea_microcosm/cli.py",
                "src/idea_microcosm/validators.py",
                "receipts/cold_sandbox_probe_latest.json",
                "receipts/redaction_scan.json",
                "receipts/validation_run.json",
                "state/artifact_manifest.json",
            ],
            "source_root": ".",
            "clone_root": str(clone_root) if keep_clone else "removed_after_probe",
            "copy_policy": {
                "excluded_dir_names": sorted(EXCLUDED_DIR_NAMES),
                "git_history_copied": (clone_root / ".git").exists(),
                "stale_self_receipt_removed": stale_self_receipt_removed,
            },
            "network_guard": {
                "status": "enabled",
                "mode": "python_sitecustomize_socket_block",
                "env_flag": "AIW_MICROCOSM_NETWORK_DISABLED=1",
                "command_count": len(COMMANDS),
            },
            "commands": command_results,
            "private_boundary_scan": private_scan,
            "required_clone_outputs": required_clone_outputs,
            "claim_boundary": (
                "local clean-clone and Python no-network baseline only; not hosted CI, "
                "external public clone proof, publication permission, or private-root equivalence"
            ),
            "failures": failures,
            "omissions": [
                "Does not prove hosted CI.",
                "Does not prove an external public remote can be cloned.",
                "Does not install package dependencies from a network.",
                "Does not grant publication permission.",
            ],
        }
        if receipt_target is not None:
            receipt_rel, receipt_path = receipt_target
            receipt["receipt_written"] = receipt_rel
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return receipt
    finally:
        if not keep_clone:
            shutil.rmtree(temp_root, ignore_errors=True)
