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

Suppose an AI assistant helps with a research question over several weeks.
It tries an approach, writes some code, finds a mistake and starts again.
Another session then needs to know which files matter, what was actually
checked, why the earlier approach failed and what is worth trying next.
Someone reviewing the result needs those answers too.

AI assistants propose approaches and write code or candidate proofs. The tools
here check specific parts of that work and preserve the results. People still
have to interpret those results and decide what is worth pursuing.

Plectis explores how to make that work accumulate. The aim is to tackle harder
questions as AI improves, while leaving explanations, checked results and
unfinished work that people can understand and continue. Human experts should
be able to suggest a direction or correct an argument without having to run
the AI themselves. They might identify a missing assumption, point to earlier
work or suggest a better question. The
[one-page introduction](https://wcook04.github.io/plectis/docs/introduction.html)
explains that aim and the collaboration it is intended to support.

That is why apparently different tools appear in one repository:

- **Find a useful next step.** Maps connect a task to relevant files and commands.
- **Investigate it.** Proof tools, calculations and research examples perform
  particular pieces of work.
- **Check what happened.** Tests and other programs compare results with
  explicit requirements, including cases that should fail.
- **Keep and explain the work.** Saved results, source references and work
  records help the next reader see what was tried and what remains unfinished.
- **Learn from a mistake.** A recurring failure can become a test or a rule in
  the software, so the next run can catch it.

This describes the design the tools explore. The public collection is a
research prototype: its examples exercise individual parts of that process,
and many use prepared data. It does not run an entire research programme for you.

## How the project fits together

| Part | What you will find |
|---|---|
| **This repository: `plectis`** | Software, example inputs, tests and recorded results. Use it to understand a mechanism, rerun an example or adapt a tool. |
| **[Mathematics: `plectis-erdos`](https://github.com/wcook04/plectis-erdos)** | Research on eight Erdős problems: papers, proofs, computations, failed approaches and open questions. Lean, a proof assistant, checks that proofs establish the formal statements written in the source. |
| **[Website](https://wcook04.github.io/plectis/)** | Readable introductions, mathematical problem pages, papers, component pages and maps linking to their sources. |
| **[Private workbench shown in the videos](https://wcook04.github.io/plectis/#demo-videos)** | The larger environment where the work developed, including interfaces for exploring code and agent activity. Those recordings are demonstrations; this clone does not install that environment. |

The mathematics gives a concrete reason to preserve more than a final answer.
A partial result can be useful even when the original problem remains open;
an explanation of a failed approach can save the next researcher from repeating
it. The companion keeps the argument, assumptions, checks and remaining question
together. Start with its [reader's guide](https://github.com/wcook04/plectis-erdos/blob/main/docs/READING_GUIDE.md)
or [results and limits](https://github.com/wcook04/plectis-erdos/blob/main/docs/RESULTS.md).

You do not need the mathematics repository or access to the private workbench
to use this toolkit. Running an example here does not verify the companion's
mathematical results; those have their own reproduction instructions.

## See it work

### Did the agent actually finish the change?

An agent reports: “I committed the fix and the tests passed.” There are two
separate things to check: does that commit exist, and did the named tests
actually finish successfully?

The [completion-checking example](docs/guides/checking-agent-completion.md)
uses a sample repository and real Git and pytest processes. It compares
completion claims with the resulting evidence, including cases where a claimed
commit is missing or a test run is incorrectly described as passing. The guide
shows how to run it, inspect the result and follow the check into the code.
It checks those specific claims in the sample; it does not judge the quality
of every change an agent might make.

### Can untrusted text acquire permission to give instructions?

Suppose an agent reads a web page that asks it to send private information
elsewhere. The [prompt-injection walkthrough](docs/UNDERSTANDING_PLECTIS.md#one-example-you-can-follow)
represents the page and the proposed action as saved records. You run the
checker, change one field to give that page permission to issue instructions,
and see the altered example rejected.

This example checks consistency of supplied records. It does not ask a live
model to read a hostile page. That distinction is visible in the inputs and
in the program, so you can judge what the result actually demonstrates.

### What would make a research question useful to an expert?

The [hypothesis example](docs/guides/hypothesis-handoffs.md) records an open
question, a tentative answer, alternatives and observations that could
distinguish them. Here the question is whether independently chosen test cases
would reveal different failures from the author's own examples.

Run it from the clone, with no installation or model account:

```bash
PYTHONPATH=src python3 -m plectis hypothesis-handoff \
  --input examples/hypothesis_handoff/independent_evaluation.json --format text
```

The command checks the structure and references in that file, then prints the
question and proposed investigation. It does not answer the question or contact
an expert. It provides a concrete starting point for a discussion.

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
the result changes as expected. The [worked guide](docs/UNDERSTANDING_PLECTIS.md)
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
[maintenance guide](docs/maintainers/architecture.md) explains command dispatch,
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
| `docs/`, `QUICKSTART.md` | Explanations, worked guides and setup instructions. |
| `src/plectis/`, `src/microcosm_core/` | Public command entry points and Python implementation. The older import name is retained for compatibility. |
| `src/microcosm_core/organs/` | Individual component implementations; “organ” is the older name for a component. |
| `examples/`, `fixtures/`, `tests/` | Example inputs, prepared test cases and executable checks. |
| `core/` | Machine-readable component lists and configuration. |
| `atlas/`, `ORGANS.md`, `ARCHITECTURE.md`, `AGENT_ROUTES.md` | Generated reference maps built from the component records. |
| `standards/`, `skills/`, `paper_modules/` | Detailed requirements, procedures and component explanations. |
| `paper/`, `docs/papers/` | The toolkit paper's source and a guide to the wider paper collection. |
| `receipts/` | Recorded example results shipped with this version. Your own runs belong in `.microcosm/`. |
| `scripts/`, `Makefile`, `.github/workflows/` | Documentation builders, local checks and continuous integration. |

The [documentation index](docs/README.md) separates human guides, reference
maps and maintainer instructions. The [terminology guide](docs/UNDERSTANDING_PLECTIS.md#the-terms-used-in-the-repository)
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

This repository contains selected public source files and examples. It does not
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

## Choose a route

| You want to… | Start here |
|---|---|
| Understand the wider project | [One-page introduction](https://wcook04.github.io/plectis/docs/introduction.html) |
| Run and change a complete example | [Understanding Plectis](docs/UNDERSTANDING_PLECTIS.md) |
| Find a particular tool | [Component map](ORGANS.md) or [website browser](https://wcook04.github.io/plectis/docs/components.html) |
| Understand the mathematics | [Companion reader's guide](https://github.com/wcook04/plectis-erdos/blob/main/docs/READING_GUIDE.md) |
| Review this software release | [Release review](RELEASE_REVIEW.md) and [Source status](SOURCE_STATUS.md) |
| Find detailed instructions | [Documentation index](docs/README.md) |

## Related ideas

There are useful precedents for parts of this approach. These projects help
place the toolkit without requiring you to learn Plectis's terminology:

- **[Inspect AI](https://inspect.aisi.org.uk/):** separates the task an AI
  performs from the procedure that scores it, and records evaluation runs.
  That is useful context for the agent-checking examples here.
- **[LeanDojo](https://github.com/lean-dojo/LeanDojo):** provides tools and data
  for interacting with Lean in theorem-proving research. It illustrates the
  distinction between proof tooling, a research model and mathematical results.
- **[Sacred](https://github.com/IDSIA/sacred):** records an experiment's
  configuration, execution and results so researchers can revisit a run.
- **[DVC](https://doc.dvc.org/user-guide/project-structure/dvcyaml-files):**
  describes computations through their commands, dependencies and outputs.
  That is a useful comparison for explicit file relationships and rerun checks.

These are comparisons, not dependencies or integrations. Plectis brings
examples of several such concerns into one public collection. The
[toolkit paper](plectis-public-system.pdf) discusses what publishing selected
tools and tests lets another person examine; the [paper guide](docs/papers/README.md)
connects it to the mathematics and research-process papers.

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
is the starting point for its mathematical claims. The historical reference
below is retained so this toolkit's recorded links remain reproducible.

<!-- The two snapshot/release bullets are maintained by scripts/check_lean_companion_snapshot.py. -->
<details>
<summary>Recorded companion snapshot and source references</summary>

## Companion project: eight open Erdős problems in Lean 4

The **Formal Math & Proof** area above includes examples drawn from a
separate repository containing the Lean proof source and mathematical papers:

[**plectis-erdos**](https://github.com/wcook04/plectis-erdos)
contains Lean 4 work on Erdős Problems **#68, #243, #249, #251, #257, #269,
#1041, and #1049**. For ani's explicit degree-seven polynomial, Lean proves
that every path through its strict lemniscate joining two distinct roots has
image of one-dimensional Hausdorff measure greater than two. This refutes the
[Formal Conjectures path-image formulation of #1041](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos1041/Counterexample/HausdorffLength.lean#L393),
as well as the earlier total-variation statement. Independent human review of
its correspondence with the 1958 curve-length wording has not been recorded.
The other seven target problems are not resolved there.
Its README gives each problem's statement, results and remaining questions.
Lean verifies the proofs
against their formal statements; the claim records and papers explain how
those statements relate to the original problems. Running a software example
here does not rerun the companion repository's Lean proofs.

For the Lean example files in this software repository, `make check` rejects proof placeholders, project-defined axioms, native
evaluation, unsafe/partial declarations, and unbounded kernel limits before
the broader test suite runs.

- [**Read the proven partial results, problem by problem**](https://github.com/wcook04/plectis-erdos/blob/main/docs/RESULTS.md):
  one entry per problem, with links to the Lean declarations, an explanation
  of what each result proves, and its limits or remaining questions.
- [**Choose a problem paper**](https://github.com/wcook04/plectis-erdos#problem-papers):
  the companion README lists one short paper for each covered problem and
  states the partial results beside it.
- [**Read the systems paper**](https://wcook04.github.io/plectis/papers/claim-faithful-publication-systems-paper.pdf):
  how the authors compare the claims in the papers with the statements
  proved in Lean, and record which source version they used.
- [**Browse the Lean source**](https://github.com/wcook04/plectis-erdos/tree/a08529a329578d172a9a2e602bacba4a8cc760cd):
  the recorded public source snapshot contains 1,816 Lean modules and 159,482
  theorem-like declarations, checked by the pinned kernel; start from
  `docs/ORIENTATION.md`. These counts include library declarations; they do
  not count solutions to Erdős problems. For this source snapshot, cite
  commit `a08529a329578d172a9a2e602bacba4a8cc760cd` and the relevant paper. `v0.10.0` is the
  latest tagged release.
- [**Release v0.10.0**](https://github.com/wcook04/plectis-erdos/releases/tag/v0.10.0):
  the version to cite when referring to that release.

</details>
