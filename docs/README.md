# Plectis documentation

The [repository README](../README.md) is the overview and starting point.
This page is the reading order behind it: choose what you want to understand
or do, then follow that route as far as you need. You can read the explanations
and papers without installing anything.

## Start

| What you came for | Read or run first | What you should have afterwards |
|---|---|---|
| Understand what Plectis is | [Understanding Plectis](UNDERSTANDING_PLECTIS.md) | The two uses of the toolkit, the terms used in the code, and one example followed from input to result. |
| Try it on your computer | [Quickstart](../QUICKSTART.md) | A local run and a record you can inspect, with no package installation required. |
| Find a component in your field | [Component specialties](../ORGANS.md#find-your-specialty) or the [interactive map](https://wcook04.github.io/plectis/docs/architecture.html#whole-system-map) | The component's code, example, checks and stated limits. |
| Read the argument and evidence | [Paper guide](papers/README.md) | A paper chosen by the question it answers, with a PDF and searchable text. |
| Read the mathematics | [Lean companion](https://github.com/wcook04/plectis-erdos) | Problem papers, theorem statements and Lean proofs in the repository that owns them. |

If you are new to the project, the explanation and one quickstart run are
enough before choosing a component. The complete architecture and component
inventory are there when you want to follow the implementation further.

## Read and explore

[Understanding Plectis](UNDERSTANDING_PLECTIS.md) follows a prompt-injection
example through the actual files and explains what its passing result means.
The [generated architecture](../ARCHITECTURE.md) then maps the shared runtime,
registries and components, and [the component map](../ORGANS.md) gives the
individual runners and evidence. These are different depths of the same system.

For the research argument, start with the [paper guide](papers/README.md).
The [Plectis paper](../plectis-public-system.pdf) discusses the public toolkit;
the guide also routes to the wider corpus, with local PDFs and searchable text.
Follow each paper's current reading path when a mirror is marked stale.
[Paper source and build instructions](../paper/README.md) are for checking or
rebuilding a manuscript.

[Hypothesis handoffs](../HYPOTHESIS_HANDOFF.md) explain a further use: writing
down an open question, the alternatives and the evidence that would distinguish
them so an expert has a concrete request to answer. For other projects and
walkthroughs, see [all public work](https://wcook04.github.io/).

## Contribute and maintain

Start with [Contributing](../CONTRIBUTING.md) for changes, corrections and
review. The runbooks answer narrower questions:

- [Validation](maintainers/validation.md): choose smoke checks, isolated tests,
  drift checks or a standalone export, and interpret their results.
- [Security](maintainers/security-runbook.md): run the local checks and report
  a security issue.
- [CLI decomposition plan](maintainers/cli-decomposition.md): the proposed split
  of the command module, for contributors working on that code.
- [Root migration plan](maintainers/root-migration-plan.md): dependencies to
  update before moving generated documents or runtime inputs.

## Reference

These maps are generated from source. Their root paths are also used by tools
and incoming links, so they remain at those paths:

| Document | Use it to |
|---|---|
| [Architecture](../ARCHITECTURE.md) | Trace the shared runtime and the complete component relationships. |
| [Component map](../ORGANS.md) | Find a component, its runner and supporting evidence. |
| [Agent task routes](../AGENT_ROUTES.md) | Find the tools and source owners for a coding task. |
| [First action examples](../FIRST_ACTION.md) | See how a goal becomes a concrete first command. |
| [Release review](../RELEASE_REVIEW.md) | Inspect the recorded release checks and limits. |

For a repository-aware coding agent, [AGENTS.override.md](../AGENTS.override.md)
is the compact entry contract and [AGENTS.md](../AGENTS.md) has the deeper
mutation rules. A human reader can stay with the guides above.

The [source directory map](UNDERSTANDING_PLECTIS.md#where-the-files-fit) explains
`src/`, `examples/`, `tests/`, the JSON registries and the generated documents.
