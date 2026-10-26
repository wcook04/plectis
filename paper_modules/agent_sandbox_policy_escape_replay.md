# Replay sandbox policy decisions

This replay checks synthetic action requests, policy decisions and recorded side effects. A fixed table derives a verdict from the action kind, capability, risk and source trust; the validator compares that verdict with the declared one. Unknown action shapes fail closed to `block`. It checks that blocked actions were not executed and had no recorded diff, and that permitted effects have the required diff and rollback records.

For example, an `allow` label on a request that the table derives as blocked is rejected. These symbolic records exercise the accounting rules; they do not run a real escape attempt or demonstrate host containment, network isolation or resistance to attack.

## Run the example

From the repository root, with Python 3.11 or newer and the repository dependencies available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.agent_sandbox_policy_escape_replay \
  run --input fixtures/first_wave/agent_sandbox_policy_escape_replay/input \
  --out .microcosm/component-guides/agent_sandbox_policy_escape_replay/output \
  --acceptance-out .microcosm/component-guides/agent_sandbox_policy_escape_replay/acceptance.json
```

The result records policy decisions, side-effect checks and any findings. It is written under `.microcosm/component-guides/agent_sandbox_policy_escape_replay/output`; the acceptance receipt is separate. These paths do not overwrite the checked-in receipts.

## Verification

The replay calls the [proved sandbox decision core](../formal/components/sandbox_policy/README.md) for each normalized action. Its proof covers the six recognized risk, action, capability and trust combinations, their exact verdict and rule strings, and the fail-closed result for all other combinations. Python supplies the observed fields; the proof does not establish their authenticity or enforce host isolation.

The example uses that core. `make component-replays` separately applies the shared [replay admission check](../formal/replay/README.md) to the exported bundle.

## Source

[Implementation](../src/microcosm_core/organs/agent_sandbox_policy_escape_replay.py) · [fixture input](../fixtures/first_wave/agent_sandbox_policy_escape_replay/input/) · [tests](../tests/test_agent_sandbox_policy_escape_replay.py) · [sample result (historical)](../receipts/first_wave/agent_sandbox_policy_escape_replay/agent_sandbox_policy_escape_replay_result.json) · [JSON record](agent_sandbox_policy_escape_replay.json).

The [least privilege and complete mediation principles](https://www.cs.virginia.edu/~evans/cs551/saltzer/) provide useful background.
