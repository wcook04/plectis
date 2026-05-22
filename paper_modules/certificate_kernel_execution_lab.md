# Certificate Kernel Execution Lab

`certificate_kernel_execution_lab` is a public replacement specimen for the
macro certificate-kernel pattern. It runs a small Lean/Lake certificate kernel,
generated certificate rows, analyzer metadata, CP2 typed-action reruns, and a
bounded Evolve policy rerun without importing private proof bodies.

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
artifact ids, authority counters, authority ceiling, and anti-claim. It omits or
redacts only proof, provider, oracle-answer, private-source, and stdout/stderr
payload bodies.

- Lean/Lake build receipt for `MicrocosmCertificateLab`.
- Analyzer metadata for public Lean files: imports, declarations, hashes, and
  line counts with bodies redacted.
- Transition rows for valid certificates, missing certificate rows, and bad
  generated certificate rows.
- CP2 typed-action translation over a missing-certificate residual, with a Lean
  rerun proving downstream effect.
- Bounded Evolve mutation over certificate row selection policy, accepted only
  after a rerun and no leakage regression.

## Anti-Claim

This is a public-safe certificate-kernel laboratory, not a miniature private
macro dump and not general proof authority beyond the declared fixture rows.
