# Agent Entry Surfaces

Projection class: index
Authored: 2026-04-24
Governing principles: pri_049, pri_097, pri_111
Governing concepts: con_001, con_021, con_024
Governing mechanisms: mech_031
Primary subdomain: control_layer_projection
Secondary subdomains: navigation_fidelity, surface_language
Depends on: codex_agent_bootstrap_surface_schema, host_agent_dotfile_surfaces
Search aliases: agent entry surfaces, agent entry points, AGENTS override, AGENTS.override.md, CODEX.md, CLAUDE.md, bootstrap projection, compressed entry projection, adapter anti-bloat, entry surface up-propagation, Claude adapter, Codex adapter, shared hub

---

## TLDR (compressed view)

Agent entry surfaces are the small set of files and generated blocks that a cold Type A agent sees before it has earned a wider read: `AGENTS.override.md`, `AGENTS.md`, `CODEX.md`, `CLAUDE.md`, and the bootstrap sidecars emitted from `codex/doctrine/agent_bootstrap.json`. The governing principle is **compressed entry projection**: when a durable subsystem matters to cold-agent orientation, the entry surface gets a route pointer, one-line rule, owning artifact, and freshness command, not the subsystem's protocol body. Codex-specific details stay in CODEX surfaces, Claude-specific details stay in Claude surfaces, shared doctrine stays in AGENTS, dynamic facts stay builder-owned, and every stale live-facts warning is repaired by refreshing the bootstrap projection before final validation. This module owns the authoring policy for how subsystems earn entry-surface presence and the contract it shares with `std_agent_entry_surface`; it delegates root-markdown ontology to `codex_markdown_doctrine`, host dotfile mechanics to `host_agent_dotfile_surfaces`, and post-projection comprehension auditing to `std_agent_entrypoint_audit`. The load-bearing invariant is "entry affordance, not entry doctrine" — a new subsystem earns a trigger phrase, one-line rule, route command, owning artifact, and freshness command at the entry plane; the full protocol body stays in its skill, standard, paper module, or generated sidecar. Cold-start relevance is the threshold: if a future agent would waste time, misunderstand authority, or miss a required freshness check without seeing the subsystem at boot, add a compressed pointer; otherwise route through ordinary depth layers.

## Intent

This module exists because entry surfaces are load-bearing but fragile: if they hide a new subsystem, future agents re-derive it; if they absorb the whole subsystem, future agents drown in bootstrap prose. The entry plane should therefore behave like a hologram thumbnail: enough signal to route, enough freshness metadata to distrust stale claims, and enough actor separation to avoid making Codex read Claude-specific hook lore or Claude read Codex-specific role TOML lore as shared doctrine.

The user request behind this module was specifically about "smart" up-propagation into agent entry surfaces: feature new generalized knowledge there, but do it dynamically and without bloating those surfaces. This module names that rule, binds it to `std_agent_entry_surface`, and wires the rule into the bootstrap projection so the markdown entry files receive a compact generated affordance instead of hand-maintained prose.

## Shape

```
codex/doctrine/agent_bootstrap.json
  entry_surface_propagation          authored policy row
  markdown_targets                   AGENTS.override.md / AGENTS.md / CODEX.md / CLAUDE.md
  actor_context_surfaces             actor read order and primary commands
  minimum_read_sets                  bounded route packets

system/lib/agent_bootstrap_projection.py
  normalize_entry_surface_propagation()
  render_entry_surface_propagation_markdown()
  render_live_markdown()
  render_adapter_markdown()
  render_instruction_discovery_markdown()

generated markdown regions
  AGENTS.override.md                 compact Codex discovery facts + one compressed entry rule
  AGENTS.md                          shared hub live block + route/minimum-read-set pointer
  CODEX.md                           Codex adapter live block + compact rule
  CLAUDE.md                          Claude adapter live block + compact rule
```

The sibling split is deliberate:

| Plane | Owns | Does not own |
|---|---|---|
| `codex_markdown_doctrine` | root markdown ontology for AGENTS / CODEX / CLAUDE | host dotfile mechanics |
| `host_agent_dotfile_surfaces` | `.claude/` and `.codex/` config trees | root markdown adapter policy |
| `agent_entry_surfaces` | how durable knowledge appears in entry surfaces | the full contents of each subsystem being routed to |
| `std_agent_entrypoint_audit` | measuring coverage after projection | authoring the projection policy |

## Ontology / Types & Invariants

| Type | Kind | One-line purpose | Symbol / file |
|---|---|---|---|
| `InstructionDiscoverySeed` | surface | Compact Codex first-read seed with live size and active-phase facts. | `AGENTS.override.md` |
| `SharedHub` | surface | Vendor-neutral doctrine hub and route table for all actors. | `AGENTS.md` |
| `CodexAdapter` | surface | Codex-specific deltas over the shared hub. | `CODEX.md` |
| `ClaudeAdapter` | surface | Claude-specific deltas over the shared hub. | `CLAUDE.md` |
| `BootstrapConfig` | authored substrate | Source of truth for markdown targets, actor packets, situation routes, and entry propagation policy. | `codex/doctrine/agent_bootstrap.json` |
| `EntrySurfacePropagation` | policy row | Defines the compressed entry projection rule and its drilldowns. | `agent_bootstrap.json::entry_surface_propagation` |
| `AgentEntrypointAudit` | generated audit | Tests whether the entry surfaces cover required comprehension axes. | `system/lib/agent_entrypoint_audit.py` |

Invariants:

- **Entry affordance, not entry doctrine.** A new subsystem earns a trigger phrase, one-line rule, route command, owning artifact, and freshness command in the entry plane; the full protocol remains in its skill, standard, paper module, kernel route, or generated sidecar.
- **Runtime routes consume projections.** A stable `--entry` / docs-route lane is not complete when Python recognizes it; it is complete when `agent_bootstrap.json`, minimum read sets, actor delivery, docs-route/skill rows, generated bootstrap blocks, and runtime matching all share the same stable id. Runtime matching must distinguish route-owned anchors from incidental projected vocabulary, and every cold-start route with projected `match_tokens` must carry semantic contrast smoke for a nearby generic false-positive task.
- **Dynamic facts are builder-owned.** Active phase, byte counts, stale live facts, generated route rows, and compact policy pointers flow through `build_agent_bootstrap_projection.py`.
- **Adapters stay actor-local.** CODEX.md carries Codex deltas; CLAUDE.md carries Claude deltas; AGENTS.md carries shared doctrine; AGENTS.override.md carries compact discovery and live facts for Codex's project-doc discovery order.
- **Stale projection is a build problem.** When the check reports `AGENTS.override.md` live facts stale against the builder, the correct next action is to run the bootstrap builder, then rerun the check.
- **Audit follows projection.** After entry-surface changes, run the entrypoint audit to verify the policy is reachable from shared, Codex, and Claude entrypoints.

Axes of variation:

| Axis | Values |
|---|---|
| Surface role | discovery seed / shared hub / actor adapter / injection strip |
| Payload authority | authored config / generated live facts / hand-authored static prose |
| Compression band | one-line seed pointer / compact adapter pointer / shared hub route row / full paper-module packet |
| Freshness posture | current / stale live region / over-budget file / missing marker |

## Code loci

| Concern | Path | Role |
|---|---|---|
| Bootstrap source of truth | `codex/doctrine/agent_bootstrap.json` | Authored policy, targets, routes, actor context, minimum read sets |
| Entry-surface standard | `codex/standards/std_agent_entry_surface.json` | Governs compressed entry projection and actor surface profiles |
| Bootstrap projection runtime | `system/lib/agent_bootstrap_projection.py` | Normalizes and renders generated entry-surface policy rows |
| Bootstrap builder | `tools/meta/factory/build_agent_bootstrap_projection.py` | Refreshes AGENTS / CODEX / CLAUDE generated regions and sidecars |
| Bootstrap checker | `tools/meta/factory/check_agent_bootstrap_projection.py` | Detects stale generated regions without writing |
| Agent-start preflight | `kernel.py --preflight`, `system/lib/kernel/commands/navigate.py::cmd_preflight` | Compact start card that exposes active phase, runtime posture, freshness risk, next-safe command, and do-not warnings before wider reads |
| Entrypoint audit standard | `codex/standards/std_agent_entrypoint_audit.json` | Governs comprehension-axis audit shape |
| Entrypoint audit runtime | `system/lib/agent_entrypoint_audit.py` | Measures surface coverage after projection |
| Entrypoint axis registry | `codex/doctrine/agent_entrypoints/axis_registry.json` | Authored comprehension obligations for shared / Codex / Claude |
| Entrypoint registry | `codex/doctrine/agent_entrypoints/entrypoint_registry.json` | Audit overlays and dotfile inventory |
| Markdown doctrine sibling | `codex/doctrine/paper_modules/codex_markdown_doctrine.md` | Root markdown ontology |
| Dotfile sibling | `codex/doctrine/paper_modules/host_agent_dotfile_surfaces.md` | Host `.claude/` / `.codex/` configuration ontology |

## Current state

Shipped:

- `codex/doctrine/agent_bootstrap.json::entry_surface_propagation` defines the compressed-entry-projection rule, owning standard, owning paper module, refresh/check commands, and surface roles.
- `system/lib/agent_bootstrap_projection.py` projects the rule into the shared live block, adapter live blocks, instruction-discovery block, live JSON sidecar, and injection strip.
- `std_agent_entry_surface` defines the standard for future entry-surface up-propagation.
- Docs-route and bootstrap situation routes can now target "agent entry surfaces" instead of falling through to unrelated PEER or generic adapter routes.
- The Type A common-sense/care/passion/critic-posture route miss now lands on `sit_type_a_judgment_metabolism`, a compact vocabulary/read-set packet that points at the open judgment-trait surface and propagation surfaces rather than adding adapter prose.
- `./repo-python kernel.py --preflight` is now the compact agent-start card in the bootstrap sequence. It gives cold agents the next safe command and explicit do-not warnings before they widen into `--pulse`, `--phase`, docs routes, or source reads.
- `dissemination_agent_entry` / `sit_dissemination_agent_entry` is the current worked example for classifier/projection convergence: the compressed bootstrap row, docs-route row, skill registry anchors, and runtime entry matcher share one projected route instead of relying on classifier-only phrase matching.

Packet-shaped surfaces that cold agents meet near entry have separate jobs:

| Surface | Job at entry | Authority posture |
|---|---|---|
| Entry packet | Route selection, lane, next action, diagnostics, and first drilldown | Generated control packet; downstream of `agent_bootstrap.json` and live kernel state |
| Context pack | Task-bound evidence compression after entry selects a neighborhood | Generated retrieval packet; not source authority |
| Agent operating packet | Compact Type A runtime doctrine frame with selected principles, agent-principle lens, and candidate pressure | Generated projection over raw-seed principles / axiom candidates and standards |
| Agent principle lens | Task-conditioned slice of agent-principle rows | Generated projection; full principle cards/tape remain source drilldown |
| Recipient packet | Recipient-facing proof branch for dissemination/review | Owned by `recipient_packet_theory`, not by entry surfaces |

In progress / expected after refresh:

- `AGENTS.override.md`, `AGENTS.md`, `CODEX.md`, and `CLAUDE.md` should show only compact generated pointers to this module and its standard.
- `codex/doctrine/agent_bootstrap_live.json` and `codex/doctrine/agent_bootstrap_injection_strip.json` should carry the same policy id for machine consumers.

Missing / not in scope:

- This module does not mine every future subsystem into the entry plane automatically. It defines the lane: a later subsystem can add a compressed affordance when it becomes cold-start relevant.
- This module does not replace `codex_markdown_doctrine` or `host_agent_dotfile_surfaces`; it explains how those planes are surfaced, refreshed, and audited from the entry boundary.

## Deliverables (what this subsystem lets a cold agent DO)

- **Route entry-surface questions** via `./repo-python kernel.py --docs-route "agent entry surfaces"` to reach this module and the governing standard.
- **Detect classifier/projection splits** by checking whether a new stable runtime lane also exists in `codex/doctrine/agent_bootstrap.json::situation_routes`, docs-route machine routes if applicable, `skill_registry.json` if a skill owns the lane, and generated bootstrap/routing projections; then prove the inverse with actor-delivery semantic contrast when the lane exposes `match_tokens`.
- **Refresh stale entry live facts** via `./repo-python tools/meta/factory/build_agent_bootstrap_projection.py` when a check reports builder drift.
- **Check generated-region drift** via `./repo-python tools/meta/factory/check_agent_bootstrap_projection.py`.
- **Audit entrypoint comprehension** via `./repo-python kernel.py --agent-entrypoint-audit`.
- **Start from the compact preflight card** via `./repo-python kernel.py --preflight` when a cold agent needs active phase, runtime posture, freshness risk, next safe command, and warnings in one bounded packet.
- **Find actor-specific boundaries** by reading the surface role table instead of inferring whether a rule belongs in AGENTS.override.md, AGENTS.md, CODEX.md, or CLAUDE.md.

## Gap (what Will is signaling)

Will is asking for the system to remember generalized ontology without turning the first-read files into another sprawling doctrine corpus. The concrete signal is the example pattern: "Routing projection is now clean. The bootstrap check found AGENTS.override.md live facts stale against the builder, so I’m refreshing the bootstrap projection as the repo contract requires before the final validation pass." That sentence is an entry-surface doctrine packet: trust the builder over stale live facts, repair projection drift before final validation, and leave the future agent a compressed explanation of why.

The remaining gap is judgment: not every new artifact deserves an entry-surface pointer. The threshold is cold-start relevance. If a future agent would reasonably waste time, misunderstand authority, or miss a required freshness check without seeing the subsystem at boot, add a compressed pointer; otherwise route through the ordinary paper-module, skill, standard, or docs-route surfaces.

## What a cold agent should NOT re-derive

- Do not decide by hand where AGENTS.override.md, AGENTS.md, CODEX.md, and CLAUDE.md should diverge; use the surface profiles in `std_agent_entry_surface`.
- Do not paste a new subsystem's full protocol into CODEX.md or CLAUDE.md to make it "discoverable"; add a compact bootstrap affordance and route to the owning artifact.
- Do not hand-edit generated regions after a stale bootstrap check; run the builder and then rerun the checker.
- Do not treat PEER propagation, system vocabulary, or paper modules as replacements for the entry plane; they are depth layers that entry surfaces can point at.
- Do not claim whole-system comprehension from markdown alone; run the entrypoint audit when the task is about cold-agent orientation.
- Do not ship `--entry` behavior as the only reliable way to discover a subsystem. If a route matters to cold agents, project it as a compressed entry row and make runtime matching derive from that row.
- Do not treat every packet-shaped artifact as an entry surface. Entry packets route; context packs retrieve; operating packets prime judgment; recipient packets transfer proof to a recipient boundary.

## Refresh contract

Refresh this module and its generated projections when any of these change:

- `codex/doctrine/agent_bootstrap.json::entry_surface_propagation`
- `markdown_targets`, `projection_roles`, `adapter_actor_map`, or `actor_context_surfaces` in `codex/doctrine/agent_bootstrap.json`
- `std_agent_entry_surface.json`
- the generated-region shape in `system/lib/agent_bootstrap_projection.py`
- entrypoint audit axes that make the compressed-entry-projection rule newly required or newly stale

Command sequence:

```bash
./repo-python tools/meta/factory/build_agent_bootstrap_projection.py
./repo-python tools/meta/factory/check_agent_bootstrap_projection.py
./repo-python tools/meta/factory/build_agent_entrypoint_audit.py --check
./repo-python tools/meta/factory/build_paper_module_index.py --check --report
```
