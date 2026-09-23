# Contributing

Contributions and error reports are welcome. You can improve one example or
report a wrong result without understanding every program in the repository.
Useful contributions include:

- fixing a command, adding a test case or making an example easier to run;
- explaining what a command reads, computes and writes, or repairing a broken link;
- showing an input that a validator accepts although it violates the stated rule;
- adding a program with its source history, input files, expected output and
  test functions, and stating which claim follows from that output.

If you are still choosing where to start, [Understanding Plectis](docs/UNDERSTANDING_PLECTIS.md)
names three JSON-field comparisons in the prompt-injection example. The README's
[Choose a route](README.md#choose-a-route) table helps you find another area.
Pick one concrete discrepancy or improvement and keep the change focused on it.

## Propose a public infrastructure change

An idea does not need a patch. Open a [toolkit issue](https://github.com/wcook04/plectis/issues)
with one observable problem, the change you suggest, and how another reader
could tell whether it helped. Name a public command or file when you can, and
say how you would like your idea, code, test, or review credited if adopted.

For the Lean corpus, proof workflow, or mathematics contributor path, use the
separate [architecture proposal form](https://github.com/wcook04/plectis-erdos/issues/new?template=architecture_proposal.yml).
It accepts a plain-language idea and asks for an observable stop condition and
credit preference. Neither route requires access to the private workbench.

## Try an entry-route experiment

Can a new reader ask for a first example and get a relevant, runnable step?
From a fresh clone with Python 3.11 or newer, run this public-only probe:

```bash
git rev-parse HEAD
python3 --version
PYTHONPATH=src python3 -m plectis comprehend --first-action "find and run a first example in a fresh clone" --format text
```

Read the returned `Do this first`, reason, and limits.
The documented first example is the project tour in [Quickstart](QUICKSTART.md#1-first-result),
which runs from source and writes under ignored `.microcosm/`. Check whether the
returned command matches that example. In a clone without an install, the
printed `plectis tour` command has this source form:

```bash
PYTHONPATH=src python3 -m microcosm_core tour --format text .
```

If the route matches, run it once. Stop after that one run or at the first
mismatch: an unrelated route, a missing command or input, or an
unclear next step. Do not run a command that writes tracked receipts just to
complete this experiment.

Report the commit, operating system, Python version, exact prompt and output,
what first step you expected, and what you observed. If you ran the variant,
include its output path. A focused fix can add a test for the same prompt and
observed route. Use only this repository's public source and fixtures; the
larger private system is outside this contribution route. For theorem status,
Lean proofs, or paper questions, use the
[mathematics companion](https://github.com/wcook04/plectis-erdos) instead.

## Reporting a discrepancy

Report an output that differs from the documented expected result, a validator
that accepts an invalid input, or a generated table whose entries differ from
its source JSON. Open a GitHub issue at
<https://github.com/wcook04/plectis/issues> with:

- the commit you ran (`git rev-parse HEAD`);
- the exact command and the operating system and Python version;
- what you expected, with the saved result file's path where one applies;
- what you observed, with the failing output pasted or attached.

Keep the input and failing output so another contributor can reproduce the
same result. You can also dispute an expected value or a claim made for a
passing result. For example, comparing prepared JSON records does not measure
how a model responds to a hostile web page; an explanation that confuses those
two experiments needs correcting even if every Python assertion passes.

## Development setup

Clone the repository, run the prepared examples, then install the development
tools. These commands use a macOS or Linux shell (or WSL):

```bash
git clone https://github.com/wcook04/plectis && cd plectis
./bootstrap.sh
VENV=/tmp/plectis-dev-venv make install
```

`./bootstrap.sh` runs the supplied examples in
`fixtures/first_wave/pattern_binding_contract/input` and scans for forbidden
secret strings. It writes the status in
`.microcosm/cold_clone_probe.json`, which is ignored by git. Use
`./bootstrap.sh --dry-run` to preview the command first.

`make install` installs Plectis and its test dependencies (pytest, requests,
NumPy and pandas) in a virtual environment. `VENV` selects the directory used
in the examples below. Without that setting, the Makefile chooses a temporary
directory from the checkout path. You do not need pytest installed beforehand.

## Tests and validation

```bash
make check      # reject registry errors and prohibited Lean source syntax
make test       # public entry and safety tests
make ci         # check, test, smoke, package-smoke
make validate   # ci plus comparison of generated doctrine tables with source data
```

`make check` rejects missing or unknown component/evidence-class IDs and
prohibited syntax in shipped Lean source. `make test` runs the test files listed
in `Makefile`; `make ci` also runs example commands and installs the package in
a fresh environment before invoking it. Start with the test file for the code
you changed, for example:

```bash
PYTHONPATH=src /tmp/plectis-dev-venv/bin/python -m pytest tests/test_public_entry_docs.py --basetemp=/tmp/plectis-bt
```

Two rules the Makefile enforces that direct pytest runs must respect:

- **One temporary test directory per process.** If you run separate pytest
  commands at the same time, give each a different `--basetemp` directory;
  otherwise one process can delete or replace another's test inputs.
- **Tracked receipts are read-only under pytest.** Generated output that needs
  to change must be regenerated by the program named in that result's contract.
  Use `MICROCOSM_TRACKED_RECEIPT_WRITES=1` only when you intentionally refresh
  committed result files. Do not edit a result by hand to make a test pass.

The commands for running all smoke examples, comparing generated files with
source data (`make test-all`), collecting a reviewer packet, producing a
standalone export and running that export's tests are documented in
[docs/maintainers/validation.md](docs/maintainers/validation.md).

## Generated files

`ORGANS.md`, `ARCHITECTURE.md`, `AGENT_ROUTES.md`, `FIRST_ACTION.md`,
`RELEASE_REVIEW.md`, and generated atlas/registry JSON records are produced by
the repository's build scripts. Change the source data and regenerate them
(for the atlas:
`PYTHONPATH=src python3 scripts/build_organ_atlas.py --write`). Tests compare
committed files with freshly generated files and fail if they differ.

## Documentation changes

Use the [documentation index](docs/README.md) to choose where a new page belongs.
State what the reader will learn or run, link the page from the relevant guide,
and include the next document or command. Define unfamiliar project terms
where a reader first needs them; [the short terminology guide](docs/UNDERSTANDING_PLECTIS.md#the-terms-used-in-the-repository)
is there for reference.

Run new commands from a clone without an activated development environment.
Open relative links and section anchors. Describe the actual input, operation
and output: for example, say which JSON fields are compared and what causes
`blocked`, rather than just saying a program "checks the policy". Keep the
author's meaning and qualifications, and verify changed claims against the
source code and recorded results. The existing first-contact tests include:

```bash
PYTHONPATH=src /tmp/plectis-dev-venv/bin/python -m pytest tests/test_documented_first_contact_commands.py tests/test_public_entry_docs.py
```

## Pull requests

Use `.github/PULL_REQUEST_TEMPLATE.md` to record the files changed, tests run
and claims made. Run `make ci`, or explain why the particular tests you ran are
sufficient for the change. A completed template does not authorise publication.

## Hard boundaries

Do not contribute secrets, credentials, saved sessions, private messages or
request/response bodies from model providers, unedited operator writing,
recordings or transcripts, private personal material, live account data, details of live
external targets, hidden evaluation rubrics, or unsafe exploit steps.

Do not treat a passing result as permission to change a user's source files,
call a model provider, publish a site or send a message. Do not cite that result
as proof of product readiness, proof correctness or production security, or as
a basis for financial advice. A test input may contain these permissions
only to demonstrate that the program rejects them. Exported result files keep
`release_authorized=false` until the operator separately authorises publication.
