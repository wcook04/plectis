# agent_memory_temporal_conflict_replay Agent Memory Temporal Conflict Replay

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/agent_memory_temporal_conflict_replay.json`
- Atlas source of record: `core/organ_atlas.json::organs[36:agent_memory_temporal_conflict_replay]`
- Registry source of record: `core/organ_registry.json::implemented_organs[36:agent_memory_temporal_conflict_replay]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this against a synthetic fixture to see the shape of the memory-update bookkeeping it should produce: updates and deletes of older memory must carry temporal conflict-edge and stale-downgrade refs before they may affect a replay; private threads appear only as metadata-only refs with no exported body; and a memory-on replay must cite evidence handles while the memory-on/off pair is reconciled by an answer-delta receipt, not by final-answer comparison alone. It also confirms seven failure fixtures (raw transcript export, private-candidate auto-promotion, stale-preference override, memory-as-source-authority, vector recall without an evidence handle, final-answer-only credit, active-injection authority) are all rejected. It validates structure and receipt presence on fixture rows, not the correctness of any real memory system.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.agent_memory_temporal_conflict_replay` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.agent_memory_temporal_conflict_replay.validates_public_memory_conflict_replay` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/agent_memory_temporal_conflict_replay.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.agent_reliability_and_safety_validator_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-1` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `organ.wires_to.organ` -> residual pressure (Organ atlas row does not name sibling wires_to targets.)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
