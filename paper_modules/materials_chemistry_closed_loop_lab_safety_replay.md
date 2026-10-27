# Materials Chemistry Simulator Safety Replay

> **In plain terms.** When software picks which material a lab should test next, someone should check that the pick follows from the scores. This component reads made-up records of candidate materials, simulated lab tests, safety screening and the candidate declared as chosen. It works out the pick again from a stand-in test score, a score for what to test next and a safety score, then compares it with the declared pick. It writes a result with findings and rejects a pick that no longer matches the scores or a claimed hands-on lab procedure. It works only on simulated records, so it runs no experiment or robot and shows nothing about laboratory safety or a materials discovery.

This validator reads synthetic candidate, simulator assay, safety-screen, and selection records. It recomputes the selected candidate using assay proxy, active-learning, and safety-gate scores, then compares the result with the declared selection. It also checks the replay graph, source manifests, and negative-case refusals before writing a result and board.

The fixture rejects a claimed wet-lab procedure and the tests reject a stale selection after scores change. The result concerns the supplied simulated records; it does not run an experiment or robot, establish laboratory safety, or demonstrate a materials discovery. A source digest verifies the referenced copy, not its scientific validity.

## Run the example

From the repository root with Python 3.11 or newer, run the supplied fixture into ignored local output:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay run \
  --input fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay/input \
  --out .microcosm/component-guides/materials_chemistry_closed_loop_lab_safety_replay/out \
  --acceptance-out .microcosm/component-guides/materials_chemistry_closed_loop_lab_safety_replay/acceptance.json
```

The supplied fixture prints `pass` when its simulation records and expected refusals meet the checks.

## Verification

Tests exercise the synthetic scoring and refusal cases; they do not formally prove the scoring algorithm. `make component-replays` runs the exported lab bundle through the [shared Dafny admission check](../formal/replay/README.md) for agreement among supplied source, input, claim policy and receipt observations. The direct command does not invoke that gate.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/materials_chemistry_closed_loop_lab_safety_replay.py) and [fixture inputs](../fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay/input/).
- [Tests](../tests/test_materials_chemistry_closed_loop_lab_safety_replay.py).
- [Saved example result](../receipts/first_wave/materials_chemistry_closed_loop_lab_safety_replay/materials_chemistry_closed_loop_lab_safety_replay_result.json) (historical, not a fresh run).
- [Component JSON record](./materials_chemistry_closed_loop_lab_safety_replay.json) and [canonical capsule](../core/paper_module_capsules.json).
