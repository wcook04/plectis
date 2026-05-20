# Microcosm Substrate

This repository slice is a standalone runtime substrate for the accepted
first-wave control spine. It runs from this root, exposes public commands, and
emits command-owned receipts from validators.

## Standalone Runtime Substrate

Fixtures are regression inputs: examples, bootstrap data, and negative cases.
They are not the product runtime and should not be used to hide missing
substrate-shaped input paths.

## Accepted Public Runtime Spine

The current accepted organs are:

1. `pattern_binding_contract`
2. `executable_doctrine_grammar`
3. `proof_diagnostic_evidence_spine`
4. `navigation_hologram_route_plane`
5. `mission_transaction_work_spine`
6. `agent_route_observability_runtime`
7. `pattern_assimilation_step`

`formal_math_lean_proof_witness` remains deferred. Lean/Lake is not authorized
by this public root.

## First Commands

From this directory:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
PYTHONPATH=src python3 -m microcosm_core.validators.private_state_scan --root . --out receipts/first_wave/private_state_scan.json
PYTHONPATH=src python3 -m microcosm_core.validators.dependency_preflight --readiness core/preflight_support/organ_fixture_validator_readiness_v1.json --negative-matrix core/preflight_support/fixture_negative_case_matrix_v1.json --out receipts/preflight/dependency_preflight.json
PYTHONPATH=src python3 -m microcosm_core.validators.fixture_freshness --readiness core/preflight_support/organ_fixture_validator_readiness_v1.json --negative-matrix core/preflight_support/fixture_negative_case_matrix_v1.json --mission-dag core/preflight_support/microcosm_rebuild_mission_graph_v1.json --receipt-coverage core/preflight_support/validator_receipt_coverage_map_v1.json --out receipts/preflight/fixture_runner_freshness.json
PYTHONPATH=src python3 -m microcosm_core.validators.public_entry_docs --root . --out receipts/first_wave/public_entry_docs_validation.json
./bootstrap.sh --suite first-wave --emit receipts/cold_clone_probe.json
python -m pytest -q
```

Use the organ commands in `core/organ_registry.json` for individual validation
runs. Receipts under `receipts/**` are generated evidence from commands and
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
