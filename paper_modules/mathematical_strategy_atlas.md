# Mathematical Strategy Atlas

The strategy scorer takes public problem features and strategy cards and recomputes a proposed first strategy before premise retrieval or proof execution. The score weights matching triggers, penalizes negative triggers, and adds a capped bonus for retrieval-term matches. The fixture includes an `iff_goal` case selecting `iff_split`; an unmapped case can yield a typed selection miss.

The validator rejects an unknown strategy, an exposed oracle label, a proof body, and an invalid declared selection. Tests change features or strategy evidence to check that the selection is recomputed. This is a hypothesis from the supplied features and scoring rules, not evidence that the strategy proves the statement or that a model performs well on a benchmark.

## Run the example

From the repository root with Python 3.11 or newer, run the fixture through the Python API. The API accepts an explicit acceptance path; the module CLI does not expose that option:

```bash
PYTHONPATH=src python3 - <<'PY'
from microcosm_core.organs.mathematical_strategy_atlas_hypothesis_scorer import run
r = run("fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer/input",
        ".microcosm/component-guides/mathematical_strategy_atlas_hypothesis_scorer/out",
        acceptance_out=".microcosm/component-guides/mathematical_strategy_atlas_hypothesis_scorer/acceptance.json")
print(r["status"])
PY
```

The supplied fixture prints `pass` when its selections and expected negative cases satisfy the validator.

## Verification

Tests check recomputation for selected inputs; they do not prove the scorer or a mathematical statement. `make component-replays` runs the exported strategy bundle through the [shared Dafny admission check](../formal/replay/README.md) for agreement among supplied source, input, claim policy and receipt observations. The direct fixture command does not invoke that gate.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/mathematical_strategy_atlas_hypothesis_scorer.py) and [fixture inputs](../fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer/input/).
- [Tests](../tests/test_mathematical_strategy_atlas_hypothesis_scorer.py).
- [Saved example result](../receipts/first_wave/mathematical_strategy_atlas_hypothesis_scorer/mathematical_strategy_atlas_result.json) (historical, not a fresh run).
- [Component JSON record](./mathematical_strategy_atlas.json) and [canonical capsule](../core/paper_module_capsules.json).
