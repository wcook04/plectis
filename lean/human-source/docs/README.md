<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reading and working with the research

Choose a problem, read its short paper, then follow the argument into the
longer record or the supporting source. All eight original Erdős problems
remain open. You can contribute a correction, explanation, counterexample or
useful failed approach without solving one.

## Read

- [A reader's way in](READING_GUIDE.md): an introduction without commands or Lean.
- [The papers](../paper/README.md): the current short papers and longer records.
- [Results and open questions](RESULTS.md): the stated progress and its limits.
- [Prior work](PRIOR_ART.md): antecedents, attribution and comparisons.
- [Related problems](RELATED_PROBLEMS.md): connections across the collection.

The short papers explain the main ideas. The long records retain more detail,
attempts and unresolved steps. Each result's own evidence boundary matters:
an ordinary mathematical argument and a Lean-checked declaration are different
kinds of evidence.

## Check

Start with the [source map](SOURCE_MAP.md) to locate the evidence for a result.
[Reproducibility](REPRODUCIBILITY.md) gives the checkout and verification
commands. [External verification](EXTERNAL_VERIFICATION.md) explains the
selected Comparator interfaces and their limits.

The [claim record](claims.json) binds statements to their status and supporting
artifacts. [Methodology](METHODOLOGY.md) explains the separate roles of Lean,
repository checks and mathematical review. A navigation page or a successful
repository check does not establish a stronger mathematical statement.

## Contribute

[Contributing](../CONTRIBUTING.md) explains how to send an observation or a
focused pull request. [Credit and stewardship](research-commons/CREDIT_POLICY.md)
explains how accepted work is attributed, including negative results and
corrections. The [research commons](research-commons/README.md) describes how
another researcher can resume and return a longer investigation.

For an AI-assisted session, use [the research-shift guide](FRONTIER_RELAY.md).
Coding agents start at [the agent entry](../AGENTS.md); the
[agent workbench](agents/AGENT_WORKBENCH.md) documents the detailed tools.

## Where things live

| Folder | What belongs there |
|---|---|
| [Papers](../paper/README.md) | Current PDFs and manuscript sources, grouped by problem. |
| [Paper full text](papers/README.md) | Browsable Markdown versions and a detailed paper index. |
| [Agent guides](agents/README.md) | Commands, proof tools and rules for making changes. |
| [Verification guides](verification/README.md) | Replay instructions, statement comparisons and submission requirements. |
| [Technical reference](reference/README.md) | Research history, correction records and indexing details. |
| [Research commons](research-commons/README.md) | Contribution, review and attribution records. |
| [Semantic index](semantic/README.md) | Generated technical navigation through declarations and relationships. |
| [Primary sources](primary-sources/) | Source provenance and redistribution records. |
| [Measurements](measurements/) | Recorded measurements of the tools. |
| [Release records](release/) | Audits and release identity records. |

The main guides stay here: [reading guide](READING_GUIDE.md),
[results](RESULTS.md), [prior art](PRIOR_ART.md), [related problems](RELATED_PROBLEMS.md),
[source map](SOURCE_MAP.md), [reproducibility](REPRODUCIBILITY.md),
[methodology](METHODOLOGY.md), [scope](SCOPE.md) and
[architecture](ARCHITECTURE.md).

The JSON files beside these guides are used by the query tools and website.
[claims.json](claims.json) records public claim status;
[methodology.json](methodology.json) records the review rules.
The remaining indexes help locate evidence. Their filenames stay stable so
existing tools and source links continue to work. You can read the papers
without opening them.

[Generated technical navigation](ORIENTATION.md) gives a compact view for
readers using those indexes.

## Files at the repository root

`README.md` introduces the work and `CONTRIBUTING.md` explains how to help.
`AGENTS.md` is the shared instruction file for coding agents. Claude Code loads
it through `CLAUDE.md`. Detailed agent rules live in
[the agent guide](agents/AGENT_GUIDE.md), so reading the root does not require a tour
of the automation.

`lakefile.toml`, `lake-manifest.json` and `lean-toolchain` configure the Lean
project and pin its dependencies. `formalization.yaml` is the Comparator
manifest for selected statements; [external verification](EXTERNAL_VERIFICATION.md)
explains its coverage. `CITATION.cff` supplies citation metadata, while
`LICENSE`, `LICENSES/` and `REUSE.toml` record the licences.

The [code of conduct](../.github/CODE_OF_CONDUCT.md) and
[security policy](../.github/SECURITY.md) live under `.github/`, alongside CI
and contribution forms. [Privacy](PRIVACY.md), [scope](SCOPE.md) and
[methodology](METHODOLOGY.md) live here with the other guides.
