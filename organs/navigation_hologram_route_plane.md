# navigation_hologram_route_plane Navigation Hologram Route Plane

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/navigation_hologram_route_plane.json`
- Atlas source of record: `core/organ_atlas.json::organs[19:navigation_hologram_route_plane]`
- Registry source of record: `core/organ_registry.json::implemented_organs[19:navigation_hologram_route_plane]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs it to confirm a fixture's route-plane contract holds and that browse rows stay projections, not authority. The fixture run exercises eight expected negative cases and confirms each is detected: (1) stale source coupling bundled with a banned first-contact drilldown route, (2) a route card missing its omission receipt, (3) an atlas projection claiming control-entry authority, (4) a route card leaking private body content, (5) a route summary overclaiming freshness while coupling is stale, (6) a duplicate route id, (7) entry-payload compaction dropping a required control-floor field, and (8) an affordance-passport anti-trigger row that must be demoted before similarity can select it. A separate validate-route-plane-bundle subcommand additionally checks copied source-module digests and required anchors plus a secret-exclusion scan, with all body text kept out of the receipts.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.navigation_hologram_route_plane` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.navigation_hologram_route_plane.validates_public_route_plane_bundle` (unresolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/navigation_hologram_route_plane.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.architecture_and_navigation_route_contract_bundle` (resolved_json_instance)
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
- `wires_to` -> `organ:cold_reader_route_map` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:agent_route_observability_runtime` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:routing_anti_patterns_registry` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:pattern_binding_contract` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:doctrine_fact_claim_audit` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:macro_projection_import_protocol` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:self_ignorance_coverage_ledger` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:voice_to_doctrine_self_improvement_loop` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:engine_room_demo` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch11_saturation_engines_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch8_compliance_pipeline_capsule` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
