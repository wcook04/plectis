# Semantic singleflight dedup runtime — exported bundle

This bundle accompanies the `semantic_singleflight_dedup_runtime` organ. The
organ surfaces the public `command_run_singleflight` engine-room capsule as a
first-class operational-discipline runtime.

## What the mechanism does

Command execution is deduplicated by a *content key* built from:

- `argv` (the command words),
- the resolved working directory,
- the git `HEAD` commit,
- a scoped dirty-tree fingerprint (status, diff, and content hashes for the
  declared scope paths),
- an environment fingerprint.

Because the key folds repo state in, a stale working tree cannot answer for a
different run. Mutating a scoped file flips the key; a completed run is reused
only when its key still matches.

## What it does not claim

It keys and dedups command runs by repo-state fingerprint. It does **not**
guarantee global mutual exclusion, does **not** replace a lock service, does
**not** prove cross-host correctness, and is **not** a job scheduler, a daemon,
or release approval.

## Fixture cases

- `single_leader.json` — a first run becomes the leader and runs once.
- `completed_reuse.json` — a same-key second run reuses the completed run; the
  side-effecting counter stays at 1.
- `scope_mutation_changes_key.json` — mutating a scoped file flips the key
  (negative case: stale state cannot dedup).
- `missing_command_rejected.json` — an empty argv is rejected (negative case).

## Run it

```bash
python -m microcosm_core.organs.semantic_singleflight_dedup_runtime run \
  --input fixtures/first_wave/semantic_singleflight_dedup_runtime/input \
  --out receipts/first_wave/semantic_singleflight_dedup_runtime
```
