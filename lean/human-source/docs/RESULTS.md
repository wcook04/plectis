<!-- SPDX-FileCopyrightText: 2026 Will Cook -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Results and limits

This repository formalises finite results, reductions, equivalences, and
obstructions related to eight open Erdős problems — #68, #243, #249, #251,
#257, #269, #1041, and #1049. Each problem has an individual canonical paper;
the retired combined #249/#257 manuscript is archive/provenance only, not a
current gateway. Nothing here solves any of the eight.

Lean source checked by the pinned Lean kernel is proof authority. The audit log
reports the headline declarations below with kernel assumptions
`[propext, Classical.choice, Quot.sound]`. A theorem with hypotheses proves only
the displayed implication; it does not prove that its hypotheses occur.

## The short version

The repository's clearest completed mathematics is concentrated in restricted
forms of Problem 257. It checks the classical full-support theorem for every
integer base `b ≥ 2`, a pairwise-coprime support theorem under explicit
summability hypotheses, and an irrationality theorem for nonnegative rational
eventually-periodic coefficients with a positive periodic tail. It also proves
global topological and measure statements for Mersenne achievement sets.
Universal Problem 257, which quantifies over every infinite support, remains
open.

Problem 249 contains the deepest collection of endpoint-facing mechanisms but
no endpoint proof. The library determines the exact finite-level rank of the
dyadic totient kernel, formalises finite denominator exclusions, and proves
several conditional routes from cofinal separation or decorrelation hypotheses
to irrationality. The missing cofinal producers are stated explicitly. The
library also proves no-go results showing why fixed precision, quotient
periodicity, or coefficient structure alone cannot supply the conclusion.

The remaining programmes have narrower but exact outcomes: Problem 68 is
reduced to a cofinal carry condition; Problem 243 has conditional recovery
criteria for its centred error dynamics; Problem 251 has exact prime-gap and
tail-shift reformulations; Problem 269 has three-prime running-LCM cell,
height, and carry structure; Problem 1041 has local Newton-flow, ray-separation,
and root-retention results; and Problem 1049 has an exact rational-base tail
recurrence together with finite Padé-model obstructions. None closes its Erdős
problem.

### Problem-by-problem guide

**Problem 68.** The library proves an exact equivalence between irrationality
and cofinally many non-unit factorial carries, together with finite channel
obstructions. It does not produce the required cofinal carries.

**Problem 243.** Descent and recovery theorems control bounded or summably
small negative centred error under the displayed dynamics. The unbounded
mixed-sign regime and the original endpoint remain open.

**Problem 249.** The checked results include exact dyadic-kernel rank, finite
denominator exclusions, conditional actual-LCM and harmonic-pivot routes, and
scoped no-go theorems. No cofinal producer reaching irrationality is proved.

**Problem 251.** The library gives a prime/prime-gap equivalence, tail-shift
classifications, and a coefficient-only countermodel boundary. A
prime-specific cofinal tail witness is still missing.

**Problem 257.** The corpus contains full-support and structured-support
irrationality theorems, eventually-periodic coefficient results,
achievement-set geometry, and exact half-value classifications. Irrationality
for every infinite support and the `1/2` and `1/21` branches remain open.

**Problem 269.** Exact three-prime LCM cell geometry, height identities, a
rank obstruction, and conditional carry observers are checked. The
actual-series carry bridge and a cofinal residue-window producer are open.

**Problem 1041.** The formal development covers Newton-flow value decay under
stated hypotheses, finite ray separation, translation avoidance, and
perturbative root retention. The global topology and metric gluing needed for
a short curve remain open.

**Problem 1049.** The library proves the rational-base tail recurrence and
sharp obstructions for specific finite Padé and Hermite–Padé models. It does
not construct approximants with analytic remainder control, including for the
base `3/2` case.

This guide is not a new result ranking. The canonical order of mathematical
attention is maintained in
[`PALOMAR_RESULT_SHOWCASE.json`](PALOMAR_RESULT_SHOWCASE.json), and exact public
statuses and open propositions live in [`claims.json`](claims.json).

For a narrative account, open the relevant item in the
[eight-paper portfolio](../README.md#problem-papers). For exact
declarations and assumptions, use the [source map](SOURCE_MAP.md). The sections
below retain the complete technical inventory, including result-family
dispositions, semantic census data, finite measurements, and retractions;
operational procedures live in the [agent workbench](AGENT_WORKBENCH.md).

<a id="ten-minute-verdict"></a>

<details>
<summary><strong>Open the complete technical results inventory</strong></summary>

## Technical verdict

All eight Erdős problems remain open. The development is neither a partial
solution nor an empty collection of restatements. For a first mathematical
pass, the high-signal spine is:

- **#257, a completed unconditional endpoint theorem in the full-support
  case.** The checked divisor-block proof combines a bounded Bertrand/CRT first
  block, middle-window divisor-pair averaging, weighted tail control, and
  parameter closure (`irrational_erdosSum_full_support`). It proves the
  canonical full-support series irrational in every integer base `b ≥ 2`, but
  not universal #257. A distinct adaptive-CRT certificate proves irrationality
  for every infinite pairwise-coprime support with summable reciprocal mass;
  those structured-support hypotheses likewise leave arbitrary support open.
  A deeper, genuinely distinct conditional route proves the base-2 support
  series under a finite-core orthogonal-petal bouquet plus the uniform
  `SunflowerForcedSlotTailSelection` predicate
  (`irrational_erdosSupportSeries_of_orthogonalPetalBouquet`,
  `Erdos249257/SupportSunflowerDichotomy.lean:540`); the selector and bouquet
  are not constructed for arbitrary supports. A separate direct result covers
  nonnegative rational eventually periodic coefficient sequences with a
  positive periodic-tail value: one common denominator reduces the claim to
  the periodic divisor-orbit sieve
  (`irrational_ratWeightSeries_eventuallyPeriodic`,
  `Erdos249257/CertificateKernel.lean:12811`); mixed-sign coefficients and
  arbitrary supports remain outside its hypotheses. Separately, the full base-2
  Mersenne achievement set has Lebesgue measure exactly one, while the
  supported-set theorem gives exact finite-complement measure or zero for an
  infinite complement (`volume_mersenneAchievementSet`,
  `Erdos249257/GreedyAchievementSet.lean:996`;
  `volume_supportedMersenneAchievementSet_dichotomy`,
  `ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean:397`). This is
  consequential global geometry, not a classification of rational points or
  a universal irrationality theorem.
- A second-layer Boolean–Möbius normal form is now an executable rationality
  equivalence: any `p/q` support value (`q>0`) is represented by a positive,
  square-root-bounded integer carry orbit whose quotient reconstructs the
  support. This is a change of coordinates for hypothetical rational support,
  not a contradiction or a universal #257 proof; arbitrary infinite support
  and the `1/2` membership boundary remain open.
- **#1041's highest-value open socket is hub selection, not the old argmin
  shortcut.** The source frontier identifies `min_c L(c) ≤ 2` over admissible
  hubs on the ray-separated locus as the surviving parent carrier; lower
  semicontinuity would turn it into the theorem. Its degree-five `SPOKE-5`
  instance would settle that degree. This is source-only research evidence,
  not a Lean theorem: hub choice, path containment, and the `SPOKE-5` supply
  remain open, while the earlier minimum-critical and aggregate shortcuts are
  explicitly refuted (`research_corpus/Erdos1041/FRONTIER.md`).
- **#249, an endpoint-facing conditional route plus a finite-level rank
  spine.** The actual-LCM orbit route gives a genuinely endpoint-facing
  reduction: an explicit approximation of the orbit by an odd-rank raw block,
  with an error radius, turns cofinal distance at least `1/32` plus that radius
  from every integer into the existing signed-margin producer. The exact
  source calls this `PowerTwoActualLcmOrbitSeparationSupply` and then derives
  irrationality from it, but this is a sufficient route, not an equivalence to
  the separate non-integrality criterion. The supply itself is not proved;
  neither divisibility nor irrationality alone supplies the required
  anti-concentration. Separately, the dyadic totient-kernel rank `2^e + 1`
  and its odd-core basis are an unconditional finite-level structural result;
  the all-base spanning/rank upgrade is conditional on the displayed
  affine-independence input. The actual-LCM, diagonal, and phase/prime
  producers remain open, so neither structural spine solves the binary
  totient endpoint.
- A distinct orbit-level carry anti-compression result is now checked: under
  hypothetical rationality, one positive multiplier supplies a tempered
  integral carry whose dyadic sections share an eventual modular period, while
  the canonical carry-kernel rank is at least `2^e-1` for every `e`. The hard
  friction is that modulo a divisor of the multiplier the totient forcing
  vanishes and the carry becomes geometric, so this gives no finite-rank
  contradiction or irrationality proof (`ExternalVerification/Challenge.lean:137`;
  `Erdos249257/TotientTailCarryPeriod.lean:224`).
- **#68, an exact endpoint reduction.** Irrationality is equivalent to
  cofinally many strict factorial-top divisibility misses, equivalently to
  cofinally many non-unit carries. The equivalence transfers the hard
  producer question exactly; it does not supply that producer.
- **#243 and #251, boundary results that diagnose the missing input.** Fresh
  pairwise-coprime moduli obstruct bounded rises, while periodic/vanishing
  negative-error regimes are excluded; for #251, unbounded prime gaps and an
  exact prime-gap irrationality equivalence still leave the concrete tail
  bridge open. A public Comparator-backed abstract denominator classifier
  reduces a dyadic tail's rationality to eventual integrality of one positive
  shift. Its companion normal form says, for a `RealDyadicTailRecurrence`,
  irrationality is equivalent to every positive tail shift being nonintegral;
  neither classification supplies the prime-specific producer.
- **#269 and #1049, structurally useful route checks.** Running-LCM height and
  rank-two obstructions, plus a distinct weighted-phase observer that separates
  a finite residue digit from an uncontrolled integral coboundary, isolate the
  #269 mechanism without claiming its endpoint. For #1049, the growing-rank
  four-jet/Padé kernel says that when `0 < R` and `4R + 2S ≤ n`, fewer finite
  endpoint signatures than binary selectors force a collision; row-content
  divisors remain as a second barrier. A separate explicit rectangular
  two-function Hermite–Padé model has a sharp no-go under `0 ≤ ρ` and
  `1 + ρ ≤ σ`, but neither route constructs approximants/remainders or proves
  irrationality at `3/2`.

The finite #249 certificate band, Stern–Brocot and gcd-moment identities,
#257 measure/noncollapse geometry, and the cited-only ladders remain useful
supporting routes. They are deliberately secondary to the mechanisms above:
finite ranges do not become cofinal theorems, and cited analytic inputs do
not become Lean results by appearing in the same paper.

### Signal-audit dispositions

These are editorial dispositions for first-contact signal, not novelty,
priority, or proof-status claims. The detailed sections below retain the
full evidence and exact boundaries.

I ranked the families by consequence, endpoint proximity, mechanism depth,
genuine distinctness, external usefulness, digestion value, evidence certainty,
natural friction, and overclaim risk—not by row count, inherited order, or
citation presence. The family-level table below is the compact reading map;
the detailed sections retain source-only families and the exact evidence
boundary alongside Comparator-transported rows.

| Disposition | Reader-facing treatment | Mathematical reason |
|---|---|---|
| **promote** | #257's full-support irrationality theorem, pairwise-coprime extension, orthogonal-petal reduction, and nonnegative rational eventually-periodic coefficient theorem, together with #249's actual-LCM separation reduction, lead the first pass. | The full-support row is an unconditional endpoint case for each `b ≥ 2`; the pairwise CRT and periodic denominator-clearing rows are distinct direct mechanisms; the bouquet and actual-LCM rows add unusually deep endpoint-facing conditional structure, with their unproved supplies kept adjacent rather than hidden. |
| **retain** | #257's achievement-set measure geometry, Boolean–Möbius exact-row conditional route, and sublogarithmic zero-window constraint, #68's exact carry equivalence, #249's diagonal full-target and foreign-residue reductions, finite kernel rank/basis, orbit-level carry anti-compression, and fixed-precision valuation/unit no-go, #243's bounded-rise, negative-orbit, and signed centered-recovery boundaries, #251's equivalence and countermodel, #269's height/rank obstruction and weighted-phase observer, #1041's admissible-hub/SPOKE-5 source frontier and Lean ray/root inputs, and #1049's recurrence, rectangular-threshold, and four-jet/no-go boundaries remain the strongest boundary for each problem. | The measure rows give consequential global geometry without classifying rational points; the Boolean–Möbius exact-row route gives a concrete local-to-cofinal half-membership mechanism under an unproved positive-skip supply, so it is useful endpoint-facing structure but not a contradiction; the sublog row gives a rationality-conditional coverage bound with a support/numerator-dependent constant, not a contradiction; the #68 and #249 rows are exact endpoint-adjacent or infinite-dimensionality results without their missing producers, while the #249 diagonal row makes integrality a full-target foreign-defect hit, the foreign-residue row adds an exact finite foreign/divisor split and closed geometric tail bound, and the orbit conjunction exposes modular periodicity alongside rank growth and its forcing-erasure friction; the fixed-precision row gives a prefix-locked centred completion for every finite compatible odd-unit word at fixed positive precision, so bounded local signatures cannot exclude every finite endpoint; its unrestricted high quotient is synthetic rather than actual totient arithmetic, and no #249 endpoint follows; the foreign row still needs the unproved `ControlledForeignProjection` bridge and unbounded separated-projection supply; the signed #243 recovery forces a centered defect to zero under exact displayed dynamics and bounded-negative hypotheses but leaves the unbounded mixed-sign branch open; the #269 observer exposes a finite residue/uncontrolled-coboundary split and a conditional finite-span criterion, but no finite-state quotient or endpoint; the source-only #1041 selector remains the direct degree-five/unrestricted socket while its local Lean inputs do not supply the global topology or metric selection; the #1049 rectangular threshold is sharp only for its explicit two-function model and the four-jet collision remains finite, so neither supplies an approximant/remainder bridge; the other rows rule out named regimes or supply exact identities without the missing universal, cofinal, topological, or irrationality bridge. |
| **consolidate** | The adjacent #249 gcd-moment, Stern–Brocot, finite-denominator, scalar-height, and synthetic LCM-shift results form one supporting arithmetic route; #257's finite-period, state, and defect results form one supporting universal-boundary route. | These results reuse finite-level or finite-support interfaces and share the same endpoint gap; the scalar-height lemma transfers denominator information but is not an irrationality criterion. Grouping these mechanisms preserves their reuse value without making repeated local identities look like separate endpoint advances. |
| **demote** | Citation-only #249 context and other classical formalised variants follow the local checked mechanisms; the canonical #257 full-support theorem stays promoted. | Provenance and known formalised cases establish context or a restricted theorem, not a new #249 conclusion; the completed full-support mechanism is the explicit exception because it is a direct checked endpoint case. |
| **replace** | The old citation-first/problem-order first pass is replaced by this mechanism-first spine; the eight problem sections remain the verification index. | Consequence and load-bearing mechanism are more informative to a first reader than paper order, while the per-problem sections preserve complete coverage and exact source routes. |
| **long-tail-only** | Finite searches, measurement logs, routine certificate shards, and unselected conditional predicate stacks remain discoverable through the source maps, but do not lead the reader. | A finite range, routine shard, or unconstructed antecedent cannot establish a cofinal family or universal endpoint, so it is evidence for follow-up rather than first-contact signal. |

The project also audits its conditional routes for endpoint equivalence. Some
named hypotheses are exact restatements of an open endpoint rather than smaller
subproblems; that diagnosis prevents a reformulation from being mistaken for
progress.

<!-- BEGIN semantic_public_census -->
Only after those theorem-level facts comes the corpus census. The current semantic graph provides three diagnostic views across every indexed Erdős problem:

| View | #68 | #243 | #249 | #251 | #257 | #269 | #1041 | #1049 | both | shared | total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mechanically nonrecurring candidates | 0 | 3 | 89 | 0 | 168 | 0 | 0 | 5 | 0 | 19 | 284 |
| classical/prior-art formalisations | 0 | 1 | 36 | 0 | 23 | 0 | 0 | 1 | 0 | 40 | 101 |
| bare open-problem equivalences | 0 | 0 | 15 | 0 | 15 | 0 | 0 | 0 | 0 | 2 | 32 |

The nonrecurring view contains 183 unconditional object theorems, 55 scoped barriers, and 46 reductions or transports after aliases, open antecedents, bare equivalences, finite/generated instances, infrastructure, classical results, and routine corollaries are removed.

The internal adjudicated frontier shortlist contains 11 nodes; it is distinct from the 8-node public prior-art review queue. 229 nonrecurring candidates remain unassessed for prior art. The live authored open-antecedent surface has 52 clusters, of which 10 are marked endpoint-equivalent. None of these populations is a novelty census.

Of 23 substantial Lean propositions extracted from hypotheses of conditional theorems, 17 are provably equivalent to an endpoint: 14 to #249 and 3 to the `1/2` membership test for #257. Equivalence here is kernel-checked against the extracted proposition, not a claim that either endpoint is settled.
<!-- END semantic_public_census -->

The large #249 denominator exclusion is a direct, kernel-checked instantiation
of the classical neighbouring-fraction/mediant method. That method supplies the
displayed bound exactly (numerical delta `0`). The local addition is the checked
arithmetic instance, its transfers, and its sharp first failure.

## Strongest checked results by problem

This is a high-signal orientation by problem, not a one-result roster: it gives
the strongest checked statements, their exact status, and where to verify them.
Each item carries the independent labels used across this repository: what Lean
checked, what the statement changes, and its literature relationship.
`formalised here` renders known mathematics;
`proved here` makes no novelty claim — that judgement is a human number
theorist's, and no query here supplies it. Reduction targets are named with
their own status in the same sentence. The claim registry and generated
verification projection are supporting navigation; they do not replace the
source declaration or enlarge its claim ceiling. The per-problem sections
below are the human reading map, with evidence, attribution, and surviving
boundaries kept together.

**#68 — is `∑_{n≥2} 1/(n!−1)` irrational?**

- Irrationality is equivalent, with no hypotheses, to one integer
  divisibility test on exact rational prefixes failing infinitely often —
  `irrational_factorialGapSeries_iff_cofinal_strictFacTopRat_misses`,
  `ErdosProblems/Erdos68/FactorialZeroPlateau.lean:1090`. Checked theorem;
  exact equivalence, transporting the difficulty without reducing it;
  registry: none.
- A separate finite quotient-band obstruction is now explicit. For a finite
  coefficient family whose indices all satisfy `k d ≤ i_j < (k+1)d`, the
  factorial moment factors as `M = (d!)^k C_d`; in the first band, channel
  cancellation `C_d = 0` therefore forces `M = 0`. More generally, if all
  indices are at least `d`, channel cancellation with `M ≠ 0` forces some
  index to be at least `2d` (`ErdosProblems/Erdos68/ChannelBreakpointRigidity.lean`;
  paper discussion in `erdos-68-factorial-denominator-irrationality.pdf`).
  Registry: `channel_quotient_band_breakpoint` (`res:bandbreakpoint`); its
  source and evidence boundary are the authority.
  This is a finite-family breakpoint only: it supplies no cancelling family,
  simultaneous-channel control, residual estimate, or cofinal non-unit carry.
- The kernel-internal denominator bound is `q ≥ 67`
  (`ErdosProblems/Erdos68/FactorialZeroPlateau.lean:940`); the `300000`
  exclusion is a checked implication
  (`ErdosProblems/Erdos68/FactorialZeroPlateau.lean:876`) whose evaluation is an external
  computation, not a kernel result.
- Open: produce infinitely many non-unit carries.
- A parallel carry form makes the same boundary explicit: irrationality is
  equivalent to cofinally many non-unit carries
  (`irrational_factorialGapSeries_iff_cofinal_nonunit_carries`,
  `ErdosProblems/Erdos68/FactorialZeroPlateau.lean`). The equivalence supplies
  no cofinal carry producer, so #68 remains open.

**#243 — does rationality force eventual Sylvester recurrence?**

- A divergent natural sequence with upward steps bounded by `B` cannot stay
  coprime to an infinite family of fresh pairwise-coprime moduli —
  `no_boundedRise_of_tailAvoidance`,
  `ErdosProblems/Erdos243/ReciprocalTailRigidity.lean:897`. Checked theorem;
  reusable obstruction; claims registry: `bounded_rise_fresh_modulus_barrier`
  (`res:barrier`).
- Given normalised vanishing — supplied for the canonical orbit by Koizumi
  (Integers 26 (2026), A28; cited, prose bridge) — a bounded negative part or
  finite normalised negative mass forces the error to vanish and the
  Sylvester recurrence to begin
  (`ErdosProblems/Erdos243/ReciprocalTailRigidity.lean:2177`,
  `ErdosProblems/Erdos243/ReciprocalTailRigidity.lean:2264`;
  `ErdosProblems/Erdos243/SparseResetRecovery.lean:155`,
  `ErdosProblems/Erdos243/SparseResetRecovery.lean:175`). Checked conditional theorems; the
  note concedes its absorption and descent lemmas as Koizumi prior art.
- A separate no-go rules out an eventually periodic negative-error orbit when
  the phase growth is positive
  (`no_eventuallyPeriodicNegative_orbit`,
  `ErdosProblems/Erdos243/ReciprocalTailRigidity.lean:796`; claims registry:
  `eventually_periodic_negative_no_go`). Its exact hypotheses include
  `2 ≤ a(n)`, `0 < e(N+n) < a(N+n)`, the denominator, tail, and shape
  recurrences, and positive-period/positive-drift equations. It does not cover
  arbitrary mixed-sign or unbounded negative behaviour, so the open boundary
  remains.
- The Comparator interface
  `no_cofinallyBoundedNegative_of_normalizedVanishes` makes another conditional
  no-go exact: with `a(n) > 1`, positive `C` and `magnitude`, the coupled
  recurrences `C(n+1) + D(n) = a(n)·C(n)` and
  `D(n+1) = a(n)·D(n)`, a bounded rise `C(n+1) ≤ C(n) + B`, normalized
  vanishing `K·magnitude(n) < C(n)` eventually for every `K`, and a cofinally
  bounded negative part, the hypotheses are inconsistent
  (`ErdosProblems/Erdos243/ReciprocalTailRigidity.lean`). Every dynamical,
  positivity, bounded-rise, and vanishing assumption remains explicit; this
  does not close the original mixed-sign regime (claims registry:
  `bounded_negative_exclusion`; source coordinate:
  `ErdosProblems/Erdos243/ReciprocalTailRigidity.lean:1748`).
- A distinct signed recovery family makes the centered mechanism executable:
  `boundedNegativePart_eventually_zero` assumes `a(n)>1`, `C(n)>0`, the exact
  natural dynamics `C(n+1)+D(n)=a(n)C(n)` and `D(n+1)=a(n)D(n)`,
  `E(n)=D(n)−(a(n)−1)C(n)`, strict `|E(n)|<C(n)`, a uniform lower bound
  `E(n)≥−B`, and division-free normalized vanishing; it forces `E=0`
  eventually. With centered zero and an eventually nonzero next tail,
  `sylvesterNext_eventually_of_centered_zero` recovers the Sylvester recurrence.
  The latter two declarations are mechanism evidence for this one family, not
  separate rows. This is not reciprocal-tail irrationality: the unbounded
  mixed-sign negative branch and prime-specific producer remain open
  (Comparator wrapper: `ExternalVerification/Challenge.lean:96-109`; source
  `ErdosProblems/Erdos243/ReciprocalTailRigidity.lean:2265`, with supporting
  declarations at `:1837` and `:1799`).
- Open: the unbounded mixed-sign regime.

**#249 — is `∑ φ(n)/2ⁿ` irrational? (reviewed core)**

- Cited-only source ceiling: Nesterenko's 1996 Corollary 2 gives algebraic
  independence of the Ramanujan values at algebraic `q` with `0 < |q| < 1`.
  At `q = 1/2`, its exact identity
  `P(1/2) = 1 − 24 ∑_{n≥1} σ(n)/2ⁿ` makes the divisor-sum series
  `∑_{n≥1} σ(n)/2ⁿ` transcendental by an elementary affine rewrite
  ([source closure](primary-sources/totient-kernel/nesterenko-1996-source-closure.md)).
  This is a distinct `σ`-coefficient ladder rung, not the Euler-totient
  constant `S`; Nesterenko's analytic proof is not formalised here, and no
  #249 irrationality or novelty claim follows.
- Cited-only q-zeta antecedent: Postelmans and Van Assche prove that
  `1`, `ζ_q(1)`, and `ζ_q(2)` are linearly independent for `q = 1/p` with
  integer `p > 1` (Theorem 1.3). At `q = 1/2`, the release's separately
  formalised identity `L₂(1) = ζ_{1/2}(2) − ζ_{1/2}(1)` therefore gives an
  irrational constant-weight squared-Lambert value
  ([source closure](primary-sources/reciprocal-tail/postelmans-van-assche-2007-source-closure.md)).
  This does not transfer to the Möbius-weighted totient constant `S`, and the
  source supplies no #249 or #257 solution.
- A nearby cited-only sparse criterion of Kaneko, Suzuki, and Tachiya gives
  irrationality of `∑ f(n)/t^{σ(n)}` and `∑ f(n)/t^{φ(n)}` under explicit
  nonnegative infinite-support and growth hypotheses ([source closure](primary-sources/reciprocal-tail/kaneko-suzuki-tachiya-2026-source-closure.md)).
  Here `φ(n)` is a denominator exponent, not the coefficient of `2⁻ⁿ`; this
  result does not transfer to `S`, arbitrary-support #257, or the release's
  gcd-moment identities.
- Unconditional: the dyadic sections `n ↦ φ(2ʲn+r)` of Euler's totient have
  an explicit rational basis, and the level-`e` span has dimension exactly
  `2ᵉ + 1` — `finrank_canonicalTotientKernel_eq`,
  `Erdos249257/TotientMahlerDefect.lean:989`; basis object at
  `Erdos249257/TotientMahlerDefect.lean:1392`. A
  theorem about the coefficient sequence, not about irrationality of `S`;
  it quantifies the known qualitative fact that `φ` is not 2-regular
  (Coons 2008, arXiv:0810.3709, via ζ zero-density — no exact rank appears
  there).
  Claim `dyadic_totient_certificate_interface` (the basis declarations at
  `Erdos249257/TotientMahlerDefect.lean:1265`,
  `Erdos249257/TotientMahlerDefect.lean:1380`,
  `Erdos249257/TotientMahlerDefect.lean:1392` — registry:
  dyadic_totient_certificate_interface).
- The Comparator interfaces make the rank frontier precise: for every
  `e ≥ 1`, `finrank_totientKernelThroughLevelFamily_eq` gives dimension
  `2ᵉ + 1` for the actual finite truncation, while
  `exists_totientDyadicSectionBasis` supplies the explicit odd-core-indexed
  basis. The full-kernel interface
  `not_finiteDimensional_span_fullTotientKernel` proves that the rational span
  is not finite-dimensional. These are coefficient-space facts, not a
  rationality-to-finite-rank bridge or an irrationality proof.
- For every base `k ≥ 2` and level `e ≥ 1`, an all-base extension has an
  explicit canonical spanning family; under its stated linear-independence
  hypothesis, the level-`e` span has dimension `kᵉ + 1`
  (`finrank_allBaseTotientKernelThroughLevelFamily_eq_of_linearIndependent`,
  `Erdos249257/TotientKernelConditional.lean:215`; claims registry:
  `all_base_totient_kernel_conditional_rank`). The independence is an
  external affine-ordering input not proved here, and this conditional rank
  statement does not prove irrationality of `S`.
- A scalar-localisation height lemma transfers, rather than discards, denominator
  information: under its displayed divisibility hypotheses,
  `scalarLocalization_complement_dvd` bounds the complementary factor of a
  reduced denominator by the multiplying integer, with the integer-coordinate
  identity supplied by `scalarLocalization_integer_eq_mul_num`
  (`Erdos249257/AdelicHeightObstruction.lean:23,56`; claims registry:
  `adelic_height_obstruction`). This is supporting arithmetic, not an
  irrationality criterion.
- A distinct actual-LCM orbit reduction makes the next analytic obligation
  explicit. With `H_a = lcm(1, …, 2^a)` and
  `R_a = totientTail(2H_a) − totientTail(H_a)`, the source defines
  `PowerTwoActualLcmOrbitSeparationSupply` as a cofinal supply of canonical
  odd ranks whose `R_a` stays at least `1/32 + actualLcmRawErrorRadius a q`
  from every integer. The checked raw-block approximation and its explicit
  error bound then force the existing half-word/signed-margin producer, and
  `irrational_totientSeries_of_actualLcmOrbitSeparationSupply` derives
  irrationality from that hypothesis. This is a new sufficient, non-equivalent
  quantitative bridge, not a proof of its supply: the module explicitly leaves
  that anti-concentration question open, and the earlier sign/top-edge result
  does not establish it. See
  `Erdos249257/TotientActualLcmOrbitSeparation.lean:254-310` and the transported
  consumer `ExternalVerification/Challenge.lean:159`.
- The public support transport keeps the boundary from collapsing into a sign
  argument. `actualLcmTailDiff_shift_pos` gives the positive corridor under
  `8 ≤ a` and its shortness inequality;
  `actualLcm_trueEndpointSurvivor_neg` shows that the true translated survivor
  can still be negative under the corresponding integer-difference hypothesis;
  and `actualLcm_integral_forces_topEdgeResidue` puts an integral orbit in the
  exact top-edge residue strip under its additional room inequality
  (`ExternalVerification/Challenge.lean:198-239`). These three declarations
  are support for the single `actual_lcm_orbit_separation` family, not three
  independent routes: positivity does not exclude the survivor, and neither
  row supplies cofinal separation or top-edge exclusion.
- A complementary diagonal pincer exposes the exact full-target coordinate:
  `diagonal_int_iff_foreignDiagonalDefect_hits_fullTarget` says that diagonal
  integrality is equivalent to the foreign defect hitting the complete reduced
  target (`Erdos249257/DiagonalPincerDecomposition.lean:215`). Its companion
  `irrational_totientSeries_of_full_target_avoidance_supply` would turn cofinal
  misses into irrationality (`:290`), but that full-target avoidance supply is
  open. This is one exact reduction subordinate to the actual-LCM frontier,
  not a new endpoint theorem or a second producer.
- A separate public first-harmonic pivot route is represented in the Comparator
  roster through its transported decomposition, budget, and conditional
  endpoint in `ExternalVerification/Challenge.lean`. The exact four-term
  decomposition of one block is
  `windowFirstExp_sum_eq_pivot_decomposition`; under the explicit room
  inequality, `PivotBudgetAt` bounds the centred real part by `14X/25` and the
  other three norms by `X/100`, `X/100`, and `8X/25`. The exact
  `first_harmonic_gap_of_pivotBudgetAt` consequence records the resulting real
  first-harmonic gap of `9X/10` and hence a finite certificate
  (`Erdos249257/FirstHarmonicPivot.lean:514-552`). The cofinal socket
  `DTWPivotResidualDecorrelation` would imply irrationality, but its supplier
  decorrelation budgets are unproved. The supporting
  `image_pivotSupplierPrimes_eq_pivotFiber` identity and
  `supplierPrime_not_globally_isolated_counterexample` counterexample expose
  the exact support boundary: at `X=16, L=20, s=1, m=2, N=18`, a supplier
  prime is not globally isolated (`:394`, `:569-588`). Comparator exposes this
  conditional route, but the supplier decorrelation budgets are unproved, so
  the unbounded certificate supply remains open.
- A separate source-current `strict_prime_tail_orbit_gap` family is retained
  below the actual-LCM and first-harmonic frontiers. Its Comparator wrapper
  `irrational_totient_series_of_naturalPrimeTailOrbitStrictGap` has one coherent
  two-branch interface. The subordinate `tailOrbitFirstExp_succ` identity records
  the exact squaring evolution of each tail-orbit phase; it clarifies the phase
  mechanism but supplies neither the `(11/100)` density nor the cofinal-prime
  producer. The later `tailOrbitFirstExp_add` and
  `tailOrbitFirstExp_eq_initial_pow_two` identities reduce every future phase to
  a power-of-two iterate of its initial phase;
  `not_naturalPrimeTailOrbitStrictGap_of_dyadic_root` shows that entering a
  dyadic root blocks the strict-gap producer. These are contrary-mechanism
  constraints, not density or cofinal-prime supply. In the block branch, for
  every `h > 0` and cutoff
  `X₀`, `TotientTailOrbitNonpositiveBlockDensity` assumes a late block with at
  least `(11/100) * X` nonpositive values of
  `Re(tailOrbitFirstExp h N)`; unit norm gives an `89/100` block saving, and a
  single `1/100` truncation budget gives the finite `9/10` certificate gap. In
  the prime branch, for every `h > 0` and `N₀`,
  `DTWNaturalPrimeTailOrbitStrictGap` assumes a prime
  `p ≥ max (N₀ + h + 1) (h + 5)` with
  `Re(tailOrbitFirstExp h (p − h − 1)) < 9/10`; its positive margin feeds exact
  natural pivot-fibre escape. The phase-density, cofinal-prime, and
  uniform-margin producers are all open for the actual totient orbit, and
  nonintegrality alone gives no fixed distance from the integers. This is
  producer-side conditional evidence, distinct from the actual-LCM and
  first-harmonic routes and not an #249 proof, novelty, or priority claim
  (`ExternalVerification/Challenge.lean`;
  `ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean:25-233`).
- Irrationality of `S` has six checked exact characterisations, from
  tail-difference certificates through the lcm-diagonal form to
  window-separated pairs — `Erdos249257/LcmConeFlatness.lean:316–426`,
  `Erdos249257/PivotAntiReconstruction.lean:1775`; claims
  `certificate_completeness`, `certificate_reduction`.
- Finite: the classical Farey/mediant window at `K = 240` excludes reduced
  denominators through `7.96 × 10³⁴` — improvement over the classical bound:
  zero (claim `denominator_exclusion`) — and diagonal certificates exist at
  every `t ≤ 82`, with the plateau broken at `t = 83` and a proved depth
  floor of `125` there
  (`ErdosProblems/Skip/LadderT67.lean:71264`,
  `ErdosProblems/Skip/LadderT67.lean:71285`,
  `ErdosProblems/Skip/LadderT67.lean:71294`; claim `certified_kill_instances`;
  no certificate at `t = 83` is
  claimed).
- Open: the unbounded certificate supply, which is equivalent to #249 itself;
  a checked splice construction shows no finite inspection can settle it.
- A separate Comparator-transported fixed-precision no-go,
  `fixedPrecisionTropicalNoGo`, gives every finite compatible valuation/unit
  word at fixed `u > 0` a bounded prefix-locked centred completion by varying
  an unrestricted high quotient (`ExternalVerification/Challenge.lean:150-158`;
  `Erdos249257/TropicalCurvatureCarry.lean:69-142`). This is synthetic finite-
  word evidence: it blocks bounded local signatures alone, but does not encode
  actual totient differences or supply growing precision, global correlation,
  a #249 endpoint, or irrationality.
- A checked synthetic no-go shows that, for every `t ≥ 3`, a nonzero dyadic
  coboundary can survive every finite integer shift polynomial while retaining
  the period-LCM totient factor ideals, exact cleared-prefix cancellation, and
  uniform state and letter bounds
  (`Erdos249257.TotientTailPeriodKiller.lcm_factorIdeal_finiteRank_shiftAlgebra_not_sufficient`,
  `Erdos249257/LcmFactorIdealPulseObstruction.lean`). This obstructs that
  finite shift-algebra route only: the forcing letters are synthetic rather
  than actual totient differences, nonlinear combinations are not covered,
  and no unbounded certificate supply follows.
- Two additional checked #249 families are directly inspectable: an exact
  [squared-Lambert gcd-moment transfer](../Erdos249257/GcdMomentCalculus.lean)
  at base `1/2` — `tsum_totient_div_mersenne_sq_eq_gcd_moment_series` identifies
  the totient-weighted squared-Mersenne Lambert series with the dyadic series
  of Pillai's gcd-sum function minus `n` — and the Comparator-transported
  `runHeight_defect_fib_sum_lower`
  (`Erdos249257/SternBrocotRunGeometry.lean`). For every finite defect list
  `e`, this theorem bounds the height of its positive Stern–Brocot run word
  from below by `(F_{r+3} + F_{r+1}) · ∑ eᵢ`, where `r` is the number of runs.
  These finite identities/inequalities do not establish analytic denominator
  survival or the unbounded family, so #249 remains open.
- At every positive Stern–Brocot node `(a,b)`,
  `cylinderMass_split` exactly decomposes the closed cylinder mass into the
  node's stop mass and the two child-cylinder masses
  (`Erdos249257/GcdMomentCalculus.lean`). This telescoping recursion and its
  geometric interpretation do not establish denominator survival,
  irrationality, or novelty; the #249 endpoint remains open.
- The same gcd-moment source gives the exact visible-coprime lattice
  normalization `∑ 1/(2ⁿ−1) = 1` over positive coprime pairs
  (`tsum_pos_coprime_inv_mersenne_eq_one`). It supplies the reduced-direction
  mass behind the fair-coin form of the totient constant, but is a rational
  normalization identity, not an irrationality result.
- A newly executable #249 complement-noncancellation reduction is deliberately
  subordinate to the actual-LCM frontier. The exact finite Möbius-residue
  split `finiteResidueDiagonal_eq_projectedForeign_add_divisor` separates
  foreign and divisor channels, while
  `abs_foreignTailWindow_le_foreignComplementBound` gives each omitted stable
  window a closed geometric budget. The consumer
  `scaleFullTarget_miss_of_projected_separation` then rules out a full-target
  hit when `ControlledForeignProjection` holds and the projected state is
  farther from every integer than that budget
  (`ExternalVerification/Challenge.lean:280-295`;
  `Erdos249257/ActualForeignResidueProjection.lean:276-417`). The analytic
  bridge identifying the actual complement with this bound, and any unbounded
  separated-projection supply, remain unproved: this sharpens the reduction,
  not #249 irrationality.

**#251 — is `∑ pₙ/2ⁿ` irrational?**

- Unconditional: `pₙ ≤ 1250(n+1)⁴` by an elementary argument, so the series
  is summable and equals `2 +` the prime-gap dyadic series with no external
  input (`ErdosProblems/Erdos251/PrimeGapDyadicTail.lean:360`,
  `ErdosProblems/Erdos251/PrimeGapDyadicTail.lean:379`,
  `ErdosProblems/Erdos251/PrimeGapDyadicTail.lean:427`); and for any sequence obeying the checked integer-digit dyadic
  tail recurrence, irrationality is exactly equivalent to cofinal
  non-integral tail shifts
  (`irrational_initial_iff_cofinalNonintegralTailShifts`,
  `ErdosProblems/Erdos251/PrimeGapDyadicTail.lean:1572`) — the
  identification of the concrete prime tail with that recurrence is
  paper-level. Claims registry: `prime_gap_unboundedness_and_nonperiodicity`
  and `prime_gap_irrationality_equivalence`; the actual prime-tail bridge
  remains open.
- The Comparator-facing boundary is also explicit: `exists_primeGap0_gt`
  proves that consecutive prime gaps are unbounded, while
  `irrational_tsum_primeDyadicTerm_iff_primeGap` proves, for a summable prime
  dyadic term, that its irrationality is equivalent to irrationality of the
  prime-gap dyadic series
  (`ErdosProblems/Erdos251/PrimeGapDyadicTail.lean`). Unbounded coefficients
  and this equivalence alone prove irrationality of neither series.
- A separate public Comparator transport makes the arithmetic boundary
  explicit. For a `DyadicTailRecurrence`,
  `tailShift_integral_iff_den_dvd_mersenne` and
  `tailShift_integral_iff_two_pow_modEq_one` classify an integral shift by the
  current reduced denominator and the congruence `2^h ≡ 1`; the source-level
  `tailShift_integral_iff_scaledTail` gives the equivalent integrality of
  `(2^h - 1) * T_N`. The transported
  `not_irrational_initial_iff_exists_eventually_integral_positive_tailShift`
  says that an integer-digit dyadic tail is rational exactly when one positive
  shift is eventually integral, while
  `irrational_initial_iff_all_positive_tailShifts_nonintegral` gives the exact
  companion normal form: under the same real recurrence, every positive
  shift at every index is nonintegral
  (`ExternalVerification/Challenge.lean:245-269`; source
  `ErdosProblems/Erdos251/PrimeGapDyadicTail.lean:802-807,1279-1295,1525-1556`).
  The classifications are abstract even though their normal form is now in the
  Comparator screen; they supply no prime-specific eventual-small or
  cofinal-mismatch producer.
- The exact finite carry identity and non-eventual-periodicity theorem close the
  coefficient-only periodicity implication at the Lean level
  (`carryPartialSum_natCast_eq`, `carryCoeff_natCast_not_eventually_periodic`,
  `ErdosProblems/Erdos251/PrimeGapDyadicTail.lean:1154-1173`). The accompanying
  rational-sum countermodel is an authored paper-level inference from the
  endpoint decay using the standard exponential-dominance limit; the
  Comparator interface does not assert that infinite limit. Its coefficients
  are synthetic, not actual prime gaps, so this is a methodological no-go and
  not an unconditional #251 refutation.
- Open: cofinally many adjacent index pairs with small tail shifts and
  differing gaps; each smallness condition constrains a complete infinite
  tail.

**#257 — is `∑_{n∈A} 1/(2ⁿ−1)` irrational for every infinite `A`? (reviewed
core)**

- Native unconditional: for every finite nonempty support `F` of positive
  exponents and every base `b ≥ 2`, the reduced denominator of `∑_{n∈F} 1/(bⁿ−1)` is coprime to `b`
  and has multiplicative order exactly `lcm F` — `finite_period_noncollapse`
  (Comparator interface `finite_period_noncollapse_rat_den_interface`),
  `Erdos249257/CertificateKernel.lean:5246`, with no witness-supply
  hypothesis. Checked theorem; claims registry: `finite_period_noncollapse`
  (`res:period`). It is a finite-support denominator result, not an
  irrationality theorem for arbitrary infinite supports.
- Formalised known results: the full-support series is irrational in every
  base `b ≥ 2` (Erdős 1948; claim `eb_full_support`), as are pairwise-coprime
  supports with summable reciprocals (Erdős 1968) and eventually periodic
  supports.
- The committed Comparator interface
  `irrational_erdosSupportSeries_pairwise_coprime` makes the pairwise-coprime
  row exact: for every base `b ≥ 2`, infinite support `A`, pairwise
  `Nat.Coprime` elements of `A`, and summable reciprocal indicator
  `Set.indicator A (fun a : ℕ => 1 / a)`, the support series
  `erdosSupportSeries b A` is irrational
  (`Erdos249257/CertificateKernel.lean`; independent statement wrapper in
  `ExternalVerification/Challenge.lean`). At base `2` this is a dedicated
  non-dilation family inside #257, not the universal infinite-support claim.
- Historical source boundary: Chowla's 1947 paper defines the ordinary
  Lambert series `f(x) = ∑ xⁿ/(1−xⁿ)` and a sine-twisted companion, conjectures
  irrationality for both at nonzero rational arguments, but expressly says he
  cannot prove the ordinary `f(x)` case. It proves only the sine-twisted
  `g(1/t)` case for integer `t ≥ 5`, via long zero blocks in sums of two
  squares ([source closure](primary-sources/reciprocal-tail/chowla-1947-source-closure.md)).
  Thus Chowla is historical context for the full-support `x = 1/2` Lambert
  value, not evidence for arbitrary-support #257 or a new release theorem.
- A distinct periodic-support antecedent is due to Luca and Tachiya: for a
  nonzero purely periodic integer coefficient sequence, their Theorem A gives
  irrationality of the associated divisor-convolution Lambert value at every
  integer base with absolute value greater than one; their stronger Theorem 1
  gives linear independence for nonnegative periodic coefficients, including
  full- and odd-support examples ([source closure](primary-sources/reciprocal-tail/luca-tachiya-2014-source-closure.md)).
  The hypotheses are periodic and coefficient-specific, so this is not a
  theorem for arbitrary infinite supports and remains distinct from the
  release's periodic-divisor certificate and mixed-sign boundary.
- The base-2 Mersenne achievement set — all subsums of `∑ 1/(2ⁿ−1)` — is
  compact, perfect, totally disconnected, nowhere dense, and of Lebesgue
  measure one (strict-tail Cantor structure after Kovač–Tao, Remark 4.1; the
  measure clause is proved here; positive measure was asserted informally by
  Kovač on the erdosproblems.com #257 discussion page in August 2025, and no
  published source computes the exact value) — the Comparator theorem
  `volume_mersenneAchievementSet`,
  `Erdos249257/GreedyAchievementSet.lean:996`,
  `Erdos249257/GreedyAchievementSet.lean:1633–1658`; claim
  `greedy_achievement_geometry`. Membership of `1/2` is equivalent to
  infinitely many greedy skips
  (`Erdos249257/GreedyAchievementSet.lean:2527`) and to the absence of
  a fatal half-gap (`Erdos249257/HalfCutLocator.lean:654`); the dyadic
  membership question was posed publicly by Kovač in the same discussion,
  and a positive answer would refute universal #257.

- Historical topological source boundary: Kakeya's 1914 paper proves
  perfectness for subsum sets of absolutely convergent real or complex
  series, gives the real interval enclosure, and states the exact term-versus-
  remaining-tail criterion for filling that interval. It also states
  nowhere density when the criterion fails, but explicitly leaves the
  “infinitely many failures” necessary-and-sufficient refinement unproved
  ([source closure](primary-sources/reciprocal-tail/kakeya-1914-source-closure.md)).
  This is classical subsum-set context only: it does not prove an arithmetic
  statement about Mersenne denominators, rational points, or universal #257.

- The Comparator theorem `seven_le_of_intBand_odd` adds a local two-adic
  band exclusion: for positive odd integers `p`, `D`, and `q` satisfying the
  stated `IntBand` inequalities, `7 ≤ p`
  (`Erdos249257/HalfGreedyTwoThirdsBand.lean`). Thus numerator classes `1`,
  `3`, and `5` are excluded in that band, while `p = 7` is sharp. The theorem
  does not show that an actual half-greedy orbit reaches or avoids the band,
  and does not decide half-membership.
- A newly transported conditional reduction makes the rational-support boundary
  concrete: if the support has a positive seed and its base-2 value is
  `p/(2^c·v)` with `v > 0`, then a positive natural shifted-tail state exists
  with the exact binary recurrence and modular orbit
  (`exists_shifted_odd_tail_nat_states_of_support_fraction`,
  `Erdos249257/RationalSupportCarrySkeleton.lean`). This exposes structure
  under a rationality hypothesis; it does not exclude rational infinite
  supports or settle universal #257.
- For a support restriction `J`, the transported measure dichotomy
  `volume_supportedMersenneAchievementSet_dichotomy`
  (`ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean`) gives exact
  measure `((2 : ℝ≥0∞) ^ F.card)⁻¹` when `J = (↑F)ᶜ` for a finite `F`, or
  measure zero when `Jᶜ` is infinite. This classifies the restricted
  achievement-set measure, not its rational points, so it does not settle
  universal #257.
- A separate unconditional composite-dilation identity now exposes the
  lower-rank defect rather than hiding it in a prime-only adapter:
  `supportCoeff_mul_eq_add_defect`
  (`Erdos249257/CompositeDilationDefect.lean`). For `a ∈ A`, `0 < a`, and
  `0 < x`, it states
  `supportCoeff A (a·x) = supportCoeff A x + (if a ∣ x then 0 else 1) + compositeDilationDefect A a x`.
  The exact defect is not bounded for arbitrary supports and supplies no tail
  selector or irrationality theorem; the separate bouquet budget remains
  conditional on its structural hypotheses.
- Methodological: a formalised squarefree-support no-go theorem is shown to
  be an artefact of normalisation — adjoining `1` to the support shifts the
  value by a rational and flips the divisor-incidence parity, and the
  finite-change principle is itself checked
  (`ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean:94`,
  `ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean:111`,
  `ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean:140`;
  `Erdos249257/CertificateKernel.lean:9467`,
  `Erdos249257/CertificateKernel.lean:9476`). The squarefree value
  itself is settled at power-of-two bases in the literature (Duverney–Tachiya
  2019; cited, not formalised). Registry: none.
- Open: universal #257, and the `1/2` and `1/21` memberships.

**#269 — are reciprocal sums of running lcms irrational?**

- For every pair of distinct primes, both the de-duplicated and the repeated
  running-lcm reciprocal sums are transcendental — a paper argument in the
  problem note; the transcendence engine is Loxton–van der Poorten 1977,
  quoted in the modern Bugeaud–Laurent form (Theorem 1.1); deliberately not a
  Lean theorem, and the note says so. Independently found and not first: the
  same reduction and conclusion were posted by Steve Fan on the
  erdosproblems.com #269 discussion page on 26 June 2026, before the note was
  finalised, with follow-ups there extending it to arbitrary coprime pairs;
  the note acknowledges this.
- Lean-checked: the exact Comparator interface
  `smoothPrefixLcm_eq_threePrimeHeight` states that, for primes `p`, `q`, and
  `r` with `p ≠ q`, `p ≠ r`, `q ≠ r`, and `x ≠ 0`, the running lcm of the
  three-prime smooth prefix is exactly `threePrimeHeight p q r x`
  (`ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean:123`; formalisation of a
  classical identity). The same source also gives the four-letter block
  alphabet `{2, 6, 10, 30}`
  (`ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean:699`), and a rank-two
  kernel obstruction
  (`ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean:479`,
  `ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean:721`): the Comparator
  theorem `kernel_235_minor_eq_neg_one_fifteen` identifies the smallest
  displayed `2,3,5` kernel minor as exactly `-1/15`. This rules out the
  displayed rank-one route only; it does not imply irrationality and does not
  supply the missing rationality-to-irrationality bridge.
- Open: any three-prime case; the rationality-to-carry bridge and the
  cofinal window escape.
- The finite residue contradiction and conditional cofinal-window carry
  extinction are indexed as `three_prime_finite_residue_contradiction` and
  `three_prime_cofinal_window_carry_extinction` in `docs/claims.json`, with
  paper routes `res:consumer` and `res:windowconsumer`.
- A separate Comparator-transported family in `ErdosProblems/Erdos269/WeightedPhaseCarry.lean`
  keeps one coherent observer mechanism visible. For `B : ℤ` with `0 < B` and
  the displayed carry recurrence, `carry_eq_residueDigit_add_coboundary`
  gives the exact residue-digit plus integral-quotient-coboundary identity
  (`WeightedPhaseCarry.lean:109`); `carryResidue_mem_interval` and
  `residueDigit_mem_interval` give the finite intervals under their explicit
  positivity and canonical-reduction hypotheses (`:150`, `:157`). The separate
  `finite_realisedSpan_of_factorisation` theorem gives finite-dimensional
  realised span only for `DivisionRing` modules with finite-dimensional
  observer space and an explicit linear factorisation
  `realise = readout.comp C` (`:334`). The quotient coboundary remains
  uncontrolled: no finite-state quotient, literal infinite realised span,
  scalar-evaluation implication, or #269 rationality/irrationality conclusion
  follows. This is now Comparator-transported evidence, with the same boundary, and is
  distinct from the
  three-prime cell, rank-two no-go, and conditional carry-escape families.
- A separate typed consumer makes the conditional carry-escape boundary concrete:
  `no_positive_reducedCarry_of_cofinalLocalWindowEscape` derives `False` from
  `CofinalLocalWindowEscape`, `B > 0`, `Nat.Coprime B 30`, positivity of an
  integer-valued carry, the exact multiplier recurrence, and its
  denominator-dependent short bound (`ExternalVerification/Challenge.lean:498-509`;
  `ErdosProblems/Erdos269/RestrictedFloorSum.lean:629-654`). Its hard step is
  the cofinal window expansion against that bound. The escape producer and the
  bridge from the actual three-prime running-LCM series (or its rationality) to
  this carry remain unproved, so this is no #269 endpoint or irrationality
  proof; it is distinct from the finite residue and weighted-phase observers.
**#1041 — short connections inside polynomial lemniscates?**

- The source-only frontier now has the sharper endpoint socket: on the
  ray-separated locus, prove `min_c L(c) ≤ 2` over admissible hubs. Its
  attachment and lower-semicontinuity reductions would then give the parent
  theorem; the degree-five `SPOKE-5` instance would settle that degree. This is
  not a Lean or Comparator theorem: hub selection, path containment, and the
  degree-five supply remain open, while the earlier minimum-critical and
  aggregate shortcuts are refuted (`research_corpus/Erdos1041/FRONTIER.md`).
- Lean checks the supporting inputs: quantitative root retention under constant
  perturbation (`constant_perturbation_roots_in_unitDisk`,
  `ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean:287`) and arbitrarily
  small translations separating all pairwise ray arguments. More precisely,
  `exists_small_translation_separating_arguments` gives every finite injective
  complex family, for each `ε > 0`, a common shift of norm `< ε` making every
  value nonzero and every positive-ray argument distinct (`:197`). The
  exponential-decay connection equation is a hypothesis of the local
  ray-separation consumer, not a theorem (`:315`).
- The note's main independent contribution is prose, not Lean: a specific
  invalid three-ended local block at an interior Morse saddle in a recent
  manuscript's load-bearing Proposition 12 — identified as a proof gap, not
  a counterexample.
- Open: repair or refute that decomposition; the planar topology and length
  bookkeeping.

- Current-source boundary: the committed [`research_corpus/Erdos1041/FRONTIER.md`](../research_corpus/Erdos1041/FRONTIER.md)
  is the dated route for later source-only research evidence. Read it before
  the generated `STRONGEST_RESULTS.json`: it records certified refutations of
  several proposed strategies, surviving carriers, and exact open gaps while
  leaving the unrestricted endpoint open. These rows are not reviewed claim
  entries, peer review, priority, novelty, or significance findings; the
  frontier itself flags priority/novelty as unchecked for named new rows.

**#1049 — Lambert series at rational bases, beginning with `3/2`?**

- Checked exclusions at `3/2`, each of one named mechanism only: the
  coordinatewise clearing scheme is impossible for all parameters
  (`threeHalves_no_coordinatewiseCorridor`,
  `ErdosProblems/Erdos1049/RationalBaseLambert.lean:155`), scalar content is
  neutral for the local-to-Archimedean balance, and unit endpoints exclude
  both `2` and `3` from a common divisor
  (`ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean:293`). Claims registry:
  `three_halves_coordinatewise_corridor_no_go` (`res:nocorridor`) and
  `rational_base_cleared_tail_recurrence` (`res:tailrec`); both are exact
  formal boundaries, not an irrationality result.
- The elementary height inequality used by Bundschuh–Väänänen's external
  irrationality criterion at `7/2` is checked
  (`ErdosProblems/Erdos1049/RationalBaseLambert.lean:83`);
  the analytic theorem itself remains external. Formalisation of known
  inputs.
- A separate exact rational-base state recurrence is checked under `r ≠ 0`:
  `rationalBaseClearedTailQ_succ` gives
  `Q(N+1) = r·Q(N) − B·coeff(N+1)·s^(N+1)` for the denominator-cleared tail
  state (`ErdosProblems/Erdos1049/RationalBaseLambert.lean`). The
  `s^(N+1)` forcing term records the denominator-base tax; this recurrence is
  not itself a rationality contradiction, so it yields no #1049 endpoint.
  The companion forcing bound is indexed as `rational_base_forcing_growth`
  (`res:forcing`): for `s ≥ 2` and positive data it gives a lower bound
  `2^(N+1)`, while `s = 1` collapses exactly to `B·coeff(N+1)`.
- A distinct source-level four-jet/Padé obstruction is deferred outside the
  Comparator screen. When `0 < R` and `4R + 2S ≤ n`, the four-jet target has
  cardinality `(3^R)^2 * (2^S)^2 < 2^n`, forcing two distinct binary selectors
  to share a four-jet signature
  (`ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean:129-167`). The
  accompanying Padé exterior determinants retain their row-content divisors
  (`ErdosProblems/Erdos1049/RationalPadeArithmetic.lean:80-220`), so the
  package exposes finite collision and content barriers without supplying an
  analytic remainder, nonvanishing, or irrationality theorem. It is distinct
  source evidence, not a Comparator result or an endpoint closure.
- A source-faithful rectangular Hermite–Padé threshold family is now exposed
  through the external consumer. In the explicit two-function exponent model,
  `0 ≤ ρ` and `1 + ρ ≤ σ` imply `hpClearedGap_nonpos` and
  `hpClearedGap_eq_zero_iff`; equivalently,
  `rectangular_hp_threshold_le_classical` and
  `rectangular_hp_threshold_eq_classical_iff` give
  `hpThreshold ≤ 1/2 − 1/π²`, with equality only at `(ρ,σ) = (0,1)`
  (`ErdosProblems/Erdos1049/HermitePadeNoGo.lean:58-129`;
  `ExternalVerification/Challenge.lean:399-420`). This is a sharp no-go for
  the displayed model, not a universal Padé result: no approximating
  polynomials or analytic remainders are constructed, and no #1049
  irrationality conclusion follows.
- The Van Assche moving diagonal fails the Amdeberhan–Zeilberger scalar
  recurrence already at `n=0`: its exact residual is
  `-p(p-1)^2(p+1)(p^5+2p^4+2p^3+2p^2+2)`, strictly negative for every real
  `p>1`
  (`ErdosProblems/Erdos1049/QAperyDiagonalNonEquivalence.lean:67,94`). This finite obstruction
  proves only non-transfer of that recurrence; it supplies no general
  recurrence, endpoint, lattice, valuation, denominator, or irrationality
  theorem. Claims registry: `van_assche_qapery_diagonal_no_go`; its source-bound
  ceiling is recurrence non-transfer at `n=0`, not an endpoint or irrationality
  result.
- Open: irrationality at `3/2`; the primitive noncollapsed construction;
  analytic remainder control. The note proves no irrationality result and
  says so.

The semantic corpus marks exactly eight statements `candidate_new_statement` —
the only machine novelty marks in this release, against 5,505 of 6,089
statement nodes still `not_assessed`. They concentrate in the #249/#257 core
(the totient Möbius-numerator normal form, a rank-one overshoot barrier, and
the `1/2` tail-escape and middle-producer family). Reproduce the list from
`docs/semantic_corpus.json` (`statement_nodes[].prior_art_state`); candidate
status is a search outcome recorded for triage, not a novelty claim.

## What is proved

### Settled support families for Problem 257

The universal problem is open, but several infinite supports are settled.
The formal source proves irrationality in every integer base `b≥2` for the
full support, factorials, powers of two, multiples of a fixed positive integer,
residue classes, the odd numbers, eventually periodic supports, and pairwise
coprime supports with summable reciprocals. The relevant declarations include:

- `irrational_erdosSum_full_support`;
- `erdos257_family_factorial_instance` and
  `erdos257_family_two_pow_instance`;
- `irrational_erdosSupportSeries_multiples`,
  `irrational_erdosSupportSeries_residueClass`, and
  `irrational_erdosSupportSeries_odd`;
- `irrational_erdosSupportSeries_eventuallyPeriodic`; and
- `irrational_erdosSupportSeries_pairwise_coprime`.

These declarations are in `Erdos249257/CertificateKernel.lean`. The prime and
prime-power supports are literature results cited by the repository, not
formalised here.

A distinct second-layer rationality normal form is now a typed public
consumer: `exists_normalized_support_fraction_iff_exists_booleanMobiusCarry`
(`ExternalVerification/Challenge.lean:363`, source
`Erdos249257/BooleanMobiusCarry.lean:949`). For `p : ℤ` and `q > 0`, it is an
existence-level equivalence between a support omitting `0`, containing a
positive index, and having value `p/q`, and a map `U : ℕ → ℤ` with
`U 0 = p`, positivity, the square-root bound `U N ≤ q(2√N+4)`, divisible carry
differences, and a Boolean–Möbius quotient; the quotient reconstructs the
support. This is genuinely distinct from the shifted-natural-tail state: it
is quotient-level and reconstructs literal support. It is only a
characterisation, not a contradiction or a universal irrationality theorem;
it does not produce cofinally nonintegral shifts for the actual recurrence,
settle arbitrary infinite support, or settle the `1/2` membership boundary.

A separate Comparator-backed conditional row route makes the half-membership
mechanism executable: under `CofinalPositiveHalfGreedySkips`, a positive
rational-greedy remainder below the next Mersenne weight yields an exact local
half row; cofinally many such skips give
`(1 / 2 : ℝ) ∈ mersenneAchievementSet`
(`half_mem_mersenneAchievementSet_of_positiveHalfGreedySkips`,
`ExternalVerification/Challenge.lean:400`, source
`Erdos249257/BooleanMobiusSkipRowCofinal.lean:22,73`). The cofinal supply is
unproved, and finite exact rows do not establish it, so this is a conditional
counterexample route rather than an unconditional #257 result; it does not
settle the universal problem.

A separate necessary-condition family controls coverage under a hypothetical
rational support value. `supportCoeffZeroWindow_length_le_eps_logb_add` forces
every zero window in the divisor-count coefficient to have length at most
`ε·log₂(N+1) + B`; the additive constant is built after the support and
numerator, so it is not uniform across supports (`SublogDivisorCoverage.lean:392`;
claims registry: `sublog_zero_windows`). This is a genuine restriction on a
possible rational support, not a contradiction or a proof of universal #257.

The squarefree support remains open. Its divisor incidence is proved to be
`2^ω(n)-1`, hence odd at every `n≥2`. The certificate engines in this
development begin by selecting an even-incidence block, so they cannot act on
that support at any block position. The checked declarations
`card_squarefreeDivisors`, `squarefreeIncidence_eq`, and
`odd_squarefreeIncidence` are in
`ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean`. This is a limitation
of the named engines, not evidence that the squarefree-support value is
rational or irrational.

### The reduction chain for the one-half test case of Problem 257

The Mersenne achievement set consists of subsums of
`1/(2^n-1)`. If `1/2` belongs to it, its support gives an infinite set with a
rational subseries, which would refute the universal statement in Problem 257.
The repository does not prove this membership.

The checked chain includes:

- `half_mem_mersenneAchievementSet_iff_greedySkippedSupport_infinite` in
  `Erdos249257/GreedyAchievementSet.lean`: membership of `1/2` is equivalent to
  infinitely many skips in its greedy expansion.
- `half_mem_mersenneAchievementSet_iff_unboundedTerminalFalse` in
  `Erdos249257/HalfCylinderHalfMembershipClassification.lean`: the same
  membership is equivalent to terminal false bits beyond every bound.
- `half_mem_iff_unboundedLargestSkipLate` in
  `ErdosProblems/Skip/D2.lean`: membership is equivalent to late largest skips
  beyond every bound.
- `exists_largestSkipLateAt_of_remainder_le_two_pow` in
  `ErdosProblems/Bit/R2.lean`: a row with remainder at most `2^N` produces a
  late largest skip in the explicit interval `[N+1,2N+1]`.
- `half_mem_of_remainderReachesHalfPointCofinally` in
  `ErdosProblems/Bit/R2.lean`: remainders at most `2^s` cofinally are sufficient
  for membership.

The final two bullets are one-way sufficient criteria. They are not
equivalences and are not known to hold cofinally.

The proposed universal `hlow` side condition is false:
`not_hlow_seven_five` in `ErdosProblems/Decl/D4.lean` and
`not_hlow_of_hhigh` in `ErdosProblems/Hlow/H1.lean` give the counterexample
`(s,d) = (7,5)`. Its failure is useful rather than obstructive:
`seamRemainder_lt_two_pow_of_not_hlow` and
`seven_is_a_hit_from_failure` in `ErdosProblems/Hlow/H2.lean` convert that
failure into a hit certificate.

### Exact ranks for dyadic sections of Euler's totient

For `j ≥ 0` and `0 ≤ r < 2^j`, let
`φ_(j,r)(n) = φ(2^j n + r)`. The family consisting of `φ_(0,0)`,
`φ_(1,0)`, and all `φ_(j,r)` with odd `r` is a rational basis for the span of
all dyadic sections. At level `e`, the span has dimension exactly `2^e + 1`.

Lean names and sources:

- `linearIndependent_oddCoreTotientKernelFamily`,
  `span_range_fullTotientKernel_eq_span_range_oddCore`, and
  `totientDyadicSectionBasis` in
  `Erdos249257/TotientMahlerDefect.lean`;
- `finrank_canonicalTotientKernel_eq` in the same file.

These are theorems about the coefficient sequence `φ`. They do not prove that
`∑ φ(n)/2^n` is irrational.

### A finite diagonal certificate band for Problem 249

Let `periodLcm t = lcm(1,…,t)`. The predicate
`certifiedKill h N L` is a finite modular-arithmetic certificate showing that a
specific binary totient-tail difference at shift `h` and position `N` is not an
integer.

`exists_diagonalKill_le_82` proves

```text
for every t ≤ 82, there is an L such that
certifiedKill (periodLcm t) (periodLcm t) L.
```

Lean name and source:

- `exists_diagonalKill_le_82` —
  `ErdosProblems/Skip/LadderT67.lean`

The exact least depths at the new boundary scales are:

| Scale `t` | Least depth `L` | Lean name | File |
|---:|---:|---|---|
| 67 | 100 | `t67_minimal_depth` | `ErdosProblems/Lift/Recon67.lean` |
| 71 | 105 | `t71_minimal_depth` | `ErdosProblems/Lift/CertT67.lean` |
| 73 | 113 | `t73_minimal_depth` | `ErdosProblems/Skip/LadderT67.lean` |
| 79 | 120 | `t79_minimal_depth` | `ErdosProblems/Skip/LadderT67.lean` |
| 81 | 120 | `t81_minimal_depth` | `ErdosProblems/Skip/LadderT67.lean` |

The same file proves

```text
periodLcm 79 = 32433859254793982911622772305630400,
```

a 35-digit modulus, as `periodLcm_79_value`.

The source-backed
[`checked_diagonal_depth_roster.json`](measurements/checked_diagonal_depth_roster.json)
covers all 33 distinct `periodLcm` scales whose plateaux fill the positive band
`t≤82`. Every recorded working depth lies `0…4` above the arithmetic
admissibility floor (median `1`, mean `40/33`). Only the five boundary scales
`t=67,71,73,79,81` have separate theorems proving their recorded depths least;
for the other 28 scales, the excess is only an upper bound on the least-depth
excess. Its reproducibility route is maintained with the other operational
checks, not part of the mathematical claim.

This is a bounded result. The reduction for Problem 249 requires certificates
at arbitrarily large scales. The theorem says nothing at `t = 83`.

### Finite off-diagonal certificates

The historical audit selects 125 verified log rows at positions not constrained
to equal `periodLcm t`. Two pairs of rows repeat the same `(h,N,L)` triple, so
the roster contains 123 distinct certificates matched to 123 public Lean
theorems across 122 files. The largest position in that audited set is:

```text
freeKill_64OneHundredFifteenDI :
  certifiedKill 1 135960691671824579163806583999 101
```

Source:
`ErdosProblems/FreePosition/FreeKill64OneHundredFifteenDI.lean`.

The generated
[`off_diagonal_certificate_roster.json`](measurements/off_diagonal_certificate_roster.json)
retains all selected source rows and their hashes, identifies both duplicate
groups, and binds each distinct triple to its exact theorem, line, and source
hash. It is a navigation and evidence projection, not a replacement for the
theorem statements.

The source log also contains 54 later verified certificate triples above the
historical position cutoff. The roster exposes that excluded census without
silently changing the historical result.

The relevant sufficient theorem for Problem 249 is
`irrational_totient_series_of_multiple_window_kill_supply` in
`Erdos249257/CertificateKernel.lean`. Its hypothesis requires, for every
positive base shift and every lower bound on the position, a later certificate
at some positive multiple of that shift. A finite list of 123 instances does
not establish that quantified supply.

### Direct Farey comparison

The denominator exclusion is exactly the standard Farey/mediant bound for the
two committed finite windows. The arithmetic below was recomputed from

```text
V_K = (∑_{r=1}^K φ(r+1) 2^(K-r)) mod 2^K
```

and from the explicit neighbouring fractions in
`Erdos249257/GapFareyBound.lean`.

| `K` | Interval width | Delta |
|---:|---:|---:|
| 120 | `123/2^120` | `0` |
| 240 | `243/2^240` | `0` |

The exact denominators of each window are:

```text
K = 120
  Farey neighbour denominators b, d   41326538792622579
                                      207345787569745331
  b+d-1                               248672326362367909
  formal exclusion bound              248672326362367909
  first failing denominator           248672326362367910

K = 240
  Farey neighbour denominators b, d   66013429300517684370587633721421187
                                      13626217346183690952768141154409867
  b+d-1                               79639646646701375323355774875831053
  formal exclusion bound              79639646646701375323355774875831053
  first failing denominator           79639646646701375323355774875831054
```

For each window, the recomputation gives determinant `1` for the two neighbours,
verifies both interval brackets, verifies the displayed bound, and verifies
failure at the next denominator. The corresponding proved declarations are
`farey_gap`, `gap_check_window_1_120_le_248672326362367909`,
`gap_check_window_1_120_first_failure`,
`gap_check_window_1_240_le_79639646646701375323355774875831053`, and
`gap_check_window_1_240_first_failure`.

The division of credit is exact: Farey supplies the bound directly;
formalisation supplies a checked arithmetic instance and proves it is sharp
for that window. Neither finite window proves that the exclusion bounds are
unbounded, so neither proves Erdős #249.

The magnitude is also a tunable window output, not an invariant measure of
progress. `scripts/check_farey_denominator_scaling.py` independently reproduces
the two formalised constants and cross-checks the producer by brute force on
six small windows. On this run, choosing `K=16000` produced a 2,406-digit bound
in `0.08` seconds for the scaling row (`0.18` seconds for the complete script).
Every fixed `K` still gives only a finite exclusion, and increasing `K` does
not supply the unbounded theorem required by #249.

### Scoped no-go theorems

These theorems rule out particular proof mechanisms. They do not rule out other
arguments.

- `no_lift_from_lower_totient_data`, `ErdosProblems/Lift/AngleA5.lean` — no
  universal lift of the displayed form can follow only from the stated lower
  totient data, pointwise bound, and a lower certificate.
- `no_window_local_lift`, `ErdosProblems/Lift/InduceLaw.lean` — for prime
  multipliers `p ≥ 3`, agreement on the lower diagonal window does not force
  any certificate in the lifted window.
- `exists_certifiedKill_antitone`, `ErdosProblems/Lift/AngleA4.lean` — a
  certificate at a larger position gives one at a smaller position; the
  implication runs opposite to a forward lift.
- `consecutiveFail_iff`, `ErdosProblems/Half/FreeWalk2.lean` — under its
  explicit depth inequality, a run of `K` failures at depth `L` is equivalent
  to failure at depth `L+K` at the base position.
- `no_absolute_bound_on_consecutive_failures`,
  `ErdosProblems/Half/FreeWalk1.lean` — the abstract admissible-run model
  permits arbitrarily long failure runs under its stated budget.
- `exists_persistent_surplus_model`, `ErdosProblems/Rem/C1.lean` — the listed
  row recurrence and ceiling inequalities admit a sequence that stays above the
  target forever.
- `rowLaw_blind_at_16`, `ErdosProblems/Rem/C1.lean` — at one concrete row,
  every listed row-level trigger is silent although the next row has a late
  skip.
- `IntervalCeiling.four_pow_le`, `ErdosProblems/Three/T1.lean` — every ceiling
  satisfying the stated branch-blind rank-recursion obligations must grow on
  the `4^s` scale.
- `two_pow_mul_y`, `ErdosProblems/Three/T2.lean` — the normalised state used in
  the doubling route is dyadic at every finite row.
- `exists_persistent_odd_surplus_model`, `ErdosProblems/Three/T3.lean` — adding
  parity to the listed row-level constraints still admits a persistent surplus
  model.
- `PairCeiling.terminal_ge_of_splits`, `ErdosProblems/Decl/D1.lean` — in the
  stated two-sided abstraction, a failed branch prediction forces the terminal
  upper bound above the target scale.

### Other standalone exact obstructions

These five registry claims are not restatements of either endpoint. Each has a
separate limitation, and none settles an Erdős problem.

- **Orbit-level carry anti-compression** — the checked consumer
  `not_irrational_totientSeries_implies_mod_period_and_unbounded_rank`
  exposes one positive multiplier `v` and tempered integral carry `u` under
  hypothetical rationality: every dyadic section is eventually periodic modulo
  `v`, while its canonical carry-kernel rank is at least `2^e-1` for every `e`
  (`ExternalVerification/Challenge.lean:137`;
  `Erdos249257/TotientTailCarryPeriod.lean:224`). This is one orbit-level
  conjunction, not the coefficient-side rank-only family. Natural friction:
  modulo a divisor of `v`, totient forcing disappears and `u` is geometric, so
  quotient periodicity cannot yield a finite-`ℚ`-rank upper bound. Boundary:
  necessary consequence of rationality only; no contradiction or #249
  irrationality proof follows. Claims registry:
  `totient_carry_kernel_anti_compression`.
- `primitive_coordinate_index_obstruction` — clearing `(φ*μ)(n)/n` through
  level `N` forces a two-tier primorial divisor; no fixed positive index clears
  every level.
  Boundary: finite Euler-coordinate obstruction, not an irrationality
  criterion.
- `lcm_factor_ideal_anchor_pulse_no_go` — for every `t≥3`, a synthetic survivor
  satisfies the factor-ideal and whole-ray-anchor constraints and survives
  every finite integer shift polynomial.
  Boundary: its letters need not be actual totient differences; nonlinear
  fresh-divisor arguments remain possible.
- `reciprocal_mass_bound` — a rational support value with odd denominator part
  `v` forces reciprocal mass at least `1/ord_v(2)`, or divergence; a
  dyadic-rational infinite support forces divergence or mass greater than one.
  Boundary: does not exclude every rational value.
- `unbounded_carry_states` — every infinite support with rational series value
  has an unbounded positive carry state.
  Boundary: rules out finite-state interpretations, not rationality itself.

Their registry identifiers lead to the declarations and current source
coordinates; operational lookup details live in the
[agent workbench](AGENT_WORKBENCH.md).

### Demand ledger

A demand is an unproved hypothesis extracted from a conditional theorem and
stored as a named Lean proposition. `ErdosProblems/DemandLedger/Basic.lean`
contains 101 named closed propositions; 23 are labelled substantive and the
rest are side conditions. The current prose frontier contains 52 entries.

The extraction snapshot in the audit log records 144 proved implication edges
among the 23 substantive demands, producing seven equivalence classes.
Seventeen substantive demands collapse to restatements of an open target rather
than smaller subproblems. For example:

- `G103_iff_erdos249` in
  `ErdosProblems/DemandLedger/edges/Discharge3_G103.lean` proves that the
  general lcm-window supply `G103` is equivalent to Problem 249 itself.
- `G103_iff_G097` in the same file identifies two supply formulations.
- `e_G083_G084` in `edges/ClusterE.lean` records one implication in the
  Problem 257 chain.

The ledger classifies obligations. It does not discharge an obligation merely
by naming it or proving it equivalent to the target.

## What is measured, not proved

Only measurements with an explicit tested range and explicit exception set are
listed here. Counts without preserved sample identities are not promoted to
release results.

| Measurement | Exact range | Exact failures or mismatches | Status |
|---|---|---|---|
| `Recon257.seamExcess s = 2` | `s = 5,…,102` (two overlapping scans, `5…64` and `58…102`) | No occurrence. | MEASURED. This makes the audited uses at `s=D+1`, `D≥60`, unobserved. |
| Three-row `hcof` on the seven audited survivor values | `D = {101,122,164,314,545,629,1112}` | Fails at all seven values. | MEASURED; every audited case satisfying `hcof` already died by depth 3. |
| Residual invariant | `s = 6,…,3000`, `d = 2,…,s-1` | Exactly `(s,d)=(13,7)`; residual `524419`, bound `524288`. | The exception is also PROVED by `Three/T1.not_residualInvariant`. |
| `hlow` and `hhigh` at late pairs | all late pairs with `s = 5,…,600` | `hlow` fails exactly at `(7,5)`; `hhigh` fails exactly at `(5,4)`. | The `hlow` exception is PROVED in `Decl/D4` and `Hlow/H1`. |
| Remainder-hit/greedy-support correspondence | `s = 5,…,900` | Zero mismatches. | MEASURED. It does not prove infinitely many hits. |
| `UnboundedLargestSkipLate` row event | `s = 5,…,1500` | Fails exactly at `s = 5,11,12,13`. | MEASURED. A finite interval does not prove eventual or unbounded behaviour. |
| Residual invariant on adjacent control rows | every rank of rows `s=12` and `s=14` | No failures. | MEASURED anti-vacuity check for the isolated `(13,7)` counterexample. |
| Diophantine height at one scale | `d=1000` | Denominator bit length `253815`; comparison value `d²/4=250000`. | MEASURED single-scale size check, not an asymptotic theorem. |
| Relative-margin scan | `d = 2,…,2000` | Record low `1.13×10^-4` at `d=1136`; no danger-zone instance. | MEASURED. It does not establish a positive lower bound. |

For the residual invariant, the maximum ratio away from the exception was
`0.9999807` at `(606,602)`.

The rows above are carried from a dated audit log whose raw run logs and
executable scan owners are not preserved in this release. Their stated finite
domains and exception sets are therefore historical measurement records, not
independently reproducible artifacts. A reported late-bit scan of about 14,000
ranks over `s=14,…,400` is omitted from the table because neither its exact
sample count nor its sample identities were preserved.

The audit also records a selection-biased certificate sample: at depth excess
`c=2`, 15 of 154 samples failed; at `c=3`, 601 of 5987 failed. The sample
identities are not preserved in the log, so these counts are not independently
reconstructible from the release and are not evidence for an equidistribution
law.

The remaining two measurements are source-backed and reproducible from this
release.

### Exact endpoint-certificate probe

Exact range: all `960` pairs `1≤N≤120`, `1≤h≤8`, searching `1≤L≤400`;
additional `h=1` probes at `N=200,500,1000,2000,5000`; exact LCM-diagonal pairs
`(N,h)=(lcm(1,…,t),lcm(1,…,t))` for `1≤t≤16`.

Exact failures or mismatches: no failures. Relative to the least arithmetically
admissible depth `L₀=min{L≥1:2ᴸ>2(N+h+L+2)}`, the rectangle's first
certificates have excess `0…11` (median `1`, mean `727/480`); the 16 indexed
diagonal rows have excess `0…4` (median `1`, mean `5/4`), and the 11 distinct
diagonal scales have mean `14/11`.

Status: MEASURED by exact integer arithmetic. Raw depth must grow with scale
because the certificate interval is empty below `L₀`; the finite excess
distributions prove no asymptotic law, equidistribution, bounded-excess
theorem, or cofinal supply. The exact probe remains available as operational
evidence through the agent workbench.

### Source-backed checked diagonal depths

Exact range: all 33 distinct `periodLcm` scales covering positive `t≤82`.

Exact failures or mismatches: every checked working depth has excess `0…4` over
`L₀` (median `1`, mean `40/33`). Five rows have proved least depths, with exact
excess `0…3`; the other 28 values are upper bounds on least-depth excess.

Status: FINITE SOURCE EXTRACTION from explicit Lean theorem signatures. It
establishes no bounded-excess law at untested scales and no cofinal supply.
The checked roster remains available as operational evidence through the agent
workbench.

## What was retracted

The detailed file-by-file record is in
[`TRUTH_AUDIT.md`](TRUTH_AUDIT.md). The main corrections are:

- `Lift/AngleB2.lean` no longer says that the survivor set is empty. Its theorem
  is conditional on a false `hcof` instance at each surviving class and on an
  unobserved `seamExcess = 2` hypothesis.
- `Lift/AngleB3.lean` no longer presents
  `ratchetOrbit_above_universal_barrier` as a live universal barrier. Its
  intended hypothesis fails at the initial row, and the proved nonrecurrence
  result covers only offsets `b ≥ Q+2`, not offsets `1,…,9`. The file now uses
  an actual Lean bridge to `Recon257`.
- `Skip/D1.lean` and `Skip/Wire1-3.lean` no longer claim to exclude residue
  classes. Their existential threshold exceeds every case admitted by their
  own hypotheses, and the same unobserved seam-excess premise remains.
- `Rem/C6.lean` no longer says the residual invariant is empirically true on
  `s = 6,…,3000`. It is false at `(13,7)`.
- `Rem/C3.lean` now distinguishes the branch it proved from the branch it only
  measured at the time, and points to `Three/T2.lean`, where the latter branch
  was subsequently proved.
- `Bit/R2.lean` labels `badRun_pins_remainder` as a conditional statement with
  no observed instance: it needs at least 12 consecutive bad rows, while the
  measured maximum was 3.
- `Three/T4.lean` and `Bit/Corr1.lean` no longer call `hlow` open. It is false
  at `(7,5)`, and that failure supplies a hit certificate.

No theorem was weakened or removed to make these corrections. The claims were
narrowed to the theorem types and the recorded counterexamples.

## What is open

### Exact questions for a human expert

The validated handoffs form a bounded set of exact questions. Each requested
input is `OPEN`; the consumer named under each question is a checked theorem.
The classification matters: the first question is the endpoint in exact normal
form, the next two are sufficient analytic producers for #249, and the last two
would produce a counterexample to universal #257 rather than prove its positive
statement. Their complete packets are indexed from the agent workbench.

No checked strictly weaker handoff currently implies the universal positive
statement of #257 for every infinite support. Named support families,
half-value analysis, reciprocal-mass bounds, and sublogarithmic zero-window
constraints are partial; treating any one as a universal proof route would
overstate what its checked consumer establishes.

The packet does not make an expert start cold. Every ask also carries a
low-confidence current hypothesis, enumerated alternatives, current evidence,
and the observation or theorem that would distinguish them; both are recorded
with each question below.

#### `XQ249-lcm-diagonal-supply` — diagonal supply

Exact `OPEN` input: for every `t₀`, find `t ≥ t₀` and `L` with a diagonal
certificate at `(lcm(1,…,t), lcm(1,…,t))`.

Payoff and boundary: equivalent to #249. A proof closes #249; until then this
is a restatement, not intermediate progress.

Current working guess: certificates occur beyond every scale, equivalently #249
is true.

Evidence that would change the guess: a rational representation or an
eventual-failure theorem decides the opposite branch. The exact rectangle has
first-depth excess `0…11`; across all 33 distinct checked diagonal scales
covering `t≤82`, working-depth excess is `0…4` (median `1`, mean `40/33`). Only
five diagonal depths are proved least, and finite low upper bounds neither
prove bounded excess nor decide the cofinal quantifier.

`PROVED` consumer:

```text
irrational_totient_series_iff_lcm_diagonal_certificate_supply
```

#### `XQ249-pivot-decorrelation` — pivot decorrelation

Exact `OPEN` input: cofinally supply the exact four pivot budgets: centred real
correlation `≤14X/25`, supplier mean and bad-supplier norms `≤X/100` each, and
non-supplier norm `≤8X/25`, with overlap `h≤L-s` and room
`16(2X+h+L+2)≤2^L`.

Payoff and boundary: sufficient for #249. The missing input is a
prime-distribution or residual-decorrelation estimate, not another certificate
reformulation.

Current working guess: for every shift, fixed `s,η` permit cofinally many
blocks satisfying overlap, room, and all four budgets; the centred real term is
likely the hard budget.

Evidence that would change the guess: exact failure requires one shift for
which every `s,η` eventually loses at least one clause. Infinitely many bad
blocks do not suffice. An exact four-budget producer proves #249.

`PROVED` consumer:

```text
irrational_totient_series_of_pivotResidualDecorrelation
```

#### `XQ249-adjacent-phase-separation` — adjacent phases

Exact `OPEN` input: for every `h>0` and `X₀`, find `X≥max(X₀,1)`, a depth `L`,
and adjacent `N,N+1∈[X,2X)` such that `16(2X+h+L+2)≤2^L` and their
first-harmonic phases have squared chordal separation at least `19/25`.

Payoff and boundary: sufficient for #249. Finite scans or average separation do
not meet the cofinal quantifiers.

Current working guess: qualifying adjacent separation occurs cofinally for
every shift.

Evidence that would change the guess: one shift and a cutoff beyond which no
admissible block, depth and adjacent pair reaches `19/25` kill this route;
infinitely many bad blocks alone do not. A cofinal adjacent-discrepancy theorem
at that threshold proves #249.

`PROVED` consumer:

```text
irrational_totient_series_of_adjacentPhaseSeparation
```

#### `XQ257-second-channel-separation` — second channel

Exact `OPEN` input: prove `HalfSecondChannelSeparatedRat n` for every `n≥7`,
i.e. that the exact rational second-channel phase stays at least
`1/6+(37/56)2^{-n}` from `1/3`; Lean checks `1,…,6`, and an independent exact
probe finds no failure through `n=1000`.

Payoff and boundary: proves `1/2` attainable. The finite-support exclusion then
forces the witness to be infinite, giving a rational counterexample to
universal #257. The finite probe does not move the quantifier; failure of this
route would not prove universal #257.

Current working guess: the separation continues for all `n≥7`; confidence
remains low despite an empty exact failure set on `1≤n≤1000`.

Evidence that would change the guess: the least measured margin on the open
range is `1033253069/8193024` at `n=7`, but `n=1001` onward is unmeasured. One
failed level closes only this socket; a global reachability invariant or
uniform sign estimate proves membership and, with finite-support exclusion, a
counterexample.

`PROVED` consumers:

```text
half_mem_mersenneAchievementSet_of_secondChannelSeparationRat_from_seven
positiveMersenneSupportValue_coe_finset_ne_half
positiveMersenneSupportValue_eq_erdosSupportSeries
```

The source-bound second-channel measurement re-evaluates the rational greedy
recurrence and the complete failure set
for `1≤n≤1000` from the definitions in
`Erdos249257/GreedyAchievementSet.lean`. The generated artifact is
[`docs/measurements/second_channel_separation_probe.json`](measurements/second_channel_separation_probe.json).
Its status is `MEASURED`, not `PROVED`; in particular, the empty finite failure
set does not establish the all-`n` hypothesis consumed by the Lean theorem.

#### `XQ257-middle-producer-tail-escape` — middle producer

Exact `OPEN` input: at every actual middle transition from rank `13`, write `C`
for the checked producer carry and `Θ` for its nonnegative coefficient tail.
Prove `C=-3` or `(1≤C and Θ<C)`.

Payoff and boundary: also proves `1/2` attainable; at the putative last-false
row the checked `-3` theorem removes the first disjunct, and the
finite-support exclusion then forces an infinite witness. The socket must
exclude every actual `C≤0`, `C≠-3`, and control `Θ<C` for every positive cell.

Current working guess: every actual middle row lies in the `C=-3` branch or has
`1≤C` and `Θ<C`.

Evidence that would change the guess: one actual nonpositive cell other than
`-3`, or one positive cell with `Θ≥C`, refutes this socket. A proof of the
displayed disjunction at every actual row proves membership; the final `-2`
sieve alone does not.

`PROVED` consumers:

```text
half_mem_mersenneAchievementSet_of_middleProducerTailEscapeExceptNegThree
positiveMersenneSupportValue_coe_finset_ne_half
positiveMersenneSupportValue_eq_erdosSupportSeries
```

### Cold-reader review boundary

The repository cannot certify its own human legibility. It therefore exposes a
second `OPEN` question: can an independent reader, starting from a fresh clone,
recover the calibrated verdict in at most ten minutes? The request is exact,
including the response schema, its consumer, payoff, and boundary:

The low-confidence working guess is that a reader will recover both open
boundaries and the zero Farey delta, but may still underweight the concrete
non-restatement results. The protocol distinguishes that failure from the
opposite error—mistaking finite or conditional results for a near-solution.

A structurally accepted response from an identified independent reader returns
an explicit rubric for its result summaries, evidence paths and verdict. A
second identified evaluator binds a final review to the response digest. The
validator cannot authenticate either person or the elapsed time, and does not
pretend to judge free prose by itself. Neither receipt validates the mathematics
or establishes priority or novelty. The same query without a domain filter
returns this systems question beside the five theorem-connected mathematical
questions; respondent-facing output omits the evaluator's scalar answer key.

### Erdős Problem 249

The irrationality of

```text
∑_{n≥1} φ(n)/2^n
```

is open. The finite band through `t=82` and the 123 distinct certificates in
the bounded historical off-diagonal roster do not provide the quantified,
unbounded certificate supply required by the reduction.

### Erdős Problem 257

The statement that

```text
∑_{n∈A} 1/(2^n-1)
```

is irrational for every infinite `A` is open. In particular, membership of
`1/2` in the Mersenne achievement set is not proved.

At level `d`, the rational compared with the remaining tail changes with `d`.
A naive common-denominator construction gives an upper height bound of the
form `2^O(d^2)`, but the repository proves neither a matching lower bound nor a
`Theta(d^2)` law for the reduced denominator along the actual greedy support.
The displayed separation boundary has an explicit correction proportional to
`2^{-d}`. No registered theorem controls the required sign uniformly at this
moving boundary, and there is no fixed rational approximation target to which
a fixed-number theorem applies directly.

Irrationality alone is insufficient because the open branch asks for the sign
of a nonzero tail difference, not merely for non-equality.

## Verification and continuation

The exact build, query, replay, contribution, and source-bound reproduction
routes are maintained in the [agent workbench](AGENT_WORKBENCH.md), where they
can stay current without interrupting the mathematical account here. The
historical isolated-tree timings were a dated manual record, not a
machine-revalidated receipt for the present source tree. Lean checks certify
the displayed formal statements; they do not certify novelty, priority,
significance, or the still-open Erdős endpoints.

</details>

## Recovered from the front page
The README is the human front door and is held to a short word budget. The sections below were moved here verbatim so that a cold reader who follows the front page still reaches every statement it used to carry.

### Problem statements

[`docs/papers/corpus.json`](papers/corpus.json) is the machine-readable
index of the papers.

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

The table is the complete problem inventory: no query is required to learn
which problems exist or what they ask, and reading it does not require
ai_workflow, a sibling repository, a cache, or network access. It is navigation, not proof
authority or a novelty claim. Drilldown is optional and uses only tracked
public files; it needs no private checkout, sibling repository, cache, or
network access.

### External verification

Nineteen selected Lean propositions are declared a second time, without proofs,
in [`ExternalVerification/Statements.lean`](../ExternalVerification/Statements.lean).
Comparator checks the proof-bearing module against those separate declarations
and against a fixed axiom budget of `propext`, `Quot.sound`, and
`Classical.choice`; an adversarial fixture alters one statement and must be
rejected. [`formalization.yaml`](../formalization.yaml) records, per selected
result, the contribution class, exact statement, source declaration, boundary,
`sorry` count, and axioms. Manifest and [verification packet](EXTERNAL_VERIFICATION.md)
cover all eight problem programmes; [replay](EXTERNAL_VERIFICATION_REPLAY.md)
gives the reviewer-run Linux route. The same check runs in continuous
integration against the reviewed source commit. Comparator checks propositions
only: no paper deduction, cited theorem, external computation, intended
meaning, novelty, or significance.

[RESULTS](RESULTS.md) gives each strongest checked result and its limit;
[prior art](PRIOR_ART.md) records classical, subsuming, and earlier public
work. The finite #249 result is the
classical Farey/mediant bound (numerical delta `0`): Farey's method supplies
the number directly, exactly the Farey bound, not an improvement. Full-kernel
infinite rank is Coons's prior result, the all-base rank paper theorem uses
Martin externally, and #269's two-prime result is not first.

This self-contained public Plectis checkout is not an entrypoint into any private
development system. `v0.9.0` is the latest tagged release and citation anchor;
[`docs/claims.json`](claims.json) pins the exact formal-source checkpoint
this release ships. Lean source checked by the pinned Lean kernel is
proof authority; do not infer results from private or unreleased work.

### What the formal source establishes

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

#### Other exact mathematics in the corpus

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
[RESULTS](#other-standalone-exact-obstructions).

An exact final-skip band formula does not show that the actual orbit avoids
an unsafe band.

[Orientation](ORIENTATION.md) routes claims; the retained
[mathematics paper](../erdos249-257-main-paper.pdf) preserves the joint
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

[`SCOPE.md`](../SCOPE.md) is the short boundary statement. The exact expert
handoffs state what input is requested, current guess, alternatives,
discriminating evidence, checked consumer, and endpoint-or-counterexample
boundary. See
[RESULTS](#exact-questions-for-a-human-expert) and
`python3 scripts/query_expert_handoffs.py`. A refuted route is withdrawn in
the next edition and the refutation credited.
