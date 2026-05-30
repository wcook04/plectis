# Cognitive Operator Registry

`cognitive_operator_registry` is the public contract diagnostic for the macro
system's typed cognitive-operator substrate. It checks that each public operator
row carries the required operator-shape fields, that every `active` operator is
backed by a dogfood receipt proving it changed a live decision, and that the
registry policy declares explicit authority ceilings before a cold reader trusts
the operators as real reusable cognition rather than inspirational prose.

It consumes public `operator_registry.json`, `operator_standard.json`, and
`dogfood_index.json` inputs that project real macro operator rows and dogfood
receipts. Its receipt contract is source-open by default: `secret_exclusion_scan`
proves that secrets, account/session material, provider payload bodies, raw
operator voice, and credential-equivalent live-access material are excluded,
while `public_runtime_refs` point at the real standard, organ, acceptance,
fixture, bundle, and paper-module substrate. Bodies are not inlined into JSON
receipts, so the positive evidence uses `body_in_receipt: false`,
`real_runtime_receipt: true`, and `synthetic_receipt_standin_allowed: false`.

The organ rejects seven boundary failures:

- operator rows missing required operator-shape fields
- active operators with no backing dogfood receipt
- dogfood receipts missing `cognition_delta_evidence`
- near-duplicate operators (identical slug or near-identical claim) with no
  recorded accretion decision (the anti-sprawl governor case)
- release, provider, source-mutation, registry-mutation, or operator-correctness
  overclaims
- operator rows that claim operator-voice or raw-seed authority
- private operator source bodies or provider payload bodies in public inputs

The exported bundle also imports three verbatim macro bodies behind an import
membrane: the cognitive-operator registry (`codex/doctrine/cognitive_operators.json`),
the cognitive-operator standard (`codex/standards/std_cognitive_operator.json`),
and the registry projection/validation tool
(`system/lib/cognitive_operator_registry.py`). Each is copied byte-for-byte with a
sha256 digest and required anchors; receipts carry refs, hashes, counts, and
verdicts only.

Authority ceiling: this is a projection-only diagnostic. It does not become
source authority for the cognitive-operator registry, mutate operators, prove
operator correctness, expose private operator bodies or raw operator voice,
authorize providers, or authorize release.
