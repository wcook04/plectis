# undeclared_library_prior_symbol_classifier Undeclared Library Prior Symbol Classifier

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/undeclared_library_prior_symbol_classifier.json`
- Atlas source of record: `core/organ_atlas.json::organs[12:undeclared_library_prior_symbol_classifier]`
- Registry source of record: `core/organ_registry.json::implemented_organs[12:undeclared_library_prior_symbol_classifier]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs it over symbol-observation rows whose qualified references are already extracted, scoring each known symbol against the allowed premise set and getting a classification: UNDECLARED_LIBRARY_PRIOR (route bridge_escalate) when a known library symbol is outside the allowed ids, or PREMISE_BUDGET_VIOLATION (route retry) which takes precedence when cited-unallowed ids are present. It also emits a secret-exclusion scan confirming no proof bodies, private source refs, oracle ids, or provider payloads entered the receipts.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.undeclared_library_prior_classifier` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.undeclared_library_prior_symbol_classifier.validates_public_symbol_boundary` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/undeclared_library_prior_symbol_classifier.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.formal_math_and_proof_witness_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-1` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `governed_by` -> `principle:P-3` (resolved_json_instance)
- `governed_by` -> `principle:P-6` (resolved_json_instance)
- `governed_by` -> `principle:P-8` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-2` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-5` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-7` (resolved_json_instance)
- `wires_to` -> `organ:corpus_readiness_mathlib_absence_gate` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:tactic_portfolio_availability_probe` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:provider_context_recipe_budget_policy` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
