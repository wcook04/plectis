# Synthetic market primitives: stock momentum and order books

This fixture runs three copied market-code exercises: a stock momentum calculation, order-book price and depth extraction, and four-lens market scoring. It checks the copied sources and records results for synthetic inputs. The current implementation does not exercise the UI and graph components described by earlier versions of this page.

The order-book exercise selects the highest bid and lowest ask by numeric value, even when rows are out of order. A sorted-book trap checks that taking the first row would give the wrong answer. The momentum exercise rejects an extreme negative change for which the logarithmic return is not finite; the scoring exercise gates a resolved synthetic market.

## Run the example

Python 3.11 or newer and the project test dependencies (install with `python3 -m pip install -e ".[test]"`) are required. Run from the repository root:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.batch7_secondary_runtime_capsule run \
  --input fixtures/first_wave/batch7_secondary_runtime_capsule/input \
  --out .microcosm/component-guides/batch7_secondary_runtime_capsule \
  --acceptance-out .microcosm/component-guides/batch7_secondary_runtime_capsule/acceptance.json
```

The command writes its result and acceptance files under `.microcosm/component-guides/`; inspect the status and findings in those files.

## Verification

The synthetic market exercises and source checks do not formally prove the market algorithms. Separately, `make component-replays` runs this component’s registered exported-bundle route through the [Dafny-proved replay admission check](../formal/replay/README.md). Using host-supplied observations, it compares source, input, claim-policy and receipt identities; it does not prove the component’s domain result. The direct command above does not invoke the shared check.

## Limits

These checks establish the named fixture behavior, not live-market accuracy, investment advice, or complete coverage. Matching source hashes and anchors establish identity and expected text, not algorithm correctness.

## Sources

[src/microcosm_core/organs/batch7_secondary_runtime_capsule.py](../src/microcosm_core/organs/batch7_secondary_runtime_capsule.py) contains the implementation. See the [input fixtures](../fixtures/first_wave/batch7_secondary_runtime_capsule/input/), [tests](../tests/test_batch7_secondary_runtime_capsule.py), [historical sample acceptance result](../receipts/acceptance/first_wave/batch7_secondary_runtime_capsule_fixture_acceptance.json), and the [component JSON record](../core/paper_module_capsules.json). [Prediction market context](https://www.cftc.gov/LearnandProtect/PredictionMarkets).
