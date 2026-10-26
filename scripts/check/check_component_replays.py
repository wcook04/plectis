#!/usr/bin/env python3
"""Replay every registered component through its existing runtime runner."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from microcosm_core.runtime_shell import RUNTIME_STEPS
from microcosm_core.release_export import _source_identity
from microcosm_core.schemas import read_json_strict
from microcosm_core.projections.organ_surface_contract import native_replay_step, replay_verdict


class UnsupportedInputSymlink(ValueError):
    """A supplied input tree contains a link outside the captured file model."""


def input_tree_hash(path: Path) -> str:
    """Bind real input bytes while pruning local build and cache directories."""
    if path.is_symlink():
        raise UnsupportedInputSymlink
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_dir():
        raise NotADirectoryError
    files = []
    for directory, names, filenames in os.walk(path):
        if any((Path(directory) / name).is_symlink() for name in names):
            raise UnsupportedInputSymlink
        names[:] = sorted(name for name in names if name not in {
            ".git", ".microcosm", ".build", "__pycache__", ".venv", ".pytest_cache",
        })
        for name in sorted(filenames):
            candidate = Path(directory) / name
            if candidate.is_symlink():
                raise UnsupportedInputSymlink
            if candidate.suffix in {".pyc", ".pyo"}:
                continue
            files.append((candidate.relative_to(path).as_posix(),
                          hashlib.sha256(candidate.read_bytes()).hexdigest(),
                          bool(candidate.stat().st_mode & 0o111)))
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def replay_steps(root: Path, out: Path, steps) -> list[dict]:
    """Retain each real result and continue so one failure cannot hide others."""
    rows = []
    for declared_step in steps:
        step = native_replay_step(declared_step)
        started = time.monotonic()
        try:
            input_path = root / step.example_rel
            if not input_path.resolve().is_relative_to(root.resolve()):
                raise UnsupportedInputSymlink
            for ancestor in (input_path, *input_path.parents):
                if ancestor == root:
                    break
                if ancestor.is_symlink():
                    raise UnsupportedInputSymlink
            input_hash = input_tree_hash(input_path)
            result = step.runner(root / step.example_rel, out / step.organ_id,
                                 "make component-replays")
            receipt = out / step.organ_id / step.receipt_name
            if receipt.is_symlink():
                raise ValueError("replay receipt must be a regular file")
            recorded = read_json_strict(receipt)
            if not isinstance(recorded, dict) or recorded.get("status") != result.get("status"):
                raise ValueError("declared receipt status does not match the runner result")
            if "organ_id" in recorded and recorded["organ_id"] != step.organ_id:
                raise ValueError("declared receipt names another component")
            after_hash = input_tree_hash(root / step.example_rel)
            if input_hash != after_hash:
                raise ValueError("component replay changed its supplied input bytes or executable modes")
            row = {"organ_id": step.organ_id, "status": replay_verdict(step, result),
                   "input_ref": step.example_rel, "error_codes": result.get("error_codes", []),
                   "execution_witness_mode": result.get("execution_witness_mode"),
                   "verification_performed": result.get("verification_performed"),
                   "tool_state": result.get("tool_state"),
                   "input_tree_sha256": input_hash,
                   "receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
                   "receipt_ref": str(receipt.relative_to(root))}
        except Exception as error:
            row = {"organ_id": step.organ_id, "status": "error",
                   "input_ref": step.example_rel, "error": type(error).__name__}
        row["elapsed_seconds"] = round(time.monotonic() - started, 3)
        rows.append(row)
        print(f"{step.organ_id}: {row['status']}", flush=True)
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=Path(".microcosm/component-replays"))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    registry = json.loads((root / "core/organ_registry.json").read_text())
    declared = {row["organ_id"] for row in registry["implemented_organs"]}
    routed = [step.organ_id for step in RUNTIME_STEPS]
    if len(routed) != len(set(routed)) or set(routed) != declared:
        parser.error("runtime replay routes must cover the complete implemented component registry exactly once")
    out = args.out.resolve()
    if not out.is_relative_to(root / ".microcosm"):
        parser.error("replay output must be inside this checkout's ignored .microcosm directory")
    out.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="run-", dir=out))
    os.environ["MICROCOSM_TRACKED_RECEIPT_WRITES"] = "0"
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    source = {"git_identity": _source_identity(root),
              "runtime_source_tree_sha256": input_tree_hash(root / "src")}
    rows = replay_steps(root, run, RUNTIME_STEPS)
    failures = [row["organ_id"] for row in rows if row["status"] != "pass"]
    summary = {"schema_version": "plectis_component_replay_gate_v1",
               "status": "pass" if not failures else "blocked", "component_count": len(rows),
               "failed_components": failures, "results": rows, "source": source,
               "claim_ceiling": "Fresh named runner results over supplied public inputs; no broader correctness or release authority."}
    path = run / "component-replays.json"
    path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Component replay gate: {summary['status']} ({len(rows)} components, {len(failures)} failures)")
    print(f"Summary: {path.relative_to(root)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
