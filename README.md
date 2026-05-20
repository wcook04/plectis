# Microcosm Substrate

Microcosm is an executable research prototype of a local project operating
substrate: it catalogs a folder you bring, discovers repo-shape patterns,
proposes routes, records governed work transactions, and emits observable
events with evidence available as drilldown.

It is small on purpose. The repo is a dense public miniature of a larger
architecture, not production infrastructure and not a hosted agent platform.
The point is to make the architecture executable enough to inspect.

## What You Bring

A project folder. It can be a tiny scratch repo, an application, a library, or
any directory with code, docs, tests, scripts, or package metadata.

## What You Get

Microcosm creates project-local state in `.microcosm/`:

- `project_manifest.json`
- `architecture.json`
- `state_index.json`
- `graph.json`
- `catalog.json`
- `patterns.json`
- `routes.json`
- `work_items.json`
- `events.jsonl`
- `explanations/*.json`
- `evidence/*.json`

The state is a local projection over your project. It does not mutate your
source files, call providers, publish anything, or claim source authority.

## Research Prototype Contract

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
That small card set distills public-safe pressure from the macro standards,
principles, WorkItem spine, projection governance, observability, and
assimilation surfaces. The cards constrain local state and explanation shape;
they are not private doctrine authority.

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

microcosm init /tmp/microcosm-scratch
microcosm index /tmp/microcosm-scratch
microcosm catalog /tmp/microcosm-scratch
microcosm architecture /tmp/microcosm-scratch
microcosm patterns /tmp/microcosm-scratch
microcosm route /tmp/microcosm-scratch
microcosm explain /tmp/microcosm-scratch readme_onboarding_route
microcosm work create /tmp/microcosm-scratch
microcosm work run /tmp/microcosm-scratch
microcosm observe /tmp/microcosm-scratch
microcosm graph /tmp/microcosm-scratch
microcosm evidence list /tmp/microcosm-scratch
```

The same commands work without installing the console script:

```bash
PYTHONPATH=src python3 -m microcosm_core.cli init /tmp/microcosm-scratch
PYTHONPATH=src python3 -m microcosm_core.cli index /tmp/microcosm-scratch
PYTHONPATH=src python3 -m microcosm_core.cli route /tmp/microcosm-scratch
PYTHONPATH=src python3 -m microcosm_core.cli explain /tmp/microcosm-scratch readme_onboarding_route
PYTHONPATH=src python3 -m microcosm_core.cli observe /tmp/microcosm-scratch
```

The older organ-adapter demo still exists for internal evidence and regression:

```bash
microcosm status
microcosm run examples/runtime_shell/demo_project
microcosm route list
microcosm evidence list
microcosm serve /tmp/microcosm-scratch --host 127.0.0.1 --port 8765
```

Evidence receipts are the black-box recorder, not the cockpit. Start with the
project loop; open receipts only when you need a drilldown.

## Architecture Kernel

`microcosm explain <project> <route_id>` is the main density surface. It shows
why a route exists by connecting grounded project refs, resolved pattern
bindings, kernel primitives, resolved standard pressure, work transaction
contracts, event refs, and evidence refs.

`microcosm serve <project> --host 127.0.0.1 --port 8765` opens a tiny local
observatory. It is intentionally dependency-free and static: a browser view
over the same JSON substrate returned by `architecture`, `catalog`, `patterns`,
`route`, `explain`, `observe`, and `evidence`.

## Internal Runtime Spine

The public package still carries seven adapter-backed runtime organs behind
the local substrate loop:

1. `pattern_binding_contract`
2. `executable_doctrine_grammar`
3. `proof_diagnostic_evidence_spine`
4. `navigation_hologram_route_plane`
5. `mission_transaction_work_spine`
6. `agent_route_observability_runtime`
7. `pattern_assimilation_step`

`formal_math_lean_proof_witness` remains deferred. Lean/Lake is not authorized
by this public root. Fixtures and exported bundles are regression inputs and
examples; they are not the primary product runtime.

## Validation Commands

```bash
PYTHONPATH=src python3 -m microcosm_core.validators.private_state_scan --root . --out receipts/first_wave/private_state_scan.json
PYTHONPATH=src python3 -m microcosm_core.validators.dependency_preflight --readiness core/preflight_support/organ_fixture_validator_readiness_v1.json --negative-matrix core/preflight_support/fixture_negative_case_matrix_v1.json --out receipts/preflight/dependency_preflight.json
PYTHONPATH=src python3 -m microcosm_core.validators.fixture_freshness --readiness core/preflight_support/organ_fixture_validator_readiness_v1.json --negative-matrix core/preflight_support/fixture_negative_case_matrix_v1.json --mission-dag core/preflight_support/microcosm_rebuild_mission_graph_v1.json --receipt-coverage core/preflight_support/validator_receipt_coverage_map_v1.json --out receipts/preflight/fixture_runner_freshness.json
PYTHONPATH=src python3 -m microcosm_core.validators.public_entry_docs --root . --out receipts/first_wave/public_entry_docs_validation.json
PYTHONPATH=src python3 -m microcosm_core.validators.research_kernel_density --root . --project /tmp/microcosm-scratch --out receipts/first_wave/research_kernel_density.json
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
- `skills/cold_start_navigation.md` gives the shortest safe path for a fresh
  public clone.

## License Posture

This microcosm substrate is licensed under Apache-2.0. That license posture
applies to this standalone root and its included tests, fixtures, validators,
receipts, and documentation. It does not authorize a public release switch,
hosting, publication, recipient work, provider calls, or private-data
equivalence.

## Boundary

The public substrate may carry runnable public input bundles, schema rows,
fixtures for tests, redacted lineage, validators, and receipt contracts. It
must not carry forbidden content bodies, live operator state, raw operator
text, provider payload bodies, browser/HUD/cockpit state, recipient or
publication surfaces, prediction/market material, or old scratch-root contents
as source authority.

Anti-claim: this README documents public runtime-spine entry and validation
only. It does not authorize release, hosted-public readiness, publication,
recipient work, provider calls, private-data equivalence, Lean/Lake execution,
or whole-system correctness.
