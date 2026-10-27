# Formal Math Verifier Trace Repair Loop

> **In plain terms.** A failed proof attempt can be patched and declared fixed without anyone checking it again. The validator reads saved records of proof attempts, the proof checker's logs, the repairs and any success claim. It ties each failure to a repair and requires every success claim to point to a separate recorded re-check of the repaired attempt, which it only looks up. It also tests a toy repair on 0, 1, 2 and 7, correcting the wrong claim that adding zero to a number gives zero, and writes a validation record. The four-number test is no proof for all numbers, no proof checker is run, and a pass does not show any theorem is correct.

This validator examines recorded attempt, verifier trace, repair, and promotion metadata. It connects a reported failure class to a repair action and checks a claim that a repaired attempt succeeded. That claim of promotion requires a reference to a cold rerun: a separate recorded check of the repaired attempt. The validator checks the reference and source records; it does not rerun the verifier. It writes a board and a validation receipt for inspection.

The fixture rejects an attempt that claims promotion without a cold rerun, and also rejects proof bodies and oracle premise IDs. It also evaluates a toy repair on the four natural-number inputs 0, 1, 2, and 7: the failed comparison `n + 0 = 0` is changed to `n + 0 = n` and checked again. This finite comparison is not a proof for all natural numbers. The run does not invoke Lean or Lake, and a retained verifier trace is not a fresh proof check. A passing result does not establish theorem correctness or turn human approval into proof.

## Trace grade boundary

The evidence-cell registry names this check `trace_grade_boundary`. A `trace_grade` describes an attempt in the recorded verifier metadata. The validator rejects a grade with no trace events and requires each public attempt to name a verifier class and carry events. A grade and its events document the attempt; they do not independently establish that a theorem is correct.

## Run the example

From the repository root with Python 3.11 or newer, run the fixture through the Python API. The API accepts an explicit acceptance path; the module CLI does not expose that option:

```bash
PYTHONPATH=src python3 - <<'PY'
from microcosm_core.organs.formal_math_verifier_trace_repair_loop import run
r = run("fixtures/first_wave/formal_math_verifier_trace_repair_loop/input",
        ".microcosm/component-guides/formal_math_verifier_trace_repair_loop/out",
        acceptance_out=".microcosm/component-guides/formal_math_verifier_trace_repair_loop/acceptance.json")
print(r["status"])
PY
```

The supplied fixture reports `pass` when the trace checks and expected negative cases succeed.

For background on proof traces see [GamePad](https://arxiv.org/abs/1806.00608), [HOList](https://arxiv.org/abs/1904.03241), and [LeanDojo](https://arxiv.org/abs/2306.15626).

## Verification

The toy comparison covers four inputs; it is not a Lean proof. `make component-replays` runs the exported trace bundle through the [shared Dafny admission check](../formal/replay/README.md) for agreement among supplied source, input, claim policy and receipt observations. That check does not prove the repair algorithm or theorem. The direct example does not invoke the admission check.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/formal_math_verifier_trace_repair_loop.py) and [fixture inputs](../fixtures/first_wave/formal_math_verifier_trace_repair_loop/input/).
- [Tests](../tests/test_formal_math_verifier_trace_repair_loop.py).
- [Saved example result](../receipts/first_wave/formal_math_verifier_trace_repair_loop/formal_math_verifier_trace_repair_loop_result.json) (historical, not a fresh run).
- [Component JSON record](./formal_math_verifier_trace_repair_loop.json) and [canonical capsule](../core/paper_module_capsules.json).
