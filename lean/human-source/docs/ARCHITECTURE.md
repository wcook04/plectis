<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# How this repository works

Eight mathematical problem programmes connect papers, proofs, computations and
research records. Start with a [problem paper](../paper/README.md#problem-papers).
You do not need to know Lean or the project history.

## What this repository is

Lean checks formal proofs. The papers explain the mathematics, including
ordinary arguments and cited results. Source maps connect those explanations
to their supporting records.

The reviewed claim registry covers #68, #243, #249, #251, #257, #269, #1041 and
#1049. It describes selected public claims and their status.
Supporting declarations need not have a claim record; a new file or successful
build creates no public claim. The two Lean roots reflect the development's
history, not different standards of evidence.
[Methodology](METHODOLOGY.md) explains the review and change rules.

Using the degree-seven polynomial constructed by the erdosproblems.com
contributor ani, Lean proves that every preconnected strict-lemniscate set
containing two distinct roots has one-dimensional Hausdorff measure greater
than two. This refutes the exact Formal Conjectures path-image-length
statement; the separate total-variation bound is also checked. The other
seven targets remain open. Independent human review of correspondence with
the 1958 wording has not been recorded. Comparator checks only selected exact
statements, axioms and kernel acceptance; it does not assess novelty or
historical correspondence. This is a self-contained public release: its use
and its mathematical claims do not depend on private files.

## Why preserve explanations and failed approaches?

The design responds to [Henry Cohn on mathematical technical debt](https://terrytao.wordpress.com/2026/09/15/the-technical-debt-of-ai-generated-mathematics/),
[Tim Gowers on active reading](https://gowers.wordpress.com/2026/09/17/why-i-didnt-sign-the-fields-medallists-letter/)
and [Grant Sanderson on explanations](https://terrytao.wordpress.com/2026/09/18/if-math-is-more-than-proof-we-need-to-better-celebrate-the-rest-of-it/).
Plectis keeps arguments, sources and failed routes together so readers can
reconstruct an argument and continue it. Whether this helps more than papers,
source and an on-demand model remains untested. The
[reading guide](READING_GUIDE.md#work-through-an-argument) offers an active way in.

## Website, map and repository

The [website](https://wcook04.github.io/plectis/maths/) and its
[maths map](https://wcook04.github.io/plectis/maths/universe.html) connect a
problem to papers, results and recorded formal evidence. This checkout holds
the sources and works independently of the site. Humans enter through
[README.md](../README.md); agents use [AGENTS.md](../AGENTS.md). Both lead to
the same evidence.

## The architecture in one page

A statement in a paper may have a formal proof, an ordinary mathematical
argument, or a cited external theorem behind it. A correspondence audit starts
from the current paper and asks what establishes each assertion, including its
assumptions and full conclusion. The evidence routes join at public claim
review:

```text
ordinary proof / cited theorem       Lean source       finite computation
              |                         |                     |
              |                 formal statement review       |
              +-------------------------+---------------------+
                                        |
                                        v
                               docs/claims.json
                        public statement, evidence, limits
                                        |
                                        v
                           papers and public guides
                                        |
                                        v
                         generated indexes and source links
```

Each evidence route keeps its own scope. An ordinary proof or cited theorem
does not require a Lean proof, and a finite computation establishes only its
finite domain. Outside reading, criticism and reuse are observed separately;
none follows from passing through this diagram.

A stronger Lean theorem needs a checked implication to the printed statement.
Unproved conditions and partial coverage stay explicit.

For selected statements, [Comparator](EXTERNAL_VERIFICATION.md) compares the
separately declared challenge with the solution under a configured axiom
budget. Inspect the current configuration and available evidence with
`python3 scripts/query_corpus.py --route comparator_assurance`.
The [Palomar qualification route](verification/PALOMAR_QUALIFICATION.md),
`python3 scripts/query_corpus.py --route palomar_qualification`, checks the
repository's packaging requirements. The
[eight per-problem repository units](https://github.com/wcook04/plectis-erdos-lean)
have their own pinned source and replay checks. A local qualification decision
does not establish a service submission, registration or acceptance, and a
Comparator pass does not establish complete paper coverage.

Lean and the release checks test different parts of that route:

- Lean decides whether a formal proof establishes its precise formal statement.
- A mathematician decides whether the public wording describes that statement
  faithfully and what mathematical significance it has.
- The release program decides whether the files satisfy the recorded
  relationships: declarations resolve, source locations agree, paper identities
  match, and required limitations remain present.

The [reading guide](READING_GUIDE.md#contributing) records authorship and review.
These responsibilities do not imply that independent review has occurred.

## Which file is authoritative for what

| Question | Source | What to read there |
|---|---|---|
| What formal statement and proof does Lean check? | [Erdos249257.lean](../lean/Erdos249257.lean), [ErdosProblems.lean](../lean/ErdosProblems.lean) and the modules they import | The exact declarations at the source revision recorded for the result. |
| What does the selected public claim say? | [docs/claims.json](claims.json) | Wording, status, supporting declarations, finite ranges and remaining open propositions. |
| What review does a claim change require? | [docs/methodology.json](methodology.json), rendered as [methodology](METHODOLOGY.md) | The evidence and review required for each kind of change. |
| Which papers are shipped? | [docs/publication_contract.json](publication_contract.json) | Manuscript roles, file identities and reading routes. |
| Where is the evidence for one result? | [docs/SOURCE_MAP.md](SOURCE_MAP.md) | Routes between problems, claims, paper passages and Lean source. |
| Which statement does Comparator compare? | [verification/comparator.json](../verification/comparator.json) and [external verification](EXTERNAL_VERIFICATION.md) | The selected challenge, solution, permitted axioms and replay boundary. |
| What is ready for Palomar? | [docs/verification/PALOMAR_QUALIFICATION.md](verification/PALOMAR_QUALIFICATION.md) and [docs/PALOMAR_POLICY_RECONCILIATION.json](PALOMAR_POLICY_RECONCILIATION.json) | Repository qualification, with external actions and outcomes recorded separately. |
| Formal Conjectures progress? | [Crosswalk source](formal_conjectures_crosswalk.json) and [guide](verification/FORMAL_CONJECTURES_CROSSWALK.md) | Dated reviews and merges; separate pinned statement comparisons. |
| What did a research round return, and what does it still owe? | [The research record](reference/RESEARCH_RECORD.md) | Custody of each return, its dispositions, computed milestones, relation rows and contrasts. |
| Which checks govern a release? | [scripts/check_release.py](../scripts/check_release.py) and [the GitHub workflow](../.github/workflows/lean.yml) | The local checks and the checks run on pushes and pull requests. |

Keep mathematical explanations and reviewed interpretations authored. Generate
volatile facts—paper lists, source locations, selected interfaces and status
summaries—from the records that own them. The programme card in the
[agent guide](agents/AGENT_GUIDE.md) comes from the problem and claim owners;
[Palomar qualification](verification/PALOMAR_QUALIFICATION.md) comes from its
selection record. The [orientation](ORIENTATION.md), atlas and module index
are generated too. `python3 scripts/refresh_projections.py` updates these
surfaces; the release gate rejects stale copies. Dated development and campaign
records live in [technical reference](reference/README.md).

The eight individual problem papers are the active mathematical routes. The
former combined manuscript,
[paper/archive/erdos249-257-main-paper.tex](../paper/archive/erdos249-257-main-paper.tex),
is archived provenance only, not an active gateway.

## Repository map

This tree groups repeated directories; folder indexes give the full contents.

```text
plectis-erdos/
|-- README.md, AGENTS.md       Human and agent entry
|-- CONTRIBUTING.md           Contributions and credit
|-- CITATION.cff, LICENSE*    Citation and licences
|-- lake*, lean-toolchain     Lean build and dependency pins
|-- formalization.yaml        Selected Comparator statements
|-- paper/
|   |-- 68/ … 1049/           Short papers and longer records
|   |-- synthesis/, systems/  Cross-problem and system papers
|   |-- exposition/           Writing-method papers
|   |-- reasoning-parts/      Long-record source sections
|   `-- evidence/, archive/   Generated links and earlier work
|-- lean/
|   |-- ErdosProblems/        Eight programmes, Shared/, Synthesis/
|   `-- Erdos249257/          Original library and certificates
|-- docs/
|   |-- *.md, *.json          Reader guides and source records
|   |-- agents/               Operational instructions
|   |-- papers/               Inventory and generated full text
|   |-- reading-edition/      Portable paper introduction
|   |-- verification/         Replay instructions
|   |-- semantic/             Statement relationships
|   |-- research-commons/     Contributions, reviews and credit
|   `-- reference/, …         Specialist guides and provenance
|-- research/                 Experiments, examples and sessions
|-- research_corpus/          Preserved research returns
|-- computations/             Exact certificates and recomputation
|-- verification/             Formal interfaces and replay setup
|-- evidence/                 Paper-to-proof and Comparator records
|-- scripts/, skills/         Tools and agent workflows
`-- .github/                  CI, forms and community policies
```

Folder guides: [papers](../paper/README.md), [Lean](../lean/README.md),
[documentation](README.md), [research](../research/README.md),
[experiments](../research/experiments/README.md),
[returns](../research_corpus/README.md), [computations](../computations/README.md),
[verification](../verification/README.md), [evidence](../evidence/README.md),
[scripts](../scripts/README.md) and [skills](../skills/README.md).

The [agent workbench](agents/AGENT_WORKBENCH.md) documents exact queries;
the [Formal Conjectures crosswalk](verification/FORMAL_CONJECTURES_CROSSWALK.md)
connects to upstream statements. The [research commons](research-commons/README.md)
explains how work returns with evidence and credit. The companion
[selected verification repository](https://github.com/wcook04/plectis-erdos-lean)
is optional; this checkout is self-contained.

### Directory and naming conventions

`paper/` holds manuscripts and PDFs; `docs/papers/` holds generated full text
and its catalogue. `verification/` holds formal interfaces and configuration;
`docs/verification/` holds instructions. `research/` contains experiments and
tools; `research_corpus/` preserves dated returns.

Lean source names follow namespaces and Lake configuration. The older
`Erdos249257` name remains in imports, citations and recorded checks; use the
[source map](SOURCE_MAP.md) to locate results across both libraries. Renaming a
source requires updating those consumers together.

## A complete example

The [certificate definition](papers/full-text/erdos249-totient-reasoning-surface.md#definition-of-the-finite-residue-test)
and [certificate source map](SOURCE_MAP.md#249--certificate-reductions)
give the mathematical notation and source routes behind this example.

One public claim says that Lean has checked successful finite calculations at
every scale up to 82, together with eight small periods and separate shards.

In ordinary language, the record says:

```text
claim id: certified_kill_instances
public statement: Lean checked the listed finite cases.
status: verified finite instance
bounded range: eight small periods, every scale value up to 82, and the shard parameters, all named in the record. Nothing is asserted at 83.
formal evidence: six named Lean declarations.
still open: prove that successful cases exist beyond every fixed cutoff.
```

The range is contiguous rather than a sampled list: the scale quantity changes
only at prime powers and is constant between them, so the earlier deposits
through 64 already covered every value up to 66. Each scale is nevertheless an
independent construction — the two supporting modules share no prime — so the
band buys reach, not leverage.

*Verified finite instance* means Lean checked the stated finite inputs. A
supply of successful cases beyond every fixed cutoff would settle the open
problem by a proved equivalence; the finite list does not supply it.

This one record connects the layers:

1. The named declarations in the Lean files are the formal evidence.
2. [`docs/claims.json`](claims.json) records the public sentence, the
   finite range, the Lean declaration names, and the question still open.
3. The README and mathematical paper explain the result to readers.
4. Generated indexes provide links and source locations.
5. The release program checks that the declaration names still exist, the
   recorded locations remain accurate, the bounded range is present, the
   public limitation has not disappeared, and the generated files are current.

A mathematician is still responsible for judging that the English sentence is
a faithful description of the Lean statement. The software preserves that
reviewed relationship after it has been recorded.

## What happens when a change is made

| Change | What follows |
|---|---|
| A Lean statement or proof changes | Check the affected proof, review its assumptions and meaning, then update the claim and paper if their content changed. |
| An explanation changes | Check its links and evidence boundary. A change in mathematical meaning also needs the corresponding claim review. |
| A generated index is stale | Run its owning builder, inspect the result and rerun the relevant check. |
| A manuscript changes | Rebuild its PDF and include the source, PDF and check output in the proposal. Maintainers complete the generated paper updates before merging. |

[The agent guide](agents/AGENT_GUIDE.md) gives the source-change and validation
instructions; the [paper build guide](../paper/README.md#build-and-update)
gives the manuscript commands. Builders run after their source records change.
An English edit cannot change what Lean proved.

Preserve and reconcile concurrent contributions with evidence and attribution:
[Contributing](../CONTRIBUTING.md), [credit policy](research-commons/CREDIT_POLICY.md).

## How the checks run

GitHub runs a Lean job and a release-surface job on pull requests and on manual
dispatch. The [workflow file](../.github/workflows/lean.yml) contains their
current commands. The Lean job installs the pinned toolchain and dependencies,
then builds the supported roots named in that file. A separate coverage build,
[lean-coverage-build.yml](../.github/workflows/lean-coverage-build.yml), compiles
the paper-coverage Lean modules outside those roots on pushes to main that touch
a Lean input, and on manual dispatch. The release-surface job checks the claim
records, source links, generated files, papers, licences and query routes,
including tests with deliberately invalid inputs.

[Reproducibility](REPRODUCIBILITY.md) gives inspection, installation and build
commands. The proof wrapper invokes `lake build`;
`python3 scripts/check_release.py` does not run Lean.

For documentation work, the focused reader checks include
`python3 scripts/test_human_first_contact.py` and
`python3 scripts/check_architecture_guide.py`.
`python3 scripts/check_cold_clone_comprehension.py --quick` checks the bounded
navigation routes before a toolchain download. Use the relevant tool's own
tests for a tooling change and the proof checks for a Lean change.

## What the checks do not prove

A passing Lean build means that the kernel accepted the formal statements and
proofs it checked. The intended mathematical meaning still needs review.

A passing release check means that the recorded comparisons succeeded. It
does not mean that a program understood every sentence in the repository. It
also does not prove that every important sentence was selected for checking.
[Methodology](METHODOLOGY.md) sets out those responsibilities, and
[external verification](verification/README.md) explains additional statement
comparisons and their limits.

The
[systems paper](../paper/systems/claim-faithful-publication-systems-paper.pdf)
explains the publication architecture in more depth. Its historical checker
example is documented in [docs/publication_evidence.json](publication_evidence.json);
it illustrates the checks recorded for that exercise.

## Where to start

Read a [problem paper](../paper/README.md#problem-papers),
[reproduce a check](REPRODUCIBILITY.md), or
[propose a contribution](../CONTRIBUTING.md).

The archived combined #249/#257 PDF is not a default reading route.
[The documentation index](README.md) lists current guides and specialist references.
