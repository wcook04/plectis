# Principles

Each principle turns one or more axioms into a working rule. It tells an agent
working in this repository (a Type A agent) what to do with a piece of work
before changing, validating, documenting, routing or publishing anything. The
grounding for each principle is recorded in `core/axiom_organ_routing.json`.

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

Treat a fixture label, a declared verdict, a route status, a count or a line of
public copy as a statement to check. Recompute the verdict from the lower-level
evidence, and keep a negative fixture with a deliberately wrong label, so that a
check which only repeats labels fails.

## P-2 Lower claim strength to checker strength

Grounding: AX-1, AX-5.
Obligation grounding: AX-1.O1.certificate_exists, AX-1.O2.checker_accepts, AX-1.O3.claim_ceiling, AX-1.O4.bare_assertion_bottom, AX-5.O1.composite_status_meets_parts, AX-5.O2.no_evidence_defaults_blocked, AX-5.O3.authority_cannot_raise_without_derivation.

A claim may say no more than the named checker, validator, registry or witness
route actually computes. If the checker decides only a local contract, describe
the result as that local contract and nothing wider.

## P-3 Concentrate trust in small checkers

Grounding: AX-2.
Obligation grounding: AX-2.O1.small_checker_decides, AX-2.O2.producer_emits_certificate, AX-2.O3.invalid_proof_rejected.

Let a small verifier, parser, harness, compiler route, registry contract or
kernel decide what is trusted, in place of a broad written account of why a
result looks right. The code that produces results may be large; the code that
decides should be small enough for a person to read and rerun.

## P-4 Possession is not permission

Grounding: AX-3.
Obligation grounding: AX-3.O1.authorization_is_derived, AX-3.O2.standing_credential_insufficient, AX-3.O3.tool_effects_require_declared_scope.

Permission to change something comes from the referenced proof, policy, result
record and rollback evidence, each opened and checked, together with the current
state of the repository. A credential, a role name, administrator wording or a
phrase such as "trusted session" is never enough on its own to authorize a
change.

## P-5 Cache by content, not by name

Grounding: AX-4.
Obligation grounding: AX-4.O1.content_basis_digest_declared, AX-4.O2.equal_basis_permits_reuse, AX-4.O3.digest_drift_forces_recompute, AX-4.O4.freshness_basis_mismatch_materialized.

A saved result, command output, source import or work-landing attempt that may
be reused must record a hash of the exact content it was computed from. Any
change to the source bytes, to uncommitted files in its scope, to the parent
commit or to the fixture input means it has to be recomputed.

## P-6 Status fails closed

Grounding: AX-5.
Obligation grounding: AX-5.O1.composite_status_meets_parts, AX-5.O2.no_evidence_defaults_blocked, AX-5.O3.authority_cannot_raise_without_derivation.

A missing piece of evidence, policy file, source digest, secret scan, negative
case or self-scan of a result record blocks the result or lowers its status. A
generated summary further downstream can explain why something passed, and it
can never turn a blocked source into a pass.

## P-7 Track known unknowns without claiming the unknown is mapped

Grounding: AX-6.
Obligation grounding: AX-6.O1.closed_world_domain_declared, AX-6.O2.absence_not_negation, AX-6.O3.fact_claims_cite_loci_and_dag.

A coverage report names the domains it declared and the gaps it found inside
them. Anything outside those domains stays unknown, and the report must never
describe it as safe, complete, exhausted or irrelevant.

## P-8 Refuse inadmissible computations with typed reasons

Grounding: AX-7.
Obligation grounding: AX-7.O1.ok_under_precondition, AX-7.O2.refusal_carries_reason_evidence, AX-7.O3.absent_library_refuses_not_overclaims.

When a precondition fails, return a refusal that gives the reason. Never emit a
meaningless statistic, a proof status, a safety verdict or a public-readiness
status just to keep a pipeline green.

## P-9 Preserve provenance across every boundary

Grounding: AX-8.
Obligation grounding: AX-8.O1.label_propagation, AX-8.O2.sink_policy, AX-8.O3.lying_endpoint_rejected.

Every piece of data that moves out of the private source system, a fixture, a
result record, public copy, a provider's response format or material stored next
to the private root must carry a label saying where it came from and how
strongly it may be claimed. If the flow is only declared, or labelled only at
its end, say so.

## P-10 Do not land effects without compensation

Grounding: AX-9.
Obligation grounding: AX-9.O1.effect_boundary_declared, AX-9.O2.cas_parent_enforced, AX-9.O3.single_writer_claim_constraint.

Writes, release steps, releasing a claim on a path, source imports and anything
that can be rolled back need evidence that their steps ran in order as one
transaction. Release a lock only after the durable records are written,
recompute after the release, and block a change whose parent commit is stale or
whose path someone else has claimed.

## P-11 Bind volatile facts to refresh routes

Grounding: AX-10.
Obligation grounding: AX-10.O1.live_claim_carries_freshness_contract, AX-10.O2.stale_basis_requires_rederive, AX-10.O3.volatile_numeric_unbound_blocked.

Counts, "current" states, live route totals, CI minimums, body-import minimums
and readiness signals must say how they can be recomputed. If they cannot be
recomputed, leave them out of lasting prose or mark them as snapshots with a
date.

## P-12 Make doctrine executable before authoritative

Grounding: AX-11.
Obligation grounding: AX-11.O1.grammar_membership_required, AX-11.O2.receipts_and_anti_claims_present, AX-11.O3.prose_alone_is_projection.

A doctrine document gains authority only when it passes the grammar, has its
required fields, lists the result records it must produce and the statements of
what it does not cover (its anti-claims), and has a validator that checks it.
Until it has that executable contract, its prose can help a reader find their
way and has no authority over the system.

## P-13 Apply the same floor to meta artifacts

Grounding: AX-12.
Obligation grounding: AX-12.O1.microcosm_claims_use_same_gate, AX-12.O2.release_claim_language_blocked, AX-12.O3.receipt_body_and_doctrine_overclaim_blocked, AX-12.O4.evidence_truth_floor_blocks_release.

Files Microcosm writes about itself get no exemptions. Its standards, paper
modules, ledgers, routes, generated pages and release claims must meet the same
evidence, anti-claim and refusal requirements they apply to everything else.

## P-14 Carry basis and provenance together

Grounding: AX-4, AX-8.
Obligation grounding: AX-4.O1.content_basis_digest_declared, AX-4.O2.equal_basis_permits_reuse, AX-4.O3.digest_drift_forces_recompute, AX-4.O4.freshness_basis_mismatch_materialized, AX-8.O1.label_propagation, AX-8.O2.sink_policy, AX-8.O3.lying_endpoint_rejected.

The content hash records which bytes or rows were used; the provenance label
records where they may go and how strongly they may be claimed. A piece of data
needs both before it is fully routed.

## P-15 Keep projections below source authority

Grounding: AX-4, AX-5, AX-11.
Obligation grounding: AX-4.O1.content_basis_digest_declared, AX-4.O2.equal_basis_permits_reuse, AX-4.O3.digest_drift_forces_recompute, AX-4.O4.freshness_basis_mismatch_materialized, AX-5.O1.composite_status_meets_parts, AX-5.O2.no_evidence_defaults_blocked, AX-5.O3.authority_cannot_raise_without_derivation, AX-11.O1.grammar_membership_required, AX-11.O2.receipts_and_anti_claims_present, AX-11.O3.prose_alone_is_projection.

Generated docs, markdown summaries, route cards and paper modules may present
what the source says and may never raise it. When the source content, the
grammar or the source's status no longer supports a generated page, recompute
the page from the source or lower its status.

## P-16 Bind authority to transaction scope

Grounding: AX-3, AX-9.
Obligation grounding: AX-3.O1.authorization_is_derived, AX-3.O2.standing_credential_insufficient, AX-3.O3.tool_effects_require_declared_scope, AX-9.O1.effect_boundary_declared, AX-9.O2.cas_parent_enforced, AX-9.O3.single_writer_claim_constraint.

Permission to change a file depends on more than who has access to it. It
combines permission derived from a proof, the write scope claimed for this
change, the current parent commit, a way to undo the change, and evidence that
this particular transaction landed.

## P-17 Anchor graph mutations to unique source rows

Grounding: AX-4, AX-9, AX-11.
Obligation grounding: AX-4.O1.content_basis_digest_declared, AX-4.O2.equal_basis_permits_reuse, AX-4.O3.digest_drift_forces_recompute, AX-4.O4.freshness_basis_mismatch_materialized, AX-9.O1.effect_boundary_declared, AX-9.O2.cas_parent_enforced, AX-9.O3.single_writer_claim_constraint, AX-11.O1.grammar_membership_required, AX-11.O2.receipts_and_anti_claims_present, AX-11.O3.prose_alone_is_projection.

Before adding or removing a link between doctrine records in a registry where
keys repeat, tie the change to the one source row, the target id and the builder
that will read it. A generated page, a change in a count or a nearby key with
the same name is no substitute for that row.

## P-18 Require fan-in before activation

Grounding: AX-3, AX-9, AX-11, AX-12.
Obligation grounding: AX-3.O1.authorization_is_derived, AX-3.O2.standing_credential_insufficient, AX-3.O3.tool_effects_require_declared_scope, AX-9.O1.effect_boundary_declared, AX-9.O2.cas_parent_enforced, AX-9.O3.single_writer_claim_constraint, AX-11.O1.grammar_membership_required, AX-11.O2.receipts_and_anti_claims_present, AX-11.O3.prose_alone_is_projection, AX-12.O1.microcosm_claims_use_same_gate, AX-12.O2.release_claim_language_blocked, AX-12.O3.receipt_body_and_doctrine_overclaim_blocked, AX-12.O4.evidence_truth_floor_blocks_release.

A staged law, standard, component or generated page becomes active only when its
owner boundary, source row, matching generated output, validation result record
and status change have all landed in the same governed transaction, or when an
explicit blocked result record records where the work stopped. If the source a
page was generated from has uncommitted changes held by another active owner,
the page is not yet current; ask for a handoff, wait for that owner to land the
change, or write a blocked result record before treating the page as current.
Anything only partly admitted stays recorded as an open gap.

## P-19 Classify residual pressure before wiring

Grounding: AX-5, AX-6, AX-11.
Obligation grounding: AX-5.O2.no_evidence_defaults_blocked, AX-5.O3.authority_cannot_raise_without_derivation, AX-6.O1.closed_world_domain_declared, AX-6.O2.absence_not_negation, AX-6.O3.fact_claims_cite_loci_and_dag, AX-11.O1.grammar_membership_required, AX-11.O2.receipts_and_anti_claims_present, AX-11.O3.prose_alone_is_projection.

A residual is a recorded, typed gap where a link might belong, and it is kept
separate from the links themselves. Before wiring a missing neighbour, record
the declared domain, the source row, whether the target resolves, whether the
gap can be filled, the minimum evidence required, and the anti-claim. A
candidate route, a neighbour suggested by generated output, a matching file
name, a single match or a stale row in a generated page all remain gaps. A gap
becomes a link only when the current source row names the relation and the
builder resolves the target. The same rule applies in both directions between
principles and the system's code: a link from a principle to the code must come
from a source row, and evidence from the code may narrow which ids a principle
governs only when current source rows name the relation. Neither kind of link
counts as support for the principle or gives a generated page authority, and
neither may be used to turn a gap into a link. If the code cannot name the
target from a source row, keep the gap open and record how to return to it;
never invent a relationship or mark the health card clean to hide the gap.

## P-20 Bind receipts before record authority

Grounding: AX-11, AX-12.
Obligation grounding: AX-11.O1.grammar_membership_required, AX-11.O2.receipts_and_anti_claims_present, AX-11.O3.prose_alone_is_projection, AX-12.O1.microcosm_claims_use_same_gate, AX-12.O3.receipt_body_and_doctrine_overclaim_blocked, AX-12.O4.evidence_truth_floor_blocks_release.

Generating a doctrine record's pages does not make the record active. Attach its
validator result records, evidence references, omissions, anti-claims and
authority limits to the record before treating its JSON, markdown, routing link
or public copy as current and authoritative.

## Anti-Claim

Following these principles gives no permission to release, run a hosted service,
call a provider, export private data, give financial advice, claim production
safety, claim a proof is correct beyond what a named verifier's result record
shows, or claim the whole system is complete. Each of those is a separate
decision.
