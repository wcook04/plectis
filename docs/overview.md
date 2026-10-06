# How Plectis fits together

Plectis is an independent experiment in research with AI. This page explains
why its tools belong together and how the public software relates to the
mathematical work. For setup, start with the [quickstart](../QUICKSTART.md);
for a program you can inspect, choose a [worked guide](guides/README.md).

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
[toolkit paper](../plectis-public-system.pdf) discusses what publishing selected
tools and tests lets another person examine; the [paper guide](papers/README.md)
connects it to the mathematics and research-process papers.
