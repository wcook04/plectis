<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Plectis: research on eight Erdős problem programmes

Plectis is an open-source, AI-assisted prototype for turning mathematical
exposition into further research. Eight Erdős programmes offer papers, Lean
source, methods and failed routes for others to question and extend.

Start with [#257's short paper](paper/257/erdos-257-mersenne-support-subseries.pdf).
If `h_P(a)` is the part of an exponent `a` supported on a finite nonempty set of primes,
the Lean-checked theorem proves irrationality at every integer base for each
infinite support `A` with finite base-two weighted mass
`∑_{a∈A} h_P(a)/(a(2^{h_P(a)}−1))`. Some such supports have divergent
`∑_{a∈A} 1/a`. The question for *every* infinite support remains open.
[Longer proof record](paper/257/erdos257-mersenne-reasoning-surface.pdf) ·
[Lean declaration](lean/ErdosProblems/Erdos257/PaperCompleteR8/WeightedReturn.lean#L120).
Other seven programmes: [results guide](docs/RESULTS.md#problem-by-problem-guide).

[#257 exercise](docs/research-commons/PROVE2ME_WEIGHTED_257_PACKET.md#try-changing-a-hypothesis) · [#243/#257 proofs](docs/research-commons/README.md#native-prove2me-theorems).

Start with the [paper](paper/257/erdos-257-mersenne-support-subseries.pdf),
[an exact-rational test you can vary](research/experiments/choices_contraction/README.md#the-probe)
(not the weighted theorem), or [return a question or correction](CONTRIBUTING.md#return-what-you-learned).

**[All papers](paper/README.md)** ·
[Reading edition](docs/reading-edition/README.md) ·
[Replay #257 theorem](docs/verification/EXTERNAL_VERIFICATION_REPLAY.md#reviewer-replay) ·
[Contribute or correct](CONTRIBUTING.md)

![Eight Erdős problem programmes: papers, checked results, failed routes, and questions another researcher can continue](.github/system-map.png)

**Using the degree-seven polynomial constructed by the erdosproblems.com
contributor ani, Lean proves that every preconnected strict-lemniscate set
containing two distinct roots has one-dimensional Hausdorff measure greater
than two. This refutes the exact Formal Conjectures path-image-length
statement; the separate total-variation bound is also checked. The other
seven targets remain open. Independent human review of correspondence with
the 1958 wording has not been recorded. Comparator checks only selected exact
statements, axioms and kernel acceptance; it does not assess novelty or
historical correspondence.**

Attribution: [ani's 7 September 2026 forum post](https://www.erdosproblems.com/forum/thread/1041#post-8861).

See [Formal Conjectures work](#formal-conjectures-contributions).

## Where to start

**Read the mathematics. Find what comes next.** Use the papers and research
records to continue a question or develop a new direction. Work with your own
AI or without one; returned work keeps its sources, checks and credit visible.

- **Explore with your AI, no clone needed.** Give your model the
  [reading edition](docs/reading-edition/README.md): one file with an
  introduction, a short research instruction and the opening of each paper.
  [One open investigation](research/experiments/choices_contraction/README.md)
  shows the route and ends with five ways to continue it.
- **Work in the repository.** The
  [agent quickstart](docs/agents/README.md#start-with-current-public-work)
  provides clone commands and a copyable prompt. Name a question, or ask your
  agent to read the corpus and decide what is worth developing. The
  [agent-navigation paper](paper/systems/cold-clone-to-proof-receipt.pdf)
  explains the workbench design.
- **Test a rational candidate with Python 3, no Lean.** From a clone, run
  `python3 research/experiments/choices_contraction/rational_membership_probe.py --target 189/388 --depth 16 17 --horizon 160`.
  The exact output shows no exclusion through step 16 and a strict gap at
  step 17, ruling out this rational as a subsum of `1/(2^n-1)`. Change
  `--target` to test your own positive fraction; the
  [probe guide](research/experiments/choices_contraction/README.md#the-probe)
  explains the outcomes and host choices. Surviving a finite depth never
  proves membership, and this test does not settle Problem 257.

The short papers explain results; longer records keep calculations and failed
routes. Both are readable without Lean. [A reader's way in](docs/READING_GUIDE.md)
introduces the questions; [Results and limits](docs/RESULTS.md) names what remains open.

Use the [source map](docs/SOURCE_MAP.md) to follow a statement into Lean, the
proof assistant that checks its formal proof. [CONTRIBUTING](CONTRIBUTING.md)
explains how to return work with credit. No model account or private system is
required to [follow one claim](docs/REPRODUCIBILITY.md#try-one-claim-without-lean).

## Why this exists

I prioritised expository quality and a collaborative structure so others can
work on these questions with me. The records include routes that stopped at a
precise obstruction, where another researcher can test or repair the argument.

I am responsible for all claims, sources and the release. Plectis is an
independent, AI-assisted prototype, not something I am declaring finished.
It has had no independent mathematical review. Meaning, novelty and significance
still need human judgement; corpus counts are navigation counts, not novelty claims.

## Problem papers

For a first look, start with **#257**: Lean checks weighted support conditions
for irrational reciprocal Mersenne subseries at every integer base, including
some supports with divergent reciprocal sum. Erdős stated the simpler
reciprocal-summable extension; Lean checks it here. The unrestricted question
remains open. **#249** gives exact ranks of totient kernels. Each paper names
its ordinary proofs, Lean-checked results and open questions.

For **#243**, Lean checks irrationality of the reciprocal sum of a strictly
increasing positive integer sequence under
`a_n²/a_(n+1) = 1 + 3/n + o(n⁻³)` in zero-based indexing. The paper gives the
one-based finite-prefix argument and a bounded-increment criterion for an
eventual Sylvester tail. The unrestricted question remains open.

For **#1049**, the paper proves irrationality of
`F(a/b) = ∑_(n≥1) 1/((a/b)^n−1)` for coprime `a>b≥1` when
`log b/log a < 0.4056830213840605…`, using Zudilin's forms with cyclotomic
cancellation and denominator accounting. Lean checks the region theorem and
`F((31/4)^r)` for positive integers `r`. The earlier Bundschuh–Väänänen
sufficient bound excludes `31/4`; irrationality at `3/2` remains open.

**Reading the eight together.** The [cross-problem paper](paper/synthesis/optimal-sparse-perturbations.pdf)
studies entire `f(z) = ∑_(n≥1) e_n z^n/n!` with nonnegative integer
`e_n≤n^c` eventually and `q|e_n` eventually for each integer `q≥1`.
For `c>0`, integer `d≥1`, the set of vectors
`(f(1), …, f^(d−1)(1))` has Hausdorff dimension `min(c,d)` and contains an
open set exactly when `c>d`. The proof is ordinary.

| Problem | Topic | Papers |
|---|---|---|
| [#68](https://www.erdosproblems.com/68) | [Factorial-denominator irrationality](https://wcook04.github.io/plectis/maths/problems/erdos_68.html) | [short paper](paper/68/erdos-68-factorial-denominator-irrationality.pdf) · [longer paper](paper/68/erdos68-factorial-reasoning-surface.pdf) |
| [#243](https://www.erdosproblems.com/243) | [Cubic-rate irrationality and reciprocal tails](https://wcook04.github.io/plectis/maths/problems/erdos_243.html) | [short paper](paper/243/erdos-243-reciprocal-tail-rigidity.pdf) · [longer paper](paper/243/erdos243-reciprocal-tail-reasoning-surface.pdf) |
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

Contribute an idea, correction, counterexample, checked failed route,
explanation or infrastructure change. You need not solve a problem or write
Lean. Will can help formalise an argument while keeping each contribution's
attribution.

Start with [a paper](docs/CONTRIBUTE_BY_PAPER.md),
[develop a method](paper/synthesis/README.md), or
[improve the machinery](docs/research-commons/ARCHITECTURE_CONTRIBUTIONS.md).
The [submission and credit process](CONTRIBUTING.md#return-what-you-learned)
also covers email and work without a clone.

- **Ideas, corrections or review:** use the
  [research-progress form](https://github.com/wcook04/plectis-erdos/issues/new?template=research_progress.yml)
  or [email me](https://wcook04.github.io/plectis/#contact).
- **Changes to the repository:** follow [CONTRIBUTING](CONTRIBUTING.md).
- **Your own agent and spare compute:** use the [frontier relay](docs/FRONTIER_RELAY.md)
  to choose a starting point and return what you find with its evidence.

Accepted work receives a public receipt naming its contributor and evidence.
The [credit policy](docs/research-commons/CREDIT_POLICY.md) and
[source attributions](docs/research-commons/SOURCE_ATTRIBUTIONS.md) explain credit.

If you solve a problem, the credit and the result are all yours. If this repo
or my intermediary progress helped, please cite this release and say how, so
others find it and we make progress together instead of hoarding partial
results out of fear of being scooped, or rebuilding the same infrastructure
instead of improving one cumulatively.

<a id="citation-and-prior-work"></a>

## Read or verify locally

[REPRODUCIBILITY](docs/REPRODUCIBILITY.md) owns clone, claim-inspection and proof
build instructions. The clone is hundreds of megabytes; building proofs also
downloads Lean and Mathlib. Cloning runs no project code; the
[security policy](.github/SECURITY.md) explains the execution boundary.

Use the [documentation index](docs/README.md) for the file map and specialist
guides. [How the repository works](docs/ARCHITECTURE.md) explains the roles of
proofs, papers and checks. Coding agents start at [`AGENTS.md`](AGENTS.md) and
follow the [agent workbench](docs/agents/AGENT_WORKBENCH.md).

<!-- BEGIN generated_corpus_at_a_glance -->
<!-- Generated by scripts/build_corpus_descriptor.py; do not edit this region. -->
<details>
<summary>Corpus inventory and counting limits</summary>

## Corpus at a glance

The reviewed layer a mathematician should judge: 150 curated claim records in 33 contribution families, reaching Lean source through 468 principal declaration links. `docs/SCOPE.md` gives its shape and `docs/RESULTS.md` gives the strongest checked result per problem. The website and the papers are the human reading path.

The rest is engineering inventory. About 87% of the 163,651 declarations (142,668 across 695 modules) are machine-emitted certificate shards: one integer checked prime, one position excluded. The remainder is not all hand-written either.

| Engineering inventory | Current size |
|---|---:|
| Lean modules (the two library roots) | 1,828 |
| Formal results and supporting lemmas | 159,737 |
| Curated claim records | 150 |
| Contribution families | 33 |

Generated shards are counted as formal source and never as separate
mathematical claims. Claim records cover every status, including cited and
open, and are partitioned once.
These are navigation counts, not novelty claims. They still need expert validation.

</details>
<!-- END generated_corpus_at_a_glance -->

## Formal Conjectures contributions

Four merged changes: [#257](https://github.com/google-deepmind/formal-conjectures/pull/6506),
[#258](https://github.com/google-deepmind/formal-conjectures/pull/5034), and
[#1049](https://github.com/google-deepmind/formal-conjectures/pull/6507) proof links
for solved variants of Erdős's 1948 theorem; a [#1041 correction](https://github.com/google-deepmind/formal-conjectures/pull/6505)
using ani's counterexample. [Trace the #1041 Lean proof](docs/case-studies/formal-conjectures-1041.md).

<!-- BEGIN generated_principal_declaration_anchors -->
<!-- Generated by scripts/build_corpus_descriptor.py; do not edit this region. -->
## Following a result into Lean

The paper links each headline result to the relevant source. For a particular
topic, start with the [source map](docs/SOURCE_MAP.md); it gives the module
order without asking you to decode Lean declaration names first.
<!-- END generated_principal_declaration_anchors -->

## About the project

[Problem-Sized Lean Worlds](paper/systems/claim-faithful-publication-systems-paper.pdf)
describes the research system: each problem kept as a persistent, checkable
record, the path from a proof to a public claim, and the contribution cycle.
[From Spare Compute to Cumulative Mathematics](paper/systems/open-source-mathematics-strategy.pdf)
explains the collaborative research process. Selected external verification
entries live in [plectis-erdos-lean](https://github.com/wcook04/plectis-erdos-lean).
The mathematics and tools in this checkout are self-contained.

## Citation and licence

Use [CITATION.cff](CITATION.cff) to cite release `v0.10.0`, and give your commit
for work beyond it. Cite the relevant [problem paper](paper/README.md) and its
original sources for mathematics. [Prior art](docs/PRIOR_ART.md) and
[source attributions](docs/research-commons/SOURCE_ATTRIBUTIONS.md) distinguish
earlier results, formalisation and local use; a repository citation does not
replace the original author's credit.

Code, scripts and documentation are Apache-2.0; manuscript sources and PDFs
are CC-BY-4.0. [REUSE.toml](REUSE.toml) records exceptions. See also
[scope](docs/SCOPE.md), [privacy](docs/PRIVACY.md) and the
[code of conduct](.github/CODE_OF_CONDUCT.md).
