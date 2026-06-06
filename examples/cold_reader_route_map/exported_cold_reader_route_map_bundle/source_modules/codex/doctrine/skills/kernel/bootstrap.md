---
id: "kernel_bootstrap_skill"
kind: "operation"
skill_type: "orientation"
summary: "Kernel startup protocol for orienting an agent to the navigation tier, workflow skills, and command surface."
focus_paths:
  - kernel.py
  - system/lib/kernel_navigation.py
  - codex/doctrine/skills/kernel/_schema.json
doc_links:
  - docs/raw_seed_doctrine_derivation.md
  - codex/doctrine/skills/kernel/navigate.md
  - codex/doctrine/skills/kernel/observe.md
  - codex/doctrine/skills/kernel/observe_patterns.md
  - codex/doctrine/skills/kernel/observe_plan_authoring.md
  - codex/doctrine/skills/kernel/plan.md
  - codex/doctrine/skills/kernel/implement.md
  - codex/doctrine/operations/runtime_change_protocol.md
last_verified_at: "2026-03-09"
name: "kernel-bootstrap"
description: "Universal startup protocol for Codex agents in this repository. Use at the start of any task to orient with the kernel navigation layer and available skills before selecting observe, plan, validate, or apply workflows."
---
<!-- registry: skill_registry.json → bootstrap | family: kernel -->
<!-- DOCTRINE_STRUCTURED_BLOCK -->

**Governing principles:**
- Run the live-state bootstrap handshake before substantive unknown work: `--info` for the router/static HUD, `--preflight` for the agent-start card, `--pulse` for current state, then `--entry "<task>"` for the task-conditioned control packet.
- Coverage-first navigation beats lexical-luck search. Broad development first contact must expose `--kind-atlas`, `--option-surface`, `--context-pack`, or `--workitem-entrypoint` coverage before exact-name lookup.
- Select the smallest relevant skill set before acting — don't load every skill by default.
- Distinguish FACTS from INFERENCES in any output. Never let inference masquerade as fact.
- Trust disk state over memory. Read pipeline_resume.json, synth_seed.json, and cycle artifacts — do not reconstruct from recollection.
- For manually queued "continue/resume/choose the next move" prompts, route through `autonomous_continuation` after the bootstrap prelude. If the latest response has a saved Trace Capsule, response bundle, or inline paste, treat it as primary evidence to read before answering, then verify live repo paths, claims, receipts, and current work before trusting specifics. Recover live app goal state, Work Ledger claims, Task Ledger/CAP pressure, recent traces, prompt-shelf evidence, sibling thread/session activity, and dirty-path ownership before selecting a write lane.
- When seed-speed Work Ledger status reports `first_action_kind=unclaimed_touched_owner_repair`, treat the named owner session as first-contact coordination evidence. Read it once before starting a fresh phase mutation, then either let the owner land/release, send one owner-visible Work Ledger message if coordination is the blocker, or pivot to a claimed disjoint owner-surface edit that reduces the same failure mode. Claim, heartbeat, release, finalization, and ledger-settlement-only passes are not successful continuation passes unless followed by substrate improvement or a blocked/non-success receipt.
- When seed-speed reports `claim_session_heartbeat_gap_count > 0` or `heartbeat_gap_claim_sessions[]`, read the named session card and treat its claimed paths as owned-but-unconfirmed, not unclaimed. If you are not that owner, do not mutate the claimed scope; either send one bounded Work Ledger signal if fan-in is the blocker, or pivot to a claimed disjoint owner-surface edit that carries the coordination rule. Publishing a heartbeat/finalize signal alone is not a successful continuation pass unless it lands a substrate improvement or a blocked/non-success receipt.

## Purpose
Kernel startup protocol for orienting an agent to the navigation tier, workflow skills, and command surface.

**“Where we are” authority (Problem 7):** `--working-set`, `--pulse`, phase packets, and pipeline JSON answer different questions—do not treat them as one interchangeable “current context.” See `docs/raw_seed_doctrine_derivation.md` (*Anchor divergence…*) and `documentation_theory_index.json` → `framework_usage.problem_7_anchor_playbook_anchor`.

## Fast Path vs Deep Reference

Keep this file skim-fast. It should name the startup sequence and the lane choice, not absorb every command table or parameter note.

- For exact kernel navigation commands and decision ladders, open `codex/doctrine/skills/kernel/navigate.md`.
- For the full browse surface of available skills, open `codex/doctrine/skills/skill_map.md`.
- For shared hub and adapter-specific read order, reopen `AGENTS.md`, `CODEX.md`, or `CLAUDE.md` instead of stuffing that detail here.

If a future edit wants to add detailed command parameters or a long skill catalog to this file, move that detail to the adjacent reference surface and link it from here.

## Scope
- This doctrine file is `codex/doctrine/skills/kernel/bootstrap.md`. [focus:kernel.py]
- Source of truth includes `kernel.py`. [focus:kernel.py]
- Source of truth includes `system/lib/kernel_navigation.py`. [focus:system/lib/kernel_navigation.py]
- Source of truth includes `codex/doctrine/skills/kernel/_schema.json`. [focus:codex/doctrine/skills/kernel/_schema.json]

## Claims
- Canonical claim path: `kernel.py`. [focus:kernel.py]
- Canonical claim path: `system/lib/kernel_navigation.py`. [focus:system/lib/kernel_navigation.py]
- Canonical claim path: `codex/doctrine/skills/kernel/_schema.json`. [focus:codex/doctrine/skills/kernel/_schema.json]

## Interfaces
- Focus paths:
  - `kernel.py`
  - `system/lib/kernel_navigation.py`
  - `codex/doctrine/skills/kernel/_schema.json`
- Related docs:
  - `docs/raw_seed_doctrine_derivation.md`
  - `codex/doctrine/skills/kernel/navigate.md`
  - `codex/doctrine/skills/kernel/observe.md`
  - `codex/doctrine/skills/kernel/observe_patterns.md`
  - `codex/doctrine/skills/kernel/observe_plan_authoring.md`
  - `codex/doctrine/skills/kernel/plan.md`
  - `codex/doctrine/skills/kernel/implement.md`
  - `codex/doctrine/operations/runtime_change_protocol.md`
<!-- END_DOCTRINE_STRUCTURED_BLOCK -->
Use this as the default system prompt pattern for any task.

## System Prompt Template

```text
You are a Codex agent operating in ai_workflow.

Always begin with orientation, but scope it first: clearly external host/OS/app support that does not need repo substrate, generated state, phase context, or durable doctrine edits may use direct local tooling or web evidence after the compact seed. Re-enter this ladder if the task becomes repo work.
1) Run `./repo-python kernel.py --info` for the compact static/router HUD.
2) Run `./repo-python kernel.py --preflight` for the compact agent-start card: active phase, runtime posture, freshness risks, next safe command, and do-not warnings.
3) Run `./repo-python kernel.py --pulse` when current live state, active phase, queues, hotspots, or next control action could affect the task.
4) Run `./repo-python kernel.py --entry "<task>" --context-budget 12000` as the task-routing control packet. `--info`, `--preflight`, and `--pulse` are the live-state prelude; they do not replace `--entry`.
5) For broad or unknown development work after entry, start from coverage: `./repo-python kernel.py --kind-atlas --band flag`, `./repo-python kernel.py --context-pack "<task>" --context-budget 12000`, or `./repo-python kernel.py --workitem-entrypoint <phase>` when active WorkItem execution matters.
6) Browse the relevant kind with `./repo-python kernel.py --option-surface <kind> --band cluster_flag` or `--band flag`; drill to `--band card --ids <id>` after a row is named.
7) Treat `--skill-find` as exact lookup, coverage-surface drilldown, or fallback only. It is banned as guessed first-contact capability discovery.
8) If you need the exhaustive routing tables, question router, or contract boilerplate, rerun `./repo-python kernel.py --info --full`.
9) Prefer `./repo-python kernel.py --orient-task <task-or-note>` only after the coverage surface does not already name the target. It resolves the strongest route across notes, plans, files, missions, and doctrine tokens.
10) Use `./repo-python kernel.py --working-set` only when the task is clearly a continuation of recent obsidian work. If the packet exposes `seed_context`, read that bounded grounding note before widening search.
11) Use `./repo-python kernel.py --bootstrap-task <note-or-token>` only when the target note is already known and you need the bounded task-entry packet. If the packet exposes `focus_board`, treat it as the folder-scoped active-state ledger for that note family.
12) Use `./repo-python kernel.py --set-focus <note-or-token>` when the continuity packet needs an explicit active note, later-use badge, or reopening handoff. It previews by default; add `--live` only after the write plan matches intent.
13) Use `./repo-python kernel.py --plan-phase` when the task is phased implementation work, then `./repo-python kernel.py --compile-batch [current|<id>]` to compile the current file slice before grepping or wide file reads.
14) Use `./repo-python kernel.py --compile <path-or-token> [...]` when you already know the files and want bounded semantic cards instead of raw file dumps.
15) Use `./repo-python kernel.py --option-surface skills --band cluster_flag` to browse the skill surface, then open only the relevant skill docs from `codex/doctrine/skills/` and `codex/doctrine/skills/kernel/`.
16) If the task starts from `observe_dumps`, `_observe_plan.json`, stored bridge answers, or a `continue` request, read `codex/doctrine/skills/kernel/observe_patterns.md`.
17) If the task authors or repairs observe plans, read `codex/doctrine/skills/kernel/observe_plan_authoring.md`.
18) If the task authors or repairs a continuity-target obsidian work note, read `codex/standards/std_work_note.json`.
19) If the task edits codex markdown or substrate JSON, read `codex/doctrine/operations/codex_change_protocol.md` before patching.
20) If the task changes runtime/path contracts or generated observe outputs, read `codex/doctrine/operations/runtime_change_protocol.md`.
21) If `--bootstrap-task` or `--read-observe latest` returns a typed result note plus synthesis artifact, use those as the primary authoring surface before opening raw grouped responses.

Execution policy:
- Evidence-first: do not propose architecture claims without file or dump evidence.
- Prefer kernel navigation commands over raw file reads for system understanding.
- If the request is cross-lane integration, hidden-substrate wiring, Type A dispatch selection, TACO/terminal-compression import, or asks whether the active phase is acting as a control envelope, run `python3 kernel.py --campaign --task "<query>"` before widening phase-task residual lanes. When `campaign_write_guard.effective_write_authority=campaign`, nested phase alignment is context only and cannot authorize live phase writes.
- If the active phase primary wave and the request appear to diverge, do not narrate the mismatch manually. Run `python3 kernel.py --phase <phase> --task "<query>"` and follow `task_phase_alignment.selected_lane`, `legal_owner_surfaces`, and `write_guard`.
- If the request is a generic continuation or manual queue seed, open `autonomous_continuation` after `--entry`/`--context-pack`. Treat stale prompt text as transport evidence, read any saved Trace Capsule or response bundle as evidence, recover live app/thread/session/work-ledger truth, and choose local continuation or a justified pivot from current ownership evidence.
- If Work Ledger seed-speed names `unclaimed_touched_owner_repair`, consume that owner card before launching, reprompting, or mutating the phase lane. A no-send pivot is valid only when the chosen local edit is disjoint, claimed, and carries the same coordination lesson. Claim repair by itself is a prerequisite or blocker receipt, not the substrate improvement.
- If Work Ledger seed-speed shows `heartbeat_gap_claim_sessions`, consume that session card before touching any claimed path. A heartbeat-gap claim is still a live ownership warning until the owner heartbeats, releases, or an explicit coordinator records a handoff; sibling passes should signal once or pivot to a disjoint claimed surface.
- Navigation and planning payloads are compact by default. Use `--full` only when a consumer truly needs the exhaustive legacy envelope.
- When continuity packets expose `seed_context` and `focus_board`, read the seed first and trust the badges (`[SEED]`, `[ACTIVE]`, or a custom `[TEXT]`) before renaming files or reopening broad note families.
- Keep focus state in frontmatter, not filenames. Preview changes with `python3 kernel.py --set-focus <note-or-token>` first, then add `--live` only when the planned write set is correct.
- For observe work, the default loop is: decompose into bounded groups, launch through `python3 kernel.py --launch-observe ...`, stop the turn, then resume from the stored artifact on the next cue. This rule is named `Launch And Yield`.
- Prefer `--bootstrap-task` authoring surfaces and `--read-observe latest` typed artifacts over raw `*_response.md` files when constructing the next grouped observe pass.
- Treat `python3 kernel.py --info` as the compact router and `python3 kernel.py --info --full` as the exhaustive routing/contract surface.
- Choose workflow by intent:
  - Diagnose/understand -> observe skill + kernel observe commands
  - Observe plan authoring -> observe_authoring skill + `--standards` / `--prompt`
  - Roadmap/sequence -> plan skill
  - Verification/status -> validate skill
  - Editing/patching -> implement/apply skill, then validate skill
- Keep command usage inside the stable kernel contract shown by `kernel.py --info`.
- Use `python3 kernel.py --paths` only when you need path diagnostics.
- When uncertain after navigation, run a targeted `kernel.py --quick` probe on specific files.

Output policy:
- Provide concise results with file references and explicit next actions.
- Distinguish FACTS from INFERENCES.
- After edits, include verification command outcomes.
```

## Operating Sequence

0. Scope the request. If it is plainly non-repo host/OS/app support and no repo substrate mutation or phase/state context is needed, use the relevant local tool or web evidence directly.
1. Orient with `--info`.
2. Read the agent-start card with `--preflight`.
3. Read current live state with `--pulse` when the task can be affected by phase, queues, hotspots, or control-plane next action.
4. Enter task routing with `--entry "<task>" --context-budget 12000`; keep the live-state prelude distinct from the task control packet.
5. For broad or unknown development work after entry, open coverage with `--kind-atlas --band flag`, `--context-pack "<task>" --context-budget 12000`, or `--workitem-entrypoint <phase>`.
6. Browse the relevant kind through `--option-surface <kind> --band cluster_flag|flag`; drill to card/source/tool only after a stable row is named.
7. Resolve the task with `--orient-task <task-or-note>` only when the coverage surface did not already identify the target.
8. Keep this doc as the thin entry layer. For deeper command detail, reopen `navigate.md`; for skill browsing, use `--option-surface skills --band cluster_flag` before opening `skill_map.md`.
9. Use `--working-set` or `--bootstrap-task` only when continuity or a known anchor note is actually part of the task.
10. If those continuity packets expose `seed_context`, read it before wider exploration. Use `focus_board` to see which note is currently active inside the folder and what later-use labels or handoffs already exist.
11. When folder focus changes, preview `./repo-python kernel.py --set-focus <note-or-token>` before writing. Use `focus_status` for active/reference/completed state and `focus_label` or `focus_handoff` when later turns need a more useful badge than a generic completion marker.
12. For phased implementation, use `--plan-phase` then `--compile-batch [current|<id>]` before broad file exploration.
13. For known files, use `--compile <path-or-token> [...]` before raw greps.
14. Select the smallest relevant skill set.
15. For generic continuation prompts, open `autonomous_continuation`; read any saved Trace Capsule/response bundle as evidence, then recover current goal/session surfaces, claims, CAP pressure, traces, prompt-shelf evidence, sibling activity, and dirty-path ownership before choosing local continuation, pivot, coordination, or blocked non-success. If seed-speed reports `unclaimed_touched_owner_repair`, read that owner session first and bind any no-send pivot to a disjoint claimed mutation that reduces the same coordination failure; claim repair alone is not a successful pass. If seed-speed reports `heartbeat_gap_claim_sessions`, read the named session card, treat its paths as owned until heartbeat/release/handoff, and only signal once or pivot to a disjoint claimed lane.
16. If the task wants several bounded reads, design the group split yourself and treat bridge workers as jigsaw-piece sub-agents.
17. Launch long grouped observe work through `--launch-observe --detach`, end the turn immediately, and resume from `--read-observe latest` or `--read-session latest`.
18. Execute observe/plan/validate/apply loop.
19. Re-validate and report exact status deltas.

Stop the bootstrap phase once the target mission, node, or run is explicit.

## Anti-Patterns

- Start implementation without the live-state prelude and task control packet when the lane is unknown.
- Use raw `cat`/`grep` as the first move when the kernel can compile context.
- Use guessed `--skill-find` as first-contact skill discovery; browse coverage surfaces first and treat skill-find as exact lookup, drilldown, or fallback only.
- Stack `--info`, `--frontier`, `--working-set`, `--bootstrap-task`, `--execution-map`, and `--map` before you have resolved what the task actually is.
- Skip coverage-first capability discovery and rely on memory.
- Rename note files just to say ACTIVE or COMPLETED when `focus_label` and `focus_handoff` can carry that state in the continuity packet.
- Change kernel flags/output contract without updating schema/docs.
