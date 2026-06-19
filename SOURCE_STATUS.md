# Microcosm Source Status

Last updated: 2026-06-19

This repository is the populated standalone public source slice for Microcosm
Substrate. It contains the public Python package, fixtures, tests, generated
component records, documentation, license files, and local-run entrypoints that
belong to the released public slice.

## What is public here

- The public source of record for the standalone slice is this repository.
- A cold clone should be able to inspect the source, run the bootstrap path, and
  replay the documented local witness commands without access to the private
  macro repository.
- The website at <https://wcook04.github.io/microcosm-substrate/> is a static
  projection over this public source and its release packets. If the website and
  repository disagree, the repository files and committed release receipts are
  the source of record.
- The package is licensed under Apache-2.0; see `LICENSE`, `NOTICE`, and
  `PROVENANCE.md`.

## What is not public here

- The larger private working root, private ledgers, operator notes, browser
  state, account material, secrets, recipient-send state, and unpublished
  reference material are outside this repository.
- Private raw video/capture sources are not part of the public source release.
  The demo film is distributed separately as controlled-review media.
- This repository is not a hosted service, production security product, legal or
  financial advice system, trading system, or whole-system correctness proof.

## Reviewer path

Start with:

```bash
./bootstrap.sh
PYTHONPATH=src python3 -m microcosm_core hello .
PYTHONPATH=src python3 -m microcosm_core tour --card .
PYTHONPATH=src python3 -m microcosm_core authority --card
```

Use `README.md`, `QUICKSTART.md`, `RELEASE_REVIEW.md`, and the receipts under
`receipts/` for the claim boundaries and replayable checks. The authority card
is intentionally narrow: it shows what the public slice records and what it
does not claim.
