# Prediction and oracle reconciliation

> **In plain terms.** A price prediction is graded unfairly if the grading uses evidence from after the prediction was made. This component is given a made-up packet of predictions, the evidence cited for each, and rows recording the realised outcomes. It checks each prediction's target and evidence dates, works out the numeric rankings again and grades the realised direction of each outcome. It writes a result and rejects an outcome with no matching prediction, a grade that disagrees with the one it works out, and later evidence used as if it came earlier. Because everything is made up, it says nothing about forecasting accuracy, uses no market feeds and gives no investment advice.

Checks a synthetic prediction packet against supplied evidence and realised outcomes, then emits a reconciliation result.

## Run the example

From the repository root with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.prediction_oracle_reconciliation run-prediction-bundle --input examples/prediction_oracle_reconciliation/exported_prediction_oracle_bundle --out .microcosm/component-guides/prediction_oracle_reconciliation --card
```

Inspect the status and findings in `.microcosm/component-guides/`; the linked result below is a historical sample.

## What it checks

The validator checks prediction targets and evidence timing, recomputes numeric rankings and grades supplied realised directions. It keeps stock and ETF counts separate and constrains dossier mutations to declared types and evidence. It rejects an oracle row without a supporting prediction, a claimed grade contradicting recomputation, and post-prediction evidence used as prior evidence.

## Limits

The packet and outcomes are synthetic. This replay does not establish forecasting accuracy, access market feeds, or provide investment advice.

## Verification

The focused tests exercise this component’s checks; they do not prove its algorithm. `make component-replays` runs its registered exported prediction bundle through the shared [Dafny admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement within the host’s observations. The direct command above does not itself invoke that admission gate.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/prediction_oracle_reconciliation.py) and [focused tests](../tests/test_prediction_oracle_reconciliation.py)
- [Example input](../fixtures/first_wave/prediction_oracle_reconciliation/input/reconciliation_packet.json) and [historical sample result](../receipts/first_wave/prediction_oracle_reconciliation/prediction_oracle_reconciliation_result.json)
- [Component JSON record](./prediction_oracle_reconciliation.json) and [canonical capsule](../core/paper_module_capsules.json)

For forecast evaluation context see the [Brier score](https://journals.ametsoc.org/doi/10.1175/1520-0493%281950%29078%3C0001%3AVOFEIT%3E2.0.CO%3B2), [Gneiting and Raftery on proper scoring rules](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf), and [Hanson on market scoring rules](https://hanson.gmu.edu/mktscore.pdf). These are background, not claims that this replay implements those methods.
