# Inspect proof and authority boundaries

> **In plain terms.** Having the code for a proof or permission check is not the same as that check making a decision. The component reads a list of copied program files and a few example cases. It only looks in the files for the code behind decisions such as rejecting a bundle whose fingerprint does not match, and scans a copied proof file for placeholders standing in for missing proofs. It also checks an example where Erdős problem 257 is wrongly claimed solved and, if the tools are installed, reports whether the proof file builds, fails or could not be tried. A placeholder scan is not a proof check, and even a successful build would not solve that problem.

This fixture checks source manifests and exercises selected proof, permission and runtime cases. Its result distinguishes source and fixture observations from claims about an actual proof or authorization decision.

## Run the example

From the repository root, with Python 3.11 or newer and the project dependencies installed:

```sh
PYTHONPATH=src python3 -m microcosm_core.organs.batch4_proof_authority_runtime run \
  --input fixtures/first_wave/batch4_proof_authority_runtime/input \
  --out .microcosm/component-guides/batch4_proof_authority_runtime/result \
  --acceptance-out .microcosm/component-guides/batch4_proof_authority_runtime/acceptance.json --card
```

The command prints a compact JSON card and writes its results under `.microcosm/component-guides/`. A passing run returns exit code 0; a blocked run returns 1.

## What this checks

The fixture checks copied-source anchors for packet digest rejection, forbidden context grants and stale closeout handling; those checks do not execute the corresponding decisions. It scans the copied Lean source for placeholder tokens and checks an Erdős solution-overclaim case. An optional Lean/Lake probe can report whether the copied file compiles, fails or is unavailable.

## Verification

The direct example runs the fixture; its optional Lean probe checks whether the copied `CertificateKernel.lean` elaborates, when its toolchain and project prerequisites are available. In `make component-replays`, the exported bundle also uses the [shared Dafny admission check](../formal/replay/README.md) for source, input, claim-policy and receipt agreement. Neither check proves an Erdős solution or the component’s algorithms.

## Limits

A token scan is not a proof check, and even successful local compilation does not establish a solution to Erdős #257. The optional probe needs Lean, Lake, the source Lake project and its dependencies; unavailable is distinct from a successful compilation.

## Source and evidence

Read the [implementation](../src/microcosm_core/organs/batch4_proof_authority_runtime.py), [fixture input](../fixtures/first_wave/batch4_proof_authority_runtime/input/batch4_probe_manifest.json), and [focused tests](../tests/test_batch4_proof_authority_runtime.py). The [saved acceptance result](../receipts/acceptance/first_wave/batch4_proof_authority_runtime_fixture_acceptance.json) is historical sample evidence, not the result of your run. The [JSON record](batch4_proof_authority_runtime.json) identifies the module; the canonical capsule metadata is in [paper_module_capsules.json](../core/paper_module_capsules.json).

Proof-carrying code is related background: see [Necula’s work](https://en.wikipedia.org/wiki/Proof-carrying_code).
