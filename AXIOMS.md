# Axioms

These axioms are the basic rules of Microcosm, and every principle rests on
one or more of them. An axiom states a rule the code is meant to follow; how
well the code follows it is computed separately for each axiom by the support
checker in `src/microcosm_core/validators/axiom_support_cover.py`.

For each axiom, `core/axiom_organ_routing.json` lists the principles that
apply it, the components and files that test it, the failure modes that break
it, its negative test cases, the limit on what its support may claim, and any
unfinished work recorded as a layer-debt receipt. This file is the readable
version. The automated checks read the JSON file.

## Axioms At A Glance

| ID | Axiom | Anti-axiom |
| --- | --- | --- |
| AX-1 | Derivation before assertion | A label is true because someone asserted it. |
| AX-2 | Kernelized verification | Trust in the producer stands in for a check. |
| AX-3 | Authority by derivation, not possession | Holding a standing credential is enough to act. |
| AX-4 | Content-addressed determinism | A cached result is reused by name after its inputs change. |
| AX-5 | Fail-closed monotone lattice | A part with no evidence passes by default. |
| AX-6 | Open-world epistemics | Finding no evidence of something shows it is absent. |
| AX-7 | Typed partiality and refusal | An invalid input still yields a number, or a silent NaN. |
| AX-8 | Provenance propagation and non-interference | A label asserted at the end replaces tracking the data's origin. |
| AX-9 | Compensable transactional effects | An irreversible write is made with no way to undo it. |
| AX-10 | Temporal validity and freshness contracts | A live count is written down with no way to refresh it. |
| AX-11 | Executable grammar before doctrine authority | Prose claims the authority of an executable rule. |
| AX-12 | Reflexive accountability / no privileged meta-layer | Microcosm's own files are exempt from its rules. |

## AX-1 Derivation before assertion

Formal clause: for any claim `phi` over basis `B`, admissibility requires a
derivation certificate `c` and checker `K` such that `K(B,c,phi)=accept`, with
`strength(phi) <= strength(K(B,c,phi))`; bare assertion has bottom evidence.

Lineage: Curry-Howard proof terms, proof-carrying code, verifiable computation.

Route: recorded as strongly witnessed by
`agent_sabotage_scheming_monitor_replay`, `belief_state_process_reward_replay`,
`evidence_truth_floor.py` and the evidence-class rows. Its negative fixtures
declare a verdict that does not follow from the lower-level evidence, and the
replay has to catch it.

Anti-axiom: a label is true because someone asserted it.

## AX-2 Kernelized verification

Formal clause: trusted claims are decided by a small checker `K` over
certificates `c`; producers emit certificates and the checker decides.

Lineage: de Bruijn criterion, LCF/Lean kernel architecture, proof by reflection.

Route: recorded as strongly witnessed by `certificate_kernel_execution_lab`,
`formal_math_lean_proof_witness`, the Crown Jewel common harness and the
generated Lean certificate modules. The tests feed in invalid proof witnesses
and require the checker to reject them.

Anti-axiom: trust in whoever produced a result stands in for a check.

## AX-3 Authority by derivation, not possession

Formal clause: `auth(subject,effect)` is derived from dereferenced tokens,
policy, proof refs, and world state; ambient identity is insufficient.

Lineage: object-capability systems, least authority, confused-deputy defenses.

Route: recorded as strongly witnessed by
`proof_derived_governed_mutation_authorization` and `mcp_tool_authority_replay`.
Before allowing a change, the authorizer opens the referenced proof, policy,
result record and rollback evidence and checks them, whatever credential the
caller holds.

Anti-axiom: holding a standing credential is enough to act.

## AX-4 Content-addressed determinism

Formal clause: for derived artifact `a=f(B)`, identity is `H(B)`; equal basis
may reuse, basis drift forces recompute, and missing basis is bottom.

Lineage: referential transparency, Merkle/content-addressed storage, hermetic
builds.

Route: recorded as strongly witnessed by `durable_agent_work_landing_replay`,
`macro_projection_import_protocol`, `command_run_singleflight.py` and the Crown
Jewel source-manifest checks. The tests reject a run whose source digest or
freshness inputs do not match the recorded ones. One layer-debt receipt is
open: a semantic freshness code that has not yet been written out as exact
public code.

Anti-axiom: a cached result is reused by name after its inputs have changed.

## AX-5 Fail-closed monotone lattice

Formal clause: `status(composite)=meet(status(parts))`; no evidence defaults to
blocked, and later stages may lower but not raise authority without a new
derivation.

Lineage: lattice information flow, fail-safe defaults, monotone dataflow.

Route: recorded as strongly witnessed by the Crown Jewel harness,
`release_export`, `organ_evidence_classes.json::fail_closed_no_default`, and
the private-state and secret-exclusion scans. The release tests block an
export that would leak a result record's body or use overclaiming language.

Anti-axiom: a part with no evidence passes silently by default.

## AX-6 Open-world epistemics

Formal clause: `not_proven(P)` does not imply `proven(not P)`; coverage is
closed-world only inside declared finite domains.

Lineage: open-world assumption, bounded closed-world assumption, soundness
versus completeness.

Route: recorded as strongly witnessed by `self_ignorance_coverage_ledger` and
`doctrine_fact_claim_audit`. Both record the gaps between what was declared and
what has been built, and leave everything outside the declared domains marked
unknown.

Anti-axiom: finding no evidence of something shows it is absent.

## AX-7 Typed partiality and refusal

Formal clause: a partial computation `g` is totalized as `Result`: `Ok(y)` when
`Pre(x)` holds, otherwise `Refusal(reason,evidence)`.

Lineage: partial functions, domain theory, Result/Maybe types.

Route: recorded as strongly witnessed by `finance_forecast_evaluation_spine`,
`corpus_readiness_mathlib_absence_gate`, the metabolism runtime and the finance
statistics modules. The tests require a typed refusal for an invalid forecast
horizon, for missing SciPy support, and for a claim that Mathlib is available
when it is not.

Anti-axiom: a computation given invalid input still returns a number, or a
silent NaN.

## AX-8 Provenance propagation and non-interference

Formal clause: data labels propagate along flows; untrusted labels reach
privileged sinks only through declared transforms satisfying sink policy.

Lineage: Denning information-flow lattice, Biba integrity, taint tracking,
non-interference.

Route: recorded as partially witnessed by
`indirect_prompt_injection_information_flow_policy_replay`, the private-state
and secret-exclusion scans, the release export gates, and the engine-room paper
modules on egress and public projection. Negative cases cover private-state
classes and leaks into public pages. One layer-debt receipt is open: labels are
not yet tracked across a general graph of flows.

Anti-axiom: a label asserted at the end of a pipeline replaces tracking where
the data came from.

## AX-9 Compensable transactional effects

Formal clause: an effect requires a compensator or declared irreversible
boundary; multi-step effects land as a saga with compare-and-swap and
single-writer constraints.

Lineage: ACID, saga pattern, optimistic concurrency control.

Route: recorded as strongly witnessed by `mission_transaction_work_spine`,
`durable_agent_work_landing_replay`, `concurrency_mission_control`, the
work-landing tools and mission preflight. The tests block a change whose
parent commit does not match, two claims on the same path, and a change with
no evidence that the branch head moved.

Anti-axiom: an irreversible write is made with no way to undo it.

## AX-10 Temporal validity and freshness contracts

Formal clause: claims over live state are cached reads valid only under
`<value,as_of,basis,rederive>` invalidation contracts.

Lineage: cache invalidation, bitemporal state, staleness bounds.

Route: recorded as strongly witnessed by `doctrine_fact_claim_audit`, the
metabolism runtime, the derived-fact hologram source, and tests on numbers that
change over time. One layer-debt receipt is open: the stable semantic code this
route uses has not yet been written out.

Anti-axiom: a live count is written down with no way to refresh it.

## AX-11 Executable grammar before doctrine authority

Formal clause: `authority(d)` implies `d in L(G)`, required receipt
obligations, and anti-claim are present; prose alone is projection.

Lineage: formal languages, type systems, operational semantics, Hoare
contracts.

Route: recorded as strongly witnessed by `executable_doctrine_grammar`,
`standards_meta_diagnostics` and all public paper modules. The tests reject a
prose standard that claims executable authority, and a claim that passing the
grammar check means more than it does.

Anti-axiom: prose claims the authority of an executable rule.

## AX-12 Reflexive accountability / no privileged meta-layer

Formal clause: for every Microcosm artifact `a`, any claim `phi` carried by `a`
must satisfy the same admissibility relation as external claims.

Lineage: reflective systems, self-hosting checks, no-special-pleading
evaluation.

Route: recorded as strongly witnessed by
`batch12_release_claim_language_gate`, `executable_doctrine_grammar`, release
export, the Crown Jewel self-scans and `evidence_truth_floor.py`. The tests
block overclaiming release language, leaks of result-record bodies, and claims
that the doctrine is complete. One layer-debt receipt is open: the evidence
truth floor does not yet block at the release boundary.

Anti-axiom: Microcosm's own files are exempt from the rules it applies to
everything else.
