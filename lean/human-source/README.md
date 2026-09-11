<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Plectis: research on eight open Erdős problems

Plectis is an open-source, AI-assisted research project organised around eight
open Erdős problems. This repository brings together the papers, Lean proofs,
computations, failed approaches, and questions that remain, so another
researcher or coding agent can inspect the work and continue from it.
**All eight problems remain open.** This repository does not solve them.

**[Visit the website](https://wcook04.github.io/plectis/)** ·
**[Explore the mathematics](https://wcook04.github.io/plectis/maths/)** ·
[Browse all papers](https://wcook04.github.io/plectis/docs/papers.html) ·
[About the project](https://wcook04.github.io/plectis/#why) ·
[Contact me](https://wcook04.github.io/plectis/#contact)

![Eight open problems: papers, checked results, failed routes, and questions another researcher can continue](.github/system-map.png)

## Why this exists

I prioritised expository quality and a collaborative structure over trying to
solve the problems; I hope to now solve them with others rather than alone.
The idea is to turn intermediary findings into something reusable by
mathematicians who actually understand the material, and by later models.
That includes the routes that stopped and the reasons they stopped.

The tools for navigation, proof checking, experiments and credit are here
so another contributor does not have to build them again.

I am responsible for all claims, sources and the release. Plectis is an
independent, AI-assisted prototype, not something I am declaring finished.
It has had no independent mathematical review (trying to get this), and I
need help to get anywhere near "done". Meaning, novelty and significance still
need human judgement.

Two papers explain the project:

- **[From Spare Compute to Cumulative Mathematics](paper/systems/open-source-mathematics-strategy.pdf)**
  explains the open-source idea, how different contributions can help, and how
  credit is recorded.
- **[Problem-Sized Lean Worlds](paper/systems/claim-faithful-publication-systems-paper.pdf)**
  explains how the research is organised and how finding a result, checking it,
  and deciding what may be claimed are kept separate.

## Where to start

The [website](https://wcook04.github.io/plectis/) is the homosapien-ergonomic way
to browse: the [mathematics pages](https://wcook04.github.io/plectis/maths/)
give each short paper, each long paper, and a map to the relevant Lean sources.

- **Read:** [A reader's way in](HUMAN_ENTRY.md) is a command-free tour of the
  problems and what the evidence establishes.
- **Check:** [RESULTS](docs/RESULTS.md) summarises progress; the
  [source map](docs/SOURCE_MAP.md) and [REPRODUCIBILITY](docs/REPRODUCIBILITY.md)
  take you to the formal statements and checks.
- **Continue from where I left off:** use the [frontier relay](docs/FRONTIER_RELAY.md)
  and [CONTRIBUTING](CONTRIBUTING.md). Use a coding agent. This is the part I
  am most excited about.

The repository's navigation, validation and contribution workflows plug into
your own coding agents via [`AGENTS.override.md`](AGENTS.override.md).
You do not need an agent or Lean to read the papers.

## Problem papers

Each problem has a short paper and a longer research record covering failed
routes, finite evidence, and remaining obligations. For a first look, start
with **#257** for full-support irrationality and achievement-set measure, or
**#249** for exact kernel rank, finite certificates, and recorded routes that
stopped.

### [#68: Factorial-denominator irrationality](https://wcook04.github.io/plectis/maths/problems/erdos_68.html)

[Original question](https://www.erdosproblems.com/68) ·
[Short paper](paper/68/erdos-68-factorial-denominator-irrationality.pdf) ·
[Longer paper](paper/68/erdos68-factorial-reasoning-surface.pdf)

A GMP non-unit carry at `m = 300000` and a continued-fraction bound
`q ≥ 2^39990` are incomparable finite exclusions. Producing cofinal carries
remains open.

### [#243: Reciprocal-tail rigidity](https://wcook04.github.io/plectis/maths/problems/erdos_243.html)

[Original question](https://www.erdosproblems.com/243) ·
[Short paper](paper/243/erdos-243-reciprocal-tail-rigidity.pdf) ·
[Longer paper](paper/243/erdos243-reciprocal-tail-reasoning-surface.pdf)

After Koizumi's normalised vanishing, a bound on the upward steps of the
unreduced integer numerator forces eventual Sylvester recurrence; the
numerator itself need not be assumed bounded. Unbounded upward excursions
of that numerator remain open. Duverney (2001) and the Tao–Kovač line are
prior art on the page; cubic-rate vanishing is not claimed as empty-page
news.

### [#249: Binary totient series](https://wcook04.github.io/plectis/maths/problems/erdos_249.html)

[Original question](https://www.erdosproblems.com/249) ·
[Short paper](paper/249/erdos-249-binary-totient-series.pdf) ·
[Longer paper](paper/249/erdos249-totient-reasoning-surface.pdf)

Bounded-residue series `A_m` are irrational for `m ≥ 3`, with a complete
dyadic-modulus classification ([§2](paper/249/erdos-249-binary-totient-series.pdf);
ordinary mathematics, not Lean). Separately: exact dyadic-kernel rank
`2^e + 1`, denominator exclusion to about `7.96 × 10³⁴`, diagonal
certificates through `t ≤ 82`, and no-go theorems for the shortcuts. This is
not an infinite witness for irrationality.

### [#251: Prime-gap dyadic series](https://wcook04.github.io/plectis/maths/problems/erdos_251.html)

[Original question](https://www.erdosproblems.com/251) ·
[Short paper](paper/251/erdos-251-prime-gap-dyadic-series.pdf) ·
[Longer paper](paper/251/erdos251-prime-gap-reasoning-surface.pdf)

A sparse perturbation of the prime gaps can have a rational dyadic sum
while retaining the prime growth scale, every fixed eventual congruence,
and asymptotically the same short-block statistics. The later positions
are not asserted to be prime. This is complementary to Land's conditional
result, not a refutation; the original problem remains open.

### [#257: Mersenne-support subseries](https://wcook04.github.io/plectis/maths/problems/erdos_257.html)

[Original question](https://www.erdosproblems.com/257) ·
[Short paper](paper/257/erdos-257-mersenne-support-subseries.pdf) ·
[Longer paper](paper/257/erdos257-mersenne-reasoning-surface.pdf)

For every infinite reciprocal-summable support, the Mersenne subseries is
irrational at every integer base `b ≥ 2` (short paper §2; ordinary
mathematics, not Lean). Erdős stated that coprimality-free extension; the
note writes out an averaging proof. Full-support irrationality at every
integer base is classical (Erdős 1948) and Lean-checked here.
The base-2 achievement set has measure one.
Pairwise-coprime plus summable-reciprocal support is Lean. Arbitrary
infinite support, and the `1/2` and `1/21` branches, remain open.

### [#269: Three-prime running LCM](https://wcook04.github.io/plectis/maths/problems/erdos_269.html)

[Original question](https://www.erdosproblems.com/269) ·
[Short paper](paper/269/erdos-269-three-prime-running-lcm.pdf) ·
[Longer paper](paper/269/erdos269-running-lcm-reasoning-surface.pdf)

Steve Fan's two-prime factorisation
([erdosproblems.com/269](https://www.erdosproblems.com/forum/thread/269),
26 June 2026) is his; no priority or Lean theorem is claimed for it. At
three primes, one binary carry produces nonsingular selected kernel minors
of every order. The actual-series reduction is given; the source-specific
cofinal escape remains unproved. Three-prime irrationality remains open.

### [#1041: Lemniscates and Newton flow](https://wcook04.github.io/plectis/maths/problems/erdos_1041.html)

[Original question](https://www.erdosproblems.com/1041) ·
[Short paper](paper/1041/erdos-1041-lemniscate-newton-flow.pdf) ·
[Longer paper](paper/1041/erdos1041-lemniscate-reasoning-surface.pdf)

Every monic trinomial `z^n + a z^m + b` with roots in the open unit disc
has each root-to-origin segment inside `{|f|<1}`, so any two roots join
through the origin with length less than `2`. Separately, a sharp Poisson
critical-value mean holds for zeros in the closed unit disc. Both are
ordinary proofs. Lean checks Newton-flow decay, ray-separating translations,
and perturbative root retention; three solved-family kernels are
Comparator-checked. The unrestricted path problem remains open. Forum
discussion of a degree-7 counterexample is a reported external claim, not a
theorem of this repository.

### [#1049: Rational-base Lambert series](https://wcook04.github.io/plectis/maths/problems/erdos_1049.html)

[Original question](https://www.erdosproblems.com/1049) ·
[Short paper](paper/1049/erdos-1049-rational-base-lambert.pdf) ·
[Longer paper](paper/1049/erdos1049-rational-base-lambert-reasoning-surface.pdf)

An ordinary specialization of Zudilin 2004 proves `F(31/4)` (and its positive
powers) irrational; that headline is not a Lean theorem. Lean checks
supporting height-region arithmetic, the `3/2` corridor exclusion, the
cleared-tail recurrence, and selected Hankel identities. The outstanding
`3/2` obligation is an approximant family with remainder control.

The notes follow Terence Tao's public guidance on writing mathematics produced
with AI assistance; that is a writing standard, not a review of this project.

The [joint #249/#257 manuscript](paper/archive/erdos249-257-main-paper.pdf) is
archive and provenance only; the papers above are the current entrances.

## What the checks establish

Lean checks that a proof establishes the formal statement written in the
source. These records connect the claims to their evidence:

- The [comprehension graph](docs/semantic/README.md) maps declarations,
  their statements, and the relations between them. It helps distinguish a
  reformulation or finite instance from the original open problem.
- **Comparator** gives the 47 selected interfaces in
  [`formalization.yaml`](formalization.yaml) a second formal check. Each
  statement is declared again without its proof, then checked against a
  proof-bearing solution and a fixed axiom budget.
- The [verification dossier](docs/EXTERNAL_VERIFICATION.md) covers all eight
  problem programmes. The [claim records](docs/claims.json) give public claim
  status, and [prior art](docs/PRIOR_ART.md) records earlier and subsuming work.

The [methodology](METHODOLOGY.md) explains what each check establishes.
These checks do not decide whether a statement captures the intended problem,
is new, or solves anything. That requires expert review. Do not infer results
from private or unreleased work.

## Contribute

An idea, a correction, a counterexample, a failed route with a checkable
reason, clearer exposition, a validation of a claim or a repaired check all
count. Anyone can contribute, even by formalising maths already established
analytically, and receive due credit. Infra suggestions also get credit!

- **Ideas, corrections or review:** use the
  [research-progress form](https://github.com/wcook04/plectis-erdos/issues/new?template=research_progress.yml)
  or [email me](https://wcook04.github.io/plectis/#contact).
- **Changes to the repository:** open a pull request following
  [CONTRIBUTING](CONTRIBUTING.md).
- **Your own agent and spare compute:** the
  [eight-frontier issue](https://github.com/wcook04/plectis-erdos/issues/105)
  lists starting points. Use the [frontier relay](docs/FRONTIER_RELAY.md) to
  return what you find with its evidence.

Accepted work gets a public receipt. The
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

[REPRODUCIBILITY](docs/REPRODUCIBILITY.md) and the
[agent workbench](docs/AGENT_WORKBENCH.md) contain the commands for checking a
claim, making a small reading or Lean checkout, and replaying a full release.
[ARCHITECTURE](ARCHITECTURE.md) and the [source map](docs/SOURCE_MAP.md)
assume no Lean and no project history.

Cloning runs no project code; there are no submodules, Git LFS filters or
hooks. Proof builds run the pinned Lean toolchain and Mathlib.
[SECURITY](SECURITY.md) explains the boundary.
Agents arriving cold start at [`AGENTS.override.md`](AGENTS.override.md); the
[agent-navigation paper](paper/systems/cold-clone-to-proof-receipt.pdf) explains that design.

<!-- BEGIN generated_corpus_at_a_glance -->
<!-- Generated by scripts/build_corpus_descriptor.py; do not edit this region. -->
## Corpus at a glance

The reviewed layer a mathematician should judge: 141 curated claim records in 30 contribution families, reaching Lean source through 451 principal declaration links. `SCOPE.md` gives its shape and `docs/RESULTS.md` gives the strongest checked result per problem. The website and the papers are the human reading path.

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
<!-- END generated_corpus_at_a_glance -->

<!-- BEGIN generated_principal_declaration_anchors -->
<!-- Generated by scripts/build_corpus_descriptor.py; do not edit this region. -->
## Following a result into Lean

The paper links each headline result to the relevant source. For a particular
topic, start with the [source map](docs/SOURCE_MAP.md); it gives the module
order without asking you to decode Lean declaration names first.
<!-- END generated_principal_declaration_anchors -->

## The wider project

The [Plectis software repository](https://github.com/wcook04/plectis) contains
runnable tools from the research system. The [software guide](https://wcook04.github.io/plectis/docs/index.html)
explains what they do and how to try them. The maths papers and proofs are
self-contained in this repository.

## Citation and licence

Cite release `v0.10.0` via [CITATION.cff](CITATION.cff). Code, scripts, and
documentation are Apache-2.0. The manuscript layer, including the paper source
and rendered PDFs, is CC-BY-4.0. Prior work and the MIT-0 wrapper are recorded
in [REUSE.toml](REUSE.toml) and the [licence texts](LICENSES/Apache-2.0.txt).
[SCOPE](SCOPE.md) defines the corpus; [`CONTRIBUTING.md`](CONTRIBUTING.md)
covers corrections.
