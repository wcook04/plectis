<!--
SPDX-FileCopyrightText: 2026 Will Cook
SPDX-License-Identifier: Apache-2.0
-->

# Source map

## Bounded reader route

Start from one mathematical question rather than decoding the complete import
graph:

1. Read `docs/orientation.json`, or its human projection
   `docs/ORIENTATION.md`, and select one programme, claim, or exact remaining
   open proposition.
2. Run one bounded lookup:
   `python3 scripts/query_corpus.py --route <programme_id>`,
   `python3 scripts/query_corpus.py --claim <claim_id>`, or
   `python3 scripts/query_corpus.py --open <remaining_open.id>`.
3. Follow the returned paper label into the authored exposition and its
   declaration or source handles into the modules grouped below.
4. Read `Erdos249257.lean` or `ErdosProblems.lean` only when package topology
   itself is the question. Read `docs/WAVE_INDEX.md` for chronology, not as the
   recommended mathematical reading order.

Lean source checked by the pinned Lean kernel is proof authority. This map is
authored navigation: it does not strengthen a claim, replace
`docs/claims.json`, or close an exact remaining-open proposition. Erdős #249
and the universal form of #257 remain open.

## Signal-first reviewed spine

Use the current [Palomar result showcase](PALOMAR_RESULT_SHOWCASE.json) for the
source-reviewed family universe and its selected, represented, subordinate,
deferred, rejected, and long-tail dispositions. It is a selection projection,
not a claim count or proof authority. The generated [verification dossier](EXTERNAL_VERIFICATION.md#mathematical-signal-spine)
expands the same spine with exact declarations, hard mechanisms, evidence
classes, and surviving boundaries. Its ranked path starts with the completed
full-support #257 result, then the conditional actual-LCM and first-harmonic
#249 routes, followed by the actual-prime-gap #251 and local-window #269
reductions; use the matrix below to return to #68, #243, #1041, or #1049.
Support lemmas remain subordinate to their family, and every conditional
producer or bridge remains explicit.

## #1041 / source-current frontier

Problem #1041 has a second, source-only navigation route in addition to the
Lean-backed Newton-flow note. Start with the dated [frontier delta](../research_corpus/Erdos1041/FRONTIER.md),
then use the [strongest-result map](../research_corpus/Erdos1041/STRONGEST_RESULTS.json)
and the [corpus manifest](../research_corpus/Erdos1041/CORPUS_MANIFEST.json).
The frontier delta is the authority for rows refuted after the activation map
was generated; do not rebuild those rows merely because they remain in the
machine map.

The high-signal reading routes are:

- [hub selection and generic closure](../research_corpus/Erdos1041/AttachmentAwareReeb.md)
  → [GenericSufficiencyClosure](../research_corpus/Erdos1041/GenericSufficiencyClosure.md):
  the surviving parent carrier is `min_c L(c) <= 2` on the ray-separated locus,
  followed by lower-semicontinuity closure.
- [quantitative Fekete stability and radial/angular reduction](../research_corpus/Erdos1041/NearFeketeRadialAngularSplit.md)
  → [degree-five sharpened cuts](../research_corpus/Erdos1041/Degree5AssemblyAndSharpenedCuts.md):
  the new tools localise the residual, but do not prove the degree-five or
  unrestricted theorem.
- [partial-cluster perimeter identity](../research_corpus/Erdos1041/PartialClusterPreimagePerimeterIdentity.md)
  → [tied-fibre moment hierarchy](../research_corpus/Erdos1041/TiedNewtonFaceFibreProduct.md):
  these are exact geometric/algebraic premises for future selection work, not
  a completed compatible-root selector.
- [new exterior-root product covering](../research_corpus/Erdos1041/ExteriorRootProductCovering.md)
  and [separatrix aggregate reduction](../research_corpus/Erdos1041/SeparatrixAggregateReduction.md):
  read their explicit hypotheses and refutations before treating either as a
  parent route.

The [earlier paper note](papers/full-text/erdos-1041-lemniscate-newton-flow.md)
remains the paper-facing route to the checked declarations in
`ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean`. The research corpus is
not part of `docs/claims.json`'s reviewed claim authority: its files preserve
source-level premises, computations, no-go results, and open boundaries.
Nothing in this route settles #1041; the exact continuation boundary is in
`FRONTIER.md` and must be read before any new proof search.

## Complete eight-problem return matrix

The per-problem [machine index](problems.json) is the source for the complete
module, paper, and open-obligation inventories. Expand each row's
`what_is_checked` and `what_is_not_checked` fields before treating its strongest
checked source as the whole result inventory: they are the evidence ceiling,
not additional claims. This single matrix makes the same route bidirectional:
start at a public problem id, reach the strongest checked source and paper
record, then use the exact index handles to resume the open boundary; a paper
or source reader can return with the `--route` command in the second column.
The checked sources under `ErdosProblems.lean` are exact Lean propositions,
not reviewed claim-registry entries. For #249 and #257, the reviewed route is
an additional registered claim spine, not a replacement for the problem-owned
index route.

| Problem | Problem return / source back-route | Strongest checked source | Paper and source record |
|---|---|---|---|
| #68 | `python3 scripts/query_corpus.py --route erdos_68` | [`FactorialZeroPlateau.lean`](../ErdosProblems/Erdos68/FactorialZeroPlateau.lean) | [paper note](papers/full-text/erdos-68-factorial-denominator-irrationality.md) · [TeX source](../paper/erdos-68-factorial-denominator-irrationality.tex) |
| #243 | `python3 scripts/query_corpus.py --route erdos_243` | [`ReciprocalTailRigidity.lean`](../ErdosProblems/Erdos243/ReciprocalTailRigidity.lean) | [paper note](papers/full-text/erdos-243-reciprocal-tail-rigidity.md) · [TeX source](../paper/erdos-243-reciprocal-tail-rigidity.tex) |
| #249 | `python3 scripts/query_corpus.py --route erdos_249` · reviewed return: `python3 scripts/query_corpus.py --route erdos249_certificate_story` · family return: `python3 scripts/query_corpus.py --route probabilistic_gcd_geometry` | [`TotientStrictPrimeEscape.lean`](../ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean) · [`GcdMomentCalculus.lean`](../Erdos249257/GcdMomentCalculus.lean#L235) · [`SternBrocotRunGeometry.lean`](../Erdos249257/SternBrocotRunGeometry.lean#L343) | [paper note](papers/full-text/erdos-249-binary-totient-series.md) · [TeX source](../paper/erdos-249-binary-totient-series.tex) · [probability/cylinder explanation](papers/full-text/erdos-249-binary-totient-series.md#exact-identities-and-representations.) |
| #251 | `python3 scripts/query_corpus.py --route erdos_251`<br>Palomar family spine (run `python3 scripts/query_semantic.py family-relations <family_id>`): `prime_gap_reformulation` → `small_mismatch_criterion` → `dyadic_tail_integrality_classification` → `integral_shift_classification` → `totient_shift_propagation` → `coefficient_only_no_go` | [`PrimeGapDyadicTail.lean`](../ErdosProblems/Erdos251/PrimeGapDyadicTail.lean) | [paper note](papers/full-text/erdos-251-prime-gap-dyadic-series.md) · [TeX source](../paper/erdos-251-prime-gap-dyadic-series.tex) |
| #257 | `python3 scripts/query_corpus.py --route erdos_257` · reviewed return: `python3 scripts/query_corpus.py --route erdos257_half_story` | [`MersenneSubseriesRigidity.lean`](../ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean) | [paper note](papers/full-text/erdos-257-mersenne-support-subseries.md) · [TeX source](../paper/erdos-257-mersenne-support-subseries.tex) |
| #269 | `python3 scripts/query_corpus.py --route erdos_269`<br>Palomar family spine (run `python3 scripts/query_semantic.py family-relations <family_id>`): `conditional_carry_escape` → `weighted_phase_carry_observer` → `rank_two_kernel_no_go` → `height_fibre_and_shell` → `dyadic_block_alphabet` → `three_prime_lcm_cells` | [`RestrictedFloorSum.lean`](../ErdosProblems/Erdos269/RestrictedFloorSum.lean) · [`WeightedPhaseCarry.lean`](../ErdosProblems/Erdos269/WeightedPhaseCarry.lean) · [`ThreePrimeRunningLcm.lean`](../ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean) | [paper note](papers/full-text/erdos-269-three-prime-running-lcm.md) · [TeX source](../paper/erdos-269-three-prime-running-lcm.tex) |
| #1041 | `python3 scripts/query_corpus.py --route erdos_1041` | [`NewtonFlowRaySeparation.lean`](../ErdosProblems/Erdos1041/NewtonFlowRaySeparation.lean) | [dated frontier](../research_corpus/Erdos1041/FRONTIER.md) → [paper note](papers/full-text/erdos-1041-lemniscate-newton-flow.md) · [TeX source](../paper/erdos-1041-lemniscate-newton-flow.tex) |
| #1049 | `python3 scripts/query_corpus.py --route erdos_1049` | [`RationalBaseLambert.lean`](../ErdosProblems/Erdos1049/RationalBaseLambert.lean) | [paper note](papers/full-text/erdos-1049-rational-base-lambert.md) · [TeX source](../paper/erdos-1049-rational-base-lambert.tex) |

The exact open boundary each row stops at, as machine handles. A five-column
table put these sentences 354px past the rendered column, so they read here:

- **#68** — `weighted_collision_and_complementary_residue`; `cofinal_prime_power_amplification`; `cofinal_lower_endpoint_escape`; `cofinal_doubled_prime_branch_failure`; `cramer_residual_nonintegrality`
- **#243** — `unbounded_negative_excursions`; `derive_the_two_analytic_hypotheses`; `formalise_the_published_criteria`
- **#249** — Index: `strict_prime_tail_orbit_gap`; `hankel_denominator_fan_in`; `euler_sieve_limit_theorem`; `prime_ray_resultant_supply`; `stern_brocot_arithmetic_bridge`. Family: `totient_coprimality_probability`; `squared_lambert_gcd_moments`; `stern_brocot_cylinder_law`; `stern_brocot_run_fibonacci_stability`. Reviewed: `remaining_open.erdos_249_irrationality`; `remaining_open.unbounded_certificate_supply`
- **#251** — `prime_gap_cofinal_shift_escape`; `cofinal_adjacent_small_mismatch`; `actual_prime_gap_tail_formal_bridge`
- **#257** — Index: `arithmetic_rigidity_for_thin_supports`; `formalise_measure_and_stride_geometry`. Reviewed: `remaining_open.half_value_membership`; `remaining_open.twenty_one_permanent_affine_supercapacity`; `remaining_open.universal_257_all_infinite_supports`
- **#269** — `actual_local_window_residue_escape`; `actual_rational_carry_instantiation`; `nonstationary_analytic_theorem`; `unbounded_height_certificate`
- **#1041** — `repair_or_refute_saddle_block`; `compact_ray_cut_strip_decomposition`; `metric_gluing_below_two`; `two_stage_stable_perturbation`; `relative_global_newton_flow_theorem`
- **#1049** — `three_halves_growing_rank_endpoint_jet_kernel`

From a reviewed route, use the registered claim or paper-anchor query to
travel back to exact Lean declarations; use the open query for the registered
unresolved boundary rather than treating a checked special case as a
solution:

```sh
python3 scripts/query_corpus.py --claim <claim_id>
python3 scripts/query_corpus.py --paper-anchor <TeX_label_or_source_ref>
python3 scripts/query_corpus.py --open <remaining_open.id>
```

## Build entrypoint

- `Erdos249257.lean`
- `ErdosProblems.lean`
- Lake package: `erdos249257`
- Lean libraries / stable root imports: `Erdos249257`, `ErdosProblems`

`Erdos249257` is the reviewed #249/#257 corpus. `ErdosProblems` is the
problem-owned expansion surface; unregistered declarations there remain exact
Lean propositions rather than reviewed public mathematical claims.

## #257 / Erdős–Borwein families

- `Erdos249257.CertificateKernel`
- Relevant declarations include: `irrational_erdosSum_full_support`,
  `irrational_erdosBorwein_series`, `irrational_erdosSum_factorial_support`,
  `irrational_erdosSum_two_pow_support`, and
  `irrational_erdosSupportSeries_eventuallyPeriodic`.

## Periodic weighted Lambert series

- `Erdos249257.CertificateKernel`
- Nonnegative weights:
  `irrational_weightedErdosSeries_periodic`,
  `irrational_weightedErdosSeries_eventuallyPeriodic`, and
  `irrational_ratWeightSeries_eventuallyPeriodic`.
- Signed weights:
  `irrational_or_bpow_mul_eq_intCast_intWeightedErdosSeries_periodic` gives
  the irrational-or-base-terminating dichotomy, while
  `irrational_intWeightedErdosSeries_periodic_of_bpow_mul_ne_intCast`
  consumes an explicit nontermination hypothesis.
- `intWeightedCoeff_periodFourSignWeight_eq_zero_of_mod_four_eq_three` is the
  residue-selection obstruction explaining why the signed endpoint is not
  unconditional irrationality.

## #249 / totient denominator exclusions

- `Erdos249257.GapFareyBound`
- `Erdos249257.CertificateKernel`
- **Visible-coprime lattice mass** (`totient_visible_coprime_lattice_mass`) —
  [`tsum_pos_coprime_inv_mersenne_eq_one`](../Erdos249257/GcdMomentCalculus.lean#L349)
  proves that the positive coprime Mersenne weights on the visible lattice sum
  exactly to one. This is the rational normalization behind the fair-coin
  coprimality form of #249, not an irrationality result. Follow the
  [individual-paper explanation](papers/full-text/erdos-249-binary-totient-series.md#exact-identities-and-representations.)
  or the reviewed claim route
  `python3 scripts/query_corpus.py --claim stern_brocot_cylinder_law`; both
  expose the explanation and reverse source links. The exact boundary is
  unchanged: this identity does not settle #249.

- **All-base totient-kernel reduction, spanning, and conditional rank**
  (`all_base_totient_kernel_index_reduction`) —
  [`TotientKernelConditional.lean`](../Erdos249257/TotientKernelConditional.lean#L102)
  gives the unconditional canonical spanning theorem, while
  [`finrank_allBaseTotientKernelThroughLevelFamily_eq_of_linearIndependent`](../Erdos249257/TotientKernelConditional.lean#L215)
  gives rank `k^e + 1` only under the explicit linear-independence hypothesis.
  That independence, and Martin's external positive-density theorem, are not
  formalised here; this algebraic boundary does not prove irrationality of
  #249. Retrieve the full claim/source record with
  `python3 scripts/query_corpus.py --claim all_base_totient_kernel_index_reduction`,
  then return to the open problem with
  `python3 scripts/query_corpus.py --route erdos_249`.

- **Prime-ray cyclotomic support escape** (`prime_ray_resultant_supply`) —
  [`PrimeRayCyclotomicCurvature.lean`](../ErdosProblems/Erdos249/PrimeRayCyclotomicCurvature.lean#L95)
  turns bounded-degree order divisibility and eventual nontrivial clean layers
  into finite-support escape and cofinal unbounded prime divisors. Its bounded
  order is an existence of an exponent witness, not exact order. The actual
  totient layer/resultant bridge and the route from unbounded prime support to
  certificate or carry escape remain open; the Mersenne-only instantiation in
  `CyclotomicAnchoredKill.lean:33-105` does not close #249 or justify novelty.

- **Tail-orbit phase-density and natural-prime strict-gap reductions**
  (`strict_prime_tail_orbit_gap`) —
  [`TotientStrictPrimeEscape.lean`](../ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L25)
  makes the two producer interfaces explicit: an `11/100` nonpositive-phase
  density on arbitrarily late dyadic blocks implies an `89/100` first-harmonic
  block saving, while the natural-prime strict-gap predicate gives a pointwise
  `9/10` pivot escape through the wrapper
  `Erdos249257.ExternalVerification.irrational_totient_series_of_naturalPrimeTailOrbitStrictGap`.
  The same module records the exact phase update
  [`tailOrbitFirstExp_succ`](../ErdosProblems/Erdos249/TotientStrictPrimeEscape.lean#L167):
  after the integer carry disappears under exponentiation, the first phase
  evolves by squaring. This is orbit-mechanism evidence only; it supplies none
  of the density, cofinal prime strict-gap, or uniform-margin hypotheses.
  The density, cofinal prime strict-gap, and positive truncation-margin
  producers are unproved for the actual totient orbit. This is conditional
  certificate/irrationality reduction only: it does not close #249, duplicate
  the finite `first_harmonic_pivot_decomposition` or `actual_lcm_orbit_separation`
  families, or justify novelty, priority, significance, or external review.

## #249 / certificate reductions

- `Erdos249257.TotientTailPeriodKiller`
- `Erdos249257.CarrySurvivorExtinction`
- `Erdos249257.LcmDiagonalReduction`
- `Erdos249257.LcmConeFlatness`
- `Erdos249257.LcmConeNonflat`

Supporting ladder modules:

- `Erdos249257.MersenneLambertLadder`
- `Erdos249257.GeometricCoprimality`
- `Erdos249257.GcdMomentCalculus`

## #249 / diagonal pincer frontier

Read this band after the certificate reductions above.  It sharpens the same
open obligation; it does not prove the required unbounded supply.

- `Erdos249257.DiagonalPincerDecomposition` — exact full-target interval
  characterisation and the target-avoidance-to-irrationality reduction.
- `Erdos249257.SquaredMersenneDiagonalEnclosure` — Lambert-projected centre,
  exact signed square tail, and a sharp separation criterion.
- `Erdos249257.DiagonalFreshLossBridge` — exact fresh-loss projection and
  stronger adjacent-suffix supply interfaces.
- `Erdos249257.DiagonalPincerCertificates` and
  `Erdos249257.DiagonalPincerCertificatesT*`, followed by
  `ErdosProblems.Lift` and `ErdosProblems.Skip` — the finite diagonal segment
  supplies a checked working depth for every
  natural `t ≤ 82`; it supplies nothing at `t = 83`. This is finite source
  extraction, not a cofinal or asymptotic result.
- `Erdos249257.DiagonalPincerPrimeCertificates.*` — finite prime certificate
  shards used by that assembled segment; read the aggregators first.

Algebraic support for the same band:

- `MersenneShadowCyclotomicNoncollapse → MersenneShadowDenominatorGrowth`
- `RadicalMobiusShadow → RepunitMobiusNumerator → CyclicTensorMobiusShadow`
- `CyclotomicProjectionOfShadow → PrimePowerJumpDynamics`
- `RationalDenominatorSurvival`, `LambertDiagonalEnclosure`,
  and `FullTargetPrimeAdjunctionNoGo`

Exploratory exact interfaces with explicit conditional boundaries live in
`PrimitiveRationalGapSupply`, `PrimitiveSupportBridge`,
`ActualForeignResidueProjection`, `SternBrocotRunGeometry`, and
`SupportDilationDifferences`.

### Transport and curvature companion band

Read `CurvatureCarry → ExponentOnlyTransport → JointExponentTransport` for the
main proof spine, then `PrimeJumpMigration → PrimeJumpWindow` and
`ThreeTransportBoundary` for the new-prime and balanced finite consumers.
For the harmonic route, read
`FirstHarmonicGap → FirstHarmonicPivot → AdjacentPhaseSeparation`.
`FirstHarmonicGap` turns a constant-saving cosine bound into a direct
certificate. `FirstHarmonicPivot` decomposes the complex harmonic sum exactly
into centred supplier-fibre, fibre-mean, bad-supplier, and non-supplier terms;
the one-sided budgets `14X/25`, `X/100`, `X/100`, and `8X/25` give the required
`9X/10` saving. `AdjacentPhaseSeparation` gives a pairwise alternative. No
cofinal harmonic, prime-distribution, or decorrelation estimate is proved.
`TropicalCurvatureCarry` is a proved negative result showing that bounded
valuation–unit precision alone cannot exclude all centred completions.

- `CurvatureCarry` — exact curvature window, sharp radius, recurrence, and
  conditional unbounded-supply endpoints.
- `ExponentOnlyTransport` — squarefree support stability and the exact
  periodic affine slope/intercept state.
- `JointExponentTransport` — universal two-moment old-channel annihilation and
  the anchored `(3,5)` four-vertex consumer.
- `PrimeJumpMigration` / `PrimeJumpWindow` — migrated-channel correction,
  sharp direct radius, and the finite `(12,5,15)` certificate.
- `ThreeTransportBoundary` — balanced `(1,2,3,6)` consumer and the finite
  `(60,12)` certificate.
- `FirstHarmonicGap` — deterministic conversion of a blockwise harmonic gap
  into a direct certificate.
- `FirstHarmonicPivot` — exact four-term complex pivot decomposition and a
  conditional cofinal budget-to-irrationality socket.
- `TropicalCurvatureCarry` — fixed-precision local-signature no-go theorem.

The former one-sided transport companion is retired.  Its exact Lean results
remain available through the claim registry and source routes; no separate
active manuscript or rendered companion is part of this release.

### Paper-curation boundary

The paper treats `GcdMomentCalculus` as supporting mathematical exposition: its
squared Lambert transform, gcd moments, reduced-direction law, and cylinder
recursion explain the representation containing the #249 Möbius-square atom.
`FullTargetPrimeAdjunctionNoGo` is included as a proved negative result because
it closes a recurring prime-adjunction strategy without changing the open
claim. `SternBrocotRunGeometry` is registered as a source-level supporting
claim: its continuant/Fibonacci stability theorems are stated in the Lambert
complements, but no endpoint argument currently consumes them. It therefore
remains outside the paper's principal result spine; the cylinder law is owned
by `GcdMomentCalculus`, while `SternBrocotRunGeometry` owns the induced-run
stability package.

## Binary-carry trunk (post-wave carry layer)

Builds on `Erdos249257.CertificateKernel`; not part of the wave chronology.
Reading order:
`GenericTailOrbitRigidity → GreedyAchievementSet → CampbellShiftSynchronization → BooleanMobiusCarry → RationalSupportCarrySkeleton → DyadicPrefixCompression → SublogDivisorCoverage`.

- `Erdos249257.GenericTailOrbitRigidity`
- Relevant declarations include: `temperedBinaryOrbit_eq_scaledTail`, `binaryCoeffSeries_rational_iff_exists_temperedBinaryOrbit`, `balancedPulse_fanout_unbounded`, `balancedPulse_no_autonomous_decoder`

- `Erdos249257.GreedyAchievementSet`
- Relevant declarations include: `volume_mersenneAchievementSet`, `perfect_mersenneAchievementSet`, `isNowhereDense_mersenneAchievementSet`, `mem_mersenneAchievementSet_iff_greedy_survival`, `certifiedGreedyMersenneDeath_not_mem`, `three_fourths_not_mem_mersenneAchievementSet`, `rational_member_support_bit_iff`, `half_mem_mersenneAchievementSet_of_prefixForcingChain` (conditional interface only)

- `Erdos249257.CampbellShiftSynchronization`
- Relevant declarations include:
  `campbellQuarterExponent_periodFreeze_noSync`,
  `campbellPhaseFreeze_parameters_impossible`,
  `shiftWindowZero_iff_greedyMersenneSkippedSupport_infinite`, and
  `shiftWindowZero_iff_half_mem_mersenneAchievementSet`. These are a
  synchronization no-go and an exact endpoint re-expression, not an
  independent half-membership producer.

- `Erdos249257.BooleanMobiusCarry`
- Relevant declarations include: `erdosSupportSeries_rational_iff_exists_temperedCarry`, `support_fraction_iff_exists_temperedCarry`, `exists_normalized_support_fraction_iff_exists_booleanMobiusCarry`, `mobius_carryQuotient_recovers_support`, `support_half_iff_affineBinaryOrbit_tempered`

- `Erdos249257.RationalSupportCarrySkeleton`
- Relevant declarations include: `sum_doublingResidue_eq_mul_wrapCount`, `one_div_oddOrder_le_reciprocalMass_of_support_fraction`, `reciprocalMass_eq_residueMean_add_excessMean`, `dyadic_support_fraction_reciprocalMass_diverges_or_gt_one`, `exists_unbounded_shifted_odd_tail_nat_state_of_support_fraction`

- `Erdos249257.DyadicPrefixCompression`
- This is #257 support, not part of the #249 diagonal band. It gives exact
  finite-fragment dyadic compression inside a hypothetical dyadic-rational
  support value, reduced/raw block-safety coordinates, primitive-lattice and
  support-tail-gap equivalences, conditional half-membership consumers, and
  checked failures of naive induction.
  Start with `finiteFragment_dyadicPrefixCompression`,
  `halfGreedyThreeDepthTakeRunExcessBound_iff_skippedExcessBound`,
  `greedyHalf_badSkipCapViolation_iff_primitiveLattice`,
  `halfGreedyPrefixSupportTailGap_eq_excess_div_denominator`, and
  `unsafeSkipGcdOvershootSupply_iff_primitive`. No cofinal witness supply is
  proved.

- `Erdos249257.SublogDivisorCoverage`
- Relevant declarations include: `supportCoeffZeroWindow_length_le_eps_logb_add`

## Half-value finite-prefix and boundary analysis

This band studies the test value `1/2` in ordinary finite-prefix language.
A greedy prefix is the first `n` include/skip decisions. A seam is a pair of
finite words whose values bracket `1/2`. A cylinder is the set of infinite
extensions of one fixed prefix. A producer is an unproved hypothesis that
supplies the required seams or return configurations arbitrarily far out.

Read the band in four layers:

1. `GreedyAchievementSet → HalfCutLocator` defines the achievement set, greedy
   coding, and the finite cut around `1/2`.
2. `HalfCarryReachability → HalfCylinderFiniteShadow` translates finite
   prefixes into integer carry and finite-shadow coordinates.
3. `HalfCylinderIntegerGreedy → HalfCylinderConcreteSeamAdapter →
   HalfCylinderFullShellSeamBridge → HalfCylinderSkippedEndpointClassifier →
   HalfCylinderFloorErrorReset → HalfCylinderSeamLimit` develops the exact
   boundary arithmetic and limiting seam interface.
4. `HalfCylinderFatalGapRightTail → HalfCylinderHalfMembershipClassification →
   HalfCylinderLastProducerContradiction → HalfCylinderMiddleCarryLowerBound`
   gives the endpoint classification, eliminates the upper and `-3` middle
   cases, and isolates the remaining carry-tail inequality for `-2` and `-1`.

The floor-error and shell modules are supporting arithmetic layers, not
separate endpoint theorems. The last layer remains conditional: no producer
supplying the required configurations cofinally is proved.

## Claim registry

- `docs/claims.json` — the single owner of release identity, claim statuses, and declaration coordinates (file and line), cross-checked by `scripts/check_release.py`

## Generated finite certificates

- `Erdos249257.GeneratedCertificates`
- `Erdos249257.GeneratedCertificates.*`

The complete import graph and every declaration are generated in
`docs/claims.json::machine_readable_paper.module_graph` and
`docs/declaration_atlas.json`; use those surfaces when a grouped route above is
not specific enough. Current corpus counts live in the generated
`docs/ORIENTATION.md`, not in this authored route map.
