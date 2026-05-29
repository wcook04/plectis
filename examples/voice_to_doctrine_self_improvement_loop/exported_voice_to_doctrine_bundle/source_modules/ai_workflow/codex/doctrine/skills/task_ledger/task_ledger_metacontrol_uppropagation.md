---
id: "task_ledger_metacontrol_uppropagation"
kind: "operation"
skill_type: "propagation"
family: "task_ledger"
title: "Task Ledger Metacontrol Uppropagation"
summary: "Route reusable lessons from Task Ledger use or improvement, including mechanism/WorkItem affinity confusion, Work Ledger mutation ordering, and standard-to-enforcer closure, into the owner surface that prevents recurrence."
triggers:
  - "Working on or through the Task Ledger reveals reusable friction"
  - "Repeated operator todo-capture or noticed-issue handling shows the Task Ledger skill should teach a stronger Type A reflex"
  - "A Task Ledger projection, organizer-report row, promotion boundary, or execution-menu commitment rule was wrong or confusing"
  - "Duplicate CAP pressure or repeated generalization captures need a projection-backed merge/retire owner route"
  - "A mechanism affinity cluster, mechanism pressure row, or mechanism/WorkItem boundary made agents treat mechanisms as backlog authority"
  - "A complaint/problem/idea signal or Type A prioritization pass exposes a missing problem frame, owner, disposition, escalation rule, ordering rule, or correction lane"
  - "A Task Ledger enforcement wave proves that a standard invalid-exit or fail-closed clause needs an owner enforcer, tests, projection visibility, and receipt binding"
  - "A Work Ledger/path claim blocks the high-value primary mutation and the agent is tempted to shrink into a tiny adjacent hygiene edit"
  - "A Work Ledger session needs multiple claim, release, or finalize mutations and the agent is tempted to parallelize them for one session"
  - "A source/docs/tests commit landed but Task Ledger metadata settlement is blocked, rejected, or still waiting on the same append-log authority"
  - "A Task Ledger fix shipped and closeout must decide refined, propagation debt, already propagated, or nothing_to_refine"
  - "An operator corrects a cap-only or propagation-record-only closeout and expects the owner substrate to be edited"
focus_paths:
  - state/task_ledger/
  - codex/doctrine/skills/task_ledger/task_ledger.md
  - codex/doctrine/skills/task_ledger/capture_assimilation.md
  - codex/standards/std_task_ledger.json
  - codex/standards/principles/std_mechanism.json
  - codex/standards/std_uppropagation_intake.json
  - system/lib/standard_option_surface.py
  - system/lib/task_ledger_events.py
  - system/server/tests/test_task_ledger_events.py
doc_links:
  - codex/doctrine/skills/task_ledger/task_ledger.md
  - codex/doctrine/skills/task_ledger/capture_assimilation.md
  - codex/doctrine/skills/doctrine/local_to_general_propagation.md
  - codex/doctrine/paper_modules/operational_work_item_spine.md
  - codex/standards/std_task_ledger.json
doctrine_edges:
  principles: [pri_049, pri_128, pri_140]
  paper_modules: [operational_work_item_spine, prompt_shelf_uppropagation_ledger, work_ledger, provider_metabolism_ledger, frontend_station_cockpit]
  standards: [std_task_ledger, std_uppropagation_intake, std_task_sign_off, std_work_ledger, std_agent_entry_surface]
governing_standard_ids:
  - std_task_ledger
  - std_uppropagation_intake
  - std_task_sign_off
  - std_work_ledger
  - std_agent_entry_surface
composes_with:
  - task_ledger
  - capture_assimilation
  - local_to_general_propagation
  - peer_propagation
---

<!-- registry: skill_registry.json -> task_ledger_metacontrol_uppropagation | family: task_ledger -->

## Purpose

This skill fires when Task Ledger work teaches the system something reusable about its own capture, projection, ordering, linkage, or propagation behavior. It is not a second backlog. It is the router that turns local friction into the owner-surface correction that prevents the same friction from recurring.

Use it after the Task Ledger was involved and one of these is true:

- A residual was named and needs fix, capture, existing WorkItem link, or explicit no-op.
- A capture or TODO was too brittle, too vague, duplicated, or poorly routed.
- Duplicate CAP pressure needs a live projection row before it becomes prose advice or another inbox capture.
- Mechanism pressure needs an affinity cluster or owner-lane correction before it becomes a second backlog or prose-only warning.
- A projection, view, organizer-report row, promotion boundary, or execution-menu rule misrepresented event authority.
- A problem-signal, disposition, escalation, or gates-before-score lesson should update the capture-assimilation grammar.
- Provider, bridge, Prompt Ledger, Work Ledger, Station/HUD, or signoff linkage exposed missing propagation.
- A standard clause declared `invalid_exit_patterns`, `applies_when`, fail-closed behavior, required evidence, or a refusal condition, but the local work had to prove whether an owner enforcer and tests actually made that exit hard.
- A Work Ledger/path claim blocks the high-value primary mutation lane and the pass risks collapsing into a small nearby edit instead of preserving the capability target.
- A Work Ledger session needs extra path/thread claims, releases, or finalization after preflight, especially around metadata settlement or source-closeout coordination.
- Source-side work has landed, but the satisfaction contract, execution receipt, signoff, propagation record, or projection settlement still needs a Task Ledger event and may collide with another live append-log claimant.

## Entry

Start with the read-only metacontrol surface:

```bash
./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2
```

Then inspect the current row or owner surface through the smallest live route that can answer the question:

```bash
./repo-python kernel.py --option-surface task_ledger --band card --ids <work_item_id>
./repo-python kernel.py --option-surface skills --band card --ids capture_assimilation
./repo-python kernel.py --option-surface standards --band card --ids std_task_ledger
```

## Decision Ladder

Classify the local lesson before editing:

| Lesson shape | Owner surface |
|---|---|
| Capture wording froze speculative paths, owners, order, or method | `pri_140`, `std_task_ledger.json::workitem_authoring_contract`, `task_ledger.md`, `capture_assimilation.md` |
| Capture preserved too little evidence, intent, risk, or satisfaction contour | `task_ledger.md`, `capture_assimilation.md`, `std_task_ledger.json` |
| A broad operator capability gesture taught a better CAP authoring pattern: duplicate scan, existing-lane anchoring, candidate-vs-exact surfaces, dependency blockers, satisfaction/non-goal contour, or continuous-run receipt boundaries | `task_ledger.md` for authoring reflex; `capture_assimilation.md` for post-capture ordering; `std_task_ledger.json` only if the schema vocabulary or validation contract must change |
| Duplicate CAP/generalization pressure is visible but not owner-routed | `system/lib/task_ledger_events.py::_build_merge_or_retire_candidates_view`, `state/task_ledger/views/merge_or_retire_candidates.json`, `organizer-report::merge_or_retire_diagnostic`, and `std_task_ledger.json::organizer_metabolism.compaction_governance_contract`; add or refine detection evidence before creating more prose |
| Mechanism pressure or a `mech_*` row seems to describe executable work | `std_task_ledger.json::standard_option_surface.cluster_flag_rule`, `std_mechanism.json::workitem_pressure_projection`, `std_agent_entry_surface.json::cross_authority_affinity_route_contract`, and `system/lib/standard_option_surface.py`; use mechanism affinity clusters to shape, note, retire, validate, or bind WorkItems, not to mint a mechanism backlog |
| Projection dropped event authority or made views lie | projector code plus standard projection semantics |
| A standard declares `invalid_exit_patterns`, `applies_when`, fail-closed behavior, required evidence, or a refusal condition | The source standard plus its nearest writer/checker/enforcer, negative regression test, positive escape test, projection/card or receipt visibility, and WorkItem closeout evidence; if no runtime guard is appropriate, record why the clause is doctrine-only rather than creating a parallel enforcement manifesto |
| Organizer routing advertises an unsupported event when an existing event already expresses the move | routing metadata plus `std_task_ledger.json::organizer_row_contract`; reuse the supported event before adding a new command |
| Cluster/contents projection repeats row-level command templates, source lists, file hints, or integration paths until the navigation surface becomes bloated | projector code plus `std_task_ledger.json::organizer_row_contract`; hoist shared templates once, expose counts and drilldowns in cluster rows, and keep full evidence on organizer-report, source views, or selected flag/card drilldowns |
| Organizer-report / promotion / execution-menu boundary confused memory with commitment | `capture_assimilation.md`, `std_task_ledger.json::metacontrol_contract` |
| Work graph priority, ordering, or clustering is vague, salience-driven, or too WorkItem-specific for live cap/seed/route/standard pressure | `std_task_ledger.json::metacontrol_contract.priority_rubric_contract`, `task_ledger.md`, `organizer-report::priority_cluster_summary`, and `operational_work_item_spine.md::Type A Priority Path` |
| Active Work Ledger/path claims block the high-value primary mutation lane and the available nearby edit is much smaller than the task's real capability target | `std_task_ledger.json::metacontrol_contract.blocked_primary_ambition_preservation`, `std_work_ledger.json::claim_contract`, `operational_work_item_spine.md::Work-Pressure Metabolism Governor`, and this skill | Classify the blocker and choose one legal continuation: finish when claimable, adopt/coordinate the blocker, advance the same capability through an uncontended sibling, or update/create the residual and switch only to a ranked independent WorkItem. A one-line hygiene edit must state why it is the highest-yield legal move, not merely the easiest safe edit. |
| One Work Ledger session needs multiple claim, release, or finalize mutations | `std_work_ledger.json::same_session_mutation_ordering`, `std_work_ledger.json::session_preflight_contract`, `work_ledger.md::Runtime invariants`, and existing self-error caps such as `cap_quick_do_not_parallelize_work_ledger_claim_mut_0a44dd9f5819` | Batch known startup scopes through one `session-preflight` call with repeated `--path` / `--td-id`; after preflight, run lower-level `session-claim`, `session-claim-path`, `session-release-claim`, and `session-finalize` commands serially for that `--session-id`, with finalization last. Parallelize read-only checks, not same-session runtime writes. |
| A write-profile or broad directory claim covered startup coordination, but scoped landing asks about exact child paths | `std_work_ledger.json::session_preflight_contract`, `std_work_ledger.json::claim_contract`, this skill, and the scoped commit / mission preflight lane | Treat write profiles as startup coordination macros, not standalone landing proof. For scoped commits, bind the landing preflight to the owning `--session-id` / `--session-id auto` and exact owned paths; if the gate still reports missing exact coverage after duplicate-claim dedupe collapsed child claims into a broad parent, release or narrow the broad claim and claim the exact child paths before landing. |
| Source commit landed but Task Ledger settlement is rejected or blocked by same-authority claim pressure | `std_task_ledger.json::metacontrol_contract.task_ledger_metadata_settlement_contract`, `std_task_ledger.json::integration_contract`, `std_work_ledger.json::claim_contract`, `task_ledger.md::Same-authority append-log landing` | Treat this as metadata settlement, not new feature work. Validate payload vocabulary first; use exact surface statuses `exists`, `missing`, `command`, `schema`, or `implied`; then settle now, wait/retry while claimable, enqueue through serial intake when supported, or capture/update a blocked residual with source commit, event type, blocker, lease evidence, and re-entry condition. |
| `propagation_needed` / closed-work rows name a clear owner surface | owner source/standard/skill/checker/projector/code path first, then `work_item.propagation_recorded` as receipt | Do not consume the row by ledger bookkeeping alone. Inspect the owner and land the bounded source edit or owner command when safe; record `already_propagated_verified` only when the owner already teaches the lesson; capture/block only the unsafe residual. |
| Problem-signal ordering needs better gates, disposition, or escalation | `capture_assimilation.md` and the Task Ledger standard |
| Provider, bridge, Prompt Ledger, Work Ledger, Station/HUD, or signoff linkage failed | the paired integration standard/skill plus Task Ledger linkage text |
| A high-class Type B / sidecar integration produced Task Ledger captures but the reusable lesson is Type A/B handoff behavior, actor-dynamics, or propagation failure | `operational_work_item_spine.md` Type B -> Type A Loop + `local_to_general_propagation.md` + this skill | Keep the captures as evidence, then route the handoff failure to the owner surface; CAP-only closeout is insufficient when the capture bundle demonstrates a recurring handoff class |
| The issue is real but out of scope | quick-capture with a `pri_140` contour and candidate surfaces, not final-report prose |
| The issue is already covered | record `already_propagated_verified` with evidence |
| No reusable lesson remains | record `nothing_to_refine` with evidence |

## Operating Rules

1. Do not create a Task Ledger improvement backlog. Route to the owner surface, append a bounded WorkItem, or record no-op evidence.
2. Do not treat `capture_inbox` as backlog or `promotion_candidates` as commitment. `execution_menu` is the committed queue.
3. Do not freeze speculative paths, owners, ordering, or methods before current-state discovery. Use the `pri_140` contour for open-ended WorkItems.
4. Do not close `nothing_to_refine` when a reusable lesson, route gap, residual, or blocked write exists.
5. Do not mutate Task Ledger projections directly. Event log and owner tools are authority; views are rebuild output.
6. Do not treat `events_audit.jsonl` as closeout authority. Audit-only events require `authority-health` / `audit-recover --replay` / rebuild before card lookup, retirement, or residual visibility claims are trusted.
7. Do not let provider-native task affordances become cross-session backlog authority. Durable work must become a Task Ledger event or an explicit disposition.
8. Treat commentary/status updates, apologies, corrections, final answers, and acknowledgements of operator corrections as user-facing prose. If any of them would name a side finding, gap, failing test, residual, or self-error, quick-capture first and cite the `cap_id`; the response text is never the durable capture.
9. When a Task Ledger option surface reports `missing_affordance_refs`, first check whether the requested move can be represented by an existing supported event. If yes, repair the organizer route to that event and command hint; add a new event/apply command only when the existing event vocabulary cannot preserve the semantics.
10. Keep `cluster_flag` surfaces as contents pages. They may carry compact organizer routing, counts, and drilldown commands, but repeated command templates and row-specific evidence should be hoisted once or deferred to organizer-report/source views/flag/card drilldowns.
11. Serialize Task Ledger mutations. Do not call mutating `task_ledger_apply.py` commands in parallel, even when they target different WorkItems; the event hash chain and regenerated views are a single ordered authority. Parallelize reads, then apply events one at a time and run `validate` before closeout.
12. Serialize Work Ledger lifecycle and claim mutations for the same session. Use `session-preflight` as the batch lane for known startup scopes; after preflight, run `session-claim`, `session-claim-path`, `session-release-claim`, and `session-finalize` one at a time for that `--session-id`, with finalization last. `mutation-check`, `session-status`, and `session-claims` are read-only and may be parallelized.
13. For scoped commit landing, use exact owned-path claims or session-bound overlap proof. Broad write-profile/directory claims are useful at startup, but they are ambiguous at landing unless the mission/scoped preflight is bound to the owning session. If duplicate-claim dedupe collapses exact child claims into a broad parent and a commit/preflight gate asks for exact coverage, do not handwave it; rerun with `--session-id auto` or release/narrow to exact child claims, then validate.
14. Treat post-commit metadata settlement as a same-authority Task Ledger append-log write. A source commit can be landed while its satisfaction contract, execution receipt, signoff, or propagation event is still pending, but the WorkItem is not fully settled until that event exists and projections validate, or a blocked residual records the exact re-entry condition.
15. When settlement payload validation rejects an `integration_contract.exact_surfaces_discovered` entry, fix the payload vocabulary before retrying. Valid `status` values are `exists`, `missing`, `command`, `schema`, and `implied`; an invalid status that did not append is a preflight failure, not a ledger event or a reason to hand-edit projections.
16. When the lesson is "how to file smarter CAPs," refine `task_ledger.md` first. Update `capture_assimilation.md` only when the lesson changes post-capture disposition/order, and update `std_task_ledger.json` only when new fields, validation, or projection semantics are required.
17. When the lesson is "these CAPs are semantically duplicate or overlapping," make the owner projection show the candidate group with evidence. The durable repair route is a supported disposition event: retire duplicate rows, add provenance notes, record propagation, shape the kept row, or capture a residual when review is required. Treat "merge" and "supersede" as dispositions unless the apply lane grows direct event support; do not add another unlinked capture or final-answer warning while `merge_or_retire_candidates` already carries the pressure.
18. Treat mechanism affinity clusters as read-only organizer lenses. Mechanism rows may explain why WorkItems belong together, but Task Ledger events remain the only authority for WorkItem creation, disposition, commitment, and signoff.
19. When a broad operator packet exceeds the current runtime slice, make the leftover deliverables recoverable through matching existing caps/WorkItems or fresh quick-captures before closeout; do not let the "rest" survive only as native TODOs, prompt prose, or a final-answer future-work paragraph.
20. If priority ordering becomes the work, use the rubric and cluster summary projected by organizer-report; do not add a second priority board, and do not let a low-pass seed mutate promotion/rank/retire decisions without an explicit operator or WorkItem event boundary.
21. A burst of quick-captures from a Type B sidecar is not proof that the sidecar lesson was absorbed. After capture, classify whether the sidecar also taught a reusable handoff, actor-axis, prompt-routing, or propagation rule; if yes, mutate or capture the owner surface explicitly before claiming closeout.
22. Treat fail-closed standard clauses as incomplete until their enforcement posture is known. A covered clause has an owner enforcer or checker, a negative test that proves the invalid exit is rejected, a positive test or escape path that proves legitimate work is not blocked, projection or receipt visibility, and a WorkItem/signoff binding. Descriptive or doctrine-only standards may stop without an enforcer, but only with an explicit doctrine-only rationale.
23. Treat a blocked high-value primary path as a flow-control signal, not as permission to downshift ambition. Use `session-preflight` or `mutation-check` evidence to classify the blocker, then pick the highest-yield legal continuation under `blocked_primary_ambition_preservation`; record the blocker, chosen continuation, and re-entry condition if the primary patch cannot land now.
24. Treat propagation queue work as owner-surface actuation by default. A `work_item.propagation_recorded` event is the receipt after the owner surface is patched or verified, not the repair itself. Do not append caps, notes, or propagation records as the only output unless the operator explicitly asked for record-only grooming or current-state inspection proves the owner edit is unsafe, claimed, blocked, or already present.

## Closeout Receipt

Every use of this skill ends with one of:

```text
refined: <owner surface changed and validation run>
propagation_debt: <capture/workitem id or blocker explaining why it could not land>
already_propagated_verified: <surface and evidence checked>
nothing_to_refine: <why the local case did not teach a reusable rule>
```

For substantive changes, run the relevant validator and refresh generated projections. Typical checks:

```bash
./repo-python tools/meta/factory/task_ledger_apply.py validate
./repo-python tools/meta/factory/task_ledger_project.py rebuild --check
./repo-python tools/meta/factory/check_skill_routing_smoke.py
```
