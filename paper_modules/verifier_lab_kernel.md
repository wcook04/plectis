# Inspect the verifier-lab kernel

> **In plain terms.** Testing an automatic prover goes wrong if a comparison note is counted as the prover's success or an outside suggestion is counted as a proof. This component is given results from smaller checks and a packet of public problems, comparison notes, provider hypotheses and proposed actions. It checks these against the packet's rules and rejects a comparison result counted as a success, a provider hypothesis claiming to be a proof, and full proofs where none belong. The output is a pass or blocked status with findings, showing whether the parts of this test keep their roles apart. It does not check arbitrary private proofs, and an outside suggestion is never treated as one.

The verifier-lab kernel combines a public component stack with a packet of forward problems, oracle sidecars, provider hypotheses and candidate actions. A forward problem is a public task to be attempted; an oracle sidecar records comparison information about that task separately. For example, a sidecar may identify a missing commutativity premise, but that observation is not counted as a forward success. The kernel also separates the bounded Lean witness from advisory or translated candidates.

## Run the example

From the repository root, with Python 3.11 or newer available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.verifier_lab_kernel run \
  --input fixtures/first_wave/verifier_lab_kernel/input \
  --out .microcosm/component-guides/verifier_lab_kernel \
  --acceptance-out .microcosm/component-guides/verifier_lab_kernel/acceptance.json
```

The command writes local output under `.microcosm/component-guides/`. Check the returned status and the result receipt; a blocked result reports findings for the supplied inputs.

## What this checks

The fixture checks component results alongside packet rules. It rejects an oracle result counted as forward success, a provider hypothesis claiming proof authority, and candidate bodies in fields that must remain body-free. Tests also exercise the standalone exported-bundle contract.

## Limits

The fixture path can invoke its bounded public Lean/Lake witness; compatible `lean` and `lake` are prerequisites. Provider suggestions and translated actions are not proofs, and the kernel does not validate arbitrary private proofs.

## Verification

The fixture stack includes a Lean/Lake witness for the public `MicrocosmProofWitness` project, including `17 % 5 = 2`; compatible Lean and Lake are required. Its exported-bundle replay validates a standalone component contract instead of running that witness. Tests exercise specific cases; no component-specific formal proof of its algorithm is established. When its exported-bundle route runs through `make component-replays`, the [shared Dafny-verified admission check](../formal/replay/README.md) checks agreement of source, input, claim-policy and receipt observations. The direct fixture command above does not itself run that check.

## Source

[Implementation](../src/microcosm_core/organs/verifier_lab_kernel.py) · [Example input](../fixtures/first_wave/verifier_lab_kernel/input/) · [Tests](../tests/test_verifier_lab_kernel.py) · [Historical sample result](../receipts/first_wave/verifier_lab_kernel/verifier_lab_kernel_result.json) · [JSON record](verifier_lab_kernel.json)

The historical sample result is blocked: its corpus-readiness, premise-index and diagnostic-spine components were blocked. It does not report a current run.

Background: [LCF and machine-checked proofs](https://www.research.ed.ac.uk/en/publications/lcf-a-way-of-doing-proofs-with-a-machine/).
