# Prediction Oracle Reconciliation

`prediction_oracle_reconciliation` is a source-available runtime fixture organ for the
prediction-engine slice. It compresses the macro pattern group around CP1
bifurcation resolution, CP2 valid target universes, oracle grounding firewalls,
diff grading, and dossier mutation into a synthetic packet a cold reader can run.

It is deliberately not a market product. The organ has no live data, no provider
calls, no trading authority, no financial or investment advice authority, no
publication authority, and no release authority. Its job is to make the reasoning
shape inspectable without making performance or action claims. The receipt
contract is source-open by default: public fixture packets, exported bundle refs,
source refs, and runtime receipts carry the evidence, while
`secret_exclusion_scan` blocks only live market feeds, provider payload bodies,
account/session material, private dossiers, and credential-equivalent access.

## Public Contract

The input packet names:

- `source_pattern_ids` for the macro pattern family being projected.
- `valid_prediction_targets` and `target_universe` for the CP2 gate.
- `cp1_branches` with selected side, rationale refs, and opposite-side
  invalidation refs.
- `cp2_predictions` with pre-target evidence refs and grounding ids.
- `oracle_diff` rows that grade synthetic realized direction against prediction.
- `dossier_mutations` constrained to fixture deltas.
- `public_runtime_refs` for the public fixture, exported bundle, and paper module
  substrate refs.
- `authority_ceiling` values that explicitly keep trading, advice, provider,
  live-market, publication, release, and secret-export authority false.

## Negative Cases

The fixture rejects:

- a CP2 prediction outside the target universe;
- an unresolved CP1 bifurcation;
- post-target evidence used as prediction evidence;
- unconfirmed equity or market-lane claims;
- unsafe high-severity dossier mutation;
- trading, advice, live-provider, publication, release, or secret-export
  authority overclaims.

## Commands

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.prediction_oracle_reconciliation run \
  --input fixtures/first_wave/prediction_oracle_reconciliation/input \
  --out receipts/first_wave/prediction_oracle_reconciliation

PYTHONPATH=src python3 -m microcosm_core.organs.prediction_oracle_reconciliation run-prediction-bundle \
  --input examples/prediction_oracle_reconciliation/exported_prediction_oracle_bundle \
  --out receipts/runtime_shell/demo_project/organs/prediction_oracle_reconciliation
```

## Anti-Claim

This module demonstrates synthetic prediction-reconciliation mechanics only. It
does not trade, give financial or investment advice, call live market providers,
publish predictions, claim forecasting performance, import private data, or
authorize release.
