<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Plectis: research on eight open Erdős problems

Plectis is an open-source, AI-assisted research project. This repository contains
the papers, Lean proofs, computations, failed approaches, and questions
that remain, so another researcher can inspect the work and continue from it.
**All eight problems remain open.**

**[Read the mathematics](https://wcook04.github.io/plectis/maths/)** ·
[Website](https://wcook04.github.io/plectis/) ·
[All papers](paper/README.md) ·
[Contact me](https://wcook04.github.io/plectis/#contact)

![Eight open problems: papers, checked results, failed routes, and questions another researcher can continue](.github/system-map.png)

## Where to start

The numbers below identify questions in [Erdős Problems](https://www.erdosproblems.com/),
a collection of mathematical problems associated with Paul Erdős.
Lean is a proof assistant: software that verifies whether a formal proof
establishes its stated conclusion from its assumptions. You can read the
arguments in ordinary mathematical notation in the papers, which identify
the results with Lean proofs.

You do not need Lean or a coding agent to read the papers.
[A reader's way in](docs/READING_GUIDE.md) introduces the questions and the
different kinds of evidence. Each problem below has a short paper to start
with and a longer research record. [Results and limits](docs/RESULTS.md)
states what each proof or computation establishes and what remains missing.

For the mathematics, choose a [problem paper](#problem-papers), then use the
[source map](docs/SOURCE_MAP.md) to locate the cited Lean declarations.
For computer science or AI, read [how the repository works](docs/ARCHITECTURE.md)
and the [project papers](paper/README.md#project-papers): how researchers and
coding agents select a question, record their work, and compare public
statements with the proofs and computations they cite. Runnable workflow
components are in the separate [Plectis software toolkit](https://github.com/wcook04/plectis).

To continue from where I left off, see [CONTRIBUTING](CONTRIBUTING.md).
Use a coding agent if you like. This is the part I am most excited about.

To inspect one recorded statement and its cited source, [follow one claim](docs/REPRODUCIBILITY.md#try-one-claim-without-lean)
using Git and Python. You do not need a Lean installation or model account.
The clone is hundreds of megabytes; the separate proof-build route downloads
a larger Lean and Mathlib environment.

## Why this exists

I prioritised expository quality and a collaborative structure over trying to
solve the problems; I hope to now solve them with others rather than alone.
The idea is to turn intermediary findings into something reusable by
mathematicians who actually understand the material. That includes the routes
that stopped and the reasons they stopped.

I am responsible for all claims, sources and the release. Plectis is an
independent, AI-assisted prototype, not something I am declaring finished.
It has had no independent mathematical review (trying to get this), and I
need help to get anywhere near "done". Meaning, novelty and significance still
need human judgement.

## Problem papers

For a first look, start with **#257** for full-support irrationality and
achievement-set measure, or **#249** for exact kernel rank, finite certificates,
and recorded routes that stopped. Each paper distinguishes ordinary proofs,
Lean-checked results and open questions.

| Problem | Topic | Papers |
|---|---|---|
| [#68](https://www.erdosproblems.com/68) | [Factorial-denominator irrationality](https://wcook04.github.io/plectis/maths/problems/erdos_68.html) | [short paper](paper/68/erdos-68-factorial-denominator-irrationality.pdf) · [longer paper](paper/68/erdos68-factorial-reasoning-surface.pdf) |
| [#243](https://www.erdosproblems.com/243) | [Reciprocal-tail rigidity](https://wcook04.github.io/plectis/maths/problems/erdos_243.html) | [short paper](paper/243/erdos-243-reciprocal-tail-rigidity.pdf) · [longer paper](paper/243/erdos243-reciprocal-tail-reasoning-surface.pdf) |
| [#249](https://www.erdosproblems.com/249) | [Binary totient series](https://wcook04.github.io/plectis/maths/problems/erdos_249.html) | [short paper](paper/249/erdos-249-binary-totient-series.pdf) · [longer paper](paper/249/erdos249-totient-reasoning-surface.pdf) |
| [#251](https://www.erdosproblems.com/251) | [Prime-gap dyadic series](https://wcook04.github.io/plectis/maths/problems/erdos_251.html) | [short paper](paper/251/erdos-251-prime-gap-dyadic-series.pdf) · [longer paper](paper/251/erdos251-prime-gap-reasoning-surface.pdf) |
| [#257](https://www.erdosproblems.com/257) | [Mersenne-support subseries](https://wcook04.github.io/plectis/maths/problems/erdos_257.html) | [short paper](paper/257/erdos-257-mersenne-support-subseries.pdf) · [longer paper](paper/257/erdos257-mersenne-reasoning-surface.pdf) |
| [#269](https://www.erdosproblems.com/269) | [Three-prime running LCM](https://wcook04.github.io/plectis/maths/problems/erdos_269.html) | [short paper](paper/269/erdos-269-three-prime-running-lcm.pdf) · [longer paper](paper/269/erdos269-running-lcm-reasoning-surface.pdf) |
| [#1041](https://www.erdosproblems.com/1041) | [Lemniscates and Newton flow](https://wcook04.github.io/plectis/maths/problems/erdos_1041.html) | [short paper](paper/1041/erdos-1041-lemniscate-newton-flow.pdf) · [longer paper](paper/1041/erdos1041-lemniscate-reasoning-surface.pdf) |
| [#1049](https://www.erdosproblems.com/1049) | [Rational-base Lambert series](https://wcook04.github.io/plectis/maths/problems/erdos_1049.html) | [short paper](paper/1049/erdos-1049-rational-base-lambert.pdf) · [longer paper](paper/1049/erdos1049-rational-base-lambert-reasoning-surface.pdf) |

[Read the result summaries and their limits](docs/RESULTS.md#problem-by-problem-guide),
including prior work, what was checked, and the questions that remain.

<a id="what-the-checks-establish"></a>

## What Lean and Comparator verify

Lean verifies that a compiled proof establishes the formal statement written
in the source. Use the [source map](docs/SOURCE_MAP.md) to locate a declaration
cited in a paper. The [claim records](docs/claims.json) list the published
statements and their status; [prior art](docs/PRIOR_ART.md) lists earlier
results and their relationship to the work here.

Comparator compares a separately declared statement with the statement
established by its Lean solution, using an explicit list of allowed assumptions.
[`formalization.yaml`](formalization.yaml) lists the **selected statements**;
the comparison does not cover every theorem in this repository. The
[verification dossier](docs/EXTERNAL_VERIFICATION.md) identifies the selected
statements across all eight problems and the limits of the comparison.

Researchers still have to judge whether a formal statement expresses the
intended problem, whether it is new, and whether it is worth studying.
[Methodology](docs/METHODOLOGY.md) records the evidence and review required
before changing a public claim. Do not infer results from private or
unreleased work.

## Contribute

An idea, a correction, a counterexample, a failed route with a checkable
reason, or a clearer explanation can help. You do not need to solve a problem.
Infra suggestions also get credit!

- **Ideas, corrections or review:** use the
  [research-progress form](https://github.com/wcook04/plectis-erdos/issues/new?template=research_progress.yml)
  or [email me](https://wcook04.github.io/plectis/#contact).
- **Changes to the repository:** follow [CONTRIBUTING](CONTRIBUTING.md).
- **Your own agent and spare compute:** use the [frontier relay](docs/FRONTIER_RELAY.md)
  to choose a starting point and return what you find with its evidence.

When maintainers accept contributed work, they commit a receipt naming the
contributor and the files, results or evidence being credited. The
[credit policy](docs/research-commons/CREDIT_POLICY.md) explains how contributions
are attributed.

If you solve a problem, the credit and the result are all yours. If this repo
or my intermediary progress helped, please cite this release and say how, so
others find it and we make progress together instead of hoarding partial
results out of fear of being scooped, or rebuilding the same infrastructure
instead of improving one cumulatively.

**Experts:** email me any insight. I will do the work and fully credit you
for the insight and whatever follows from it.

## Read or verify locally

Use [REPRODUCIBILITY](docs/REPRODUCIBILITY.md) for commands to clone the
repository, inspect claim records and compile proofs. Choose other guides
from the [documentation index](docs/README.md). For the roles of the source
files, claim records and release programs, read
[how the repository works](docs/ARCHITECTURE.md); it assumes no Lean knowledge
or project history.

| Location | What you will find |
|---|---|
| [`paper/`](paper/README.md) | PDFs and manuscript sources, grouped by problem. |
| [`lean/`](lean/) | The Lean proofs. |
| [`docs/`](docs/README.md) | Reading guides, results, prior art and evidence records. |
| [`research/`](research/) | Additional research libraries and experiments. |
| [`research_corpus/`](research_corpus/Erdos1041/CORPUS_MANIFEST.json) | The separate source-only research record for #1041. |
| [`verification/`](verification/) | Comparator interfaces, certificates and failed-route records. |
| [`scripts/`](scripts/) | Navigation, build and release tools. |
| [`skills/`](skills/README.md) | Optional workflows for coding agents. |

Coding agents start at [`AGENTS.md`](AGENTS.md). `CLAUDE.md` loads that same
entry for Claude Code; the detailed commands live in the
[agent workbench](docs/agents/AGENT_WORKBENCH.md). The
[agent-navigation paper](paper/systems/cold-clone-to-proof-receipt.pdf)
explains the design.

Cloning runs no project code. Proof builds use the pinned Lean toolchain and
Mathlib. See the [security policy](.github/SECURITY.md) for the execution boundary.

<!-- BEGIN generated_corpus_at_a_glance -->
<!-- Generated by scripts/build_corpus_descriptor.py; do not edit this region. -->
<details>
<summary>Corpus inventory and counting limits</summary>

## Corpus at a glance

The reviewed layer a mathematician should judge: 141 curated claim records in 30 contribution families, reaching Lean source through 451 principal declaration links. `docs/SCOPE.md` gives its shape and `docs/RESULTS.md` gives the strongest checked result per problem. The website and the papers are the human reading path.

The rest is engineering inventory. About 91% of the 156,245 declarations (142,668 across 695 modules) are machine-emitted certificate shards: one integer checked prime, one position excluded. The remainder is not all hand-written either.

| Engineering inventory | Current size |
|---|---:|
| Lean modules (the two library roots) | 1,274 |
| Formal results and supporting lemmas | 153,502 |
| Curated claim records | 141 |
| Contribution families | 30 |

Generated shards are counted as formal source and never as separate
mathematical claims. Claim records cover every status, including cited and
open, and are partitioned once.
These are navigation counts, not novelty claims. They still need expert validation.

</details>
<!-- END generated_corpus_at_a_glance -->

<!-- BEGIN generated_principal_declaration_anchors -->
<!-- Generated by scripts/build_corpus_descriptor.py; do not edit this region. -->
## Following a result into Lean

The paper links each headline result to the relevant source. For a particular
topic, start with the [source map](docs/SOURCE_MAP.md); it gives the module
order without asking you to decode Lean declaration names first.
<!-- END generated_principal_declaration_anchors -->

## About the project

Read [From Spare Compute to Cumulative Mathematics](paper/systems/open-source-mathematics-strategy.pdf)
for the open-source research process and the ways to contribute.
[Problem-Sized Lean Worlds](paper/systems/claim-faithful-publication-systems-paper.pdf)
describes how researchers publish mathematical claims with their proofs,
source references and validation records.

For the wider project, see the [Plectis software repository](https://github.com/wcook04/plectis).
The maths papers and proofs here are self-contained.

## Citation and licence

Cite release `v0.10.0` via [CITATION.cff](CITATION.cff). Code, scripts and
documentation are Apache-2.0; manuscript sources and PDFs are CC-BY-4.0.
[REUSE.toml](REUSE.toml) records the file-level licences and exceptions.
[Scope](docs/SCOPE.md), [privacy](docs/PRIVACY.md) and the
[code of conduct](.github/CODE_OF_CONDUCT.md) are available in the documentation.
