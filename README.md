# Plectis

**Plectis is an experiment in doing research with AI while keeping the work
understandable, checkable and possible for someone else to continue.** This
repository is its public Python toolkit: programs and worked examples for
checking proposed proofs, testing records of agent actions, comparing forecasts,
keeping generated documents consistent with their sources, and preserving
work between sessions.

The tools come from a larger research workbench built by Will Cook with AI
coding agents. You can run the public examples independently, study how they
work and adapt useful parts. The mathematical papers and proofs live in the
separate [Plectis Erdős repository](https://github.com/wcook04/plectis-erdos).

[About the project](https://wcook04.github.io/plectis/docs/introduction.html) ·
[Worked examples](#see-it-work) · [Quickstart](QUICKSTART.md) ·
[Documentation](docs/README.md) · [Contributing](CONTRIBUTING.md)

For a first look in a terminal, run the repository tour. Two commands, no
install, Python 3.11 or newer:

```bash
git clone https://github.com/wcook04/plectis && cd plectis
PYTHONPATH=src python3 -m plectis tour --format text .
```

This lists project files, suggests a starting task and saves a local run record.
It makes no model calls and leaves your source unchanged. The examples below
show what the individual tools do; the tour itself does not run your tests or
carry out the suggested task.

## Why this exists

AI-assisted research can span many sessions, files and failed approaches.
Plectis explores how to preserve that work so another person can understand
what was tried, check the results and choose a useful next step. Experts can
contribute a correction or direction without operating the AI themselves.

This toolkit publishes selected parts of that effort. The
[mathematics repository](https://github.com/wcook04/plectis-erdos) holds the
papers, proofs and open questions; the [website](https://wcook04.github.io/plectis/)
explains both. The larger private workbench shown in the videos is separate
from this clone. The [project overview](docs/overview.md) explains how the
parts fit together and relates them to other research tools.

<a id="choose-a-route"></a>

## Choose a starting point

| You want to… | Start here |
|---|---|
| Understand the project | [Why these tools belong together](docs/overview.md) |
| Run something locally | [Quickstart](QUICKSTART.md) |
| Follow a complete example | [Worked guides](docs/guides/README.md) |
| Find a tool in your field | [Component map](ORGANS.md) |
| Work on the code | [Contributing](CONTRIBUTING.md) and [implementation map](docs/maintainers/architecture.md#implementation-map) |
| Read the mathematics | [Companion reader's guide](https://github.com/wcook04/plectis-erdos/blob/main/docs/READING_GUIDE.md) |

## See it work

An AI says: “I committed the fix and the tests passed.” The
[completion-checking guide](docs/guides/checking-agent-completion.md) shows how
one component checks those claims using a sample Git repository and actual
pytest runs. It verifies three supplied claims and rejects four deliberately
incorrect ones. You can follow the result back to the code that checked it.

Two more [worked guides](docs/guides/README.md) show different uses:

- [Change a prompt-injection example](docs/guides/prompt-injection.md)
  and see a checker reject an inconsistent permission in saved records.
- [Prepare a research question](docs/guides/hypothesis-handoffs.md) with a
  tentative answer, alternatives and proposed observations for an expert.

Try the second example from the clone, without installing anything:

```bash
PYTHONPATH=src python3 -m plectis hypothesis-handoff \
  --input examples/hypothesis_handoff/independent_evaluation.json --format text
```

It validates the supplied file and prints the question and proposed
investigation. It does not answer the question, contact an expert or call a
model. Each guide explains what its example tests and what remains untested.

## What is in the toolkit?

There are **88 components**, grouped into seven areas. A component is a named
program or group of related programs, with its own instructions and stated
limits. Some run a computation or an external tool; others compare supplied
records against rules. An entry in the catalogue is not a promise that every
example can run in every environment: its page lists required tools and source
files, and the runner reports unavailable requirements.

| If you are interested in… | Open this area | Example |
|---|---|---|
| Getting oriented in an unfamiliar project | [Getting started](ORGANS.md#entry--reveal) | Check that a suggested first step names an available command, document and result file. |
| Finding the right files and tools | [Maps and navigation](ORGANS.md#architecture--navigation) | Compare selected files and components with an expected selection. |
| Working with formal proofs | [Mathematics and proof tools](ORGANS.md#formal-math--proof) | Try proof steps on small supplied theorems and ask Lean whether they are accepted. |
| Checking agent behaviour | [Agent reliability and safety](ORGANS.md#agent-reliability--safety-replays) | Test records involving prompt injection, poisoned memory or unsupported completion claims. |
| Evaluating research methods | [Research and forecasting](ORGANS.md#research--science-replays) | Compare forecast errors on synthetic data using statistical resampling. |
| Keeping generated documents consistent with their sources | [Source and generated-file checks](ORGANS.md#import-projection--drift) | Compare file fingerprints and check that declared outputs exist. |
| Resuming and coordinating work | [Work and continuity](ORGANS.md#work-landing--continuity) | Check that a completed-work record names the changes, validation results and commits. |

You can [browse the components on the website](https://wcook04.github.io/plectis/docs/components.html)
or list and search their descriptions from the terminal:

```bash
PYTHONPATH=src python3 -m plectis comprehend --slice mechanism --format text
PYTHONPATH=src python3 -m plectis comprehend --first-action "prompt injection" --format text
```

The search uses phrase and word matching to suggest a command and relevant files.
It neither calls an AI model nor executes the suggested command.

## How it works

Most components run independently. They share command handling, file formats
and a catalogue that names each component's code, inputs, checks and saved
results. The catalogue also supplies the generated documentation and maps.
The connections between components are recorded where they exist; the seven
areas are a browsing aid, not seven stages that every run executes.

To understand a component, open its example input, the source function that
processes it and the output it produces. Compare that output with the test or
expected result. Then change an input in a disposable copy and check whether
the result changes as expected. The [worked guide](docs/guides/prompt-injection.md)
follows this path through one component.

The project tour is a separate orientation command. It mostly classifies
filenames and paths, with limited inspection of Python entry points. It
writes a file inventory, suggested tasks and a simulated task record under
`.microcosm/`, an ignored directory retained from the project's former name.
A saved run result is called a *receipt* in the source. It records what ran and
which inputs and results it refers to; it does not by itself prove a claim.
To see the tour's structured output:

```bash
PYTHONPATH=src python3 -m plectis tour --card .
```

[Architecture](ARCHITECTURE.md) maps the implementation. The
[maintainer guides](docs/maintainers/README.md) explain command dispatch,
data ownership and how to regenerate the maps.

## Explore with a coding agent

A coding agent is an AI assistant that can read files, run commands and edit
code. You can use your own to explore this repository. Open a current clone
and ask, for example:

> Read AGENTS.override.md. I want to understand how this project checks an
> agent's claim that a task is finished. Find the relevant example, explain
> its inputs, run it, and show me the result and the code that checks it.
> Explain what this run establishes and what it leaves untested. Include the
> checkout commit and commands so I can repeat it.

The [agent quickstart](QUICKSTART.md#use-your-own-coding-agent) explains where
to save results. [AGENTS.md](AGENTS.md) contains the editing instructions.
The toolkit's local examples do not require a model API key; your chosen
coding agent has its own account and provider requirements.

## Install

The basic commands run from a clone with **Python 3.11 or newer**, without
third-party runtime dependencies. The shell examples above work on macOS,
Linux and WSL. In Windows PowerShell, first set `$env:PYTHONPATH = 'src'`,
then use `python -m plectis` in place of `PYTHONPATH=src python3 -m plectis`.
Individual examples may require Git, pytest, Lean or other tools; follow the
selected example's instructions.

To install the shorter `plectis` command on macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/plectis tour --format text .
```

Use the virtual environment if your system Python reports
[`externally-managed-environment`](https://peps.python.org/pep-0668/).
For development dependencies, Windows
installation commands and other options, see [Quickstart](QUICKSTART.md),
[Contributing](CONTRIBUTING.md) and [troubleshooting](docs/README.md#troubleshooting).
The older `microcosm` command remains an alias.

## Repository layout

Start with the guides and examples. The large reference files are indexes for
looking things up; you do not need to read them all before trying a component.

| Location | What belongs here |
|---|---|
| [Documentation](docs/README.md), [quickstart](QUICKSTART.md) | Explanations, worked guides and setup instructions. |
| `src/plectis/`, `src/microcosm_core/` | Public command entry points and Python implementation. The older import name is retained for compatibility. |
| `src/microcosm_core/organs/` | Individual component implementations; “organ” is the older name for a component. |
| [Examples](examples/README.md), [fixtures](fixtures/README.md), `tests/` | Example inputs, prepared test cases and executable checks. |
| `core/` | Machine-readable component lists and configuration. |
| `atlas/`, `ORGANS.md`, `ARCHITECTURE.md`, `AGENT_ROUTES.md` | Generated reference maps built from the component records. |
| `standards/`, `skills/`, `paper_modules/` | Detailed requirements, procedures and component explanations. |
| [Paper source](paper/README.md), [paper collection](docs/papers/README.md) | The toolkit paper's source and a guide to the wider paper collection. |
| [Recorded results](receipts/README.md) | Recorded example results shipped with this version. Your own runs belong in `.microcosm/`. |
| `scripts/`, `Makefile`, `.github/workflows/` | Documentation builders, local checks and continuous integration. |

The [documentation index](docs/README.md) separates human guides, reference
maps and maintainer instructions. Open a directory’s README for its starting points. The [terminology guide](docs/reference/terminology.md)
translates older names you may encounter in source files.

<a id="how-the-result-stays-honest"></a>

## What a passing result means

A pass is about a particular input and check. The component records classify
the result: a computation run now, a replay of supplied data, or a comparison
of files. That is why the source, test and stated limits are published together.

<details>
<summary>Limits by kind of example</summary>

- **Formal proof:** Lean can check the supplied formal statement and proof.
  A successful toolkit example does not prove an unrelated theorem.
- **Agent safety:** a replay does not establish that a deployed agent is safe.
  Its prepared cases cover specific checks, not every possible attack.
- **Research and forecasting:** synthetic examples do not establish scientific
  expertise, investment returns or a forecasting track record. This is not
  professional advice or investment advice.
- **Generated files:** a match establishes agreement for the specified files.
  You do not gain permission to publish private material by comparing them.
- **Recording and resuming work:** you do not gain permission to edit someone
  else's source files or publish a release by recording a task as complete.

</details>

This is a research prototype containing selected public source files and
examples. It does not
contain enough code or data to reconstruct the private system. It is not a
hosted service or a production security product, and has no model-provider
affiliation or endorsement. Public examples do not establish the reliability
of the unseen private workbench.

## Develop and contribute

A useful contribution can be small: an input that exposes a mistaken check,
a clearer explanation, an easier first command or an improvement to one tool.
[Contributing](CONTRIBUTING.md) explains how to report a reproducible mismatch,
try an entry-route experiment or propose an infrastructure change. Mathematical
contributions belong in the [companion repository](https://github.com/wcook04/plectis-erdos/blob/main/CONTRIBUTING.md).

From the clone root:

```bash
make check   # fast registry and Lean-source checks; no installation
make ci      # tests, command smoke tests and a fresh package installation
```

`make ci` creates temporary environments and installs build and test
dependencies, so it may need network access. `make help` lists narrower checks.
The [validation guide](docs/maintainers/validation.md) explains how to reproduce
release records and check generated files. Edit their source and run the owning
builder rather than changing generated maps or recorded results by hand.
The [release review](RELEASE_REVIEW.md) records the candidate’s checks;
[source status](SOURCE_STATUS.md) explains which source material is included.

## Name and history

**How this was built.** William Cook sets the direction and is responsible for
the public claims; AI coding agents write and maintain most of the code.
[PROVENANCE.md](PROVENANCE.md) records authorship and third-party sources.

The project was called Microcosm until 21 June 2026. It became Plectis to avoid
confusion with Southampton's earlier Microcosm hypermedia system, without
implying endorsement or affiliation. Old names remain in package imports,
output paths and historical records so existing tools keep working.

For private security reports, see [SECURITY.md](SECURITY.md). To cite the
software, use [CITATION.cff](CITATION.cff). Copyright 2026 William Cook;
licensed under Apache 2.0, with details in [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Mathematics companion snapshot

The companion's [current results guide](https://github.com/wcook04/plectis-erdos/blob/main/docs/RESULTS.md)
owns its mathematical claims. This toolkit's recorded source and release links
are preserved in the [companion reference](docs/reference/lean-companion.md).
