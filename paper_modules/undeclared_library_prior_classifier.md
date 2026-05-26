# Undeclared Library Prior Symbol Classifier

This module is the Microcosm projection of the formal-prover rule that a
Lean-accepted proof can still violate the evaluation contract when it uses a
real library symbol that was not in the allowed premise set. It is a
provenance-bearing symbol-boundary organ, not a proof checker.

The fixture now carries copied non-secret Lean/Std premise rows from the real
Ring2 premise-index substrate and real Ring2 problem ids / candidate artifact
digests for the symbol-boundary examples. It records extracted qualified symbol
refs and classifies a known symbol outside `allowed_premise_ids` as
`UNDECLARED_LIBRARY_PRIOR`. If `cited_unallowed_premise_ids` is present, that
explicit budget violation takes precedence and routes as
`PREMISE_BUDGET_VIOLATION`.

The source chain is digest-bearing: the real Ring2 premise index
`sha256:c78b176388a5e81bd8a785950e7db0c9a65fd38e556515134146163b48604df1`,
Ring2 run summary
`sha256:93304410f32d40f5cad1c161c1d01a5d6f353ee10b7cf3fecbaaf7b068b43008`,
copied Lean/Std premise fixture
`sha256:0be36ba5b75b40d2ede2d90cefa5181829420df7abbae216d18282b92a30f869`,
and the adjacent corpus-readiness / tactic-availability receipts anchor the
Mathlib-absent toolchain boundary.

The exported runtime bundle now carries a source-open body floor at
`examples/undeclared_library_prior_symbol_classifier/exported_symbol_classifier_bundle/source_module_manifest.json`.
It imports the reducer and batch-calibration builder source bodies exactly,
plus public-safe run bodies for the Ring2 premise index, Ring2 run summary,
recipe policy metrics, and receipt reduction matrix. The two run-state bodies
that originally contained host-local absolute roots are path-normalized to
`<repo-root>` and `<lean-toolchain-root>` while preserving source and target
digests, line counts, byte counts, and required anchors.

## Public Mechanics

- Qualified symbol refs are restricted to `Nat`, `List`, `Bool`, `Iff`, and
  `Eq` namespaces in this public fixture.
- The closed premise index is an allowlist boundary, not permission to use the whole standard library.
- `UNDECLARED_LIBRARY_PRIOR` routes to `bridge_escalate` because the proof may be informative while still out of recipe.
- `PREMISE_BUDGET_VIOLATION` routes to `retry` and short-circuits the residual symbol classifier.
- Receipts expose ids, candidate artifact digests, symbols, counts, failure
  classes, source refs, source digests, and authority ceilings.
- `secret_exclusion_scan` proves proof bodies, provider payloads, private refs,
  oracle IDs, and release claims stayed out of the public receipt stream.

## Regression Cases

The forbidden proof-body, private-ref, allowed-symbol false-positive,
unqualified-token, and theorem-correctness cases are regression-only leakage
guards. They are not product evidence and cannot stand in for the copied
Lean/Std symbol-boundary substrate.

## Anti-Claim

This module does not prove theorem correctness, run Lean or Lake, expose proof
bodies, call providers, import private source refs, treat all Std/Mathlib
declarations as allowed priors, claim Mathlib availability, or authorize
release.
