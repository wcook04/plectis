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
comparing manuscript assertions with repository data and compiling the PDF.

[Hypothesis handoffs](../HYPOTHESIS_HANDOFF.md) explain a further use: writing
down an open question, the alternatives and the evidence that would distinguish
them so an expert has a concrete request to answer. For other projects and
walkthroughs, see [all public work](https://wcook04.github.io/).

## Contribute and maintain

Start with [Contributing](../CONTRIBUTING.md) for changes, corrections and
review. The runbooks answer narrower questions:

- [Validation](maintainers/validation.md): run example commands and automated
  tests, compare generated files with their source data, or produce a standalone export.
- [Security](maintainers/security-runbook.md): scan for secrets and private
  material, inspect the permitted operations, and report a security issue.
- [CLI decomposition plan](maintainers/cli-decomposition.md): the proposed split
  of the command module, for contributors working on that code.
- [Root migration plan](maintainers/root-migration-plan.md): dependencies to
  update before moving generated documents or runtime inputs.

<a id="reference"></a>

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
| [First action examples](../FIRST_ACTION.md) | See how a goal becomes a concrete first command. |
| [Release review](../RELEASE_REVIEW.md) | Reproduce the candidate's example runs, file comparisons and installation tests. |

Agent instructions: [first files and commands to use](../AGENTS.override.md)
and [rules for editing source and regenerating results](../AGENTS.md).

The [source directory map](UNDERSTANDING_PLECTIS.md#where-the-files-fit) explains
`src/`, `examples/`, `tests/`, the JSON registries and the generated documents.
