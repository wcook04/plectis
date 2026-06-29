# Generated Projection Drift Runtime - exported bundle

This bundle accompanies the `generated_projection_drift_runtime` organ. The organ surfaces the public `generated_projection_drift_gate` engine-room capsule as a first-class runtime.

## What the mechanism does

Generated files (build outputs that are supposed to be reproducible from their source) can quietly drift when someone hand-edits the output or a builder stops matching its source. This component is the gate that catches that. For each "owner" (a generated artifact plus its source and a check command) it hashes the source and the output, checks whether a recent clean record lets it safely skip re-running the check, makes sure the required output actually exists, and otherwise runs the owner's own no-write check. It calls the file clean only when that check passes and the output is present. It flags drift; it does not fix files, does not judge every builder in the larger private system, and does not decide anything about releasing software.

## What it does not claim

A clean result means the selected owner's declared no-write check passed and its required artifacts were present for the supplied root over bounded public fixtures. It is command-receipt-style evidence, not a semantic proof, not a file repairer, not full-registry validation, and not release/publication/source-mutation authority.

## Fixture cases

clean_command_owner (positive): generated/report.md byte-matches expected/report.md, so the builtin:assert-file-equals no-write check returns zero and the owner is clean.
clean_source_hash_cache_hit (positive): a prior clean receipt whose baked source/artifact SHA-256s match the recomputed fingerprints lets the gate skip the owner check (check_mode=source_hash_cache_hit), so the deliberately failing builtin:fail command is never run.
planted_byte_drift (negative): the generated artifact carries an extra planted byte, so the no-write check recomputes a mismatch and the owner is reported drift with status_reason check_command_failed.
missing_artifact_drift (negative): the declared artifact never landed, so even though builtin:pass returns zero the required-artifact presence check reports drift with status_reason artifact_missing.

## Run it

```bash
python -m microcosm_core.organs.generated_projection_drift_runtime run \
  --input fixtures/first_wave/generated_projection_drift_runtime/input \
  --out receipts/first_wave/generated_projection_drift_runtime
```
