# mechanism.mcp_tool_authority_replay.validates_public_mcp_tool_authority_replay validates public mcp tool authority replay

_Generated from the governed mechanism JSON instance. Do not edit this markdown by hand._

- Source JSON: `mechanisms/mechanism.mcp_tool_authority_replay.validates_public_mcp_tool_authority_replay.json`
- Registry source of record: `core/mechanism_sources.json::mechanisms[79:mechanism.mcp_tool_authority_replay.validates_public_mcp_tool_authority_replay]`
- Authority boundary: JSON parity seed; mechanism registry source authority has not flipped.

## Statement

The MCP tool authority replay organ validates public tool manifest scope, call metadata, approval token refs, side-effect ledger refs, rollback and cold-replay receipts, untrusted-output instruction/data separation, source-module digest anchors, negative cases, body-free receipts, and authority ceilings without accessing live MCP accounts, exporting credentials or provider payloads, obeying tool output as instruction, claiming benchmark safety, mutating source, or authorizing release.

## Lattice Neighbours

- `grounded_in` -> `code_locus:src/microcosm_core/organs/mcp_tool_authority_replay.py` (resolved_code_locus)
- `runs_in` -> `organ:mcp_tool_authority_replay` (resolved_registry_or_atlas_target)
- `grounds` -> `concept:concept.agent_reliability_and_safety_validator_bundle` (resolved_json_instance)
- `upstream_of` -> `mechanism:mechanism.agent_sandbox_policy_escape_replay.validates_public_sandbox_policy_trace` (resolved_json_instance)

## Anti-Claims

- This mechanism JSON seed does not flip source authority away from core/mechanism_sources.json.
- Resolved code-locus paths prove filesystem grounding only, not runtime correctness or release readiness.
- Absent concept or sibling mechanism edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
