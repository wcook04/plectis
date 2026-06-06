# Local-to-General Propagation

**Projection class:** index
**Primary subdomain:** authority_projection
**Secondary subdomains:** surface_language, navigation_fidelity, runtime_cockpit
**Authored:** 2026-04-20
**Governing principles:** pri_111 (paper modules preempt re-derivation), pri_088 (re-read substrate at each compression level), pri_049 (minimum sufficient read graph / controlled routing vocabulary), pri_080 (adapt, not adopt), pri_016 (extract, never replace with compression)
**Governing concepts:** con_001 (holographic self-documentation), con_028 (projection substrate and drift)
**Governing mechanisms:** mech_019 (doctrine router surfaces), mech_034 (failure-class propagation packet)

## TLDR (compressed view)

Local-to-general propagation is the repo's explicit discipline that every local use of a plane artifact — a skill invoked, a paper module authored, a standard consulted, a doctrine node cited, an annex note transferred — is simultaneously a read AND a deposit opportunity back upstream, so the generalised artifact absorbs what the local situation taught about it instead of letting the learning die in a session. The named macro for reusable additions is **generalise-uppropagate**: local change -> owning artifact -> sibling/peer propagation -> generated agent entry when behavior changed -> unified system description when shape changed -> `uppropagate.py intake` -> WorkItem residual capture. The missing executable distinction is now first-class as `mech_034`: when the lesson begins as a local failure, route miss, repeated workaround, stale projection, or agent confusion, it must become a **failure-class propagation packet** before doctrine mutation or `nothing_to_refine`. The packet carries local case, failure class, evidence refs, sibling scan, owner surface, overgeneralization guard, currentness boundary, validation receipt, stop condition, and outcome. The global teleology is explicit now: every local task should help the system navigate, learn, compress, or route itself better, and the closing question is where that learning belongs durably. If the turn-ending question is *"how does this local task help the system navigate, learn, compress, or route itself better?"*, this module is the doctrine roof that answers where the deposit goes. The repo already carries the propagation machinery: iteration-diagnostics on skills ([skill_authoring.md](../skills/doctrine/skill_authoring.md), [paper_module_authoring.md](../skills/doctrine/paper_module_authoring.md) §Governing rules), the closeout skill [local_to_general_propagation.md](../skills/doctrine/local_to_general_propagation.md), maintenance protocols on standards ([std_paper_module.json](../../standards/std_paper_module.json) §`maintenance_protocol`), durable intake ([std_uppropagation_intake.json](../../standards/std_uppropagation_intake.json)), apply gates for doctrine nodes ([raw_seed_apply_loop.py](../../../tools/meta/factory/raw_seed_apply_loop.py)), under-projection signals ([rediscovery_miner.py](../../../tools/meta/factory/rediscovery_miner.py) + [paper_module_candidates.json](paper_module_candidates.json)), the operator-side assimilation reflex in [CLAUDE.md](../../../CLAUDE.md) §Memory discipline + §Assimilation trigger, and the agent-voice deposit lane at [agent_seed_authoring.md](../skills/raw_seed/agent_seed_authoring.md). This module is an index over those mechanisms — it names the propagation lane as a first-class repo practice so a cold agent arrives knowing the reflex (act locally, always hand the learning back to the general, aware that you're in a local situation) without re-deriving it from five places at once.

## Intent

The propagation discipline was already operating across half a dozen surfaces but was nowhere cold-readable as a single practice. A controller arriving at the repo would piece it together from the iteration-diagnostics table in `skill_authoring.md`, the governing-rules section in `paper_module_authoring.md`, the `maintenance_protocol` in `std_paper_module.json`, the assimilation-trigger block in `CLAUDE.md`, the apply-lanes pipeline, and the rediscovery miner — each authoritative for one mechanism, none naming the whole. This index closes that rediscovery cost.

The moment the operator voiced *"whenever you're doing anything you're always propagating that upwards to the general, aware that you're in a local situation"* (anchor in §Gap) is the moment the propagation lane became a named subsystem of the plane rather than a silent side-effect of other lanes. This module is the browse surface over that subsystem; each constituent mechanism retains its own authoritative skill or paper module.

## Shape

```text
local act on a plane artifact
  │
  ├─ CONSUME direction (always):
  │    read the artifact; apply it to the current situation
  │
  └─ DEPOSIT direction (not optional — this is the discipline):
        │
        ├─ skill invoked that didn't fit this local case?
        │    → refine the skill's triggers / workflow / anti-patterns in place
        │
        ├─ paper module read that drifted from shipped code?
        │    → queue entry in _validation_report.json; refresh the drifted section
        │
        ├─ standard consulted that was under-specified?
        │    → maintenance_protocol update; bump schema_version if invariant changed
        │
        ├─ doctrine node cited that was shape-wrong for the local claim?
        │    → raw-seed par_* append + apply-routing lane (never hand-edit the node)
        │
        ├─ rediscovery hit: I just re-derived something already in the plane?
        │    → paper_module_candidates.json entry; coverage_ledger mark
        │
        ├─ Will voiced a principle-class claim this turn?
        │    → raw seed append as-voiced; par_* anchor via --sync-raw-seed
        │
        └─ agent itself noticed a drift signal or synthesized corollary worth surviving?
              → agent_seed authoring lane under explicit attribution in `agent_seed.md`

reusable local addition
  │
  └─ GENERALISE-UPPROPAGATE macro:
        classify local rule
        → update the narrow owner artifact
        → peer-check sibling surfaces
        → regenerate agent entry if default behavior changed
        → update unified self-description if system shape changed
        → record through up-propagation intake
        → capture unimplemented residuals as WorkItems
```

The asymmetry is load-bearing. Consume-only is the failure mode; the generalised artifact stays frozen while local use reveals its gaps. Consume-and-deposit is the discipline; the generalised artifact converges toward the repo's accumulated taste every time it is used.

## Ontology / Types & Invariants

| Name | Kind | One-line purpose | File |
|---|---|---|---|
| Skill iteration diagnostics | Skill section | In-artifact protocol for refining a skill when local use exposes a gap | `codex/doctrine/skills/doctrine/skill_authoring.md` |
| Local closeout protocol | Skill | Reusable end-of-task reflex that routes local learning back into the right general plane artifact | `codex/doctrine/skills/doctrine/local_to_general_propagation.md` |
| Paper-module authoring governing rules | Skill section | Local authoring deposits back into the skill itself, not just into the module | `codex/doctrine/skills/doctrine/paper_module_authoring.md` §Governing rules |
| Standard maintenance_protocol | JSON field | What schema-bump and follow-up refreshes fire when a generalised standard evolves | `codex/standards/std_paper_module.json` §`maintenance_protocol` |
| Assimilation trigger reflex | CLAUDE-adapter section | Routes Will-voiced principles and agent synthesis into raw seed / skill / paper module rather than memory | `CLAUDE.md` §Memory discipline + §Assimilation trigger |
| Raw-seed apply lanes | Runtime | Controller-gated commit of local evidence into general doctrine nodes | `tools/meta/factory/raw_seed_apply_loop.py` |
| Rediscovery miner | Runtime | Flags when repeat local re-derivation signals under-projected generalisation | `tools/meta/factory/rediscovery_miner.py` |
| Paper-module candidates | Backlog | Typed list of under-projected subsystems awaiting first-author | `codex/doctrine/paper_modules/paper_module_candidates.json` |
| Agent-seed authoring lane | Skill | Agent-voice deposit surface for drift signals and synthesized corollaries; never ventriloquizes the operator | `codex/doctrine/skills/raw_seed/agent_seed_authoring.md` |
| Generalise-uppropagate macro | Procedure | Closeout composition for reusable additions: owner update, sibling propagation, agent entry, unified description, intake, and residual capture | `codex/doctrine/skills/doctrine/local_to_general_propagation.md` + `std_uppropagation_intake.json` |
| Failure-class propagation packet | Mechanism | Bounded packet that turns a local failure sample into owner mutation, intake, PEER, Task Ledger capture, already-propagated proof, or residual-free `nothing_to_refine` | `codex/doctrine/mechanisms/mech_034_failure_class_propagation_packet.json` + `std_uppropagation_intake.json::failure_class_propagation_packet_contract` |

Named invariants:

- **Every consume is a deposit opportunity.** Reading a skill and running it is not complete until any local surprise is noted back against the skill. Reading a paper module and acting on it is not complete until any code-loci drift is flagged against the module.
- **A local failure is a sample before it is doctrine.** The failure-class propagation packet prevents both extremes: chat-only repetition and local-irritation overgeneralization. A promotable lesson names the local case, failure class, evidence, sibling scan, owner surface, guard, currentness boundary, validation, stop condition, and outcome.
- **Safety is the envelope, not the ambition cap.** The propagation lane should not collapse broad operator pressure into a token proof case just because one bounded slice is easy to verify. When the local situation safely couples prompt shelf, principles, standards, runtime, tests, generated state, and voice anchors, the correct unit is the largest coherent verified wave the actor can finish now; a tiny slice is valid only when it unlocks or de-risks the larger move.
- **Receipt field names are not receipts.** `stewardship_checked`, `next_best_lane_checked`, and `reentry_condition` are clearance only when they carry action or rejection evidence: the next bounded lane was acted on, rejected with an exact unsafe/claimed/policy-bound/genuinely-absent reason, captured as a durable blocker, or proven residual-free. A line that names those fields while the next useful lane remains safe and unacted is null-pass laundering.
- **Deposit upward, never sideways into memory.** Local learning routes to the generalised plane artifact (skill / paper module / standard / raw seed / apply lane). `memory/` is the narrow user-identity carve-out per `CLAUDE.md` §Memory discipline; it is not a substitute for plane-deposit.
- **Adapters stay pointer-thin.** `CLAUDE.md` and `CODEX.md` may hold only the trigger, the one-line rule, deep-link targets, and the audit reminder for this protocol. If the protocol body needs more than that, it belongs in the skill or this paper-module roof, not in the adapters.
- **Voice lanes stay separated.** Will-voice deposits land in raw seed with a `par_*` anchor (append-only, as-voiced). Agent-voice deposits land in `agent_seed.md` under explicit attribution via `agent_seed_authoring`. Paraphrasing Will into agent-authored prose is voice-theft.
- **Doctrine nodes mutate only through apply lanes.** Local evidence becomes raw-seed paragraphs + shards; the apply-routing lane commits `pri_*` / `con_*` / `mech_*` nodes. Hand-editing a doctrine JSON to encode newly-voiced material is the canonical anti-pattern.
- **The generalised artifact converges, it does not balloon.** A local act can deposit evidence upstream, but the generalised surface tightens — skills collect invariants, standards bump under maintenance_protocol, paper modules refresh or split, raw seed grows only by voice-lineage append.
- **Locality awareness is part of the reflex, not a footnote.** The deposit is framed in "this local situation taught X" language; the generalised artifact does not pretend the local case is the general rule.

Axes of variation:

| Axis | Values |
|---|---|
| Deposit direction | same-file refine / sibling-artifact refresh / raw-seed append + apply lane |
| Voice lane | operator-voice (`raw_seed.md`) / agent-voice (`agent_seed.md`) / historical mixed lineage resolved through the migration ledger |
| Confidence threshold | principle-grade (raw seed) / drift signal (agent seed) / schema-grade (standard maintenance_protocol) |
| Gate owner | self-edit (skill / paper-module refresh) / controller gate (apply-lane doctrine mutation) |

## Code loci

| Role | Loci | What it owns |
|---|---|---|
| Skill iteration | `codex/doctrine/skills/doctrine/skill_authoring.md`, `codex/doctrine/skills/doctrine/paper_module_authoring.md` | In-artifact refinement protocol when local use surfaces a gap |
| Closeout protocol | `codex/doctrine/skills/doctrine/local_to_general_propagation.md`, `codex/doctrine/skills/kernel/navigation_seed.md` | Opening ladder + closing deposition reflex as one paired protocol |
| Standard evolution | `codex/standards/std_paper_module.json` §`maintenance_protocol`, `codex/standards/std_skill.json`, `codex/standards/standards_registry.json` | Schema-bump and follow-up contracts for generalised schemas |
| Voice-to-doctrine pipeline | `codex/doctrine/skills/raw_seed/raw_seed_navigation.md`, `codex/doctrine/skills/raw_seed/agent_seed_authoring.md`, `tools/meta/factory/raw_seed_pipeline.py`, `tools/meta/factory/raw_seed_apply_loop.py` | Append-only voice capture and controller-gated doctrine commit |
| Under-projection signal | `tools/meta/factory/rediscovery_miner.py`, `codex/doctrine/paper_modules/paper_module_candidates.json`, `codex/doctrine/paper_modules/_validation_report.json` (`refresh_queue` / `split_queue` / `first_author_queue`) | Drift and under-projection telemetry |
| Operator-side reflex | `CLAUDE.md` §Memory discipline + §Assimilation trigger, `CODEX.md` adapter block, `AGENTS.md` §shared principles | Routing of local learnings into plane artifacts |
| Apply-gated doctrine mutation | `tools/meta/factory/raw_seed_apply_loop.py` (`apply-routing`, `coverage-enrich`, `edge-migrate`, `edge-validate`), `tools/meta/factory/raw_seed_pipeline.py` `route-review` | Minting and edge-mutation of doctrine nodes from accumulated raw-seed + shard evidence |
| Failure-class packet execution | `codex/doctrine/mechanisms/mech_034_failure_class_propagation_packet.json`, `system/lib/up_propagation.py`, `system/lib/uppropagation_intake.py`, `tools/meta/factory/uppropagate.py`, `tools/meta/factory/task_ledger_apply.py` | Packet shape, dry-run/apply lane, idempotency, WorkItem/PEER fallback, and validation receipt for local failure samples |

## Current state

Snapshot: 2026-04-20.

**Shipped:**

- Each constituent mechanism exists and is exercised: skill iteration-diagnostics tables, paper-module refresh / split queues, standard maintenance protocols, raw-seed metabolism + apply lanes, rediscovery miner, and the agent-seed deposit lane.
- The operator-side reflex is documented in `CLAUDE.md` §Memory discipline (explicit decision tree before any write into `memory/`) and §Assimilation trigger (routing when Will voices a principle-class claim).
- `paper_module_authoring.md` and `skill_authoring.md` are kept current by touch, each authoring referring to the standard rather than restating rules.
- `agent_seed_authoring.md` is the shipped agent-voice lane for drift signals and synthesized corollaries under explicit attribution.
- First worked example now exists in-plane: the 2026-04-20 session-dump assimilation wave used `navigation_seed` before widening, resolved to the propagation + navigation-layer substrates, then promoted the local case into a named closeout skill, thin adapter pointers, and refreshes to the existing roofs instead of leaving the lesson in session prose.
- Second worked example now exists in the runtime plane: the 2026-04-22 09.38 autonomy-runtime self-use pass found duplicate resident `metabolismd` ownership and LaunchAgent/TCC drift while trying to drain overnight bridge work. The local fix landed as a single-resident daemon guard, then the generic packet builder at `system/lib/up_propagation.py` let `autonomy_diagnostics.up_propagation` project reusable deposits upward to `continuous_runtime_layer`, `overnight_autonomous_operation`, the job-launch attribution contract, Codex driver diagnostics, raw seed, and agent seed.
- The same runtime worked example refined the projection contract again: the up-propagation packet now separates archived revision proof (`local_runtime_case`) from the current diagnostics projection (`current_runtime_case`) and reports `runtime_case_delta`, while `autonomy_diagnostics.metabolism_runtime.projection_freshness` marks stale status projections explicitly. This prevents a future seed from treating old duplicate-daemon proof as live truth when the queue has already moved on.
- Third worked example now exists in the entry-surface plane: the 2026-04-24 `--preflight` cold-start self-use pass treated "go above and beyond" as bounded completion. The local kernel command was not enough; the reusable lesson landed in `navigation_seed`, `agent_bootstrap.json`, `agent_entry_surfaces.md`, docs-route tokens, and the governed `above_and_beyond` vocabulary row so future cold agents start from the compact warning / next-safe-command surface instead of rediscovering it from source.
- Fourth worked example now exists in the doctrine-authoring plane: the 2026-05-11 autonomous-seed doctrine pass found `axiom_candidate_common_sense_up_propagates` repeatedly pointing at local failures becoming class-wide repairs, while the closeout skill, PEER, Task Ledger, and intake standard each held part of the process. The reusable object became `mech_034` rather than a new axiom: a code-grounded failure-class packet that routes the sample into owner mutation, intake, PEER, Task Ledger capture, already-propagated proof, or residual-free `nothing_to_refine`.
- Fifth worked example now exists in the public-copy campaign plane: the 2026-06-03 Microcosm copy-wave trace separated public projected fields (`human_gloss`, `claim_ceiling_restated`, `wiring_note` as public links note, and family blurbs) from internal-only `agent_gloss`, then generalized the reusable rule into the closeout skill and intake standard. The durable lesson is field-governed public copy: style/humanizer waves must preserve facts and claim ceilings, worker rewrites remain advisory until controller-reviewed, generated projection reconciliation belongs to owner builders, and moving `drain_source_cluster` closeout work routes through mission-scoped provenance instead of being folded into the copy wave.

**In-progress / partial:**

- There is no unified validator that spots "consumed without depositing" — the propagation reflex is enforced culturally and per-artifact, not globally.
- Agent-seed deposit is shipped but thin in practice; most drift-signal material still dies as session chatter rather than landing as an attributed paragraph.
- `paper_module_authoring.md` only just added an explicit propagation-reflex governing rule (2026-04-20); older authored modules predate that rule and may not have closed their authoring turn with an explicit skill-level deposit.

**Missing / NOT YET BUILT:**

- No telemetry surface counts a "local-act → upstream-refinement" ratio. The rediscovery miner measures one shape of failure (repeat re-derivation); there is no positive-side propagation-rate metric.
- No dedicated frontend lens surfaces this propagation queue; evidence is spread across `_validation_report.json`, `paper_module_candidates.json`, `autonomy_diagnostics.up_propagation`, `agent_seed.md`, and apply-lane plans rather than in one pane.
- No `reactions.yaml` class fires on "controller consumed a skill without depositing a refinement" — that signal does not yet exist in the reactions engine.

## Deliverables (what this subsystem lets a cold agent DO)

- **Run the propagation reflex at turn close.** Before yielding on any local task, enumerate the generalised artifacts consumed and, for each, what the local situation taught about it; edit the generalised artifact if a gap surfaced; say so explicitly in the audit trail either way.
- **Run generalise-uppropagate for reusable additions.** A local prompt/protocol/standard/skill/paper-module/entry/runtime rule is not complete when the local file changes; it is complete when the owner absorbs the rule, sibling surfaces are checked, entry/self-description surfaces are refreshed when needed, intake records the lesson, and residual work is captured.
- **Packetize local failures before promotion.** When the lesson begins as a failure or repeated workaround, use `mech_034` and `std_uppropagation_intake::failure_class_propagation_packet_contract` to bind local case, class, evidence, sibling scan, owner, guard, currentness, validation, stop condition, and outcome before mutating doctrine or claiming `nothing_to_refine`.
- **Run field-governed public-copy campaigns.** When local evidence is a structured public-copy or humanizer wave, prove source-field visibility, map source fields to public labels, split style from claim-ceiling honesty, skip internal-only/private fields, run adversarial overclaim checks, and reconcile generated projections through owner builders before closeout.
- **Reject pro-forma null closeouts.** Treat "already exists", verify-only, settlement-only, threshold-not-met, CAP-only, and no-clean-lane closeouts as one family. If the pass cannot patch the originally requested lane, it still owes the next bounded substrate-care lane or a concrete rejection/capture/proof receipt; `system/lib/egress_compliance.py::detect_no_op_closeout_without_next_action` is the egress-side compliance mirror.
- **Route policy-shaped side notices above generic capture.** Ordinary sidebar TODO pressure can enter through Task Ledger quick-capture, but notices about prompt friction, repeated agent failure, mechanism candidates, policy drift, doctrine drift, or Type A/Type B actor dynamics must preserve their class and route to the owning general surface after capture. The capture is the inlet, not the adoption proof.
- **Do not localize Type B handoff lessons into domain CAPs.** When a sidecar or operator-carried Type B packet names a broad Type A/B, "elsewhere", or propagation failure, classify the handoff itself before filing local-domain captures. If the receiving Type A is the named elsewhere, use the failure-class packet and mutate or capture the owner surface that governs future handoff behavior.
- **Generalize above-and-beyond requests without scope creep or tokenism.** When the user asks for care, passion, common sense, extra effort, or explicitly rejects "one bounded fix at a time," finish as much of the coherent safe wave as the evidence supports, then deposit the reusable correction upstream. Do not wander indefinitely, but do not shrink a system-level complaint into a single symbolic audit when multiple coupled surfaces can be fixed and verified now.
- **Ship cold-start commands as entry surfaces, not just flags.** A new preflight / wake / next-safe-command command must update the navigation ladder, bootstrap pointer, and owning paper module before it counts as discoverable.
- **Ship stable navigation routes as projected surfaces, not just runtime classifiers.** A new `--entry` / docs-route / classifier lane must update `agent_bootstrap.json::situation_routes`, minimum read sets, actor delivery, docs-route machine routes when applicable, skill-registry anchors when a skill owns the lane, generated routing/bootstrap projections, and the governing standard before it counts as generalized.
- **Read active runtime propagation recommendations.** When the local act is an autonomy-runtime self-use pass, inspect `autonomy_diagnostics.up_propagation` before closing; it consumes the reusable `up_propagation` packet contract and turns active-subphase revision evidence into plane-home recommendations without hardcoding a subphase id.
- **Deposit a skill refinement from local surprise.** Follow `codex/doctrine/skills/doctrine/skill_authoring.md` §Iteration diagnostics to add a trigger, adjust a workflow step, or append an anti-pattern.
- **Deposit a paper-module refresh from local drift.** Run `./repo-python tools/meta/factory/build_paper_module_index.py --check --report` to surface the queue entry, then refresh per `paper_module_authoring.md` §Authoring workflow.
- **Deposit a Will-voiced principle.** Run `./repo-python kernel.py --append-raw-seed <family> "<voice>"` followed by `./repo-python kernel.py --sync-raw-seed <family> --live`; cite the new `par_*` in downstream artifacts.
- **Deposit an agent-authored drift signal.** Follow `codex/doctrine/skills/raw_seed/agent_seed_authoring.md` workflow (`--append-agent-seed --author <agent_id>`, `authored_by`, `source_substrate=agent_seed`); never paraphrase Will into this lane.
- **Check under-projection pressure.** Run `./repo-python tools/meta/factory/rediscovery_miner.py` and inspect `codex/doctrine/paper_modules/paper_module_candidates.json` / `_validation_report.json` queues.

## Gap (what Will is signaling)

Will's voiced principle at `par_phase_05_4_agentic_navigation_and_subsystem_convergence_raw_seed__agent_authored_claude_code_2026_04_19_generalized_problem_solving_lane_observations_009` makes the propagation discipline explicit as a **GLOBAL PRINCIPLE**: *"whenever you're doing anything you're always propagating that upwards to the general, aware that you're in a local situation."* Both halves are load-bearing. The "always propagating upwards" half is the deposit reflex this module indexes. The "aware that you're in a local situation" half is the grounding — a local act is not the general; the general is not a local act — and the awareness prevents the reflex from collapsing into "rewrite the generalised artifact as if this one case were representative."

The sibling paragraph at `..._observations_005` carries the same gesture in operator-mode framing: *"there's a protocol of like okay does it already exist as a skill generalised, can i map my localised thing to the generalised and improve the generalised skill, that's always a thing type A must always do at the end."* The "at the end" framing matters — propagation is a closing step, not an opening one. It runs after the local act is mostly done and the accumulated evidence is in hand, which is also why the reflex should be audit-trail-visible rather than hidden inside the main task flow.

I am likely wrong about where the line sits between "every local act deposits" and "let the signal accumulate before depositing." The strong form says every skill use that hit a rough edge should refine the skill the same turn. The weak form says let the plane absorb only load-bearing signals. Will has gestured at the strong form (*"always"*, *"whenever"*); the repo's current machinery supports the weak form (no propagation-rate telemetry, reliance on operator and agent discipline). This module preserves both readings rather than forcing a choice.

## What a cold agent should NOT re-derive

- The propagation reflex is a named subsystem indexed here, not an implicit cross-cutting discipline. Its mechanisms are listed in `Code loci`; do not reinvent them under new names.
- Voice lanes stay separated: operator-voice in raw seed with `par_*`, agent-voice in `agent_seed.md` via `agent_seed_authoring`. Paraphrasing Will into agent prose is voice-theft, covered in `CLAUDE.md` §Memory discipline.
- Doctrine nodes (`pri_*`, `con_*`, `mech_*`) mutate only through apply lanes. Propagation deposits raw-seed paragraphs and shards; apply-routing commits nodes. Do not hand-edit a doctrine JSON to encode a newly-voiced principle.
- `memory/` is the user-identity carve-out only. Local learnings about skills, subsystems, external references, Will's voice, or agent observations route to plane artifacts, not to memory.
- This module is `projection_class: index` — a browse surface over many siblings. It does not replace any listed subsystem paper module or skill; each constituent remains the authority for its mechanism.
- The propagation reflex does not require a new validator or lens to be observed. It runs at authoring time, with the generalised artifact open alongside the local act.
- Failure-class promotion is not a mood or a final-report paragraph. It is a packet (`mech_034`) with owner, guard, validation, and outcome; if the owner is premature, the packet becomes PEER or Task Ledger debt rather than doctrine.
- Sidecar-localization collapse is not solved by appending more local-domain CAPs. A Type B / sidecar packet can carry both a local execution payload and a meta-payload about handoff behavior. Type A must classify both and route the meta-payload through the handoff / propagation owner surface when present.
- A cold-start command is not discoverable merely because `--help` prints it. If it changes the first safe move for future agents, the entry ladder and compressed start packet must point to it.
- A runtime classifier match is not discoverable merely because one smoke phrase returns the right lane. If the route matters to cold agents, the compressed bootstrap/docs-route/routing surfaces must carry the same stable id and command, and runtime matching should consume those projected rows.

## Refresh contract

Refresh when:

- A new propagation mechanism ships (e.g. a `/station/<lens>` propagation pane; a new `reactions.yaml` class that fires on consume-without-deposit; a telemetry surface counting propagation rate).
- The failure-class propagation packet (`mech_034`) changes its required fields, outcome set, validation sequence, or owner-selection rule.
- `std_uppropagation_intake.json::failure_class_propagation_packet_contract` adds or changes a reusable campaign class such as `structured_public_copy_campaign_generalization`.
- `skill_authoring.md` or `paper_module_authoring.md` changes its iteration-diagnostics or governing-rules posture in a way that shifts the propagation reflex.
- `std_paper_module.json::maintenance_protocol` or a sibling standard's maintenance_protocol changes its schema-bump or follow-up contract.
- `CLAUDE.md` §Memory discipline or §Assimilation trigger changes the operator-side reflex.
- A new `agent_seed.md` section lands whose shape argues for a second propagation-lane index (e.g. a substrate-reference-mining-specific variant).
- Will voices an extension or reversal of the global principle anchored at `par_phase_05_4_..._observations_009`.
- A new kernel cold-start, preflight, wake-packet, or next-safe-command surface ships and should become part of the generalized opening / closeout loop.
- A new stable runtime route or classifier behavior ships and should become part of the generalized compressed entry / docs-route / routing surface.
- The generalise-uppropagate macro changes its owner sequence, entry-surfacing rule, intake binding, or residual-capture obligations.

Stale signals:

- Any cited code locus 404s.
- A sibling paper module begins claiming ownership of the whole propagation reflex, which would mean this index should split or deprecate.
- The operator-side reflex in `CLAUDE.md` §Memory discipline contradicts any Ontology invariant listed here.
