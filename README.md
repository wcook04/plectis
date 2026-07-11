# Plectis

[Website](https://wcook04.github.io/plectis/) ·
[Quickstart](QUICKSTART.md) ·
[System map](ORGANS.md) ·
[Contributing](CONTRIBUTING.md)

**Plectis is a set of public, runnable tests for the claims of an AI-built
system. Each component states one claim, takes a small frozen input, runs a
local check, and writes a receipt you can read. Run a check, then compare the
receipt with the claim.**

It runs entirely on your machine: no network or model calls, and it never
changes the source files it reads.

```bash
git clone https://github.com/wcook04/plectis && cd plectis
python3 -m pip install .
plectis tour --format text .
```

## What you get

Plectis is a local Python toolkit plus an executable reference corpus. In
practice that means four things you can do in the first five minutes:

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

Every component carries the same contract: a runner, source loci, an evidence
class (the kind of evidence that backs its claim), a receipt path, and an
authority ceiling (the stated limit of what a passing result proves).

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

From a clone (Python 3.11 or newer, no third-party runtime dependencies):

```bash
python3 -m pip install .
plectis tour --format text .
```

Without installing anything, the same commands run in source form:

```bash
PYTHONPATH=src python3 -m plectis tour --format text .
```

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
shared path, is in [Architecture](ARCHITECTURE.md) and as an interactive map
on the [website](https://wcook04.github.io/plectis/).

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

For the full per-component cards, open the [System map](ORGANS.md). One person
sets the direction; AI agents do the building and upkeep; and every
component's work is kept as evidence a separate check can read.

## Choose a route

| You want to | Go to | What you get |
|---|---|---|
| Run the first local witness | [Quickstart](QUICKSTART.md) | The shortest path to a working local run. |
| Understand how it works | [Architecture](ARCHITECTURE.md) | The runtime loop, the evidence loop, and the component families. |
| Browse every component | [System map](ORGANS.md) | A generated card for each part, one line at a glance or in full. |
| Inspect what each component computes, verifies, or rejects | `comprehend --slice mechanism` | `plectis comprehend --slice mechanism --format text`: every component's real mechanism, one line each. |
| Verify a specific claim before trusting it | `comprehend --first-action` | `plectis comprehend --first-action "<claim to verify>" --format text`: the owning component, its authority ceiling, and the command that tests it. |
| Audit what is and is not claimed | [Release review](RELEASE_REVIEW.md) · [Source status](SOURCE_STATUS.md) | The claim under review, the evidence behind it, and the distribution boundary. |
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

## Related projects

[plectis-lean-erdos249-257](https://github.com/wcook04/plectis-lean-erdos249-257)
is a Lean 4 formalisation of partial results, finite exclusions, and scope
boundaries for two open Erdős problems (#249 and #257), released as a citable
scholarly artefact. Both problems remain open; the repository is explicit
about exactly what is and is not proved.
