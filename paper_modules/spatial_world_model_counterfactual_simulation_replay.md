# Compare a predicted transition with a toy gridworld

> **In plain terms.** A prediction of how a scene will change after a 'what if' event goes out of date when the scene or event changes. This component is given made-up scenes on a small grid, each with a 'what if' event and a predicted scene afterwards. For each one it works out the grid's next step under fixed rules, then compares the number of actors and the other changes with the prediction. The output is a list of findings showing each mismatch, and a prediction that no longer matches the computed step is rejected. It is a small made-up grid, not evidence of geographic accuracy, robot operation or a production simulator.

For each synthetic scene and counterfactual event, this replay constructs a deterministic gridworld step and compares its computed next state and transition differences with the supplied prediction. It writes findings and a board for inspecting mismatches.

## Run the example

From the repository root, with Python 3.11 or newer and the checkout dependencies available:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay run \
  --input fixtures/first_wave/spatial_world_model_counterfactual_simulation_replay/input \
  --out .microcosm/component-guides/spatial_world_model_counterfactual_simulation_replay \
  --acceptance-out .microcosm/component-guides/spatial_world_model_counterfactual_simulation_replay/acceptance.json
```

Inspect `.microcosm/component-guides/spatial_world_model_counterfactual_simulation_replay/spatial_world_model_counterfactual_simulation_replay_result.json` for the result and findings.

The comparison includes actor counts, transition deltas and other declared state details. Changing the input scene or event can therefore invalidate a previously supplied prediction.

## What the result means

A stale predicted state that disagrees with the computed step is rejected. This is a small synthetic gridworld check, not evidence of geographic accuracy, robot operation or a production simulator.

Related reading: [Ha and Schmidhuber, World Models](https://arxiv.org/abs/1803.10122).

## Verification

When `make component-replays` runs this component, the shared [Dafny-verified replay admission](../formal/replay/README.md) checks observed source and input identities, claim-policy identity, and receipt agreement. The example above runs directly and does not invoke that gate. There is no component-specific formal proof of the gridworld computation; its tests do not establish real-world accuracy.

## Source

[Implementation](../src/microcosm_core/organs/spatial_world_model_counterfactual_simulation_replay.py) · [input](../fixtures/first_wave/spatial_world_model_counterfactual_simulation_replay/input) · [tests](../tests/test_spatial_world_model_counterfactual_simulation_replay.py) · [historical sample result](../receipts/acceptance/first_wave/spatial_world_model_counterfactual_simulation_replay_fixture_acceptance.json) · [component record](../core/paper_module_capsules.json).
