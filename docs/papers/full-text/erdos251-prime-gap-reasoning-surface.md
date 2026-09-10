<a id="erdos251-prime-gap-reasoning-surface"></a>

# Prime Gaps and Dyadic Tails: Complete Reasoning Record

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

Let $`p_0=2,p_1=3,\ldots`$ enumerate the primes and let $`g_n=p_{n+1}-p_n`$. Both dyadic series converge and
``` math
\Pi=\sum_{n\ge0}\frac{p_n}{2^{\,n+1}}
 \;=\;2+\sum_{n\ge0}\frac{g_n}{2^{\,n+1}}\;=\;2+S .
```
The identity is exact, carries no hypothesis, and rests on the elementary polynomial bound $`p_n\le1250(n+1)^4`$ proved in Appendix <a href="#long251:app:prime-bound" data-reference-type="ref" data-reference="long251:app:prime-bound">9</a>. The prime number theorem is not used. Everything after it is negative knowledge or an exact reformulation, and each statement is labelled by what it is.

Write $`T_N=\sum_{j\ge1}g_{N+j}2^{-j}`$ for the scaled tails, so that $`T_{N+1}=2T_N-g_{N+1}`$. Irrationality of $`\Pi`$ is equivalent to nonintegrality of every positive tail shift $`T_{N+h}-T_N`$, and equivalently to the free-pair condition that for every modulus $`t`$ and every cutoff some pair of indices congruent modulo $`t`$ beyond the cutoff has nonintegral tail difference. Two adjacent shifts in $`(-1,1)`$ with unequal corresponding gaps cannot both be integral, and an explicit remainder bound certifies one such pair at $`h=1`$, $`N=2`$ by exact integer arithmetic. Every rational equal to $`\Pi`$, and hence every rational equal to $`S`$, has denominator at least $`2^{589}>10^{177}`$ by a certificate the Lean kernel decides, and at least $`2^{39997}>10^{12040}`$ by a certified continued-fraction prefix.

Four proved statements constrain any argument. Raising every gap by at most $`M`$ beyond a prescribed prefix, preserving each residue modulo $`M`$, already makes the sum rational. That rationalising perturbation inherits the fixed-block polynomial nonconcentration property which Schlage-Puchta proved for the actual gaps, so nonconcentration together with prefix, size, residue and cumulative-growth data still permits a rational value. Under the two window conditions the gap mismatch is forced to be $`\pm2`$, and by the same nonconcentration lemma that event has density zero, so the missing input is a cofinality statement on a sparse set. Finally, two even values differing by $`2`$, each recurring infinitely often inside every index residue class, do not force irrationality: an explicit positive even word of prime-number-theorem cumulative growth has both values recurring and an integral tail at every index. Problem #251 remains open, and the exact unproved input is cofinal nonintegrality of the actual prime-gap tail shifts.

<div class="center">

<div class="minipage">

------------------------------------------------------------------------

**The exact identity, the finite exclusions, and the open boundary**

**Exact identity.** The prime-index dyadic series equals two plus the consecutive-prime-gap dyadic series, unconditionally, with summability and the identity checked by the Lean kernel over an elementary polynomial prime bound. **Denominator floors.** Every rational equal to either series has denominator at least $`2^{589}>10^{177}`$ by a kernel-decided certificate, and at least $`2^{39997}>10^{12040}`$ by a certified continued-fraction prefix. **Exact criteria.** Irrationality is equivalent to cofinal nonintegrality of every fixed positive tail shift, to the free-pair condition with the offset free, and to nonintegrality along the lcm diagonal. **Proved obstructions.** Bounded residue-preserving perturbations make the sum rational; that perturbation inherits fixed-block polynomial nonconcentration; the two-window event forces a $`\pm2`$ mismatch and therefore has density zero; and recurring gap values differing by $`2`$ inside every residue class are compatible with an integral tail at every index. **Open boundary.** No result here proves cofinal nonintegrality for the actual prime gaps or irrationality of either series, and Erdős #251 remains open.

</div>

</div>

<a id="long251:sec:problem"></a>

# Introduction

Let $`p_n`$ denote the $`n`$th prime. Erdős Problem #251 asks whether
``` math
\Pi=\sum_{n\ge1}\frac{p_n}{2^{\,n}}
```
is irrational \[erdos1958, p. 94\]\[erdosgraham1980, p. 62\] \[erdos1988, p. 103\]. Bloom’s catalogue records the problem as open \[erdosproblems\]. Numerically $`\Pi=2/2+3/4+5/8+7/16+11/32+\cdots=3.674643966\ldots`$.

Throughout the formal development the primes are indexed from zero, so that $`p^{(0)}_0=2`$, $`p^{(0)}_1=3`$, $`p^{(0)}_2=5`$, and the gaps are $`g_i=p^{(0)}_{i+1}-p^{(0)}_i`$. In that indexing
``` math
\Pi=\sum_{i\ge0}\frac{p^{(0)}_i}{2^{\,i+1}} ,
```
which is the convention every statement below uses; we drop the superscript from here on. The first values are
``` math
\begin{array}{c|cccccccccc}
  i   & 0&1&2&3&4 &5 &6 &7 &8 &9\\\hline
  p_i & 2&3&5&7&11&13&17&19&23&29\\
  g_i & 1&2&2&4&2 &4 &2 &4 &6 &2
 \end{array}
```
so $`g_0=1`$ and every later gap is even, the primes after $`2`$ being odd. A second normalisation with denominator $`2^{\,i}`$ also occurs, and at every finite horizon it is exactly twice this one,
``` math
\sum_{i=0}^{n-1}\frac{p_i}{2^{\,i}}
 =2\sum_{i=0}^{n-1}\frac{p_i}{2^{\,i+1}} ,
```
the [factor-of-two normalisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L111). A factor of two does not change rationality, so no result below depends on the choice; the identity is stated so that the indexing cannot drift silently.

<a id="notation."></a>

#### Notation.

$`\mathbb{N}=\{0,1,2,\ldots\}`$ and $`\mathbb{N}_{>0}=\{1,2,\ldots\}`$. We write $`\varphi`$ for Euler’s totient function, $`\operatorname{den}q`$ for the denominator of a rational number $`q`$ written in lowest terms, $`\operatorname{dist}(x,\mathbb{Z})`$ for the distance from a real number $`x`$ to the nearest integer, and $`\operatorname{Irr}(x)`$ for the assertion that $`x`$ is irrational. A rational number is called *integral* when it is the image of an integer. A sequence $`(a_n)`$ is *eventually periodic with period $`h\ge1`$* when $`a_{n+h}=a_n`$ for every sufficiently large $`n`$. A set $`A\subseteq\mathbb{N}`$ has *density zero* when $`|A\cap[1,x]|=o(x)`$, and a property holds for *almost all* indices when its exceptional set has density zero. A sum over an empty range of indices is zero.

<a id="relation-to-prior-work."></a>

#### Relation to prior work.

The passage from the primes to their gaps is already public. Tao recorded on the problem page that summation by parts makes the question equivalent to irrationality of $`\sum_n(p_{n+1}-p_n)2^{-n}`$, and named the shape of the missing input as a sufficiently quantitative and uniform prime-tuples hypothesis giving statistical control of the binary expansion of about $`\log\log n`$ consecutive gaps \[erdosproblems251thread, comment of 7 October 2025\]. Theorem <a href="#long251:res:infinite" data-reference-type="ref" data-reference="long251:res:infinite">3</a> below is that reduction in exact form, with the endpoint retained, with convergence supplied by an elementary bound, and with the statement checked by the Lean kernel. The elementary bound replaces the prime number theorem. No priority is claimed for the reduction.

Land has since posted a conditional proof of irrationality assuming Kuperberg’s uniform Hardy-Littlewood prime-tuples conjecture, together with a Lean formalisation of that conditional argument \[land2026, Conjecture 1 and §1\]. His route constructs weighted prime-gap tails converging to $`6`$ from above, imposes a consecutive quadratic prime pattern by a mixed prime-counting moment, and averages over later prime indices to control the unprescribed tail. Nothing in this note is conditional on a prime-tuples hypothesis, and nothing in this note proves the unconditional statement his argument would need.

Erdős stated on p. 93 of the 1958 article that $`\sum_n p_n^{k}/n!`$ is irrational for every $`k\ge1`$, and wrote there that the proof for $`k>1`$ is complicated enough that only the case $`k=1`$ is printed \[erdos1958, pp. 93–95\]. A proof of the full family appears in Schlage-Puchta’s Theorem 3, which gives the stronger statement that $`1,S_0,S_1,S_2,\ldots`$ are linearly independent over $`\mathbb{Q}`$, where $`S_k=\sum_{n\ge1}p_n^{k}/n!`$ \[schlagepuchta2011, Theorem 3\]. The catalogue entry still attributes the whole family to the 1958 article \[erdosproblems\].

On page 103 of his 1988 problem paper Erdős separately stated the fixed-denominator problem: he could not prove that $`\sum_n p_n^{k}/2^{n}`$ is irrational for every $`k\ge1`$, and wrote that the case $`k=1`$ was probably already very difficult. He also stated the variable-denominator expectation that $`\sum_{n\ge1}p_n/(g_1\cdots g_n)`$ is irrational whenever $`g_n\ge2`$ and $`g_n=o(p_n)`$ \[erdos1988, p. 103\]. That expectation is false: Kovač posted a construction of such a sequence $`(g_n)`$ for which the sum is exactly $`1`$, on 15 April 2026 \[kovac2026, Theorem 1 and proof, pp. 1–2\]. The catalogue record still repeats the refuted expectation without mentioning the counterexample, as checked on 6 September 2026 \[erdosproblems\]; its warning that relevant literature may be missing applies directly to this omission.

Section 3 of the 1958 article proves a classification for the variable-denominator family, and the hypotheses matter. Let $`1<q_1\le q_2\le\cdots`$ be integers satisfying, for some $`k>0`$, the lower growth condition $`q_n>o(n/\log^{k}n)`$. Then $`\sum_{n\ge1}p_n/(q_1\cdots q_n)`$ is rational if and only if $`q_n=q\,p_n+1`$ for one fixed integer $`q\ge1`$ and all large $`n`$ \[erdos1958, pp. 96–97\]. The denominators are nondecreasing, and the printed condition bounds them from below. Strict increase is not assumed, and no upper bound is imposed. The endpoint $`q=1`$ is attained: if $`G_n=\prod_{j=1}^{n}(p_j+1)`$ then $`p_n/G_n=1/G_{n-1}-1/G_n`$, so the corresponding series telescopes to $`1`$. Kovač’s sequence evades the lower growth condition, and neither statement addresses the fixed-denominator dyadic series studied here.

There is also a genuinely adjacent proved dyadic theorem. If $`P(m)`$ denotes the largest prime factor of $`m`$, Erdős and Pomerance proved that
``` math
\sum_{m\ge2}\frac{\mathbf 1_{\{P(m)>P(m+1)\}}}{2^m}
```
is irrational \[erdospomerance1978, §7, p. 320\]. Erdős and Graham record the complementary indicator on p. 62: equality of the two largest prime factors is impossible for consecutive integers, so its series is $`1/2`$ minus the displayed one and is irrational as well. That is a theorem about a bounded prime-factor comparison digit sequence, and the numerators in $`\Pi`$ are unbounded.

Two further results of Schlage-Puchta enter below. His Theorem 2 classifies rationality for numbers whose base-$`b`$ digit string concatenates the representations of a slowly growing integer sequence, and is a different object from the tail criterion here; it was already pointed at this problem in the catalogue thread on 15 April 2026. His Lemma 4 is the input this note actually uses. It states that for every polynomial $`F\in\mathbb{Z}[x_0,\ldots,x_k]`$ which does not vanish identically, $`F(g_n,\ldots,g_{n+k})\ne0`$ for almost all $`n`$, where $`g_n`$ are the actual consecutive prime gaps \[schlagepuchta2011, Lemma 4, pp. 5–6\]. Its proof runs through Selberg’s sieve. Sections <a href="#long251:sec:obstructions" data-reference-type="ref" data-reference="long251:sec:obstructions">6</a> draws two consequences from it.

Problem #251 also appears as the unproved declaration `erdos_251` in the *Formal Conjectures* repository \[formalconjectures251\]. Its zero-based Lean sum starts with the zeroth prime over $`2^0`$, so it is twice the displayed normalisation and has equivalent irrationality status; its proof is `sorry`.

<a id="the-strategy."></a>

#### The strategy.

The digits $`p_n`$ grow, so the series is not a digit expansion in any bounded alphabet, and the standard rationality criteria for such expansions do not apply directly. The classical elementary criteria for series of this kind instead control irrationality through the growth of the denominators. Erdős and Straus named a sum $`\sum_k 1/a_k`$ over a strictly increasing sequence of positive integers an *Ahmes series* \[erdosstraus1963\]; for such a series the condition $`a_k^{1/2^k}\to\infty`$ is sufficient for irrationality, and it is sharp, since shifted Sylvester sequences grow like $`C^{2^{k}}`$ for arbitrarily large $`C`$ and have rational reciprocal sum. Both statements and their attribution are recorded in the introduction of Kovač and Tao \[kovactao2024, §1\]. Splitting each term $`p_i/2^{\,i+1}`$ into $`p_i`$ copies of $`2^{-(i+1)}`$ writes $`\Pi`$ as a sum of unit fractions with repetitions, and the denominators occurring in it are exactly the powers of two. Even ignoring the repetitions the growth hypothesis fails by every available margin, since $`(2^{\,n})^{1/2^{\,n}}\to1`$, and every arithmetic constraint has to come from the numerators instead.

What replaces growth control is denominator control on the sequence of rescaled tails. Rationality of the sum is equivalent to an eventual integrality condition on differences of those tails, and that condition uses nothing about the numerators beyond the fact that they are integers. The condition does not by itself force the numerators to repeat: Proposition <a href="#long251:res:telescope" data-reference-type="ref" data-reference="long251:res:telescope">25</a>, applied to $`K_n=n`$, produces the integer sequence $`\kappa_n=n-1`$, which is unbounded and hence not eventually periodic, and whose dyadic sum is zero.

<a id="outline."></a>

#### Outline.

Section <a href="#long251:sec:parts" data-reference-type="ref" data-reference="long251:sec:parts">2</a> proves the identity and the irrationality equivalence. Section <a href="#long251:sec:tail" data-reference-type="ref" data-reference="long251:sec:tail">3</a> develops the tail recurrence and states the three exact criteria: pointwise shift escape, the free-pair form with a free offset, and the lcm diagonal. Section <a href="#long251:sec:local-certificate" data-reference-type="ref" data-reference="long251:sec:local-certificate">4</a> gives the local obstruction, its signed normal form, the explicit remainder bound and one certified actual pair. Section <a href="#long251:sec:denominator-floor" data-reference-type="ref" data-reference="long251:sec:denominator-floor">5</a> records the two denominator floors. Section <a href="#long251:sec:obstructions" data-reference-type="ref" data-reference="long251:sec:obstructions">6</a> proves the four obstructions. Section <a href="#long251:sec:measurements" data-reference-type="ref" data-reference="long251:sec:measurements">7</a> reports the two finite measurements. Section <a href="#long251:sec:open" data-reference-type="ref" data-reference="long251:sec:open">8</a> states the remaining obligation. All declarations linked below are checked by the Lean 4 kernel against the pinned Mathlib revision at the formal-source commit ee650b32b8b2, and the pinned sources contain no proof placeholders and no project-defined axioms. The cited system paper identifies Lean 4 \[lean4, abstract and §1, pp. 625–626\], while the Mathlib paper documents the library’s historical Lean 3-era architecture \[mathlib, abstract and §1.1, p. 367\]; it is not authority for the current pinned revision.

*Status.* The problem treated here is open, and this note does not close it. Every statement below marked as checked is a proposition that the pinned Lean kernel accepts from the sources this note links to, with no `sorry`, no added axiom, and no unchecked evaluation. That is a claim about the formal statement, not about its mathematical interest, its novelty, or the original problem. The unresolved obligations are named exactly, in their own section, and none of the finite computations, reductions, or no-go results here removes one of them.

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.

| Statement | Status | Treatment here |
|:---|:---|:---|
| Irrationality of $`\Pi`$ | Open | Not proved. |
| Finite prime-gap identity | Proved here | Theorem <a href="#long251:res:parts" data-reference-type="ref" data-reference="long251:res:parts">2</a>, with the endpoint retained. |
| Infinite prime-gap identity | Lean-checked unconditionally | Theorem <a href="#long251:res:infinite" data-reference-type="ref" data-reference="long251:res:infinite">3</a>. |
| Prime-series/gap-series irrationality equivalence | Lean-checked unconditionally | Corollary <a href="#long251:res:irr-equivalence" data-reference-type="ref" data-reference="long251:res:irr-equivalence">4</a>. |
| Elementary polynomial prime bound $`p_n\le1250(n+1)^4`$ | Lean-checked; proof reprinted here | Appendix <a href="#long251:app:prime-bound" data-reference-type="ref" data-reference="long251:app:prime-bound">9</a>. |
| Actual real prime-gap tail and its recurrence | Lean-checked unconditionally | Section <a href="#long251:sec:tail" data-reference-type="ref" data-reference="long251:sec:tail">3</a>. |
| Rationality/integral-shift classification | Lean-checked; an equivalence | Theorem <a href="#long251:res:escape-irrational" data-reference-type="ref" data-reference="long251:res:escape-irrational">7</a>. |
| Free-pair irrationality criterion | Lean-checked; an equivalence | Theorem <a href="#long251:res:freepair" data-reference-type="ref" data-reference="long251:res:freepair">8</a>. |
| Lcm-diagonal irrationality criterion | Lean-checked; an equivalence | Theorem <a href="#long251:res:lcmdiagonal" data-reference-type="ref" data-reference="long251:res:lcmdiagonal">9</a>. |
| Adjacent small-shift obstruction, rational and real | Lean-checked | Theorem <a href="#long251:res:smallpair" data-reference-type="ref" data-reference="long251:res:smallpair">10</a>, Corollary <a href="#long251:res:smallpair-real" data-reference-type="ref" data-reference="long251:res:smallpair-real">11</a>. |
| Signed two-window normal form | Lean-checked; an equivalence | Theorem <a href="#long251:res:signedwindow" data-reference-type="ref" data-reference="long251:res:signedwindow">13</a>. |
| Explicit remainder bound and the certified pair at $`h=1`$, $`N=2`$ | Ordinary proof; exact integer replay in Appendix <a href="#long251:app:certificates" data-reference-type="ref" data-reference="long251:app:certificates">10</a> | Propositions <a href="#long251:res:explicit-remainder" data-reference-type="ref" data-reference="long251:res:explicit-remainder">14</a> and <a href="#long251:res:finite-smallpair" data-reference-type="ref" data-reference="long251:res:finite-smallpair">15</a>. |
| Denominator floor $`b\ge2^{589}`$ | Lean-checked by `decide +kernel`; ordinary proof reprinted here | Theorem <a href="#long251:res:denominatorfloor" data-reference-type="ref" data-reference="long251:res:denominatorfloor">16</a>. |
| Certified continued-fraction exclusion $`q\ge2^{39997}`$ | Exact computation over a Lean-checked tail bound | Theorem <a href="#long251:res:cfexclusion" data-reference-type="ref" data-reference="long251:res:cfexclusion">17</a>; no Lean declaration. |
| Bounded-perturbation obstruction | Lean-checked | Theorem <a href="#long251:res:boundedperturbation" data-reference-type="ref" data-reference="long251:res:boundedperturbation">18</a>. |
| Nonconcentration survives the rationalising perturbation | Ordinary proof; external lemma cited | Theorem <a href="#long251:res:nonconcentration" data-reference-type="ref" data-reference="long251:res:nonconcentration">20</a> and Corollary <a href="#long251:res:nonconc-primes" data-reference-type="ref" data-reference="long251:res:nonconc-primes">21</a>. |
| The two-window event has density zero | Ordinary proof; external lemma cited | Theorem <a href="#long251:res:sparse" data-reference-type="ref" data-reference="long251:res:sparse">22</a>. |
| Recurring gap values differing by $`2`$ do not suffice | Ordinary proof | Theorem <a href="#long251:res:polignacfail" data-reference-type="ref" data-reference="long251:res:polignacfail">23</a>. |
| Quadratic polynomial-shift countermodel | Lean-checked | Proposition <a href="#long251:res:polynomialcountermodel" data-reference-type="ref" data-reference="long251:res:polynomialcountermodel">24</a>. |
| Rationality alone forces periodic integer coefficients | False | Proposition <a href="#long251:res:telescope" data-reference-type="ref" data-reference="long251:res:telescope">25</a>. |
| Affine and fixed-lattice cofinal escape tests | Lean-checked; both equivalences | Theorem <a href="#long251:res:affinecollapse" data-reference-type="ref" data-reference="long251:res:affinecollapse">26</a>. |
| Actual prime gaps are unbounded and not eventually periodic | Lean-checked | Proposition <a href="#long251:res:gap-nonperiodic" data-reference-type="ref" data-reference="long251:res:gap-nonperiodic">12</a>. |
| Adjacent-mismatch event density below $`1.2\times10^{8}`$ | Finite measurement, floating-point tails | Section <a href="#long251:sec:measurements" data-reference-type="ref" data-reference="long251:sec:measurements">7</a>. |
| Free-pair witnesses for every $`t\le20`$ below $`2\times10^{7}`$ | Finite measurement | Section <a href="#long251:sec:measurements" data-reference-type="ref" data-reference="long251:sec:measurements">7</a>. |
| Cofinal adjacent small mismatch | Sufficient condition; not proved | Problem <a href="#long251:prob:smallpair" data-reference-type="ref" data-reference="long251:prob:smallpair">28</a>. |

**Keywords.** irrationality; prime gaps; dyadic series; summation by parts; Lean 4. **MSC 2020.** 11J72 (primary); 11N05, 68V20 (secondary).

<a id="long251:sec:parts"></a>

# Summation by parts, with the endpoint retained

Summation by parts trades a sequence for its consecutive differences. The form recorded here is exact: it carries no error term, it assumes nothing about the sequence, and it retains the endpoint term. No endpoint is absorbed into an estimate. For a sequence $`P`$ of rational numbers and $`n\ge0`$ put
``` math
D(P,n)=\sum_{i=0}^{n-1}\frac{P(i)}{2^{\,i+1}},
 \qquad
 \Delta(P,n)=\sum_{i=0}^{n-1}\frac{P(i+1)-P(i)}{2^{\,i+1}} ,
```
both empty, hence zero, at $`n=0`$. We call these the [dyadic partial sum](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L101) and the [dyadic difference sum](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L121) of $`P`$.

<div id="long251:res:abel" class="proposition">

**Proposition 1** (finite summation by parts). *For every rational sequence $`P`$ and every $`n\ge0`$,
``` math
D(P,n+1)=P(0)+\Delta(P,n)-\frac{P(n)}{2^{\,n+1}} .
```*

</div>

<div class="proof">

*Proof.* A routine induction on $`n`$. At $`n=0`$ both sides equal $`P(0)/2`$. For the step, adding $`P(n+1)/2^{\,n+2}`$ to the left and $`\bigl(P(n+1)-P(n)\bigr)/2^{\,n+1}`$ to the difference sum changes the endpoint term from $`P(n)/2^{\,n+1}`$ to $`P(n+1)/2^{\,n+2}`$, and the two adjustments agree. ◻

</div>

Formalised as the [summation-by-parts identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L138). Nothing is assumed about $`P`$: no positivity, no monotonicity, and no convergence.

Specialising to $`P(i)=p_i`$, whose first value is $`p_0=2`$, and writing $`g_i=p_{i+1}-p_i`$ for the zero-based gaps, gives the reformulation.

<div id="long251:res:parts" class="theorem">

**Theorem 2** (prime-gap reformulation). *Let $`p_0=2,p_1=3,\ldots`$ be the primes in increasing order and $`g_i=p_{i+1}-p_i`$. For every $`n\ge0`$,
``` math
\sum_{i=0}^{n}\frac{p_i}{2^{\,i+1}}
 =2+\sum_{i=0}^{n-1}\frac{g_i}{2^{\,i+1}}-\frac{p_n}{2^{\,n+1}} .
```*

</div>

Formalised as the [prime-gap summation by parts](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L172), using the [gap partial sum](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L161) and the [gap cast identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L156); the latter records that the natural-number difference $`p_{n+1}-p_n`$ agrees with the difference taken in $`\mathbb{Q}`$, which needs $`p_n\le p_{n+1}`$, the [monotonicity step](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L152). The leading $`2`$ is the first prime, not a normalising constant. At $`n=2`$, for instance, the left side is $`2/2+3/4+5/8=19/8`$ and the right side is $`2+(1/2+2/4)-5/8=19/8`$.

<a id="long251:sec:infinite"></a>

## The infinite identity and the irrationality equivalence

Write
``` math
u_n=\frac{p_n}{2^{\,n+1}},\qquad
 v_n=\frac{g_n}{2^{\,n+1}}
```
for the terms of the prime series and of the gap series, so that $`\sum_{n\ge0}u_n=\Pi`$. The termwise identity $`v_n=2u_{n+1}-u_n`$ is the [dyadic discrete derivative](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L202). It expresses each gap term as an integer combination of two consecutive prime terms, so once $`(u_n)`$ is summable the gap series can be summed by rearranging two copies of the prime series.

<div id="long251:res:infinite" class="theorem">

**Theorem 3** (infinite prime-gap identity). *Both series converge and
``` math
\sum_{n\ge0}\frac{p_n}{2^{\,n+1}}
 \;=\;2+\sum_{n\ge0}\frac{g_n}{2^{\,n+1}} .
```*

</div>

<div class="proof">

*Proof.* The bound $`p_n\le1250(n+1)^4`$ of Appendix <a href="#long251:app:prime-bound" data-reference-type="ref" data-reference="long251:app:prime-bound">9</a> makes $`(u_n)`$ summable, and $`0<g_n\le p_{n+1}`$ then makes $`(v_n)`$ summable. The shifted sequence $`(u_{n+1})`$ is summable, so summing $`v_n=2u_{n+1}-u_n`$ and using $`u_0=1`$ gives
``` math
\sum_{n\ge0}v_n
 =2\left(\sum_{n\ge0}u_n-u_0\right)-\sum_{n\ge0}u_n
 =\sum_{n\ge0}u_n-2 . \qedhere
```
 ◻

</div>

The polynomial bound is [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L360), summability of the prime series [here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L379), the summability transfer is the [gap-series summability theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L385), and the displayed identity is the [unconditional prime-gap identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L427). The prime number theorem is not a dependency at any point.

<div id="long251:res:irr-equivalence" class="corollary">

**Corollary 4** (exact irrationality reformulation). *$`\Pi`$ is irrational if and only if $`S=\sum_{n\ge0}g_n2^{-(n+1)}`$ is irrational. The corresponding zero-based series with denominator $`2^n`$ equals $`4+2S`$ and has the same irrationality status.*

</div>

These are the [normalised irrationality equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L435), the [displayed-series identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L444), and the [displayed-series irrationality equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L459). Concretely, $`\Pi=3.674643966\ldots`$ is irrational if and only if $`S=1.674643966\ldots`$ is, and neither is known.

<a id="long251:sec:tail"></a>

# The tail recurrence and the exact criteria

The series is not attacked directly. Suppose $`\sum_{i\ge0}a_i2^{-(i+1)}`$ converges with every $`a_i`$ an integer, and rescale its tails by putting
``` math
T_N=2^{\,N+1}\sum_{i>N}\frac{a_i}{2^{\,i+1}}
    =\sum_{j\ge1}\frac{a_{N+j}}{2^{\,j}} .
```
Two facts follow immediately. First $`T_{N+1}=2T_N-a_{N+1}`$, so moving one level along doubles the rescaled tail and subtracts a single coefficient. Second $`T_0=2\sum_{i\ge0}a_i2^{-(i+1)}-a_0`$, so the sum is rational exactly when $`T_0`$ is. This section studies that recurrence, assuming nothing about the coefficients beyond the fact that they are integers, and resumes the prime-gap instance at the end.

<div id="long251:def:rec" class="definition">

**Definition 5**. Let $`g:\mathbb{N}\to\mathbb{Z}`$ and $`T:\mathbb{N}\to\mathbb{Q}`$ or $`T:\mathbb{N}\to\mathbb{R}`$. Say $`T`$ satisfies the *dyadic tail recurrence* with *digits* $`g`$ when $`T_{N+1}=2T_N-g_{N+1}`$ for every $`N`$. Write $`\sigma_h(N)=T_{N+h}-T_N`$ for the *shift* of length $`h`$ at $`N`$, and call a rational number *integral* when it is the image of an integer.

</div>

These are the [tail recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L482), the [shift](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L544), and [integrality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L575). One small orbit is worth having in view. Take every digit $`g_N=0`$ and $`T_0=1/12`$. Then the orbit is $`\tfrac1{12},\tfrac16,\tfrac13,\tfrac23,\tfrac43,\ldots`$ and $`\sigma_h(N)=(2^{h}-1)2^{\,N}/12`$. The shift of length $`2`$ is not integral at $`N=0`$ and is integral at $`N=2`$; the shift of length $`1`$ is never integral. Nonintegrality at one prescribed shift length therefore does not imply irrationality.

Iterating the recurrence $`h`$ times multiplies $`T_N`$ by $`2^{h}`$ and accumulates an explicit integer. Define $`B_{0,N}=0`$ and $`B_{h+1,N}=2B_{h,N}+g_{N+h+1}`$, so that $`B_{h,N}=g_{N+1}2^{\,h-1}+\cdots+g_{N+h}`$: the [tail block](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L647).

<div id="long251:res:block" class="theorem">

**Theorem 6** (block identity). *For every $`N`$ and $`h`$,
``` math
T_{N+h}=2^{h}T_N-B_{h,N},
 \qquad\text{hence}\qquad
 \sigma_h(N)=(2^{h}-1)\,T_N-B_{h,N} .
```*

</div>

<div class="proof">

*Proof.* A routine induction on $`h`$; the step is one application of the recurrence together with the recursion defining $`B`$. The second identity is the first minus $`T_N`$. ◻

</div>

Formalised as the [iterated block identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L653) and the [scaled shift identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L667). The shift also obeys the recurrence in its own right,
``` math
\begin{equation}
\label{long251:eq:shift-step}
 \sigma_h(N+1)=2\sigma_h(N)-\bigl(g_{N+h+1}-g_{N+1}\bigr),
\end{equation}
```
the [shift step identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L563). Since $`B_{h,N}`$ is an integer, Theorem <a href="#long251:res:block" data-reference-type="ref" data-reference="long251:res:block">6</a> converts a question about the shift into a question about $`(2^{h}-1)T_N`$: the shift $`\sigma_h(N)`$ is integral if and only if $`(2^{h}-1)T_N`$ is, the [integral-shift criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L802). The criterion holds in both directions, so once $`T_N`$ is fixed no choice of the digits after index $`N`$ can change whether $`\sigma_h(N)`$ is an integer.

For a rational orbit the denominator settles the matter exactly:
``` math
\begin{equation}
 \operatorname{den}(T_{N+1})
 =\frac{\operatorname{den}(T_N)}{\gcd(2,\operatorname{den}(T_N))},
 \qquad
 \sigma_h(N)\in\mathbb{Z}
 \iff
 \operatorname{den}(T_N)\mid 2^h-1 .
\tag{3.1}\label{long251:eq:den-law}
\end{equation}
```
Each even denominator loses exactly one factor of $`2`$ and an odd denominator is unchanged, so after finitely many steps the denominator is an odd integer $`d`$; Euler’s congruence then gives $`d\mid2^{\varphi(d)}-1`$, and the multiplicative order of $`2`$ modulo $`d`$ is the least such exponent. These are the [denominator recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1217), its [odd case](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1226) and [even case](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1236), the [denominator classification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1279), the [totient shift](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L877), and the [propagation of an integral shift to every later index](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L900). The hypothesis that $`d`$ is odd cannot be dropped: if $`T_N=1/2`$ then $`2^{h}-1`$ is odd for every $`h\ge1`$, so no shift at $`N`$ is integral.

<div id="long251:res:escape-irrational" class="theorem">

**Theorem 7** (exact rationality classification). *Let $`T:\mathbb{N}\to\mathbb{R}`$ satisfy $`T_{N+1}=2T_N-g_{N+1}`$ with integer digits $`g`$. The following are equivalent:*

1.  *$`T_0`$ is rational;*

2.  *$`\sigma_h(N)`$ is an integer for some $`h\ge1`$ and some $`N`$;*

3.  *for some fixed $`h\ge1`$, $`\sigma_h(N)`$ is an integer at every sufficiently large $`N`$.*

*Consequently $`T_0`$ is irrational if and only if every positive-length shift is nonintegral at every index, equivalently if and only if for every $`h\ge1`$ and every cutoff some later $`N`$ has $`\sigma_h(N)\notin\mathbb{Z}`$.*

</div>

<div class="proof">

*Proof.* For <span class="upright">(i)</span>$`\Rightarrow`$<span class="upright">(iii)</span>, the block identity identifies the whole orbit with the cast of the rational recurrence starting at $`T_0`$; apply <a href="#long251:eq:den-law" data-reference-type="eqref" data-reference="long251:eq:den-law">[long251:eq:den-law]</a> at an index where the denominator has become odd, and propagate forward. The implication <span class="upright">(iii)</span>$`\Rightarrow`$<span class="upright">(ii)</span> is immediate. For <span class="upright">(ii)</span>$`\Rightarrow`$<span class="upright">(i)</span>, the block identity gives $`\sigma_h(N)=(2^h-1)T_N-B_{h,N}`$ with $`B_{h,N}`$ and $`\sigma_h(N)`$ integers and $`2^h-1\ne0`$, so $`T_N`$ is rational, and $`T_N=2^NT_0-B_{N,0}`$ then makes $`T_0`$ rational. Negating the three conditions gives the two irrationality formulations. ◻

</div>

The exact real classifiers are [one integral positive shift](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1479), [eventual integrality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1525), [pointwise nonintegrality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1551), and [cofinal nonintegrality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1572).

<a id="the-actual-prime-gap-orbit."></a>

#### The actual prime-gap orbit.

Put
``` math
T_N=\sum_{j\ge1}\frac{g_{N+j}}{2^{\,j}},
```
which converges by Theorem <a href="#long251:res:infinite" data-reference-type="ref" data-reference="long251:res:infinite">3</a>. The scaled tail equals its shifted-gap series, the [shifted-gap series identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L31), and satisfies $`T_{N+1}=2T_N-g_{N+1}`$ with no rationality hypothesis, the [real tail recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L48). Since $`T_0=2S-1=2.349287932\ldots`$, the numbers $`\Pi`$, $`S`$ and $`T_0`$ have the same rationality status, and Theorem <a href="#long251:res:escape-irrational" data-reference-type="ref" data-reference="long251:res:escape-irrational">7</a> specialises to the actual series: irrationality of $`\Pi`$ is equivalent to cofinal nonintegrality of the positive shifts of $`T`$, the [escape equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L73). Nothing about the bridge from the series to its actual tail is left open; the open content is the escape hypothesis itself.

<a id="long251:sec:freepair"></a>

## The free-pair criterion and the lcm diagonal

The escape condition quantifies over a fixed shift length. Freeing the offset gives an equivalent condition with a weaker-looking producer.

<div id="long251:res:freepair" class="theorem">

**Theorem 8** (free-pair criterion). *$`S`$ is irrational if and only if for every $`t\ge1`$ and every $`N_0`$ there are $`N,M\ge N_0`$ with $`M\equiv N\pmod t`$ and $`T_M-T_N\notin\mathbb{Z}`$.*

</div>

<div class="proof">

*Proof.* If $`S`$ is irrational, take $`M=N+t`$ for the $`N`$ supplied by Theorem <a href="#long251:res:escape-irrational" data-reference-type="ref" data-reference="long251:res:escape-irrational">7</a> at shift length $`t`$. Conversely, suppose $`S`$ is rational. By <a href="#long251:eq:den-law" data-reference-type="eqref" data-reference="long251:eq:den-law">[long251:eq:den-law]</a> the orbit reaches an index $`N_0`$ beyond which the reduced denominator is a fixed odd $`d`$; let $`t`$ be the multiplicative order of $`2`$ modulo $`d`$. For $`N,M\ge N_0`$ with $`M\equiv N`$ modulo $`t`$, the difference $`T_M-T_N`$ is then an integer, contradicting the stated property at this $`t`$ and this cutoff. ◻

</div>

The offset $`M-N`$ is free, so one nonintegral congruent pair for each modulus and each cutoff suffices in place of a supply at a single fixed offset. The mechanism is exact: beyond a rational state with odd reduced denominator $`d`$, the difference $`T_M-T_N`$ is integral precisely when $`M\equiv N`$ modulo the order of $`2`$ in $`\mathbb{Z}/d\mathbb{Z}`$, the [free-pair lattice](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/FreePairReduction.lean#L92), so every rational orbit has a cutoff and a modulus at which integrality holds exactly on the congruence classes, the [lattice corollary](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/FreePairReduction.lean#L105). The criterion for the actual series is checked as the [free-pair equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/FreePairReduction.lean#L236), over the [actual real tail recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/FreePairReduction.lean#L186). No antecedent for this packaging has been located; the nearest located neighbour is Schlage-Puchta’s Theorem 2 \[schlagepuchta2011\], which treats periodic base-$`b`$ digit expansions and is a different object, and the sweep of the dyadic tail-recurrence and Bézivin-style functional-equation literature has not been run.

The criterion rules out two shortcuts. Rationality makes the tail a finite-state object at every scale, so pairs with $`T_M=T_N`$ are abundant for free and the whole difficulty sits in nonintegrality of the difference. And under the free-pair lattice the difference is an integer whenever the modulus divides the offset, and an integer cannot lie in $`(\tfrac12,1)`$, so the window component of the reduced event below is already a contradiction on its own. Both derivations are ordinary proofs, recorded in the long record and not formalised.

A second exact reformulation collapses all shift lengths and basepoints onto a single schedule. Let $`L_0=1`$ and $`L_j=\operatorname{lcm}(1,\ldots,j)`$.

<div id="long251:res:lcmdiagonal" class="theorem">

**Theorem 9** ([lcm-diagonal criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/OrderLatticeDiagonal.lean#L153)). *Let $`g:\mathbb{N}\to\mathbb{Z}`$ and $`T:\mathbb{N}\to\mathbb{R}`$ satisfy $`T_{N+1}=2T_N-g_{N+1}`$. Then $`T_0`$ is irrational if and only if $`T_{2L_j}-T_{L_j}\notin\mathbb{Z}`$ for every $`j\ge0`$.*

</div>

<div class="proof">

*Proof.* Theorem <a href="#long251:res:escape-irrational" data-reference-type="ref" data-reference="long251:res:escape-irrational">7</a> gives the forward implication. Conversely, if $`T_0`$ is rational then some positive shift length $`h`$ is integral at every basepoint beyond an index $`N_0`$. Choose $`j`$ so large that $`N_0\le L_j`$ and $`h\mid L_j`$. The cocycle identity $`\sigma_{a+b}(N)=\sigma_a(N)+\sigma_b(N+a)`$ shows by induction that every positive multiple of $`h`$ is integral at every such basepoint, so $`T_{2L_j}-T_{L_j}`$ is an integer. ◻

</div>

The factorial schedule has the same divisibility property; the lcm schedule is pointwise no larger and is the endpoint used here. Theorems <a href="#long251:res:freepair" data-reference-type="ref" data-reference="long251:res:freepair">8</a> and <a href="#long251:res:lcmdiagonal" data-reference-type="ref" data-reference="long251:res:lcmdiagonal">9</a> are exact reformulations on the class of integer-digit orbits. They change the shape of the required producer and they supply no nonintegrality statement for the actual prime gaps.

<a id="long251:sec:local-certificate"></a>

# A local certificate, and one actual pair

The classifiers reduce irrationality to a condition of infinite precision imposed on a complete tail. Inside $`(-1,1)`$ integrality is equality with zero, so on that range the shift step identity <a href="#long251:eq:shift-step" data-reference-type="eqref" data-reference="long251:eq:shift-step">[long251:eq:shift-step]</a> turns simultaneous integrality of two adjacent shifts into a single comparison of digits. What this buys is a certificate attached to one pair of adjacent indices, whose verification already contradicts integrality there. The distance of a shift from the integers never has to be estimated.

<div id="long251:res:smallpair" class="theorem">

**Theorem 10** (adjacent small-shift obstruction). *Let $`T`$ satisfy the dyadic tail recurrence with integer digits $`g`$, and fix $`h`$ and $`N`$. If
``` math
-1<\sigma_h(N)<1,\qquad -1<\sigma_h(N+1)<1,
 \qquad g_{N+h+1}\ne g_{N+1},
```
then $`\sigma_h(N)`$ and $`\sigma_h(N+1)`$ cannot both be integers. Consequently, if such a pair occurs beyond every threshold, the $`h`$-shift is not eventually integral.*

</div>

<div class="proof">

*Proof.* An integer strictly between $`-1`$ and $`1`$ is zero. If both shifts were integers, both would vanish, and <a href="#long251:eq:shift-step" data-reference-type="eqref" data-reference="long251:eq:shift-step">[long251:eq:shift-step]</a> would give $`g_{N+h+1}=g_{N+1}`$. The cofinal statement chooses one such adjacent pair after the alleged onset of integrality. ◻

</div>

<div id="long251:res:smallpair-real" class="corollary">

**Corollary 11** (real form and the sufficient condition). *The same statement holds for a real orbit, with the same proof. If for every $`h\ge1`$ and every cutoff some later $`N`$ satisfies the three displayed conditions for the actual prime gaps, then $`\Pi`$ is irrational.*

</div>

The rational finite contradiction is the [adjacent small-shift obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L979) with its [cofinal form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1006); the real form is the [real adjacent-pair consumer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L99), and the implication to irrationality of the actual series is the [small-mismatch criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L120). The third hypothesis alone is available for the actual gaps: it reads $`g_4=2\ne4=g_3`$ at $`h=1`$, $`N=2`$, and by Proposition <a href="#long251:res:gap-nonperiodic" data-reference-type="ref" data-reference="long251:res:gap-nonperiodic">12</a> it holds for arbitrarily large $`N`$ at every fixed $`h`$. What is missing is the pair of inequalities, each of which constrains a complete infinite tail.

<div id="long251:res:gap-nonperiodic" class="proposition">

**Proposition 12** (prime gaps do not become periodic). *For every positive $`h`$, the actual consecutive-prime-gap sequence is not eventually periodic with period $`h`$.*

</div>

<div class="proof">

*Proof.* For $`m\ge2`$ the integers $`(m+1)!+2,\ldots,(m+1)!+m+1`$ are composite, so the gaps are unbounded. An eventually periodic sequence of natural numbers has finite range after its preperiod and a bounded initial segment, hence is bounded. ◻

</div>

Lean checks the factorial argument as [unboundedness of the actual gaps](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L57) and the conclusion as [non-eventual periodicity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1023). Far stronger lower bounds for large gaps are known \[fgkmt2018, Theorem 1, p. 66\]; unboundedness is all that is needed.

The conjunction in Theorem <a href="#long251:res:smallpair" data-reference-type="ref" data-reference="long251:res:smallpair">10</a> has an exact normal form. For fixed $`h`$ write $`D_N=\sigma_h(N)`$ and $`\delta_N=g_{N+h+1}-g_{N+1}`$, so that $`D_{N+1}=2D_N-\delta_N`$.

<div id="long251:res:signedwindow" class="theorem">

**Theorem 13** ([signed two-window normal form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/AffineShiftEscape.lean#L113)). *Assume $`\delta_N`$ is even. The conjunction $`-1<D_N<1`$, $`-1<D_{N+1}<1`$, $`\delta_N\ne0`$ is equivalent to
``` math
\bigl(\delta_N=2\ \hbox{ and }\tfrac12<D_N<1\bigr)
 \quad\hbox{or}\quad
 \bigl(\delta_N=-2\ \hbox{ and }-1<D_N<-\tfrac12\bigr).
```*

</div>

<div class="proof">

*Proof.* The recurrence and the two unit windows give $`-3<\delta_N<3`$. A nonzero even integer in that interval is $`2`$ or $`-2`$. Substitution into $`D_{N+1}=2D_N-\delta_N`$ gives the stated half-window and, in the reverse direction, recovers the second unit window. ◻

</div>

For the actual gaps and $`N\ge1`$ every $`\delta_N`$ is even, so Theorem <a href="#long251:res:signedwindow" data-reference-type="ref" data-reference="long251:res:signedwindow">13</a> applies throughout the range where the local certificate is sought. The same computation for a real orbit is one line and is used in Theorem <a href="#long251:res:sparse" data-reference-type="ref" data-reference="long251:res:sparse">22</a> below.

<a id="an-explicit-remainder-and-a-certified-actual-pair"></a>

## An explicit remainder and a certified actual pair

Both window conditions involve complete infinite tails. A dominated truncation reduces each of them to a finite integer comparison.

<div id="long251:res:explicit-remainder" class="proposition">

**Proposition 14** (explicit remainder). *For integers $`h,N\ge0`$ and $`L\ge1`$ put
``` math
F_{h,N,L}=\sum_{j=1}^{L}\frac{g_{N+h+j}-g_{N+j}}{2^{\,j}},\qquad
 P(x)=x^4+8x^3+36x^2+104x+150,
```
``` math
E_{h,N,L}=\frac{1250}{2^{L}}\bigl(P(N+h+L+2)+P(N+L+2)\bigr).
```
Then $`\bigl|\sigma_h(N)-F_{h,N,L}\bigr|\le E_{h,N,L}`$. In particular $`|F_{h,N,L}|+E_{h,N,L}<1`$ certifies $`|\sigma_h(N)|<1`$, and $`\operatorname{dist}(F_{h,N,L},\mathbb{Z})>E_{h,N,L}`$ certifies $`\sigma_h(N)\notin\mathbb{Z}`$.*

</div>

<div class="proof">

*Proof.* The checked bound $`p_n\le1250(n+1)^4`$ gives $`0\le g_m\le p_{m+1}\le1250(m+2)^4`$, so the omitted absolute tail is at most
``` math
1250\sum_{j>L}\frac{(N+h+j+2)^4+(N+j+2)^4}{2^{\,j}} .
```
The polynomial identity $`2P(x)=(x+1)^4+P(x+1)`$ telescopes to $`\sum_{k=1}^{J}(m+k)^42^{-k}=P(m)-P(m+J)2^{-J}`$, whose last term tends to zero. Apply it with $`m=N+h+L+2`$ and $`m=N+L+2`$ after writing $`j=L+k`$. The two tests follow from the triangle inequality and the definition of distance to $`\mathbb{Z}`$. ◻

</div>

<div id="long251:res:finite-smallpair" class="proposition">

**Proposition 15** (a certified adjacent pair). *For the actual prime gaps, $`h=1`$ and $`N=2`$ satisfy the three hypotheses of Theorem <a href="#long251:res:smallpair" data-reference-type="ref" data-reference="long251:res:smallpair">10</a>: both $`\sigma_1(2)`$ and $`\sigma_1(3)`$ lie in $`(-1,1)`$ and are nonintegral, and $`g_4=2\ne4=g_3`$.*

</div>

<div class="proof">

*Proof.* Take $`L=40`$ and $`Q=2^{40}=1099511627776`$. Exact integer arithmetic over the first $`46`$ primes gives
``` math
\begin{array}{c|r|r}
 N&Q\,F_{1,N,40}&Q\,E_{1,N,40}\\\hline
 2&-662838684750&11764181250\\
 3& 873345886050&12805761250
\end{array}
```
In each row $`|QF|+QE<Q`$, which puts the whole certified interval inside $`(-1,1)`$, and $`QE`$ is smaller than the distance from $`QF`$ to the nearest multiple of $`Q`$, which excludes every integer. The margins are $`424908761776`$ and $`213359980476`$ respectively. These are strict integer comparisons rather than inferences from rounded numerical tails. Appendix <a href="#long251:app:certificates" data-reference-type="ref" data-reference="long251:app:certificates">10</a> replays them. ◻

</div>

This witness proves the local condition at one pair of indices. The quantifiers over every $`h`$ and every cutoff remain.

<a id="long251:sec:denominator-floor"></a>

# Two denominator floors

The same polynomial bound yields an exact rational enclosure of $`\Pi`$, and any such enclosure excludes an initial range of denominators.

<div id="long251:res:denominatorfloor" class="theorem">

**Theorem 16** (kernel-decided denominator floor). *Let $`a\in\mathbb{Z}`$ and $`b\in\mathbb{N}_{>0}`$. If $`\Pi=a/b`$ then $`b\ge2^{589}>10^{177}`$, and the same floor holds for every rational equal to $`S`$.*

</div>

<div class="proof">

*Proof.* Put $`c=1229`$, the number of primes below $`10^4`$, and $`A=\sum_{i=0}^{c-1}p_i2^{\,c-i-1}`$, so that $`A/2^{c}`$ is the $`c`$th partial sum of $`\Pi`$. All terms are positive, so $`A/2^{c}\le\Pi`$. For the upper bound, $`p_{c+j}\le1250(c+j+1)^4`$ and $`(c+1+j)^4\le(c+1)^4(3/2)^{j}`$ for $`j\ge0`$, valid because $`c\ge9`$; summing the resulting geometric tail with ratio $`3/4`$ gives
``` math
\frac{A}{2^{c}}\;\le\;\Pi\;\le\;\frac{2A+5000(c+1)^4}{2^{\,c+1}} .
```
The four positive integers $`u,v,u',v'`$ printed in Appendix <a href="#long251:app:certificates" data-reference-type="ref" data-reference="long251:app:certificates">10</a> satisfy
``` math
u'v-uv'=1,\qquad
 \frac uv<\frac{A}{2^{c}},\qquad
 \frac{2A+5000(c+1)^4}{2^{\,c+1}}<\frac{u'}{v'},\qquad
 v+v'\ge2^{589},
```
all four being integer comparisons after clearing the positive denominators. If $`\Pi=a/b`$ then $`av-bu\ge1`$ and $`bu'-av'\ge1`$, and the determinant identity gives
``` math
b=b(u'v-uv')=(av-bu)v'+(bu'-av')v\ge v+v' \ge 2^{589}.
```
Since $`589\log_{10}2>177`$, the floor exceeds $`10^{177}`$. If $`S=a/b`$, apply the same argument to $`\Pi=(a+2b)/b`$. ◻

</div>

The Lean kernel decides the four inequalities on the same literals by `decide +kernel` with no `native_decide`, over a trial-division sieve it re-runs on $`[2,10^4)`$: the [certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/KernelDenominatorFloor.lean#L310), the [floor for the prime series](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/KernelDenominatorFloor.lean#L316), and the [floor for the gap series](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/KernelDenominatorFloor.lean#L324). Its analytic input is the same enclosure, over the polynomial bound at [line 360](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L360). The four Farey literals have $`175`$ to $`181`$ digits.

<div id="long251:res:cfexclusion" class="theorem">

**Theorem 17** (certified continued-fraction exclusion). *Every rational equal to $`\Pi`$, and hence every rational equal to $`S`$, has reduced denominator $`q\ge2^{39997}`$, and therefore $`q>10^{12040}`$.*

</div>

*Evidence.* This is an exact finite computation and no Lean declaration carries it. The continued-fraction expansion of $`\Pi`$ is developed to $`23369`$ partial quotients at a working scale of $`80000`$ bits. Each quotient is forced by a rational bracket of width $`1`$ in those scaled integer units around the true value, and the separation $`|q_n\Pi-p_n|>0`$ is verified against that bracket, so the prefix is the true prefix. No floating-point reconstruction enters it. The bracket uses the Lean-checked tail estimate $`p_n\le1250(n+1)^4`$, so no conjecture enters. The classical theorem that a best approximation of the second kind is a convergent then converts the certified prefix into the denominator bound \[khinchin1964\]. The receipt is `state/formal_math/probes/erdos251_certified_cf_receipt.json`, which records the generating program and its digest, the power-of-two exponent $`39997`$, the bit length $`39998`$, the strict decimal power $`12040`$, the decimal digit count $`12041`$, the largest partial quotient $`973919`$ at index $`16442`$, and an arithmetic self-check of the same routine against the known expansions of $`e`$ and $`\pi`$. The certified statement is $`q\ge2^{39997}`$ and $`q>10^{12040}`$. Printing the bit length or the digit count as an exponent overstates the bound by one power of two and one decimal order.

Each floor is finite, and extending either one raises the excluded range and reproduces the same statement form. Neither decides the problem.

<a id="long251:sec:obstructions"></a>

# What cannot supply the missing input

This section proves four boundaries. Each says that a named class of hypotheses about the prime gaps is compatible with a rational dyadic value, or that a named event is too sparse for a named method.

<a id="bounded-residue-preserving-perturbations"></a>

## Bounded residue-preserving perturbations

<div id="long251:res:boundedperturbation" class="theorem">

**Theorem 18** (bounded-perturbation obstruction). *Let $`a_n`$ be natural numbers with $`\sum_{n\ge0}a_n2^{-(n+1)}`$ convergent. For every integer $`M\ge1`$ and every cutoff $`K`$ there are digits $`\varepsilon_n\in\{0,1\}`$, zero for $`n<K`$, such that $`\sum_{n\ge0}(a_n+M\varepsilon_n)2^{-(n+1)}`$ is rational.*

</div>

<div class="proof">

*Proof.* Write $`A=\sum_{n\ge0}a_n2^{-(n+1)}`$ and choose a rational $`r\in\bigl(A,A+M2^{-K}\bigr)`$. A binary expansion of $`(r-A)/M`$ has the form $`\sum_{n\ge K}\varepsilon_n2^{-(n+1)}`$ with $`\varepsilon_n\in\{0,1\}`$; set $`\varepsilon_n=0`$ for $`n<K`$. The perturbed series converges and equals $`r`$. ◻

</div>

The [construction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/BoundedPerturbationCountermodel.lean#L193) is kernel checked. The invariant-property consequence—a property shared by every admissible perturbation cannot by itself force irrationality—is the ordinary logical reading of that construction, rather than a separately named Lean theorem. The construction is also checked at the actual consecutive prime gaps for every $`M\ge1`$ and every $`K`$, the [rational perturbed prime-gap series](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/BoundedPerturbationCountermodel.lean#L208), with the perturbed gap lying in $`[g_n,g_n+M]`$ and congruent to $`g_n`$ modulo $`M`$, the [gap bounds](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/BoundedPerturbationCountermodel.lean#L234). Consequently no theorem about the size or the residue of prime gaps that survives such a perturbation can suffice for Problem #251; that class includes the bounded-gap and large-gap theorems cited in Section <a href="#long251:sec:open" data-reference-type="ref" data-reference="long251:sec:open">8</a> and equidistribution of $`p_n`$ modulo any fixed $`q`$, on taking $`M=2q`$. The perturbed digits need not remain prime gaps.

<a id="algebraic-nonconcentration-survives-the-rationalising-perturbation"></a>

## Algebraic nonconcentration survives the rationalising perturbation

The obvious reply to Theorem <a href="#long251:res:boundedperturbation" data-reference-type="ref" data-reference="long251:res:boundedperturbation">18</a> is to demand a finer property of the actual gaps than size and residue. A relevant such property is Schlage-Puchta’s Lemma 4: for every polynomial $`F\in\mathbb{Z}[x_0,\ldots,x_k]`$ which does not vanish identically, $`F(g_n,\ldots,g_{n+k})\ne0`$ for almost all $`n`$ \[schlagepuchta2011, Lemma 4, pp. 5–6\]. Say that an integer sequence $`a`$ has *fixed-block nonconcentration* when it satisfies that conclusion for every $`k\ge0`$ and every nonzero $`F\in\mathbb{Z}[x_0,\ldots,x_k]`$. The property transfers across bounded perturbations with no independence or randomness assumption.

<div id="long251:res:shiftedcount" class="proposition">

**Proposition 19** (finite counting for shifted gap differences). *Write $`p_n`$ for the primes indexed from $`p_0=2`$ and $`g_n=p_{n+1}-p_n`$. For $`h\ge2`$ and $`r\in\mathbb{Z}`$, let $`M_{h,r}(N)`$ count $`n<N`$ with $`g_{n+h}-g_n=r`$. Let $`Q_{N,H,r}`$ count triples $`(x,d,s)`$ with $`x<p_N`$, $`0<d<s\le H`$, $`d+r>0`$, and all four integers $`x,x+d,x+s,x+s+d+r`$ prime. Then, for every $`N,H\ge0`$,
``` math
(H+1)M_{h,r}(N)\le
 (h+1)p_{N+h+1}+(H+1)Q_{N,H,r}.
```*

</div>

<div class="proof">

*Proof.* Windows of total span at most $`H`$ inject into these four-prime configurations; the sum of all length-$`(h+1)`$ spans is at most $`(h+1)p_{N+h+1}`$, which bounds the number of larger spans. ◻

</div>

The [finite shifted-count bound](https://github.com/wcook04/plectis-erdos/blob/d058b9150218ae23d2cfd975580088d6167e9da8/ErdosProblems/Erdos251/ShiftedGapCountingR9.lean#L152) is unconditional. To deduce zero density one still needs, for every $`\varepsilon>0`$ and all large $`N`$, a choice of $`H`$ making the right side less than $`\varepsilon N(H+1)`$. The adjacent case $`h=1`$ instead requires the corresponding three-prime estimate, because two of the four positions would coincide. The all-shift implication records these analytic premises explicitly; it supplies neither estimate and does not prove irrationality.

<div id="long251:res:nonconcentration" class="theorem">

**Theorem 20** (nonconcentration is perturbation-stable). *Let $`a:\mathbb{N}\to\mathbb{Z}`$ have fixed-block nonconcentration, let $`E\subset\mathbb{Z}`$ be finite, and let $`b_n=a_n+e_n`$ with $`e_n\in E`$ for every $`n`$. Then $`b`$ has fixed-block nonconcentration.*

</div>

<div class="proof">

*Proof.* Fix $`k\ge0`$ and a nonzero $`F\in\mathbb{Z}[x_0,\ldots,x_k]`$. For a tuple $`\mathbf e=(e^{(0)},\ldots,e^{(k)})\in E^{k+1}`$ put $`F_{\mathbf e}(x_0,\ldots,x_k)=F(x_0+e^{(0)},\ldots,x_k+e^{(k)})`$. The substitution $`x_i\mapsto x_i+e^{(i)}`$ is a ring automorphism of $`\mathbb{Z}[x_0,\ldots,x_k]`$ with inverse $`x_i\mapsto x_i-e^{(i)}`$, so $`F_{\mathbf e}\ne0`$. If $`F(b_n,\ldots,b_{n+k})=0`$ then $`F_{\mathbf e}(a_n,\ldots,a_{n+k})=0`$ for the tuple $`\mathbf e=(e_n,\ldots,e_{n+k})`$, whence
``` math
\{\,n:F(b_n,\ldots,b_{n+k})=0\,\}
 \;\subseteq\!\!
 \bigcup_{\mathbf e\in E^{k+1}}\!\!
 \{\,n:F_{\mathbf e}(a_n,\ldots,a_{n+k})=0\,\}.
```
Each set on the right has density zero by hypothesis, and the union is over the finite index set $`E^{k+1}`$, so a finite union of density-zero sets has density zero. ◻

</div>

<div id="long251:res:nonconc-primes" class="corollary">

**Corollary 21** (nonconcentration does not force irrationality). *Fix $`M\ge1`$ and $`K\ge0`$, and let $`b`$ be the perturbed sequence supplied by Theorem <a href="#long251:res:boundedperturbation" data-reference-type="ref" data-reference="long251:res:boundedperturbation">18</a> at the actual prime gaps. Then $`\sum_{n\ge0}b_n2^{-(n+1)}`$ is rational, $`b_n=g_n`$ for $`n<K`$, $`b_n-g_n\in\{0,M\}`$ and $`b_n\equiv g_n\pmod M`$ for every $`n`$, $`b`$ has fixed-block nonconcentration, and the cumulative sequence $`P_n=2+\sum_{i<n}b_i`$ satisfies $`p_n\le P_n\le p_n+Mn`$ and hence $`P_n\sim n\log n`$.*

</div>

<div class="proof">

*Proof.* Everything except nonconcentration is Theorem <a href="#long251:res:boundedperturbation" data-reference-type="ref" data-reference="long251:res:boundedperturbation">18</a> together with $`\sum_{i<n}g_i=p_n-2`$. The perturbation takes values in the fixed two-element set $`E=\{0,M\}`$, so Theorem <a href="#long251:res:nonconcentration" data-reference-type="ref" data-reference="long251:res:nonconcentration">20</a> applies to the actual gaps, which have fixed-block nonconcentration by Schlage-Puchta’s Lemma 4. ◻

</div>

Fixed-block polynomial nonconcentration, taken together with a prescribed finite prefix of actual gaps, a pointwise bound $`b_n\le g_n+M`$, every residue modulo $`M`$, positivity and cumulative growth at the prime-number-theorem scale, is therefore compatible with a rational dyadic value. Taking $`M`$ even also preserves eventual evenness. To preserve a prescribed modulus $`q`$ together with parity, take $`M=2q`$, with the corresponding pointwise bound $`b_n\le g_n+2q`$. The boundary is exact: the terms $`P_n`$ are not asserted to be prime, and the conclusion says nothing about constraints with a block length or a polynomial family growing with the index.

<a id="the-producer-is-an-event-of-density-zero"></a>

## The producer is an event of density zero

The same lemma bounds the event that the local certificate consumes.

<div id="long251:res:sparse" class="theorem">

**Theorem 22** (sparsity of the two-window event). *Fix $`h\ge1`$. The set of $`N\ge1`$ at which the three hypotheses of Theorem <a href="#long251:res:smallpair" data-reference-type="ref" data-reference="long251:res:smallpair">10</a> hold for the actual prime gaps has density zero. For the same $`h`$, the set of $`N`$ with $`g_{N+h+1}=g_{N+1}`$ also has density zero.*

</div>

<div class="proof">

*Proof.* For $`N\ge1`$ every gap involved is even, so $`\delta_N=g_{N+h+1}-g_{N+1}`$ is even. If $`|\sigma_h(N)|<1`$, $`|\sigma_h(N+1)|<1`$ and $`\delta_N\ne0`$, then $`\delta_N=2\sigma_h(N)-\sigma_h(N+1)`$ lies in $`(-3,3)`$, so $`\delta_N=\pm2`$. Apply Schlage-Puchta’s Lemma 4 at index $`n=N+1`$ with $`k=h`$ to the two polynomials $`F_\pm(x_0,\ldots,x_h)=x_h-x_0\mp2`$, neither of which vanishes identically: each of $`\{N:\delta_N=2\}`$ and $`\{N:\delta_N=-2\}`$ has density zero, and the event is contained in their union. The second assertion is the same lemma applied to $`F(x_0,\ldots,x_h)=x_h-x_0`$. ◻

</div>

The two halves point in opposite directions and both are useful. The mismatch hypothesis on its own holds for almost all $`N`$, which is strictly stronger than the cofinal statement Proposition <a href="#long251:res:gap-nonperiodic" data-reference-type="ref" data-reference="long251:res:gap-nonperiodic">12</a> supplies. The full conjunction is confined to a set of density zero, because the two window conditions force the mismatch to be exactly $`\pm2`$. A producer for Problem <a href="#long251:prob:smallpair" data-reference-type="ref" data-reference="long251:prob:smallpair">28</a> therefore has to be a cofinality statement about a sparse set. Consequently, this event cannot be supplied on a set of positive lower density. A sufficient producer would have to yield cofinally many witnesses in a density-zero set; density zero alone does not exclude an averaging argument capable of detecting such sparse witnesses. The measurement reported in Section <a href="#long251:sec:measurements" data-reference-type="ref" data-reference="long251:sec:measurements">7</a> is consistent with this: the observed density at $`h=1`$ declines like $`1/\log p`$, and the observed count up to $`X`$ grows like $`X/(\log X)^2`$.

<a id="recurring-gap-values-differing-by-two-do-not-suffice"></a>

## Recurring gap values differing by two do not suffice

Theorem <a href="#long251:res:signedwindow" data-reference-type="ref" data-reference="long251:res:signedwindow">13</a> reduces the producer to a $`\pm2`$ mismatch together with a half-window condition. It is tempting to hope that the mismatch half is the substance, and that two even values differing by $`2`$, each occurring infinitely often as a consecutive prime gap inside a common index residue class, would suffice. At the level of integer-digit recurrences that implication is false, and it stays false under growth at the scale the primes actually have.

<div id="long251:res:polignacfail" class="theorem">

**Theorem 23** (recurring values are not enough). *There is a sequence $`(a_n)_{n\ge1}`$ of positive even integers with the following properties. The values $`2`$ and $`4`$ each occur infinitely often at indices divisible by every fixed $`t\ge1`$. The sequence is unbounded, not eventually periodic, and satisfies $`a_n=O(\log n)`$. The series $`\sum_{n\ge1}a_n2^{-n}`$ equals $`6`$, and every scaled tail $`\sum_{j\ge1}a_{N+j}2^{-j}`$ is an integer, so every tail shift is integral. The increasing odd sequence $`P_n=3+\sum_{j\le n}a_j`$ satisfies $`P_n\sim n\log n`$.*

</div>

<div class="proof">

*Proof.* Let logarithms be natural and put $`b_n=2\lceil\tfrac12\log(n+64)\rceil`$, so that $`b_n`$ is even, $`b_n\ge6`$, and $`b_n=\log(n+64)+O(1)`$. Since $`\tfrac12\log(n+65)-\tfrac12\log(n+63)<1`$ for every $`n\ge1`$, consecutive increments of $`b`$ lie in $`\{0,2\}`$ and $`b_{n+1}-b_{n-1}\le2`$. Call an index $`n`$ *special* when $`n=k!`$ or $`n=2\,k!`$ for some $`k\ge5`$, and define
``` math
U_n=\begin{cases}
  2b_{n-1}-2,& n=k!,\ k\ge5,\\
  2b_{n-1}-4,& n=2\,k!,\ k\ge5,\\
  b_n,&\text{otherwise},
 \end{cases}
 \qquad a_n=2U_{n-1}-U_n\quad(n\ge1).
```
The special indices are distinct and never adjacent, since $`k!`$ and $`2\,k!`$ are even and differ by more than one from each other and from the neighbouring special indices. Each $`U_n`$ is an even integer by construction, so each $`a_n`$ is an even integer.

At an ordinary index whose predecessor is also ordinary, $`a_n=2b_{n-1}-b_n=b_{n-1}-(b_n-b_{n-1})\ge6-2=4`$. At a special index the predecessor is ordinary and $`a_n=2b_{n-1}-(2b_{n-1}-r)=r`$, which is $`2`$ at $`n=k!`$ and $`4`$ at $`n=2\,k!`$. Immediately after a special index carrying $`r`$,
``` math
a_{n+1}=2(2b_{n-1}-r)-b_{n+1}\ge4b_{n-1}-2r-(b_{n-1}+2)
 =3b_{n-1}-2r-2\ge8 .
```
Every $`a_n`$ is therefore a positive even integer, and $`U_n=O(\log n)`$ gives $`a_n=O(\log n)`$. At ordinary indices with ordinary predecessors $`a_n\ge b_{n-1}-2\to\infty`$, so $`(a_n)`$ is unbounded and hence not eventually periodic.

The definition $`a_n=2U_{n-1}-U_n`$ is exactly $`a_n2^{-n}=U_{n-1}2^{-(n-1)}-U_n2^{-n}`$, so for every $`N\ge0`$ and $`m\ge1`$
``` math
\sum_{j=1}^{m}\frac{a_{N+j}}{2^{\,j}}=U_N-\frac{U_{N+m}}{2^{\,m}} .
```
Since $`U_n=O(\log n)`$ the endpoint tends to zero, so the tail at $`N`$ equals the integer $`U_N`$; at $`N=0`$ the series equals $`U_0=b_0=6`$. Every difference $`U_{N+h}-U_N`$ is an integer, so every tail shift is integral.

For each $`t`$ and every sufficiently large $`k`$ we have $`t\mid k!`$, hence $`t\mid2\,k!`$, and $`a_{k!}=2`$ while $`a_{2k!}=4`$: both values recur infinitely often at indices congruent to $`0`$ modulo $`t`$.

Finally, summing $`a_j=2U_{j-1}-U_j`$ gives $`\sum_{j=1}^{n}a_j=2U_0+\sum_{j=1}^{n-1}U_j-U_n`$. The baseline $`\sum_{j<n}b_j=n\log n+O(n)`$. The special indices up to $`n`$ number $`O(\log n/\log\log n)`$ and each changes the summand by $`O(\log n)`$, so their total contribution is $`O((\log n)^2)=o(n)`$. Hence $`P_n=3+\sum_{j\le n}a_j\sim n\log n`$, and $`P_n`$ is odd and increasing. ◻

</div>

The factorial schedule above proves recurrence in the zero residue class. The following separate construction strengthens this to every residue class.

<a id="long251:res:all-residue-log-countermodel"></a>

## A complete countermodel in every residue class

There is a synthetic integer sequence $`(a_n)_{n\ge1}`$ with all of the following properties. Each $`a_n`$ is positive and divisible by $`2`$, and
``` math
a_n\le 4\log(n+1)+24.
```
For every $`t\ge1`$, every $`0\le r<t`$, and every cutoff $`N`$, there are $`i,j\ge N`$ such that
``` math
i\equiv j\equiv r\pmod t,\qquad a_i=2,\quad a_j=4.
```
For every integer $`B`$ and cutoff $`N`$, some $`n\ge N`$ satisfies $`a_n>B`$. For every $`h\ge1`$ there is no cutoff after which $`a_{n+h}=a_n`$ for all $`n`$. Nevertheless, all the complete tails
``` math
U_N=\sum_{j\ge1}\frac{a_{N+j}}{2^j}\quad(N\ge0)
```
are integers, $`U_0=6`$, and $`U_{N+h}-U_N\in\mathbb Z`$ for every $`N,h\ge0`$. The sequence
``` math
P_N=3+\sum_{j=1}^{N}a_j
```
is strictly increasing and odd, with $`P_N/(N\log N)\to1`$. These are synthetic positions; no $`P_N`$ is asserted to be prime.

To obtain every residue class, enumerate triples consisting of a positive modulus, a residue, and a repetition index. Choose the corresponding centres $`c_k`$ in the prescribed classes with $`c_0\ge100`$, $`c_{k+1}\ge c_k+3`$ and $`c_k\ge2^{k^2}`$ for $`k\ge1`$. The parity of the repetition index selects the desired value $`v_k=2`$ or $`4`$. Use the even baseline
``` math
b_n=6+2\left\lfloor\frac{\log(n+1)}2\right\rfloor,
 \qquad
 U_n=\begin{cases}2b_{n-1}-v_k,&n=c_k,\\b_n,&n\notin\{c_k:k\ge0\},\end{cases}
```
and define $`a_n=2U_{n-1}-U_n`$. The separation of the centres and the baseline increment bound give positivity and the displayed logarithmic bound. Finite telescoping leaves $`U_{N+m}/2^m`$, which tends to zero; thus these carries are the complete tails. The sparse changes to the baseline have negligible contribution after division by $`N\log N`$, which gives the stated growth of $`P_N`$.

The full statement is [kernel-checked in Lean](https://github.com/wcook04/plectis-erdos/blob/d4fed71423840f70f10edf27b9ad27c22fc4f49a/ErdosProblems/Erdos251/AllResidueLogarithmicR9.lean#L503).

This rules out an inference from these coefficient properties alone to nonintegral tail shifts. It gives no counterexample to the prime-gap problem and does not reproduce the extreme large gaps of the primes.

The consequence is exact. Positivity, evenness, unboundedness, non-eventual periodicity, a pointwise logarithmic bound, cumulative growth at the prime-number-theorem scale, and the recurrence of two even values differing by $`2`$ inside every index residue class are jointly compatible with an integral tail at every index. Any route through that input must use a property of the consecutive primes beyond this list. The sequence $`(a_n)`$ is synthetic and the $`P_n`$ are not asserted to be prime. The pointwise logarithmic bound also precludes the known large-gap behaviour, so the theorem does not speak to hypotheses that use extreme gaps.

<a id="two-further-boundaries"></a>

## Two further boundaries

<div id="long251:res:polynomialcountermodel" class="proposition">

**Proposition 24** (quadratic polynomial-shift countermodel). *Put $`c_n=2(n^2+4n+2)`$ and $`U_n=2(n+4)^2`$. Then $`c_n`$ is positive, even and strictly increasing, $`U_{n+1}=2U_n-c_{n+1}`$, every shift $`U_{N+h}-U_N`$ is integral, $`c_{n+1}-c_n=4n+10`$ is never $`\pm2`$, and
``` math
\sum_{j\ge1}\frac{c_j}{2^{\,j}}=32 .
```*

</div>

<div class="proof">

*Proof.* Direct expansion gives the recurrence, and the finite telescope is $`\sum_{j=1}^{n}c_j2^{-j}=32-2(n+4)^22^{-n}`$, whose last term tends to zero. The remaining assertions follow from the integer values of $`U_n`$ and from $`c_{n+1}-c_n=4n+10\ge10`$. ◻

</div>

The series is the one starting at $`j=1`$, whose initial tail state is $`U_0=32`$; under the opening convention $`\sum_{n\ge0}c_n2^{-(n+1)}`$ the same word has value $`18`$, and the two ranges must be kept apart. The formal construction checks the [recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1596), [strict growth](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1632), [integrality of every shift](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1654), [exclusion of adjacent differences of size two](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1644), and the [value $`32`$ for the shifted series](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PolynomialGapSeriesValue.lean#L92), whose summand is $`c_{n+1}/2^{\,n+1}`$; the rational value is recorded at [line 109](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PolynomialGapSeriesValue.lean#L109). Positivity, parity, strict growth, unboundedness and nonperiodicity are therefore jointly compatible with rationality, and the adjacent trigger of Theorem <a href="#long251:res:signedwindow" data-reference-type="ref" data-reference="long251:res:signedwindow">13</a> fails at every index. The telescoping mechanism is the one Kovač used against the variable-denominator conjecture printed under the problem \[kovac2026, Theorem 1 and proof, pp. 1–2\]; the word carries no priority claim and is not a result about Problem #251.

Rationality also fails to force the coefficients to repeat. Let $`K:\mathbb{N}\to\mathbb{Q}`$ be arbitrary and put $`\kappa_n=2K_n-K_{n+1}`$: the [carry coefficient](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1129).

<div id="long251:res:telescope" class="proposition">

**Proposition 25** (exact telescoping). *For every $`n\ge0`$, $`\sum_{i=0}^{n-1}\kappa_i2^{-(i+1)}=K_0-K_n2^{-n}`$.*

</div>

<div class="proof">

*Proof.* A routine induction; the added term is $`(2K_n-K_{n+1})2^{-(n+1)}=K_n2^{-n}-K_{n+1}2^{-(n+1)}`$. ◻

</div>

Formalised as the [carry telescoping identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1137). Taking $`K_0=\tfrac52`$ and $`K_n=2n+2`$ for $`n\ge1`$ gives $`\kappa_0=1`$ and $`\kappa_n=2n`$, so the coefficients $`1,2,4,6,8,\ldots`$ are positive, even after the first term, unbounded and not eventually periodic, while their dyadic sum is $`\tfrac52`$. Rationality alone therefore cannot imply eventual periodicity even for a positive, parity-correct integer coefficient sequence, and no argument may play periodicity of a rational value against Proposition <a href="#long251:res:gap-nonperiodic" data-reference-type="ref" data-reference="long251:res:gap-nonperiodic">12</a>.

Finally, two escape tests that look like independent producers are equivalent to the conclusion they were introduced to supply. For fixed $`h`$ write $`\delta_N=g_{N+h+1}-g_{N+1}`$, $`D_N=\sigma_h(N)`$ and $`B_{h,N,r}=\sum_{i=0}^{r-1}2^{\,r-1-i}\delta_{N+i}`$, so that $`D_{N+r}=2^{r}D_N-B_{h,N,r}`$, and call the data-dependent affine condition $`\mathcal A_{N,r}`$ the assertion $`D_{N+r}\in-B_{h,N,r}+2^{\,r+1}\mathbb{Z}`$.

<div id="long251:res:affinecollapse" class="theorem">

**Theorem 26** (affine and fixed-lattice circularity). *For every rational dyadic tail recurrence and all $`h,N,r\ge0`$, $`\mathcal A_{N,r}`$ holds if and only if $`D_N\in2\mathbb{Z}`$. Consequently, if every $`\delta_N`$ is even, cofinal failure of $`\mathcal A`$ is equivalent to nonintegrality of $`D_N`$ for arbitrarily large $`N`$. The same equivalence holds for the fixed-lattice replacement, under any bound $`|D_N|\le b(N)`$ satisfying $`2b(N+r)q<2^{r}`$ for some $`r`$ at every $`N`$ and every positive integer $`q`$.*

</div>

<div class="proof">

*Proof.* Substituting $`D_{N+r}=2^{r}D_N-B_{h,N,r}`$ into $`\mathcal A_{N,r}`$ cancels the observed block and leaves $`D_N=2z`$. After one recurrence step, evenness of $`\delta_N`$ identifies even integrality at $`N+1`$ with ordinary integrality at $`N`$; the reverse implication chooses a nonintegral $`D_N`$ and depth $`r=0`$. For the fixed-lattice form, eventual integrality and the block identity give $`B_{h,N,r}-2^{r}z=-D_{N+r}`$, so a strict separation exceeding $`b(N+r)`$ is contradictory; conversely a nonintegral $`D_N`$ with reduced denominator $`q`$ has distance at least $`1/q`$ from every integer, and scaling that separation by $`2^{r}`$ at a legal depth gives the required strict inequality. ◻

</div>

These are the [pointwise affine identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/AffineCylinderCollapse.lean#L91), its [cofinal form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/AffineCylinderCollapse.lean#L162), and the [fixed-lattice equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/AffineCylinderCollapse.lean#L308). The apparent affine hierarchy contains no depth-dependent information, and the fixed lattice removes the data dependence at the cost of a growth condition under which rational denominator separation already forces every required escape. Neither is an independent source of information about consecutive primes.

<a id="long251:sec:measurements"></a>

# What is measured

Two finite computations report on the two producers. Each covers one bounded range and supplies no cofinal statement.

Over the $`6\,841\,648`$ primes below $`1.2\times10^{8}`$ and offsets $`h=1,\ldots,16`$, the reduced two-window event of Theorem <a href="#long251:res:signedwindow" data-reference-type="ref" data-reference="long251:res:signedwindow">13</a> occurs at every offset, with density between $`0.00418`$ and $`0.008248`$ and the two signs near balanced; at $`h=1`$ there are $`56\,427`$ occurrences among $`6\,841\,564`$ candidate indices, the last at the prime $`119\,995\,753`$. Rescaled by $`\log p`$ the band densities run from $`0.17671`$ down to $`0.13148`$ with decelerating drift, so the count up to $`X`$ still grows like $`X/(\log X)^2`$, which is the rate Theorem <a href="#long251:res:sparse" data-reference-type="ref" data-reference="long251:res:sparse">22</a> permits. The tails in this scan are double-precision floating-point, so an individual hit is a numerical observation and carries no certificate; the median distance from the shift to the nearer window boundary is $`0.127`$ and the worst case over $`34\,000`$ hits is $`6.1\times10^{-7}`$, eight orders above the working resolution, and $`3\,200`$ sampled hits across $`h=1,\ldots,8`$ were rechecked against the literal three-part statement with no violations. Proposition <a href="#long251:res:finite-smallpair" data-reference-type="ref" data-reference="long251:res:finite-smallpair">15</a> is the one pair certified by exact integer arithmetic. The receipt is `state/formal_math/probes/erdos251_adjacent_mismatch_receipt.json`.

Over the $`1\,270\,607`$ primes below $`2\times10^{7}`$, and for every modulus $`t\le20`$ and every residue class modulo $`t`$, the free-pair event of Theorem <a href="#long251:res:freepair" data-reference-type="ref" data-reference="long251:res:freepair">8</a> has witnesses running to the last usable index: the leanest class at $`t=20`$ carries $`90\,150`$ witnesses and the latest witness sits at index $`1\,270\,519`$ of $`1\,270\,540`$. Every recorded witness satisfies the stronger two-window event, so it certifies both producers at once. What the scan does not supply is uniformity in $`t`$ and in the cutoff. The receipt is `state/formal_math/erdos257_period_noncollapse/` `erdos251_free_pair_receipt.json`.

<a id="long251:sec:open"></a>

# The remaining obligation

Problem #251 is open. The exact unresolved condition, equivalent to irrationality by Theorem <a href="#long251:res:escape-irrational" data-reference-type="ref" data-reference="long251:res:escape-irrational">7</a> and the escape equivalence for the actual tail, is the following.

<div id="long251:prob:escape" class="problem">

**Problem 27** (universal prime-gap shift escape). For every $`h\ge1`$ and every $`N_0`$, prove that some $`N\ge N_0`$ satisfies
``` math
\sum_{j\ge1}\frac{g_{N+h+j}-g_{N+j}}{2^{\,j}}\notin\mathbb{Z}.
\tag{8.1}\label{long251:eq:shift-escape}
```

</div>

<div id="long251:prob:smallpair" class="problem">

**Problem 28** (cofinal adjacent small mismatch). For every $`h\ge1`$ and every $`N_0`$, prove that some $`N\ge N_0`$ satisfies
``` math
\bigl|\sigma_h(N)\bigr|<1,\qquad
 \bigl|\sigma_h(N+1)\bigr|<1,\qquad
 g_{N+h+1}\ne g_{N+1} .
\tag{8.2}\label{long251:eq:smallpair}
```

</div>

Corollary <a href="#long251:res:smallpair-real" data-reference-type="ref" data-reference="long251:res:smallpair-real">11</a> makes Problem <a href="#long251:prob:smallpair" data-reference-type="ref" data-reference="long251:prob:smallpair">28</a> sufficient for Problem <a href="#long251:prob:escape" data-reference-type="ref" data-reference="long251:prob:escape">27</a>, and Theorem <a href="#long251:res:freepair" data-reference-type="ref" data-reference="long251:res:freepair">8</a> supplies an equivalent target in which the offset is free. The three formulations are equivalent or ordered by implication; none of them is an analytic saving on its own.

What the proved obstructions leave. By Theorem <a href="#long251:res:boundedperturbation" data-reference-type="ref" data-reference="long251:res:boundedperturbation">18</a> no hypothesis stable under bounded residue-preserving perturbation can work; by Corollary <a href="#long251:res:nonconc-primes" data-reference-type="ref" data-reference="long251:res:nonconc-primes">21</a> adding fixed-block polynomial nonconcentration to that list does not repair it; the construction in Section <a href="#long251:res:all-residue-log-countermodel" data-reference-type="ref" data-reference="long251:res:all-residue-log-countermodel">6.5</a> shows that recurring gap values differing by $`2`$ in every residue class do not work at the level of integer recurrences; and by Theorem <a href="#long251:res:sparse" data-reference-type="ref" data-reference="long251:res:sparse">22</a> the event in <a href="#long251:eq:smallpair" data-reference-type="eqref" data-reference="long251:eq:smallpair">[long251:eq:smallpair]</a> has density zero, so it must be produced cofinally on a sparse set. Isolated small gaps, isolated large gaps and average gap estimates are insufficient. Any prescribed finite prefix can be preserved while the complete sum is rationalised, so that prefix alone cannot force irrationality or a cofinal small-tail producer. A finite block together with a proved tail bound can still certify one window: both inequalities in <a href="#long251:eq:smallpair" data-reference-type="eqref" data-reference="long251:eq:smallpair">[long251:eq:smallpair]</a> contain the complete infinite continuation, and Proposition <a href="#long251:res:explicit-remainder" data-reference-type="ref" data-reference="long251:res:explicit-remainder">14</a> supplies the corresponding finite reduction. Nor does parity help, since after the first gap every $`g_n`$ is even.

The finite reduction is available. Proposition <a href="#long251:res:explicit-remainder" data-reference-type="ref" data-reference="long251:res:explicit-remainder">14</a> turns each window condition into an integer comparison at truncation length $`L`$, and for fixed $`h`$ and $`\varepsilon>0`$ the choice $`L=\lceil(4+\varepsilon)\log_2(N+2)\rceil`$ makes $`E_{h,N,L}=O_h(N^{-\varepsilon})`$. A prescribed positive margin $`\eta_h`$ therefore converts <a href="#long251:eq:smallpair" data-reference-type="eqref" data-reference="long251:eq:smallpair">[long251:eq:smallpair]</a> into a statement about the joint distribution modulo powers of two of the finite block $`(g_{N+h+1}-g_{N+1},\ldots,g_{N+h+L}-g_{N+L})`$ over a window of logarithmic length. Deciding one instance costs $`O(\log N)`$ gaps together with the elementary prime bound; producing them cofinally, with uniformity in $`h`$ and in the cutoff, is the open work.

The strongest published results on prime gaps address a different shape of question. Zhang’s bounded-gap theorem \[zhang2014, Theorem 1, p. 1122\] produces infinitely many bounded consecutive-prime gaps. Maynard bounds $`\liminf_n(p_{n+m}-p_n)`$ for every fixed $`m`$, giving bounded clusters of every fixed size \[maynard2015, Theorem 1.1, p. 384\], with the explicit unconditional bound $`\liminf_n(p_{n+1}-p_n)\le600`$ \[maynard2015, Theorem 1.3, p. 385\]. The large-gap theorem of Ford, Green, Konyagin, Maynard and Tao bounds the largest single consecutive-prime gap below $`X`$ \[fgkmt2018, Theorem 1, p. 66\]. A theorem giving bounded clusters at each fixed cluster size does not by itself supply a weighted condition on windows whose length grows with the basepoint, and none of these results is used as a proof input here.

Conditionally the picture is different. Tao’s comment names uniform quantitative prime-tuples control of about $`\log\log n`$ consecutive gaps as the plausible route \[erdosproblems251thread, comment of 7 October 2025\], and Land’s draft carries that out under Kuperberg’s uniform prime-tuples conjecture \[land2026\]. The obstructions of Section <a href="#long251:sec:obstructions" data-reference-type="ref" data-reference="long251:sec:obstructions">6</a> say which unconditional substitutes cannot replace that hypothesis.

<a id="what-remains-to-be-formalised."></a>

#### What remains to be formalised.

The two finite certificates of Propositions <a href="#long251:res:explicit-remainder" data-reference-type="ref" data-reference="long251:res:explicit-remainder">14</a> and <a href="#long251:res:finite-smallpair" data-reference-type="ref" data-reference="long251:res:finite-smallpair">15</a>, the continued-fraction exclusion of Theorem <a href="#long251:res:cfexclusion" data-reference-type="ref" data-reference="long251:res:cfexclusion">17</a>, the nonconcentration transfer of Theorem <a href="#long251:res:nonconcentration" data-reference-type="ref" data-reference="long251:res:nonconcentration">20</a> with its corollary, the sparsity statement of Theorem <a href="#long251:res:sparse" data-reference-type="ref" data-reference="long251:res:sparse">22</a>, and the construction of Theorem <a href="#long251:res:polignacfail" data-reference-type="ref" data-reference="long251:res:polignacfail">23</a> are ordinary mathematical proofs with exact arithmetic replay and no Lean declaration. Everything else linked above is checked by the kernel at the pinned commit.

<a id="statements-and-declarations"></a>

## Statements and declarations

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

The [pinned formal-source revision](https://github.com/wcook04/plectis-lean-erdos249-257/tree/ee650b32b8b2cb98b94e5500df5370d85f7403b8) contains the Lean sources, the fixed toolchain, and the library manifest used in the verification. Proof authority rests in those pinned sources. The present text is exposition and navigation.

Lean checks each proof term against the fixed library version, and the sources linked here contain no proof placeholders and no project-defined axioms; Lean does not authorise the exposition, the citation choices, or the interpretation, for which the author remains responsible. The two receipts named in Section <a href="#long251:sec:measurements" data-reference-type="ref" data-reference="long251:sec:measurements">7</a> and the continued-fraction receipt of Theorem <a href="#long251:res:cfexclusion" data-reference-type="ref" data-reference="long251:res:cfexclusion">17</a> record their generating programs with digests and are held in the private research development.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.

<a id="acknowledgements."></a>

#### Acknowledgements.

The problem numbering and status follow the Erdős Problems catalogue maintained by Thomas Bloom \[erdosproblems\]. The logarithmic-scale construction of Theorem <a href="#long251:res:polignacfail" data-reference-type="ref" data-reference="long251:res:polignacfail">23</a> and the transfer argument of Theorem <a href="#long251:res:nonconcentration" data-reference-type="ref" data-reference="long251:res:nonconcentration">20</a> arose in an external review of an earlier draft of this note; both proofs printed here were checked independently.

<a id="long251:app:prime-bound"></a>

# An elementary polynomial bound for the primes

We prove $`p_n\le1250(n+1)^4`$ for every $`n\ge0`$. Let $`\pi(x)`$ count the primes at most $`x`$. For an integer $`m\ge4`$,
``` math
\begin{equation}
\label{long251:eq:binomial-bound}
 4^m<m\binom{2m}{m}\le m(2m)^{\pi(2m)} .
\end{equation}
```
For the first inequality, $`m\binom{2m}{m}/4^{m}`$ equals $`70/64`$ at $`m=4`$ and its ratio at successive indices is $`(2m+1)/(2m)>1`$. For the second, the exponent of a prime $`\ell`$ in $`\binom{2m}{m}`$ is $`\sum_{k\ge1}\bigl(\lfloor2m/\ell^{k}\rfloor-2\lfloor m/\ell^{k}\rfloor\bigr)`$, each summand is $`0`$ or $`1`$, and every summand with $`\ell^{k}>2m`$ vanishes; hence each prime power dividing $`\binom{2m}{m}`$ is at most $`2m`$, and there are $`\pi(2m)`$ of them.

Now fix $`n\ge0`$, put $`x=n+5`$ and $`m=x^4\ge625`$, and suppose $`\pi(2m)\le n`$. Since $`x\le2^{x}`$ and $`n+4(n+1)x=4x^2-15x-5\le2x^4`$,
``` math
m(2m)^{n}=2^{n}x^{4(n+1)}
 \le2^{\,n+4(n+1)x}\le2^{\,2x^4}=4^{m},
```
contradicting <a href="#long251:eq:binomial-bound" data-reference-type="eqref" data-reference="long251:eq:binomial-bound">[long251:eq:binomial-bound]</a>. Hence $`\pi(2m)>n`$, so at least $`n+1`$ primes lie below $`2m`$ and therefore
``` math
p_n\le2(n+5)^4\le1250(n+1)^4 ,
```
the last step because $`(n+5)\le5(n+1)`$ for $`n\ge0`$. The same bound is checked by the kernel at [line 360](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L360).

<a id="long251:app:certificates"></a>

# Integer certificates

The following calculation uses trial division and integer arithmetic only. It reproduces the two rows of Proposition <a href="#long251:res:finite-smallpair" data-reference-type="ref" data-reference="long251:res:finite-smallpair">15</a> and every inequality used in Theorem <a href="#long251:res:denominatorfloor" data-reference-type="ref" data-reference="long251:res:denominatorfloor">16</a>. The four literals are the certificate the Lean kernel decides in `KernelDenominatorFloor.lean`; their use here requires no floating-point approximation. Adjacent quoted strings are concatenated by Python.

    from math import isqrt

    primes = [n for n in range(2, 10000)
              if all(n % d for d in range(2, isqrt(n) + 1))]
    gaps = [q - p for p, q in zip(primes, primes[1:])]
    P = lambda x: x**4 + 8*x**3 + 36*x*x + 104*x + 150
    Q = 2**40
    expected = [(-662838684750, 11764181250),
                (873345886050, 12805761250)]
    for N, target in zip((2, 3), expected):
        D = sum((gaps[N+1+j] - gaps[N+j])*2**(40-j)
                for j in range(1, 41))
        B = 1250*(P(N+43) + P(N+42))
        distance = min(D % Q, Q - D % Q)
        if (D, B) != target or not (abs(D)+B < Q and B < distance):
            raise ArithmeticError("tail certificate failed")
    if gaps[4] == gaps[3]:
        raise ArithmeticError("gap mismatch failed")

    u = int(
        "8065641857152652932176019632186898003271162829171466334827"
        "3083607794415278717445033509407855988903369988525550746159"
        "7355889792250084202344821020139160956663658789718168152662"
        "0217"
    )

    v = int(
        "2194945124413663232143970924541263312422069524635615360518"
        "4247077351958221816830720189289904831662955084392690248683"
        "1216291723988537733235173040607254496838530213867781442335"
        "1745"
    )

    up = int(
        "6539437101498162626882411892470905222108260008568555445975"
        "3026163315521784668689909712759876562484620059098138417469"
        "5232839888185316374272333277389611483117334000493867584923"
        "912"
    )

    vp = int(
        "1779611075789866551198427241621709630120136323281598176637"
        "8490605249229735501968764904036152970729491656650873938580"
        "6203025466313389810291243786005499164537499383612081805160"
        "767"
    )

    c = len(primes)
    A = sum(p*2**(c-1-i) for i, p in enumerate(primes))
    checks = (c == 1229,
              u > 0 and v > 0 and up > 0 and vp > 0,
              up*v - u*vp == 1,
              u*2**c < A*v,
              (2*A + 5000*(c+1)**4)*vp < up*2**(c+1),
              v+vp >= 2**589,
              2**589 > 10**177)
    if not all(checks):
        raise ArithmeticError("denominator certificate failed")
    print("Both tail rows and the denominator floor verified.")

<a id="long251:app:index"></a>

# Guide to the formal sources

Each linked phrase opens its Lean declaration at the pinned source revision ee650b32b8b2. The summation-by-parts and prime-bound declarations are prime-specific. Section <a href="#long251:sec:tail" data-reference-type="ref" data-reference="long251:sec:tail">3</a> is stated for arbitrary integer digits and arbitrary rational or real orbits, while Section <a href="#long251:sec:local-certificate" data-reference-type="ref" data-reference="long251:sec:local-certificate">4</a> records the actual-gap specialisation. The concrete prime-gap tail, its unconditional convergence, its recurrence and the real-to-rational scaled-tail bridge are defined and checked in `RealPrimeGapTail.lean` and `PrimeGapDyadicTail.lean`; the free-pair lattice and its actual-series equivalence in `FreePairReduction.lean`; the kernel-decided denominator certificate in `KernelDenominatorFloor.lean`; the rational countermodels in `BoundedPerturbationCountermodel.lean` and `PolynomialGapSeriesValue.lean`; and the two circularity theorems in `AffineCylinderCollapse.lean`, with the signed normal form in `AffineShiftEscape.lean` and the lcm diagonal in `OrderLatticeDiagonal.lean`.

<a id="long251:sec:erdos-251-extended-record"></a>

# Extended record: displaced results, ordinary proofs and corrections

This section holds mathematics that belongs to the complete record for Problem #251 and sits outside the short note. Every statement here is labelled by its evidence class in the same vocabulary the note uses.

<a id="long251:sec:xr-totient"></a>

## The totient witness and forward propagation

The note states the exact denominator law <a href="#long251:eq:den-law" data-reference-type="eqref" data-reference="long251:eq:den-law">[long251:eq:den-law]</a> and uses it directly. The classical witness that produced it is worth recording, because it is the form in which the shift length first appears.

<div id="long251:xr:totient" class="proposition">

**Proposition 29** (a shift of totient length). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer digits. If the reduced denominator $`d`$ of $`T_N`$ is odd, then $`\sigma_{\varphi(d)}(N)`$ is an integer.*

</div>

<div class="proof">

*Proof.* Since $`d`$ is odd, $`2`$ and $`d`$ are coprime, so Euler’s congruence gives $`d\mid2^{\varphi(d)}-1`$. Writing $`2^{\varphi(d)}-1=dk`$ and $`T_N=u/d`$ in lowest terms, $`(2^{\varphi(d)}-1)T_N=ku`$ is an integer, and the integral-shift criterion transfers this to the shift. ◻

</div>

<div id="long251:xr:propagate" class="proposition">

**Proposition 30** (propagation). *If $`\sigma_h(N)`$ is an integer, then $`\sigma_h(N+k)`$ is an integer for every $`k\ge0`$.*

</div>

<div class="proof">

*Proof.* The shift step identity gives $`\sigma_h(N+1)=2\sigma_h(N)-(g_{N+h+1}-g_{N+1})`$, an integer combination of an integer and two digits. Induct on $`k`$. ◻

</div>

These are the totient shift and the propagation theorems cited in the note. Two worked instances. If $`\operatorname{den}T_N=3`$ then $`\varphi(3)=2`$ and $`3T_N`$ is an integer, so $`\sigma_2(N)`$ is integral while $`\sigma_1(N)`$ is not; if $`\operatorname{den}T_N=5`$ then $`\sigma_4(N)`$ is integral. In the orbit with every digit zero and $`T_0=1/12`$, the denominator is $`12=2^2\cdot3`$, the orbit reaches $`T_2=1/3`$ with odd denominator at $`s=2`$, and $`h=\varphi(3)=2`$ is exactly the shift length seen to be integral from index $`2`$ onwards. The totient is a witness rather than the classification: the exact criterion is $`\operatorname{den}(T_N)\mid2^{h}-1`$, and the least admissible $`h`$ is the multiplicative order of $`2`$ modulo the odd part.

<a id="long251:sec:xr-truncation"></a>

## The finite truncation criterion

The note gives the explicit remainder bound for the actual gaps. The general truncation statement behind it, valid for any dominating majorant, is the following.

<div id="long251:xr:truncation" class="proposition">

**Proposition 31** (finite truncation). *Let $`M(n)\ge g_n`$ for every $`n`$, assume the series below converges, and put
``` math
S_{h,N,L}=\sum_{j=1}^{L}\frac{g_{N+h+j}-g_{N+j}}{2^{\,j}},\qquad
 R_{h,N,L}(M)=\sum_{j>L}\frac{M(N+h+j)+M(N+j)}{2^{\,j}} .
```
If for every $`h\ge1`$ and every $`N_0`$ there are $`N\ge N_0`$ and $`L\ge1`$ with $`\operatorname{dist}(S_{h,N,L},\mathbb{Z})>R_{h,N,L}(M)`$, then the universal shift escape of Problem <a href="#long251:prob:escape" data-reference-type="ref" data-reference="long251:prob:escape">27</a> holds.*

</div>

<div class="proof">

*Proof.* The part of $`\sum_{j\ge1}(g_{N+h+j}-g_{N+j})2^{-j}`$ omitted from $`S_{h,N,L}`$ has absolute value at most $`R_{h,N,L}(M)`$, so under the displayed inequality the full sum lies at positive distance from every integer. ◻

</div>

The truncation is an exact modular small-arc problem. Writing the integral dyadic block
``` math
D_{h,N,L}=\sum_{j=1}^{L}2^{\,L-j}(g_{N+h+j}-g_{N+j}),
 \qquad S_{h,N,L}=\frac{D_{h,N,L}}{2^{L}},
```
one has
``` math
\operatorname{dist}(S_{h,N,L},\mathbb{Z})
 =2^{-L}\min\bigl\{D_{h,N,L}\bmod2^{L},\;
 2^{L}-(D_{h,N,L}\bmod2^{L})\bigr\},
```
where $`D_{h,N,L}\bmod2^{L}`$ is the least nonnegative residue, including when $`D_{h,N,L}<0`$. The finite criterion therefore asks the residue of $`D_{h,N,L}`$ to avoid the two arcs of radius $`2^{L}R_{h,N,L}(M)`$ around $`0`$ modulo $`2^{L}`$. A one-block certificate would be a prime-gap theorem producing such an avoided arc on a logarithmic block. This rewriting is paper-level and carries no Lean declaration.

<a id="long251:sec:xr-divisorhit"></a>

## A weaker recurrence-level target

<div id="long251:xr:divisor-hit" class="problem">

**Problem 32** (divisor-hitting shift escape). For every $`r\ge1`$, does some positive multiple of $`r`$ escape cofinally, in the sense of <a href="#long251:eq:shift-escape" data-reference-type="eqref" data-reference="long251:eq:shift-escape">[long251:eq:shift-escape]</a> at shift length $`mr`$ for some $`m\ge1`$?

</div>

A hypothetical rational value produces an eventually integral fixed shift, and the tail-shift cocycle propagates integrality forward and through positive multiples of that shift, so hitting one compatible multiple suffices in place of escaping at every prescribed $`h`$. Forward propagation is Lean-checked; the short multiple-in-shift closure is an elementary paper-level derivation with no named declaration, so this is recorded as a sharper proposed criterion rather than a registered equivalence.

<a id="long251:sec:xr-compression"></a>

## Two ordinary proofs about the free-pair producer

Both statements below are ordinary proofs recorded in the private research development. Neither is formalised and neither carries an independent check.

<a id="state-compression."></a>

#### State compression.

Exchanging the order of summation gives $`\sum_{N\le X}T_N\le(p_{X+1}-p_0)+2T_X`$. Under rationality with reduced odd denominator $`d`$, Markov’s inequality supplies for each $`C>1`$ a set $`B\subseteq(X,2X]`$ of density at least $`1-1/C`$ on which $`T_N\le C\log p_{2X}`$; on that set $`T_N`$ lies in $`\tfrac1d\mathbb{Z}`$ and takes at most $`dC\log p_{2X}+1`$ values, so some single value is attained more than a constant multiple of $`X/\log X`$ times. Rationality therefore makes the tail a finite-state object at every scale: pairs with $`T_M=T_N`$ are abundant for free, and the whole difficulty in the free-pair producer is nonintegrality of the difference. The naive form $`\sum_{N\le X}T_N\le p_{X+1}`$ is false.

<a id="redundancy-of-the-gap-condition."></a>

#### Redundancy of the gap condition.

Under the free-pair lattice the difference $`T_M-T_N`$ is an integer whenever the modulus divides the offset, and an integer cannot lie in $`(\tfrac12,1)`$. The half-window component of the reduced event of Theorem <a href="#long251:res:signedwindow" data-reference-type="ref" data-reference="long251:res:signedwindow">13</a> is therefore already a contradiction on its own, and the gap-mismatch condition adds nothing to it. That changes which component a proof has to produce.

<a id="long251:sec:xr-boundedpolignac"></a>

## A bounded companion to the recurring-values countermodel

Theorem <a href="#long251:res:polignacfail" data-reference-type="ref" data-reference="long251:res:polignacfail">23</a> carries a logarithmic growth profile so that its cumulative sequence matches the primes. The mechanism is visible in a much smaller example, which is recorded here because it is checkable by hand.

<div id="long251:xr:boundedpolignac" class="proposition">

**Proposition 33** (bounded recurring-values countermodel). *Put $`U_0=4`$ and, for $`n\ge1`$, $`U_n=6`$ when $`n=k!`$ for some $`k\ge3`$ and $`U_n=4`$ otherwise, and set $`a_n=2U_{n-1}-U_n`$ for $`n\ge1`$. Then $`a_n\in\{2,4,8\}`$, the value $`2`$ occurs at every index $`k!`$ and the value $`4`$ at every index $`2\,k!`$, so both recur infinitely often at indices divisible by any fixed $`t\ge1`$. The series $`\sum_{n\ge1}a_n2^{-n}`$ equals $`4`$ and every tail $`\sum_{j\ge1}a_{N+j}2^{-j}`$ equals the integer $`U_N`$.*

</div>

<div class="proof">

*Proof.* For $`k\ge3`$ the index $`k!`$ is even and at least $`6`$, and $`k!-1`$ is odd, so the predecessor of a spike is an ordinary index; hence $`a_{k!}=8-6=2`$, $`a_{k!+1}=12-4=8`$, and $`a_n=8-4=4`$ elsewhere. For $`k\ge2`$ one has $`k!<2\,k!<(k+1)!`$, so $`2\,k!`$ is not a factorial, and $`2\,k!-1`$ is odd so it is not a factorial either; therefore $`a_{2k!}=4`$. Since $`t\mid k!`$ for every large $`k`$, both values recur in the residue class $`0`$ modulo $`t`$. The identity $`a_n2^{-n}=U_{n-1}2^{-(n-1)}-U_n2^{-n}`$ telescopes to $`\sum_{j=1}^{m}a_{N+j}2^{-j}=U_N-U_{N+m}2^{-m}`$, and $`U`$ is bounded, so the endpoint vanishes. ◻

</div>

The cumulative sequence of this word grows linearly, which is the one property that separates it from the primes and the reason the note carries the logarithmic version instead. Both refute the same generic implication.

<a id="long251:sec:xr-densities"></a>

## The measured densities in full

The note reports the range of the adjacent-mismatch density. The per-offset figures below come from the same scan over the $`6\,841\,648`$ primes under $`1.2\times10^{8}`$, with double-precision tails.

<div class="center">

| $`h`$ | events |  density | $`\delta=+2`$ | $`\delta=-2`$ | last event at prime |
|------:|-------:|---------:|--------------:|--------------:|--------------------:|
|     1 | 56 427 | 0.008248 |        28 022 |        28 405 |         119 995 753 |
|     2 | 31 979 | 0.004674 |        15 742 |        16 237 |         119 993 807 |
|     3 | 30 233 | 0.004419 |        15 093 |        15 140 |         119 998 321 |
|     4 | 29 262 | 0.004277 |        14 606 |        14 656 |         119 993 473 |

</div>

Every offset $`h\le16`$ has events, with minimum density $`0.00418`$ and maximum $`0.008248`$; the two signs are near balanced at every offset. For $`h=1`$ the eight band densities, and the same figures after rescaling by the band mean of $`\log p`$, run
``` math
\begin{array}{l}
 0.011285,\;0.008951,\;0.008303,\;0.007936,\;0.007651,\;0.007507,\;0.007253,\;0.007094;\\[2pt]
 0.17671,\;0.15058,\;0.14420,\;0.14067,\;0.13766,\;0.13667,\;0.13333,\;0.13148 .
\end{array}
```
The rescaled drift is $`0.744`$ at $`h=1`$ and lies between $`0.744`$ and $`0.8121`$ across all offsets. Theorem <a href="#long251:res:sparse" data-reference-type="ref" data-reference="long251:res:sparse">22</a> proves that the limiting density is zero, so the observed decline is the expected behaviour rather than a failure of the event.

<a id="long251:sec:xr-corrections"></a>

## Corrections to earlier records

<a id="the-superseded-exclusion."></a>

#### The superseded exclusion.

An earlier internal record narrated a denominator exclusion at $`10^{602}`$. That figure is correct as written and is superseded twice over: by the kernel-decided floor $`2^{589}>10^{177}`$ of Theorem <a href="#long251:res:denominatorfloor" data-reference-type="ref" data-reference="long251:res:denominatorfloor">16</a>, which is smaller but kernel-checked, and by the certified continued-fraction exclusion $`2^{39997}>10^{12040}`$ of Theorem <a href="#long251:res:cfexclusion" data-reference-type="ref" data-reference="long251:res:cfexclusion">17</a>, which supersedes it in strength. The receipt records the decimal digit count $`12041`$; the certified decimal statement uses the exponent $`12040`$.

<a id="the-named-missing-input."></a>

#### The named missing input.

An earlier record named Hardy-Littlewood $`k`$-tuple correlation of consecutive gaps at a fixed offset as the missing input. With the offset freed by Theorem <a href="#long251:res:freepair" data-reference-type="ref" data-reference="long251:res:freepair">8</a> the route needs, for each modulus $`t`$, cofinally many congruent pairs with certified nonintegral tail difference. A further record proposed that two even values differing by $`2`$, each occurring infinitely often inside a common index residue class, would supply the two-condition form. No proof of that implication was ever produced, and Theorem <a href="#long251:res:polignacfail" data-reference-type="ref" data-reference="long251:res:polignacfail">23</a> shows that no proof exists at the level of integer-digit recurrences. That entry is withdrawn.

<a id="the-formal-boundary."></a>

#### The formal boundary.

An earlier reading of the short note placed the real-tail bridge and the real form of the adjacent-pair consumer on the paper side. Both are kernel-checked, at [line 48](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L48) and [line 99](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L99) of the real prime-gap tail module. A second reading placed the kernel-decided denominator floor and the free-pair criterion outside the source revision the note pins. Both modules are present at that revision, and both are linked from the note.

<a id="sec:erdos-251-complete-family-map"></a>

# Complete result-family map

This section places every registered family for this problem in the shared 70-family reader order. The five display bands control exposition only; the separate promotion state currently covers 6 families and is reported but does not hide or strengthen any family. Mathematical statements and evidence modes come from the public claim registry. Across all eight problems the public result-atom catalog contains 681 exact packet coordinates; this problem contributes 30. The recovered source catalog contains 682 rows; 1 row(s) belong to families absent from the current claim registry and remain disclosed as detached source rows. Catalog rows expose bounded statement excerpts plus full-source digests, not a claim that every complete packet statement is reproduced here.

<a id="prime-gap-reformulation"></a>

## Prime gap reformulation

**Reader position.** 4 of 70; display band: front door. Formal editorial disposition: promote. These are separate classifications.

**Reader entry.** Exact finite summation by parts, the unconditional infinite prime-gap identity, and irrationality equivalence.

Exact finite summation by parts, the unconditional infinite prime-gap identity, and irrationality equivalence.

**Authority and reach.** Lean kernel; Comparator-selected; locally proved result; novelty unassessed.

**Exact boundary.** The equivalence does not prove irrationality of either series.

**Result-atom population.** 4 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** exact selected interface; 1 executable interface(s), 1 repository-registered selected result interface(s).

**Publication placement.** This family remains in the complete long record and is not a short-note headline.

<a id="dyadic-tail-integrality-classification"></a>

## Dyadic tail integrality classification

**Reader position.** 11 of 70; display band: major result. Formal editorial disposition: merge. These are separate classifications.

**Reader entry.** For any integer-digit dyadic tail recurrence T(N+1) = 2\*T(N) - g(N+1), the rational h-shift is integral exactly when the reduced denominator of T(N) divides 2^h - 1, equivalently when 2^h is congruent to 1 modulo that denominator. For the real recurrence, the load-bearing normal form says that irrationality of T(0) is equivalent to every positive tail shift being nonintegral; the eventual-integrality equivalence and denominator/order laws are supporting mechanism evidence.

For any integer-digit dyadic tail recurrence T(N+1) = 2\*T(N) - g(N+1), the rational h-shift is integral exactly when the reduced denominator of T(N) divides 2^h - 1, equivalently when 2^h is congruent to 1 modulo that denominator. For the real recurrence, the load-bearing normal form says that irrationality of T(0) is equivalent to every positive tail shift being nonintegral; the eventual-integrality equivalence and denominator/order laws are supporting mechanism evidence.

**Authority and reach.** Lean kernel; Comparator-selected; abstract Lean-checked classification and normal form; novelty unassessed.

**Exact boundary.** These exact statements cover arbitrary integer-digit dyadic tail recurrences with the declared rational and real state types; they classify integrality and give an irrationality normal form but do not supply a cofinal nonintegral shift for the consecutive-prime-gap recurrence. The generic hypotheses therefore do not close the prime-specific producer gap: no prime-gap irrationality, novelty, significance, or external review is claimed, and Erdős \#251 remains open. This is one abstract classification family, distinct from prime_gap_reformulation, not a duplicate frontier claim.

**Result-atom population.** 10 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** exact selected interface; 1 executable interface(s), 1 repository-registered selected result interface(s).

**Publication placement.** This family remains in the complete long record and is not a short-note headline.

- `ErdosProblems.Erdos251.tailShift_integral_iff_den_dvd_mersenne`

- `ErdosProblems.Erdos251.tailShift_integral_iff_two_pow_modEq_one`

- `ErdosProblems.Erdos251.not_irrational_initial_iff_exists_eventually_integral_positive_tailShift`

- `ErdosProblems.Erdos251.irrational_initial_iff_all_positive_tailShifts_nonintegral`

<a id="integral-shift-classification"></a>

## Integral shift classification

**Reader position.** 27 of 70; display band: mechanism. Formal editorial disposition: merge. These are separate classifications.

**Reader entry.** Block identities and exact denominator criteria classify rationality through integral positive tail shifts.

Block identities and exact denominator criteria classify rationality through integral positive tail shifts.

**Authority and reach.** Lean kernel; locally proved result; novelty unassessed.

**Exact boundary.** The concrete prime-gap producer remains missing.

**Result-atom population.** 1 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** not selected for comparator; 0 executable interface(s), 0 repository-registered selected result interface(s).

**Publication placement.** This family is also admitted to the short note.

- `ErdosProblems.Erdos251.irrational_initial_iff_all_positive_tailShifts_nonintegral`

- `ErdosProblems.Erdos251.not_irrational_initial_iff_exists_eventually_integral_positive_tailShift`

- `ErdosProblems.Erdos251.tailShift_integral_iff_den_dvd_mersenne`

- `ErdosProblems.Erdos251.tailShift_integral_iff_two_pow_modEq_one`

<a id="small-mismatch-criterion"></a>

## Small mismatch criterion

**Reader position.** 45 of 70; display band: frontier. Formal editorial disposition: hold. These are separate classifications.

**Reader entry.** For the actual prime-gap dyadic tail, cofinally many adjacent pairs of strictly small h-shifts with unequal corresponding prime gaps force failure of eventual RatIntegral h-shifts. The adjacent-pair zero obstruction is the load-bearing mechanism; exact non-eventual periodicity of consecutive prime gaps supplies the actual-prime-gap contrast.

For the actual prime-gap dyadic tail, cofinally many adjacent pairs of strictly small h-shifts with unequal corresponding prime gaps force failure of eventual RatIntegral h-shifts. The adjacent-pair zero obstruction is the load-bearing mechanism; exact non-eventual periodicity of consecutive prime gaps supplies the actual-prime-gap contrast.

**Authority and reach.** Lean kernel; Comparator-selected; conditional actual-prime-gap endpoint reduction; novelty and significance unassessed.

**Exact boundary.** The representative assumes T : $`\mathbb{N}`$ $`\to`$ $`\mathbb{Q}`$, the DyadicTailRecurrence for the actual prime-gap digits, and for every N$`_{0}`$ an N $`\ge`$ N$`_{0}`$ whose adjacent h-shifts both lie strictly in (-1, 1) while the corresponding prime gaps differ. Under that cofinal small-mismatch supply it excludes eventual RatIntegral h-shifts; it does not prove the supply or actual smallness. rationalPrimeGapTail_has_positive_shift_not_eventually_small records the contrary rational-state obstruction for at least one positive shift. This is a conditional reduction only: no \#251 irrationality, infinite rational-sum limit, universal producer, novelty, priority, significance, or external-review claim is made; \#251 remains open. The actual-prime-gap specialization is distinct from coefficient_only_no_go and does not duplicate prime_gap_reformulation.

**Result-atom population.** 10 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** exact selected interface; 1 executable interface(s), 1 repository-registered selected result interface(s).

**Publication placement.** This family is also admitted to the short note.

- `ErdosProblems.Erdos251.primeGapTailShift_not_eventuallyIntegral_of_cofinal_small_mismatch`

- `ErdosProblems.Erdos251.not_eventuallyIntegralTailShift_of_cofinal_small_mismatch`

- `ErdosProblems.Erdos251.tailShift_not_both_integral_of_small_pair_of_digit_ne`

- `ErdosProblems.Erdos251.primeGap0_not_eventually_periodic`

- `ErdosProblems.Erdos251.rationalPrimeGapTail_has_positive_shift_not_eventually_small`

<a id="coefficient-only-no-go"></a>

## Coefficient only no go

**Reader position.** 51 of 70; display band: frontier. Formal editorial disposition: hold. These are separate classifications.

**Reader entry.** The exact finite carry identity and the two non-eventual-periodicity statements expose the coefficient-only barrier: irregularity and growth of a coefficient stream do not by themselves force irrationality, while the synthetic carry stream remains distinct from the actual prime-gap stream.

The exact finite carry identity and the two non-eventual-periodicity statements expose the coefficient-only barrier: irregularity and growth of a coefficient stream do not by themselves force irrationality, while the synthetic carry stream remains distinct from the actual prime-gap stream.

**Authority and reach.** Lean kernel plus authored synthesis; coefficient-only barrier; novelty and significance unassessed.

**Exact boundary.** CoefficientOnlyNoGo checks the exact finite partial-sum identity and the two non-eventual-periodicity statements. It does not assert the infinite limit of the synthetic countermodel, identify its coefficient stream with actual prime gaps, establish a prime-gap tail bridge, prove \#251 irrationality, or make novelty, priority, significance, or external-review claims.

**Result-atom population.** 3 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** exact selected interface; 2 executable interface(s), 2 repository-registered selected result interface(s).

**Publication placement.** This family is also admitted to the short note.

- `ErdosProblems.Erdos251.carryPartialSum_natCast_eq`

- `ErdosProblems.Erdos251.carryCoeff_natCast_not_eventually_periodic`

- `ErdosProblems.Erdos251.primeGap0_not_eventually_periodic`

<a id="totient-shift-propagation"></a>

## Totient shift propagation

**Reader position.** 60 of 70; display band: technical support. Formal editorial disposition: merge. These are separate classifications.

**Reader entry.** Odd rational denominators give totient-length integral shifts, and integrality propagates through the recurrence.

Odd rational denominators give totient-length integral shifts, and integrality propagates through the recurrence.

**Authority and reach.** Lean kernel; locally proved result; novelty unassessed.

**Exact boundary.** This describes rational states and supplies no contradiction for actual prime gaps.

**Result-atom population.** 2 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** represented by selected interface; 0 executable interface(s), 0 repository-registered selected result interface(s).

**Publication placement.** This family remains in the complete long record and is not a short-note headline.

- `ErdosProblems.Erdos251.tailShift_integral_totient_of_odd_den`

- `ErdosProblems.Erdos251.tailShift_integral_succ`

- `ErdosProblems.Erdos251.tailShift_integral_add`

<div class="thebibliography">

99

P. Erdős, [*Sur certaines séries à valeur irrationnelle*](https://users.renyi.hu/~p_erdos/1958-19.pdf), Enseign. Math. (2) **4** (1958), 93–100, doi:[10.5169/seals-34629](https://doi.org/10.5169/seals-34629). The dyadic prime series is stated as unproved on p. 94; the factorial-prime family is stated on p. 93, with only the $`k=1`$ proof printed on pp. 94–95; the variable-denominator classification, with nondecreasing denominators and a lower growth condition, is Theorem §3 on pp. 96–97. P. Erdős and R. L. Graham, [*Old and New Problems and Results in Combinatorial Number Theory*](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf), Monogr. Enseign. Math. 28, Geneva, 1980, p. 62. P. Erdős and C. Pomerance, [*On the largest prime factors of $`n`$ and $`n+1`$*](https://doi.org/10.1007/BF01818569), Aequationes Math. **17** (1978), 311–321, doi:[10.1007/BF01818569](https://doi.org/10.1007/BF01818569). The unnumbered dyadic irrationality theorem and its complete proof are in §7 on p. 320. P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). P. Erdős and E. G. Straus, *On the irrationality of certain Ahmes series*, J. Indian Math. Soc. (N.S.) **27** (1964), 129–133. MR 175848. K. Ford, B. Green, S. Konyagin, J. Maynard and T. Tao, *Long gaps between primes*, J. Amer. Math. Soc. **31** (2018), 65–105, doi:[10.1090/jams/876](https://doi.org/10.1090/jams/876). Theorem 1 on p. 66 gives the effective lower bound for the largest single consecutive-prime gap below $`X`$. A. Ya. Khinchin, *Continued Fractions*, University of Chicago Press, Chicago, 1964. Cited for the classical fact that a best approximation of the second kind is a convergent, which converts a certified partial-quotient prefix into a denominator lower bound. V. Kovač and T. Tao, [*On several irrationality problems for Ahmes series*](https://doi.org/10.1007/s10474-025-01528-0), Acta Math. Hungar. **175** (2025), 572–608. J. Land, [*A conditional proof of the irrationality of $`\sum_{n\ge1}p_n2^{-n}`$ under a uniform Hardy-Littlewood prime-tuples conjecture*](https://github.com/beetree/math_erdos_251), research draft, 5 September 2026, with an accompanying Lean formalisation of the conditional argument. Its Conjecture 1 is the large-$`x`$ form of Conjecture 1.3 of V. Kuperberg, *Sums of singular series with large sets and the tail of the distribution of primes*, arXiv:2210.09775v2, 15 June 2023. L. de Moura and S. Ullrich, [*The Lean 4 theorem prover and programming language*](https://doi.org/10.1007/978-3-030-79876-5_37), in A. Platzer and G. Sutcliffe (eds.), CADE 28, Lecture Notes in Comput. Sci. 12699, Springer, 2021, pp. 625–635, doi:[10.1007/978-3-030-79876-5_37](https://doi.org/10.1007/978-3-030-79876-5_37). The mathlib Community, [*The Lean mathematical library*](https://doi.org/10.1145/3372885.3373824), in CPP 2020, ACM, 2020, pp. 367–381, doi:[10.1145/3372885.3373824](https://doi.org/10.1145/3372885.3373824). The article describes a December 2019 Lean 3-era snapshot; the current revision is the one named in the repository lock. J. Maynard, [*Small gaps between primes*](https://doi.org/10.4007/annals.2015.181.1.7), Ann. of Math. (2) **181** (2015), 383–413. J.-C. Schlage-Puchta, [*The irrationality of some number theoretical series*](https://arxiv.org/abs/1105.1451), arXiv:1105.1451, 2011. Theorem 2 treats base-$`b`$ digit strings that concatenate the representations of a slowly growing integer sequence; Theorem 3 gives the $`\mathbb{Q}`$-linear independence of $`1,S_0,S_1,\ldots`$ with $`S_k=\sum_{n\ge1}p_n^{k}/n!`$; Lemma 4, on pp. 5–6, states that for every nonzero $`F\in\mathbb{Z}[x_0,\ldots,x_k]`$ the equation $`F(\delta_n,\ldots,\delta_{n+k})=0`$ holds for a set of $`n`$ of density zero, where $`\delta_n=p_{n+1}-p_n`$, and its proof uses Selberg’s sieve. Y. Zhang, [*Bounded gaps between primes*](https://doi.org/10.4007/annals.2014.179.3.7), Ann. of Math. (2) **179** (2014), 1121–1174. T. F. Bloom, [*Erdős Problem \#251*](https://www.erdosproblems.com/251), `erdosproblems.com/251`, accessed 6 September 2026 (page displays “last edited 28 September 2025”). The current record labels the main dyadic problem open, cites `[Er58b]`, `[ErGr80, p. 62]` and `[Er88c, p. 103]`, attributes the whole factorial-prime family to the 1958 article, and explicitly describes its status as the website owner’s present assessment, with no guarantee of literature completeness; it does not mention the 2026 counterexample in \[kovac2026\] to the adjacent variable-denominator conjecture. *Erdős Problem \#251 discussion thread*, `erdosproblems.com/forum/thread/251`, accessed 6 September 2026. Cited for T. Tao’s comment of 17:17 on 7 October 2025 recording the summation-by-parts equivalence and naming a uniform quantitative prime-tuples hypothesis as a plausible route, and for the two comments of J. Land of 6 September 2026 announcing \[land2026\]. Comments on that site are the responsibility of their authors and are not verified for correctness by the catalogue. ChatGPT 5.4 Pro (orchestrated by V. Kovač), [*On the Erdős problem \#251*](https://web.math.pmf.unizg.hr/~vjekovac/files/Erdos_problem_251.pdf), unpublished note, 2026, hosted by the Department of Mathematics, University of Zagreb, `web.math.pmf.unizg.hr`, accessed 6 September 2026; posted as a thread comment at 11:13 on 15 April 2026 \[erdosproblems251thread\]. The Formal Conjectures Authors, [*FormalConjectures.ErdosProblems.`251`*](https://github.com/google-deepmind/formal-conjectures/blob/f776d2f2039351b00737ffcafb9d7d7666e1d9af/FormalConjectures/ErdosProblems/251.lean), Lean source at commit `f776d2f`, 2025, accessed 28 July 2026.

</div>
