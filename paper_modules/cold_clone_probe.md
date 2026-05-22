# Cold Clone Probe

## Teleology

`cold_clone_probe` is the public clone smoke test. It verifies that a fresh
checkout can import the package, run the accepted first-wave command surface,
and emit command-owned receipts without local absolute paths.

## Public Contract

Run `./bootstrap.sh --suite first-wave --emit receipts/cold_clone_probe.json`
from the public root. The probe validates package importability and first-wave
bootstrap mechanics while preserving the public/private boundary.

## Receipt Expectations

The probe emits `receipts/cold_clone_probe.json` with `status=pass`, public
relative receipt paths, anti-claims, and no private body excerpts.

## Anti-Claim

This module documents clone/bootstrap mechanics only. It does not certify
release operations, hosted deployment, publication, recipient work,
provider calls, secret export, Lean/Lake execution, or whole-system
correctness.
