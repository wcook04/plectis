# Agent Sabotage Scheming-Monitor Replay

`agent_sabotage_scheming_monitor_replay` is a drilldown-only regression contract for synthetic sabotage/scheming monitor claims. It asks a narrow question: does a public claim have episode metadata, action traces, per-step monitor scores, counterfactual benign replay, cold replay, falsification fixtures, body-free fixture refs, and an explicit authority ceiling?

## Runnable Path

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.agent_sabotage_scheming_monitor_replay run --input fixtures/first_wave/agent_sabotage_scheming_monitor_replay/input --out receipts/first_wave/agent_sabotage_scheming_monitor_replay --acceptance-out receipts/acceptance/first_wave/agent_sabotage_scheming_monitor_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli agent-sabotage-scheming-monitor-replay run-sabotage-bundle --input examples/agent_sabotage_scheming_monitor_replay/exported_sabotage_monitor_bundle --out receipts/runtime_shell/demo_project/organs/agent_sabotage_scheming_monitor_replay
```

## Contract

- Input shape: `projection_protocol`, `scheming_monitor_policy`, `task_episodes`, `action_traces`, `monitor_scores`, `counterfactual_replay`, and `cold_replay`.
- Positive evidence: three synthetic episodes, six action rows, six monitor-score rows, three counterfactual replays, and three cold replay rows.
- Negative cases: live sabotage instruction, real credentials/accounts, exploit instruction material, private chain-of-thought export, raw harmful payload export, monitor-only final grading, and deployment scare-story claim.
- Receipt boundary: the validation receipt proves only the body-free synthetic replay contract, negative-case coverage, private-state scan, and authority ceiling.
- Authority ceiling: no live sabotage, exploit instruction, credential/account material, private reasoning, harmful payload, deployment-risk product claim, provider call, source mutation, or release authority.

## Projection Protocol

Copied: the public shape of a scheming-monitor replay and the idea that monitor disagreement must fail closed.

Reimplemented: local JSON validators, body-free synthetic fixtures, counterfactual replay checks, and receipt generation.

Cleaned: private bodies, raw action payloads, provider data, credentials, and any live-agent traffic.

Omitted: private chain-of-thought, live sabotage details, real account identifiers, actionable exploit steps, raw harmful payloads, and production telemetry.

Public regression fixture refs: a synthetic fixture bundle plus generated receipts under `receipts/first_wave/agent_sabotage_scheming_monitor_replay/`.

Validation proves the projection boundary for this contract; it does not prove real model scheming detection, production monitor performance, benchmark scores, or whole-system safety.
