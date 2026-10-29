# Exercise receipt and execution safeguards

> **In plain terms.** Systems that keep saved records and run programs need safeguards that catch mistakes. It is given made-up cases for saved records and background processes, plus a map of what depends on what. It runs each safeguard on its cases and rejects the bad ones, and for the dependency map it lists everything that relies on a chosen item, directly or indirectly. The output is an outcome for each case, so someone can check each safeguard did what it should. One small step, finding what relies on the chosen item, is checked by a mathematical proof against written rules.

This fixture runs examples of receipt validation, replay scope, proof-contract checks, process classification, state convergence, trace recording, dependency impact and doctrine drift. It records each outcome alongside source-manifest evidence.

## Run the example

From the repository root, with Python 3.11 or newer and the project dependencies installed:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.batch5_authority_systems_capsule run \
  --input fixtures/first_wave/batch5_authority_systems_capsule/input \
  --out .microcosm/component-guides/batch5_authority_systems_capsule/result \
  --acceptance-out .microcosm/component-guides/batch5_authority_systems_capsule/acceptance.json --card
```

The command prints a compact JSON card and writes its results under `.microcosm/component-guides/`. A passing run returns exit code 0; a blocked run returns 1.

## What this checks

A receipt with provider-context drift is rejected, and a proof contract containing `sorry` is rejected. A live descendant must not be signalled by the orphan classifier. When a generated projection remains unresolved and its source signature changes between checks, the fixture classifies it as a source-moved residual.

## Verification

The dependency-impact exercise calls a [Dafny-verified reachability core](../formal/components/dependency_reachability/README.md). For the supplied finite graph it returns exactly the nodes connected to the starting dependency by one or more dependency edges, including the start only if a cycle reaches it. Python constructs the graph; the proof does not establish that its edges are complete or verify the other exercises.

The direct fixture runs this core. `make component-replays` separately applies the [shared admission check](../formal/replay/README.md) to the component replay’s captured observations.

## Limits

Runs examples of receipt validation, replay scope, proof contracts, process classification, state convergence, trace recording, dependency impact and doctrine drift, and checks each copied source against its manifest digest, rejecting a receipt with provider-context drift and a proof contract containing `sorry`.

## Source and evidence

Read the [implementation](../src/microcosm_core/organs/batch5_authority_systems_capsule.py), [fixture input](../fixtures/first_wave/batch5_authority_systems_capsule/input/batch5_exercise_manifest.json), and [focused tests](../tests/test_batch5_authority_systems_capsule.py). The [saved acceptance result](../receipts/acceptance/first_wave/batch5_authority_systems_capsule_fixture_acceptance.json) is historical sample evidence, not the result of your run. The [JSON record](batch5_authority_systems_capsule.json) identifies the module; the canonical capsule metadata is in [paper_module_capsules.json](../core/paper_module_capsules.json).

[W3C PROV](https://www.w3.org/TR/prov-overview/) and [SLSA provenance](https://slsa.dev/spec/v1.2/provenance) provide related provenance models.
