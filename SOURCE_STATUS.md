# Plectis Source Status

Last updated: 2026-06-22

This repository is the populated standalone public source slice for Plectis. It
contains the public Python package, fixtures, tests, generated component
records, documentation, license files, and local-run entrypoints that belong to
the released public slice.

Microcosm is the former public name. It remains only where compatibility or
technical continuity still requires it: the `microcosm_core` import path, the
legacy `microcosm` command alias, `.microcosm/` local state, historical source
paths, fixture names, and previously published links.

## What is public here

- The public source of record for the standalone slice is the canonical Plectis
  repository at <https://github.com/wcook04/plectis>.
- A cold clone should be able to inspect the source, run the bootstrap path, and
  replay the documented local witness commands without access to the private
  macro repository.
- The website at <https://wcook04.github.io/plectis/> is a static projection
  over this public source and its release packets. If the website and repository
  disagree, the repository files and committed release receipts are the source
  of record.
- The retired `wcook04/microcosm-substrate` repository and old Pages URL are
  historical compatibility surfaces only; they are not current source authority.
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

After installation, use the Plectis console command as the public-primary entry
point:

```bash
plectis hello .
plectis tour --card .
plectis authority --card
```

The legacy `microcosm` command remains a compatibility alias for existing local
scripts and historical receipts.

Use `README.md`, `QUICKSTART.md`, `RELEASE_REVIEW.md`, and the receipts under
`receipts/` for the claim boundaries and replayable checks. The authority card
is intentionally narrow: it shows what the public slice records and what it
does not claim.
