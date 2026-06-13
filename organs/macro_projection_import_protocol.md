# macro_projection_import_protocol Macro Projection Import Protocol

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/macro_projection_import_protocol.json`
- Atlas source of record: `core/organ_atlas.json::organs[30:macro_projection_import_protocol]`
- Registry source of record: `core/organ_registry.json::implemented_organs[30:macro_projection_import_protocol]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to preview or validate a projection bundle before import: confirm each proposed cell has source and public-target refs, a matching content digest, omission receipts for any withheld private material, a body-free receipt contract, and an authority ceiling that stays capped below release. Use `plan` for a no-write preview (emits the intake-preview schema and per-cell ready/blocked status); use `run-projection-bundle` to validate-and-record.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.macro_projection_import_protocol` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.macro_projection_import_protocol.validates_public_macro_projection_imports` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/macro_projection_import_protocol.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.import_projection_and_drift_control_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-14` (resolved_json_instance)
- `governed_by` -> `principle:P-15` (resolved_json_instance)
- `governed_by` -> `principle:P-17` (resolved_json_instance)
- `governed_by` -> `principle:P-18` (resolved_json_instance)
- `governed_by` -> `principle:P-5` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-4` (resolved_json_instance)
- `wires_to` -> `organ:formal_math_readiness_gate` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:agent_route_observability_runtime` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:mission_transaction_work_spine` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:navigation_hologram_route_plane` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:pattern_binding_contract` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:materials_chemistry_closed_loop_lab_safety_replay` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch11_saturation_engines_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch8_compliance_pipeline_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch10_frontend_work_market_cockpit_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch10_governance_compilers_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch10_live_source_drift_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch4_proof_authority_runtime` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch5_authority_systems_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch6_unsurfaced_primitives_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch7_macro_engines_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch7_oracle_sibling_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch7_secondary_runtime_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch8_audio_level_rms_port` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch8_policy_engines_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch9_macro_engines_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:concurrency_mission_control` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:workstream_driver_recency_coalescer` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
