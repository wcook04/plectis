# Finance Forecast Evaluation Spine

## Teleology

`finance_eval_spine` makes the macro finance evaluator inspectable inside
Microcosm by copying the non-secret `tools/finance` evaluator bodies and the
generated `finance_eval_operating_picture` into a public bundle. The point is
not to show a market toy; it is to expose the comparison-key, CP1 admission,
CP2 resolution, replay, calibration, variant, and operating-picture machinery
with its no-advice/no-mutation boundary intact.

## Public Contract

The public command is:

```bash
PYTHONPATH=src python3 -m microcosm_core.cli finance-eval-spine validate-finance-eval-bundle \
  --input examples/finance_forecast_evaluation_spine/exported_finance_eval_bundle \
  --out receipts/first_wave/finance_forecast_evaluation_spine
```

The validator checks copied module digests, line counts, required source
anchors, the real operating-picture schema, false mutation gates,
`tools/finance/event_keys.py` comparison-key authority, and a secret-exclusion
scan over the copied bundle. Source bodies live in the bundle; receipts carry
refs, hashes, counts, gates, and findings.

## Governing Standard

`standards/std_microcosm_finance_forecast_evaluation_spine.json` owns the
receipt contract, source refs, allowed public inputs, forbidden private inputs,
and authority ceiling for this import.

## Source Substrate

The copied macro bodies are:

- `tools/finance/event_keys.py`
- `tools/finance/admit_forecasts.py`
- `tools/finance/resolve_forecasts.py`
- `tools/finance/eval_replay.py`
- `tools/finance/historical_replay.py`
- `tools/finance/calibrate_forecast_probabilities.py`
- `tools/finance/variant_registry.py`
- `tools/finance/compare_variants.py`
- `tools/finance/build_eval_operating_picture.py`

The real macro receipt is
`state/finance_eval/views/finance_eval_operating_picture.json`.

## Anti-Claim

This spine is local evaluator and replay substrate. It does not provide
trading, financial, or investment advice; call live market data providers;
export account or portfolio state; expose provider payload bodies; claim
forecast performance; mutate optimizer or calculator weights; publish; host; or
authorize release.
