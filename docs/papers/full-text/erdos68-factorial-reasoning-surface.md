<a id="erdos68-factorial-reasoning-surface"></a>

# Denominators and Rationality Criteria for \sum\_{n\ge2}(n!-1)^{-1}

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

Let $`S=\sum_{n\ge2}(n!-1)^{-1}`$ and $`L_N=\operatorname{lcm}(2!-1,\ldots,N!-1)`$. We prove
``` math
\liminf_{N\to\infty}\frac{\log L_N}{N^{3/2}\log N}
 \ge\frac{2\sqrt2}{3}.
```
The proof compares the product of a terminal block of denominators with their pairwise gcds, using $`\gcd(i!-1,j!-1)\mid j!/i!-1`$ rather than an external multiplicity theorem. This is a bound before reduction. To study the reduced partial sums, we specialise a valuation formula of Louwsma and Martino to reciprocal sums. Exact examples show that the primes $`139`$ and $`2593`$ are absent from the reduced denominators of every partial sum from indices $`137`$ and $`2591`$ onward, respectively.

The coefficient constructions give integer linear forms $`MS+k`$. We classify the vectors that cancel prescribed initial weighted sums, determine their attainable moments $`M`$ on indices at least $`2`$, and give a lower bound for their largest support index when the moment obeys a stated upper bound there. At fixed moment the remainder changes only by an integer. The rationality criteria use factorial digits and the next integer above a scaled partial sum. The digit argument also applies to $`\sum_{n\ge2}1/(n!+t)`$ for integers $`t\ge-1`$, recovering the irrationality of $`e`$ at $`t=0`$.

Finally, two exact finite calculations give $`q\nmid299999!`$ and $`q\ge2^{39990}>10^{12038}`$ for any rational representation $`S=a/q`$, $`q>0`$. The full carry calculation and the continued-fraction calculation are external to Lean. These exclusions do not prove irrationality; the additional tail and residue inequalities that would suffice are stated separately.

<a id="organisation."></a>

#### Organisation.

The first two sections keep two different questions separate: which prime powers survive reduction (§<a href="#long68:sec:prime-powers" data-reference-type="ref" data-reference="long68:sec:prime-powers">1</a>), and how large a common denominator must be before reduction (§<a href="#long68:sec:lcm" data-reference-type="ref" data-reference="long68:sec:lcm">2</a>). The tail comparisons in §<a href="#long68:sec:residue" data-reference-type="ref" data-reference="long68:sec:residue">4</a> require information not supplied by either answer. For the finite exclusions, only the carry criterion in §<a href="#long68:sec:carry" data-reference-type="ref" data-reference="long68:sec:carry">3</a> and the computations in §<a href="#long68:sec:finite" data-reference-type="ref" data-reference="long68:sec:finite">6</a> are needed. The coefficient constructions in §<a href="#long68:sec:channels" data-reference-type="ref" data-reference="long68:sec:channels">5</a> are a separate approach; §<a href="#long68:sec:open" data-reference-type="ref" data-reference="long68:sec:open">7</a> identifies the remaining inequalities, and the appendices give further deductions, unsuccessful approaches, and formal-source links.

<a id="long68:sec:prime-powers"></a>

# Which prime powers survive reduction

<div id="long68:res:problem" class="problem">

**Problem 1** (Erdős \#68). Is $`S=\sum_{n\ge2}(n!-1)^{-1}`$ irrational?

</div>

Erdős states the question on p. 102 of his 1988 survey and, in the same passage, records the expectation that $`\sum_n1/(n!+t)`$ is irrational, indeed transcendental, for every integer $`t`$ \[erdos1988, p. 102\]. Here the sum starts sufficiently far out that $`n!+t>0`$; changing that starting index adds or removes only a rational number. In particular, no term with zero denominator is included. The expectation for all integer shifts is not proved here. Numbering follows [Bloom’s Erdős problem catalogue](https://www.erdosproblems.com/68) \[bloom\].

Put
``` math
d_n=n!-1,\qquad H_M=\sum_{n=2}^{M}\frac1{d_n},\qquad
 L_M=\operatorname{lcm}(d_2,\ldots,d_M),\qquad
 A_M=\sum_{n=2}^{M}\frac{L_M}{d_n},
```
so that $`H_M=A_M/L_M`$. Throughout, $`\operatorname{den}(x)`$ is the positive denominator of a rational number in lowest terms, and $`v_p(a)`$ is the exponent of the prime $`p`$ in a positive integer $`a`$. The first question is which prime power present in $`L_M`$ remains in $`\operatorname{den}(H_M)`$. For the largest exponent the answer follows by specialising Louwsma and Martino’s valuation formula for an elementary symmetric sum \[louwsma-martino, Lemma 4.1, p. 10\]. Indeed, $`\sum_i1/x_i=(\sum_i\prod_{j\ne i}x_j)/\prod_i x_i`$ for positive integers $`x_i`$. Their lemma evaluates the numerator’s valuation; subtracting the product’s valuation gives the reciprocal-sum form. The proof below uses the least common multiple instead of the product.

The need to check cancellation is already visible in $`1/3+1/15=2/5`$: the common denominator contains $`3`$, but the reduced denominator does not. By contrast, $`1/9+1/45=2/15`$ only lowers the exponent of $`3`$ from $`2`$ to $`1`$. The theorem below tests whether the largest exponent is preserved; a failure of that test need not remove the prime completely. The formula is standard, whereas the two factorial-prefix examples below and the later tail comparison concern this particular series.

<span id="long68:res:lead-prime-pole" label="long68:res:lead-prime-pole"></span>

<div id="long68:res:prime-pole" class="theorem">

**Theorem 2** (maximal prime-power survival). *Let $`M\ge2`$, let $`p`$ be a prime dividing $`L_M`$, and put $`e=v_p(L_M)`$. Let $`J=\{n:2\le n\le M,\ v_p(d_n)=e\}`$ and write $`d_n=p^eu_n`$ for $`n\in J`$. Then, with inverses in $`\mathbb F_p`$,
``` math
\begin{equation}
\label{long68:eq:prime-pole-survival}
 v_p\bigl(\operatorname{den}(H_M)\bigr)=e
 \quad\Longleftrightarrow\quad
 \sum_{n\in J}u_n^{-1}\ne0\quad\hbox{in }\mathbb F_p.
\end{equation}
```*

</div>

<div class="proof">

*Proof.* Write $`L_M=p^eW`$ with $`p\nmid W`$. If $`v_p(d_n)<e`$, then $`p\mid L_M/d_n`$. If $`n\in J`$, then $`u_n(L_M/d_n)=W`$, so $`L_M/d_n\equiv Wu_n^{-1}\pmod p`$. Summing over $`2\le n\le M`$ gives
``` math
\begin{equation}
\label{long68:eq:prime-pole-residue}
 A_M\equiv \frac{L_M}{p^e}\sum_{n\in J}u_n^{-1}\pmod p.
\end{equation}
```

Finally $`\operatorname{den}(H_M)=L_M/\gcd(A_M,L_M)`$, whose $`p`$-valuation is $`e`$ exactly when $`p\nmid A_M`$. Since $`W`$ is invertible modulo $`p`$, that is exactly the stated condition. ◻

</div>

The complete valuation identity is
``` math
v_p\bigl(\operatorname{den}(H_M)\bigr)=\max\{0,e-v_p(A_M)\}.
```
A zero residue in <a href="#long68:eq:prime-pole-survival" data-reference-type="eqref" data-reference="long68:eq:prime-pole-survival">[long68:eq:prime-pole-survival]</a> therefore lowers the exponent, whereas complete cancellation requires $`v_p(A_M)\ge e`$. For $`e>1`$, reduction modulo $`p`$ alone cannot distinguish partial from complete cancellation. The proof uses no property of factorials beyond the displayed denominators, so it applies to any finite sum of reciprocals of positive integers. For $`d_n=n!-1`$, the examples below show that complete cancellation can actually occur; the general valuation formula alone does not predict it.

<a id="two-complete-cancellations."></a>

#### Two complete cancellations.

A unique maximal exponent makes the residue sum a single nonzero term, so the condition holds automatically. With several maximal terms it can fail. The following examples show cancellation in the factorial sequence itself, not just in arbitrary rational sums. Take $`M=p-1`$. The table lists every index with $`p\mid d_n`$, and every one has valuation exactly one.

<div class="center">

|    $`p`$ | indices $`n`$         | $`d_n/p\pmod p`$       | inverses modulo $`p`$ |
|---------:|:----------------------|:-----------------------|:----------------------|
|  $`139`$ | $`69,\ 122,\ 137`$    | $`6,\ 49,\ 73`$        | $`116,\ 122,\ 40`$    |
| $`2593`$ | $`349,\ 2243,\ 2591`$ | $`1508,\ 1566,\ 1678`$ | $`1367,\ 356,\ 870`$  |

</div>

The inverse sums are $`278=2\cdot139`$ and $`2593`$. By Theorem <a href="#long68:res:prime-pole" data-reference-type="ref" data-reference="long68:res:prime-pole">2</a>, $`139\nmid\operatorname{den}(H_{138})`$ and $`2593\nmid\operatorname{den}(H_{2592})`$: each prime divides the common denominator of its prefix and vanishes from the reduced one. Both hit lists and both valuations are checked by the recurrence
``` math
r_1=1,\qquad r_n\equiv nr_{n-1}\pmod{p^2},\qquad 0\le r_n<p^2,
```
run through $`n=p-1`$. A hit is an index with $`r_n\equiv1\pmod p`$, its lifted cofactor is $`(r_n-1)/p`$ modulo $`p`$. Valuation at least two would give $`r_n=1`$, which occurs for neither prime among the tested indices $`2\le n\le p-1`$. That enumeration is a finite calculation separate from the theorem.

The recurrence is run modulo $`p^2`$, not merely modulo $`p`$: reduction modulo $`p`$ would locate hits but could not establish that their valuations are exactly one. This is why the zero inverse sums prove complete cancellation in these examples.

For each prime $`p\ge3`$, the exponent $`v_p(\operatorname{den}(H_M))`$ is constant for $`M\ge\max(2,p-2)`$. Wilson’s theorem gives $`(p-1)!-1\equiv-2\pmod p`$, and $`n!-1\equiv-1\pmod p`$ for $`n\ge p`$. Hence every summand after index $`p-2`$ has denominator coprime to $`p`$. If a reduced fraction $`a/b`$ is followed by a summand $`1/d`$ with $`p\nmid d`$, their sum has numerator $`ad+b`$ over $`bd`$. When $`p\mid b`$, this numerator is nonzero modulo $`p`$, so the exponent of $`p`$ in the reduced denominator stays the same. When $`p\nmid b`$, the new denominator remains coprime to $`p`$. Consequently, the two cancellations persist in every later partial sum:
``` math
139\nmid\operatorname{den}(H_M)\quad(M\ge137),\qquad
 2593\nmid\operatorname{den}(H_M)\quad(M\ge2591).
```
The primes still divide the corresponding common denominators $`L_M`$. These are assertions about the partial sums; they do not constrain a hypothetical denominator of their real limit $`S`$ without a further approximation estimate.

We next ask where a prime first divides a denominator $`d_m`$. This means it divides none of $`d_2,\ldots,d_{m-1}`$; it may still divide a later denominator, so uniqueness at its first occurrence gives no uniqueness in every larger block.

<div id="long68:res:wilson-cofinality" class="proposition">

**Proposition 3** (cofinal first prime occurrences). *For every integer $`B\ge0`$ there are a prime $`q`$ and an integer $`m>B`$ with $`m<q`$, $`q\mid m!-1`$ and $`\gcd(q,k!-1)=1`$ for every $`k`$ with $`2\le k<m`$.*

</div>

<div class="proof">

*Proof.* Choose a prime $`q\ge B!+5`$. Wilson’s theorem gives $`(q-2)!\equiv1\pmod q`$, so there is a least index $`m\ge2`$ with $`q\mid m!-1`$, and $`m\le q-2`$. If $`m\le B`$, then $`q\le m!-1\le B!-1`$, contradicting the choice of $`q`$. Hence $`m>B`$, and minimality gives the coprimality assertions. ◻

</div>

The construction proves cofinality of first occurrences, but not the inequality involving $`q`$ needed for the additional two-factor test in §<a href="#long68:sec:residue" data-reference-type="ref" data-reference="long68:sec:residue">4</a>. The sufficient tail inequality there does not require choosing a prime $`q`$. Wilson reflection limits what can be inferred from a large prime factor alone: for odd $`2\le n<q`$ with $`q\mid n!-1`$, the identity $`(q-1-n)!\,n!\equiv(-1)^{n+1}\pmod q`$ gives the reflected congruence at $`q-n-1`$. It gives a second summand denominator only when $`q\ne2n+1`$ and $`n\le q-3`$. At the Wilson endpoint $`n=q-2`$, it instead returns index $`1`$, where $`1!-1=0`$ is not a denominator of this series. The reflection identity is classical; see Stewart \[stewart2004, p. 462, (4)\].

*Status.* The problem treated here is open, and this note does not close it. Every statement below marked as checked is a proposition that the pinned Lean kernel accepts from the sources this note links to, with no `sorry`, no added axiom, and no unchecked evaluation. That is a claim about the formal statement, not about its mathematical interest, its novelty, or the original problem. The unresolved obligations are named exactly, in their own section, and none of the finite computations, reductions, or no-go results here removes one of them.

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.

<a id="long68:sec:lcm"></a>

# The growth of the common denominator

Theorem <a href="#long68:res:prime-pole" data-reference-type="ref" data-reference="long68:res:prime-pole">2</a> concerns the denominator after reduction. The common denominator before reduction admits an unconditional lower bound of its own, by an elementary argument.

<div id="long68:res:product-lcm" class="lemma">

**Lemma 4** (product, least common multiple, pairwise gcd). *For positive integers $`x_1,\ldots,x_k`$,
``` math
\prod_{i=1}^{k}x_i\ \Big|\ \operatorname{lcm}(x_1,\ldots,x_k)\prod_{i<j}\gcd(x_i,x_j).
```*

</div>

<div class="proof">

*Proof.* Fix a prime $`r`$ and relabel so that $`a_1\le\cdots\le a_k`$, where $`a_i=v_r(x_i)`$. The right-hand side has $`r`$-valuation $`a_k+\sum_{i<j}\min(a_i,a_j)=a_k+\sum_{i=1}^{k-1}(k-i)a_i`$, and the left-hand side has $`\sum_{i=1}^{k}a_i`$. The difference is $`\sum_{i=1}^{k-1}(k-i-1)a_i`$, which is nonnegative. ◻

</div>

The next divisibility is the case $`P=-1`$ of the relation $`\gcd(i!+P(i),j!+P(j))\mid (j!/i!)P(i)-P(j)`$ for $`P\in\mathbb{Z}[X]`$, obtained by multiplying $`i!+P(i)`$ by $`j!/i!`$ and subtracting $`j!+P(j)`$. Luca and Shparlinski use this relation to bound a common divisor of $`n!+P(n)`$ and $`(n+h)!+P(n+h)`$ in the proof of their Lemma 5 \[luca-shparlinski\], and Lai uses it for a common prime-power divisor \[lai, proof of Lemma 2.4, display (2.5)\].

The earlier spacing method of Erdős and Stewart \[erdos-stewart1976, §3, pp. 516–517\] is related background. We now state only the subtraction needed for the lcm argument, rather than importing the prime-factor estimates of those papers.

<div id="long68:res:gap-gcd" class="lemma">

**Lemma 5** (factorial-gap gcd). *For $`2\le i<j`$, the integer $`g=\gcd(i!-1,j!-1)`$ divides $`j!/i!-1`$, and $`g\le j!/i!-1<j^{\,j-i}`$.*

</div>

<div class="proof">

*Proof.* Both $`i!`$ and $`j!`$ are congruent to $`1`$ modulo $`g`$. The quotient $`j!/i!=(i+1)(i+2)\cdots j`$ is an integer, and $`j!=i!\cdot(j!/i!)`$, so $`j!/i!\equiv1\pmod g`$. Since $`j!/i!\ge i+1>1`$, the positive integer $`j!/i!-1`$ is a multiple of $`g`$, whence $`g\le j!/i!-1`$. Finally $`j!/i!`$ is a product of $`j-i`$ integers each at most $`j`$. ◻

</div>

<div id="long68:res:segment" class="lemma">

**Lemma 6** (segment inequality). *For $`2\le k\le N-1`$,
``` math
\begin{equation}
\label{long68:eq:segment}
 \sum_{n=N-k+1}^{N}\log(n!-1)
 \ \le\ \log L_N+\binom{k+1}{3}\log N.
\end{equation}
```*

</div>

<div class="proof">

*Proof.* Apply Lemma <a href="#long68:res:product-lcm" data-reference-type="ref" data-reference="long68:res:product-lcm">4</a> to $`x_n=d_n`$ for $`N-k+1\le n\le N`$. Their least common multiple divides $`L_N`$. By Lemma <a href="#long68:res:gap-gcd" data-reference-type="ref" data-reference="long68:res:gap-gcd">5</a> each pairwise gcd is smaller than $`N^{\,j-i}`$, and over a block of $`k`$ consecutive indices
``` math
\sum_{i<j}(j-i)=\sum_{d=1}^{k-1}d(k-d)=\binom{k+1}{3}.
```
Taking logarithms of the resulting divisibility gives <a href="#long68:eq:segment" data-reference-type="eqref" data-reference="long68:eq:segment">[long68:eq:segment]</a>. ◻

</div>

<div id="long68:res:lcm-growth" class="theorem">

**Theorem 7** (common-denominator growth).
*``` math
\liminf_{N\to\infty}\frac{\log L_N}{N^{3/2}\log N}
 \ \ge\ \frac{2\sqrt2}{3}.
```*

</div>

<div class="proof">

*Proof.* A terminal block keeps every factorial near $`N!`$, but increasing its length also increases the total pairwise-gcd loss. The gain is of order $`kN\log N`$ and the loss of order $`k^3\log N`$, so the useful balance is $`k`$ of order $`\sqrt N`$. Fix $`\alpha>0`$ and take $`k=\lfloor\alpha\sqrt N\rfloor`$, which satisfies $`2\le k\le N-1`$ for all large $`N`$. Put $`u=N-k+1`$.

For the left-hand side of <a href="#long68:eq:segment" data-reference-type="eqref" data-reference="long68:eq:segment">[long68:eq:segment]</a>, use $`n!-1\ge n!/2`$ and $`\log n!\ge n\log n-n`$. Since $`n\mapsto n\log n-n`$ increases,
``` math
\sum_{n=u}^{N}\log(n!-1)\ \ge\ k\,(u\log u-u)-k\log2 .
```
Here $`u\ge N-\alpha\sqrt N`$ and $`k=\alpha\sqrt N+O(1)`$, so $`k\,u\log u=\alpha N^{3/2}\log N+O(N\log N)`$, while $`k\,u=O(N^{3/2})`$ and $`k\log2=O(\sqrt N)`$. Hence the left-hand side is at least $`\alpha N^{3/2}\log N+o(N^{3/2}\log N)`$.

For the right-hand side, $`\binom{k+1}{3}\le(k+1)^3/6`$, so $`\binom{k+1}{3}\log N=\tfrac{\alpha^3}{6}N^{3/2}\log N+o(N^{3/2}\log N)`$. Therefore
``` math
\liminf_{N\to\infty}\frac{\log L_N}{N^{3/2}\log N}
 \ \ge\ \alpha-\frac{\alpha^3}{6}.
```
The right-hand side is maximised at $`\alpha=\sqrt2`$, with value $`\sqrt2-\tfrac{2\sqrt2}{6}=\tfrac{2\sqrt2}{3}`$. ◻

</div>

The displayed proof of the lcm bound uses only Lemmas <a href="#long68:res:product-lcm" data-reference-type="ref" data-reference="long68:res:product-lcm">4</a> and <a href="#long68:res:gap-gcd" data-reference-type="ref" data-reference="long68:res:gap-gcd">5</a>. Its formal counterpart is listed in the sources section; the status of that entry is not a blanket assertion about all linked modules. Theorem 12 of Garaev, Luca and Shparlinski \[garaev-luca-shparlinski, arXiv v1, p. 16\] supplies a different input: a uniform $`O(N^{2/3})`$ bound for the number of solutions of $`n!\equiv a\pmod p`$, for fixed $`a\not\equiv0\pmod p`$, in an interval of length $`N`$ contained in $`1\le n<p`$. The weaker lcm deduction from it is retained in §<a href="#long68:sec:ext-superseded" data-reference-type="ref" data-reference="long68:sec:ext-superseded">9.3</a>, not used here. No exhaustive priority claim is made for the lcm estimate; its precise elementary derivation and the inherited subtraction are stated so that the claim can be assessed without relying on a search conclusion.

<div class="remark">

*Remark 1* (polynomial shifts). Fix $`P\in\mathbb{Z}[X]\smallsetminus\{0\}`$. By Lemma 3 of Luca and Shparlinski \[luca-shparlinski\], in the form given by Lai \[lai, Lemma 2.1\], there is $`n_0\ge2`$, depending only on $`P`$, such that $`n!+P(n)>1`$ for all $`n\ge n_0`$ and $`P(n)(n+1)\cdots(n+h)\ne P(n+h)`$ for all $`n\ge n_0`$ and $`h\ge1`$. The nonvanishing has a short direct proof. Beyond a cutoff, $`P`$ has constant nonzero sign and $`P(n+1)/P(n)\to1`$, so $`0<P(n+1)/P(n)<n+1`$ for every sufficiently large $`n`$. Multiplying these inequalities gives
``` math
0<\frac{P(n+h)}{P(n)}<\prod_{j=1}^{h}(n+j)\qquad(h\ge1).
```
Thus the required subtraction is nonzero for every gap $`h`$, not merely for each fixed $`h`$ after a separate cutoff. Increasing $`n_0`$ also makes $`n!+P(n)>1`$. The proof of Theorem <a href="#long68:res:lcm-growth" data-reference-type="ref" data-reference="long68:res:lcm-growth">7</a> then gives
``` math
\liminf_{N\to\infty}
 \frac{\log\operatorname{lcm}\{n!+P(n):n_0\le n\le N\}}{N^{3/2}\log N}
 \ \ge\ \frac{2\sqrt2}{3}.
```
For $`n_0\le i<j\le N`$, multiplying $`i!+P(i)`$ by $`j!/i!`$ and subtracting $`j!+P(j)`$ gives
``` math
\gcd\bigl(i!+P(i),\,j!+P(j)\bigr)\ \Big|\ \frac{j!}{i!}P(i)-P(j),
```
which replaces Lemma <a href="#long68:res:gap-gcd" data-reference-type="ref" data-reference="long68:res:gap-gcd">5</a>. The right-hand side is nonzero by the choice of $`n_0`$, and its absolute value is at most $`C_PN^{\,j-i+\deg P}`$ for a constant $`C_P`$. Over a block of $`k`$ indices the pairwise loss therefore grows by $`O_P(k^2\log N)`$, which is $`O_P(N\log N)`$ when $`k=\lfloor\alpha\sqrt N\rfloor`$. Since $`n!+P(n)\ge n!/2`$ for large $`n`$, the lower estimate for the sum of logarithms is unchanged. The cutoff is needed, since for $`P=-2`$ the factor at $`n=2`$ vanishes. The hypothesis $`P\ne0`$ is needed as well, since for $`P=0`$ the least common multiple is $`N!`$ whatever the cutoff.

</div>

<a id="a-non-polynomial-comparison."></a>

#### A non-polynomial comparison.

For $`n!+2^n-1`$, Luca and Shparlinski \[luca-shparlinski-exp, Lemmas 2.1–2.3, pp. 860–862\] eliminate the exponential term using three hits; multiplicative order enters the counting. Their valuation-layer identity \[luca-shparlinski-exp, (3.2), p. 863\] records repeated prime-power divisibility. These are related tools, not inputs to Theorem <a href="#long68:res:lcm-growth" data-reference-type="ref" data-reference="long68:res:lcm-growth">7</a>, and no extension to general non-polynomial perturbations is asserted.

Within the terminal-block estimate just proved, maximising $`\alpha-\alpha^3/6`$ gives $`2\sqrt2/3`$. This is an optimisation of that one-parameter bound, not an optimality theorem for all block selections or all gcd arguments. The discarded factorial term has size $`N^{3/2}`$, so a finite normalised ratio need not be close to the limiting lower bound.

Theorem <a href="#long68:res:lcm-growth" data-reference-type="ref" data-reference="long68:res:lcm-growth">7</a> concerns $`L_N`$, not $`\operatorname{den}(H_N)`$. Theorem <a href="#long68:res:prime-pole" data-reference-type="ref" data-reference="long68:res:prime-pole">2</a> and the cancellations at $`139`$ and $`2593`$ show why these cannot be interchanged: a prime present in the common denominator may be absent after reduction. The two examples establish this possibility, not an asymptotic estimate for cancellation.

Even two consecutive denominators obstruct clearing by the full lcm. For $`N\ge3`$, the gcd of $`(N-1)!-1`$ and $`N!-1`$ divides $`N-1`$, whereas $`(N-1)!-1`$ is coprime to $`N-1`$. Thus those denominators are coprime, and
``` math
L_N(S-H_N)>
\frac{((N-1)!-1)(N!-1)}{(N+1)!-1}\longrightarrow\infty.
```
This argument does not use the stronger asymptotic growth theorem.

The direction of denominator control matters. Write $`H_N=\widehat A_N/Q_N`$ in lowest terms, reserving $`A_N`$ above for the numerator over the full common denominator. Under the hypothetical identity $`S=a/q`$, with $`a\in\mathbb{Z}`$ and $`q\ge1`$, positivity of the tail gives
``` math
qQ_N(S-H_N)=aQ_N-q\widehat A_N\in\mathbb{Z}_{>0}.
```
A direct clearing contradiction therefore requires an upper estimate that makes $`qQ_N(S-H_N)<1`$ for some $`N`$; equivalently, it needs $`Q_N`$ to be small relative to the reciprocal tail. A lower bound on $`Q_N`$ points in the opposite direction. Indeed, the rational limit $`1`$ and the approximants $`1-1/Q_N`$ have arbitrarily large reduced denominators without any irrationality. The inequality $`d_N(S-H_N)<1`$ alone would not repair the argument, because $`d_N`$ generally does not clear the earlier summands of $`H_N`$. The prime-power analysis describes which factors survive reduction, but it does not yet supply the required upper control on $`Q_N`$.

For linear forms in $`p`$-adic zeta values, with $`p\ge5`$ a fixed prime and $`n`$ the index of the form, Lai, Lupu and Sprang quantify a saving of this kind. They bound the denominators of the coefficients by powers of $`\operatorname{lcm}(1,\ldots,n)`$, show that the bound may be divided by a product $`\Phi_n`$ of prime powers, and compute the growth rate of $`\Phi_n`$ \[lai-lupu-sprang, Lemmas 5.3–5.7 and 7.3\]. That saving enters the inequality \[lai-lupu-sprang, (8.1)\] under which the rescaled forms, which have integer coefficients, meet the irrationality criterion \[lai-lupu-sprang, Lemma 2.1, p. 3\] that they quote from Lai \[lai-2adic, Lemma 2.1, p. 4\]. Along one unbounded subsequence, the forms must be nonzero and their $`p`$-adic absolute values, multiplied by the largest ordinary absolute value of an integer coefficient, must tend to zero. The coefficient bound is archimedean; the bound on the value is $`p`$-adic. The conclusion is that at least one of the finitely many $`p`$-adic numbers in the forms is irrational, not that each is irrational. The corresponding saving for $`H_N`$ is the ratio $`L_N/Q_N`$.

This ratio is an integer. Merely naming it supplies neither its growth nor a small linear form; the analogy is about what an eventual estimate would have to accomplish. Theorem <a href="#long68:res:prime-pole" data-reference-type="ref" data-reference="long68:res:prime-pole">2</a> decides, for each prime $`p\mid L_N`$, whether $`p`$ divides this ratio; no asymptotic lower bound for the ratio is established here. This paragraph compares the two methods; no $`p`$-adic theorem is applied to $`S`$.

<a id="long68:sec:carry"></a>

# Rationality and the next integer above a scaled partial sum

For each scaled partial sum, take the least integer strictly above it. This differs from the ordinary ceiling when the scaled sum is an integer. Write
``` math
Z_m=\lfloor m!H_m\rfloor+1,\qquad
 \Delta_m=Z_{m-1}-(m-1)!H_{m-1}\quad(m\ge3).
```
Thus $`\Delta_m`$ is the distance from the preceding scaled partial sum to the next integer, and $`0<\Delta_m\le1`$. Define an integer $`b_m`$ by
``` math
\begin{equation}
\label{long68:eq:carry-recurrence}
 Z_m=mZ_{m-1}+1-b_m .
\end{equation}
```

Call $`b_m=1`$ a *unit carry*. Put $`E_m=m!(S-H_m)`$ and $`\varepsilon_m=1/(m!-1)`$. Since $`d_{n+1}>(n+1)d_n`$, a geometric majorant gives the tail estimate
``` math
\begin{equation}
\label{long68:eq:tail-bound}
 0<E_m<\frac{2\,m!}{(m+1)!-1}<\frac2m\le1\qquad(m\ge2).
\end{equation}
```
Compare the factorial scaling in Hančl and Tijdeman’s tail-integrality lemma for factorial series with integer coefficients \[hancl-tijdeman, Lemma 2.1 and the following remark, p. 385\]. Their scaled partial sums are integers; ours need not be, since already $`3!H_3=36/5`$. The next proof instead uses the short positive tail to identify the least integer above a scaled prefix under a rationality assumption. The carry-defect expansion in §<a href="#long68:sec:ext-literature" data-reference-type="ref" data-reference="long68:sec:ext-literature">9.2</a> gives a separate, direct application of factorial-series rationality criteria.

<span id="long68:res:lead-carry-equivalence" label="long68:res:lead-carry-equivalence"></span> <span id="long68:res:strict-successor-complete-characterization" label="long68:res:strict-successor-complete-characterization"></span>

<div id="long68:res:carry-equivalence" class="theorem">

**Theorem 8** (an exact criterion from successive partial sums). *For $`m\ge3`$,
``` math
\begin{equation}
\label{long68:eq:unit-window}
 b_m=1
 \iff m\mid Z_m
 \iff 1+\varepsilon_m<m\Delta_m\le2+\varepsilon_m .
\end{equation}
```*

*Moreover
``` math
\begin{align}
 S\in\mathbb{Q}
 &\iff b_m=1\ \hbox{for all sufficiently large }m,
 \label{long68:eq:carry-rationality}\\
 S\notin\mathbb{Q}
 &\iff \forall B\ \exists m>B:\ m\nmid Z_m .
 \label{long68:eq:strict-misses}
\end{align}
```
If $`S=a/q`$ with $`a\in\mathbb{Z}`$, $`q\ge1`$ and $`b_m\ne1`$, then $`q\nmid(m-1)!`$ and $`q\ge m`$.*

</div>

<div class="proof">

*Proof.* From $`m!H_m=mZ_{m-1}-m\Delta_m+1+\varepsilon_m`$ one gets $`b_m=\lceil m\Delta_m-1-\varepsilon_m\rceil`$ with $`-1\le b_m\le m-1`$, which gives both equivalences in <a href="#long68:eq:unit-window" data-reference-type="eqref" data-reference="long68:eq:unit-window">[long68:eq:unit-window]</a>, endpoints included.

Suppose $`S=a/q`$ and $`q\mid(m-1)!`$. For $`j=m-1`$ and $`j=m`$ the number $`j!\,S`$ is an integer, and $`j!H_j=j!\,S-E_j`$ with $`0<E_j<1`$ by <a href="#long68:eq:tail-bound" data-reference-type="eqref" data-reference="long68:eq:tail-bound">[long68:eq:tail-bound]</a>, so $`Z_j=j!\,S`$. Substituting into <a href="#long68:eq:carry-recurrence" data-reference-type="eqref" data-reference="long68:eq:carry-recurrence">[long68:eq:carry-recurrence]</a> forces $`b_m=1`$. Every fixed $`q`$ divides $`(m-1)!`$ eventually, which gives one direction of <a href="#long68:eq:carry-rationality" data-reference-type="eqref" data-reference="long68:eq:carry-rationality">[long68:eq:carry-rationality]</a> and, by contraposition, the final assertion; $`q<m`$ would imply $`q\mid(m-1)!`$. Conversely, an eventual unit-carry tail makes $`Z_m/m!`$ eventually constant, and $`0<Z_m/m!-H_m\le1/m!`$ with $`H_m\to S`$ identifies that constant as $`S`$, which is then rational. Negating <a href="#long68:eq:carry-rationality" data-reference-type="eqref" data-reference="long68:eq:carry-rationality">[long68:eq:carry-rationality]</a> gives <a href="#long68:eq:strict-misses" data-reference-type="eqref" data-reference="long68:eq:strict-misses">[long68:eq:strict-misses]</a>. ◻

</div>

The conclusion $`q\nmid(m-1)!`$ is about prime-power multiplicities, not just prime factors. It permits all prime factors of $`q`$ to be at most $`m-1`$ if one occurs to a larger exponent than in $`(m-1)!`$.

<a id="long68:sec:adjacent-unit-no-go"></a>

## Why one proposed window argument is circular

A proposed argument starts by assuming $`b_m=b_{m+1}=1`$, clears the denominators in the resulting inequalities, and tries to contradict the size of a prime-power divisor. The following calculation shows why the resulting size bound alone cannot provide that contradiction.

Write $`\Delta_k=P^\Delta_k/Q^\Delta_k`$ in lowest terms, with $`P^\Delta_k,Q^\Delta_k>0`$. In one recurrence step the unreduced denominator is $`Q^\Delta_k(k!-1)`$; let $`G_k=Q^\Delta_k(k!-1)/Q^\Delta_{k+1}`$ be the positive integer cancelled in reduction. For $`m\ge3`$, put
``` math
\begin{aligned}
 D_m&=Q^\Delta_m(m!-1)((m+1)!-1),\\
 \Omega_m&=D_m\left(m(m+1)\Delta_m-m-2
       -\frac{m+1}{m!-1}-\frac1{(m+1)!-1}\right).
 \end{aligned}
```
Both are integers. The two unit carries are equivalent to $`0<\Omega_m\le D_m`$. Independently of the carries, cancellation in two successive steps gives
``` math
D_m=Q^\Delta_{m+2}G_{m+1}G_m=Q^\Delta_m(m!-1)\bigl((m+1)!-1\bigr),
```
and under the pair assumption the offset factors to match, $`\Omega_m=P^\Delta_{m+2}G_{m+1}G_m`$. Dividing by $`G_{m+1}G_m>0`$ reduces the proposed bound to
``` math
0<P^\Delta_{m+2}\le Q^\Delta_{m+2},
```
which every reduced positive gap in $`(0,1]`$ already satisfies. Thus the resulting gap bound is not an additional restriction on a pair of unit carries. This calculation does not exclude an independent arithmetic obstruction involving the transition numerators or their valuations. Such an obstruction would need information not already implied by the pair assumption; it need not take the form of a bound on the preceding gap $`\Delta_m`$.

<a id="factorial-digits-of-s-e2"></a>

## Factorial digits of $`S-e+2`$

Let $`C=\sum_{n\ge2}\bigl(n!(n!-1)\bigr)^{-1}`$. The identity $`1/(n!-1)=1/n!+1/(n!(n!-1))`$ and absolute convergence give
``` math
\begin{equation}
\label{long68:eq:companion-decomposition}
 S=C+e-2 .
\end{equation}
```
The canonical factorial digits of a real $`x`$ are $`a_m(x)=\lfloor m!x\rfloor-m\lfloor(m-1)!x\rfloor\in\{0,\ldots,m-1\}`$ for $`m\ge2`$. At a rational endpoint, the floor convention selects the terminating representation. For example, $`1/2=1/2!`$ also equals $`\sum_{m\ge3}(m-1)/m!`$, but its canonical digits are $`a_2=1`$ and $`a_m=0`$ for $`m\ge3`$, not an eventually maximal tail. With this convention, $`x`$ is rational exactly when its digits vanish from some index on. The criterion goes back to Cantor \[cantor1869\]; Galambos treats the rationality of Cantor series in \[galambos1976, Ch. II, §2.1, pp. 21–22\], and Koepf and Schmersau prove the irrationality direction for nonterminating factorial expansions whose digits are not eventually maximal \[koepf-schmersau, Example 3.2, p. 121\].

<span id="long68:res:lead-companion-orbit" label="long68:res:lead-companion-orbit"></span>

<div id="long68:res:companion-orbit" class="proposition">

**Proposition 9** (rationality and factorial residues).
*``` math
S\in\mathbb{Q}
 \quad\Longleftrightarrow\quad
 \lfloor m!C\rfloor\equiv-2\pmod m
 \quad\hbox{for all sufficiently large }m.
```*

</div>

<div class="proof">

*Proof.* Put $`J_m=\sum_{k=0}^{m}m!/k!`$. Then $`J_m`$ is an integer, every summand with $`k<m`$ is divisible by $`m`$ and the summand at $`k=m`$ is $`1`$, so $`J_m\equiv1\pmod m`$; and $`0<m!\,e-J_m<1`$ for $`m\ge2`$.

Suppose $`S`$ is rational. For all large $`m`$ both $`(m-1)!\,S`$ and $`m!\,S`$ are integers, so $`m\mid m!\,S`$. Multiplying <a href="#long68:eq:companion-decomposition" data-reference-type="eqref" data-reference="long68:eq:companion-decomposition">[long68:eq:companion-decomposition]</a> by $`m!`$ and using $`\lfloor -m!\,e\rfloor=-J_m-1`$ gives $`\lfloor m!C\rfloor=m!\,S+2\,m!-J_m-1\equiv-2\pmod m`$.

Conversely, assume the congruence from some index on. Because $`0\le a_m(C)<m`$, for $`m\ge3`$ the congruence is equivalent to $`a_m(C)=m-2`$. Choose $`N`$ beyond the exceptional indices. The canonical expansion gives
``` math
C=\frac{\lfloor N!C\rfloor}{N!}+\sum_{m>N}\frac{m-2}{m!},
```
and the telescope $`\sum_{m>N}(m-1)/m!=1/N!`$ turns this into
``` math
S=C+e-2
 =\frac{\lfloor N!C\rfloor+1}{N!}+\sum_{m=2}^{N}\frac1{m!},
```
which is rational. ◻

</div>

The condition is eventual equality, not equality at many computed indices. The proof works for any real $`C`$: it holds exactly when $`C+e-2`$ is rational. For example, $`C=2-e`$ gives a rational sum, whereas $`C=0`$ gives the irrational number $`e-2`$. The issue here is to decide the condition for the particular positive series defining $`C`$.

<a id="escape-from-a-smaller-interval"></a>

## Escape from a smaller interval

Write $`\theta_m=\{m!\,S\}`$. We ask whether $`\theta_{m-1}`$ lies outside $`[0,E_m/m)`$, an interval of width less than $`2/m^2`$.

<div id="long68:res:lower-escape" class="proposition">

**Proposition 10** (lower-interval criterion).
*``` math
\begin{equation}
\label{long68:eq:lower-escape}
 S\notin\mathbb{Q}
 \quad\Longleftrightarrow\quad
 \forall B\ \exists m>B:\ E_m\le m\theta_{m-1}.
\end{equation}
```
For $`m\ge3`$ the finite condition
``` math
\begin{equation}
\label{long68:eq:finite-escape}
 m\Delta_m\le1+\varepsilon_m
 \quad\hbox{or}\quad
 1+\varepsilon_m+\frac2m\le m\Delta_m
\end{equation}
```
implies the escape inequality in <a href="#long68:eq:lower-escape" data-reference-type="eqref" data-reference="long68:eq:lower-escape">[long68:eq:lower-escape]</a>. Cofinally many instances of <a href="#long68:eq:finite-escape" data-reference-type="eqref" data-reference="long68:eq:finite-escape">[long68:eq:finite-escape]</a> therefore imply $`S\notin\mathbb{Q}`$.*

</div>

<div class="proof">

*Proof.* If $`S`$ is rational, the remainders $`\theta_{m-1}`$ vanish eventually while $`E_m>0`$, so the escape inequality fails eventually. Conversely, suppose $`m\theta_{m-1}<E_m`$ for every sufficiently large $`m`$. By <a href="#long68:eq:tail-bound" data-reference-type="eqref" data-reference="long68:eq:tail-bound">[long68:eq:tail-bound]</a> this gives $`m\theta_{m-1}<1`$, so $`a_m(S)=0`$ and $`\theta_m=m\theta_{m-1}`$. Fix $`N`$ after this recurrence begins. Then $`\theta_{N+k}=((N+k)!/N!)\theta_N<1`$ for every $`k\ge0`$, forcing $`\theta_N=0`$. Hence $`N!S`$ is an integer and $`S`$ is rational.

For the finite implication, suppose $`m\theta_{m-1}<E_m`$. The tail recurrence is $`mE_{m-1}=1+\varepsilon_m+E_m`$, so $`E_{m-1}>E_m/m>\theta_{m-1}\ge0`$, and with $`0<E_{m-1}<1`$ the strict-successor identity gives $`\Delta_m=E_{m-1}-\theta_{m-1}`$. Hence
``` math
1+\varepsilon_m<m\Delta_m=1+\varepsilon_m+E_m-m\theta_{m-1}
 \le1+\varepsilon_m+E_m<1+\varepsilon_m+\frac2m,
```
which contradicts <a href="#long68:eq:finite-escape" data-reference-type="eqref" data-reference="long68:eq:finite-escape">[long68:eq:finite-escape]</a>. ◻

</div>

Escape at a single index does not give a non-unit carry there.

The finite test excludes only the open interval $`1+\varepsilon_m<m\Delta_m<1+\varepsilon_m+2/m`$; it accepts either endpoint and all values outside. The width $`2/m`$ refers to $`m\Delta_m`$; the interval for $`\Delta_m`$ has width $`2/m^2`$. At one index this is a sufficient test for escape, obtained by replacing $`E_m`$ with the upper bound $`2/m`$.

At arbitrarily large integer indices, however, the finite test itself characterises irrationality:
``` math
S\notin\mathbb{Q}\quad\Longleftrightarrow\quad
 \text{\eqref{long68:eq:finite-escape} holds for arbitrarily large integers }m.
```
Only the forward implication remains to be shown. If $`S`$ is irrational, Theorem <a href="#long68:res:carry-equivalence" data-reference-type="ref" data-reference="long68:res:carry-equivalence">8</a> gives $`b_m\ne1`$ at arbitrarily large indices. By <a href="#long68:eq:unit-window" data-reference-type="eqref" data-reference="long68:eq:unit-window">[long68:eq:unit-window]</a>, each such index satisfies $`m\Delta_m\le1+\varepsilon_m`$ or $`m\Delta_m>2+\varepsilon_m`$. Since $`2/m<1`$ for $`m\ge3`$, either alternative implies <a href="#long68:eq:finite-escape" data-reference-type="eqref" data-reference="long68:eq:finite-escape">[long68:eq:finite-escape]</a>. The converse is Proposition <a href="#long68:res:lower-escape" data-reference-type="ref" data-reference="long68:res:lower-escape">10</a>. This is an ordinary consequence of the two proved criteria, not a proof that either occurs infinitely often for $`S`$. The equivalence is over all integer indices; restricting to primes is only a sufficient condition here.

For comparison at a single index, the exact classification is
``` math
\begin{equation}
\label{long68:eq:escape-classification}
 E_m\le m\theta_{m-1}
 \quad\Longleftrightarrow\quad
 b_m\ne1\ \hbox{ or }\ a_m(S)=m-1
 \qquad(m\ge3).
\end{equation}
```

To verify the classification, use $`0<E_j<1`$ to write
``` math
Z_j=\lfloor j!S\rfloor+\mathbf1_{\{\theta_j\ge E_j\}}.
```
Substitution in the carry recurrence gives
``` math
b_m=1-a_m(S)+m\mathbf1_{\{\theta_{m-1}\ge E_{m-1}\}}
                 -\mathbf1_{\{\theta_m\ge E_m\}}.
```
Since $`0\le a_m(S)\le m-1`$, a unit carry has exactly two possibilities: both indicators are zero and $`a_m(S)=0`$, or both are one and $`a_m(S)=m-1`$. In the first case $`m\theta_{m-1}=\theta_m<E_m`$; in the second, $`m\theta_{m-1}\ge m-1>E_m`$. Conversely, $`m\theta_{m-1}<E_m<1`$ forces $`a_m(S)=0`$ and both indicators to be zero, using $`mE_{m-1}=1+\varepsilon_m+E_m`$. It therefore forces a unit carry with zero digit. This proves <a href="#long68:eq:escape-classification" data-reference-type="eqref" data-reference="long68:eq:escape-classification">[long68:eq:escape-classification]</a>, including the equality case in its left-hand inequality.

Thus escape can occur even when $`b_m=1`$, provided the digit is $`m-1`$. This happens at $`m=52`$: exact rational arithmetic gives $`b_{52}=1`$ together with $`52\,\Delta_{52}>1+\varepsilon_{52}+2/52`$, the margin being about $`0.5689674908`$. This example separates the two events at a single index: the finite test can hold at a unit carry. Their occurrence at arbitrarily large indices nevertheless gives equivalent rationality criteria. Since $`52`$ is composite, the example supplies no prime-index instance.

<a id="the-series-with-denominators-nt"></a>

## The series with denominators $`n!+t`$

The same digit argument applies to the other shifts mentioned by Erdős. For an integer $`t\ge-1`$ put $`S_t=\sum_{n\ge2}1/(n!+t)`$ and $`C_t=\sum_{n\ge2}1/\bigl(n!(n!+t)\bigr)`$, so that $`S_t=-tC_t+(e-2)`$.

The restriction $`t\ge-1`$ keeps every denominator positive for $`n\ge2`$; $`t=-2`$ is excluded because its first denominator is zero. All series in this identity converge absolutely. The familiar case $`t=0`$ is $`e-2`$; this example will make the residue condition explicit.

<div id="long68:res:shift-family" class="theorem">

**Theorem 11** (a criterion for the shifts $`t\ge-1`$). *For every integer $`t\ge-1`$, the series $`S_t`$ is rational exactly when
``` math
\bigl\lceil t\,m!\,C_t\bigr\rceil\equiv2\pmod m
```
for all sufficiently large $`m`$, and irrational exactly when that residue is missed cofinally. The member $`t=-1`$ is $`S`$, and the member $`t=0`$ is $`e-2`$, for which the scaled correction is always $`0`$ and hence misses the residue class at every $`m\ge3`$, proving the irrationality of $`e`$.*

</div>

<div class="proof">

*Proof.* Put $`Y=-tC_t`$, so that $`S_t=Y+e-2`$. The proof of Proposition <a href="#long68:res:companion-orbit" data-reference-type="ref" data-reference="long68:res:companion-orbit">9</a> applies to any real $`Y`$: rationality of $`Y+e-2`$ forces $`\lfloor m!Y\rfloor\equiv-2\pmod m`$ eventually. Conversely, that congruence forces the canonical digits of $`Y`$ to equal $`m-2`$ eventually; adding the factorial series of $`e-2`$ leaves an eventually telescoping tail, hence a rational sum. Finally $`\lceil t m!C_t\rceil=-\lfloor m!Y\rfloor`$ translates the congruence. Negation gives the cofinal statement. For $`t=0`$, the left side is zero, which is not congruent to $`2`$ for $`m\ge3`$. ◻

</div>

The $`t=0`$ specialisation recovers the classical irrationality of $`e`$. For $`t\ne0`$, no estimate proving failure of the displayed congruence at arbitrarily large indices is supplied here. This is a statement about the scope of the present argument, not an assertion that every other member has the same current literature status.

<a id="long68:sec:residue"></a>

# A sufficient comparison between the tail and an integer gap

We choose to clear every prime-power level shared by two summand denominators. Each remaining prime then occurs in just one scaled summand denominator, so its maximal exponent cannot cancel. This is a sufficient construction, not a necessary size for a clearing factor: cancellation in the partial sum can make a smaller scale suffice. The remaining denominator will determine the gap to the next integer. For an integer $`p\ge3`$, not necessarily prime, put $`I_p=\{2,\ldots,2p-1\}`$ and $`F_p=(p-1)!`$, and define
``` math
\begin{align*}
 D_p&=\operatorname{lcm}_{\substack{i,j\in I_p\\ i<j}}\gcd(d_i,d_j),
 &C_p&=\operatorname{lcm}(F_p,D_p),\\
 L^{\mathrm{blk}}_p&=\operatorname{lcm}(F_p,d_2,\ldots,d_{2p-1}),
 &R_p&=L^{\mathrm{blk}}_p/C_p .
\end{align*}
```
The integer $`D_p`$ contains the prime powers shared by at least two of the denominators. The integer $`C_p`$ also contains the factorial base $`F_p`$, and $`R_p`$ is the quotient left in the full common denominator. The factors $`C_p`$ and $`R_p`$ need not be coprime: a prime absent from $`F_p`$ with largest exponent $`5`$ and second-largest exponent $`2`$ occurs to powers $`2`$ and $`3`$ in the two factors. This is an illustration of the valuation calculation, not a claimed pattern in a particular factorial block. It will be useful to retain the ratio $`\widetilde C_p=C_p/F_p`$, so that
``` math
\begin{equation}
\label{long68:eq:core-normalisation}
 L^{\mathrm{blk}}_p=C_pR_p=F_p\widetilde C_pR_p .
\end{equation}
```

Including $`F_p`$ in both $`C_p`$ and $`L_p^{\mathrm{blk}}`$ ensures that a fixed rational denominator divides $`C_p`$ for all large $`p`$. The ratio $`\widetilde C_p`$ removes precisely that factorial factor when we estimate the shared part. Put
``` math
T_p=\sum_{i\in I_p}\frac{L^{\mathrm{blk}}_p}{d_i},\qquad
 \rho_p=(-T_p)\bmod R_p,\qquad
 K_p=2p^2(2p-1)! ,
```
with $`\rho_p`$ the least nonnegative representative. All of these depend only on a finite prefix.

For each prime, $`C_p`$ contains the larger of its exponent in $`F_p`$ and its second-largest exponent among the denominators. A prime dividing $`R_p`$ therefore has a unique denominator whose exponent is maximal and exceeds the exponent in $`F_p`$, so the argument of Theorem <a href="#long68:res:prime-pole" data-reference-type="ref" data-reference="long68:res:prime-pole">2</a> applies to it and gives $`\gcd(T_p,R_p)=1`$. Thus $`R_p=\operatorname{den}(C_pH_{2p-1})`$, the reduced denominator of the scaled prefix, not generally of $`H_{2p-1}`$. When $`R_p>1`$, this ratio is nonintegral and
``` math
\begin{equation}
\label{long68:eq:gap-normalisation}
 \frac{\rho_p}{R_p}
 =\bigl\lceil C_pH_{2p-1}\bigr\rceil-C_pH_{2p-1}\in(0,1),
\end{equation}
```
the distance to the next integer. When $`R_p=1`$, $`\rho_p=0`$ but the scaled partial sum is integral, so the least strictly larger integer is at distance $`1`$. The theorem below uses only $`R_p>1`$.

At $`p=3`$, the denominators $`1,5,23,119`$ are pairwise coprime. Thus $`D_3=1`$, $`C_3=2`$, $`R_3=13685`$, and
``` math
C_3H_5=\frac{34264}{13685},\qquad
\frac{\rho_3}{R_3}=3-\frac{34264}{13685}=\frac{6791}{13685}.
```
The tail estimate in the proof below gives $`C_3(S-H_5)<7/1080<6791/13685`$. This verifies the comparison for one actual prefix. The theorem needs such prefixes at arbitrarily large $`p`$, so that $`F_p`$ can absorb any fixed rational denominator.

<div id="long68:res:global-residue" class="theorem">

**Theorem 12** (a sufficient tail inequality). *Suppose that for every $`B`$ there is a natural parameter $`p\ge3`$ with $`p>B`$, $`R_p>1`$, and
``` math
\begin{equation}
\label{long68:eq:global-scale}
 (2p+1)L^{\mathrm{blk}}_p<K_p\rho_p .
\end{equation}
```
Then $`S`$ is irrational.*

</div>

<div class="proof">

*Proof.* Suppose $`S=a/q`$ with $`q\ge1`$, and choose a parameter in the hypothesis with $`p>q`$. Since $`q\mid F_p\mid C_p`$, the number $`C_pS`$ is an integer strictly above $`C_pH_{2p-1}`$. The gap identity <a href="#long68:eq:gap-normalisation" data-reference-type="eqref" data-reference="long68:eq:gap-normalisation">[long68:eq:gap-normalisation]</a> gives
``` math
C_p(S-H_{2p-1})\ge\frac{\rho_p}{R_p}.
```
On the other hand, $`1/(n!-1)<2/n!`$ for $`n\ge2p`$, and comparison with a geometric series of ratio $`1/(2p+1)`$ gives
``` math
S-H_{2p-1}<\frac{2}{(2p)!}\frac{2p+1}{2p}=\frac{2p+1}{K_p}.
```
Multiplication by $`C_p`$ and <a href="#long68:eq:global-scale" data-reference-type="eqref" data-reference="long68:eq:global-scale">[long68:eq:global-scale]</a>, with $`L_p^{\mathrm{blk}}=C_pR_p`$, now give $`C_p(S-H_{2p-1})<\rho_p/R_p`$, a contradiction. ◻

</div>

The formal statement for natural-number parameters is [comparison of the tail with the next integer](https://github.com/wcook04/plectis-erdos/blob/f36a98bf3d3e6f65f1074e3b800e3293d5b8a51a/ErdosProblems/Erdos68/PaperCompleteExisting.lean#L156-L168).

Cancelling $`R_p`$ in <a href="#long68:eq:global-scale" data-reference-type="eqref" data-reference="long68:eq:global-scale">[long68:eq:global-scale]</a> through <a href="#long68:eq:core-normalisation" data-reference-type="eqref" data-reference="long68:eq:core-normalisation">[long68:eq:core-normalisation]</a> displays the quantitative issue directly:
``` math
\begin{equation}
\label{long68:eq:core-gap-scale}
 (2p+1)C_p<K_p\frac{\rho_p}{R_p}.
\end{equation}
```
The factor $`R_p`$ has cancelled. Thus new prime divisors, even large ones, do not by themselves bound $`C_p`$ or keep $`\rho_p/R_p`$ away from zero. Proposition <a href="#long68:res:wilson-cofinality" data-reference-type="ref" data-reference="long68:res:wilson-cofinality">3</a> supplies the primes but not these two estimates.

Under $`R_p>1`$, we have $`\rho_p>0`$, and taking logarithms gives
``` math
\log\widetilde C_p-\log\frac{\rho_p}{R_p}
 <\log\frac{2p^2(2p-1)!}{(2p+1)(p-1)!}
 =p\log p+(2\log2-1)p+O(\log p).
```
Both terms on the left must be controlled at the same $`p`$. The elementary bound $`\rho_p\ge1`$ gives only $`\rho_p/R_p\ge1/R_p`$, which may be too small. For a concrete comparison, a gap of at least $`1/2`$ would reduce the sufficient test to $`(2p+1)C_p<K_p/2`$. At the opposite extreme, the gap $`1/R_p`$ requires the stronger bound $`(2p+1)C_p<K_p/R_p`$. Neither type of favourable behaviour is proved here for an unbounded family of these particular prefixes.

<span id="long68:res:lead-moving-factor-split" label="long68:res:lead-moving-factor-split"></span> <span id="long68:res:moving-factor-scale-split" label="long68:res:moving-factor-scale-split"></span> A more restrictive test also uses a prime $`q`$ that first divides $`m!-1`$ at an index $`m\ge4`$. Choose $`p=\lfloor m/2\rfloor+1`$, which need not be prime. This choice puts $`m`$ in the block and gives $`q\mid R_p`$. Indeed, $`q>m\ge p`$, so $`q\nmid F_p`$, and no earlier denominator contains $`q`$. The only possible later index in the block is $`m+1`$; when it occurs, $`(m+1)!-1\equiv m\not\equiv0\pmod q`$. Thus $`q`$ occurs in just one block denominator and is absent from $`C_p`$.

The additional comparison uses the integer $`R_p/q`$. Requiring the tail bound to be smaller than both $`\rho_p`$ and $`R_p/q`$ gives $`\min(\rho_p,R_p/q)`$ and is equivalent to the following two inequalities:
``` math
\begin{equation}
\label{long68:eq:factor-split}
 (2p+1)L^{\mathrm{blk}}_p<K_p\min(\rho_p,R_p/q)
 \quad\Longleftrightarrow\quad
 \begin{cases}
 (2p+1)L^{\mathrm{blk}}_p<K_p\rho_p,\\
 (2p+1)C_pq<K_p .
 \end{cases}
\end{equation}
```

The equivalence follows by testing each entry of the minimum and using <a href="#long68:eq:core-normalisation" data-reference-type="eqref" data-reference="long68:eq:core-normalisation">[long68:eq:core-normalisation]</a>. Both inequalities must hold for the same arbitrarily large parameters. The first alone is already sufficient by Theorem <a href="#long68:res:global-residue" data-reference-type="ref" data-reference="long68:res:global-residue">12</a>; the second is an extra restriction, not an equivalent formulation of irrationality.

<span id="long68:res:split-factor-normalized-collision" label="long68:res:split-factor-normalized-collision"></span> <span id="long68:bdry:fixed-owner-absorption" label="long68:bdry:fixed-owner-absorption"></span> A fixed small index cannot supply new factors indefinitely. If $`n`$ is fixed and $`p>n!-1`$, then $`n!-1`$ divides $`(p-1)!`$, so none of its prime powers remains outside the factorial base. For example, the factor $`719`$ of $`6!-1`$ is useful only over a finite range of $`p`$. Any argument using such factors at arbitrarily large $`p`$ must let their indices increase.

<a id="long68:sec:channels"></a>

# What can be achieved by cancelling finitely many weighted sums

We next try to remove the first few terms of a remainder by integer linear combinations. The weights are chosen so that their difference from ordinary factorial weights is divisible by $`d!-1`$. This preserves fractional parts after division by $`d!-1`$, while allowing the contributions at selected denominators to vanish. For a finitely supported integer vector $`c=(c_i)`$ on indices $`i\ge2`$, put
``` math
M(c)=\sum_i c_i\,i!,\qquad
 W_{d,i}=\frac{i!}{(d!)^{\lfloor i/d\rfloor}},\qquad
 V_{d}(c)=\sum_i c_iW_{d,i}\quad(d\ge2).
```
We call $`M(c)`$ the moment; it and the weighted sums $`V_d(c)`$ may be negative. The remainder is
``` math
\mathcal R(c)=\sum_{d\ge2}\frac{V_d(c)}{d!-1}.
```
Beyond the support, $`V_d(c)=M(c)`$, so this series converges absolutely. Cancelling its first weighted sums leaves a finite signed block followed by $`M(c)`$ times the original tail. The congruence below explains why this is still an integer linear form in $`1`$ and $`S`$. The power $`(d!)^{\lfloor i/d\rfloor}`$ need not be the largest power of $`d!`$ dividing $`i!`$: at $`d=2`$, $`i=6`$, the chosen exponent is $`3`$, although $`2^4\mid6!`$. We use the floor exponent because it changes between $`i-1`$ and $`i`$ exactly when $`d\mid i`$. Adjacent differences will therefore affect only divisor-indexed weighted sums, which is the reason the elimination in §5.1 works. Each $`W_{d,i}`$ is an integer: writing $`i=kd+r`$ with $`0\le r<d`$, the quotient $`i!/\bigl((d!)^kr!\bigr)`$ is a multinomial coefficient. Since $`i!=(d!)^{\lfloor i/d\rfloor}W_{d,i}`$ and $`d!\equiv1\pmod{d!-1}`$,
``` math
\begin{equation}
\label{long68:eq:channel-congruence}
 V_{d}(c)\equiv M(c)\pmod{d!-1}.
\end{equation}
```

<div id="long68:res:normalform" class="theorem">

**Theorem 13** (divisibility of the difference). *For every finite integer support and every $`d\ge2`$ there is an integer $`k`$ with $`V_{d}(c)=M(c)+(d!-1)k`$.*

</div>

<div class="proof">

*Proof.* By <a href="#long68:eq:channel-congruence" data-reference-type="eqref" data-reference="long68:eq:channel-congruence">[long68:eq:channel-congruence]</a>, $`d!-1`$ divides $`V_d(c)-M(c)`$. Thus $`k=(V_d(c)-M(c))/(d!-1)`$ is an integer and gives the identity. The modulus is positive also at $`d=2`$, when it equals one. ◻

</div>

For any $`N\ge2`$ at least as large as every supported index, the terms with $`d>N`$ equal $`M(c)/(d!-1)`$. Therefore
``` math
\mathcal R(c)-M(c)S
 =\sum_{d=2}^N\frac{V_d(c)-M(c)}{d!-1}\in\mathbb Z.
```
The sum is finite and each term is integral by <a href="#long68:eq:channel-congruence" data-reference-type="eqref" data-reference="long68:eq:channel-congruence">[long68:eq:channel-congruence]</a>. This argument also holds when index $`1`$ is temporarily allowed in the basis calculation below. In particular, a zero-moment vector has integral remainder, and fixed moment fixes the fractional part. These facts do not depend on solving the cancellation equations.

In the next theorem, the parameters $`d,k`$ and the support indices are integers.

<div id="long68:res:bandbreakpoint" class="theorem">

**Theorem 14** (constant values of the floor in the weights). *Let $`d\ge2`$ and $`k\ge0`$, and suppose every supported index $`i`$ satisfies $`kd\le i<(k+1)d`$. Then $`M(c)=(d!)^kV_{d}(c)`$. In particular, cancellation on the interval $`d\le i<2d`$ forces $`M(c)=0`$; and if every supported index is at least $`d`$ while $`M(c)\ne0`$ and $`V_{d}(c)=0`$, then some supported index is at least $`2d`$.*

</div>

<div class="proof">

*Proof.* On this interval the quotient $`\lfloor i/d\rfloor`$ is the constant $`k`$, so $`i!=(d!)^kW_{d,i}`$ for every supported index and the factor $`(d!)^k`$ comes out of the sum. The two consequences follow by taking $`k=1`$ and by contraposition. ◻

</div>

The hypothesis means that all supported indices lie in one interval on which $`\lfloor i/d\rfloor`$ is constant. A single supported index always has this property; indices on opposite sides of a multiple of $`d`$ need not. The conclusion restricts the support of a solution with $`V_d(c)=0`$ and $`M(c)\ne0`$. It neither constructs such a solution nor bounds its infinite remainder.

By <a href="#long68:eq:channel-congruence" data-reference-type="eqref" data-reference="long68:eq:channel-congruence">[long68:eq:channel-congruence]</a>, a vanishing $`d`$-th weighted sum forces $`(d!-1)\mid M(c)`$, and annihilating every weighted sum $`2\le d\le D`$ forces $`L_D\mid M(c)`$, where $`L_D=\operatorname{lcm}_{2\le d\le D}(d!-1)`$ is the same quantity as in §<a href="#long68:sec:lcm" data-reference-type="ref" data-reference="long68:sec:lcm">2</a>. At fixed moment, the same congruence fixes the fractional part of each quotient $`V_d(c)/(d!-1)`$ separately.

<a id="all-solutions-and-their-remainders-modulo-integers"></a>

## All solutions and their remainders modulo integers

Fix $`D\ge2`$. We will solve $`V_2=\cdots=V_D=0`$, impose the restriction that the coefficient at index $`1`$ vanish, and then calculate the resulting infinite remainder. The support restriction is an additional equation, not a consequence of cancelling the weighted sums.

Temporarily allow finitely supported integer vectors on $`n\ge1`$, with $`M`$ and $`V_{d}(\cdot)`$ given by the same formulas; this introduces no term $`1/(1!-1)`$ into $`S`$. Let $`e_n`$ have coefficient $`1`$ at index $`n`$ and zero elsewhere. Adjacent factorials suggest starting with
``` math
T_n=ne_{n-1}-e_n\quad(n\ge2),
```
which has moment zero. The quotient $`\lfloor i/d\rfloor`$ changes between $`i=n-1`$ and $`i=n`$ exactly when $`d\mid n`$, so
``` math
V_{d}(T_n)=(d!-1)W_{d,n}\mathbf1_{d\mid n}.
```
For example, $`T_4=4e_3-e_4`$ has $`V_2(T_4)=6`$ and $`V_4(T_4)=23`$, with all other weighted sums zero. Since $`U_2:=T_2=2e_1-e_2`$ has only $`V_2(U_2)=1`$ nonzero, subtracting $`6U_2`$ leaves only the fourth weighted sum. This suggests removing the contribution of each proper divisor:
``` math
U_n=T_n-\sum_{\substack{d\mid n\\2\le d<n}}W_{d,n}U_d\quad(n\ge2).
```
Induction gives $`M(U_n)=0`$ and $`V_{d}(U_n)=(d!-1)\mathbf1_{d=n}`$. On each finite initial segment, the columns $`e_1,T_2,T_3,\ldots`$ form a triangular integer matrix with diagonal entries $`1,-1,-1,\ldots`$. Its determinant is $`\pm1`$, so it is unimodular. The change from $`T_n`$ to $`U_n`$ is triangular over $`\mathbb Z`$ with diagonal entries $`1`$. Thus $`e_1,U_2,U_3,\ldots`$ is a $`\mathbb Z`$-basis of the finitely supported integer vectors. Applying $`M`$ and each $`V_{d}(\cdot)`$ gives the unique expansion
``` math
c=M(c)\,e_1+\sum_{d\ge2}\frac{V_{d}(c)-M(c)}{d!-1}\,U_d .
```
When $`V_2=\cdots=V_D=0`$, the congruences above force $`L_D\mid M(c)`$. To obtain moment $`L_D`$, define
``` math
K_D=L_De_1-\sum_{d=2}^{D}\frac{L_D}{d!-1}U_d.
```
Then $`M(K_D)=L_D`$ and $`V_{d}(K_D)=0`$ for $`2\le d\le D`$. Consequently every vector of the enlarged space whose weighted sums $`2,\ldots,D`$ vanish has a unique expression
``` math
\begin{equation}
\label{long68:eq:low-channel-basis}
 c=tK_D+\sum_{n>D}z_nU_n,
 \qquad M(c)=tL_D,
\end{equation}
```
with finitely many nonzero integers $`z_n`$. Let $`a_D`$ and $`u_n`$ denote the coefficients at index $`1`$ in $`K_D`$ and $`U_n`$, respectively. Requiring support on $`n\ge2`$ adds precisely the scalar equation
``` math
\begin{equation}
\label{long68:eq:low-channel-support}
 ta_D+\sum_{n>D}z_nu_n=0.
\end{equation}
```
The scalar coefficients satisfy $`u_2=2`$ and $`u_n=-\sum_{d\mid n,\ 2\le d<n}W_{d,n}u_d`$ for $`n>2`$. Every proper divisor of an odd $`n`$ is odd, so induction gives $`u_n=0`$ for odd $`n>1`$. At $`n=2p`$ with $`p`$ prime, only $`d=2`$ contributes a nonzero term; hence $`u_{2p}=-(2p)!/2^{p-1}`$, also for $`p=2`$. If $`p`$ is a prime with $`D/2<p\le D`$ and $`H=D(2p-1)`$, then
``` math
\begin{equation}
\label{long68:eq:finite-horizon}
 \gcd\{u_n:n>D\}=\gcd(u_{D+1},\ldots,u_H)>0,\qquad H<2D^2 .
\end{equation}
```
Indeed, the finite gcd $`g`$ divides $`u_{2p}\ne0`$ and hence $`(2p)!`$. For $`n>H`$ and a divisor $`d\le D`$ of $`n`$ one has $`n/d\ge2p`$. The quotient $`W_{d,n}/(n/d)!`$ counts partitions of $`n`$ points into $`n/d`$ unordered blocks of size $`d`$, so $`(n/d)!\mid W_{d,n}`$ and hence $`g\mid W_{d,n}`$. Strong induction in the recurrence handles the remaining divisors $`D<d<n`$, so $`g`$ divides every $`u_n`$ with $`n>D`$. Bertrand’s postulate supplies $`p`$ for $`D\ge3`$, and $`p=2`$ serves for $`D=2`$; finally $`H\le D(2D-1)<2D^2`$. The short note proves the same determination in its theorem “a finite formula for the gcd”.

<div id="long68:res:moment-ideal" class="theorem">

**Theorem 15** (the set of attainable moments). *Fix $`D\ge2`$ and a prime $`p`$ with $`D/2<p\le D`$. Put
``` math
H=D(2p-1),\qquad
 G_D=\gcd\{|u_n|:D<n\le H\},\qquad
 \mu_D=L_D\frac{G_D}{\gcd(G_D,a_D)}.
```
The moments of finite integer vectors supported on $`n\ge2`$ and cancelling all weighted sums $`2,\ldots,D`$ are exactly $`\mu_D\mathbb{Z}`$. The integer $`\mu_D`$ is positive, is independent of the eligible prime $`p`$, and is attained by a vector of coefficients with gcd one, that is, by a primitive vector.*

</div>

<div class="proof">

*Proof.* By <a href="#long68:eq:finite-horizon" data-reference-type="eqref" data-reference="long68:eq:finite-horizon">[long68:eq:finite-horizon]</a>, $`G_D>0`$ is the gcd of the whole tail $`\{u_n:n>D\}`$, and $`H<2D^2`$. Thus the finite integer combinations in <a href="#long68:eq:low-channel-support" data-reference-type="eqref" data-reference="long68:eq:low-channel-support">[long68:eq:low-channel-support]</a> form $`G_D\mathbb{Z}`$, so that the equation is soluble exactly when $`G_D\mid ta_D`$. Dividing by $`\gcd(G_D,a_D)`$ shows that $`t`$ is a multiple of $`G_D/\gcd(G_D,a_D)`$, and <a href="#long68:eq:low-channel-basis" data-reference-type="eqref" data-reference="long68:eq:low-channel-basis">[long68:eq:low-channel-basis]</a> gives the displayed moment ideal. Bezout coefficients attain its positive generator. If an attaining vector had a nontrivial common coefficient divisor, division by that divisor would produce a smaller positive attainable moment. Hence its coefficients have gcd one. Since the set of attainable moments does not depend on the chosen prime, neither does its least positive element. ◻

</div>

For a concrete instance, take $`D=4`$. One first needs $`\operatorname{lcm}(1,\ldots,n)\mid u_n`$, not just a list of computed coefficients. For $`d\mid n`$, Legendre’s formula shows that the valuation of $`W_{d,n}`$ at a prime $`r`$ is at least the number of powers of $`r`$ in $`(d,n]`$: each such power contributes at least $`1`$ to $`\sum_{j\ge1}(\lfloor n/r^j\rfloor-(n/d)\lfloor d/r^j\rfloor)`$, and the other terms are nonnegative. Hence $`\operatorname{lcm}(1,\ldots,n)\mid W_{d,n}\operatorname{lcm}(1,\ldots,d)`$, and induction in the recurrence for $`u_n`$ proves the divisibility. It follows that $`60`$ divides every $`u_n`$ with $`n>4`$. Conversely, $`u_6=-180`$, $`u_8=-4200`$ and $`23u_6-u_8=60`$, so $`G_4=60`$. Since $`L_4=115`$ and $`a_4=-55`$, the least positive moment is therefore $`115\cdot60/\gcd(60,55)=1380`$. The vector $`12K_4+253U_6-11U_8`$ attains it: its coefficient at index $`1`$ is $`12(-55)+253(-180)-11(-4200)=0`$. This example uses the gcd of the entire tail, not only the observed coefficients.

If support is additionally restricted to $`n\le6`$, only $`u_5=0`$ and $`u_6=-180`$ remain available in <a href="#long68:eq:low-channel-support" data-reference-type="eqref" data-reference="long68:eq:low-channel-support">[long68:eq:low-channel-support]</a>. The least positive moment is then $`115\cdot180/\gcd(180,55)=4140`$. Minimising the moment and minimising the largest supported index are therefore different problems.

The factor beyond $`L_D`$ is not always $`12`$. At $`D=6`$, the same recurrence gives
``` math
L_6=9839515,\qquad a_6=-2242555,\qquad G_6=840.
```
To verify the last value, $`u_7=0`$, while $`840=\operatorname{lcm}(1,\ldots,8)`$ divides every $`u_n`$ for $`n\ge8`$ by the preceding divisibility. Conversely, $`u_8=-4200`$, $`u_{12}=-14386680`$ and $`\gcd(u_8,u_{12})=840`$. Thus $`\gcd(G_6,a_6)=35`$ and the least positive moment is $`\mu_6=24L_6`$, not $`12L_6`$. It is attained by $`24K_6-16240U_8+U_{12}`$: the coefficient at index $`1`$ is zero and the coefficient at $`12`$ is $`-1`$. The attainable-moment formula records restrictions that the uniform factor $`12`$ alone does not capture.

We can now express the remainder using the basis coefficients in <a href="#long68:eq:low-channel-basis" data-reference-type="eqref" data-reference="long68:eq:low-channel-basis">[long68:eq:low-channel-basis]</a>. This refines the integer-difference identity at the start of §<a href="#long68:sec:channels" data-reference-type="ref" data-reference="long68:sec:channels">5</a> by giving its integer term explicitly for the classified vectors.

<div id="long68:res:residual-transparency" class="theorem">

**Theorem 16** (how the coefficient choices change the remainder). *For the vector in <a href="#long68:eq:low-channel-basis" data-reference-type="eqref" data-reference="long68:eq:low-channel-basis">[long68:eq:low-channel-basis]</a>,
``` math
\mathcal R\!\left(tK_D+\sum_{n>D}z_nU_n\right)
 =tL_D(S-H_D)+\sum_{n>D}z_n.
```
The residual series converges for every finite vector supported away from index zero. A zero-moment vector has integral residual, and any two finite vectors with the same factorial moment have residuals differing by an integer.*

</div>

<div class="proof">

*Proof.* For $`d>D`$, we have $`V_d(K_D)=L_D`$ and $`V_d(U_n)/(d!-1)=\mathbf1_{d=n}`$. Summing these identities gives $`tL_D(S-H_D)+\sum_{n>D}z_n`$, as claimed. The first series converges and the second sum is finite.

Absolute convergence and the general integer-difference identity were proved at the start of §<a href="#long68:sec:channels" data-reference-type="ref" data-reference="long68:sec:channels">5</a>, including for the auxiliary index $`1`$. Setting the moment to zero proves integrality; subtracting the identity for two vectors of equal moment proves the last assertion. ◻

</div>

Formal counterparts are linked for [a primitive vector attaining the least positive moment](https://github.com/wcook04/plectis-erdos/blob/f20f727ae44d6dc3b24036bf63118b8fe591912e/ErdosProblems/Erdos68/PaperCompleteMomentIdeal.lean#L242) (Theorem <a href="#long68:res:moment-ideal" data-reference-type="ref" data-reference="long68:res:moment-ideal">15</a>) and [the integer difference between remainders with equal moments](https://github.com/wcook04/plectis-erdos/blob/f20f727ae44d6dc3b24036bf63118b8fe591912e/ErdosProblems/Erdos68/PaperCompleteResidualIdentity.lean#L195) (Theorem <a href="#long68:res:residual-transparency" data-reference-type="ref" data-reference="long68:res:residual-transparency">16</a>).

The factor $`12`$ used below follows directly on support $`n\ge2`$. For $`n=2,3`$ one has $`n!=2W_{2,n}`$. For $`n\ge4`$, both $`n!`$ and $`2W_{2,n}`$ are divisible by $`12`$: if $`n=2k`$ or $`2k+1`$, then $`W_{2,2k}=k!\prod_{j=1}^k(2j-1)`$ is divisible by $`6`$ for $`k\ge2`$. Thus $`12\mid M(c)-2V_2(c)`$. Every $`d!-1`$ is coprime to $`6`$, so $`V_2=\cdots=V_D=0`$ implies $`12L_D\mid M(c)`$. This factor is attained at $`D=2`$ and $`D=3`$ by $`-6e_2+e_4`$ and $`-6e_2-8e_3+5e_4`$, respectively. The depth-$`6`$ example above shows why it is not always the whole restriction.

The basis formula <a href="#long68:eq:low-channel-basis" data-reference-type="eqref" data-reference="long68:eq:low-channel-basis">[long68:eq:low-channel-basis]</a> describes all solutions of the weighted-sum equations, and <a href="#long68:eq:low-channel-support" data-reference-type="eqref" data-reference="long68:eq:low-channel-support">[long68:eq:low-channel-support]</a> imposes the support restriction. The remainder identity then determines their residues modulo $`\mathbb{Z}`$. In particular, $`\mathcal R(c)`$ is an integer linear form in $`1`$ and $`S`$, and its distance from the nearest integer equals that of $`M(c)S`$. Integer translation can choose a representative near zero, but cannot change this distance. To exclude every rational denominator this way, each positive integer $`q`$ must divide the moment of some nonintegral remainder in the family. Eventual divisibility by every fixed $`q`$ is sufficient; growth of the moments alone is not. For example, the compulsory factor $`12L_D`$ has $`3`$-adic valuation exactly $`1`$ for every $`D`$, so this necessary divisor alone never guarantees that $`9`$ divides the moment.

A truncation cutoff can exceed the largest supported index without changing the vector. For example, $`c=-6e_2+e_4`$ has $`M(c)=12`$ and $`\mathcal R(c)=12S-17`$. At cutoff $`4`$, its finite part is $`-239/115`$: the gap $`9/115`$ is smaller than the tail bound $`24/119`$. At cutoff $`5`$, the finite part is $`-27061/13685`$, whose gap $`13376/13685`$ exceeds the new bound $`24/719`$. Thus the second cutoff certifies nonintegrality of the same remainder, although the first does not. This excludes only denominators dividing $`12`$, already covered by the finite exclusions.

For fixed $`c`$ with $`M(c)>0`$, the finite part increases to $`\mathcal R(c)`$, with omitted tail $`M(c)(S-H_N)`$. The upper bound $`2M(c)/((N+1)!-1)`$ is smaller than the finite part’s gap to the next integer at every sufficiently large cutoff if and only if $`\mathcal R(c)\notin\mathbb{Z}`$. Indeed, for a nonintegral remainder the gap is eventually at least $`\lfloor\mathcal R(c)\rfloor+1-\mathcal R(c)>0`$, whereas the upper bound tends to zero. For an integral remainder, the eventual gap equals the omitted tail itself and is smaller than that upper bound. At any one cutoff, success places the remainder strictly above the finite part and below the least integer strictly exceeding it, so it implies nonintegrality. The short note writes out the inequality in its section “The remaining real comparison”; increasing the cutoff alone does not prove that it succeeds. This is a truncation choice, distinct from prescribing the largest nonzero coefficient index.

To impose this small-tail comparison at the largest supported index, one needs more than $`L_D\mid M`$: the positive moment must also fit below a factorial at that index. The next theorem combines those two demands at $`D=2t^2`$. Its variable $`R`$ is a support parameter, not the remainder or the modulus $`R_p`$ of the preceding section. If a larger truncation cutoff is used instead, the same numerical bound applies to that cutoff, not to the vector’s actual support. The extra size assumption on $`M`$ is not a consequence of cancelling the weighted sums.

<span id="long68:res:lead-channel-radius" label="long68:res:lead-channel-radius"></span>

<div id="long68:res:channel-radius" class="theorem">

**Theorem 17** (a lower bound for the support parameter). *Let $`t,M,R\in\mathbb{N}`$ satisfy
``` math
t\ge2^{32},\qquad M>0,\qquad L_{2t^2}\mid M,\qquad M<(R+1)!-1 .
```
Then $`3t^3<2(R+1)`$. Consequently no family satisfying these hypotheses for all sufficiently large $`t`$ has $`(R(t)+1)/t^3\le3/2`$ eventually, and none has $`R(t)=o(t^3)`$.*

</div>

<div class="proof">

*Proof.* Put $`D=2t^2`$, $`k=2t`$ and $`u=D-k+1=2t^2-2t+1`$. Lemma <a href="#long68:res:segment" data-reference-type="ref" data-reference="long68:res:segment">6</a> at $`N=D`$, with $`n!-1\ge n!/2`$ and $`\log n!\ge n\log n-n`$, and with $`L_D\le M<(R+1)!`$, gives
``` math
\begin{equation}
\label{long68:eq:radius-log}
 2t\bigl(u\log u-u-\log2\bigr)
 <(R+1)\log(R+1)+\binom{2t+1}{3}\log(2t^2).
\end{equation}
```

Suppose $`R+1\le\tfrac32t^3`$. Since $`t\ge16`$ one has $`\tfrac{15}{8}t^2\le u\le2t^2`$ and $`\log u\ge2\log t`$, so the left side of <a href="#long68:eq:radius-log" data-reference-type="eqref" data-reference="long68:eq:radius-log">[long68:eq:radius-log]</a> is at least $`\tfrac{15}{2}t^3\log t-4t^3-2t\log2`$. Using $`\binom{2t+1}{3}<\tfrac43t^3`$ and $`\log\tfrac32<\log2`$, the right side is at most
``` math
\tfrac32t^3\bigl(\log2+3\log t\bigr)+\tfrac43t^3\bigl(\log2+2\log t\bigr).
```
Dividing by $`t^3`$ and rearranging, <a href="#long68:eq:radius-log" data-reference-type="eqref" data-reference="long68:eq:radius-log">[long68:eq:radius-log]</a> would require
``` math
\tfrac13\log t<4+\frac{2\log2}{t^2}+\tfrac{17}6\log2 .
```
But $`\log t\ge32\log2`$ and $`\tfrac23<\log2<1`$ give $`\tfrac13\log t-\tfrac{17}6\log2\ge\tfrac{47}6\log2>5`$, while $`4+2\log2/t^2<5`$. This contradiction proves the finite inequality, and the two sequence conclusions follow. ◻

</div>

These hypotheses are compatible: for a fixed $`t`$, one may take $`M=L_{2t^2}`$ and then choose $`R`$ large enough. The restriction is on how small $`R`$ can be. Vanishing of $`V_2,\ldots,V_{2t^2}`$ forces the divisibility condition, but not the upper bound $`M<(R+1)!-1`$. An application to a remainder estimate must establish that additional size bound and $`M>0`$. The theorem then rules out a parameter growing more slowly than cubically. It is a bound on the actual support only when $`R`$ denotes its largest index and the stated size condition holds there; it does not prove irrationality.

Theorem <a href="#long68:res:lcm-growth" data-reference-type="ref" data-reference="long68:res:lcm-growth">7</a> raises the asymptotic constant in the same estimate.

<div id="long68:res:radius-constant" class="corollary">

**Corollary 18** (the asymptotic lower bound). *Let $`M(t),R(t)`$ satisfy $`M(t)>0`$, $`L_{2t^2}\mid M(t)`$ and $`M(t)<(R(t)+1)!-1`$ for all sufficiently large $`t`$. Then
``` math
\liminf_{t\to\infty}\frac{R(t)+1}{t^3}\ \ge\ \frac{16}{9}.
```*

</div>

<div class="proof">

*Proof.* Put $`r=R(t)+1`$, so $`L_{2t^2}\le M(t)<r!`$ and $`\log L_{2t^2}<r\log r`$. Since
``` math
\frac{(2t^2)^{3/2}\log(2t^2)}{t^3\log t}\longrightarrow4\sqrt2,
```
Theorem <a href="#long68:res:lcm-growth" data-reference-type="ref" data-reference="long68:res:lcm-growth">7</a> gives, for every $`\varepsilon>0`$ and all sufficiently large $`t`$,
``` math
\log L_{2t^2}\ge
 \Bigl(\tfrac{16}{3}-\varepsilon\Bigr)t^3\log t.
```
Suppose $`r\le ct^3`$ for arbitrarily large $`t`$, with $`0<c<16/9`$ fixed. On that subsequence $`r\log r\le ct^3(3\log t+\log c)=\bigl(3c+o(1)\bigr)t^3\log t`$. Choosing $`0<\varepsilon<16/3-3c`$ contradicts the lower bound for sufficiently large $`t`$. ◻

</div>

This corollary does not assert the strict inequality $`R+1>\tfrac{16}9t^3`$ eventually. Indeed, the finite logarithmic constraint <a href="#long68:eq:radius-log" data-reference-type="eqref" data-reference="long68:eq:radius-log">[long68:eq:radius-log]</a> allows equality at that constant. To check this directly, set $`R+1=16t^3/9`$ with $`t\ge4`$. Since $`u=2t^2-2t+1\le2t^2`$ and $`x\log x-x`$ is increasing for $`x\ge1`$, the left side of <a href="#long68:eq:radius-log" data-reference-type="eqref" data-reference="long68:eq:radius-log">[long68:eq:radius-log]</a> is at most $`4t^3(\log(2t^2)-1)-2t\log2`$. Subtracting this bound from the right side gives
``` math
t^3\left(4+\frac{16}{9}\log\frac{16}{9}-\frac83\log2\right)
 +t\left(\frac53\log2-\frac23\log t\right)
 >\frac43t^3-\frac23t^2>0,
```
where $`\log2<1`$ and $`\log t\le t`$ suffice for the last comparison. Integer pairs with $`9(R+1)=16t^3`$ exist for every multiple $`t\ge6`$ of $`3`$. This verifies the numerical constraint, not the existence of a coefficient vector with that support. The asymptotic assertion in Corollary <a href="#long68:res:radius-constant" data-reference-type="ref" data-reference="long68:res:radius-constant">18</a> instead follows from Theorem <a href="#long68:res:lcm-growth" data-reference-type="ref" data-reference="long68:res:lcm-growth">7</a>; the finite-block Lean source does not carry that deduction. The corresponding Lean source statement is [the asymptotic lower bound for the support parameter](https://github.com/wcook04/plectis-erdos/blob/0b500c7cf8e8bb7ae343484378df02f277fb8194/lean/ErdosProblems/Erdos68/PaperCompleteLiminf.lean#L54).

At a prime index, the two-term vector $`T_p`$ already changes only one weighted sum; there are no proper divisors to eliminate.

<div id="long68:res:translator" class="theorem">

**Theorem 19** (changing just one weighted sum). *Let $`p\ge3`$ be prime and let $`c_{p-1}=p`$, $`c_p=-1`$, with every other coefficient zero. Then $`M(c)=0`$, $`V_{p}(c)=p!-1`$, and $`V_{d}(c)=0`$ for every $`d\ge2`$ with $`d\ne p`$.*

</div>

<div class="proof">

*Proof.* Since $`p\ge3`$, both indices $`p-1`$ and $`p`$ lie in the prescribed coefficient domain $`i\ge2`$. The moment is $`p\,(p-1)!-p!=0`$. For $`2\le d<p`$ the quotient identity $`\lfloor(p-1)/d\rfloor=\lfloor p/d\rfloor`$ holds, since $`d\nmid p`$, so the two factorial weights carry the same power of $`d!`$ and the weighted sum evaluates to $`p\,(p-1)!/(d!)^{\lfloor p/d\rfloor}-p!/(d!)^{\lfloor p/d\rfloor}=0`$. For $`d>p`$ both indices lie below $`d`$, so both weights are the plain factorials and the same cancellation occurs. At $`d=p`$ the weights are $`(p-1)!`$ and $`p!/p!=1`$, giving $`p\,(p-1)!-1=p!-1`$. ◻

</div>

For $`p=2`$, the same auxiliary identities would require $`c_1=2`$. They do not define an admissible vector on the domain $`i\ge2`$, since every vector supported on that domain has $`c_1=0`$.

Adding an integer multiple of this vector changes $`V_p`$ by that multiple of $`p!-1`$, without changing $`M`$ or any other $`V_d`$. Suppose $`c`$ has nonzero moment, $`V_2(c)=\cdots=V_D(c)=0`$, and every supported index exceeds a prescribed integer $`B`$. Choose a prime $`p>\max(D,B+1,2)`$ and replace $`c`$ by
``` math
c-\lfloor\mathcal R(c)+1/2\rfloor T_p.
```
Both new indices, $`p-1`$ and $`p`$, exceed $`B`$. Since $`p>D`$, the prescribed weighted sums remain zero, and the moment is unchanged. The new remainder is $`\mathcal R(c)-\lfloor\mathcal R(c)+1/2\rfloor\in[-1/2,1/2)`$. The progression construction below supplies such an initial vector: choose its first index $`r>B`$.

This rounding proves a size bound, not nonvanishing: an integral remainder becomes zero. In fact, a rounded remainder is nonzero exactly when the original remainder is nonintegral. Choosing larger adjustment primes cannot extend the denominator coverage, since the moment stays fixed. The chosen integer $`\lfloor\mathcal R(c)+1/2\rfloor`$ depends on the remainder itself. The formula establishes the existence of a representative in the stated interval; it does not independently certify that this representative is nonzero.

<a id="a-primitive-solution-on-an-arithmetic-progression."></a>

#### A primitive solution on an arithmetic progression.

To extend the example $`-6e_2+e_4`$ to cancellation at larger $`D`$, place the support on an arithmetic progression with its first index prescribed. Let $`D,r\ge2`$ and let $`\ell`$ be a positive multiple of $`2,\ldots,D`$. Equal spacing makes $`V_d=0`$ a root condition at $`(d!)^{-\ell/d}`$. We choose the degree-$`D-1`$ polynomial with exactly these roots and scale its coefficients so that the last supported coefficient is $`1`$. Put
``` math
i_j=r+j\ell\ (0\le j<D),\quad N=r+(D-1)\ell,\quad
\alpha_d=(d!)^{\ell/d},
```
``` math
\prod_{d=2}^D(\alpha_dX-1)=\sum_{j=0}^{D-1}h_jX^j,
\qquad A=\prod_{d=2}^D\alpha_d.
```
At index $`i_j`$ put the coefficient
``` math
c_{i_j}=\frac{N!h_j}{A i_j!},
```
and put every other coefficient equal to zero. We verify that these coefficients are integers and that $`V_2=\cdots=V_D=0`$. For $`2\le d\le D`$, divisibility of $`\ell`$ by $`d`$ gives $`\lfloor i_j/d\rfloor=\lfloor r/d\rfloor+j\ell/d`$. Hence
``` math
V_d(c)=
\frac{N!}{A(d!)^{\lfloor r/d\rfloor}}
\sum_{j=0}^{D-1}h_j\alpha_d^{-j}=0,
```
because $`\alpha_d^{-1}`$ is a root of the displayed polynomial. Evaluating that polynomial at $`1`$ gives the moment
``` math
M=N!\prod_{d=2}^D(1-1/\alpha_d)>0.
```

For integrality, each term of $`h_j/A`$ is, up to sign, the reciprocal of a product of $`D-1-j`$ distinct factors $`\alpha_d`$. In that denominator, each selected $`d`$ contributes $`\ell/d`$ blocks of size $`d`$. The total size is $`(D-1-j)\ell=N-i_j`$, so the multinomial coefficient shows that this denominator divides $`N!/i_j!`$. Thus every $`c_{i_j}`$ is an integer. Since $`h_{D-1}=A`$, the coefficient at $`N`$ is $`1`$, and the coefficients have gcd one. This does not establish minimal support. The smallest permitted step is $`\ell=\operatorname{lcm}(2,\ldots,D)`$; taking $`D=r=\ell=2`$ recovers $`-6e_2+e_4`$.

The stronger divisibility
``` math
r!\prod_{d=2}^D(\ell/d)!\prod_{d=2}^D(\alpha_d-1)\mid M
```
follows because
``` math
\frac{N!}{r!\,A\prod_{d=2}^D(\ell/d)!}
```
is an integer: it counts partitions into one distinguished block of size $`r`$ and, for each $`d`$, an unordered collection of $`\ell/d`$ blocks of size $`d`$. Their sizes sum to $`N`$. Using $`M=(N!/A)\prod_{d=2}^D(\alpha_d-1)`$ now gives the asserted divisibility. Put $`v=\max(r,\ell/2)`$, an integer since $`2\mid\ell`$. The displayed factor divides $`M`$, so $`v!\mid M`$. Since $`D\le\ell\le2v`$ and $`r\le v`$,
``` math
N=r+(D-1)\ell\le4v^2-v<4v^2,
 \qquad v\ge\lfloor\sqrt N/2\rfloor+1.
```
Consequently $`(\lfloor\sqrt N/2\rfloor+1)!\mid M`$. Every positive integer $`q\le\lfloor\sqrt N/2\rfloor+1`$ therefore divides $`M`$, as does every divisor of that factorial. In particular, $`N\ge4(q-1)^2`$ suffices for $`q\mid M`$. This includes denominators growing with $`N`$.

The construction also supplies the required absolute smallness of the omitted tail at its own support endpoint. Every factor $`1-1/\alpha_d`$ lies strictly between $`0`$ and $`1`$, so $`0<M<N!`$ and
``` math
0<M(S-H_N)<\frac{2M}{(N+1)!-1}<\frac2N,
```
where the last inequality follows from $`(N+1)!-1>NN!`$ for $`N\ge2`$. In particular, the moment obeys $`M<(N+1)!-1`$ without an additional hypothesis for this family. What is not established is that the displayed upper bound is smaller than the finite part’s gap to the next integer. That gap depends on the same vector and may shrink with $`N`$; an upper bound tending to zero does not supply the required comparison. Neither this size estimate nor the divisibility proves nonintegrality of the remainders.

<a id="long68:sec:finite"></a>

# Finite denominator exclusions

<span id="long68:res:lead-denominator-exclusions" label="long68:res:lead-denominator-exclusions"></span>

Two finite computations constrain a hypothetical denominator $`q`$ in $`S=a/q`$, and they constrain different features of it:
``` math
\begin{equation}
\label{long68:eq:finite-bounds}
 q\nmid299999!,\qquad q\ge2^{39990}>10^{12038}.
\end{equation}
```
The size bound holds for every integer $`a`$ and positive natural $`q`$ with $`S=a/q`$; no reducedness assumption is needed. Its evidence is the exact continued-fraction computation described below. The stronger candidate [finite-size Lean certificate](https://github.com/wcook04/plectis-erdos/blob/27c2fc5fe3c55fe547feaeb4c9bb68b3cf63a5bf/lean/ErdosProblems/Erdos68/PaperCompleteFiniteSizeCertificate.lean#L58) is not cited as kernel verification: its source records that the computation has not yet been kernel checked. The factorial-grid exclusion $`q\nmid299999!`$ is supported separately by the external GMP computation; its full Lean certificate also remains an outstanding formal obligation.

Neither condition implies the other. The prime $`300007`$ fails to divide $`299999!`$ but is smaller than $`2^{39990}`$, whereas $`299999!`$ satisfies the size lower bound but fails the nondivisibility condition. High powers of small primes further show why nondivisibility is not a smoothness exclusion.

The first exclusion comes from an exact interval carry census. The supplied record describes an independently implemented GMP integer computation certifying all $`299998`$ carry cells for $`3\le m\le300000`$ with a scale of $`2^{5025679}`$ and $`96`$ guard bits, using no floating-point arithmetic; at every step the outward interval is proved to lie inside one half-open unit cell before the carry is recorded. Its unit carries occur exactly at
``` math
52,\ 591,\ 1030,\ 1407,\ 1438,\ 2164,\ 4258,\ 10991,\ 21236,
```
so $`b_{300000}\ne1`$. Theorem <a href="#long68:res:carry-equivalence" data-reference-type="ref" data-reference="long68:res:carry-equivalence">8</a> then gives $`q\nmid299999!`$ and in particular $`q\ge300000`$. The full-range carry replay reported in the supplied manuscript was not repeated for this prose revision. A separately recorded replay through $`m=4000`$ reproduces the unit-carry prefix $`52,591,1030,1407,1438,2164`$ with a non-unit carry at the endpoint, giving $`q\ge4000`$ on its own. These are external computations; the implication from a non-unit carry to a factorial-divisibility exclusion is the kernel-checked statement.

The first exclusion says that the least positive integer $`r`$ with $`q\mid r!`$ is at least $`300000`$. This is the factorial index used by Sondow \[sondow2006, §3, Theorem 1\], not the largest prime factor of $`q`$. No approximation bound for $`e`$ is being applied to $`S`$.

The second exclusion has a short integer description. Put $`D=2^{80000}`$ and let $`N`$ be the first integer with $`N!-1>D`$. Define
``` math
\ell=\sum_{n=2}^{N-1}\left\lfloor\frac D{n!-1}\right\rfloor,
 \qquad
 u=\ell+(N-2)+\left\lfloor\frac{2D}{N!-1}\right\rfloor+1 .
```
Each rounded prefix term loses less than one. Since $`(n+1)!-1>(n+1)(n!-1)`$, successive terms in the tail from $`N`$ have ratio less than $`1/(N+1)`$. Their sum is consequently smaller than $`(N+1)/(N(N!-1))<2/(N!-1)`$, proving $`\ell/D<S<u/D`$.

There are exactly $`N-2`$ rounded prefix terms. The extra $`+1`$ in $`u`$ keeps the upper enclosure strict even if $`2D/(N!-1)`$ happens to be an integer; the positive omitted tail keeps the lower enclosure strict. Here $`N=7054`$ and $`u-\ell=7053`$. Apply the continued-fraction algorithm to both endpoints at once, retaining a quotient only while the integer parts agree and both remainders are nonzero, and reversing the endpoint order at each inversion. There are $`23449`$ common quotients, and the convergent denominators
``` math
Q_{-2}=1,\quad Q_{-1}=0,\quad Q_j=a_jQ_{j-1}+Q_{j-2}
```
satisfy $`Q_{23448}\ge2^{39990}`$. Every rational in the open enclosure shares this initial segment, so its reduced denominator is at least $`Q_{23448}`$. Indeed, write $`P_j`$ for the convergent numerators. Such a rational either equals $`P_{23448}/Q_{23448}`$ or has a complete quotient $`A/B>1`$ after the segment, with $`A`$ and $`B`$ coprime, and then equals $`(P_{23448}A+P_{23447}B)/(Q_{23448}A+Q_{23447}B)`$; the determinant identity $`P_jQ_{j-1}-P_{j-1}Q_j=\pm1`$ makes both fractions reduced \[nist-dlmf, §1.12(ii), (1.12.5)–(1.12.7), (1.12.20)–(1.12.21)\]. The argument is about a common prefix and does not require the last convergent to lie inside the enclosure. The integer comparison $`2^{39990}>10^{12038}`$ closes <a href="#long68:eq:finite-bounds" data-reference-type="eqref" data-reference="long68:eq:finite-bounds">[long68:eq:finite-bounds]</a>. The [integer replay](https://github.com/wcook04/plectis-erdos/blob/cd3bd6fe245867a435e15d503ccedd699c5d02e2/scripts/check_erdos68_continued_fraction.py) and its [receipt](https://github.com/wcook04/plectis-erdos/blob/cd3bd6fe245867a435e15d503ccedd699c5d02e2/verification/erdos68-continued-fraction.json) record scale $`80000`$ bits, bracket width $`7053`$, $`23449`$ certified partial quotients, power-of-two exponent $`39990`$ and strict decimal exponent $`12038`$.

<a id="carry-computation-record."></a>

#### Carry computation record.

The receipt `verification/erdos68-strict-successor.json`, with schema `erdos68_strict_successor_exact_interval_v1`, records the scale and guard bits above, the driver and backend used for its run, the event-trace digest, and the final enclosure. The source packet names the driver `scripts/check_erdos68_strict_successor.py` and the backend `scripts/check_erdos68_strict_successor_gmp.cpp`. Their published digests, followed by the receipt payload digest, are

> Driver: `f25b5bd8ffbfd66bdbb42ca6a07a936aab9b4eb7d3a57446725be55acb642191`.\
> Backend: `43308ddc3902dd537b789ae6e0648054a0d752adf07e5d6e1d829811e9342083`.\
> Payload: `044ef27a60f7294c39b8279b7f04e22e1234a942e2862e9e8c64eb66505af29b`.

The supplied record states that the event trace and unit-carry certificate match the previously retained receipt. These identifiers distinguish the reported full run from the separate computation through $`4000`$; they do not certify a new replay in this revision.

Both certificates are finite. A further computation can enlarge an exclusion, but need not do so: a narrower enclosure may retain the same common continued-fraction prefix, and a later unit carry supplies no new carry exclusion. Neither finite calculation excludes an eventual unit-carry tail. The continued-fraction identities are classical \[nist-dlmf, §1.12(ii)\]; the enclosure, the prefix length and the exponent are outputs of the computation above.

<a id="long68:sec:open"></a>

# The remaining arithmetic inputs

The exact target is $`m\nmid Z_m`$ at arbitrarily large indices, as in <a href="#long68:eq:strict-misses" data-reference-type="eqref" data-reference="long68:eq:strict-misses">[long68:eq:strict-misses]</a>; the equivalent comparison with fractional parts is <a href="#long68:eq:lower-escape" data-reference-type="eqref" data-reference="long68:eq:lower-escape">[long68:eq:lower-escape]</a>. The estimates discussed below would suffice for this target but are not proved here. The finite test <a href="#long68:eq:finite-escape" data-reference-type="eqref" data-reference="long68:eq:finite-escape">[long68:eq:finite-escape]</a> implies escape at each index; its occurrence at arbitrarily large integer indices is also equivalent to irrationality, as proved in §<a href="#long68:sec:carry" data-reference-type="ref" data-reference="long68:sec:carry">3</a>. Thus the missing step is to prove that this actual rational sequence meets the test at arbitrarily large indices, not to supply another equivalence. Restricting to a prime subsequence or replacing a numerator by a residue imposes additional conditions. A model obeying only selected congruences is not the actual sequence.

<a id="value-sets-do-not-determine-the-weighted-residue-sum."></a>

#### Value sets do not determine the weighted residue sum.

Garaev, Luca and Shparlinski’s harmonic-sum estimate \[garaev-luca-shparlinski-harmonic, Theorem 1 and (5)\] concerns unconditioned harmonic sums, not sums restricted to the indices where $`n!\equiv1\pmod q`$. The value-set literature addresses different invariants. Banks, Luca, Shparlinski and Stichtenoth \[banks-et-al2005\] provide historical missing-value context; Klurman and Munsch \[klurman-munsch2017, Theorems 2.1–2.2\] distinguish unconditional averages from GRH-dependent improvements. Grebennikov, Sagdeev, Semchankau and Vasilevskii \[grebennikov-et-al2024, Corollaries 1.2 and 1.4\] study sizes of value and quotient sets, as do the factorial-residue and representation results of Hu \[hu2026\] and Garaev and Pardo \[garaev-pardo2026\]. None is a noncancellation theorem for the reciprocal unit weights here. A lower bound for the number of distinct residues does give an upper bound on the multiplicity of residue $`1`$, since every other value needs at least one index. But that bound does not determine the reciprocal unit weights or test whether they cancel modulo $`q`$. The two explicit cancellations in §<a href="#long68:sec:prime-powers" data-reference-type="ref" data-reference="long68:sec:prime-powers">1</a> illustrate why the weights matter. Hu’s September preprint \[hu-september2026, Theorem 3.1\] considers pairwise distinct maps $`T_\theta(x)=b_\theta+c_\theta/x`$ over $`\mathbb F_p`$, with $`c_\theta\ne0`$. An internal transition is a pair $`(x,\theta)`$ for which $`x\in A\smallsetminus\{0\}`$ and $`T_\theta(x)\in A`$. With at least $`M`$ distinct such pairs, at most $`|A|`$ parameters, and a bound $`\mu\ge1`$ on the number of ordered parameter pairs representing each nonidentity map $`T_\eta T_\theta^{-1}`$, the theorem gives $`|A|\gg\min\{M,p\}^{8/15}\mu^{-4/15}`$. Its incidence estimate comes from Stevens and de Zeeuw \[stevens-dezeeuw2017, Theorem 4\]. To apply this to the residue classes of indices satisfying $`n!\equiv1\pmod q`$, one would first have to specify the set $`A`$ and the transition maps. The number of such indices is not automatically a lower bound for $`M`$: different indices may produce the same pair $`(x,\theta)`$, and their factorial values are all $`1`$. One must prove that enough distinct transitions remain, as well as bound the ordered-pair multiplicity $`\mu`$. The unconditioned value-set theorem does not provide these additional facts.

<a id="the-shared-denominator-and-the-gap-must-be-controlled-together."></a>

#### The shared denominator and the gap must be controlled together.

For the blocks selected from first prime occurrences, the second inequality in <a href="#long68:eq:factor-split" data-reference-type="eqref" data-reference="long68:eq:factor-split">[long68:eq:factor-split]</a> is
``` math
\begin{equation}
\label{long68:eq:weighted-target}
 \log\widetilde C_p
 <\log\left(\frac{2p^2}{2p+1}\cdot
       \frac{\prod_{j=p}^{2p-1}j}{q}\right).
\end{equation}
```
The first inequality is <a href="#long68:eq:global-scale" data-reference-type="eqref" data-reference="long68:eq:global-scale">[long68:eq:global-scale]</a>. Both must hold at the same arbitrarily large parameters.

The order of quantifiers is part of the proposed result: for every bound, one parameter must satisfy both inequalities. Two unrelated infinite subsequences would not prove the combined criterion.

For a prime $`r`$ and an integer $`e\ge1`$, let $`h_{r,e}(p)=\#\{i\in I_p:r^e\mid i!-1\}`$. The exponent of $`r`$ in the shared part is at least $`e`$ exactly when $`h_{r,e}(p)>1`$. Removing the exponent already present in $`F_p`$ therefore gives
``` math
v_r(\widetilde C_p)
 =\#\{e\ge1:h_{r,e+v_r(F_p)}(p)>1\}.
```
When $`r\nmid F_p`$, this counts the positive exponents for which two or more denominators are divisible by $`r^e`$. The spacing bound $`h_{r,e}(p)(e+1)\le2p+e-2`$ follows from the gap-product argument: if $`i<j`$ are two such indices, then $`j<r`$ and $`0<r^e\le j!/i!-1<r^{j-i}`$, so $`j-i\ge e+1`$. All indices lie between $`2`$ and $`2p-1`$, giving the bound; the zero-hit case is immediate. To estimate $`\log\widetilde C_p`$, these exponent counts must be multiplied by $`\log r`$ and summed over primes. A count ignoring the sizes of the primes does not give <a href="#long68:eq:weighted-target" data-reference-type="eqref" data-reference="long68:eq:weighted-target">[long68:eq:weighted-target]</a>. For a prime $`q`$, Wilson reflection of an odd index $`n<q`$ contributes a repeated divisor only when the reflected index is distinct and in the same block, with both indices at least $`2`$. The endpoint $`n=q-2`$ reflects to $`1`$ and contributes no such pair, as shown in §<a href="#long68:sec:prime-powers" data-reference-type="ref" data-reference="long68:sec:prime-powers">1</a>.

Even for two admissible indices, the reflection identity is only modulo $`q`$ \[stewart2004, (4), p. 462\]. For example, exact multiplication gives
``` math
609!\equiv1\pmod{971^2},\qquad
 361!\equiv736019=1+758\cdot971\pmod{971^2},
```
where $`361=971-609-1`$. Both indices lie in $`I_{306}`$, but their factorial denominators have $`971`$-exponents at least $`2`$ and exactly $`1`$, respectively. Thus reflection supplies two hits modulo $`q`$, not necessarily modulo $`q^e`$ for $`e>1`$. Each level in the valuation sum requires its own congruence; neither distinctness nor a higher exponent may be inferred from the prime-level identity alone. Theorem 12 of Garaev, Luca and Shparlinski \[garaev-luca-shparlinski, arXiv v1, Thm. 12, p. 16\] is a multiplicity bound and supplies no lower bound for the distance to the next integer in <a href="#long68:eq:global-scale" data-reference-type="eqref" data-reference="long68:eq:global-scale">[long68:eq:global-scale]</a>.

For the first inequality alone, a joint mean bound
``` math
\frac1{|I_X|}\sum_{p\in I_X}
 \left(\log\widetilde C_p-\log\frac{\rho_p}{R_p}\right)
 <(1-\varepsilon)X\log X
```
on nonempty sets $`I_X\subseteq[X,2X]\cap\mathbb N`$, with $`R_p>1`$, a fixed $`0<\varepsilon<1`$, and arbitrarily large $`X`$, would suffice: at least one summand is at most the average, while the required upper bound is $`\log(K_p/((2p+1)F_p))=p\log p+O(p)`$, uniformly for $`p\in[X,2X]`$. Two separate estimates on unrelated sets of indices would not give this joint comparison.

<a id="what-two-gap-product-tests-do-not-show."></a>

#### What two gap-product tests do not show.

For integers $`h\ge1`$ and $`x\ge0`$, let $`F_h(X)=\prod_{j=1}^h(X+j)`$. Suppose $`x+h<q`$ for a prime $`q`$. If $`x!`$ and $`(x+h)!`$ both equal $`1`$ modulo $`q`$ and the harmonic sums through these indices are equal modulo $`q`$, then $`F_h(x)=1`$ and $`F'_h(x)=F_h(x)\sum_{j=1}^h(x+j)^{-1}=0`$ in that field. An exact calculation gives
``` math
\gcd(F_{12}-1,F'_{12})
 =(X-4626)(X-7848)\quad\hbox{in }\mathbb F_{12487}[X].
```
Thus a uniform bound of one repeated root is false. But $`4626!\equiv442`$ and $`7848!\equiv6300`$ modulo $`12487`$, so neither root also satisfies $`x!\equiv1`$. Counting repeated roots of $`F_h-1`$ therefore does not count the indices required by the factorial problem. These are finite modular calculations, not a bound on the number of indices satisfying both congruences.

Stewart’s gap-product estimate \[stewart2004, Lemma 2, (21)–(24)\] requires the two products to be unequal. He supplies that step separately: in the proof of his bound (14), a prime-distribution argument separates the products when the common divisor is large; the smaller-divisor case is immediate \[stewart2004, p. 467, proof of Lemma 2\].

The non-power theorem gives a different argument when the gaps are adjacent. For integers $`2\le i<j<k`$, equality $`j!/i!=k!/j!`$ would make $`k!/i!`$ a square, contrary to that theorem \[erdos-selfridge1975, Theorem 1\]. Selecting two short gaps with nearly equal lengths need not preserve adjacency, so this observation alone cannot replace Stewart’s nonvanishing argument. The wider equal-product problem has a separate history \[macleod-barrodale1970\]; the doubled-length theorem discussed by Nguyen Xuan Tho \[nguyen-tho2026, Theorem 1\] is another special case, not arbitrary near-equal-length nonvanishing. No stronger lcm exponent is inferred from these local observations.

<a id="prime-powers-already-seen-at-earlier-indices."></a>

#### Prime powers already seen at earlier indices.

Recall that $`\Delta_n=P^\Delta_n/Q^\Delta_n`$ is the positive gap in lowest terms. Define
``` math
\mathcal A_n=\prod_{\substack{r\ \mathrm{prime},\ r\mid n!-1\\
     r\mid k!-1\ \text{for some }2\le k<n\\
     v_r(Q^\Delta_n)<v_r(n!-1)}}r^{\,v_r(n!-1)} .
```
Thus the product includes the full power of a prime in $`n!-1`$ when that prime has appeared before but has smaller exponent in $`Q^\Delta_n`$. The recurrence for the gaps is
``` math
\Delta_{n+1}=n\Delta_n-b_n-\frac1{n!-1}.
```
For a prime $`r`$ in the product, put $`e=v_r(n!-1)`$. The reduced denominator of $`n\Delta_n-b_n`$ has $`r`$-exponent at most $`v_r(Q^\Delta_n)<e`$, whereas $`1/(n!-1)`$ has exponent $`e`$. Clearing denominators leaves exactly one numerator term nonzero modulo $`r`$, so the reduced denominator of $`\Delta_{n+1}`$ has exponent exactly $`e`$. Hence $`\mathcal A_n\mid Q^\Delta_{n+1}`$ and, when $`\mathcal A_n>1`$, $`P^\Delta_{n+1}\not\equiv0\pmod{\mathcal A_n}`$. The earlier occurrence of $`r`$ is not used in this divisibility argument; it restricts the product to the primes proposed for this approach. A sufficient quantitative estimate, at arbitrarily large indices $`n`$, with $`m=n+1`$ and $`d=\mathcal A_n>1`$, is
``` math
\begin{equation}
\label{long68:eq:amplification-target}
 \bigl((m+2)m!-2\bigr)Q^\Delta_m
 \le m^2(m!-1)\,(P^\Delta_m\bmod d).
\end{equation}
```
It implies the upper alternative of <a href="#long68:eq:finite-escape" data-reference-type="eqref" data-reference="long68:eq:finite-escape">[long68:eq:finite-escape]</a>. A nonzero least representative can equal one even when the modulus is large. Neither a lower bound for $`\log\mathcal A_n`$ nor infinitely many increases in a previously occurring prime’s exponent therefore proves <a href="#long68:eq:amplification-target" data-reference-type="eqref" data-reference="long68:eq:amplification-target">[long68:eq:amplification-target]</a>: the least representative itself must satisfy the displayed inequality. Repeated prime squares can first occur before the Wilson index $`r-2`$: for example, $`971`$ divides $`361!-1`$ and its square first divides $`609!-1`$, with $`609<971-2`$. Such an example rules out confinement to that last index but supplies no unbounded family satisfying the required inequality.

<a id="the-upper-alternative-in-the-finite-test."></a>

#### The upper alternative in the finite test.

It would suffice for <a href="#long68:eq:finite-escape" data-reference-type="eqref" data-reference="long68:eq:finite-escape">[long68:eq:finite-escape]</a> to hold at arbitrarily large indices; an unbounded set of prime indices would suffice as well. The upper alternative is exactly $`\bigl((m+2)m!-2\bigr)Q^\Delta_m\le m^2(m!-1)P^\Delta_m`$. Replacing $`P^\Delta_m`$ by its least nonnegative residue modulo a specified divisor of $`Q^\Delta_m`$ gives a stronger sufficient test. No bound forcing this inequality at arbitrarily large indices is established here. The full recurrence for the actual scaled partial sums, including its initial value, is fixed; a rational example for a weakened recurrence does not satisfy that full specification (§<a href="#long68:sec:ext-nogo" data-reference-type="ref" data-reference="long68:sec:ext-nogo">9.7</a>). Nor does a zero canonical digit assert membership in the specified real interval.

<a id="conditions-at-twice-a-prime."></a>

#### Conditions at twice a prime.

For an odd prime $`p`$, the carry range and $`Z_{2p}=2pZ_{2p-1}+1-b_{2p}`$ give
``` math
\begin{equation}
\label{long68:eq:doubled-prime}
 p^2\mid Z_{2p}
 \quad\Longleftrightarrow\quad
 \begin{cases}
 b_{2p}=1\ \hbox{and}\ p\mid Z_{2p-1},\ \hbox{or}\\
 b_{2p}=1+p\ \hbox{and}\ p\mid2Z_{2p-1}-1 .
 \end{cases}
\end{equation}
```

Reduction modulo $`p`$ forces $`b_{2p}\equiv1\pmod p`$, and the two displayed values are the only possibilities in $`[-1,2p-1]`$; division by $`p`$ gives the predecessor conditions. For rational $`S=a/q`$ and $`p>q`$, the tail estimate gives $`Z_{2p}=(2p)!\,S`$, which is divisible by $`p^2`$. A proof through $`p^2\nmid Z_{2p}`$ must therefore exclude both displayed alternatives at the same prime, for arbitrarily large primes. That is a requirement of this particular test, not of every irrationality argument. Rationality also forces $`b_{2p}=1`$ and $`Z_{2p-1}=(2p-1)!a/q`$, with $`p\mid Z_{2p-1}`$: here $`q\mid(p-1)!`$, and the remaining factorial factors include $`p`$. Thus either $`b_{2p}\ne1`$ at arbitrarily large odd primes or $`p\nmid Z_{2p-1}`$ at arbitrarily large odd primes would already contradict rationality. The first is a special case of Theorem <a href="#long68:res:carry-equivalence" data-reference-type="ref" data-reference="long68:res:carry-equivalence">8</a>; the second uses the same factorial-clearing argument. Neither unbounded occurrence is proved here.

<a id="the-cofactor-form-of-the-progression-construction."></a>

#### The cofactor form of the progression construction.

For a positive starting parameter, a Vandermonde matrix gives another formula for the progression vectors of §<a href="#long68:sec:channels" data-reference-type="ref" data-reference="long68:sec:channels">5</a>; it does not resolve the remaining nonintegrality problem. For integers $`n,t\ge0`$, put $`s_n=((n+2)!)^2`$ and $`i_j=(t+j)s_n`$ for $`0\le j\le n+1`$. This step size matches the recorded construction; the determinant argument only needs a positive step divisible by every $`d=2,\ldots,n+2`$. Here the factorial-weight formula is also allowed at index $`0`$; the case $`t=0`$ will show why a lower support condition is necessary. Form the integer matrix $`A`$ with moment row $`(i_j!)_j`$ and weighted-sum rows $`(W_{d,i_j})_j`$ for $`2\le d\le n+2`$.

To see that $`\det A\ne0`$, divide column $`j`$ by $`i_j!`$. Since $`d\mid s_n`$, the $`d`$th weighted-sum row becomes $`((d!)^{-(t+j)s_n/d})_j`$. Removing the nonzero factor $`(d!)^{-t s_n/d}`$ from that row leaves a Vandermonde matrix with nodes
``` math
1,\ (2!)^{-s_n/2},\ \ldots,\ ((n+2)!)^{-s_n/(n+2)}.
```
These nodes are distinct: $`(d!)^{1/d}`$ is strictly increasing, since $`d!<(d+1)^d`$. The Vandermonde determinant is the product of their pairwise differences \[nist-vandermonde, (1.3.13)\], and is therefore nonzero. None of the row or column factors removed is zero, so the original determinant is nonzero too.

Let $`c`$ be the cofactor vector of the moment row, and let $`N_d`$ be the determinant obtained by replacing that row with $`(W_{d,i_j})_j`$. Cofactor expansion gives $`M(c)=\det A\ne0`$ and $`V_{d}(c)=N_d`$. For $`2\le d\le n+2`$ the replacement duplicates a row, so $`V_{d}(c)=0`$. By <a href="#long68:eq:channel-congruence" data-reference-type="eqref" data-reference="long68:eq:channel-congruence">[long68:eq:channel-congruence]</a> each $`(V_{d}(c)-M(c))/(d!-1)`$ is an integer and vanishes for $`d>\max_ji_j`$, so
``` math
\mathcal R_{n,t}:=\sum_{d>n+2}\frac{N_d}{d!-1},\qquad
 \mathcal R_{n,t}-\det(A)\,S\in\mathbb{Z}.
```
A family with $`\min_ji_j=t\,s_n\to\infty`$ and $`\mathcal R_{n,t}\notin\mathbb{Z}`$ would prove irrationality. Indeed, for a fixed denominator $`q`$, every entry of the moment row is divisible by $`q`$ once the least support index is at least $`q`$, so $`q\mid\det A`$. If $`S=a/q`$, the integer-difference identity would then force $`\mathcal R_{n,t}\in\mathbb{Z}`$. Conversely, if $`S`$ is irrational, that same identity and $`\det A\ne0`$ make every $`\mathcal R_{n,t}`$ irrational. Taking, for example, $`n=0`$ and $`t\to\infty`$ gives the required family. Thus nonintegrality along such a family is equivalent to the original irrationality question, not a weaker conjecture obtained from the construction.

Merely making $`(n,t)`$ unbounded does not ensure that the support tends to infinity: when $`t=0`$, the least support index is always zero. The coefficient at $`i_0`$ really is nonzero: its cofactor uses columns $`1,\ldots,n+1`$, and after nonzero row and column scalings it is a Vandermonde determinant on the weighted-sum nodes. The eventual identity $`N_d=\det A`$ determines the tail, but not the finite intermediate sum, whose terms may have either sign. The construction solves the linear equations. What is still needed here is a proof that the particular sum is nonintegral, whether by a gap estimate or another arithmetic argument.

For $`t\ge1`$, primitive normalization identifies this vector exactly. Take $`D=n+2`$, $`\ell=s_n`$ and $`r=t s_n`$ in the progression construction of §<a href="#long68:sec:channels" data-reference-type="ref" data-reference="long68:sec:channels">5</a>, and put $`N=r+(D-1)\ell`$. For any coefficient vector supported on these $`D`$ indices, the equations $`V_2=\cdots=V_D=0`$ say that the polynomial
``` math
\sum_{j=0}^{D-1}c_{i_j}i_j!X^j
```
vanishes at the $`D-1`$ distinct points $`\alpha_d^{-1}=(d!)^{-\ell/d}`$, $`2\le d\le D`$. Its degree is at most $`D-1`$, so it is a scalar multiple of $`\prod_{d=2}^D(\alpha_dX-1)`$. Thus the rational solution space is one-dimensional. The progression vector has coefficient $`1`$ at $`N`$, so every integer solution is its integer multiple, with multiplier $`c_N`$. In particular, the cofactor gcd is $`|c_N|`$, and the primitive cofactor vector is the progression vector up to sign. With the sign chosen so that its moment is positive, that moment equals
``` math
N!\prod_{d=2}^D\bigl(1-(d!)^{-\ell/d}\bigr).
```
For example, $`n=0,t=1`$ gives support $`\{4,8\}`$, cofactor vector $`2520e_4-6e_8`$, and positive-moment primitive vector $`-420e_4+e_8`$.

The factorial divisibility proved for the progression moment therefore also applies to this primitive vector. Normalization still leaves the nonintegrality condition equivalent to irrationality along families whose least support index tends to infinity: the moment is nonzero, every factorial below that index divides it, and <a href="#long68:eq:channel-congruence" data-reference-type="eqref" data-reference="long68:eq:channel-congruence">[long68:eq:channel-congruence]</a> gives the integer-difference identity. This identification does not estimate the distance from an integer. The case $`t=0`$ is excluded from the identification with the stated progression construction, whose indices are at least $`2`$.

<a id="criteria-from-the-literature-that-do-not-apply."></a>

#### Criteria from the literature that do not apply.

Duverney’s Theorem 3.1 assumes, among other conditions, quadratic growth $`cu_n^2\le u_{n+1}\le c'u_n^2`$ for positive constants $`c,c'`$. For $`u_n=n!-1`$, however, $`u_{n+1}/u_n^2\to0`$. His Corollary 3.2 assumes convergence of the signed series $`\sum_n(u_{n+1}/u_n^2-1)`$ in (3.6). Here its terms tend to $`-1`$, so that hypothesis fails as well \[duverney, pp. 275, 285–287\]. For a single denominator sequence the rapid-growth criterion goes back to Erdős \[erdos1975, Theorem 1, p. 1\]; Barreto, Kang, Kim, Kovač and Zhang treat products of consecutive denominators and weighted extensions \[barreto-et-al, Thms. 2–3 and Rem. 4\]. For $`a_n=n!-1`$, $`\log(n!-1)=O(n\log n)`$ makes $`(n!-1)^{1/\psi^n}\to1`$ for every fixed $`\psi>1`$, so neither Erdős’s hypothesis $`\limsup_na_n^{1/2^n}=\infty`$ nor the growth hypotheses of their Theorems 2 and 3 hold. These criteria do not decide $`S`$; the useful content is the target these papers identify: a subsequence with clearing integers small enough for the corresponding remainders, or enough exact cancellation in those integers. Theorem <a href="#long68:res:lcm-growth" data-reference-type="ref" data-reference="long68:res:lcm-growth">7</a> measures the cost of clearing all summands before reduction; it does not bound cancellation in their sum. Theorem <a href="#long68:res:prime-pole" data-reference-type="ref" data-reference="long68:res:prime-pole">2</a> tests whether a maximal prime power survives reduction. Neither supplies the upper bound for a clearing integer, relative to its remainder, that these arguments need.

No irrationality conclusion is obtained here. The finite conclusion is that every rational representation $`S=a/q`$, $`q>0`$, must satisfy both $`q\nmid299999!`$ and $`q\ge2^{39990}>10^{12038}`$. The criteria above require a condition at arbitrarily large indices. Extending either finite computation alone does not establish it.

<a id="sources-and-evidence"></a>

# Sources and evidence

The links below identify formal statements and proofs in the source records supplied with this revision. They retain their original commits and paths; they are not a claim that all linked modules were compiled together at `92b88dc1bbe0`.

The attached declaration index is for public snapshot `6b78209ab63a8c643281115f8628a3be79ff7ec7` and the separate release `52f29ad173b04e3bac941b3663f2b9aebe5de0bb`. It distinguishes recorded checked declarations from source outside the recorded build and from release-only declarations. In particular, `PaperCompleteExisting` is present but outside the recorded checked build; the earlier references to its absence are superseded by this source packet. The same outside-build qualification applies to the candidate finite-size certificate.

The build receipt refers to a successful Lean build at an earlier commit; the Lean build step at the supplied public pin was skipped. No Lean build or axiom audit was run for this prose revision. A source declaration, a recorded proof-checking result, and a numerical computation are different kinds of evidence. Descriptions below of checked statements refer to the supplied records, not to a new compilation. Theorem <a href="#long68:res:lcm-growth" data-reference-type="ref" data-reference="long68:res:lcm-growth">7</a> and Corollary <a href="#long68:res:radius-constant" data-reference-type="ref" data-reference="long68:res:radius-constant">18</a> are ordinary proofs given in full above, with corresponding Lean source statements [the liminf bound for the common denominator](https://github.com/wcook04/plectis-erdos/blob/0b500c7cf8e8bb7ae343484378df02f277fb8194/lean/ErdosProblems/Erdos68/PaperCompleteLiminf.lean#L42) and [the asymptotic lower bound for the support parameter](https://github.com/wcook04/plectis-erdos/blob/0b500c7cf8e8bb7ae343484378df02f277fb8194/lean/ErdosProblems/Erdos68/PaperCompleteLiminf.lean#L54). The finite-block inequality is the separate Lean source [the inequality for a terminal block](https://github.com/wcook04/plectis-erdos/blob/d788dd4b8c59f2246000f2ed98fffb8a5e8ac72e/lean/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L524-L529). The two prefix cancellations, the index-$`52`$ example and the continued-fraction enclosure are finite integer calculations with the procedures displayed above. The carry census through $`300000`$ is a separate exact-interval computation with the receipt named in §<a href="#long68:sec:finite" data-reference-type="ref" data-reference="long68:sec:finite">6</a>.

| Statement | Formal counterpart |
|:---|:---|
| Statement | Formal counterpart (continued) |
| Theorem <a href="#long68:res:prime-pole" data-reference-type="ref" data-reference="long68:res:prime-pole">2</a> | [maximal-power survival](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimePoleCriterion.lean#L223), with the residue formula at [line 129](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimePoleCriterion.lean#L129) and the denominator form at [line 41](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimePoleDenominator.lean#L41) |
| Proposition <a href="#long68:res:wilson-cofinality" data-reference-type="ref" data-reference="long68:res:wilson-cofinality">3</a> | [first prime occurrences at arbitrarily large indices](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L3097); reflection at [line 3139](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L3139) |
| Theorem <a href="#long68:res:carry-equivalence" data-reference-type="ref" data-reference="long68:res:carry-equivalence">8</a> | [failures of divisibility for the next integer](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialGapPlateauCore.lean#L986); denominator exclusions at [line 812](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialGapPlateauCore.lean#L812) and [line 836](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialGapPlateauCore.lean#L836) |
| Proposition <a href="#long68:res:companion-orbit" data-reference-type="ref" data-reference="long68:res:companion-orbit">9</a> | [factorial residues and rationality](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/CompanionOrbitRationality.lean#L438) |
| Proposition <a href="#long68:res:lower-escape" data-reference-type="ref" data-reference="long68:res:lower-escape">10</a> | [the equivalent fractional-part inequality](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ShrinkingTargetNormalForm.lean#L82); finite window at [line 122](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ShrinkingTargetNormalForm.lean#L122), irrationality implication at [line 145](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ShrinkingTargetNormalForm.lean#L145), classification <a href="#long68:eq:escape-classification" data-reference-type="eqref" data-reference="long68:eq:escape-classification">[long68:eq:escape-classification]</a> at [line 39](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ShrinkingTargetNormalForm.lean#L39), radius at [line 158](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ShrinkingTargetNormalForm.lean#L158) |
| Theorem <a href="#long68:res:shift-family" data-reference-type="ref" data-reference="long68:res:shift-family">11</a> | [the criterion for the shifted series](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialShiftFamilyOrbit.lean#L139); escape form at [line 156](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialShiftFamilyOrbit.lean#L156), member $`t=-1`$ at [line 175](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialShiftFamilyOrbit.lean#L175), and the irrationality of $`e`$ at [line 211](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialShiftFamilyOrbit.lean#L211) |
| Theorem <a href="#long68:res:global-residue" data-reference-type="ref" data-reference="long68:res:global-residue">12</a> | [the prime-parameter specialization](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L6164); the natural-parameter wrapper is linked after the proof and is outside the recorded checked build. Coprimality <a href="#long68:eq:gap-normalisation" data-reference-type="eqref" data-reference="long68:eq:gap-normalisation">[long68:eq:gap-normalisation]</a> is at [line 4209](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L4209) |
| Equation <a href="#long68:eq:factor-split" data-reference-type="eqref" data-reference="long68:eq:factor-split">[long68:eq:factor-split]</a> | [the two simultaneous inequalities](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L4766), floor identity at [line 4701](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L4701), irrationality implication at [line 1574](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L1574) |
| Removal of a fixed denominator factor | [a fixed factor eventually divides the factorial](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L2677) |
| Weight identities used in Theorem <a href="#long68:res:normalform" data-reference-type="ref" data-reference="long68:res:normalform">13</a> and <a href="#long68:eq:channel-congruence" data-reference-type="eqref" data-reference="long68:eq:channel-congruence">[long68:eq:channel-congruence]</a> | [integrality of the weights](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L25), [the denominator-times-weight identity](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L43) |
| Theorem <a href="#long68:res:channel-radius" data-reference-type="ref" data-reference="long68:res:channel-radius">17</a> | [detail note 1](#paper-table-note-6270dc86792d8675) |
| Changing one weighted sum $`V_p`$ | [adjustment at sufficiently large indices](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimeUnitTranslator.lean#L1657), residual identity at [line 1559](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimeUnitTranslator.lean#L1559) |
| Equation <a href="#long68:eq:doubled-prime" data-reference-type="eqref" data-reference="long68:eq:doubled-prime">[long68:eq:doubled-prime]</a> | [doubled-prime criterion](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialZeroPlateauSupplement.lean#L257) |
| Canonical factorial digits | [termination equivalence](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/CanonicalFactorialTermination.lean#L78) |
| Amplification modulus | [divisibility](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L5557), nonvanishing at [line 5572](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L5572) |

<a id="paper-table-note-6270dc86792d8675"></a> **Detail note 1.** [finite radius bound](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L1084); sequence form at [line 1103](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L1103), little-$`o`$ form at [line 905](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L905), limitation of the numerical inequalities proved here (the attached release also contains `sharp_radius_satisfies_square_log_constraint`; this is separate from the historical link above)


The two weight identities in the table are ingredients, not the complete congruence statement. In the supplied public snapshot, `ChannelIntegralCongruence.lean` contains `channelNumerator_mod_factorialMoment` (line 76) and `exists_channelCorrection` (line 127). The former states $`(d!-1)\mid M(c)-V_d(c)`$; negating the integer quotient gives the sign convention of Theorem <a href="#long68:res:normalform" data-reference-type="ref" data-reference="long68:res:normalform">13</a>. These are source correspondences, not a fresh build or axiom audit.

Attribution. Wilson’s theorem and the Wilson reflection identity are classical, the latter recorded by Stewart \[stewart2004, p. 462, (4)\]. The factorial-digit termination criterion goes back to Cantor \[cantor1869\]; Koepf and Schmersau prove its irrationality direction for digits that are not eventually maximal \[koepf-schmersau, Example 3.2, p. 121\], and Galambos treats rationality criteria for Cantor series \[galambos1976, Ch. II, §2.1\]. Here the identity $`C=S-e+2`$ gives the eventual digit value $`m-2`$ and extends to the shifted family. The comparison with Hančl and Tijdeman \[hancl-tijdeman, Lemma 2.1 and the following remark, p. 385\] concerns factorial scaling: their lemma makes a scaled tail integral, whereas the proof in §<a href="#long68:sec:carry" data-reference-type="ref" data-reference="long68:sec:carry">3</a> identifies the next integer above a generally nonintegral scaled prefix. The multiplicity bound is Garaev, Luca and Shparlinski’s \[garaev-luca-shparlinski\], and the lcm deduction from it is not theirs. The divisibility in Lemma <a href="#long68:res:gap-gcd" data-reference-type="ref" data-reference="long68:res:gap-gcd">5</a> is the case $`P=-1`$ of the relation used in the proof of Lemma 5 of Luca and Shparlinski \[luca-shparlinski\] and at display (2.5) of Lai \[lai\]. The nonvanishing cutoff for polynomial shifts is Lemma 3 of \[luca-shparlinski\], restated with the bound $`n!+P(n)>1`$ in \[lai, Lemma 2.1\]. The survival criterion is a specialisation of Louwsma and Martino’s valuation formula \[louwsma-martino, Lemma 4.1, p. 10\]. The single-denominator growth criterion is Erdős’s \[erdos1975, Theorem 1, p. 1\], and the continued-fraction identities are those of \[nist-dlmf, §1.12(ii)\]. The deductions from Wilson’s theorem, the conditional finite support bound and Theorem <a href="#long68:res:lcm-growth" data-reference-type="ref" data-reference="long68:res:lcm-growth">7</a> are proved above. No further priority claim is inferred from this comparison.

<a id="long68:app:sources"></a>

# Guide to the formal sources

The following links identify the statements used above and related lemmas. Each preserves the original file, declaration, and line reference. The evidence qualifications in the preceding section apply throughout; in particular, source presence alone does not establish inclusion in a checked build.

- [the factorial-scaled floor of a rational number](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/CanonicalFactorialDigits.lean#L47)

- [eventual zero digits of a rational number](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/CanonicalFactorialDigits.lean#L81)

- [a digit as the floor of a scaled fractional part](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/CanonicalFactorialDigits.lean#L124)

- [the digit is smaller than its radix](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/CanonicalFactorialDigits.lean#L153)

- [the recurrence for fractional parts](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/CanonicalFactorialDigits.lean#L162)

- [the finite factorial expansion with its remainder](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/CanonicalFactorialDigits.lean#L196)

- [a zero remainder forces all later digits to vanish](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/CanonicalFactorialDigits.lean#L269)

- [eventual zero digits force a zero remainder](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/CanonicalFactorialTermination.lean#L38)

- [a zero factorial remainder implies rationality](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/CanonicalFactorialTermination.lean#L54)

- [the scaled partial sum and limit select the same integer](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialGapPlateauCore.lean#L82)

- [non-unit carries at arbitrarily large indices imply irrationality](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialGapPlateauCore.lean#L945)

- [every rational denominator is at least sixty-seven](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialZeroPlateauCertificates.lean#L136)

- [the exact interval condition for the lower endpoint](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L6099)

- [a prime-product bound gives a late first occurrence](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L3047)

- [a reflected prime survives normalization under the block and upper-half hypotheses](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L3231)

- [two distinct in-block indices under the same reflection hypotheses](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L3252)

- [the selected prime powers divide the remaining quotient](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L1419)

- [the factors one and a selected prime in the chosen block](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/PrimeZeroBranch.lean#L1524)

- [the exact integer interval for two consecutive unit carries](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L148)

- [the two denominator-reduction factors telescope](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L215)

- [the denominator after two steps](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L243)

- [the offset equals the later numerator times the reduction factors](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/AdjacentUnitCarryWindow.lean#L337)

- [factorisation when the floor in the weights is constant](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ChannelBreakpointRigidity.lean#L71)

- [vanishing of the moment on one such interval](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ChannelBreakpointRigidity.lean#L91)

- [factorisation on the interval from d to twice d](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ChannelBreakpointRigidity.lean#L101)

- [a nonzero moment forces an index at least twice d](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ChannelBreakpointRigidity.lean#L130)

- [a cubic lower bound for the support parameter](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L868)

- [exclusion of the stated eventual cubic upper bound](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/ChannelIntegralCongruence.lean#L885)

- [no change unless the divisor divides the index](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L65)

- [the strict rational bounds for the example remainder](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialChannelCertificate.lean#L156)

- [the consecutive-term quadratic ratio tends to zero](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialAnalyticBoundary.lean#L52)

- [divergence of the absolute quadratic-ratio errors](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialAnalyticBoundary.lean#L84)

- [the iterated-root growth expression tends to one](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/FactorialAnalyticBoundary.lean#L131)

- [updating the pairwise gcd lcm after insertion](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L556)

- [updating the lcm with a fixed prescribed factor](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L586)

- [exact removal of the common part with the base](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L698)

- [the valuation after removal of the base](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L739)

- [the shared part times the lcm divides the product](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L800)

- [fixed denominator indices are eventually absorbed by the factorial](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L2707)

- [the shared part is bounded by the product divided by the lcm](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L3327)

- [the surviving valuation after removal of the factorial base](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L3394)

- [a shared prime power is bounded by the gap product](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L3443)

- [two indices sharing a prime power are farther apart than its exponent](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L3472)

- [the resulting bound on the number of such indices](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L3602)

- [the total relevant exponent is less than the prime](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L3790)

- [the total relevant exponent is less than the block diameter](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L3848)

- [a surviving prime has square greater than the parameter minus one](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L3982)

- [the projection moduli have the required lcm](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L4387)

- [the two-factor bound is no larger than the full residue bound](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L4854)

- [the valuation counts exponents occurring at two indices](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L5213)

- [a finite exponent range suffices for that count](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L5277)

- [the exact repeated-power criterion above the factorial base](https://github.com/wcook04/plectis-erdos/blob/92b88dc1bbe099aa73bcc900c3c405e9ba5c2334/ErdosProblems/Erdos68/EndpointWeightedPrivateSupport.lean#L5389)

<a id="long68:sec:extended-record"></a>

# Further deductions and limitations

This appendix supplies details used by the earlier sections: factorial digits and their remainders, exact gcd and lcm identities, and additional finite examples. It also records weaker deductions and explains why several proposed irrationality arguments do not establish their needed hypotheses.

<a id="long68:sec:ext-digits"></a>

## Factorial digits and their remainders

For a real number $`x`$, write $`\theta_0=\{x\}`$ and, for $`m\ge1`$,
``` math
a_m=\lfloor m\,\theta_{m-1}\rfloor,\qquad \theta_m=m\,\theta_{m-1}-a_m ,
```
so that $`\theta_m=\{m!\,x\}`$ for $`m\ge1`$. The kernel checks the floor formula, the digit bounds $`0\le a_m<m`$, the recurrence $`\theta_{m+1}=(m+1)\theta_m-a_{m+1}`$, the finite telescoping expansion
``` math
x=\lfloor x\rfloor+\sum_{m=2}^{N}\frac{a_m}{m!}+\frac{\theta_N}{N!},
```
and the rule that a zero remainder at one index forces every later digit to vanish. The rational direction is also checked: if $`a\in\mathbb Z`$, $`q\in\mathbb N`$, and $`0<q\le n`$, then $`\lfloor n!a/q\rfloor=(n!/q)a`$ and the canonical digit at radix $`n+1`$ vanishes, so every rational input has an eventually zero expansion. The converse holds for every real input, and gives Cantor’s termination criterion \[cantor1869\]
``` math
x\in\mathbb{Q}\quad\Longleftrightarrow\quad a_m(x)=0\ \hbox{for all large }m .
```
If all digits after index $`N\ge1`$ vanish, the recurrence gives $`\theta_{N+k}\ge(k+1)\theta_N`$; since every remainder is below one, $`\theta_N=0`$ and $`x=\lfloor N!x\rfloor/N!`$.

For $`x=S`$, a zero canonical digit means $`m\theta_{m-1}<1`$. The stronger condition $`m\theta_{m-1}<E_m`$, where $`E_m=m!(S-H_m)`$, is the lower-interval event used in §<a href="#long68:sec:carry" data-reference-type="ref" data-reference="long68:sec:carry">3</a>. The reported interval data contain zero digits at $`m=5`$ and $`m=23`$, but no occurrence of that stronger condition through $`m=100000`$.

There is also a useful identity for an abstract rational sequence $`F_m`$ and integer sequence $`k_m`$. Suppose $`F_m=mF_{m-1}+1+\varepsilon_m-k_m`$, and define
``` math
\delta_m=\lceil F_m\rceil-F_m,\qquad
 q_m=m\lceil F_{m-1}\rceil+1-k_m-\lceil F_m\rceil.
```
Then $`0\le\delta_m<1`$, and the exact identities are
``` math
q_m=\lfloor m\delta_{m-1}-\varepsilon_m\rfloor,\qquad
 \delta_m=m\delta_{m-1}-\varepsilon_m-q_m.
```
The attached Lean source proves these identities under the displayed recurrence. They do apply to the actual partial sums: take $`F_m=m!H_m`$, $`k_m=0`$ and $`\varepsilon_m=1/(m!-1)`$ for $`m\ge3`$. The recurrence then follows from $`H_m=H_{m-1}+1/(m!-1)`$, starting with $`F_2=2`$. The ceiling code $`q_m`$ need not equal the carry $`b_m`$, because $`Z_m`$ is the least integer strictly above $`F_m`$, not always its ceiling. Precisely, $`Z_m=\lceil F_m\rceil+\mathbf1_{\{F_m\in\mathbb{Z}\}}`$, so
``` math
b_m=q_m+m\mathbf1_{\{F_{m-1}\in\mathbb{Z}\}}
          -\mathbf1_{\{F_m\in\mathbb{Z}\}}.
```
For example, $`F_2=2`$ and $`F_3=36/5`$ give $`q_3=-1`$ but $`b_3=2`$. The codes agree whenever both scaled prefixes are nonintegral. Once $`F_2=2`$ and $`\varepsilon_m=1/(m!-1)`$ are fixed, the recurrence with $`k_m=0`$ determines every $`F_m`$ uniquely by induction. Thus matching the recurrence and its initial value is stronger than satisfying selected congruences or carry bounds. This specialization is an ordinary deduction from the partial-sum recurrence, not a new Lean check. It does not show that the rational gaps admit a finite-state description or establish the unbounded non-unit carries needed for irrationality.

<a id="long68:sec:ext-literature"></a>

## How the classical criteria apply here

Let $`s_n<a`$ be partial sums tending to $`a`$. Koepf and Schmersau show that $`\lfloor ns_n\rfloor=\lfloor na\rfloor`$ for all sufficiently large $`n`$ forces $`a`$ to be irrational \[koepf-schmersau, Thm. 1.1, p. 117\]. The strict inequality matters: if $`a=A/B`$ were rational, then every sufficiently large multiple $`n`$ of $`B`$ would give $`\lfloor ns_n\rfloor<na=\lfloor na\rfloor`$. Their rational-term version uses a positive integer multiplier $`p_n`$ and obtains the floor equality from $`np_ns_n\in\mathbb N_0`$ and the strict tail bound $`a-s_n<1/(np_n)`$ \[koepf-schmersau, (2.1) and (2.3), p. 118; Thms. 2.2–2.3, pp. 119–120\]. Indeed, integrality makes $`ns_n`$ a multiple of $`1/p_n`$, so its gap to the least strictly larger integer is at least $`1/p_n`$; the increase $`n(a-s_n)<1/p_n`$ cannot cross that integer. For the choice they record after (2.1), the least common multiple of the reduced summand denominators, here $`p_n=\operatorname{lcm}\{k!-1:2\le k\le n\}`$, the last two denominators already obstruct the tail bound. As proved in §<a href="#long68:sec:lcm" data-reference-type="ref" data-reference="long68:sec:lcm">2</a>, they are coprime for $`n\ge3`$, so
``` math
p_n\ge(n!-1)\bigl((n-1)!-1\bigr).
```
For $`n\ge4`$ this gives $`np_n>(n+1)!-1`$. Hence the first omitted summand $`1/((n+1)!-1)`$ already exceeds $`1/(np_n)`$, and this $`p_n`$ cannot satisfy their tail hypothesis. This rules out the displayed choice of $`p_n`$, not the criterion itself. In fact, the least positive integer $`p_n`$ for which $`np_nH_n`$ is integral is exactly
``` math
p_n=\operatorname{den}(nH_n)
     =\frac{\operatorname{den}(H_n)}{\gcd(n,\operatorname{den}(H_n))}.
```
Indeed, writing $`H_n`$ in lowest terms shows that its denominator must divide $`np_n`$. With this least choice the required inequality is
``` math
0<S-H_n<\frac{\gcd(n,\operatorname{den}(H_n))}{n\operatorname{den}(H_n)}.
```
Thus reduction of the partial sum, and the common factor of its reduced denominator with $`n`$, determine the best scale available in this criterion. The eventual inequality above remains unproved here; failure of a larger clearing multiplier does not establish its failure.

Duverney’s Theorem 3.1 includes the quadratic growth assumption $`cu_n^2\le u_{n+1}\le c'u_n^2`$ for positive constants $`c,c'`$, while $`u_{n+1}/u_n^2\to0`$ for $`u_n=n!-1`$ \[duverney, (1.3), p. 275; Thm. 3.1, pp. 285–286\]. His Corollary 3.2, which allows signs $`a_n\in\{-1,1\}`$, assumes convergence of the signed series $`\sum_n(u_{n+1}/u_n^2-1)`$ in (3.6) \[duverney, Cor. 3.2, p. 287\]. Its terms tend to $`-1`$ here, so the series does not converge. The supplied Lean records check the ratio limit and also the divergence of the absolute-value series; the signed condition fails already by the term test. To see the ratio limit directly, divide numerator and denominator by $`(n!)^2`$: the numerator tends to zero and the denominator $`(1-1/n!)^2`$ tends to one.

For a strictly increasing sequence $`(n_k)`$ of positive integers, Erdős proved irrationality of $`\sum_k1/n_k`$ under the following conditions, with a fixed $`\varepsilon>0`$ \[erdos1975, Theorem 1, p. 1\]:
``` math
\limsup_{k\to\infty}n_k^{1/2^k}=\infty,
 \qquad n_k>k^{1+\varepsilon}\quad\text{eventually}.
```
Barreto, Kang, Kim, Kovač and Zhang treat products of consecutive denominators and weighted extensions \[barreto-et-al, Thms. 2–3 and Rem. 4, pp. 2–5\]. For $`a_n=n!-1`$ and every fixed $`\psi>1`$,
``` math
0\le\frac{\log(n!-1)}{\psi^n}\le\frac{n^2}{\psi^n}\longrightarrow0,
 \qquad (n!-1)^{1/\psi^n}\longrightarrow1.
```
Thus neither Erdős’s limsup hypothesis, which uses $`\psi=2`$, nor the growth hypotheses of their Theorems 2 and 3 hold. The supplied Lean limit is the special case $`\psi=2`$; the estimate above also covers the other bases greater than one used in those theorems. Their proof of Theorem 3 uses the classical criterion, which they trace to Fourier’s proof that $`e`$ is irrational, that a rational sum of nonnegative rationals with infinitely many positive terms admits no prefix-clearing integers $`D_N`$ with $`\liminf_ND_Nr_N=0`$, where $`r_N`$ is the tail after $`N`$ terms \[barreto-et-al, Lem. 8, p. 6\]; their Proposition 12 produces such integers under the hypotheses of that theorem \[barreto-et-al, pp. 9–12\]. For the present series, even the full summand lcm $`L_N`$ makes $`L_N(S-H_N)`$ tend to infinity, as shown in §<a href="#long68:sec:lcm" data-reference-type="ref" data-reference="long68:sec:lcm">2</a>. A smaller integer cannot clear every summand. It can nevertheless clear the partial sum after addition: the least positive such integer is $`\operatorname{den}(H_N)`$, and every other one is a multiple of it. Thus this criterion would require information about cancellation in the reduced partial sum, not merely an improvement from the product to the lcm. More precisely, if $`S=a/q`$, then
``` math
q\operatorname{den}(H_N)(S-H_N)\in\mathbb Z_{>0},
 \qquad \operatorname{den}(H_N)(S-H_N)\ge\frac1q.
```
Thus $`\liminf_N\operatorname{den}(H_N)(S-H_N)=0`$ is a sufficient target for this prefix-clearing criterion; the preceding common-denominator estimates do not establish it.

Dividing the recurrence $`Z_m=mZ_{m-1}+1-b_m`$ by $`m!`$ and telescoping gives the exact finite identity
``` math
\frac{Z_M}{M!}=\frac{Z_2}{2!}+\sum_{m=3}^{M}\frac{1-b_m}{m!},
```
so the carry defects $`1-b_m`$ are integer coefficients of a factorial series. Hančl and Tijdeman classify the rational sums with polynomial coefficients \[hancl-tijdeman, Thm. 3.1 and Cor. 3.1, pp. 390–391\]; their denominator is the cumulative linear product $`\prod_{n\le N}(an+b)`$, and the individual number $`N!-1`$ does not occur. In the factorial case $`a=1`$, $`b=0`$, the criterion of Oppenheim that they reproduce \[hancl-tijdeman, Lem. 2.2, p. 385\] says the following: for integer coefficients $`c_n`$ with $`|c_n|<n`$ eventually and $`\liminf_n|c_n|/n=0`$, the sum $`\sum_n c_n/n!`$ is rational exactly when $`c_n=0`$ eventually. This formulation concerns integer coefficients and factorial denominators, not reciprocal terms with denominator $`n!-1`$. However, their introduction records a version of Oppenheim’s result without the liminf assumption: under $`|c_m|<m-1`$ eventually, rationality is equivalent to eventual vanishing \[hancl-tijdeman, Introduction, p. 383\]. Changing finitely many terms adds a rational number, so eventual hypotheses suffice. Here $`2-m\le c_m=1-b_m\le2`$ gives $`|c_m|<m-1`$ for $`m\ge4`$; the classical result therefore applies directly.

For completeness, the following elementary proof specialises that result to these one-sided bounds. For $`N\ge2`$, telescoping $`\sum_{m>N}(m-1)/m!=1/N!`$ gives
``` math
-1<N!\sum_{m>N}\frac{c_m}{m!}
 \le2N!\sum_{m>N}\frac1{m!}<\frac2N.
```
The lower bound follows from $`c_m\ge2-m`$ and $`N!\sum_{m>N}(m-2)/m!=1-N!\sum_{m>N}1/m!<1`$. The upper bound follows by comparison with $`\sum_{j\ge1}(N+1)^{-j}=1/N`$. If $`\sum_{m\ge3}c_m/m!`$ is rational, the scaled tails are integers for all sufficiently large $`N`$. They must then be zero, and subtracting consecutive tails gives $`c_m=0`$ eventually. The converse is immediate. Since $`Z_M/M!\to S`$, the displayed finite identity recovers Theorem <a href="#long68:res:carry-equivalence" data-reference-type="ref" data-reference="long68:res:carry-equivalence">8</a>. This is a self-contained specialisation of the classical rationality criterion, not a strengthening of it. It proves an equivalence, not the nonvanishing needed for irrationality.

<a id="long68:sec:ext-superseded"></a>

## A superseded deduction

A multiplicity theorem gives a weaker lcm bound, which is useful for comparison with the elementary proof in §<a href="#long68:sec:lcm" data-reference-type="ref" data-reference="long68:sec:lcm">2</a>. For an odd prime $`r`$, let $`m_r`$ count the indices $`2\le n\le N`$ with $`r\mid n!-1`$; such an index satisfies $`n<r`$. The factorial-congruence multiplicity estimate of Garaev, Luca and Shparlinski \[garaev-luca-shparlinski, arXiv v1, Thm. 12, p. 16\], applied to the residue $`a=1`$ on $`1\le n\le\min(N,r-1)`$, gives $`m_r\ll N^{2/3}`$; the prime $`2`$ divides none of these factors. The sum of the exponents at a prime is at most the number of occurrences times the largest exponent, which is its exponent in $`L_N`$. Thus
``` math
\sum_{n=2}^{N}\log(n!-1)=\sum_r\sum_{n=2}^{N}v_r(n!-1)\log r
 \le\bigl(\max_r m_r\bigr)\log L_N
 \ll N^{2/3}\log L_N ,
```
and Stirling’s formula makes the left side $`\asymp N^2\log N`$, whence $`\log L_N\gg N^{4/3}\log N`$. Theorem <a href="#long68:res:lcm-growth" data-reference-type="ref" data-reference="long68:res:lcm-growth">7</a> supersedes this: its exponent is $`3/2`$, its constant is explicit, and it does not use the external multiplicity theorem. The deduction is retained because it is the only place a multiplicity bound enters the record.

Dividing all coefficients by their gcd does not evade the lcm restriction: the resulting integer vector still has $`V_2=\cdots=V_D=0`$, so its moment is still divisible by $`L_D`$. For the nonzero cofactor vector in §<a href="#long68:sec:open" data-reference-type="ref" data-reference="long68:sec:open">7</a>, normalization is justified by the elementary argument given there. It supplies no proof that the remainder is nonintegral. No formalised primitive cofactor construction is claimed here.

<a id="long68:sec:ext-plateau"></a>

## Rational grid points and first crossings

One can instead compare a partial sum $`H`$ with the rational numbers having a fixed positive denominator $`q`$. The next such number above $`H`$ is $`(\lfloor qH\rfloor+1)/q`$. It is at most $`S`$ exactly when $`\lfloor qH\rfloor+1\le qS`$. Suppose $`H<G\le S`$, the number $`n!G`$ is an integer, and $`n!(S-H)<1`$. Then
``` math
n!H<n!G\le n!S<n!H+1.
```
Thus $`n!G`$ is both the least integer strictly above $`n!H`$ and the floor of $`n!S`$. In particular, for $`n\ge2`$, suppose a single rational level $`G`$ satisfies $`H_{n+1}<G\le S`$ and $`n!G\in\mathbb{Z}`$. Since $`H_n<H_{n+1}`$, the tail bounds at both indices give
``` math
\lfloor(n+1)!S\rfloor=(n+1)!G
   =(n+1)\lfloor n!S\rfloor.
```
The next canonical digit is therefore zero. The same level must persist at both indices; choosing an unrelated rational level at each index would not imply this equality.

Set $`H_1=0`$, the empty partial sum. Now let $`\tau\ge2`$ be a first crossing of a rational level $`G`$, so that $`H_{\tau-1}<G\le H_\tau`$, and write $`G-H_{\tau-1}=a/v`$ with positive integers $`a,v`$. The newly added summand gives
``` math
0<\frac av\le\frac1{\tau!-1},
 \qquad v\ge a(\tau!-1)\ge\tau!-1.
```
The scaled overshoot is
``` math
0\le\tau!(H_\tau-G)
 =1+\frac1{\tau!-1}-\tau!\frac av<2.
```
Consequently $`-\lfloor\tau!(H_\tau-G)\rfloor`$ is $`0`$ or $`-1`$. Here the minus sign is outside the floor; taking the floor of the negative overshoot would give a different integer at nonintegral overshoots. The displayed integer is $`-1`$ precisely when the overshoot is at least $`1`$, or equivalently when
``` math
\frac av\le\frac1{\tau!(\tau!-1)}.
```
In that case $`v\ge\tau!(\tau!-1)`$. This extra small-gap condition is not asserted for every crossing. Nor is $`-\lfloor\tau!(H_\tau-G)\rfloor`$ automatically the carry $`b_\tau`$ defined from $`Z_\tau`$: here $`G`$ is an arbitrary rational level. Neither denominator bound requires $`a/v`$ to be in lowest terms.

There is also a direct obstruction at prime indices. With $`\Delta_m`$ as defined in §<a href="#long68:sec:carry" data-reference-type="ref" data-reference="long68:sec:carry">3</a>, the formal source proves for $`m\ge3`$ the criterion
``` math
m\mid Z_m
 \quad\Longleftrightarrow\quad
 1+\frac1{m!-1}<m\Delta_m\le2+\frac1{m!-1},
```
and if $`S=a/q`$ with $`q>0`$, then $`p\mid Z_p`$ for every prime $`p>q`$, so one exact missed prime $`p`$ gives $`q\ge p`$. Exact kernel reduction gives $`11\nmid Z_{11}`$, hence $`q\ge11`$; exact rational normalisation gives $`60\nmid Z_{60}`$, $`64\nmid Z_{64}`$ and $`67\nmid Z_{67}`$, and the prime index $`67`$ gives the checked bound
``` math
S=\frac aq,\ q>0\quad\Longrightarrow\quad q\ge67 .
```
The exact-interval census of the short note replaces $`67`$ by $`300000`$.

The finite geometric-series identity gives another exact decomposition. For a real $`x\ne0,1`$ and an integer $`K\ge0`$,
``` math
\frac1{x-1}=\sum_{j=1}^{K}\frac1{x^j}+\frac1{x^K(x-1)} .
```
When $`x=k!`$ and a chosen factorial scale is divisible by $`(k!)^K`$, the scaled finite sum is integral and only the last term retains the factor $`k!-1`$ in its denominator. The identity isolates one residual fraction before exact bounding, and it supplies no cofinal family of nonzero residuals.

The earlier record rejects a proposed divisibility strengthening of the first-crossing bound and reports examples at $`m=52`$ and $`m=591`$. Its notation for the rational quantity in that claim was not defined, so those reports are not used as a verified counterexample here. The established conclusion remains the lower bound on the denominator’s size, not a specified factor dividing it.

There is a second, more arithmetic mechanism at doubled prime indices, stated in <a href="#long68:eq:doubled-prime" data-reference-type="eqref" data-reference="long68:eq:doubled-prime">[long68:eq:doubled-prime]</a>. The formal theorem is not restricted to individually computed indices; the divisibility criterion holds for the actual partial sums at every odd prime.

<a id="long68:sec:ext-collision"></a>

## Exact identities for shared prime powers

The following identities make it possible to update the shared part of a common denominator and to calculate the prime powers left after removal of a factorial factor. Let $`I\subseteq\{2,3,\ldots\}`$ be finite.

Write $`D(I)=\operatorname{lcm}_{i<j,\ i,j\in I}\gcd(d_i,d_j)`$, with $`D(I)=1`$ for an empty or singleton family. For each prime $`r`$, its valuation is the second-largest valuation among the $`d_i`$, counting missing values as zero; the denominator lcm has the largest valuation. This proves $`D(I)\operatorname{lcm}_{i\in I}d_i\mid\prod_{i\in I}d_i`$ prime by prime.

The integer $`D(I)`$ can be updated exactly when one index is added. For the positive factorial-gap denominators, adjoining a new index $`a\ge2`$, $`a\notin I`$, gives
``` math
D(I\cup\{a\})=\operatorname{lcm}\!\Bigl(D(I),\ \gcd\bigl(d_a,\operatorname{lcm}_{j\in I}d_j\bigr)\Bigr),
```
since finite-family gcd and lcm distributivity collapses the lcm of all pairwise gcds against $`d_a`$ to a single gcd. For a fixed positive integer $`F`$, take the lcm with $`F`$ on both sides:
``` math
\operatorname{lcm}\bigl(F,D(I\cup\{a\})\bigr)
 =\operatorname{lcm}\Bigl(F,D(I),\gcd\bigl(d_a,\operatorname{lcm}_{j\in I}d_j\bigr)\Bigr).
```
Thus one need only retain the denominator lcm and $`\operatorname{lcm}(F,D(I))`$ at each step. The prescribed factor $`F`$ is not an extra summand denominator.

There is also an exact bound by the product of the denominators divided by their least common multiple. For a positive integer $`F`$, define $`\widetilde C(I)=\operatorname{lcm}(F,D(I))/F=D(I)/\gcd(F,D(I))`$. Since $`\widetilde C(I)`$ divides $`D(I)`$, the preceding divisibility gives
``` math
\widetilde C(I)\operatorname{lcm}_{j\in I}d_j\mid\prod_{j\in I}d_j,\qquad
 \widetilde C(I)\le\frac{\prod_{j\in I}d_j}{\operatorname{lcm}_{j\in I}d_j}.
```
For the factorial block this specialises to
``` math
\widetilde C_p\le\frac{\prod_{n\in I_p}(n!-1)}{\operatorname{lcm}_{n\in I_p}(n!-1)},
```
an upper bound for the shared factor in terms of the denominator product and lcm. The bound alone does not establish <a href="#long68:eq:weighted-target" data-reference-type="eqref" data-reference="long68:eq:weighted-target">[long68:eq:weighted-target]</a>.

Dividing by $`F_p`$ subtracts its prime exponents; it does not remove every prime that occurs in $`F_p`$. With $`F_p=(p-1)!`$, $`D_p=D(I_p)`$ and $`C_p=\operatorname{lcm}(F_p,D_p)`$, as in the main record,
``` math
\widetilde C_p=\frac{C_p}{F_p}=\frac{D_p}{\gcd(F_p,D_p)},\qquad
 v_r(\widetilde C_p)=\max\{0,v_r(D_p)-v_r(F_p)\} .
```
For $`e>0`$, $`r^e\mid\widetilde C_p`$ exactly when $`D_p`$ is divisible by $`r^{e+v_r(F_p)}`$, which in the block forces two distinct denominators to be divisible by that higher power, by the second-largest-valuation formula. If $`i<j`$ are two such hits and $`f=v_r(F_p)`$, then $`r^{e+f}\mid j!/i!-1`$. Since $`r\mid j!-1`$ forces $`j<r`$, $`0<j!/i!-1<r^{j-i}`$, hence $`e+f<j-i`$. For a prime $`r\mid\widetilde C_p`$, this bounds the surviving valuation by $`v_r(\widetilde C_p)+v_r(F_p)<r`$. Since $`v_r(\widetilde C_p)\ge1`$ and $`v_r(F_p)\ge\lfloor(p-1)/r\rfloor`$, we obtain $`\lfloor(p-1)/r\rfloor\le r-2`$, hence $`p-1<r(r-1)<r^2`$. Consequently $`\widetilde C_p`$ is coprime to $`k!`$ whenever $`k(k-1)\le p-1`$: a prime $`r\le k`$ dividing both would give $`p-1<r(r-1)\le k(k-1)\le p-1`$. This excludes the small primes but does not bound the product of the remaining prime powers.

If a prime $`r`$ divides a denominator $`n!-1`$ with $`n\ge p`$, then $`r\nmid F_p`$ and $`r^e\mid\widetilde C_p\iff r^e\mid C_p`$ for every $`e>0`$. This has an exact incidence-count form,
``` math
r^e\mid\widetilde C_p
 \quad\Longleftrightarrow\quad
 1<\#\{i\in I_p:r^e\mid i!-1\},
```
so a bound of at most one such index implies $`v_r(\widetilde C_p)<e`$. Counting the exponents gives
``` math
v_r(\widetilde C_p)=\#\bigl\{e\in[1,r-1]:1<\#\{i\in I_p:r^e\mid i!-1\}\bigr\},
```
and for a prime $`r>2p-1`$ the range can be restricted to $`e\in[1,2p-4]`$. The same equivalence holds under the exact condition $`r\nmid F_p`$ in place of $`r>2p-1`$, hence in particular for every prime $`r\ge p`$. At $`e=2`$, an upper bound of one on the number of indices gives $`v_r(\widetilde C_p)\le1`$.

A surviving prime power also forces two indices to be far apart. If $`r`$ is prime, $`e>0`$ and $`r^e\mid\widetilde C_p`$, there are $`i<j`$ in $`I_p`$ with $`r^{e+v_r(F_p)}\mid i!-1`$, $`r^{e+v_r(F_p)}\mid j!-1`$ and $`r^{e+v_r(F_p)}\le j^{\,j-i}`$; consequently $`(2p-1)^d<r^{e+v_r(F_p)}`$ forces $`d<j-i`$. The required spacing follows directly: any two $`r^e`$-hits $`i<j`$ satisfy $`e<j-i`$, because $`r\mid j!-1`$ already forces $`j<r`$ and the inequality for $`j!/i!-1`$ then forces the strict separation. More generally, for any two indices $`2\le i<j`$ and any prime power $`r^e`$ with $`e>0`$,
``` math
r^e\mid i!-1,\quad r^e\mid j!-1
 \quad\Longrightarrow\quad r^e\le j^{\,j-i},
```
so successive solutions of $`i!\equiv1\pmod{r^e}`$ are at least $`e+1`$ apart, and
``` math
(e+1)\,\#\{i\in I_p:r^e\mid i!-1\}\ \le\ 2p+e-2 .
```
The resulting bound on the exponent is
``` math
r\mid\widetilde C_p
 \quad\Longrightarrow\quad
 v_r(\widetilde C_p)+v_r(F_p)<2p-3
```
for every prime $`r`$ and $`p\ge2`$. Thus the exponent already present in $`F_p`$ uses part of the same bound $`2p-3`$. To apply <a href="#long68:eq:global-scale" data-reference-type="eqref" data-reference="long68:eq:global-scale">[long68:eq:global-scale]</a>, one still needs sufficiently strong bounds for the product of the shared prime powers and for the gap $`\rho_p/R_p`$.

The available squarefreeness evidence is finite. An exhaustive modular scan through $`r\le2{,}000{,}000`$ and $`n\le240`$ found four individual square hits and no prime with two such hits. All $`498{,}501`$ pairs $`2\le a<b\le1000`$ have squarefree $`\gcd(a!-1,b!-1)`$. The supplied aggregate scan through $`p=499`$ also reports a ratio below $`0.374`$, but does not specify its logarithmic normalisation; that ratio is not used as a quantitative premise here. These are reported finite computations, not an asymptotic bound or a proof of squarefreeness at all indices.

A finite version of the argument for first prime occurrences compares the product of a chosen set of primes, each at least $`5`$, with $`\prod_{2\le k\le B}(k!-1)`$; if the prime product is larger, at least one chosen prime has no hit through $`B`$, while Wilson still bounds its least hit by $`q-2`$. Wilson reflection limits what a linear-size divisor can be assumed to be: if $`n`$ is odd, $`n<q`$, and $`q\mid n!-1`$, then $`q\mid(q-n-1)!-1`$. Suppose also that $`p\le n`$, both indices lie in $`I_p`$, and the reflected index is earlier, equivalently $`q<2n+1`$. The prime $`q`$ then divides two denominators in the block. Since $`q>n\ge p`$, it does not divide $`F_p=(p-1)!`$, so $`q\mid\widetilde C_p`$: removing the factorial factor does not remove this shared prime.

Stewart states that for every $`\varepsilon>0`$ there are infinitely many odd $`n`$ whose least prime factor $`q`$ of $`n!-1`$ satisfies
``` math
n<q<\left(\frac{\sqrt{145}-1}{8}+\varepsilon\right)n ,
```
estimate (9) of Theorem 1 being stated for $`n!+1`$ \[stewart2004, p. 463\] and transferred to $`n!-1`$ in the text \[stewart2004, p. 464\]. This controls $`q`$ relative to the specified index $`n`$, not to its first occurrence. It does not by itself force a repeated divisor. For the minus sign, the bound is already met at all sufficiently large Wilson indices $`n=q-2`$. For every prime $`q\ge5`$, Wilson gives $`q\mid(q-2)!-1`$, and $`q`$ is its least prime factor. Indeed, every prime divisor exceeds $`q-2`$, and $`q-1`$ is even; moreover $`q/(q-2)\to1`$. The reflected index is then $`1`$, outside the denominators of $`S`$.

For example, modulo $`11`$ the only solution of $`k!\equiv1`$ with $`2\le k\le9`$ is $`k=9`$, although $`11/9<(\sqrt{145}-1)/8`$. A small ratio $`q/n`$ therefore supplies neither a second admissible hit nor membership of a reflected index in the chosen block. The earlier reflection argument needs both block-membership hypotheses and distinct indices. Neither the required estimate at first occurrences nor a bound for the total shared part follows from the transferred least-prime-factor estimate alone.

For a selected prime $`q\mid R_p`$, the factors $`1`$ and $`q`$ are coprime, and the associated moduli $`R_p`$ and $`R_p/q`$ have lcm $`R_p`$. Thus this specialisation requires no second selected prime.

The elementary fact behind the projection argument is as follows. Let $`Z,T,B`$ be nonnegative integers, let $`R>0`$, and suppose $`Z\equiv T\pmod R`$. Every positive divisor $`Q`$ of $`R`$ with $`Z\le B<Q`$ satisfies $`T\bmod Q=Z`$, since $`Z`$ is already the least nonnegative representative. Consequently, unequal residues modulo two divisors exceeding $`B`$ rule out such a $`Z`$. More generally, if $`T\bmod Q_1\ne T\bmod Q_2`$, then $`\min(Q_1,Q_2)\le T`$: otherwise both residues would equal $`T`$.

<a id="long68:sec:ext-certificates"></a>

## Finite vectors and exact numerical examples

The minimum-moment vector $`12K_4+253U_6-11U_8`$ from §<a href="#long68:sec:channels" data-reference-type="ref" data-reference="long68:sec:channels">5</a> also gives a finite nonintegral remainder. By Theorem <a href="#long68:res:residual-transparency" data-reference-type="ref" data-reference="long68:res:residual-transparency">16</a>, its remainder is $`242+1380(S-H_4)`$. Exact rational arithmetic gives
``` math
255+\frac45
 <242+1380\sum_{d=5}^{8}\frac1{d!-1}
 <255+\frac56,
 \qquad \frac{2\cdot1380}{9!-1}<\frac1{100}.
```
The tail bound therefore places the remainder strictly between $`255`$ and $`256`$. Its fractional part, rather than the size of the remainder itself, is what excludes denominators dividing $`1380`$. This small instance explains the signed-part comparison in the short note; the headline finite exclusions already imply its denominator restriction.

The finite-support vector $`\lambda=2e_3-e_4`$ has, by kernel check, $`V_{2}(\lambda)=0`$, factorial moment $`-12`$, $`V_{3}(\lambda)=-2`$, $`V_{4}(\lambda)=11`$, and $`V_{d}(\lambda)=-12`$ for every $`d\ge5`$. Under the exact tail enclosure $`1/119<\sum_{d\ge5}1/(d!-1)<1/50`$ its residual lies strictly between $`-93/575`$ and $`-309/13685`$, so it is nonzero and has absolute value less than $`1`$.

In the enlarged coefficient space of §<a href="#long68:sec:channels" data-reference-type="ref" data-reference="long68:sec:channels">5</a>, exact integer computation verifies the vectors $`K_D`$ for every $`2\le D\le12`$: weighted sums $`2`$ through $`D`$ vanish, the factorial moment is $`L_D`$, and the coefficients have gcd one. They lie outside the space of vectors supported on $`n\ge2`$, since $`L_D`$ is odd and every such vector has even moment. At $`D=9`$,
``` math
L_9=31540008254514077395,\qquad a_9=[e_1]K_9=-3902884074990939115 .
```
Since $`U_{11}=T_{11}`$ has $`u_{11}=0`$, the vector $`K_9-9553024718754\,U_{11}`$ keeps the coordinate $`a_9`$ and has coefficients with gcd one. By Theorem <a href="#long68:res:residual-transparency" data-reference-type="ref" data-reference="long68:res:residual-transparency">16</a> its residual is $`L_9(S-H_9)-9553024718754`$, and exact rational arithmetic with the tail bound $`\sum_{n\ge36}1/(n!-1)<2/(36!-1)`$ places it strictly between $`1353/100000`$ and $`1354/100000`$. A different example is supported on $`n\ge2`$: the vector $`c=(-40,55,-10,1)`$ on the support $`(3,4,5,6)`$ annihilates weighted sums $`2`$ and $`3`$, has moment $`600`$, and satisfies
``` math
0.09925341997208298<\mathcal R(c)<0.09925341997208300 ,
```
which excludes denominators dividing $`600`$.

A separate interval computation reports the stronger geometric statement that no lower-interval event $`m\theta_{m-1}<E_m`$ occurs at any $`3\le m\le100000`$; its executable and source digest are not available, so that classification remains external finite evidence. The carry census through $`300000`$ used in the short note is the GMP computation reported in the supplied manuscript, not a run repeated for this prose revision. Section <a href="#long68:sec:finite" data-reference-type="ref" data-reference="long68:sec:finite">6</a> records its reported driver, backend and payload digests and the separate earlier calculation through $`4000`$. The full range is external computational evidence outside the Lean development. The original prose packet contains the manuscript’s report, not the complete GMP executable and payload, so the present revision does not independently authenticate those digests.

<a id="long68:sec:ext-nogo"></a>

## Limits of the recurrences and clearing factors used here

- Without the defining floor relation, the carry recurrence and its range allow $`Z_m/m!`$ to be the constant $`3/2`$. Taking $`Z_m=3m!/2`$ for $`m\ge2`$ and $`b_m=1`$ for $`m\ge3`$ gives $`Z_m=mZ_{m-1}+1-b_m`$ and $`-1\le b_m\le m-1`$, with the actual initial value $`Z_2=3`$. But it gives $`Z_3=9`$, whereas the actual prefix $`H_3=6/5`$ gives $`Z_3=8`$. This example only disproves sufficiency of the stated recurrence, bounds and initial integer. It fails the floor definition. No claim is made that it satisfies the additional prime-index identities. The rational recurrence for $`F_m=m!H_m`$ in §<a href="#long68:sec:ext-digits" data-reference-type="ref" data-reference="long68:sec:ext-digits">9.1</a> determines the actual partial sums uniquely.

- The arguments considered with Wilson quotients, harmonic sums, $`p`$-adic gamma identities, and factorial residues still need a real gap estimate and the required modular divisibility at the same indices. No such unbounded family is obtained here. This records the missing step in these arguments, not an impossibility theorem for the use of those identities.

- For the genus-zero product $`E(z)=\prod_{n\ge2}(1-z/n!)`$, local uniform convergence and logarithmic differentiation give $`-E'(1)/E(1)=S`$. Termwise clearing by $`\prod_{n=2}^N(n!-1)`$ cannot give a positive remainder tending to zero: this product is at least $`L_N`$, and $`L_N(S-H_N)\to\infty`$ by §<a href="#long68:sec:lcm" data-reference-type="ref" data-reference="long68:sec:lcm">2</a>. The conclusion concerns this clearing factor alone; Hermite–Padé systems with other denominators are not ruled out.

- Changing a coefficient vector without changing its moment changes the residual by an integer only. Also, cancelling the first $`D-1`$ weighted sums forces $`L_D`$ to divide the moment; factorial divisibility does not remove that constraint.

- A fixed pair of denominator indices cannot make the projection argument work at arbitrarily large parameters, because their factors eventually divide the factorial being removed.

<a id="long68:sec:ext-generic"></a>

## An elementary criterion for any real number

The fractional-part condition in <a href="#long68:eq:lower-escape" data-reference-type="eqref" data-reference="long68:eq:lower-escape">[long68:eq:lower-escape]</a> follows from the following consequence of Cantor’s termination criterion. For a real $`x`$ and any positive sequence $`c_m`$ with $`c_m\le1/m`$ eventually,
``` math
x\notin\mathbb{Q}
 \quad\Longleftrightarrow\quad
 \{(m-1)!\,x\}\ge c_m\ \hbox{for arbitrarily large }m .
```
For rational $`x`$ the fractional parts vanish eventually. Conversely, if $`\{(m-1)!x\}<c_m\le1/m`$ for all large $`m`$, then $`m\{(m-1)!x\}<1`$, so every sufficiently late canonical digit is zero. Cantor’s criterion then makes $`x`$ rational. Equality $`c_m=1/m`$ is allowed: it is failure of the displayed weak inequality that makes $`m\{(m-1)!x\}`$ strictly less than one. For $`x=S`$, the choice $`c_m=E_m/m`$ gives exactly <a href="#long68:eq:lower-escape" data-reference-type="eqref" data-reference="long68:eq:lower-escape">[long68:eq:lower-escape]</a>; indeed $`0<E_m<1`$ ensures the required threshold bound. The finite test <a href="#long68:eq:finite-escape" data-reference-type="eqref" data-reference="long68:eq:finite-escape">[long68:eq:finite-escape]</a> is a separate sufficient condition at one index. Its cofinal converse uses the carry theorem, as shown in §<a href="#long68:sec:carry" data-reference-type="ref" data-reference="long68:sec:carry">3</a>, not substitution into this general criterion. Neither argument proves that $`S`$ meets the test at arbitrarily large indices.

The threshold $`1/m`$ cannot be replaced by $`\lambda/m`$ for a fixed $`\lambda>1`$. For $`x=e`$ and $`m\ge3`$, the factorial tail gives
``` math
m\{(m-1)!e\}
 =1+m!\sum_{n>m}\frac1{n!}<1+\frac1m<\lambda
 \qquad\text{eventually}.
```
Thus the irrational number $`e`$ would never meet the enlarged threshold at sufficiently large indices. Positivity is also essential: with $`c_m=0`$, rational numbers would meet the threshold eventually. These examples explain the two assumptions without imposing any equidistribution hypothesis.

<a id="sec:erdos-68-complete-family-map"></a>

# Relations among the criteria

The two finite exclusions in §<a href="#long68:sec:finite" data-reference-type="ref" data-reference="long68:sec:finite">6</a> use only the carry criterion and a rational enclosure. The coefficient constructions do not enter either calculation. They instead produce integer linear forms $`\mathcal R(c)=M(c)S+k`$, $`k\in\mathbb{Z}`$. At fixed moment, changing coefficients changes only $`k`$; primitive cofactors on the stated progression reproduce the explicit progression vector rather than a new family.

For a rational value $`S=a/q`$, such a form is integral whenever $`q\mid M(c)`$. To extend this method beyond finite exclusions, one therefore needs nonintegral remainders with moments covering every positive denominator in this divisibility sense. The common-denominator lower bound and the prime-power survival test do not supply the needed upper bound for a remainder relative to its integer gap. Likewise, the equivalent carry, digit and interval criteria still require events at arbitrarily large indices. A finite calculation can rule out denominators without proving any of those unbounded assertions.

<a id="acknowledgements"></a>

# Acknowledgements

The author thanks Wouter van Doorn for advice on exposition: explaining notation when it first appears, avoiding private terminology, and saying how restrictive a conditional hypothesis is. His advice concerned the writing of another note; he has not reviewed the mathematics of this paper.

<div class="thebibliography">

99

Paul Erdős. [On the irrationality of certain series: problems and results](https://doi.org/10.1017/CBO9780511897184.009). In Alan Baker (ed.), *New Advances in Transcendence Theory*, Cambridge University Press (1988), pp. 102–109.

Thomas F. Bloom. [Erdős Problem \#68](https://www.erdosproblems.com/68). Online resource (2026). Historical access: 28 July 2026; present-page status not reverified.

Paul Erdős. [Some problems and results on the irrationality of the sum of infinite series](https://www.renyi.hu/~p_erdos/1976-44.pdf). *Journal of Mathematical Sciences* **10** (1975), 1–7.

Joel Louwsma and Joseph Martino. [Rational numbers with odd greedy expansion of fixed length](https://arxiv.org/abs/2309.07280v1). Preprint (2023). arXiv:2309.07280.

Georg Cantor. Über die einfachen Zahlensysteme. *Zeitschrift für Mathematik und Physik* **14** (1869), 121–128.

János Galambos. [Representations of Real Numbers by Infinite Series](https://doi.org/10.1007/BFb0081642). Lecture Notes in Mathematics 502, Springer (1976).

Moubariz Z. Garaev, Florian Luca and Igor E. Shparlinski. [Character sums and congruences with $`n!`$](https://doi.org/10.1090/S0002-9947-04-03612-8). *Transactions of the American Mathematical Society* **356** (12) (2004), 5089–5102. arXiv:math/0403422.

Cameron L. Stewart. [On the greatest and least prime factors of $`n!+1`$, II](https://doi.org/10.5486/PMD.2004.3190). *Publicationes Mathematicae Debrecen* **65** (3–4) (2004), 461–480.

Wolfram Koepf and Dieter Schmersau. [Irrationality of certain infinite series II](https://doi.org/10.1524/anly.2011.1094). *Analysis* **31** (2011), 117–124.

Daniel Duverney. [Irrationality of fast converging series of rational numbers](https://www.ms.u-tokyo.ac.jp/journal/pdf/jms080206.pdf). *Journal of Mathematical Sciences, the University of Tokyo* **8** (2001), 275–316.

Jaroslav Hančl and Robert Tijdeman. [On the irrationality of factorial series](https://doi.org/10.4064/aa118-4-5). *Acta Arithmetica* **118** (4) (2005), 383–401.

Kevin Barreto, Jiwon Kang, Sang-hyun Kim, Vjekoslav Kovač and Shengtong Zhang. [Irrationality of rapidly converging series: a problem of Erdős and Graham](https://arxiv.org/abs/2601.21442v3). Preprint (2026). arXiv:2601.21442.

Florian Luca and Igor E. Shparlinski. [Prime divisors of shifted factorials](https://doi.org/10.1112/S0024609305004923). *Bulletin of the London Mathematical Society* **37** (6) (2005), 809–817.

Li Lai. [On the largest prime divisor of $`n!+1`$](https://doi.org/10.1017/S0004972725100543). *Bulletin of the Australian Mathematical Society* **113** (3) (2026), 390–403. arXiv:2103.14894.

Li Lai, Cezar Lupu and Johannes Sprang. [On the irrationality of certain $`p`$-adic zeta values](https://doi.org/10.1007/s40687-025-00559-x). *Research in the Mathematical Sciences* **12** (4) (2025), article 77. arXiv:2505.23088.

Li Lai. [On the irrationality of certain $`2`$-adic zeta values](https://doi.org/10.1142/S1793042125500113). *International Journal of Number Theory* **21** (1) (2025), 207–235. arXiv:2304.00816.

NIST Digital Library of Mathematical Functions. [Continued fractions: convergents](https://dlmf.nist.gov/1.12). Online resource (2026).

Paul Erdős and Cameron L. Stewart. [On the greatest and least prime factors of $`n!+1`$](https://doi.org/10.1112/jlms/s2-13.3.513). *Journal of the London Mathematical Society* **13** (3) (1976), 513–519.

Florian Luca and Igor E. Shparlinski. [On the largest prime factor of $`n!+2^n-1`$](https://doi.org/10.5802/jtnb.524). *Journal de Théorie des Nombres de Bordeaux* **17** (3) (2005), 859–870.

Moubariz Z. Garaev, Florian Luca and Igor E. Shparlinski. [Distribution of harmonic sums and Bernoulli polynomials modulo a prime](https://doi.org/10.1007/s00209-006-0939-5). *Mathematische Zeitschrift* **253** (2006), 855–865.

Jonathan Sondow. [A geometric proof that $`e`$ is irrational and a new measure of its irrationality](https://arxiv.org/abs/0704.1282v2). *American Mathematical Monthly* **113** (7) (2006), 637–641. arXiv:0704.1282. Addendum: *Amer. Math. Monthly* **114** (2007), 659; reading copy v2.

Xiyu Hu. [Factorial residues modulo a prime: beyond the square-root bound](https://arxiv.org/abs/2608.01781v1). Preprint (2026). arXiv:2608.01781. Version 1, 3 August 2026.

Moubariz Z. Garaev and Julio C. Pardo. [Additive congruences with factorials modulo a prime](https://doi.org/10.1090/proc/17753). *Proceedings of the American Mathematical Society* **154** (10) (2026), 4179–4190. arXiv:2508.12127. Published online 1 July 2026; assigned October 2026 issue.

Xiyu Hu. [Lower bounds for some value sets over finite fields: incidence geometry and Bourgain’s group expansion theorem](https://arxiv.org/abs/2609.05652v1). Preprint (2026). arXiv:2609.05652. Version 1, 4 September 2026.

William D. Banks, Florian Luca, Igor E. Shparlinski and Henning Stichtenoth. [On the Value Set of $`n!`$ Modulo a Prime](https://journals.tubitak.gov.tr/math/vol29/iss2/6/). *Turkish Journal of Mathematics* **29** (2) (2005), 169–174.

Oleksiy Klurman and Marc Munsch. [Distribution of factorials modulo $`p`$](https://doi.org/10.5802/jtnb.974). *Journal de Théorie des Nombres de Bordeaux* **29** (1) (2017), 169–177.

Alexandr Grebennikov, Arsenii Sagdeev, Aliaksei Semchankau and Aliaksei Vasilevskii. [On the sequence $`n!`$ mod $`p`$](https://doi.org/10.4171/RMI/1422). *Revista Matemática Iberoamericana* **40** (2) (2024), 637–648.

Sophie Stevens and Frank de Zeeuw. [An improved point-line incidence bound over arbitrary fields](https://doi.org/10.1112/blms.12077). *Bulletin of the London Mathematical Society* **49** (5) (2017), 842–858. arXiv:1609.06284.

R. A. Macleod and I. Barrodale. [On Equal Products of Consecutive Integers](https://doi.org/10.4153/CMB-1970-052-8). *Canadian Mathematical Bulletin* **13** (2) (1970), 255–259.

Nguyen Xuan Tho. [On equal products of consecutive integers](https://doi.org/10.4171/EM/556). *Elemente der Mathematik* **81** (3) (2026), 119–124. First published online 10 July 2025.

Paul Erdős and John L. Selfridge. [The product of consecutive integers is never a power](https://doi.org/10.1215/ijm/1256050816). *Illinois Journal of Mathematics* **19** (2) (1975), 292–301.

NIST Digital Library of Mathematical Functions. [Vandermonde determinant](https://dlmf.nist.gov/1.3.E13), §1.3(ii), formula (1.3.13). Online resource, consulted 18 September 2026.

</div>
