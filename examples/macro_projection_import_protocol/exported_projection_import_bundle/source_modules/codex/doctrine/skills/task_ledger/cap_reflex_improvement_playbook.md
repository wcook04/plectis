---
id: "cap_reflex_improvement_playbook"
kind: "reference"
family: "task_ledger"
title: "Cap Reflex Improvement Playbook"
summary: "Detailed operational rules for repeated CAP-reflex passes. The compact skill remains the entry contract; this file preserves the accumulated drilldown rules."
owner_skill: "cap_reflex_improvement"
---

# Cap Reflex Improvement Playbook

Use this file after `cap_reflex_improvement.md` has selected the CAP-reflex lane and a concrete slice. It preserves the detailed rules that are too large for the cold-entry skill body.

## Route And Projection Rules

Projection parity rule: when a live defect row says a high-cardinality option surface has clusterability debt, verify the actual kernel route before creating a cap:

```bash
./repo-python kernel.py --option-surface <kind> --band cluster_flag
```

Library-reference distinction: navigation-surface audit may intentionally keep an in-memory `*.row_flag_all.library` measurement as an unsafe reference after the public CLI route has been repaired to redirect to `cluster_flag`. Treat that as projection memory, not proof of a live route regression. Before filing or escalating it, run the public CLI command and make the debt row title/evidence say `library-only unsafe reference` or `CLI regression` explicitly.

If the route exists but still emits row-level flags, patch the owning adapter to produce true cluster rows from an existing stable grouping key in its source projection. Update the kind-atlas first rung and supported bands when the option surface becomes cluster-first, then add a regression at the option-surface boundary. Do not invent a parallel grouping table or a new skill when an existing adapter owns the projection.

Sibling-projection rule: after repairing a route advertised through Kind Atlas, rerun the task-conditioned entry packet that consumes it:

```bash
./repo-python kernel.py --context-pack "<same task>" --context-budget 12000
```

If the entry packet still reports the old route state, fix the projection consumer to derive from the owner row (`bands`, `option_surface_command`, or equivalent route authority) instead of carrying a second hardcoded list. This is part of the same failure class; do not close after the owner adapter passes while a sibling entry surface still teaches the stale path.

Compatibility debug-route rule: when a route lifecycle marks a command as a compatibility shim or debug trace, inspect every public teaching projection in the same owner family, not only the first wrapper that failed. Generated Agent Skills, AGENTS/CLAUDE router blocks, compact catalog seeds, and browse maps must all teach the stable control/card route first and show debug commands only in exact-id form after a row is selected. Free-text placeholders such as `<query>` or `<task or intent>` in compatibility debug examples keep the failure class alive.

Compact-sibling preservation rule: when a sibling projection compacts owner rows, preserve the fields that define the classification semantics, not only ids and command hints. For example, `library_reference_only`, `compatibility_behavior`, `authority_posture`, `repair_class`, and safe alternatives are often the difference between "known unsafe reference retained for audit" and "live route regression."

Landmine projection rule: context-pack or entry landmines are still teaching surfaces. If the owner route has been reduced to a compatibility shim or library-only audit reference, the landmine must say that explicitly (`library_reference_only`, `compatibility_behavior`, `live_cli_regression=false`, or the standard-owned equivalent) instead of preserving an old raw size estimate that makes future agents think the live CLI route regressed.

Cluster alternative is not redirect proof: a high-cardinality kind may have a `cluster_flag` safe alternative without having an all-row flag compatibility shim. Do not stamp `compatibility_behavior` or `live_cli_regression=false` onto every landmine that has a cluster command; first check the route lifecycle row or a direct no-ids smoke for that kind.

For legacy-command-only kinds, the equivalent route authority should live on the atlas row itself as `cluster_command` (or the standard-owned equivalent), not as a consumer-private special case. If `bands` advertises `cluster_flag` and the owner route works, teach the atlas/standard to expose the cluster command, then make context-pack and landmines consume that field.

Use `./repo-python tools/meta/factory/check_agent_bootstrap_projection.py --actor-receipt` only when the selected defect touches actor bootstrap delivery or entrypoint health. Treat these packets as evidence selectors, not new authority.

## Selection Rules

Low-hanging fruit rule: when the operator asks for "low hanging fruit" without naming a specific WorkItem, do not default to tiny cosmetic edits or generic contract prose. First build a short ranked candidate set from existing Task Ledger organizer surfaces: `ready_by_rank`, `execution_menu_schedulable`, `dependency_blocked`, `unlocks_by_rank`, `promotion_candidates`, `capture_triage`, `missing_contracts_ranked`, `missing_integration_contract`, `missing_satisfaction_contract`, `merge_or_retire_candidates`, `propagation_needed`, and the organizer report.

Search hygiene rule: once a kernel entry packet or Task Ledger card has selected a stable CAP id, narrow any text search to the owner paths, source refs, or exact identifiers named by that card. Avoid repo-wide search across generated ledgers, prompt-shelf transcripts, and annex projections unless the selected owner route is still unknown; if broad search noise teaches a reusable route problem, quick-capture it before mentioning it in closeout.

Agent repair-packet rule: when a CAP closes by improving a control-plane diagnostic surface, prefer a bounded `agent_repair_packet` over raw report expansion. Each row must name `owner`, `failure_class`, `status`, `summary`, `safe_next_command`, and `proof_route`; drilldowns must bind the current CAP or subject id instead of a hardcoded exemplar, and clear sentinel actions such as `none` must not mask an actionable upstream status.

Dependency/unlock rule: when choosing a cap slice, inspect card-band `dependency_status` for the candidate and its immediate blockers/unlocks. `upstream_dependency_edges` says which titled caps must land first and why they are or are not satisfied. `downstream_unlock_edges` says which titled caps become eligible or closer to eligible when this cap lands. Prefer caps that unlock real downstream work when the edge evidence is grounded and the upstream work is low-blast-radius; do not infer dependency authority from prose or `dependencies` context refs.

Prefer candidates in this order:

1. directly executable, low-blast-radius WorkItems with grounded surfaces and local proof routes;
2. live defect rows whose owner file is clear, source authority is not generated output, and validation can prove the repair;
3. WorkItems that can be made materially more executable by cheaply grounding exact files, commands, acceptance checks, integration paths, or verification evidence;
4. obvious merge/retire or propagation cleanup with clear evidence;
5. completion-contract-only shaping rows whose only missing field is `completion_contract` and whose `requires_operator_review` is false.

For each selected candidate, record why it is easy, why it matters, the exact files/surfaces to inspect or edit, the verification route, and the intended mutation or implementation action. Completion-contract-only shaping is a fallback cleanup lane, not the default meaning of low hanging fruit.

## Repeat-Pass Rules

Ambition floor: bounded scope is an admissibility filter, not the target size. When the operator asks for low-hanging fruit, clear caps, bang out todos, or similar broad cleanup, walk the coupled queue and keep taking the next grounded, reversible, materially useful action while the work remains in the same complaint/lane and validation remains available. Do not stop merely because one event was appended, one skill was patched, three rows were shaped, or the first validation passed.

A low-hanging pass should continue across multiple small actions when they share the same operator complaint:

1. build a ranked queue from Task Ledger views and organizer report;
2. execute directly ready, low-blast-radius WorkItems when exact files and local proof routes are grounded;
3. enrich under-specified but valuable WorkItems with exact files, commands, acceptance checks, proof routes, and integration surfaces;
4. merge, retire, or note obvious duplicate/stale rows only when evidence is clear;
5. sign off or propagate completed/proofed rows when the closeout evidence is already present;
6. patch the owning skill, standard, paper module, or projection when repeated operator irritation or observed failure warrants it;
7. rebuild projections, validate, re-open the organizer queue, and continue until a real stopping condition appears.

Valid stopping conditions are operator-review required, high blast radius, unrelated dirty-path entanglement, unavailable private evidence that changes the decision, failed validation that must be diagnosed before continuing, no remaining easy candidates in the coupled queue, or risk of inventing authority outside existing doctrine. Invalid stopping conditions include a single defensible mutation, a file-size concern, or a token proof case that leaves obvious adjacent low-hanging work untouched.

Autonomous-seed metabolism rule: when the operator phrases the pass as "do caps and self-up-propagate/generalize this autonomous seed," treat that as one coupled queue, not as permission to create a fresh seed surface. First preserve or execute the top committed CAP with a recoverable priority path. Then clear adjacent, low-risk `propagation_needed`, `missing_contracts_ranked`, and `needs_signoff` rows whose proof already exists or whose missing contract can be repaired through `shape`. Only after the run proves a reusable workflow rule should you patch the cap-reflex skill/registry/projections; otherwise record `nothing_to_refine`. If a new issue appears while doing this, fix it, link it to an existing CAP, or quick-capture it before any user-facing prose.

Exact-surface shaping rule: when appending `integration_contract.exact_surfaces_discovered`, use the Task Ledger's existing vocabulary and evidence shape instead of inventing status labels. Existing repo paths use `status: exists` with a `test -e <path>` evidence receipt; absent expected paths use `status: missing` with an explicit absence receipt; logical/chat/schema refs stay out of disk-grounded exact surfaces unless the standard already models them as command or schema evidence. If unsure, inspect `std_task_ledger.json` and recent valid events before running `shape`.

Queue-pressure discipline: before changing rank, promotion, signoff, or routing, write the current priority path in evidence terms and separate the signals:

- `execution_menu` / `ready_by_rank` says the row is eligible to work, not that it is complete.
- `needs_signoff` says a closeout condition exists, not that proof already landed.
- `promotion_candidates` is operator-review pressure, not permission to reorder the execution menu.
- `dependency_status.schedulable` and upstream/downstream edge rows are the dependency authority; prose hints are not enough.

If a row is both ready and needs signoff, first decide whether the card has landed proof that satisfies its closure condition. Sign off only when the proof is already present and reusable lessons are propagated; otherwise keep it in execution order and improve the work contract, routing note, or implementation slice.

Startup pressure lane rule: when WorkItem pressure is surfaced in startup, pulse, preflight, or entry packets, preserve four lanes instead of one fake top task: `schedulable_now` for executable rank, `schedulable_unlock_pressure` for executable downstream pressure, `global_unlock_pressure` for hidden topology that may not be schedulable, and `dependency_blocked` for blocked-but-important work. Entry packets should carry counts, top handles, lane labels, and an omission receipt; fuller startup views can carry edges. Terminal rows may remain evidence, but they must not win pressure lanes.

Standard-backed CAP rule: `codex/standards/std_task_ledger.json::cap_identity_contract` defines CAPs as Task Ledger WorkItem identity, not a second backlog. `codex/standards/std_task_ledger.json::cap_reflex_pass_contract` governs improvement passes, including repeat-pass action classes, action-class evidence, proof dimensions, no-op verdicts, and top-path saturation. `codex/standards/std_task_ledger.json::cap_standard_propagation_contract` governs CAP-standard publication across source skill, registry, generated Agent Skill, and browse projections. A cap-reflex pass is not just "browse caps and pick one"; it must build a recoverable priority path, pass the owner/evidence/dependency/authority/proof gates, mutate only through Task Ledger events or the owning source artifact, and close with one of the standard outcomes: `event_append`, `bounded_implementation`, `existing_workitem_link`, `signoff_or_propagation_receipt`, `captured_residual`, or `nothing_to_refine`.

Priority-path storage rule: before a CAP pass mutates rank, promotion, shape, signoff, retirement, or implementation, the priority path must be recoverable from disk. Prefer a Task Ledger `note` or `shape` event when the path changes a WorkItem; use commit prose or closeout receipt only for source-artifact patches that do not target a single WorkItem.

Broad-capability CAP rule: when the operator names a throughput idea, provider lane, corpus mining pass, or "wire X through Y" gesture, preserve the reusable job shape without pretending implementation certainty. Route through `--entry` or `--context-pack`, inspect adjacent WorkItems and existing substrate lanes, then either shape/note the existing owner or create a specific orchestrator, data-product, owner-surface, provider-job, metabolic-reflex, or integration CAP. Put invariant outcome, success signals, and non-goals in the satisfaction contract; keep candidate surfaces as hypotheses until disk paths, commands, schemas, option-surface ids, or absence receipts prove them. For continuous work, add cursor, budget, cooldown, provider receipt, retry/blocker, and stop-condition expectations before treating the row as shaped.

Blocked-promotion rule: a row can be valuable enough for `promotion_candidates` while still being intentionally unschedulable. If card-band `dependency_status.schedulable=false`, do not promote, rerank, or add workaround dependencies merely to make it look actionable. First decide whether the existing hard deps are real blockers. If they are, add an ordering note that names the upstream proof path and downstream unlock; change dependencies only when an edge is wrong, missing, stale, or too broad for scheduler authority.

Promotion-candidate disposition rule: before acting on `promotion_candidates`, split shaped-ready rows into three bins. If the card is schedulable but has a contract or acceptance gap, use `shape` to add the missing satisfaction, integration, proof route, or completion contract. If it is schedulable and has a concrete downstream unlock, add an ordering note or promote only with operator-review evidence. If it is unschedulable but unlock-rich, preserve it with a blocked-ordering note and route effort to the upstream hard dependency. Do not let the shared `promote_rank_or_execute` label erase those differences.

Shape reducer rule: shape events are projection inputs with a specific reducer contract. Grounded surfaces belong under `integration_contract.exact_surfaces_discovered`; proof commands belong under `completion.acceptance_checks` or the integration contract's discovery command fields. Do not assume a `shape` event can repair every projection-completeness bit: for example, authority repair is not fixed by writing an arbitrary nested authority note unless the reducer supports that field. Reopen the card after every shape and, if the projection still reports a missing bit, either use the owning event lane, capture the affordance gap, or leave a precise ordering note.

Authority-shape rule: the Task Ledger reducer now supports top-level `authority` in `work_item.shaped` events. Put authority repair at `payload.authority`, then reopen the card and require `projection_completeness.has_authority=true` before using the row as shaped-ready evidence.

Completion-shape field rule: completion repair is not satisfied by a descriptive `completion_contract` object unless the reducer explicitly supports that alias. For `work_item.shaped`, put definition of done, acceptance checks, non-satisfaction, and signoff policy under top-level `payload.completion`, then reopen the card and require `projection_completeness.has_completion_contract=true`. If the field still does not project, stop and inspect the reducer before appending another synonym-shaped event.

Capture subject-collision rule: quick captures should normally get fresh `cap_quick_*` ids. If a diagnostic or side capture reuses an existing ranked, promoted, shaped, blocked, done, or propagated WorkItem id, the reducer must preserve the existing WorkItem identity and treat the capture as attached evidence, not as a state/title/type downgrade. Reopen the card after rebuild and verify the original rank, title, state, completion, and authority still project before using the execution menu as ordered.

Coherent-order rule: a cap pass does not need to force a rerank to count as ordering work. If `execution_menu`, `ready_by_rank`, `schedulable_by_rank`, and card-band dependency status already agree, preserve the rank and improve the row by recording the reason the order is right, the next proof move, and the downstream unlock. Use `note` for this; use `rerank-commit` only when the current order is actually wrong and the justification can name the violated dependency, operator priority, or proof path.

Repeat-pass progression rule: when the operator repeats the same broad cap-ordering request and the top wave already has current priority-path notes, do not duplicate notes to prove effort. Move to the next adjacent useful surface: an under-shaped captured row with a concrete owner, a `propagation_needed` row with landed evidence, a missing completion contract, or a signoff row whose closure proof is already present. Record why the top wave was preserved or saturated.

Repeated broad CAP pass exit rule: after the top wave has current priority-path notes and the next adjacent completion-lane batch has been shaped, the next pass must choose exactly one action class: `execute_current_top`, `signoff_with_existing_proof`, `repair_projection_or_reducer`, `bounded_queue_health_audit`, or `no_op_with_evidence`. Do not keep selecting new legacy completion batches merely because they are available. A batch-shape is valid only when it changes queue decision quality, unblocks a named downstream CAP, or repairs a projection completeness class that would otherwise misroute agents.

CAP-reflex proof requirement: a pass counts as improved only if it changes at least one of top execution readiness, blocker correctness, signoff correctness, projection trust, downstream unlock visibility, or missing-contract class elimination. Prose-only notes count only when they resolve a specific routing ambiguity and are recoverable from a Task Ledger event, source patch, or explicit no-op verdict.

Top-path saturation rule: if the current top CAP remains unchanged across multiple CAP-reflex passes, execute it, prove it is blocked or signoff-ready, or create/route a blocker CAP that names the missing proof. Do not continue sweeping lower rows while the same top proof path remains actionable.

Sibling residual consumption rule: when another live seed leaves low-ceremony residual captures that point at an already-ranked operational CAP, consume them through the existing CAP instead of creating a parallel lane. Shape the ranked CAP with exact surfaces, authority, completion, and acceptance checks; add or cite the residual captures as evidence; close self-error residuals with a signoff only after the reusable reflex has landed in this playbook or the owning skill. If the residual requires a real architecture decision, block or capture that missing decision and move on.

Legacy-spine completion rule: bootstrapped WorkItem-spine captures may already have satisfaction refs, raw-seed refs, and integration paths but still lack `completion` and `authority`. Do not promote these rows just because they are schedulable. First append a `shape` event that names definition-of-done, acceptance checks, non-goals, and the owning authority surface; leave execution rank unchanged unless the row is the current proof path.

Legacy-spine chain rule: adjacent bootstrapped WorkItem-spine captures often describe a real substrate sequence even when the initial import left them all schedulable. When shaping a contiguous legacy slice, infer hard dependencies only from concrete substrate order, not from id adjacency alone: authority declaration before event substrate, substrate before legacy preservation, lifecycle skill before prompt routing, and prompt routing before Type B to Type A shuttle architecture. Encode those dependencies in `--depends-on`, reopen the card, and verify downstream unlock edges show the intended chain.

Completion-lane batch rule: when a repeated cap-ordering pass finds a contiguous legacy slice whose cards already have satisfaction refs, raw-seed refs, exact integration paths, and no dependency blockers, but all share only `completion_contract` and `authority` gaps, batch-shape the slice instead of reranking the execution menu. For each row, add top-level `completion`, top-level `authority`, a routing contract, and proof commands; then reopen the card and require `triage_status=shaped_ready`, `missing_contracts=[]`, `projection_completeness.has_completion_contract=true`, and `projection_completeness.has_authority=true` before counting the batch as improved. Preserve existing downstream unlocks such as a later CAP waiting on the shaped row; do not mark the upstream done unless execution proof has actually landed.

Transaction/retry discipline: if a Task Ledger mutation, projection rebuild, or signoff command fails after touching append-only state, inspect the recent events before retrying. Treat "append succeeded, rebuild failed" as a partial transaction: do not blindly retry the same closeout, capture or fix idempotency residuals before naming them, then validate the ledger before continuing. In shared-tree commits, remember that same-authority append-log events from another Type A agent can be included with your owned ledger path; use scoped/private-index commit dry-runs and report that same-authority entanglement instead of pretending the queue was single-writer.
