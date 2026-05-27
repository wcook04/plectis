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
`tools/finance/event_keys.py` comparison-key authority, the finance research
assurance surface, the no-silent-omissions module coverage contract, and a
secret-exclusion scan over the copied bundle. Source bodies live in the bundle;
receipts carry refs, hashes, counts, gates, and findings.

## Finance Research Assurance Spine

The product-shaped surface is now the finance research assurance spine, not a
larger copied-source manifest for its own sake. It binds five proofs into one
public-safe, non-advisory packet:

- module coverage: every macro `tools/finance/*.py` module is imported,
  deferred, operational-receipt-only, or operational-only with an explicit
  reason;
- feed freshness: `fresh_green_feed`, `stale_green_feed`,
  `scheduled_shell`, and `blocked_missing_artifact` are separate states;
- non-empty demo: one public-safe target universe, evidence-construction path,
  forecast-scoring path, pairwise comparison, multiple-comparison guard,
  oracle reconciliation, review-gated Evolve decision, and no-advice receipt;
- statistical discipline: proper scoring first, pairwise equal-loss evidence
  second, multiple-comparison guard third, and review-gated Evolve implication
  last;
- safety boundary: no financial advice, no live provider calls, no private
  account/portfolio export, no optimizer/calculator mutation, no publication,
  and no release authority.

The external benchmark is model-risk-grade research hygiene, not compliance
theater. Dated public regulator guidance from 2026-04-17 moved U.S. banking
model-risk guidance to a revised risk-based frame; this Microcosm spine uses
that only as a rubric for development/use, validation/monitoring, governance,
inventory, and documentation evidence. It does not claim regulated-bank
compliance.

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

The classified-but-not-yet-copied macro finance modules are:

- `tools/finance/build_effective_evidence.py` — deferred public-safe core
  evidence construction.
- `tools/finance/bootstrap_reference.py`,
  `tools/finance/family_loss_matrix.py`,
  `tools/finance/loss_differentials.py`,
  `tools/finance/model_selection.py`,
  `tools/finance/model_selection_stats.py`, and
  `tools/finance/spa_statistics.py` — deferred public-safe statistical
  discipline.
- `tools/finance/build_price_history.py` and
  `tools/finance/refresh_feeds.py` — operational receipt-only until
  provider/runtime touching behavior is represented by public-safe fixtures.
- `tools/finance/__init__.py` — operational-only package marker.

The real macro receipt is
`state/finance_eval/views/finance_eval_operating_picture.json`.

The non-empty public-safe assurance surface is
`examples/finance_forecast_evaluation_spine/exported_finance_eval_bundle/finance_research_assurance_surface.json`.

## Anti-Claim

This spine is local evaluator and replay substrate. It does not provide
trading, financial, or investment advice; call live market data providers;
export account or portfolio state; expose provider payload bodies; claim
forecast performance; mutate optimizer or calculator weights; publish; host; or
authorize release. It also does not let a stale green feed masquerade as a
fresh market capability.
