# Plectis

[Website](https://wcook04.github.io/plectis/) ·
[Quickstart](QUICKSTART.md) ·
[Human guides](docs/README.md#human-guides) ·
[Contributing](CONTRIBUTING.md)

**Plectis is a public Python toolkit developed as part of the research and
engineering system I built with AI coding agents.** There are programs for
running Lean on proposed proofs, rejecting inconsistent records of agent
actions, comparing forecasts,
comparing generated files with their source, and recording unfinished work.
You can run the examples, read the code and change the inputs to test what
happens.

Start with a tour of this repository. It lists project files, identifies files
such as the README and Python package configuration, and suggests a task
such as reading the README. It saves the file list and a record of its own
run locally. The tour
makes no network or model calls and does not edit your source files or run
your project's tests.

Two commands, no install, any Python 3.11 or newer:

```bash
git clone https://github.com/wcook04/plectis && cd plectis
PYTHONPATH=src python3 -m plectis tour --format text .
```

This runs the project tour. To try a particular component, choose its example
from the [component list](ORGANS.md). Some examples run external programs such
as git, pytest or Lean; their instructions list the requirements.

Installing is optional and covered under [Install](#install). Wherever this
page abbreviates a command to `plectis`, you can use
`PYTHONPATH=src python3 -m plectis` from the clone instead. The examples use a
macOS or Linux shell; in Windows PowerShell, set `$env:PYTHONPATH = 'src'`
first, then use `python -m plectis`.

**How this was built, and why it is built the way it is.** One person sets the
direction; large-language-model agents write and maintain most of the code.
William Cook selects the public claims and is responsible for them. Each
component includes source code, runnable examples and files recording the
results, so that another developer can inspect how a result was obtained.

This is an *AI-native* repository: it includes instructions, task maps and
JSON records designed for coding agents to use when working on the code.
This README, the [human guides](docs/README.md#human-guides) and the
[website](https://wcook04.github.io/plectis/) explain the work for readers.
For exploring the code, I recommend [cloning the repository and using a
coding agent](#explore-with-a-coding-agent).

For the argument behind the toolkit, read [the Plectis paper](plectis-public-system.pdf).
The [paper guide](docs/papers/README.md) introduces the other papers, with PDFs
and searchable text available in the clone.

The [mathematics companion](https://github.com/wcook04/plectis-erdos) contains
papers and Lean proofs around eight open Erdős problems. A maths task needs
only that repository; a software task needs only this one.
[Recorded walkthroughs](https://wcook04.github.io/plectis/#demo-videos)
show the private interface; they do not establish its reliability.

## Where to start

- **Read an explanation without installing anything:** the
  [website tour](https://wcook04.github.io/plectis/docs/tour.html).
- **Follow one example through the code:**
  [Understanding Plectis](docs/UNDERSTANDING_PLECTIS.md). It explains how a
  program detects an inconsistent trust label in supplied example data.
- **Study agent failures:**
  [agent reliability and safety replays](ORGANS.md#agent-reliability--safety-replays).
  These include examples of prompt injection and poisoned memory. The examples
  use supplied data; passing them does not establish that a live agent is safe.
- **Read the mathematics:** the
  [Lean companion](https://github.com/wcook04/plectis-erdos), with its own
  problem papers and reading guide.
- **Find a command, paper or source file:** the [documentation index](docs/README.md)
  or the [links below](#choose-a-route).

## Explore with a coding agent

Clone the repository, open the folder in a coding agent with access to local
files and a terminal, and give it a question. For example:

> Read AGENTS.override.md and follow its instructions. Explain how Plectis
> relates to [my topic]. Run one relevant example, show me the input and
> output files, and explain what the program computed or compared.

[AGENTS.override.md](AGENTS.override.md) and [AGENTS.md](AGENTS.md) contain
instructions for the agent. Task maps list commands and relevant files;
JSON records contain inputs, configuration and saved results. You can read
the explanations and source directly, or ask an agent to locate and explain
particular files.

For the website, *digestion* means turning source material into explanations,
examples and diagrams for a particular reader or question. People can do
this work themselves; here, AI agents draft the explanations. For mathematics,
this is *AI pre-digestion*: preparing material for a reader. The reader still
needs to reconstruct the argument, examine its assumptions and difficult
steps, and understand how to use the result. Build scripts assemble component
pages and source links from the repository's records. The aim is to repeat
this process when the source changes. The website provides explanations and
navigation for readers; the repository also provides structured records and
commands for agents. Both include links to the source files and recorded
results.

## What you get

The public executable code includes **88 components grouped into seven areas**.
A component is one program or group of related programs listed in
[ORGANS.md](ORGANS.md). Some run a computation or an external tool; others
compare supplied records against explicit rules. The component pages state
which kind of example you are running.

You can also search the component descriptions:

```bash
PYTHONPATH=src python3 -m plectis comprehend --first-action "prompt injection" --format text
```

This matches your words against the supplied component names and task
descriptions, using phrase and word matching. It prints a suggested command,
source references and the stated limits of the example. It does not execute
the suggested command or verify a claim you type into the search.

For a research question with several possible answers, the
[hypothesis handoff example](HYPOTHESIS_HANDOFF.md) records a leading hypothesis,
alternatives, observations that would distinguish them, and proposed tests.
The following command validates the supplied JSON example:

```sh
PYTHONPATH=src python3 -m plectis hypothesis-handoff --input examples/hypothesis_handoff/independent_evaluation.json --format text
```

It does not determine whether the leading hypothesis is true. The example
keeps the proposed answer separate from the observations and tests needed to
accept it.

## See it work

The tour prints a summary like this; the count and selected route depend on
the project. Here, a *route* means a suggested task and the files relevant to it.

```text
Plectis read 5102 project files and wrote a local record.  repo -> .microcosm

  Route taken     readme_onboarding_route  (one of 5 it found)
  Record written  .microcosm/  (21 local files, written beside your project)
  Your source     unchanged

  Every finding in that record carries three handles:
    Evidence   .microcosm/evidence/   (what backs the finding)
    Source     .microcosm/events.jsonl   (where the finding came from)
    Scope      does not authorize release, provider calls, whole-system correctness
```

The output uses the older name `.microcosm` for the directory it writes.
`catalog.json` in that directory lists the files found. `evidence/routes.json`
records the suggested tasks and file references. `events.jsonl` records the
program's operations. A *receipt* is a JSON file recording a command, its result and
references to the files used to obtain that result.

“Read” in this summary does not mean that the program analysed every file's
contents. It mostly classifies paths and filenames. For Python projects it
also reads package entry points from `pyproject.toml` and the first 4,096
characters of each Python file to count import lines and identify script
entry points. The tour records a simulated task run; it does not execute the
project's application or tests.

To print the same result as JSON:

```bash
PYTHONPATH=src python3 -m plectis tour --card .
```

## Install

You can run the toolkit directly from a clone with Python 3.11 or newer and
no third-party runtime dependencies:

```bash
PYTHONPATH=src python3 -m plectis tour --format text .
```

Installing gives you the shorter `plectis` command name. On macOS or Linux,
create a virtual environment and activate it in the shell where you will work:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/plectis tour --format text .
source .venv/bin/activate
```

If your system Python refuses installation with
`error: externally-managed-environment`, use the virtual environment above.
This is a restriction on installing packages into a Python installation
managed by the operating system ([PEP 668](https://peps.python.org/pep-0668/)).
Running from source needs no installation.

For the test dependencies and development setup, see
[Contributing](CONTRIBUTING.md). The legacy `microcosm` command remains
available as an alias for older scripts.

## How it works

The project-reading code creates a file inventory, identifies source,
documentation and test directories, and selects from predefined tasks.
If it finds a README, it suggests reading that file first.
Other modules record task steps, command results and references to input and
output files. These modules are reused by the components.

To inspect a component, open its example input, the function that processes
it, and the resulting file. Then read the test or comparison used to accept
that result. A result from supplied example data establishes only what the
program did with those inputs. Running an external tool, such as Lean, is
identified separately in the component's instructions and output.

[Architecture](ARCHITECTURE.md) lists the implementation modules and their
relationships. The website has an
[interactive diagram](https://wcook04.github.io/plectis/docs/architecture.html#whole-system-map).

## Browse the component map

The names below match the headings in [ORGANS.md](ORGANS.md). Each description
gives one concrete example from that group; it is not a description of every
component in the group.

| Group | Components | Example |
|---|---:|---|
| [Entry & Reveal](ORGANS.md#entry--reveal) | 2 | Require each proposed first step to name a command, a public document and a result file, then verify those references against the public files. |
| [Architecture & Navigation](ORGANS.md#architecture--navigation) | 12 | Compare selected file and component IDs against expected IDs, and report missing or unwanted selections. |
| [Formal Math & Proof](ORGANS.md#formal-math--proof) | 20 | Generate tactic scripts for supplied small theorems and run Lean to accept or reject them. Report when Lean is unavailable. |
| [Agent Reliability & Safety Replays](ORGANS.md#agent-reliability--safety-replays) | 20 | Reject supplied records that give untrusted web text permission to issue instructions. |
| [Research & Science Replays](ORGANS.md#research--science-replays) | 9 | Compare synthetic forecast-error tables using statistical resampling. Include a simulated case where the statistics package is unavailable. |
| [Import, Projection & Drift](ORGANS.md#import-projection--drift) | 20 | Compare hashes of source and generated files, and require each declared output file to exist. |
| [Work, Landing & Continuity](ORGANS.md#work-landing--continuity) | 5 | Reject a record of completed work if it omits the changed paths, references to validation results or before-and-after commit IDs. This example does not execute Git. |

You can also use the
[component browser](https://wcook04.github.io/plectis/docs/components.html)
to read the commands and source references without cloning.

## Choose a route

| You want to | Open |
|---|---|
| Run the first example | [Quickstart](QUICKSTART.md) |
| Follow one example's input, code and output | [Understanding Plectis](docs/UNDERSTANDING_PLECTIS.md) |
| Find implementation modules | [Architecture](ARCHITECTURE.md) |
| Browse all 88 components | [System map](ORGANS.md) or the [website browser](https://wcook04.github.io/plectis/docs/components.html) |
| Choose a paper | [Paper guide](docs/papers/README.md) or the [paper browser](https://wcook04.github.io/plectis/docs/papers.html) |
| Inspect the stated software claims and their recorded results | [Release review](RELEASE_REVIEW.md) and [Source status](SOURCE_STATUS.md) |
| Read the Lean proofs and mathematical papers | [Companion repository](https://github.com/wcook04/plectis-erdos) |
| Watch recorded use of the private interface | [Demo videos](https://wcook04.github.io/plectis/#demo-videos) |
| Give a reviewer or model the public documentation | [Reader digest](https://wcook04.github.io/plectis/plectis-ai-reader-digest.json), then the [full review packet](https://wcook04.github.io/plectis/plectis-ai-review-packet.json) for source and result records |
| Find the related software, mathematics and films | [wcook04.github.io](https://wcook04.github.io/) |
| Work on Plectis with a coding agent | [AGENTS.md](AGENTS.md) |
| Report an error or contribute | [Contributing](CONTRIBUTING.md) and [Security](SECURITY.md) |

To list component descriptions or search for a command from the terminal:

```bash
PYTHONPATH=src python3 -m plectis comprehend --slice mechanism --format text
PYTHONPATH=src python3 -m plectis comprehend --first-action "prompt injection" --format text
```

## Scope and limitations

Plectis is a research prototype and developer tool. The public repository
contains selected source files and runnable examples from the larger private
system. It does not contain enough code or data to reconstruct that system.

- **Formal proof:** an example that runs Lean can establish that Lean accepted
  the supplied statement and proof. A recorded result or successful example
  does not prove an unrelated theorem.
- **Agent safety:** replaying supplied failure cases does not establish that a
  deployed agent is safe or that it will resist other attacks.
- **Research and forecasting:** examples using synthetic data do not establish
  scientific expertise, investment returns or a forecasting track record. This
  is not professional advice or investment advice.
- **Generated files:** a successful comparison establishes that the specified
  files match. You do not gain permission to publish private material by
  comparing files.
- **Recording and resuming work:** you do not gain permission to edit someone
  else's source files or publish a release by recording a task as complete.
  The tour leaves
  the project's source files unchanged.

Plectis is not a hosted service or a production security product. It is an
independent project, with no model-provider affiliation or endorsement.

<a id="how-the-result-stays-honest"></a>

## Inspect the recorded results

[ORGANS.md](ORGANS.md) is generated from the component records in this
repository. Each card links to the example command, source files and output
files. The records also classify the result: for example, a computation run
now, a replay of supplied data, or a comparison of generated files. They state
what the result does and does not establish.

For the commands that regenerate release records, reproduce installation and
command runs in a fresh checkout, or inspect previously recorded runs, see the
[maintainer's validation guide](docs/maintainers/validation.md). That guide
also explains how unsuccessful commands are recorded. `make public-site-parity`
compares the live website's downloadable packets with this source tree.

## Name and history

This project was published under the name Microcosm until 21 June 2026, when
**Microcosm became Plectis** to avoid confusion with the earlier Southampton
Microcosm hypermedia system, and to acknowledge that lineage without implying
any endorsement or affiliation. **Microcosm remains only where compatibility
or historical continuity requires it**: the `microcosm_core` import name, the
local state directory, generated records, and older links. See
[PROVENANCE.md](PROVENANCE.md) for the full lineage.

## Contributing, security, citation and licence

Contributions and error reports are welcome; [CONTRIBUTING.md](CONTRIBUTING.md)
has the development setup and commands for running the tests, and
[SECURITY.md](SECURITY.md) has the private reporting route. To cite Plectis,
use [CITATION.cff](CITATION.cff) (GitHub renders it under "Cite this
repository").

Plectis is Copyright 2026 William Cook and is licensed under the Apache
License, Version 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). It was
developed by William Cook as an independent project using AI coding agents; see
[PROVENANCE.md](PROVENANCE.md) for authorship and third-party sources.

## Companion project: eight open Erdős problems in Lean 4

The **Formal Math & Proof** area above includes examples drawn from a
separate repository containing the Lean proof source and mathematical papers:

[**plectis-erdos**](https://github.com/wcook04/plectis-erdos)
contains Lean 4 work on Erdős Problems **#68, #243, #249, #251, #257, #269,
#1041, and #1049**. All eight remain open. Its README gives the statement, partial results
and remaining unsolved question for each problem. Lean verifies the proofs
against their formal statements; the claim records and papers explain how
those statements relate to the original problems. Running a software example
here does not rerun the companion repository's Lean proofs.

For the Lean example files in this software repository, `make check` rejects proof placeholders, project-defined axioms, native
evaluation, unsafe/partial declarations, and unbounded kernel limits before
the broader test suite runs.

- [**Read the proven partial results, problem by problem**](https://github.com/wcook04/plectis-erdos/blob/main/docs/RESULTS.md):
  one entry per problem, with links to the Lean declarations, an explanation
  of what each result proves, and the part of the problem that remains open. All eight problems remain open.
- [**Choose a problem paper**](https://github.com/wcook04/plectis-erdos#problem-papers):
  the companion README lists one short paper for each covered problem and
  states the partial results beside it.
- [**Read the systems paper**](https://wcook04.github.io/plectis/papers/claim-faithful-publication-systems-paper.pdf):
  how the authors compare the claims in the papers with the statements
  proved in Lean, and record which source version they used.
- [**Browse the Lean source**](https://github.com/wcook04/plectis-erdos/tree/ba9e7b27349712b1f0a703febf244ef33a245ee9):
  the recorded public source snapshot contains 1,274 Lean modules and 153,502
  theorem-like declarations, checked by the pinned kernel; start from
  `docs/ORIENTATION.md`. These counts include library declarations; they do
  not count solutions to Erdős problems. `v0.10.0` remains the version to cite.
- [**Release v0.10.0**](https://github.com/wcook04/plectis-erdos/releases/tag/v0.10.0):
  the version to cite when referring to that release.
