# Bridge Phase Continuity Runtime

This public slice validates disk-first bridge continuity over fake transport fixtures.

It checks that a yielded synthetic job has a continuation packet, heartbeat rows stay liveness evidence only, resource pressure can block dispatch, a packet resumes exactly once, duplicate resume attempts fail, worker-skip rows do not close claims silently, and closeout transition receipts remain the boundary for landed-work claims.

The runtime owner is `src/microcosm_core/organs/bridge_phase_continuity_runtime.py`. The public standard is `standards/std_microcosm_bridge_phase_continuity_runtime.json`, the fixture manifest is `core/fixture_manifests/bridge_phase_continuity_runtime.fixture_manifest.json`, and the runtime-spine command is:

```bash
microcosm bridge-phase-continuity-runtime run --input fixtures/second_wave/bridge_phase_continuity_runtime/input --out /tmp/microcosm-bridge-continuity
```

The reusable mechanism is not "subagents are good" or "mapping is needed"; it is the concrete continuity membrane that lets future agents test observe/apply bridge resumption without live provider, HUD, browser, phase-runtime, prompt-shelf, or private-memory state.

Anti-claim: this module does not run live bridge transport, call providers, read operator HUD/browser/phase runtime state, prove provider or UI uptime, land work, mutate source, or authorize release.
