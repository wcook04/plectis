# provider_context_recipe_budget_policy Provider Context Recipe Budget Policy

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/provider_context_recipe_budget_policy.json`
- Atlas source of record: `core/organ_atlas.json::organs[15:provider_context_recipe_budget_policy]`
- Registry source of record: `core/organ_registry.json::implemented_organs[15:provider_context_recipe_budget_policy]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to validate that its planned provider-context recipes respect their fixed byte budgets, fill sections in declared order under those budgets, emit an omitted-sections manifest whenever something is dropped, and route to the correct deliverable type, while rejecting any recipe that authorizes a provider call or carries truth-side, oracle, or proof-body material. It also digest-checks the copied standard/source-module bodies it ships. Output is context metadata and verdicts only.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.provider_context_recipe_budget` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.provider_context_recipe_budget_policy.validates_public_context_budget_boundary` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/provider_context_recipe_budget_policy.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.agent_reliability_and_safety_validator_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-1` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `governed_by` -> `principle:P-3` (resolved_json_instance)
- `governed_by` -> `principle:P-6` (resolved_json_instance)
- `governed_by` -> `principle:P-8` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-2` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-5` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-7` (resolved_json_instance)
- `wires_to` -> `organ:bounded_autonomy_campaign_packet` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:tool_server_pressure_inventory` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
