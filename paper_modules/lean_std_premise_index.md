# Lean/Std Premise Index

> **In plain terms.** A program that helps write proofs needs an index of known facts that matches its source and gives away no answers. This component is given such an index for the standard library of the proof-checking program Lean, listing each fact's name, source and allowed uses, plus copied source details. It matches entries to those details, checks that source files still match their stored fingerprints, and rejects entries from the Mathlib library, leaked proofs or answer keys, and tuning on the test portion. It reports a pass when the checks are met, and a mismatch flags a change to the copied index.

This component validates a public index of Lean and Std premise descriptors: names, namespaces, retrieval terms, split eligibility, and source references. It compares public rows with copied source metadata by premise ID and checks declared source digests. A toolchain path may be represented by a public `lean-toolchain://` reference.

The fixture rejects Mathlib premises, proof-body or oracle-ID leakage, test-split tuning, and a namespace without a source reference. Digest and row checks help identify changes to the copied index; they do not establish mathematical correctness. The validator does not run Lean or Lake or prove that a premise is useful in a new proof.

## Run the example

From the repository root with Python 3.11 or newer, run the supplied fixture into ignored local output:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.lean_std_premise_index run \
  --input fixtures/first_wave/lean_std_premise_index/input \
  --out .microcosm/component-guides/lean_std_premise_index/out \
  --acceptance-out .microcosm/component-guides/lean_std_premise_index/acceptance.json
```

The JSON result reports `status: pass` when the fixture meets its index and negative-case checks.

For related premise-retrieval work see [LeanDojo](https://arxiv.org/abs/2306.15626) and [HOList](https://arxiv.org/abs/1904.03241).

## Verification

The fixture and tests check premise metadata and copied-source agreement; they do not prove an indexing algorithm or run Lean. `make component-replays` runs the exported index bundle through the [shared Dafny admission check](../formal/replay/README.md) for agreement among supplied source, input, claim policy and receipt observations. The direct example does not invoke the admission check.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/lean_std_premise_index.py) and [fixture inputs](../fixtures/first_wave/lean_std_premise_index/input/).
- [Tests](../tests/test_lean_std_premise_index.py).
- [Saved example result](../receipts/first_wave/lean_std_premise_index/lean_std_premise_index_result.json) (historical, not a fresh run).
- [Component JSON record](./lean_std_premise_index.json) and [canonical capsule](../core/paper_module_capsules.json).
