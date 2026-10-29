# Run the bounded verifier-lab execution spine

> **In plain terms.** A fair test of an automatic prover must run its steps for real, with no answers leaking in. This component is given a small public project for Lean, a proof-checking program, with recorded proof steps, a retry that supplies a missing fact, and a proposed change to failure handling. It runs Lean on the project, rejecting steps that expose a full proof or let comparison notes or provider suggestions in, and any change that claims unlimited power over source files. It writes saved records of the run and the checks, without candidate proofs, showing whether the inputs pass or are blocked. It is a small public experiment and does not show that arbitrary proofs are correct.

The execution spine runs a small public Lean project and checks recorded transitions, translation candidates and bounded policy-change candidates. It produces receipts with execution and validation results without including candidate proof bodies.

## Run the example

From the repository root, with Python 3.11 or newer available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.verifier_lab_execution_spine run \
  --input fixtures/first_wave/verifier_lab_execution_spine/input \
  --out .microcosm/component-guides/verifier_lab_execution_spine \
  --acceptance-out .microcosm/component-guides/verifier_lab_execution_spine/acceptance.json
```

The command writes local output under `.microcosm/component-guides/`. Check the returned status and the result receipt; a blocked result reports findings for the supplied inputs.

## What this checks

The fixture includes a Lake project and deliberate negative cases. One transition selects `decide` for a closed natural-number modular arithmetic problem; a separate translation request selects `Nat.add_comm` as a premise for a rerun after a missing-premise diagnosis. An Evolve candidate proposes changing the failure-class route and comparing baseline and rerun transitions. The validator rejects transitions exposing candidate bodies or mixing provider/oracle visibility into the forward path, and rejects an Evolve candidate claiming arbitrary source mutation. Its tests exercise Lean execution and the candidate checks.

## Limits

This is a bounded public witness and policy experiment. It does not establish correctness of arbitrary proofs or authorize arbitrary source changes. The command requires compatible `lean` and `lake` on PATH and can take time to build.

## Verification

The shown fixture command requires Lean and Lake and builds the public `MicrocosmProofWitness` project, including the checked statement `17 % 5 = 2`, and checks selected transitions. The exported-bundle replay validates a standalone receipt contract rather than running Lean. Tests exercise specific cases; no component-specific formal proof of its algorithm is established. When its exported-bundle route runs through `make component-replays`, the [shared Dafny-verified admission check](../formal/replay/README.md) checks agreement of source, input, claim-policy and receipt observations. The direct fixture command above does not itself run that check.

## Source

[Implementation](../src/microcosm_core/organs/verifier_lab_execution_spine.py) · [Example input](../fixtures/first_wave/verifier_lab_execution_spine/input/) · [Tests](../tests/test_verifier_lab_execution_spine.py) · [Historical sample result](../receipts/first_wave/verifier_lab_execution_spine/verifier_lab_execution_spine_result.json) · [JSON record](verifier_lab_execution_spine.json)

Background: [Lean system description](https://www.microsoft.com/en-us/research/publication/the-lean-theorem-prover-system-description/).
