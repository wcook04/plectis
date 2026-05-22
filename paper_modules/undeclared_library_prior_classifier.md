# Undeclared Library Prior Symbol Classifier

This module is the public Microcosm projection of the formal-prover rule that a Lean-accepted proof can still violate the evaluation contract when it uses a real library symbol that was not in the allowed premise set. It is a redacted symbol-observation organ, not a proof checker.

The fixture keeps the closed premise index explicit, records only proof-body hashes and extracted qualified symbol refs, and classifies a known symbol outside `allowed_premise_ids` as `UNDECLARED_LIBRARY_PRIOR`. If `cited_unallowed_premise_ids` is present, that explicit budget violation takes precedence and routes as `PREMISE_BUDGET_VIOLATION`.

## Public Mechanics

- Qualified symbol refs are restricted to `Nat`, `List`, `Bool`, `Iff`, and `Eq` namespaces in the public fixture.
- The closed premise index is an allowlist boundary, not permission to use the whole standard library.
- `UNDECLARED_LIBRARY_PRIOR` routes to `bridge_escalate` because the proof may be informative while still out of recipe.
- `PREMISE_BUDGET_VIOLATION` routes to `retry` and short-circuits the residual symbol classifier.
- Receipts redact bodies and expose only ids, hashes, symbols, counts, failure classes, and authority ceilings.

## Anti-Claim

This module does not prove theorem correctness, run Lean or Lake, expose proof bodies, call providers, import private source refs, treat all Std/Mathlib declarations as allowed priors, or authorize release.
