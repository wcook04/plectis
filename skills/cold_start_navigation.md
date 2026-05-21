# Cold Start Navigation

Use this skill when entering `microcosm-substrate/` from a fresh public clone.

## Steps

1. Read `README.md`.
2. Read `AGENTS.md`.
3. Run `microcosm compile <project>` or
   `PYTHONPATH=src python3 -m microcosm_core.cli compile <project>` to create
   `.microcosm/` over a folder you bring.
4. Open `microcosm serve <project>` when you want the local observatory.
5. Inspect `core/organ_registry.json` for accepted organs and validator
   commands only when you need evidence drilldown.
6. Inspect `core/acceptance/first_wave_acceptance.json` for the current
   acceptance boundary.
7. Run:

```bash
PYTHONPATH=src python3 -m microcosm_core.validators.public_entry_docs --root . --out receipts/first_wave/public_entry_docs_validation.json
PYTHONPATH=src python3 -m microcosm_core.validators.dependency_preflight --readiness core/preflight_support/organ_fixture_validator_readiness_v1.json --negative-matrix core/preflight_support/fixture_negative_case_matrix_v1.json --out receipts/preflight/dependency_preflight.json
PYTHONPATH=src python3 -m microcosm_core.validators.fixture_freshness --readiness core/preflight_support/organ_fixture_validator_readiness_v1.json --negative-matrix core/preflight_support/fixture_negative_case_matrix_v1.json --mission-dag core/preflight_support/microcosm_rebuild_mission_graph_v1.json --receipt-coverage core/preflight_support/validator_receipt_coverage_map_v1.json --out receipts/preflight/fixture_runner_freshness.json
PYTHONPATH=src python3 -m microcosm_core.validators.launch_compression --root . --project <project> --out receipts/first_wave/launch_compression.json
./bootstrap.sh --suite first-wave --emit receipts/cold_clone_probe.json
```

## Anti-Claim

This skill gives public-root navigation only. It does not authorize Lean/Lake,
release, hosted-public readiness, publication, recipient work, provider calls,
private-data equivalence, or whole-system correctness.
