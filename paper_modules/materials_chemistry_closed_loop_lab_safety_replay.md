# Materials Chemistry Closed-Loop Lab-Safety Replay

`materials_chemistry_closed_loop_lab_safety_replay` is a public
validator-backed claim contract for autonomous-science language. It turns a
materials-chemistry closed-loop pattern into a runnable local check: candidate
materials, safety screens, simulator assays, active-learning decisions, cold
replay refs, falsification fixtures, and receipts.

## Public Claim

Microcosm can expose closed-loop materials chemistry claims as inspectable,
simulator-only metadata without pretending to run a lab, synthesize materials,
operate robots, discover compounds, or certify benchmark performance. Each
accepted row binds candidate, safety-screen, simulator-assay, decision, result
table, failure taxonomy, and cold-replay references.

## Runtime Command

```bash
microcosm materials-chemistry-closed-loop-lab-safety-replay run-lab-bundle --input examples/materials_chemistry_closed_loop_lab_safety_replay/exported_materials_lab_safety_bundle --out receipts/runtime_shell/demo_project/organs/materials_chemistry_closed_loop_lab_safety_replay
```

## Fixture Contract

Positive fixture rows live in
`fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay/input`.
The fixture covers four abstract candidates and four simulator-only assay and
active-learning decision rows.

Negative cases reject wetlab protocol export, hazardous synthesis steps,
reagent quantities, controlled or bioactive targets, live lab credentials, robot
command execution, private lab notebook export, and discovery claims.

## Authority Ceiling

This organ is metadata-only and simulator-only. It does not export wetlab
protocols, hazardous synthesis steps, reagent quantities, controlled or
bioactive targets, live lab credentials, robot commands, private lab notebooks,
live assay data, discovery claims, benchmark scores, provider calls,
publication, hosting, or release authority.

## Evidence

- `standards/std_microcosm_materials_chemistry_closed_loop_lab_safety_replay.json`
- `core/fixture_manifests/materials_chemistry_closed_loop_lab_safety_replay.fixture_manifest.json`
- `receipts/first_wave/materials_chemistry_closed_loop_lab_safety_replay/materials_chemistry_closed_loop_lab_safety_replay_validation_receipt.json`
- `receipts/acceptance/first_wave/materials_chemistry_closed_loop_lab_safety_replay_fixture_acceptance.json`
