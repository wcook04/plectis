# Memory Injection Tiers

**Projection class:** subsystem
**Subsystem slug:** `memory_injection_tiers`
**Authored:** 2026-04-27
**Status:** in_progress
**Depends on:** `claude_memory_discipline`, `claude_memory_routing_tables`, `unified_navigation_layer`
**Governing principles:** `pri_080` (adapt not adopt — external substrate must be translated), `pri_088` (reread substrate at each compression level), `pri_111` (paper modules preempt re-derivation), `pri_003` (projection not design)
**Governing concepts:** `con_001` (holographic self-documentation), `con_028` (projection substrate and drift), `con_021` (situation-routed instruction surfaces)
**Governing mechanisms:** `mech_019`
**Primary subdomain:** memory_substrate
**Secondary subdomains:** agent_context, controller_continuity
Search aliases: memory tiers, three-tier memory injection, passive memory, reactive memory, active memory, prepareStep injection, per-step memory, rolling tool-call window, proactive substrate injection

## TLDR (compressed view)

ai_workflow currently injects cross-session memory through a **passive tier** only — paper modules, skills, raw-seed substrate, and the `agent_bootstrap.json` live-context block all assemble at session start (or at each cold agent's bootstrap call) into the system prompt. This module names the **two missing tiers** by adapting aperant's three-tier model: a **reactive tier** where an agent calls a `--paper-module` / `--skill-find` / `--locate` / `mcp-search.smart_search`-equivalent tool to fetch relevant substrate mid-session, and an **active tier** where the runtime watches the rolling window of recent tool calls and proactively injects relevant context per step. Today our reactive surfaces exist but aren't *named* as the reactive tier; the active per-step tier doesn't exist at all. Naming the three tiers makes the gap addressable: the active tier would track the last N tool calls, score recently-touched paths against the paper-module / skill / raw-seed substrate, and surface a relevant snippet without the agent having to ask. This is doctrine first, code second — the paper module names the contract; implementation in `metabolismd` or a new step-injection layer is future work tracked through normal apply lanes. The active tier's load-bearing invariant is **advisory, never authoritative**: the agent can ignore an injected snippet without consequence; making active injection authoritative breaks pri_088.

## Intent

Cold agents currently re-discover the same paper modules, skills, and doctrine concerns turn after turn within a single session. The passive-tier injection at bootstrap is rich (CLAUDE.md, AGENTS.md, agent_bootstrap.json's live block) but freezes at session start. Once a session is running, agents pull substrate explicitly through reactive surfaces (`--paper-module`, `--skill-find`, `--locate`, claude-mem search). What's missing is the proactive layer: a runtime that watches what the agent is *doing* — which paths it touches, which tool errors it retries, which substrate kinds it has already consumed — and surfaces relevant substrate before the agent has to ask.

Aperant's `Memory.md` design document (pre-implementation V5, 2026-02-22) names this gap precisely. It splits memory injection into three moments:

1. **Passive:** at session start, via system prompt assembly.
2. **Reactive:** mid-session, via a `search_memory` tool the agent calls when it needs context.
3. **Active:** per-step, via a `prepareStep` callback that watches the last 20 tool calls and injects context based on what's been touched.

The active tier's `StepMemoryState` + `StepInjectionDecider` shape (rolling tool-call window + injection decision) is the highest-value addition because it removes the asymmetry where the agent must remember to ask. In a long debugging session that touches `system/lib/semantic_routing.py` ten times, the agent should be told once: "the paper module for this is `semantic_routing_plane.md`; have you opened it?"

## Shape

```text
Tier 1 — PASSIVE (exists, fully named)
  session start → bootstrap → system prompt assembled from:
    - CLAUDE.md / AGENTS.md / CODEX.md
    - codex/doctrine/agent_bootstrap.json (live-context block)
    - paper-module index summary (deliverables_preview, code_loci_preview)
    - skill registry summary (one-liners + triggers)
  fires:    once per cold session
  authority: passive-tier substrate is canonical at bootstrap moment
  builder:  tools/meta/factory/build_agent_bootstrap_projection.py

Tier 2 — REACTIVE (exists, this module names it as a tier)
  agent → tool call → substrate fetch
    - kernel.py --paper-module <slug>
    - kernel.py --skill-find "<intent>"
    - kernel.py --locate <token>
    - kernel.py --shards / --raw-seed-paragraph <id>
    - mcp-search.smart_search / get_observations
    - claude-mem search / timeline
  fires:    on agent demand
  authority: substrate is canonical; agent sets the query
  invariant: reactive surfaces never invent content, they only project

Tier 3 — ACTIVE (NOT YET BUILT — this module is the contract)
  runtime watches rolling N-call window → step decider →
    proactive injection of substrate snippet into next step
  fires:    every K tool calls (or on signal: error retry, repeated path access)
  authority: substrate selection is heuristic; INJECTION IS ADVISORY
  invariant: agent can ignore injection without consequence
  proposed home: metabolismd or new system/lib/agent_step_injection/
```

## Ontology / Types & Invariants

| Name | Tier | Trigger | Authority | Status |
|---|---|---|---|---|
| Passive bootstrap injection | 1 | Session start | Canonical — substrate at bootstrap is the trusted floor | shipped |
| Reactive tool fetch | 2 | Agent calls retrieval verb | Substrate-authoritative; agent sets the query | shipped |
| Active per-step injection | 3 | Runtime fires after K tool calls or on signal | Advisory — agent can ignore; injection is hint, not edict | not yet built |
| Rolling tool-call window | 3 | Continuous (last N calls) | State holder; not visible to agent except via injection | not yet built |
| Step injection decider | 3 | After K tool calls | Selects which substrate kind (paper module, skill, raw seed shard) is most relevant | not yet built |
| Active-tier injection result | 3 | Output of decider | Surfaces a single snippet (≤200 tokens) referencing the substrate by slug + path | not yet built |

### Named invariants

- **Active tier is advisory, never authoritative.** The agent can ignore an injected snippet without consequence; the injection is a hint based on heuristic scoring, not the truth-source. Making active injection authoritative breaks pri_088 (substrate is reread, not pre-compressed).
- **Tier order is bootstrap → demand → proactive.** Active injection should never preempt reactive demand: if the agent already asked, the active layer skips that turn.
- **The rolling window is a state structure, not a log.** Bounded (N ≈ 20) and forgets old calls; it is not the work_ledger and does not persist beyond the live session.
- **Substrate authority is preserved across tiers.** All three tiers route through the same substrate (paper modules, skills, raw seed, doctrine nodes); none invent new content. The active tier is a *router*, not a writer.
- **Active tier never injects user-identity content.** The user-identity carve-out from `claude_memory_discipline.md` applies — no `~/.claude/projects/<slug>/memory/` content reaches active injection.
- **Active tier respects the assimilation table.** If a substrate kind is governed by a routing table (per `claude_memory_routing_tables.md`), active injection points at it; it does not synthesize a competing surface.

## Code loci

| Concern | Path | Tier |
|---|---|---|
| Passive bootstrap projection builder | `tools/meta/factory/build_agent_bootstrap_projection.py` | 1 |
| Passive bootstrap consumer | `codex/doctrine/agent_bootstrap.json` | 1 |
| Reactive substrate fetch (paper module / skill / shard / locate) | `system/lib/kernel/commands/embed.py` | 2 |
| Reactive raw-seed apply / append surface | `system/lib/kernel/commands/apply.py` | 2 |
| Active step decider (proposed home) | `tools/meta/control/` — NOT YET BUILT; concrete module name reserved in §Gap | 3 |
| Active rolling window (proposed home) | `tools/meta/control/` — NOT YET BUILT; could be a `metabolismd` blackboard field or a session-scoped sidecar JSON, see §Gap | 3 |

## Current state

**Shipped:**

- Tier 1 fully shipped — passive substrate injection at every cold bootstrap via the agent_bootstrap projection.
- Tier 2 fully shipped, now named as a tier — every retrieval verb in `kernel.py` is a reactive injection surface; same with mcp-search.

**NOT YET BUILT:**

- Tier 3 has no implementation. The rolling tool-call window does not exist as a state structure. No injection decider runs. The agent has no proactive surface short of explicitly asking.

## Deliverables (what this subsystem lets a cold agent DO)

- **Name the active-tier gap** when scoping memory work; previously it was implicit and got lost in conversations about "memory" generically.
- **Route a passive vs reactive vs active concern** into the right tier instead of conflating them — useful when designing new injection surfaces.
- **Reference the rolling-window + step-decider shape** from aperant when proposing an active-tier prototype, with the load-bearing invariants pre-named.
- **Diagnose context-pressure causes** — if a long session keeps re-fetching the same paper module reactively, that's evidence the active tier would help.

## Gap (what Will is signaling)

The active tier is the highest-leverage missing primitive in our memory substrate. Concretely, building it would mean:

1. **Rolling window state.** A bounded N-deep deque (N ≈ 20) of `{path, verb, result_hash, ts}` entries held in memory or in a metabolismd blackboard field. Bounded by call count, not time.

2. **Step injection decider.** Triggered after every K tool calls (or on a named signal: error retry, repeated path access ≥3 times in window, edit-without-prior-read on a known-substrate path). Scores recent paths against:
   - paper-module `code_loci_preview` paths (best match)
   - skill `focus_paths`
   - raw-seed shard targets
   - doctrine concept / mechanism `code_loci`
   Returns at most one substrate reference per fire — `{kind: paper_module|skill|raw_seed_shard|doctrine_node, slug: "...", reason: "<why this is relevant>"}`.

3. **Injection surface.** Three candidate shapes:
   - **Hook injection** — runtime_hook.py emits a system-message addendum (cleanest; integrates with our existing hook ladder; see `runtime_hook_ladder.md` once authored)
   - **Tool-result wrapper** — wrap the next tool's result with a small `<active_injection>` block (most reliable but couples to tool-call format)
   - **Proactive system-prompt addendum** — append to the next system message (least reliable; many hosts compress system prompts)
   The hook injection is the recommended route because it composes with `runtime_hook_ladder.md`'s SessionStart/PostToolUse pattern.

4. **Decider configuration.** Per-agent-type overrides — a paper-module authoring session probably wants more aggressive injection of paper modules; a raw-seed metabolism session wants raw-seed shard injection.

The active tier is *advisory*: the agent should be able to ignore an injection without consequence. This is the load-bearing invariant — making active injection authoritative breaks pri_088 (substrate is reread, not pre-compressed).

## What a cold agent should NOT re-derive

- Don't re-argue whether memory should live in `~/.claude/projects/<slug>/memory/` — that's settled by `claude_memory_discipline.md`. This module is about how plane substrate gets injected back into the agent's working context, not about where the substrate lives.
- Don't conflate "active tier" with "agent self-memory" — active is the runtime's heuristic injection from the durable plane, not a per-agent mutable store.
- Don't import aperant's `prepareStep` / `StepMemoryState` runtime — adapt the shape (per pri_080) into a metabolismd blackboard field or a new `system/lib/agent_step_injection/` module.
- Don't invent a fourth tier — bootstrap, demand, proactive is the closed set. Anything else (sub-agent-context-passing, dispatch payload assembly) is a different subsystem.

## Refresh contract

Refresh this module when any of these happen:

- A Tier-3 active-injection prototype lands anywhere in the repo (rolling window, step decider, or injection surface) — the `Code loci` row for the proposed home transitions from `NOT YET BUILT` to a concrete path, and `Current state` adds a `Shipped: Tier 3 partial` row naming what was implemented.
- A new reactive surface is added to `kernel.py` or to an MCP server that exposes substrate retrieval — list it in the Tier-2 inventory.
- The user-identity carve-out in `claude_memory_discipline.md` changes scope — the active-tier invariant referencing it must be updated in lockstep.
- The advisory-not-authoritative invariant for Tier 3 is challenged or refined — the `Named invariants` row and the `What a cold agent should NOT re-derive` section must be updated together.
- `memory_injection_tiers` is cited by a new skill or doctrine artifact — add the back-reference under `Depends on` reciprocity if the citation is structural.
- A new aperant or claude-mem distillation pattern lands that extends the three-tier model (e.g. a fourth phase or a sub-tier within active) — capture the new shape and re-derive the closed set claim.

### Pattern provenance

Adapted from `annexes/aperant/distillation.json#p002` "Three-Tier Memory Injection Model" via pri_080 (adapt, not adopt). The aperant repo (`apps/desktop/src/main/ai/memory/injection/step-memory-state.ts` + `apps/desktop/src/main/ai/session/runner.ts` + the `Memory.md` V5 design doc) is the implementation reference; the three-tier framing is the transferable shape; this paper module is the doctrine that translates the framing into our idiom and identifies the local active-tier gap.
