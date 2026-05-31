# Contributing

Start by proving the source-root boundary from `microcosm-substrate/` before
installing or running the broader validation floor:

```bash
./bootstrap.sh
```

The probe writes ignored `.microcosm/cold_clone_probe.json` evidence and checks
the first-wave fixture boundary without refreshing tracked receipts. Use
`./bootstrap.sh --dry-run` when you need the exact source-root command without
writing the ignored receipt.

Then prove the public entry path:

```bash
make smoke
make package-smoke
make test
make ci
```

Before choosing a file to edit, use the README
[Public Repo Map](README.md#public-repo-map) and
[Component Map](README.md#component-map). Treat those sections as the
contributor routing layer: they identify the runtime package, command cards,
public doctrine, evidence fixtures, source capsules, and validation shell.
The commands below are validation lanes after that route, not a replacement
for it.

The smoke target is the no-install public sanity check. It writes ignored
`.microcosm/` route state through `tour --card`, stores command outputs under
`.microcosm/smoke/`, then checks the compact public authority, workingness,
legibility, version, and stripping-boundary surfaces without dumping the full
cards into CI logs. A healthy terminal summary includes
`Microcosm smoke check: pass`, `authority: pass`, `workingness: clear`, and
`served status: pass`:

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

`make clean` removes the smoke receipt directory and the shared pytest scratch
root while leaving the rest of project-local `.microcosm/` state alone.

The package smoke target installs this source tree into a fresh temporary venv
and runs the installed `microcosm` console command through the compact cards.
Use it when the question is package installability rather than source-form
runtime behavior.

The test target creates a repository-local `.venv`, installs the test extra
there, and then runs pytest, so a clean clone does not need pytest preinstalled
or system-site package writes. If you want to install once up front, use
`make install`. The Makefile also routes pytest basetemp, Python bytecode
cache, and `TMPDIR` under per-run folders inside
`$(TMPDIR)/microcosm-substrate-test-tmp` so broad local runs do not share the
same active basetemp. Each run removes its own scratch folder after pytest
exits unless `PYTEST_KEEP_TMP=1` is set, and `make clean` removes the shared
scratch parent if a previous run was interrupted. The scratch root stays outside
the checkout so tests that inspect git ancestry keep their normal cold-clone
shape.

If you bypass `make` and run separate pytest subsets at the same time, pass a
unique `--basetemp` to each process. The default raw pytest basetemp is shared
through `.microcosm/test-tmp/pytest`, so parallel direct invocations can race
while copying fixture trees even when the code under test is fine.

For the full macro-root development suite, use `make test-all` from a checkout
where the sibling macro source paths are present.
This is a broad drift-detection lane rather than the public release floor: it
can surface exact-copy or source-freshness failures when macro source changes,
while pytest keeps tracked source-tree receipts read-only unless a caller
explicitly opts into receipt writes with
`MICROCOSM_TRACKED_RECEIPT_WRITES=1`. Temp receipts and caller-owned output
directories still write by default; tracked `receipts/**` snapshots are the
opt-in refresh surface. It uses the same outside-checkout pytest
scratch parent as `make test`; any generated output that needs to change still
belongs in its owner lane, not disposable temp state.
The default `make test`, `make package-smoke`, and `make ci` are the
standalone public verification floor.

After install, the fuller first-screen route is:

```bash
.venv/bin/microcosm hello .
.venv/bin/microcosm tour --card .
.venv/bin/microcosm status --card .
.venv/bin/microcosm authority --card
.venv/bin/microcosm workingness --card
.venv/bin/microcosm legibility-scorecard
```

If editable install is not available, keep the same first-screen route in
source form:

```bash
PYTHONPATH=src python3 -m microcosm_core hello .
PYTHONPATH=src python3 -m microcosm_core tour --card .
PYTHONPATH=src python3 -m microcosm_core status --card .
```

That is the source-only minimum: map, behavior proof, then status card. The
smoke section above lists the fuller source-form check set when you need the
authority, workingness, legibility, version, and stripping-boundary cards too.

## Standalone Candidate Export

To generate a bounded standalone folder and release-export receipt for review,
run the explicit export target:

```bash
make standalone-export EXPORT_OUT=/tmp/microcosm-substrate-export
```

This writes `/tmp/microcosm-substrate-export/microcosm-substrate/` and records
`receipts/release/release_export_receipt.json` inside that artifact. The target
is intentionally not part of `make ci`; it performs heavier outside-root smoke
checks and still keeps `release_authorized=false` until a separate human release
decision exists.

Before handing off that folder, validate it from inside the exported artifact:

```bash
cd /tmp/microcosm-substrate-export/microcosm-substrate
make ci
```

That cold-clone check proves the exported package can install, test, and smoke
from its own root. It does not authorize release; the release receipt remains
the authority boundary until a separate operator decision exists.

## Good Contributions

- Improve runnable public substrate: CLI behavior, validators, standards,
  fixtures, receipts, tests, examples, and card-first documentation.
- Import real non-secret macro bodies when they can be copied with provenance,
  bounded claims, and a validator or receipt that proves the boundary.
- Delete, demote, or label surfaces that imply fake progress, release
  readiness, private-root equivalence, or authority beyond their receipt.
- Keep compact commands useful before raw receipt trees. A cold reader should
  get an honest answer from cards before drilldown.

When you open a pull request, use `.github/PULL_REQUEST_TEMPLATE.md` as the
inline checklist for validation evidence, public/private payload exclusions,
claim boundaries, and standalone source inventory. The template is a guardrail,
not a release approval surface.

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

For the bounded cold-clone probe that checks fixture availability, secret
exclusion, and pattern-binding receipts, use:

```bash
./bootstrap.sh
```

The default writes ignored `.microcosm/cold_clone_probe.json` evidence so a
routine cold-clone smoke does not dirty tracked receipt files. Use `--emit` only
when you intentionally own a tracked receipt refresh.
