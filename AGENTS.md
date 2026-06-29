# AGENTS.md - Plectis

Reading this as a person? The human map is [README.md](README.md); this file
is the agent entry contract.

This root is a public executable atlas of an AI-native workflow and research
runtime: 88 bounded components across formal proof, agent reliability and
safety, research and forecasting, projection-drift control, validators, work
landing, and continuity. Each component has a runner or replay, source loci,
evidence class, receipt path, and authority ceiling.

Treat that mechanism atlas as the product and the local project operating
substrate as its inspection layer. A user can bring a project folder, initialize
`.microcosm/` state, index files, discover patterns, propose routes, inspect
route explanations, record work transactions, observe events, and inspect
evidence only when drilldown is needed.

It is small on purpose, but it is not a synthetic safety proxy. The public root
should make the macro architecture legible through real, runnable substrate:
project, catalog, pattern, standard, route, work, event, evidence, explanation,
assimilation, imported macro bodies, and exported macro-shaped bundles.
It is an executable research prototype and developer tool, not hosted-service,
production-readiness, provider-execution, source-mutation, private-system,
formal-proof-correctness, benchmark-score, or financial-advice authority.

## Fast Entry For Cold Agents

**Arrived with a goal? Convert it into your first correct action before
absorbing anything:**

```bash
PYTHONPATH=src python3 -m microcosm_core comprehend --first-action "<your goal>" --format text
```

It returns one graph-backed contract: the runnable command, the owning
component, the validator that proves it, the shipped receipts, the stop
condition, and the do-not-edit boundary. [FIRST_ACTION.md](FIRST_ACTION.md)
demonstrates this across a goal battery — localization, change-shaped goals,
authority refusals, vocabulary traps — and is regenerated from the live
compiler, so the examples are compiler output, not prose.

If this is your first touch in a standalone clone and you have no task yet, do
not start by absorbing the organ inventory. First prove the local entry path
and the public authority membrane:

1. Read `README.md` for the human map and install mode. In that README, use
   the `Choose a route` table and `How the result stays honest` before opening
   raw receipts or the long organ inventory.
2. From the repository root, run the bounded cold-clone probe before any
   install step:

```bash
./bootstrap.sh
```

   It validates the first-wave fixture and boundary floor, writes ignored
   `.microcosm/cold_clone_probe.json` evidence, and points back to the README
   map. Use `./bootstrap.sh --dry-run` when you need to see the exact command
   without writing the ignored receipt.
3. From the repository root, make the console command available with
   `make install`. If you cannot use `make`, run
   `python3 -m pip install -e '.[test]'` directly; if you cannot install, use
   the source form `PYTHONPATH=src python3 -m microcosm_core <command>`.
4. Run the standard smoke target before opening raw receipts:

```bash
make smoke
```

The smoke target writes ignored receipts under `.microcosm/smoke/`, validates
them, and prints a compact terminal summary. A healthy run includes
`Plectis smoke check: pass`, `authority: pass`, `workingness: clear`, and
`served status: pass`. If you are inspecting each output, use the same commands
by hand:

```bash
plectis hello .
plectis hello --reader cold_cloner .
plectis hello --reader reviewer .
plectis hello --reader skeptical_reviewer .
plectis hello --reader agent .
plectis hello --reader domain_specialist .
plectis first-screen --card .
plectis comprehend --first-action "<goal>"
plectis comprehend --first-contact
plectis comprehend --organ <organ_id>
plectis tour --card .
plectis status --card .
plectis authority --card
plectis workingness --card
plectis legibility-scorecard
```

The reader aliases are shortcuts into existing first-screen branches, not new
routes: `cold_cloner` / `cold-cloner` maps to the public GitHub visitor branch,
`interesting_parts` / `interesting-parts` maps to that same public visitor
branch for "what is interesting here?" questions,
`skeptical_reviewer` / `skeptical-reviewer` / `reviewer` maps to the safety/evals branch,
and `agent` / `type-a-agent` maps to the repo-reading agent branch.
`domain_specialist` / `domain-specialist` is the specialty reader branch; it
points to the generated organ specialty index without claiming domain
correctness or expert review. The card echoes the requested alias or route id
for copy/paste while resolving it to the selected branch.

Read those outputs as the first contract: `plectis hello` is the no-write
human card, `plectis first-screen --card` is the compact JSON reader map,
`plectis comprehend --first-action "<goal>"` is the goal-shaped entry (one
graph-backed First Correct Action contract: action, owner, validator, receipts,
stop condition, do-not-edit boundary — demonstrated in
[FIRST_ACTION.md](FIRST_ACTION.md)),
`plectis comprehend --packet-atlas` is the navigable menu of comprehension
packets (pick the one matching your goal: self_model, first_contact, authority,
organ_cluster, math, claim_trace, flow, mutation_plan, path),
`plectis comprehend --self-model` compiles the WHOLE substrate into one
budgeted packet so you comprehend every family, the real-vs-thin calibration,
and what not to claim at once (`--profile whole_substrate_map` for every
organ essence), `plectis comprehend --first-contact` is the source-body-free
comprehension read pack that answers "what is this substrate, what does each
organ do, and what may I trust" without rereading source (drill in with
`plectis comprehend --organ <organ_id>`, trace a claim with
`plectis comprehend --slice claims --organ <organ_id>`, and prove the whole
surface comprehends with `plectis comprehension-assay --whole-system`),
`plectis tour --card` is the shared state-writing behavior proof,
`plectis status --card` is the compressed public evidence map,
`plectis authority --card` is the claim ceiling, `plectis workingness --card`
is the failure envelope, `plectis observe --card` is the compact
route/work/event/evidence handoff, and `plectis legibility-scorecard` is the
cold-reader comprehension check. These commands do not create release, hosting,
proof, production, provider-call, source-mutation, or financial-advice
authority.

## Default Reflexes

These are passive defaults: you invoke them yourself the instant the trigger
holds. No one has to tell you. They exist because the most common failure here
is reasoning about the whole substrate from the one slice you happened to open.

- **First-action reflex.** If you have a concrete goal (or were handed one) and
  you are about to grep, glob, or open source to figure out where to start, run
  `plectis comprehend --first-action "<goal>"` first. It names the owner, the
  runnable command, the validator, the receipts, and the stop condition; source
  search before that contract is almost always wasted or unsafe reading.
- **Comprehension reflex.** If you ever catch yourself assessing, summarizing,
  scoring, or judging Plectis from only the part you looked at (the tell:
  "based on the part I worked on…"), or you have just arrived cold, then before
  you answer run `plectis comprehend --self-model` — add
  `--profile whole_substrate_map` to read every organ's essence at once.
  Comprehend the whole substrate first, then speak.
- **Mechanism-before-impression reflex.** If the question is specifically how
  impressive Plectis is, what the components actually do, or whether any family
  (for example finance) is thin, run `plectis comprehend --slice mechanism`
  first (source-only clone:
  `PYTHONPATH=src python3 -m microcosm_core comprehend --slice mechanism`). It
  returns every organ's real mechanism — what it computes, verifies, and
  rejects — one line each, across the whole substrate. The proven failure is
  forming the verdict from the nearest surfaces you opened (wrappers, line
  counts, one-line glosses) and emitting that as judgement.
  `finance_forecast_evaluation_spine`,
  `finite_erdos_denominator_certificate_strike`,
  `agent_sabotage_scheming_monitor_replay`, and `batch8_audio_level_rms_port`
  are sentinels whose mechanism is invisible from the gloss — they are tells,
  not the whole catalogue, so read the mechanism slice over every organ before
  concluding. A skeptical reviewer or evals reader starts here, not at `tour`
  or `hello`.
- **Calibration-before-claim reflex.** If you ever are about to state how good,
  complete, ready, or impressive something is, first read its `claim_ceiling`
  and the self-model's `thin_or_projection_surfaces`. Infer quality from the
  evidence; never assert it. The thinness is surfaced on purpose, not hidden —
  most organ runners are exact-copy macro bodies, and the self-model says so.
- **Custody-before-trust reflex.** If you ever are about to treat an organ's
  runner as deep owned code, check `runner_custody_basis` first. An exact-copy
  macro body is comprehended via registry metadata and receipts, not by reading
  the copy as if it were authored here.
- **Escalate-only-when-needed reflex.** If you ever are about to open a source
  file, confirm you are mutating or proving. Otherwise stay in the
  source-body-free read packs. When unsure which packet to open,
  `plectis comprehend --packet-atlas` is the menu.

Before the full test floor, run `make check` for the fastest public preflight.
It should print `Plectis preflight: organ evidence-class registry loads
cleanly.` Before publishing, handing off, or treating the standalone clone as
verified, run `make ci`. It is the public GitHub Actions entry and expands to
editable install, public tests, source-form smoke, and package-install smoke
verification.

Do not launch multiple raw `pytest` processes against this root in parallel
unless each one uses its own `--basetemp`. The Makefile targets already isolate
pytest scratch roots per run; direct parallel subsets must do the same or they
can race while copying fixture trees if they share a basetemp. The standalone
pytest config disables pytest's cache provider so direct runs do not write
`.pytest_cache` into the checkout.

The standalone clone does not currently provision Black or Ruff in the default
or `.[test]` dependency path. Treat a missing `python -m black` / formatter
module as expected unless `pyproject.toml` changes. For organ edits, preserve
local style and verify with `python -m py_compile` for touched Python files,
focused pytest with an isolated `--basetemp`, JSON validity or owner builders,
and the relevant checker commands. Do not add formatter commands to closeout
claims unless package metadata provides them.

If you need a bounded standalone review artifact, run
`make standalone-export EXPORT_OUT=/tmp/plectis-export`. This
writes a candidate folder plus `receipts/release/release_export_receipt.json`;
it is not part of `make ci`, performs heavier outside-root smoke checks, and
still keeps `release_authorized=false` until a separate human release decision
exists.

Before handing off or reviewing that artifact as a standalone clone, validate
the exported root itself:

```bash
cd /tmp/plectis-export/plectis
make ci
```

That cold-clone check proves the exported package can install, test, and smoke
from its own root. It does not authorize release; the release receipt remains
the authority boundary until a separate operator decision exists.

After the compact route is green, use `skills/cold_start_navigation.md` for the
shortest validation ladder. Use the inventory below only as a public runtime
index, not as a substitute for running the commands.

## Live CLI Registry Boundary

Treat `plectis --help` as the bounded first-screen console-command registry.
It is not the full drilldown inventory. In a source-only checkout, use
`PYTHONPATH=src python3 -m microcosm_core --help` for the same first-screen
registry without installing the console script. The organ inventory below also
names route labels, bundle handles, fixture validators, and paper-module
contracts; drilldown commands remain callable by exact name when a route card,
test, or inventory row names them, but they are not guaranteed to appear in
root help. If a label is not listed in root help, use the shipped lens command,
package tests, fixture validator, or exact drilldown command named by the
owning route instead of inventing a CLI path from the label.

## Real Substrate Posture

Plectis is the public repo form of the macro system, reorganized so a cold
reader can run and inspect it without inheriting the private root's historical
mess. Public should carry private by default: import, refactor, or export as
much of the macro substrate as possible into this tree. Use synthetic fixtures
only as regression wrappers, negative cases, or toy inputs around a real
mechanism.

The hard exclusion set is narrow: secrets and credential-equivalent live
access (`.env` files, API keys, tokens, passwords, private keys, cookies,
browser profiles, keychains, account sessions, and direct credential-bearing
payloads), raw operator voice, slurs or abusive wording, private personal
material, and other clearly unsafe or non-releasable content. Do not turn
"private state" or "release authority" into a generic excuse for metadata-only
stand-ins. Hosted launch and recipient sends are separate operational
decisions; they do not block this repo from carrying real source-available
content.

Any `body_copied=true` claim must point at a real target file and a verified
source-to-target import record. A source ref, provenance pointer, digest of an
already-existing validator, activation score, or maturity label is not an
imported macro body.

## Accepted Public Runtime Spine

This is the public entry inventory over `core/organ_registry.json` and
`core/organ_evidence_classes.json`: accepted public runtime organ records
with receipt-index status. Those counts are inventory-only route-alignment metadata:
`accepted_current_authority`, organ counts, and adapter-backed counts are not product progress, release readiness, product completeness, proof
authority,
private-root equivalence, or whole-system correctness. These rows do not authorize release, and the prediction and market organs are
evidence boundaries, not trading or financial advice.

Do not read organs from this index alone. The generated atlas is the contract:

- **[AGENT_ROUTES.md](AGENT_ROUTES.md)** — the generated task-class route
  table for agents: task class, relevant organ(s), first command, authority
  ceiling, evidence/receipt ref, stop condition, and drilldown target.
- **[ORGANS.md#microcosm-at-a-glance--every-organ-in-one-line](ORGANS.md#microcosm-at-a-glance--every-organ-in-one-line)** —
  the generated one-line organ ladder, grouped by canonical family order with
  Entry & Reveal first.
- **[ORGANS.md](ORGANS.md)** — the comprehension card for every organ: what it
  makes visible (plain language), what an agent runs it for, its first command,
  its evidence class, and what it does **not** authorize.
- **[ORGANS.md#find-your-specialty](ORGANS.md#find-your-specialty)** — the
  generated human specialty index; use it when the reader starts from a domain
  rather than an agent task class.
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — the system at a glance: the local
  runtime loop, the claim/evidence loop, the kernel primitives, and how the
  seven families sit on one shared spine.

The atlas is regenerated from substrate with
`PYTHONPATH=src python3 scripts/build_organ_atlas.py --write` and gated by
`tests/test_organ_atlas.py`; do not hand-edit `AGENT_ROUTES.md`,
`ORGANS.md`, `ARCHITECTURE.md`, or `atlas/agent_task_routes.json`.
Drilldown CLIs such as `plectis reveal` and `plectis spatial-simulation` are
documented per organ in [ORGANS.md](ORGANS.md). The accepted organs cluster into
generated families in [ORGANS.md#families](ORGANS.md#families). Do not copy that
family inventory into AGENTS; agents enter through [AGENT_ROUTES.md](AGENT_ROUTES.md),
while the first faithful inventory pass is the generated
[one-line organ ladder](ORGANS.md#microcosm-at-a-glance--every-organ-in-one-line)
and humans can also browse through [ORGANS.md#find-your-specialty](ORGANS.md#find-your-specialty).

## Concept And Mechanism Entry

When a Plectis task asks to read, populate, or refine concepts and
mechanisms, use the entry surface instead of starting from the extracted
pattern inventory. First open `plectis first-screen <project>` and read
`doctrine_effect_frame`; it now exposes `CONCEPTS` and `MECHANISMS` as
authority-boundary handles, not ceremonial doctrine labels.

The concept floor is `standards/std_microcosm_concept.json`; it governs typed
vocabulary boundaries with source refs, relationships, payload shape, omission
receipts, and anti-claims. The mechanism floor is
`standards/std_microcosm_mechanism.json`; it governs reusable state, proof,
routing, or doctrine transformations with validator attachment. Both standards
point back to this agent-entry section and the first-screen doctrine frame.

Use `core/public_standard_pressure.json` for the populated local pressure rows
`concept_handle_requires_entry_surface` and
`mechanism_handle_requires_runnable_contract`, plus
`concept_mechanism_requires_population_specimen_loop` for the specimen-backed
population rule.

Do not stop at the standards. Continue through
`atlas/entry_packet.json::concept_mechanism_entry_route.population_specimens`.
Those rows are the specimen-backed loop: each specimen binds a concept role to a
mechanism role, names source refs, relationship shape, payload shape,
anti-claims, omission receipt, validator refs, and the public/private authority
boundary. Use the specimen whose validator matches the pressure:
first-screen route shape, executable grammar standard shape, standards-meta
organ mapping, or voice-to-doctrine refinement. Only create a new packet if none
of those existing lanes can carry the pressure without distortion.

- Standard shape: `plectis executable-doctrine-grammar validate-standards-bundle --input examples/executable_doctrine_grammar/exported_standards_bundle --out /tmp/microcosm-executable-doctrine-grammar`
- Organ-to-standard mapping: `plectis standards-meta-diagnostics run-diagnostics-bundle --input examples/standards_meta_diagnostics/exported_standards_meta_diagnostics_bundle --out /tmp/microcosm-standards-meta-diagnostics`
- Local pressure -> owner surface -> validation -> closeout loop: `plectis voice-to-doctrine-self-improvement-loop run-bundle --input examples/voice_to_doctrine_self_improvement_loop/exported_voice_to_doctrine_bundle --out /tmp/microcosm-voice-to-doctrine`

## Rules

1. Start with `README.md`, then run `skills/cold_start_navigation.md` if you
   need the shortest validation route.
2. The human first-screen text projection is `plectis hello <project>`.
   It opens the cold-entry card without writing `.microcosm/`, mutating source
   files (`source_files_mutated=false`), calling providers, or proving local
   behavior. The shared
   state-writing behavior proof is `plectis tour --card <project>`:
   repo -> `.microcosm` plus the first-screen route card. The full drilldown
   tour is `plectis tour <project>`, and the explicit rebuild loop is
   `plectis compile <project>`. The ten-minute tour should compress
   compile state, Python lens, spine, authority, workingness, prediction, market boundary, corpus, trace repair,
   repair-loop curriculum, formal evidence cells, proof-loop depth, verifier-lab
   execution spine, work landing replay, durable agent work landing replay, view quality, projection safety, drift control,
   circuit attribution, route cleanup, projection import map, import projector, stripping guard,
   standards control, hook intervention coverage, replay gauntlet,
   MCP tool-authority replay,
   benchmark lab, legibility
   scorecard, intake, reveal,
   observatory, and evidence drilldown into one real-substrate route with a
   receipt ref and no release, hosting,
   credentialed provider-call, unsafe source-mutation,
   proof-authority, secret-export, or financial-advice authority.
   Reader-typed branches live in
   `atlas/entry_packet.json::reader_first_screen_routes`: public GitHub
   visitors go from the shared entry map to the local behavior proof and
   authority ceiling, safety/evals readers go from the shared local card to
   status, authority card, and workingness card,
   hiring reviewers go to the legibility scorecard plus the local card, and
   peer developers go to the local card plus `plectis observe --card <project>`;
   use `plectis observe <project>` only when full event rows are needed.
   Those branches route attention; they do not create release, proof,
   production, hiring, or safety-evaluation authority.
   The Python route loop is `plectis python-lens <project>`; it should expose
   path-level Python roles, package roots, readiness checks, and route rows
   without source bodies, provider calls, source mutation, package-quality
   claims, or static-analysis authority claims.
   The public spine loop is `plectis spine`; it should expose the accepted
   runtime organs, first-run command path, counts, evidence policy, explicit
   `evidence_class` rows, and
   secret-only boundary without forcing a cold reader into raw receipts first.
   The pattern route-readiness loop is `plectis pattern-route-readiness
   validate-bundle`; it should validate the exported route-readiness selector
   overlays before any mined pattern row is treated as selectable. It keeps
   pattern selection organ-first and fixture-bound, with no standalone public
   leaf, release, publication, or private-data equivalence authority.
   The workingness map is `plectis workingness`; it should compare each
   organ's required substrate against observed evidence and owning-standard
   failure modes.
   The runtime intake loop is `plectis intake`; it should connect the macro
   projection intake board, formal-math readiness extension board, reveal
   bundle, body-import verification rows, and runtime evidence refs so ready,
   landed, bridged, copied, and consumed projection cells are visible without
   secrets or credential-bearing payloads.
   The public reveal loop is `plectis reveal`; it should show the ten-minute
   path from repo compile to route explanation, observatory, evidence, and
   secret-only boundary.
   `mission_transaction_work_spine` also exposes checkpoint lane receipts:
   scoped commit is the normal lane for isolated owned paths, broad checkpoint
   requires explicit operator authorization, and suspected private leakage
   routes to hard stop.
   The cold-reader route loop is `plectis cold-reader-route-map
   run-route-map-bundle`; it should validate first-run route order, command
   refs, docs refs, receipt refs, and the public-runtime authority boundary.
   The expanded local loop is `plectis tour --card <project>`,
   `plectis status --card <project>`, `plectis observe <project>`,
   `plectis explain <project> <route_id>`, and
   `plectis evidence list <project> --limit 25`, then
   `plectis evidence inspect <project> <ref>` for a listed project evidence
   ref. Older macro stage labels such as init, index, architecture, route
   selection, and work-run are conceptual
   stages inside the current commands, not separate live top-level commands.
   Public input bundles and organ demos are compatibility/regression surfaces,
   not the product center.
   The `public_reveal_walkthrough` organ is the exception that binds entry
   legibility itself to fixtures, commands, negative cases, and receipts.
   The `macro_projection_import_protocol` organ is the import membrane for
   future macro patterns: use `plectis macro-projection-import-protocol` to
   import real non-secret bodies when they are copyable, and to demote
   metadata-only cells when they are not. Use `plectis macro-projection-import-protocol plan --input examples/macro_projection_import_protocol/exported_projection_import_bundle`
   before a new import slice; it is the non-writing intake board for per-cell
   source refs, target refs,
   validation refs, copy policy, body-import verification, omitted material, and
   ready/blocked status. It must also expose `projection_status`,
   `cell_state`, `action_required`, landed evidence refs, status counts, and
   open-actionable count so a landed cell is not reread as unfinished work. Use
   `plectis intake` when a cold reader needs the public runtime bridge from
   that intake board into spine/reveal/evidence.
   The `voice_to_doctrine_self_improvement_loop` organ is the public self-update
   membrane: it validates local pressure -> owner surface -> mutation or
   capture -> validation -> closeout -> re-entry, while rejecting raw operator
   voice export, private thread body export, direct doctrine-node edits,
   receipt-only progress, and global promotion without owner validation. Use
   `voice-to-doctrine-self-improvement-loop` when a Plectis pass needs to
   prove it imported the macro system's learning loop instead of only adding
   pattern receipts.
   Authority ceiling: start with `plectis authority --card` for the compact
   public ceiling, then open `plectis authority` only when a claim needs the
   full map. The authority loop should aggregate status,
   spine, intake, reveal, accepted organs, hard public boundaries, safe
   local-only exceptions, evidence refs, `evidence_class` rows, and anti-claims
   into one source-open authority map. `accepted_current_authority` is not an
   evidence-strength claim. It is the entry point for checking what Plectis
   may not do: release,
   publish, host, call providers with credentials, mutate source unsafely,
   export secrets or credential-equivalent payloads, make general proof claims,
   or offer financial advice. It must not treat private-state language as a
   generic reason to replace real non-secret bodies with placeholders.
   The workingness loop is `plectis workingness`; it should expose one
   failure envelope per organ: required substrate, observed evidence class,
   known failure modes from the owning standard, and concrete future-work
   targets. It is not a maturity board, activation label, release signal, or
   score-based progress surface.
   The prediction lens loop is `plectis prediction-lens`; it should project
   `prediction_oracle_reconciliation` as a public synthetic reasoning surface
   with target-universe gating, CP1 bifurcation resolution, CP2 prediction
   rows, oracle diff grading, bounded dossier mutation, negative-case coverage,
   source/projection refs, and no-advice/no-live-data boundaries.
   The market-boundary loop is `plectis market-boundary`; it should project
   market-facing prediction reasoning as a public claim contract: observation
   versus forecast labels, base-rate/prior-context gates, scenario-tree gates,
   confidence-band uncertainty, timestamp/freshness boundaries, and decision
   policy that is not trading or investment advice. It must not use live market
   data, export private portfolio or account state, call providers, claim
   performance, publish, host, mutate source, or imply release authority.
   The corpus lens loop is `plectis corpus-lens`; it should project
   `corpus_readiness_mathlib_absence_gate` as a public formal-math
   corpus/toolchain surface with Mathlib import absence, absent-corpus blocks,
   translation-smoke-only rows, consumer gating, negative-case coverage, and
   metadata-only authority before retrieval or proof-witness work.
   The trace-repair lens loop is `plectis trace-lens`; it should project
   formal-math verifier feedback as public metadata: failure classes, trace
   grades, repair routes, negative cases, cold-rerun promotion gates, and
   omission/authority ceilings. It must not expose proof bodies,
   oracle-needed premise ids, provider payloads, Lean/Lake proof execution,
   human-approval proof authority, source mutation, secret export, or
   release authority.
   The verifier repair-loop lens is `plectis repair-loop`; it should turn
   trace rows into an explicit public curriculum transition table: capture the
   verifier failure, classify it, route a metadata-only repair, require a cold
   rerun, and promote only a receipt-backed metadata cell. It must not expose
   proof bodies, oracle-needed premise ids, provider payloads, Lean/Lake proof
   execution, human-approval proof authority, source mutation, private
   equivalence, or release authority.
   The formal evidence-cell loop is `plectis evidence-cells`; it should
   resolve proof-adjacent public language to explicit metadata cell ids,
   receipt refs, source-anchor status, negative cases, and authority ceilings.
   It must reject unknown cells, missing source anchors, embedded proof bodies,
   private refs, general theorem-solution claims, Lean/Lake proof authority,
   provider calls, source mutation, secret export, and release authority.
   The proof-loop depth lens is `plectis proof-loop-depth`; it should show
   the public metadata-only chain from corpus boundary through premise
   retrieval, tactic availability, target-shape routing, verifier trace repair,
   cold rerun, evidence-cell resolution, and verifier-lab execution-spine
   routing. It must not export proof bodies, oracle-needed premise ids,
   provider payloads, benchmark scores, Lean/Lake proof execution,
   theorem-solution claims, source mutation, private equivalence, or release
   authority. The verifier-lab execution-spine lens is
   `plectis verifier-lab-execution-spine-lens`; it should expose bounded
   Lean/Lake transition rows, CP2 downstream rerun effects, Evolve rerun
   acceptance, tool return-code evidence, and secret-exclusion status without
   turning tool execution into general proof authority.
   The work landing replay loop is `plectis landing-replay`; it should
   expose dirty-tree landing lanes, scoped commit versus broad checkpoint
   boundaries, metadata-blocked recovery, blocker refs, ledger finalizer refs,
   and negative cases. It must not mutate Git, stage unrelated dirty paths,
   treat broad checkpoint as authorized without the operator, export private
   source bodies, claim HEAD advanced when it did not, or imply release
   authority.
   The durable agent work-landing replay organ is
   `durable_agent_work_landing_replay`; use `durable-agent-work-landing-replay`
   to validate the exported work landing replay bundle. It must show owned-path
   claims, validation refs, validation-before-commit ordering, scoped commit
   attempts, HEAD-advance gates, metadata-blocked recovery, Task Ledger blocker refs, and Work Ledger
   finalizers without mutating Git, staging unrelated paths, exporting private
   bodies, claiming a commit landed without evidence, or implying release
   authority.
   The research replication rubric artifact replay organ is
   `research_replication_rubric_artifact_replay`; use
   `research-replication-rubric-artifact-replay` to validate synthetic paper
   capsules, artifact hash plans, grader reports, cold rerun receipts, ablation
   diffs, failure taxonomies, and cost/runtime ceilings. It must not reuse
   original-author code, leak hidden rubrics or private paper bodies, accept
   report-only success, claim benchmark performance, run unbounded compute
   search, grade final answers only, or imply publication/release authority.
   The `world_model_projection_drift_control_room` organ is the runnable public
   drift-control lane: use `world-model-projection-drift-control-room` to
   validate synthetic projection rows with source signals, source refs, repair
   routes, validation refs, public replacements, and metadata-only authority
   ceilings. It must not inspect private runtime bodies, export provider
   payloads, mutate source, repair live routes, promote doctrine, claim source
   authority, or imply release authority.
   The `spatial_world_model_counterfactual_simulation_replay` organ is the
   runnable public spatial replay lane: use
   `spatial-world-model-counterfactual-simulation-replay` or
   `spatial-simulation` to validate synthetic scene states, action traces,
   predicted states, transition diffs, oracle checks, sensor packet refs,
   rare-event labels, fidelity limits, and limitation labels. It must not
   export private video or raw sensors, operate robots or AVs, claim real-world
   geography, sell a simulator product, treat generated video as sole
   authority, claim benchmark scores, or imply publication/release authority.
   The `materials_chemistry_closed_loop_lab_safety_replay` organ is the
   runnable public autonomous-science lab-safety lane: use
   `materials-chemistry-closed-loop-lab-safety-replay` to validate synthetic
   candidate materials, safety screens, simulator assays, active-learning
   decisions, cold replay refs, projection protocol, negative cases, and
   no-wetlab authority ceilings. It must not export wetlab protocols,
   hazardous synthesis steps, reagent quantities, controlled or bioactive
   targets, live lab credentials, robot commands, private lab notebooks, live
   assay data, discovery claims, benchmark scores, or release authority.
   The `mechanistic_interpretability_circuit_attribution_replay` organ is the
   runnable public circuit-attribution lane: use
   `mechanistic-interpretability-circuit-attribution-replay` or
   `circuit-attribution` to validate toy prompt refs, sparse feature ids,
   machine-readable graph nodes and edges, replacement-model approximation
   scores, causal inhibition and injection deltas, sufficiency labels,
   faithfulness limits, contradiction cases, and cold replay refs. It must not
   export private model weights, raw activation dumps, proprietary prompts,
   hidden chain-of-thought, provider payloads, private model internals,
   benchmark scores, model-transparency product authority, or imply
   publication/release authority.
   The `agent_monitor_redteam_falsification_replay` organ is a drilldown-only
   public monitor/redteam regression lane: use `replay-gauntlet` in the
   product path, and use `agent-monitor-redteam-falsification-replay` only when
   inspecting the regression bundle. It validates synthetic trajectories,
   monitor verdicts, adversarial probe refs, escalation refs, body-omission refs,
   mitigation refs, and cold replay refs. It must not export private
   chain-of-thought, internal code, exploit details, credentials, live agent
   traffic, provider payloads, monitor product performance claims,
   control-eval scores, source mutation, or release
   authority.
   The `agent_sabotage_scheming_monitor_replay` organ is a drilldown-only
   public scheming-monitor regression lane: use `replay-gauntlet` in the
   product path, and use `agent-sabotage-scheming-monitor-replay` only when
   inspecting the regression bundle. It validates synthetic episodes, action
   traces, per-step monitor scores, counterfactual benign replays, cold replay
   receipts, and negative cases before sabotage-monitor language is admitted.
   It must not export live sabotage instructions, real credentials or account
   identifiers, exploit details, private chain-of-thought, raw harmful
   payloads, deployment-risk claims, provider payloads, source mutation, or
   release authority.
   The `agent_sandbox_policy_escape_replay` organ is the runnable public
   sandbox/security policy lane: use `agent-sandbox-policy-escape-replay` or
   `replay-gauntlet` to compute public `agent_execution_trace` spans from
   action requests, pre-execution policy verdicts, side-effect diffs, rollback
   receipts, cold replay receipts, and negative cases before sandbox-security
   language is admitted. It must not
   export real secrets, live network targets, raw environments, host filesystem
   paths, executable escape payloads, provider payloads, security benchmark
   claims, source mutation, or release authority.
   The `indirect_prompt_injection_information_flow_policy_replay` organ is the
   runnable public indirect prompt-injection information-flow lane: use
   `indirect-prompt-injection-information-flow-policy-replay` or
   `replay-gauntlet` to validate synthetic source trust labels, taint graph
   rows, pre-action policy verdicts, sanitized output refs, cold replay
   receipts, and negative cases before prompt-injection language is admitted.
   It must not export real account material, secrets, raw prompt bodies,
   credentials, hidden system messages, provider payloads, source mutation,
   live tool calls, benchmark claims, or release authority.
   The `agentic_vulnerability_discovery_patch_proof_replay` organ is the
   runnable public patch-proof vulnerability lane: use
   `agentic-vulnerability-discovery-patch-proof-replay` or `replay-gauntlet`
   to validate synthetic targets, issue hypotheses, trace evidence, abstract
   exploitability refs, patch diffs, regression tests, verifier receipts,
   sandbox policy verdicts, false-positive triage, cold replay, and negative
   cases before vulnerability-discovery language is admitted. It must not
   export live targets, real CVE exploitation, weaponized payloads,
   credentials, network exfiltration, actionable exploit steps, provider
   payloads, source mutation, benchmark claims, or release authority.
   The `agent_memory_temporal_conflict_replay` organ is the runnable public
   `agent_execution_trace` refactor over memory temporal-conflict rows: use
   `agent-memory-temporal-conflict-replay` or `replay-gauntlet` to validate
   ADD, UPDATE, DELETE, and NOOP memory decisions, conflict-edge refs,
   stale-downgrade refs, metadata-only private refs, paired memory-on/off cold
   replay receipts, and answer-delta refs. It must not export raw transcripts,
   auto-promote private memory candidates, let stale memory override newer
   scope, treat memory as source authority, accept vector recall without an
   evidence handle, credit final-answer-only deltas, adopt active injection,
   call providers, mutate source, or authorize release.
   The `sleeper_memory_poisoning_quarantine_replay` organ is the runnable
   public body-free persistent-memory security policy refactor: use
   `sleeper-memory-poisoning-quarantine-replay` or `replay-gauntlet` to
   validate source capsule refs, provenance-bound write proposals, quarantine
   verdicts, later retrieval influence gates, rollback audit refs, cold rerun
   receipts, and negative cases. It must not export private memory bodies or
   raw transcripts, import live user memory, promote untrusted context into
   trusted memory, claim benchmark security, call providers, mutate source, or
   authorize release.
   The `mcp_tool_authority_replay` organ is the runnable public tool-authority
   lane: use `mcp-tool-authority-replay` or `replay-gauntlet` to validate
   body-free public tool manifests, capability scope refs, call argument hashes,
   approval token refs, side-effect ledger refs, rollback refs,
   instruction/data split refs, cold replay receipts, and negative cases. It
   must not access live MCP accounts, export credentials or provider payloads,
   obey tool output as instruction, accept unapproved side effects, claim
   benchmark safety, mutate source, or authorize release.
   The `proof_derived_governed_mutation_authorization` organ is the runnable
   public governed-mutation authorization lane: use
   `proof-derived-governed-mutation-authorization` or `replay-gauntlet` to
   validate synthetic intent capsules, proof cells, visible policy verdict refs,
   ephemeral execution identity refs, side-effect diff refs, rollback receipts,
   cold replay receipts, and negative cases. It must not use standing
   credentials, access live cloud/accounts, export proof bodies or provider
   payloads, claim benchmark safety, mutate source, or authorize release.
   The `belief_state_process_reward_replay` organ is the runnable public
   process-reward evidence lane: use `belief-state-process-reward-replay` or
   `replay-gauntlet` to validate the source-faithful public agent-execution
   trace over observation digests, typed belief-state summaries, predicted next
   evidence, verifier or feedback refs, process rewards, outcome rewards,
   trajectory groups, cold replay receipts, and negative cases. It must not
   export hidden reasoning, use hidden gold labels, rely on neural-judge-only
   labels, claim benchmark performance, run live RL, call providers, mutate
   source, or authorize release.
   The view-quality action-map loop is `plectis view-quality`; it should
   expose one typed next-action row per requested view, including missing and
   partial rows, plus a hot-action rollup that is explicitly a projection and
   not the whole census. It must not export private screenshot paths, control
   browsers, import private UI state, claim complete frontend quality, mutate
   source, call providers, or imply release authority.
   The projection-safety audit loop is `plectis projection-safety`; it should
   expose omission receipts, named drilldowns, owner routes, source refs, and
   per-projection authority ceilings for the compressed public lenses. It must
   not export private source bodies, proof bodies, provider payloads, raw
   private paths, source mutation authority, public/secret export claims,
   or release authority.
   The market-boundary loop should be included in projection-safety and
   authority checks before any market-facing public claim is treated as
   evidence.
   The projection-drift control loop is `plectis drift-control`; it should
   expose drift rows with source signals, repair routes, validation refs, and
   explicit no-live-repair/no-source-authority/no-doctrine-promotion ceilings.
   It must not inspect private runtime bodies, mutate source, perform live
   route repair, export provider payloads, promote doctrine, or imply release
   authority.
   The route-cleanup contract loop is `plectis route-cleanup`; it should
   expose first-contact, context-pack, generated-region, option-surface, Work
   Ledger, scoped landing, seed reentry, and public/private cleanup rows with
   owner routes, validator refs, and explicit authority ceilings. It must not
   delete routes, hand-edit generated regions, mutate source, export private
   bodies or provider payloads, promote doctrine, or imply release authority.
   The projection import-map loop is `plectis projection-import-map`; it
   should name each macro-pattern-to-public-lens projection row, what was
   copied, cleaned, omitted, validated, and bounded by authority ceiling. It
   must separate body imports from metadata projections and reject provenance,
   activation, maturity, or fixture/projection refs as proof that a body was copied.
   It must not automate imports, export private bodies, expose proof bodies or
   provider payloads, mutate source, or imply release authority.
   The public import-projector contract loop is `plectis import-projector`;
   it should turn the next macro import into candidate-selection,
   public-manifest, secret stripping, body-import verification,
   runtime-binding, and validation-closeout rows with source refs, target refs,
   copied-body status, omitted material, validation refs, and per-row authority
   ceilings. It must not treat metadata, provenance, maturity, activation, or
   public fixture/projection refs as imported bodies; export private bodies; expose
   proof bodies or provider payloads; mutate source; or imply release
   authority.
   The compression profile option-surface loop is `plectis
   option-surface-lens`; it should consume
   `compression_profile_governed_option_surface` through the import-projector
   contract and expose profile choice as command, endpoint, receipt, sidecar,
   validation, and authority rows. It must not switch profiles, auto-select
   options, export private context or sidecar bodies, hand-edit generated
   regions, mutate source, claim lossless projection, or imply release
   authority.
   The public/private stripping guard loop is `plectis stripping-guard`; it
   should name the export-denial rows for private source bodies, proof bodies,
   provider payloads, raw private paths, example secrets, financial advice,
   source mutation, release, and private-root equivalence. It is a read-model
   only; it must not claim complete secret scanning or authorize publication.
   The standards-control loop is `plectis standards-control`; it should tie
   the standards registry, public standard pressure, validator receipt coverage,
   fixture manifests, acceptance commands, docs, authority ceilings, and
   projection safety into one public read-model. It must not make the registry
   source authority, claim complete standards coverage, call providers, mutate
   source, claim secret export, or imply release authority.
   The hook intervention coverage loop is `plectis hook-coverage`; it should
   compress `agent_route_observability_runtime` receipts into public hook-shadow,
   route-compliance, actor-axis, anti-pattern debt, and route-lease intervention
   rows with mapped repair classes and hook-shadow denial cases. It must not
   read live operator state, provider payloads, browser/HUD/cockpit state,
   mutate Task Ledger, authorize pattern
   assimilation, certify runtime behavior, or imply release authority.
   The same organ owns the computer-use action-trace replay path:
   `plectis agent-route-observability-runtime validate-computer-use-bundle --input examples/agent_route_observability_runtime/exported_computer_use_action_trace_bundle --out /tmp/microcosm-computer-use` validates synthetic observations,
   affordances, actions, pre-action authority verdicts, state transitions,
   recovery receipts, cold replay, and negative cases without live browser
   control, accounts, credentials, external network mutation, raw screenshots,
   benchmark claims, source mutation, or release authority.
   The bridge-continuity loop is `plectis bridge-phase-continuity-runtime`;
   it should validate synthetic transport continuation packets, heartbeat boundaries,
   resource-pressure blocking, resume-once semantics, duplicate-resume rejection,
   worker-skip dedupe, closeout transition receipts, and private-state scans.
   It must not claim live bridge transport health, provider or UI uptime,
   operator HUD/browser state, phase runtime state, work landing, source
   mutation, or release authority.
   The replay-gauntlet loop is `plectis replay-gauntlet`; it should expose
   synthetic agent-reliability replay episodes across benchmark integrity,
   monitor falsification, sabotage/scheming, sandbox escape, MCP/tool authority,
   indirect prompt injection, temporal memory conflict, and sleeper-memory
   poisoning. It must not run live agents or tools, export real secrets, import
   real user memory, authorize sandbox escape, claim benchmark performance,
   prove complete security, mutate source, call providers, or imply release
   authority.
   The repository benchmark transaction lab is `plectis benchmark-lab`; it
   should expose two synthetic issue/patch fixtures, oracle diff grading,
   FAIL_TO_PASS and PASS_TO_PASS-style guards, misleading-test denial, scoped
   diff receipts, workitem admission, and provider-slot cooldown decisions. It
   must not claim SWE-bench performance, mutate live repos, call providers,
   import private issues, export private repositories, authorize broad
   checkpointing, prove production delivery rate, or imply release authority.
   Its rows are synthetic transaction boundary rows, not benchmark scores,
   score-based progress, maturity, readiness, or release evidence.
   The cold-reader legibility scorecard is `plectis legibility-scorecard`;
   it should map the public reveal to five reader questions, six runnable
   checkpoints, endpoint parity, evidence refs, and negative cases. It must
   not prove reader understanding, claim private-root equivalence, publish,
   call providers, mutate source, export benchmark scores, prove mathematical
   correctness, or imply release authority.
   Its rows are checkpoint and boundary rows, not score-based progress,
   maturity, readiness, or release evidence.
   The `prediction_oracle_reconciliation` organ is the prediction-engine
   fixture lane: use `prediction-oracle-reconciliation` for synthetic CP1/CP2,
   oracle diff, and dossier-mutation checks only.
   The `standards_meta_diagnostics` organ is the terminal standards coverage
   lane: use `standards-meta-diagnostics` to verify organ-to-standard mappings,
   runtime contracts, receipt refs, and authority ceilings without turning the
   diagnostic into registry source authority.
   The `research_replication_rubric_artifact_replay` organ is the synthetic
   research-replay lane: use `research-replication-rubric-artifact-replay` for
   public artifact-rerun evidence, declared artifact-hash roster membership,
   rubric boundaries, and no-benchmark/no-private leakage checks only.
   The `cold_reader_route_map` organ is the executable entry-map lane: use
   `cold-reader-route-map` to verify the ten-minute first-run path before
   widening docs, reveal views, or route commands. It is not route-registry
   authority.
   The `formal_math_readiness_gate` organ is the formal-math intake boundary:
   use `plectis formal-math-readiness-gate plan --input fixtures/first_wave/formal_math_readiness_gate/input` to inspect the
   `formal_math_readiness_extensions` board before retrieval or proof witness
   work. It reports closed-premise coverage, tactic probe availability,
   target-shape routing admissibility, context budget posture, selected
   pattern ids, and macro-intake refs without running Lean/Lake.
   The `corpus_readiness_mathlib_absence_gate` organ is the formal-math
   corpus/toolchain guard: use `corpus-readiness-mathlib-absence-gate` to make
   Mathlib import absence explicit, mark translation-smoke rows as non-proof
   metadata, and block absent-corpus or Mathlib-dependent consumers before
   retrieval or proof-witness work.
   The `mathematical_strategy_atlas_hypothesis_scorer` organ is the pre-oracle
   strategy layer: use `mathematical-strategy-atlas-hypothesis-scorer` to map
   public problem features to a known strategy enum, expand retrieval terms,
   and record typed strategy-selection misses without proof authority.
   The `tactic_portfolio_availability_probe` organ is the tactic callability
   layer: use `tactic-portfolio-availability-probe` to validate scoped
   compile-status metadata, Mathlib absence handling, unprobed tactic
   references, and proof/provider/benchmark/release overclaim boundaries.
   The `target_shape_tactic_routing_gate` organ is the pre-execution tactic
   admissibility layer: use `target-shape-tactic-routing-gate` to validate
   that target shapes only admit available, probed tactics through public route
   metadata before Lean/Lake runs.
   The `lean_std_premise_index` organ is the closed public premise-index lane:
   use `lean-std-premise-index` to validate Init-sourced declaration metadata,
   namespace coverage, split eligibility, retrieval terms, and proof/Mathlib
   leakage boundaries before retrieval machinery consumes the index.
   The `formal_math_premise_retrieval` organ is a real import slice through
   that membrane: use `formal-math-premise-retrieval` to validate public
   Lean/Std premise metadata, term scoring, context budgets, and strategy
   gates, but it must not claim proof authority.
   The `formal_math_verifier_trace_repair_loop` organ is the runnable verifier
   self-repair slice: use `formal-math-verifier-trace-repair-loop` to
   validate verifier failure classes, trace grades, repair actions,
   failure-mode ledger updates, curriculum deltas, cold-rerun promotion gates,
   and negative-case denials without proof authority.
   The `formal_evidence_cell_anchor_resolver` organ is the claim-boundary
   slice: use `formal-evidence-cell-anchor-resolver` to validate public
   evidence-cell ids, source-anchor refs, machine-anchor metadata, and
   theorem-correctness denials without proof authority.
   The `undeclared_library_prior_symbol_classifier` organ is the payload-boundary
   proof-symbol slice: use `undeclared-library-prior-symbol-classifier` to
   classify known qualified library symbols outside `allowed_premise_ids` as
   `UNDECLARED_LIBRARY_PRIOR`, preserve cited-unallowed premise precedence as
   `PREMISE_BUDGET_VIOLATION`, and keep proof bodies/private refs out.
   The `ring2_premise_retrieval_precision_recall_harness` organ is the
   retrieval-quality boundary: use `ring2-premise-retrieval-precision-recall-harness`
   to compute synthetic Ring-2 precision/recall, require an adversarial decoy
   miss, and separate retrieval misses from proof failures despite premise hits
   without leaking labels into provider context.
   The `agent_benchmark_integrity_anti_gaming_replay` organ is a body-free
   benchmark integrity regression drilldown, not product-spine substrate: use
   `agent-benchmark-integrity-anti-gaming-replay` to validate locked
   evaluators, contamination checks, file-access logs, trusted-reference
   scoring, held-out guards, benchmark-case roster binding, and anti-gaming
   negative cases without claiming a benchmark score, exposing private
   issue/oracle bodies, authorizing provider execution, or counting fixture
   verdicts as product progress.
   The `provider_context_recipe_budget_policy` organ is the provider-context
   budget boundary: use `provider-context-recipe-budget-policy` to validate
   fixed recipe byte ceilings, ordered section fill, omitted-section manifests,
   graph roles, and reducer deliverable types without calling providers or
   exposing proof/oracle bodies.
   The `formal_math_lean_proof_witness` organ is the only bounded Lean/Lake
   execution lane: use `formal-math-lean-proof-witness` for the tiny public
   Lake witness bundle, and keep receipts inside the payload boundary.
   The `verifier_lab_kernel` organ is the formal-math composition root: use
   `verifier-lab-kernel` to validate bounded Lean witness execution, tactic
   portfolio/routing evidence, verifier trace repair, provider-hypothesis
   quarantine, CP2 action candidates, and bounded Evolve candidates in one
   leak-proof receipt. It must keep verifier success, oracle comparison,
   provider suggestion, contract rejection, retrieval miss, CP2 translation,
   and Evolve candidates separated.
   Architecture primitives must resolve through the project-local pattern
   surface: catalog observations become `.microcosm/patterns.json`, routes
   carry `pattern_refs`, and explanations show resolved pattern bindings.
   Explanations must also resolve public standard pressure from
   `core/public_standard_pressure.json`; do not inline private doctrine or
   create a second pattern taxonomy.
   The causal chain must stay stable across `plectis route`,
   `plectis explain`, `plectis work run`, `plectis observe`,
   `plectis graph`, and `plectis evidence`: route refs, pattern bindings,
   standard bindings, work state, event ids, and evidence refs should agree.
   The local observatory is the first browser-facing cockpit for that chain:
   keep causal-chain sections legible before raw JSON drilldowns. It must also
   surface the Python lens and spine/intake/reveal bridge in browser form,
   including `/project/python-lens`, `/tour`, `/spine`, `/authority`, `/prediction`,
   `/market-boundary`, `/corpus`, `/trace`, `/repair-loop`, `/evidence-cells`, `/proof-loop-depth`, `/verifier-lab-execution-spine`, `/landing-replay`,
   `/view-quality`, `/projection-safety`, `/drift-control`, `/route-cleanup`, `/projection-import-map`,
   `/import-projector`, `/option-surface-lens`, `/stripping-guard`, `/standards-control`, `/hook-coverage`,
   `/replay-gauntlet`, `/benchmark-lab`, `/legibility-scorecard`, `/intake`, `/reveal`,
   projection-status counts,
   open-actionable intake count, and release-authority ceiling, so a cold reader does not need to
   discover the JSON commands before seeing why the runtime is coherent.
3. Fixtures Are Tests: fixtures under `fixtures/first_wave/**` are examples,
   bootstrap data, and negative cases. Do not treat fixture-only behavior as
   product-complete runtime behavior.
4. Receipts Are Evidence: generate receipts by running validators or
   `bootstrap.sh`; do not edit receipts by hand. `bootstrap.sh` writes ignored
   local `.microcosm/cold_clone_probe.json` evidence by default; pass `--emit`
   only when refreshing an owned tracked receipt on purpose.
5. Treat `core/organ_registry.json`, `core/acceptance/first_wave_acceptance.json`,
   generated receipts, and public paper modules as public-root navigation
   surfaces.
6. Do not widen Lean/Lake. `mathematical_strategy_atlas_hypothesis_scorer`,
   `tactic_portfolio_availability_probe`,
   `target_shape_tactic_routing_gate`, `lean_std_premise_index`,
   `formal_math_premise_retrieval`,
   `formal_math_verifier_trace_repair_loop`,
   `formal_evidence_cell_anchor_resolver`,
   `undeclared_library_prior_symbol_classifier`,
   `ring2_premise_retrieval_precision_recall_harness`,
   `agent_benchmark_integrity_anti_gaming_replay`, and
   `agent_monitor_redteam_falsification_replay`,
   `agent_sabotage_scheming_monitor_replay`, and
   `agent_sandbox_policy_escape_replay`,
   `indirect_prompt_injection_information_flow_policy_replay`, and
   `agentic_vulnerability_discovery_patch_proof_replay`, and
   `provider_context_recipe_budget_policy` are
   metadata/retrieval/admissibility/metric/context-budget lanes only, and
   `formal_math_lean_proof_witness` authorizes only the tiny public witness
   fixture in a temporary workspace, and `verifier_lab_kernel` authorizes only
   a public leak-proof verifier-lab receipt with no private proof bodies,
   provider proof authority, oracle-to-forward contamination, arbitrary
   Evolve, source mutation, benchmark claims, or release/publication work.
   `corpus-lens` is public evidence over corpus readiness receipts:
   it may make Mathlib import absence and blocked consumers legible, but it
   must not become Lean/Lake execution, Mathlib proof authority,
   corpus-completeness authority, benchmark authority, provider authority, or
   release authority.
   `standards_meta_diagnostics` is public runtime diagnostics: it may diagnose
   public standards/runtime/receipt coverage, but it must not claim registry
   source authority, private macro access, release operations, provider calls,
   proof authority, or whole-system correctness.
   `research_replication_rubric_artifact_replay` is a runnable
   research-replay harness: it may diagnose artifact replay completeness,
   declared artifact-hash roster binding, grading rubric boundaries, rerun
   evidence, and private-leakage guards, but it must not claim external
   benchmark performance, original-paper replication, publication operations,
   provider calls, secret export, or release authority.
   `cold_reader_route_map` is executable public route evidence: it may diagnose public
   entry route order, command refs, docs refs, and receipt refs, but it must not
   claim route-registry authority, source mutation authority, private macro
   access, release operations, provider calls, trading advice, or whole-system
   correctness.
7. Do not treat prediction fixtures as trading or financial advice. The
   `prediction_oracle_reconciliation` organ may validate synthetic reasoning
   mechanics only; it must not imply investment advice, live market data,
   provider calls, performance claims, publication, or release authority.
8. Do not import parent-repository-only tools, host-local state, prompt bodies,
   provider payloads, operator threads, HUD/browser/cockpit state, or old
   scratch public-root content as source authority.
9. Do not add release, hosted-public, publication, recipient, credentialed
   provider-call, or secret-export surfaces from this root.
10. Do copy real non-secret macro bodies into public runtime code, fixtures,
   docs, or exported bundles when they are the mechanism being released. Do not
   copy secrets, credential-equivalent payloads, private operator text, or
   provider payload bodies. Any macro material that enters Plectis must pass
   the `macro_projection_import_protocol` boundary with source refs, target
   refs, body-import verification, omission receipts, and validation receipts.
11. Keep research-prototype posture explicit. Do not describe this root as
   production infrastructure, a hosted service, or a release-ready agent
   platform.

## Receipt Floor

Every new validator receipt must include `status`, `secret_exclusion_scan`,
`authority_ceiling`, `anti_claim`, and `receipt_paths`. Organ receipts also
include `organ_id` and `fixture_id`. Legacy `private_state_scan` is a
compatibility surface only; do not introduce it in new receipt contracts.

Receipt evidence has a real-substrate supremacy floor. Prefer real runtime
receipts, copied non-secret macro bodies with provenance, and source-faithful
public refactors. Synthetic receipts are allowed only as regression/negative
harness artifacts or temporary blocked-import debt with a named real substrate
replacement target; they are defects when they stand in for available real
substrate.

## Anti-Claim

This public agent entry file gives bounded public-root navigation only. It does
not authorize Lean/Lake beyond the bounded public witness fixture, trading or
financial advice, hosted deployment, publication, recipient work, credentialed
provider calls, secret export, or whole-system correctness.
