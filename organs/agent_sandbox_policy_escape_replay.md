# agent_sandbox_policy_escape_replay Agent Sandbox Policy Escape Replay

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/agent_sandbox_policy_escape_replay.json`
- Atlas source of record: `core/organ_atlas.json::organs[41:agent_sandbox_policy_escape_replay]`
- Registry source of record: `core/organ_registry.json::implemented_organs[41:agent_sandbox_policy_escape_replay]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to validate that a sandbox-policy fixture has pre-execution policy verdicts on every one of the six action requests, body-free side-effect/rollback/cold-replay receipts (4 blocked with zero side effects, 2 executed with verified rollback), a public agent-execution trace span per request, and that the eight escape negative cases (real_secret_material, live_network_access, raw_environment_export, policy_after_execution, unlogged_side_effect, tool_output_policy_bypass, executable_escape_payload, security_benchmark_claim) all trip. Validation covers projection/trace-refactor mechanics over a synthetic fixture only.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.agent_sandbox_policy_escape_replay` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.agent_sandbox_policy_escape_replay.validates_public_sandbox_policy_trace` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/agent_sandbox_policy_escape_replay.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.agent_reliability_and_safety_validator_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-1` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `wires_to` -> `organ:sleeper_memory_poisoning_quarantine_replay` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
