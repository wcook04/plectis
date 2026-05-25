# Microcosm Substrate

`repo -> .microcosm`: turn any folder into an inspectable work substrate.

Microcosm compiles your project folder into local state: catalog, patterns,
routes, a governed work transaction, events, evidence, and a tiny observatory.
It does not mutate your source files or call providers.

## Try It On Your Repo

From `microcosm-substrate/`, install the console command:

```bash
python -m pip install -e '.[test]'
```

Or run the same product CLI directly from the checkout without installing the
entry point:

```bash
PYTHONPATH=src python -m microcosm_core.cli tour .
PYTHONPATH=src python -m microcosm_core.cli compile .
```

After the console command is installed, the first-screen path is:

```bash
microcosm tour .
microcosm compile .
microcosm python-lens .
microcosm explain . <selected_route_id>
microcosm evidence list .
microcosm status --card .
microcosm workingness
microcosm proof-lab --out /tmp/microcosm-proof-lab
microcosm pattern-route-readiness validate-bundle --input examples/pattern_binding_contract/exported_route_readiness_bundle --out /tmp/microcosm-pattern-route-readiness
microcosm serve . --host 127.0.0.1 --port 8765
```

The first screen is the `microcosm tour .` JSON. Its `first_screen` card names
the local `.microcosm/` state files, the selected project route id, the
route/work/event/evidence chain, the status card, workingness map,
observatory command, proof-lab command, and the authority ceiling. Use
`selected_route_id` from `microcosm tour .` or `microcosm compile .` for
`microcosm explain . <selected_route_id>`; `readme_onboarding_route` is present
when the project has a README. Open
`http://127.0.0.1:8765` to see the causal chain. The output folder is
`.microcosm/`.

Use `microcosm status --card <project>` after `tour` or `compile` for the
compressed first-screen lens over local `.microcosm/` route state plus the full
runtime status. It includes the selected project route id,
`front_door.route_explanation` with the compact route/work/event/evidence
chain, `source_files_mutated=false`, the `microcosm workingness` counts, and a
small `gap_preview` of the first missing-standard or failure-mode rows and
their target refs before opening the full organ-by-organ map; `microcosm
status` remains the full JSON drilldown.

Read `front_door_status` before treating the tour's `status` as a blanket
health claim. `blocking_surface_ids=[]` means the required first-screen path is
green. `drilldown_warning_surface_ids=["authority","intake"]` means those
surfaces remain visible bounded warnings to inspect; if one is non-pass, it is
reported under `drilldown_blocked_surface_ids`, not hidden as release
authority.

Use `microcosm authority` before trusting any organ label. It shows each
organ's explicit `evidence_class`, and `accepted_current_authority` is not an
evidence-strength claim.

The first proof-lab route is runnable from a clean clone:

```bash
microcosm proof-lab --out /tmp/microcosm-proof-lab
```

It is backed by
`receipts/first_wave/verifier_lab_kernel/exported_verifier_lab_kernel_bundle_validation_result.json`
and route metadata at
`examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle/proof_lab_route.json`.
The command prints a compact proof-lab card and writes that receipt; the receipt
validates route `formal_prover_context_strategy_gate` with 9 route
components, Lean/Lake return code `0`, 8 compiled declarations, retrieval
recall `1.0`, Ring2 precision/recall `0.36`/`0.9`, 5 target-shape cases, and 5
verifier attempts. It does not export proof bodies, provider payloads,
credentials, account/session state, or release authority.

Pattern rows become routable only through their organ and fixture overlays. The
route-readiness command validates the exported selector bundle and writes
`exported_route_readiness_bundle_validation_result.json`; it does not make any
mined pattern row a standalone public leaf.

## Real Substrate Posture

Microcosm is the public repo form of the macro system, reorganized so the
capabilities are inspectable in a clean clone instead of buried in the private
root. It is not a synthetic safety proxy, a provenance brochure, or a
metadata-only substitute for the system.

Public should carry private by default: import, refactor, or export as much of
the macro substrate as possible into this tree, then bind it to commands,
fixtures, receipts, standards, and tests. Synthetic fixtures are allowed only
as regression wrappers, negative cases, or small inputs around a real
mechanism.

Receipts obey real-substrate maximality. A receipt is not good because it is
clean; it is good because it proves real substrate. Prefer real runtime
receipts, copied non-secret macro bodies with provenance, and source-faithful
public refactors. A synthetic receipt is admissible only when it is intrinsically
test scaffolding, a negative case, or named blocked-import debt with a concrete
replacement target. It is never a substitute for available non-secret macro
code, doctrine, tool output, receipt output, proof body, or runtime behavior.

The exclusion set is narrow: secrets and credential-equivalent live access
(`.env` files, API keys, tokens, passwords, private keys, cookies, browser
profiles, keychains, account sessions, and direct credential-bearing payloads),
raw operator voice, slurs or abusive wording, private personal material, and
other clearly unsafe or non-releasable content. "Private state", "release
authority", "provenance", "activation", or "maturity" is not a reason to ship
a fake stand-in. Hosted launch and recipient sends are operational decisions
outside this repo; they do not block source-available content from being
imported here.

Any `body_copied=true` claim must name the source file, target file, and
validator or receipt that proves the import. A source ref, digest, label,
synthetic receipt, or replacement pointer is not an imported body.

## Before / After

Before:

```text
my-repo/
  README.md
  pyproject.toml
  src/
  tests/
```

After:

```text
my-repo/.microcosm/
  catalog.json
  patterns.json
  routes.json
  work_items.json
  events.jsonl
  evidence/
  graph.json
  python_lens.json
  explanations/
```

## What You Get

Microcosm creates project-local substrate state in `.microcosm/`:

- `project_manifest.json`
- `architecture.json`
- `state_index.json`
- `graph.json`
- `catalog.json`
- `python_lens.json`
- `patterns.json`
- `routes.json`
- `work_items.json`
- `events.jsonl`
- `explanations/*.json`
- `evidence/*.json`

The state is real project-local substrate over your project. It can read,
index, route, explain, observe, and record work evidence without mutating your
source files or calling providers.

## Research Prototype Contract

Microcosm is an executable research prototype of a local project operating
substrate. It is small on purpose: a dense public reorganization of the larger
architecture, not a downgraded claim about what the architecture can do.

1. Bring a folder.
2. Watch Microcosm build a local project substrate.
3. Inspect the architecture behind each route, work transaction, event, and
   evidence object.

The kernel primitives are deliberately compact: project, catalog, pattern,
standard, route, work, event, evidence, explanation, and assimilation. They
are defined in `core/architecture_kernel.json` and projected into each project
as `.microcosm/architecture.json`.

The architecture kernel does not replace the pattern surface. Catalog roles
become rows in `.microcosm/patterns.json`, routes carry `pattern_refs`, and
`explain` resolves those refs before showing work, events, and evidence. This
keeps the miniature architecture tied to the same public pattern-binding
surface used by the adapter spine.

Route explanations also resolve through `core/public_standard_pressure.json`.
That card set distills public runtime pressure from the macro standards,
principles, WorkItem spine, projection governance, observability, and
assimilation surfaces. The cards constrain local state and explanation shape
and must be backed by real Microcosm commands or explicit omissions.

## First Run

From this directory:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
mkdir -p /tmp/microcosm-scratch/src/app /tmp/microcosm-scratch/tests
printf '# Scratch Project\n' > /tmp/microcosm-scratch/README.md
printf '[project]\nname = "scratch-project"\nversion = "0.1.0"\n' > /tmp/microcosm-scratch/pyproject.toml
printf 'VALUE = 1\n' > /tmp/microcosm-scratch/src/app/__init__.py
printf 'from app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n' > /tmp/microcosm-scratch/tests/test_app.py

microcosm tour /tmp/microcosm-scratch
microcosm compile /tmp/microcosm-scratch
microcosm python-lens /tmp/microcosm-scratch
microcosm explain /tmp/microcosm-scratch readme_onboarding_route
microcosm evidence list /tmp/microcosm-scratch
microcosm status --card /tmp/microcosm-scratch
microcosm proof-lab --out /tmp/microcosm-proof-lab
microcosm pattern-route-readiness validate-bundle --input examples/pattern_binding_contract/exported_route_readiness_bundle --out /tmp/microcosm-pattern-route-readiness
microcosm serve /tmp/microcosm-scratch --host 127.0.0.1 --port 8765
```

The same commands work without installing the console script:

```bash
PYTHONPATH=src python3 -m microcosm_core.cli tour /tmp/microcosm-scratch
PYTHONPATH=src python3 -m microcosm_core.cli compile /tmp/microcosm-scratch
PYTHONPATH=src python3 -m microcosm_core.cli python-lens /tmp/microcosm-scratch
PYTHONPATH=src python3 -m microcosm_core.cli explain /tmp/microcosm-scratch readme_onboarding_route
PYTHONPATH=src python3 -m microcosm_core.cli evidence list /tmp/microcosm-scratch
PYTHONPATH=src python3 -m microcosm_core.cli status --card /tmp/microcosm-scratch
PYTHONPATH=src python3 -m microcosm_core.cli proof-lab --out /tmp/microcosm-proof-lab
```

The older organ-adapter demo still exists for internal evidence and regression:

```bash
microcosm status
microcosm run examples/runtime_shell/demo_project
microcosm route list
microcosm evidence list
```

Evidence receipts are the black-box recorder, not the cockpit. Start with the
project loop; open receipts only when you need a drilldown.

`microcosm tour <project>` is the compressed cold-reader route. It compiles
the project, then emits one real-substrate ten-minute path through spine,
authority, prediction, corpus, trace repair, repair-loop curriculum, formal
evidence cells, proof-loop depth, work landing replay, durable agent work
landing replay, research replication replay, world-model projection drift control,
view quality, projection safety, hook
intervention coverage, projection import map, import-projector contract,
compression-profile option surface, stripping guard, replay gauntlet, benchmark lab, legibility scorecard, intake, reveal,
observatory, and evidence drilldowns. It writes
`receipts/runtime_shell/public_ten_minute_tour.json` and
keeps release, hosting, provider calls, unsafe source mutation,
credential-bearing exports, proof authority, and financial advice
unauthorized.

`microcosm spine` is the compact x-ray for first-run evaluation: accepted
adapter-backed organs, the concrete command path, surface counts, evidence
policy, and the secret-only boundary in one JSON view.

`microcosm python-lens <project>` is the project-local Python route lens. It
emits `.microcosm/python_lens.json` with Python file roles, package roots,
readiness checks, route rows, and the `std_python_microcosm_navigation_assay`
inside `implementation_atlas.python_navigation_assay`, plus
`route_utility_curriculum` task rows that check entry-to-span navigation while
redacting source bodies. Its `route_utility_curriculum.ratchet` section marks
changed watched surfaces, affected route tasks, stale task ids, and the next
reentry condition when a non-writing inspection sees drift against written lens
state. Use that assay to choose the `module_docs`, `file_card`,
`symbol_capsule`, `graph_context`, or `source_span` depth before opening proof
spans. It does not
execute Python, mutate source files, call providers, claim static-analysis
authority, export source bodies, or certify package quality.

`microcosm authority` is the boundary map. It aggregates the runtime status,
spine, intake bridge, reveal board, accepted organs, projection cells, hard
public boundaries, safe local-only exceptions, and evidence refs into one JSON
surface. It is the quickest way to verify that secret export, credentialed
live access, publication, provider calls, unsafe source mutation, general proof
authority, and trading advice remain unauthorized without downgrading the
public repo into metadata-only claims.

`microcosm trace-lens` is the formal verifier trace-repair lens. It shows
failure classes, trace grades, repair routing, negative cases, and the
cold-rerun promotion gate while omitting proof bodies, oracle-needed premise
ids, provider payloads, and proof-correctness authority.

`microcosm repair-loop` is the formal verifier repair-loop curriculum lens. It
turns trace rows into explicit stages and transitions: capture verifier
failure, classify failure, route the repair through public evidence, require a
cold rerun, then promote only a receipt-backed curriculum cell. It omits proof bodies,
oracle-needed premise ids, provider payloads, source mutation, and
proof-correctness authority.

`microcosm evidence-cells` is the public formal evidence-cell resolver. It
turns proof-adjacent language into explicit cell ids, receipt refs, negative
cases, and authority ceilings before a cold reader trusts it. It accepts only
metadata cells with public receipt anchors and rejects unknown cells, missing
source anchors, embedded proof bodies, private refs, general theorem-solution
claims, and release overclaims.

`microcosm proof-loop-depth` is the public formal proof-loop depth lens. It
shows the public evidence route from corpus boundary through premise retrieval,
tactic availability, target-shape routing, verifier trace repair, cold rerun,
evidence-cell resolution, and bounded verifier-lab execution. It is a
projection protocol, not a proof engine: it exports no proof bodies, oracle
premise ids, provider payloads, benchmark scores, source mutation authority,
release authority, or theorem-solution claims.

`microcosm verifier-lab-execution-spine-lens` is the public runtime lens over
the verifier-lab execution-spine receipt. It exposes bounded Lean/Lake
transition rows, CP2 downstream rerun effect, Evolve rerun acceptance, tool
return-code evidence, and secret-exclusion status without proof bodies, raw
tactics, oracle answers, provider payloads, stdout/stderr bodies, source
mutation, benchmark solve-rate claims, or release authority.

`microcosm landing-replay` is the public work-landing replay lens. It turns the
dirty-tree landing rules into a compact decision table: scoped commit for
isolated owned paths, broad checkpoint only with explicit operator
authorization, metadata-blocked patch-bundle recovery, and hard stop for
secrets or private leakage. It records blocker and ledger refs without
mutating Git, staging unrelated dirt, exporting private source bodies, or
claiming that a commit landed.

`microcosm view-quality` is the public view-quality action-map lens. It uses
synthetic rows to show that every requested view receives one typed next
action, including missing and partially measured views. Its hot-action rollup
is a projection, not the complete universe, and it exports no private
screenshot paths, controls no browser, claims no complete frontend quality,
and authorizes no release.

`microcosm projection-safety` is the public omission-receipt audit lens. It
checks that compressed public projections carry named omission receipts,
drilldowns, source refs, and authority ceilings before they are treated as
legible public state. It exports no private bodies, proof bodies, provider
payloads, source mutation authority, or release claims.

`microcosm market-boundary` is the public market/prediction evidence boundary.
It separates observations from forecasts, requires base-rate or prior-context
hooks before narrative pressure, names scenario-tree and confidence-band gates,
and keeps decision policy distinct from trading or investment advice. It is
local evidence only: no live market data, private portfolio/account export,
provider payloads, performance guarantees, publication, or release authority.

`microcosm finance-eval-spine validate-finance-eval-bundle` validates the
copied non-secret macro finance evaluator bundle. It checks the `tools/finance`
comparison-key, CP1 admission, CP2 resolution, replay, historical replay,
shadow calibration, variant, comparison, and operating-picture modules against
their manifest hashes, then checks the real finance operating picture's
no-advice/no-mutation gates. It exports source bodies in the bundle, not in the
receipt, and authorizes no trading advice, live provider calls, private account
state, forecast-performance claim, optimizer mutation, publication, hosting, or
release.

`microcosm drift-control` is the public projection-drift control lens. It
turns world-model, route, view-quality, CAP-assimilation, and entry-payload
drift signals into rows with source refs, repair routes, validation refs, and
authority ceilings. It is public runtime evidence: no live repair, source mutation,
private runtime export, provider payload export, doctrine promotion, or
release authority.

`microcosm route-cleanup` is the public route cleanup contract lens. It names
the first-contact, context-pack, generated-region, option-surface, Work Ledger,
scoped landing, seed reentry, and public/private cleanup rows with owner
routes, validator refs, and authority ceilings. It is public runtime evidence: no route
deletion, generated-region hand edit, private export, provider payload export,
source mutation, doctrine promotion, or release authority.

`microcosm projection-import-map` is the public projection import map. It names
which macro pattern each runtime lens came from, what was copied, what was
cleaned, what was omitted, which validators prove the projection, and which
authority ceiling still applies. It does not automate imports, export private
bodies, expose proof bodies or provider payloads, claim private-root
equivalence, or authorize release. It must distinguish real body imports from
metadata projections and demote anything that cannot prove the copy.

`microcosm import-projector` is the public contract for making future macro
imports cheaper without making them fake. It turns a prospective import into
explicit stages: candidate selection, public manifest, secret stripping,
body-import verification, runtime binding, and validation closeout. Each row
names source, target, copied body status, omitted material, validation refs,
and authority ceiling. It may plan the import without writing; it must not
pretend metadata, provenance, or fixture/projection refs are imported macro bodies.

`microcosm option-surface-lens` is the first concrete consumer of that
projector contract for `compression_profile_governed_option_surface`. It turns
profile choice into public command, endpoint, receipt, sidecar, validation, and
authority rows. It does not switch profiles, auto-select options, export private
context or sidecar bodies, hand-edit generated regions, mutate source, claim
lossless projection, or authorize release.

`microcosm stripping-guard` is the public/private export guard. It names the
denials that must remain true before a macro pattern becomes public runtime
state: no private source body, proof body, provider payload, raw private path,
example secret, financial advice, source mutation, release, or private-root
equivalence export. It is a read-model and not a complete secret scanner.

`microcosm standards-control` is the public standards control lens. It ties the
standards registry, public standard pressure, validator receipt coverage,
fixture manifests, acceptance commands, docs, authority ceilings, and projection
safety into one read-model. It does not make the registry source authority,
prove complete coverage, mutate source, call providers, or authorize release.

`microcosm hook-coverage` is the public hook intervention coverage lens. It
compresses the `agent_route_observability_runtime` receipts into hook-shadow,
route-compliance, actor-axis, anti-pattern debt, and route-lease intervention
rows. It exposes mapped repair classes, expected interventions,
missing-authority, banned-route, command-displacement, live-state-read, and
budget negative-case metadata without reading live operator state, provider
payloads, browser/HUD/cockpit state, mutating Task Ledger, authorizing pattern
assimilation, certifying runtime behavior, or claiming release.

`agent-route-observability-runtime validate-computer-use-bundle` is the
computer-use action-trace showcase under the same observability organ. It
validates synthetic observations, affordances, actions, pre-action authority
verdicts, state transitions, recovery receipts, cold replay, and falsification
fixtures without live browser control, accounts, credentials, external network
mutation, raw screenshots, benchmark scores, source mutation, or release
authority.

`agent-route-observability-runtime validate-session-attribution-bundle` is the
public session-attribution showcase. It runs the copied
`agent_session_attribution` macro body over synthetic AgentTraceStore and Work
Ledger metadata envelopes, then exposes matched, unattributable, infrastructure,
ATS-only, and WorkLedger-only session classes without raw transcript bodies,
provider payloads, browser/HUD/cockpit state, account/session control state,
credentials, cookies, Work Ledger mutation, source mutation, or release
authority.

`microcosm replay-gauntlet` is the public synthetic agent-reliability replay
lens. It projects benchmark-integrity, monitor falsification, sabotage,
sandbox escape, MCP/tool-authority, indirect prompt-injection, temporal memory
conflict, and sleeper-memory poisoning cases as source-open containment metadata.
It does not run live agents or tools, export real secrets, import real user
memory, authorize sandbox escape, claim benchmark performance, prove complete
security, mutate source, call providers, or authorize release.

`microcosm benchmark-lab` is the public synthetic repository benchmark
transaction lab. It projects two issue/patch fixtures with oracle diffs,
FAIL_TO_PASS and PASS_TO_PASS-style guards, misleading-test denial, scoped diff
receipts, workitem admission, and provider-slot cooldown metadata. It does not
claim SWE-bench performance, mutate live repos, call providers, import private
issues, export private repositories, authorize broad checkpointing, prove
production delivery rate, or authorize release.

`microcosm legibility-scorecard` is the cold-reader comprehension contract. It
maps five questions to runnable proof commands, six checkpoints, endpoint
parity, evidence refs, and negative cases so a stranger can evaluate the
public reveal without reading the private macro root first. It does not prove
every reader will understand the system, claim private-root equivalence,
publish, call providers, mutate source, export benchmark scores, prove
mathematical correctness, or authorize release.

`microcosm workingness` is the per-organ failure envelope map. It compares
what each organ needs to work against the evidence Microcosm currently has:
owning standard, typed failure modes, validator command, authority receipt,
generated receipts, evidence class, claim ceiling, and public/private
boundary. It emits concrete future-work targets without becoming a maturity
board, activation label, release signal, or score-based progress surface.

`microcosm prediction-lens` is the public read-model for the
`prediction_oracle_reconciliation` organ. It shows synthetic target-universe
gating, CP1 bifurcation resolution, CP2 prediction rows, oracle diff grading,
bounded dossier mutation, negative-case coverage, and source/projection refs
without live market data or private bodies. It is not trading, financial or
investment advice, forecast-performance evidence, publication authority, or a
release claim.

`microcosm market-boundary` complements the prediction lens with the public
claim contract a cold reader needs before trusting market-facing reasoning:
observation/forecast separation, timestamped evidence boundaries, base-rate and
scenario-tree gates, and explicit denial of advice, live data, private account
state, and performance guarantees.

`microcosm corpus-lens` is the public read-model for the
`corpus_readiness_mathlib_absence_gate` organ. It shows Mathlib import
absence, available and absent corpora, translation-smoke-only rows, allowed and
blocked formal-math consumers, negative-case coverage, and the read-model-only
authority ceiling before retrieval or proof-witness work. It is not Lean/Lake
execution, Mathlib proof authority, benchmark evidence, corpus-completeness
evidence, provider output, source mutation, or a release claim.

`microcosm intake` is the runtime reveal/import bridge. It connects the macro
projection intake board, the formal-math readiness extension board, the
public reveal bundle, and runtime evidence refs into one source-open boundary view so a
cold reader can see which projection cells are ready, landed, bridged, or
already consumed as public runtime imports
without opening private macro material.

`microcosm reveal` projects the ten-minute public reveal board. It is the
short path for a cold technical reader: compile a repo, inspect
`.microcosm/`, open one route explanation, see the observatory causal chain,
then drill into receipts and authority ceilings.

`microcosm cold-reader-route-map run-route-map-bundle` validates the entry path
itself. The `cold_reader_route_map` organ binds first-run steps to commands,
docs refs, receipt refs, and authority ceilings so "what should I run first?"
is executable evidence instead of prose.

## Architecture Kernel

`microcosm explain <project> <route_id>` is the main density surface. It shows
why a route exists by connecting grounded project refs, resolved pattern
bindings, kernel primitives, resolved standard pressure, work transaction
contracts, event refs, and evidence refs.

`microcosm serve <project> --host 127.0.0.1 --port 8765` opens a tiny local
observatory. The first screen shows the causal chain before raw JSON: project
summary, resolved pattern bindings, standard pressure, selected route, work
state history, event refs, and evidence drilldowns. It also exposes the
runtime spine/intake/reveal bridge in the browser: `/spine`, `/intake`, and
`/reveal` show the same accepted runtime spine, projection-cell status counts,
open-actionable intake count, reveal board, and evidence refs that the CLI
commands print. `/tour` adds the same ten-minute route compression that
`microcosm tour <project>` emits. `/authority` adds the same authority-ceiling
map in browser form, `/workingness` adds the per-organ failure envelope map,
`/prediction` adds the synthetic prediction-mechanics
lens with its no-advice/no-live-data boundary, `/market-boundary` adds the
market/prediction evidence contract, `/corpus` adds the formal-math
corpus readiness lens with its no-proof/no-Mathlib boundary, `/trace` and
`/repair-loop` expose proof-adjacent repair metadata boundaries,
`/evidence-cells` exposes evidence-cell boundaries, `/proof-loop-depth` shows
the public proof-loop gate chain and no-proof/no-benchmark authority ceiling,
`/verifier-lab-execution-spine` exposes bounded external tool-witness rows,
`/landing-replay` shows dirty-tree landing lanes and commit-claim limits, `/view-quality` shows
all-view action rows and hot-action projection limits, `/projection-safety`
shows omission receipts and reversible projection drilldowns,
`/market-boundary` shows observation/forecast, timestamp, base-rate,
scenario-tree, and no-advice gates,
`/drift-control` shows projection-drift rows with repair routes and validation
refs,
`/route-cleanup` shows first-contact, generated-region, option-surface, Work
Ledger, scoped landing, and seed reentry cleanup rows,
`/projection-import-map` shows the copy/clean/omit/validate/authority rows for
macro-pattern projections, `/import-projector` shows the staged future-import
contract rows, `/option-surface-lens` shows compression-profile option rows,
`/stripping-guard` shows export-denial guard rows,
`/standards-control` shows registry/pressure/validator/authority control rows,
`/hook-coverage` shows hook-intervention and live-state boundaries,
`/replay-gauntlet` shows synthetic agent reliability
replay and containment boundaries, `/benchmark-lab` shows repository benchmark
transaction fixtures and oracle-grading boundaries, `/legibility-scorecard`
shows the cold-reader question/checkpoint contract, and `/project/python-lens`
exposes the project-local Python route lens. The JSON endpoints remain
available for automation and deeper inspection.

## Internal Runtime Spine

The public package now carries 46 accepted public runtime organs behind the
local substrate loop. The first-screen status card separates the 42
product-spine adapter-backed organs from 4 runnable drilldown-only regression
surfaces; this list is the public entry claim that must stay aligned with
`core/organ_registry.json` and `core/organ_evidence_classes.json`.

1. `pattern_binding_contract`
2. `executable_doctrine_grammar`
3. `proof_diagnostic_evidence_spine`
4. `formal_math_readiness_gate`
5. `corpus_readiness_mathlib_absence_gate`
6. `mathematical_strategy_atlas_hypothesis_scorer`
7. `tactic_portfolio_availability_probe`
8. `target_shape_tactic_routing_gate`
9. `lean_std_premise_index`
10. `formal_math_premise_retrieval`
11. `formal_math_verifier_trace_repair_loop`
12. `formal_evidence_cell_anchor_resolver`
13. `undeclared_library_prior_symbol_classifier`
14. `ring2_premise_retrieval_precision_recall_harness`
15. `agent_benchmark_integrity_anti_gaming_replay`
16. `provider_context_recipe_budget_policy`
17. `formal_math_lean_proof_witness`
18. `verifier_lab_kernel`
19. `verifier_lab_execution_spine`
20. `navigation_hologram_route_plane`
21. `mission_transaction_work_spine`
22. `durable_agent_work_landing_replay`
23. `research_replication_rubric_artifact_replay`
24. `world_model_projection_drift_control_room`
25. `spatial_world_model_counterfactual_simulation_replay`
26. `materials_chemistry_closed_loop_lab_safety_replay`
27. `mechanistic_interpretability_circuit_attribution_replay`
28. `agent_route_observability_runtime`
29. `pattern_assimilation_step`
30. `public_reveal_walkthrough`
31. `macro_projection_import_protocol`
32. `prediction_oracle_reconciliation`
33. `standards_meta_diagnostics`
34. `cold_reader_route_map`
35. `agent_monitor_redteam_falsification_replay`
36. `agent_sabotage_scheming_monitor_replay`
37. `agent_memory_temporal_conflict_replay`
38. `sleeper_memory_poisoning_quarantine_replay`
39. `mcp_tool_authority_replay`
40. `proof_derived_governed_mutation_authorization`
41. `belief_state_process_reward_replay`
42. `agent_sandbox_policy_escape_replay`
43. `indirect_prompt_injection_information_flow_policy_replay`
44. `agentic_vulnerability_discovery_patch_proof_replay`
45. `certificate_kernel_execution_lab`
46. `voice_to_doctrine_self_improvement_loop`

`pattern_binding_contract` is the real pattern-ledger root: it validates the
373-row public macro pattern ledger, the substrate-binding sidecar, and now the
copied route-readiness selector overlays. Run `microcosm pattern-binding
validate-route-readiness-bundle --input
examples/pattern_binding_contract/exported_route_readiness_bundle --out
receipts/first_wave/pattern_binding_contract/route_readiness` to inspect the
selector gate directly. It proves that mined pattern ids route through organ
bundles, fixture specs, dependency edges, and hard no-standalone rules; it does
not make individual rows public leaves or authorize release.

`agent_benchmark_integrity_anti_gaming_replay` is a body-free benchmark claim
integrity regression drilldown, not product-spine substrate: it validates
locked evaluator ids, evaluator config hashes, file-access logs, contamination
checks, trusted-reference score refs, output-replay refs, held-out guards, and
anti-gaming negative cases before any benchmark-style language is admitted. Run
`microcosm
agent-benchmark-integrity-anti-gaming-replay run-benchmark-integrity-bundle`
to inspect the synthetic body-free replay bundle. The organ rejects evaluator
edits, train/test leakage, oracle patch bodies, hidden-gold access,
final-answer-only grading, provider payloads, score overclaims, pass-k
cherry-picking, misleading tests, private issue bodies, and replay rows whose
case id is outside the declared benchmark roster without claiming a SWE-bench
score, live repo mutation, provider execution, product progress, or release
authority.

`agent_monitor_redteam_falsification_replay` is a monitor/redteam regression
drilldown, not product-spine substrate: it validates synthetic trajectories,
monitor verdicts, adversarial probe refs, escalation refs, body-omission refs,
mitigation refs, and cold replay refs before monitor-language is admitted.
Run `microcosm agent-monitor-redteam-falsification-replay run-monitor-bundle`
only when inspecting that drilldown bundle; the product path goes through
`microcosm replay-gauntlet`. The organ rejects private chain-of-thought,
internal code, exploit instruction detail, credential material, live agent
traffic, monitor product-performance claims, and coverage labels without
adversarial probes without claiming live monitoring performance, control-eval
scores, provider execution, source mutation, or release authority.

`agent_sabotage_scheming_monitor_replay` is a scheming-monitor regression
drilldown, not product-spine substrate: it validates synthetic task episodes,
action traces, per-step monitor scores, counterfactual benign replays, and cold
replay refs before sabotage-monitor language is admitted. Run `microcosm
agent-sabotage-scheming-monitor-replay run-sabotage-bundle` only when
inspecting that drilldown bundle; the product path goes through `microcosm
replay-gauntlet`. The organ rejects live sabotage instructions, real
credentials or account identifiers, exploit details, private chain-of-thought
export, raw harmful payloads, monitor-only final grading, and deployment
scare-story claims without claiming live sabotage detection, monitor product
performance, provider execution, source mutation, or release authority.

`agent_sandbox_policy_escape_replay` is the sandbox policy boundary: it
computes public `agent_execution_trace` spans from body-free action requests,
pre-execution policy verdicts, side-effect diff receipts, rollback receipts,
and cold replay refs before sandbox/security language is admitted. Run `microcosm
agent-sandbox-policy-escape-replay run-sandbox-bundle` to inspect the exported
bundle. The organ rejects real secret material, live network access, raw
environment export, policy after execution, unlogged side effects, tool-output
policy bypass, executable escape payloads, and security benchmark claims
without claiming live sandbox security, provider execution, source mutation, or
release authority.

`indirect_prompt_injection_information_flow_policy_replay` is the
prompt-injection information-flow boundary: it validates synthetic source trust
labels, taint graph rows, pre-action policy verdicts, sanitized-output refs,
and cold replay receipts before prompt-injection language is admitted. Run
`microcosm indirect-prompt-injection-information-flow-policy-replay
run-prompt-injection-bundle` to inspect the exported bundle. The organ rejects
real accounts, secret exfiltration, raw prompt bodies, tool-output instruction
authority, hidden system-message promotion, credential exfiltration,
final-answer-only success, and ungated untrusted privileged sinks without
claiming general prompt-injection robustness, provider execution, source
mutation, benchmark performance, or release authority.

`agentic_vulnerability_discovery_patch_proof_replay` is the patch-proof
vulnerability-discovery boundary: it validates synthetic targets, issue
hypotheses, trace evidence, abstract exploitability refs, patch diffs,
regression tests, verifier receipts, sandbox policy verdicts, false-positive
triage, and cold replay before vulnerability-discovery language is admitted.
Run `microcosm agentic-vulnerability-discovery-patch-proof-replay
run-patch-proof-bundle` to inspect the exported bundle. The organ rejects live
targets, real CVE exploitation, weaponized payloads, credentials, network
exfiltration, actionable exploit steps, patch claims without tests, and
benchmark score claims without claiming live security authority, provider
execution, source mutation, or release authority.

`agent_memory_temporal_conflict_replay` is the agent-memory honesty boundary:
it runs the public `agent_execution_trace` refactor over declared
three-episode memory-conflict rows where ADD, UPDATE, DELETE, and NOOP memory
decisions, conflict-edge refs, stale-downgrade refs, metadata-only private
refs, paired memory-on/off cold replay receipts, and an answer-delta receipt
must align before memory-language is admitted. Run `microcosm
agent-memory-temporal-conflict-replay run-memory-bundle` to inspect the
source-faithful trace bundle. The organ rejects raw transcript export, private
candidate auto-promotion, stale preference override, memory as source
authority, vector recall without evidence, final-answer-only memory credit,
and active injection as authoritative without claiming live memory product
quality, provider execution, source mutation, or release authority.

`sleeper_memory_poisoning_quarantine_replay` is the persistent-memory security
boundary: it validates a body-free public policy projection where source
capsule refs, provenance refs, quarantine verdicts, retrieval influence gates,
rollback audit refs, and cold-rerun receipts must align before sleeper-memory
poisoning language is admitted. Run `microcosm
sleeper-memory-poisoning-quarantine-replay run-quarantine-bundle` to inspect
the exported bundle. The organ rejects private memory bodies, live user memory
claims, raw transcript export, provenance-less writes, trusted promotion from
untrusted context, deletion without audit, final-answer-only grading, and
unmetered poison influence without claiming live memory security, provider
execution, benchmark performance, source mutation, or release authority.

`mcp_tool_authority_replay` is the agent tool-authority boundary: it validates
a public agent-execution trace refactor where manifest scopes, call argument
hashes, approval refs, side-effect ledger refs, rollback refs, untrusted-output
instruction/data splits, and cold replay receipts must align before tool-use
authority language is admitted. Run `microcosm
mcp-tool-authority-replay run-tool-authority-bundle` to inspect the exported
bundle. The organ rejects overbroad scopes, hidden credential export,
tool-output-as-instruction, unapproved side effects, live account access,
final-answer-only grading, missing rollback receipts, and unsafe tool payload
exports without claiming live MCP account safety, provider execution,
benchmark performance, source mutation, or release authority.

`proof_derived_governed_mutation_authorization` is the governed-mutation
authority boundary: it validates synthetic intent capsules, proof evidence
cells, visible policy verdict refs, ephemeral execution identity refs, logged
side-effect diffs, rollback receipts, and cold replay receipts before mutation
authorization language is admitted. Run `microcosm
proof-derived-governed-mutation-authorization run-authorization-bundle` to
inspect the exported bundle. The organ rejects standing credential authority,
policy-after-execution, hidden policy votes, live cloud credentials,
irreversible mutation, unlogged side effects, consensus without evidence, and
final-answer-only success without claiming live account action, source mutation,
provider execution, benchmark performance, or release authority.

`belief_state_process_reward_replay` is the process-reward evidence boundary:
it validates a source-faithful public agent-execution trace over partially
observable episodes, public typed belief-state summaries, predicted next
evidence, verifier or observed feedback refs, belief-discrepancy scores, dense
process rewards, outcome rewards, reward-hacking trap results, trajectory
groups, and cold replay before reward-language is admitted. Run `microcosm
belief-state-process-reward-replay run-reward-bundle` to inspect the exported
bundle, or `python -m microcosm_core.macro_tools.agent_execution_trace
belief-reward --input examples/belief_state_process_reward_replay/exported_belief_state_process_reward_bundle`
to inspect the trace projection directly. The organ rejects hidden reasoning
export, neural-judge-only labels, hidden gold labels, reward-by-formatting,
verifier bypass, benchmark-performance claims, and final-answer-only scoring
without claiming live RL, benchmark performance, provider execution, source
mutation, or release authority.

`mission_transaction_work_spine` now includes the public checkpoint lane
decision receipt: clean and mixed owned-path work can choose scoped commit,
broad checkpoint requires explicit operator authorization, and suspected
private leakage forces a hard stop. This keeps the demo honest about how work
lands in a dirty tree without implying broad staging authority.

`durable_agent_work_landing_replay` is the work-landing transaction replay
organ: it validates claimed owned paths, owner-native validation refs, scoped
commit attempts, validation-before-commit ordering, HEAD-advance checks before landed language, metadata-blocked
patch-bundle recovery, Task Ledger blocker refs, and Work Ledger finalizers.
Run `microcosm durable-agent-work-landing-replay run-work-landing-bundle` to
inspect the public bundle. The organ rejects missing evidence, missing ledger
closeout, validation after commit attempt, commit claims without HEAD advance,
live Git mutation authority, unrelated dirty-path staging, uncaptured blockers,
release overclaims, and private path/body leakage without proving a commit
landed or authorizing release.

`research_replication_rubric_artifact_replay` is the public research-replay
rubric organ: it validates synthetic paper capsules, artifact hash plans,
declared artifact-hash roster membership, grader reports, cold rerun receipts,
ablation diffs, failure taxonomies, and cost/runtime ceilings before any
replication-style language is admitted. Run
`microcosm research-replication-rubric-artifact-replay run-replication-bundle`
to inspect the exported replay bundle. The organ rejects original-author code
reuse, hidden rubric leakage, report-only success, benchmark performance claims,
private paper/data bodies, unbounded compute search, final-answer-only grading,
and undeclared artifact hash refs without claiming external benchmark
performance, live provider calls, publication, release, or proof of real-world
replication.

`world_model_projection_drift_control_room` is the public drift-control organ:
it validates synthetic world-model projection rows with source signals, public
source refs, repair routes, validation refs, body-free public fixture refs, and
metadata-scoped authority ceilings. Run `microcosm
world-model-projection-drift-control-room run-drift-control-bundle` to inspect
the exported drift-control bundle. The organ rejects missing source refs,
missing validation refs, source-authority claims, live repair authority,
private runtime export, provider payload export, automatic doctrine promotion,
and release claims without inspecting private runtime bodies, mutating source,
repairing live routes, promoting doctrine, or authorizing release.

`spatial_world_model_counterfactual_simulation_replay` is the public spatial
counterfactual replay organ: it validates synthetic scene states, action traces,
predicted states, transition diffs, oracle checks, sensor packet refs,
rare-event labels, fidelity limits, and limitation labels. Run `microcosm
spatial-world-model-counterfactual-simulation-replay run-simulation-bundle` or
`microcosm spatial-simulation` to inspect the exported simulation bundle. The
organ rejects private video export, raw sensor export, live robot or AV
operation, real-world location claims, simulator-product claims,
generated-video-only authority, geographic accuracy claims, benchmark score
overclaims, and release claims without claiming a trained simulator, geographic
truth, generated-video proof, live operation authority, benchmark score,
publication, or release.

`materials_chemistry_closed_loop_lab_safety_replay` is the public
autonomous-science lab-safety replay organ: it validates synthetic candidate
materials, safety screens, simulator assays, active-learning decisions, cold
replay refs, projection protocol, negative cases, and no-wetlab authority
ceilings. Run `microcosm
materials-chemistry-closed-loop-lab-safety-replay run-lab-bundle` to inspect
the exported bundle. The organ rejects wetlab protocol export, hazardous
synthesis steps, reagent quantities, controlled or bioactive targets, live lab
credentials, robot commands, private lab notebooks, live assay data, discovery
claims, benchmark score claims, and release authority.

`mechanistic_interpretability_circuit_attribution_replay` is the public
mechanistic-interpretability replay organ: it validates toy prompt refs, sparse
feature ids, machine-readable graph nodes and edges, replacement-model
approximation scores, feature visualization summary refs, causal inhibition and
injection delta refs, sufficiency labels, faithfulness limits, contradiction
cases, and cold replay refs. Run `microcosm
mechanistic-interpretability-circuit-attribution-replay run-attribution-bundle`
or `microcosm circuit-attribution` to inspect the exported attribution bundle.
The organ rejects private model weights, raw activation dumps, proprietary
prompts, hidden chain-of-thought, unverifiable feature names, screenshot-only
graphs, transparency claims without intervention receipts, faithfulness claims
without limits, benchmark overclaims, provider payloads, and release claims
without claiming private model internals, a model-transparency product,
benchmark score, publication, or release.

`formal_math_readiness_gate` is accepted as a metadata-only readiness boundary:
it validates synthetic corpus, tactic, premise, route, and provider-context
policy packets without executing Lean/Lake or exposing proof bodies. It also
emits `formal_math_readiness_extension_board.json`, the public replacement for
the `formal_math_readiness_extensions` intake cell: namespace/split coverage
for the closed premise index, tactic probe availability, target-shape routing
admissibility, provider-context budgets, source intake refs, selected pattern
ids, and validation refs.
`corpus_readiness_mathlib_absence_gate` is the sharper corpus/toolchain
readiness boundary: it makes Mathlib import absence explicit, marks translation
corpora as smoke-only, blocks absent LeanDojo/Pantograph consumers, and rejects
proof-body, private-source, and release-authority overclaims before downstream
formal-math organs run. `microcosm corpus-lens` projects that board as a
single cold-reader read-model and writes
`receipts/runtime_shell/public_corpus_readiness_lens.json`.
`mathematical_strategy_atlas_hypothesis_scorer` is the pre-oracle strategy
layer: it maps public problem features to a known strategy enum, expands
retrieval terms, and records typed `STRATEGY_SELECTION_MISS` rows when no
strategy matches. It is a retrieval lens and hypothesis scorer, not proof
authority, oracle visibility, provider output, test tuning, or release
authority.
`tactic_portfolio_availability_probe` is the environment-scoped tactic
callability layer: it records compile-status metadata for a synthetic public
portfolio, marks Mathlib-dependent `aesop` unavailable when the Mathlib import
probe fails, and rejects missing statuses, unprobed consumers, proof-body
leakage, and proof/provider/benchmark/release overclaims. It is availability
metadata, not proof authority or a complete tactic inventory.
`target_shape_tactic_routing_gate` is the pre-execution tactic admissibility
layer: it compares target shapes with a public tactic portfolio and strategy
route before Lean/Lake runs, records why a tactic was admitted or rejected, and
blocks unavailable tactics, unprobed tactics, proof-body leakage,
post-execution routing, and release overclaims. It is route gating metadata,
not proof authority or toolchain authority.
`formal_math_lean_proof_witness` is now accepted only as a bounded public
witness: it copies a tiny synthetic Lake project into a temporary workspace,
runs the installed local Lean/Lake toolchain, and emits payload-boundary receipts with
source hashes and declaration names. That does not authorize Mathlib-dependent
proofs, provider calls, benchmark claims, private proof import, or release.
Fixtures and exported bundles are regression inputs and examples; they are not
the primary product runtime.

`verifier_lab_kernel` composes the public formal-math witness, tactic
portfolio, target-shape routing, verifier trace repair, provider-hypothesis
quarantine, CP2 action candidates, and bounded Evolve candidates into one
leak-proof receipt. Run `verifier-lab-kernel` to inspect the exported kernel
bundle; it separates verifier success, oracle comparison, provider suggestion,
contract rejection, retrieval miss, CP2 translation, and Evolve candidates
without importing proof bodies or upgrading provider/oracle output into proof
authority.

`formal_math_premise_retrieval` is the first real formal-math import slice
through the projection protocol: a Lean/Std premise index, term-scored
retrieval queries, context-budget recipes, strategy gates, synthetic recall,
and leakage negative cases. It is retrieval machinery, not theorem proof
authority.

`formal_math_verifier_trace_repair_loop` is the proof-lab self-repair slice:
verifier failure classes, trace grades, repair actions, failure-mode ledger
updates, curriculum deltas, and cold-rerun promotion gates are all explicit
public metadata. It rejects proof bodies, oracle premise ids, provider payload
bodies, and human approval as proof correctness. Use
`formal-math-verifier-trace-repair-loop` to validate the runnable replay; it is
repair-loop machinery, not theorem proof authority.

`formal_evidence_cell_anchor_resolver` is the claim-boundary slice: toy paper
claims resolve to public evidence-cell ids, each cell carries source-anchor refs
and machine-anchor metadata, and proof-language claims fail if the cell is
unknown, missing anchors, or trying to claim theorem correctness. Use
`formal-evidence-cell-anchor-resolver` to validate the public anchor bundle; it
is evidence metadata, not proof authority.

`undeclared_library_prior_symbol_classifier` is the out-of-recipe proof-symbol
slice: payload-boundary proof observations carry only body hashes, qualified symbol
refs, allowed premise ids, and cited-unallowed premise ids. Known symbols outside
the allowed set classify as `UNDECLARED_LIBRARY_PRIOR` and bridge-escalate, while
explicit cited-unallowed premise ids stay `PREMISE_BUDGET_VIOLATION` and retry.
Use `undeclared-library-prior-symbol-classifier` to validate the public symbol
bundle; it is source-open classifier metadata, not theorem proof authority.

`lean_std_premise_index` isolates the premise-index substrate itself as a
closed public metadata lane: Init-sourced declaration refs, namespace
coverage, split eligibility, and retrieval terms. It rejects Mathlib refs,
proof bodies, oracle-needed ids, test-split tuning, provider authority, and
release overclaims before retrieval machinery consumes the index.

`ring2_premise_retrieval_precision_recall_harness` is the retrieval-quality
boundary: it computes public synthetic precision/recall against after-the-fact
Ring-2 labels, separates retrieval misses from proof failures despite premise
hits, and requires an adversarial decoy miss. It is metric metadata, not proof,
benchmark, provider, or release authority.

`provider_context_recipe_budget_policy` is the provider-context boundary: it
validates fixed 4KB/16KB/32KB/64KB recipe budgets, ordered section fill,
omitted-section manifests, graph roles, and deliverable routes without calling
providers or exposing proof/oracle bodies. It is context metadata, not provider
or proof authority.

`public_reveal_walkthrough` validates the first-ten-minutes entry path as a
real organ. Its receipts bind the public claim, commands, evidence refs,
negative cases, and authority ceiling so the reveal is inspectable rather than
marketing-only.

`macro_projection_import_protocol` validates how macro substrate enters this
public root: source refs and pattern metadata may be projected into fixtures,
standards, paper modules, exported bundles, and receipts, while private bodies,
missing omission receipts, authority upgrades, missing validation refs, release
claims, and secret-export claims are rejected.

It also exposes a non-writing intake preview:

```bash
PYTHONPATH=src python3 -m microcosm_core.cli macro-projection-import-protocol plan --input examples/macro_projection_import_protocol/exported_projection_import_bundle
```

That board is the handoff surface for future import waves: each proposed cell
shows source refs, target refs, validation refs, selected pattern ids, copy
policy, omitted material, authority ceiling, and ready/blocked status before
anything is copied. The intake board now also carries the cell-state protocol:
`projection_status`, `cell_state`, `action_required`, status reason, landed
evidence refs, status counts, and open-actionable count. `microcosm intake` is
the public runtime bridge over that board: it shows
`formal_math_readiness_extensions` as a landed public replacement,
`projection_protocol_self_host` as the landed self-hosted status protocol, and
`runtime_reveal_import_bridge` as a landed runtime bridge with a command plus
runtime receipt.

`prediction_oracle_reconciliation` validates a synthetic prediction-engine
slice: CP1 branch resolution, CP2 target-universe gating, pre-target evidence
discipline, oracle diff grading, and bounded dossier mutation. It is not
trading or financial advice, not investment advice, not live market data, not a
provider integration, not a performance claim, and not publication or release
authority.

`standards_meta_diagnostics` is the terminal coverage diagnostic for the public
runtime spine: it checks that accepted organs remain mapped to standards,
runtime contracts, receipt refs, and authority ceilings. It is a projection
over public refs, not source authority for the registries, private macro source
access, release authority, provider authority, proof authority, or
whole-system correctness.

`cold_reader_route_map` is the executable entry-map organ: it validates the
first-run route sequence, commands, docs refs, receipt refs, and route-map
authority ceiling. It is executable public route evidence, not route-registry
authority, source mutation authority, release authority, provider authority,
secret-export authority, trading advice, or whole-system correctness.

## Validation Commands

```bash
PYTHONPATH=src python3 -m microcosm_core.validators.secret_exclusion_scan --root . --out receipts/first_wave/secret_exclusion_scan.json
PYTHONPATH=src python3 -m microcosm_core.validators.dependency_preflight --readiness core/preflight_support/organ_fixture_validator_readiness_v1.json --negative-matrix core/preflight_support/fixture_negative_case_matrix_v1.json --out receipts/preflight/dependency_preflight.json
PYTHONPATH=src python3 -m microcosm_core.validators.fixture_freshness --readiness core/preflight_support/organ_fixture_validator_readiness_v1.json --negative-matrix core/preflight_support/fixture_negative_case_matrix_v1.json --mission-dag core/preflight_support/microcosm_rebuild_mission_graph_v1.json --receipt-coverage core/preflight_support/validator_receipt_coverage_map_v1.json --out receipts/preflight/fixture_runner_freshness.json
PYTHONPATH=src python3 -m microcosm_core.validators.public_entry_docs --root . --out receipts/first_wave/public_entry_docs_validation.json
PYTHONPATH=src python3 -m microcosm_core.organs.formal_math_readiness_gate run --input fixtures/first_wave/formal_math_readiness_gate/input --out receipts/first_wave/formal_math_readiness_gate
PYTHONPATH=src python3 -m microcosm_core.cli formal-math-readiness-gate plan --input fixtures/first_wave/formal_math_readiness_gate/input
PYTHONPATH=src python3 -m microcosm_core.organs.corpus_readiness_mathlib_absence_gate run --input fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input --out receipts/first_wave/corpus_readiness_mathlib_absence_gate
PYTHONPATH=src python3 -m microcosm_core.cli corpus-readiness-mathlib-absence-gate run-projection-bundle --input examples/corpus_readiness_mathlib_absence_gate/exported_corpus_readiness_bundle --out receipts/runtime_shell/demo_project/organs/corpus_readiness_mathlib_absence_gate
PYTHONPATH=src python3 -m microcosm_core.cli tour /tmp/microcosm-scratch
PYTHONPATH=src python3 -m microcosm_core.cli corpus-lens
PYTHONPATH=src python3 -m microcosm_core.cli import-projector
PYTHONPATH=src python3 -m microcosm_core.cli option-surface-lens
PYTHONPATH=src python3 -m microcosm_core.organs.mathematical_strategy_atlas_hypothesis_scorer run --input fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer/input --out receipts/first_wave/mathematical_strategy_atlas_hypothesis_scorer
PYTHONPATH=src python3 -m microcosm_core.cli mathematical-strategy-atlas-hypothesis-scorer run-strategy-bundle --input examples/mathematical_strategy_atlas_hypothesis_scorer/exported_mathematical_strategy_atlas_bundle --out receipts/runtime_shell/demo_project/organs/mathematical_strategy_atlas_hypothesis_scorer
PYTHONPATH=src python3 -m microcosm_core.organs.tactic_portfolio_availability_probe run --input fixtures/first_wave/tactic_portfolio_availability_probe/input --out receipts/first_wave/tactic_portfolio_availability_probe --acceptance-out receipts/acceptance/first_wave/tactic_portfolio_availability_probe_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli tactic-portfolio-availability-probe run-availability-bundle --input examples/tactic_portfolio_availability_probe/exported_tactic_portfolio_availability_bundle --out receipts/runtime_shell/demo_project/organs/tactic_portfolio_availability_probe
PYTHONPATH=src python3 -m microcosm_core.organs.target_shape_tactic_routing_gate run --input fixtures/first_wave/target_shape_tactic_routing_gate/input --out receipts/first_wave/target_shape_tactic_routing_gate
PYTHONPATH=src python3 -m microcosm_core.cli target-shape-tactic-routing-gate run-routing-bundle --input examples/target_shape_tactic_routing_gate/exported_target_shape_tactic_routing_bundle --out receipts/runtime_shell/demo_project/organs/target_shape_tactic_routing_gate
PYTHONPATH=src python3 -m microcosm_core.organs.lean_std_premise_index run --input fixtures/first_wave/lean_std_premise_index/input --out receipts/first_wave/lean_std_premise_index --acceptance-out receipts/acceptance/first_wave/lean_std_premise_index_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli lean-std-premise-index run-index-bundle --input examples/lean_std_premise_index/exported_lean_std_premise_index_bundle --out receipts/runtime_shell/demo_project/organs/lean_std_premise_index
PYTHONPATH=src python3 -m microcosm_core.organs.formal_math_premise_retrieval run --input fixtures/first_wave/formal_math_premise_retrieval/input --out receipts/first_wave/formal_math_premise_retrieval
PYTHONPATH=src python3 -m microcosm_core.cli formal-math-premise-retrieval run-retrieval-bundle --input examples/formal_math_premise_retrieval/exported_premise_retrieval_bundle --out receipts/runtime_shell/demo_project/organs/formal_math_premise_retrieval
PYTHONPATH=src python3 -m microcosm_core.organs.formal_math_verifier_trace_repair_loop run --input fixtures/first_wave/formal_math_verifier_trace_repair_loop/input --out receipts/first_wave/formal_math_verifier_trace_repair_loop
PYTHONPATH=src python3 -m microcosm_core.cli formal-math-verifier-trace-repair-loop run-loop-bundle --input examples/formal_math_verifier_trace_repair_loop/exported_verifier_trace_repair_bundle --out receipts/runtime_shell/demo_project/organs/formal_math_verifier_trace_repair_loop
PYTHONPATH=src python3 -m microcosm_core.organs.formal_evidence_cell_anchor_resolver run --input fixtures/first_wave/formal_evidence_cell_anchor_resolver/input --out receipts/first_wave/formal_evidence_cell_anchor_resolver
PYTHONPATH=src python3 -m microcosm_core.cli formal-evidence-cell-anchor-resolver run-anchor-bundle --input examples/formal_evidence_cell_anchor_resolver/exported_evidence_cell_anchor_bundle --out receipts/runtime_shell/demo_project/organs/formal_evidence_cell_anchor_resolver
PYTHONPATH=src python3 -m microcosm_core.organs.undeclared_library_prior_symbol_classifier run --input fixtures/first_wave/undeclared_library_prior_symbol_classifier/input --out receipts/first_wave/undeclared_library_prior_symbol_classifier
PYTHONPATH=src python3 -m microcosm_core.cli undeclared-library-prior-symbol-classifier run-symbol-bundle --input examples/undeclared_library_prior_symbol_classifier/exported_symbol_classifier_bundle --out receipts/runtime_shell/demo_project/organs/undeclared_library_prior_symbol_classifier
PYTHONPATH=src python3 -m microcosm_core.organs.ring2_premise_retrieval_precision_recall_harness run --input fixtures/first_wave/ring2_premise_retrieval_precision_recall_harness/input --out receipts/first_wave/ring2_premise_retrieval_precision_recall_harness
PYTHONPATH=src python3 -m microcosm_core.cli ring2-premise-retrieval-precision-recall-harness run-precision-recall-bundle --input examples/ring2_premise_retrieval_precision_recall_harness/exported_ring2_precision_recall_bundle --out receipts/runtime_shell/demo_project/organs/ring2_premise_retrieval_precision_recall_harness
PYTHONPATH=src python3 -m microcosm_core.organs.provider_context_recipe_budget_policy run --input fixtures/first_wave/provider_context_recipe_budget_policy/input --out receipts/first_wave/provider_context_recipe_budget_policy
PYTHONPATH=src python3 -m microcosm_core.cli provider-context-recipe-budget-policy run-budget-bundle --input examples/provider_context_recipe_budget_policy/exported_provider_context_budget_bundle --out receipts/runtime_shell/demo_project/organs/provider_context_recipe_budget_policy
PYTHONPATH=src python3 -m microcosm_core.organs.formal_math_lean_proof_witness run --input fixtures/first_wave/formal_math_lean_proof_witness/input --out receipts/first_wave/formal_math_lean_proof_witness
PYTHONPATH=src python3 -m microcosm_core.cli formal-math-lean-proof-witness run-witness-bundle --input examples/formal_math_lean_proof_witness/exported_lean_proof_witness_bundle --out receipts/runtime_shell/demo_project/organs/formal_math_lean_proof_witness
PYTHONPATH=src python3 -m microcosm_core.organs.verifier_lab_kernel run --input fixtures/first_wave/verifier_lab_kernel/input --out receipts/first_wave/verifier_lab_kernel
PYTHONPATH=src python3 -m microcosm_core.cli proof-lab --out receipts/runtime_shell/demo_project/organs/verifier_lab_kernel
PYTHONPATH=src python3 -m microcosm_core.organs.public_reveal_walkthrough run --input fixtures/first_wave/public_reveal_walkthrough/input --out receipts/first_wave/public_reveal_walkthrough
PYTHONPATH=src python3 -m microcosm_core.organs.macro_projection_import_protocol run --input fixtures/first_wave/macro_projection_import_protocol/input --out receipts/first_wave/macro_projection_import_protocol
PYTHONPATH=src python3 -m microcosm_core.cli macro-projection-import-protocol run-projection-bundle --input examples/macro_projection_import_protocol/exported_projection_import_bundle --out receipts/runtime_shell/demo_project/organs/macro_projection_import_protocol
PYTHONPATH=src python3 -m microcosm_core.organs.prediction_oracle_reconciliation run --input fixtures/first_wave/prediction_oracle_reconciliation/input --out receipts/first_wave/prediction_oracle_reconciliation
PYTHONPATH=src python3 -m microcosm_core.cli prediction-oracle-reconciliation run-prediction-bundle --input examples/prediction_oracle_reconciliation/exported_prediction_oracle_bundle --out receipts/runtime_shell/demo_project/organs/prediction_oracle_reconciliation
PYTHONPATH=src python3 -m microcosm_core.organs.research_replication_rubric_artifact_replay run --input fixtures/first_wave/research_replication_rubric_artifact_replay/input --out receipts/first_wave/research_replication_rubric_artifact_replay --acceptance-out receipts/acceptance/first_wave/research_replication_rubric_artifact_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli research-replication-rubric-artifact-replay run-replication-bundle --input examples/research_replication_rubric_artifact_replay/exported_research_replication_bundle --out receipts/runtime_shell/demo_project/organs/research_replication_rubric_artifact_replay
PYTHONPATH=src python3 -m microcosm_core.organs.world_model_projection_drift_control_room run --input fixtures/first_wave/world_model_projection_drift_control_room/input --out receipts/first_wave/world_model_projection_drift_control_room --acceptance-out receipts/acceptance/first_wave/world_model_projection_drift_control_room_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli world-model-projection-drift-control-room run-drift-control-bundle --input examples/world_model_projection_drift_control_room/exported_projection_drift_control_bundle --out receipts/runtime_shell/demo_project/organs/world_model_projection_drift_control_room
PYTHONPATH=src python3 -m microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay run --input fixtures/first_wave/spatial_world_model_counterfactual_simulation_replay/input --out receipts/first_wave/spatial_world_model_counterfactual_simulation_replay --acceptance-out receipts/acceptance/first_wave/spatial_world_model_counterfactual_simulation_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli spatial-world-model-counterfactual-simulation-replay run-simulation-bundle --input examples/spatial_world_model_counterfactual_simulation_replay/exported_spatial_world_model_simulation_bundle --out receipts/runtime_shell/demo_project/organs/spatial_world_model_counterfactual_simulation_replay
PYTHONPATH=src python3 -m microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay run --input fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay/input --out receipts/first_wave/materials_chemistry_closed_loop_lab_safety_replay --acceptance-out receipts/acceptance/first_wave/materials_chemistry_closed_loop_lab_safety_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli materials-chemistry-closed-loop-lab-safety-replay run-lab-bundle --input examples/materials_chemistry_closed_loop_lab_safety_replay/exported_materials_lab_safety_bundle --out receipts/runtime_shell/demo_project/organs/materials_chemistry_closed_loop_lab_safety_replay
PYTHONPATH=src python3 -m microcosm_core.organs.mechanistic_interpretability_circuit_attribution_replay run --input fixtures/first_wave/mechanistic_interpretability_circuit_attribution_replay/input --out receipts/first_wave/mechanistic_interpretability_circuit_attribution_replay --acceptance-out receipts/acceptance/first_wave/mechanistic_interpretability_circuit_attribution_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli mechanistic-interpretability-circuit-attribution-replay run-attribution-bundle --input examples/mechanistic_interpretability_circuit_attribution_replay/exported_circuit_attribution_bundle --out receipts/runtime_shell/demo_project/organs/mechanistic_interpretability_circuit_attribution_replay
PYTHONPATH=src python3 -m microcosm_core.organs.agent_monitor_redteam_falsification_replay run --input fixtures/first_wave/agent_monitor_redteam_falsification_replay/input --out receipts/first_wave/agent_monitor_redteam_falsification_replay --acceptance-out receipts/acceptance/first_wave/agent_monitor_redteam_falsification_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli agent-monitor-redteam-falsification-replay run-monitor-bundle --input examples/agent_monitor_redteam_falsification_replay/exported_monitor_redteam_bundle --out receipts/runtime_shell/demo_project/organs/agent_monitor_redteam_falsification_replay
PYTHONPATH=src python3 -m microcosm_core.organs.agent_sabotage_scheming_monitor_replay run --input fixtures/first_wave/agent_sabotage_scheming_monitor_replay/input --out receipts/first_wave/agent_sabotage_scheming_monitor_replay --acceptance-out receipts/acceptance/first_wave/agent_sabotage_scheming_monitor_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli agent-sabotage-scheming-monitor-replay run-sabotage-bundle --input examples/agent_sabotage_scheming_monitor_replay/exported_sabotage_monitor_bundle --out receipts/runtime_shell/demo_project/organs/agent_sabotage_scheming_monitor_replay
PYTHONPATH=src python3 -m microcosm_core.organs.agent_sandbox_policy_escape_replay run --input fixtures/first_wave/agent_sandbox_policy_escape_replay/input --out receipts/first_wave/agent_sandbox_policy_escape_replay --acceptance-out receipts/acceptance/first_wave/agent_sandbox_policy_escape_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli agent-sandbox-policy-escape-replay run-sandbox-bundle --input examples/agent_sandbox_policy_escape_replay/exported_sandbox_policy_escape_bundle --out receipts/runtime_shell/demo_project/organs/agent_sandbox_policy_escape_replay
PYTHONPATH=src python3 -m microcosm_core.organs.indirect_prompt_injection_information_flow_policy_replay run --input fixtures/first_wave/indirect_prompt_injection_information_flow_policy_replay/input --out receipts/first_wave/indirect_prompt_injection_information_flow_policy_replay --acceptance-out receipts/acceptance/first_wave/indirect_prompt_injection_information_flow_policy_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli indirect-prompt-injection-information-flow-policy-replay run-prompt-injection-bundle --input examples/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle --out receipts/runtime_shell/demo_project/organs/indirect_prompt_injection_information_flow_policy_replay
PYTHONPATH=src python3 -m microcosm_core.organs.agentic_vulnerability_discovery_patch_proof_replay run --input fixtures/first_wave/agentic_vulnerability_discovery_patch_proof_replay/input --out receipts/first_wave/agentic_vulnerability_discovery_patch_proof_replay --acceptance-out receipts/acceptance/first_wave/agentic_vulnerability_discovery_patch_proof_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli agentic-vulnerability-discovery-patch-proof-replay run-patch-proof-bundle --input examples/agentic_vulnerability_discovery_patch_proof_replay/exported_patch_proof_bundle --out receipts/runtime_shell/demo_project/organs/agentic_vulnerability_discovery_patch_proof_replay
PYTHONPATH=src python3 -m microcosm_core.organs.agent_memory_temporal_conflict_replay run --input fixtures/first_wave/agent_memory_temporal_conflict_replay/input --out receipts/first_wave/agent_memory_temporal_conflict_replay --acceptance-out receipts/acceptance/first_wave/agent_memory_temporal_conflict_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli agent-memory-temporal-conflict-replay run-memory-bundle --input examples/agent_memory_temporal_conflict_replay/exported_memory_temporal_conflict_bundle --out receipts/runtime_shell/demo_project/organs/agent_memory_temporal_conflict_replay
PYTHONPATH=src python3 -m microcosm_core.organs.sleeper_memory_poisoning_quarantine_replay run --input fixtures/first_wave/sleeper_memory_poisoning_quarantine_replay/input --out receipts/first_wave/sleeper_memory_poisoning_quarantine_replay --acceptance-out receipts/acceptance/first_wave/sleeper_memory_poisoning_quarantine_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli sleeper-memory-poisoning-quarantine-replay run-quarantine-bundle --input examples/sleeper_memory_poisoning_quarantine_replay/exported_sleeper_memory_poisoning_bundle --out receipts/runtime_shell/demo_project/organs/sleeper_memory_poisoning_quarantine_replay
PYTHONPATH=src python3 -m microcosm_core.organs.mcp_tool_authority_replay run --input fixtures/first_wave/mcp_tool_authority_replay/input --out receipts/first_wave/mcp_tool_authority_replay --acceptance-out receipts/acceptance/first_wave/mcp_tool_authority_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli mcp-tool-authority-replay run-tool-authority-bundle --input examples/mcp_tool_authority_replay/exported_mcp_tool_authority_bundle --out receipts/runtime_shell/demo_project/organs/mcp_tool_authority_replay
PYTHONPATH=src python3 -m microcosm_core.organs.proof_derived_governed_mutation_authorization run --input fixtures/first_wave/proof_derived_governed_mutation_authorization/input --out receipts/first_wave/proof_derived_governed_mutation_authorization --acceptance-out receipts/acceptance/first_wave/proof_derived_governed_mutation_authorization_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli proof-derived-governed-mutation-authorization run-authorization-bundle --input examples/proof_derived_governed_mutation_authorization/exported_governed_mutation_authorization_bundle --out receipts/runtime_shell/demo_project/organs/proof_derived_governed_mutation_authorization
PYTHONPATH=src python3 -m microcosm_core.organs.belief_state_process_reward_replay run --input fixtures/first_wave/belief_state_process_reward_replay/input --out receipts/first_wave/belief_state_process_reward_replay --acceptance-out receipts/acceptance/first_wave/belief_state_process_reward_replay_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli belief-state-process-reward-replay run-reward-bundle --input examples/belief_state_process_reward_replay/exported_belief_state_process_reward_bundle --out receipts/runtime_shell/demo_project/organs/belief_state_process_reward_replay
PYTHONPATH=src python3 -m microcosm_core.organs.standards_meta_diagnostics run --input fixtures/first_wave/standards_meta_diagnostics/input --out receipts/first_wave/standards_meta_diagnostics --acceptance-out receipts/acceptance/first_wave/standards_meta_diagnostics_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli standards-meta-diagnostics run-diagnostics-bundle --input examples/standards_meta_diagnostics/exported_standards_meta_diagnostics_bundle --out receipts/runtime_shell/demo_project/organs/standards_meta_diagnostics
PYTHONPATH=src python3 -m microcosm_core.organs.cold_reader_route_map run --input fixtures/first_wave/cold_reader_route_map/input --out receipts/first_wave/cold_reader_route_map --acceptance-out receipts/acceptance/first_wave/cold_reader_route_map_fixture_acceptance.json
PYTHONPATH=src python3 -m microcosm_core.cli cold-reader-route-map run-route-map-bundle --input examples/cold_reader_route_map/exported_cold_reader_route_map_bundle --out receipts/runtime_shell/demo_project/organs/cold_reader_route_map
PYTHONPATH=src python3 -m microcosm_core.validators.research_kernel_density --root . --project /tmp/microcosm-scratch --out receipts/first_wave/research_kernel_density.json
PYTHONPATH=src python3 -m microcosm_core.validators.transaction_evidence_stability --root . --project /tmp/microcosm-scratch --out receipts/first_wave/transaction_evidence_stability.json
PYTHONPATH=src python3 -m microcosm_core.validators.observatory_legibility --root . --project /tmp/microcosm-scratch --out receipts/first_wave/observatory_legibility.json
PYTHONPATH=src python3 -m microcosm_core.validators.launch_compression --root . --project /tmp/microcosm-scratch --out receipts/first_wave/launch_compression.json
./bootstrap.sh --suite first-wave --emit receipts/cold_clone_probe.json
python -m pytest -q
```

Use the organ commands in `core/organ_registry.json` for individual validation
runs. Receipts under `receipts/**` are generated evidence from commands. They
should not be edited by hand.

## Public Entry Map

- `core/organ_registry.json` lists accepted organs, commands, and generated
  receipts.
- `core/acceptance/first_wave_acceptance.json` records the current acceptance
  boundary.
- `core/standards_registry.json` and `standards/*.json` describe public
  standard rows.
- `paper_modules/*.md` are cold-read summaries of accepted organs and deferred
  proof boundaries.
- `paper_modules/public_reveal_walkthrough.md` explains the ten-minute public
  reveal organ.
- `paper_modules/macro_projection_import_protocol.md` explains the real
  macro-substrate import membrane and its body-import verification floor.
- `paper_modules/prediction_oracle_reconciliation.md` explains the synthetic
  prediction-reconciliation organ and its no-trading/no-advice authority
  ceiling.
- `paper_modules/standards_meta_diagnostics.md` explains the terminal standards
  coverage diagnostic and its projection-only authority ceiling.
- `paper_modules/research_replication_rubric_artifact_replay.md` explains the
  synthetic research-replication replay rubric and artifact-rerun boundary.
- `paper_modules/cold_reader_route_map.md` explains the executable route map
  for the ten-minute cold-reader path.
- `paper_modules/corpus_readiness_mathlib_absence.md` explains the Mathlib
  absence and corpus-readiness gate.
- `paper_modules/mathematical_strategy_atlas.md` explains the pre-oracle
  mathematical strategy atlas and typed strategy-miss boundary.
- `paper_modules/formal_math_premise_retrieval.md` explains the first
  retrieval-grade formal-math import slice.
- `paper_modules/formal_evidence_cell_anchor_resolver.md` explains the public
  evidence-cell claim boundary.
- `paper_modules/undeclared_library_prior_classifier.md` explains the payload-boundary
  proof-symbol classifier and premise-budget precedence boundary.
- `paper_modules/lean_std_premise_index.md` explains the closed Lean/Std
  premise metadata index and its proof/Mathlib authority ceiling.
- `paper_modules/provider_context_recipe_budget.md` explains the provider
  context recipe budget boundary.
- `skills/cold_start_navigation.md` gives the shortest safe path for a fresh
  public clone.

## License Posture

This microcosm substrate is licensed under Apache-2.0. That license posture
applies to this standalone root and its included tests, fixtures, validators,
receipts, and documentation. It does not authorize hosting, credentialed
provider calls, recipient sends, or secret export.

## Boundary

The public substrate should carry real source-available macro mechanisms,
runnable input bundles, schema rows, fixtures for tests, source-open lineage,
validators, and receipt contracts. It must not carry secrets,
credential-equivalent live access, live operator state, raw private operator
text, provider payload bodies, browser/HUD/cockpit account state, recipient
sends, or old scratch-root contents as source authority.

Anti-claim: this README documents public runtime-spine entry and validation
only. It does not authorize trading, financial or investment advice, live
market data, hosted deployment, publication, recipient work, credentialed
provider calls, secret export, Lean/Lake execution beyond the bounded public
witness fixture, or whole-system correctness. These docs do not authorize
release operations; they do authorize honest source-available Microcosm content
inside this repo.
