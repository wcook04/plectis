# bounded_autonomy_campaign_packet Bounded Autonomy Campaign Packet

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/bounded_autonomy_campaign_packet.json`
- Atlas source of record: `core/organ_atlas.json::organs[52:bounded_autonomy_campaign_packet]`
- Registry source of record: `core/organ_registry.json::implemented_organs[52:bounded_autonomy_campaign_packet]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

Use this to emit bounded self-proposal packets and reject source-write campaign packets or repeated failed campaign digests.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.bounded_autonomy_campaign_packet` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.bounded_autonomy_campaign_packet.validates_public_bounded_autonomy_campaign_packet` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/bounded_autonomy_campaign_packet.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.agent_reliability_and_safety_validator_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-1` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `governed_by` -> `principle:P-3` (resolved_json_instance)
- `governed_by` -> `principle:P-6` (resolved_json_instance)
- `governed_by` -> `principle:P-8` (resolved_json_instance)
- `governed_by` -> `principle:P-15` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-2` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-5` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-7` (resolved_json_instance)
- `organ.wires_to.organ` -> residual pressure (Organ atlas row does not name sibling wires_to targets.)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
