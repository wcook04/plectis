<a id="erdos-251-prime-gap-dyadic-series"></a>

# A Countermodel for Growth-and-Parity Arguments on the Prime-Gap Dyadic Series

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

The positive even word $`a_n=2(n^2+4n+2)`$ has complete dyadic tails $`U_N=2(N+4)^2`$ and rational sum $`\sum_{j\ge1}a_j2^{-j}=32`$. Its unbounded, nonperiodic coefficients therefore coexist with integral shifts at every pair of indices. A sparse rationalising perturbation of the actual prime gaps preserves every fixed eventual congruence of both gaps and cumulative sums, together with the empirical distributions of all unnormalised gap blocks of length $`o(\log\log X)`$. Its corrections can be bounded by $`(\log n)^\varepsilon`$ for any $`0<\varepsilon<1`$. We identify the actual complete prime-gap tails and classify rationality by integrality of their shifts. Two adjacent shifts in $`(-1,1)`$ with unequal associated gaps cannot both be integral. Their joint occurrence cofinally for every positive shift would prove irrationality of the prime series; this prime-specific assertion remains unproved.

There is an exact finite obstruction recorded in the pinned source: a second example has finite sum $`-n/2^n`$ and non-eventually-periodic coefficients ([finite endpoint](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1157); [coefficient nonperiodicity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1163)). The actual prime gaps are also not eventually periodic ([prime-gap nonperiodicity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1023)), but that fact alone is insufficient.

<a id="sec:problem"></a>

# Introduction

<a id="the-complete-countermodel-in-one-calculation."></a>

#### The complete countermodel in one calculation.

Set $`a_n=2(n^2+4n+2)`$ and $`U_N=2(N+4)^2`$. Since $`2U_N-U_{N+1}=a_{N+1}`$, finite telescoping gives
``` math
\sum_{j=1}^{m}\frac{a_{N+j}}{2^j}
   =U_N-\frac{U_{N+m}}{2^m}\longrightarrow U_N.
```
Thus $`U_N`$ is the actual infinite tail, not merely a solution of its recurrence, and the sum at $`N=0`$ is $`32`$. Moreover
``` math
a_{n+1}-a_n=4n+10,\qquad
 U_{N+h}-U_N=2h(2N+h+8)\in\mathbb{Z}.
```
These positive even coefficients grow polynomially and are unbounded and nonperiodic, but every tail difference is integral. The unshifted normalisation $`\sum_{n\ge0}a_n2^{-(n+1)}`$ is $`18`$. Proposition <a href="#res:polynomialcountermodel" data-reference-type="ref" data-reference="res:polynomialcountermodel">5</a> states the resulting obstruction.

<a id="preserving-more-of-the-actual-gaps."></a>

#### Preserving more of the actual gaps.

The quadratic example has the wrong cumulative growth to imitate the primes. A different construction addresses that limitation. If $`A=\sum_{n\ge0}a_n2^{-(n+1)}`$ converges, fix $`M\ge1`$ and a cutoff $`K`$, and choose a rational $`r\in(A,A+M2^{-K})`$. Write
``` math
\frac{2^K(r-A)}{M}=\sum_{j\ge0}\frac{\delta_j}{2^{j+1}},
 \qquad \delta_j\in\{0,1\}.
```
Set $`b_n=a_n`$ for $`n<K`$ and $`b_{K+j}=a_{K+j}+M\delta_j`$. Then $`\sum_{n\ge0}b_n2^{-(n+1)}=r`$. Every coefficient retains its residue modulo $`M`$ and changes by at most $`M`$; each cumulative sum changes by at most $`Mn`$. Applied to prime gaps, this retains the cumulative $`n\log n`$ scale. Taking $`M`$ even retains parity as well. Thus a bounded residue-preserving perturbation can have a rational value without sharing the polynomial example’s growth. Neither construction asserts that its cumulative sums are prime.

<a id="sparse-corrections-and-local-information."></a>

#### Sparse corrections and local information.

The following construction preserves congruences of cumulative sums as well as coefficients. Its sparse support also preserves the empirical laws of short gap blocks.

<div id="res:sparserationalisation" class="proposition">

**Proposition 1** (sparse congruence-preserving rationalisation). *Let $`a_n`$ be nonnegative integers with $`\sum_{n\ge0}a_n2^{-(n+1)}=A<\infty`$, let $`K\in\mathbb{N}`$, and let $`f:\mathbb{N}\to\mathbb{R}`$ tend to $`+\infty`$. There exist a set $`S\subseteq[K,\infty)`$ of upper Banach density zero and a nondegenerate interval $`I\subset(A,\infty)`$ such that every $`r\in I`$ is realised by a nonnegative correction $`e`$ supported on $`S`$, with $`0\le e_n\le f(n)`$ eventually, $`\sum(a_n+e_n)2^{-(n+1)}=r`$, and every fixed modulus eventually dividing both $`e_n`$ and $`\sum_{i<n}e_i`$. For the actual prime gaps and every $`0<\varepsilon<1`$ the same construction may be taken with $`e_n\le(\log(n+3))^\varepsilon`$ eventually and $`|S\cap[X,2X)|=O_\varepsilon(X/\log\log X)`$, so that all unnormalised blocks of length $`o(\log\log X)`$ are preserved in total variation.*

</div>

<div class="proof">

*Construction.* At selected centres $`n_j`$, choose a free digit $`0\le d_j\le D_j`$ and put $`e_{n_j}=M_jd_j`$, $`e_{n_j+1}=M_j(D_j-d_j)`$. The two identities
``` math
e_{n_j}+e_{n_j+1}=M_jD_j,\qquad
 \frac{e_{n_j}}{2^{n_j+1}}+\frac{e_{n_j+1}}{2^{n_j+2}}
   =\frac{M_j(D_j+d_j)}{2^{n_j+2}}
```
separate the cumulative correction from its weighted value. If $`C_j`$ is the preceding cumulative correction, a buffer $`c_j=(-C_j)\bmod M_j`$ makes the new cumulative sum divisible by $`M_j`$. The divisibility chain $`M_{j-1}\mid M_j`$ ensures that earlier congruences remain valid. With $`w_j=M_j2^{-n_j-2}`$ and $`D_j=2^{n_j-n_{j-1}}-1`$ for $`j\ge1`$, telescoping gives
``` math
w_j\le\sum_{i>j}D_iw_i.
```
The allowed digits therefore have overlapping continuation intervals. Greedy selection keeps the remainder between zero and the remaining capacity, which tends to zero, and fills an interval of complete sums. The centres may be delayed to keep the corrections below $`f`$ while their spacing tends to infinity. For the polylogarithmic bound the spacing is comparable to $`\log\log n`$. At most $`m`$ starting blocks of length $`m`$ meet one changed coefficient, so the total variation error is $`O_\varepsilon(m/\log\log X)`$ for $`m=o(\log\log X)`$. The full schedule and endpoint estimates are given in the companion sparse-rationalisation proof. ◻

</div>

Every bounded test of these blocks has the same asymptotic empirical average. A density-zero witness family can lie inside the changed blocks, so its occurrence is not implied by this preservation statement. The reconstructed positions retain their congruences and cumulative growth; they are not asserted to be prime.

<a id="the-prime-series-and-its-tails."></a>

#### The prime series and its tails.

Index the primes from zero: $`p_0=2`$, $`p_1=3`$, and $`g_n=p_{n+1}-p_n`$. In this notation Erdős Problem #251 asks whether
``` math
\Pi=\sum_{n\ge0}\frac{p_n}{2^{n+1}}
 \quad\text{is irrational}.
```
This is the usual one-based series $`2/2+3/4+5/8+\cdots`$. The first gaps are $`1,2,2,4,2,4,2,4,6,2`$; only $`g_0`$ is odd. Let $`G=\sum_{n\ge0}g_n2^{-(n+1)}`$. The exact identities are
``` math
\Pi=2+G,\qquad
 T_N=\sum_{j\ge1}\frac{g_{N+j}}{2^j},\qquad
 T_0=2G-1,\qquad T_{N+1}=2T_N-g_{N+1}.
```
Convergence and the identification of these actual tails are established below. They are not additional assumptions under a hypothetical rational value of $`\Pi`$.

<a id="what-remains-to-be-distinguished."></a>

#### What remains to be distinguished.

For any integer-digit recurrence, iteration gives
``` math
T_N=2^NT_0-B_N,\qquad
 T_{N+h}-T_N=2^N(2^h-1)T_0-C_{N,h},
 \qquad B_N,C_{N,h}\in\mathbb{Z}.
```
A rational initial value forces an eventual integral shift; an irrational initial value permits no integral positive shift. This is the arithmetic reason for the lcm-diagonal criterion in Theorem <a href="#res:lcmdiagonal" data-reference-type="ref" data-reference="res:lcmdiagonal">2</a>. A more local sufficient condition uses two adjacent shift values in $`(-1,1)`$ and a nonzero associated gap difference. If both values were integral they would be zero, contradicting their recurrence. The missing input is their joint occurrence at arbitrarily late indices for every positive shift. The countermodels show why several coarse hypotheses do not supply it.

<a id="relation-to-prior-work."></a>

#### Relation to prior work.

Erdős stated the fixed-denominator question in his work on irrational series \[erdos1958, p. 94\]\[erdosgraham1980, p. 62\] \[erdos1988, p. 103\]. His irrationality result for prime numerators with factorial denominators does not apply to this dyadic denominator sequence. Kovač’s counterexample to a related variable-denominator expectation likewise does not decide the fixed-denominator problem \[kovac2026\]. An adjacent dyadic theorem of Erdős and Pomerance concerns bounded digits recording comparisons of the largest prime factors of consecutive integers \[erdospomerance1978, §7\]; our prime numerators and gaps are unbounded. The detailed historical comparisons and their hypotheses belong to the companion reasoning record. No priority claim is made for the elementary identities or constructions in this note.

<a id="notation-and-organisation."></a>

#### Notation and organisation.

Write $`\mathbb{N}=\{0,1,\ldots\}`$, $`\mathbb{Z}`$ for the integers, $`\operatorname{Irr}(x)`$ for irrationality, $`\operatorname{den}(q)`$ for the reduced denominator of $`q\in\mathbb{Q}`$, and $`\varphi`$ for Euler’s totient. Section <a href="#sec:diagonal-collapse" data-reference-type="ref" data-reference="sec:diagonal-collapse">2</a> isolates the recurrence-level classifiers and the polynomial obstruction. Section <a href="#sec:parts" data-reference-type="ref" data-reference="sec:parts">3</a> proves the actual prime-to-gap identity; Section <a href="#sec:tail" data-reference-type="ref" data-reference="sec:tail">4</a> proves the shift classification and local criterion. Section <a href="#sec:carry" data-reference-type="ref" data-reference="sec:carry">5</a> explains the remaining carry freedom, and Section <a href="#sec:open" data-reference-type="ref" data-reference="sec:open">6</a> states the exact prime-specific obligation. The sources and verification boundary are recorded after the mathematics.

**Keywords.** irrationality; prime gaps; dyadic series; summation by parts; Lean 4. **MSC 2020.** 11J72 (primary); 11N05, 68V20 (secondary).

<a id="sec:diagonal-collapse"></a>

# Integral shifts and recurrence obstructions

We first record the strongest recurrence-level conclusions. They apply to arbitrary integer digits and therefore separate the finite algebra from the prime-specific input still missing in Problem #251.

For a real recurrence put
``` math
\Delta_hT(N)=T_{N+h}-T_N,
```
and let $`L_0=1`$, $`L_j=\operatorname{lcm}(1,\ldots,j)`$ for $`j\ge1`$.

<div id="res:lcmdiagonal" class="theorem">

**Theorem 2** (lcm-diagonal criterion). *Let $`g:\mathbb{N}\to\mathbb{Z}`$ and $`T:\mathbb{N}\to\mathbb{R}`$ satisfy $`T_{N+1}=2T_N-g_{N+1}`$ for every $`N`$. Then
``` math
\operatorname{Irr}(T_0)
 \quad\Longleftrightarrow\quad
 \Delta_{L_j}T(L_j)\notin\mathbb{Z}
 \quad\hbox{for every }j\ge0.
```*

</div>

<div class="proof">

*Proof.* Iteration gives $`T_N=2^NT_0-B_N`$ with $`B_N\in\mathbb{Z}`$, and hence
``` math
\Delta_hT(N)=2^N(2^h-1)T_0-C_{N,h},\qquad C_{N,h}\in\mathbb{Z}.
```
For $`h\ge1`$ the coefficient of $`T_0`$ is nonzero, so an integral shift forces $`T_0\in\mathbb{Q}`$. Conversely, write $`T_0=a/(2^sd)`$ in lowest terms with $`d`$ odd. Euler’s congruence gives $`d\mid2^{\varphi(d)}-1`$. Choose $`j`$ with $`L_j\ge s`$ and $`\varphi(d)\mid L_j`$. Then $`2^s d\mid2^{L_j}(2^{L_j}-1)`$, making the displayed $`L_j`$-shift integral at $`N=L_j`$. This contradicts the right-hand condition. ◻

</div>

The statement is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/OrderLatticeDiagonal.lean#L153).

The factorial schedule $`j!`$ has the same divisibility property, but the lcm schedule is pointwise no larger and is the canonical endpoint used here. The theorem is an exact one-sequence reformulation; it gives no non-integrality statement for the actual prime-gap recurrence.

The adjacent-small-mismatch condition also admits an exact normal form. For a rational recurrence and a fixed $`h`$, write
``` math
D_N=\Delta_hT(N),\qquad
 \delta_N=g_{N+h+1}-g_{N+1}.
```
Then $`D_{N+1}=2D_N-\delta_N`$.

<div id="res:signedwindow" class="theorem">

**Theorem 3** (signed two-window normal form). *Assume that $`\delta_N`$ is even. The conjunction
``` math
-1<D_N<1,\qquad -1<D_{N+1}<1,\qquad \delta_N\ne0
```
is equivalent to
``` math
\bigl(\delta_N=2\ \hbox{ and }\tfrac12<D_N<1\bigr)
 \quad\hbox{or}\quad
 \bigl(\delta_N=-2\ \hbox{ and }-1<D_N<-\tfrac12\bigr).
```*

</div>

<div class="proof">

*Proof.* The recurrence and the two unit windows give $`-3<\delta_N<3`$. A nonzero even integer in that interval is $`2`$ or $`-2`$. Substitution into $`D_{N+1}=2D_N-\delta_N`$ gives the stated half-window and, in the reverse direction, recovers the second unit window. ◻

</div>

The rational normal form is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/AffineShiftEscape.lean#L113). The same equivalence for real states is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperCoreR7.lean#L135).

For the longer block, set
``` math
B_{h,N,r}=\sum_{i=0}^{r-1}2^{r-1-i}\delta_{N+i};
 \qquad D_{N+r}=2^rD_N-B_{h,N,r}.
```
Call the data-dependent affine condition
``` math
\mathcal A_{N,r}:\qquad
 D_{N+r}\in -B_{h,N,r}+2^{r+1}\mathbb{Z}.
```

<div id="res:affinecollapse" class="theorem">

**Theorem 4** (affine and fixed-lattice circularity). *For every rational dyadic tail recurrence and all $`h,N,r\ge0`$,
``` math
\mathcal A_{N,r}\quad\Longleftrightarrow\quad D_N\in2\mathbb{Z}.
\tag{2.1}\label{eq:affinecollapse}
```
Consequently, if every $`\delta_N`$ is even, then
``` math
\bigl(\forall N_0\ \exists N,r:\ N_0<N\text{ and }\neg\mathcal A_{N,r}\bigr)
 \quad\Longleftrightarrow\quad
 D_N\notin\mathbb{Z}\text{ for arbitrarily large }N.
\tag{2.2}\label{eq:affinecofinal}
```*

*There is a second equivalence. Let $`b:\mathbb{N}\to\mathbb{Q}`$ satisfy $`|D_N|\le b(N)`$ for every $`N`$, and suppose that for every $`N`$ and every positive integer $`q`$ there is an $`r`$ with
``` math
2b(N+r)q<2^r.
\tag{2.3}\label{eq:dyadicscale}
```
Then
``` math
\begin{split}
 &\forall N_0\ \exists N,r:\ N_0<N\text{ and }
   \forall z\in\mathbb{Z},\quad
   b(N+r)<|B_{h,N,r}-2^rz|\\
 &\hspace{35mm}\Longleftrightarrow\quad
 D_N\notin\mathbb{Z}\text{ for arbitrarily large }N.
 \end{split}
\tag{2.4}\label{eq:fixedcollapse}
```*

</div>

<div class="proof">

*Proof.* Substituting $`D_{N+r}=2^rD_N-B_{h,N,r}`$ into $`\mathcal A_{N,r}`$ cancels the observed block from both sides and leaves $`D_N=2z`$. This proves <a href="#eq:affinecollapse" data-reference-type="eqref" data-reference="eq:affinecollapse">[eq:affinecollapse]</a>. After one recurrence step, evenness of $`\delta_N`$ identifies even integrality at $`N+1`$ with ordinary integrality at $`N`$. The forward implication in <a href="#eq:affinecofinal" data-reference-type="eqref" data-reference="eq:affinecofinal">[eq:affinecofinal]</a> follows, while the reverse implication chooses a nonintegral $`D_N`$ and the legal depth $`r=0`$.

For <a href="#eq:fixedcollapse" data-reference-type="eqref" data-reference="eq:fixedcollapse">[eq:fixedcollapse]</a>, eventual integrality and the block identity give some $`z\in\mathbb{Z}`$ with
``` math
B_{h,N,r}-2^rz=-D_{N+r},
```
so the displayed strict separation contradicts $`|D_{N+r}|\le b(N+r)`$. Conversely, if $`D_N`$ is nonintegral and has reduced denominator $`q`$, then its distance from every integer is at least $`1/q`$. Choose $`r`$ from <a href="#eq:dyadicscale" data-reference-type="eqref" data-reference="eq:dyadicscale">[eq:dyadicscale]</a>, scale this separation by $`2^r`$, and use the block identity together with $`|D_{N+r}|\le b(N+r)`$. The triangle inequality gives $`|B_{h,N,r}-2^rz|>b(N+r)`$ for every integer $`z`$. ◻

</div>

The three displayed equivalences are assembled in one declaration, [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperCoreR7.lean#L241).

The first equivalence shows that the apparent affine hierarchy contains no depth-dependent information: it is the pullback of even integrality through the recurrence identity. The fixed lattice removes that data dependence, but under the stated growth condition rational denominator separation already forces every required escape. Hence neither cofinal condition is an independent source of information about consecutive primes.

Finally, the coarse coefficient profile itself has an exact infinite counterexample.

<div id="res:polynomialcountermodel" class="proposition">

**Proposition 5** (quadratic polynomial-shift countermodel). *Put
``` math
a_n=2(n^2+4n+2),\qquad U_n=2(n+4)^2.
```
Then $`a_n`$ is positive, even and strictly increasing, $`U_{n+1}=2U_n-a_{n+1}`$, every shift $`U_{N+h}-U_N`$ is integral,
``` math
a_{N+2}-a_{N+1}\ne2,-2
 \qquad\hbox{for every }N,
```
and
``` math
\sum_{j\ge1}\frac{a_j}{2^j}=32
```
as the kernel-checked identity for the countermodel series value.*

</div>

<div class="proof">

*Proof.* Expand $`a_{n+1}-a_n=4n+10`$ and $`2U_n-U_{n+1}=a_{n+1}`$. The $`h`$-shift is $`U_{N+h}-U_N=2h(2N+h+8)`$, an even integer. The finite telescope $`\sum_{j=1}^{N}a_j/2^j=32-U_N/2^N`$ is exact rational algebra from the recurrence; $`U_N/2^N\to0`$ because a quadratic is dominated by $`2^N`$. The nonnegative terms therefore have infinite sum $`32`$. Strict growth makes the word unbounded and nonperiodic. ◻

</div>

The eight displayed clauses are assembled as one statement in [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperCoreR7.lean#L27).

<a id="sec:parts"></a>

# Summation by parts, with the endpoint retained

Summation by parts trades a sequence for its consecutive differences. The form recorded here is exact: it carries no error term, it assumes nothing about the sequence, and it retains the endpoint term rather than absorbing it into an estimate. For a sequence $`P`$ of rational numbers and $`n\ge0`$ put
``` math
D(P,n)=\sum_{i=0}^{n-1}\frac{P(i)}{2^{\,i+1}},
 \qquad
 \Delta(P,n)=\sum_{i=0}^{n-1}\frac{P(i+1)-P(i)}{2^{\,i+1}} ,
```
both empty, hence zero, at $`n=0`$. We call these the [dyadic partial sum](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L101) and the [dyadic difference sum](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L121) of $`P`$.

<div id="res:abel" class="proposition">

**Proposition 6** (finite summation by parts). *For every rational sequence $`P`$ and every $`n\ge0`$,
``` math
D(P,n+1)=P(0)+\Delta(P,n)-\frac{P(n)}{2^{\,n+1}} .
```*

</div>

<div class="proof">

*Proof.* A routine induction on $`n`$. At $`n=0`$ both sides equal $`P(0)/2`$. For the step, adding $`P(n+1)/2^{\,n+2}`$ to the left and $`\bigl(P(n+1)-P(n)\bigr)/2^{\,n+1}`$ to the difference sum changes the endpoint term from $`P(n)/2^{\,n+1}`$ to $`P(n+1)/2^{\,n+2}`$, and the two adjustments agree. ◻

</div>

No positivity, monotonicity or convergence is required.

Specialising to $`P(i)=p_i`$, whose first value is $`p_0=2`$, and writing $`g_i=p_{i+1}-p_i`$ for the zero-based gaps, gives the reformulation.

<div id="res:parts" class="theorem">

**Theorem 7** (prime-gap reformulation). *Let $`p_0=2,p_1=3,\ldots`$ be the primes in increasing order and $`g_i=p_{i+1}-p_i`$. For every $`n\ge0`$,
``` math
\sum_{i=0}^{n}\frac{p_i}{2^{\,i+1}}
 =2+\sum_{i=0}^{n-1}\frac{g_i}{2^{\,i+1}}-\frac{p_n}{2^{\,n+1}} .
```*

</div>

The leading $`2`$ is $`p_0`$. At $`n=2`$ both sides equal $`19/8`$.

<a id="sec:infinite"></a>

## The infinite identity and the irrationality equivalence

Write
``` math
u_n=\frac{p_n}{2^{\,n+1}},\qquad
 v_n=\frac{g_n}{2^{\,n+1}}
```
for the terms of the prime series and of the gap series, so that $`\sum_{n\ge0}u_n=\Pi`$. The termwise identity $`v_n=2u_{n+1}-u_n`$ is the [dyadic discrete derivative](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L202). It expresses each gap term as an integer combination of two consecutive prime terms, so once $`(u_n)`$ is summable the gap series can be summed by rearranging two copies of the prime series, which is what the following proof does.

<div id="res:infinite" class="theorem">

**Theorem 8** (infinite prime-gap identity). *Let $`u_n=p_n/2^{\,n+1}`$ and $`v_n=g_n/2^{\,n+1}`$. If $`(u_n)`$ is summable, then $`(v_n)`$ is summable and
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

The summability transfer is the [gap-series summability theorem](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L385), and the displayed identity is the [infinite prime-gap identity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L404). Summability of both series is part of the conclusion in [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperCoreR7.lean#L47) rather than a hypothesis carried by the reader.

<div id="res:irr-equivalence" class="corollary">

**Corollary 9** (exact irrationality reformulation). *With $`u_n`$ and $`v_n`$ as in Theorem <a href="#res:infinite" data-reference-type="ref" data-reference="res:infinite">8</a>, and $`(u_n)`$ summable,
``` math
\operatorname{Irr}\!\left(\sum_{n\ge0}u_n\right)
 \quad\Longleftrightarrow\quad
 \operatorname{Irr}\!\left(\sum_{n\ge0}v_n\right).
```
The corresponding zero-based series with denominator $`2^n`$ is $`4+2\sum_{n\ge0}v_n`$ and has the same irrationality status.*

</div>

These are the [normalised irrationality equivalence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L435), the [displayed-series identity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L444), and the [displayed-series irrationality equivalence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L459). The three clauses are also available as the single declaration [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperCoreR7.lean#L56).

<a id="the-summability-hypothesis."></a>

#### The summability hypothesis.

The formal source now proves the elementary polynomial bound $`p_n\le1250(n+1)^4`$, using prime counting and central-binomial growth, and deduces summability directly ([polynomial bound](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L360), [summability](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L379)). Thus Theorem <a href="#res:infinite" data-reference-type="ref" data-reference="res:infinite">8</a> and Corollary <a href="#res:irr-equivalence" data-reference-type="ref" data-reference="res:irr-equivalence">9</a> are now unconditional Lean-checked statements; the prime number theorem remains useful context but is no longer a proof dependency of this note. The open content is exactly irrationality of the prime-gap series. Concretely, $`\Pi=3.674643966\ldots`$ is irrational if and only if $`\sum_{n\ge0}g_n2^{-(n+1)}=1.674643966\ldots`$ is, and neither is known.

<a id="sec:tail"></a>

# The tail recurrence and integral shifts

The series is not attacked directly. Suppose $`\sum_{i\ge0}a_i2^{-(i+1)}`$ converges, with every $`a_i`$ an integer, and rescale its tails by putting
``` math
T_N=2^{\,N+1}\sum_{i>N}\frac{a_i}{2^{\,i+1}}
    =\sum_{j\ge1}\frac{a_{N+j}}{2^{\,j}} .
```
Two facts follow immediately. First $`T_{N+1}=2T_N-a_{N+1}`$, so moving one level along doubles the rescaled tail and subtracts a single coefficient. Second $`T_0=2\sum_{i\ge0}a_i2^{-(i+1)}-a_0`$, so the sum is rational exactly when $`T_0`$ is. The whole of Section <a href="#sec:tail" data-reference-type="ref" data-reference="sec:tail">4</a> therefore studies that recurrence in isolation, assuming nothing about the coefficients beyond the fact that they are integers; the prime-gap instance is resumed at the end of the section. The following definition is the object so obtained, stripped of its origin.

<div id="def:rec" class="definition">

**Definition 10**. Let $`g:\mathbb{N}\to\mathbb{Z}`$ and $`T:\mathbb{N}\to\mathbb{Q}`$. Say $`T`$ satisfies the *dyadic tail recurrence* with *digits* $`g`$ when
``` math
T_{N+1}=2T_N-g_{N+1}\qquad\text{for every }N .
```
We call the sequence $`(T_N)_{N\ge0}`$ the *orbit* of $`T_0`$ under $`g`$, write $`\sigma_h(N)=T_{N+h}-T_N`$ for the *shift* of length $`h`$ at $`N`$, and call a rational number *integral* when it is the image of an integer.

</div>

These are the [tail recurrence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L482), the [shift](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L544), and [integrality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L575). The digits are arbitrary integers. In the intended instance they are the prime gaps and $`T_N`$ is the complete gap tail $`\sum_{j\ge1}g_{N+j}2^{-j}`$. That identification, and the recurrence over $`\mathbb R`$ with no rationality hypothesis, already sit in `RealPrimeGapTail.lean`. Every statement below is a theorem about Definition <a href="#def:rec" data-reference-type="ref" data-reference="def:rec">10</a>.

One small orbit, referred to again below, is worth having in view. Take every digit $`g_N=0`$ and $`T_0=1/12`$. Then $`T_{N+1}=2T_N`$, so the orbit is $`\tfrac1{12},\tfrac16,\tfrac13,\tfrac23,\tfrac43,\ldots`$, and $`\sigma_h(N)=(2^{h}-1)2^{\,N}/12`$. The shift of length $`2`$ is not integral at $`N=0`$, where $`\sigma_2(0)=\tfrac13-\tfrac1{12}=\tfrac14`$, and is integral at $`N=2`$, where $`\sigma_2(2)=\tfrac43-\tfrac13=1`$; the shift of length $`1`$ is $`\sigma_1(N)=2^{\,N}/12`$ and is never integral. The change at $`N=2`$ is accounted for by Theorem <a href="#res:collapse" data-reference-type="ref" data-reference="res:collapse">15</a>, and the failure at $`h=1`$ by Theorem <a href="#res:shiftiff" data-reference-type="ref" data-reference="res:shiftiff">12</a>.

Iterating the recurrence $`h`$ times multiplies $`T_N`$ by $`2^{h}`$ and accumulates an explicit integer, which we now name. Define $`B_{0,N}=0`$ and $`B_{h+1,N}=2B_{h,N}+g_{N+h+1}`$, so that $`B_{h,N}=g_{N+1}2^{\,h-1}+\cdots+g_{N+h}`$: the [tail block](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L647). Thus $`B_{1,N}=g_{N+1}`$, $`B_{2,N}=2g_{N+1}+g_{N+2}`$ and $`B_{3,N}=4g_{N+1}+2g_{N+2}+g_{N+3}`$: the block puts the weights $`2^{\,h-1},\ldots,2^{0}`$ on the $`h`$ digits following index $`N`$.

<div id="res:block" class="theorem">

**Theorem 11** (block identity). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer digits $`g`$, and let $`B_{h,N}`$ be as above. For every $`N`$ and $`h`$,
``` math
T_{N+h}=2^{h}T_N-B_{h,N},
 \qquad\text{hence}\qquad
 \sigma_h(N)=(2^{h}-1)\,T_N-B_{h,N} .
```*

</div>

<div class="proof">

*Proof.* A routine induction on $`h`$; the step is one application of the recurrence together with $`2\cdot2^{h}=2^{h+1}`$ and the recursion defining $`B`$. The second identity is the first minus $`T_N`$. ◻

</div>

Both identities are stated together in [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperCoreR7.lean#L68), and the real-state form is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperCoreR7.lean#L76).

The shifts themselves satisfy
``` math
\sigma_h(N+1)=2\sigma_h(N)-(g_{N+h+1}-g_{N+1}).
```

Since $`B_{h,N}`$ is an integer, Theorem <a href="#res:block" data-reference-type="ref" data-reference="res:block">11</a> converts a question about the shift into a question about the single scaled term $`(2^{h}-1)T_N`$.

<div id="res:shiftiff" class="theorem">

**Theorem 12** (integral-shift criterion). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer digits $`g`$. For every $`N`$ and $`h`$, the shift $`\sigma_h(N)`$ is integral if and only if $`(2^{h}-1)T_N`$ is integral.*

</div>

<div class="proof">

*Proof.* By Theorem <a href="#res:block" data-reference-type="ref" data-reference="res:block">11</a> the two differ by the integer $`B_{h,N}`$, and subtracting an integer does not change integrality. ◻

</div>

Thus integrality depends only on the reduced denominator of $`T_N`$.

The denominator criterion is exact:
``` math
\sigma_h(N)\in\mathbb{Z}
  \quad\Longleftrightarrow\quad
  \operatorname{den}(T_N)\mid 2^h-1.
\tag{3.4}\label{eq:shift-denominator}
```
This is the [denominator classification](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1279). Euler’s totient supplies one admissible shift length when the denominator is odd; it is a witness, not the classification itself.

<div id="res:totient" class="theorem">

**Theorem 13** (a shift of totient length). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer digits $`g`$, and let $`\varphi`$ be Euler’s totient function. If the reduced denominator $`d`$ of $`T_N`$ is odd, then $`\sigma_{\varphi(d)}(N)`$ is integral.*

</div>

<div class="proof">

*Proof.* Since $`d`$ is odd, $`2`$ and $`d`$ are coprime, so Euler’s congruence gives $`2^{\varphi(d)}\equiv1\pmod d`$, that is $`d\mid 2^{\varphi(d)}-1`$. Writing $`2^{\varphi(d)}-1=dk`$ and $`T_N=u/d`$ in lowest terms, $`(2^{\varphi(d)}-1)T_N=ku`$ is an integer, and Theorem <a href="#res:shiftiff" data-reference-type="ref" data-reference="res:shiftiff">12</a> transfers this to the shift. ◻

</div>

For $`\operatorname{den}T_N=3`$, the shift of length $`2`$ is integral while the shift of length $`1`$ is not. For denominator $`5`$, length $`4`$ is admissible.

The hypothesis is a genuine restriction: the argument uses coprimality of $`2`$ with the denominator, and the even part of a denominator is exactly what the doubling in the recurrence acts on. It cannot be dropped. If $`T_N=1/2`$ then $`2^{h}-1`$ is odd for every $`h\ge1`$, so $`(2^{h}-1)T_N`$ is never an integer and, by Theorem <a href="#res:shiftiff" data-reference-type="ref" data-reference="res:shiftiff">12</a>, no shift at $`N`$ is integral.

<div id="res:propagate" class="theorem">

**Theorem 14** (propagation). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer digits $`g`$, and fix $`h`$ and $`N`$. If $`\sigma_h(N)`$ is integral, then $`\sigma_h(N+k)`$ is integral for every $`k\ge0`$.*

</div>

<div class="proof">

*Proof.* By the shift step identity, $`\sigma_h(N+1)=2\sigma_h(N)-(g_{N+h+1}-g_{N+1})`$ is an integer combination of an integer and two digits; induct on $`k`$. ◻

</div>

The three preceding theorems combine as follows, and this is the statement the rest of the note rests on. The special case is immediate: if $`\operatorname{den}T_0`$ is already odd, then Theorem <a href="#res:totient" data-reference-type="ref" data-reference="res:totient">13</a> at $`N=0`$ makes the shift of length $`\varphi(\operatorname{den}T_0)`$ integral and Theorem <a href="#res:propagate" data-reference-type="ref" data-reference="res:propagate">14</a> keeps it integral at every later index, so one may take $`N_0=0`$. In general a denominator carries a power of two as well, and the key point is that the doubling in the recurrence annihilates exactly the $`2`$-adic part of a denominator, and nothing else: after finitely many steps the orbit therefore reaches a term with odd reduced denominator, which is precisely the situation Theorem <a href="#res:totient" data-reference-type="ref" data-reference="res:totient">13</a> handles. No control of the digits is needed anywhere.

<div id="res:collapse" class="theorem">

**Theorem 15** (exact denominator dynamics and eventual integrality). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer digits $`g`$ (Definition <a href="#def:rec" data-reference-type="ref" data-reference="def:rec">10</a>). Then some fixed positive shift is integral from some point onwards:
``` math
\exists h\ge1\ \exists N_0\ \forall N\ge N_0,\qquad
 \sigma_h(N)\in\mathbb{Z}.
```*

</div>

<div class="proof">

*Proof.* At every step the reduced denominator obeys the exact recurrence
``` math
\operatorname{den}(T_{N+1})
 =\frac{\operatorname{den}(T_N)}{\gcd(2,\operatorname{den}(T_N))}.
```
Thus each even denominator loses exactly one factor of $`2`$, while an odd denominator is unchanged. After finitely many steps the denominator is odd. Theorem <a href="#res:totient" data-reference-type="ref" data-reference="res:totient">13</a>, applied at that index $`s`$, supplies the positive shift $`h=\varphi(\operatorname{den}T_s)`$, and Theorem <a href="#res:propagate" data-reference-type="ref" data-reference="res:propagate">14</a> keeps that shift integral at every later index. ◻

</div>

The one-step formula is the [denominator recurrence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1217), with its [odd case](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1226) and [even case](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1236).

In the orbit displayed after Definition <a href="#def:rec" data-reference-type="ref" data-reference="def:rec">10</a> the proof runs as follows: $`\operatorname{den}T_0=12=2^{2}\cdot3`$, so $`s=2`$, the orbit reaches $`T_2=1/3`$ with odd denominator, and $`h=\varphi(3)=2`$. That is exactly the shift length seen to be integral there from index $`2`$ onwards, and no shorter one works.

Three features of the argument are used later. The proof may take as its number of preparatory steps the $`2`$-adic valuation of $`\operatorname{den}T_0`$. The resulting shift length $`h`$ is the totient of the odd denominator reached from a hypothetical rational initial value, and is not known in advance for the prime-gap orbit. This is why this argument requires Problem <a href="#prob:escape" data-reference-type="ref" data-reference="prob:escape">22</a> for every $`h`$, rather than for one preassigned shift length. Finally, the digits enter only through the integer $`B_{s,0}`$, so the conclusion holds for an arbitrary integer digit sequence.

In the current formal source, denominator factorisation and cancellation are packaged directly in the [fixed-denominator theorem](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L830), and the quantified conclusion is the [eventual integral-shift theorem](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L853) for the actual prime-gap tail state. The displayed indexed form is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperCoreR7.lean#L84).

The useful contrapositive is stated for a real recurrence. Call its shifts *cofinally non-integral* when, for every fixed $`h\ge1`$ and every threshold $`N_0`$, some $`N\ge N_0`$ has $`\sigma_h(N)\notin\mathbb{Z}`$. This is precisely the negation of the conclusion of Theorem <a href="#res:collapse" data-reference-type="ref" data-reference="res:collapse">15</a>: no shift length whatever becomes integral and stays integral.

<div id="res:escape-irrational" class="theorem">

**Theorem 16** (exact rationality classification). *Let $`T:\mathbb{N}\to\mathbb{R}`$ satisfy $`T_{N+1}=2T_N-g_{N+1}`$ with integer $`g`$. If its shifts are defined by $`\sigma_h(N)=T_{N+h}-T_N`$, then the following are equivalent:*

1.  *$`T_0`$ is rational;*

2.  *$`\sigma_h(N)`$ is integral for some $`h\ge1`$ and some $`N`$;*

3.  *for some fixed $`h\ge1`$, $`\sigma_h(N)`$ is integral at every sufficiently large $`N`$.*

*Consequently $`T_0`$ is irrational if and only if every positive-length shift is non-integral at every index, equivalently if and only if the shifts are cofinally non-integral.*

</div>

<div class="proof">

*Proof.* For <span class="upright">(i)</span>$`\Rightarrow`$<span class="upright">(iii)</span>, choose $`q\in\mathbb{Q}`$ whose real cast is $`T_0`$. The real block identity identifies the whole orbit with the cast of the rational recurrence starting at $`q`$; Theorem <a href="#res:collapse" data-reference-type="ref" data-reference="res:collapse">15</a> applied to that rational orbit then gives <span class="upright">(iii)</span>. The implication <span class="upright">(iii)</span>$`\Rightarrow`$<span class="upright">(ii)</span> is immediate. For <span class="upright">(ii)</span>$`\Rightarrow`$<span class="upright">(i)</span>, the real block identity gives
``` math
\sigma_h(N)=(2^h-1)T_N-B_{h,N}.
```
Here $`B_{h,N}`$ and $`\sigma_h(N)`$ are integers and $`2^h-1\ne0`$, so $`T_N`$ is rational. Iterating the recurrence backwards through the block identity then makes $`T_0`$ rational. Negating the pointwise and eventual forms gives the two irrationality formulations. ◻

</div>

Lean checks the rational actual-tail state as [rational prime-gap tail state](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L489), its [recurrence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L527), and the bridge from a hypothetical rational value to that state as [the rational-tail representation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L510). The exact real classifiers are [one integral positive shift](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1479), [eventual integrality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1525), [pointwise non-integrality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1551), and [cofinal non-integrality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1572). All four equivalences are collected in [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperCoreR7.lean#L94).

<a id="the-actual-prime-gap-orbit."></a>

#### The actual prime-gap orbit.

The concrete tails
``` math
T_N=\sum_{j\ge1}\frac{g_{N+j}}{2^j}
```
are already identified in Lean, with no rationality hypothesis . The Lean-checked polynomial prime bound gives convergence, and $`T_{N+1}=2T_N-g_{N+1}`$ is the same identification. If $`G=\sum_{n\ge0}g_n/2^{n+1}`$, then $`T_0=2G-1`$. Together with Theorem <a href="#res:infinite" data-reference-type="ref" data-reference="res:infinite">8</a>, this shows that $`\Pi`$, $`G`$, and $`T_0`$ have the same rationality status. Thus Theorem <a href="#res:escape-irrational" data-reference-type="ref" data-reference="res:escape-irrational">16</a> identifies Problem #251 exactly with cofinal shift escape for $`T`$. The older rational-candidate representation remains in `PrimeGapDyadicTail.lean`. What is not proved is the cofinal non-integrality needed by Theorem <a href="#res:escape-irrational" data-reference-type="ref" data-reference="res:escape-irrational">16</a>.

<a id="sec:local-certificate"></a>

## Two adjacent small shifts cannot both be integral

The exact classifier reduces irrationality to cofinal non-integrality, a condition of infinite precision imposed on a complete tail. The key point is that inside the open interval $`(-1,1)`$ integrality is equality with zero, so on that range the one-step shift recurrence
``` math
\sigma_h(N+1)=2\sigma_h(N)-\bigl(g_{N+h+1}-g_{N+1}\bigr)
```
turns simultaneous integrality of two adjacent shifts into a single comparison of digits. What this buys is a *certificate*: a condition attached to a single pair of adjacent indices, whose verification already contradicts integrality at that pair. The point of arranging the argument this way is that the distance of a shift from the integers never has to be estimated; it suffices to know that both shifts lie in $`(-1,1)`$ and that two digits differ.

<div id="res:smallpair" class="theorem">

**Theorem 17** (adjacent small-shift obstruction). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer digits $`g`$. Fix $`h`$ and $`N`$. If
``` math
-1<\sigma_h(N)<1,\qquad -1<\sigma_h(N+1)<1,
 \qquad g_{N+h+1}\ne g_{N+1},
```
then $`\sigma_h(N)`$ and $`\sigma_h(N+1)`$ cannot both be integral. Consequently, if such a pair occurs beyond every threshold, the $`h`$-shift is not eventually integral.*

</div>

<div class="proof">

*Proof.* An integral rational strictly between $`-1`$ and $`1`$ is zero. If both shifts were integral, both would therefore vanish, and substitution in the displayed shift step identity would give $`g_{N+h+1}=g_{N+1}`$, a contradiction. The cofinal statement chooses one such adjacent pair after the alleged onset of integrality. ◻

</div>

The finite contradiction is the [adjacent small-shift obstruction](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L979); its quantified form is the [cofinal small-mismatch theorem](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1006); and the actual-prime-gap specialisation is the [prime-gap specialisation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1112). Theorem <a href="#res:smallpair" data-reference-type="ref" data-reference="res:smallpair">17</a> is conditional on its two tail inequalities; no theorem asserting that such pairs occur is claimed here. The local obstruction and its cofinal consequence are stated as one declaration in [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperCoreR7.lean#L267).

All three are stated for a rational orbit, while the prime-gap tail $`T`$ of Section <a href="#sec:tail" data-reference-type="ref" data-reference="sec:tail">4</a> is real, so the rational statement does not on its own discharge the instances that arise downstream. The same argument gives the real form directly.

<div id="res:smallpair-real" class="corollary">

**Corollary 18** (adjacent small-shift obstruction, real form). *Let $`T:\mathbb{N}\to\mathbb{R}`$ satisfy $`T_{N+1}=2T_N-g_{N+1}`$ with integer digits $`g`$, and write $`\sigma_h(N)=T_{N+h}-T_N`$. Fix $`h`$ and $`N`$. If
``` math
-1<\sigma_h(N)<1,\qquad -1<\sigma_h(N+1)<1,
 \qquad g_{N+h+1}\ne g_{N+1},
```
then $`\sigma_h(N)`$ and $`\sigma_h(N+1)`$ do not both lie in $`\mathbb{Z}`$. Consequently, if such a pair occurs beyond every threshold, the $`h`$-shift is not eventually integral.*

</div>

<div class="proof">

*Proof.* The real recurrence gives the same shift step identity $`\sigma_h(N+1)=2\sigma_h(N)-\bigl(g_{N+h+1}-g_{N+1}\bigr)`$, and an integer strictly between $`-1`$ and $`1`$ is zero. If both shifts lay in $`\mathbb{Z}`$, both would therefore vanish, and substitution in that identity would give $`g_{N+h+1}=g_{N+1}`$, a contradiction. The cofinal statement chooses one such adjacent pair after the alleged onset of integrality. ◻

</div>

Corollary <a href="#res:smallpair-real" data-reference-type="ref" data-reference="res:smallpair-real">18</a> is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperCoreR7.lean#L282), and the resulting implication for the actual prime series is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperCoreR7.lean#L298). These live declarations can postdate the historical public snapshot used by the source links.

The third hypothesis, on its own, is available. For the actual gaps tabulated in Section <a href="#sec:problem" data-reference-type="ref" data-reference="sec:problem">1</a> it reads $`g_4=2\ne4=g_3`$ at $`h=1`$, $`N=2`$; and Proposition <a href="#res:gap-nonperiodic" data-reference-type="ref" data-reference="res:gap-nonperiodic">19</a> below says precisely that for each fixed $`h\ge1`$ the inequality $`g_{N+h+1}\ne g_{N+1}`$ holds for arbitrarily large $`N`$, since its failure from some index onwards is eventual periodicity with period $`h`$. What is missing is their joint occurrence with the digit mismatch at the same indices. Each inequality constrains a complete infinite tail.

<div id="res:gap-nonperiodic" class="proposition">

**Proposition 19** (prime gaps do not become periodic). *For every positive $`h`$, the actual consecutive-prime-gap sequence is not eventually periodic with period $`h`$.*

</div>

<div class="proof">

*Proof.* The gaps are unbounded, by the standard construction: the interval from $`n!+2`$ to $`n!+n`$ contains no prime. Far stronger lower bounds for large gaps are known \[fgkmt2018, Theorem 1, p. 66\], but unboundedness is all that is needed. An eventually periodic natural-valued sequence has finite range after its preperiod, while its finite initial segment is bounded as well; hence it is bounded, a contradiction. ◻

</div>

Lean checks the factorial argument as [unboundedness of the actual gaps](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L57) and the conclusion as [non-eventual periodicity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1023). The statement at the index convention displayed above is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperCoreR7.lean#L175). Combining nonperiodicity with eventual strict smallness of one positive shift would also exclude eventual integrality, but eventual smallness at every sufficiently large index is stronger than the cofinal adjacent-pair hypothesis in Theorem <a href="#res:smallpair" data-reference-type="ref" data-reference="res:smallpair">17</a> and is not asserted here.

<a id="sec:carry"></a>

# Nonperiodic coefficients with a rational sum

Proposition <a href="#res:gap-nonperiodic" data-reference-type="ref" data-reference="res:gap-nonperiodic">19</a> shows that the prime gaps are not eventually periodic. One might therefore hope that rationality of a dyadic series forces its integer coefficients to be eventually periodic, and play the two against each other. The hoped-for implication is false, and a single explicit sequence refutes it.

The construction runs the emission of coefficients backwards. Let $`K:\mathbb{N}\to\mathbb{Q}`$ be arbitrary, read $`K_n`$ as the value carried into level $`n`$, and put $`\kappa_n=2K_n-K_{n+1}`$: the [carry coefficient](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1129). That definition is exactly the statement that
``` math
\frac{K_n}{2^{\,n}}
 =\frac{\kappa_n}{2^{\,n+1}}+\frac{K_{n+1}}{2^{\,n+1}} ,
```
so at each level the carried value splits into one emitted coefficient and a new carry. Nothing at all is assumed about $`K`$: not integrality, not positivity, not any bound. That is the sense in which the carry is free, and it is what the counterexample below exploits.

<div id="res:telescope" class="proposition">

**Proposition 20** (exact telescoping). *Let $`K:\mathbb{N}\to\mathbb{Q}`$ be arbitrary and $`\kappa_n=2K_n-K_{n+1}`$. For every $`n\ge0`$,
``` math
\sum_{i=0}^{n-1}\frac{\kappa_i}{2^{\,i+1}}=K_0-\frac{K_n}{2^{\,n}} .
```*

</div>

<div class="proof">

*Proof.* A routine induction on $`n`$; the added term is $`(2K_n-K_{n+1})/2^{\,n+1}=K_n/2^{\,n}-K_{n+1}/2^{\,n+1}`$. ◻

</div>

<a id="consequence-for-the-coefficients."></a>

#### Consequence for the coefficients.

If $`K_n2^{-n}\to0`$, the emitted partial sums converge to $`K_0`$. A parity-compatible positive example is
``` math
K_0=\frac52,\qquad K_n=2n+2\ (n\ge1),\qquad
 \kappa_0=1,\quad\kappa_n=2n\ (n\ge1),
```
for which
``` math
\sum_{i=0}^{n-1}\frac{\kappa_i}{2^{\,i+1}}
   =\frac52-\frac{K_n}{2^n}\longrightarrow\frac52.
```
Thus the emitted coefficients $`1,2,4,6,8,10,\ldots`$ are positive, even after the first term, unbounded and not eventually periodic, although their dyadic sum is rational. Rationality alone therefore cannot imply eventual periodicity even for a positive, parity-correct integer coefficient sequence. The example does not claim that these coefficients are prime gaps; it isolates the additional arithmetic information any successful argument must use.

<a id="sec:open"></a>

# Complements and further questions

Problem #251 is open. The public Lean source now proves unconditional convergence of both dyadic series, their exact infinite summation-by-parts identity, and the real-to-rational scaled-tail representation ([identity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L427), [tail representation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L510)). It also proves that every rational candidate supplies one positive fixed shift which is integral at every sufficiently late tail index ([checked](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L853)). The denominator construction selects that same shift so that prime-gap nonperiodicity also rules out its eventual confinement to the open unit interval ([not eventually small](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1097)). This conclusion is compatible with rationality: it says that the rationally forced shift cannot support an eventual-smallness contradiction. It supplies neither eventual smallness nor cofinally many adjacent small mismatches for that shift. The remaining issue is recurrence or anti-concentration of the *actual* prime-gap shifts. Throughout, $`g_i=p_{i+1}-p_i`$ are the zero-based prime gaps of Section <a href="#sec:problem" data-reference-type="ref" data-reference="sec:problem">1</a>. Write $`\mathsf E(h)`$ for the cofinal escape statement in <a href="#eq:shift-escape" data-reference-type="eqref" data-reference="eq:shift-escape">[eq:shift-escape]</a> at shift $`h`$.

<div id="prob:divisor-hit" class="problem">

**Problem 21** (divisor-hitting shift escape). For every $`r\ge1`$, does some positive multiple of $`r`$ escape cofinally?
``` math
\forall r\ge1\ \exists m\ge1:\qquad \mathsf E(mr).
```

</div>

Divisor-hitting escape changes the organisation of the quantifiers. Within an integer-digit recurrence it is equivalent to irrationality, just as universal shift escape is: a rational state has a positive eventual order, and every positive multiple of that order is an integral shift. A quantitatively stated sufficient estimate can still be easier to attack, but that requires a separately proved analytic bound. Forward propagation is Lean-checked.

<div id="prob:escape" class="problem">

**Problem 22** (universal prime-gap shift escape). For every $`h\ge1`$ and every $`N_0`$, prove that some $`N\ge N_0`$ satisfies
``` math
\sum_{j\ge1}
 \frac{g_{N+h+j}-g_{N+j}}{2^j}\notin\mathbb{Z}.
\tag{5.1}\label{eq:shift-escape}
```

</div>

The series in <a href="#eq:shift-escape" data-reference-type="eqref" data-reference="eq:shift-escape">[eq:shift-escape]</a> is exactly $`T_{N+h}-T_N`$. Theorem <a href="#res:escape-irrational" data-reference-type="ref" data-reference="res:escape-irrational">16</a> makes Problem <a href="#prob:escape" data-reference-type="ref" data-reference="prob:escape">22</a> equivalent to irrationality of $`\Pi`$. Within the integer-digit recurrence, divisor-hitting and universal escape are equivalent: a hypothetical rational value chooses a shift length from the odd part of its reduced denominator, and the cocycle then makes every positive multiple eventually integral. The two formulations organise the quantifiers differently; they do not give a strict logical weakening.

<div id="prob:smallpair" class="problem">

**Problem 23** (cofinal adjacent small mismatch). For every fixed $`h\ge1`$ and every $`N_0`$, prove that some $`N\ge N_0`$ satisfies
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

The two sums are adjacent $`h`$-shifts. Corollary <a href="#res:smallpair-real" data-reference-type="ref" data-reference="res:smallpair-real">18</a> turns each instance of <a href="#eq:smallpair" data-reference-type="eqref" data-reference="eq:smallpair">[eq:smallpair]</a> into a finite contradiction to simultaneous integrality; Theorem <a href="#res:smallpair" data-reference-type="ref" data-reference="res:smallpair">17</a> is the Lean-checked rational case. A cofinal family of such pairs therefore proves Problem <a href="#prob:escape" data-reference-type="ref" data-reference="prob:escape">22</a>; Theorem <a href="#res:escape-irrational" data-reference-type="ref" data-reference="res:escape-irrational">16</a> then gives irrationality of the gap series, and Corollary <a href="#res:irr-equivalence" data-reference-type="ref" data-reference="res:irr-equivalence">9</a> transfers it to $`\Pi`$. The endpoint takes every positive $`h`$: a proof only at $`h=1`$ eliminates one eventual-integrality possibility and does not discharge the classifier. Digit mismatches and small shifts must occur at the same indices; separate cofinal occurrence statements do not establish that intersection. This formulation deliberately asks only for sporadic adjacent pairs; the stronger assertion that a fixed shift is eventually always smaller than one is unnecessary. The conjunction may have density zero: that excludes a positive-proportion lower bound, but an averaging argument may still produce an unbounded sparse count.

Several natural prime-distribution inputs are insufficient. Isolated small gaps, isolated large gaps, average gap estimates, and the occurrence of any one fixed finite pattern do not suffice: both inequalities in <a href="#eq:smallpair" data-reference-type="eqref" data-reference="eq:smallpair">[eq:smallpair]</a> contain the complete infinite continuation. Nor does parity: after the first gap all $`g_n`$ are even. Unboundedness and non-eventual-periodicity of the actual gaps, though now checked, do not imply the required small-tail recurrence. In particular, Section <a href="#sec:carry" data-reference-type="ref" data-reference="sec:carry">5</a> shows that no argument can deduce eventual periodicity from rationality alone.

<a id="a-finite-truncation-criterion."></a>

#### A finite truncation criterion.

Both problems above are stated in terms of infinite tails, but a dominated truncation reduces the first of them to a finite quantity. For $`L\ge1`$ put
``` math
S_{h,N,L}=\sum_{j=1}^{L}
 \frac{g_{N+h+j}-g_{N+j}}{2^j},
```
the truncation of the series in <a href="#eq:shift-escape" data-reference-type="eqref" data-reference="eq:shift-escape">[eq:shift-escape]</a> after $`L`$ terms. This is a finite sum of gap differences and can be computed; the point of the following proposition is to say how far from an integer it must be before the discarded tail is irrelevant.

Equivalently, introduce the integral dyadic block
``` math
D_{h,N,L}=\sum_{j=1}^{L}2^{L-j}
   (g_{N+h+j}-g_{N+j}),\qquad S_{h,N,L}=\frac{D_{h,N,L}}{2^L}.
```
Then
``` math
\operatorname{dist}(S_{h,N,L},\mathbb{Z})
 =2^{-L}\min\{D_{h,N,L}\bmod2^L,
 2^L-(D_{h,N,L}\bmod2^L)\}.
```
Here $`D_{h,N,L}\bmod2^L`$ denotes the least nonnegative residue, including when $`D_{h,N,L}<0`$. Thus the finite criterion below is an exact modular small-arc problem: the residue of $`D_{h,N,L}`$ must avoid the two arcs of radius $`2^LR_{h,N,L}(M)`$ around $`0`$ modulo $`2^L`$. A one-block certificate would be a prime-gap theorem producing such an avoided arc on a logarithmic block.

<div id="res:truncation" class="proposition">

**Proposition 24** (finite truncation). *Let $`M(n)\ge g_n`$ for every $`n`$, assume that the series below converges, and put
``` math
R_{h,N,L}(M)=
 \sum_{j>L}\frac{M(N+h+j)+M(N+j)}{2^j}.
```
Suppose that for every fixed $`h\ge1`$ and every $`N_0`$ there exist $`N\ge N_0`$ and $`L\ge1`$ with
``` math
\operatorname{dist}(S_{h,N,L},\mathbb{Z})>R_{h,N,L}(M).
\tag{5.3}\label{eq:truncation}
```
Then Problem <a href="#prob:escape" data-reference-type="ref" data-reference="prob:escape">22</a> holds.*

</div>

<div class="proof">

*Proof.* The part of $`\sum_{j\ge1}(g_{N+h+j}-g_{N+j})2^{-j}`$ omitted from $`S_{h,N,L}`$ has absolute value at most $`R_{h,N,L}(M)`$, so under <a href="#eq:truncation" data-reference-type="eqref" data-reference="eq:truncation">[eq:truncation]</a> the full sum lies at positive distance from every integer. ◻

</div>

The last distance-to-integers inference is the elementary paper argument in the displayed proof: an error at most $`R`$ cannot reach an integer when the approximation is farther than $`R`$ from every integer. It is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperTailBoundsR7.lean#L203), and the proposition itself is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperTailBoundsR7.lean#L261). For instance, if $`S_{h,N,L}=3/8`$ and $`R_{h,N,L}(M)=1/32`$, the full sum lies within $`1/32`$ of $`3/8`$ and so at distance at least $`11/32`$ from every integer, which settles <a href="#eq:shift-escape" data-reference-type="eqref" data-reference="eq:shift-escape">[eq:shift-escape]</a> at that $`N`$. The prime-gap tail bound, the convergence used above, and the existence of blocks satisfying <a href="#eq:truncation" data-reference-type="eqref" data-reference="eq:truncation">[eq:truncation]</a> are not consequences of that inference. The proposition’s full sum is real-valued, and the formal declaration is stated for the real tail throughout. Its conditional endpoint for the actual prime series is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos251/PaperTailBoundsR7.lean#L273).

Taking the classical bound $`M(n)\ll n\log n`$, a choice $`L=\lceil A\log_2(N+h+2)\rceil`$ with any fixed $`A>1`$ makes the right side a negative power of $`N`$ up to logarithms. Thus <a href="#eq:truncation" data-reference-type="eqref" data-reference="eq:truncation">[eq:truncation]</a> asks for a finite dyadic anti-concentration estimate on a logarithmic-length block, not control of an infinite tail and not eventual periodicity of the full gap sequence. For Problem <a href="#prob:smallpair" data-reference-type="ref" data-reference="prob:smallpair">23</a>, the same truncation must certify two adjacent full-tail values inside the open unit interval, together with the displayed gap mismatch. A finite prefix is useful only when its omitted tail is rigorously dominated.

What <a href="#eq:truncation" data-reference-type="eqref" data-reference="eq:truncation">[eq:truncation]</a> requires is joint control of the finite block of weighted differences $`(g_{N+h+1}-g_{N+1},\ldots,g_{N+h+L}-g_{N+L})`$ modulo powers of two, along a block of logarithmic length. We do not know how to obtain such control and we make no progress on it here. The strongest results on prime gaps address a different shape of question. Zhang’s bounded-gap theorem \[zhang2014, Theorem 1, p. 1122\] produces infinitely many bounded consecutive-prime gaps. Maynard proves substantially more than an individual-gap statement: \[maynard2015, Theorem 1.1, p. 384\] bounds $`\liminf_n(p_{n+m}-p_n)`$ for every fixed $`m`$, and hence gives bounded clusters of every fixed size; \[maynard2015, Theorem 1.3, p. 385\] gives the explicit unconditional bound $`\liminf_n(p_{n+1}-p_n)\le 600`$. The large-gap theorem of Ford, Green, Konyagin, Maynard and Tao \[fgkmt2018, Theorem 1, p. 66\] bounds the largest single consecutive-prime gap below $`X`$. None of these results supplies the joint dyadic distribution of a logarithmic block of consecutive gap differences required by <a href="#eq:truncation" data-reference-type="eqref" data-reference="eq:truncation">[eq:truncation]</a>. The same introduction notes a separate sequel on chains of large gaps; the cited theorem itself supplies no residue-sensitive block estimate of the kind needed here.

<a id="the-remaining-estimate."></a>

#### The remaining estimate.

The actual tails satisfy convergence, the prime-to-gap identity, and the recurrence used above. The unresolved input is the joint occurrence in <a href="#eq:smallpair" data-reference-type="eqref" data-reference="eq:smallpair">[eq:smallpair]</a> for every positive shift. A separate first-moment approach in the companion record uses
``` math
\sum_{X\le N<2X}T_{N+L}\ll X\log X\qquad(L\le X).
```
It controls the number of excessive omitted tails. A lower bound for the corresponding finite prime-gap configurations is still required. Sparse witness counts can suffice when they exceed that error budget. The independent finite continued-fraction enclosure gives $`q\ge2^{39997}>10^{12040}`$ for a rational representation of $`\Pi`$; it makes no assertion about an irrationality exponent.

<a id="statements-and-declarations"></a>

## Statements and declarations

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

The [source links](https://github.com/wcook04/plectis-erdos/tree/99f4bf47422abbd8757cbb22b50ba079d764d3a7) identify a fixed public snapshot. More recent live declarations are identified explicitly where they are used; a local declaration locator does not establish its presence at a historical public pin. The repository’s versioned source and verification records, rather than this manuscript’s navigation links, identify the checked object.

Lean checks each proof term against the fixed library version, and the sources linked here contain no proof placeholders and no project-defined axioms; Lean does not authorise the exposition, the citation choices, or the interpretation, for which the author remains responsible.

For Proposition <a href="#res:sparserationalisation" data-reference-type="ref" data-reference="res:sparserationalisation">1</a>, the pair identities, congruence buffer and abstract variable-alphabet filling are checked in `SparseRationalisationCore.lean`. The schedule, upper Banach density, and block-law transfer have ordinary proofs in `SparseRationalisation.md`.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.

<a id="acknowledgements."></a>

#### Acknowledgements.

The problem numbering and status follow the Erdős Problems catalogue maintained by Thomas Bloom \[erdosproblems\].

<a id="app:index"></a>

# Guide to the formal sources

Each linked phrase opens its Lean declaration at the pinned source revision 99f4bf47422a. The note’s declarations live in the \#251 modules, including the actual real-tail bridge. A local locator is not evidence that the historical public pin contains the file. The summation-by-parts declarations are prime-specific; most of Section <a href="#sec:tail" data-reference-type="ref" data-reference="sec:tail">4</a> is stated for arbitrary integer digits and arbitrary rational or real orbits, while Section <a href="#sec:local-certificate" data-reference-type="ref" data-reference="sec:local-certificate">4.1</a> records the actual-gap specialisation.

<div class="thebibliography">

99

P. Erdős, [*Sur certaines séries à valeur irrationnelle*](https://users.renyi.hu/~p_erdos/1958-19.pdf), Enseign. Math. (2) **4** (1958), 93–100, doi:[10.5169/seals-34629](https://doi.org/10.5169/seals-34629). The dyadic prime series is stated as unproved on p. 94; the factorial-prime family is stated on p. 93, with only the $`k=1`$ proof printed on pp. 94–95. P. Erdős and R. L. Graham, [*Old and New Problems and Results in Combinatorial Number Theory*](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf), Monogr. Enseign. Math. 28, Geneva, 1980, p. 62. P. Erdős and C. Pomerance, [*On the largest prime factors of $`n`$ and $`n+1`$*](https://doi.org/10.1007/BF01818569), Aequationes Math. **17** (1978), 311–321, doi:[10.1007/BF01818569](https://doi.org/10.1007/BF01818569). The unnumbered dyadic irrationality theorem and its complete proof are in §7 on p. 320. P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). P. Erdős and E. G. Straus, *On the irrationality of certain Ahmes series*, J. Indian Math. Soc. (N.S.) **27** (1964), 129–133. MR 175848. K. Ford, B. Green, S. Konyagin, J. Maynard and T. Tao, *Long gaps between primes*, J. Amer. Math. Soc. **31** (2018), 65–105, doi:[10.1090/jams/876](https://doi.org/10.1090/jams/876). Theorem 1 on p. 66 gives the effective lower bound for the largest single consecutive-prime gap below $`X`$. V. Kovač and T. Tao, [*On several irrationality problems for Ahmes series*](https://doi.org/10.1007/s10474-025-01528-0), Acta Math. Hungar. **175** (2025), 572–608. L. de Moura and S. Ullrich, [*The Lean 4 theorem prover and programming language*](https://doi.org/10.1007/978-3-030-79876-5_37), in A. Platzer and G. Sutcliffe (eds.), CADE 28, Lecture Notes in Comput. Sci. 12699, Springer, 2021, pp. 625–635, doi:[10.1007/978-3-030-79876-5_37](https://doi.org/10.1007/978-3-030-79876-5_37). The mathlib Community, [*The Lean mathematical library*](https://doi.org/10.1145/3372885.3373824), in CPP 2020, ACM, 2020, pp. 367–381, doi:[10.1145/3372885.3373824](https://doi.org/10.1145/3372885.3373824). The article describes a December 2019 Lean 3-era snapshot; the repository lock owns the current revision. J. Maynard, [*Small gaps between primes*](https://doi.org/10.4007/annals.2015.181.1.7), Ann. of Math. (2) **181** (2015), 383–413. H. L. Montgomery and R. C. Vaughan, [*Multiplicative Number Theory I: Classical Theory*](https://doi.org/10.1017/CBO9780511618314.008), Cambridge Stud. Adv. Math. 97, Cambridge UP, 2007, Chapter 6, pp. 168–198; Theorem 6.9, pp. 179–181, and Exercise 6.2.5, p. 183, doi:[10.1017/CBO9780511618314.008](https://doi.org/10.1017/CBO9780511618314.008). Y. Zhang, [*Bounded gaps between primes*](https://doi.org/10.4007/annals.2014.179.3.7), Ann. of Math. (2) **179** (2014), 1121–1174. T. F. Bloom, [*Erdős Problem \#251*](https://www.erdosproblems.com/251), `erdosproblems.com/251`, accessed 28 July 2026 (page displays “last edited 28 September 2025”). The current record labels the main dyadic problem open, cites `[Er58b]`, `[ErGr80, p. 62]` and `[Er88c, p. 103]`, and explicitly describes its status as the website owner’s present assessment rather than a literature-completeness guarantee; it does not mention the 2026 counterexample in \[kovac2026\] to the adjacent variable-denominator conjecture. ChatGPT 5.4 Pro (orchestrated by V. Kovač), [*On the Erdős problem \#251*](https://web.math.pmf.unizg.hr/~vjekovac/files/Erdos_problem_251.pdf), unpublished note, 2026, hosted by the Department of Mathematics, University of Zagreb, `web.math.pmf.unizg.hr`, accessed 28 July 2026. The Formal Conjectures Authors, [*FormalConjectures.ErdosProblems.`251`*](https://github.com/google-deepmind/formal-conjectures/blob/f776d2f2039351b00737ffcafb9d7d7666e1d9af/FormalConjectures/ErdosProblems/251.lean), Lean source at commit `f776d2f`, 2025, accessed 28 July 2026.

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.
