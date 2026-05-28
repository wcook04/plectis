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

## Quant Research Experiment Spine

Closure of finance assurance is the floor, not the ceiling. The next public
contract is a non-advisory quant research experiment spine: a public-safe
hypothesis card, target universe, horizon, evidence sources, exclusions,
leakage risks, expected failure modes, split discipline, overfit guard,
comparison status, uncertainty state, Oracle reconciliation path, and
review-gated Evolve implication.

The macro composition root is `tools/finance/build_eval_operating_picture.py`.
It now projects `quant_research_experiment_spine` from the existing historical
replay, variant comparison, model-selection, SPA/bootstrap, and effective
evidence receipts. Empty inputs remain a valid awaiting-evidence state; a
non-empty public demo lives in `finance_research_assurance_surface.json` so a
cold reader can see the intended research loop without a performance claim.

The second-wave contract is experiment lineage. The spine must now carry an
`experiment_registry` and `lineage_summary`, not just a single demo card. A
valid public receipt includes at least two public-safe experiment entries: the
shadow forecast-family comparison and a weak/negative-control stress case that
is rejected or marked insufficient. This proves the lane can say "not enough
evidence" or "control rejected" without treating that as failure, and it keeps
Oracle/Evolve learning review-gated rather than self-promoting.

The allowed output language is `awaiting_evidence`, `insufficient_evidence`,
`candidate_set`, `review_candidate`, `rejected`, or
`blocked_authority_overclaim`. The spine is not allowed to declare a tradable
winner, produce personalized account actions, claim performance, or auto-apply
Evolve learning.

The third-wave contract is agenda compilation. Once the registry can preserve
positive, weak, and rejected evidence, the spine must also say what is worth
testing next and what is deliberately deferred. A valid `research_agenda`
contains a small public-safe candidate set with selected, data-snooping-deferred,
control, and needs-more-evidence states; search-budget metadata; family
diversity pressure; and review-gated Oracle/Evolve implications. This makes
closed finance assurance a floor for a research program, not a ceiling.

The fourth-wave contract is agenda-to-experiment cycle closure. The selected
agenda candidate must be consumed into a locked pre-analysis plan before the
public-safe evaluator runs; the result then updates the experiment registry,
family memory, and recompiled agenda. A valid cycle records the selected
candidate id, plan id, evaluator chain, result state, registry delta,
family-memory delta, and next selected candidate while keeping no-advice,
winner-language, and auto-apply gates closed. Negative or insufficient evidence
is a valid research result and must reduce future search pressure instead of
being rewritten into a post-hoc success story.

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
