# Formal Math Verifier Trace Repair Loop

`formal_math_verifier_trace_repair_loop` is the source-available replay of a macro
proof-lab pattern over copied Ring2 run substrate: verifier feedback becomes a
teaching signal only after a trace grade, a repair action, a failure-mode ledger
append, a curriculum delta, and a cold rerun receipt.

It is deliberately not a Lean/Lake proof organ. It sits between the existing
readiness, premise retrieval, tactic routing, proof diagnostic, and Lean witness
surfaces so a cold reader can inspect real failure taxonomy, graph-update
candidates, and oracle-repair contrast rows without seeing proof bodies, oracle
premise ids, provider payload bodies, or private run logs.

## Runtime

- Organ runner: `python -m microcosm_core.organs.formal_math_verifier_trace_repair_loop run --input fixtures/first_wave/formal_math_verifier_trace_repair_loop/input --out receipts/first_wave/formal_math_verifier_trace_repair_loop`
- Exported bundle runner: `python -m microcosm_core.organs.formal_math_verifier_trace_repair_loop run-loop-bundle --input examples/formal_math_verifier_trace_repair_loop/exported_verifier_trace_repair_bundle --out receipts/runtime_shell/demo_project/organs/formal_math_verifier_trace_repair_loop`
- CLI: `microcosm formal-math-verifier-trace-repair-loop run-loop-bundle --input examples/formal_math_verifier_trace_repair_loop/exported_verifier_trace_repair_bundle --out receipts/runtime_shell/demo_project/organs/formal_math_verifier_trace_repair_loop`
- Standard: `standards/std_microcosm_formal_math_verifier_trace_repair_loop.json`
- Fixture manifest: `core/fixture_manifests/formal_math_verifier_trace_repair_loop.fixture_manifest.json`

## What It Proves

- A public verifier replay can require trace events before trace grades.
- Copied Ring2 failure rows can feed a repair curriculum without becoming proof
  authority.
- A repair action must name the verifier failure class it responds to.
- A failure-mode ledger update can be represented without proof bodies.
- Promotion requires a cold rerun receipt reference.
- Human or provider advice stays advisory until checker evidence exists.

## What It Refuses

- Proof bodies in public verifier traces.
- Oracle-needed premise ids in public inputs.
- Provider payload bodies in fixtures or receipts.
- Human approval as proof correctness.
- Release, publication, secret export, or general theorem-proving claims.

## Receipts

- `receipts/first_wave/formal_math_verifier_trace_repair_loop/formal_math_verifier_trace_repair_loop_result.json`
- `receipts/first_wave/formal_math_verifier_trace_repair_loop/verifier_trace_repair_board.json`
- `receipts/first_wave/formal_math_verifier_trace_repair_loop/formal_math_verifier_trace_repair_loop_validation_receipt.json`
- `receipts/acceptance/first_wave/formal_math_verifier_trace_repair_loop_fixture_acceptance.json`

The authority boundary is copied non-secret Ring2 verifier trace repair
public non-secret fields only. The organ demonstrates control-loop mechanics over real run
rows, not theorem correctness.
