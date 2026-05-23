# Standards Meta Diagnostics

`standards_meta_diagnostics` is the terminal public coverage diagnostic for the
Microcosm runtime spine. It checks that accepted adapter-backed organs remain
mapped to standards, runtime contracts, receipts, and explicit authority
ceilings before a cold reader trusts the spine as coherent.

It consumes public `standards_inventory.json`, `organ_runtime_contracts.json`,
and `diagnostic_policy.json` inputs backed by registry refs, runtime commands,
acceptance receipts, and the exported diagnostics bundle. Its receipt contract
is source-open by default: `secret_exclusion_scan` proves that secrets,
account/session material, provider payload bodies, raw operator bodies, and
credential-equivalent live-access material are excluded, while
`public_runtime_refs` point at the real standards, organ, acceptance, fixture,
bundle, and paper-module substrate. Bodies are not inlined into JSON receipts,
so the positive evidence uses `body_in_receipt: false`,
`real_runtime_receipt: true`, and
`synthetic_receipt_standin_allowed: false`.

The organ rejects five boundary failures:

- accepted organ rows without `standard_id` or `standard_ref`
- accepted organs missing from the standards inventory
- accepted organ rows without receipt refs
- release, provider, publication, secret export, trading/advice, or
  whole-system correctness overclaims
- private source bodies or provider payload bodies in public diagnostics

Authority ceiling: this is a projection-only diagnostic. It does not become
source authority for `core/standards_registry.json`, mutate source surfaces,
expose private macro material, authorize providers, authorize release, or prove
whole-system correctness.
