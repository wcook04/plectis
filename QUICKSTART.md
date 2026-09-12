# Quickstart

Run Plectis, inspect what it wrote, then choose one component to explore.
For an explanation before running anything, read
[Understanding Plectis](docs/UNDERSTANDING_PLECTIS.md).

## 1. First result

You need Git and Python 3.11 or newer. These commands use a macOS / Linux shell
(or WSL on Windows), and every later source command runs from the clone root:

```bash
git clone https://github.com/wcook04/plectis && cd plectis
PYTHONPATH=src python3 -m plectis tour --format text .
```

The tour reads the project, selects a route, writes a local record in
`.microcosm/` (ignored by git), and prints what it did. Your source files are
unchanged. The record describes this local run; it does not run every component.

```bash
PYTHONPATH=src python3 -m plectis tour --card .
PYTHONPATH=src python3 -m plectis hello .
```

`tour --card` returns the machine-readable result; `hello` gives a no-write
orientation card. In PowerShell, set `$env:PYTHONPATH = "src"` and use
`python -m plectis` in place of `PYTHONPATH=src python3 -m plectis`.

For a separate clone check, `./bootstrap.sh` validates the shipped fixture and
boundary checks and writes `.microcosm/cold_clone_probe.json`.
`./bootstrap.sh --dry-run` previews that command without running it.

## 2. Install

Installation is optional. The browse and browser steps use the source form,
so you can skip this step. To install into a virtual environment on macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/plectis tour --format text .
```

Use `.venv/bin/plectis` for installed commands, or activate the environment with
`source .venv/bin/activate` to use `plectis`. On Windows the corresponding paths
are `.venv\Scripts\python.exe` and `.venv\Scripts\plectis.exe`.

If pip reports `error: externally-managed-environment`, it is protecting a
system-managed Python ([PEP 668](https://peps.python.org/pep-0668/)). Use the
virtual environment above or the source commands; neither needs a system-wide
package installation. The runtime has no third-party dependencies, although
cloning and installing build / test dependencies can need network access.

## 3. Browse the component corpus

```bash
PYTHONPATH=src python3 -m plectis comprehend --slice mechanism --format text
PYTHONPATH=src python3 -m plectis comprehend --first-action "Replay a prompt injection example" --format text
```

The first command lists the component mechanisms. The second returns a matching
component, a command, its checks and the limit of the result; replace the quoted
goal with your own. Check the returned command's `--out` path before running it.
[The worked example](docs/UNDERSTANDING_PLECTIS.md#one-example-you-can-follow)
uses `.microcosm/` for output so the committed example records stay unchanged.

For other routes, use the [README Component Map](README.md#choose-a-route),
the [one-line component list](ORGANS.md#plectis-at-a-glance--every-organ-in-one-line)
or the [specialty index](ORGANS.md#find-your-specialty).

## 4. Inspect in a browser

```bash
PYTHONPATH=src python3 -m plectis serve . --host 127.0.0.1 --port 8765 --max-requests 7
```

Open `http://127.0.0.1:8765` while it runs. The server stops after seven requests;
a browser can make several requests for one page. Omit `--max-requests` only when
you want to keep exploring, then press Ctrl-C in the terminal to stop it.

## 5. Verify the public floor

```bash
make check   # registry and proof-trust preflight
make ci      # install, tests, smoke checks and package smoke used by CI
```

These targets need `make` and Python. `make check` runs without installation;
`make ci` creates its own temporary virtual environment and installs test
dependencies. The [validation runbook](docs/maintainers/validation.md) explains
the individual checks and gives a Python setup when `make` is unavailable.

## Boundaries

The runtime commands above make no network or model calls, with no source mutation.
Their results describe local checks, not general proof correctness or
production readiness. `.microcosm/` retains the project's older name; see
[Name and history](README.md#name-and-history). Once you know which result you
want to inspect, `PYTHONPATH=src python3 -m plectis evidence list . --limit 25`
lists local evidence. Continue with [the documentation map](docs/README.md), or
[CONTRIBUTING.md](CONTRIBUTING.md) if you want to change or check the code.
