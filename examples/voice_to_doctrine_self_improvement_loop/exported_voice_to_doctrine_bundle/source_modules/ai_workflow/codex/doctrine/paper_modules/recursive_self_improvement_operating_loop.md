# Recursive Self-Improvement Operating Loop

Projection class: index
Depends on: local_to_general_propagation, raw_seed_metabolism, raw_seed_substrate, bridge_operating_system, autonomy_runtime_metabolism_loop, principle_population_metabolism, navigation_hologram_theory, agent_entry_surfaces
Authored: 2026-04-27
Governing principles: `pri_049`, `pri_088`, `pri_111`, `pri_115`, `pri_120`, `pri_121`, `pri_124`
Governing concepts: `con_001`, `con_028`
Governing axiom candidates: `axiom_candidate_availability_before_invention`, `axiom_candidate_common_sense_up_propagates`, `axiom_candidate_meaning_is_relational`, `axiom_candidate_standards_shared_grammar`
Primary subdomain: recursive_self_improvement
Secondary subdomains: `propagation`, `telemetry`, `validation`, `checkpoint`, `route_visibility`
Search aliases: recursive-self-improvement loop, operator-gesture to substrate, voice-to-substrate metabolism, propagation operating loop, prompt-shelf-to-checkpoint loop, availability-ladder-to-autocommit pipeline

## TLDR (compressed view)

The recursive self-improvement operating loop is the system's metabolism for converting operator gesture and agent discovery into durable navigable substrate. A model noticing a friction is not enough — the noticing must route through bridge intent extraction, an availability ladder, a smallest reversible substrate edit, schema-governed objecthood (standards / routes / tests), telemetry capture (v3 noticing + aiw:movement v=1 motion), validation discipline (currentness vs semantic vs historical-scar vs forward-gate), and local autocommit checkpointing — so the next agent inherits the improvement without re-deriving it. The system learned during the 2026-04-27 doctrine session not because a model had a good thought, but because each thought was routed into route-visible, tested, validated, version-controlled substrate. This module is the cold-read theory surface over that loop: what the states are, how the lanes compose, what the live case study proved, what false-wins were structurally prevented, and what the next-agent checklist looks like. Compresses with [local_to_general_propagation](local_to_general_propagation.md) (which is the deposit-direction node within this loop) and [raw_seed_metabolism](raw_seed_metabolism.md) (which is the operator-voice intake substrate the loop reads from).

## Intent

The propagation discipline already had a roof at [local_to_general_propagation](local_to_general_propagation.md). The voice intake had a roof at [raw_seed_metabolism](raw_seed_metabolism.md). The runtime loop had a roof at [autonomy_runtime_metabolism_loop](autonomy_runtime_metabolism_loop.md). The bridge runtime had a roof at [bridge_operating_system](bridge_operating_system.md). Each was authoritative for one slice of the metabolism. None was the cold-read entry surface for the **whole loop** — the chain that converts "operator noticed a friction" or "agent surfaced a missing affordance" into route-visible, tested, validated, checkpointed system behavior that future agents can navigate.

The 2026-04-27 doctrine session executed that chain end-to-end across multiple hand-offs: prompt-shelf digest route visibility → live v3 telemetry refresh → availability_before_invention axiom candidate → propagation into A0/B1/B2/B3 prompts → Type A continue-to-file half-built discovery via PEER lane → aiw:movement v=1 standard / parser / tests → terminal-cluster placement rule (after a quoted-example false win) → `--validate --since` cutover (after a clean-but-semantically-broken false win) → local autocommit checkpoint policy and five commits. Every step exposed at least one pattern worth preserving. Without this module, the next agent would rediscover the chain piecewise from five separate authoritative surfaces and miss the composition.

This module is that composition — not the constituent mechanisms. Each constituent retains its own authority.

## Shape

The loop is a state machine over substrate metabolism: each state has explicit owning surfaces, and skipping a state silently degrades the durability of the work.

```text
                            ┌──────────────────────────────────────┐
                            │  operator gesture / agent friction   │
                            │  (raw seed, prompt, pasted trace,    │
                            │   noticed missing affordance)        │
                            └─────────────────┬────────────────────┘
                                              │
                                              ▼
              ┌──────────────────────────────────────────────────────┐
              │  intent extraction                                   │
              │  - preserve voice as intent / pressure / metaphor    │
              │  - distinguish stated / inferred / system goal       │
              │  - challenge stale or faulty framing                 │
              │  Owners: B2 prompt clause; bridge_info_request_v1    │
              └─────────────────┬────────────────────────────────────┘
                                │
                                ▼
              ┌──────────────────────────────────────────────────────┐
              │  availability ladder                                 │
              │  1. local routes / standards / skills / tests / state│
              │  2. half-built / stale / uncommitted substrate       │
              │  3. raw-seed paragraphs / operator voice anchors     │
              │  4. annex prior-art / distillation rows              │
              │  5. bridge research infrastructure                   │
              │  → reuse | finish | import | research | build_new    │
              │  Owners: axiom_candidate_availability_before_invention│
              └─────────────────┬────────────────────────────────────┘
                                │
                                ▼
              ┌──────────────────────────────────────────────────────┐
              │  smallest reversible substrate action                │
              │  - smallest blast radius for the chosen result       │
              │  - schema-governed objecthood, not just breadcrumb   │
              │  - source-of-truth, not generated state              │
              │  Owners: each owning plane's curation skill          │
              └─────────────────┬────────────────────────────────────┘
                                │
                                ▼
              ┌──────────────────────────────────────────────────────┐
              │  validation                                          │
              │  - currentness  (--check, drift vs disk)             │
              │  - semantic     (--validate, contract correctness)   │
              │  - historical   (--validate honest about scars)      │
              │  - forward gate (--validate --since <cutover>)       │
              │  Owners: per-pipeline indexer + tests                │
              └─────────────────┬────────────────────────────────────┘
                                │
                                ▼
              ┌──────────────────────────────────────────────────────┐
              │  telemetry capture                                   │
              │  - v3 up-propagation footer (per-turn noticing)      │
              │  - aiw:movement v=1 sidecar (per-signal motion)      │
              │  - PEER record (curated agent judgment, selective)   │
              │  - agent_execution_trace (action accounting)         │
              │  Owners: prompt_shelf indexers, peer_ledger,         │
              │          agent_execution_trace standards             │
              └─────────────────┬────────────────────────────────────┘
                                │
                                ▼
              ┌──────────────────────────────────────────────────────┐
              │  local checkpoint                                    │
              │  - explicit pathspecs only                           │
              │  - no -A / no `.` / no commit -am                    │
              │  - autocommit by default after coherent validated    │
              │    scoped work; no push by default                   │
              │  Owners: AGENTS.md § Git scope discipline            │
              └─────────────────┬────────────────────────────────────┘
                                │
                                ▼
              ┌──────────────────────────────────────────────────────┐
              │  future retrieval                                    │
              │  - kernel.py --docs-route / --paper-module / --navigate
              │  - art_*_route artifact-kind objecthood              │
              │  - test_docs_route locks the discoverability         │
              │  - movement_index recurrence_key clusters cross-runs │
              │  Owners: documentation_theory_index, route plane     │
              └─────────────────┬────────────────────────────────────┘
                                │
                                ▼
                            ◀── (cycle: future agents extract intent, walk
                                 the ladder, find the prior work via routes,
                                 deposit new lessons via local_to_general_
                                 propagation; the loop runs again)
```

The asymmetry is load-bearing. Each state has explicit owning surfaces, and **skipping a state silently degrades the durability of the work**: skip intent extraction and the loop literalizes operator typos; skip the availability ladder and the loop reinvents existing capabilities; skip objecthood and the loop produces breadcrumbs invisible to the route plane; skip telemetry capture and the loop forgets what it learned; skip the checkpoint and the worktree accumulates uncheckpointed drift. The states are ordered, but each must be performed.

### Per-state automation tier

The eight states do not share an automation posture. Confusing them produces either ungated autonomous mutation (treating "deliberate" states as natural) or ceremonial-only RSI (treating "natural" states as deliberate). The governing phrase distilled from §Live case study #2 below — **"Natural sensing and staging; deliberate substrate promotion"** — names the boundary across the eight states.

| # | State | Automation tier | What that means |
|---|---|---|---|
| 1 | Operator gesture / agent friction | natural | Any substantive task can generate friction; no scaffolding required |
| 2 | Intent extraction | scaffolded-natural | Required by Type A/B prompt templates; absent on ad-hoc threads |
| 3 | Availability ladder | culturally enforced | Doctrine-mandated; no global "consumed-without-depositing" validator (named NOT YET BUILT in [local_to_general_propagation.md](local_to_general_propagation.md) §Missing) |
| 4 | Smallest reversible substrate action | deliberate | Agent / controller chooses and edits; no automation by design |
| 5 | Validation | deliberate | Tests / `--check` / `--validate` must be invoked; not globally automatic |
| 6 | Telemetry capture | scaffolded-natural | v3 footer required by Type A/B prompts on every substantive turn; movement sidecar only when motion is recommended |
| 7 | Local checkpoint | semi-deliberate | Autocommit-by-default policy after validated scoped work (per `AGENTS.md § Git scope discipline`); agent must still act |
| 8 | Future retrieval | natural-after-objecthood | Routes / indexes carry future agents to source automatically once the artifact has `art_*` objecthood |

The boundary is not arbitrary: automating state 4 collapses the safety gate (raw notice becomes mutation); ceremonializing state 1 collapses ambient sensing (only labeled-RSI sessions improve the system). Both failures defeat the loop.

## Ontology / Types & Invariants

### Layer map

The metabolism uses different lanes for different jobs. Confusing the lanes is itself a recurring failure class.

| Lane | Purpose | Trigger | Schema authority | Indexer / consumer |
|---|---|---|---|---|
| **v3 up-propagation footer** | per-turn noticing telemetry | every substantive agent turn | prompt-shelf prompt items + cockpit (8 fields) | `tools/meta/observability/prompt_shelf_uppropagation_index.py` + `_digest.py` |
| **aiw:movement v=1 sidecar** | per-signal typed motion telemetry | turn explicitly recommends substrate motion | [std_aiw_movement_v1](../../standards/std_aiw_movement_v1.json) (10 fields) | `tools/meta/observability/prompt_shelf_movement_index.py` (--check / --validate / --validate --since) |
| **ASK_TYPE_A / bridge_info_request** | bounded evidence pull when a Type B decision is blocked on facts | Type B reasoning blocked, bounded evidence would unblock | [std_bridge_info_request_v1](../../standards/std_bridge_info_request_v1.json) | bridge response packet via Type A controller |
| **PEER propagation record** | curated agent-to-agent reusable judgment | local task taught a reusable peer lesson too exploratory for direct doctrine mutation | [std_peer_propagation_record](../../standards/std_peer_propagation_record.json) | `codex/doctrine/peer_propagation/peer_ledger.json` (append-only-intent) |
| **Axiom candidate** | constitutional-grade pressure, not active doctrine | repeated cross-plane pattern; system-wide pre-test of a deep prior | [std_system_axiom_candidate](../../standards/principles/std_system_axiom_candidate.json) | `obsidian/.../raw_seed/system_axiom_candidates.json` |
| **Paper module** | cold-read subsystem ontology + Rosetta projection | a subsystem boundary that future agents will hit cold | [std_paper_module](../../standards/std_paper_module.json) | `codex/doctrine/paper_modules/_index.json` + builder |
| **docs-route + artifact-kind route** | discoverability + objecthood | any artifact future agents need to navigate to from natural-language queries | [documentation_theory_index.json](../documentation_theory_index.json) + `system/lib/kernel_navigation.py` | `kernel.py --docs-route` / `--navigate` / `--paper-module` |
| **Local git commit** | memory checkpoint after coherent validated scoped work | any coherent unit of work passes its validation | [AGENTS.md § Git scope discipline](../../../AGENTS.md) | local repo state |
| **Push / publication** | remote-sync, PR, GitHub | operator explicitly authorizes | `./checkpoint` script (operator-invoked) | remote `origin/main` |

The most important distinctions in this layer map are:

- **v3 captures noticing; movement captures motion.** Bundling them into one footer (the v4 temptation) loses the per-signal recurrence-key clustering that the digest will project. Keeping them as siblings — never nested — preserves both.
- **Local commit is not publication.** Conflating them produces either uncheckpointed worktree growth (the recurring failure that triggered the autocommit policy update on 2026-04-27) or premature pushes that publish unfinished work.
- **Breadcrumb is not objecthood.** A path appearing in some route's `local_artifacts` is not the same as the path being the canonical target of an `artifact_kind_route`. The first lets the path be cited; the second lets the path be queried by name.

### Live case study — 2026-04-27 doctrine session

Compressed chronology. Each step exposed the structural pattern named in the right column.

| Step | Event | Pattern revealed |
|---|---|---|
| 1 | Operator asked whether prompt-shelf digest was navigable | route-visibility ≠ file existence |
| 2 | Type A walked the ladder; found `documentation_theory_index.json` is source-of-truth, `state/semantic_routing/route_graph.json` is generated state | source-of-truth vs generated projection distinction |
| 3 | Added `art_prompt_shelf_uppropagation_digest` artifact-kind route | breadcrumb → objecthood escalation |
| 4 | Live `--write` produced 17 records → 21 candidate rows from raw_events of this very conversation | the loop is recursive |
| 5 | `axiom_candidate_availability_before_invention` minted with 5 compression bands, 7 deliverables, 10 evidence_refs | axiom-candidate posture (not active doctrine) is the right durability for cross-plane pressure |
| 6 | A0/B1/B2/B3 + cockpit absorbed the availability-ladder clause + voice-as-intent sharpening | propagation = doctrine arrives in the agent's behavior, not just in standards |
| 7 | Type A continue-to-file framing collapsed when the ladder revealed `peer_ledger.json` already existed | capability amnesia is the failure class; availability ladder is the discipline |
| 8 | `aiw:movement v=1` standard + parser + 11 tests + route landed | movement telemetry = sibling, not v4 |
| 9 | First `--write` of `movement_index` reported 6 movement blocks — but 5 were quoted examples from design packets | telemetry parsers must distinguish emitted from quoted; the false-win class was named |
| 10 | Terminal-cluster placement rule + `_classify_blocks()` + 13 new tests | structural prevention via parser logic + standard rule + regression test |
| 11 | `--check` reported clean while semantic violation persisted | currentness ≠ semantic validity; mode separation needed |
| 12 | `--validate` semantic mode added; exit 1 on the historical malformed footer | honest history is non-negotiable |
| 13 | Operator caught: `--validate` always failing makes it ignorable as a gate | another false-win class: gate ignored because all-history fails forever |
| 14 | `--validate --since 2026-04-27T06:10:00+00:00` cutover added | preserve scar, gate forward; a mature pattern in safety systems |
| 15 | Operator: "the commit policy is wrong — local commit is not publication" | the system was conflating preservation with publication, blocking its own metabolism |
| 16 | `AGENTS.md § Git scope discipline` rewritten with autocommit-by-default + push-only-on-explicit-ask | doctrine update before behavior change |
| 17 | Five local commits landed with explicit pathspecs; no push; 15 pre-existing dirty paths excluded | the policy first execution proved the policy correct |

Cumulative outputs: 5 local commits ahead of `origin/main`, 102 pytest pass, `art_aiw_movement_sidecar` + `art_prompt_shelf_uppropagation_digest` route-visible, one historical scar preserved + gated, no push.

### Live case study #2 — natural metabolism via ordinary operator pressure (2026-04-27 morning)

The 06:10 doctrine session above was *deliberately* framed as RSI work — the operator and the controller were jointly authoring substrate, the loop was the explicit topic. A second case study captured ~2.5h later proves the loop also runs **without ceremonial framing**.

| Step | Event | Pattern revealed |
|---|---|---|
| 1 | Operator asked, verbatim: *"have we built a system that can only RSI if it's trying to or can it naturally do it?"* | The question was a question about the system, not a request to do RSI work |
| 2 | A0 surface exploration traced the answer across this module, [reactions_engine.md](reactions_engine.md), [local_to_general_propagation.md](local_to_general_propagation.md), [autonomy_runtime_metabolism_loop.md](autonomy_runtime_metabolism_loop.md), `.claude/hooks/runtime_hook.py`, prompt-shelf captures, `metabolismd doctor` output, `reactions.yaml`, and live `reactions_engine.py status`; emitted v3 up-propagation footer | Substrate-aware threads naturally feed RSI telemetry without intent to RSI; the loop's State 1 (gesture) and State 6 (telemetry) ran with zero ceremony |
| 3 | A B1 instantiation pass distilled the verdict phrase: **"Natural sensing and staging; deliberate substrate promotion"** | Cross-plane constitutional pressure phrasing emerged from ordinary inquiry, not from authored doctrine |
| 4 | The B1 caught a side-effect drift: this module's sibling [reactions_engine.md](reactions_engine.md) §Current state still claimed *"three seed reactions in V1"* while `reactions.yaml` had expanded well past that (live count now bound dynamically via fact `reactions.config.reaction_count` — see [reactions_engine.md](reactions_engine.md) §Current state fact-assertion table) | Live consume-without-deposit failure caught during ordinary inquiry — exactly the gap [local_to_general_propagation.md](local_to_general_propagation.md) §Missing names: "no unified validator that spots 'consumed without depositing'" |
| 5 | A B2 reconciliation pass narrowed the next move to a bounded two-surface refresh (this case study + the reactions_engine.md correction); deferred the axiom-mint, the `consume_without_deposit_detected` reactions source kind, and the `thread_substrate_awareness` taxonomy until repeat signal | State 4 (smallest reversible substrate action) chosen over speculative scaffolding |
| 6 | Operator authorized writes; this very edit lands the case study + the sibling correction, with explicit-pathspec autocommit | The exchange itself becomes the validation receipt for the verdict it produced |

Cumulative outputs (this case study): two doctrine surfaces refreshed (this module + [reactions_engine.md](reactions_engine.md) §Current state), no new modules, no axiom candidates minted, no detectors built. Substrate promotion remained deliberate; sensing and staging stayed ambient. **The case study is the deposit; the verdict phrase is the proposition the deposit is evidence for.**

If the phrase **"Natural sensing and staging; deliberate substrate promotion"** recurs across enough additional decisions to clear the axiom-candidate bar, it should be promoted to `axiom_candidate_natural_sensing_deliberate_promotion`. Until then, it lives inside this module as the per-state automation tier's organizing principle.

### Core invariants

1. **Preserve voice as intent.** The operator's words encode pressure, metaphor, and load-bearing phrasing. Voice preservation is *never* imitation of disfluency, hedging, profanity-as-filler, or stream-of-consciousness disorganization. Translate raw operator gestures into precise system-facing language; preserve the load-bearing phrases verbatim and rewrite the rest with precision.

2. **Availability before invention.** Before authoring new doctrine, standards, skills, prompts, or implementation, route the missing-affordance claim through the availability ladder. Search depth scales with blast radius. Bounded-unavailable is a first-class outcome — not laziness, not exhaustive audit. (See `axiom_candidate_availability_before_invention`.)

3. **Objecthood matters.** A breadcrumb (path in some route's `local_artifacts`) lets the artifact be cited. An artifact-kind route (`art_*` row in `documentation_theory_index.machine_routes.artifact_kind_routes`) lets the artifact be the canonical target of natural-language queries. Choose objecthood when future agents will look for the artifact by name, not by neighborhood.

4. **Validation has four orthogonal questions.** *Currentness* (`--check`): does the projection match disk? *Semantic correctness* (`--validate`): does the projection conform to its contract? *Historical scars*: are pre-cutover violations honest? *Forward gateability* (`--validate --since`): can the gate be wired into a hook without falsing on immutable history? Conflating any two produces a false-win class.

5. **Local commit is preservation; push is publication.** Solo-operator recursive-self-improvement systems are harmed more by uncheckpointed worktree growth than by occasional small unscoped commits. Local autocommit after validated scoped work is the default. Push, PR, GitHub sync are explicit-operator-authorization only.

6. **Do not build projection layers before traffic exists.** Build the substrate (standard, parser, tests, route). Wait for organic emission. *Then* build the digest / atlas. Building a projection over zero data produces a Rosetta Stone for nothing.

7. **Each artifact emits its smallest projection at the file boundary.** The system is a multiresolution projection lattice: large dolls (artifacts), each with standard-governed compression bands, with typed expansion edges back to source. The smallest projections from many artifacts compose into a palm-sized global comprehension layer; the large pieces do not. (See §Technical framing below.)

### Failure classes closed

The 2026-04-27 session caught and structurally prevented eight false-win classes. Each one is now a regression test or a parser warning or a standard rule, not just a remembered lesson.

| Failure class | False win | Structural prevention |
|---|---|---|
| 1 | "JSON is malformed" alarm based on diff display, not actual parse | Always run `jq empty` before assuming malformedness; diff display ≠ semantic state |
| 2 | Breadcrumb-only route visibility mistaken for objecthood | `art_*` artifact-kind route + regression test that authority surfaces include the right files; `documentation_theory_index.machine_routes.artifact_kind_routes` |
| 3 | v3 footer captures lesson / self_prompting_idea / information_demand but not where the noticed thing should move | `aiw:movement v=1` sidecar standard + parser + tests; `recurrence_key` field for cross-row clustering |
| 4 | Movement parser counted quoted examples in design-packet prose as real telemetry | Terminal-cluster placement rule + `_classify_blocks()` + non-terminal advisory warnings; only blocks immediately before final v3 footer with whitespace-only gaps count |
| 5 | `--check` reported clean while nesting / missing-required-field violations existed | `--check` (currentness) vs `--validate` (semantic) mode separation; `semantic_kinds` vs `advisory_kinds` warning split |
| 6 | `--validate` always failing on immutable historical scar makes the gate ignorable | `--validate --since <cutover>` cutover argument; warnings carry `captured_at` so filtering doesn't re-read files; std documents `validation_cutover_policy` |
| 7 | "Never commit unless asked" conflated local checkpoint with publication; worktree grew uncheckpointed | `AGENTS.md § Git scope discipline` rewritten: local autocommit by default after validated scoped work; push only on explicit operator ask |
| 8 | "We need to invent Type A continue-to-file" — but `peer_ledger.json` already existed as half-built receipt lane | Availability ladder + capability amnesia naming; the existing PEER substrate became the answer (compose, don't invent) |

### Technical framing — multiresolution projection lattice

The operator's "reverse Russian doll" metaphor encodes a precise computer-science model. Stated formally:

```text
Let A be the set of artifacts.
Let B be the set of compression bands {tiny, flag, card, context, deep}.
For each artifact a ∈ A and band b ∈ B, a standard S(a) defines a projection:

    π_{a,b}: a → V_{a,b}

where V_{a,b} is bounded but ROUTE-SUFFICIENT: the projection either
(1) preserves the invariants needed to act safely at band b, or
(2) exposes a typed expansion edge to the next necessary surface.

The global comprehension layer at band b is:

    C_b = { π_{a,b}(a) | a ∈ A }

Navigation is materialized-view traversal with edges back to source,
owning standard, validation, related artifacts, and dependent artifacts.

The availability ladder operates over C_b at the smallest band proportionate
to blast radius: it queries the global comprehension layer for existing
capability before any authoring step.
```

Computer-science analogues that compose with this model:

- **Materialized views**: each `π_{a,b}` is a maintained derived view over its source. Standards govern view shape; route-coverage projections audit view presence.
- **Abstract interpretation**: each band is a tier of abstraction over the artifact; deeper bands reveal dependencies, governed implications, counterexamples, and proof obligations.
- **Bidirectional lenses**: the typed expansion edge from V_{a,b} back to `a` (or from V_{a,b} to V_{a,b'} at a deeper band) is a get/put lens preserving relevant invariants.
- **Source maps**: every projection in `C_b` carries provenance back to authored source (raw seed paragraph anchor, paper module section, standard field, code locus).
- **Provenance-aware derived state**: generated state files record `source_fingerprint` so drift is mechanically detectable.
- **Schema-governed compression**: the standards layer is the moulds; the projection layer fits each artifact into its mould; the route layer is the expansion mechanism; the test layer is the proof that the projection still leads back to the right source.

The reverse-Russian-doll insight: the system is **not** one large doll containing nested smaller dolls. It is a **room of many large dolls**, each emitting its own small projection at the file boundary. The small projections compose into the palm-sized global view that fits in an agent's working context. The large pieces stay in the artifacts they belong to and are reached by typed expansion when needed. Standards are what make this composition possible; without standards, projections drift and the global view fragments.

## Code loci

### Relationship to existing doctrine

This module composes with — and does not replace — the following authoritative surfaces:

| Surface | Role in the loop |
|---|---|
| [local_to_general_propagation](local_to_general_propagation.md) (paper module + skill) | The deposit-direction node: where the loop hands learning back to owning planes after each local act. This module is the roof OVER local_to_general_propagation; the propagation paper module remains authoritative for the deposit step. |
| [raw_seed_metabolism](raw_seed_metabolism.md) + [raw_seed_substrate](raw_seed_substrate.md) | The voice-intake pair the loop reads from. Operator gesture enters via raw seed; the loop's first state ("operator gesture / agent friction") often resolves to a raw_seed paragraph, and voice preservation (invariant 1) is governed by the substrate authority. |
| [bridge_operating_system](bridge_operating_system.md) + [autonomy_runtime_metabolism_loop](autonomy_runtime_metabolism_loop.md) | Runtime + bridge composition. Bridge owns ASK_TYPE_A / type_a_evidence_packet contracts (intent-extraction may emit ASK_TYPE_A when bounded evidence would unblock reasoning); the autonomy runtime metabolism (daemon / reactions / always-awake) is the agent-driven counterpart for interactive sessions. |
| [principle_population_metabolism](principle_population_metabolism.md) | The principle-population audit / queue / rubric / drain / merge shape. The loop's "axiom candidate" lane composes with principle population when a candidate is reviewed for promotion. |
| [provider_metabolism_ledger](provider_metabolism_ledger.md) | Provider throughput substrate. Future capability-atlas projection may compose movement_index recurrence_keys with provider population data. |
| [navigation_hologram_theory](navigation_hologram_theory.md) + [agent_entry_surfaces](agent_entry_surfaces.md) | Route plane + entry-surface contract. The loop's "future retrieval" state is implemented via the navigation hologram; entry-surface compression governs that this loop adds only `art_*` artifact-kind routes (not new entry surfaces) for narrow new artifacts. |

Standards directly governing loop states:

| Standard | State governed |
|---|---|
| Meta-doctrine standards: [std_paper_module](../../standards/std_paper_module.json) + [std_agent_entry_surface](../../standards/std_agent_entry_surface.json) | This module's authored shape and projection-class budget; compression-via-projection contract (Rosetta Stone seed) |
| Telemetry + bridge standards: [std_aiw_movement_v1](../../standards/std_aiw_movement_v1.json) + [std_bridge_info_request_v1](../../standards/std_bridge_info_request_v1.json) | aiw:movement v=1 sidecar shape, placement, validation modes; ASK_TYPE_A / type_a_evidence_packet shape |
| [std_peer_propagation_record](../../standards/std_peer_propagation_record.json) | PEER record candidate shape; agent-peer-candidate authority posture |
| [std_system_axiom_candidate](../../standards/principles/std_system_axiom_candidate.json) | Axiom candidate row shape with formal_clause, dense_clause, compression_expansion_bands, deliverables, etc. |

Code loci:

| Path | Role |
|---|---|
| Prompt-shelf telemetry pipeline: [prompt_shelf_uppropagation_index.py](../../../tools/meta/observability/prompt_shelf_uppropagation_index.py), [prompt_shelf_uppropagation_digest.py](../../../tools/meta/observability/prompt_shelf_uppropagation_digest.py), [prompt_shelf_movement_index.py](../../../tools/meta/observability/prompt_shelf_movement_index.py), [prompt_shelf_prompt_lint.py](../../../tools/meta/observability/prompt_shelf_prompt_lint.py) | v3 telemetry indexer + digest projection; aiw:movement v=1 indexer with terminal-cluster + `--validate` + `--since` cutover; prompt-corpus integrity lint. All under `tools/meta/observability/`. |
| [codex/doctrine/documentation_theory_index.json](../documentation_theory_index.json) | Route plane source-of-truth (machine_routes.artifact_kind_routes / situation_routes / file_type_routes / runtime_surfaces) |
| `obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/system_axiom_candidates.json` | Axiom candidate ledger |
| [AGENTS.md](../../../AGENTS.md) | Shared agent doctrine root, including § Git scope discipline |

## Current state

The loop is operationally functional as of 2026-04-27. See Validation receipts below for concrete evidence and §Refresh contract for sidecar regeneration. The historical scar is preserved at `obsidian/prompt_shelf/usage/raw_events/B2_continue/20260427T060553860625--B2--874e0115.json`; routine forward gates use `--validate --since 2026-04-27T06:10:00+00:00`.

## Deliverables (what this subsystem lets a cold agent DO)

- **Classify the current work state** across operator gesture, intent extraction, availability ladder, substrate action, validation, telemetry, checkpoint, and future retrieval.
- **Choose the right deposit lane** for a local lesson: telemetry, movement sidecar, bridge request, peer record, axiom candidate, paper module, route objecthood, or scoped commit.
- **Validate recursive improvement work** by separating currentness checks, semantic validation, historical-scar handling, and forward-gate cutovers before closeout.

A cold agent reading this module gains the capability to:

1. Recognize the loop's eight states (operator gesture / intent extraction / availability ladder / substrate action / validation / telemetry / checkpoint / future retrieval) and identify which state any current task is in.
2. Apply the operational checklist below verbatim, end-to-end, without re-deriving any constituent mechanism.
3. Distinguish currentness (`--check`) from semantic validity (`--validate`) from forward-gate semantics (`--validate --since`) for any pipeline that has both kinds of failure modes.
4. Choose between extending an existing surface and minting a new one, by walking the availability ladder at depth proportional to blast radius (see `axiom_candidate_availability_before_invention`).
5. Decide between local autocommit and pause based on the six-condition all-true rule and the six-condition pause-when rule in `AGENTS.md § Git scope discipline`.
6. Treat any false win caught during a session as a structural-prevention candidate: standard rule + parser detector + regression test + route exposure + validation receipt.

### Operational checklist

```text
[ ] Extract operator intent, not surface literalism (preserve voice as
    intent / pressure / metaphor / load-bearing phrasing — not disfluency).

[ ] Walk the availability ladder before authoring:
      local → half-built → raw-seed/voice → annex → bridge research.
    Depth scales with blast radius.

[ ] Choose the smallest reversible substrate action that resolves the
    intent. Prefer extending existing surfaces over minting new ones.

[ ] If the artifact will be queried by name from natural language, give
    it artifact-kind objecthood (art_* route in machine_routes), not
    just a breadcrumb in some situation route's local_artifacts.

[ ] Add tests for behavior that can regress: route resolution, parser
    classification, validation exit codes, path existence.

[ ] Run currentness checks (--check) and semantic validation
    (--validate) SEPARATELY before claiming the work is clean.

[ ] If validation surfaces a historical scar, preserve it in the
    artifact (immutable receipt) and add a forward gate via
    --validate --since <cutover>; document the cutover in the standard.

[ ] Emit telemetry: v3 footer for noticing on every substantive turn;
    aiw:movement v=1 sidecar ONLY when the turn explicitly recommends
    substrate motion. Movement blocks before final v3 footer with
    whitespace-only gaps; never nested.

[ ] Commit locally with explicit pathspecs after coherent validated
    scoped work. Never -A. Never `.`. Never push without explicit
    operator ask.

[ ] Report: commit hash, paths committed, validation outputs (incl.
    historical-scar acknowledgment), paths deliberately excluded,
    next move.
```

## Gap (what Will is signaling)

The 2026-04-27 doctrine session closed several false-win classes (see §Failure classes closed) but explicitly deferred the next layer of substrate. The Gap section names what is signaled but not yet built — what future agents should treat as scaffolded deliverables (per the operator's prior gesture: "you can always figure out what you need... populate the deliverables, then later actually do it properly").

### Open deliverables

Named, not implemented in this module. Each will become its own bounded pass when the prerequisite traffic / signal accumulates.

| Deliverable | Prerequisite | Owner plane |
|---|---|---|
| Type A continue-to-file Option C (composed receipt) | operator approval; PEER + capture_writer + execution_trace already compose | new skill at `codex/doctrine/skills/agent_runtime/type_a_continue_to_file.md` (~50 lines) + 1 test |
| `prompt_shelf_movement_digest.py` | ≥ 20 terminal movement blocks across ≥ 3 distinct recurrence_keys | sibling to `prompt_shelf_uppropagation_digest.py`; groups by recurrence_key / owning_plane / signal_kind / promotion_boundary |
| Capability atlas projection | movement_digest produces real cross-row clusters | downstream of movement_digest; not a hand-authored ledger |
| Optional B2/B3 prompt clauses for movement emission | observed low organic adoption of aiw:movement sidecar | small one-line invitations; only if telemetry shows agents miss the emission_trigger discriminator |
| `formal_model` field on axiom candidates | repeated demand for inspectable mathematical / typed-logic expression of axiom clauses | extend `std_system_axiom_candidate.json::row_shape.recommended_record_fields`; keep optional |
| Operator-voice compression schema (raw_phrase / intent_preserved / system_translation / do_not_misread_as / owning_plane) | repeated need to preserve voice across long sessions without diary-style accumulation | extend B2 prompt clause OR add new skill; ladder check first against raw_seed_substrate / std_agent_entry_surface |
| Pre-commit / CI gate using `--validate --since 2026-04-27T06:10:00+00:00` | operator decision to wire the forward gate into automation | hook script + standards-registry note |

### Validation receipts

Concrete evidence supporting the claims in this module, captured during the 2026-04-27 session:

```text
Five local commits ahead of origin/main, no push:
  3773975e  doctrine: agent autocommit checkpoint policy + push-vs-commit split
  6e0030a8  bridge: evidence-pull protocol candidate
  ec3b1c62  prompt-shelf: v3 up-propagation index, digest, lint pipeline
  26566720  doctrine: route visibility + availability axiom + aiw:movement v1
  2e4386b8  prompt-shelf: capture receipts (2026-04-27 doctrine session)

Test sweep (most recent run):
  102 passed in 8.55s
    - 24  test_prompt_shelf_movement_index.py
    - 59  test_docs_route.py
    - 9   test_docs_route_prompt_shelf_uppropagation.py
    - 2   test_docs_route_exogenous_aliases.py
    - 5   test_prompt_shelf_uppropagation_index.py
    - 2   test_prompt_shelf_uppropagation_digest.py
    - 3   test_prompt_shelf_prompt_lint.py
    - rest are upstream

Validation modes (post-commit):
  prompt_shelf_movement_index.py --check                                  → clean
  prompt_shelf_movement_index.py --validate                               → exit 1 (historical scar, expected)
  prompt_shelf_movement_index.py --validate --since 2026-04-27T06:10:00+00:00 → exit 0 (forward gate)

Route discoverability (kernel.py --docs-route):
  "aiw movement sidecar"                  → art_aiw_movement_sidecar
  "movement telemetry recurrence_key"     → art_aiw_movement_sidecar
  "noticing telemetry movement telemetry" → art_aiw_movement_sidecar
  "prompt shelf telemetry digest"         → art_prompt_shelf_uppropagation_digest
  "availability before invention"         → sit_system_axiom_candidates
  "up propagation"                        → sit_local_to_general_propagation (broad concept, NOT hijacked)

Movement_v1 cutover timestamp (canonical for forward gates):
  2026-04-27T06:10:00+00:00

Historical scar preserved (immutable receipt):
  obsidian/prompt_shelf/usage/raw_events/B2_continue/20260427T060553860625--B2--874e0115.json
  Violation: nested_movement_inside_uppropagation
  Treatment: preserved + excluded from forward gate via --since cutover
```

Natural-RSI case study #2 (2026-04-27 morning, ~2.5h after 06:10 doctrine session):

```text
Trigger: operator asked an architectural question (not framed as RSI work)
A0 explore capture:    obsidian/prompt_shelf/usage/raw_events/A0_explore/20260427T025314926080--A0--de0cb0e7.json
B1 / B2 pass distilled the verdict phrase:
  "Natural sensing and staging; deliberate substrate promotion."

Drift caught during ordinary inquiry (not during scheduled audit):
  reactions_engine.md §Current state: "three seed reactions in V1"
  reactions.yaml live count:           bound to fact `reactions.config.reaction_count`
                                       (callable provider in derived_fact_hologram.py;
                                       refreshed each build_fact_hologram.py run)
  Sibling correction landed in same checkpoint as this case study.

Bounded refresh scope (state 4 — smallest reversible substrate action):
  - This module: per-state automation tier table + Live case study #2
  - reactions_engine.md §Current state: count-neutral wording + pointer at reactions.yaml
  Deliberately NOT done in this checkpoint:
  - axiom_candidate_natural_sensing_deliberate_promotion (defer until repeat signal)
  - consume_without_deposit_detected reaction source kind (defer)
  - thread_substrate_awareness paper-module candidate (defer)

Loop states exercised without ceremonial RSI framing:
  state 1 (gesture)            ✓ operator question, not RSI ask
  state 2 (intent extraction)  ✓ A0/B1/B2 prompt scaffolding
  state 3 (availability ladder)✓ ladder walk — reuse + finish-half-built selected
  state 4 (substrate action)   ✓ this checkpoint
  state 5 (validation)         ✓ paper-module index builder + tests
  state 6 (telemetry)          ✓ v3 footer on every substantive turn (A0 + B1 + B2 + this)
  state 7 (local checkpoint)   ✓ explicit-pathspec autocommit
  state 8 (future retrieval)   ✓ already route-visible via existing kernel.py --paper-module
```

## What a cold agent should NOT re-derive

The following patterns were already worked out during the 2026-04-27 session (and prior sessions referenced in the constituent paper modules). Skip the rediscovery cost; cite the doctrine instead.

- **Why local commit is not publication.** See `AGENTS.md § Git scope discipline` for the policy and §Failure classes closed item 7 above for the false-win class that motivated the split.
- **Why availability ladder before authoring.** See `axiom_candidate_availability_before_invention` for the constitutional case and §Failure classes closed item 8 for capability amnesia.
- **Why v3 and aiw:movement are siblings, not nested.** See `std_aiw_movement_v1.placement_rules.terminal_sidecar_cluster_rule` and §Failure classes closed item 4.
- **Why generated state is not source-of-truth.** See `documentation_theory_index.json` (source) vs `state/semantic_routing/route_graph.json` (generated) and §Anti-patterns below.
- **Why "preserve voice" ≠ imitate disfluency.** See `axiom_candidate_availability_before_invention.evidence_refs[10]` (the operator's verbatim voice-as-intent clarification) and the B2 prompt clause.
- **Why digests come after traffic.** See §Open deliverables in §Gap below; movement_digest is correctly deferred until ≥ 20 terminal blocks across ≥ 3 distinct recurrence_keys.

### Anti-patterns

- **Do not turn every passing thought into doctrine.** v3 telemetry is the right home for mild reusable insights. Axiom candidates are reserved for cross-plane constitutional pressure. Paper modules are reserved for subsystem boundaries that future agents will hit cold.

- **Do not build a digest before traffic accumulates.** The movement digest is correctly deferred until ≥ 20 terminal movement blocks across ≥ 3 distinct recurrence_keys exist. Building a Rosetta Stone over zero data produces noise, not signal.

- **Do not treat generated state as source-of-truth.** `state/semantic_routing/route_graph.json` is generated; `codex/doctrine/documentation_theory_index.json` is source. Hand-editing generated state is a false win that disappears on the next projection rebuild.

- **Do not encode operator biography, age, university affiliation, emotional state, fatigue, or self-deprecation as doctrine.** The operational fact (solo-operator system; uncheckpointed worktree growth is a system-risk) propagates; private/contextual operator-state details do not.

- **Do not imitate raw operator disfluency under the banner of "preserve voice."** Voice preservation = preserve intent, pressure, metaphor, and load-bearing phrases; translate the rest with precision.

- **Do not use `git add .`, `git add -A`, `git commit -am`, or `./checkpoint`** during agent autocommit work. Explicit pathspecs only. `./checkpoint` (which `git add -A`'s, commits, AND pushes) remains operator-invoked only.

- **Do not push without explicit operator authorization.** Local commit is preservation; push is publication; the two are not the same gate.

- **Do not conflate `--check` (currentness) with semantic validation.** Each pipeline that has both kinds of failure modes should expose both modes separately. A `--check`-clean-but-`--validate`-failing artifact is a real false win.

- **Do not nest aiw:movement inside aiw:uppropagation, or vice versa.** They are siblings. The standard forbids it; the parser detects it; the regression test locks it.

- **Do not treat absence-from-current-context as absence-from-system.** This is the capability amnesia failure mode. The availability ladder is the discipline.

## Refresh contract

This module is a `class:index` paper module per `std_paper_module_v8` projection-class budget. It indexes the loop across constituent surfaces; it does not redefine any constituent's authority. Each constituent retains its own paper module / standard / skill as authoritative.

**Sidecar regeneration**: `tools/meta/factory/build_paper_module_index.py` writes `_index.json`, `_validation_report.json`, `_doctrine_to_paper_modules.json`, and `_route_coverage.json` from this and sibling authored markdown. Builder is idempotent; rerun after any edit.

**Freshness signals**: this module's `code_loci` claims point at constituent paper modules and standards rather than at Python source, so its freshness is governed by the cited paper modules' code-loci freshness rather than direct Python drift. If any cited constituent paper module enters `stale_code_changed`, this module should be re-read for cascading drift.

**Route discoverability**: kernel `--paper-module "<query>"` and `--docs-route "<query>"` resolve via `documentation_theory_index.json` and `system/lib/paper_modules.py`. If natural-language queries about the loop (e.g., "recursive self improvement operating loop", "operator gesture to substrate", "voice-to-substrate metabolism") do not resolve cleanly after authoring + builder run, the narrowest fix is token additions to an existing `machine_routes.situation_routes` row (likely `sit_local_to_general_propagation` for the deposit-direction queries). Add a regression test in `system/server/tests/test_docs_route.py` for any new route exposure.

**Cadence**: this module is `class:index`, not `class:snapshot` — it does not require dated re-authoring. Refresh when:
- a constituent surface (any cited paper module / standard) lands a major revision;
- a new lane joins the layer map (e.g., capability atlas projection lands and becomes a sibling to v3 / movement / PEER);
- the validation cutover timestamp moves (cutover bumps should be rare; record the previous cutover in this module's history when they occur).

**What a cold agent should run after refresh**:

```bash
./repo-python tools/meta/factory/build_paper_module_index.py
./repo-python kernel.py --paper-module "recursive self improvement operating loop"
./repo-python kernel.py --docs-route "recursive self improvement operating loop"
./repo-python tools/meta/observability/prompt_shelf_movement_index.py --validate --since 2026-04-27T06:10:00+00:00
./repo-python -m pytest system/server/tests/test_docs_route.py
```

### Closing

The 2026-04-27 doctrine session was not memorable because a model produced clever output. It was memorable because every clever output was structurally preserved: the operator's pressure became system substrate via standards, routes, tests, telemetry, validation modes, and version control. The next agent reading this paper module does not inherit the cleverness. They inherit the loop. That is the difference between a transient chat and a self-improving system.

The loop runs again as soon as the next gesture arrives.
