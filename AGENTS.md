# AGENTS.md - Microcosm Substrate

This root is a standalone runnable substrate. Treat it as the runtime surface
in front of you: public commands, public input bundles, validators, receipts,
tests, and docs all live here.

## Accepted Public Runtime Spine

- `pattern_binding_contract`
- `executable_doctrine_grammar`
- `proof_diagnostic_evidence_spine`
- `navigation_hologram_route_plane`
- `mission_transaction_work_spine`
- `agent_route_observability_runtime`
- `pattern_assimilation_step`

## Rules

1. Start with `README.md`, then run `skills/cold_start_navigation.md` if you
   need the shortest validation route.
2. Fixtures Are Tests: fixtures under `fixtures/first_wave/**` are examples,
   bootstrap data, and negative cases. Do not treat fixture-only behavior as
   product-complete runtime behavior.
3. Receipts Are Evidence: generate receipts by running validators or
   `bootstrap.sh`; do not edit receipts by hand.
4. Treat `core/organ_registry.json`, `core/acceptance/first_wave_acceptance.json`,
   generated receipts, and public paper modules as public-root navigation
   surfaces.
5. Do not run Lean/Lake. `formal_math_lean_proof_witness` remains deferred.
6. Do not import parent-repository-only tools, host-local state, prompt bodies,
   provider payloads, operator threads, HUD/browser/cockpit state, or old
   scratch public-root content as source authority.
7. Do not add release, hosted-public, publication, recipient, provider-call, or
   private-data-equivalence surfaces from this root.

## Receipt Floor

Every validator receipt must include `status`, `private_state_scan`,
`authority_ceiling`, `anti_claim`, and `receipt_paths`. Organ receipts also
include `organ_id` and `fixture_id`.

## Anti-Claim

This public agent entry file gives bounded public-root navigation only. It does
not authorize Lean/Lake, public release, hosted-public readiness, publication,
recipient work, provider calls, private-data equivalence, or whole-system
correctness.
