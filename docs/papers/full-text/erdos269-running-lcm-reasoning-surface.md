<a id="erdos269-running-lcm-reasoning-surface"></a>

# The Three-Prime Running LCM: Kernel Rank and Tail Arithmetic

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

The reciprocal three-prime running-LCM kernel has nonsingular minors of every order: row and column rescaling leaves a two-valued matrix, and density supplies the required threshold pattern. For the rescaled matrix, we compute the rank of every finite restriction and the least uniform approximation error over all matrices of finite separated rank. For the repeated $`\{2,3,5\}`$ sum, we derive an integer-coefficient tail recurrence and determine exactly when a hypothetical rational denominator would clear. Quadratic tail bounds then give a residue criterion equivalent to irrationality. The unproved step is to find such windows for every positive multiplier coprime to $`30`$ and after every prescribed start. We also give the full two-prime comparison, following Fan’s earlier Hecke–Mahler reduction, and identify the boundary terms that survive a proposed finite-difference cancellation.

<a id="long269:sec:problem"></a>

# The problem, and what is settled

Let $`P`$ be a finite set of primes with $`|P|\ge2`$, and let $`a_1<a_2<\cdots`$ enumerate the positive integers all of whose prime factors lie in $`P`$. Erdős Problem #269 asks whether
``` math
\sum_{n\ge1}\frac{1}{[a_1,\ldots,a_n]}
```
is irrational, where $`[a_1,\ldots,a_n]`$ is the least common multiple \[erdosgraham1980, p. 65\]\[erdos1988, p. 106\]. The problem number is that of Bloom’s catalogue \[erdosproblems\]. Theorem <a href="#long269:res:lead-two-prime" data-reference-type="ref" data-reference="long269:res:lead-two-prime">1</a> settles every instance with $`|P|=2`$, at the level of transcendence, and Fan posted that argument first \[fan2026comment\]; this record leaves the repeated finite cases with $`|P|\ge3`$ unresolved.

Write $`\mathcal R_P`$ for the sum above and $`\mathcal D_P`$ for the sum in which each distinct running-LCM value contributes its reciprocal once. These differ because the running value can repeat. The catalogue question concerns $`\mathcal R_P`$; Erdős’s earlier assertion about $`\mathcal D_P`$ and the singleton and infinite-prime cases are discussed in Section <a href="#long269:long:history" data-reference-type="ref" data-reference="long269:long:history">10.1</a>.

<div id="long269:res:lead-two-prime" class="theorem">

**Theorem 1** (two-prime transcendence). *Let $`p`$ and $`q`$ be distinct primes. Then $`\mathcal R_{\{p,q\}}`$ and $`\mathcal D_{\{p,q\}}`$ are transcendental.*

</div>

Section <a href="#long269:sec:two-prime" data-reference-type="ref" data-reference="long269:sec:two-prime">3</a> proves this by expressing both values as nonconstant polynomials over $`\mathbb Q`$ in the same Hecke–Mahler boundary sum. Transcendence of that sum is the theorem of Loxton and van der Poorten \[loxtonvdp1977, Theorem 8, p. 40\] in the modern form of Bugeaud and Laurent \[bugeaudlaurent2023, Theorem 1.1\]. The two-prime argument therefore consists of an elementary identity followed by that external value theorem.

The supplied forum record credits Steve Fan’s post of 26 June 2026 with the running-LCM identity for finite prime sets, the two-prime factorisation, the Hecke–Mahler reduction and its transcendence conclusion \[fan2026comment\]. We include the calculation to distinguish repeated from distinct-height sums, without claiming priority for that argument.

<a id="what-the-third-prime-changes."></a>

#### What the third prime changes.

With two primes, row and column rescaling reduces the kernel to a constant matrix. With three, the remaining entry is $`1`$ or $`1/r`$, according to whether two fractional parts add to at least one. Their separate density lets us choose nonsingular minors of every order. No joint density assumption is required.

The arithmetic argument starts elsewhere. We group the supported integers between consecutive powers of two, retaining all multiplicities. The resulting normalised tails satisfy an integer-coefficient recurrence. Were the repeated $`\{2,3,5\}`$ sum rational, the part of its denominator coprime to $`30`$ would make every sufficiently late normalised tail a positive integer after multiplication. These integers have a quadratic bound in the index. A least positive residue exceeding that bound would contradict rationality. We prove an equivalence: irrationality holds exactly when suitable windows exist for every remaining denominator and after every prescribed index. The existence of such windows with both quantifiers unrestricted remains unproved. Section <a href="#long269:sec:evidence" data-reference-type="ref" data-reference="long269:sec:evidence">8</a> gives finite tests, and Section <a href="#long269:sec:open" data-reference-type="ref" data-reference="long269:sec:open">9</a> explains the remaining arithmetic question.

We use $`\mathbb{N}=\{0,1,2,\ldots\}`$ for exponent indices and braces for fractional parts. Until the prime set is fixed to $`\{2,3,5\}`$ in Section <a href="#long269:sec:blocks" data-reference-type="ref" data-reference="long269:sec:blocks">5</a>, take $`P=\{p,q,r\}`$ with pairwise distinct primes $`p,q,r`$. An integer is $`P`$-*smooth* when its prime factors lie in $`P`$, equivalently when it has the form $`p^iq^jr^k`$ with $`i,j,k\ge0`$. For $`x\ge1`$ write
``` math
\operatorname{L}(x)=\operatorname{lcm}\{\,n\le x:\ n\ \text{smooth}\,\},
 \qquad
 \operatorname{H}(x)=p^{\lfloor\log_p x\rfloor}\,q^{\lfloor\log_q x\rfloor}\,
 r^{\lfloor\log_r x\rfloor},
```
for the running least common multiple and the product of the three maximal prime powers. We call the latter the height. Here $`\lfloor\log_b x\rfloor`$ is the largest $`e`$ with $`b^{e}\le x`$. Since $`a_1,\ldots,a_n`$ are exactly the smooth numbers up to $`a_n`$, we have $`[a_1,\ldots,a_n]=\operatorname{L}(a_n)`$. We regard the reciprocal height as a function of the exponent triple:
``` math
\operatorname{K}(i,j,k)=\frac{1}{\operatorname{H}(p^{i}q^{j}r^{k})} .
```
For example, $`5`$ and $`6`$ are both supported on $`\{2,3,5\}`$ and have height $`60`$: they contribute twice to $`\mathcal R_P`$ but only once to $`\mathcal D_P`$. For $`P=\{2,3,5\}`$ these are precisely the usual $`5`$-smooth integers. The parameter here is the size of the integer, not a growing smoothness bound $`y`$ in $`\Psi(x,y)`$ \[hildebrand1986\]; no smooth-number density asymptotic is used below. The appropriate fixed-support context is Tijdeman–Meijer \[tijdemanmeijer1974, Sections 1–4\]. The modern two-prime treatment of Languasco, Luca, Moree and Togbé \[languasco2025\] also makes the lattice-triangle geometry explicit; its gap estimates are not inputs to our shell bound. The jumps occur at positive powers of one of the three primes.

Kovač and Tao \[kovactao2024\] treat several other irrationality problems for unit-fraction series by elementary means; their results are not inputs to the present arguments. The formal statement of Problem #269 and its rational normalisation are discussed in Section <a href="#long269:long:history" data-reference-type="ref" data-reference="long269:long:history">10.1</a>.

**Keywords.** irrationality; transcendence; least common multiple; smooth numbers; separated rank; Lean 4. **MSC 2020.** 11J72 (primary); 11A05, 11N25, 68V20 (secondary).

<a id="relation-to-the-short-paper."></a>

#### Relation to the short paper.

The short paper leads with the determinant construction and proves a quadratic tail bound sufficient for the residue criterion. This companion supplies the finite geometry, full two-prime calculation and approximation arguments in Sections <a href="#long269:sec:lcm" data-reference-type="ref" data-reference="long269:sec:lcm">2</a>–<a href="#long269:sec:rank" data-reference-type="ref" data-reference="long269:sec:rank">4</a>. Sections <a href="#long269:sec:blocks" data-reference-type="ref" data-reference="long269:sec:blocks">5</a>–<a href="#long269:sec:escape" data-reference-type="ref" data-reference="long269:sec:escape">7</a> derive the tail coefficients, sharpen the bound, determine the denominator-clearing index and prove the exact growth condition for other window bounds. Section <a href="#long269:sec:evidence" data-reference-type="ref" data-reference="long269:sec:evidence">8</a> contains the finite tests and the twelve-shell denominator certificate. Section <a href="#long269:sec:open" data-reference-type="ref" data-reference="long269:sec:open">9</a> keeps the weighted differences, recodings and value-theorem comparisons separate from the proved residue criterion: none is a premise of that criterion. The tail notation agrees with the short paper and is defined when first used.

<a id="long269:sec:lcm"></a>

# The finite geometry of the running value

The prime-exponent maximum rule for the least common multiple is classical. Applied to all integers up to $`N`$, it gives $`\operatorname{lcm}(1,\ldots,N)=\prod_{t\le N}t^{\lfloor\log_t N\rfloor}`$, where the product is over primes, or equivalently $`\log\operatorname{lcm}(1,\ldots,N)=\psi(N)`$; see Apostol \[apostol1976\] and Montgomery and Vaughan \[montgomeryvaughan2007\]. The same rule applies to the supported prefix below.

The smooth numbers up to $`x`$ are indexed by the exponent triples $`(i,j,k)`$ with $`i\le\lfloor\log_p x\rfloor`$, $`j\le\lfloor\log_q x\rfloor`$, $`k\le\lfloor\log_r x\rfloor`$ and $`p^{i}q^{j}r^{k}\le x`$. The coordinate bounds alone need not describe the prefix: each prime-power factor may be at most $`x`$ while their product exceeds $`x`$. For instance, at $`x=6`$ the factors $`4`$, $`3`$ and $`5`$ satisfy their coordinate bounds, but the corresponding smooth number is $`60`$.

<div id="long269:res:lcm" class="theorem">

**Theorem 2** (the running least common multiple). *Let $`p,q,r`$ be pairwise distinct primes and $`x\ge1`$. Then $`\operatorname{L}(x)=\operatorname{H}(x)`$.*

</div>

<div class="proof">

*Proof.* Every smooth $`n\le x`$ has exponents bounded by the corresponding integer logarithms, so $`n\mid\operatorname{H}(x)`$ and hence $`\operatorname{L}(x)\mid\operatorname{H}(x)`$. Conversely the three pure powers $`p^{\lfloor\log_p x\rfloor}`$, $`q^{\lfloor\log_q x\rfloor}`$ and $`r^{\lfloor\log_r x\rfloor}`$ are themselves smooth numbers not exceeding $`x`$, so each divides $`\operatorname{L}(x)`$, and distinct primes have coprime powers, so their product divides $`\operatorname{L}(x)`$ as well. ◻

</div>

At $`(p,q,r)=(2,3,5)`$ the first ten values are
``` math
\begin{array}{c|cccccccccc}
x&1&2&3&4&5&6&7&8&9&10\\ \hline
\operatorname{L}(x)&1&2&6&12&60&60&60&120&360&360
\end{array}
```
So $`\operatorname{L}(6)=4\cdot3\cdot5=60`$, which exceeds $`6`$: the running value at a smooth cutoff already contains powers of the other two primes that the cutoff itself does not. The kernel must therefore account for all three maximal powers, not just the factorisation of the cutoff. Also $`\operatorname{H}(x)\le x^3`$, since each factor is at most $`x`$. The exponent is the number of generating primes.

Say that $`x`$ and $`y`$ lie in the same *logarithmic cell* when $`\lfloor\log_b x\rfloor=\lfloor\log_b y\rfloor`$ for each of $`b=p,q,r`$. By Theorem <a href="#long269:res:lcm" data-reference-type="ref" data-reference="long269:res:lcm">2</a> the running value depends on $`x`$ only through the three integer logarithms, so it is constant on cells and moves only where one logarithm moves.

<div id="long269:res:cell" class="proposition">

**Proposition 3** (constancy and jump ratios). *If $`x,y\ge1`$ lie in the same logarithmic cell then $`\operatorname{L}(x)=\operatorname{L}(y)`$, and the same holds for the kernel at two smooth points of one cell. If $`\lfloor\log_p y\rfloor=\lfloor\log_p x\rfloor+1`$ while the other two logarithms agree, then $`\operatorname{L}(y)=p\,\operatorname{L}(x)`$, and similarly with $`q`$ or $`r`$ in place of $`p`$.*

</div>

<div class="proof">

*Proof.* Both parts are immediate from Theorem <a href="#long269:res:lcm" data-reference-type="ref" data-reference="long269:res:lcm">2</a>: the height depends on $`x`$ only through the three integer logarithms, and advancing one of them multiplies exactly one factor by its base. ◻

</div>

<span id="long269:res:jump" label="long269:res:jump"></span>

<div id="long269:res:count" class="proposition">

**Proposition 4** (jump count). *Let $`n\ge0`$. The set of the first $`n`$ positive powers of $`p`$, of $`q`$ and of $`r`$ has exactly $`3n`$ elements, and adjoining the common origin $`1`$ gives exactly $`3n+1`$.*

</div>

<div class="proof">

*Proof.* For a fixed prime $`b`$, the powers $`b,b^{2},\ldots,b^{n}`$ are distinct. A common value for two different primes would contradict unique factorisation. Finally $`1`$ is not a positive power of any prime. ◻

</div>

The later tail estimates use two elementary counting facts. Write $`\mathcal B(h_p,h_q,h_r)`$ for the exponent triples with $`i\le h_p`$, $`j\le h_q`$ and $`k\le h_r`$, and $`F(H)`$ for the points of this box whose height equals $`H`$.

<div id="long269:res:fibre" class="proposition">

**Proposition 5** (grouping equal heights). *For every box $`\mathcal B`$,
``` math
\sum_{(i,j,k)\in\mathcal B}\operatorname{K}(i,j,k)=\sum_{H}\#F(H)/H,
```
the outer sum ranging over the heights attained on $`\mathcal B`$.*

</div>

<div class="proof">

*Proof.* Partition $`\mathcal B`$ into the fibres of the height map. On $`F(H)`$ every summand is $`1/H`$, so the fibre contributes $`\#F(H)/H`$. ◻

</div>

Now fix an interval $`[\lambda,\eta)`$ with $`0\le\lambda<\eta`$ and write $`\mathcal S`$ for the exponent triples of $`\mathcal B(h_p,h_q,h_r)`$ whose value $`p^iq^jr^k`$ lies in it. In the next lemma, the exponents $`a,a'`$ are nonnegative integers, and $`w\ge0`$ is the product of the fixed factors.

<div id="long269:res:short" class="lemma">

**Lemma 6** (uniqueness in a short interval). *Let $`b\ge1`$ and $`\eta\le b\,\lambda`$. If $`b^{a}w`$ and $`b^{a'}w`$ both lie in $`[\lambda,\eta)`$ then $`a=a'`$.*

</div>

<div class="proof">

*Proof.* If $`a<a'`$ then $`\eta\le b\,\lambda\le b^{a+1}w\le b^{a'}w<\eta`$, which is impossible; the case $`a>a'`$ is symmetric. ◻

</div>

The short-interval condition says that multiplying by the omitted base moves a point beyond the interval. It holds for $`[L,2L)`$ when that base is at least two. A wider interval need not have this property: $`1`$ and $`2`$ both lie in $`[1,3)`$ and have the same odd part. Thus the ratio bound, not just finiteness of the interval, permits the injective projection.

<div id="long269:res:drop" class="proposition">

**Proposition 7** (counting a shell by two coordinates). *<span id="long269:res:shell" label="long269:res:shell"></span> If $`\eta\le r\,\lambda`$ then $`\#\mathcal S\le(h_p+1)(h_q+1)`$, and if $`\eta\le p\,\lambda`$ then $`\#\mathcal S\le(h_q+1)(h_r+1)`$. If moreover $`\eta\le r\,\lambda`$ and $`h_p\le h_q\le h_r`$ with $`h_p+h_q+h_r=j`$, then $`9\,\#\mathcal S\le(j+3)^{2}`$.*

</div>

<div class="proof">

*Proof.* Suppose $`\eta\le r\,\lambda`$. If two triples of $`\mathcal S`$ agree in their first two coordinates, Lemma <a href="#long269:res:short" data-reference-type="ref" data-reference="long269:res:short">6</a> with $`b=r`$ and $`w=p^{i}q^{j}`$ forces their third coordinates to agree, so the projection forgetting the third coordinate is injective on $`\mathcal S`$ and its image lies in a rectangle with $`(h_p+1)(h_q+1)`$ points. The other case is the same with the first coordinate projected away. Under the sorting hypothesis the two surviving coordinates are the two smallest, so it suffices that $`a\le b\le c`$ with $`a+b+c=j`$ gives $`9(a+1)(b+1)\le(j+3)^{2}`$. From $`a\le b\le c`$ we get $`a+2b\le j`$, so it is enough that $`9(a+1)(b+1)\le(a+2b+3)^{2}`$; writing $`b=a+d`$ with $`d\ge0`$, the difference of the two sides is $`d(3a+4d+3)\ge0`$. ◻

</div>

<a id="long269:sec:two-prime"></a>

# One Hecke–Mahler value controls both two-prime sums

Temporarily let $`P=\{p,q\}`$ with $`p<q`$, and write $`L_{p,q}(t)=p^{\lfloor\log_p t\rfloor}q^{\lfloor\log_q t\rfloor}`$, which is the running least common multiple of the $`\{p,q\}`$-smooth numbers up to $`t`$ by the argument of Theorem <a href="#long269:res:lcm" data-reference-type="ref" data-reference="long269:res:lcm">2</a> with one coordinate omitted. The distinct-height sum retains the initial value $`1`$ and one reciprocal for every later distinct running value, so
``` math
\mathcal D_{\{p,q\}}
 =1+\sum_{t\in\{p,p^2,\ldots\}\cup\{q,q^2,\ldots\}}\frac1{L_{p,q}(t)},
 \qquad
 \mathcal R_{\{p,q\}}=\sum_{i,j\ge0}\frac1{L_{p,q}(p^iq^j)} .
```

<div class="proof">

*Proof of Theorem <a href="#long269:res:lead-two-prime" data-reference-type="ref" data-reference="long269:res:lead-two-prime">1</a>.* Set
``` math
\theta=\frac{\log p}{\log q},\qquad x=\frac1p,\qquad y=\frac1q,\qquad
 m_n=\lfloor n\theta\rfloor,\qquad \delta_n=m_{n+1}-m_n .
```
Here $`0<\theta<1`$, and $`\theta`$ is irrational, since a rational value would give $`p^{b}=q^{a}`$ for positive integers $`a,b`$. Consequently $`\delta_n\in\{0,1\}`$. Put
``` math
A=\sum_{n\ge0}x^ny^{m_n},
 \qquad
 B_\ast=\sum_{n\ge0}\delta_nx^ny^{m_n+1} .
```
The initial value and the positive powers of $`p`$ contribute $`A`$, since $`L_{p,q}(p^n)=p^nq^{m_n}`$. A power of $`q`$ lies strictly between $`p^n`$ and $`p^{n+1}`$ exactly when $`\delta_n=1`$, it is then $`q^{m_n+1}`$, and its post-jump reciprocal is $`x^ny^{m_n+1}`$; so the positive powers of $`q`$ contribute $`B_\ast`$ and $`\mathcal D_{\{p,q\}}=A+B_\ast`$. All these series converge absolutely.

Since $`y^{m_{n+1}}-y^{m_n}=\delta_ny^{m_n}(y-1)`$, an index shift gives $`A-1-xA=x(y-1)B_\ast/y`$, so $`B_\ast=\bigl((p-1)A-p\bigr)/(1-q)`$ and
``` math
\begin{equation}
\label{long269:eq:two-prime-affine}
 \mathcal D_{\{p,q\}}=\frac{(q-p)A+p}{q-1} .
\end{equation}
```
At a smooth point, $`\log_p(p^iq^j)=i+j/\theta`$ and $`\log_q(p^iq^j)=j+i\theta`$, so $`L_{p,q}(p^iq^j)=p^{\,i+\lfloor j/\theta\rfloor}q^{\,j+m_i}`$ and absolute convergence permits the factorisation
``` math
\mathcal R_{\{p,q\}}=A\sum_{j\ge0}y^jx^{\lfloor j/\theta\rfloor}.
```
For $`j\ge1`$, the index $`n=\lfloor j/\theta\rfloor`$ is precisely the one for which $`p^n<q^j<p^{n+1}`$; the inequalities are strict because distinct primes have no common positive power. This interval contains at most one power of $`q`$, since $`p<q`$. Thus $`\delta_n=1`$ and $`j=m_n+1`$. Conversely, every $`n`$ with $`\delta_n=1`$ contains that unique power of $`q`$. The second factor is therefore $`1+B_\ast`$, giving
``` math
\begin{equation}
\label{long269:eq:two-prime-quadratic}
 \mathcal R_{\{p,q\}}
 =\frac{(p+q-1)A-(p-1)A^{2}}{q-1} .
\end{equation}
```

It remains to prove that $`A`$ is transcendental. For the Hecke–Mahler series
``` math
F_\theta(x,y)=\sum_{n\ge1}\sum_{k=1}^{\lfloor n\theta\rfloor}x^ny^k
```
a finite geometric sum gives $`\bigl((1-y)/y\bigr)F_\theta(x,y)=x/(1-x)-(A-1)`$, that is
``` math
\begin{equation}
\label{long269:eq:hecke-mahler-boundary}
 A=\frac1{1-x}-\frac{1-y}{y}F_\theta(x,y).
\end{equation}
```
Bugeaud and Laurent’s Theorem 1.1 states, in particular, that $`F_\theta(\beta,\alpha)`$ is transcendental when $`\theta\in(0,1)`$ is irrational, $`\alpha`$ and $`\beta`$ are nonzero algebraic numbers, $`|\beta|<1`$ and $`|\beta\alpha^\theta|<1`$ \[bugeaudlaurent2023, Theorem 1.1\]; the $`\rho=0`$ case used here goes back to Loxton and van der Poorten \[loxtonvdp1977, Theorem 8, p. 40\]. Take $`(\beta,\alpha)=(x,y)`$: then $`|\beta|=1/p<1`$ and
``` math
|xy^{\theta}|=\frac1p\left(\frac1q\right)^{\log p/\log q}=\frac1{p^{2}}<1 .
```
So $`F_\theta(x,y)`$ is transcendental, and <a href="#long269:eq:hecke-mahler-boundary" data-reference-type="eqref" data-reference="long269:eq:hecke-mahler-boundary">[long269:eq:hecke-mahler-boundary]</a> makes $`A`$ transcendental. The coefficient of $`A`$ in <a href="#long269:eq:two-prime-affine" data-reference-type="eqref" data-reference="long269:eq:two-prime-affine">[long269:eq:two-prime-affine]</a> is $`(q-p)/(q-1)\ne0`$ and the coefficient of $`A^{2}`$ in <a href="#long269:eq:two-prime-quadratic" data-reference-type="eqref" data-reference="long269:eq:two-prime-quadratic">[long269:eq:two-prime-quadratic]</a> is $`-(p-1)/(q-1)\ne0`$, both rational. If either value were algebraic, its identity would exhibit $`A`$ as a root of a nonzero polynomial over the algebraic numbers. ◻

</div>

<span id="long269:res:two-prime-transcendence" label="long269:res:two-prime-transcendence"></span><span id="long269:res:two-prime-repeated-transcendence" label="long269:res:two-prime-repeated-transcendence"></span> A product of two transcendental numbers need not be transcendental. What proves the repeated sum transcendental is its nonconstant quadratic expression in the single value $`A`$, not the factorisation by itself. The value theorem adds no unverified hypothesis in this two-prime case: distinct primes give an irrational slope and the displayed reciprocal arguments satisfy its size conditions. Primality is stronger than the calculation needs. For coprime integers $`1<p<q`$, enumerate the monoid $`\{p^iq^j:i,j\ge0\}`$, not all integers supported on the prime factors of $`pq`$. Unique exponent pairs, the running-LCM product and the irrationality of $`\log p/\log q`$ still hold, so both identities and transcendence conclusions remain valid. For example, this applies to generators $`4,9`$. By contrast, the monoid generated by $`4,8`$ has running LCM $`8`$ at the cutoff $`8`$, not $`4^{\lfloor\log_4 8\rfloor}8^{\lfloor\log_8 8\rfloor}=32`$; its slope is rational as well. The coprime extension was already noted in the supplied forum discussion (Section <a href="#long269:long:history" data-reference-type="ref" data-reference="long269:long:history">10.1</a>).

A third prime introduces an additional floor term that cannot be separated in this way. The next section makes that obstruction precise.

<a id="long269:sec:rank"></a>

# Why the third prime prevents finite separation

With two generators the reciprocal-height kernel is one product of a row function and a column function. With three primes, no finite sum of products separating one exponent from the other two can equal the kernel. The first proposition is algebraic and even allows real generators; the later rank theorem uses distinct primes.

<div id="long269:res:two-prime-rank" class="proposition">

**Proposition 8** (two generators separate). *For real $`p,q>1`$, with $`L_{p,q}(t)=p^{\lfloor\log_p t\rfloor}q^{\lfloor\log_q t\rfloor}`$ as above, and all integers $`i,j\ge0`$, the two-prime kernel $`\operatorname{K}_2(i,j)=1/L_{p,q}(p^iq^j)`$ is the outer product
``` math
\operatorname{K}_2(i,j)
 =\bigl(p^{i}q^{\lfloor\log_q p^{i}\rfloor}\bigr)^{-1}
  \bigl(p^{\lfloor\log_p q^{j}\rfloor}q^{j}\bigr)^{-1},
```
so every two-by-two minor of $`\operatorname{K}_2`$ vanishes.*

</div>

<div class="proof">

*Proof.* Since $`i`$ and $`j`$ are integers, $`\lfloor\log_p(p^iq^j)\rfloor=i+\lfloor\log_p q^{j}\rfloor`$ and $`\lfloor\log_q(p^iq^j)\rfloor=j+\lfloor\log_q p^{i}\rfloor`$. Hence $`L_{p,q}(p^iq^j)`$ is the product of $`p^{i}q^{\lfloor\log_q p^{i}\rfloor}`$, which depends on $`i`$ alone, and $`p^{\lfloor\log_p q^{j}\rfloor}q^{j}`$, which depends on $`j`$ alone. A matrix whose entries are a product of a row function and a column function has vanishing two-by-two minors. For distinct primes $`p,q`$ the product $`L_{p,q}`$ is the running least common multiple by the argument of Theorem <a href="#long269:res:lcm" data-reference-type="ref" data-reference="long269:res:lcm">2</a>. ◻

</div>

At three generators the smallest rectangle already fails to factor. A factorisation $`f(i)g(j)h(k)`$ would force $`\operatorname{K}(0,0,0)\operatorname{K}(1,1,0)=\operatorname{K}(1,0,0)\operatorname{K}(0,1,0)`$.

<div id="long269:res:rank" class="proposition">

**Proposition 9** (non-separability at $`\{2,3,5\}`$). *With $`(p,q,r)=(2,3,5)`$,
``` math
\det\begin{pmatrix}
 \operatorname{K}(0,0,0)&\operatorname{K}(0,1,0)\\
 \operatorname{K}(1,0,0)&\operatorname{K}(1,1,0)
 \end{pmatrix}
 =\det\begin{pmatrix}1&1/6\\1/2&1/60\end{pmatrix}
 =-\frac1{15}\ne0 .
```*

</div>

<div class="proof">

*Proof.* The four values are computed from $`\operatorname{H}(1)=1`$, $`\operatorname{H}(2)=2`$, $`\operatorname{H}(3)=2\cdot3=6`$ and $`\operatorname{H}(6)=4\cdot3\cdot5=60`$, so the determinant is $`1/60-1/12=-1/15`$. ◻

</div>

<div id="long269:res:infinite-rank" class="theorem">

**Theorem 10** (no finite separation of the kernel). *<span id="long269:res:lead-infinite-rank" label="long269:res:lead-infinite-rank"></span> Let $`p,q,r`$ be primes with $`p\ne q`$, $`p\ne r`$ and $`q\ne r`$. For every $`n\ge1`$ there are injective maps $`I,J:\{0,\ldots,n-1\}\to\mathbb{N}`$ such that, for every $`k\ge0`$,
``` math
\det\bigl(\operatorname{K}(I(a),J(b),k)\bigr)_{0\le a,b<n}\ne0 .
```
Consequently, for no finite $`d`$ do there exist rational-valued functions $`f_\ell:\mathbb{N}\to\mathbb{Q}`$ and $`G_\ell:\mathbb{N}^{2}\to\mathbb{Q}`$, $`0\le\ell<d`$, satisfying $`\operatorname{K}(i,j,k)=\sum_{\ell<d}f_\ell(i)G_\ell(j,k)`$ for all $`i,j,k`$.*

</div>

<div class="proof">

*Proof.* Put $`\alpha=\log_r p`$, $`\beta=\log_r q`$, $`x_i=\{i\alpha\}`$ and $`y_j=\{j\beta\}`$. Write $`v_p(N)`$ for the exponent of the prime $`p`$ in the positive integer $`N`$. The three height exponents are
``` math
\begin{split}
 v_p(\operatorname{H}(p^iq^jr^k))&=i+\lfloor j\log_pq+k\log_pr\rfloor,\\
 v_q(\operatorname{H}(p^iq^jr^k))&=j+\lfloor i\log_qp+k\log_qr\rfloor,\\
 v_r(\operatorname{H}(p^iq^jr^k))&=k+\lfloor i\alpha\rfloor+\lfloor j\beta\rfloor+
   \lfloor x_i+y_j\rfloor .
 \end{split}
```
Every term except the last floor depends on $`i`$ and $`k`$ alone or on $`j`$ and $`k`$ alone, so with positive rational $`R_i(k)`$ and $`C_j(k)`$,
``` math
\begin{equation}
\label{long269:eq:carry-factorisation}
 \operatorname{K}(i,j,k)=R_i(k)\,C_j(k)\,t^{\lfloor x_i+y_j\rfloor},
 \qquad t=r^{-1} .
\end{equation}
```
The remaining matrix is independent of $`k`$, and $`x_i+y_j\in[0,2)`$, so its entries are $`1`$ and $`t`$.

Each of $`\alpha`$ and $`\beta`$ is irrational, since a rational value would give an equality of positive powers of distinct primes, so each fractional-part orbit is dense in $`[0,1]`$ and each is injective. The row and column indices are chosen independently, so no density theorem for a single orbit of pairs is required. First choose indices with $`0<x_{I(0)}<\cdots<x_{I(n-1)}<1`$. We want the columns to cross their thresholds at successive selected rows, so that consecutive row differences will leave a triangular matrix. Write $`s_b=1-y_{J(b)}`$, and use density of the second orbit to choose
``` math
s_0\in(0,x_{I(0)}),\qquad
 s_b\in(x_{I(b-1)},x_{I(b)})\quad(1\le b<n).
```
The intervals are disjoint, so the $`J(b)`$ are distinct. Their strict endpoints ensure that no selected entry lies on a threshold, and $`x_{I(a)}+y_{J(b)}\ge1`$ holds exactly when $`b\le a`$. Dividing row $`a`$ by $`R_{I(a)}(k)`$ and column $`b`$ by $`C_{J(b)}(k)`$ therefore leaves
``` math
C_n(t)=\begin{pmatrix}
 t&1&1&\cdots&1\\
 t&t&1&\cdots&1\\
 \vdots&\vdots&\ddots&\ddots&\vdots\\
 t&t&\cdots&t&1\\
 t&t&\cdots&t&t
 \end{pmatrix},
 \qquad
 \det C_n(t)=t(t-1)^{n-1}\ne0 ,
```
the determinant following by subtracting from each row its predecessor, working upwards from the last. Before the division, the determinant equals
``` math
\det C_n(t)\prod_{a<n}R_{I(a)}(k)\prod_{b<n}C_{J(b)}(k),
```
which is nonzero for every $`k`$; this also explains why the same indices work in every layer.

For the last assertion, suppose that a representation with $`d`$ summands exists and fix $`k`$. On the selected rows $`I(0),\ldots,I(d)`$ and columns $`J(0),\ldots,J(d)`$ the resulting matrix factors as
``` math
(f_\ell(I(a)))_{0\le a\le d,\,\ell<d}
 (G_\ell(J(b),k))_{\ell<d,\,0\le b\le d}.
```
It has rank at most $`d`$ and hence zero determinant, contradicting the nonzero minor of order $`d+1`$. ◻

</div>

Index selection is essential. In the $`k=0`$ layer of the $`\{2,3,5\}`$ kernel, the leading $`4\times4`$ minor is singular because $`\operatorname{K}(3,j,0)=\operatorname{K}(0,j,0)/120`$ for $`0\le j\le3`$. This is not a proportionality of the full rows: at the next column,
``` math
\operatorname{K}(3,4,0)-\frac{\operatorname{K}(0,4,0)}{120}=-\frac1{19440000}.
```
A singular leading minor therefore does not settle the rank.

In each fixed layer $`k`$, the same threshold description determines every finite sampled rank, rather than only producing one nonsingular minor.

<div id="long269:res:finite-cut-rank" class="proposition">

**Proposition 11** (rank of threshold columns). *Let $`m\ge1`$ and let $`c`$ lie in a field with $`c\ne0,1`$. For $`0\le h\le m`$, let $`v_h`$ be the length-$`m`$ column whose first $`h`$ entries are $`1`$ and whose remaining entries are $`c`$. If the distinct columns of a matrix are the $`v_h`$ with $`h`$ in a nonempty set $`E\subseteq\{0,\ldots,m\}`$, then its rank is
``` math
|E|-\mathbf 1_{\{0,m\}\subseteq E}.
```*

</div>

<div class="proof">

*Proof.* Write $`E=\{h_1<\cdots<h_s\}`$. The $`s-1`$ consecutive differences are
``` math
v_{h_{a+1}}-v_{h_a}
   =(1-c)\mathbf 1_{\{h_a,\ldots,h_{a+1}-1\}},
```
so they are linearly independent because their nonempty supports are disjoint. If $`h_1>0`$ or $`h_s<m`$, those supports miss a coordinate on which $`v_{h_1}`$ is nonzero, and adjoining $`v_{h_1}`$ gives rank $`s`$. If $`h_1=0`$ and $`h_s=m`$, the differences sum to $`(1-c)\mathbf 1`$ while $`v_0=c\mathbf 1`$, so $`v_0`$ is already in their span and the rank is $`s-1`$. ◻

</div>

The restrictions $`c\ne0,1`$ exclude the zero column at $`c=0`$ and the collapse of all columns at $`c=1`$. They hold automatically at $`c=1/r`$ over $`\mathbb Q`$. To apply the proposition, fix $`k`$ and sort the chosen row phases $`x_i`$. Each normalised column is a threshold column $`v_h`$, where $`h`$ is the number of sampled phases strictly below $`1-y_j`$. Repeated threshold positions give proportional columns before column normalisation. The row and column factors in <a href="#long269:eq:carry-factorisation" data-reference-type="eqref" data-reference="long269:eq:carry-factorisation">[long269:eq:carry-factorisation]</a> are nonzero, so the formula gives the exact rank of every nonempty rectangular sample within this layer, independently of $`k`$. Repeated rows or columns do not change rank.

This also gives an exact algorithm. Order the sampled rows by the rational numbers $`p^i/r^{\lfloor\log_r p^i\rfloor}`$. For column $`j`$, count those strictly below $`r^{\lfloor\log_r q^j\rfloor+1}/q^j`$, then apply the endpoint correction to the set of resulting counts. Indeed, raising $`x_i<1-y_j`$ to base $`r`$ gives exactly this rational comparison, and $`x_i+y_j=1`$ belongs to the $`c`$ side of the threshold. The integer logarithms are found by comparing powers, so the whole calculation uses integer arithmetic rather than numerical logarithms.

The fixed-layer restriction is essential. With $`(p,q,r)=(2,3,5)`$, rows $`i=0,1`$ and columns indexed by $`(j,k)=(0,0),(0,1)`$ give
``` math
\begin{pmatrix}
  \operatorname{K}(0,0,0)&\operatorname{K}(0,0,1)\\
  \operatorname{K}(1,0,0)&\operatorname{K}(1,0,1)
 \end{pmatrix}
 =\begin{pmatrix}1&1/60\\1/2&1/360\end{pmatrix},
 \qquad \det=-\frac1{180}.
```
Both columns have the same phase $`y_0=0`$, yet their rank is $`2`$, not $`1`$. When $`k`$ varies with the column, the row factor also varies with that column and cannot be removed by one common diagonal rescaling. The threshold formula is not a rank formula for such mixed-layer samples.

<a id="scope-of-the-rank-theorem."></a>

#### Scope of the rank theorem.

Fan’s comment of 26 June 2026 \[fan2026comment\] notes that the two-prime argument does not seem to generalise immediately to $`|P|\ge3`$. The theorem above gives a precise obstruction: no finite exact separation of the stated form exists. The same finite-dimensional proof works for real or complex factors, without continuity or boundedness assumptions. This does not exclude approximation or imply irrationality or transcendence of the sum. The threshold construction needs $`\log_r p`$ and $`\log_r q`$ irrational, but not $`p\ne q`$. The latter condition is needed for the three-prime running-LCM interpretation, not for the two independent dense orbits.

<a id="the-exact-uniform-approximation-error"></a>

## The exact uniform approximation error

Exact infinite rank does not by itself give a lower bound on approximation error. Here such a bound follows because any two distinct columns of the normalised matrix have a fixed positive distance. The matrix is
``` math
\begin{equation}
\label{long269:eq:carry-matrix}
 C(i,j)=t^{\lfloor x_i+y_j\rfloor},
 \qquad
 x_i=\{i\log_r p\},\quad y_j=\{j\log_r q\},\quad t=r^{-1},
\end{equation}
```
which is the factor left in <a href="#long269:eq:carry-factorisation" data-reference-type="eqref" data-reference="long269:eq:carry-factorisation">[long269:eq:carry-factorisation]</a> after the row and column factors are divided out. Say that a real matrix $`A`$ on $`\mathbb{N}\times\mathbb{N}`$ has *finite separated rank* when all of its columns lie in one finite-dimensional space of real sequences, equivalently when $`A(i,j)=\sum_{\ell<d}f_\ell(i)g_\ell(j)`$ for some finite $`d`$ and some sequences $`f_\ell,g_\ell`$, with no continuity or boundedness assumed. This is ordinary finite column rank; a basis of the column space supplies a separated expression.

<div id="long269:res:uniform-rank" class="theorem">

**Theorem 12** (distance from matrices of finite separated rank). *Let $`p,q,r`$ be pairwise distinct primes and let $`C`$ be as in <a href="#long269:eq:carry-matrix" data-reference-type="eqref" data-reference="long269:eq:carry-matrix">[long269:eq:carry-matrix]</a>. Then
``` math
\inf_{A}\ \sup_{i,j\ge0}\ |C(i,j)-A(i,j)|=\frac{1-t}{2}=\frac{r-1}{2r},
```
the infimum being over all matrices $`A`$ of finite separated rank, and it is attained by the constant matrix of value $`(1+t)/2`$.*

</div>

<div class="proof">

*Proof.* Every entry of $`C`$ lies in $`\{1,t\}`$, and $`C(i,j)=t`$ exactly when $`x_i+y_j\ge1`$. Fix $`j\ne k`$. The numbers $`y_j`$ are pairwise distinct, since $`\log_r q`$ is irrational, so we may assume $`y_j<y_k`$, and then $`0\le1-y_k<1-y_j\le1`$. Density of the orbit $`(x_i)`$ in $`(0,1)`$ supplies an index $`i`$ with $`1-y_k<x_i<1-y_j`$, and at that row the two columns carry the entries $`t`$ and $`1`$. Hence any two distinct columns of $`C`$ are at sup-distance exactly $`1-t`$.

Let $`A`$ have finite separated rank and put $`\varepsilon=\sup_{i,j}|C(i,j)-A(i,j)|`$. Suppose $`\varepsilon<(1-t)/2`$. Each column $`A_j`$ then satisfies $`\|A_j\|_\infty\le1+\varepsilon`$. Let $`V`$ be the span of these columns. It is finite-dimensional by hypothesis and consists of bounded sequences, so the supremum norm is defined on $`V`$. No boundedness of the individual separated factors is needed. By the triangle inequality, distinct columns satisfy
``` math
\|A_j-A_k\|_\infty\ \ge\ \|C_j-C_k\|_\infty-2\varepsilon
 \ =\ 1-t-2\varepsilon\ >\ 0 .
```
The columns would be an infinite family in the bounded ball of radius $`1+\varepsilon`$ in $`V`$, separated by the fixed positive distance $`1-t-2\varepsilon`$. This contradicts total boundedness of bounded subsets of a finite-dimensional normed space. Hence $`\varepsilon\ge(1-t)/2`$ for every $`A`$ of finite separated rank.

For sharpness take $`A(i,j)=(1+t)/2`$, which has separated rank one; every entry of $`C`$ is at distance exactly $`(1-t)/2`$ from it. ◻

</div>

The lower bound concerns the entire normalised matrix, not each finite restriction. For example, at $`t=1/5`$ the matrices
``` math
T=\begin{pmatrix}1/5&1\\1/5&1/5\end{pmatrix},\qquad
 A=\begin{pmatrix}3/10&9/10\\1/10&3/10\end{pmatrix}
```
satisfy $`\det A=0`$ and $`\|T-A\|_{\max}=1/10<2/5`$. Here $`\|\cdot\|_{\max}`$ is the largest absolute entry. This finite example has no bearing on the infinite family of separated columns used in the proof.

For the original kernel, the decaying row and column factors instead allow approximation in the summation norm. Let $`K^{(N)}(i,j,k)=\operatorname{K}(i,j,k)`$ for $`i<N`$ and $`K^{(N)}(i,j,k)=0`$ otherwise. This is a sum of at most $`N`$ terms separated between $`i`$ and $`(j,k)`$. Since $`\operatorname{H}(x)>x^3/(pqr)`$ for $`x\ge1`$, geometric summation gives
``` math
\begin{equation}
\label{long269:eq:l1-finite-rank-approximation}
 \sum_{i,j,k\ge0}|\operatorname{K}(i,j,k)-K^{(N)}(i,j,k)|
 \le
 \frac{pqr\,p^{-3N}}
 {(1-p^{-3})(1-q^{-3})(1-r^{-3})}.
\end{equation}
```
The same bound controls the supremum of the entrywise errors, so these finite separated-rank approximants converge both in $`\ell^1`$ and uniformly to the original kernel. The positive uniform lower bound in Theorem <a href="#long269:res:uniform-rank" data-reference-type="ref" data-reference="long269:res:uniform-rank">12</a> belongs to the rescaled matrix. Diagonal rescaling preserves exact rank, but the rescaling factors here are unbounded and do not preserve uniform error estimates. Neither the rank obstruction nor these approximation bounds decide whether the scalar sum is rational.

<a id="long269:sec:blocks"></a>

# The recurrence for tails between powers of two

For the rest of the record set $`P=\{2,3,5\}`$ and $`S=\mathcal R_P`$. Write $`P_a=\operatorname{H}(2^a)`$ and $`h_a=P_a/2`$. Here $`P_a`$ is a boundary height, not a set of primes; $`h_0=1/2`$, while $`h_a`$ is a positive integer for $`a\ge1`$. At a dyadic endpoint the power of $`2`$ is exact, while the maximal powers of $`3`$ and $`5`$ exceed $`2^a/3`$ and $`2^a/5`$. Hence
``` math
\frac{8^a}{15}<P_a\le8^a\qquad(a\ge0).
```
These bounds will control both the tail scale and the growth of a recurrence error. Group the terms between consecutive powers of two and define
``` math
\begin{equation}
\label{long269:eq:actual-tail}
 s_a=\sum_{\substack{i,j,k\ge0\\ 2^{a}\le2^{i}3^{j}5^{k}<2^{a+1}}}
       \frac1{\operatorname{H}(2^{i}3^{j}5^{k})},
 \qquad
 T_a=\sum_{j\ge a}s_j,
 \qquad
 X_a=h_aT_a .
\end{equation}
```

The factor $`1/2`$ in $`h_a`$ comes from the strict cutoff. For $`a\ge1`$, every height $`\operatorname{H}(x)`$ with $`x<2^a`$ divides $`P_a/2`$: the exponent of $`2`$ is at most $`a-1`$, and the other exponents are at most their boundary values. We will use this to clear the finite prefix in Lemma <a href="#long269:res:all-scale-lattice" data-reference-type="ref" data-reference="long269:res:all-scale-lattice">18</a>.

The jumps after $`2^a`$ and up to $`2^{a+1}`$ consist of any powers of $`3`$ or $`5`$ strictly inside that interval, followed by the factor $`2`$ at its right endpoint. There is at most one power of each odd prime: successive powers have ratio greater than two. Let $`I_a`$ list the pairs $`(p,e)`$ with $`p\in\{3,5\}`$ and $`2^a<p^e<2^{a+1}`$, ordered by the value $`p^e`$.

<div id="long269:res:dyadic-alphabet" class="proposition">

**Proposition 13** (four possible bases). *For every $`a`$,
``` math
\begin{equation}
\label{long269:eq:dyadic-alphabet}
 b_a=\frac{P_{a+1}}{P_a}=2\prod_{(p,e)\in I_a}p\in\{2,6,10,30\},
 \qquad\text{so}\qquad 2\le b_a\le30 .
\end{equation}
```*

</div>

<div class="proof">

*Proof.* A power of $`3`$ may occur and a power of $`5`$ may occur, each at most once. The resulting factor is $`2`$, $`2\cdot3`$, $`2\cdot5`$ or $`2\cdot3\cdot5`$. ◻

</div>

The coefficient subtracted at step $`a`$ is the shell mass with its denominators cleared:
``` math
m_a=h_{a+1}s_a
 =\sum_{\substack{x\text{ smooth}\\2^a\le x<2^{a+1}}}
       \frac{P_{a+1}}{2\operatorname{H}(x)}.
```
Each summand is an integer, by the same strict-cutoff argument. For example, $`[2,4)`$ contains just $`2`$ and $`3`$, so $`m_1=6(1/2+1/6)=4`$ and $`X_2=6X_1-4`$. The first four pairs $`(b_a,m_a)`$, starting at $`a=1`$, are $`(6,4)`$, $`(10,7)`$, $`(6,7)`$ and $`(30,65)`$. In particular $`m_3>b_3`$: these coefficients are not positional digits.

The shell $`[16,32)`$ shows why the order of the jumps matters. Its internal jumps are $`25`$ and $`27`$, in that order. The four smooth numbers $`16,18,20,24`$ precede both jumps and have weight $`15`$; $`25`$ precedes only the jump at $`27`$ and has weight $`3`$; and $`27,30`$ have weight $`1`$. Thus
``` math
m_4=4\cdot15+1\cdot3+2\cdot1
     =7+(5-1)\cdot4\cdot3+(3-1)\cdot5=65.
```
The second expression starts with the seven points and adds the corrections before $`25`$ and $`27`$. It is this form that extends to every shell.

To compute $`m_a`$ in general, count the smooth numbers before each prime-power jump. Let $`\mathcal N(t)`$ be the number of positive $`\{2,3,5\}`$-smooth integers strictly below $`t`$. First give every point in $`[2^a,2^{a+1})`$ weight one. At an internal jump $`p^e`$, the points before that jump need an additional weight $`p-1`$, multiplied by the prime factors at all later internal jumps. Thus, for $`a\ge1`$,
``` math
\begin{equation}
\label{long269:eq:actual-digit}
\begin{aligned}
 m_a&=\mathcal N(2^{a+1})-\mathcal N(2^a)\\
 &\quad+\sum_{(p,e)\in I_a}(p-1)
       \bigl(\mathcal N(p^e)-\mathcal N(2^a)\bigr)
       \prod_{\substack{(q,f)\in I_a\\p^e<q^f}}q,\\
 m_0&=1.
\end{aligned}
\end{equation}
```
The first difference counts the whole shell; each later difference counts its points strictly before the indicated jump. The proof below justifies these weights, establishes convergence and derives the tail identities.

<div id="long269:res:actual-orbit" class="theorem">

**Theorem 14** (the tail recurrence). *The shell masses are summable and $`S=\sum_{a\ge0}s_a`$. For every $`a\ge0`$,
``` math
\begin{equation}
\label{long269:eq:shell-digit-identity}
 m_a=h_{a+1}s_a\in\mathbb{N}_{>0},
 \qquad
 X_{a+1}=b_aX_a-m_a,
 \qquad
 X_a=\sum_{j\ge a}\frac{m_j}{b_ab_{a+1}\cdots b_j} .
\end{equation}
```*

</div>

<div class="proof">

*Proof.* Every exponent of $`3`$ or $`5`$ in the $`a`$th shell is at most $`a`$, and for each such pair Lemma <a href="#long269:res:short" data-reference-type="ref" data-reference="long269:res:short">6</a> leaves at most one exponent of $`2`$ placing the point in $`[2^{a},2^{a+1})`$. Each height is at least $`2^{a}`$ and the shell contains $`2^{a}`$, so $`0<s_a\le(a+1)^{2}2^{-a}`$. The majorant is summable, which justifies every tail splitting below, and unique prime factorisation identifies $`\sum_a s_a`$ with the original repeated series.

Write the internal jumps as $`t_\ell=p_\ell^{e_\ell}`$, $`1\le\ell\le v`$, and set $`t_0=2^{a}`$, $`t_{v+1}=2^{a+1}`$ and $`n_\ell=\mathcal N(t_\ell)`$. On $`[t_\ell,t_{\ell+1})`$ the height is $`P_a\prod_{u\le\ell}p_u`$, and the terminal jump has factor two, so
``` math
h_{a+1}s_a
 =\sum_{\ell=0}^{v}(n_{\ell+1}-n_\ell)\prod_{u>\ell}p_u
 =n_{v+1}-n_0+\sum_{\ell=1}^{v}(p_\ell-1)
        \Bigl(\prod_{u>\ell}p_u\Bigr)(n_\ell-n_0).
```
The second equality is finite summation by parts and is exactly <a href="#long269:eq:actual-digit" data-reference-type="eqref" data-reference="long269:eq:actual-digit">[long269:eq:actual-digit]</a>. The count itself is finite: for $`p=2,3,5`$, with $`q,r`$ the other primes, counting by the exponent of $`p`$ gives
``` math
\mathcal N(p^e)=\sum_{u=1}^e\#\{(i,j)\in\mathbb{N}^2:q^ir^j<p^u\}.
```
At $`a=0`$ the shell is the single point $`1`$, giving $`m_0=1`$. Positivity follows from $`s_a>0`$. Splitting $`T_a=s_a+T_{a+1}`$ and multiplying by $`h_a`$ gives the recurrence, and $`b_a\cdots b_j=P_{j+1}/P_a`$ with $`m_j=h_{j+1}s_j`$ gives $`m_j/(b_a\cdots b_j)=h_as_j`$, whose summation is the last identity. ◻

</div>

For estimates, it is useful to count by the odd part $`3^j5^k`$ instead. Each such part below $`2^{a+1}`$ has exactly one power-of-two multiple in $`[2^a,2^{a+1})`$. This turns the same numerator into a two-dimensional count, with weights determined by the remaining odd-prime jumps.

<div id="long269:res:literal-triangle" class="lemma">

**Lemma 15** (the shell numerator as a weighted lattice count). *Put $`\lambda_3=\log_2 3`$, $`\lambda_5=\log_2 5`$ and $`\theta_p=1/\lambda_p`$ for $`p=3,5`$. For $`j,k\ge0`$ write $`w_{j,k}=j\lambda_3+k\lambda_5`$ and $`t_{j,k}=\{w_{j,k}\}`$. The shell numerator is
``` math
m_a=\sum_{\substack{j,k\ge0\\w_{j,k}<a+1}}
 3^{\lfloor(a+1)\theta_3\rfloor-\lfloor(a+t_{j,k})\theta_3\rfloor}
 5^{\lfloor(a+1)\theta_5\rfloor-\lfloor(a+t_{j,k})\theta_5\rfloor}.
```
Every summand is in $`\{1,3,5,15\}`$. In particular, for $`a\ge0`$,
``` math
\bigl(\lfloor a/(2\lambda_3)\rfloor+1\bigr)
 \bigl(\lfloor a/(2\lambda_5)\rfloor+1\bigr)
 \le m_a\le15(a+1)^2.
```
Thus $`m_a=\Theta((a+1)^2)`$ and the numerator sequence is unbounded. These are integer numerators, not positional digits restricted to $`\{0,\ldots,b_a-1\}`$.*

</div>

<div class="proof">

*Proof.* For each pair with $`w_{j,k}<a+1`$, exactly one exponent $`i=a-\lfloor w_{j,k}\rfloor\ge0`$ puts $`2^i3^j5^k=2^{a+t_{j,k}}`$ in $`[2^a,2^{a+1})`$. This pairs each point of the triangle with exactly one smooth integer in the shell. Substituting in $`P_{a+1}/(2\operatorname{H}(2^i3^j5^k))`$ cancels the power of $`2`$ and gives the displayed weight. Each remaining floor increment is zero or one since $`0<\theta_p<1`$. Finally $`\lambda_3,\lambda_5>1`$ implies $`j,k\le a`$ for every summation pair, proving the upper bound. For the lower bound, restrict to $`0\le j\le\lfloor a/(2\lambda_3)\rfloor`$ and $`0\le k\le\lfloor a/(2\lambda_5)\rfloor`$. Then $`w_{j,k}\le a`$ and each weight is at least one. ◻

</div>

The formula shows two sources of variation in $`m_a`$: points enter the triangle as $`a`$ increases, and their weights depend on two floors. Quadratic growth does not make this count a quadratic polynomial.

The recurrence also restricts how persistently a nonintegral tail can approach the integers. The following alternative uses only the integer coefficients and the bounds $`2\le b_a\le30`$.

<div id="long269:res:actual-dichotomy" class="proposition">

**Proposition 16** (integer tails or repeated separation from the integers). *For every integer $`B\ge1`$, either $`BX_a\in\mathbb{Z}`$ for some $`a\ge0`$ and every later $`a`$, or for every $`a_0`$ there is $`a\ge a_0`$ with $`|BX_a-z|\ge1/31`$ for every $`z\in\mathbb{Z}`$.*

</div>

<div class="proof">

*Proof.* If the second alternative fails, there are $`A`$ and integers $`z_a`$ such that $`e_a=BX_a-z_a`$ satisfies $`|e_a|<1/31`$ for all $`a\ge A`$. The recurrence gives $`z_{a+1}-b_az_a+Bm_a=b_ae_a-e_{a+1}`$. Since $`Bm_a`$ is integral, the left side is an integer; the right side has absolute value less than $`(30+1)/31=1`$. Both sides therefore vanish, so $`e_{a+1}=b_ae_a`$. Hence $`|e_{A+k}|\ge2^k|e_A|`$ for every $`k`$, whereas $`|e_{A+k}|<1/31`$. Thus $`e_A=0`$, and the integer recurrence propagates integrality from $`BX_A`$ to every later $`BX_a`$. ◻

</div>

The proposition does not determine which alternative holds for the tails of $`S`$. For comparison, Erdős–Taylor \[erdostaylor1957, Theorem 1, p. 600\] prove a countability statement for increasing integer sequences with bounded successive ratios; Fan \[fan2026strongly, Lemma 3.1, arXiv v1\] allows an unbounded, not necessarily increasing sequence, still with a uniform upper bound on successive ratios. For our divisibility chain the same error argument identifies the entire exceptional set, not just its cardinality. For each fixed integer $`B\ge1`$,
``` math
\bigl\{\xi\in\mathbb{R}:\operatorname{dist}(Bh_a\xi,\mathbb{Z})\longrightarrow0\bigr\}
 =\frac1B\mathbb{Z}[1/30],
 \qquad
 \mathbb{Z}[1/30]=\{m/30^t:m\in\mathbb{Z},\ t\in\mathbb{N}\}.
```
Indeed, apply the proof above to $`Bh_a\xi`$, whose successive terms are related by multiplication by $`b_a`$. Convergence of the distances forces $`Bh_A\xi\in\mathbb{Z}`$ for some $`A\ge1`$. Since $`h_A`$ has no prime factors outside $`2,3,5`$, this gives membership in the right-hand side. Conversely, every fixed product of powers of $`2,3,5`$ eventually divides $`h_a`$, so every member of the right-hand side gives integral values for all large $`a`$.

Separation from the integers for one multiplier does not prove irrationality. For example, $`\xi=1/7`$ satisfies $`\operatorname{dist}(h_a\xi,\mathbb{Z})\ge1/7`$ for every $`a\ge1`$, because $`7\nmid h_a`$; with $`B=7`$ the values $`Bh_a\xi`$ are all integers. For $`S`$, the denominator clearing in Theorem <a href="#long269:res:actual-cancellation" data-reference-type="ref" data-reference="long269:res:actual-cancellation">19</a> below shows which multipliers matter: the integral alternative for the actual tails must be excluded for every $`B\ge1`$ coprime to $`30`$, not merely for $`B=1`$.

<a id="long269:sec:actual-orbit"></a>

# Bounding the tails and clearing a rational denominator

We first bound the tail without assuming rationality. The sum of the three height exponents will index the height cells. Put
``` math
n_a=a+\lfloor\log_3(2^{a})\rfloor+\lfloor\log_5(2^{a})\rfloor,
 \qquad
 Q(n)=\frac{n^{2}+8n+18}{9},
```
so $`n_a`$ is the sum of the three height exponents at $`2^{a}`$.

<div id="long269:res:actual-tail-bound" class="theorem">

**Theorem 17** (a quadratic upper bound). *For every $`a\ge0`$, $`0<X_a\le Q(n_a)`$.*

</div>

<div class="proof">

*Proof.* Partition the smooth integers $`x\ge2^{a}`$ by their height vector
``` math
(A,B,C)=(\lfloor\log_2x\rfloor,\lfloor\log_3x\rfloor,\lfloor\log_5x\rfloor).
```
The cell of a vector is the interval $`[\lambda,\eta)`$, where
``` math
\lambda=\max(2^{A},3^{B},5^{C}),\qquad
 \eta=\min(2^{A+1},3^{B+1},5^{C+1}).
```
Thus $`\eta\le2^{A+1}\le2\lambda`$. By Lemma <a href="#long269:res:short" data-reference-type="ref" data-reference="long269:res:short">6</a>, fixing the exponents of $`3`$ and $`5`$ leaves at most one exponent of $`2`$. Since $`A\ge B\ge C`$, the cell contains at most
``` math
(B+1)(C+1)\le\frac{(A+B+C+3)^{2}}{9}
```
smooth points: writing $`u=B+1\ge v=C+1`$ and using $`A+1\ge u`$, the difference $`(2u+v)^{2}-9uv=(u-v)(4u-v)`$ is nonnegative. Unique factorisation identifies these exponent triples with distinct smooth integers.

As the cutoff increases all three height exponents are nondecreasing, so two nonempty cells with the same exponent sum are the same cell, and there is at most one nonempty cell with each exponent sum. Every cell above $`2^a`$ has exponent sum at least $`n_a`$, and a cell with sum $`n_a+k`$ has height at least $`P_a2^k`$, since each of the $`k`$ extra prime factors is at least $`2`$. Nonnegative summation over exponent sums, allowing empty cells, gives
``` math
X_a\le\frac1{18}\sum_{k\ge0}\frac{(n_a+k+3)^{2}}{2^{k}}
      =\frac{n_a^{2}+8n_a+18}{9},
```
the evaluation using the geometric moments $`\sum2^{-k}=2`$, $`\sum k2^{-k}=2`$ and $`\sum k^{2}2^{-k}=6`$. Positivity follows from the shell at $`2^{a}`$. ◻

</div>

Increasing the exponent sum by one costs a factor of at least two in the denominator, whereas the number of points in a cell grows at most quadratically. Summing those geometric contributions gives the bound. The argument uses unique factorisation and the projection count, not an asymptotic estimate for smooth numbers or a Hecke–Mahler theorem.

The quadratic order is also necessary. The positive next tail and the recurrence give
``` math
X_a=\frac{m_a+X_{a+1}}{b_a}>\frac{m_a}{b_a}\ge\frac{m_a}{30}.
```
The lower bound of Lemma <a href="#long269:res:literal-triangle" data-reference-type="ref" data-reference="long269:res:literal-triangle">15</a>, together with $`n_a\le3a`$, therefore gives $`X_a=\Theta((a+1)^2)`$. In particular, the normalised tails are not uniformly bounded. This order estimate does not assert an asymptotic constant or optimality of $`Q`$.

The bound is used at the endpoint of a window, where the natural index is the positive prime-power jump count strictly below the cutoff. Put
``` math
\begin{equation}
\label{long269:eq:endpoint-index}
 j_a=\#\{p^{e}<2^{a}:p\in\{2,3,5\},\ e\ge1\}=n_a-1\qquad(a\ge1),
\end{equation}
```
the equality holding for $`a\ge1`$ because the powers of $`2`$ below $`2^{a}`$ number $`a-1`$ while the powers of $`3`$ and of $`5`$ below $`2^{a}`$ number $`\lfloor\log_3 2^{a}\rfloor`$ and $`\lfloor\log_5 2^{a}\rfloor`$; at $`a=0`$ the count is $`j_0=0`$ and $`n_0-1=-1`$. Substituting $`n_a=j_a+1`$ into $`Q`$ gives the integer bound used throughout the rest of the note:
``` math
\begin{equation}
\label{long269:eq:actual-bound}
 K(B,a)=\bigl\lfloor B\,Q(n_a)\bigr\rfloor,
 \qquad
 K(B,a)=\left\lfloor\frac{B(j_a^{2}+10j_a+27)}9\right\rfloor\quad(a\ge1).
\end{equation}
```
The cutoff in <a href="#long269:eq:endpoint-index" data-reference-type="eqref" data-reference="long269:eq:endpoint-index">[long269:eq:endpoint-index]</a> is $`2^{a}`$ and it is strict. The symbol $`K(B,a)`$ bounds an *integral* quantity $`BX_a`$: from $`BX_a\le BQ(n_a)`$ one may take the floor only after integrality has been established. We do not assert $`BX_a\le K(B,a)`$ for arbitrary real tails.

<div id="long269:res:all-scale-lattice" class="lemma">

**Lemma 18** (finite denominator clearing). *For all integers $`0\le u\le b`$ the window mass $`h_b\sum_{a=u}^{b-1}s_a`$ is a natural number. If $`S=N/D`$ with $`N\in\mathbb{Z}`$ and $`D\in\mathbb{N}_{>0}`$, then $`DX_a\in\mathbb{Z}`$ for every $`a\ge1`$, and there are indices $`1\le i<j\le D+1`$ for which $`X_i-X_j\in\mathbb{Z}`$.*

</div>

<div class="proof">

*Proof.* An empty window has mass zero. Otherwise $`b\ge1`$, and every integer $`x<2^{b}`$ has $`2`$-height exponent at most $`b-1`$ while its other height exponents are at most those at $`2^{b}`$, so $`\operatorname{H}(x)\mid P_b/2=h_b`$ and every term of the finite window clears at $`h_b`$. Since $`h_a\sum_{u<a}s_u`$ is an integer,
``` math
DX_a=h_aN-Dh_a\sum_{u<a}s_u\in\mathbb{Z}.
```
Among $`D+1`$ of these integers two share a residue modulo $`D`$, and the corresponding states differ by an integer. ◻

</div>

The strict upper endpoint is what permits division by two. A cutoff including $`2^b`$ would not clear its term at the normaliser $`h_b=P_b/2`$.

<div id="long269:res:actual-cancellation" class="theorem">

**Theorem 19** (rationality gives positive integer tails). *<span id="long269:res:lead-carry-bridge" label="long269:res:lead-carry-bridge"></span> <span id="long269:res:actual-carry-bound" label="long269:res:actual-carry-bound"></span><span id="long269:res:denominator-reduction" label="long269:res:denominator-reduction"></span> Suppose $`S=N/D`$ with $`N\in\mathbb{Z}`$, $`D\in\mathbb{N}_{>0}`$, and write
``` math
D=2^{u}3^{v}5^{w}B,\qquad u,v,w\in\mathbb{N},\quad B\in\mathbb{N}_{>0},\quad\gcd(B,30)=1,
 \qquad a_D=u+1+2v+3w .
```
Then for every $`a\ge a_D`$ the number $`d_a=BX_a`$ is a positive integer and
``` math
d_{a+1}=b_ad_a-Bm_a,\qquad 1\le d_a\le K(B,a)\le90B(a+1)^{2} .
```*

</div>

<div class="proof">

*Proof.* Let $`M=2^{u}3^{v}5^{w}`$. For $`a\ge a_D`$ we have $`2^{a}\ge2^{u+1}`$, $`2^{a}\ge3^{v}`$ and $`2^{a}\ge5^{w}`$, using $`3<2^{2}`$ and $`5<2^{3}`$; hence $`M\mid h_a`$. By Lemma <a href="#long269:res:all-scale-lattice" data-reference-type="ref" data-reference="long269:res:all-scale-lattice">18</a>, $`X_a`$ differs from $`h_aN/D`$ by an integer. Since $`M\mid h_a`$ and $`D=MB`$, multiplying by $`B`$ shows that $`BX_a`$ is an integer. Positivity and the recurrence come from <a href="#long269:eq:shell-digit-identity" data-reference-type="eqref" data-reference="long269:eq:shell-digit-identity">[long269:eq:shell-digit-identity]</a>, and the upper bound is Theorem <a href="#long269:res:actual-tail-bound" data-reference-type="ref" data-reference="long269:res:actual-tail-bound">17</a> with the floor taken, since $`d_a`$ is an integer at most $`BQ(n_a)`$. Finally $`n_a\le3a`$, so $`Q(n_a)\le a^{2}+\tfrac83a+2\le90(a+1)^{2}`$. ◻

</div>

Every positive denominator admits the stated factorisation: remove all powers of $`2`$, $`3`$ and $`5`$, leaving $`B`$ coprime to $`30`$. Thus the theorem does not impose an extra restriction on a hypothetical rational $`S`$. The removed factor $`2^u3^v5^w`$ controls how far out the integer tails begin; their bound depends on $`B`$. The displayed $`a_D`$ is sufficient, but need not be the first such index. The next proposition gives the first index when the fraction is reduced. Write $`\operatorname{den}(x)`$ for the positive denominator of a rational number $`x`$ in lowest terms.

<div id="long269:res:exact-denominator" class="proposition">

**Proposition 20** (exact denominators and minimal clearing). *Suppose $`S=N/(MB)`$ is in lowest terms, with $`M=2^u3^v5^w`$ and $`\gcd(B,30)=1`$. For every $`a\ge1`$,
``` math
\operatorname{den}(X_a)=\frac{MB}{\gcd(M,h_a)},\qquad
 \operatorname{den}(BX_a)=\frac{M}{\gcd(M,h_a)}.
```
Hence the first integral reduced tail occurs at
``` math
a_* =\min\{a\ge1:2^a\ge\max(2^{u+1},3^v,5^w)\}\le a_D,
```
and $`BX_a`$ is integral exactly for $`a\ge a_*`$. This onset is computable by integer powers; it is not an estimate obtained by rounding logarithms.*

</div>

<div class="proof">

*Proof.* By Lemma <a href="#long269:res:all-scale-lattice" data-reference-type="ref" data-reference="long269:res:all-scale-lattice">18</a>, $`X_a`$ differs from $`h_aN/(MB)`$ by an integer. Since $`N`$ is coprime to $`MB`$ and $`h_a`$ is supported on $`\{2,3,5\}`$, reduction gives both denominators. Now $`M\mid h_a`$ means $`a-1\ge u`$, $`\lfloor\log_3 2^a\rfloor\ge v`$ and $`\lfloor\log_5 2^a\rfloor\ge w`$, precisely the three integer inequalities. All three persist when $`a`$ increases, giving the first and every later integral reduced tail. The earlier bounds $`3<4`$ and $`5<8`$ give $`a_*\le a_D`$. ◻

</div>

For example, a hypothetical reduced denominator $`2^3 3^2 5\cdot7`$ would require $`2^a\ge\max(16,9,5)`$, so $`a_*=4`$ rather than the sufficient $`a_D=11`$. Lowest terms matter for this exact answer: unreduced factors could cancel against the numerator sooner.

The recurrence preserves integrality forward. Its homogeneous equation also determines how fast two distinct solutions separate.

<div id="long269:res:pinning" class="proposition">

**Proposition 21** (propagation of integrality and uniqueness of a small solution). *For every $`a`$, $`X_a=(m_a+X_{a+1})/b_a>0`$, and if $`X_a\in\mathbb{Z}`$ then $`X_n\in\mathbb{Z}`$ for every $`n\ge a`$. Moreover, fix $`A`$, a positive width function $`w`$ with $`w(A+k)/8^{k}\to0`$, and a real sequence $`(y_n)_{n\ge A}`$ satisfying $`y_{n+1}=b_ny_n-m_n`$. If $`y_n`$ and $`X_n`$ both lie in $`(m_n/b_n,\;m_n/b_n+w(n)]`$ for every $`n\ge A`$, then $`y_A=X_A`$.*

</div>

<div class="proof">

*Proof.* The identity is the recurrence solved for $`X_a`$, and positivity holds because every shell contains its dyadic left endpoint. Integer coefficients preserve integrality at every later step. For the last assertion, $`y_{A+k}-X_{A+k}=(P_{A+k}/P_A)(y_A-X_A)`$. The dyadic height bounds from Section <a href="#long269:sec:blocks" data-reference-type="ref" data-reference="long269:sec:blocks">5</a> give $`P_{A+k}/P_A>8^k/15`$, whereas the common interval bounds the absolute difference by $`w(A+k)`$. Thus $`|y_A-X_A|<15w(A+k)/8^k\to0`$. ◻

</div>

The width condition allows every positive polynomial width and widths $`\rho^n`$ with $`1<\rho<8`$, but not $`8^n`$ itself. Both solutions must lie in the stated intervals; the recurrence alone does not supply that condition. More generally, fix an integer $`B\ge1`$. Every real solution of $`y_{a+1}=b_ay_a-Bm_a`$ starting at an index $`A`$ satisfies
``` math
y_a=BX_a+\frac{P_a}{P_A}(y_A-BX_A)\qquad(a\ge A).
```
Subtracting the recurrence for $`BX_a`$ proves the identity. Since $`X_a=O((a+1)^2)`$ and $`P_a=\Theta(8^a)`$, the unique solution with $`y_a=o(8^a)`$ is $`y_a=BX_a`$; every other solution has $`|y_a|=\Theta(8^a)`$. This classifies growth; integrality of $`BX_a`$ remains a separate question. The same formula explains a numerical precaution: a starting error $`\varepsilon`$ is multiplied by $`P_a/P_A`$ under forward iteration. A decimal approximation propagated forwards is therefore not a certificate of the tail floors. The digit calculation in Section <a href="#long269:sec:open" data-reference-type="ref" data-reference="long269:sec:open">9</a> uses rational intervals with an explicit infinite-tail bound instead.

<a id="a-smaller-bound-from-the-order-of-the-prime-power-jumps"></a>

## A smaller bound from the order of the prime-power jumps

The proof of Theorem <a href="#long269:res:actual-tail-bound" data-reference-type="ref" data-reference="long269:res:actual-tail-bound">17</a> bounded each new prime factor below by $`2`$. But too many powers of $`2`$ cannot occur without an intervening power of $`3`$. Using this restriction gives a smaller geometric majorant.

<div id="long269:res:jump-constrained-bound" class="proposition">

**Proposition 22** (a smaller quadratic bound). *For every $`a\ge0`$,
``` math
0<X_a\le\widetilde Q(n_a)<Q(n_a),\qquad
 \widetilde Q(n)=\frac{1210n^2+9130n+18847}{11979}.
```*

</div>

<div class="proof">

*Proof.* For a point $`x\ge2^a`$, let $`d_p`$ be the increase in its $`p`$-height exponent from the boundary $`2^a`$, and put $`k=d_2+d_3+d_5`$. The definition of $`d_3`$ gives $`x<3^{\lfloor\log_3 2^a\rfloor+d_3+1}\le2^a3^{d_3+1}
<2^{a+2d_3+2}`$, hence $`d_2\le2d_3+1`$. It follows that $`k\le3(d_3+d_5)+1`$, so at least $`j=\lfloor(k+1)/3\rfloor`$ of the $`k`$ new prime factors are odd. Each of these contributes at least $`3`$, and each remaining factor at least $`2`$. Hence
``` math
\frac{\operatorname{H}(x)}{P_a}\ge2^{k-j}3^j=:d(k).
```
There is at most one height cell with each exponent sum, with at most $`(n_a+k+3)^2/9`$ supported points by the earlier projection bound. Consequently
``` math
X_a\le\sum_{k\ge0}\frac{(n_a+k+3)^2}{18d(k)}.
```
Now $`d(3m)=12^m`$, $`d(3m+1)=2\cdot12^m`$ and $`d(3m+2)=6\cdot12^m`$. Grouping in threes and summing the quadratic geometric series gives $`\widetilde Q(n_a)`$. Finally $`11979\bigl(Q(n)-\widetilde Q(n)\bigr)
=121n^2+1518n+5111>0`$ for $`n\ge0`$. ◻

</div>

The estimate uses the original shell multiplicities and the order of the prime-power jumps. It is not a bound for an arbitrary recurrence with the same bases. For an integral $`BX_a`$, the bound can be rounded down to $`\lfloor B\widetilde Q(n_a)\rfloor`$. This improves the bound available in a rationality contradiction. Theorem <a href="#long269:res:actual-escape-endpoint" data-reference-type="ref" data-reference="long269:res:actual-escape-endpoint">24</a> and the recorded finite tests use $`K`$, not this smaller bound. No optimality claim is made for either quadratic bound.

Section <a href="#long269:sec:escape" data-reference-type="ref" data-reference="long269:sec:escape">7</a> explains how the smaller bound can also replace $`K`$ in the residue argument.

<a id="relation-to-cantor-series-criteria."></a>

#### Relation to Cantor-series criteria.

Since $`h_0=1/2`$, the value $`S/2=X_0`$ is the Cantor series $`\sum_{a\ge0}m_a/P_{a+1}`$, with $`P_0=1`$ and $`P_{a+1}=b_aP_a`$. Its normalised tails $`X_a`$ are the usual objects in the rationality criteria for Cantor series. Under a small-numerator hypothesis, Erdős and Straus characterise rationality by the existence of a positive integer $`B`$ and integers $`c_a`$ satisfying, eventually,
``` math
Bm_a=b_ac_a-c_{a+1},\qquad |c_{a+1}|<b_a/2
```
\[erdosstraus1974, Theorem 2.1 and (2.4), pp. 85–86\]. The second condition is part of the criterion, not a consequence of the recurrence alone. Their proof already chooses nearest integers. Hančl and Tijdeman make that choice part of the criterion: they prescribe $`c_a`$ as a nearest integer to $`Bm_a/b_a`$ and require the recurrence \[hancltijdeman2004, §§2–3 and Theorem 3.1, pp. 372–375\]. Koutsoukou-Argyraki and Li formalised the Erdős–Straus criteria in Isabelle/HOL \[afperdosstraus2020\].

Both cited criteria require $`m_a/(b_{a-1}b_a)\to0`$ in our notation. Here the weighted-triangle count gives $`m_a=\Theta((a+1)^2)`$, and
``` math
\frac{m_a}{900}\le\frac{m_a}{b_{a-1}b_a}\le\frac{m_a}{4}
 \qquad(a\ge1).
```
The ratio therefore has quadratic order and tends to infinity. There is also a direct lower count that does not use the real-logarithm triangle estimate. For $`a\ge1`$, each pair $`0\le j,k\le\lfloor a/5\rfloor`$ has $`3^j5^k<2^a`$, since $`15<2^5`$, and hence a unique power-of-two multiple in $`[2^a,2^{a+1})`$. Each such point contributes at least one to $`m_a`$. Thus $`m_a\ge(\lfloor a/5\rfloor+1)^2`$, an elementary lower bound sufficient to see directly that the small-numerator condition fails.

The actual scaled tails also satisfy
``` math
BX_a-\frac{Bm_a}{b_a}=\frac{BX_{a+1}}{b_a}
 =\Theta((a+1)^2)
```
for each fixed $`B\ge1`$, by the recurrence, the quadratic tail bounds and $`2\le b_a\le30`$. Thus any eventual integer tails supplied by a hypothetical rational value could not be the prescribed nearest integers. In fact, those prescribed integers fail the recurrence at every sufficiently large index, regardless of how ties are resolved. If $`c_a`$ is a nearest integer to $`Bm_a/b_a`$, then
``` math
|b_ac_a-Bm_a|\le15,\qquad
 c_{a+1}\ge\frac{Bm_{a+1}}{30}-\frac12\longrightarrow\infty.
```
Consequently $`c_{a+1}=b_ac_a-Bm_a`$ is impossible for all sufficiently large $`a`$. This is a failure of the proposed carry construction, not an irrationality contradiction: the criterion’s small-numerator hypothesis also fails.

The denominator clearing itself is standard; the calculations specific to this series retain its multiplicities, use the strict endpoint to divide the normaliser by two, and bound the resulting positive tails.

For polynomial Cantor data, Hančl–Tijdeman \[hancltijdeman2008, Theorems 2.2 and 3.1\] give a polynomial cancellation criterion and a division mechanism. Their nonconstant polynomial radix is not our bounded $`(b_a)`$. Their separate Theorem 4.2 uses a finite-product rearrangement. We do not use an unrestricted infinite reindexing from that argument: for the integer decompositions considered here, the terminal terms must be checked separately. In the first-order case $`m_a=b_ac_a-c_{a+1}`$, finite summation gives
``` math
\sum_{a=0}^{N-1}\frac{m_a}{P_{a+1}}
 =c_0-\frac{c_N}{P_N}.
```
Every integer $`c_0`$ generates an integer solution recursively. Hence $`c_N/P_N\to c_0-S/2`$; the existence of an integer solution gives no rationality information.

For these actual numerators the terminal term cannot vanish for *any* integer $`c_0`$. Indeed, $`P_3=120`$, $`n_3=5`$ and $`(m_0,m_1,m_2)=(1,4,7)`$, so the tail bound gives
``` math
0<\frac S2
 =\frac12+\frac4{12}+\frac7{120}+\frac{X_3}{120}
 \le\frac{107}{120}+\frac{83}{1080}
 =\frac{523}{540}<1.
```
Thus $`c_0-S/2\ne0`$ for every integer $`c_0`$. Since $`8^N/15<P_N\le8^N`$, every such unscaled integer solution satisfies $`|c_N|=\Theta(8^N)`$. This is a concrete reason that quadratic growth of $`m_a`$ does not imply polynomial growth of recursively defined carries. The starting index is essential: this does not exclude the actual tails becoming integral at a later index. After replacing $`m_a`$ by $`D m_a`$ for an integer $`D\ge1`$, however, a vanishing terminal term would require $`DS/2=c_0`$. Excluding that possibility for every $`D`$ would require irrationality itself; the unscaled calculation does not do so.

In the cited rearrangement the transformed integer numerator must be $`o(b_a)`$, which for bounded radices means eventual zero. Only after the terminal terms have been controlled does this cancellation determine the infinite sum. A polynomial bound on each individual decomposition coefficient would suffice for a fixed number of shifts: the corresponding series are absolutely convergent, since their denominators are products of at least $`2`$ at each step. A polynomial bound on the combined numerators is not a substitute, as the exponentially growing carries above demonstrate. Nor does quadratic growth force a carry to be a polynomial in the floor coordinates.

<a id="long269:sec:escape"></a>

# A residue criterion and the bounds it allows

For example, the first two steps give
``` math
X_2=6X_1-4,\qquad X_3=10X_2-7=60X_1-47.
```
If $`BX_1`$ is an integer, then $`BX_3\equiv-47B\pmod{60}`$. Thus a finite calculation determines the endpoint residue without determining the real tail itself. We next compare such residues with the tail bound.

A window starts at $`\ell\ge0`$ and consists of $`h\ge0`$ steps. Its product of bases and accumulated numerator are integers, even when the tails are not. Set
``` math
W_{\ell,0}=1,\quad F_{\ell,0}=0,\qquad
 W_{\ell,h+1}=b_{\ell+h}W_{\ell,h},\quad
 F_{\ell,h+1}=b_{\ell+h}F_{\ell,h}+m_{\ell+h}.
```
Induction gives
``` math
\begin{equation}
\label{long269:eq:window-identity}
 X_{\ell+h}=W_{\ell,h}X_\ell-F_{\ell,h},\qquad
 d_{\ell+h}=W_{\ell,h}d_\ell-BF_{\ell,h}
\end{equation}
```
for any sequence satisfying $`d_{n+1}=b_nd_n-Bm_n`$. Since $`b_a=P_{a+1}/P_a`$, the product telescopes to $`W_{\ell,h}=P_{\ell+h}/P_\ell`$. The previously proved bounds $`8^a/15<P_a\le8^a`$ therefore give $`W_{\ell,h}>8^h/15`$. For a positive integer $`C`$ and an integer $`N`$, use $`\operatorname{lpr}_C(N)=1+((N-1)\bmod C)\in\{1,\ldots,C\}`$. In particular $`\operatorname{lpr}_C(0)=C`$. Positivity of this representative is what allows comparison with a positive integral carry.

<div id="long269:res:consumer" class="proposition">

**Proposition 23** (least positive residues). *Let $`C>0`$ and let $`c`$ be an integer with $`0<c`$ and $`|c|\le K`$. If $`c\equiv N\pmod C`$ and $`K<\operatorname{lpr}_C(N)`$, then the hypotheses are contradictory.*

</div>

<div class="proof">

*Proof.* Every positive integer congruent to $`N`$ is at least $`\operatorname{lpr}_C(N)`$. Thus $`\operatorname{lpr}_C(N)\le c=|c|\le K`$, contrary to the strict inequality. ◻

</div>

For a bound $`G:\mathbb{N}_{>0}\times\mathbb{N}\to\mathbb{N}`$ let $`\mathsf E(G)`$ be the statement
``` math
\begin{equation}
\label{long269:eq:actual-escape}
 \begin{gathered}
 \text{for every }B\ge1\text{ with }\gcd(B,30)=1\text{ and every }a_0\ge1,\\
 \text{there are }\ell\ge a_0\text{ and }h\ge1\text{ with }
 \operatorname{lpr}_{W_{\ell,h}}(-BF_{\ell,h})>G(B,\ell+h) .
 \end{gathered}
\end{equation}
```
The window may depend on both $`B`$ and $`a_0`$. All quantities in the inequality are finite integers. The quantifiers over denominators and prescribed onsets are nevertheless unbounded; a search over a finite rectangle of $`(B,\ell)`$ does not verify them. Every $`b_a>0`$, so $`W_{\ell,h}>0`$ is automatic.

The two hypotheses on $`G`$ in the next theorem serve different purposes. Domination of $`K`$ lets a residue above $`G`$ exclude a positive integer tail. The limit $`G(B,a)/8^a\to0`$ lets every sufficiently long window from a fixed nonintegral start overtake $`G`$. It is a sufficient growth condition, not a necessary one: if only existence of a window is required, a subsequence of small endpoint bounds can suffice, as we prove below. The stated theorem already covers every polynomial upper bound that dominates $`K`$, and also $`\max\{K(B,a),\lceil B\rho^a\rceil\}`$ for $`1<\rho<8`$. The zero bound fails to control the possible integer tail.

<div id="long269:res:actual-escape-endpoint" class="theorem">

**Theorem 24** (a residue criterion for every dominating bound of size $`o(8^a)`$). *<span id="long269:res:lead-escape-equivalence" label="long269:res:lead-escape-equivalence"></span><span id="long269:res:windowconsumer" label="long269:res:windowconsumer"></span> Let $`G:\mathbb{N}_{>0}\times\mathbb{N}\to\mathbb{N}`$ satisfy $`K(B,a)\le G(B,a)`$ for all $`B`$ and $`a`$, and $`G(B,a)/8^{a}\to0`$ as $`a\to\infty`$ for each fixed $`B`$. Then
``` math
\mathsf E(G)\quad\Longleftrightarrow\quad S\notin\mathbb{Q}.
```
Both $`K`$ of <a href="#long269:eq:actual-bound" data-reference-type="eqref" data-reference="long269:eq:actual-bound">[long269:eq:actual-bound]</a> and $`K_0(B,a)=90B(a+1)^{2}`$ satisfy these hypotheses, so $`\mathsf E(K)`$, $`\mathsf E(K_0)`$ and irrationality of $`S`$ are mutually equivalent. By contrast, $`\mathsf E(0)`$ holds automatically, since every least positive residue is at least $`1`$; its truth alone therefore provides no contradiction to an integral tail.*

</div>

<div class="proof">

*Proof.* Suppose $`\mathsf E(G)`$ and suppose $`S=N/D`$ were rational. Theorem <a href="#long269:res:actual-cancellation" data-reference-type="ref" data-reference="long269:res:actual-cancellation">19</a> supplies $`B\ge1`$ coprime to $`30`$, an onset $`a_D`$, and positive integers $`d_a=BX_a\le K(B,a)\le G(B,a)`$ for $`a\ge a_D`$ satisfying the cleared recurrence. Apply <a href="#long269:eq:actual-escape" data-reference-type="eqref" data-reference="long269:eq:actual-escape">[long269:eq:actual-escape]</a> with $`a_0=a_D`$ to obtain a window $`(\ell,h)`$ with $`\ell\ge a_D`$. By <a href="#long269:eq:window-identity" data-reference-type="eqref" data-reference="long269:eq:window-identity">[long269:eq:window-identity]</a>, $`d_{\ell+h}\equiv-BF_{\ell,h}`$ modulo $`W_{\ell,h}`$, while $`0<d_{\ell+h}\le G(B,\ell+h)<\operatorname{lpr}_{W_{\ell,h}}(-BF_{\ell,h})`$. Proposition <a href="#long269:res:consumer" data-reference-type="ref" data-reference="long269:res:consumer">23</a> is the contradiction, so $`S`$ is irrational.

Conversely suppose $`S\notin\mathbb{Q}`$, and fix $`B\ge1`$ coprime to $`30`$ and $`a_0\ge1`$. Set $`\ell=a_0`$ and $`\delta=\lceil BX_\ell\rceil-BX_\ell\in(0,1)`$; the prefix identity makes $`BX_\ell`$ irrational. For all sufficiently large $`h`$, $`0<\delta+BX_{\ell+h}/W_{\ell,h}<1`$, because $`X_{\ell+h}=O((\ell+h+1)^2)`$ and $`W_{\ell,h}>8^h/15`$ as shown above. The integer $`\lceil BX_\ell\rceil W_{\ell,h}-BF_{\ell,h}`$ is therefore exactly
``` math
\operatorname{lpr}_{W_{\ell,h}}(-BF_{\ell,h})
 =\delta W_{\ell,h}+BX_{\ell+h}.
```
Its first term eventually exceeds $`G(B,\ell+h)`$, since $`G(B,a)=o(8^a)`$. Thus every sufficiently long window from this fixed start escapes, which is stronger than the required existence.

For the two stated bounds, $`n_a\le3a`$ gives $`K(B,a)\le BQ(3a)\le90B(a+1)^2=K_0(B,a)`$. Both are $`O((a+1)^2)`$ for fixed $`B`$, so both satisfy the required limit. Finally, $`\operatorname{lpr}_C(N)\ge1>0`$ always, independently of whether any tail is integral; a residue greater than zero cannot exclude a positive integer. ◻

</div>

The domination assumption is sufficient, not asserted to be necessary for equivalence. In particular, Proposition <a href="#long269:res:jump-constrained-bound" data-reference-type="ref" data-reference="long269:res:jump-constrained-bound">22</a> already supplies the smaller valid bound $`\lfloor B\widetilde Q(n_a)\rfloor`$. Replacing $`K`$ by that bound in the forward implication leaves the argument unchanged; the converse uses only $`G(B,a)=o(8^a)`$. The zero-bound example explains why a size comparison with the possible integer tail is needed in the contradiction, not why this particular $`K`$ is indispensable.

The reverse implication gives more than existence: at any fixed start with $`BX_\ell`$ nonintegral, the least positive residue eventually occupies a fixed positive fraction of the whole modulus. The next proposition states this without assuming that $`S`$ is irrational.

<div id="long269:res:residue-limit" class="proposition">

**Proposition 25** (the fixed-start residue limit). *For fixed integers $`B,\ell\ge1`$, write
``` math
R_h=\operatorname{lpr}_{W_{\ell,h}}(-BF_{\ell,h}).
```
For all sufficiently large $`h`$,
``` math
R_h=(\lceil BX_\ell\rceil-BX_\ell)W_{\ell,h}+BX_{\ell+h},
```
and consequently
``` math
\lim_{h\to\infty}\frac{R_h}{W_{\ell,h}}
 =\lceil BX_\ell\rceil-BX_\ell.
```
In particular, if $`BX_\ell`$ is integral, then $`R_h=BX_{\ell+h}`$ for all sufficiently large $`h`$.*

</div>

<div class="proof">

*Proof.* The least positive residue is the modulus times the gap to the next strictly larger integer. Division with remainder gives
``` math
\frac{R_h}{W_{\ell,h}}
 =\left\lfloor\frac{BF_{\ell,h}}{W_{\ell,h}}\right\rfloor+1
       -\frac{BF_{\ell,h}}{W_{\ell,h}}.
```
By the window identity, $`BF_{\ell,h}/W_{\ell,h}=BX_\ell-BX_{\ell+h}/W_{\ell,h}`$. These finite sums approach $`BX_\ell`$ strictly from below, since $`BX_{\ell+h}>0`$ and $`BX_{\ell+h}/W_{\ell,h}\to0`$. Their floors therefore eventually equal $`\lceil BX_\ell\rceil-1`$, including when $`BX_\ell`$ is an integer. Substitution proves both claims. The strict approach from below matters at an integer limit; the residue convention alone would assign a zero congruence class the value $`W_{\ell,h}`$, not zero. ◻

</div>

Thus a nonintegral $`BX_\ell`$, even for a rational $`S`$, gives arbitrarily long successful windows against any bound $`G(B,a)=o(8^a)`$ for that fixed $`B`$. The rationality contradiction instead uses the denominator’s specific multiplier and a start beyond its clearing onset. Success for one pair $`(B,\ell)`$ does not replace either quantifier.

<a id="the-exact-growth-restriction-on-a-dominating-bound."></a>

#### The exact growth restriction on a dominating bound.

A bound need not be small at every late endpoint. For example, set
``` math
G(B,a)=
 \begin{cases}
 K(B,a),&a\text{ even},\\
 K(B,a)+8^a,&a\text{ odd}.
 \end{cases}
```
At an odd endpoint $`a=\ell+h`$, no window with $`\ell\ge1`$ can pass: its residue is at most $`W_{\ell,h}=P_a/P_\ell\le8^a/2<G(B,a)`$. At even endpoints the test is unchanged. If $`S`$ is irrational, the proof above therefore supplies successful windows ending at every sufficiently large even index, from each fixed start. Thus $`G(B,a)/8^a\to0`$ is not necessary for the equivalence.

More precisely, for every integer-valued $`G\ge K`$,
``` math
\mathsf E(G)\quad\Longleftrightarrow\quad
 \left\{\begin{gathered}
 S\notin\mathbb{Q},\\
 \liminf_{a\to\infty}\frac{G(B,a)}{8^a}=0
 \quad\text{for every }B\ge1\text{ with }\gcd(B,30)=1.
 \end{gathered}\right.
```
Suppose first that $`\mathsf E(G)`$ holds. The earlier rationality contradiction uses only $`G\ge K`$. For a successful window starting at $`\ell\ge a_0`$, put $`a=\ell+h`$. Since a least positive residue is at most its modulus,
``` math
0\le\frac{G(B,a)}{8^a}
 <\frac{P_a}{P_\ell8^a}\le\frac1{P_\ell}
 \le\frac1{P_{a_0}}.
```
Such endpoints satisfy $`a>a_0`$, and $`P_{a_0}\to\infty`$; hence the lower limit is zero. Conversely, suppose $`S`$ is irrational and these lower limits vanish. Fix $`B`$ and $`\ell\ge1`$. By the fixed-start residue limit, with $`\delta=\lceil BX_\ell\rceil-BX_\ell>0`$,
``` math
\frac{\operatorname{lpr}_{W_{\ell,h}}(-BF_{\ell,h})}{P_{\ell+h}}
 \longrightarrow\frac{\delta}{P_\ell}>0.
```
The bounds $`8^a/15<P_a\le8^a`$ imply $`\liminf_a G(B,a)/P_a=0`$. Along a sufficiently late subsequence of endpoints the residue therefore exceeds $`G`$. This gives arbitrarily long successful windows from each fixed start, but need not give success at every sufficiently large length, as the parity example shows.

In particular, $`G(B,a)=K(B,a)+8^a`$ allows no window at all. More generally, an eventual lower bound $`G(B,a)\ge c8^a`$, for one eligible $`B`$ and some $`c>0`$, excludes every sufficiently late start: choose $`P_\ell\ge1/c`$ and compare the bound with $`W_{\ell,h}\le8^{\ell+h}/P_\ell`$. These are restrictions on the test bound, not additional assumptions about the series. The original quadratic bounds satisfy the lower-limit condition, so the remaining problem is still the existence of the windows. Equivalence alone says nothing about the relative difficulty of the formulations; a useful arithmetic proof must exploit further information about the numerators $`m_a`$.

A fixed window can have a lower bound greater than $`1`$. Write $`W`$ and $`F`$ for its product and accumulated numerator. Every prime factor of $`W`$ lies in $`\{2,3,5\}`$, so an eligible multiplier $`B`$ is a unit modulo $`W`$. Congruence then gives
``` math
\gcd\bigl(\operatorname{lpr}_W(-BF),W\bigr)=\gcd(F,W).
```
For $`(W,F)=(6,4)`$, the possible residues are $`2`$ and $`4`$, attained at $`B=1`$ and $`11`$; thus $`2`$ is a lower bound for this window, and the residues are not units. For $`(W,F)=(60,47)`$, however, $`\operatorname{lpr}_{60}(-37\cdot47)=1`$, with $`37`$ coprime to $`30`$. Thus no lower bound greater than $`1`$ works for all windows and eligible multipliers, although a particular window may have one.

<a id="how-fast-the-window-base-grows"></a>

## How fast the window base grows

Using only $`W_{\ell,h}\ge2^h`$ in the converse proof gives the sufficient condition $`G(B,a)=o(2^a)`$ for each fixed $`B`$. The exact height formula instead gives growth comparable to $`8^h`$, uniformly in the start, and hence admits the larger class $`G(B,a)=o(8^a)`$. For an irrational $`S`$, the exact restriction on a dominating bound is the preceding lower-limit condition, not either little-$`o`$ bound.

<div id="long269:res:window-growth" class="proposition">

**Proposition 26** (growth of the window product). *Put $`\theta_3=\log_32`$ and $`\theta_5=\log_52`$. For all $`\ell\ge0`$ and $`h\ge1`$,
``` math
W_{\ell,h}=2^{h}\,
 3^{\lfloor(\ell+h)\theta_3\rfloor-\lfloor\ell\theta_3\rfloor}\,
 5^{\lfloor(\ell+h)\theta_5\rfloor-\lfloor\ell\theta_5\rfloor},
 \qquad
 \frac{8^{h}}{15}<W_{\ell,h}<15\cdot8^{h} .
```*

</div>

<div class="proof">

*Proof.* Telescoping <a href="#long269:eq:dyadic-alphabet" data-reference-type="eqref" data-reference="long269:eq:dyadic-alphabet">[long269:eq:dyadic-alphabet]</a> gives $`W_{\ell,h}=P_{\ell+h}/P_\ell`$, and the displayed formula is that quotient written out. Each floor difference differs from $`h\theta_p`$ by less than one, and $`3^{\theta_3}=5^{\theta_5}=2`$, so the $`3`$-factor lies strictly between $`2^{h}/3`$ and $`3\cdot2^{h}`$ and the $`5`$-factor strictly between $`2^{h}/5`$ and $`5\cdot2^{h}`$. Multiplying the three ranges gives the bounds. ◻

</div>

<div id="long269:res:no-bounded-length" class="corollary">

**Corollary 27** (a fixed maximum length cannot cover arbitrarily late starts). *Fix $`B\ge1`$ coprime to $`30`$ and $`H\ge1`$. Only finitely many starts $`\ell`$ admit an escaping window of length at most $`H`$ against the bound $`K`$.*

</div>

<div class="proof">

*Proof.* A least positive residue never exceeds its modulus, so escape at $`(\ell,h)`$ requires $`K(B,\ell+h)<W_{\ell,h}<15\cdot8^{h}\le15\cdot8^{H}`$. On the other hand $`j_a\ge a-1`$, since the powers $`2,\ldots,2^{a-1}`$ already lie below $`2^{a}`$, so $`K(B,\ell+h)\ge\lfloor B((\ell-1)^{2}+10(\ell-1)+27)/9\rfloor`$, which tends to infinity with $`\ell`$. ◻

</div>

Corollary <a href="#long269:res:no-bounded-length" data-reference-type="ref" data-reference="long269:res:no-bounded-length">27</a> is the exact reason a finite scan cannot approach the cofinal quantifier by widening its denominator range alone. For $`\ell\ge1`$, the inequality $`K(B,\ell+h)>B\ell^2/9`$ shows that an escaping window must satisfy
``` math
3h>\log_2K(B,\ell+h)-\log_215
    >\log_2B+2\log_2\ell-\log_2135.
```
This is only a necessary lower bound, not an asymptotic formula or an upper bound for the first successful length. An explicit eventual escape threshold can be obtained from a positive lower bound for $`\delta=\lceil BX_\ell\rceil-BX_\ell`$ and for $`1-\delta`$, together with the displayed tail and window estimates. No such uniform information about the tails of $`S`$ is proved here.

*Status.* The problem treated here is open, and this note does not close it. Every statement below marked as checked is a proposition that the pinned Lean kernel accepts from the sources this note links to, with no `sorry`, no added axiom, and no unchecked evaluation. That is a claim about the formal statement, not about its mathematical interest, its novelty, or the original problem. The unresolved obligations are named exactly, in their own section, and none of the finite computations, reductions, or no-go results here removes one of them.

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.

<a id="long269:sec:evidence"></a>

# Finite computations and their limits

The three displayed window tuples and the twelve-shell denominator bound below have directly replayable finite certificates. The larger scan and the two much larger denominator exclusions are archived computational reports. Their full execution records are not supplied here; in particular the two large exclusions lack their machine-readable witnesses. They are not theorem inputs, and none supplies the unbounded quantifiers.

<a id="checking-individual-windows"></a>

## Checking individual windows

The three rows below record individual instances of the residue inequality <a href="#long269:eq:actual-escape" data-reference-type="eqref" data-reference="long269:eq:actual-escape">[long269:eq:actual-escape]</a>. The integer-only [dyadic-window checker](https://github.com/wcook04/plectis-erdos/tree/ee650b32b8b2cb98b94e5500df5370d85f7403b8/scripts/check_erdos269_dyadic_windows.py) is their historical source; exact enumeration independently reproduces them. For each required shell, enumerate the pairs with $`3^j5^k<2^{a+1}`$, choose the unique exponent $`i`$ that puts $`2^i3^j5^k`$ in $`[2^a,2^{a+1})`$, and add $`P_{a+1}/(2\operatorname{H}(2^i3^j5^k))`$. All powers and comparisons are integral. The recursions for $`W`$ and $`F`$ then give the displayed window data. The columns give the denominator $`B`$, the start $`\ell`$, the length $`h`$, the endpoint jump index $`j_{\ell+h}`$, the product $`W`$ of the bases, the accumulated numerator $`F`$, the residue $`R=\operatorname{lpr}_W(-BF)`$ and the bound $`K`$ of <a href="#long269:eq:actual-bound" data-reference-type="eqref" data-reference="long269:eq:actual-bound">[long269:eq:actual-bound]</a>.
``` math
\begin{array}{c|c|c|c|r|r|r|r}
B&\ell&h&j_{\ell+h}&W&F&R&K\\ \hline
1&1&2&4&60&47&13&9\\
7&1&3&6&360&289&137&95\\
16&1&4&9&10800&8735&640&352
\end{array}
```
The first row reads as follows. The window starts at $`\ell=1`$ and has length $`2`$, so $`W=b_1b_2=6\cdot10=60`$; the accumulated numerator is $`F=47`$; and $`\operatorname{lpr}_{60}(-47)=13`$, since $`-47+60=13`$, which exceeds $`K(1,3)=\lfloor(16+40+27)/9\rfloor=9`$. The third row lies outside the domain of <a href="#long269:eq:actual-escape" data-reference-type="eqref" data-reference="long269:eq:actual-escape">[long269:eq:actual-escape]</a>, since $`\gcd(16,30)=2`$, and is displayed to illustrate the window arithmetic at greater depth.

The archived scan report covers $`B\le5000`$ coprime to $`30`$ and $`100\le\ell\le3000`$: $`3{,}869{,}934`$ pairs, with reported first escape length at most $`18`$ in a search to length $`24`$. The full scan was not rerun. Its histogram in Section <a href="#long269:long:experiments" data-reference-type="ref" data-reference="long269:long:experiments">10.4</a> is an archived observation, not a consequence of the window-growth bound. By contrast, the accompanying integer-only check reconstructs the shells and tests all $`2496`$ pairs with $`1\le B\le97`$, $`\gcd(B,30)=1`$ and $`1\le\ell\le96`$. Every pair escapes; the first successful lengths range from $`1`$ to $`10`$, with a search limit of $`24`$. This smaller scan uses the enumeration and window recursions above, without floating-point logarithms. Neither computation proves escape for unbounded $`B`$ or arbitrarily late starts; Corollary <a href="#long269:res:no-bounded-length" data-reference-type="ref" data-reference="long269:res:no-bounded-length">27</a> rules out covering the latter quantifier with any fixed maximum length.

<a id="finite-denominator-bounds"></a>

## Finite denominator bounds

<a id="a-denominator-bound-from-twelve-shells."></a>

#### A denominator bound from twelve shells.

The actual tail bound gives a small certificate whose integer data fit on the page. Since $`h_1=1`$, we have $`X_1=S-1`$. Finite summation through shell $`11`$, with $`P_{12}=27993600000`$ and $`Q(n_{12})=Q(24)=262/3`$, gives
``` math
X_1=2\sum_{a=1}^{11}\frac{m_a}{P_{a+1}}
          +\frac{2X_{12}}{P_{12}},
```
``` math
\frac{11327881097}{13996800000}<X_1
 \le\frac{33983643553}{41990400000}.
```
The enclosure is strictly inside the interval $`(11498/14207,\,6409/7919)`$, as integer cross-multiplication verifies. The endpoint determinant is $`14207\cdot6409-11498\cdot7919=1`$. For any rational $`u/v`$ strictly between them, with $`v>0`$, both integers $`14207u-11498v`$ and $`6409v-7919u`$ are positive. Consequently
``` math
v=7919(14207u-11498v)+14207(6409v-7919u)\ge22126.
```
Thus, if $`S`$ is rational, its reduced denominator is at least $`22126`$. This is the elementary denominator bound between two fractions with cross-determinant one, often expressed using Farey neighbours. It is also the best lower bound on a possible denominator obtainable from this enclosure alone: the mediant
``` math
\frac{11498+6409}{14207+7919}=\frac{17907}{22126}
```
is in lowest terms and lies strictly inside the certified enclosure. This does not identify $`X_1`$ with the mediant or assert that $`S`$ has that denominator. It says that this interval is still compatible with a rational of denominator $`22126`$.

The certificate uses the actual shell coefficients and proved tail bound, not the archived continued-fraction statistics below. A narrower certified enclosure could exclude further denominators; the two much larger reported exclusions that follow are not verified by this calculation.

<a id="long269:res:lead-block-exclusion"></a>

#### Archived window-$`128`$ exclusion report (witness unavailable).

The archived report asserts the following, which is not used as a proved result in this revision. Using windows of length $`128`$ and $`64`$ starting indices, the first $`10005`$, it reports that no rational value of the $`\{2,3,5\}`$ running-LCM series has reduced denominator $`MB`$ with $`M`$ a divisor supported on $`\{2,3,5\}`$ of $`2^{10005}3^{6312}5^{4308}`$, $`\gcd(B,30)=1`$ and $`1<B\le B_{\max}`$, where $`B_{\max}`$ is the $`106`$-digit integer
``` math
\begin{aligned}
 B_{\max}={}&1134599670999687767349520845707093359257353022286558739363600235\\
 &016103207564063373270305324172145281971729 ,
\end{aligned}
```
so that $`\log_2B_{\max}=348.9846\ldots`$.

The exponent triple $`(10005,6312,4308)`$ is that of $`\operatorname{H}(2^{10005})`$. The reported normalisation therefore uses the full height at its first start, whereas Lemma <a href="#long269:res:all-scale-lattice" data-reference-type="ref" data-reference="long269:res:all-scale-lattice">18</a> uses the half height $`h_{10005}`$. The reported family of smooth denominators is the larger one.

The archived report gives $`386.40993\ldots`$ for the base-two logarithm of its window product. It also records an exclusion index of $`1`$, an enclosure width of $`9.674\times10^{-227}`$, and a maximum ratio of $`0.185997`$, labelled $`X/W`$ in the report. This label is retained without identifying its $`X`$ with a tail $`X_a`$. The report attributes the exclusion index to a reduced basis within a bound assigned to each starting index. Without the exact enclosure, basis, integer inequalities, software revision and execution command, these figures do not verify the claimed exclusion. No Lean declaration is claimed for this report.

<a id="long269:res:cf-exclusion"></a>

#### Archived continued-fraction report.

The archived report claims $`13{,}109`$ certified partial quotients for the normalised tail $`X_1`$ and an exclusion of reduced denominators at most $`2^{22482}`$, about $`10^{6768}`$.

The stated certification method is a common prefix of the continued fractions of the two endpoints of an interval provably containing $`X_1`$; the numbers with a given prefix of partial quotients form an interval \[bosmaCF, Lemma 10.1.2, p. 106\], so this method can give an exact certificate rather than a numerical approximation. The report also says that its truncation was checked against the direct smooth-number sum as an exact rational. Those checks cannot be repeated from the supplied material: the machine-readable witness and execution record are absent. The asserted exclusion is therefore not a theorem input. A replay must supply rational endpoints, a proof that $`X_1`$ lies in the interval, the common continued-fraction cylinder, and a rigorous lower bound for denominators of all rationals in the enclosure. A count of matching partial quotients alone is not that denominator certificate. The recorded statistics are a largest denominator of $`22{,}483`$ bits, a largest partial quotient of $`129{,}114`$, a mean partial quotient of $`23.4133`$, observed Gauss–Kuzmin frequencies $`0.4208`$, $`0.1665`$, $`0.0917`$, $`0.0575`$, $`0.0391`$ against the predicted $`0.4150`$, $`0.1699`$, $`0.0931`$, $`0.0589`$, $`0.0406`$, and a Lévy constant of $`1.18869`$ against $`\pi^{2}/(12\log2)=1.18657`$. The predicted values are the almost-everywhere frequencies of Gauss’s law and Lévy’s almost-everywhere constant \[levy1936, pp. 288–289 and footnote 5\]. These statistics describe a finite prefix and do not bear on whether $`X_1`$ is a Liouville number, algebraic, or rational with a larger denominator.

The two archived reports concern different finite families: one uses a lattice at a fixed starting index and fixed smooth part, the other a continued-fraction enclosure at $`a=1`$. Neither has a reproducible witness in the supplied material. Even after verification, each would exclude only its stated denominator range and neither would settle an instance of the problem.

<a id="long269:sec:open"></a>

# The remaining arithmetic questions

<a id="long269:sec:weighted-shifts"></a>

## An exact weighted-shift identity for the repeated series

We return to the repeated sum $`S`$, not the distinct-height sum $`\mathcal D_{2,3,5}`$. Set $`\alpha=S/2`$ and keep the boundary heights $`P_a`$ defined above. A shifted tail represents the same value after a finite rational correction. The following identity combines several such shifts with fixed integer coefficients. Its weights are necessary: ordinary shifts of the numerators alone would not account for the changing denominators. In this subsection and the next, $`r`$ denotes a positive integer shift, not a prime generator.

<div id="long269:res:weighted-shift-identity" class="lemma">

**Lemma 28** (weighted shifts preserve the actual value). *Fix integers $`c_0,\ldots,c_\sigma`$, not all zero, independently of the positive integer shift $`r`$. Put
``` math
\gamma_{a,t}=\frac{P_tP_{a+1}}{P_{a+t+1}},\qquad
 D_{r,a}=15\sum_{j=0}^{\sigma}c_j\gamma_{a,jr}m_{a+jr}.
```
Then $`\gamma_{a,t}\in\{1,1/3,1/5,1/15\}`$ and $`D_{r,a}\in\mathbb{Z}`$. Furthermore, with
``` math
A_r=15\sum_{j=0}^{\sigma}c_jP_{jr},\qquad
 Z_r=15\sum_{j=0}^{\sigma}c_jP_{jr}
       \sum_{k<jr}\frac{m_k}{P_{k+1}}\in\mathbb{Z},
```
we have the absolutely convergent identity
``` math
\begin{equation}
\label{long269:eq:weighted-shift-identity}
 A_r\alpha-Z_r=\sum_{a\ge0}\frac{D_{r,a}}{P_{a+1}}.
\end{equation}
```
One may take $`C=225\sum_{j=0}^{\sigma}|c_j|\max(1,j)^2`$ in $`|D_{r,a}|\le C(a+r+1)^2`$. If $`J`$ is the largest index with $`c_J\ne0`$, then $`A_r\ne0`$ whenever $`\sum_{j<J}|c_j|2^{-(J-j)r}<|c_J|`$; an empty sum is zero.*

</div>

<div class="proof">

*Proof.* The exponent of $`2`$ in $`\gamma_{a,t}`$ is $`t+(a+1)-(a+t+1)=0`$. For $`p=3,5`$, the exponent is $`\lfloor t\theta_p\rfloor+\lfloor(a+1)\theta_p\rfloor
-\lfloor(a+t+1)\theta_p\rfloor`$, which is $`0`$ or $`-1`$ by floor addition. Thus the only possible denominator factors are one $`3`$ and one $`5`$; the prefactor $`15`$ in $`D_{r,a}`$ clears both. For $`k<jr`$, $`P_{k+1}`$ divides $`P_{jr}`$, so $`Z_r`$ is an integer. For each $`t`$, absolute convergence gives
``` math
\sum_{a\ge0}\frac{\gamma_{a,t}m_{a+t}}{P_{a+1}}
 =P_t\sum_{k\ge t}\frac{m_k}{P_{k+1}}
 =P_t\left(\alpha-\sum_{k<t}\frac{m_k}{P_{k+1}}\right).
```
The finite linear combination proves the identity. Lemma <a href="#long269:res:literal-triangle" data-reference-type="ref" data-reference="long269:res:literal-triangle">15</a>, $`0<\gamma\le1`$ and $`a+jr+1\le\max(1,j)(a+r+1)`$ give the stated constant. For $`j<J`$, $`P_{jr}/P_{Jr}\le2^{-(J-j)r}`$. Dividing $`A_r`$ by $`15P_{Jr}`$ and bounding the remaining terms proves the nonvanishing condition, which holds for all sufficiently large $`r`$. ◻

</div>

For any fixed nonzero coefficient vector, including $`(1,-3,3,-1)`$, the nonvanishing condition is automatic for sufficiently large $`r`$: each term on its left tends to zero. No arithmetic assumption on $`S`$ is needed. The identity still represents $`S/2`$, but gives no sparsity or cancellation of $`D_{r,a}`$.

<a id="long269:sec:boundary-difference"></a>

## Why the growing boundary need not cancel

The numerators count weighted lattice points in growing triangles. Suppose first that a point’s weight is unchanged by the four shifts. In a third difference with coefficients $`(1,-3,3,-1)`$, a point present in all four triangles has total coefficient zero. A point entering only the last three, last two or last triangle has coefficient $`-1`$, $`2`$ or $`-1`$, respectively. The common interior therefore cancels, but the new boundary strips need not. We now separate these contributions from changes in the weights caused by floor crossings.

Recall that $`w_{j,k}=j\log_2 3+k\log_2 5`$, $`t_{j,k}=\{w_{j,k}\}`$ and $`\theta_p=1/\log_2 p`$ for $`p=3,5`$. To distinguish the shared points from the new ones, let $`\mathcal T_a=\{(j,k)\in\mathbb N^2:w_{j,k}<a+1\}`$ and, for $`0\le t<1`$, set
``` math
\omega_a(t)=\prod_{p\in\{3,5\}}
 p^{\lfloor(a+1)\theta_p\rfloor-\lfloor(a+t)\theta_p\rfloor}.
```
This weight is defined even for pairs outside $`\mathcal T_a`$. For $`\nu\ge0`$, put
``` math
\begin{split}
 \kappa_p(a,t,\nu r)
 &=\lfloor(a+t+\nu r)\theta_p\rfloor
   -\lfloor(a+t)\theta_p\rfloor-\lfloor\nu r\theta_p\rfloor,\\
 \chi_\nu(a,t)&=3^{-\kappa_3(a,t,\nu r)}5^{-\kappa_5(a,t,\nu r)}.
 \end{split}
```
Each $`\kappa_p`$ is $`0`$ or $`1`$. A value $`\kappa_p=1`$ records a floor-addition carry. This is different from a new lattice point entering $`\mathcal T_a`$ as $`a`$ increases.

<div id="long269:res:strip-decomposition" class="proposition">

**Proposition 29** (an exact interior-and-strip decomposition). *For a fixed operator $`c_0,\ldots,c_\sigma`$ and $`r\ge1`$, let $`E_0=\mathcal T_a`$ and $`E_s=\mathcal T_{a+sr}\smallsetminus \mathcal T_{a+(s-1)r}`$ for $`1\le s\le\sigma`$. Then
``` math
\frac{D_{r,a}}{15}=
 \sum_{s=0}^{\sigma}\ \sum_{(j,k)\in E_s}
 \omega_a(t_{j,k})\sum_{\nu=s}^{\sigma}c_\nu\chi_\nu(a,t_{j,k}).
```
For the cubic operator $`(1,-3,3,-1)`$, if all these crossing bits vanish, then
``` math
\frac{D_{r,a}}{15}=-M_0+2M_1-M_2,\qquad
 M_s=\sum_{(j,k)\in \mathcal T_{a+(s+1)r}\smallsetminus \mathcal T_{a+sr}}\omega_a(t_{j,k}).
```
Thus absence of floor crossings cancels the common interior, but not necessarily the three boundary strips.*

</div>

<div class="proof">

*Proof.* For each $`p=3,5`$, the exponent of $`p`$ on either side of
``` math
\gamma_{a,\nu r}\omega_{a+\nu r}(t)
   =\omega_a(t)\chi_\nu(a,t)
```
is
``` math
\lfloor(a+1)\theta_p\rfloor+\lfloor\nu r\theta_p\rfloor
 -\lfloor(a+t+\nu r)\theta_p\rfloor.
```
On the left the upper-boundary exponents cancel; on the right the $`\lfloor(a+t)\theta_p\rfloor`$ terms cancel. This proves the pointwise identity. Insert the triangle formula for each $`m_{a+\nu r}`$ and group by the first triangle containing a pair. A pair in $`E_s`$ occurs exactly in the terms $`\nu\ge s`$, proving the first formula. Under the no-crossing hypothesis, $`\chi_\nu=1`$. The full cubic sum is zero, while its three successive suffix sums are $`-1,2,-1`$, proving the second formula. ◻

</div>

<div id="long269:res:no-crossing-counterexample" class="example">

**Example 30** (cubic cancellation can fail with no floor crossings). Take $`a=0`$, $`r=35`$ and $`(c_0,c_1,c_2,c_3)=(1,-3,3,-1)`$. Exact integer comparisons give
``` math
\begin{array}{c|rrrr}
 u&0&35&70&105\\\hline
 \lfloor\log_3 2^u\rfloor=\lfloor\log_3 2^{u+1}\rfloor&0&22&44&66\\
 \lfloor\log_5 2^u\rfloor=\lfloor\log_5 2^{u+1}\rfloor&0&15&30&45\\
 m_u&1&195&723&1582
\end{array}
```
The first two rows imply $`b_u=2`$ and $`\lfloor(u+t)\theta_p\rfloor=\lfloor u\theta_p\rfloor`$ for every $`0\le t<1`$, $`p=3,5`$. Hence every relevant $`\kappa_p(0,t,u)`$ vanishes, $`\gamma_{0,u}=1`$, and all triangle weights at these four indices are $`1`$. The last row is therefore the count of pairs satisfying $`3^j5^k<2^{u+1}`$, not a floating-point estimate. The strips have sizes $`194,528,859`$, so
``` math
D_{35,0}=15(-194+2\cdot528-859)=45\ne0.
```
Exact enumeration in this revision reproduced all four counts and checked the endpoint power inequalities using integers. This example disproves the claim that avoiding floor crossings alone forces the third difference to vanish. It does not exclude a different fixed operator, different shifts, a boundary correction or a sparse-defect statement restricted to a suitable infinite subsequence.

</div>

<a id="what-the-heckemahler-comparison-does-and-does-not-supply."></a>

#### What the Hecke–Mahler comparison does and does not supply.

In the published Luca–Ouaknine–Worrell article \[lucaouaknineworrell2025, Definition 5 and Theorem 6\], the same fixed integer coefficients are applied to shifts of one integer sequence. The resulting nonzero terms must have expanding gaps and uniform polynomial variation; the original sequence must also have polynomial growth. Theorem 6 then gives a fixed-base value criterion. Theorem 8 verifies that condition for $`f(\lfloor m\vartheta+\rho\rfloor)`$ when $`f\in\mathbb Z[x]`$ is nonconstant, $`\vartheta,\rho\in(0,1)`$ and $`\vartheta`$ is irrational. These interval restrictions belong to that normalised combinatorial statement. Their main value theorem, Theorem 1, allows every real $`\rho`$ and every irrational real $`\vartheta`$, with any algebraic base $`\beta`$ satisfying $`|\beta|>1`$. Claim 10 uses a finite difference of order $`\deg f+1`$, which vanishes when no floor crossing occurs. This is a polynomial evaluated at a floor, not merely an integer sequence of polynomial growth. Our $`m_a`$ is instead a weighted lattice count. Proposition <a href="#long269:res:strip-decomposition" data-reference-type="ref" data-reference="long269:res:strip-decomposition">29</a> separates floor crossings from its moving boundary, and Example <a href="#long269:res:no-crossing-counterexample" data-reference-type="ref" data-reference="long269:res:no-crossing-counterexample">30</a> shows that the latter can survive a cubic difference even with no crossings.

There is a second distinction. In our displayed shift identity the coefficient of $`m_{a+jr}`$ is $`15c_j\gamma_{a,jr}`$, which can depend on $`a`$. For example, $`P_1=2`$, $`P_2=12`$ and $`P_3=120`$ give $`\gamma_{0,1}=1/3`$ but $`\gamma_{1,1}=1/5`$. These factors are required by the denominator chain. A support estimate for $`D_{r,a}`$ is therefore not by itself a verification of Definition 5 for the sequence $`(m_a)`$. No fixed-coefficient representation to which that theorem applies has been established here.

For a variable-denominator analogue, a useful hypothesis would be a fixed choice of coefficients and shifts $`r_n\to\infty`$ for which $`\Delta_n=\{a\ge0:D_{r_n,a}\ne0\}`$ is infinite and distinct members are at least $`\eta r_n`$ apart, for a fixed $`\eta>0`$. Even this would leave the uniform polynomial-variation requirement, for example
``` math
|D_{r_n,a'}|\le C\bigl((a'-a)^d+|D_{r_n,a}|\bigr)
 \quad(a<a',\ a,a'\in\Delta_n),
```
with $`C,d`$ independent of $`n`$, $`a`$ and $`a'`$. This is a condition on the gaps between nonzero terms, not merely on their density: even a set of density zero can contain adjacent pairs. It also requires infinitely many nonzero terms for each selected shift. A small but nonzero term at every index would fail it, and an identically zero difference would also fail the infinitude requirement. The cited paper constructs suitable shifts for the polynomial-floor sequences just described; no such result is proved for our weighted counts. The bound $`O((a+r+1)^2)`$ controls absolute size: it depends on the location $`a`$ itself. The variation condition instead bounds a later nonzero term by the gap from an earlier one and the size of that earlier term, with constants uniform in the shift. The absolute-size bound alone gives no such comparison. The denominator chain itself is not a fixed-base power sequence. The next proposition shows what is lost in two direct fixed-base recodings. A value criterion for the original chain would need a separate proof, including non-cancellation and the height estimates in any Subspace-Theorem argument. Here height means Diophantine height, which controls the numerators and denominators of the approximating algebraic quantities, not the running-LCM height $`\operatorname{H}`$. The finite set of prime divisors alone does not provide those estimates.

<a id="why-a-finite-alphabet-of-bases-is-not-enough."></a>

#### Why a finite alphabet of bases is not enough.

Kebis, Luca, Ouaknine, Scoones and Worrell \[kebis2024echoing, Definition 3, Theorem 6 and Claim 7\] work with fixed-base series whose coefficients lie in a finite algebraic alphabet. Their echoing condition requires long near-repetitions, separated intervals containing the mismatches, and nonzero weighted mismatch sums on at least two of those intervals. Claim 7 supplies the non-cancellation step in the proof of the value theorem. Merely having finitely many letters does not give these properties. The four-letter radix sequence is not the numerator sequence: the actual $`m_a`$ is unbounded. A recoding would have to preserve the scalar value, identify its coefficient alphabet and verify the echoing conditions. No fixed-base recoding with verified echoing properties is proved here.

Two natural bases expose the tradeoff. The least integer base whose powers clear every $`P_n`$ is $`30`$, while base $`8`$ matches the growth of $`P_n=\operatorname{H}(2^n)`$. The former keeps integrality; the latter keeps polynomial size.

<div id="long269:res:fixed-base-recoding" class="proposition">

**Proposition 31** (what direct fixed-base recoding preserves). *The following identities converge absolutely:
``` math
\alpha=\sum_{a\ge0}\frac{e_a}{30^{a+1}}
        =\sum_{a\ge0}\frac{v_a}{8^{a+1}},\qquad
 e_a=\frac{m_a30^{a+1}}{P_{a+1}},\quad
 v_a=\frac{m_a8^{a+1}}{P_{a+1}}.
```
Here $`e_a\in\mathbb Z_{>0}`$ and $`e_a\ge(15/4)^{a+1}`$, whereas $`v_a\in\mathbb Z[1/15]`$ and $`0<v_a<225(a+1)^2`$. For an integer $`q\ge2`$, the termwise divisibility $`P_n\mid q^n`$ for every $`n\ge1`$ holds exactly when $`30\mid q`$; that direct recoding then has coefficients at least $`(q/8)^{a+1}`$.*

</div>

<div class="proof">

*Proof.* Each exponent in $`P_n`$ is at most $`n`$, so $`P_n\mid30^n`$. The estimate $`8^n/15<P_n\le8^n`$ was proved in Section <a href="#long269:sec:blocks" data-reference-type="ref" data-reference="long269:sec:blocks">5</a>. These facts, $`m_a\ge1`$ and $`m_a\le15(a+1)^2`$, give all the coefficient bounds and identities. Necessity of $`30\mid q`$ follows because each of $`2,3,5`$ divides some $`P_n`$; sufficiency follows from $`P_n\mid30^n`$. The general lower bound follows again from $`P_n\le8^n`$. ◻

</div>

The base-$`30`$ coefficients are integral but grow exponentially, so the cited polynomial-growth criterion does not apply. The base-$`8`$ coefficients have polynomial size but are not all integral: already $`v_1=4\cdot8^2/12=64/3`$. In fact, their reduced denominators grow exponentially even after cancellation. Since $`P_{a+1}/2^{a+1}`$ is odd, the expression
``` math
v_a=\frac{m_a4^{a+1}}{P_{a+1}/2^{a+1}}
```
can cancel an odd factor only through $`m_a`$. Consequently,
``` math
\operatorname{den}(v_a)
 \ge \frac{P_{a+1}}{2^{a+1}m_a}
 >\frac{4^{a+1}}{225(a+1)^2}.
```
The last inequality uses $`P_{a+1}>8^{a+1}/15`$ and $`m_a\le15(a+1)^2`$. Thus the bound on absolute value does not control Diophantine height even for these particular coefficients; fixed denominator-prime support is not enough.

More generally, no fixed integer base gives this termwise recoding both eventually integral coefficients and polynomial growth. If $`30\mid q`$, the proposition gives exponential growth. Otherwise choose $`p\in\{2,3,5\}`$ not dividing $`q`$. Cancellation by $`m_a`$ removes at most a factor $`m_a`$, so
``` math
\operatorname{den}\!\left(\frac{m_aq^{a+1}}{P_{a+1}}\right)
 \ge\frac{p^{\lfloor(a+1)\log_p2\rfloor}}{m_a}
 >\frac{2^{a+1}}{15p(a+1)^2}.
```
This denominator tends to infinity. The argument concerns only the displayed termwise rescaling, not regrouping or carrying.

Carrying can in fact make the coefficients into digits, while leaving the radices variable. To see exactly what changes, set
``` math
\delta_a=m_a+\lfloor X_{a+1}\rfloor-b_a\lfloor X_a\rfloor
          =\lfloor b_a\{X_a\}\rfloor.
```
The equality follows from the tail recurrence and $`m_a\in\mathbb{Z}`$. Thus $`0\le\delta_a<b_a`$ and $`\{X_a\}=(\delta_a+\{X_{a+1}\})/b_a`$. Iterating gives the finite identity
``` math
\{X_0\}=\sum_{a=0}^{N-1}\frac{\delta_a}{P_{a+1}}
              +\frac{\{X_N\}}{P_N}.
```
The last term is nonnegative, is less than $`1/P_N\le2^{-N}`$, and tends to zero. This is the greedy mixed-radix expansion of the fractional part of $`X_0=S/2`$, with digits in $`\{0,\ldots,29\}`$. For the actual series its first eight digits are
``` math
(\delta_0,\ldots,\delta_7)=(1,4,8,3,10,1,8,5).
```
To certify them, use the twelve-shell enclosure from Section <a href="#long269:sec:evidence" data-reference-type="ref" data-reference="long269:sec:evidence">8</a>, either propagated by the recurrence or evaluated directly as
``` math
P_a\sum_{j=a}^{11}\frac{m_j}{P_{j+1}}<X_a
 \le P_a\sum_{j=a}^{11}\frac{m_j}{P_{j+1}}
       +\frac{P_a}{P_{12}}Q(n_{12})\qquad(0\le a<12).
```
Both descriptions give the same rational endpoints. At indices $`0`$ through $`8`$ the whole interval lies strictly between consecutive integers, which certifies the floor; a small interval width alone would not suffice if the interval crossed an integer. For example, $`\lfloor X_4\rfloor=2`$ and $`\lfloor X_5\rfloor=5`$, giving $`\delta_4=65+5-30\cdot2=10`$, not the uncarried numerator $`m_4=65`$. This finite calculation makes no claim about the later digit complexity.

A rational number need not have eventually periodic digits when the radices vary. For example, take radix $`5`$ at the indices $`1,2,4,8,\ldots`$ and radix $`3`$ elsewhere. The constant tail fraction $`1/2`$ gives digit $`2`$ at those indices and $`1`$ elsewhere. These digits are not eventually periodic, but their mixed-radix expansion sums to $`1/2`$. This example uses different radices from our four possible bases; it shows why fixed-base eventual periodicity cannot be transferred to a variable-radix expansion. Our digits also depend on the actual tail fractions, not just on the four-letter radix sequence. The construction supplies neither a fixed-base expansion with verified echoing properties nor a bound on its digit complexity.

Adamczewski–Bugeaud’s complexity theorem \[adamczewskibugeaud2007, Theorem 1\] concerns the actual digits of an integer-base expansion: for an algebraic irrational their length-$`n`$ block complexity divided by $`n`$ tends to infinity. Neither $`(b_a)`$ nor the uncarried $`(e_a)`$ is such a digit expansion of $`\alpha`$.

<div id="long269:prob:producer" class="problem">

**Problem 32** (the repeated three-prime target). <span id="long269:prob:tails269" label="long269:prob:tails269"></span> Prove irrationality of $`S=\mathcal R_{\{2,3,5\}}`$. Equivalent forms are $`\mathsf E(K)`$ and
``` math
\begin{equation}
\label{long269:eq:tail-nonintegrality}
 BX_a\notin\mathbb Z
 \quad\text{for every }B\ge1\text{ with }\gcd(B,30)=1\text{ and every }a\ge1.
\end{equation}
```

</div>

The residue formulation uses finite integer computations, but asks for a success for every eligible denominator and beyond every prescribed start. The tail formulation requires that no positive integer multiplier coprime to $`30`$ make any $`X_a`$, $`a\ge1`$, integral. These are reformulations of the same irrationality assertion, not extra assumptions on the series, and neither follows from the rank obstruction. The next proposition proves the tail reformulation, complementing Theorem <a href="#long269:res:actual-escape-endpoint" data-reference-type="ref" data-reference="long269:res:actual-escape-endpoint">24</a>.

<div id="long269:res:tails-equivalence" class="proposition">

**Proposition 33** (irrationality is equivalent to nonintegrality of every reduced tail). *Statement <a href="#long269:eq:tail-nonintegrality" data-reference-type="eqref" data-reference="long269:eq:tail-nonintegrality">[long269:eq:tail-nonintegrality]</a>, quantified over every $`B\ge1`$ coprime to $`30`$ and every $`a\ge1`$, is equivalent to irrationality of $`S`$.*

</div>

<div class="proof">

*Proof.* If $`BX_a\in\mathbb{Z}`$ for some such $`B`$ and $`a`$, then $`X_a\in\mathbb{Q}`$, and since $`S=\sum_{j<a}s_j+X_a/h_a`$ with $`h_a`$ a positive rational and the prefix a finite sum of rationals, $`S\in\mathbb{Q}`$. Conversely if $`S\in\mathbb{Q}`$, then Theorem <a href="#long269:res:actual-cancellation" data-reference-type="ref" data-reference="long269:res:actual-cancellation">19</a> produces $`B`$ coprime to $`30`$ with $`BX_a\in\mathbb{Z}`$ for every $`a\ge a_D`$. ◻

</div>

Integrality at one index propagates forwards, but nonintegrality at one early index does not propagate forever: a rational denominator can clear later. Proposition <a href="#long269:res:exact-denominator" data-reference-type="ref" data-reference="long269:res:exact-denominator">20</a> describes that onset exactly. The dichotomy in Proposition <a href="#long269:res:actual-dichotomy" data-reference-type="ref" data-reference="long269:res:actual-dichotomy">16</a> also permits integral tails, so it does not settle this question.

<a id="what-a-function-theoretic-proof-would-require"></a>

## What a function-theoretic proof would require

This subsection concerns a different sum: each height is now counted once, at the jump where it first appears. Put
``` math
\mathcal D_{2,3,5}=1+
 \sum_{t\in\{2^{n},3^{n},5^{n}:n\ge1\}}
 \frac{1}{2^{\lfloor\log_2t\rfloor}3^{\lfloor\log_3t\rfloor}
           5^{\lfloor\log_5t\rfloor}}.
```
The same prime-power jumps determine the bases $`b_a`$ in <a href="#long269:eq:dyadic-alphabet" data-reference-type="eqref" data-reference="long269:eq:dyadic-alphabet">[long269:eq:dyadic-alphabet]</a>, but this sum counts each height once, not once for every smooth integer at that height.

<div id="long269:prob:representation" class="problem">

**Problem 34** (an exact function representing the distinct-height sum). The historical irrationality assertion for $`\mathcal D_{2,3,5}`$ is not being reclassified as a new open problem. A recovered proof or a transcendence theorem would require its own argument. For a functional approach, first specify the function, its coefficient field and convergence domain, then prove an exact identity for $`\mathcal D_{2,3,5}`$, and only then apply a stated value theorem. A conditional theorem must display the extra nondegeneracy assumption; a no-representation theorem must specify the class it excludes.

</div>

For $`(p,q,r)=(2,3,5)`$, the two slopes in the rank proof are $`\log_5 2=\theta_5`$ and $`\log_5 3=\theta_5/\theta_3`$, not $`\theta_3`$ and $`\theta_5`$. Each is irrational: a rational value would equate a positive power of $`5`$ with a positive power of $`2`$ or $`3`$. The proof chooses the row and column indices independently. It therefore needs no rational independence of $`1,\theta_3,\theta_5`$ and no density assertion for the singly indexed orbit $`(\{n\theta_3\},\{n\theta_5\})`$. Any functional approach that needs such a stronger hypothesis must establish it separately.

A finite-dimensional encoding must preserve equality of the functions it is meant to represent. If two encodings agree but their functions do not, the encoding cannot justify a conclusion about those functions. The supplied formal sources express this condition as a factorisation through a finite-dimensional space and prove that the resulting space of functions is then finite-dimensional ([identity for the carry](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L109), [map to functions](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L293), [finite-dimensional conclusion](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L334)). They also bound the carry residue and its digit in their stated intervals ([residue bound](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L150), [digit bound](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L157)). These conditional linear-algebra statements neither construct a function representing $`\mathcal D_{2,3,5}`$ nor show that a corresponding function space must be infinite-dimensional.

<a id="the-cited-value-theorems-and-their-hypotheses."></a>

#### The cited value theorems and their hypotheses.

Pellarin’s rank-one theorem concerns quadratic irrational slopes and algebraic evaluation points in the convergence domain \[pellarin2006, Theorem 1.1 and Remark 1.2, pp. 330–332\]. The prime-logarithm slopes used here are not quadratic: each $`\log_r p`$ is irrational by unique factorisation, and the Gelfond–Schneider theorem then makes it transcendental, since $`r^{\log_r p}=p`$ is algebraic.[^1] This rules out direct substitution of those slopes into Pellarin’s quadratic-slope theorem. It does not rule out a different representation of the scalar sum, and it does not affect the two-prime argument above, which uses a theorem for general irrational slopes.

In Pellarin’s reduced-slope normalisation, the rank-one condition says that the evaluation points arise from a common point by the quadratic order’s monomial action, up to multiplication by torsion points. For a single evaluation point it is automatic: use that point itself and the identity action. For several points it is a condition to check, not a consequence of having two lattice coordinates. Under it, algebraic independence of the values is equivalent to $`\mathbb{Q}`$-linear independence of the specified auxiliary formal Laurent series; the rank-one condition alone does not imply independence. This module rank is not the rank of our reciprocal kernel. No exact representation suitable for this theorem has been constructed here, but infinite kernel rank alone does not preclude one.

For one variable, Adamczewski and Faverjon’s proofs of Nishioka’s theorem and the lifting theorem are regular-point results \[adamczewskifaverjon2023, Theorems 1 and 2\]. Regularity means that the system matrix stays defined and invertible along the evaluation orbit. Their multivariate lifting theorem \[adamczewskifaverjon2026, Theorem 3.3\] additionally assumes an admissible transformation–point pair. Its growth, decay and nonvanishing conditions are specified in Definition 5.1; none follows merely from writing a double sum. Lifting transfers a relation among values to one among functions; a transcendence application must exclude the latter. A Mahler system alone cannot do this, as the constant function $`1`$ illustrates.

Regularity of a preselected system is not, however, a universal prerequisite for Mahler’s method. The same paper’s Theorem 1.1 treats univariate Mahler functions at algebraic points in the punctured unit disc where their values are defined, without that regularity hypothesis. The hypotheses must therefore be matched to the particular theorem being invoked. No exact Mahler representation or suitable evaluation data for this distinct-height sum are constructed here. The locators for this paper refer to its 68-page author manuscript, not the older 52-page arXiv version.

<a id="what-the-auxiliary-carry-results-assume"></a>

## What the auxiliary carry results assume

The finite set of possible bases extends to any finite list of primes. For ordered primes $`p_1<\cdots<p_s`$ an interval $`(p_1^{a},p_1^{a+1})`$ contains at most one power of each other prime, because consecutive $`p_i`$-powers have ratio $`p_i>p_1`$, so its block radix belongs to the $`2^{s-1}`$-letter alphabet $`\{p_1\prod_{i=2}^{s}p_i^{\varepsilon_i}:\varepsilon_i\in\{0,1\}\}`$. This observation does not give the frequencies or spacing of the bases. An irrationality proof might need estimates for those frequencies, an asymptotic formula with an error term for the weighted shell counts, or information about the kernel after a specified family of shifts.

Some auxiliary results explain why bounded integer approximations alone are insufficient. Here are their hypotheses in explicit form.

Let $`j(n)\in\{2,3,5\}`$ label a sequence of jumps, and suppose each label occurs. A perturbation $`\varepsilon_n`$ in an additive abelian group has sum zero on every interval $`[a,b)`$ whose endpoints have the same label exactly when
``` math
\varepsilon_n=u(j(n+1))-u(j(n))
```
for three potential values $`u(2),u(3),u(5)`$. One direction follows by telescoping. Conversely, the zero-sum assumption makes $`\sum_{k<n}\varepsilon_k`$ the same at any two indices with the same label. Assign that common value to $`u(j(n))`$; every label occurs, so all three values are defined. Consecutive partial sums then give the displayed identity. In the usual terminology, the perturbation is a coboundary of the function $`u`$ on the labels: it is the difference of successive potential values. This is a telescoping condition, not a bound on the size of the perturbation. It does not by itself force the perturbation to vanish: unequal potential values give nonzero differences when the label changes. If the perturbation also vanishes on a genuine $`2\to3`$ transition and on a genuine $`2\to5`$ transition, all three potential values agree, so every perturbation is zero.

For an integer carry satisfying $`c_{n+1}=b_nc_n-Dm_n`$, compare it with an integer sequence $`z_n`$. Define the error $`e_n=Dz_n-c_n`$ and the perturbation $`\varepsilon_n=b_nz_n-z_{n+1}-m_n`$. Then
``` math
e_{n+1}=b_ne_n-D\varepsilon_n.
```
Under the preceding zero-sum and transition hypotheses, $`\varepsilon_n=0`$ and hence $`e_N=(\prod_{n<N}b_n)e_0`$. If every $`b_n\ge2`$ and the integer $`e_0`$ is nonzero, then $`|e_N|\ge2^N`$. This contradicts even one bound $`|e_N|<2^N`$, and therefore also excludes a uniform bound for all $`N`$. The nonzero initial error is essential: the identically zero error causes no contradiction.

A calculation on four states gives a related obstruction. If $`0<T_i<1`$, $`z_i\in\mathbb{Z}`$ and $`|z_i-T_i|<1`$, then $`z_i`$ is $`0`$ or $`1`$. For bases $`2,3,2,5`$, the equalities $`2z_0-z_1-1=0`$ and $`2z_2-z_3-1=0`$ force all four integers to be $`1`$. The sum of the first two perturbations is then
``` math
(2z_0-z_1-1)+(3z_1-z_2-1)=1,
```
not zero. Thus unit accuracy, the two exact equalities and a zero sum on that block cannot all hold. Unit accuracy alone does not give either exact equality.

No integer approximation to the tails of $`S`$ is constructed here that satisfies all these conditions. Rationality supplies integer carries of at most quadratic growth, but not the additional zero-sum and transition identities. The carries obtained from $`S`$ satisfy a weighted block identity instead. Applying the auxiliary results would require that identity to imply their hypotheses, or would require a different construction of the integer approximations.

There is also a conditional criterion for a sum supported on the powers of $`2`$. Its elementary ingredients can be stated without introducing another formal vocabulary. From $`y'=by-1`$ with $`b>0`$ and $`0<y'<1`$ one gets $`1/b<y<2/b`$. For integers $`a>0`$ and $`p\ge3`$, if $`u>1/a`$ and $`v<2/(pa)`$, then $`u-v>1/(3a)`$. Finally, a real number $`x`$ is irrational if, for every positive integer $`d`$, there are integers $`n,k`$ with $`0<|nx-k|<1/d`$.

To use these observations for a series, the supplied conditional result requires exact identities $`y_M=H_Mx-z_M`$, with $`H_M,z_M\in\mathbb{Z}`$, and, for every positive $`d`$, two indices with different $`H_M`$, different $`y_M`$, and $`|y_M-y_{M'}|<1/d`$. Their difference gives the required nonzero linear form. Equal states would give zero and would not suffice; a merely bounded gap would not suffice either. Indeed, for a rational $`x`$ of denominator $`d`$, every nonzero difference of this form has size at least $`1/d`$. No concrete series in this record is shown to satisfy all these clearing and arbitrarily small nonzero-gap conditions.

<a id="where-the-problem-stands"></a>

## Where the problem stands

For the repeated $`\{2,3,5\}`$ sum, the coefficients, recurrence, quadratic bounds and denominator clearing are derived here from the original multiplicities. What remains is to exclude eventual integral reduced tails, equivalently to prove residue escape for every admissible denominator and beyond every prescribed starting index. The fixed-start residue formula explains these quantifiers, and the strip decomposition shows why absence of floor crossings alone does not give the required cancellation.

The rank and uniform-norm results concern the kernel, not the arithmetic of its sum. Finite tests, countability, radix recoding and denominator support do not close the remaining argument. The settled two-prime case uses Fan’s earlier reduction to the cited Hecke–Mahler value theorem.

<a id="statements-and-declarations"></a>

## Statements and declarations

<a id="proof-sources."></a>

#### Proof sources.

The two-prime deduction rests on the cited external value theorem and is not formalised here. Fan’s priority is retained from the supplied forum record. The live thread and catalogue could not be rechecked for this revision; no new claim about their current status is made. The supplied `LEAN_INDEX.json` labels selected declarations `ci_checked`, including results on arbitrary-order rank, the tail recurrence, the scaled integrality dichotomy, denominator clearing, the two quadratic bounds and the residue criterion for bounds of size $`o(8^a)`$. Its public source snapshot is `6b78209a`, while its build record names an earlier compiled revision, `6fdb8a20`, and marks the pinned build step as skipped. These records are not a fresh build of all the attached files. The separate Palomar release at `52f29ad1` selects arbitrary-order uniform-minor and prime non-separation statements as well as the finite example; its selection is not limited to a $`2\times2`$ determinant. This revision did not run Lean, Isabelle, Comparator or NanoDa, and did not independently verify the inherited build coverage. An index entry is not a complete axiom audit. The original source links retain their historical revisions, not the newer snapshot.

The weighted-triangle and weighted-shift identities, exact denominator formula, scaled dichotomy, uniqueness argument, residue limit, strip decomposition and direct recoding proposition have ordinary proofs here. The independent integer computations check finite instances, not infinite quantifiers; they are not new formalisation results. The twelve-shell rational enclosure, denominator bound and eight mixed-radix digits have the exact finite proofs given above. The large numerical exclusions remain unverified reports because their witnesses are unavailable. None of these records proves escape beyond every prescribed starting index.

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

The [historical source revision](https://github.com/wcook04/plectis-erdos/tree/ee650b32b8b2cb98b94e5500df5370d85f7403b8) is the original repository reference for the formal sources and the dyadic-window checker. The attached Lean files and index permit source inspection, but not every historical dependency or computation is included. The formal evidence applies only to the statements identified in the source index. Ordinary proofs and external analytic inputs have their own stated dependencies; the unavailable numerical witnesses are not supplied by a repository link.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.

<a id="authorship-and-review."></a>

#### Authorship and review.

Will Cook directed the work. AI agents did most of the research and drafting. Cook has not independently verified every mathematical claim, and these manuscripts have not had independent human mathematical review.

<a id="acknowledgements."></a>

#### Acknowledgements.

We thank Wouter van Doorn for advice on exposition: reducing private terminology, removing unnecessary notation, and explaining the strength of conditional hypotheses. His comments concerned a different manuscript, on Erdős #243; this acknowledgement does not attribute mathematical review or endorsement of the present work to him. Steve Fan’s forum post of 26 June 2026 supplied the two-prime factorisation and its Hecke–Mahler reduction before this manuscript; it also records the elementary running-LCM identity for finite prime sets \[fan2026comment\]. The transcendence input is due to Yann Bugeaud and Michel Laurent and to the earlier work of Loxton and van der Poorten cited by them. The problem numbering and historical status snapshot are taken from the Erdős Problems catalogue maintained by Thomas Bloom \[erdosproblems\].

<a id="long269:long:extended"></a>

# Further examples, conditional lemmas and source references

This section collects the historical details, the integer recurrence lemmas in their general form, worked examples and the original formal source links. The reported large computations remain unverified here.

<a id="long269:long:history"></a>

## The historical and catalogue record

For $`P=\{p\}`$, the enumeration is $`a_n=p^{n-1}`$, so $`[a_1,\ldots,a_n]=p^{n-1}`$ and both sums equal $`p/(p-1)`$. In the primary 1988 source Erdős states irrationality for infinite $`P`$ as a simple exercise and presents persistence for a finite number of primes greater than one as a probable extension, not a theorem \[erdos1988, p. 106\]. The catalogue snapshot cited in the supplied manuscript records an open problem \[erdosproblems\]; that historical status is not inferred from the conjectural wording and has not been reverified against the live page for this revision. In the letter written on 1 January 1973 and published in 1974, Erdős says he can prove irrationality of the distinct-height sum \[erdos1974letter, p. 335\]. He writes “given primes $`p_1,\ldots,p_r`$” without restricting $`r`$, so the singleton calculation forces the qualification $`|P|\ge2`$. The assertion is made for a general finite list of primes and supplies no proof. We record it as an attributed historical assertion rather than present $`\mathcal D_P`$ as a newly identified open case. The note’s unresolved target is the repeated series $`\mathcal R_P`$. A recovered proof of the letter’s assertion, or a transcendence statement for $`\mathcal D_P`$ with $`|P|\ge3`$, would be a different question and needs its own formulation.

The letter prints no argument. On 26 June 2026 Steve Fan posted the two-prime factorisation, the Hecke–Mahler reduction and the transcendence conclusion in the discussion thread of the problem’s page \[fan2026comment\]; the comment itself notes that the argument does not seem to generalise immediately to $`|P|\ge3`$, and a reply there observes that it applies to arbitrary coprime pairs. The supplied publication record dates the note’s first public manuscript to 22 July 2026, at commit `a9d3ab8`, after Fan’s post. We retain the calculation as exposition and make no priority claim for it.

The statement of the problem has been formalised as a conjecture with an unfilled proof in the *Formal Conjectures* collection \[formalconjectures269\]. In the cited source, the rational, irrational and infinite-prime assertions end in `sorry`. Its Nat-indexed series includes the empty-prefix least-common-multiple term, so its value differs from the conventional one by a rational constant; transporting a theorem across that boundary needs an explicit series-identification lemma, which is not supplied here.

<a id="long269:long:general-carries"></a>

## The abstract carry lemmas in their general form

The earlier argument used carries obtained from the actual $`\{2,3,5\}`$ sum. The following statements instead concern arbitrary integer recurrences. Divisibility and escaping windows are explicit hypotheses. For general radices they need separate justification; for the actual radices, the divisibility criterion below shows that every integral carry acquires the smooth factor eventually. This does not supply escaping windows. The Cantor-series comparison is in Section <a href="#long269:sec:actual-orbit" data-reference-type="ref" data-reference="long269:sec:actual-orbit">6</a>.

Let $`D`$ and $`B`$ be positive integers with $`D=D_{\mathrm{sm}}B`$, where $`D_{\mathrm{sm}}=2^u3^v5^w`$, $`u,v,w\in\mathbb{N}`$ and $`\gcd(B,30)=1`$. Let $`(c_n)`$ be an integer sequence satisfying $`c_{n+1}=b_nc_n-Dm_n`$ for integer sequences $`(b_n)`$ and $`(m_n)`$. For these general sequences, form $`W`$ and $`F`$ by the recursions in Section <a href="#long269:sec:escape" data-reference-type="ref" data-reference="long269:sec:escape">7</a>; an escaping window must have $`W\ne0`$, and its modulus is $`|W|`$. In the factorisation below the quotients $`d_n`$ are required to be integers; writing $`c_n=D_{\mathrm{sm}}d_n`$ asserts divisibility, not just an identity in $`\mathbb Q`$.

<div id="long269:long:denominator-reduction" class="proposition">

**Proposition 35** (conditional denominator reduction). *If $`c_n=D_{\mathrm{sm}}d_n`$ for every $`n`$, with $`D_{\mathrm{sm}}>0`$, then the recurrence and window identity for $`(d_n)`$ have multiplier $`B`$ in place of $`D`$. Moreover, for every $`n`$ and every real $`t`$,
``` math
0<c_n\le Dt\quad\Longleftrightarrow\quad0<d_n\le Bt.
```*

</div>

<div class="proof">

*Proof.* Substitute $`c_n=D_{\mathrm{sm}}d_n`$ and $`D=D_{\mathrm{sm}}B`$ in the recurrence and divide by $`D_{\mathrm{sm}}`$. Dividing $`0<c_n\le D_{\mathrm{sm}}Bt`$ by this positive factor gives the stated bound equivalence. Dividing the window identity $`c_{\ell+h}=W_{\ell,h}c_\ell-DF_{\ell,h}`$ likewise gives $`d_{\ell+h}=W_{\ell,h}d_\ell-BF_{\ell,h}`$. ◻

</div>

For a general bound $`c_n\le G(D,n)`$, division and integrality give only
``` math
d_n\le\left\lfloor\frac{G(D,n)}{D_{\mathrm{sm}}}\right\rfloor,
```
not automatically $`d_n\le G(B,n)`$. The bounds used for the actual tails are linear in the multiplier before rounding. For any real $`t`$,
``` math
\left\lfloor\frac{\lfloor Dt\rfloor}{D_{\mathrm{sm}}}\right\rfloor
 =\lfloor Bt\rfloor.
```
Indeed, an integer $`z`$ satisfies $`D_{\mathrm{sm}}z\le\lfloor Dt\rfloor`$ exactly when $`D_{\mathrm{sm}}z\le Dt`$, or $`z\le Bt`$. Thus rounding does not change the reduced bound in this case.

Growth of the radix product is not enough: $`b_n=3`$, $`m_n=1`$, $`D=2`$ and $`c_n=1`$ satisfy the recurrence, but $`2`$ never divides $`c_n`$. The precise condition follows by reducing the recurrence modulo $`D_{\mathrm{sm}}`$. For any starting index $`A`$ and every $`n\ge A`$,
``` math
\begin{aligned}
 c_n&\equiv\left(\prod_{j=A}^{n-1}b_j\right)c_A
       \pmod{D_{\mathrm{sm}}},\\
 D_{\mathrm{sm}}\mid c_n
 &\quad\Longleftrightarrow\quad
 \frac{D_{\mathrm{sm}}}{\gcd(D_{\mathrm{sm}},c_A)}
       \mid\prod_{j=A}^{n-1}b_j.
 \end{aligned}
```
The congruence is an induction, since $`D_{\mathrm{sm}}\mid D`$. For the equivalence, cancel the positive greatest common divisor; the remaining factor of $`c_A`$ is coprime to the remaining modulus. Thus it is growth of the required prime valuations, not growth of the product as a real number, that ensures divisibility.

For the actual radices the product is $`P_n/P_A`$. Its valuations at $`2,3,5`$ all tend to infinity, so every fixed $`D_{\mathrm{sm}}`$ eventually divides $`c_n`$, for any integral initial carry $`c_A`$. Under rationality $`S=N/D`$ in lowest terms, one may start at $`A=1`$: $`c_1=DX_1=N-D`$ is integral and coprime to $`D_{\mathrm{sm}}`$. Since $`P_1=2`$, the criterion becomes $`D_{\mathrm{sm}}\mid P_n/2=h_n`$, exactly the onset already obtained from the finite-prefix identity in Proposition <a href="#long269:res:exact-denominator" data-reference-type="ref" data-reference="long269:res:exact-denominator">20</a>. This is an alternative proof of the divisibility step, not an additional arithmetic hypothesis left to verify for $`S`$. The finite-prefix proof in Theorem <a href="#long269:res:actual-cancellation" data-reference-type="ref" data-reference="long269:res:actual-cancellation">19</a> remains valid.

<div id="long269:long:windowconsumer" class="proposition">

**Proposition 36** (escaping windows exclude a positive bounded integer solution). *Let $`(b_n)`$ and $`(m_n)`$ be sequences of nonnegative integers, let $`G:\mathbb{N}_{>0}\times\mathbb{N}\to\mathbb{N}`$, and assume the residue condition <a href="#long269:eq:actual-escape" data-reference-type="eqref" data-reference="long269:eq:actual-escape">[long269:eq:actual-escape]</a> for these sequences and $`G`$, using $`|W_{\ell,h}|>0`$ as the modulus. Fix $`B>0`$ coprime to $`30`$. There is no integral sequence $`(d_n)`$ satisfying simultaneously $`d_{n+1}=b_nd_n-Bm_n`$, $`d_n>0`$ and $`|d_n|\le G(B,n)`$ for every $`n\ge0`$.*

</div>

<div class="proof">

*Proof.* Choose one escaping window $`(\ell,h)`$. The window identity gives $`d_{\ell+h}\equiv-BF_{\ell,h}`$ modulo $`|W_{\ell,h}|`$. The endpoint state is positive and at most $`G(B,\ell+h)`$, whereas the least positive residue of the right-hand side exceeds that bound, so Proposition <a href="#long269:res:consumer" data-reference-type="ref" data-reference="long269:res:consumer">23</a> applies. ◻

</div>

The escape hypothesis is the substantial arithmetic assumption. It requires a residue above the bound, not just a rapidly growing product of bases. For example, the constant data $`b_n=2`$, $`m_n=1`$ have the positive solution $`d_n=B`$. For any bound $`G(B,n)\ge B`$, every window has $`W=2^h`$, $`F=2^h-1`$ and least positive residue at most $`B`$, so the hypothesis fails. For the actual three-prime coefficients and $`G=K`$, Theorem <a href="#long269:res:actual-escape-endpoint" data-reference-type="ref" data-reference="long269:res:actual-escape-endpoint">24</a> makes the escape hypothesis equivalent to irrationality of $`S`$. That equivalence does not hold for an arbitrary choice of $`G`$.

Coprimality with $`30`$ selects the denominators covered by the hypothesis; once a window is fixed, the finite contradiction does not use it. The conventions cover the edge cases: a zero window base is excluded, a zero residue is represented by the full modulus, and positivity prevents the endpoint carry from vanishing. The version stated with a nonzero smooth factor assumes the exact factorisation $`c_n=D_{\mathrm{sm}}d_n`$, the corresponding recurrence for $`(c_n)`$ and the positive upper bound for $`(d_n)`$, and gives the same contradiction.

Even retaining the actual radix sequence and quadratic growth does not force irrationality if the numerators are changed. For the same $`b_a`$, prescribe the positive integer carries $`(a+3)^2`$ and set
``` math
\widehat m_a=b_a(a+3)^2-(a+4)^2.
```
The shift by three ensures positivity even at $`a=0`$: since $`b_a\ge2`$,
``` math
\widehat m_a\ge2(a+3)^2-(a+4)^2=a^2+4a+2>0.
```
Both these integer coefficients and the prescribed carries have quadratic order, because $`2\le b_a\le30`$. Nevertheless, finite telescoping gives
``` math
\sum_{a=0}^{N-1}\frac{\widehat m_a}{P_{a+1}}
 =9-\frac{(N+3)^2}{P_N}\longrightarrow9.
```
This example keeps the exact radices, not the actual shell multiplicities or their numerical upper bound $`Q`$. It shows why the arithmetic of the specific $`m_a`$, rather than the radix alphabet and growth orders alone, must enter a proof for $`S`$.

<a id="long269:long:finite-geometry"></a>

## Worked finite examples

The values of the running least common multiple at the first ten integer cutoffs are tabulated in Section <a href="#long269:sec:lcm" data-reference-type="ref" data-reference="long269:sec:lcm">2</a>. They illustrate both parts of Proposition <a href="#long269:res:cell" data-reference-type="ref" data-reference="long269:res:cell">3</a>: the value is constant on $`\{5,6,7\}`$ and on $`\{9,10\}`$, and each change multiplies by a single prime, by $`2`$ at $`x=2,4,8`$, by $`3`$ at $`x=3,9`$ and by $`5`$ at $`x=5`$. Also $`\operatorname{L}(10)=8\cdot9\cdot5=360`$ is the least common multiple of the smooth numbers $`1,2,3,4,5,6,8,9,10`$.

For Proposition <a href="#long269:res:fibre" data-reference-type="ref" data-reference="long269:res:fibre">5</a> take $`(p,q,r)=(2,3,5)`$ and the box $`\mathcal B(1,1,1)`$, whose eight points carry the smooth values $`1,2,3,5,6,10,15,30`$ and the heights
``` math
\begin{array}{c|cccccccc}
p^{i}q^{j}r^{k}&1&2&3&5&6&10&15&30\\ \hline
\operatorname{H}&1&2&6&60&60&360&360&10800
\end{array}
```
Six heights occur, two of them twice: the points $`5`$ and $`6`$ share the height $`60`$, and $`10`$ and $`15`$ share the height $`360`$. The identity reads
``` math
1+\tfrac12+\tfrac16+\tfrac1{60}+\tfrac1{60}+\tfrac1{360}+\tfrac1{360}
 +\tfrac1{10800}
 =1+\tfrac12+\tfrac16+\tfrac2{60}+\tfrac2{360}+\tfrac1{10800}
 =\tfrac{18421}{10800},
```
and the two coefficients $`2`$ carry the whole content of the regrouping on this box. Where the heights are pairwise distinct the identity is a relabelling.

Multiplying block radices along a run of blocks gives the product of the prime multipliers at the jumps in that run: for instance $`b_1b_2=60`$ is the product of the four multipliers at $`3,4,5,8`$. Block $`4`$ is the only one among the first six containing an internal power of each odd prime, whereas block $`5`$ contains neither, so its radix falls back to the terminal factor alone.

<a id="long269:long:experiments"></a>

## The finite-scan histogram

The archived scan report described in Section <a href="#long269:sec:evidence" data-reference-type="ref" data-reference="long269:sec:evidence">8</a> claims coverage of $`B\le5000`$ coprime to $`30`$ and $`100\le\ell\le3000`$, with search depth $`24`$. It reports $`3{,}869{,}934`$ pairs, an escape in every case, and the following first-success histogram. These figures were not rerun for this revision and are retained as historical data:
``` math
\resizebox{\linewidth}{!}{$\begin{array}{c|rrrrrrrrrrrrrrr}
h&4&5&6&7&8&9&10&11&12&13&14&15&16&17&18\\ \hline
\#&1&104&812&5437&51409&237423&735450&1431226&1132756&236752&34910&3076&521&49&8
\end{array}$}
```
The first reported case attaining the maximal observed length $`18`$ has $`B=917`$ and $`\ell=2980`$. An earlier archived run over $`B\le1000`$ coprime to $`30`$ and $`100\le\ell\le500`$ reports $`106{,}666`$ pairs and maximal first successful length $`14`$, first attained at $`B=359`$ and $`\ell=291`$. The two reported cases have the following data; neither underlying scan was reproduced for this revision.

<div class="center">

|                        |                Later report |        Earlier report |
|:-----------------------|----------------------------:|----------------------:|
| Denominator $`B`$      |                     $`917`$ |               $`359`$ |
| Start $`\ell`$         |                    $`2980`$ |               $`291`$ |
| Length $`h`$           |                      $`18`$ |                $`14`$ |
| Endpoint jump index    |                    $`6179`$ |               $`627`$ |
| Window base            |       $`18139852800000000`$ |     $`5038848000000`$ |
| Accumulated numerator  | $`13196471407660025821045`$ | $`25864575212865807`$ |
| Least positive residue |             $`76322101735`$ |         $`213175287`$ |
| Upper bound            |              $`3896420420`$ |          $`15932659`$ |

</div>

These histograms concern a bounded region. The window-growth law gives a necessary lower bound on a possible escape length, not a distribution law for residues or first successful lengths. No generic-residue model is used as evidence for cofinal escape.

<a id="long269:long:sources"></a>

## Source inventory

Each entry pairs a mathematical statement with its original Lean source link. Declaration names are retained here for lookup, not introduced as mathematical terminology. These links keep their original immutable revisions. The supplied index describes a newer snapshot and inherited build evidence, as explained above; agreement between the revisions must not be assumed without comparing them.

Two conventions require care. The natural-number helper `heightNormalizer235` uses integer division: its value at $`0`$ is $`0`$, not $`h_0=1/2`$. It agrees with $`h_a`$ for $`a\ge1`$, as assumed in the supplied half-height identity. The real tail definition `dyadicNormalizedTailStateR235` divides after casting to $`\mathbb R`$, so agrees with $`X_a=h_aT_a`$ at every index.

The denominator-clearing and reduced-carry lemmas assume $`T_1`$ rational. The first shell consists of $`1`$ alone, so $`T_1=S-1`$; thus $`S=N/D`$ supplies
``` math
T_1=\frac{N-D}{D},\qquad \gcd(N-D,D)=\gcd(N,D).
```
The supplied `PaperR7RationalBridge.lean` proves this translation, which preserves the denominator, its smooth factor and the clearing onset. These comparisons use the attached sources; they are not a new build or verification of all historical link targets.

Two displayed statements also have direct current-source counterparts. The threshold-column rank formula is [finite cut rank](https://github.com/wcook04/plectis-erdos/blob/d11bd0b16f2c0b68d722777762ebbd4f96a12db8/lean/ErdosProblems/Erdos269/PaperR7FiniteCutRank.lean#L182); its range equality allows repeated columns and arbitrary ordering. The uniform modular-minor statement is [uniform modular minors](https://github.com/wcook04/plectis-erdos/blob/d11bd0b16f2c0b68d722777762ebbd4f96a12db8/lean/ErdosProblems/Erdos269/PaperR7ModularMinors.lean#L133); its row and column indices are chosen before the modulus and layer. The two modules compiled under Lean 4.29.1 during this source migration.

| informal statement | linked Lean source |
|:---|:---|
| integer represented by an exponent triple | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L32) |
| pure-power height | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L37) |
| lattice kernel | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L41) |
| exponent triples below the cutoff | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L47) |
| running least common multiple | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L54) |
| prefix value divides the height | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L60) |
| divisibility into the height | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L78) |
| first pure-power membership | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L85) |
| second pure-power membership | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L98) |
| third pure-power membership | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L111) |
| running-lcm identity | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L124) |
| cell relation | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L164) |
| cell constancy of the height | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L170) |
| cell constancy of the running value | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L180) |
| cell constancy of the kernel | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L192) |
| positive power sets | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L205) |
| counting positive prime powers | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L209) |
| exclusion of the origin | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L220) |
| disjoint positive prime powers | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L230) |
| union of positive prime powers | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L244) |
| positive jump count | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L250) |
| jump set with the origin | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L274) |
| jump count with the origin | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L279) |
| first height step | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L295) |
| second height step | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L306) |
| third height step | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L317) |
| first coordinate step | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L327) |
| second coordinate step | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L340) |
| third coordinate step | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L353) |
| exponent box | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L369) |
| point height | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L374) |
| height fibre | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L378) |
| fibre sum | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L385) |
| grouping equal denominators in a finite sum | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L407) |
| upper bound by the cube of the cutoff | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L431) |
| origin value | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L444) |
| value at two | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L451) |
| value at three | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L459) |
| value at six | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L468) |
| example excluding a product of two factors | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L480) |
| variable-base tail step | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L488) |
| expanded tail step | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L491) |
| smooth exponent shell | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L501) |
| short-interval uniqueness | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L510) |
| first-coordinate projection | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L544) |
| third-coordinate projection | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L586) |
| sorted quadratic estimate | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L630) |
| quadratic shell bound | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L647) |
| dyadic internal power | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L663) |
| internal-power uniqueness | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L669) |
| dyadic block base | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L751) |
| exact dyadic radix alphabet | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L762) |
| bounded-radix consequence | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L774) |
| a nonzero $`2\times2`$ determinant | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L827) |
| no integer rotation orbit | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L154) |
| height factorisation | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L218) |
| kernel factorisation | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L259) |
| two-prime outer product | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L278) |
| two-prime vanishing minors | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L298) |
| uniform minors, general form | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L313) |
| uniform minors for primes | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L376) |
| no finite separation | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L388) |
| second-order minor | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L560) |
| third-order minor | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L570) |
| misleading proportional row | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L583) |
| failure of that proportionality | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L592) |
| integer numerator for one dyadic shell | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicBlockThresholdPartition.lean#L150) |
| normalised state step | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicOrderedTailRecurrence.lean#L110) |
| shell summability | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicShellSummability.lean#L142) |
| infinite tail recurrence | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicShellSummability.lean#L177) |
| integer tails or separation from the integers | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicShellSummability.lean#L188) |
| boundary divisibility | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L51) |
| half-height identity for $`a\ge1`$ | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L101) |
| window clearing identity | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L158) |
| clearing a rational $`T_1`$ at $`a\ge1`$ | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L196) |
| normalised-state collision | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L296) |
| least positive residue | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L26) |
| positive representative range | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L31) |
| representative congruence | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L52) |
| escape condition | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L71) |
| excluding a bounded positive natural number | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L76) |
| contrapositive form | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L96) |
| excluding a bounded positive integer | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L110) |
| identifying the least positive representative | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L138) |
| window base | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L417) |
| accumulated numerator in a window | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L422) |
| affine window identity | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L455) |
| scaling the accumulated numerator | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L469) |
| integral carry window | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L480) |
| endpoint residue identification | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L497) |
| divisibility by the smooth part of the denominator | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L548) |
| common-factor cancellation | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L581) |
| bound after dividing out the common factor | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L601) |
| window identity after division | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L612) |
| cofinal window hypothesis | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L629) |
| escape excludes a reduced positive integer carry | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L645) |
| the same contradiction with a common factor | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L689) |
| real window identity | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L68) |
| escape from irrationality, general bound | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L327) |
| escape from irrationality, quadratic family | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L355) |
| escape from irrationality, actual bound | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L379) |
| residue criterion equivalent to an irrational tail | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L392) |
| residue criterion equivalent to an irrational sum | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L398) |
| rational $`T_1`$ gives eventual integer carries | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalityCarryBridge.lean#L324) |
| residue condition for the actual series | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalityCarryBridge.lean#L397) |
| irrationality from the residue condition | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalityCarryBridge.lean#L479) |
| bounded-radix alternative | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/BoundedRadixTailEscape.lean#L89) |
| rational value from an integral scaled tail | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/BoundedRadixTailEscape.lean#L183) |
| zero block sums as differences of potentials | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreeChannelBlockRigidity.lean#L59) |
| a nonzero error exceeds the bound at one index | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L178) |
| a nonzero error cannot stay uniformly bounded | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L238) |
| first-block sum | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L289) |
| four states cannot meet all three conditions | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L308) |
| carry as a residue plus a potential difference | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L109) |
| carry interval | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L150) |
| digit interval | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L157) |
| map from formal expressions to functions | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L293) |
| finite-dimensional span of the resulting functions | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L334) |
| interval containing a Cantor-series tail | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/PurePowerIrrationality.lean#L61) |
| state gap bound | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/PurePowerIrrationality.lean#L74) |
| small-form criterion | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/PurePowerIrrationality.lean#L94) |
| irrationality from clearing and small nonzero gaps | [](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/PurePowerIrrationality.lean#L156) |
| indices giving the threshold staircase | [staircase indices](https://github.com/wcook04/plectis-erdos/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Shared/IrrationalRotationStaircase.lean#L271) |
| finite threshold-column rank, including the extreme-column defect | [finite cut rank](https://github.com/wcook04/plectis-erdos/blob/d11bd0b16f2c0b68d722777762ebbd4f96a12db8/lean/ErdosProblems/Erdos269/PaperR7FiniteCutRank.lean#L182) |
| uniform admissible modular minors, with indices chosen before modulus and layer | [uniform modular minors](https://github.com/wcook04/plectis-erdos/blob/d11bd0b16f2c0b68d722777762ebbd4f96a12db8/lean/ErdosProblems/Erdos269/PaperR7ModularMinors.lean#L133) |

<a id="sec:erdos-269-complete-family-map"></a>

# What the results use and what they do not prove

The main arguments have different inputs and different conclusions. In particular, the kernel result does not imply irrationality, and the residue criterion still requires an arithmetic proof of escape.

<div class="center">

| Result | Dependency and limit |
|:---|:---|
| Height and cells | Prime-power divisibility and unique factorisation. Their geometry alone gives no irrationality statement. |
| Two-prime values | Earlier factorisation plus the cited external Hecke–Mahler value theorem; not formalised here. |
| Arbitrary-order rank | Diagonal rescaling, separate one-dimensional densities and a staircase determinant; selected supplied formal evidence. |
| Tail recurrence | Counting the original multiplicities, normalising by half the boundary height, and convergence; an abstract recurrence would not identify the sum. |
| Denominator reduction | A finite prefix with cleared denominators and an upper bound for positive integer tails. The first valid index is determined by an ordinary proof. |
| Residue criterion | The actual recurrence, a dominating bound and window products comparable to $`8^h`$; escape at arbitrarily late starts remains unproved. |
| Weighted differences | Exact reindexing and the contributions of the new boundary strips; integer enumeration checks the displayed counterexample to third-difference cancellation. |
| Finite computations | Direct checks settle only their individual windows; the large reports cannot be verified without their missing data. |

</div>

A source link identifies code; a build record reports what was run; an axiom audit concerns logical dependencies; and a finite computation checks its stated inputs. None substitutes for a proof of the remaining irrationality assertion.

<div class="thebibliography">

99 Paul Erdős and Ronald L. Graham, *Old and New Problems and Results in Combinatorial Number Theory*, Monographies de L’Enseignement Mathématique **28**, L’Enseignement Mathématique (1980), [source](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf). Paul Erdős, *On the irrationality of certain series: problems and results*, in *New Advances in Transcendence Theory*, Cambridge University Press (1988), 102–109, [doi:`10.1017/CBO9780511897184.009`](https://doi.org/10.1017/CBO9780511897184.009). Paul Erdős, *Letter to the Editor*, Fibonacci Quarterly **12**, no. 4 (1974), 335, [source](https://www.fq.math.ca/Scanned/12-4/letter.pdf). Thomas F. Bloom, *Erdős Problem \#269* (2026), [source](https://www.erdosproblems.com/269). Catalogue snapshot cited in the supplied manuscript: 28 July 2026. The Formal Conjectures Authors, *FormalConjectures.ErdosProblems.269* (2025), [source](https://github.com/google-deepmind/formal-conjectures/blob/f776d2f2039351b00737ffcafb9d7d7666e1d9af/FormalConjectures/ErdosProblems/269.lean). Tom M. Apostol, *Introduction to Analytic Number Theory*, Springer (1976), [doi:`10.1007/978-1-4757-5579-4`](https://doi.org/10.1007/978-1-4757-5579-4). Adolf Hildebrand, *On the number of positive integers $`\le`$ x and free of prime factors \> y*, Journal of Number Theory **22** (1986), 289–307, [doi:`10.1016/0022-314X(86)90013-2`](https://doi.org/10.1016/0022-314X(86)90013-2). Hugh L. Montgomery and Robert C. Vaughan, *The Prime Number Theorem*, in *Multiplicative Number Theory I: Classical Theory*, Cambridge Studies in Advanced Mathematics **97**, Cambridge University Press (2007), 168–198, [doi:`10.1017/CBO9780511618314.008`](https://doi.org/10.1017/CBO9780511618314.008). Vjekoslav Kovač and Terence Tao, *On several irrationality problems for Ahmes series*, Acta Mathematica Hungarica **175** (2025), 572–608, [doi:`10.1007/s10474-025-01528-0`](https://doi.org/10.1007/s10474-025-01528-0); arXiv:[2406.17593](https://arxiv.org/abs/2406.17593). Yann Bugeaud and Michel Laurent, *Transcendence and continued fraction expansion of values of Hecke–Mahler series*, Acta Arithmetica **209** (2023), 59–90, [doi:`10.4064/aa220323-18-1`](https://doi.org/10.4064/aa220323-18-1); arXiv:[2203.12901](https://arxiv.org/abs/2203.12901). John H. Loxton and Alfred J. van der Poorten, *Arithmetic properties of certain functions in several variables III*, Bulletin of the Australian Mathematical Society **16** (1977), 15–47, [doi:`10.1017/S0004972700022978`](https://doi.org/10.1017/S0004972700022978). Steve Fan, *Comment on Erdős Problem \#269, thread 269, post 7218* (2026), [source](https://www.erdosproblems.com/forum/thread/269#post-7218). 26 June 2026, thread 269, post 7218; priority retained from the supplied record. Paul Erdős and Ernst G. Straus, *On the irrationality of certain series*, Pacific Journal of Mathematics **55**, no. 1 (1974), 85–92, [doi:`10.2140/pjm.1974.55.85`](https://doi.org/10.2140/pjm.1974.55.85). Jaroslav Hančl and Robert Tijdeman, *On the irrationality of Cantor and Ahmes series*, Publicationes Mathematicae Debrecen **65**, no. 3–4 (2004), 371–380, [doi:`10.5486/PMD.2004.3254`](https://doi.org/10.5486/PMD.2004.3254). Angeliki Koutsoukou-Argyraki and Wenda Li, *Irrationality Criteria for Series by Erdős and Straus*, Archive of Formal Proofs (2020), [source](https://isa-afp.org/entries/Irrational_Series_Erdos_Straus.html). Entry dated 12 May 2020; proof-document version consulted: 6 February 2026. Paul Erdős and S. James Taylor, *On the set of points of convergence of a lacunary trigonometric series and the equidistribution properties of related sequences*, Proceedings of the London Mathematical Society **s3-7**, no. 1 (1957), 598–615, [doi:`10.1112/plms/s3-7.1.598`](https://doi.org/10.1112/plms/s3-7.1.598). Steve Fan, *Strongly complete sets and a conjecture of Erdős* (2026), [source](https://arxiv.org/abs/2607.14071v1); arXiv:[2607.14071](https://arxiv.org/abs/2607.14071). The cited Lemma 3.1 is in arXiv v1, 15 July 2026. Paul Lévy, *Sur le développement en fraction continue d’un nombre choisi au hasard*, Compositio Mathematica **3** (1936), 286–303, [source](https://www.numdam.org/item/CM_1936__3__286_0/). Wieb Bosma, Cor Kraaikamp, S. Hommersom, M. Keune, C. Kooloos, W. van Loon, R. Loos, E. Omiljan, G. Popma, D. Venhoek and M. Zwart, *Continued Fractions* (2013), [source](https://www.math.ru.nl/~bosma/Students/CF.pdf). Jaroslav Hančl and Robert Tijdeman, *On the irrationality of polynomial Cantor series*, Acta Arithmetica **133**, no. 1 (2008), 37–52, [doi:`10.4064/aa133-1-3`](https://doi.org/10.4064/aa133-1-3). Florian Luca, Joël Ouaknine and James Worrell, *Transcendence of Hecke–Mahler Series*, Bulletin of the London Mathematical Society **57**, no. 5 (2025), 1360–1368, [doi:`10.1112/blms.70033`](https://doi.org/10.1112/blms.70033); arXiv:[2412.07908](https://arxiv.org/abs/2412.07908). Numbered references use the published article. Pavol Kebis, Florian Luca, Joël Ouaknine, Andrew Scoones and James Worrell, *On Transcendence of Numbers Related to Sturmian and Arnoux-Rauzy Words*, in *51st International Colloquium on Automata, Languages, and Programming (ICALP 2024)*, Leibniz International Proceedings in Informatics **297**, Schloss Dagstuhl – Leibniz-Zentrum für Informatik (2024), 144:1–144:15, [doi:`10.4230/LIPIcs.ICALP.2024.144`](https://doi.org/10.4230/LIPIcs.ICALP.2024.144). Robert Tijdeman and H. G. Meijer, *On integers generated by a finite number of fixed primes*, Compositio Mathematica **29**, no. 3 (1974), 273–286, [source](https://www.numdam.org/article/CM_1974__29_3_273_0.pdf). Alessandro Languasco, Florian Luca, Pieter Moree and Alain Togbé, *Sequences of integers generated by two fixed primes*, Abhandlungen aus dem Mathematischen Seminar der Universität Hamburg **95** (2025), 123–148, [doi:`10.1007/s12188-025-00293-9`](https://doi.org/10.1007/s12188-025-00293-9); arXiv:[2309.12806](https://arxiv.org/abs/2309.12806). Boris Adamczewski and Yann Bugeaud, *On the complexity of algebraic numbers I. Expansions in integer bases*, Annals of Mathematics **165**, no. 2 (2007), 547–565, [doi:`10.4007/annals.2007.165.547`](https://doi.org/10.4007/annals.2007.165.547). Federico Pellarin, *On the arithmetic properties of complex values of Hecke–Mahler series I. The rank one case*, Annali della Scuola Normale Superiore di Pisa, Classe di Scienze (5) **5**, no. 3 (2006), 329–374, [published source](https://www.numdam.org/item/ASNSP_2006_5_5_3_329_0/). Boris Adamczewski and Colin Faverjon, *A new proof of Nishioka’s theorem in Mahler’s method*, Comptes Rendus. Mathématique **361** (2023), 1011–1028, [doi:`10.5802/crmath.458`](https://doi.org/10.5802/crmath.458). Boris Adamczewski and Colin Faverjon, *Mahler’s method in several variables and finite automata*, Annals of Mathematics **204**, no. 2 (2026), 455–533, [doi:`10.4007/annals.2026.204.2.1`](https://doi.org/10.4007/annals.2026.204.2.1). Online 13 September 2026; locators here refer to the [68-page author manuscript](https://faverjon.perso.math.cnrs.fr/AdamczewskiFaverjon_MahlerFiniteAutomata.pdf).

</div>

[^1]: For this logarithmic form of the Gelfond–Schneider theorem, see Keith Conrad, *Transcendence of $`e`$*, p. 1, footnote 1, <https://kconrad.math.uconn.edu/blurbs/analysis/transcendence-e.pdf> (accessed 18 September 2026).
