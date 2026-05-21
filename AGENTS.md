# AGENTS.md - Microcosm Substrate

This root is an executable research prototype of a local project operating
substrate. Treat it as the public runtime surface in front of you: a user can
bring a project folder, initialize `.microcosm/` state, index files, discover
patterns, propose routes, inspect route explanations, record work
transactions, observe events, and inspect evidence only when drilldown is
needed.

It is small on purpose: the public root should make the architecture legible
through project, catalog, pattern, standard, route, work, event, evidence,
explanation, and assimilation primitives, not through production claims.

## Accepted Public Runtime Spine

- `pattern_binding_contract`
- `executable_doctrine_grammar`
- `proof_diagnostic_evidence_spine`
- `formal_math_readiness_gate`
- `navigation_hologram_route_plane`
- `mission_transaction_work_spine`
- `agent_route_observability_runtime`
- `pattern_assimilation_step`

## Rules

1. Start with `README.md`, then run `skills/cold_start_navigation.md` if you
   need the shortest validation route.
2. The compressed product loop is `microcosm compile <project>`: repo -> `.microcosm`.
   The expanded loop is `microcosm init <project>`,
   `microcosm index <project>`, `microcosm architecture <project>`,
   `microcosm route <project>`, `microcosm explain <project> <route_id>`,
   `microcosm work run <project>`, `microcosm observe <project>`, and
   `microcosm evidence list <project>`.
   Public input bundles and organ demos are compatibility/regression surfaces,
   not the product center.
   Architecture primitives must resolve through the project-local pattern
   surface: catalog observations become `.microcosm/patterns.json`, routes
   carry `pattern_refs`, and explanations show resolved pattern bindings.
   Explanations must also resolve public standard pressure from
   `core/public_standard_pressure.json`; do not inline private doctrine or
   create a second pattern taxonomy.
   The causal chain must stay stable across `route`, `explain`, `work run`,
   `observe`, `graph`, and `evidence`: route refs, pattern bindings, standard
   bindings, work state, event ids, and evidence refs should agree.
   The local observatory is the first browser-facing cockpit for that chain:
   keep causal-chain sections legible before raw JSON drilldowns.
3. Fixtures Are Tests: fixtures under `fixtures/first_wave/**` are examples,
   bootstrap data, and negative cases. Do not treat fixture-only behavior as
   product-complete runtime behavior.
4. Receipts Are Evidence: generate receipts by running validators or
   `bootstrap.sh`; do not edit receipts by hand.
5. Treat `core/organ_registry.json`, `core/acceptance/first_wave_acceptance.json`,
   generated receipts, and public paper modules as public-root navigation
   surfaces.
6. Do not run Lean/Lake. `formal_math_lean_proof_witness` remains deferred.
7. Do not import parent-repository-only tools, host-local state, prompt bodies,
   provider payloads, operator threads, HUD/browser/cockpit state, or old
   scratch public-root content as source authority.
8. Do not add release, hosted-public, publication, recipient, provider-call, or
   private-data-equivalence surfaces from this root.
9. Keep research-prototype posture explicit. Do not describe this root as
   production infrastructure, a hosted service, or a release-ready agent
   platform.

## Receipt Floor

Every validator receipt must include `status`, `private_state_scan`,
`authority_ceiling`, `anti_claim`, and `receipt_paths`. Organ receipts also
include `organ_id` and `fixture_id`.

## Anti-Claim

This public agent entry file gives bounded public-root navigation only. It does
not authorize Lean/Lake, public release, hosted-public readiness, publication,
recipient work, provider calls, private-data equivalence, or whole-system
correctness.
