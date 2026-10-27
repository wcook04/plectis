# Ordered budget packing

`BudgetPacking.dfy` verifies the ordered decision used by the provider-context
recipe projection. Given a sequence of nonnegative integer sizes and a signed
budget, `Pack` returns one decision for every input position, in order. A position
is included exactly when its size plus the total of earlier included positions
fits the budget. The returned total is the sum of included sizes; it does not
exceed a nonnegative budget. A negative budget includes nothing. The
`GreedyConcat` lemma proves that decisions from consecutive batches agree with
the same ordered rule when each batch receives the remaining budget.

The production hook is `_recipe_projection` in
`src/microcosm_core/organs/provider_context_recipe_budget_policy.py`. It computes
sizes using the existing text and declared-size rules, passes the normalized
integers through `plectis.components.budget_packing.pack`, and uses the returned
position decisions to assemble the original metadata. The wrapper batches long
sequences and calls the generated kernel through the shared isolated worker.
Inputs and the returned total use hexadecimal integers on the worker wire, so
Python's decimal JSON digit limit does not truncate the supported integer range.
Python normalization, UTF-8 byte counting, the adapter, batching and metadata
assembly, the worker and the Dafny compiler/runtime remain trusted. In particular,
a declared fallback size need not equal any actual body size. The shared worker has a timeout; it does not prove provider policy,
model behavior, or receipt authenticity.

The source-linked negative changes the fit test to compare each item against
the full budget instead of the remaining budget. The proof rejects that change;
for budget 10 and sizes 6, 6 it would include 12 bytes. `metadata.json` records
the source and generated hashes and the verification summaries. Reproduction
uses Dafny 4.11.0 and the repository's component-kernel checker; focused runtime
coverage is in `tests/test_component_budget_packing.py`.
