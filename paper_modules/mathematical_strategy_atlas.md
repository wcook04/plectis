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

The current body-floor import carries eight copied non-secret macro bodies:
the prover graph benchmark harness, the provider receipt reducer, their
strategy-boundary regression tests, the compute-provider strategy
classification standard, and three public runtime artifacts from
`PROVER_PROVIDER_CONTEXT_SWEEP_20260510_v0` (`strategy_cards.json`,
`strategy_hypothesis_set.json`, and `prover_skill_atlas.json`). They live in
`source_artifacts/` under both the first-wave fixture input and the exported
runtime bundle; receipts carry refs, counts, hashes, anchors, and verdicts
instead of body text.

## Public Inputs

- `strategy_atlas.json` defines the known strategy enum, match features, and
  retrieval-term additions.
- `problem_features.json` carries synthetic public problem features with
  oracle labels hidden.
- `hypothesis_cases.json` validates deterministic pre-oracle strategy scoring.
- `source_module_manifest.json` binds copied macro body files to exact source
  refs, SHA-256 digests, byte counts, line counts, material classes, and
  required anchors.
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
Mathlib-dependent proof claims. The copied runtime artifacts are public
strategy traces, not oracle labels, provider payloads, or proof bodies.
