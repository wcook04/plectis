# Generated Projection Drift Runtime

> **In plain terms.** Files made automatically from other files can fall out of step with their sources. This check is given example setups, each naming source files, the files generated from them, and a check that changes nothing. It fingerprints the sources and generated files, reuses an earlier clean result if the fingerprint matches, and otherwise checks that each generated file exists and runs the setup's own check. It reports the outcome without repairing or regenerating anything, and it treats a missing file as out of step even when the setup's own check passes. A clean result covers only the declared files and checks, and a matching fingerprint does not show the content is correct.

This runtime exercises a generated-file drift gate using fixture owners. An owner names source files, generated artifacts, and a no-write check. The gate fingerprints the inputs and outputs, can reuse a prior clean receipt when its fingerprint matches, and otherwise checks artifact presence and the owner's command. It reports the outcome; it does not repair or regenerate files.

The fixture includes a planted extra byte and a missing artifact. The missing artifact is drift even when the owner's check command returns success. A clean result is limited to the declared files and checks: a hash match is not a proof of semantic correctness or a validation of every generated file in the repository.

## Run the example

From the repository root with Python 3.11 or newer, run the supplied fixture into ignored local output:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.generated_projection_drift_runtime run \
  --input fixtures/first_wave/generated_projection_drift_runtime/input \
  --out .microcosm/component-guides/generated_projection_drift_runtime/out \
  --acceptance-out .microcosm/component-guides/generated_projection_drift_runtime/acceptance.json
```

A successful fixture run reports `pass` for four cases, including the two expected drift detections.

The fixture executes its declared built-in checks in temporary directories.

## Verification

The direct fixture exercises the drift checks without formally proving them. `make component-replays` runs this fixture route through the [shared Dafny admission check](../formal/replay/README.md), checking agreement among supplied source, input, claim policy and receipt observations. It does not prove that every drift is detected. The direct example does not invoke the admission check.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/generated_projection_drift_runtime.py) and [fixture inputs](../fixtures/first_wave/generated_projection_drift_runtime/input/).
- [Tests](../tests/test_engine_room_generated_projection_drift_gate.py).
- [Saved example result](../receipts/first_wave/generated_projection_drift_runtime/generated_projection_drift_runtime_result.json) (historical, not a fresh run).
- [Component JSON record](./generated_projection_drift_runtime.json) and [canonical capsule](../core/paper_module_capsules.json).
