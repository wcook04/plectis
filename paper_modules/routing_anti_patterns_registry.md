# Routing Anti-Patterns Registry

`routing_anti_patterns_registry` is the public contract diagnostic for the macro
system's typed navigation failure rows. It validates the copied
`codex/doctrine/routing_anti_patterns.json` registry as runnable Microcosm
substrate: the input must declare `kind: routing_anti_patterns`, carry a
positive version, and expose stable `anti_patterns` rows with unique ids and
plain explanatory text.

The positive fixture imports the real macro registry body. The exported runtime
bundle also carries a source module manifest and a byte-for-byte copy under
`source_modules/codex/doctrine/routing_anti_patterns.json`, with sha256 hashes
and anchors for `kernel_before_grep`, `bridge_before_scope`, and
`mode_in_chat_only`. Receipts carry refs, hashes, counts, and verdicts only;
they do not inline the copied body.

The organ rejects five boundary failures:

- missing `kind`
- duplicate anti-pattern ids
- anti-pattern rows missing explanatory text
- release, provider, source-mutation, route-policy mutation, maturity, or
  whole-system-correctness overclaims
- private routing bodies, raw seed bodies, provider payload bodies, or secret
  values in public inputs

Authority ceiling: this is a projection-only diagnostic. It does not become
route source authority, mutate routes, expose private routing notes, authorize
providers, authorize release, or prove whole-system correctness.
