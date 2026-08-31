<!--
SPDX-FileCopyrightText: 2026 Will Cook
SPDX-License-Identifier: Apache-2.0
-->

# Prior art and attribution map

This is a reading map for the mathematical sources cited in the exposition. It
records relationship, not proof authority: only the pinned Lean source
establishes what this release proves. A citation never widens a release claim,
and a source listed as *context* is not an imported argument or a claim of
mathematical priority. Formalisation/software dependencies are recorded in
[CITATION.cff](../CITATION.cff); the Erdős Problems catalogue supplies
numbering and status context rather than mathematical priority.

The [exposition](../paper/erdos249-257-main-paper.tex) carries the
mathematics bibliography. [CITATION.cff](../CITATION.cff) is intentionally
selected release/software citation metadata: it supplies the recommended
citation for this version and selected foundational or software references,
not a duplicate bibliography. This map explains why the principal sources are
credited.

## Bounded comparison route

Start with
`python3 scripts/query_corpus.py --route trace_prior_art`, then select the
exact local claim with `python3 scripts/query_corpus.py --claim <claim_id>`.
Read its registry status, statement, assumptions, remaining-open links, and
Lean declarations before interpreting any row below. A status such as
`proved here` or `formalised here` is an evidence statement, not a novelty
statement.

For a theorem-level comparison, record the source statement, assumptions,
conclusion, specialisation map, proof mechanism, and residual difference
against that selected local claim. Failure to identify a matching source is
not evidence of novelty. Lean source checked by the pinned Lean kernel remains
proof authority; this bibliography and its search history are authored
attribution evidence only.

## Principal sources

Each entry gives the source, then its relationship to this release, then the
boundary of that relationship.

- P. Erdős and R. L. Graham, [*Old and New Problems and Results in Combinatorial Number Theory* (1980)](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf); P. Erdős, [*On the irrationality of certain series: problems and results* (1988)](https://doi.org/10.1017/CBO9780511897184.009)

  Original published formulations for the #249 and #257 problem setting.

  **Boundary.** They formulate open problems; they are not proofs of either universal statement.

- S. Chowla, [*On Series of the Lambert Type which assume Irrational Values for Rational Values of the Argument* (1947)](https://insa.nic.in/UI/Archivesection.aspx?JID=MA%3D%3D&JYrs=MTk0Nw%3D%3D)

  Historical conjectural predecessor: its rational-argument Lambert question contains the full-support specialisation \(x=1/b\).

  **Boundary.** Chowla's source is a conjecture in this relation, not the proof source; the theorem formalised here is credited to Erdős (1948).

- P. Erdős, [*On arithmetical properties of Lambert series* (1948)](https://users.renyi.hu/~p_erdos/1948-04.pdf)

  Full-support Erdős--Borwein irrationality formalised here.

  **Boundary.** The formalisation is a checked rendering, not a priority claim.

- P. Erdős, [*On the irrationality of certain series* (Math. Student 36, 1968)](https://users.renyi.hu/~p_erdos/1969-09.pdf)

  Pairwise-coprime support condition.

  **Boundary.** Only that classical family is attributed to this source; it does not settle universal #257.

- P. B. Borwein, [*On the irrationality of certain series* (1992)](https://doi.org/10.1017/S030500410007081X)

  Broader irrationality theorem containing the relevant Mersenne--Lambert specialisation.

  **Boundary.** Context for the full-support family, not a proof route for the new #249 reductions.

- H. Kaneko, Y. Suzuki, and Y. Tachiya, [*Refinements of Erdős's irrationality criterion for certain sparse infinite series* (2026)](https://arxiv.org/abs/2601.20743)

  Nearby current work proving irrationality for sparse series such as \(\sum d(n)^k/t^{\varphi(n)}\).

  **Boundary.** Here \(\varphi(n)\) occurs in the exponent. It does not treat the coefficient-weighted constant \(\sum\varphi(n)/2^n\), its denominator bound, or its tail-certificate equivalence.

- T. M. Apostol, [*Introduction to Analytic Number Theory* (1976)](https://doi.org/10.1007/978-1-4757-5579-4); M. Merca, [*The Lambert series factorization theorem* (2017)](https://doi.org/10.1007/s11139-016-9856-3); M. Merca and M. D. Schmidt, [*Generating Special Arithmetic Functions by Lambert Series Factorizations* (2019)](https://doi.org/10.55016/ojs/cdm.v14i1.62425)

  Apostol supplies the classical Dirichlet/Möbius background; Merca gives the modern factorisation theorem and Merca--Schmidt its synthesis/unification treatment.

  **Boundary.** The release uses classical transforms and claims a Lean-checked composition, not new Möbius inversion, Lambert identities, or the cited factorisation theorems.

- Y. V. Nesterenko, [*Modular functions and transcendence questions* (1996)](https://doi.org/10.1070/SM1996v187n09ABEH000158)

  Direct source for the cited-only transcendence of the divisor-sum ladder rung \(L(\mathrm{Id})=\sum_{m\geq1}\sigma(m)/2^m\).

  **Boundary.** This positions one ladder row only; no part of its modular-transcendence proof is formalised here.

- K. Postelmans and W. Van Assche, [*Irrationality of \(\zeta_q(1)\) and \(\zeta_q(2)\)* (2007)](https://doi.org/10.1016/j.jnt.2006.11.011)

  Primary source for the cited-only linear independence of \(1,\zeta_q(1),\zeta_q(2)\) when \(q^{-1}\) is an integer of absolute value greater than one. At \(q=1/2\), this implies the irrationality of the squared-ladder value \(L_2(\mathbf1)=\zeta_{1/2}(2)-\zeta_{1/2}(1)\).

  **Boundary.** The release formalises the identity placing \(L_2(\mathbf1)\) in this q-zeta family, not the Hermite--Padé proof. Linear independence of the constant-weight row gives no irrationality transfer to the Möbius row \(L_2(\mu)=S-1/2\), which remains open.

- S. Kakeya, [*On the Set of Partial Sums of an Infinite Series* (1914)](https://doi.org/10.11429/ptmps1907.7.14_250)

  Classical strict-tail criterion for subsum sets: domination of every remaining tail by its term gives the Cantor-set regime.

  **Boundary.** The release uses this as historical geometry, not as a claim that Kakeya supplied the local executable machinery.

- V. Kovač and T. Tao, [*On several irrationality problems for Ahmes series* (2025)](https://doi.org/10.1007/s10474-025-01528-0)

  Direct fixed-base antecedent: their Remark 4.1 verifies \(\sum_{\ell>n}(t^\ell-1)^{-1}<(t^n-1)^{-1}\) for every integer \(t\ge2\), and deduces distinct Lambert subsums and a Cantor set.

  **Boundary.** At \(t=2\) this supplies the known Mersenne geometry. The release now formalises compactness, perfection, total disconnectedness, nowhere density, and measure one as well as the two-scale gap, greedy interface, and finite death certificates. It makes no novelty claim for those refinements; only the stated strict-tail antecedent has been compared here, and none settles #257.

- J. Farey, [*On a Curious Property of Vulgar Fractions* (1816)](https://doi.org/10.1080/14786441608628487)

  Historical source for the Farey language. The standard neighbouring-fraction/mediant lemma is the method that directly produces the finite #249 denominator bound: for the committed interval it gives `b+d-1`, exactly the formal bound.

  **Boundary.** The mathematical method and denominator estimate are classical. The local contribution is a kernel-checked arithmetic instance and proof that `b+d` is the first failure for each selected window; the improvement over the classical Farey bound is zero.

- G. Martin, [*Simultaneous inequalities among values of the Euler phi-function* (arXiv:math/0603053, 2006)](https://arxiv.org/abs/math/0603053)

  **Subsuming source for affine-totient linear independence.** His Theorem 1 assumes only that the slopes \(a_i\) are positive integers and that \(a_ib_j\neq a_jb_i\), and proves that for every \(C>0\) the simultaneous ratio gaps \(\varphi(a_1n+b_1)/\varphi(a_2n+b_2)>C,\ldots\) hold on a set of positive lower density; with his symmetry remark this yields linear independence of \(n\mapsto\varphi(a_in+b_i)\) over \(\mathbb{R}\) at once. His Corollary 4 transfers Theorem 1 and Corollaries 2–3 to \(\sigma\).

  **Boundary.** The dyadic Lean independence result is an independently formalised corollary of Martin, by a finite CRT–Dirichlet–determinant argument, not an original theorem. The all-base paper theorem applies Martin directly; Lean checks its zero-residue and composite-base arithmetic layers but does not formalise Martin's positive-density theorem or the final all-base independence step. Martin needs neither odd slopes, nor primitivity, nor a residue bound, and concludes strictly more. A \(\sigma\) analogue would likewise not be new. Exact-title, DOI and venue searches did not locate a separate journal publication, so this is cited as a public preprint.

- F. Luca and Y. Tachiya, [*Irrationality of Lambert series associated with a periodic sequence* (2014)](https://doi.org/10.1142/S1793042113501121)

  Direct antecedent for the eventually-periodic coefficient family. Their rational-coefficient theorem contains the indicator-support case and the nonnegative rational weights formalised here.

  **Boundary.** Their theorem is broader, and its Chowla--Erdős/large-modulus-prime proof is separate. This release uses a periodic-divisor certificate route. For signed integer weights it proves only an irrational-or-base-terminating dichotomy; it does not exclude the terminating alternative in general or claim the full mixed-sign theorem.

- T. Tao and J. Teräväinen, [*Quantitative correlations and some problems on prime factors of consecutive integers* (arXiv v2, 2026)](https://arxiv.org/abs/2512.01739v2)

  Direct source for the cited-only irrationality of the prime-support series, through its \(\sum_n\omega(n)/2^n\) formulation and this release's separately formalised identity bridge.

  **Boundary.** It settles that one support family, not universal #257; its quantitative correlation proof is not formalised here.

- H. Wang and J. M. Grau Ribas, [*Positive dyadic density for rational weighted binary expansions* (arXiv, 2026)](https://arxiv.org/abs/2606.24972)

  Direct antecedent for the rationality-forced integral carry recurrence in the weighted-binary special case (c(n)=n d_n).

  **Boundary.** The public generic criterion is a formalisation/abstraction; its converse and rigidity make no priority claim. The source's positive-density theorem and Erdős #260 corollary are neither used nor formalised here.

- R. Crandall, [*The googol-th bit of the Erdős--Borwein constant* (2012)](https://doi.org/10.1515/integers-2012-0007); J. M. Campbell, [*On the binary digits of the Erdős--Borwein constant* (arXiv, 2026)](https://arxiv.org/abs/2605.24160)

  Adjacent work on binary digits of the full-support constant; Campbell resolves Crandall's question on infinitely many occurrences of the block \(11\).

  **Boundary.** Neither result is formalised or used by this release, and neither changes its irrationality or open-problem claims.

## Expansion-note principal sources (#68, #243, #251, #269, #1041, #1049)

The same contract as above applies: relationship, not proof authority, and no
row widens a release claim. Each source below is load-bearing for exactly the
stated use in its problem note, where the full statement-level comparison is
recorded.

Entries carry the same three parts as above — source, relationship, boundary —
grouped by the problem whose note they serve.

### #68

- Koepf–Schmersau, doi:10.1524/anly.2011.1094; D. Duverney (2001), https://www.ms.u-tokyo.ac.jp/journal/pdf/jms080206.pdf; Barreto–Kang–Kim–Kovač–Zhang (2026); Hančl–Tijdeman

  Four cited irrationality criteria, each checked in the note *not* to apply to `∑ 1/(n!−1)` at a named boundary.

  **Boundary.** Non-applicability results; no criterion is claimed to transfer.

- Garaev–Luca–Shparlinski (Trans. AMS 356), doi:10.1090/S0002-9947-04-03612-8; C. L. Stewart (Publ. Math. Debrecen 65)

  Growth and divisor inputs for the collision-core layer, derived and source-verified in the note.

  **Boundary.** Not kernel-checked; explicitly load-bearing for nothing beyond the stated uses.

### #243

- K. Koizumi, *Irrationality of the reciprocal sum of doubly exponential sequences* (Integers 26 (2026), A28; [arXiv:2504.05933](https://arxiv.org/abs/2504.05933))

  Supplies normalised vanishing for the canonical orbit, the sole hypothesis of the note's headline conditional theorems not proved in Lean; its Lemma 3 and Proposition 1(2) are conceded in-note as prior art for the note's absorption and descent lemmas.

  **Boundary.** The bridge is prose; only the integer state-system theorems are kernel-checked here, and no priority or independence is adjudicated.

### #251

- V. Kovač, counterexample to Erdős's variable-denominator expectation (2026, Theorem 1)

  Refutes the 1988 expectation that `∑ p_n/(g_1⋯g_n)` is irrational whenever `g_n ≥ 2`, `g_n = o(p_n)`; the note records that the live catalogue still repeats the refuted expectation.

  **Boundary.** Concerns the variable-denominator variant, not the fixed dyadic series studied here.

- Y. Zhang (2014); J. Maynard (2015), doi:10.4007/annals.2015.181.1.7; Ford–Green–Konyagin–Maynard–Tao (2018), doi:10.1090/jams/876

  Bounded-gap and large-gap prime results, cited and each shown insufficient for the required joint dyadic distribution of a logarithmic block of gap differences.

  **Boundary.** Context; none is used as a proof input.

### #269

- Y. Bugeaud and M. Laurent, Hecke–Mahler transcendence (Theorem 1.1 as cited in the #269 note), doi:10.4064/aa220323-18-1

  External transcendence engine for the note's two-prime theorems: both the de-duplicated and repeated running-lcm reciprocal sums are transcendental for every pair of distinct primes, by a paper argument.

  **Boundary.** The two-prime theorems are deliberately not Lean declarations; nothing follows for three or more primes.

- S. Fan, [comment on Erdős Problem #269](https://www.erdosproblems.com/forum/thread/269), 26 June 2026

  Earlier public disclosure of the same two-channel factorisation, Hecke–Mahler reduction, and transcendence conclusion; later comments extend it to coprime pairs. This note first appeared on 22 July 2026, 26 days later.

  **Boundary.** No priority claim for the two-prime result. The paper argument was developed independently but is not first and is not a Lean theorem; a broader search would be needed to identify the first public proof.

- P. Erdős, letter of 1 January 1973 (printed p. 335 as cited in the #269 note)

  Asserted the de-duplicated two-prime irrationality without a printed proof; the note's route is an independent modern argument, not a recovery of the unprinted one.

  **Boundary.** Historical formulation and priority context only.

### #1041

- P. Erdős, F. Herzog, and G. Piranian, *Metric properties of polynomials* (J. Analyse Math. 6 (1958), Problem 5, p. 139), doi:10.1007/BF02790232

  Original problem source, including the known input that one lemniscate component contains at least two zeros.

  **Boundary.** Formulation, not proof; the note's saddle-block diagnosis of a recent manuscript is prose, not Lean.

### #1049

- P. Bundschuh and K. Väänänen, *Compositio Math.* 91 (1994), Theorem 2, https://numdam.org/item/CM_1994__91_2_175_0.pdf

  External irrationality criterion at base `7/2`; the release checks only its elementary Archimedean height inequality.

  **Boundary.** The analytic argument remains external, and nothing follows at `3/2`.

- T. Amdeberhan and D. Zeilberger, [*$q$-Apéry irrationality proofs by $q$-WZ pairs* (1998)](https://doi.org/10.1006/aama.1997.0565); W. Van Assche, [*Little $q$-Legendre polynomials and irrationality of certain Lambert series* (2001)](https://doi.org/10.1023/A:1012930828917); P. B. Borwein, [*On the irrationality of certain series* (1992)](https://doi.org/10.1017/S030500410007081X)

  Amdeberhan--Zeilberger and Van Assche target the same Lambert value with the same little-$q$-Legendre kernel on different moving diagonals; Van Assche cites Borwein's Lemma 2 for the neighbouring evaluation used in the comparison.

  **Boundary.** The exact nonzero residual in the paper disproves transfer of the Amdeberhan--Zeilberger scalar recurrence to Van Assche's diagonal. No endpoint, lattice, valuation, or denominator gain is transferred merely from the shared kernel. Borwein 1992, not the adjacent 1991 paper, is the cited evaluation source.

## Provisional theorem-specific comparisons

These local rows come after the direct antecedents on purpose. They record
dated searches and residual comparisons; failure to identify a closer theorem
is not a novelty result.

Each entry names the local package, the comparison this release recorded for
it, and the boundary of that comparison.

- **The complete tail-certificate normal form.** The comparison search covered the original problem sources, Erdős's and Borwein's Lambert-series theorems, periodic-coefficient results, and current arithmetic-function series literature. No theorem with the same pointwise certificate equivalence was identified as of 16 July 2026. The finite denominator number is deliberately excluded because it is obtained directly by the classical Farey/mediant method.

  **Boundary.** This is a dated search result, not a priority or novelty theorem. A closer antecedent should replace it if one is found.

- **Finite-difference and affine-moment transport.** General algebraic techniques are applied here to exact Möbius residue kernels and totient-tail windows. The primary-source search found no cited theorem matching the combined curvature, prime-jump, anchored `(3,5)`, or fixed-precision no-go statements.

  **Boundary.** Absence of an identified match is not a novelty claim. The release claims only the pinned Lean theorems and keeps the open supply hypotheses explicit.

- **First-harmonic and large-prime pivot reductions.** The additive-character step and \(\varphi(mp)=\varphi(m)(p-1)\) use standard ingredients; Apostol supplies the arithmetic background. The local statement is the four-term supplier-fibre decomposition, its one-sided \(14/25,1/100,1/100,8/25\) budget, and its composition with certificate completeness.

  **Boundary.** No matching combined theorem is recorded, but no prime-distribution or residual-decorrelation estimate populating the four budgets is proved.

- **Reduced-direction, Stern--Brocot cylinder, and continuant-run package.** The direct sources above supply the classical divisor/Möbius, mediant, and adjacent squared-Lambert settings. The release proves an exact Mersenne-weight probability normalization, a telescoping cylinder law with uniform geometric error, and sharp Fibonacci/continuant run estimates.

  **Boundary.** No priority claim is made. The run estimates have no endpoint consumer, and matching Fibonacci and denominator scales does not prove denominator survival or irrationality of \(S\).

- **Exact \(1/2\)-membership, fatal-gap, and last-producer package.** The strict-tail source above gives the global subsum geometry. The maintained search found no source stating the exact equivalence between \(1/2\)-membership, infinitely many greedy skips, cofinal false seam terminals, and absence of a last skip, nor the surviving middle-producer future-tail condition.

  **Boundary.** This is provisional positioning, not a novelty assertion. Positive membership would refute universal #257; nonmembership would decide only this test value.

## Audit rule for new sources

Add a public citation only when the source can be tied to a named statement,
method, or historical formulation in the release. Before describing a source as
an antecedent of a local theorem family, record the exact statement comparison:
assumptions, conclusion, specialisation map, proof mechanism, and the remaining
delta. Otherwise, retain it as private research context rather than turning a
bibliographic lead into a public priority claim.
