# agent_closeout_faithfulness_audit Agent Closeout Faithfulness Audit

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/agent_closeout_faithfulness_audit.json`
- Atlas source of record: `core/organ_atlas.json::organs[49:agent_closeout_faithfulness_audit]`
- Registry source of record: `core/organ_registry.json::implemented_organs[49:agent_closeout_faithfulness_audit]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

Use this to audit closeout receipts for evidence-existence and explicit pytest pass-status boundaries; fake commit, fake cap, and fake test claims are rejected by stable negative cases.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.agent_closeout_faithfulness_audit` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.agent_closeout_faithfulness_audit.validates_closeout_evidence_claims` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/agent_closeout_faithfulness_audit.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.agent_reliability_and_safety_validator_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-1` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `organ.wires_to.organ` -> residual pressure (Organ atlas row does not name sibling wires_to targets.)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
