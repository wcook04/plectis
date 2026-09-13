<a id="erdos-269-three-prime-running-lcm"></a>

# No Finite Separable Representation at Three Prime Generators

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

For three pairwise distinct primes, the reciprocal running-LCM kernel has nonsingular minors of every order, with one choice of indices valid in every third-coordinate layer. Dividing out row and column powers leaves a binary carry whose consecutive threshold columns differ on disjoint intervals. This gives both arbitrary-order non-separability and the exact rank of every finite sample. Steve Fan posted the two-prime factorisation, reduction and transcendence conclusion first (erdosproblems.com/269, 26 June 2026, post-7218). This paper records that argument as an ordinary deduction from Bugeaud–Laurent and does not claim priority or a Lean theorem for the two-prime case. The repeated three-prime irrationality question remains open.

<a id="sec:problem"></a>

# Introduction

Let $`P`$ be a finite set of at least two primes and $`\mathcal S_P`$ its positive smooth integers. Put
``` math
\operatorname{L}(x)=\operatorname{lcm}\{u\in\mathcal S_P:u\le x\},\qquad
 \mathcal R_P=\sum_{u\in\mathcal S_P}\operatorname{L}(u)^{-1}.
```
Erdős asks whether $`\mathcal R_P`$ is irrational \[erdosgraham1980, p. 65\]\[erdos1988, p. 106\]. For $`P=\{p,q,r\}`$, define
``` math
\operatorname{H}(x)=p^{\lfloor\log_p x\rfloor}
 q^{\lfloor\log_q x\rfloor}r^{\lfloor\log_r x\rfloor},\qquad
 \operatorname{K}(i,j,k)=\operatorname{H}(p^iq^jr^k)^{-1}.
```
Prime-power divisibility gives $`\operatorname{L}=\operatorname{H}`$ (Proposition <a href="#res:lcm" data-reference-type="ref" data-reference="res:lcm">6</a>).

With two primes, the corresponding kernel factors into a function of each exponent separately, reducing the double sum to a product. The first question at three primes is whether finitely many such products still suffice. Theorem <a href="#res:infinite-rank" data-reference-type="ref" data-reference="res:infinite-rank">1</a> rules this out: one floor carry survives after all row and column factors have been removed. We first explain that obstruction, then recover the two-prime comparison, and finally identify the arithmetic of the actual three-prime tails. The last step is necessary because the rank of a kernel does not determine the irrationality of its sum.

<a id="sec:rank"></a>

# The binary carry and arbitrary-order rank

<div id="res:infinite-rank" class="theorem">

**Theorem 1** (arbitrary-order non-separability). *Let $`p,q,r`$ be primes with $`p\ne q`$, $`p\ne r`$ and $`q\ne r`$. For every $`n\ge0`$ there are injective maps $`I,J:\{0,\ldots,n-1\}\to\mathbb{N}`$ such that, for every $`k\ge0`$,
``` math
\det\bigl(\operatorname{K}(I(a),J(b),k)\bigr)_{0\le a,b<n}\ne0.
```
Consequently, for no finite $`d`$ do there exist rational-valued functions $`f_\ell(i)`$ and $`G_\ell(j,k)`$, $`0\le\ell<d`$, satisfying
``` math
\operatorname{K}(i,j,k)=\sum_{\ell<d}f_\ell(i)G_\ell(j,k)
 \qquad\hbox{for all }i,j,k.
```*

</div>

<div class="proof">

*Proof.* Put $`c=r^{-1}`$, $`x_i=\{i\log_r p\}`$ and $`y_j=\{j\log_r q\}`$. Splitting the floor exponents gives
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
Both factors are positive. Distinct primes make $`\log_r p`$ and $`\log_r q`$ irrational, so each individual rotation is dense. No joint density of $`(x_i,y_j)`$ is needed. For $`n\ge1`$, use density of $`(x_i)`$ to choose distinct row indices with $`0<x_{I(0)}<\cdots<x_{I(n-1)}<1`$. Now put $`s_b=1-y_{J(b)}`$. Density of $`(y_j)`$ lets us choose

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
Indeed, subtracting each preceding row from the next, working upwards from the last row, leaves diagonal entries $`c,c-1,\ldots,c-1`$. Before normalisation, the determinant is this nonzero number times
``` math
\prod_{a<n}U_{I(a)}(k)^{-1}\prod_{b<n}V_{J(b)}(k)^{-1}.
```
The factors are nonzero, and the same $`I,J`$ work for every $`k`$. The empty minor for $`n=0`$ equals $`1`$.

For the final assertion, suppose a separation with $`d`$ summands existed and fix any $`k`$. On the rows $`I(0),\ldots,I(d)`$ and columns $`J(0),\ldots,J(d)`$ its matrix would be the product of the $`(d+1)\times d`$ matrix $`(f_\ell(I(a)))_{a,\ell}`$ and the $`d\times(d+1)`$ matrix $`(G_\ell(J(b),k))_{\ell,b}`$. Its rank would be at most $`d`$, so its determinant would vanish, contrary to the minor just constructed. ◻

</div>

The two clauses are the Lean declarations [uniform nonsingular minors](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos269/KernelCarryRank.lean#L376) and [no finite separation](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos269/KernelCarryRank.lean#L388). Those declarations require $`p\ne r`$ and $`q\ne r`$, but not $`p\ne q`$. The theorem above keeps pairwise distinctness because it is stated for a three-prime set; allowing $`p=q`$ gives an extension of the abstract indexed kernel, not a new three-prime case of the running-LCM problem.

<div id="res:admissible-modular-minors" class="corollary">

**Corollary 2** (the same minors modulo every admissible denominator). *For $`(p,q,r)=(2,3,5)`$ and every $`n\ge1`$, there are injective maps $`I,J:\{0,\ldots,n-1\}\to\mathbb{N}`$, chosen independently of $`B`$ and $`k`$, such that for every $`B\ge2`$ coprime to $`30`$ and every $`k\ge0`$, the selected $`n\times n`$ kernel matrix has unit determinant over $`\mathbb Z/B\mathbb Z`$, with each reciprocal prime power interpreted by its modular inverse.*

</div>

<div class="proof">

*Proof.* Choose the maps from Theorem <a href="#res:infinite-rank" data-reference-type="ref" data-reference="res:infinite-rank">1</a>. Every row and column factor is a unit modulo $`B`$. The normalised determinant is $`5^{-1}(-4/5)^{n-1}`$, also a unit. ◻

</div>

The statement is [admissible modular minors](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos269/PaperR7ModularMinors.lean#L133).

<div id="res:rank" class="example">

**Example 3**. For $`(p,q,r)=(2,3,5)`$, the leading two-by-two determinant is $`-1/15`$: its four entries are $`1,1/6,1/2,1/60`$, so it equals $`1/60-1/12`$.

</div>

The four entries and the determinant are [two by two fixture](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos269/PaperR7BasicAssembly.lean#L102).

<a id="the-indices-must-be-selected."></a>

#### The indices must be selected.

The leading $`4\times4`$ block at $`\{2,3,5\}`$ is singular:
``` math
\operatorname{K}(3,j,0)=\frac1{120}\operatorname{K}(0,j,0)\qquad(0\le j<4).
```
These equalities follow by evaluating the height at $`3^j`$ and $`8\cdot3^j`$. At $`j=4`$ the difference is $`-1/19440000`$. Thus the leading minors do not supply the arbitrary-order theorem.

<div id="res:finite-cut-rank" class="proposition">

**Proposition 4** (finite sampled cut rank). *Let $`m\ge1`$ and let $`c`$ lie in a field with $`c\ne 0,1`$. For $`0\le k\le m`$ write $`v_k`$ for the length-$`m`$ column with a $`1`$ in each of the first $`k`$ coordinates and $`c`$ thereafter. A matrix whose distinct columns are $`v_k`$ for $`k`$ in a nonempty set $`E`$ has rank $`|E|-\mathbf 1_{\{0,m\}\subseteq E}`$.*

</div>

<div class="proof">

*Proof.* List $`E=\{k_1<\cdots<k_t\}`$. The $`t-1`$ differences $`v_{k_{j+1}}-v_{k_j}=(1-c)\mathbf 1_{\{k_j,\ldots,k_{j+1}-1\}}`$ have disjoint nonempty supports, hence are linearly independent. If $`k_1>0`$ or $`k_t<m`$, their union misses a coordinate where $`v_{k_1}`$ is nonzero, so the rank is $`t`$. If $`k_1=0`$ and $`k_t=m`$, then $`v_0=c\,\mathbf 1`$ lies in the span of the differences (their sum is $`(1-c)\mathbf 1`$), so the rank is $`t-1`$. ◻

</div>

The statement is [rank cut matrix](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos269/PaperR7FiniteCutRank.lean#L182).

The formula classifies every finite sampled kernel rank after the row and column factors of Theorem <a href="#res:infinite-rank" data-reference-type="ref" data-reference="res:infinite-rank">1</a>, independently of the third coordinate. An exact logarithm-free algorithm orders the rationals $`p^i/r^{\lfloor\log_r p^i\rfloor}`$, counts those strictly below each $`r^{\lfloor\log_r q^j\rfloor+1}/q^j`$, and applies the displayed correction. Direct elimination on the $`\{2,3,5\}`$ kernel agrees with the formula through order $`24`$; larger leading ranks recorded with the accompanying checker use the formula and exact integer phase comparisons.

<a id="the-norm-matters."></a>

#### The norm matters.

For the infinite normalised carry matrix,
``` math
\inf_{F\text{ of finite separated rank}}\|C-F\|_\infty=(1-c)/2.
```
Distinct columns are exactly $`1-c`$ apart in the supremum norm, by density of the row phases. An approximation below half that distance would give infinitely many bounded, uniformly separated columns in a finite-dimensional space. Compactness excludes this. The constant $`(1+c)/2`$ attains the bound.

Finite restrictions have a different behaviour. At $`c=1/5`$,
``` math
T=\begin{pmatrix}1/5&1\\1/5&1/5\end{pmatrix},\qquad
 A=\begin{pmatrix}3/10&9/10\\1/10&3/10\end{pmatrix}
```
satisfy $`\det A=0`$ and $`\|T-A\|_{\max}=1/10<2/5`$. For the original kernel, truncating the first coordinate at $`N`$ gives separated rank at most $`N`$ and
``` math
\|K-K^{(N)}\|_{\ell^1}
 \le\frac{pqr\,p^{-3N}}{(1-p^{-3})(1-q^{-3})(1-r^{-3})}.
```
This follows from $`\operatorname{H}(x)>x^3/(pqr)`$. Thus the infinite uniform obstruction coexists with geometric approximation in the summation norm. The scalar irrationality question requires arithmetic information about the actual multiplicities.

<a id="sec:two-prime"></a>

# The two-prime comparison

For distinct primes $`p<q`$, write $`L_{p,q}(t)=p^{\lfloor\log_p t\rfloor}q^{\lfloor\log_q t\rfloor}`$. Prime-power divisibility identifies this product with the running LCM. Let $`\mathcal R_{p,q}`$ retain every smooth-number multiplicity, and let $`\mathcal D_{p,q}`$ retain the initial value and one reciprocal at each positive pure-power jump. Fan’s argument gives the repeated two-prime factorisation and its quadratic reduction to a single Hecke–Mahler value. The same boundary-channel calculation also yields the de-duplicated affine formula displayed below \[fan2026comment\].

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

<div class="proof">

*Proof.* Set $`x=1/p`$, $`y=1/q`$, $`m_n=\lfloor n\theta\rfloor`$ and $`\delta_n=m_{n+1}-m_n`$. Unique factorisation makes $`\theta`$ irrational, and $`0<\theta<1`$ gives $`\delta_n\in\{0,1\}`$. The initial value and the $`p`$-channel contribute $`A=\sum_{n\ge0}x^ny^{m_n}`$. There is one $`q`$-power between $`p^n`$ and $`p^{n+1}`$ precisely when $`\delta_n=1`$, so the other channel contributes
``` math
B=\sum_{n\ge0}\delta_nx^ny^{m_n+1},\qquad \mathcal D_{p,q}=A+B.
```
All these series converge absolutely. Since $`y^{m_{n+1}}-y^{m_n}=\delta_ny^{m_n}(y-1)`$, shifting the series for $`A`$ gives $`A-1-xA=x(y-1)B/y`$. Therefore
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
Bugeaud and Laurent’s Theorem 1.1 applies to these nonzero algebraic $`x,y`$ \[bugeaudlaurent2023, authors’ Online First PDF, p. 3\]: $`|x|<1`$ and $`|xy^\theta|=p^{-2}<1`$; the zero-shift case goes back to Loxton and van der Poorten \[bugeaudlaurent2023; loxtonvdp1977\]. Thus $`A`$ is transcendental. The displayed affine and quadratic polynomials are nonconstant, so an algebraic value of either would force $`A`$ to be algebraic. ◻

</div>

The two-prime reduction expresses both sums through one value. The third prime leaves the binary carry of Section <a href="#sec:rank" data-reference-type="ref" data-reference="sec:rank">2</a>. Its rank theorem concerns that function; the scalar arithmetic depends on the multiplicities introduced next. The de-duplicated irrationality assertion is historical \[erdos1974letter\].

<a id="sec:lcm"></a>

# Exact multiplicities and normalised tails

<span id="sec:cells" label="sec:cells"></span><span id="sec:fibre" label="sec:fibre"></span><span id="sec:shell" label="sec:shell"></span> <span id="sec:actual-orbit" label="sec:actual-orbit"></span>

<div id="res:lcm" class="proposition">

**Proposition 6** (the running least common multiple). *Let $`p,q,r`$ be pairwise distinct primes and $`x\ge1`$. Then the [smooth-prefix LCM](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L123) equals the three-prime height: $`\operatorname{L}(x)=\operatorname{H}(x)`$.*

</div>

<div class="proof">

*Proof.* Every smooth $`n\le x`$ has prime exponents bounded by the corresponding integer logarithms, so $`n\mid\operatorname{H}(x)`$. Conversely the three maximal pure powers occur among those smooth numbers; their product divides the running LCM because they are pairwise coprime. ◻

</div>

The statement is [smooth prefix lcm equals three-prime height](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L124). The same definition gives
``` math
\begin{equation}
\label{res:cube}
 x^3/(pqr)<\operatorname{H}(x)\le x^3.
\end{equation}
```
Both inequalities are [cubic height bounds](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos269/PaperR7BasicAssembly.lean#L112).

<div id="res:cell" class="proposition">

**Proposition 7** (smooth-prefix LCM cells). *If $`x,y\ge1`$ lie in the same logarithmic cell, then $`\operatorname{L}(x)=\operatorname{L}(y)`$: the [smooth-prefix LCM cell](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L179) is constant. Advancing exactly one logarithm multiplies the running value by the corresponding [first-channel step](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L326), [second-channel step](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L339) or [third-channel step](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L352). The [jump set with the origin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L278), formed from the first $`n`$ positive powers in each channel together with $`1`$, has cardinality $`3n+1`$.*

</div>

<div class="proof">

*Proof.* Cell constancy and the three jump ratios follow from Proposition <a href="#res:lcm" data-reference-type="ref" data-reference="res:lcm">6</a>, since the height depends on $`x`$ only through the three integer logarithms. Within one channel the first $`n`$ positive powers are distinct; across channels a common value would be a positive power of two distinct primes; and $`1`$ is not a positive prime power. ◻

</div>

<div id="res:fibre-prop" class="proposition">

**Proposition 8** (height-fibre regrouping). *If $`F(H)`$ is a height fibre in a finite exponent box $`\mathcal B`$, the [height-fibre regrouping](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L406) gives
``` math
\begin{equation}
\label{res:fibre}
 \sum_{(i,j,k)\in\mathcal B}\operatorname{K}(i,j,k)=\sum_H\frac{\#F(H)}H.
\end{equation}
```*

</div>

<div class="proof">

*Proof.* Each term in $`F(H)`$ equals $`1/H`$. The multiplicities remain present in every subsequent infinite sum. ◻

</div>

The regrouping is [finite smooth kernel sum grouped by height](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L407).

From now on let $`P=\{2,3,5\}`$ and $`S=\mathcal R_P`$. For $`a\ge0`$ define
``` math
s_a=\sum_{\substack{x\text{ smooth}\\2^a\le x<2^{a+1}}}\frac1{\operatorname{H}(x)},
 \quad T_a=\sum_{j\ge0}s_{a+j},\quad
 h_a=\frac{\operatorname{H}(2^a)}2,\quad X_a=h_aT_a.
```
Thus $`T_a`$ is the raw tail and $`X_a`$ its normalised state. The literal radix and forcing digit are
``` math
\begin{equation}
\label{eq:actual-digit}
 b_a=\frac{\operatorname{H}(2^{a+1})}{\operatorname{H}(2^a)},\qquad
 m_a=\sum_{\substack{x\text{ smooth}\\2^a\le x<2^{a+1}}}
       \frac{\operatorname{H}(2^{a+1})}{2\operatorname{H}(x)}.
\end{equation}
```

<div id="res:dyadic-alphabet" class="lemma">

**Lemma 9** (integer forcing and the four radices). *For every $`a\ge0`$, $`m_a`$ is a positive integer and the [four-letter dyadic alphabet](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L699) satisfies $`b_a\in\{2,6,10,30\}`$.*

</div>

<div class="proof">

*Proof.* If $`x<2^{a+1}`$, the two-exponent of $`\operatorname{H}(x)`$ is at most $`a`$, while the other exponents are bounded by those of $`\operatorname{H}(2^{a+1})`$. Hence $`2\operatorname{H}(x)\mid\operatorname{H}(2^{a+1})`$. Each forcing summand is an integer, and the shell contains $`2^a`$. Between consecutive two-powers, [internal-power uniqueness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L668) leaves at most one three-power and at most one five-power. Their optional factors, together with the terminal factor two, give the four radices. ◻

</div>

Both clauses are [literal integer forcing and four radices](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos269/PaperR7ActualOrbit.lean#L48).

<div id="res:actual-orbit" class="proposition">

**Proposition 10** (the actual recurrence and a polynomial bound). *The series defining $`S,T_a`$ converge. For every $`a\ge0`$,
``` math
X_{a+1}=b_aX_a-m_a,\qquad
 0<X_a\le\frac{8640}{343}(a+1)^2<90(a+1)^2.
```
For every integer $`B\ge1`$, either some $`BX_a`$ is integral and all later states are integral, or $`\operatorname{dist}(BX_a,\mathbb Z)\ge1/31`$ at arbitrarily large indices.*

</div>

<div class="proof">

*Proof.* A dyadic shell contains at most one two-exponent for each pair of three- and five-exponents. Each of the latter lies between $`0`$ and $`a`$, so the [quadratic shell bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L646) gives at most $`(a+1)^2`$ terms. By <a href="#res:cube" data-reference-type="eqref" data-reference="res:cube">[res:cube]</a>, $`s_a\le30(a+1)^2/8^a`$. Therefore
``` math
X_a\le15(a+1)^2\sum_{j\ge0}\frac{(j+1)^2}{8^j}
      =\frac{8640}{343}(a+1)^2.
```
This proves convergence and the bound. Splitting the first shell gives the recurrence because $`m_a=h_{a+1}s_a`$ and $`h_{a+1}=b_ah_a`$. All four clauses are [short actual orbit](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos269/PaperR7SeriesIdentification.lean#L168).

Put $`Y_a=BX_a`$. If all sufficiently late distances are strictly below $`1/31`$, write $`Y_a=z_a+e_a`$ with $`z_a\in\mathbb Z`$ and $`|e_a|<1/31`$. Then $`e_{a+1}-b_ae_a`$ is an integer of absolute value less than one, so $`e_{a+1}=b_ae_a`$. The factors $`b_a\ge2`$ force a bounded such error to be zero. An integral state propagates by the integer recurrence. ◻

</div>

The constant above is a simple bound for the cap used below. The stronger source estimate $`\widetilde Q(n)=(1210n^2+9130n+18847)/11979`$ uses the exclusion of three successive two-jumps and has a separate ordinary proof. The present cap suffices for the criterion; the sharper argument belongs in the extended record rather than in this proof.

<div id="res:denominator-reduction" class="theorem">

**Theorem 11** (actual rationality-to-reduced-carry bridge). *If $`S=A/D`$ in lowest terms, where $`D=2^u3^v5^wB`$ and $`\gcd(B,30)=1`$, then for every $`a\ge a_0=u+1+2v+3w`$,
``` math
d_a=BX_a\in\mathbb Z_{>0},\qquad
 d_{a+1}=b_ad_a-Bm_a,\qquad d_a\le90B(a+1)^2.
```*

</div>

<div class="proof">

*Proof.* For $`a\ge1`$, strict boundary clearing gives
``` math
\begin{equation}
\label{eq:prefix-lattice}
 X_a=h_aS-Z_a,\qquad
 Z_a=\sum_{\substack{x\text{ smooth}\\x<2^a}}\frac{h_a}{\operatorname{H}(x)}\in\mathbb Z.
\end{equation}
```
The two-exponent of $`h_a`$ is $`a-1`$. Moreover $`a\ge2v`$ gives $`2^a\ge3^v`$, and $`a\ge3w`$ gives $`2^a\ge5^w`$. Thus $`2^u3^v5^w\mid h_a`$ after the stated onset, and $`BX_a=h_aA/(2^u3^v5^w)-BZ_a`$ is integral. Positivity, the recurrence and the bound follow from Proposition <a href="#res:actual-orbit" data-reference-type="ref" data-reference="res:actual-orbit">10</a>. ◻

</div>

The statement is [short fixed split bridge](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos269/PaperR7RationalBridge.lean#L80).

<a id="sec:escape"></a>

# A window test and the remaining arithmetic

<span id="sec:open" label="sec:open"></span> The actual digits in <a href="#eq:actual-digit" data-reference-type="eqref" data-reference="eq:actual-digit">[eq:actual-digit]</a> define
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
Let $`\operatorname{lpr}_W(t)`$ be the representative in $`\{1,\ldots,W\}`$ of $`t\bmod W`$, representing a zero residue by $`W`$. Throughout this section use the valid cap
``` math
\begin{equation}
\label{eq:actual-bound}
 K(B,a)=90B(a+1)^2.
\end{equation}
```

<div id="res:consumer" class="lemma">

**Lemma 12** (finite endpoint obstruction). *If $`d`$ is a positive integer with $`d\le K`$ and $`d\equiv -BF\pmod W`$, where $`W\ge1`$, then $`\operatorname{lpr}_W(-BF)\le K`$.*

</div>

<div class="proof">

*Proof.* Every positive representative of the residue is at least its least positive representative, so $`\operatorname{lpr}_W(-BF)\le d\le K`$. ◻

</div>

The statement is [finite endpoint obstruction](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos269/PaperR7BasicAssembly.lean#L138).

<div id="res:windowconsumer" class="theorem">

**Theorem 13** (the actual window criterion). *The number $`S`$ is irrational if and only if
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

<div class="proof">

*Proof.* If $`S`$ is rational, Theorem <a href="#res:denominator-reduction" data-reference-type="ref" data-reference="res:denominator-reduction">11</a> supplies a positive integral carry $`d_a=BX_a`$ after its onset. Choose a window in <a href="#eq:escape" data-reference-type="eqref" data-reference="eq:escape">[eq:escape]</a> beyond that onset. Equation <a href="#eq:actual-tail" data-reference-type="eqref" data-reference="eq:actual-tail">[eq:actual-tail]</a> gives $`d_{\ell+h}\equiv-BF_{\ell,h}\pmod{W_{\ell,h}}`$, contradicting Lemma <a href="#res:consumer" data-reference-type="ref" data-reference="res:consumer">12</a> and the valid cap.

Conversely, let $`S`$ be irrational and fix $`B,\ell\ge1`$. Equation <a href="#eq:prefix-lattice" data-reference-type="eqref" data-reference="eq:prefix-lattice">[eq:prefix-lattice]</a> makes $`BX_\ell`$ nonintegral. Put $`\delta=\lceil BX_\ell\rceil-BX_\ell\in(0,1)`$. Since $`W_{\ell,h}\ge2^h`$ and $`X_{\ell+h}=O((\ell+h+1)^2)`$, for all sufficiently large $`h`$ the number $`\delta+BX_{\ell+h}/W_{\ell,h}`$ lies in $`(0,1)`$. The window identity then gives the exact equality
``` math
\operatorname{lpr}_{W_{\ell,h}}(-BF_{\ell,h})
 =\delta W_{\ell,h}+BX_{\ell+h}.
```
Its exponentially growing first term eventually exceeds $`K(B,\ell+h)`$. This proves <a href="#eq:escape" data-reference-type="eqref" data-reference="eq:escape">[eq:escape]</a>, in fact from each fixed start. ◻

</div>

The equivalence, at the literal smooth-number series, is [short window equivalence](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos269/PaperR7WindowResults.lean#L51).

The validity of the cap is needed in the rational direction; an upper polynomial growth condition by itself would not suffice. The zero cap, for example, makes positive-residue escape automatic. The criterion identifies the target in window coordinates. The unresolved point is the source-specific exclusion below.

<div id="prob:tails269" class="problem">

**Problem 14** (exact nonintegrality of every reduced tail). Prove that for every $`a\ge1`$ and every integer $`B\ge1`$ coprime to $`30`$,
``` math
\begin{equation}
\label{eq:tail-nonintegrality}
 BX_a\notin\mathbb Z.
\end{equation}
```

</div>

<div id="prob:producer" class="problem">

**Problem 15** (actual cofinal local-window escape). Prove the displayed quantifier order
``` math
\forall B\ge1\ (\gcd(B,30)=1),\ \forall a_0\ge1,\
 \exists\ell\ge a_0\ \exists h\ge1:\quad
 \operatorname{lpr}_{W_{\ell,h}}(-BF_{\ell,h})
   >K(B,\ell+h).
```

</div>

<div class="problem">

**Problem 16** (function-faithful two-dimensional representation). Express $`\mathcal D_{2,3,5}`$ as a nonconstant algebraic combination of values of a specified two-dimensional Hecke–Mahler, cone-generating or multivariate Mahler function and verify every hypothesis of a published value theorem; or give a conditional theorem under an explicit logarithmic nondegeneracy hypothesis; or prove that the literal series has no representation in the specified finite-dimensional class.

</div>

By <a href="#eq:prefix-lattice" data-reference-type="eqref" data-reference="eq:prefix-lattice">[eq:prefix-lattice]</a>, one integral value would make $`S`$ rational; the bridge proves the reverse implication after clearing its denominator. Thus the pointwise formulation is equivalent to the irrationality question.

<a id="the-information-the-remaining-argument-must-use."></a>

#### The information the remaining argument must use.

The bounded-radix alternative permits the integral branch. Infinite rank and the modular minors of Corollary <a href="#res:admissible-modular-minors" data-reference-type="ref" data-reference="res:admissible-modular-minors">2</a> constrain the kernel, while a scalar argument must also use its exact multiplicities. In the existing three-channel rigidity result, preservation of every complete same-channel block makes a perturbation a difference of three channel potentials. Two zero anchor transitions make that potential constant. A bounded rationalising lift does not automatically supply those unweighted block identities: its actual block defect is weighted. A proof using this route must establish that extra source-faithful condition. The extended record retains the exact countermodels and the other proposed representations at their stated scopes.

<a id="statements-and-declarations"></a>

## Statements and declarations

<a id="proof-sources."></a>

#### Proof sources.

The two-prime argument uses the cited Hecke–Mahler value theorem and is Steve Fan’s; it is not a Lean theorem. The arbitrary-order kernel theorem is proved in the Lean module `KernelCarryRank`: it contains the uniform minors and the exact finite-separation contradiction used above. The literal recurrence and the fixed-split rationality bridge likewise have the named Lean statements linked at their occurrences above. The [source-current validation receipt](https://github.com/wcook04/plectis-erdos/blob/06f57893e0f9c6d80668048f26f096367ae4cfe7/verification/erdos269-wavea-validation.json) byte-matches these modules and records their compilation inside the public recursive import closure. The receipt’s declaration-by-declaration axiom audit concerns the named R12 Wave A results, not these rank declarations. Comparator separately records the finite $`(2,3,5)`$ minor $`-1/15`$, the running-LCM height identity, and a conditional carry-escape consumer; it is not the evidence for the arbitrary-order theorem. The finite cut-rank argument and the modular corollary are proved above; no additional formal verification claim is made for the latter. The actual-series reduction is given; the source-specific cofinal escape remains unproved.

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

Each source link is pinned to its own immutable revision. The exact-reference inventory records those revisions and their bytewise comparison with the current public source commit. The extended reasoning record and the accompanying source retain the detailed shell bounds, finite experiments and alternative representations with their exact hypotheses. Supplied later-source labels and public links remain separate source coordinates.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.

<a id="acknowledgements."></a>

#### Acknowledgements.

The problem numbering and status follow the Erdős Problems catalogue maintained by Thomas Bloom \[erdosproblems\].

<a id="app:sources"></a>

# Guide to the formal sources

The formal sources are recorded by the following per-link immutable revisions.

[](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L31), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L36), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L40), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L46), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L53), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L59), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L77), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L84), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L97), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L110), [smooth-prefix LCM](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L123), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L163), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L169), [smooth-prefix LCM cell](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L179), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L191), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L204), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L208), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L219), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L229), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L243), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L249), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L273), [jump set with the origin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L278), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L294), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L305), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L316), [first-channel step](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L326), [second-channel step](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L339), [third-channel step](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L352), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L368), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L373), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L377), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L384), [height-fibre regrouping](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L406), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L430), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L443), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L450), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L458), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L467), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L479), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L487), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L490), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L500), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L509), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L543), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L585), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L629), [quadratic shell bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L646), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L662), [internal-power uniqueness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L668), [](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L688), [four-letter dyadic alphabet](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L699), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L711), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L26), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L31), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L52), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L71), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L76), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L96), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L110), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L417), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L422), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L455), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L469), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L480), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L548), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L581), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L601), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L612), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L629), [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L645), [smooth lattice value](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L31), [running least common multiple](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L53), [pure-power height](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L36), [lattice kernel](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L40), [smooth prefix index set](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L46), [running-lcm identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L123), [divisibility into the height](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L77), [first](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L84), [second](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L97), [third](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L110), [cubic majorant](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L430), [cell relation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L163), [cell constancy of the running value](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L179), [cell constancy of the height](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L169), [cell constancy of the kernel](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L191), [first](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L326), [second](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L339), [third](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L352), [first height step](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L294), [second](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L305), [third](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L316), [positive jump count](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L249), [jump count with the origin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L278), [channel cardinality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L208), [channel disjointness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L229), [exclusion of the origin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L219), [positive power sets](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L204), [exponent box](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L368), [height fibre](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L377), [height-fibre normal form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L406), [fibre sum](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L384), [point height](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L373), [variable-base tail step](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L487), [that names its expanded form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L490), [smooth exponent shell](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L500), [short-interval uniqueness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L509), [third-coordinate projection](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L585), [first-coordinate projection](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L543), [quadratic shell bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L646), [sorted quadratic estimate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L629), [non-separation witness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L479), [origin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L443), [value at two](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L450), [value at three](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L458), [value at six](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L467), [rank-two certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L721), [checked internal-power uniqueness lemma](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L668), [dyadic block base](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L688), [exact four-case alphabet](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L699), [bounded-radix consequence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L711), [checked absorption](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L548), [checked cancellation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L581), [checked bound transfer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L601), [checked window transfer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L612), [window base](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L417), [window forcing](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L422), [checked window identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L480), [canonical representative](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L26), [positive range](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L31), [congruence to the source integer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L52), [cofinal local-window escape condition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L629), [finite contradiction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L76), [integer form of the contradiction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L110), [exact least-positive-residue classifier](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ResidueEscape.lean#L138), [reduced-carry extinction theorem](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L645), [absorbed-carry extinction theorem](https://github.com/wcook04/plectis-erdos/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L689), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/BoundedRadixTailEscape.lean#L89), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L497), [residue–coboundary form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L109), [symbolic realisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L293), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L334), [carry interval](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L150), [digit interval](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L157), [potential classifier](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/ThreeChannelBlockRigidity.lean#L59), [one-index extinction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L178), [uniform extinction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L238), [first-block sum](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L289), [four-state obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/99f4bf47422abbd8757cbb22b50ba079d764d3a7/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L308).

<div class="thebibliography">

10

P. Erdős and R. L. Graham, [*Old and New Problems and Results in Combinatorial Number Theory*](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf), Monogr. Enseign. Math. 28, Geneva, 1980, p. 65. For a possibly infinite prime set $`Q`$, the page states the infinite-$`Q`$ irrationality and asks what happens for finite $`Q`$ with more than one element. P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). P. Erdős, [*Letter to the Editor*](https://www.fq.math.ca/Scanned/12-4/letter.pdf) (written 1 January 1973), Fibonacci Quart. **12** (1974), no. 4, p. 335. The letter poses the full series as a conjecture and asserts irrationality after retaining only the distinct running-LCM values. T. F. Bloom, [*Erdős Problem \#269*](https://www.erdosproblems.com/269), `erdosproblems.com/269`, accessed 28 July 2026 (page displays “last edited 28 December 2025”). The current record labels the finite-support problem open, cites `[ErGr80, p. 65]` and `[Er88c, p. 106]`, routes to the 1974 letter on p. 335, records the infinite-prime and de-duplicated variants, and explicitly describes its status as the website owner’s present assessment rather than a literature-completeness guarantee. Y. Bugeaud and M. Laurent, *Transcendence and continued fraction expansion of values of Hecke–Mahler series*, Acta Arith. **209** (2023), 59–90, doi:10.4064/aa220323-18-1; [authors’ Online First PDF](https://irma.math.unistra.fr/~bugeaud/travaux/BuMLAA.pdf), [arXiv:2203.12901v1](https://arxiv.org/abs/2203.12901). Theorem 1.1 is on p. 3 of the inspected Online First PDF; the journal publication is pp. 59–90. The authors note there that its $`\rho=0`$ case was already obtained by Loxton and van der Poorten. J. H. Loxton and A. J. van der Poorten, *Arithmetic properties of certain functions in several variables III*, Bull. Austral. Math. Soc. **16** (1977), 15–47. S. Fan, comment on Erdős Problem \#269, [erdosproblems.com forum, thread 269](https://www.erdosproblems.com/forum/thread/269), 26 June 2026. The comment gives the two-channel factorisation, the Hecke–Mahler reduction, and the transcendence conclusion for $`|P|=2`$; follow-up comments there note the extension to arbitrary coprime pairs.

</div>

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.
