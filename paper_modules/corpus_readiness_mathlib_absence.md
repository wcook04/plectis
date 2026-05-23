# Corpus Readiness Mathlib Absence

`corpus_readiness_mathlib_absence_gate` is a formal-math organ for a small but
important piece of the macro proof lab: consumers must know when Mathlib is
absent before they route proof work, retrieve premises, or interpret translation
corpora.

The Microcosm version is backed by copied non-secret macro substrate from the
2026-05-11 proof-state curriculum smoke run. It carries the real
`corpus_readiness.json` rows, tactic-affordance boundary refs, source digests,
and generated receipts that show Mathlib import availability is false, which
corpora are translation-smoke-only or absent, and which consumer cases are
blocked before Mathlib-dependent proof work is attempted.

The organ is not a Lean benchmark and not a theorem prover. It does not rerun
Lean or Lake. It makes the recorded environment boundary runnable and inspectable
while excluding proof bodies, provider payloads, private logs, oracle IDs, and
release claims.

## Public Contract

The input bundle names:

- `source_pattern_ids` for the macro pattern being projected.
- `source_refs` for the real corpus-readiness, tactic-affordance, Mathlib probe,
  and tactic-portfolio source artifacts.
- `source_digests` for the copied non-secret macro sources:
  `sha256:c413608118229bea32062ce9b8b5af393bcd5f63bbf1030983e98ffa6d07778d`
  for `corpus_readiness.json`,
  `sha256:20fdef8a53401f2bb21483002730895ca0295d2170bf148e8c328c041d8524c3`
  for `tactic_affordance_probe.json`,
  `sha256:8c020f6884cda37338cb5216ded61722a9993fcd6d69aee1db655885738abbd1`
  for `mathlib_probe.lean`, and
  `sha256:405efadd8045057279a4481c05cdea8e1d99fceee253809526fb37675889d712`
  for the tactic portfolio availability result.
- `body_material_status` and corpus/toolchain readiness statuses that identify
  copied non-secret macro substrate rather than synthetic metadata.
- `corpora` with corpus status, Lean availability, Mathlib import probe status,
  translation-smoke flags, and consumer rules.
- `consumer_gate_cases` that decide whether downstream work is allowed or
  blocked before proof execution.
- `secret_exclusion_scan` receipts that prove excluded bodies stayed out of the
  public receipt stream.
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

These negative cases are regression-only leakage guards. They are not product
evidence and cannot substitute for the copied corpus readiness substrate.

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

This module validates copied non-secret corpus/toolchain readiness substrate from
the 2026-05-11 proof-state curriculum smoke run. It does not run Lean or Lake,
claim Mathlib availability beyond the recorded failed probe, prove theorem
correctness, benchmark formal-math corpora, expose proof bodies, call providers,
or authorize release.
