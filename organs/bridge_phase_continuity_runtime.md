# bridge_phase_continuity_runtime Bridge Phase Continuity Runtime

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/bridge_phase_continuity_runtime.json`
- Atlas source of record: `core/organ_atlas.json::organs[27:bridge_phase_continuity_runtime]`
- Registry source of record: `core/organ_registry.json::implemented_organs[27:bridge_phase_continuity_runtime]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs it to confirm, against a public synthetic fixture, that detached-job continuity rules hold before relying on them: a resumable job needs a continuation packet, a packet resumes exactly once (duplicate resume is rejected), heartbeats are liveness-only (and stale heartbeats are not live-health evidence), resource pressure blocks dispatch as a recorded decision, worker-skip rows dedupe without silently closing a claim, and only a closeout transition receipt marks work as landed. Each rule is exercised by a matching negative case.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.bridge_phase_continuity_runtime` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.bridge_phase_continuity_runtime.validates_synthetic_bridge_continuity` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/bridge_phase_continuity_runtime.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.work_landing_and_continuity_control_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-1` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `governed_by` -> `principle:P-3` (resolved_json_instance)
- `governed_by` -> `principle:P-5` (resolved_json_instance)
- `governed_by` -> `principle:P-6` (resolved_json_instance)
- `governed_by` -> `principle:P-8` (resolved_json_instance)
- `governed_by` -> `principle:P-9` (resolved_json_instance)
- `governed_by` -> `principle:P-12` (resolved_json_instance)
- `governed_by` -> `principle:P-15` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-4` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-5` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-7` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-8` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-11` (resolved_json_instance)
- `wires_to` -> `organ:concurrency_mission_control` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:workstream_driver_recency_coalescer` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
