<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Papers

Each of the eight covered Erdős problems has a short first-read paper and a
longer complete reasoning record. Start with the short paper for the result,
its argument and the question that remains. Use the longer record when you
want to recover a detailed step, inspect a computation, or follow an approach
that stopped. You do not need Lean or a coding agent to read either.

All eight problems remain open. The papers report partial results, failed or
equivalent routes, finite evidence, and the exact obligations that survive.
If the problem numbers or formalisation are unfamiliar, read
[a reader's way in](../docs/READING_GUIDE.md) first. For the design of the tools
and the research process, go to the [project papers](#project-papers).

## Problem papers

| Problem | Short paper | Complete reasoning record |
|---|---|---|
| #68 | [Two Incomparable Denominator Exclusions for ∑ₙ≥₂ 1/(n!−1)](68/erdos-68-factorial-denominator-irrationality.pdf) ([source](68/erdos-68-factorial-denominator-irrationality.tex)) | [The Factorial-Denominator Series: Complete Reasoning Record](68/erdos68-factorial-reasoning-surface.pdf) ([source](68/erdos68-factorial-reasoning-surface.tex)) |
| #243 | [Excluding the Bounded Negative Part](243/erdos-243-reciprocal-tail-rigidity.pdf) ([source](243/erdos-243-reciprocal-tail-rigidity.tex)) | [Reciprocal-Tail Rigidity: Complete Reasoning Record](243/erdos243-reciprocal-tail-reasoning-surface.pdf) ([source](243/erdos243-reciprocal-tail-reasoning-surface.tex)) |
| #249 | [A Basis for the 2-Kernel of Euler's Totient](249/erdos-249-binary-totient-series.pdf) ([source](249/erdos-249-binary-totient-series.tex)) | [The Binary Totient Series](249/erdos249-totient-reasoning-surface.pdf) ([source](249/erdos249-totient-reasoning-surface.tex)) |
| #251 | [A Countermodel for Growth-and-Parity Arguments on the Prime-Gap Dyadic Series](251/erdos-251-prime-gap-dyadic-series.pdf) ([source](251/erdos-251-prime-gap-dyadic-series.tex)) | [Prime Gaps and Dyadic Tails: Complete Reasoning Record](251/erdos251-prime-gap-reasoning-surface.pdf) ([source](251/erdos251-prime-gap-reasoning-surface.tex)) |
| #257 | [Weighted Support Criteria for Reciprocal Mersenne Subseries](257/erdos-257-mersenne-support-subseries.pdf) ([source](257/erdos-257-mersenne-support-subseries.tex)) | [Reciprocal Mersenne Subseries](257/erdos257-mersenne-reasoning-surface.pdf) ([source](257/erdos257-mersenne-reasoning-surface.tex)) |
| #269 | [No Finite Separable Representation at Three Prime Generators](269/erdos-269-three-prime-running-lcm.pdf) ([source](269/erdos-269-three-prime-running-lcm.tex)) | [The Three-Prime Running LCM: Complete Reasoning Record](269/erdos269-running-lcm-reasoning-surface.pdf) ([source](269/erdos269-running-lcm-reasoning-surface.tex)) |
| #1041 | [Sharp Solved Families and Constant-Factor Paths in Polynomial Lemniscates](1041/erdos-1041-lemniscate-newton-flow.pdf) ([source](1041/erdos-1041-lemniscate-newton-flow.tex)) | [Lemniscates and Newton Flow: Complete Reasoning Record](1041/erdos1041-lemniscate-reasoning-surface.pdf) ([source](1041/erdos1041-lemniscate-reasoning-surface.tex)) |
| #1049 | [Irrationality of F(31/4) and the Exact Normalized Hankel Order](1049/erdos-1049-rational-base-lambert.pdf) ([source](1049/erdos-1049-rational-base-lambert.tex)) | [Rational-Base Lambert Series: Complete Reasoning Record](1049/erdos1049-rational-base-lambert-reasoning-surface.pdf) ([source](1049/erdos1049-rational-base-lambert-reasoning-surface.tex)) |

## Follow the argument into its evidence

Read the assumptions of the result you want to use, then the proof. The
longer record gives the surrounding working context, including routes that
failed, finite experiments and open obligations. If you cannot reconstruct a
step or find its source, that is useful feedback through
[Contributing](../CONTRIBUTING.md).

Some results are checked in Lean; others are ordinary mathematical arguments
or applications of cited external theorems. Each paper states the boundary for
its own claims. [Results and limits](../docs/RESULTS.md) gives the result beside
what remains open, and the [source map](../docs/SOURCE_MAP.md) connects the
paper to supporting declarations. Lean files are proof authority only for the
exact declarations they check; [`docs/claims.json`](../docs/claims.json)
records the selected public claim interfaces.

The [full-text index](../docs/papers/README.md) provides generated Markdown
versions for browsing. The PDFs and `.tex` files above are the authored
manuscripts. The older joint #249/#257 paper is retained for provenance;
it is not the entry point for either problem.

## Project papers

These papers explain how the work is organised, how an agent uses the public
checkout, and how another researcher can take part. Start with the question
that interests you.

| Question | Paper |
|---|---|
| How do formal proofs, public claims and release checks fit together? | [Problem-Sized Lean Worlds](systems/claim-faithful-publication-systems-paper.pdf) ([source](systems/claim-faithful-publication-systems-paper.tex)) |
| How does an agent find a task, use the tools and record what was checked? | [From a Cold Clone to a Proof Receipt](systems/cold-clone-to-proof-receipt.pdf) ([source](systems/cold-clone-to-proof-receipt.tex)) |
| How can people contribute research or compute while keeping evidence and credit? | [From Spare Compute to Cumulative Mathematics](systems/open-source-mathematics-strategy.pdf) ([source](systems/open-source-mathematics-strategy.tex)) |

For the repository layout, sources of truth, build path, and release
infrastructure, see [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).
The companion [Plectis software repository](https://github.com/wcook04/plectis)
contains the general workflow components discussed alongside the mathematics.

## Sources and earlier manuscripts

The manuscript layer (the `.tex` sources and rendered PDFs) is licensed
CC-BY-4.0; see [`REUSE.toml`](../REUSE.toml) at the repository root.

<details>
<summary>Source note for the #251 sparse construction</summary>

For #251, the elementary pair identities live in
`SparseRationalisationCore.lean`; the ordinary schedule sketch is Proposition
1.1 of the short paper. There is no separately published
`SparseRationalisation.md`. End-to-end sparse Lean candidates are labelled
UNRUN and are not presented as verified.

</details>

<details>
<summary>Earlier combined manuscript: provenance only</summary>

The older joint #249/#257 paper is retained for provenance; it is not the
entry point for either problem. Its arguments and release history can be
inspected in the [archived PDF](archive/erdos249-257-main-paper.pdf) and
[LaTeX source](archive/erdos249-257-main-paper.tex). Use the individual papers
above for the current work.

</details>

<details>
<summary>Commands for agents following a paper into the source</summary>

### Returning from a problem note to checked evidence

The notes are exposition, not proof authority.  To return from any note to the
machine-owned problem record, run the matching route below.  Each problem route
returns its exact paper/source record, checked module inventory, and open
obligation handles; the [complete eight-problem source map](../docs/SOURCE_MAP.md#complete-eight-problem-return-matrix)
keeps the same joins readable.  For a source-fingerprinted continuation packet,
use the route-memory command in the last column.

| Problem | Public problem route | Resumable route-memory handoff |
|---|---|---|
| #68 | `python3 scripts/query_corpus.py --route erdos_68` | `python3 scripts/query_route_memory.py --problem 68` |
| #243 | `python3 scripts/query_corpus.py --route erdos_243` | `python3 scripts/query_route_memory.py --problem 243` |
| #249 | `python3 scripts/query_corpus.py --route erdos_249` | `python3 scripts/query_route_memory.py --problem 249` |
| #251 | `python3 scripts/query_corpus.py --route erdos_251` | `python3 scripts/query_route_memory.py --problem 251` |
| #257 | `python3 scripts/query_corpus.py --route erdos_257` | `python3 scripts/query_route_memory.py --problem 257` |
| #269 | `python3 scripts/query_corpus.py --route erdos_269` | `python3 scripts/query_route_memory.py --problem 269` |
| #1041 | `python3 scripts/query_corpus.py --route erdos_1041` | `python3 scripts/query_route_memory.py --problem 1041` |
| #1049 | `python3 scripts/query_corpus.py --route erdos_1049` | `python3 scripts/query_route_memory.py --problem 1049` |


</details>

## Build and update

Run from the repository root, with Tectonic or a TeX Live installation:

```sh
make -C paper
```

The Makefile builds the manuscripts registered in
[`docs/publication_contract.json`](../docs/publication_contract.json) and
copies the PDFs into their problem or systems directory under `paper/`.
The temporary build PDFs in `paper/` are not the published copies.

After editing a manuscript, rebuild its PDF before updating its recorded
digests. The following command previews digest changes; add `--apply` only
after reviewing the source and rebuilt PDF:

```sh
python3 scripts/check_publication_contract.py --restamp
```

The statement links inside a paper identify the exact proof-source revision
used for that paper. They serve reproducibility. They are not a reason to
keep an older manuscript on the reading path. When the source changes, update
the explanation and source links together, rebuild the PDF, and check its
coverage against the current proofs:

```sh
python3 scripts/check_problem_note_sources.py --coverage
python3 docs/papers/check_paper_corpus.py
```

The last check rejects a Markdown mirror or recorded PDF that no longer
matches its manuscript. Include the edited source, rebuilt PDF and check
output in your pull request. If the remaining failure is a generated copy
made stale by your manuscript edit, say so in the pull request; do not
hand-edit the copy to make the check pass.

Maintainers refresh the generated full text and paper-corpus records through
their export step, then run `python3 scripts/refresh_projections.py` and
`python3 docs/papers/check_paper_corpus.py` before merging. The full-text
exporter is not included in this checkout. You do not need access to a private
repository to propose a manuscript change; include the check output so the
maintainer can complete that part of the update.
