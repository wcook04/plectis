<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reading and working with the research

The [front page](../README.md) introduces the project. This index helps you
choose what to read or do next, whether you want to understand a result, check
its proof, continue the research, or inspect how the tools work.

All eight original Erdős problems remain open. The papers report intermediate
results and the approaches that stopped, with enough of the record preserved
for somebody else to inspect the argument and continue from it.

## Choose a way in

| What you want to do | Start here | Where it takes you |
|---|---|---|
| Understand the project without installing anything | [A reader's way in](READING_GUIDE.md) | The eight questions, what formalisation adds, and how to read the evidence. |
| Read the mathematics | [The papers](../paper/README.md) | A short paper for each problem, then a longer record when you need the details. |
| Find what has been established and what is missing | [Results and limits](RESULTS.md) | The results beside their remaining open questions, with routes to the evidence. |
| Check a result yourself | [Reproducibility](REPRODUCIBILITY.md) | Inspect one claim without Lean, then install the pinned environment if you want to rebuild proofs. |
| Continue the work or send a correction | [Contributing](../CONTRIBUTING.md) | A plain-language issue or a focused pull request, with evidence and credit. |
| Understand the software and research process | [How this repository works](ARCHITECTURE.md) | The roles of proofs, claim records, papers, query tools and release checks. |

## Read

Choose a statement in a [short paper](../paper/README.md#problem-papers).
Read its assumptions and argument, then use the longer record for a compressed
step, an earlier attempt, or the surrounding computations. [Prior work](PRIOR_ART.md)
helps with attribution; [related problems](RELATED_PROBLEMS.md) follows
connections elsewhere in the collection.

The [source map](SOURCE_MAP.md) locates the supporting Lean declarations and
paper passages. Each paper says which results have a Lean proof and which use
an ordinary mathematical argument or a cited theorem. The
[claim record](claims.json) gives the selected public statements, their status
and their exact remaining-open propositions. [Scope](SCOPE.md) records the
release boundary, and [methodology](METHODOLOGY.md) explains the rules for
changing a claim.

## Check

To replay a check, follow [reproducibility](REPRODUCIBILITY.md). For selected
statements, [external verification](EXTERNAL_VERIFICATION.md) also provides
Comparator interfaces: separately declared formal statements that can be
compared with the development. The [verification guides](verification/README.md)
explain those checks and their limits.

## Contribute

A contribution can be a correction, clearer explanation, earlier reference,
counterexample, or useful failed approach. [Contributing](../CONTRIBUTING.md)
explains what to send back. The [research commons](research-commons/README.md)
describes how longer investigations retain their starting point, evidence and
[credit](research-commons/CREDIT_POLICY.md).

For an AI-assisted session, use the [research-shift guide](FRONTIER_RELAY.md).
Give a coding agent [AGENTS.md](../AGENTS.md) so it can find the relevant
workflow. The [agent guides](agents/README.md) explain the tools once you have
a question to work on. You can also contribute to navigation, validation or
the contributor experience through the
[architecture contribution path](research-commons/ARCHITECTURE_CONTRIBUTIONS.md).

## Where things live

| Folder | What belongs there |
|---|---|
| [Papers](../paper/README.md) | Current PDFs and manuscript sources, grouped by problem. |
| [Paper full text](papers/README.md) | Generated Markdown versions and the detailed paper inventory. |
| [Agent guides](agents/README.md) | Query tools, proof tools and instructions for making changes. |
| [Verification guides](verification/README.md) | Replay instructions, statement comparisons and submission requirements. |
| [Technical reference](reference/README.md) | Research history, correction records and indexing details. |
| [Research commons](research-commons/README.md) | Contribution, review and attribution records. |
| [Semantic index](semantic/README.md) | Technical navigation through formal statements and their recorded relationships. |
| [Primary sources](primary-sources/) | Source provenance and redistribution records. |
| [Measurements](measurements/) | Recorded measurements of the tools. |
| [Release records](release/) | Audits and release identity records. |

The main reading guides stay directly under `docs/`. The JSON files beside
them supply the query tools and website. For example, `claims.json` records
public claim status and `methodology.json` records review rules; the other
indexes help locate evidence. You can read the papers without opening these
files. [Generated technical navigation](ORIENTATION.md) is a compact entry for
readers who want to use the indexes.

## Files at the repository root

`README.md` introduces the work and `CONTRIBUTING.md` explains how to help.
`AGENTS.md` is the shared entry for coding agents; `CLAUDE.md` loads it for
Claude Code. The detailed rules live in the [agent guide](agents/AGENT_GUIDE.md).

`lakefile.toml`, `lake-manifest.json` and `lean-toolchain` configure the Lean
project and pin its dependencies. `formalization.yaml` is the Comparator
manifest for selected statements. `CITATION.cff` supplies citation metadata;
`LICENSE`, `LICENSES/` and `REUSE.toml` record the licences.

The [code of conduct](../.github/CODE_OF_CONDUCT.md),
[security policy](../.github/SECURITY.md), CI and contribution forms live under
`.github/`. The [privacy policy](PRIVACY.md) stays here with the other guides.

## Improving these guides

Give each guide a reader's question to answer, and make its index link say
what the reader will learn or be able to do. Define terms where they first
matter, and check examples from the repository root. Keep mathematical
hypotheses, evidence and open boundaries exact when changing the prose.
For a generated page, change its source and run its owning builder;
[Contributing](../CONTRIBUTING.md) explains how to return the improvement.
