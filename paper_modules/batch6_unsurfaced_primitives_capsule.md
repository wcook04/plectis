# Exercise text, policy and timing primitives

> **In plain terms.** Small building blocks inside a large project, like one that picks key phrases out of text, can fail on odd inputs. It is given copies of selected blocks and small made-up cases covering text, money units, tasks running at once, recording timing and more. It runs each block on its cases, and a phrase made only of filler words yields no key phrase while amounts whose unit scales do not match are blocked. Each exercise gets its own result, so someone can see how every block handles these cases.

This fixture loads selected copied modules and runs small exercises across text extraction, memory, market situations, finance units, policy, concurrency and recording timing. It checks the selected mechanism set and returns individual exercise results.

## Run the example

From the repository root, with Python 3.11 or newer and the project dependencies installed:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.batch6_unsurfaced_primitives_capsule run \
  --input fixtures/first_wave/batch6_unsurfaced_primitives_capsule/input \
  --out .microcosm/component-guides/batch6_unsurfaced_primitives_capsule/result \
  --acceptance-out .microcosm/component-guides/batch6_unsurfaced_primitives_capsule/acceptance.json --card
```

The command prints a compact JSON card and writes its results under `.microcosm/component-guides/`. A passing run returns exit code 0; a blocked run returns 1.

## What this checks

The negative cases include a stopword-only phrase that yields no keyphrase, a finance unit-scale mismatch that blocks, and a missing counterevidence case. The concurrency case identifies a parent-child conflict; the recording case checks pause-time remapping.

## Verification

The example above runs the fixture directly. In `make component-replays`, this component’s exported bundle is checked by the [shared Dafny replay admission core](../formal/replay/README.md) for agreement among supplied source, input, claim-policy and receipt observations. That admission check does not prove this component’s algorithm or the truth of its domain claims.

## Limits

Runs selected copied modules on small text, memory, market, finance-unit, policy, concurrency and recording-timing exercises, blocking a finance unit-scale mismatch and a case without counterevidence.

## Source and evidence

Read the [implementation](../src/microcosm_core/organs/batch6_unsurfaced_primitives_capsule.py), [fixture input](../fixtures/first_wave/batch6_unsurfaced_primitives_capsule/input/batch6_probe_manifest.json), and [focused tests](../tests/test_batch6_unsurfaced_primitives_capsule.py). The [saved acceptance result](../receipts/acceptance/first_wave/batch6_unsurfaced_primitives_capsule_fixture_acceptance.json) is historical sample evidence, not the result of your run. The [JSON record](batch6_unsurfaced_primitives_capsule.json) identifies the module; the canonical capsule metadata is in [paper_module_capsules.json](../core/paper_module_capsules.json).

[Open Policy Agent](https://www.openpolicyagent.org/docs/latest) is related background on policy evaluation.
