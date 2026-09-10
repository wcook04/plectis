<a id="erdos-257-mersenne-support-subseries"></a>

# Reciprocal-Summable Support Irrationality at Every Integer Base

The source annotations in this note deliberately name two immutable revisions. Links produced by the standard note macros use `99f4bf47422a`; across this note and its long reasoning surface, fourteen paper-local coordinates link revision `f36a98bf3d3e`. These families are audited separately; a historical aggregate reference count is not asserted to be an exact inventory of this PDF.

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

For every infinite set $`A`$ of positive integers with $`\sum_{a\in A}1/a<\infty`$, we give a complete proof that $`\sum_{a\in A}(b^a-1)^{-1}`$ is irrational at every integer base $`b\ge2`$. Averaging modular divisor atoms produces arbitrarily small positive displacements, which rationality would confine to a fixed lattice. Two extensions accommodate divergent reciprocal mass: prime-power weights and positive fractional divisor covers. Their classes are incomparable, but a common finite averaging estimate combines them and yields supports in neither class. A logarithmic incidence invariant quantifies the cost of every positive cover. Finite denominator periods and the actual greedy return inequality delimit the remaining arithmetic problem. Universal irrationality remains unresolved.

<a id="sec:problem"></a>

# Introduction and main results

Write $`X_A(b)=\sum_{a\in A}(b^a-1)^{-1}`$ for $`A\subseteq\mathbb{N}_{>0}`$ and an integer $`b\ge2`$. Our first result is the following.

<div id="res:reciprocal-support" class="theorem">

**Theorem 1** (reciprocal-summable supports). *Let $`A\subseteq\mathbb{N}_{>0}`$ be infinite. If
``` math
\sum_{a\in A}\frac1a<\infty,
```
then $`X_A(b)`$ is irrational for every integer $`b\ge2`$.*

</div>

The statement is [](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/Erdos249257/AllBaseReciprocalSupportIrrationality.lean#L395).

For infinite $`A`$ and $`N>0`$, division of $`N`$ by each $`a\in A`$ gives
``` math
0<\Delta_{b,A}(N)
 :=\sum_{a\in A}\frac{b^{N\bmod a}-1}{b^a-1}
 =(b^N-1)X_A(b)-J_{b,A}(N),\qquad J_{b,A}(N)\in\mathbb{Z}.
 \label{eq:intro-displacement}\tag{D}
```
Only $`a\le N`$ contribute to $`J_{b,A}(N)`$. Rationality $`X_A(b)=p/q`$ would force every positive displacement to be at least $`1/q`$. The proof makes these positive displacements arbitrarily small by averaging along multiples of a growing divisibility modulus.

The conclusion is hereditary: every infinite subset of such an $`A`$ satisfies the theorem at every base. For example, every powerful integer can be written as $`u^2v^3`$, so
``` math
\sum_{\substack{a\ge1\\a\text{ powerful}}}\frac1a
 \le\zeta(2)\zeta(3)<\infty.
```
Thus arbitrary infinite thinnings of the powerful integers are included.

<div id="res:problem" class="problem">

**Problem 2** (Erdős \#257). Is $`X_A(2)`$ irrational for every infinite $`A\subseteq\mathbb{N}_{>0}`$?

</div>

Theorem <a href="#res:reciprocal-support" data-reference-type="ref" data-reference="res:reciprocal-support">1</a> excludes the entire reciprocal-summable region. Section <a href="#sec:eight-return-extensions" data-reference-type="ref" data-reference="sec:eight-return-extensions">3</a> gives two different extensions into the reciprocal-divergent region. The final section retains the actual arithmetic constraint for a proposed rational value.

Erdős proved the pairwise-coprime case at every integer base and stated that the coprimality condition could be removed, leaving the details unprinted \[erdos1968, p. 222\]. Theorem <a href="#res:reciprocal-support" data-reference-type="ref" data-reference="res:reciprocal-support">1</a> gives a complete proof of that stated extension. The all-base quantifier is already in Erdős’s statement.

The coefficient sequence throughout is the divisor transform of one Boolean selector:
``` math
\begin{equation}
 c_A(n)=\#\{a\in A:a\mid n\},\qquad
 X_A(b)=\sum_{n\ge1}\frac{c_A(n)}{b^n}.
 \label{eq:incidence}
\end{equation}
```
Nonnegative interchange proves this identity. The coefficients may exceed one, and their common origin in a single support will matter below.

<a id="sec:reciprocal-support"></a>

# Reciprocal-summable supports at every integer base

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
The passage from individual atoms to their infinite sum needs a uniform bound. Counting positive multiples of $`d`$ gives
``` math
\begin{align*}
 \frac1X\sum_{m=1}^Xw_{b,d}(Qm)
 &=\sum_{r\ge1}b^{-r}
       \frac{\#\{1\le m\le X:d\mid Qm+r\}}X\\
 &\le\sum_{r\ge1}b^{-r}\frac{Q+r}{d}
 =\frac{Q/(b-1)+b/(b-1)^2}{d}\le\frac{Q+2}{d}.
\end{align*}
```
Indeed, the counted multiples are distinct and at most $`QX+r`$. Reciprocal summability now permits dominated convergence, so the Cesaro mean of $`T_{Qm}^{(b)}`$ tends to $`\sum_{d\in A}M_{Q,b}(d)`$.

Next let $`Q_t=\operatorname{lcm}(1,\ldots,t)`$. For each fixed $`d`$, eventually $`d\mid Q_t`$ and $`M_{Q_t,b}(d)=(b^d-1)^{-1}`$. A second dominated-convergence argument, using $`M_{Q_t,b}(d)\le1/d`$, yields
``` math
\begin{equation}
 \sum_{d\in A}M_{Q_t,b}(d)\longrightarrow X_A(b).
 \label{eq:lcm-prefix-orbit-limit}
\end{equation}
```
Thus the limiting averages of the nonnegative displacements $`\Delta_{b,A}(Q_tm)`$ tend to zero. Choose $`t`$, then a sufficiently long finite average, and finally a term no larger than that average. This gives arbitrarily small positive displacements, contradicting the rational lattice in <a href="#eq:intro-displacement" data-reference-type="eqref" data-reference="eq:intro-displacement">[eq:intro-displacement]</a>. This proves Theorem <a href="#res:reciprocal-support" data-reference-type="ref" data-reference="res:reciprocal-support">1</a> directly at every integer base.

The order of limits is essential: the observation length tends to infinity with the modulus fixed, and only then does the modulus increase. Reciprocal summability controls both interchanges. Beyond that hypothesis, the next arguments replace the summable majorant or use a finite estimate which remains effective as the modulus changes.

<a id="sec:eight-return-extensions"></a>

# Extensions beyond reciprocal summability

The two criteria use different controls on the same positive displacement. Both remain valid for arbitrary infinite thinnings. The finite estimate in Section <a href="#sec:common-kernel" data-reference-type="ref" data-reference="sec:common-kernel">3.2</a> will put their error terms on one observation scheme and prove the mixed extension.

<a id="divisibility-weighted-and-quantitative-criteria"></a>

## Divisibility-weighted and quantitative criteria

For a finite nonempty prime set $`P`$, let $`h(a)=\prod_{p\in P}p^{v_p(a)}`$. The weighted condition
``` math
\sum_{a\in A}\frac{h(a)}{a(2^{h(a)}-1)}<\infty
  \tag{W}\label{eq:weighted-return}
```
implies irrationality of $`\sum_{a\in A}(b^a-1)^{-1}`$ for every infinite $`A`$ and every integer $`b\ge2`$. The conclusion is hereditary under passage to infinite subsets. A fixed-base version replaces $`2`$ by $`b`$ in the condition; arbitrary nested divisibility chains have the same criterion with $`h(a)`$ the largest chain element dividing $`a`$.

Here the decisive estimate is a finite orbit average. If $`g=(a,Q)`$, then
``` math
\frac1T\sum_{m=1}^T
 \frac{b^{Qm\bmod a}-1}{b^a-1}
 \le \frac{g}{a(b^g-1)}+\frac1{T(b^g-1)}.
```
The second term cannot be discarded before summing over $`a`$. Choose $`Q`$ to freeze the finite prefix and all small $`P`$-parts. Average again over $`T=2^j`$, $`M\le j<2M`$. The incomplete-period contribution from small $`P`$-parts is at most $`2QW/M`$, where $`W`$ is the sum in <a href="#eq:weighted-return" data-reference-type="eqref" data-reference="eq:weighted-return">[eq:weighted-return]</a>; the large-part contribution is suppressed by the exponential denominator. This produces arbitrarily small positive shifted-atom displacements. The integral lattice gap then gives irrationality, and the binary atom comparison gives every larger base. The supplement gives all truncation estimates and an explicit reciprocal-divergent host with gaps $`O(\log\log a)`$.

A quantitative consequence also admits reciprocal-divergent supports. Put $`H_A(x)=\sum_{a\in A,\ a\le x}1/a`$, $`T_0=2`$, $`T_{j+1}=2^{T_j}`$, and $`\ell(x)=\min\{j:x\le T_j\}`$. The condition $`H_A(x)=o(\ell(x))`$ implies all-base irrationality. The proof and the sharper rational-phase lower bound are in the analytic proof supplement; no positive density of $`A`$ is required.

<a id="sec:common-kernel"></a>

## A finite estimate on common observation scales

For $`1<B\le2`$, positive integers $`L,d,M`$, and $`R\ge0`$, put
``` math
w_{B,d}(n)=\frac{B^{n\bmod d}}{B^d-1},\qquad
 \mathscr D_{L;R,M}F
 =\frac1M\sum_{j=R}^{R+M-1}\frac1{2^j}
      \sum_{m=1}^{2^j}F(Lm).
```
The finite estimate
``` math
\mathscr D_{L;R,M}w_{B,d}
 \le\frac{1+4L/M}{d(B-1)}
 \label{eq:mixed-finite-kernel}\tag{S}
```
is uniform in $`d`$, $`R`$, and $`B`$ as $`B`$ decreases to one. The ratio $`L/M`$ measures the cost of incomplete modular periods.

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
Summing the main terms and these two error budgets proves <a href="#eq:mixed-finite-kernel" data-reference-type="eqref" data-reference="eq:mixed-finite-kernel">[eq:mixed-finite-kernel]</a>. The complete-cycle mass $`1/(B-1)`$ is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos257/PaperCompleteR7/CoverKernel.lean#L150), the bound $`g/(B^g-1)\le1/(B-1)`$ used for complete cycles is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos257/PaperCompleteR7/CoverKernel.lean#L140), and the no-wrap inequality $`\sum_{i<d}B^i\ge dB^{(d-1)/2}`$ is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos257/PaperCompleteR7/CoverKernel.lean#L343). Nonnegative interchange permits summation against any coefficients $`c_d`$ with $`\sum_dc_d/d<\infty`$.

<a id="positive-fractional-divisor-covers"></a>

## Positive fractional divisor covers

For a finite set $`F`$, put $`f_F(n)=\#\{a\in F:a\mid n\}`$. Let $`F_j`$ be finite sets of positive integers, let $`0<\alpha_j\le1`$, and suppose $`c_{j,d}\ge0`$ satisfy
``` math
f_{F_j}(n)^{\alpha_j}\le\sum_{d\mid n}c_{j,d},\qquad
 C_j=\sum_{d\ge1}\frac{c_{j,d}}d.
```

<div id="thm:variable-fractional-cover" class="theorem">

**Theorem 3** (strengthened positive covers). *If
``` math
\sum_{j\ge1}\frac{C_j2^{j\alpha_j}}{2^{\alpha_j}-1}<\infty,
 \tag{V}\label{eq:strengthened-cover}
```
then $`X_A(b)`$ is irrational for every infinite $`A\subseteq\bigcup_jF_j`$ and every integer $`b\ge2`$.*

</div>

<div class="proof">

*Proof.* Write $`B_j=2^{\alpha_j}`$ and
``` math
U_j(N)=\sum_{r\ge1}2^{-r}f_{F_j}(N+r),\qquad
 V_j(N)=\sum_{d\ge1}c_{j,d}w_{B_j,d}(N).
```
Subadditivity of the fractional powers and the positive majorants give $`U_j(N)^{\alpha_j}\le V_j(N)`$. Fix $`\varepsilon>0`$, set $`t_j=\varepsilon2^{-j}`$, and choose $`J`$ with
``` math
K_J:=\sum_{j>J}\frac{C_jt_j^{-\alpha_j}}{B_j-1}<\frac14.
```
This is possible since $`\varepsilon^{-\alpha_j}\le\max(1,\varepsilon^{-1})`$. Choose $`L`$ divisible by every member of the first $`J`$ frames. Equation <a href="#eq:mixed-finite-kernel" data-reference-type="eqref" data-reference="eq:mixed-finite-kernel">[eq:mixed-finite-kernel]</a> bounds the finite mean of $`S_J(N):=\sum_{j>J}t_j^{-\alpha_j}V_j(N)`$ by $`(1+4L/M)K_J<1/2`$ whenever $`M\ge4L`$. One sample therefore has $`S_J(N)<1`$, forcing $`U_j(N)<t_j`$ for every $`j>J`$. The frozen frames have zero displacement, so
``` math
0<\Delta_{2,A}(N)\le\sum_{j>J}U_j(N)\le\varepsilon.
```
The fixed rational lattice excludes rationality at base two. For every $`b\ge2`$, the elementary atom inequality $`(b^r-1)/(b^d-1)\le2(2^r-1)/(2^d-1)`$ for $`0\le r<d`$ gives the same conclusion at base $`b`$; that inequality is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos257/PaperCompleteR7/CoverKernel.lean#L232). Any prescribed positive divisor can be included in $`L`$, so the witnesses can also be required to be arbitrarily large. ◻

</div>

The same proof permits any positive weights $`\eta_j`$ with $`\sum_j\eta_j=1`$, replacing $`2^{-j}`$ by $`\eta_j`$. The condition strengthens the earlier two-inverse-power cost $`\sum_jC_j2^{j\alpha_j}2^{\alpha_j}/(2^{\alpha_j}-1)^2<\infty`$. There is a squarefree support $`A^\star`$ satisfying <a href="#eq:strengthened-cover" data-reference-type="eqref" data-reference="eq:strengthened-cover">[eq:strengthened-cover]</a> for which every cover with that older cost, and every finite-prime weighted criterion, fails. Its complete construction is in the accompanying *Strengthened Variable-Exponent Cover* proof.

<a id="what-every-positive-cover-must-pay"></a>

## What every positive cover must pay

The strengthening has a cover-independent boundary. For finite $`F`$, write $`\mathbb E_F`$ for the uniform mean modulo $`\operatorname{lcm}(F)`$. More generally allow weights $`\eta_j>0`$ with $`\sum_j\eta_j=1`$, and set
``` math
K=\sum_j\frac{C_j\eta_j^{-\alpha_j}}{2^{\alpha_j}-1},\qquad
 \Psi(0)=0,\quad
 \Psi(t)=\inf_{0<\alpha\le1}\frac{t^\alpha}{2^\alpha-1}\quad(t\ge1).
```
For every finite $`F`$ covered by the frames,
``` math
\begin{equation}
 K\ge\mathbb E_F\Psi(f_F)\ge e\,\mathbb E_F\log^+f_F.
 \label{eq:cover-log-obstruction}
\end{equation}
```
Indeed, at a point where $`f_F(n)=t>0`$, some frame has $`f_{F_j}(n)\ge\eta_jt`$. Otherwise summing contradicts coverage. The corresponding weighted majorant is at least $`\Psi(t)`$. Averaging and using $`\lfloor X/d\rfloor/X\le1/d`$ proves the first inequality. Convexity gives $`2^\alpha-1\le\alpha`$, and $`e^u/u\ge e`$ proves the second. Those two scalar steps are [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos257/PaperCompleteR7/CoverKernel.lean#L170) and [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos257/PaperCompleteR7/CoverKernel.lean#L177), and the bound $`t^\alpha/(2^\alpha-1)\ge e\log t`$ at every admissible exponent is [Lean source](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos257/PaperCompleteR7/CoverKernel.lean#L188).

This bound survives optimisation over all covers. For $`F(q,P)=\{qd:d\mid\prod_{p\in P}p\}`$, where $`q\ge2`$ and no $`p\in P`$ divides $`q`$, put $`S=\sum_{p\in P}1/p`$. If $`S\ge1`$, the infimum $`K_*`$ over all covers satisfies
``` math
\begin{equation}
 \frac{e(S-1)}q\le K_*\bigl(F(q,P)\bigr)\le\frac{eS}q.
 \label{eq:optimal-cube-cost}
\end{equation}
```
For the lower bound, condition on $`q\mid n`$ and write $`f_F(n)=2^Z`$. The Chinese remainder theorem gives $`\mathbb EZ=S`$, and direct minimisation gives $`\Psi(2^z)\ge e(z-1)`$. For the upper bound, use the single frame, $`z=1/S`$, and $`\alpha=\log_2(1+z)`$; its exact positive expansion has cost
``` math
\frac1{qz}\prod_{p\in P}(1+z/p)\le\frac{eS}q.
```
Thus the optimised cost is asymptotically $`eS/q`$.

The weighted class and the strengthened-cover class are incomparable. The support $`A^\star`$ above lies only in the latter. In the reverse direction, disjoint prime blocks with reciprocal mass of order $`2^k`$, placed in frames $`\{2^kd:d\mid M_k\}`$, give a support $`A_W`$ satisfying <a href="#eq:weighted-return" data-reference-type="eqref" data-reference="eq:weighted-return">[eq:weighted-return]</a>; its first logarithmic moments diverge, so <a href="#eq:cover-log-obstruction" data-reference-type="eqref" data-reference="eq:cover-log-obstruction">[eq:cover-log-obstruction]</a> excludes every strengthened cover. Exact constructions and the scalar minimisation are in the accompanying *First Logarithmic Moment of Positive Covers* proof. These comparisons concern the individual sufficient classes.

<a id="combining-the-two-support-criteria"></a>

## Combining the two support criteria

<div id="res:mixed-supports" class="theorem">

**Theorem 4** (mixed weighted and cover supports). *Suppose $`E`$ has finite weighted mass <a href="#eq:weighted-return" data-reference-type="eqref" data-reference="eq:weighted-return">[eq:weighted-return]</a> for a finite nonempty prime set, and $`V`$ admits a strengthened positive cover <a href="#eq:strengthened-cover" data-reference-type="eqref" data-reference="eq:strengthened-cover">[eq:strengthened-cover]</a>. Then $`X_A(b)`$ is irrational for every infinite $`A\subseteq E\cup V`$ and every integer $`b\ge2`$.*

</div>

<div class="proof">

*Proof of the combination step.* Freeze a sufficiently large finite prefix from each component with one modulus. The weighted argument supplies subsequent moduli $`Q`$ and observation ranges $`M\le j<2M`$ with $`Q/M\to0`$ and arbitrarily small weighted-displacement mean. By nonnegative interchange, <a href="#eq:mixed-finite-kernel" data-reference-type="eqref" data-reference="eq:mixed-finite-kernel">[eq:mixed-finite-kernel]</a> bounds the positive-cover tail test under exactly the same finite measure, with factor $`1+4Q/M`$. Choose the two tail budgets so that the mean of their normalised sum is less than one. One common sample then makes both displacements small. Infinitude supplies strict positivity and the rational lattice excludes rationality. The full estimates and parameter schedule are in `ErdosProblems/Erdos257/MixedSupportSynchronisation.md`, Theorems 2.1 and 5.1. ◻

</div>

In particular, every infinite subset of $`A_W\cup A^\star`$ has irrational subseries at every integer base. Downward closure and the two earlier separations show that this mixed host belongs to neither individual class. The mixed class is closed under finite unions and finite changes. Countable unions require an additional budget: all prime singletons are admitted, while the full prime support has $`\Delta_{2,\mathcal P}(N)>1/3`$ for every $`N\ge1`$. The reciprocal-summable class is contained in the weighted class, since $`h/(2^h-1)\le1`$. Theorem <a href="#res:reciprocal-support" data-reference-type="ref" data-reference="res:reciprocal-support">1</a> supplies the direct proof of that baseline case.

<a id="the-prime-power-regime."></a>

#### The prime-power regime.

A separate ordinary argument proves irrationality for every infinite subset of the prime powers, at every integer base, including fixed dilations and finite modifications. Its analytic input is Tao–Teräväinen \[taoteravainen2025, Theorem 3.1\]. The proof uses the reciprocal mass of the selected primes as its scale, so arbitrarily slow divergence is retained; higher prime powers produce errors only on prime-square events. The equidistribution, small-prime, progression and exceptional-set hypotheses are checked in the supplement. The full-prime theorem and the authors’ stated full-prime-power extension are theirs; no priority claim is made for the returned thinning argument.

The actual greedy membership problem is treated in Section <a href="#sec:actual-repairs" data-reference-type="ref" data-reference="sec:actual-repairs">8</a>; its repair inequality has a different logical role from the sufficient irrationality criteria above.

<a id="sec:period"></a>

# Finite-support denominator periods

For a finite nonempty $`F\subseteq\mathbb{N}_{>0}`$, let $`D_F`$ be the positive reduced denominator of $`x_F(b)=\sum_{n\in F}(b^n-1)^{-1}`$. We use $`\operatorname{ord}_1(b)=1`$.

<div id="res:period" class="theorem">

**Theorem 5** (finite-period noncollapse). *Let $`F\subseteq\mathbb{N}_{>0}`$ be finite and nonempty, let $`b\ge2`$ be an integer, and let $`D_F>0`$ be the denominator of $`x_F(b)`$ in lowest terms. Then $`D_F`$ is coprime to $`b`$, and
``` math
\operatorname{ord}_{D_F}(b)=\operatorname{lcm}\{n:n\in F\}.
```
If moreover $`\operatorname{lcm}(F)\ge2`$, then $`\operatorname{lcm}(F)<D_F`$.*

</div>

Coprimality is [base coprimality of the reduced denominator](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5221), the order statement is [the exact multiplicative order](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5246), and the size bound is [the strict denominator inequality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5260). The three clauses hold together in one declaration, [](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos257/PaperCompleteR7/Assemblies.lean#L29).

Put $`L=\operatorname{lcm}(F)`$. Clearing denominators gives $`D_F\mid b^L-1`$, so the upper divisibility for the order is immediate. For the reverse, choose $`n\ge2`$ maximal under divisibility in $`F`$ and a prime $`\ell\mid\Phi_n(b)`$. If $`e=v_\ell(b^n-1)`$, the full prime power $`\ell^e`$ has $`\operatorname{ord}_{\ell^e}(b)=n`$. Every other selected exponent $`m`$ has $`n\nmid m`$, hence $`v_\ell(b^m-1)<e`$. The $`n`$th summand has uniquely smallest $`\ell`$-adic valuation and cannot cancel. Thus $`\ell^e\mid D_F`$ and $`n\mid\operatorname{ord}_{D_F}(b)`$. Taking all maximal selected exponents proves the order statement; the size bound follows from $`\operatorname{ord}_{D_F}(b)\mid\varphi(D_F)<D_F`$ when $`L\ge2`$. The case $`F=\{1\}`$ has order one directly.

The same unique-valuation argument permits any signs $`\pm1`$ on the finite summands, and that signed statement is [](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos257/SignedFinitePeriodNoncollapse.lean#L507). Its cyclotomic prime-power lemma, including the $`2`$-adic case, is proved in *Finite Denominator Realisation*. The distinction between primes and prime powers is visible in
``` math
X_{\{2,3\}}(2)=\frac{10}{21},\qquad
 X_{\{2,6\}}(2)=\frac{22}{63}.
```
Both denominators have order six. The first combines orders two and three, while the second retains the order-six prime power $`9`$; no prime divisor of $`63`$ itself has order six. The boundary $`F=\{1\}`$ at base two has $`D_F=L=1`$. These lower denominator bounds give no upper height control for infinite partial sums and do not decide an infinite-support value.

<a id="sec:forced"></a>

# Rational values and scaled tails

The displacement identity gives a fixed arithmetic lattice under rationality. Its recurrence is
``` math
z_{N+1}=2z_N-vc_A(N+1),\qquad
 z_N=v\sum_{r\ge1}c_A(N+r)2^{-r}\in\mathbb{Z}
```
when $`X_A(2)=p/v`$. The sequence $`c_A`$ is determined by one Boolean selector.

Two elementary facts explain why size information alone has little force here. If $`a_0=\min A`$, every $`a_0`$ consecutive integers contain a multiple of $`a_0`$, so a divisor-incidence zero window has length at most $`a_0-1`$. If $`A`$ is infinite, choose $`k`$ exponents and a common multiple $`L`$; then $`c_A(L)\ge k`$ and $`T_{L-1}^{(2)}\ge k/2`$. Both facts hold without rationality. The arithmetic information lies in the lattice and in the compatibility of all coefficients with the same selector.

Precisely, Dirichlet convolution gives $`\mu*c_A=\mathbf1_A`$, where $`\mu`$ is the Möbius function. A putative recurrence with integral forcing must therefore satisfy $`(\mu*c_A)(n)\in\{0,1\}`$ for all $`n`$. The complete Boolean–Möbius scaled-tail correspondence and its finite example are retained in the long record, under *Exact descriptions of a rational-valued support* (Theorem `thm:bmc`). The correspondence permits finite supports; infinitude remains a separate requirement for a counterexample to Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">2</a>.

<a id="sec:map"></a>

# Where the return mechanism stops

The preceding criteria establish irrationality through small positive returns. This mechanism already fails at the full support:
``` math
\Delta_{2,\mathbb{N}_{>0}}(N)
 >(2^N-1)\sum_{a>N}2^{-a}=1-2^{-N}\ge\frac12
 \qquad(N\ge1).
```
The full-support value is nevertheless irrational \[erdos1968\]. A universal proof must therefore control arithmetic behaviour beyond small returns.

The distinction also appears in the squarefree support. Its series is known to be irrational at powers-of-two bases by Duverney–Tachiya \[duverneytachiya, Corollary 1.2 and Example 1.1\]. The zero-window obstruction for one normalised certificate scheme concerns that scheme’s hypotheses. It gives no obstruction to irrationality of the value. The precise normalisation counterexamples are retained in the long record, together with the complete catalogue of known support families.

A related independence boundary concerns prime-incidence arguments. Writing $`f_A(n)=\sum_{a\in A}{\bf1}_{a\mid n}`$, the local identity
``` math
f_A(an)-f_A(n)=1-{\bf1}_{a\mid n}\quad(n\ge1)
```
for a fixed $`a\in A`$ holds exactly when $`a`$ is coprime to every other member of $`A`$. Already for the dilated prime support $`2\mathcal P`$,
``` math
\operatorname{Cov}({\bf1}_{2p\mid n},{\bf1}_{2q\mid n})
 =\frac1{4pq}\qquad(p\ne q\text{ odd primes}),
```
where covariance is taken over a common arithmetic period. Thus multiplicative size conditions alone do not supply the independence used by the prime argument. The accompanying *Prime-Incidence Boundary* proof identifies the exact dilation condition and accumulated covariance error.

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
shows that every represented value has a unique selector. The middle inequality follows by writing $`w_n=2^{-n}+4^{-n}/(1-2^{-n})`$ and using $`n\ge N+1\ge2`$. The coding image is a Cantor set, and the disjoint level-$`N`$ cylinder covers have total length $`2^NR_N\to1`$, so $`\lambda(\mathcal A)=1`$. Kovač–Tao record this strict-tail inequality and the Cantor conclusion in the fixed-base setting \[kovactao, Remark 4.1\]. The long record proves the restricted-volume dichotomy and records the formula $`\dim_H\mathcal A_J=\liminf_N\#(J\cap[1,N])/N`$, together with the periodic-stride measure refinements. For a specified rational target, the useful consequence here is uniqueness of its possible selector.

<a id="sec:actual-repairs"></a>

# The actual greedy return inequality

For $`x\ge0`$, the greedy rule starts with $`r_0=x`$ and, at rank $`n\ge1`$, selects $`n`$ when $`r_{n-1}\ge(2^n-1)^{-1}`$, subtracting that weight if selected. Let $`A_x`$ be the resulting support and $`c_x(n)=\#\{a\in A_x:a\mid n\}`$. Set
``` math
P_0=0,\qquad P_{N+1}=2P_N+c_x(N+1),\qquad
 Q_N=\lfloor2^Nx\rfloor-P_N.
```
The nonnegative integer defect obeys
``` math
\begin{equation}
 Q_{N+1}=2Q_N+\beta_N-c_x(N+1),\qquad
 \beta_N=\lfloor2^{N+1}x\rfloor-2\lfloor2^Nx\rfloor\in\{0,1\}.
 \label{eq:actual-repair-recurrence}
\end{equation}
```

<div id="res:general-repair" class="theorem">

**Theorem 6** (general greedy repair criterion). *For every real $`x\ge0`$, the following are equivalent:
``` math
\begin{gathered}
 x\in\mathcal A;\\
 \forall K\ge0\ \exists N\ge K:\quad Q_{N+1}\le Q_N;\\
 \forall K\ge0\ \exists N\in[K,K+2\lfloor\sqrt K\rfloor+12):
 \quad Q_{N+1}\le Q_N.
 \end{gathered}
```*

</div>

The cofinal form is [](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos257/GreedyRepairCriterion.lean#L175) and the windowed form with the constant $`12`$ is [](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos257/GreedyRepairCriterion.lean#L192). Both equivalences hold together in one declaration, [](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos257/PaperCompleteR7/Assemblies.lean#L40).

<div class="proof">

*Proof.* Strict domination of each Mersenne weight over its tail implies that a represented target is recovered by the greedy rule. For such a target,
``` math
0\le Q_N\le\sum_{r\ge1}c_x(N+r)2^{-r}
 \le2\sqrt N+4,
```
since $`c_x(n)\le\tau(n)\le2\sqrt n`$ and $`\sqrt{N+r}\le\sqrt N+\sqrt r\le\sqrt N+r`$. Put $`s=\lfloor\sqrt K\rfloor`$ and $`T=2s+12`$. Strict increase at all $`T`$ steps would imply $`Q_{K+T}\ge T`$. But $`K+T<(s+4)^2`$ gives $`Q_{K+T}<2s+12=T`$. This proves the window condition and hence cofinal nonincreases.

Conversely, if $`x\notin\mathcal A`$, then $`\delta=x-X_{A_x}(2)>0`$. The Lambert prefix is at most $`2^NX_{A_x}(2)`$, so $`Q_N\ge2^N\delta-1`$. Eventually this exceeds $`c_x(N+1)\le N+1`$. Equation <a href="#eq:actual-repair-recurrence" data-reference-type="eqref" data-reference="eq:actual-repair-recurrence">[eq:actual-repair-recurrence]</a> then makes $`Q_N`$ strictly increasing, contradicting cofinal nonincreases. ◻

</div>

The explicit square-root estimate is uniform in the target. The ordinary subpower refinement replaces its window length by $`\lceil C_\varepsilon(K+1)^\varepsilon\rceil`$ for every $`0<\varepsilon<1`$, using $`\tau(n)=O_\delta(n^\delta)`$. This changes the permissible deadline without proving any occurrence for a specified target.

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

The preceding arguments isolate two different tasks. For new irrational supports, one needs a summable or uniformly averaged control of the shifted divisor atoms, or an arithmetic functional that also detects supports whose positive displacements stay separated from zero. For a proposed rational target, one needs the actual-selector inequality <a href="#eq:actual-selector-obligation" data-reference-type="eqref" data-reference="eq:actual-selector-obligation">[eq:actual-selector-obligation]</a>; synthetic recurrences satisfying only growth and integrality conditions do not provide it.

<div id="res:one-over-twenty-one-frontier" class="theorem">

**Theorem 7** (fatal-branch quotient refinement at $`1/21`$). *The following statements hold.*

1.  *$`1/21\in\mathcal A`$ if and only if $`\mathcal F_{21}`$ does not hold.*

2.  *If there is an unbounded sequence of ranks $`R`$ with $`s_R\le 2^R`$, then $`1/21\in\mathcal A`$.*

3.  *On $`\mathcal F_{21}`$, eventually $`s_R>2^R`$, the boundary rank $`R+1`$ belongs to $`D_{R+1}`$, and $`(D_R,s_R)`$ follows one exact affine recurrence.*

</div>

The equivalence is [kernel checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L3507); the closed-row compactness step is [kernel checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5554); and the eventual affine regime is [kernel checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5658). The denominator-specific separation theorem additionally proves that every closed Boolean quotient row is exactly the canonical quotient-greedy row ([kernel checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L231)). An aligned crossing from saturation into strict supercapacity forces a missing canonical ancestor and a real skipped exponent ([ancestor hole](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5179), [scaled skip](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5223)).

<div id="res:terminalhalf" class="theorem">

**Theorem 8** (terminal scaled vanishing implies the half-value). *Let $`S`$ be a `HalfTerminalOnlyScaledVanishingSequence`: its finite words exclude ranks $`0`$ and $`1`$, their depths tend to infinity, and the absolute terminal carry divided by $`2^M`$ tends to zero along the depths $`M`$. Then there is an infinite set $`A\subseteq\mathbb{N}`$ with*

*``` math
\sum_{a\in A}\frac1{2^a-1}=\frac12.
```
Consequently the universal irrationality assertion in Problem <a href="#res:problem" data-reference-type="ref" data-reference="res:problem">2</a> is false under this hypothesis. This is a conditional implication, not a construction of $`S`$ and not a solution of Problem #257.*

</div>

<div id="res:cylinderhalf" class="theorem">

**Theorem 9** (cofinal cylinders imply an infinite half-support). *Suppose that for every $`N`$ there are $`M,K`$ with $`\max\{N,1\}\le M`$ and a nonempty `CylinderStage` $`K~M`$. Then there is an infinite set $`A\subseteq\mathbb{N}`$ with $`0\notin A`$ and*

*``` math
\sum_{a\in A}\frac{1}{2^a-1}=\frac12.
```
Thus the universal irrationality assertion in Problem #257 is false under this cofinal-stage hypothesis. The formal proof does not construct the cofinal family of full-cylinder stages.*

</div>

<div id="prob:one-over-twenty-one-membership" class="problem">

**Problem 10** (membership of 1/21 in the Mersenne achievement set). Prove cofinal crossings of the exact moving lower separatrix
``` math
2\,\operatorname{scaledGreedyRemainder}(1/21,N)
 <\operatorname{mersenneScale}(N+1).
```
Equivalently, exclude the explicit fatal/cofinite/aligned branch $`\mathcal F_{21}`$. It is sufficient either to contradict the eventual permanent affine-supercapacity recurrence forced by that branch or to force an unbounded sequence of closed canonical quotient rows; neither sufficient route is claimed to be equivalent by itself.

</div>

<div id="prob:scaled-return" class="problem">

**Problem 11** (weakest native recurrence criterion). Does the scaled actual greedy remainder return cofinally to one bounded interval?
``` math
\exists B<\infty\ \forall K\ \exists N\ge K:
 \qquad 2^N r_N\le B.
```

</div>

<div id="prob:actual-invariant" class="problem">

**Problem 12** (actual-orbit invariant). Is there a finite-memory, $`2`$-adic or discrepancy invariant, using the correlated divisor pulses of the actual support, that forces a closed return or forbids permanent supercapacity? More precisely, can one use a bounded window of $`R\bmod6`$, residues of $`s_R`$, endpoint divisor counts and the finite set of eventual skips to force descent or a forbidden state? Alternatively, can one prove that no bounded-memory invariant distinguishes the true orbit from synthetic permanent-supercapacity controls?

</div>

<div id="prob:fatal-interval" class="problem">

**Problem 13** (final-skip Diophantine exclusion). Let $`E=\sum_{n\ge1}(2^n-1)^{-1}`$. If $`1/21\notin\mathcal A`$, let $`M`$ be the last skipped exponent, $`S_M`$ its finite skipped prefix, and
``` math
a_M=\frac1{21}+\sum_{d\in S_M}\frac1{2^d-1}.
```
Can the complete final-skip signatures be used to prove $`|E-a_M|\ge\operatorname{gap}_M`$, contradicting
``` math
0<a_M-E<\operatorname{gap}_M?
```

</div>

The logarithmic obstruction <a href="#eq:cover-log-obstruction" data-reference-type="eqref" data-reference="eq:cover-log-obstruction">[eq:cover-log-obstruction]</a> is necessary for a finite-cost positive cover. Determining when a converse holds would give an intrinsic description of that sufficient class. The mixed class is a finite-union ideal. Countable gluing needs an explicit tail budget: every prime singleton is admitted, while the full prime support has displacement greater than $`1/3`$ at every positive shift.

<a id="statements-and-declarations"></a>

# Statements and declarations

Theorem <a href="#res:reciprocal-support" data-reference-type="ref" data-reference="res:reciprocal-support">1</a>, the finite-period statement and the general repair criterion have formal counterparts in the supplied Lean corpus. Their mathematical assertions, historical antecedents and formal coverage are separate entries in the source record. The principal modules are `AllBaseReciprocalSupportIrrationality.lean`, `SignedFinitePeriodNoncollapse.lean` and `GreedyRepairCriterion.lean`. The source checkpoint is `99f4bf47422a`; later counterparts are identified separately rather than attributed to that checkpoint.

The weighted and cover arguments, the mixed theorem and the cost separations use the accompanying ordinary proofs: *Strengthened Variable-Exponent Cover*, *First Logarithmic Moment of Positive Covers*, *Mixed Support Synchronisation* and *Prime-Incidence Boundary*. The mixed proof’s complete parameter schedule is in `MixedSupportSynchronisation.md`, Sections 3–5. The analytic proof supplement also contains the tower-scale reciprocal-mass criterion and the prime-power thinning argument. No universal irrationality conclusion is asserted.

<a id="app:sources"></a>

# Guide to the formal sources

The following source links are the public snapshot used by this note.

[checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5091), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5246), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5221), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L5260). ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GenericTailOrbitRigidity.lean#L426)). [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/RationalSupportCarrySkeleton.lean#L2383). [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SublogDivisorCoverage.lean#L392). [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/RationalSupportCarrySkeleton.lean#L1480). [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/RationalSupportCarrySkeleton.lean#L2210). [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusCarry.lean#L949). [formalised here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L9045)\
([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L9103))\
[checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L12811); above ([residue class](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L11672), [odd](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L11686)); [checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L6035)\
[checked here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L6059)\
[formalised here](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L10776)\
[the exact checked statement](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L8328); ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L6272)). ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L14175)). [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L94), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L111), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L140). ([Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L71)), [the carry-aware no-go](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L274) [the digitwise no-go](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L292). [$`2^{\omega(n)}`$ incidence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L314) [the shift iff](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L335). [for $`\omega`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L441) [for the shifted incidence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/SquarefreeSupportIncidence.lean#L485). [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L9467) [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CertificateKernel.lean#L9476). [compact](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L656), [perfect](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L1656), [totally disconnected](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L1672), [nowhere dense](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L1681), [of measure one](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L996). ([Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L1458)). ([Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L1784)). ([definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L20), [Lean](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L24)). ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L30)), ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L54)), [digit strings vanishing off $`J`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L45) [restricted digit map](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L49), [supported digit set](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L63), [closed](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L66). [restricted achievement set](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L76); [the image theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L79). [compact](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L90) [closed](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L96). [support restriction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L103) [nowhere dense](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L112). [preperfect](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L120); [$`\mathcal A_J`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L150), [perfect](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L167). [controls digit terms](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L175), [the update formula](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L182). [exactly](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L203). [disjoint](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L262), [doubles the volume](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L286). [by definition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L300). [multiplies the face volume by $`2^{|F|}`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L313) [gives $`2^{-|F|}`$](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L349). [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L358). [measure zero](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L368). [the formal dichotomy](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/MersenneSubseriesRigidity.lean#L397). [the greedy form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyAchievementSet.lean#L2583), [the terminal-bit form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L126), [the skipped-rank form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfCylinderHalfMembershipClassification.lean#L213), [the fatal-gap equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfCylinderFatalGapRightTail.lean#L781), [its transfer to non-membership](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfCylinderFatalGapRightTail.lean#L787), [the finite-support exclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfCarryReachability.lean#L589). [the local row constructor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkipRowCofinal.lean#L55). [the upper-half Boolean fill](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkippedCoreExactRow.lean#L228). [the strict-positivity theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkipRowCofinal.lean#L32); [the cofinal-skip hypothesis](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkipRowCofinal.lean#L22), [the row fan-in](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkipRowCofinal.lean#L84). [the closed-set step](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusCofinalExactRows.lean#L71). [forward endpoint theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkipRowCofinal.lean#L97) [the checked equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusSkipRowCofinal.lean#L110). [achievement-set conclusion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TerminalOnlyScaledVanishing.lean#L165), [infinite-support lift](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TerminalOnlyScaledVanishing.lean#L221). [rational half counterexample](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/HalfCounterexampleFrontier.lean#L31), [universal-claim refutation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/HalfCounterexampleFrontier.lean#L39). [general band localization](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfGreedyTwoThirdsBand.lean#L88), [two-thirds band](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfGreedyTwoThirdsBand.lean#L127), [odd numerator bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfGreedyTwoThirdsBand.lean#L231). [integral safety](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/HalfGreedyTwoThirdsBand.lean#L185). [forced carry supply](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SupportSunflowerDichotomy.lean#L531) [irrationality endpoint](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SupportSunflowerDichotomy.lean#L540). [uniform tail selector](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SupportSunflowerDichotomy.lean#L406). [exact dilation identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CompositeDilationDefect.lean#L30). [prime-support no-defect](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CompositeDilationDefect.lean#L103), [prime specialization](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CompositeDilationDefect.lean#L119). [foreign-divisor classification](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CompositeDilationDefect.lean#L133) [defect bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CompositeDilationDefect.lean#L151). ([two-six witness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/CompositeDilationDefect.lean#L218)). [terminal-only bridge](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SuffixCylinderTerminalOnlyBridge.lean#L264), [infinite half-support](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SuffixCylinderTerminalOnlyBridge.lean#L277), [positive-support lift](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/SuffixCylinderTerminalOnlyBridge.lean#L287). ([identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/MobiusSignSupportNoGo.lean#L111), [bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/MobiusSignSupportNoGo.lean#L150)). [the formal theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos257/HalfCounterexampleFrontier.lean#L61). ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/Primitive23Multiplicity.lean#L52)), ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/Primitive23Multiplicity.lean#L26)). ([rank eleven](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/Primitive23Multiplicity.lean#L38), [multiples of ten](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/Primitive23Multiplicity.lean#L86)). [kernel checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyTrapDynamics.lean#L262), [kernel checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyTrapDynamics.lean#L189), [kernel checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyTrapDynamics.lean#L225). [kernel checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyTrapDynamics.lean#L152), [kernel checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyTrapDynamics.lean#L283). ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusCarry.lean#L2117)). ([support](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L32), [remainder](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L39)). [kernel checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L3507); [kernel checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5554); [kernel checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5658). ([kernel checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L231)). ([ancestor hole](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5179), [scaled skip](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L5223)). ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/GreedyTrapDynamics.lean#L275)). ([sufficient condition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusCarry.lean#L2843)) ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusCarry.lean#L1892)). [the exact equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/BooleanMobiusCarry.lean#L1927). [an exact one-sided approximation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L3735). ([order identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L3569), [lower bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/Erdos249257/TwentyOneQuotientGreedy.lean#L3583)).

<div class="thebibliography">

10 D. Duverney and Y. Tachiya, [*Refinement of the Chowla–Erdős method and linear independence of certain Lambert series*](https://danielduverney.fr/documents/theorie-des-nombres/DuverneyTachiya190522.pdf), Forum Math. 31 (2019), no. 6, 1557–1566, [DOI](https://doi.org/10.1515/forum-2018-0299). Corollary 1.2 gives the general $`F_s(E)`$ theorem and its monomial images under $`|q|^{\operatorname{lcm}(1,\dots,\ell)}\le s`$; Example 1.1 gives the joint squarefree family at all bases $`2^j`$, $`j\ge1`$. Both are on p. 4 of the linked author preprint; the proof is on pp. 9–11. T. Tao and J. Teräväinen, *Quantitative correlations and some problems on prime factors of consecutive integers*, arXiv:2512.01739 (submitted December 2025, revised April 2026). Theorem 1.3 proves $`\sum_{n\ge1}\omega(n)/2^n=\sum_p(2^p-1)^{-1}`$ irrational, settling the prime-support case of \#257 at base $`2`$; the extension to every integer base and the prime-power support are stated as remarks with the modifications left to the reader. The theorem is on p. 4 and its proof is Section 5, pp. 44–56, in arXiv v2. V. Kovač and T. Tao, *On several irrationality problems for Ahmes series*, Acta Math. Hungar. 175 (2025), 572–608, [DOI](https://doi.org/10.1007/s10474-025-01528-0). Remark 4.1 (p. 13) records the strict tail inequality and the Cantor structure. Theorem 2.3 (p. 5; proof pp. 13–14) constructs rational merged sums from several bases under its mass hypothesis; it is not a fixed-base counterexample. P. Erdős, *On arithmetical properties of Lambert series*, J. Indian Math. Soc. 12 (1948), 63–66. P. Erdős, [*On the irrationality of certain series*](https://users.renyi.hu/~p_erdos/1969-09.pdf), Math. Student 36 (1968), 222–226 (issued 1969). The theorem on p. 222 treats pairwise-coprime support with convergent reciprocal sum at every integer base $`b\ge2`$; the claimed removal of pairwise coprimality is stated without proof.

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.
