# AGENTS.md — ai_workflow | Deep shared hub; Codex seed is `AGENTS.override.md`; If reads truncate: run `./repo-python kernel.py --info` then `./repo-python kernel.py --docs-route documentation`

Vendor-neutral entry point for **any** AI coding agent working in this repository — Claude Code, Codex, Cursor, bridge workers. This file is the hub; depth lives in linked paper modules, skills, standards, and kernel-compiled JSON. Codex auto-loads [AGENTS.override.md](AGENTS.override.md) first as the compact discovery seed.

This file follows `codex/standards/std_agent_entry_surface.json::compression_via_projection_contract` (Rosetta Stone substrate-projection compression, `pri_121_candidate`, anchored at `par_phase_09_raw_seed__naming_a_structural_drift_signal_is_not_the_same_as_routing_it_017`). Long subsystem doctrine compresses to entry-affordance rows pointing to substrate. Three layers: (1) preamble + entry-affordance tables + locked doctrine, (2) builder-projected live regions (do not hand-edit — refresh via `./repo-python tools/meta/factory/build_agent_bootstrap_projection.py` and `./repo-python tools/meta/factory/build_skill_catalog_projection.py`), (3) read-next pointers.

Cold-entry contract: read the bounded top sections + generated live block, then run `./repo-python kernel.py --entry "<task>" --context-budget 12000` for the canonical control packet (per `std_agent_entry_surface.json::canonical_option_surface_routes.first_move_contract`). `--context-pack "<task>" --context-budget 12000` is the downstream cross-kind packet route after entry selects it. Use `--navigation-metabolism` for navigation/compression complaints. `--skill-find`, `--paper-module`, raw `--help`, and paper-lattice calls are drilldowns after stable ids are selected, not first-contact discovery. A full single-read of this hub is not mandatory.

## MANDATORY: Execution mode decision (read this FIRST)

**Before any substantial work, STOP. Pick an execution mode out loud before writing a single line of code.** Your default instinct (read files, improvise a plan in chat memory, decide on bridge/subagents later) is the anti-pattern this repo was built to fix. Start from the family charter and phase card.

| Mode | When | Controller does | Delegated surface does |
|------|------|-----------------|------------------------|
| `direct_local` | Bounded local change, no meaningful delegation seam | Reads charter/phase card, edits, validates, assimilates | Nothing |
| `hybrid` | Local wiring primary, one bounded seam benefits from delegation | Owns wave, picks seam, integrates, assimilates | Bridge or subagents handle the delegated seam |
| `bridge_graph` | Work decomposes into 3–8+ independent groups with fan-in barrier | Authors wave, compiles observe plan, dispatches, assimilates | Bridge workers perform grouped reasoning |
| `continuous_conductor` | Long-running bounded campaign with explicit wake barriers | Defines cadence, resume contract, closure gate | Bridge workers continue across wakes |
| `subagent_cohort` | Parallel native workers cover disjoint slices or zero-write evidence | Defines write boundaries + one assimilation sink | Subagents execute bounded slices |

**Decision test:** start at `family_charter.json` + `./repo-python kernel.py --phase`. If bounded with no delegation seam → `direct_local`. If one bounded slice delegates → `hybrid`. If natural fan-out into parallel groups with typed barrier → `bridge_graph` or `subagent_cohort`. If detached time + explicit wake barriers → `continuous_conductor`.

**One group = one prompt = NOT fan-out.** Fan-out means 3+ groups in parallel. Observe plans are NOT the universal entry gate — compile only when the wave mode is `bridge_graph` or `continuous_conductor`.

| Trigger | One-line rule | Owning artifact | Freshness |
|---------|---------------|-----------------|-----------|
| About to spawn Explore subagents to understand existing subsystem | `./repo-python kernel.py --context-pack "<task>" --context-budget 12000` first; open `--paper-lattice navigation_hologram_theory` only when that stable slug is selected, otherwise use paper-module evidence by explicit slug | [paper_module_authoring.md](codex/doctrine/skills/doctrine/paper_module_authoring.md) + [std_paper_module.json](codex/standards/std_paper_module.json) | `./repo-python tools/meta/factory/build_paper_module_index.py --check --report` |
| About to dispatch multi-group bridge fan-out | Read decomposition / context-injection / anti-pattern skill files first | [dispatch_yield.md](codex/doctrine/skills/bridge_runtime/dispatch_yield.md) + [resume_contract.md](codex/doctrine/skills/bridge_runtime/resume_contract.md) + [bridge_campaign_authoring.md](codex/doctrine/skills/kernel/bridge_campaign_authoring.md) + [observe_plan_authoring.md](codex/doctrine/skills/kernel/observe_plan_authoring.md) + [graph_authoring.md](codex/doctrine/skills/bridge_runtime/graph_authoring.md) | `kernel.py --skill-find "bridge graph"` |

If you skip the family-charter / phase-card gate and improvise execution mode from chat memory, you have violated the core operating principle. Dispatch procedure: shared contract below + [CLAUDE.md § Dispatch-yield-resume](CLAUDE.md) (Claude pause/resume/yield specifics).

## What this repository is

**ai_workflow** is a self-directing meta-workflow: observe–apply loops, optional bridge-dispatched reasoning (ChatGPT/Gemini via Chrome CDP), phase-based work under `obsidian/okay lets do this/`, machine-first doctrine under `codex/doctrine/`. The kernel (`kernel.py`) is the CLI navigation and (with `--apply`) mutation surface. The same tree hosts **Zenith** codex assets (`codex/substrate/`); for market-analysis substrate work, follow [codex/CODEX.md](codex/CODEX.md) after this hub's shared contract.

## Layer map (How / What / Why)

| Layer | Role | Primary artifacts |
|-------|------|-------------------|
| **How** | Procedural instructions; env; agent-specific stop/resume | This file, [CLAUDE.md](CLAUDE.md), [CODEX.md](CODEX.md) |
| **What** | Executable specs + working state | `family_charter.json`, `phase_scaffold.json`, `synth_seed.json`, `meta_ledger.json`, `observe_plan.json` (delegated waves), `codex/standards/*`, typed `.receipt.json` |
| **Why** | Durable intent, principles, concepts, mechanisms | `raw_seed.md` (family), `codex/doctrine/*`, `raw_seed_principles.json`, `doctrine_surface.json` |

## Multi-agent entry points

| Agent | Read first | Primary delta |
|-------|------------|----------------|
| **Claude / Claude Code** | [CLAUDE.md](CLAUDE.md), then this file | Thin Claude adapter: hooks, session/subagent semantics, Claude-specific yield/resume |
| **Codex** | [AGENTS.override.md](AGENTS.override.md) (compact seed), then [CODEX.md](CODEX.md), then this file | Thin Codex adapter: continuity, watcher/handoff surfaces, app-control |
| **Cursor** | This file directly | Reads `AGENTS.md` natively; no separate adapter needed |
| **Bridge workers** | `codex/doctrine/agent_bootstrap_injection_strip.json` (compact ≤8KB sidecar) | Workers receive bounded inject; controller curates plans + applies gates |

## Workspace discovery roots

- `AGENTS.md` is the shared context-file authority (Gemini reads it via `.gemini/settings.json::context.fileName`).
- [skill_map.md](codex/doctrine/skills/skill_map.md) is the generated full skill browse surface (compact catalog projects into AGENTS.md skill_catalog block).
- `.agents/skills/` holds workspace-local companion skills + annex-backed wrappers.
- `.claude/follow_on/` is the canonical follow-on register; `.codex/follow_on/README.md` is the Codex-side pointer.
- `python3 kernel.py --annex-inspiration "<problem shape>"` is the compressed annex inspiration surface; route there before authoring new patterns from scratch.

## Shared doctrine stack — activation router

The repo's substrate is **externalized cognition**. Reading it is activation, not retrieval: raw seed, shards, doctrine nodes, paper modules, ledgers, and code are layers of one world model. The current agent is the present-moment prefrontal-cortex layer thinking with that material. Principles are activation-grade compressions completed against the local situation, not static menu items to replay literally.

`kernel.py` is the activation router. Projection ladder traversed in order:

| Rung | Question | Surface |
|------|----------|---------|
| `0` | What is alive right now? | `./repo-python kernel.py --info` / `--pulse` |
| `1` | What is the whole system structurally? | `./repo-python kernel.py --system-map` |
| `2` | What compressed surfaces relate to task X? | `./repo-python kernel.py --context-pack "<task>" --context-budget 12000` |
| `3` | What should I read for situation X? | `./repo-python kernel.py --docs-route "<query-or-path>"` |
| `4` | Where is attention pointed? | `./repo-python kernel.py --frontier 5` |
| `5` | What thought has happened on topic X? | `./repo-python kernel.py --shards --shards-query "<topic>"` |
| `6` | What shards descend from this paragraph? | `./repo-python kernel.py --shards-paragraph <par_id>` |
| `7` | What was actually voiced? | `./repo-python kernel.py --resolve-raw-seed-ref __active__ "paragraph:<par_id>"` |
| `8` | Strongest local truth | substrate: open the file or artifact directly |

Default rule: start at the lowest rung that can answer the question; escalate only when the current rung leaves a named gap. Same shape recurs across artifact classes (`std_python`: docstring → bounded structural view → source).

## Routing Hologram

<!-- BEGIN generated_routing -->
_Auto-generated from `skill_registry.json`, `std_synth_seed.json`, `wave_conductor.md`, `delegation_protocol.md`, `routing_anti_patterns.json` + `state/agent_telemetry/latest_full/routing_candidates.json`. Do not edit by hand._
_Full browse: [codex/doctrine/skills/skill_map.md](codex/doctrine/skills/skill_map.md) | Refresh: `./repo-python tools/meta/factory/build_routing_projection.py`_

**Entry Protocol**
1. Run `python3 kernel.py --pulse` for repo state, hotspots, and drift signals.
2. Run `python3 kernel.py --phase <phase>` for the active wave and bounded packet contract.
3. Open one skill from the table below, then execute through that skill instead of improvising a new lane.

**Situation -> Skill**
_Top 10 rows by routing score. Full browse stays in `skill_map.md`._
| Situation | Open first |
|---|---|
| Any instruction mentions raw seed, paragraphs, shards, or voice substrate and the agent has not yet loaded the… | `raw_seed/raw_seed_navigation.md` |
| Cold boot, vague question, substrate unknown, or reflex-to-grep surfaced | `kernel/navigation_seed.md` |
| User asks about the codex/claude session folder, wants to know what past agents actually did, or wants to impro… | `kernel/agent_session_diagnostics.md` |
| Approval rows are pending and the conversation is the current operator surface | `kernel/operator_approval_surfacing.md` |
| Starting a new phase, reopening a stale phase, or checking whether a phase packet has the current wave protocol… | `kernel/subphase_bootstrap.md` |
| A navigation layer has changed or the user asks whether the ladder is actually usable | `kernel/navigation_dogfooding.md` |
| Need to find files, phases, or know what touches what | `kernel/navigate.md` |
| A non-raw-seed row, artifact, standard, paper section, worker packet, or navigation surface needs compact repre… | `compression/profile_governed_compression.md` |
| Session start, context lost, or first action in any new task | `kernel/bootstrap.md` |
| A proposed grammar spans standards, rows, lenses, skills, packets, receipts, workers, UI, or autonomy, especial… | `doctrine/system_microcosm_probe.md` |

**Modes + Persistence**
| Mode | Worker surface | Use when | Persistence |
|---|---|---|---|
| `direct_local` | controller | bounded local edits, no meaningful delegation seam. | `synth_seed.json` + `ledger_path` via `--phase-assimilate` |
| `hybrid` | controller + delegated seam | local wiring plus one or more bounded delegated seams. | `synth_seed.json` + `ledger_path`; delegated lane inherits the bridge or cohort contract |
| `mission_launch` | observe runtime + controller | mission expansion or launch owns the observe runtime handoff, but controller closure still lives in `seed_pipeline.py --status/--step --state <_mission_controller_state.json>`. | `observe_plan_path` + `resume_contract.json` (for detached observe wake) + `_mission_controller_state.json` + mission-local `pipeline_resume.json` / `pipeline_attention.json` |
| `bridge_graph` | bridge | injected-context bridge fan-out is the primary execution engine. | `observe_plan_path` + `resume_contract_path` + bridge receipts |
| `continuous_conductor` | bridge | long-running bounded campaign with explicit wake barriers. | `observe_plan_path` + `resume_contract_path` + `continuation_summary_path` + bridge receipts |
| `subagent_cohort` | subagent | the native tool-using sibling of `bridge_graph` for fan-out work. Use multiple scoped workers with explicit write boundaries, or zero-write evidence returns, and one controller-owned assimilation sink. | synth_seed.json:synthesis_memory + `delta_path` + `archive_root/cohort_wave_<wave_id>_bundles/` + `ledger_path` |

**Delegated Worker Contract**
| Surface | Contract |
|---|---|
| `subagent_cohort` | Workers are stateless, self-contained single-return calls; each prompt carries target paths, scope, expected artifacts, handoff requirements, and forbidden writes. |
| `zero-write cohort` | Evidence workers return typed bundles in-tool; the controller alone writes synthesis memory, optional delta/archive artifacts, and the ledger. |
| `bridge_graph / continuous_conductor` | Detached bridge work is resumed from the observe plan, resume contract, and stored receipts before controller assimilation. |

**Anti-patterns**
- Using grep, glob, or find as discovery when a kernel route or phase card can narrow the space first.
- Using bridge to discover scope before the controller or cohort has already selected refs, files, or slices.
- Letting zero-write workers persist files instead of returning typed bundles in-tool.
- Inventing new top-level subphase directories such as `cohort_wave_001/` or `worker_outputs/`.
- Changing execution mode in chat memory without updating the synth or wave contract.

_Artifact: `codex/doctrine/routing_hologram.json` | Sources sha256[:16]: `b265a29b750bb35d`_<!-- END generated_routing -->

## Shared contract (all agents) — entry-affordance table

| Concern | One-line rule | Owning artifact / freshness |
|---------|---------------|------------------------------|
| Environment | Use `./repo-python` + `./repo-pytest` from repo root; `./repo-env` for venv inheritance | — |
| Checkpointing | `./checkpoint "message"` — one command, no branches, no staging. **Never create branches**, repo is main-only | [checkpoint.md](codex/doctrine/skills/kernel/checkpoint.md) |
| Mutations | Prefer `python3 kernel.py --apply` and documented apply plans. Do not bypass mutation paths in production workflow | [doctrine_apply_lanes.md](codex/doctrine/paper_modules/doctrine_apply_lanes.md) |
| State | Durable JSON + phase artifacts over chat memory. Resume from phase-local / mission-local `pipeline_resume.json`, `doctrine_runtime.json`, `synth_seed.json`. Mission launches bootstrap from `_mission_controller_state.json` | [synth_first_scaffold_contract.md](docs/synth_first_scaffold_contract.md) |
| Raw-seed continuity entry order | `--raw-seed-autonomous-seed-bundle` → `--raw-seed-navigation-atlas-bundle` → `--raw-seed-navigation-runtime` → only then `--raw-seed-query` / `--raw-seed-navigation-prepare`. Five-sentence heartbeat is default minimal packet, not ceiling | [raw_seed_navigation.md](codex/doctrine/skills/raw_seed/raw_seed_navigation.md) |
| Voice substrates | `raw_seed.md` is operator voice only. Agent prose → sibling `agent_seed.md` via `python3 kernel.py --append-agent-seed --author <agent_id>`. Do not direct-edit either with file-edit tools | [agent_seed_authoring.md](codex/doctrine/skills/raw_seed/agent_seed_authoring.md) + [claude_memory_discipline.md](codex/doctrine/paper_modules/claude_memory_discipline.md) |
| Packet vocabulary | Learn packet roles before filenames: family raw-seed substrate, family charter, active seed surface, generated seed projection, cycle/wave-history ledger. Legacy `reference.md` / `observe_seed.md` names are compatibility materializations | — |
| Scaffold contract | New families/phases are synth-first + wave-based. Family roots emit `phase_family.json` + `family_charter.json` + raw-seed substrate. Phases emit `phase_scaffold.json` + `synth_seed.json` + `synth_seed.md` + `meta_ledger.json`, with `baseline_snapshot` + `archive_root` + `wave_protocol_version` | [synth_first_scaffold_contract.md](docs/synth_first_scaffold_contract.md) |
| Wave protocol | Subphase = one family anchor + one active synth + wave history. Start at `family_charter.json`; `kernel.py --phase <phase>` for compressed card; `--phase-step <phase>` for controller wave advancement; `--phase-assimilate <phase>` for closeout | [subphase_bootstrap.md](codex/doctrine/skills/kernel/subphase_bootstrap.md) |
| Mission launch | Typed execution lane, not generic bridge dispatch. Detached observe wake → `resume_contract.json`; controller closure → `_mission_controller_state.json` + mission-local `pipeline_resume.json` / `pipeline_attention.json` + `python3 seed_pipeline.py --step --state <path>` | [mission_launch.md](codex/doctrine/skills/kernel/mission_launch.md) |
| Bridge as worker | Bridge receives grouped probes; IDE agent curates plans and applies gates. Delegation economics → `con_029` | [graph_authoring.md](codex/doctrine/skills/bridge_runtime/graph_authoring.md) + [bridge_runtime.md](codex/doctrine/paper_modules/bridge_runtime.md) |
| Dispatch-yield-resume (bridge fan-out) | When wave mode is `bridge_graph` or `continuous_conductor`: (1) `./repo-python run_bridge_preflight.py`, (2) author observe plan (JSON, one group per prompt, `depends_on` for synthesis), (3) write `resume_contract.json` BEFORE dispatch (on_success / on_failure / context_bundle), (4) `./repo-python -m tools.meta.apply.run_observe_plan --plan <plan.json> --bridge --provider chatgpt --bridge-workers 3 --detach`, (5) **end the turn** — do not poll, do not substitute local parallelism. On resume: read contract, follow on_success/on_failure, read artifacts from disk | [dispatch_yield.md](codex/doctrine/skills/bridge_runtime/dispatch_yield.md) + [resume_contract.md](codex/doctrine/skills/bridge_runtime/resume_contract.md) + [bridge_campaign_authoring.md](codex/doctrine/skills/kernel/bridge_campaign_authoring.md) + [CLAUDE.md § Dispatch-yield-resume](CLAUDE.md) |
| Artifact authority | `std_artifact_ontology.json` → `core_authority_index.json`. JSON is the contract; markdown is the projection. `synth_seed.json` > `synth_seed.md` | — |
| Documentation honesty | Document what exists, not what should exist. Mark `**NOT YET BUILT**` inline or move to spec file. Plane trust > polished prose | [paper_module_authoring.md](codex/doctrine/skills/doctrine/paper_module_authoring.md) §Governing rules |
| Continuity protocol | Pause/resume lifecycle per `std_continuity_protocol.json`. `synth_seed.json` two layers: native whiteboard (`orientation`, `work_items`, `synthesis_memory`) + living continuity extensions (`continuity_mode`, `outstanding_questions`, `active_hypotheses`, `progress_state`, `next_step_posture`). Delta ops via `std_synth_seed_delta.json` | [controller_continuity.md](docs/controller_continuity.md) |
| Control plane | Runtime snapshot at `tools/meta/control/orchestration_state.json`. Docs-route focus: `python3 kernel.py --set-docs-route-focus <preset_id>` or `python3 run_control_room.py --set-docs-focus <preset_id>` | [orchestration_state.md](docs/orchestration_state.md) |
| Reactions engine (Phase 09.35) | Tracked config: `reactions.yaml` (schema [std_reactions.json](codex/standards/std_reactions.json)). Engine: `tools/meta/control/reactions_engine.py`. Runtime state / journal / stop-flag: `reactions_state.json` / `reactions_ledger.jsonl` / `reactions_stop.flag`. Orchestration writer projects `reactions` block into `orchestration_state.json` — engine never writes that snapshot itself | [reactions_engine.md](codex/doctrine/paper_modules/reactions_engine.md). Status: `./repo-python tools/meta/control/reactions_engine.py status` |
| Trust-default (`pri_121_candidate` sibling) | Controller-merge IS the trust gate, not operator-promotion-from-`proposed`. When clean rows merge (paths resolve, schema valid, lane decided, dedup clean), promote past holding-pen state in same merge step. Reserve `proposed` / `low` for rows worker itself flagged uncertain | [prime_directives.md §PD2c](codex/doctrine/paper_modules/prime_directives.md) + [doctrine_apply_lanes.md](codex/doctrine/paper_modules/doctrine_apply_lanes.md) |
| Entry-surface up-propagation | Compressed entry projection: route pointers, not protocol bodies. `pri_121_candidate` extends to refining the standard governing the artifact so it carries less hand-authored content and more substrate-derived projection | [agent_entry_surfaces.md](codex/doctrine/paper_modules/agent_entry_surfaces.md) + [std_agent_entry_surface.json](codex/standards/std_agent_entry_surface.json) |

<!-- pattern: crystallized session principles — shared doctrine for all agents -->

## Shared principles (all agents) — the crystallized doctrine

Seven principles locked in during active work. Every agent honors these, every mission pack is authored against them, every skill file cites them. Each has a raw-seed anchor; resolve with `python3 kernel.py --raw-seed-browse __active__ --query "<motif>"`.

1. **Extract intent, not text.** When reading Will's voice (raw seed, prompts, complaints, corrections), extract what he is *gesturing towards*, not what he literally said. Compression is a side effect of clarity, never the goal. This is the prime directive for every agent that reads Will. Anchor: `par_phase_05_4_agentic_navigation_and_subsystem_convergence_raw_seed__source_7_2026_04_14_infrastructure_integration_note_058` — "I am likely wrong. It's about intent."
2. **Bridge is a worker, not a black box.** Bridge receives a complete skill bundle (rubric + patterns + examples + schema) and returns typed output. The "black box" behaviour is a symptom of incomplete skill injection, not a property of bridge. Canonical skill-bundle contract: [codex/standards/observe/mission_templates/meta_missions/raw_seed_bridge_distillation/](codex/standards/observe/mission_templates/meta_missions/raw_seed_bridge_distillation/).
3. **No single-use infrastructure.** Every workflow is a Mission pack (a reusable Job template), never a one-off pipeline. If it runs once and dies, it was the wrong shape. Corollary: when a new pattern succeeds twice, package it as a Job before running it a third time.
4. **Dispatch policy is three separate knobs.** `cohort_size` (how many items this plan selects as backlog), `wave_width` (how many are dispatching at the same moment — bridge tabs open right now), `provider_ceiling` (hard cap from `tools/meta/bridge/provider_capabilities.json`). Never conflated in CLI, schema, or UI. Anchor: the note_047 paragraph — "never more than like 10 tabs open at a time, though, in case we get rate limited."
5. **Every doctrine edge is bidirectional.** `forward_gloss` + `reverse_gloss` + `reverse_gloss_status` required on every edge written from 2026-04-16 onward. One-sided edges are rejected at apply time. Migration lane: `./repo-python tools/meta/factory/raw_seed_apply_loop.py edge-migrate --commit --apply-back-mirror`.
6. **Shard lifecycle states accumulate, never subtract.** `extracted` → `routed` → `implemented` → `papered`, plus `contradicts` and `superseded_by` as first-class graph edges. Nothing ever "deprecates" — contradictions stay in the graph, supersessions are links not deletions. Schema: `codex/standards/observe_apply/std_extracted_shards.json`.
7. **Voice preservation is load-bearing.** Distilled shards must still sound like Will at his cleanest. A Wikipedia-voice shard has failed the Job. Canonical rubric: `codex/standards/observe/mission_templates/meta_missions/raw_seed_bridge_distillation/rubric.md` (with `voice_patterns.md` + `gold_examples.jsonl`).

### The factory framing

Mission packs are Worker Roles (Distiller, Router, Curator, Paperist, Critic, Researcher). Bridge is the Worker Pool; IDE Agents (Claude Code, Codex) are Curators/Foremen. Every Job has a rubric + examples + memory; skills improve over time by append to `gold_examples.jsonl`. Canonical Worker Role shape: [codex/standards/observe/mission_templates/meta_missions/raw_seed_bridge_distillation/](codex/standards/observe/mission_templates/meta_missions/raw_seed_bridge_distillation/) — rubric, voice_patterns, gold_examples, mission.json with `skill_files` + `shared_context_files` + `dispatch_policy`.

### Type A / Type B still holds (do not rename)

`Type A` = IDE Agents (Claude Code, Codex) — filesystem-aware, can read and write, expensive. `Type B` = Bridge Workers (ChatGPT/Gemini/Claude via CDP) — free, parallel up to provider_ceiling, receive-only-what-you-inject. Will considered renaming and decided against it; keep the terms, document their meaning. Anchor: the note_058 paragraph explicitly rejects the rename.

### Git scope discipline

Multiple agents share this worktree. Broad staging in one session silently sweeps another session's scoped work into a mistitled commit, which has been the recurring git-coordination failure here. Equally, treating every local commit as a high-blast-radius event blocks the basic survival mechanism — preserving coherent completed work — and lets the worktree grow until checkpointing becomes risky ceremony. The corrected posture distinguishes **local checkpoint** (commit) from **publication** (push/PR/remote sync): local commits are agent-default after validated scoped work; publication is operator-explicit only.

**Default posture — autocommit local checkpoint:**

After completing a coherent scoped unit of work and running validation, agents commit locally without re-asking. A local commit is a checkpoint, not publication. The repo treats local commits as the system's memory; uncheckpointed worktree growth is itself a system-risk in this solo-operator setup.

**Commit automatically when ALL are true:**

- the work is a coherent unit with a clear purpose;
- the changed paths are within the task scope or deliberately grouped;
- validation has run, or any skipped/failed validation is named in the commit message and/or final report;
- generated/gitignored state is excluded unless repo policy explicitly says to force-add it;
- no secrets, credentials, private tokens, or unrelated operator-private material are included;
- the commit will not destroy, overwrite, or silently absorb unrelated dirty work.

**Pause before committing only when:**

- the change is irreversible or high-blast-radius;
- the path scope is ambiguous;
- unrelated dirty paths would be swept in;
- validation failure is unexplained;
- secrets/private data may be present;
- the operator explicitly says not to commit.

If validation is partially failing because of a known historical scar (an immutable raw_event, an existing capture-pipeline regression, etc.), commit only if the forward gate passes (e.g. `--validate --since <cutover>`) and the commit/report names the scar, the cutover timestamp, and the exact failing command.

**Staging discipline:**

- **Never use `git add -A`, `git add .`, or `git commit -am`** during scoped repo work. Stage explicit pathspecs only, and commit only the files belonging to the current task scope.
- **Broad sweep / batch / all-in-one checkpoint commits are allowed only when the operator explicitly asks** for a *batch*, *sweep*, *checkpoint*, *save everything*, *commit everything*, *clean branch*, or *all-in-one* commit (those words signal the override). In the private-repo trust envelope, those words authorize the broad checkpoint lane after quick safety checks; do not require per-path ownership proof first. The `./checkpoint` shell script is the operator-invoked save-button for that case — it `git add -A`'s, commits, AND pushes.
- **If unrelated dirty paths exist, leave them unstaged** and report them separately for the operator to triage.
- **Assert the staged index equals the intended pathspec set AND the staged hunks equal the intended change before commit.** `git commit` ships the entire staged index, not just the latest `git add`, so two pollution paths must both be closed: (a) **cross-file** — another agent's previously-staged paths in this shared index ride along when `git commit` runs; (b) **same-file** — when the target file was already dirty before your edit, `git add <path>` stages every uncommitted hunk in that file, including unrelated concurrent changes. After staging, run `git diff --cached --name-only` and verify the file list exactly equals the intended pathspec set; for any dirty target file, also run `git diff --cached -- <path>` and verify the staged hunks contain only the intended change. If extras appear in either check, unstage with `git restore --staged <path>` (or `git reset HEAD <path>`), or rebuild the staged patch via a non-interactive hunk-only diff applied with `git apply --cached <hunk.patch>`, then re-verify both checks before commit. Post-commit recovery via `git reset --soft HEAD~1` followed by `git restore --staged <unintended-paths>` is non-destructive but the wrong shape; the equality assertions before commit are the right shape. (Failure modes caught 2026-04-27: cross-file — a scoped provider-worker test commit absorbed three pre-staged `system/core/bridge*.py` files because the shared index already held them; same-file — landing this very rule into AGENTS.md required a hunk-only `git apply --cached` patch because AGENTS.md was concurrently dirty with a builder-regenerated `agent_bootstrap_live` projection block, and a normal `git add AGENTS.md` would have swept that block too.)
- **Close the post-verification shared-index race with a pathspec-scoped commit when target paths are fully owned.** The previous bullet's `git diff --cached` checks are necessary but not sufficient in a multi-agent shared index: the verification can be correct and still become stale before `git commit` runs if another actor stages paths in the gap. For scoped commits where each target path's working tree exactly matches the intended staged content, prefer `git commit -m "..." -- <exact-pathspec...>` (the `-m` MUST precede the `--` separator; otherwise `--` makes `-m` itself a pathspec and the commit fails with "pathspec '-m' did not match any file(s)") after the staged path and hunk checks; this records only the named paths and prevents unrelated staged paths from riding along, regardless of what else has been pre-staged. Caveat: pathspec commit records the **current working-tree contents** of the named paths, not merely the already-staged hunks, so it is **unsafe for a concurrently dirty target file** unless `git diff -- <target-path>` (worktree-vs-cached) is empty after staging, or the target-path worktree otherwise equals the intended commit content. For hunk-only commits into dirty target files, first isolate the hunk so the target-path residual is empty — e.g. `git stash push -- <path>` to set aside unrelated worktree mods, edit, stage, commit with pathspec, then `git stash pop` — or use a private-index workflow (`GIT_INDEX_FILE=/tmp/private_index git read-tree HEAD; ... git apply --cached <patch>; git write-tree; git commit-tree; git update-ref` with CAS-on-parent) for true atomic isolation; do not trade a cross-file leak for a same-file hunk leak. Together the three layers are: (1) exact `git add <pathspec>` prevents accidental broad staging; (2) staged path equality + staged hunk equality detect *current* index pollution; (3) `git commit -m "..." -- <exact pathspec>` prevents *post-verification* cross-file staging races, but only when target-path worktree residual is empty. (Failure mode caught 2026-04-27: a scoped provider-metabolism CLI commit passed both staged-path and staged-hunk checks, then absorbed five newly pre-staged unrelated paths — `.claude/follow_on/closing_out.md`, `.claude/follow_on/passion.md`, `.gitignore`, `codex/doctrine/skills/doctrine/ship_implies_commit.md`, `tools/meta/templates/codex_continue_mode_activation_prompt.md` — between the final verification and `git commit`. Recovery required `git reset --soft HEAD~1`, clearing the staged index with `git reset HEAD -- .`, and recommitting via `git commit -m "..." -- <exact pathspecs>`. The commit that bootstraps this very rule should itself be landed via the layered defense — pathspec commit, target-path residual checked empty.)
- **Prefer `tools/meta/control/scoped_commit.py` over raw `git commit` in contested-index conditions.** The previous bullet's three-layer defense is implemented as repo-tracked infrastructure: `scoped_commit.py full-paths --path <p>... --message-file <m>` and `scoped_commit.py patch --patch-file <p> [--path <p>...] --message-file <m>` author a single bounded commit through a temporary `GIT_INDEX_FILE` initialized from HEAD and a `git update-ref <branch> <new> <captured-parent>` CAS, so the shared `.git/index` is read but never written by the actuator. Refusal cases (empty message, no-op, untracked-without-flag, declared paths != private-index changed paths, patch outside declared paths, parent CAS mismatch) hand failures back to the operator instead of producing wrong commits. Use `full-paths` mode when each target path's worktree is the intended commit content; use `patch` mode when target files are concurrently dirty and only a hunk is yours. The actuator was authored 2026-04-27 directly from the failure modes the previous two bullets describe and was dogfooded on its own bootstrap; tests live at `system/server/tests/test_scoped_commit_tool.py`.

**Publication discipline (push / remote sync):**

- **Never push, publish, open a PR, sync to GitHub, or update a remote unless the operator explicitly asks.** A local commit is a forward-only memory checkpoint; turning it into a remote one is a separate, higher-blast-radius decision requiring explicit operator authorization.
- Agent-autonomous scoped commits **do not push** unless the active adapter policy explicitly says to push by default. Operator-invoked `./checkpoint` does push; explicit broad-save language such as "commit everything" or "clean branch" counts as that operator opt-in in the private-repo trust envelope.

**After committing, report:**

- commit hash;
- exact paths committed;
- validation commands and outputs (including any historical-scar acknowledgment);
- paths deliberately excluded (and why);
- next move.

**Bounded forward-only commits on the current branch are not destructive** — when the scope is clear and validation passes, agents commit without re-asking. Confirmation gates apply only to destructive ops (force push, `reset --hard`, branch deletion, history rewrite, broad sweeps without operator authorization) and to publication (push / remote sync).

**Ambitious closure inside the trust envelope** AND **propagate corrections to durable substrate (not "mental model updated")** — boundedness is a blast-radius/proof discipline, not an ambition cap or a reason to ship one token slice. Full doctrine + anti-patterns + conservative-stop conditions + routing rule (process / structural / doctrine / voice) live in [`local_to_general_propagation.md`](codex/doctrine/skills/doctrine/local_to_general_propagation.md) (governing principles section). Routed here per pri_121 to keep the hub at byte-budget; the skill is source of truth.

## Workflow analogy (not Spec Kit)

This repo is **not** GitHub Spec Kit, but the **shape** is similar: **intent** (family charter / synth) → **bounded wave contract** → **optional compiled observe plan for delegated lanes** → **execution** (controller, bridge, or subagents) → **validated apply + assimilation**. Prefer typed JSON at handoff boundaries.

## Substrate-specific entry-affordance table (Rosetta Stone)

| Trigger | One-line rule | Owning artifact | Freshness |
|---------|---------------|-----------------|-----------|
| Browsing Python substrate (system/lib, tools, kernel internals) | `codex/hologram/system/` is the current named Python browse surface; canonical emitted artifacts are `inventory.json`, `scope_tree.json`, `symbols.json`, `graph.json`, `quality.json`, `navigation_cache.json`, `ui_index.json`, `scope_state.json`. Browse fidelity ladder: `scope_tree.json` → `symbols.json` → `graph.json` → `quality.json` + `navigation_cache.json` → `python3 kernel.py --compile <path>` → raw source. Do NOT reference legacy numbered dumps (`08_self_model.json`, etc.) — those are legacy outputs, not current contract | [system_lib_directory_index.md](codex/doctrine/paper_modules/system_lib_directory_index.md) + [kernel_entry_paths.md](codex/doctrine/paper_modules/kernel_entry_paths.md) | `./repo-python kernel.py --build status` |
| Search / find / locate (kernel-first, grep fallback) | Kernel before grep: `--orient-task X` for "files related to X"; `--compile <path>` for "understand this Python file"; `--locate <token>` for "where is X defined"; `--pulse` for "current state"; `--raw-seed-browse <family> --query "X"` for "raw seed says about X"; `--docs-route <path>` for "which standard governs this file". Grep is right ONLY for exact string match ("find all call sites of function_name") AFTER the target is already named | [navigation_seed.md](codex/doctrine/skills/kernel/navigation_seed.md) | `./repo-python kernel.py --skill-find "navigation"` |
| Orientation bootstrap (cold-start read path) | `--info` → `--preflight` → `--pulse` → `--entry "<task>" --context-budget 12000` (canonical front door per `std_agent_entry_surface.json::canonical_option_surface_routes.first_move_contract`); `--context-pack "<task>"` only when entry routes to a cross-kind packet; use `--navigation-metabolism` for route/compression complaints, and only then drill into docs, paper-module, skill, or paper-lattice evidence by stable id. | [bootstrap.md](codex/doctrine/skills/kernel/bootstrap.md) | `./repo-python kernel.py --entry "<task>" --context-budget 12000` |
| Phase / wave gate (once task is phase-scoped) | `family_charter.json` → `./repo-python kernel.py --phase <phase>` → matching skill / `--phase-step` / `--phase-assimilate`. Do NOT overload orientation bootstrap with phase gate — different questions | [subphase_bootstrap.md](codex/doctrine/skills/kernel/subphase_bootstrap.md) | `./repo-python kernel.py --phase` |
| Reset authority (fresh repo-entry, semantic hologram cleanup, phase-reset) | Start from [family_charter.json](obsidian/okay%20lets%20do%20this/09%20-%20Raw-Seed%20Preservation,%20Semantic%20Reset,%20and%20Fresh%20Execution%20Spine/family_charter.json) → `./repo-python kernel.py --phase` for live wave. Phase 09.1 is preserved as closed lineage + reset rationale, not default runtime packet | — | — |
| Refresh live bootstrap projection | After editing `agent_bootstrap.json` or its inputs, regenerate live blocks in CLAUDE.md / CODEX.md / AGENTS.md | [agent_entry_surfaces.md](codex/doctrine/paper_modules/agent_entry_surfaces.md) + [codex_markdown_doctrine.md](codex/doctrine/paper_modules/codex_markdown_doctrine.md) | `./repo-python tools/meta/factory/build_agent_bootstrap_projection.py` |

<!-- BEGIN agent_bootstrap_live -->
### Live context (from disk)

_This block is regenerated by the builder; do not edit by hand._

**Refresh:**

```bash
./repo-python tools/meta/factory/build_agent_bootstrap_projection.py
```

**Pipeline (runtime-eligible active state):**
- State: `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/09.44 - Phase 09.44 - Provider Metabolism and Operator Context Spine/pipeline_state.json` — stage `synth_seed_emitted`, controller phase `scope`, cycle `0`
- Phase dir: `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/09.44 - Phase 09.44 - Provider Metabolism and Operator Context Spine`
- Explicit active phase: `09_44` — `Phase 09.44 - Provider Metabolism and Operator Context Spine`
- Explicit active dir: `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/09.44 - Phase 09.44 - Provider Metabolism and Operator Context Spine`

**Factory runner:**
- `tools/meta/factory/factory_state.json` — stage `stage_apply_failed`, last_run `2026-03-25T02:01:06.404686+00:00`

**Holographic / control plane:**
- `system_map.json` generated_at: `2026-04-22T17:51:47.347103+00:00`
- `doctrine_runtime.json` mtime (UTC): `2026-04-15T15:18:29.361722+00:00`
- `orchestration_state.json`: `phase_pipeline` gate `none`
- `orchestration_events.jsonl`: `tools/meta/control/orchestration_events.jsonl`
- `documentation_route_focus.json`: `neutral`
- `focus_directive.json`: `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/09.44 - Phase 09.44 - Provider Metabolism and Operator Context Spine/focus_directive.json` — `active directive`
- `system_view.json`: `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/09.44 - Phase 09.44 - Provider Metabolism and Operator Context Spine/system_view.json` — file_count `2000`

**Extracted shards (factory lane backlog):**
- `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/09.44 - Phase 09.44 - Provider Metabolism and Operator Context Spine/extracted_shards.json` — shard count: 1

**Multi-agent entry points (stable):**

| Agent | Read first | Primary delta |
|-------|------------|---------------|
| **Claude / Claude Code** | CLAUDE.md adapter, then AGENTS.md hub | Thin Claude adapter: hooks, session/subagent semantics, and Claude-specific yield/resume deltas after the mandatory AGENTS handoff. |
| **Codex** | CODEX.md adapter, then AGENTS.md hub | Thin Codex adapter: controller continuity, watcher/app-control behavior, and Codex-specific detached-wake posture after the mandatory AGENTS handoff. |

**Compact startup command surface:**

- Bootstrap path (kernel.py): `--info` → `--preflight` → `--pulse` → `--context-pack "<task>" --context-budget 12000` → `--navigation-metabolism "<task>" --context-budget 12000` → `--kind-atlas` → `--option-surface paper_modules --band cluster_flag` → `--docs-route documentation` → `--system-map` → `--frontier 5`
- Lane registry (5 lanes: `apply`, `infrastructure`, `navigate`, `observe`, `planning`): `./repo-python kernel.py --info` for full lane × command × flags taxonomy (also in `codex/doctrine/agent_bootstrap_live.json::compact_command_surface`).

**Runtime control plane:**

- Snapshot: `tools/meta/control/orchestration_state.json`
- Event log: `tools/meta/control/orchestration_events.jsonl`
- Control room: `python3 run_control_room.py`
- Refresh write: `python3 overnight_control.py --write`
- Docs route: `python3 kernel.py --docs-route system/control/orchestration.py`

**Situation routes (canonical next read):**

_Compressed per pri_121 / std_agent_entry_surface.json::compression_via_projection_contract. `set` (MRS id) and `fallback` live in `codex/doctrine/agent_bootstrap_live.json::situation_routes`; expand a row via `./repo-python kernel.py --docs-route <query>` or follow `next`._

- `russian_doll_option_surface_entry` (pri_128) — Russian-doll option surface entry (per pri_128). Cold start; route miss; the artifact kind is not yet known; before…
  - route `./repo-python kernel.py --kind-atlas`; → `codex/doctrine/paper_modules/navigation_hologram_theory.md`; freshness `./repo-python kernel.py --navigation-context-rosetta`
- `documentation_plane` — Documentation plane orientation. Fresh-session or ambiguous documentation questions: what do I read…
  - route `./repo-python kernel.py --docs-route documentation`; → `docs/documentation_plane_map.md`
- `agent_telemetry_navigation_diagnostics` — Agent telemetry and navigation diagnostics. The task is about how Claude/Codex actually navigate this repo: bash…
  - route `./repo-python kernel.py --docs-route "agent telemetry"`; → `docs/agent_telemetry.md`
- `agent_session_diagnostics_training_loop` — Agent session diagnostics training loop. The task is about out-of-repo Codex/Claude session storage, what the…
  - route `./repo-python kernel.py --docs-route "session storage"`; → `codex/doctrine/skills/kernel/agent_session_diagnostics.md`
- `runtime_control` — Runtime control plane. The task is about orchestration ownership, proof/approval gates,…
  - route `python3 kernel.py --docs-route system/control/orchestration.py`; → `docs/orchestration_state.md`
- `always_on_metabolism_governor` — Always-on metabolism governor. The task is about always-on metabolism, overnight/day gas pedal,…
  - route `./repo-python kernel.py --docs-route "always-on metabolism gas pedal"`; → `codex/doctrine/paper_modules/continuous_runtime_layer.md`
- `self_description_campaign` — Self-description campaign bootstrap. The task is broad objective self-description, projection ladders,…
  - route `python3 kernel.py --docs-route "self description"`; → `docs/self_description_campaign_bootstrap.md`
- `external_reference_prior_art` — External reference / prior-art routing. The task is to look online, find repos, find GitHubs, run cited…
  - route `python3 kernel.py --docs-route "look online bridge research probe"`; → `codex/doctrine/skills/bridge_runtime/bridge_research_probe.md`
- `annex_bridge_navigation` — Annex bridge into navigation/control/docs. The task is about connecting annex prior-patterns, distillation rows,…
  - route `python3 kernel.py --docs-route "annex control plane navigation"`; → `codex/doctrine/paper_modules/codex_annex_substrate.md`
- `paper_modules_surface` (pri_128) — Paper modules / subsystem projections. The task is to understand an existing subsystem quickly, recover a…
  - route `./repo-python kernel.py --option-surface paper_modules --band cluster_flag`; → `codex/doctrine/paper_modules/system_constitution_seed.md`
- `bridge_session_continuity` — Bridge OS and session continuity. The task is about bridge provider caps, prompt manifests, validator…
  - route `python3 kernel.py --docs-route bridge`; → `docs/bridge_operating_system.md`
- `controller_continuity` — IDE controller continuity. The task is about controller pause/resume, wake conditions, detached…
  - route `python3 kernel.py --docs-route "controller continuity"`; → `docs/controller_continuity.md`
- `codex_control_surface` — Codex control surface. The task is about Codex desktop control, the CDP driver, same-thread…
  - route `python3 kernel.py --docs-route "codex control surface"`; → `docs/codex_control_surface.md`
- `type_a_convergence` — Type A convergence and host-record feedback. The task is about keeping Codex, Claude Code, AGENTS.md, and…
  - route `./repo-python kernel.py --docs-route "agent telemetry"`; → `docs/agent_telemetry.md`
- `type_a_entry_experience` — Type A entry experience and cold-comprehension guard. The task is about Claude/Codex entry points, AGENTS.override.md,…
  - route `./repo-python kernel.py --docs-route "agent entry surfaces"`; → `codex/doctrine/paper_modules/agent_entry_surfaces.md`
- `type_a_operating_register` — Type A operating register and useful-finding readout. The task is about common sense, care, passion, going above and…
  - route `./repo-python kernel.py --docs-route "type a operating register"`; → `codex/doctrine/system_vocabulary/term_registry.json`
- `type_a_judgment_metabolism` — Type A judgment, common sense, and thinking traits. The task is about critic posture, thinking traits, judgment traits,…
  - route `./repo-python kernel.py --docs-route "critic posture"`; → `codex/doctrine/system_vocabulary/term_registry.json`
- `system_axiom_candidates` — System axiom candidates and constitutional pressure. The task is about axiom candidates, common-sense-up-propagates,…
  - route `./repo-python kernel.py --docs-route "axiom candidate"`; → `codex/doctrine/skills/doctrine/axiom_up_propagation.md`
- `semantic_naming` — Semantic naming and reference-preserving rename. The task is about file naming systems, semantic filenames, bad or…
  - route `./repo-python kernel.py --docs-route "semantic naming option surface"`; → `codex/standards/std_semantic_naming.json`
- `local_to_general_propagation` — Local-to-general propagation and lattice transposition. The task is about up-propagating a local lesson into the generalized…
  - route `./repo-python kernel.py --docs-route "lattice transposition generalized up-propagation"`; → `codex/doctrine/skills/doctrine/local_to_general_propagation.md`
- `peer_propagation` — PEER propagation and tribal knowledge receipts. The task is about PEER propagation, tribal knowledge, peer-to-peer…
  - route `./repo-python kernel.py --docs-route "peer propagation tribal knowledge"`; → `codex/doctrine/skills/doctrine/peer_propagation.md`
- `raw_seed_substrate` — Family raw-seed substrate. The task is about blackboard intent, family voice, paragraph anchors,…
  - route `python3 kernel.py --docs-route "raw_seed substrate"`; → `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_meta.md`
- `doctrine_and_standards` — Doctrine and standards IO. The task is about con_*.json, mech_*.json, std_*.json, or…
  - route `python3 kernel.py --docs-route "standards registry"`; → `codex/standards/standards_registry.json`
- `doctrine_lattice_context` — Doctrine lattice context. The task is about axioms, principles, standards, compression…
  - route `./repo-python kernel.py --docs-route "raw_seed_principles standards axioms"`; → `docs/raw_seed_principles_curation.md`
- `python_runtime_surface` — Python runtime surface. The task is localized to a Python file under system/, tools/, or a…
  - route `python3 kernel.py --docs-route <repo-relative .py path>`; → `codex/standards/std_python.py`
- `python_runtime_architecture` — Python runtime architecture. The task is a freeform Python runtime, Python architecture,…
  - route `python3 kernel.py --docs-route "Python runtime"`; → `codex/doctrine/paper_modules/system_lib_directory_index.md`

**Actor context surfaces:**

_Compressed per pri_121. `set` (MRS id) and `surface` (runtime surface id) live in `agent_bootstrap_live.json::actor_context_surfaces`; the headline + first command + first read is the Rosetta Stone seed._

- `codex` — Codex IDE agent
  - cmd `./repo-python kernel.py --info`; read `AGENTS.override.md`
- `claude_code` — Claude Code IDE agent
  - cmd `./repo-python kernel.py --info`; read `CLAUDE.md`
- `bridge_worker` — Bridge worker
  - cmd `./repo-python kernel.py --pulse`; read `codex/doctrine/agent_bootstrap_injection_strip.json`
- `human_operator` — Human operator
  - cmd `./repo-python run_control_room.py`; read `docs/orchestration_state.md`
- `control_room_manager` — Control-room manager
  - cmd `python3 run_control_room.py`; read `tools/meta/control/orchestration_state.json`

**Type A convergence contract:**

- Codex and Claude Code converge through the shared hub first, then adapter deltas, with observed host records used as feedback on how agents actually navigate and mutate this repo.
- route `./repo-python kernel.py --docs-route "agent telemetry"`; next `docs/agent_telemetry.md`; coverage `./repo-python tools/meta/agent_telemetry/coverage.py --symbolic-only`
- Source surfaces: `AGENTS.md + CODEX.md + CLAUDE.md`; `.codex/ + .claude/`; `~/.codex/ + ~/.claude/` (roles/authority in `codex/doctrine/agent_bootstrap_live.json`).
- Safe probes: `./repo-python tools/meta/agent_telemetry/extract.py --since <ISO8601>`; `./repo-python tools/meta/agent_telemetry/host_surface_probe.py --since <ISO8601>`; `./repo-python tools/meta/agent_telemetry/coverage.py --symbolic-only` (purposes in `codex/doctrine/agent_bootstrap_live.json`).
- Comprehension gate: A Type A agent may only report whole-system understanding after citing evidence from both control surfaces and Python substrate. Missing buckets mean the report is partial, even if the control plane felt coherent.
  - Gate route: `./repo-python kernel.py --docs-route "agent entry points"`
  - Required evidence buckets (8): `shared_markdown_adapters`; `repo_host_dotfiles`; `python_substrate`; `derived_facts_anti_drift`; `raw_seed_projection_coverage`; `agent_execution_trace_visibility`; `active_phase_control`; `doctrine_or_raw_seed_authority` (per pri_121; full glosses in `codex/doctrine/agent_bootstrap_live.json`).
  - `derived_facts_anti_drift`: `python3 kernel.py --facts` | `python3 kernel.py --fact-audit` | `python3 kernel.py --paper-module-facts <slug>`
  - `raw_seed_projection_coverage`: `python3 kernel.py --raw-seed-projection-theme <theme>` | `python3 kernel.py --raw-seed-projection-coverage` | `python3 kernel.py --raw-seed-projection-gap-audit`
  - `agent_execution_trace_visibility`: `python3 kernel.py --process-audit` | `python3 kernel.py --process-patterns` | `python3 kernel.py --process-trace latest`
  - Failure mode: If any bucket is missing, say partial comprehension and name the missing bucket instead of claiming whole-system understanding.
- Feedback loop: probe → compare → patch → regenerate → run (full prose in `codex/doctrine/agent_bootstrap_live.json`).
- Invariants: 4 (text in `codex/doctrine/agent_bootstrap_live.json::type_a_convergence_contract.invariants`).

**Minimum read set registry:**

- Total available sets: 63. Full id list lives in `codex/doctrine/agent_bootstrap_live.json::minimum_read_sets` (builder-projected sidecar) and `codex/doctrine/agent_bootstrap.json::minimum_read_sets` (source).
- Resolve the actual bounded path set with `./repo-python kernel.py --docs-route <query-or-path>` (path list returned in `payload.minimum_read_set.paths`).
<!-- END agent_bootstrap_live -->

<!-- BEGIN paper_module_index -->
### Paper modules — subsystem ontology (auto-projected)

_Freshness-aware discoverability slice from authored paper modules, per `codex/standards/std_paper_module.json::bootstrap_projection_contract`. Full inventory lives in `codex/doctrine/paper_modules/README.md`, `_index.json`, and `_validation_report.json`. Do not edit by hand._

Pins first: `raw_seed_substrate`, `raw_seed_metabolism`, `system_constitution_seed` · Ranked tail: fan-in desc
Freshness: `stale_sidecars_and_readme` · authored modules: `140` · checked-in sidecars: index `140` / report `140`

_Shared paper-module sidecars are stale or incomplete; this block resolves from authored markdown via the shared runtime and should not be treated as high-trust shared machine state until the builder is rerun._

| Slug | Open this when | Status |
|---|---|---|
| `raw_seed_substrate` | Raw seed is the **operator-voice authority substrate** of this repo: one append-only family-sco… | `up_to_date` |
| `raw_seed_metabolism` | Raw-seed metabolism is the repo's two-phase chain for turning family seed paragraphs into doctr… | `up_to_date` |
| `system_constitution_seed` | The system constitution seed is the **root-ontology paper module**: one idempotent file that a… | `up_to_date` |
| `reactions_engine` | The Reactions Engine is a journal-gated, single-flight automation lane that watches durable rep… | `up_to_date` |
| `embedding_substrate` | The embedding substrate is a generalised faceted-vector-field cache over every durable plane ar… | `up_to_date` |
| `bridge_runtime_control_plane` | The bridge runtime control plane is the dispatch-yield-resume policy surface that owns job ids,… | `up_to_date` |
| `meta_mission_runtime` | A meta-mission is a fixed, named, reusable procedure with a versioned skill bundle and a durabl… | `up_to_date` |
| `station_backend_world_model` | The Station backend is a **read-only projection layer** over the repo's durable JSON artifacts:… | `up_to_date` |
| _… +132 more_ | _See_ `README.md` / `_index.json` for the full inventory._ | |

**Read flow:** open the module, read TLDR-first, then spot-check one `Code loci` row before acting.
**Refresh:** `./repo-python tools/meta/factory/build_paper_module_index.py && ./repo-python tools/meta/factory/build_agent_bootstrap_projection.py`.
<!-- END paper_module_index -->

## Skills and kernel runbooks

<!-- BEGIN skill_catalog -->
## Skill router

_Generated from `codex/doctrine/skills/skill_registry.json`. Refresh with `./repo-python tools/meta/factory/build_skill_catalog_projection.py --target all`._

Canonical routing source: `codex/doctrine/skills/skill_registry.json`

Route by intent:
`./repo-python kernel.py --skill-find "<task or intent>"`

List published Agent Skills:
`./repo-python kernel.py --skill-list --surface agent-skills --format names`

**Published Agent Skills** (`.agents/skills/`):
- generated: `bootstrap`, `navigation-seed`, `local-to-general-propagation`, `agent-session-diagnostics`, `checkpoint`, `raw-seed-distill`
- hand-authored: `claude-code-best-practice-annex`, `codex-annex`, `codexia-annex`, `continuous-claude-v4-7-annex`, `craft-agents-oss-annex`, `euphony-annex`, `gemini-cli-annex`, `get-shit-done-annex`, `insforge-annex`, `karpathy-skills-annex`, `lycheemem-annex`, `magi-annex`, `memoryos-annex`, `mex-annex`, `ml-intern-annex`, `openclaw-mission-control-annex`, `openmemory-annex`, `ouros-annex`, `paseo-annex`, `skillclaw-annex`, `socraticode-annex`, `tamux-annex`, `tmux-agent-sidebar-annex`, `understand`, `understand-anything-annex`, `understand-chat`, `understand-dashboard`, `understand-diff`, `understand-explain`, `understand-onboard`

Full registry map: `codex/doctrine/skills/skill_map.md`

---

### Skill catalog — Rosetta Stone seed (full body in skill_map.md)

_Auto-generated from `skill_registry.json` per `std_agent_entry_surface.json::compression_via_projection_contract` (Rosetta Stone shape: minimum surface + route to expansion). Do not edit by hand._
_Refresh: `./repo-python tools/meta/factory/build_skill_catalog_projection.py`_

**Full browse:** [codex/doctrine/skills/skill_map.md](codex/doctrine/skills/skill_map.md) — family-grouped catalog with one-liners, triggers, and entry commands for every active skill.
**Query:** `./repo-python kernel.py --skill-find "<query>"` — ranked lookup against active skills.
**Browse one family:** open `codex/doctrine/skills/<family_id>/` directly after picking the right family from the table below.

**Active families (counts + canonical entry skill):**

| Family | Active skills | Canonical entry |
|---|---:|---|
| **Kernel Operations** (`kernel`) | 42 | `bootstrap` — Orient to repo and select the right workflow to begin |
| **Bridge Operations** (`bridge`) | 10 | `dispatch_yield` — Dispatch bridge work, stop your turn, get resumed later |
| **Frontend** (`frontend`) | 13 | `frontend_design` — Design operator-first frontend surfaces with quiet, utility-first p... |
| **Reasoning & Cognition** (`reasoning`) | 4 | `understand` — Build a mental model before acting on unfamiliar code |
| **Doctrine & Self-Knowledge** (`doctrine`) | 47 | `curate` — Extract and register principles, concepts, and mechanisms from raw ... |
| **Obsidian Operator Vault** (`obsidian`) | 1 | `vault_projection` — Refresh the operator Obsidian vault projection without touching raw... |
| **Raw-Seed Substrate and Metabolism** (`raw_seed`) | 7 | `raw_seed_navigation` — Agent-entry map for raw seed: operator substrate, sibling agent sub... |
| **Shared Compression Profiles** (`compression`) | 2 | `profile_governed_compression` — Compress rows only through declared profiles, bands, and drilldowns |
| **Agent Skills façade** (`agent_skills_facade`) | 30 | `claude_code_best_practice_annex` — Surface annex-backed patterns from the claude-code-best-practice pr... |

_Total: 156 active skills across 9 families. Full per-skill catalog lives in `skill_map.md`; this projection is intentionally compressed per `pri_121_candidate` (compression-via-substrate-projection / Rosetta Stone)._
<!-- END skill_catalog -->

- Docs-first router: [docs/agent_instruction_router.md](docs/agent_instruction_router.md) (trigger → which file to open) + [docs/skills_kernel_and_doc_layers.md](docs/skills_kernel_and_doc_layers.md) (How/What/Why, runbooks vs playbooks, annex substrate).
- Trigger map (observe/apply depth): [codex/CODEX.md](codex/CODEX.md) "Guide Router".
- Kernel runbooks: `codex/doctrine/skills/kernel/*.md` — open the ONE that matches the task; do not improvise observe/apply semantics.
- Bridge runtime runbooks: load the matching `codex/doctrine/skills/bridge_runtime/*.md` runbook before dispatching detached grouped observe / yield-resume / same-session Claude wake.
- Machine index: `codex/doctrine/skills/kernel/_schema.json`.
- Formal Agent Skills spec (upstream): [agentskills.io/specification](https://agentskills.io/specification); local: `annexes/anthropic-skills/repo/spec/agent-skills-spec.md`.

## Hosted tools, MCP, factory, prompts — entry-affordance table

| Concern | One-line rule | Owning artifact |
|---------|---------------|-----------------|
| Hosted tools / MCP | Repo does NOT ship a repo-owned MCP server or repo-root `.mcp.json`. MCP here is host-descriptor / external-tool discipline + shared-venv guardrails. Read host-exposed tool schema files BEFORE invoking | Phase-08 annex `mcp-spec` — `annexes/mcp-spec/repo/schema/<DATE>/schema.json` |
| Doctrine reference packs (observe plans) | Optional `doctrine_reference_injection` merges concept/mechanism/principle reference groups into session packs | [std_doctrine_reference_bundle.json](codex/standards/principles/std_doctrine_reference_bundle.json) + [doctrine_reference_context.py](system/lib/doctrine_reference_context.py) |
| Factory lane (overnight / batch) | Dry-run or run | `./repo-python tools/meta/factory/factory_runner.py --run --dry-run` (see [doctrine_runtime.json](codex/doctrine/doctrine_runtime.json)) |
| System prompts as composed context | Layered: AGENTS.md → CLAUDE.md / CODEX.md → kernel JSON + skills loaded when task matches. Prefer a small routing file over pasting duplicate encyclopedic text | This file's structure is the canonical example |

## Read next

| Agent / situation | File |
|---|---|
| Claude Code | [CLAUDE.md](CLAUDE.md) |
| Codex (start with seed) | [AGENTS.override.md](AGENTS.override.md) → [CODEX.md](CODEX.md) |
| Zenith substrate tasks (any agent) | [codex/CODEX.md](codex/CODEX.md) — Guide Router |
| Assimilation traceability | [docs/agent_bootstrap_assimilation.md](docs/agent_bootstrap_assimilation.md) |
| Controller continuity (shared) | [docs/controller_continuity.md](docs/controller_continuity.md) |
| Bridge OS / runtime | [docs/bridge_operating_system.md](docs/bridge_operating_system.md) |
