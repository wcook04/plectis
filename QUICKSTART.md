# Quickstart

The shortest trustworthy path from a clone to a meaningful local result. The
deeper review lanes (full smoke set, flight recorder, standalone export) live
in [CONTRIBUTING.md](CONTRIBUTING.md) and `docs/maintainers/`.

## 1. Install

```bash
git clone https://github.com/wcook04/plectis && cd plectis
python3 -m pip install .
```

There are no third-party runtime dependencies (Python 3.11+). If you would
rather not install anything, every command below also runs in source form:
swap `plectis` for `PYTHONPATH=src python3 -m plectis`. To probe the clone
before installing, run `./bootstrap.sh`; it validates the fixture and boundary
floor, writes ignored `.microcosm/cold_clone_probe.json` evidence, and
`./bootstrap.sh --dry-run` previews the exact command first.

## 2. First result

```bash
plectis tour --format text .
```

It reads the project, picks a route, writes a local record beside it
(`.microcosm/`, ignored by git), and prints what it did. Your source files are
never changed. The same record as a machine-readable card:

```bash
plectis tour --card .
plectis hello .
```

`hello` is the no-write orientation card; `tour --card` is the state-writing
behaviour proof.

## 3. Browse the component corpus

```bash
plectis comprehend --slice mechanism --format text
plectis comprehend --first-action "<your goal>" --format text
```

The first command prints every component's real mechanism, one line each. The
second routes a concrete goal to the owning component, the command that tests
it, and the limit of the result. For reading rather than running, use the
[README Component Map](README.md#choose-a-route), the one-line ladder at
[ORGANS.md#plectis-at-a-glance--every-organ-in-one-line](ORGANS.md#plectis-at-a-glance--every-organ-in-one-line),
or the human specialty index at
[ORGANS.md#find-your-specialty](ORGANS.md#find-your-specialty).

## 4. Inspect in a browser

```bash
plectis serve . --host 127.0.0.1 --port 8765 --max-requests 7
```

Open `http://127.0.0.1:8765` while it runs. Omit `--max-requests` only when
you intentionally want an interactive server.

## 5. Verify the public floor

```bash
make check   # sub-second registry preflight
make ci      # the same install + test + smoke floor GitHub Actions runs
```

## Boundaries

Everything above is local: no network or model calls, no source mutation, and
no release, hosting, proof-correctness, or financial-advice authority. The
local state directory keeps the compatibility name `.microcosm/`, and the
legacy `microcosm` command remains an alias; see the README's
[Name and history](README.md#name-and-history). Receipts are drilldown
evidence: start with the compact cards, and open raw receipts (via
`plectis evidence list . --limit 25`) only once you know which claim you are
checking.
