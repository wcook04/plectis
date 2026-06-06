---
id: "task_ledger"
kind: "operation"
skill_type: "authoring"
family: "task_ledger"
title: "Task Ledger Authoring + Reading"
summary: "Mental todo-list discipline: browse Task Ledger bands, append tasks/captures through events, justify rank changes, and sign off with propagated lessons."
triggers:
  - "Operator says 'add a task / todo / note this for later'"
  - "Operator gestures at broader work, uncertainty, or repeated friction that should become durable follow-up even if the wording is informal"
  - "Operator or agent voices a complaint, problem, fear, aspiration, idea, unifying principle, refinement want, integration pressure, or ordinary todo that should not stay in chat memory"
  - "Agent notices sidebar TODO pressure, quick note, or side work while deep in another task"
  - "Agent finishes a piece of work that reveals follow-up work — file it as a task before yielding"
  - "Operator says 're-rank' / 'reprioritize' / 'this is more urgent than'"
  - "A task reaches completion and the closeout reflex must record what shipped + what was learned"
  - "Cold agent at session start needs to know what's pending and at what rank"
  - "About to author a new doctrine, standard, skill, or paper module from scratch — check the ledger first to see if a task is already filed"
  - "Operator says 'what's the todo list' / 'what should I be doing' / 'where are we'"
  - "Reviewing ranked debt rows — debt may motivate task append"
focus_paths:
  - state/task_ledger/
  - tools/meta/factory/task_ledger_apply.py
  - codex/standards/std_task_ledger.json
  - codex/standards/std_task_sign_off.json
  - codex/doctrine/paper_modules/task_ledger.md
doc_links:
  - codex/doctrine/paper_modules/task_ledger.md
  - codex/standards/std_task_ledger.json
  - codex/standards/std_task_sign_off.json
  - codex/doctrine/paper_modules/navigation_hologram_theory.md
  - codex/standards/std_skill.json
composes_with: [annex_pattern_transfer, principles_curation, ship_implies_commit]
name: "task-ledger"
description: "Keep the system's mental todo list current: turn operator intent and noticed residuals into durable WorkItem events, browse option-surface bands before authoring, justify rank changes in rank_history, and sign off completions with lessons_propagated."
provenance: "derived"
governing_principles:
  - "Browse the ledger before authoring a new task; if a task already names this work, append a note instead of duplicating."
  - "Every rank change appends a rank_history row with justification. Silent re-rank breaks the audit chain."
  - "Tasks ship compression_passport rungs (atom/flag/card) before body. If atom does not fit in 6 words, the task is not coherent enough to file."
  - "Sign-offs must propagate lessons. A completed task with no lessons_propagated entry is leaving learning on the floor."
  - "The ledger is the system's mental todo list at all times — read it at session start, refresh against recent additions, hold it as background model."
agent_surface:
  does: "Append, quick-capture, link, or no-op named residuals and durable WorkItems."
  use_when: "A todo, broad operator intent, named residual, noticed issue, follow-up, ranking, capture, or sign-off needs durable handling."
  not_when: "The work is fully transient (within-turn scratch), or already recorded in a more specific surface (concept_mechanism_candidate, axiom_candidate, raw_seed paragraph)."
  must: "Before yielding, close named residuals by fixing, capturing, linking, or explicit no-op."
  entry: "Read state/task_ledger/ledger.json::tasks[] (compressed) before authoring; use task_ledger_apply CLI when v1 wiring lands"
  yields: "An updated ledger entry with intact audit chain; on sign-off, lessons propagated upward and follow-ups filed."
  composes: "annex_pattern_transfer, principles_curation, ship_implies_commit"
holographic:
  one_liner: "The system's mental todo list with audit chain"
  situation_signature: "Pending work needs to be filed, ranked, worked, or signed off with learning propagated"
compression_passport:
  cluster_keys: ["task_ledger", "todo", "operator_intent", "residual_closure", "named_residual", "noticed_issue", "quick_capture", "ranking", "sign_off", "audit_chain"]
  atom: "Mental todo list discipline"
  flag: "Close named residuals by fixing, quick-capturing, linking, or no-oping; capture operator intent and noticed issues as durable WorkItems."
  card: |
    The task ledger is the system's mental todo list: task_ledger plus task_sign_offs, governed by std_task_ledger.json and std_task_sign_off.json. Browse cluster_flag/flag/card bands before raw JSON. Append tasks with compression_passport rungs, rerank only by rank_history append with justification, and sign off with outcome_summary plus lessons_propagated. Direct rank edits break the audit chain.
  when_to_open: "A todo is being filed, ranked, worked, completed, or learned-from"
  when_not_to_open: "The work is within-turn transient or already lives in a more specific surface"
  safe_drilldown: "./repo-python kernel.py --option-surface task_ledger --band cluster_flag"
  landmines:
    - "Silent re-rank without rank_history append"
    - "Sign-off with empty lessons_propagated"
    - "Hand-editing rank_history (it is append-only)"
    - "Filing a task without compression_passport (invisible to option-surface)"
    - "Filing an unranked task (a wish, not a todo)"
doctrine_edges:
  principles: [pri_049, pri_118, pri_121_candidate, pri_128, pri_136, pri_140]
  axiom_candidates: [axiom_candidate_integration_not_greenfield]
  paper_modules: [task_ledger, navigation_hologram_theory, agent_entry_surfaces]
  standards: [std_task_ledger, std_task_sign_off, std_skill]
---

<!-- registry: skill_registry.json -> task_ledger | family: task_ledger -->

## Why this skill exists

The operator's gesture (2026-04-30): *"can you create for me a ledger which agents can add to and update and its always being updated and each entry can be ranked and we're always adjusting the rankings and justifying why we adjust... so that our system can constantly have a mental todo list this is super powerful if done right."*

That is unambiguous: a multi-writer, durable, rank-ordered, justification-bearing surface with a sign-off lane. No existing kind covers it; the paper module carries the coverage-gap proof, and the standards carry the schema.

This skill governs **when** to reach for the ledger and **how** to mutate it without breaking the audit chain, so todos do not evaporate into chat memory.

## Forward Integration Default

Type A agents operate in `forward_integration` mode by default. A dirty tree is normal; classify risk, continue when the target action will not lose information, and capture unresolved uncertainty as WorkItems instead of final-report prose.

Strictness is about authority, not cleanliness. `state/task_ledger/events.jsonl` is WorkItem mutation authority; `events_audit.jsonl` is ignored recovery journal; `ledger.json`, `sign_offs.json`, and `views/*.json` are projections. Audit-only events require `authority-health` / `audit-recover --replay` plus rebuild before closeout claims. Unrelated dirty traces/projections/indexes/sidecars are warnings unless this action would overwrite them. Unknown dirty targets need inspection; destructive restore/reset/clean/delete needs `destructive_override_required`; touched Task Ledger authority needs strict validation and projection rebuild/check.

The runtime entrypoint for this law is:

```bash
./repo-python kernel.py --workitem-entrypoint [PHASE]
```

Use its Kanban rows only as projection affordances for choosing work and inspecting WIP/blockers/signoff. Mutate through Task Ledger events, never by editing board rows.

## Organizer Report

When the question is "what should happen to captured work?", start with the organizer report before acting:

```bash
./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2
```

The report is read-only. It explains backlog health, propagation-needed rows, promotion candidates, execution-menu commitments, missing contracts, merge/retire candidates, and possible adapter-leak captures. `actuation_recommendations` proposes safe command templates with mutation verb, payload fields, review posture, and blast radius.

Treat those templates as proposals, not automation. Promotion/ranking, duplicate retirement, and possible adapter-leak quick-captures still require operator review. The report must never auto-mutate rows, install hooks, bulk-clear candidates, or treat view membership as priority authority.

For complex payloads, prefer writing the JSON to a temporary file and passing it with the existing `--payload-file` option on Task Ledger event verbs. Inline `--payload-json` templates are examples for small payloads only.

Priority means gated leverage, not salience. Read hard gates from `work_graph_priority_metabolism_v0` / `priority_cluster_summary`, then choose the smallest owner action that changes future behavior: WorkItem, cap family, dependency blocker, duplicate chain, missing contract, propagation debt, seed/standard/skill/route/paper gap, generated-state blocker, or operator-review boundary. Execution-menu rows still matter, but repeated caps/self-errors may point to an owner-surface patch. Raw inbox volume is memory pressure, not priority. Low-pass organizer work may scan, cluster, patch safe owner surfaces, and propose event commands; it must not auto-promote, auto-rerank, auto-retire semantic duplicate groups, execute from `capture_inbox`, or treat classification as success when a patchable owner action exists.

The metacontrol contract lives in `codex/standards/std_task_ledger.json::metacontrol_contract`, especially `provider_native_task_affordance_boundary`: provider-native todo/task displays are within-session scratch only. Durable side work becomes a Task Ledger event, propagation disposition, retirement/blocker, or explicit `nothing_to_refine`; native affordances are never cross-session backlog authority.

The same contract treats problem-shaped signals as first-class capture input. Preserve complaints, aspirations, principles, integration pressure, or todos cheaply; capture assimilation later normalizes, dedupes, routes, orders, promotes, blocks, retires, or propagates them.

## Projection Handle Boundary

Task Ledger cluster rows may expose diagnostic handles that are not WorkItem ids. For example, `dependency_anomalies` can surface `dep_anom_*` handles as view-local findings; if `--option-surface task_ledger --band card --ids <handle>` reports `missing_ids`, do not treat that handle as a mutation subject or CAP to close. Open the governing view or organizer report, identify the concrete WorkItem/event/source row behind the diagnostic, then append the owner event against that subject.

When live concurrency makes a diagnostic handle disappear between cluster browse and card drilldown, treat that as recovered local truth, not as a failed proof. Re-check the view or `validate --allow-warnings`, record the pivot in Work Ledger if you held a claim, and choose a disjoint owner lane instead of creating a parallel capture just to satisfy no-null pressure.

## WorkItem Spine Operating Grammar

When Type A work touches more than a local implementation detail, operate through the spine rather than from chat memory. The runtime wake path is the first affordance, not an optional diagnostic:

```bash
./repo-python kernel.py --pulse
./repo-python kernel.py --phase
./repo-python kernel.py --workitem-entrypoint <phase>
./repo-python kernel.py --agent-wake-packet <phase> --agent-wake-limit 12
./repo-python tools/meta/factory/task_ledger_apply.py validate --allow-warnings
./repo-python tools/meta/factory/task_ledger_project.py rebuild --check
```

Add Prompt Ledger validation for prompt/provenance traces, and use Work Ledger `session-preflight` with exact path claims before mutation. The entrypoint covers dirty-surface policy, backlog selection, concurrency/subphase posture, and validation obligations.
Use bare `validate` only when strict nonzero exit on warning-only evidence durability is the intended diagnostic.

Warning-only validation baseline: when `validate --allow-warnings` returns `valid_with_warnings` with `error_count=0`, classify the warnings before capture. If they are known historical/baseline evidence-durability rows and there is no task-owned warning, new warning class/source, or warning-count delta, cite the validation as closeout evidence and do not quick-capture another WorkItem just to mention it. If a new warning must be captured during ledger concurrency, run one serialized append-only `quick-capture` without `--rebuild` and wait for the authority-visible `visibility_receipt`; do not start duplicate retry commands.

Authority grammar:

| Surface | Authority role | Mutation rule |
|---|---|---|
| Task Ledger | WorkItem/cap/task/signoff authority | Append events through `task_ledger_apply.py`; rebuild projections. |
| Work Ledger | execution/session/claim/closeout authority | Use Work Ledger CLI for preflight, claims, closeout, release, finalize. |
| Prompt Ledger | prompt/provenance/idempotency authority | Append prompt provenance; derived work becomes Task Ledger capture/link. |
| Phase/kernel/mission blackboard | orientation and readiness packets | Treat as phase/subphase read models unless owner tooling says otherwise. |
| Provider receipts | immutable provider-output provenance once implemented | Adopt by receipt; never let provider output mutate source directly. |
| HUD/Station/Kanban/Vantage | projections and cockpit affordances | Read for selection/visibility; mutate underlying ledgers only. |
| Annexes | mined candidate patterns | Translate into captures/mechanisms; do not import wholesale. |

Work selection:

1. Read `state/task_ledger/views/execution_menu.json` before implementation work. It is the commitment-event queue, not the shaped-capture list or legacy rank list. Do not pick only the newest cap unless the menu or operator override explains why.
2. Treat `capture_inbox` as append-only raw material, not an execution queue. Large capture count is not failure; unshaped captures never being triaged is failure.
3. Treat `promotion_candidates` as the shaped-capture review queue. Promote, finish-shape, block, or retire rows there before they become execution commitments.
4. Closed/signoff caps are evidence, merge/retire candidates, or provenance anchors, not active WIP.
5. An urgent operator-driven repair may create or use a capture outside the menu, but it must record why it bypassed the menu and must not silently become global rank.
6. Every active slice must name the WorkItem/cap it serves. If no item exists, append a capture before implementation.

Meta-missions and metabolism:

- A foreground bounded campaign is a `meta_mission` WorkItem lane or projection over WorkItems.
- A background recurring reflex is a `metabolic_reflex` WorkItem lane or projection over WorkItems.
- Runtime blackboards may show current state, cadence, or active rows, but they are not separate boards.
- Every meta-mission/metabolic run must say which WorkItem, phase/subphase, authority surface, and closeout receipt it serves.

Concurrency:

- Multiple Type A agents may work in parallel when their exact target path claims do not collide.
- Stale/orphan sessions are watch-level unless they hold active claims or collide with the target path.
- Unknown-scope sessions are attention, not a global stop sign.
- Claim exact paths before mutation; after Task Ledger signoff/residual capture and Work Ledger closeout, run `session-finalize` to release remaining active claims by default.
- WorkItem-id claim collision is not a separate authority yet; Work Ledger path/td claims are the enforceable coordination primitive.

Subphase:

- `subphase_runtime_attention` is projection-only. It composes phase freshness, mission blackboard, execution menu, Work Ledger pressure, strict JSON attention, and mechanism affordances.
- Phase freshness conflicts do not block ordinary scoped work, but phase-file mutation requires owner tooling or an explicit capture for missing phase authority.
- A phase objective and execution menu may differ during substrate/meta-mission repair. The agent must name the mismatch and either justify it as an urgent/operator-driven spine repair or capture the ambiguity.

Mechanisms:

- Mechanisms are operational recipes, not a decorative registry. A valid mechanism names its authority surface, mutation surface, projection surface, owner tool, validation command, concurrency policy, and closeout policy.
- `applicable_mechanisms` in the WorkItem entrypoint is a code-grounded affordance list. If a mechanism cannot be tied to real code, standard, skill, or owner command, file a capture instead of minting mechanism JSON.
- Mechanism self-use/failure/miss/conflict/error teaching its class is self-uppropagation-shaped; route to governing mechanism, not generic TODO

Local-to-general propagation:

- At closeout, decide whether the local case refined a skill, paper module, standard, mechanism, capture, or principle candidate.
- "Future work", "maybe", "needs verification", "v1", and "not yet wired" are not final-report payloads. They become Task Ledger captures, blockers, retirements, or explicit no-propagation receipts.
- A sidecar capture bundle is only the inlet. If an operator-carried packet says the issue is handoff behavior, Type A/B dynamics, or propagation failure, route through local-to-general propagation instead of treating local CAPs as sufficient.

## When does this skill fire — consume time, not annotation time

Like `annex_pattern_transfer`, this skill fires on **situated** moments, not preemptively. Specifically:

1. **Operator names a todo.** *"add a task,"* *"file this for later,"* *"note this and rank it,"* *"this is more urgent than X."*
2. **Agent finishes work that reveals follow-ups.** A task closes; the closeout uncovers two new pending items; file them before yielding.
3. **Cold agent at session start needs orientation.** The ledger is the first thing to read after `--vantage` or `--pulse` to know what's pending and at what rank.
4. **About to author new substrate.** Pri_136-conformant: check the ledger first; a task may already name this work.
5. **Re-prioritization moment.** New evidence, dependency unblock, operator gesture, doctrine update — any of these may trigger a rank change.
6. **Sign-off moment.** A task hits `completed`. The skill governs the propagation.

### Quick capture for noticed side work

When an agent is deep in another task and notices a real follow-up, preserve it with the low-friction capture lane instead of leaving a sidebar TODO in chat memory:

```bash
./repo-python tools/meta/factory/task_ledger_apply.py quick-capture \
  --title "Short noticed work title" \
  --statement "One sentence describing what should be handled later." \
  --source-ref "raw_seed:<paragraph_id or local evidence ref>" \
  --surface "path/or/command/that/anchors/the/notice"
```

Capture discipline:

- Capture intent, not just literal wording. Preserve the broad capability, uncertainty, owner clues, evidence refs, risk, and satisfaction contour.
- Keep exact paths, ordering, owner, and method provisional until current disk proves them. Use `candidate_surfaces`, `type_a_discovery_required`, and `unresolved_surface_questions` when needed.
- Do not rank, shape, merge, claim, or plan from a quick capture unless the current slice already owns that work.
- Prefer "investigate/close X surfaced by Y; candidate surfaces include Z; verify ownership/generated-vs-source/duplicates before acting; satisfied when proof P exists."
- Treat the CLI as receipt shape. `quick-capture` takes `--title` plus `--statement`, `--note`, or `--problem`, not a positional title. Prefer repeated `--tag` flags; `--tags` is accepted only as a compatibility alias and comma-separated values are normalized. If uncertain, run `quick-capture --help` before mutating.
- Do not cite a `cap_id` until the command exits successfully and the returned `visibility_receipt` shows the event visible in Task Ledger authority. Projection/card visibility is separate: add `--rebuild` only when the current action needs card visibility and the projection lane is uncontended. A failed append, shell error, intended title, or stale projection card is not a capture receipt.
- If `quick-capture` or Work Ledger `session-preflight` fails before append/claim with a disk-headroom or `errno 28` guard, treat it as no authority receipt and no Work Ledger claim. Stay off user-facing blocker prose, inspect free space, remove only explicit disposable scratch/cache paths with no active owner handles, then retry the capture or session-preflight. Capture the disk-headroom failure once authority append works; do not delete active temp clones or lower guard thresholds as a routine bypass.

Status/update/final micro-protocol:

1. Before any user-facing status, final answer, apology, correction, or operator-correction acknowledgement, scan the sentence for side findings, gaps, failing tests, residuals, blockers, or self-errors.
2. If one is present and no authority-visible event id already exists, run exactly one serialized append-only `quick-capture` first, normally without `--rebuild` during scoped source or ledger concurrency.
3. Do not publish "capturing now," "will capture," or "I'll record this" as the status update. Stay silent until the command returns an authority-visible `visibility_receipt`, then cite that event id or avoid the residual text.
4. If another Task Ledger mutation is currently running, wait for it to finish before writing the status. The chat text is not the backlog and not a receipt.

Residual Closure Protocol: a named residual cannot evaporate into prose. Before yielding, any noticed unresolved issue, drift, validation failure, missing affordance, suspicious invariant, or follow-up needs one receipt: fixed now, quick-captured, linked to a WorkItem, or explicit no-op/not-actionable. `quick-capture` enters `capture_inbox` / `capture_triage`; promotion, commitment, rank, and signoff happen later through organizer events.

Warning-only baseline results are not residuals by themselves. `valid_with_warnings` plus `error_count=0` routes to the baseline rule above unless the warning is new, task-owned, or materially changed.

Partial-instruction residual rule: when a broad packet yields only a slice, bind the slice to the active mission/WorkItem and route remaining durable deliverables to an existing WorkItem, new quick-capture, blocker/retirement, or explicit no-residual/no-op verdict. Native TODOs and "future work" prose are scratch.

Keep `--surface` concrete: one path, command, schema, option-surface id, or owner artifact. Put extra surfaces in payload/notes/shape events; no fake concatenated paths. Run append/rebuild serially. Keep the Task Ledger authority lock short: expensive projection loads, duplicate scans, host-pressure checks, queue planning, and rebuild/check work happen outside the lock; the locked section only verifies the authority tail, finalizes hashes/metadata, and appends. During scoped source commits or active Task Ledger concurrency, prefer append-first quick-capture without `--rebuild`, cite the authority-visible receipt, and leave projection assimilation to the generated-state drainer lane. After retry/collision, rerun projection + validation and add bookkeeping. For notice classification, use `std_task_ledger.json::metacontrol_contract` plus `capture_assimilation`.

### Same-authority append-log landing

When `state/task_ledger/events.jsonl` contains valid apply-lane events, attribution is by `event_id`, `created_by`, `previous_event_hash`, and `event_hash`. Multiple agents' valid events can land in one deterministic projection bundle; shared event/projection files alone are not a commit blocker. If a scoped source commit only needed a capture receipt, do not stage Task Ledger projections with that source commit just to satisfy the capture reflex; land source paths through scoped commit and settle Task Ledger authority/projection dirt through this lane.

Landing lane:

```bash
./repo-python tools/meta/factory/task_ledger_apply.py validate --allow-warnings
./repo-python tools/meta/control/generated_state_drainer.py settlement-plan --owner-id task_ledger_projection
./repo-python tools/meta/control/generated_state_drainer.py settle --owner-id task_ledger_projection --dry-run
./repo-python tools/meta/factory/work_ledger.py session-preflight --session-slug <slug> --actor codex --phase-id <phase> --write-profile task_ledger --work-admission-class projection_settlement --require-exclusive
./repo-python tools/meta/control/generated_state_drainer.py settle --owner-id task_ledger_projection --work-ledger-session-id <session_id>
```

Dry-run planning may omit a Work Ledger session id, but mutating `settle` must use a live session id with the `task_ledger` write profile or exact owner paths claimed. If authority health reports missing audit events, run `audit-recover --replay` before landing. `drain-intake` is only for pending execution-receipt intake, not quick-capture intake, hunk-only event commits, or normal deterministic projection landing.

If `generated_state_drainer.py settle` returns a terminal residual or nonzero failure for a ledger owner such as `task_ledger_projection` or `work_ledger_index_projection`, do not loop or broaden staging. Read the owner row: `source_moved_owner_ids`, `residual_actionability=wait_for_source_authority_quiescence_before_retry`, `owner_bundle_completeness`, `missing_expected_stage_paths`, and `next_safe_command` are the re-entry contract. When the pass revealed an owner-tool contract gap, append one authority-visible quick-capture without `--rebuild`, finalize/release the Work Ledger session with that capture or landed commit refs as append-exempt evidence, and leave projection settlement for a quiet owner window.

### Organizer metabolism: salience is not priority

The Task Ledger is deliberately split into cognitive roles:

```text
quick-capture -> capture_inbox -> capture_triage -> promotion_candidates -> execution_menu -> signoff/propagation
                         \              \                       \                  \
                          \              \                       \                  Work Ledger claims and receipts
                           \              merge_or_retire / stale_review
                            prompt_trace / work_ledger linkage repair
```

`quick-capture` has side-observation privilege only. It preserves signal, source ref, surface, tag, and confidence; it does not rank, select execution, or make operator authority. The organizer pass owns later planning.

Use the browse surface before raw JSON:

```bash
./repo-python kernel.py --option-surface task_ledger --band cluster_flag
./repo-python tools/meta/factory/task_ledger_apply.py search --query "<text-or-id>" --limit 20
```

Use `search` for exact text/id lookup when a query is known but a WorkItem id is not. It reads the existing projection only, returns compact rows with card drilldowns, and must not append events, rebuild projections, or scan the repo. Use `cluster_flag` when selecting by backlog shape, view, or organizer lane.

Each cluster row carries `organizer_routing`: role, claim, allowed actions, recommended next events, hints, missing affordances, integration/file hints, and salience boundary. Treat `common_file_hints` as scent, not authority. Verify exact surfaces before mutation; aspirational bridge/provider moves stay conceptual until the apply lane exposes them.

Organizer actions by view:

| View | Role | Typical next event |
|---|---|---|
| `capture_inbox` | salience inbox | `work_item.triaged`, `work_item.shaped`, or `work_item.retired` |
| `capture_triage` | gating triage | `work_item.shaped`, `work_item.promoted`, `work_item.blocked`, or `work_item.retired` |
| `promotion_candidates` | promotion review | `work_item.promoted`, `work_item.shaped`, `work_item.blocked`, or `work_item.retired` |
| `execution_menu` | commitment boundary | `work_item.claimed`, `work_item.state_transitioned`, `work_item.blocked`, or signoff evidence |
| `missing_*` / `incomplete_work_items` | contract shaping | `work_item.shaped`, `work_item.blocked`, or `work_item.note_added` |
| `needs_signoff` / `signoffs` | consolidation | `work_item.signoff_recorded`, `work_item.propagation_recorded`, or a fresh `work_item.captured` follow-up |
| `merge_or_retire_candidates` / `stale_review` | trace evaporation | `work_item.retired`, `work_item.note_added`, or evidence linkage |
| `prompt_trace_unlinked` / `work_ledger_unlinked` | provenance and execution linkage | `work_item.note_added`, `work_item.claimed`, or signoff evidence |

Healthy organizer metabolism keeps capture cheap while preventing trace pollution: stale, duplicate, closed, or ungrounded traces must be merged, retired, blocked, or left as evidence before distorting promotion review or the execution menu.

### Problem signals are feedback

Problem capture is the Task Ledger form of the cybernetic axiom. A complaint is not noise and not automatically a task; it is a feedback signal. The minimum useful packet is:

```text
signal_kind, source_ref, surface, complaint_or_desire, why_it_matters,
suspected_owner, desired_change, evidence_or_absence, confidence, dedupe_keys
```

Use `quick-capture` when the current slice should not stop to organize. Use `capture_assimilation` when many signals need a correction path. Type A assimilation should route: `subject_id -> signal_kind -> problem_frame -> owner surface -> disposition -> next move -> dependency -> uncertainty probe -> proof signal -> escalation level`.

During assimilation, keep capture rows distinct from richer protocol output. Events store source, signal, desired change, and evidence; organizer review may add frame, severity, priority basis, escalation, uncertainty probe, and proof signal before deciding whether to append more events.

## Preconditions — the ledger must exist and be parseable

1. **`state/task_ledger/ledger.json` exists and parses as `task_ledger_v1`.** If parse fails, the skill is in error state; do not author until repaired.
2. **`state/task_ledger/sign_offs.json` exists and parses as `task_sign_off_ledger_v1`.** Same.
3. **The relevant paper module + standards are on disk.** This skill is the verb; the paper module is the noun; the standards are the schema. All three together are required for a clean authoring move.

## The MOVE

Use the apply lane whenever it supports the needed event:

```bash
./repo-python tools/meta/factory/task_ledger_apply.py quick-capture --help
./repo-python tools/meta/factory/task_ledger_apply.py search --query "<text-or-id>" --limit 20
./repo-python tools/meta/factory/task_ledger_apply.py authority-health --ids <cap_id>
./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2
./repo-python tools/meta/factory/task_ledger_apply.py validate --allow-warnings
./repo-python tools/meta/factory/task_ledger_project.py rebuild --check
```

Operational rules stay simple:

- Browse first with `./repo-python kernel.py --option-surface task_ledger --band cluster_flag`.
- Append or shape through events; direct projection edits are rescue-only.
- Every rank change needs a rank/history justification.
- Every status transition needs evidence or a blocker note.
- Completion requires sign-off evidence plus propagation or explicit `nothing_propagated`.
- Problem-signal ordering uses `capture_assimilation`; this skill only preserves and mutates the WorkItem substrate.

Full field-level requirements live in `codex/standards/std_task_ledger.json` and `codex/doctrine/paper_modules/task_ledger.md`.

## Read-discipline — option-surface before raw json

Before `cat`-ing the ledger or grepping it, climb the bands:

1. **cluster_flag band.** Cheapest browse: views such as execution_menu, dependency_blocked, unlocks_by_rank, promotion_candidates, capture_triage, needs_signoff, active_wip, blocked, merge_or_retire_candidates, prompt_trace_unlinked, and work_ledger_unlinked. Use this before opening rows.
2. **projection search.** `task_ledger_apply.py search --query "<text-or-id>"` reads the ledger projection once and emits compact matches plus card drilldowns. Use it instead of `find`, raw `jq`, or grep when asking "which WorkItem mentions X?"
3. **flag band.** WorkItem row: stable id, title, state, work_item_type, triage status, missing contracts, source refs, prompt/Work Ledger linkage, dependency_status, views, rank, and card drilldown.
4. **card band.** Selected WorkItem: statement, refs, paths, checks, dependency_status, authority/execution summary, projection completeness, source events, and omission receipt.

Dependency reading rule: if the task asks what blocks a cap, what it depends on, what it unlocks, or priority order, open card band before raw JSON. Upstream/downstream edge rows carry titled prerequisites, states, reasons, and waiting status; id lists alone are indexes. Station/Vantage samples are not authority.

The option surface is browse-only. Mutation still goes through `task_ledger_apply.py` events, then projection rebuild/validation.

## Anti-patterns

- **Unranked tasks.** A task without a rank is a wish, not a todo.
- **Silent re-rank.** Changing rank without appending rank_history is a discipline failure that breaks the audit chain.
- **Compression-passport-less entries.** Tasks lacking atom/flag/card cannot be browsed at low bands; debt accumulates.
- **Sign-off without lessons_propagated.** Leaving learning on the floor. At minimum: `kind: nothing_propagated` with gloss.
- **Hand-editing rank_history or notes.** Both are append-only by contract. Past entries are never edited or deleted.
- **Ledger as dumping ground.** A ledger with 200 'proposed' tasks and 0 'completed' is a wishlist. Retire stale entries.
- **Direct file edit when v1 apply lane is live.** Once `task_ledger_apply` ships, hand-edit becomes the same kind of failure as hand-editing principles JSON: the metabolism may revert.
- **Greenfield re-implementation.** Per pri_136, do not author a parallel todo surface. Densify within the existing pair.

## Lifecycle Drilldown

Keep this loaded skill operational: browse the ledger, choose the event lane, mutate through `task_ledger_apply.py`, rebuild/check projections, and close residuals before prose. Full lifecycle detail lives in [task_ledger_lifecycle_reference.md](task_ledger_lifecycle_reference.md) and [operational_work_item_spine.md](../../paper_modules/operational_work_item_spine.md).

Compact lifecycle:

```text
capture -> triage -> promote/shape -> claim -> execute -> review -> sign-off -> propagate -> closeout
```

The invariant remains: the pair (`task_ledger` + `task_sign_offs`) is the surface. New UI, bridge, provider, prompt, closeout, and vantage work must project from WorkItem events instead of creating a parallel todo system.
