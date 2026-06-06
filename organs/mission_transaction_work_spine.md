# mission_transaction_work_spine Mission Transaction Work Spine

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/mission_transaction_work_spine.json`
- Atlas source of record: `core/organ_atlas.json::organs[20:mission_transaction_work_spine]`
- Registry source of record: `core/organ_registry.json::implemented_organs[20:mission_transaction_work_spine]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs it to confirm that the projected work-landing, claim, checkpoint-lane, and Work Ledger seed-speed source-import metadata obeys the expected rules and emits the expected blocking error codes (e.g. SAME_PATH_CLAIM_CONFLICT, EXPECTED_PARENT_MISMATCH, PREFLIGHT_PASS_OVERCLAIMS_WORK_LANDED) before treating any change as landed.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.mission_transaction_work_spine` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.mission_transaction_work_spine.validates_public_mission_transaction_bundle` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/mission_transaction_work_spine.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.work_landing_and_continuity_control_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-10` (resolved_json_instance)
- `governed_by` -> `principle:P-16` (resolved_json_instance)
- `governed_by` -> `principle:P-17` (resolved_json_instance)
- `governed_by` -> `principle:P-18` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-9` (resolved_json_instance)
- `wires_to` -> `organ:bounded_autonomy_campaign_packet` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:concurrency_mission_control` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:macro_projection_import_protocol` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:tool_server_pressure_inventory` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch10_live_source_drift_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch4_proof_authority_runtime` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch8_tools_tail_primitives_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:agent_benchmark_integrity_anti_gaming_replay` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:agentic_vulnerability_discovery_patch_proof_replay` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
