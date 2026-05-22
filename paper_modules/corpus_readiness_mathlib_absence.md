# Corpus Readiness Mathlib Absence

`corpus_readiness_mathlib_absence_gate` is a public-safe formal-math organ for a
small but important piece of the macro proof lab: consumers must know when
Mathlib is absent before they route proof work, retrieve premises, or interpret
translation corpora.

The public version is not a Lean benchmark and not a theorem prover. It makes
the environment boundary runnable. A reader can inspect a corpus readiness
fixture, see that Mathlib import availability is false, see which corpora are
translation-smoke-only or absent, and see consumer cases blocked before any
Mathlib-dependent proof work is attempted.

## Public Contract

The input bundle names:

- `source_pattern_ids` for the macro pattern being projected.
- `source_refs` as path-level lineage labels only.
- `corpora` with corpus status, Lean availability, Mathlib import probe status,
  translation-smoke flags, and consumer rules.
- `consumer_gate_cases` that decide whether downstream work is allowed or
  blocked before proof execution.
- `authority_ceiling` values that keep Lean/Lake execution, Mathlib proof
  authority, corpus benchmark authority, provider calls, and release authority
  false.

## Negative Cases

The fixture rejects:

- Mathlib availability claimed without a passing probe;
- a Mathlib-dependent consumer that skips the readiness gate;
- private/raw source refs in corpus metadata;
- proof/provider body fields in readiness rows;
- release, publication, or proof-authority overclaims.

## Commands

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.corpus_readiness_mathlib_absence_gate run \
  --input fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input \
  --out receipts/first_wave/corpus_readiness_mathlib_absence_gate

PYTHONPATH=src python3 -m microcosm_core.organs.corpus_readiness_mathlib_absence_gate run-projection-bundle \
  --input examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle \
  --out receipts/runtime_shell/demo_project/organs/corpus_readiness_mathlib_absence_gate
```

## Anti-Claim

This module validates public corpus/toolchain readiness metadata only. It does
not run Lean or Lake, claim Mathlib availability, prove theorem correctness,
benchmark formal-math corpora, expose proof bodies, call providers, or authorize
release.
