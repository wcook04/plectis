# Rank a small catalogue by keyword overlap

> **In plain terms.** A catalogue of entries only helps if a person can find the ones that fit their problem. This ranking tool reads a written problem and a small catalogue, where each entry has routing labels, family text, a summary and notes. It counts the words and phrases the problem shares with each entry, weighting routing labels most, then family text, then summary and notes. It returns a ranked list showing what matched in each entry, so a person can pick the best fit, or reports no match when nothing overlaps or a chosen filter excludes every entry. It matches words and phrases, not meaning, and it searches only the catalogue it is given.

The annex router takes a problem statement and an in-memory catalogue, scores matching terms and returns ranked entries with a breakdown of their matches. Structured routing fields receive the highest weight, followed by family text, summaries and notes. Optional domain and cluster filters restrict the candidates.

The fixture runner checks positive matches and two negative cases: no overlapping terms and a domain filter that excludes the candidates. In both cases the router returns `no_match`. The component uses weighted token and phrase matching, not semantic or embedding search. It searches only the supplied catalogue and does not establish licensing or provenance.

## Run the example

From the repository root, with Python 3.11 or newer and the repository dependencies available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.annex_knowledge_routing \
  run --input fixtures/first_wave/annex_knowledge_routing/input \
  --out .microcosm/component-guides/annex_knowledge_routing/output \
  --acceptance-out .microcosm/component-guides/annex_knowledge_routing/acceptance.json
```

The result records each fixture case, including its top match or `no_match` and the match breakdown. It is written under `.microcosm/component-guides/annex_knowledge_routing/output`; the acceptance receipt is separate. These paths do not overwrite the checked-in receipts.

## Verification

Tests and fixtures exercise the keyword matching and negative fixture cases; they do not formally prove the ranking algorithm. The command above runs directly, without the shared admission gate. `make component-replays` separately runs the registered fixture route through the [Dafny-verified admission decision](../formal/replay/README.md), checking the host's observations of source and input identities, claim policy and receipt agreement.

## Source

[Implementation](../src/microcosm_core/organs/annex_knowledge_routing.py) · [fixture input](../fixtures/first_wave/annex_knowledge_routing/input/) · [tests](../tests/test_engine_room_annex_knowledge_router.py) · [sample result (historical)](../receipts/first_wave/annex_knowledge_routing/annex_knowledge_routing_result.json) · [JSON record](annex_knowledge_routing.json). [Scoring implementation](../src/microcosm_core/engine_room/annex_knowledge_router.py).
