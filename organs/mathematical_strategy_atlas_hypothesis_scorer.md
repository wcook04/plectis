# mathematical_strategy_atlas_hypothesis_scorer Mathematical Strategy Atlas Hypothesis Scorer

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/mathematical_strategy_atlas_hypothesis_scorer.json`
- Atlas source of record: `core/organ_atlas.json::organs[5:mathematical_strategy_atlas_hypothesis_scorer]`
- Registry source of record: `core/organ_registry.json::implemented_organs[5:mathematical_strategy_atlas_hypothesis_scorer]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to deterministically pick a pre-proof strategy hypothesis and retrieval terms from problem feature tags (highest feature overlap wins; zero overlap becomes a typed strategy-selection miss), and to check that unknown strategy ids, proof bodies, oracle labels, post-oracle selection, and release/proof/provider overclaims are all rejected.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.mathematical_strategy_atlas` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.mathematical_strategy_atlas_hypothesis_scorer.validates_public_strategy_hypothesis_projection` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/mathematical_strategy_atlas_hypothesis_scorer.py` (resolved_code_locus)
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
- `organ.wires_to.organ` -> residual pressure (Organ atlas row does not name sibling wires_to targets.)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
