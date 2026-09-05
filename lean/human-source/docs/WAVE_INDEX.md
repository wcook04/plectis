<!--
SPDX-FileCopyrightText: 2026 Will Cook
SPDX-License-Identifier: Apache-2.0
-->

# Wave index

Wave labels are **development chronology**, not Lean import order.

Read order for humans:

1. `docs/orientation.json` or `docs/ORIENTATION.md` — select one mathematical
   programme, claim, or exact remaining open proposition.
2. `docs/SOURCE_MAP.md` — follow that selected intention into a bounded module
   route.
3. `paper/erdos249-257-main-paper.tex` — read the authored mathematical
   exposition and its source handles.
4. this file — recover development chronology only when chronology is the
   question.
5. `Erdos249257.lean` and `ErdosProblems.lean` — inspect package topology only
   when import structure is the question.

For an external statement-identity handoff, use the generated [Formal
Conjectures crosswalk](FORMAL_CONJECTURES_CROSSWALK.md). It binds each of the
eight problem rows to its pinned upstream declaration, source hash, and local
problem route. For a module or paper handle, use
`python3 scripts/query_corpus.py --module <module_path_or_sigil>` or
`--paper-anchor <TeX_label_or_source_ref>` to recover the corresponding
proof/source context before returning to the problem's exact boundary.

Lean source checked by the pinned Lean kernel is proof authority. Wave order
does not strengthen a claim or close an exact open proposition. Erdős #249 and
the universal form of #257 remain open.

## Chronology map

| Band | Where it lives | Notes |
|---|---|---|
| Pre-wave / early kernel mass | `Erdos249257/CertificateKernel.lean` | Core #257 support-family and certificate machinery assembled before the separately named #249 modules |
| Waves 8–16 | mainly `CertificateKernel.lean` | Earlier kernel layers retained inside the assembled microkernel |
| Waves 17–25 | separately named modules under `Erdos249257/` | Reader-facing ladder, detailed below |
| Wave 26–27 | public material inside `CertificateKernel.lean` | Not a separate top-level module |
| Wave 30 | referenced in `LcmConeNonflat.lean` | Small-prime support of the cone-window argument |
| Generated certificates | `GeneratedCertificates.lean` + `GeneratedCertificates/*` | Generated finite certificate layers, not waves |
| Carry trunk | five post-wave modules under `Erdos249257/` | Not waves; a shared binary-carry layer over the kernel, see below |
| Diagonal pincer frontier | exact decomposition modules, algebraic support, and finite prime-certificate shards | Post-wave #249 work; sharpens the open certificate-supply obligation without closing it |

## Waves 17–25 (named modules)

Each module is a self-contained step with a header docstring stating its own honest boundary. The import chain is `GapFareyBound → MersenneLambertLadder → … → LcmConeNonflat → CertificateKernel ← GeneratedCertificates`.

| Wave | Module |
|---|---|
| 17 | `GapFareyBound.lean` |
| 18 | `MersenneLambertLadder.lean` |
| 19 | `GeometricCoprimality.lean` |
| 20 | `GcdMomentCalculus.lean` |
| 21 | `TotientTailPeriodKiller.lean` |
| 22 | `CarrySurvivorExtinction.lean` |
| 23 | `LcmDiagonalReduction.lean` |
| 24 | `LcmConeFlatness.lean` |
| 25 | `LcmConeNonflat.lean` |

### Wave 17 — `GapFareyBound.lean`

**Farey-gap denominator bounds.** A mediant/Farey argument places any rational
`m/q` inside a forbidden gap, so no `q` below the bound can represent `S`.
Elementary and per-window; clears `q ≤ 2.49×10¹⁷` (`K=120`) and
`q ≤ 7.96×10³⁴` (`K=240`).

### Wave 18 — `MersenneLambertLadder.lean`

**The Mersenne–Lambert ladder**, machine-checked: the rational rungs
`L(μ)=1/2`, `L(φ)=2`, the positive lift `L(A)=S`, and the Möbius-square lens
`S = 1/2 + ∑ μ(d)/(2^d−1)²`. Engine: a signed, linear-growth weighted Lambert
rearrangement.

### Wave 19 — `GeometricCoprimality.lean`

**`S` as coprime-pair mass.** `#{(a,b) : a+b=n, 0<a, gcd(a,b)=1} = φ(n)`, so at
`r=1/2`, `S − 1/2 = P(gcd(X,Y)=1)` for independent fair-coin waiting times.
Base 2 is the unique self-normalising point of the geometric law.

### Wave 20 — `GcdMomentCalculus.lean`

**The squared transform** `L₂(f) = ∑ f(d)/(2^d−1)² = E[(f * ζ)(gcd(X,Y))]`,
since gcd-divisibility factorises across independent coordinates. Yields
`L₂(μ) = S − 1/2`, the gcd-moment ladder, and Pillai's gcd-sum function.
The exact family return is the [probabilistic gcd-geometry route](SOURCE_MAP.md#complete-eight-problem-return-matrix):
the [totient gcd-moment declaration](../Erdos249257/GcdMomentCalculus.lean#L235)
and
the [Stern–Brocot cylinder recursion](../Erdos249257/GcdMomentCalculus.lean#L474),
[cylinder remainder bound](../Erdos249257/GcdMomentCalculus.lean#L525), and
[run-stability declaration](../Erdos249257/SternBrocotRunGeometry.lean#L343)
return to the paper's [probability-coordinate appendix](papers/full-text/erdos249-257-main-paper.md#app:lambert-probability),
with the stable records `res:directionnormalization`, `res:sternbrocotcylinders`,
and `res:sternbrocotruns`. The cylinder-law family is also directly recoverable
through `python3 scripts/query_corpus.py --claim stern_brocot_cylinder_law`,
which returns the `probabilistic_gcd_geometry` route and its source-fingerprinted
resume handoff. These exact identities and combinatorial bounds do not close
the open #249 irrationality or unbounded-certificate obligations.

### Wave 21 — `TotientTailPeriodKiller.lean`

**Period, not digits.** Rationality of `S` forces the tail-period law
`R_{N+h} − R_N ∈ ℤ`; missing that integer by a decidable margin is a finite
"kill". Reduction:

```
irrational_totient_series_of_certificate_supply
```

### Wave 22 — `CarrySurvivorExtinction.lean`

**Multiple-period collapse.** Every multiple of a period is a period, so the
obligation collapses onto the one-parameter family `periodLcm t = lcm(1..t)`.
Adds the carry-survivor orbit certificate (a bounded integer orbit that must
escape a narrow strip).

### Wave 23 — `LcmDiagonalReduction.lean`

**Diagonal collapse.** Standing on the ray (`N = periodLcm t`) removes the
second parameter: #249 follows from one ℕ-indexed decidable sequence
`∃ L, certifiedKill (periodLcm t) (periodLcm t) L` holding infinitely often.

### Wave 24 — `LcmConeFlatness.lean`

**Cone-flatness law.** Rationality forces one fractional constant on the whole
lcm cone `{k·periodLcm t}`. Certificate **completeness**: a kill exists iff the
tail difference is a non-integer:

```
exists_certifiedKill_iff_tail_diff_notMem_int
```

Plus rank-2 second-difference certificates.

### Wave 25 — `LcmConeNonflat.lean`

**Cone non-flatness refuter.** Interrogates a whole menu of cone vertices at
once: if their one-sided arcs shared a common fractional part, the
minimal-deep-tail vertex would be a common endpoint, and its certificate row
denies exactly that. Sharper than pairwise; genuinely joint for menus of
size ≥ 3.

## Carry trunk (post-wave modules)

These five modules are **not waves**. They form a shared binary-carry layer added after the chronology above, building on `CertificateKernel`: what rationality of a binary series forces on its integer carry states. Reading order: `GenericTailOrbitRigidity → GreedyAchievementSet → BooleanMobiusCarry → RationalSupportCarrySkeleton → SublogDivisorCoverage`.

### `GenericTailOrbitRigidity`

Depends on `CertificateKernel`.

For coefficients `c(n) ≤ n`, the binary series `∑ c(n)/2ⁿ` is rational exactly
when a tempered integer carry orbit exists (`u(N+1) = 2·u(N) − v·c(N+1)` with
`u(N)/2ᴺ → 0`); every such orbit is rigid, equal to the scaled analytic tail
`v·T_c(N)`. Balanced pulses also prove unbounded exact successor fan-out,
ruling out a generic autonomous finite-state decoder.

Main theorems:

```
temperedBinaryOrbit_eq_scaledTail
binaryCoeffSeries_rational_iff_exists_temperedBinaryOrbit
balancedPulse_no_autonomous_decoder
```

### `GreedyAchievementSet`

Depends on `CertificateKernel`.

Greedy geometry for the Mersenne achievement set (values `∑_{n∈A} 1/(2ⁿ−1)`):
strict superincreasing tail inequalities, the quantitative gap asymptotic
`(2/3)·4⁻ⁿ + O(8⁻ⁿ)`, compact/perfect/totally-disconnected/nowhere-dense
structure with Lebesgue measure one, exact real and rational greedy
recurrences, membership ⇔ all-level greedy survival, sound one-sided finite
rational death certificates (the exact level-one certificate excludes `3/4`),
and uniqueness of normalised support coding. Certificates prove nonmembership
only.

Main theorems:

```
volume_mersenneAchievementSet
isNowhereDense_mersenneAchievementSet
mem_mersenneAchievementSet_iff_greedy_survival
certifiedGreedyMersenneDeath_not_mem
```

### `BooleanMobiusCarry`

Depends on `GenericTailOrbitRigidity`.

Boolean–Möbius carry coordinates for support series: the Lambert coefficient
`f_A(n) = #{a ∈ A : a ∣ n}` satisfies `f_A = 1_A * ζ` and `μ * f_A = 1_A` on
positive integers; rationality of the support series is equivalent to a
tempered carry orbit whose carry quotient is exactly `f_A`; normalised nonempty
supports with value `p/q` correspond exactly to quotient-only Boolean Möbius
carry certificates. The displayed value `1/2` has a canonical affine-orbit
criterion. Worked support `{2,3}`: value `10/21`, period-six orbit
`10, 20, 19, 17, 13, 26`.

Main theorems:

```
erdosSupportSeries_rational_iff_exists_temperedCarry
exists_normalized_support_fraction_iff_exists_booleanMobiusCarry
support_half_iff_affineBinaryOrbit_tempered
```

### `RationalSupportCarrySkeleton`

Depends on `BooleanMobiusCarry`.

Residue wraps and reciprocal mass: the binary repetend identity (least positive
residues in a complete doubling cycle sum to odd modulus × number of wraps), an
algebraic one-wrap classification, the Cesàro identification of mean support
tails with the reciprocal mass `∑_{a∈A} 1/a`, the exact excess-mean identity,
the rationality-forced lower bound `1/ord_v(2)` on reciprocal mass, the dyadic
strengthening (mass divergent or `> 1` for infinite dyadic-rational supports),
and global unboundedness of the positive carry state attached to any infinite
support with rational value.

Main theorems:

```
sum_doublingResidue_eq_mul_wrapCount
one_div_oddOrder_le_reciprocalMass_of_support_fraction
dyadic_support_fraction_reciprocalMass_diverges_or_gt_one
exists_unbounded_shifted_odd_tail_nat_state_of_support_fraction
```

### `SublogDivisorCoverage`

Depends on `RationalSupportCarrySkeleton`.

**Sublogarithmic divisor coverage.** If an Erdős support series has a rational
value, consecutive zero windows in its divisor-count coefficient `f_A` have
length at most `ε log₂(N+1) + B` for every `ε > 0`, with `B ≥ 0` obtained for
that support and numerator. The proof builds `B` from `ε`, `c` and `v`, but the
support and numerator are bound before the existential, so this declaration
does not export one constant uniform across all supports. The proof composes an
explicit fixed-power divisor bound (`τ(n)^k ≤ (k^{2^k})^k n`), a binary-tail
estimate, and the exact carry recurrence. This constrains support coverage; it
does not solve universal #257.

Main theorem:

```
supportCoeffZeroWindow_length_le_eps_logb_add
```

None of these modules claims a solution of Erdős #249 or #257. The contribution boundary is theorem-family-specific: the carry recurrence and strict-tail geometry have direct prior art (Han Wang; Kovač–Tao); Möbius inversion, repetend algebra, and divisor averaging are classical; the converse/rigidity, certificate-normal-form, and coupled reciprocal-mass families remain exact-source-comparison candidates. No priority claim is made.

`SupportSunflowerDichotomy` is an adjacent conditional #257 route. It gives
the exact carry conversion for finite-core orthogonal-petal bouquets and
records an explicit alternating-core squared-prime-petal support. Its uniform
tail-selection hypothesis is not proved, so it adds no unconditional support
family.

`CompositeDilationDefect` supplies the exact finite correction when a
composite support element dilates the divisor-count coefficient, and bounds
that correction for orthogonal-petal bouquets. It is a local identity, not a
correlation or irrationality theorem.

`MaximalOmegaLayer` extends the one-prime-power identity to two distinct
prime-power layers. It records finite coefficient algebra only, with no
bounded-Ω or irrationality endpoint.

## Diagonal pincer frontier (post-wave #249 band)

This band refines the lcm-diagonal reduction.  Its main reading chain is
`DiagonalPincerDecomposition → SquaredMersenneDiagonalEnclosure →
DiagonalFreshLossBridge`.  The first module makes diagonal integrality exactly
equivalent to a foreign-defect term hitting a full-target interval.  The second
centres the diagonal expression at a Lambert projection and bounds the signed
squared-Mersenne tail.  The third turns the remaining fresh loss into an exact
integer projection and then into binary suffix conditions.  Every
irrationality theorem in this band retains an explicit unbounded-supply
hypothesis.

`DiagonalPincerCertificates` and the `DiagonalPincerCertificatesT*`
aggregators assemble 28 checked scales through `t = 64`; the many
`DiagonalPincerPrimeCertificates.*` files are finite proof shards, not separate
mathematical claims.  The denominator/cyclotomic chain
`RadicalMobiusShadow → RepunitMobiusNumerator → CyclicTensorMobiusShadow →
CyclotomicProjectionOfShadow → PrimePowerJumpDynamics →
MersenneShadowCyclotomicNoncollapse → MersenneShadowDenominatorGrowth`
supplies exact rational-denominator information used by the frontier.  The
remaining named modules provide finite identities or conditional interfaces;
their headers state the boundary locally.

## Transport and curvature companion band

This post-wave #249 band forms a second, self-contained reading chain:
`CurvatureCarry → ExponentOnlyTransport → JointExponentTransport`, with
`PrimeJumpMigration → PrimeJumpWindow`, `ThreeTransportBoundary`,
`FirstHarmonicGap`, `TropicalCurvatureCarry`, and
`LcmFactorIdealPulseObstruction` as adjacent branches.  It
proves exact dyadic window decompositions, affine old-channel annihilation,
new-channel migration, two concrete finite certificates, and two scoped no-go
theorems: fixed local precision and finite LCM factor/anchor shift algebra.
The latter is a synthetic countermodel rather than a model of actual totient
differences.  It does not prove an unbounded certificate supply or a
first-harmonic estimate, so #249 remains open.  The former one-sided companion
is retired; its checked declarations remain queryable through the claim
registry and source map.

The finite factor-ideal result is one claim inside the reviewed
`transport_strategy_no_go_boundaries` family, alongside the fixed-precision
obstruction.  Retrieve that family with
`python3 scripts/query_corpus.py --publication-family transport_strategy_no_go_boundaries`, or inspect the factor-ideal claim with
`python3 scripts/query_corpus.py --claim lcm_factor_ideal_anchor_pulse_no_go`.
Its exact formal anchors are
[`lcm_factorIdeal_finiteRank_shiftAlgebra_not_sufficient`](../Erdos249257/LcmFactorIdealPulseObstruction.lean#L798),
[`lcm_factorIdeal_sparseAnchor_not_sufficient`](../Erdos249257/LcmFactorIdealPulseObstruction.lean#L866),
and [`lcmAnchorPulse_t3_letters`](../Erdos249257/LcmFactorIdealPulseObstruction.lean#L895).
The family remains a synthetic survivor: its forcing letters need not be
actual totient differences, nonlinear fresh-divisor arguments remain outside
the result, and no unbounded certificate supply follows.

## Source-current #1041 frontier (not a wave)

The public #1041 research corpus is a dated source projection, not a new Lean
wave and not a reviewed claim-registry surface. Its source checkpoint is
`6658deca35adde05f60bd2a19c76da996698bc9a`. Read
[`research_corpus/Erdos1041/FRONTIER.md`](../research_corpus/Erdos1041/FRONTIER.md)
first: it supersedes stale activation rows by naming the 2026-08-29
refutations, the surviving carriers, and the exact open gaps. Then consult
[`STRONGEST_RESULTS.json`](../research_corpus/Erdos1041/STRONGEST_RESULTS.json)
for the machine-readable premise/consumer map and
[`CORPUS_MANIFEST.json`](../research_corpus/Erdos1041/CORPUS_MANIFEST.json)
for the published-file and digest inventory.

For a machine-first handoff, run
`python3 scripts/query_corpus.py --route erdos_1041`. The route checks the
four public frontier files against their indexed digests and returns the
35-result/open envelope; for a resumable, source-fingerprinted packet use
`python3 scripts/query_route_memory.py --problem 1041`. Neither route enters
the reviewed claim registry, Comparator, or Lean proof authority.

Use this compact reading order:

1. [`AttachmentAwareReeb.md`](../research_corpus/Erdos1041/AttachmentAwareReeb.md)
   and [`GenericSufficiencyClosure.md`](../research_corpus/Erdos1041/GenericSufficiencyClosure.md)
   for the surviving hub-selection carrier and its generic-to-closed
   extension.
2. [`NearFeketeRadialAngularSplit.md`](../research_corpus/Erdos1041/NearFeketeRadialAngularSplit.md)
   and [`Degree5AssemblyAndSharpenedCuts.md`](../research_corpus/Erdos1041/Degree5AssemblyAndSharpenedCuts.md)
   for the new near-regular and degree-five reductions. The origin-spoke and
   critical-value-envelope rows refuted in `FRONTIER.md` are not continuation
   targets.
3. [`PartialClusterPreimagePerimeterIdentity.md`](../research_corpus/Erdos1041/PartialClusterPreimagePerimeterIdentity.md),
   [`TiedNewtonFaceFibreProduct.md`](../research_corpus/Erdos1041/TiedNewtonFaceFibreProduct.md),
   and [`ExteriorRootProductCovering.md`](../research_corpus/Erdos1041/ExteriorRootProductCovering.md)
   for exact perimeter, moment, and covering premises; each still requires an
   attachment-compatible selector or metric consumer.
4. [`MinimalHubArmBudgetRefutation.md`](../research_corpus/Erdos1041/MinimalHubArmBudgetRefutation.md)
   and [`SeparatrixAggregateReduction.md`](../research_corpus/Erdos1041/SeparatrixAggregateReduction.md)
   for the strongest negative evidence and the machinery that survives only
   as a possible tool for a different functional.

The paper-facing route remains
[`erdos-1041-lemniscate-newton-flow.md`](papers/full-text/erdos-1041-lemniscate-newton-flow.md),
which points to the checked Newton-flow declarations and states the older
topology/metric boundary. The current source frontier does not change the
open status of #1041, and its machine rows must not be read as Lean claims.

## Expansion-problem reading handoff (not a wave)

The five expansion roots have no shared Lean-wave chronology. Their exact
paper/source joins and open boundaries live in the
[complete eight-problem return matrix](SOURCE_MAP.md#complete-eight-problem-return-matrix)
and the generated [`problems.json`](problems.json) index. The paper notes are
the shortest first read:

| Problem | Paper note | Principal source |
|---|---|---|
| #68 | [`factorial carries`](papers/full-text/erdos-68-factorial-denominator-irrationality.md) | `ErdosProblems/Erdos68/FactorialZeroPlateau.lean` |
| #243 | [`reciprocal-tail rigidity`](papers/full-text/erdos-243-reciprocal-tail-rigidity.md) | `ErdosProblems/Erdos243/ReciprocalTailRigidity.lean` |
| #251 | [`prime-gap dyadic tails`](papers/full-text/erdos-251-prime-gap-dyadic-series.md) | `ErdosProblems/Erdos251/PrimeGapDyadicTail.lean` |
| #269 | [`three-prime running lcm`](papers/full-text/erdos-269-three-prime-running-lcm.md) | `ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean` |
| #1049 | [`rational-base Lambert`](papers/full-text/erdos-1049-rational-base-lambert.md) | [`RationalBaseLambert`](../ErdosProblems/Erdos1049/RationalBaseLambert.lean#L155) · [`ZudilinHeightRegion`](../ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L91) · [`RationalPadeArithmetic`](../ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L30) · [`HermitePadeNoGo`](../ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L103) · [`QAperyDiagonalNonEquivalence`](../ErdosProblems/Erdos1049/QAperyDiagonalNonEquivalence.lean#L67) · [`ZudilinConeArithmetic`](../ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L286) |

These notes preserve their own evidence classes and limitations; the source
map is the route to the exact continuation obligation, not a chronology or a
claim-status authority.

<!-- BEGIN generated_package_shape -->
<!-- Generated by scripts/build_corpus_descriptor.py; do not edit this region. -->
## Package shape

- `CertificateKernel.lean` (0.85 MiB, 19,278 lines, 845 declarations; 519 theorems and 275 lemmas): the assembled microkernel and headline interfaces.
- `GeneratedCertificates.lean` (1.18 MiB, 27,728 lines, 1,174 declarations) plus 3 generated shards: finite certificate instances checked by the Lean kernel.
- The diagonal-pincer family contains 495 isolated prime-certificate modules and 16 scale aggregators. The shards are indexed through aggregators rather than presented as separate mathematical claims.
- Entire checked corpus: 1,058 modules, 153,671 declarations, 151,397 theorem-like declarations, and 8,171 manifest-marked generated-certificate declarations (a classification floor, not the generated share). The release gate rejects `sorry`, `admit`, custom `axiom` declarations, and `native_decide`.

These are generated inventory facts, not mathematical claim counts. The declaration atlas
and Lean source remain the drilldown owners.
<!-- END generated_package_shape -->
