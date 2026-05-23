# Materials Chemistry Closed-Loop Lab-Safety Replay

`materials_chemistry_closed_loop_lab_safety_replay` is a public,
source-faithful Lab/Evolve failure-replay refactor for autonomous-science
language. It turns a materials-chemistry closed-loop pattern into a runnable
local check: candidate materials, safety screens, simulator assays,
active-learning decisions, cold replay refs, restart points, source capsule
hashes, teachings, falsification fixtures, and receipts.

## Public Claim

Microcosm can expose closed-loop materials chemistry claims as inspectable,
body-free simulator-only replay substrate without pretending to run a lab,
synthesize materials, operate robots, discover compounds, or certify benchmark
performance. Each accepted row binds candidate, safety-screen, simulator-assay,
decision, result table, failure taxonomy, cold-replay reference, replay case,
source capsule, and reusable teaching boundary.

The imported mechanism is a public refactor of the macro Lab/Evolve failure
replay specimen. It preserves graph nodes and edges, failure classification,
restart-point selection, bounded replay cases, teaching-ledger carryforward,
source capsule hashing, and anti-claim boundaries while omitting wetlab,
credential, robot, private notebook, live assay, provider-payload, and release
material.

## Runtime Command

```bash
microcosm materials-chemistry-closed-loop-lab-safety-replay run-lab-bundle --input examples/materials_chemistry_closed_loop_lab_safety_replay/exported_materials_lab_safety_bundle --out receipts/runtime_shell/demo_project/organs/materials_chemistry_closed_loop_lab_safety_replay
```

## Fixture Contract

Positive fixture rows live in
`fixtures/first_wave/materials_chemistry_closed_loop_lab_safety_replay/input`.
The fixture covers four abstract candidates and four simulator-only assay and
active-learning decision rows. Those rows are consumed by
`microcosm_core.macro_tools.lab_evolve_replay.build_materials_lab_evolve_replay`;
the fixture is not counted as product progress unless the replay graph,
source-capsule provenance, secret-exclusion scan, and body-free verification
are present.

Negative cases reject wetlab protocol export, hazardous synthesis steps,
reagent quantities, controlled or bioactive targets, live lab credentials, robot
command execution, private lab notebook export, and discovery claims.

## Authority Ceiling

This organ is source-faithful public replay metadata and simulator-only. It does
not export wetlab protocols, hazardous synthesis steps, reagent quantities,
controlled or bioactive targets, live lab credentials, robot commands, private
lab notebooks, live assay data, discovery claims, benchmark scores, provider
calls, publication, hosting, or release authority.

## Evidence

- `src/microcosm_core/macro_tools/lab_evolve_replay.py`
- `standards/std_microcosm_materials_chemistry_closed_loop_lab_safety_replay.json`
- `core/fixture_manifests/materials_chemistry_closed_loop_lab_safety_replay.fixture_manifest.json`
- `receipts/first_wave/materials_chemistry_closed_loop_lab_safety_replay/materials_chemistry_closed_loop_lab_safety_replay_validation_receipt.json`
- `receipts/acceptance/first_wave/materials_chemistry_closed_loop_lab_safety_replay_fixture_acceptance.json`
