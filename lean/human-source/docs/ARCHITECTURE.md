<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# How this repository works

This is a public Lean project about eight mathematical problem programmes.
It keeps the proofs, papers, computations and research records together so
another researcher can inspect the work and continue it. This guide explains
how those files fit together and what the checks establish.

You do not need to know Lean or the project history to use this guide. To read
the mathematics first, choose a [problem paper](../paper/README.md#problem-papers).

## What this repository is

The repository has two jobs: preserve the mathematical work and publish an
account of it that a reader can check. Lean checks formal proofs. The papers
explain the mathematics, including ordinary arguments and results drawn from
the literature. Source maps and query tools connect those explanations to
their supporting records.

The reviewed claim registry covers #68, #243, #249, #251, #257, #269, #1041 and
#1049. The two Lean roots reflect the development's history, not different
standards of evidence. A declaration has the public status recorded for it in
the registry; adding a file or compiling a library does not create that status.
[Methodology](METHODOLOGY.md) explains the review and change rules.

The degree-seven counterexample found by the erdosproblems.com contributor ani
refutes the total-variation formulation of Erdős #1041; this repository
formalises it in Lean. The other seven target problems are not resolved here. Independent human
review of correspondence with the historical curve-length formulation has not
been recorded. Comparator checks only its selected exact statements, configured
axioms and kernel acceptance; it does not assess novelty or historical
correspondence. This is a self-contained public release: its use and its
mathematical claims do not depend on private files.

## The architecture in one page

A statement in a paper may have a formal proof, an ordinary mathematical
argument, or a cited external theorem behind it. A correspondence audit starts
from the current paper and asks what establishes each assertion, including its
assumptions and full conclusion. Publication proceeds from checked evidence:

```text
Lean source + review of its mathematical meaning
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

These are two directions through the same records. Starting from a paper
selects what needs checking; it does not make the paper proof authority. A
stronger Lean theorem needs a checked implication to the printed statement.
An unproved condition or a proof of only part of a statement stays explicit.

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

Those are responsibilities, not a claim that independent mathematical review
has occurred. The [reading guide](READING_GUIDE.md#contributing) states the
project's authorship and current review position.

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

| Location | What it contains |
|---|---|
| [paper/](../paper/README.md) | Short papers, longer research records, manuscript sources and PDFs. |
| [lean/Erdos249257.lean](../lean/Erdos249257.lean) and [lean/Erdos249257/](../lean/Erdos249257/) | The historical library for #249/#257 and machinery used by later work. |
| [lean/ErdosProblems.lean](../lean/ErdosProblems.lean) and [lean/ErdosProblems/](../lean/ErdosProblems/) | Formal work grouped by problem; claim status is recorded separately. |
| [research/examples/](../research/examples/Examples.lean) | A small downstream Lean user of the library. |
| [docs/](README.md) | Reading guides, claim records and generated indexes. |
| [scripts/](../scripts/) | Queries, builders, release checks and tests. |
| [verification/](../verification/) | Comparator statements and configuration, replay tools and external-statement comparisons. |
| [skills/](../skills/README.md) | Workflows for research, validation and contribution. |
| [research/experiments/](../research/experiments/) | [Rerun the finite #251 computations and compare their outputs with saved results](../research/experiments/erdos251/README.md), or inspect [test changes used to exercise the release checker](../research/experiments/publication_mutations.json). |

Start from a problem or a statement, then follow the source map to its
modules. The [agent workbench](agents/AGENT_WORKBENCH.md) documents the query
commands for a problem, claim, module, declaration or paper passage. The
[Formal Conjectures crosswalk](verification/FORMAL_CONJECTURES_CROSSWALK.md)
provides the corresponding routes into the pinned upstream statement collection.

The [research commons](research-commons/README.md) explains how independent
work returns to the repository with its starting commit, evidence and credit.
The companion [Plectis software repository](https://github.com/wcook04/plectis)
contains the general workflow components. This checkout contains the
mathematics and the tools needed to work with it.

## A complete example

The [certificate definition](papers/full-text/erdos249-totient-reasoning-surface.md#the-problem-and-what-is-actually-known)
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

The phrase *verified finite instance* is not a score or a project-specific
milestone. It means only that Lean checked a stated finite set of inputs. The
open problem requires cases beyond every fixed cutoff, so the finite list does
not settle it. The development also proves an exact equivalence: a supply of
cases beyond every fixed cutoff would settle the open problem itself. An edit
that erased this boundary would therefore be a false mathematical
announcement, not a small wording change.

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

The kind of change determines the checks and the files that follow it.

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

When another contribution lands during the work, preserve the original delta,
reconcile it with current main and check the combined result. The
[contributor guide](../CONTRIBUTING.md) and
[credit policy](research-commons/CREDIT_POLICY.md) explain how that return is
reviewed and attributed.

## How the checks run

GitHub runs a Lean job and a release-surface job on pushes and pull requests.
The [workflow file](../.github/workflows/lean.yml) contains their current commands.
The Lean job installs the pinned toolchain and dependencies, then builds the
formal libraries and supported downstream examples. The release-surface job
checks the claim records, source links, generated files, papers, licences and
query routes, including tests with deliberately invalid inputs.

[Reproducibility](REPRODUCIBILITY.md) is the command guide. It starts with a
claim you can inspect without Lean, then gives installation and proof-build
instructions. The proof wrapper invokes `lake build`; it is separate from
`python3 scripts/check_release.py`, which does not run Lean.

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

The printable
[Problem-Sized Lean Worlds](../paper/systems/claim-faithful-publication-systems-paper.pdf)
explains the publication architecture in more depth. Its historical checker
example is documented in [docs/publication_evidence.json](publication_evidence.json);
it illustrates the checks recorded for that exercise.

## Where to start

| Your next step | Guide |
|---|---|
| Read one mathematical argument | [Individual problem papers](../paper/README.md#problem-papers) |
| Inspect a result and its remaining question | [Results and limits](RESULTS.md), then [scope](SCOPE.md) |
| Find the proof behind a statement | [Source map](SOURCE_MAP.md) |
| Reproduce a check on your machine | [Reproducibility](REPRODUCIBILITY.md) |
| Work with a coding agent | [Agent guides](agents/README.md) |
| Propose a correction or continuation | [Contributing](../CONTRIBUTING.md) |

The archived combined #249/#257 PDF is not a default reading route.
[The documentation index](README.md) lists the current guides and specialist
references.
