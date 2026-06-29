# Annex Knowledge Routing - exported bundle

This bundle accompanies the `annex_knowledge_routing` organ. The organ surfaces the public `annex_knowledge_router` engine-room capsule as a first-class runtime.

## What the mechanism does

Give it a plain-English problem and a small catalog of annex entries (each tagged with the domains, capabilities, and problem-spaces it covers), and it returns the entries most likely to help, ranked, with a breakdown of why each matched. It weighs strong structured tags more than loose description text, and shows its working rather than hiding it behind a black-box score. If nothing in the catalog actually overlaps your problem, it says no_match instead of inventing a result. It is a transparent keyword-overlap matcher, not a search engine or embedding model, and it never reaches outside the catalog you hand it.

## What it does not claim

Real-substrate capsule surfaced over bounded public fixtures. Does NOT clone repositories, ship the private annex corpus, perform semantic/embedding/BM25/TF-IDF search, adjudicate licenses or provenance, call providers or external solvers, mutate source, or authorize release or publication. Routes only over the sanitized catalog supplied in each case; absolute scores are catalog-relative (no statistical normalization). Not a production retrieval system and not private-root equivalent.

## Fixture cases

structured_route_ok (positive): problem 'rate limit backoff across multiple llm providers' matches the provider annex's structured problem_spaces exactly, routing to provider-rate-limit-patterns with score 144 (>= expected_min_score 80); a competing finance annex scores zero and is dropped.
note_route_ok (positive): problem 'provider rate limit retry receipt' routes via the curated-note tier to provider-rate-limit-patterns (score 63 >= 40) and surfaces note_provider_backoff in matched_note_ids, exercising the weakest (notes) evidence tier.
no_overlap_rejected (negative, planted defect): the fixture claims a route (expected_ok false) but the problem 'subaquatic origami choreography for migrating waterfowl' shares no token with the catalog, so every per-tier score is zero, all rows drop, and the capsule recomputes status=no_match (the expected reject marker).
domain_filter_rejected (negative, planted defect): problem 'forecast error scoring for market outcomes' would match the finance annex, but the domain filter 'agent-runtime' excludes the only (finance-domain) candidate before scoring, so the capsule recomputes status=no_match.

## Run it

```bash
python -m microcosm_core.organs.annex_knowledge_routing run \
  --input fixtures/first_wave/annex_knowledge_routing/input \
  --out receipts/first_wave/annex_knowledge_routing
```
