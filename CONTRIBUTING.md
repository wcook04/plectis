# Contributing

Start by proving the public entry path from `microcosm-substrate/`:

```bash
make install
make smoke
```

The smoke target runs the same first-screen checks directly:

```bash
microcosm hello .
microcosm tour --card .
microcosm status --card .
microcosm authority --card
microcosm workingness --card
microcosm legibility-scorecard
```

If editable install is not available, use the source form:

```bash
PYTHONPATH=src python3 -m microcosm_core hello .
```

## Good Contributions

- Improve runnable public substrate: CLI behavior, validators, standards,
  fixtures, receipts, tests, examples, and card-first documentation.
- Import real non-secret macro bodies when they can be copied with provenance,
  bounded claims, and a validator or receipt that proves the boundary.
- Delete, demote, or label surfaces that imply fake progress, release
  readiness, private-root equivalence, or authority beyond their receipt.
- Keep compact commands useful before raw receipt trees. A cold reader should
  get an honest answer from cards before drilldown.

## Hard Boundaries

Do not contribute secrets, credentials, sessions, provider payload bodies, raw
operator voice, private personal material, live account data, live external
target details, hidden rubric bodies, or unsafe exploit steps.

Do not add source-mutation, provider-call, hosted-release, recipient-send,
financial-advice, product-readiness, proof-correctness, or production-security
authority unless the surface is explicitly a negative fixture proving that the
authority is rejected.

## Validation Floor

Run the focused tests for the surface you touched. For public-entry and
boundary docs, use:

```bash
python3 -m pytest tests/test_public_entry_docs.py tests/test_secret_exclusion_scan.py tests/test_private_state_scan.py
```

For the repository verification path used by GitHub Actions, use:

```bash
make ci
```

For a broad cold-clone smoke, use:

```bash
./bootstrap.sh --suite first-wave --emit receipts/cold_clone_probe_local.json
```
