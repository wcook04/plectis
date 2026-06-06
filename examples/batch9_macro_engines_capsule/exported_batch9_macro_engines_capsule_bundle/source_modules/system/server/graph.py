# system/server/graph.py

"""
[PURPOSE]
- Teleology: Compile a UI-facing `GraphSnapshot` from filesystem-backed Codex nodes.
- Mechanism: Group Closure Scoping + Upstream dependency walk + upstream zoning.

[INTERFACE]
- Inputs: `root_dir` (repo root), `target_id` (node id), `run_id` (label for snapshot provenance).
- Outputs: `GraphSnapshot` containing `NodeView[]` + `EdgeView[]` for UI rendering.
- Reads: `codex/nodes/**` via `PhysicalLoader`.
- Writes: None (pure compilation).

[FLOW]
1. Hydrate node universe from disk.
2. Compute scope using Group Closure Scoping + upstream BFS.
3. Topologically bucket scoped nodes into waves.
4. Project scoped nodes/edges into API models and return a `GraphSnapshot`.

[UPDATES - PASS 3 (FIXED)]
- [LOCKED DECISION L5] Group Closure Scoping: Scope now seeds ALL nodes belonging to the 
  target's group (siblings) rather than just the target node. This fixes the "Missing Feeds" bug.
- [LOCKED DECISION L6] Upstream Zoning: non-native dependencies are projected as "UPSTREAM"
  while preserving original `source_group` metadata for UI grouping.
- Rich Data: Extracts 'instruction', 'dependencies', 'timeout'.
- Sanitization: Tool nodes have 'platform' forced to None.
[DEPENDENCIES]
- system.core.loader.PhysicalLoader: graph_hydration
- system.server.schemas: GraphSnapshot (API models)

[CONSTRAINTS]
- Atomicity: Read-only snapshot compilation (no filesystem writes).
- Orders: Waves are sorted for determinism; projections are stable given a stable universe.
- Non-goal: Full cycle-path detection (topology failures are only surfaced for missing targets).
- When-needed: Open when a server route needs the scoped mission graph projection that the UI renders, rather than reading raw node JSON and reconstructing zoning rules manually.
- When-needed: Open when tracing how a `GraphSnapshot` or `graph_snapshot` is compiled from Codex nodes, including Group Closure Scoping and UPSTREAM zoning rules.
- Escalates-to: system/core/loader.py::PhysicalLoader; system/server/schemas.py::GraphSnapshot; system/server/main.py::get_mission_graph
- Navigation-group: server_backend

"""

import logging
import json
import time
import re
from pathlib import Path
from collections import defaultdict, deque
from typing import Dict, List, Set, Any, Optional

from system.core.loader import PhysicalLoader
from system.lib.types import CodexNode
from system.lib.contracts import normalize_contracts, extract_contract_fnames
from system.server.schemas import (
    GraphSnapshot, NodeView, EdgeView, LaneEnum, ProvenanceView, TopologyError
)

logger = logging.getLogger(__name__)


def _json_safe(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:
        return str(value)


_INLINE_OVERRIDE_PREVIEW_MAX_KEYS = 20
_INLINE_OVERRIDE_PREVIEW_MAX_CHARS = 4096

def _build_inline_override_preview(overrides: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
    preview: Dict[str, Any] = {}
    truncated = False

    sorted_keys = sorted(str(key) for key in overrides.keys())
    for idx, key in enumerate(sorted_keys):
        if idx >= _INLINE_OVERRIDE_PREVIEW_MAX_KEYS:
            truncated = True
            break
        preview[key] = _json_safe(overrides.get(key))

    serialized = json.dumps(preview, sort_keys=True, default=str)
    if len(serialized) > _INLINE_OVERRIDE_PREVIEW_MAX_CHARS:
        truncated = True
        items = list(preview.items())
        while items and len(serialized) > _INLINE_OVERRIDE_PREVIEW_MAX_CHARS:
            items = items[:-1]
            preview = dict(items)
            serialized = json.dumps(preview, sort_keys=True, default=str)

    return preview, truncated

def _derive_lane(node: CodexNode) -> LaneEnum:
    """
    [ACTION]
    - Teleology: Map a `CodexNode` to a strict `LaneEnum` for UI zoning.
    - Preconditions: `node.id` is present; `node.lane` may be absent or invalid.
    - Guarantee: Returns a `LaneEnum`.
    """
    # 1. Trust the explicit lane on the node first
    if hasattr(node, "lane") and node.lane:
        try:
            return LaneEnum(node.lane.upper())
        except ValueError:
            pass 

    # 2. Fallback to ID-based detection
    nid = node.id.lower()
    if "stockgrid" in nid: return LaneEnum.STOCKGRID
    if "stock" in nid: return LaneEnum.STOCK
    if "etf" in nid: return LaneEnum.ETF
    if "macro" in nid: return LaneEnum.MACRO
    if "news" in nid: return LaneEnum.NEWS
    if "poly" in nid: return LaneEnum.POLYMARKET
    if "calc" in nid: return LaneEnum.CALCULATOR

    # 3. Default to Spine
    return LaneEnum.SPINE

def _extract_rich_data(node: CodexNode) -> dict:
    """
    [ACTION]
    - Teleology: Extract HUD metadata from a `CodexNode`.
    - Source of truth: Read execution/config metadata from canonical `CodexNode` fields.
    """
    meta = getattr(node, "meta", {})
    if not isinstance(meta, dict):
        meta = {}

    execution = getattr(node, "execution", {})
    if not isinstance(execution, dict):
        execution = {}

    tools_raw = execution.get("tools", [])
    tools = [str(tool) for tool in tools_raw] if isinstance(tools_raw, list) else []

    platform = getattr(node, "platform", None)
    if not platform:
        platform = meta.get("platform")

    instruction = str(getattr(node, "instruction", "") or meta.get("instruction", ""))
    contracts = normalize_contracts(meta.get("contracts"))
    if not contracts:
        contracts = extract_contract_fnames(instruction)

    config_ref = getattr(node, "config_ref", None)
    inline_overrides = getattr(node, "inline_overrides", None)
    merged_hash = getattr(node, "merged_hash", None)
    override_keys: Optional[List[str]] = None
    inline_preview: Optional[Dict[str, Any]] = None
    preview_truncated = False
    if isinstance(inline_overrides, dict):
        override_keys = sorted(str(key) for key in inline_overrides.keys())
        inline_preview, preview_truncated = _build_inline_override_preview(inline_overrides)
    provenance = None
    if config_ref or merged_hash or override_keys or inline_preview:
        provenance = ProvenanceView(
            config_ref=config_ref if isinstance(config_ref, str) else None,
            override_keys=override_keys,
            inline_overrides_preview=inline_preview,
            preview_truncated=preview_truncated,
            merged_hash=merged_hash if isinstance(merged_hash, str) else None,
        )

    return {
        "teleology": getattr(node, "teleology", "") or meta.get("teleology", "N/A"),
        "mechanism": getattr(node, "mechanism", "") or meta.get("mechanism", "Standard"),
        "expectation": getattr(node, "expectation", "") or meta.get("expectation", ""),
        "instruction": instruction,
        "dependencies": list(getattr(node, "dependencies", []) or []),
        "contracts": contracts,
        "timeout": execution.get("timeout"),
        "platform": platform,
        "tools": tools,
        "is_artifact": bool(getattr(node, "is_artifact", False)),
        "provenance": provenance,
    }

def compile_graph_snapshot(root_dir: Path, target_id: str, run_id: str) -> GraphSnapshot:
    """
    [ACTION]
    - Teleology: Produce the immutable UI snapshot for a single `target_id`.
    - Updates: Implements Group Closure Scoping and UPSTREAM zoning logic.
    - When-needed: Open when mission-graph debugging needs `compile_graph_snapshot` and the exact scoping, wave bucketing, and upstream zoning rules used by the backend snapshot.
    - Escalates-to: system/core/loader.py::PhysicalLoader; system/server/schemas.py::GraphSnapshot; system/server/main.py::get_mission_graph
    """
    try: loader = PhysicalLoader(root_dir, inject_sys_path=False)
    except Exception: loader = PhysicalLoader(root_dir)

    universe = loader.load_all_nodes()

    if target_id not in universe:
        return GraphSnapshot(
            run_id=run_id, timestamp=time.time(), root_id=target_id, nodes=[], edges=[],
            topology_error=TopologyError(details=f"Target node '{target_id}' not found.")
        )

    # 0. Identify Target Group
    target_node = universe[target_id]
    target_group = getattr(target_node, "group", "unknown")

    # 1. Scope: Group Closure + Upstream Walk
    # [LOCKED DECISION L5] Seed with ALL nodes in the target's group to capture disconnected siblings
    scope = set()
    queue = deque()

    for nid, node in universe.items():
        grp = getattr(node, "group", "unknown")
        if grp == target_group and target_group != "unknown":
            scope.add(nid)
            queue.append(nid)
    
    # Fallback: Ensure target is in scope if group logic fails
    if target_id not in scope:
        scope.add(target_id)
        queue.append(target_id)

    # Native scope is exactly the target group's closure before upstream BFS.
    native_scope = frozenset(scope)

    # BFS to pull in upstream dependencies (e.g., Feeds from outside the group)
    while queue:
        curr = queue.popleft()
        if curr in universe:
            for dep in universe[curr].dependencies:
                if dep not in scope:
                    scope.add(dep)
                    queue.append(dep)

    scoped_graph = {nid: universe[nid] for nid in scope}

    # 2. Waves (Topological Sort)
    adj = defaultdict(list)
    in_degree = {n: 0 for n in scope}
    for nid, node in scoped_graph.items():
        for dep in node.dependencies:
            if dep in scope:
                adj[dep].append(nid)
                in_degree[nid] += 1

    q = deque([n for n in scope if in_degree[n] == 0])
    waves = []
    while q:
        level_sz = len(q)
        current_wave = []
        for _ in range(level_sz):
            nid = q.popleft()
            current_wave.append(nid)
            for neighbor in adj[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0: q.append(neighbor)
        waves.append(sorted(current_wave))

    # 3. Build Views
    view_nodes = []

    for wave_idx, wave_nodes in enumerate(waves):
        for nid in wave_nodes:
            node = scoped_graph[nid]
            rich = _extract_rich_data(node)
            
            # --- ZONING LOGIC ---
            # Non-native nodes are upstream dependencies.
            # CRITICAL: We do NOT change the lane. The node must stay in its
            # native lane (e.g. STOCK) to align with the inputs of that lane.
            raw_group = getattr(node, "group", "default")
            final_group = raw_group
            is_upstream = nid not in native_scope
            source_group = raw_group

            view_nodes.append(NodeView(
                id=node.id,
                label=node.id,
                type="tool" if getattr(node, "type", None) and node.type.value == "tool" else "node",
                lane=_derive_lane(node),
                wave=wave_idx,
                group=final_group,
                
                # Rich Data Injection
                teleology=rich["teleology"],
                mechanism=rich["mechanism"],
                expectation=rich["expectation"],
                instruction=rich["instruction"],
                dependencies=rich["dependencies"],
                contracts=rich["contracts"],
                timeout=rich["timeout"],
                platform=rich["platform"],
                tools=rich["tools"],
                is_artifact=rich["is_artifact"],
                provenance=rich["provenance"],
                is_upstream=is_upstream,
                source_group=source_group
            ))

    view_edges = []
    for nid, node in scoped_graph.items():
        for dep in node.dependencies:
            if dep in scope:
                view_edges.append(EdgeView(id=f"{dep}->{nid}", source=dep, target=nid))

    return GraphSnapshot(
        run_id=run_id, timestamp=time.time(), root_id=target_id,
        nodes=view_nodes, edges=view_edges
    )

def compile_mission_view(root_dir: Path, target_id: str) -> GraphSnapshot:
    """
    [ACTION]
    - Teleology: Convenience wrapper to compile a mission preview `GraphSnapshot` for a `target_id`.
    - Preconditions: `root_dir` points at a valid repo; `target_id` is a node id.
    - Guarantee: Returns `compile_graph_snapshot(..., run_id="PREVIEW")`.
    - Fails: None (errors are surfaced inside the returned snapshot where applicable).
    - When-needed: Open when a route already resolved `target_id` and only needs the preview graph contract used by the mission UI.
    - Escalates-to: system/server/main.py::get_mission_graph; system/server/schemas.py::GraphView
    """
    return compile_graph_snapshot(root_dir, target_id, "PREVIEW")

def compile_physics_graph(root):
    """
    [ACTION]
    - Teleology: Legacy API placeholder for older clients expecting `/api/graph`.
    - Mechanism: Currently returns an empty object; real graph compilation is `compile_graph_snapshot`.
    - Guarantee: Returns `{}`.
    - Fails: None.
    - Non-goal: Producing a full physics graph (deprecated surface).
    - When-needed: Open when tracing why the legacy `/api/graph` surface returns a placeholder instead of the modern mission snapshot.
    - Escalates-to: system/server/main.py::get_graph; system/server/schemas.py::GraphView
    """
    return {}
