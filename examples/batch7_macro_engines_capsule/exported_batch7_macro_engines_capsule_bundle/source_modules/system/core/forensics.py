"""
[PURPOSE]
- Teleology: Reconstruct run state from disk artifacts (frontier detection).
- Mechanism: Scan run directories and artifacts to rebuild execution status without in-memory state.

[INTERFACE]
- Inputs: root_dir / run_dir (Path), and optional run_id selectors.
- Outputs: Reconstructed run state (status + per-node/per-container summaries).

[FLOW]
- Discover candidate run directories.
- Read persisted manifests/summaries.
- Infer node/container statuses from artifacts and structural logs.
- Return reconstructed state for UI or downstream tooling.
- When-needed: Open when a task is about rebuilding run state from artifacts after the engine, UI, or controller lost in-memory context.
- Escalates-to: system/core/engine.py::GodModeEngine.run; system/core/loader.py::PhysicalLoader.load_all_nodes
- Navigation-group: system_core

[DEPENDENCIES]
- standard_lib.pathlib: directory traversal
- standard_lib.json: manifest decoding
- state/runs/<run_id>: artifacts + manifests as the ground truth

[CONSTRAINTS]
- Atomicity: Forensics is read-only; it must not create, mutate, or delete artifacts/manifests.
- Determinism: Given identical on-disk run data, reconstruction output is deterministic.
- Robustness: Missing files must degrade gracefully (partial reconstruction allowed).

"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional

_STRUCTURAL_FILES = frozenset({
    "graph_snapshot.json", "seed_manifest.json", 
    "run_summary.json", "runtime_context.json"
})

def reconstruct_run_state(run_dir: Path) -> Dict[str, str]:
    """
    [ACTION]
    - Teleology: Rebuilds node_outcomes from disk artifacts + topology.
    - Mechanism: Merges snapshot dependencies with artifact status.
    - Fails: Returns empty dict on IO error.
    - Guarantee: Returns Dict[node_id, status].
    - When-needed: Open when recovering per-node status from a persisted run directory without restarting the engine.
    - Escalates-to: system/core/engine.py::GodModeEngine.run; system/core/loader.py::PhysicalLoader.load_all_nodes
    """
    artifacts_dir = run_dir / "artifacts"
    snapshot_path = artifacts_dir / "graph_snapshot.json"
    
    if not snapshot_path.exists():
        return {}
        
    try:
        with open(snapshot_path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
        dep_map = {n["id"]: n.get("dependencies", []) for n in snapshot.get("nodes", [])}
    except Exception:
        return {}

    real_status_map = {}
    if artifacts_dir.exists():
        for p in artifacts_dir.glob("*.json"):
            if p.name in _STRUCTURAL_FILES: continue
            if p.stat().st_size == 0: continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                status = data.get("status") or data.get("metadata", {}).get("status")
                if status in ("success", "loaded"):
                    real_status_map[p.stem] = status
                elif status == "failure":
                    real_status_map[p.stem] = "failure"
            except Exception:
                continue

    outcomes = {}
    for nid, deps in dep_map.items():
        if nid in real_status_map:
            outcomes[nid] = real_status_map[nid]
        else:
            is_ready = True
            if deps:
                for dep in deps:
                    if dep not in real_status_map or real_status_map[dep] not in ("success", "loaded"):
                        is_ready = False
                        break
            
            outcomes[nid] = "failure" if is_ready else "idle"
            
    return outcomes

def reconstruct_run_state_by_id(run_id: str, runs_dir: Path) -> Dict[str, str]:
    """
    [ACTION]
    - Teleology: Convenience wrapper to reconstruct state by ID.
    - Mechanism: Resolves path and calls `reconstruct_run_state`.
    - Fails: None.
    - Guarantee: Returns status dict.
    - When-needed: Open when a caller has a run id plus runs root and needs the quickest path to the reconstructed status map.
    - Escalates-to: system/core/engine.py::GodModeEngine.run; system/core/loader.py::PhysicalLoader.load_all_nodes
    """
    return reconstruct_run_state(runs_dir / run_id)
