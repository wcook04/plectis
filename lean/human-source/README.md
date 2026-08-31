<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Plectis: a public frontier across eight open Erdős problems

Plectis is an AI-assisted mathematical research system. Its public
proof corpus for Erdős Problems 68, 243, 249, 251, 257, 269, 1041, and 1049.
It contains exact reductions, model families, theorems,
countermodels, method boundaries, and certificates. **It does not solve them. All eight problems remain open.**
Each programme states what is checked and what still blocks the question.

**Start with the mathematics.** Read the [eight-programme verification map](docs/EXTERNAL_VERIFICATION.md),
then inspect one proof handle. No Lean build is needed for the first check:

```bash
python3 scripts/verify_claims.py --claim eb_full_support
```

The command prints the statement, re-resolves its declaration, names any
Comparator interface and paper, shows the release receipts, and states where
the claim stops. Most claims intentionally have no Comparator interface.
`--verify-all` checks all 103 claims and 335 declarations in about a fifth of a
second. [Read or run it](#read-or-run-it) lists the routes that do need Lean.

[RESULTS](docs/RESULTS.md) → [SCOPE](SCOPE.md) → [SOURCE MAP](docs/SOURCE_MAP.md)
→ [prior art and attribution](docs/PRIOR_ART.md)
→ [architecture and repository guide](ARCHITECTURE.md) ·
[printable PDF](claim-faithful-publication-systems-paper.pdf).
It assumes no Lean or project history. The
[agent-navigation paper](cold-clone-to-proof-receipt.pdf) audits the
cold-clone route and the recorded workbench session.

The repository began with #249 and #257 and keeps that name so old citations
continue to resolve. Those are reviewed headline programmes, not the whole
corpus. The companion [Plectis](https://github.com/wcook04/plectis) repository
owns the runnable research tooling and claims no proof authority here. The
[art-led public front door](https://wcook04.github.io/) explains how the system,
the eight programmes, the papers, and this proof corpus fit together.

**AI assistance and responsibility.** Large-language-model agents drafted and
revised prose, Lean proofs, and repository software. Will Cook set the
objectives, selected and reviewed the public claims and the cited sources, and
is responsible for the release; the tools are not authors. The pinned Lean
kernel checks the exact formal propositions. It does not establish that a
proposition expresses the intended mathematics, that a result is new, or that it
matters: those remain authored judgements, and the papers state them per result.

Routes: [mathematics](docs/RESULTS.md) · [verification](docs/EXTERNAL_VERIFICATION.md)
· [systems](ARCHITECTURE.md) · `query_corpus.py --overview` / `--papers`.

## Problem papers

[`docs/papers/corpus.json`](docs/papers/corpus.json) indexes them by machine.

| Problem | Mathematical statement |
|---|---|
| **#68** | Is `∑_{n≥2} 1/(n!−1)` irrational? |
| **#243** | Does rationality of a rapidly growing integer sequence's reciprocal sum force eventual Sylvester recurrence? |
| **#249** | Is `∑ φ(n)/2ⁿ` irrational? |
| **#251** | Is `∑ p_n/2ⁿ` irrational, equivalently the consecutive-prime-gap dyadic series? |
| **#257** | Is `∑_{n∈A} 1/(2ⁿ-1)` irrational for every infinite `A ⊆ ℕ_{>0}`? |
| **#269** | For at least two primes, is the reciprocal sum of running lcms of the smooth numbers irrational? |
| **#1041** | Must two roots of a monic polynomial in the unit disc admit a curve of length `<2` inside its open unit lemniscate? |
| **#1049** | For which rational bases is the corresponding Lambert-type series irrational, beginning with `3/2`? |

This table is the blank-slate agent and reader inventory: no query is required
to discover which problems exist or what they ask. It is navigation, not proof
authority or a novelty claim. Drilldown is optional and uses only tracked
public files; it does not require `ai_workflow`, a sibling checkout, a private
cache, or network access.

### Public checked frontier; what remains

[**#68: factorial-denominator irrationality**](erdos-68-factorial-denominator-irrationality.pdf).
A checked hypothesis-free equivalence reduces irrationality to one integer
divisibility test failing infinitely often. The kernel-internal denominator
bound is `67`; the `300000` exclusion is a checked implication evaluated
externally. Producing infinitely many failures remains open.

[**#243: reciprocal-tail rigidity**](erdos-243-reciprocal-tail-rigidity.pdf).
Koizumi supplies normalised vanishing for the canonical orbit. Lean then
excludes a bounded negative part and finite normalised negative mass; the
missing negative-part bound and the unbounded mixed-sign regime remain open.

[**#249: dyadic sections of Euler's totient**](erdos-249-binary-totient-series.pdf) · [claim-bounded reasoning surface](erdos249-totient-reasoning-surface.pdf).
For every `k≥2`, the paper derives section-span rank `k^e+1`, explicit bases,
and the relation normal form from Martin plus elementary reductions. Lean checks
the dyadic theorem and all-base arithmetic, residue coordinates, canonical
spanning, and exact rank conditional on linear independence; Martin and that
independence are not formalised. Coons already implies infinite rank. Reduced
denominators through `79,639,646,646,701,375,323,355,774,875,831,053` and
diagonal scales through `t=82` are excluded; no `t=83` or unbounded producer is
proved.

[**#251: prime-gap dyadic series**](erdos-251-prime-gap-dyadic-series.pdf).
Summability and the prime-gap identity are checked unconditionally via an
elementary polynomial prime bound; for any sequence obeying the checked tail
recurrence, irrationality is exactly equivalent to cofinal non-integral tail
shifts. The concrete prime-tail bridge remains open; no theorem produces the
required cofinal adjacent small-mismatch gap pairs.

[**#257: reciprocal Mersenne subseries**](erdos-257-mersenne-support-subseries.pdf) · [claim-bounded reasoning surface](erdos257-mersenne-reasoning-surface.pdf).
Lean checks full support, finite-period noncollapse, and exact restricted-set
coding, topology, perfectness, and measure. Prime support at base `2` and
squarefree support at power-of-two bases are cited prior results. Universal #257
and the `1/2` and `1/21` targets remain open.

[**#269: three-prime running least common multiple**](erdos-269-three-prime-running-lcm.pdf).
For every two-prime set, both the de-duplicated and repeated sums are
transcendental, by a paper argument using Loxton–van der Poorten in the
Bugeaud–Laurent form. **This is not first and not formalised.** Steve Fan posted
the same factorisation and conclusion on the erdosproblems.com #269 discussion
page on 26 June 2026; this note was first released publicly on 22 July 2026.
This project therefore claims no priority for the two-prime theorem, and no Lean
declaration asserts it. From three primes onward the problem remains open; Lean
checks exact structure and a conditional carry consumer, not the
rationality-to-carry bridge, cofinal escape, or unbounded denominator exclusion.

[**#1041: short connections inside polynomial lemniscates**](erdos-1041-lemniscate-newton-flow.pdf).
Newton-flow value decay, the ray-separation consumer (connection decay is its
hypothesis), the translation collision locus, and quantitative root-retention
bounds are checked. The printed proof of a recent claimed spanning-tree
decomposition has an invalid local saddle block (a proof gap, not a
counterexample); repairing the topology and metric gluing remains open.

[**#1049: multiplicative obstructions at base 3/2**](erdos-1049-rational-base-lambert.pdf).
Lean checks construction-specific no-go theorems, four-jet cancellation, and
direct-clearing obstructions at `3/2`, plus the elementary height inequality used
by Bundschuh–Väänänen's external criterion at `7/2`. It proves no irrationality
result; `3/2`, the primitive noncollapsed construction, and analytic remainder
control remain open.

[Retained joint #249/#257 exposition](erdos249-257-main-paper.pdf) ·
[![Lean CI](https://github.com/wcook04/plectis-lean-erdos249-257/actions/workflows/lean.yml/badge.svg)](https://github.com/wcook04/plectis-lean-erdos249-257/actions/workflows/lean.yml)

## External verification

Nineteen selected Lean propositions are declared a second time, without proofs,
in [`ExternalVerification/Statements.lean`](ExternalVerification/Statements.lean).
Comparator checks the proof-bearing module against those separate declarations
and against a fixed axiom budget of `propext`, `Quot.sound`, and
`Classical.choice`; an adversarial fixture alters one statement and must be
rejected. [`formalization.yaml`](formalization.yaml) records, per selected
result, the contribution class, exact statement, source declaration, boundary,
`sorry` count, and axioms. Manifest and [verification packet](docs/EXTERNAL_VERIFICATION.md)
cover all eight problem programmes; [replay](docs/EXTERNAL_VERIFICATION_REPLAY.md)
gives the reviewer-run Linux route. The same check runs in continuous
integration against the reviewed source commit. Comparator checks propositions
only: no paper deduction, cited theorem, external computation, intended
meaning, novelty, or significance.

[RESULTS](docs/RESULTS.md) gives each strongest checked result and its limit;
[prior art](docs/PRIOR_ART.md) records classical, subsuming, and earlier public
work. The finite #249 result is the
classical Farey/mediant bound (numerical delta `0`): Farey's method supplies
the number directly, exactly the Farey bound, not an improvement. Full-kernel
infinite rank is Coons's prior result, the all-base rank paper theorem uses
Martin externally, and #269's two-prime result is not first.

This self-contained public Plectis checkout is not an entrypoint into any private
development system. `v0.9.0` is the latest tagged release and citation anchor;
[`docs/claims.json`](docs/claims.json) pins the exact formal-source checkpoint
this release ships. Lean source checked by the pinned Lean kernel is
proof authority; do not infer results from private or unreleased work.

## What the formal source establishes

Labels are descriptions, not scores. **Formalised here** means a statement
rendered and kernel-checked in Lean, which for a known theorem is a checked
rendering and not a priority claim; **proved here** means the argument is this
project's. **Verified finite instance** means
Lean checked only the listed inputs; **conditional reduction** means the
conclusion depends on a named open condition.

| Status | Result |
|---|---|
| **formalised here** | For every integer `b ≥ 2`, the full-support series `∑ 1/(bⁿ - 1)` is irrational; Erdős (1948) is a checked rendering rather than a new result. Several named infinite-support families are also formalised; this does not cover every infinite support. |
| **formalised here** | The base-2 Mersenne achievement set is compact, perfect, totally disconnected, nowhere dense, and has Lebesgue measure one. Membership is equivalent to greedy survival at every level. |
| **proved here** | For the #257 test value `1/2`, achievement-set membership is equivalent to infinitely many greedy skips and would produce an infinite support of rational sum, refuting universal #257. Under the last-skip schema's hypotheses (a rank floor, a carry condition, and a strict middle-cell inequality), the upper branch and the middle coordinate `-3` are impossible. |
| **conditional reduction** | Within that same last-skip contradiction schema, the two still-unexcluded middle coordinates, `-2` and `-1`, would also be ruled out if one current contribution were larger than the sum of all later possible contributions. That inequality is not proved. |
| **formalised here** | The dyadic sections of Euler's totient have an explicit rational basis; for `e ≥ 1` the level-`e` span has dimension exactly `2ᵉ + 1`. The Lean proof is an independent constructive route to an independence consequence of Martin's stronger theorem; this is a theorem about the coefficient sequence, not the irrationality of `S`. |
| **unconditional progress** | For every integer `k ≥ 2`, the sections through level `e ≥ 1` have rank `kᵉ + 1`, with an explicit basis and complete scalar relation normal form. The paper combines Martin's external affine-independence theorem with Lean-checked zero-channel and composite-base reduction identities, exact fixed-level residue coordinates, unconditional spanning, and a `kᵉ + 1` rank theorem parameterised by explicit linear independence. Martin's theorem and the all-base linear-independence premise are not formalised. |
| **formalised here** | Applying the classical Farey/mediant bound directly to the committed `K=240` interval excludes rational denominators through `79 639 646 646 701 375 323 355 774 875 831 053` (about `7.96 × 10³⁴`). This is exactly the Farey bound, not an improvement on it; Lean also checks that the next denominator fails this finite window. |
| **proved here** | `S` is irrational exactly when every positive binary tail difference is non-integral, equivalently when every fixed pair has a finite certificate. Finishing the argument would require certificates at arbitrarily large stages; that step is not proved. |
| **verified finite instance** | Lean proves a diagonal certificate at every `t ≤ 82`. Historical free-position audit: 125 verified log rows represent 123 distinct off-diagonal `(h,N,L)` certificates in 122 Lean files. This finite evidence does not prove successful cases beyond every fixed cutoff. |

### Other exact mathematics in the corpus

| Package | Exact checked content | Boundary |
|---|---|---|
| Fair-coin coprimality | `S = 1/2 + P(gcd(X,Y)=1)` for independent `P(X=n)=2⁻ⁿ`. | Irrationality remains open. |
| Squared-Lambert gcd moments | Two exact divisor-sum identities for squared Lambert denominators. | No transfer to the open Möbius row. |
| Stern–Brocot cylinder law | Exact stop/child splitting; depth error at most `(2/3)^d`. | Probability law, not irrationality. |
| Fibonacci/continuant run stability | Height at least `F_{r+3}` with exact defect expansion. | No analytic denominator-clearing theorem. |
| Tempered binary tail rigidity | Exact rationality/carry-orbit classification for `c(n) ≤ n`. | Needs problem-specific orbit control. |
| Exact Möbius-shadow denominator | Exact reduced denominator and an explicit divisor lower bound. | No unbounded avoidance supply. |
| Scalar-localisation height obstruction | If `H ∣ x.den` and `(c·x).den ∣ H`, then `x.den/H ∣ |c|`. | Local obstruction only. |

Typed routes expose sources: `probabilistic_gcd_geometry` for the first four
rows, `boolean_mobius_constraints` for tail rigidity, and
`arithmetic_obstruction_interfaces` for the last two. Orientation also lists
eventually-periodic nonnegative weighted irrationality, a signed
irrational-or-base-terminating dichotomy, five binary-carry
criteria/consequences, and two scoped #249 no-go countermodels.
Five further obstructions are stated with their limits in
[RESULTS](docs/RESULTS.md#other-standalone-exact-obstructions).

An exact final-skip band formula does not show that the actual orbit avoids
an unsafe band.

[Orientation](docs/ORIENTATION.md) routes claims; the retained
[mathematics paper](erdos249-257-main-paper.pdf) preserves the joint
#249/#257 exposition.

## What remains open

- Prove that `S = ∑ φ(n)/2ⁿ` is irrational without placing a bound on a possible
  rational denominator.
- Produce the unbounded certificate supply required by the exact #249
  reduction.
- Prove irrationality of `∑_{n∈A} 1/(2ⁿ - 1)` for every infinite
  `A ⊆ ℕ`, rather than only the named support families formalised here.

The two working records each close with a section titled "The wall": every
attempted argument class is stopped by a stated bound, recorded with what it
does not rule out.

[`SCOPE.md`](SCOPE.md) is the short boundary statement. The exact expert
handoffs state what input is requested, current guess, alternatives,
discriminating evidence, checked consumer, and endpoint-or-counterexample
boundary. See
[RESULTS](docs/RESULTS.md#exact-questions-for-a-human-expert) and
`python3 scripts/query_expert_handoffs.py`. A refuted route is withdrawn in
the next edition and the refutation credited.

<!-- BEGIN generated_corpus_at_a_glance -->
<!-- Generated by scripts/build_corpus_descriptor.py; do not edit this region. -->
## Corpus at a glance

The layer a mathematician should judge is small: 103 curated claim records in 21 contribution families, reaching Lean source through 333 principal declaration links. `SCOPE.md` gives its shape and `docs/RESULTS.md` gives the strongest checked result per problem.

The rest is engineering inventory. About 93% of the 153,320 declarations (142,668 across 683 modules) are machine-emitted certificate shards: one integer checked prime, one position excluded. The remainder is not all hand-written either.

| Engineering inventory | Current size |
|---|---:|
| Lean modules (the two library roots) | 1,023 |
| Formal results and supporting lemmas | 151,085 |
| Curated claim records | 103 |
| Contribution families | 21 |

Generated shards are counted as formal source and never as separate
mathematical claims. Claim records span every status, including cited and
open, and are partitioned exactly once.
These are navigation counts, not novelty claims.
<!-- END generated_corpus_at_a_glance -->

## Read or run it

- **Follow one claim, without installing Lean:** `verify_claims.py`, above, also
  shows the Lean proof text, and both it and `--verify-all` work on a
  `git clone --depth 1` checkout. Run it with no
  argument for the environment check, which exits `2` and prints
  `git fetch --unshallow` when a truncated history cannot reach the gates that
  read pinned commits; never `1`, so a shallow clone can never be misread as a
  claim that failed. `check_release.py` remains the authority for locators.
- **Mathematician:** use the top reading route, then follow one result from
  [SOURCE MAP](docs/SOURCE_MAP.md) into Lean. The per-problem papers are the
  live route; the [joint PDF](erdos249-257-main-paper.pdf) is retired.
- **Coding agent:** read [`AGENTS.override.md`](AGENTS.override.md), then the
  bounded [`docs/orientation.json`](docs/orientation.json); select one programme
  or claim before expanding the registry. [`AGENTS.md`](AGENTS.md) is the deep one.
- **Whole-corpus agent navigation, without a Lean build:** run
  `python3 scripts/query_corpus.py --tour --format card`, then follow
  `python3 scripts/query_corpus.py --route agent_native_corpus_navigation`.
  The no-build tour exposes corpus scale, the mathematical map, canonical
  eight-problem map, the distinct reviewed #249/#257 open-proposition
  frontier, and authority boundaries. Use
  `query_semantic.py problem-registry` for every indexed problem and
  `structural-backlog` for authored replacement. Committed indexes expose every
  indexed declaration and exact dependencies for both loaded roots; coverage
  keeps direct evidence, family context, and structural discovery distinct.
  These are navigation projections, not proof authority.
- **Agent working inside the corpus:** [the Agent Workbench](docs/AGENT_WORKBENCH.md)
  gives the instrument panel, the typed move grammar, and the three-rung
  invention ladder that fixes what a session may claim. Sessions are append-only
  ledgers under `workbench/sessions/`; `python3 scripts/proof_workbench.py show
  --session <slug>` reads one without Lean, and `replay --session <slug>`
  re-runs its stored probes and reports whether the recorded verdicts still hold. The one landed prospective session,
  [`carry_pivot_2026_07_27`](workbench/sessions/carry_pivot_2026_07_27/ledger.jsonl),
  produced [`SuffixCylinderCarryPivot.lean`](Erdos249257/SuffixCylinderCarryPivot.lean).
  Only kernel receipts assert; ledger notes and static nominations stay advisory.
- **Building proof search:** `hypOf%` lifts an unresolved hypothesis out of
  binder position into a `Prop`, so whether a sketch's remaining obligation
  differs from the target it started from becomes a question for the kernel
  rather than for a rater; the failure
  [AlphaProof Nexus](https://arxiv.org/abs/2605.22763) reports prompting could
  not prevent. [Deciding whether a sketch reduced its target or renamed
  it](docs/RESIDUAL_PROGRESS.md) has the evaluator, its eight labelled fixtures,
  and what it refuses to decide.
  [The proof-state compiler](docs/PROOF_STATE_COMPILER.md) asks the pinned Lean
  environment which candidate applications it actually accepts from a goal, and
  [the semantic compiler](docs/SEMANTIC_COMPILER.md) nominates declarations
  structurally without claiming they apply.
- **Publication topology:** run
  `python3 scripts/query_corpus.py --publication-architecture` or
  `python3 scripts/query_corpus.py --publication-family <id>`.
- **Placing this against the public benchmark:** the
  [Formal Conjectures crosswalk](docs/FORMAL_CONJECTURES_CROSSWALK.md) binds all
  eight programmes to Google DeepMind's Formal Conjectures statements at a pinned
  upstream commit, with a SHA-256 per source file and the indexing, ambient-type,
  and cast differences a reviewer must inspect. It is statement identity and
  adapter-review metadata, not a Lean equivalence proof or a submission-readiness
  decision; every row is `not_ready_to_submit`.
  [Related problems](docs/RELATED_PROBLEMS.md) places five of the eight
  programmes among the neighbouring numbered problems, each external status as
  listed on its erdosproblems.com page.
- **Verify:** `python3 scripts/check_cold_clone_comprehension.py --quick`
  checks reading surfaces without Lean; `python3 scripts/check_release.py`
  runs the full public-surface/query sweep.

## How the repository fits together

The package has two compact supported roots. [`Erdos249257.lean`](Erdos249257.lean)
preserves the reviewed #249/#257 corpus. [`ErdosProblems.lean`](ErdosProblems.lean)
is the problem-owned expansion surface: work lives under its actual Erdős
problem number instead of being forced into the historical #249/#257 tree.
Kernel checking of that second root establishes its exact Lean propositions;
it does not by itself promote them into the reviewed claim registry or claim
that an open problem is solved.

The source has five reader-facing layers:

- **Assembled kernel.** [`CertificateKernel.lean`](Erdos249257/CertificateKernel.lean)
  contains the common series machinery, the full-support Erdős-Borwein theorem,
  named support-family interfaces, and the unconditional #249 denominator
  exclusion.
- **The #249 reduction spine.** The period-killer, lcm-diagonal, cone, diagonal
  pincer, fresh-loss, and transport modules turn the open irrationality problem
  into exact certificate or avoidance obligations. Finite certificate modules
  verify explicit parameters; they do not supply the unbounded family required
  by the reduction.
- **The #257 carry trunk.** The tail-orbit, achievement-set, Boolean-Möbius
  carry, reciprocal-mass, and divisor-coverage modules give exact criteria and
  necessary conditions, not the universal #257 theorem.
- **Navigation.** The atlas finds every declaration and import. Selected
  semantic meanings carry scoped reviews (`python3 scripts/query_semantic.py
  semantic-reviews`), not human, novelty, or proof authority. The theory lab
  adds nine mechanisms, nine transfer capsules, and three failure receipts;
  four holdouts have no results, so no measured transfer is claimed.
- **Problem-owned expansion.** `ErdosProblems/Erdos<N>/` contains bounded
  results and explicit open frontiers for one problem at a time. New entries
  remain outside the reviewed claim registry until mathematical review
  establishes their intended meaning and public framing.

[SOURCE MAP](docs/SOURCE_MAP.md) gives module order; [METHODOLOGY](METHODOLOGY.md)
governs claim changes; [WAVE INDEX](docs/WAVE_INDEX.md) gives chronology, not
reading order.

<!-- BEGIN generated_principal_declaration_anchors -->
<!-- Generated by scripts/build_corpus_descriptor.py; do not edit this region. -->
## Following a result into Lean

The paper links each headline result to the relevant source. For a particular
topic, start with the [source map](docs/SOURCE_MAP.md); it gives the module
order without asking you to decode Lean declaration names first.
<!-- END generated_principal_declaration_anchors -->

## Build and verify

Everything above this heading runs with Python alone. Building the Lean source
needs the toolchain, and `lake` arrives with it: install `elan`, Lean's
toolchain manager, from the
[Lean setup guide](https://leanprover-community.github.io/get_started.html).
`elan` then reads [`lean-toolchain`](lean-toolchain) and selects
`leanprover/lean4:v4.29.1`; [`lake-manifest.json`](lake-manifest.json) pins the
matching Mathlib.

```sh
lake exe cache get   # fetches the pinned Mathlib build: several GB, once
lake build
```

For a focused build, run
`python3 scripts/lean_fast_build.py --jobs 2 [target]`. Add `--lake-staleness`
with restored `.lake` outputs so it trusts Lake content traces, not checkout
times. Without a target it checks both roots; `--plan` reports waves without
building. Partial caches stay on that trace-aware path even when a root output
is absent. One verbose no-build verdict identifies the stale frontier, which is
expanded through local import dependents; same-wave targets then share Lake
graph scans in batches capped by `--jobs`.
A cold clone can navigate before this step; formal editing needs the
pinned toolchain. Later builds reuse outputs and rebuild only the selected or
stale dependency cone; `--changed-from <git-ref>` selects changed modules.
The dependency-index validator stores an exact `.lake` receipt: unchanged
inputs make `--check` constant-time; `--check --full-check` forces an audit.

Check the public release surfaces separately:

```sh
python3 scripts/check_cold_clone_comprehension.py --quick
python3 scripts/check_release.py
python3 scripts/test_methodology_contract.py
```

The pinned public Lean proof corpus contains no `sorry`, `admit`, project-defined
`axiom`, or `native_decide`; finite computations use kernel-checked `decide`.
One deliberate exception is outside the default build:
[`ExternalVerification/Challenge.lean`](ExternalVerification/Challenge.lean)
states the trusted propositions Comparator checks the solution against; they
carry `sorry` by construction.

## Use as a Lean package

Import the reviewed #249/#257 root:

```lean
import Erdos249257
```

For the problem-owned expansion surface, import:

```lean
import ErdosProblems
```

[`examples/Examples.lean`](examples/Examples.lean) is the minimal downstream
consumer; its conditional shell-pressure example leaves the analytic
hypothesis explicit and does not prove universal #257.

## Citation and licence

Use [`CITATION.cff`](CITATION.cff) for `v0.9.0`.
Code, scripts, and documentation are Apache-2.0. The manuscript layer, including
the paper source and rendered PDFs, is CC-BY-4.0.
[`REUSE.toml`](REUSE.toml) is complete.

Use the issue forms for corrections. [`CONTRIBUTING.md`](CONTRIBUTING.md)
explains local checks; [`SECURITY.md`](SECURITY.md) gives the private route.
