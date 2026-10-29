# Rank public premise metadata for a query

> **In plain terms.** Proving a statement relies on earlier results, which must be found among many. It is given short public descriptions of known results, without proofs, and a query of keywords for what is to be proved. It scores each description by how many keywords it shares with the query, adds a bonus for a matching strategy tag, drops disallowed ones, and sorts from highest score to lowest. The result is a ranked shortlist, checked against the list the example expects, and inputs carrying a full proof are rejected. One small step, the scoring and sorting, is checked by a mathematical proof against written rules.

The retrieval fixture scores public Lean/Std premise metadata by token overlap with the query and adds a strategy-tag bonus. It filters candidates by allowed split, sorts by score and checks the shortlist against fixture expectations. The tests show that changing a premise can change the ranking and cause expected recall to fail.

Ranks public Lean/Std premise metadata by query-token overlap plus a strategy-tag bonus and checks the shortlist, rejecting a premise containing a proof body, a query carrying oracle premise IDs, test-split tuning, an unknown strategy and an over-budget context recipe.

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
