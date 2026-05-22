# Pattern Binding Contract

## Teleology

`pattern_binding_contract` is the public root organ that binds synthetic pattern
rows to source-available source capsules, authority-chain handles, anti-claims, and
omission receipts.

## Public Contract

The validator checks required binding fields, duplicate pattern conflicts,
unsupported authority-chain handles, unresolved reference capsules, private-body
sentinels, and public-leaf overclaim failures. It emits command-owned receipts
under `receipts/first_wave/pattern_binding_contract/`.

## Receipt Expectations

The primary receipt is
`receipts/first_wave/pattern_binding_contract/pattern_binding_validation_result.json`.
Supporting receipts include source capsules, omission receipts, reference
capsule resolver receipts, and authority-chain resolver receipts.

## Anti-Claim

This module documents public synthetic pattern-binding mechanics only. It does
not certify the private pattern ledger, public release operations, hosted-public
readiness, publication, recipient work, provider calls, private-data
equivalence, or whole-system correctness.
