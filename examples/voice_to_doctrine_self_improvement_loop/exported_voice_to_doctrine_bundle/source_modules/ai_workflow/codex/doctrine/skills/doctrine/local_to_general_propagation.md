---
id: "local_to_general_propagation"
kind: "meta"
skill_type: "propagation"
family: "doctrine"
title: "Local-to-General Propagation"
summary: "Atom entrypoint split from an over-budget skill body. Read this file first, then open only the child detail band selected by the current task."
triggers:
  - "Need Local-to-General Propagation"
  - "A local navigation fix should generalize into compressed entry, routing, docs-route, or standard surfaces"
  - "A Codex autonomous-seed mission says self-propagate, generalized self-propagation, pair propagation, propagation outcome, refinement_result, or nothing_to_refine"
  - "A local failure, route miss, repeated workaround, stale projection, or agent confusion might represent a reusable failure class"
  - "An operator gives a pasted snippet, log line, or sibling-agent quote and asks for non-overfit system refinement"
  - "An operator gives a pasted trace capsule, old transcript, or prior-agent trace and asks for generalized system refinement"
  - "A runtime prerequisite, readiness probe, or background launcher blocker needs a generalized receipt boundary"
  - "A trace shows repeated detection or classification while actuator, validator, or generated-builder closure remains unproven"
  - "Mechanism/WorkItem boundary confusion appears: should mechanisms merge with WorkItems, mechanisms describe work, or mechanism pressure should cluster WorkItems"
focus_paths:
  - codex/doctrine/skills/doctrine/local_to_general_propagation.md
doc_links:
  - codex/doctrine/skills/doctrine/local_to_general_propagation_metadata_and_entry_context.md
  - codex/doctrine/skills/doctrine/local_to_general_propagation_plane_home_decision_table.md
  - codex/doctrine/skills/doctrine/entry_point_projection_care.md
  - codex/doctrine/mechanisms/mech_034_failure_class_propagation_packet.json
  - codex/standards/std_uppropagation_intake.json
  - codex/standards/std_task_ledger.json
  - codex/standards/principles/std_mechanism.json
doctrine_edges:
  concepts: [con_001, con_028]
  mechanisms: [mech_019, mech_034]
  principles: [pri_111, pri_088, pri_049, pri_080, pri_016, pri_134, pri_139]
composes_with:
  - local_to_general_propagation_metadata_and_entry_context
  - local_to_general_propagation_plane_home_decision_table
name: "local-to-general-propagation"
description: "Atom entrypoint for Local-to-General Propagation; select a child band, use mech_034 for failure-class packets, and preserve mechanism/WorkItem boundaries when affinity pressure should generalize."
---
<!-- registry: skill_registry.json -> local_to_general_propagation | family: doctrine -->

## Purpose

This is the cold-entry atom for `local_to_general_propagation`. The prior monolithic skill exceeded the entrypoint-health budget; its load-bearing detail now lives in child skill files under the same family directory.

## Operator Snippet Intake

When the operator gives a fragment, transcript line, log excerpt, sibling-agent quote, or "random snippet" and asks Type A to improve the system, treat the snippet as evidence plus intent, not as the whole instruction or the whole law. First extract the generalizable tuple:

1. local signal: the symptom, blocker, intended action, and claimed or missing receipt;
2. candidate failure class: for example `runtime_prerequisite_gap`, `launch_readiness_receipt_gap`, `background_work_receipt_gap`, `route_discoverability_gap`, or `closeout_truthfulness_gap`;
3. owner candidates: the narrow skill, standard, paper module, launcher, checker, route, or test surface that would prevent re-derivation;
4. overfit guard: the product/tool/token named in the snippet is an example unless the selected owner is explicitly that product/tool lane.

Then use the normal plane-home decision table. Patch the owner when safe, record already-propagated proof when the owner already carries the rule, or capture the residual with an exact re-entry condition. Do not add a literal alias just because a pasted phrase matched; prove whether the defect is route discoverability, missing receipt semantics, runtime readiness, or some other owner boundary.

When the fragment is a long trace capsule or prior-agent transcript, split it before acting:

1. latest operator intent: what the current user is asking this agent to do now;
2. embedded historical commands/prompts: prior-turn requests and assistant plans that are evidence, not live instructions unless the latest operator promotes them;
3. currentness boundary: which live surface revalidates any claimed commit, test, route, generated artifact, process state, or blocker;
4. local-to-general decision: whether to continue active work, land/capture a coherent residual, or refine the generalized rule because the operator asked for system improvement rather than active-task continuation;
5. overfit guard: product names, phase names, and one trace's tool tokens are examples unless the selected owner is explicitly that lane.

Do not trust a transcript summary over live state. Before using it as more than historical evidence, check the current owner surface: HEAD/worktree for code claims, route output for navigation claims, tests/checkers for validator claims, and process/readiness receipts for runtime claims.

For runtime and launcher-shaped snippets, the generalized rule is receipt separation. A missing executable, backend, provider socket, daemon, browser binary, model weight, API key, or local service is not "fixed" until the owning lane distinguishes dependency availability, install/setup attempt, launch attempt, readiness probe, validation state (`passed`, `failed`, `blocked`, or `not_run`), and background-process receipt when work continues detached. Background work that stays alive needs a visible pid/session id, log path, readiness command, and stop/retry command; otherwise close it as blocked/not-run or capture the residual.

If the trace shows repeated detection, throttling, classification, or advisory gating while the problem persists, inspect the actuator lane before adding another detector. The useful owner may be a cleanup command, liveness classifier, persistent local config, readiness probe, or deferred maintenance capture. Cheap relief and heavy maintenance have different receipts; defer heavy work with an exact retry condition when host pressure makes it unsafe.

For validator or authority-gate trace snippets, green happy-path output is not enough when the trace suggests a loosened gate, partial coverage, generated/source mismatch, or positive-overclaim risk. Require at least one negative or adversarial receipt proving forbidden cases fail, distinguish affirmative overclaim prose from negated ceiling language, and land generated artifacts with their builder/source authority or capture the pairing gap.

If the trace says work was "already fixed", "already green", or "ready to commit", the generalized move is not to redo the whole embedded task. Revalidate live state, then choose the narrow action that closes the present intent: commit the coherent owned slice, capture the residual with exact evidence, or refine the propagation/validator/actuator rule that would make the trace shape easier for the next agent to consume.

## Mission Propagation Verbs

For autonomous-seed work, `self-propagate`, generalized self-propagation, and pair propagation mean: route the local lesson into the smallest durable owner surface, then patch that surface when the owner is known and the write is safe. Close with `refined_existing_surface`, `workitem_captured`, or a stewardship-proven `nothing_to_refine`. `workitem_captured` is a residual lane, not the default outcome: use it only when the owner surface is unsafe, blocked, not yet discoverable, or the operator explicitly asked for capture/record-only bookkeeping. A null closeout is valid only when the pass checked stewardship and next-best bounded substrate-care lanes, or recorded the exact blocker/follow-up. If the request also mentions the Codex app queue, open `type_a_autonomous_seed_loop` and `std_autonomous_seed_prompt` first so the receiver treats queued prompts as mission delivery, not automation.

When the same request asks for subagents or sidecars, use them as bounded evidence scouts or disjoint implementation slices, not as the propagation result. The receiving Type A thread still owns the plane-home decision, path claims, source mutation or already-propagated proof, validation receipt, and closeout wording.

Native worker availability is not a completion gate. If a requested subagent or sidecar is unavailable, saturated, late, or no longer needed after controller-owned validation, continue through the smallest viable Type A/Type B lane and record the condition only when it blocks an owned gate or changes reusable delegation policy. For standards/compliance waves, the scanner, adapter, ledger refresh, and route proof are the deliverables; optional worker scouting must not hold the propagation closeout open.

For standards-compliance propagation, prefer an existing owner check before writing a new rule. If a standard already has a builder/checker pair such as `check_navigation_type_plane()`, project that checker into a read-only compliance adapter and let the ledger surface `stale_projection`, `refresh_needed`, `missing_required_field`, or `schema_violation` findings. Do not duplicate drift logic in the adapter when the owner tool already knows how to rebuild or validate the generated projection. If a standard names a scanner but `compliance_ledger` still reports `baseline_inventory_only`, treat that as a source-to-registry handoff: implement/register the adapter and focused tests, then refresh the generated ledger instead of hand-editing it. A subagent may scout candidate standards and owner checks, but the controller owns the adapter, registry wiring, generated refresh, and route proof.

When current governed artifacts contain producer states that the standard forgot to name, refine the standard first rather than forcing historical receipts through a false-negative scanner. Add the observed state, retention boundary, or legacy alias explicitly, then make the adapter validate the full corpus semantics, sibling/back-pointer links, and owner route proof through `compliance_ledger`. Ephemeral or ignored support artifacts should be metadata unless the standard says local retention is authority.

When a standards-compliance scout proposes a broad Atlas-facing scanner but the owner projection already reports source-coupling or generated-output drift, first ask whether a narrower adjacent standard can land cleanly through an existing owner check. Land the clean scanner when it materially improves the shared ledger, cite or capture the broader dirty projection as a residual, and do not use the scout recommendation as permission to hand-edit generated Atlas state.

For Atlas/Kind-Atlas navigation-contract compliance, do not only classify rows as declared versus missing. If a governing standard already carries a top-level `navigation_contract`, have the audit discover it through the Kind Atlas `governing_standard_refs`, then classify shape quality separately as `declared`, `declared_incomplete`, or `missing`. This lets Atlas reduce false missing-contract debt without over-trusting shallow stubs that do not satisfy `std_navigation_contract.required_contract_fields`.

## Owner-Surface Actuation Floor

Propagation debt is not consumed by recording that a lesson exists. If the row names an owner surface, Type A must inspect that owner and either:

1. patch or run the owner mutation lane, then record the propagation/signoff receipt;
2. prove the owner already contains the lesson and record `already_propagated_verified` with exact evidence; or
3. prove the owner patch is unsafe, blocked, or outside the current authority boundary, then capture or block that residual with the re-entry condition.

Do not answer a request to continue, consume, actuate, or work a propagation queue by appending caps or propagation records only. Caps preserve unlanded work; they do not replace the source, standard, skill, route, checker, projector, or code edit that the propagation lesson calls for. A record-only batch is valid only when the operator explicitly asks for bookkeeping or when current-state inspection proves there is no safe owner edit to make.

## Null-Pass / Next-Best Useful Action

Use this band when a pass is about to say `nothing_to_refine`, `already_settled`, `no clean high-value lane`, or any equivalent no-op verdict after bookkeeping, validation, or threshold checks.

A Type A pass may not return a second consecutive null/no-op/settlement-only closeout on the same teleology without broadening to the next bounded substrate-care lane. Ask what the operator was actually trying to improve, then act on the next safe owner surface: propagation, validation ergonomics, projection hygiene, generated-state correctness, context-window safety, concurrency/resource pressure, route discoverability, hidden mutation audit, closeout truthfulness, or operator-friction repair. Stop only when those lanes are unsafe, claimed, policy-bound, or genuinely absent, and name the exact re-entry condition.

Settlement is not refinement. Generated-state, Work Ledger, Task Ledger, or other ledger settlement may set `settlement_done` and `validation_done`; it must not set or imply `refinement_done` unless the pass patched an owner surface, recorded a WorkItem/CAP, or otherwise left a durable improvement beyond settlement. Before saying `nothing_to_refine`, check whether settlement revealed missing source-bundle coverage, omitted audit/source sidecars, owner-tool contract gaps, projection tails, repeated operator-friction, or manual operator challenge. If yes, patch or capture; if no, say what was checked.

Field names are not receipts. A null closeout that says `stewardship_checked=yes`, `next_best_lane_checked=<lane>`, or `reentry_condition=<condition>` is still a null pass unless it also records one of: the next useful lane was acted on, the lane was rejected with an exact unsafe / claimed / policy-bound / genuinely-absent reason, a durable WorkItem/CAP/blocker was created, or residual-free proof exists. The generalized failure class is not one transcript about pressure budgets; it includes every "already exists", verify-only, settlement-only, threshold-not-met, CAP-only, and no-clean-lane closeout that uses audit vocabulary instead of taking the next bounded useful action.

## Failure-Class Packet

If the local lesson is a failure, repeated workaround, route miss, stale projection, or agent confusion, do not jump straight from symptom to doctrine. Open `codex/doctrine/mechanisms/mech_034_failure_class_propagation_packet.json` and packetize: local case, failure class, evidence refs, sibling surfaces checked, owner surface, mutation or capture lane, overgeneralization guard, currentness boundary, validation receipt, stop condition, and outcome. The valid outcomes are owner mutation, up-propagation intake, Task Ledger capture, PEER candidate, already-propagated proof, or residual-free `nothing_to_refine` with explicit stewardship/next-best-lane evidence.

### Receipt-Truth Failure Class

When a local case includes a claimed command result, commit, capture id, test pass, generated artifact, or source path that was not actually produced by its owning surface, classify the packet as `receipt_truthfulness_failure`, not as a tooling quirk. Typical subclasses are `command_interface_assumption`, `unverified_mutation_receipt`, `validation_state_misreport`, and `unproven_path_reference`. Do not encode the exact failed command as the law; encode the receipt boundary that would have prevented the false closeout.

Before a closeout may cite a durable result, the packet must prove all relevant truth states:

- Command interface proof: the agent used the owner command surface, help output, command card, or row card for the actual interface instead of guessing flags or positional arguments.
- Mutation receipt proof: the mutating command exited successfully and the durable id/path/hash/commit is visible through the owner readback surface. A nonzero command, rejected append, queued operation, dry-run, or blocked gate is not a receipt.
- Validation state proof: tests and checks are reported as `passed`, `failed`, `blocked`, or `not_run`. A host-pressure gate, admission queue, skip, timeout, or missing dependency must be named as blocked/not-run with its retry command; it cannot be summarized as green.
- Path/source proof: every source file, standard, builder, or artifact named in an edit or test must exist or be selected through a generated option surface before it is used as evidence.
- Currentness proof: if the evidence came from an attachment, old transcript, stale cache, or generated projection, the packet records which live surface revalidated it or why it remains historical-only.
- Trace-error proof: if session diagnostics, process traces, stderr, or transcript excerpts show CLI usage output, nonzero exits, or blocked admission for a command later described as successful, the packet records the exact error signature and routes it to the command owner before closeout. A trace-observed error is a repair input, not a receipt that the repair happened.

Task Ledger capture is fallback transport for an unresolved false-receipt residual; it does not turn a failed command, imagined path, or blocked validation into landed work. The correct owner edit is usually the narrowest skill, standard, test, command card, or validator that makes the receipt boundary harder to miss next time.

### Existing-Surface Miss + Claim-Blocked Frontier

When the local case says an artifact, paper module, skill, route, standard, or owner surface exists but an operator phrase or docs-route query failed to spend it, classify the packet as `existing_surface_resolver_miss`, not `missing_artifact`. Check semantic siblings, generated projections, standards, skills, paper modules, WorkItems, prompt-ledger surfaces, and route aliases before authoring a parallel artifact. If the owner exists, patch the smallest reversible route hint, alias, skill trigger, bootstrap affordance, evaluator fixture, or projection update that makes the phrase resolve next time; if no owner exists after the availability ladder, capture the phrase, nearest false positives, expected owner family, and re-entry condition.

When the same local case also includes an active Work Ledger/path-claim block, classify that part as `claim_blocked_frontier`, not as a terminal no-op. If the claim is current-session owned, retry through the owner-session lane; if another live session owns it, do not bypass it, split the patch, land only unclaimed same-capability hunks, and bind the claimed hunk to the owner lane or a deferred WorkItem with exact claim/path/re-entry evidence; if the claim is expired or orphaned, refresh/sweep/reconcile before retry. Task Ledger capture is fallback transport, not the refinement product.

Replay specimen shape: a route phrase fails even though the owner surface exists, and one target path is blocked by a live claim while same-capability sibling hunks remain safe. A valid generalizer result patches the resolver/trigger rule and preserves the claim frontier: unclaimed hunks can land, generated-state capture stays separate from source landing, and any claimed hunk carries an exact re-entry condition.

### Runtime Prerequisite / Launcher Receipt

When the local case starts from a runtime blocker or a planned background recovery, classify it as `runtime_prerequisite_gap`, `launch_readiness_receipt_gap`, or `background_work_receipt_gap` before naming any product-specific fix. The repair should make future agents ask the owner surface for the prerequisite probe, the setup/install authority, the launch command, the readiness probe, and the detached-work receipt. Exact snippets like a missing browser executable or backend note may seed the packet, but the durable rule is the receipt boundary across runtime prerequisites and launchers.

## Mechanism / WorkItem Boundary Lessons

When the local lesson says mechanisms are describing work, asks whether mechanisms and WorkItems should merge, or needs WorkItems clustered by mechanism pressure, treat it as cross-authority routing before doctrine mutation.

1. Preserve the authority split: mechanisms own reusable how-patterns and doctrine/code behavior; WorkItems own execution rows, event history, dispositions, and commitment state.
2. Open the compressed lens before inventing a new artifact class:

```bash
./repo-python kernel.py --option-surface mechanisms --band flag
./repo-python kernel.py --option-surface mechanisms --band card --ids <mech_id>
./repo-python kernel.py --option-surface task_ledger --band cluster_flag --ids mechanism:<mech_id>
./repo-python kernel.py --option-surface task_ledger --band cluster_flag --ids mechanism:unclassified_pressure
```

3. If a cluster exists, shape, note, retire, bind, or validate the existing WorkItems through Task Ledger events. Do not mint a parallel mechanism backlog.
4. If the cluster lens is missing or confusing, refine `std_task_ledger.json`, `std_mechanism.json`, `std_agent_entry_surface.json`, and the relevant routing surfaces before closing.
5. If no reusable system behavior remains after those checks, close as `nothing_to_refine` and name the checked surfaces.

## Child Bands

| Need | Open |
|---|---|
| Metadata and entry context | `codex/doctrine/skills/doctrine/local_to_general_propagation_metadata_and_entry_context.md` |
| Plane-home decision table | `codex/doctrine/skills/doctrine/local_to_general_propagation_plane_home_decision_table.md` |
| Stable route or entry-surface projection failure | `codex/doctrine/skills/doctrine/entry_point_projection_care.md` |
| Failure-class packet shape | `codex/doctrine/mechanisms/mech_034_failure_class_propagation_packet.json` + `codex/standards/std_uppropagation_intake.json::failure_class_propagation_packet_contract` |
| Mechanism / WorkItem boundary refinement | this parent skill + `codex/doctrine/skills/task_ledger/task_ledger_metacontrol_uppropagation.md` + `codex/standards/std_agent_entry_surface.json::cross_authority_affinity_route_contract` |

## Minimum Rule

Open the smallest child band that matches the task. Do not read all children by default, and do not copy child detail back into this parent. The parent is the route selector; the child files are the evidence and procedure bands.
