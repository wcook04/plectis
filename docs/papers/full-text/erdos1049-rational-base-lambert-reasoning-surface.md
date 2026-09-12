<a id="erdos1049-rational-base-lambert-reasoning-surface"></a>

# Rational-Base Lambert Series: Complete Reasoning Record

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

Erdős Problem #1049 asks whether $`F(t)=\sum_{n\ge1}(t^n-1)^{-1}`$ is irrational for every rational $`t>1`$. We prove that $`F(a/b)`$ is irrational for every pair of coprime integers $`a>b\ge1`$ with $`b^{\mu}<a`$, where $`\mu=C_1/C_0=2.464978683574975\ldots`$, equivalently $`\log b/\log a<\theta^{*}=1/\mu=0.40568302138406054\ldots`$, and where $`C_1=1091/2`$ and $`C_0=266-(3/\pi^{2})(225-J)`$ are the constants printed by Zudilin in 2004 for his $`(14,12,14;27)`$ direction, whose ratio is the integer-base irrationality-exponent bound proved there. The first base this settles beyond the published region of Bundschuh and Väänänen is $`31/4`$, together with every power $`(31/4)^{r}`$, $`r\ge1`$.

The region theorem is an ordinary proof. It cites the polynomial conclusion of Zudilin’s Lemma 7 together with the inputs of that lemma’s own proof, and every remaining step is proved here: the exact degrees, the cyclotomic limit, positivity, the homogenisation and the denominator balance. The finite arithmetic is checked by the Lean kernel: the rational bracket $`81/200<\theta^{*}<1/2`$ around the derived constant, the integer identities of the degree computation, and the comparisons that place $`31/4`$ inside the region and outside the earlier one.

A degree-budget theorem bounds the reach of the same mechanism. For a family of integer polynomial pairs with decay exponent $`\sigma`$, degree exponent $`\delta`$ and coefficient-height exponent $`h`$, all three independent of the base, one has $`\sigma\le\delta`$, so the homogenised forms are proved to decay only below $`\sigma/(\sigma+\delta)\le1/2`$. The base $`3/2`$ sits at $`\log2/\log3=0.6309297535714574\ldots`$, which is $`0.2252467\ldots`$ above $`\theta^{*}`$.

We also determine the $`q`$-order of Zudilin’s normalised Hankel determinant exactly: $`\operatorname{ord}_qV_N^{*}=N(N-1)(2N-1)/6`$ at every rank, with leading coefficient $`(N!)^{2}(N+1)!/2^{N}`$, where the source proves the inequality alone. The initial monomial of every transformed row is identified here by a filtered reciprocal-state argument. That all-rank identification, including the first transformed-row initial monomial and the closed-form assembly, is ordinary mathematics, not a kernel-checked theorem of this library. The all-depth associated-graded recurrence is kernel-checked. The Lean formalisation of the row identity stops at the second row, so the Lean identification of the determinant itself retains a row hypothesis.

At $`3/2`$ we prove exact obstructions to several approximation methods and a conditional reduction of the number of rows needed to cancel endpoint residues. The integer bracket $`2^{64}<3^{41}<2^{65}`$ gives a uniform gap greater than $`3/13`$ between $`\log2/\log3`$ and every threshold in the rectangular Hermite–Padé exponent model studied here. The scalar factor and its universally forced first-order border also fall short of the required $`39/41`$ charge. These comparisons exclude the stated height mechanisms.

For the additive alternative, the same bracket gives a four-jet collision among binary selectors whenever $`M\ge130T+2S`$ polynomial pairs are used at bottom depth $`41T`$ and top depth $`S`$. The counting threshold is exact at $`T=1`$. If the rows modulo $`2^S3^R`$ are unimodular and their adjacent determinants vanish, a Bézout shear reduces all selector sums to one residue coordinate; $`S+2R`$ rows then suffice for $`R>0`$. Neither coordinate need be invertible. A separate bounded-fibre theorem states the additional multiplicity estimate that would force a collision with distinct analytic remainders.

Integer scalar content cannot improve the ratio of a determinant’s local divisor to its absolute height, while coordinatewise clearing at $`3/2`$ fails an exact exponential growth bound. The unresolved step at that base is an actual approximation family combining primitive coefficients, a nonzero remainder, and decay faster than height growth. No irrationality theorem at $`3/2`$ is proved.

<div class="center">

<div class="minipage">

------------------------------------------------------------------------

**What the paper proves**

**New irrational bases.** $`F(a/b)`$ is irrational for coprime $`a>b\ge1`$ with $`\log b/\log a<\theta^{*}=0.40568302138406054\ldots`$ (Theorem <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a>). The base $`31/4`$ and every power $`(31/4)^{r}`$ lie in that region and outside the published region of Bundschuh and Väänänen, whose cutoff is $`1/2-1/\pi^{2}=0.398678816\ldots`$ (Theorem <a href="#long1049:res:31over4" data-reference-type="ref" data-reference="long1049:res:31over4">3</a>). **Evidence.** An ordinary proof citing Zudilin’s Lemma 7 and the inputs of its proof, with the finite height arithmetic at $`31/4`$ checked by the Lean kernel. **Reach of the mechanism.** A degree-budget theorem caps every base-uniform family of this shape at $`\sigma/(\sigma+\delta)\le1/2`$, and $`3/2`$ sits at $`0.6309297535714574\ldots`$ (Theorem <a href="#long1049:res:archcap" data-reference-type="ref" data-reference="long1049:res:archcap">4</a>). **Exact arithmetic at $`3/2`$.** The bracket $`2^{64}<3^{41}<2^{65}`$ excludes the stated scalar and first-order Hermite–Padé height mechanisms there. It also yields the sharp finite four-jet count at bottom depth $`41`$, with a Bézout–Plücker reduction under explicit minor and unimodularity hypotheses. **Transfer obstruction.** Direct integer-base clearing fails by an exact growth inequality and forcing recurrence. **Open boundary.** No primitive noncollapsed approximation family with a sufficiently small nonzero remainder is constructed at $`3/2`$, so no irrationality at $`3/2`$ is proved, and the universal assertion over all rational $`t>1`$ remains open.

</div>

</div>

<a id="long1049:sec:problem"></a>

# Introduction

Let $`t>1`$ be a rational number and let $`\tau(n)`$ count the divisors of $`n`$. Erdős Problem #1049 asks whether
``` math
F(t)=\sum_{n\ge1}\frac{1}{t^{n}-1}=\sum_{n\ge1}\frac{\tau(n)}{t^{n}}
```
is irrational \[erdos1988, p. 102\].

The two forms agree by expanding $`(t^{n}-1)^{-1}=\sum_{k\ge1}t^{-nk}`$ and collecting the terms with the same exponent, the coefficient of $`t^{-m}`$ being the number of divisors of $`m`$. The question is a conjecture of Chowla; Erdős proved it for every integer $`t\ge2`$ \[erdos1948\]. Bloom’s current catalogue record reproduces the displayed rational-$`t`$ question, labels it *open*, attributes it to Chowla, and points to Erdős’s 1988 statement on p. 102 and the 1948 integer-base theorem \[erdosproblems\]. This note proves $`F(a/b)`$ irrational for every pair of coprime integers $`a>b\ge1`$ with $`\log b/\log a<\theta^{*}=0.40568302138406054\ldots`$, which settles the base $`31/4`$ and every power $`(31/4)^{r}`$, $`r\ge1`$. The universal conjecture over all rational $`t>1`$ remains open; individual non-integral rational bases are known, including $`7/2`$ below.

Write $`t=r/s`$ in lowest terms with $`r>s\ge1`$, so that $`s=1`$ is exactly the integer case Erdős settled. The resistant explicit base of least naive height $`H(r/s)=\max(r,s)`$ is $`t=3/2`$. A published height criterion of Bundschuh and Väänänen \[bv1994, Thm. 2, p. 177; hypotheses pp. 175–176\] settles a family of rational bases restricted by a height condition; that family contains $`7/2`$ and does not contain $`3/2`$. Between the two lies the question this note is about: what exactly stops the integer-base argument from running at $`3/2`$?

<a id="relation-to-prior-work."></a>

#### Relation to prior work.

The *Formal Conjectures* file for Problem #1049 contains the conjecture and integer-base theorem as `sorry` placeholders, but it also proves the Lambert identity between the two displayed series for rational $`t`$ \[formalconjectures1049\]. In the present $`t>1`$ regime its `lambert_convergent` branch is an ordinary convergent-series proof; the same file’s $`|t|\le1`$ branch instead uses Lean’s convention that the `tsum` of a nonsummable series is zero. Thus it supplies genuine checked prior art for the identity, but no irrationality theorem. The present note formalises propositions about the clearing argument and likewise does not answer the conjecture.

Erdős’s positive-integer theorem of 1948 \[erdos1948\] sits inside a larger integer-base literature. At the level of functions, Rivin proves that if a sequence $`\gamma`$ and its divisor-sum sequence are both eventually linearly recurrent, then $`\gamma`$ is finitely supported \[rivin2026, Theorem 1.1, p. 2; proof pp. 6–7\]. His periodic-coefficient corollary therefore shows that
``` math
\sum_{n\ge1}\frac{z^n}{1-z^n}
```
is not a rational function \[rivin2026, Corollary 6.4, p. 9\]. This is an exact structural statement about the function underlying Problem #1049, but it gives no irrationality statement for a special value at $`z=1/t`$: a nonrational function may take rational values at particular rational points.

In 1991 Borwein proved the irrationality of shifted series $`\sum_{n\ge1}(t^{n}+w)^{-1}`$ at integer bases $`t\ge2`$, for every nonzero rational $`w`$ with $`w\ne-t^m`$ for all $`m\ge1`$, by Padé approximation rather than by digit clearing; his estimates also show that these values are not Liouville numbers \[borwein1991, Thm. 4, pp. 257–258\]. In 2001 Van Assche recovered the integer-base irrationality and the bound $`\mu(F(p))\le 2\pi^2/(\pi^2-2)=2.50828\ldots`$ using little $`q`$-Legendre Padé approximants  \[vanassche2001, Thm. 1, p. 10; proof pp. 10–11\]. His more general Theorem 3 proves irrationality of $`\sum_{k\ge1}(cp^k-1)^{-1}`$ for an integer $`p>1`$ and fixed rational $`c`$ away from the poles \[vanassche2001, Thm. 3, p. 14\]; it does not cover a rational noninteger base $`t`$ in $`F(t)`$, because the multiplier needed to write $`t^k`$ over an integer base varies with $`k`$.

The same Lambert value was already the target of Amdeberhan and Zeilberger’s $`q`$-WZ construction \[az1998\]. Here $`p>1`$ is the integer-base parameter and the little-$`q`$ kernel uses $`q=p^{-1}`$. The two constructions share that bivariate little-$`q`$-Legendre Padé kernel, but Van Assche’s diagonal does not satisfy the Amdeberhan–Zeilberger scalar recurrence. Their Theorems 1 and 2 do prove, respectively, the irrationality of the non-alternating $`h_p(1)`$ and alternating $`q`$-logarithm values for their stated integer parameters, with reported irrationality measure $`4.80`$; those are external integer-parameter results and do not transfer to the rational noninteger base $`3/2`$ studied here.

Amdeberhan–Zeilberger use the moving diagonal $`P_n(p^{n+1}\mid p^{-1})`$, whereas Van Assche uses $`P_n(p^n\mid p^{-1})`$. Van Assche also records, citing Borwein’s 1992 Lemma 2, the neighbouring evaluation $`P_{n-1}(c p^{n+1}\mid p^{-1})`$ \[borwein1992; vanassche2001\]. The shared kernel therefore does not license transfer of recurrence, endpoint, lattice, or valuation claims between the diagonals. Indeed, if $`A_n(p)=P_n(p^n\mid p^{-1})`$, exact substitution at $`n=0`$ into the Amdeberhan–Zeilberger operator leaves
``` math
-p(p-1)^2(p+1)(p^5+2p^4+2p^3+2p^2+2),
```
which is nonzero for every real $`p>1`$. One nonzero residual is decisive for non-transfer of that recurrence.

Lean checks the [exact residual factorisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/QAperyDiagonalNonEquivalence.lean#L67) and its [nonvanishing for $`p>1`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/QAperyDiagonalNonEquivalence.lean#L94). These are finite statements at $`n=0`$; they do not supply a recurrence for either diagonal. No recurrence, endpoint, lattice, or valuation statement for one diagonal is used for the other; the displayed exact residual is the sole claim made here about their incompatibility.

There is a second distinction at rational base $`3/2`$. Over the checked range, the raw rational approximation errors decrease while the selected cleared integer forms grow from $`n\ge2`$. This says that the chosen integerisation does not produce small linear forms; it does *not* say that the raw approximants fail to converge.

In 2013 Vandehey proved that $`\sum_{n\ge1}d(n)a_n/b^n`$ is irrational whenever $`b>1`$ is an integer and $`(a_n)`$ ranges in a finite integer alphabet excluding zero; taking $`a_n=(-1)^n`$ completes the elementary digit method for integer bases $`b\le-2`$ \[vandehey2013, Thm. 1.2, p. 2\]. His companion theorem permits a finite alphabet of nonnegative integers containing zero, provided the coefficient sequence is not eventually zero \[vandehey2013, Thm. 1.1, p. 2\]. All three retain an integer base. Luca and Tachiya’s periodic-coefficient theorem likewise proves irrationality at every integer base of absolute value greater than one; their full-support example strengthens this to joint linear independence for finite families of iterated divisor functions \[lucatachiya2017, Theorem A, p. 139; Example 1, p. 140\]. This is strong integer-base evidence, but it does not cover a rational noninteger base.

In 2004 Zudilin obtained the uniform bound $`\mu(F(p))\le2.46497868\ldots`$ for every integer $`p\notin\{0,\pm1\}`$, by way of Heine’s basic transform and a permutation group \[zudilin2004, Thm. 1, p. 154; Secs. 4–5, pp. 159–162\]. The ordinary-hypergeometric antecedent is Rhin and Viola’s $`S_5`$ action and twelve-coset denominator reduction for rational forms in $`\zeta(2)`$ \[rhinviola1996, Sec. 3, pp. 38–42; Sec. 4, pp. 46–51\].

Those sources motivate the permutation, denominator and polynomial- specialisation architecture of Section <a href="#long1049:sec:endpoints" data-reference-type="ref" data-reference="long1049:sec:endpoints">5</a>; the endpoint lemmas there are abstract and are not yet applied to either source’s actual coefficient family.

The neighbouring problem of Lambert subseries $`\sum_{n\in A}(t^{n}-1)^{-1}`$ over a restricted index set $`A`$ is treated by Kovač and Tao \[kovactao2024\].

The rational non-integer progress relevant here is instead the height criterion of Bundschuh and Väänänen \[bv1994\], which remains the strongest explicit numerical threshold among the sources compared here for this value. Zudilin’s later Padé-and-Hankel treatment also admits non-integral rational bases: its generalized $`q`$-logarithm remarks that its results also hold for non-integer $`p=r/s`$ with $`|p|>1`$, under an assumption $`\log|r|>c\log|s|`$ for some computable $`c>0`$ \[zudilin2016\]. No value of $`c`$ is computed there. That remark announces the shape of a rational-base extension for the generalized $`q`$-logarithm of that paper. Section <a href="#long1049:sec:region" data-reference-type="ref" data-reference="long1049:sec:region">2</a> identifies an admissible constant for $`F`$ itself, $`c=\mu=2.464978683574975\ldots`$, which is the 2004 bound quoted above, by specialising the 2004 forms at a rational base and carrying out the denominator accounting, and derives the region and its first new base from that constant.

A third published rational-base region for this same series is Duverney’s Théorème 2, whose hypothesis is $`\log|s|/\log|r|<\frac13\bigl(1-3/\pi^{2}\bigr)=0.2320\ldots`$ \[duverney1996, Théorème 2, p. 174\]; his Théorème 1 for general numerators is weaker still. Both cutoffs lie strictly inside the Bundschuh and Väänänen region. Matala-aho, Väänänen and Zudilin’s combined treatment of $`q`$-logarithms keeps the integer hypothesis $`p=1/q\in\mathbb{Z}\mathbin{\backslash}\{0,\pm1\}`$ throughout, and states in print that its methods do not sharpen the $`q`$-harmonic case of \[zudilin2004\] \[matalaaho2006, abstract p. 879; introduction p. 880\]. So none of the printed regions for $`F`$ compared here reaches $`\log4/\log31`$.

<a id="erdőss-integer-base-argument-in-outline."></a>

#### Erdős’s integer-base argument, in outline.

For an integer $`b\ge2`$, Erdős rewrites $`F(b)=\sum_{n\ge1}\tau(n)b^{-n}`$. A Chinese-remainder construction forces arbitrarily long blocks in which the divisor coefficients have the powers of $`b`$ needed to make the corresponding base-$`b`$ digits zero. Explicit bounds control the middle and far tails, while positivity proves that the expansion does not terminate. The resulting base-$`b`$ expansion has arbitrarily long zero blocks without being eventually zero and is therefore irrational  \[erdos1948, pp. 63–66\].

<a id="the-direct-cut-and-clear-attempt-studied-here."></a>

#### The direct cut-and-clear attempt studied here.

A more naive attempt is to suppose $`F(b)=p/q`$, cut at $`N`$, and multiply the remaining identity by $`qb^N`$. This does not by itself trap a positive integer below $`1`$: the first uncleared tail contribution is $`q\tau(N+1)/b`$. The sections below isolate additional corridor hypotheses under which a bounded-window version of this attempt would work, and then show why those hypotheses fail at $`3/2`$.

Write $`\beta=r/s`$ for the base and $`c(n)`$ for the coefficient of $`\beta^{-n}`$, so that $`c=\tau`$ in the case at hand. The term $`c(n)\beta^{-n}`$ is $`c(n)s^{n}/r^{n}`$. Clearing the power of $`r`$ leaves the numerator factor $`s^{n}`$ in place. That factor is invisible when $`s=1`$ and grows geometrically when $`s\ge2`$. At $`3/2`$ it is $`2^{n}`$.

<a id="terminology."></a>

#### Terminology.

The linear-form method uses polynomial pairs before specialisation and integer pairs afterwards. We reserve *row* for an integer pair $`(U,V)`$. Its *integer scalar content* is $`\gcd(|U|,|V|)`$; a row is *primitive* when this number is $`1`$, and dividing by it is *primitive normalisation*. A polynomial pair may instead have a polynomial common factor in $`\mathbb{Z}[X]`$; that is a different operation and is not called row content here. The *exterior determinant* of two integer rows is $`U_{n}V_{m}-U_{m}V_{n}`$, the determinant of the $`2\times2`$ matrix they form. Two quantities attached to that determinant are compared throughout: an integer dividing it, which is a local gain, and its absolute value, which is an Archimedean cost; we call that comparison the *local-to-Archimedean balance*.

The *endpoints* of a coefficient polynomial, taken relative to the declared width $`W`$ of Section <a href="#long1049:sec:endpoints" data-reference-type="ref" data-reference="long1049:sec:endpoints">5</a>, are its constant coefficient and its coefficient at $`W`$; we call these the *constant endpoint* and the *top endpoint*, so the top endpoint is the coefficient at $`W`$ and not the leading coefficient unless the two agree. A *unit* endpoint is one equal to $`\pm1`$, the units of $`\mathbb{Z}`$; Theorem <a href="#long1049:res:endpoints" data-reference-type="ref" data-reference="long1049:res:endpoints">14</a> is the reason only these two coefficients decide divisibility by $`3`$ and by $`2`$ after specialisation at $`(3,2)`$. A *jet* is a residue of a specialised coefficient modulo a prime power: the bottom jet is its residue modulo $`3^{R}`$ and the top jet its residue modulo $`2^{S}`$, and $`R`$ and $`S`$ are the bottom and top *depths*. A jet vanishes exactly when the prime power in question divides the specialised coefficient.

<a id="the-shortfall-at-32."></a>

#### The shortfall at $`3/2`$.

The elementary method and the linear-form method are both examined below. For the height argument, the exact bracket $`2^{64}<3^{41}<2^{65}`$ gives a gap greater than $`3/13`$ across the whole admissible rectangular exponent cone and fixes the $`39/41`$ denominator-charge comparison. Neither the source scalar factor nor that factor together with the universally forced first-order residual border reaches the required charge. These comparisons leave higher residual valuations, determinant cancellation, and other integral models untouched. For the additive argument, the same bracket replaces the generic $`4R+2S`$ threshold by $`130T+2S`$ at depth $`R=41T`$ and gives an exact first-row failure at $`T=1`$.

For the coordinatewise clearing scheme the leftover at each step is the forcing term of an exact recurrence, of size at least $`2^{N+1}`$ whenever $`s\ge2`$ and the scaling constant $`B`$ and the coefficient $`c(N+1)`$ are at least $`1`$ (Theorem <a href="#long1049:res:forcing" data-reference-type="ref" data-reference="long1049:res:forcing">32</a>), and the scheme itself is excluded at $`3/2`$ for every shift $`N\ge1`$ and every cleared window of width $`K\ge1`$ (Theorem <a href="#long1049:res:nocorridor" data-reference-type="ref" data-reference="long1049:res:nocorridor">30</a>).

For the linear-form constructions we examine two possible sources of $`2`$-adic and $`3`$-adic gain. Integer scalar content is exactly neutral, since it scales the exterior determinant and its absolute height by the same factor (Theorem <a href="#long1049:res:content" data-reference-type="ref" data-reference="long1049:res:content">12</a>), while unit endpoints keep both $`2`$ and $`3`$ out of any common divisor of the two specialised evaluations (Theorem <a href="#long1049:res:endpoints" data-reference-type="ref" data-reference="long1049:res:endpoints">14</a> and Proposition <a href="#long1049:res:commonmult" data-reference-type="ref" data-reference="long1049:res:commonmult">16</a>). Corollary <a href="#long1049:res:nomult" data-reference-type="ref" data-reference="long1049:res:nomult">18</a> states the two scoped exclusions together; neither is claimed to be necessary for every linear-form proof. Separately, the scalar parameter margin is negative under the assumed source inequality (Theorem <a href="#long1049:res:scalar" data-reference-type="ref" data-reference="long1049:res:scalar">25</a>).

One candidate pursued here is additive: an integer relation among rows that cancels the endpoint jets. Theorem <a href="#long1049:res:jetkernel" data-reference-type="ref" data-reference="long1049:res:jetkernel">20</a> shows that a nonzero relation with coefficients in $`\{-1,0,1\}`$ cancelling all four jets exists whenever the bottom depth is positive and the number of coefficient pairs is at least $`4R+2S`$. It does not show that the resulting combination has a nonzero polynomial pair or a nonzero remainder. Problem <a href="#long1049:prob:kernel" data-reference-type="ref" data-reference="long1049:prob:kernel">37</a> gives a precise sufficient specification for that particular candidate architecture, not a necessary condition for solving Problem #1049.

Sections <a href="#long1049:sec:sevenhalves" data-reference-type="ref" data-reference="long1049:sec:sevenhalves">8</a> and <a href="#long1049:sec:pade" data-reference-type="ref" data-reference="long1049:sec:pade">9</a> record two external methods and what each leaves unproved at $`3/2`$.

<a id="sharpness."></a>

#### Sharpness.

Two questions of scope are worth isolating. The corridor bound of Theorem <a href="#long1049:res:corridorbound" data-reference-type="ref" data-reference="long1049:res:corridorbound">27</a> is exponential on the left and linear on the right, so for a fixed numerator and any $`s\ge2`$ a corridor can survive only for bounded $`N+K`$; the base $`3/2`$ is the case in which the crossing has already happened at the smallest admissible window, which is why the exclusion there holds for all $`N\ge1`$ and $`K\ge1`$ with no further restriction. The height criterion of \[bv1994\] is restricted by a height condition satisfied at $`7/2`$ and not at $`3/2`$, so the two bases are separated by that criterion rather than by a universal obstruction. The exponent $`65`$ in $`3^{41}<2^{65}`$ cannot be replaced by $`64`$. The separate direct comparison $`2^{129}<3^{82}`$ then proves that at bottom depth $`41`$ the least number of input rows satisfying the ambient-cardinality inequality is exactly $`130+2S`$: $`129+2S`$ does not satisfy it. That is a statement about the counting test, and a family with fewer rows may still have a collision.

For $`R=41T`$ with $`T>1`$, the displayed $`130T+2S`$ bound is uniform and sufficient and is not always the least such number.

*Status.* The problem treated here is open, and this note does not close it. Every statement below marked as checked is a proposition that the pinned Lean kernel accepts from the sources this note links to, with no `sorry`, no added axiom, and no unchecked evaluation. That is a claim about the formal statement, not about its mathematical interest, its novelty, or the original problem. The unresolved obligations are named exactly, in their own section, and none of the finite computations, reductions, or no-go results here removes one of them.

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.

<a id="results-and-boundary."></a>

#### Results and boundary.

Theorems <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a> and <a href="#long1049:res:31over4" data-reference-type="ref" data-reference="long1049:res:31over4">3</a> are ordinary mathematics. They consume Zudilin’s Lemma 7 together with the inputs of that lemma’s own proof, and every further step is proved in Section <a href="#long1049:sec:region" data-reference-type="ref" data-reference="long1049:sec:region">2</a>. They are not kernel-checked. The linked Lean declarations establish exact inequalities, congruences, finite collision counts, recurrence identities, and exclusions for the named models; among them are the height comparisons that place $`31/4`$ inside the enlarged logarithmic region and outside the earlier one. No Lean declaration in this release’s library carries an irrationality statement at a rational noninteger base. Bundschuh and Väänänen’s irrationality theorem at $`7/2`$, Rivin’s functional nonrationality theorem, and the two-variable Mahler theorem used below remain external results. At $`3/2`$, the missing step is still an actual primitive approximation family with nonzero remainder and an asymptotic height margin.

<a id="structure."></a>

#### Structure.

Section <a href="#long1049:sec:region" data-reference-type="ref" data-reference="long1049:sec:region">2</a> states and proves the region theorem, the base $`31/4`$ and the degree-budget cap on the mechanism that produces them. Section <a href="#long1049:sec:sharp" data-reference-type="ref" data-reference="long1049:sec:sharp">3</a> derives the height and charge exclusions from the sharp $`41/65`$ power certificate. Section <a href="#long1049:sec:primitive" data-reference-type="ref" data-reference="long1049:sec:primitive">4</a> proves that integer scalar content is neutral for the local-to-Archimedean balance.

Section <a href="#long1049:sec:endpoints" data-reference-type="ref" data-reference="long1049:sec:endpoints">5</a> proves the endpoint congruences at $`(3,2)`$, deduces from them and from Section <a href="#long1049:sec:primitive" data-reference-type="ref" data-reference="long1049:sec:primitive">4</a> that neither integer scalar content nor a common divisor of the two specialised evaluations supplies the targeted endpoint gain, gives the four-jet collision count and its conditional Bézout–Plücker compression, and records one further exclusion on Zudilin’s scalar parameters. Sections <a href="#long1049:sec:corridor" data-reference-type="ref" data-reference="long1049:sec:corridor">6</a> and <a href="#long1049:sec:tail" data-reference-type="ref" data-reference="long1049:sec:tail">7</a> return to the elementary clearing scheme and record what the residue $`s^{n}`$ costs there, first as an exclusion and then as an exact recurrence with a lower bound on the surviving term. Sections <a href="#long1049:sec:sevenhalves" data-reference-type="ref" data-reference="long1049:sec:sevenhalves">8</a> and <a href="#long1049:sec:pade" data-reference-type="ref" data-reference="long1049:sec:pade">9</a> record what is and is not formalised of two external routes, together with the separate $`81/200`$ logarithmic comparison. Section <a href="#long1049:sec:open" data-reference-type="ref" data-reference="long1049:sec:open">10</a> separates kernel escape from asymptotic adequacy and states the remaining obligations. Linked phrases open the corresponding Lean declaration at the pinned source revision 92b88dc1bbe0.

**Keywords.** irrationality; Lambert series; rational base; Padé approximation; Lean 4. **MSC 2020.** 11J72 (primary); 11J82, 68V20 (secondary).

<a id="long1049:sec:region"></a>

# The region $`b^{\mu}<a`$ and the base $`31/4`$

This section states the note’s leading results. Fix Zudilin’s direction $`(\alpha_0,\alpha_1,\alpha_2;\beta)=(14,12,14;27)`$ of \[zudilin2004, Sec. 5\] and put
``` math
C_1=(\alpha_0+\alpha_1+\alpha_2)\beta-\tfrac12(\alpha_1^{2}+\alpha_2^{2}+\beta^{2})
 =\frac{1091}{2},
 \qquad
 C_0=266-\frac{3}{\pi^{2}}\,(225-J),
```
``` math
J=\sum_{i=1}^{13}\bigl(\psi_1(u_i)-\psi_1(v_i)\bigr),
 \qquad
 \psi_1(x)=\sum_{k\ge0}\frac1{(k+x)^{2}},
```
the thirteen demi-intervals $`[u_i,v_i)`$ being $`[1/14,1/12)`$, $`[1/7,1/6)`$, $`[3/14,1/4)`$, $`[2/7,1/3)`$, $`[5/14,2/5)`$, $`[3/7,7/15)`$, $`[1/2,8/15)`$, $`[4/7,3/5)`$, $`[9/14,2/3)`$, $`[5/7,11/15)`$, $`[11/14,4/5)`$, $`[6/7,13/15)`$, $`[13/14,14/15)`$. Numerically
``` math
\begin{align*}
 J&=77.943184475009095922589567023992\ldots,\\
 C_0&=221.300088165005025124042696692215\ldots,\\
 \mu&:=\frac{C_1}{C_0}=2.464978683574975037454488275535\ldots,\\
 \theta^{*}&:=\frac1\mu=0.405683021384060541015660305576\ldots
\end{align*}
```
The direction, the thirteen demi-intervals, the values $`C_1=545.5`$ and $`C_0=221.30008816\ldots`$ and the ratio $`C_1/C_0=2.46497868\ldots`$ are printed at \[zudilin2004, p. 162\], where that ratio is the irrationality-exponent bound of \[zudilin2004, Thm. 1, p. 154\] for integer bases. The further digits displayed above and the reciprocal $`\theta^{*}`$ are recomputed here from the same trigamma series.

The proof below needs $`J`$ in its combinatorial form as well. Put
``` math
\omega(\xi)=\max\bigl\{0,\;
 \lfloor14\xi\rfloor+\lfloor13\xi\rfloor-\lfloor12\xi\rfloor-\lfloor15\xi\rfloor,\;
 2\lfloor14\xi\rfloor-\lfloor13\xi\rfloor-\lfloor15\xi\rfloor\bigr\},
```
the weight attached by \[zudilin2004, (26)\] to the six-tuple $`c=(13,14,12,14,15,13)`$ of the fixed direction.

<div id="long1049:res:omega-indicator" class="lemma">

**Lemma 1** (the weight is an indicator). *On $`[0,1)`$ the function $`\omega`$ takes only the values $`0`$ and $`1`$, and $`\omega=1`$ exactly on the union of the thirteen demi-intervals listed above.*

</div>

<div class="proof">

*Proof.* Each of the three expressions inside the maximum is constant on every interval between consecutive elements of $`\{k/c: c\in\{12,13,14,15\},\ 0\le k\le c\}`$, since those are the only points at which one of the four floor functions changes. There are $`48`$ such intervals in $`[0,1)`$; evaluating $`\omega`$ at the midpoint of each gives the value $`1`$ on the thirteen listed demi-intervals and $`0`$ elsewhere, and the thirteen listed intervals are unions of consecutive cells. The evaluation is exact rational arithmetic on finitely many points. ◻

</div>

Writing $`\mathbf 1_{[u,v)}`$ for indicators, Lemma <a href="#long1049:res:omega-indicator" data-reference-type="ref" data-reference="long1049:res:omega-indicator">1</a> and termwise integration of the positive series $`-\psi_1'(\xi)=\sum_{k\ge0}2(k+\xi)^{-3}`$ give the two forms of $`J`$ used below,
``` math
J=\int_0^1\omega(\xi)\sum_{k\ge0}\frac{2}{(k+\xi)^{3}}\,d\xi
  =\sum_{i=1}^{13}\bigl(\psi_1(u_i)-\psi_1(v_i)\bigr),
```
the first being the integral $`\int_0^1\omega\,d(-\psi_1)`$ of \[zudilin2004, Lemma 2\]. Since $`\omega`$ vanishes near $`0`$, both are finite.

<div id="long1049:res:region" class="theorem">

**Theorem 2** (rational-base region). *Let $`a>b\ge1`$ be coprime integers with
``` math
b^{\mu}<a,
 \qquad\text{equivalently}\qquad
 \frac{\log b}{\log a}<\theta^{*}=0.40568302138406054\ldots
```
Then $`F(a/b)=\sum_{m\ge1}(( a/b)^{m}-1)^{-1}`$ is irrational.*

</div>

The proof occupies Sections <a href="#long1049:sec:source-forms" data-reference-type="ref" data-reference="long1049:sec:source-forms">2.1</a>–<a href="#long1049:sec:integer-forms" data-reference-type="ref" data-reference="long1049:sec:integer-forms">2.4</a>. It cites one external statement, the polynomial conclusion of Zudilin’s Lemma 7 together with the coefficientwise argument that proves it; everything else is carried out here.

<a id="long1049:sec:source-forms"></a>

## The source forms as polynomial identities

Fix $`n\ge1`$, write $`x`$ for an indeterminate or a real number greater than $`1`$ according to context, and put $`q=x^{-1}`$. Set
``` math
\begin{gathered}
 a_0=14n+1,\quad a_1=12n+1,\quad a_2=14n+1,\\
 \beta_n=27n+2,\quad N=15n,\quad M_n=266n^{2}+34n+1 .
\end{gathered}
```
The symbol $`\beta_n`$ is the upper hypergeometric parameter of \[zudilin2004, Sec. 2\]; the letter $`b`$ continues to denote the denominator of the base, and $`M_n`$ is the integer of that paper’s (16). With $`(z;q)_m=\prod_{j=0}^{m-1}(1-zq^{j})`$, the source’s summand is
``` math
\begin{equation}
\label{long1049:eq:positive-source-form}
 H_n(x)=\sum_{t\ge0}
 \frac{(q^{t+1};q)_{a_1-1}}{(q;q)_{a_1-1}}\,
 \frac{(q;q)_{\beta_n-a_2-1}}{(q^{a_2+t};q)_{\beta_n-a_2}}\,q^{a_0t},
\end{equation}
```
and \[zudilin2004, (8)–(11)\] gives $`H_n=A_nF-B_n`$ with $`A_n,B_n\in\mathbb{Q}(x)`$. The two coefficients can be written down. Let $`\genfrac{[}{]}{0pt}{}{m}{r}_X`$ be the Gaussian binomial polynomial, of degree $`r(m-r)`$ and with nonnegative coefficients summing to $`\binom{m}{r}`$, and for $`a_2\le k\le\beta_n-1`$ put
``` math
\begin{equation}
\label{long1049:eq:c-explicit}
 c_{n,k}(X)=(-1)^{a_1+a_2+k+1}X^{e_{n,k}}
 \genfrac{[}{]}{0pt}{}{k-1}{a_1-1}_X
 \genfrac{[}{]}{0pt}{}{\beta_n-a_2-1}{\beta_n-k-1}_X,
\end{equation}
```
``` math
e_{n,k}=\frac{a_1(a_1-1)}2-\frac{(\beta_n-a_2)(\beta_n-a_2-1)}2
 +\frac{(\beta_n-k)(\beta_n-k-1)}2 .
```
Then
``` math
\begin{align}
 A_n(X)&=\sum_{k=a_2}^{\beta_n-1}c_{n,k}(X)X^{a_0k},\label{long1049:eq:A-explicit}\\
 B_n(X)&=\sum_{k=a_2}^{\beta_n-1}c_{n,k}(X)X^{a_0k}
 \biggl(\sum_{l=1}^{k-a_1}\frac1{X^{l}-1}
 +\sum_{j=1}^{a_0-1}\frac{X^{-j(k-a_1)}}{X^{j}-1}\biggr).\label{long1049:eq:B-explicit}
\end{align}
```
Put
``` math
\begin{equation}
\label{long1049:eq:cyclotomic-products}
 D_N(X)=\prod_{l=1}^{N}\Phi_l(X),\qquad
 \nu_{n,l}=\omega(n/l),\qquad
 \Omega_n(X)=\prod_{l=2}^{N}\Phi_l(X)^{\nu_{n,l}},
\end{equation}
```
with $`\Phi_l`$ the $`l`$th cyclotomic polynomial; by Lemma <a href="#long1049:res:omega-indicator" data-reference-type="ref" data-reference="long1049:res:omega-indicator">1</a> every $`\nu_{n,l}`$ is $`0`$ or $`1`$, and $`\nu_{n,l}=0`$ for $`l>15n`$ because the intervals all begin at or above $`1/14`$.

Zudilin’s Lemma 7 \[zudilin2004, p. 161, (23)\] applies at the parameters above: the tuple is $`c=n\cdot(13,14,12,14,15,13)`$ with maximum $`m(c)=15n`$ and difference $`s(c)=n>0`$, and the source’s (14) holds because $`12n+1\le14n+1`$ and $`26n+2\le27n+2\le28n+2`$. Its conclusion is the inclusion
``` math
\begin{equation}
\label{long1049:eq:integer-polynomial-pair}
 U_n:=X^{-M_n}\frac{D_N}{\Omega_n}A_n\in\mathbb{Z}[X],\qquad
 V_n:=X^{-M_n}\frac{D_N}{\Omega_n}B_n\in\mathbb{Z}[X].
\end{equation}
```
Two points about that citation matter. First, the conclusion used is the one in $`\mathbb{Z}[X]`$, not integrality at integer arguments: an integer-valued polynomial such as $`X(X-1)/2`$ shows that the two statements differ. The source’s proof supplies the polynomial form. Its Lemma 4 clears the two rational coefficients separately by Gaussian-binomial identities in $`\mathbb{Z}[X]`$, its Lemma 5 is Heine’s transform in the parameter $`q`$, and Lemma 7 removes the cyclotomic factors by polynomial divisibility, $`\Omega_n`$ being monic. All three precede the source’s evaluation at an integer $`p`$ in its (24), and all three remain valid with an indeterminate. Second, the pair extracted from the source’s module inclusion is unique, because $`F`$ is not a rational function of $`X`$: as $`h\downarrow0`$, splitting the original Lambert sum $`F(e^h)=\sum_{m\ge1}(e^{hm}-1)^{-1}`$ at $`L=\lfloor1/h\rfloor`$ gives an initial sum $`h^{-1}\sum_{m\le L}m^{-1}+O(L)`$, since $`y^{-1}-1\le(e^y-1)^{-1}\le y^{-1}`$ for $`0<y\le1`$. The remaining sum is at most $`e^{-h(L+1)}/((1-e^{-1})(1-e^{-h}))=O(h^{-1})`$. Hence $`F(e^h)=h^{-1}\log(1/h)+O(h^{-1})`$, so $`(X-1)F(X)\to\infty`$ and $`(X-1)^{2}F(X)\to0`$ as $`X\downarrow1`$, which no rational function does. Hence the coefficients of $`F`$ and of $`1`$ in an identity over $`\mathbb{Q}(X)`$ are determined, and <a href="#long1049:eq:integer-polynomial-pair" data-reference-type="eqref" data-reference="long1049:eq:integer-polynomial-pair">[long1049:eq:integer-polynomial-pair]</a> identifies them. This is a statement about $`F`$ as a function and says nothing about any individual value.

<a id="long1049:sec:degrees"></a>

## Exact degrees

Let $`d_{n,k}=\deg\bigl(c_{n,k}(X)X^{a_0k}\bigr)`$. The Gaussian-binomial degree formula gives
``` math
d_{n,k}=e_{n,k}+a_0k+(a_1-1)(k-a_1)+(\beta_n-k-1)(k-a_2)
 =\frac{-k^{2}+80kn+3k-340n^{2}-26n}{2},
```
``` math
d_{n,k+1}-d_{n,k}=40n+1-k>0\qquad(a_2\le k\le\beta_n-2),
```
the inequality because $`k\le\beta_n-2=27n`$ and $`27n<40n+1`$. The summand of top degree is therefore the one at $`k=\beta_n-1`$ alone, no cancellation occurs there, and
``` math
\begin{equation}
\label{long1049:eq:exact-degree}
 \begin{gathered}
 K_n:=\deg A_n=d_{n,\beta_n-1}=\frac{1091n^{2}+81n+2}{2},
 \\
 W_n:=\deg U_n=K_n-M_n+\sum_{l\le N}\varphi(l)-\sum_{2\le l\le N}\nu_{n,l}\varphi(l),
\end{gathered}
\end{equation}
```
the second equality because $`\deg D_N=\sum_{l\le N}\varphi(l)`$ and $`\deg\Omega_n=\sum_{2\le l\le N}\nu_{n,l}\varphi(l)`$, and because $`U_n`$ is a polynomial by <a href="#long1049:eq:integer-polynomial-pair" data-reference-type="eqref" data-reference="long1049:eq:integer-polynomial-pair">[long1049:eq:integer-polynomial-pair]</a>, so subtracting $`M_n`$ from the degree of $`D_NA_n/\Omega_n`$ is legitimate. In particular $`U_n\ne0`$.

The three integer identities in this step are checked by the Lean kernel: $`2M_n`$ against the source’s (16) is [one declaration](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseContour.lean#L317), the degree step $`d_{n,k+1}-d_{n,k}=40n+1-k`$ is [a second](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseContour.lean#L337), its positivity on the whole range $`a_2\le k\le\beta_n-2`$ is [a third](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseContour.lean#L350), and the top value $`2K_n=1091n^{2}+81n+2`$ is [a fourth](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseContour.lean#L344). They decide the arithmetic of this step and no analytic step anywhere in the note.

For the second coefficient, fix $`n`$ and let $`x\to\infty`$. Every factor in <a href="#long1049:eq:positive-source-form" data-reference-type="eqref" data-reference="long1049:eq:positive-source-form">[long1049:eq:positive-source-form]</a> tends to $`1`$ and the geometric factor $`q^{a_0t}`$ makes the sum converge, so $`H_n(x)=O(1)`$, while $`F(x)=\sum_m\tau(m)x^{-m}=O(x^{-1})`$. From $`B_n=A_nF-H_n`$ and $`\deg A_n=K_n`$ it follows that $`B_n(x)=O(x^{K_n-1})`$; multiplying by $`x^{-M_n}D_N(x)/\Omega_n(x)`$ and using integrality <a href="#long1049:eq:integer-polynomial-pair" data-reference-type="eqref" data-reference="long1049:eq:integer-polynomial-pair">[long1049:eq:integer-polynomial-pair]</a> gives
``` math
\begin{equation}
\label{long1049:eq:V-degree}
 \deg V_n\le W_n-1 .
\end{equation}
```
One common homogenising width $`W_n`$ therefore serves both coefficients.

<a id="long1049:sec:cyclotomic-limit"></a>

## The cyclotomic limit

Write $`\Sigma_n=\sum_{2\le l\le N}\nu_{n,l}\varphi(l)`$. The elementary summatory estimate is $`\sum_{l\le y}\varphi(l)=3\pi^{-2}y^{2}+O(y\log(2y))`$. Fix one demi-interval $`[u,v)`$ of Lemma <a href="#long1049:res:omega-indicator" data-reference-type="ref" data-reference="long1049:res:omega-indicator">1</a>. The condition $`\{n/l\}\in[u,v)`$ holds exactly on the blocks
``` math
\frac{n}{k+v}<l\le\frac{n}{k+u},\qquad k=0,1,2,\dots,
```
so the summatory estimate gives, for each fixed $`k`$, $`n^{-2}\sum_{l\text{ in block }k}\varphi(l)\to3\pi^{-2}\bigl((k+u)^{-2}-(k+v)^{-2}\bigr)`$. The blocks with $`k\ge L`$ consist of integers $`l\le n/(L+u)`$, and $`\varphi(l)\le l`$, so their total is at most $`\tfrac12(n/(L+u))^{2}+O(n)`$ and their normalised contribution is $`O(L^{-2})`$ uniformly in $`n`$. Taking $`n\to\infty`$ first and then $`L\to\infty`$ therefore justifies the infinite block sum, and summing the thirteen demi-intervals gives $`n^{-2}\Sigma_n\to3J/\pi^{2}`$. With $`\sum_{l\le15n}\varphi(l)=3\pi^{-2}225n^{2}+O(n\log n)`$, equation <a href="#long1049:eq:exact-degree" data-reference-type="eqref" data-reference="long1049:eq:exact-degree">[long1049:eq:exact-degree]</a> yields
``` math
\begin{equation}
\label{long1049:eq:degree-limits}
 \frac{K_n}{n^{2}}\to C_1,
 \qquad
 \frac{K_n-W_n}{n^{2}}=\frac{M_n-\sum_{l\le N}\varphi(l)+\Sigma_n}{n^{2}}
 \to266-\frac{3}{\pi^{2}}(225-J)=C_0,
\end{equation}
```
and hence $`W_n/n^{2}\to C_1-C_0`$. This limit replaces Lemmas 1 and 2 of the source, which are consequently not part of the citation set.

For the Archimedean side, fix a real $`x>1`$. From $`\log\Phi_l(x)-\varphi(l)\log x=\sum_{d\mid l}\mu_{\mathrm{Mob}}(l/d)\log(1-x^{-d})`$, with $`\mu_{\mathrm{Mob}}`$ the Möbius function, each summand has absolute value at most $`-\log(1-x^{-1})`$, and $`\sum_{l\le N}\tau(l)=O(N\log(2N))`$. Since $`\nu_{n,l}\in\{0,1\}`$,
``` math
\begin{equation}
\label{long1049:eq:cyclotomic-size}
 \log\frac{D_N(x)}{\Omega_n(x)}
 =\Bigl(\sum_{l\le N}\varphi(l)-\Sigma_n\Bigr)\log x+O_x\bigl(N\log(2N)\bigr),
\end{equation}
```
whose error term is $`O_x(n\log n)=o(n^{2})`$. By <a href="#long1049:eq:exact-degree" data-reference-type="eqref" data-reference="long1049:eq:exact-degree">[long1049:eq:exact-degree]</a> the bracket equals $`W_n-K_n+M_n`$.

<a id="long1049:sec:integer-forms"></a>

## Positive integral forms and the contradiction

Fix the base $`x=a/b>1`$ and write $`P_q=(q;q)_\infty>0`$. Each of the four finite $`q`$-Pochhammer products in <a href="#long1049:eq:positive-source-form" data-reference-type="eqref" data-reference="long1049:eq:positive-source-form">[long1049:eq:positive-source-form]</a> is a product of factors $`1-q^{j}`$ with $`j\ge1`$, hence lies in $`[P_q,1]`$, so each of the two ratios lies in $`[P_q,P_q^{-1}]`$, every summand is positive, and
``` math
P_q^{2}\le H_n(x)\le\frac{P_q^{-2}}{1-q^{a_0}}\le\frac{P_q^{-2}}{1-q},
```
whence $`H_n(x)>0`$ and $`\log H_n(x)=O_x(1)`$ uniformly in $`n`$. Cyclotomic polynomials are positive on $`(1,\infty)`$, so by <a href="#long1049:eq:integer-polynomial-pair" data-reference-type="eqref" data-reference="long1049:eq:integer-polynomial-pair">[long1049:eq:integer-polynomial-pair]</a>
``` math
\Lambda_n(x):=U_n(x)F(x)-V_n(x)=x^{-M_n}\frac{D_N(x)}{\Omega_n(x)}H_n(x)>0 .
```
By <a href="#long1049:eq:exact-degree" data-reference-type="eqref" data-reference="long1049:eq:exact-degree">[long1049:eq:exact-degree]</a> and <a href="#long1049:eq:V-degree" data-reference-type="eqref" data-reference="long1049:eq:V-degree">[long1049:eq:V-degree]</a> both polynomial degrees are at most $`W_n`$, so
``` math
\widehat U_n=b^{W_n}U_n(a/b),\qquad \widehat V_n=b^{W_n}V_n(a/b)
```
are integers, and $`\widehat\Lambda_n:=b^{W_n}\Lambda_n(a/b)
=\widehat U_nF(a/b)-\widehat V_n`$ is positive and lies in $`\mathbb{Z}F(a/b)+\mathbb{Z}`$. This is the only non-Archimedean step, and it is where the denominator is paid for. Combining the size estimates,
``` math
\begin{aligned}
 \log\widehat\Lambda_n
 &=W_n\log b-M_n\log x+\Bigl(\sum_{l\le N}\varphi(l)-\Sigma_n\Bigr)\log x+O_x(n\log n)\\
 &=K_n\log b-(K_n-W_n)\log a+o(n^{2}),
\end{aligned}
```
the second equality by $`\log x=\log a-\log b`$ and <a href="#long1049:eq:exact-degree" data-reference-type="eqref" data-reference="long1049:eq:exact-degree">[long1049:eq:exact-degree]</a>. With <a href="#long1049:eq:degree-limits" data-reference-type="eqref" data-reference="long1049:eq:degree-limits">[long1049:eq:degree-limits]</a> this proves
``` math
\begin{equation}
\label{long1049:eq:final-limit}
 \lim_{n\to\infty}\frac{\log\widehat\Lambda_n}{n^{2}}=C_1\log b-C_0\log a .
\end{equation}
```

<div class="proof">

*Proof of Theorem <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a>.* The hypothesis $`\log b/\log a<\theta^{*}=C_0/C_1`$ makes the right side of <a href="#long1049:eq:final-limit" data-reference-type="eqref" data-reference="long1049:eq:final-limit">[long1049:eq:final-limit]</a> negative, so $`\widehat\Lambda_n>0`$ and $`\widehat\Lambda_n\to0`$. Suppose $`F(a/b)=P/Q`$ with integers $`P`$ and $`Q\ge1`$. Then $`Q\widehat\Lambda_n=P\widehat U_n-Q\widehat V_n`$ is a positive integer for every $`n`$ and tends to $`0`$, which is impossible. ◻

</div>

Above the threshold <a href="#long1049:eq:final-limit" data-reference-type="eqref" data-reference="long1049:eq:final-limit">[long1049:eq:final-limit]</a> says that these same homogenised forms grow like $`e^{cn^{2}}`$ with $`c>0`$, and at equality the limit decides nothing. Both statements are about the displayed family.

The hypothesis $`b\ge1`$ admits $`b=1`$, where the statement reduces to the known integer-base theorem. Coprimality is a restriction on the pairs treated and is used nowhere in the argument. Negative bases are excluded, because Step 4 is a positivity argument.

<div id="long1049:res:31over4" class="theorem">

**Theorem 3** (the first base beyond the published region). *$`F(31/4)`$ is irrational, and so is $`F\bigl((31/4)^{r}\bigr)`$ for every integer $`r\ge1`$. Here
``` math
\frac{\log4}{\log31}=0.4036981731641997\ldots<\frac{81}{200}<\theta^{*},
```
while $`4^{\mu}=30.483515\ldots<31<4^{\mu_{\mathrm{BV}}}=32.369642\ldots`$ with $`\mu_{\mathrm{BV}}=2\pi^{2}/(\pi^{2}-2)=2.508284761994\ldots`$, so $`31/4`$ lies outside the region $`\log b/\log a<1/2-1/\pi^{2}=0.3986788163576622\ldots`$ of \[bv1994, Thm. 2, p. 177\] and inside the region of Theorem <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a>.*

</div>

<div class="proof">

*Proof.* The comparison $`\log4/\log31<81/200`$ is the integer certificate $`4^{200}<31^{81}`$, checked as [the power certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L26), and the membership it yields is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L45); the ratio $`\log b/\log a`$ is invariant under $`(a,b)\mapsto(a^{r},b^{r})`$, which gives the [power family](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L59), and $`(31^{r},4^{r})`$ are coprime. The exclusion from the earlier region is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L91). That exclusion also has a two-line rational certificate: $`31^{2}<4^{5}`$ gives $`\log4/\log31>2/5`$, and $`\pi^{2}<10`$ gives $`1/2-1/\pi^{2}<2/5`$, so
``` math
\frac12-\frac1{\pi^{2}}<\frac25<\frac{\log4}{\log31}<\frac{81}{200}<\theta^{*}.
```
The remaining comparison $`81/200<\theta^{*}`$ is proved in Section <a href="#long1049:sec:regionbracket" data-reference-type="ref" data-reference="long1049:sec:regionbracket">2.5</a>. Theorem <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a> then applies. ◻

</div>

<a id="long1049:sec:regionbracket"></a>

## The rational bracket around $`\theta^{*}`$

The constant $`\theta^{*}`$ is defined by a trigamma series, so a decidable membership test needs explicit rational bounds on it. Both are finite rational arithmetic, and neither uses a decimal expansion.

For the lower bound, keep only the $`k=0`$ term of each of the thirteen differences $`\psi_1(u_i)-\psi_1(v_i)`$. All later terms are positive, so
``` math
J\ \ge\ \sum_{i=1}^{13}\Bigl(\frac1{u_i^{2}}-\frac1{v_i^{2}}\Bigr)
  =\frac{2015640690251}{25971865920}
  >\frac{776}{10}.
```
Since $`\pi>157/50`$ and $`225-J<225`$,
``` math
C_0>266-\frac{3\,(225-776/10)}{(157/50)^{2}}=\frac{5451134}{24649}
 >\frac{88371}{400}=\frac{81}{200}\,C_1,
```
so $`81/200<\theta^{*}`$. For the upper bound the thirteen demi-intervals are disjoint and ordered and $`\psi_1`$ is positive and decreasing, so the sum telescopes below its first term:
``` math
J<\psi_1(1/14)=196+\sum_{k\ge1}\frac1{(k+1/14)^{2}}<196+\frac{\pi^{2}}6<198<225,
```
whence $`C_0<266`$ and $`\theta^{*}<532/1091<1/2`$. So
``` math
\frac{81}{200}<\theta^{*}<\frac12 .
```

Both bounds, the definitions of $`C_0`$, $`C_1`$ and $`\theta^{*}`$ from the trigamma series, the membership of $`31/4`$ and of every power of it, and the exclusion of $`3/2`$ are checked by the Lean kernel in the module `RationalBaseContour`, which the library root imports at the pinned source revision 92b88dc1bbe0. The lower bound on $`J`$ is [one declaration](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseContour.lean#L159), the rational bound on $`C_0`$ is [a second](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseContour.lean#L180), the comparison $`81/200<\theta^{*}`$ is [a third](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseContour.lean#L201), the bound $`\theta^{*}<1/2`$ is [a fourth](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseContour.lean#L251), the membership of $`31/4`$ and of its powers are [a fifth](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseContour.lean#L266) and [a sixth](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseContour.lean#L279), and the exclusion of $`3/2`$ is [a seventh](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseContour.lean#L296). Each is a finite comparison against the defined constant; none of them is any part of the analytic argument of Theorem <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a>. A finite-precision evaluation of the trigamma series with the integral tail bound over its first thousand terms gives the sharper enclosure $`0.4056830211<\theta^{*}<0.4056830214`$; that enclosure is a numerical receipt and is not kernel-checked.

<a id="evidence-attribution-and-the-remaining-obligation"></a>

## Evidence, attribution and the remaining obligation

<a id="evidence-decomposition."></a>

#### Evidence decomposition.

Theorems <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a> and <a href="#long1049:res:31over4" data-reference-type="ref" data-reference="long1049:res:31over4">3</a> are ordinary proofs. Their citation set is Zudilin’s Lemma 7 in its polynomial reading, together with the inputs of that lemma’s own proof, namely his Lemma 3, the exponent $`M(a;b)`$ of (16) proved by his Lemma 4, Heine’s transform as his Lemma 5, and the identity (9)–(11) \[zudilin2004\]. Everything else above is proved here: the nonrationality of $`F`$ as a function, the transfer of Lemma 7 to explicit integer polynomials, the exact degree computation, the degree bound on $`V_n`$, positivity, the Archimedean size estimate, and the limit $`(K_n-W_n)/n^{2}\to C_0`$. That last limit is the content of the source’s Lemmas 1 and 2, and the elementary proof of Section <a href="#long1049:sec:cyclotomic-limit" data-reference-type="ref" data-reference="long1049:sec:cyclotomic-limit">2.3</a> replaces them, so they are not part of the citation set. Kernel-checked are the finite height comparisons of Theorem <a href="#long1049:res:31over4" data-reference-type="ref" data-reference="long1049:res:31over4">3</a>, the rational bracket of Section <a href="#long1049:sec:regionbracket" data-reference-type="ref" data-reference="long1049:sec:regionbracket">2.5</a>, and the four integer identities of the degree step in Section <a href="#long1049:sec:degrees" data-reference-type="ref" data-reference="long1049:sec:degrees">2.2</a>. Checked by exact computation are the reconstructions of $`U_n`$ and $`V_n`$ for $`n\le4`$, together with the numerical values of $`J`$, $`C_0`$ and $`\theta^{*}`$; those are computational receipts, and the reconstruction is described in Section <a href="#long1049:sec:receipts" data-reference-type="ref" data-reference="long1049:sec:receipts">2.7</a>. No part of Theorem <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a> is a Lean theorem.

<a id="attribution."></a>

#### Attribution.

Bundschuh and Väänänen proved the irrationality of this value on the region $`\log b/\log a<1/2-1/\pi^{2}=0.3986788163576622\ldots`$ \[bv1994, Thm. 2, p. 177; hypotheses pp. 175–176\], and every base of Theorem <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a> with $`b\le3`$ is already theirs. Their printed hypothesis for $`\alpha=-1`$ is $`\lambda<(1/2+1/\pi^{2})^{-1}`$ with $`\lambda=\log h(q)/\log|q|`$; at $`q=a/b`$ this reads $`\log a/\log(a/b)<(1/2+1/\pi^{2})^{-1}`$, which is the displayed inequality. Duverney proved an independent and strictly smaller region for the same series \[duverney1996, Théorème 2, p. 174\]. Zudilin announced a rational-base extension of his generalized $`q`$-logarithm results under an assumption $`\log|r|>c\log|s|`$ for a computable $`c>0`$, without computing a value \[zudilin2016\]. Zudilin’s 2004 paper supplies the forms and the exponent $`\mu`$ under the standing hypothesis $`p=1/q\in\mathbb{Z}\mathbin{\backslash}\{0,\pm1\}`$, and it states no rational-base result \[zudilin2004, Sec. 2, p. 154; Thm. 1\]. The contribution here is the rational specialisation of the 2004 forms, with the denominator accounting and the limit passage carried out in full, which identifies the printed $`\mu`$ as an admissible $`c`$ for $`F`$ itself, together with the region that constant defines and its first new base.

<a id="where-the-earlier-criterion-stops."></a>

#### Where the earlier criterion stops.

Both regions are cut out by the same quantity. The published cutoff $`1/2-1/\pi^{2}`$ of \[bv1994, Thm. 2, p. 177\] is the reciprocal of $`\mu_{\mathrm{BV}}=2\pi^{2}/(\pi^{2}-2)`$, the constant Van Assche later recovered as an integer-base irrationality-exponent bound for $`F(p)`$ \[vanassche2001, Thm. 1, p. 10\], and the cutoff $`\theta^{*}`$ of Theorem <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a> is the reciprocal of the smaller integer-base bound $`\mu=C_1/C_0`$ printed at \[zudilin2004, p. 162\]. The remark following Theorem <a href="#long1049:res:archcap" data-reference-type="ref" data-reference="long1049:res:archcap">4</a> records that reciprocal relation for every family satisfying the hypotheses of that theorem, and Zudilin’s family satisfies them with decay exponent $`\sigma=C_0`$ and exact degree limit $`d=C_1-C_0`$. The step taken here is the homogenisation of Step 3 in the proof of Theorem <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a>, applied to the forms that carry the smaller exponent. It substitutes one integer-base exponent bound for another, and it leaves the analytic content of each bound where its own source proves it. The bases gained are exactly the strip $`s^{\mu}<r\le s^{\mu_{\mathrm{BV}}}`$, which is empty for $`s=2`$ and $`s=3`$ and is first occupied at $`s=4`$ by the single numerator $`31`$. The kernel-checked declarations of Theorem <a href="#long1049:res:31over4" data-reference-type="ref" data-reference="long1049:res:31over4">3</a> and of Section <a href="#long1049:sec:regionbracket" data-reference-type="ref" data-reference="long1049:sec:regionbracket">2.5</a> decide the integer comparisons and the rational bracket that place a base inside or outside each region. They decide no step of either analytic argument, and they improve neither exponent bound.

<a id="the-exact-remaining-obligation."></a>

#### The exact remaining obligation.

Theorem <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a> settles no base with $`\log b/\log a\ge\theta^{*}`$, and in particular settles nothing at $`3/2`$, whose parameter is $`\log2/\log3=0.6309297535714574\ldots`$, a gap of $`0.2252467\ldots`$ above $`\theta^{*}`$. Enlarging the region by this proof requires a smaller integer-base exponent bound carried by forms with the $`\mathbb{Z}[p]`$-integrality of Lemma 7 type and with base-uniform size; a bound $`2.4234`$ would give $`0.4126`$ and would admit $`29/4`$. Formalising the theorem requires Lemma 7 and its inputs, the identity (9)–(11), and the steps of Sections <a href="#long1049:sec:source-forms" data-reference-type="ref" data-reference="long1049:sec:source-forms">2.1</a>–<a href="#long1049:sec:integer-forms" data-reference-type="ref" data-reference="long1049:sec:integer-forms">2.4</a>. Of these only the integer degree bookkeeping is formalised here.

<div id="long1049:res:archcap" class="theorem">

**Theorem 4** (degree-budget cap on the mechanism). *Let $`(U_n,V_n)\in\mathbb{Z}[x]^{2}`$ be a sequence such that, for constants $`\sigma,\delta>0`$ and $`h\ge0`$ independent of $`n`$ and of the base,*

1.  *$`\Lambda_n(x):=U_n(x)F(x)-V_n(x)\ne0`$ for every real $`x>1`$;*

2.  *$`\deg U_n,\deg V_n\le\delta n^{2}(1+o(1))`$;*

3.  *$`\log\max\bigl(H(U_n),H(V_n)\bigr)\le hn^{2}(1+o(1))`$, where $`H(P)`$ is the largest absolute value of a coefficient of $`P`$;*

4.  *$`\log|\Lambda_n(x)|=-\sigma n^{2}\log x\,(1+o(1))`$ for every real $`x>1`$.*

*Put $`d_n:=\max(\deg U_n,\deg V_n)`$. Then $`\sigma\le\delta`$, and for every fixed rational base $`a/b>1`$,
``` math
\limsup_{n\to\infty}n^{-2}\log\bigl|b^{d_n}\Lambda_n(a/b)\bigr|
 \le\delta\log b-\sigma\log(a/b).
```
Consequently the homogenised forms tend to zero whenever $`\log b/\log a<\sigma/(\sigma+\delta)`$, a sufficient region whose cutoff is at most $`1/2`$. If the actual degrees satisfy $`d_n/n^{2}\to d`$, then $`d\ge\sigma`$ and the limit exists and equals $`d\log b-\sigma\log(a/b)`$; in that case the forms tend to zero below $`\log b/\log a=\sigma/(\sigma+d)`$ and their absolute values tend to infinity above it, so the exact-degree case has no decaying homogenised forms at $`3/2`$.*

</div>

<div class="proof">

*Proof.* The displayed inequality is the identity $`n^{-2}\log|b^{d_n}\Lambda_n(a/b)|=(d_n/n^{2})\log b-\sigma\log(a/b)+o(1)`$ together with hypothesis (2); the degree bound is what makes $`b^{d_n}U_n(a/b)`$ and $`b^{d_n}V_n(a/b)`$ integers.

For $`\sigma\le\delta`$, fix an integer $`p\ge2`$, write $`\xi=F(p)`$, $`\alpha=h+\delta\log p`$ and $`\beta=\sigma\log p`$, and set $`\varepsilon_n=\Lambda_n(p)`$. Hypotheses (2) and (3) give the upper bound $`|U_n(p)|\le e^{(\alpha+o(1))n^{2}}`$, an inequality and not an equality: a degree and height bound leaves cancellation at $`p`$ possible. Hypothesis (4) gives $`\log|\varepsilon_n|=-\beta n^{2}(1+o(1))`$ on both sides, and hypothesis (1) gives $`\varepsilon_n\ne0`$. Since $`U_n(p)\xi-V_n(p)=\varepsilon_n`$ is a nonzero real tending to $`0`$ while $`U_n(p)`$ and $`V_n(p)`$ are integers, $`\xi`$ is irrational; in particular $`U_n(p)\ne0`$ for all large $`n`$, since otherwise $`\varepsilon_n=-V_n(p)`$ would be a nonzero integer tending to $`0`$.

Let $`P/Q`$ be rational with $`Q`$ large, and let $`n`$ be least with $`|\varepsilon_n|<1/(2Q)`$. Minimality and the two-sided asymptotic give $`n^{2}\le(1+o(1))\log Q/\beta`$, hence
``` math
|\varepsilon_n|\ge Q^{-1-o(1)},\qquad |U_n(p)|\le Q^{\alpha/\beta+o(1)} .
```
If $`U_n(p)P-V_n(p)Q\ne0`$, then from $`U_n(p)P-V_n(p)Q=Q\varepsilon_n-U_n(p)(Q\xi-P)`$ and $`|Q\varepsilon_n|<1/2`$ one gets $`|U_n(p)|\,|Q\xi-P|>1/2`$, so $`|\xi-P/Q|>1/\bigl(2Q|U_n(p)|\bigr)`$. If instead $`P/Q=V_n(p)/U_n(p)`$, then $`|\xi-P/Q|=|\varepsilon_n|/|U_n(p)|`$. In both cases $`|\xi-P/Q|\ge Q^{-1-\alpha/\beta-o(1)}`$, so the irrationality exponent satisfies $`\mu(\xi)\le1+\alpha/\beta`$. Dirichlet’s theorem gives $`\mu(\xi)\ge2`$ for the irrational $`\xi`$, hence $`\beta\le\alpha`$, that is $`(\sigma-\delta)\log p\le h`$. The three constants do not depend on $`p`$, so letting $`p\to\infty`$ gives $`\sigma\le\delta`$. The exact-degree statement is the same argument with $`d+\varepsilon`$ in place of $`\delta`$ for every $`\varepsilon>0`$. ◻

</div>

<div id="long1049:cor:no-decay-below-square" class="corollary">

**Corollary 5** (Undivided forms below the square boundary). *Under the hypotheses of Theorem <a href="#long1049:res:archcap" data-reference-type="ref" data-reference="long1049:res:archcap">4</a>, for positive integers $`a,b`$ with $`b<a<b^2`$, the undivided forms $`b^{d_n}\Lambda_n(a/b)`$ do not tend to zero. No limit of $`d_n/n^2`$ is assumed.*

</div>

<div class="proof">

*Proof.* Write $`x=a/b`$ and suppose $`C_n=b^{d_n}\Lambda_n(x)\to0`$. Eventual nonvanishing gives $`\log|C_n|=d_n\log b+\log|\Lambda_n(x)|`$ for all sufficiently large $`n`$. Also $`|C_n|\le1`$ eventually. The lower side of the remainder asymptotic therefore implies
``` math
d_n\log b\le-\log|\Lambda_n(x)|
       =\sigma\log x\,n^2+o(n^2).
```
Set $`c=\sigma\log x/\log b`$. Since $`1<x<b`$, we have $`0<c<\sigma`$, and the displayed inequality gives $`d_n\le(c+\varepsilon)n^2`$ eventually for each $`\varepsilon>0`$. The same family thus satisfies the cap hypotheses with degree upper rate $`c`$, its original height bound, and its original nonvanishing and remainder asymptotics at every real base greater than one. The cap yields $`\sigma\le c`$, a contradiction. ◻

</div>

The no-decay conclusion is [kernel-checked in Lean](https://github.com/wcook04/plectis-erdos/blob/3be82b1a7340284aea72e9a5c8493cb020843921/ErdosProblems/Erdos1049/PaperNoDecayR9.lean#L69) under the stated all-base hypotheses.

This strengthens the failure of a sufficient-cutoff test to an exclusion of decay under the stated all-base hypotheses. It does not supply an actual-degree limit or assert divergence. If $`d_n/n^2\to d`$, the separate exact-degree result gives the stronger conclusion $`|b^{d_n}\Lambda_n(a/b)|\to\infty`$ in the same strict region. Equality $`a=b^2`$ remains unclassified. The corollary concerns the undivided forms; it does not exclude base-dependent content division or other irrationality methods outside its hypotheses.

For the maximum-coefficient height convention, the passage to the $`\ell^1`$ norm uses $`\|P\|_1\le(\deg P+1)H(P)`$. The original quadratic degree bound makes the extra logarithm $`o(n^2)`$. This established height bound remains available when the degree rate is replaced by $`c`$.

Hypothesis (3) is essential and was absent from an earlier form of this statement: a bound on $`\deg U_n`$ alone controls $`|U_n(p)|`$ only through $`H(U_n)`$. At the boundary $`\log b/\log a=\sigma/(\sigma+d)`$ the normalised logarithm is zero and these hypotheses decide neither behaviour. Theorem <a href="#long1049:res:archcap" data-reference-type="ref" data-reference="long1049:res:archcap">4</a> constrains families satisfying its hypotheses and does not exclude every possible Padé construction.

For the family of Section <a href="#long1049:sec:source-forms" data-reference-type="ref" data-reference="long1049:sec:source-forms">2.1</a> the fourth hypothesis is the size estimate proved there and the second is <a href="#long1049:eq:exact-degree" data-reference-type="eqref" data-reference="long1049:eq:exact-degree">[long1049:eq:exact-degree]</a>. The third is proved next, so the cap applies to that family with no further assumption.

<div id="long1049:res:sourceheight" class="lemma">

**Lemma 6** (uniform coefficient height of the source forms). *There is a constant $`h`$ with $`\log\max\bigl(H(U_n),H(V_n)\bigr)\le hn^{2}`$ for every $`n\ge1`$, where $`U_n`$ and $`V_n`$ are the polynomials of <a href="#long1049:eq:integer-polynomial-pair" data-reference-type="eqref" data-reference="long1049:eq:integer-polynomial-pair">[long1049:eq:integer-polynomial-pair]</a>.*

</div>

<div class="proof">

*Proof.* Write $`\|P\|`$ for the sum of the absolute values of the coefficients of $`P\in\mathbb{Z}[X]`$, so that $`H(P)\le\|P\|`$ and $`\|PQ\|\le\|P\|\,\|Q\|`$.

By Lemma <a href="#long1049:res:omega-indicator" data-reference-type="ref" data-reference="long1049:res:omega-indicator">1</a> every $`\nu_{n,l}`$ is $`0`$ or $`1`$, so $`D_N/\Omega_n=\prod_{l\in S}\Phi_l`$ over a subset $`S\subseteq\{1,\dots,N\}`$. Each $`\Phi_l`$ has Mahler measure $`1`$, and a polynomial of degree $`D`$ satisfies $`\|P\|\le2^{D}M(P)`$, so $`\|\Phi_l\|\le2^{\varphi(l)}`$ and
``` math
\Bigl\|\frac{D_N}{\Omega_n}\Bigr\|\le2^{\sum_{l\le N}\varphi(l)}\le2^{225n^{2}} .
```
For $`A_n`$, the Gaussian binomial $`\genfrac{[}{]}{0pt}{}{m}{r}_X`$ has nonnegative coefficients summing to $`\binom{m}{r}`$, so $`\|c_{n,k}\|\le\binom{k-1}{a_1-1}\binom{\beta_n-a_2-1}{\beta_n-k-1}\le2^{2\beta_n}`$ by <a href="#long1049:eq:c-explicit" data-reference-type="eqref" data-reference="long1049:eq:c-explicit">[long1049:eq:c-explicit]</a>, and summing the at most $`\beta_n`$ terms of <a href="#long1049:eq:A-explicit" data-reference-type="eqref" data-reference="long1049:eq:A-explicit">[long1049:eq:A-explicit]</a> gives $`\|A_n\|\le\beta_n2^{2\beta_n}`$. Hence $`\|U_n\|\le\|D_N/\Omega_n\|\,\|A_n\|\le e^{O(n^{2})}`$ and $`H(U_n)\le e^{O(n^{2})}`$.

For $`V_n`$, bound it on the circle $`|z|=2`$ and use Cauchy’s estimate $`H(V_n)\le\max_{|z|=2}|V_n(z)|`$, valid because $`\deg V_n\ge0`$ and each coefficient is $`|v_i|\le2^{-i}\max_{|z|=2}|V_n(z)|`$. On that circle $`|z^{l}-1|\ge2^{l}-1\ge1`$, so each of the at most $`\beta_n+a_0`$ inner terms of <a href="#long1049:eq:B-explicit" data-reference-type="eqref" data-reference="long1049:eq:B-explicit">[long1049:eq:B-explicit]</a> has modulus at most $`1`$; also $`|c_{n,k}(z)z^{a_0k}|\le\|c_{n,k}\|\,2^{K_n}`$ and $`|D_N(z)/\Omega_n(z)|\le\|D_N/\Omega_n\|\,2^{225n^{2}}\le e^{O(n^{2})}`$, while $`|z^{-M_n}|\le1`$. Multiplying the $`O(n)`$ bounds and using $`K_n=O(n^{2})`$ gives $`\max_{|z|=2}|V_n(z)|\le e^{O(n^{2})}`$, hence $`H(V_n)\le e^{O(n^{2})}`$. ◻

</div>

With Lemma <a href="#long1049:res:sourceheight" data-reference-type="ref" data-reference="long1049:res:sourceheight">6</a>, Zudilin’s family satisfies all four hypotheses of Theorem <a href="#long1049:res:archcap" data-reference-type="ref" data-reference="long1049:res:archcap">4</a>, with exact degree limit $`d=C_1-C_0`$ by <a href="#long1049:eq:degree-limits" data-reference-type="eqref" data-reference="long1049:eq:degree-limits">[long1049:eq:degree-limits]</a>, and decay exponent $`\sigma=C_0`$ because $`\log\Lambda_n(x)=-(K_n-W_n)\log x+o(n^{2})`$ for each fixed real $`x>1`$ by the size estimate of Section <a href="#long1049:sec:integer-forms" data-reference-type="ref" data-reference="long1049:sec:integer-forms">2.4</a>. For it $`\sigma/(\sigma+d)=\theta^{*}`$ and $`(\sigma+d)/\sigma=\mu`$: within this family the rational-base threshold is the reciprocal of the integer-base irrationality-exponent bound. Lemma <a href="#long1049:res:sourceheight" data-reference-type="ref" data-reference="long1049:res:sourceheight">6</a> is an ordinary proof and is not kernel-checked.

<a id="the-region-explicitly."></a>

#### The region, explicitly.

Among coprime $`a/b`$ with $`a\le60`$ the region of Theorem <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a> has $`137`$ members, of which $`78`$ are non-integral. The tightest members are $`53/5`$, at margin $`0.000313`$ below $`\theta^{*}`$, and $`31/4`$, at margin $`0.001985`$; the closest miss is $`52/5`$ at $`\theta=0.4073243836\ldots`$, short by $`0.001641`$. The bases new relative to \[bv1994\] are those in the strip $`s^{\mu}<r\le s^{\mu_{\mathrm{BV}}}`$, which is empty for $`s=2`$ and $`s=3`$, is $`\{31\}`$ for $`s=4`$, and is $`\{53,54,56\}`$ for $`s=5`$. The strip is infinite: its width $`s^{\mu_{\mathrm{BV}}}-s^{\mu}`$ eventually exceeds $`s`$, so for every large enough denominator it contains an integer congruent to $`1`$ modulo $`s`$. Hence $`31/4`$ is the new base of least denominator and least numerator.

<a id="the-direction-is-optimal-in-its-box."></a>

#### The direction is optimal in its box.

Over the $`37{,}533`$ primitive directions on Zudilin’s cone with all entries at most $`30`$, the quantity $`\theta^{*}(\mathrm{dir})=C_0/C_1`$ computed from his (25) and (26) is maximised by $`(14,12,14;27)`$ and its group image $`(15,12,13;26)`$, both at $`0.4056830213840605\ldots`$; the next value is $`0.4056394327738419\ldots`$, at $`(16,13,14;28)`$. Larger boxes were not scanned, so this is a search result over that box and not a proof of optimality over the whole cone. The enumeration ranges over integer tuples $`(\alpha_0,\alpha_1,\alpha_2;\beta)`$ with $`1\le\alpha_j\le30`$, $`1\le\beta\le30`$, satisfying the cone conditions of \[zudilin2004, Sec. 5\] and taken up to the common factor of the four entries; the objective is the ratio $`C_0/C_1`$ of the source’s (25) and (26), evaluated by the same thirteen-interval trigamma sum. The two maximising tuples are exchanged by the source’s permutation group, so they are one direction.

<a id="long1049:sec:receipts"></a>

## Finite receipts

Four finite computations support statements above. Each is exact rational or integer arithmetic except where a numerical enclosure is named; none of them proves a statement quantified over all indices, and none is kernel-checked.

The forms of Section <a href="#long1049:sec:source-forms" data-reference-type="ref" data-reference="long1049:sec:source-forms">2.1</a> were reconstructed as explicit elements of $`\mathbb{Z}[X]`$ from cyclotomic products, without rational-function arithmetic, for $`n\le4`$. At $`n=1,2,3`$ the reconstruction confirms $`\deg A_n=K_n`$ with $`K_n=587,2264,5032`$, that $`\Omega_n`$ divides both $`D_NA_n`$ and $`D_NB_n`$ with zero remainder, that $`X^{M_n}`$ divides both quotients, and that $`W_n=\deg U_n=333,1315,2944`$ with $`\deg V_n=W_n-1`$ and leading coefficients $`\pm1`$. It also confirms $`\sum_{l\le N}\varphi(l)=72,278,628`$ and $`\Sigma_n=25,94,219`$, hence $`(K_n-W_n)/n^{2}=254,949/4,232`$. The identity $`U_n(x)F(x)-V_n(x)=x^{-M_n}(D_N/\Omega_n)(x)H_n(x)`$ was then evaluated at $`x=31/4`$, $`3`$ and $`7/2`$ to relative accuracy below $`10^{-39}`$ at $`n=3`$, with $`\widehat\Lambda_n>0`$ at each, with $`b^{W_n}U_n(a/b)`$ an integer and $`b^{W_n-1}U_n(a/b)`$ not an integer at $`31/4`$ and $`7/2`$, and with $`H_n(x)`$ inside the bounds of Section <a href="#long1049:sec:integer-forms" data-reference-type="ref" data-reference="long1049:sec:integer-forms">2.4</a>.

The constant was evaluated independently of the source’s printed digits from $`\omega`$, the thirteen intervals of Lemma <a href="#long1049:res:omega-indicator" data-reference-type="ref" data-reference="long1049:res:omega-indicator">1</a> and the trigamma series at forty digits, giving $`J=77.94318447500909\ldots`$, $`C_0=221.30008816500502\ldots`$ and $`C_1/C_0=2.46497868357497\ldots`$, which agree with \[zudilin2004, p. 162\] to its printed precision.

The main term $`K_n\log b-(K_n-W_n)\log a`$ at $`31/4`$, computed from $`\sum_{l\le N}\varphi(l)`$ and $`\Sigma_n`$ alone, is negative from $`n=1`$ and its normalisation by $`n^{2}`$ runs $`-58.478,-10.280,-4.297,-3.863`$ at $`n=1,10,100,400`$ against the limit $`C_1\log4-C_0\log31=-3.718\ldots`$. The elementary bound on the convergence rate is $`O(\log^2(n+2)/n)`$. Indeed, summing the $`O(y\log(2y))`$ endpoint errors over the floor blocks with $`k\le n`$ gives $`O(n\log^2(n+2))`$; the remaining main-term tail is $`O(1)`$ since its summands are $`O(n^2/k^3)`$. The linear terms of $`M_n`$ add $`O(n)`$. The stronger rate $`O(1/n)`$ does not follow from these estimates. Only the limit enters Theorem <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a>.

The order and leading coefficient of $`V_N^{*}`$ were computed exactly for $`1\le N\le7`$, giving orders $`0,1,5,14,30,55,91`$ and coefficients $`1,6,108,4320,324000,40824000,8001504000`$.

<a id="long1049:sec:sharp"></a>

# The sharp $`41/65`$ certificate

The numerical obstruction at $`3/2`$ is controlled by one small exact calculation. Writing it out is useful because the upper and lower inequalities play different roles: the upper inequality proves every strict analytic threshold below, while the lower inequality establishes the sharp rational scale. Exact failure of the rank-$`41`$ selector count one row earlier uses the additional integer comparison $`2^{129}<3^{82}`$ below.

<div id="long1049:res:powerbracket" class="theorem">

**Theorem 7** (sharp power bracket). *One has
``` math
2^{64}<3^{41}<2^{65}.
```
Consequently
``` math
\frac{41}{65}<\frac{\log2}{\log3},
 \qquad
 \frac{\log3}{\log2}<\frac{65}{41}.
```*

</div>

<div class="proof">

*Proof.* Direct evaluation gives
``` math
\begin{aligned}
 2^{64}&=18446744073709551616,\\
 3^{41}&=36472996377170786403,\\
 2^{65}&=36893488147419103232.
 \end{aligned}
```
The logarithmic inequalities follow by taking logarithms and dividing by the positive numbers $`41\log3`$ and $`41\log2`$, respectively. ◻

</div>

The integer sides are checked as [the upper certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/AdelicHeightBridge.lean#L42) and [the sharp lower certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/AdelicHeightBridge.lean#L45).

The upper half is stronger than the earlier $`81/200`$ comparison in the direction needed at $`3/2`$. Combining it with the elementary bound $`1/2-1/\pi^2<2/5`$ gives the following exact deficits.

For $`\rho,\sigma\in\mathbb{R}`$, write
``` math
\Theta_{\mathrm{HP}}(\rho,\sigma)=
 \frac{(1+\rho^2)/2+\sigma-3\sigma^2/\pi^2}
 {(1+\rho)^2/2+\sigma(1+\rho)+(1+\rho^2)/2+\sigma}.
```

<div id="long1049:res:sharpgaps" class="corollary">

**Corollary 8** (height and Hankel deficits). *For every $`\rho,\sigma\in\mathbb{R}`$ with $`0\le\rho`$ and $`1+\rho\le\sigma`$,
``` math
\frac3{13}<\frac{\log2}{\log3}
   -\left(\frac12-\frac1{\pi^2}\right),
 \qquad
 \frac3{13}<\frac{\log2}{\log3}-\Theta_{\mathrm{HP}}(\rho,\sigma),
```
where $`\Theta_{\mathrm{HP}}`$ is the rectangular exponent threshold. Moreover
``` math
\frac{\log3/\log2-1}{3}<\frac8{41}.
```*

</div>

<div class="proof">

*Proof.* The first inequality follows from $`41/65-2/5=3/13`$, Theorem <a href="#long1049:res:powerbracket" data-reference-type="ref" data-reference="long1049:res:powerbracket">7</a>, and $`1/2-1/\pi^2<2/5`$. The rectangular threshold is no larger than the classical margin $`1/2-1/\pi^2`$, so the second follows. The final inequality is a direct rearrangement of $`\log3/\log2<65/41`$. ◻

</div>

The uniform rectangular bound and cubic charge bound are [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/AdelicHeightBridge.lean#L86) and [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/AdelicHeightBridge.lean#L97).

The next statement is the source-facing charge comparison. It does not prove the degree ceilings: those come from the scalar factor and the universally forced first-order southeast-border factor in the Zudilin model. It proves that even granting those ceilings, neither extraction reaches the required $`39/41`$ fraction of the raw charge.

<div id="long1049:res:chargeceilings" class="theorem">

**Theorem 9** (scalar and border charge no-go). *For every integer $`N>0`$,
``` math
41(N^3-N)<39(4N^3-3N^2).
```
For every integer $`N\ge2`$,
``` math
41(2N^3-N)<39(4N^3-3N^2).
```
Hence the same strict inequalities hold with the left side replaced by $`41E`$ whenever, respectively, $`E\le N^3-N`$ or $`E\le2N^3-N`$.*

</div>

<div class="proof">

*Proof.* After subtraction, the first inequality is
``` math
N(115N^2-117N+41)>0,
```
which holds for $`N>0`$. The second becomes
``` math
N(74N^2-117N+41)>0.
```
For $`N\ge2`$ the quadratic factor is positive and increasing. The assertions for $`E`$ follow by monotonicity. ◻

</div>

The application-facing downward-closed forms are [the scalar no-go](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/AdelicHeightBridge.lean#L123) and [the scalar-plus-border no-go](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/AdelicHeightBridge.lean#L153).

The formal source checks Theorem <a href="#long1049:res:powerbracket" data-reference-type="ref" data-reference="long1049:res:powerbracket">7</a>, Corollary <a href="#long1049:res:sharpgaps" data-reference-type="ref" data-reference="long1049:res:sharpgaps">8</a>, and Theorem <a href="#long1049:res:chargeceilings" data-reference-type="ref" data-reference="long1049:res:chargeceilings">9</a> as exact Lean propositions. Their role is exclusion: scalar content and the forced first-order border do not supply enough charge. Higher residual valuations, determinant cancellation, a different integral model, and irrationality of $`F(3/2)`$ remain open.

<a id="long1049:sec:hankel-order"></a>

## The sharp $`q`$-order of the normalised Hankel determinant

The charge comparison of Corollary <a href="#long1049:res:sharpgaps" data-reference-type="ref" data-reference="long1049:res:sharpgaps">8</a> is a statement about how much denominator the Hankel determinant can shed. How much it actually sheds is settled by the following exact order.

<div id="long1049:res:zudilin-sharp-qorder" class="theorem">

**Theorem 10** (sharp all-rank $`q`$-order and leading coefficient). *For every rank $`N`$, the normalised Hankel determinant $`V_N^{*}`$ of \[zudilin2016, Sec. 4\], evaluated at $`x=z=1`$, has
``` math
\operatorname{ord}_q V_N^{*}=\frac{N(N-1)(2N-1)}{6},
 \qquad
 \text{leading coefficient}\quad\frac{(N!)^{2}(N+1)!}{2^{N}} .
```*

</div>

The source proves the inequality $`\operatorname{ord}_q V_N^{*}\ge N(N-1)(2N-1)/6`$ and uses it as an upper bound on $`|V_N^{*}|`$ \[zudilin2016, Sec. 4\]. Equality is the statement that no further cancellation is available inside the determinant, so the hope of a hidden cubic decay there is closed.

<a id="the-row-identity."></a>

#### The row identity.

Work over $`A=\mathbb{Z}[[q]]`$. Let $`H(X)=1+\sum_{s\ge1}a_s(q)X^{s}`$ and put
``` math
W_m(t)=q^{(m+1)t}\prod_{r=1}^{m}H(q^{r}),
 \qquad
 D_j=\prod_{r=0}^{j-1}(I-q^{r}\mathcal N),
 \qquad
 E(m,j)=mj-\frac{j(j-1)}2,
```
where $`\mathcal N`$ is the backward shift $`(\mathcal Nf)_m=f_{m-1}`$ in the index $`m`$, so $`D_j`$ is the source’s backward-difference operator of \[zudilin2016, Sec. 4\]. Write $`\bar H=H\bmod q`$ and $`h_r=[X^{r}]\bar H(X)^{-1}`$, with $`h_r=0`$ for $`r<0`$ and $`h_0=1`$.

<div id="long1049:res:allrowinitial" class="lemma">

**Lemma 11** (all-depth initial monomial). *For $`m\ge j\ge0`$ one has $`D_jW_m(t)\in q^{E(m,j)}A`$ and
``` math
\bigl[q^{E(m,j)}\bigr]D_jW_m(t)=(-1)^{j}h_{j-t}.
```*

</div>

<div class="proof">

*Proof.* Define the following transition coefficients on states $`(e_u)_{u\ge0}`$. Powers $`\Phi^j`$ mean the finite-depth path sums, not endomorphisms of the algebraic direct sum: for fixed initial state $`t`$, endpoint $`u`$ and depth $`j`$, all visited states are at most $`\max(t,u+j)`$, so each such coefficient is a finite sum. Subsequent sums over endpoints are interpreted coefficientwise as justified below. The transition coefficients are
``` math
\Phi e_0=\sum_{s\ge1}a_se_{s-1},
 \qquad
 \Phi e_u=(q^{u}-1)e_{u-1}+q^{u}\sum_{s\ge1}a_se_{u+s-1}\quad(u>0).
```
A direct expansion gives $`W_m(u)-W_{m-1}(u)=q^{m}\sum_v(\Phi e_u)_vW_{m-1}(v)`$: both sides equal $`q^{mu}\prod_{r<m}H(q^{r})\bigl(q^{u}H(q^{m})-1\bigr)`$. Using $`r+E(m-1,r)=E(m,r)`$, induction on $`j`$ turns this into
``` math
\begin{equation}
\label{long1049:eq:state-expansion}
 D_jW_m(t)=q^{E(m,j)}\sum_u(\Phi^{j}e_t)_uW_{m-j}(u).
\end{equation}
```
The sum is locally finite: one transition lowers a state by at most one, so a depth-$`j`$ path ending at $`u`$ never visits a state above $`\max(t,u+j)`$, and $`\operatorname{ord}W_{m-j}(u)=(m-j+1)u`$, so only finitely many endpoints contribute to any fixed power of $`q`$.

Modulo $`q`$ the operator simplifies: $`\bar\Phi e_u=-e_{u-1}`$ for $`u>0`$, and $`\bar\Phi e_0=\sum_{s\ge1}a_s(0)e_{s-1}`$. Put $`c_{j,t}=(\bar\Phi^{j}e_t)_0`$. Then $`c_{j+1,t}=-c_{j,t-1}`$ for $`t>0`$ and $`c_{j+1,0}=\sum_{s=1}^{j+1}a_s(0)c_{j,s-1}`$, the sum terminating because a state above $`j`$ cannot reach $`0`$ in $`j`$ steps. Now $`c_{0,t}=\delta_{t,0}=h_{-t}`$, and if $`c_{j,t}=(-1)^{j}h_{j-t}`$ for all $`t`$ then $`c_{j+1,t}=(-1)^{j+1}h_{j+1-t}`$ for $`t>0`$ at once, while for $`t=0`$ the identity $`\bar H\bar H^{-1}=1`$ gives $`h_{j+1}=-\sum_{s\ge1}a_s(0)h_{j+1-s}`$ and hence $`c_{j+1,0}=(-1)^{j}\sum_{s\ge1}a_s(0)h_{j+1-s}=(-1)^{j+1}h_{j+1}`$. So $`c_{j,t}=(-1)^{j}h_{j-t}`$ for all $`j,t`$. Since $`\operatorname{ord}W_{m-j}(u)=(m-j+1)u`$ and $`m\ge j`$, in <a href="#long1049:eq:state-expansion" data-reference-type="eqref" data-reference="long1049:eq:state-expansion">[long1049:eq:state-expansion]</a> only the state $`u=0`$ contributes at degree $`E(m,j)`$, which gives both assertions. ◻

</div>

Apply this to the normalised source tail
``` math
T_{m,t}=q^{(m+1)t}\,(q;q)_m^{3}\,\frac{(q^{t+1};q)_m}{(q^{m+t+1};q)_{m+1}} .
```
With $`C_t=(1-q^{t+1})^{-1}`$ and
``` math
H_t(X)=\frac{(1-X)^{3}(1-q^{t}X)^{2}}{(1-q^{t}X^{2})(1-q^{t+1}X^{2})}
```
one has $`T_{m,t}=C_tW_m^{H_t}(t)`$, because $`\prod_{r\le m}H_t(q^{r})`$ telescopes to $`(q;q)_m^{3}(1-q^{t+1})(q^{t+1};q)_m/(q^{m+t+1};q)_{m+1}`$: the two denominator products contribute the consecutive factors $`1-q^{t+2},\dots,1-q^{t+2m+1}`$. Reducing modulo $`q`$ gives $`\bar H_t=(1-X)^{3}`$ for $`t>0`$, so $`h^{(t)}_r=\binom{r+2}{2}`$, and $`\bar H_0=(1-X)^{4}/(1+X)`$, so $`h^{(0)}_r=(r+1)(r+2)(2r+3)/6`$. Both have $`C_t(0)=1`$. The rows are $`v_m=\sum_{t\ge0}T_{m,t}`$, and interchanging that sum with the finite difference $`D_j`$ is legitimate because $`\operatorname{ord}T_{m,t}=(m+1)t`$. Terms with $`t>j`$ contribute $`h^{(t)}_{j-t}=0`$, so Lemma <a href="#long1049:res:allrowinitial" data-reference-type="ref" data-reference="long1049:res:allrowinitial">11</a> at $`m=j+\ell`$, where $`E(j+\ell,j)=j(j+1)/2+j\ell`$, gives
``` math
\begin{equation}
\label{long1049:eq:row-initial}
 D_jv_{j+\ell}=(-1)^{j}\frac{(j+1)^{2}(j+2)}2\,q^{\,j(j+1)/2+j\ell}
 +O\bigl(q^{\,j(j+1)/2+j\ell+1}\bigr)
 \qquad(j,\ell\ge0),
\end{equation}
```
the coefficient because
``` math
h^{(0)}_j+\sum_{t=1}^{j}h^{(t)}_{j-t}
 =\frac{(j+1)(j+2)(2j+3)}6+\binom{j+2}3
 =\frac{(j+1)^{2}(j+2)}2 .
```

<div class="proof">

*Proof of Theorem <a href="#long1049:res:zudilin-sharp-qorder" data-reference-type="ref" data-reference="long1049:res:zudilin-sharp-qorder">10</a>.* The operators $`D_j`$ act by lower unitriangular row operations, so they leave $`\det(v_{i+j})_{0\le i,j<N}`$ unchanged. By <a href="#long1049:eq:row-initial" data-reference-type="eqref" data-reference="long1049:eq:row-initial">[long1049:eq:row-initial]</a> the entry in row $`j`$ and column $`\ell`$ has order $`e(j,\ell)=j(j+1)/2+j\ell`$. In the Leibniz expansion the weight of a permutation $`\varsigma`$ is $`\sum_j\bigl(j(j+1)/2+j\varsigma(j)\bigr)`$, and by the rearrangement inequality $`\sum_jj\varsigma(j)`$ is uniquely minimised by the reversal $`\varsigma(j)=N-1-j`$, the values $`j`$ being distinct. The minimum weight is $`\sum_{j<N}j^{2}=N(N-1)(2N-1)/6`$, so exactly one Leibniz term attains it and no cancellation is possible there. The sign of the reversal is $`(-1)^{N(N-1)/2}`$, which cancels $`\prod_{j<N}(-1)^{j}`$, and the surviving coefficient is
``` math
\prod_{j=0}^{N-1}\frac{(j+1)^{2}(j+2)}2=\frac{(N!)^{2}(N+1)!}{2^{N}} .
```
 ◻

</div>

<a id="formal-order-and-analytic-size-are-different-questions."></a>

#### Formal order and analytic size are different questions.

Theorem <a href="#long1049:res:zudilin-sharp-qorder" data-reference-type="ref" data-reference="long1049:res:zudilin-sharp-qorder">10</a> fixes the first nonzero power of $`q`$ and its coefficient at each fixed rank. It does not control the value at a fixed rational $`q`$ as the rank grows. For the logic, the integer polynomials $`f_N(q)=C_Nq^{B_N}(1-q)^{N^{3}}`$, with $`B_N=\sum_{j<N}j^{2}`$ and $`C_N=(N!)^{2}(N+1)!/2^{N}`$, have exactly the order $`B_N`$ and exactly the leading coefficient $`C_N`$, while $`f_N(2/3)=C_N(2/3)^{B_N}3^{-N^{3}}`$ carries a further cubic exponential factor that neither datum sees. The following separate positive-measure argument supplies the fixed-base estimate for $`V_N^*`$; it is not inferred from the formal order.

<a id="a-separate-positive-measure-estimate."></a>

#### A separate positive-measure estimate.

For fixed $`0<q<1`$ write $`P=(q;q)_\infty`$, $`Q=(\sqrt q;q)_\infty`$, $`T=(-1;q)_\infty^2`$, and
``` math
G_q(w)=\frac1{(w;q)_\infty^3}\sum_{t\ge0}\frac{w^t}{(q;q)_t}
          \frac{(q^tw^2;q)_\infty}{(q^tw;q)_\infty^2},
 \qquad \gamma_k=[w^k]G_q(w),\qquad c_k=\frac{(k+1)^2(k+2)}2.
```
All products converge normally on $`|w|\le r<1`$ and the $`t`$-sum is bounded there by a constant times $`\sum_t r^t`$. The finite-to-infinite product identities give $`v_m^*=P^4G_q(q^{m+1})`$. The identity
``` math
\frac{(Aw;q)_\infty}{(w;q)_\infty}
   =\sum_{j\ge0}\frac{(A;q)_j}{(q;q)_j}w^j\quad(0\le A\le1)
```
follows by comparing coefficients in $`(1-w)R(w)=(1-Aw)R(qw)`$ with $`R(0)=1`$; the series converges for $`|w|<1`$ since its coefficients are at most $`P^{-1}`$. They are nonnegative, and at least $`(A;q)_\infty`$ if $`A<1`$. For $`A=1`$ the series equals $`1`$. Factor the numerator of the $`t`$th term using
``` math
(q^tw^2;q)_\infty=(q^{t/2}w;q)_\infty(-q^{t/2}w;q)_\infty
 (q^{(t+1)/2}w;q)_\infty(-q^{(t+1)/2}w;q)_\infty.
```
Pair the two positive-argument factors with two copies of $`(w;q)_\infty^{-1}`$. All remaining factors have nonnegative coefficients. The $`t=0`$ term bounds $`\gamma_k`$ below by $`Q\binom{k+3}3`$. For upper bounds, a nonnegative-coefficient regular factor $`R`$ with $`R(1)\le C`$, multiplying a series with nondecreasing coefficients $`d_k`$, contributes at most $`Cd_k`$ by convolution. This rule bounds the $`t=0`$ term by $`TP^{-4}\binom{k+3}3`$ and the sum of the $`t\ge1`$ terms by $`TP^{-6}\binom{k+2}3`$. Consequently
``` math
\frac Q3 c_k\le\gamma_k\le T(P^{-4}+P^{-6})c_k.
```
Thus $`\sum_{k\ge0}P^4\gamma_kq^k\delta_{q^k}`$ is a finite positive measure with infinitely many distinct support points and moments $`v_m^*`$. A nonzero polynomial of degree less than $`N`$ cannot vanish at all of its first $`N`$ atoms; the associated Gram matrix is positive definite. Finite Cauchy–Binet followed by convergence of every matrix entry and monotone convergence of the nonnegative tuple sums gives
``` math
V_N^*=\sum_{k_0<\cdots<k_{N-1}}
 \prod_i(P^4\gamma_{k_i}q^{k_i})\prod_{i<j}(q^{k_i}-q^{k_j})^2.
```
Retaining the tuple $`k_i=i`$ and using $`\prod_{d=1}^{N-1}(1-q^d)^{2(N-d)}\ge P^{2N}`$ gives the lower bound below. For the upper bound put $`k_i=i+\lambda_i`$, use $`c_{i+\lambda}/c_i\le(\lambda+1)^3`$, discard residual Vandermonde factors bounded by $`1`$, and drop the ordering restriction on the nonnegative $`\lambda_i`$. With $`S(q)=(1+4q+q^2)/(1-q)^4`$ this gives
``` math
(P^6Q/3)^N C_Nq^{B_N}\le V_N^*(q)
 \le\bigl[P^4T(P^{-4}+P^{-6})S(q)\bigr]^N C_Nq^{B_N}.
```
Both constants are positive and finite, so $`V_N^*(q)>0`$ and $`\log(V_N^*(q)/(C_Nq^{B_N}))=O_q(N)`$, including $`N=0`$ under the empty determinant convention. This is a separate analytic proof; it supplies no new denominator factor for the 2004 polynomial forms. The generating-function identification and infinite determinant expansion in this argument are not yet formalised in Lean.

<a id="evidence-decomposition.-1"></a>

#### Evidence decomposition.

The proof above is ordinary mathematics. One part of it is kernel-checked in this library: the all-depth associated-graded recurrence [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/AdelicHeightBridge.lean#L183). The initial monomial of transformed row $`1`$ in every column, of order exactly $`l+1`$ and coefficient exactly $`-6`$, and the two closed forms $`6\operatorname{ord}=N(N-1)(2N-1)`$ and $`2^{N}\mathrm{lc}=(N!)^{2}(N+1)!`$, are ordinary in this record; those Lean names are not in this checkout. The initial-monomial theorem for rows $`j\ge2`$ is outside this library; row $`j=2`$, with initial monomial $`18q^{2l+3}`$, is checked in a module of the external-verification cut, and rows $`j\ge3`$ are open, so the Lean identification of $`V_N^{*}`$ itself with the assembled leading matrix stays conditional on a row hypothesis. Independently of the proof, the order and the leading coefficient were computed exactly for $`1\le N\le7`$, giving orders $`0,1,5,14,30,55,91`$ and leading coefficients $`1,6,108,4320,324000,40824000,8001504000`$, each matching the closed forms.

<a id="attribution-and-remaining-obligation."></a>

#### Attribution and remaining obligation.

The antecedent is the inequality of \[zudilin2016, Sec. 4\]; the equality and the leading coefficient are proved here. The remaining obligation is a formal one. Lemma <a href="#long1049:res:allrowinitial" data-reference-type="ref" data-reference="long1049:res:allrowinitial">11</a> and <a href="#long1049:eq:row-initial" data-reference-type="eqref" data-reference="long1049:eq:row-initial">[long1049:eq:row-initial]</a> give the initial monomial of every row, and the Lean formalisation of that identity stops at $`j=2`$, so the Lean statement about $`V_N^{*}`$ retains a row hypothesis that the proof above discharges. Nothing in this subsection decides the arithmetic nature of $`F(3/2)`$.

<a id="long1049:sec:primitive"></a>

# Integer scalar content is neutral

An irrationality argument by linear forms replaces the clearing scheme by explicit rational approximation: one constructs integer linear forms in $`1`$ and $`F(\beta)`$ whose analytic decay outruns the height of their common denominator. For an integer coefficient pair $`(U,V)`$ and a real target $`S`$, put
``` math
L_S(U,V)=US-V,
 \qquad
 \Delta\bigl((U_n,V_n),(U_m,V_m)\bigr)=U_nV_m-U_mV_n.
```
We call $`L_S(U,V)`$ the *error* of the row at $`S`$; a good approximation is one that makes it small. The second expression is the exterior determinant of the two rows, and it eliminates $`S`$ exactly:
``` math
\Delta=U_mL_S(U_n,V_n)-U_nL_S(U_m,V_m).
```

This identity is what makes the determinant useful. Since $`\Delta`$ is an integer, if it does not vanish then
``` math
1\le|\Delta|
  \le|U_m|\,\bigl|L_S(U_n,V_n)\bigr|+|U_n|\,\bigl|L_S(U_m,V_m)\bigr|,
```
and the two errors cannot both be smaller than $`1/(|U_n|+|U_m|)`$. The determinant therefore carries two competing quantities at once, an integer that divides it and its own absolute value, and the theorem below is about how a rescaling moves them.

<div id="long1049:res:content" class="theorem">

**Theorem 12** (integer-scalar-content no-go). *Let $`S`$ be real, let $`(U_n,V_n)`$ and $`(U_m,V_m)`$ be pairs of integers, and let $`c_n,c_m`$ be integers. Then
``` math
L_S(c_nU_n,c_nV_n)=c_nL_S(U_n,V_n),
```
``` math
\Delta\bigl(c_n(U_n,V_n),c_m(U_m,V_m)\bigr)
 =c_nc_m\Delta\bigl((U_n,V_n),(U_m,V_m)\bigr),
```
and consequently
``` math
\left|\Delta\bigl(c_n(U_n,V_n),c_m(U_m,V_m)\bigr)\right|
 =|c_n|\,|c_m|\,
   \left|\Delta\bigl((U_n,V_n),(U_m,V_m)\bigr)\right|.
```
In particular $`c_nc_m`$ divides the scaled determinant. Hence a local divisor supplied only by the two integer scalar factors is paid for by exactly the same factor in the Archimedean determinant height.*

</div>

<div class="proof">

*Proof.* All three identities are routine expansions in $`\mathbb{Z}`$ or $`\mathbb{R}`$; the divisibility statement uses the primitive determinant as its witness. ◻

</div>

Informally, Theorem <a href="#long1049:res:content" data-reference-type="ref" data-reference="long1049:res:content">12</a> says that multiplying specialised integer rows by scalar factors moves the local gain and the Archimedean cost by exactly the same amount. Within an argument whose only extra divisor is integer scalar content, primitive normalisation therefore loses no net gain. This says nothing about polynomial factors before specialisation, cross-row common factors, determinant-specific arithmetic, or additive combinations.

<div id="long1049:ex:content" class="example">

**Example 13**. Take $`(U_n,V_n)=(1,2)`$ and $`(U_m,V_m)=(3,5)`$, so that $`\Delta=1\cdot5-3\cdot2=-1`$. Multiplying the first row by $`c_n=6`$ and the second by $`c_m=10`$ gives the rows $`(6,12)`$ and $`(30,50)`$, whose determinant is $`6\cdot50-30\cdot12=-60`$. That determinant is now divisible by $`60`$, which looks like a local gain of $`60`$; and its absolute value has risen from $`1`$ to $`60`$, which is a cost of exactly the same size.

</div>

Lean checks the error identity in [error scaling](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L84), the determinant identity in [content factorisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L94), the exact absolute-height identity in [absolute determinant scaling](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L104), and the divisor statement in [content-product divisibility](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L116). The elimination identity is the checked [exterior determinant identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L124).

The key point is that the two scalings are the same scaling. Each identity on its own is a one-line expansion, and the interest of the theorem is not in any one of them. Taken together they say that the factor $`c_nc_m`$ which a rescaling introduces into the determinant reappears undiminished, as $`|c_n|\,|c_m|`$, in the absolute value of that determinant. The third identity is displayed with absolute values for exactly that reason: it is what makes the statement one about the Archimedean height and not about divisibility alone. Whatever $`c_n`$ and $`c_m`$ are, a rescaling therefore leaves the balance between the local divisor and that height where it was.

The theorem does not construct primitive Padé rows, estimate their remainders, or prove that their exterior determinant is nonzero. It removes one source of apparent gain: multiplying a useful row by a large common integer cannot improve the local-to-Archimedean balance. Within a construction whose proposed gain comes only from those integer scalars, the rows may be primitive-normalised without a net loss. This does not say that every candidate family must use such a normalisation or that every proof needs separate $`2`$-adic and $`3`$-adic gain. The theorem quantifies over arbitrary integer pairs, so it applies whenever a construction has reached that specialised-row stage.

<a id="long1049:sec:endpoints"></a>

# Endpoint residues at $`(3,2)`$ and the four-jet kernel

Zudilin’s treatment of $`q`$-harmonic series \[zudilin2004\] builds linear forms of the shape used in Section <a href="#long1049:sec:primitive" data-reference-type="ref" data-reference="long1049:sec:primitive">4</a> out of Heine’s basic transform. The generic endpoint and jet lemmas below concern arbitrary integral coefficient pairs of this shape; they do not construct or instantiate Zudilin’s actual polynomial family. Each lemma uses no property beyond integrality and quantifies over arbitrary elements of $`\mathbb{Z}[X]`$. The exception is Theorem <a href="#long1049:res:scalar" data-reference-type="ref" data-reference="long1049:res:scalar">25</a> at the end of the section, whose subject is the scalar parameters of Zudilin’s cone. It says nothing about the coefficient polynomials.

Substituting $`X=3/2`$ into an integer polynomial produces a rational number, and multiplying by a power of $`2`$ clears its denominator. The following evaluation records that cleared numerator, so that all the arithmetic below stays inside $`\mathbb{Z}`$. For $`P(X)=\sum_i p_iX^i\in\mathbb{Z}[X]`$ and a declared width $`W\ge0`$, put
``` math
H_W(P)=\sum_{i=0}^{W}p_i\,3^i2^{W-i}.
```
This is the [homogeneous endpoint evaluation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L98). It is homogeneous in the sense that $`X^{i}`$ is replaced by $`3^{i}2^{W-i}`$, so the numerator and the denominator of the base are carried symmetrically. When $`W\ge\deg P`$ it is exactly the cleared numerator, since
``` math
\sum_{i=0}^{W}p_i\,3^i2^{W-i}=2^{W}\sum_{i=0}^{W}p_i\left(\tfrac32\right)^{i}
 =2^{W}P\!\left(\tfrac32\right).
```

<div id="long1049:res:endpoints" class="theorem">

**Theorem 14** (endpoint residues). *Let $`P=\sum_ip_iX^i\in\mathbb{Z}[X]`$ and let $`W\ge0`$. Then
``` math
H_W(P)\equiv p_0\,2^W\pmod 3,\qquad
 H_W(P)\equiv p_W\,3^W\pmod 2.
```
Consequently a unit constant coefficient prevents divisibility by $`3`$, and a unit coefficient at the declared width $`W`$ prevents divisibility by $`2`$.*

</div>

<div class="proof">

*Proof.* Modulo $`3`$, every summand with $`i>0`$ vanishes; modulo $`2`$, every summand with $`i<W`$ vanishes. The remaining powers are units in the corresponding residue fields. ◻

</div>

Since $`2^{W}`$ is invertible modulo $`3`$ and $`3^{W}`$ is invertible modulo $`2`$, the two congruences say more than the stated consequence: divisibility of $`H_W(P)`$ by $`3`$ is decided by $`p_0`$ alone, and divisibility by $`2`$ by $`p_W`$ alone. The rest of the coefficient vector is invisible to both primes. The coefficient $`p_W`$ is the top coefficient of $`P`$ exactly when $`\deg P=W`$, and is zero when $`\deg P<W`$; the identity $`H_W(P)=2^{W}P(3/2)`$ likewise holds only for $`\deg P\le W`$.

<div id="long1049:ex:endpoints" class="example">

**Example 15**. Take $`W=2`$. The three polynomials below differ only at an endpoint.

<div class="center">

| $`P`$      | $`H_2(P)`$                     | $`3\mid H_2(P)`$ | $`2\mid H_2(P)`$ |
|:-----------|:-------------------------------|:----------------:|:----------------:|
| $`X^2+1`$  | $`1\cdot4+0\cdot6+1\cdot9=13`$ |        no        |        no        |
| $`X^2+3`$  | $`3\cdot4+0\cdot6+1\cdot9=21`$ |       yes        |        no        |
| $`2X^2+1`$ | $`1\cdot4+0\cdot6+2\cdot9=22`$ |        no        |       yes        |

</div>

The first has both endpoints equal to $`1`$ and its evaluation, $`13`$, is divisible by neither prime; as a check, $`2^{2}\bigl((3/2)^2+1\bigr)=13`$. The second and third show that each hypothesis is used: spoiling the constant endpoint admits $`3`$, and spoiling the top endpoint admits $`2`$.

</div>

The congruences are the [bottom-endpoint identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L203) and [top-endpoint identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L320); the unit consequences are the [constant-endpoint obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L338) and [top-endpoint obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L356).

The proof is two lines, but the shape of the statement is not incidental. The difficulty lies in the fact that the specialisation sees a different endpoint at each of the two primes: modulo $`3`$ only the constant coefficient survives, and modulo $`2`$ only the top one does. The two exclusions are therefore conditions at opposite ends of the coefficient vector, and the statement below imposes one at each end, on the two entries of a single coefficient pair.

<div id="long1049:res:commonmult" class="proposition">

**Proposition 16** (common divisor). *Let $`U,V\in\mathbb{Z}[X]`$ and let $`W\ge0`$. If $`U`$ has unit top endpoint, $`V`$ has unit constant endpoint, and an integer $`c`$ divides both $`H_W(U)`$ and $`H_W(V)`$, then
``` math
2\nmid c\qquad\text{and}\qquad 3\nmid c.
```*

</div>

This is the checked [common-divisor exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L398). The proposition does not say that the two evaluations are coprime; it says that whatever they share misses both of the primes that matter at $`3/2`$.

<div id="long1049:ex:commonmult" class="example">

**Example 17**. Take $`W=2`$, $`U=X^2+3`$ and $`V=5X^2+1`$. The top endpoint of $`U`$ and the constant endpoint of $`V`$ are both $`1`$, and
``` math
H_2(U)=3\cdot4+1\cdot9=21,\qquad H_2(V)=1\cdot4+5\cdot9=49 .
```
Here $`\gcd(21,49)=7`$, so a common divisor does exist and is not small; it is simply coprime to $`6`$.

</div>

<div id="long1049:res:nomult" class="corollary">

**Corollary 18** (no gain from integer scalar content or the stated common divisor at $`3/2`$). *Under the endpoint hypotheses of Proposition <a href="#long1049:res:commonmult" data-reference-type="ref" data-reference="long1049:res:commonmult">16</a>, neither integer scalar content of specialised rows nor a common divisor of the two specialised evaluations $`H_W(U)`$ and $`H_W(V)`$ can supply factors $`2`$ and $`3`$ by those mechanisms in the common-width endpoint architecture studied here.*

</div>

<div class="proof">

*Proof.* By Theorem <a href="#long1049:res:content" data-reference-type="ref" data-reference="long1049:res:content">12</a> integer scalar content multiplies the analytic error and the exterior determinant, including the absolute determinant height, by exactly the factors it introduces, so a divisor obtained that way is paid for by the same factor in that height. By Proposition <a href="#long1049:res:commonmult" data-reference-type="ref" data-reference="long1049:res:commonmult">16</a> an integer dividing both specialised evaluations is divisible by neither $`2`$ nor $`3`$. ◻

</div>

One further consequence of Theorem <a href="#long1049:res:endpoints" data-reference-type="ref" data-reference="long1049:res:endpoints">14</a> is worth stating, because it bears on the most natural way one might hope to import an existing denominator reduction. Write $`\Phi_m`$ for the $`m`$th cyclotomic polynomial and, for coprime $`a>b\ge1`$, put $`\Phi_m(a,b)=b^{\varphi(m)}\Phi_m(a/b)`$ for its homogenisation at the declared width $`\varphi(m)=\deg\Phi_m`$.

<div id="long1049:res:cyclounit" class="proposition">

**Proposition 19** (homogenised cyclotomic values are unit at both endpoints). *Let $`a>b\ge1`$ with $`\gcd(a,b)=1`$ and let $`m\ge1`$. Then $`\gcd(\Phi_m(a,b),ab)=1`$. In particular $`\gcd(\Phi_m(3,2),6)=1`$ for every $`m`$.*

</div>

<div class="proof">

*Proof.* $`\Phi_m`$ is monic and $`\Phi_m(0)=\pm1`$, so its coefficients at both declared endpoints are units. Theorem <a href="#long1049:res:endpoints" data-reference-type="ref" data-reference="long1049:res:endpoints">14</a> applies verbatim with $`W`$ replaced by $`\varphi(m)`$: modulo a prime dividing $`b`$ only the top term of the homogenisation survives, and modulo a prime dividing $`a`$ only the constant term does. ◻

</div>

The kernel-checked declaration [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L302) proves Proposition <a href="#long1049:res:cyclounit" data-reference-type="ref" data-reference="long1049:res:cyclounit">19</a> in the same homogeneous-evaluation representation. It checks Proposition 3.6 under the displayed coprimality assumptions; it does not certify the later analytic deductions or Proposition 8.6.

The methods that reduce denominators at integer bases, the factorial-coset quotients of Rhin and Viola \[rhinviola1996\] and the order-twelve group and cyclotomic divisor of Zudilin \[zudilin2004\], produce their gain as cyclotomic or factorial factors of the coefficient polynomials. Proposition <a href="#long1049:res:cyclounit" data-reference-type="ref" data-reference="long1049:res:cyclounit">19</a> says that transporting such a factor through the homogenisation at $`(3,2)`$ contributes no power of $`2`$ and no power of $`3`$, whatever its size. This does not make such factors useless: a large odd divisor still reduces Archimedean height, and that is a different account of the same product formula. It does say that the $`2`$- and $`3`$-primary gain the architecture of Section <a href="#long1049:sec:open" data-reference-type="ref" data-reference="long1049:sec:open">10</a> requires must come from somewhere other than an imported cyclotomic factor. The exclusions therefore reflect the architecture itself, beyond the local behaviour of the two primes involved.

Both ingredients are Lean-checked; the combination is an ordinary deduction and is not separately formalised. The corollary excludes two ways of producing the targeted gain. It does not show that a gain of that kind is necessary for a proof by linear forms at $`3/2`$.

Corollary <a href="#long1049:res:nomult" data-reference-type="ref" data-reference="long1049:res:nomult">18</a> excludes the two multiplicative mechanisms above, and one candidate pursued in the rest of this section is additive: take an integer combination of several rows and ask that the combination be divisible where the individual rows are not. No single row is multiplied by a scalar. The endpoint congruences are the first case of a divisibility condition that can be imposed to any depth, and it is that condition, read additively, which is counted below.

We first raise the two congruences to prime powers. Fix depths $`R,S\ge0`$. For $`P\in\mathbb{Z}[X]`$ the *bottom jet* $`J_{3,R}(P)`$ is the residue of $`H_W(P)`$ modulo $`3^R`$, and the *top jet* $`J_{2,S}(P)`$ is its residue modulo $`2^S`$; Theorem <a href="#long1049:res:endpoints" data-reference-type="ref" data-reference="long1049:res:endpoints">14</a> computes them at $`R=S=1`$. Their vanishing is exactly the requested divisibility:
``` math
J_{3,R}(P)=0\iff 3^R\mid H_W(P),\qquad
 J_{2,S}(P)=0\iff 2^S\mid H_W(P).
```
These are the checked [bottom-jet divisibility criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L191) and [top-jet divisibility criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L197).

The *four-jet signature* of a coefficient pair $`(U,V)`$ is then the quadruple
``` math
\bigl(J_{3,R}(U),J_{3,R}(V),J_{2,S}(U),J_{2,S}(V)\bigr)
 \in(\mathbb{Z}/3^R\mathbb{Z})^2\times(\mathbb{Z}/2^S\mathbb{Z})^2 ,
```
two residues for each of the two primes, one from each entry of the pair. By the displayed criteria it vanishes exactly when $`3^R`$ divides both specialised entries and $`2^S`$ divides both.

For this candidate architecture, this turns the targeted local divisor into an additive congruence-kernel problem: what is sought is no longer a common divisor of the two evaluations, but a vector of small integer coefficients on which four residues vanish at once. Since $`H_W`$ is linear in the coefficients of $`P`$, the four-jet signature of a combination is the corresponding combination of signatures, which is what makes the following count possible.

<div id="long1049:res:jetkernel" class="theorem">

**Theorem 20** (binary four-jet collision). *Fix a width $`W`$ and depths $`R,S`$, and let $`(U_j,V_j)_{j<M}`$ be any $`M`$ pairs of integral polynomials. Call a subset of $`\{0,\dots,M-1\}`$, equivalently a vector of $`\{0,1\}^M`$, a *binary selector*. If the $`2^M`$ binary selectors outnumber the finite four-jet target
``` math
(\mathbb{Z}/3^R\mathbb{Z})^2\times(\mathbb{Z}/2^S\mathbb{Z})^2,
```
then two distinct subsets have the same four-jet sum. Subtracting their indicator vectors gives a nonzero coefficient vector in $`\{-1,0,1\}^M`$ cancelling all four jets. The target has exact cardinality
``` math
(3^R)^2(2^S)^2.
```
In particular, if $`R>0`$ and $`4R+2S\le M`$, such a collision exists.*

</div>

<div class="proof">

*Proof.* Send each binary selector to the sum of the four-jet signatures it selects. The claimed cardinal inequality and the pigeonhole principle give two distinct selectors in the same fibre. The cardinality formula is the product of the four cyclic-modulus cardinalities. For $`R>0`$,
``` math
(3^R)^2(2^S)^2<(4^R)^2(2^S)^2=2^{4R+2S}\le2^M,
```
which proves the stated sufficient threshold. ◻

</div>

The power bracket improves the generic coefficient $`4R`$ when the bottom depth is a multiple of $`41`$.

<div id="long1049:res:rankfortyone" class="corollary">

**Corollary 21** (sharp rank-$`41`$ four-jet threshold). *Let $`T>0`$. At bottom depth $`R=41T`$, any family of $`M\ge130T+2S`$ integral polynomial pairs has two distinct binary selectors with the same four-jet sum. For $`T=1`$ the coefficient $`130`$ is exact for this counting argument:
``` math
2^{129+2S}<\bigl| (\mathbb{Z}/3^{41}\mathbb{Z})^2\times
                       (\mathbb{Z}/2^S\mathbb{Z})^2\bigr|.
```
No exact-optimality assertion is made here for $`T>1`$.*

</div>

<div class="proof">

*Proof.* The upper power inequality gives
``` math
(3^{41T})^2(2^S)^2
 <(2^{65})^{2T}(2^S)^2=2^{130T+2S}\le2^M,
```
so Theorem <a href="#long1049:res:jetkernel" data-reference-type="ref" data-reference="long1049:res:jetkernel">20</a> applies. For $`T=1`$, direct integer evaluation gives $`2^{129}<3^{82}`$; multiplying by $`(2^S)^2`$ gives the displayed reverse count at $`129+2S`$. ◻

</div>

The sufficient collision threshold is [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/AdelicHeightBridge.lean#L279), while its exact unit-block failure one row earlier is [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/AdelicHeightBridge.lean#L292).

For all depths at once the ambient-cardinality inequality $`2^{M}>3^{2R}2^{2S}`$ holds exactly when
``` math
M\ \ge\ M_{\mathrm{count}}(R,S)=\bigl\lfloor2R\log_23+2S\bigr\rfloor+1,
```
because $`2R\log_23`$ is irrational for $`R\ge1`$. At $`R=41`$ this is $`130+2S`$, and at $`R=41\cdot31`$ it is $`4029+2S`$, one below the uniform bound $`4030+2S`$ of Corollary <a href="#long1049:res:rankfortyone" data-reference-type="ref" data-reference="long1049:res:rankfortyone">21</a>; the corollary trades exactness for a certificate that is a single integer comparison. The name of the parameter $`41`$ is the bottom depth, and the number of input rows is $`130+2S`$.

Counting alone does not ensure that the two selectors produce different analytic remainders. The exact missing step is a bounded-fibre estimate.

<div id="long1049:res:boundedfibre" class="theorem">

**Theorem 22** (bounded-fibre escape). *Let $`A`$ and $`B`$ be finite sets, let $`f:A\to B`$, and let $`g:A\to C`$ be any map into a set $`C`$. Suppose every fibre of $`g`$ has at most $`k`$ elements. If
``` math
|B|k<|A|,
```
then there exist distinct $`x,y\in A`$ such that
``` math
f(x)=f(y)\qquad\hbox{and}\qquad g(x)\ne g(y).
```
Thus, with $`f`$ the four-jet sum and $`g`$ the analytic remainder, a uniform remainder-multiplicity bound converts surplus selector entropy into a four-jet collision outside the remainder nullspace.*

</div>

<div class="proof">

*Proof.* If every pair in a common $`f`$-fibre also had the same $`g`$-value, each $`f`$-fibre would lie in one $`g`$-fibre and hence have size at most $`k`$. Summing over the at most $`|B|`$ fibres of $`f`$ would give $`|A|\le |B|k`$, contrary to the hypothesis. ◻

</div>

This finite escape principle is [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/AdelicHeightBridge.lean#L311).

<div id="long1049:res:plucker-collapse" class="theorem">

**Theorem 23** (Bézout–Plücker tail collapse). *Let $`R_0`$ be a commutative ring and let $`w_n=(A_n,B_n)\in R_0^2`$. Suppose that each row is unimodular, meaning that $`u_nA_n+v_nB_n=1`$ for some $`u_n,v_n\in R_0`$, and that every adjacent minor vanishes:
``` math
A_nB_{n+1}-B_nA_{n+1}=0\qquad(n\ge0).
```
Then every pairwise minor $`A_iB_j-B_iA_j`$ vanishes. In particular, take $`R_0=\mathbb{Z}/(2^S3^R)\mathbb{Z}`$ with $`R>0`$. If $`S+2R\le k`$, there are two distinct binary selectors $`s,t\in\{0,1\}^{k}`$ such that
``` math
\sum_{i<k}s_iw_i=\sum_{i<k}t_iw_i.
```
Thus the sufficient width is $`S+2R`$. The ambient two-coordinate width is $`2S+4R`$.*

</div>

<div class="proof">

*Proof.* If $`(a,b)`$ is unimodular, say $`ua+vb=1`$, and $`ay-bx=0`$, then
``` math
(x,y)=(ux+vy)(a,b).
```
Indeed, the first coordinate follows by replacing $`ay`$ with $`bx`$, and the second by the reverse substitution. Apply this identity to consecutive rows: each next row is a scalar multiple of the current one. Induction places the entire tail on the line through $`w_0`$ and proves the pairwise-minor assertion. A determinant-one Bézout shear sends $`w_0`$ to $`(1,0)`$, so all selector sums have only one free residue coordinate and occupy at most $`2^S3^R`$ values. Finally
``` math
2^S3^R<2^S4^R=2^{S+2R}\le2^k,
```
and pigeonhole gives the two selectors. ◻

</div>

No particular coordinate needs to be invertible: modulo six, $`(2,3)`$ is unimodular because $`-2+3=1`$, although neither entry is a unit. Some nondegeneracy is essential. The three rows $`(1,0),(0,0),(0,1)`$ have zero adjacent minors but outer minor one; a zero middle row transmits no information between its neighbours.

The unimodular [adjacent-to-pairwise determinant propagation](https://github.com/wcook04/plectis-erdos/blob/0cfa24a7fe555d75a9d9e7f119da4720a88c1396/ErdosProblems/Erdos1049/BezoutPluckerJets.lean#L191) and the resulting [modular selector collision](https://github.com/wcook04/plectis-erdos/blob/0cfa24a7fe555d75a9d9e7f119da4720a88c1396/ErdosProblems/Erdos1049/BezoutPluckerJets.lean#L280) are Lean-checked, including the [explicit $`S+2R`$ threshold](https://github.com/wcook04/plectis-erdos/blob/0cfa24a7fe555d75a9d9e7f119da4720a88c1396/ErdosProblems/Erdos1049/BezoutPluckerJets.lean#L299). The unit-coordinate statements are special cases of the stronger rowwise-coprime theorem. This conditional theorem is stronger than the ambient four-jet count only after its minor-vanishing hypothesis has been established. No such all-tail hypothesis is proved here for an actual $`q`$-Apéry or Zudilin family, and the theorem says nothing about whether the resulting selector difference has nonzero analytic remainder.

**Boundary.** Corollary <a href="#long1049:res:rankfortyone" data-reference-type="ref" data-reference="long1049:res:rankfortyone">21</a> is a sharp finite kernel statement at $`T=1`$, not an analytic nonvanishing theorem. Theorem <a href="#long1049:res:boundedfibre" data-reference-type="ref" data-reference="long1049:res:boundedfibre">22</a> identifies the precise extra input needed to escape the nullspace, but this paper does not prove a multiplicity bound for the actual $`q`$-Apéry or Zudilin remainder family.

The target count is the checked [four-jet target cardinality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L131); the abstract collision is the checked [four-jet pigeonhole kernel](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L142), and the linear sufficient condition is the checked [rank–depth collision threshold](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L161). The count is a routine pigeonhole; the reformulation above is what makes it relevant. Pigeonhole cancellation itself requires no independence. Additional information about the input family is needed to ensure that the resulting nonzero selector difference has a nonzero combined polynomial pair and analytic remainder. None of the statements proved here supplies such a family or proves either nonvanishing conclusion.

<div id="long1049:ex:jetcount" class="example">

**Example 24**. At depths $`R=S=1`$ the four-jet target is $`(\mathbb{Z}/3\mathbb{Z})^2\times(\mathbb{Z}/2\mathbb{Z})^2`$, of cardinality $`9\cdot4=36`$, and the threshold reads $`M\ge4\cdot1+2\cdot1=6`$. With six pairs there are $`2^{6}=64`$ binary selectors against $`36`$ targets, so two of them collide and their difference is a vector in $`\{-1,0,1\}^{6}`$, not identically zero, killing all four jets.

</div>

Informally, the theorem says only this: once there are at least $`4R+2S`$ pairs and the bottom depth $`R`$ is positive, some coefficient vector in $`\{-1,0,1\}^M`$, not identically zero, kills all four jets of the corresponding combination. It does not say that the combination is nonzero as a pair of polynomials, and it does not say that its remainder is nonzero. Those are the two obligations Problem <a href="#long1049:prob:kernel" data-reference-type="ref" data-reference="long1049:prob:kernel">37</a> carries.

One further exclusion is recorded here. Its subject is the scalar parameters of Zudilin’s cone, and it says nothing about the coefficient polynomials.

<div id="long1049:res:scalar" class="theorem">

**Theorem 25** (scalar margin no-go). *Let $`C_1>0`$. If $`C_0\le0`$ or $`2C_0\le C_1`$, then
``` math
C_0\log 3-C_1\log 2<0.
```
In the positive branch $`C_0>0`$ and $`2C_0\le C_1`$, the stronger estimate is
``` math
C_0\log3-C_1\log2< -\frac{17}{41}C_0\log2.
```*

</div>

Written multiplicatively, the conclusion is $`3^{C_0}<2^{C_1}`$. The inequality is immediate from $`\log3<2\log2`$ and $`C_1>0`$, and is the checked [three-halves scalar margin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinConeArithmetic.lean#L428). The positive-branch deficit is the checked [$`17/41`$ margin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/AdelicHeightBridge.lean#L242). The interest is in the fence around it. The primary Zudilin theorem \[zudilin2004, Theorem 1, p. 154; Sec. 5, pp. 161–162\] supplies an integer-base irrationality-exponent estimate on its parameter cone, and the elementary inequality $`\mu\ge2`$ then forces $`2C_0\le C_1`$ whenever $`C_0>0`$; Lean checks that implication separately. The primary theorem assumes an integer base $`p=1/q`$. It does not state a rational $`p=3/2`$ theorem, so the all-scale coefficient construction and rational specialisation remain external to the checked result, which is the scalar parameter margin alone.

<a id="long1049:sec:corridor"></a>

# Failure of coordinatewise clearing at $`3/2`$

This section and the next return to the elementary route and record what the residue $`s^{n}`$ costs there. We first isolate the arithmetic that the clearing scheme leaves behind, in a form that does not mention the series. The point of doing so is that the clearing argument asks for two things at once, that a power of the numerator divide what has been accumulated and that what survives be small, and these are easier to play off against each other once the series has been discarded and only six natural numbers remain.

<div id="long1049:def:corridor" class="definition">

**Definition 26** (coordinatewise corridor). Let $`a,b,N,K,Q,D`$ be natural numbers. Say that $`(a,b,N,K,Q,D)`$ is a *coordinatewise corridor* when
``` math
a>0,\qquad Q>0,\qquad D>0,\qquad D\le N+K,\qquad
 a^{K}\mid QD,\qquad Q\,b^{\,N+K+1}<a^{\,K+1}.
```

</div>

The reading is: $`a`$ and $`b`$ are the numerator and denominator of the base, playing the roles of $`r`$ and $`s`$ in the introduction, so that $`(a,b)=(3,2)`$ is the case of interest; $`N`$ is the shift, $`K`$ is the width of the cleared window, $`Q`$ is the accumulated clearing factor, and $`D`$ is the final coefficient being cleared. The bound $`D\le N+K`$ is the only property of the coefficient used; for the divisor-counting coefficient it holds because $`\tau(n)\le n`$. The divisibility $`a^{K}\mid QD`$ is the requirement that clearing succeeded coordinatewise, and the last inequality is the tail estimate that makes the trapped integer smaller than $`1`$. The name records the shape of the constraint: the divisibility bounds $`a^{K}`$ from above by $`Q(N+K)`$, the tail estimate bounds $`a^{K+1}`$ from below by $`Q\,b^{\,N+K+1}`$, and admissible parameters must fit in the band between them. The definition is the [corridor predicate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L113).

<div id="long1049:res:corridorbound" class="theorem">

**Theorem 27** (corridor bound). *If $`(a,b,N,K,Q,D)`$ is a coordinatewise corridor, then
``` math
b^{\,N+K+1}<a\,(N+K).
```*

</div>

<div class="proof">

*Proof.* A routine divisibility computation. Since $`QD>0`$ and $`a^{K}\mid QD`$, we have $`a^{K}\le QD`$, and $`D\le N+K`$ gives $`a^{K}\le Q(N+K)`$. Hence
``` math
Q\,b^{\,N+K+1}<a^{\,K+1}=a^{K}\cdot a\le Q(N+K)\cdot a,
```
and cancelling the positive factor $`Q`$ gives the claim. ◻

</div>

Formalised as the [power-versus-linear consequence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L121).

The inequality of Theorem <a href="#long1049:res:corridorbound" data-reference-type="ref" data-reference="long1049:res:corridorbound">27</a> is where the integer and rational cases part. At $`b=1`$ it reads $`1<a(N+K)`$, which holds for every $`a\ge2`$ and every nonempty window; this necessary inequality imposes no obstruction. The other corridor hypotheses remain in force. At $`b\ge2`$ the left side is exponential in $`N+K`$ and the right side is linear, so the corridor can survive only for small $`N+K`$. At $`(a,b)=(3,2)`$ the crossing has already happened at the smallest admissible window.

<div id="long1049:ex:corridor" class="example">

**Example 28**. Take the smallest window, $`N=K=1`$, and numerator $`a=3`$. At $`b=1`$ the tuple $`(3,1,1,1,3,1)`$ is a corridor: $`D=1\le2`$, the divisibility reads $`3\mid3`$, and the tail estimate reads $`3\cdot1^{3}=3<3^{2}=9`$. At $`b=2`$ no choice works. The tail estimate becomes $`Q\cdot2^{3}<3^{2}`$, which forces $`Q=1`$; the divisibility then reads $`3\mid D`$, and the only candidates are $`D=1`$ and $`D=2`$, neither divisible by $`3`$. This is the proof of Theorem <a href="#long1049:res:corridorbound" data-reference-type="ref" data-reference="long1049:res:corridorbound">27</a> in miniature: it derives $`a^{K}\le Q(N+K)`$, here $`3\le2`$.

</div>

<div id="long1049:res:exp" class="proposition">

**Proposition 29**. *For every natural number $`x\ge2`$ we have $`3x<2^{\,x+1}`$.*

</div>

<div class="proof">

*Proof.* A routine induction from $`x=2`$, where $`6<8`$. For the step, $`2^{x+1}\ge2^{2}>3`$ when $`x\ge1`$, so $`3(x+1)=3x+3<2^{x+1}+2^{x+1}=2^{x+2}`$. ◻

</div>

Formalised as the [exponential comparison](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L142).

<div id="long1049:res:nocorridor" class="theorem">

**Theorem 30** (no corridor at base $`3/2`$). *For all $`N\ge1`$ and $`K\ge1`$ and all natural $`Q,D`$, the tuple $`(3,2,N,K,Q,D)`$ is not a coordinatewise corridor.*

</div>

<div class="proof">

*Proof.* A corridor would give $`2^{\,N+K+1}<3(N+K)`$ by Theorem <a href="#long1049:res:corridorbound" data-reference-type="ref" data-reference="long1049:res:corridorbound">27</a>, contradicting Proposition <a href="#long1049:res:exp" data-reference-type="ref" data-reference="long1049:res:exp">29</a> applied to $`x=N+K\ge2`$. ◻

</div>

Formalised as the [corridor exclusion at three halves](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L155).

Theorem <a href="#long1049:res:nocorridor" data-reference-type="ref" data-reference="long1049:res:nocorridor">30</a> excludes the coordinatewise clearing scheme at $`3/2`$, and nothing else: it does not bound the denominator of $`F(3/2)`$, it does not show that $`F(3/2)`$ is irrational, and it does not show that $`F(3/2)`$ is rational. It also does not cover a clearing scheme of a different shape, since the corridor fixes one divisibility pattern and one tail inequality.

<a id="long1049:sec:tail"></a>

# The cleared-tail recurrence and the size of the forcing term

Theorem <a href="#long1049:res:nocorridor" data-reference-type="ref" data-reference="long1049:res:nocorridor">30</a> says that one scheme fails. This section identifies the quantity responsible, as an exact recurrence.

Let $`r,s,B,F`$ be rationals with $`r\ne0`$ and let $`c:\mathbb{N}\to\mathbb{Q}`$ be arbitrary. Define the prefix and the cleared tail state by
``` math
P_N=\sum_{m=0}^{N-1}\frac{c(m+1)\,s^{\,m+1}}{r^{\,m+1}},
 \qquad
 U_N=B\,r^{N}\bigl(F-P_N\bigr).
\tag{$\ast$}\label{long1049:eq:tailstate}
```
Thus $`P_N`$ is the partial sum of $`\sum_{n\ge1}c(n)(s/r)^{n}`$ through level $`N`$, and $`U_N`$ is the tail of a putative value $`F`$ after that level, scaled by $`Br^{N}`$. These are the [rational-base prefix](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L168) and the [cleared tail state](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L181).

<div id="long1049:res:tailrec" class="theorem">

**Theorem 31** (cleared-tail recurrence). *Let $`r,s,B,F\in\mathbb{Q}`$ with $`r\ne0`$, let $`c:\mathbb{N}\to\mathbb{Q}`$, and let $`P_N`$ and $`U_N`$ be as in <a href="#long1049:eq:tailstate" data-reference-type="eqref" data-reference="long1049:eq:tailstate">[long1049:eq:tailstate]</a>. Then for every $`N`$,
``` math
U_{N+1}=r\,U_N-B\,c(N+1)\,s^{\,N+1}.
```*

</div>

<div class="proof">

*Proof.* An immediate computation. Expanding $`P_{N+1}=P_N+c(N+1)s^{N+1}/r^{N+1}`$ and $`r^{N+1}=r^{N}\cdot r`$ in the definition of $`U_{N+1}`$ and clearing the denominator $`r^{N+1}`$, which is nonzero, gives the identity. ◻

</div>

Formalised as the [cleared-tail recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L187).

The recurrence has a linear part $`rU_N`$ and a forcing term $`Bc(N+1)s^{N+1}`$, the inhomogeneous term the state receives at each step. The direct-clearing route studied here works only if the state remains in a bounded window, and the forcing term is what that window must absorb. Its size is what separates the two denominator regimes.

<div id="long1049:res:forcing" class="theorem">

**Theorem 32** (the forcing term). *Let $`s,B`$ be natural numbers and $`c:\mathbb{N}\to\mathbb{N}`$, and put $`G_N=B\,c(N+1)\,s^{\,N+1}`$.*

1.  *If $`s\ge2`$, $`B\ge1`$ and $`c(N+1)\ge1`$, then $`2^{\,N+1}\le G_N`$.*

2.  *If $`s=1`$, then $`G_N=B\,c(N+1)`$.*

</div>

<div class="proof">

*Proof.* Both parts are routine. For the first, $`2^{N+1}\le s^{N+1}=1\cdot s^{N+1}\le Bc(N+1)s^{N+1}`$, using $`B\,c(N+1)\ge1`$. The second part is the definition with $`s=1`$. ◻

</div>

Formalised as the [exponential lower bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L204) and the [integer-base collapse](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L218).

At $`s=1`$ the forcing term is $`Bc(N+1)`$, so it grows only as fast as the coefficient; for the divisor function that is $`O(N^{\varepsilon})`$ for every $`\varepsilon>0`$, and a bounded-state argument has room. At $`s\ge2`$ the same term is at least $`2^{N+1}`$ whenever the coefficient is nonzero.

<div id="long1049:ex:forcing" class="example">

**Example 33**. Take $`B=1`$, $`c=\tau`$ and $`N=9`$, so that the coefficient is $`\tau(10)=4`$. At $`s=1`$ the forcing term is $`4`$. At $`s=2`$ it is $`4\cdot2^{10}=4096`$, and part (1) of Theorem <a href="#long1049:res:forcing" data-reference-type="ref" data-reference="long1049:res:forcing">32</a> already guarantees at least $`2^{10}=1024`$ without knowing the coefficient at all.

</div>

This is an exact lower bound on one quantity, and it is all that is proved. It is not a proof that no bounded-state argument exists at $`s\ge2`$; the theorem that one particular scheme fails is Theorem <a href="#long1049:res:nocorridor" data-reference-type="ref" data-reference="long1049:res:nocorridor">30</a>, and the bound here records the size of the term that scheme would have to absorb.

<a id="long1049:sec:sevenhalves"></a>

# The height criterion at $`7/2`$

In 1994 Bundschuh and Väänänen proved an irrationality criterion for a family of rational bases cut out by a height condition \[bv1994, Theorem 2, p. 177; hypotheses pp. 175–176\]. We keep their notation: $`q`$ is the base, and $`\alpha`$ and $`\lambda`$ are the parameters of the criterion. In its special case $`\alpha=-1`$, the printed hypothesis is
``` math
\lambda<\left(\frac12+\frac1{\pi^2}\right)^{-1}.
```
At $`q=7/2`$ the Archimedean parameter is $`\lambda=\log 7/\log(7/2)`$. The criterion therefore applies once the following strict inequality is checked.

<div id="long1049:res:sevenhalves" class="theorem">

**Theorem 34** (the $`7/2`$ height condition).
*``` math
\frac{\log 7}{\log(7/2)}
 <
 \left(\frac12+\frac1{\pi^2}\right)^{-1}.
```*

</div>

Numerically the two sides are $`1.5533\ldots`$ and $`1.6630\ldots`$, so the condition holds with a margin of about $`0.11`$. The Lean proof factors the estimate through the explicit [height-region predicate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L44) and the [integer certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L32) $`2^{18}<7^7`$, the resulting [logarithmic ratio bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L48) $`\log2/\log7<7/18`$, the [$`\pi`$-bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L64) $`1/\pi^2<1/9`$, and the [strict margin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L73)
``` math
\frac{\log2}{\log7}<\frac12-\frac1{\pi^2}.
```
The [final height inequality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalBaseLambert.lean#L83) then rewrites $`\log(7/2)=\log7-\log2`$ and closes the displayed condition.

This formalises the complete elementary parameter check at $`q=7/2`$; it does not formalise Bundschuh and Väänänen’s analytic irrationality theorem, whose proof occupies pp. 189–193 of the source. The conclusion that $`F(7/2)`$ is irrational is consequently cited from that theorem, not claimed as a Lean theorem here.

The criterion does not cover $`3/2`$, and the results of Sections <a href="#long1049:sec:corridor" data-reference-type="ref" data-reference="long1049:sec:corridor">6</a> and <a href="#long1049:sec:tail" data-reference-type="ref" data-reference="long1049:sec:tail">7</a> give no evidence either way about whether $`F(3/2)`$ is irrational.

<a id="the-81200-logarithmic-region"></a>

## The $`81/200`$ logarithmic region

Consider the rational-height region
``` math
\frac{\log b}{\log a}<\frac{81}{200}
 \qquad(a>b>0).
```
The rational number $`81/200`$ is not itself a threshold with an analytic theorem attached to it. It is the lower half of the rational bracket $`81/200<\theta^{*}<1/2`$ of Section <a href="#long1049:sec:regionbracket" data-reference-type="ref" data-reference="long1049:sec:regionbracket">2.5</a> around the derived constant of Theorem <a href="#long1049:res:region" data-reference-type="ref" data-reference="long1049:res:region">2</a>, and its role is to make membership of the region of that theorem decidable by an integer comparison. The Lean module of this library treats the displayed inequality as a definition and proves elementary memberships and exclusions. In particular,
``` math
\frac25
 <\frac{\log4}{\log31}
 <\frac{81}{200}
 <\frac{\log2}{\log3}.
```
The first two comparisons come respectively from $`31^2<4^5`$ and $`4^{200}<31^{81}`$; the last comes from $`3^{81}<2^{200}`$. The lower bound is the checked theorem [two-fifths lower bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L65). Consequently $`31/4`$, and every positive power $`(31/4)^r`$, lies in the enlarged region ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L45), [power family](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L59)). The same base lies strictly outside the earlier Bundschuh–Väänänen region ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L91)), so the $`81/200`$ inequality defines a strict set-theoretic enlargement of the earlier recorded logarithmic region. Combined with the bracket $`81/200<\theta^{*}`$, these memberships are exactly the finite input to Theorem <a href="#long1049:res:31over4" data-reference-type="ref" data-reference="long1049:res:31over4">3</a>, which is where the irrationality of $`F(31/4)`$ and of every $`F\bigl((31/4)^{r}\bigr)`$ is proved.

It still does not approach $`3/2`$. The exact comparison
``` math
3^{81}<2^{200}
 \quad\Longrightarrow\quad
 \frac{81}{200}<\frac{\log2}{\log3}
```
is Lean-checked, as is the conclusion that $`3/2`$ belongs to neither height region ([boundary](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L105), [exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/ZudilinHeightRegion.lean#L122)). Thus $`81/200`$ is the larger of the two explicitly defined cutoffs used below, while a cutoff that includes $`3/2`$ must be strictly larger than $`\log2/\log3\approx0.6309`$.

<a id="long1049:sec:pade"></a>

# Denominator exponents for a homogenised Padé construction

A second external route builds the linear forms of Section <a href="#long1049:sec:primitive" data-reference-type="ref" data-reference="long1049:sec:primitive">4</a> by Padé approximation. Such a construction produces its coefficients as sums of rational summands, and to obtain integer rows one multiplies through by a single common denominator. The bookkeeping obligation is then to check that no summand needs a larger denominator than the one proposed, which is a comparison between the exponents alone. This section does that comparison, and only that.

No source construction is named here for the exponent expressions below, and they are checked as displayed polynomial identities. No derivation of them is given here. Giving them Padé-theoretic force would additionally require deriving the expressions from a stated homogenised coefficient formula, proving integrality of the coefficients after multiplication by the proposed common denominator, and establishing nonvanishing and decay of the associated remainder. None of those three is claimed here.

For a homogenised construction over integer parameters the proposed common denominator exponent is $`E_n=(3n^{2}-n)/2`$. Since only doubled exponents occur below, every statement lives over $`\mathbb{Z}`$ and no parity bookkeeping is needed; we write $`\widetilde{E}_n=2E_n=3n^{2}-n`$.

<div id="long1049:res:pade" class="proposition">

**Proposition 35** (summand bound and exact gap). *Let $`\widetilde{E}_n=3n^{2}-n`$ and put
``` math
\widetilde{P}(n,k)=2\bigl(k(n-k)+nk\bigr)+k(k-1),
```
``` math
\widetilde{Q}(n,m)=2(n^{2}-n)+j^{2}+2jm+j-m^{2}+3m,
 \qquad j=n-m-1 .
```
Then, for integers $`n,k,m`$:*

1.  *if $`0\le k\le n`$, then $`\widetilde{P}(n,k)\le\widetilde{E}_n`$, and the gap factors as $`\widetilde{E}_n-\widetilde{P}(n,k)=(n-k)(3n-k-1)`$;*

2.  *$`\widetilde{E}_n-\widetilde{Q}(n,m)=2\bigl(n+m(m-1)\bigr)`$ identically;*

3.  *if $`n\ge0`$ and $`m\ge1`$, then $`\widetilde{Q}(n,m)\le\widetilde{E}_n`$.*

</div>

Part (1) is the [summand exponent bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L30), part (2) the [exact gap identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L52), and part (3) the [maximal exponent bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/RationalPadeArithmetic.lean#L60). The gap in (2) is an identity in $`\mathbb{Z}[n,m]`$, so (3) follows from $`m(m-1)\ge0`$ and $`n\ge0`$; the hypothesis $`m\ge1`$ names the range in which the corresponding summand does not vanish, and it is not the sharpest hypothesis under which the inequality holds.

<div id="long1049:ex:pade" class="example">

**Example 36**. At $`n=2`$ the proposed doubled exponent is $`\widetilde{E}_2=10`$, and $`\widetilde{P}(2,k)`$ takes the values $`0,6,10`$ at $`k=0,1,2`$. The three gaps are $`10,4,0`$, matching the factorisation $`(2-k)(5-k)`$ of part (1); the summand at $`k=2`$ is the one that saturates the proposed denominator. For part (2), at $`m=1`$ we have $`j=0`$ and $`\widetilde{Q}(2,1)=6`$, with gap $`4=2\bigl(2+1\cdot0\bigr)`$.

</div>

These are routine inequalities between polynomials in the exponents. They establish that the proposed exponent $`\widetilde{E}_n`$ dominates the two displayed summand exponent expressions, and nothing further. Positivity of the remainder, its rate of decay, and the comparison of that rate against the denominator height are the analytic obligations, and none of them is treated here, so nothing in this section is an irrationality measure.

<a id="long1049:sec:open"></a>

# Complements and further questions

Problem #1049 remains open. Theorem <a href="#long1049:res:jetkernel" data-reference-type="ref" data-reference="long1049:res:jetkernel">20</a> suggests the following precise sufficient subproblem for one common-width additive architecture. It is not asserted to be necessary for every proof of irrationality.

<div id="long1049:prob:kernel" class="problem">

**Problem 37** (common-width simultaneous endpoint-jet construction). Exhibit an integer constant $`C\ge1`$ and, for every sufficiently large positive integer $`n`$, positive integers $`W_n,R_n,S_n,M_n`$ such that
``` math
n^2\le W_n,R_n,S_n\le Cn^2,
 \qquad 4R_n+2S_n\le M_n\le Cn^2,
```
together with polynomial pairs $`(U_{n,j},V_{n,j})\in\mathbb{Z}[X]^2`$ for $`0\le j<M_n`$, each of degree at most the common declared width $`W_n`$, whose specialised integer rows are primitive:
``` math
\gcd\!\bigl(H_{W_n}(U_{n,j}),H_{W_n}(V_{n,j})\bigr)=1.
```
Find a nonzero vector $`\lambda^{(n)}\in\{-1,0,1\}^{M_n}`$ for which, on putting
``` math
U_n=\sum_{j<M_n}\lambda^{(n)}_jU_{n,j},
 \qquad V_n=\sum_{j<M_n}\lambda^{(n)}_jV_{n,j},
```
the pair $`(U_n,V_n)`$ is not $`(0,0)`$, all four common-width jets vanish,
``` math
J_{3,R_n}(U_n)=J_{3,R_n}(V_n)=0,
 \qquad J_{2,S_n}(U_n)=J_{2,S_n}(V_n)=0,
```
where every jet in this display is formed using the declared width $`W_n`$, and the resulting divided integer linear form
``` math
A_n=\frac{H_{W_n}(U_n)}{3^{R_n}2^{S_n}},
 \qquad
 B_n=\frac{H_{W_n}(V_n)}{3^{R_n}2^{S_n}},
 \qquad
 \rho_n=A_nF(3/2)-B_n
```
satisfies the explicit analytic condition
``` math
0<|\rho_n|<\frac1n.
```

</div>

The jet equations make $`A_n,B_n`$ integers. A solution would prove irrationality: if $`F(3/2)=a/b`$ in lowest terms, every nonzero $`\rho_n`$ has absolute value at least $`1/b`$, contradicting the displayed bound for $`n>b`$. Theorem <a href="#long1049:res:jetkernel" data-reference-type="ref" data-reference="long1049:res:jetkernel">20</a> supplies only a nonzero signed relation with the four jet equations once the pairs and size inequality are present; it does not supply primitive input rows, a nonzero combined polynomial pair, or the nonvanishing and decay of $`\rho_n`$.

Integer rescaling and a common divisor of the two specialised evaluations are the two mechanisms excluded by Corollary <a href="#long1049:res:nomult" data-reference-type="ref" data-reference="long1049:res:nomult">18</a>. Polynomial factors before specialisation, cross-row or determinant-specific arithmetic, cyclotomic factors, other additive constructions, and entirely different architectures remain outside that corollary and are not decided either way.

The remaining linear-form argument therefore has two independent gates: first find a four-jet collision that does not collapse algebraically or analytically; only then ask whether its divisibility and decay beat its height. We state those gates separately below.

<a id="exact-kernel-escape"></a>

## Exact kernel escape

Fix, for each $`n`$, a declared width $`W_n`$ and a specified family
``` math
(U_{n,j},V_{n,j},\mathcal R_{n,j})_{j<M_n},
```
where $`U_{n,j},V_{n,j}\in\mathbb{Z}[X]`$ and $`\mathcal R_{n,j}`$ is the corresponding remainder function. Normalisation must be fixed before the jet map is formed. Call the family *polynomially primitive* when the common coefficient content of the pair in $`\mathbb{Z}[X]^2`$ is divided out before specialisation; as the Terminology paragraph records, that is a different operation from primitive normalisation of a specialised integer row, which is what Problem <a href="#long1049:prob:kernel" data-reference-type="ref" data-reference="long1049:prob:kernel">37</a> imposes.

The specialised row content
``` math
g^{\mathrm{spec}}_{n,j}
 =\gcd\!\bigl(H_{W_n}(U_{n,j}),H_{W_n}(V_{n,j})\bigr)
```
and the content of a final additive combination are separate quantities; they are not silently divided out. If either is divided out later, both the height and the remainder below are measured after that same division. Under the unit endpoint hypotheses, $`g^{\mathrm{spec}}_{n,j}`$ is coprime to $`6`$, so such division does not manufacture or destroy the $`2`$- and $`3`$-primary jet vanishing.

Dividing a specialised row by its content changes the polynomial family it came from, and lifting the divided row back is a constrained problem. At width $`W`$ the map $`P\mapsto H_W(P)`$ on integer polynomials of degree at most $`W`$ is surjective onto $`\mathbb{Z}`$, since $`3^{W}`$ and $`2^{W}`$ are coprime, so a lift always exists; what is not automatic is a lift carrying the intended remainder identity and a uniform coefficient-height bound. At width $`1`$, for instance, $`(X+1,X+1)`$ specialises to $`(5,5)`$, whose primitive normalisation $`(1,1)`$ lifts to $`(X-1,X-1)`$ and not to any rescaling of the original pair. Any lift used below is therefore supplied together with its width, its height bound and its exact remainder.

For target depths $`R_n,S_n`$, let $`J_n(\lambda)`$ be the four-jet signature of the pair $`\sum_j\lambda_j(U_{n,j},V_{n,j})`$, and define
``` math
\mathcal C_n=
 \{\lambda\in\{-1,0,1\}^{M_n}\mathbin{\backslash}\{0\}:J_n(\lambda)=0\},
```
``` math
\begin{aligned}
 K_n^{\mathrm{poly}}
   &=\left\{\lambda\in\{-1,0,1\}^{M_n}:
       \sum_j\lambda_jU_{n,j}=0,\ \sum_j\lambda_jV_{n,j}=0\right\},\\
 K_n^{\mathrm{rem}}
   &=\left\{\lambda\in\{-1,0,1\}^{M_n}:
       \sum_j\lambda_j\mathcal R_{n,j}(3/2)=0\right\}.
\end{aligned}
```
The second nullspace concerns the value at $`3/2`$; an identically zero remainder function is a still stronger collapse and is automatically bad.

The exact pigeonhole condition is
``` math
2^{M_n}>3^{2R_n}2^{2S_n},
 \qquad\text{equivalently}\qquad
 M_n>2R_n\log_2 3+2S_n.
\tag{8.1}\label{long1049:eq:exact-jet-threshold}
```
Thus the least admissible integer rank is
``` math
M_{\min}(R,S)=
 \left\lfloor2R\log_2 3+2S\right\rfloor+1.
```
The checked condition $`M\ge4R+2S`$ for $`R>0`$ is a convenient sufficient corollary, not the exact threshold. Moreover, with $`N=2^{M_n}`$ and $`Q=3^{2R_n}2^{2S_n}`$, convexity of the fibre sizes gives at least
``` math
\frac12\left(\frac{N^2}{Q}-N\right)
\tag{8.2}\label{long1049:eq:collision-count}
```
unordered equal-signature selector pairs. A normality estimate can therefore win by showing that fewer than this many collision pairs land in the two bad nullspaces.

<div id="long1049:prob:escape" class="problem">

**Problem 38** (four-jet kernel escape). For one literal polynomially primitive family satisfying <a href="#long1049:eq:exact-jet-threshold" data-reference-type="eqref" data-reference="long1049:eq:exact-jet-threshold">[long1049:eq:exact-jet-threshold]</a>, prove, preferably by comparing the lower bound <a href="#long1049:eq:collision-count" data-reference-type="eqref" data-reference="long1049:eq:collision-count">[long1049:eq:collision-count]</a> with the bad-pair multiplicities, that
``` math
\mathcal C_n\mathbin{\backslash}
 \bigl(K_n^{\mathrm{poly}}\cup K_n^{\mathrm{rem}}\bigr)
 \ne\varnothing
```
for all sufficiently large $`n`$.

</div>

Theorem <a href="#long1049:res:jetkernel" data-reference-type="ref" data-reference="long1049:res:jetkernel">20</a> supplies only $`\mathcal C_n\ne\varnothing`$. It gives a nonzero selector difference, but it gives neither polynomial-pair nonvanishing nor remainder nonvanishing. Problem <a href="#long1049:prob:escape" data-reference-type="ref" data-reference="long1049:prob:escape">38</a> is finite algebra and normality; it makes no asymptotic product-formula claim. It is the first of the two gates in Problem <a href="#long1049:prob:kernel" data-reference-type="ref" data-reference="long1049:prob:kernel">37</a>: it asks for the two nonvanishing conclusions, and not for the analytic condition stated there.

<a id="determinant-families"></a>

## Determinant families

An exploratory calculation suggests a contiguous $`a_0`$-shift determinant at $`r_n=13n+2`$, after apparent failure of lower ranks $`r\le13n+1`$. These computations are not Lean theorems. More importantly, no literal definition of the matrix $`A_{n,r}`$ is given here, so writing merely “$`\det A_{n,13n+2}\ne0`$” would not yet be a public mathematical question.

<div class="problem">

**Problem 39** (the first saturated determinant). Give the entrywise formula for the contiguous $`a_0`$-shift matrix $`A_{n,r}`$, the exact relation $`M_n=M(n,r)`$ between its size and the number of coefficient pairs, and the declared width $`W_n`$. Then determine whether
``` math
\det A_{n,13n+2}\ne0
```
for every sufficiently large $`n`$. At the first computable scales, report the rank, determinant, coefficient-pair contents, specialised row contents, four endpoint jets, and the first nonzero remainder coefficient. A negative answer must identify a systematic rank relation or the first exact failing $`n`$.

</div>

This formulation makes the matrix definition part of the problem statement. No undeclared notation is relied on.

<div class="problem">

**Problem 40** (minimal non-$`a_0`$ deformation). If the saturated contiguous family collapses, enlarge it by exactly one $`a_1`$-shift while retaining the same source cone and widths. Does this one-direction extension increase the polynomial-pair rank and produce a collision outside $`K_n^{\mathrm{poly}}\cup K_n^{\mathrm{rem}}`$? If every such one-shift extension collapses, prove that class-wide obstruction before adding a second new direction.

</div>

This is the smallest specified deformation beyond the contiguous family; it replaces the unbounded request for a “genuinely independent deformation.”

<a id="asymptotic-adequacy-after-kernel-escape"></a>

## Asymptotic adequacy after kernel escape

Suppose a good collision has been found. Let $`D_n=3^{R_n}2^{S_n}`$ be the certified local divisor (or replace it by the exact determinant-specific divisor), let $`H_n`$ be the coefficient or exterior height after precisely the normalisation just declared, and let $`L_n\ne0`$ be the resulting analytic form or exterior remainder.

<div class="problem">

**Problem 41** (negative normalised product-formula margin). Prove the explicit estimate
``` math
\limsup_{n\to\infty}
 \frac{\log H_n+\log|L_n|-R_n\log3-S_n\log2}{n^2}<0.
\tag{8.3}\label{long1049:eq:negative-margin}
```
Every denominator, row content and final-combination content must already be included in $`H_n`$ and $`L_n`$.

</div>

Nonvanishing alone does not address <a href="#long1049:eq:negative-margin" data-reference-type="eqref" data-reference="long1049:eq:negative-margin">[long1049:eq:negative-margin]</a>. Conversely, excellent formal decay is irrelevant if every jet collision lies in a bad nullspace. The exploratory adjacent-exterior calculation leaves a positive normalised exponent of about $`110.850\,n^2`$; this is not a checked theorem. Any proposed improvement must remove this explicit deficit; extra divisibility alone is insufficient.

<a id="one-exact-alternative-criterion-test"></a>

## One exact alternative-criterion test

A separate possible method is Mahler’s method. Its first applicability test has an exact negative answer, which we record here; an earlier version of this note left it open.

<div id="long1049:res:nomahler" class="proposition">

**Proposition 42** (no finite simultaneous $`2/3`$-system). *Let
``` math
\mathcal L(z)=\sum_{n\ge1}\frac{z^n}{1-z^n}.
```
There is no finite-dimensional $`\mathbb{Q}(z)`$-vector space that contains $`\mathcal L`$ and is stable under both $`z\mapsto z^2`$ and $`z\mapsto z^3`$.*

</div>

<div class="proof">

*Proof.* Suppose $`V`$ were such a space, of dimension $`d`$. Stability under $`z\mapsto z^2`$ places the $`d+1`$ elements $`\mathcal L(z),\mathcal L(z^2),\dots,\mathcal
L(z^{2^{d}})`$ in $`V`$, so they are linearly dependent over $`\mathbb{Q}(z)`$; clearing denominators gives polynomials $`P_0,\dots,P_d`$, not all zero, with $`\sum_{i=0}^{d}P_i(z)\mathcal L(z^{2^i})=0`$. Thus $`\mathcal L`$ is $`2`$-Mahler, and the same argument under $`z\mapsto z^3`$ makes it $`3`$-Mahler. Since $`2`$ and $`3`$ are multiplicatively independent, a theorem of Adamczewski and Bell \[adamczewskibell2013, Theorem 1\] then forces $`\mathcal L`$ to be a rational function. That contradicts Rivin’s periodic-coefficient corollary \[rivin2026, Cor. 6.4, p. 9\], by which $`\mathcal L`$ is not rational. ◻

</div>

The proposition uses no property of the point $`2/3`$: the obstruction is functional and appears before regularity at a particular point is considered. It closes the simultaneous route only. It says nothing about a single $`k`$-Mahler system, about $`q`$-difference or Mahler-type arguments that do not require stability under two multiplicatively independent substitutions, or about special-value theorems reached by other means. Neither ingredient is proved here; both are cited.

<a id="the-quantitative-height-limitation"></a>

## The quantitative height limitation

The module `HermitePadeNoGo` defines an explicit rectangular two-parameter exponent model. Writing $`\sigma=1+\rho+u`$, its denominator-cleared gap has the exact expansion
``` math
-\pi^2\rho^2-\pi^2\rho u-2\pi^2\rho-2\rho^2-10\rho u
 -4\rho-6u^2-8u.
```
Thus for $`\rho\ge0`$ and $`\sigma\ge1+\rho`$ the cleared gap is nonpositive, and it vanishes exactly when $`\rho=0`$ and $`\sigma=1`$ ([exact expansion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L48), [nonpositivity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L58), [equality case](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L75)). Equivalently, within that model the displayed threshold never exceeds the classical one-function margin, with equality only at the classical endpoint ([bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L103), [equality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos1049/HermitePadeNoGo.lean#L126)). This is an algebraic theorem about the four defined exponent expressions and only that explicit rectangular model. It does not construct polynomials, remainders, integrality, a determinant, or asymptotics, and it is not a method-universal no-go theorem. The separate $`81/200`$ cutoff of the preceding section satisfies
``` math
\frac{81}{200}<\frac{\log2}{\log3}.
```
Thus “improve the height theorem” has a precise numerical target.

<div class="problem">

**Problem 43** (optimal admissible height threshold). Specify a concrete class $`\mathcal A`$ of primitive, noncollapsed constructions, excluding scalar row rescaling, proportional permutation-orbit forms, pure row-content gain, and constructions governed by the rectangular exponent model above. For that class define
``` math
\theta_*=\sup_{\alpha\in\mathcal A}
   \frac{C_0(\alpha)}{C_1(\alpha)}.
```
Prove one of the following: $`\theta_*>81/200`$ by an explicit construction; an exact value for $`\theta_*`$; a converse $`\theta_*<\log2/\log3`$; or a class theorem showing that every member reduces to one of the checked scalar or rectangular no-go mechanisms.

</div>

Reaching $`3/2`$ requires a threshold strictly beyond $`\log2/\log3\approx0.6309`$; exceeding $`81/200=0.405`$ is insufficient. The unrestricted question of which rational bases give irrational values remains open and is not reduced to any one of these problems.

<a id="statements-and-declarations"></a>

## Statements and declarations

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

The [pinned formal-source revision](https://github.com/wcook04/plectis-lean-erdos249-257/tree/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334) contains the Lean sources, the fixed toolchain, and the library manifest used in the verification. Proof authority rests in those pinned sources. The present text is exposition and navigation.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.

<a id="acknowledgements."></a>

#### Acknowledgements.

The problem numbering and status follow the Erdős Problems catalogue maintained by Thomas Bloom \[erdosproblems\].

<a id="long1049:app:index"></a>

# Guide to the formal sources

Each linked phrase opens its Lean declaration at the pinned source revision 92b88dc1bbe0. The declarations of this note live in nine modules: `RationalBaseLambert`, `QAperyDiagonalNonEquivalence`, `RationalPadeArithmetic`, `ZudilinConeArithmetic`, `ZudilinHeightRegion`, `HermitePadeNoGo`, `BezoutPluckerJets`, `AdelicHeightBridge`, and `RationalBaseContour`. The first contains the corridor, cleared-tail recurrence, and elementary $`7/2`$ certificate; the second checks the finite $`n=0`$ diagonal residual; the next five separate the Padé exponent arithmetic, endpoint arithmetic, logarithmic comparisons, rectangular exponent model, Bézout–Plücker tail collapse, power certificates, charge comparisons, four-jet counting and the Hankel assembly; the last holds the constant, its rational bracket and the degree bookkeeping. The link coordinates are validated against that pinned revision, so they remain correct as later work moves lines in the working tree.

The finite arithmetic behind the rational bracket $`81/200<\theta^{*}<1/2`$ of Section <a href="#long1049:sec:regionbracket" data-reference-type="ref" data-reference="long1049:sec:regionbracket">2.5</a> and the integer degree bookkeeping of Section <a href="#long1049:sec:degrees" data-reference-type="ref" data-reference="long1049:sec:degrees">2.2</a> lives in a further module, `RationalBaseContour`, which the library root imports at the pinned revision 92b88dc1bbe0. Its declarations are linked at their line coordinates in those two sections.

<a id="four-jet-collision-family."></a>

#### Four-jet collision family.

For a modular tail whose every row is unimodular and whose adjacent minors vanish, all minors vanish, the sharper $`N<2^k`$ collision threshold applies, and at modulus $`2^S3^R`$ with $`R>0`$ the depth $`k\ge S+2R`$ suffices. These three statements are ordinary in this record; those Lean names are not in this checkout. Neither coordinate must be a unit; $`(2,3)`$ modulo six is an example.

<a id="sec:erdos-1049-complete-family-map"></a>

# Complete result-family map

This section places every registered family for this problem in the shared 70-family reader order. The five display bands control exposition only; the separate promotion state currently covers 6 families and is reported but does not hide or strengthen any family. Mathematical statements and evidence modes come from the public claim registry. Across all eight problems the public result-atom catalog contains 681 exact packet coordinates; this problem contributes 90. The recovered source catalog contains 682 rows; 1 row(s) belong to families absent from the current claim registry and remain disclosed as detached source rows. Catalog rows expose bounded statement excerpts plus full-source digests, not a claim that every complete packet statement is reproduced here.

<a id="rational-base-tail-recurrence"></a>

## Rational base tail recurrence

**Reader position.** 8 of 70; display band: front door. Formal editorial disposition: hold. These are separate classifications.

**Reader entry.** The exact rational-base cleared-tail recurrence exposes exponential denominator-base forcing absent at integer bases.

The exact rational-base cleared-tail recurrence exposes exponential denominator-base forcing absent at integer bases.

**Authority and reach.** Lean kernel; Comparator-selected; locally proved result; novelty unassessed.

**Exact boundary.** The recurrence is not derived from a rationality contradiction.

**Result-atom population.** 6 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** exact selected interface; 1 executable interface(s), 1 repository-registered selected result interface(s).

**Publication placement.** This family is also admitted to the short note.

<a id="seven-halves-irrationality"></a>

## Seven halves irrationality

**Reader position.** 14 of 70; display band: major result. Formal editorial disposition: hold. These are separate classifications.

**Reader entry.** Irrationality at 7/2 is obtained from an external analytic criterion whose elementary height hypothesis is checked in Lean.

Irrationality at 7/2 is obtained from an external analytic criterion whose elementary height hypothesis is checked in Lean.

**Authority and reach.** paper argument plus cited theorem and Lean arithmetic; paper plus external theorem.

**Exact boundary.** Comparator may check the height inequality, not the cited theorem application.

**Result-atom population.** 4 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** not applicable to comparator; 0 executable interface(s), 0 repository-registered selected result interface(s).

**Publication placement.** This family is also admitted to the short note.

<a id="endpoint-residues"></a>

## Endpoint residues

**Reader position.** 29 of 70; display band: mechanism. Formal editorial disposition: hold. These are separate classifications.

**Reader entry.** Endpoint residues at 2 and 3 exclude a common multiplier under unit-endpoint hypotheses.

Endpoint residues at 2 and 3 exclude a common multiplier under unit-endpoint hypotheses.

**Authority and reach.** Lean kernel; no-go result.

**Exact boundary.** Other local or cross-row arithmetic remains possible.

**Result-atom population.** 3 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** not selected for comparator; 0 executable interface(s), 0 repository-registered selected result interface(s).

**Publication placement.** This family is also admitted to the short note.

<a id="height-and-pade-arithmetic"></a>

## Height and pade arithmetic

**Reader position.** 47 of 70; display band: frontier. Formal editorial disposition: split. These are separate classifications.

**Reader entry.** For the explicit rectangular two-function exponent model, the cleared gap is nonpositive throughout rho \>= 0 and 1 + rho \<= sigma, and the threshold is at most 1/2 - 1/pi^2 with equality exactly at rho = 0, sigma = 1. The gap sign and unique-zero mechanism support this sharp threshold no-go within the wider height-and-Padé arithmetic family.

For the explicit rectangular two-function exponent model, the cleared gap is nonpositive throughout rho \>= 0 and 1 + rho \<= sigma, and the threshold is at most 1/2 - 1/pi^2 with equality exactly at rho = 0, sigma = 1. The gap sign and unique-zero mechanism support this sharp threshold no-go within the wider height-and-Padé arithmetic family.

**Authority and reach.** Lean kernel; Comparator-selected; locally proved sharp model-specific no-go; novelty unassessed.

**Exact boundary.** This is a sharp no-go only for the explicit rectangular two-function exponent model under the stated real hypotheses; it constructs no approximating polynomials or remainders and is not a universal Padé or Hermite-Padé no-go. It proves no irrationality at 3/2 or any general rational-base endpoint, and the analytic remainder/nonvanishing input remains untreated. No novelty, priority, significance, external-review, or endpoint claim is made; Erdős \#1049 remains open.

**Result-atom population.** 65 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** exact selected interface; 1 executable interface(s), 1 repository-registered selected result interface(s).

**Publication placement.** This family is also admitted to the short note.

- `ErdosProblems.Erdos1049.hpClearedGap_nonpos`

- `ErdosProblems.Erdos1049.hpClearedGap_eq_zero_iff`

- `ErdosProblems.Erdos1049.rectangular_hp_threshold_le_classical`

- `ErdosProblems.Erdos1049.rectangular_hp_threshold_eq_classical_iff`

<a id="coordinatewise-corridor-no-go"></a>

## Coordinatewise corridor no go

**Reader position.** 52 of 70; display band: frontier. Formal editorial disposition: hold. These are separate classifications.

**Reader entry.** The coordinatewise corridor forces a power-versus-linear inequality and cannot occur at base 3/2.

The coordinatewise corridor forces a power-versus-linear inequality and cannot occur at base 3/2.

**Authority and reach.** Lean kernel; Comparator-selected; no-go result.

**Exact boundary.** This excludes one proof architecture and proves no irrationality statement.

**Result-atom population.** 2 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** exact selected interface; 1 executable interface(s), 1 repository-registered selected result interface(s).

**Publication placement.** This family is also admitted to the short note.

<a id="scalar-content-no-go"></a>

## Scalar content no go

**Reader position.** 56 of 70; display band: frontier. Formal editorial disposition: hold. These are separate classifications.

**Reader entry.** Integer scalar content changes analytic error and exterior determinant by matching factors, yielding no margin by itself.

Integer scalar content changes analytic error and exterior determinant by matching factors, yielding no margin by itself.

**Authority and reach.** Lean kernel; no-go result.

**Exact boundary.** The conclusion is scoped to one normalisation strategy.

**Result-atom population.** 3 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** not selected for comparator; 0 executable interface(s), 0 repository-registered selected result interface(s).

**Publication placement.** This family is also admitted to the short note.

<a id="four-jet-collision"></a>

## Four jet collision

**Reader position.** 63 of 70; display band: technical support. Formal editorial disposition: hold. These are separate classifications.

**Reader entry.** Binary selectors collide in the four-jet signature at the stated rank and depth.

Binary selectors collide in the four-jet signature at the stated rank and depth.

**Authority and reach.** Lean kernel; locally proved result and no-go result; novelty unassessed.

**Exact boundary.** A signed relation is not nonzero analytic data.

**Result-atom population.** 7 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** not selected for comparator; 0 executable interface(s), 0 repository-registered selected result interface(s).

**Publication placement.** This family remains in the complete long record and is not a short-note headline.

<div class="thebibliography">

99

P. Erdős, [*On arithmetical properties of Lambert series*](https://users.renyi.hu/~p_erdos/1948-04.pdf), J. Indian Math. Soc. (N.S.) **12** (1948), 63–66. P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). P. B. Borwein, *On the irrationality of $`\sum1/(q^{n}+r)`$*, J. Number Theory **37** (1991), no. 3, 253–259, doi:[10.1016/S0022-314X(05)80041-1](https://doi.org/10.1016/S0022-314X(05)80041-1). P. B. Borwein, *On the irrationality of certain series*, Math. Proc. Cambridge Philos. Soc. **112** (1992), no. 1, 141–146, doi:[10.1017/S030500410007081X](https://doi.org/10.1017/S030500410007081X). Van Assche cites Lemma 2 for the neighbouring little-$`q`$-Legendre evaluation used above. T. Amdeberhan and D. Zeilberger, *$`q`$-Apéry irrationality proofs by $`q`$-WZ pairs*, Adv. Appl. Math. **20** (1998), no. 2, 275–283, [arXiv:math/9804122](https://arxiv.org/abs/math/9804122), doi:[10.1006/aama.1997.0565](https://doi.org/10.1006/aama.1997.0565). P. Bundschuh and K. Väänänen, [*Arithmetical investigations of a certain infinite product*](https://numdam.org/item/CM_1994__91_2_175_0.pdf), Compositio Math. **91** (1994), no. 2, 175–199. W. Zudilin, [*Heine’s basic transform and a permutation group for $`q`$-harmonic series*](https://geodesic.mathdoc.fr/articles/10.4064/aa111-2-4/), Acta Arith. **111** (2004), no. 2, 153–164, doi:10.4064/aa111-2-4. W. Zudilin, [*On the irrationality of generalized $`q`$-logarithm*](https://arxiv.org/abs/1601.02688), arXiv:1601.02688; Res. Number Theory **2** (2016), doi:[10.1007/s40993-016-0042-x](https://doi.org/10.1007/s40993-016-0042-x). The remark that the results extend to non-integer $`p=r/s`$, $`|p|>1`$, under an assumption $`\log|r|>c\log|s|`$ for a computable $`c>0`$, is at the end of Section 2; no value of $`c`$ is computed there, and the remark is made for the generalized $`q`$-logarithm of that paper. D. Duverney, [*À propos de la série $`\sum_{n\ge1}x^{n}/(q^{n}-1)`$*](https://numdam.org/item/JTNB_1996__8_1_173_0.pdf), J. Théor. Nombres Bordeaux **8** (1996), no. 1, 173–181. Théorème 2 on p. 174 gives the rational-base region $`\log|s|/\log|r|<\frac13(1-3/\pi^{2})=0.2320\ldots`$ for this series; Théorème 1, for a general numerator, is weaker. T. Matala-aho, K. Väänänen and W. Zudilin, [*New irrationality measures for $`q`$-logarithms*](https://doi.org/10.1090/S0025-5718-05-01812-0), Math. Comp. **75** (2006), no. 254, 879–889, doi:10.1090/S0025-5718-05-01812-0. The hypothesis $`p=1/q\in\mathbb{Z}\mathbin{\backslash}\{0,\pm1\}`$ is carried in the abstract on p. 879 and in both theorem statements on p. 880, where the authors also record that their methods do not sharpen the $`q`$-harmonic case of \[zudilin2004\]. B. Adamczewski and J. P. Bell, [*A problem about Mahler functions*](https://arxiv.org/abs/1303.2019), Ann. Sc. Norm. Super. Pisa Cl. Sci. **17** (2017), no. 4, 1301–1355; arXiv:1303.2019, 2013. Theorem 1: over a field of characteristic zero, a power series is both $`k`$- and $`\ell`$-Mahler for multiplicatively independent $`k,\ell`$ if and only if it is a rational function. G. Rhin and C. Viola, [*On a permutation group related to $`\zeta(2)`$*](https://geodesic.mathdoc.fr/articles/10.4064/aa-77-1-23-56/), Acta Arith. **77** (1996), no. 1, 23–56, doi:10.4064/aa-77-1-23-56. W. Van Assche, [*Little $`q`$-Legendre polynomials and irrationality of certain Lambert series*](https://arxiv.org/abs/math/0101187), Ramanujan J. **5** (2001), no. 3, 295–310, doi:[10.1023/A:1012930828917](https://doi.org/10.1023/A:1012930828917). J. Vandehey, [*On an incomplete argument of Erdős on the irrationality of Lambert series*](https://arxiv.org/abs/1206.0340), Integers **13** (2013), Paper A58. F. Luca and Y. Tachiya, [*Linear independence results for the values of divisor functions series*](https://www.kurims.kyoto-u.ac.jp/~kyodo/kokyuroku/contents/pdf/2014-14.pdf), RIMS Kôkyûroku No. 2014 (2017), 138–150. Theorem A on p. 139 restates the periodic-coefficient irrationality theorem; Example 1 on p. 140 gives the divisor-function specialization. I. Rivin, [*Zero Coefficients of Rational Power Series and Rational Lambert Series*](https://arxiv.org/abs/2604.25151), arXiv:2604.25151v1, 2026. Theorem 1.1 is on p. 2 and proved on pp. 6–7; the periodic-coefficient Corollary 6.4 is on p. 9. V. Kovač and T. Tao, [*On several irrationality problems for Ahmes series*](https://arxiv.org/abs/2406.17593), Acta Math. Hungar. **175** (2025), 572–608; arXiv:2406.17593, 2024. T. F. Bloom, [*Erdős Problem \#1049*](https://www.erdosproblems.com/1049), `erdosproblems.com/1049`, accessed 28 July 2026 (page displays “last edited 28 September 2025”). The current record labels the problem open, cites <span class="upright">\[Er88c, p. 102\]</span> and <span class="upright">\[Er48\]</span>, and explicitly describes its status as the website owner’s present assessment, with no guarantee of literature completeness. The Formal Conjectures Authors, [*FormalConjectures.ErdosProblems.`1049`*](https://github.com/google-deepmind/formal-conjectures/blob/f776d2f2039351b00737ffcafb9d7d7666e1d9af/FormalConjectures/ErdosProblems/1049.lean), Lean source at commit `f776d2f`, 2026, accessed 28 July 2026. The irrationality declarations are unproved; the Lambert-series identity is proved.

</div>
