#!/usr/bin/env python3
"""Attempt the Lean full-fidelity packet dependency/replay lane."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.meta.factory import build_lean_mathematics_microcosm_projection as lean_microcosm


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_path(path: str | Path, *, repo_root: Path = REPO_ROOT) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _rel(path: str | Path, *, repo_root: Path = REPO_ROOT) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _write_json(path: str | Path, payload: Mapping[str, Any], *, repo_root: Path) -> None:
    target = _repo_path(path, repo_root=repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: str | Path, payload: str, *, repo_root: Path) -> None:
    target = _repo_path(path, repo_root=repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")


def _tail(text: str, *, limit: int = 4000) -> str:
    return text[-limit:] if len(text) > limit else text


def _run_command(args: Sequence[str], *, cwd: Path, timeout_seconds: int, mode: str) -> dict[str, Any]:
    started_at = _utc_now()
    try:
        proc = subprocess.run(
            list(args),
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "mode": mode,
            "command": " ".join(args),
            "args": list(args),
            "cwd": _rel(cwd),
            "started_at": started_at,
            "ended_at": _utc_now(),
            "timeout_seconds": timeout_seconds,
            "timed_out": False,
            "returncode": proc.returncode,
            "stdout_tail": _tail(proc.stdout),
            "stderr_tail": _tail(proc.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return {
            "mode": mode,
            "command": " ".join(args),
            "args": list(args),
            "cwd": _rel(cwd),
            "started_at": started_at,
            "ended_at": _utc_now(),
            "timeout_seconds": timeout_seconds,
            "timed_out": True,
            "returncode": None,
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
        }


def _target_rel_to_lake_root(target_file: str | None, lake_root: str, *, repo_root: Path) -> str | None:
    if not target_file:
        return None
    target_path = _repo_path(target_file, repo_root=repo_root)
    lake_root_path = _repo_path(lake_root, repo_root=repo_root)
    try:
        return target_path.resolve().relative_to(lake_root_path.resolve()).as_posix()
    except ValueError:
        return target_path.as_posix()


def build_replay_attempt_receipt(
    *,
    repo_root: Path = REPO_ROOT,
    attempt_hydration: bool = False,
    attempt_target: bool = False,
    force_target: bool = False,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    _, packet, packet_receipt, base_replay_receipt, *_ = lean_microcosm.build_projection_and_packet(repo_root=repo_root)
    workspace = (
        base_replay_receipt.get("lake_workspace_status")
        if isinstance(base_replay_receipt.get("lake_workspace_status"), Mapping)
        else {}
    )
    lake_root = str(workspace.get("lake_root") or "")
    lake_root_path = _repo_path(lake_root, repo_root=repo_root) if lake_root else repo_root
    previous_overlay: dict[str, Any] = {
        "replay_context_fingerprint": base_replay_receipt.get("replay_context_fingerprint"),
        "attempted_at": _utc_now(),
    }
    if attempt_hydration and lake_root and lake_root_path.is_dir():
        previous_overlay["hydration_attempt"] = _run_command(
            ("lake", "exe", "cache", "get"),
            cwd=lake_root_path,
            timeout_seconds=timeout_seconds,
            mode="mathlib_cache",
        )
    elif attempt_hydration:
        previous_overlay["hydration_attempt"] = {
            "mode": "mathlib_cache",
            "command": "lake exe cache get",
            "cwd": _rel(lake_root_path),
            "started_at": previous_overlay["attempted_at"],
            "ended_at": _utc_now(),
            "timeout_seconds": timeout_seconds,
            "timed_out": False,
            "returncode": None,
            "status": "skipped",
            "reason": "lake_root_missing",
        }

    replay_receipt = lean_microcosm.build_full_fidelity_evidence_packet_replay_receipt(
        packet,
        packet_receipt,
        repo_root=repo_root,
        previous_receipt=previous_overlay,
    )
    if attempt_target and lake_root and lake_root_path.is_dir():
        target_rel = _target_rel_to_lake_root(
            (replay_receipt.get("lake_workspace_status") or {}).get("target_file"),
            lake_root,
            repo_root=repo_root,
        )
        if target_rel and (force_target or replay_receipt.get("dependency_hydration_status") == "PASS"):
            previous_overlay["target_attempt"] = _run_command(
                ("lake", "env", "lean", "--profile", target_rel),
                cwd=lake_root_path,
                timeout_seconds=timeout_seconds,
                mode="lake_target_replay",
            )
        else:
            previous_overlay["target_attempt"] = {
                "mode": "lake_target_replay",
                "command": f"lake env lean --profile {target_rel or '<missing-target>'}",
                "cwd": _rel(lake_root_path),
                "started_at": previous_overlay["attempted_at"],
                "ended_at": _utc_now(),
                "timeout_seconds": timeout_seconds,
                "timed_out": False,
                "returncode": None,
                "status": "skipped",
                "reason": "dependency_hydration_not_pass",
            }
        replay_receipt = lean_microcosm.build_full_fidelity_evidence_packet_replay_receipt(
            packet,
            packet_receipt,
            repo_root=repo_root,
            previous_receipt=previous_overlay,
        )
    return replay_receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt-hydration", action="store_true")
    parser.add_argument("--attempt-target", action="store_true")
    parser.add_argument("--force-target", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)
    receipt = build_replay_attempt_receipt(
        attempt_hydration=args.attempt_hydration,
        attempt_target=args.attempt_target,
        force_target=args.force_target,
        timeout_seconds=args.timeout_seconds,
    )
    if args.write:
        _write_json(lean_microcosm.FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL, receipt, repo_root=REPO_ROOT)
        _write_text(
            lean_microcosm.FULL_FIDELITY_PACKET_REPLAY_DOC_REL,
            lean_microcosm.render_full_fidelity_packet_replay_markdown(receipt),
            repo_root=REPO_ROOT,
        )
    summary = {
        "status": receipt.get("status"),
        "replay_receipt_ref": lean_microcosm.FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL,
        "dependency_hydration_status": receipt.get("dependency_hydration_status"),
        "target_replay_status": receipt.get("target_replay_status"),
        "reviewer_acceptance_status": receipt.get("reviewer_acceptance_status"),
        "proof_authority_delta": receipt.get("proof_authority_delta"),
    }
    print(json.dumps(summary if args.compact else receipt, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
