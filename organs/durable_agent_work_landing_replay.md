# durable_agent_work_landing_replay Durable Agent Work Landing Replay

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/durable_agent_work_landing_replay.json`
- Atlas source of record: `core/organ_atlas.json::organs[21:durable_agent_work_landing_replay]`
- Registry source of record: `core/organ_registry.json::implemented_organs[21:durable_agent_work_landing_replay]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this over recorded work-landing rows to confirm they satisfy the declared contract (each row cites owned claimed paths and owner-native validation refs; validation precedes the commit attempt; a "committed-landed" claim carries a declared HEAD-before != HEAD-after advance; metadata-blocked rows capture a blocker ref; Work Ledger closeout is cited) and to confirm the fixture's nine negative rows are each rejected with their expected error codes. It validates the recorded contract only; it does not execute Git or prove real-world landedness.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.durable_agent_work_landing_replay` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.durable_agent_work_landing_replay.validates_public_work_landing_replay_contract` (unresolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/durable_agent_work_landing_replay.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.work_landing_and_continuity_control_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-10` (resolved_json_instance)
- `governed_by` -> `principle:P-14` (resolved_json_instance)
- `governed_by` -> `principle:P-15` (resolved_json_instance)
- `governed_by` -> `principle:P-16` (resolved_json_instance)
- `governed_by` -> `principle:P-17` (resolved_json_instance)
- `governed_by` -> `principle:P-18` (resolved_json_instance)
- `governed_by` -> `principle:P-5` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-4` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-9` (resolved_json_instance)
- `wires_to` -> `organ:agent_closeout_faithfulness_audit` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:macro_projection_import_protocol` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
