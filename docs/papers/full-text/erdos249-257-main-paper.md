<a id="erdos249-257-main-paper"></a>

# Exact Reductions for Two Open Irrationality Problems of Erdős

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

Let $`S=\sum_{n\geq1}\varphi(n)/2^n`$, and for $`A\subseteq\mathbb{N}_{>0}`$ let $`X_A=\sum_{n\in A}(2^n-1)^{-1}`$. Erdős asked whether $`S`$ is irrational (Problem #249) and whether $`X_A`$ is irrational for every infinite $`A`$ (Problem #257). Both problems remain open. We formalise in Lean two exact reductions that identify an equivalent unbounded condition in each question.

For \#249, irrationality of $`S`$ is equivalent to the existence, beyond every bound, of a finite integer calculation plus a rigorous tail estimate showing that two shifted binary tails differ by a non-integer. We also prove unconditionally that any rational representation $`S=p/q`$ has $`q>Q_0\approx7.96\times10^{34}`$. At the lcm scales $`M_t=\operatorname{lcm}(1,\ldots,t)`$, Lean checks 28 such calculations through $`t=64`$. These checks remain finite; they do not prove the required unbounded supply.

For \#257, we formalise the classical irrationality theorem for the sum over all positive exponents in every integer base $`b\geq2`$, together with several previously known structured choices of infinite $`A`$. At base $`2`$, each weight exceeds the sum of all later weights, so every attainable value has a unique choice of exponents. The value $`1/2`$ is attainable exactly when its greedy expansion omits weights at arbitrarily large ranks; this would refute the universal assertion in \#257. Nonattainment is equivalent to a final omission. After a putative final omission, the next-step recurrence has two branches. We exclude one branch and the integer remainder $`-3`$ in the other; the values $`-2,-1`$ and a comparison with the unused tail remain unresolved.

An exact change of variables places both series in one common formula, but transfers no irrationality theorem between them. The contribution is a Lean-checked obstruction atlas: finite objects and an exact beyond-every-cutoff statement for each question, without a proof of the missing unbounded mechanism. We prove neither the irrationality of $`S`$ nor the universal assertion in \#257, and we do not decide whether $`1/2`$ is attainable.

<a id="sec:intro"></a>

# Introduction

We study two questions. The first asks whether $`S=\sum_{n\ge1}\varphi(n)/2^n`$ is irrational (#249). The second asks whether $`\sum_{n\in A}(2^n-1)^{-1}`$ is irrational for every infinite $`A\subseteq\mathbb{N}_{>0}`$ (#257). Here $`\varphi(n)`$ is Euler’s totient, the number of integers from $`1`$ to $`n`$ that are coprime to $`n`$. Problem \#249 appears on p. 61 of Erdős–Graham and p. 102 of Erdős’s survey \[erdosgraham1980, p. 61\]\[erdos1988, p. 102\]; problem \#257 appears on pp. 62 and 105, respectively \[erdosgraham1980, p. 62\] \[erdos1988, p. 105\]. Numbering follows Bloom’s catalogue \[erdosproblems\]. Neither problem is settled.

Throughout, $`\mathbb{N}=\{0,1,2,\ldots\}`$ and $`\mathbb{N}_{>0}=\{1,2,3,\ldots\}`$. A *support* $`A\subseteq\mathbb{N}_{>0}`$ is the set of selected exponents; the set of all resulting sums is the *achievement set* $`\mathcal A`$. Exponent $`0`$ is excluded because $`2^0-1=0`$. An infinite support with sum $`1/2`$ would therefore refute the universal assertion in \#257.

<a id="what-is-proved"></a>

## What is proved

Each question is reduced to a finite Lean-checkable calculation and one unbounded condition that remains open. For \#249, a *certificate* is a finite integer calculation plus a rigorous bound on the omitted tail. Put $`M_t=\operatorname{lcm}(1,\ldots,t)`$, the least common multiple of $`1,\ldots,t`$, and $`R_N=\sum_{m\geq1}\varphi(N+m)2^{-m}`$, the original series tail after position $`N`$, rescaled by $`2^N`$. For \#257, skipping rank $`n`$ means omitting the weight $`(2^n-1)^{-1}`$. Its greedy rule takes the next weight exactly when doing so does not overshoot the target $`1/2`$. The two central equivalences, stated before the later proof machinery, are:
``` math
\begin{aligned}
 \substack{\text{finite certificates for }R_{2M_t}-R_{M_t}\notin\mathbb{Z}\\
   \text{at arbitrarily large }t}
 &\quad\Longleftrightarrow\quad S\notin\mathbb{Q},\\[4pt]
 \substack{\text{the greedy expansion of }\tfrac12\text{ skips ranks}\\
   \text{beyond every bound}}
 &\quad\Longleftrightarrow\quad \dfrac12\in\mathcal A,\\[-1pt]
 &\quad\Longrightarrow\quad \text{a counterexample to universal \#257}.
 \end{aligned}
```
The first line is an exact reformulation of \#249. The second concerns only the proposed half-value counterexample to \#257, not the universal statement. Neither line proves the required unbounded behaviour. The current analysis of the final possible skip reduces the second open condition to two explicit obligations; neither obligation is proved.

The phrase “beyond every bound” is essential: finitely many checks settle neither line. The common coordinates give a checked obstruction atlas, not a recurrence mechanism or evidence that the two programmes merge.

The totient constant also has the elementary form
``` math
S=\frac12+\Pr(\gcd(X,Y)=1),
```
where $`X,Y\in\mathbb{N}_{>0}`$ are independent and $`\Pr(X=n)=\Pr(Y=n)=2^{-n}`$. Both series are values of one Lambert transform, but this common description transfers no theorem from one problem to the other; Section <a href="#sec:architecture" data-reference-type="ref" data-reference="sec:architecture">6</a> gives the exact map.

| Question or result | Mathematical status | Treatment in this paper |
|:---|:---|:---|
| Irrationality in \#249 | Open | No proof of $`S\notin\mathbb{Q}`$ is claimed. |
| Denominator exclusion | Proved | If $`S=p/q`$, then $`q>Q_0`$. |
| Tail differences and $`M_t`$-diagonal certificates | Exact equivalences | The unbounded supply is equivalent to $`S\notin\mathbb{Q}`$, but remains open. |
| Diagonal computation | Finite evidence | Lean checks 28 diagonal certificates through $`t=64`$; this is not an unbounded family. |
| Universal assertion in \#257 | Open | No proof covers every infinite support. |
| Structural/support results | Explicit rank theorem; Prior work/formalised | Exact totient-section ranks sharpen known nonregularity in a different form; strict-tail support coding and named irrational supports have prior-work context. None settles \#257. |
| Membership of $`1/2`$ | Open; exact reductions | Greedy and recurrence laws give exact equivalences without proving either event. |

<a id="what-lean-checked-means-here."></a>

#### What “Lean-checked” means here.

A *proof term* is a formal expression that Lean’s kernel accepts as a proof. Here a linked theorem is “Lean-checked” when such a term is accepted from the fixed source revision and dependencies. An exact equivalence remains an equivalence even when both sides are open. A finite calculation remains finite. A theorem with a rationality hypothesis does not prove that a rational support exists. The manuscript, its link checker, and its generated indexes help a reader find the proof but are not themselves proof authority. Section <a href="#sec:verify" data-reference-type="ref" data-reference="sec:verify">7</a> states how the fixed source revision and trusted dependencies are checked.

<a id="reading-map."></a>

#### Reading map.

For a first pass, read Section <a href="#sec:spines" data-reference-type="ref" data-reference="sec:spines">2</a>, followed by Sections <a href="#sec:architecture" data-reference-type="ref" data-reference="sec:architecture">6</a> and <a href="#sec:unresolved" data-reference-type="ref" data-reference="sec:unresolved">8.2</a>: the reductions, the comparison limit, and every remaining obligation. That route contains the headline claims and their open boundaries; the appendices are not needed on a first reading. Sections <a href="#sec:eb" data-reference-type="ref" data-reference="sec:eb">4</a> and <a href="#sec:249" data-reference-type="ref" data-reference="sec:249">5</a> contain the detailed results, and Section <a href="#sec:verify" data-reference-type="ref" data-reference="sec:verify">7</a> gives the verification protocol. The appendices retain alternative certificate, carry, Möbius, and greedy interfaces, local arguments, and audits for readers following a particular route. Linked phrases open the corresponding Lean proofs.

**Keywords.** irrationality; Erdős–Borwein constant; Euler totient; Lambert series; achievement sets; binary carry systems; Lean 4. **MSC 2020.** 11J72 (primary); 11A25, 68V20 (secondary).

<a id="sec:spines"></a>

# The two exact reductions

The first equivalence below restates \#249 itself. The second restates only the proposed half-value counterexample to \#257. Neither equivalence proves the unbounded behaviour that it identifies.

<a id="res:249story"></a>

## Erdős \#249: tail differences and finite certificates

Write
``` math
R_N=\sum_{m\geq1}\frac{\varphi(N+m)}{2^m}.
```
This is the tail of the original series after position $`N`$, multiplied by $`2^N`$; hence $`R_N`$ is $`2^NS`$ minus an integer. Rationality of $`S`$ would force one binary period $`h`$ whose tail differences $`R_{N+h}-R_N`$ are eventually all integral; the certificates below refute exactly such candidate periods (Section <a href="#sec:reduction" data-reference-type="ref" data-reference="sec:reduction">5.3</a>).

<a id="exact-reduction."></a>

#### Exact reduction.

The formal source proves the exact chain
``` math
\begin{split}
 S\notin\mathbb{Q}
 &\quad\Longleftrightarrow\quad
   R_{N+h}-R_N\notin\mathbb{Z}
   \quad\text{for every }h>0\text{ and every }N\\
 &\quad\Longleftrightarrow\quad
   \text{for every }h>0,N\text{ there is an }L
   \text{ with }\mathsf{Sep}(h,N,L).
\end{split}
```
Here $`\mathsf{Sep}(h,N,L)`$ is a retained $`L`$-place residue computation with rigorous tail allowance. At fixed $`h,N`$, some $`L`$ succeeds exactly when the tail difference is non-integral; one integral positive-shift difference forces $`S`$ to be rational. These statements are the [tail-difference equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/LcmConeFlatness.lean#L386), [pointwise certificate equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/LcmConeFlatness.lean#L399), and the fixed-parameter [certificate-completeness theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/LcmConeFlatness.lean#L316).

<a id="unconditional-finite-baseline."></a>

#### Unconditional finite baseline.

Independently of the unbounded certificate supply, if $`S=p/q`$, then
``` math
q>Q_0
 =79\,639\,646\,646\,701\,375\,323\,355\,774\,875\,831\,053.
```
This is the [denominator exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L18056).

<a id="open-boundary."></a>

#### Open boundary.

The exact open statement is an unbounded certificate supply: for every positive $`h`$, non-integral differences $`R_{N+h}-R_N`$ occur at arbitrarily large $`N`$. Theorem <a href="#res:diag" data-reference-type="ref" data-reference="res:diag">25</a> gives the equivalent one-parameter lcm-diagonal form. The 28 changing-lcm scales through $`t=64`$ are verified, but neither this finite computation nor the denominator bound proves the unbounded supply.

<a id="res:halfstory"></a>

## Erdős \#257: half-value membership and final greedy skips

Let
``` math
\mathcal A=\left\{\sum_{n\in A}\frac1{2^n-1}:A\subseteq\mathbb{N}_{>0}\right\}.
```

<a id="exact-reduction-and-finite-exclusion."></a>

#### Exact reduction and finite exclusion.

Writing $`w_n=(2^n-1)^{-1}`$, the weights satisfy $`w_n>\sum_{m>n}w_m`$, so a value has at most one support $`A\subseteq\mathbb{N}_{>0}`$. No finite such support can have value $`1/2`$. For $`1/2`$, the following are equivalent:
``` math
\begin{aligned}
\frac12\in\mathcal A
&\quad\Longleftrightarrow\quad
\text{the set of exponents omitted by the greedy expansion is infinite}\\
&\quad\Longleftrightarrow\quad
\text{a successor terminal bit equal to zero occurs beyond every bound}
\end{aligned}
```
Here the terminal bit is the $`0/1`$ decision recording whether the next greedy weight is taken; Section <a href="#sec:eb" data-reference-type="ref" data-reference="sec:eb">4</a> gives its formal definition. Concretely, the greedy expansion of $`1/2`$ skips rank $`1`$, takes ranks $`2,3`$, skips $`4,5`$, and takes $`6,7`$; membership asks whether such skips recur beyond every bound.

<a id="counterexample-consequence."></a>

#### Counterexample consequence.

Membership would produce an infinite support of rational sum and refute the universal statement of Erdős #257. Thus the counterexample condition is exact: terminal zeros beyond every bound, equivalently no last greedy skip. The formal statements are the [infinite-skip equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L2514), [unbounded-terminal equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L126), [no-last-skip equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L235), and the [finite-support exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryReachability.lean#L589).

<a id="open-boundary.-1"></a>

#### Open boundary.

The open statement is that the terminal bit is zero beyond every bound. The later integer-recurrence analysis splits a putative final skip into two transition branches. It rules out one branch and the integer transition value $`-3`$ in the other, but does not exclude $`-2,-1`$ or prove the required unused-tail inequality for the remaining nonnegative transition values. The exact conditional implication is the [remaining-tail implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderLastProducerContradiction.lean#L387). Proposition <a href="#res:finalskipexclusions" data-reference-type="ref" data-reference="res:finalskipexclusions">17</a> gives the local exclusions and Corollary <a href="#res:taildominance" data-reference-type="ref" data-reference="res:taildominance">18</a> states the sufficient global hypothesis.

<a id="relation-to-prior-work."></a>

#### Relation to prior work.

Prior results are cited at their first use in the body, beginning in Section <a href="#sec:ladder" data-reference-type="ref" data-reference="sec:ladder">3</a>. The claims above concern formalisation and exact logical status; no historical-priority claim is made for the reductions.

<a id="sec:ladder"></a>

# Lambert-series identities and comparison values

Whenever $`\sum_{n\ge1}|f(n)|/(2^n-1)<\infty`$, define the Lambert transform by
``` math
L(f)\;=\;\sum_{n\ge1}\frac{f(n)}{2^n-1}\;=\;\sum_{m\ge1}\frac{(f*\mathbf 1)(m)}{2^m},
\qquad (f*\mathbf 1)(m)=\sum_{d\mid m} f(d),
```
the second equality being the absolutely convergent Lambert rearrangement. It follows by expanding $`(2^n-1)^{-1}=\sum_{k\geq1}2^{-nk}`$, interchanging the sums, and collecting the terms with $`m=nk`$. The coefficient $`(f*\mathbf 1)(m)`$ is the Dirichlet convolution of $`f`$ with the constant function $`\mathbf 1(n)=1`$. We also write $`\mathrm{Id}(n)=n`$, let $`\mu`$ denote the Möbius function, and put $`\sigma(m)=\sum_{d\mid m}d`$. For classical arithmetic-function and Dirichlet-convolution background, see Apostol \[apostol\]. Lambert-series factorisations and their matrix formulations are treated by Merca \[merca2017\] and Merca–Schmidt \[mercaschmidt\].

The rearrangement separates two operations: the divisor transform $`f\mapsto f*\mathbf 1`$, followed by evaluation of the resulting coefficients at binary scales, $`\gamma\mapsto\sum_{m\ge1}\gamma(m)2^{-m}`$. Section <a href="#sec:architecture" data-reference-type="ref" data-reference="sec:architecture">6</a> uses this decomposition to compare the two open questions. Three inputs form the convolution chain
``` math
\alpha \xrightarrow{*\mathbf 1} \varphi
 \xrightarrow{*\mathbf 1} \mathrm{Id},
 \qquad \alpha=\varphi*\mu,
```
whereas $`\mu`$ and $`\mathbf 1`$ are comparison inputs. Write $`E=L(\mathbf 1)=\sum_{n\ge1}(2^n-1)^{-1}`$ for the Erdős–Borwein constant. The weight $`\alpha`$ is nonnegative; for example, $`\alpha(p)=p-2`$ at a prime $`p`$. The corresponding values have the following statuses.

<div class="center">

<div class="tabular">

@llll@ input $`f`$ & value & mathematical status & treatment here\
\
$`\alpha=\varphi*\mu`$ & $`L(\alpha)=S`$ & open (#249) & identities and bounds formalised\
$`\varphi`$ & $`L(\varphi)=2`$ & rational & formalised\
$`\mathrm{Id}`$ & $`L(\mathrm{Id})=\sum\sigma(m)/2^m`$ & transcendental & cited \[nesterenko\]\
\
$`\mu`$ & $`L(\mu)=1/2`$ & rational & formalised\
$`\mathbf 1`$ & $`L(\mathbf 1)=E`$ & irrational & formalised\

</div>

</div>

The arrows apply only to the first three rows. The rows for $`\mu`$ and $`\mathbf 1`$ are separate comparisons, and the table records arithmetic statuses rather than implications between them. In particular, $`S`$ and $`E`$ have the same Mersenne-denominator form, with weights $`\alpha`$ and $`\mathbf 1`$, but no displayed convolution connects those weights. The known status of one row therefore does not transfer to another.

Nesterenko proved that $`\mathbb Q(q,E_2(q),E_4(q),E_6(q))`$ has transcendence degree at least $`3`$ when $`0<|q|<1`$. Since $`q=1/2`$ is algebraic, the three Eisenstein values at $`1/2`$ are algebraically independent. In particular,
``` math
L(\mathrm{Id})=\sum_{m\ge1}\frac{\sigma(m)}{2^m}
 =\frac{1-E_2(1/2)}{24}
```
is transcendental \[nesterenko\].

<div class="proposition">

**Proposition 1** (Two rational Lambert identities).
*``` math
L(\mu)=\sum_{d\ge1}\frac{\mu(d)}{2^d-1}=\frac12,
 \qquad
 L(\varphi)=\sum_{d\ge1}\frac{\varphi(d)}{2^d-1}=2.
```*

</div>

These equalities are formalised as the [Möbius identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/MersenneLambertLadder.lean#L587) and the [totient identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/MersenneLambertLadder.lean#L575). Möbius inversion gives $`\mu*\mathbf 1=(1,0,0,\ldots)`$, while $`\varphi*\mathbf 1=\mathrm{Id}`$; the rearranged sums are therefore $`2^{-1}`$ and $`\sum_{m\geq1}m2^{-m}=2`$, respectively.

<div id="res:lift" class="proposition">

**Proposition 2** (Lambert representation of $`S`$). *With the weight $`\alpha=\varphi*\mu`$,
``` math
\sum_{d\ge1}\frac{\alpha(d)}{2^d-1}\;=\;\sum_{n\ge1}\frac{\varphi(n)}{2^n}\;=\;S.
```*

</div>

The first equality is formalised as the [Lambert representation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L18117). The second is the definition of $`S`$. The proposition places $`S`$ in the same $`\sum(\cdot)/(2^d-1)`$ family as $`E`$, with the nonnegative weight $`\alpha`$.

<a id="probabilistic-reading."></a>

#### Probabilistic reading.

If $`X,Y`$ are independent fair-coin waiting times, $`\Pr(X=n)=2^{-n}`$, then
``` math
S=\tfrac12+\Pr(\gcd(X,Y)=1).
```
Thus Erdős #249 also asks whether the probability that two independent fair-coin waiting times are coprime is irrational. The exact identity is Proposition <a href="#res:coprime" data-reference-type="ref" data-reference="res:coprime">20</a>; its Möbius-square form and the periodic and finite-algebraic variants of these identities are collected in Appendices <a href="#app:lambert-weighted" data-reference-type="ref" data-reference="app:lambert-weighted">[app:lambert-weighted]</a>–<a href="#app:lambert-algebraic" data-reference-type="ref" data-reference="app:lambert-algebraic">12.2</a>.

<a id="what-this-section-provesand-does-not-prove."></a>

#### What this section proves—and does not prove.

The content checked here is $`L(\mu)=1/2`$, $`L(\varphi)=2`$, and $`L(\alpha)=S`$; the transcendental row is cited from Nesterenko. None of these statuses transfers between inputs. For \#249 the remaining issue is still the unbounded certificate supply isolated in Section <a href="#sec:249" data-reference-type="ref" data-reference="sec:249">5</a>; for \#257 this section supplies context rather than either the universal theorem or a rational counterexample.

<a id="sec:eb"></a>

# Erdős–Borwein-type irrationality (the \#257 direction)

We begin with the classical full-support theorem and named structured supports. We then specialise to base $`2`$, where each weight exceeds the sum of all later weights and hence determines a unique support. In these coordinates we derive necessary conditions on a hypothetical rational value, then return to the target $`1/2`$ and its final-skip reduction. None of these results covers arbitrary infinite supports, so the universal assertion in Erdős #257 remains open.

<a id="full-support-the-erdősborwein-constant-every-base"></a>

## Full support: the Erdős–Borwein constant, every base

<div id="res:full" class="theorem">

**Theorem 3** (full-support irrationality). *For every integer $`b\ge2`$, the series $`\displaystyle\sum_{n\ge1}\frac{1}{b^n-1}`$ is irrational. In particular, the Erdős–Borwein constant $`E=\sum_{n\ge1}1/(2^n-1)`$ is irrational.*

</div>

The [all-base theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L8000) and its [base-$`2`$ corollary](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L8007) are formalised. This is Erdős’s 1948 theorem \[erdos1948, Theorem, p. 63\]. Section <a href="#sec:ladder" data-reference-type="ref" data-reference="sec:ladder">3</a> writes this constant as $`L(\mathbf 1)`$, a proved comparison value in the same Mersenne–Lambert family as the open $`S`$. This comparison supplies no further convolution step from $`S`$. Borwein later proved a wider rational-shift Lambert-series theorem \[borwein1992\]; that result is not formalised here.

The proof turns rationality into a spacing obstruction. Its coefficient model is the Lambert identity
``` math
\sum_{n\geq 1}\frac{1}{b^n-1}
   =\sum_{m\geq 1}\frac{\tau(m)}{b^m},
```
where $`\tau(m)`$ is the number of positive divisors of $`m`$; see the [Lambert identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L5865). If the right-hand side were rational with reduced denominator $`q`$, then a non-integral integer multiple could not lie at distance less than $`1/q`$ from an integer. The proof therefore seeks, for every $`q`$, an $`N`$ such that $`b^N\sum_m\tau(m)b^{-m}`$ is non-integral but lies within $`1/q`$ of an integer. This is the formal [near-integer criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L5792).

The construction of $`N`$ is divided into three finite parts. First, a bounded use of Bertrand’s postulate supplies disjoint prime blocks, and the Chinese remainder theorem chooses an arithmetic progression on which
``` math
b^r\mid \tau(N+r) \qquad (1\leq r\leq K).
```
These divisibilities make the first $`K`$ terms of the shifted tail integral. The multiplicativity step that converts prescribed prime valuations into the displayed divisibility is the [prime-block divisibility lemma](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L6177). Second, divisor pairing bounds the average of the weighted middle window
``` math
\sum_{K<r\leq L}\tau(N+r)b^{L-r}
```
along that progression. A pigeonhole choice then selects one translate with a small middle contribution; see the [weighted-middle selection lemma](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L7246). Third, the elementary estimate $`\tau(n)\leq n`$ controls the infinite tail after $`L`$. The parameters are chosen so that the middle and far-tail bounds together are smaller than $`1/q`$; the shifted tail is strictly positive because every divisor count is positive, so the dilated sum is not an integer.

Thus the analytic series is used only in the Lambert identity and the geometric tail estimate. The remaining proof is a finite CRT construction, divisor counting, and explicit parameter arithmetic. The final certificate existence theorem holds for every $`b\geq2`$ and every precision $`q`$; see the [uniform certificate theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L7859). Its composition with the near-integer criterion is Theorem <a href="#res:full" data-reference-type="ref" data-reference="res:full">3</a>, which formalises the classical full-support theorem rather than a new irrationality result.

<a id="named-infinite-support-cases"></a>

## Named infinite-support cases

Beyond full support, the development formalises irrationality for several infinite supports $`A`$ at every base $`b\ge2`$. Each gives one case of \#257. None gives the universal statement, and none is claimed as new mathematics.

<div id="res:support" class="theorem">

**Theorem 4** (irrationality for structured supports). *For every integer $`b\ge2`$, the series $`\sum_{n\in A} 1/(b^n-1)`$ is irrational for each of the following infinite supports $`A`$:*

1.  *factorial support $`A=\{n! : n\ge1\}`$, giving $`\sum 1/(b^{n!}-1)`$;*

2.  *power-of-two support $`A=\{2^n : n\ge0\}`$, giving $`\sum 1/(b^{2^n}-1)`$;*

3.  *multiples $`A=d\mathbb{N}_{>0}=\{dk:k\ge1\}`$ with $`d\ge1`$;*

4.  *pairwise-coprime supports with summable reciprocals (Erdős’s condition \[erdos1968, Theorem, p. 222\]);*

5.  *eventually-periodic supports, residue classes, and the odd numbers.*

</div>

These sort into three groups. The classical case is (d): infinite pairwise-coprime $`A`$ with $`\sum_{a\in A}1/a<\infty`$, formalised from Erdős’s condition. The lcm-gap named cases are (a) and (b), whose support gaps outgrow the running $`\operatorname{lcm}`$; the structured families are (c) and (e).[^1] Formalised case by case by the [factorial-support theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L5707), [power-of-two-support theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L5731), [multiple-support theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L8775), [pairwise-coprime-support theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L10448), and [eventually-periodic-support theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L11276). The residue-class and odd supports in part <span class="upright">(e)</span> are direct specialisations of the last theorem; the first two theorems already hold for every base $`b\geq2`$.

The prime support is now known unconditionally: Tao and Teräväinen proved that
``` math
\sum_p\frac1{2^p-1}=\sum_{n\ge1}\frac{\omega(n)}{2^n}
```
is irrational \[taoteravainen, Theorem 1.3\]. Their proof uses quantitative two-point correlations of multiplicative functions and is not formalised here. This settles the prime-support case, not the universal support statement. They also indicate how the argument should extend to prime-power support, but leave that modification to the reader; it is not counted here as a proved support case.

Cases <span class="upright">(a)</span> and <span class="upright">(b)</span> both use the lcm-gap criterion. The power-of-two case is not a Liouville argument: before $`2^k`$, the prefix lcm is $`2^{k-1}`$, so the gap has only the same size as the lcm. Period noncollapse gives the finite input: the order of $`b`$ modulo the reduced denominator of a partial sum equals that prefix lcm. The denominator therefore exceeds the lcm, while the additive gap to the next exponent still tends to infinity; the tail is then too small for a rational limit.

These theorems apply only when the whole support has one of the stated forms. Finding one listed subseries inside an arbitrary support would not suffice: its irrational value could be cancelled by the complementary subseries. We now fix the base at $`2`$. The support sums form one achievement set. An infinite-support counterexample is a rational point of this set whose unique support is infinite. We first derive necessary conditions for such a rational point and then specialise to $`1/2`$, for which finite support is impossible.

<a id="the-base-2-achievement-set"></a>

## The base-$`2`$ achievement set

For $`n\geq1`$, put
``` math
w_n=\frac1{2^n-1}.
```
For $`n\geq0`$, put
``` math
T_n=\sum_{m>n}w_m,
 \qquad
 \mathcal A=\left\{\sum_{n\in A}w_n:A\subseteq\mathbb{N}_{>0}\right\}.
```
For $`x\geq0`$, define the greedy residuals by $`r_0(x)=x`$ and
``` math
\varepsilon_n(x)=
 \begin{cases}
  1,&w_n\leq r_{n-1}(x),\\
  0,&w_n>r_{n-1}(x),
 \end{cases}
 \qquad
 r_n(x)=r_{n-1}(x)-\varepsilon_n(x)w_n.
```
When $`\varepsilon_n(x)=1`$ we say the expansion *takes* rank $`n`$; otherwise it *skips* rank $`n`$.

<div id="res:greedy" class="theorem">

**Theorem 5** (strict-tail greedy coding). *For every $`n\geq1`$,
``` math
T_n<w_n.
```
Hence every $`x\in\mathcal A`$ has a unique support by positive exponents (the “normalised” support in the formal source). Moreover, a real number $`x`$ lies in $`\mathcal A`$ if and only if $`x\geq0`$ and $`r_n(x)\leq T_n`$ for every $`n\geq0`$. In that case $`x=\sum_{n\geq1}\varepsilon_n(x)w_n`$.*

</div>

The strict-tail inequality and greedy criterion are the [strict-tail theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L180) and [greedy membership theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L1445). Uniqueness is the [support-coding theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L1527). Kovač–Tao provide the strict-tail Cantor-set context \[kovactao, Remark 4.1\].

<a id="geometric-and-finite-arithmetic-consequences."></a>

#### Geometric and finite-arithmetic consequences.

Proposition <a href="#res:greedytopology" data-reference-type="ref" data-reference="res:greedytopology">55</a> proves that $`\mathcal A`$ is compact, perfect, totally disconnected, nowhere dense, and of Lebesgue measure $`1`$. Proposition <a href="#res:death" data-reference-type="ref" data-reference="res:death">56</a> shows that the greedy recursion in exact rational arithmetic agrees step by step with the real recursion and gives sound finite certificates of nonmembership. For the half-value question, Theorem <a href="#res:greedy" data-reference-type="ref" data-reference="res:greedy">5</a> makes the candidate support canonical, while compactness passes from finite approximations at arbitrarily large depths to a point of $`\mathcal A`$. The measure-one statement does not decide whether $`1/2\in\mathcal A`$; a finite certificate can prove nonmembership, but survival through any finite depth proves nothing about membership. These consequences use the same greedy coordinates but are not clauses of the membership equivalence. Their detailed statements and the one-sided certificate boundary are in Appendix <a href="#app:carry-geometry" data-reference-type="ref" data-reference="app:carry-geometry">10.5</a>. No novelty claim is made for the strict-tail geometry. Before specialising to $`1/2`$, we record the carry constraints forced by any rational $`X_A\in\mathcal A`$; these are necessary conditions in the universal direction, not yet a contradiction.

<a id="rigidity-of-a-hypothetical-rational-support"></a>

## Rigidity of a hypothetical rational support

For $`A\subseteq\mathbb{N}_{>0}`$, define
``` math
f_A(m)=\#\{a\in A:a\mid m\},
 \qquad
 X_A=\sum_{a\in A}\frac1{2^a-1}
     =\sum_{m\geq1}\frac{f_A(m)}{2^m},
 \qquad
 T_f(N)=\sum_{j\geq1}\frac{f(N+j)}{2^j}.
```
Thus $`f_A(m)`$ counts the selected exponents dividing $`m`$, $`X_A`$ is the original support sum, and $`T_f(N)`$ is the binary tail of a coefficient sequence after position $`N`$.

<div id="res:rigidity-main" class="theorem">

**Theorem 6** (rational-support carry recurrence). *Suppose that $`A\neq\varnothing`$ and
``` math
X_A=\frac{p}{2^c v},
 \qquad p\in\mathbb{Z},\quad c\in\mathbb{N},\quad v\geq1\ \text{odd}.
```
Then $`u_N=vT_{f_A}(c+N)`$ is a positive integer for every $`N`$, and
``` math
u_{N+1}+v f_A(c+N+1)=2u_N. \tag{4.1}
```*

</div>

This is formalised by [the shifted natural-state theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L668). Here $`u_N`$ is the scaled remaining binary tail, or carry. Equation <span class="upright">(4.1)</span> is binary long division. The identity $`2T_f(M)=f(M+1)+T_f(M+1)`$ shows that doubling the scaled tail separates the next coefficient. Rationality makes the states $`u_N`$ integers. A two-element support, with its explicit period-six orbit and multiplier $`21`$, is worked at the end of Appendix <a href="#app:carry-boolean" data-reference-type="ref" data-reference="app:carry-boolean">10.2</a>. The recurrence is a necessary consequence of rationality, not a criterion by itself. Wang uses the same forward mechanism for $`\gamma(n)=n d_n`$ \[wang2026, Section 3\]; Appendix <a href="#app:carry-normal-form" data-reference-type="ref" data-reference="app:carry-normal-form">10.1</a> separates that antecedent from the generic converse and rigidity statements formalised here. Wang’s density theorem and its Erdős #260 corollary are not used.

<div id="res:rigidity-unbounded-main" class="corollary">

**Corollary 7** (unbounded-state consequence). *Under the hypotheses of Theorem <a href="#res:rigidity-main" data-reference-type="ref" data-reference="res:rigidity-main">6</a>, if $`A`$ is infinite, then $`(u_N)`$ is unbounded.*

</div>

This is formalised by [the unbounded-state theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L2377); see also Theorem <a href="#res:unbounded" data-reference-type="ref" data-reference="res:unbounded">53</a>.

<div id="res:rigidity-sublog-main" class="corollary">

**Corollary 8** (sublogarithmic coverage consequence). *Under the hypotheses of Theorem <a href="#res:rigidity-main" data-reference-type="ref" data-reference="res:rigidity-main">6</a>, for every $`\varepsilon>0`$ there is $`B=B(\varepsilon,c,v)`$ such that every interval $`\{c+N+1,\ldots,c+N+\ell\}`$ on which $`f_A`$ vanishes satisfies
``` math
\ell\leq\varepsilon\log_2(N+1)+B;
```*

</div>

This is formalised by [the sublogarithmic zero-window theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SublogDivisorCoverage.lean#L392); see also Theorem <a href="#res:sublog" data-reference-type="ref" data-reference="res:sublog">49</a>.

<div id="res:rigidity-mass-main" class="corollary">

**Corollary 9** (odd-denominator reciprocal-mass consequence). *Under the hypotheses of Theorem <a href="#res:rigidity-main" data-reference-type="ref" data-reference="res:rigidity-main">6</a>, if $`\rho(A)=\sum_{a\in A}a^{-1}<\infty`$, $`v>1`$, and $`h=\operatorname{ord}_v(2)`$, then
``` math
\rho(A)=\frac{w}{h}
   +\lim_{M\to\infty}\frac1M\sum_{N<M}e_N\geq\frac{w}{h},
```
where $`w`$ is the number of wraps in one doubling-residue cycle and $`e_N=\lfloor u_N/v\rfloor`$ is the integral excess in the split $`u_N=ve_N+\bar p_N`$, with $`\bar p_N`$ the least residue of $`p2^N`$ modulo $`v`$. A step wraps precisely when doubling $`\bar p_N`$ crosses $`v`$; thus $`w`$ counts the resulting carry digits over one cycle of length $`h`$. The term $`w/h`$ is the cycle’s mean residue contribution, while the displayed excess mean is nonnegative. If $`(p,v)=1`$, then $`w\geq1`$.*

</div>

The exact excess-mean identity is [the shifted excess-mean theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L1577); see also Proposition <a href="#res:orderwrap" data-reference-type="ref" data-reference="res:orderwrap">51</a>.

<div id="res:rigidity-dyadic-mass-main" class="corollary">

**Corollary 10** (dyadic reciprocal-mass consequence). *Under the hypotheses of Theorem <a href="#res:rigidity-main" data-reference-type="ref" data-reference="res:rigidity-main">6</a>, if $`v=1`$ and $`A`$ is infinite, then either $`\rho(A)`$ diverges or $`\rho(A)>1`$.*

</div>

This is formalised by [the dyadic reciprocal-mass alternative](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L2200); see also Corollary <a href="#res:collision" data-reference-type="ref" data-reference="res:collision">52</a>.

Read together, the four statements say that rationality would force an unbounded integer state sequence for an infinite support, severely limit intervals containing no support divisor, and constrain the reciprocal mass according to whether the reduced denominator has an odd factor. They are independent necessary consequences of one rationality premise, not a contradiction. The corresponding appendices develop the common recurrence and Boolean certificate, then the sublogarithmic and reciprocal-mass filters. The corollaries share carry machinery but are not hypotheses of one another.

<div id="res:universal-boolean-obstruction" class="corollary">

**Corollary 11** (Boolean–Möbius orbit form of universal \#257). *The universal assertion in Erdős #257 is equivalent to the following orbit statement: for every rational number $`p/q`$, every Boolean–Möbius carry certificate for $`p/q`$ reconstructs a finite support. Equivalently, the universal assertion fails exactly when one such certificate reconstructs an infinite support.*

</div>

Concretely, the name means an integer carry orbit $`U`$ with $`U(0)=p`$, positive states bounded by $`q(2\sqrt N+4)`$, and $`q\mid 2U(N)-U(N+1)`$. Dividing these differences by $`q`$ gives an integer coefficient sequence $`f_U`$. Its Boolean Möbius condition is $`(\mu*f_U)(n)\in\{0,1\}`$, and inversion reconstructs the support as $`A_U=\{n\geq1:(\mu*f_U)(n)=1\}`$. These are exactly the conditions in Theorem <a href="#res:carrycert" data-reference-type="ref" data-reference="res:carrycert">47</a>, the Lean-checked equivalence [support/carry equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/BooleanMobiusCarry.lean#L948); the corollary quantifies it over $`p/q`$ and separates finite from infinite supports. This remains an exact reformulation over infinite objects, not a finite algorithm.

<a id="the-target-12"></a>

## The target $`1/2`$

<a id="why-this-target."></a>

#### Why this target.

Any infinite support with any rational value would refute the universal statement. Fixing $`1/2`$ turns one possible counterexample route into the point-membership question $`1/2\in\mathcal A`$. This target is convenient, not forced.

The reason it is distinguished is the signed Möbius identity $`L(\mu)=1/2`$ from Section <a href="#sec:ladder" data-reference-type="ref" data-reference="sec:ladder">3</a>. A support series is different: each term has coefficient $`0`$ or $`1`$. The most immediate conversion, selecting exactly the indices with $`\mu(d)=-1`$, overshoots $`1/2`$ by at least $`1/63`$ (Proposition <a href="#res:mobiussignnogo" data-reference-type="ref" data-reference="res:mobiussignnogo">45</a>). Moreover, no finite support attains $`1/2`$ (Proposition <a href="#res:nofinitehalf" data-reference-type="ref" data-reference="res:nofinitehalf">14</a> below), while the strict-tail coding of Theorem <a href="#res:greedy" data-reference-type="ref" data-reference="res:greedy">5</a> makes any candidate support unique.

Let
``` math
\mathcal S(x)=\{n\geq1:\varepsilon_n(x)=0\}
```
be the set of exponents omitted by the greedy expansion.

<a id="a-worked-start."></a>

#### A worked start.

The greedy expansion of $`1/2`$ first skips rank $`1`$, because $`w_1=1>\tfrac12`$. It takes rank $`2`$, leaving $`1/6`$, and then rank $`3`$, leaving $`1/42`$. It skips ranks $`4,5`$, whose weights $`1/15`$ and $`1/31`$ exceed that residual. It then takes ranks $`6,7`$, leaving
``` math
\frac12-\Bigl(\frac13+\frac17+\frac1{63}+\frac1{127}\Bigr)
 =\frac1{16002}.
```
The exact calculation continues with the next take at rank $`14`$, and through rank $`26`$ it takes exactly
``` math
2,3,6,7,14,20,21,26.
```
The finite seam model introduced below reproduces this prefix uniformly for every row $`s\geq27`$; this is the [kernel-checked rank-(26) prefix](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfFinalMiddlePhaseSieve.lean#L1190) used again in Appendix <a href="#app:half-final-skip" data-reference-type="ref" data-reference="app:half-final-skip">9.4</a>.

This is only an initial segment. Membership of $`1/2`$ in $`\mathcal A`$ requires the complementary skips to recur beyond every bound. Nonmembership has a finite alternative: one skip is the *last*, precisely when its residual lies strictly above the whole remaining tail (Appendix <a href="#res:fixedtailsocket" data-reference-type="ref" data-reference="res:fixedtailsocket">9.4.6</a>). Theorem <a href="#res:fatalright" data-reference-type="ref" data-reference="res:fatalright">16</a> below identifies nonmembership with the existence of such a skip.

The next definition replaces the real greedy calculation by an integer one. A *row* $`s`$ keeps the ranks $`2,\ldots,s-1`$, rescales every weight by $`4^s`$, rounds down, and uses a target $`2^s`$ below the rescaled value $`4^s/2`$. The resulting zero–one word records the finite take/skip decisions across adjacent cutoffs; this aligned family is the “seam.” Its last entry records whether rank $`s-1`$ is taken or skipped and is the terminal bit used in Theorem <a href="#res:halfmembership" data-reference-type="ref" data-reference="res:halfmembership">13</a>.

<div id="def:terminal-bit" class="definition">

**Definition 12** (finite greedy seam and terminal bit). For an integer $`s\geq6`$, set
``` math
q_{s,d}=\lfloor4^sw_d\rfloor
 =\left\lfloor\frac{4^s}{2^d-1}\right\rfloor
 \quad(2\leq d<s),
 \qquad
 \kappa_s=4^s\cdot\frac12-2^s=2^{2s-1}-2^s.
```
Starting from $`R_{s,2}=\kappa_s`$, define successively, for $`2\leq d<s`$,
``` math
\beta_{s,d}=
 \begin{cases}
  1,&q_{s,d}\leq R_{s,d},\\
  0,&q_{s,d}>R_{s,d},
 \end{cases}
 \qquad
 R_{s,d+1}=R_{s,d}-\beta_{s,d}q_{s,d}.
```
The Boolean word $`(\beta_{s,2},\ldots,\beta_{s,s-1})`$ is the *finite greedy seam at row $`s`$*, and $`\tau_s=\beta_{s,s-1}`$ is its terminal bit (zero means that rank $`s-1`$ is skipped; a final skip is the last such zero).

</div>

For example, at $`s=7`$ we have $`\kappa_7=8064`$, and the run takes $`q_{7,2}=5461`$ and $`q_{7,3}=2340`$, skips $`1092`$ and $`528`$, and takes $`q_{7,6}=260`$, leaving $`3`$: the word is $`1,1,0,0,1`$, matching the real greedy decisions at ranks $`2`$–$`6`$, with terminal bit $`\tau_7=1`$. The seam is thus an exact integer coordinate model of the real greedy process. Appendix <a href="#app:half-final-skip" data-reference-type="ref" data-reference="app:half-final-skip">9.4</a> develops the equivalence with final skips and the unresolved transition carries; the finite coordinate changes in Appendix <a href="#app:half-evidence" data-reference-type="ref" data-reference="app:half-evidence">9.5</a> do not strengthen that equivalence.

<div id="res:halfmembership" class="theorem">

**Theorem 13** (exact half-membership classification). *The following are equivalent:
``` math
\begin{aligned}
\textup{(i)}\;&\quad \frac12\in\mathcal A;\\
\textup{(ii)}\;&\quad \mathcal S(1/2)\ \text{is infinite};\\
\textup{(iii)}\;&\quad \mathcal S(1/2)\ \text{has no largest element};\\
\textup{(iv)}\;&\quad
  \text{for every }N\text{ there is }s\geq\max\{N,6\}
  \text{ with }\tau_s=0.
\end{aligned}
```*

</div>

The omitted-set equivalence is the [infinite-skip theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L2514); the terminal forms are the [unbounded-terminal theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L126) and [no-final-skip theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L235).

<div id="res:nofinitehalf" class="proposition">

**Proposition 14** (finite half-value exclusion). *No finite support $`A\subseteq\mathbb{N}_{>0}`$ has value $`1/2`$.*

</div>

This is the [finite-support theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryReachability.lean#L589).

<div id="res:halfcounterexample" class="corollary">

**Corollary 15** (counterexample from half-membership). *Any one of the equivalent conditions in Theorem <a href="#res:halfmembership" data-reference-type="ref" data-reference="res:halfmembership">13</a> produces an infinite support $`A\subseteq\mathbb{N}_{>0}`$ with $`X_A=1/2`$, and therefore refutes the universal form of Erdős #257.*

</div>

This combines the unique greedy support from Theorem <a href="#res:greedy" data-reference-type="ref" data-reference="res:greedy">5</a> with Proposition <a href="#res:nofinitehalf" data-reference-type="ref" data-reference="res:nofinitehalf">14</a>. A tempting signed-to-Boolean shortcut also fails: selecting precisely the negative Möbius indices overshoots $`1/2`$ by at least $`1/63`$. Proposition <a href="#res:mobiussignnogo" data-reference-type="ref" data-reference="res:mobiussignnogo">45</a> gives the exact sign-separation identity.

In ordinary terms, Theorem <a href="#res:halfmembership" data-reference-type="ref" data-reference="res:halfmembership">13</a> says that membership means no skip is the last. It does not prove that skips continue beyond every bound. The next subsection characterises the opposite case and identifies what would be required to exclude it.

<a id="sec:final-skip-reduction"></a>

## The final-skip reduction

Appendix <a href="#app:half-final-skip" data-reference-type="ref" data-reference="app:half-final-skip">9.4</a> contains the detailed derivations used in this subsection; the statements and their logical status are recorded here. Here $`w_n=(2^n-1)^{-1}`$, and $`T_n=\sum_{m>n}w_m`$ is the full later weight. Assume a final skip, classify its successor by comparing the ranks selected in consecutive seam rows, and eliminate every branch. The elimination stops at two middle carry values and one future-tail inequality; these are the open inputs stated below.

For each $`s\geq6`$, let
``` math
G_s=\{d:2\leq d<s,\ \beta_{s,d}=1\}.
```
Thus $`G_s`$ is the set chosen by the integer greedy run at row $`s`$. Among all subsets of $`\{2,\ldots,s-1\}`$ whose integer weight exceeds $`\kappa_s`$, let $`G_s^\uparrow`$ be the unique one with the smallest weight. It is the cheapest strict overshoot of the target.

The recurrence from row $`s`$ to row $`s+1`$ has three forms:
``` math
\begin{aligned}
 \textup{reset (upper):}&\quad G_{s+1}=G_s^\uparrow,\\
 \textup{keep and skip (middle):}&\quad G_{s+1}=G_s,\\
 \textup{keep and take (right):}&\quad G_{s+1}=G_s\cup\{s\}.
\end{aligned}
```
The parenthetical names are the compact labels used in the formal source. A final skipped exponent $`D`$ is therefore an upper or middle transition followed only by right transitions. The terminal bit at row $`13`$ is false. Consequently, if the seam is eventually right, its last false terminal row satisfies $`D\geq13`$; the lower bound comes from this calculation rather than an omitted range of cases. This is the [last-false row theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderLastProducerContradiction.lean#L178).

At a middle transition $`D\geq13`$, the next question is whether restoring the skipped rank $`D`$ still leaves the support below $`1/2`$. Let
``` math
A_D=G_D\cup\{D\},\qquad f_{A_D}(n)=\#\{a\in A_D:a\mid n\},
```
and put
``` math
P_D=2f_{G_D}(2D+1)+f_{G_D}(2D+2),
 \quad C_D=4R_{D,D}-P_D-4,
 \quad \Theta_D=\sum_{j\geq1}\frac{f_{A_D}(2D+2+j)}{2^j}.
```
Here $`R_{D,D}`$ is the final integer remainder in seam row $`D`$, $`P_D`$ is its paired divisor-incidence pulse, $`C_D\in\mathbb{Z}`$ is the resulting carry, and $`\Theta_D`$ is the full future tail, not a finite truncation. The residual identity of Appendix <a href="#res:producercarry" data-reference-type="ref" data-reference="res:producercarry">9.4.7</a> compares the two quantities exactly:
``` math
\frac12-\sum_{a\in A_D}w_a
 =2^{-(2D+2)}\bigl(C_D-\Theta_D\bigr),
```
so $`\Theta_D<C_D`$ is equivalent to $`\sum_{a\in A_D}w_a<\tfrac12`$.

For a finite set $`u\subseteq\{1,\ldots,d\}`$, write $`V(u)=\sum_{n\in u}w_n`$. Once this prefix through rank $`d`$ is fixed, the next decision is whether to take $`w_{d+1}`$. If it is skipped, even taking every later weight reaches at most $`V(u)+T_{d+1}`$; if it is taken, the resulting sum is at least $`V(u)+w_{d+1}`$. We call $`(u,d)`$ a *fatal half-gap* when $`1/2`$ lies strictly between these two bounds:
``` math
V(u)+T_{d+1}<\frac12<V(u)+w_{d+1}.
```
No support agreeing with $`u`$ through rank $`d`$ can then represent $`1/2`$: extensions omitting rank $`d+1`$ fall short, while those containing it overshoot.

<div id="res:fatalright" class="theorem">

**Theorem 16** (final-skip classification). *Nonmembership of $`1/2`$ in $`\mathcal A`$ is equivalent to each of the following:*

1.  *the integer seam recurrence is eventually right;*

2.  *a fatal half-gap exists;*

3.  *the real greedy expansion of $`1/2`$ has a final skipped exponent.*

</div>

The three equivalent nonmembership criteria are formalised in [fatal-gap classification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFatalGapRightTail.lean#L781), [nonmembership classification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFatalGapRightTail.lean#L787), and [final-skip classification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFatalGapRightTail.lean#L802).

<div id="res:finalskipexclusions" class="proposition">

**Proposition 17** (excluded final-skip branches). *At a final skipped exponent $`D\geq13`$, the upper successor is impossible. On the middle branch, the only carry values outside the ranges $`C_D\leq-4`$ and $`C_D\geq0`$ are $`C_D\in\{-3,-2,-1\}`$. At a final skip, the value $`C_D=-3`$ is impossible; the values $`-2`$ and $`-1`$ remain unresolved.*

</div>

The upper and $`C_D=-3`$ exclusions are the [upper-branch exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderLastProducerContradiction.lean#L250) and [middle-$`-3`$ exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderLastProducerContradiction.lean#L315); the upper case is proved directly at the linked declaration, and Appendix <a href="#app:half-final-skip" data-reference-type="ref" data-reference="app:half-final-skip">9.4</a> sketches a prose argument only for the case $`C_D=-3`$. The three exceptional values are identified by the [three exceptional carry values](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderMiddleCarryLowerBound.lean#L3090).

<div id="res:taildominance" class="corollary">

**Corollary 18** (tail-dominance membership criterion). *If every middle transition at a row $`D\geq13`$ with $`C_D\neq-3`$ satisfies
``` math
\Theta_D<C_D, \tag{4.2}
```
then no final skipped exponent exists, and hence $`1/2\in\mathcal A`$.*

</div>

This implication is the [tail-dominance theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderLastProducerContradiction.lean#L387). Since $`\Theta_D\geq0`$, inequality <span class="upright">(4.2)</span> cannot hold when $`C_D=-2`$ or $`-1`$. The corollary therefore has two open inputs. First, these two carry values must be shown not to occur at any actual middle transition. Second, every remaining middle transition with $`C_D\geq0`$ must have complete future tail smaller than $`C_D`$. Neither input is proved for the greedy orbit. The word “every” is essential: one final middle transition is enough for nonmembership, so a bound that failed at even one row would not rule it out.

<a id="logical-status-of-the-final-skip-argument."></a>

#### Logical status of the final-skip argument.

The proved levels of the argument are
``` math
\begin{array}{rcl}
 \frac12\notin\mathcal A
 &\Leftrightarrow
   \text{a final skipped exponent exists}
 &[\text{proved}],\\
 \text{final upper, or final middle with }C_D=-3
 &\Rightarrow\bot
 &[\text{proved}].
\end{array}
```
These lines do not imply membership. The unproved hypothesis has two parts: exclude all actual middle transitions with $`C_D\in\{-2,-1\}`$, and prove <span class="upright">(4.2)</span> at every remaining non-$`(-3)`$ middle transition. Together they establish the global hypothesis of Corollary <a href="#res:taildominance" data-reference-type="ref" data-reference="res:taildominance">18</a>; only then does Corollary <a href="#res:halfcounterexample" data-reference-type="ref" data-reference="res:halfcounterexample">15</a> produce an infinite rational-valued support and a counterexample to the universal \#257 statement.

<a id="what-remains-open"></a>

## What remains open

The two directions remain separate.

1.  The universal problem is to prove $`X_A\notin\mathbb{Q}`$ for every infinite $`A\subseteq\mathbb{N}_{>0}`$. Theorem <a href="#res:support" data-reference-type="ref" data-reference="res:support">4</a> proves several families, while Theorem <a href="#res:rigidity-main" data-reference-type="ref" data-reference="res:rigidity-main">6</a> and its four corollaries constrain a hypothetical rational support. Neither route supplies the universal quantifier.

2.  The distinguished half-value route asks whether $`1/2\in\mathcal A`$. Theorem <a href="#res:halfmembership" data-reference-type="ref" data-reference="res:halfmembership">13</a> identifies this with infinitely many greedy skips, while Theorem <a href="#res:fatalright" data-reference-type="ref" data-reference="res:fatalright">16</a> identifies nonmembership with a final skip. Proposition <a href="#res:finalskipexclusions" data-reference-type="ref" data-reference="res:finalskipexclusions">17</a> proves that this final transition cannot be upper and that a final middle transition cannot have $`C_D=-3`$. Corollary <a href="#res:taildominance" data-reference-type="ref" data-reference="res:taildominance">18</a> would prove membership if no actual middle transition had $`C_D=-2`$ or $`-1`$, and if every remaining middle transition with $`C_D\geq0`$ satisfied $`\Theta_D<C_D`$, comparing its full future tail to its transition carry as in <span class="upright">(4.2)</span>. Neither statement is proved.

Appendix <a href="#app:half-technical" data-reference-type="ref" data-reference="app:half-technical">9</a> records the exact local reductions, conditional compactness criteria, finite certificates, counterexamples to stronger local assertions, and failed strategies. These narrow the remaining cases but decide neither open \#257 question.

<a id="sec:249"></a>

# The totient constant $`S`$ (Erdős \#249)

Whether
``` math
S=\sum_{n\ge1}\frac{\varphi(n)}{2^n}
```
is irrational remains open. The argument has four logically distinct layers. First, a finite Farey computation excludes every rational denominator up to an explicit bound. Second, irrationality is characterised exactly by the existence of finite certificates against every possible eventual binary period. Third, many such certificates are verified at bounded parameters. Fourth, and still missing, is a theorem supplying them at unbounded parameters. Only the fourth layer would settle the problem.

The main section states this reduction. Appendix <a href="#app:totient-normal" data-reference-type="ref" data-reference="app:totient-normal">11.1</a> gives equivalent forms of the missing assertion that certificates occur at arbitrarily large scales. Appendix <a href="#app:totient-finite" data-reference-type="ref" data-reference="app:totient-finite">11.2</a> collects finite estimates and checked certificates; any conclusion of irrationality there assumes, rather than proves, an unbounded supply. Appendix  <a href="#app:totient-boundaries" data-reference-type="ref" data-reference="app:totient-boundaries">11.3</a> records candidate sufficient conditions and shows why several natural shortcuts fail. Appendix <a href="#app:totient-rank" data-reference-type="ref" data-reference="app:totient-rank">11.4</a> proves exact dyadic rank growth but not the missing implication from that growth to irrationality. Only the first appendix is an exact reformulation of the open fourth layer.

<a id="sec:uncond"></a>

## Unconditional: no small denominator

<div id="res:farey" class="theorem">

**Theorem 19** (denominator exclusion). *Set
``` math
Q_0:=79\,639\,646\,646\,701\,375\,323\,355\,774\,875\,831\,053
       \approx7.96\times10^{34}.
```
For every integer $`p`$ and every $`q`$ with $`1\le q\le Q_0`$,
``` math
S \;\ne\; \frac{p}{q}.
```
Equivalently, if $`S`$ is rational then its reduced denominator exceeds that bound.*

</div>

Formalised as the [denominator-exclusion theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L18056). For a fixed window length $`K`$, the checked prefix and a rigorous tail bound define a finite *denominator-gap* certificate, distinct from the tail-period certificates below. If a denominator $`q`$ failed this check, elementary rearrangement would put some rational $`r/q`$ in a specific short interval. The larger bounds bracket that interval by fractions $`a/b<c/d`$ satisfying $`bc-ad=1`$. The mediant lemma says that every rational strictly between such neighbours has denominator at least $`b+d`$. Thus no $`q<b+d`$ can fail the certificate; for each such $`q`$, the corresponding scaled tail lies strictly between consecutive integers, whereas $`S=m/q`$ would force it to be an integer.

The finite exclusion ladder records the successive verified thresholds
``` math
4838 \;\to\; 4\,194\,304 = 2^{22} \;\to\; 2.49\times10^{17}\ (K{=}120)
\;\to\; 7.96\times10^{34}\ (K{=}240).
```
Farey’s 1816 note supplies only the historical terminology for neighbouring fractions \[farey1816\], not a bound for $`S`$. Every exclusion in this ladder is Lean-checked. The first threshold is a direct low-carry check, $`2^{22}`$ is retained as a named intermediate corollary, and the two largest thresholds use the Farey separation. See [denominator exclusion through 4838](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L15347) and [the intermediate 4194304 bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L18029), then [the 120-term Farey bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GapFareyBound.lean#L88) and [240-term Farey bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GapFareyBound.lean#L176) for the two Farey windows.

This excludes rational denominators through $`Q_0`$, not rationality; larger denominators remain possible. No priority claim is made for the bound.

<div class="remark">

*Remark 1* (one bound, four representations). The Lambert identities of Section <a href="#sec:ladder" data-reference-type="ref" data-reference="sec:ladder">3</a> are equalities, so the same finite record transfers verbatim to three other representations of the constant. The first is the Lambert representation $`\sum_d \alpha(d)/(2^d-1)`$ ([Lambert-representation denominator transfer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L18145)), the second is the signed Möbius-square constant $`T=\sum_d\mu(d)/(2^d-1)^2`$ at half the bound ([signed-square denominator transfer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L18159)), and the third is the coprimality probability of Section <a href="#sec:geom" data-reference-type="ref" data-reference="sec:geom">5.2</a>, also at half the bound. Half appears because $`S=\tfrac12+T`$ turns a denominator $`d`$ for $`T`$ into $`2d`$ for $`S`$.

</div>

<a id="sec:geom"></a>

## The geometric picture: $`S`$ as coprime-pair mass

Let $`X,Y`$ be independent fair-coin waiting times, $`\Pr(X=n)=2^{-n}`$ for $`n\ge1`$. Then $`\Pr(d\mid X)=1/(2^d-1)`$, so the Lambert transform is a divisor calculus of $`X`$: $`L(f)=\mathbb E[(f*\mathbf 1)(X)]`$. The identities give $`L(\mu)=\Pr(X=1)=1/2`$, $`L(\varphi)=\mathbb E[X]=2`$, $`L(\mathbf 1)=\mathbb E[\tau(X)]=E`$, and $`L(\alpha)=\mathbb E[\varphi(X)]=S`$.

Counting visible lattice points $`(a,b)`$ with $`a+b=n`$, $`a\ge1`$, $`b\ge0`$, and $`\gcd(a,b)=1`$ gives exactly $`\varphi(n)`$, uniformly in $`n`$, so $`S`$ is itself a coprime-pair mass.

<div id="res:coprime" class="proposition">

**Proposition 20** (coprimality probability).
*``` math
S \;=\; \tfrac12 \;+\; \Pr\!\big(\gcd(X,Y)=1\big)
\;=\; \tfrac12 \;+\!\!\sum_{\substack{a,b\ge1\\ \gcd(a,b)=1}}\!\! 2^{-(a+b)}.
```*

</div>

Formalised: [coprime-pair representation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L18229), with the underlying lattice identity at [visible-lattice-point identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L18216). Base $`2`$ is the one point where $`\Pr(X=a)\Pr(Y=b)=2^{-(a+b)}`$ needs no normalising constant. Restricting the half-open lattice mass to positive waiting times removes $`(1,0)`$, producing the boundary term $`1/2`$. Thus \#249 asks whether two independent fair-coin waiting times are coprime with irrational probability. After reducing $`(X,Y)`$ by their gcd, the same distribution has an exact Stern–Brocot cylinder decomposition. Appendix <a href="#app:lambert-probability" data-reference-type="ref" data-reference="app:lambert-probability">12.3</a> states the resulting probability law and the sharp Fibonacci stability of its alternating runs. These are unconditional structural theorems inside one representation of $`S`$; they do not produce $`\mathsf{Sep}(h,N,L)`$ certificates after every cutoff.

<a id="sec:reduction"></a>

## Exact certificate characterisation

The inputs—eventual periodicity of rational binary expansions, $`\varphi(n)\le n`$, and geometric tail estimates—are classical. The finite predicate and exact equivalences are formalised here without a priority claim. For $`t\ge1`$, write $`M_t=\operatorname{lcm}(1,\ldots,t)`$.

<a id="why-tail-differences-detect-rationality."></a>

#### Why tail differences detect rationality.

Since $`2^NS=\sum_{n\le N}\varphi(n)\,2^{N-n}+R_N`$, each scaled tail $`R_N`$ is $`2^NS`$ minus an integer. Suppose $`S=p/q`$ with $`q=2^cv`$ and $`v`$ odd. For every multiple $`h`$ of the multiplicative order of $`2`$ modulo $`v`$ and every $`N\geq c`$,
``` math
R_{N+h}-R_N
 =\frac{2^N\bigl(2^h-1\bigr)p}{q}-k
 \in\mathbb{Z}
```
for some integer $`k`$, because $`v\mid2^h-1`$ and $`2^c\mid2^N`$. Rationality therefore supplies one period $`h`$ all of whose tail differences at large $`N`$ are integral; conversely, a single integral positive-shift difference already forces $`S`$ to be rational. A finite certificate refutes one candidate integrality, and refuting every period at arbitrarily large $`N`$ refutes rationality outright. This is the mechanism behind the equivalences of this subsection.

<div id="def:totient-certificate" class="definition">

**Definition 21** (tail differences and finite certificates). For $`N\ge0`$, define the scaled tail
``` math
R_N \;=\; \sum_{m\ge1}\frac{\varphi(N+m)}{2^m}.
```
For $`h\in\mathbb{N}_{>0}`$ and $`N,L\in\mathbb{N}`$, define
``` math
\Delta_{h,N,L}=\sum_{j=0}^{L-1}\big(\varphi(N+h+1+j)-\varphi(N+1+j)\big)\,2^{\,L-1-j}\in\mathbb{Z},
```
with the sum empty when $`L=0`$, and say that $`(h,N,L)`$ is a *finite certificate* when
``` math
\mathsf{Sep}(h,N,L):\quad
N+h+L+2 \;<\; \big(\Delta_{h,N,L}\bmod 2^L\big) \;<\; 2^L-(N+h+L+2).
```

</div>

Here $`h`$ is the candidate period, $`N`$ the tail location, and $`L`$ the number of binary places retained. The notation $`x\bmod 2^L`$ denotes the least residue in $`\{0,\ldots,2^L-1\}`$. The integer $`\Delta_{h,N,L}`$ contains the first $`L`$ binary places of $`R_{N+h}-R_N`$; the two margins bound the omitted tail using $`\varphi(n)\le n`$. Thus each instance of the predicate is decidable by finite integer arithmetic, while its conclusion concerns the infinite tail difference. The strict inequalities are impossible when $`L=0`$, so every successful certificate has positive depth. Heuristically, the two margins together occupy a proportion of about $`2(N{+}h{+}L{+}2)/2^L`$ of the modulus, which is small as soon as $`2^L`$ is large compared with $`N+h+L`$. A certificate can fail only when the residue lies exceptionally close to $`0`$ or $`2^L`$, that is, when the tail difference is exceptionally close to an integer. Nothing in this paper converts that observation into the required supply at arbitrarily large $`N`$.

<div id="res:complete" class="proposition">

**Proposition 22** (certificate completeness). *For every $`h\ge1`$ and $`N\ge0`$,
``` math
\bigl(\exists L,\ \mathsf{Sep}(h,N,L)\bigr)
\quad\Longleftrightarrow\quad
R_{N+h}-R_N\notin\mathbb{Z}.
```*

</div>

This is the [certificate-completeness equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/LcmConeFlatness.lean#L316). Thus the finite predicate loses no information at a fixed pair $`(h,N)`$. Searching $`L=1,2,\ldots`$ is therefore a complete one-sided test at fixed $`(h,N)`$: it halts exactly when the difference is non-integral. When the difference is integral, completeness says that no depth succeeds, so this search does not halt. It is not a two-sided decision procedure for an infinite tail.

<div id="res:pointwisecomplete" class="theorem">

**Theorem 23** (pointwise certificate characterisation). *The following are equivalent:
``` math
\begin{aligned}
 &S\notin\mathbb{Q},\\
 &\forall\,h\ge1\ \forall\,N\ge0,\qquad R_{N+h}-R_N\notin\mathbb{Z},\\
 &\forall\,h\ge1\ \forall\,N\ge0\ \exists\,L,\qquad
      \mathsf{Sep}(h,N,L).
\end{aligned}
```*

</div>

Formalised: [all-differences equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/LcmConeFlatness.lean#L386), and [pointwise certificate equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/LcmConeFlatness.lean#L399). The converse direction uses the fact that integrality of even one positive-shift tail difference forces $`S`$ to be rational ([integral-difference rationality criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/LcmConeFlatness.lean#L357)).

The next two equivalences compress the search without changing its conclusion. Theorem <a href="#res:red21" data-reference-type="ref" data-reference="res:red21">24</a> replaces “every $`N`$” by one $`N`$ after every cutoff for each $`h`$; Theorem <a href="#res:diag" data-reference-type="ref" data-reference="res:diag">25</a> then restricts both $`h`$ and $`N`$ to $`M_t`$. A bounded list satisfies neither condition.

<div id="res:red21" class="theorem">

**Theorem 24** (exact tail-period characterisation). *$`S`$ is irrational if and only if, for every period $`h\ge1`$ and every threshold $`N_0`$, there exist $`N\ge N_0`$ and $`L`$ with $`\mathsf{Sep}(h,N,L)`$.*

</div>

Formalised as the [certificate-supply equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/LcmConeFlatness.lean#L412).

For the diagonal compression, every multiple of an eventual period is again a period, and every fixed $`h`$ divides $`M_t`$ for all $`t\geq h`$. Setting both period and tail location to $`M_t`$ therefore tests every candidate period.

<div id="res:diag" class="theorem">

**Theorem 25** (exact diagonal characterisation). *The following are equivalent:
``` math
\begin{aligned}
 &S\notin\mathbb{Q};\\
 &\forall\,t_0\in\mathbb{N}\ \exists\,t\geq t_0\ \exists\,L,\qquad
   \mathsf{Sep}(M_t,M_t,L).
\end{aligned}
```*

</div>

Formalised as the [exact lcm-diagonal characterisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/LcmConeFlatness.lean#L426). This replaces the two free parameters $`h,N`$ by $`(M_t,M_t)`$; producing such certificates at arbitrarily large $`t`$ is still open.

<div id="res:deposits" class="example">

**Example 26** (verified finite range). Lean checks:

- $`\mathsf{Sep}(h,12,16)`$ for every $`1\le h\le8`$;

- a fixed-window certificate for every $`1\le h\le16`$;

- diagonal certificates $`\mathsf{Sep}(M_t,M_t,L)`$ at $`t=1`$ and every lcm-height change endpoint $`2\le t\le64`$ (that is, $`M_{t-1}<M_t`$), namely
  ``` math
  \begin{aligned}
  t\in\{&1,2,3,4,5,7,8,9,11,13,16,17,19,23,25,27,\\
        &29,31,32,37,41,43,47,49,53,59,61,64\};
  \end{aligned}
  ```

- three finite lists of tails that cannot all share one fractional part.

</div>

These four classes are formalised by the [small-window certificate family](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TotientTailPeriodKiller.lean#L404), [periods through sixteen](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CarrySurvivorExtinction.lean#L574), [28 imported diagonal certificates through scale 64](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalPincerCertificatesT64.lean#L1967), and [joint-nonflatness table](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/LcmConeNonflat.lean#L506).

For example, at $`(h,N,L)=(1,12,16)`$,
``` math
\Delta_{1,12,16}=-143140,\qquad
\Delta_{1,12,16}\bmod 2^{16}=53468,
```
while the omitted-tail allowance is $`12+1+16+2=31`$. Hence
``` math
31<53468<2^{16}-31,
```
which is exactly $`\mathsf{Sep}(1,12,16)`$ and therefore proves $`R_{13}-R_{12}\notin\mathbb{Z}`$. A pairwise certificate names a non-integral difference; a joint certificate proves that one exists in a finite list. Neither forms an unbounded family.

<a id="sec:249-open"></a>

## What remains open

By Theorem <a href="#res:red21" data-reference-type="ref" data-reference="res:red21">24</a>, the unresolved statement is precisely
``` math
\forall h\ge1\ \forall N_0\ge0\ \exists N\ge N_0\ \exists L\ge1,\qquad
\mathsf{Sep}(h,N,L).
\tag{5.1}\label{eq:unbounded-certificate-supply}
```
The diagonal condition in Theorem <a href="#res:diag" data-reference-type="ref" data-reference="res:diag">25</a> is an equivalent one-parameter form of this statement. The verified scales in Example <a href="#res:deposits" data-reference-type="ref" data-reference="res:deposits">26</a> form a finite set; they do not give certificates for every period after every cutoff. No theorem in the formal source proves <a href="#eq:unbounded-certificate-supply" data-reference-type="eqref" data-reference="eq:unbounded-certificate-supply">[eq:unbounded-certificate-supply]</a>; consequently no irrationality claim for $`S`$ is made here.

<div class="remark">

*Remark 2* (finite inspection cannot establish the supply). The finite status of the verified scales is forced, not cautious. Fix a bound $`B\ge1`$ and a period $`P>B`$, and define $`\gamma(n)=\varphi(n)`$ for $`n\le B`$, while for $`n>B`$ let $`\gamma(n)=n-1`$ if $`P\mid n`$ and $`\gamma(n)=n`$ otherwise. Then $`0\le\gamma(n)\le n`$, and
``` math
\sum_{n\ge1}\frac{\gamma(n)}{2^n}
 =\sum_{n\le B}\frac{\varphi(n)}{2^n}+\frac{B+2}{2^B}-\frac1{2^P-1}
```
is rational, and its reduced denominator has odd part exactly $`2^P-1`$. Every finite computation that inspects only coefficients with index at most $`B`$ — in particular every certificate $`\mathsf{Sep}(h,N,L)`$ with $`N+h+L\le B`$ — returns the same result for $`\gamma`$ as for $`\varphi`$, and choosing $`P`$ with $`2^P-1>Q_0`$ makes the splice consistent with the denominator exclusion as well. This elementary splice is not formalised in the source and proves nothing about $`\varphi`$ itself; it shows that a proof of <a href="#eq:unbounded-certificate-supply" data-reference-type="eqref" data-reference="eq:unbounded-certificate-supply">[eq:unbounded-certificate-supply]</a> must use totient values at unbounded indices, so no extension of the finite record in Example <a href="#res:deposits" data-reference-type="ref" data-reference="res:deposits">26</a> can establish the supply.

</div>

Appendix <a href="#app:totient-normal" data-reference-type="ref" data-reference="app:totient-normal">11.1</a> records the exact reformulations of this open obligation. Appendix <a href="#app:totient-finite" data-reference-type="ref" data-reference="app:totient-finite">11.2</a> records fixed-scale enclosures, projections, and certificates, followed by conditional implications that assume them at arbitrarily large scales. Appendices  <a href="#app:totient-boundaries" data-reference-type="ref" data-reference="app:totient-boundaries">11.3</a>–<a href="#app:totient-rank" data-reference-type="ref" data-reference="app:totient-rank">11.4</a> delimit candidate unbounded routes. None proves <a href="#eq:unbounded-certificate-supply" data-reference-type="eqref" data-reference="eq:unbounded-certificate-supply">[eq:unbounded-certificate-supply]</a>.

<a id="sec:architecture"></a>

# One transform and the limit of finite evidence

This section maps the two open reductions and the limit of finite evidence. It adds organisation, not theorems; its closing elementary observation is explicitly unformalised.

<a id="sec:one-transform"></a>

## One transform, three distinct questions

The Lambert rearrangement of Section <a href="#sec:ladder" data-reference-type="ref" data-reference="sec:ladder">3</a> factors the common transform through two maps, the divisor transform followed by binary evaluation:
``` math
f\;\longmapsto\;f*\mathbf 1\;\longmapsto\;
 \sum_{m\ge1}\frac{(f*\mathbf 1)(m)}{2^m}\;=\;L(f).
```
In this summary, $`*`$ denotes Dirichlet convolution, $`\mathbf 1`$ is the constant-one arithmetic function, $`\mu`$ is the Möbius function, and $`\alpha=\varphi*\mu`$; Section <a href="#sec:ladder" data-reference-type="ref" data-reference="sec:ladder">3</a> gives the full definitions. Here $`(f*\mathbf 1)(m)=\sum_{d\mid m}f(d)`$ is the *divisor stream*: the first map sums over divisors, and the second reads those sums as binary-series coefficients. The input $`f=\alpha`$ gives $`L(\alpha)=S`$ with divisor stream $`\alpha*\mathbf 1=\varphi`$ (Proposition <a href="#res:lift" data-reference-type="ref" data-reference="res:lift">2</a>). A support indicator $`f=\mathbf 1_A`$ gives $`L(\mathbf 1_A)=X_A`$ with divisor stream $`f_A(m)=\sum_{d\mid m}\mathbf 1_A(d)`$ (Appendix <a href="#app:carry-boolean" data-reference-type="ref" data-reference="app:carry-boolean">10.2</a>). The comparison inputs $`\mu`$, $`\mathbf 1`$, and $`\varphi`$ give the comparison values listed in Section <a href="#sec:ladder" data-reference-type="ref" data-reference="sec:ladder">3</a>.

For any $`\mathbb{N}`$-valued stream $`\gamma`$ with $`\gamma(n)\le n`$, including $`\varphi`$ and every $`f_A`$, Theorem <a href="#res:rigidity" data-reference-type="ref" data-reference="res:rigidity">44</a> says that $`\sum_n\gamma(n)2^{-n}`$ is rational exactly when an integer sequence $`u(N)`$ and positive integer $`v`$ satisfy $`v\gamma(N+1)=2u(N)-u(N+1)`$ and $`u(N)=o(2^N)`$. This exact recurrence plus subexponential bound is what *tempered integer orbit* means here. Tail differences (Section <a href="#sec:reduction" data-reference-type="ref" data-reference="sec:reduction">5.3</a>) and carry states (Theorem <a href="#res:rigidity-main" data-reference-type="ref" data-reference="res:rigidity-main">6</a>) are two coordinates for that condition. Möbius inversion recovers the underlying input: $`\alpha=\varphi*\mu`$ for \#249 and $`\mu*f_A=\mathbf 1_A`$ for \#257 (Proposition <a href="#res:boolmob" data-reference-type="ref" data-reference="res:boolmob">46</a>).

The three open questions have different quantifiers, even though they use this one map. Write $`\mathcal I_\infty`$ for the indicator functions $`\mathbf 1_A`$ of infinite supports $`A\subseteq\{2,3,\ldots\}`$. Restricting to exponents at least $`2`$ loses no universal-#257 case: toggling exponent $`1`$ adds the rational number $`1`$, so it preserves whether $`X_A`$ is rational. Then:

1.  Erdős #249 fixes one input and asks for the status of its one value: $`L(\alpha)=S\notin\mathbb{Q}`$?

2.  Universal \#257 asks whether every permitted value is irrational: $`L(\mathcal I_\infty)\cap\mathbb{Q}=\varnothing`$. Its negation is one infinite support $`A`$ with $`X_A\in\mathbb{Q}`$.

3.  The half-value route fixes one rational target and asks an existence question: $`L^{-1}(1/2)\cap\mathcal I_\infty\ne\varnothing`$. Here $`L^{-1}(1/2)`$ is the *fibre*, meaning all inputs mapped to $`1/2`$. Theorem <a href="#res:greedy" data-reference-type="ref" data-reference="res:greedy">5</a> allows at most one positive-exponent support in that fibre, namely the canonical greedy orbit.

Question (iii) would refute (ii), but failure at the particular target $`1/2`$ would not prove (ii): another rational target could still be reached. Figure <a href="#fig:transform" data-reference-type="ref" data-reference="fig:transform">1</a> marks these three ways of interrogating the map; it supplies no theorem transferring status between them.

<figure id="fig:transform" data-latex-placement="t">

<figcaption>The one transform behind the paper, with the statuses of Section <a href="#sec:ladder" data-reference-type="ref" data-reference="sec:ladder">3</a>. Labels (i)–(iii) are the three questions of Section <a href="#sec:one-transform" data-reference-type="ref" data-reference="sec:one-transform">6.1</a>. Label (i), #249, fixes the top input and asks about the single image point <span class="math inline"><em>S</em></span>. Label (ii), universal #257, restricts the domain to indicators of infinite supports and asks whether its image ever meets <span class="math inline">ℚ</span>. Label (iii), the half-value route, fixes the value <span class="math inline">1/2</span>, reached by the signed Möbius input through the stream <span class="math inline">1, 0, 0, …</span>, and asks whether an infinite Boolean input reaches it as well. The figure organises statements proved in Sections <a href="#sec:ladder" data-reference-type="ref" data-reference="sec:ladder">3</a>–<a href="#sec:eb" data-reference-type="ref" data-reference="sec:eb">4</a> and Appendix <a href="#sec:carry" data-reference-type="ref" data-reference="sec:carry">10</a>; it asserts nothing further.</figcaption>
</figure>

<a id="why-no-status-transfers"></a>

## Why no status transfers

The transform alone does not determine status: Section <a href="#sec:ladder" data-reference-type="ref" data-reference="sec:ladder">3</a> gives rational $`L(\varphi)=2`$ and $`L(\mu)=1/2`$, irrational $`L(\mathbf 1)=E`$, transcendental $`L(\mathrm{Id})`$, and open $`L(\alpha)=S`$.

Nor do simple input properties distinguish them: $`\varphi`$ and $`\mathbf 1`$ are positive, multiplicative, and at most linear, yet their values are rational and irrational. Every finite Boolean support has rational value, whereas Theorem <a href="#res:support" data-reference-type="ref" data-reference="res:support">4</a> gives infinite supports with irrational values. Appendix <a href="#app:carry-boolean" data-reference-type="ref" data-reference="app:carry-boolean">10.2</a> works out the finite support $`\{2,3\}`$, value $`10/21`$, and its period-six carry orbit.

The transform therefore leaves the input-specific arithmetic untouched: exact totient values for \#249, Boolean Möbius inversion plus infinitude for universal \#257, and greedy divisor feedback for the half-value fibre. Appendix <a href="#app:totient-boundaries" data-reference-type="ref" data-reference="app:totient-boundaries">11.3</a> rules out several generic shortcuts.

<a id="the-shared-bottleneck"></a>

## The shared bottleneck

Both reductions require finite events beyond every proposed cutoff, but the conclusions point in opposite directions. In literal quantifiers,
``` math
\begin{aligned}
 S\notin\mathbb{Q}
 &\quad\Longleftrightarrow\quad
 \forall h\ge 1\;\forall N_0\;\exists N\ge N_0\;\exists L\;
 \mathsf{Sep}(h,N,L),\\
 \frac12\in\mathcal A
 &\quad\Longleftrightarrow\quad
 \forall N_0\;\exists s\ge\max\{N_0,6\}\;(\tau_s=0).
\end{aligned}
```
The first line requires separating certificates after every cutoff for each shift $`h`$; the second requires terminal zero bits after every row cutoff. The events belong to different constructions and imply opposite kinds of conclusion: irrationality in the first line, membership in the second. Proposition <a href="#res:complete" data-reference-type="ref" data-reference="res:complete">22</a>, Theorem <a href="#res:pointwisecomplete" data-reference-type="ref" data-reference="res:pointwisecomplete">23</a>, and Theorem <a href="#res:red21" data-reference-type="ref" data-reference="res:red21">24</a> give the first equivalence; Theorem <a href="#res:halfmembership" data-reference-type="ref" data-reference="res:halfmembership">13</a> gives the second. Neither required unbounded-depth supply is known. By contrast, the classical full-support argument uses Bertrand–CRT and averaging to construct witnesses at every precision. Other coordinate identities and rational-support filters do not change either missing quantifier.

In these coordinates, resolving the displayed statements requires $`\mathsf{Sep}`$-certificates at unbounded parameters for \#249, or terminal zeros beyond every row cutoff (or an eventually right greedy seam) for the half-value route. More fixed-scale computation alone changes neither open statement.

<a id="what-finite-witnesses-can-decide."></a>

#### What finite witnesses can decide.

Here a *finite witness* is exactly checkable data whose conclusion does not assume how the uninspected tail behaves; its force depends on the claim. For the half-value route, a finite calculation can settle nonmembership. By Theorem <a href="#res:fatalright" data-reference-type="ref" data-reference="res:fatalright">16</a>, $`1/2\notin\mathcal A`$ is equivalent to the existence of a fatal half-gap. Exact rational evaluation of the greedy prefix, together with the rational tail enclosures of Proposition <a href="#res:death" data-reference-type="ref" data-reference="res:death">56</a>, can verify such a gap after finitely many steps. The gap excludes every support agreeing with that prefix. The reverse direction has no finite certificate here: survival through any finite row is inconclusive, while membership requires $`\tau_s=0`$ beyond every row cutoff.

For $`S`$, each $`\mathsf{Sep}`$-certificate has narrower scope: it proves that one specified tail difference is non-integral. Theorem <a href="#res:red21" data-reference-type="ref" data-reference="res:red21">24</a> requires certificates after every cutoff for every positive shift, so no single certificate proves irrationality. Rationality forces eventual integrality, but failure to find a certificate at one truncation proves neither integrality nor rationality: a greater binary depth $`L`$ may still certify the same tail difference. Thus finite discovery can certify half-value nonmembership, but not half-value membership or either status of $`S`$ within these certificate systems.

<div class="remark">

*Remark 3* (why finite agreement does not decide the open cases). The following two elementary countermodels are not formalised in the source. Both alter the object beyond a finite inspected range; neither makes a claim about the actual totient stream or the actual Mersenne weights.

For \#249, any fixed finite family of certificate computations inspects only finitely many coefficients. The splice in Section <a href="#sec:249-open" data-reference-type="ref" data-reference="sec:249-open">5.4</a> constructs a stream $`\gamma`$ agreeing with $`\varphi`$ on all of them, still satisfying $`0\leq\gamma(n)\leq n`$, whose binary series is rational. The same finite output is therefore compatible with rationality. A proof of the missing supply must use totient values beyond every fixed bound.

For the half-value route, fix any finite prefix of greedy decisions and replace only the uninspected weights by a ratio-one-third geometric tail. If its total mass is below the pending residual, the complete modified tail falls short and the last inspected skip is final. If its total mass equals the residual, that tail realises the target. Both choices preserve strict tails and every inspected decision. Thus a finite prefix and strict-tail geometry do not decide membership; a proof must use the specific Mersenne arithmetic of the tail.

</div>

<a id="sec:verify"></a>

# Formal verification and reproducibility

This section records proof authority and reproducibility; it does not add a mathematical conclusion to either reduction.

<a id="proof-authority-and-source-identity."></a>

#### Proof authority and source identity.

The Lean 4 proof assistant \[lean\] and Mathlib library \[mathlib\] check the named results. The source, links from prose to formal statements, and build instructions are available in the [public repository](https://github.com/wcook04/plectis-lean-erdos249-257). This paper fixes source revision `ebc98ee71f68`, published under the tag [`formal-source-2026-07-18`](https://github.com/wcook04/plectis-lean-erdos249-257/tree/formal-source-2026-07-18). The blue links resolve to immutable source files at that checkpoint. The release also fixes the Lean and Mathlib versions; the toolchain is Lean `v4.29.1`.

<a id="reproduction-commands-and-artefact-identities."></a>

#### Reproduction commands and artefact identities.

A fresh copy of the published repository is checked with `lake build`. The release command also checks that every registered claim resolves to its stated Lean declaration (a named theorem or definition) and manuscript location, that the PDF matches the committed source, and that the public source tag resolves to the recorded revision. The resulting report records release validation; it is not mathematical proof authority. The repository records SHA-256 cryptographic hashes for the claims file, Lean-declaration index, manuscript source, rendered PDF, and generated navigation files, together with their regeneration commands. No hardware-independent build time is claimed; elapsed time depends on the Lean cache and machine, and is not part of the mathematical claim.

<a id="what-the-computation-establishes."></a>

#### What the computation establishes.

Lean elaborates each declaration into a proof term, which the kernel checks; tactics construct these terms but are not separate proof authority. `norm_num` constructs concrete arithmetic proofs, and `decide` reduces a decidable finite proposition to obtain a proof. The [finite survivor-count theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfFinalMiddlePhaseSieve.lean#L2050) uses `decide` to count 412 phases. Its local `maxRecDepth` setting only raises the permitted unfolding depth; the proposition and logical rules are unchanged. The finite survivor-count proof does not use compiler-backed native evaluation, and its adjoining `#print axioms` report lists neither `Lean.trustCompiler`, which would trust compiler evaluation, nor `sorryAx`, Lean’s unfinished-proof axiom. Generated Lean certificate declarations receive the same check; external data, scripts, indexes, and this manuscript do not receive kernel proof checking. Appendix <a href="#app:index" data-reference-type="ref" data-reference="app:index">13</a> connects each displayed result to its exact formal statement.

<a id="section-consequence."></a>

#### Section consequence.

At the published source revision, the linked declarations and their checked proof terms certify the stated proved, conditional, finite, and equivalence results. This verification does not change the mathematical status of the unresolved statements: the open problems collected in Section <a href="#sec:further" data-reference-type="ref" data-reference="sec:further">8</a> remain open.

<a id="sec:further"></a>

# Exact remaining problems and further questions

Section <a href="#sec:spines" data-reference-type="ref" data-reference="sec:spines">2</a> gives the exact reductions. Here we record two concrete sufficient criteria and then state the unresolved questions. Erdős \#249 has one open obligation in two equivalent forms. Erdős \#257 has a universal statement and a counterexample route pointing in opposite directions: half-value membership would refute the universal statement, while nonmembership would decide only the half-value question.

<a id="two-concrete-scalar-criteria"></a>

## Two concrete scalar criteria

Two scalar conditions give conditional implications for the two open directions. Both are exact arithmetic statements; neither hypothesis is proved at the unbounded range needed for its conclusion.

For \#249, retain $`M_t=\operatorname{lcm}(1,\ldots,t)`$ and write
``` math
P_L(N)=\sum_{j=0}^{L-1}\varphi(N+1+j)\,2^{L-1-j}.
```
Thus $`P_L(N)`$ is the base-two weighted block of the next $`L`$ totient values after $`N`$. At scale $`t`$, choose one logarithmic depth and compare the blocks after $`M_t`$ and $`2M_t`$:
``` math
m_t=\lfloor\log_2 M_t\rfloor+10,\qquad
 \delta_t=\bigl(P_{m_t}(2M_t)-P_{m_t}(M_t)\bigr)\bmod 2^{m_t},
```
where $`0\le \delta_t<2^{m_t}`$. The integer $`\delta_t`$ is their block-difference residue. Define
``` math
\sigma_t=\min\bigl(\delta_t-2^{m_t-5},
    (2^{m_t}-2^{m_t-5})-\delta_t\bigr)\in\mathbb{Z}.
```
This signed band-edge distance, called *slack* below, is nonnegative exactly on the central band and negative outside it.

<div id="res:slackfrontier" class="proposition">

**Proposition 27** (fixed-depth central-band equivalence). *For every $`t\ge1`$, the residue $`\delta_t`$ lies in the central band $`[2^{m_t-5},2^{m_t}-2^{m_t-5}]`$ if and only if $`\sigma_t\ge0`$.*

</div>

This fixed-scale equivalence and its beyond-every-cutoff strict-jump form are the [canonical central-band equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalFreshLossBridge.lean#L2469) and [strict-jump slack equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalFreshLossBridge.lean#L2559).

<div id="res:slackcriterion" class="corollary">

**Corollary 28** (central-band supply criterion for irrationality). *If, for every $`t_0`$, there is a $`t\ge\max\{3,t_0\}`$ such that
``` math
M_t<M_{t+1}\qquad\text{and}\qquad \sigma_t\ge0,
```
then $`S`$ is irrational.*

</div>

This implication is the [strict-jump slack irrationality criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalFreshLossBridge.lean#L2731). The proposition is a fixed-$`t`$ equivalence; the corollary gives only sufficiency. No converse is known: completeness may choose a depth from the tail difference, whereas this criterion fixes $`m_t`$. Persistent negative slack at that depth refutes only this route and does not decide whether $`S`$ is rational.

For \#257, write $`r_n=r_n(1/2)`$ for the unrepresented remainder after rank $`n`$. The exact tail expansion and second-scale normalisation are
``` math
T_n=2^{-n}+\frac13\,4^{-n}+E_n,
 \qquad u_n=4^n(2r_n-2^{-n}),
```
where $`0\le4^nE_n\le(2/7)2^{-n}`$. The identity $`u_n-1/3=4^n(2r_n-T_n)+4^nE_n`$ explains the centre $`1/3`$: distance from it is the scaled residual–tail imbalance, up to the bounded error. Under $`r_n\le T_n`$, the next step survives exactly when $`\lvert2r_n-T_n\rvert\ge w_{n+1}-T_{n+1}`$. A sufficient condition is
``` math
\frac16+\frac{37}{56}2^{-n}\le \left|u_n-\frac13\right|.
```
We call this the *residual–tail separation condition*. Here $`37/56=2/7+3/8`$ budgets the higher-tail and gap errors, respectively. The absolute value is needed because $`u_n<0`$ at $`n=3,4`$.

<div id="res:secondfrontier" class="proposition">

**Proposition 29** (verified residual–tail separation through rank $`6`$). *The residual–tail separation condition is decidable over $`\mathbb{Q}`$ and holds for $`1\le n\le6`$.*

</div>

This is the [verified rank-(6) residual–tail separation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L2723).

<div id="res:secondcriterion" class="corollary">

**Corollary 30** (eventual residual–tail separation criterion). *If the residual–tail separation condition holds for every $`n\ge7`$, then $`1/2`$ belongs to the Mersenne achievement set $`\mathcal A`$.*

</div>

This implication is the [eventual residual–tail separation criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L2901). The finite proposition supplies $`1\le n\le6`$, but no case with $`n\ge7`$; no converse is proved. Membership itself has the exact characterisation
``` math
1/2\in\mathcal A
  \quad\Longleftrightarrow\quad
  \text{the canonical greedy orbit omits infinitely many exponents}.
```
This is formalised at [half-membership–infinite-skip equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L2514). The forward implication uses the [full-support irrationality theorem](#res:full); for the reverse, if a residual ever exceeds the remaining tail, every later exponent is selected; hence only finitely many omissions remain. The $`n\ge7`$ hypothesis is open. If proved, it would yield an infinite support of rational value $`1/2`$, refuting rather than proving the universal \#257 statement.

<a id="dependency-direction."></a>

#### Dependency direction.

The two criteria have the proved logical form
``` math
\begin{array}{c}
 \text{after every cutoff, nonnegative slack}\\[-1pt]
 \text{occurs at a strict lcm jump}\\
 \Downarrow\\
 \text{unbounded \#249 certificate supply}\\
 \Downarrow\\
 S\notin\mathbb{Q}
\end{array}
\qquad\qquad
\begin{array}{c}
 \text{residual--tail separation}\\[-1pt]
 \text{for every }n\ge7\\
 \Downarrow\\
 \dfrac12\in\mathcal A\\
 \Updownarrow\\
 \mathcal S(1/2)\text{ is infinite}.
\end{array}
```
Neither premise is proved. The range $`1\le n\le6`$ is only a finite prefix of the second. The left conclusion settles \#249; the right would refute, not prove, the universal \#257 statement.

<a id="sec:unresolved"></a>

## The unresolved statements

<a id="erdős-249-one-obligation-in-two-equivalent-forms."></a>

#### Erdős \#249: one obligation in two equivalent forms.

<div class="problem">

**Problem 31** (Erdős \#249). Prove that
``` math
S=\sum_{n\ge1}\frac{\varphi(n)}{2^n}
```
is irrational.

</div>

By Theorem <a href="#res:red21" data-reference-type="ref" data-reference="res:red21">24</a>, the preceding problem is equivalent to the following exact quantifier statement.

<div class="problem">

**Problem 32** (unbounded certificate supply). Prove that for every $`h\ge1`$ and cutoff $`N_0\ge0`$, there exist $`N\ge N_0`$ and $`L\ge1`$ with $`\mathsf{Sep}(h,N,L)`$, where $`\mathsf{Sep}`$ is the finite tail-separation certificate defined in Section <a href="#res:249story" data-reference-type="ref" data-reference="res:249story">2.1</a>. Equivalently, prove the lcm-diagonal supply in Theorem <a href="#res:diag" data-reference-type="ref" data-reference="res:diag">25</a>. The finite scales in Example <a href="#res:deposits" data-reference-type="ref" data-reference="res:deposits">26</a> do not establish either unbounded form.

</div>

These are not two independent open problems: Theorem <a href="#res:red21" data-reference-type="ref" data-reference="res:red21">24</a> and Theorem <a href="#res:diag" data-reference-type="ref" data-reference="res:diag">25</a> identify the second as an exact certificate form of the first.

<a id="erdős-257-universal-statement-and-counterexample-route."></a>

#### Erdős \#257: universal statement and counterexample route.

<div class="problem">

**Problem 33** (universal Erdős \#257). Prove that
``` math
\sum_{n\in A}\frac{1}{2^n-1}
```
is irrational for every infinite set $`A\subseteq\mathbb{N}_{>0}`$, rather than only for the support families in Theorem <a href="#res:support" data-reference-type="ref" data-reference="res:support">4</a>.

</div>

<div class="problem">

**Problem 34** (the half-value counterexample route). Decide whether $`1/2\in\mathcal A`$. By Theorem <a href="#res:halfmembership" data-reference-type="ref" data-reference="res:halfmembership">13</a>, this is equivalent to the canonical greedy orbit omitting infinitely many exponents. A positive answer would give an infinite support of rational value $`1/2`$ and refute the universal \#257 statement; a negative answer would decide only this distinguished point-membership question.

</div>

<a id="conclusion-what-the-reductions-change."></a>

#### Conclusion: what the reductions change.

The paper is an obstruction atlas: it records finite certificates and local no-go results while converting each problem into an exact after-every-cutoff obligation. The reductions change form, not status. Progress needs a uniform mechanism—such as anti-concentration, cancellation, recurrence, or rigidity—forcing witnesses arbitrarily far out. For \#249 this means unbounded certificate supply, in pointwise or lcm-diagonal form. For the half-value route it means infinitely many terminal zeros, or equivalently no final skip; the values $`-2,-1`$ and a future-tail inequality remain open. A negative half-value answer would not prove universal \#257.

<a id="statements-and-declarations"></a>

## Statements and declarations

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

The [archived formal-source revision](https://github.com/wcook04/plectis-lean-erdos249-257/tree/ebc98ee71f6819bd9fe344a0bb343542c604e533) contains the Lean sources, fixed toolchain, library manifest, and generated certificate data used in the verification. Repository metadata and this manuscript provide navigation rather than proof authority; Section <a href="#sec:verify" data-reference-type="ref" data-reference="sec:verify">7</a> gives the verification route.

<a id="use-of-ai-assistance."></a>

#### Use of AI assistance.

Large-language-model assistants were used during development for proof drafting, refactoring, and prose editing. Every registered formal claim is linked to a declaration in the archived source revision. Lean checks each proof term against the fixed library version; the project contains no proof placeholders or project-defined axioms.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.

<a id="acknowledgements."></a>

#### Acknowledgements.

The problem numbering and status follow the Erdős Problems catalogue maintained by Thomas Bloom \[erdosproblems\].

<a id="app:half-technical"></a>

# Technical reductions for the half-value branch

This appendix records the local arithmetic used to reach Theorems <a href="#res:halfmembership" data-reference-type="ref" data-reference="res:halfmembership">13</a> and <a href="#res:fatalright" data-reference-type="ref" data-reference="res:fatalright">16</a>, Proposition <a href="#res:finalskipexclusions" data-reference-type="ref" data-reference="res:finalskipexclusions">17</a>, and Corollary <a href="#res:taildominance" data-reference-type="ref" data-reference="res:taildominance">18</a>. Its statements have four statuses: exact identities or equivalences; implications with an unproved hypothesis; exact finite calculations; and counterexamples showing that a proposed local argument is insufficient. None changes the two open conclusions at the end of Section <a href="#sec:eb" data-reference-type="ref" data-reference="sec:eb">4</a>. Readers concerned only with the main reductions may skip the appendix.

The parts are ordered by their role in the greedy argument. Appendix <a href="#app:half-localizer" data-reference-type="ref" data-reference="app:half-localizer">[app:half-localizer]</a> computes the residual interval for one take–skip–take pattern, without showing that the half-value orbit enters or avoids it. Appendix <a href="#app:half-conditional-producers" data-reference-type="ref" data-reference="app:half-conditional-producers">9.2</a> gives one conditional irrationality criterion for a structured support, several sufficient hypotheses for $`1/2\in\mathcal A`$, and the local identities they use. Appendix <a href="#app:half-finite-cofinal" data-reference-type="ref" data-reference="app:half-finite-cofinal">9.3</a> separates a finite witness from the unbounded supply of such witnesses needed for membership. Appendix <a href="#app:half-final-skip" data-reference-type="ref" data-reference="app:half-final-skip">9.4</a> identifies nonmembership with a last greedy skip, excludes some possible last transitions, and states the two exceptional carry exclusions and unused-tail inequality still missing. Appendix <a href="#app:half-evidence" data-reference-type="ref" data-reference="app:half-evidence">9.5</a> contains finite checks, changes of coordinates, and counterexamples to shortcuts.

The two routes used below have the logical form
``` math
\begin{array}{rclcl}
\text{unbounded witnesses (\ref{app:half-conditional-producers}--\ref{app:half-finite-cofinal})}
&\Rightarrow& \frac12\in\mathcal A
&\Rightarrow& \text{infinite support summing to }\frac12,\\
\text{exclusions and tail bound (\ref{app:half-final-skip})}
&\Rightarrow& \text{no final skip}
 &\Leftrightarrow& \frac12\in\mathcal A.
\end{array}
```
The displayed implications are proved, and the final equivalence is exact. Both leftmost hypotheses are open. Thus the appendix explains what would suffice and why several finite arguments fail; it does not decide whether $`1/2\in\mathcal A`$.

Throughout this appendix:

- a *take* (respectively a *skip*) at rank $`n`$ is the greedy decision $`\varepsilon_n=1`$ (respectively $`\varepsilon_n=0`$);

- the *finite greedy seam at row $`s`$* is the Boolean word of Definition <a href="#def:terminal-bit" data-reference-type="ref" data-reference="def:terminal-bit">12</a>; an unqualified *seam* in this appendix is an adjacent pair of such words at a branch boundary, and the compounds seam pair, one-hole seam, first-wrap seam, and rewind seam carry this pair sense;

- the *square-root strip* at depth $`N`$ is the carry interval $`[1,H_N]`$ with $`H_N=2\lfloor\sqrt N\rfloor+4`$; an interval of carries kept available by a construction is *protected*;

- a *hole* of a seam is the missing carry value in an otherwise covered protected interval;

- a *rewind* runs the fixed carry recurrence backwards to find earlier carries that can produce a chosen terminal carry;

- the *transition carry* is the integer coordinate appearing in the exact residual identity, and the *remainder* of a row is its integer greedy residual;

- the branches are *upper* (reset to $`G_s^\uparrow`$), *middle* (keep $`G_s`$ and skip $`s`$), and *right* (keep $`G_s`$ and take $`s`$);

- the *pulse* of a rank at row $`s`$ counts its divisor incidences at $`2s+1`$ and $`2s+2`$, the first counting twice; the pulse of a word is the sum over its ranks.

These terms denote mathematical objects, not stages of a proof search. Module-local coordinates not listed here (for example the centred, lazy, or first-wrap variants) are defined in the linked formal statements.

<a id="res:twothirdsband"></a>

## Exact band for a final skip between two takes

<span id="app:half-localizer" label="app:half-localizer"></span>

At rank $`k`$, call the current residual *dyadically safe* when it is at most $`2^{-k}`$, and *unsafe* otherwise. Since the actual Mersenne tail satisfies $`T_k>2^{-k}`$, safety is sufficient but not necessary for survival; an unsafe skip need not stop the orbit.

Suppose a take at rank $`b`$ is followed by the next take at $`c>b+1`$. Put $`q=2^b-1`$, $`m=2^{c-1}`$, and write the residual just before rank $`b`$ as $`r=1/R`$, so $`R`$ is its reciprocal. Taking $`w_b=1/q`$ changes the reciprocal to $`R'=Rq/(q-R)`$, which stays fixed through the intervening skips. The last skip, at rank $`c-1`$, occurs exactly when $`R'>m-1`$ and is dyadically unsafe exactly when $`R'<m`$. For $`0<R<q`$, solving $`m-1<R'<m`$ for the pre-take reciprocal gives
``` math
\frac{q(m-1)}{q+m-1}<R<\frac{qm}{q+m}.
```
The interval has exact width
``` math
\frac{q^2}{(q+m)(q+m-1)}.
```
Formalised: [the general unsafe-band equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfGreedyTwoThirdsBand.lean#L88) and [the general band-width formula](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfGreedyTwoThirdsBand.lean#L104).

For a single intervening skip, $`c=b+2`$ and $`m=2q+2`$. The band becomes
``` math
\frac{q(2q+1)}{3q+1}<R<\frac{2q(q+1)}{3q+2},
```
with width $`q^2/((3q+1)(3q+2))<1/9`$, entirely between $`2q/3`$ and $`2q/3+2/9`$. No integral $`R`$ lies in this window. If instead $`r=p/(2D)`$, then $`R=2D/p`$; for positive odd $`p,D,q`$, clearing denominators in the same inequalities forces $`p\ge7`$. Formalised: [the one-skip band equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfGreedyTwoThirdsBand.lean#L127), [the one-skip width formula](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfGreedyTwoThirdsBand.lean#L154), [the width bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfGreedyTwoThirdsBand.lean#L163), [the integral-reciprocal exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfGreedyTwoThirdsBand.lean#L185), and [the odd-coordinate lower bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfGreedyTwoThirdsBand.lean#L231).

These results neither show that the greedy orbit of $`1/2`$ enters or avoids the band nor identify the remaining transition coordinates $`-2,-1`$ with dyadically unsafe skips.

<a id="app:half-conditional-producers"></a>

## Conditional criteria and local inputs for structured supports

The results here have three distinct roles. The pairwise-coprime dilation criterion is a conditional irrationality theorem for one structured support family. The seam, strip, and terminal criteria are sufficient hypotheses for $`1/2\in\mathcal A`$. The dilation, prime-power, and reverse-carry spacing results are local algebraic inputs that prove neither an irrationality conclusion nor half-membership without an additional supply hypothesis. Nothing in this subsection is a new unconditional case.

<a id="res:sunflower"></a>

### A conditional pairwise-coprime dilation criterion

Write $`A=E\cup\{c_ip_i:i\geq0\}`$, where $`E`$ is a finite set of positive integers and $`Q,c_i,p_i`$ are positive. Suppose that $`Q`$ is divisible by every $`d\in E`$ and every $`c_i`$, while $`p_i>1`$ is coprime to $`Q`$ and to $`p_j`$ for $`j\ne i`$, and $`\sum_i1/p_i<\infty`$. We call this a *finite-core pairwise-coprime dilation family*: $`Q`$ contains the fixed factors and the $`p_i`$ are mutually coprime. Lean includes the example $`E=\varnothing`$, $`Q=6`$, with $`c_i`$ alternating between $`2,3`$ and $`p_i=5^2,7^2,11^2,\ldots`$; each support element has three prime factors with multiplicity.

Put $`f_A(n)=\#\{d\in A:d\mid n\}`$ and $`T_A(M)=\sum_{j\geq1}f_A(M+j)2^{-j}`$. For every $`K\geq1`$, the unproved selector requires some $`N`$ for which $`2^K\mid\sum_{r=1}^K f_A(N+r)2^{K-r}`$ and $`T_A(N+K)\leq16`$. These are the carry divisibility and scaled-tail bounds. Lean proves that they imply the [forced-carry certificate supply](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SupportSunflowerDichotomy.lean#L531) and hence [irrationality of the support series](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SupportSunflowerDichotomy.lean#L540). The selector itself is not proved. This is therefore a conditional reduction for one structured support family, not an unconditional case of Erdős #257.

<a id="res:compositedefect"></a>

### Composite dilation defects

Let $`\Delta_A(a,x)`$ count the $`d\in A`$ such that $`d\mid ax`$, $`d\nmid x`$, and $`d\ne a`$. For $`a\in A`$ and $`a,x>0`$, partitioning the support divisors of $`ax`$ gives $`f_A(ax)=f_A(x)+\mathbf 1_{a\nmid x}+\Delta_A(a,x)`$: [the composite-dilation identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CompositeDilationDefect.lean#L30). For $`A=\{2,6\}`$ and $`(a,x)=(6,1)`$, the additional divisor $`2`$ gives [$`\Delta_A(6,1)=1`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CompositeDilationDefect.lean#L218).

If $`A=E\cup\{c_jp_j:j\geq0\}`$ is such a family and $`a=c_ip_i`$, every divisor counted by $`\Delta_A(a,x)`$ either lies in $`E`$ or equals $`c_jp_j`$ with $`j\ne i`$ and $`p_j\mid x`$. Hence, for $`P=\{p_j:j\geq0\}`$, $`\Delta_A(c_ip_i,x)\leq |E|+f_P(x)`$: [the dilation-family defect bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CompositeDilationDefect.lean#L151). These finite local identities prove neither a correlation estimate, the tail selector, nor irrationality.

<a id="res:mixedlayer"></a>

### Mixed prime-power layers

For $`e\geq1`$ and an integer-valued coefficient $`g`$, put $`L_{p,e}g(n)=g(p^en)-g(p^{e-1}n)`$. This finite difference records the change between the two adjacent $`p`$-power arguments. The operators commute, $`L_{q,f}L_{p,e}=L_{p,e}L_{q,f}`$: [the layer-commutation identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/MaximalOmegaLayer.lean#L29). If $`p\ne q`$ are prime, $`e,f\geq1`$, and $`\gcd(n,pq)=1`$, then, viewing $`f_A`$ as integer-valued, $`L_{q,f}L_{p,e}f_A(n)=f_B(n)`$ for $`B=\{d:\gcd(d,pq)=1,\ p^eq^fd\in A\}`$: [the two-prime layer identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/MaximalOmegaLayer.lean#L39). For $`A=\{12\}`$, $`(p^e,q^f,n)=(4,3,1)`$, and the value is one: [the singleton-support calculation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/MaximalOmegaLayer.lean#L65). These finite identities provide no decimation transport, bounded-$`\Omega`$ conclusion, or irrationality theorem.

<a id="res:halftrapping"></a>

### Rank-one obstruction and reverse-carry spacing

For rational-linear maps $`\varepsilon,\lambda_j:V\to\mathbb Q`$, assume $`\varepsilon(v_0)=1`$ and $`\ker\varepsilon\subseteq\ker\lambda_j`$ for every $`j`$. Each $`\lambda_j`$ is a scalar multiple of $`\varepsilon`$; hence every square matrix $`(\lambda_j(v_i))`$ of size at least two has determinant zero: [the rank-one determinant criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfTrappingReturnCarry.lean#L42). A reverse-carry word consists of integer sequences $`c_m,b_m,u_m`$ satisfying $`b_m+2u_m=c_m+u_{m+1}`$. Two words with a common $`c_m`$ at a seam, bits $`1,0`$ there, and common $`c_m,b_m`$ for the next $`\ell`$ positions have terminal carry difference $`2^\ell z`$ with $`z`$ odd: [the exact carry factorisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfTrappingReturnCarry.lean#L124). If both terminal carries lie in $`[0,B]`$, this forces $`2^\ell\leq B`$: [the dyadic spacing inequality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfTrappingReturnCarry.lean#L191). Neither theorem constructs the two words or an earlier overlap.

<a id="res:halfcarryreachability"></a>

### Half-carry reachability

For a Boolean word $`a`$, set $`f_a(n)=\#\{d:d\mid n,\ a_d=1\}`$, $`K_1=1`$, $`K_n=2K_{n-1}-f_a(n)`$, and $`H_n=2\lfloor\sqrt n\rfloor+4`$. Admissibility through $`N`$ means $`a_0=a_1=0`$ and $`1\leq K_n\leq H_n`$ for $`1\leq n\leq N`$; $`K_N`$ is its terminal carry. At an unresolved half-divisor step to depth $`2d`$, let $`h`$ be the parent carry, $`\delta`$ the last parent that takes the divisor, $`c`$ the remaining coefficient, and $`b\in\{0,1\}`$ the new bit. The child is $`2h-c-1-b`$ when $`h\leq\delta`$ and $`2h-c-b`$ otherwise. Hence $`h,b`$ realise exactly $`k\neq2\delta-c`$: one missing carry and no others ([the exact one-hole equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryReachability.lean#L235)).

A *canonical even seam* is the corresponding adjacent pair of admissible parent words at depth $`2d`$ that realises this one-hole pattern. The unproved supply hypothesis gives one at every $`2d`$, $`d\geq10`$. Choose $`k=1`$, except $`k=2`$ when the hole is $`1`$; this gives words at unbounded depths ([the unbounded-depth admissibility implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryReachability.lean#L999)). Restriction fills earlier depths, and König compactness gives one infinite support of value $`1/2`$ ([the half-value conclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryReachability.lean#L1027)). The seam supply is unproved, so Erdős #257 remains undecided.

<a id="arbitrarily-late-strip-returns."></a>

#### Arbitrarily late strip returns.

Let $`A_g`$ be the canonical greedy support of $`1/2`$, and set $`\Gamma_N=K_{N+1}`$, $`g_N=\Gamma_N/2^N`$, and $`B_N=H_{N+1}/2^N`$. The normalised carry obeys $`g_{N+1}=g_N-f_{A_g}(N+2)/2^{N+1}\leq g_N`$ ([the scaled-carry monotonicity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CofinalStripReturn.lean#L23)), and the proved nonnegativity of $`\Gamma_N-1`$ gives $`g_N\geq0`$; meanwhile $`B_N\to0`$ ([the strip-envelope limit](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CofinalStripReturn.lean#L42)). Such a return means an arbitrarily late $`M`$ with $`g_M\leq B_M`$. For $`\varepsilon>0`$, choose one with $`B_M<\varepsilon`$; then $`0\leq g_N\leq g_M\leq B_M<\varepsilon`$ for $`N\geq M`$, so $`g_N\to0`$. Hence the centred carry $`C_N=\Gamma_N-1`$ satisfies $`C_N/2^N\to0`$, and the tempered-carry theorem gives an infinite greedy support of value $`1/2`$.

<div id="res:cofinalstripreturn" class="proposition">

**Proposition 35** (arbitrarily late strip-return criterion). *Let $`\Gamma_M`$ be the uncentred integer carry of the canonical greedy expansion of $`1/2`$. If
``` math
\forall N\in\mathbb{N}\;\exists M\geq N,\qquad
 \Gamma_M\leq 2\lfloor\sqrt{M+1}\rfloor+4,
```
then $`1/2\in\mathcal A`$, and its canonical greedy support is infinite.*

</div>

Formalised: [scaled-carry decay](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CofinalStripReturn.lean#L84) and [the strip-return membership criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CofinalStripReturn.lean#L157). The arbitrarily late return condition itself is not established. It is weaker than a uniform strip bound and still does not give an unconditional membership theorem.

<a id="terminal-only-unbounded-depth-approximation."></a>

#### Terminal-only unbounded-depth approximation.

A *terminal-only witness* at depth $`M`$ is a Boolean word $`a`$ with $`a_0=a_1=0`$; its earlier carries are unrestricted, while its terminal carry $`K_M`$ satisfies $`|K_M|\leq H_M`$. Put $`A=\{d:a_d=1\}`$, $`X_A=\sum_{d\in A}(2^d-1)^{-1}`$, and $`T_M=\sum_{j\geq1}f_A(M+j)2^{-j}`$. The exact residual identity is $`K_M=2^M(1/2-X_A)+T_M`$. Since both $`|K_M|`$ and $`T_M`$ are at most $`2\sqrt M+4`$,
``` math
\left|X_A-\frac12\right|
 \leq\frac{4\sqrt M+8}{2^M}
 \leq\frac{4M+12}{2^M}.
```
For witnesses at unbounded depths, the last bound tends to zero. Each $`X_A`$ belongs to the closed Mersenne achievement set, so their limit $`1/2`$ also belongs to it. The words at different depths need not agree, and the finite-support obstruction forces the support representing the limit to be infinite.

<div id="res:terminalonlycofinal" class="proposition">

**Proposition 36** (terminal-only unbounded-depth criterion). *Normalised terminal witnesses at unbounded depths in the square-root strip imply that $`1/2`$ belongs to the Mersenne achievement set, and hence that an infinite support has support-series value $`1/2`$.*

</div>

Formalised: [the terminal approximation bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TerminalOnlyCofinal.lean#L68), [the terminal-strip compactness criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TerminalOnlyCofinal.lean#L134), and [the infinite-support conclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TerminalOnlyCofinal.lean#L192). The unbounded-depth terminal-witness supply is not proved. In particular, the proposition does not establish membership of $`1/2`$ unconditionally.

<a id="scaled-terminal-vanishing."></a>

#### Scaled terminal vanishing.

Let $`M_n\to\infty`$, and let $`a^{(n)}`$ be a normalised word of depth $`M_n`$. Write $`A_n`$ for its finite support, $`X_n`$ for its support-series value, and $`K_n`$ for its terminal carry. The carry–tail identity gives
``` math
\left|X_n-\frac12\right|
 \leq \frac{|K_n|}{2^{M_n}}
   +\frac{2\sqrt{M_n}+4}{2^{M_n}}.
```
The second term tends to zero for every such depth sequence. Thus the sole additional hypothesis $`|K_n|/2^{M_n}\to0`$ gives $`X_n\to1/2`$; closedness and the finite-support obstruction give an infinite support of value $`1/2`$. The preceding square-root-strip condition is stronger, since $`|K_n|\leq H_{M_n}`$ and $`H_{M_n}/2^{M_n}\to0`$.

<div id="res:terminalscaledvanishing" class="proposition">

**Proposition 37** (scaled terminal-vanishing criterion). *A normalised terminal-word sequence with depths tending to infinity and vanishing binary-scaled terminal carries yields an infinite support with support-series value $`1/2`$.*

</div>

Formalised: [the scaled terminal error bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TerminalOnlyScaledVanishing.lean#L24), [the scaled-vanishing compactness criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TerminalOnlyScaledVanishing.lean#L165), and [the scaled-vanishing support conclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TerminalOnlyScaledVanishing.lean#L221). No such scaled-vanishing sequence is constructed here; the result is a conditional reduction, not an unconditional membership theorem.

<a id="app:half-finite-cofinal"></a>

## Finite-to-unbounded-depth criteria: windows, seams, and compactness

Every half-value route below has the form “finite witness at depth $`N`$” plus “witnesses at unbounded depths” implies $`1/2\in\mathcal A`$. These are alternative sufficient criteria, not successive stages of one proof. Local identities advance one witness; compactness consumes witnesses at unbounded depths, which no result below proves.

<a id="res:halfcylindershadow"></a>

### Finite residuals for the half-value problem

For admissible depth-$`N`$ word $`a`$, let $`A=\{d:a_d=1\}`$, with terminal carry $`K_N`$ and future tail $`T_N`$. Exactly $`\frac12-X_A=(K_N-T_N)/2^N`$ ([residual identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFiniteShadow.lean#L55)). A first even seam has sole missing carry $`H=2\delta-c`$; hence $`[1,B]`$ is fully reachable iff $`H<1`$ or $`B<H`$ ([seam equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFiniteShadow.lean#L807)). Raw safety is weaker: rank-three $`A=\{2,3\}`$ has residual $`1/42<1/32`$, but its depth-six strip $`[1,8]`$ contains $`H=3`$. After a skip at rank $`k+1`$, freeze the selected support $`A`$ through $`k`$ and let $`K`$ be its centred carry. The sole input is that $`m_0=-K`$, $`m_{J+1}=2m_J+f_A(k+J+2)`$ reaches $`m_J\geq0`$ for some $`J\leq k+1`$; the first $`J`$ future rows then cover $`K`$. This unproved hypothesis implies $`1/2`$-membership ([half-membership](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFiniteShadow.lean#L1256)), but the hypothesis is not proved here.

<a id="res:fixedcoeffrewind"></a>

### Fixed-coefficient rewind

With fixed coefficient $`c`$, rewinding carry $`k`$ gives the parent $`T_c(k)=\lfloor(k+c+1)/2\rfloor=\lceil(k+c)/2\rceil`$. For a list $`\mathbf c`$ of $`L`$ rows, write $`R_{\mathbf c}`$ for their composition, $`O_{\mathbf c}`$ for its accumulated offset, and $`D=2^L`$. Then $`R_{\mathbf c}(k)=\lfloor(k+O_{\mathbf c})/D\rfloor`$ ([rewind closed form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryCeilParentContraction.lean#L49)). Put $`\theta=(1+O_{\mathbf c})\bmod D`$. If $`1\leq B\leq D`$, every target in $`[1,B]`$ has one common ancestor exactly when $`\theta+B-1<D`$ ([phase-fit equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryCeilParentContraction.lean#L99)). Otherwise the endpoints differ by one and every target maps to one of those adjacent ancestors ([singleton-or-seam dichotomy](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryCeilParentContraction.lean#L180)). The width bound does not select the alternative; this finite lemma supplies neither a seam exclusion nor an Erdős #257 conclusion.

<a id="res:selectedhalfwindow"></a>

### Selected half-carry windows

At depth $`N`$, a finite family called a *selected window* of radius $`R`$ assigns each $`k\in[1,R]`$ an admissible Boolean word with terminal carry $`k`$. If such windows exist for every large $`N`$ with $`R\geq1`$, choosing $`k=1`$ gives unbounded-depth witnesses ([the unbounded-depth implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarrySelectedWindow.lean#L831)); compactness then gives an infinite support with sum $`1/2`$ ([half-value conclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarrySelectedWindow.lean#L864)). The unproved input is a coherent one-row history: the representatives either agree on every divisor of $`N+1`$, making the next coefficient common, or the adjacent outcome realises the canonical one-hole seam ([coefficient-or-hole](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarrySelectedWindow.lean#L236)). No such history is supplied at all large depths; hence no unbounded-depth window supply and no proof of Erdős #257 follow.

<a id="res:rewindphase"></a>

### A realised rewind criterion

For a realised carry-one history, list the suffix bits newest first and put $`X=\sum_{j<L}b_j2^j`$, so the newest row is the low bit. With $`D=2^L`$, $`\theta=D-1-X`$ ([suffix-phase identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryRewindPhase.lean#L39)). Thus $`[1,B]`$ rewinds to one ancestor iff $`B-1\leq X`$ ([suffix-coverage equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryRewindPhase.lean#L65)). Equivalently, for frozen-prefix carry $`Z=1+X`$, this is $`B\leq Z`$ ([prefix-carry equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryRewindPhase.lean#L352)). No theorem proves either coverage inequality at all large depths; hence no proof of Erdős #257 follows.

<a id="res:protectedseam"></a>

### Localised protected seams

Here “protected” means only the band $`[3,27]`$, and “realised at $`M`$” means each seam-reachable carry there comes from an admissible word ([protected-seam predicate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryProtectedSeamConsumer.lean#L18)). The hole is $`H=2\delta-c`$; take $`k=4`$ if $`H=3`$, otherwise $`k=3`$. Seams beyond every bound yield witnesses by [unbounded-depth protected-seam implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryProtectedSeamConsumer.lean#L31), and compactness gives [an infinite support summing to $`1/2`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryProtectedSeamConsumer.lean#L53). The unbounded-depth supply is unproved, so Erdős #257 remains open.

<a id="res:cofinalwindowseam"></a>

### Combining the two unbounded-depth half-carry criteria

For every $`N`$, the hypothesis gives an $`M\geq N`$ with a selected window or a realised seam. The window uses carry $`1`$; the seam uses $`4`$ if its hole is $`3`$, otherwise $`3`$. Either gives an admissible word and hence [unbounded-depth admissibility](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryCofinalWindowOrSeamConsumer.lean#L32); compactness then gives [an infinite support summing to $`1/2`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarryCofinalWindowOrSeamConsumer.lean#L58). Branches may alternate. The hypothesis is unproved; Erdős #257 is open.

<a id="res:integergreedy"></a>

### Integer-greedy first-wrap reduction

For $`s\geq3`$, put $`\kappa_s=2^{2s-1}-2^s`$ and $`B_s=2\lfloor\sqrt{2s}\rfloor+4`$. Starting at $`\kappa_s`$, subtract each truncated seam weight in descending order whenever possible; let $`r_s`$ be the final remainder. By the [defect/remainder equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderIntegerGreedy.lean#L654), a positive subset-sum defect at most $`B_s`$ exists exactly when $`1\leq r_s\leq B_s`$. Each weight clears its tail by at least $`2^{s+1}>B_s`$. At a fixed row this is only a finite repackaging, not a stronger membership criterion. The unproved [skipped-rank escape](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFullShellSeamBridge.lean#L687) asks for $`B_s<r_s`$ at every genuine skipped rank; Erdős #257 remains open.

<a id="res:concreteseam"></a>

### Exact finite recurrence for the greedy seam

The finite seam construction realises the adjacent cut, and its next word is the integer-greedy choice: [the seam-word recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderConcreteSeamAdapter.lean#L667). This is a finite recurrence, not the missing escape estimate.

<a id="app:half-final-skip"></a>

## Exact final-skip reduction and its exceptional carries

This subsection alone feeds the main final-skip reduction. It identifies nonmembership with a final skip and membership with terminal zeros beyond every bound, then separates the excluded terminal branches from the unresolved middle carries and comparison with the unused tail. Later formulas only attack those obligations; they add no second conclusion.

<a id="app:fatalright-detail"></a>

### Fatal gaps and eventual right tails

Call the seam eventually right if some $`S\geq5`$ has $`G_{s+1}=G_s\cup\{s\}`$ for every $`s\geq S`$: all later words append `true`. Call a finite prefix $`u`$ through rank $`d`$ a fatal half gap if $`V(u)+T_{d+1}<1/2<V(u)+w_{d+1}`$. Skipping rank $`d+1`$ then falls short even after the full tail, while taking it overshoots, so every continuation misses $`1/2`$.

For the concrete integer seam words, eventual right extension is equivalent to such a gap, [the fatal-gap equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFatalGapRightTail.lean#L781), to nonmembership of $`1/2`$ in the Mersenne achievement set, [the nonmembership equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFatalGapRightTail.lean#L787), and to a final skipped exponent in the real greedy orbit, [the final-skip equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFatalGapRightTail.lean#L802). This classifies the nonmembership branch exactly. It does not decide which branch holds or prove universal Erdős #257.

<a id="the-case-c_d-3."></a>

#### The case $`C_D=-3`$.

At a putative final skip $`D`$, let $`u`$ be the selected prefix and $`B_D=u\cup\{n:n>D\}`$ the *lazy support*: it skips $`D`$, takes every later rank, and has value $`V(u)+T_D<1/2`$. The finite transition carry is $`C_D=4R_{D,D}-P_D-4`$, and the exact swap makes its centred carry $`C_D+3`$ at row $`2D+1`$. For $`C_D=-3`$ this is zero; forced divisor counts at least $`1`$ and $`2`$ in the next rows make it negative at $`2D+3`$, contradicting finite-level nonnegativity below $`1/2`$, [the middle-$`-3`$ exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFinalMiddleCellEscape.lean#L587). Only $`C_D=-3`$ is excluded; $`C_D=-2,-1`$ and the right-tail branch remain open.

<a id="the-case-c_d-2."></a>

#### The case $`C_D=-2`$.

This transition carry is not eliminated. Here its *phase* means the triple of residue classes of the putative last skip $`D`$ modulo $`21`$, $`10`$, and $`13`$. The possible phases are nevertheless sharply constrained. Uniformly for seam rows $`s\ge27`$, the greedy decisions through rank $`26`$ select exactly the ranks
``` math
2,3,6,7,14,20,21,26,
```
by [the exact rank-(26) prefix](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfFinalMiddlePhaseSieve.lean#L1190).

If $`D\ge27`$ has $`C_D=-2`$ and is followed by an all-right suffix, then
``` math
D\bmod21\in\{11,14,17,20\},\qquad D\bmod10\ne8,
 \qquad D\bmod13\ne11,
```
the class $`D\bmod10=7`$ cannot pair with $`D\bmod21=11`$, and the class $`D\bmod13=10`$ cannot pair with $`D\bmod21=11`$. The orbit theorem is [the finite $`C_D=-2`$ sieve](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfFinalMiddlePhaseSieve.lean#L1913). The three moduli are pairwise coprime, so their phase triples correspond to the $`21\cdot10\cdot13=2730`$ residue classes modulo $`2730`$. Exactly $`412`$ survive; this finite count is [the exact survivor count](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfFinalMiddlePhaseSieve.lean#L2050). Thus a hypothetical final $`C_D=-2`$ transition lies in one of $`412`$ classes modulo $`2730`$, a finite necessary condition rather than an exclusion; the $`C_D=-1`$ case is untouched. Even a survivor density tending to zero would not suffice, since nested nonempty residue sets can have a nonempty inverse limit. This route needs an empty finite sieve or an Archimedean contradiction.

<a id="the-two-remaining-inputs."></a>

#### The two remaining inputs.

The criterion requires $`\Theta_D<C_D`$ at every actual middle transition $`D\ge13`$ except $`C_D=-3`$. Since $`\Theta_D\ge0`$, exactly two open tasks remain: exclude $`C_D=-2,-1`$, and prove $`\Theta_D<C_D`$ at every remaining transition with $`C_D\ge0`$. Together they imply half-membership, [unused-tail criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderLastProducerContradiction.lean#L387); a separate square-root lower bound also suffices, [square-root condition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderLastProducerContradiction.lean#L409). Neither input is proved.

A stronger finite hypothesis puts $`g_D=\#G_D`$. Since $`A_D=G_D\cup\{D\}`$ has $`g_D+1`$ elements, $`\Theta_D\le g_D+1`$. Using $`C_D=4R_{D,D}-P_D-4`$, the condition $`g_D+P_D+5<4R_{D,D}`$ is exactly $`g_D+1<C_D`$. At every late middle row it therefore excludes the negative carries and proves tail dominance. This is [the cardinality escape condition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderMiddleCarryLowerBound.lean#L111), and its membership consequence is [the prefix-cardinality criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderMiddleCarryLowerBound.lean#L1503); it follows in turn from $`R_{D,D}\ge D`$ at every late middle row, [row-scale criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderMiddleCarryLowerBound.lean#L1510). Both hypotheses are unproved.

<a id="finite-upper-reset-band-certificates."></a>

#### Finite upper-reset band certificates.

At the upper reset $`G_{d+1}=G_d^\uparrow`$, let $`O_d`$ be the upper overshoot, $`A_d`$ its corresponding divisor pulse, $`Q_d=4O_d+A_d`$, and $`B_{d,j}=2^{d-j+1}`$. For $`13\le d\le30`$ and $`j\le d`$, Lean proves $`B_{d,j}<Q_d`$ or $`Q_d+2(d+j)\le B_{d,j}`$, [the finite upper-reset certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderUpperResetBandCertificates.lean#L78). Thus $`Q_d`$ avoids the danger band $`Q_d\le B_{d,j}<Q_d+2(d+j)`$. For fixed $`d`$, one exact $`R_{d+1,d+1}`$ certifies every $`j`$; no $`d>30`$ is checked, so the global band-escape hypothesis remains open.

<a id="app:halfmembership-detail"></a>

### Positive half-membership classification

The complementary branch has an equally exact seam formulation. Membership of $`1/2`$ in the Mersenne achievement set is equivalent to the occurrence, beyond every bound, of a successor terminal bit equal to zero, [the unbounded terminal-zero equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L126); equivalently, it is equivalent to such terminal zeros at unbounded depths, [the unbounded-depth terminal-zero equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L203). It is also equivalent to integer-seam witnesses at unbounded depths with skipped ranks tending to infinity, [the unbounded skipped-rank equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L213). These equivalences isolate the required unbounded skipped-rank condition; they do not establish that condition.

<a id="res:largestskip"></a>

### Largest skipped ranks

At row $`s`$, let $`d`$ be the largest skipped rank and put $`u=G_s\cap\{2,\ldots,d-1\}`$. Then $`G_s=u\cup\{d+1,\ldots,s-1\}`$. Write $`L=\sum_{e\in G_s}q_{s,e}`$ and $`U=\sum_{e\in u\cup\{d\}}q_{s,e}`$: $`U`$ replaces the filled suffix above $`d`$ by $`d`$. In the late range $`d>2s/3`$ (equivalently $`2s<3d`$), its exact gap is
``` math
3L+\bigl(3\cdot2^{s+1}+2\cdot4^{s-d}+4\bigr)=3U
```
in division-free form, [the exact late-gap identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderLargestSkipGap.lean#L259).

The branch recurrence is separate. An upper or middle step to row $`s+1`$ skips the new rank $`s`$, making it the largest skip; a right step selects $`s`$ and preserves $`d`$: [the terminal largest-skip branch](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderLargestSkipGap.lean#L328) and [right-branch persistence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderLargestSkipGap.lean#L339). Global propagation still requires an upper or middle step whenever $`2s<3d`$ but $`2(s+1)<3d`$ fails. This first-crossing statement is not proved.

<a id="res:boundarypulse"></a>

### Divisor pulses at the largest-skip boundary

For a selected rank $`e`$, its row-$`s`$ pulse counts two if $`e\mid2s+1`$ and one if $`e\mid2s+2`$; the word pulse sums these counts. If $`d`$ is a largest skip with $`2s<3d`$, every filled suffix rank $`d<e<s`$ divides neither new index, so the whole word pulse comes from the selected prefix below $`d`$: [the lower-prefix pulse localisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderBoundaryPulse.lean#L85). At the first crossing $`2s<3d\leq2(s+1)`$, either $`3d=2s+1`$ or $`3d=2s+2`$; the twice- and once-counted alternatives give pulses two and one: [the first-crossing pulse classification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderBoundaryPulse.lean#L150). The required transition-carry estimate remains unproved.

<a id="res:largestskipinduction"></a>

### Largest-skip induction

Assume that for every $`s\geq14`$ and largest skip $`d`$ with $`2s<3d`$, either $`2(s+1)<3d`$ or the step to row $`s+1`$ is upper or middle. This hypothesis is unproved. Lean checks the base $`s=14`$, $`d=13`$ directly, including $`28<39`$, [the row-14 base](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderLargestSkipInduction.lean#L73). Induction with the branch recurrence then gives a late largest skip at every row $`s\geq14`$, [the row-by-row induction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderLargestSkipInduction.lean#L120). Those ranks tend to infinity, so $`1/2`$ belongs to the Mersenne achievement set, [largest-skip membership criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderLargestSkipInduction.lean#L167).

<a id="res:fixedtailsocket"></a>

### The fixed-tail survival criterion

Here $`r_M(1/2)=1/2-\sum_{n\leq M}\varepsilon_n(1/2)w_n`$ is the post-rank-$`M`$ remainder, and $`T_M=\sum_{n>M}w_n`$ is all future mass. An actual skip $`M`$ is final exactly when $`T_M<r_M(1/2)`$: all later mass then falls short, [the final-skip equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFixedTailSocket.lean#L22). Negating gives $`r_M(1/2)\leq T_M`$ for all $`M\in\mathcal S(1/2)`$, [the no-final-skip equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFixedTailSocket.lean#L57); since $`1/2\in\mathcal A`$ exactly when there is no final skip, this is the [membership equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderFixedTailSocket.lean#L73). The equivalence is proved; the orbit inequalities are not.

<a id="res:producercarry"></a>

### Residual identity for the middle-transition support

For the middle-transition coordinates $`A_D,C_D,\Theta_D`$ introduced in Section <a href="#sec:final-skip-reduction" data-reference-type="ref" data-reference="sec:final-skip-reduction">4.6</a>, the generic finite-support theorem reads $`1/2-X_{A_D}=2^{-(2D+2)}(C_D-\Theta_D)`$, [the residual identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderProducerCarrySocket.lean#L27). Since the scale is positive, $`C_D>\Theta_D\iff X_{A_D}<1/2`$ and $`C_D<\Theta_D\iff X_{A_D}>1/2`$, [the below-half equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderProducerCarrySocket.lean#L48) and [the above-half equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderProducerCarrySocket.lean#L78). Tail nonnegativity makes $`C_D<0`$ sufficient for $`X_{A_D}>1/2`$, [the negative-carry corollary](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderProducerCarrySocket.lean#L145). A carry at most $`-8`$ strengthens this to $`1/2+(w_D-T_D)<X_{A_D}`$, [the full-gap corollary](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderProducerCarrySocket.lean#L190). These criteria do not determine $`C_D`$ on actual middle transitions or compare every nonnegative $`C_D`$ with $`\Theta_D`$.

<a id="res:quarterband"></a>

### Quarter-band endpoint cases

At row $`s`$ put $`H=2^{s-1}`$, and let $`R,U,R',p^-,p^+`$ denote the adjacent cut’s remainder, overshoot, successor remainder, and two pulses. Its gap is $`4H`$; on either non-carry branch, failure of $`R'<8H`$ is equivalent to:
``` math
\begin{array}{ll}
 \text{middle:}&\exists k:\ R=H+k,\quad p^-\leq4k<p^-+4,\\
 \text{right:}&\exists k:\ R=3H+k,\quad p^-+4\leq4k,\quad
 4k+16H<4(R+U)+p^+.
 \end{array}
```
[the middle-case equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderQuarterBandEndpoints.lean#L153); and [the right-case equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderQuarterBandEndpoints.lean#L175). The middle-case $`k`$ is unique, [the parameter uniqueness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderQuarterBandEndpoints.lean#L34). These equivalences classify failure but prove no concrete-orbit avoidance.

<a id="res:resetdeficit"></a>

### Right-branch deficit escape

Write $`R_s=R_{s,s}`$ for the final integer remainder. At a largest skip $`d`$ with $`2s<3d`$, a right successor forces the explicit window
``` math
2^{s+1}+4\leq4R_s,\qquad
 12R_s+3\cdot2^{s+1}<
 4\bigl(3\cdot2^{s+1}+2\cdot4^{s-d}+4\bigr)+6(s-2),
```
[the right-branch window](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderResetDeficitEscape.lean#L200). If $`p_s^-`$ is the below pulse, the same branch obeys $`R_{s+1}+2^{s+1}+p_s^-+4=4R_s`$, [the exact recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderResetDeficitEscape.lean#L218). When $`R_s\leq2^s`$, put $`\delta_s=2^s-R_s`$. A right step makes $`\delta_{s+1}\geq4\delta_s`$ while the reference scale only doubles. Consequently, if $`2^s\leq2^k\delta_s`$, some $`t\in[s,s+k]`$ is upper or middle, [the deficit escape bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderResetDeficitEscape.lean#L261). These formulas are proved, but they do not show that the actual orbit avoids the window.

<a id="res:seamproducer"></a>

### Alignment of seam and transition carries

Let $`P`$ omit $`s`$, put $`A=P\cup\{s\}`$, and let $`\delta`$ be its half-carry at row $`2s-2`$. The one carry not reached at this seam is the first-wrap hole $`H=2\delta-f_P(2s)`$. With paired pulse $`\Pi=2f_A(2s+1)+f_A(2s+2)`$, the transition carry is $`C(A,s)=4(H-1)-\Pi`$, [seam–carry alignment](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderSeamProducerAlignment.lean#L24). This aligns $`H-1`$ with the transition carry but supplies no sign, size, or occurrence estimate.

<a id="app:half-evidence"></a>

## Finite evidence, coordinate changes, and eliminated special cases

Nothing here decides an open question. The bases are bounded evidence for A.2–A.3, the coordinate changes translate finite formulations, and the counterexamples rule out shortcuts. Each item must be read through its earlier criterion.

<a id="res:selectedwindowbase"></a>

### A verified initial selected window

At depth $`18`$, twelve checked words cover every terminal carry in $`[1,12]`$ inside the half strip, [the depth-$`18`$ table verification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarrySelectedWindowBase.lean#L79); they define [the depth-$`18`$ selected window](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarrySelectedWindowBase.lean#L129). Their common depth-$`13`$ restriction gives the first next-row certificate, [the depth-$`18`$ divisor-agreement certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCarrySelectedWindowBase.lean#L172). This finite base supplies no windows at unbounded depths.

<a id="res:rewindseambridge"></a>

### Rewind-to-seam equivalence

For a selected depth-$`N`$ window $`W=(a^{(h)})_{1\leq h\leq R}`$, suppose the depth-$`M`$ rewind has adjacent ancestors, denominator $`D`$, and phase $`\phi`$; put $`\delta=D-\phi`$. If $`M\leq N`$, $`(N+1)/2\leq M`$, $`R\leq D`$, and the ancestor coefficients at $`N+1`$ are $`c+1,c`$, then $`f_{a^{(h)}}(N+1)=c+1`$ for $`h\leq\delta`$ and $`c`$ otherwise, [next-row profile](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RewindSeamOperationalBridge.lean#L140). With $`27\leq S\leq2\lfloor\sqrt{N+1}\rfloor+4`$ and $`S+c+1\leq2R`$, [a protected seam occurs at $`N+1`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RewindSeamOperationalBridge.lean#L217). The theorem assumes, rather than proves, every displayed hypothesis.

<a id="selected-suffix-cylinders"></a>

### Selected suffix cylinders

Put
``` math
H_N=2\lfloor\sqrt N\rfloor+4.
```
For a Boolean word $`a=(a_0,\ldots,a_N)`$, let
``` math
f_a(n)=\#\{d\leq N:d\mid n,\ a_d=1\},\qquad
 K_0(a)=1,\qquad K_{r+1}(a)=2K_r(a)-f_a(r+2).
```

<div id="def:selected-suffix-cylinder" class="definition">

**Definition 38** (selected window and suffix cylinder). A *selected window* of depth $`N`$ and radius $`R`$ is a family $`(a^{(k)})_{1\leq k\leq R}`$ of Boolean words with $`a^{(k)}_0=a^{(k)}_1=0`$ such that
``` math
1\leq K_{n-1}(a^{(k)})\leq H_n
 \quad(1\leq n\leq N),
 \qquad K_{N-1}(a^{(k)})=k.
```
For $`M\leq N`$, define the suffix numeral
``` math
\nu_{M,N}(a)=\sum_{j=M+1}^{N}a_j\,2^{N-j}.
```
The window has a *suffix cylinder at cutoff $`M`$ with endpoint $`E`$* if all $`a^{(k)}`$ have the same prefix through $`M`$ and
``` math
\nu_{M,N}(a^{(k)})+k=E
 \qquad(1\leq k\leq R).
```
A *profiled gap stage* permits one missing carry interval $`[g_-,g_+]\subseteq[1,H_N]`$: lower and upper suffix-cylinder families represent $`1,\ldots,g_--1`$ and $`g_++1,\ldots,H_N`$, with independent fixed prefixes through $`M`$. Its upper endpoint $`E_+`$ covers $`H_N`$ and satisfies $`E_+=g_++2^{N-M}`$; prefix adjacency is a separate transition hypothesis.

</div>

Here $`R`$ lists the represented terminal carries $`k`$; $`K_{n-1}`$ is the carry at row $`n`$, bounded by the strip width $`H_n`$. The cutoff $`M`$ separates a shared past from the variable suffix—the shared prefix is why this family is called a cylinder—while $`\nu_{M,N}(a)+k=E`$ makes every representative meet the same endpoint. A full cylinder covers the strip; a profiled gap records its one uncovered interval, with separate fixed pasts below and above it.

The logical roles differ. Depth $`18`$ is checked data. The one-row and gap updates are conditional on their coefficient inequalities; the quarter-band bound is only necessary for swallowing a gap. Only full stages at unbounded depths—not a finite run—imply half-membership.

<div id="res:selectsuffix" class="proposition">

**Proposition 39** (verified base and one-row cylinder update). *The depth-$`18`$ selected window has $`R=12`$ and a suffix cylinder at cutoff $`M=13`$ with endpoint $`E=17`$.*

*More generally, let a depth-$`N`$, radius-$`R`$ selected window $`(a^{(k)})_{1\leq k\leq R}`$ have a suffix cylinder at cutoff $`M\leq N`$ with endpoint $`E`$, where $`1\leq N`$ and $`R\leq E`$. Let $`1\leq R'\leq H_{N+1}`$. If
``` math
f_{a^{(k)}}(N+1)=C\qquad(1\leq k\leq R)
```
and
``` math
R'+C\leq2R,
```
then the radius-$`R'`$ successor remains a suffix cylinder, with endpoint
``` math
E'=2E-C.
```*

</div>

The base and endpoint update are the [depth-$`18`$ cylinder](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SelectedSuffixCylinder.lean#L88) and [endpoint recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SelectedSuffixCylinder.lean#L136).

<div id="res:feedbackdichotomy" class="proposition">

**Proposition 40** (full-cylinder or profiled-gap transition). *Let a full suffix-cylinder stage have depth $`N`$, cutoff $`M`$, with $`1\leq N`$, $`M+1\leq N`$, and
``` math
N+1=2(M+1).
```
At depth $`N+1`$, either a full stage exists at cutoff $`M+1`$, or the exceptional carries form a two-sheet profiled gap stage. If $`27\leq H_{N+1}`$, the residual alternative also realises a protected one-hole seam.*

</div>

Formalised by the [full-cylinder/gap alternative](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SuffixCylinderGlobalProducer.lean#L174) and [two-family gap alternative](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SuffixCylinderInStrip.lean#L665).

<div id="res:profiledgap" class="proposition">

**Proposition 41** (one-row profiled-gap recurrence). *Suppose a profiled gap stage has lower and upper next coefficients $`C_-`$ and $`C_+`$, respectively. If
``` math
\begin{gathered}
 1\leq 2g_- -C_- -1,\qquad C_+\leq2g_+,\\
 2g_- -C_- -1\leq 2g_+ -C_+\leq H_{N+1},\\
 H_{N+1}+C_+\leq2H_N,
\end{gathered}
```
then the stage advances one row with exact child gap
``` math
[g'_-,g'_+]
   =[\,2g_- -C_- -1,\;2g_+ -C_+\,].
```
At a cutoff boundary $`N=2M+1`$, $`M\geq4`$, the lower and upper prefixes acquire the forced bits $`0`$ and $`1`$; their consecutiveness is preserved. Under the displayed child-gap conditions at the next row, this promoted stage therefore advances with coefficients determined by its retained prefixes.*

</div>

Formalised by the [two-coefficient gap recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SuffixCylinderProfiledGap.lean#L124) and [promote and advance](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SuffixCylinderProfiledAutoStep.lean#L110).

<div id="res:cylinderswallow" class="proposition">

**Proposition 42** (two-row full-gap width bound). *Suppose that after a two-row update the child gap has lower endpoint at most $`1`$ and upper endpoint at least $`B`$, so neither tracked sheet supplies a canonical parent for any protected carry $`1,\ldots,B`$. If the lower coefficient pulse is at most the upper pulse plus $`2`$, then
``` math
B\leq4(g_+-g_-+1)+2. \tag{A.1}
```
This is a necessary gap-width condition, not a contradiction.*

</div>

Formalised as the [two-row gap-width bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SuffixCylinderProfiledSwallow.lean#L254).

<div id="res:cofinalcylinder" class="corollary">

**Corollary 43** (unbounded-depth suffix-cylinder criterion). *If full suffix-cylinder stages exist at arbitrarily large depths, then there is an infinite set $`A\subseteq\mathbb{N}_{>0}`$ such that
``` math
\sum_{n\in A}\frac1{2^n-1}=\frac12.
```*

</div>

This is the [positive-support unbounded-depth cylinder criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SuffixCylinderTerminalOnlyBridge.lean#L148).

<a id="status-and-relation-to-prior-work."></a>

#### Status and relation to prior work.

The two transition propositions do not supply their coefficient inequalities, and the finite base does not supply witnesses at unbounded depths as required by Corollary <a href="#res:cofinalcylinder" data-reference-type="ref" data-reference="res:cofinalcylinder">43</a>. The strict-tail achievement-set literature supplies the surrounding Cantor-set geometry \[kovactao, Remark 4.1\], not this finite carry recurrence; the comparison record makes no novelty claim for the recurrence itself.

<a id="res:prefeedback"></a>

### Verified finite suffix-cylinder stages

The finite record has three milestones.

1.  *Depth $`27`$.* Before the cutoff rank first divides a new row, a full selected window exists at every depth from $`18`$ through $`27`$, and the depth-$`27`$ endpoint covers the whole protected strip: [stages through depth $`27`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SelectedSuffixCylinderPreFeedback.lean#L118) and [depth-$`27`$ strip coverage](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SelectedSuffixCylinderPreFeedback.lean#L147).

2.  *Depth $`29`$.* The threshold-stage continuation still covers the strip and has a common suffix cylinder at every cutoff from $`14`$ through $`25`$, while cutoff $`26`$ is explicitly not common: [depth-$`29`$ strip coverage](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SuffixCylinderThreshold.lean#L700) and [cutoff-$`26`$ obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SuffixCylinderThreshold.lean#L806).

3.  *Depth $`52`$.* An independent exact run reaches depth $`51`$ with endpoint $`51{,}327{,}745`$, beyond the next head-bit threshold, and the promoted successor at depth $`52`$ is checked: [depth-$`51`$ threshold margin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SuffixCylinderStage51.lean#L536) and [depth-$`52`$ terminal-strip witness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SuffixCylinderTerminalOnlyBridge.lean#L118).

These are finite milestones, not an unbounded induction; they do not provide the arbitrarily large stages required by Corollary <a href="#res:cofinalcylinder" data-reference-type="ref" data-reference="res:cofinalcylinder">43</a>.

<a id="res:halfdivisordrop"></a>

### Half-divisor unit drop

Here the terminal half-divisor bit selects whether the row coefficient is $`C`$ or $`C+1`$. Since the carry update is $`K'=2K-C`$, switching that bit from $`0`$ to $`1`$ drops the successor carry by exactly one: [the terminal-bit unit-drop identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfDivisorUnitDrop.lean#L20). An explicitly identified adjacent boundary pair packages the same one-unit split at a shared cutoff, [the boundary-pair unit-drop identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfDivisorUnitDrop.lean#L35). The inverse-parent recurrence transfers such a pair to the next protected seam while retaining the exact unit-drop witness, [the rewind unit-drop transfer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RewindHalfDivisorAdapter.lean#L86) and [the protected-seam transfer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RewindHalfDivisorAdapter.lean#L147). This is the local coefficient input for the rewind-seam profile, not a global construction of such boundary pairs.

<a id="res:rewindboundarycounterexample"></a>

### A finite rewind-boundary obstruction

The next example separates numerical seam data from the structural boundary predicate. A concrete depth-$`26`$ two-word window has, at depth $`27`$, rewind history $`[1]`$, a width-two seam, and the doubled-row identity, yet no depth-$`13`$ half-divisor boundary-pair witness: [the depth-$`27`$ boundary-pair counterexample](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RewindBoundaryPairCounterexample.lean#L169). Thus the protected-window buffer in the compactness criterion is a genuine hypothesis, not a consequence of the scalar seam facts alone.

<a id="res:producercarrycoordinates"></a>

### Explicit carry coordinates at the final non-right transition

At an adjacent cut, the *below* and *above* row words are the neighbouring subset sums immediately below and above the target. Their unsigned distances from it are the remainder and overshoot; their pulses record the paired divisor-incidence contribution of the next two rows. After adjoining the terminal rank $`s\ge5`$, the below support has transition carry
``` math
4\,\mathrm{remainder}-\mathrm{belowPulse}-4,
```
whereas the above support has transition carry
``` math
-\bigl(4\,\mathrm{overshoot}+\mathrm{abovePulse}+4\bigr).
```
The generic row-word identity is [row-word transition identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderProducerLowerBound.lean#L105), with the below and above specialisations at [middle-coordinate identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderProducerLowerBound.lean#L150) and [upper-coordinate identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/HalfCylinderProducerLowerBound.lean#L183). Thus the upper carry is negative, while the middle sign depends on the competition between remainder and pulse. The identities supply no uniform exponential lower bound, sign persistence at unbounded ranks, or universal escape mechanism.

<a id="res:campbellboundary"></a>

### Incompatibility with Campbell’s prime-progression bound

Crandall asked whether the binary block $`11`$ occurs infinitely often in the Erdős–Borwein constant \[crandall\]. Campbell’s 2026 preprint proves this affirmatively \[campbell\], using a Chinese-remainder construction and a prime-progression estimate of Alford–Granville–Pomerance \[alfordgranvillepomerance\]. Campbell chooses exponent $`\delta=1/4`$: at prime-search height $`X`$, the progression modulus $`d`$ must satisfy $`d\le X^{1/4}`$, equivalently $`d^4\le X`$.

For the proposed last-skip synchronization, $`P`$ is the fatal window’s prime cap, $`t`$ its unavoidable phase period, and $`d`$ the combined progression modulus. The window gives $`P\le4t`$, while absorbing the period requires $`t\le d`$. Taking $`X=P`$, the four requirements $`2\le d`$, $`t\le d`$, $`P\le4t`$, and $`d^4\le P`$ are inconsistent. Formalised: [the period-freeze incompatibility](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CampbellShiftSynchronization.lean#L299) and [the parameter incompatibility](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CampbellShiftSynchronization.lean#L320).

The associated shifted-zero condition is guarded by a putative last skip: it requires every such endpoint to violate its own dyadic cylinder. It is therefore exactly equivalent both to infinitely many actual greedy skips and to $`1/2\in\mathcal A`$: [the shifted-zero/skip equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CampbellShiftSynchronization.lean#L471) and [the shifted-zero/half-membership equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CampbellShiftSynchronization.lean#L488). It is an endpoint restatement, not an independent Campbell input, and does not decide half-membership.

<a id="appendix-consequence."></a>

#### Appendix consequence.

This appendix supplies the local implications behind Theorems <a href="#res:halfmembership" data-reference-type="ref" data-reference="res:halfmembership">13</a> and <a href="#res:fatalright" data-reference-type="ref" data-reference="res:fatalright">16</a>, Proposition <a href="#res:finalskipexclusions" data-reference-type="ref" data-reference="res:finalskipexclusions">17</a>, and Corollary <a href="#res:taildominance" data-reference-type="ref" data-reference="res:taildominance">18</a>. It does not establish the corollary’s global hypothesis. One sufficient route is a window, seam, or terminal approximation at unbounded depths producing $`1/2\in\mathcal A`$. A second route requires both an exclusion of every actual middle transition with $`C_D=-2,-1`$ and a proof of $`\Theta_D<C_D`$ at every remaining non-$`(-3)`$ middle transition. The bounded checks and local no-go theorems provide neither route.

<a id="sec:carry"></a>

# Auxiliary rationality criteria from binary carry systems

This appendix supplies the general results assembled in Theorem <a href="#res:rigidity-main" data-reference-type="ref" data-reference="res:rigidity-main">6</a> and Corollaries <a href="#res:rigidity-unbounded-main" data-reference-type="ref" data-reference="res:rigidity-unbounded-main">7</a>–<a href="#res:rigidity-dyadic-mass-main" data-reference-type="ref" data-reference="res:rigidity-dyadic-mass-main">10</a>, and the detailed greedy geometry cited after Theorem <a href="#res:greedy" data-reference-type="ref" data-reference="res:greedy">5</a>. Readers interested only in achievement-set geometry may skip to Appendix <a href="#app:carry-geometry" data-reference-type="ref" data-reference="app:carry-geometry">10.5</a>. It has two independent roles. Appendix <a href="#app:carry-normal-form" data-reference-type="ref" data-reference="app:carry-normal-form">10.1</a> gives the first exact coordinate change: rationality is equivalent to a *tempered tail orbit*, an integer recurrence with a vanishing boundary condition. Appendix <a href="#app:carry-boolean" data-reference-type="ref" data-reference="app:carry-boolean">10.2</a> gives the second: the orbit becomes a Boolean–Möbius certificate whose quotient stream reconstructs a Boolean support. Appendices <a href="#app:carry-sublog" data-reference-type="ref" data-reference="app:carry-sublog">10.3</a> and <a href="#app:carry-mass" data-reference-type="ref" data-reference="app:carry-mass">10.4</a> use those coordinates only forward, to derive necessary divisor-coverage, denominator-wrap, reciprocal-mass, and carry-growth conditions. A *wrap* occurs when doubling a least residue crosses its odd modulus; the reciprocal mass is $`\rho(A)=\sum_{a\in A}1/a`$.

Appendix <a href="#app:carry-geometry" data-reference-type="ref" data-reference="app:carry-geometry">10.5</a> is separate. It studies the achievement set itself: a finite nonmembership certificate proves exclusion, whereas survival through a finite depth proves nothing. The following display records these statuses before introducing the detailed coordinates.

The dependency chain is
``` math
\begin{array}{rcl}
 \text{a rational support value}
 &\Longleftrightarrow& \text{a tempered integral tail orbit}
 \quad\text{(\ref{app:carry-normal-form})},\\
 \text{a nonempty support with value \(p/q\)}
 &\Longleftrightarrow& \text{a Boolean--M\"obius carry certificate}
 \quad\text{(\ref{app:carry-boolean})},\\
 \text{a nonempty rational support}
 &\Longrightarrow& \text{sublogarithmic zero gaps}\quad\text{(\ref{app:carry-sublog})},\\
 \substack{\text{a nonempty rational support}\\
 \text{with odd denominator part }v>1}
 &\Longrightarrow& \text{wrap and reciprocal-mass bounds}
 \quad\text{(\ref{app:carry-mass})},\\
 \text{an infinite rational support}
 &\Longrightarrow& \text{unbounded carry states}
 \quad\text{(\ref{app:carry-mass})},\\
 \substack{\text{an infinite rational support}\\
 \text{with dyadic denominator}}
 &\Longrightarrow& \text{the reciprocal-mass alternative}
 \quad\text{(\ref{app:carry-mass}).}
\end{array}
```
The last four lines list independent necessary conditions, at the weakest hypotheses under which they are proved, not converses and not contradictions. Appendix <a href="#app:carry-geometry" data-reference-type="ref" data-reference="app:carry-geometry">10.5</a> is orthogonal to this rationality chain: finite greedy failure proves nonmembership in the achievement set, whereas survival through any finite depth proves nothing.

The prior-art boundary is theorem-family-specific. The integral carry recurrence has a direct antecedent in Wang \[wang2026, Section 3\]; the strict-tail geometry is recorded by Kovač–Tao \[kovactao, Remark 4.1\]; Möbius inversion, repetend algebra, and divisor averaging are classical (see, for example, Apostol \[apostol\]). We make no claim of mathematical priority for the converse/rigidity, certificate-normal-form, or coupled reciprocal-mass/collision statements collected here.

<a id="app:carry-normal-form"></a>

## Exact normal form: tail-orbit rigidity

This subsection supplies the generic equivalence used in Appendix <a href="#app:carry-boolean" data-reference-type="ref" data-reference="app:carry-boolean">10.2</a>. It converts rationality into an integer recurrence with a boundary condition; it does not itself exclude such an orbit or impose the Boolean support constraint.

For a coefficient sequence $`\gamma:\mathbb{N}\to\mathbb{N}`$ with $`\gamma(n)\le n`$, write
``` math
X_\gamma=\sum_{n\ge1}\frac{\gamma(n)}{2^n},
\qquad
T_\gamma(N)=\sum_{j\ge1}\frac{\gamma(N+j)}{2^j},
```
the series and its scaled tail after $`N`$ binary digits. Call an integer sequence $`u`$ a *tempered orbit* for $`\gamma`$ with multiplier $`v\ge1`$ if
``` math
u(N+1)=2\,u(N)-v\,\gamma(N+1)\ \text{ for all } N,
\qquad\text{and}\qquad
u(N)/2^N\to0 .
```
The recurrence is exact binary long division against the coefficient stream; the boundary condition forbids the homogeneous solution. Wang uses the integral carry recurrence forced by rationality for the weighted binary special case $`\gamma(n)=n d_n`$ \[wang2026, Section 3\]. The theorem below applies that forward mechanism to arbitrary nonnegative $`\gamma(n)\le n`$ and also proves the converse and subexponential-orbit rigidity. No historical-priority claim is made for those clauses. Wang’s positive-density theorem and its Erdős \#260 corollary are not used or formalised here.

<div id="res:rigidity" class="theorem">

**Theorem 44** (tail-orbit rigidity). *Let $`\gamma(n)\le n`$ for all $`n`$. Every tempered orbit is the scaled tail, $`u(N)=v\,T_\gamma(N)`$ for all $`N`$; and $`X_\gamma`$ is rational if and only if a tempered orbit exists for some multiplier $`v\ge1`$.*

</div>

Formalised: [the scaled-tail orbit identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GenericTailOrbitRigidity.lean#L338) (rigidity) and [the rationality–orbit equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GenericTailOrbitRigidity.lean#L425) (the criterion), restated in Mathlib’s irrationality vocabulary at [the non-irrationality–orbit equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GenericTailOrbitRigidity.lean#L434). The engine is one observation: a real orbit with $`d(N+1)=2\,d(N)`$ and $`d(N)=o(2^N)`$ vanishes identically ([zero-tail rigidity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GenericTailOrbitRigidity.lean#L314)).

The tempered boundary is essential: the homogeneous parasite $`N\mapsto2^N`$ can be added to any orbit without disturbing the recurrence, so positivity of an orbit certifies nothing by itself, and positivity is nowhere advertised as an equivalent criterion. The linear-growth hypothesis covers both constants introduced in Section <a href="#sec:intro" data-reference-type="ref" data-reference="sec:intro">1</a>: $`\varphi(n)\le n`$ for the \#249 coefficients, and $`f_A(n)\le\tau(n)\le n`$ for the \#257 support coefficients $`f_A(n)=\#\{a\in A:a\mid n\}`$. The results below instantiate the criterion on supports. Its separate totient carry-rank consequence belongs to the \#249 rank route in Appendix <a href="#app:totient-rank" data-reference-type="ref" data-reference="app:totient-rank">11.4</a>.

<a id="app:carry-boolean"></a>

## Exact \#257 coordinates: Boolean–Möbius carry certificates

This subsection has one preliminary boundary result and then one exact equivalence chain. The boundary result rules out extracting the desired Boolean support directly from the signs in $`L(\mu)=1/2`$; it is not a premise of the carry equivalence that follows.

<div id="res:mobiussignnogo" class="proposition">

**Proposition 45** (Möbius-sign support no-go). *Let
``` math
A_-=\{d\ge2:\mu(d)=-1\},
 \qquad A_+=\{d\ge2:\mu(d)=1\}.
```
Then
``` math
\sum_{d\in A_-}\frac1{2^d-1}
 =\frac12+\sum_{d\in A_+}\frac1{2^d-1}
 \ge\frac12+\frac1{63}>\frac12.
```
In particular, the signed identity $`L(\mu)=1/2`$ cannot be converted into a Boolean support of value $`1/2`$ merely by selecting the negative Möbius indices.*

</div>

Formalised: [the negative-Möbius decomposition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/MobiusSignSupportNoGo.lean#L111) and [the strict lower bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/MobiusSignSupportNoGo.lean#L150). The term $`d=6`$ supplies the displayed $`1/63`$. This rules out one sign-truncation route only; it does not exclude another infinite Boolean support with value $`1/2`$.

<a id="the-exact-coordinate-chain."></a>

#### The exact coordinate chain.

At base $`2`$ the support series of Section <a href="#sec:eb" data-reference-type="ref" data-reference="sec:eb">4</a> is itself a binary coefficient series, $`\sum_{n\in A}1/(2^n-1)=X_{f_A}`$ ([the support-series/binary-series identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/BooleanMobiusCarry.lean#L376)). Boolean Möbius inversion first identifies the support from its divisor coefficients; tail-orbit rigidity then identifies rationality with a tempered integer orbit. Theorem <a href="#res:carrycert" data-reference-type="ref" data-reference="res:carrycert">47</a> is exactly the composition of those two equivalences. The divisor transform and Möbius inversion are classical Lambert-series tools \[apostol; merca2017; mercaschmidt\]; the composition with the tempered-orbit criterion is what is checked here.

<div id="res:boolmob" class="proposition">

**Proposition 46** (Boolean Möbius inversion, both directions). *On positive integers, $`f_A=\mathbf 1_A*\mathbf 1`$ and $`\mu*f_A=\mathbf 1_A`$, where $`\mathbf 1_A`$ is the indicator of $`A`$. Conversely, every integer-valued arithmetic function $`f`$ whose Möbius transform is Boolean, $`(\mu*f)(n)\in\{0,1\}`$ for all $`n\ge1`$, satisfies $`f=f_B`$ for the support $`B=\{n\ge1:(\mu*f)(n)=1\}`$ selected by that transform.*

</div>

Formalised: [the positive-support divisor identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/BooleanMobiusCarry.lean#L76), [the Möbius inversion identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/BooleanMobiusCarry.lean#L94), and, with no search or finiteness hypothesis, the converse [the Boolean reconstruction theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/BooleanMobiusCarry.lean#L180).

On the carry side, Theorem <a href="#res:rigidity" data-reference-type="ref" data-reference="res:rigidity">44</a> applies at $`\gamma=f_A`$. The support series is rational exactly when a tempered carry orbit for $`f_A`$ exists ([the rationality–carry equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/BooleanMobiusCarry.lean#L383)). A displayed fraction $`p/q`$ corresponds to an orbit $`U`$ with multiplier $`q`$ and initial value $`U(0)=p`$ ([the support-fraction carry equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/BooleanMobiusCarry.lean#L466)). Exact division then recovers the coefficient from the orbit, $`\bigl(2U(N)-U(N+1)\bigr)/q=f_A(N+1)`$ ([carry-quotient recovery](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/BooleanMobiusCarry.lean#L680)). The elementary divisor-pair bound $`\tau(n)\le2\lfloor\sqrt n\rfloor`$ confines the tails to a square-root strip, $`T_{f_A}(N)\le2\sqrt N+4`$. For a nonempty support the orbit states are positive and satisfy $`U(N)\le q\,(2\sqrt N+4)`$ ([the carry upper bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/BooleanMobiusCarry.lean#L705)); and the strip is strong enough to re-derive the tempered boundary, so the analytic side condition can be traded for one inequality. The two coordinate changes compose.

<div id="res:carrycert" class="theorem">

**Theorem 47** (support fraction–Boolean-carry equivalence). *Fix $`p\in\mathbb Z`$ and an integer $`q\ge1`$. There is a nonempty support $`A`$ of positive integers with $`\sum_{n\in A}1/(2^n-1)=p/q`$ if and only if there is an integer sequence $`U`$, with $`U(0)=p`$, such that, for every $`N`$,
``` math
0<U(N)\le q\,(2\sqrt N+4)
  \qquad\text{and}\qquad
  q\mid 2U(N)-U(N+1),
```
and the Möbius transform of the quotient sequence $`N\mapsto\bigl(2U(N)-U(N+1)\bigr)/q`$ is Boolean. The support is not guessed: it is reconstructed from the certificate by Proposition <a href="#res:boolmob" data-reference-type="ref" data-reference="res:boolmob">46</a>.*

</div>

Formalised as [the normalised support-fraction certificate equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/BooleanMobiusCarry.lean#L948).

<div class="example">

**Example 48** (the support $`\{2,3\}`$). The support $`\{2,3\}`$ has value $`\tfrac13+\tfrac17=\tfrac{10}{21}`$ ([the two-point series value](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/BooleanMobiusCarry.lean#L1054)), its orbit is the pure period-six cycle $`10,20,19,17,13,26`$ with multiplier $`21`$ ([the tempered two-point orbit](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/BooleanMobiusCarry.lean#L1103)), and the Möbius transform of the carry quotient recovers exactly $`\{2,3\}`$ ([support recovery](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/BooleanMobiusCarry.lean#L1140)).

</div>

These are coordinates, not by themselves a strategy: nothing here excludes infinite Boolean carry paths, and no finite search is promoted to a completeness argument.

<a id="app:carry-sublog"></a>

## Necessary condition I: sublogarithmic divisor coverage

This theorem is a one-way consequence of a rational support value and is used in Corollary <a href="#res:rigidity-sublog-main" data-reference-type="ref" data-reference="res:rigidity-sublog-main">8</a>. It limits zero gaps in the divisor-coefficient stream; it neither reconstructs a support nor contradicts the existence of an infinite rational support.

The coefficient $`f_A(n)`$ counts the elements of $`A`$ dividing $`n`$. Say that a zero window of length $`h`$ starts after $`c+N`$ when $`f_A(c+N+j+1)=0`$ for every $`0\le j<h`$. Thus no integer in that interval is divisible by an element of the support.

<div id="res:sublog" class="theorem">

**Theorem 49** (sublogarithmic zero windows). *Let $`A`$ contain a positive integer and suppose
``` math
\sum_{a\in A}\frac1{2^a-1}=\frac{p}{2^c v},
  \qquad p\in\mathbb{Z},\quad c\in\mathbb{N},\quad v\ge1.
```
For every $`\varepsilon>0`$ there is a constant $`B\ge0`$, depending only on $`\varepsilon,c,`$ and $`v`$, such that every zero window after $`c+N`$ satisfies
``` math
h\le \varepsilon\log_2(N+1)+B,
  \qquad \log_2 x:=\frac{\log x}{\log 2}.
```
The bound is uniform in $`A,p,N,`$ and $`h`$.*

</div>

Formalised: [sublogarithmic zero-window bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SublogDivisorCoverage.lean#L392).

The proof uses $`k`$ as a tunable moment parameter. For each integer $`k\ge2`$ it first establishes the explicit divisor estimate
``` math
\tau(n)^k\le \bigl(k^{2^k}\bigr)^k n.
```
It transports the resulting $`n^{1/k}`$ bound through the binary tail and then uses the exact carry recurrence across a zero window. Raising the resulting inequality to the $`k`$th power absorbs the occurrence of $`h`$ on the right and leaves a coefficient $`1/(k-1)`$ in front of the binary logarithm; only then is $`k`$ chosen large enough for $`\varepsilon`$. This controls gaps in divisor coverage; it does not assert a subpower bound for the carry state itself.

For one fixed support the conclusion is elementary, since every zero window is shorter than the least support element. The content is uniformity: $`B`$ does not depend on $`A`$, and taking $`N=0`$ shows that a rational value with denominator data $`(c,v)`$ bounds the least element of its support in terms of $`(\varepsilon,c,v)`$ alone. Against the half-value fibre the constraint is inert: the greedy candidate support there contains $`2`$, so its divisor stream has no zero window of length above one and satisfies the bound with room to spare.

<a id="app:carry-mass"></a>

## Necessary conditions II: wraps, mass, and unbounded states

Three routes use the carry recurrence:
``` math
\begin{array}{rcl}
\text{odd denominator}&\longrightarrow&
  \text{doubling-residue wraps}\longrightarrow\text{mass lower bound},\\
\text{finite common multiple}&\longrightarrow&
  \text{recurring excess spikes}\longrightarrow\text{collision correction},\\
\text{infinite support}&\longrightarrow&\text{unbounded carry states}.
\end{array}
```
The first two routes use Cesàro averages when the reciprocal mass is finite; the third needs no summability hypothesis. These are parallel necessary consequences of rationality, not implications from one conclusion to the next. The one-wrap classification identifies the extremal residue cycles and is not a premise of any of the three routes.

Suppose now the support series equals $`p/(2^c v)`$ with $`v`$ odd and $`A`$ containing a positive element. Write $`q=2^cv`$, and let $`U`$ be the tempered orbit of Appendix <a href="#app:carry-boolean" data-reference-type="ref" data-reference="app:carry-boolean">10.2</a> with multiplier $`q`$. Removing the first $`c`$ binary places and the dyadic factor gives the positive integer state
``` math
u(N)=\frac{U(c+N)}{2^c}=v\,T_{f_A}(c+N);
```
this is $`u_N`$ in Theorem <a href="#res:rigidity-main" data-reference-type="ref" data-reference="res:rigidity-main">6</a>, and it satisfies $`u(N+1)+v\,f_A(c+N+1)=2u(N)`$. Its least residue modulo $`v`$ is $`\bar p_N=p2^N\bmod v`$, with $`0\leq\bar p_N<v`$. Put
``` math
e_N=\left\lfloor\frac{u(N)}v\right\rfloor,
 \qquad u(N)=ve_N+\bar p_N;
```
thus $`e_N`$ is the nonnegative integral excess above the least residue ([shifted natural-state existence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L668), [residue–excess decomposition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L506)). Doubling a least residue either stays under $`v`$ or wraps past it exactly once, so each step emits a wrap digit $`k_N=\lfloor2\bar p_N/v\rfloor\in\{0,1\}`$, and over any cycle length $`h`$ with $`2^h\equiv1\pmod v`$ the repetend identity holds:
``` math
\sum_{N<h}\bar p_N \;=\; v\cdot w,
\qquad
w=\sum_{N<h}k_N,
```
with $`w\ge1`$ when $`p`$ is coprime to $`v>1`$. The formal development records the displayed equality as the [wrap-count identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L171) and its non-vanishing as the [positive-wrap theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L181).

<div id="res:onewrap" class="proposition">

**Proposition 50** (one-wrap classification). *Let $`v>1`$ be odd, $`p`$ coprime to $`v`$, and $`h\ge1`$ with $`2^h\equiv1\pmod v`$. If the cycle of $`p`$ wraps exactly once, then $`v=2^h-1`$ and the starting residue is a power of two: $`\bar p_0=2^a`$ for some $`a<h`$.*

</div>

The one-wrap cycles are thus exactly the Mersenne repetends $`2^a/(2^h-1)`$. Formalised: [one-wrap classification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L415), from the generic closed-cycle form [one-wrap cycle classification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L353), and instantiated at the true order $`h=\operatorname{ord}_v(2)`$ ([odd-order one-wrap classification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L478)). The classification is algebraic; a finite check of $`446`$ coprime starting residues across twelve modulus/order rows is retained as kernel-checked validation, not as the proof ([446-start finite validation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L2454)).

The analytic bridge is Cesàro averaging. Write $`\rho(A)=\sum_{a\in A}1/a`$ for the reciprocal mass. When the reciprocal family is summable, the mean of $`f_A(1),\dots,f_A(N)`$ converges to $`\rho(A)`$ — the density of the multiples of $`a`$, summed over the support — and the mean of the scaled tails has the same limit ([divisor-mean limit](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L945), [coefficient-tail mean limit](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L1036)). The divergent case is carried as an explicit disjunction, not through a default value assigned to a divergent formal sum.

<div id="res:orderwrap" class="proposition">

**Proposition 51** (order-wrap lower bound, with exact excess mean). *Let $`A\subseteq\mathbb{N}_{>0}`$ be nonempty and suppose
``` math
X_A=\frac{p}{2^cv},
 \qquad p\in\mathbb{Z},\quad c\in\mathbb{N},\quad v>1\ \text{odd}.
```
Let $`h=\operatorname{ord}_v(2)`$, let $`w`$ be the number of wraps in the least-residue cycle $`p2^N\bmod v`$ for $`0\leq N<h`$, and set
``` math
u(N)=vT_{f_A}(c+N),\qquad e_N=\left\lfloor\frac{u(N)}v\right\rfloor.
```
Then $`\sum_{a\in A}1/a`$ diverges or $`\rho(A)\ge w/h`$; if moreover $`p`$ is coprime to $`v`$, then $`w\ge1`$, so $`\rho(A)\ge1/\operatorname{ord}_v(2)`$. In the summable case the bound is the periodic part of an exact identity: the Cesàro mean of $`e_N`$ converges, and
``` math
\rho(A)\;=\;\frac{w}{h}\;+\;\lim_{N\to\infty}\frac1N\sum_{n<N}e_n .
```*

</div>

The divergent-or-bounded conclusion is formalised by the [wrap-ratio mass alternative](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L1501), its coprime specialisation by the [odd-order mass alternative](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L1517), and the automatic excess limit in the fraction-facing coordinates above by the [shifted excess-mean identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L1577). A rational value thus ties the odd part of its denominator to the sparsity of its support: a summable support with small $`\rho(A)`$ can only display denominators whose odd part has small multiplicative order of $`2`$.

<div id="res:collision" class="corollary">

**Corollary 52** (collision strengthening at common multiples). *In the summable case, let $`F\subseteq A`$ be finite and let $`L\ge1`$ be a common multiple of $`F`$. Then
``` math
\rho(A)\;\ge\;\frac{w}{h}\;+\;\frac{\lceil(|F|-1)/2\rceil}{L}.
```
In particular, an infinite support whose value is a dyadic rational $`p/2^c`$ has $`\sum_{a\in A}1/a`$ divergent or $`\rho(A)>1`$.*

</div>

The mechanism is a collision. At every positive multiple of $`L`$, at least $`|F|`$ support divisors land on the same index, so $`f_A\ge|F|`$ there. The exact carry equation $`f_A(n)+e_n=k_{n-1}+2e_{n-1}`$, with $`k_{n-1}\le1`$, lets one step absorb at most one unit. The preceding excess must therefore spike to at least $`\lceil(|F|-1)/2\rceil`$, and these spikes recur with density $`1/L`$. The three steps are formalised by the [shifted common-multiple bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L1963), [shifted wrap–excess recurrence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L1868), and [dyadic reciprocal-mass alternative](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L2200).

<div id="res:unbounded" class="theorem">

**Theorem 53** (carry states are unbounded over infinite supports). *Let $`A`$ be infinite with value $`p/(2^c v)`$, $`v\ge1`$. Then the positive integer carry state $`u(N)=v\,T_{f_A}(c+N)`$ is unbounded: for every $`B`$ there is an $`N`$ with $`u(N)>B`$.*

</div>

The proof picks $`2B+1`$ positive support elements; at a common multiple $`L`$ of all of them, the local inequality $`1+v\,|F|\le2\,u(L-c-1)`$ pushes the state past $`B`$. The conclusion is the [fraction-facing unbounded-state theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L2377); its local engine is the [support-cardinality state bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/RationalSupportCarrySkeleton.lean#L2228). So a rational value over an infinite support cannot run on a bounded carry alphabet. That rules out finite-state readings of the carry system; it does not decide the problem. Nothing in the constraints above prevents an infinite support from satisfying every one of these constraints. The repetend identities and divisor averages used here are classical. We make no claim of mathematical novelty for the coupled reciprocal-mass bounds, collision strengthening, or global unboundedness statement.

<a id="app:carry-geometry"></a>

## Independent geometry and one-sided nonmembership certificates

Finally, consider the set of all values a base-$`2`$ support series can take. For $`n\ge1`$ put $`w_n=1/(2^n-1)`$, let $`T(n)`$ be the mass strictly after exponent $`n`$, and let
``` math
\mathcal A\;=\;\Bigl\{\,\sum_{n\in A}w_n \;:\; A\subseteq\mathbb{N},\ 0\notin A\Bigr\},
```
the *Mersenne achievement set*, the exponent $`0`$ being normalised away as analytically invisible. Coding by supports of positive exponents is literally the formal support series ([support-value identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L554)). In this language the base-$`2`$ \#257 statement reads: the rational members of $`\mathcal A`$ are exactly the finite subset sums. Nothing below decides that. Kovač and Tao verify, for every fixed integer $`t\ge2`$, that
``` math
\sum_{\ell>n}\frac1{t^\ell-1}<\frac1{t^n-1},
```
and deduce distinct Lambert subsums and a Cantor set \[kovactao, Remark 4.1\]. At $`t=2`$ this is the relevant Lambert-series instance of Kakeya’s classical strict-tail criterion for subsum sets \[kakeya1914\]. What is checked here, beyond that cited geometry, is the greedy criterion, quantitative enclosure, and finite nonmembership certificates. No historical-priority claim is made for those refinements, and they do not settle \#257.

<div id="res:greedy-details" class="theorem">

**Theorem 54** (superincreasing geometry and greedy membership). *For every $`n\ge1`$ the weight dominates the whole tail after it, $`T(n)<w_n`$, with the two-scale gap $`w_n-T(n)=\tfrac23\,4^{-n}+O(8^{-n})`$ and explicit valid $`O`$-constant $`3`$. Consequently, a real $`x`$ belongs to $`\mathcal A`$ exactly when $`x\ge0`$ and every greedy residual of $`x`$ is at most the remaining tail. Normalised support coding is injective; hence each member of $`\mathcal A`$ has a unique support, which the greedy recursion recovers bit by bit.*

</div>

Formalised: [strict-tail inequality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L180), [gap big-O estimate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L473) (explicit bound [explicit gap bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L448)), [greedy survival criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L1445), and [normalised support-value injectivity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L1527), transferred to the kernel series at [normalised support-series injectivity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L1536). The nonnegativity guard in the membership criterion is necessary: without it a negative target would survive every level while lying outside $`\mathcal A`$.

The binary coding also permits the global geometry to be checked directly.

<div id="res:greedytopology" class="proposition">

**Proposition 55** (fat-Cantor geometry). *The achievement set $`\mathcal A`$ is compact, perfect, totally disconnected, and nowhere dense. Its Lebesgue measure is exactly one.*

</div>

Formalised: [measure-one theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L996), [perfectness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L1620), [total disconnectedness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L1636), and [nowhere density](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L1645). Kovač–Tao supply the strict-tail Cantor-set context \[kovactao, Remark 4.1\]. The formalisation records these exact properties without making a novelty or priority claim for them.

<div id="res:death" class="proposition">

**Proposition 56** (exact rational runs and finite nonmembership certificates). *The greedy recursion executed in exact rational arithmetic agrees step by step with the real recursion under casting. For a rational target $`x`$, write $`r_n(x)`$ for its exact rational residual after level $`n`$ and, for a lookahead $`\ell\ge0`$, put
``` math
\widehat T_{n,\ell}
  =\sum_{k=0}^{\ell-1}w_{n+k+1}+2w_{n+\ell+1}\in\mathbb{Q}.
```
The sum is empty when $`\ell=0`$, and always $`T(n)<\widehat T_{n,\ell}`$. Hence the finite inequality $`\widehat T_{n,\ell}\le r_n(x)`$ soundly proves $`x\notin\mathcal A`$; its level-one instance shows $`3/4\notin\mathcal A`$. A rational number already known to lie in $`\mathcal A`$ has computable support bits.*

</div>

Formalised: [rational–real greedy agreement](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L1130), [rational tail-enclosure bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L1692), [finite-certificate soundness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L1726), [three-quarters nonmembership](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L1748), and [rational-member support-bit equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GreedyAchievementSet.lean#L1832). The certificates are one-sided: survival through any finite depth proves nothing about membership, and no decidability of membership in $`\mathcal A`$ is asserted. Neither the global geometry nor the finite nonmembership certificates exclude rational values for either open series.

<a id="appendix-consequence.-1"></a>

#### Appendix consequence.

The transfer to the main text is Theorem <a href="#res:rigidity-main" data-reference-type="ref" data-reference="res:rigidity-main">6</a> followed by the four independent Corollaries <a href="#res:rigidity-unbounded-main" data-reference-type="ref" data-reference="res:rigidity-unbounded-main">7</a>–<a href="#res:rigidity-dyadic-mass-main" data-reference-type="ref" data-reference="res:rigidity-dyadic-mass-main">10</a>. Rationality yields the exact carry recurrence. Any nonempty rational support must satisfy the sublogarithmic divisor-coverage bound. If its denominator has odd part $`v>1`$, it must also satisfy the wrap and mass bounds. If the support is infinite, the carry states are unbounded; at a dyadic denominator, the reciprocal-mass alternative also holds. Appendix <a href="#app:carry-geometry" data-reference-type="ref" data-reference="app:carry-geometry">10.5</a> also supplies the finite nonmembership certificates used in Theorem <a href="#res:greedy" data-reference-type="ref" data-reference="res:greedy">5</a>. What is not proved is that the support attached to either target violates one of these necessary conditions. That contradiction, not another rational normal form, is the missing premise.

<a id="app:totient-technical"></a>

# Technical reductions for the totient-certificate branch

Recall the scaled tail $`R_N=\sum_{m\geq1}\varphi(N+m)/2^m`$. The predicate $`\mathsf{Sep}(h,N,L)`$ retains the first $`L`$ binary places of $`R_{N+h}-R_N`$ and checks, by finite integer arithmetic, that their least residue modulo $`2^L`$ clears the rigorous omitted-tail margins at both $`0`$ and $`2^L`$. Thus $`N`$ is the tail location and $`L`$ the finite certificate depth. At a fixed pair $`(h,N)`$, some $`L`$ succeeds exactly when the difference is non-integral. Irrationality requires the stronger unbounded statement: for every candidate period $`h`$, a certificate must occur after every cutoff. This appendix develops coordinates and finite mechanisms for that statement; it does not prove the required unbounded supply <a href="#eq:unbounded-certificate-supply" data-reference-type="eqref" data-reference="eq:unbounded-certificate-supply">[eq:unbounded-certificate-supply]</a>. Readers following only the exact main reduction may skip the details here. Appendix <a href="#app:totient-normal" data-reference-type="ref" data-reference="app:totient-normal">11.1</a> contains the exact reduction; Appendices <a href="#app:totient-finite" data-reference-type="ref" data-reference="app:totient-finite">11.2</a>–<a href="#app:totient-rank" data-reference-type="ref" data-reference="app:totient-rank">11.4</a> give independent finite mechanisms, candidate inputs and their limits, and dyadic-rank consequences.

The exact chain is
``` math
\begin{array}{rcl}
 R_{N+h}-R_N\notin\mathbb{Z}
 &\Longleftrightarrow&
 \exists L\geq1,\ \mathsf{Sep}(h,N,L),\\
 S\notin\mathbb{Q}
 &\Longleftrightarrow&
 \forall h\geq1\ \forall N_0\ \exists N\geq N_0\ \exists L\geq1,\
 \mathsf{Sep}(h,N,L).
\end{array}
```
Appendix <a href="#app:totient-normal" data-reference-type="ref" data-reference="app:totient-normal">11.1</a> gives exact coordinates for the two lines. Appendix <a href="#app:totient-finite" data-reference-type="ref" data-reference="app:totient-finite">11.2</a> separates fixed-scale mechanisms from conditional implications that assume repetition at unbounded scales. Appendix <a href="#app:totient-boundaries" data-reference-type="ref" data-reference="app:totient-boundaries">11.3</a> records candidate sufficient inputs and rules out several shortcuts. Appendix <a href="#app:totient-rank" data-reference-type="ref" data-reference="app:totient-rank">11.4</a> proves unconditional dyadic rank growth but not the missing implication from rank to the second line. Thus only the normal forms are equivalences; the remaining subsections provide finite results, conditional routes, or boundaries.

<a id="app:totient-normal"></a>

## Exact unbounded-depth normal forms and cone consequences

Put $`M_t=\operatorname{lcm}(1,\ldots,t)`$. This subsection has two routes with different logical status. The cone route starts from a necessary consequence of rationality: for large $`t`$, the tails at the locations $`M_t,2M_t,3M_t,\ldots`$ have one fractional part. A finite joint certificate can contradict this prediction at finitely many locations, but no converse completeness theorem is claimed. The diagonal route instead gives an exact decomposition of $`R_{2M_t}-R_{M_t}`$: integrality is equivalent to one residue-class condition at each $`t`$, and missing that class at unbounded $`t`$ is equivalent to the irrationality of $`S`$.

<a id="cone-flatness-and-completeness."></a>

#### Cone flatness and completeness.

For fixed $`t`$, the *lcm cone* is the sequence $`\{kM_t:k\ge1\}`$. Cone flatness means its tails share one fractional part, as rationality eventually forces.

<div id="res:flat" class="proposition">

**Proposition 57** (cone flatness). *If $`S`$ is rational, then for every sufficiently large $`t`$ there is $`\theta_t\in[0,1)`$ such that the fractional part of the tail $`R_{kM_t}`$ equals $`\theta_t`$ for every $`k\ge1`$.*

</div>

Formalised: [cone flatness under rationality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/LcmConeFlatness.lean#L90).

Proposition <a href="#res:complete" data-reference-type="ref" data-reference="res:complete">22</a> states fixed-parameter certificate completeness, and Theorem <a href="#res:pointwisecomplete" data-reference-type="ref" data-reference="res:pointwisecomplete">23</a> gives its global pointwise form. Their additional role here is cone-level: a joint finite refuter tests several multipliers $`k`$ at once rather than one pair. It refutes the single-fractional-part model that rationality predicts on a finite sample ([common-fraction contradiction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/LcmConeNonflat.lean#L126)). This finite cone predicate is sound in the direction just stated: a certificate produces a non-integral pair and hence contradicts the sampled flatness model. No converse is proved saying that every non-flat finite sample, or every irrational value of $`S`$, must be detected by this joint predicate. It is therefore a refuter, not a complete decision procedure.

<a id="an-exact-target-residue-class."></a>

#### An exact target residue class.

At the lcm scale $`M_t`$, put
``` math
D_t=R_{2M_t}-R_{M_t}.
```
Write the explicitly summed Möbius contribution as the reduced rational $`Q_t=a_t/d_t`$ and call it the *Möbius shadow*. Define the remaining term $`F_t=D_t-Q_t`$ as the *foreign defect*: exactly the omitted divisor-indexed terms. No part of $`D_t`$ is discarded. The *full target* is the residue class of $`-a_t`$ modulo $`d_t`$:
``` math
\mathsf{Hit}(t)
 \quad\Longleftrightarrow\quad
 \exists k\in\mathbb{Z},\qquad d_tF_t=-a_t+d_tk.
```
Thus $`Q_t`$ is the explicit part and $`F_t`$ the exact remainder; $`\mathsf{Hit}(t)`$ asks whether their sum is an integer. Nothing is discarded or assigned a conjectural sign.

<div id="res:pincer" class="proposition">

**Proposition 58** (diagonal integrality as one congruence). *For every $`t`$, $`D_t\in\mathbb{Z}`$ if and only if $`d_tF_t\equiv-a_t\pmod{d_t}`$, that is, if and only if the full target is met.*

</div>

This is the [full-target equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalPincerDecomposition.lean#L215).

<div id="res:fulltargetavoidance" class="corollary">

**Corollary 59** (exact unbounded target-avoidance characterisation). *The following are equivalent:
``` math
\begin{aligned}
 &S\notin\mathbb{Q};\\
 &\forall\,t_0\in\mathbb{N}\ \exists\,t\geq t_0,\qquad
   \neg\mathsf{Hit}(t).
\end{aligned}
```*

</div>

The reverse implication is the [unbounded target-avoidance criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalPincerDecomposition.lean#L290). For the forward implication, Theorem <a href="#res:diag" data-reference-type="ref" data-reference="res:diag">25</a> supplies non-integral diagonal differences at unbounded $`t`$, and Proposition <a href="#res:pincer" data-reference-type="ref" data-reference="res:pincer">58</a> converts each one into a missed full target. Thus the proposition is the fixed-scale equivalence and the corollary is its exact global form. The unbounded avoidance statement remains open.

<a id="app:totient-finite"></a>

## Fixed-scale mechanisms and conditional unbounded implications

This subsection groups alternative fixed-scale mechanisms, not a dependency chain. Enclosure and projected-separation tests are sufficient only: separation forces a missed target, with no converse asserted. Prime-power unit-gap characterisations, divisor-index decompositions, the shadow-denominator formula, and the residue–projection equivalence are exact at fixed parameters but, unless stated, do not characterise target avoidance. Irrationality corollaries assume unproved repetition at unbounded scales. The tabulated rows, primality facts, and diagonal certificates through $`t=64`$ are verified finite instances; none proves <a href="#eq:unbounded-certificate-supply" data-reference-type="eqref" data-reference="eq:unbounded-certificate-supply">[eq:unbounded-certificate-supply]</a>.

<a id="a-one-way-analytic-enclosure."></a>

#### A one-way analytic enclosure.

For $`H\ge1`$, put $`\mathcal D_H=R_{2H}-R_H`$, $`c_H=2^H(2^H-1)`$, and $`\Phi_N=\sum_{0\le n\le N}\varphi(n)2^{N-n}`$. The binary shift identity gives $`\mathcal D_H=c_HS+\Phi_H-\Phi_{2H}`$. Truncate the Möbius-square identity of Proposition <a href="#res:lens" data-reference-type="ref" data-reference="res:lens">84</a> after $`D`$ terms.

<div id="res:squareenclosure" class="proposition">

**Proposition 60** (squared-Mersenne enclosure). *For $`D\ge0`$, the rational centre and its exact error are
``` math
\begin{aligned}
 C_{H,D}&=\Phi_H-\Phi_{2H}
   +c_H\left(\frac12+\sum_{1\le d\le D}
      \frac{\mu(d)}{(2^d-1)^2}\right),\\
 \mathcal D_H-C_{H,D}
   &=c_H\sum_{d>D}\frac{\mu(d)}{(2^d-1)^2}.
 \end{aligned}
```
The second identity is exact, and $`|\mathcal D_H-C_{H,D}|\le4c_H/[3(2^{D+1}-1)^2]`$. Hence separation of $`C_{H,D}`$ from every integer by more than this bound forces $`\mathcal D_H\notin\mathbb{Z}`$ and full-target avoidance. No converse is asserted.*

</div>

Formalised: [squared-Mersenne tail identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SquaredMersenneDiagonalEnclosure.lean#L116) and [Lambert-projected separation criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SquaredMersenneDiagonalEnclosure.lean#L237).

<a id="a-reduced-denominator-finite-predicate."></a>

#### A reduced-denominator finite predicate.

Separately, there is a stricter finite condition for an odd reduced denominator $`u`$. Its predicate $`\mathsf{UnitGap}(u,N,K)`$ asks that every candidate integer in the associated dyadic tail interval be non-coprime to $`u`$. At a prime power $`u=p^e`$, the condition is equivalent to the exact alternative that the interval has no candidate, or that it has one candidate and $`p`$ divides that candidate. Thus such an interval has at most one candidate.

<div id="res:unitgap" class="proposition">

**Proposition 61** (prime-power unit-gap ceiling). *For every prime power $`p^e`$ with $`e>0`$, a $`\mathsf{UnitGap}(p^e,N,K)`$ has candidate count at most one. The instance $`(u,N,K)=(3,3,5)`$ satisfies this predicate, although its corresponding ordinary empty-gap inequality fails.*

</div>

Formalised: [prime-power unit-gap characterisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/PrimitiveWeightCertificate.lean#L54), [prime-power one-candidate bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/PrimitiveWeightCertificate.lean#L111), [three-window unit-gap certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/PrimitiveWeightCertificate.lean#L151), and [three-window ordinary-gap failure](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/PrimitiveWeightCertificate.lean#L157). This is a finite certificate-level strengthening. We do not establish that rationality of $`S`$ supplies these predicates at unbounded parameters.

<a id="verified-finite-certificate-families."></a>

#### Verified finite certificate families.

Four bounded certificate families are machine-checked. Each successful $`\mathsf{Sep}`$ instance is a kernel-checked proof of one stated non-integral tail difference, not a numerical experiment; the joint cone table uses its own sound finite refuter.

<div id="app:deposits-detail" class="example">

**Example 62** (verified finite instances, expanded record). The following are checked by the Lean kernel:

- $`\mathsf{Sep}(h,12,16)`$ for every period $`h\in[1,8]`$;

- finite certificates for every period $`h\in[1,16]`$ at a fixed window;

- diagonal certificates $`\mathsf{Sep}(M_t,M_t,L)`$ at $`t=1`$ and the 27 strict lcm-jump scales through $`64`$, namely
  ``` math
  \begin{aligned}
  t\in\{&1,2,3,4,5,7,8,9,11,13,16,17,19,23,25,27,\\
        &29,31,32,37,41,43,47,49,53,59,61,64\};
  \end{aligned}
  ```

- a tabulated joint cone-vertex certificate.

</div>

The four validation classes are formalised, in order, by the [small-window certificate family](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TotientTailPeriodKiller.lean#L404), [periods through sixteen](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CarrySurvivorExtinction.lean#L574), [28 imported diagonal certificates through scale 64](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalPincerCertificatesT64.lean#L1967), and [joint-nonflatness table](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/LcmConeNonflat.lean#L506). For the first three classes, fixed-parameter completeness converts each successful $`\mathsf{Sep}`$ instance into the stated non-integral tail difference. The fourth uses the separate cone-refuter soundness theorem. None is evidence that certificates occur at unbounded scales.

The first instance is worked in full following Example <a href="#res:deposits" data-reference-type="ref" data-reference="res:deposits">26</a>; its underlying implication is [certificate soundness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TotientTailPeriodKiller.lean#L262). No instance asserts that such differences occur at unbounded scales.

<a id="exact-finite-divisor-index-split-and-sufficient-projection-test."></a>

#### Exact finite divisor-index split and sufficient projection test.

There is a second finite presentation of the same obstruction. For a cutoff $`D`$, split the finite Möbius residue diagonal into the terms indexed by $`d\leq D`$ which divide $`H`$ and the remaining terms. The divisor part is exactly the truncated Möbius shadow, while every retained nondivisor term is explicit. Above the stable cutoff $`2H`$, a finite window of omitted terms is bounded by
``` math
c_H\left(\frac{2}{2^D}+\frac{4}{3\,4^D}\right),
```
where $`c_H`$ is the diagonal coefficient. Thus, if the actual foreign defect agrees with this projection within the displayed bound, and the projected quantity is farther than that bound from every integer, then the full target is missed.

<div id="res:foreignresidue" class="proposition">

**Proposition 63** (finite sufficient test for diagonal nonintegrality). *Let $`F_H^{(D)}`$ be the retained nondivisor projection at cutoff $`D`$, let $`F_H`$ be the actual foreign defect, and let $`Q_H`$ be the scaled explicit divisor shadow. The finite residue diagonal is exactly the sum of $`F_H^{(D)}`$ and its divisor-index complement. For $`2H\leq D`$, put
``` math
B_{H,D}=c_H\left(\frac{2}{2^D}+\frac{4}{3\,4^D}\right).
```
If
``` math
|F_H-F_H^{(D)}|\leq B_{H,D}
 \quad\text{and}\quad
 |Q_H+F_H^{(D)}-z|>B_{H,D}\quad\text{for every }z\in\mathbb{Z},
```
then the full target at height $`H`$ is not attained.*

</div>

Formalised: [foreign–divisor split](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/ActualForeignResidueProjection.lean#L307), [omitted-term bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/ActualForeignResidueProjection.lean#L275), and [projected-separation criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/ActualForeignResidueProjection.lean#L348). The passage from finite windows to the analytic foreign complement, including the corresponding kernel identity, is not supplied here. Nor is an unbounded family of separated projections. Both missing inputs belong to the open certificate-supply problem.

Second, the rational Möbius shadow has an exact reduced denominator. If $`r_t`$ is the square-free kernel of $`M_t`$, $`s_t=M_t/r_t`$, and $`J(r_t)=\prod_{q}(q^2-1)`$ is the odd Jordan scalar, the product running over the odd prime divisors $`q`$ of $`r_t`$, then
``` math
d_t=
 \frac{2^{r_t}-1}
 {\gcd\!\bigl(2^{r_t}-1,\,s_t\lvert J(r_t)\rvert\bigr)}.
```
For $`t\geq5`$, the product of the Mersenne factors $`2^p-1`$ over primes $`t/2<p\leq t`$ divides $`d_t`$; in particular $`d_t\geq2^{\lfloor t/2\rfloor}`$. This is a denominator theorem for $`Q_t`$ only. Cancellation by $`F_t`$ is exactly what the full-target condition retains.

<div id="res:shadowden" class="proposition">

**Proposition 64** (exact denominator of the M"obius shadow). *Let $`r_t`$ be the square-free kernel of $`M_t`$, let $`s_t=M_t/r_t`$, and let $`J(r_t)`$ be the odd Jordan scalar. The reduced denominator $`d_t`$ of the scaled Möbius shadow is
``` math
d_t=
 \frac{2^{r_t}-1}
 {\gcd\!\bigl(2^{r_t}-1,\,s_t\lvert J(r_t)\rvert\bigr)}.
```
If $`t\geq5`$, then
``` math
\prod_{\substack{p\ \mathrm{prime}\\ t/2<p\leq t}}(2^p-1)
 \ \mid\ d_t,
 \qquad d_t\geq2^{\lfloor t/2\rfloor}.
```*

</div>

Formalised: [upper-half Mersenne divisor bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/MersenneShadowDenominatorGrowth.lean#L99) and [exact shadow denominator](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/MersenneShadowDenominatorGrowth.lean#L147).

Finally, a second finite coordinate projects the diagonal difference to an integer and then to binary suffix data. At depth $`L`$, let
``` math
P_L(M)=\sum_{j=0}^{L-1}\varphi(M+1+j)\,2^{L-1-j}
```
be the length-$`L`$ window numerator underlying Definition <a href="#def:totient-certificate" data-reference-type="ref" data-reference="def:totient-certificate">21</a>, and define
``` math
W_{t,L}=P_L(2M_t)-P_L(M_t),\qquad
 \eta_{t,L}=W_{t,L}\bmod 2^L,
```
with the residue chosen in $`[0,2^L)`$. The finite residue certificate is the asymmetric safe interval
``` math
M_t+L+2<\eta_{t,L}<2^L-(2M_t+L+2).
```
The two unequal margins are the tail bounds at the two cone vertices $`M_t`$ and $`2M_t`$; replacing them by a symmetric slogan would lose part of the checked statement.

<div id="res:freshloss" class="corollary">

**Corollary 65** (finite residue projection). *For every $`t,L\in\mathbb{N}`$, the diagonal projection certificate is equivalent to
``` math
M_t+L+2<\eta_{t,L}<2^L-(2M_t+L+2),
```
and either condition forces full-target avoidance at height $`t`$. Consequently,
``` math
\forall t_0\in\mathbb{N}\;\exists t\geq t_0\;\exists L\in\mathbb{N},\qquad
 M_t+L+2<\eta_{t,L}<2^L-(2M_t+L+2)
```
implies that $`S`$ is irrational.*

</div>

Formalised: [residue–projection equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalFreshLossBridge.lean#L61) and [unbounded projection criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalFreshLossBridge.lean#L191). The finite equivalence is only between the residue inequality and the projection certificate. Neither condition is asserted to be necessary for full-target avoidance or for irrationality. The module’s stronger adjacent-suffix hypotheses imply the displayed unbounded supply; they are not additional conclusions of one finite certificate. Finite instances of this implication are proved, but no unbounded projection or suffix supply is established.

<a id="res:t64closure"></a>

#### Primality certificates at changing-lcm scales through $`t=64`$.

A finite family of Lucas certificates proves the primality facts required by the diagonal certificates at every $`t\leq64`$ where $`M_t`$ increases; for example, [representative Lucas primality certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalPincerPrimeCertificates/ClosureT64.lean#L51759). This finite theorem family verifies the required primality inputs only through $`t=64`$.

<a id="res:t64endpoint"></a>

#### The diagonal certificate at $`t=64`$.

Using those primality facts, Lean checks the individual diagonal certificate at $`t=64`$, [scale-64 diagonal certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalPincerCertificateT64Endpoint.lean#L1928). This endpoint is one of the 28 finite diagonal certificates in Example <a href="#res:deposits" data-reference-type="ref" data-reference="res:deposits">26</a>.

<a id="app:totient-boundaries"></a>

## Candidate unbounded inputs and no-go boundaries

This subsection catalogues independent candidate routes, not a proof sequence. Only the three-rank hypothesis is a proposed positive input: if it holds at arbitrarily large power-of-two scales, then $`S`$ is irrational, but that occurrence statement is unproved. The affine, fresh-prime, and one-bit results rewrite exact finite quantities; the zero orbit shows that correction-size bounds alone cannot force the needed escape. The last four results independently exclude particular shortcuts. None supplies the missing unbounded input or rules out the whole strategy.

<a id="res:flexibleoddwindow"></a>

#### Candidate unbounded input: a three-rank odd window.

Fix $`t=2^a`$ and increase the canonical suffix depth by at most one to write it as $`m=2q+1`$. Call a rank *central* when its half-word residue lies between $`4^q/32`$ and $`31\cdot4^q/32`$. Test $`q,q+1,q+2`$; centrality at any one yields the required adjacent-suffix gap condition, [three-rank suffix-gap implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalFlexibleOddWindowSupply.lean#L93). Thus success of this three-rank test for arbitrarily large $`a`$ implies irrationality, [unbounded three-rank criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalFlexibleOddWindowSupply.lean#L136); that supply is not proved.

<a id="res:flexibleoddaffine"></a>

#### Exact affine form and bounded zero-orbit obstruction.

Let $`x_q`$ be the centred half-word residue and put $`e_q=4^q/32`$. Centrality is $`|x_q|\geq e_q`$; under the stated bounds on the next two corrections, the three tests are equivalent to one affine escape disjunction, [three-scale affine equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalFlexibleOddWindowAffine.lean#L236). Yet the generic recurrence $`y_{j+1}=4y_j+c_j`$, started at zero, can satisfy $`|y_j|<4^j e`$ for every $`j`$ even when every $`|c_j|<2e`$, [zero-orbit obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/DiagonalFlexibleOddWindowAffine.lean#L225).

<a id="exact-fresh-prime-deficit-decomposition."></a>

#### Exact fresh-prime deficit decomposition.

The foreign defect from Appendix C.1 has an endpoint split suited to curvature tests. Retain only the prime support already present at $`H`$ in the two endpoints $`H+s`$ and $`2H+s`$, and write the resulting discrepancy from the actual totient as an endpoint deficit, a nonnegative difference attributed to fresh prime support. The actual diagonal increment then equals the old-prime increment plus the lower deficit minus the upper deficit. The second and five-point curvature operators preserve this exact split; the five-point operator has coefficient row $`[-8,4,2,1,1]`$. Consequently, the old curvature margin loses at most the stated adverse weighted deficit.

<div id="res:freshprimedeficit" class="proposition">

**Proposition 66** (fresh-prime deficit decomposition). *The endpoint fresh deficits are nonnegative, give an exact decomposition of the foreign-defect increment, and bound the loss from the old-prime curvature margins.*

</div>

Formalised: [endpoint-deficit nonnegativity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/FreshPrimeDeficitDecomposition.lean#L91), [foreign-increment decomposition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/FreshPrimeDeficitDecomposition.lean#L184), and [adverse-deficit curvature bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/FreshPrimeDeficitDecomposition.lean#L269). This supplies the exact correction term for the finite evaluations. It supplies neither an unbounded deficit bound nor an irrationality criterion.

<a id="exact-one-bit-lifting."></a>

#### Exact one-bit lifting.

The power-of-two signed-margin condition admits a separate exact arithmetic reduction. If a signed difference is already divisible by $`2^k`$, lifting its congruence to $`2^{k+1}`$ is equivalent to evenness of the quotient after division by $`2^k`$. Failure of the lift gives the unique translated residue class. Thus, for integers $`P,N,c`$ with $`P-N=16c`$, one has $`P\equiv N\pmod{32}`$ exactly when $`c`$ is even; otherwise the residue is offset by $`16`$.

<div id="res:powertwobitlift" class="proposition">

**Proposition 67** (one-bit signed-margin lift). *The fifth-bit question after fourth-bit agreement is exactly one cofactor parity test, with the complementary offset class characterising failure.*

</div>

Formalised: [one-bit divisibility lift](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/PowerTwoBitLift.lean#L34), [mod-32 cofactor criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/PowerTwoBitLift.lean#L111), and [offset-16 complement](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/PowerTwoBitLift.lean#L129). The centred-state formulation identifies the signed-margin interval condition with failure of this next lift, subject to its stated correction and margin budget: [centred-lift equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/PowerTwoCenteredBitLift.lean#L121) and [centred mod-32 equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/PowerTwoCenteredBitLift.lean#L159). This is a finite arithmetic equivalence. It does not supply the required cofactors at unbounded scales and gives no irrationality conclusion.

<a id="independent-no-go-parity-is-not-a-margin-certificate."></a>

#### Independent no-go: parity is not a margin certificate.

Proposition <a href="#res:powertwobitlift" data-reference-type="ref" data-reference="res:powertwobitlift">67</a> does not settle the reduced signed-margin interval condition. For a positive even modulus $`m`$ and integral radius parameter $`a`$ with $`16<a<8m-16`$, each parity class contains both a residue inside the interval and one outside it. The same statement applies to a positive power-of-two modulus. Thus even a fifth-bit computation, by itself, cannot decide the required margin condition.

<div id="res:paritysocket" class="proposition">

**Proposition 68** (parity does not decide the reduced margin condition). *Let $`m,a\in\mathbb{Z}`$, with $`m>0`$ even and
``` math
16<a<8m-16,
```
and put
``` math
\mathcal M_{m,a}
 =\{y\in\mathbb{Z}:\exists k\in\mathbb{Z},\ 16|y-km|<a\}.
```
Each parity class contains both a member and a nonmember of $`\mathcal M_{m,a}`$. In particular, the conclusion holds for $`m=2^j`$ whenever $`j\geq1`$.*

</div>

Formalised: [parity obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/Totient827ParitySocketCeiling.lean#L73) and [power-of-two parity obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/Totient827ParitySocketCeiling.lean#L110). The result is structural and proves no signed-margin certificate at any particular scale; it excludes parity as a sufficient standalone criterion.

<a id="independent-no-go-prime-adjunction."></a>

#### Independent no-go: prime adjunction.

One tempting way to seek an unbounded obstruction is to compare the full target at $`H`$, $`pH`$, $`qH`$, and $`pqH`$. The following affine transport law rules out this route before any projection is introduced.

<div id="res:primeadjunction" class="proposition">

**Proposition 69** (prime-adjunction transport collapse). *For every positive $`H`$ and $`k`$, the actual diagonal satisfies
``` math
D_{kH}=Q_k(H)D_H+Z_k(H),
 \qquad Q_k(H)\in\mathbb{N},\quad Z_k(H)\in\mathbb{Z}.
```
Hence integrality at $`H`$ propagates to every multiple, and the four target hits at the prime-adjunction diamond are equivalent to the single hit at its root. The corresponding transport of the complete foreign defect has zero diamond curvature: the two transport compositions around the diamond agree exactly.*

</div>

Formalised: [the prime-adjunction diamond collapse](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/FullTargetPrimeAdjunctionNoGo.lean#L196) and [the foreign-correction flatness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/FullTargetPrimeAdjunctionNoGo.lean#L247). Thus tracking only the explicit shadow cannot create a transport obstruction. A future positive route would need a separately defined projection together with a theorem controlling what that projection discards. This is a proved obstruction to one strategy, not progress on the unbounded-supply proposition.

<div id="res:adelic" class="proposition">

**Proposition 70** (independent no-go: scalar localisation). *Let $`x\in\mathbb{Q}`$ and $`c\in\mathbb{Z}`$. If $`H\mid\operatorname{den}(x)`$ and the reduced denominator of $`cx`$ divides $`H`$, then
``` math
\frac{\operatorname{den}(x)}{H}\mid |c|.
```*

</div>

Formalised: [complementary-denominator divisibility](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/AdelicHeightObstruction.lean#L23) and [scalar-localisation identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/AdelicHeightObstruction.lean#L56). Thus a scalar localisation can move a complementary denominator factor into its coefficient, but cannot erase it. This rules out a scalar-denominator shortcut of that form. It neither proves full-target avoidance nor supplies any certificates, so it gives no irrationality criterion for $`S`$.

<div id="res:squarecrt" class="proposition">

**Proposition 71** (independent no-go: square-CRT correction suppression). *Let $`\mathcal E`$ be a finite family indexed by distinct primes $`p_i`$, with prescribed anchors $`A_i`$ and residues $`a_i`$. There is a bounded common base $`n`$ such that, for each $`i\in\mathcal E`$ and each shift $`h`$ with $`p_i\nmid a_i+h`$, one has
``` math
n=A_i+p_i(a_i+p_i t)\quad\text{and}\quad
 \varphi(n+p_i h-A_i)=(p_i-1)\varphi(a_i+p_i t+h)
```
for a suitable $`t\in\mathbb{N}`$. In particular, if every $`p_i`$ exceeds a fixed horizon $`J`$, the choice $`a_i=0`$ works simultaneously for all $`1\le h\le J`$.*

</div>

Formalised: [finite clean totient family](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SquareCRTCube.lean#L198) and [clean horizon family](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SquareCRTCube.lean#L228). The tested coefficient is a difference of two totient values. Removing the prime-dilation correction does not force it to be nonzero: one checked clean two-step block has both differences zero ([vanishing clean block](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SquareCRTCube.lean#L285)), while another has second difference $`-4`$ ([nonzero clean block](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SquareCRTCube.lean#L303)). Thus the result gives neither an unbounded certificate supply nor an irrationality criterion for $`S`$.

<a id="app:totient-rank"></a>

## Unconditional dyadic rank and the rationality-side carry bound

For a sequence $`a(n)`$, its level-$`j`$ *dyadic sections* are the $`2^j`$ subsequences $`n\mapsto a(2^jn+r)`$, $`0\leq r<2^j`$; the dyadic kernel collects these sections over all $`j`$. This subsection first proves an unconditional rank theorem for the sections of $`\varphi`$. It then shows that rationality of $`S`$ would force similarly large ranks among the sections of one integer carry sequence. No theorem gives the upper bound needed for a contradiction, and a counterexample below shows that rank alone cannot do so. The remaining results are exact finite inputs or obstructions to particular certificate strategies.

<div id="res:dyadictotient" class="theorem">

**Theorem 72** (unconditional dyadic totient-kernel rank). *For every $`e\geq0`$, take the sections $`n\mapsto\varphi(n)`$ and $`n\mapsto\varphi(2n)`$, together with every odd-residue section $`n\mapsto\varphi(2^jn+r)`$ for $`1\leq j\leq e`$. These $`2^e+1`$ functions are linearly independent over $`\mathbb{Q}`$. Consequently, the span of all sections
``` math
n\longmapsto \varphi(2^j n+r),\qquad j\geq0,\quad 0\leq r<2^j,
```
is not finite-dimensional over $`\mathbb{Q}`$.*

</div>

Formalised by the all-level minor construction [CRT–Dirichlet separated minors](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TotientMahlerDefect.lean#L847), the independence theorem [canonical kernel independence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TotientMahlerDefect.lean#L900), the exact rank formula [exact canonical rank](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TotientMahlerDefect.lean#L954), and [infinite full-kernel dimension](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TotientMahlerDefect.lean#L1014). The theorem concerns the coefficient kernel. It does not imply that $`S`$ is irrational.

<a id="relation-to-prior-work.-1"></a>

#### Relation to prior work.

The related qualitative nonregularity is known. In the terminology of Allouche and Shallit, a sequence is $`2`$-regular when the $`\mathbb{Z}`$-module generated by all its dyadic sections is finitely generated \[alloucheshallit, Chapter 16\]. Coons proved that $`\varphi`$ is not $`k`$-regular for any $`k\geq2`$ by comparing the poles of $`\zeta(s-1)/\zeta(s)`$ with the meromorphic continuation available to a regular sequence’s Dirichlet series \[coons2010, Theorem 3.2\]. Theorem <a href="#res:dyadictotient" data-reference-type="ref" data-reference="res:dyadictotient">72</a> instead gives an explicit $`\mathbb{Q}`$-linear statement: the exact rank $`2^e+1`$ at each level, witnessed by a CRT–Dirichlet evaluation minor and checked without analytic continuation. Proposition <a href="#res:carryrank" data-reference-type="ref" data-reference="res:carryrank">73</a> uses exactly this level-by-level form.

<div id="res:carryrank" class="proposition">

**Proposition 73** (carry-section rank forced by rationality). *If $`S`$ were rational, there would be an integer $`v>0`$ and integers $`u(N)`$ such that $`u(N+1)=2u(N)-v\varphi(N+1)`$ and $`u(N)/2^N\to0`$. For every $`e`$, the sections $`n\mapsto u(2^jn+r)`$ with $`1\leq j\leq e`$ would span a space of dimension at least $`2^e-1`$.*

</div>

Formalised: [the carry-kernel rank lower bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TotientCarryKernelRigidity.lean#L211) and [the rationality-to-unbounded-rank implication](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TotientCarryKernelRigidity.lean#L284). The recurrence and limit above define a *tempered carry*. No theorem bounds the section rank of every rationality-supplied tempered carry. The proposition identifies a rationality-side barrier, not an irrationality criterion for $`S`$.

<div class="remark">

*Remark 4* (rank alone cannot decide rationality). The following counterexample is an unformalised observation. The same class of coefficient streams satisfying $`0\leq\gamma(n)\leq n`$ contains rational series whose tempered orbits have infinite-dimensional section span. Choose Boolean values $`a_N\in\{0,1\}`$ with $`a_0=a_1=1`$ whose dyadic sections satisfy no nontrivial rational linear relation, obtained by successively violating the countably many finite relations on disjoint sparse blocks. Set $`u_N=N+a_N`$ and $`\gamma(N+1)=2u_N-u_{N+1}`$. Then $`0\le\gamma(n)\le n`$, the orbit $`u`$ is tempered, and Theorem <a href="#res:rigidity" data-reference-type="ref" data-reference="res:rigidity">44</a> evaluates $`\sum_{n\ge1}\gamma(n)2^{-n}=u_0=1\in\mathbb{Q}`$; yet the sections of $`u`$ span an infinite-dimensional space, because the sections of $`N\mapsto N`$ span only two dimensions. This fixes the shape of the missing ingredient: a route through Proposition <a href="#res:carryrank" data-reference-type="ref" data-reference="res:carryrank">73</a> must couple carry-section rank to the arithmetic size of a totient carry, since dimension alone is compatible with rationality.

</div>

<div id="res:signedmoment" class="proposition">

**Proposition 74** (exact rectangular determinant expansion). *For matrices $`M:\iota\times\kappa\to R`$ and $`N:\kappa\times\iota\to R`$ over a commutative ring, the determinant of $`MN`$ is the sum over all maps $`p:\iota\to\kappa`$ of the determinant of the corresponding selected-column matrix times the diagonal product $`\prod_i N_{p(i),i}`$.*

</div>

This is the [rectangular determinant expansion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SignedQMomentObstruction.lean#L28).

<div id="res:dominantdyadic" class="proposition">

**Proposition 75** (exact dominant-dyadic-term test). *If one selected integer numerator is odd and its dyadic exponent is strictly larger than every other selected exponent, then the common numerator after dyadic denominator clearing is odd and hence nonzero.*

</div>

Formalised by [dominant dyadic parity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SignedQMomentObstruction.lean#L77), and [dominant dyadic nonvanishing](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SignedQMomentObstruction.lean#L95). These are finite algebraic inputs to a signed-moment route. They do not show that any actual totient Hankel determinant is nonzero, and they give no irrationality criterion for $`S`$.

The formal proof also exposes the generic theorem that any supplied separated minor gives the corresponding rank, [separated-minor rank criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TotientMahlerDefect.lean#L101). Propositions <a href="#res:signedmoment" data-reference-type="ref" data-reference="res:signedmoment">74</a> and <a href="#res:dominantdyadic" data-reference-type="ref" data-reference="res:dominantdyadic">75</a> remain useful as possible inputs to other determinant routes, but the totient-kernel minor itself is supplied at every level by Theorem <a href="#res:dyadictotient" data-reference-type="ref" data-reference="res:dyadictotient">72</a>.

<div id="res:evenresidue" class="proposition">

**Proposition 76** (exact even-residue reduction). *If $`r=2^{t+1}s`$ with $`s`$ odd and $`t+1<j`$, then $`\varphi(2^jn+r)=2^t\varphi(2^{j-(t+1)}n+s)`$. Thus every even-residue section is a scalar multiple of an odd-residue section.*

</div>

Formalised as the [even-residue reduction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TotientMahlerDefect.lean#L159). This removes duplicate section rows before the separated minor is constructed.

<div id="res:compressedadjoint" class="proposition">

**Proposition 77** (compressed-adjoint size obstruction). *If positive integers $`Q,v`$ and integers $`A,b`$ satisfy $`QvA=b`$ and $`|b|<Qv`$, then $`A=0`$.*

</div>

Formalised as the [compressed-adjoint contradiction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/TotientMahlerDefect.lean#L1051). Here $`A`$ is the proposed integer obstruction and $`b`$ its boundary error. The proposition does not construct these data.

<div id="res:residualgauge" class="proposition">

**Proposition 78** (column-rescaling obstruction for monomial minors). *Let $`z_j,W_j\ne0`$ and $`M_{ij}=W_jz_j^{e_i}`$. Then $`det M=\det(z_j^{e_i})\prod_jW_j`$, so the column weights preserve determinant nonvanishing. If $`e_i=1`$, choosing $`W_j=z_j^{-1}`$ makes row $`i`$ identically $`1`$. Allowing row-dependent weights $`W_{ij}=z_j^i/z_j^{e_i}`$ reconstructs a consecutive-power matrix whose zeroth row is identically $`1`$.*

</div>

Formalised: [residual-gauge determinant equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/ResidualGaugeObstruction.lean#L55), [locked-reconstruction nonvanishing](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/ResidualGaugeObstruction.lean#L94), and [reconstructed zero row](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/ResidualGaugeObstruction.lean#L145). Thus rank, determinant, or conditioning information alone cannot exclude the target without an arithmetic constraint on the residual weights. Such a coupled criterion remains possible; the proposition gives no irrationality criterion for $`S`$.

<a id="appendix-consequence.-2"></a>

#### Appendix consequence.

Nothing in this appendix strengthens the fixed-parameter completeness of Proposition <a href="#res:complete" data-reference-type="ref" data-reference="res:complete">22</a> into an unbounded supply. Its remaining condition is therefore the still-open quantifier in Theorem <a href="#res:red21" data-reference-type="ref" data-reference="res:red21">24</a>:
``` math
\forall h\geq1\;\forall N_0\;\exists N\geq N_0\;\exists L\geq1,\qquad
 \mathsf{Sep}(h,N,L).
```
The one-scale mechanisms and conditional implications in Appendix <a href="#app:totient-finite" data-reference-type="ref" data-reference="app:totient-finite">11.2</a>, the candidate inputs and no-go boundaries in Appendix <a href="#app:totient-boundaries" data-reference-type="ref" data-reference="app:totient-boundaries">11.3</a>, and the conditional rank routes in Appendix <a href="#app:totient-rank" data-reference-type="ref" data-reference="app:totient-rank">11.4</a> delimit possible approaches to this statement. None provides the required certificates after every cutoff.

<a id="app:lambert-complements"></a>

# Lambert, probability, and finite-algebraic complements

This appendix supplies the extensions cited from the Lambert-series identities in Section <a href="#sec:ladder" data-reference-type="ref" data-reference="sec:ladder">3</a> and from the coprime-pair representation after Proposition <a href="#res:coprime" data-reference-type="ref" data-reference="res:coprime">20</a>. The results proved here are the periodic-weight classifications, finite denominator obstructions, the Möbius-square and squared Lambert identities, and the Stern–Brocot cylinder and continuant laws. These enlarge the two coordinate pictures; they are not additional steps in either open proof.

The three parallel families may be skipped on a first reading. Appendix <a href="#app:lambert-weighted" data-reference-type="ref" data-reference="app:lambert-weighted">[app:lambert-weighted]</a> proves or classifies weighted Lambert series with coefficient inputs different from the open totient input. Appendix <a href="#app:lambert-algebraic" data-reference-type="ref" data-reference="app:lambert-algebraic">12.2</a> gives exact identities and finite algebraic boundaries for the squared and Möbius coordinates. Appendix <a href="#app:lambert-probability" data-reference-type="ref" data-reference="app:lambert-probability">12.3</a> develops unconditional geometry internal to the coprime-pair probability coordinate. No conclusion about a comparison input transfers irrationality to $`S`$, and none of the three families supplies the after-every-cutoff $`\mathsf{Sep}`$ theorem.

<a id="sec:additional-lambert"></a>

## Weighted Lambert comparison families

<span id="app:lambert-weighted" label="app:lambert-weighted"></span>

Put $`L_b(\gamma)=\sum_{a\geq1}\gamma(a)/(b^a-1)`$ ($`b\geq2`$) and $`c_\gamma(n)=\sum_{d\mid n}\gamma(d)`$. Here $`\gamma`$ replaces the defining input $`\alpha=\varphi*\mu`$; none of these comparisons changes $`L_2(\alpha)=S`$.

<a id="sec:periodicweights"></a>

#### Periodic weights.

Eventually periodic means $`\gamma(a+p)=\gamma(a)`$ for all sufficiently large $`a`$ and some $`p\geq1`$; periodic means this holds from $`a=1`$.

<div id="res:periodicnonnegative" class="theorem">

**Theorem 79** (eventually-periodic nonnegative weights). *For every $`b\ge2`$, an eventually-periodic nonnegative rational weight that is not identically zero on its eventual period gives an irrational series.*

</div>

Formalised: [eventually-periodic nonnegative criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L12483). Luca–Tachiya prove more: every nonzero eventually periodic rational weight gives an irrational series for each integer base $`|b|>1`$ \[lucatachiya\].

<div id="res:periodicsigned" class="theorem">

**Theorem 80** (periodic signed-weight dichotomy). *For a periodic integer weight $`\gamma`$, either $`L_b(\gamma)`$ is irrational or $`b^kL_b(\gamma)\in\mathbb{Z}`$ for some $`k\ge0`$. In the rational branch its denominator therefore divides a power of $`b`$; the theorem does not select a branch.*

</div>

Formalised: [periodic signed-weight dichotomy](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L13847).

<div id="res:periodfourobstruction" class="proposition">

**Proposition 81** (period-four example). *For the nonzero period-four weight $`\gamma=1,0,-1,0,\ldots`$, $`c_\gamma(n)=0`$ whenever $`n\equiv3\pmod4`$.*

</div>

Formalised: [period-four coefficient obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L13898). Thus a nonzero input may vanish on a residue class; this obstructs residue-blind nonvanishing, not irrationality, and says nothing about $`\alpha`$.

<a id="app:lambert-algebraic"></a>

## Finite algebraic boundaries and squared-Lambert coordinates

This subsection has three logically distinct parts. Propositions <a href="#res:primitiveindex" data-reference-type="ref" data-reference="res:primitiveindex">82</a> and <a href="#res:mersennetailatoms" data-reference-type="ref" data-reference="res:mersennetailatoms">83</a> give finite denominator-clearing boundaries, not irrationality criteria. Proposition <a href="#res:lens" data-reference-type="ref" data-reference="res:lens">84</a> rewrites $`S`$ exactly. Proposition <a href="#res:gcdmoment" data-reference-type="ref" data-reference="res:gcdmoment">85</a> then compares three squared-denominator transforms; only its constant-weight row has a cited irrationality theorem.

<a id="sec:primitiveindex"></a>

#### Finite denominator-clearing boundaries.

Put $`a_n=(\varphi*\mu)(n)/n`$. Let $`\mathcal P_N`$ be the product of $`4`$, one factor $`p`$ for every odd prime $`p\le N`$, and a second factor $`p`$ when $`p^2\le N`$.

<div id="res:primitiveindex" class="proposition">

**Proposition 82** (finite denominator obstruction). *For $`N\ge4`$, if a positive integer $`D`$ makes $`Da_n`$ integral for every $`1\le n\le N`$, then $`\mathcal P_N\mid D`$. Hence no fixed positive $`D`$ clears every $`a_n`$.*

</div>

Formalised: [two-tier primorial obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/PrimitiveDeterminantLift.lean#L148).

For $`d\ge1`$ and $`N\ge0`$, define the periodic Mersenne atom
``` math
\omega_d(N)=\frac{2^{\,N\bmod d}}{2^d-1}.
```
Its exact carry law is
``` math
2\omega_d(N)-\omega_d(N+1)=\mathbf1_{d\mid N+1}.
```
The indicator is $`1`$ exactly when the binary phase wraps.

<div id="res:mersennetailatoms" class="proposition">

**Proposition 83** (finite Mersenne-atom determinant identity). *Fix $`m\ge1`$, conductors $`d_j\ge1`$, indices $`n_{ij}\ge0`$, and integer column weights $`w_j`$, and set
``` math
W_{ij}=w_j\omega_{d_j}(n_{ij}),
 \qquad U_{ij}=2^{\,n_{ij}\bmod d_j}.
```
Then
``` math
\left(\prod_{j=1}^m(2^{d_j}-1)\right)\det W
 =\left(\prod_{j=1}^m w_j\right)\det U\in\mathbb{Z}.
```
If the integer on the right is nonzero, then the absolute value of the cleared determinant on the left is at least $`1`$.*

</div>

Formalised: [Mersenne-atom carry law](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/MersenneTailAtoms.lean#L28), [determinant-clearing identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/MersenneTailAtoms.lean#L158), and [cleared-determinant lower bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/MersenneTailAtoms.lean#L181). Thus finite denominator clearing recovers an integer determinant, whose absolute value is at least $`1`$ when nonzero. It supplies no sequence of nonzero integers tending to $`0`$, and hence no irrationality criterion for $`S`$.

<div id="res:lens" class="proposition">

**Proposition 84** (Möbius-square identity for $`S`$).
*``` math
S \;=\; \tfrac12 \;+\; \sum_{d\ge1}\frac{\mu(d)}{(2^d-1)^2}.
```*

</div>

Formalised: [Möbius-square identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/CertificateKernel.lean#L18126). Writing $`T=\sum_{d\ge1}\mu(d)/(2^d-1)^2`$, Proposition <a href="#res:coprime" data-reference-type="ref" data-reference="res:coprime">20</a> gives $`T=\Pr(\gcd(X,Y)=1)=S-\tfrac12`$; hence $`S`$ is irrational exactly when $`T`$ is. By contrast, the tail residual $`R_N=2^NS-\sum_{n\le N}\varphi(n)2^{N-n}`$ depends on $`N`$ and is an integer translate of $`2^NS`$. Section <a href="#sec:reduction" data-reference-type="ref" data-reference="sec:reduction">5.3</a> uses its differences to encode rationality; $`R_N`$ is not another name for $`T`$.

<a id="sec:squared"></a>

#### Squared Lambert calculus.

Write $`L^{(2)}(f)=\sum_{d\ge1}f(d)/(2^d-1)^2`$; this notation distinguishes the squared-denominator transform from the ordinary base-two transform $`L_2`$ in Appendix <a href="#app:lambert-weighted" data-reference-type="ref" data-reference="app:lambert-weighted">[app:lambert-weighted]</a>. If $`X,Y`$ are independent and $`\Pr(X=n)=\Pr(Y=n)=2^{-n}`$ for $`n\ge1`$, then $`\Pr(d\mid\gcd(X,Y))=(2^d-1)^{-2}`$. The formal transfer theorem, [squared Lambert transfer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GcdMomentCalculus.lean#L105), therefore gives a divisor calculus for their gcd.

<div id="res:gcdmoment" class="proposition">

**Proposition 85** (squared Lambert identity). *The three weights $`f=\mu,\mathbf 1,\varphi`$ give respectively
``` math
L^{(2)}(\mu)=S-\tfrac12,\qquad
 L^{(2)}(\mathbf 1)=\sum_{n\ge1}\frac{\sigma(n)-\tau(n)}{2^n},\qquad
 L^{(2)}(\varphi)=\sum_{n\ge1}\frac{P(n)-n}{2^n},
```
where $`P`$ is Pillai’s gcd-sum function.*

</div>

The first identity is Proposition <a href="#res:lens" data-reference-type="ref" data-reference="res:lens">84</a>. The other two are formalised as [constant-weight squared-Lambert identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GcdMomentCalculus.lean#L216) and [totient gcd-moment identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GcdMomentCalculus.lean#L235). Write $`\zeta_q(1)=\sum_{n\ge1}q^n/(1-q^n)`$ and $`\zeta_q(2)=\sum_{n\ge1}nq^n/(1-q^n)`$. Postelmans–Van Assche prove that $`1,\zeta_q(1),\zeta_q(2)`$ are linearly independent over $`\mathbb{Q}`$ for $`q=1/p`$ and every integer $`p\ge2`$  \[postelmansvanassche, Theorem 1.3\]. Since $`L^{(2)}(\mathbf1)=\zeta_{1/2}(2)-\zeta_{1/2}(1)`$, their theorem makes the constant-weight value irrational. This cited conclusion is not formalised here and does not transfer to the Möbius row $`L^{(2)}(\mu)=S-\tfrac12`$.

<a id="app:lambert-probability"></a>

## Probability-coordinate geometry: reduced slopes and cylinders

Two measures appear below. The cylinder law uses the reduced-direction mass $`\nu`$, which sums every gcd layer; Proposition <a href="#res:onerunmass" data-reference-type="ref" data-reference="res:onerunmass">89</a> uses only the gcd-one contribution $`2^{-(a+b)}`$. Neither supplies the open certificate theorem.

<a id="reduced-directions-and-cylinder-masses."></a>

#### Reduced directions and cylinder masses.

For the independent fair-coin pair $`X,Y`$ above, divide $`(X,Y)`$ by its gcd. For positive coprime $`a,b`$, put
``` math
\nu(a,b)=\frac1{2^{a+b}-1},
  \qquad
  M(a,b)=\frac1{(2^a-1)(2^b-1)}.
```
The first quantity is the probability that the reduced pair equals $`(a,b)`$. The second is the closed form for the Stern–Brocot cylinder rooted there. The children of $`(u,v)`$ are $`(u+v,v)`$ and $`(u,u+v)`$. Let $`M_d(a,b)`$ sum the node masses $`(2^{u+v}-1)^{-1}`$ over descendants at distance less than $`d`$; thus $`M_0=0`$, and the theorem below proves $`M_d\to M`$.

<div id="res:directionnormalization" class="proposition">

**Proposition 86** (reduced-direction normalisation). *The reduced directions form a probability distribution,
``` math
\sum_{\substack{a,b\ge1\\(a,b)=1}}\nu(a,b)=1.
```*

</div>

This is the [reduced-direction mass one](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GcdMomentCalculus.lean#L349).

<div id="res:sternbrocotcylinders" class="theorem">

**Theorem 87** (Stern–Brocot cylinder recursion and convergence). *At every positive node,
``` math
M(a,b)=\frac1{2^{a+b}-1}+M(a+b,b)+M(a,a+b),
```
and, uniformly in $`a,b`$ and $`d`$,
``` math
0\le M(a,b)-M_d(a,b)
  \le \left(\frac23\right)^d M(a,b).
```
Consequently $`M_d(a,b)\to M(a,b)`$; at the root $`M(1,1)=1`$.*

</div>

Formalised: [cylinder mass recursion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GcdMomentCalculus.lean#L474), [depth-$`d`$ remainder bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GcdMomentCalculus.lean#L525), and [cylinder convergence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/GcdMomentCalculus.lean#L560). The recursion is the elementary rational identity obtained after setting $`A=2^a`$, $`B=2^b`$; the quantitative point is that the two children retain at most two thirds of their parent’s mass.

<a id="run-lengths-and-arithmetic-height."></a>

#### Run lengths and arithmetic height.

A *run* is a maximal consecutive block of the same left or right move. List the $`r`$ positive run lengths as $`n_i=1+e_i`$, newest first, with $`e_i\ge0`$. The starting direction only swaps the two coordinates, so the height depends on these lengths alone. Starting with $`P_\varnothing=(1,1)`$, define
``` math
P_{(n_1,\ldots,n_r)}=(n_1A+B,A)
  \quad\text{when}\quad P_{(n_2,\ldots,n_r)}=(A,B),
  \qquad H(n_1,\ldots,n_r)=P_1+P_2.
```
Thus $`H`$ is the arithmetic height of the primitive pair reached by the word. Let $`F_0=0,F_1=1`$.

<div id="res:sternbrocotruns" class="theorem">

**Theorem 88** (Fibonacci height bound and exact run-length defects). *Every $`r`$-run word satisfies
``` math
H(1+e_1,\ldots,1+e_r)
 \ge F_{r+3}+F_{r+1}\sum_{i=1}^r e_i,
```
and $`H(1,\ldots,1)=F_{r+3}`$. A defect at position $`i\in\{0,\ldots,r-1\}`$ (the newest run is $`i=0`$) has the exact size
``` math
H(\underbrace{1,\ldots,1}_{i},1+e,
   \underbrace{1,\ldots,1}_{r-i-1})
 =F_{r+3}+F_{i+2}F_{r-i+1}e.
```
More generally, the excess over $`F_{r+3}`$ is a polynomial in the $`e_i`$, with nonnegative coefficients and degree at most one in each variable; the linked recursive formula determines every mixed coefficient.*

</div>

Formalised: [Fibonacci height lower bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SternBrocotRunGeometry.lean#L185), [multiaffine run-height formula](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SternBrocotRunGeometry.lean#L263), [aggregate defect lower bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SternBrocotRunGeometry.lean#L343), [one-site defect identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SternBrocotRunGeometry.lean#L413).

<div id="res:onerunmass" class="proposition">

**Proposition 89** (one-run first-layer mass). *The two orientations with one nonempty Stern–Brocot run have total first-layer weight $`1/2`$.*

</div>

This is the [one-run mass](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SternBrocotRunGeometry.lean#L467).

<div id="res:rundenominator" class="proposition">

**Proposition 90** (unit-run exponent sum). *Along the all-unit $`r`$-run, denominator-clearing bookkeeping encounters the Fibonacci exponents $`F_2,\ldots,F_{r+1}`$. Their sum $`E_r=\sum_{j=0}^{r-1}F_{j+2}`$ satisfies $`E_r=F_{r+3}-2`$.*

</div>

This is the [unit-run exponent sum](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ebc98ee71f6819bd9fe344a0bb343542c604e533/Erdos249257/SternBrocotRunGeometry.lean#L491). The sum $`E_r`$ records exponents before any denominator cancellation. This identity does not identify a reduced denominator for a probability mass or for $`S`$.

For arithmetic functions and Möbius inversion we use Apostol \[apostol\]; Merca and Merca–Schmidt treat Lambert-series factorisations  \[merca2017; mercaschmidt\]. Stern supplies the rational enumeration underlying the tree \[stern1858\]; the Postelmans–Van Assche theorem concerns only Appendix <a href="#app:lambert-algebraic" data-reference-type="ref" data-reference="app:lambert-algebraic">12.2</a>’s constant-weight value. The claims here are the linked Lean identities and estimates, not priority for the classical mediant or continuant framework.

<a id="appendix-consequence.-3"></a>

#### Appendix consequence.

The three subsections independently change the Lambert weight, rewrite the squared coordinates, and refine the coprime-pair geometry. None supplies the after-every-cutoff $`\mathsf{Sep}`$ theorem for $`S`$ or decides whether $`1/2\in\mathcal A`$.

<a id="app:index"></a>

# Guide to the formal sources

Each blue phrase opens its Lean declaration at the fixed source revision; the accompanying claim index records its name and status. For bounded rational exclusion, see Theorem <a href="#res:farey" data-reference-type="ref" data-reference="res:farey">19</a>; for the exact \#249 reduction, see Proposition <a href="#res:complete" data-reference-type="ref" data-reference="res:complete">22</a> and Theorems <a href="#res:pointwisecomplete" data-reference-type="ref" data-reference="res:pointwisecomplete">23</a>–<a href="#res:diag" data-reference-type="ref" data-reference="res:diag">25</a>; for the \#257 half-value classification, see Theorems <a href="#res:halfmembership" data-reference-type="ref" data-reference="res:halfmembership">13</a> and <a href="#res:fatalright" data-reference-type="ref" data-reference="res:fatalright">16</a>. Theorem <a href="#res:full" data-reference-type="ref" data-reference="res:full">3</a> is the classical benchmark, and Section <a href="#sec:architecture" data-reference-type="ref" data-reference="sec:architecture">6</a> compares the reductions. Independent structural results, none of which closes either problem, are Theorem <a href="#res:dyadictotient" data-reference-type="ref" data-reference="res:dyadictotient">72</a>, the sublogarithmic zero-window corollary, and Theorems <a href="#res:sternbrocotcylinders" data-reference-type="ref" data-reference="res:sternbrocotcylinders">87</a> and <a href="#res:sternbrocotruns" data-reference-type="ref" data-reference="res:sternbrocotruns">88</a>.

<div class="thebibliography">

99

P. Erdős, [*On arithmetical properties of Lambert series*](https://users.renyi.hu/~p_erdos/1948-04.pdf), J. Indian Math. Soc. (N.S.) **12** (1948), 63–66. P. Erdős, [*On the irrationality of certain series*](https://users.renyi.hu/~p_erdos/1969-09.pdf), Math. Student **36** (1968), 222–226 (issued 1969). P. Erdős and R. L. Graham, [*Old and New Problems and Results in Combinatorial Number Theory*](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf), Monogr. Enseign. Math. 28, Geneva, 1980, pp. 61–62. P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). P. B. Borwein, *On the irrationality of certain series*, Math. Proc. Cambridge Philos. Soc. **112** (1992), no. 1, 141–146, doi:[10.1017/S030500410007081X](https://doi.org/10.1017/S030500410007081X). T. M. Apostol, [*Introduction to Analytic Number Theory*](https://doi.org/10.1007/978-1-4757-5579-4), Springer, 1976. M. Merca, *The Lambert series factorization theorem*, Ramanujan J. **44** (2017), no. 2, 417–435, doi:[10.1007/s11139-016-9856-3](https://doi.org/10.1007/s11139-016-9856-3). M. Merca and M. D. Schmidt, *Generating special arithmetic functions by Lambert series factorizations*, Contrib. Discrete Math. **14** (2019), no. 1, 31–45, doi:[10.55016/ojs/cdm.v14i1.62425](https://doi.org/10.55016/ojs/cdm.v14i1.62425). S. Kakeya, *On the set of partial sums of an infinite series*, Proc. Tokyo Math.-Phys. Soc., 2nd ser. **7** (1914), no. 14, 250–251, doi:[10.11429/ptmps1907.7.14_250](https://doi.org/10.11429/ptmps1907.7.14_250). J. Farey, [*On a curious property of vulgar fractions*](https://doi.org/10.1080/14786441608628487), Philos. Mag. **47** (1816), no. 217, 385–386. M. Stern, [*Ueber eine zahlentheoretische Funktion*](https://doi.org/10.1515/crll.1858.55.193), J. Reine Angew. Math. **55** (1858), 193–220. J.-P. Allouche and J. Shallit, *Automatic Sequences: Theory, Applications, Generalizations*, Cambridge Univ. Press, 2003, doi:[10.1017/CBO9780511546563](https://doi.org/10.1017/CBO9780511546563). M. Coons, *(Non)automaticity of number theoretic functions*, J. Théor. Nombres Bordeaux **22** (2010), no. 2, 339–352, doi:[10.5802/jtnb.718](https://doi.org/10.5802/jtnb.718). Yu. V. Nesterenko, *Modular functions and transcendence questions*, Sb. Math. **187** (1996), no. 9, 1319–1348, doi:[10.1070/SM1996v187n09ABEH000158](https://doi.org/10.1070/SM1996v187n09ABEH000158). K. Postelmans and W. Van Assche, [*Irrationality of $`\zeta_q(1)`$ and $`\zeta_q(2)`$*](https://arxiv.org/abs/math/0604312v1), J. Number Theory **126** (2007), no. 1, 119–154, doi:[10.1016/j.jnt.2006.11.011](https://doi.org/10.1016/j.jnt.2006.11.011). F. Luca and Y. Tachiya, *Irrationality of Lambert series associated with a periodic sequence*, Int. J. Number Theory **10** (2014), no. 3, 623–636, doi:[10.1142/S1793042113501121](https://doi.org/10.1142/S1793042113501121). V. Kovač and T. Tao, [*On several irrationality problems for Ahmes series*](https://arxiv.org/abs/2406.17593v4), Acta Math. Hungar. **175** (2025), no. 2, 572–608, doi:[10.1007/s10474-025-01528-0](https://doi.org/10.1007/s10474-025-01528-0). H. Wang, [*Positive dyadic density for rational weighted binary expansions*](https://arxiv.org/abs/2606.24972v2), arXiv:2606.24972v2 (revised 15 July 2026), doi:[10.48550/arXiv.2606.24972](https://doi.org/10.48550/arXiv.2606.24972). R. Crandall, *The googol-th bit of the Erdős–Borwein constant*, Integers **12** (2012), no. 5, 811–840, doi:[10.1515/integers-2012-0007](https://doi.org/10.1515/integers-2012-0007). J. M. Campbell, [*On the binary digits of the Erdős–Borwein constant*](https://arxiv.org/abs/2605.24160v1), arXiv:2605.24160v1 (22 May 2026), doi:[10.48550/arXiv.2605.24160](https://doi.org/10.48550/arXiv.2605.24160). W. R. Alford, A. Granville, and C. Pomerance, *There are infinitely many Carmichael numbers*, Ann. of Math. (2) **139** (1994), no. 3, 703–722, doi:[10.2307/2118576](https://doi.org/10.2307/2118576). T. Tao and J. Teräväinen, [*Quantitative correlations and some problems on prime factors of consecutive integers*](https://arxiv.org/abs/2512.01739v2), arXiv:2512.01739v2 (revised 25 April 2026), doi:[10.48550/arXiv.2512.01739](https://doi.org/10.48550/arXiv.2512.01739). L. de Moura, S. Kong, J. Avigad, F. van Doorn, and J. von Raumer, *The Lean theorem prover (system description)*, in *CADE-25*, LNCS 9195 (2015), 378–388, doi:[10.1007/978-3-319-21401-6_26](https://doi.org/10.1007/978-3-319-21401-6_26). The mathlib Community, *The Lean mathematical library*, in *CPP 2020*, ACM, 2020, 367–381, doi:[10.1145/3372885.3373824](https://doi.org/10.1145/3372885.3373824). T. F. Bloom, [*Erdős Problem \#249*](https://www.erdosproblems.com/249) and [*Erdős Problem \#257*](https://www.erdosproblems.com/257), accessed 19 July 2026.

</div>

[^1]: Luca–Tachiya prove the broader eventual-periodic rational-coefficient theorem; its indicator specialisation directly contains case (e) \[lucatachiya\]. Their Chowla–Erdős-style large-modulus proof is distinct from the periodic-divisor certificate route formalised here, and the full mixed-sign coefficient theorem is not claimed.
