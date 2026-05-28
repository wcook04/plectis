# Contributing

Start by proving the public entry path from `microcosm-substrate/`:

```bash
make smoke
make test
make ci
```

The smoke target is the no-install public sanity check. It writes ignored
`.microcosm/` route state through `tour --card`, then checks the compact public
authority, workingness, legibility, version, and stripping-boundary surfaces:

```bash
PYTHONPATH=src python3 -m microcosm_core hello .
PYTHONPATH=src python3 -m microcosm_core tour --card .
PYTHONPATH=src python3 -m microcosm_core status --card .
PYTHONPATH=src python3 -m microcosm_core authority --card
PYTHONPATH=src python3 -m microcosm_core workingness --card
PYTHONPATH=src python3 -m microcosm_core legibility-scorecard
PYTHONPATH=src python3 -m microcosm_core --version
PYTHONPATH=src python3 -m microcosm_core stripping-guard
```

The test target creates a repository-local `.venv`, installs the test extra
there, and then runs pytest, so a clean clone does not need pytest preinstalled
or system-site package writes. If you want to install once up front, use
`make install`.

For the full macro-root development suite, use `make test-all` from a checkout
where the sibling macro source paths are present. The default `make test` path
is the standalone public verification floor.

After install, the fuller first-screen route is:

```bash
.venv/bin/microcosm hello .
.venv/bin/microcosm tour --card .
.venv/bin/microcosm status --card .
.venv/bin/microcosm authority --card
.venv/bin/microcosm workingness --card
.venv/bin/microcosm legibility-scorecard
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
boundary docs, first run `make install` or
`.venv/bin/python -m pip install -e '.[test]'` if your environment does not
already have the test extra installed, then use the source-tree form:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_public_entry_docs.py tests/test_secret_exclusion_scan.py tests/test_private_state_scan.py
```

For the repository verification path used by GitHub Actions, use:

```bash
make ci
```

For a broad cold-clone smoke, use:

```bash
./bootstrap.sh --suite first-wave --emit receipts/cold_clone_probe_local.json
```
