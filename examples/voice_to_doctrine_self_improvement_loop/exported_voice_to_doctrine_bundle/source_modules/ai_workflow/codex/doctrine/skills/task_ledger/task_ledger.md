---
id: "task_ledger"
kind: "operation"
skill_type: "authoring"
family: "task_ledger"
title: "Task Ledger Authoring + Reading"
summary: "The named move for keeping the system's mental todo list current: append tasks with compression_passport rungs and evidence; re-rank with appended justification; sign off completions with lessons_propagated. Pairs std_task_ledger.json + std_task_sign_off.json. Browse-first via the ledger's option-surface bands before authoring; never hand-edit rank without rank_history append."
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
description: "Keep the system's mental todo list current: interpret operator intent and noticed residuals as durable closure signals, append tasks with compression_passport rungs (atom/flag/card + when_to_open/when_not_to_open/safe_drilldown), justify every rank change in rank_history, and sign off completions with lessons_propagated chained back to raw_seed/principles/papers/skills/prompt_shelf. Browse-first via the ledger's option-surface bands; direct hand-edit of rank fields without rank_history append is a discipline failure."
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
    The task ledger is the system's mental todo list. Two paired kinds (task_ledger + task_sign_offs) governed by std_task_ledger.json and std_task_sign_off.json. Append tasks at status 'proposed' with compression_passport rungs (atom <=6 words, flag <=180 chars, card <=1200 chars, when_to_open, when_not_to_open, safe_drilldown). Re-rank with rank_history append carrying justification. Sign off completions with outcome_summary and lessons_propagated (raw_seed_append / principle_mint / axiom_candidate_append / paper_module_update / skill_update / standard_update / prompt_shelf_edit / follow_up_filed). Browse-first via task_ledger option-surface bands (cluster_flag / flag / card) before raw JSON. Direct hand-edit of rank fields without rank_history append violates the audit-chain discipline.
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

That is unambiguous: a multi-writer, durable, rank-ordered, justification-bearing surface, paired with a sign-off lane. No existing kind covers it (see [task_ledger.md paper module §Intent](../../paper_modules/task_ledger.md) for the coverage-gap proof against meta_missions / mission_blackboard / work_ledger / agent_observations / artifact_projection_debt). This skill is the operational discipline; the paper module is the theory; the standards are the schema.

The skill governs **when** an agent reaches for the ledger and **how** mutations are disciplined to keep the audit chain intact. It is the inverse of the failure mode where todos live as ephemeral chat statements that drift away after a session: the ledger holds them durably, with rank, with justification, and with sign-off propagation when the work lands.

## Forward Integration Default

Type A agents operate in `forward_integration` mode by default. A dirty tree is normal and is not a reason to stop using the Task Ledger. The ledger becomes relevant when the mess must be made recoverable: classify dirty state, continue if the target action does not risk information loss, and capture unresolved uncertainty as WorkItems instead of leaving it in final-report prose.

Strictness is aimed at authority, not cleanliness. `state/task_ledger/events.jsonl` remains WorkItem mutation authority; `state/task_ledger/events_audit.jsonl` is only the ignored recovery journal; `ledger.json`, `sign_offs.json`, and `views/*.json` remain projections. An event that exists only in `events_audit.jsonl` is recovery evidence, not closeout authority: run `task_ledger_apply.py authority-health` / `audit-recover --replay` and rebuild before claiming a card is retired, visible, or navigable. Dirty unrelated prompt traces, raw-seed projections, Work Ledger indexes, frontend files, or generated sidecars are warnings unless the current target action would overwrite or regenerate over them. Dirty unknown targets require inspection; destructive restore/reset/clean/delete actions require `destructive_override_required`; touched Task Ledger authority requires strict validation and projection rebuild/check.

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

The report is read-only. It explains backlog health, propagation-needed rows, promotion candidates, execution-menu commitments, missing contracts, merge/retire candidates, and possible adapter-leak captures. Its `actuation_recommendations` block turns those rows into safe command templates that name the existing mutation verb, required payload fields, review posture, and blast radius.

Treat those templates as proposals, not automation. Promotion/ranking, duplicate retirement, and possible adapter-leak quick-captures still require operator review. The report must never auto-mutate rows, install hooks, bulk-clear candidates, or treat view membership as priority authority.

For complex payloads, prefer writing the JSON to a temporary file and passing it with the existing `--payload-file` option on Task Ledger event verbs. Inline `--payload-json` templates are examples for small payloads only.

Priority means gated leverage, not salience. The organizer report projects `work_graph_priority_metabolism_v0` plus `priority_cluster_summary`; read hard gates first, then choose the smallest owner action that changes future behavior. The correct unit may be a WorkItem, cap family, self-error cluster, dependency blocker, duplicate chain, missing-contract cluster, propagation debt, seed drift, standard/skill gap, route gap, paper-module gap, generated-state blocker, or operator-review boundary. Execution-menu commitments and schedulable committed rows still matter, but they are not the whole graph; repeated caps and self-errors may point to an owner-surface patch that beats single-row sorting. Missing-contract rows are shaping work before they are execution work; raw capture inbox volume is memory pressure, not priority. A low-pass autonomous organizer seed may scan, cluster, patch an owner surface when safe, and propose event commands from these views, but it must not auto-promote, auto-rerank, auto-retire semantic duplicate groups, execute implementation work from `capture_inbox`, or treat classification as success when a patchable owner action exists.

The governing metacontrol contract lives in `codex/standards/std_task_ledger.json::metacontrol_contract`. Its named adapter boundary is `provider_native_task_affordance_boundary`: provider-native task tools (`TodoWrite`, TaskCreate/Update/List, `spawn_task` chips, schedule offers, or equivalent adapter task displays) are allowed as within-session scratch only. Durable side work must become a Task Ledger event, a propagation disposition, a retirement/blocker, or an explicit `nothing_to_refine`; native task affordances are never cross-session backlog authority.

The same contract now treats problem-shaped signals as first-class capture input. A complaint, problem, fear, aspiration, idea, unifying principle, refinement wish, integration pressure, or todo should be easy to preserve without deciding its final form. Capture is the cheap memory step; capture assimilation later normalizes, dedupes, routes, orders, promotes, blocks, retires, or propagates it.

## WorkItem Spine Operating Grammar

When Type A work touches more than a local implementation detail, operate through the spine rather than from chat memory. The runtime wake path is the first affordance, not an optional diagnostic:

```bash
./repo-python kernel.py --pulse
./repo-python kernel.py --phase
./repo-python kernel.py --workitem-entrypoint <phase>
./repo-python kernel.py --agent-wake-packet <phase> --agent-wake-limit 12
./repo-python tools/meta/factory/task_ledger_apply.py validate
./repo-python tools/meta/factory/task_ledger_project.py rebuild --check
```

Add Prompt Ledger validation when prompt/provenance traces are part of the slice, and use Work Ledger `session-preflight` with exact path claims before mutation. The entrypoint answers four questions in one packet: dirty-surface policy, backlog selection, concurrency/subphase posture, and validation obligations.

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

1. Read `state/task_ledger/views/execution_menu.json` before choosing implementation work. It is the explicit commitment-event queue, not the shaped-capture candidate list or legacy ranked-task list. Do not select only the newest cap unless the menu or operator override explains why.
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
- A sidecar capture bundle is only the inlet. If a Type B / operator-carried packet or follow-up correction says the real issue is handoff behavior, Type A/B actor dynamics, or propagation failure, route that class through local-to-general propagation instead of treating the local CAPs as sufficient absorption.

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
  --surface "path/or/command/that/anchors/the/notice" \
  --rebuild
```

Capture discipline:

- Capture intent, not just literal wording. Preserve the broad capability, uncertainty, owner clues, evidence refs, risk, and satisfaction contour.
- Keep exact paths, ordering, owner, and method provisional until current disk proves them. Use `candidate_surfaces`, `type_a_discovery_required`, and `unresolved_surface_questions` when needed.
- Do not rank, shape, merge, claim, or plan from a quick capture unless the current slice already owns that work.
- Prefer "investigate/close X surfaced by Y; candidate surfaces include Z; verify ownership/generated-vs-source/duplicates before acting; satisfied when proof P exists."

Residual Closure Protocol: a named residual cannot evaporate into prose. Before yielding, any unresolved issue, drift, bug-like finding, validation failure, missing affordance, suspicious invariant, or follow-up that the agent noticed or mentioned must close through exactly one receipt: fixed now, quick-captured, linked to an existing WorkItem, or explicitly no-op/not-actionable with reason. The `quick-capture` event enters `capture_inbox` / `capture_triage`; promotion, execution commitment, rank, and signoff happen later through explicit organizer events.

Partial-instruction residual rule: when the operator gives a broad packet and the current runtime executes only a slice, bind the slice to the active mission/WorkItem and route every remaining durable deliverable to an existing cap/WorkItem, a new quick-capture, a blocker/retirement disposition, or an explicit no-residual/no-op verdict before final prose. Native TODOs and "future work" paragraphs are scratch, not durable closure.

Keep `--surface` concrete: one path, command, schema, option-surface id, or owner artifact. Extra surfaces go in payload/notes/shape events; no fake concatenated paths. Run append/rebuild serially. After retry/collision, rerun projection + validation and add bookkeeping. For the full notice classification ladder, use `codex/standards/std_task_ledger.json::metacontrol_contract` plus `capture_assimilation` rather than expanding the ladder in this loaded skill.

### Same-authority append-log landing

When `state/task_ledger/events.jsonl` contains valid events from the canonical apply lane, attribution is by `event_id`, `created_by`, `previous_event_hash`, and `event_hash`. Multiple agents' valid events can land in one deterministic projection bundle; do not report that as "cannot commit" just because later captures share the same event log or projection files.

Landing lane:

```bash
./repo-python tools/meta/factory/task_ledger_apply.py validate
./repo-python tools/meta/control/generated_state_drainer.py settlement-plan --owner-id task_ledger_projection
./repo-python tools/meta/control/generated_state_drainer.py settle --owner-id task_ledger_projection --dry-run
```

If the dry run is correct, run the same `settle` command without `--dry-run`. If authority health reports missing audit events, run `./repo-python tools/meta/factory/task_ledger_apply.py audit-recover --replay` before any landing. `task_ledger_apply.py drain-intake` remains only for pending execution-receipt intake; it is not a quick-capture intake, a hunk-only event-log commit lane, or the normal way to land deterministic projections after quick-capture.

### Organizer metabolism: salience is not priority

The Task Ledger is deliberately split into cognitive roles:

```text
quick-capture -> capture_inbox -> capture_triage -> promotion_candidates -> execution_menu -> signoff/propagation
                         \              \                       \                  \
                          \              \                       \                  Work Ledger claims and receipts
                           \              merge_or_retire / stale_review
                            prompt_trace / work_ledger linkage repair
```

`quick-capture` has side-observation privilege only. It may preserve the noticed signal, source ref, surface, tag, and confidence, but it does not rank the item, select it for execution, or make it operator authority. The organizer pass owns that later planning work.

Use the browse surface before raw JSON:

```bash
./repo-python kernel.py --option-surface task_ledger --band cluster_flag
./repo-python tools/meta/factory/task_ledger_apply.py search --query "<text-or-id>" --limit 20
```

Use `search` for exact text/id lookup when a query is known but a WorkItem id is not. It reads the existing projection only, returns compact rows with card drilldowns, and must not append events, rebuild projections, or scan the repo. Use `cluster_flag` when selecting by backlog shape, view, or organizer lane.

Each cluster row carries `organizer_routing`: role, cluster claim, allowed organizer actions, executable recommended next events, command hints, conceptual next events, missing affordance refs, common source surfaces, integration/file hints, and a salience boundary. Treat `common_file_hints` as routing scent, not authority. Verify exact surfaces before mutation and append only supported events through `task_ledger_apply.py`; aspirational moves such as bridge delegation or provider job creation stay under `conceptual_next_events` until the apply lane exposes them.

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

Healthy organizer metabolism keeps capture cheap while preventing trace pollution: weak signals are easy to preserve, but stale, duplicate, already-closed, or ungrounded traces must be merged, retired, blocked, or explicitly left as evidence before they can distort promotion review or the execution menu.

### Problem signals are feedback

Problem capture is the Task Ledger form of the cybernetic axiom. A complaint is not noise and not automatically a task; it is a feedback signal. The minimum useful packet is:

```text
signal_kind, source_ref, surface, complaint_or_desire, why_it_matters,
suspected_owner, desired_change, evidence_or_absence, confidence, dedupe_keys
```

Use `quick-capture` when the current slice should not stop to organize it. Use `capture_assimilation` when the request is to turn many signals into a logical correction path. Type A should output owner-routed assimilation: `subject_id -> signal_kind -> problem_frame -> owner surface -> disposition -> next move -> dependency -> uncertainty probe -> proof signal -> escalation level`.

During assimilation, keep the capture packet distinct from richer protocol output. The event row may only store source, signal, desired change, and evidence; the organizer path may add `problem_frame`, `severity`, `priority_basis`, `escalation_level`, `uncertainty_next_probe`, and `proof_signal` as review output before deciding whether any durable event should be appended.

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
./repo-python tools/meta/factory/task_ledger_apply.py validate
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

1. **cluster_flag band.** Cheapest browse: Task Ledger views such as execution_menu, execution_menu_schedulable, dependency_blocked, dependency_graph, unlocks_by_rank, promotion_candidates, ready_by_rank, capture_triage, missing_contracts_ranked, needs_signoff, active_wip, blocked, merge_or_retire_candidates, prompt_trace_unlinked, and work_ledger_unlinked. Use this to select a WorkItem group before opening rows.
2. **projection search.** `task_ledger_apply.py search --query "<text-or-id>"` reads `state/task_ledger/ledger.json` once and emits compact matches plus card drilldowns. Use it instead of `find`, raw `jq`, or grepping ledger JSON when the only question is "which WorkItem mentions X?"
3. **flag band.** WorkItem row: stable id, title, state, work_item_type, triage status, missing contracts, source refs, prompt/Work Ledger linkage, dependency_status, views, rank, and card drilldown.
4. **card band.** Selected WorkItem: statement, satisfaction refs, raw_seed refs, integration paths, acceptance checks, dependency_status, authority/execution summary, projection completeness, source event ids, and omission receipt.

Dependency reading rule: if the task asks what blocks a cap, what a cap depends on, what completing it unlocks, or which caps should be done first, open the card band before raw JSON. `dependency_status.upstream_dependency_edges` names titled hard prerequisites with state/satisfaction/reason; `dependency_status.downstream_unlock_edges` names titled downstream WorkItems and whether they are currently waiting on this cap. `downstream_unlock_ids` alone is only an index; use the edge rows for planning explanations. Station/Vantage `work_spine` may show compact samples, but Task Ledger cards and dependency views remain authority.

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

Keep this loaded skill to the operational minimum: browse the ledger, choose the event lane, mutate through `task_ledger_apply.py`, rebuild/check projections, and close residuals before prose. Full composition, lifecycle, canonical-surface, and roadmap details live in [task_ledger_lifecycle_reference.md](task_ledger_lifecycle_reference.md) and [operational_work_item_spine.md](../../paper_modules/operational_work_item_spine.md).

Compact lifecycle:

```text
capture -> triage -> promote/shape -> claim -> execute -> review -> sign-off -> propagate -> closeout
```

The invariant remains: the pair (`task_ledger` + `task_sign_offs`) is the surface. New UI, bridge, provider, prompt, closeout, and vantage work must project from WorkItem events instead of creating a parallel todo system.
