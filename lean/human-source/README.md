<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Plectis: research on eight open Erdős problems

![Eight open problems: papers, checked results, failed routes, and open questions another researcher can continue](.github/system-map.png)

We focused on eight arbitrarily hard Erdős problems:
[68](https://www.erdosproblems.com/68),
[243](https://www.erdosproblems.com/243),
[249](https://www.erdosproblems.com/249),
[251](https://www.erdosproblems.com/251),
[257](https://www.erdosproblems.com/257),
[269](https://www.erdosproblems.com/269),
[1041](https://www.erdosproblems.com/1041) and
[1049](https://www.erdosproblems.com/1049). **All eight problems remain open.** This repository does
not solve any of them. It holds formal statements, Lean checks, a Comparator
gate and a Palomar submission, and two papers per problem, one short and one
long, written with Terence Tao's public guidance on how AI mathematics should
be expositioned in mind.

I prioritised expository quality and a collaborative structure over trying to
solve the problems; I hope to now solve them with others rather than alone. With
the unreleased frontier models, these could probably be solved if enough
compute were poured at them. The difference here is that we show every one of
the routes that stopped, and try to turn intermediary findings into something reusable
by mathematicians who actually understand the material, and by later models.
Meaning, novelty and significance still need human judgement.

The repo substrate is built by and for AI agents; I would not recommend driving it by hand
with commands. Its navigation, validation, contribution and
mathematical-reasoning workflows plug into your own agents. Progress varies by
problem and is stated in [RESULTS](docs/RESULTS.md) and the source records your
agent can find for you. Lean checks the formal statements. Coverage is not the
100% I wanted, because I am officially out of money and time. Anyone can
contribute, even by formalising maths already established analytically, and
receive due credit.

I am responsible for all claims, sources and the release. Plectis is an independent, AI-assisted prototype, not
something I am declaring finished. It has had no independent mathematical
review (trying to get this), and I need help to get anywhere near "done".

If you solve a problem, the credit and the result are all yours. If this repo or my
intermediary progress helped, please cite this release and say how, so others
find it and we make progress together instead of hoarding partial results out
of fear of being scooped, or rebuilding the same infrastructure instead of
improving one cumulatively (infra suggestions also get credit!).

The [website](https://wcook04.github.io/plectis/) is the homosapien-ergonomic way to
browse: the [mathematics pages](https://wcook04.github.io/plectis/maths/) give
each short paper, each long paper, and a map to the relevant Lean sources. The
API behind its backend is machine generated so nothing hard-coded drifts (hopefully!).

Ways in:

- **Read** a problem in [A reader's way in](HUMAN_ENTRY.md), a command-free
  tour of the problems and the evidence boundary.
- **Check** a stated result with the claim verifier in
  [REPRODUCIBILITY](docs/REPRODUCIBILITY.md).
- **Continue** from where I left off: a bounded research shift from one exact
  public revision, via the [frontier relay](docs/FRONTIER_RELAY.md) and
  [CONTRIBUTING](CONTRIBUTING.md). Use a coding agent. This is the part I am
  most excited about.
- **Experts:** [email me](https://wcook04.github.io/plectis/#contact) any
  insight. I will do the work and fully credit you for the insight and whatever
  follows from it.

## Problem papers

For a first look from a maths generalist, start with **#257** for full-support irrationality and
achievement-set measure, or **#249** for exact kernel rank, finite certificates
and recorded failed routes.

- **[#68](https://www.erdosproblems.com/68)** · Factorial-denominator irrationality ·
  [short paper](erdos-68-factorial-denominator-irrationality.pdf) ·
  [longer paper](erdos68-factorial-reasoning-surface.pdf).
  Irrationality is equivalent to cofinally many non-unit factorial carries;
  producing those carries remains open.
- **[#243](https://www.erdosproblems.com/243)** · Reciprocal-tail rigidity ·
  [short paper](erdos-243-reciprocal-tail-rigidity.pdf) ·
  [longer paper](erdos243-reciprocal-tail-reasoning-surface.pdf).
  After Koizumi's normalised vanishing, a bounded or summably small negative
  centred error forces eventual Sylvester recurrence. The unbounded mixed-sign
  regime remains open.
- **[#249](https://www.erdosproblems.com/249)** · Binary totient series ·
  [short paper](erdos-249-binary-totient-series.pdf) ·
  [longer paper](erdos249-totient-reasoning-surface.pdf).
  Exact dyadic-kernel rank `2^e + 1`, denominator exclusion to about
  `7.96 × 10³⁴`, diagonal certificates through `t ≤ 82`, and no-go theorems
  for the shortcuts. The infinitely many witnesses for irrationality are not
  produced.
- **[#251](https://www.erdosproblems.com/251)** · Prime-gap dyadic series ·
  [short paper](erdos-251-prime-gap-dyadic-series.pdf) ·
  [longer paper](erdos251-prime-gap-reasoning-surface.pdf).
  The prime series equals the gap series; irrationality is equivalent to
  cofinal non-integral tail shifts. The actual-prime tail witness remains open.
- **[#257](https://www.erdosproblems.com/257)** · Mersenne-support subseries ·
  [short paper](erdos-257-mersenne-support-subseries.pdf) ·
  [longer paper](erdos257-mersenne-reasoning-surface.pdf).
  Irrationality for the full support in every integer base `b ≥ 2`, and for
  structured supports under summability; the base-2 Mersenne achievement set has
  measure one. Every infinite support, and the `1/2` and `1/21` branches,
  remain open.
- **[#269](https://www.erdosproblems.com/269)** · Three-prime running LCM ·
  [short paper](erdos-269-three-prime-running-lcm.pdf) ·
  [longer paper](erdos269-running-lcm-reasoning-surface.pdf).
  Three-prime height identity, nonsingular kernel minors, and the `(2,3,5)`
  minor `-1/15`. The two-prime transcendence argument in the longer paper is
  Steve Fan's ([erdosproblems.com/269](https://www.erdosproblems.com/forum/thread/269),
  26 June 2026, before this note); no priority or Lean theorem is claimed. Three
  or more primes remain open.
- **[#1041](https://www.erdosproblems.com/1041)** · Lemniscates and Newton flow ·
  [short paper](erdos-1041-lemniscate-newton-flow.pdf) ·
  [longer paper](erdos1041-lemniscate-reasoning-surface.pdf).
  Newton-flow decay, arbitrarily small translations that separate ray arguments,
  and perturbative root retention. A length-`<2` curve, and the hub that would
  make one, remain open.
- **[#1049](https://www.erdosproblems.com/1049)** · Rational-base Lambert series ·
  [short paper](erdos-1049-rational-base-lambert.pdf) ·
  [longer paper](erdos1049-rational-base-lambert-reasoning-surface.pdf).
  Exact rational-base tail recurrence, sharp Hankel order, and a checked height
  region that includes `31/4`. No irrationality at `3/2`; the approximant
  construction remains open.

The [joint #249/#257 manuscript](erdos249-257-main-paper.pdf) is kept for
archive and provenance only (OG ones I did); the papers above are the current entrances.

## What the checks establish

Three things come between a Lean proof and a claim in this repo (agents advised!). The
[comprehension graph](docs/semantic/README.md) is the map: every declaration in
the atlas, the statements they make, and typed relations between them, so you
or your agent can see that a theorem is a reformulation or finite instance of
the open problem rather than the problem itself. Comparator is a second
formal check: nineteen proof-bearing modules against separately declared
statements and a fixed axiom budget, with [`formalization.yaml`](formalization.yaml)
recording source, boundary, `sorry` count and axioms for each. Palomar is
where the release is submitted for outside registry and review;
[`docs/PALOMAR_RESULT_SHOWCASE.json`](docs/PALOMAR_RESULT_SHOWCASE.json) owns
the reader-priority ranking that goes with it.

The [verification dossier](docs/EXTERNAL_VERIFICATION.md) covers all eight
problem programmes; the [methodology](METHODOLOGY.md) outlines what each check does
and does not establish. [`docs/claims.json`](docs/claims.json) covers claim
status and [prior art](docs/PRIOR_ART.md) records earlier and subsuming work (WIP, out of tokens).
None of it decides whether a statement captures the intended problem, is new,
or solves anything, which requires expert review (credit offered for this).

Two papers explain the design. [Problem-Sized Lean Worlds](claim-faithful-publication-systems-paper.pdf)
is how finding a result, checking it and deciding what may be claimed are kept
separate, just the repo paper really. [From Spare Compute to Cumulative Mathematics](open-source-mathematics-strategy.pdf)
is why the work is public and how credit is recorded, basically the open source idea I had.

## Contribute

An idea, a correction, a counterexample, a failed route with a checkable
reason, clearer exposition, a validation/invalidation of a claim or a repaired check all count. Open the
[plain-language research-progress form](https://github.com/wcook04/plectis-erdos/issues/new?template=research_progress.yml)
with no patch — a coding agent can fill it; the questions are ordinary
language — or a pull request for a focused change. Accepted work gets a
public receipt naming you, the exact files or results, the starting commit, and
what was checked. The [credit policy](docs/research-commons/CREDIT_POLICY.md)
gives the exact boundary. You can also just email me anything and I will credit you myself if that's a pain.

## Read or verify locally

Every command your agent can run lives in [REPRODUCIBILITY](docs/REPRODUCIBILITY.md) and the
[agent workbench](docs/AGENT_WORKBENCH.md), not here: claim verifier, reader-only
and quick Lean checkouts, complete proof source, full release replay. [ARCHITECTURE](ARCHITECTURE.md) and the
[source map](docs/SOURCE_MAP.md) assume no Lean and no project history.

Cloning runs no project code; there are no submodules, Git LFS filters or
hooks. Proof builds run the pinned Lean toolchain and Mathlib.
[SECURITY](SECURITY.md) explains the boundary and the private reporting route.
Agents arriving cold start at [`AGENTS.override.md`](AGENTS.override.md); the
[agent-navigation paper](cold-clone-to-proof-receipt.pdf) explains that design.

## Citation and licence

Cite release `v0.9.0` via [CITATION.cff](CITATION.cff). Code, scripts, and
documentation are Apache-2.0. The manuscript layer, including the paper source
and rendered PDFs, is CC-BY-4.0. Prior work and the MIT-0 wrapper are recorded
in [REUSE.toml](REUSE.toml) and the [licence texts](LICENSES/Apache-2.0.txt).
[SCOPE](SCOPE.md) defines the corpus; [`CONTRIBUTING.md`](CONTRIBUTING.md)
covers corrections.
[Where I actually am](HUMAN_ENTRY.md#where-i-actually-am) says why this is
being released now.

<!-- BEGIN generated_corpus_at_a_glance -->
<!-- Generated by scripts/build_corpus_descriptor.py; do not edit this region. -->
## Corpus at a glance

The layer a mathematician should judge has been denoised (tried): 140 curated claim records in 30 contribution families, reaching Lean source through 449 principal declaration links. `SCOPE.md` gives its shape and `docs/RESULTS.md` gives the strongest checked result per problem. Again, agents advised, website or papers are what's designed for humans.

The rest is engineering inventory. About 91% of the 156,245 declarations (142,668 across 695 modules) are machine-emitted certificate shards: one integer checked prime, one position excluded. The remainder is not all hand-written either.

| Engineering inventory | Current size |
|---|---:|
| Lean modules (the two library roots) | 1,274 |
| Formal results and supporting lemmas | 153,502 |
| Curated claim records | 140 |
| Contribution families | 30 |

Generated shards are counted as formal source and never as separate
mathematical claims. Claim records cover every status, including cited and
open, and are partitioned once.
These are navigation counts, not novelty claims; this needs expert validation, again: credit provided for this. With funding I would also be happy to provide some kind of compensation, alas, currently challenged in that department.
<!-- END generated_corpus_at_a_glance -->

<!-- BEGIN generated_principal_declaration_anchors -->
<!-- Generated by scripts/build_corpus_descriptor.py; do not edit this region. -->
## Following a result into Lean

The paper links each headline result to the relevant source. For a particular
topic, start with the [source map](docs/SOURCE_MAP.md); it gives the module
order without asking you to decode Lean declaration names first.
<!-- END generated_principal_declaration_anchors -->
