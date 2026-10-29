# Check projection-drift records

> **In plain terms.** A public view built from source material can stop agreeing with the source. This check takes the rules for building the view, the source evidence and a saved list of mismatches, each tying a source signal to a target, a proposed repair and a check. It recomputes the mismatches from the rules and evidence, compares them with the saved list, checks saved records of the source and of a running program, and rejects entries missing a source or check reference. The output is a report of these checks, showing whether the view still agrees with the evidence. It checks only declared public evidence and does not repair anything, change a source or authorize a release.

A projection is a derived public view of source information. Drift can occur when that view or its references no longer agree with the source evidence. This component recomputes public drift rows from the projection protocol and source evidence, compares them with a supplied snapshot, and checks source state and runtime receipt witnesses. Each row connects a source signal to a target, a proposed repair route and a validation reference; the component writes a report of the checks.

## Run the example

From the repository root, with Python 3.11 or newer available:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.world_model_projection_drift_control_room run \
  --input fixtures/first_wave/world_model_projection_drift_control_room/input \
  --out .microcosm/component-guides/world_model_projection_drift_control_room \
  --acceptance-out .microcosm/component-guides/world_model_projection_drift_control_room/acceptance.json
```

The command writes local output under `.microcosm/component-guides/`. Check the returned status and the result receipt; a blocked result reports findings for the supplied inputs.

## What this checks

A row missing a source reference or a validation reference is rejected. Tests also change source-ledger rows and receipt witnesses to check that the verdict follows the evidence, and reject an unsupported source reference or a projection claiming source authority.

## Limits

The report checks declared public evidence; it does not repair a live route, mutate a source, promote doctrine or authorize a release. Source digest checks do not prove the copied algorithms correct.

## Verification

Tests exercise specific cases; no component-specific formal proof of its algorithm is established. When its exported-bundle route runs through `make component-replays`, the [shared Dafny-verified admission check](../formal/replay/README.md) checks agreement of source, input, claim-policy and receipt observations. The direct fixture command above does not itself run that check.

## Source

[Implementation](../src/microcosm_core/organs/world_model_projection_drift_control_room.py) · [Example input](../fixtures/first_wave/world_model_projection_drift_control_room/input/) · [Tests](../tests/test_world_model_projection_drift_control_room.py) · [Historical sample result](../receipts/first_wave/world_model_projection_drift_control_room/world_model_projection_drift_control_room_result.json) · [JSON record](world_model_projection_drift_control_room.json)

Background: [Concept drift](https://en.wikipedia.org/wiki/Concept_drift).
