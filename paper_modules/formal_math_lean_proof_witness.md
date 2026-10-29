# Run a Lean and Lake proof witness

> **In plain terms.** Saying a proof was checked is different from showing that a checking program really ran on it. The component takes a small public project of very simple example theorems and needs Lean, a program that checks proofs, and its build tool, Lake. It runs both on the project and records each outcome, then checks that a wrong proof is rejected and that a file importing a forbidden library, Mathlib, is turned away. The result is a short saved record of those outcomes, usable as evidence that the checker really ran.

This fixture runs Lean and Lake on a small declared public project and records the subprocess outcomes in a bounded witness receipt. The fixture checks that an invalid proof is rejected, and separately checks a source file containing a forbidden Mathlib import. Negative manifest cases include a private source reference and an embedded proof body. The test suite checks the witness and its receipt redaction.

Runs Lean and Lake, which must be installed, on the small public fixture project and rejects an invalid proof, a forbidden Mathlib import and a manifest that carries a private source or a proof body. The exported bundle checks the recorded results instead of rebuilding.

## Run the example

Python 3.11 or later is required. From the repository root, write the fixture result and acceptance record to ignored local state. Install the Lean toolchain and Lake specified by the fixture first.

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.formal_math_lean_proof_witness run --input fixtures/first_wave/formal_math_lean_proof_witness/input --out .microcosm/component-guides/formal_math_lean_proof_witness --acceptance-out .microcosm/component-guides/formal_math_lean_proof_witness/acceptance.json --card
```

## Verification

With Lean and Lake installed, the direct fixture builds the public project containing `nat_add_zero_public` and the other declared toy theorems. `make component-replays` also runs the native Lean and Lake fixture for this component, then checks its captured observations with the [shared Dafny admission core](../formal/replay/README.md). The standalone exported-bundle validator is a separate route and does not freshly build the project. Neither check proves the Python wrapper correct.

## Source

[Implementation](../src/microcosm_core/organs/formal_math_lean_proof_witness.py) · [Input](../fixtures/first_wave/formal_math_lean_proof_witness/input) · [Tests](../tests/test_formal_math_lean_proof_witness.py) · [Historical sample](../receipts/first_wave/formal_math_lean_proof_witness/formal_math_lean_proof_witness_result.json) · [JSON record](formal_math_lean_proof_witness.json)

For background on Lean, see its [system description](https://www.microsoft.com/en-us/research/publication/the-lean-theorem-prover-system-description/).
