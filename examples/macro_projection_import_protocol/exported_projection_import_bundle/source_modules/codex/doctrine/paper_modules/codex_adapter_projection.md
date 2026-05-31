# Codex Adapter Projection

Projection class: subsystem
Authored: 2026-04-25
Governing principles: pri_049 (minimum sufficient read graph), pri_056 (projection ladder), pri_111 (paper modules preempt re-derivation), pri_115 (activation-grade principles)
Governing concepts: con_001 (holographic self-documentation), con_021 (situation-routed instruction surfaces), con_024 (holographic world model and projection graph)
Governing mechanisms: mech_031 (Codex-Claude activation gradient entry surfaces)
Primary subdomain: control_layer_projection
Depends on: codex_agent_bootstrap_surface_schema
Search aliases: codex adapter, CODEX.md, codex adapter live, AGENTS.override.md, instruction discovery, codex compact discovery seed, codex bootstrap projection, codex entry surface

---

## TLDR (compressed view)

The Codex adapter projection covers two coordinated entry surfaces — `AGENTS.override.md` (compact discovery seed Codex CLI checks before any deeper read) and `CODEX.md` (full Codex actor adapter over the shared hub). `AGENTS.override.md` is intentionally tiny: a hand-authored protocol section above an `instruction_discovery_live` managed region that the bootstrap builder fills with file sizes, active-phase facts, bootstrap sequence, and routing pointers under a fixed byte budget. `CODEX.md` mirrors the Claude adapter shape (preamble + `codex_adapter_live` + `paper_module_index` + Codex-specific deltas) but routes Codex deltas instead of Claude ones: the three named role TOMLs (`.codex/roles/{explorer,monitor,worker}.toml`), the runtime control plane (`docs/codex_control_surface.md`, `codex_runtime_control_plane`), and the manual work-ledger lifecycle the worker role follows until Codex host hooks exist. The schema hinge (actor contexts, MRS ids, projection-vs-delta) lives in `codex_agent_bootstrap_surface_schema`; this module owns the Codex-side shape only — including the unique two-surface structure that makes Codex's discovery-budget-safe entry possible without bloating the deep hub.

## Intent

Codex has a different first-read surface than Claude: the Codex CLI uses a project-doc discovery order that checks `AGENTS.override.md` before falling through to `AGENTS.md`. Putting the full hub at the top of that order would blow the discovery byte budget; putting nothing there would force every Codex session to re-derive the activation gradient. The compact `AGENTS.override.md` seed solves that asymmetry: it carries a small hand-authored static protocol above a builder-owned `instruction_discovery_live` region with live byte counts, active phase facts, and the same five-step bootstrap sequence Claude reads. `CODEX.md` then carries the full Codex adapter — analogous in structure to `CLAUDE.md` but with Codex-specific deltas (role TOMLs, runtime control plane, manual work-ledger). This module isolates Codex's two-surface adapter shape so the schema hinge does not have to special-case it, and so adding a new Codex-only delta has one canonical home.

## Shape

```
AGENTS.override.md (compact Codex discovery seed)
├── static protocol (hand-authored, kept below seed budget)
└── <!-- BEGIN instruction_discovery_live -->         ← builder-owned
    ├── file size facts (AGENTS.override.md, AGENTS.md, CODEX.md, CLAUDE.md)
    ├── active phase summary
    ├── bootstrap sequence (5 compact steps)
    └── routing pointers (kernel.py --info / --pulse / --docs-route)

CODEX.md
├── preamble (hand-authored)
│   ├── mandatory read order
│   ├── Prime Directives Rosetta Stone table (PD1, PD2, PD2c, PD3)
│   └── shared doctrine stack
├── <!-- BEGIN codex_adapter_live -->                 ← builder-owned
│   ├── active phase, factory stage, orchestration state
│   ├── actor context — codex (MRS id, runtime surface, entry commands)
│   ├── bootstrap sequence
│   ├── Type A convergence
│   └── shared route
├── <!-- END codex_adapter_live -->
├── <!-- BEGIN paper_module_index -->                 ← builder-owned
└── Codex-specific deltas (hand-authored)
    ├── runtime control plane (docs/codex_control_surface.md)
    ├── role TOMLs (.codex/roles/{explorer,monitor,worker}.toml)
    ├── manual work-ledger lifecycle (worker role)
    └── codex follow-on register (.codex/follow_on/README.md)
```

The two surfaces are written by the same builder run: `system/lib/agent_bootstrap_projection.py::render_adapter_markdown` writes the `codex_adapter_live` and `paper_module_index` regions in `CODEX.md`; `render_instruction_discovery_markdown` writes the `instruction_discovery_live` region in `AGENTS.override.md`. Both share the same `agent_bootstrap.json` source plus runtime artifacts.

## Ontology / Types & Invariants

| Type | Kind | One-line purpose | Symbol / file |
|---|---|---|---|
| `CodexAdapterMarkdown` | actor adapter surface | Codex's actor-scoped delta over the shared hub. | `CODEX.md` |
| `CodexCompactDiscoverySeed` | discovery surface | Tiny first-read seed Codex CLI checks before AGENTS.md. | `AGENTS.override.md` |
| `CodexAdapterLiveBlock` | builder-owned region | Live snapshot in CODEX.md: phase, actor context, bootstrap sequence. | `CODEX.md::codex_adapter_live` |
| `InstructionDiscoveryLiveBlock` | builder-owned region | Live byte counts + active phase + bootstrap routing in seed. | `AGENTS.override.md::instruction_discovery_live` |
| `CodexPaperModuleIndexBlock` | builder-owned region | Compact paper-module discoverability slice. | `CODEX.md::paper_module_index` |
| `CodexRoleProfile` | runtime config | Reasoning / sandbox / instructions for a named Codex role. | `.codex/roles/{explorer,monitor,worker}.toml` |
| `CodexRoleRegistry` | runtime config | Codex CLI agent registry binding role names to config files. | `.codex/config.toml` |
| `CodexRuntimeControlSurface` | runtime doc | Codex-side detached-wake / continuation-packet contract. | `docs/codex_control_surface.md` |
| `CodexFollowOnRegister` | hand-authored register | Codex-side pointer into the canonical `.claude/follow_on/` register. | `.codex/follow_on/README.md` |

### Invariants

- **AGENTS.override.md is the Codex-only discovery seed.** Claude does not read it as a primary surface. The seed is intentionally compact so Codex's project-doc discovery order does not blow byte budget on first read.
- **CODEX.md carries Codex deltas, not shared doctrine.** Role TOMLs, runtime control plane, manual work-ledger — these are Codex-specific. Shared doctrine routes through `AGENTS.md`.
- **Live blocks are projections — never hand-edit.** Both `instruction_discovery_live` (in `AGENTS.override.md`) and `codex_adapter_live` (in `CODEX.md`) plus `paper_module_index` are overwritten by every builder run.
- **AGENTS.override.md size is policy-bound.** `agent_bootstrap.json::instruction_discovery` carries the seed budget; the builder enforces it. Adding more hand-authored protocol above the live region must keep the file inside discovery budget or Codex CLI may truncate it on first read.
- **Codex roles are leaves, not chains.** `explorer`, `monitor`, `worker` each have a standalone TOML profile. They do not reference each other; selecting a role at `codex --agent <role>` activates one profile.
- **Manual work-ledger lifecycle is doctrine, not a temporary scaffold.** Until Codex host hooks exist, the worker role manually runs `session-status --overview`, `session-bootstrap`, `session-claim`, `session-release-claim`, `session-finalize` — this lifecycle is hand-authored in the Codex deltas section.

### Axes of variation

| Axis | Values |
|---|---|
| Surface role | compact discovery seed (`AGENTS.override.md`) / actor adapter (`CODEX.md`) |
| Section ownership | preamble (hand) / live block (builder) / actor deltas (hand) |
| Codex role | `explorer` (read-only, medium effort) / `monitor` (read-only, medium effort) / `worker` (no sandbox, high effort) |
| Live region in seed | `instruction_discovery_live` (file sizes + active phase + bootstrap sequence + routes) |
| Live region in adapter | `codex_adapter_live` + `paper_module_index` |

## Code loci

| Concern | Path |
|---|---|
| Codex compact discovery seed | `AGENTS.override.md` |
| Codex adapter markdown | `CODEX.md` |
| Schema config (live block source) | `codex/doctrine/agent_bootstrap.json` |
| Adapter / discovery renderer | `system/lib/agent_bootstrap_projection.py` |
| Codex agent registry | `.codex/config.toml` |
| Worker role TOML | `.codex/roles/worker.toml` |

## Current state

Snapshot dated 2026-04-25.

**Shipped:**
- `AGENTS.override.md` carries `<!-- BEGIN instruction_discovery_live -->` (line 7) and is populated by the bootstrap builder via `render_instruction_discovery_markdown`.
- `CODEX.md` carries `<!-- BEGIN codex_adapter_live -->` (line 64) and `<!-- BEGIN paper_module_index -->` (line 95); both regions are populated by the bootstrap builder.
- The Codex-deltas section (runtime control plane reference, role TOMLs, manual work-ledger lifecycle, follow-on register pointer) is hand-authored below the managed regions.
- Three Codex role profiles exist on disk: `explorer.toml`, `monitor.toml`, `worker.toml` under `.codex/roles/`.
- `.codex/config.toml` declares the three-agent registry with `description` + `config_file` per role.

**In progress / not yet built:**
- Codex host-hook plane is not built; the worker role runs the manual work-ledger cohort lifecycle until host hooks land.
- `codex/standards/principles/std_agent_bootstrap.json` is referenced by some downstream rows but is not validated by the builder; standard may be a stub.

## Deliverables (what this subsystem lets a cold agent DO)

- **Identify Codex-specific managed regions** by reading the Shape diagram and the markers in `AGENTS.override.md` (`<!-- BEGIN instruction_discovery_live -->`) and `CODEX.md` (`<!-- BEGIN codex_adapter_live -->`, `<!-- BEGIN paper_module_index -->`).
- **Refresh the Codex live regions** via `./repo-python tools/meta/factory/build_agent_bootstrap_projection.py` — one builder run regenerates both surfaces atomically.
- **Inspect the discovery seed bindings without writing** via `./repo-python tools/meta/factory/build_agent_bootstrap_projection.py --dry-run` (the preview includes the `instruction_discovery_preview` markdown).
- **Select a Codex role** via `codex --agent explorer|monitor|worker` (backed by `.codex/config.toml` + `.codex/roles/*.toml`).
- **Find the Codex runtime control plane** via the deltas-section pointer at `docs/codex_control_surface.md` and the `codex_runtime_control_plane` paper module.

## Gap (what Will is signaling)

The Codex two-surface adapter shape is the structural answer to a real asymmetry: Codex's project-doc discovery has a tighter byte budget than Claude's mandatory read order, so the entry plane needs a compact seed pointing into the deep hub instead of the deep hub directly. Will's signal is that this asymmetry should be honored without forcing duplication or drift — one bootstrap config, one builder, two coordinated surfaces. The deeper gap is that Codex still lacks host hooks (the Claude-side pattern); until those exist, the worker role's manual work-ledger lifecycle is the closest Codex-side analogue. A future refinement is to project the manual lifecycle into the `codex_adapter_live` block as a typed packet so workers do not have to re-read the deltas section every session. Anchor: `dtx_011` in `documentation_theory_index.json`, par `par_phase_08_raw_seed__source_1_next_ideas_md_020`.

## What a cold agent should NOT re-derive

- That `AGENTS.override.md` is Codex-only — Claude does not read it as a primary discovery surface.
- That `CODEX.md` is the full Codex adapter; `AGENTS.override.md` is the compact seed; both are needed and they project from one config.
- The three Codex roles and their profiles — enumerated in the role-profile axis; authority is `.codex/config.toml` + `.codex/roles/*.toml`.
- That live blocks (`instruction_discovery_live`, `codex_adapter_live`, `paper_module_index`) are builder-owned — hand edits are silently lost on the next builder run.
- Whether to read `AGENTS.md` after the seed — yes, the seed points into the deep hub; Codex is an adapter actor, not self-sufficient.
- That `docs/codex_control_surface.md` and the `codex_runtime_control_plane` paper module own Codex runtime semantics — `CODEX.md` deltas point at them, not duplicate them.

## Refresh contract

Refresh triggers:
- `agent_bootstrap.json::actor_context_surfaces` for `codex` changes — adapter live block needs rerun of the builder.
- `agent_bootstrap.json::instruction_discovery` config changes (seed budget, active-phase facts shape, byte caps) — `AGENTS.override.md` live region must be rerun.
- A new role TOML is added under `.codex/roles/` or `.codex/config.toml` is updated — update the Codex deltas section by hand and re-run the builder.
- The Codex runtime control plane shape changes (new docs path, new continuation-packet contract) — refresh `codex_runtime_control_plane` first, then this module's deltas pointer.
- A new paper module is authored that should appear in the `paper_module_index` slice — author the module, then run `./repo-python tools/meta/factory/build_paper_module_index.py && ./repo-python tools/meta/factory/build_agent_bootstrap_projection.py`.
- The schema hinge in `codex_agent_bootstrap_surface_schema` changes — refresh that hinge first, then this module.

Stale signals:
- A row inside `<!-- BEGIN codex_adapter_live --> … <!-- END codex_adapter_live -->` does not match `agent_bootstrap.json::actor_context_surfaces` for `codex` after a builder run.
- The byte counts in `<!-- BEGIN instruction_discovery_live -->` do not match `wc -c` of the four root markdowns after a builder run.
- A path in the Codex-deltas section 404s (role TOML missing, control plane doc moved).
- `AGENTS.override.md` exceeds the discovery budget configured in `agent_bootstrap.json::instruction_discovery`.

Snapshot dated 2026-04-25.
