# Replay a process-reward record with verifier feedback

This replay checks synthetic records of task episodes, belief states, feedback and rewards. Process rewards refer to intermediate steps; outcome rewards refer to the final result. A trajectory group links those rewards with an episode and a stored cold-replay record, which names replay evidence and records a status.

For example, the terminal-investigation fixture links its first belief state and process reward to `fb_terminal_1`, a deterministic-verifier feedback record. Its trajectory group also names a second process reward and an outcome reward. The validator checks these references and their relationships. Its policy permits process rewards based on deterministic verification or observed environment feedback, and requires a cold-replay record, an outcome reward and a reward-hacking trap.

Negative cases include a verifier bypass, hidden reasoning export, a neural-judge-only process label and a reward based on formatting. A mutated feedback link or a numeric perturbation can block semantic recomputation in the tests.

## Run the example

Python 3.11 or newer and the project test dependencies (install with `python3 -m pip install -e ".[test]"`) are required. Run from the repository root:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.belief_state_process_reward_replay run \
  --input fixtures/first_wave/belief_state_process_reward_replay/input \
  --out .microcosm/component-guides/belief_state_process_reward_replay \
  --acceptance-out .microcosm/component-guides/belief_state_process_reward_replay/acceptance.json
```

The command writes its result and acceptance files under `.microcosm/component-guides/`; inspect the status and findings in those files.

## Verification

Checks on the synthetic records do not formally prove the reward policy or model performance. Separately, `make component-replays` runs this component’s registered exported-bundle route through the [Dafny-proved replay admission check](../formal/replay/README.md). Using host-supplied observations, it compares source, input, claim-policy and receipt identities; it does not prove the component’s domain result. The direct command above does not invoke the shared check.

## Limits

This is a check of the supplied public records and policy, not live reinforcement learning, a benchmark result or evidence of improved model performance. It does not export hidden reasoning.

## Sources

[src/microcosm_core/organs/belief_state_process_reward_replay.py](../src/microcosm_core/organs/belief_state_process_reward_replay.py) contains the implementation. See the [input fixtures](../fixtures/first_wave/belief_state_process_reward_replay/input/), [tests](../tests/test_belief_state_process_reward_replay.py), [historical sample acceptance result](../receipts/acceptance/first_wave/belief_state_process_reward_replay_fixture_acceptance.json), and the [component JSON record](../core/paper_module_capsules.json). Background: [process supervision research](https://arxiv.org/abs/2305.20050).
