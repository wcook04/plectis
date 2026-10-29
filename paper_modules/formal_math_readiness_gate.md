# Formal Math Readiness Gate

> **In plain terms.** Declared facts about a proof setup, such as which tools work, need checking before anything relies on them. The gate reads declarations of available libraries and proof techniques, a list of known results, routes from kinds of goals to techniques, and size-limited plans for background material. It rejects availability claims with no passing test, routes using unavailable techniques, and entries or plans that hold finished proofs or exceed their size limit. It writes a readiness summary and a saved validation record; in the example, Mathlib, a large shared library of mathematics, is reported unavailable. It judges only the declarations and cited evidence; it does not run a proof checker, confirm Mathlib is installed or prove a theorem.

The readiness gate checks declared formal-math inputs before a proof workflow consumes them. It reads corpus availability, tactic probes, a premise index, target-to-tactic routes, and provider context recipes, then writes a board and validation receipt. For example, the fixture reports Mathlib unavailable; a claim that it is available without a passing probe is rejected.

The checks also reject a premise carrying a proof body, a tactic marked available without a probe, routes to unavailable tactics, and recipes exceeding their allowed budget or carrying proof bodies. An exported bundle additionally checks copied source-module manifests and digests. These checks evaluate the declarations and referenced evidence; they do not run Lean or Lake, establish that Mathlib is installed, or prove a theorem.

## Run the example

From the repository root with Python 3.11 or newer, run the fixture through the Python API. The API accepts an explicit acceptance path; the module CLI does not expose that option:

```bash
PYTHONPATH=src python3 - <<'PY'
from microcosm_core.organs.formal_math_readiness_gate import run
r = run("fixtures/first_wave/formal_math_readiness_gate/input",
        ".microcosm/component-guides/formal_math_readiness_gate/out",
        acceptance_out=".microcosm/component-guides/formal_math_readiness_gate/acceptance.json")
print(r["status"])
PY
```

The supplied fixture reports `pass` when its positive declarations and expected negative cases meet the checks.

[LeanDojo](https://arxiv.org/abs/2306.15626) and [mathlib](https://arxiv.org/abs/1910.09336) provide context for premise and library tooling.

## Verification

The direct fixture checks declarations and does not run a proof assistant. `make component-replays` runs the exported readiness bundle through the [shared Dafny admission check](../formal/replay/README.md), which checks agreement among supplied source, input, claim policy and receipt observations. It does not prove the readiness rules correct. The direct example does not invoke the admission check.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/formal_math_readiness_gate.py) and [fixture inputs](../fixtures/first_wave/formal_math_readiness_gate/input/).
- [Tests](../tests/test_formal_math_readiness_gate.py).
- [Saved example result](../receipts/first_wave/formal_math_readiness_gate/readiness_gate_result.json) (historical, not a fresh run).
- [Component JSON record](./formal_math_readiness_gate.json) and [canonical capsule](../core/paper_module_capsules.json).
