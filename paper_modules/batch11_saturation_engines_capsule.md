# Exercise a collection of source-backed checks

This fixture runs thirteen selected checks on examples ranging from run affinity and navigation to market data, research evidence and recording segments. It checks source manifests and records each exercise and its negative cases.

## Run the example

From the repository root, with Python 3.11 or newer and the project dependencies installed:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.batch11_saturation_engines_capsule run \
  --input fixtures/first_wave/batch11_saturation_engines_capsule/input \
  --out .microcosm/component-guides/batch11_saturation_engines_capsule/result \
  --acceptance-out .microcosm/component-guides/batch11_saturation_engines_capsule/acceptance.json --card
```

The command prints a compact JSON card and writes its results under `.microcosm/component-guides/`. A passing run returns exit code 0; a blocked run returns 1.

## What this checks

For example, the run selector chooses a working feed run over a stale failed run, even when the latter is marked as the preferred run. A scan of sample public file contents and paths blocks a key-shaped token; an unreachable navigation target fails its route check. The market examples normalize units and route unknown macro categories to an other bucket. Each result is specific to its test inputs.

## Verification

The example above runs the fixture directly. In `make component-replays`, this component’s exported bundle is checked by the [shared Dafny replay admission core](../formal/replay/README.md) for agreement among supplied source, input, claim-policy and receipt observations. That admission check does not prove this component’s algorithm or the truth of its domain claims.

## Limits

The collection mixes copied source with declared public refactors; a matching digest or passing synthetic case does not establish production performance, market truth or security.

## Source and evidence

Read the [implementation](../src/microcosm_core/organs/batch11_saturation_engines_capsule.py), [fixture input](../fixtures/first_wave/batch11_saturation_engines_capsule/input/batch11_saturation_engines_capsule_probe_manifest.json), and [focused tests](../tests/test_batch11_saturation_engines_capsule.py). The [saved acceptance result](../receipts/acceptance/first_wave/batch11_saturation_engines_capsule_fixture_acceptance.json) is historical sample evidence, not the result of your run. The [JSON record](batch11_saturation_engines_capsule.json) identifies the module; the canonical capsule metadata is in [paper_module_capsules.json](../core/paper_module_capsules.json).

[Monitoring distributed systems](https://sre.google/sre-book/monitoring-distributed-systems/) offers background on interpreting operational signals.
