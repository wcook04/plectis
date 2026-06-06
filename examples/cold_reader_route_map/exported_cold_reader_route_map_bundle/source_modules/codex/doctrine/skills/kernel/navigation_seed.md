---
id: "navigation_seed"
kind: "meta"
skill_type: "orientation"
family: "kernel"
title: "Navigation Seed"
summary: "Coverage-first cold navigation: use kind atlas, option surfaces, context packs, and WorkItem entrypoints before exact-name lookup or grep."
triggers:
  - "Cold session, user asks 'what in the repo is about X' and substrate is unknown"
  - "About to grep, read, or Glob before running a kernel flag"
  - "User asks how to navigate the repo, find a subsystem, or locate content"
  - "Want the navigation CLI ladder in one place"
  - "A new cold-start / preflight / next-safe-command surface shipped and must be added to the opening ladder"
  - "Don't know if the question is structural (file/path) or semantic (meaning/topic)"
  - "Commands are slow, output is too full, or an agent keeps using --phase --full / wide context-pack output as default navigation"
  - "An agent is semantically matching a prose query instead of navigating control -> kind -> cluster -> card -> source layers"
  - "A process-audit or coverage row reports anti_pattern_deep_without_ladder, or a control packet leaves the next move as multi-hop source/docs traversal without a stable owner row"
  - "A Claude/Codex entry experiment claims whole-system understanding without touching host adapters or Python substrate"
  - "A pasted agent trace, context packet, or closeout claim needs routing before the claims are trusted or assimilated"
  - "A task may benefit from annex pattern transfer, prior OSS/document patterns, or annex-backed inspiration before local design"
  - "Operator asks a system-comprehension question ('what is this system?' / 'what is X?' / 'where does Y live?' / 'what's stale?' / 'what should I read next?' / 'can this be public?' / 'how do these modules relate?') — emit the seven-part Comprehension Packet via system_self_comprehension_spine, not ad-hoc prose"
  - "Operator asks what state axes exist, what states things can be in, or adjective-shaped state questions like banned/stale/first-contact"
  - "A verification pass found nothing to edit but the operator expected a durable substrate improvement"
focus_paths:
  - kernel.py
  - codex/standards/std_kind_atlas.json
  - system/lib/kernel/commands/embed.py
  - system/lib/navigation_trace.py
  - system/lib/semantic_routing.py
  - system/lib/embedding_substrate.py
  - codex/doctrine/paper_modules/unified_navigation_layer.md
  - codex/doctrine/paper_modules/navigation_trace_binding.md
doc_links:
  - .claude/follow_on/passion.md
  - .claude/follow_on/closing_out.md
  - codex/doctrine/skills/kernel/navigate.md
  - codex/doctrine/skills/kernel/bootstrap.md
  - codex/doctrine/skills/doctrine/local_to_general_propagation.md
  - codex/doctrine/skills/doctrine/paper_module_lookup.md
  - codex/doctrine/paper_modules/local_to_general_propagation.md
  - codex/doctrine/paper_modules/embedding_substrate.md
  - codex/doctrine/paper_modules/hologram_substrate_navigation.md
  - codex/doctrine/paper_modules/semantic_routing_plane.md
  - codex/doctrine/paper_modules/unified_navigation_layer.md
  - codex/doctrine/paper_modules/host_agent_dotfile_surfaces.md
  - codex/doctrine/paper_modules/host_agent_external_surfaces.md
  - codex/doctrine/paper_modules/system_self_comprehension_spine.md
  - codex/standards/std_derived_fact.json
  - codex/doctrine/paper_modules/codex_annex_substrate.md
  - codex/doctrine/skills/annex/annex_pattern_transfer.md
  - codex/doctrine/skills/annex/annex_distillation_authoring.md
doctrine_edges:
  concepts: [con_001, con_024, con_028]
  mechanisms: [mech_019]
  principles: [pri_049, pri_111, pri_003, pri_080, pri_117]
governing_standard_ids:
  - std_navigation_contract
  - std_kind_atlas
  - std_navigation_rosetta_grammar
  - std_semantic_naming
composes_with: [bootstrap, navigate, paper_module_lookup, raw_seed_contextualize, local_to_general_propagation, nav_driven_wiring_repair, agent_session_diagnostics, annex_pattern_transfer]
name: "navigation-seed"
description: "Cold-boot navigation ladder: --entry or --workitem-entrypoint first, then Kind Atlas and option-surface cluster/card rows. Context-pack follows atlas for cross-kind work; navigation-metabolism follows a typed failure, command id, anti-pattern, or owner surface. --skill-find is DEBUG_TRACE with --debug."
---
<!-- registry: skill_registry.json -> navigation_seed | family: kernel -->

**Governing principles:**
- **Context economy (pri_049).** The minimum sufficient read graph is always a kernel flag, not a grep. If you can answer your question with one `python3 kernel.py --<flag>` call, do it before reading any file. A 2000-line Read or a 100-match Grep is a failure of the ladder, not of the substrate.
- **Document-read economy.** Full prose and tool-result reads are a command path with latency and context cost. For instruction adapters (`AGENTS.override.md`, `CODEX.md`, `AGENTS.md`), prompt shelves, tool-result files, and generated reports, use the compact owner packet, row/card route, status/process packet, `--compile <path>`, or a bounded line range first. Reopen the whole file only when the owner route cannot answer the specific question or the edit target itself requires full local context.
- **Coverage before invocation.** Existing affordances must be discoverable by coverage before they are invocable by name, but coverage is not permission. For broad development work, first contact must be a control packet (`--entry` or `--workitem-entrypoint`); exact-name lookup is a drilldown, not discovery. After entry, unknown-kind work must use Kind Atlas before context-pack, semantic ranking, or navigation-metabolism. When the question is whether the invariant holds system-wide, use `--coverage-enforcement-matrix` as the audit surface over Kind Atlas, route lifecycle, hook shadow coverage, and process-audit pressure.
- **Deep traversal guard.** `anti_pattern_deep_without_ladder` is a point-of-use routing failure, not a reason to read more files. Reopen the coverage or metabolism owner route, select the artifact kind and row, then open source only after a stable card or owner surface names it.
- **Entry adoption before completion.** A new capability, projection, evaluator, provider lane, cockpit affordance, WorkItem class, standard, or generated artifact is not operationally adopted until `--entry` or `--context-pack` routes a representative cold-start task to it, supplies the cheapest sufficient card/capsule/projection first, and exposes the stale/ambiguous/missing/unsafe/provider-boundary escalation route. Exact `--ids` lookup proves prior knowledge, not cold discoverability.
- **No-null-pass floor.** A pass that finds no source patch is not automatically done. Before yielding, either close an owner lane, update or retire a residual, improve the entry/projection mechanism that made the pass useful, or record a typed no-edit receipt with `stewardship_checked`, `next_best_lane_checked`, and a re-entry condition. `nothing_to_refine` is only valid after those checks.
- **Structural vs semantic is the first fork after entry.** Structural = "what is this file / where is this phase / what's in this folder" → hologram + frontier + working-set. Semantic = "what in the repo is about X / what subsystem handles Y / what did Will voice about Z" → selected paper-module slug + --navigate + selected docs-route + --shards.
- **Entry first, atlas second when substrate is unknown.** If you don't know whether the answer is in a paper module, a skill, doctrine, Python source, or raw seed, start with `--entry "<task>"`. If entry has not selected a stable kind, run `--kind-atlas --band flag`, then the emitted `--option-surface <kind> --band cluster_flag|flag|card` command. Use `--context-pack` only when the atlas/entry path proves the task needs a cross-kind packet. Use `--navigation-metabolism` only after a typed failed command, anti-pattern id, repair class, or owner surface is known.
- **Layer first, semantics later.** Do not turn the task into a bag of words and ask the substrate to understand it. Pick the next layer from the previous layer's typed output: control lane -> live-state packet -> artifact kind -> cluster contents page -> stable row card -> source evidence -> mutation owner. Semantic ranking is one evidence route after the layer is selected, not the agent's understanding engine.
- **Actionability before advisory debt.** When navigation metabolism marks a row `library_reference_only=true`, keep the row as evidence but do not chase it as the first repair until the live CLI route has been checked. Prefer actionable `top_repairs` rows and use the advisory row to verify the compatibility shim still points to the compressed route.
- **State adjectives route through facts.** Cross-kind state questions like "what is banned?", "what is stale?", or "what states can things be in?" should open the generated fact state-axis artifact. Use `--entry` first; the overview drilldown is `./repo-python kernel.py --facts --band cluster_flag`, with exact tag/facet drilldowns through `--facts --facts-tag <tag>` or `--facts --facts-facet <facet>`.
- **Claim-bearing traces route before trust.** If the operator pastes a prior agent trace, context packet, or closeout that says something was implemented, route the packet through `agent_session_diagnostics` or the owning option surface first; then verify the claim with stable ids, source paths, or owner checks before treating it as substrate truth.
- **Annex compression is a navigation rung, not a design authority.** For system-design, agent-entry, navigation, retrieval, runtime, or frontend questions where prior work may help, briefly scan the annex distillation layer or `annex_notes` route before inventing. Annex notes describe the external substrate; the local mapping is still a consume-time judgment under `pri_080`.
- **Document what exists.** Every flag cited here is verified via `python3 kernel.py --help` as of 2026-04-30. If a flag is not found, the skill is stale — refresh before citing.

## Purpose

This is the skill a cold agent loads first when the question is "where in this repo is X?" and the substrate is unknown. It is the **navigation seed** — the first navigable thing in the nav layer, named so by Will on 2026-04-20 (par_phase_05_4...source_11...004).

Without this skill, a cold agent defaults to grep/Read/Glob or guessed lexical lookup, reads hundreds of lines of unrelated code, and burns context window before narrowing. With this skill, the agent climbs a coverage ladder where each rung is a single CLI call that returns a bounded JSON packet naming the next-right substrate.

## Coverage-First Rule

For broad or unknown development work, a control packet selects the route before coverage surfaces are browsed:

```text
entry -> kind atlas -> option surface cluster/flag/card -> exact row/source/tool/debug trace -> context-pack or metabolism only when a typed row/failure asks for it
```

Allowed first-contact control surfaces are `--entry "<task>"` and `--workitem-entrypoint <phase>` for active WorkItem execution. `--kind-atlas` and `--option-surface <kind> --band cluster_flag|flag|card` are atlas projections: use them after a control packet selected browse, or immediately when the operator explicitly asks to browse the atlas. Do not put a prose complaint into `--navigation-metabolism` and expect the substrate to infer the layer; metabolism is a repair/audit surface after the failed command, anti-pattern id, repair class, or owner surface is typed. Use `--context-pack` after the atlas hop when the selected kind rows show that a cross-kind task-conditioned packet is actually needed. Use `--campaign --task "<query>"` when the request is cross-lane integration, hidden-substrate wiring, Type A dispatch selection, or campaign/phase freshness. Campaign authority dominates phase authority: if `campaign_write_guard.effective_write_authority=campaign`, any nested phase alignment is context only and cannot grant live phase writes. Use `--phase <phase> --task "<query>"` when the active phase primary wave and the current request may diverge inside a known phase; it emits a phase/task alignment packet instead of forcing the agent to narrate an exception. Use `--coverage-enforcement-matrix "<task>"` when auditing whether those surfaces cover every kind and whether process-audit behavior still violates the rule. `--skill-find` is DEBUG_TRACE only; scores, matched_on, token_overlap, and match_count require `--debug` after a stable skill row or explicit operator debug request.

Residual lane means a sanctioned, task-conditioned route inside the active phase that is not the phase's current primary wave. It is not an exception and not an override; it must carry `legal_when`, owner surface, copy-runnable commands when a task is known, write scope, and tests. If the packet returns `status=residual_lane`, primary-wave live writes are blocked by `write_guard` until the residual owner surface is followed. If it returns `status=mixed_lane`, follow the packet's execution order and run residual verification after primary-wave edits.

The ladder exists because the repo has three parallel navigation planes — structural (hologram, working-set, frontier), semantic (embedding substrate + route graph), and raw-seed (shard neighborhood). Each plane answers different questions. Picking the wrong plane wastes a cycle; picking none and reaching for grep wastes many.

## Deep-Traversal Guard

When `--entry`, `--context-pack`, `--coverage-enforcement-matrix`, or a process-audit row names `anti_pattern_deep_without_ladder`, stop before source/docs traversal and reopen the owner route:

```text
./repo-python kernel.py --coverage-enforcement-matrix "<task>" --context-budget 12000
./repo-python kernel.py --navigation-metabolism "<failed command or anti-pattern id>" --metabolism-profile quick --context-budget 12000
```

For the common process-audit fast path, keep the repair bounded to the owner card before opening broad rows:

```text
process_audit_fast_path.status=active_behavior_debt
process_audit_fast_path.owner_card_command=./repo-python kernel.py --option-surface skills --band card --ids navigation_seed,agent_session_diagnostics
```

Do not open the full matrix rows, source files, docs routes, or broad context before the owner card names the stable handle and repair boundary.

Then follow the typed row:

1. If the packet names a `kind_id`, open `./repo-python kernel.py --option-surface <kind_id> --band cluster_flag` and then the emitted card route.
2. If the packet names a repeated command family, open `./repo-python kernel.py --command-card "<query>"` or the owner quote before implementation reads.
3. If it names neither kind nor owner row, climb `./repo-python kernel.py --kind-atlas --band flag` and select the next emitted option surface.
4. Open source only after a stable card, owner surface, or exact path names it.

## Layered Navigation, Not Semantic Guessing

The navigation substrate is not an LLM that proves understanding because a query string got a plausible hit. Treat every command output as a typed packet with a role:

```text
control entry -> live state -> kind coverage -> cluster page -> stable row card -> evidence/source -> mutation owner
```

Use exact ids, paths, flags, and owner names emitted by the previous packet. If you only have prose, run the control entry packet first. If the packet names a kind, browse that kind's `cluster_flag` or `card` surface. If the packet names a row id, open that row. Only use `--navigate`, broad `--context-pack`, `--paper-module`, `--docs-route`, or `--skill-find --debug` after a layer has justified that drilldown.

### Atlas Hop Rule

When the task is "which layer/kind owns this?" the next move is not another sentence-shaped query. Run the atlas and move by emitted ids:

```text
./repo-python kernel.py --kind-atlas --band flag
./repo-python kernel.py --option-surface <kind_id> --band cluster_flag
./repo-python kernel.py --option-surface <kind_id> --band card --ids <row_id>
```

Use the `kind_id`, `option_surface_command`, `cluster_command`, and `card_command` fields directly. System Atlas is one Kind Atlas row (`kind_id=system_atlas`); open it through `--option-surface system_atlas --band cluster_flag` after the Kind Atlas row is selected. Do not replace Kind Atlas with context-pack/System Atlas just because the words "system" or "atlas" appear.

PageIndex is the external analogue, but not the ceiling. PageIndex proves that a generated tree plus reasoning beats flat similarity lookup for long documents; the local upgrade is a typed, multi-kind atlas over a living substrate. Kind Atlas rows carry artifact kind, support status, currentness, emitted drilldown commands, evidence/source fields, omission receipts, standards, and owner surfaces. That makes the path `entry -> kind -> cluster -> card -> source -> owner`, not `query -> plausible hit`. Treat PageIndex as prior art for structure-first traversal and as a boundary warning: vectorless tree search is still weaker than a governed typed atlas if it lacks currentness, mutation ownership, and process-audit feedback.

When commands feel slow or over-wide, classify the failed command before running a larger one:

- `--phase --full` too large: use `--phase`, `--phase --summary`, `--phase --warnings-only`, or `--phase <phase> --task "<query>"`.
- `--context-pack` returns generic system-self-comprehension rows for a specific task: step back to `--entry`, then browse the selected kind/cluster/card.
- `--skill-find` feels tempting: browse `skills.cluster_flag` or `skills.card --ids <skill_id>`; `--skill-find` is only a debug trace.
- `--navigate` returns plausible but broad semantic hits: constrain by `--embed-kinds` only after the kind is known, or use the option surface for that kind.
- `rg` or grep over a whole tree hits generated raw/hologram payloads, projection views, or standards indexes: rerun against the source/test paths named by the owner card, or use the generated owner's projection/card surface first. Treat an unowned broad-search scope as `route_or_stale_surface` pressure, not as permission to widen the search.
- Raw-seed or dissemination work tempts grep/wc/head/ls because the operator asked for aggressive search: use the raw-seed owner's aggressive surfaces (`--raw-seed-ideas`, `--raw-seed-query`, `--raw-seed-browse`, `--shards-packet`) before shell fallbacks. If those routes are missing or stale, capture the route gap instead of hiding it behind broad Bash.
- Full `Read` of adapter prose or tool-result files shows up in process bottlenecks: use `--agent-operating-packet`, `--entry`, `--context-pack`, `--command-card`, `--process-summary`, `--process-bottlenecks`, `--compile <path>`, or a targeted line range before loading the whole body.
- A command stays slow after narrowing: record the command and repair owner through `--navigation-metabolism`; do not compensate by dumping full outputs.

This skill is the opening half of a pair. `navigation_seed` opens the task by choosing the cheapest navigable surface first; [local_to_general_propagation](../doctrine/local_to_general_propagation.md) closes the task by asking what the local case taught the general navigation / learning / compression / routing system.

The outbound-vs-observed pair: this skill is **what the agent should do**. Its retrospective inbound twin is [agent_session_diagnostics](agent_session_diagnostics.md) — **what past agents actually did**, mined from out-of-repo Codex / Claude session storage. Its live inbound twin is [navigation_trace_binding](../../paper_modules/navigation_trace_binding.md): semantic kernel flags now append bounded decision events under `state/navigation_trace/` so a wake can replay the actual route path before repeating it. When the user asks "find the codex folder," "mine what the model did," or "improve navigation off the diagnostics we've set up," load `agent_session_diagnostics`; when the user asks why the current wake keeps revisiting the same semantic route, use `--navigation-trace-replay latest` and `--navigation-trace-convergence`.

## The ladder

Climb in this order when the repo substrate is unknown. Stop at the first rung that answers the question. If the request is plainly external host/OS/app support and does not need repo state, generated projections, phase context, or durable doctrine edits, use direct local tooling/web evidence and re-enter this ladder only if the task crosses back into repo substrate work.

```
Rung 1  python3 kernel.py --info                          Orient. One compact HUD. Always cheap.
Rung 2  python3 kernel.py --preflight                     Agent-start card: active phase, runtime posture, freshness, next safe command, do-not warnings.
Rung 2p python3 kernel.py --pulse                         Fuller live runtime state: phase, orchestration, hotspots, next-action.
Rung 2a python3 kernel.py --agent-wake-packet             Type A reentry packet: pulse + phase + view graph + projection coverage + work ledger.
Rung 2a.campaign python3 kernel.py --campaign --task "<query>"
                                                           Integration campaign packet above phase: active phase freshness, legal lanes, Work Ledger signal, annex pressure, and Type A dispatch packets.
Rung 2b python3 kernel.py --phase --summary               Bounded phase truth: active phase, wave identity, warning count, next posture.
Rung 2b.task python3 kernel.py --phase <phase> --task "<query>"
                                                           Phase/task arbitration: primary wave, legal residual lane, or mixed lane.
Rung 2c python3 kernel.py --command-card "<query>"        Typed command memory: use/avoid/next/cost for repeated movement commands.
Rung 2w python3 kernel.py --workitem-entrypoint <phase>    WorkItem control-plane packet when active work selection or ledger posture matters.
Rung 3  python3 kernel.py --kind-atlas --band flag         ATLAS_PROJECTION: coverage map of supported artifact kinds after entry or explicit browse.
Rung 3a python3 kernel.py --option-surface <kind> --band cluster_flag
                                                            ATLAS_PROJECTION: compressed contents page for a kind after entry; use before exact row/tool lookup.
Rung 3b python3 kernel.py --context-pack "<task>"          Task-conditioned mixed-band packet only after entry/atlas shows the task is cross-kind.
Rung 3s python3 kernel.py --facts --band cluster_flag      DRILLDOWN after entry/context selects state-axis territory: generated compressed state universe; exact adjectives use --facts-tag/--facts-facet.
Rung 3c python3 kernel.py --coverage-enforcement-matrix "<task>"
                                                            Per-kind audit of coverage availability, lifecycle status, hook coverage, and process-audit pressure; not a first-contact permission grant.
Rung 4  python3 kernel.py --paper-module <stable-slug>     DRILLDOWN: subsystem ontology after entry/context selects paper-module territory and a stable slug.
Rung 5  python3 kernel.py --navigate "<query>"             Semantic rank across embedded kinds in one call.
Rung 5e python3 kernel.py --navigation-efficiency "<query>" One-shot intent-first packet when the task is a vague navigation/process-efficiency complaint.
Rung 5t python3 kernel.py --navigation-trace-replay latest
                                                            Replay the live semantic decision path before repeating a route.
Rung 5a python3 kernel.py --annex-inspiration "<query>"    One-shot annex prior-pattern packet for local design inspiration.
Rung 5b python3 kernel.py --navigate "<query>" \
            --embed-kind annex_notes                       Semantic rank across annex notes when deeper annex shape is needed.
Rung 5c python3 kernel.py --annex-distillation <axis>      Compressed annex pattern rows by adoption axis.
Rung 5r ./repo-python annex_import.py route --problem "<query>"  Keyword route to shape-matched annexes.
Rung 5f ./repo-python tools/meta/observability/exogenous_nav_ladder_grader.py
                                                            Outside-oracle grade for docs-route / paper-module / navigate recursion.
Rung 5d python3 kernel.py --docs-route <stable-route>      DRILLDOWN/DEBUG: documentation route only after entry/context selects it; broad query is not first-contact control.
Rung 6  python3 kernel.py --shards --shards-source family \
            --shards-query "<topic>"                       Raw-seed voice. When the question is "what did Will voice".
Rung 7a python3 kernel.py --locate <token>                 Python symbol/file lookup (hologram).
Rung 7b python3 kernel.py --compile <path>                 High-fidelity file card (symbols.json).
Rung 7c python3 kernel.py --lens <target>                  Boundary / group / file-card browse.
Rung 8  python3 kernel.py --working-set [count]            Note-family continuity (obsidian). When task is "what was I doing".
```

Rungs 1-2 are orientation. Rung 3 is coverage over kinds and compressed contents. Rungs 4-6 are semantic and situation-specific drilldown. Rungs 7a/b/c are structural Python. Rung 8 is operator workflow.

## Fast Routing Table

Use the ladder above as the command source. The highest-frequency forks are: cold start -> `--info` / `--preflight` / `--pulse`; Type A wake -> `--agent-wake-packet`; active work selection -> `--workitem-entrypoint`; campaign authority -> `--campaign --task`; phase/task conflict -> `--phase <phase> --task`; unknown kind -> `--kind-atlas` then `--option-surface <kind> --band cluster_flag`; prompt-shelf metadata -> `--option-surface prompt_shelf_metadata --band cluster_flag`; state adjectives -> `--facts --band cluster_flag`; route-quality audit -> `--coverage-enforcement-matrix`; pasted agent trace or claim packet -> `agent_session_diagnostics` then stable-id/source verification; selected subsystem -> `--paper-module <stable-slug>`; semantic unknown -> `--navigate`; prior-art scan -> `--annex-inspiration`; raw voice -> `--shards`; structural source -> `--locate` / `--compile` / `--lens`; comprehension claim -> `--agent-entrypoint-audit`.

## When NOT to use this skill

- **You already know the exact file path.** Use `Read` directly for small or edit-local files. For large prose, instruction adapters, generated reports, or tool-result bodies, prefer `--compile`, owner cards/status packets, or a bounded line range before a full read.
- **The task is a known workflow with its own skill.** If the situation matches `bootstrap` (session start), `observe`, `plan`, `apply`, `dispatch_yield`, etc., load that skill — not this one.
- **You need continuity, not navigation.** "What was I doing" is `bootstrap` + `--working-set`, not navigation_seed.
- **You're editing code in a known file.** Just edit. Navigation is for finding, not executing.

## Workflow

### When the substrate is unknown (the default cold-boot path)

1. Run `python3 kernel.py --info`, then the cheapest live packet that answers the task (`--preflight`, `--pulse`, `--entry`, or `--workitem-entrypoint`).
2. If the task is broad and the kind is not stable, run `--kind-atlas --band flag`, then the emitted `--option-surface <kind> --band cluster_flag|card`.
3. Structural questions use `--locate`, `--compile`, or `--lens`; semantic questions use selected paper modules first, then `--navigate`; raw-voice questions use `--shards`.
4. Use annex compression before inventing local patterns for design, navigation, runtime, retrieval, frontend, or agent-entry work.
5. Only after the ladder fails should you reach for `Grep`, `Glob`, or full-file `Read`.
6. For route truth tests, use the exogenous grader and filesystem evidence. For route-miss cohorts, repair the owning route, not the diagnostics lane, and use exact tokens for one-word aliases that would otherwise steal longer phrases.
7. For entry-surface audit debt, patch the named owner surface, refresh generated projections, and capture a residual instead of forcing through an actively claimed path.

### When the question is definitely semantic

Use `python3 kernel.py --navigate "<query>" --embed-top-k 10`, inspect `routed_hits` and `seed_hits`, then narrow with `--embed-kinds` or per-facet `--semantic-search` only after the packet names the useful kind.

### When the question is about Will's voice

Skip to rung 6: `python3 kernel.py --shards --shards-source family --shards-query "<topic>"`. The first compression unit is usually `idea_group_id`; pair with `raw_seed_contextualize` when the shard set needs paragraph expansion.

## Anti-patterns

- **Grep before kernel.** Raw `rg/find/sed/awk/head/tail`, including wrapped Bash forms, is fallthrough when used for discovery.
- **Lexical skill lookup.** `--skill-find "<phrase>"` is debug trace only; use `--entry`, atlas, and `skills.cluster_flag|card` first.
- **Full-file read before compile.** Use `--compile <path>` or row cards before opening large source files.
- **Full adapter/prose read as orientation.** Do not reread all of `AGENTS.override.md`, `CODEX.md`, `AGENTS.md`, prompt-shelf runs, or tool-result files when a compact owner packet, command card, section, or line range would answer the question.
- **Deep traversal without ladder.** Do not jump from `--entry` or `--context-pack` straight into broad source/docs reads, raw implementation spelunking, or multi-hop drilldowns. If the control packet did not name a stable owner row, climb `--kind-atlas` -> `--option-surface <kind> --band cluster_flag|card`; if it did name a repeated command family, open `--command-card "<query>"` or the owner quote before reading implementation.
- **Wrong plane.** Phase questions go to `--pulse` / `--phase`; subsystem questions go through coverage and paper-module; raw voice goes to shards; structural paths go to locate/compile/lens.
- **Skipping compact packets.** Do not stop at `--info`, skip `--preflight` on ambiguous wake, repeat the wake ladder by hand instead of `--agent-wake-packet`, dump `--phase --full` when summary/warnings suffice, or reread command code instead of `--command-card`.
- **Campaign/phase confusion.** Campaign authority dominates nested phase context. Legal residual lanes are not exceptions; use `--phase <phase> --task "<query>"` and follow its write guard.
- **Control-surface-only comprehension.** Markdown adapters without Python substrate or agent-entry audit evidence prove only partial comprehension.
- **Annex misuse.** Do a compressed annex scan when prior work likely exists, but translate locally; annex notes are not edit instructions.
- **Self-grading navigation.** Use the exogenous grader or filesystem evidence when judging route truth.
- **Loading every nav skill.** This meta-ladder is enough until a rung surfaces a specific companion skill.

## Propagation reflex

`navigation_seed` is the mandatory opening companion to [local_to_general_propagation](../doctrine/local_to_general_propagation.md). If the local use surfaced a rung that was missing from the ladder, an anti-pattern not listed, or a composition (`navigation_seed` + X) that was emergent, route the closeout through that skill before yielding and either refine this file or explicitly record `nothing_to_refine`. New agent-start, cold-boot, preflight, or next-safe-command surfaces are not fully shipped until this ladder and the compact entry pointer know about them; `--preflight` is the reference case. New capability surfaces are not fully adopted until the entry-adoption contract in `std_agent_entry_surface.json` has a proof: representative `--entry` or `--context-pack` route, cheapest sufficient compression band, failure/escalation route, dogfood usage, and WorkItem binding. If the new or changed surface affects first-contact behavior or recurring operator questions, it also needs an explicit `actor_delivery` decision and `--actor-receipt` proof, or a recorded drilldown/private/debug/deferred boundary. Navigation-seed is load-bearing for every cold agent cycle; drift here compounds across every session that loads it.

When the *purpose* of the turn is to improve wiring itself — the user asks to densify interconnectedness, or a rung pass surfaces isolated paper modules / broken back-edges / drifted routes — escalate to [nav_driven_wiring_repair](../doctrine/nav_driven_wiring_repair.md). That skill reuses this ladder as a drift-sensor array and closes gaps with prose-justified frontmatter edits measured on the same tool. The three-skill protocol is: `navigation_seed` opens, `nav_driven_wiring_repair` closes wiring gaps surfaced by the open, `local_to_general_propagation` closes the turn.
