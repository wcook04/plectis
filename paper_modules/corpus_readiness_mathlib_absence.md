# Check corpus readiness and a Mathlib absence case

> **In plain terms.** A written claim that Mathlib, a large shared library of mathematics, is ready to use can be wrong. The checker is given a saved record of which libraries were available and what each example user needs. It compares those claims with saved evidence and runs a small test in which Lean, a proof-checking program, must load its basic library but fail to load Mathlib with a 'module missing' message. It marks each example user as allowed or blocked and rejects any record that says Mathlib is available without evidence.

This checker compares declared formal-math corpus readiness and consumer decisions with supplied source artifacts and a narrow Lean import probe. It records which fixture consumers are allowed or blocked, so an absent corpus or unsupported Mathlib claim cannot silently become a readiness result.

## Run the example

From the repository root, with Python 3.11 or later and Lean and Lake available on `PATH`:

```bash
PYTHONPATH=src python3 - <<'PYTHON'
from microcosm_core.organs.corpus_readiness_mathlib_absence_gate import run
result = run(
    'fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input',
    '.microcosm/component-guides/corpus_readiness_mathlib_absence_gate',
    acceptance_out='.microcosm/component-guides/corpus_readiness_mathlib_absence_gate/acceptance.json',
)
print(result['status'])
PYTHON
```

This uses the Python API because the `run` CLI does not expose an acceptance-output override. The probe runs `lake env lean` in a temporary directory: a `Std` import must succeed and the Mathlib import must fail with the expected missing-module diagnostic. Missing tools, timeouts or a different failure do not establish Mathlib absence.

## What this checks

The 2026 fixture records corpus status and consumer requirements; the checker compares aliases and decisions against the anchored runtime evidence and checks source artifact digests. A fixture that claims Mathlib is available without supporting probe evidence is rejected. The historical inputs describe that run's corpus state, not an inventory of this checkout today.

## Limits

The temporary import probe is not a build of a Mathlib project, a theorem proof or a benchmark. A passing result does not establish corpus completeness or global Mathlib availability. A digest match identifies an unchanged artifact; it does not prove its claims.

## Verification

The shown run uses Lean and Lake for the narrow `Std` and Mathlib import probes, not to prove the readiness checker. The registered bundle replay also runs the probe and applies the [Dafny replay admission check](../formal/replay/README.md) to its observed envelope; the direct example does not invoke that admission gate.

## Sources

- [Implementation](../src/microcosm_core/organs/corpus_readiness_mathlib_absence_gate.py), [fixture inputs](../fixtures/first_wave/corpus_readiness_mathlib_absence_gate/input) and [tests](../tests/test_corpus_readiness_mathlib_absence_gate.py).
- [Historical result](../receipts/first_wave/corpus_readiness_mathlib_absence_gate/corpus_readiness_mathlib_absence_gate_result.json) and [component record](../core/paper_module_capsules.json).
- [Mathlib](https://leanprover-community.github.io/mathlib4_docs/) documents the library independently of this probe.
