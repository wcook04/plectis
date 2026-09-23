<a id="erdos-269-three-prime-running-lcm"></a>

# No Finite Separable Representation at Three Prime Generators

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

For three distinct primes, the reciprocal running-LCM kernel has nonsingular minors of every order, with the same indices in every third-coordinate layer. Row and column rescaling reduces the proof to a matrix whose entries are $`1`$ or the reciprocal of the third prime. Thus no finite sum of products separates one exponent from the other two. Separately, for the repeated $`\{2,3,5\}`$ series we prove a tail recurrence and a residue criterion equivalent to irrationality. The unresolved step is to prove its inequalities for every positive multiplier coprime to $`30`$ and arbitrarily late starts.

<a id="sec:problem"></a>

# Introduction

For a finite prime set $`P`$, let $`\mathcal S_P`$ consist of the positive integers whose prime factors lie in $`P`$, including $`1`$. We use $`\mathbb{N}=\{0,1,2,\ldots\}`$ for exponent indices. For $`x\ge1`$, put
``` math
\operatorname{L}(x)=\operatorname{lcm}\{u\in\mathcal S_P:u\le x\},\qquad
 \mathcal R_P=\sum_{u\in\mathcal S_P}\operatorname{L}(u)^{-1}.
```
Erdős asked whether $`\mathcal R_P`$ is irrational when $`|P|\ge2`$ \[erdosgraham1980, p. 65\]\[erdos1988, p. 106\]. For $`P=\{p,q,r\}`$, write
``` math
\operatorname{H}(x)=p^{\lfloor\log_p x\rfloor}q^{\lfloor\log_q x\rfloor}
 r^{\lfloor\log_r x\rfloor},\qquad
 \operatorname{K}(i,j,k)=\operatorname{H}(p^iq^jr^k)^{-1}.
```
Prime-power divisibility gives $`\operatorname{L}=\operatorname{H}`$ (Proposition <a href="#res:lcm" data-reference-type="ref" data-reference="res:lcm">6</a>). Fan used this identity to separate the two-prime kernel \[fan2026comment\]. With three primes, even a finite sum of separated products is impossible. This is a statement about the kernel, not the arithmetic nature of its sum.

<a id="sec:rank"></a>

# Nonsingular minors of every order

<div id="res:infinite-rank" class="theorem">

**Theorem 1** (no finite separation of the kernel). *Let $`p,q,r`$ be primes with $`p\ne q`$, $`p\ne r`$ and $`q\ne r`$. For every $`n\ge0`$ there are injective maps $`I,J:\{0,\ldots,n-1\}\to\mathbb{N}`$ such that, for every $`k\ge0`$,
``` math
\det\bigl(\operatorname{K}(I(a),J(b),k)\bigr)_{0\le a,b<n}\ne0.
```
Consequently, for no finite $`d`$ do there exist rational-valued functions $`f_\ell(i)`$ and $`G_\ell(j,k)`$, $`0\le\ell<d`$, satisfying
``` math
\operatorname{K}(i,j,k)=\sum_{\ell<d}f_\ell(i)G_\ell(j,k)
 \qquad\hbox{for all }i,j,k.
```*

</div>

Lean: [paper uniform rank and nonseparation](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperR7BasicAssembly.lean#L22).

<div class="proof">

*Proof.* For fixed $`k`$, we rescale rows and columns to obtain a matrix independent of $`k`$. Put $`c=r^{-1}`$, $`x_i=\{i\log_r p\}`$ and $`y_j=\{j\log_r q\}`$, where braces denote fractional parts. Splitting the floor exponents gives
``` math
\operatorname{K}(i,j,k)=U_i(k)^{-1}C_{ij}V_j(k)^{-1},\qquad
 C_{ij}=c^{\mathbf1_{\{x_i+y_j\ge1\}}},
```
where
``` math
\begin{aligned}
 U_i(k)&=p^i q^{\lfloor\log_q(p^ir^k)\rfloor}
            r^{k+\lfloor\log_r p^i\rfloor},\\
 V_j(k)&=q^j p^{\lfloor\log_p(q^jr^k)\rfloor}
            r^{\lfloor\log_r q^j\rfloor}.
\end{aligned}
```
The positive factors do not affect whether a minor vanishes; $`C`$ records only whether $`x_i+y_j\ge1`$. Distinct primes make $`\log_r p`$ and $`\log_r q`$ irrational, so each fractional-part orbit is dense in $`[0,1]`$. The row and column indices are independent choices; no density of a single orbit of pairs is required. For $`n\ge1`$, choose distinct rows with $`0<x_{I(0)}<\cdots<x_{I(n-1)}<1`$. We choose each column so that its entries change from $`1`$ to $`c`$ at a different selected row. Writing $`s_b=1-y_{J(b)}`$, density of $`(y_j)`$ lets us choose

``` math
s_0\in(0,x_{I(0)}),\qquad
 s_b\in(x_{I(b-1)},x_{I(b)})\quad(1\le b<n).
```

The intervals for the $`s_b`$ are disjoint, so the column indices are distinct. The strict inequalities also avoid the threshold itself, and give $`x_{I(a)}+y_{J(b)}\ge1`$ exactly when $`b\le a`$. Thus multiplying row $`a`$ by $`U_{I(a)}(k)`$ and column $`b`$ by $`V_{J(b)}(k)`$ reduces the selected kernel minor to
``` math
T_n(c)=\begin{pmatrix}
 c&1&\cdots&1\\
 c&c&\cdots&1\\
 \vdots&\vdots&\ddots&\vdots\\
 c&c&\cdots&c
 \end{pmatrix},\qquad
 \det T_n(c)=c(c-1)^{n-1}.
```
Indeed, subtracting each preceding row from the next, working upwards from the last row, leaves diagonal entries $`c,c-1,\ldots,c-1`$. The original determinant is therefore
``` math
c(c-1)^{n-1}
 \prod_{a<n}U_{I(a)}(k)^{-1}\prod_{b<n}V_{J(b)}(k)^{-1}\ne0.
```
The indices were chosen from $`C`$, independently of $`k`$. For $`n=0`$ the empty determinant equals $`1`$.

For the final assertion, suppose a separation with $`d`$ summands existed and fix any $`k`$. On the rows $`I(0),\ldots,I(d)`$ and columns $`J(0),\ldots,J(d)`$ its matrix would be the product of the $`(d+1)\times d`$ matrix $`(f_\ell(I(a)))_{a,\ell}`$ and the $`d\times(d+1)`$ matrix $`(G_\ell(J(b),k))_{\ell,b}`$. Its rank would be at most $`d`$, so its determinant would vanish, contrary to the minor just constructed. ◻

</div>

No continuity or boundedness is assumed for the separated factors.

<div id="res:admissible-modular-minors" class="corollary">

**Corollary 2** (the same minors modulo integers coprime to $`30`$). *For $`(p,q,r)=(2,3,5)`$ and every $`n\ge1`$, there are injective maps $`I,J:\{0,\ldots,n-1\}\to\mathbb{N}`$, chosen independently of $`B`$ and $`k`$, such that for every $`B\ge2`$ coprime to $`30`$ and every $`k\ge0`$, the selected $`n\times n`$ kernel matrix has unit determinant over $`\mathbb Z/B\mathbb Z`$, with each reciprocal prime power interpreted by its modular inverse.*

</div>

Lean: [admissible modular minors](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperR7ModularMinors.lean#L133).

<div class="proof">

*Proof.* Choose the maps from Theorem <a href="#res:infinite-rank" data-reference-type="ref" data-reference="res:infinite-rank">1</a>. Every row and column factor is a unit modulo $`B`$. The normalised determinant is $`5^{-1}(-4/5)^{n-1}`$, also a unit. ◻

</div>

The modulus may be composite, for example $`49`$ or $`77`$. Coprimality with $`30`$ makes both the reciprocal entries and the determinant units: the latter introduces only a power of $`4`$ in its numerator.

<div id="res:rank" class="example">

**Example 3**. For $`(p,q,r)=(2,3,5)`$, the leading two-by-two determinant is $`-1/15`$: its four entries are $`1,1/6,1/2,1/60`$, so it equals $`1/60-1/12`$.

</div>

<a id="the-indices-must-be-selected."></a>

#### The indices must be selected.

The leading $`4\times4`$ block at $`\{2,3,5\}`$ is singular:
``` math
\operatorname{K}(3,j,0)=\frac1{120}\operatorname{K}(0,j,0)\qquad(0\le j<4).
```
These equalities follow by evaluating the height at $`3^j`$ and $`8\cdot3^j`$. But at $`j=4`$, $`\operatorname{K}(3,4,0)-\operatorname{K}(0,4,0)/120=-1/19440000`$. Thus the leading minors do not supply the arbitrary-order theorem.

<div id="res:finite-cut-rank" class="proposition">

**Proposition 4** (rank of a matrix of threshold columns). *Let $`m\ge1`$ and let $`c`$ lie in a field with $`c\ne 0,1`$. For $`0\le k\le m`$ write $`v_k`$ for the length-$`m`$ column with a $`1`$ in each of the first $`k`$ coordinates and $`c`$ thereafter. A matrix whose distinct columns are $`v_k`$ for $`k`$ in a nonempty set $`E`$ has rank $`|E|-\mathbf 1_{\{0,m\}\subseteq E}`$.*

</div>

Lean: [rank cut matrix](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperR7FiniteCutRank.lean#L182).

The correction accounts for the two constant columns: $`v_0=c v_m`$. There is no other dependence among distinct threshold columns.

<div class="proof">

*Proof.* List $`E=\{k_1<\cdots<k_t\}`$. The $`t-1`$ differences $`v_{k_{j+1}}-v_{k_j}=(1-c)\mathbf 1_{\{k_j,\ldots,k_{j+1}-1\}}`$ have disjoint nonempty supports, hence are linearly independent. If $`k_1>0`$ or $`k_t<m`$, their union misses a coordinate where $`v_{k_1}`$ is nonzero, so the rank is $`t`$. If $`k_1=0`$ and $`k_t=m`$, then $`v_0=c\,\mathbf 1`$ lies in the span of the differences (their sum is $`(1-c)\mathbf 1`$), so the rank is $`t-1`$. ◻

</div>

The restrictions $`c\ne0,1`$ exclude a zero column or identical columns; they hold for $`c=1/r`$ over $`\mathbb Q`$. In one fixed layer $`k`$, ordering the sampled row phases puts every column in the stated form. The formula therefore determines the rank of each nonempty rectangular sample. For fixed row and column indices this rank is independent of $`k`$. The companion, Section 4, gives the exact rational comparisons.

<a id="exact-rank-is-not-an-approximation-obstruction."></a>

#### Exact rank is not an approximation obstruction.

Truncating the original kernel to $`i<N`$ gives a sum of $`N`$ separated terms. The bound $`\operatorname{H}(x)>x^3/(pqr)`$ makes the truncation error tend to zero both uniformly and in $`\ell^1(\mathbb N^3)`$. By contrast, the rescaled matrix in the rank proof has uniform distance $`(1-1/r)/2`$ from the matrices of finite rank. Rescaling preserves exact rank but removes the decay responsible for the first approximation. The companion proves both assertions, including the distinction between finite restrictions and the full infinite matrix, in Section 4.1.

<a id="sec:two-prime"></a>

# The two-prime comparison

Fan’s post of 26 June 2026 gives the repeated two-prime factorisation, its quadratic expression in one Hecke–Mahler value and its transcendence conclusion \[fan2026comment\]. Counting the contributions at powers of each prime also gives the affine formula for the distinct-height sum below. The calculation fixes the normalisations and distinguishes the two sums.

<div id="res:two-prime-transcendence" class="theorem">

**Theorem 5** (both two-prime sums). *<span id="res:two-prime-repeated-transcendence" label="res:two-prime-repeated-transcendence"></span> Let $`p<q`$ be distinct primes. Put $`\theta=\log p/\log q`$ and $`A=\sum_{n\ge0}p^{-n}q^{-\lfloor n\theta\rfloor}`$. Let $`\mathcal R_{p,q}`$ sum the reciprocal running LCM at every positive $`\{p,q\}`$-smooth integer, and let $`\mathcal D_{p,q}`$ count each distinct running LCM once. Then
``` math
\begin{equation}
\label{eq:two-prime-affine}
 \mathcal D_{p,q}=\frac{(q-p)A+p}{q-1},\qquad
 \mathcal R_{p,q}=\frac{(p+q-1)A-(p-1)A^2}{q-1}.
\end{equation}
```
Both numbers are transcendental.*

</div>

Lean: [two prime affine and quadratic](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperCompleteR21/TwoPrimeSums.lean#L841), [two prime sums transcendental](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperCompleteR21/TwoPrimeSums.lean#L872), [running lcm eq two prime height](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperCompleteR21/TwoPrimeSums.lean#L88), [two prime height smooth](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperCompleteR21/TwoPrimeSums.lean#L159), and 9 further declarations. Conditional on the transcendence theorem of Bugeaud and Laurent; see the [coverage section of the companion record](../mirror/erdos269-running-lcm-reasoning-surface.pdf#nameddest=coverage).

<div class="proof">

*Proof.* Set $`x=1/p`$, $`y=1/q`$, $`m_n=\lfloor n\theta\rfloor`$ and $`\delta_n=m_{n+1}-m_n`$. Unique factorisation makes $`\theta`$ irrational, and $`0<\theta<1`$ gives $`\delta_n\in\{0,1\}`$. The initial value and the positive powers of $`p`$ contribute $`A=\sum_{n\ge0}x^ny^{m_n}`$. There is one $`q`$-power strictly between $`p^n`$ and $`p^{n+1}`$ exactly when $`\delta_n=1`$, so the positive powers of $`q`$ contribute
``` math
B=\sum_{n\ge0}\delta_nx^ny^{m_n+1},\qquad \mathcal D_{p,q}=A+B.
```
Since $`0<x,y<1`$, these series converge absolutely. The identity $`y^{m_{n+1}}-y^{m_n}=\delta_ny^{m_n}(y-1)`$ and an index shift in $`A`$ give $`A-1-xA=x(y-1)B/y`$. Therefore
``` math
B=\frac{p-(p-1)A}{q-1}.
```
At $`p^iq^j`$ the height is $`p^{i+\lfloor j/\theta\rfloor}q^{j+m_i}`$, hence
``` math
\mathcal R_{p,q}
 =A\sum_{j\ge0}y^jx^{\lfloor j/\theta\rfloor}=A(1+B).
```
For the last equality, each $`j\ge1`$ corresponds to $`n=\lfloor j/\theta\rfloor`$ with $`m_n=j-1`$ and $`\delta_n=1`$. These identities prove <a href="#eq:two-prime-affine" data-reference-type="eqref" data-reference="eq:two-prime-affine">[eq:two-prime-affine]</a>.

For the Hecke–Mahler series $`F_\theta(x,y)=\sum_{n\ge1}\sum_{k=1}^{m_n}x^ny^k`$, geometric summation gives
``` math
\begin{equation}
\label{eq:hecke-mahler-boundary}
 A=\frac1{1-x}-\frac{1-y}{y}F_\theta(x,y).
\end{equation}
```
Bugeaud and Laurent’s theorem \[bugeaudlaurent2023, Theorem 1.1\] applies with intercept $`\rho=0`$, $`\beta=x`$ and $`\alpha=y`$: the slope $`\theta`$ is irrational and lies in $`(0,1)`$, $`x`$ and $`y`$ are nonzero algebraic numbers, $`|x|<1`$ and $`|xy^\theta|=p^{-2}<1`$. Hence $`F_\theta(x,y)`$ is transcendental; this case $`\rho=0`$ is due to Loxton and van der Poorten \[loxtonvdp1977, Theorem 8, p. 40\]. Thus $`A`$ is transcendental. The displayed affine and quadratic polynomials are nonconstant, so an algebraic value of either would force $`A`$ to be algebraic. ◻

</div>

The same calculation applies to the monoid generated by any coprime integers $`1<p<q`$, such as $`4,9`$, but need not describe all integers supported on their prime factors. The companion’s Section 3 gives this extension and the failure for $`4,8`$.

The three-prime tail argument starts again from the running LCM, retaining every multiplicity; it does not use the rank theorem. The distinct-height assertion is a separate historical statement \[erdos1974letter\].

<a id="sec:lcm"></a>

# The recurrence for the repeated sum

<span id="sec:cells" label="sec:cells"></span><span id="sec:fibre" label="sec:fibre"></span><span id="sec:shell" label="sec:shell"></span> <span id="sec:actual-orbit" label="sec:actual-orbit"></span>

<div id="res:lcm" class="proposition">

**Proposition 6** (the running least common multiple). *Let $`p,q,r`$ be pairwise distinct primes and $`x\ge1`$. Then the running LCM equals the three-prime height: $`\operatorname{L}(x)=\operatorname{H}(x)`$.*

</div>

Lean: [running lcm real cutoff exact](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperCompleteR20/RealCutoffs.lean#L49).

<div class="proof">

*Proof.* Every smooth $`n\le x`$ has prime exponents bounded by the corresponding integer logarithms, so $`n\mid\operatorname{H}(x)`$. Conversely the three maximal pure powers occur among those smooth numbers; their product divides the running LCM because they are pairwise coprime. ◻

</div>

The inequalities $`x/p<p^{\lfloor\log_p x\rfloor}\le x`$ for each of the three primes also give
``` math
\begin{equation}
\label{res:cube}
 x^3/(pqr)<\operatorname{H}(x)\le x^3.
\end{equation}
```

<div id="res:cell" class="proposition">

**Proposition 7** (cells and jumps). *The running LCM is constant when the three integer logarithms are constant. A jump in exactly one logarithm multiplies it by the corresponding prime. The first $`n`$ positive powers of each prime, together with $`1`$, form $`3n+1`$ distinct points.*

</div>

Lean: [real prefix lcm eq of same log cell](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperCompleteR20/RealCutoffs.lean#L65), [real prefix lcm jump first](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperCompleteR20/RealCutoffs.lean#L87), [real prefix lcm jump second](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperCompleteR20/RealCutoffs.lean#L117), [real prefix lcm jump third](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperCompleteR20/RealCutoffs.lean#L129), and 1 further declaration in the [coverage section of the companion record](../mirror/erdos269-running-lcm-reasoning-surface.pdf#nameddest=coverage).

<div class="proof">

*Proof.* The first two claims follow from the height formula. Positive powers of different primes cannot coincide, by unique factorisation, and none is $`1`$. ◻

</div>

For $`(p,q,r)=(2,3,5)`$, the smooth numbers $`5`$ and $`6`$ have the same running LCM, $`60`$. They contribute $`2/60`$ to the repeated sum, whereas the height $`60`$ contributes only $`1/60`$ to the distinct-height sum. The next identity retains this multiplicity when equal heights are grouped.

<div id="res:fibre-prop" class="proposition">

**Proposition 8** (grouping terms with the same height). *For a finite exponent box $`\mathcal B`$, set $`F(H)=\{(i,j,k)\in\mathcal B:\operatorname{H}(p^iq^jr^k)=H\}`$. Then
``` math
\begin{equation}
\label{res:fibre}
 \sum_{(i,j,k)\in\mathcal B}\operatorname{K}(i,j,k)=\sum_H\frac{\#F(H)}H.
\end{equation}
```*

</div>

Lean: [finite smooth kernel sum grouped by height](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L407).

<div class="proof">

*Proof.* Each term in $`F(H)`$ equals $`1/H`$. The multiplicities remain present in every subsequent infinite sum. ◻

</div>

From now on let $`P=\{2,3,5\}`$ and $`S=\mathcal R_P`$. For $`a\ge0`$ define
``` math
s_a=\sum_{\substack{x\text{ smooth}\\2^a\le x<2^{a+1}}}\frac1{\operatorname{H}(x)},
 \quad T_a=\sum_{j\ge0}s_{a+j},\quad
 h_a=\frac{\operatorname{H}(2^a)}2,\quad X_a=h_aT_a.
```
The half-height $`h_a`$ clears the finite prefix: for $`a\ge1`$ and smooth $`x<2^a`$, the exponent of $`2`$ in $`\operatorname{H}(x)`$ is at most $`a-1`$, so $`\operatorname{H}(x)\mid\operatorname{H}(2^a)/2`$. This is why we omit the final factor $`2`$. Here $`h_0=1/2`$; only for $`a\ge1`$ is $`h_a`$ an integer. Define
``` math
\begin{equation}
\label{eq:actual-digit}
 b_a=\frac{\operatorname{H}(2^{a+1})}{\operatorname{H}(2^a)},\qquad
 m_a=\sum_{\substack{x\text{ smooth}\\2^a\le x<2^{a+1}}}
       \frac{\operatorname{H}(2^{a+1})}{2\operatorname{H}(x)}.
\end{equation}
```

<div id="res:dyadic-alphabet" class="lemma">

**Lemma 9** (integer coefficients and four possible bases). *For every $`a\ge0`$, $`m_a`$ is a positive integer and $`b_a\in\{2,6,10,30\}`$. The word “numerator” does not impose the positional-digit restriction $`m_a<b_a`$; that restriction need not hold.*

</div>

Lean: [dyadic alphabet whole](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperCompleteR20/DyadicAlphabetWhole.lean#L19).

<div class="proof">

*Proof.* If $`x<2^{a+1}`$, the exponent of $`2`$ in $`\operatorname{H}(x)`$ is at most $`a`$, while the other exponents are bounded by those of $`\operatorname{H}(2^{a+1})`$. Hence $`2\operatorname{H}(x)\mid\operatorname{H}(2^{a+1})`$. Each summand is an integer, and the shell contains $`2^a`$. Between consecutive powers of $`2`$ there is at most one power of $`3`$ and at most one power of $`5`$: successive powers of either odd prime have ratio greater than two. These factors, when present, and the factor $`2`$ at the right endpoint give the four possible bases. ◻

</div>

In the shell $`[2,4)`$ the terms $`1/2`$ and $`1/6`$, with $`h_2=b_1=6`$, give $`m_1=4`$ and the recurrence $`X_2=6X_1-4`$. The shell $`[16,32)`$ shows why these numerators are not positional digits: $`m_4=65>b_4=30`$. The companion computes the carried digits separately.

<div id="res:actual-orbit" class="proposition">

**Proposition 10** (the tail recurrence and a quadratic bound). *The series defining $`S,T_a`$ converge. For every $`a\ge0`$,
``` math
X_{a+1}=b_aX_a-m_a,\qquad
 0<X_a\le\frac{8640}{343}(a+1)^2<90(a+1)^2.
```
For every integer $`B\ge1`$, either some $`BX_a`$ is integral and all later states are integral, or $`\operatorname{dist}(BX_a,\mathbb Z)\ge1/31`$ at arbitrarily large indices.*

</div>

Lean: [short actual orbit](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperR7SeriesIdentification.lean#L168).

<div class="proof">

*Proof.* For each pair of exponents of $`3`$ and $`5`$, at most one exponent of $`2`$ places the smooth integer in $`[2^a,2^{a+1})`$. The two odd-prime exponents lie between $`0`$ and $`a`$, giving at most $`(a+1)^2`$ terms. By <a href="#res:cube" data-reference-type="eqref" data-reference="res:cube">[res:cube]</a>, $`s_a\le30(a+1)^2/8^a`$. Since $`h_a\le8^a/2`$ and $`a+j+1\le(a+1)(j+1)`$ for $`a,j\ge0`$, summing the later shells gives
``` math
X_a\le15(a+1)^2\sum_{j\ge0}\frac{(j+1)^2}{8^j}
      =\frac{8640}{343}(a+1)^2.
```
This proves convergence and the bound. Splitting the first shell gives the recurrence because $`m_a=h_{a+1}s_a`$ and $`h_{a+1}=b_ah_a`$. If all sufficiently late distances are strictly below $`1/31`$, write $`BX_a=z_a+e_a`$ with $`z_a\in\mathbb Z`$ and $`|e_a|<1/31`$. Since $`Bm_a`$ is integral, $`e_{a+1}-b_ae_a`$ is an integer of absolute value less than $`(1+b_a)/31\le1`$, so $`e_{a+1}=b_ae_a`$. The lower bound $`b_a\ge2`$ forces this bounded error to vanish; integrality then propagates by the recurrence. ◻

</div>

The identity $`S/2=\sum_{a\ge0}m_a/(b_0\cdots b_a)`$ places the recurrence in the setting of Cantor series. The classical criteria of Erdős–Straus \[erdosstraus1974, Theorem 2.1\] and Hančl–Tijdeman \[hancltijdeman2004, Theorem 3.1\] require $`m_a/(b_{a-1}b_a)\to0`$. That hypothesis fails here: the numerators grow quadratically while the bases are bounded. The companion’s Section 6 proves the growth assertion and gives the precise carry conditions. The argument below instead uses the recurrence and the proved bound $`90B(a+1)^2`$ directly.

<div id="res:denominator-reduction" class="theorem">

**Theorem 11** (rationality gives positive integer tails). *If $`S=A/D`$ in lowest terms, where $`D=2^u3^v5^wB`$ and $`\gcd(B,30)=1`$, then for every $`a\ge a_0=u+1+2v+3w`$,
``` math
d_a=BX_a\in\mathbb Z_{>0},\qquad
 d_{a+1}=b_ad_a-Bm_a,\qquad d_a\le90B(a+1)^2.
```*

</div>

Lean: [short fixed split bridge](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperR7RationalBridge.lean#L80).

<div class="proof">

*Proof.* For $`a\ge1`$, every $`\operatorname{H}(x)`$ with $`x<2^a`$ divides $`h_a`$. Subtracting the finite prefix therefore gives
``` math
\begin{equation}
\label{eq:prefix-lattice}
 X_a=h_aS-\sum_{\substack{x\text{ smooth}\\x<2^a}}
                  \frac{h_a}{\operatorname{H}(x)},
 \qquad
 \sum_{\substack{x\text{ smooth}\\x<2^a}}
                  \frac{h_a}{\operatorname{H}(x)}\in\mathbb Z.
\end{equation}
```
The exponent of $`2`$ in $`h_a`$ is $`a-1`$. Moreover $`a\ge2v`$ gives $`2^a\ge3^v`$, and $`a\ge3w`$ gives $`2^a\ge5^w`$. Thus $`2^u3^v5^w\mid h_a`$ after the stated onset, and $`BX_a`$ differs from $`h_aA/(2^u3^v5^w)`$ by an integer and is therefore integral. Positivity, the recurrence and the bound follow from Proposition <a href="#res:actual-orbit" data-reference-type="ref" data-reference="res:actual-orbit">10</a>. ◻

</div>

Every positive denominator splits in the required way: $`B`$ is what remains after removing all factors $`2`$, $`3`$ and $`5`$. For example, a hypothetical reduced denominator $`2^3 3^2 5\cdot7`$ would give $`B=7`$; the next result gives the first integral $`7X_a`$ at $`a=4`$, whereas the sufficient bound above gives $`a_0=11`$.

<div id="res:exact-onset" class="corollary">

**Corollary 12** (the first index at which the denominator clears). *Under the same lowest-terms hypothesis, put $`M=2^u3^v5^w`$ and let $`\operatorname{den}`$ denote the positive reduced denominator. For $`a\ge1`$,
``` math
\operatorname{den}(BX_a)=\frac{M}{\gcd(M,h_a)}.
```
Consequently $`BX_a`$ is integral exactly when $`2^a\ge\max(2^{u+1},3^v,5^w)`$. The first such $`a`$ can be found by integer comparisons, without logarithmic rounding.*

</div>

Lean: [exact denominators and minimal clearing](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperExactDenominatorR13.lean#L334), [scaled state is integer iff first clearing index le](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperExactDenominatorR13.lean#L309), [clearing condition iff max](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperExactDenominatorR13.lean#L166).

<div class="proof">

*Proof.* By <a href="#eq:prefix-lattice" data-reference-type="eqref" data-reference="eq:prefix-lattice">[eq:prefix-lattice]</a>, $`BX_a`$ differs from $`h_aA/M`$ by an integer. Since $`\gcd(A,M)=1`$, reducing that fraction gives the displayed denominator. The three divisibility conditions for $`h_a`$ are precisely the three inequalities stated above. ◻

</div>

<a id="sec:escape"></a>

# A window test and the remaining arithmetic

<span id="sec:open" label="sec:open"></span> Two steps of the recurrence already show the finite data we need:
``` math
X_{\ell+2}=b_{\ell+1}b_\ell X_\ell
             -(b_{\ell+1}m_\ell+m_{\ell+1}).
```
If $`BX_\ell`$ is an integer, this identity determines the residue of $`BX_{\ell+2}`$ modulo the product of the two bases. We will compare the least positive representative of that residue with the upper bound for the endpoint tail.

For a window starting at $`\ell\ge0`$ and having $`h\ge0`$ steps, define its product of bases and accumulated numerator from <a href="#eq:actual-digit" data-reference-type="eqref" data-reference="eq:actual-digit">[eq:actual-digit]</a> by
``` math
W_{\ell,0}=1,\quad F_{\ell,0}=0,\qquad
 W_{\ell,h+1}=b_{\ell+h}W_{\ell,h},\quad
 F_{\ell,h+1}=b_{\ell+h}F_{\ell,h}+m_{\ell+h}.
```
Induction on $`h`$ gives
``` math
\begin{equation}
\label{eq:actual-tail}
 X_{\ell+h}=W_{\ell,h}X_\ell-F_{\ell,h}.
\end{equation}
```
For integers $`W\ge1`$ and $`t`$, define $`\operatorname{lpr}_W(t)=1+((t-1)\bmod W)`$, using a remainder in $`\{0,\ldots,W-1\}`$. Thus a zero residue is represented by $`W`$, not $`0`$. Throughout this section use the upper bound
``` math
\begin{equation}
\label{eq:actual-bound}
 K(B,a)=90B(a+1)^2.
\end{equation}
```

<div id="res:consumer" class="lemma">

**Lemma 13** (least positive residues). *If $`d`$ is a positive integer with $`d\le K`$ and $`d\equiv -BF\pmod W`$, where $`W\ge1`$, then $`\operatorname{lpr}_W(-BF)\le K`$.*

</div>

Lean: [paper finite endpoint obstruction](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperR7BasicAssembly.lean#L138).

<div class="proof">

*Proof.* Every positive representative of the residue is at least its least positive representative, so $`\operatorname{lpr}_W(-BF)\le d\le K`$. ◻

</div>

For example, the window starting at $`\ell=1`$ with length $`6`$ has $`W_{1,6}=648000`$ and $`F_{1,6}=524431`$. At $`B=1`$ its least positive residue is $`123569`$, exceeding $`K(1,7)=5760`$. This rules out an integral $`X_1`$, but not a rational denominator that would clear only at a later index. The theorem therefore asks for windows beyond every prescribed starting index, as well as for every eligible denominator.

<div id="res:windowconsumer" class="theorem">

**Theorem 14** (a residue criterion for irrationality). *The number $`S`$ is irrational if and only if
``` math
\begin{equation}
\label{eq:escape}
 \begin{gathered}
 \text{for every }B\ge1\text{ with }\gcd(B,30)=1
 \text{ and every }a_0\ge1,\\
 \text{there are }\ell\ge a_0,\ h\ge1\text{ such that}
 \operatorname{lpr}_{W_{\ell,h}}(-BF_{\ell,h})>K(B,\ell+h).
 \end{gathered}
\end{equation}
```*

</div>

Lean: [short window equivalence](https://github.com/wcook04/plectis-erdos/blob/a25cb360bef8dd818dde14b5fb752244304af354/lean/ErdosProblems/Erdos269/PaperR7WindowResults.lean#L51).

<div class="proof">

*Proof.* Assume <a href="#eq:escape" data-reference-type="eqref" data-reference="eq:escape">[eq:escape]</a> and suppose $`S`$ is rational. Theorem <a href="#res:denominator-reduction" data-reference-type="ref" data-reference="res:denominator-reduction">11</a> supplies a positive integral carry $`d_a=BX_a`$ after its onset. Choose a window in <a href="#eq:escape" data-reference-type="eqref" data-reference="eq:escape">[eq:escape]</a> beyond that onset. Equation <a href="#eq:actual-tail" data-reference-type="eqref" data-reference="eq:actual-tail">[eq:actual-tail]</a> gives $`d_{\ell+h}\equiv-BF_{\ell,h}\pmod{W_{\ell,h}}`$, contradicting Lemma <a href="#res:consumer" data-reference-type="ref" data-reference="res:consumer">13</a> and the upper bound.

Conversely, let $`S`$ be irrational and fix $`B,\ell\ge1`$. Equation <a href="#eq:prefix-lattice" data-reference-type="eqref" data-reference="eq:prefix-lattice">[eq:prefix-lattice]</a> makes $`BX_\ell`$ nonintegral. Put $`\delta=\lceil BX_\ell\rceil-BX_\ell\in(0,1)`$. Since $`W_{\ell,h}\ge2^h`$ and $`X_{\ell+h}=O((\ell+h+1)^2)`$, for all sufficiently large $`h`$ the number $`\delta+BX_{\ell+h}/W_{\ell,h}`$ lies in $`(0,1)`$. The window identity shows that the integer $`\lceil BX_\ell\rceil W_{\ell,h}-BF_{\ell,h}`$ lies strictly between $`0`$ and $`W_{\ell,h}`$ and is congruent to $`-BF_{\ell,h}`$. Hence
``` math
\operatorname{lpr}_{W_{\ell,h}}(-BF_{\ell,h})
 =\delta W_{\ell,h}+BX_{\ell+h}.
```
Its exponentially growing first term eventually exceeds $`K(B,\ell+h)`$. This proves <a href="#eq:escape" data-reference-type="eqref" data-reference="eq:escape">[eq:escape]</a>, in fact from each fixed start. ◻

</div>

The proved bound $`90B(a+1)^2`$ controls every positive integral $`BX_a`$ that rationality would force. Polynomial growth alone does not suffice: the zero bound would make the residue inequality automatic. The companion, Section 7, treats smaller and more general bounds. No finite search establishes the unbounded quantifiers in <a href="#eq:escape" data-reference-type="eqref" data-reference="eq:escape">[eq:escape]</a>.

The remaining task has the following three equivalent formulations.

<div class="problem">

**Problem 15** (the repeated three-prime target). Prove that $`S=\mathcal R_{\{2,3,5\}}`$ is irrational.

</div>

<div id="prob:tails269" class="problem">

**Problem 16** (no reduced tail is an integer). Prove that for every $`a\ge1`$ and every integer $`B\ge1`$ coprime to $`30`$,
``` math
\begin{equation}
\label{eq:tail-nonintegrality}
 BX_a\notin\mathbb Z.
\end{equation}
```

</div>

<div id="prob:producer" class="problem">

**Problem 17** (residue inequalities after every starting index). Prove <a href="#eq:escape" data-reference-type="eqref" data-reference="eq:escape">[eq:escape]</a>.

</div>

Indeed, one integral scaled tail makes $`S`$ rational by <a href="#eq:prefix-lattice" data-reference-type="eqref" data-reference="eq:prefix-lattice">[eq:prefix-lattice]</a>, whereas denominator clearing gives such tails from a rational $`S`$. Theorem <a href="#res:windowconsumer" data-reference-type="ref" data-reference="res:windowconsumer">14</a> supplies the third equivalence. These arithmetic assertions remain unproved. The companion’s finite certificate (Section 8) and comparisons with other approaches (Section 9) are supplementary, not premises of this argument.

<a id="statements-and-declarations"></a>

## Statements and declarations

<a id="proof-sources."></a>

#### Proof sources.

The two-prime deduction uses an external transcendence theorem and is not formalised here. Fan’s priority is retained from the supplied forum record; the live thread and catalogue could not be rechecked for this revision. The formal sources for the rank theorem and the tail recurrence are listed below. The supplied `LEAN_INDEX.json` identifies the public snapshot as `6b78209ab63a8c643281115f8628a3be79ff7ec7` and marks selected declarations `ci_checked`. Its recorded successful compilation is at an earlier commit; the build step in the pinned run was skipped. This revision reports that evidence, not a fresh compilation of the snapshot. The separate Palomar release at `52f29ad1` selects the arbitrary-order uniform-minor and non-separation statements, not just the $`2\times2`$ example.

The finite cut-rank proposition is the checked declaration [finite cut rank](https://github.com/wcook04/plectis-erdos/blob/d11bd0b16f2c0b68d722777762ebbd4f96a12db8/lean/ErdosProblems/Erdos269/PaperR7FiniteCutRank.lean#L182). Its column-range hypothesis permits repeated columns and arbitrary column order. The modular-minor corollary is the checked declaration [uniform modular minors](https://github.com/wcook04/plectis-erdos/blob/d11bd0b16f2c0b68d722777762ebbd4f96a12db8/lean/ErdosProblems/Erdos269/PaperR7ModularMinors.lean#L133). There the injective maps are chosen before the universal quantifiers over $`B`$ and $`k`$, and the modulus is assumed at least $`2`$ and coprime to $`30`$. Both modules compiled under Lean 4.29.1 during this source migration. The exact-denominator corollary has an ordinary proof above. The moving-boundary example is proved in the companion, without a new formalisation claim. No Comparator, Isabelle or NanoDa run was performed for this exposition revision. Neither the listed checks nor the finite calculations certify every sentence of the papers, and none supplies the required windows for every eligible denominator and arbitrarily late starts.

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

The source links retain their original revisions, which can differ from the snapshot in the supplied index. A link identifies a declaration; it does not establish that declaration’s build status at another commit. The companion contains the detailed bounds and supplementary arguments; its source inventory explains the index and normalisation conventions. AI agents carried out most of the research and drafting. The work has not had independent human mathematical review.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.

<a id="acknowledgements."></a>

#### Acknowledgements.

The problem numbering and the historical status snapshot are taken from the Erdős Problems catalogue maintained by Thomas Bloom \[erdosproblems\]. Earlier mathematical inputs are credited at their points of use. We thank Wouter van Doorn for advice on exposition, especially on unexplained terminology, unnecessary notation and the need to explain restrictive hypotheses. His advice concerned a note on Problem #243; he has not reviewed the mathematics of this paper.

<a id="app:sources"></a>

# Guide to the formal sources

There are two separate arguments. The rank proof uses the height formula, row and column rescaling, and a threshold determinant. The arithmetic argument uses the shell coefficients, the tail recurrence, denominator clearing and least positive residues. The table identifies the relevant Lean modules. Declaration names appear only in this source guide and the index that follows; the links preserve the revisions used in the original note.

<div class="center">

| Result | Source and scope |
|:---|:---|
| Kernel rank | `KernelCarryRank`: arbitrary-order uniform minors and no finite rational separation; also selected in the Palomar release. |
| Tail recurrence | `DyadicShellSummability`, `RationalityCarryBridge`: summable tails and denominator clearing, not merely an abstract recurrence. |
| Quadratic bounds | `PaperR8RankMajorant` and `ActualSharpTailMajorantR10`: the companion’s two bounds in the sum of the boundary exponents, the smaller using the order of the jumps. |
| Residue equivalence | `CofinalWindowEscapeEquivalence` and `R12/OcticWindowBand`: the residue contradiction and equivalence with irrationality, not a proof of the required unbounded window existence. |
| External input | Bugeaud–Laurent and Loxton–van der Poorten for the two-prime theorem; no Lean value theorem claimed. |

</div>

The public index supplied for this revision identifies commit `6b78209ab63a8c643281115f8628a3be79ff7ec7`. The links below still use the note’s original commit, not that newer snapshot. A source location, a successful build, a selected Comparator statement and an axiom audit establish different things; none substitutes for the others.

<a id="scope-of-the-supplementary-literature."></a>

#### Scope of the supplementary literature.

The companion develops the comparisons omitted from the main argument. Its Section 5 relates the bounded-ratio argument to Erdős–Taylor \[erdostaylor1957, Theorem 1, p. 600\] and Fan \[fan2026strongly, Lemma 3.1, p. 7\]; Section 6 compares the exact carry restrictions and polynomial-radix assumptions of Hančl–Tijdeman \[hancltijdeman2008, Theorems 2.2, 3.1 and 4.2\]. The Isabelle development of Koutsoukou-Argyraki and Li \[afperdosstraus2020\] verifies classical criteria, not the present series.

Section 9 of the companion separates the finite-difference hypotheses of Luca–Ouaknine–Worrell \[lucaouaknineworrell2025, Definition 5, Theorems 6 and 8, Claim 10\] from quadratic growth alone, and checks the obstacles to using the echoing \[kebis2024echoing\], digit-complexity \[adamczewskibugeaud2007, Theorem 1\] and multivariate Mahler \[adamczewskifaverjon2026\] results. These comparisons do not establish the missing hypotheses for $`S`$.

For broader background, the companion distinguishes work on fixed-prime semigroups \[tijdemanmeijer1974; languasco2025\] from other unit-fraction irrationality problems \[kovactao2024\]. No estimate from those papers is used in this note’s counting argument.

<a id="sec:pinned-lean-sources"></a>

# Pinned Lean sources

The following index retains every original declaration link. Line numbers refer to the unchanged commit named by `\commit`, not to the newer source tree supplied with this revision.

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L123)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L179)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L326)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L339)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L352)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L278)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L406)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L699)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L668)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L646)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L31)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L36)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L40)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L46)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L53)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L59)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L77)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L84)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L97)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L110)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L163)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L169)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L191)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L204)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L208)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L219)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L229)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L243)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L249)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L273)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L294)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L305)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L316)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L368)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L373)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L377)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L384)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L430)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L443)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L450)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L458)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L467)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L479)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L487)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L490)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L500)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L509)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L543)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L585)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L629)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L662)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L711)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L26)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L31)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L52)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L71)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L76)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L96)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L110)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L417)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L422)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L455)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L469)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L480)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L548)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L581)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L601)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L612)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L629)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L645)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L721)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L138)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/BoundedRadixTailEscape.lean#L89)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L497)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L109)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L293)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L334)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L150)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L157)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreeChannelBlockRigidity.lean#L59)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L178)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L238)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L289)

- [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L308)

<div class="thebibliography">

99 Paul Erdős and Ronald L. Graham, *Old and New Problems and Results in Combinatorial Number Theory*, Monographies de L’Enseignement Mathématique **28**, L’Enseignement Mathématique (1980), [source](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf). Paul Erdős, *On the irrationality of certain series: problems and results*, in *New Advances in Transcendence Theory*, Cambridge University Press (1988), 102–109, [doi:`10.1017/CBO9780511897184.009`](https://doi.org/10.1017/CBO9780511897184.009). Paul Erdős, *Letter to the Editor*, Fibonacci Quarterly **12**, no. 4 (1974), 335, [source](https://www.fq.math.ca/Scanned/12-4/letter.pdf). Thomas F. Bloom, *Erdős Problem \#269* (2026), [source](https://www.erdosproblems.com/269). Catalogue snapshot cited in the supplied manuscript: 28 July 2026. Yann Bugeaud and Michel Laurent, *Transcendence and continued fraction expansion of values of Hecke–Mahler series*, Acta Arithmetica **209** (2023), 59–90, [doi:`10.4064/aa220323-18-1`](https://doi.org/10.4064/aa220323-18-1); arXiv:[2203.12901](https://arxiv.org/abs/2203.12901). John H. Loxton and Alfred J. van der Poorten, *Arithmetic properties of certain functions in several variables III*, Bulletin of the Australian Mathematical Society **16** (1977), 15–47, [doi:`10.1017/S0004972700022978`](https://doi.org/10.1017/S0004972700022978). Steve Fan, *Comment on Erdős Problem \#269, thread 269, post 7218* (2026), [source](https://www.erdosproblems.com/forum/thread/269#post-7218). 26 June 2026, thread 269, post 7218; priority retained from the supplied record. Paul Erdős and Ernst G. Straus, *On the irrationality of certain series*, Pacific Journal of Mathematics **55**, no. 1 (1974), 85–92, [doi:`10.2140/pjm.1974.55.85`](https://doi.org/10.2140/pjm.1974.55.85). Jaroslav Hančl and Robert Tijdeman, *On the irrationality of Cantor and Ahmes series*, Publicationes Mathematicae Debrecen **65**, no. 3–4 (2004), 371–380, [doi:`10.5486/PMD.2004.3254`](https://doi.org/10.5486/PMD.2004.3254). Paul Erdős and S. James Taylor, *On the set of points of convergence of a lacunary trigonometric series and the equidistribution properties of related sequences*, Proceedings of the London Mathematical Society **s3-7**, no. 1 (1957), 598–615, [doi:`10.1112/plms/s3-7.1.598`](https://doi.org/10.1112/plms/s3-7.1.598). Steve Fan, *Strongly complete sets and a conjecture of Erdős* (2026), [source](https://arxiv.org/abs/2607.14071v1); arXiv:[2607.14071](https://arxiv.org/abs/2607.14071). The cited Lemma 3.1 is in arXiv v1, 15 July 2026. Jaroslav Hančl and Robert Tijdeman, *On the irrationality of polynomial Cantor series*, Acta Arithmetica **133**, no. 1 (2008), 37–52, [doi:`10.4064/aa133-1-3`](https://doi.org/10.4064/aa133-1-3). Florian Luca, Joël Ouaknine and James Worrell, *Transcendence of Hecke–Mahler Series*, Bulletin of the London Mathematical Society **57**, no. 5 (2025), 1360–1368, [doi:`10.1112/blms.70033`](https://doi.org/10.1112/blms.70033); arXiv:[2412.07908](https://arxiv.org/abs/2412.07908). Numbered references use the published article. Pavol Kebis, Florian Luca, Joël Ouaknine, Andrew Scoones and James Worrell, *On Transcendence of Numbers Related to Sturmian and Arnoux-Rauzy Words*, in *51st International Colloquium on Automata, Languages, and Programming (ICALP 2024)*, Leibniz International Proceedings in Informatics **297**, Schloss Dagstuhl – Leibniz-Zentrum für Informatik (2024), 144:1–144:15, [doi:`10.4230/LIPIcs.ICALP.2024.144`](https://doi.org/10.4230/LIPIcs.ICALP.2024.144). Robert Tijdeman and H. G. Meijer, *On integers generated by a finite number of fixed primes*, Compositio Mathematica **29**, no. 3 (1974), 273–286, [source](https://www.numdam.org/article/CM_1974__29_3_273_0.pdf). Alessandro Languasco, Florian Luca, Pieter Moree and Alain Togbé, *Sequences of integers generated by two fixed primes*, Abhandlungen aus dem Mathematischen Seminar der Universität Hamburg **95** (2025), 123–148, [doi:`10.1007/s12188-025-00293-9`](https://doi.org/10.1007/s12188-025-00293-9); arXiv:[2309.12806](https://arxiv.org/abs/2309.12806). Vjekoslav Kovač and Terence Tao, *On several irrationality problems for Ahmes series*, Acta Mathematica Hungarica **175** (2025), 572–608, [doi:`10.1007/s10474-025-01528-0`](https://doi.org/10.1007/s10474-025-01528-0); arXiv:[2406.17593](https://arxiv.org/abs/2406.17593). Angeliki Koutsoukou-Argyraki and Wenda Li, *Irrationality Criteria for Series by Erdős and Straus*, Archive of Formal Proofs (2020), [source](https://isa-afp.org/entries/Irrational_Series_Erdos_Straus.html). Entry dated 12 May 2020; proof-document version consulted: 6 February 2026. Boris Adamczewski and Yann Bugeaud, *On the complexity of algebraic numbers I. Expansions in integer bases*, Annals of Mathematics **165**, no. 2 (2007), 547–565, [doi:`10.4007/annals.2007.165.547`](https://doi.org/10.4007/annals.2007.165.547). Boris Adamczewski and Colin Faverjon, *Mahler’s method in several variables and finite automata*, Annals of Mathematics **204**, no. 2 (2026), 455–533, [doi:`10.4007/annals.2026.204.2.1`](https://doi.org/10.4007/annals.2026.204.2.1). Online 13 September 2026; locators here refer to the [68-page author manuscript](https://faverjon.perso.math.cnrs.fr/AdamczewskiFaverjon_MahlerFiniteAutomata.pdf).

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.
