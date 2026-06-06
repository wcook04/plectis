# mechanism.agent_monitor_redteam_falsification_replay.validates_public_monitor_verdict_receipts validates public monitor verdict receipts

_Generated from the governed mechanism JSON instance. Do not edit this markdown by hand._

- Source JSON: `mechanisms/mechanism.agent_monitor_redteam_falsification_replay.validates_public_monitor_verdict_receipts.json`
- Registry source of record: `core/mechanism_sources.json::mechanisms[6:mechanism.agent_monitor_redteam_falsification_replay.validates_public_monitor_verdict_receipts]`
- Authority boundary: JSON parity seed; mechanism registry source authority has not flipped.

## Statement

The agent monitor redteam falsification replay organ validates public monitor-verdict evidence shape by checking trajectory rosters, suspicious-span refs, adversarial-probe refs, escalation refs, body-omission refs, mitigation refs, cold-replay refs, public trace recomputation, source-module manifest boundaries, and falsification negative cases before writing bounded receipts.

## Lattice Neighbours

- `grounded_in` -> `code_locus:src/microcosm_core/organs/agent_monitor_redteam_falsification_replay.py` (resolved_code_locus)
- `runs_in` -> `organ:agent_monitor_redteam_falsification_replay` (resolved_registry_or_atlas_target)
- `grounds` -> `concept:concept.agent_reliability_and_safety_validator_bundle` (resolved_json_instance)
- `upstream_of` -> `mechanism:mechanism.agent_sabotage_scheming_monitor_replay.validates_public_sabotage_scheming_monitor_replay` (resolved_json_instance)

## Anti-Claims

- This mechanism JSON seed does not flip source authority away from core/mechanism_sources.json.
- Resolved code-locus paths prove filesystem grounding only, not runtime correctness or release readiness.
- Absent concept or sibling mechanism edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
