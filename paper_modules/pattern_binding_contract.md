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

The exported substrate bundle also carries the macro route-readiness selector
overlays as public source-open bodies:
`examples/pattern_binding_contract/exported_route_readiness_bundle/`. The
validator recomputes the selector contract against the imported pattern ledger,
route-readiness audit, row-to-organ router, route cards, fixture specs, decision
matrix, dependency DAG, internal routing graph, and copied macro validation
report. This closes the old gap where a mined pattern row could look selectable
without opening the organ bundle that owns it.

Cold readers should use `microcosm pattern-route-readiness validate-bundle`
against `examples/pattern_binding_contract/exported_route_readiness_bundle/`
when the question is selector admission rather than generic pattern binding.
The older `pattern-binding validate-route-readiness-bundle` action remains a
compatibility route to the same validator.

## Receipt Expectations

The primary receipt is
`receipts/first_wave/pattern_binding_contract/pattern_binding_validation_result.json`.
Supporting receipts include source capsules, omission receipts, reference
capsule resolver receipts, and authority-chain resolver receipts. Positive
receipts must expose `secret_exclusion_scan`, `body_in_receipt`,
`real_runtime_receipt`, `public_runtime_refs`, and
`synthetic_receipt_standin_allowed: false`. The substrate-bundle receipt must
also expose `real_pattern_route_readiness_consumed`,
`route_readiness_summary`, `selection_contract`, `source_manifest`, and
`route_readiness_error_rules`. The standalone route-readiness receipt is
`receipts/first_wave/pattern_binding_contract/route_readiness/exported_route_readiness_bundle_validation_result.json`.

## Anti-Claim

This module documents public pattern-binding mechanics and regression harnesses.
It does not certify the private pattern ledger, public release operations,
hosted-public readiness, publication, recipient work, provider calls,
private-data equivalence, or whole-system correctness. Route-readiness import
does not make any mined pattern row a standalone public leaf; selection remains
organ-first and fixture-bound.
