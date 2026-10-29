# Check prediction-market row aggregation

> **In plain terms.** Prediction markets let people trade on whether an event will happen, and a list of them can repeat a market or hide missing data. This component is given made-up market rows and records of which market is which, plus small test cases for data problems. Among duplicate listings it keeps the row with more trading, totals without double counting, and refuses to invent an identity for a market with no matching record. The output is totals plus data warnings, such as a feed with no rows or a change marked unavailable for lack of an earlier successful run. The examples do not test live prices, real data providers or forecast accuracy, and they are not trading advice.

This fixture exercises copied board and quantitative-mart helpers using synthetic market rows, identity records and helper cases. It records deduplication and aggregate results alongside diagnostics for data availability and provider drift.

## Run the example

From the repository root, with Python 3.11 or newer and the project dependencies installed:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.batch12_prediction_market_board_capsule run \
  --input fixtures/first_wave/batch12_prediction_market_board_capsule/input \
  --out .microcosm/component-guides/batch12_prediction_market_board_capsule/result \
  --acceptance-out .microcosm/component-guides/batch12_prediction_market_board_capsule/acceptance.json --card
```

The command prints a compact JSON card and writes its results under `.microcosm/component-guides/`. A passing run returns exit code 0; a blocked run returns 1.

## What this checks

For duplicate listings, the fixture checks that the higher-volume row is retained and aggregates are deduplicated. A market slug without a matching identity record must not acquire an invented identity. Other cases flag a feed with zero rows and leave the change in feed evidence unavailable when there is no previous successful run to compare against.

## Verification

The example above runs the fixture directly. In `make component-replays`, this component’s exported bundle is checked by the [shared Dafny replay admission core](../formal/replay/README.md) for agreement among supplied source, input, claim-policy and receipt observations. That admission check does not prove this component’s algorithm or the truth of its domain claims.

## Limits

The examples do not validate live market prices, provider data, forecast accuracy or calibration; they are not trading advice.

## Source and evidence

Read the [implementation](../src/microcosm_core/organs/batch12_prediction_market_board_capsule.py), [fixture input](../fixtures/first_wave/batch12_prediction_market_board_capsule/input/prediction_market_rows.json), and [focused tests](../tests/test_batch12_prediction_market_board_capsule.py). The [saved acceptance result](../receipts/acceptance/first_wave/batch12_prediction_market_board_capsule_fixture_acceptance.json) is historical sample evidence, not the result of your run. The [JSON record](batch12_prediction_market_board_capsule.json) identifies the module; the canonical capsule metadata is in [paper_module_capsules.json](../core/paper_module_capsules.json).

For context, see the [CFTC prediction markets explainer](https://www.cftc.gov/LearnandProtect/PredictionMarkets) and [Polymarket API documentation](https://docs.polymarket.com/api-reference).
