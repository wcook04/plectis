# sleeper_memory_poisoning_quarantine_replay Sleeper Memory Poisoning Quarantine Replay

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/sleeper_memory_poisoning_quarantine_replay.json`
- Atlas source of record: `core/organ_atlas.json::organs[37:sleeper_memory_poisoning_quarantine_replay]`
- Registry source of record: `core/organ_registry.json::implemented_organs[37:sleeper_memory_poisoning_quarantine_replay]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to check that a synthetic memory-poisoning handling record has all the required pieces (provenance-bound write proposals, a quarantine verdict on the untrusted poisoned source, a retrieval-blocked-before-action gate, and a rollback with a deletion-audit ref plus a cold-rerun receipt marking the memory absent), that a body-free private-state scan finds no leaks, and that all eight known bad patterns (e.g. private-body export, live-user-memory claim, trusted promotion from untrusted context, deletion without audit) are each rejected with the expected error codes.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.sleeper_memory_poisoning_quarantine_replay` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.sleeper_memory_poisoning_quarantine_replay.validates_public_sleeper_memory_poisoning_quarantine_replay` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/sleeper_memory_poisoning_quarantine_replay.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.agent_reliability_and_safety_validator_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-14` (resolved_json_instance)
- `governed_by` -> `principle:P-9` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-8` (resolved_json_instance)
- `organ.wires_to.organ` -> residual pressure (Organ atlas row does not name sibling wires_to targets.)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
