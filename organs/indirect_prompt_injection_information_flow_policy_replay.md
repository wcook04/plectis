# indirect_prompt_injection_information_flow_policy_replay Indirect Prompt Injection Information Flow Policy Replay

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/indirect_prompt_injection_information_flow_policy_replay.json`
- Atlas source of record: `core/organ_atlas.json::organs[42:indirect_prompt_injection_information_flow_policy_replay]`
- Registry source of record: `core/organ_registry.json::implemented_organs[42:indirect_prompt_injection_information_flow_policy_replay]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs it to confirm that, in this replayed synthetic episode, every recorded flow from untrusted source text to a privileged action was gated (blocked, sent to review, or sanitized) before the action, and that the recorded outputs disclosed no trusted context or credential. Evidence is the validated fixture rows plus a body-free agent-execution trace, not a live agent run or a general robustness guarantee.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.indirect_prompt_injection_information_flow_policy_replay` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.indirect_prompt_injection_information_flow_policy_replay.validates_public_indirect_prompt_injection_information_flow_policy_replay` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/indirect_prompt_injection_information_flow_policy_replay.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.agent_reliability_and_safety_validator_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-14` (resolved_json_instance)
- `governed_by` -> `principle:P-9` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-8` (resolved_json_instance)
- `organ.wires_to.organ` -> residual pressure (Organ atlas row does not name sibling wires_to targets.)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
