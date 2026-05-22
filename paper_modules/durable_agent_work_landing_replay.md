# Durable Agent Work-Landing Replay

Durable agent work-landing replay is the public work-spine organ for showing how Microcosm treats agent work as a transaction instead of a chat claim. It binds owned-path claims, owner-native validation, scoped commit attempts, protected Git-metadata blockers, Task Ledger capture, Work Ledger finalizers, and seed reentry into a public-safe replay contract.

## Public Contract

- The source pattern is `durable_agent_work_landing_replay_compound`.
- The fixture lives at `fixtures/first_wave/durable_agent_work_landing_replay/input/`.
- The runtime example lives at `examples/durable_agent_work_landing_replay/exported_work_landing_replay_bundle/`.
- The validator is `microcosm_core.organs.durable_agent_work_landing_replay`.
- The CLI command is `microcosm durable-agent-work-landing-replay run-work-landing-bundle`.

## Negative Cases

The fixture rejects missing validation evidence, validation recorded after a commit attempt, missing Work Ledger closeout, commit-landed language without a HEAD advance, live Git mutation authority, unrelated dirty-path staging, uncaptured metadata blockers, release overclaims, and private path/body leakage.

## Authority Ceiling

This organ is metadata-only. It does not mutate Git, stage unrelated dirty paths, prove a commit landed, export private source bodies, run providers, publish, host, or authorize release.
