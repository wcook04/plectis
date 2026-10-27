# Choose tactics for a target shape

This gate reads recorded tactic availability and target-shape route cases, then checks the selected tactic against the candidates, availability and shape-specific preferences. It writes a routing report for use before proof execution.

## Run the example

From the repository root, with Python 3.11 or newer available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.target_shape_tactic_routing_gate run \
  --input fixtures/first_wave/target_shape_tactic_routing_gate/input \
  --out .microcosm/component-guides/target_shape_tactic_routing_gate \
  --acceptance-out .microcosm/component-guides/target_shape_tactic_routing_gate/acceptance.json
```

The command writes local output under `.microcosm/component-guides/`. Check the returned status and the result receipt; a blocked result reports findings for the supplied inputs.

## What this checks

For example, the test for a Boolean double-negation goal checks that the preferred available tactic is `decide`. The gate rejects selecting an unavailable tactic and requires a fallback for an unknown shape or an unavailable preferred tactic. The input includes invalid post-execution and proof-body cases.

## Limits

A selected tactic is a routing suggestion, not a proof or a guarantee that the tactic will solve a goal. This validator does not execute Lean or Lake.

## Verification

The selector calls the [proved tactic-selection core](../formal/components/tactic_selection/README.md). Given ordered preferences and candidates marked known, available and allowed, it selects the first eligible preferred tactic, otherwise the first eligible candidate, or reports no selection. The proof covers that ordering for finite inputs; Python supplies the preferences and availability observations.

The example uses that core. `make component-replays` separately applies the shared [replay admission check](../formal/replay/README.md) to the exported bundle.

## Source

[Implementation](../src/microcosm_core/organs/target_shape_tactic_routing_gate.py) · [Example input](../fixtures/first_wave/target_shape_tactic_routing_gate/input/) · [Tests](../tests/test_target_shape_tactic_routing_gate.py) · [Historical sample result](../receipts/first_wave/target_shape_tactic_routing_gate/target_shape_tactic_routing_result.json) · [JSON record](target_shape_tactic_routing.json)

Background: [Lean tactics](https://lean-lang.org/theorem_proving_in_lean4/Tactics/).
