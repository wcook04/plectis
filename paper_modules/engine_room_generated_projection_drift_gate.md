# Check generated artifacts for drift

This gate checks generated artifacts, called projections, against their declared sources. Each configured owner record names the artifacts, source paths and check command responsible for a projection. The gate selects those records, fingerprints the sources and artifacts, and runs their configured check commands. It can reuse a clean receipt when the relevant hashes match. The result identifies owners with detected drift, missing files or failed checks.

## Run the example

From the repository root, with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.generated_projection_drift_gate evaluate-fixtures \
  --input fixtures/first_wave/engine_room_generated_projection_drift_gate/input --json
```

The fixture matrix uses temporary roots to exercise clean output, a planted byte, a missing artifact, path selection and missing fact-authority lineage. A missing artifact is drift even when an owner’s command succeeds. The matrix passes when each observed status matches its expected status.

A matching fingerprint and successful check support the declared freshness test; they do not prove semantic equivalence or correctness of the generator. The check route does not invoke the declared repair command. It does execute configured check commands, so use only trusted owner definitions. [Bazel’s hermeticity discussion](https://bazel.build/concepts/hermeticity) is useful background on declared inputs and reproducibility.

## Verification

The focused tests exercise owner selection, missing artifacts and cache decisions. This helper has no registered component replay route of its own and no component-specific formal proof. Hash matches and successful check commands do not prove semantic equivalence of generated output.

## Source and evidence

- [Implementation](../src/microcosm_core/engine_room/generated_projection_drift_gate.py) and [focused tests](../tests/test_engine_room_generated_projection_drift_gate.py).
- [Fixture inputs](../fixtures/first_wave/engine_room_generated_projection_drift_gate/input/); [historical Engine Room composition result](../receipts/first_wave/engine_room_demo/engine_room_demo_result.json) (summary, not a detailed result for this individual fixture).
- [JSON record](../paper_modules/engine_room_generated_projection_drift_gate.json); canonical metadata: [`core/paper_module_capsules.json`](../core/paper_module_capsules.json).
