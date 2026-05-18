# AGENTS.md - Microcosm Substrate

This public root is intentionally smaller than the source reconstruction
workspace. Treat it as a runnable public-safe slice, not as the private control
plane.

## Rules

1. Start with the first commands in `README.md`.
2. Use only synthetic fixtures under `fixtures/first_wave/**`.
3. Generate receipts by running validators or `bootstrap.sh`; do not edit
   receipts by hand.
4. Do not add later organs while working in this slice. The only implemented
   organ here is `pattern_binding_contract`.
5. Do not import private reconstruction tools, host-local state, prompt bodies,
   provider payloads, operator threads, HUD/browser/cockpit state, or the old
   scratch public root as source authority.

## Stop-Before Organs

- `executable_doctrine_grammar`
- `proof_diagnostic_evidence_spine`
- `formal_math_lean_proof_witness`
- `navigation_hologram_route_plane`
- `mission_transaction_work_spine`
- `agent_route_observability_runtime`
- `pattern_assimilation_step`

## Receipt Floor

Every validator receipt must include `status`, `organ_id`, `fixture_id`,
`private_state_scan`, `authority_ceiling`, `anti_claim`, and `receipt_paths`.
