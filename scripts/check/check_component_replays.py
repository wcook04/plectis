#!/usr/bin/env python3
"""Replay the complete component registry through the shared admission host."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from microcosm_core.runtime_shell import RUNTIME_STEPS
from microcosm_core.component_replay import (
    UnsupportedInputSymlink, input_tree_hash, native_replay_step,
    new_replay_directory, replay_components, replay_steps, replay_verdict,
)
from microcosm_core.release_export import _source_identity
from microcosm_core.schemas import read_json_strict


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=Path(".microcosm/component-replays"))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    registry = read_json_strict(root / "core/organ_registry.json")
    registry_rows = registry["implemented_organs"]
    declared = [row["organ_id"] for row in registry_rows]
    routed = [step.organ_id for step in RUNTIME_STEPS]
    if (not declared or len(declared) != len(set(declared))
            or len(routed) != len(set(routed)) or set(routed) != set(declared)):
        parser.error("runtime replay routes must cover the nonempty unique component registry exactly once")
    out = args.out.resolve()
    if not out.is_relative_to(root / ".microcosm"):
        parser.error("replay output must be inside this checkout's ignored .microcosm directory")
    run = new_replay_directory(root, out)
    os.environ["MICROCOSM_TRACKED_RECEIPT_WRITES"] = "0"
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    identity = _source_identity(root)
    summary = replay_components(root, run, RUNTIME_STEPS, registry_rows=registry_rows,
                                route_provider=lambda: RUNTIME_STEPS)
    summary["git_identity"] = identity
    for row in summary["results"]:
        if row.get("receipt_ref"):
            row["receipt_ref"] = str(Path(row["receipt_ref"]).relative_to(root))
        print(f"{row['organ_id']}: {row['status']}", flush=True)
    path = run / "component-replays.json"
    path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Component replay gate: {summary['status']} ({summary['component_count']} components, {len(summary['failed_components'])} failures)")
    print(f"Summary: {path.relative_to(root)}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
