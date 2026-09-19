# Plectis documentation

The [repository README](../README.md) is the overview and starting point.
The guides below explain the toolkit, show commands you can run, and link to
source code and papers. You can read the explanations and papers without
installing anything.

<a id="start"></a>

## Human guides

| Task | Document | Contents |
|---|---|---|
| Understand what Plectis is | [Understanding Plectis](UNDERSTANDING_PLECTIS.md) | The two uses of the toolkit, the terms used in the code, and one example followed from input to result. |
| Try it on your computer | [Quickstart](../QUICKSTART.md) | A local run and a record you can inspect, with no package installation required. |
| Find a component in your field | [Component specialties](../ORGANS.md#find-your-specialty) or the [interactive map](https://wcook04.github.io/plectis/docs/architecture.html#whole-system-map) | The Python program, prepared input files, saved output and pass/fail conditions for that component. |
| Read the argument and evidence | [Paper guide](papers/README.md) | A paper chosen by the question it answers, with a PDF and searchable text. |
| Read the mathematics | [Lean companion](https://github.com/wcook04/plectis-erdos) | Problem papers, theorem statements and the corresponding Lean source. |

If you are new to the project, the explanation and one quickstart run are
enough before choosing a component. The complete architecture and component
inventory are there when you want to follow the implementation further.

## Read and explore

In [Understanding Plectis](UNDERSTANDING_PLECTIS.md), you can inspect a prepared
record for a hostile web page, run the Python program that compares the record
with its policy, and open the resulting JSON file. The
[generated architecture](../ARCHITECTURE.md) identifies the command handler,
project-state functions and registry files. In the
[component map](../ORGANS.md), each entry lists the program and saved results
for another example.

For the research argument, start with the [paper guide](papers/README.md).
The [Plectis paper](../plectis-public-system.pdf) discusses the public toolkit;
the guide also lists the other papers, with local PDFs and searchable text.
If a paper’s Markdown copy is marked stale, open the current source or PDF
linked in its catalogue entry.
[Paper source and build instructions](../paper/README.md) give the commands for
comparing manuscript text with its recorded evidence and compiling the PDF.

[Hypothesis handoffs](guides/hypothesis-handoffs.md) explain a further use: writing
down an open question, a tentative answer, alternatives and proposed
observations or experiments to discuss with an expert. For other projects and
walkthroughs, see [all public work](https://wcook04.github.io/).

## Contribute and maintain

Start with [Contributing](../CONTRIBUTING.md) for changes, corrections and
review. The runbooks answer narrower questions:

- [Public boundary](governance/public-boundary.md): which material belongs in the
  public toolkit and what a passing check establishes.
- [Release discipline](governance/release-discipline.md): rules for publishing
  changes and interpreting their evidence.
- [Validation](maintainers/validation.md): run example commands and automated
  tests, compare generated files with their source data, or produce a standalone export.
- [Security](maintainers/security-runbook.md): search selected text files for
  the policy's listed tokens, read recorded permission fields, and report a security issue.
- [Architecture maintenance](maintainers/architecture.md): document owners,
  regeneration rules, and the interfaces to preserve when moving code or files.

<a id="reference"></a>

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
outputs under `.microcosm/`, as in the [worked example](UNDERSTANDING_PLECTIS.md#one-example-you-can-follow). Return the commit,
commands, input and output paths, what passed or failed, and what the example
does not establish. A concrete failed run is a useful contribution too; see
[CONTRIBUTING](../CONTRIBUTING.md).

For theorem status, proof search or mathematical work, use the separate
[Lean corpus agent quickstart](https://github.com/wcook04/plectis-erdos/blob/main/docs/agents/README.md#start-with-current-public-work).
Its `scripts/agent_entry.py` selects the mathematical workflow and reports
checkout provenance. Plectis component examples do not substitute for that
repository's proof evidence.

## Generated reference and agent instructions

You can [clone the repository and ask a coding agent a question](../README.md#explore-with-a-coding-agent).
`AGENTS.override.md` and `AGENTS.md` specify which files and commands the agent
should use; JSON files store input data, configuration and program results.
You can also read the guides, source files and reference tables yourself,
including the detailed entries below.

These maps are generated from source. Their root paths are also used by tools
and incoming links, so they remain at those paths:

| Document | Use it to |
|---|---|
| [Architecture](../ARCHITECTURE.md) | Trace the shared runtime and the complete component relationships. |
| [Component map](../ORGANS.md) | Find a component's Python program, prepared inputs and saved results. |
| [Agent task routes](../AGENT_ROUTES.md) | Find commands and implementation files for a coding task. |
| [Find a component command](../FIRST_ACTION.md) | Match words in a task description to a suggested command, then run that command separately. |
| [Release review](../RELEASE_REVIEW.md) | Reproduce the candidate's example runs, file comparisons and installation tests. |

Agent instructions: [first files and commands to use](../AGENTS.override.md)
and [rules for editing source and regenerating results](../AGENTS.md).

The [source directory map](UNDERSTANDING_PLECTIS.md#where-the-files-fit) explains
`src/`, `examples/`, `tests/`, the JSON registries and the generated documents.
