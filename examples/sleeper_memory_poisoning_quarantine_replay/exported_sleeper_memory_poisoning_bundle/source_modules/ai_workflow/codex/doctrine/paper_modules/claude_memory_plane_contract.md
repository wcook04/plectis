# Claude Memory Plane Contract

Projection class: subsystem
Authored: 2026-04-25
Search aliases: memory plane contract, plane is memory, five invariants, user identity carve-out, shadow doctrine, memory invariants, par anchors, bidirectional edges
Depends on: agent_entry_surfaces, raw_seed_substrate, agent_seed_substrate
Governing principles: pri_088 (reread substrate at each compression level), pri_080 (adapt, not adopt), pri_016 (extract, never replace with compression), pri_047 (situation-routed, not predetermined), pri_111 (paper modules preempt re-derivation)
Governing concepts: con_001 (holographic self-documentation), con_018 (documentation authority hierarchy), con_021 (situation-routed instruction surfaces)
Primary subdomain: memory_substrate

---

## TLDR (compressed view)

This module is the substrate-level contract for why Claude's `~/.claude/projects/<slug>/memory/` is a **vestigial notebook** in this repo: the structured plane (skills, paper modules, standards, doctrine nodes, annex notes, raw seed, agent seed) IS Claude's memory by design, and a Claude-private store creates **shadow doctrine** — content that looks like memory but never gates through apply lanes, never anchors to operator voice, never gets read by Codex or the world-model server. Five plane invariants Claude's private memory breaks: `par_*` anchors, bidirectional edges, controlled routing vocabulary, cross-host visibility, apply-lane gating. One narrow carve-out remains valid: user identity, hardware, contact (~3 files). Routing tables (where each kind of would-be memory lands) live in [claude_memory_routing_tables](claude_memory_routing_tables.md); the assimilation trigger protocol (the "assimilate this" 8-step flow) lives in [claude_assimilation_trigger_protocol](claude_assimilation_trigger_protocol.md).

## Intent

Claude Code ships with an `# auto memory` block in its system prompt that treats `~/.claude/projects/<slug>/memory/` as a first-class durable store with three types — feedback, project, reference. That block is generic across all Claude Code projects and assumes the project has no other persistent memory layer. **In ai_workflow that assumption is wrong.** This repo runs on a structured substrate plane (doctrine + paper modules + skills + standards + annex notes + raw seed + agent seed) that the entire Type A / Type B / human-operator stack reads from. A Claude-private notebook that predates this plane creates shadow doctrine that silently accumulates duplicates of what the plane already knows.

This module names the *contract*: which invariants the plane enforces that private memory breaks, what the narrow carve-out is, and the shape of the substrate. It is the substrate-foundation child of the original `claude_memory_discipline` index; routing tables and the assimilation-trigger protocol are separate children to keep this contract focused on the invariants.

## Shape

```
~/.claude/projects/<slug>/memory/        ← carve-out only: user / hardware / contact (~3 files target)
  MEMORY.md                              ← index file (one line per memory pointer)
  user_*.md                              ← Will's role, identity, machine, contact
  feedback_*.md                          ← FORBIDDEN (route to skill / paper module / standard)
  project_*.md                           ← FORBIDDEN (route to live-context block / paper module)
  reference_*.md                         ← FORBIDDEN (route to docs-route alias / paper module)

The plane (where everything else lives):
  obsidian/<phase>/raw_seed.md           ← operator voice (Will articulating)
  obsidian/<phase>/agent_seed.md         ← agent voice (Claude / Codex authored)
  codex/doctrine/skills/<family>/*.md    ← named moves, protocols, operations
  codex/doctrine/paper_modules/*.md      ← subsystem ontologies
  codex/standards/*.json                 ← schemas, rules, validators
  codex/doctrine/{concepts,mechanisms}/  ← architectural nodes (apply-lane only)
  obsidian/.../raw_seed/raw_seed_principles.json ← principle rows (apply-lane only)
  annexes/<repo>/annex_notes.json        ← external pattern notes
  codex/doctrine/agent_bootstrap.json    ← live runtime state config
```

## Ontology / Types & Invariants

### The five plane invariants Claude's private memory breaks

| Invariant | What the plane has | What private memory lacks |
|---|---|---|
| **par_* anchors** | Every durable doctrine claim anchors to a raw-seed paragraph ID | Memory is orphan content with no path back to operator voice |
| **Bidirectional edges** | Concepts/mechanisms/principles/skills link through the doctrine graph (apply-lane enforced) | Memory entries have no edges; cannot reach or be reached from sibling artifacts |
| **Controlled routing vocabulary** | `annex_routing_vocabulary.json`, situation routes, skill families, paper-module slugs | Memory is invisible to every routing surface (`kernel.py --docs-route`, `--frontier`, `annex_import.py route`) |
| **Cross-host visibility** | Codex, world-model server, station frontend, hologram projector, bridge workers all read plane artifacts | Memory is one-Claude-one-host; `~/.claude/projects/.../memory/` is local |
| **Apply-lane gating** | Doctrine mutations pass through `raw_seed_apply_loop.py`: dry-run, plan review, bidirectional-edge validation, lifecycle-state accumulation | Memory writes are ungated; any Claude turn drops a shadow claim that never validates against the graph |

Recursively this is `codex/standards/annex/std_annex_notes.json` §`interpretation_discipline` applied to Claude's own learnings. Same four governing principles: `pri_088` (reread substrate at each compression level), `pri_080` (adapt, not adopt), `pri_016` (extract, never replace with compression), `pri_047` (situation-routed, not predetermined). A Claude-private compression blocks every future situated reading in exactly the way a pre-baked annex note does.

### The narrow carve-out — what stays in memory/

**User identity, hardware, contact.** Will's role, his machine, `williamwkcook@gmail.com`. No plane home; cross-project persistence; not about the repo at all. Target cardinality: ~3 files.

### Reading memory

Read `memory/` only for the user / hardware / contact carve-out. Every other query routes to the plane — `kernel.py --docs-route <route>`, `kernel.py --paper-module <subsystem>`, `annex_import.py route --problem "..."`, `grep` over `codex/`, and the machine paper-module surfaces under `codex/doctrine/paper_modules/`. When a memory entry and a plane artifact both carry the same content, trust the plane and flag the memory entry for migration. Never mix memory content into a doctrine-query answer — it's shadow doctrine that hasn't been gated.

## Code loci

| Concern | Paths |
|---|---|
| Vestigial memory dir (carve-out only) | `~/.claude/projects/<slug>/memory/`, `~/.claude/projects/<slug>/memory/MEMORY.md` |
| Raw seed substrate (operator voice, family-09) | `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/` |
| Agent seed substrate (AI voice, family-09) | `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/agent_seed/` |
| Apply-lane-only principle rows | `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json` |
| Plane artifact roots | `codex/doctrine/`, `codex/standards/`, `annexes/` |

## Current state

**Shipped (2026-04-25):**

- The five-invariant contract is canonical doctrine in this paper module; both sibling children ([claude_memory_routing_tables](claude_memory_routing_tables.md), [claude_assimilation_trigger_protocol](claude_assimilation_trigger_protocol.md)) inject this TLDR via Depends on.
- The carve-out is named: user identity / hardware / contact, target cardinality ~3 files.
- Plane artifacts (raw_seed, agent_seed, skills, paper modules, standards, doctrine nodes, annex notes) are all live and validated by the build/check loop.

**In-progress / drift:**

- The existing `~/.claude/projects/<slug>/memory/` directory carries legacy entries that predate this protocol (cardinality is operator-machine-local and not tracked in repo facts); the discipline target is the user-identity carve-out (~3 files). Migration is natural-touch — when Claude touches an adjacent plane artifact, check whether a memory entry duplicates it and migrate via the right authoring skill. Do **not** run a bulk migration pass.

**Not yet enforced:**

- No automated audit checks `~/.claude/projects/<slug>/memory/` for non-carve-out files. The discipline is operator-conscience-enforced today; a hook-level audit is candidate work.

## Deliverables (what this subsystem lets a cold agent DO)

- **Decide whether content belongs in memory/ or the plane** by checking the user-identity carve-out first; everything else routes to the plane via the routing tables in [claude_memory_routing_tables](claude_memory_routing_tables.md).
- **Enumerate the five invariants Claude's private memory breaks** (par_* anchors / bidirectional edges / controlled routing vocabulary / cross-host visibility / apply-lane gating) so the plane-first reflex is explicit, not hand-waved.
- **Read memory only for the carve-out** via direct `Read` of `~/.claude/projects/<slug>/memory/user_*.md`; route every other query to the plane via `./repo-python kernel.py --docs-route <route>` / `--paper-module <subsystem>` / `--skill-find "..."` / `annex_import.py route --problem "..."`.

## Gap (what Will is signaling)

Will's signal anchors at the assimilation-trigger phenomenon: he says *"assimilate this into our knowledge system"* and the right reflex is plane-first routing, not memory-writing. The candidate paragraph that ratifies this contract lives in `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/` under the family-09 raw seed; the pre-distillation gesture is *"the plane IS Claude's memory; the memory directory predates this design."* The voice-discipline subtlety (writer-conditional preservation rule for raw_seed intake) is preserved in the sibling [claude_assimilation_trigger_protocol](claude_assimilation_trigger_protocol.md), anchored at par_phase_09_raw_seed__assimilation_trigger_deepseek_v4_abstract_pattern_mapping_002.

The unresolved direction: should the `~/.claude/projects/<slug>/memory/` directory itself be deprecated entirely once the carve-out lands? Will has not voiced this — the current posture is "natural-touch migration, converge on the carve-out across sessions." Flagging, not resolving.

## What a cold agent should NOT re-derive

- The five invariants are canonical. Do NOT re-derive a different list from first principles; cite this table.
- The carve-out is exactly user identity / hardware / contact (~3 files). Do NOT extend it to "session-state", "feedback", "project notes", or "reference" content; those route to the plane via routing tables.
- The plane IS Claude's memory by design — this is not a temporary state. Do NOT propose "let's make memory the durable store and the plane the projection." The substrate plane is the authority; memory is the vestigial notebook.
- Migration is natural-touch, not bulk. Do NOT propose a one-shot script that walks all ~40 memory entries and routes them. Each entry's correct plane home depends on its content shape; only the live authoring skill knows how to translate.
- Apply-lane gating is real. Do NOT hand-edit `con_*.json`, `mech_*.json`, or `raw_seed_principles.json` rows to "remember" something — those mutate only through `raw_seed_apply_loop.py`.

## Refresh contract

Refresh this module when:

- The user-identity carve-out grows beyond user / hardware / contact (it should not — that would mean the plane is missing a routing lane).
- A new plane invariant is added that shadow doctrine breaks (today there are five; if a sixth lands, the table grows).
- The `~/.claude/projects/<slug>/memory/` directory is itself deprecated in favor of a plane-only design (would invalidate the carve-out and shift this module to a deprecation notice).
- The plane shape changes substantively (e.g., a new top-level `codex/doctrine/<family>/` lands that should appear in the substrate diagram).

Stale signals:

- A `Code loci` path 404s.
- The carve-out drifts (memory dir grows past ~3 files target without explicit operator decision).
- A sibling child module ([claude_memory_routing_tables](claude_memory_routing_tables.md), [claude_assimilation_trigger_protocol](claude_assimilation_trigger_protocol.md)) renames or restructures.
