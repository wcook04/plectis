# Pattern Binding Contract

## Teleology

`pattern_binding_contract` is the public root organ that binds pattern rows to
source-available source capsules, public runtime refs, authority-chain handles,
anti-claims, and secret-exclusion receipts. Synthetic rows are allowed only as
regression controls or negative cases; they are not product evidence.

## Public Contract

The validator checks required binding fields, duplicate pattern conflicts,
unsupported authority-chain handles, unresolved reference capsules,
secret/provider/operator body sentinels, and public-leaf overclaim failures. It
emits command-owned receipts under
`receipts/first_wave/pattern_binding_contract/`.

## Receipt Expectations

The primary receipt is
`receipts/first_wave/pattern_binding_contract/pattern_binding_validation_result.json`.
Supporting receipts include source capsules, omission receipts, reference
capsule resolver receipts, and authority-chain resolver receipts. Positive
receipts must expose `secret_exclusion_scan`, `body_in_receipt`,
`real_runtime_receipt`, `public_runtime_refs`, and
`synthetic_receipt_standin_allowed: false`.

## Anti-Claim

This module documents public pattern-binding mechanics and regression harnesses.
It does not certify the private pattern ledger, public release operations,
hosted-public readiness, publication, recipient work, provider calls,
private-data equivalence, or whole-system correctness.
