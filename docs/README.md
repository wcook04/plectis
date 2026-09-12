# Plectis documentation

Plectis is a Python toolkit and a collection of runnable research components.
Start with one question or one component; you do not need to read the whole
repository.

## Start

- [Repository overview](../README.md): what the toolkit does and a two-command tour.
- [Quickstart](../QUICKSTART.md): installation and a first local run.
- [Interactive map](https://wcook04.github.io/plectis/docs/architecture.html#whole-system-map): browse the components by area.

## Read and explore

- [The Plectis paper](../plectis-public-system.pdf): the argument, evidence and limits of the public toolkit.
- [Paper guide](papers/README.md): the wider corpus, with local PDFs and searchable text. Follow each paper's current reading path when a mirror is marked stale.
- [Paper source and build guide](../paper/README.md): how to check and build the Plectis paper.
- [Hypothesis handoffs](../HYPOTHESIS_HANDOFF.md): turn an open question into a testable request for expert review.
- [Maths companion](https://github.com/wcook04/plectis-erdos): papers and Lean source for eight open Erdős problems.
- [All public work](https://wcook04.github.io/): the other projects and walkthroughs.

## Contribute and maintain

- [Contributing](../CONTRIBUTING.md): changes, corrections and review.
- [Validation runbook](maintainers/validation.md): smoke checks, isolated tests, drift checks and exports.
- [Security runbook](maintainers/security-runbook.md): local checks and reporting.
- [CLI decomposition plan](maintainers/cli-decomposition.md): the plan for splitting the command module.
- [Root migration plan](maintainers/root-migration-plan.md): dependencies to update when moving generated documents and runtime inputs.

## Reference

These maps are generated from the source and still live at the root:

| Document | Use it to |
|---|---|
| [System map](../ORGANS.md) | Find a component, its runner and supporting evidence. |
| [Architecture](../ARCHITECTURE.md) | Understand how the components fit together. |
| [Agent task routes](../AGENT_ROUTES.md) | Find the tools for a coding task. |
| [First action examples](../FIRST_ACTION.md) | See how a goal becomes a concrete first command. |
| [Release review](../RELEASE_REVIEW.md) | Inspect the recorded release checks and limits. |

`src/` contains the Python package; `examples/` contains worked uses;
`tests/` contains checks. `core/`, `standards/` and `paper_modules/` describe
the components and their contracts. `atlas/` contains generated navigation;
`fixtures/` and `receipts/` contain the inputs and records used to test claims.
Agent instructions and compatibility filenames at the root serve coding
tools; the overview and this index are the routes for human readers.
