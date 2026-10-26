# Run a small Lean certificate lab

The certificate lab checks supplied finite certificate examples with a Lean project. Its fixture includes natural-number sum certificates and bounded-order certificates, including deliberately invalid rows. The runner records build and certificate transition results and analyzer metadata in JSON.

## Run the example

From the repository root, with Python 3.11 or later and the fixture's Lean and Lake toolchain available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.certificate_kernel_execution_lab run \
  --input fixtures/first_wave/certificate_kernel_execution_lab/input \
  --out .microcosm/component-guides/certificate_kernel_execution_lab \
  --acceptance-out .microcosm/component-guides/certificate_kernel_execution_lab/acceptance.json
```

The fixture route builds the public Lean project in a temporary workspace and checks the declared transitions. The result separates Lean-verified rows from provider suggestions and oracle comparisons. For example, the manifest includes `2 + 3 = 5` and the invalid `2 + 3 = 6`; the latter must be rejected. The tests also check that proof bodies and private source references do not enter the receipts.

## Limits

A successful fixture run supports the stated checks on these certificates, not an arbitrary theorem or a proof of the original research problem. The exported bundle has a separate standalone contract: its test verifies that it does **not** launch Lean or Lake, so a passing bundle result is not a fresh kernel execution. Source-copy digest checks establish matching bytes, not mathematical correctness.

## Verification

The shown fixture run uses Lean and Lake to check the supplied sum and bounded-order certificate declarations, including `cert_2_3_5_valid`; it does not prove the Python runner correct. `make component-replays` instead uses the standalone exported bundle, with no fresh Lean run, and applies the [Dafny replay admission check](../formal/replay/README.md) to the observed envelope.

## Sources

- [Runner](../src/microcosm_core/organs/certificate_kernel_execution_lab.py), [certificate manifest](../fixtures/first_wave/certificate_kernel_execution_lab/input/certificate_manifest.json), [Lean project](../fixtures/first_wave/certificate_kernel_execution_lab/input/lake_project) and [tests](../tests/test_certificate_kernel_execution_lab.py).
- [Historical fixture result](../receipts/first_wave/certificate_kernel_execution_lab/certificate_kernel_execution_lab_result.json) and [component record](../core/paper_module_capsules.json).
- [Lean documentation](https://lean-lang.org/documentation/) explains the proof assistant used by the fixture.
