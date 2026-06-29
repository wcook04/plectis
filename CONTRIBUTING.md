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

Before a commit, `make validate` runs the full `ci` floor plus the
doctrine-lattice drift check in one command, and `make check` is a sub-second
organ-registry integrity preflight you can run on every save.

Before choosing a file to edit, use the README
[Public Repo Map](README.md#choose-a-route) and
[Component Map](README.md#choose-a-route). Treat those sections as the
contributor routing layer: they identify the runtime package, command cards,
public doctrine, evidence fixtures, source capsules, and validation shell.
The commands below are validation lanes after that route, not a replacement
for it.

The smoke target is the no-install public sanity check. It writes ignored
`.microcosm/` route state through `tour --card`, stores command outputs under
`.microcosm/smoke/`, then checks the compact public authority, workingness,
legibility, version, and stripping-boundary surfaces without dumping the full
cards into CI logs. A healthy terminal summary includes
`Plectis smoke check: pass`, `authority: pass`, `workingness: clear`, and
`served status: pass`:

```bash
PYTHONPATH=src python3 -m microcosm_core hello .
PYTHONPATH=src python3 -m microcosm_core hello --reader cold_cloner .
PYTHONPATH=src python3 -m microcosm_core hello --reader skeptical_reviewer .
PYTHONPATH=src python3 -m microcosm_core hello --reader agent .
PYTHONPATH=src python3 -m microcosm_core hello --reader domain_specialist .
PYTHONPATH=src python3 -m microcosm_core first-screen --card .
PYTHONPATH=src python3 -m microcosm_core tour --card .
PYTHONPATH=src python3 -m microcosm_core status --card .
PYTHONPATH=src python3 -m microcosm_core authority --card
PYTHONPATH=src python3 -m microcosm_core workingness --card
PYTHONPATH=src python3 -m microcosm_core legibility-scorecard
PYTHONPATH=src python3 -m microcosm_core --version
PYTHONPATH=src python3 -m microcosm_core stripping-guard
```

The reader-specific `hello` rows in that source-form smoke are branch checks,
not new doctrine: `cold_cloner` / `cold-cloner`, `skeptical_reviewer` /
`skeptical-reviewer`, and `agent` / `type-a-agent` are aliases for existing
first-screen routes, while `domain_specialist` / `domain-specialist` is the
specialty-reader branch that points back to the generated organ specialty
index.

`make clean` removes the smoke receipt directory and the shared pytest scratch
root while leaving the rest of project-local `.microcosm/` state alone.

The package smoke target installs this source tree into a fresh temporary venv
and runs the installed `microcosm` console command through the compact cards.
Use it when the question is package installability rather than source-form
runtime behavior.

The test target creates a checkout-keyed temporary venv under
`$(TMPDIR)/microcosm-substrate-venv-<checkout-key>`, installs the test extra
there, and then runs pytest, so a clean clone does not need pytest preinstalled
or system-site package writes. If you want a stable command path, set `VENV`
explicitly when you install. The Makefile also routes pytest basetemp, Python bytecode
cache, and `TMPDIR` under per-run folders inside
`$(TMPDIR)/microcosm-substrate-test-tmp` so broad local runs do not share the
same active basetemp. Each run removes its own scratch folder after pytest
exits unless `PYTEST_KEEP_TMP=1` is set, and `make clean` removes the shared
scratch parent if a previous run was interrupted. The scratch root stays outside
the checkout so tests that inspect git ancestry keep their normal cold-clone
shape. Microcosm also disables pytest's cache provider in `pyproject.toml`, so
direct pytest does not create `.pytest_cache` in the checkout.

If you bypass `make` and run separate pytest subsets at the same time, pass a
unique `--basetemp` to each process. Parallel direct invocations can still race
while copying fixture trees if they are forced to share one basetemp, even when
the code under test is fine.

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
VENV=/tmp/plectis-dev-venv make install
/tmp/plectis-dev-venv/bin/plectis hello .
/tmp/plectis-dev-venv/bin/plectis first-screen --card .
/tmp/plectis-dev-venv/bin/plectis tour --card .
/tmp/plectis-dev-venv/bin/plectis status --card .
/tmp/plectis-dev-venv/bin/plectis authority --card
/tmp/plectis-dev-venv/bin/plectis workingness --card
/tmp/plectis-dev-venv/bin/plectis legibility-scorecard
```

If editable install is not available, keep the same first-screen route in
source form:

```bash
PYTHONPATH=src python3 -m microcosm_core hello .
PYTHONPATH=src python3 -m microcosm_core hello --reader cold_cloner .
PYTHONPATH=src python3 -m microcosm_core hello --reader skeptical_reviewer .
PYTHONPATH=src python3 -m microcosm_core hello --reader agent .
PYTHONPATH=src python3 -m microcosm_core hello --reader domain_specialist .
PYTHONPATH=src python3 -m microcosm_core tour --card .
PYTHONPATH=src python3 -m microcosm_core status --card .
```

That is the source-only minimum: map, reader branches, behavior proof, then
status card. The smoke section above lists the fuller source-form check set
when you need the authority, workingness, legibility, version, and
stripping-boundary cards too.

## Standalone Candidate Export

To generate a bounded standalone folder and release-export receipt for review,
run the explicit export target:

```bash
make standalone-export EXPORT_OUT=/tmp/plectis-export
```

This writes `/tmp/plectis-export/plectis/` and records
`receipts/release/release_export_receipt.json` inside that artifact. The target
is intentionally not part of `make ci`; it performs heavier outside-root smoke
checks and still keeps `release_authorized=false` until a separate human release
decision exists.

Before handing off that folder, validate it from inside the exported artifact:

```bash
cd /tmp/plectis-export/plectis
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
boundary docs, first run `VENV=/tmp/plectis-dev-venv make install` if your
environment does not already have the test extra installed, then use the
source-tree form:

```bash
PYTHONPATH=src /tmp/plectis-dev-venv/bin/python -m pytest tests/test_public_entry_docs.py tests/test_secret_exclusion_scan.py tests/test_private_state_scan.py
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
