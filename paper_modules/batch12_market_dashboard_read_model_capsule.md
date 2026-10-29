# Check a market dashboard read model

> **In plain terms.** A market dashboard can mislead if its data has broken links, unsafe references or stale feeds. This component is given a made-up bundle of dashboard data, covering a queue of situations, a diagram of points and links, and feed status. It rejects a link with no destination or a reference that climbs out of its folder, tells a stale feed from a fresh one, and treats two situations as unrelated when they share no subject and differ in type. It writes a result for each of the three checks and notes how each broken example was handled. The examples concern only the dashboard's data and labels, not current market data, forecast accuracy or investment advice.

This fixture loads a copied dashboard module and checks a synthetic dashboard payload containing a situation queue, graph nodes and links, evidence references and feed status. It also checks feed freshness and which situations the dashboard treats as related. It writes the three mechanism results and their negative-case observations.

## Run the example

From the repository root, with Python 3.11 or newer and the project dependencies installed:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.batch12_market_dashboard_read_model_capsule run \
  --input fixtures/first_wave/batch12_market_dashboard_read_model_capsule/input \
  --out .microcosm/component-guides/batch12_market_dashboard_read_model_capsule/result \
  --acceptance-out .microcosm/component-guides/batch12_market_dashboard_read_model_capsule/acceptance.json --card
```

The command prints a compact JSON card and writes its results under `.microcosm/component-guides/`. A passing run returns exit code 0; a blocked run returns 1.

## What this checks

The validator rejects a graph edge with no destination and unsafe traversal references. The freshness classifier distinguishes a stale feed from a fresh one and blocks missing readiness evidence; the related-situation check returns no match for two situations with neither shared entities nor the same type. The fixture also allows a same-type match without shared entities.

## Verification

The example above runs the fixture directly. In `make component-replays`, this component’s exported bundle is checked by the [shared Dafny replay admission core](../formal/replay/README.md) for agreement among supplied source, input, claim-policy and receipt observations. That admission check does not prove this component’s algorithm or the truth of its domain claims.

## Limits

These cases test the read model and its labels, not current market data, investment advice or the accuracy of a forecast.

## Source and evidence

Read the [implementation](../src/microcosm_core/organs/batch12_market_dashboard_read_model_capsule.py), [fixture input](../fixtures/first_wave/batch12_market_dashboard_read_model_capsule/input/dashboard_payload.json), and [focused tests](../tests/test_batch12_market_dashboard_read_model_capsule.py). The [saved acceptance result](../receipts/acceptance/first_wave/batch12_market_dashboard_read_model_capsule_fixture_acceptance.json) is historical sample evidence, not the result of your run. The [JSON record](batch12_market_dashboard_read_model_capsule.json) identifies the module; the canonical capsule metadata is in [paper_module_capsules.json](../core/paper_module_capsules.json).

The [CQRS pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs) describes a broader use of read models.
