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

It is bounded on purpose, but it is not a synthetic safety proxy. The public root
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
- **Mechanism-before-claim reflex.** If the question is specifically about
  component substance, what the components actually do, or whether any family
  (for example finance) is thin, run `plectis comprehend --slice mechanism`
  first (source-only clone:
  `PYTHONPATH=src python3 -m microcosm_core comprehend --slice mechanism`). It
  returns every organ's real mechanism — what it computes, verifies, and
  rejects — one line each, across the whole substrate. The proven failure is
  forming the verdict from the nearest surfaces you opened (wrappers, line
  counts, one-line glosses) and emitting that as a whole-system claim.
  `finance_forecast_evaluation_spine`,
  `finite_erdos_denominator_certificate_strike`,
  `agent_sabotage_scheming_monitor_replay`, and `batch8_audio_level_rms_port`
  are sentinels whose mechanism is invisible from the gloss — they are tells,
  not the whole catalogue, so read the mechanism slice over every organ before
  concluding. A skeptical reviewer or evals reader starts here, not at `tour`
  or `hello`.
- **Calibration-before-claim reflex.** If you ever are about to characterize
  quality, completeness, readiness, or public significance, first read its `claim_ceiling`
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
It validates the organ evidence-class registry and scans every shipped Lean
file for proof placeholders, project-defined axioms, native evaluation,
unsafe/partial declarations, and unbounded kernel limits.
It should print both `Lean proof-trust check: pass` and `Plectis preflight:
organ evidence-class registry loads cleanly.` Before publishing, handing off,
or treating the standalone clone as verified, run `make ci`. It is the
public GitHub Actions entry and expands to that proof-trust preflight, editable
install, public tests, source-form smoke, and package-install smoke
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
2. Keep first contact split by reader and task.
   The human first-screen text projection is `plectis hello <project>`:

   - People start in `README.md`; its no-write text view is
     `plectis hello <project>`.
   - Agents with a concrete goal run
     `plectis comprehend --first-action "<goal>"`.
   - Agents choosing a bounded read packet run
     `plectis comprehend --packet-atlas`.
   - `plectis first-screen --card <project>` returns the compact JSON reader
     map. `plectis tour --card <project>` is the state-writing behavior proof;
     `plectis tour <project>` is the full drilldown, and
     `plectis compile <project>` is the explicit rebuild loop.
   - `plectis explain <project> <route_id>` resolves one selected route.

   Do not duplicate the component catalogue here. Resolve a task through
   [AGENT_ROUTES.md](AGENT_ROUTES.md), a component through
   [ORGANS.md](ORGANS.md), system structure through
   [ARCHITECTURE.md](ARCHITECTURE.md), and exact command availability through
   `plectis --help` or `PYTHONPATH=src python3 -m microcosm_core --help`. The
   generated route owns the first command, validator, evidence or receipt,
   stop condition, drilldown target, and authority ceiling. If a command is
   absent from root help, use the exact lens, fixture validator, or drilldown
   named by that route; do not invent a CLI spelling.

   The state-writing path is repo -> `.microcosm`. Registry status is a
   routing boundary: `accepted_current_authority` is not an evidence-strength
   claim. Fixture verdicts are not benchmark scores and not score-based progress.
   Bridge continuity examples use synthetic transport; they do not
   report live bridge health.

   The shared
   state-writing behavior proof is `plectis tour --card <project>`.

   These read models and fixtures do not authorize live provider calls, private
   state access, source mutation, publication, hosting, trading, production
   claims, benchmark claims, mathematical correctness, or release. Formal-math
   metadata organs may classify, retrieve, route, and validate bounded public
   fixtures. Only `formal_math_lean_proof_witness` may run its tiny public
   Lean/Lake witness, and that witness grants no broader proof authority.
   Generated projections stay downstream of `core/organ_registry.json`,
   `core/organ_evidence_classes.json`, source modules, standards, and named
   receipts; use their owner builders instead of editing projections.

   Before release, run `make check` and require:

```text
Lean proof-trust check: pass
Plectis preflight: organ evidence-class registry loads
cleanly.
```

   Then run `make ci`.

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
