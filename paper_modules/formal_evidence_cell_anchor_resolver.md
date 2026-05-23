# Formal Evidence Cell Anchor Resolver

`formal_evidence_cell_anchor_resolver` makes Microcosm's formal-math evidence
claims inspectable without turning receipt summaries into proof authority. It
resolves fixture-backed paper-module claims to evidence-cell ids,
checks source-anchor refs, records machine-anchor classes, and enforces a claim
strength boundary before any proof-language claim can pass.

It is not a theorem prover. It does not execute Lean or Lake, expose proof
bodies, expose private source refs, call providers, or claim theorem
correctness. It emits real runtime receipts over the imported evidence-cell
substrate and uses secret-exclusion scanning only for credential-equivalent or
non-receipt body payloads.

## Runtime

- Organ runner: `python -m microcosm_core.organs.formal_evidence_cell_anchor_resolver run --input fixtures/first_wave/formal_evidence_cell_anchor_resolver/input --out receipts/first_wave/formal_evidence_cell_anchor_resolver`
- Exported bundle runner: `python -m microcosm_core.organs.formal_evidence_cell_anchor_resolver run-anchor-bundle --input examples/formal_evidence_cell_anchor_resolver/exported_evidence_cell_anchor_bundle --out receipts/runtime_shell/demo_project/organs/formal_evidence_cell_anchor_resolver`
- CLI: `microcosm formal-evidence-cell-anchor-resolver run-anchor-bundle --input examples/formal_evidence_cell_anchor_resolver/exported_evidence_cell_anchor_bundle --out receipts/runtime_shell/demo_project/organs/formal_evidence_cell_anchor_resolver`
- Standard: `standards/std_microcosm_formal_evidence_cell_anchor_resolver.json`
- Fixture manifest: `core/fixture_manifests/formal_evidence_cell_anchor_resolver.fixture_manifest.json`

## What It Proves

- Proof-language claims must resolve to a public evidence cell.
- Evidence cells must carry source-anchor refs.
- Machine-anchor metadata is visible as metadata, not proof correctness.
- Claim strength is bounded by the resolved cell.
- Secret, credential-equivalent, or non-receipt body payloads must have explicit
  exclusion receipts.

## What It Refuses

- Unknown evidence-cell ids used as proof authority.
- Proof-language claims without evidence-cell ids.
- Proof bodies in public claim rows.
- Private source refs in public claim or cell rows.
- Human approval as proof authority.
- Theorem-correctness claims from metadata cells.
- Release, publication, secret export, or provider authority.

## Receipts

- `receipts/first_wave/formal_evidence_cell_anchor_resolver/formal_evidence_cell_anchor_resolver_result.json`
- `receipts/first_wave/formal_evidence_cell_anchor_resolver/evidence_cell_anchor_board.json`
- `receipts/first_wave/formal_evidence_cell_anchor_resolver/formal_evidence_cell_anchor_resolver_validation_receipt.json`
- `receipts/acceptance/first_wave/formal_evidence_cell_anchor_resolver_fixture_acceptance.json`

The authority boundary is evidence-cell anchor resolution backed by real runtime
receipts. The organ makes claim boundaries legible; it does not certify
mathematical truth.
