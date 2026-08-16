# Plectis

[Website](https://wcook04.github.io/plectis/) ·
[Interactive map](https://wcook04.github.io/plectis/docs/architecture.html#whole-system-map) ·
[The Plectis paper (PDF)](plectis-public-system.pdf) ·
[Paper guide](docs/papers/README.md) ·
[Lean companion](https://github.com/wcook04/plectis-lean-erdos249-257) ·
[Hypothesis handoffs](HYPOTHESIS_HANDOFF.md) ·
[Quickstart](QUICKSTART.md) ·
[Contributing](CONTRIBUTING.md) ·
[All public work](https://wcook04.github.io/)

**Plectis checks claims about software nobody watched being built.** Point it at
a project and it writes a local record you can re-run: the route it took through
the code, the evidence behind each finding, and the line where that finding
stops. The 88 components in this repository are the same mechanism published as
working examples — each states one narrow claim, takes a small frozen input,
runs a local check, and writes a receipt you can inspect.

It runs entirely on your machine: no network or model calls, and it never
changes the source files it reads.

Two commands, no install, any Python 3.11 or newer:

```bash
git clone https://github.com/wcook04/plectis && cd plectis
PYTHONPATH=src python3 -m plectis tour --format text .
```

That reads the project, picks a route through it, writes an inspectable record
beside it, and prints what it did — in about a tenth of a second, with your
source files unchanged. Installing is optional and covered under
[Install](#install); it only buys the shorter `plectis` command name.

**How this was built, and why it is built the way it is.** One person sets the
direction; large-language-model agents write and maintain most of the code.
William Cook selects the public claims and is responsible for them. That is also
why the corpus is built the way it is: every component has to leave evidence a
separate check can read, because the author's own confidence is not the thing
being offered.

The companion Lean repository,
[plectis-lean-erdos249-257](https://github.com/wcook04/plectis-lean-erdos249-257),
contains the Lean source and papers for eight open Erdős problems: #68, #243,
#249, #251, #257, #269, #1041, and #1049. All eight remain open. Plectis carries the runnable
claim-checking tools; the Lean repository carries the machine-checked
mathematics. Neither repository establishes anything about the private
development environment from which the public work was prepared.

For Plectis itself, start with [the Plectis paper](plectis-public-system.pdf).
For a mathematical problem or result, start with the
[Lean repository README](https://github.com/wcook04/plectis-lean-erdos249-257#readme)
and its per-problem map of strongest checked results,
[RESULTS.md](https://github.com/wcook04/plectis-lean-erdos249-257/blob/main/docs/RESULTS.md),
then choose its problem-specific paper. Read
[the systems paper](https://wcook04.github.io/plectis/papers/claim-faithful-publication-systems-paper.pdf)
for the boundary between a Lean theorem and a public claim about that theorem.
The clone-local [`docs/papers/`](docs/papers/) directory carries the active
paper corpus as PDFs and searchable text, so reading it does not require the
website.

For the wider scholarly corpus, start with the clone-local
[paper guide](docs/papers/README.md), or ask the machine route:

```bash
PYTHONPATH=src python3 -m plectis comprehend --slice papers --format text
```

It says what each paper owns, what it cannot establish, and which short
sequence fits your question. You do not need to read every paper.

## What you get

Plectis is a local Python toolkit plus an executable reference corpus. In
practice that means five things you can do in the first five minutes:

1. **Point it at a project.** `plectis tour --format text <project>` reads the
   project, picks a route through it, writes an inspectable record beside it,
   and prints what it did.
2. **Browse and run the component corpus.** The corpus is **88 components
   grouped into seven areas**: formal proof and certificates, agent
   reliability and safety, research and forecasting, projection-drift control,
   validators, work landing, and continuity. Each has a runner or replay you
   can execute locally.
3. **Test a specific claim before trusting it.**
   `plectis comprehend --first-action "<claim to verify>" --format text`
   routes any question to the owning component, the command that tests it, and
   the stated limit of the result.
4. **Reproduce the verification floor.** `make ci` runs the same install,
   test, and smoke path GitHub Actions runs; `./bootstrap.sh` is the
   pre-install probe for a cold clone.
5. **Make an open question cheap for an expert to answer.** A
   [hypothesis handoff](HYPOTHESIS_HANDOFF.md) exposes a tentative leading
   hypothesis, serious alternatives, the evidence that would distinguish
   them, and a checked landing path. Validate the worked example with:

   ```sh
   plectis hypothesis-handoff --input examples/hypothesis_handoff/independent_evaluation.json --format text
   ```

Every component carries the same contract: a runner, source loci, an evidence
class (the kind of evidence that backs its claim), a receipt path, and an
authority ceiling (the stated limit of what a passing result proves).
Hypothesis handoffs use the same discipline for what the project does not yet
know: a working guess remains a research prior, and an expert answer remains
advisory until its declared checks and release path pass.

## See it work

From a clone, point it at any repository and ask for the plain-text summary:

```bash
plectis tour --format text .
```

```text
Plectis read 5283 project files and wrote a local record.  repo -> .microcosm

  Route taken     readme_onboarding_route  (one of 5 it found)
  Record written  .microcosm/  (local files, written beside your project)
  Your source     unchanged

  Every finding in that record carries three handles:
    Evidence   .microcosm/evidence/   (what backs the finding)
    Source     .microcosm/events.jsonl   (where the finding came from)
    Scope      does not authorize release, provider calls, whole-system correctness
```

The record is built to be checked rather than trusted:

- **Rerunnable.** One command produced it, so you can run it again and compare
  instead of taking this page's word.
- **Traceable.** Each consequential finding names the evidence that backs it
  and the source it came from.
- **Bounded.** Each finding records where its authority stops, kept as machine
  state rather than buried in disclaimers.

The same record as a machine-readable card:

```bash
plectis tour --card .
```

## Install

Every command in this README runs from a clone without installing anything
(Python 3.11 or newer, no third-party runtime dependencies):

```bash
PYTHONPATH=src python3 -m plectis tour --format text .
```

Installing buys the shorter `plectis` command name. Install into a virtual
environment, which behaves the same on every platform:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/plectis tour --format text .
```

A system Python installed by Homebrew, Debian, or Ubuntu refuses
`python3 -m pip install .` with `error: externally-managed-environment`
([PEP 668](https://peps.python.org/pep-0668/)), because that interpreter
belongs to your operating system. The virtual environment above is the
supported answer, and the source form needs neither.

Contributors and the full test floor use `make install` and the `[test]`
extra instead; see [Contributing](CONTRIBUTING.md). The legacy `microcosm`
command remains available as a compatibility alias for older notes and
receipts.

## How it works

One shared spine serves every component: a project substrate that indexes
files and discovers patterns, a route layer that proposes and explains paths
through a project, a work layer that records reversible transactions, and an
evidence layer that binds every consequential claim to a receipt. Components
plug into that spine rather than shipping their own.

Read Plectis in this order: **mechanisms -> evidence discipline -> local
runtime**. If the record layer sounds like the product, the project has been
underclaimed and underread. If a validator result sounds like release, proof,
security, finance, provider, mutation, or private-system authority, it has
been overclaimed and overread.

The full picture, with the runtime loop and the component families on one
shared path, is in [Architecture](ARCHITECTURE.md) and as an
[interactive map on the website](https://wcook04.github.io/plectis/docs/architecture.html#whole-system-map).

## Browse the component map

Each area groups related components. Open one to read a card for every
component inside it: one line at a glance, or expanded in full.

| Area | Components | What it is |
|---|---|---|
| [Entry & Reveal](ORGANS.md#entry--reveal) | 2 | The entry point, and what its short guided path actually proves. |
| [Architecture & Navigation](ORGANS.md#architecture--navigation) | 12 | The kernel primitives, pattern binding, doctrine grammar, route plane, and standards that give the system its shape. |
| [Formal Math & Proof](ORGANS.md#formal-math--proof) | 20 | The Lean proof-evidence pipeline: corpus readiness, premise retrieval, tactic routing, verifier-trace repair, bounded witnesses, and certificates. |
| [Agent Reliability & Safety Replays](ORGANS.md#agent-reliability--safety-replays) | 20 | Source-open replay specimens for agent failure modes: red-team monitors, sabotage, sandbox escape, prompt injection, tool authority, memory poisoning, and benchmark gaming. |
| [Research & Science Replays](ORGANS.md#research--science-replays) | 9 | Replay specimens for scientific and forecasting workflows: replication rubrics, spatial world models, materials-lab safety, and prediction reconciliation. |
| [Import, Projection & Drift](ORGANS.md#import-projection--drift) | 20 | The membrane that brings non-secret substrate into the public tree and keeps generated projections honest instead of letting them drift. |
| [Work, Landing & Continuity](ORGANS.md#work-landing--continuity) | 5 | How reversible work transactions are recorded, how dirty-tree landing decisions are made, and how detached runs resume. |

For the full per-component cards, open the [System map](ORGANS.md), or click
through the same corpus as an
[interactive component browser](https://wcook04.github.io/plectis/docs/components.html)
on the website. One person sets the direction; AI agents do the building and
upkeep; and every component's work is kept as evidence a separate check can
read.

## Choose a route

| You want to | Go to | What you get |
|---|---|---|
| Run the first local witness | [Quickstart](QUICKSTART.md) | The shortest path to a working local run. |
| Understand how it works | [Architecture](ARCHITECTURE.md) | The runtime loop, the evidence loop, and the component families. |
| Browse every component | [System map](ORGANS.md) | A generated card for each part, one line at a glance or in full. |
| Inspect what each component computes, verifies, or rejects | `comprehend --slice mechanism` | `plectis comprehend --slice mechanism --format text`: every component's real mechanism, one line each. |
| Verify a specific claim before trusting it | `comprehend --first-action` | `plectis comprehend --first-action "<claim to verify>" --format text`: the owning component, its authority ceiling, and the command that tests it. |
| Choose a paper without scanning the library | [Paper guide](docs/papers/README.md) · `comprehend --slice papers` | A question-first route across all active papers, including their evidence boundaries and companion-repository handoff. |
| Audit what is and is not claimed | [Release review](RELEASE_REVIEW.md) · [Source status](SOURCE_STATUS.md) | The claim under review, the evidence behind it, and the distribution boundary. |
| Go deeper into the formal-math proofs | [Companion Lean repo](https://github.com/wcook04/plectis-lean-erdos249-257) · [Paper guide](docs/papers/README.md) | Lean 4 source and problem-specific papers for eight open Erdős problems: #68, #243, #249, #251, #257, #269, #1041, and #1049. |
| Watch it being used rather than read about it | [Demo videos](https://wcook04.github.io/plectis/#demo-videos) | Recorded walkthroughs of the system in use, on the website. |
| Click through the corpus instead of cloning | [Component browser](https://wcook04.github.io/plectis/docs/components.html) · [Paper browser](https://wcook04.github.io/plectis/docs/papers.html) | The same 88 components and the paper corpus as browsable pages, no install. |
| Hand the whole thing to a reviewer or a model at once | [Review packet](https://wcook04.github.io/plectis/plectis-ai-review-packet.json) · [reader digest](https://wcook04.github.io/plectis/plectis-ai-reader-digest.json) | One 14.4 MB JSON carrying the public cross-section for a single reading pass; the digest is the smaller cut for pasting. |
| See the rest of the work this belongs to | [wcook04.github.io](https://wcook04.github.io/) | The front door across the software, the Lean mathematics, the papers, and the films. |
| Work on Plectis with a coding agent | [AGENTS.md](AGENTS.md) | The durable agent contract: setup, authority, validation, and task routing. |
| Report a problem or contribute | [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) | How to raise an issue safely, and the verification floor for changes. |

## Scope and limitations

Plectis is an executable research prototype and a developer tool, offered for
inspection, experimentation, and learning. The public claim is deliberately
two-sided:

- **What is here:** a public executable cross-section of a larger AI-native
  workflow and research runtime, published as bounded mechanisms with source
  handles, commands or replays, evidence classes, receipts, and authority
  ceilings.
- **What backs it:** public code, copied non-secret source bodies, bounded
  public replays, subprocess witnesses, deterministic projections, validators,
  and generated registry records.
- **Where it stops:** it grants no release authority and no hosting
  authority, and it is not a hosted service, production-security system,
  professional-advice system, provider-affiliated product, trading or
  investment-advice system, formal-proof correctness oracle, source-mutation
  authority, or private-root equivalent.

A run inspects the project and leaves its files unchanged (no source
mutation); the record itself reports `source_files_mutated=false`. And this
public tree is **not a copy of any private system**: it is a cross-section of
a larger one, not a reconstruction.

The same boundary, per area: the formal-proof cluster is a bounded
proof-adjacent lab, not theorem-proof authority. The agent safety cluster
turns failure modes into replayable public mechanisms, not production safety
approval. The research cluster carries forecasting, replication, and
lab-safety workflow capsules, not domain expertise, market advice, or
track-record authority. The projection-drift cluster is the public membrane
for source imports and generated-projection checks, not permission to export
private/live material. The work-continuity cluster shows how agent work is
landed, resumed, and bounded, not authority to mutate a caller's source tree.

These boundaries are what let the smaller claims be exact.

## How the result stays honest

Plectis is built so a sceptic can check it rather than take its word:

- **The component list has one source of truth.** The [System map](ORGANS.md)
  is generated from the repository's governed component records, so the parts
  it shows are the parts that exist. Being listed there is not a quality or
  progress score.
- **Each finding says what kind of thing backs it.** The
  [Release review](RELEASE_REVIEW.md) sets out the claim under review and the
  evidence behind it, so you can weigh a finding by its support rather than by
  a headline count.
- **You can run the checks yourself.** `make release-review` regenerates and
  verifies the release review. `make release-candidate-proof` proves the
  first-action product end to end in a fresh checkout, and
  `make release-candidate-proof-verify` re-checks that proof as a
  distribution-true packet without rebuilding it. `make flight-recorder`
  records a run, keeping blocked/non-zero commands as preserved evidence, and
  `make flight-recorder-verify` replays it without rerunning the substrate.
  Each records what happened and does not authorize release, standards,
  provider calls, proof correctness, or production use.
- **The public site has its own parity check.** `make public-site-parity`
  compares the live website's downloadable packets against this source tree.

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
has the development setup and the verification floor, and
[SECURITY.md](SECURITY.md) has the private reporting route. To cite Plectis,
use [CITATION.cff](CITATION.cff) (GitHub renders it under "Cite this
repository").

Plectis is Copyright 2026 William Cook and is licensed under the Apache
License, Version 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). It was
developed by William Cook as an independent, AI-native solo project; see
[PROVENANCE.md](PROVENANCE.md) for authorship, third-party, and
no-affiliation boundaries.

## Companion project: eight open Erdős problems in Lean 4

The **Formal Math & Proof** area above includes bounded examples drawn from a
separate Lean repository. That repository owns the proof source and
mathematical exposition:

[**plectis-lean-erdos249-257**](https://github.com/wcook04/plectis-lean-erdos249-257)
contains Lean 4 work on Erdős Problems **#68, #243, #249, #251, #257, #269,
#1041, and #1049**. All eight remain open. Its README gives the statement, checked frontier,
and remaining obligation for each problem. The pinned Lean kernel checks the
formal propositions; the repository's claim records and papers explain what
those propositions do and do not establish. Plectis does not inherit proof
authority from that repository.

The public Plectis checkout applies the same floor to every Lean fixture it
ships: `make check` rejects proof placeholders, project-defined axioms, native
evaluation, unsafe/partial declarations, and unbounded kernel limits before
the broader test suite runs.

- [**Read the strongest checked results, problem by problem**](https://github.com/wcook04/plectis-lean-erdos249-257/blob/main/docs/RESULTS.md):
  one entry per problem — the strongest checked statements with exact Lean
  anchors, what each does not establish, and the surviving obligation beside
  it. All eight problems remain open.
- [**Choose a problem paper**](https://github.com/wcook04/plectis-lean-erdos249-257#problem-papers):
  the companion README lists one short paper for each covered problem and
  states the checked frontier beside it.
- [**Read the systems paper**](https://wcook04.github.io/plectis/papers/claim-faithful-publication-systems-paper.pdf):
  how that repository keeps its public claims matched to what the Lean kernel
  checked; the same publication discipline Plectis applies to software.
- [**Browse the Lean source**](https://github.com/wcook04/plectis-lean-erdos249-257/tree/ff9a4932bffe4f4f03daf98afe366650ef7e6f99):
  the recorded public source snapshot contains 1,023 Lean modules and 151,085
  theorem-like declarations, checked by the pinned kernel; start from
  `docs/ORIENTATION.md`. These are scale and navigation counts, not separate
  mathematical claims; `v0.8.0` remains the tagged citation anchor.
- [**Release v0.8.0**](https://github.com/wcook04/plectis-lean-erdos249-257/releases/tag/v0.8.0):
  the tagged, citable scholarly artefact and citation anchor.
