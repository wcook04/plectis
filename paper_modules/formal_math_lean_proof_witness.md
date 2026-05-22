# Formal Math Lean Proof Witness

## Teleology

`formal_math_lean_proof_witness` is now the bounded public crossing from
formal-math readiness into an actual local Lean/Lake run. It exists so a cold
reader can see Microcosm compile a tiny synthetic proof witness with the
installed toolchain while the receipts stay redacted, public-relative, and
honest about the narrow authority boundary.

## Public Contract

The organ copies `examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle`
or the first-wave fixture Lake project into a temporary workspace and runs
`lake build`. The public receipt records tool availability, Lake build status,
source hashes, declaration names, line counts, negative-case coverage, and the
authority ceiling. It does not export proof bodies in JSON receipts.

The accepted witness scope is deliberately small:

- public synthetic Lean source is allowed;
- JSON manifests and receipts may not embed proof bodies;
- Mathlib, Aesop, and Batteries imports are rejected until a wider authority
  ceiling exists;
- private source refs, provider payloads, oracle proofs, and private macro run
  bodies remain outside the public root.

## Receipt Expectations

The owner command is:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.formal_math_lean_proof_witness run --input fixtures/first_wave/formal_math_lean_proof_witness/input --out receipts/first_wave/formal_math_lean_proof_witness
```

The runtime-shell bundle command is:

```bash
PYTHONPATH=src python3 -m microcosm_core.cli formal-math-lean-proof-witness run-witness-bundle --input examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle --out receipts/runtime_shell/demo_project/organs/formal_math_lean_proof_witness
```

Required receipts include:

- `receipts/first_wave/formal_math_lean_proof_witness/formal_math_lean_proof_witness_result.json`
- `receipts/first_wave/formal_math_lean_proof_witness/lean_proof_witness_board.json`
- `receipts/first_wave/formal_math_lean_proof_witness/formal_math_lean_proof_witness_validation_receipt.json`
- `receipts/acceptance/first_wave/formal_math_lean_proof_witness_fixture_acceptance.json`

## Anti-Claim

This module authorizes only a tiny public fixture witness compiled by local
Lean/Lake in a temporary workspace. It does not authorize Mathlib-dependent
proofs, provider calls, private proof import, benchmark performance claims,
release operations, hosted deployment, publication, recipient work,
secret export, or whole-system correctness.
