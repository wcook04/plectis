# AX-9 Compensable transactional effects

_Generated from the governed axiom JSON instance. Do not edit this markdown by hand._

- Source JSON: `axioms/AX-9.json`
- Routing source of record: `core/axiom_organ_routing.json::rows[8:AX-9]`
- Authority boundary: Active JSON record synchronized from routing registry; source authority has not flipped.

## Formal Clause

Effect e requires a compensator or declared irreversible boundary; multi-step effects land as saga with CAS and single-writer constraints.

## Lattice Neighbours

- `grounds` -> `principle:P-10` (resolved_json_instance)
- `grounds` -> `principle:P-16` (resolved_json_instance)
- `grounds` -> `principle:P-17` (resolved_json_instance)
- `grounds` -> `principle:P-18` (resolved_json_instance)
- `guarded_by` -> `anti_principle:AP-8` (resolved_json_instance)
- `witnessed_by` -> `organ:mission_transaction_work_spine` (resolved_registry_or_atlas_target)
- `witnessed_by` -> `organ:durable_agent_work_landing_replay` (resolved_registry_or_atlas_target)
- `witnessed_by` -> `organ:concurrency_mission_control` (resolved_registry_or_atlas_target)

## Support

Support is computed by `validator.microcosm.axiom_support_cover`; this markdown does not assert support.

## Anti-Claims

- This active axiom JSON record does not flip source authority away from core/axiom_organ_routing.json.
- Legacy witness_strength is not a computed support verdict.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
- Axiom admission as law does not prove that the axiom is witnessed, enforced, strong, or complete.
