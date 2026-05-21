# Formal Math Readiness Gate

## Teleology

`formal_math_readiness_gate` is the public runtime cell that turns the formal
math tranche from a deferred slogan into an executable boundary. It validates
synthetic readiness metadata for corpus availability, tactic probes, premise
indexes, target-shape routing, and provider context recipes before any future
Lean witness can claim authority.

## Public Contract

The organ does not run Lean or Lake. It consumes public JSON fixtures and
exported bundles, records which capabilities are available or blocked, rejects
Mathlib availability overclaims, rejects unprobed tactics, rejects premise
rows that contain proof bodies, rejects routes that admit unavailable tactics,
and rejects provider recipes that exceed the public budget or allow proof
bodies.

The accepted result is a readiness board. That board can tell a later organ
what is safe to attempt, but it is not proof evidence, benchmark evidence, or
permission to execute a theorem prover.

## Runtime Surfaces

- `python -m microcosm_core.organs.formal_math_readiness_gate run --input fixtures/first_wave/formal_math_readiness_gate/input --out receipts/first_wave/formal_math_readiness_gate`
- `python -m microcosm_core.organs.formal_math_readiness_gate run-readiness-bundle --input examples/formal_math_readiness_gate/exported_formal_math_readiness_bundle --out receipts/runtime_shell/demo_project/organs/formal_math_readiness_gate`
- `microcosm formal-math-readiness-gate run --input fixtures/first_wave/formal_math_readiness_gate/input --out receipts/first_wave/formal_math_readiness_gate`

## Receipt Expectations

The fixture run emits:

- `receipts/first_wave/formal_math_readiness_gate/readiness_gate_result.json`
- `receipts/first_wave/formal_math_readiness_gate/formal_math_readiness_board.json`
- `receipts/first_wave/formal_math_readiness_gate/formal_math_readiness_validation_receipt.json`
- `receipts/acceptance/first_wave/formal_math_readiness_gate_fixture_acceptance.json`

The runtime-shell bundle run emits
`receipts/runtime_shell/demo_project/organs/formal_math_readiness_gate/exported_formal_math_readiness_bundle_validation_result.json`.

## Relationship To Lean Witness

`formal_math_lean_proof_witness` remains deferred. This gate makes the deferral
typed and testable: Mathlib is absent until a passing probe says otherwise,
unavailable tactics cannot be routed, premise indexes cannot carry proof or
oracle bodies, and provider recipes cannot smuggle proof-body deliverables.

## Anti-Claim

This module documents a public readiness gate only. It does not authorize
Lean/Lake execution, formal proof authority, Mathlib-dependent proof attempts,
provider calls, benchmark claims, public release, hosted-public readiness,
publication, recipient work, private-data equivalence, or whole-system
correctness.
