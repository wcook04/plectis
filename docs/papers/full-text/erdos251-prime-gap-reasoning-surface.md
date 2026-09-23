<a id="erdos251-prime-gap-reasoning-surface"></a>

# Prime-Gap Dyadic Series: Perturbations, Exact Criteria and Certificates

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

A convergent dyadic series with nonnegative integer coefficients can be made rational by adding nonnegative integer corrections on a sparse set. Given the original sequence, a finite prefix to retain, and any allowance $`f(n)`$ tending to infinity, we fix a set of permitted correction indices of upper Banach density zero and a nondegenerate interval above the original sum. Every target in this interval is attained by corrections supported in that set and eventually bounded by the prescribed function. Each fixed modulus eventually divides both the corrections and their cumulative sums, with a cutoff independent of the target. For the choice $`f(n)=(\log(n+3))^\varepsilon`$, $`\varepsilon>0`$, we can also make the total variation distance between the empirical unnormalised block distributions, sampled at integer starts in $`[X,2X)`$, tend to zero for lengths $`o(\log\log X)`$. The construction varies the split of a fixed total between adjacent coordinates and corrects the cumulative residue immediately before them. For prime gaps the cumulative positions remain asymptotic to $`n\log n`$, and the construction preserves the property that each fixed nonzero polynomial with integer coefficients in a fixed number of consecutive gaps vanishes only on a density-zero set. No primality conclusion is asserted for the cumulative positions.

For primes $`p_0=2,p_1=3,\ldots`$ and gaps $`g_n=p_{n+1}-p_n`$, summation by parts reduces the prime series to the gap series. The complete tails $`T_N=\sum_{j\ge1}g_{N+j}2^{-j}`$ satisfy $`T_{N+1}=2T_N-g_{N+1}`$; we use this recurrence to characterise rationality and to derive finite tests with explicit remainder bounds. Counterexamples show why several weaker coefficient conditions do not suffice. An exact finite certificate shows that a rational value of the prime series would have denominator at least $`2^{39998}>10^{12040}`$. This denominator bound does not establish irrationality.

<a id="long251:sec:problem"></a>

# Introduction

Throughout, the primes are indexed from zero: $`p_0=2`$, $`p_1=3`$, $`p_2=5`$, and $`g_n=p_{n+1}-p_n`$. Erdős Problem #251 concerns
``` math
\Pi=\sum_{n\ge0}\frac{p_n}{2^{n+1}}
     =2/2+3/4+5/8+7/16+\cdots,
```
with the question recorded in \[erdos1958, p. 94\], \[erdosgraham1980, p. 62\] and \[erdos1988, p. 103\]. The catalogue lists this as Problem #251 \[erdosproblems\]. We construct rational gap series that retain specified congruences and block statistics of the actual prime gaps. No condition in the construction guarantees that the cumulative positions are prime. We also give exact tail criteria for irrationality of $`\Pi`$, but do not establish them for the actual gaps. The first values are
``` math
\begin{array}{c|cccccccccc}
  i   & 0&1&2&3&4 &5 &6 &7 &8 &9\\\hline
  p_i & 2&3&5&7&11&13&17&19&23&29\\
  g_i & 1&2&2&4&2 &4 &2 &4 &6 &2
 \end{array}
```
Thus $`g_0=1`$ and every later gap is even, since all primes after $`2`$ are odd. The parity will matter in the criterion involving two consecutive tail differences. A second normalisation with denominator $`2^{\,i}`$ also occurs, and at every finite horizon it is exactly twice this one:
``` math
\sum_{i=0}^{n-1}\frac{p_i}{2^{\,i}}
 =2\sum_{i=0}^{n-1}\frac{p_i}{2^{\,i+1}} .
```
This [factor-of-two identity](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L111) preserves rationality. We use $`\Pi`$ as normalised above throughout.

The perturbation theorem in Section <a href="#long251:sec:paired-corrections" data-reference-type="ref" data-reference="long251:sec:paired-corrections">2</a> applies to arbitrary nonnegative integer coefficients. The independent actual-prime argument starts with summation by parts, identifies the complete tails and characterises their integral differences. Its finite certificates use an explicit prime bound, not the perturbation construction. The counterexamples in Section <a href="#long251:sec:obstructions" data-reference-type="ref" data-reference="long251:sec:obstructions">8</a> identify coefficient properties that cannot supply the missing prime-gap estimate.

<a id="notation."></a>

#### Notation.

We use $`\mathbb{N}=\{0,1,2,\ldots\}`$, write $`\varphi`$ for Euler’s totient function, and write $`\operatorname{den}q`$ for the positive denominator of $`q\in\mathbb{Q}`$ in lowest terms. The notation $`\operatorname{dist}(x,\mathbb{Z})`$ means the distance from $`x`$ to the nearest integer. A rational or real number is *integral* when it belongs to $`\mathbb{Z}`$. A sequence $`(a_n)`$ is *eventually periodic with period $`h\ge1`$* when $`a_{n+h}=a_n`$ for every sufficiently large $`n`$. A set $`A\subseteq\mathbb{N}`$ has *density zero* when $`|A\cap[1,x]|=o(x)`$, and a property holds for *almost all* indices when its exceptional set has density zero. A sum over an empty range of indices is zero. A property holds *cofinally* when it holds at arbitrarily large indices; this does not imply that those indices have positive density.

<a id="long251:sec:paired-corrections"></a>

# Sparse congruence-preserving perturbations

Two adjacent corrections can have a fixed ordinary sum while their dyadic contribution varies. For example, the pairs $`(0,6),(2,4),(4,2),(6,0)`$ at $`n,n+1`$ have ordinary sum $`6`$ and dyadic contributions $`6,8,10,12`$ divided by $`2^{n+2}`$. If the cumulative correction before them is $`1`$, adding $`1`$ at $`n-1`$ makes it even; changing the pair then preserves that residue.

Changing finitely many integer coefficients adds a dyadic rational and cannot alter rationality. To rationalise an irrational sum, we must therefore allow infinitely many corrections. The theorem repeats the paired operation with moduli divisible by every fixed integer eventually. Widely separated triples give sparse support. The range of choices at each triple is large enough to compensate for the intervening powers of two, so the attainable sums fill an interval. The permitted index set and the interval are chosen before the target.

<a id="density-and-block-conventions."></a>

#### Density and block conventions.

All intervals of indices contain integers, and $`\log`$ is natural unless a base is displayed. Upper Banach density zero means
``` math
\lim_{H\to\infty}\sup_{u\in\mathbb{N}}\frac{|S\cap[u,u+H)|}{H}=0.
```
For integers $`X\ge1`$ and $`m\ge1`$, let $`\mu_{a,X,m}`$ be the empirical probability measure obtained by choosing an integer $`n\in[X,2X)`$ uniformly and observing $`(a_n,\ldots,a_{n+m-1})`$. Equal blocks are counted with multiplicity. We use $`d_{\rm TV}(\mu,\nu)=\sup_B|\mu(B)-\nu(B)|`$. For the same function of the block, bounded in absolute value by $`B_0`$, its means under the two measures differ by at most $`2B_0d_{\rm TV}(\mu,\nu)`$. No rescaling of the coefficients is implicit.

<div id="long251:res:sparse-rationalisation" class="theorem">

**Theorem 1** (sparse changes preserving congruences). *Let $`a_n\in\mathbb{N}`$ and $`A=\sum_{n\ge0}a_n2^{-n-1}<\infty`$. For every cutoff $`K`$ and every $`f:\mathbb{N}\to\mathbb{R}`$ tending to infinity, there are a set $`S\subseteq[K,\infty)`$ of upper Banach density zero and a nondegenerate interval $`I\subset(A,\infty)`$ with the following property. Every $`r\in I`$ has the form
``` math
r=\sum_{n\ge0}(a_n+e_n)2^{-n-1},
```
where $`e_n\in\mathbb{N}`$ is supported on $`S`$, $`e_n\le f(n)`$ eventually, and, for every integer $`q\ge1`$, there is an $`N_q`$, chosen independently of $`r`$, such that
``` math
q\mid e_n\quad\hbox{and}\quad q\mid\sum_{i<n}e_i
 \qquad(n\ge N_q).
```
For every $`\varepsilon>0`$, the construction can instead be chosen with $`e_n\le(\log(n+3))^\varepsilon`$ eventually and $`|S\cap[X,2X)|=O_\varepsilon(X/\log\log X)`$. In that case the empirical distributions of original and corrected unnormalised blocks of length $`m(X)=o(\log\log X)`$, sampled at the same integer starts in $`[X,2X)`$, have total variation distance tending to zero, uniformly over $`r`$. Precisely the coupling error is at most $`m|S\cap[X,2X+m)|/X`$; with $`\|\Phi\|_\infty\le B_0`$ the bounded-test error is at most twice this quantity times $`B_0`$, also for tests depending on the starting index.*

</div>

Lean: [arbitrary word sparse rationalisation uniform](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/SparseAmbientR9.lean#L269), [polylogarithmic word interval uniform](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/SparsePaperR11.lean#L137), [bounded test finite coupling](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/SparseConstructionAudit.lean#L8).

The hypotheses allow any nonnegative integer sequence of polynomial growth, but not $`a_n=2^n`$, whose dyadic series diverges. The correction allowance can grow as slowly as $`\log\log(n+3)`$. A fixed bound is not possible here: eventual boundedness together with eventual divisibility by every fixed modulus would make the corrections eventually zero; their fixed total would then have to be divisible by every modulus and hence be zero. Nonnegative corrections could not change the sum. The set $`S`$ contains every permitted correction index; the nonzero corrections may occupy a smaller, target-dependent subset. Requiring upper Banach density zero is stronger than requiring ordinary density zero. For example, the union of the integer intervals $`[k!,k!+k)`$, $`k\ge3`$, has ordinary density zero but upper Banach density one. If $`k!\le x<(k+1)!`$, at most $`k(k+1)/2`$ indices have occurred, so their proportion is at most $`k(k+1)/(2k!)\to0`$. Nevertheless each interval is filled and their lengths are unbounded. The hypothesis rules out this concentration in long intervals, however far apart those intervals lie.

<div class="proof">

*Proof.* We first arrange the congruences, then choose sizes and spacings that respect $`f`$, and finally prove that every target in an interval is attained. Choose centres $`n_j`$, indexed by $`j\ge0`$, and an initial $`n_{-1}\ge K`$, with spacings $`s_j=n_j-n_{j-1}\ge4`$. Let $`M_j`$ be positive moduli with $`M_j\mid M_{j+1}`$, and put $`D_j=2^{s_j}-1`$. The value of $`D_j`$ is chosen so that the weighted range of one pair becomes a difference of two successive powers of $`1/2`$. Those differences will telescope in the interval argument. All these parameters will be chosen before the target.

*Preserving the congruences.* Let $`C_j`$ denote the cumulative correction before the triple at $`n_j`$. Starting with $`C_0=0`$, define
``` math
c_j=(-C_j)\bmod M_j,\qquad C_{j+1}=C_j+c_j+M_jD_j.
```
For any choice $`d_j\in\{0,\ldots,D_j\}`$, put
``` math
\begin{equation}
\label{long251:eq:sparse-triple}
 e_{n_j-1}=c_j,\qquad e_{n_j}=M_jd_j,\qquad
 e_{n_j+1}=M_j(D_j-d_j),
\end{equation}
```
and put $`e_n=0`$ off these triples. The spacing makes the triples disjoint. Their total is $`c_j+M_jD_j`$, independent of $`d_j`$, so $`C_j`$ really is the cumulative correction $`C_j=\sum_{i<n_j-1}e_i`$ before its residue correction, for every choice of the $`d_j`$. The pair alone could not repair that cumulative residue: its total is already a multiple of $`M_j`$. The residue correction does, since $`M_j\mid C_j+c_j`$.

The preceding correction contributes $`c_j2^{-n_j}`$ to the dyadic sum. It therefore changes the location of the attainable interval, although it does not change the range obtained by varying $`d_j`$.

Assume that each fixed $`q`$ divides $`M_j`$ eventually, and choose $`J`$ with $`q\mid M_J`$. At index $`n_J`$, just after its residue correction, the cumulative sum is divisible by $`q`$. Both entries of the pair are also divisible by $`q`$, so every later cumulative sum through that stage remains divisible by $`q`$. Inductively $`q\mid C_j`$ and $`q\mid M_j`$ imply $`q\mid c_j`$, since $`M_j\mid C_j+c_j`$. Thus every subsequent residue correction, pair entry and zero entry is divisible by $`q`$, as is every intermediate cumulative sum. We may take $`N_q=n_J`$. The first residue correction need not itself be divisible by $`q`$, and its coordinate $`n_J-1`$ is deliberately outside this eventual range.

*Keeping the corrections small and sparse.* The factorial modulus must grow to include every divisor, and the spacing must grow to make the support sparse. Since $`f`$ need not be monotone, we first replace it by a nondecreasing lower bound. Define
``` math
h(n)=\inf_{m\ge n}\min(f(m),m).
```
This finite real number is nondecreasing in $`n`$, satisfies $`h(n)\le n`$, and tends to infinity. Choose $`n_{-1}\ge K`$ with $`h(n_{-1})\ge32`$ and recursively set
``` math
\begin{equation}
\label{long251:eq:sparse-general-schedule}
 \begin{split}
 k_j&=\max\{k\in\mathbb{N}:k\ge2,\ k!2^{k+2}\le h(n_{j-1})\},\\
 M_j&=k_j!,\qquad s_j=k_j+2,\qquad n_j=n_{j-1}+s_j.
 \end{split}
\end{equation}
```
The maximum exists: $`k=2`$ is eligible and $`k!2^{k+2}`$ tends to infinity. Since $`h`$ is nondecreasing, the integers $`k_j`$ are nondecreasing; since $`n_j\to\infty`$, they tend to infinity. The factorials form a divisibility chain and eventually contain every fixed divisor, as do the distinguished terms in \[vandoornkovac2025, Proposition 8\]. At each of the three coordinates $`n`$ in stage $`j`$,
``` math
0\le e_n\le M_j2^{s_j}\le h(n_{j-1})\le f(n),
 \qquad e_n\le n_{j-1}<n.
```
Here the residue correction is smaller than $`M_j`$ and each pair entry is at most $`M_jD_j`$. Thus every correction series converges by comparison with $`\sum_n n2^{-n-1}`$.

Let $`S=\bigcup_j\{n_j-1,n_j,n_j+1\}`$. It is independent of the choices $`d_j`$. To see upper Banach density zero, fix $`H>0`$. Outside a finite initial segment, consecutive centres are at least $`H`$ apart, since $`s_j\to\infty`$. An interval of length $`L`$ therefore meets at most $`3(L/H+2)`$ late permitted correction indices, plus the fixed finite number of early indices. Divide by $`L`$, take the supremum over interval positions, then let $`L\to\infty`$ and $`H\to\infty`$.

*Filling an interval.* The preceding choices satisfy the size and congruence requirements. We now show that their weighted sums have no gaps. Put $`w_j=M_j2^{-n_j-2}`$ and
``` math
F_j=\sum_{i\ge j}D_iw_i,\qquad
 \beta=\sum_{j\ge0}\bigl(c_j2^{-n_j}+D_jw_j\bigr).
```
The size estimates just proved give convergence of both series, $`F_j\to0`$, and $`F_0>0`$. The constant $`\beta`$ is positive and independent of the choices $`d_j`$. The complete weighted correction, including every residue correction, is exactly
``` math
\begin{equation}
\label{long251:eq:sparse-baseline}
 \sum_n e_n2^{-n-1}=\beta+\sum_jd_jw_j.
\end{equation}
```
For $`i>j`$, we have $`M_i\ge M_j`$ and
``` math
D_iw_i=M_i\bigl(2^{-n_{i-1}-2}-2^{-n_i-2}\bigr)
 \ge M_j\bigl(2^{-n_{i-1}-2}-2^{-n_i-2}\bigr).
```
For $`J>j`$, the finite sum is therefore at least $`M_j(2^{-n_j-2}-2^{-n_J-2})`$. Since $`n_J\to\infty`$, letting $`J\to\infty`$ yields $`F_{j+1}\ge w_j`$. Adjacent intervals $`[dw_j,dw_j+F_{j+1}]`$, for $`0\le d\le D_j`$, therefore overlap or touch. Their union is $`[0,F_j]`$; no strict inequality is needed. For any $`y\in[0,F_0]`$, choose successive integers $`d_j`$ leaving each remainder in $`[0,F_{j+1}]`$. Since these capacities tend to zero, the resulting series has sum $`y`$. The finite choice set $`\{0,w_j,\ldots,D_jw_j\}`$ has maximum and diameter $`D_jw_j`$ and largest successive gap $`w_j`$. The size estimates give $`\sum_jD_jw_j<\infty`$; together with $`w_j\le F_{j+1}`$, this verifies the hypotheses of the covering lemma of Crmarić–Kovač \[crmarickovac2025, Lemma 4\]. Fridy’s generalised-base lemma \[fridy1966, Lemma, p. 194\] and the reciprocal-choice argument in Kovač–Tao \[kovactao2024, Lemma 5.1\] are antecedents. The finite-choice argument needs no monotonicity of the weights: increasing $`n_j`$ alone would not ensure that $`w_j=M_j2^{-n_j-2}`$ decreases, since the moduli also grow. Only the covering inequality $`w_j\le F_{j+1}`$ is used. Equation <a href="#long251:eq:sparse-baseline" data-reference-type="eqref" data-reference="long251:eq:sparse-baseline">[long251:eq:sparse-baseline]</a> therefore realises every $`r`$ in the fixed interval $`I=(A+\beta,A+\beta+F_0)\subset(A,\infty)`$.

*Preserving growing blocks.* The spacing controls how many coordinates are changed, whereas the product $`M_j2^{s_j}`$ controls their size. For a prescribed $`\varepsilon>0`$, allow exponents $`\varepsilon/4`$ for $`M_j`$ and $`\varepsilon/2`$ for $`2^{s_j}`$. Their sum is less than $`\varepsilon`$, leaving room in the correction bound. Replace <a href="#long251:eq:sparse-general-schedule" data-reference-type="eqref" data-reference="long251:eq:sparse-general-schedule">[long251:eq:sparse-general-schedule]</a> by
``` math
\begin{equation}
\label{long251:eq:sparse-polylog-schedule}
 \begin{split}
 s_j&=\left\lfloor\frac{\varepsilon}{2}
          \log_2\log(n_{j-1}+3)\right\rfloor,\qquad n_j=n_{j-1}+s_j,\\
 k_j&=\max\{k\in\mathbb{N}:k\ge2,\ k!\le(\log(n_{j-1}+3))^{\varepsilon/4}\},
 \qquad M_j=k_j!.
 \end{split}
\end{equation}
```
Take the initial cutoff so large that $`s_j\ge4`$ and the maximum is nonempty from the first step. Again $`k_j`$ is nondecreasing and tends to infinity. Keep $`D_j=2^{s_j}-1`$ and the same recursion for $`c_j`$. All triple entries obey
``` math
e_n\le M_j2^{s_j}\le(\log(n_{j-1}+3))^{3\varepsilon/4}
 \le(\log(n+3))^\varepsilon.
```
Enlarge the initial cutoff, if necessary, so that $`(\log(n_{j-1}+3))^{3\varepsilon/4}\le n_{j-1}`$ from the first step. Then every correction again satisfies $`e_n\le n`$, and the common bound $`\sum_n n2^{-n-1}<\infty`$ gives convergence of $`F_j`$ and $`\beta`$. The congruence and interval arguments therefore apply to this schedule. Also $`s_j`$ is comparable, with constants depending on $`\varepsilon`$, to $`\log\log(n_{j-1}+3)`$, and $`s_j=o(n_{j-1})`$. Hence consecutive centres near $`X`$ are separated by at least a constant multiple of $`\log\log X`$, giving $`|S\cap[X,2X)|=O_\varepsilon(X/\log\log X)`$. The estimate on $`[X,3X)`$ follows by covering it with $`[X,2X)`$ and $`[2X,4X)`$.

Finally sample both length-$`m`$ blocks at the same uniform integer start in $`[X,2X)`$. They can differ only if that block meets $`S`$. Each changed coordinate belongs to at most $`m`$ such blocks, so the total variation distance is at most $`m|S\cap[X,2X+m)|/X`$. If a test bounded by $`B_0`$ also depends on the starting index, its two values still agree on every unchanged block at that same index and differ by at most $`2B_0`$ elsewhere. Its mean difference is therefore bounded by $`2B_0m|S\cap[X,2X+m)|/X`$ as well. This conclusion uses the coupling, not just the marginal distributions of the blocks. If $`m\le X`$, then $`[X,2X+m)\subseteq[X,3X)`$, so the preceding support estimate gives
``` math
\frac{m\,|S\cap[X,2X+m)|}{X}
 =O_\varepsilon\!\left(\frac{m}{\log\log X}\right).
```
For integer $`m=m(X)=o(\log\log X)`$, the condition $`m\le X`$ holds for all large $`X`$ and the bound tends to zero. This comparison uses unnormalised blocks of coefficient values. It requires neither a limiting distribution nor any randomness or independence in the original sequence. ◻

</div>

Identical marginal distributions alone would not control an index-dependent test. For example, let $`a_n=n\bmod2`$ and $`b_n=1-a_n`$. For every even $`X`$, their one-coordinate empirical distributions on $`[X,2X)`$ are equal, but the test $`\mathbf{1}_{\{x=n\bmod2\}}`$ has mean $`1`$ for $`(n,a_n)`$ and $`0`$ for $`(n,b_n)`$. This example is not a sparse perturbation; it isolates why the proof couples blocks at the same index.

The comparison concerns absolute, not relative, error in event frequencies. For example, it applies to fixed block lengths and to $`m(X)=\lfloor\sqrt{\log\log X}\rfloor`$ for large $`X`$, but makes no vanishing-error assertion for lengths comparable to $`\log\log X`$. An $`o(1)`$ change may erase an event whose probability tends to zero; relative preservation requires an error small compared with that probability. The comparison is of finite coefficient blocks, not complete weighted tails: coefficients beyond an unchanged block can still change its tail.

The printed construction and the formal construction use different corrections. Their statements and quantifier order are compared in Appendix <a href="#long251:app:index" data-reference-type="ref" data-reference="long251:app:index">13</a>.

<div id="long251:res:local-targets" class="corollary">

**Corollary 2** (target intervals arbitrarily close to the original sum). *For the sparse theorem for an arbitrary sequence, the target interval can additionally be required to lie in $`(A,A+\eta)`$ for any prescribed $`\eta>0`$.*

</div>

Lean: [local target interval](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/LocalTargetInterval.lean#L38).

<div class="proof">

*Proof.* In the general schedule, every supported entry satisfies $`e_n\le n`$. Choose an integer $`K'\ge K`$ sufficiently large that $`\sum_{n\ge K'}n2^{-(n+1)}=(K'+1)2^{-K'}<\eta`$, and start the construction beyond $`K'`$. This still leaves the originally prescribed prefix unchanged. The complete interval of corrections has positive lower endpoint and upper endpoint at most this sum. Thus the interval may be chosen as close to $`A`$ as desired; this does not say that one fixed allowance permits every target above $`A`$. ◻

</div>

<a id="long251:sec:context"></a>

# Context and mathematical dependencies

<a id="relation-to-prior-work."></a>

#### Relation to prior work.

The passage from the primes to their gaps is already public. Tao posted on the problem’s forum thread on 7 October 2025 that summation by parts makes the question equivalent to irrationality of $`\sum_n(p_{n+1}-p_n)2^{-n}`$, and named the shape of the missing input as a sufficiently quantitative and uniform prime-tuples hypothesis giving statistical control of the binary expansion of about $`\log\log n`$ consecutive gaps \[erdosproblems251thread, comment of 7 October 2025\]. Theorem <a href="#long251:res:infinite" data-reference-type="ref" data-reference="long251:res:infinite">5</a> below is that reduction in exact form, with the endpoint retained, with convergence supplied by an elementary bound, and with the statement checked by the Lean kernel. The elementary bound replaces the prime number theorem in this reduction. The prime number theorem is still used in the different argument establishing $`P_n\sim n\log n`$ in Corollary <a href="#long251:res:jointcountermodel" data-reference-type="ref" data-reference="long251:res:jointcountermodel">27</a>; that application also uses Schlage-Puchta’s fixed-polynomial theorem.

A sufficiently uniform Hardy–Littlewood hypothesis gives conditional results of a different kind. Land’s draft states conditional irrationality \[land2026, Conjecture 1, Theorem 2\]; Ringer’s draft states conditional normality in each integer base \[ringer2026\]. For a fixed base $`b\ge2`$, the number in the latter statement is $`\sum_{n\ge0}p_n b^{-(n+1)}`$, and normality is to base $`b`$. Changing $`b`$ changes the number; this is not absolute normality of a single constant. The authors supply formalisation material, which has not been independently rebuilt for this revision. The uniform hypothesis in \[kuperberg2023, Conjecture 1.3\] counts prime translates of every nonempty admissible tuple of $`k\le(\log\log x)^3`$ distinct integer shifts in $`[0,(\log x)^2]`$. Its main term is the tuple’s singular series times $`\int_2^x(\log t)^{-k}\,dt`$, with absolute error at most $`Cx^{1-\delta}`$. The logarithmic integral cannot simply be replaced by its leading asymptotic while retaining that error bound. Here admissible means that the shifts omit a residue class modulo each prime. The positive constants $`C,\delta`$ and the starting threshold are chosen before $`x`$ and the tuple. Qualitative asymptotics for each fixed tuple do not provide this uniformity.

In the version rechecked on 18 September 2026, Ringer also gives weaker assumptions for the joint positions of the first $`L`$ primes after a prime basepoint, with $`L`$ growing on the order of $`\log\log X`$. These are not single-gap marginal estimates. Here $`X`$ measures prime values: the basepoints are primes in $`(X,2X]`$, sampled uniformly. One assumption controls a weighted sum of adverse tuple-count errors; another permits bounded domination by a comparison law rather than total-variation approximation. In the weighted error condition, the adverse direction alternates with the order in inclusion–exclusion: undercounts matter at some orders and overcounts at others. An upper sieve estimate alone does not supply these assumptions, and none is used below.

Our index band $`[X,2X)`$ corresponds to primes in $`[p_X,p_{2X})`$. The prime number theorem gives $`\pi(2p_X)=2X+o(X)`$, so this set and $`(p_X,2p_X]`$ have symmetric difference of size $`o(X)`$ and each has $`X+o(X)`$ elements. Their uniform measures share mass equal to the intersection size divided by the larger sample size. This tends to $`1`$, so their total variation distance is $`o(1)`$. The comparison uses the same uniformly bounded observable, with the same normalisation at common basepoints. It does not by itself transfer the stronger weighted, relative, or quantitative estimates for growing prime patterns.

Erdős stated on p. 93 of the 1958 article that $`\sum_{n\ge1}p_{n-1}^{k}/n!`$ is irrational for every $`k\ge1`$, and wrote there that the proof for $`k>1`$ is complicated enough that only the case $`k=1`$ is printed \[erdos1958, pp. 93–95\]. A proof of the full family appears in Schlage-Puchta’s Theorem 3, which gives the stronger statement that $`1,S_0,S_1,S_2,\ldots`$ are linearly independent over $`\mathbb{Q}`$, where $`S_k=\sum_{n\ge1}p_{n-1}^{k}/n!`$ in our zero-based indexing \[schlagepuchta2011, Theorem 3\].

On page 103 of his 1988 problem paper Erdős separately stated the fixed-denominator problem: he could not prove that $`\sum_{n\ge1}p_{n-1}^{k}/2^{n}`$ is irrational for every $`k\ge1`$, and wrote that the case $`k=1`$ was probably already very difficult. He also stated the variable-denominator expectation that $`\sum_{n\ge1}p_{n-1}/(d_1\cdots d_n)`$ is irrational whenever $`d_n\ge2`$ and $`d_n=o(p_{n-1})`$ \[erdos1988, p. 103\]. That expectation is false: on 15 April 2026 Kovač posted a note, with the printed attribution ChatGPT 5.4 Pro (orchestrated by Vjeko Kovač), constructing such a sequence $`(d_n)`$ for which the sum is exactly $`1`$ \[kovac2026, Theorem 1 and proof, pp. 1–2\].

Section 3 of the 1958 article concerns variable product denominators, not the dyadic denominator sequence \[erdos1958, pp. 96–97\]. Its printed growth condition (5) uses nonstandard asymptotic typography; we neither use that condition as a hypothesis nor assign it a modern quantified interpretation. The simple endpoint example is unambiguous: if $`G_n=\prod_{j=1}^n(p_{j-1}+1)`$ and $`G_0=1`$, then
``` math
\frac{p_{n-1}}{G_n}=\frac1{G_{n-1}}-\frac1{G_n},\qquad
 \sum_{n\ge1}\frac{p_{n-1}}{G_n}=1.
```
Neither this variable-denominator example nor the counterexample in \[kovac2026\] addresses fixed dyadic denominators.

There is a related theorem with dyadic denominators and bounded coefficients. If $`P(m)`$ denotes the largest prime factor of $`m`$, Erdős and Pomerance proved that
``` math
\sum_{m\ge2}\frac{\mathbf 1_{\{P(m)>P(m+1)\}}}{2^m}
```
is irrational \[erdospomerance1978, §7, p. 320\]. Erdős and Graham record the complementary indicator on p. 62: equality of the two largest prime factors is impossible for consecutive integers, so its series is $`1/2`$ minus the displayed one and is irrational as well. That theorem concerns a sequence of zeros and ones comparing largest prime factors, whereas the numerators in $`\Pi`$ are unbounded.

Schlage-Puchta gives a necessary condition for rationality of a number formed by concatenating integer blocks in a base $`b\ge2`$ that is not a proper power, under the stated monotonicity and growth assumptions \[schlagepuchta2011, Theorem 2, p. 1\]. The positions of those blocks depend on their lengths; they are not the fixed positions of the coefficients in our series. This concatenation theorem is not used here. The input we use is his Lemma 4. For each fixed nonzero polynomial $`F\in\mathbb{Z}[x_0,\ldots,x_k]`$, the actual prime gaps satisfy $`F(g_n,\ldots,g_{n+k})\ne0`$ outside a set of indices of natural density zero \[schlagepuchta2011, Lemma 4, pp. 5–6\]. Its proof uses Selberg’s sieve. Section <a href="#long251:sec:obstructions" data-reference-type="ref" data-reference="long251:sec:obstructions">8</a> draws two consequences from it.

Theorems <a href="#long251:res:boundedperturbation" data-reference-type="ref" data-reference="long251:res:boundedperturbation">22</a> and <a href="#long251:res:sparse-rationalisation" data-reference-type="ref" data-reference="long251:res:sparse-rationalisation">1</a> fill intervals of attainable values. The first is a binary expansion. For the second, the direct reference is Crmarić–Kovač’s finite-choice covering lemma \[crmarickovac2025, Lemma 4\]. For finite nonnegative choice sets, each with at least two elements and with summable maxima, their lemma gives a single interval when each stage’s largest successive gap is at most the sum of the later diameters. They apply it to product-denominator series. In the notation of the proof of Theorem <a href="#long251:res:sparse-rationalisation" data-reference-type="ref" data-reference="long251:res:sparse-rationalisation">1</a>, the choices are $`\{0,w_j,\ldots,D_jw_j\}`$, and the required inequality is $`w_j\le\sum_{i>j}D_iw_i`$. Fridy’s generalised-base lemma \[fridy1966, Lemma, p. 194\] is an antecedent with nonincreasing weights; the finite-choice form avoids that additional assumption. Kovač–Tao use sets of reciprocal choices \[kovactao2024, Lemma 5.1, Theorem 2.5\]. Van Doorn–Kovač use finite subsums and a distinguished subsequence of denominators: each distinguished denominator is divisible by every earlier denominator, and each positive integer divides some denominator \[vandoornkovac2025, Lemma 7, Proposition 8\]. Hence every fixed positive integer divides all sufficiently late distinguished denominators. It is this eventual divisibility, not a condition on every denominator in their sequence, that our factorial moduli share. At a distinguished cutoff, their finite sums are all multiples of the reciprocal of the last denominator. Summing the covering inequalities between successive distinguished cutoffs gives the hypothesis of their Lemma 7 for the whole finite prefix. That lemma leaves no gaps in this grid between zero and the full finite sum. Once the target’s denominator divides that last denominator and the target lies in this range, a finite representation follows. Their proposition thus represents rational targets in a half-open interval by finite subsums, whereas our infinite choices attain every real target in a fixed interval.

A further comparison is van Doorn’s exchange $`\{21d,28d\}\leftrightarrow\{20d,30d\}`$: both reciprocal sums are $`1/(12d)`$, while the ordinary sums are $`49d`$ and $`50d`$ \[vandoorn2025, proof of Theorem 3\]. Our paired corrections preserve the ordinary sum and vary the dyadic contribution instead. This is an analogy between conserved quantities, not an application of his partition theorem. We claim no new interval-covering principle.

For binary subsums, each term is either retained or omitted; the set of all resulting sums is called the achievement set. The powers $`2^{-n}`$, $`n\ge1`$, fill $`[0,1]`$ by binary expansion. In contrast, the powers $`3^{-n}`$ omit $`(1/6,1/3)`$, since all terms after the first sum to $`1/6`$. More complicated subsum sets can contain intervals even when the simple covering inequality fails at some indices. Bartoszewicz–Filipczak–Szymonik use a central run of attainable integer block sums to obtain interior in a multigeometric family \[bartoszewicz2014, Theorem 2\]. Prus-Wiśniowski–Ptak construct Cantorvals for which the overlap indices $`\{n:a_n\le\sum_{i>n}a_i\}`$ have density zero \[prusptak2024, Theorem\]. These compact sets equal the closure of their interiors, and both endpoints of every nondegenerate interval component are accumulation points of one-point components. Thus a finite-stage gap between possible subsums does not by itself rule out an interval elsewhere in the full set of subsums. Nor is it enough merely to know that neither comparison between a term and its remaining tail holds eventually. The survey \[glabprus2025, §1\] records the surrounding classification. Our variable-digit proof verifies covering at every stage and does not depend on a classification theorem for binary subsums. Nitecki’s preprint \[nitecki2015, Theorem 14\] gives an exposition explicitly crediting the Guthrie–Nymann classification; its title and numbering differ from the published Monthly article.

The inequality pattern alone is insufficient even when its index set is specified exactly: Marchwicki–Miska’s construction \[marchwickimiska2021, Theorem 2.1\], with the repaired proof in \[miskaprusptak2023\], can realise any infinite strict term-dominating index set with a Cantor achievement set. The repair preserves the original uniqueness conclusion; the latter paper also gives a simpler proof of a weaker statement without uniqueness. Nowakowski’s Star Procedure \[nowakowski2025, Definition 2, Theorem 3.1\] is a different sufficient route to a Cantorval, requiring every stage of a positivity recursion. These comparisons explain why our proof checks overlap at every stage instead of relying only on the set of indices at which overlap occurs.

<a id="automatic-sequences-and-the-limit-of-the-analogy."></a>

#### Automatic sequences and the limit of the analogy.

Adamczewski–Drmota–Müllner compute logarithmic densities for each fixed automatic sequence along primes. Their Theorem 1.2 also gives a sufficient condition for natural densities to exist and be rational; Theorem 1.4 reduces the logarithmic-density calculation to integers coprime to a suitable fixed modulus \[adm2022, Theorems 1.2, 1.4\]. The general logarithmic densities are not all rational. The fixed finite-alphabet automaton is essential: the result is not a theorem about unbounded consecutive prime gaps, their complete dyadic tails, or a growing family of residue or carry automata. Any such application would have to specify the automaton, prove that it computes the required observable, and supply uniform errors as its state space grows. We do not infer any of those steps from the density theorem.

<a id="the-uniformity-required-from-prime-statistics."></a>

#### The uniformity required from prime statistics.

Kuperberg’s large-set singular-series estimates allow a specified growing cardinality, not arbitrary dimension \[kuperberg2023, Theorem 1.1\]. Her arithmetic-progression and smooth-weight estimates are a useful fixed-parameter comparison \[kuperbergweighted2025\]; they do not by themselves give a law for ordered consecutive-gap blocks. Jha’s revised Poisson-tail preprint \[jha2026\] concerns growing short-interval prime counts under a strong Hardy–Littlewood hypothesis. Counting primes in an interval does not by itself control the weighted differences of consecutive gaps used by our tail criteria. We do not infer the required estimates for growing blocks from these results or from a fixed-dimensional limit theorem.

At the cited revision, Problem #251 appears as an unproved statement in the *Formal Conjectures* repository \[formalconjectures251\]. Its zero-based Lean sum starts with the zeroth prime over $`2^0`$, so it is twice the displayed normalisation and has equivalent irrationality status; its proof is `sorry`.

<a id="the-strategy."></a>

#### The strategy.

An ordinary binary expansion uses digits in $`\{0,1\}`$ and is rational exactly when those digits are eventually periodic. The primes $`p_n`$ are coefficients, not binary digits; carrying them changes the sequence to which this criterion applies. Even bounded integer coefficients can be nonperiodic and have a rational dyadic sum, as Proposition <a href="#long251:xr:boundedpolignac" data-reference-type="ref" data-reference="long251:xr:boundedpolignac">39</a> illustrates. A different classical approach uses the growth of denominators in series of unit fractions. Erdős and Straus named a sum $`\sum_k 1/a_k`$ over a strictly increasing sequence of positive integers an *Ahmes series* \[erdosstraus1963\]; for such a series the condition $`a_k^{1/2^k}\to\infty`$ is sufficient for irrationality. Its growth scale is sharp: replacing divergence by a sufficiently large fixed lower threshold does not suffice, since shifted Sylvester sequences grow like $`C^{2^{k}}`$ for arbitrarily large $`C`$ and have rational reciprocal sum. This is not a necessary condition for irrationality. Both statements and their attribution are recorded in the introduction of Kovač and Tao \[kovactao2024, §1\]. Splitting each term $`p_i/2^{\,i+1}`$ into $`p_i`$ copies of $`2^{-(i+1)}`$ writes $`\Pi`$ as a sum of unit fractions with repetitions, and the denominators occurring in it are exactly the powers of two. Even ignoring the repetitions the growth hypothesis fails, since $`(2^{\,n})^{1/2^{\,n}}\to1`$, and the growth criterion does not apply.

For the dyadic series below, we instead examine the reduced denominators of the complete tails under a rationality assumption. Rationality of the sum is equivalent to an eventual integrality condition on differences of those tails, and that equivalence uses nothing about the numerators beyond the fact that they are integers. The condition does not by itself force the numerators to repeat: Proposition <a href="#long251:res:telescope" data-reference-type="ref" data-reference="long251:res:telescope">31</a>, applied to $`K_n=n`$, produces the integer sequence $`\kappa_n=n-1`$, which is unbounded and hence not eventually periodic, and whose dyadic sum is zero.

<a id="proof-dependencies."></a>

#### Proof dependencies.

The sparse theorem is independent of primes: residue correction and finite-choice covering give the interval, and counting changed starts gives its statistical consequences. Applying this construction to prime gaps then uses Schlage-Puchta’s lemma and the prime number theorem. The recurrence classification needs integer coefficients and Euler’s congruence, not any prime-tuple conjecture. The signed certificate bounds one tail difference using an explicit majorant and exact finite prime data. To prove irrationality by this local criterion, it would suffice to establish the simultaneous inequalities of Section <a href="#long251:sec:open" data-reference-type="ref" data-reference="long251:sec:open">10</a> arbitrarily late for every positive shift. We do not prove that condition or assert that it is necessary. The appendices give the finite computations, further equivalent criteria, complete counterexamples and formal references. The short paper gives the main construction and the prime-tail criterion without these extensions.

<a id="long251:sec:parts"></a>

# Summation by parts, with the endpoint retained

Summation by parts expresses a weighted sum of a sequence in terms of its first value, its consecutive differences and one final term. We use finite sums first, so the identity needs neither growth nor convergence assumptions. The linked definitions are the [dyadic partial sum](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L101) and the [weighted sum of consecutive differences](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L121). The formula below writes both sums explicitly.

<div id="long251:res:abel" class="proposition">

**Proposition 3** (finite summation by parts). *For every rational sequence $`P`$ and every $`n\ge0`$,
``` math
\sum_{i=0}^{n}\frac{P(i)}{2^{\,i+1}}
 =P(0)+\sum_{i=0}^{n-1}\frac{P(i+1)-P(i)}{2^{\,i+1}}
       -\frac{P(n)}{2^{\,n+1}} .
```*

</div>

Lean: [dyadic partial sum q eq start add differences](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L138).

<div class="proof">

*Proof.* At $`n=0`$ both sides equal $`P(0)/2`$. When $`n`$ is replaced by $`n+1`$, the change on the right is
``` math
\frac{P(n+1)-P(n)}{2^{n+1}}
 -\frac{P(n+1)}{2^{n+2}}+\frac{P(n)}{2^{n+1}}
 =\frac{P(n+1)}{2^{n+2}}.
```
This is the next term on the left, which proves the identity by induction. ◻

</div>

Specialising to $`P(i)=p_i`$, whose first value is $`p_0=2`$, and writing $`g_i=p_{i+1}-p_i`$ for the zero-based gaps, gives the reformulation.

<div id="long251:res:parts" class="theorem">

**Theorem 4** (prime-gap reformulation). *Let $`p_0=2,p_1=3,\ldots`$ be the primes in increasing order and $`g_i=p_{i+1}-p_i`$. For every $`n\ge0`$,
``` math
\sum_{i=0}^{n}\frac{p_i}{2^{\,i+1}}
 =2+\sum_{i=0}^{n-1}\frac{g_i}{2^{\,i+1}}-\frac{p_n}{2^{\,n+1}} .
```*

</div>

Lean: [prime0 dyadic summation by parts](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L172).

The leading $`2`$ is the first prime, not a normalising constant. At $`n=2`$, for instance, the left side is $`2/2+3/4+5/8=19/8`$ and the right side is $`2+(1/2+2/4)-5/8=19/8`$.

<a id="long251:sec:infinite"></a>

## The infinite identity and the irrationality equivalence

Write
``` math
u_n=\frac{p_n}{2^{\,n+1}},\qquad
 v_n=\frac{g_n}{2^{\,n+1}}
```
for the terms of the prime series and of the gap series, so that $`\sum_{n\ge0}u_n=\Pi`$. The termwise identity $`v_n=2u_{n+1}-u_n`$ is the [dyadic discrete derivative](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L202). It expresses each gap term as an integer combination of two consecutive prime terms, so once $`(u_n)`$ is summable the gap series can be summed by rearranging two copies of the prime series.

<div id="long251:res:infinite" class="theorem">

**Theorem 5** (infinite prime-gap identity). *Both series converge and
``` math
\sum_{n\ge0}\frac{p_n}{2^{\,n+1}}
 \;=\;2+\sum_{n\ge0}\frac{g_n}{2^{\,n+1}} .
```*

</div>

Lean: [infinite prime gap identity](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L47).

<div class="proof">

*Proof.* The bound $`p_n\le1250(n+1)^4`$ of Appendix <a href="#long251:app:prime-bound" data-reference-type="ref" data-reference="long251:app:prime-bound">11</a> makes $`(u_n)`$ summable, and $`0<g_n\le p_{n+1}`$ then makes $`(v_n)`$ summable. The shifted sequence $`(u_{n+1})`$ is summable, so summing $`v_n=2u_{n+1}-u_n`$ and using $`u_0=1`$ gives
``` math
\sum_{n\ge0}v_n
 =2\left(\sum_{n\ge0}u_n-u_0\right)-\sum_{n\ge0}u_n
 =\sum_{n\ge0}u_n-2 . \qedhere
```
 ◻

</div>

The prime number theorem is needed neither for this convergence nor for the identity. Its asymptotic $`p_n\sim n\log n`$ is used in Corollary <a href="#long251:res:nonconc-primes" data-reference-type="ref" data-reference="long251:res:nonconc-primes">25</a> and in the argument counting repeated tail values \[mv2007, Chapter 6\].

<div id="long251:res:irr-equivalence" class="corollary">

**Corollary 6** (exact irrationality reformulation). *<span id="res:irr-equivalence" label="res:irr-equivalence"></span> $`\Pi`$ is irrational if and only if $`S=\sum_{n\ge0}g_n2^{-(n+1)}`$ is irrational. The corresponding zero-based series with denominator $`2^n`$ equals $`4+2S`$ and has the same irrationality status.*

</div>

Lean: [irrationality reformulation](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L56).

<div class="proof">

*Proof.* The identity just proved gives $`\Pi=2+S`$. Adding a rational constant or multiplying by a nonzero rational number preserves rationality and irrationality. ◻

</div>

Concretely, $`\Pi=3.674643966\ldots`$ is irrational if and only if $`S=1.674643966\ldots`$ is. Neither irrationality statement is established here.

<a id="long251:sec:tail"></a>

# The tail recurrence and the exact criteria

Rescaled tails turn the series question into a recurrence. Suppose $`\sum_{i\ge0}a_i2^{-(i+1)}`$ converges with every $`a_i`$ an integer, and rescale its tails by putting
``` math
T_N=2^{\,N+1}\sum_{i>N}\frac{a_i}{2^{\,i+1}}
    =\sum_{j\ge1}\frac{a_{N+j}}{2^{\,j}} .
```
Two facts follow immediately. First $`T_{N+1}=2T_N-a_{N+1}`$, so advancing one index doubles the rescaled tail and subtracts a single coefficient. Second $`T_0=2\sum_{i\ge0}a_i2^{-(i+1)}-a_0`$, so the sum is rational exactly when $`T_0`$ is. This section studies that recurrence, assuming nothing about the coefficients beyond the fact that they are integers, and resumes the prime-gap instance at the end.

<div id="long251:def:rec" class="definition">

**Definition 7**. Let $`g:\mathbb{N}\to\mathbb{Z}`$ and $`T:\mathbb{N}\to\mathbb{Q}`$ or $`T:\mathbb{N}\to\mathbb{R}`$. Say $`T`$ satisfies the *dyadic tail recurrence* with *coefficients* $`g`$ when $`T_{N+1}=2T_N-g_{N+1}`$ for every $`N`$. Write $`\sigma_h(N)=T_{N+h}-T_N`$ for the *shift* of length $`h`$ at $`N`$, and call a real number *integral* when it belongs to $`\mathbb{Z}`$.

</div>

For a complete-tail example, take $`g_n=2`$ for odd $`n\ge1`$ and $`g_n=4`$ for even $`n\ge1`$. Its complete tail at index $`0`$ is $`T_0=(2/2+4/4)/(1-1/4)=8/3`$, and the tails alternate between $`8/3`$ and $`10/3`$. Thus $`\sigma_1(N)`$ is always $`2/3`$ or $`-2/3`$, whereas $`\sigma_2(N)=0`$ for every $`N`$. Nonintegrality at one prescribed shift length does not imply irrationality, even for positive even coefficients and genuine tails.

Modulo integers, the recurrence is repeated doubling: the coefficient term does not affect the fractional part. An integral shift means that the fractional part has returned to an earlier value. Iterating the recurrence $`h`$ times makes this observation explicit: it multiplies $`T_N`$ by $`2^{h}`$ and accumulates an integer. Define $`B_{0,N}=0`$ and $`B_{h+1,N}=2B_{h,N}+g_{N+h+1}`$, so that $`B_{h,N}=g_{N+1}2^{\,h-1}+\cdots+g_{N+h}`$ is the [weighted integer sum](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L647) accumulated in those $`h`$ steps.

<div id="long251:res:block" class="theorem">

**Theorem 8** (block identity). *For every $`N`$ and $`h`$,
``` math
T_{N+h}=2^{h}T_N-B_{h,N},
 \qquad\text{hence}\qquad
 \sigma_h(N)=(2^{h}-1)\,T_N-B_{h,N} .
```*

</div>

Lean: [real block identity](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L76).

<div class="proof">

*Proof.* The case $`h=0`$ follows from $`B_{0,N}=0`$. If the first identity holds at $`h`$, then
``` math
T_{N+h+1}=2(2^hT_N-B_{h,N})-g_{N+h+1}
          =2^{h+1}T_N-B_{h+1,N}.
```
Subtracting $`T_N`$ gives the second identity. ◻

</div>

Subtracting the tail recurrences at $`N+h`$ and $`N`$ gives
``` math
\begin{equation}
\label{long251:eq:shift-step}
 \sigma_h(N+1)=2\sigma_h(N)-\bigl(g_{N+h+1}-g_{N+1}\bigr),
\end{equation}
```
which is the [recurrence for the tail differences](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L563). Since $`B_{h,N}`$ is an integer, Theorem <a href="#long251:res:block" data-reference-type="ref" data-reference="long251:res:block">8</a> also gives the [integrality criterion](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L802): $`\sigma_h(N)`$ is integral if and only if $`(2^h-1)T_N`$ is integral. For fixed $`h`$ in this general recurrence, $`T_N`$ therefore determines whether the shift is integral, regardless of the later integer coefficients. For a complete tail, however, changing those coefficients also changes $`T_N`$; the observation does not permit arbitrary changes to prime gaps.

For rational $`T_N=u/v`$ in lowest terms, the recurrence gives $`T_{N+1}=(2u-g_{N+1}v)/v`$. The numerator has greatest common divisor $`\gcd(2,v)`$ with $`v`$, because $`\gcd(u,v)=1`$. Thus
``` math
\begin{equation}
 \operatorname{den}(T_{N+1})
 =\frac{\operatorname{den}(T_N)}{\gcd(2,\operatorname{den}(T_N))},
 \qquad
 \sigma_h(N)\in\mathbb{Z}
 \iff
 \operatorname{den}(T_N)\mid 2^h-1 .
\label{long251:eq:den-law}\ltx@label{eq:shift-denominator}\ltx@label{res:shiftiff}
\end{equation}
```
Each even denominator loses exactly one factor of $`2`$ and an odd denominator is unchanged, so after finitely many steps the denominator is an odd integer $`d`$; Euler’s congruence then gives $`d\mid2^{\varphi(d)}-1`$, and the multiplicative order of $`2`$ modulo $`d`$ is the least positive such exponent, with the convention that this order is $`1`$ when $`d=1`$. The hypothesis that $`d`$ is odd cannot be dropped: if $`T_N=1/2`$ then $`2^{h}-1`$ is odd for every $`h\ge1`$, so no shift at $`N`$ is integral. The resulting periodicity is modulo $`\mathbb{Z}`$: the fractional parts eventually repeat, not necessarily the full tail values or the integer coefficients.

<div id="long251:res:escape-irrational" class="theorem">

**Theorem 9** (exact rationality classification). *Let $`T:\mathbb{N}\to\mathbb{R}`$ satisfy $`T_{N+1}=2T_N-g_{N+1}`$ with integer coefficients $`g`$. The following are equivalent:*

1.  *$`T_0`$ is rational;*

2.  *$`\sigma_h(N)`$ is an integer for some $`h\ge1`$ and some $`N`$;*

3.  *for some fixed $`h\ge1`$, $`\sigma_h(N)`$ is an integer at every sufficiently large $`N`$.*

*Consequently $`T_0`$ is irrational if and only if every positive-length shift is nonintegral at every index, equivalently if and only if for every $`h\ge1`$ and every cutoff some later $`N`$ has $`\sigma_h(N)\notin\mathbb{Z}`$.*

</div>

Lean: [rationality classification](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L94).

<div class="proof">

*Proof.* For <span class="upright">(i)</span>$`\Rightarrow`$<span class="upright">(iii)</span>, the block identity makes every $`T_N`$ rational. By <a href="#long251:eq:den-law" data-reference-type="eqref" data-reference="long251:eq:den-law">[long251:eq:den-law]</a>, its denominator is a fixed odd integer $`d`$ for all sufficiently large $`N`$. Choose $`h=\varphi(d)`$; Euler’s congruence and the same formula show that every subsequent $`\sigma_h(N)`$ is integral. The implication <span class="upright">(iii)</span>$`\Rightarrow`$<span class="upright">(ii)</span> is immediate. For <span class="upright">(ii)</span>$`\Rightarrow`$<span class="upright">(i)</span>, the block identity gives $`\sigma_h(N)=(2^h-1)T_N-B_{h,N}`$ with $`B_{h,N}`$ and $`\sigma_h(N)`$ integers and $`2^h-1\ne0`$, so $`T_N`$ is rational, and $`T_N=2^NT_0-B_{N,0}`$ then makes $`T_0`$ rational. Negating the three conditions gives the two irrationality formulations. ◻

</div>

<div id="long251:res:true-tail" class="lemma">

**Lemma 10** (the boundary condition identifying a true tail). *Let $`a_1,a_2,\ldots`$ be real numbers with $`\sum_{j\ge1}|a_j|2^{-j}<\infty`$, and let $`U_{N+1}=2U_N-a_{N+1}`$. Then
``` math
U_N=\sum_{j\ge1}a_{N+j}2^{-j}\quad\hbox{for every }N
 \quad\Longleftrightarrow\quad 2^{-N}U_N\longrightarrow0.
```*

</div>

Lean: [real dyadic orbit eq true tail iff](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/TrueTail.lean#L57).

<div class="proof">

*Proof.* Iteration gives $`2^{-N}U_N=U_0-\sum_{j=1}^{N}a_j2^{-j}`$. The limit is zero exactly when $`U_0`$ equals the full series; subtracting its first $`N`$ terms then gives the claimed tail formula. Without the boundary condition, one may add $`C2^N`$ to every $`U_N`$ without changing the recurrence. ◻

</div>

For instance, zero coefficients and initial value $`U_0=1/12`$ give $`\tfrac1{12},\tfrac16,\tfrac13,\tfrac23,\tfrac43,\ldots`$, with $`U_{N+h}-U_N=(2^h-1)2^N/12`$. Shifts of length $`2`$ become integral at index $`2`$; shifts of length $`1`$ never do. These are not complete tails of the zero sequence, since $`2^{-N}U_N=1/12`$ does not tend to zero. The denominator calculation remains valid, but the boundary condition excludes this extra homogeneous term.

<a id="the-actual-prime-gap-tails."></a>

#### The actual prime-gap tails.

Put
``` math
T_N=\sum_{j\ge1}\frac{g_{N+j}}{2^{\,j}},
```
which converges by Theorem <a href="#long251:res:infinite" data-reference-type="ref" data-reference="long251:res:infinite">5</a>. Reindexing identifies this sum with the rescaled complete tail of $`S`$, as in the [shifted-gap series identity](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L31). Splitting off the first term gives $`T_{N+1}=2T_N-g_{N+1}`$ without a rationality hypothesis, as formalised in the [real tail recurrence](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L48). Since $`T_0=2S-1=2.349287932\ldots`$, the numbers $`\Pi`$, $`S`$ and $`T_0`$ have the same rationality status, and Theorem <a href="#long251:res:escape-irrational" data-reference-type="ref" data-reference="long251:res:escape-irrational">9</a> specialises to the actual series: irrationality of $`\Pi`$ is equivalent to nonintegrality arbitrarily far out for each positive shift of $`T`$. The formal statement is the [irrationality equivalence for the actual prime tails](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L73). Thus the passage from the series to its complete tails is proved. What remains is to establish the required nonintegrality for these prime-gap tails.

<a id="long251:sec:freepair"></a>

## Pairs of congruent indices and least-common-multiple shifts

The previous criterion fixes the distance between the two indices. An equivalent version allows that distance to vary, but requires the indices to be congruent modulo each prescribed positive integer. It is not a weaker hypothesis on the tail: the next theorem proves that it is equivalent to irrationality.

<div id="long251:res:freepair" class="theorem">

**Theorem 11** (pairs of congruent indices). *$`S`$ is irrational if and only if for every $`t\ge1`$ and every $`N_0`$ there are $`N,M\ge N_0`$ with $`M\equiv N\pmod t`$ and $`T_M-T_N\notin\mathbb{Z}`$.*

</div>

Lean: [actual free pair criterion](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L189).

<div class="proof">

*Proof.* If $`S`$ is irrational, take $`M=N+t`$ for the $`N`$ supplied by Theorem <a href="#long251:res:escape-irrational" data-reference-type="ref" data-reference="long251:res:escape-irrational">9</a> at shift length $`t`$. Conversely, suppose $`S`$ is rational. By <a href="#long251:eq:den-law" data-reference-type="eqref" data-reference="long251:eq:den-law">[long251:eq:den-law]</a> the orbit reaches an index $`N_0`$ beyond which the reduced denominator is a fixed odd $`d`$; let $`t`$ be the multiplicative order of $`2`$ modulo $`d`$, taking $`t=1`$ when $`d=1`$. For $`N,M\ge N_0`$ with $`M\equiv N`$ modulo $`t`$, the difference $`T_M-T_N`$ is then an integer, contradicting the stated property at this $`t`$ and this cutoff. ◻

</div>

Modulo one, the tail recurrence is multiplication by two. Once the reduced denominator is the fixed odd integer $`d`$, a difference $`T_M-T_N`$ is integral precisely when $`M-N`$ is divisible by the order of $`2`$ modulo $`d`$. Theorem <a href="#long251:res:freepair" data-reference-type="ref" data-reference="long251:res:freepair">11</a> therefore allows the distance between the indices to vary, but requires a nonintegral pair beyond every cutoff for every prescribed modulus.

Equal tail values do not help this criterion, since their difference is zero. Section <a href="#long251:sec:xr-compression" data-reference-type="ref" data-reference="long251:sec:xr-compression">14.4</a> shows that rationality and the prime number theorem would in fact force many equal tail values. It also explains why, beyond the rational denominator cutoff, an interval condition excluding integers already contradicts rationality at indices congruent modulo the corresponding multiplicative order. These are ordinary deductions, not additional formalised statements.

A second reformulation tests one prescribed sequence of pairs of indices. Let $`L_0=1`$ and $`L_j=\operatorname{lcm}(1,\ldots,j)`$.

<div id="long251:res:lcmdiagonal" class="theorem">

**Theorem 12** ([criterion using least common multiples](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/OrderLatticeDiagonal.lean#L153)). *Let $`g:\mathbb{N}\to\mathbb{Z}`$ and $`T:\mathbb{N}\to\mathbb{R}`$ satisfy $`T_{N+1}=2T_N-g_{N+1}`$. Then $`T_0`$ is irrational if and only if $`T_{2L_j}-T_{L_j}\notin\mathbb{Z}`$ for every $`j\ge0`$.*

</div>

Lean: [irrational initial iff all lcm diagonal nonintegral](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/OrderLatticeDiagonal.lean#L153).

<div class="proof">

*Proof.* Theorem <a href="#long251:res:escape-irrational" data-reference-type="ref" data-reference="long251:res:escape-irrational">9</a> gives the forward implication. Conversely, if $`T_0`$ is rational then some positive shift length $`h`$ is integral at every basepoint beyond an index $`N_0`$. Choose $`j`$ so large that $`N_0\le L_j`$ and $`h\mid L_j`$. The telescoping identity $`\sigma_{a+b}(N)=\sigma_a(N)+\sigma_b(N+a)`$ shows by induction that every positive multiple of $`h`$ is integral at every such basepoint, so $`T_{2L_j}-T_{L_j}`$ is an integer. ◻

</div>

One could use factorials instead of least common multiples, since they have the same eventual divisibility property. The least common multiples are no larger at each index. Theorems <a href="#long251:res:freepair" data-reference-type="ref" data-reference="long251:res:freepair">11</a> and <a href="#long251:res:lcmdiagonal" data-reference-type="ref" data-reference="long251:res:lcmdiagonal">12</a> change which tail differences one must test, but remain exact equivalences for integer-coefficient recurrences. Neither proves the needed nonintegrality for the actual prime gaps.

<a id="long251:sec:local-certificate"></a>

# A local certificate, and one actual pair

An integer in $`(-1,1)`$ must be zero. Thus, if two consecutive tail differences lie in that interval and are both integral, both vanish. The recurrence then forces $`g_{N+h+1}=g_{N+1}`$. An unequal pair of gaps therefore gives a finite way to rule out simultaneous integrality, provided that both complete tail differences have been bounded.

<div id="long251:res:smallpair" class="theorem">

**Theorem 13** (adjacent small-shift obstruction). *Let $`T`$ satisfy the dyadic tail recurrence with integer coefficients $`g`$, and fix $`h`$ and $`N`$. If
``` math
-1<\sigma_h(N)<1,\qquad -1<\sigma_h(N+1)<1,
 \qquad g_{N+h+1}\ne g_{N+1},
```
then $`\sigma_h(N)`$ and $`\sigma_h(N+1)`$ cannot both be integers. Consequently, if such a pair occurs beyond every threshold, the $`h`$-shift is not eventually integral.*

</div>

Lean: [rational small pair bundle](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L267).

<div class="proof">

*Proof.* An integer strictly between $`-1`$ and $`1`$ is zero. If both shifts were integers, both would vanish, and <a href="#long251:eq:shift-step" data-reference-type="eqref" data-reference="long251:eq:shift-step">[long251:eq:shift-step]</a> would give $`g_{N+h+1}=g_{N+1}`$. The final assertion chooses one such adjacent pair after the alleged onset of integrality. ◻

</div>

<div id="long251:res:smallpair-real" class="corollary">

**Corollary 14** (real form and the sufficient condition). *The same statement holds for a real orbit, with the same proof. If for every $`h\ge1`$ and every cutoff some later $`N`$ satisfies the three displayed conditions for the actual prime gaps, then $`\Pi`$ is irrational.*

</div>

Lean: [real small pair prime endpoint](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L298).

The unequal-gap condition alone is available: at $`h=1`$, $`N=2`$ it reads $`g_4=2\ne4=g_3`$, and Proposition <a href="#long251:res:gap-nonperiodic" data-reference-type="ref" data-reference="long251:res:gap-nonperiodic">15</a> gives such inequalities at arbitrarily large indices for each fixed $`h`$. The missing assertion is that both small-tail inequalities and the unequal-gap condition hold at the same arbitrarily late indices. Separate infinite sets of witnesses for the three requirements need not intersect.

<div id="long251:res:gap-nonperiodic" class="proposition">

**Proposition 15** (prime gaps do not become periodic). *<span id="res:gap-nonperiodic" label="res:gap-nonperiodic"></span> For every positive $`h`$, the actual consecutive-prime-gap sequence is not eventually periodic with period $`h`$.*

</div>

Lean: [prime gaps not eventually periodic](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L175).

<div class="proof">

*Proof.* For $`m\ge2`$ the integers $`(m+1)!+2,\ldots,(m+1)!+m+1`$ are composite, so the gaps are unbounded. An eventually periodic sequence of natural numbers has finite range after its preperiod and a bounded initial segment, hence is bounded. ◻

</div>

Lean checks the factorial argument as [unboundedness of the actual gaps](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L57) and the conclusion as [non-eventual periodicity](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1023). Far stronger lower bounds for large gaps are known \[fgkmt2018, Theorem 1\]; unboundedness is all that is needed.

With even gap differences, the three conditions in Theorem <a href="#long251:res:smallpair" data-reference-type="ref" data-reference="long251:res:smallpair">13</a> reduce to two possible signed intervals, each accompanied by a prescribed gap difference. For fixed $`h`$ write $`D_N=\sigma_h(N)`$ and $`\delta_N=g_{N+h+1}-g_{N+1}`$, so that $`D_{N+1}=2D_N-\delta_N`$.

<div id="long251:res:signedwindow" class="theorem">

**Theorem 16** ([an equivalent signed interval test](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/AffineShiftEscape.lean#L113)). *Assume $`\delta_N`$ is even. The conjunction $`-1<D_N<1`$, $`-1<D_{N+1}<1`$, $`\delta_N\ne0`$ is equivalent to
``` math
\bigl(\delta_N=2\ \hbox{ and }\tfrac12<D_N<1\bigr)
 \quad\hbox{or}\quad
 \bigl(\delta_N=-2\ \hbox{ and }-1<D_N<-\tfrac12\bigr).
```*

</div>

Lean: [real signed two window](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L135).

<div class="proof">

*Proof.* Since $`\delta_N=2D_N-D_{N+1}`$, the bounds $`|D_N|<1`$ and $`|D_{N+1}|<1`$ give $`-3<\delta_N<3`$. A nonzero even integer in this interval is $`2`$ or $`-2`$. If $`\delta_N=2`$, the inequality $`-1<2D_N-2<1`$, together with $`|D_N|<1`$, is equivalent to $`1/2<D_N<1`$. Negating both differences gives the case $`\delta_N=-2`$. Each substitution is reversible. ◻

</div>

For the actual gaps, both indices $`N+1`$ and $`N+h+1`$ are positive, so $`\delta_N`$ is even for every $`N\ge0`$. Theorem <a href="#long251:res:signedwindow" data-reference-type="ref" data-reference="long251:res:signedwindow">16</a> therefore applies to the actual tails. Its proof uses order, the recurrence and the evenness of $`\delta_N`$; it does not require rational tail values. This is the real version used in Theorem <a href="#long251:res:sparse" data-reference-type="ref" data-reference="long251:res:sparse">28</a>.

<a id="an-explicit-remainder-and-a-certified-actual-pair"></a>

## An explicit remainder and a certified actual pair

Both window conditions involve complete infinite tails. Bounding the omitted terms turns each test into a finite integer comparison.

<div id="long251:res:explicit-remainder" class="proposition">

**Proposition 17** (explicit remainder). *For integers $`h,N\ge0`$ and $`L\ge1`$ put
``` math
F_{h,N,L}=\sum_{j=1}^{L}\frac{g_{N+h+j}-g_{N+j}}{2^{\,j}},\qquad
 P(x)=x^4+8x^3+36x^2+104x+150,
```
``` math
E_{h,N,L}=\frac{1250}{2^{L}}\bigl(P(N+h+L+2)+P(N+L+2)\bigr).
```
Then $`\bigl|\sigma_h(N)-F_{h,N,L}\bigr|\le E_{h,N,L}`$. In particular $`|F_{h,N,L}|+E_{h,N,L}<1`$ certifies $`|\sigma_h(N)|<1`$, and $`\operatorname{dist}(F_{h,N,L},\mathbb{Z})>E_{h,N,L}`$ certifies $`\sigma_h(N)\notin\mathbb{Z}`$.*

</div>

Lean: [explicit remainder certificate](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperTailBoundsR7.lean#L211).

<div class="proof">

*Proof.* The checked bound $`p_n\le1250(n+1)^4`$ gives $`0\le g_m\le p_{m+1}\le1250(m+2)^4`$, so the omitted absolute tail is at most
``` math
1250\sum_{j>L}\frac{(N+h+j+2)^4+(N+j+2)^4}{2^{\,j}} .
```
The polynomial identity $`2P(x)=(x+1)^4+P(x+1)`$ telescopes to $`\sum_{k=1}^{J}(m+k)^42^{-k}=P(m)-P(m+J)2^{-J}`$, whose last term tends to zero. Apply it with $`m=N+h+L+2`$ and $`m=N+L+2`$ after writing $`j=L+k`$. The two tests follow from the triangle inequality and the definition of distance to $`\mathbb{Z}`$. ◻

</div>

<div id="long251:res:finite-smallpair" class="proposition">

**Proposition 18** (a certified adjacent pair). *For the actual prime gaps, $`h=1`$ and $`N=2`$ satisfy the three hypotheses of Theorem <a href="#long251:res:smallpair" data-reference-type="ref" data-reference="long251:res:smallpair">13</a>: both $`\sigma_1(2)`$ and $`\sigma_1(3)`$ lie in $`(-1,1)`$ and are nonintegral, and $`g_4=2\ne4=g_3`$.*

</div>

Lean: [finite small pair](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperFiniteCertificatesR7.lean#L111).

<div class="proof">

*Proof.* Take $`L=40`$ and $`Q=2^{40}=1099511627776`$. Exact integer arithmetic over the first $`46`$ primes gives
``` math
\begin{array}{c|r|r}
 N&Q\,F_{1,N,40}&Q\,E_{1,N,40}\\\hline
 2&-662838684750&11764181250\\
 3& 873345886050&12805761250
\end{array}
```
In each row $`|QF|+QE<Q`$, which puts the whole certified interval inside $`(-1,1)`$, and $`QE`$ is smaller than the distance from $`QF`$ to the nearest multiple of $`Q`$, which excludes every integer. The margins are $`424908761776`$ and $`213359980476`$ respectively. These are strict integer comparisons rather than inferences from rounded numerical tails. Appendix <a href="#long251:app:certificates" data-reference-type="ref" data-reference="long251:app:certificates">12</a> replays them. ◻

</div>

This computation proves the local condition at one pair of indices. The quantifiers over every $`h`$ and every cutoff remain.

<div id="long251:res:one-tail-certificate" class="proposition">

**Proposition 19** (a one-tail signed certificate). *Let $`D_{N+1}=2D_N-\delta_N`$ with real $`D_N`$, and suppose $`\delta_N=2s`$ for $`s\in\{-1,1\}`$. If integers $`A,B,Q`$ satisfy $`Q>0`$, $`B\ge0`$, $`|QD_N-A|\le B`$, and
``` math
2sA-Q>2B,\qquad Q-sA>B,
```
then $`1/2<sD_N<1`$, $`|D_{N+1}|<1`$, and both $`D_N,D_{N+1}`$ are nonintegral. In particular the adjacent small-shift obstruction is certified from just one tail enclosure.*

</div>

Lean: [one tail signed certificate](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/FiniteSeparation.lean#L6).

<div class="proof">

*Proof.* The inequalities place the complete interval $`[(sA-B)/Q,(sA+B)/Q]`$ inside $`(1/2,1)`$. Thus $`sD_{N+1}=2sD_N-2\in(-1,0)`$, proving every assertion. ◻

</div>

For $`h=1,N=2`$, the exact data already used above give $`Q=2^{40}`$, $`A=-662838684750`$, $`B=11764181250`$ and $`s=-1`$. The two positive integer margins are respectively $`202637379224`$ and $`424908761776`$. The second enclosure in Proposition <a href="#long251:res:finite-smallpair" data-reference-type="ref" data-reference="long251:res:finite-smallpair">18</a> remains a useful independent cross-check, not a logical necessity.

<a id="long251:sec:denominator-floor"></a>

# Two lower bounds on a possible rational denominator

An exact rational enclosure of $`\Pi`$ can exclude all rational values whose denominator lies below an explicit bound. The two results here use the same polynomial estimate for the omitted prime terms, but have different supplied verification records. Both bounds are finite; neither proves irrationality.

<div id="long251:res:denominatorfloor" class="theorem">

**Theorem 20** (a denominator bound checked by exact integer comparisons). *Let $`a\in\mathbb{Z}`$ and let $`b`$ be a positive integer. If $`\Pi=a/b`$ then $`b\ge2^{589}>10^{177}`$, and the same floor holds for every rational equal to $`S`$.*

</div>

Lean: [denominator floor both](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperFiniteCertificatesR7.lean#L142), [denominator floor decimal](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperFiniteCertificatesR7.lean#L137).

<div class="proof">

*Proof.* Put $`c=1229`$, the number of primes below $`10^4`$, and $`A=\sum_{i=0}^{c-1}p_i2^{\,c-i-1}`$, so that $`A/2^{c}`$ is the $`c`$th partial sum of $`\Pi`$. All terms are positive, so $`A/2^{c}\le\Pi`$. For the upper bound, $`p_{c+j}\le1250(c+j+1)^4`$. Since $`c\ge9`$, each successive ratio of $`(c+1+j)^4`$ is at most $`(11/10)^4<3/2`$. Hence $`(c+1+j)^4\le(c+1)^4(3/2)^j`$ for all $`j\ge0`$. The omitted dyadic terms are therefore bounded by a geometric series with ratio $`3/4`$, whose sum gives
``` math
\frac{A}{2^{c}}\;\le\;\Pi\;\le\;\frac{2A+5000(c+1)^4}{2^{\,c+1}} .
```
The four positive integers $`u,v,u',v'`$ printed in Appendix <a href="#long251:app:certificates" data-reference-type="ref" data-reference="long251:app:certificates">12</a> satisfy
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
The only properties needed of the bracketing fractions are their order, positive denominators and determinant one. Their decimal expansions and the way they were found play no part in this denominator bound. Since $`589\log_{10}2>177`$, the floor exceeds $`10^{177}`$. If $`S=a/b`$, apply the same argument to $`\Pi=(a+2b)/b`$. ◻

</div>

The Lean kernel decides the four inequalities on the same literals by `decide +kernel` with no `native_decide`, over a trial-division sieve it re-runs on $`[2,10^4)`$: the [certificate](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/KernelDenominatorFloor.lean#L310), the [floor for the prime series](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/KernelDenominatorFloor.lean#L316), and the [floor for the gap series](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/KernelDenominatorFloor.lean#L324). Its analytic input is the same enclosure, over the polynomial bound at [line 360](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L360). The four Farey literals have $`177`$ and $`178`$ digits.

<div id="long251:res:cfexclusion" class="theorem">

**Theorem 21** (certified continued-fraction exclusion). *Every rational equal to $`\Pi`$, and hence every rational equal to $`S`$, has reduced denominator $`q\ge2^{39997}`$, and therefore $`q>10^{12040}`$.*

</div>

Not formalised: the deduction from the four integer comparisons is checked in general form, and the certificate they are applied to is too large for the Lean kernel to evaluate, so the exclusion rests on the separate exact-arithmetic verifier described in the proof. See the [coverage section](#long251:sec:coverage).

<div class="proof">

*Proof.* The accompanying integer-arithmetic verifier constructs an $`80000`$-bit enclosure with $`23369`$ common partial quotients and checks the following certificate. It uses neither floating-point arithmetic nor a Lean build.

Let $`c=80128`$ and $`A=\sum_{i=0}^{c-1}p_i2^{c-i-1}`$, with the primes obtained by a sieve below $`1200000`$. The polynomial bound and the quartic identity of Proposition <a href="#long251:res:explicit-remainder" data-reference-type="ref" data-reference="long251:res:explicit-remainder">17</a> give
``` math
\frac{A}{2^c}\le\Pi\le\frac{A+1250P(c)}{2^c}.
```
Round the lower endpoint down and the upper endpoint up to multiples of $`2^{-80000}`$. The resulting integers $`L,U`$ satisfy $`U-L=1`$ and $`\Pi\in[L2^{-80000},U2^{-80000}]`$. This is the width reported as $`1`$ in the scaled receipt. The verifier computes the common continued-fraction prefix of these two rational endpoints by integer division and inversion.

Its last two convergents, ordered as $`u/v<u'/v'`$, satisfy
``` math
u'v-uv'=1,\qquad
 u\,2^{80000}<Lv,\qquad Uv'<u'\,2^{80000},\qquad
 v+v'\ge2^{39998}.
```
Thus the entire enclosure lies strictly between two Farey neighbours. The same determinant calculation as in Theorem <a href="#long251:res:denominatorfloor" data-reference-type="ref" data-reference="long251:res:denominatorfloor">20</a> gives $`q\ge v+v'`$ for every rational value of $`\Pi`$. It proves the stated bound and, in fact, the slightly stronger dyadic bound $`q\ge2^{39998}`$; the strict decimal bound remains $`10^{12040}`$. The continued fractions used in the computation are those of the rational enclosure endpoints, not an assumed infinite continued fraction for $`\Pi`$. Once the neighbours are found, only the four displayed integer comparisons are needed. ◻

</div>

The original receipt uses the best-approximation property of convergents \[khinchin1964, §6, Theorems 16 and 17\]; Short gives an accessible statement and proof \[short2009, Theorem 1.1\]. The receipt is [the continued-fraction receipt](https://github.com/wcook04/plectis-erdos/blob/dd6cc708f650f061de06594eba6ba43878f4de31/research/experiments/erdos251/receipts/certified-cf.json), which records the generating program and its digest, the power-of-two exponent $`39997`$, the bit length $`39998`$, the strict decimal power $`12040`$, the decimal digit count $`12041`$, the largest partial quotient $`973919`$ at index $`16442`$, and an arithmetic self-check of the same routine against the known expansions of $`e`$ and $`\pi`$. Those bit and digit counts describe the original routine’s last convergent, not an arbitrary rational in the enclosure. Bit length $`39998`$ implies a denominator at least $`2^{39997}`$, and $`12041`$ decimal digits imply only a non-strict lower bound $`10^{12040}`$. The bound for $`q`$ instead uses the checked sum $`v+v'\ge2^{39998}`$. The strict decimal inequality follows from the separate integer comparison $`2^{39997}>10^{12040}`$.

A rational number may have a denominator beyond either bound. Extending the computation can exclude a larger finite range, but a longer prefix need not improve the bound at every step and cannot by itself exclude all denominators. These statements are denominator exclusions, not estimates for an irrationality exponent.

<a id="long251:sec:obstructions"></a>

# What cannot supply the missing input

The counterexamples in this section test which information about the gaps could force irrationality. They preserve selected growth, residue and nonconcentration properties while changing the dyadic value. The sparsity result has a different role: it rules out a positive-proportion lower bound for the two-window event, while leaving sparse-witness arguments available.

<a id="bounded-residue-preserving-perturbations"></a>

## Bounded residue-preserving perturbations

Here a single positive modulus $`M`$ is fixed in advance. Adding either zero or $`M`$ to each sufficiently late coefficient preserves that modulus and gives a binary choice at every index. Unlike the sparse theorem, this construction need not preserve all moduli eventually and need not have a support of density zero.

<div id="long251:res:boundedperturbation" class="theorem">

**Theorem 22** (bounded-perturbation obstruction). *Let $`a_n`$ be natural numbers with $`\sum_{n\ge0}a_n2^{-(n+1)}`$ convergent. For every integer $`M\ge1`$ and every cutoff $`K`$ there are digits $`\varepsilon_n\in\{0,1\}`$, zero for $`n<K`$, such that $`\sum_{n\ge0}(a_n+M\varepsilon_n)2^{-(n+1)}`$ is rational.*

</div>

Lean: [rational bounded perturbation](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L200).

<div class="proof">

*Proof.* Write $`A=\sum_{n\ge0}a_n2^{-(n+1)}`$ and choose a rational $`r\in\bigl(A,A+M2^{-K}\bigr)`$. A binary expansion of $`(r-A)/M`$ has the form $`\sum_{n\ge K}\varepsilon_n2^{-(n+1)}`$ with $`\varepsilon_n\in\{0,1\}`$; set $`\varepsilon_n=0`$ for $`n<K`$. The perturbed series converges and equals $`r`$. ◻

</div>

The [construction](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/BoundedPerturbationCountermodel.lean#L193) is covered by the supplied formal verification record. It follows that a property shared by every allowed perturbation cannot by itself force irrationality, since one such perturbation has a rational sum. This is an ordinary consequence of the construction, not a separate formal theorem. The construction is also checked at the actual consecutive prime gaps for every $`M\ge1`$ and every $`K`$, the [rational perturbed prime-gap series](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/BoundedPerturbationCountermodel.lean#L208), with the perturbed gap lying in $`[g_n,g_n+M]`$ and congruent to $`g_n`$ modulo $`M`$, the [gap bounds](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/BoundedPerturbationCountermodel.lean#L234). For each fixed $`k\ge1`$, the sum of $`k`$ consecutive gaps increases by at most $`kM`$. Thus infinitely many bounded gaps and bounded clusters of each fixed size survive, but their original numerical bounds need not. Nonnegative corrections also preserve lower bounds for large gaps. Taking $`M=2q`$ preserves parity and the cumulative positions modulo a prescribed $`q`$, hence any limiting residue frequencies of those positions. These conclusions concern the size and residue information in the results discussed in Section <a href="#long251:sec:open" data-reference-type="ref" data-reference="long251:sec:open">10</a>; they establish neither primality of the new positions nor preservation of every quantitative assertion of those theorems.

<a id="algebraic-nonconcentration-survives-the-rationalising-perturbation"></a>

## Algebraic nonconcentration survives the rationalising perturbation

The bounded perturbation also preserves fixed-block polynomial nonconcentration. The relevant input is Schlage-Puchta’s Lemma 4: for every polynomial $`F\in\mathbb{Z}[x_0,\ldots,x_k]`$ which does not vanish identically, $`F(g_n,\ldots,g_{n+k})\ne0`$ for almost all $`n`$ \[schlagepuchta2011, Lemma 4, pp. 5–6\]. Say that an integer sequence $`a`$ has *fixed-block nonconcentration* when it satisfies that conclusion for every $`k\ge0`$ and every nonzero $`F\in\mathbb{Z}[x_0,\ldots,x_k]`$. The property transfers across bounded perturbations with no independence or randomness assumption.

This nonconcentration condition excludes every bounded integer sequence: if its values lie in a finite set $`E`$, the nonzero polynomial $`\prod_{c\in E}(x_0-c)`$ vanishes at every index. It also excludes a sequence satisfying a fixed nonzero polynomial relation on every short block, such as $`a_n=n`$, for which $`x_1-x_0-1`$ vanishes. The density-zero exceptional set depends on the fixed polynomial. There cannot be one such set for all polynomials: $`x_0-a_n`$ vanishes on the block beginning at $`n`$, so a common exceptional set would contain every index. No uniform estimate for growing families of polynomials or block lengths is asserted.

In the next proposition, $`N,H`$ are nonnegative integers, $`h`$ is an integer, and all counts are over integer indices and integer triples.

<div id="long251:res:shiftedcount" class="proposition">

**Proposition 23** (finite counting for shifted gap differences). *Write $`p_n`$ for the primes indexed from $`p_0=2`$ and $`g_n=p_{n+1}-p_n`$. For $`h\ge2`$ and $`r\in\mathbb{Z}`$, let $`M_{h,r}(N)`$ count $`n<N`$ with $`g_{n+h}-g_n=r`$. Let $`Q_{N,H,r}`$ count triples $`(x,d,s)`$ with $`x<p_N`$, $`0<d<s\le H`$, $`d+r>0`$, and all four integers $`x,x+d,x+s,x+s+d+r`$ prime. Then, for every $`N,H\ge0`$,
``` math
(H+1)M_{h,r}(N)\le
 (h+1)p_{N+h+1}+(H+1)Q_{N,H,r}.
```*

</div>

Lean: [shifted count bound](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/ShiftedGapCountingR9.lean#L152).

<div class="proof">

*Proof.* For a counted index $`n`$, put $`x=p_n`$, $`d=g_n`$ and $`s=p_{n+h}-p_n`$. If the total span $`p_{n+h+1}-p_n`$ is at most $`H`$, then $`0<d<s\le H`$, $`d+r=g_{n+h}>0`$, and the four primes are precisely $`x,x+d,x+s,x+s+d+r`$. The map is injective because $`x=p_n`$ determines $`n`$. For the remaining indices the integer span is at least $`H+1`$. Each gap appears in at most $`h+1`$ of the spans, so their total is at most $`(h+1)\sum_{i<N+h}g_i<(h+1)p_{N+h+1}`$. Multiply the resulting bound on the exceptional count by $`H+1`$ and add the small-span contribution. ◻

</div>

The displayed finite shifted-count bound is unconditional by the ordinary proof above. Its [historical source locator](https://github.com/wcook04/plectis-erdos/blob/d058b9150218ae23d2cfd975580088d6167e9da8/ErdosProblems/Erdos251/ShiftedGapCountingR9.lean#L152) is retained; Appendix <a href="#long251:app:index" data-reference-type="ref" data-reference="long251:app:index">13</a> identifies the relocated proof in the supplied packet and distinguishes its recorded release status from a checked build. To obtain zero density from this particular finite bound, one would need, for every $`\varepsilon>0`$ and all large $`N`$, a choice of $`H`$ making its right side less than $`\varepsilon N(H+1)`$. For $`h=1`$, the same definitions give $`s=d`$, so $`x+d=x+s`$. The strict condition $`d<s`$ in the four-prime count fails; that case requires a three-prime count instead. Zero density itself is already known for every fixed $`h\ge1`$ and $`r\in\mathbb{Z}`$: apply Schlage-Puchta’s lemma above to the nonzero polynomial $`x_h-x_0-r`$. Thus the finite reduction should not be read as leaving that upper bound open. Neither upper bound supplies the late occurrences or weighted-tail separation required for irrationality.

For the perturbation claim, first suppose that $`a`$ has fixed-block nonconcentration and every correction is either $`0`$ or a fixed integer $`M\ge1`$. For a fixed $`r\in\mathbb{Z}`$, an equality $`b_{n+1}-b_n=r`$ then requires $`a_{n+1}-a_n\in\{r-M,r,r+M\}`$. Each of these three equalities holds on a set of density zero. The general argument uses the same finite-union step for translated polynomials.

<div id="long251:res:nonconcentration" class="theorem">

**Theorem 24** (nonconcentration is perturbation-stable). *Let $`a:\mathbb{N}\to\mathbb{Z}`$ have fixed-block nonconcentration, let $`E\subset\mathbb{Z}`$ be finite, and let $`b_n=a_n+e_n`$ with $`e_n\in E`$ for every $`n`$. Then $`b`$ has fixed-block nonconcentration.*

</div>

Lean: [finite perturbation stability](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperNonconcentrationR7.lean#L100).

<div class="proof">

*Proof.* Fix $`k\ge0`$ and a nonzero $`F\in\mathbb{Z}[x_0,\ldots,x_k]`$. For a tuple $`\mathbf e=(e^{(0)},\ldots,e^{(k)})\in E^{k+1}`$ put $`F_{\mathbf e}(x_0,\ldots,x_k)=F(x_0+e^{(0)},\ldots,x_k+e^{(k)})`$. The substitution $`x_i\mapsto x_i+e^{(i)}`$ is a ring automorphism of $`\mathbb{Z}[x_0,\ldots,x_k]`$ with inverse $`x_i\mapsto x_i-e^{(i)}`$, so $`F_{\mathbf e}\ne0`$. If $`F(b_n,\ldots,b_{n+k})=0`$ then $`F_{\mathbf e}(a_n,\ldots,a_{n+k})=0`$ for the tuple $`\mathbf e=(e_n,\ldots,e_{n+k})`$, whence
``` math
\{\,n:F(b_n,\ldots,b_{n+k})=0\,\}
 \;\subseteq\!\!
 \bigcup_{\mathbf e\in E^{k+1}}\!\!
 \{\,n:F_{\mathbf e}(a_n,\ldots,a_{n+k})=0\,\}.
```
Each set on the right has density zero by hypothesis, and there are only finitely many such sets because $`E^{k+1}`$ is finite. Their union therefore has density zero. ◻

</div>

Finiteness of the correction set is essential to this argument; no independence between the corrections and the sequence is needed. Without a restriction on the corrections, the choice $`e_n=-a_n`$ would give $`b_n=0`$, which fails nonconcentration even for the polynomial $`x_0`$.

<div id="long251:res:nonconc-primes" class="corollary">

**Corollary 25** (nonconcentration does not force irrationality). *Fix $`M\ge1`$ and $`K\ge0`$, and let $`b`$ be the perturbed sequence supplied by Theorem <a href="#long251:res:boundedperturbation" data-reference-type="ref" data-reference="long251:res:boundedperturbation">22</a> at the actual prime gaps. Then $`\sum_{n\ge0}b_n2^{-(n+1)}`$ is rational, $`b_n=g_n`$ for $`n<K`$, $`b_n-g_n\in\{0,M\}`$ and $`b_n\equiv g_n\pmod M`$ for every $`n`$, $`b`$ has fixed-block nonconcentration, and the cumulative sequence $`P_n=2+\sum_{i<n}b_i`$ satisfies $`p_n\le P_n\le p_n+Mn`$ and hence $`P_n\sim n\log n`$.*

</div>

Lean: [nonconcentration does not force irrationality](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR21/PerturbedPrimePositions.lean#L126), [perturbed position bounds](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR21/PerturbedPrimePositions.lean#L67), [sum range prime gap0](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR21/PerturbedPrimePositions.lean#L45), [perturbed position eq](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR21/PerturbedPrimePositions.lean#L59), and 1 further declaration. Conditional on the prime number theorem; see the [coverage section](#long251:sec:coverage).

<div class="proof">

*Proof.* Theorem <a href="#long251:res:boundedperturbation" data-reference-type="ref" data-reference="long251:res:boundedperturbation">22</a> gives the rational sum, prefix and congruence assertions. Summing $`0\le b_i-g_i\le M`$ and using $`\sum_{i<n}g_i=p_n-2`$ gives $`p_n\le P_n\le p_n+Mn`$. Now $`p_n\sim n\log n`$ \[mv2007, Chapter 6\] implies $`P_n\sim n\log n`$. The perturbation takes values in the fixed two-element set $`E=\{0,M\}`$, so Theorem <a href="#long251:res:nonconcentration" data-reference-type="ref" data-reference="long251:res:nonconcentration">24</a> applies to the actual gaps, which have fixed-block nonconcentration by Schlage-Puchta’s lemma \[schlagepuchta2011, Lemma 4\]. ◻

</div>

Fixed-block polynomial nonconcentration, taken together with a prescribed finite prefix of actual gaps, a pointwise bound $`b_n\le g_n+M`$, every residue modulo $`M`$, positivity and cumulative growth at the prime-number-theorem scale, is therefore compatible with a rational dyadic value. Taking $`M`$ even also preserves eventual evenness. To preserve a prescribed modulus $`q`$ together with parity, take $`M=2q`$, with the corresponding pointwise bound $`b_n\le g_n+2q`$. The terms $`P_n`$ are not asserted to be prime. The nonconcentration conclusion is for each fixed polynomial in a fixed block; it gives no uniform bound for polynomial families or block lengths growing with the index.

<div id="long251:res:sparse-nonconcentration" class="proposition">

**Proposition 26** (nonconcentration under sparse changes). *Let $`a,b:\mathbb{N}\to\mathbb{Z}`$ agree off a set $`S`$ of ordinary density zero. If $`a`$ has fixed-block nonconcentration, then so does $`b`$. No boundedness assumption on $`a-b`$ is needed.*

</div>

Lean: [sparse nonconcentration](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/SparseNonconcentration.lean#L80).

<div class="proof">

*Proof.* For fixed $`k`$ and a nonzero $`F\in\mathbb{Z}[x_0,\ldots,x_k]`$, a zero of $`F(b_n,\ldots,b_{n+k})`$ either is already a zero at the $`a`$-block or has $`n+i\in S`$ for some $`0\le i\le k`$. Each fixed translate of a density-zero set has density zero, and a finite union retains that property. This proves the assertion for each fixed $`F`$ and $`k`$. It gives no uniform estimate for polynomial families or lengths growing with $`n`$. ◻

</div>

<div class="samepage">

<div id="long251:res:jointcountermodel" class="corollary">

**Corollary 27** (simultaneous prime-gap countermodel). *For every prescribed finite prime-gap prefix and $`0<\varepsilon\le1`$, there is an altered sequence $`b=g+e`$, with $`P_n=2+\sum_{i<n}b_i`$, for which one can simultaneously impose a rational dyadic value, nonnegative integer corrections eventually at most $`(\log(n+3))^\varepsilon`$, all fixed eventual coefficient and cumulative congruences, fixed-block polynomial nonconcentration, and vanishing total variation distance between unnormalised block distributions for lengths $`o(\log\log X)`$. The cumulative positions satisfy
``` math
0\le P_n-p_n=O_\varepsilon\left(
    \frac{n(\log(n+3))^\varepsilon}{\log\log n}\right),
 \qquad P_n\sim n\log n.
```*

</div>

Lean: [long joint prime gap countermodel](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR21/JointPrimeGapCountermodel.lean#L256), [cut prefix bound](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR21/JointPrimeGapCountermodel.lean#L228). Conditional on Schlage-Puchta’s density lemma and the prime number theorem; see the [coverage section](#long251:sec:coverage).

</div>

<div class="proof">

*Proof.* Apply Theorem <a href="#long251:res:sparse-rationalisation" data-reference-type="ref" data-reference="long251:res:sparse-rationalisation">1</a> at a rational target. Proposition <a href="#long251:res:sparse-nonconcentration" data-reference-type="ref" data-reference="long251:res:sparse-nonconcentration">26</a> transfers the nonconcentration supplied by Schlage-Puchta’s Lemma 4 \[schlagepuchta2011\] to the corrected sequence. To obtain the cumulative support bound, split $`[\sqrt n,n)`$ into dyadic intervals, use $`\log\log x\asymp\log\log n`$ there, and bound the first $`\sqrt n`$ indices trivially. Thus $`|S\cap[0,n)|=O(n/\log\log n)`$. The pointwise correction bound gives the displayed estimate, including a fixed constant for the exceptional prefix. Since $`(\log n)^{\varepsilon-1}/\log\log n\to0`$ for $`0<\varepsilon\le1`$, the prime number theorem \[mv2007, Chapter 6\] gives the last conclusion. The position series is rational as well: reversing the order of summation of nonnegative terms gives
``` math
\sum_{n\ge0}\frac{P_n}{2^{n+1}}
 =2+\sum_{i\ge0}b_i\sum_{n>i}2^{-n-1}
 =2+\sum_{i\ge0}\frac{b_i}{2^{i+1}}\in\mathbb{Q}.
```
The finite value on the right also proves convergence on the left. ◻

</div>

These are ordinary deductions from the sparse theorem and the stated external analytic input. In fact, all conclusions also hold for every $`\varepsilon>1`$: apply the corollary with exponent $`1`$. Its correction is smaller than the prescribed allowance, and its cumulative estimate $`O(n\log(n+3)/\log\log n)`$ is stronger than the displayed bound and still gives $`P_n\sim n\log n`$. Thus the stated range $`0<\varepsilon\le1`$ suffices to obtain every positive allowance exponent; no larger correction is required.

The congruences imply that for every fixed integer $`y\ge2`$, all sufficiently late $`P_n`$ have no prime divisor at most $`y`$: use modulus $`y!`$ and $`p_n>y`$ to get $`\gcd(P_n,y!)=1`$. This is stronger than eventual oddness, but it does not establish primality. Excluding divisors up to $`\sqrt{P_n}`$ would require a bound growing with $`n`$, whereas the congruence cutoff depends on the fixed $`y`$. Even primality of every $`P_n`$ would not identify the sequence with the consecutive primes, since a prime-valued sequence may skip primes.

The two preservation arguments are different. The bounded construction uses a finite set of translated polynomials to preserve nonconcentration; it need not preserve empirical block frequencies. The sparse construction instead compares blocks at the same indices, most of which are unchanged. Its total variation bound is absolute, so it need not preserve relative frequencies of rare events. Moreover, its vanishing-error range is $`m=o(\log\log X)`$, not $`m`$ comparable to $`\log\log X`$. Neither comparison establishes preservation of the quantitative prime-pattern hypotheses of the conditional irrationality and normality results discussed in Section <a href="#long251:sec:context" data-reference-type="ref" data-reference="long251:sec:context">3</a>.

<a id="the-two-window-event-has-density-zero"></a>

## The two-window event has density zero

The same nonconcentration lemma shows that the three conditions of the small-pair test can hold only on a set of density zero. This does not prevent that set from containing arbitrarily large indices.

<div id="long251:res:sparse" class="theorem">

**Theorem 28** (sparsity of the two-window event). *Fix $`h\ge1`$. The set of $`N\ge1`$ at which the three hypotheses of Theorem <a href="#long251:res:smallpair" data-reference-type="ref" data-reference="long251:res:smallpair">13</a> hold for the actual prime gaps has density zero. For the same $`h`$, the set of $`N`$ with $`g_{N+h+1}=g_{N+1}`$ also has density zero.*

</div>

Lean: [prime gap two window sparse](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR21/TwoWindowSparsity.lean#L38), [prime gap equal shift zero density](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR21/TwoWindowSparsity.lean#L50), [prime gap tail recurrence](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR21/TwoWindowSparsity.lean#L30). Conditional on Schlage-Puchta’s density lemma; see the [coverage section](#long251:sec:coverage).

<div class="proof">

*Proof.* For $`N\ge1`$ every gap involved is even, so $`\delta_N=g_{N+h+1}-g_{N+1}`$ is even. If $`|\sigma_h(N)|<1`$, $`|\sigma_h(N+1)|<1`$ and $`\delta_N\ne0`$, then $`\delta_N=2\sigma_h(N)-\sigma_h(N+1)`$ lies in $`(-3,3)`$, so $`\delta_N=\pm2`$. Apply Schlage-Puchta’s lemma \[schlagepuchta2011, Lemma 4\] at index $`n=N+1`$ with $`k=h`$ to the two polynomials $`x_h-x_0-2`$ and $`x_h-x_0+2`$, neither of which vanishes identically: each of $`\{N:\delta_N=2\}`$ and $`\{N:\delta_N=-2\}`$ has density zero, and the event is contained in their union. The second assertion is the same lemma applied to $`x_h-x_0`$. ◻

</div>

Unequal gaps occur at almost every index, a stronger conclusion than Proposition <a href="#long251:res:gap-nonperiodic" data-reference-type="ref" data-reference="long251:res:gap-nonperiodic">15</a>. But combining unequal gaps with the two small tail differences forces their difference to be exactly $`2`$ or $`-2`$, which occurs only on a density-zero set. Thus a proof of Problem <a href="#long251:prob:smallpair" data-reference-type="ref" data-reference="long251:prob:smallpair">33</a> must find arbitrarily large successful indices in that sparse set. A positive-density lower bound for the same event is impossible. An averaging argument that detects a sparse set is not ruled out.

The proof of Schlage-Puchta’s lemma gives a quantitative upper bound as well. For fixed $`h`$, it bounds the number of eligible indices in $`[X,2X)`$ by $`O_h(X/\log\log X)`$. To see the two contributions, discard starts whose block of $`h+1`$ gaps contains a gap exceeding $`\log X\log\log X`$. The sum of these block sums is $`O_h(X\log X)`$ by the prime number theorem, so there are at most $`O_h(X/\log\log X)`$ discarded starts. For the remaining starts, the sieve calculation in the cited proof bounds the zeros of each of $`x_h-x_0-2`$ and $`x_h-x_0+2`$ by
``` math
O_h\!\left(\frac{X(\log\log X)^{2h+2}}{\log X}\right)
 =o_h\!\left(\frac{X}{\log\log X}\right).
```
The shift from $`n=N+1`$ changes only the band endpoints. Thus the same upper bound applies to the two-window event. This is an ordinary consequence of the cited sieve argument, not a new lower bound or an asymptotic formula for the number of successful indices.

The observed proportions in Section <a href="#long251:sec:measurements" data-reference-type="ref" data-reference="long251:sec:measurements">9</a> decrease across the sampled bands. These finite observations establish neither an asymptotic rate nor the required existence beyond every cutoff. Counting by prime size and counting by gap index also give different cutoffs and must not be compared without converting between them.

<a id="recurring-gap-values-differing-by-two-do-not-suffice"></a>

## Recurring gap values differing by two do not suffice

Theorem <a href="#long251:res:signedwindow" data-reference-type="ref" data-reference="long251:res:signedwindow">16</a> requires both a gap difference of $`2`$ or $`-2`$ at a prescribed distance $`h`$ and a tail difference in the corresponding interval. Infinite recurrence of two values differing by $`2`$ in one residue class guarantees neither their occurrence at that distance nor the weighted-tail bound. The next example has the stated recurrence and growth properties, yet its dyadic sum is rational and every tail difference is integral. It is a sequence of integers, not of actual prime gaps.

The mechanism is to choose integer tails first, then recover the coefficients from $`a_n=2U_{n-1}-U_n`$. Constant tails $`U_n=4`$ give constant coefficients $`a_n=4`$. Raising one isolated tail to $`6`$ changes the two affected coefficients from $`4,4`$ to $`2,8`$, with the same combined dyadic contribution. A slowly growing even background will supply cumulative growth $`n\log n`$; factorial indices will impose the recurrence in residue classes while keeping these changes sparse.

<div id="long251:res:polignacfail" class="theorem">

**Theorem 29** (recurring values are not enough). *There is a sequence $`(a_n)_{n\ge1}`$ of positive even integers with the following properties. The values $`2`$ and $`4`$ each occur infinitely often at indices divisible by every fixed $`t\ge1`$. The sequence is unbounded, not eventually periodic, and satisfies $`a_n=O(\log n)`$. The series $`\sum_{n\ge1}a_n2^{-n}`$ equals $`6`$, and every scaled tail $`\sum_{j\ge1}a_{N+j}2^{-j}`$ is an integer, so every tail shift is integral. The increasing odd sequence $`P_n=3+\sum_{j\le n}a_j`$ satisfies $`P_n\sim n\log n`$.*

</div>

Lean: [exists logarithmic recurring values countermodel](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/LogarithmicCarryAsymptoticsR8.lean#L368).

<div class="proof">

*Proof.* Put $`b_n=2\lceil\tfrac12\log(n+64)\rceil`$, so that $`b_n`$ is even, $`b_n\ge6`$, and $`b_n=\log(n+64)+O(1)`$. Since $`\tfrac12\log(n+65)-\tfrac12\log(n+63)<1`$ for every $`n\ge1`$, consecutive increments of $`b`$ lie in $`\{0,2\}`$ and $`b_{n+1}-b_{n-1}\le2`$. Call an index $`n`$ *special* when $`n=k!`$ or $`n=2\,k!`$ for some $`k\ge5`$, and define
``` math
U_n=\begin{cases}
  2b_{n-1}-2,& n=k!,\ k\ge5,\\
  2b_{n-1}-4,& n=2\,k!,\ k\ge5,\\
  b_n,&\text{otherwise},
 \end{cases}
 \qquad a_n=2U_{n-1}-U_n\quad(n\ge1).
```
For $`k\ge5`$ one has $`k!<2\,k!<(k+1)!`$, so all special indices are distinct. They are even and therefore never adjacent. Each $`U_n`$ is an even integer by construction, so each $`a_n`$ is an even integer.

At an ordinary index whose predecessor is also ordinary, $`a_n=2b_{n-1}-b_n=b_{n-1}-(b_n-b_{n-1})\ge6-2=4`$. At a special index the predecessor is ordinary and $`a_n=2b_{n-1}-(2b_{n-1}-r)=r`$, which is $`2`$ at $`n=k!`$ and $`4`$ at $`n=2\,k!`$. Immediately after a special index carrying $`r`$,
``` math
a_{n+1}=2(2b_{n-1}-r)-b_{n+1}\ge4b_{n-1}-2r-(b_{n-1}+2)
 =3b_{n-1}-2r-2\ge8 .
```
Every $`a_n`$ is therefore a positive even integer, and $`U_n=O(\log n)`$ gives $`a_n=O(\log n)`$. For $`k\ge5`$, the index $`n=k!+2`$ and its predecessor are ordinary: both lie strictly between $`k!`$ and $`2\,k!`$, where there are no special indices. Along these indices $`a_n\ge b_{n-1}-2\to\infty`$. Thus $`(a_n)`$ is unbounded and hence not eventually periodic.

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

## A rational series with recurring values in every residue class

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

Enumerate all triples $`(t,r,m)`$ with $`t\ge1`$, $`0\le r<t`$ and $`m\ge0`$, each once. For the $`k`$th triple choose $`c_k\equiv r\pmod t`$, with $`c_0\ge100`$, $`c_{k+1}\ge c_k+3`$ and $`c_k\ge2^{k^2}`$ for $`k\ge1`$. Each arithmetic progression is unbounded, so these lower bounds can be met recursively. Set $`v_k=2`$ for even $`m`$ and $`v_k=4`$ for odd $`m`$. For each $`(t,r)`$ both choices then occur infinitely often. Use the even baseline
``` math
b_n=6+2\left\lfloor\frac{\log(n+1)}2\right\rfloor,
 \qquad
 U_n=\begin{cases}2b_{n-1}-v_k,&n=c_k,\\b_n,&n\notin\{c_k:k\ge0\},\end{cases}
```
and define $`a_n=2U_{n-1}-U_n`$. The separation of the centres will ensure that $`a_{c_k}=v_k`$.

The baseline is even and at least $`6`$. For $`n\ge1`$, the increase of $`\log(n+1)`$ over two consecutive steps is less than $`2`$, so the floor in the definition gives $`b_n-b_{n-1}\in\{0,2\}`$ and $`b_{n+1}-b_{n-1}\le2`$. Away from a centre and its successor, $`a_n=2b_{n-1}-b_n\ge4`$. At a centre, $`a_{c_k}=v_k`$. Immediately afterwards,
``` math
a_{c_k+1}=4b_{c_k-1}-2v_k-b_{c_k+1}
 \ge3b_{c_k-1}-2v_k-2\ge8.
```
Since the centres are at least three apart, these cases exhaust all indices. Also $`0<U_n\le2b_n`$, so $`a_n\le4b_{n-1}\le4\log(n+1)+24`$. The indices $`n=c_k+2`$ lie outside the centres and their successors, because consecutive centres are at least three apart. Along these indices $`a_n\ge b_{n-1}-2\to\infty`$. Thus the sequence is unbounded and cannot be eventually periodic.

Finite telescoping gives
``` math
\sum_{j=1}^{m}a_{N+j}2^{-j}=U_N-U_{N+m}2^{-m}.
```
The bound $`U_n=O(\log(n+1))`$ makes the last term tend to zero. Hence the complete tail equals the integer $`U_N`$, and its initial value is $`6`$. For the cumulative growth, $`b_n=\log(n+1)+O(1)`$ and there are at most $`1+\sqrt{\log_2 N}`$ centres up to $`N`$. Replacing $`b_n`$ by $`U_n`$ changes its partial sum by $`O((\log N)^{3/2})`$. Therefore
``` math
\sum_{j=1}^{N}a_j=2U_0+\sum_{j=1}^{N-1}U_j-U_N
                =N\log N+O(N),
```
which gives the stated asymptotic for $`P_N`$.

The full statement is [kernel-checked in Lean](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/AllResidueLogarithmicR9.lean#L503).

Thus positivity, evenness, unboundedness, nonperiodicity, logarithmic size, cumulative growth $`N\log N`$, and recurrence of the values $`2`$ and $`4`$ in every residue class are jointly compatible with integral tails. These properties alone cannot prove that a tail difference is nonintegral. The sequence is not asserted to consist of prime gaps: its logarithmic bound in particular excludes the extreme large gaps of the primes. The construction therefore does not address hypotheses that use those extreme gaps.

<a id="polynomial-coefficients-and-telescoping-sums"></a>

## Polynomial coefficients and telescoping sums

<div id="long251:res:polynomialcountermodel" class="proposition">

**Proposition 30** (quadratic polynomial-shift countermodel). *Put $`c_n=2(n^2+4n+2)`$ and $`U_n=2(n+4)^2`$. Then $`c_n`$ is positive, even and strictly increasing, $`U_{n+1}=2U_n-c_{n+1}`$, every shift $`U_{N+h}-U_N`$ is integral, $`c_{n+1}-c_n=4n+10`$ is never $`\pm2`$, and
``` math
\sum_{j\ge1}\frac{c_j}{2^{\,j}}=32 .
```*

</div>

Lean: [polynomial countermodel](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L27).

<div class="proof">

*Proof.* Direct expansion gives the recurrence, and the finite telescope is $`\sum_{j=1}^{n}c_j2^{-j}=32-2(n+4)^22^{-n}`$, whose last term tends to zero. The remaining assertions follow from the integer values of $`U_n`$ and from $`c_{n+1}-c_n=4n+10\ge10`$. ◻

</div>

The series starts at $`j=1`$ and equals the initial rescaled tail $`U_0=32`$. Under the opening convention its sum is $`\sum_{n\ge0}c_n2^{-(n+1)}=(c_0+32)/2=18`$. The formal construction checks the [recurrence](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1596), [strict growth](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1632), [integrality of every shift](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1654), [exclusion of adjacent differences of size two](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1644), and the [value $`32`$ for the shifted series](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PolynomialGapSeriesValue.lean#L92), whose summand is $`c_{n+1}/2^{\,n+1}`$; the rational value is recorded at [line 109](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PolynomialGapSeriesValue.lean#L109). Positivity, parity, strict growth, unboundedness and nonperiodicity are therefore jointly compatible with rationality, and the adjacent-gap condition of Theorem <a href="#long251:res:signedwindow" data-reference-type="ref" data-reference="long251:res:signedwindow">16</a> fails at every index. The telescoping mechanism is the one used in the note of ChatGPT 5.4 Pro (orchestrated by Vjeko Kovač) against the variable-denominator expectation of Erdős \[kovac2026, Theorem 1 and proof, pp. 1–2\]; the sequence is not a result about Problem #251.

Rationality also fails to force the coefficients to repeat. Let $`K:\mathbb{N}\to\mathbb{Q}`$ be arbitrary and put $`\kappa_n=2K_n-K_{n+1}`$: the [coefficient of the telescoping series](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1129).

<div id="long251:res:telescope" class="proposition">

**Proposition 31** (exact telescoping). *For every $`n\ge0`$, $`\sum_{i=0}^{n-1}\kappa_i2^{-(i+1)}=K_0-K_n2^{-n}`$.*

</div>

Lean: [carry partial sum eq](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1137).

<div class="proof">

*Proof.* The sum is empty when $`n=0`$. Passing from $`n`$ to $`n+1`$ adds $`(2K_n-K_{n+1})2^{-(n+1)}=K_n2^{-n}-K_{n+1}2^{-(n+1)}`$, which replaces the terminal term by the required one. ◻

</div>

The identity $`\kappa_n=2K_n-K_{n+1}`$ has the algebraic form used in the rationality criterion of Erdős and Straus when $`a_n=2`$. That criterion has additional hypotheses: for integers $`b_n`$ and positive integers $`a_n`$ with $`a_n>1`$ for all large $`n`$ and $`|b_n|/(a_{n-1}a_n)\to0`$, the series $`\sum_nb_n/(a_1\cdots a_n)`$ is rational exactly when some positive integer $`B`$ and integers $`c_n`$ satisfy $`Bb_n=c_na_n-c_{n+1}`$ and $`|c_{n+1}|<a_n/2`$ for all large $`n`$ \[erdosstraus1974, Theorem 2.1, pp. 85–86\]. With $`a_n=2`$, the smallness hypothesis becomes $`|b_n|/4\to0`$. Since the $`b_n`$ are integers, this forces $`b_n=0`$ eventually. Thus the criterion in this specialisation does not apply even to a bounded integer sequence that is nonzero infinitely often, let alone to the positive prime gaps. Proposition <a href="#long251:res:telescope" data-reference-type="ref" data-reference="long251:res:telescope">31</a>, by contrast, imposes no growth condition on $`K`$. The infinite series converges precisely when $`2^{-n}K_n`$ has a finite limit, and then its sum is $`K_0-\lim_{n\to\infty}2^{-n}K_n`$. The sum equals $`K_0`$ precisely when that limit is zero; polynomial growth suffices. For $`K_n=2^n`$, every $`\kappa_n`$ is zero, so the series converges to $`0`$, not to $`K_0=1`$.

The [finite telescoping identity](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1137) is also formalised. Taking $`K_0=\tfrac52`$ and $`K_n=2n+2`$ for $`n\ge1`$ gives $`\kappa_0=1`$ and $`\kappa_n=2n`$, so the coefficients $`1,2,4,6,8,\ldots`$ are positive, even after the first term, unbounded and not eventually periodic, while their dyadic sum is $`\tfrac52`$. Rationality alone therefore cannot imply eventual periodicity even for a positive, parity-correct integer coefficient sequence, and rationality cannot be contradicted merely by Proposition <a href="#long251:res:gap-nonperiodic" data-reference-type="ref" data-reference="long251:res:gap-nonperiodic">15</a>.

The arithmetic-progression formulations of nonintegrality do not create new prime-distribution information. Their full definitions and exact hypotheses are preserved in Appendix <a href="#long251:app:affine-detail" data-reference-type="ref" data-reference="long251:app:affine-detail">15</a>.

<a id="long251:sec:measurements"></a>

# Finite numerical searches

The two searches described below concern finite ranges of the prime-gap tails. Their receipts record floating-point observations, not exact certificates or proofs of occurrence beyond every cutoff. The exact integer checks are given separately in Appendix <a href="#long251:app:certificates" data-reference-type="ref" data-reference="long251:app:certificates">12</a>. The searches have not been rerun for this edition.

Over the $`6\,841\,648`$ primes below $`1.2\times10^{8}`$ and offsets $`h=1,\ldots,16`$, the scan records hits for the reduced two-window event of Theorem <a href="#long251:res:signedwindow" data-reference-type="ref" data-reference="long251:res:signedwindow">16</a> at every tested offset, with observed proportions between $`0.00418`$ and $`0.008248`$ and nearly balanced signs. At $`h=1`$ it records $`56\,427`$ hits among $`6\,841\,564`$ candidate indices, the last at the prime $`119\,995\,753`$. Multiplying the observed proportion in each band by that band’s mean of $`\log p`$ gives $`0.17671`$ in the first band and $`0.13148`$ in the last. This finite observation does not establish an asymptotic counting law or cofinality. The tails in this scan use double-precision arithmetic. The receipt gives no certified enclosure for the accumulated rounding error, so neither a count nor an individual hit is an exact certificate. A bound for the omitted infinite tail would not, by itself, bound that rounding error. Proposition <a href="#long251:res:finite-smallpair" data-reference-type="ref" data-reference="long251:res:finite-smallpair">18</a> gives a separate pair certified by exact integer arithmetic. The receipt is [the adjacent-pair search receipt](https://github.com/wcook04/plectis-erdos/blob/dd6cc708f650f061de06594eba6ba43878f4de31/research/experiments/erdos251/receipts/adjacent-mismatch.json).

A second scan uses the $`1\,270\,607`$ primes below $`2\times10^{7}`$ and pairs of indices in the half-open range $`1\,143\,545\le n,m<1\,270\,540`$. It searches each residue class modulo each $`1\le t\le20`$ for the condition of Theorem <a href="#long251:res:freepair" data-reference-type="ref" data-reference="long251:res:freepair">11</a>, selecting pairs by a next-gap difference of $`2`$ and a shifted-tail window. At $`t=20`$, every residue class has at least $`90\,150`$ counted pairs; pairs may share indices. For each class, the program also records the larger index of a selected late witness. The minimum of those recorded indices is $`1\,270\,520`$; it need not come from the class with the fewest pairs. The saved sample pairs pass the resulting two-window check in floating-point arithmetic. These observations are not exact certificates, and the scan supplies neither arbitrary moduli nor witnesses beyond every prescribed cutoff. The receipt is [the congruent-pair search receipt](https://github.com/wcook04/plectis-erdos/blob/dd6cc708f650f061de06594eba6ba43878f4de31/research/experiments/erdos251/receipts/free-pair.json). The [public computation guide](https://github.com/wcook04/plectis-erdos/blob/dd6cc708f650f061de06594eba6ba43878f4de31/research/experiments/erdos251/README.md) provides the programs, dependencies and exact replay commands for all three recorded runs, including the continued-fraction calculation above.

<a id="long251:sec:open"></a>

# Remaining prime-gap estimates

Theorem <a href="#long251:res:escape-irrational" data-reference-type="ref" data-reference="long251:res:escape-irrational">9</a> reduces irrationality of the actual prime series to nonintegrality of its tail differences. The following two problems distinguish that equivalent condition from the stronger, local condition used by the finite certificates.

<div id="long251:prob:escape" class="problem">

**Problem 32** (nonintegral tail differences of each positive length). For every $`h\ge1`$ and every $`N_0`$, prove that some $`N\ge N_0`$ satisfies
``` math
\begin{equation}
 \sum_{j\ge1}\frac{g_{N+h+j}-g_{N+j}}{2^{\,j}}\notin\mathbb{Z}.
\label{long251:eq:shift-escape}\ltx@label{eq:shift-escape}
\end{equation}
```

</div>

<div id="long251:prob:smallpair" class="problem">

**Problem 33** (two small tail differences at arbitrarily large indices). For every $`h\ge1`$ and every $`N_0`$, prove that some $`N\ge N_0`$ satisfies
``` math
\begin{equation}
 \bigl|\sigma_h(N)\bigr|<1,\qquad
 \bigl|\sigma_h(N+1)\bigr|<1,\qquad
 g_{N+h+1}\ne g_{N+1} .
\label{long251:eq:smallpair}
\end{equation}
```

</div>

Problem <a href="#long251:prob:escape" data-reference-type="ref" data-reference="long251:prob:escape">32</a> and the variable-offset criterion of Theorem <a href="#long251:res:freepair" data-reference-type="ref" data-reference="long251:res:freepair">11</a> are each equivalent to irrationality. By Corollary <a href="#long251:res:smallpair-real" data-reference-type="ref" data-reference="long251:res:smallpair-real">14</a>, Problem <a href="#long251:prob:smallpair" data-reference-type="ref" data-reference="long251:prob:smallpair">33</a> is sufficient; no converse is asserted. These logical reformulations do not supply the required prime-gap estimate.

The counterexamples retain a fixed prefix and modulus (Theorem <a href="#long251:res:boundedperturbation" data-reference-type="ref" data-reference="long251:res:boundedperturbation">22</a>), polynomial nonconcentration and cumulative growth $`n\log n`$ (Corollary <a href="#long251:res:nonconc-primes" data-reference-type="ref" data-reference="long251:res:nonconc-primes">25</a>), or all the congruences and block statistics of the sparse construction. The distinct construction in Section <a href="#long251:res:all-residue-log-countermodel" data-reference-type="ref" data-reference="long251:res:all-residue-log-countermodel">8.5</a> makes two values differing by $`2`$ recur in every residue class. Each has a rational sum; none guarantees prime cumulative positions.

For the actual gaps, Theorem <a href="#long251:res:sparse" data-reference-type="ref" data-reference="long251:res:sparse">28</a> shows that the event in <a href="#long251:eq:smallpair" data-reference-type="eqref" data-reference="long251:eq:smallpair">[long251:eq:smallpair]</a> has density zero for each fixed $`h`$. A proof of its occurrence must therefore find arbitrarily late witnesses inside a sparse set, rather than prove that they occupy a positive proportion. A finite prefix alone cannot do this: it can be retained while the dyadic sum is made rational. A finite block together with a proved bound on the omitted tail can still certify one pair, as in Proposition <a href="#long251:res:finite-smallpair" data-reference-type="ref" data-reference="long251:res:finite-smallpair">18</a>. The distinction is between a finite certified instance and an occurrence theorem beyond every cutoff.

Proposition <a href="#long251:res:explicit-remainder" data-reference-type="ref" data-reference="long251:res:explicit-remainder">17</a> gives sufficient integer inequalities for window membership at a chosen truncation length $`L`$. Failure of such a test need not mean that the complete tail lies outside the window: its error interval may still cross an endpoint. For fixed $`h`$ and $`\varepsilon>0`$, the choice $`L=\lceil(4+\varepsilon)\log_2(N+2)\rceil`$ gives $`E_{h,N,L}=O_{h,\varepsilon}(N^{-\varepsilon})`$. Indeed, $`L=O_\varepsilon(\log N)`$, both arguments of the quartic $`P`$ are $`O_{h,\varepsilon}(N)`$, and $`2^{-L}\le(N+2)^{-4-\varepsilon}`$. Requiring a fixed positive margin from both endpoints is stronger than strict window membership in <a href="#long251:eq:smallpair" data-reference-type="eqref" data-reference="long251:eq:smallpair">[long251:eq:smallpair]</a>. At this depth, the test bounds the signed integer $`2^LF_{h,N,L}`$, not just its residue modulo $`2^L`$, and also requires $`g_{N+h+1}-g_{N+1}=\pm2`$. For fixed $`h`$ and $`\varepsilon`$, checking one certificate uses $`O_\varepsilon(\log N)`$ gap values and the explicit remainder bound. This counts data, not bit operations. The unproved input is the existence of certified witnesses beyond every cutoff for each fixed $`h`$; constants uniform in $`h`$ are not required.

The following published results control gap sizes and clusters, not the signed weighted sums required by this criterion. Zhang’s bounded-gap theorem \[zhang2014, Theorem 1, p. 1122\] produces infinitely many bounded consecutive-prime gaps. Maynard bounds $`\liminf_n(p_{n+m}-p_n)`$ for every fixed $`m`$, giving bounded clusters of every fixed size \[maynard2015, Theorem 1.1, p. 384\], with the explicit unconditional bound $`\liminf_n(p_{n+1}-p_n)\le600`$ \[maynard2015, Theorem 1.3, p. 385\]. Polymath subsequently improved this to $`246`$ \[polymath2014, Theorem 1.4(i) of arXiv v4\]; neither numerical bound controls the signed weighted tails required here. The large-gap theorem of Ford, Green, Konyagin, Maynard and Tao gives an effective lower bound for the largest single consecutive-prime gap below $`X`$ \[fgkmt2018, Theorem 1\]. A theorem giving bounded clusters at each fixed cluster size does not by itself supply a weighted condition on windows whose length grows with the basepoint, and none of these results is used as a proof input here.

Conditionally the picture is different. Tao’s comment names uniform quantitative prime-tuples control of about $`\log\log n`$ consecutive gaps as the plausible route \[erdosproblems251thread, comment of 7 October 2025\], and Land’s draft carries that out under Kuperberg’s uniform prime-tuples conjecture \[land2026\]. The countermodels in Section <a href="#long251:sec:obstructions" data-reference-type="ref" data-reference="long251:sec:obstructions">8</a> show that the listed size, congruence and block-statistical properties alone do not force irrationality. These constructions are not shown to enumerate the consecutive primes, so they do not rule out arguments that combine those properties with further information about primes.

<a id="verification-boundary."></a>

#### Verification boundary.

The smaller denominator bound has a recorded kernel-decided integer certificate. The larger bound is supported by the archived computation and the independent integer-arithmetic replay described above. Neither is an irrationality theorem, and the replay is not a Lean kernel check. The older $`4096`$-bit calculation and the separate justification of its tail bound are discussed in Section <a href="#long251:sec:xr-corrections" data-reference-type="ref" data-reference="long251:sec:xr-corrections">14.7</a>. Declaration-level build status is recorded below, separately from the ordinary proofs and numerical receipts.

<a id="statements-and-declarations"></a>

## Statements and declarations

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

Declaration links identify immutable revisions, not a live branch. The main source links in this manuscript retain revision `3d6d938d696f`; release-only declarations are linked to `52f29ad173b0`. The supplied declaration index distinguishes `ci_checked`, `outside_checked_build`, and `release_only`; presence of a file or link alone is not evidence that its proof was checked. The recorded CI receipt is [run 35073961520](https://github.com/wcook04/plectis-erdos/actions/runs/35073961520). The declaration index records the status of each result. The build record reports `lake build ErdosProblems Erdos249257` with Lean 4.29.1. No new execution of that build is claimed here.

Lean 4 \[lean4\] and mathlib \[mathlib\] provide the proof-checking environment. A checked proof statement, its hypotheses and its transitive axiom report must be distinguished from a challenge containing `sorry`, an executable certificate, or an ordinary proof. Formal checking does not establish novelty, attribution, or the faithfulness of an unexamined mathematical interpretation.

The finite-computation receipts and generating programs remain separately identified in the [pinned computation guide](https://github.com/wcook04/plectis-erdos/blob/dd6cc708f650f061de06594eba6ba43878f4de31/research/experiments/erdos251/README.md). For this edition the self-contained verifier in Appendix <a href="#long251:app:certificates" data-reference-type="ref" data-reference="long251:app:certificates">12</a> was rerun; it checks the adjacent pair and the bound $`2^{589}`$. A separate verifier, supplied as `checks/verify_independent_cf.py`, regenerates the $`80000`$-bit enclosure and checks the Farey certificate for the larger exclusion. It reproduces the common-prefix length and the receipt’s denominator threshold, and checks the stronger neighbouring-denominator sum stated above. It does not rerun the original program’s floating-point statistics or its self-tests on $`e`$ and $`\pi`$. The prime-gap frequency scans were not rerun, and neither verifier is a new Lean build.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.

<a id="acknowledgements."></a>

#### Acknowledgements.

I thank Wouter van Doorn for advice on explaining unfamiliar hypotheses, removing unnecessary terminology, and using notation only when it helps the reader. His comments concerned an earlier note on Problem #243; this acknowledgement does not imply that he reviewed or endorsed the mathematics of the present paper. The problem numbering follows the Erdős Problems catalogue maintained by Thomas Bloom \[erdosproblems\]. The logarithmic-scale construction and the transfer of nonconcentration are retained from the earlier review materials accompanying this project; that provenance is not evidence of independent mathematical review.

<a id="long251:app:prime-bound"></a>

# An elementary polynomial bound for the primes

We prove $`p_n\le1250(n+1)^4`$ for every $`n\ge0`$ by the central binomial coefficient method of Erdős’s proof of Chebyshev’s theorem \[erdos1932, §1, pp. 194–196\]. Let $`\pi(x)`$ count the primes at most $`x`$. For an integer $`m\ge4`$,
``` math
\begin{equation}
\label{long251:eq:binomial-bound}
 4^m<m\binom{2m}{m}\le m(2m)^{\pi(2m)} .
\end{equation}
```
For the first inequality, $`m\binom{2m}{m}/4^{m}`$ equals $`70/64`$ at $`m=4`$ and its ratio at successive indices is $`(2m+1)/(2m)>1`$. For the second, the exponent of a prime $`\ell`$ in $`\binom{2m}{m}`$ is $`\sum_{k\ge1}\bigl(\lfloor2m/\ell^{k}\rfloor-2\lfloor m/\ell^{k}\rfloor\bigr)`$, each summand is $`0`$ or $`1`$, and every summand with $`\ell^{k}>2m`$ vanishes; the exponent is therefore at most $`\lfloor\log_\ell(2m)\rfloor`$. Thus the full power of each prime appearing in $`\binom{2m}{m}`$ is at most $`2m`$. Multiplying over at most $`\pi(2m)`$ distinct primes gives the second inequality.

Now fix $`n\ge0`$, put $`x=n+5`$ and $`m=x^4\ge625`$, and suppose $`\pi(2m)\le n`$. Since $`x\le2^{x}`$ and $`n+4(n+1)x=4x^2-15x-5\le2x^4`$,
``` math
m(2m)^{n}=2^{n}x^{4(n+1)}
 \le2^{\,n+4(n+1)x}\le2^{\,2x^4}=4^{m},
```
contradicting <a href="#long251:eq:binomial-bound" data-reference-type="eqref" data-reference="long251:eq:binomial-bound">[long251:eq:binomial-bound]</a>. Hence $`\pi(2m)>n`$, so at least $`n+1`$ primes lie below $`2m`$ and therefore
``` math
p_n\le2(n+5)^4\le1250(n+1)^4 ,
```
the last step because $`(n+5)\le5(n+1)`$ for $`n\ge0`$. The coarser bound $`p_n\le1250(n+1)^4`$ is checked by the kernel at [line 360](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L360).

<a id="long251:app:certificates"></a>

# Integer certificates

The following calculation uses trial division and integer arithmetic only. It reproduces the two rows of Proposition <a href="#long251:res:finite-smallpair" data-reference-type="ref" data-reference="long251:res:finite-smallpair">18</a> and every inequality used in Theorem <a href="#long251:res:denominatorfloor" data-reference-type="ref" data-reference="long251:res:denominatorfloor">20</a>. The four literals are the certificate the Lean kernel decides in `KernelDenominatorFloor.lean`; their use here requires no floating-point approximation. Adjacent quoted strings are concatenated by Python.

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

The links in this appendix and after selected proofs identify formal definitions and statements at fixed revisions and line numbers. The declaration index records their build status; the ordinary arguments are printed in the paper itself.

The summation-by-parts identity and polynomial prime bound concern the actual primes. The recurrence results apply to arbitrary integer coefficients and, as stated, rational or real sequences. Substituting the actual prime-gap tail requires its convergence and boundary condition. The finite certificates use the same polynomial bound to control the omitted terms. The counterexamples concern other coefficient sequences, not a construction of new primes. The complete link inventory is also retained in the TeX source.

<a id="long251:sec:coverage"></a>

## Formalisation coverage and remaining dependencies

<div id="coverage">

</div>

Every theorem, lemma, proposition and corollary of this record other than the four listed below has a Lean statement of the same assertion, with the same hypotheses, checked by the Lean kernel using only the axioms `propext`, `Classical.choice` and `Quot.sound`, in the development at revision `181078b6b009`.

Three of the exceptions share cited inputs. The development verifies the reduction of Theorem <a href="#long251:res:sparse" data-reference-type="ref" data-reference="long251:res:sparse">28</a> to Schlage-Puchta’s lemma that, for a fixed nonzero integer polynomial in a fixed block of consecutive prime gaps, the set of indices where it vanishes has density zero \[schlagepuchta2011, Lemma 4, pp. 5–6\], and the reduction of Corollary <a href="#long251:res:nonconc-primes" data-reference-type="ref" data-reference="long251:res:nonconc-primes">25</a> and Corollary <a href="#long251:res:jointcountermodel" data-reference-type="ref" data-reference="long251:res:jointcountermodel">27</a> to that lemma together with the prime number theorem in the form $`p_n\sim n\log n`$ \[mv2007, Chapter 6\]. Formal proofs of those two inputs are not included in the verified development, so these three endpoints remain conditional on them. What each statement adds to them is checked, including the estimate that the corrected sequence of Corollary <a href="#long251:res:jointcountermodel" data-reference-type="ref" data-reference="long251:res:jointcountermodel">27</a> differs from the prime gaps at $`O_\varepsilon(n/\log\log n)`$ indices below $`n`$, which uses no information about the distribution of primes.

Theorem <a href="#long251:res:cfexclusion" data-reference-type="ref" data-reference="long251:res:cfexclusion">21</a> is a different case. Its deduction from the four integer comparisons between the enclosure and its Farey neighbours is checked in general form, and the certificate those comparisons are applied to is too large for the Lean kernel to evaluate at present. The exclusion therefore rests on the separate exact-arithmetic verifier described in its proof.

A theorem whose own statement is conditional is formalised exactly as stated. The four results above are asserted unconditionally here, and their Lean counterparts either carry a named input or rest on a computation the kernel does not perform.

<a id="concordance-of-statements-and-lean-declarations."></a>

#### Concordance of statements and Lean declarations.

Each result of this record that has a kernel-checked Lean statement of the same assertion is listed below with the declarations that jointly state it. Each name links to its declaration at revision `a25cb360bef8`. Where the Lean statement is stronger than the printed one and implies it by an immediate specialisation, the entry says so. An entry marked *compared* was also checked independently: a restatement of the same declarations against Mathlib alone, together with its proof, was verified by Comparator (`leanprover/comparator`) in a clean continuous integration environment, in the run named by its number. Comparator trusts the restated statement, so the correspondence between the printed result and that statement is the one this concordance records.

Theorem <a href="#long251:res:sparse-rationalisation" data-reference-type="ref" data-reference="long251:res:sparse-rationalisation">1</a>: [`arbitrary_word_sparse_rationalisation_uniform`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/SparseAmbientR9.lean#L269), [`polylogarithmic_word_interval_uniform`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/SparsePaperR11.lean#L137), [`bounded_test_finite_coupling`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/SparseConstructionAudit.lean#L8). *Compared*, runs [`35544127144`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35544127144), [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Corollary <a href="#long251:res:local-targets" data-reference-type="ref" data-reference="long251:res:local-targets">2</a>: [`local_target_interval`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/LocalTargetInterval.lean#L38). *Compared*, run [`35674034595`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35674034595).

Proposition <a href="#long251:res:abel" data-reference-type="ref" data-reference="long251:res:abel">3</a>: [`dyadicPartialSumQ_eq_start_add_differences`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L138). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Theorem <a href="#long251:res:parts" data-reference-type="ref" data-reference="long251:res:parts">4</a>: [`prime0_dyadic_summation_by_parts`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L172). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Theorem <a href="#long251:res:infinite" data-reference-type="ref" data-reference="long251:res:infinite">5</a>: [`infinite_prime_gap_identity`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L47). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Corollary <a href="#long251:res:irr-equivalence" data-reference-type="ref" data-reference="long251:res:irr-equivalence">6</a>: [`irrationality_reformulation`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L56). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Theorem <a href="#long251:res:block" data-reference-type="ref" data-reference="long251:res:block">8</a>: [`real_block_identity`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L76). *Compared*, run [`35674034595`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35674034595).

Theorem <a href="#long251:res:escape-irrational" data-reference-type="ref" data-reference="long251:res:escape-irrational">9</a>: [`rationality_classification`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L94). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Lemma <a href="#long251:res:true-tail" data-reference-type="ref" data-reference="long251:res:true-tail">10</a>: [`real_dyadic_orbit_eq_true_tail_iff`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/TrueTail.lean#L57). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Theorem <a href="#long251:res:freepair" data-reference-type="ref" data-reference="long251:res:freepair">11</a>: [`actual_free_pair_criterion`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L189). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Theorem <a href="#long251:res:lcmdiagonal" data-reference-type="ref" data-reference="long251:res:lcmdiagonal">12</a>: [`irrational_initial_iff_all_lcmDiagonal_nonintegral`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/OrderLatticeDiagonal.lean#L153). *Compared*, run [`35674034595`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35674034595).

Theorem <a href="#long251:res:smallpair" data-reference-type="ref" data-reference="long251:res:smallpair">13</a>: [`rational_small_pair_bundle`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L267). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Corollary <a href="#long251:res:smallpair-real" data-reference-type="ref" data-reference="long251:res:smallpair-real">14</a>: [`real_small_pair_prime_endpoint`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L298). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Proposition <a href="#long251:res:gap-nonperiodic" data-reference-type="ref" data-reference="long251:res:gap-nonperiodic">15</a>: [`prime_gaps_not_eventually_periodic`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L175). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Theorem <a href="#long251:res:signedwindow" data-reference-type="ref" data-reference="long251:res:signedwindow">16</a>: [`real_signed_two_window`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L135). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Proposition <a href="#long251:res:explicit-remainder" data-reference-type="ref" data-reference="long251:res:explicit-remainder">17</a>: [`explicit_remainder_certificate`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperTailBoundsR7.lean#L211). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Proposition <a href="#long251:res:finite-smallpair" data-reference-type="ref" data-reference="long251:res:finite-smallpair">18</a>: [`finite_small_pair`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperFiniteCertificatesR7.lean#L111). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Proposition <a href="#long251:res:one-tail-certificate" data-reference-type="ref" data-reference="long251:res:one-tail-certificate">19</a>: [`one_tail_signed_certificate`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/FiniteSeparation.lean#L6). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Theorem <a href="#long251:res:denominatorfloor" data-reference-type="ref" data-reference="long251:res:denominatorfloor">20</a>: [`denominator_floor_both`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperFiniteCertificatesR7.lean#L142), [`denominator_floor_decimal`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperFiniteCertificatesR7.lean#L137). *Compared*, runs [`35544127144`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35544127144), [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Theorem <a href="#long251:res:boundedperturbation" data-reference-type="ref" data-reference="long251:res:boundedperturbation">22</a>: [`rational_bounded_perturbation`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L200). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Proposition <a href="#long251:res:shiftedcount" data-reference-type="ref" data-reference="long251:res:shiftedcount">23</a>: [`shifted_count_bound`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/ShiftedGapCountingR9.lean#L152). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Theorem <a href="#long251:res:nonconcentration" data-reference-type="ref" data-reference="long251:res:nonconcentration">24</a>: [`finite_perturbation_stability`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperNonconcentrationR7.lean#L100). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Proposition <a href="#long251:res:sparse-nonconcentration" data-reference-type="ref" data-reference="long251:res:sparse-nonconcentration">26</a>: [`sparse_nonconcentration`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/SparseNonconcentration.lean#L80). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Theorem <a href="#long251:res:polignacfail" data-reference-type="ref" data-reference="long251:res:polignacfail">29</a>: [`exists_logarithmic_recurring_values_countermodel`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/LogarithmicCarryAsymptoticsR8.lean#L368). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Proposition <a href="#long251:res:polynomialcountermodel" data-reference-type="ref" data-reference="long251:res:polynomialcountermodel">30</a>: [`polynomial_countermodel`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L27). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Proposition <a href="#long251:res:telescope" data-reference-type="ref" data-reference="long251:res:telescope">31</a>: [`carryPartialSum_eq`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1137). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Proposition <a href="#long251:xr:totient" data-reference-type="ref" data-reference="long251:xr:totient">34</a>: [`tailShift_integral_totient_of_odd_den`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L877). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Proposition <a href="#long251:xr:propagate" data-reference-type="ref" data-reference="long251:xr:propagate">35</a>: [`realTailShift_integral_add`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/RealPropagation.lean#L27). *Compared*, run [`35674034595`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35674034595).

Proposition <a href="#long251:xr:truncation" data-reference-type="ref" data-reference="long251:xr:truncation">36</a> (the Lean statement is stronger): [`cofinal_escape_of_finite_truncation`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperTailBoundsR7.lean#L261). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Proposition <a href="#long251:res:complete-truncation" data-reference-type="ref" data-reference="long251:res:complete-truncation">37</a>: [`finite_separation_complete`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/FiniteSeparation.lean#L25). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Proposition <a href="#long251:xr:boundedpolignac" data-reference-type="ref" data-reference="long251:xr:boundedpolignac">39</a> (the Lean statement is stronger): [`bounded_recurring_values_countermodel`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperBoundedCarryR7.lean#L179). *Compared*, run [`35605146048`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35605146048).

Theorem <a href="#long251:res:affinecollapse" data-reference-type="ref" data-reference="long251:res:affinecollapse">40</a>: [`affine_circularity_bundle`](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L241). *Compared*, run [`35674034595`](https://github.com/wcook04/plectis-erdos-lean/actions/runs/35674034595).

<a id="sparse-construction."></a>

#### Sparse construction.

The source index records [the interval theorem for an arbitrary sequence](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/SparseAmbientR9.lean#L217), [its rational-target consequence](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/SparsePaperR11.lean#L53), [the polylogarithmic interval theorem](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/SparsePaperR11.lean#L78), [the block total-variation bound](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/GrowingBlocksR11.lean#L139) and [the uniform bounded-test theorem](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/GrowingBlocksR11.lean#L152) as `ci_checked`. The formal construction chooses one coordinate at a time, rather than the triples used here. Its polylogarithmic statement fixes the permitted set, interval, and support-count constant and cutoff before the target; the eventual congruences and convergence are quantified after it. The common support-count bound and same-index block comparison therefore give a target-independent statistical error bound. A common congruence cutoff instead requires the construction, which chooses it from the schedule and modulus. The printed schedule independently supplies the common cutoffs and bounds in Theorem <a href="#long251:res:sparse-rationalisation" data-reference-type="ref" data-reference="long251:res:sparse-rationalisation">1</a>. The recorded build status is described under Statements and declarations; no new Lean build is claimed.

<a id="finite-shifted-gap-count."></a>

#### Finite shifted-gap count.

The supplied release contains a [relocated proof of the finite shifted-gap count](https://github.com/wcook04/plectis-erdos-lean/blob/52f29ad173b04e3bac941b3663f2b9aebe5de0bb/ErdosProblems/Erdos251/ShiftedCountingSourceR11.lean) in Proposition <a href="#long251:res:shiftedcount" data-reference-type="ref" data-reference="long251:res:shiftedcount">23</a>. Its natural-number triples agree with the printed integer triples: $`x,d,s`$ and $`x+s+d+r`$ are positive under the stated conditions. The finite inequality has no sieve premise; the separate sieve-dependent density-zero implication is not used here. The declaration index records this file as `release_only`, not `ci_checked`; source availability does not establish a successful build.

<a id="finite-summation-by-parts."></a>

#### Finite summation by parts.

Formalised as the [summation-by-parts identity](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L138). The finite identity requires no positivity, monotonicity or convergence.

<a id="prime-gap-summation-by-parts."></a>

#### Prime-gap summation by parts.

Formalised as the [prime-gap summation by parts](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L172), using the [gap partial sum](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L161) and the [agreement of the two gap formulas](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L156); the latter records that the natural-number difference $`p_{n+1}-p_n`$ agrees with the difference taken in $`\mathbb{Q}`$, which needs $`p_n\le p_{n+1}`$, the [increase of consecutive primes](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L152).

<a id="convergence-and-the-infinite-identity."></a>

#### Convergence and the infinite identity.

The sources prove the [polynomial prime bound](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L360), [convergence of the prime series](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L379) and the [convergence transfer to the gap series](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L385). The identity in Theorem <a href="#long251:res:infinite" data-reference-type="ref" data-reference="long251:res:infinite">5</a> is the [unconditional prime-gap identity](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L427).

<a id="the-irrationality-equivalences."></a>

#### The irrationality equivalences.

The source proves the [irrationality equivalence between $`\Pi`$ and $`S`$](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L435). For the second normalisation, it proves the [identity $`\sum_{n\ge0}p_n2^{-n}=4+2S`$](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L444) and the [corresponding irrationality equivalence](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L459).

<a id="the-general-recurrence."></a>

#### The general recurrence.

The source defines the [tail recurrence](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L482), the [shift](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L544), and [integrality](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L575).

<a id="iteration-of-the-recurrence."></a>

#### Iteration of the recurrence.

The source versions of Theorem <a href="#long251:res:block" data-reference-type="ref" data-reference="long251:res:block">8</a> give the [iterated block identity](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L653) and the [scaled shift identity](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L667).

<a id="two-consecutive-small-differences."></a>

#### Two consecutive small differences.

The sources for Theorem <a href="#long251:res:smallpair" data-reference-type="ref" data-reference="long251:res:smallpair">13</a> and Corollary <a href="#long251:res:smallpair-real" data-reference-type="ref" data-reference="long251:res:smallpair-real">14</a> are the rational [adjacent small-shift obstruction](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L979), its [arbitrarily late consequence](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1006), the [real small-pair implication](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L99), and the [sufficient condition for irrationality](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L120).

<a id="congruent-indices."></a>

#### Congruent indices.

For Theorem <a href="#long251:res:freepair" data-reference-type="ref" data-reference="long251:res:freepair">11</a>, the source gives the [criterion for congruent indices](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/FreePairReduction.lean#L92), the [eventual congruence classification](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/FreePairReduction.lean#L105), and the [irrationality criterion using congruent indices](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/FreePairReduction.lean#L236), using the [actual real tail recurrence](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/FreePairReduction.lean#L186).

<a id="denominators-and-integral-shifts."></a>

#### Denominators and integral shifts.

The sources for <a href="#long251:eq:den-law" data-reference-type="eqref" data-reference="long251:eq:den-law">[long251:eq:den-law]</a> and its consequences give the [denominator recurrence](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1217), its [odd case](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1226) and [even case](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1236), the [denominator classification](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1279), the [totient shift](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L877), and the [propagation of an integral shift to every later index](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L900).

<a id="rationality-of-the-initial-value."></a>

#### Rationality of the initial value.

For Theorem <a href="#long251:res:escape-irrational" data-reference-type="ref" data-reference="long251:res:escape-irrational">9</a>, the sources give two rationality criteria: [one integral shift of positive length](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1479) and [eventual integrality for a fixed positive length](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1525). The corresponding irrationality criteria are [nonintegrality at every index for every positive length](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1551) and [arbitrarily late nonintegrality for every positive length](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1572).

<a id="long251:sec:erdos-251-extended-record"></a>

# Further criteria, examples and computational details

This appendix proves additional consequences of the recurrence, explains the finite truncation test, and gives a bounded counterexample and the full numerical table. These results are not needed for the sparse construction.

<a id="long251:sec:xr-totient"></a>

## Totient-length shifts and persistence of integrality

Euler’s congruence gives an explicit integral shift once the denominator is odd. The next proposition records that choice of length; the following one shows that integrality then persists at later indices.

<div id="long251:xr:totient" class="proposition">

**Proposition 34** (a shift of totient length). *Let $`T:\mathbb{N}\to\mathbb{Q}`$ satisfy the dyadic tail recurrence with integer coefficients. If the reduced denominator $`d`$ of $`T_N`$ is odd, then $`\sigma_{\varphi(d)}(N)`$ is an integer.*

</div>

Lean: [tail shift integral totient of odd den](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L877).

<div class="proof">

*Proof.* Since $`d`$ is odd, $`2`$ and $`d`$ are coprime, so Euler’s congruence gives $`d\mid2^{\varphi(d)}-1`$. Writing $`2^{\varphi(d)}-1=dk`$ and $`T_N=u/d`$ in lowest terms, $`(2^{\varphi(d)}-1)T_N=ku`$ is an integer, and the integral-shift criterion transfers this to the shift. ◻

</div>

<div id="long251:xr:propagate" class="proposition">

**Proposition 35** (propagation). *Let $`T:\mathbb{N}\to\mathbb{R}`$ satisfy $`T_{n+1}=2T_n-a_{n+1}`$ with integer coefficients, and define $`\sigma_h(N)=T_{N+h}-T_N`$. For fixed $`h,N\ge0`$, if $`\sigma_h(N)`$ is an integer, then $`\sigma_h(N+k)`$ is an integer for every $`k\ge0`$.*

</div>

Lean: [real tail shift integral add](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/RealPropagation.lean#L27).

<div class="proof">

*Proof.* The shift step identity gives $`\sigma_h(N+1)=2\sigma_h(N)-(a_{N+h+1}-a_{N+1})`$, an integer combination of an integer and two coefficients. Induct on $`k`$. ◻

</div>

These are the totient shift and the propagation theorems cited in the note. For example, if $`\operatorname{den}T_N=3`$ then $`\varphi(3)=2`$ and $`3T_N`$ is an integer, so $`\sigma_2(N)`$ is integral while $`\sigma_1(N)`$ is not; if $`\operatorname{den}T_N=5`$ then $`\sigma_4(N)`$ is integral. In the orbit with every coefficient zero and $`T_0=1/12`$, the denominator is $`12=2^2\cdot3`$, the orbit reaches $`T_2=1/3`$ with odd denominator at $`s=2`$, and $`h=\varphi(3)=2`$ is exactly the shift length seen to be integral from index $`2`$ onwards. The totient supplies one length, while the exact criterion is $`\operatorname{den}(T_N)\mid2^{h}-1`$. At an index with odd denominator $`d>1`$, the least positive length is the multiplicative order of $`2`$ modulo $`d`$. When $`d=1`$, every positive length works; before the denominator becomes odd, no positive length works.

<a id="long251:sec:xr-truncation"></a>

## The finite truncation criterion

Here $`g_n`$ denotes the actual prime gaps. We bound the omitted terms by a nonnegative majorant whose dyadic series converges. For an arbitrary real-valued majorant, convergence alone does not provide a computable remainder bound. The polynomial bound in Proposition <a href="#long251:res:explicit-remainder" data-reference-type="ref" data-reference="long251:res:explicit-remainder">17</a> supplies an explicit rational bound, so the resulting certificate can be checked by integer arithmetic.

<div class="samepage">

<div id="long251:xr:truncation" class="proposition">

**Proposition 36** (finite truncation). *Let $`M:\mathbb{N}\to\mathbb{R}`$ satisfy $`M(n)\ge g_n`$ for every $`n`$ and $`\sum_{n\ge0}M(n)2^{-n}<\infty`$, and put
``` math
S_{h,N,L}=\sum_{j=1}^{L}\frac{g_{N+h+j}-g_{N+j}}{2^{\,j}},\qquad
 R_{h,N,L}(M)=\sum_{j>L}\frac{M(N+h+j)+M(N+j)}{2^{\,j}} .
```
If for every $`h\ge1`$ and every $`N_0`$ there are $`N\ge N_0`$ and $`L\ge1`$ with $`\operatorname{dist}(S_{h,N,L},\mathbb{Z})>R_{h,N,L}(M)`$, then the nonintegrality condition in Problem <a href="#long251:prob:escape" data-reference-type="ref" data-reference="long251:prob:escape">32</a> holds.*

</div>

Lean: [cofinal escape of finite truncation](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperTailBoundsR7.lean#L261).

</div>

<div class="proof">

*Proof.* The part of $`\sum_{j\ge1}(g_{N+h+j}-g_{N+j})2^{-j}`$ omitted from $`S_{h,N,L}`$ has absolute value at most $`R_{h,N,L}(M)`$, so under the displayed inequality the full sum lies at positive distance from every integer. ◻

</div>

Unlike the signed-window test, this criterion asks only for separation from the integers. The distance from the truncated sum to $`\mathbb{Z}`$ is determined by a finite integer calculation. Write the weighted block sum as
``` math
D_{h,N,L}=\sum_{j=1}^{L}2^{\,L-j}(g_{N+h+j}-g_{N+j}),
 \qquad S_{h,N,L}=\frac{D_{h,N,L}}{2^{L}}.
```
Then
``` math
\operatorname{dist}(S_{h,N,L},\mathbb{Z})
 =2^{-L}\min\bigl\{D_{h,N,L}\bmod2^{L},\;
 2^{L}-(D_{h,N,L}\bmod2^{L})\bigr\},
```
where $`D_{h,N,L}\bmod2^{L}`$ is the least nonnegative residue, including when $`D_{h,N,L}<0`$. The criterion requires this residue to be more than $`2^LR_{h,N,L}(M)`$ from both $`0`$ and $`2^L`$. One successful comparison certifies nonintegrality at that index; a failed comparison is inconclusive. Irrationality requires such certificates arbitrarily late for every positive $`h`$. At prescribed logarithmic depth, the needed residue must be farther from both endpoints than the error bound. With the polynomial majorant in Proposition <a href="#long251:res:explicit-remainder" data-reference-type="ref" data-reference="long251:res:explicit-remainder">17</a>, the remainder bound is rational and explicit, so the whole test reduces to integer comparisons. The modular rewriting is an ordinary deduction, not a separately checked Lean declaration.

<div id="long251:res:complete-truncation" class="proposition">

**Proposition 37** (completeness of finite separation). *Suppose $`D\in\mathbb{R}`$, $`S_L\in\mathbb{R}`$ and $`R_L\ge0`$ satisfy $`|D-S_L|\le R_L`$ and $`R_L\to0`$. Then
``` math
D\notin\mathbb{Z}\quad\Longleftrightarrow\quad
 \text{there exists }L\text{ with }\operatorname{dist}(S_L,\mathbb{Z})>R_L.
```*

</div>

Lean: [finite separation complete](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/FiniteSeparation.lean#L25).

<div class="proof">

*Proof.* The reverse implication follows from the triangle inequality. For the forward implication put $`\delta=\operatorname{dist}(D,\mathbb{Z})>0`$. For all sufficiently large $`L`$, one has $`R_L<\delta/2`$, and the $`1`$-Lipschitz property of distance gives $`\operatorname{dist}(S_L,\mathbb{Z})\ge\delta-R_L>R_L`$. No monotonicity of the errors is required. ◻

</div>

For fixed $`h,N`$ and the explicit polynomial remainder, testing $`L=1,2,\ldots`$ therefore stops with a certificate whenever $`\sigma_h(N)`$ is nonintegral. An unsuccessful comparison is inconclusive. A proof that every depth fails, unlike a finite unsuccessful run, would imply integrality by the same equivalence. None of this shows that suitable indices occur arbitrarily late. Quantitative estimates are still needed to guarantee separation at a prescribed truncation length as $`N`$ varies. For a numerical example unrelated to primes, $`[1-2^{-N},1+2^{-N}]`$ contains both the noninteger $`1+2^{-2N}`$ and the integer $`1`$ for every $`N\ge1`$. Its radius tends to zero, yet it never certifies the changing value as nonintegral. This does not contradict completeness, which keeps the value fixed while refining its enclosure.

<a id="long251:sec:xr-divisorhit"></a>

## Nonintegral differences at multiples of each shift

<div id="long251:xr:divisor-hit" class="problem">

**Problem 38** (multiples of each shift). For every $`r\ge1`$, is there an $`m\ge1`$ such that the tail differences of length $`mr`$ are nonintegral at arbitrarily large indices, as in <a href="#long251:eq:shift-escape" data-reference-type="eqref" data-reference="long251:eq:shift-escape">[long251:eq:shift-escape]</a>?

</div>

This is an exact reformulation, not a weaker mathematical target. If $`T_0`$ is irrational, every positive shift is nonintegral by the block identity, so the stated condition follows with $`m=1`$. Conversely, rationality gives a shift $`h\ge1`$ that is integral at every sufficiently late index. For each positive integer $`m`$, the identity
``` math
T_{N+mh}-T_N=\sum_{j=0}^{m-1}(T_{N+(j+1)h}-T_{N+jh})
```
makes every multiple $`mh`$ eventually integral. Taking $`r=h`$ contradicts the stated condition. This ordinary deduction uses the checked rationality classification and a finite telescope; rearranging the quantifiers supplies no new estimate for the actual prime gaps.

<a id="long251:sec:xr-compression"></a>

## Repeated tail values and congruent indices

In this subsection, $`T_N=\sum_{j\ge1}g_{N+j}2^{-j}`$ denotes the complete tail of the actual prime-gap series, rather than an arbitrary solution of the recurrence. The first argument uses the prime number theorem to find many equal tail values under rationality. The second distinguishes these repetitions from the nonintegral differences required at congruent indices. Both are ordinary deductions; the linked formal results concern the recurrence and the congruent-index criterion.

<a id="repeated-tail-values."></a>

#### Repeated tail values.

For an integer $`X\ge0`$, summing $`g_{N+1}=2T_N-T_{N+1}`$ over $`0\le N<X`$ gives the exact identity
``` math
\sum_{N=0}^{X}T_N=p_{X+1}-p_1-T_0+2T_X
 \le(p_{X+1}-p_0)+2T_X.
```
The inequality uses $`T_0\ge0`$ and $`p_1\ge p_0`$. The prime number theorem \[mv2007, Ch. 6\] also gives
``` math
\begin{equation}
\label{long251:eq:tail-small-relative-prime}
 \frac{T_X}{p_X}
 =\sum_{j\ge1}\frac{g_{X+j}}{2^jp_X}\longrightarrow0.
\end{equation}
```
Indeed, for each fixed $`j`$, both $`p_{X+j+1}/p_X`$ and $`p_{X+j}/p_X`$ tend to $`1`$, so their difference $`g_{X+j}/p_X`$ tends to zero. For the uniform bound needed to pass the limit through the sum, the two-sided estimates $`p_n\asymp n\log n`$ give one constant $`K`$ such that, for $`X\ge2`$ and $`j\ge1`$,
``` math
\begin{aligned}
 \frac{g_{X+j}}{p_X}
 &\le K\frac{(X+j+1)\log(X+j+1)}{X\log X}\\
 &\le K(1+j)\left(1+\frac{\log(1+j)}{\log X}\right)
 \le K(1+j)^2.
 \end{aligned}
```
The second line uses $`X+j+1\le X(1+j)`$ and $`\log(1+j)\le j\log2\le j\log X`$. Since $`\sum_{j\ge1}(1+j)^2 2^{-j}<\infty`$, dominated convergence applies. Subtracting the exact summation identities at $`2X`$ and $`X`$ now gives
``` math
\sum_{X<N\le2X}T_N
 =p_{2X+1}-p_{X+1}+2(T_{2X}-T_X)
 \sim X\log X.
```
Indeed, the prime difference is asymptotic to $`X\log X`$, and <a href="#long251:eq:tail-small-relative-prime" data-reference-type="eqref" data-reference="long251:eq:tail-small-relative-prime">[long251:eq:tail-small-relative-prime]</a> makes both tail terms $`o(X\log X)`$. Thus the mean complete tail in this band is asymptotic to $`\log X`$, without a rationality assumption. This is a mean, not a pointwise estimate. For the counting argument we only need the upper bound $`\sum_{X<N\le2X}T_N\le K_0X\log X`$, valid for any fixed $`K_0>1`$ and all sufficiently large $`X`$. For each fixed $`C>1`$, Markov’s inequality then leaves at least $`(1-1/C)X`$ indices with $`T_N\le K_0C\log X`$.

Under rationality, take $`X`$ beyond the point where the reduced denominator is the fixed odd integer $`d`$. Among the indices just selected by Markov’s inequality, the values lie in $`d^{-1}\mathbb{Z}_{\ge0}\cap[0,K_0C\log X]`$. There are at most $`dK_0C\log X+1`$ such values. Pigeonhole therefore gives one value occurring at least
``` math
\frac{(1-1/C)X}{dK_0C\log X+1}
```
times. Taking, for example, $`K_0=2`$ gives a lower bound of order $`\gg_{C,d}X/\log X`$. The value may depend on $`X`$; no single value recurring in every band is established.

This count uses the growth of the actual primes. It is false for a general rational integer-coefficient recurrence: the quadratic countermodel of Proposition <a href="#long251:res:polynomialcountermodel" data-reference-type="ref" data-reference="long251:res:polynomialcountermodel">30</a> has strictly increasing tails $`T_N=2(N+4)^2`$. Even for the primes, equal-tail pairs have difference zero and hence do not supply the nonintegral difference required by the criterion using congruent indices.

The terminal term in the exact identity cannot simply be omitted. The factorial-gap argument in the proof of Proposition <a href="#long251:res:gap-nonperiodic" data-reference-type="ref" data-reference="long251:res:gap-nonperiodic">15</a> shows that $`T_X\ge g_{X+1}/2`$ is unbounded, whereas $`p_1+T_0`$ is fixed. The exact identity therefore gives $`\sum_{N=0}^{X}T_N>p_{X+1}`$ for arbitrarily large $`X`$. It does not establish that this strict inequality holds eventually.

<a id="the-interval-condition-at-congruent-indices."></a>

#### The interval condition at congruent indices.

Suppose the sum is rational, let $`d`$ be the eventual odd reduced denominator, and let $`t`$ be the order of $`2`$ modulo $`d`$, with $`t=1`$ when $`d=1`$. Beyond the denominator cutoff, $`M\equiv N\pmod t`$ forces $`T_M-T_N\in\mathbb{Z}`$. Neither this difference nor its negative can then lie in $`(\tfrac12,1)`$. Thus a witness in that interval, at two such congruent indices, would contradict rationality without a further condition on the intervening gaps. This uses only the interval occurring in Theorem <a href="#long251:res:signedwindow" data-reference-type="ref" data-reference="long251:res:signedwindow">16</a>; it does not assert that its other hypotheses hold for arbitrary congruent pairs.

<a id="long251:sec:xr-boundedpolignac"></a>

## A bounded companion to the recurring-values countermodel

The logarithmic growth in Theorem <a href="#long251:res:polignacfail" data-reference-type="ref" data-reference="long251:res:polignacfail">29</a> gives its cumulative sequence the same leading asymptotic $`n\log n`$ as the primes. The same mechanism is visible in the following bounded example.

<div id="long251:xr:boundedpolignac" class="proposition">

**Proposition 39** (bounded recurring-values countermodel). *Put $`U_0=4`$ and, for $`n\ge1`$, $`U_n=6`$ when $`n=k!`$ for some $`k\ge3`$ and $`U_n=4`$ otherwise, and set $`a_n=2U_{n-1}-U_n`$ for $`n\ge1`$. Then $`a_n\in\{2,4,8\}`$. For every $`k\ge3`$, the value $`2`$ occurs at index $`k!`$ and the value $`4`$ at index $`2\,k!`$, so both recur infinitely often at indices divisible by any fixed $`t\ge1`$. The series $`\sum_{n\ge1}a_n2^{-n}`$ equals $`4`$ and every tail $`\sum_{j\ge1}a_{N+j}2^{-j}`$ equals the integer $`U_N`$.*

</div>

Lean: [bounded recurring values countermodel](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperBoundedCarryR7.lean#L179).

<div class="proof">

*Proof.* For $`k\ge3`$ the index $`k!`$ is even and at least $`6`$, and $`k!-1`$ is odd, so the predecessor of a spike is an ordinary index; hence $`a_{k!}=8-6=2`$, $`a_{k!+1}=12-4=8`$, and $`a_n=8-4=4`$ elsewhere. For $`k\ge2`$ one has $`k!<2\,k!<(k+1)!`$, so $`2\,k!`$ is not a factorial. Its odd predecessor $`2\,k!-1\ge3`$ is not a factorial either; therefore $`a_{2k!}=4`$. Since $`t\mid k!`$ for every large $`k`$, both values recur in the residue class $`0`$ modulo $`t`$. The identity $`a_n2^{-n}=U_{n-1}2^{-(n-1)}-U_n2^{-n}`$ telescopes to $`\sum_{j=1}^{m}a_{N+j}2^{-j}=U_N-U_{N+m}2^{-m}`$, and $`U`$ is bounded, so the endpoint vanishes. ◻

</div>

The indices with coefficient $`2`$ are precisely the factorials $`k!`$, $`k\ge3`$. They occur infinitely often with unbounded gaps, which is impossible for a value recurring in an eventually periodic sequence. Thus even this bounded coefficient sequence is nonperiodic, despite its rational dyadic sum. Its cumulative sum has linear growth. The logarithmic construction in Theorem <a href="#long251:res:polignacfail" data-reference-type="ref" data-reference="long251:res:polignacfail">29</a> adds unboundedness and cumulative growth $`N\log N`$ without changing the telescoping mechanism. Neither construction guarantees prime cumulative positions.

<a id="long251:sec:xr-densities"></a>

## Numerical counts and proportions

Section <a href="#long251:sec:measurements" data-reference-type="ref" data-reference="long251:sec:measurements">9</a> describes the scan over the $`6\,841\,648`$ primes under $`1.2\times10^{8}`$, with double-precision tails. The table gives its reported counts for $`h=1,\ldots,4`$; the scan covered all offsets $`h\le16`$. Each proportion divides the event count by $`6\,841\,565-h`$ tested basepoints, not by the number of primes.

<div class="center">

| $`h`$ | events | proportion | $`\delta=+2`$ | $`\delta=-2`$ | last event at prime |
|------:|-------:|-----------:|--------------:|--------------:|--------------------:|
|     1 | 56 427 |   0.008248 |        28 022 |        28 405 |         119 995 753 |
|     2 | 31 979 |   0.004674 |        15 742 |        16 237 |         119 993 807 |
|     3 | 30 233 |   0.004419 |        15 093 |        15 140 |         119 998 321 |
|     4 | 29 262 |   0.004277 |        14 606 |        14 656 |         119 993 473 |

</div>

The scan records hits at every tested offset $`h\le16`$. The observed proportions range from $`0.00418`$ to $`0.008248`$, with nearly balanced signs at each offset. For $`h=1`$, the first row below gives the proportions in the eight bands; the second multiplies each by its band’s mean of $`\log p`$:
``` math
\begin{array}{l}
 0.011285,\;0.008951,\;0.008303,\;0.007936,\;0.007651,\;0.007507,\;0.007253,\;0.007094;\\[2pt]
 0.17671,\;0.15058,\;0.14420,\;0.14067,\;0.13766,\;0.13667,\;0.13333,\;0.13148 .
\end{array}
```
The ratio of the last rescaled proportion to the first is $`0.744`$ at $`h=1`$ and lies between $`0.744`$ and $`0.8121`$ across the measured offsets. Theorem <a href="#long251:res:sparse" data-reference-type="ref" data-reference="long251:res:sparse">28</a> gives limiting density zero for each fixed offset. The bound $`O_h(X/\log\log X)`$ derived after its proof is only an upper bound; it predicts neither a monotone decline nor an asymptotic proportion. The finite-band ratios therefore do not establish an asymptotic rate.

<a id="long251:sec:xr-corrections"></a>

## Corrections to earlier records

<a id="the-earlier-tail-bound-calculation."></a>

#### The earlier tail-bound calculation.

The $`4096`$-bit program linked through Section <a href="#long251:sec:measurements" data-reference-type="ref" data-reference="long251:sec:measurements">9</a> bounds $`T_s`$ by summing the first $`400`$ terms of $`1250(s+j+2)^4 2^{-j}`$ after rounding each down, then adding $`1`$. This does not necessarily bound that polynomial series: at the recorded $`s=1\,270\,306`$, the returned value is $`40`$ below the exact sum $`1250P(s+2)`$, with $`P`$ as in Proposition <a href="#long251:res:explicit-remainder" data-reference-type="ref" data-reference="long251:res:explicit-remainder">17</a>.

The returned bound nevertheless has a valid justification. The stronger estimate $`p_n\le2(n+5)^4`$ proved in Appendix <a href="#long251:app:prime-bound" data-reference-type="ref" data-reference="long251:app:prime-bound">11</a> gives
``` math
T_s\le2P(s+6)<625(s+3)^4\qquad(s\ge0).
```
The last expression is already the first summand of the program, and all its remaining summands are nonnegative. The strict inequality follows from
``` math
625(s+3)^4-2P(s+6)
 =623s^4+7436s^3+32958s^2+62972s+40437>0.
```
Thus the rounding issue is in the stated majorant argument, not a failure of the returned enclosure. This argument justifies the analytic bound; it is not a rerun of the denominator-exclusion search.

<a id="two-different-improvements-to-the-exclusion-record."></a>

#### Two different improvements to the exclusion record.

An earlier internal record gave a denominator exclusion at $`10^{602}`$. The kernel-decided floor $`2^{589}>10^{177}`$ of Theorem <a href="#long251:res:denominatorfloor" data-reference-type="ref" data-reference="long251:res:denominatorfloor">20</a> is numerically smaller but has a different verification status. It does not supersede $`10^{602}`$ in numerical strength. The continued-fraction exclusion $`2^{39997}>10^{12040}`$ of Theorem <a href="#long251:res:cfexclusion" data-reference-type="ref" data-reference="long251:res:cfexclusion">21</a> is the larger numerical bound. The bound has $`12041`$ decimal digits; the corresponding strict power-of-ten lower bound is $`10^{12040}`$, not $`10^{12041}`$. The earlier manuscript reports a separate interval and Farey-neighbour replay. Independently of that report, this edition regenerates an $`80000`$-bit enclosure and its Farey certificate, as described in Theorem <a href="#long251:res:cfexclusion" data-reference-type="ref" data-reference="long251:res:cfexclusion">21</a>. The original program was not executed, and the new verification is not a Lean check.

<a id="an-insufficient-proposed-condition."></a>

#### An insufficient proposed condition.

An earlier record named Hardy-Littlewood $`k`$-tuple correlation of consecutive gaps at a fixed offset as the missing input. With the offset freed by Theorem <a href="#long251:res:freepair" data-reference-type="ref" data-reference="long251:res:freepair">11</a> the route needs, for each modulus $`t`$, cofinally many congruent pairs with certified nonintegral tail difference. A further record proposed that two even values differing by $`2`$, each occurring infinitely often inside a common index residue class, would supply the two-condition form. Theorem <a href="#long251:res:polignacfail" data-reference-type="ref" data-reference="long251:res:polignacfail">29</a> shows that this implication is false for integer-coefficient recurrences. That entry is withdrawn.

<a id="the-formal-boundary."></a>

#### The formal boundary.

An earlier reading of the short note placed the relation between rational and real tails and the real small-pair implication among the results supported only by ordinary proofs. The supplied record instead identifies formal proofs at [line 48](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L48) and [line 99](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L99) of the real prime-gap tail module. A second reading placed the kernel-decided denominator floor and the criterion using congruent indices outside the source revision the note pins. Both modules are present at that revision, and both are linked from the note.

<a id="long251:app:affine-detail"></a>

# Arithmetic-progression reformulations of integrality

One can ask whether an iterated tail difference lies in an arithmetic progression determined by the intervening coefficients. The next theorem shows exactly what this asks of the original tail difference. Under the stated growth bound, a second test using the fixed progression $`2^r\mathbb{Z}`$ also reduces to the same nonintegrality condition.

Here $`D_N=\sigma_h(N)`$ and $`\delta_N=g_{N+h+1}-g_{N+1}`$, with $`h`$ fixed. For a longer block, set
``` math
B_{h,N,r}=\sum_{i=0}^{r-1}2^{r-1-i}\delta_{N+i};
 \qquad D_{N+r}=2^rD_N-B_{h,N,r}.
```
The progression $`-B_{h,N,r}+2^{r+1}\mathbb{Z}`$ depends on the very coefficients used to compute $`D_{N+r}`$. Substituting the displayed recurrence will cancel that dependence; no new information is obtained by increasing $`r`$.

<div id="long251:res:affinecollapse" class="theorem">

**Theorem 40** (equivalent arithmetic-progression tests). *For every rational dyadic tail recurrence and all $`h,N,r\ge0`$,
``` math
\begin{equation}
 D_{N+r}\in-B_{h,N,r}+2^{r+1}\mathbb{Z}\quad\Longleftrightarrow\quad D_N\in2\mathbb{Z}.
\label{eq:affinecollapse}\ltx@label{long251:eq:affinecollapse}
\end{equation}
```
Consequently, if every $`\delta_N`$ is even, then
``` math
\begin{equation}
 \begin{split}
 &\bigl(\forall N_0\ \exists N,r:\ N_0<N\text{ and }
 D_{N+r}\notin-B_{h,N,r}+2^{r+1}\mathbb{Z}\bigr)\\
 &\hspace{12mm}\Longleftrightarrow\quad
 D_N\notin\mathbb{Z}\text{ for arbitrarily large }N.
 \end{split}
\label{eq:affinecofinal}\ltx@label{long251:eq:affinecofinal}
\end{equation}
```*

*There is a second equivalence. Let $`b:\mathbb{N}\to\mathbb{Q}`$ satisfy $`|D_N|\le b(N)`$ for every $`N`$, and suppose that for every $`N`$ and every positive integer $`q`$ there is an $`r`$ with
``` math
\begin{equation}
 2b(N+r)q<2^r.
\label{eq:dyadicscale}\ltx@label{long251:eq:dyadicscale}
\end{equation}
```
Then
``` math
\begin{equation}
 \begin{split}
 &\forall N_0\ \exists N,r:\ N_0<N\text{ and }
   \forall z\in\mathbb{Z},\quad
   b(N+r)<|B_{h,N,r}-2^rz|\\
 &\hspace{35mm}\Longleftrightarrow\quad
 D_N\notin\mathbb{Z}\text{ for arbitrarily large }N.
 \end{split}
\label{eq:fixedcollapse}\ltx@label{long251:eq:fixedcollapse}
\end{equation}
```*

</div>

Lean: [affine circularity bundle](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L241).

<div class="proof">

*Proof.* Substituting $`D_{N+r}=2^rD_N-B_{h,N,r}`$ into the first membership condition cancels the observed block from both sides and leaves $`D_N=2z`$. This proves <a href="#eq:affinecollapse" data-reference-type="eqref" data-reference="eq:affinecollapse">[eq:affinecollapse]</a>. When every $`\delta_N`$ is even, the recurrence also gives $`D_{N+1}\in2\mathbb{Z}`$ if and only if $`D_N\in\mathbb{Z}`$. Thus eventual integrality would force eventual even integrality and contradict the left side of <a href="#eq:affinecofinal" data-reference-type="eqref" data-reference="eq:affinecofinal">[eq:affinecofinal]</a>. This proves the forward implication. Conversely, given a cutoff, choose a nonintegral $`D_N`$ beyond it and take $`r=0`$ in <a href="#eq:affinecollapse" data-reference-type="eqref" data-reference="eq:affinecollapse">[eq:affinecollapse]</a>.

For <a href="#eq:fixedcollapse" data-reference-type="eqref" data-reference="eq:fixedcollapse">[eq:fixedcollapse]</a>, eventual integrality and the block identity give some $`z\in\mathbb{Z}`$ with
``` math
B_{h,N,r}-2^rz=-D_{N+r},
```
so the displayed strict separation contradicts $`|D_{N+r}|\le b(N+r)`$. Conversely, if $`D_N`$ is nonintegral, choose a positive integer $`q`$ with $`1/q\le\operatorname{dist}(D_N,\mathbb{Z})`$. Such a $`q`$ exists because $`\mathbb{Z}`$ is closed and $`D_N\notin\mathbb{Z}`$. Choose $`r`$ from <a href="#eq:dyadicscale" data-reference-type="eqref" data-reference="eq:dyadicscale">[eq:dyadicscale]</a>. The block identity and the triangle inequality give, for every $`z\in\mathbb{Z}`$,
``` math
|B_{h,N,r}-2^rz|
 \ge 2^r|D_N-z|-|D_{N+r}|
 \ge \frac{2^r}{q}-b(N+r)>b(N+r).
```
The same $`r`$ works for all integers $`z`$, as required. ◻

</div>

The three displayed equivalences are assembled in one declaration, [the three arithmetic-progression equivalences](https://github.com/wcook04/plectis-erdos/blob/3d6d938d696fed0fb71dd55115a18a73738ff223/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L241).

Evenness is essential in <a href="#eq:affinecofinal" data-reference-type="eqref" data-reference="eq:affinecofinal">[eq:affinecofinal]</a>. Without it, the recurrence $`T_N=N+1`$, $`g_n=n-1`$ for $`n\ge1`$, has $`D_N=\sigma_1(N)=1`$ and $`\delta_N=1`$ at every index. Thus $`D_N`$ is never an even integer but is always an integer. By <a href="#eq:affinecollapse" data-reference-type="eqref" data-reference="eq:affinecollapse">[eq:affinecollapse]</a>, the left side of <a href="#eq:affinecofinal" data-reference-type="eqref" data-reference="eq:affinecofinal">[eq:affinecofinal]</a> holds while the right side fails.

The growth hypothesis <a href="#eq:dyadicscale" data-reference-type="eqref" data-reference="eq:dyadicscale">[eq:dyadicscale]</a> is equivalent to
``` math
\liminf_{n\to\infty}2^{-n}b(n)=0.
```
Indeed, writing $`n=N+r`$, its inequality becomes $`2^{-n}b(n)<1/(2^{N+1}q)`$. Since $`b(n)\ge0`$, finding such an $`n\ge N`$ for every $`N`$ and every positive integer $`q`$ is exactly the stated liminf condition. In particular it holds for polynomial bounds and for $`Cc^n`$ with fixed $`C>0`$ and $`1<c<2`$, but fails for $`b(n)=2^n`$. A limit of zero is not necessary: the bound $`b(n)=1`$ at odd indices and $`b(n)=2^n`$ at even indices also satisfies the hypothesis. This example concerns the growth condition alone, not a bound for the prime tails. Only one suitable scale is needed to magnify the positive distance to $`\mathbb{Z}`$ beyond the error; no comparison at every sufficiently large scale is required.

The proof in fact uses no rationality of $`D_N`$: the integer $`q`$ is chosen from its positive distance to $`\mathbb{Z}`$, not from a reduced denominator. Thus <a href="#eq:fixedcollapse" data-reference-type="eqref" data-reference="eq:fixedcollapse">[eq:fixedcollapse]</a> holds for real integer-coefficient recurrences under the same bound and growth hypothesis. The same is true of <a href="#eq:affinecollapse" data-reference-type="eqref" data-reference="eq:affinecollapse">[eq:affinecollapse]</a>, and of <a href="#eq:affinecofinal" data-reference-type="eqref" data-reference="eq:affinecofinal">[eq:affinecofinal]</a> when the coefficient differences are even. These extensions follow from the printed argument; the cited formal statement is the rational one.

The first test is exactly even integrality of $`D_N`$, regardless of $`r`$. The fixed-progression test compares $`2^r\operatorname{dist}(D_N,\mathbb{Z})`$ with the bound on the remaining tail. When $`D_N`$ is nonintegral, the growth hypothesis makes the former larger than twice the latter at a suitable scale. Rewriting the test does not provide an estimate about the distribution of consecutive primes.

<a id="sec:erdos-251-complete-family-map"></a>

# Conclusions

The sparse construction attains every value in an interval while preserving the specified gap statistics and every fixed congruence eventually. Both rational and irrational values occur, so these properties do not determine rationality. The other counterexamples isolate further insufficient conditions. All these constructions alter integer sequences; they do not construct consecutive primes.

The exact tail criteria characterise rationality but do not produce actual-prime witnesses. One sufficient route to irrationality would establish the simultaneous small-difference conditions arbitrarily late for every positive shift. The finite certificates and denominator exclusions do not establish that conclusion.

<div class="thebibliography">

99

Paul Erdős, [*Sur certaines séries à valeur irrationnelle*](https://users.renyi.hu/~p_erdos/1958-19.pdf). L’Enseignement Mathématique **4** (1958), 93–100, doi:[10.5169/seals-34629](https://doi.org/10.5169/seals-34629). Paul Erdős and Ronald L. Graham, [*Old and New Problems and Results in Combinatorial Number Theory*](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf). Monographies de L’Enseignement Mathématique, L’Enseignement Mathématique, 1980. Paul Erdős and Carl Pomerance, [*On the largest prime factors of $`n`$ and $`n+1`$*](https://doi.org/10.1007/BF01818569). Aequationes Mathematicae **17** (1978), 311–321, doi:[10.1007/BF01818569](https://doi.org/10.1007/BF01818569). Paul Erdős, [*On the irrationality of certain series: problems and results*](https://doi.org/10.1017/CBO9780511897184.009). New Advances in Transcendence Theory, Cambridge University Press, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). Paul Erdős, [*Beweis eines Satzes von Tschebyschef*](https://users.renyi.hu/~p_erdos/1932-01.pdf). Acta Litterarum ac Scientiarum Szeged **5** (1932), 194–198. Paul Erdős and Ernst G. Straus, *On the irrationality of certain Ahmes series*. Journal of the Indian Mathematical Society (N.S.) **27** (1964), 129–133. MR0175848. Paul Erdős and Ernst G. Straus, [*On the irrationality of certain series*](https://doi.org/10.2140/pjm.1974.55.85). Pacific Journal of Mathematics **55** (1974), no. 1, 85–92, doi:[10.2140/pjm.1974.55.85](https://doi.org/10.2140/pjm.1974.55.85). Kevin Ford, Ben Green, Sergei Konyagin, James Maynard and Terence Tao, [*Long gaps between primes*](https://arxiv.org/abs/1412.5029v3). Journal of the American Mathematical Society **31** (2018), 65–105, doi:[10.1090/jams/876](https://doi.org/10.1090/jams/876); arXiv:[1412.5029v3](https://arxiv.org/abs/1412.5029v3). John A. Fridy, [*Generalized bases for the real numbers*](https://www.fq.math.ca/Scanned/4-3/fridy.pdf). The Fibonacci Quarterly **4** (1966), no. 3, 193–201. A. Ya. Khinchin, *Continued Fractions*. University of Chicago Press, 1964. Vjekoslav Kovač and Terence Tao, [*On several irrationality problems for Ahmes series*](https://arxiv.org/abs/2406.17593v4). Acta Mathematica Hungarica **175** (2025), 572–608, doi:[10.1007/s10474-025-01528-0](https://doi.org/10.1007/s10474-025-01528-0); arXiv:[2406.17593v4](https://arxiv.org/abs/2406.17593v4). Statement and section numbers refer to arXiv version 4. Vivian Kuperberg, [*Sums of singular series with large sets and the tail of the distribution of primes*](https://arxiv.org/abs/2210.09775v2). The Quarterly Journal of Mathematics **74** (2023), no. 4, 1457–1479, doi:[10.1093/qmath/haad030](https://doi.org/10.1093/qmath/haad030); arXiv:[2210.09775v2](https://arxiv.org/abs/2210.09775v2). Statement numbers refer to arXiv version 2, 15 June 2023. Johan Land, [*A conditional proof of the irrationality of $`\sum_{n\ge1}p_n2^{-n}`$ under a uniform Hardy–Littlewood prime-tuples conjecture*](https://github.com/beetree/math_erdos_251). Research draft, 5 September 2026. Formalisation material accompanies the draft. Leonardo de Moura and Sebastian Ullrich, [*The Lean 4 theorem prover and programming language*](https://doi.org/10.1007/978-3-030-79876-5_37). Automated Deduction – CADE 28, Lecture Notes in Computer Science, Springer, 2021, pp. 625–635, doi:[10.1007/978-3-030-79876-5_37](https://doi.org/10.1007/978-3-030-79876-5_37). The mathlib Community, [*The Lean mathematical library*](https://doi.org/10.1145/3372885.3373824). Proceedings of the 9th ACM SIGPLAN International Conference on Certified Programs and Proofs, ACM, 2020, pp. 367–381, doi:[10.1145/3372885.3373824](https://doi.org/10.1145/3372885.3373824). Describes a Lean 3-era snapshot; the repository lock identifies the library used by the present Lean 4 sources. James Maynard, [*Small gaps between primes*](https://doi.org/10.4007/annals.2015.181.1.7). Annals of Mathematics **181** (2015), 383–413, doi:[10.4007/annals.2015.181.1.7](https://doi.org/10.4007/annals.2015.181.1.7). Hugh L. Montgomery and Robert C. Vaughan, [*Multiplicative Number Theory I: Classical Theory*](https://doi.org/10.1017/CBO9780511618314). Cambridge Studies in Advanced Mathematics, Cambridge University Press, 2007, doi:[10.1017/CBO9780511618314](https://doi.org/10.1017/CBO9780511618314). Jan-Christoph Schlage-Puchta, [*The irrationality of some number theoretical series*](https://arxiv.org/abs/1105.1451v1). Acta Arithmetica **126** (2007), no. 4, 295–303, doi:[10.4064/aa126-4-1](https://doi.org/10.4064/aa126-4-1); arXiv:[1105.1451v1](https://arxiv.org/abs/1105.1451v1). Published in 2007; arXiv upload is from 2011. Lemma and preprint page locators refer to arXiv version 1. Ian Short, [*Ford Circles, Continued Fractions, and Rational Approximation*](https://arxiv.org/abs/0912.1997v1). The American Mathematical Monthly **118** (2011), no. 2, 130–135, doi:[10.4169/amer.math.monthly.118.02.130](https://doi.org/10.4169/amer.math.monthly.118.02.130); arXiv:[0912.1997v1](https://arxiv.org/abs/0912.1997v1). Preprint title: Ford circles, continued fractions, and best approximation of the second kind. Preprint theorem locators refer to arXiv version 1. Wouter van Doorn and Vjekoslav Kovač, [*Lacunary sequences whose reciprocal sums represent all rational numbers in an interval*](https://arxiv.org/abs/2509.24971v3). Acta Arithmetica **223** (2026), 275–295, doi:[10.4064/aa251001-13-1](https://doi.org/10.4064/aa251001-13-1); arXiv:[2509.24971v3](https://arxiv.org/abs/2509.24971v3). Statement numbers refer to arXiv version 3. Yitang Zhang, [*Bounded gaps between primes*](https://doi.org/10.4007/annals.2014.179.3.7). Annals of Mathematics **179** (2014), 1121–1174, doi:[10.4007/annals.2014.179.3.7](https://doi.org/10.4007/annals.2014.179.3.7). Thomas F. Bloom, [*Erdős Problem \#251*](https://www.erdosproblems.com/251). 2026. Catalogue snapshot accessed 6 September 2026. Erdős Problems contributors, [*Erdős Problem \#251 discussion thread*](https://www.erdosproblems.com/forum/thread/251). 2026. Snapshot accessed 6 September 2026: Tao comment of 7 October 2025 and Land comments of 6 September 2026. ChatGPT 5.4 Pro (orchestrated by Vjeko Kovač), [*On the Erdős problem \#251*](https://web.math.pmf.unizg.hr/~vjekovac/files/Erdos_problem_251.pdf). Unpublished note, Department of Mathematics, University of Zagreb, 2026. Accessed 6 September 2026. The Formal Conjectures Authors, [*FormalConjectures.ErdosProblems.251*](https://github.com/google-deepmind/formal-conjectures/blob/f776d2f2039351b00737ffcafb9d7d7666e1d9af/FormalConjectures/ErdosProblems/251.lean). 2025. Pinned statement source, not a proof of Problem 251; accessed 28 July 2026. Stefan Ringer, [*Local gap statistics, telescoping, and normality: a local-pattern approach to Erdős problem 251*](https://github.com/StefanRinger/erdos-251). Preprint, 11 September 2026. Mutable main-branch TeX consulted 16 September 2026; the cited conditional statements were rechecked 18 September 2026. Formalisation material accompanies the draft. Tonći Crmarić and Vjekoslav Kovač, [*On the irrationality of certain super-polynomially decaying series*](https://arxiv.org/abs/2504.18712v1). Colloquium Mathematicum **179** (2025), 55–68, doi:[10.4064/cm9628-5-2025](https://doi.org/10.4064/cm9628-5-2025); arXiv:[2504.18712v1](https://arxiv.org/abs/2504.18712v1). Lemma 4 is cited using arXiv version 1. Boris Adamczewski, Michael Drmota and Clemens Müllner, [*(Logarithmic) densities for automatic sequences along primes and squares*](https://arxiv.org/abs/2009.14773v2). Transactions of the American Mathematical Society **375** (2022), no. 1, 455–499, doi:[10.1090/tran/8476](https://doi.org/10.1090/tran/8476); arXiv:[2009.14773v2](https://arxiv.org/abs/2009.14773v2). Theorems 1.2 and 1.4 refer to arXiv version 2, 13 April 2021; journal publication is 2022. Wouter van Doorn, [*Partitions with prescribed sum of reciprocals: asymptotic bounds*](https://arxiv.org/abs/2502.02200v2). 2025; arXiv:[2502.02200v2](https://arxiv.org/abs/2502.02200v2). Version 2, 23 July 2025. Szymon Głąb and Franciszek Prus-Wiśniowski, [*Achievement sets – current results and open problems*](https://arxiv.org/abs/2512.17285v1). Real Analysis Exchange (2026), doi:[10.14321/realanalexch.1766383782](https://doi.org/10.14321/realanalexch.1766383782); arXiv:[2512.17285v1](https://arxiv.org/abs/2512.17285v1). Advance publication, first available in Project Euclid 8 June 2026. Consulted text remains arXiv:2512.17285v1 (19 December 2025). Franciszek Prus-Wiśniowski and Jolanta Ptak, [*Achievable Cantorvals almost without reversed Kakeya conditions*](https://arxiv.org/abs/2412.08768v1). 2024; arXiv:[2412.08768v1](https://arxiv.org/abs/2412.08768v1). Version 1 submitted 11 December 2024. The sparse indices satisfy the overlap inequality, not its strict term-dominating reverse. Artur Bartoszewicz, Małgorzata Filipczak and Emilia Szymonik, [*Multigeometric sequences and Cantorvals*](https://arxiv.org/abs/1304.4218v2). Central European Journal of Mathematics **12** (2014), no. 7, 1000–1007, doi:[10.2478/s11533-013-0396-4](https://doi.org/10.2478/s11533-013-0396-4); arXiv:[1304.4218v2](https://arxiv.org/abs/1304.4218v2). Vivian Kuperberg, [*Sums of singular series along arithmetic progressions and with smooth weights*](https://arxiv.org/abs/2301.06095v1). International Journal of Number Theory **21** (2025), no. 1, 53–74, doi:[10.1142/S1793042125500046](https://doi.org/10.1142/S1793042125500046); arXiv:[2301.06095v1](https://arxiv.org/abs/2301.06095v1). Preprint uploaded 15 January 2023; journal publication is 2025. Abhishek Jha, [*The Poisson Tail Conjecture for primes in short intervals*](https://arxiv.org/abs/2605.23014v2). 2026; arXiv:[2605.23014v2](https://arxiv.org/abs/2605.23014v2). Substantially revised version 2, 12 September 2026, 31 pages. Conditional statements must retain their strong Hardy–Littlewood hypotheses. D. H. J. Polymath, [*Variants of the Selberg sieve, and bounded intervals containing many primes*](https://arxiv.org/abs/1407.4897v4). Research in the Mathematical Sciences **1** (2014), article 12, doi:[10.1186/s40687-014-0012-7](https://doi.org/10.1186/s40687-014-0012-7); arXiv:[1407.4897v4](https://arxiv.org/abs/1407.4897v4). Theorem 1.4(i) refers to arXiv version 4 (22 December 2014); the journal numbers it Theorem 4(i). An erratum is recorded at doi:10.1186/s40687-015-0033-x. Zbigniew Nitecki, [*Cantorvals and Subsum Sets of Null Sequences*](https://arxiv.org/abs/1106.3779v2). The American Mathematical Monthly **122** (2015), no. 9, 862–870, doi:[10.4169/amer.math.monthly.122.9.862](https://doi.org/10.4169/amer.math.monthly.122.9.862); arXiv:[1106.3779v2](https://arxiv.org/abs/1106.3779v2). Consulted preprint: Subsum Sets: Intervals, Cantor Sets, and Cantorvals, version 2 (8 July 2013). Theorem 14 is attributed there to Guthrie–Nymann; its locator is not journal pagination. Piotr Miska, Franciszek Prus-Wiśniowski and Jolanta Ptak, [*More on Kakeya Conditions for Achievement Sets*](https://ruj.uj.edu.pl/server/api/core/bitstreams/d6630f7b-e6ee-4de8-8a1b-81c7b4c59d2e/content). Results in Mathematics **78** (2023), article 113, doi:[10.1007/s00025-023-01890-x](https://doi.org/10.1007/s00025-023-01890-x). Repairs an estimate in the 2021 proof, preserving its uniqueness conclusion, and gives a simpler proof of a weaker theorem without that conclusion. Jacek Marchwicki and Piotr Miska, [*On Kakeya Conditions for Achievement Sets*](https://link.springer.com/article/10.1007/s00025-021-01479-2). Results in Mathematics **76** (2021), article 181, doi:[10.1007/s00025-021-01479-2](https://doi.org/10.1007/s00025-021-01479-2). Theorem 2.1 is to be read with the proof repair in Miska–Prus-Wiśniowski–Ptak (2023). Piotr Nowakowski, [*On a new condition implying that an achievement set is a Cantorval and its applications*](https://arxiv.org/abs/2512.17761v1). 2025; arXiv:[2512.17761v1](https://arxiv.org/abs/2512.17761v1). Version 1, 19 December 2025. Theorem 3.1 requires the Star Procedure of Definition 2 never to break; no application to the present factorial weights is asserted.

</div>
