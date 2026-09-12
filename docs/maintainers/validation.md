# Validation runbook (maintainers and reviewers)

This guide explains the commands linked from [CONTRIBUTING.md](../../CONTRIBUTING.md)
and the [README](../../README.md). `make ci` runs the public test suite, example
commands and package-installation test. The commands below let you inspect
individual outputs, compare saved records, or repeat the installation tests
in an exported copy.

Run them from the repository root. The Make targets need `make` and Python.
For the shorter `plectis` command, first follow the virtual-environment
installation in [Quickstart](../../QUICKSTART.md#2-install). Without installing,
replace `plectis` with `PYTHONPATH=src python3 -m plectis` in this guide's
commands. `python3 -m microcosm_core` remains the compatibility spelling.

## The full smoke card set

`make smoke` runs selected CLI commands and saves their output under
`.microcosm/smoke/`, which Git ignores. A *card* is a JSON summary of a
command's result. The Makefile then runs `scripts/check_smoke_outputs.py`,
which reads those files and tests their required fields, statuses and
references. It prints a summary instead of every JSON file.

Expected summary lines include `Plectis smoke check: pass`, `authority: pass`,
`workingness: clear` and `served status: pass`. These report the particular
conditions tested by the script. They do not establish that every component
works with every input.

To inspect individual commands, using an installed `plectis`:

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

The `hello --reader` options select different introductions:

| Option and accepted aliases | Introduction printed |
|---|---|
| `cold_cloner`, `cold-cloner` | First commands for someone who just cloned the repository. |
| `reviewer`, `skeptical_reviewer`, `skeptical-reviewer` | Agent-safety and evaluation examples. |
| `agent`, `type-a-agent` | Instructions for a coding agent working with the repository. |
| `domain_specialist`, `domain-specialist` | The generated organ specialty index: components grouped by subject. |

The complete `make smoke` command list is in [Makefile](../../Makefile). It
also includes the proof-lab example, local HTTP response tests, a first-action
query, the package version and a scan for forbidden private strings. The Makefile keeps
output even when an individual command exits with an error; the final script
determines whether the saved files satisfy the smoke-test conditions.

<a id="browser-drilldowns"></a>

## Inspect the local HTTP responses

Start the local server with:

```bash
plectis serve . --host 127.0.0.1 --port 8765 --max-requests 7
```

Open `http://127.0.0.1:8765` with one of the paths below appended. The browser
shows the JSON data in a formatted HTML page; clients requesting
`Accept: application/json` receive raw JSON. The server stops after seven
requests; a browser may make additional requests for page assets. Omit `--max-requests 7` for a longer session and press Ctrl-C to stop it.

| Path | Data returned |
|---|---|
| `/project/status` | Project status. |
| `/project/first-screen` | First commands, introductions for different readers and links to project summaries. |
| `/project/first-screen-full` | The longer introduction, with component classifications, result references and scope limits. |
| `/project/observatory-card` | Compact list of project-state summaries and links. |
| `/project/observatory` | The longer project-state response. |
| `/workingness-card` | Summary of the component definitions and recorded failure conditions. |
| `/workingness` | The full per-component records used for that summary. |

<a id="receipt-drilldowns"></a>

## Open saved result files

List up to 25 saved results, then print a summary of one by its path:

```bash
plectis evidence list . --limit 25
plectis evidence inspect . .microcosm/evidence/routes.json
```

The `inspect` command also accepts `--project .` instead of the positional
project directory. `--limit 0` prints the complete list. `inspect` prints
metadata and a summary, including the command for opening the full JSON file.
For this example, that command is:

```bash
python3 -m json.tool .microcosm/evidence/routes.json
```

Run `plectis tour --card .` first if the result file does not exist. Reading
a saved result does not rerun the command that produced it.

## Pytest isolation detail

If `make` is unavailable, install the test dependencies in a virtual environment:

```bash
python3 -m venv /tmp/plectis-dev-venv
/tmp/plectis-dev-venv/bin/python -m pip install -e '.[test]'
```

You can then invoke pytest through `/tmp/plectis-dev-venv/bin/python -m pytest`.
The public test-file list is `PUBLIC_TESTS` in [Makefile](../../Makefile).

`make test` creates a temporary virtual environment whose name is derived from
the checkout path. It gives each run separate directories for pytest inputs,
Python bytecode and temporary files. The directories are outside the checkout,
so tests that inspect Git history do not count their own temporary files.
The pytest cache is disabled in `pyproject.toml`.

Each run removes its temporary files unless `PYTEST_KEEP_TMP=1` is set.
`make clean` can remove files left by an interrupted run; wait for other test
processes to finish before removing their shared temporary parent directory.
When running pytest commands in parallel yourself, give each a different
`--basetemp` directory.

<a id="the-drift-detection-lane"></a>

## Compare against the private source checkout

`make test-all` runs the complete pytest collection. Some tests compare public
copies with files in the private parent repository and require that repository
to be available locally. A missing private source file is different from a
failure of the public package. Use `make ci` for the test suite intended for
a standalone public clone.

Pytest refuses to write tracked `receipts/**` files by default. To refresh
committed results, use their documented producer program. Set
`MICROCOSM_TRACKED_RECEIPT_WRITES=1` only for an intentional refresh; do not
change saved outputs merely to make an assertion pass.

## Reviewer proof packets

A *packet* here is a directory containing command outputs, JSON summaries and
file hashes. There are two separate procedures.

### Record commands and compare their saved outputs

```bash
make flight-recorder FLIGHT_RECORDER_OUT=/tmp/microcosm-flight-recorder
make flight-recorder-verify FLIGHT_RECORDER_VERIFY_DIR=/tmp/microcosm-flight-recorder
```

`flight-recorder` runs the commands listed in
[`command_plan`](../../src/microcosm_core/skeptic_flight_recorder.py), records
their exit statuses and output, and writes `flight-recorder-packet.json`.
It retains failed commands. It also records file hashes before and after the
run and scans output for forbidden private paths or strings.

`flight-recorder-verify` reads the packet, recomputes hashes and summaries
from its saved files, and writes `flight-recorder-verification.json`. It does
not run the recorded commands again. Agreement between a packet and its
files establishes internal consistency; it is not independent confirmation
that the described experiment occurred. Run the first command again if you
want new observations.

### Compare a checkout, installed package and exported copy

```bash
make release-candidate-proof
make release-candidate-proof-verify
make release-review
```

`release-candidate-proof` runs the same first-action query in three contexts:
the source checkout, a fresh package installation and a standalone export.
It compares the selected component IDs exactly. For the suggested command
and validator, it removes recognised invocation prefixes and normalises
whitespace before comparing the strings. It compares these results with each
other and with `receipts/code_lens/first_action_demo.json`; it does not execute
the suggested finance command or validator. It also runs the predefined
`comprehension-assay --first-action` scenarios in each context. The output
files are `release-candidate-proof.json` and `release-candidate-proof-card.md`.

`release-candidate-proof-verify` recomputes the comparisons from the recorded
files without rerunning the commands in those three environments. `release-review` performs
both steps, then prints the Markdown summary. You can run `make release-review`
on its own; the first two commands are available when you want each step
separately. [RELEASE_REVIEW.md](../../RELEASE_REVIEW.md) names the exact query,
fields compared and failure codes.

These commands do not evaluate forecasting accuracy, prove a mathematical
theorem or establish whole-system correctness. Do not treat a successful
result as permission to publish a release or use private material.

## Standalone export

```bash
make standalone-export EXPORT_OUT=/tmp/plectis-export
```

This writes an exported `plectis` directory and
`receipts/release/release_export_receipt.json` inside it. The exporter runs
additional programs in the exported directory; it is not part of `make ci`.
The receipt records `release_authorized=false`: this command does not grant
permission to publish. Publication requires a separate operator decision.

Before distributing the directory, run its own installation, tests and examples:

```bash
cd /tmp/plectis-export/plectis
make ci
```

A successful run establishes that those commands worked in that exported
copy. It does not authorize release.
