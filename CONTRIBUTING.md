# Contributing

Contributions and error reports are welcome. Good contributions:

- improve runnable public substrate: CLI behaviour, validators, standards,
  fixtures, receipts, tests, examples, and card-first documentation;
- import real non-secret macro bodies when they can be copied with
  provenance, bounded claims, and a validator or receipt that proves the
  boundary;
- delete, demote, or label surfaces that imply fake progress, release
  readiness, or authority beyond their receipt.

Before choosing a file to edit, use the README's
[Choose a route](README.md#choose-a-route) table as the contributor routing
layer; the commands below are validation lanes after that route, not a
replacement for it.

## Development setup

Before installing anything, `./bootstrap.sh` probes the clone's fixture and
boundary floor and writes ignored `.microcosm/cold_clone_probe.json` evidence
(`./bootstrap.sh --dry-run` previews the exact command first). Then:

```bash
git clone https://github.com/wcook04/plectis && cd plectis
VENV=/tmp/plectis-dev-venv make install
```

`make install` creates a checkout-keyed temporary venv and installs the
`[test]` extra there (pytest, requests, NumPy, pandas), so a clean clone does
not need pytest preinstalled. Set `VENV` explicitly (as above) when you want a
stable interpreter path such as `/tmp/plectis-dev-venv/bin/plectis hello .`.

## Tests and validation

```bash
make check      # sub-second organ-registry preflight, run on every save
make test       # public entry and safety tests
make ci         # the GitHub Actions floor: test + smoke + package-smoke
make validate   # ci plus the doctrine-lattice drift check (maintainer gate)
```

Run the focused tests for the surface you touched first, for example:

```bash
PYTHONPATH=src /tmp/plectis-dev-venv/bin/python -m pytest tests/test_public_entry_docs.py --basetemp=/tmp/plectis-bt
```

Two rules the Makefile enforces that direct pytest runs must respect:

- **One basetemp per process.** If you run separate pytest subsets at the same
  time, pass a unique `--basetemp` to each; parallel direct invocations can
  race while copying fixture trees if they share one.
- **Tracked receipts are read-only under pytest.** Generated output that needs
  to change belongs in its owner lane (a builder or an explicit
  `MICROCOSM_TRACKED_RECEIPT_WRITES=1` opt-in), never a hand edit.

The full review lanes (complete smoke card set, the `make test-all` drift
suite, flight recorder, release-candidate proof, standalone export and its
exported-clone validation) are documented in
[docs/maintainers/validation.md](docs/maintainers/validation.md).

## Generated files

`ORGANS.md`, `ARCHITECTURE.md`, `AGENT_ROUTES.md`, `FIRST_ACTION.md`,
`RELEASE_REVIEW.md`, and the atlas/registry JSON records are builder-owned.
Do not hand-edit them; change the source and regenerate (for the atlas:
`PYTHONPATH=src python3 scripts/build_organ_atlas.py --write`). Tests compare
committed output to live regeneration and fail on drift.

## Pull requests

Use `.github/PULL_REQUEST_TEMPLATE.md` as the inline checklist for validation
evidence, public/private payload exclusions, claim boundaries, and standalone
source inventory. The template is a guardrail, not a release approval surface.
State which tests you ran; `make ci` or an explained narrower lane is the
floor.

## Hard boundaries

Do not contribute secrets, credentials, sessions, provider payload bodies, raw
operator voice, private personal material, live account data, live external
target details, hidden rubric bodies, or unsafe exploit steps.

Do not add source-mutation, provider-call, hosted-release, recipient-send,
financial-advice, product-readiness, proof-correctness, or production-security
authority unless the surface is explicitly a negative fixture proving that the
authority is rejected. Nothing in a contribution changes the release
boundary: export receipts keep `release_authorized=false` until a separate
operator decision exists.
