# Replay monitor evidence and counterfactuals

> **In plain terms.** A watching program labels each episode of an automated assistant's work as caught or not caught for pursuing a hidden side goal. This component is given recorded episodes, the watcher's scores, the assistant's actions and the evidence behind each label. It compares each episode with a rerun that has no side goal but the same main job, and checks that the difference points to the step tied to the side goal. It lists findings, such as an outdated caught label or a comparison that misses that step, so a reader can judge each label. These example records test only the chain of evidence, so they say nothing about how often a real watcher would succeed.

This replay checks whether recorded monitor scores and action steps support declared caught or not-caught verdicts. It joins episodes, action traces and evidence references, then compares the recorded episode with a benign replay where the agent’s side objective is removed while its main task is preserved. It also checks cold-replay references and source-artifact digests.

A stale caught label or a counterfactual that fails to isolate the step associated with that side objective is rejected. These public records are bounded examples for checking the evidence chain. They do not implement a deployed scheming detector or establish its detection rate, and matching source hashes do not establish algorithm correctness.

## Run the example

From the repository root, with Python 3.11 or newer and the repository dependencies available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.agent_sabotage_scheming_monitor_replay \
  run --input fixtures/first_wave/agent_sabotage_scheming_monitor_replay/input \
  --out .microcosm/component-guides/agent_sabotage_scheming_monitor_replay/output \
  --acceptance-out .microcosm/component-guides/agent_sabotage_scheming_monitor_replay/acceptance.json
```

The result records the monitor and counterfactual checks and any findings. It is written under `.microcosm/component-guides/agent_sabotage_scheming_monitor_replay/output`; the acceptance receipt is separate. These paths do not overwrite the checked-in receipts.

## Verification

Tests and fixtures exercise the monitor and counterfactual checks; they do not formally prove the monitor algorithm. The command above runs directly, without the shared admission gate. `make component-replays` separately runs the exported sabotage-monitor bundle through the [Dafny-verified admission decision](../formal/replay/README.md), checking the host's observations of source and input identities, claim policy and receipt agreement.

## Source

[Implementation](../src/microcosm_core/organs/agent_sabotage_scheming_monitor_replay.py) · [fixture input](../fixtures/first_wave/agent_sabotage_scheming_monitor_replay/input/) · [tests](../tests/test_agent_sabotage_scheming_monitor_replay.py) · [sample result (historical)](../receipts/first_wave/agent_sabotage_scheming_monitor_replay/agent_sabotage_scheming_monitor_replay_result.json) · [JSON record](agent_sabotage_scheming_monitor_replay.json).
