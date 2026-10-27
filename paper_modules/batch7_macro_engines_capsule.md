# Run selected macro-engine exercises

> **In plain terms.** Tools that run a software project rely on helper routines to order tasks, apply edits and choose which tests to rerun. It is given copies of such routines and small example cases for each. It runs each routine on its cases, rejecting tasks that depend on one another in a circle, refusing an edit whose surrounding lines do not match, and checking that an empty test choice falls back to a default. The result combines checks on the copied source with each routine's outcome, showing whether they handle these cases as intended. It does not show that edits are safe, that test selection is complete or that the whole system is correct.

This fixture exercises copied source for trace parsing, dependency scheduling, source indexing, patch validation, clean-clone isolation, numeric scoring, PageRank and regression-test selection. Its result combines source checks with the outcomes of the individual witnesses.

## Run the example

From the repository root, with Python 3.11 or newer and the project dependencies installed:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.batch7_macro_engines_capsule run \
  --input fixtures/first_wave/batch7_macro_engines_capsule/input \
  --out .microcosm/component-guides/batch7_macro_engines_capsule/result \
  --acceptance-out .microcosm/component-guides/batch7_macro_engines_capsule/acceptance.json --card
```

The command prints a compact JSON card and writes its results under `.microcosm/component-guides/`. A passing run returns exit code 0; a blocked run returns 1.

## What this checks

A cyclic dependency graph is rejected, a patch with mismatched context fails, and an unknown PageRank source is refused. When regression selection would be empty, the example checks the fallback selection. The trace parser also runs its original Node test witness.

## Verification

The example above runs the fixture directly. In `make component-replays`, this component’s exported bundle is checked by the [shared Dafny replay admission core](../formal/replay/README.md) for agreement among supplied source, input, claim-policy and receipt observations. That admission check does not prove this component’s algorithm or the truth of its domain claims.

## Limits

The fixture is not a general guarantee of safe patches, complete test selection or whole-system correctness. The original witnesses require Node and their declared JavaScript dependencies; `numpy` is required for the numeric exercise.

## Source and evidence

Read the [implementation](../src/microcosm_core/organs/batch7_macro_engines_capsule.py), [fixture input](../fixtures/first_wave/batch7_macro_engines_capsule/input/batch7_exercise_manifest.json), and [focused tests](../tests/test_batch7_macro_engines_capsule.py). The [saved acceptance result](../receipts/acceptance/first_wave/batch7_macro_engines_capsule_fixture_acceptance.json) is historical sample evidence, not the result of your run. The [JSON record](batch7_macro_engines_capsule.json) identifies the module; the canonical capsule metadata is in [paper_module_capsules.json](../core/paper_module_capsules.json).

[NetworkX PageRank](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.link_analysis.pagerank_alg.pagerank.html) is useful background for the ranking algorithm.
