# Lean Proof Search Lab

> **In plain terms.** A proof-finding program can look good by cheating, so its proofs need checking. The lab is given two tiny logic statements, such as that two true statements are true together, and needs Lean, a program that checks proofs. It searches step by step, within limits, for a proof of each statement, has Lean check every candidate, and compares the result with a simpler method. The result is pass or fail, or 'locked' if Lean is missing, meaning nothing was checked, and cheats such as answer-key fields, proofs resting on placeholders or extra assumptions, and searches that memorize problem names are rejected. Two tiny statements say nothing about open problems, and the packaged version never runs Lean.

This lab runs bounded symbolic search on small Lean propositions and checks candidate proofs with Lean. The positive fixture includes `theorem lab_and_intro (p q : Prop) : p -> q -> And p q` and `theorem lab_or_comm (p q : Prop) : Or p q -> Or q p`. Search uses a bounded AND/OR procedure and compares it with a hammer-style baseline; an ID-blind policy ablation checks for dependence on problem identifiers.

The negative cases include oracle fields, `sorry`/axiom taint, and a policy that memorizes problem IDs. The fixture run requires a `lean` executable on PATH. If Lean is absent, it reports `locked` with no verification performed, rather than a pass or failure. The separate exported-bundle runner checks that three required files exist and counts JSON files. It neither executes Lean nor verifies the retained proof material, so its pass is not a fresh proof check. These examples do not establish results for open problems or neural theorem proving.

## Run the example

From the repository root with Python 3.11 or newer, run the supplied fixture into ignored local output:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.lean_proof_search_lab_runtime run \
  --input fixtures/first_wave/lean_proof_search_lab_runtime/input \
  --out .microcosm/component-guides/lean_proof_search_lab_runtime/out \
  --acceptance-out .microcosm/component-guides/lean_proof_search_lab_runtime/acceptance.json
```

Inspect the reported status as well as the process exit code: `locked` exits successfully but means Lean did not run.

## Verification

The direct fixture needs Lean on `PATH` to check candidate proofs of `lab_and_intro` and `lab_or_comm`; without it the run is `locked`. `make component-replays` instead runs the exported file-presence check under the [shared Dafny admission check](../formal/replay/README.md). Neither admission nor file presence proves the search algorithm correct.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/lean_proof_search_lab_runtime.py) and [fixture inputs](../fixtures/first_wave/lean_proof_search_lab_runtime/input/).
- [Tests](../tests/test_lean_proof_search_lab_runtime.py).
- [Saved example result](../receipts/first_wave/lean_proof_search_lab_runtime/lean_proof_search_lab_runtime_result.json) (historical, not a fresh run).
- [Component JSON record](./lean_proof_search_lab_runtime.json) and [canonical capsule](../core/paper_module_capsules.json).
