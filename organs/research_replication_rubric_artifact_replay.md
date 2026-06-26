# research_replication_rubric_artifact_replay Research Replication Rubric Artifact Replay

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/research_replication_rubric_artifact_replay.json`
- Atlas source of record: `core/organ_atlas.json::organs[22:research_replication_rubric_artifact_replay]`
- Registry source of record: `core/organ_registry.json::implemented_organs[22:research_replication_rubric_artifact_replay]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs it to validate a replication-claim bundle: that the two synthetic paper capsules each carry all fourteen required evidence references (rubric tree, contribution decomposition, allowed-input refs, scaffold, experiment DAG, metric scripts, declared+actual artifact-hash refs, grader report, budget, ablation diff, failure taxonomy, cold-rerun receipt), that the policy forbids the prohibited shortcuts, and that all eight negative fixtures fire their expected error codes (author-code reuse, hidden-rubric leakage, report-only success, benchmark overclaim, private-body leak, unbounded compute, final-answer-only grading, undeclared artifact hash). It validates reference presence and receipt shape only; it does not execute the scripts, run a rerun, or call providers.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.research_replication_rubric_artifact_replay` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.research_replication_rubric_artifact_replay.validates_public_research_replication_replay` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/research_replication_rubric_artifact_replay.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.research_and_science_replay_evidence_bundle` (resolved_json_instance)
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
- `wires_to` -> `organ:materials_chemistry_closed_loop_lab_safety_replay` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:mechanistic_interpretability_circuit_attribution_replay` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:prediction_oracle_reconciliation` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:spatial_world_model_counterfactual_simulation_replay` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch10_cold_eval_honesty_capsule` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
