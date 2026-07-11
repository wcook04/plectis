# Validation runbook (maintainers and reviewers)

This is the deep lane behind [CONTRIBUTING.md](../../CONTRIBUTING.md). The
public floor is `make ci`; everything here is for reviewers who want the full
card set, drift detection, or a distribution-true proof.

## The full smoke card set

`make smoke` writes ignored receipts under `.microcosm/smoke/`, validates
them, and prints a compact summary. A healthy run includes
`Plectis smoke check: pass`, `authority: pass`, `workingness: clear`, and
`served status: pass`. The same cards by hand, installed form:

```bash
plectis hello .
plectis hello --reader cold_cloner .
plectis hello --reader reviewer .
plectis hello --reader skeptical_reviewer .
plectis hello --reader agent .
plectis hello --reader domain_specialist .
plectis first-screen --card .
plectis tour --card .
plectis status --card .
plectis authority --card
plectis workingness --card
plectis legibility-scorecard
```

The target stores command outputs under `.microcosm/smoke/` and validates
them without dumping the full cards into CI logs.

Source-only form: prefix with `PYTHONPATH=src` and swap `plectis` for
`python3 -m plectis` (the module façade; `python3 -m microcosm_core` remains
the compatibility spelling). The reader-specific `hello` rows are branch
checks, not new doctrine: `cold_cloner` / `cold-cloner` maps to the public
GitHub visitor branch, `skeptical_reviewer` / `skeptical-reviewer` /
`reviewer` to the safety/evals branch, `agent` / `type-a-agent` to the
repo-reading agent branch, and `domain_specialist` / `domain-specialist` to
the generated organ specialty index.

## Browser drilldowns

The bounded server (`plectis serve . --host 127.0.0.1 --port 8765
--max-requests 7`) exposes the compact drilldowns `/project/status`,
`/project/first-screen`, `/project/observatory-card`, `/workingness-card`,
`/project/first-screen-full`, and `/project/observatory`. Treat
`/project/observatory-card` as the compact bridge into local state, status,
and evidence endpoints; open `/workingness` only when you need the full
per-organ failure-envelope map.

## Receipt drilldowns

Receipts are drilldown evidence after the cards: `plectis evidence list .
--limit 25` gives a bounded receipt index, then
`plectis evidence inspect . .microcosm/evidence/routes.json` (or the
`--project .` spelling) opens a listed ref. Use `--limit 0` only when you
intentionally want the full list.

## Pytest isolation detail

If `make` is unavailable, the equivalent environment is
`python3 -m venv /tmp/plectis-dev-venv` followed by
`/tmp/plectis-dev-venv/bin/python -m pip install -e '.[test]'`.

`make test` creates a checkout-keyed temporary venv under
`$(TMPDIR)/microcosm-substrate-venv-<checkout-key>`, installs the test extra,
and routes pytest basetemp, Python bytecode cache, and `TMPDIR` under per-run
folders inside `$(TMPDIR)/microcosm-substrate-test-tmp` so broad local runs do
not share the same active basetemp. Each run removes its own scratch folder
unless `PYTEST_KEEP_TMP=1` is set; `make clean` removes the shared scratch
parent after an interrupted run. The scratch root stays outside the checkout
so tests that inspect git ancestry keep their cold-clone shape, and pytest's
cache provider is disabled in `pyproject.toml`, so direct pytest does not
create `.pytest_cache` in the checkout.

## The drift-detection lane

`make test-all` is the broad macro-root drift-detection suite, not the public
release floor. From a checkout where the sibling macro source paths are
present it can surface exact-copy or source-freshness failures when macro
source changes. Pytest keeps tracked source-tree receipts read-only unless a
caller explicitly opts in with `MICROCOSM_TRACKED_RECEIPT_WRITES=1`; tracked
`receipts/**` snapshots are the opt-in refresh surface.

## Reviewer proof packets

```bash
make flight-recorder FLIGHT_RECORDER_OUT=/tmp/microcosm-flight-recorder
make flight-recorder-verify FLIGHT_RECORDER_VERIFY_DIR=/tmp/microcosm-flight-recorder
```

The flight recorder preserves command output digests, scope limits,
private-path scans, and blocked/non-zero command evidence; verification
replays the packet without rerunning the substrate. It is an evaluation
artifact, not a launch decision, and does not authorize release.

```bash
make release-candidate-proof
make release-candidate-proof-verify
make release-review
```

`release-review` regenerates the proof packet fresh, verifies it with the
strict no-rerun verifier, and prints the reviewer card (contract:
`RELEASE_REVIEW.md`).

## Standalone export

```bash
make standalone-export EXPORT_OUT=/tmp/plectis-export
```

This writes a candidate standalone folder plus
`receipts/release/release_export_receipt.json` inside the artifact. It is
intentionally not part of `make ci`, performs heavier outside-root smoke
checks, and keeps `release_authorized=false` until a separate human release
decision exists. Before handing the folder off, validate it as its own clone:

```bash
cd /tmp/plectis-export/plectis
make ci
```

That cold-clone check proves the exported package can install, test, and
smoke from its own root. It does not authorize release.
