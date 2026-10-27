# Circuit attribution replay

> **In plain terms.** A claim about which input feature mattered most to a computer model's answer can go stale when the model's numbers change. This component is given a tiny made-up model written as plain numbers, plus a claim naming the top feature and a diagram of connections. It runs the model and measures how much the output changes when each feature is nudged and when it is removed. The result records whether the claimed top feature agrees with those measurements, and it rejects a stale claim or a disconnected diagram. It looks only at a toy network, not a trained model, so it does not show that any trained model can be understood.

Checks a public circuit-attribution fixture and a small numerical model, recording whether the declared feature attribution agrees with its inputs.

## Run the example

From the repository root with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.mechanistic_interpretability_circuit_attribution_replay run --input fixtures/first_wave/mechanistic_interpretability_circuit_attribution_replay/input --out .microcosm/component-guides/mechanistic_interpretability_circuit_attribution_replay --acceptance-out .microcosm/component-guides/mechanistic_interpretability_circuit_attribution_replay/acceptance.json --card
```

Inspect the status and findings in `.microcosm/component-guides/`; the linked result below is a historical sample.

## What it checks

The synthetic fixture supplies token IDs, embeddings and weights. The code averages embeddings, applies a linear layer, tanh and a second linear layer, then recomputes gradients and feature ablations for this small network. Despite its `toy_transformer` identifier, this network has no attention. It checks the declared top feature, graph paths and intervention references. A stale top-feature claim or disconnected graph is rejected.

## Limits

This toy replay does not establish transparency for a trained model or access private activations. Source digests check copied inputs, not the correctness of interpretability methods.

## Verification

The focused tests exercise this component’s checks; they do not prove its algorithm. `make component-replays` runs its registered exported circuit-attribution bundle through the shared [Dafny admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement within the host’s observations. The direct command above does not itself invoke that admission gate.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/mechanistic_interpretability_circuit_attribution_replay.py) and [focused tests](../tests/test_mechanistic_interpretability_circuit_attribution_replay.py)
- [Example input](../fixtures/first_wave/mechanistic_interpretability_circuit_attribution_replay/input) and [historical sample result](../receipts/first_wave/mechanistic_interpretability_circuit_attribution_replay/mechanistic_interpretability_circuit_attribution_replay_result.json)
- [Component JSON record](./mechanistic_interpretability_circuit_attribution_replay.json) and [canonical capsule](../core/paper_module_capsules.json)

[Transformer Circuits](https://transformer-circuits.pub/) offers context on circuit analysis.
