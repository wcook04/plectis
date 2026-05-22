# Spatial World-Model Counterfactual Simulation Replay

`spatial_world_model_counterfactual_simulation_replay` is the public spatial
counterfactual replay organ. It turns a high-novelty macro pattern into a
runnable Microcosm surface: six synthetic scene states, action traces, predicted
states, transition diffs, oracle checks, source-available sensor packet refs, and
negative-case receipts.

## Public Claim

Microcosm can expose spatial world-model counterfactuals as inspectable public
metadata without pretending to be a trained simulator, a generated-video proof
system, a robot or AV command plane, or a geographic ground-truth source. Each
replay row binds the scene state, counterfactual event, predicted state,
transition diff, oracle check, rare-event coverage label, fidelity limit, and
limitation labels.

## Runtime Command

```bash
microcosm spatial-world-model-counterfactual-simulation-replay run-simulation-bundle --input examples/spatial_world_model_counterfactual_simulation_replay/exported_spatial_world_model_simulation_bundle --out receipts/runtime_shell/demo_project/organs/spatial_world_model_counterfactual_simulation_replay
```

The runtime shell also exposes the compressed lens at:

```bash
microcosm spatial-simulation
```

## Fixture Contract

Positive fixture rows live in
`fixtures/first_wave/spatial_world_model_counterfactual_simulation_replay/input/counterfactual_replays.json`.
The fixture covers occlusion, pedestrian emergence, wind disturbance, surface
reflection, load shift, and late-yield counterfactuals.

Negative cases reject private video export, raw sensor export, live robot or AV
operation, real-world location claims, simulator-product claims,
generated-video-only authority, geographic accuracy claims, benchmark score
overclaims, and release authority.

## Authority Ceiling

This organ is metadata-only. It does not export private video or raw sensors,
operate robots or AVs, claim real-world geographic accuracy, sell or validate a
simulator product, treat generated video as sole authority, report benchmark
scores, call providers, publish, host, or authorize release.

## Evidence

- `standards/std_microcosm_spatial_world_model_counterfactual_simulation_replay.json`
- `core/fixture_manifests/spatial_world_model_counterfactual_simulation_replay.fixture_manifest.json`
- `receipts/first_wave/spatial_world_model_counterfactual_simulation_replay/spatial_world_model_counterfactual_simulation_replay_validation_receipt.json`
- `receipts/acceptance/first_wave/spatial_world_model_counterfactual_simulation_replay_fixture_acceptance.json`
