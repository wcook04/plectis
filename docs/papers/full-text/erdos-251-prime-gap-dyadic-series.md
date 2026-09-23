<a id="erdos-251-prime-gap-dyadic-series"></a>

# Sparse Congruence-Preserving Perturbations of Dyadic Series

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

We construct sparse nonnegative integer corrections that rationalise a convergent dyadic series with nonnegative integer coefficients. Given a finite prefix to retain and any allowance $`f(n)\to\infty`$, one permitted index set of upper Banach density zero supports corrections attaining every real target in a nondegenerate interval above the original sum. The corrections are eventually bounded by $`f`$; each fixed modulus divides both the corrections and their cumulative sums beyond a cutoff independent of the target. The construction varies adjacent corrections with fixed ordinary total, while a preceding correction fixes the cumulative residue. For $`f(n)=(\log(n+3))^\varepsilon`$ with $`\varepsilon>0`$, the empirical distributions of original and corrected unnormalised blocks, sampled at integer starts in $`[X,2X)`$, have total variation distance tending to zero for lengths $`o(\log\log X)`$. Applied to prime gaps, it gives rational dyadic sums while the cumulative positions remain asymptotic to $`n\log n`$. Thus these congruences and block statistics alone cannot establish irrationality. The construction does not assert that the cumulative positions are prime.

<a id="sec:problem"></a>

# Introduction

Erdős Problem #251 asks whether the sum of the primes weighted by successive powers of $`1/2`$ is irrational. Proposition <a href="#res:sparserationalisation" data-reference-type="ref" data-reference="res:sparserationalisation">1</a> constructs an interval of dyadic sums while preserving the specified congruences and block statistics; Corollary <a href="#res:jointcountermodel" data-reference-type="ref" data-reference="res:jointcountermodel">2</a> applies it to prime gaps. The interval contains both rational and irrational targets, so these properties do not determine rationality.

Finite integer changes add a dyadic rational and cannot change rationality. The construction therefore uses infinitely many corrections, separating their ordinary sum from their dyadic sum. At adjacent coordinates $`n,n+1`$, the pairs $`(0,6),(2,4),(4,2),(6,0)`$ all have ordinary sum $`6`$, but their dyadic contributions are $`6,8,10,12`$ divided by $`2^{n+2}`$. A third correction at $`n-1`$ fixes the residue of the cumulative sum. Placing these triples farther apart leaves almost every fixed-length block unchanged. The choices within the triples then fill an interval of dyadic sums without changing the permitted indices or the congruence cutoffs.

<a id="density-and-block-conventions."></a>

#### Density and block conventions.

Here $`\mathbb{N}=\{0,1,\ldots\}`$, all intervals of indices contain integers, and $`\log`$ is natural unless a base is displayed. Upper Banach density zero means
``` math
\lim_{H\to\infty}\sup_{u\in\mathbb{N}}\frac{|S\cap[u,u+H)|}{H}=0.
```
For integers $`X\ge1`$ and $`m\ge1`$, let $`\mu_{a,X,m}`$ be the empirical probability measure obtained by choosing an integer $`n\in[X,2X)`$ uniformly and observing $`(a_n,\ldots,a_{n+m-1})`$. Equal blocks are counted with multiplicity. We use $`d_{\rm TV}(\mu,\nu)=\sup_B|\mu(B)-\nu(B)|`$. For the same function of the block, bounded in absolute value by $`B_0`$, its means under the two measures differ by at most $`2B_0d_{\rm TV}(\mu,\nu)`$. No rescaling of the coefficients is implicit. For a correction sequence $`e`$, its support is $`\{n:e_n\ne0\}`$. It may depend on the target and be a proper subset of the common permitted set $`S`$.

<div id="res:sparserationalisation" class="proposition">

**Proposition 1** (sparse changes preserving congruences). *Let $`a:\mathbb{N}\to\mathbb{N}`$ satisfy $`A=\sum_{n\ge0}a_n2^{-(n+1)}<\infty`$, let $`K\in\mathbb{N}`$, and let $`f:\mathbb{N}\to\mathbb{R}`$ tend to $`+\infty`$. There exist a set $`S\subseteq[K,\infty)`$ of upper Banach density zero and a nondegenerate interval $`I\subset(A,\infty)`$ such that, for every $`r\in I`$, there is an integer correction $`e:\mathbb{N}\to\mathbb{N}`$ satisfying
``` math
\operatorname{supp}e\subseteq S,\qquad e_n\le f(n)\ \text{eventually},
 \qquad \sum_{n\ge0}(a_n+e_n)2^{-(n+1)}=r.
```
For each integer $`q\ge1`$ there is a cutoff $`N_q`$, independent of $`r`$, such that $`q\mid e_n`$ and $`q\mid\sum_{i<n}e_i`$ for all $`n\ge N_q`$. For every $`\varepsilon>0`$, the choice $`f(n)=(\log(n+3))^\varepsilon`$ can be made with
``` math
|S\cap[X,2X)|=O_\varepsilon\!\left(\frac{X}{\log\log X}\right),
 \qquad
 d_{\rm TV}(\mu_{a,X,m},\mu_{a+e,X,m})
 \le\frac{m|S\cap[X,2X+m)|}{X}.
```
In particular the distance tends to zero for every integer-valued $`m=m(X)\ge1`$ with $`m(X)=o(\log\log X)`$, uniformly over target values.*

</div>

Lean: [arbitrary word sparse rationalisation uniform](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/SparseAmbientR9.lean#L269), [polylogarithmic word interval uniform](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/SparsePaperR11.lean#L137).

The convergence hypothesis includes all nonnegative integer sequences of polynomial growth, but excludes $`a_n=2^n`$. The allowance $`f(n)\to\infty`$ may grow as slowly as $`\log\log(n+3)`$; it cannot be replaced by a constant. Indeed, eventual divisibility by a modulus larger than the bound forces the corrections eventually to vanish. Their cumulative sum then becomes constant; divisibility by every modulus forces that constant to be zero. Nonnegativity makes every correction zero. Upper Banach density zero also rules out arbitrarily long intervals filled by permitted correction indices, even when their ordinary density is zero.

<div class="proof">

*Construction.* We first preserve the congruences, then choose the spacings and sizes, and finally show that the attainable sums fill an interval. Choose an initial index $`n_{-1}\ge K`$. For $`j=0,1,\ldots`$, use disjoint triples $`n_j-1,n_j,n_j+1`$, with spacings $`s_j=n_j-n_{j-1}\ge4`$ and positive moduli satisfying $`M_j\mid M_{j+1}`$. Put $`D_j=2^{s_j}-1`$. This choice compensates for the factor $`2^{s_j}`$ lost by moving to the next triple; the resulting weighted ranges will telescope. Let $`C_j`$ be the cumulative correction before the triple, namely $`\sum_{i<n_j-1}e_i`$. Starting from $`C_0=0`$, define
``` math
c_j=(-C_j)\bmod M_j\quad(0\le c_j<M_j),\qquad
 C_{j+1}=C_j+c_j+M_jD_j.
```
For each choice $`d_j\in\{0,\ldots,D_j\}`$, assign the corrections:
``` math
e_{n_j-1}=c_j,\qquad e_{n_j}=M_jd_j,\qquad
 e_{n_j+1}=M_j(D_j-d_j),
```
and set $`e_n=0`$ elsewhere. The complete triple has total $`c_j+M_jD_j`$, independent of $`d_j`$, so $`c_j`$ is independent of all the choices $`d_i`$. Immediately after adding $`c_j`$, the cumulative correction is divisible by $`M_j`$; both pair entries preserve that divisibility. If $`q`$ divides both $`C_j`$ and $`M_j`$, it also divides $`c_j`$, since $`M_j\mid C_j+c_j`$. Induction therefore preserves each previously imposed divisor. Thus each fixed modulus eventually divides both individual and cumulative corrections if it eventually divides $`M_j`$. More precisely, if $`q\mid M_J`$, every index $`n\ge n_J`$ has both divisibilities. The first residue correction at $`n_J-1`$ need not itself be divisible by $`q`$; it is deliberately before this cutoff. The cutoff depends only on the schedule and $`q`$, not on the target.

The moduli must eventually contain every divisor, while the spacings must tend to infinity. We can make both grow slowly enough to respect $`f`$. To handle a nonmonotone $`f`$, set
``` math
h(n)=\inf_{m\ge n}\min(f(m),m),
```
take the initial $`n_{-1}`$ so large that $`h(n_{-1})\ge32`$, and recursively let
``` math
k_j=\max\{k\ge2:k!2^{k+2}\le h(n_{j-1})\},\quad
 M_j=k_j!,\quad s_j=k_j+2,\quad n_j=n_{j-1}+s_j.
```
The threshold $`32=2!2^4`$ makes $`k=2`$ admissible, and factorial growth makes the maximum finite. The function $`h`$ is nondecreasing, tends to infinity, and satisfies $`h(n)\le n`$. The infimum ensures that a choice made at $`n_{j-1}`$ respects $`f`$ at every later coordinate, even if $`f`$ subsequently decreases. Hence $`k_j`$ is nondecreasing and tends to infinity. Each triple entry is at most $`M_j2^{s_j}\le h(n_{j-1})`$, which is at most $`f(n)`$ at every coordinate of that triple and at most $`n_{j-1}`$. This proves the size bound and summability of the correction. To see uniform sparsity, fix $`R`$. Beyond finitely many triples, centres are separated by at least $`R`$. An interval of length $`H`$ therefore meets at most $`3(H/R+2)`$ permitted correction indices, plus a fixed finite number. Divide by $`H`$, take the supremum over translates, let $`H\to\infty`$, and then let $`R\to\infty`$.

It remains to show that these choices attain every point of an interval, not merely a dense set. Increasing $`d_j`$ by one changes the dyadic sum by $`w_j=M_j2^{-n_j-2}`$. The complete weighted correction is
``` math
\sum_n\frac{e_n}{2^{n+1}}=\beta+\sum_jd_jw_j,
 \qquad \beta=\sum_j\bigl(c_j2^{-n_j}+D_jw_j\bigr).
```
The sum defining $`\beta`$ includes the preceding corrections $`c_j`$; it is fixed and positive. For $`i>j`$, monotonicity of the moduli gives $`D_iw_i\ge M_j(2^{-n_{i-1}-2}-2^{-n_i-2})`$. Hence, for $`J>j`$,
``` math
\sum_{i=j+1}^{J}D_iw_i
 \ge M_j\bigl(2^{-n_j-2}-2^{-n_J-2}\bigr).
```
Letting $`J\to\infty`$ gives $`\sum_{i>j}D_iw_i\ge w_j`$. At stage $`j`$, the allowed contributions $`0,w_j,\ldots,D_jw_j`$ are $`w_j`$ apart. The intervals
``` math
\left[d w_j,\ d w_j+\sum_{i>j}D_iw_i\right],\qquad 0\le d\le D_j,
```
therefore cover $`[0,\sum_{i\ge j}D_iw_i]`$. Given a target remainder in this interval, choose $`d_j`$ so that subtracting $`d_jw_j`$ leaves a remainder between zero and $`\sum_{i>j}D_iw_i`$. Repeating this choice represents the target exactly, since the remaining capacity tends to zero. This is Crmarić and Kovač’s covering lemma \[crmarickovac2025, Lemma 4\] applied to the finite sets of choices; it gives all of $`[0,\sum_jD_jw_j]`$. This is a finite-choice version of Fridy’s generalised-base argument \[fridy1966, Lemma, p. 194\], without his monotonicity assumption on the weights. Kovač–Tao use analogous sets of reciprocal choices \[kovactao2024, Lemma 5.1\]. Take $`I=(A+\beta,A+\beta+\sum_jD_jw_j)`$.

For the polylogarithmic bound, we bound the factorial modulus by a small power of $`\log n`$, leaving room for the larger range $`2^{s_j}`$ of choices. Specifically, after a sufficiently large initial cutoff, set
``` math
s_j=\left\lfloor\frac{\varepsilon}{2}\log_2\log(n_{j-1}+3)\right\rfloor,
 \qquad
 k_j=\max\{k\ge2:k!\le(\log(n_{j-1}+3))^{\varepsilon/4}\},
```
with $`M_j=k_j!`$, $`n_j=n_{j-1}+s_j`$ and the same $`D_j`$ and residue corrections. The exponents $`\varepsilon/4`$ and $`\varepsilon/2`$ add to less than $`\varepsilon`$, so the product stays within the correction allowance. This schedule works for every $`\varepsilon>0`$; no prime-growth assertion is used here. We have $`s_j\ge4`$ and $`M_j2^{s_j}\le(\log(n_{j-1}+3))^{3\varepsilon/4}`$. The preceding congruence, convergence and interval arguments still apply. Spacing comparable to $`\log\log n_j`$ gives $`|S\cap[X,2X)|=O_\varepsilon(X/\log\log X)`$. Couple the original and corrected length-$`m`$ blocks at the same starting index in $`[X,2X)`$. Each changed coordinate belongs to at most $`m`$ such blocks, so at most $`m|S\cap[X,2X+m)|`$ starts meet a correction. For $`m\le X`$, the interval $`[X,2X+m)`$ lies in $`[X,4X)`$, where the support bound applies on two dyadic intervals. The total variation distance is therefore $`O_\varepsilon(m/\log\log X)`$, which tends to zero when $`m=o(\log\log X)`$. ◻

</div>

For tests bounded in absolute value by $`B_0`$ that also depend on the starting index, the same coupling bounds the mean change by $`2B_0m|S\cap[X,2X+m)|/X`$. This is an absolute bound, not a relative estimate for rare events; unchanged finite blocks need not have unchanged complete tails. The companion, Section 2, discusses these distinctions.

To apply the construction, write $`p_0=2,p_1=3,\ldots`$ and $`g_n=p_{n+1}-p_n`$. The central-binomial argument of Erdős \[erdos1932, pp. 194–196\] gives, for $`m\ge4`$,
``` math
4^m<m\binom{2m}{m}\le m(2m)^{\pi(2m)}.
```
The first inequality follows by induction; the second holds because the full power of each prime in the binomial coefficient is at most $`2m`$. For $`m=(n+5)^4`$, the supposition $`\pi(2m)\le n`$ would imply $`4^m<m(2m)^n\le4^m`$: writing $`x=n+5`$, the last inequality follows from $`x\le2^x`$ and $`n+4(n+1)x\le2x^4`$. Hence $`p_n\le2(n+5)^4\le1250(n+1)^4`$, so both dyadic series converge absolutely. The companion, Appendix A, gives the prime-power calculation in full.

<div id="res:jointcountermodel" class="corollary">

**Corollary 2** (a rational sum with the stated prime-gap statistics). *Let $`p_0=2,p_1=3,\ldots`$ be the primes and $`g_n=p_{n+1}-p_n`$. Given $`K\in\mathbb{N}`$ and $`0<\varepsilon\le1`$, there is $`b:\mathbb{N}\to\mathbb{N}`$ with rational dyadic sum such that $`b_n=g_n`$ for $`n<K`$, $`b_n\ge g_n`$, and $`b_n-g_n\le(\log(n+3))^\varepsilon`$ eventually. For every fixed positive modulus, both the coefficients and the cumulative positions eventually retain their corresponding residues. The empirical distributions of unnormalised blocks have total variation distance tending to zero for lengths $`o(\log\log X)`$, and for every fixed nonzero $`F\in\mathbb{Z}[x_0,\ldots,x_k]`$,
``` math
\bigl|\{n<N:F(b_n,\ldots,b_{n+k})=0\}\bigr|=o(N).
```
Moreover, with $`P_n=2+\sum_{i<n}b_i`$,
``` math
0\le P_n-p_n=O_\varepsilon\!\left(
       \frac{n(\log(n+3))^\varepsilon}{\log\log n}\right),
 \qquad P_n\sim n\log n.
```
These positions are not asserted to be prime.*

</div>

Lean: [short joint prime gap countermodel](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR21/JointPrimeGapCountermodel.lean#L431), [cut prefix bound](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR21/JointPrimeGapCountermodel.lean#L228). Conditional on Schlage-Puchta’s density lemma and the prime number theorem; see the [coverage section of the companion record](../mirror/erdos251-prime-gap-reasoning-surface.pdf#nameddest=coverage).

<div class="proof">

*Proof.* Choose a rational target in the interval of Proposition <a href="#res:sparserationalisation" data-reference-type="ref" data-reference="res:sparserationalisation">1</a> and put $`b=g+e`$. Fixed-block nonconcentration for $`g`$ is Schlage-Puchta’s Lemma 4 \[schlagepuchta2011\]. A length-$`(k+1)`$ block changes only at a start in $`\bigcup_{i=0}^{k}(S-i)`$, a density-zero set. Thus the same zero-density conclusion holds for each fixed polynomial at $`b`$, without a bound on its values or on the values of $`e`$. For the cumulative estimate, the indices below $`\sqrt n`$ contribute at most $`O(\sqrt n)`$ support points. On $`[\sqrt n,n)`$, sum the support bound over dyadic intervals; their lengths have sum $`O(n)`$ and $`\log\log X`$ is comparable to $`\log\log n`$. Thus $`|S\cap[0,n)|=O_\varepsilon(n/\log\log n)`$. Multiplication by the eventual pointwise bound on $`e`$, with finitely many initial terms absorbed in the constant, gives the displayed cumulative estimate. The prime number theorem gives $`p_n\sim n\log n`$ \[mv2007, Chapter 6\]; the error is $`o(n\log n)`$ even at $`\varepsilon=1`$. The congruences and growing-block conclusion are those of the proposition. Finally, summing the nonnegative terms in the definition of $`P_n`$ in the opposite order gives
``` math
\sum_{n\ge0}\frac{P_n}{2^{n+1}}
 =2+\sum_{i\ge0}b_i\sum_{n>i}2^{-n-1}
 =2+\sum_{i\ge0}\frac{b_i}{2^{i+1}}\in\mathbb{Q}.
```
Thus the cumulative positions themselves also have a rational dyadic sum, not just their gaps. ◻

</div>

For $`\varepsilon>1`$, using exponent $`1`$ in the corollary gives smaller corrections and the stronger error $`O(n\log(n+3)/\log\log n)`$. Thus all conclusions hold for every $`\varepsilon>0`$, not just the range used in its proof.

For each fixed integer $`y\ge2`$, the congruence modulo $`y!`$ also gives $`\gcd(P_n,y!)=1`$ once $`p_n>y`$ and the congruence holds. The cutoff depends on $`y`$: this does not exclude divisors up to the growing threshold $`\sqrt{P_n}`$. Even prime-valued positions could omit primes, so would not by themselves be the sequence of consecutive primes.

<a id="relation-to-prior-work."></a>

#### Relation to prior work.

The fixed-denominator question is recorded in \[erdos1958, p. 94\], \[erdosgraham1980, p. 62\] and \[erdos1988, p. 103\]. Neither the variable-denominator counterexample in \[kovac2026\] nor the largest-prime-factor coefficient series in \[erdospomerance1978, §7\] decides it.

The covering argument is established: Crmarić–Kovač \[crmarickovac2025, Lemma 4\] treat finite choices; Fridy \[fridy1966\] and Kovač–Tao \[kovactao2024, Lemma 5.1\] give generalised-base and reciprocal-choice precedents. Van Doorn–Kovač combine finite subsum covering with divisibility at distinguished denominators \[vandoornkovac2025, Lemma 7, Proposition 8\]; their conclusion represents rational targets by finite subsums, rather than every real target by infinite choices. Van Doorn’s exchange \[vandoorn2025, proof of Theorem 3\] preserves a reciprocal sum; our pair preserves an ordinary sum and varies its dyadic contribution. The contribution here is the combination of covering with sparse nonnegative corrections and eventual congruences for both coefficients and cumulative sums.

A uniform Hardy–Littlewood hypothesis of the type in \[kuperberg2023, Conjecture 1.3\] yields conditional irrationality in Land’s draft \[land2026, Theorem 2\] and conditional normality in Ringer’s draft \[ringer2026\]. The uniform quantitative prime-pattern estimates in those arguments are not supplied by the present absolute $`o(1)`$ block comparison. None of their hypotheses is assumed here. The companion, Section 3, compares the hypotheses and sampling conventions; Section <a href="#sec:pinned-lean-sources" data-reference-type="ref" data-reference="sec:pinned-lean-sources">7</a> below retains the further literature references.

The remaining sections ask what information about the actual weighted tails would prove irrationality. Further equivalences, counterexamples and computations are in the companion, *Prime-Gap Dyadic Series: Perturbations, Exact Criteria and Certificates*.

<a id="sec:parts"></a>

# The prime series and its actual tails

Retain the zero-based primes and gaps of Corollary <a href="#res:jointcountermodel" data-reference-type="ref" data-reference="res:jointcountermodel">2</a>, and put
``` math
\Pi=\sum_{n\ge0}p_n2^{-(n+1)},\qquad
 G=\sum_{n\ge0}g_n2^{-(n+1)}.
```
Both series converge absolutely by the bound proved in the introduction.

<div id="res:infinite" class="theorem">

**Theorem 3** (prime-to-gap identity). *The actual prime and gap series satisfy $`\Pi=2+G`$. Their complete tails
``` math
T_N=\sum_{j\ge1}g_{N+j}2^{-j}
```
satisfy $`T_0=2G-1`$ and $`T_{N+1}=2T_N-g_{N+1}`$. Thus $`\Pi`$, $`G`$ and $`T_0`$ have the same rationality status.*

</div>

Lean: [infinite prime gap identity](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L47), [real prime gap tail eq tsum shifted gaps](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L31), [real prime gap tail zero](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L57), [real prime gap tail recurrence](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/RealPrimeGapTail.lean#L48), and 2 further declarations in the [coverage section of the companion record](../mirror/erdos251-prime-gap-reasoning-surface.pdf#nameddest=coverage).

<div class="proof">

*Proof.* Finite summation by parts retains the endpoint:
``` math
\sum_{i=0}^{n}\frac{p_i}{2^{i+1}}
 =2+\sum_{i=0}^{n-1}\frac{g_i}{2^{i+1}}-\frac{p_n}{2^{n+1}}.
```
The endpoint tends to zero by the polynomial bound. Splitting off the first term of the absolutely convergent tail gives its recurrence, and $`g_0=1`$ gives $`T_0=2G-1`$. ◻

</div>

This is the reduction noted by Tao in the problem’s forum discussion \[erdosproblems251thread, 7 October 2025\], with convergence and the endpoint made explicit; summation by parts itself is not a new method.

<div id="res:true-tail" class="lemma">

**Lemma 4** (the boundary condition identifying a true tail). *Let $`\sum_{j\ge1}|a_j|2^{-j}<\infty`$ and $`U_{N+1}=2U_N-a_{N+1}`$. Then $`U_N=\sum_{j\ge1}a_{N+j}2^{-j}`$ for every $`N`$ if and only if $`2^{-N}U_N\to0`$.*

</div>

Lean: [real dyadic orbit eq true tail iff](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/TrueTail.lean#L57).

<div class="proof">

*Proof.* The recurrence gives $`2^{-N}U_N=U_0-\sum_{j=1}^{N}a_j2^{-j}`$. If its limit is zero, then $`U_0`$ is the full series; subtracting the first $`N`$ terms and multiplying by $`2^N`$ gives the stated formula for every $`U_N`$. Conversely, that formula gives $`2^{-N}U_N=\sum_{k>N}a_k2^{-k}\to0`$ by absolute convergence. Without the boundary condition, a term $`C2^N`$ can be added to every tail without changing the recurrence. ◻

</div>

<a id="sec:tail"></a>

# Integral shifts: an exact algebraic classification

Let $`U:\mathbb{N}\to\mathbb{R}`$ satisfy $`U_{N+1}=2U_N-a_{N+1}`$ with integer coefficients $`a_n`$, and write $`D_h(N)=U_{N+h}-U_N`$. Modulo integers, the recurrence is repeated doubling: subtracting $`a_{N+1}`$ does not change the fractional part. For rational $`U_0`$, the classification therefore depends on its denominator, not on the particular integer coefficients. It does not assume that $`U`$ consists of complete tails or that the coefficients are prime gaps.

For the positive even coefficients $`2,4,2,4,\ldots`$ starting at $`n=1`$, the complete tails alternate between $`8/3`$ and $`10/3`$. Thus $`U_0=8/3`$ is rational, although every length-$`1`$ difference is nonintegral; every length-$`2`$ difference is zero. Nonintegrality at one fixed shift length therefore does not certify irrationality.

<div id="res:escape-irrational" class="theorem">

**Theorem 5** (exact rationality classification). *For a real integer-coefficient recurrence, the following are equivalent: $`U_0\in\mathbb{Q}`$; $`D_h(N)\in\mathbb{Z}`$ for some $`h\ge1,N\ge0`$; and, for some fixed $`h\ge1`$, $`D_h(N)\in\mathbb{Z}`$ at every sufficiently large $`N`$. More precisely, if $`U_0=u/(2^sd)`$ is in lowest terms, with $`d`$ odd, then
``` math
\operatorname{den}(U_N)=2^{\max(s-N,0)}d,\qquad
 D_h(N)\in\mathbb{Z}\ \Longleftrightarrow\ N\ge s\ \text{and}\ d\mid2^h-1
 \quad(h\ge1).
```
Consequently $`U_0`$ is irrational exactly when every positive shift is nonintegral at every index, equivalently when for each fixed $`h\ge1`$ there are arbitrarily late nonintegral shifts.*

</div>

Lean: [real orbit exact den and shift](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/ExactDenominator.lean#L62), [rationality classification](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L94).

<div class="proof">

*Proof.* Iteration gives
``` math
U_N-2^NU_0\in\mathbb{Z},\qquad
 D_h(N)-2^N(2^h-1)U_0\in\mathbb{Z}.
```
The multiplier $`2^N(2^h-1)`$ is nonzero for $`h\ge1`$, so one integral shift forces $`U_0`$ rational. Subtracting an integer leaves a reduced denominator unchanged. For $`U_0=u/(2^sd)`$ in lowest terms, multiplication by $`2^N`$ therefore leaves denominator $`2^{\max(s-N,0)}d`$. Since $`2^h-1`$ is odd, $`D_h(N)`$ is integral exactly when $`N\ge s`$ and $`d\mid2^h-1`$. Euler’s congruence supplies $`d\mid2^{\varphi(d)}-1`$; for $`d=1`$ take $`h=1`$. This gives an integral fixed shift for every $`N\ge s`$. Negating the pointwise and eventual statements gives the last assertion. ◻

</div>

The eventual periodicity concerns fractional parts; it need not extend to the full tails or the integer coefficients. Applied to Theorem <a href="#res:infinite" data-reference-type="ref" data-reference="res:infinite">3</a>, the classification is an equivalence for the actual prime series, not an irrationality proof. The companion, Section 5 and Appendix E, gives the other recurrence reformulations.

<a id="sec:local-certificate"></a>

# A local certificate and the missing prime input

Fix $`h\ge1`$ and, for the actual prime-gap tail, put $`D_N=T_{N+h}-T_N`$ and $`\delta_N=g_{N+h+1}-g_{N+1}`$. The recurrence gives $`D_{N+1}=2D_N-\delta_N`$, with $`\delta_N`$ even. If both $`D_N`$ and $`D_{N+1}`$ were integers of absolute value less than one, both would be zero and hence $`\delta_N=0`$. The next proposition identifies exactly what happens when $`\delta_N\ne0`$.

<div id="res:signedwindow" class="proposition">

**Proposition 6** (two consecutive differences of absolute value less than one). *Let $`D,D'\in\mathbb{R}`$, $`\delta\in2\mathbb{Z}`$ and $`D'=2D-\delta`$. The conditions $`|D|<1`$, $`|D'|<1`$ and $`\delta\ne0`$ hold exactly when, for some $`s\in\{-1,1\}`$,
``` math
\delta=2s,\qquad \tfrac12<sD<1.
```
In that case $`sD'\in(-1,0)`$ and both $`D`$ and $`D'`$ are nonintegral.*

</div>

Lean: [signed two window iff](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/SignedWindow.lean#L7), [signed two window consequences](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCompleteR20/SignedWindow.lean#L47).

<div class="proof">

*Proof.* The bounds on $`D`$ and $`D'`$ imply $`-3<\delta<3`$. Since $`\delta`$ is nonzero and even, it equals $`2s`$ for $`s=1`$ or $`s=-1`$. Substituting in $`D'=2D-2s`$ gives $`1/2<sD<1`$. Conversely this inequality gives $`sD'=2sD-2\in(-1,0)`$, so both required absolute values are less than one. ◻

</div>

For $`\delta=2`$, the endpoints $`D=1/2`$ and $`D=1`$ give the integral values $`D'=-1`$ and $`D'=0`$. The zero case $`D=D'=\delta=0`$ also shows why the mismatch condition is needed.

<div id="prob:smallpair" class="problem">

**Problem 7** (two small tail differences at arbitrarily large indices). For every integer $`h\ge1`$ and every cutoff $`N_0`$, exhibit $`N\ge N_0`$ with
``` math
\begin{equation}
\label{eq:smallpair}
 |T_{N+h}-T_N|<1,\quad |T_{N+h+1}-T_{N+1}|<1,\quad
 g_{N+h+1}\ne g_{N+1}.
\end{equation}
```

</div>

This sufficient condition would prove irrationality by Theorem <a href="#res:escape-irrational" data-reference-type="ref" data-reference="res:escape-irrational">5</a>. For each fixed $`h`$, Schlage-Puchta’s Lemma 4 \[schlagepuchta2011\], applied to $`x_h-x_0\pm2`$, makes the eligible $`\delta_N=\pm2`$ indices a density-zero set. All three conditions must hold together arbitrarily late; separate infinite witness sets need not intersect.

<a id="finite-exact-tests"></a>

## Finite, exact tests

Choose $`M:\mathbb{N}\to\mathbb{R}`$ with $`M(n)\ge g_n`$ for every $`n`$ and $`\sum_{n\ge0}M(n)2^{-n}<\infty`$. For $`h\ge1,N\ge0,L\ge1`$, put
``` math
S_{h,N,L}=\sum_{j=1}^{L}(g_{N+h+j}-g_{N+j})2^{-j},\qquad
 R_{h,N,L}(M)=\sum_{j>L}(M(N+h+j)+M(N+j))2^{-j}.
```
The omitted terms give $`|D_N-S_{h,N,L}|\le R_{h,N,L}(M)`$. For a general real-valued $`M`$, convergence alone need not give an effective remainder bound; the polynomial choice below makes the test explicit.

<div id="res:truncation" class="proposition">

**Proposition 8** (finite separation criterion). *If for every $`h\ge1`$ and every cutoff $`N_0`$ there are $`N\ge N_0,L\ge1`$ with
``` math
\begin{equation}
\label{eq:truncation}
 \operatorname{dist}(S_{h,N,L},\mathbb{Z})>R_{h,N,L}(M),
\end{equation}
```
then $`\Pi`$ is irrational.*

</div>

Lean: [irrational prime series of finite truncation](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperTailBoundsR7.lean#L273).

<div class="proof">

*Proof.* The distance from $`D_N`$ to $`\mathbb{Z}`$ is at least $`\operatorname{dist}(S_{h,N,L},\mathbb{Z})-R_{h,N,L}(M)>0`$. The resulting nonintegrality at arbitrarily large indices is the criterion in Theorem <a href="#res:escape-irrational" data-reference-type="ref" data-reference="res:escape-irrational">5</a>. ◻

</div>

<div id="res:complete-truncation" class="remark">

*Remark 1* (what arbitrary truncation does not gain). Whenever $`|D-S_L|\le R_L\to0`$, nonintegrality of $`D`$ is equivalent to $`\operatorname{dist}(S_L,\mathbb{Z})>R_L`$ for some $`L`$. Indeed, for $`\delta=\operatorname{dist}(D,\mathbb{Z})>0`$, take $`R_L<\delta/2`$ and use the $`1`$-Lipschitz property of distance. Unrestricted depth therefore gives an exact reformulation, not an additional analytic estimate. At a prescribed logarithmic depth one must also control the margin from the integers as $`N`$ varies; a shrinking remainder alone does not do so. The companion, Appendix D.2, gives an explicit example distinguishing refinement at a fixed value from enclosures of changing values.

</div>

For the signed window it suffices that $`\delta_N=2s`$, $`s\in\{-1,1\}`$, and $`|QD_N-A|\le B`$, where $`A\in\mathbb{Z}`$, $`Q\in\mathbb{Z}_{>0}`$ and $`B\in\mathbb{Z}_{\ge0}`$, with
``` math
2sA-Q>2B,\qquad Q-sA>B.
```
These inequalities put the enclosure of $`sD_N`$ inside $`(1/2,1)`$. Here $`A`$ is a signed numerator, not a residue modulo $`Q`$. Choose $`M(n)=1250(n+2)^4`$ and put $`P(x)=x^4+8x^3+36x^2+104x+150`$. The identity $`2P(x)=(x+1)^4+P(x+1)`$ telescopes, with the polynomial terminal term vanishing, to $`\sum_{j\ge1}(x+j)^4 2^{-j}=P(x)`$. Thus
``` math
R_{h,N,L}(M)=\frac{1250}{2^L}
     \bigl(P(N+h+L+2)+P(N+L+2)\bigr).
```
For $`h=1,N=2,L=40`$, the required gap difference is $`\delta_2=g_4-g_3=2-4=-2`$. The certificate is
``` math
Q=2^{40},\quad A=-662838684750,\quad B=11764181250,\quad s=-1,
```
with $`A/Q=S_{1,2,40}`$ and $`B/Q=R_{1,2,40}(M)`$. The left sides exceed the right sides of the two certificate inequalities by $`202637379224`$ and $`424908761776`$, respectively. The companion, Section 6.1 and Appendix B, gives the full remainder derivation and prime-index calculation. One such pair supplies neither arbitrarily late pairs nor every shift.

<a id="sec:carry"></a>

# Nonperiodic coefficients with a rational sum

Eventual periodicity characterises rational binary expansions with digits in $`\{0,1\}`$, not arbitrary integer coefficients. For example,
``` math
\sum_{i=0}^{n-1}\frac{i-1}{2^{i+1}}=-\frac{n}{2^n}\longrightarrow0,
```
although the coefficients are unbounded and hence not eventually periodic. The first coefficient is negative. Positive even coefficients give the same obstruction. Let $`c_n=2(n^2+4n+2)`$ and $`U_n=2(n+4)^2`$. Then $`U_{n+1}=2U_n-c_{n+1}`$ and $`2^{-n}U_n\to0`$, so Lemma <a href="#res:true-tail" data-reference-type="ref" data-reference="res:true-tail">4</a> gives
``` math
\sum_{j\ge1}c_j2^{-j}=32,
 \qquad \sum_{n\ge0}c_n2^{-(n+1)}=18.
```
The coefficients are strictly increasing, and their adjacent differences $`4n+10`$ are never $`\pm2`$. This is a synthetic sequence, not a prime-gap construction; the companion, Section 8.6, treats the polynomial examples. For the first example, the sources give [the telescoping formula](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1157) and [nonperiodicity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1163).

The companion, Appendix D.5, also gives a bounded nonperiodic example. The actual prime gaps are [not eventually periodic](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1023), so that property alone does not settle their dyadic sum.

<a id="sec:open"></a>

# Consequences and limits

The construction can place its target interval inside $`(A,A+\eta)`$ for any $`\eta>0`$. Choose $`K'\ge K`$ sufficiently large that $`(K'+1)2^{-K'}<\eta`$, start beyond $`K'`$, and use $`e_n\le n`$ from the general schedule. Then $`0<\sum_{n\ge0}e_n2^{-(n+1)}\le(K'+1)2^{-K'}<\eta`$. It is the dyadic change, not the unweighted total, that is arbitrarily small.

<div id="res:irr-equivalence" class="corollary">

**Corollary 9** (exact irrationality reformulation). *The prime-value dyadic series is irrational if and only if the prime-gap dyadic series is. Both series converge by the polynomial bound proved above; neither side is proved irrational.*

</div>

Lean: [infinite prime gap identity](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L47), [irrationality reformulation](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L56).

<div class="proof">

*Proof.* Theorem <a href="#res:infinite" data-reference-type="ref" data-reference="res:infinite">3</a> gives $`\Pi=2+G`$, and adding a rational number preserves both rationality and irrationality. ◻

</div>

<div id="res:gap-nonperiodic" class="proposition">

**Proposition 10** (prime gaps do not become periodic). *For every positive $`h`$, the actual consecutive-prime-gap sequence is not eventually periodic with period $`h`$.*

</div>

Lean: [prime gaps not eventually periodic](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos251/PaperCoreR7.lean#L175).

<div class="proof">

*Proof.* An eventually periodic sequence takes only finitely many values and is bounded. Prime gaps are unbounded: for each $`m\ge2`$, the $`m-1`$ consecutive integers $`m!+2,\ldots,m!+m`$ are composite. The consecutive primes on either side of this interval therefore have a gap at least $`m`$. ◻

</div>

Bounded gaps \[zhang2014\], clusters of each fixed size \[maynard2015; polymath2014\], and extreme large gaps \[fgkmt2018\] do not themselves supply a signed weighted-tail window, even with Polymath’s bound $`\liminf_n g_n\le246`$ \[polymath2014, Theorem 1.4(i)\]. The logarithmic depth chosen in the companion, Section 10, makes the explicit remainder tend to zero, but the finite sum still needs a larger margin from the relevant boundary.

For the actual prime tails, separation from the integers is still needed arbitrarily late for every positive shift; <a href="#eq:smallpair" data-reference-type="eqref" data-reference="eq:smallpair">[eq:smallpair]</a> is a stronger sufficient condition. The preserved statistics do not supply this step, but primality or sharper rare-event estimates may still be used. The finite certificates do not prove irrationality.

<a id="attribution-and-verification"></a>

## Attribution and verification

The source links retain revision `99f4bf47422a`; the companion’s declaration index records the sparse existence results and build status. The printed construction uses triples; the formal one changes one coordinate at a time. The linked polylogarithmic statement chooses the permitted set, interval, and support-count constant and cutoff before the target; its eventual congruences and convergence are quantified after the target. The common congruence cutoffs used here follow from the printed schedule. The companion separates these statement-level guarantees from the uniform bounds deduced using the common support. The prime-gap corollary is an ordinary deduction using Schlage-Puchta’s theorem and the prime number theorem.

The verification record reports a build of `ErdosProblems` and `Erdos249257` with Lean 4.29.1; no new Lean build is claimed here. Lean 4 \[lean4\] and mathlib \[mathlib\] provide the checking environment. The companion distinguishes checked declarations, exact integer computations and ordinary proofs. A source link alone does not establish that the linked statement belongs to a successful build.

I thank Wouter van Doorn for advice on explaining unfamiliar hypotheses, removing unnecessary terminology, and using notation only when it helps the reader. His comments concerned an earlier note on Problem #243; this acknowledgement does not imply that he reviewed or endorsed the mathematics of the present paper. The author received no external funding and declares no competing interests. The numbering follows Bloom’s catalogue \[erdosproblems\].

<a id="sec:pinned-lean-sources"></a>

# Sources and further comparisons

The links below identify the formal definitions and statements used in this note. Each retains its original source revision and line number. The descriptions give the mathematical content rather than the names used in the Lean files.

**Finite series.** [The first prime gap is one](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L47); [The second prime gap is two](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L51); [Finite dyadic sums](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L101); [Finite dyadic sums of consecutive differences](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L121); [Summation by parts for a rational sequence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L138); [The two prime-series normalisations differ by a factor of two](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L111); [Summation by parts for the primes](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L172); [Terms of the prime series](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L183); [Terms of the prime-gap series](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L192); [The identity relating prime and gap terms](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L202).

**Convergent series.** [Convergence of the gap series from convergence of the prime series](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L385); [The infinite prime-to-gap identity under summability](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L404); [Prime terms with denominator powers starting at zero](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L188); [The factor-of-two identity for individual terms](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L196); [Equivalent irrationality of the prime and gap series](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L435); [The infinite identity in the second normalisation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L444); [Equivalent irrationality in the second normalisation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L459); [An elementary polynomial upper bound for the primes](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L360); [Convergence of the prime series](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L379); [The prime-to-gap identity with convergence proved](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L427).

**Recurrences.** [The recurrence satisfied by rescaled dyadic tails](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L482); [The difference between two terms of a recurrence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L544); [The weighted integer sum accumulated by iteration](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L647); [Iteration of the recurrence](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L653); [A shift as a multiple of a tail minus an integer](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L667); [The recurrence for consecutive tail differences](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L563); [Subtracting an integer preserves integrality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L677); [The criterion for a shift to be integral](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L802).

**Denominators and integral shifts.** [The denominator divisibility criterion for an integral shift](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1279); [Euler’s congruence for an odd denominator](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L695); [An integral shift of totient length](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L877); [An integral shift remains integral at the next index](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L888); [An integral shift remains integral at every later index](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L900); [The denominator after one recurrence step](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1217); [An odd denominator is unchanged by a step](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1226); [An even denominator is halved by a step](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1236); [Removing the power of two from a rational denominator](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L723); [An integral multiple after the power of two is removed](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L756); [Eventual integral shifts from the denominator factorisation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L830); [Eventual integral shifts under rationality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L853).

**Rationality criteria.** [Rational representation of a rescaled prime-gap tail](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L489); [The recurrence for that rational representation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L527); [Existence of the rational representation under rationality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L510); [Rationality is equivalent to one integral positive-length shift](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1479); [Rationality is equivalent to eventual integrality of a fixed shift](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1525); [Irrationality is equivalent to nonintegrality of every positive-length shift](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1551); [Irrationality is equivalent to arbitrarily late nonintegral shifts of each length](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1572).

**Small differences and counterexamples.** [Two small differences with unequal coefficients cannot both be integral](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L979); [Arbitrarily late small unequal pairs exclude eventual integrality](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1006); [The small-pair implication for prime gaps](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1112); [Prime gaps exceed every prescribed bound](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L57); [Prime gaps are not eventually periodic](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1023); [Coefficients obtained by telescoping](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1129); [The finite telescoping identity](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1137); [The telescoping example with coefficients equal to the index minus one](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1157); [Nonperiodicity of the telescoping example](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1163); [Rationality forces some fixed shift to fail eventual smallness](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1097).

**Further finite identities.** [Finite prime sums in the second normalisation](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L106); [Adding one term to a dyadic partial sum](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L124); [Adding one term to a difference partial sum](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L129); [Consecutive primes are in increasing order](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L152); [The natural-number gap agrees with subtraction in the rationals](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L156); [Finite sums of weighted prime gaps](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L161); [Finite sums for the telescoping coefficients](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1133); [A nonnegative version of the telescoping coefficients](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1177); [Agreement of the nonnegative and integer formulas](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos251/PrimeGapDyadicTail.lean#L1180).

<a id="further-comparisons."></a>

#### Further comparisons.

The companion, Section 3, treats the broader subsum literature, which is not needed for the construction. Interval-containing multigeometric subsum sets \[bartoszewicz2014, Theorem 2\] and Cantorvals with the overlap inequality holding on a density-zero set \[prusptak2024, Theorem\] show why sufficient covering conditions are not a classification. The terminology and classification are discussed in \[glabprus2025, §1\] and \[nitecki2015, Theorem 14 of the consulted preprint\]; prescribed inequality patterns need not determine the presence of interior \[miskaprusptak2023, Theorem 2\], while \[nowakowski2025, Definition 2, Theorem 3.1\] gives a different sufficient condition requiring an infinite positivity procedure.

Schlage-Puchta’s result concerns each fixed polynomial in a fixed number of consecutive gaps \[schlagepuchta2011, Lemma 4\]. The automatic-sequence density results of Adamczewski–Drmota–Müllner \[adm2022, Theorems 1.2, 1.4\] likewise concern fixed automatic sequences, not growing families of automata or the unbounded gap sequence. They give logarithmic densities in general, and a sufficient condition for natural densities to exist and be rational; the logarithmic densities need not be rational.

<div class="thebibliography">

99

Paul Erdős, [*Sur certaines séries à valeur irrationnelle*](https://users.renyi.hu/~p_erdos/1958-19.pdf). L’Enseignement Mathématique **4** (1958), 93–100, doi:[10.5169/seals-34629](https://doi.org/10.5169/seals-34629). Paul Erdős and Ronald L. Graham, [*Old and New Problems and Results in Combinatorial Number Theory*](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf). Monographies de L’Enseignement Mathématique, L’Enseignement Mathématique, 1980. Paul Erdős and Carl Pomerance, [*On the largest prime factors of $`n`$ and $`n+1`$*](https://doi.org/10.1007/BF01818569). Aequationes Mathematicae **17** (1978), 311–321, doi:[10.1007/BF01818569](https://doi.org/10.1007/BF01818569). Paul Erdős, [*On the irrationality of certain series: problems and results*](https://doi.org/10.1017/CBO9780511897184.009). New Advances in Transcendence Theory, Cambridge University Press, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). Kevin Ford, Ben Green, Sergei Konyagin, James Maynard and Terence Tao, [*Long gaps between primes*](https://arxiv.org/abs/1412.5029v3). Journal of the American Mathematical Society **31** (2018), 65–105, doi:[10.1090/jams/876](https://doi.org/10.1090/jams/876); arXiv:[1412.5029v3](https://arxiv.org/abs/1412.5029v3). John A. Fridy, [*Generalized bases for the real numbers*](https://www.fq.math.ca/Scanned/4-3/fridy.pdf). The Fibonacci Quarterly **4** (1966), no. 3, 193–201. Vjekoslav Kovač and Terence Tao, [*On several irrationality problems for Ahmes series*](https://arxiv.org/abs/2406.17593v4). Acta Mathematica Hungarica **175** (2025), 572–608, doi:[10.1007/s10474-025-01528-0](https://doi.org/10.1007/s10474-025-01528-0); arXiv:[2406.17593v4](https://arxiv.org/abs/2406.17593v4). Statement and section numbers refer to arXiv version 4. Vivian Kuperberg, [*Sums of singular series with large sets and the tail of the distribution of primes*](https://arxiv.org/abs/2210.09775v2). The Quarterly Journal of Mathematics **74** (2023), no. 4, 1457–1479, doi:[10.1093/qmath/haad030](https://doi.org/10.1093/qmath/haad030); arXiv:[2210.09775v2](https://arxiv.org/abs/2210.09775v2). Statement numbers refer to arXiv version 2, 15 June 2023. Johan Land, [*A conditional proof of the irrationality of $`\sum_{n\ge1}p_n2^{-n}`$ under a uniform Hardy–Littlewood prime-tuples conjecture*](https://github.com/beetree/math_erdos_251). Research draft, 5 September 2026. Formalisation material accompanies the draft. Leonardo de Moura and Sebastian Ullrich, [*The Lean 4 theorem prover and programming language*](https://doi.org/10.1007/978-3-030-79876-5_37). Automated Deduction – CADE 28, Lecture Notes in Computer Science, Springer, 2021, pp. 625–635, doi:[10.1007/978-3-030-79876-5_37](https://doi.org/10.1007/978-3-030-79876-5_37). The mathlib Community, [*The Lean mathematical library*](https://doi.org/10.1145/3372885.3373824). Proceedings of the 9th ACM SIGPLAN International Conference on Certified Programs and Proofs, ACM, 2020, pp. 367–381, doi:[10.1145/3372885.3373824](https://doi.org/10.1145/3372885.3373824). Describes a Lean 3-era snapshot; the repository lock identifies the library used by the present Lean 4 sources. James Maynard, [*Small gaps between primes*](https://doi.org/10.4007/annals.2015.181.1.7). Annals of Mathematics **181** (2015), 383–413, doi:[10.4007/annals.2015.181.1.7](https://doi.org/10.4007/annals.2015.181.1.7). Hugh L. Montgomery and Robert C. Vaughan, [*Multiplicative Number Theory I: Classical Theory*](https://doi.org/10.1017/CBO9780511618314). Cambridge Studies in Advanced Mathematics, Cambridge University Press, 2007, doi:[10.1017/CBO9780511618314](https://doi.org/10.1017/CBO9780511618314). Wouter van Doorn and Vjekoslav Kovač, [*Lacunary sequences whose reciprocal sums represent all rational numbers in an interval*](https://arxiv.org/abs/2509.24971v3). Acta Arithmetica **223** (2026), 275–295, doi:[10.4064/aa251001-13-1](https://doi.org/10.4064/aa251001-13-1); arXiv:[2509.24971v3](https://arxiv.org/abs/2509.24971v3). Statement numbers refer to arXiv version 3. Yitang Zhang, [*Bounded gaps between primes*](https://doi.org/10.4007/annals.2014.179.3.7). Annals of Mathematics **179** (2014), 1121–1174, doi:[10.4007/annals.2014.179.3.7](https://doi.org/10.4007/annals.2014.179.3.7). Thomas F. Bloom, [*Erdős Problem \#251*](https://www.erdosproblems.com/251). 2026. Catalogue snapshot accessed 6 September 2026. Erdős Problems contributors, [*Erdős Problem \#251 discussion thread*](https://www.erdosproblems.com/forum/thread/251). 2026. Snapshot accessed 6 September 2026: Tao comment of 7 October 2025 and Land comments of 6 September 2026. ChatGPT 5.4 Pro (orchestrated by Vjeko Kovač), [*On the Erdős problem \#251*](https://web.math.pmf.unizg.hr/~vjekovac/files/Erdos_problem_251.pdf). Unpublished note, Department of Mathematics, University of Zagreb, 2026. Accessed 6 September 2026. Stefan Ringer, [*Local gap statistics, telescoping, and normality: a local-pattern approach to Erdős problem 251*](https://github.com/StefanRinger/erdos-251). Preprint, 11 September 2026. Mutable main-branch TeX consulted 16 September 2026; the cited conditional statements were rechecked 18 September 2026. Formalisation material accompanies the draft. Tonći Crmarić and Vjekoslav Kovač, [*On the irrationality of certain super-polynomially decaying series*](https://arxiv.org/abs/2504.18712v1). Colloquium Mathematicum **179** (2025), 55–68, doi:[10.4064/cm9628-5-2025](https://doi.org/10.4064/cm9628-5-2025); arXiv:[2504.18712v1](https://arxiv.org/abs/2504.18712v1). Lemma 4 is cited using arXiv version 1. Boris Adamczewski, Michael Drmota and Clemens Müllner, [*(Logarithmic) densities for automatic sequences along primes and squares*](https://arxiv.org/abs/2009.14773v2). Transactions of the American Mathematical Society **375** (2022), no. 1, 455–499, doi:[10.1090/tran/8476](https://doi.org/10.1090/tran/8476); arXiv:[2009.14773v2](https://arxiv.org/abs/2009.14773v2). Theorems 1.2 and 1.4 refer to arXiv version 2, 13 April 2021; journal publication is 2022. Wouter van Doorn, [*Partitions with prescribed sum of reciprocals: asymptotic bounds*](https://arxiv.org/abs/2502.02200v2). 2025; arXiv:[2502.02200v2](https://arxiv.org/abs/2502.02200v2). Version 2, 23 July 2025. Szymon Głąb and Franciszek Prus-Wiśniowski, [*Achievement sets – current results and open problems*](https://arxiv.org/abs/2512.17285v1). Real Analysis Exchange (2026), doi:[10.14321/realanalexch.1766383782](https://doi.org/10.14321/realanalexch.1766383782); arXiv:[2512.17285v1](https://arxiv.org/abs/2512.17285v1). Advance publication, first available in Project Euclid 8 June 2026. Consulted text remains arXiv:2512.17285v1 (19 December 2025). Franciszek Prus-Wiśniowski and Jolanta Ptak, [*Achievable Cantorvals almost without reversed Kakeya conditions*](https://arxiv.org/abs/2412.08768v1). 2024; arXiv:[2412.08768v1](https://arxiv.org/abs/2412.08768v1). Version 1 submitted 11 December 2024. The sparse indices satisfy the overlap inequality, not its strict term-dominating reverse. Artur Bartoszewicz, Małgorzata Filipczak and Emilia Szymonik, [*Multigeometric sequences and Cantorvals*](https://arxiv.org/abs/1304.4218v2). Central European Journal of Mathematics **12** (2014), no. 7, 1000–1007, doi:[10.2478/s11533-013-0396-4](https://doi.org/10.2478/s11533-013-0396-4); arXiv:[1304.4218v2](https://arxiv.org/abs/1304.4218v2). Jan-Christoph Schlage-Puchta, [*The irrationality of some number theoretical series*](https://arxiv.org/abs/1105.1451v1). Acta Arithmetica **126** (2007), no. 4, 295–303, doi:[10.4064/aa126-4-1](https://doi.org/10.4064/aa126-4-1); arXiv:[1105.1451v1](https://arxiv.org/abs/1105.1451v1). Published in 2007; arXiv upload is from 2011. Lemma and preprint page locators refer to arXiv version 1. Paul Erdős, [*Beweis eines Satzes von Tschebyschef*](https://users.renyi.hu/~p_erdos/1932-01.pdf). Acta Litterarum ac Scientiarum Szeged **5** (1932), 194–198. D. H. J. Polymath, [*Variants of the Selberg sieve, and bounded intervals containing many primes*](https://arxiv.org/abs/1407.4897v4). Research in the Mathematical Sciences **1** (2014), article 12, doi:[10.1186/s40687-014-0012-7](https://doi.org/10.1186/s40687-014-0012-7); arXiv:[1407.4897v4](https://arxiv.org/abs/1407.4897v4). Theorem 1.4(i) refers to arXiv version 4 (22 December 2014); the journal numbers it Theorem 4(i). An erratum is recorded at doi:10.1186/s40687-015-0033-x. Zbigniew Nitecki, [*Cantorvals and Subsum Sets of Null Sequences*](https://arxiv.org/abs/1106.3779v2). The American Mathematical Monthly **122** (2015), no. 9, 862–870, doi:[10.4169/amer.math.monthly.122.9.862](https://doi.org/10.4169/amer.math.monthly.122.9.862); arXiv:[1106.3779v2](https://arxiv.org/abs/1106.3779v2). Consulted preprint: Subsum Sets: Intervals, Cantor Sets, and Cantorvals, version 2 (8 July 2013). Theorem 14 is attributed there to Guthrie–Nymann; its locator is not journal pagination. Piotr Miska, Franciszek Prus-Wiśniowski and Jolanta Ptak, [*More on Kakeya Conditions for Achievement Sets*](https://ruj.uj.edu.pl/server/api/core/bitstreams/d6630f7b-e6ee-4de8-8a1b-81c7b4c59d2e/content). Results in Mathematics **78** (2023), article 113, doi:[10.1007/s00025-023-01890-x](https://doi.org/10.1007/s00025-023-01890-x). Repairs an estimate in the 2021 proof, preserving its uniqueness conclusion, and gives a simpler proof of a weaker theorem without that conclusion. Piotr Nowakowski, [*On a new condition implying that an achievement set is a Cantorval and its applications*](https://arxiv.org/abs/2512.17761v1). 2025; arXiv:[2512.17761v1](https://arxiv.org/abs/2512.17761v1). Version 1, 19 December 2025. Theorem 3.1 requires the Star Procedure of Definition 2 never to break; no application to the present factorial weights is asserted.

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.
