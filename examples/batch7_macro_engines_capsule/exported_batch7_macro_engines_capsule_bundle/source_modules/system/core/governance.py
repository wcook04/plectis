"""
[PURPOSE]
- Teleology: Act as the "Constitutional Court". Interpret JSON standards as executable law for Codex nodes and configs.
- Mechanism:
  1. Compile raw JSON standards into immutable `NodeStandard` rules.
  2. Enforce rules (keys, types, enums) on raw node data.
  3. Compute execution waves (Kahn's Algorithm).
  4. Audit configuration purity.
- Strictness: High. Enforces schema contracts strictly.
[INTERFACE]
- Exposes: `compile_standard`, `load_standards`, `parse_node`, `validate_graph`, `compute_waves`, `audit_config_purity`.
- Reads: Raw JSON standard dicts, raw node dicts, arbitrary config payloads.
- Writes: In-memory standards registry (`_STANDARDS_REGISTRY`).
- Returns: `NodeStandard` (optional), `CodexNode`, `List[ValidationIssue]`, `List[List[str]]`.
- Raises: `TypeError`, `ValueError`, `RuntimeError` on governance violations.
[FLOW]
1. `load_standards([...])` compiles and registers standards keyed by `NodeType`.
2. `parse_node(raw_node)` selects `NodeType`, enforces key/type/enum/role constraints, constructs `CodexNode`.
3. `validate_graph(nodes)` checks missing dependencies and detects cycles via `compute_waves`.
4. `audit_config_purity(payload)` walks payload and emits `ValidationIssue` for forbidden structural keys.
- When-needed: Open when the task is about node law, schema enforcement, dependency validation, or execution-wave computation for the core runtime.
- Escalates-to: system/core/loader.py::PhysicalLoader.load_node; system/core/analysis.py::configure_from_standard
- Navigation-group: system_core
[DEPENDENCIES]
- system.lib.types: CodexNode (type definitions)
- data.codex/standards: schema_validation (contract enforcement)
[CONSTRAINTS]
- Standards are the source of truth: forbidden keys are rejected when a standard exists.
- Tool nodes must include `config` as dict and must specify `config.module`.
- `lane` values, when present, must be within `VALID_LANES`.
- Config payloads must not contain structural/system keys (e.g., deps/dependencies/id/type/etc.).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple, Union

from system.lib.types import CodexNode, NodeType, NodeRole, ValidationIssue, VALID_LANES

# --- 1. Constitutional Models ---

@dataclass(frozen=True)
class NodeStandard:
    """
    [ROLE]
    - Teleology: Immutable executable "law" compiled from JSON standards.
    - Mechanism: Encodes allowed/required keys, enum constraints, and phase allowances per `NodeType`.
    """
    node_type: NodeType
    allowed_keys: Set[str]
    required_keys: Set[str]
    allowed_phases: Set[str]
    meta_schema: Dict[str, Any]
    enum_constraints: Mapping[str, Set[str]] = field(default_factory=dict)

# --- 2. Registry & Compilation ---

_STANDARDS_REGISTRY: Dict[NodeType, NodeStandard] = {}

def compile_standard(raw_std: Mapping[str, Any]) -> Optional[NodeStandard]:
    """
    [ACTION]
    - Teleology: Convert a raw JSON standard into an executable `NodeStandard`.
    - Mechanism: Infer `NodeType` from schema.type, compute allowed/required keys + enum constraints,
      and return a compiled `NodeStandard` (or `None` if the input does not describe a known node type).
    - When-needed: Open when a raw standard JSON payload needs to become the immutable rule object used by loader and graph validation paths.
    - Escalates-to: system/core/loader.py::PhysicalLoader.load_node; system/core/analysis.py::configure_from_standard
    """
    schema = dict(raw_std.get("schema", {}))
    
    # 1. Determine Type (Discriminator)
    # [SCORCHED EARTH] Treat schema.type as metadata, remove from rules
    type_def = str(schema.pop("type", "")).lower()
    
    if "tool" in type_def and "config" not in type_def: 
        n_type = NodeType.TOOL
    elif "reasoning" in type_def:
        n_type = NodeType.REASONING
    else:
        # Fallback if "const(tool)" style
        if "tool" in type_def:
            n_type = NodeType.TOOL
        else:
            return None 

    # 2. Key Analysis
    allowed = set() # Start empty, add only valid keys
    required = set()
    enums = {}
    phases = set()

    for key, rule in schema.items():
        # [FIX] Sanitization: Don't treat directive keys (containing parens) as field names
        if "(" in key and ")" in key:
            # This is a constraint directive (e.g. "enum(type)"), not a field
            pass
        else:
            allowed.add(key)
            rule_str = str(rule)
            is_optional = "optional" in rule_str or "default" in rule_str
            if not is_optional:
                required.add(key)

        # Parse constraints regardless of key type
        rule_str = str(rule)
        if isinstance(rule, str) and "enum(" in rule:
            match = re.search(r'enum\((.*?)\)', rule)
            if match:
                values = {v.strip() for v in match.group(1).split(',')}
                # Determine target key
                target_key = key
                if "(" in key:
                    # Extract target from key like "enum(type)" -> "type"
                    k_match = re.search(r'\((.*?)\)', key)
                    if k_match: target_key = k_match.group(1)
                
                enums[target_key] = values
                if target_key == "phase":
                    phases = values

    # Lane is always governed by VALID_LANES — the JSON enum string is documentation only
    enums["lane"] = set(VALID_LANES)

    # Force implicit keys
    allowed.add("id")
    required.add("id")
    
    allowed.add("type")
    required.add("type")

    # Implicit System Fields (Loader Injected or Common)
    # These fields are injected by the loader or are fundamental to system operation
    # and must be allowed even if not explicitly in the specific node standard.
    allowed.update({
        "dependencies", "group", "lane", "is_artifact",
        "platform", "teleology", "mechanism",
        "execution", "config", "instruction",
        "config_ref", "inline_overrides", "merged_hash",
        # Phase 2: execution ontology fields
        "output_schema", "boundary", "routing_class",
    })

    return NodeStandard(
        node_type=n_type,
        allowed_keys=allowed,
        required_keys=required,
        allowed_phases=phases,
        meta_schema=schema.get("meta", {}),
        enum_constraints=enums
    )

def load_standards(raw_standards_list: List[Mapping[str, Any]]) -> None:
    """
    [ACTION]
    - Teleology: Populate the in-memory standards registry used for constitutional enforcement.
    - Mechanism: Compile each raw standard and register by `NodeType`; hard-fail if core standards
      (TOOL and REASONING) are missing or malformed.
    - When-needed: Open when startup or tests need to understand how standards become the active governance registry.
    - Escalates-to: system/core/analysis.py::configure_from_standard; system/core/loader.py::PhysicalLoader.load_all_nodes
    """
    global _STANDARDS_REGISTRY
    compiled = {}
    for raw in raw_standards_list:
        try:
            std = compile_standard(raw)
            if std is not None:
                compiled[std.node_type] = std
        except Exception:
            continue
    _STANDARDS_REGISTRY = compiled
    
    # [SCORCHED EARTH] Hard Fail if core standards missing
    if NodeType.TOOL not in _STANDARDS_REGISTRY:
        raise RuntimeError("Governance Failure: Standard for TOOL nodes missing or malformed.")
    if NodeType.REASONING not in _STANDARDS_REGISTRY:
        raise RuntimeError("Governance Failure: Standard for REASONING nodes missing or malformed.")

def _get_standard(n_type: NodeType) -> NodeStandard:
    if n_type in _STANDARDS_REGISTRY:
        return _STANDARDS_REGISTRY[n_type]
    
    # [SCORCHED EARTH] Fallback matches the minimal types.py definition
    base_keys = set(CodexNode.__dataclass_fields__.keys())
    
    return NodeStandard(
        node_type=n_type,
        allowed_keys=base_keys,
        required_keys={"id", "type"},
        allowed_phases=set(), 
        meta_schema={},
        enum_constraints={}
    )

# --- 3. Node Parsing & Enforcement ---

def parse_node(raw: Mapping[str, Any]) -> CodexNode:
    """
    [ACTION]
    - Teleology: Convert raw node JSON into a validated `CodexNode`.
    - Mechanism: Determine `NodeType`, enforce key/type/enum constraints from standards, enforce tool-config
      requirements, validate lane + role enums, then construct the `CodexNode` in SAFE MODE.
    - When-needed: Open when a node payload failed constitutional validation or a caller needs the exact normalization path from raw JSON to `CodexNode`.
    - Escalates-to: system/core/loader.py::PhysicalLoader.load_node; system/core/analysis.py::analyze_python_module
    """
    if not isinstance(raw, Mapping):
        raise TypeError(f"Node definition must be a dict, got {type(raw).__name__}")
    
    data = dict(raw)
    nid = data.get("id", "unknown")

    # [SCORCHED EARTH] Defaults applied in code
    data.setdefault("dependencies", [])
    data.setdefault("meta", {})

    # A. Global Syntax Bans
    if "deps" in data:
        raise ValueError(f"Governance violation in '{nid}': Found 'deps'. Use 'dependencies'.")

    # B. Determine Type
    raw_type = data.get("type")
    target_type: NodeType
    if raw_type == "tool" or (isinstance(raw_type, str) and "tool" in raw_type):
        target_type = NodeType.TOOL
    elif raw_type == "reasoning" or (isinstance(raw_type, str) and "reasoning" in raw_type):
        target_type = NodeType.REASONING
    else:
        raise ValueError(f"Governance violation in '{nid}': Unknown 'type'. Got: {raw_type}")

    # [SCORCHED EARTH] Tool Config Enforcement
    if target_type == NodeType.TOOL:
        config = data.get("config")
        if not isinstance(config, dict):
             raise ValueError(f"Governance violation in '{nid}': Tool nodes must have a 'config' dict.")
        if "module" not in config:
             raise ValueError(f"Governance violation in '{nid}': Tool config must specify 'module'.")

    # [SCORCHED EARTH] Lane Validity
    lane = data.get("lane")
    if lane is not None and lane not in VALID_LANES:
         raise ValueError(f"Governance violation in '{nid}': Invalid lane '{lane}'. Must be one of {sorted(list(VALID_LANES))}.")

    # [FIX] Expectation Check removed to allow standards to drive optionality.
    # Expectation logic is now purely handled by 'required_keys' in the Standard.

    # C. Fetch Law
    std = _get_standard(target_type)

    # D. Constitutional Enforcement
    # 1. Unknown Keys
    actual_keys = set(data.keys())
    unknown_keys = actual_keys - std.allowed_keys
    if unknown_keys:
        raise ValueError(
            f"Governance violation in '{nid}' ({target_type.value}): "
            f"Forbidden keys {sorted(list(unknown_keys))}. "
            f"Allowed: {sorted(list(std.allowed_keys))}."
        )

    # 2. Required Keys
    missing_keys = std.required_keys - actual_keys
    if missing_keys:
        if _STANDARDS_REGISTRY: 
            raise ValueError(
                f"Governance violation in '{nid}' ({target_type.value}): "
                f"Missing required keys {sorted(list(missing_keys))}."
            )

    # 3. Enum Constraints
    for key, allowed_vals in std.enum_constraints.items():
        if key in data:
            val = data[key]
            val_str = str(val.value if hasattr(val, "value") else val)
            if val_str not in allowed_vals:
                raise ValueError(
                    f"Governance violation in '{nid}': Invalid '{key}' value '{val_str}'. "
                    f"Must be one of {sorted(list(allowed_vals))}."
                )

    # 4. Role Integrity (Strict UI Contract)
    meta = data.get("meta", {})
    if isinstance(meta, dict):
        role_raw = meta.get("role")
        if role_raw:
            # [FIX] Validate against NodeRole Enum
            try:
                NodeRole(role_raw)
            except ValueError:
                valid_roles = [e.value for e in NodeRole]
                raise ValueError(f"Governance violation in '{nid}': Invalid role '{role_raw}'. Must be one of {sorted(valid_roles)}.")

    # E. Construction (SAFE MODE)
    constructor_kwargs = {}
    valid_fields = set(CodexNode.__dataclass_fields__.keys())

    for k, v in data.items():
        if k not in valid_fields:
            continue

        if k == "dependencies":
            # [SCORCHED EARTH] Normalization
            if isinstance(v, list):
                constructor_kwargs[k] = tuple(str(x) for x in v)
            elif isinstance(v, str):
                constructor_kwargs[k] = (v,)
            elif isinstance(v, tuple):
                constructor_kwargs[k] = v
            else:
                constructor_kwargs[k] = tuple()
        else:
            constructor_kwargs[k] = v

    constructor_kwargs["type"] = target_type

    try:
        return CodexNode(**constructor_kwargs)
    except TypeError as e:
        raise ValueError(f"CodexNode construction failed for '{nid}': {e}") from e

# --- 4. Graph Topology ---

def validate_graph(nodes: Union[Mapping[str, CodexNode], Any]) -> List[ValidationIssue]:
    """
    [ACTION]
    - Teleology: Validate dependency integrity and cycle-freedom of a node graph.
    - Mechanism: Emit `ValidationIssue` for missing dependencies; detect cycles by attempting
      `compute_waves` (Kahn's algorithm) and converting cycle errors into graph issues.
    - When-needed: Open when checking whether a loaded graph is missing dependencies or contains a cycle before execution starts.
    - Escalates-to: system/core/loader.py::PhysicalLoader.validate_topology; system/core/engine.py::GodModeEngine.run
    """
    issues = []
    
    if hasattr(nodes, "values"):
        nodes_dict = nodes
    else:
        nodes_dict = {n.id: n for n in nodes}
    
    all_ids = set(nodes_dict.keys())

    # 1. Missing Dependencies
    for node_id, node in nodes_dict.items():
        deps = getattr(node, "dependencies", ()) or ()
        for dep in deps:
            if dep not in all_ids:
                issues.append(ValidationIssue(
                    node_id=node_id,
                    severity="error",
                    message=f"Missing dependency '{dep}'",
                    field="dependencies"
                ))

    # 2. Cycles
    try:
        compute_waves(nodes_dict)
    except ValueError as e:
        if "Cycle detected" in str(e):
             issues.append(ValidationIssue(
                node_id="GRAPH",
                severity="error",
                message=str(e),
                field="topology"
            ))
    
    return issues

validate_topology = validate_graph

def compute_waves(nodes: Mapping[str, CodexNode]) -> List[List[str]]:
    """
    [ACTION]
    - Teleology: Compute execution waves (topological layers) for dependency-ordered execution.
    - Mechanism: Apply Kahn's algorithm over the dependency graph; returns ordered layers of node IDs;
      raises `ValueError` if a cycle is detected.
    - When-needed: Open when execution ordering or cycle detection needs the authoritative topological-wave algorithm.
    - Escalates-to: system/core/engine.py::GodModeEngine.run; system/core/loader.py::PhysicalLoader.compute_waves
    """
    adj = {nid: [] for nid in nodes}
    in_degree = {nid: 0 for nid in nodes}
    
    for nid, node in nodes.items():
        deps = getattr(node, "dependencies", ()) or ()
        for dep in deps:
            if dep in adj: 
                adj[dep].append(nid)
                in_degree[nid] += 1
    
    queue = sorted([nid for nid, deg in in_degree.items() if deg == 0])
    waves = []
    
    count = 0
    while queue:
        current_wave = queue
        waves.append(current_wave)
        queue = []
        next_batch = []
        
        for nid in current_wave:
            count += 1
            for neighbor in adj[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_batch.append(neighbor)
        
        queue = sorted(next_batch)

    if count != len(nodes):
        raise ValueError("Cycle detected in dependency graph.")

    return waves

# --- 5. Config Purity ---

def audit_config_purity(data: Any, context: str = "config") -> List[ValidationIssue]:
    """
    [ACTION]
    - Teleology: Enforce "config purity" by banning structural/system keys inside config payloads.
    - Mechanism: Walk dict/list payloads depth-first, emitting `ValidationIssue` entries with
      precise field paths for each forbidden key encountered.
    - When-needed: Open when config payloads need a targeted audit for forbidden structural keys before loader or execution use them.
    - Escalates-to: system/core/loader.py::PhysicalLoader.load_node; system/core/analysis.py::analyze_python_module
    """
    # [SCORCHED EARTH] Removed 'expectation' from forbidden list as it is no longer a valid field anyway
    # output_schema is a structural execution parameter, not an LLM runtime parameter (Phase 2)
    FORBIDDEN_IN_CONFIG = {
        "deps", "dependencies", "instruction", "teleology", "mechanism", "id", "type", "phase",
        "output_schema",
    }
    
    issues = []
    
    def _walk(obj, path):
        if isinstance(obj, dict):
            for k, v in obj.items():
                curr_path = f"{path}.{k}" if path else k
                if k in FORBIDDEN_IN_CONFIG:
                    issues.append(ValidationIssue(
                        node_id="CONFIG",
                        severity="error",
                        message=f"Forbidden key '{k}' found in config payload.",
                        field=curr_path
                    ))
                _walk(v, curr_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _walk(item, f"{path}[{i}]")

    _walk(data, context)
    return issues
