# ring2_premise_retrieval_precision_recall_harness Ring2 Premise Retrieval Precision Recall Harness

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/ring2_premise_retrieval_precision_recall_harness.json`
- Atlas source of record: `core/organ_atlas.json::organs[13:ring2_premise_retrieval_precision_recall_harness]`
- Registry source of record: `core/organ_registry.json::implemented_organs[13:ring2_premise_retrieval_precision_recall_harness]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to compute per-problem precision@k / recall@k over copied Ring-2 retrieval rankings and bucket each problem into retrieval_hit / partial_retrieval_miss / retrieval_miss / proof_failure_despite_hit, plus aggregate hit-over-candidate precision and hit-over-needed recall. The validator emits blocking findings (status blocked, non-zero exit) for oracle/needed premise ids planted in rankings, leaked proof/provider/private body fields, test-split tuning flags, metric overclaims (proof/benchmark/provider/release authority), a missing adversarial-decoy case, incomplete copied-material provenance, and source-artifact digest mismatches; receipts carry import ids/digests only, never proof bodies.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.ring2_premise_precision_recall` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.ring2_premise_retrieval_precision_recall_harness.validates_public_premise_retrieval_attribution` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/ring2_premise_retrieval_precision_recall_harness.py` (resolved_code_locus)
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
- `wires_to` -> `organ:mathematical_strategy_atlas_hypothesis_scorer` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:verifier_lab_kernel` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
