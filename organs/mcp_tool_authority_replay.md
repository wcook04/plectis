# mcp_tool_authority_replay MCP Tool Authority Replay

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/mcp_tool_authority_replay.json`
- Atlas source of record: `core/organ_atlas.json::organs[38:mcp_tool_authority_replay]`
- Registry source of record: `core/organ_registry.json::implemented_organs[38:mcp_tool_authority_replay]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to check that a recorded tool-use bundle is admissible: every call has a narrow scope ref, writes carry approval plus ledger plus rollback refs, untrusted output is treated as data not instruction, cold-replay receipts exist, payloads/account refs stay metadata-only, and all eight expected negative-abuse cases fire. It validates presence and consistency of this evidence only; it does not run tools, hit providers, or authorize anything.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.mcp_tool_authority_replay` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.mcp_tool_authority_replay.validates_public_mcp_tool_authority_replay` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/mcp_tool_authority_replay.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.agent_reliability_and_safety_validator_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-16` (resolved_json_instance)
- `governed_by` -> `principle:P-18` (resolved_json_instance)
- `governed_by` -> `principle:P-4` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-3` (resolved_json_instance)
- `wires_to` -> `organ:agent_sandbox_policy_escape_replay` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
