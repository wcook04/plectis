<a id="erdos-251-prime-gap-dyadic-series"></a>

# An Integral-Shift Criterion for Dyadic Tail Recurrences

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

The contribution is a Lean-checked rigidity criterion for dyadic tails and an exact reduction of the prime series to the prime-gap series. If a real sequence satisfies $`T_{N+1}=2T_N-g_{N+1}`$ with integer digits, then
``` math
T_{N+h}=2^hT_N-
 \bigl(g_{N+1}2^{h-1}+\cdots+g_{N+h}\bigr).
```
For rational $`T_0`$, denominator arithmetic and propagation therefore give one fixed $`h\ge1`$ for which $`T_{N+h}-T_N`$ is integral at every sufficiently large $`N`$. Contrapositively, cofinal non-integrality for every fixed $`h`$ forces $`T_0`$ to be irrational. This abstract criterion is proved; the required cofinal property for the actual prime-gap tails is not.

Let $`p_0=2,p_1=3,\ldots`$ enumerate the primes and let $`g_n=p_{n+1}-p_n`$. We formalise in Lean both the exact finite identity
``` math
\sum_{i=0}^{n}\frac{p_i}{2^{\,i+1}}
 \;=\;2+\sum_{i=0}^{n-1}\frac{g_i}{2^{\,i+1}}-\frac{p_n}{2^{\,n+1}},
```
and, conditional only on summability, the infinite identity and irrationality equivalence
``` math
\sum_{i\ge0}\frac{p_i}{2^{\,i+1}}
 =2+\sum_{i\ge0}\frac{g_i}{2^{\,i+1}},\qquad
 \operatorname{Irr}\!\left(\sum_{i\ge0}\frac{p_i}{2^{\,i+1}}\right)
 \Longleftrightarrow
 \operatorname{Irr}\!\left(\sum_{i\ge0}\frac{g_i}{2^{\,i+1}}\right).
```
The prime number theorem supplies summability externally; it is an explicit hypothesis, not part of the Lean development.

Problem #251 remains open. A local theorem shows that adjacent shifts in $`(-1,1)`$ cannot both be integers when the corresponding prime gaps differ, so cofinally many such small-mismatch pairs would suffice. Unboundedness and nonperiodicity of the prime gaps, although Lean-checked, do not control the tails: we exhibit an unbounded, nonperiodic integer sequence whose dyadic sum is rational. The missing input must therefore control the full prime-gap tails, not merely individual gaps or eventual periodicity.

<a id="sec:problem"></a>

# Introduction

Let $`p_n`$ denote the $`n`$th prime. Erdős Problem #251 asks whether
``` math
\Pi=\sum_{n\ge1}\frac{p_n}{2^{\,n}}
```
is irrational \[erdos1958, p. 94\]\[erdosgraham1980, p. 62\] \[erdos1988, p. 103\]. Bloom’s current catalogue record reproduces this question and labels it open, while explicitly warning that the status is the website owner’s present assessment and may omit relevant literature \[erdosproblems\]. We therefore use the catalogue for numbering and current reported status only; the three original publications carry the mathematical claims. The problem is open. Numerically $`\Pi=2/2+3/4+5/8+7/16+11/32+\cdots=3.674643966\ldots`$.

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
the [factor-of-two normalisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L105). A factor of two does not change rationality, so no result below depends on the choice; the identity is stated so that the indexing cannot drift silently.

<a id="notation."></a>

#### Notation.

$`\mathbb{N}=\{0,1,2,\ldots\}`$ and $`\mathbb{N}_{>0}=\{1,2,\ldots\}`$. We write $`\varphi`$ for Euler’s totient function, $`\operatorname{den}q`$ for the denominator of a rational number $`q`$ written in lowest terms, $`\operatorname{dist}(x,\mathbb{Z})`$ for the distance from a real number $`x`$ to the nearest integer, and $`\operatorname{Irr}(x)`$ for the assertion that $`x`$ is irrational. A rational number is called *integral* when it is the image of an integer. A sequence $`(a_n)`$ is *eventually periodic with period $`h\ge1`$* when $`a_{n+h}=a_n`$ for every sufficiently large $`n`$. A sum over an empty range of indices is zero.

<a id="relation-to-prior-work."></a>

#### Relation to prior work.

Erdős proved that $`\sum_n p_n^{k}/n!`$ is irrational for every $`k\ge1`$ \[erdos1958, p. 93\]. The 1958 article gives the $`k=1`$ proof on pp. 94–95 and says explicitly that the more complicated $`k>1`$ proof is omitted. On page 103 of his 1988 problem paper he separately stated the fixed-denominator problem: he could not prove that $`\sum_n p_n^{k}/2^{n}`$ is irrational for every $`k\ge1`$, and wrote that the case $`k=1`$ was probably already very difficult. He also stated the variable-denominator expectation that $`\sum_{n\ge1}p_n/(g_1\cdots g_n)`$ is irrational whenever $`g_n\ge2`$ and $`g_n=o(p_n)`$ \[erdos1988, p. 103\]. The latter expectation is false: ChatGPT 5.4 Pro, orchestrated by Vjeko Kovač, constructs such a sequence $`(g_n)`$ for which the sum is exactly $`1`$  \[kovac2026, Theorem 1 and proof, pp. 1–2\]. Under the stronger hypotheses that $`(g_n)`$ is strictly increasing and $`g_n=O(n\log^k n)`$, Erdős had already classified the rational cases: rationality holds exactly when $`g_n=q p_n+1`$ eventually for one fixed integer $`q\ge1`$ \[erdos1958, pp. 96–99\]. The endpoint $`q=1`$ is included: if $`G_n=\prod_{j=1}^{n}(p_j+1)`$, then $`p_n/G_n=1/G_{n-1}-1/G_n`$, so the corresponding series telescopes to $`1`$. The counterexample evades those hypotheses. It does not address the fixed-denominator dyadic series studied here. The current catalogue record still repeats this variable-denominator expectation without mentioning the counterexample \[erdosproblems\]; its warning about possibly missing literature is therefore material here, not merely boilerplate.

There is also a genuinely adjacent proved dyadic theorem. If $`P(m)`$ denotes the largest prime factor of $`m`$, Erdős and Pomerance proved that
``` math
\sum_{m\ge2}\frac{\mathbf 1_{\{P(m)>P(m+1)\}}}{2^m}
```
is irrational \[erdospomerance1978, §7, p. 320\]. Erdős and Graham record the complementary indicator on p. 62: equality of the two largest prime factors is impossible for consecutive integers, so its series is $`1/2`$ minus the displayed one and is irrational as well. This is a theorem about a bounded prime-factor comparison digit sequence, not the unbounded prime numerators in $`\Pi`$; it supplies nearby positive evidence without solving Problem #251.

Problem #251 also appears as the unproved declaration `erdos_251` in the *Formal Conjectures* repository \[formalconjectures251\]. Its zero-based Lean sum starts with the zeroth prime over $`2^0`$, so it is twice the displayed normalisation and has equivalent irrationality status, but it is not literally the same indexing; its proof is `sorry`. No priority is claimed for anything below.

<a id="the-strategy."></a>

#### The strategy.

The digits $`p_n`$ grow, so the series is not a digit expansion in any bounded alphabet, and the standard rationality criteria for such expansions do not apply directly. The classical elementary criteria for series of this kind instead control irrationality through the growth of the denominators. Erdős and Straus named a sum $`\sum_k 1/a_k`$ over a strictly increasing sequence of positive integers an *Ahmes series* \[erdosstraus1963\]; for such a series the condition $`a_k^{1/2^k}\to\infty`$ is sufficient for irrationality, and it is sharp, since shifted Sylvester sequences grow like $`C^{2^{k}}`$ for arbitrarily large $`C`$ and have rational reciprocal sum. Both statements and their attribution are recorded in the introduction of Kovač and Tao \[kovactao2024, §1\], who develop the elementary technology for such series much further. Splitting each term $`p_i/2^{\,i+1}`$ into $`p_i`$ copies of $`2^{-(i+1)}`$ writes $`\Pi`$ as a sum of unit fractions, but with repetitions, and the denominators occurring in it are exactly the powers of two. Even ignoring the repetitions the growth hypothesis fails by every available margin, since $`(2^{\,n})^{1/2^{\,n}}\to1`$, and every arithmetic constraint has to come from the numerators instead.

What replaces growth control is denominator control on the sequence of rescaled tails. Rationality of the sum turns out to be equivalent to an eventual integrality condition on differences of those tails, and that condition uses nothing about the numerators beyond the fact that they are integers. The condition does not by itself force the numerators to repeat: Proposition <a href="#res:telescope" data-reference-type="ref" data-reference="res:telescope">15</a>, applied to $`K_n=n`$, produces the integer sequence $`\kappa_n=n-1`$, which is unbounded and hence not eventually periodic, and whose dyadic sum $`\sum_{n\ge0}\kappa_n2^{-(n+1)}`$ is zero.

<a id="outline."></a>

#### Outline.

Section <a href="#sec:parts" data-reference-type="ref" data-reference="sec:parts">2</a> replaces the primes by their consecutive gaps, the natural increments studied by prime-distribution theory. Summation by parts with the endpoint retained gives an exact finite identity, and the termwise relation $`v_n=2u_{n+1}-u_n`$ between the gap terms and the prime terms makes the passage to the limit a matter of summability alone; the prime number theorem supplies that summability externally. Section <a href="#sec:tail" data-reference-type="ref" data-reference="sec:tail">3</a> rescales the tails of a dyadic series into a recurrence and develops it: the block identity, the integral-shift criterion, the collapse of every rational solution onto an eventually integral shift, its contrapositive over the reals, and a local obstruction that converts an infinite-tail condition into a single comparison of gaps. Section <a href="#sec:carry" data-reference-type="ref" data-reference="sec:carry">4</a> shows that the tail constraint does not by itself make the coefficient sequence eventually periodic, and Section <a href="#sec:open" data-reference-type="ref" data-reference="sec:open">5</a> states the remaining obligation. The pinned Lean 4 toolchain and Mathlib revision check the formal statements. The cited system paper identifies Lean 4 \[lean4, abstract and §1, pp. 625–626\], while the Mathlib paper documents the library’s historical Lean 3-era architecture \[mathlib, abstract and §1.1, p. 367\]; it is not authority for the current pinned revision. Linked phrases open the corresponding declaration at the pinned source revision 7558c58afb7c.

*Status.* The problem treated here is open, and this note does not close it. Every statement below marked as checked is a proposition that the pinned Lean kernel accepts from the sources this note links to, with no `sorry`, no added axiom, and no unchecked evaluation. That is a claim about the formal statement, not about its mathematical interest, its novelty, or the original problem. The unresolved obligations are named exactly, in their own section, and none of the finite computations, reductions, or no-go results here removes one of them.

| Statement | Status | Treatment here |
|:---|:---|:---|
| Irrationality of $`\Pi`$ | Open | Not proved. |
| Finite prime-gap identity | Proved here | Theorem <a href="#res:parts" data-reference-type="ref" data-reference="res:parts">2</a>, with the endpoint retained. |
| Infinite prime-gap identity | Lean-checked conditionally | Theorem <a href="#res:infinite" data-reference-type="ref" data-reference="res:infinite">3</a>; the prime number theorem supplies the hypothesis externally. |
| Prime-series/gap-series irrationality equivalence | Lean-checked conditionally | Corollary <a href="#res:irr-equivalence" data-reference-type="ref" data-reference="res:irr-equivalence">4</a>. |
| Block identity for the tail recurrence | Proved here | Theorem <a href="#res:block" data-reference-type="ref" data-reference="res:block">6</a>. |
| Integral shift criterion | Proved here; an equivalence | Theorem <a href="#res:shiftiff" data-reference-type="ref" data-reference="res:shiftiff">7</a>. |
| Totient shift from an odd denominator | Proved here | Theorem <a href="#res:totient" data-reference-type="ref" data-reference="res:totient">8</a>. |
| Propagation of an integral shift | Proved here | Theorem <a href="#res:propagate" data-reference-type="ref" data-reference="res:propagate">9</a>. |
| Eventual integral shift for every rational-valued recurrence | Lean-checked | Theorem <a href="#res:collapse" data-reference-type="ref" data-reference="res:collapse">10</a>. |
| Cofinal shift escape implies irrationality | Lean-checked abstractly | Theorem <a href="#res:escape-irrational" data-reference-type="ref" data-reference="res:escape-irrational">11</a>. |
| Finite-approximation gap | Lean-checked over $`\mathbb{Q}`$ | Its real-valued use in Proposition <a href="#res:truncation" data-reference-type="ref" data-reference="res:truncation">18</a> is paper-level. |
| Actual prime gaps are unbounded and not eventually periodic | Lean-checked | Proposition <a href="#res:gap-nonperiodic" data-reference-type="ref" data-reference="res:gap-nonperiodic">14</a>. |
| Adjacent small-mismatch pair excludes simultaneous integrality | Lean-checked | Theorem <a href="#res:smallpair" data-reference-type="ref" data-reference="res:smallpair">12</a>. |
| Concrete prime-gap tail recurrence | Paper-proved from PNT | Not yet instantiated as a Lean infinite sum. |
| Rationality alone forces periodic integer coefficients | False | Section <a href="#sec:carry" data-reference-type="ref" data-reference="sec:carry">4</a>, Proposition <a href="#res:telescope" data-reference-type="ref" data-reference="res:telescope">15</a>. |
| Cofinal adjacent small-mismatch hypothesis | Proposed sufficient theorem | Problem <a href="#prob:smallpair" data-reference-type="ref" data-reference="prob:smallpair">17</a>; not proved. |

<div class="minipage">

*How to read the middle column.* *Proved here* marks a statement proved in the text; each such statement also carries a link to a Lean declaration where it appears below. *Lean-checked* marks a statement the pinned kernel accepts, in the exact sense fixed by the Status paragraph above. The modifier *conditionally* marks a hypothesis that the Lean statement carries and that ordinary mathematics discharges from outside the formal development; *abstractly* marks a statement proved for an arbitrary integer digit sequence rather than for the actual prime gaps. *Paper-proved from PNT* marks a statement proved in the text from the prime number theorem and not formalised. *Proposed sufficient theorem* marks an unproved statement which, if proved, would give irrationality of $`\Pi`$.

</div>

**Keywords.** irrationality; prime gaps; dyadic series; summation by parts; Lean 4. **MSC 2020.** 11J72 (primary); 11N05, 68V20 (secondary).

<a id="sec:parts"></a>

# Summation by parts, with the endpoint retained

Summation by parts trades a sequence for its consecutive differences. The form recorded here is exact: it carries no error term, it assumes nothing about the sequence, and it retains the endpoint term rather than absorbing it into an estimate. For a sequence $`P`$ of rational numbers and $`n\ge0`$ put
``` math
D(P,n)=\sum_{i=0}^{n-1}\frac{P(i)}{2^{\,i+1}},
 \qquad
 \Delta(P,n)=\sum_{i=0}^{n-1}\frac{P(i+1)-P(i)}{2^{\,i+1}} ,
```
both empty, hence zero, at $`n=0`$. We call these the [dyadic partial sum](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L95) and the [dyadic difference sum](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L115) of $`P`$.

<div id="res:abel" class="proposition">

**Proposition 1** (finite summation by parts). *For every rational sequence $`P`$ and every $`n\ge0`$,
``` math
D(P,n+1)=P(0)+\Delta(P,n)-\frac{P(n)}{2^{\,n+1}} .
```*

</div>

<div class="proof">

*Proof.* A routine induction on $`n`$. At $`n=0`$ both sides equal $`P(0)/2`$. For the step, adding $`P(n+1)/2^{\,n+2}`$ to the left and $`\bigl(P(n+1)-P(n)\bigr)/2^{\,n+1}`$ to the difference sum changes the endpoint term from $`P(n)/2^{\,n+1}`$ to $`P(n+1)/2^{\,n+2}`$, and the two adjustments agree. ◻

</div>

Formalised as the [summation-by-parts identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L132). Nothing is assumed about $`P`$: no positivity, no monotonicity, and no convergence.

Specialising to $`P(i)=p_i`$, whose first value is $`p_0=2`$, and writing $`g_i=p_{i+1}-p_i`$ for the zero-based gaps, gives the reformulation.

<div id="res:parts" class="theorem">

**Theorem 2** (prime-gap reformulation). *Let $`p_0=2,p_1=3,\ldots`$ be the primes in increasing order and $`g_i=p_{i+1}-p_i`$. For every $`n\ge0`$,
``` math
\sum_{i=0}^{n}\frac{p_i}{2^{\,i+1}}
 =2+\sum_{i=0}^{n-1}\frac{g_i}{2^{\,i+1}}-\frac{p_n}{2^{\,n+1}} .
```*

</div>

Formalised as the [prime-gap summation by parts](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L161), using the [gap partial sum](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L155) and the [gap cast identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L150); the latter records that the natural-number difference $`p_{n+1}-p_n`$ agrees with the difference taken in $`\mathbb{Q}`$, which needs $`p_n\le p_{n+1}`$, the [monotonicity step](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L146). The leading $`2`$ is the first prime, not a normalising constant. At $`n=2`$, for instance, the left side is $`2/2+3/4+5/8=19/8`$ and the right side is $`2+(1/2+2/4)-5/8=19/8`$.

<a id="sec:infinite"></a>

## The infinite identity and the irrationality equivalence

Write
``` math
u_n=\frac{p_n}{2^{\,n+1}},\qquad
 v_n=\frac{g_n}{2^{\,n+1}}
```
for the terms of the prime series and of the gap series, so that $`\sum_{n\ge0}u_n=\Pi`$. The termwise identity $`v_n=2u_{n+1}-u_n`$ is the [dyadic discrete derivative](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L191). It expresses each gap term as an integer combination of two consecutive prime terms, so once $`(u_n)`$ is summable the gap series can be summed by rearranging two copies of the prime series, which is what the following proof does.

<div id="res:infinite" class="theorem">

**Theorem 3** (infinite prime-gap identity). *Let $`u_n=p_n/2^{\,n+1}`$ and $`v_n=g_n/2^{\,n+1}`$. If $`(u_n)`$ is summable, then $`(v_n)`$ is summable and
``` math
\sum_{n\ge0}u_n=2+\sum_{n\ge0}v_n .
```*

</div>

<div class="proof">

*Proof.* The shifted sequence $`(u_{n+1})`$ is summable. Sum $`v_n=2u_{n+1}-u_n`$ and use $`u_0=1`$:
``` math
\sum_{n\ge0}v_n
 =2\left(\sum_{n\ge0}u_n-u_0\right)-\sum_{n\ge0}u_n
 =\sum_{n\ge0}u_n-2 .
```
 ◻

</div>

The summability transfer is the [gap-series summability theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L202), and the displayed identity is the [infinite prime-gap identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L214).

<div id="res:irr-equivalence" class="corollary">

**Corollary 4** (exact irrationality reformulation). *With $`u_n`$ and $`v_n`$ as in Theorem <a href="#res:infinite" data-reference-type="ref" data-reference="res:infinite">3</a>, and $`(u_n)`$ summable,
``` math
\operatorname{Irr}\!\left(\sum_{n\ge0}u_n\right)
 \quad\Longleftrightarrow\quad
 \operatorname{Irr}\!\left(\sum_{n\ge0}v_n\right).
```
The corresponding zero-based series with denominator $`2^n`$ is $`4+2\sum_{n\ge0}v_n`$ and has the same irrationality status.*

</div>

These are the [normalised irrationality equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L239), the [displayed-series identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L248), and the [displayed-series irrationality equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L263).

<a id="the-summability-hypothesis."></a>

#### The summability hypothesis.

The prime number theorem, proved by Hadamard and by de la Vallée Poussin in 1896, is proved quantitatively by Montgomery and Vaughan in Theorem 6.9 \[mv2007, pp. 179–181\]. Their Exercise 6.2.5 \[mv2007, p. 183\] then gives the sharper expansion
``` math
p_n=n\left(
 \log n+\log\log n-1+
 \frac{\log\log n-2}{\log n}
 +O\!\left(\frac{(\log\log n)^2}{(\log n)^2}\right)\right).
```
In particular $`p_n\sim n\log n`$, so $`p_n/2^n`$ is summable by comparison with any fixed exponential $`\rho^n`$ with $`1<\rho<2`$. Consequently Theorem <a href="#res:infinite" data-reference-type="ref" data-reference="res:infinite">3</a> and Corollary <a href="#res:irr-equivalence" data-reference-type="ref" data-reference="res:irr-equivalence">4</a> are unconditional paper-level consequences of a classical external theorem. The local Lean development does not formalise the prime number theorem, so its declarations retain summability as an explicit hypothesis. This is a gap in the formalisation, not in the mathematics: the open content is exactly irrationality of the prime-gap series. Concretely, $`\Pi=3.674643966\ldots`$ is irrational if and only if $`\sum_{n\ge0}g_n2^{-(n+1)}=1.674643966\ldots`$ is, and neither is known.

<a id="sec:tail"></a>

# The tail recurrence and integral shifts

The series is not attacked directly. Suppose $`\sum_{i\ge0}a_i2^{-(i+1)}`$ converges, with every $`a_i`$ an integer, and rescale its tails by putting
``` math
T_N=2^{\,N+1}\sum_{i>N}\frac{a_i}{2^{\,i+1}}
    =\sum_{j\ge1}\frac{a_{N+j}}{2^{\,j}} .
```
Two facts follow immediately. First $`T_{N+1}=2T_N-a_{N+1}`$, so moving one level along doubles the rescaled tail and subtracts a single coefficient. Second $`T_0=2\sum_{i\ge0}a_i2^{-(i+1)}-a_0`$, so the sum is rational exactly when $`T_0`$ is. The whole of Section <a href="#sec:tail" data-reference-type="ref" data-reference="sec:tail">3</a> therefore studies that recurrence in isolation, assuming nothing about the coefficients beyond the fact that they are integers; the prime-gap instance is resumed at the end of the section. The following definition is the object so obtained, stripped of its origin.

<div id="def:rec" class="definition">

**Definition 5**. Let $`g:\mathbb{N}\to\mathbb{Z}`$ and $`T:\mathbb{N}\to\mathbb{Q}`$. Say $`T`$ satisfies the *dyadic tail recurrence* with *digits* $`g`$ when
``` math
T_{N+1}=2T_N-g_{N+1}\qquad\text{for every }N .
```
We call the sequence $`(T_N)_{N\ge0}`$ the *orbit* of $`T_0`$ under $`g`$, write $`\sigma_h(N)=T_{N+h}-T_N`$ for the *shift* of length $`h`$ at $`N`$, and call a rational number *integral* when it is the image of an integer.

</div>

These are the [tail recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L278), the [shift](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L282), and [integrality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L298). The digits are arbitrary integers. In the intended instance they are the prime gaps and $`T_N`$ is the scaled tail of $`\Pi`$ after level $`N`$, but that instantiation needs a summability argument and is not made here; every statement below is a theorem about Definition <a href="#def:rec" data-reference-type="ref" data-reference="def:rec">5</a>.

One small orbit, referred to again below, is worth having in view. Take every digit $`g_N=0`$ and $`T_0=1/12`$. Then $`T_{N+1}=2T_N`$, so the orbit is $`\tfrac1{12},\tfrac16,\tfrac13,\tfrac23,\tfrac43,\ldots`$, and $`\sigma_h(N)=(2^{h}-1)2^{\,N}/12`$. The shift of length $`2`$ is not integral at $`N=0`$, where $`\sigma_2(0)=\tfrac13-\tfrac1{12}=\tfrac14`$, and is integral at $`N=2`$, where $`\sigma_2(2)=\tfrac43-\tfrac13=1`$; the shift of length $`1`$ is $`\sigma_1(N)=2^{\,N}/12`$ and is never integral. The change at $`N=2`$ is accounted for by Theorem <a href="#res:collapse" data-reference-type="ref" data-reference="res:collapse">10</a>, and the failure at $`h=1`$ by Theorem <a href="#res:shiftiff" data-reference-type="ref" data-reference="res:shiftiff">7</a>.

Iterating the recurrence $`h`$ times multiplies $`T_N`$ by $`2^{h}`$ and accumulates an explicit integer, which we now name. Define $`B_{0,N}=0`$ and $`B_{h+1,N}=2B_{h,N}+g_{N+h+1}`$, so that $`B_{h,N}=g_{N+1}2^{\,h-1}+\cdots+g_{N+h}`$: the [tail block](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L304). Thus $`B_{1,N}=g_{N+1}`$, $`B_{2,N}=2g_{N+1}+g_{N+2}`$ and $`B_{3,N}=4g_{N+1}+2g_{N+2}+g_{N+3}`$: the block puts the weights $`2^{\,h-1},\ldots,2^{0}`$ on the $`h`$ digits following index $`N`$.

<div id="res:block" class="theorem">

**Theorem 6** (block identity). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer digits $`g`$, and let $`B_{h,N}`$ be as above. For every $`N`$ and $`h`$,
``` math
T_{N+h}=2^{h}T_N-B_{h,N},
 \qquad\text{hence}\qquad
 \sigma_h(N)=(2^{h}-1)\,T_N-B_{h,N} .
```*

</div>

<div class="proof">

*Proof.* A routine induction on $`h`$; the step is one application of the recurrence together with $`2\cdot2^{h}=2^{h+1}`$ and the recursion defining $`B`$. The second identity is the first minus $`T_N`$. ◻

</div>

Formalised as the [iterated block identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L310) and the [scaled shift identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L324). The shift also obeys the recurrence in its own right, $`\sigma_h(N+1)=2\sigma_h(N)-(g_{N+h+1}-g_{N+1})`$, the [shift step identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L286).

Since $`B_{h,N}`$ is an integer, Theorem <a href="#res:block" data-reference-type="ref" data-reference="res:block">6</a> converts a question about the shift into a question about the single scaled term $`(2^{h}-1)T_N`$.

<div id="res:shiftiff" class="theorem">

**Theorem 7** (integral-shift criterion). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer digits $`g`$. For every $`N`$ and $`h`$, the shift $`\sigma_h(N)`$ is integral if and only if $`(2^{h}-1)T_N`$ is integral.*

</div>

<div class="proof">

*Proof.* By Theorem <a href="#res:block" data-reference-type="ref" data-reference="res:block">6</a> the two differ by the integer $`B_{h,N}`$, and subtracting an integer does not change integrality. ◻

</div>

Formalised as the [integral-shift criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L380), on the [integer-shift invariance](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L334). This is an equivalence, not a one-way reduction: the block carries no information about integrality, so the two conditions are the same condition. Informally, once $`T_N`$ is fixed no choice of the digits after index $`N`$ can change whether the shift $`\sigma_h(N)`$ is an integer; that is decided by the denominator of $`T_N`$ alone.

<div id="res:totient" class="theorem">

**Theorem 8** (a shift of totient length). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer digits $`g`$, and let $`\varphi`$ be Euler’s totient function. If the reduced denominator $`d`$ of $`T_N`$ is odd, then $`\sigma_{\varphi(d)}(N)`$ is integral.*

</div>

<div class="proof">

*Proof.* Since $`d`$ is odd, $`2`$ and $`d`$ are coprime, so Euler’s congruence gives $`2^{\varphi(d)}\equiv1\pmod d`$, that is $`d\mid 2^{\varphi(d)}-1`$. Writing $`2^{\varphi(d)}-1=dk`$ and $`T_N=u/d`$ in lowest terms, $`(2^{\varphi(d)}-1)T_N=ku`$ is an integer, and Theorem <a href="#res:shiftiff" data-reference-type="ref" data-reference="res:shiftiff">7</a> transfers this to the shift. ◻

</div>

Formalised as the [totient shift](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L391) and the [Euler multiplier](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L352). For example, if $`\operatorname{den}T_N=3`$ then $`\varphi(3)=2`$ and $`(2^{2}-1)T_N=3T_N`$ is an integer, so $`\sigma_2(N)`$ is integral, while $`(2^{1}-1)T_N=T_N`$ is not; if $`\operatorname{den}T_N=5`$ then $`\varphi(5)=4`$ and $`\sigma_4(N)`$ is integral.

The hypothesis is a genuine restriction: the argument uses coprimality of $`2`$ with the denominator, and the even part of a denominator is exactly what the doubling in the recurrence acts on. It cannot be dropped. If $`T_N=1/2`$ then $`2^{h}-1`$ is odd for every $`h\ge1`$, so $`(2^{h}-1)T_N`$ is never an integer and, by Theorem <a href="#res:shiftiff" data-reference-type="ref" data-reference="res:shiftiff">7</a>, no shift at $`N`$ is integral.

<div id="res:propagate" class="theorem">

**Theorem 9** (propagation). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer digits $`g`$, and fix $`h`$ and $`N`$. If $`\sigma_h(N)`$ is integral, then $`\sigma_h(N+k)`$ is integral for every $`k\ge0`$.*

</div>

<div class="proof">

*Proof.* By the shift step identity, $`\sigma_h(N+1)=2\sigma_h(N)-(g_{N+h+1}-g_{N+1})`$ is an integer combination of an integer and two digits; induct on $`k`$. ◻

</div>

Formalised as the [one-step propagation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L402) and the [propagation to every later index](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L414).

The three preceding theorems combine as follows, and this is the statement the rest of the note rests on. The special case is immediate: if $`\operatorname{den}T_0`$ is already odd, then Theorem <a href="#res:totient" data-reference-type="ref" data-reference="res:totient">8</a> at $`N=0`$ makes the shift of length $`\varphi(\operatorname{den}T_0)`$ integral and Theorem <a href="#res:propagate" data-reference-type="ref" data-reference="res:propagate">9</a> keeps it integral at every later index, so one may take $`N_0=0`$. In general a denominator carries a power of two as well, and the key point is that the doubling in the recurrence annihilates exactly the $`2`$-adic part of a denominator, and nothing else: after finitely many steps the orbit therefore reaches a term with odd reduced denominator, which is precisely the situation Theorem <a href="#res:totient" data-reference-type="ref" data-reference="res:totient">8</a> handles. No control of the digits is needed anywhere.

<div id="res:collapse" class="theorem">

**Theorem 10** (denominator collapse). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer digits $`g`$ (Definition <a href="#def:rec" data-reference-type="ref" data-reference="def:rec">5</a>). Then some fixed positive shift is integral from some point onwards:
``` math
\exists h\ge1\ \exists N_0\ \forall N\ge N_0,\qquad
 \sigma_h(N)\in\mathbb{Z}.
```*

</div>

<div class="proof">

*Proof.* Write the reduced denominator of $`T_0`$ as $`2^s m`$ with $`m`$ odd. The block identity gives $`T_s=2^sT_0-B_{s,0}`$. Multiplying by $`2^s`$ clears the entire power of two from the denominator, and subtracting the integer $`B_{s,0}`$ cannot reintroduce one, so the reduced denominator of $`T_s`$ divides $`m`$ and is in particular odd. Theorem <a href="#res:totient" data-reference-type="ref" data-reference="res:totient">8</a>, applied at index $`s`$, supplies the positive shift $`h=\varphi(\operatorname{den}T_s)`$, and Theorem <a href="#res:propagate" data-reference-type="ref" data-reference="res:propagate">9</a> keeps that shift integral at every later index. ◻

</div>

In the orbit displayed after Definition <a href="#def:rec" data-reference-type="ref" data-reference="def:rec">5</a> the proof runs as follows: $`\operatorname{den}T_0=12=2^{2}\cdot3`$, so $`s=2`$, the orbit reaches $`T_2=1/3`$ with odd denominator, and $`h=\varphi(3)=2`$. That is exactly the shift length seen to be integral there from index $`2`$ onwards, and no shorter one works.

Three features of the argument are used later. The proof may take as its number of preparatory steps the $`2`$-adic valuation of $`\operatorname{den}T_0`$. The resulting shift length $`h`$ is the totient of the odd denominator reached from a hypothetical rational initial value, and is not known in advance for the prime-gap orbit. This is why this argument requires Problem <a href="#prob:escape" data-reference-type="ref" data-reference="prob:escape">16</a> for every $`h`$, rather than for one preassigned shift length. Finally, the digits enter only through the integer $`B_{s,0}`$, so the conclusion holds for an arbitrary integer digit sequence.

The factorisation and cancellation are the [odd-denominator doubling lemma](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L426); the orbit form is the [odd-denominator state theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L461); and the quantified conclusion is the [eventual integral-shift theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L477).

The useful contrapositive is stated for a real recurrence. Call its shifts *cofinally non-integral* when, for every fixed $`h\ge1`$ and every threshold $`N_0`$, some $`N\ge N_0`$ has $`\sigma_h(N)\notin\mathbb{Z}`$. This is precisely the negation of the conclusion of Theorem <a href="#res:collapse" data-reference-type="ref" data-reference="res:collapse">10</a>: no shift length whatever becomes integral and stays integral.

<div id="res:escape-irrational" class="theorem">

**Theorem 11** (cofinal shift escape implies irrationality). *Let $`T:\mathbb{N}\to\mathbb{R}`$ satisfy $`T_{N+1}=2T_N-g_{N+1}`$ with integer $`g`$. If its shifts are cofinally non-integral, then $`T_0`$ is irrational.*

</div>

<div class="proof">

*Proof.* If $`T_0`$ were rational, the whole real orbit would be the image in $`\mathbb{R}`$ of the rational orbit with that initial value. Theorem <a href="#res:collapse" data-reference-type="ref" data-reference="res:collapse">10</a> would then produce one $`h\ge1`$ whose shifts are integral at every sufficiently large index, contradicting cofinal non-integrality. ◻

</div>

Lean checks the real recurrence and shift definitions as [real dyadic recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L492) and [real shift](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L496), the rational-orbit transport as the [rational-orbit cast theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L515), cofinal non-integrality as the [cofinal shift-escape predicate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L528), and Theorem <a href="#res:escape-irrational" data-reference-type="ref" data-reference="res:escape-irrational">11</a> as the [cofinal-escape irrationality theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L537).

<a id="the-actual-prime-gap-orbit."></a>

#### The actual prime-gap orbit.

Define, at paper level,
``` math
\mathcal T_N=\sum_{j\ge1}\frac{g_{N+j}}{2^j}.
```
The prime number theorem gives convergence, and an index shift gives
``` math
\mathcal T_{N+1}=2\mathcal T_N-g_{N+1}.
```
If $`G=\sum_{n\ge0}g_n/2^{n+1}`$, then $`\mathcal T_0=2G-g_0=2G-1=2.349287932\ldots`$. Together with Theorem <a href="#res:infinite" data-reference-type="ref" data-reference="res:infinite">3</a>, this shows that $`\Pi`$, $`G`$, and $`\mathcal T_0`$ have the same rationality status. Thus Theorem <a href="#res:escape-irrational" data-reference-type="ref" data-reference="res:escape-irrational">11</a> applies directly to Problem #251 once cofinal shift escape is proved for $`\mathcal T`$. This last analytic instantiation is proved here from the classical prime number theorem; it is not yet a Lean declaration. The abstract theorem, including its real/rational transport, is kernel-checked.

<a id="sec:local-certificate"></a>

## Two adjacent small shifts cannot both be integral

Applying Theorem <a href="#res:escape-irrational" data-reference-type="ref" data-reference="res:escape-irrational">11</a> requires cofinal non-integrality, which is a condition of infinite precision imposed on a complete tail. The key point is that inside the open interval $`(-1,1)`$ integrality is equality with zero, so on that range the one-step shift recurrence
``` math
\sigma_h(N+1)=2\sigma_h(N)-\bigl(g_{N+h+1}-g_{N+1}\bigr)
```
turns simultaneous integrality of two adjacent shifts into a single comparison of digits. What this buys is a *certificate*: a condition attached to a single pair of adjacent indices, whose verification already contradicts integrality at that pair. The point of arranging the argument this way is that the distance of a shift from the integers never has to be estimated; it suffices to know that both shifts lie in $`(-1,1)`$ and that two digits differ.

<div id="res:smallpair" class="theorem">

**Theorem 12** (adjacent small-shift obstruction). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer digits $`g`$. Fix $`h`$ and $`N`$. If
``` math
-1<\sigma_h(N)<1,\qquad -1<\sigma_h(N+1)<1,
 \qquad g_{N+h+1}\ne g_{N+1},
```
then $`\sigma_h(N)`$ and $`\sigma_h(N+1)`$ cannot both be integral. Consequently, if such a pair occurs beyond every threshold, the $`h`$-shift is not eventually integral.*

</div>

<div class="proof">

*Proof.* An integral rational strictly between $`-1`$ and $`1`$ is zero. If both shifts were integral, both would therefore vanish, and substitution in the displayed shift step identity would give $`g_{N+h+1}=g_{N+1}`$, a contradiction. The cofinal statement chooses one such adjacent pair after the alleged onset of integrality. ◻

</div>

The finite contradiction is the [adjacent small-shift obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L626); its quantified form is the [cofinal small-mismatch theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L653); and the actual-prime-gap specialisation is the [prime-gap specialisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L723). Theorem <a href="#res:smallpair" data-reference-type="ref" data-reference="res:smallpair">12</a> is conditional on its two tail inequalities; no theorem asserting that such pairs occur is claimed here.

All three are stated for a rational orbit, while the prime-gap tail $`\mathcal T`$ of Section <a href="#sec:tail" data-reference-type="ref" data-reference="sec:tail">3</a> is real, so the rational statement does not on its own discharge the instances that arise downstream. The same argument gives the real form directly.

<div id="res:smallpair-real" class="corollary">

**Corollary 13** (adjacent small-shift obstruction, real form). *Let $`T:\mathbb{N}\to\mathbb{R}`$ satisfy $`T_{N+1}=2T_N-g_{N+1}`$ with integer digits $`g`$, and write $`\sigma_h(N)=T_{N+h}-T_N`$. Fix $`h`$ and $`N`$. If
``` math
-1<\sigma_h(N)<1,\qquad -1<\sigma_h(N+1)<1,
 \qquad g_{N+h+1}\ne g_{N+1},
```
then $`\sigma_h(N)`$ and $`\sigma_h(N+1)`$ do not both lie in $`\mathbb{Z}`$. Consequently, if such a pair occurs beyond every threshold, the $`h`$-shift is not eventually integral.*

</div>

<div class="proof">

*Proof.* The real recurrence gives the same shift step identity $`\sigma_h(N+1)=2\sigma_h(N)-\bigl(g_{N+h+1}-g_{N+1}\bigr)`$, and an integer strictly between $`-1`$ and $`1`$ is zero. If both shifts lay in $`\mathbb{Z}`$, both would therefore vanish, and substitution in that identity would give $`g_{N+h+1}=g_{N+1}`$, a contradiction. The cofinal statement chooses one such adjacent pair after the alleged onset of integrality. ◻

</div>

Corollary <a href="#res:smallpair-real" data-reference-type="ref" data-reference="res:smallpair-real">13</a> is proved here and is not a declaration in the pinned Lean module, whose small-shift theorems are stated for the rational orbit. It is the form that applies to the real tail, and it carries the same two unproved inequalities as its rational counterpart.

The third hypothesis, on its own, is available. For the actual gaps tabulated in Section <a href="#sec:problem" data-reference-type="ref" data-reference="sec:problem">1</a> it reads $`g_4=2\ne4=g_3`$ at $`h=1`$, $`N=2`$; and Proposition <a href="#res:gap-nonperiodic" data-reference-type="ref" data-reference="res:gap-nonperiodic">14</a> below says precisely that for each fixed $`h\ge1`$ the inequality $`g_{N+h+1}\ne g_{N+1}`$ holds for arbitrarily large $`N`$, since its failure from some index onwards is eventual periodicity with period $`h`$. What is missing is the pair of inequalities, each of which constrains a complete infinite tail.

<div id="res:gap-nonperiodic" class="proposition">

**Proposition 14** (prime gaps do not become periodic). *For every positive $`h`$, the actual consecutive-prime-gap sequence is not eventually periodic with period $`h`$.*

</div>

<div class="proof">

*Proof.* The gaps are unbounded, by the standard construction: the interval from $`n!+2`$ to $`n!+n`$ contains no prime. Far stronger lower bounds for large gaps are known \[fgkmt2018, Theorem 1, p. 66\], but unboundedness is all that is needed. An eventually periodic natural-valued sequence has finite range after its preperiod, while its finite initial segment is bounded as well; hence it is bounded, a contradiction. ◻

</div>

Lean checks the factorial argument as [unboundedness of the actual gaps](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L51) and the conclusion as [non-eventual periodicity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L670). Combining nonperiodicity with eventual strict smallness of one positive shift would also exclude eventual integrality, but eventual smallness at every sufficiently large index is stronger than the cofinal adjacent-pair hypothesis in Theorem <a href="#res:smallpair" data-reference-type="ref" data-reference="res:smallpair">12</a> and is not asserted here.

<a id="sec:carry"></a>

# Nonperiodic coefficients with a rational sum

Proposition <a href="#res:gap-nonperiodic" data-reference-type="ref" data-reference="res:gap-nonperiodic">14</a> shows that the prime gaps are not eventually periodic. One might therefore hope that rationality of a dyadic series forces its integer coefficients to be eventually periodic, and play the two against each other. The hoped-for implication is false, and a single explicit sequence refutes it.

The construction runs the emission of coefficients backwards. Let $`K:\mathbb{N}\to\mathbb{Q}`$ be arbitrary, read $`K_n`$ as the value carried into level $`n`$, and put $`\kappa_n=2K_n-K_{n+1}`$: the [carry coefficient](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L738). That definition is exactly the statement that
``` math
\frac{K_n}{2^{\,n}}
 =\frac{\kappa_n}{2^{\,n+1}}+\frac{K_{n+1}}{2^{\,n+1}} ,
```
so at each level the carried value splits into one emitted coefficient and a new carry. Nothing at all is assumed about $`K`$: not integrality, not positivity, not any bound. That is the sense in which the carry is free, and it is what the counterexample below exploits.

<div id="res:telescope" class="proposition">

**Proposition 15** (exact telescoping). *Let $`K:\mathbb{N}\to\mathbb{Q}`$ be arbitrary and $`\kappa_n=2K_n-K_{n+1}`$. For every $`n\ge0`$,
``` math
\sum_{i=0}^{n-1}\frac{\kappa_i}{2^{\,i+1}}=K_0-\frac{K_n}{2^{\,n}} .
```*

</div>

<div class="proof">

*Proof.* A routine induction on $`n`$; the added term is $`(2K_n-K_{n+1})/2^{\,n+1}=K_n/2^{\,n}-K_{n+1}/2^{\,n+1}`$. ◻

</div>

Formalised as the [carry telescoping identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L747), on the [carry partial sum](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L742). When $`K`$ takes natural-number values and $`K_{n+1}\le2K_n`$ for every $`n`$, the coefficients $`\kappa_n`$ are natural numbers as well, and the natural-number and rational readings of the definition agree under the cast, the [natural-carry cast](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L763).

<a id="consequence-for-the-coefficients."></a>

#### Consequence for the coefficients.

If $`K_n2^{-n}\to0`$, the emitted partial sums converge to $`K_0`$. For the explicit choice $`K_n=n`$ one has
``` math
\kappa_n=n-1,\qquad
 \sum_{i=0}^{n-1}\frac{\kappa_i}{2^{\,i+1}}
   =-\frac{n}{2^n}\longrightarrow0,
```
that is, the first values are
``` math
\begin{array}{c|ccccccc}
  n & 0&1&2&3&4&5&6\\\hline
  \kappa_n & -1&0&1&2&3&4&5\\[2pt]
  \displaystyle\sum_{i<n}\frac{\kappa_i}{2^{\,i+1}}
    & 0&-\tfrac12&-\tfrac12&-\tfrac38&-\tfrac14&-\tfrac5{32}&-\tfrac3{32}
 \end{array}
```
converging to $`0`$. The sequence $`(\kappa_n)`$ is unbounded and therefore not eventually periodic, although its dyadic sum is rational. Thus rationality alone cannot imply eventual periodicity of an unrestricted integer coefficient sequence. Informally, an arbitrarily large value may be carried forward from level to level and still disappear in the limit, so rationality of a dyadic sum is compatible with arbitrarily large integer coefficients. This does not classify which sequences occur, and it does not show that a prescribed prime-gap pattern is emitted by a bounded or nonnegative carry; here $`K_1=1>0=2K_0`$, so this example is not of the natural-number kind above, and indeed $`\kappa_0=-1`$.

<a id="sec:open"></a>

# Complements and further questions

Problem #251 is open. Two statements would close it, and neither is proved here. Both ask for indices beyond every threshold rather than for one index, because Theorem <a href="#res:collapse" data-reference-type="ref" data-reference="res:collapse">10</a> produces integrality only from some unspecified point onwards; a single non-integral shift, however far out, is consistent with that conclusion. Throughout, $`g_i=p_{i+1}-p_i`$ are the zero-based prime gaps of Section <a href="#sec:problem" data-reference-type="ref" data-reference="sec:problem">1</a>.

<div id="prob:escape" class="problem">

**Problem 16** (minimal prime-gap shift escape). For every $`h\ge1`$ and every $`N_0`$, prove that some $`N\ge N_0`$ satisfies
``` math
\sum_{j\ge1}
 \frac{g_{N+h+j}-g_{N+j}}{2^j}\notin\mathbb{Z}.
\tag{5.1}\label{eq:shift-escape}
```

</div>

The series in <a href="#eq:shift-escape" data-reference-type="eqref" data-reference="eq:shift-escape">[eq:shift-escape]</a> is exactly $`\mathcal T_{N+h}-\mathcal T_N`$. Theorem <a href="#res:escape-irrational" data-reference-type="ref" data-reference="res:escape-irrational">11</a> therefore turns any solution of Problem <a href="#prob:escape" data-reference-type="ref" data-reference="prob:escape">16</a> directly into irrationality of $`\Pi`$. The quantifier over $`h`$ is essential: a hypothetical rational value chooses a shift length from the odd part of its reduced denominator, and that length is not known in advance.

<div id="prob:smallpair" class="problem">

**Problem 17** (cofinal adjacent small mismatch). For every fixed $`h\ge1`$ and every $`N_0`$, prove that some $`N\ge N_0`$ satisfies
``` math
\begin{split}
\left|\sum_{j\ge1}
 \frac{g_{N+h+j}-g_{N+j}}{2^j}\right|&<1,\\
\left|\sum_{j\ge1}
 \frac{g_{N+h+1+j}-g_{N+1+j}}{2^j}\right|&<1,\\
g_{N+h+1}&\ne g_{N+1}.
\end{split}
\tag{5.2}\label{eq:smallpair}
```

</div>

The two sums are adjacent $`h`$-shifts. Corollary <a href="#res:smallpair-real" data-reference-type="ref" data-reference="res:smallpair-real">13</a> turns each instance of <a href="#eq:smallpair" data-reference-type="eqref" data-reference="eq:smallpair">[eq:smallpair]</a> into a finite contradiction to simultaneous integrality; Theorem <a href="#res:smallpair" data-reference-type="ref" data-reference="res:smallpair">12</a> is the Lean-checked rational case. A cofinal family of such pairs therefore proves Problem <a href="#prob:escape" data-reference-type="ref" data-reference="prob:escape">16</a>; Theorem <a href="#res:escape-irrational" data-reference-type="ref" data-reference="res:escape-irrational">11</a> then gives irrationality of the gap series, and Corollary <a href="#res:irr-equivalence" data-reference-type="ref" data-reference="res:irr-equivalence">4</a> transfers it to $`\Pi`$. This formulation deliberately asks only for sporadic adjacent pairs; the stronger assertion that a fixed shift is eventually always smaller than one is unnecessary.

Several natural prime-distribution inputs are insufficient. Isolated small gaps, isolated large gaps, average gap estimates, and the occurrence of any one fixed finite pattern do not suffice: both inequalities in <a href="#eq:smallpair" data-reference-type="eqref" data-reference="eq:smallpair">[eq:smallpair]</a> contain the complete infinite continuation. Nor does parity: after the first gap all $`g_n`$ are even. Unboundedness and non-eventual-periodicity of the actual gaps, though now checked, do not imply the required small-tail recurrence. In particular, Section <a href="#sec:carry" data-reference-type="ref" data-reference="sec:carry">4</a> shows that no argument can deduce eventual periodicity from rationality alone.

<a id="a-finite-truncation-criterion."></a>

#### A finite truncation criterion.

Both problems above are stated in terms of infinite tails, but a dominated truncation reduces the first of them to a finite quantity. For $`L\ge1`$ put
``` math
S_{h,N,L}=\sum_{j=1}^{L}
 \frac{g_{N+h+j}-g_{N+j}}{2^j},
```
the truncation of the series in <a href="#eq:shift-escape" data-reference-type="eqref" data-reference="eq:shift-escape">[eq:shift-escape]</a> after $`L`$ terms. This is a finite sum of gap differences and can be computed; the point of the following proposition is to say how far from an integer it must be before the discarded tail is irrelevant.

<div id="res:truncation" class="proposition">

**Proposition 18** (finite truncation). *Let $`M(n)\ge g_n`$ for every $`n`$, assume that the series below converges, and put
``` math
R_{h,N,L}(M)=
 \sum_{j>L}\frac{M(N+h+j)+M(N+j)}{2^j}.
```
Suppose that for every fixed $`h\ge1`$ and every $`N_0`$ there exist $`N\ge N_0`$ and $`L\ge1`$ with
``` math
\operatorname{dist}(S_{h,N,L},\mathbb{Z})>R_{h,N,L}(M).
\tag{5.3}\label{eq:truncation}
```
Then Problem <a href="#prob:escape" data-reference-type="ref" data-reference="prob:escape">16</a> holds.*

</div>

<div class="proof">

*Proof.* The part of $`\sum_{j\ge1}(g_{N+h+j}-g_{N+j})2^{-j}`$ omitted from $`S_{h,N,L}`$ has absolute value at most $`R_{h,N,L}(M)`$, so under <a href="#eq:truncation" data-reference-type="eqref" data-reference="eq:truncation">[eq:truncation]</a> the full sum lies at positive distance from every integer. ◻

</div>

The rational analogue of the last distance-to-integers inference is Lean-checked as the generic [finite-approximation certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/7558c58afb7cb0046dbd3101c1b3187ccdac5909/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L772): an error at most $`R`$ cannot reach an integer when the approximation is farther than $`R`$ from every integer. For instance, if $`S_{h,N,L}=2/5`$ and $`R_{h,N,L}(M)=1/20`$, the full sum lies within $`1/20`$ of $`2/5`$ and so at distance at least $`7/20`$ from every integer, which settles <a href="#eq:shift-escape" data-reference-type="eqref" data-reference="eq:shift-escape">[eq:shift-escape]</a> at that $`N`$. The prime-gap tail bound, the convergence used above, and the existence of blocks satisfying <a href="#eq:truncation" data-reference-type="eqref" data-reference="eq:truncation">[eq:truncation]</a> are not consequences of that formal theorem. Moreover, the proposition’s full sum is real-valued, so the reverse-triangle inference used here is a paper proof rather than an instance of the linked rational-valued Lean declaration.

Taking the classical bound $`M(n)\ll n\log n`$, a choice $`L=\lceil A\log_2(N+h+2)\rceil`$ with any fixed $`A>1`$ makes the right side a negative power of $`N`$ up to logarithms. Thus <a href="#eq:truncation" data-reference-type="eqref" data-reference="eq:truncation">[eq:truncation]</a> asks for a finite dyadic anti-concentration estimate on a logarithmic-length block, not control of an infinite tail and not eventual periodicity of the full gap sequence. For Problem <a href="#prob:smallpair" data-reference-type="ref" data-reference="prob:smallpair">17</a>, the same truncation must certify two adjacent full-tail values inside the open unit interval, together with the displayed gap mismatch. A finite prefix is useful only when its omitted tail is rigorously dominated.

What <a href="#eq:truncation" data-reference-type="eqref" data-reference="eq:truncation">[eq:truncation]</a> requires is joint control of the finite block of weighted differences $`(g_{N+h+1}-g_{N+1},\ldots,g_{N+h+L}-g_{N+L})`$ modulo powers of two, along a block of logarithmic length. We do not know how to obtain such control and we make no progress on it here. The strongest results on prime gaps address a different shape of question. Zhang’s bounded-gap theorem \[zhang2014, Theorem 1, p. 1122\] produces infinitely many bounded consecutive-prime gaps. Maynard proves substantially more than an individual-gap statement: \[maynard2015, Theorem 1.1, p. 384\] bounds $`\liminf_n(p_{n+m}-p_n)`$ for every fixed $`m`$, and hence gives bounded clusters of every fixed size; \[maynard2015, Theorem 1.3, p. 385\] gives the explicit unconditional bound $`\liminf_n(p_{n+1}-p_n)\le 600`$. The large-gap theorem of Ford, Green, Konyagin, Maynard and Tao \[fgkmt2018, Theorem 1, p. 66\] bounds the largest single consecutive-prime gap below $`X`$. None of these results supplies the joint dyadic distribution of a logarithmic block of consecutive gap differences required by <a href="#eq:truncation" data-reference-type="eqref" data-reference="eq:truncation">[eq:truncation]</a>. The same introduction notes a separate sequel on chains of large gaps; the cited theorem itself supplies no residue-sensitive block estimate of the kind needed here.

<a id="what-remains-to-be-formalised."></a>

#### What remains to be formalised.

The abstract irrationality theorem and the prime-specific local small-mismatch theorem are Lean-checked, as is the rational analogue of the finite-approximation certificate used in Proposition <a href="#res:truncation" data-reference-type="ref" data-reference="res:truncation">18</a>; the proposition’s real-valued inference remains paper-level. The local source still takes summability of the prime series as a hypothesis and does not define $`\mathcal T_N`$ by an infinite sum; the prime-number-theorem comparison and the identification of that concrete tail with the checked real recurrence are paper proofs, as is the real form of the small-shift obstruction in Corollary <a href="#res:smallpair-real" data-reference-type="ref" data-reference="res:smallpair-real">13</a>. The local source’s prime-gap tail domination and anti-concentration hypotheses also remain paper-level obligations. No theorem supplies the cofinal pairs in <a href="#eq:smallpair" data-reference-type="eqref" data-reference="eq:smallpair">[eq:smallpair]</a>, and none of the prime-distribution estimates described above is claimed or formalised.

<a id="statements-and-declarations"></a>

## Statements and declarations

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

The [pinned formal-source revision](https://github.com/wcook04/plectis-lean-erdos249-257/tree/7558c58afb7cb0046dbd3101c1b3187ccdac5909) contains the Lean sources, the fixed toolchain, and the library manifest used in the verification. This manuscript provides navigation rather than proof authority.

<a id="declaration-of-generative-ai-use."></a>

#### Declaration of generative AI use.

Large-language-model agents were used throughout development to draft and revise prose, formal proofs, and software. The author set the objectives and acceptance criteria, selected and reviewed the claims, and approved the published version. The author assumes responsibility for the accuracy, interpretation, and presentation of the work. Generative systems are production tools; they are not authors and supply no independent authority. Lean checks each proof term against the fixed library version, and the sources linked here contain no proof placeholders and no project-defined axioms; Lean does not authorise the exposition, the citation choices, or the interpretation, for which the author remains responsible.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.

<a id="acknowledgements."></a>

#### Acknowledgements.

The problem numbering and status follow the Erdős Problems catalogue maintained by Thomas Bloom \[erdosproblems\].

<a id="app:index"></a>

# Guide to the formal sources

Each linked phrase opens its Lean declaration at the pinned source revision 7558c58afb7c. All declarations of this note live in one module. The summation-by-parts declarations are prime-specific; most of Section <a href="#sec:tail" data-reference-type="ref" data-reference="sec:tail">3</a> is stated for arbitrary integer digits and arbitrary rational or real orbits, while Section <a href="#sec:local-certificate" data-reference-type="ref" data-reference="sec:local-certificate">3.1</a> records the actual-gap specialisation. The concrete prime-gap tail and its convergence are paper-level consequences of the prime number theorem; they are not definitions in the pinned Lean module.

<div class="thebibliography">

99

P. Erdős, [*Sur certaines séries à valeur irrationnelle*](https://combinatorica.hu/~p_erdos/1958-19.pdf), Enseign. Math. (2) **4** (1958), 93–100, doi:[10.5169/seals-34629](https://doi.org/10.5169/seals-34629). The dyadic prime series is stated as unproved on p. 94; the factorial-prime family is stated on p. 93, with only the $`k=1`$ proof printed on pp. 94–95. P. Erdős and R. L. Graham, [*Old and New Problems and Results in Combinatorial Number Theory*](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf), Monogr. Enseign. Math. 28, Geneva, 1980, p. 62. P. Erdős and C. Pomerance, [*On the largest prime factors of $`n`$ and $`n+1`$*](https://doi.org/10.1007/BF01818569), Aequationes Math. **17** (1978), 311–321, doi:[10.1007/BF01818569](https://doi.org/10.1007/BF01818569). The unnumbered dyadic irrationality theorem and its complete proof are in §7 on p. 320. P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). P. Erdős and E. G. Straus, *On the irrationality of certain Ahmes series*, J. Indian Math. Soc. (N.S.) **27** (1964), 129–133. MR 175848. K. Ford, B. Green, S. Konyagin, J. Maynard and T. Tao, *Long gaps between primes*, J. Amer. Math. Soc. **31** (2018), 65–105, doi:[10.1090/jams/876](https://doi.org/10.1090/jams/876). Theorem 1 on p. 66 gives the effective lower bound for the largest single consecutive-prime gap below $`X`$. V. Kovač and T. Tao, [*On several irrationality problems for Ahmes series*](https://doi.org/10.1007/s10474-025-01528-0), Acta Math. Hungar. **175** (2025), 572–608. L. de Moura and S. Ullrich, [*The Lean 4 theorem prover and programming language*](https://doi.org/10.1007/978-3-030-79876-5_37), in A. Platzer and G. Sutcliffe (eds.), CADE 28, Lecture Notes in Comput. Sci. 12699, Springer, 2021, pp. 625–635, doi:[10.1007/978-3-030-79876-5_37](https://doi.org/10.1007/978-3-030-79876-5_37). The mathlib Community, [*The Lean mathematical library*](https://doi.org/10.1145/3372885.3373824), in CPP 2020, ACM, 2020, pp. 367–381, doi:[10.1145/3372885.3373824](https://doi.org/10.1145/3372885.3373824). The article describes a December 2019 Lean 3-era snapshot; the repository lock owns the current revision. J. Maynard, [*Small gaps between primes*](https://doi.org/10.4007/annals.2015.181.1.7), Ann. of Math. (2) **181** (2015), 383–413. H. L. Montgomery and R. C. Vaughan, [*Multiplicative Number Theory I: Classical Theory*](https://doi.org/10.1017/CBO9780511618314.008), Cambridge Stud. Adv. Math. 97, Cambridge UP, 2007, Chapter 6, pp. 168–198; Theorem 6.9, pp. 179–181, and Exercise 6.2.5, p. 183, doi:[10.1017/CBO9780511618314.008](https://doi.org/10.1017/CBO9780511618314.008). Y. Zhang, [*Bounded gaps between primes*](https://doi.org/10.4007/annals.2014.179.3.7), Ann. of Math. (2) **179** (2014), 1121–1174. T. F. Bloom, [*Erdős Problem \#251*](https://www.erdosproblems.com/251), `erdosproblems.com/251`, accessed 28 July 2026 (page displays “last edited 28 September 2025”). The current record labels the main dyadic problem open, cites `[Er58b]`, `[ErGr80, p. 62]` and `[Er88c, p. 103]`, and explicitly describes its status as the website owner’s present assessment rather than a literature-completeness guarantee; it does not mention the 2026 counterexample in \[kovac2026\] to the adjacent variable-denominator conjecture. ChatGPT 5.4 Pro (orchestrated by V. Kovač), [*On the Erdős problem \#251*](https://web.math.pmf.unizg.hr/~vjekovac/files/Erdos_problem_251.pdf), unpublished note, 2026, hosted by the Department of Mathematics, University of Zagreb, `web.math.pmf.unizg.hr`, accessed 28 July 2026. The Formal Conjectures Authors, [*FormalConjectures.ErdosProblems.`251`*](https://github.com/google-deepmind/formal-conjectures/blob/f776d2f2039351b00737ffcafb9d7d7666e1d9af/FormalConjectures/ErdosProblems/251.lean), Lean source at commit `f776d2f`, 2025, accessed 28 July 2026.

</div>
