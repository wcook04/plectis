# formal_math_premise_retrieval Formal Math Premise Retrieval

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/formal_math_premise_retrieval.json`
- Atlas source of record: `core/organ_atlas.json::organs[9:formal_math_premise_retrieval]`
- Registry source of record: `core/organ_registry.json::implemented_organs[9:formal_math_premise_retrieval]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs the first-wave fixture (`run` mode, which includes the negative inputs) to replay term-scored premise retrieval over the copied index and confirm that all five guards — proof-body leakage, oracle/answer-key ids, context-budget overflow, test-split tuning, and unknown-strategy-id — observe and block their planted negative cases (expected == observed, none missing). The separate `run-retrieval-bundle` mode replays only the positive retrieval demo and does not exercise the negative cases.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.formal_math_premise_retrieval` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.formal_math_premise_retrieval.validates_public_premise_retrieval_projection` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/formal_math_premise_retrieval.py` (resolved_code_locus)
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
- `wires_to` -> `organ:formal_math_lean_proof_witness` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:formal_math_verifier_trace_repair_loop` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:lean_std_premise_index` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:verifier_lab_kernel` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:mathematical_strategy_atlas_hypothesis_scorer` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:ring2_premise_retrieval_precision_recall_harness` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
