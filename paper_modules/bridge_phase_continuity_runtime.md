# Check a synthetic bridge continuation

`bridge_phase_continuity_runtime` reads a synthetic detached job, continuation packet, heartbeat rows, resource-pressure decisions and worker-skip records. The continuation packet identifies the job to resume and records whether the packet has already been consumed. The validator checks whether the supplied records describe a coherent continuation and writes five JSON receipts. This is useful for testing handoff rules without running a bridge.

## Run the example

From the repository root, with Python 3.11 or later:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.bridge_phase_continuity_runtime run \
  --input fixtures/second_wave/bridge_phase_continuity_runtime/input \
  --out .microcosm/component-guides/bridge_phase_continuity_runtime
```

Inspect `closeout_transition.json` for findings and the other four files for continuation, heartbeat, pressure and resume details. The input also references a source manifest; the validator checks the listed copied modules against their digests.

## What this checks

The positive job must have yielded to disk, reference an unconsumed packet, and have a fresh heartbeat with compatible phase and continuity identifiers. Other fixture cases exercise missing packets, duplicate resume attempts and stale heartbeat overclaims. Tests change the supplied records to show the findings follow their contents. A heartbeat is evidence of a recorded liveness signal, not evidence that work landed.

## Limits

The fixture is synthetic. It does not connect to a live bridge, dispatch a provider or establish that a real handoff succeeded. Matching source hashes shows that copies match their manifest, not that their algorithms are correct.

## Verification

The direct example does not invoke the shared gate. In `make component-replays`, this component’s registered route passes through the [Dafny replay admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement over host-supplied observations. It does not prove this component’s algorithm.

## Sources

- [Implementation](../src/microcosm_core/organs/bridge_phase_continuity_runtime.py), [input files](../fixtures/second_wave/bridge_phase_continuity_runtime/input) and [tests](../tests/test_bridge_phase_continuity_runtime.py).
- [Historical closeout result](../receipts/second_wave/bridge_phase_continuity_runtime/closeout_transition.json) and [component record](../core/paper_module_capsules.json).
- [Temporal durable execution](https://docs.temporal.io/) and [W3C PROV](https://www.w3.org/TR/prov-overview/) provide wider workflow and provenance context.
