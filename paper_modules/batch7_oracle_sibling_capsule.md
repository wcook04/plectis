# Exercise Oracle indexing and repair planning

This fixture loads copied modules from Oracle, a market-evidence system, to index artifacts from a sample subject run, build a snapshot and compare a macroeconomic series. It also tests a plan for filling missing artifacts in a related truth run and runs an original pytest witness. It writes summaries of these local exercises.

## Run the example

From the repository root, with Python 3.11 or newer and the project dependencies installed:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.batch7_oracle_sibling_capsule run \
  --input fixtures/first_wave/batch7_oracle_sibling_capsule/input \
  --out .microcosm/component-guides/batch7_oracle_sibling_capsule/result \
  --acceptance-out .microcosm/component-guides/batch7_oracle_sibling_capsule/acceptance.json --card
```

The command prints a compact JSON card and writes its results under `.microcosm/component-guides/`. A passing run returns exit code 0; a blocked run returns 1.

## What this checks

The subject index requires a run directory and artifact identity. In the repair example, the plan remains blocked because source nodes are missing, but writes a `prediction_reconciliation` alias of the existing `oracle_truth_diff_equity` artifact. It excludes the missing-quartet execution path and does not construct the bridge-backed reasoning engine. Missing artifact identity is a rejected case.

## Verification

The example above runs the fixture directly. In `make component-replays`, this component’s exported bundle is checked by the [shared Dafny replay admission core](../formal/replay/README.md) for agreement among supplied source, input, claim-policy and receipt observations. That admission check does not prove this component’s algorithm or the truth of its domain claims.

## Limits

The pytest witness requires pytest and its source dependencies. These examples do not establish semantic truth, live market reasoning or coverage of the full Oracle system.

## Source and evidence

Read the [implementation](../src/microcosm_core/organs/batch7_oracle_sibling_capsule.py), [fixture input](../fixtures/first_wave/batch7_oracle_sibling_capsule/input/batch7_oracle_sibling_exercise_manifest.json), and [focused tests](../tests/test_batch7_oracle_sibling_capsule.py). The [saved acceptance result](../receipts/acceptance/first_wave/batch7_oracle_sibling_capsule_fixture_acceptance.json) is historical sample evidence, not the result of your run. The [JSON record](batch7_oracle_sibling_capsule.json) identifies the module; the canonical capsule metadata is in [paper_module_capsules.json](../core/paper_module_capsules.json).

The [test oracle problem survey](https://discovery.ucl.ac.uk/1471263/) provides background on the distinction between outputs and evidence of correctness.
