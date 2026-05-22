# Lean/Std Premise Index

`lean_std_premise_index` is the closed public premise-index lane for the formal-math slice. It validates premise metadata that a cold reader can inspect without importing Mathlib, exposing proof bodies, or relying on private macro run state.

## Runtime Route

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.lean_std_premise_index run --input fixtures/first_wave/lean_std_premise_index/input --out receipts/first_wave/lean_std_premise_index --acceptance-out receipts/acceptance/first_wave/lean_std_premise_index_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli lean-std-premise-index run-index-bundle --input examples/lean_std_premise_index/exported_lean_std_premise_index_bundle --out receipts/runtime_shell/demo_project/organs/lean_std_premise_index
```

## Inputs

- `projection_protocol.json` records source pattern ids, macro source refs, public replacement refs, projection receipts, omitted material, and copy policy.
- `premise_index.json` carries public metadata rows: premise id, declaration name, namespace, `Init/` source ref, retrieval terms, and split eligibility.
- `index_policy.json` keeps the closed-index authority ceiling explicit.

## Negative Cases

The fixture rejects Mathlib premise refs, proof-body leakage, oracle-needed premise ids, test-split tuning authority, and namespace rows without `Init/` source refs. These are stable negative cases because the index is intended to be useful without becoming proof authority.

## Authority Ceiling

This lane is metadata only. It does not run Lean or Lake, import Mathlib, expose proof bodies, expose oracle-needed premise ids, tune on test split truth, call providers, prove theorem correctness, authorize public release, or claim private-data equivalence.

## Receipts

The validator emits `lean_std_premise_index_result.json`, `lean_std_premise_index_board.json`, `lean_std_premise_index_validation_receipt.json`, and an acceptance receipt under `receipts/acceptance/first_wave/`. Runtime-shell execution emits `exported_lean_std_premise_index_bundle_validation_result.json`.
