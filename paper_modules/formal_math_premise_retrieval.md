# Rank public premise metadata for a query

The retrieval fixture scores public Lean/Std premise metadata by token overlap with the query and adds a strategy-tag bonus. It filters candidates by allowed split, sorts by score and checks the shortlist against fixture expectations. The tests show that changing a premise can change the ranking and cause expected recall to fail.

The validator rejects a premise containing a proof body, a query carrying oracle premise IDs, test-split tuning, an unknown strategy and context recipes over budget. This is a small transparent retrieval exercise, not a benchmark of retrieval quality. It does not execute Lean or establish theorem correctness.

## Run the example

Python 3.11 or later is required. From the repository root, use the Python API to direct both result and acceptance output into ignored local state. The CLI does not expose the acceptance path for this action.

```bash
PYTHONPATH=src python3 - <<'PYCODE'
from microcosm_core.organs.formal_math_premise_retrieval import run
result = run('fixtures/first_wave/formal_math_premise_retrieval/input', '.microcosm/component-guides/formal_math_premise_retrieval', acceptance_out='.microcosm/component-guides/formal_math_premise_retrieval/acceptance.json')
print(result['status'])
PYCODE
```

## Verification

`_score_query` calls the [proved premise-ranking core](../formal/components/premise_ranking/README.md). For normalized token counts it returns exactly the eligible occurrences, with scores equal to the sum of per-token minimum counts plus the strategy bonus. It orders them by descending score, premise-ID rank and original position. Python supplies tokenization and eligibility; the proof does not establish retrieval quality.

The example uses that core. `make component-replays` separately applies the shared [replay admission check](../formal/replay/README.md) to the exported bundle.

## Source

[Implementation](../src/microcosm_core/organs/formal_math_premise_retrieval.py) · [Input](../fixtures/first_wave/formal_math_premise_retrieval/input) · [Tests](../tests/test_formal_math_premise_retrieval.py) · [Historical sample](../receipts/first_wave/formal_math_premise_retrieval/formal_math_premise_retrieval_result.json) · [JSON record](formal_math_premise_retrieval.json)

For research context on premise selection, see [this paper](https://arxiv.org/abs/1904.03241).
