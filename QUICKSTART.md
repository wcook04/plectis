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

The tour lists project files in `.microcosm/catalog.json` and proposes tasks
such as inspecting a README in `.microcosm/routes.json`. It records a simulated
task run; it does not execute your project's tests. Your source files are
unchanged, and `.microcosm/` is ignored by git. The component examples have separate commands.

```bash
PYTHONPATH=src python3 -m plectis tour --card .
PYTHONPATH=src python3 -m plectis hello .
```

`plectis tour --card` prints JSON including the selected job's identifier; `hello`
prints introductory text without creating files. In PowerShell, set `$env:PYTHONPATH = "src"` and use
`python -m plectis` in place of `PYTHONPATH=src python3 -m plectis`.

`./bootstrap.sh` runs the supplied examples in
`fixtures/first_wave/pattern_binding_contract/input` and scans for forbidden secret strings. It writes
`.microcosm/cold_clone_probe.json` with the resulting status.
`./bootstrap.sh --dry-run` previews that command without running it.

## Use your own coding agent

Open this clone in any coding agent that can read files and run shell commands.
Ask it to read `AGENTS.override.md`, then give it a concrete question or change.
The public commands use local files; they do not need the author's private
system or a model API key. Your coding agent has its own provider requirements.

For new work, start from public `main`. Before running an example, record the
checkout and any local changes:

```bash
git rev-parse HEAD
git status --short
git ls-remote https://github.com/wcook04/plectis.git refs/heads/main
PYTHONPATH=src python3 -m plectis comprehend --first-action "Replay a prompt injection example" --format text
```

The first and third commands report the local and current public commits.
The third needs a network connection but changes no files. Different commits
can mean older, ahead or divergent work; preserve existing changes and use a
fresh clone in another directory when you need current `main`. A release tag
is a frozen edition. Offline, use the local tools and report that public
currentness was not checked.

Follow the selected component's command, replacing the `plectis` executable
with `PYTHONPATH=src python3 -m plectis` if you did not install it. Put run
outputs under `.microcosm/`, as in the worked example below. Return the commit,
commands, input and output paths, what passed or failed, and what the example
does not establish. A concrete failed run is a useful contribution too; see
[CONTRIBUTING](CONTRIBUTING.md).

For theorem status, proof search or mathematical work, use the separate
[Lean corpus agent quickstart](https://github.com/wcook04/plectis-erdos/blob/main/docs/agents/AGENT_WORKBENCH.md#start-with-current-public-work).
Its `scripts/agent_entry.py` selects the mathematical workflow and reports
checkout provenance. Plectis component examples do not substitute for that
repository's proof evidence.

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

The first command prints an implementation summary for each component. The
second matches words in the quoted goal to a component and prints commands,
input/output paths and saved result paths; it does not run those commands.
Replace the goal with your own. Check the printed `--out` path before running it.
[The worked example](docs/UNDERSTANDING_PLECTIS.md#one-example-you-can-follow)
uses `.microcosm/` for output so the committed example records stay unchanged.

For other examples and source files, use the [README Component Map](README.md#choose-a-route),
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
make check   # reject registry errors and prohibited Lean source syntax
make ci      # install, run tests, run example commands, install/run the package
```

These targets need `make` and Python. `make check` rejects missing or unknown
component/evidence-class IDs and prohibited syntax in shipped Lean source.
`make ci` also creates a temporary virtual environment and installs test
dependencies. The [validation runbook](docs/maintainers/validation.md) lists
the programs each target runs and gives a Python setup when `make` is unavailable.

## Boundaries

The runtime commands above make no network or model calls, with no source mutation.
The prompt-injection example compares prepared JSON rows with policy rules;
it does not measure a model's response to a hostile page.
`.microcosm/` retains the project's older name; see
[Name and history](README.md#name-and-history). Once you know which result you
want to inspect, `PYTHONPATH=src python3 -m plectis evidence list . --limit 25`
lists the saved result files. Continue with [the documentation map](docs/README.md), or
[CONTRIBUTING.md](CONTRIBUTING.md) if you want to change or check the code.
