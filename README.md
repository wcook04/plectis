# Microcosm Substrate

Microcosm is the public, source-open cross-section of a larger private
AI-native workflow system. It exists to make the system's architecture,
evidence habits, component families, and claim limits inspectable without
publishing the full working system.

The package in this folder is one concrete witness for that public slice. When
run locally, it turns repo -> .microcosm beside a project so a reader can
inspect routes, events, evidence handles, and source links without changing
source files or making external model calls.

For a one-page cold-clone path, start with [QUICKSTART.md](QUICKSTART.md).
For the first local card from a source checkout, run
`PYTHONPATH=src python3 -m microcosm_core hello .`; after install, run
`microcosm hello .`.

## Public Repo Map

Use this map before opening the longer reference body or raw receipt trees:

| Surface | Use it for |
|---|---|
| [QUICKSTART.md](QUICKSTART.md) | One-page cold-clone run path and boundary check. |
| [AGENTS.md](AGENTS.md) | Agent entry contract and public authority membrane. |
| [CONSTITUTION.md](CONSTITUTION.md) / [AXIOMS.md](AXIOMS.md) / [PRINCIPLES.md](PRINCIPLES.md) / [ANTI_PRINCIPLES.md](ANTI_PRINCIPLES.md) | Root doctrine: authority spine, public-safe source rules, operating principles, and rejected failure shapes. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Public verification floor, standalone export path, and contribution boundaries. |
| [SECURITY.md](SECURITY.md) | Secret-exclusion and vulnerability-reporting boundary. |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) / [Makefile](Makefile) | GitHub Actions and local command surface; both route through `make ci`. |
| [pyproject.toml](pyproject.toml) / [MANIFEST.in](MANIFEST.in) | Package metadata, console entry point, and source distribution inventory. |
| [src/microcosm_core/](src/microcosm_core/) / [tests/](tests/) | Runnable substrate and regression contracts. |
| [core/](core/) / [standards/](standards/) / [paper_modules/](paper_modules/) | Public registries, standards, and bounded organ summaries. |
| [examples/](examples/) / [fixtures/](fixtures/) / [receipts/](receipts/) | Input bundles, negative cases, and drilldown evidence. |

This map is navigation only. Receipts and counts remain drilldown evidence, and
none of these links authorize release, hosting, provider calls, source
mutation, private-root equivalence, or proof authority.

## Component Map

Read the tree as cooperating component families before treating any receipt
count, organ count, or route label as a claim:

| Component family | Local surface | What to inspect |
|---|---|---|
| Runtime package | [src/microcosm_core/](src/microcosm_core/) | CLI-backed local behavior: first-screen cards, project scan, route selection, validators, server, and release export. |
| Command cards | `hello`, `tour --card`, `status --card`, `authority --card`, `workingness --card` | The copyable first screen, behavior proof, evidence classes, authority ceiling, and failure envelope. |
| Public doctrine | [core/](core/), [standards/](standards/), [paper_modules/](paper_modules/), [atlas/](atlas/) | Organ registry, standards, bounded explanations, and the first-screen entry packet. |
| Evidence fixtures | [examples/](examples/), [fixtures/](fixtures/), [receipts/](receipts/) | Public-safe input bundles, negative cases, drilldown receipts, and copied artifact bodies. |
| Source capsules | `source_modules/` plus `source_module_manifest.json` inside bundles | Non-secret macro source bodies with target paths, digests, anchors, omissions, and light-edit receipts. |
| Validation shell | [tests/](tests/), [Makefile](Makefile), [.github/workflows/ci.yml](.github/workflows/ci.yml) | The public verification floor that keeps docs, CLI cards, fixtures, packaging, and standalone export honest. |

This component map is still navigation, not authority. The command cards,
validators, manifests, and receipts remain the evidence-bearing surfaces.

New here? Two generated surfaces give you the whole system fast:
[ARCHITECTURE.md](ARCHITECTURE.md) is the architecture at a glance, and
[ORGANS.md](ORGANS.md) is the comprehension card for all 48 runtime organs.

From an uninstalled source checkout, the immediately runnable first screen is:

```bash
PYTHONPATH=src python3 -m microcosm_core hello .
```

After `python3 -m pip install -e '.[test]'` or `make install`, the same card
is available as the console command:

```bash
microcosm hello .
```

Run `microcosm compile .` when you want the full `.microcosm/` rebuild JSON
after the first-screen card is legible.

## Choose Your First Screen

If you only read one terminal screen, ask the package-backed card for the map:

```bash
microcosm hello <project>
```

`hello` is the text projection of the first-screen card. It is not a separate
proof surface. It sends every reader through the same local behavior command
before branching:

```bash
microcosm tour --card <project>
```

Use `microcosm first-screen --card <project>` when you want the same reader
map as compact JSON instead of terminal text. The plain
`microcosm first-screen <project>` form stays valid for scripts that already
use it.

After that shared card, branch by reader instead of forcing one README to carry
every job:

If an agent lands on this README, the agent-facing equivalent is `AGENTS.md`;
use it after this human first-screen map, then follow `skills/cold_start_navigation.md`
for the shortest validation route.

| Reader | Open next | What to check |
|---|---|---|
| Public GitHub visitor | `microcosm hello <project>`, then `microcosm tour --card <project>` | The copyable first command, shared local behavior proof, authority ceiling, and anti-claims before opening receipts or treating the repo as release-ready. |
| Safety/evals engineer | `microcosm status --card <project>`, then `microcosm authority --card`, then `microcosm workingness --card` | Evidence classes, source-open body imports, authority ceilings, anti-claims, missing standards, and failure modes; open full authority/workingness only as drilldowns. |
| Hiring reviewer | `microcosm legibility-scorecard`, then `microcosm tour --card <project>` | The question-to-command scorecard, endpoint parity, local behavior, and the explicit rejection of reader-success, release, benchmark, and production claims. |
| Peer developer | `microcosm tour --card <project>`, then `microcosm observe <project>` | The generated `.microcosm/` files, selected route id, route/work/event/evidence graph chain, and `source_files_mutated=false`. |

Evidence counts are accounting, not maturity scores. Low counts are not hidden:
they tell you exactly which claims are backed by copied source bodies, external
subprocess receipts, algorithmic projections, metadata-only rows, or explicit
omissions. Most projects do not publish that boundary; Microcosm puts it on the
first screen so strong claims stay narrow.

Read the evidence class counters as a claim-boundary legend:

| Evidence class | What the count means | What it does not mean |
|---|---|---|
| `verified_macro_body_import` | Non-secret macro source body copied into the public tree with a target, digest, validator, or receipt. | Private-root equivalence, release readiness, or source authority above the validator. |
| `external_subprocess_witness` | A bounded local tool return code or subprocess receipt exists. | General proof authority or correctness outside the declared witness. |
| `algorithmic_projection` | A deterministic computation over public/local rows produced the value. | Domain correctness or real-world validation. |
| `semantic_validator` | A validator checked declared schema, policy, or routing semantics. | Runtime behavior, release authority, or source mutation permission. |
| `fixture_schema_replay` / `fixture_echo_smoke` | Fixture or smoke coverage protects a contract and its negative cases. | Product completeness, safety validation, or benchmark evidence. |

When a bundle includes `source_modules/`, treat those files as exact
non-secret source capsules, not standalone documentation trees. Their internal
links may still point to macro-root files outside this public slice; the
adjacent `source_module_manifest.json` is the navigation authority for copied
targets, digests, anchors, and omissions.

## Rigor Without Ceremony

The discipline is visible because Microcosm refuses to collapse different
questions into one green badge:

| Cold-reader question | Microcosm surface | Why it matters |
|---|---|---|
| What ran locally? | `microcosm tour --card <project>` and `.microcosm/` refs. | The demo is a source-local behavior proof, not a prose claim. |
| What backs each claim? | Evidence classes, receipts, validators, and source-open body-import counts. | Counts stay legible as claim boundaries instead of maturity scores. |
| What is not authorized? | `authority_ceiling`, anti-claims, and `source_files_mutated=false`. | The first screen blocks release, provider, proof, and source-mutation overreads. |
| What still needs inspection? | Failure modes, missing standards, and compact drilldown refs. | Warnings remain visible without turning the first screen into the full audit. |

If another system gives only a status badge, ask for these four separations.
They are what make the compact card smaller without making its claims broader.

## Demo To Scale Bridge

The browser first screen has a `Demo To Scale` bridge so the local run and the
structural evidence do not live in separate places.

1. `microcosm tour --card <project>` proves the local behavior: it writes
   `.microcosm/` state, selects a route, and exposes compact route/work/event/
   evidence refs without mutating source or calling providers.
2. `microcosm serve <project> --host 127.0.0.1 --port 8765` opens the same
   first-screen card plus four bridge cards: `Local demo`, `Structural scale`,
   `Evidence floor`, and `Authority boundary`. For a bounded route smoke, use
   `microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 6`.
3. `/project/observatory-card` is the JSON card for that bridge;
   `/project/status` is the compact body-import and authority lens; the full
   `/project/observatory` model stays a drilldown.

For a bounded validation run, add `--max-requests N`; the local server exits
cleanly after serving that many HTTP requests, so route smokes do not need an
external interrupt.

If the first run only shows `.microcosm/`, you have not seen the scale claim
yet. If the status card only shows body-import counts, you have not seen the
local proof yet. The bridge is the join: runnable local behavior, structural
breadth, honest evidence accounting, and authority limits on one first screen.

## Try It On Your Repo

From `microcosm-substrate/` in a local checkout or generated standalone export,
install the console command from this source tree:

```bash
python3 -m pip install .
```

That is a local-source smoke path, not a PyPI, wheel, hosted-release, or
operator-release claim. Use the standalone export section below when you need a
reviewable candidate artifact.

For development, install the same command in editable mode with the test extras:

```bash
python3 -m pip install -e '.[test]'
```

Either install path should pass the first-screen self-check:

```bash
microcosm hello .
microcosm tour --card .
microcosm status --card .
```

Or run the same product CLI directly from the checkout without installing the
entry point:

```bash
PYTHONPATH=src python3 -m microcosm_core hello .
PYTHONPATH=src python3 -m microcosm_core tour --card .
PYTHONPATH=src python3 -m microcosm_core first-screen --card .
PYTHONPATH=src python3 -m microcosm_core status --card .
PYTHONPATH=src python3 -m microcosm_core proof-lab --out /tmp/microcosm-proof-lab
PYTHONPATH=src python3 -m microcosm_core observe .
```

After the console command is installed, the first-screen path is:

```bash
microcosm hello .
microcosm tour --card .
microcosm first-screen --card .
microcosm status --card .
microcosm workingness --card
microcosm proof-lab --out /tmp/microcosm-proof-lab
microcosm observe .
microcosm serve . --host 127.0.0.1 --port 8765 --max-requests 6
microcosm compile .
microcosm python-lens .
microcosm explain . <selected_route_id>
microcosm evidence list . --limit 25
microcosm evidence inspect . .microcosm/evidence/routes.json
microcosm tour .
microcosm pattern-route-readiness validate-bundle --input examples/pattern_binding_contract/exported_route_readiness_bundle --out /tmp/microcosm-pattern-route-readiness
```

The quickest human first screen is `microcosm hello .`. Its observatory line
uses the bounded serve validation command so a first-screen route smoke can
exit by itself. The local behavior
proof is the compact `microcosm tour --card .` JSON: it writes the local
`.microcosm/` state, names the selected project route id, exposes
`state_inspection` plus route/work/event/evidence/graph refs, points to the
status card, compact workingness card, `microcosm observe <project>`
causal-chain command, observatory command, proof-lab command, and authority
ceiling, and keeps route cards plus receipt refs out of the cockpit.
Run `microcosm tour .` only when you want the full route-card, endpoint-path,
and evidence-ref drilldown.
In that full packet, `route_cards_by_id.status_and_workingness` remains the
status and workingness drilldown, not the first screen.
Use
`selected_route_id` from `microcosm tour --card .`, `microcosm tour .`, or
`microcosm compile .` for `microcosm explain . <selected_route_id>`; do not hardcode
`readme_onboarding_route` for arbitrary folders. `readme_onboarding_route` is
present when the project has a README, while a folder without a README uses
another generated route, for example `missing_tests_route` when tests are
absent. Open
`http://127.0.0.1:8765/project/status` for the same compact status-card lens as
`microcosm status --card <project>`, then
`http://127.0.0.1:8765/project/first-screen` for the same compact one-screen
reader map as `microcosm first-screen --card <project>`, then
`http://127.0.0.1:8765/project/observatory-card` for the compact JSON card that
ties `state_inspection`, status, route, work, evidence, graph, proof, and
safe-to-show boundaries together before opening `http://127.0.0.1:8765` or the full
`/project/observatory` model. Use `/project/first-screen-full` only when you
want the full first-screen contract behind that compact browser entry. Use
`http://127.0.0.1:8765/workingness-card` for the compact browser workingness
card, and `/workingness` only when you need the full per-organ failure map. The
output folder is `.microcosm/`.

Use `microcosm status --card <project>` after `tour` or `compile` for the
compressed first-screen lens over local `.microcosm/` route state plus the full
runtime status. It includes the selected project route id,
`front_door.route_selection_proof` with the `.microcosm/routes.json` source,
route-explanation status, and observatory proof ref, `front_door.route_explanation`
with the compact route/work/event/evidence chain,
`front_door.observatory.compact_endpoint=/project/observatory-card`,
`front_door.observatory.project_observe_command=microcosm observe <project>`,
`front_door.source_open_body_import_floor` with verified source-open body-import
counts, direct source-module-manifest counts, spotlighted source-module families,
and body-text exclusion flags, the shorter
`front_door.source_open_body_imports` pointer for count-first scanning,
`source_files_mutated=false`, the `microcosm workingness` counts, and a small
`gap_preview` of the first missing-standard or failure-mode rows and their
target refs before opening the full organ-by-organ map; `microcosm status`
remains the full JSON drilldown.
When serving a project, `/project/status` exposes that same compact card in the
browser while `/status` remains the full runtime status plus a project overlay.
When a project path is supplied, the card keeps `front_door.project_state` and
`macro_body_import_floor` to compact state/ref summaries and leaves route proof
plus route explanation in `front_door.route_selection_proof` and
`front_door.route_explanation`; run `microcosm status` for the full body-floor
drilldown.

Read `front_door_status` before treating the tour's `status` as a blanket
health claim. `front_door_status.status=pass` with `blocking_surface_ids=[]`
means the required first-screen path is green.
`drilldown_warning_surface_ids=["authority","intake"]` means those
surfaces remain visible bounded warnings to inspect; if one is non-pass, it is
reported under `drilldown_blocked_surface_ids`, not hidden as release
authority.
`microcosm status --card <project>` exits zero for the expected first-run
missing-state recovery card so strict shell probes can read the next command.
If it exits non-zero, keep the JSON output as the evidence packet. The field
`front_door_status.blocking_surface_ids` names the blocking first-screen
surfaces; inspect those exact surfaces, and do not treat warning drilldowns as
source, release, provider, or proof authority.
If the blocker is `project_state=missing_state`, the same card includes
`front_door.project_state.recovery`,
`front_door.project_recovery`, top-level `next_commands`, and
`front_door_status.blocking_surface_details.project_state` with
`microcosm tour --card <project>` as the primary recovery command and
`microcosm status --card <project>` as the verification command. This keeps a
status-before-tour mistake on the product route instead of sending readers into
raw receipts or doctrine.

Use `microcosm authority --card` before trusting any organ label. It gives the
compact authority ceiling first; open `microcosm authority` only when you need
the full map. Each organ still carries an explicit `evidence_class`, and
`accepted_current_authority` is not an evidence-strength claim.

The first proof-lab route is runnable from a clean clone:

```bash
microcosm proof-lab --out /tmp/microcosm-proof-lab
```

It is backed by
`receipts/first_wave/verifier_lab_kernel/exported_verifier_lab_kernel_bundle_validation_result.json`
and route metadata at
`examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle/proof_lab_route.json`.
The command prints a compact proof-lab card and writes a receipt under the
chosen `--out` directory. When local Lean/Lake are installed, it rebuilds the
bounded public witness; when they are absent, it writes a canonical-receipt
fallback card with `local_toolchain_status=missing_lean_lake` and
`live_receipt_rebuild_status=skipped_toolchain_missing` instead of pretending a
live proof rebuild occurred. The bundled canonical receipt validates route
`formal_prover_context_strategy_gate` with 9 route components, Lean/Lake return
code `0`, 8 compiled declarations, retrieval recall `1.0`, Ring2
precision/recall `0.36`/`0.9`, 5 target-shape cases, and 5 verifier attempts.
It does not export proof bodies, provider payloads, credentials,
account/session state, or release authority.
For first-screen hygiene, the card prints repo-relative proof refs, preserves
portable `/tmp/...` refs, normalizes `/private/tmp/...` to `/tmp/...`, and
uses `<proof-lab-input>` / `<proof-lab-out>` placeholders instead of leaking
host-private temp roots. The actual receipt still lands in the local directory
you passed to `--out`.

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

The private-state scanner is a bounded import membrane, not a whole-repo
secret-audit certificate. Its policy detects declared synthetic regression
sentinels and classifies explicit macro-import rows; a passing scan does not
certify that no private material exists, and scanner findings never expose
matched body text.

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

1. Start with the public system map.
2. Run one command as a local witness.
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

From this directory, install from the local source tree:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
mkdir -p /tmp/microcosm-scratch/src/app /tmp/microcosm-scratch/tests
printf '# Scratch Project\n' > /tmp/microcosm-scratch/README.md
printf '[project]\nname = "scratch-project"\nversion = "0.1.0"\n' > /tmp/microcosm-scratch/pyproject.toml
printf 'VALUE = 1\n' > /tmp/microcosm-scratch/src/app/__init__.py
printf 'from app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n' > /tmp/microcosm-scratch/tests/test_app.py

microcosm tour --card /tmp/microcosm-scratch | tee /tmp/microcosm-scratch-tour-card.json
MICROCOSM_ROUTE_ID=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["selected_route_id"])' < /tmp/microcosm-scratch-tour-card.json)
microcosm status --card /tmp/microcosm-scratch
microcosm workingness
microcosm proof-lab --out /tmp/microcosm-proof-lab
microcosm serve /tmp/microcosm-scratch --host 127.0.0.1 --port 8765 --max-requests 6
microcosm compile /tmp/microcosm-scratch
microcosm python-lens /tmp/microcosm-scratch
microcosm explain /tmp/microcosm-scratch "$MICROCOSM_ROUTE_ID"
microcosm evidence list /tmp/microcosm-scratch --limit 25
microcosm evidence inspect /tmp/microcosm-scratch .microcosm/evidence/routes.json
microcosm tour /tmp/microcosm-scratch | tee /tmp/microcosm-scratch-tour.json
microcosm pattern-route-readiness validate-bundle --input examples/pattern_binding_contract/exported_route_readiness_bundle --out /tmp/microcosm-pattern-route-readiness
```

This first run proves local install and local project inspection only. It does
not promote the checkout into a release artifact or a hosted service.

This scratch project deliberately creates a README, so its selected route is
`readme_onboarding_route`. For your own folder, use the `selected_route_id`
emitted by `microcosm tour --card`, `microcosm tour`, or `microcosm compile`;
empty/non-README folders can select `missing_tests_route`.

The same commands work without installing the console script:

```bash
PYTHONPATH=src python3 -m microcosm_core tour --card /tmp/microcosm-scratch | tee /tmp/microcosm-scratch-tour-card.json
MICROCOSM_ROUTE_ID=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["selected_route_id"])' < /tmp/microcosm-scratch-tour-card.json)
PYTHONPATH=src python3 -m microcosm_core status --card /tmp/microcosm-scratch
PYTHONPATH=src python3 -m microcosm_core workingness
PYTHONPATH=src python3 -m microcosm_core proof-lab --out /tmp/microcosm-proof-lab
PYTHONPATH=src python3 -m microcosm_core serve /tmp/microcosm-scratch --host 127.0.0.1 --port 8765 --max-requests 6
PYTHONPATH=src python3 -m microcosm_core compile /tmp/microcosm-scratch
PYTHONPATH=src python3 -m microcosm_core python-lens /tmp/microcosm-scratch
PYTHONPATH=src python3 -m microcosm_core explain /tmp/microcosm-scratch "$MICROCOSM_ROUTE_ID"
PYTHONPATH=src python3 -m microcosm_core evidence list /tmp/microcosm-scratch --limit 25
PYTHONPATH=src python3 -m microcosm_core evidence inspect /tmp/microcosm-scratch .microcosm/evidence/routes.json
PYTHONPATH=src python3 -m microcosm_core tour /tmp/microcosm-scratch
```

The older organ-adapter demo still exists for internal evidence and regression:

```bash
microcosm status
microcosm run examples/runtime_shell/demo_project
microcosm route list
microcosm evidence list --limit 25
```

Evidence receipts are the black-box recorder, not the cockpit. Start with the
project loop; open receipts only when you need a drilldown. Inspect a listed
project ref with `microcosm evidence inspect <project> <ref>` or
`microcosm evidence inspect --project <project> <ref>`. Use `--limit 0` only
when you intentionally want the full receipt index.

`microcosm tour --card <project>` is the compressed cold-reader route. It
compiles the project into `.microcosm/`, then emits a compact first-screen
card with selected route id, route/work/event/evidence/graph refs, status,
observatory, proof-lab, body-import, and boundary pointers. `microcosm tour
<project>` is the full drilldown; it emits one real-substrate ten-minute path
through spine,
authority, prediction, corpus, trace repair, repair-loop curriculum, formal
evidence cells, proof-loop depth, work landing replay, durable agent work
landing replay, research replication replay, world-model projection drift control,
view quality, projection safety, hook
intervention coverage, projection import map, import-projector contract,
compression-profile option surface, stripping guard, replay gauntlet, benchmark lab, legibility scorecard, intake, reveal,
observatory, and evidence drilldowns. The compact card does not persist the
tour receipt; the full drilldown writes
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

`bridge_phase_continuity_runtime` is the synthetic transport bridge-continuity
membrane. Run `microcosm bridge-phase-continuity-runtime run --input
fixtures/second_wave/bridge_phase_continuity_runtime/input --out
/tmp/microcosm-bridge-continuity` to validate continuation packets, heartbeat
boundaries, resource-pressure blocking, resume-once semantics, duplicate-resume
rejection, worker-skip dedupe, closeout transition receipts, and private-state
scan ceilings without live bridge transport, providers, HUD/browser state,
phase runtime state, work-landing authority, or release authority.

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
Its rows are synthetic transaction boundary rows, not benchmark scores,
score-based progress, maturity, readiness, or release evidence.

`microcosm legibility-scorecard` is the cold-reader comprehension contract. It
maps five questions to runnable proof commands, six checkpoints, endpoint
parity, evidence refs, and negative cases so a stranger can evaluate the
public reveal without reading the private macro root first. It does not prove
every reader will understand the system, claim private-root equivalence,
publish, call providers, mutate source, export benchmark scores, prove
mathematical correctness, or authorize release.
Its rows are checkpoint and boundary rows, not score-based progress, maturity,
readiness, or release evidence.

`microcosm workingness` is the per-organ failure envelope map. It compares
what each organ needs to work against the evidence Microcosm currently has:
owning standard, typed failure modes, validator command, authority receipt,
generated receipts, evidence class, claim ceiling, and public/private
boundary. Its top-level count lens repeats the mapped-organ, adapter-backed,
demoted-drilldown, missing-standard, missing-failure-mode, and gap-preview
fields before the full per-organ rows. It emits concrete future-work targets
without becoming a maturity board, activation label, release signal, or
score-based progress surface.

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
map in browser form, `/workingness-card` adds the compact workingness card,
`/workingness` remains the full per-organ failure envelope map,
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

The public package carries 48 accepted public runtime organs behind the local
substrate loop. Treat that as a public entry inventory/read-model over
`core/organ_registry.json` and `core/organ_evidence_classes.json`, not a product progress meter.
`accepted_current_authority`, organ counts, and adapter-backed counts are
inventory-only route-alignment metadata, not product progress, release readiness, product
completeness, proof authority, private-root equivalence, or whole-system correctness. These rows do not authorize release, and the prediction and market organs are
evidence boundaries, not trading or financial advice.

**Read the organs through the generated atlas, not a flat list:**

- **[ORGANS.md](ORGANS.md)** — the comprehension card for every organ: what it
  makes visible (plain language), what an agent runs it for, its first command,
  its evidence class, and what it does **not** authorize.
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — the system at a glance: the local
  runtime loop, the claim/evidence loop, the kernel primitives, and how the
  seven families sit on one shared spine.

Both files are generated from substrate by
`PYTHONPATH=src python3 scripts/build_organ_atlas.py --write`; the build fails
closed if the registry, the family grouping, and the glosses disagree. Most
organs are standalone specimens that bind to one shared kernel + evidence spine
rather than calling each other; each card in [ORGANS.md](ORGANS.md) says whether
it is standalone or wired.

Fixture and validator readiness for these organs is tracked in-tree at
`core/preflight_support/organ_fixture_validator_readiness_v1.json` and
`core/preflight_support/fixture_negative_case_matrix_v1.json`, never from parent
state. Drilldown CLIs such as `microcosm reveal` and `microcosm spatial-simulation`
are documented per organ in [ORGANS.md](ORGANS.md).

The 48 organs cluster into seven families (full cards in [ORGANS.md](ORGANS.md)):

### Entry & Reveal (2)

How a cold human or agent first meets Microcosm and what the short guided path actually proves.

`cold_reader_route_map`, `public_reveal_walkthrough`

### Architecture & Navigation (6)

The kernel primitives, pattern binding, doctrine grammar, route plane, and standards that give the system its shape and let you navigate it.

`pattern_binding_contract`, `pattern_assimilation_step`, `executable_doctrine_grammar`, `navigation_hologram_route_plane`, `standards_meta_diagnostics`, `voice_to_doctrine_self_improvement_loop`

### Formal Math & Proof (17)

The Lean/proof evidence pipeline: corpus readiness, premise retrieval, tactic routing, verifier trace repair, bounded witnesses, and certificates.

`proof_diagnostic_evidence_spine`, `formal_math_readiness_gate`, `corpus_readiness_mathlib_absence_gate`, `mathematical_strategy_atlas_hypothesis_scorer`, `tactic_portfolio_availability_probe`, `target_shape_tactic_routing_gate`, `lean_std_premise_index`, `formal_math_premise_retrieval`, `formal_math_verifier_trace_repair_loop`, `formal_evidence_cell_anchor_resolver`, `undeclared_library_prior_symbol_classifier`, `ring2_premise_retrieval_precision_recall_harness`, `formal_math_lean_proof_witness`, `verifier_lab_kernel`, `verifier_lab_execution_spine`, `certificate_kernel_execution_lab`, `proof_derived_governed_mutation_authorization`

### Agent Reliability & Safety Replays (12)

Source-open replay specimens for agent failure modes: red-team monitors, sabotage, sandbox escape, prompt injection, tool authority, memory poisoning, benchmark gaming, route observability, and provider budgets.

`agent_benchmark_integrity_anti_gaming_replay`, `agent_monitor_redteam_falsification_replay`, `agent_sabotage_scheming_monitor_replay`, `agent_memory_temporal_conflict_replay`, `sleeper_memory_poisoning_quarantine_replay`, `mcp_tool_authority_replay`, `belief_state_process_reward_replay`, `agent_sandbox_policy_escape_replay`, `indirect_prompt_injection_information_flow_policy_replay`, `agentic_vulnerability_discovery_patch_proof_replay`, `agent_route_observability_runtime`, `provider_context_recipe_budget_policy`

### Research & Science Replays (5)

Replay specimens that project scientific and forecasting workflows: replication rubrics, spatial world models, materials-lab safety, mechanistic interpretability, and prediction reconciliation.

`research_replication_rubric_artifact_replay`, `spatial_world_model_counterfactual_simulation_replay`, `materials_chemistry_closed_loop_lab_safety_replay`, `mechanistic_interpretability_circuit_attribution_replay`, `prediction_oracle_reconciliation`

### Import, Projection & Drift (2)

The membrane that brings non-secret macro substrate into the public tree and keeps projections honest instead of letting them drift from source.

`macro_projection_import_protocol`, `world_model_projection_drift_control_room`

### Work, Landing & Continuity (3)

How reversible work transactions are recorded, how dirty-tree landing decisions are made, and how detached runs resume.

`mission_transaction_work_spine`, `durable_agent_work_landing_replay`, `bridge_phase_continuity_runtime`
