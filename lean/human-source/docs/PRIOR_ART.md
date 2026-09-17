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

Each current [problem paper and research record](../paper/README.md) carries
its own bibliography and credits sources at the point of use. The
[joint #249/#257 exposition](../paper/archive/erdos249-257-main-paper.tex) is
archival. [CITATION.cff](../CITATION.cff) supplies the software release citation
and selected mathematical and software references; it is not a duplicate of
all the paper bibliographies. Its linked source records explain the local use
and limits of the selected references. When citing work added after that
release, also record the commit used. This map explains why the principal
sources are credited.

## Browse all source credits

The [source attribution index](research-commons/SOURCE_ATTRIBUTIONS.md) connects
named literature, public Erdős Problems contributions, and software sources to
exact paper and Lean locations. It includes anonymous credit for implemented
private advice until the correspondent confirms public naming. The
[machine-readable view](research-commons/source-attribution-index.json) records
citation coverage, source locators, content digests, and unresolved matches;
the [authored registry](research-commons/source-attributions.json) owns the
credit decisions. These records complement the principal-source comparisons
below and the separate accepted-contribution receipts in Research Commons.

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

## Erdős #249: attribution update, 16 September 2026

The finite-level result is an explicit basis, rank \(k^e+1\) for \(k\ge2,e\ge1\), and an integral basis of all relations among the totient sections. Coons’s non-regularity theorem and Martin’s affine-independence theorem are antecedents, not new claims of this release. For composite bases the retained condition is \(k\nmid r\).

Yazdani’s Theorem 2 and proof (2001, pp. 652–653) use CRT–Dirichlet separation and explicitly credit Shallit; this is the method antecedent of the evaluation-matrix proof. Yazdani’s Corollary 4 (p. 654) already gives non-automaticity of totient residues modulo every m≥3 in every base. Allouche–Shallit–Yassawi’s survey (published 2022; arXiv v1 2021, Theorem 3, Example 4 and Remark 7) explains that result. The fixed-base-2 bounded-residue irrationality theorem requires a separate carrying argument; Wong’s earlier base-equals-modulus theorem remains credited.

Bell–Smertnig (2026 preprint, Theorem 1.3) proves that a characteristic-zero Mahler series with multiplicative coefficients is regular, and explicitly excludes the totient series from every Mahler base. Bell–Bruin–Coons (2012, Theorems 1.5–1.6) supplies the earlier algebraic and D-finite classification context. These are generating-function statements, not proofs about the value at 1/2. Adamczewski–Drmota–Müllner (2022; arXiv v2 2021, Theorem 1.4 and Remark 1.5) provides the automatic-prime density context, with local conditions rather than unconditional positive density for every state.

Primary sources: [Yazdani](https://www.numdam.org/item/JTNB_2001__13_2_651_0/); [Allouche–Shallit–Yassawi](https://arxiv.org/abs/2104.13072v1); [Bell–Smertnig](https://arxiv.org/abs/2603.23456v1); [Bell–Bruin–Coons](https://arxiv.org/abs/1003.2221v2); [Adamczewski–Drmota–Müllner](https://arxiv.org/abs/2009.14773v2); [Martin](https://arxiv.org/abs/math/0603053v1). No priority claim for the local normal form is certified by this comparison.

## Principal sources

Each entry gives the source, then its relationship to this release, then the
boundary of that relationship.

- P. Erdős and R. L. Graham, [*Old and New Problems and Results in Combinatorial Number Theory* (1980)](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf) ([read source closure](primary-sources/reciprocal-tail/erdos-graham-1980-source-closure.md)); P. Erdős, [*On the irrationality of certain series: problems and results* (1988)](https://doi.org/10.1017/CBO9780511897184.009) ([Renyi scan](https://users.renyi.hu/~p_erdos/1988-22.pdf); [read source closure](primary-sources/reciprocal-tail/erdos-1988-source-closure.md))

  The 1980 monograph records the full-support divisor Lambert value \(\sum_{n\ge1}d(n)/2^n\) as irrational (printed p. 61), states that the analogous binary totient series could not then be proved irrational (p. 61), and identifies the full-support Mersenne identity \(\sum_{n\ge1}(2^n-1)^{-1}=\sum_{n\ge1}d(n)/2^n\) (p. 62). It also records the squarefree reciprocal question as open (p. 63). Erdős's 1988 article, printed p. 105, explicitly asks whether every increasing support gives an irrational \(\sum_k(2^{n_k}-1)^{-1}\); its density/LCM irrationality theorem is a separate result on pp. 106--108.

  **Boundary.** The 1980 full-support identity and the 1988 p. 105 subseries statement do not prove universal #257; the separate LCM theorem does not automatically apply to Mersenne denominators. The 1980 source explicitly leaves the binary totient irrationality question unresolved, so neither source proves #249, the release's Lean, Comparator, Palomar, geometry, finite-certificate, or totient-kernel claims.

- S. Chowla, [*On Series of the Lambert Type which assume Irrational Values for Rational Values of the Argument* (1947)](https://insa.nic.in/UI/Archivesection.aspx?JID=MA%3D%3D&JYrs=MTk0Nw%3D%3D) ([read source closure](primary-sources/reciprocal-tail/chowla-1947-source-closure.md))

  Historical conjectural predecessor: its rational-argument Lambert question contains the full-support specialisation \(x=1/b\).

  **Boundary.** Chowla's source is a conjecture in this relation, not the proof source; the theorem formalised here is credited to Erdős (1948).

- P. Erdős, [*On arithmetical properties of Lambert series* (1948)](https://users.renyi.hu/~p_erdos/1948-04.pdf) ([read source closure](primary-sources/totient-kernel/erdos-1948-lambert-source-closure.md))

  **Full-support divisor row.** Printed p. 63 states irrationality of `f(1/t) = Σ_{r≥1}d(r)/t^r` for every integer `|t|>1`, the Erdős--Borwein divisor-weighted Lambert theorem used for the full-support row.

  **Boundary.** Printed p. 66 explicitly says the analogous Euler-totient series `Σφ(n)/t^n` “seem[s] to present difficulties.” This source therefore does not support irrationality of the #249 totient series, any totient-kernel rank/basis, or the release’s Lean/Comparator claims; no novelty or priority claim is made.

- P. Erdős, [*On the irrationality of certain series* (Math. Student 36, 1968)](https://users.renyi.hu/~p_erdos/1969-09.pdf) ([read source closure](primary-sources/reciprocal-tail/erdos-1968-source-closure.md))

  **Pairwise-coprime support theorem.** Printed p. 222 states that if `n_1 < n_2 < ...` are pairwise coprime and `Σ 1/n_i < ∞`, then `Σ_i 1/(t^(n_i)-1)` is irrational for every integer `t ≥ 2`; the proof occupies printed pp. 223–225.

  **Boundary.** Printed p. 222 says the pairwise-coprimality condition can be removed only by more complicated arguments and gives no details, and that `Σ 1/n_i < ∞` could be replaced by an unstated weaker but more complicated condition; printed p. 226 suggests `Σ_{n_i<x} 1/n_i = o(log log x)` via Brun's method for pairwise coprime supports and says the all-primes case is not handled. The source therefore does not support the coprimality-free extension, universal #257, the release's Lean/Comparator claims, or any novelty or priority claim.

- D. Duverney and Y. Tachiya, [*Refinement of the Chowla–Erdős method and linear independence of certain Lambert series* (2019)](https://doi.org/10.1515/forum-2018-0299) ([author preprint](https://danielduverney.fr/documents/theorie-des-nombres/DuverneyTachiya190522.pdf); [read source closure](primary-sources/reciprocal-tail/duverney-tachiya-2019-source-closure.md))

  **Squarefree-support antecedent.** Corollary 1.2 (PDF p. 4; proof pp. 10–11), specialised to `E` equal to the primes, `s=2`, `ell=1`, and `q=2`, proves linear independence of `1` and the squarefree Lambert values at bases `2^j`; Example 1.1 displays the family using `|mu(n)|`.

  **Averaging antecedent.** The proof of Theorem 1.1 (Section 2, (2.3)–(2.9), PDF pp. 5–6) selects its index by averaging a local coefficient mass over an arithmetic progression and taking a term attaining the minimum. The #257 note cites this after its weighted-support theorem as the antecedent of the selection step in its displacement averaging.

  **Boundary.** The condition `|q| L <= s`, a product with `L = lcm(1,...,ell)`, is essential to this specialisation, so the result does not give squarefree irrationality at every integer base and does not settle universal #257. With `s = infinity` it covers the perfect `i`th-power supports at every integer base. It also does not prove the release's Lean, Comparator, Palomar, geometry, or totient-kernel claims; no novelty or priority claim is made.

- P. B. Borwein, [*On the irrationality of ∑ 1/(q^n+r)* (1991)](https://doi.org/10.1016/S0022-314X(05)80041-1) ([publisher record](https://www.sciencedirect.com/science/article/pii/S0022314X05800411); [read source closure](primary-sources/reciprocal-tail/borwein-1991-qn-r-source-closure.md))

  **Fixed-base rational-offset antecedent.** Theorem 4 (printed pp. 257--258) proves that ∑ 1/(q^n+r) is irrational and not a Liouville number when q is an integer greater than one and r is a nonzero rational avoiding the denominator zeros r = -q^n for n ≥ 1. The paper’s Padé/Stieltjes construction is the direct source for this full-support family.

  **Boundary.** The result is for every positive index with an integer base; it does not settle arbitrary infinite supports, the release's rational noninteger-base claim at `3/2`, universal #257, or the release's Lean results. Its recurrence and Padé estimates are not the Amdeberhan--Zeilberger q-WZ operator, and no novelty or priority claim is made.

- P. B. Borwein, [*On the irrationality of certain series* (1992)](https://doi.org/10.1017/S030500410007081X) ([author PDF](https://www.cecm.sfu.ca/~pborwein/PAPERS/P59.pdf); [read source closure](primary-sources/reciprocal-tail/borwein-1992-source-closure.md))

  **Full-support antecedent.** Theorems 1 and 2 (printed pp. 142 and 145; proof pp. 142--146) prove irrationality, and non-Liouville behavior, for the full-support series \(\sum_{n\ge1}(q^n+c)^{-1}\) and its alternating variant under their stated integer/rational hypotheses. Theorem 1 with \(q=2\), \(c=-1\) contains the full-support Mersenne--Lambert specialization.

  **Boundary.** The paper sums over every positive index, not an arbitrary infinite support, so it does not settle universal #257, prime-support or squarefree subseries, or the release's #249 reductions. Its contour-integral proof is not formalised here; no novelty or priority claim is made.

- H. Kaneko, Y. Suzuki, and Y. Tachiya, [*Refinements of Erdős's irrationality criterion for certain sparse infinite series* (2026)](https://arxiv.org/abs/2601.20743) ([read source closure](primary-sources/reciprocal-tail/kaneko-suzuki-tachiya-2026-source-closure.md))

  Nearby current work proving irrationality for sparse series such as \(\sum d(n)^k/t^{\varphi(n)}\).

  **Averaged-tail antecedent for #257.** The quantity \(R_c(q,x,z)\) of (1.7) (PDF p. 3) and Lemmas 1–2 (PDF pp. 6–8) derive irrationality from scaled tails that are small on average. The #257 note cites them beside its weighted-support theorem. There the divisor-incidence coefficients are positive on every multiple of \(\min A\), so the scaled tail is at least the series value and the note averages the displacement instead.

  **Boundary.** Here \(\varphi(n)\) occurs in the exponent. It does not treat the coefficient-weighted constant \(\sum\varphi(n)/2^n\), its denominator bound, or its tail-certificate equivalence. The counting hypotheses of Theorems 1 and 3 fail for divisor-incidence coefficients, so these criteria do not apply to Mersenne–Lambert subseries.

- T. M. Apostol, [*Introduction to Analytic Number Theory* (1976)](https://doi.org/10.1007/978-1-4757-5579-4); M. Merca, [*The Lambert series factorization theorem* (2017)](https://doi.org/10.1007/s11139-016-9856-3); M. Merca and M. D. Schmidt, [*Generating Special Arithmetic Functions by Lambert Series Factorizations* (2019)](https://doi.org/10.55016/ojs/cdm.v14i1.62425) ([official journal PDF](https://cdm.ucalgary.ca/article/download/62425/53773); [read source closure](primary-sources/totient-kernel/merca-schmidt-2017-lambert-factorizations-source-closure.md))

  Apostol supplies the classical Dirichlet/Möbius background; Merca gives the modern factorisation theorem and Merca--Schmidt its synthesis/unification treatment. Merca--Schmidt's equation (2) records the totient Lambert identity used as transform background, while Theorem 3.2 and Corollary 3.3 give their partition/inverse-matrix mechanism. Apostol/Merca 2017 remain cited background without a source closure in this pass.

  **Boundary.** The release uses classical transforms and claims a Lean-checked composition, not new Möbius inversion, Lambert identities, or the cited factorisation theorems.

- Y. V. Nesterenko, [*Modular functions and transcendence questions* (1996)](https://doi.org/10.1070/SM1996v187n09ABEH000158) ([read source closure](primary-sources/totient-kernel/nesterenko-1996-source-closure.md))

  Direct source for the cited-only transcendence of the divisor-sum ladder rung \(L(\mathrm{Id})=\sum_{m\geq1}\sigma(m)/2^m\).

  **Boundary.** This positions one ladder row only; no part of its modular-transcendence proof is formalised here.

- K. Postelmans and W. Van Assche, [*Irrationality of \(\zeta_q(1)\) and \(\zeta_q(2)\)* (2007)](https://doi.org/10.1016/j.jnt.2006.11.011) ([read source closure](primary-sources/reciprocal-tail/postelmans-van-assche-2007-source-closure.md))

  Primary source for the cited-only linear independence of \(1,\zeta_q(1),\zeta_q(2)\) when \(q^{-1}\) is an integer of absolute value greater than one. At \(q=1/2\), this implies the irrationality of the squared-ladder value \(L_2(\mathbf1)=\zeta_{1/2}(2)-\zeta_{1/2}(1)\).

  **Boundary.** The release formalises the identity placing \(L_2(\mathbf1)\) in this q-zeta family, not the Hermite--Padé proof. Linear independence of the constant-weight row gives no irrationality transfer to the Möbius row \(L_2(\mu)=S-1/2\), which remains open.

- S. Kakeya, [*On the Set of Partial Sums of an Infinite Series* (1914)](https://doi.org/10.11429/ptmps1907.7.14_250) ([read source closure](primary-sources/reciprocal-tail/kakeya-1914-source-closure.md))

  Classical strict-tail criterion for subsum sets: domination of every remaining tail by its term gives the Cantor-set regime.

  **Boundary.** The release uses this as historical geometry, not as a claim that Kakeya supplied the local executable machinery.

- V. Kovač and T. Tao, [*On several irrationality problems for Ahmes series* (2025)](https://doi.org/10.1007/s10474-025-01528-0) ([read source closure](primary-sources/reciprocal-tail/kovac-tao-2025-source-closure.md))

  **Fixed-base strict-tail antecedent.** Their Remark 4.1 (PDF p. 13) verifies \(\sum_{\ell>n}(t^\ell-1)^{-1}<(t^n-1)^{-1}\) for every integer \(t\ge2\), and deduces distinct Lambert subsums and a Cantor set. Their Theorem 2.3 (PDF p. 5; proof pp. 13–14) separately constructs rational *merged* sums from several bases under a mass hypothesis.

  **Boundary.** At \(t=2\) the strict-tail remark supplies the known Mersenne geometry, but it does not assert a measure formula. The multi-base theorem allows repeated terms and is not a fixed-base counterexample. The release now formalises compactness, perfection, total disconnectedness, nowhere density, and measure one as well as the two-scale gap, greedy interface, and finite death certificates. It makes no novelty claim for those refinements, and Kovač–Tao explicitly leave the universal fixed-base subseries question open; none of these results settles #257.

- M. Coons, [*(Non)Automaticity of number theoretic functions* (Journal de Théorie des Nombres de Bordeaux 22 (2010), no. 2, 339--352)](https://jtnb.centre-mersenne.org/articles/10.5802/jtnb.718/) ([official PDF](https://jtnb.centre-mersenne.org/item/10.5802/jtnb.718.pdf); [read source closure](primary-sources/totient-kernel/coons-2010-source-closure.md))

  **Global totient-kernel boundary.** Coons's Theorem 3.2, stated on printed p. 348 and proved on p. 349, shows that Euler's totient function is not \(k\)-regular for any \(k\ge2\), using the Dirichlet-series identity \(\sum_{n\ge1}\varphi(n)n^{-s}=\zeta(s-1)/\zeta(s)\) and the pole-counting criterion of Corollary 3.1. This is the prior-art source for the release's global non-finite-generation context; it does not state the finite-level rank, explicit basis, or relation normal form proved or discussed locally.

  **Boundary.** For integer-valued sequences, finite generation of the \(\mathbb Z\)-module generated by the kernel is equivalent to finite dimension of its rational span: if the span has dimension \(d\), some \(d\) evaluations embed it in \(\mathbb Q^d\) and the module in \(\mathbb Z^d\). The #249 short note states this in §1, so the infinite-dimensionality of the totient-kernel span is Coons's theorem in another form, and the exact ranks recover it. Coons does not prove the release's Lean declarations, dyadic rank \(2^e+1\), CRT--Dirichlet--determinant construction, or Erdős Problem #249. No novelty or priority claim is made for either the cited theorem or the local finite-level results.

- M. Coons, [*Regular sequences and the joint spectral radius* (International Journal of Foundations of Computer Science 28 (2017), no. 2, 135--140)](https://doi.org/10.1142/S0129054117500095) ([arXiv:1511.07535](https://arxiv.org/abs/1511.07535); [read source closure](primary-sources/totient-kernel/coons-2017-joint-spectral-radius-source-closure.md))

  **Basis versus spanning family for regular sequences.** For a \(k\)-regular sequence, Theorem 1 identifies the growth exponent with the base-\(k\) logarithm of the joint spectral radius of matrices associated to a basis of the kernel span; Proposition 4 gives the upper bound for any spanning set, Corollary 7 compares the two, and the example after it shows that a redundant spanning set can overestimate. Appendix A shows that the evaluation vectors of a basis of sequences span the coefficient space. The #249 short note cites these results for the basis-versus-spanning-family distinction and for the evaluation argument in the equivalence above.

  **Boundary.** The source concerns regular sequences and does not mention Euler's totient, which is not regular, so its growth theorem is not applied to the totient. It does not state the release's finite-level basis, ranks, section-map description, relation module, or Lean declarations. Statement numbers follow arXiv:1511.07535v1. No novelty or priority claim is made.

- J. Farey, [*On a Curious Property of Vulgar Fractions* (1816)](https://doi.org/10.1080/14786441608628487)

  Historical source for the Farey language. The standard neighbouring-fraction/mediant lemma is the method that directly produces the finite #249 denominator bound: for the committed interval it gives `b+d-1`, exactly the formal bound.

  **Boundary.** The mathematical method and denominator estimate are classical. The local contribution is a kernel-checked arithmetic instance and proof that `b+d` is the first failure for each selected window; the improvement over the classical Farey bound is zero.

- G. Martin, [*Simultaneous inequalities among values of the Euler phi-function* (arXiv:math/0603053, 2006)](https://arxiv.org/abs/math/0603053) ([read source closure](primary-sources/totient-kernel/martin-2006-source-closure.md))

  **Subsuming source for affine-totient ratio comparisons.** His Theorem 1 assumes only that the slopes \(a_i\) are positive integers and that \(a_ib_j\neq a_jb_i\), and proves that for every \(C>0\) the simultaneous ratio gaps \(\varphi(a_1n+b_1)/\varphi(a_2n+b_2)>C,\ldots\) hold on a set of positive lower density; the symmetry discussion supplies strict ordering patterns. In the local all-base argument this is the external comparison input behind the affine-totient independence statement; the finite dyadic Lean theorem remains separately formalised, not a theorem directly stated by Martin. His Corollary 4 transfers Theorem 1 and Corollaries 2–3 to \(\sigma\).

  **Boundary.** The release's dyadic Lean independence result is separately formalised from this broader comparison input by a finite CRT–Dirichlet–determinant argument; Martin does not present the release's Lean statement or proof. The all-base paper theorem applies Martin directly; Lean checks its zero-residue and composite-base arithmetic layers but does not formalise Martin's positive-density theorem or the final all-base independence step. Martin needs neither odd slopes, nor primitivity, nor a residue bound, and concludes strictly more. A \(\sigma\) analogue would likewise not be new. Exact-title, DOI and venue searches did not locate a separate journal publication, so this is cited as a public preprint.

- F. Luca and Y. Tachiya, [*Irrationality of Lambert series associated with a periodic sequence* (2014)](https://doi.org/10.1142/S1793042113501121) ([read source closure](primary-sources/reciprocal-tail/luca-tachiya-2014-source-closure.md))

  Direct antecedent for the eventually-periodic coefficient family. Their rational-coefficient theorem contains the indicator-support case and the nonnegative rational weights formalised here.

  **Boundary.** Their theorem is broader, and its Chowla--Erdős/large-modulus-prime proof is separate. This release uses a periodic-divisor certificate route. For signed integer weights it proves only an irrational-or-base-terminating dichotomy; it does not exclude the terminating alternative in general or claim the full mixed-sign theorem.

- T. Tao and J. Teräväinen, [*Quantitative correlations and some problems on prime factors of consecutive integers* (arXiv v2, 2026)](https://arxiv.org/abs/2512.01739v2) ([read source closure](primary-sources/reciprocal-tail/tao-teravainen-2026-source-closure.md))

  Direct source for the cited-only irrationality of the prime-support series: Theorem 1.3, equation (1.7), on PDF p. 4, with proof on pp. 44--56. It gives the \(\sum_n\omega(n)/2^n = \sum_p(2^p-1)^{-1}\) formulation and this release's separately formalised identity bridge.

  **Boundary.** It settles the prime-support family at base 2, not universal #257. The source only says that other integer bases and the prime-power variant can be treated by modifications and leaves those details to the reader; its quantitative correlation proof is not formalised here.

- H. Wang, [*Sparse Polynomial-Weighted Expansions* (arXiv:2606.24972v4, 2026)](https://arxiv.org/abs/2606.24972v4) ([read source closure](primary-sources/dyadic-carry/wang-2026-source-closure.md))

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

- J. Louwsma and J. Martino, *Rational numbers with odd greedy expansion of fixed length*, [arXiv:2309.07280v1](https://arxiv.org/abs/2309.07280v1)

  Lemma 4.1, p. 10, is the reciprocal-sum valuation formula. The notes' maximal prime-power survival test is its top valuation layer, written out for the denominators `n!−1`; the 139 and 2593 cancellations are the notes' own exact computations.

  **Boundary.** The lemma concerns finite sums of reciprocals and gives no statement about the infinite series.

- J. Hančl and R. Tijdeman, *On the irrationality of factorial series*, Acta Arith. 118 (2005), [doi:10.4064/aa118-4-5](https://doi.org/10.4064/aa118-4-5); W. Koepf and D. Schmersau, *Irrationality of certain infinite series II*, Analysis 31 (2011), [doi:10.1524/anly.2011.1094](https://doi.org/10.1524/anly.2011.1094)

  Hančl–Tijdeman Lemma 2.1 and the following remark (p. 385) give the factorial-tail integrality argument behind the finite-denominator implication. Koepf–Schmersau Example 3.2 (p. 121) states the irrationality direction of the factorial-digit criterion, whose analogue for the companion `C = S − e + 2` the notes prove. The long record compares the Hančl–Tijdeman polynomial-coefficient classification (Theorem 3.1) and the Oppenheim criterion they reproduce (Lemma 2.2), naming the unmet hypothesis of each.

  **Boundary.** The carry characterisation is proved directly in the notes; no source theorem supplies the needed cofinal event.

- F. Luca and I. E. Shparlinski, Bull. London Math. Soc. 37 (2005), [doi:10.1112/S0024609305004923](https://doi.org/10.1112/S0024609305004923); L. Lai, *On the largest prime divisor of n!+1*, Bull. Aust. Math. Soc. 113 (2026), [doi:10.1017/S0004972725100543](https://doi.org/10.1017/S0004972725100543)

  The factorial-gap gcd bound is the case `P = −1` of the subtraction that Luca and Shparlinski use in the proof of their Lemma 5 and Lai uses at display (2.5); Lai's Lemma 2.1 supplies the non-vanishing cutoff for polynomial shifts.

  **Boundary.** The terminal-block optimisation and the resulting lcm growth theorem are the notes' own argument.

- P. Erdős, *Some problems and results on the irrationality of the sum of infinite series* (1975), Theorem 1; D. Duverney (2001), [journal PDF](https://www.ms.u-tokyo.ac.jp/journal/pdf/jms080206.pdf); Barreto–Kang–Kim–Kovač–Zhang, [arXiv:2601.21442v3](https://arxiv.org/abs/2601.21442v3)

  Rapid-growth and fast-series irrationality criteria, each checked in the long record against `n!−1` with the unmet hypothesis named.

  **Boundary.** Non-applicability results; no criterion is claimed to transfer.

- M. Z. Garaev, F. Luca and I. E. Shparlinski (Trans. AMS 356), doi:10.1090/S0002-9947-04-03612-8; C. L. Stewart (Publ. Math. Debrecen 65), doi:10.5486/PMD.2004.3190

  Multiplicity (Theorem 12) and Wilson-reflection and least-prime-factor inputs (pp. 462–464) for the collision-core layer and the superseded lcm deduction.

  **Boundary.** Not kernel-checked; load-bearing for nothing beyond the stated uses.

### #243

- P. Erdős and E. G. Straus, [*On the irrationality of certain Ahmes series*](https://users.renyi.hu/~p_erdos/1964-19.pdf) ([read source closure](primary-sources/reciprocal-tail/erdos-straus-1964-source-closure.md))

  Original source for the conditional Ahmes-series rationality criterion cited at Theorem 3, p. 132. Its printed theorem uses the prefix quotient `N_k/n_(k+1)` and the next-index factor `n_(k+1)^2/n_(k+2)-1`; this is the source boundary for the note's correction of the shifted catalogue/survey display.

  **Boundary.** The criterion is conditional and only gives eventual Sylvester recurrence. It does not settle unrestricted #243, the release's Lean results, or any novelty/priority claim.

- D. Duverney, [*Irrationality of Fast Converging Series of Rational Numbers*](https://www.ms.u-tokyo.ac.jp/journal/pdf/jms080206.pdf) ([read source closure](primary-sources/reciprocal-tail/duverney-2001-source-closure.md))

  Corollary 3.2, p. 287, gives a conditional signed form of the #243 criterion: with `a_n` in `{-1,1}`, rationality of `sum a_n/u_n` is equivalent to the eventual signed recurrence under Duverney's one-sided condition `sum (u_(n+1)/u_n^2-1) < infinity`.

  **Boundary.** The source condition is not written with absolute values; absolute convergence is only a stronger sufficient specialization. The result remains conditional and does not settle unrestricted #243, the release's Lean results, or any novelty/priority claim.

- C. Badea, [*A theorem on irrationality of infinite series and applications*](https://www.impan.pl/en/publishing-house/journals-and-series/acta-arithmetica/all/63/4/107785/a-theorem-on-irrationality-of-infinite-series-and-applications) ([publisher PDF](https://matwbn.icm.edu.pl/ksiazki/aa/aa63/aa6342.pdf); [read source closure](primary-sources/reciprocal-tail/badea-1993-source-closure.md))

  Adjacent positive-term prior art: Theorem A (p. 313), Theorem 2.10 and Corollary 2.2 (pp. 315–316) force eventual equality in Badea's explicit term-inequality regime, generalizing the positive Sylvester boundary.

  **Boundary.** The hypotheses are positive rational terms plus an eventual inequality; they do not cover unrestricted #243, mixed-sign state orbits, the release's Lean results, or any novelty/priority claim.

- J. Koizumi, [*Irrationality of the reciprocal sum of doubly exponential sequences* (Integers 26 (2026), A28)](https://math.colgate.edu/~integers/aa28/aa28.pdf); [arXiv:2504.05933](https://arxiv.org/abs/2504.05933) ([read source closure](primary-sources/reciprocal-tail/koizumi-2026-source-closure.md))

  Supplies normalised vanishing for the canonical orbit, the sole hypothesis of the note's headline conditional theorems not proved in Lean; the published Lemma 3 and Proposition 1(2) (the preprint-v1 Lemma 13 and Proposition 19(2)) are conceded in-note as prior art for the note's absorption and descent lemmas.

  **Boundary.** The bridge is prose; only the integer state-system theorems are kernel-checked here, and no priority or independence is adjudicated.

### #251

- V. Kovač, counterexample to Erdős's variable-denominator expectation (2026, Theorem 1)

  Refutes the 1988 expectation that `∑ p_n/(g_1⋯g_n)` is irrational whenever `g_n ≥ 2`, `g_n = o(p_n)`; the note records that the live catalogue still repeats the refuted expectation.

  **Boundary.** Concerns the variable-denominator variant, not the fixed dyadic series studied here.

- J.-C. Schlage-Puchta, *The irrationality of some number theoretical series*, [arXiv:1105.1451](https://arxiv.org/abs/1105.1451)

  Lemma 4, a Selberg-sieve density-zero statement for polynomial relations among consecutive prime gaps, is the input the reasoning record uses. Theorem 2 treats base-`b` digit strings that concatenate the representations of a slowly growing integer sequence, and Theorem 3 gives the `ℚ`-linear independence of `1, S_0, S_1, …` with `S_k = ∑ p_n^k / n!`.

  **Boundary.** No antecedent for the tail criteria recorded here has been located. Theorem 2 is the nearest located neighbour and treats a different object; no declaration in this release uses Lemma 4.

- Y. Zhang (2014); J. Maynard (2015), doi:10.4007/annals.2015.181.1.7; Ford–Green–Konyagin–Maynard–Tao (2018), doi:10.1090/jams/876

  Bounded-gap and large-gap prime results, cited and each shown insufficient for the required joint dyadic distribution of a logarithmic block of gap differences. Maynard's Theorem 1.1 bounds `liminf (p_(n+m) - p_n)` for every fixed `m`; the explicit bound 600 for consecutive gaps is cited by page. The 2018 large-gap Theorem 1 gives an effective lower bound for the largest single consecutive-prime gap below a threshold.

  **Boundary.** Context; none is used as a proof input.

- J. Land, conditional proof of the irrationality of `∑_(n≥1) p_n 2^(-n)` (research draft, 5 September 2026), with an accompanying Lean formalisation of the conditional argument

  Assumes Kuperberg's uniform Hardy-Littlewood prime-tuples conjecture and constructs weighted prime-gap tails; announced on the problem's discussion thread. The #251 note and reasoning record both cite it.

  **Boundary.** Every #251 declaration in this release is unconditional and was proved independently of it. A proof conditional on a prime-tuples conjecture leaves Erdős #251 open unconditionally.

- S. Ringer, *Local gap statistics, telescoping, and normality* (preprint, 11 September 2026, [github.com/StefanRinger/erdos-251](https://github.com/StefanRinger/erdos-251)), with a Lean formalisation whose conditional endpoint theorems take Kuperberg's Conjecture 1.3 as an explicit hypothesis

  Corollary 1.2 deduces from Kuperberg's uniform Hardy-Littlewood prime-tuples conjecture that `∑_(n≥1) p_n B^(-n)` is normal to base `B` for each integer `B ≥ 2`, which gives irrationality at `B = 2`. Appendix C proves unconditionally that `∑_(n≥1) p_n B^(-S_n)` with `S_n = ∑_(j≤n) ⌈log_B log(j+3)⌉` is normal to base `B`. The preprint was submitted as a partial proof claim on the problem page on 13 September 2026. The #251 note and reasoning record both cite it.

  **Boundary.** Every #251 declaration in this release is unconditional and was proved independently of it. A normality proof conditional on a prime-tuples conjecture leaves Erdős #251 open unconditionally.

- W. van Doorn and V. Kovač, [*Lacunary sequences whose reciprocal sums represent all rational numbers in an interval* (Acta Arith. 223 (2026), 275–295)](https://doi.org/10.4064/aa251001-13-1) ([arXiv:2509.24971v3](https://arxiv.org/abs/2509.24971v3); [read source closure](primary-sources/reciprocal-tail/van-doorn-kovac-2026-source-closure.md))

  Proposition 8 proves that the finite reciprocal sums take every rational value in an interval, combining the dense filling of Lemma 7 with a divisibility chain among distinguished terms that eventually absorbs every positive integer. The #251 note and reasoning record cite both statements beside the interval-filling and divisibility-chain steps of the sparse rationalisation construction.

  **Boundary.** The source concerns finite sums of unit fractions and has no prime numerators. The #251 construction uses its own factorial moduli and does not invoke Proposition 8.

### #269

- J. H. Loxton and A. J. van der Poorten, *Arithmetic properties of certain functions in several variables III*, Bull. Austral. Math. Soc. 16 (1977), [doi:10.1017/S0004972700022978](https://doi.org/10.1017/S0004972700022978); Y. Bugeaud and M. Laurent, *Transcendence and continued fraction expansion of values of Hecke–Mahler series*, Acta Arith. 209 (2023), [doi:10.4064/aa220323-18-1](https://doi.org/10.4064/aa220323-18-1)

  The Hecke–Mahler value theorem (Loxton–van der Poorten Theorem 8, p. 40, in the modern form of Bugeaud–Laurent Theorem 1.1) is the transcendence input for the note's two-prime theorems: both the de-duplicated and repeated running-lcm reciprocal sums are transcendental for every pair of distinct primes, by a paper argument.

  **Boundary.** The two-prime theorems are deliberately not Lean declarations; nothing follows for three or more primes.

- S. Fan, [comment on Erdős Problem #269](https://www.erdosproblems.com/forum/thread/269#post-7218), 26 June 2026

  Public forum post giving the same two-channel factorisation, Hecke–Mahler reduction and transcendence conclusion, and the running-LCM identity for every prime set; later comments extend it to coprime pairs. The note first appeared on 22 July 2026, 26 days later.

  **Boundary.** Priority for the two-prime result is Fan's. The note's argument was developed independently and is not a Lean theorem; a broader search would be needed to identify the earliest public proof.

- P. Erdős and E. G. Straus, *On the irrationality of certain series*, Pacific J. Math. 55 (1974), [doi:10.2140/pjm.1974.55.85](https://doi.org/10.2140/pjm.1974.55.85); J. Hančl and R. Tijdeman, *On the irrationality of Cantor and Ahmes series*, Publ. Math. Debrecen 65 (2004), [doi:10.5486/PMD.2004.3254](https://doi.org/10.5486/PMD.2004.3254)

  The literal `{2,3,5}` value is a Cantor series whose normalised tails obey an integer carry recurrence, the classical setting of Erdős–Straus Theorem 2.1 and the Hančl–Tijdeman tail criteria (§§2–3, Theorem 3.1).

  **Boundary.** Both criteria assume a small-numerator hypothesis that fails for this series, so the recurrence, the bounds and the denominator clearing are proved directly in the notes.

- P. Erdős and S. J. Taylor, Proc. London Math. Soc. (3) 7 (1957), Theorem 1; S. Fan, *Strongly complete sets and a conjecture of Erdős*, [arXiv:2607.14071v1](https://arxiv.org/abs/2607.14071v1), Lemma 3.1

  For an unbounded integer sequence with bounded successive ratios, the reals whose multiples by that sequence approach integers form a countable set; the note uses this to identify the integral branch of the bounded-radix alternative.

  **Boundary.** Used only to identify that branch; it gives no irrationality statement.

- P. Erdős, letter of 1 January 1973 (printed p. 335 as cited in the #269 note)

  Asserted the de-duplicated irrationality for given primes without a printed proof; the note's route is an independent modern argument.

  **Boundary.** Historical formulation and priority context only.

### #1041

- P. Erdős, F. Herzog, and G. Piranian, *Metric properties of polynomials* (J. Analyse Math. 6 (1958), Problem 5, p. 139), doi:10.1007/BF02790232; see the [read source closure](primary-sources/bergman-geodesic/erdos-herzog-piranian-1958-source-closure.md)

  Original problem source, including the known input that one lemniscate component contains at least two zeros.

  **Boundary.** Formulation, not proof; the note's saddle-block diagnosis of a recent manuscript is prose, not Lean.

- Current evidence boundary: the committed [`research_corpus/Erdos1041/FRONTIER.md`](../research_corpus/Erdos1041/FRONTIER.md)
  is the dated route for the current source-only research state, not an
  antecedent source. It records certified strategy refutations, surviving
  carriers, and open gaps that are not part of this historical bibliography.
  Read it before generated `STRONGEST_RESULTS.json`, which can lag the dated
  notes. The corpus is not thereby prior art or a reviewed claim: its rows make
  no peer-review, priority, novelty, or significance assertion, and #1041
  remains open.

### #1049

- W. Zudilin, [*Heine's basic transform and a permutation group for $q$-harmonic series* (2004)](https://doi.org/10.4064/aa111-2-4) ([read source closure](primary-sources/reciprocal-tail/zudilin-2004-heine-permutation-group-source-closure.md)); W. Zudilin, [*On the irrationality of generalized $q$-logarithm* (2016)](https://doi.org/10.1007/s40993-016-0042-x) ([read source closure](primary-sources/reciprocal-tail/zudilin-2016-generalized-q-logarithm-source-closure.md))

  The 2004 paper supplies the linear forms, Lemma 7 with display (23) on p. 161, the direction `(14, 12, 14; 27)`, the thirteen intervals, and the constant `C_1/C_0 = 2.46497868...` printed on p. 162 as an integer-base exponent bound, which defines the rational-base region of the #1049 notes. The 2016 paper proves the `q`-order inequality for the normalised Hankel determinant and remarks in its Section 2, on p. 4, that its results can be given at non-integer rational bases under a computable height restriction.

  **Boundary.** Both papers state their theorems for integer bases, and the 2016 remark computes no constant. The rational specialisation, its denominator accounting, the explicit region and the equality case of the Hankel order are argued in the #1049 notes, and no priority claim is attached to them.

- P. Bundschuh and K. Väänänen, *Compositio Math.* 91 (1994), Theorem 2, [official Numdam PDF](https://numdam.org/item/CM_1994__91_2_175_0.pdf) ([read source closure](primary-sources/totient-kernel/bundschuh-vaanenen-1994-source-closure.md))

  External irrationality criterion at base `7/2`; the release checks only its elementary Archimedean height inequality.

  **Boundary.** The analytic argument remains external, and nothing follows at `3/2`.

- T. Amdeberhan and D. Zeilberger, [*$q$-Apéry irrationality proofs by $q$-WZ pairs* (1998)](https://doi.org/10.1006/aama.1997.0565) ([read source closure](primary-sources/reciprocal-tail/amdeberhan-zeilberger-1998-q-apery-source-closure.md)); W. Van Assche, [*Little $q$-Legendre polynomials and irrationality of certain Lambert series* (2001)](https://doi.org/10.1023/A:1012930828917) ([read source closure](primary-sources/reciprocal-tail/van-assche-2001-little-q-legendre-source-closure.md)); P. B. Borwein, [*On the irrationality of certain series* (1992)](https://doi.org/10.1017/S030500410007081X)

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
