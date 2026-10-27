# Route a problem to catalogue entries

The annex knowledge router takes a problem description and a catalogue of entries, scores matches from structured routing fields and other text, and returns ranked rows with match details. Optional domain and cluster filters narrow the candidates; matching notes can add evidence to a row.

## Run the example

From the repository root, with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.annex_knowledge_router evaluate-fixtures \
  --input fixtures/first_wave/engine_room_annex_knowledge_router/input --json
```

The JSON reports each expected outcome and an overall status. In the provider-backoff fixture, the top result is `provider-rate-limit-patterns`; an empty problem returns `no_match`. The latter is a useful rejection of an uninformative query, rather than a recommendation based on no evidence.

This is a small deterministic router over supplied catalogue fields. Its scoring is not BM25 and the fixture does not establish search quality over a real collection. For background on retrieval evaluation and BM25, see [TREC](https://trec.nist.gov/) and [Lucene’s BM25 description](https://lucene.apache.org/core/9_8_0/core/org/apache/lucene/search/similarities/BM25Similarity.html).

## Verification

The focused tests check the fixture rankings, filters and empty-query behavior. This helper has no registered component replay route and no component-specific formal proof in this repository. A passing fixture matrix is evidence for the tested cases, not proof of the ranking algorithm.

## Source and evidence

- [Implementation](../src/microcosm_core/engine_room/annex_knowledge_router.py) and [focused tests](../tests/test_engine_room_annex_knowledge_router.py).
- [Fixture inputs](../fixtures/first_wave/engine_room_annex_knowledge_router/input/); [historical Engine Room composition result](../receipts/first_wave/engine_room_demo/engine_room_demo_result.json) (summary, not a detailed result for this individual fixture).
- [JSON record](../paper_modules/engine_room_annex_knowledge_router.json); canonical metadata: [`core/paper_module_capsules.json`](../core/paper_module_capsules.json).
