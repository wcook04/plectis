# Quickstart

This is the shortest cold-clone path for a reader who wants to know whether
Microcosm is runnable, inspectable, and honest before opening the full README.
After the smoke path passes, use the [README Component Map](README.md#component-map)
before raw receipts; it names the runtime package, command cards, public
doctrine, evidence fixtures, source capsules, and validation shell.

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

The smoke path writes command outputs under ignored `.microcosm/smoke/` and
uses compact cards first:

```bash
microcosm hello .
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
PYTHONPATH=src python3 -m microcosm_core first-screen --card .
PYTHONPATH=src python3 -m microcosm_core tour --card .
PYTHONPATH=src python3 -m microcosm_core status --card .
PYTHONPATH=src python3 -m microcosm_core authority --card
PYTHONPATH=src python3 -m microcosm_core workingness --card
PYTHONPATH=src python3 -m microcosm_core legibility-scorecard
```

Read those as a first-screen contract, not a release badge. They show local
behavior, route state, evidence classes, failure envelopes, and authority
ceilings before sending you into full receipt drilldowns.

## 3. Inspect The Browser Surface

```bash
microcosm serve . --host 127.0.0.1 --port 8765 --max-requests 6
```

If you are staying source-only, run the same bounded server through the module
entry point:

```bash
PYTHONPATH=src python3 -m microcosm_core serve . --host 127.0.0.1 --port 8765 --max-requests 6
```

Open `http://127.0.0.1:8765` while the server is running. The compact JSON
drilldowns are:

- `/project/status`
- `/project/first-screen`
- `/project/observatory-card`
- `/workingness-card`
- `/project/first-screen-full`
- `/project/observatory`

Open `/workingness` only when you need the full per-organ failure-envelope map.

## 4. Verify The Public Floor

```bash
make ci
```

`make ci` is the GitHub Actions floor: install, public tests, and smoke. For a
review artifact outside this checkout, run:

```bash
make standalone-export EXPORT_OUT=/tmp/microcosm-substrate-export
```

That export writes a candidate standalone folder and a
`receipts/release/release_export_receipt.json` inside the artifact. It still
keeps `release_authorized=false`.

Before sharing that folder, validate the exported artifact as its own clone:

```bash
cd /tmp/microcosm-substrate-export/microcosm-substrate
make ci
```

This checks standalone install, tests, and smoke from the exported root. It does
not authorize release.

## Boundaries

Microcosm is a local source-open research runtime. These commands do not
authorize release, hosted publication, provider calls, source mutation, proof
correctness, trading or financial advice, production security claims,
private-root equivalence, or credential/session export.

Receipts are drilldown evidence. Start with the compact cards; open raw
receipts only after you know which claim, route, or failure mode you are
checking. Use `microcosm evidence list . --limit 25` for a bounded receipt
index, then inspect a listed project ref with
`microcosm evidence inspect . .microcosm/evidence/routes.json` or
`microcosm evidence inspect --project . .microcosm/evidence/routes.json`.
Use `--limit 0` only when you intentionally want the full list.
