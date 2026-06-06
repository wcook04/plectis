# Principles

Principles are operational projections of the axioms. They tell a Type A agent
what to do with a shard before it mutates, validates, documents, routes, or
publishes anything. Each principle is grounded in `core/axiom_organ_routing.json`.

## Principles At A Glance

| ID | Principle | Grounding |
| --- | --- | --- |
| P-1 | Recompute, do not echo | AX-1. |
| P-2 | Lower claim strength to checker strength | AX-1, AX-5. |
| P-3 | Concentrate trust in small checkers | AX-2. |
| P-4 | Possession is not permission | AX-3. |
| P-5 | Cache by content, not by name | AX-4. |
| P-6 | Status fails closed | AX-5. |
| P-7 | Track known unknowns without claiming the unknown is mapped | AX-6. |
| P-8 | Refuse inadmissible computations with typed reasons | AX-7. |
| P-9 | Preserve provenance across every boundary | AX-8. |
| P-10 | Do not land effects without compensation | AX-9. |
| P-11 | Bind volatile facts to refresh routes | AX-10. |
| P-12 | Make doctrine executable before authoritative | AX-11. |
| P-13 | Apply the same floor to meta artifacts | AX-12. |
| P-14 | Carry basis and provenance together | AX-4, AX-8. |
| P-15 | Keep projections below source authority | AX-4, AX-5, AX-11. |
| P-16 | Bind authority to transaction scope | AX-3, AX-9. |
| P-17 | Anchor graph mutations to unique source rows | AX-4, AX-9, AX-11. |
| P-18 | Require fan-in before activation | AX-3, AX-9, AX-11, AX-12. |
| P-19 | Classify residual pressure before wiring | AX-5, AX-6, AX-11. |
| P-20 | Bind receipts before record authority | AX-11, AX-12. |

## P-1 Recompute, do not echo

Grounding: AX-1.
Obligation grounding: AX-1.O1.certificate_exists, AX-1.O2.checker_accepts, AX-1.O3.claim_ceiling, AX-1.O4.bare_assertion_bottom.

Do not trust a fixture label, declared verdict, route status, count, or public
copy line as proof. Recompute the verdict from lower-level evidence and keep a
negative fixture where the cheap lie fails.

## P-2 Lower claim strength to checker strength

Grounding: AX-1, AX-5.
Obligation grounding: AX-1.O1.certificate_exists, AX-1.O2.checker_accepts, AX-1.O3.claim_ceiling, AX-1.O4.bare_assertion_bottom, AX-5.O1.composite_status_meets_parts, AX-5.O2.no_evidence_defaults_blocked, AX-5.O3.authority_cannot_raise_without_derivation.

The claim ceiling is the strongest thing the named checker, validator, registry,
or witness route actually computes. If the checker decides only a local
contract, do not let prose project global authority.

## P-3 Concentrate trust in small checkers

Grounding: AX-2.
Obligation grounding: AX-2.O1.small_checker_decides, AX-2.O2.producer_emits_certificate, AX-2.O3.invalid_proof_rejected.

Prefer a small verifier, parser, harness, compiler route, registry contract, or
kernel over broad narrative confidence. Producers may be large; the authority
boundary should be small enough to inspect and rerun.

## P-4 Possession is not permission

Grounding: AX-3.
Obligation grounding: AX-3.O1.authorization_is_derived, AX-3.O2.standing_credential_insufficient, AX-3.O3.tool_effects_require_declared_scope.

Authority comes from dereferenced proof, policy, receipt, rollback evidence,
and current world state. Credentials, role names, admin phrasing, or "trusted
session" language cannot authorize mutation by themselves.

## P-5 Cache by content, not by name

Grounding: AX-4.
Obligation grounding: AX-4.O1.content_basis_digest_declared, AX-4.O2.equal_basis_permits_reuse, AX-4.O3.digest_drift_forces_recompute, AX-4.O4.freshness_basis_mismatch_materialized.

A reusable receipt, command result, source import, or work-landing attempt must
carry its content basis. Drift in source bytes, dirty scoped files, parent SHA,
or fixture input invalidates reuse.

## P-6 Status fails closed

Grounding: AX-5.
Obligation grounding: AX-5.O1.composite_status_meets_parts, AX-5.O2.no_evidence_defaults_blocked, AX-5.O3.authority_cannot_raise_without_derivation.

Missing evidence, policy files, source digests, secret scans, negative cases, or
receipt self-scans block or demote. A downstream projection can explain a pass;
it cannot upgrade a blocked source truth.

## P-7 Track known unknowns without claiming the unknown is mapped

Grounding: AX-6.
Obligation grounding: AX-6.O1.closed_world_domain_declared, AX-6.O2.absence_not_negation, AX-6.O3.fact_claims_cite_loci_and_dag.

Coverage reports name declared domains and materialized gaps. They must not say
that unmapped space is safe, complete, exhausted, or irrelevant.

## P-8 Refuse inadmissible computations with typed reasons

Grounding: AX-7.
Obligation grounding: AX-7.O1.ok_under_precondition, AX-7.O2.refusal_carries_reason_evidence, AX-7.O3.absent_library_refuses_not_overclaims.

When preconditions fail, return a reasoned refusal. Do not emit meaningless
statistics, proof authority, safety verdicts, or public-readiness status just to
keep a green path.

## P-9 Preserve provenance across every boundary

Grounding: AX-8.
Obligation grounding: AX-8.O1.label_propagation, AX-8.O2.sink_policy, AX-8.O3.lying_endpoint_rejected.

Every shard crossing from macro source, fixture, receipt, public copy, provider
shape, or private-root adjacency must carry a provenance class and claim
ceiling. If the flow is only declared or endpoint-labeled, say so.

## P-10 Do not land effects without compensation

Grounding: AX-9.
Obligation grounding: AX-9.O1.effect_boundary_declared, AX-9.O2.cas_parent_enforced, AX-9.O3.single_writer_claim_constraint.

Writes, release steps, claim release, source imports, and rollback-shaped
operations need ordered transaction evidence. Release locks after durable
records, recompute after release, and block stale parent or same-path conflicts.

## P-11 Bind volatile facts to refresh routes

Grounding: AX-10.
Obligation grounding: AX-10.O1.live_claim_carries_freshness_contract, AX-10.O2.stale_basis_requires_rederive, AX-10.O3.volatile_numeric_unbound_blocked.

Counts, "current" states, live route totals, CI floors, body-import floors, and
readiness signals must cite how they can be re-derived. If they cannot, keep
them out of durable prose or mark them as dated snapshots.

## P-12 Make doctrine executable before authoritative

Grounding: AX-11.
Obligation grounding: AX-11.O1.grammar_membership_required, AX-11.O2.receipts_and_anti_claims_present, AX-11.O3.prose_alone_is_projection.

A doctrine surface earns authority through grammar, required fields, receipt
obligations, anti-claims, and validator coverage. Prose can orient a reader,
but it cannot become substrate authority without an executable contract.

## P-13 Apply the same floor to meta artifacts

Grounding: AX-12.
Obligation grounding: AX-12.O1.microcosm_claims_use_same_gate, AX-12.O2.release_claim_language_blocked, AX-12.O3.receipt_body_and_doctrine_overclaim_blocked, AX-12.O4.evidence_truth_floor_blocks_release.

Microcosm artifacts about Microcosm do not get exemptions. Standards, paper
modules, ledgers, routes, generated projections, and release claims must satisfy
the same evidence, anti-claim, and refusal floors they impose on other shards.

## P-14 Carry basis and provenance together

Grounding: AX-4, AX-8.
Obligation grounding: AX-4.O1.content_basis_digest_declared, AX-4.O2.equal_basis_permits_reuse, AX-4.O3.digest_drift_forces_recompute, AX-4.O4.freshness_basis_mismatch_materialized, AX-8.O1.label_propagation, AX-8.O2.sink_policy, AX-8.O3.lying_endpoint_rejected.

Content basis says which bytes or rows were used; provenance says where they may
flow and how strongly they may be claimed. A shard missing either side is not
fully routed.

## P-15 Keep projections below source authority

Grounding: AX-4, AX-5, AX-11.
Obligation grounding: AX-4.O1.content_basis_digest_declared, AX-4.O2.equal_basis_permits_reuse, AX-4.O3.digest_drift_forces_recompute, AX-4.O4.freshness_basis_mismatch_materialized, AX-5.O1.composite_status_meets_parts, AX-5.O2.no_evidence_defaults_blocked, AX-5.O3.authority_cannot_raise_without_derivation, AX-11.O1.grammar_membership_required, AX-11.O2.receipts_and_anti_claims_present, AX-11.O3.prose_alone_is_projection.

Generated docs, markdown summaries, route cards, and paper modules may expose a
source truth, but they cannot upgrade it. Recompute from source or demote when
the source basis, grammar, or status lattice no longer supports the projection.

## P-16 Bind authority to transaction scope

Grounding: AX-3, AX-9.
Obligation grounding: AX-3.O1.authorization_is_derived, AX-3.O2.standing_credential_insufficient, AX-3.O3.tool_effects_require_declared_scope, AX-9.O1.effect_boundary_declared, AX-9.O2.cas_parent_enforced, AX-9.O3.single_writer_claim_constraint.

Mutation authority is not merely who can touch a file. It is the combination of
proof-derived permission, claimed write scope, current parent state,
compensation, and landing evidence for this transaction.

## P-17 Anchor graph mutations to unique source rows

Grounding: AX-4, AX-9, AX-11.
Obligation grounding: AX-4.O1.content_basis_digest_declared, AX-4.O2.equal_basis_permits_reuse, AX-4.O3.digest_drift_forces_recompute, AX-4.O4.freshness_basis_mismatch_materialized, AX-9.O1.effect_boundary_declared, AX-9.O2.cas_parent_enforced, AX-9.O3.single_writer_claim_constraint, AX-11.O1.grammar_membership_required, AX-11.O2.receipts_and_anti_claims_present, AX-11.O3.prose_alone_is_projection.

Before adding or removing a lattice edge in a repeated registry, anchor the
mutation to the unique source row, target id, and builder route that will
consume it. A generated projection, count delta, or nearby repeated key cannot
substitute for that row-level basis.

## P-18 Require fan-in before activation

Grounding: AX-3, AX-9, AX-11, AX-12.
Obligation grounding: AX-3.O1.authorization_is_derived, AX-3.O2.standing_credential_insufficient, AX-3.O3.tool_effects_require_declared_scope, AX-9.O1.effect_boundary_declared, AX-9.O2.cas_parent_enforced, AX-9.O3.single_writer_claim_constraint, AX-11.O1.grammar_membership_required, AX-11.O2.receipts_and_anti_claims_present, AX-11.O3.prose_alone_is_projection, AX-12.O1.microcosm_claims_use_same_gate, AX-12.O2.release_claim_language_blocked, AX-12.O3.receipt_body_and_doctrine_overclaim_blocked, AX-12.O4.evidence_truth_floor_blocks_release.

A staged law, standard, organ, or projection is not active authority until its
owner boundary, source row, generated parity, validation receipt, and status
transition have landed in the same governed transaction or an explicit blocked
receipt preserves the frontier. A projection generated from source authority
held dirty by another live owner is still outside fan-in; request handoff,
owner landing, or a blocked receipt before treating it as current. Partial
admission must remain residual pressure.

## P-19 Classify residual pressure before wiring

Grounding: AX-5, AX-6, AX-11.
Obligation grounding: AX-5.O2.no_evidence_defaults_blocked, AX-5.O3.authority_cannot_raise_without_derivation, AX-6.O1.closed_world_domain_declared, AX-6.O2.absence_not_negation, AX-6.O3.fact_claims_cite_loci_and_dag, AX-11.O1.grammar_membership_required, AX-11.O2.receipts_and_anti_claims_present, AX-11.O3.prose_alone_is_projection.

A residual is a typed pressure route, not an edge. Before wiring a missing
neighbour, classify the declared domain, source row, target resolution,
fillability, evidence floor, and anti-claim. A candidate route, generated
neighbour hint, basename match, singleton match, or stale projection row is
still pressure; it becomes an edge only when the current source authority row
names the relation and the target resolves under the builder. Bidirectional
substrate representation follows the same floor: principle-to-substrate edges
must be source-derived, and substrate-to-principle evidence may refine governed
ids only when current source rows name the relation. Neither direction is
support proof, projection authority, or permission to launder residual pressure
into an edge. If the substrate cannot name the target from source authority,
keep the gap residual and make the re-entry computable instead of inventing a
relationship or whitening the health card.

## P-20 Bind receipts before record authority

Grounding: AX-11, AX-12.
Obligation grounding: AX-11.O1.grammar_membership_required, AX-11.O2.receipts_and_anti_claims_present, AX-11.O3.prose_alone_is_projection, AX-12.O1.microcosm_claims_use_same_gate, AX-12.O3.receipt_body_and_doctrine_overclaim_blocked, AX-12.O4.evidence_truth_floor_blocks_release.

A doctrine record is not fully active by projection alone. Bind validator
receipts, evidence refs, omissions, anti-claims, and authority ceilings on the
record before treating its JSON, markdown, routing edge, or public copy as
current substrate authority.

## Anti-Claim

These principles do not authorize release, hosted operation, provider calls,
private-data export, financial advice, production safety claims, proof
correctness beyond named verifier receipts, or whole-system completeness.
