# Certificate Kernel Execution Lab

`certificate_kernel_execution_lab` is a source-available public runtime refactor
of the macro certificate-kernel pattern. It runs a small Lean/Lake certificate kernel,
generated certificate rows, analyzer metadata, CP2 typed-action reruns, and
bounded Evolve policy reruns without importing private proof bodies. The v2
fixture carries both a simple `NatSumCertificate` row family and a miniature
`BoundedOrderCertificate` family so the public lab is no longer only a
single-shape arithmetic receipt.

## Public Surfaces

- Organ runner: `python -m microcosm_core.organs.certificate_kernel_execution_lab run --input fixtures/first_wave/certificate_kernel_execution_lab/input --out receipts/first_wave/certificate_kernel_execution_lab`
- Exported bundle runner: `python -m microcosm_core.organs.certificate_kernel_execution_lab run-certificate-bundle --input examples/certificate_kernel_execution_lab/exported_certificate_kernel_execution_lab_bundle --out receipts/runtime_shell/demo_project/organs/certificate_kernel_execution_lab`
- CLI: `microcosm certificate-kernel-execution-lab run --input fixtures/first_wave/certificate_kernel_execution_lab/input --out receipts/first_wave/certificate_kernel_execution_lab`
- Standard: `standards/std_microcosm_certificate_kernel_execution_lab.json`
- Fixture manifest: `core/fixture_manifests/certificate_kernel_execution_lab.fixture_manifest.json`

## Authority Boundary

The lab proves only that the declared public Lean fixture compiled and that the
declared transition rows were accepted, rejected, or left residual under the
local verifier. It does not import macro proof bodies, expose proof text, count
oracle/provider output as proof authority, mutate source, claim benchmark
solve-rate, or authorize release.

## Receipt Shape

Receipts are public evidence. The lab exposes structured theorem/declaration
names, Lean/Lake command identity, return codes, hashes, declaration counts,
accepted/residual counts, negative-case ids, CP2 action classes, Evolve policy
artifact ids, authority counters, authority ceiling, and anti-claim. It omits
only proof, provider, oracle-answer, private-source, and stdout/stderr payload
bodies, and records that omission through `secret_exclusion_scan` and
`body_in_receipt: false` rather than treating absence as product evidence.

- Lean/Lake build receipt for `MicrocosmCertificateLab`.
- Analyzer metadata for public Lean files: imports, declarations, hashes, and
  line counts with proof bodies omitted from JSON receipts.
- Transition rows for valid certificates, missing certificate rows, bad
  generated certificate rows, and bounded order-certificate rows.
- CP2 typed-action translations over missing-certificate residuals, with Lean
  reruns proving downstream effect.
- Bounded Evolve mutations over certificate row selection policy, accepted only
  after reruns and no leakage regression.

## Anti-Claim

This is a source-available certificate-kernel laboratory, not a miniature private
macro dump and not general proof authority beyond the declared fixture rows.
