# Quickstart

This is the shortest cold-clone path for a reader who wants to know whether
Microcosm is runnable, inspectable, and honest before opening the full README.
After the smoke path passes, use the [README Component Map](README.md#component-map)
before raw receipts; it names the runtime package, command cards, public
doctrine, evidence fixtures, source capsules, and validation shell.
For task-specific agent routing use [AGENT_ROUTES.md](AGENT_ROUTES.md); for the
one-line organ ladder use
[ORGANS.md#microcosm-at-a-glance--every-organ-in-one-line](ORGANS.md#microcosm-at-a-glance--every-organ-in-one-line);
for human specialty browsing use [ORGANS.md#find-your-specialty](ORGANS.md#find-your-specialty);
for the system shape use [ARCHITECTURE.md](ARCHITECTURE.md).

## 0. Run The Bounded Cold-Clone Probe

If you want one command before installing the console script, run the public
bootstrap probe:

```bash
./bootstrap.sh
```

It validates the first-wave fixture and boundary floor, writes ignored
`.microcosm/cold_clone_probe.json` evidence, and points back to the README map.
Use `./bootstrap.sh --dry-run` to see the exact probe command without writing a
receipt. Do not use `--emit` for tracked receipts unless you intentionally own
a receipt refresh.

## 1. Install The Local Command

From this directory:

```bash
python3 -m pip install -e '.[test]'
```

Or use the source form without installing:

```bash
PYTHONPATH=src python3 -m microcosm_core hello .
```

## 2. Run The Public Smoke Path

```bash
make smoke
```

The smoke path writes command outputs under ignored `.microcosm/smoke/`,
validates those receipts, and prints a compact terminal summary. A healthy run
includes `Microcosm smoke check: pass`, `authority: pass`, `workingness: clear`,
and `served status: pass`. It uses compact cards first:

```bash
microcosm hello .
microcosm hello --reader cold_cloner .
microcosm hello --reader reviewer .
microcosm hello --reader skeptical_reviewer .
microcosm hello --reader agent .
microcosm hello --reader domain_specialist .
microcosm first-screen --card .
microcosm tour --card .
microcosm status --card .
microcosm authority --card
microcosm workingness --card
microcosm legibility-scorecard
```

If you are staying source-only, use the exact same hand smoke through the
module entry point:

```bash
PYTHONPATH=src python3 -m microcosm_core hello .
PYTHONPATH=src python3 -m microcosm_core hello --reader cold_cloner .
PYTHONPATH=src python3 -m microcosm_core hello --reader reviewer .
PYTHONPATH=src python3 -m microcosm_core hello --reader skeptical_reviewer .
PYTHONPATH=src python3 -m microcosm_core hello --reader agent .
PYTHONPATH=src python3 -m microcosm_core hello --reader domain_specialist .
PYTHONPATH=src python3 -m microcosm_core first-screen --card .
PYTHONPATH=src python3 -m microcosm_core tour --card .
PYTHONPATH=src python3 -m microcosm_core status --card .
PYTHONPATH=src python3 -m microcosm_core authority --card
PYTHONPATH=src python3 -m microcosm_core workingness --card
PYTHONPATH=src python3 -m microcosm_core legibility-scorecard
```

Read those as a first-screen contract, not a launch badge. They show local
behavior, route state, evidence classes, failure envelopes, and scope limits
before sending you into full receipt drilldowns.
The reader-specific `hello` aliases are a shortcut into the same card:
`cold_cloner` / `cold-cloner` maps to the public GitHub visitor branch,
`interesting_parts` / `interesting-parts` maps to that same public visitor
branch for "what is interesting here?" questions,
`skeptical_reviewer` / `skeptical-reviewer` / `reviewer` maps to the safety/evals branch,
and `agent` / `type-a-agent` maps to the repo-reading agent branch.
`domain_specialist` / `domain-specialist` is the specialty reader branch and
points back to `ORGANS.md#find-your-specialty`; it is not an expert-review or
domain-correctness claim.

## 3. Inspect The Browser Surface

```bash
microcosm serve . --host 127.0.0.1 --port 8765 --max-requests 7
```

If you are staying source-only, run the same bounded server through the module
entry point:

```bash
PYTHONPATH=src python3 -m microcosm_core serve . --host 127.0.0.1 --port 8765 --max-requests 7
```

Open `http://127.0.0.1:8765` while the server is running. Browser visits to
the drilldowns show readable HTML pages with the JSON payload embedded; clients
that request `application/json` receive the raw JSON. The compact drilldowns
are:

- `/project/status`
- `/project/first-screen`
- `/project/observatory-card`
- `/workingness-card`
- `/project/first-screen-full`
- `/project/observatory`

Treat `/project/observatory-card` as the compact Demo To Scale bridge: it
joins local `.microcosm/` state and status with the runtime bridge summary:
intake, reveal, proof-lab, and evidence endpoints; projection status counts;
open/closed intake-cell counts; and authority-safe receipt refs. Use
`/project/observatory` only when you need the expanded model.

Open `/workingness` only when you need the full per-organ failure-envelope map.

## 4. Verify The Public Floor

For the fastest preflight before the full test floor, run:

```bash
make check
```

It should print `Microcosm preflight: organ evidence-class registry loads
cleanly.`

```bash
make ci
```

`make ci` is the GitHub Actions floor: editable install, public tests,
source-form smoke, and package-install smoke. To run only the fresh-venv
package check:

```bash
make package-smoke
```

For a reviewer-grade replay packet that preserves command output digests,
scope limits, private-path scans, and blocked/non-zero command evidence
without rerunning the substrate during verification, run:

```bash
make flight-recorder FLIGHT_RECORDER_OUT=/tmp/microcosm-flight-recorder
make flight-recorder-verify FLIGHT_RECORDER_VERIFY_DIR=/tmp/microcosm-flight-recorder
```

This is an evaluation artifact, not a launch, standards, external-model,
formal-result correctness, or production-readiness decision.

For a cold clone, treat `make ci` as the public green floor. `make validate`
adds the doctrine-lattice drift check and is the maintainer pre-commit gate
when you are changing doctrine-lattice projection inputs or generated entry
cards; it is not a broader launch, formal-result correctness, or production claim.

For a review artifact outside this checkout, run:

```bash
make standalone-export EXPORT_OUT=/tmp/microcosm-substrate-export
```

That export writes a candidate standalone folder and a review receipt inside
the artifact. The receipt records a local review export, not a launch operation.

Before sharing that folder, validate the exported artifact as its own clone:

```bash
cd /tmp/microcosm-substrate-export/microcosm-substrate
make ci
```

This checks standalone install, tests, and smoke from the exported root. It
stays inside local review scope.

## Boundaries

Microcosm is a local source-open research runtime. These commands stay scoped
to local inspection, tests, source-linked records, and result evidence; launch
operations, hosted sharing, external model access, source-file changes, proof
correctness, trading or financial decisions, production security claims,
private-system equivalence, and account-secret or session export are outside
that scope.

Receipts are drilldown evidence. Start with the compact cards; open raw
receipts only after you know which claim, route, or failure mode you are
checking. Use `microcosm evidence list . --limit 25` for a bounded receipt
index, then inspect a listed project ref with
`microcosm evidence inspect . .microcosm/evidence/routes.json` or
`microcosm evidence inspect --project . .microcosm/evidence/routes.json`.
If you are staying source-only, use
`PYTHONPATH=src python3 -m microcosm_core evidence list . --limit 25` and
`PYTHONPATH=src python3 -m microcosm_core evidence inspect . .microcosm/evidence/routes.json`.
Use `--limit 0` only when you intentionally want the full list.
