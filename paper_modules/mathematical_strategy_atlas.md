# Mathematical Strategy Atlas

`mathematical_strategy_atlas_hypothesis_scorer` is the public pre-oracle
strategy layer for Microcosm formal-math work. It turns problem feature tags
into an explicit strategy hypothesis before premise retrieval or proof
execution, then records the result as redacted receipts.

The point is not to prove anything. The point is to make the first
mathematical move inspectable: an `iff_goal` shape selects `iff_split`, a
recursive list shape selects `recursive_data_induction`, arithmetic
normalization selects the arithmetic lens, and unmapped shapes become a typed
`STRATEGY_SELECTION_MISS` instead of a hidden failure mode.

## Public Inputs

- `strategy_atlas.json` defines the known strategy enum, match features, and
  retrieval-term additions.
- `problem_features.json` carries synthetic public problem features with
  oracle labels hidden.
- `hypothesis_cases.json` validates deterministic pre-oracle strategy scoring.
- Negative cases reject unknown strategy ids, proof bodies, oracle labels,
  post-oracle strategy selection, and release/proof/provider overclaims.

## Receipts

The organ emits:

- `mathematical_strategy_atlas_result.json`
- `mathematical_strategy_atlas_board.json`
- `mathematical_strategy_atlas_validation_receipt.json`
- `mathematical_strategy_atlas_hypothesis_scorer_fixture_acceptance.json`

Runtime-shell exported bundle validation writes
`exported_mathematical_strategy_atlas_bundle_validation_result.json`.

## Authority Ceiling

The atlas is metadata and strategy-hypothesis machinery only. It does not run
Lean or Lake, claim theorem correctness, reveal oracle strategy labels, expose
proof bodies, call providers, tune on test answers, authorize release, or make
Mathlib-dependent proof claims.
