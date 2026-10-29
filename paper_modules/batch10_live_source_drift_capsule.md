# Check copied source for drift

> **In plain terms.** A copied program file can quietly change or go out of date. Its input is a sample set of four copied program files, the fingerprint recorded for each (a short code worked out from its exact contents), and text each file must still contain. It recomputes each fingerprint and compares it with the record, checks the required text, confirms old fingerprints no longer match, and checks that each file is valid program text without running it. The result is a pass or blocked verdict with a summary board, showing whether the copies still match the record.

This check compares four copied Python source files with their recorded digests, checks required anchors, and compiles the copies without importing them. It produces a result, a board and a validation receipt for the supplied fixture.

## Run the example

From the repository root, with Python 3.11 or newer and the project dependencies installed:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.batch10_live_source_drift_capsule run \
  --input fixtures/first_wave/batch10_live_source_drift_capsule/input \
  --out .microcosm/component-guides/batch10_live_source_drift_capsule/result \
  --acceptance-out .microcosm/component-guides/batch10_live_source_drift_capsule/acceptance.json --card
```

The command prints a compact JSON card and writes its results under `.microcosm/component-guides/`. A passing run returns exit code 0; a blocked run returns 1.

## What this checks

The digest matrix requires each current digest to match and each stale digest to differ. A replay using a stale digest is rejected; the compile gate also rejects a bypass. Matching bytes and successful compilation do not prove the program behaves correctly or authorize changes to source, ledgers or routes.

## Verification

The example above runs the fixture directly. In `make component-replays`, this component’s exported bundle is checked by the [shared Dafny replay admission core](../formal/replay/README.md) for agreement among supplied source, input, claim-policy and receipt observations. That admission check does not prove this component’s algorithm or the truth of its domain claims.

## Limits

Compares four copied Python files with their recorded digests and anchors and compiles them without importing them, rejecting a replay with a stale digest and a compile-gate bypass.

## Source and evidence

Read the [implementation](../src/microcosm_core/organs/batch10_live_source_drift_capsule.py), [fixture input](../fixtures/first_wave/batch10_live_source_drift_capsule/input/batch10_live_source_drift_capsule_probe_manifest.json), and [focused tests](../tests/test_batch10_live_source_drift_capsule.py). The [saved acceptance result](../receipts/acceptance/first_wave/batch10_live_source_drift_capsule_fixture_acceptance.json) is historical sample evidence, not the result of your run. The [JSON record](batch10_live_source_drift_capsule.json) identifies the module; the canonical capsule metadata is in [paper_module_capsules.json](../core/paper_module_capsules.json).

[Bazel hermeticity](https://bazel.build/concepts/hermeticity) and [SLSA provenance](https://slsa.dev/spec/) provide related background on reproducible inputs and provenance.
