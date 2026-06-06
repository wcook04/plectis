# corpus_readiness_mathlib_absence_gate Corpus Readiness Mathlib Absence Gate

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/corpus_readiness_mathlib_absence_gate.json`
- Atlas source of record: `core/organ_atlas.json::organs[4:corpus_readiness_mathlib_absence_gate]`
- Registry source of record: `core/organ_registry.json::implemented_organs[4:corpus_readiness_mathlib_absence_gate]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs it to check, against copied non-secret readiness rows, whether the recorded Mathlib import probe passed and therefore which consumer cases are allowed versus blocked before routing proof or premise work. It validates and projects the recorded accounting only; it does not itself import Mathlib, run Lean, or prove anything.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.corpus_readiness_mathlib_absence` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.corpus_readiness_mathlib_absence_gate.validates_public_mathlib_absence_boundary` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/corpus_readiness_mathlib_absence_gate.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.formal_math_and_proof_witness_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-8` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-7` (resolved_json_instance)
- `wires_to` -> `organ:verifier_lab_kernel` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:tactic_portfolio_availability_probe` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:undeclared_library_prior_symbol_classifier` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:formal_math_lean_proof_witness` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
