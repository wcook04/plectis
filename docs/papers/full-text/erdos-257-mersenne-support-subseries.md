<a id="erdos-257-mersenne-support-subseries"></a>

# Weighted Support Criteria for Reciprocal Mersenne Subseries

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

For a finite nonempty set $`P`$ of primes, let $`h(a)`$ be the $`P`$-part of $`a`$. We prove that $`\sum_{a\in A}h(a)/[a(2^{h(a)}-1)]<\infty`$ makes $`\sum_{a\in B}(b^a-1)^{-1}`$ irrational for every integer $`b\ge2`$ and every infinite $`B\subseteq A`$. The condition permits a divergent reciprocal sum, but excludes full support and all odd exponents. The proof averages positive displacements over multiples of a finite modulus; a second, dyadic average controls incomplete periods. We also prove the reciprocal-summable criterion stated by Erdős and a common-average extension using positive divisor covers. Supplementary results concern finite denominators and conditional rational-membership tests, not a resolution of the universal problem.

<a id="sec:problem"></a>

# Introduction and main results

For $`A\subseteq\mathbb{N}_{>0}`$ and $`b>1`$, put $`X_A(b)=\sum_{a\in A}(b^a-1)^{-1}`$. This converges because $`(b^a-1)^{-1}\le b^{1-a}/(b-1)`$. For a finite set $`P`$ of primes, the *$`P`$-part* of $`a`$ is $`h(a)=\prod_{p\in P}p^{v_p(a)}`$, where $`v_p(a)`$ is the exponent of $`p`$ in $`a`$. For example, if $`P=\{2\}`$ and $`a=2^km`$ with $`m`$ odd, then $`h(a)=2^k`$.

<div id="res:weighted-support" class="theorem">

**Theorem 1** (a weighted condition on the support). *Let $`b\ge2`$ be an integer, let $`A\subseteq\mathbb{N}_{>0}`$ be infinite, and let $`P`$ be a finite nonempty set of primes. Set $`h(a)=\prod_{p\in P}p^{v_p(a)}`$. If
``` math
\begin{equation}
\label{eq:weighted-fixed-base}
 W_{b,P}(A):=\sum_{a\in A}
 \frac{h(a)}{a(b^{h(a)}-1)}<\infty,
\end{equation}
```
then $`X_A(b)`$ is irrational. In particular, the base-two condition
``` math
\begin{equation*}
\label{eq:weighted-return}
 \sum_{a\in A}\frac{h(a)}{a(2^{h(a)}-1)}<\infty
 \tag{W}
\end{equation*}
```
implies that $`X_A(b)`$ is irrational for every integer $`b\ge2`$. Both conclusions are hereditary under passage to infinite subsets.*

</div>

Lean: [divisibility weighted claim](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos257/PaperCompleteR8/WeightedReturn.lean#L120), [finite prime weighted fixed base hereditary](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos257/PaperCompleteR8/WeightedHereditaryClaim.lean#L31).

For $`P=\{2\}`$, the summand in <a href="#eq:weighted-fixed-base" data-reference-type="eqref" data-reference="eq:weighted-fixed-base">[eq:weighted-fixed-base]</a> is $`1/[m(b^{2^k}-1)]`$ when $`a=2^km`$ and $`m`$ is odd. Large powers of $`2`$ can therefore compensate for large reciprocal mass among the odd factors. The example following the proof in Section <a href="#sec:eight-return-extensions" data-reference-type="ref" data-reference="sec:eight-return-extensions">3</a> makes this precise. The reciprocal mass at each fixed $`P`$-part must be finite, and its weighted sum over the parts must converge; the first requirement alone is insufficient. Section 1.2 of the companion, *Reciprocal Mersenne Subseries*, gives the decomposition and a separating example.

For every finite $`P`$, full support and all odd exponents fail the condition: the integers coprime to $`2\prod_{p\in P}p`$ have $`h(a)=1`$ and divergent reciprocal sum, by inclusion–exclusion. The full set of primes fails too, since the primes outside $`P`$ contribute $`1/[a(b-1)]`$. These are limitations of this criterion, not assertions of rationality. By contrast, $`h/(2^h-1)\le1`$ shows that it includes every reciprocal-summable support.

<div id="res:reciprocal-support" class="theorem">

**Theorem 2** (reciprocal-summable supports). *Let $`A\subseteq\mathbb{N}_{>0}`$ be infinite. If
``` math
\sum_{a\in A}\frac1a<\infty,
```
then $`X_A(b)`$ is irrational for every integer $`b\ge2`$.*

</div>

Lean: [irrational erdos support series of summable reciprocal](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/Erdos249257/AllBaseReciprocalSupportIrrationality.lean#L395).

Erdős stated Theorem <a href="#res:reciprocal-support" data-reference-type="ref" data-reference="res:reciprocal-support">2</a>, including the all-base conclusion, after proving its pairwise-coprime case \[erdos1968, p. 222\]. We give a complete averaging proof of that stated extension. Erdős also discussed weakening reciprocal summability \[erdos1968, pp. 222, 226\]; no identification of the weighted condition with his suggested conditions is asserted.

The proof uses a positive displacement that rationality would separate from zero. Erdős likewise points to fractional parts of powers times the series value \[erdos1968, p. 226\]. For an integer $`b\ge2`$, infinite $`A`$ and $`N>0`$, division of $`N`$ by each $`a\in A`$ gives
``` math
0<\Delta_{b,A}(N)
 :=\sum_{a\in A}\frac{b^{N\bmod a}-1}{b^a-1}
 =(b^N-1)X_A(b)-J_{b,A}(N),\qquad J_{b,A}(N)\in\mathbb{Z}.
 \label{eq:intro-displacement}\tag{D}
```
The integer term is explicitly
``` math
J_{b,A}(N)=\sum_{\substack{a\in A\\a\le N}}
             \sum_{j=1}^{\lfloor N/a\rfloor}b^{N-ja}.
```
The identity holds for every real $`b>1`$; integrality uses the integer-base hypothesis. Every summand in the displacement is nonnegative, and an exponent $`a>N`$ gives a positive summand; such an exponent exists because $`A`$ is infinite. Rationality $`X_A(b)=p/q`$ would force every positive displacement to be at least $`1/q`$. The proof makes these positive displacements arbitrarily small by averaging along multiples of a growing divisibility modulus.

For an application of Theorem <a href="#res:reciprocal-support" data-reference-type="ref" data-reference="res:reciprocal-support">2</a>, call an integer *powerful* when every prime dividing it occurs to exponent at least two. Every such integer can be written as $`u^2v^3`$, so
``` math
\sum_{\substack{a\ge1\\a\text{ powerful}}}\frac1a
 \le\zeta(2)\zeta(3)<\infty.
```
Thus arbitrary infinite thinnings of the powerful integers are included. For full perfect-power supports, compare Duverney–Tachiya \[duverneytachiya, Corollary 1.2, p. 4\] and the earlier linear-independence results of Luca–Tachiya \[lucatachiya2014independence\].

<div id="res:problem" class="problem">

**Problem 3** (Erdős \#257). Is $`X_A(2)`$ irrational for every infinite $`A\subseteq\mathbb{N}_{>0}`$?

</div>

Sections <a href="#sec:reciprocal-support" data-reference-type="ref" data-reference="sec:reciprocal-support">2</a>–<a href="#sec:eight-return-extensions" data-reference-type="ref" data-reference="sec:eight-return-extensions">3</a> prove the support criteria: first the simpler reciprocal-summable argument, then the weighted theorem and its common-average extension. The remaining sections give supplementary finite-denominator and rational-membership results. None is needed for the weighted proof.

The coefficient sequence throughout is the divisor transform of the indicator function of the support:
``` math
\begin{equation}
 c_A(n)=\#\{a\in A:a\mid n\},\qquad
 X_A(b)=\sum_{n\ge1}\frac{c_A(n)}{b^n}.
 \label{eq:incidence}
\end{equation}
```
Tonelli’s theorem applied to $`(b^a-1)^{-1}=\sum_{j\ge1}b^{-aj}`$ proves the identity. Moreover $`0\le c_A(n)\le\tau(n)`$. The selector $`1_A`$ is Boolean; its divisor transform $`c_A`$ generally is not.

<a id="sec:reciprocal-support"></a>

# Reciprocal-summable supports at every integer base

A shift divisible by each exponent in a finite part of $`A`$ makes those terms of the displacement vanish. We then average over such shifts. Reciprocal summability controls the terms outside that finite part without requiring a common period for the whole support.

Fix the integer base $`b\ge2`$ and put
``` math
w_{b,d}(N)=\frac{b^{N\bmod d}}{b^d-1},\qquad
 T_N^{(b)}=\sum_{d\in A}w_{b,d}(N).
```
Then $`T_N^{(b)}-T_0^{(b)}=\Delta_{b,A}(N)`$. For a fixed positive integer $`Q`$, the orbit of $`Q`$ modulo $`d`$ consists of $`d/g`$ residues, where $`g=(Q,d)`$. Summing the geometric progression gives
``` math
\begin{equation}
 M_{Q,b}(d):=\lim_{X\to\infty}\frac1X\sum_{m=1}^Xw_{b,d}(Qm)
 =\frac{g}{d(b^g-1)}\le\frac1d.
 \label{eq:gcd-orbit-mean}
\end{equation}
```
For example, at $`b=2`$, $`Q=4`$ and $`d=6`$, the orbit is $`4,2,0`$ modulo $`6`$. Its mean atom is $`(16+4+1)/(3\cdot63)=1/9`$, whereas its zero-shift atom is $`1/63`$. If $`6\mid Q`$, the orbit instead stays at zero and the mean is exactly $`1/63`$. Making an exponent divide $`Q`$ therefore changes its orbit mean. The infinite tail still requires the bound that follows. The passage from individual atoms to their infinite sum needs a uniform bound. Counting positive multiples of $`d`$ gives
``` math
\begin{align*}
 \frac1X\sum_{m=1}^Xw_{b,d}(Qm)
 &=\sum_{r\ge1}b^{-r}
       \frac{\#\{1\le m\le X:d\mid Qm+r\}}X\\
 &\le\sum_{r\ge1}b^{-r}\frac{Q+r}{d}
 =\frac{Q/(b-1)+b/(b-1)^2}{d}\le\frac{Q+2}{d}.
\end{align*}
```
Indeed, the counted multiples are distinct and at most $`QX+r`$. For this fixed $`Q`$, the majorant $`(Q+2)/d`$ is summable over $`A`$. Dominated convergence therefore takes the observation-length limit inside the sum over $`d`$, giving the Cesàro mean $`\sum_{d\in A}M_{Q,b}(d)`$. This majorant is not uniform in growing $`Q`$.

Next let $`Q_t=\operatorname{lcm}(1,\ldots,t)`$. For each fixed $`d`$, eventually $`d\mid Q_t`$ and $`M_{Q_t,b}(d)=(b^d-1)^{-1}`$. A second dominated-convergence argument, using $`M_{Q_t,b}(d)\le1/d`$, yields
``` math
\begin{equation}
 \sum_{d\in A}M_{Q_t,b}(d)\longrightarrow X_A(b).
 \label{eq:lcm-prefix-orbit-limit}
\end{equation}
```
Thus the limiting averages of the nonnegative displacements $`\Delta_{b,A}(Q_tm)`$ tend to zero. Choose $`t`$, then a sufficiently long finite average, and finally a term no larger than that average. This gives arbitrarily small positive displacements, contradicting the rational lattice in <a href="#eq:intro-displacement" data-reference-type="eqref" data-reference="eq:intro-displacement">[eq:intro-displacement]</a>. This proves Theorem <a href="#res:reciprocal-support" data-reference-type="ref" data-reference="res:reciprocal-support">2</a> directly at every integer base.

The order of limits is essential: the observation length tends to infinity with the modulus fixed, and only then does the modulus increase. Reciprocal summability controls both interchanges. The exact all-base result, with hypotheses $`b\ge2`$, infinitude of $`A`$, and summability of $`a\mapsto
\mathbf1_A(a)/a`$, is kernel-checked as [`irrational_erdosSupportSeries_of_summable_reciprocal`](https://github.com/wcook04/plectis-erdos/blob/065e09523286894dfb57ba205e69666843817009/lean/Erdos249257/AllBaseReciprocalSupportIrrationality.lean#L395).

<a id="sec:eight-return-extensions"></a>

# Extensions beyond reciprocal summability

The weighted condition can hold when $`\sum_{a\in A}1/a`$ diverges, so the previous proof’s summable majorant is no longer available. We instead bound finite averages for each exponent and then average over dyadic observation lengths. This second average controls the incomplete periods. Estimate (S) will also allow the divisor-cover argument to use these same observation lengths.

<a id="proof-of-the-weighted-criterion"></a>

## Proof of the weighted criterion

For a finite nonempty prime set $`P`$, put $`h(a)=\prod_{p\in P}p^{v_p(a)}`$.

We prove the fixed-base assertion of Theorem <a href="#res:weighted-support" data-reference-type="ref" data-reference="res:weighted-support">1</a>. The base-two condition implies every integer-base instance because $`b^{h(a)}-1\ge2^{h(a)}-1`$.

<div class="proof">

*Proof.* The rational-lattice obstruction is <a href="#eq:intro-displacement" data-reference-type="eqref" data-reference="eq:intro-displacement">[eq:intro-displacement]</a>: if $`X_A(b)=p/q`$, every positive $`\Delta_{b,A}(m)`$ is at least $`1/q`$. For $`d_a(m)=(b^{m\bmod a}-1)/(b^a-1)`$ and $`g=(Q,a)`$, one complete orbit of $`Qm\bmod a`$ gives, for $`Q,a,T\ge1`$,
``` math
\begin{equation}
\label{eq:weighted-finite-orbit}
 \frac1T\sum_{t=1}^T d_a(tQ)
 \le \frac{g}{a(b^g-1)}+\frac1{T(b^g-1)}.
\end{equation}
```
Indeed, the orbit has length $`a/g`$ and $`\sum_{t=1}^{a/g}b^{tQ\bmod a}/(b^a-1)=1/(b^g-1)`$; an incomplete orbit costs at most one more complete orbit. Also, for $`Y=QT`$,
``` math
\begin{equation}
\label{eq:weighted-outer-short}
 \frac1T\sum_{t=1}^T\sum_{\substack{a\in A\\a>Y}}d_a(tQ)
 \le\frac4T,
\end{equation}
```
because $`d_a(tQ)\le2\,2^{tQ-a}`$ when $`a>QT`$ and $`\sum_{t=1}^T2^{tQ-QT}\le2`$.

The incomplete-orbit errors are controlled by a second finite average. For integers $`Q,M\ge1`$ and $`\alpha_a\ge0`$ with $`\sum_a\alpha_a/a<\infty`$,
``` math
\begin{equation}
\label{eq:weighted-dyadic-short}
 \sum_{j=M}^{2M-1}\frac1{2^j}\sum_{a\le Q2^j}\alpha_a
 \le2Q\sum_{a\ge1}\frac{\alpha_a}{a};
\end{equation}
```
for each fixed $`a`$, the admissible geometric tail is at most $`2Q/a`$.

Fix $`\varepsilon>0`$. Choose finite nonempty $`F\subseteq A`$ so that the <a href="#eq:weighted-fixed-base" data-reference-type="eqref" data-reference="eq:weighted-fixed-base">[eq:weighted-fixed-base]</a> mass outside $`F`$ is below $`\varepsilon`$, and let $`L`$ be any fixed positive common multiple of $`F`$. With $`p_*=\max P`$, $`r=|P|`$, and large $`H\ge2p_*`$, set
``` math
Q=L\prod_{p\in P}p^{\lfloor\log_pH\rfloor},\qquad
 G=\left\lfloor\frac H{p_*}\right\rfloor.
```
For $`a\in F`$ the displacement term vanishes, since $`a\mid Q`$. For $`a\notin F`$ with $`h(a)\le H`$, we have $`h(a)\mid Q`$ and hence $`(Q,a)\ge h(a)`$. The complete-period term in <a href="#eq:weighted-finite-orbit" data-reference-type="eqref" data-reference="eq:weighted-finite-orbit">[eq:weighted-finite-orbit]</a> is therefore bounded by $`h(a)/[a(b^{h(a)}-1)]`$, using the monotonicity of $`n/(b^n-1)`$. Their sum is less than $`\varepsilon`$; their incomplete-period errors will be handled by the dyadic average.

For $`h(a)>H`$, we instead have $`(Q,a)\ge G`$. Sum the complete-period bounds over $`a\le QT`$, using $`\sum_{a\le QT}1/a\le1+\log(QT)`$. There are at most $`QT`$ incomplete-period terms, each at most $`1/[T(b^G-1)]`$. The total contribution from these exponents is thus at most
``` math
\frac{G(1+\log(QT))+Q}{b^G-1}.
```
For the gcd claim, either every $`P`$-prime-power component of $`h(a)`$ is at most $`H`$, in which case $`h(a)\mid Q`$, or some $`p^{v_p(a)}>H`$ contributes $`p^{\lfloor\log_pH\rfloor}>H/p\ge H/p_*\ge G`$ to the gcd. The second averaging length must make both $`Q/M`$ and $`GM/b^G`$ small. Since $`Q`$ grows only polynomially in $`H`$ and $`G`$ grows linearly, $`M=\lfloor b^{G/2}\rfloor`$ lies between these two scales. Combining the preceding estimates with <a href="#eq:weighted-outer-short" data-reference-type="eqref" data-reference="eq:weighted-outer-short">[eq:weighted-outer-short]</a>, averaging over $`T=2^j`$ for $`M\le j<2M`$, and using <a href="#eq:weighted-dyadic-short" data-reference-type="eqref" data-reference="eq:weighted-dyadic-short">[eq:weighted-dyadic-short]</a> with $`\alpha_a={\bf1}_A(a)/(b^{h(a)}-1)`$ yields
``` math
\begin{equation}
\label{eq:weighted-main-bound}
 \frac1M\sum_{j=M}^{2M-1}\frac1{2^j}
 \sum_{t=1}^{2^j}\Delta_{b,A}(tQ)
 \le \varepsilon+\frac{2QW_{b,P}(A)}M
 +\frac{G(1+\log Q+2M\log2)+Q}{b^G-1}+4\,2^{-M}.
\end{equation}
```
The order of choices is important. First fix $`\varepsilon`$ and choose $`F`$ and its common multiple $`L`$; only then let $`H\to\infty`$. With $`L`$ fixed, $`Q\le LH^r`$, $`G=H/p_*+O(1)`$ and $`M\asymp b^{G/2}`$, so every term after $`\varepsilon`$ tends to zero. This produces arbitrarily small displacements, but gives no specified decay rate in the index $`N=Qt`$. The left side is a finite average of positive displacements, so one is below $`2\varepsilon`$ for large $`H`$. Since $`\varepsilon`$ is arbitrary, this contradicts the lower bound $`1/q`$ under rationality. Finally $`W_{b,P}(A)\le W_{2,P}(A)`$ for $`b\ge2`$, and weighted mass decreases on taking subsets. ◻

</div>

The exact interface of Theorem <a href="#res:weighted-support" data-reference-type="ref" data-reference="res:weighted-support">1</a>, including its fixed-base conclusion and hereditary all-base clause, is kernel-checked as [`divisibilityWeightedClaim`](https://github.com/wcook04/plectis-erdos/blob/065e09523286894dfb57ba205e69666843817009/lean/ErdosProblems/Erdos257/PaperCompleteR8/WeightedReturn.lean#L99).

<a id="an-example-beyond-reciprocal-summability"></a>

## An example beyond reciprocal summability

The hypothesis is genuinely weaker than reciprocal summability. Let
``` math
A_\star=\{2^k m:k\ge1,\ m\text{ odd},\ m\le2^{2^k}\}.
```
Write $`H_N=\sum_{m=1}^N1/m`$ and $`N_k=2^{2^k}`$. The reciprocal mass in the $`k`$th layer is
``` math
\rho_k=2^{-k}\sum_{\substack{m\le N_k\\m\text{ odd}}}\frac1m
 =2^{-k}\bigl(H_{N_k}-\tfrac12H_{N_k/2}\bigr)
 \longrightarrow\frac{\log2}{2},
```
so $`\sum_{a\in A_\star}1/a`$ diverges. For $`P=\{2\}`$ the weighted mass of that layer is
``` math
\frac{2^k}{2^{2^k}-1}\rho_k.
```
Since $`H_N\le1+\log N`$, one has $`\rho_k\le2^{-k}+\log2`$. The weighted terms are therefore at most $`(1+2^k\log2)2^{1-2^k}`$, a summable sequence. Thus every infinite subset of $`A_\star`$ has irrational $`X_A(b)`$ at every integer base, although $`\sum_{a\in A_\star}1/a`$ diverges.

Both proofs select a term no larger than a finite average. For a related selection step on arithmetic progressions, see Duverney–Tachiya \[duverneytachiya, Section 2, (2.3)–(2.9)\]. The sparse-coefficient criteria of Kaneko–Suzuki–Tachiya \[kanekosuzukitachiya, Theorems 1 and 3\] do not apply directly to $`c_A`$: for nonempty $`A`$, it is positive on every multiple of $`\min A`$. The companion, Section 1.2, gives the counting argument and distinguishes their remote-tail average from the displacement used here.

<a id="sec:common-kernel"></a>

## A common finite average for the extensions

To combine the weighted criterion with positive divisor majorants, both arguments must use the same indices. The following estimate supplies that common average; Theorem <a href="#res:mixed-supports" data-reference-type="ref" data-reference="res:mixed-supports">5</a> gives the combination.

For $`1<B\le2`$, positive integers $`L,d,M`$, and an integer $`R\ge0`$, put
``` math
w_{B,d}(n)=\frac{B^{n\bmod d}}{B^d-1},\qquad
 \mathscr D_{L;R,M}F
 =\frac1M\sum_{j=R}^{R+M-1}\frac1{2^j}
      \sum_{m=1}^{2^j}F(Lm).
```
The finite estimate
``` math
\begin{equation*}
 \mathscr D_{L;R,M}w_{B,d}
 \le\frac{1+4L/M}{d(B-1)}
 \tag{S}\label{eq:mixed-finite-kernel}
\end{equation*}
```
equivalently bounds $`(B-1)\mathscr D_{L;R,M}w_{B,d}`$ by $`(1+4L/M)/d`$. This normalized bound is uniform as $`B\downarrow1`$; the unnormalized right side grows like $`(B-1)^{-1}`$. The ratio $`L/M`$ measures the cost of incomplete modular periods.

To prove it, fix $`T=2^j`$ and average over $`1\le m\le T`$. When $`d\le LT`$, the complete orbit has length $`d/g`$, with $`g=(L,d)`$, and total weight $`1/(B^g-1)`$. Complete cycles and one remaining piece give
``` math
\frac1T\sum_{m=1}^T w_{B,d}(Lm)
 \le\frac{g}{d(B^g-1)}+\frac1{T(B^g-1)}
 \le\frac1{d(B-1)}+\frac1{T(B-1)}.
```
Across dyadic lengths satisfying $`d\le L2^j`$, the reciprocal-length errors sum to at most $`2L/[d(B-1)]`$. When $`d>2LT`$, there is no wrap and $`2Lm\le d-1`$; hence $`\sum_{i=0}^{d-1}B^i\ge dB^{(d-1)/2}\ge dB^{Lm}`$. Each atom is then at most $`1/[d(B-1)]`$. Finally, at most one dyadic length satisfies $`LT<d\le2LT`$. For that length the geometric sum and convexity give
``` math
\frac1T\sum_{m=1}^T w_{B,d}(Lm)
 =\frac{B^L}{T(B^L-1)}\frac{B^{LT}-1}{B^d-1}
 \le\frac{LB^L}{d(B^L-1)}
 \le\frac{2L}{d(B-1)}.
```
For the last inequality, use $`(B^L-1)/(B-1)=\sum_{i=0}^{L-1}B^i\ge B^{L-1}`$ and $`B\le2`$. Summing the main terms and the two error bounds proves <a href="#eq:mixed-finite-kernel" data-reference-type="eqref" data-reference="eq:mixed-finite-kernel">[eq:mixed-finite-kernel]</a>. The release snapshot contains a proof body for the full estimate in [the finite averaging estimate](https://github.com/wcook04/plectis-erdos-lean/blob/52f29ad173b04e3bac941b3663f2b9aebe5de0bb/ErdosProblems/Erdos257/PaperCompleteR8/DyadicKernel.lean#L207). Its complete-cycle and no-wrap scalar ingredients are in [the scalar averaging estimates](https://github.com/wcook04/plectis-erdos-lean/blob/52f29ad173b04e3bac941b3663f2b9aebe5de0bb/ErdosProblems/Erdos257/PaperCompleteR7/CoverKernel.lean#L130). Their formal-checking status is described in Appendix <a href="#app:sources" data-reference-type="ref" data-reference="app:sources">11</a>. Nonnegative interchange permits summation against any coefficients $`c_d`$ with $`\sum_dc_d/d<\infty`$.

<a id="positive-divisor-majorants"></a>

## Positive divisor majorants

For a finite set $`F`$, write $`f_F(n)=\#\{a\in F:a\mid n\}`$. We bound a fractional power of this count by a nonnegative sum over divisors of $`n`$. The inequality must hold for every positive integer $`n`$, not just on average.

<div id="thm:variable-fractional-cover" class="theorem">

**Theorem 4** (a summable divisor-cover criterion). *For each $`j\ge1`$, let $`F_j\subseteq\mathbb{N}_{>0}`$ be finite, let $`0<\alpha_j\le1`$, and let $`c_{j,d}\ge0`$ satisfy
``` math
f_{F_j}(n)^{\alpha_j}\le\sum_{d\mid n}c_{j,d}\quad(n\ge1).
```
Set $`C_j=\sum_{d\ge1}c_{j,d}/d`$. If
``` math
\begin{equation*}
 \sum_{j\ge1}\frac{C_j2^{j\alpha_j}}{2^{\alpha_j}-1}<\infty,
 \tag{V}\label{eq:strengthened-cover}
\end{equation*}
```
then $`X_A(b)`$ is irrational for every infinite $`A\subseteq\bigcup_jF_j`$ and every integer $`b\ge2`$.*

</div>

Lean: [strengthened positive cover claim](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos257/PaperCompleteR8/PositiveCoverReturn.lean#L241).

Every finite set admits a majorant of the required kind: take $`\alpha_j=1`$ and $`c_{j,d}=\mathbf1_{F_j}(d)`$. The restriction is that the costs of the whole sequence satisfy <a href="#eq:strengthened-cover" data-reference-type="eqref" data-reference="eq:strengthened-cover">[eq:strengthened-cover]</a>. For a simple admissible family, take $`F_j=\{4^j\}`$, $`\alpha_j=1`$, and $`c_{j,4^j}=1`$, with all other coefficients zero. Then $`C_j=4^{-j}`$ and the series in <a href="#eq:strengthened-cover" data-reference-type="eqref" data-reference="eq:strengthened-cover">[eq:strengthened-cover]</a> is $`\sum_j2^{-j}`$. The logarithmic obstruction below gives a necessary condition for such a cover.

<div class="proof">

*Proof.* Write $`B_j=2^{\alpha_j}`$ and
``` math
U_j(N)=\sum_{r\ge1}2^{-r}f_{F_j}(N+r),\qquad
 V_j(N)=\sum_{d\ge1}c_{j,d}w_{B_j,d}(N).
```
The choice $`B_j=2^{\alpha_j}`$ matches the decay after taking a fractional power. Subadditivity and the divisor majorant give
``` math
U_j(N)^{\alpha_j}
 \le\sum_{r\ge1}B_j^{-r}f_{F_j}(N+r)^{\alpha_j}
 \le\sum_{d\ge1}c_{j,d}
       \sum_{\substack{r\ge1\\d\mid N+r}}B_j^{-r}
 =V_j(N).
```
The last identity sums a geometric progression in each residue class. The geometric-series identity also gives
``` math
\Delta_{2,F_j}(N)=U_j(N)-X_{F_j}(2)\le U_j(N).
```
Consequently, once the first $`J`$ finite sets have zero displacement, nonnegativity bounds the displacement of their union by $`\sum_{j>J}U_j(N)`$.

Fix $`\varepsilon>0`$, set $`t_j=\varepsilon2^{-j}`$, and choose $`J`$ with
``` math
K_J:=\sum_{j>J}\frac{C_jt_j^{-\alpha_j}}{B_j-1}<\frac14.
```
This is possible since $`\varepsilon^{-\alpha_j}\le\max(1,\varepsilon^{-1})`$. Choose $`L`$ divisible by every member of the first $`J`$ finite sets. Equation <a href="#eq:mixed-finite-kernel" data-reference-type="eqref" data-reference="eq:mixed-finite-kernel">[eq:mixed-finite-kernel]</a> bounds the finite mean of $`S_J(N):=\sum_{j>J}t_j^{-\alpha_j}V_j(N)`$ by $`(1+4L/M)K_J<1/2`$ whenever $`M\ge4L`$. One sample therefore has $`S_J(N)<1`$, forcing $`U_j(N)<t_j`$ for every $`j>J`$. Every exponent in the first $`J`$ finite sets divides $`L`$, so those terms have zero displacement. Consequently,
``` math
0<\Delta_{2,A}(N)\le\sum_{j>J}U_j(N)\le\varepsilon.
```
The fixed rational lattice excludes rationality at base two. For $`0\le r<d`$, the function $`(b^r-1)/(b^d-1)`$ is nonincreasing on $`b>1`$. For $`r>0`$, cancel $`b-1`$ and write it as $`A(b)/(A(b)+C(b))`$, where $`A(b)=\sum_{i<r}b^i`$ and $`C(b)=\sum_{r\le j<d}b^j`$. Its derivative has the sign of $`A'C-AC'=\sum_{i<r\le j<d}(i-j)b^{i+j-1}<0`$. Thus $`\Delta_{b,A}(N)\le\Delta_{2,A}(N)`$ for every real $`b\ge2`$; when $`b`$ is an integer, the same rational-lattice argument applies. Any prescribed positive divisor can be included in $`L`$, so the witnesses can also be required to be arbitrarily large. ◻

</div>

The same proof permits any positive weights $`\eta_j`$ with $`\sum_j\eta_j=1`$: replace $`2^{j\alpha_j}`$ in <a href="#eq:strengthened-cover" data-reference-type="eqref" data-reference="eq:strengthened-cover">[eq:strengthened-cover]</a> by $`\eta_j^{-\alpha_j}`$ and take $`t_j=\varepsilon\eta_j`$. The earlier condition $`\sum_jC_j2^{j\alpha_j}2^{\alpha_j}/(2^{\alpha_j}-1)^2<\infty`$ implies <a href="#eq:strengthened-cover" data-reference-type="eqref" data-reference="eq:strengthened-cover">[eq:strengthened-cover]</a>, since each old summand is the new one multiplied by $`2^{\alpha_j}/(2^{\alpha_j}-1)>1`$. This proves inclusion of the hypotheses for a given cover, not strict inclusion of the resulting support classes after optimisation over all covers. No separating construction is proved here.

<a id="what-every-positive-cover-must-pay"></a>

## What every positive cover must pay

A necessary lower bound on the cost holds for every choice of cover. For finite $`F`$, write $`\mathbb E_F`$ for the uniform mean modulo $`\operatorname{lcm}(F)`$, with $`\operatorname{lcm}(\varnothing)=1`$ and $`f_{\varnothing}=0`$. More generally allow weights $`\eta_j>0`$ with $`\sum_j\eta_j=1`$, and set
``` math
K=\sum_j\frac{C_j\eta_j^{-\alpha_j}}{2^{\alpha_j}-1},\qquad
 \Psi(0)=0,\quad
 \Psi(t)=\inf_{0<\alpha\le1}\frac{t^\alpha}{2^\alpha-1}\quad(t\ge1).
```
Here $`\log^+t=\log\max\{1,t\}`$. For every finite $`F`$ contained in $`\bigcup_jF_j`$,
``` math
\begin{equation}
 K\ge\mathbb E_F\Psi(f_F)\ge e\,\mathbb E_F\log^+f_F.
 \label{eq:cover-log-obstruction}
\end{equation}
```
Indeed, at a point where $`f_F(n)=t>0`$, some covering set $`F_j`$ satisfies $`f_{F_j}(n)\ge\eta_jt`$. Otherwise summing contradicts coverage. The corresponding weighted majorant is at least $`\Psi(t)`$. Average first over $`1\le n\le X`$, using $`\lfloor X/d\rfloor/X\le1/d`$, and let $`X\to\infty`$. The periodic left side tends to $`\mathbb E_F\Psi(f_F)`$, proving the first inequality; the covering moduli need not divide $`\operatorname{lcm}(F)`$. Convexity gives $`2^\alpha-1\le\alpha`$, and $`e^u/u\ge e`$ proves the second. Those scalar steps have corresponding source bodies in [the scalar averaging estimates, lines 170–214](https://github.com/wcook04/plectis-erdos-lean/blob/52f29ad173b04e3bac941b3663f2b9aebe5de0bb/ErdosProblems/Erdos257/PaperCompleteR7/CoverKernel.lean#L170), including the bound $`t^\alpha/(2^\alpha-1)\ge e\log t`$. This does not by itself formalise the assembled averaging argument, and no fresh Lean verification is claimed.

This bound survives optimisation over all covers. For $`F(q,P)=\{qd:d\mid\prod_{p\in P}p\}`$, where $`q\ge2`$ and no $`p\in P`$ divides $`q`$, put $`S=\sum_{p\in P}1/p`$. If $`S\ge1`$, the infimum $`K_*`$ over finite or countable covers satisfies
``` math
\begin{equation}
 \frac{e(S-1)}q\le K_*\bigl(F(q,P)\bigr)\le\frac{eS}q.
 \label{eq:optimal-cube-cost}
\end{equation}
```
For the lower bound, condition on $`q\mid n`$ and write $`f_F(n)=2^Z`$. The Chinese remainder theorem gives $`\mathbb EZ=S`$. For $`z\ge0`$ and $`v=\alpha\log2>0`$,
``` math
\frac{2^{\alpha z}}{2^\alpha-1}
 \ge\frac{e^{(z-1)v}}v\ge e(z-1)\quad(z>1);
```
for $`0\le z\le1`$ the claimed lower bound is nonpositive. Thus $`\Psi(2^z)\ge e(z-1)`$. For the upper bound, use the one-set cover with $`z=1/S`$ and $`\alpha=\log_2(1+z)`$; its exact positive expansion has cost
``` math
\frac1{qz}\prod_{p\in P}(1+z/p)\le\frac{eS}q.
```
In particular, $`1-1/S\le qK_*(F(q,P))/(eS)\le1`$. Thus $`K_*(F(q,P))\sim eS/q`$ as $`S\to\infty`$, uniformly over the permitted choices of $`q`$ and $`P`$.

The logarithmic lower bound is not a converse: replacing a fractional majorant by a logarithmic one need not control averages along the multiples of a prescribed modulus. A counterexample and the distinct bound for ordinary initial intervals are proved in the companion, Section 13, and in \[endpoint2026, Theorem 1, Corollary 3 and Proposition 4\]. Those arguments concern finite functionals, not a comparison of the infinite-support irrationality classes.

The source [constructs a weighted support with no strengthened cover](https://github.com/wcook04/plectis-erdos-lean/blob/52f29ad173b04e3bac941b3663f2b9aebe5de0bb/ErdosProblems/Erdos257/PaperCompleteR8/AnalyticSeparationReturn.lean#L16). The reverse separation is not established here, so two-way incomparability is not asserted. This source statement is distinct from the finite-functional counterexample just cited.

<a id="combining-the-two-support-criteria"></a>

## Combining the two support criteria

Separate small-displacement witnesses need not occur at the same index. For example, a sequence small only at even indices and one small only at odd indices need never have a small sum. The useful feature of (S) is its uniformity in the moving modulus: the positive-cover argument can use the exact observation window selected by the weighted proof.

<div id="res:mixed-supports" class="theorem">

**Theorem 5** (mixed weighted and cover supports). *Let $`E,V\subseteq\mathbb{N}_{>0}`$. Suppose $`E`$ satisfies <a href="#eq:weighted-return" data-reference-type="eqref" data-reference="eq:weighted-return">[eq:weighted-return]</a> for a finite nonempty prime set $`P`$, and $`V\subseteq\bigcup_jF_j`$ for finite sets and nonnegative majorants satisfying the hypotheses of Theorem <a href="#thm:variable-fractional-cover" data-reference-type="ref" data-reference="thm:variable-fractional-cover">4</a>, with either <a href="#eq:strengthened-cover" data-reference-type="eqref" data-reference="eq:strengthened-cover">[eq:strengthened-cover]</a> or its positive-weight variant. Then $`X_A(b)`$ is irrational for every infinite $`A\subseteq E\cup V`$ and every integer $`b\ge2`$.*

</div>

Lean: [mixed support claim](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos257/PaperCompleteR8/WeightedReturn.lean#L126), [arbitrary weight mixed support all base hereditary](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos257/PaperCompleteR8/ArbitraryWeightMixedClaim.lean#L101).

<div class="proof">

*Proof.* Fix $`\varepsilon>0`$ and an integer $`N_0\ge1`$, and put $`\rho=\varepsilon/3`$. Use the cover notation $`B_j,U_j,V_j`$ above, with $`\eta_j=2^{-j}`$ in the case <a href="#eq:strengthened-cover" data-reference-type="eqref" data-reference="eq:strengthened-cover">[eq:strengthened-cover]</a>. Set $`t_j=\rho\eta_j`$ and choose $`J`$ so that
``` math
K_J=\sum_{j>J}\frac{C_jt_j^{-\alpha_j}}{B_j-1}<\frac1{16}.
```
Choose a finite $`F\subseteq E`$ whose complementary weighted mass is $`\kappa<\rho/16`$. Let $`L`$ be a positive common multiple of $`N_0`$, all members of $`F`$, and all members of the first $`J`$ finite sets. For large $`H`$, choose the same modulus and averaging length as in the base-two weighted proof:
``` math
Q=L\prod_{p\in P}p^{\lfloor\log_pH\rfloor},\qquad
 G=\lfloor H/\max P\rfloor,\qquad M=\lfloor2^{G/2}\rfloor.
```
The finite estimate <a href="#eq:weighted-main-bound" data-reference-type="eqref" data-reference="eq:weighted-main-bound">[eq:weighted-main-bound]</a>, with complementary weighted mass $`\kappa`$, remains valid for this $`L`$: its proof requires only that every member of $`F`$ divide $`L`$. It also applies to finite or empty $`E`$, since positivity was used only after the averaging estimate. Thus
``` math
\mathscr D_{Q;M,M}(\Delta_{2,E}/\rho)<\frac18
```
for sufficiently large $`H`$. For the same finite distribution, (S) and nonnegative interchange give
``` math
\mathscr D_{Q;M,M}S_J\le(1+4Q/M)K_J<\frac18,
 \qquad S_J=\sum_{j>J}t_j^{-\alpha_j}V_j,
```
because $`Q/M\to0`$. Hence some sample $`N=Qm`$ satisfies $`\Delta_{2,E}(N)/\rho+S_J(N)<1`$. At this index the weighted displacement is below $`\rho`$ and $`U_j(N)<t_j`$ for every $`j>J`$. The terms with $`j\le J`$ vanish because their exponents divide $`L`$, and hence divide $`N`$. Therefore
``` math
\Delta_{2,A}(N)\le\Delta_{2,E}(N)+\Delta_{2,V}(N)<2\rho<\varepsilon,
 \qquad N\ge Q\ge L\ge N_0.
```
Overlaps between the supports only improve the inequality. Infinitude of $`A`$ makes its displacement positive. The atom comparison used in the cover proof transfers arbitrarily small displacements to every integer base; the fixed rational lattice then excludes rationality. ◻

</div>

The proof does not establish strict containment of either individual class in the mixed class.

With arbitrary positive cover weights, the class of subsets of such mixed hosts is closed under finite unions and finite changes. For weighted supports use the union of the two finite prime sets: the prime part grows and $`h/(2^h-1)`$ decreases. For two covers, interleave their finite sets with weights $`\eta_j/2`$ and $`\theta_j/2`$; the total cost grows by at most two, since $`2^{\alpha_j}\le2`$. Subsets inherit the same hosts, and finite sets have finite weighted mass. This argument uses the positive-weight variant; it does not silently reindex the dyadic weights in (V). Countable unions require a tail budget. Every prime singleton is admitted, but for the full prime support $`\mathcal P`$ one has $`\Delta_{2,\mathcal P}(N)>1/3`$ for every $`N\ge1`$: indeed $`\sum_{r\ge1}2^{-r}\omega(N+r)\ge1`$, whereas $`X_{\mathcal P}(2)\le\sum_{a\ge2}(2^a-1)^{-1}<2/3`$. Here $`\omega(n)`$ is the number of distinct prime divisors of $`n`$. The reciprocal-summable class is contained in the weighted class, since $`h/(2^h-1)\le1`$. Theorem <a href="#res:reciprocal-support" data-reference-type="ref" data-reference="res:reciprocal-support">2</a> supplies the direct proof of that baseline case.

For comparison, Tao–Teräväinen prove the full-prime case at base $`2`$ \[taoteravainen2025, Theorem 1.3, p. 4\]. The paragraph following it states extensions to prime support at every integer base and to full prime-power support at base $`2`$, leaving the modifications to the reader. It does not treat arbitrary infinite thinnings. The proposed thinning extension is not a premise of any theorem here.

<a id="sec:period"></a>

# Finite-support denominator periods

For a finite nonempty $`F\subseteq\mathbb{N}_{>0}`$, let $`D_F`$ be the positive reduced denominator of $`X_F(b)=\sum_{n\in F}(b^n-1)^{-1}`$. We use $`\operatorname{ord}_1(b)=1`$.

<div id="res:period" class="theorem">

**Theorem 6** (the exact denominator period). *Let $`F\subseteq\mathbb{N}_{>0}`$ be finite and nonempty, let $`b\ge2`$ be an integer, and let $`D_F>0`$ be the denominator of $`X_F(b)`$ in lowest terms. Then $`D_F`$ is coprime to $`b`$, and
``` math
\operatorname{ord}_{D_F}(b)=\operatorname{lcm}\{n:n\in F\}.
```
If moreover $`\operatorname{lcm}(F)\ge2`$, then $`\operatorname{lcm}(F)<D_F`$. We use $`\operatorname{ord}_1(b)=1`$, so the statement includes $`F=\{1\}`$ at $`b=2`$.*

</div>

Lean: [coprime base den finite erdos sum](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/Erdos249257/CertificateKernel.lean#L5221), [finite period noncollapse rat den](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/Erdos249257/CertificateKernel.lean#L5246), [lcm lt den finite erdos sum](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/Erdos249257/CertificateKernel.lean#L5260).

Coprimality is [coprimality of the base and finite-sum denominator](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5221), the order statement is [noncollapse for the reduced rational denominator](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5246), and the size bound is [the lower bound for the finite-sum denominator](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5260). The three clauses are the CertificateKernel declarations just cited; `PaperCompleteR7/Assemblies.lean` is not in this checkout.

Put $`L=\operatorname{lcm}(F)`$. Clearing denominators gives $`D_F\mid b^L-1`$, so the upper divisibility for the order is immediate. For the reverse, choose $`n\ge2`$ maximal under divisibility in $`F`$ and a prime $`\ell\mid\Phi_n(b)`$. If $`e=v_\ell(b^n-1)`$, the full prime power $`\ell^e`$ has $`\operatorname{ord}_{\ell^e}(b)=n`$. Every other selected exponent $`m`$ has $`n\nmid m`$, hence $`v_\ell(b^m-1)<e`$. The $`n`$th summand has uniquely smallest $`\ell`$-adic valuation and cannot cancel. Thus $`\ell^e\mid D_F`$ and $`n\mid\operatorname{ord}_{D_F}(b)`$. Taking all maximal selected exponents proves the order statement; the size bound follows from $`\operatorname{ord}_{D_F}(b)\mid\varphi(D_F)<D_F`$ when $`L\ge2`$. The case $`F=\{1\}`$ has order one directly.

The same unique-valuation argument permits signs $`\pm1`$ on the finite summands. This is an ordinary deduction here, not a claim of a formal proof in the unavailable `SignedFinitePeriodNoncollapse.lean`. The required cyclotomic prime-power fact is proved in Section <a href="#app:elementary-details" data-reference-type="ref" data-reference="app:elementary-details">10</a>. The distinction between primes and prime powers is visible in
``` math
X_{\{2,3\}}(2)=\frac{10}{21},\qquad
 X_{\{2,6\}}(2)=\frac{22}{63}.
```
In both examples $`2`$ has multiplicative order six modulo the denominator. The first combines orders two and three; the second retains the order-six prime power $`9`$, although no prime divisor of $`63`$ has order six. The boundary $`F=\{1\}`$ at base two has $`D_F=L=1`$. These lower denominator bounds give no upper height control for infinite partial sums and do not decide an infinite-support value. By contrast, Van Assche constructs approximants for the full Lambert series and proves both nonvanishing and decay of the associated integer linear forms \[vanassche2001, Lemma 1 and (34)–(35)\]. That approximation mechanism does not follow from denominator survival alone.

<a id="sec:forced"></a>

# Rational values and scaled tails

Suppose $`X_A(2)=p/v`$, where $`p\in\mathbb{Z}`$ and $`v\ge1`$ is an integer. Multiplying the coefficient-series identity by $`v2^N`$ gives
``` math
z_N:=v\sum_{r\ge1}c_A(N+r)2^{-r}
     =2^Np-v\sum_{n=1}^{N}c_A(n)2^{N-n}\in\mathbb{Z}.
```
Separating the first term of the tail then gives $`z_{N+1}=2z_N-vc_A(N+1)`$. All the coefficients $`c_A(n)`$ are divisor counts of the same set $`A`$.

Two elementary facts delimit what these size estimates can show. Assume first that $`A`$ is nonempty and put $`a_0=\min A`$. Then every $`a_0`$ consecutive integers contain a multiple of $`a_0`$, so a divisor-incidence zero window has length at most $`a_0-1`$. If $`A`$ is infinite, choose $`k`$ exponents and a common multiple $`L`$; then $`c_A(L)\ge k`$ and $`\sum_{r\ge1}c_A(L-1+r)2^{-r}\ge k/2`$, by its first term. Both facts hold without rationality. The arithmetic information lies in the lattice and in the compatibility of all coefficients with the same selector.

Precisely, Dirichlet convolution gives $`\mu*c_A=\mathbf1_A`$, where $`\mu`$ is the Möbius function. A putative recurrence with integral forcing must therefore satisfy $`(\mu*c_A)(n)\in\{0,1\}`$ for all $`n`$. The long record gives the integer-recurrence criterion, its telescoping proof, Möbius inversion, and the coefficient-series identity in Theorems 6.105–6.107, under *Bounds for a general coefficient sequence*. The example $`A=\{2\}`$ there has value $`1/3`$. The correspondence permits finite supports; infinitude remains a separate requirement for a counterexample to Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">3</a>.

<a id="sec:map"></a>

# Limits of the small-displacement criterion

The preceding criteria establish irrationality by making $`\Delta_{2,A}(N)`$ positive and arbitrarily small. The particular requirement $`\inf_{N\ge1}\Delta_{2,A}(N)=0`$ fails at full support:
``` math
\Delta_{2,\mathbb{N}_{>0}}(N)
 >(2^N-1)\sum_{a>N}2^{-a}=1-2^{-N}\ge\frac12
 \qquad(N\ge1).
```
The full-support value is nevertheless [irrational](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L8328) \[erdos1948\]. Thus a proof covering full support cannot rely solely on this small-displacement requirement. This does not exclude other integer linear forms or other uses of averaging.

The distinction also appears in the squarefree support. Its series is irrational at every base $`2^j`$, $`j\ge1`$, by Corollary 1.2 and Example 1.1 of Duverney and Tachiya \[duverneytachiya, p. 4\]. Their corollary covers the $`s`$-free products of any pairwise coprime sequence of polynomial growth, and they present it as support for the conjecture of Erdős and Graham stated here as Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">3</a>. The zero-window obstruction for one normalised certificate scheme concerns that scheme’s hypotheses. It gives no obstruction to irrationality of the value. The precise normalisation counterexamples are retained in the long record, together with the complete catalogue of known support families.

A growth-only criterion gives a different class: if $`A=\{c_1<c_2<\cdots\}`$ and $`\limsup_n c_n/2^n=\infty`$, then $`X_A(b)`$ is irrational for every integer $`b\ge2`$ \[erdos1975, Theorem 1\]. The companion, Section 1.7, proves the translation from denominator growth and gives examples showing that this class and reciprocal summability are incomparable. The interval-filling constructions in \[bkkkz2026\] and the freely chosen lacunary denominators of \[vandoornkovac\] are not constructions of subseries of these fixed Mersenne weights.

Prime-incidence arguments require additional care as well: multiplying all prime exponents by $`2`$ creates positive correlations between their divisibility indicators. The exact identity and covariance calculation are in the companion, Section 1.5. Size conditions alone do not supply that independence.

<a id="sec:geometry"></a>

# Unique coding and arithmetic membership

Let $`w_n=(2^n-1)^{-1}`$ and
``` math
\mathcal A=\left\{\sum_{n\ge1}\varepsilon_nw_n:
                   \varepsilon_n\in\{0,1\}\right\},\qquad
 R_N=\sum_{n>N}w_n.
```
The estimate
``` math
2^{-N}<R_N\le2^{-N}+\frac23\,4^{-N}<w_N\qquad(N\ge1)
```
implies uniqueness of the selector. Indeed, at the first differing exponent $`n`$, the difference $`w_n`$ exceeds everything later terms can cancel. The middle inequality follows by writing $`w_n=2^{-n}+4^{-n}/(1-2^{-n})`$ and using $`n\ge N+1\ge2`$. Since every weight exceeds its tail, Hornich’s theorem \[hornich1941\], as proved by Nitecki \[nitecki2013, Theorem 4(1), p. 9\], shows that the coding image is a Cantor set of measure $`\lim_N2^NR_N`$; the estimate above gives $`2^NR_N\to1`$, so $`\lambda(\mathcal A)=1`$. Concretely, fixing the first $`N`$ digits gives $`2^N`$ disjoint closed intervals of length $`R_N`$. These interval unions decrease to $`\mathcal A`$, and continuity of Lebesgue measure from above gives the same limit. Kovač–Tao record this strict-tail inequality and the Cantor conclusion in the fixed-base setting \[kovactao, Remark 4.1\]. For a specified rational target, the useful consequence here is uniqueness of its possible selector. Restricted-set dimension and measure calculations are given in the companion, Section 1.8.

<a id="sec:actual-repairs"></a>

# Greedy membership and an integer recurrence

For $`x\ge0`$, the greedy rule starts with $`r_0=x`$ and, at rank $`n\ge1`$, selects $`n`$ when $`r_{n-1}\ge(2^n-1)^{-1}`$, subtracting that weight if selected. Let $`A_x`$ be the resulting support and $`c_x(n)=\#\{a\in A_x:a\mid n\}`$. Set
``` math
P_0=0,\qquad P_{N+1}=2P_N+c_x(N+1),\qquad
 Q_N=\lfloor2^Nx\rfloor-P_N.
```
Thus $`P_N=\sum_{j=1}^N2^{N-j}c_x(j)`$ is the integer truncation of the Lambert expansion <a href="#eq:incidence" data-reference-type="eqref" data-reference="eq:incidence">[eq:incidence]</a>. It is at most $`2^NX_{A_x}(2)\le2^Nx`$, so $`Q_N\ge0`$. These integer remainders obey
``` math
\begin{equation}
 Q_{N+1}=2Q_N+\beta_N-c_x(N+1),\qquad
 \beta_N=\lfloor2^{N+1}x\rfloor-2\lfloor2^Nx\rfloor\in\{0,1\}.
 \label{eq:actual-repair-recurrence}
\end{equation}
```

<div id="res:general-repair" class="theorem">

**Theorem 7** (membership and nonincreasing integer remainders). *For every real $`x\ge0`$, the following are equivalent:
``` math
\begin{gathered}
 x\in\mathcal A;\\
 \forall K\ge0\ \exists N\ge K:\quad Q_{N+1}\le Q_N;\\
 \forall K\ge0\ \exists N\in[K,K+2\lfloor\sqrt K\rfloor+12):
 \quad Q_{N+1}\le Q_N.
 \end{gathered}
```*

</div>

Lean: [paper general repair criteria](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos257/PaperCompleteR20/GeneralRepairCorrespondence.lean#L15).

The following is an ordinary proof. The supplied solution wrapper `Solutions/PalomarCorpus/E257/GeneralRepairCriterion.lean` contains the two named equivalences, with explicit bridges to the challenge definitions and the same square-root window. Its provenance is the separate release `52f29ad173b0`. This static comparison is not a new replay; a challenge declaration alone is not cited as a proof.

<div class="proof">

*Proof.* Strict domination of each Mersenne weight over its tail implies that a represented target is recovered by the greedy rule. For such a target,
``` math
0\le Q_N\le\sum_{r\ge1}c_x(N+r)2^{-r}
 \le2\sqrt N+4,
```
since $`c_x(n)\le\tau(n)\le2\sqrt n`$ and $`\sqrt{N+r}\le\sqrt N+\sqrt r\le\sqrt N+r`$. Put $`s=\lfloor\sqrt K\rfloor`$ and $`T=2s+12`$. Strict increase at all $`T`$ steps would imply $`Q_{K+T}\ge T`$. But $`K+T<(s+4)^2`$ gives $`Q_{K+T}<2s+12=T`$. This proves the window condition and hence cofinal nonincreases.

Conversely, if $`x\notin\mathcal A`$, then $`\delta=x-X_{A_x}(2)>0`$. The Lambert prefix is at most $`2^NX_{A_x}(2)`$, so $`Q_N\ge2^N\delta-1`$. Eventually this exceeds $`c_x(N+1)\le N+1`$. Equation <a href="#eq:actual-repair-recurrence" data-reference-type="eqref" data-reference="eq:actual-repair-recurrence">[eq:actual-repair-recurrence]</a> then makes $`Q_N`$ strictly increasing, contradicting cofinal nonincreases. ◻

</div>

Theorem <a href="#res:general-repair" data-reference-type="ref" data-reference="res:general-repair">7</a> characterises membership, but it does not locate the required nonincreases for a specified rational target. For $`x=0`$, the selector is empty and $`Q_N=0`$ at every rank. A finite subseries sum is likewise represented and satisfies the criterion. In contrast, $`x=3/4`$ lies strictly between $`R_1<2/3`$ and $`w_1=1`$, so it is not represented and its integer remainders eventually increase strictly. For $`1/2`$ and $`1/21`$, the theorem does not establish which alternative occurs.

The square-root estimate is uniform in the target. There is also a uniform subpower refinement: for each $`0<\varepsilon<1`$, a constant $`C_\varepsilon`$ gives the window length $`\lceil C_\varepsilon(K+1)^\varepsilon\rceil`$. Indeed, $`\tau(n)\le A_\varepsilon n^\varepsilon`$ gives $`Q_N\le D_\varepsilon(N+1)^\varepsilon`$ for represented targets, where $`D_\varepsilon=A_\varepsilon\sum_{r\ge1}r^\varepsilon2^{-r}`$. Choose $`C_\varepsilon>D_\varepsilon(C_\varepsilon+3)^\varepsilon`$, which is possible because $`\varepsilon<1`$. For $`T=\lceil C_\varepsilon(K+1)^\varepsilon\rceil`$, strict increase at all $`T`$ steps would give
``` math
T\le Q_{K+T}\le D_\varepsilon(K+T+1)^\varepsilon
 \le D_\varepsilon(C_\varepsilon+3)^\varepsilon(K+1)^\varepsilon<T,
```
a contradiction. The converse still follows from exponential growth when $`x`$ is not represented. This ordinary argument strengthens the window bound, not the occurrence claim for a specified target; it is separate from the square-root statement in the cited formal source.

At $`x=1/2`$, the digits $`\beta_N`$ vanish for $`N\ge1`$; at $`x=1/21`$ they are six-periodic. Thus the unresolved arithmetic input is
``` math
\begin{equation}
 \boxed{\quad
 \forall K\ \exists N\ge K:\qquad
 c_x(N+1)\ge Q_N+\beta_N,
 \qquad x\in\{1/2,1/21\}.
 \quad}\label{eq:actual-selector-obligation}
\end{equation}
```
Both $`Q_N`$ and $`c_x`$ must arise from the same greedy selector. The long record retains exact counterexamples to fixed-multiplier repair schedules and the finite phase masks used to test them. Neither target is decided here.

<a id="sec:open"></a>

# Further questions

The support theorems give sufficient conditions for irrationality; the tests below instead concern whether a specified rational is a subseries sum. Their hypotheses must be verified for the actual selector or for finite approximants at arbitrarily large depths. An equivalent test does not itself establish membership.

<a id="integer-quotients-for-121."></a>

#### Integer quotients for $`1/21`$.

For $`M,d\ge1`$, set
``` math
q_M(d)=\left\lfloor\frac{2^M}{2^d-1}\right\rfloor,
 \qquad T_M=\left\lfloor\frac{2^M}{21}\right\rfloor.
```
Starting with the integer remainder $`T_{2R}`$, consider $`d=2,\ldots,R`$ in order and subtract $`q_{2R}(d)`$ whenever it does not exceed the current remainder. Let $`D_R`$ be the set of selected exponents and $`s_R`$ the final remainder. Thus
``` math
s_R=T_{2R}-\sum_{d\in D_R}q_{2R}(d)\ge0.
```
A second comparison uses the same integer rule through $`d=2R`$, rather than stopping at $`R`$. For example, $`R=6`$ gives $`T_{12}=195`$, $`D_6=\{5\}`$ and $`s_6=195-\lfloor4096/31\rfloor=63\le64`$. This is one row satisfying the bound below, not evidence that such rows occur at unbounded depths.

Write $`r_n=r_n(1/21)`$ for the real greedy remainder and $`A_{1/21}`$ for its support. The condition $`\mathcal F_{21}`$ means that there exist integers $`n,R_0,K_0\ge0`$ with all of the following properties:

1.  $`r_n>R_n`$, the set of positive exponents outside $`A_{1/21}`$ is finite, and every exponent greater than $`n`$ belongs to $`A_{1/21}`$;

2.  for every $`R\ge R_0`$, the integer rule with target $`T_{2R}`$ and weights $`q_{2R}(2),\ldots,q_{2R}(2R)`$ selects exactly the same exponents as the real greedy rule on $`\{2,\ldots,2R\}`$;

3.  for every $`K\ge K_0`$, the interval $`(K,2K]`$ contains an exponent of $`A_{1/21}`$.

Some of these clauses follow from others once the eventual all-selected behaviour is known. They are written out to match the precise branch used in the formal result. In particular, $`\mathcal F_{21}`$ is not a hypothesis about an arbitrary recurrence with similar coefficients.

<div id="res:one-over-twenty-one-frontier" class="theorem">

**Theorem 8** (integer-quotient tests for $`1/21`$). *The following statements hold.*

1.  *$`1/21\in\mathcal A`$ if and only if $`\mathcal F_{21}`$ does not hold.*

2.  *If there is an unbounded sequence of ranks $`R`$ with $`s_R\le 2^R`$, then $`1/21\in\mathcal A`$.*

3.  *On $`\mathcal F_{21}`$, eventually $`s_R>2^R`$, the boundary rank $`R+1`$ belongs to $`D_{R+1}`$, and, for all sufficiently large $`R`$,
    ``` math
    \begin{aligned}
     D_{R+1}&=D_R\cup\{R+1\},\\
     s_{R+1}&=4s_R+
     \left\lfloor\frac{4(2^{2R}\bmod21)}{21}\right\rfloor
     -2c_{D_R}(2R+1)-c_{D_R}(2R+2)\\
     &\hspace{3em}{}-(2^{R+1}+1).
     \end{aligned}
    ```
    Here $`c_{D_R}(m)=\#\{d\in D_R:d\mid m\}`$.*

</div>

Lean: [one div twenty one mem iff not fatal aligned branch](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/Erdos249257/TwentyOneQuotientGreedy.lean#L3507), [twenty one cofinal even quotient greedy decay of closed rows](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/Erdos249257/TwentyOneQuotientGreedy.lean#L5554), [one div twenty one mem mersenne achievement set of cofinal greedy decay](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/Erdos249257/TwentyOneQuotientGreedy.lean#L5458), [twenty one fatal aligned branch eventually strict supercapacity](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/Erdos249257/TwentyOneQuotientGreedy.lean#L5625), and 1 further declaration in the [coverage section of the companion record](../mirror/erdos257-mersenne-reasoning-surface.pdf#nameddest=coverage).

The equivalence is [the equivalence with failure of $`\mathcal F_{21}`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L3507); the closed-row compactness step is [vanishing scaled error from unbounded closed rows](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5554); and the eventual affine regime is [the eventual affine recurrence on $`\mathcal F_{21}`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5658). The finite uniqueness statement is also explicit: if $`D\subseteq\{2,\ldots,R\}`$ and an integer $`s`$ satisfy $`\sum_{d\in D}q_{2R}(d)+s=T_{2R}`$ with $`0\le s\le2^R`$, then $`D=D_R`$ and $`s=s_R`$. This is the denominator-specific separation theorem ([uniqueness of a finite representation with the stated remainder bound](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L231)). The cited finite crossing lemmas give additional consequences under their alignment hypotheses: an earlier finite prefix cannot occur, and a real greedy exponent must be skipped ([the missing-prefix consequence of an aligned crossing](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5179), [the real greedy skip forced by that crossing](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5223)).

<a id="approximation-to-12-by-finite-supports."></a>

#### Approximation to $`1/2`$ by finite supports.

For $`A\subseteq\{2,\ldots,M\}`$ and $`1\le m\le M`$, define the integer
``` math
K_A(m)=2^{m-1}-\sum_{j=2}^{m}2^{m-j}c_A(j).
```
It measures the error in the truncated divisor-coefficient sum, after multiplication by $`2^m`$. In particular, $`K_A(1)=1`$ and $`K_A(m+1)=2K_A(m)-c_A(m+1)`$.

<div id="res:terminalhalf" class="theorem">

**Theorem 9** (finite approximations with vanishing scaled error). *Suppose there are integers $`M_j\ge1`$ tending to infinity and sets $`A_j\subseteq\{2,\ldots,M_j\}`$ such that
``` math
\frac{|K_{A_j}(M_j)|}{2^{M_j}}\longrightarrow0.
```
Then $`X_A(2)=1/2`$ for some infinite set $`A\subseteq\mathbb{N}_{>0}`$.*

</div>

Lean: [paper terminalhalf](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos257/PaperCompleteR20/TerminalSetCorrespondence.lean#L51).

No agreement between different $`A_j`$ is assumed, and no bound is imposed on their earlier carries. Producing such finite approximants would refute Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">3</a>; their existence is not established here. The implication follows from the estimate
``` math
\left|X_{A_j}(2)-\frac12\right|
 \le \frac{|K_{A_j}(M_j)|+2\sqrt{M_j}+4}{2^{M_j}}.
```
It follows by separating the Lambert-series coefficient tail and using $`c_{A_j}(n)\le\tau(n)\le2\sqrt n`$. The finite sums therefore tend to $`1/2`$. The achievement set is closed, and no finite support has value $`1/2`$, so its representing support is infinite. A square-root bound on the terminal carry would suffice, but the theorem permits any error $`o(2^{M_j})`$. For a finite $`D\subseteq\{2,\ldots,M\}`$, the floor-quotient identity gives
``` math
K_D(M)=2^{M-1}-\sum_{d\in D}
                \left\lfloor\frac{2^M}{2^d-1}\right\rfloor.
```
Thus an exact quotient row has $`K_D(M)=1`$, whereas the terminal criterion permits a larger error of either sign. These are different conditions at a fixed depth, even though their cofinal existence conditions both characterise half-membership.

Conversely, if $`X_A(2)=1/2`$, then $`1\notin A`$, and the prefixes $`A_M=A\cap\{2,\ldots,M\}`$ satisfy
``` math
K_{A_M}(M)=\sum_{r\ge1}c_A(M+r)2^{-r}
       \le 2\sqrt M+4.
```
The equality uses the coefficients of the full support $`A`$ on the right: truncation does not change the coefficients through $`M`$. Hence the existence hypothesis of Theorem <a href="#res:terminalhalf" data-reference-type="ref" data-reference="res:terminalhalf">9</a> is equivalent to half-membership. Allowing incompatible finite supports removes a construction requirement, not the difficulty of the existence problem. Compactness proves the implication; it does not produce the approximating supports.

<a id="finite-families-with-a-shared-prefix."></a>

#### Finite families with a shared prefix.

Put $`B(m)=2\lfloor\sqrt m\rfloor+4`$. For $`0\le K\le M`$, consider a family $`A_1,\ldots,A_{B(M)}\subseteq\{2,\ldots,M\}`$ with
``` math
1\le K_{A_k}(m)\le B(m)\quad(1\le m\le M),
 \qquad K_{A_k}(M)=k.
```
Require that all the $`A_k`$ agree on $`\{1,\ldots,K\}`$ and that some integer $`E\ge B(M)`$ satisfies
``` math
\sum_{j=K+1}^{M}1_{A_k}(j)\,2^{M-j}+k=E
 \qquad(1\le k\le B(M)).
```
Thus the binary suffixes have consecutive values $`E-k`$, while the terminal carry ranges through the entire permitted interval. This is substantially more data than one finite approximation to $`1/2`$.

<div id="res:cylinderhalf" class="theorem">

**Theorem 10** (unbounded shared-prefix families imply a half-support). *Suppose that for every $`N`$ there are $`M,K`$ with $`\max\{N,1\}\le M`$, $`0\le K\le M`$, and a family satisfying all the conditions in the preceding paragraph. Then $`X_A(2)=1/2`$ for some infinite set $`A\subseteq\mathbb{N}_{>0}`$.*

</div>

Lean: [exists infinite positive support half of cofinal cylinder stages](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/Erdos249257/SuffixCylinderTerminalOnlyBridge.lean#L287).

Choosing one member from each family gives the terminal bound in Theorem <a href="#res:terminalhalf" data-reference-type="ref" data-reference="res:terminalhalf">9</a>, proving the conclusion. The shared-prefix conditions are needed for the proposed construction of the families, not for this final compactness step. Such a construction at unbounded depths would refute Problem #257; none is proved here.

<div id="prob:one-over-twenty-one-membership" class="problem">

**Problem 11** (membership of 1/21 in the Mersenne achievement set). For the greedy remainder of $`1/21`$, prove that arbitrarily large $`N`$ satisfy
``` math
2^{N+1}r_N(1/21)<\frac{2^{N+1}}{2^{N+1}-1},
 \quad\text{equivalently}\quad
 r_N(1/21)<\frac1{2^{N+1}-1}.
```
Equivalently, exclude the condition $`\mathcal F_{21}`$ defined above. One sufficient route is to rule out the eventual recurrence in Theorem <a href="#res:one-over-twenty-one-frontier" data-reference-type="ref" data-reference="res:one-over-twenty-one-frontier">8</a>(3) together with $`s_R>2^R`$; another is to prove $`s_R\le2^R`$ at arbitrarily large ranks. Neither sufficient route is claimed to be necessary by itself.

</div>

<div id="prob:scaled-return" class="problem">

**Problem 12** (bounded returns of the scaled remainder). For each of the targets $`x=1/2`$ and $`x=1/21`$, does the greedy remainder $`r_N(x)`$ return to one bounded interval after scaling by $`2^N`$?
``` math
\exists B<\infty\ \forall K\ \exists N\ge K:
 \qquad 2^N r_N(x)\le B.
```

</div>

<div id="prob:actual-invariant" class="problem">

**Problem 13** (arithmetic tests for the greedy sequence). Can a finite-memory, $`2`$-adic or discrepancy argument prove $`s_R\le2^R`$ at arbitrarily large ranks, or rule out the eventual recurrence in Theorem <a href="#res:one-over-twenty-one-frontier" data-reference-type="ref" data-reference="res:one-over-twenty-one-frontier">8</a>(3)? Such an argument must use the divisor counts of the actual greedy support. Can a bounded window of $`R\bmod6`$, residues of $`s_R`$, endpoint divisor counts and the finite set of eventual skips force a decrease or a contradiction? Alternatively, can one show that these bounded-memory data cannot distinguish the actual sequence from sequences that remain above $`2^R`$ but need not come from a support?

</div>

<div id="prob:fatal-interval" class="problem">

**Problem 14** (final-skip Diophantine exclusion). Let $`E=\sum_{n\ge1}(2^n-1)^{-1}`$. If $`1/21\notin\mathcal A`$, let $`M`$ be the last skipped exponent, $`S_M`$ its finite skipped prefix, and
``` math
a_M=\frac1{21}+\sum_{d\in S_M}\frac1{2^d-1}.
```
Write $`\operatorname{gap}_M=(2^M-1)^{-1}-R_M>0`$. Can the arithmetic restrictions on this last skipped exponent be used to prove $`|E-a_M|\ge\operatorname{gap}_M`$, contradicting
``` math
0<a_M-E<\operatorname{gap}_M?
```

</div>

<a id="app:elementary-details"></a>

# Elementary details used in the proofs

<a id="cyclotomic-prime-power-fact."></a>

#### Cyclotomic prime-power fact.

Let $`b\ge2`$, $`n\ge2`$, $`\ell\mid\Phi_n(b)`$ be prime and $`e=v_\ell(b^n-1)`$. Then $`\operatorname{ord}_{\ell^e}(b)=n`$. Here is a proof including the exceptional $`2`$-adic behaviour. For odd $`\ell`$, put $`d=\operatorname{ord}_{\ell}(b)`$ and $`s=v_\ell(b^d-1)`$. The elementary lifting identity $`v_\ell(b^{dt}-1)=s+v_\ell(t)`$ follows by factoring a geometric sum when $`\ell\nmid t`$ and by a binomial expansion for a factor $`\ell`$. In the factorisation $`b^n-1=\prod_{r\mid n}\Phi_r(b)`$, subtracting these valuations over proper divisors gives
``` math
v_\ell(\Phi_n(b))=
 \begin{cases}s&n=d,\\1&n=d\ell^j,\ j\ge1,\\0&\text{otherwise.}\end{cases}
```
If $`n=d`$, no smaller positive exponent gives $`b^m\equiv1\pmod\ell`$. If $`n=d\ell^j`$, the full valuation is $`e=s+j`$; the same lifting identity shows that the least exponent giving valuation $`e`$ is $`d\ell^j=n`$. For $`\ell=2`$, $`b`$ is odd. Factoring $`b^{2t}-1`$ gives
``` math
v_2(b^{2^j}-1)=v_2(b-1)+v_2(b+1)+j-1\qquad(j\ge1).
```
The only possible indices $`n\ge2`$ are $`n=2^j`$: $`v_2(\Phi_2(b))=v_2(b+1)`$ and $`v_2(\Phi_{2^j}(b))=1`$ for $`j\ge2`$; all other indices have valuation zero. The displayed identity again makes $`2^j`$ the least exponent with the full valuation. This proves the fact. Finally $`\Phi_n(b)>1`$: each primitive $`n`$th root $`\zeta`$ satisfies $`|b-\zeta|>1`$, and their product is $`\Phi_n(b)`$.

<a id="exact-scalar-cover-cost."></a>

#### Exact scalar cover cost.

For $`t\ge1`$, put $`z=\log_2t`$. The substitution $`y=2^\alpha`$ reduces the infimum defining $`\Psi(t)`$ to $`y^z/(y-1)`$ on $`1<y\le2`$. Its derivative has the sign of $`(z-1)y-z`$. Hence
``` math
\Psi(t)=
 \begin{cases}t,&1\le t\le4,\\
 z^z/(z-1)^{z-1},&t>4.
 \end{cases}
```
The endpoint and the open lower bound $`\alpha>0`$ are both included in this calculation. This scalar identity does not supply a converse to the positive-cover criterion.

<a id="app:sources"></a>

# Guide to the formal sources

The public proof closure at `065e09523286` was replayed under Lean 4.29.1. Besides the reciprocal and weighted declarations cited above, the replay checked the exact strengthened positive-cover conclusion in [`strengthenedPositiveCoverClaim`](https://github.com/wcook04/plectis-erdos/blob/065e09523286894dfb57ba205e69666843817009/lean/ErdosProblems/Erdos257/PaperCompleteR8/PositiveCoverReturn.lean#L241) and the common-witness conclusion in [`mixedSupportClaim`](https://github.com/wcook04/plectis-erdos/blob/065e09523286894dfb57ba205e69666843817009/lean/ErdosProblems/Erdos257/PaperCompleteR8/WeightedReturn.lean#L105). The axiom audit for these endpoints reports only `propext`, `Classical.choice`, and `Quot.sound`. The ordinary proof for $`A_\star`$ remains separate from the existential host wrapper, which does not verify that named example.

Erdős’s five-page paper was checked directly: p. 222 states the reciprocal-summable extension without proof, and p. 226 describes the fractional-part approach. The original Luca–Tachiya and Hornich articles were not independently retrieved. The periodic theorem \[lucatachiya2014periodic\] was checked in Luca and Tachiya’s own account \[lucatachiya2017, Theorem A and Example 2, pp. 139–140\], and the strict-tail result in Nitecki’s exposition. The *Formal Conjectures* file \[formalconjectures257\] is statement-level prior art, not a proof dependency.

The index retains the original names and revisions: standard macros use `99f4bf47422a`, and fourteen paper-local coordinates across the two papers use `f36a98bf3d3e`. The linked hypotheses and conclusions, not the abbreviated index labels, give the precise statements.

<a id="finite-sums-and-rational-denominators."></a>

#### Finite sums and rational denominators.

[noncollapse of the finite period](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5091); [noncollapse for the reduced rational denominator](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5246); [coprimality of the base and finite-sum denominator](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5221); [the lower bound for the finite-sum denominator](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5260).

<a id="rationality-and-integer-carries."></a>

#### Rationality and integer carries.

[rationality and integer recurrences with vanishing scaled error](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GenericTailOrbitRigidity.lean#L426); [unboundedness of the shifted odd-tail recurrence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/RationalSupportCarrySkeleton.lean#L2383); [lengths of intervals with zero divisor count](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SublogDivisorCoverage.lean#L392); [a lower bound for reciprocal mass](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/RationalSupportCarrySkeleton.lean#L1480); [the reciprocal-mass alternative for dyadic values](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/RationalSupportCarrySkeleton.lean#L2210); [rational support values and Möbius-inverted carries](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusCarry.lean#L949).

<a id="classical-support-theorems-and-examples."></a>

#### Classical support theorems and examples.

The formal [pairwise-coprime theorem](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L10776) retains the coprimality hypothesis, whereas [full-support irrationality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L8328) is a separate result. The other classical-support declarations are: [irrationality for full support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L9045); [irrationality for multiples of an integer](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L9103); [irrationality for the stated eventually periodic weights](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L12811); [residue class](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L11672); [odd](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L11686); [factorial support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L6035); [powers-of-two support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L6059); [factorial-support instance](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L6082); [powers-of-two-support instance](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L6090); [pairwise-coprime support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L10776); [full-support irrationality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L8328); [failure of the least-common-multiple gap condition for full support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L6272); [the rationality alternative for signed periodic weights](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L14175).

<a id="squarefree-divisor-counts-and-certificate-restrictions."></a>

#### Squarefree divisor counts and certificate restrictions.

[the number $`2^{\omega(n)}`$ of squarefree divisors](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L94); [the squarefree divisor-count identity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L111); [parity of the squarefree divisor count](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L140); [squarefree divisors as products of distinct primes](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L71); [failure of the stated carry certificates for squarefree support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L274); [failure of the stated digitwise certificates for squarefree support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L292); [$`2^{\omega(n)}`$ incidence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L314); [equivalence after shifting the squarefree divisor count](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L335); [blocks on which $`\omega(n)`$ is large](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L441); [digitwise blocks for the shifted divisor count](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L485).

<a id="deleting-finitely-many-terms."></a>

#### Deleting finitely many terms.

[passing irrationality from a tail to the series](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L9467); [passing irrationality from the series to a tail](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L9476).

<a id="the-full-achievement-set."></a>

#### The full achievement set.

[compact](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L656); [perfect](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L1656); [totally disconnected](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L1672); [nowhere dense](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L1681); [Lebesgue measure one](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L996); [membership and greedy tail bounds](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L1458); [non-membership of $`3/4`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L1784).

<a id="restricted-achievement-sets."></a>

#### Restricted achievement sets.

[the tail of a restricted subseries](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L20); [summability of the restricted tail](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L24); [strict domination of the restricted tail by the preceding weight](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L30); [injectivity of the restricted digit map](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L54); [digit strings vanishing off $`J`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L45); [restricted digit map](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L49); [supported digit set](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L63); [closed](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L66); [restricted achievement set](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L76); [the image theorem](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L79); [compact](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L90); [closed](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L96); [support restriction](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L103); [nowhere dense](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L112); [absence of isolated restricted digit strings for infinite support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L120); [absence of isolated represented values for infinite support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L150); [perfect](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L167); [controls digit terms](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L175); [the update formula](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L182); [the union formula after adding one exponent](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L203); [disjointness of the two translated copies](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L262); [doubles the volume](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L286); [recovery of the full achievement set](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L300); [the scaled volume identity after deleting finitely many exponents](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L313); [gives $`2^{-|F|}`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L349); [monotonicity under inclusion of supports](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L358); [measure zero](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L368); [the formal dichotomy](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L397).

<a id="half-membership-and-finite-approximations."></a>

#### Half-membership and finite approximations.

[the greedy form](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L2583); [the terminal-bit form](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L126); [the skipped-rank form](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L213); [the fatal-gap equivalence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfCylinderFatalGapRightTail.lean#L781); [its transfer to non-membership](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfCylinderFatalGapRightTail.lean#L787); [the finite-support exclusion](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfCarryReachability.lean#L589); [an exact finite sum from one greedy skip](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkipRowCofinal.lean#L55); [the upper-half Boolean fill](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkippedCoreExactRow.lean#L228); [the strict-positivity theorem](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkipRowCofinal.lean#L32); [the cofinal-skip hypothesis](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkipRowCofinal.lean#L22); [exact finite sums from arbitrarily late greedy skips](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkipRowCofinal.lean#L84); [compactness from exact sums at unbounded depths](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusCofinalExactRows.lean#L71); [membership from infinitely many greedy skips](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkipRowCofinal.lean#L97); [equivalence of infinitely many skips and half-membership](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkipRowCofinal.lean#L110); [achievement-set conclusion](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TerminalOnlyScaledVanishing.lean#L165); [infinite-support lift](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TerminalOnlyScaledVanishing.lean#L221); [a conditional infinite support representing one half](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/HalfCounterexampleFrontier.lean#L31); [the conditional counterexample to universal irrationality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/HalfCounterexampleFrontier.lean#L39).

<a id="finite-greedy-inequalities."></a>

#### Finite greedy inequalities.

[general band localization](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfGreedyTwoThirdsBand.lean#L88); [two-thirds band](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfGreedyTwoThirdsBand.lean#L127); [odd numerator bound](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfGreedyTwoThirdsBand.lean#L231); [integral safety](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfGreedyTwoThirdsBand.lean#L185).

<a id="fixed-core-supports-and-dilation."></a>

#### Fixed-core supports and dilation.

[carry certificates for the stated fixed-core support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SupportSunflowerDichotomy.lean#L531); [irrationality for the stated fixed-core support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SupportSunflowerDichotomy.lean#L540); [the uniform tail-selection hypothesis](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SupportSunflowerDichotomy.lean#L406); [the divisor-count identity under dilation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CompositeDilationDefect.lean#L30); [vanishing of the dilation correction for prime support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CompositeDilationDefect.lean#L103); [prime specialization](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CompositeDilationDefect.lean#L119); [classification of the extra divisors](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CompositeDilationDefect.lean#L133); [the upper bound for the dilation correction](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CompositeDilationDefect.lean#L151); [the example with exponents two and six](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CompositeDilationDefect.lean#L218).

<a id="the-shared-prefix-families."></a>

#### The shared-prefix families.

[terminal bounds from the shared-prefix families](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SuffixCylinderTerminalOnlyBridge.lean#L264); [infinite half-support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SuffixCylinderTerminalOnlyBridge.lean#L277); [positive-support lift](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SuffixCylinderTerminalOnlyBridge.lean#L287).

<a id="the-möbius-example-and-two-prime-digit-systems."></a>

#### The Möbius example and two-prime digit systems.

[identity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/MobiusSignSupportNoGo.lean#L111); [bound](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/MobiusSignSupportNoGo.lean#L150); [exclusion of finite support for $`1/21`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/HalfCounterexampleFrontier.lean#L61); [existence for the stated two-prime digit system from rank eleven](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/Primitive23Multiplicity.lean#L52); [nonexistence for that system at rank ten](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/Primitive23Multiplicity.lean#L26); [two solutions at rank eleven](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/Primitive23Multiplicity.lean#L38); [two solutions at the stated multiples of ten](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/Primitive23Multiplicity.lean#L86).

<a id="scaled-greedy-remainders."></a>

#### Scaled greedy remainders.

[membership and a bounded scaled greedy remainder](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyTrapDynamics.lean#L262); [divergence of the scaled remainder outside the achievement set](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyTrapDynamics.lean#L189); [membership and bounded scaled returns at unbounded ranks](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyTrapDynamics.lean#L225); [the equivalent small-remainder test for rational targets](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyTrapDynamics.lean#L152); [the small-remainder test for $`1/21`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyTrapDynamics.lean#L283); [the relation between the integer and scaled real remainders](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusCarry.lean#L2117).

<a id="finite-quotient-tests-for-121."></a>

#### Finite quotient tests for $`1/21`$.

[support](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L32); [remainder](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L39); [the equivalence with failure of $`\mathcal F_{21}`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L3507); [vanishing scaled error from unbounded closed rows](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5554); [the eventual affine recurrence on $`\mathcal F_{21}`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5658); [uniqueness of a finite representation with the stated remainder bound](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L231); [the missing-prefix consequence of an aligned crossing](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5179); [the real greedy skip forced by that crossing](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5223); [the bounded-return test for $`1/21`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyTrapDynamics.lean#L275); [a sufficient integer-remainder bound for $`1/21`$](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusCarry.lean#L2843); [the six-step integer-remainder recurrence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusCarry.lean#L1892); [the equivalent divisor-count inequality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusCarry.lean#L1927); [an exact one-sided approximation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L3735); [order identity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L3569); [lower bound](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L3583).

<a id="acknowledgements"></a>

# Acknowledgements

I thank Wouter van Doorn for advice on mathematical exposition, in particular on explaining restrictive hypotheses, avoiding unnecessary notation, and writing for a first-time reader. His comments concerned a note on Problem 243; this acknowledgement does not imply that he reviewed the mathematics of the present paper.

<div class="thebibliography">

99 D. Duverney and Y. Tachiya, [*Refinement of the Chowla–Erdős method and linear independence of certain Lambert series*](https://danielduverney.fr/documents/theorie-des-nombres/DuverneyTachiya190522.pdf), Forum Math. 31 (2019), no. 6, 1557–1566, [DOI](https://doi.org/10.1515/forum-2018-0299). Page numbers refer to the linked author preprint. H. Kaneko, Y. Suzuki, and Y. Tachiya, [*Refinements of Erdős’s irrationality criterion for certain sparse infinite series*](https://arxiv.org/abs/2601.20743v1), arXiv:2601.20743v1 (2026). T. Tao and J. Teräväinen, [*Quantitative correlations and some problems on prime factors of consecutive integers*](https://arxiv.org/abs/2512.01739v2), arXiv:2512.01739v2 (submitted December 2025, revised April 2026). V. Kovač and T. Tao, *On several irrationality problems for Ahmes series*, Acta Math. Hungar. 175 (2025), no. 2, 572–608, [DOI](https://doi.org/10.1007/s10474-025-01528-0). Page numbers refer to arXiv:2406.17593v4. P. Erdős, *On arithmetical properties of Lambert series*, J. Indian Math. Soc. 12 (1948), 63–66. The Formal Conjectures Authors, [*FormalConjectures.ErdosProblems.`257`*](https://github.com/google-deepmind/formal-conjectures/blob/f776d2f2039351b00737ffcafb9d7d7666e1d9af/FormalConjectures/ErdosProblems/257.lean), Lean source at commit `f776d2f`, 2025, accessed 13 September 2026.

P. Erdős, [*On the irrationality of certain series*](https://users.renyi.hu/~p_erdos/1969-09.pdf), Math. Student 36 (1968), 222–226 (issued 1969); [five-page scan](https://www.renyi.hu/~p_erdos/1969-09.pdf). P. Erdős, *Some problems and results on the irrationality of the sum of infinite series*, J. Math. Sci. 10 (1975), 1–7. K. Barreto, J. Kang, S.-H. Kim, V. Kovač, and S. Zhang, [*Irrationality of rapidly converging series: a problem of Erdős and Graham*](https://arxiv.org/abs/2601.21442v3), arXiv:2601.21442v3 (2026), to appear in Bull. London Math. Soc. Z. Nitecki, [*Subsum sets: intervals, Cantor sets, and Cantorvals*](https://arxiv.org/abs/1106.3779v2), arXiv:1106.3779v2 (2013). F. Luca and Y. Tachiya, [*Linear independence results for the values of divisor functions series*](https://www.kurims.kyoto-u.ac.jp/~kyodo/kokyuroku/contents/pdf/2014-14.pdf), RIMS Kôkyûroku No. 2014 (2017), 138–150. Theorem A restates their periodic-sequence theorem ([DOI](https://doi.org/10.1142/S1793042113501121)). F. Luca and Y. Tachiya, *Irrationality of Lambert series associated with a periodic sequence*, International Journal of Number Theory **10** (2014), no. 3, 623–636. [doi:10.1142/S1793042113501121](https://doi.org/10.1142/S1793042113501121).

F. Luca and Y. Tachiya, *Linear independence of certain Lambert series*, Proceedings of the American Mathematical Society **142** (2014), no. 10, 3411–3419. [doi:10.1090/S0002-9939-2014-12102-2](https://doi.org/10.1090/S0002-9939-2014-12102-2).

W. Van Assche, *Little $`q`$-Legendre polynomials and irrationality of certain Lambert series*, The Ramanujan Journal **5** (2001), 295–310. [doi:10.1023/A:1012930828917](https://doi.org/10.1023/A:1012930828917); [arXiv:math/0101187v1](https://arxiv.org/abs/math/0101187v1).

H. Hornich, *Über beliebige Teilsummen absolut konvergenter Reihen*, Monatshefte für Mathematik und Physik **49** (1941), 316–320. [doi:10.1007/BF01707309](https://doi.org/10.1007/BF01707309).

*The logarithmic endpoint fails under arithmetic sampling*, AI-assisted ordinary proof note, 17 September 2026. Theorem 1, Corollary 3 and Proposition 4. Unpublished working note; independent review and fresh Lean verification are outstanding. W. van Doorn and V. Kovač, *Lacunary sequences whose reciprocal sums represent all rational numbers in an interval*, Acta Arith. 223 (2026), 275–295. [DOI](https://doi.org/10.4064/aa251001-13-1). Page references use <https://arxiv.org/abs/2509.24971v3>.

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.
