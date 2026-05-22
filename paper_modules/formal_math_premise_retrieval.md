# Formal Math Premise Retrieval

`formal_math_premise_retrieval` is the public-safe first real formal-math import tranche after the macro projection protocol. It turns the macro prover lab's premise-index, term-scoring, context-budget, and strategy-selection patterns into a runnable Microcosm organ.

It is still deliberately below proof authority. It validates Lean/Std premise metadata, query term scoring, split eligibility, context recipe budgets, public strategy ids, redacted receipts, and negative cases. It does not run Lean or Lake, call providers, expose proof bodies, expose oracle-needed premise ids, tune on test split truth, claim theorem correctness, or authorize release.

## Runtime Surfaces

- Organ runner: `python -m microcosm_core.organs.formal_math_premise_retrieval run --input fixtures/first_wave/formal_math_premise_retrieval/input --out receipts/first_wave/formal_math_premise_retrieval`
- Exported bundle runner: `python -m microcosm_core.organs.formal_math_premise_retrieval run-retrieval-bundle --input examples/formal_math_premise_retrieval/exported_premise_retrieval_bundle --out receipts/runtime_shell/demo_project/organs/formal_math_premise_retrieval`
- CLI route: `microcosm formal-math-premise-retrieval run-retrieval-bundle`
- Standard: `standards/std_microcosm_formal_math_premise_retrieval.json`
- Fixture manifest: `core/fixture_manifests/formal_math_premise_retrieval.fixture_manifest.json`

## Public Claim

Microcosm can now show a real formal-math retrieval mechanism in miniature: a synthetic Lean/Std premise index, term-scored queries, split-aware eligibility, context recipe ceilings, strategy gates, and redacted validation receipts.

## Negative Cases

- `premise_index_proof_body_forbidden`
- `query_oracle_ids_forbidden`
- `test_split_tuning_attempt`
- `context_recipe_budget_overflow`
- `unknown_strategy_id`

## Authority Ceiling

The organ proves only that public retrieval metadata is internally coherent and leakage-checked. The deferred `formal_math_lean_proof_witness` boundary remains unchanged.
