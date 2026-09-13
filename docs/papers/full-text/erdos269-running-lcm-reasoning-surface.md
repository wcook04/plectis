<a id="erdos269-running-lcm-reasoning-surface"></a>

# The Three-Prime Running LCM: Complete Reasoning Record

<div class="center">

<span class="smallcaps">Abstract</span>

</div>

For three pairwise distinct primes, the reciprocal running-LCM kernel has nonsingular minors of every order, with the same indices valid in every third-coordinate layer. Removing row and column factors leaves a binary floor carry. Its threshold columns give both the arbitrary-order rank obstruction and the exact rank of a finite sample. The normalised carry also has a sharp uniform finite-rank approximation barrier, although the original summable kernel admits finite-rank approximation in the summation norm. These are statements about representations, not irrationality of the resulting scalar sum.

For two distinct primes, both the repeated and de-duplicated running-LCM series are transcendental. They are nonconstant polynomials in one Hecke–Mahler value, whose transcendence follows from the theorem of Loxton and van der Poorten in the form given by Bugeaud and Laurent. Steve Fan posted the factorisation, reduction and conclusion first, on 26 June 2026. The argument recorded here uses that external theorem; it is not a Lean formalisation of the two-prime result.

For the repeated $`\{2,3,5\}`$ series, the complete record constructs the literal tail recurrence and proves that rationality forces eventually positive integral tails under a quadratic bound. Escape of the exact window residues is equivalent to irrationality. Finite certificates test that criterion and exclude bounded denominator ranges, but do not supply its unbounded quantifiers. The record gives the proofs, exact finite evidence and failed representation methods behind the short paper; the repeated-series problem with three or more primes remains open.

<a id="how-the-short-paper-uses-this-record."></a>

#### How the short paper uses this record.

The short paper centres on the binary carry and its rank obstruction. Section <a href="#long269:sec:rank" data-reference-type="ref" data-reference="long269:sec:rank">4</a> gives the rank and approximation arguments; Section <a href="#long269:sec:two-prime" data-reference-type="ref" data-reference="long269:sec:two-prime">3</a> gives the two-prime comparison. Sections <a href="#long269:sec:blocks" data-reference-type="ref" data-reference="long269:sec:blocks">5</a>–<a href="#long269:sec:escape" data-reference-type="ref" data-reference="long269:sec:escape">7</a> recover the literal tails, denominator clearing and window criterion, while Section <a href="#long269:sec:evidence" data-reference-type="ref" data-reference="long269:sec:evidence">8</a> retains the finite certificates. These are two distinct mathematical tasks: the rank argument excludes a separated representation, and the tail argument identifies the arithmetic condition still needed for irrationality. Neither substitutes for the other.

<a id="long269:sec:problem"></a>

# The problem, and what is settled

Let $`P`$ be a finite set of primes with $`|P|\ge2`$, and let $`a_1<a_2<\cdots`$ enumerate the positive integers all of whose prime factors lie in $`P`$. Erdős Problem #269 asks whether
``` math
\sum_{n\ge1}\frac{1}{[a_1,\ldots,a_n]}
```
is irrational, where $`[a_1,\ldots,a_n]`$ is the least common multiple \[erdosgraham1980, p. 65\]\[erdos1988, p. 106\]. Bloom’s catalogue records the problem as open \[erdosproblems\]. This note settles every instance with $`|P|=2`$, at the level of transcendence, and the unresolved finite cases begin at $`|P|=3`$.

The restriction $`|P|\ge2`$ is necessary. For $`P=\{p\}`$ the enumeration is $`a_n=p^{\,n-1}`$, so $`[a_1,\ldots,a_n]=p^{\,n-1}`$ and the sum is $`p/(p-1)`$. For infinite $`P`$ the sum is always irrational, which Erdős calls a simple exercise \[erdos1988, p. 106\].

Write $`\mathcal R_P`$ for the sum above and $`\mathcal D_P`$ for the de-duplicated sum, in which each distinct value of the running least common multiple contributes its reciprocal once. The two differ because the running value is constant along stretches of the enumeration. In a letter written on 1 January 1973 Erdős recorded that he could prove irrationality of the de-duplicated sum \[erdos1974letter, p. 335\]. He states that assertion for a general finite list of primes and supplies no proof, so the historical record already covers $`\mathcal D_P`$ for every finite $`P`$; the open question addressed by the catalogue is $`\mathcal R_P`$.

<div id="long269:res:lead-two-prime" class="theorem">

**Theorem 1** (two-prime transcendence). *Let $`p`$ and $`q`$ be distinct primes. Then $`\mathcal R_{\{p,q\}}`$ and $`\mathcal D_{\{p,q\}}`$ are transcendental.*

</div>

Section <a href="#long269:sec:two-prime" data-reference-type="ref" data-reference="long269:sec:two-prime">3</a> proves this. Both values are explicit polynomials in one Hecke–Mahler boundary sum $`A`$, the coefficients are nonzero rationals, and transcendence of $`A`$ is the theorem of Loxton and van der Poorten \[loxtonvdp1977, p. 40, Theorem 8\] in the modern form of Bugeaud and Laurent’s Theorem 1.1 \[bugeaudlaurent2023, p. 61, Theorem 1.1\]. The evidence class is an ordinary proof in this paper over a cited external theorem, and no Lean declaration formalises it.

<a id="attribution."></a>

#### Attribution.

Steve Fan posted the running-LCM identity for every $`|P|`$, the two-channel factorisation, the Hecke–Mahler reduction and the transcendence conclusion in the discussion thread of the problem’s page on 26 June 2026 \[fan2026comment\], with follow-up remarks extending the argument to arbitrary coprime pairs. The priority for the two-prime case is his. The proof below is independent and is given in full because it fixes the $`|P|=2`$ boundary of the problem and because the same boundary sum drives the three-prime discussion. The identity of Theorem <a href="#long269:res:lcm" data-reference-type="ref" data-reference="long269:res:lcm">2</a> is cited to him.

<a id="what-the-third-prime-does."></a>

#### What the third prime does.

Section <a href="#long269:sec:rank" data-reference-type="ref" data-reference="long269:sec:rank">4</a> isolates the obstruction exactly. After separating row and column factors, the two-prime kernel is an outer product and the three-prime kernel retains one binary floor carry. That carry is enough to produce nonsingular minors of every order, uniformly in the third coordinate, and to make the normalised carry matrix inapproximable by finite separated sums below half its own jump. Sections <a href="#long269:sec:blocks" data-reference-type="ref" data-reference="long269:sec:blocks">5</a> to <a href="#long269:sec:escape" data-reference-type="ref" data-reference="long269:sec:escape">7</a> take a second route on the literal $`\{2,3,5\}`$ series: dyadic shells give an integer-coefficient tail recurrence, a strict endpoint clears the smooth part of a hypothetical denominator, and the surviving carry is trapped between a quadratic bound and a residue condition. Section <a href="#long269:sec:evidence" data-reference-type="ref" data-reference="long269:sec:evidence">8</a> reports the finite evidence and its ceiling, and Section <a href="#long269:sec:open" data-reference-type="ref" data-reference="long269:sec:open">9</a> states what remains.

Throughout, $`p,q,r`$ are pairwise distinct primes. Call $`n`$ *smooth* when $`n=p^{i}q^{j}r^{k}`$ for some $`i,j,k\ge0`$; this is the [smooth lattice value](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L32). For $`x\ge1`$ write
``` math
\operatorname{L}(x)=\operatorname{lcm}\{\,n\le x:\ n\ \text{smooth}\,\},
 \qquad
 \operatorname{H}(x)=p^{\lfloor\log_p x\rfloor}\,q^{\lfloor\log_q x\rfloor}\,
 r^{\lfloor\log_r x\rfloor},
```
the [running least common multiple](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L54) and the [pure-power height](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L37), where $`\lfloor\log_b x\rfloor`$ is the largest $`e`$ with $`b^{e}\le x`$. Since $`a_1,\ldots,a_n`$ are exactly the smooth numbers up to $`a_n`$, we have $`[a_1,\ldots,a_n]=\operatorname{L}(a_n)`$. The reciprocal of the height at a smooth point is the [lattice kernel](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L41)
``` math
\operatorname{K}(i,j,k)=\frac{1}{\operatorname{H}(p^{i}q^{j}r^{k})} .
```
Here “smooth” always means supported on the fixed prime set, and it is not the varying-bound notion counted by $`\Psi(x,y)`$ in the Dickman–Hildebrand theory \[hildebrand1986, Theorem 1\]; no smooth-number density asymptotic is used below. For $`b\in\{p,q,r\}`$ the set of positive powers of $`b`$ is the *$`b`$-channel*.

The statement of Problem #269 has been formalised before, as a conjecture with an unfilled proof, in the *Formal Conjectures* collection \[formalconjectures269\]. That is a formal statement of the question up to a rational normalisation, since its Nat-indexed series includes the empty-prefix term, and its rational, irrational and infinite-prime assertions all end in `sorry`. Kovač and Tao \[kovactao2024\] treat several irrationality problems of Erdős for series of unit fractions by elementary means; nothing from that work is used here.

**Keywords.** irrationality; transcendence; least common multiple; smooth numbers; separated rank; Lean 4. **MSC 2020.** 11J72 (primary); 11A05, 11N25, 68V20 (secondary).

<a id="long269:sec:lcm"></a>

# The finite geometry of the running value

The smooth numbers up to $`x`$ are indexed by the exponent triples $`(i,j,k)`$ with $`i\le\lfloor\log_p x\rfloor`$, $`j\le\lfloor\log_q x\rfloor`$, $`k\le\lfloor\log_r x\rfloor`$ and $`p^{i}q^{j}r^{k}\le x`$, the [smooth prefix index set](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L47). Both conditions matter: the coordinate box is strictly larger than the prefix, since a product of three large pure powers can exceed $`x`$ while each factor does not.

<div id="long269:res:lcm" class="theorem">

**Theorem 2** (the running least common multiple). *Let $`p,q,r`$ be pairwise distinct primes and $`x\ge1`$. Then $`\operatorname{L}(x)=\operatorname{H}(x)`$.*

</div>

<div class="proof">

*Proof.* Every smooth $`n\le x`$ has exponents bounded by the corresponding integer logarithms, so $`n\mid\operatorname{H}(x)`$ and hence $`\operatorname{L}(x)\mid\operatorname{H}(x)`$. Conversely the three pure powers $`p^{\lfloor\log_p x\rfloor}`$, $`q^{\lfloor\log_q x\rfloor}`$ and $`r^{\lfloor\log_r x\rfloor}`$ are themselves smooth numbers not exceeding $`x`$, so each divides $`\operatorname{L}(x)`$, and distinct primes have coprime powers, so their product divides $`\operatorname{L}(x)`$ as well. ◻

</div>

Formalised as the [running-lcm identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L124), from the [pointwise divisibility](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L60), the [divisibility into the height](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L78) and the three pure-power memberships, namely the [first](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L85), [second](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L98) and [third](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L111). The unrestricted analogue is classical: iterating the prime-exponent maximum rule gives $`\operatorname{lcm}(1,\ldots,N)=\prod_{t\le N}t^{\lfloor\log_t N\rfloor}`$ over the primes $`t\le N`$ \[apostol1976, Ex. 1.21(a), p. 22\], equivalently $`\log\operatorname{lcm}(1,\ldots,N)=\psi(N)`$ \[apostol1976, §4.2, p. 75\], and Montgomery and Vaughan state the identity directly in Exercise 6.2.7 \[montgomeryvaughan2007, p. 183\]. Fan states the $`P`$-restricted form for every $`|P|`$ \[fan2026comment\]. The pairwise distinctness hypothesis is used exactly once, in the coprimality step.

At $`(p,q,r)=(2,3,5)`$ the first ten values are
``` math
\begin{array}{c|cccccccccc}
x&1&2&3&4&5&6&7&8&9&10\\ \hline
\operatorname{L}(x)&1&2&6&12&60&60&60&120&360&360
\end{array}
```
So $`\operatorname{L}(6)=4\cdot3\cdot5=60`$, which exceeds $`6`$: the running value at a smooth cutoff already contains powers of the other two primes that the cutoff itself does not. That small fact is the mechanism behind Section <a href="#long269:sec:rank" data-reference-type="ref" data-reference="long269:sec:rank">4</a>. Also $`\operatorname{H}(x)\le x^{3}`$, since each of the three factors is a power of its base not exceeding $`x`$; this is the [cubic majorant](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L431), and the exponent is the number of generating primes.

Say that $`x`$ and $`y`$ lie in the same *logarithmic cell* when $`\lfloor\log_b x\rfloor=\lfloor\log_b y\rfloor`$ for each of $`b=p,q,r`$, the [cell relation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L164). By Theorem <a href="#long269:res:lcm" data-reference-type="ref" data-reference="long269:res:lcm">2</a> the running value depends on $`x`$ only through the three integer logarithms, so it is constant on cells and moves only where one logarithm moves.

<div id="long269:res:cell" class="proposition">

**Proposition 3** (constancy and jump ratios). *If $`x,y\ge1`$ lie in the same logarithmic cell then $`\operatorname{L}(x)=\operatorname{L}(y)`$, and the same holds for the kernel at two smooth points of one cell. If $`\lfloor\log_p y\rfloor=\lfloor\log_p x\rfloor+1`$ while the other two logarithms agree, then $`\operatorname{L}(y)=p\,\operatorname{L}(x)`$, and similarly with $`q`$ or $`r`$ in place of $`p`$.*

</div>

<div class="proof">

*Proof.* Both parts are immediate from Theorem <a href="#long269:res:lcm" data-reference-type="ref" data-reference="long269:res:lcm">2</a>: the height depends on $`x`$ only through the three integer logarithms, and advancing one of them multiplies exactly one factor by its base. ◻

</div>

The first part is the [cell constancy of the running value](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L180), over the [cell constancy of the height](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L170) and the [cell constancy of the kernel](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L192). The jump statement is <span id="long269:res:jump" label="long269:res:jump"></span>the [first](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L327), [second](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L340) and [third](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L353) coordinate steps, over the corresponding height steps, which need no primality: the [first](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L295), [second](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L306) and [third](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L317).

<div id="long269:res:count" class="proposition">

**Proposition 4** (jump count). *Let $`n\ge0`$. The set of the first $`n`$ positive powers of $`p`$, of $`q`$ and of $`r`$ has exactly $`3n`$ elements, and adjoining the common origin $`1`$ gives exactly $`3n+1`$.*

</div>

<div class="proof">

*Proof.* Within one channel the powers $`b,b^{2},\ldots,b^{n}`$ are distinct because $`b\ge2`$. Across two channels a common value would be a positive power of two distinct primes, which unique factorisation forbids. Finally $`1`$ is not a positive power of any prime. ◻

</div>

Formalised as the [positive jump count](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L250) and the [jump count with the origin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L279), over the [channel cardinality](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L209), the [channel disjointness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L230) and the [exclusion of the origin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L220); the channels are the [positive power sets](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L205), whose union is the [positive jump set](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L244) and, with the origin adjoined, the [full jump set](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L274). Two channels never meet, so at each positive pure power exactly one logarithm advances and the running value is multiplied there by the prime of that channel. Reading those multipliers in increasing order of the pure powers gives the *jump word* of $`\operatorname{L}`$. At $`\{2,3,5\}`$ the pure powers in increasing order are $`2,3,4,5,8,9,16,25,27,32,\ldots`$, so the jump word begins
``` math
2,\;3,2,\;5,2,\;3,2,\;5,3,2,\;\ldots
```
grouped so that each group ends at a power of two, which is the grouping used in Section <a href="#long269:sec:blocks" data-reference-type="ref" data-reference="long269:sec:blocks">5</a>.

Two finite statements are recorded here because they are the exact shape of the counting used later. Write $`\mathcal B(h_p,h_q,h_r)`$ for the box of exponent triples with $`i\le h_p`$, $`j\le h_q`$, $`k\le h_r`$, the [exponent box](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L369), and $`F(H)`$ for the set of its points whose height equals $`H`$, the [height fibre](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L378).

<div id="long269:res:fibre" class="proposition">

**Proposition 5** (finite normal form). *For every box $`\mathcal B`$, $`\sum_{(i,j,k)\in\mathcal B}\operatorname{K}(i,j,k)=\sum_{H}\#F(H)/H`$, the outer sum ranging over the heights attained on $`\mathcal B`$.*

</div>

<div class="proof">

*Proof.* Partition $`\mathcal B`$ into the fibres of the height map. On $`F(H)`$ every summand is $`1/H`$, so the fibre contributes $`\#F(H)/H`$. ◻

</div>

Formalised as the [height-fibre normal form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L407), over the [fibre sum](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L385) and the [point height](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L374). At $`(2,3,5)`$ on $`\mathcal B(1,1,1)`$ the eight smooth values $`1,2,3,5,6,10,15,30`$ carry heights $`1,2,6,60,60,360,360,10800`$, so two coefficients equal $`2`$ and the identity reads $`18421/10800`$ on both sides. The identity is between two finite sums over a box, so it is not a statement about $`\operatorname{L}`$ at a cutoff. The same module records the one-step map $`\tau(b,d,s)=b(s-d)`$, the [variable-base tail step](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L488), with the rewriting [that names its expanded form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L491); the orbits analysed in Section <a href="#long269:sec:blocks" data-reference-type="ref" data-reference="long269:sec:blocks">5</a> are the actual ones, and no orbit of this abstract map is analysed.

Now fix an interval $`[\lambda,\eta)`$ and write $`\mathcal S`$ for the exponent triples of $`\mathcal B(h_p,h_q,h_r)`$ whose smooth value lies in it, the [smooth exponent shell](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L501).

<div id="long269:res:short" class="lemma">

**Lemma 6** (uniqueness in a short interval). *Let $`b\ge1`$ and $`\eta\le b\,\lambda`$. If $`b^{a}w`$ and $`b^{a'}w`$ both lie in $`[\lambda,\eta)`$ then $`a=a'`$.*

</div>

<div class="proof">

*Proof.* If $`a<a'`$ then $`\eta\le b\,\lambda\le b^{a+1}w\le b^{a'}w<\eta`$, which is impossible; the case $`a>a'`$ is symmetric. ◻

</div>

<div id="long269:res:drop" class="proposition">

**Proposition 7** (projection and the quadratic shell bound). *<span id="long269:res:shell" label="long269:res:shell"></span> If $`\eta\le r\,\lambda`$ then $`\#\mathcal S\le(h_p+1)(h_q+1)`$, and if $`\eta\le p\,\lambda`$ then $`\#\mathcal S\le(h_q+1)(h_r+1)`$. If moreover $`\eta\le r\,\lambda`$ and $`h_p\le h_q\le h_r`$ with $`h_p+h_q+h_r=j`$, then $`9\,\#\mathcal S\le(j+3)^{2}`$.*

</div>

<div class="proof">

*Proof.* Suppose $`\eta\le r\,\lambda`$. If two triples of $`\mathcal S`$ agree in their first two coordinates, Lemma <a href="#long269:res:short" data-reference-type="ref" data-reference="long269:res:short">6</a> with $`b=r`$ and $`w=p^{i}q^{j}`$ forces their third coordinates to agree, so the projection forgetting the third coordinate is injective on $`\mathcal S`$ and its image lies in a rectangle with $`(h_p+1)(h_q+1)`$ points. The other case is the same with the first coordinate projected away. Under the sorting hypothesis the two surviving coordinates are the two smallest, so it suffices that $`a\le b\le c`$ with $`a+b+c=j`$ gives $`9(a+1)(b+1)\le(j+3)^{2}`$. From $`a\le b\le c`$ we get $`a+2b\le j`$, so it is enough that $`9(a+1)(b+1)\le(a+2b+3)^{2}`$; writing $`b=a+d`$ with $`d\ge0`$, the difference of the two sides is $`d(3a+4d+3)\ge0`$. ◻

</div>

Formalised as the [third-coordinate projection](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L586), the [first-coordinate projection](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L544), the [quadratic shell bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L647) and the [sorted quadratic estimate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L630), over the [short-interval uniqueness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L510). The constant $`9`$ is the square of the number of generating primes, and the last inequality of the proof is an equality when $`h_p=h_q=h_r`$, so no larger constant survives that step. The estimate uses no analytic input on the distribution of smooth numbers.

<a id="long269:sec:two-prime"></a>

# One Hecke–Mahler value controls both two-prime sums

Temporarily let $`P=\{p,q\}`$ with $`p<q`$, and write $`L_{p,q}(t)=p^{\lfloor\log_p t\rfloor}q^{\lfloor\log_q t\rfloor}`$, which is the running least common multiple of the $`\{p,q\}`$-smooth numbers up to $`t`$ by the argument of Theorem <a href="#long269:res:lcm" data-reference-type="ref" data-reference="long269:res:lcm">2</a> with one coordinate omitted. The de-duplicated sum retains the initial value $`1`$ and one reciprocal for every later distinct running value, so
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
The initial value and the $`p`$-channel contribute $`A`$, since $`L_{p,q}(p^n)=p^nq^{m_n}`$. A power of $`q`$ lies strictly between $`p^n`$ and $`p^{n+1}`$ exactly when $`\delta_n=1`$, it is then $`q^{m_n+1}`$, and its post-jump reciprocal is $`x^ny^{m_n+1}`$; so the $`q`$-channel contributes $`B_\ast`$ and $`\mathcal D_{\{p,q\}}=A+B_\ast`$. All these series converge absolutely.

Since $`y^{m_{n+1}}-y^{m_n}=\delta_ny^{m_n}(y-1)`$, an index shift gives $`A-1-xA=x(y-1)B_\ast/y`$, so $`B_\ast=\bigl((p-1)A-p\bigr)/(1-q)`$ and
``` math
\begin{equation}
\label{long269:eq:two-prime-affine}
 \mathcal D_{\{p,q\}}=\frac{(q-p)A+p}{q-1} .
\end{equation}
```
At a smooth point, $`\log_p(p^iq^j)=i+j/\theta`$ and $`\log_q(p^iq^j)=j+i\theta`$, so $`L_{p,q}(p^iq^j)=p^{\,i+\lfloor j/\theta\rfloor}q^{\,j+m_i}`$ and absolute convergence permits the factorisation
``` math
\mathcal R_{\{p,q\}}=AC,\qquad C=\sum_{j\ge0}y^jx^{\lfloor j/\theta\rfloor}.
```
For $`j\ge1`$ put $`n=\lfloor j/\theta\rfloor`$. Then $`n>j/\theta-1`$ gives $`n\theta>j-\theta>j-1`$, and $`n+1>j/\theta`$ gives $`(n+1)\theta>j`$, while $`n\theta\le j`$ and $`(n+1)\theta<j+\theta<j+1`$; hence $`m_n=j-1`$, $`m_{n+1}=j`$ and $`\delta_n=1`$. Conversely every $`n`$ with $`\delta_n=1`$ arises from the unique $`j=m_{n+1}`$. Therefore $`C=1+B_\ast`$ and
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
Bugeaud and Laurent’s Theorem 1.1 states, in particular, that $`F_\theta(\beta,\alpha)`$ is transcendental when $`\theta\in(0,1)`$ is irrational, $`\alpha`$ and $`\beta`$ are nonzero algebraic numbers, $`|\beta|<1`$ and $`|\beta\alpha^\theta|<1`$ \[bugeaudlaurent2023, p. 61, Theorem 1.1\]; the $`\rho=0`$ case used here goes back to Loxton and van der Poorten \[loxtonvdp1977, p. 40, Theorem 8\]. Take $`(\beta,\alpha)=(x,y)`$: then $`|\beta|=1/p<1`$ and
``` math
|xy^{\theta}|=\frac1p\left(\frac1q\right)^{\log p/\log q}=\frac1{p^{2}}<1 .
```
So $`F_\theta(x,y)`$ is transcendental, and <a href="#long269:eq:hecke-mahler-boundary" data-reference-type="eqref" data-reference="long269:eq:hecke-mahler-boundary">[long269:eq:hecke-mahler-boundary]</a> makes $`A`$ transcendental. The coefficient of $`A`$ in <a href="#long269:eq:two-prime-affine" data-reference-type="eqref" data-reference="long269:eq:two-prime-affine">[long269:eq:two-prime-affine]</a> is $`(q-p)/(q-1)\ne0`$ and the coefficient of $`A^{2}`$ in <a href="#long269:eq:two-prime-quadratic" data-reference-type="eqref" data-reference="long269:eq:two-prime-quadratic">[long269:eq:two-prime-quadratic]</a> is $`-(p-1)/(q-1)\ne0`$, both rational. If either value were algebraic, its identity would exhibit $`A`$ as a root of a nonzero polynomial over the algebraic numbers. ◻

</div>

The two identities are separately labelled <span id="long269:res:two-prime-transcendence" label="long269:res:two-prime-transcendence"></span><span id="long269:res:two-prime-repeated-transcendence" label="long269:res:two-prime-repeated-transcendence"></span> because they carry different weight. A product of two transcendental numbers need not be transcendental, so the factorisation $`\mathcal R=AC`$ alone proves nothing; the quadratic identity <a href="#long269:eq:two-prime-quadratic" data-reference-type="eqref" data-reference="long269:eq:two-prime-quadratic">[long269:eq:two-prime-quadratic]</a> in the single value $`A`$ is what settles the repeated sum. A third prime replaces the single Beatty boundary by a genuinely two-dimensional ordering problem, and the next section makes that failure exact.

<a id="long269:sec:rank"></a>

# The rank phase transition

One might hope to write the kernel as $`f(i)g(j)h(k)`$ and reduce the problem to one-dimensional criteria. At two generators that hope is exactly correct, and at three it fails at every finite order.

<div id="long269:res:two-prime-rank" class="proposition">

**Proposition 8** (two generators separate). *For $`p,q>1`$ and all $`i,j`$, the two-prime kernel $`\operatorname{K}_2(i,j)=1/L_{p,q}(p^iq^j)`$ is the outer product
``` math
\operatorname{K}_2(i,j)
 =\bigl(p^{i}q^{\lfloor\log_q p^{i}\rfloor}\bigr)^{-1}
  \bigl(p^{\lfloor\log_p q^{j}\rfloor}q^{j}\bigr)^{-1},
```
so every two-by-two minor of $`\operatorname{K}_2`$ vanishes.*

</div>

<div class="proof">

*Proof.* By the two-variable form of Theorem <a href="#long269:res:lcm" data-reference-type="ref" data-reference="long269:res:lcm">2</a> the exponents of $`p`$ and of $`q`$ in $`L_{p,q}(p^iq^j)`$ are $`i+\lfloor\log_p q^{j}\rfloor`$ and $`j+\lfloor\log_q p^{i}\rfloor`$, each depending on one index only. A matrix whose entries are a product of a row function and a column function has vanishing two-by-two minors. ◻

</div>

Checked as the [outer-product identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L278) and the [vanishing of every two-by-two minor](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L298). This is the linear-algebraic shadow of Section <a href="#long269:sec:two-prime" data-reference-type="ref" data-reference="long269:sec:two-prime">3</a>: the two-prime value factors because the kernel does.

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

Checked as the [rank-two certificate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L827) and the [non-separation witness](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L480), over the four exact values, the [origin](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L444), [value at two](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L451), [value at three](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L459) and [value at six](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L468); the third-order witness $`1/81000`$ is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L570) beside the [second-order one](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L560). The height at $`6`$ is $`60`$ because the maximal pure powers below $`6`$ are $`4`$, $`3`$ and $`5`$, so the running value at a smooth cutoff sees powers of the other primes that the cutoff itself omits.

<div id="long269:res:infinite-rank" class="theorem">

**Theorem 10** (arbitrary-order non-separability). *<span id="long269:res:lead-infinite-rank" label="long269:res:lead-infinite-rank"></span> Let $`p,q,r`$ be primes with $`p\ne q`$, $`p\ne r`$ and $`q\ne r`$. For every $`n\ge1`$ there are injective maps $`I,J:\{0,\ldots,n-1\}\to\mathbb{N}`$ such that, for every $`k\ge0`$,
``` math
\det\bigl(\operatorname{K}(I(a),J(b),k)\bigr)_{0\le a,b<n}\ne0 .
```
Consequently, for no finite $`d`$ do there exist rational-valued functions $`f_\ell:\mathbb{N}\to\mathbb{Q}`$ and $`G_\ell:\mathbb{N}^{2}\to\mathbb{Q}`$, $`0\le\ell<d`$, satisfying $`\operatorname{K}(i,j,k)=\sum_{\ell<d}f_\ell(i)G_\ell(j,k)`$ for all $`i,j,k`$.*

</div>

<div class="proof">

*Proof.* Put $`\alpha=\log_r p`$, $`\beta=\log_r q`$, $`x_i=\{i\alpha\}`$ and $`y_j=\{j\beta\}`$. The three height exponents are
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

Each of $`\alpha`$ and $`\beta`$ is irrational, since a rational value would give an equality of positive powers of distinct primes, so each fractional-part orbit is dense in $`(0,1)`$ and each is injective. No simultaneous density of the pair of rotations is required. First choose indices with $`0<x_{I(0)}<\cdots<x_{I(n-1)}<1`$. For the columns write $`s_b=1-y_{J(b)}`$, and use density of the second orbit to choose
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

The factorisation <a href="#long269:eq:carry-factorisation" data-reference-type="eqref" data-reference="long269:eq:carry-factorisation">[long269:eq:carry-factorisation]</a> is the [checked kernel factorisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L259), over the [height factorisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L218). The uniform minor family is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L376), the exclusion of every finite separation is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L388), and the index selection is discharged by the problem-neutral staircase engine [exists_staircase_indices](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Shared/IrrationalRotationStaircase.lean#L271), which realises the full $`n\times n`$ pattern from two rotations without integer returns and depends on Mathlib only; the absence of integer returns is the [checked irrationality of the two logarithm ratios](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L154). The Lean forms assume that $`p`$, $`q`$ and $`r`$ are prime with $`p\ne r`$ and $`q\ne r`$, and they do not use $`p\ne q`$. The proof uses the two one-dimensional density statements separately and needs no joint equidistribution hypothesis.

Index selection is essential. The leading minors of the $`\{2,3,5\}`$ kernel are not a witness: row three is $`1/120`$ times row zero for $`j\le3`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L583)), and the proportionality fails at $`j=4`$ ([checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L592)). A proof that read off leading minors alone would be false.

The same threshold description determines every finite sampled rank, rather than only producing one nonsingular minor.

<div id="long269:res:finite-cut-rank" class="proposition">

**Proposition 11** (finite sampled cut rank). *Let $`m\ge1`$ and let $`c`$ lie in a field with $`c\ne0,1`$. For $`0\le h\le m`$, let $`v_h`$ be the length-$`m`$ column whose first $`h`$ entries are $`1`$ and whose remaining entries are $`c`$. If the distinct columns of a matrix are the $`v_h`$ with $`h`$ in a nonempty set $`E\subseteq\{0,\ldots,m\}`$, then its rank is
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

To apply the proposition, sort any chosen row phases $`x_i`$. Each normalised column is a threshold column $`v_h`$, where $`h`$ is the number of sampled phases strictly below $`1-y_j`$. Repeated threshold positions give proportional columns before column normalisation, and the nonzero row and column factors in <a href="#long269:eq:carry-factorisation" data-reference-type="eqref" data-reference="long269:eq:carry-factorisation">[long269:eq:carry-factorisation]</a> do not change rank. Thus the displayed formula is the exact rank of every finite sample.

<a id="attribution-and-reach."></a>

#### Attribution and reach.

Fan recorded the qualitative obstruction for $`|P|\ge3`$ in his comment of 26 June 2026 \[fan2026comment\], observing that the two-prime argument does not seem to generalise immediately. The quantitative form above, its uniformity in the third coordinate, and its formalisation are proved here. Theorem <a href="#long269:res:infinite-rank" data-reference-type="ref" data-reference="long269:res:infinite-rank">10</a> excludes exact separations of the displayed finite-sum form; it is not an independence, irrationality or transcendence statement, and it settles no instance of Erdős #269.

<a id="a-sharp-uniform-obstruction-for-the-normalised-carry-matrix"></a>

## A sharp uniform obstruction for the normalised carry matrix

The determinant argument is exact and therefore fragile: an arbitrarily small perturbation of the kernel can destroy an exact vanishing. The next theorem replaces exactness by a uniform distance, and the constant it produces is sharp. It concerns the normalised carry matrix
``` math
\begin{equation}
\label{long269:eq:carry-matrix}
 C(i,j)=t^{\lfloor x_i+y_j\rfloor},
 \qquad
 x_i=\{i\log_r p\},\quad y_j=\{j\log_r q\},\quad t=r^{-1},
\end{equation}
```
which is the factor left in <a href="#long269:eq:carry-factorisation" data-reference-type="eqref" data-reference="long269:eq:carry-factorisation">[long269:eq:carry-factorisation]</a> after the row and column factors are divided out. Say that a real matrix $`A`$ on $`\mathbb{N}\times\mathbb{N}`$ has *finite separated rank* when all of its columns lie in one finite-dimensional space of real sequences, equivalently when $`A(i,j)=\sum_{\ell<d}f_\ell(i)g_\ell(j)`$ for some finite $`d`$ and some sequences $`f_\ell,g_\ell`$, with no continuity or boundedness assumed.

<div id="long269:res:uniform-rank" class="theorem">

**Theorem 12** (sharp uniform separated approximation). *Let $`p,q,r`$ be pairwise distinct primes and let $`C`$ be as in <a href="#long269:eq:carry-matrix" data-reference-type="eqref" data-reference="long269:eq:carry-matrix">[long269:eq:carry-matrix]</a>. Then
``` math
\inf_{A}\ \sup_{i,j\ge0}\ |C(i,j)-A(i,j)|=\frac{1-t}{2}=\frac{r-1}{2r},
```
the infimum being over all matrices $`A`$ of finite separated rank, and it is attained by the constant matrix of value $`(1+t)/2`$.*

</div>

<div class="proof">

*Proof.* Every entry of $`C`$ lies in $`\{1,t\}`$, and $`C(i,j)=t`$ exactly when $`x_i+y_j\ge1`$. Fix $`j\ne k`$. The numbers $`y_j`$ are pairwise distinct, since $`\log_r q`$ is irrational, so we may assume $`y_j<y_k`$, and then $`0\le1-y_k<1-y_j\le1`$. Density of the orbit $`(x_i)`$ in $`(0,1)`$ supplies an index $`i`$ with $`1-y_k<x_i<1-y_j`$, and at that row the two columns carry the entries $`t`$ and $`1`$. Hence any two distinct columns of $`C`$ are at sup-distance exactly $`1-t`$.

Let $`A`$ have finite separated rank and put $`\varepsilon=\sup_{i,j}|C(i,j)-A(i,j)|`$. Suppose $`\varepsilon<(1-t)/2`$. Each column $`A_j`$ then satisfies $`\|A_j\|_\infty\le1+\varepsilon`$, so all columns of $`A`$ lie in $`W=V\cap\ell^{\infty}`$, where $`V`$ is the finite-dimensional space containing the columns of $`A`$; the space $`W`$ is a subspace of $`V`$, hence finite-dimensional, and $`\|\cdot\|_\infty`$ is a genuine norm on it. By the triangle inequality, distinct columns satisfy
``` math
\|A_j-A_k\|_\infty\ \ge\ \|C_j-C_k\|_\infty-2\varepsilon
 \ =\ 1-t-2\varepsilon\ >\ 0 .
```
The compactness input is the standard fact that closed bounded subsets of a finite-dimensional real normed space are compact. The use of $`W=V\cap\ell^\infty`$ is essential: the individual separated row factors need not be bounded. The columns $`A_j`$, $`j\ge0`$, are therefore infinitely many points of $`W`$, all of norm at most $`1+\varepsilon`$ and pairwise separated by a fixed positive distance. A bounded subset of a finite-dimensional normed space is totally bounded, so it contains no infinite uniformly separated family. This contradiction gives $`\varepsilon\ge(1-t)/2`$ for every $`A`$ of finite separated rank.

For sharpness take $`A(i,j)=(1+t)/2`$, which has separated rank one; every entry of $`C`$ is at distance exactly $`(1-t)/2`$ from it. ◻

</div>

The compactness step is standard, and the statement is recorded here for this kernel without a claim of technique. Three qualifications fix its reach. It is a statement about the normalised carry matrix <a href="#long269:eq:carry-matrix" data-reference-type="eqref" data-reference="long269:eq:carry-matrix">[long269:eq:carry-matrix]</a>: the original kernel carries positive row and column factors that decay, so the conclusion transfers to a weighted uniform norm relative to those factors and not to the unweighted sup norm of $`\operatorname{K}`$. It bounds approximation of the whole infinite matrix, and on any finite range a separated approximant of small rank exists. And it says nothing about approximating the scalar sum, so it yields no irrationality conclusion. What it does add to Theorem <a href="#long269:res:infinite-rank" data-reference-type="ref" data-reference="long269:res:infinite-rank">10</a> is robustness: no finite separated model of the carry, however chosen, gets uniformly closer than half a carry jump. The threshold is exact in both directions, since rank one attains it.

The original kernel behaves differently in the summation norm because its row and column factors decay. Let $`K^{(N)}(i,j,k)=\operatorname{K}(i,j,k)`$ for $`i<N`$ and $`K^{(N)}(i,j,k)=0`$ otherwise. This is a sum of at most $`N`$ terms separated between $`i`$ and $`(j,k)`$. Since $`\operatorname{H}(x)>x^3/(pqr)`$ for $`x>0`$, geometric summation gives
``` math
\begin{equation}
\label{long269:eq:l1-finite-rank-approximation}
 \sum_{i,j,k\ge0}|\operatorname{K}(i,j,k)-K^{(N)}(i,j,k)|
 \le
 \frac{pqr\,p^{-3N}}
 {(1-p^{-3})(1-q^{-3})(1-r^{-3})}.
\end{equation}
```
Hence the original summable kernel has finite separated-rank approximants in $`\ell^1`$, even though its normalised carry matrix has the sharp uniform barrier of Theorem <a href="#long269:res:uniform-rank" data-reference-type="ref" data-reference="long269:res:uniform-rank">12</a>. This norm distinction is why neither statement decides the arithmetic nature of the scalar sum.

<a id="long269:sec:blocks"></a>

# Dyadic blocks and the literal infinite tail

For the rest of the note set $`P=\{2,3,5\}`$ and $`S=\mathcal R_P`$, and write $`\operatorname{H}_a=\operatorname{H}(2^{a})`$ and $`h_a=\operatorname{H}_a/2`$, so that $`h_0=1/2`$ while $`h_a`$ is a positive integer for $`a\ge1`$. Define the dyadic shell mass, its tail and its normalisation by
``` math
\begin{equation}
\label{long269:eq:actual-tail}
 s_a=\sum_{\substack{i,j,k\ge0\\ 2^{a}\le2^{i}3^{j}5^{k}<2^{a+1}}}
       \frac1{\operatorname{H}(2^{i}3^{j}5^{k})},
 \qquad
 U_a=\sum_{j\ge a}s_j,
 \qquad
 X_a=h_aU_a .
\end{equation}
```

Compress the jump word of Section <a href="#long269:sec:lcm" data-reference-type="ref" data-reference="long269:sec:lcm">2</a> into the blocks cut out by consecutive powers of two: block $`a`$ starts just after $`2^{a}`$, contains every pure $`3`$- or $`5`$-power strictly between $`2^{a}`$ and $`2^{a+1}`$, and ends with the jump at $`2^{a+1}`$. A channel cannot occur twice inside one block, because two powers of the same base $`b\ge2`$ inside an interval of ratio $`2\le b`$ must coincide; this is the [checked internal-power uniqueness lemma](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L669) for the [internal-power predicate](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L663). Let $`I_a`$ list the internal jumps $`(p,e)`$ with $`p\in\{3,5\}`$ and $`2^{a}<p^{e}<2^{a+1}`$, in increasing order.

<div id="long269:res:dyadic-alphabet" class="proposition">

**Proposition 13** (the dyadic block alphabet). *For every $`a`$,
``` math
\begin{equation}
\label{long269:eq:dyadic-alphabet}
 b_a=\frac{\operatorname{H}_{a+1}}{\operatorname{H}_a}=2\prod_{(p,e)\in I_a}p\in\{2,6,10,30\},
 \qquad\text{so}\qquad 2\le b_a\le30 .
\end{equation}
```*

</div>

<div class="proof">

*Proof.* Internal-power uniqueness leaves two independent yes-or-no choices, one for the $`3`$-channel and one for the $`5`$-channel. Multiplying the terminal factor $`2`$ by the selected channel factors gives exactly the four displayed cases. ◻

</div>

The definition is the [dyadic block base](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L751), and Lean checks both the [exact four-case alphabet](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L762) and the [bounded-radix consequence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L774). All four letters occur early:
``` math
\begin{array}{c|c|c|c|c}
a & (2^{a},2^{a+1}) & \text{internal }3\text{-power} & \text{internal }5\text{-power} & b_a\\ \hline
0 & (1,2)   & \text{none} & \text{none} & 2\\
1 & (2,4)   & 3           & \text{none} & 6\\
2 & (4,8)   & \text{none} & 5           & 10\\
3 & (8,16)  & 9           & \text{none} & 6\\
4 & (16,32) & 27          & 25          & 30\\
5 & (32,64) & \text{none} & \text{none} & 2
\end{array}
```

For $`p\in P`$ with $`q,r`$ the other two primes, put
``` math
A_p(e)=\#\{(i,j)\in\mathbb{N}^2:q^{i}r^{j}<p^{e}\},\qquad
 C_p(e)=\sum_{u=1}^{e}A_p(u),\qquad C_p(0)=0 ,
```
and for $`(p,e)\in I_a`$ let $`\sigma_a(p,e)`$ be the product of the channels of the later internal jumps of block $`a`$. The *ordered block digit* is
``` math
\begin{equation}
\label{long269:eq:actual-digit}
 m_a=A_2(a+1)+\sum_{(p,e)\in I_a}(p-1)\,\sigma_a(p,e)\,
        \bigl(C_p(e)-C_2(a)\bigr)\quad(a\ge1),
 \qquad m_0=1 ,
\end{equation}
```
the integer implemented by the pinned checker and the [checked ordered digit](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicBlockThresholdPartition.lean#L150). The first four pairs $`(b_a,m_a)`$ from $`a=1`$ are $`(6,4)`$, $`(10,7)`$, $`(6,7)`$, $`(30,65)`$.

<div id="long269:res:actual-orbit" class="theorem">

**Theorem 14** (the literal shell recurrence). *The shell masses are summable and $`S=\sum_{a\ge0}s_a`$. For every $`a\ge0`$,
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

Write the internal jumps as $`t_\ell=p_\ell^{e_\ell}`$, $`1\le\ell\le v`$, and set $`t_0=2^{a}`$, $`t_{v+1}=2^{a+1}`$. Let $`N(t)`$ count smooth positive integers strictly below $`t`$ and put $`n_\ell=N(t_\ell)`$. On $`[t_\ell,t_{\ell+1})`$ the height is $`\operatorname{H}_a\prod_{u\le\ell}p_u`$, and the terminal jump has factor two, so
``` math
h_{a+1}s_a
 =\sum_{\ell=0}^{v}(n_{\ell+1}-n_\ell)\prod_{u>\ell}p_u
 =n_{v+1}-n_0+\sum_{\ell=1}^{v}(p_\ell-1)
        \Bigl(\prod_{u>\ell}p_u\Bigr)(n_\ell-n_0),
```
the second equality being finite summation by parts. Counting by the exponent of $`p`$ gives $`N(p^{e})=C_p(e)`$, so the right-hand side is exactly <a href="#long269:eq:actual-digit" data-reference-type="eqref" data-reference="long269:eq:actual-digit">[long269:eq:actual-digit]</a>; at $`a=0`$ the shell is the single point $`1`$, giving $`m_0=1`$. Positivity follows from $`s_a>0`$. Splitting $`U_a=s_a+U_{a+1}`$ and multiplying by $`h_a`$ gives the recurrence, and $`b_a\cdots b_j=\operatorname{H}_{j+1}/\operatorname{H}_a`$ with $`m_j=h_{j+1}s_j`$ gives $`m_j/(b_a\cdots b_j)=h_as_j`$, whose summation is the last identity. ◻

</div>

Summability is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicShellSummability.lean#L142), and so is the [recurrence for the genuine infinite tail](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicShellSummability.lean#L177), over the [normalised state step](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicOrderedTailRecurrence.lean#L110).

<div id="long269:res:actual-dichotomy" class="proposition">

**Proposition 15** (integral state or cofinal separation). *Either $`X_a\in\mathbb{Z}`$ for some $`a\ge0`$, or for every $`a_0`$ there is $`a\ge a_0`$ with $`|X_a-z|\ge1/31`$ for every $`z\in\mathbb{Z}`$.*

</div>

<div class="proof">

*Proof.* Suppose cofinal separation fails, so for some $`A`$ and every $`a\ge A`$ there is an integer $`z_a`$ with $`e_a=X_a-z_a`$ and $`|e_a|<1/31`$. The recurrence gives $`z_{a+1}-b_az_a+m_a=b_ae_a-e_{a+1}`$. The left side is an integer and the right side has absolute value below $`(30+1)/31=1`$, so both vanish and $`e_{a+1}=b_ae_a`$. Hence $`|e_{A+k}|\ge2^{k}|e_A|`$ for every $`k`$ while $`|e_{A+k}|<1/31`$, which forces $`e_A=0`$. ◻

</div>

This is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicShellSummability.lean#L188) for the genuine infinite tail, over the abstract [integral-state or cofinal-distance alternative](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/BoundedRadixTailEscape.lean#L89). It excludes neither branch, and it says nothing about a rational value whose reduced denominator has a factor coprime to $`30`$: that case is the subject of Section <a href="#long269:sec:actual-orbit" data-reference-type="ref" data-reference="long269:sec:actual-orbit">6</a>.

<a id="long269:sec:actual-orbit"></a>

# A quadratic tail bound and denominator cancellation

Put
``` math
n_a=a+\lfloor\log_3(2^{a})\rfloor+\lfloor\log_5(2^{a})\rfloor,
 \qquad
 Q(n)=\frac{n^{2}+8n+18}{9},
```
so $`n_a`$ is the sum of the three height exponents at $`2^{a}`$.

<div id="long269:res:actual-tail-bound" class="theorem">

**Theorem 16** (quadratic bound for the actual tail). *For every $`a\ge0`$, $`0<X_a\le Q(n_a)`$.*

</div>

<div class="proof">

*Proof.* Partition the smooth integers $`x\ge2^{a}`$ by their height vector $`(A,B,C)=(\lfloor\log_2x\rfloor,\lfloor\log_3x\rfloor,\lfloor\log_5x\rfloor)`$. The cell of a vector is the interval $`[\lambda,\eta)`$ with $`\lambda=\max(2^{A},3^{B},5^{C})`$ and $`\eta=\min(2^{A+1},3^{B+1},5^{C+1})`$, so $`\eta\le2^{A+1}\le2\lambda`$ and, by Lemma <a href="#long269:res:short" data-reference-type="ref" data-reference="long269:res:short">6</a>, fixing the exponents of $`3`$ and $`5`$ leaves at most one exponent of $`2`$. Since $`A\ge B\ge C`$, the cell contains at most
``` math
(B+1)(C+1)\le\frac{(A+B+C+3)^{2}}{9}
```
smooth points: writing $`u=B+1\ge v=C+1`$ and using $`A+1\ge u`$, the difference $`(2u+v)^{2}-9uv=(u-v)(4u-v)`$ is nonnegative. Unique factorisation identifies these exponent triples with distinct smooth integers.

As the cutoff increases all three height exponents are nondecreasing, so two nonempty cells with the same exponent sum are the same cell, and there is at most one nonempty cell of each rank. Every cell above $`2^{a}`$ has rank at least $`n_a`$, and a cell of rank $`n_a+k`$ has height at least $`\operatorname{H}_a2^{k}`$, since each of the $`k`$ extra prime factors is at least $`2`$. Nonnegative summation over ranks, allowing empty ones, gives
``` math
X_a\le\frac1{18}\sum_{k\ge0}\frac{(n_a+k+3)^{2}}{2^{k}}
      =\frac{n_a^{2}+8n_a+18}{9},
```
the evaluation using the geometric moments $`\sum2^{-k}=2`$, $`\sum k2^{-k}=2`$ and $`\sum k^{2}2^{-k}=6`$. Positivity follows from the shell at $`2^{a}`$. ◻

</div>

The rank here is the sum of the three fixed height exponents, not a varying-smoothness density parameter. The estimate uses only unique factorisation, the short-cell counting bound and geometric moments; it does not invoke a Dickman–Hildebrand asymptotic or a Hecke–Mahler theorem.

This is the analytic content of the section: each additional height rank costs a geometric factor while its multiplicity grows only quadratically. The finite projection and the sorted quadratic inequality are the checked ingredients of Proposition <a href="#long269:res:drop" data-reference-type="ref" data-reference="long269:res:drop">7</a>; grouping the actual infinite tail by height cells and summing the majorant is the argument above.

The bound is used at the endpoint of a window, where the natural index is the positive prime-power jump count strictly below the cutoff. Put
``` math
\begin{equation}
\label{long269:eq:endpoint-index}
 j_a=\#\{p^{e}<2^{a}:p\in\{2,3,5\},\ e\ge1\}=n_a-1 ,
\end{equation}
```
the equality holding because the powers of $`2`$ below $`2^{a}`$ number $`a-1`$ while the powers of $`3`$ and of $`5`$ below $`2^{a}`$ number $`\lfloor\log_3 2^{a}\rfloor`$ and $`\lfloor\log_5 2^{a}\rfloor`$. Substituting $`n_a=j_a+1`$ into $`Q`$ gives the integer bound used throughout the rest of the note:
``` math
\begin{equation}
\label{long269:eq:actual-bound}
 K(B,a)=\bigl\lfloor B\,Q(n_a)\bigr\rfloor
 =\left\lfloor\frac{B(j_a^{2}+10j_a+27)}9\right\rfloor .
\end{equation}
```
The cutoff in <a href="#long269:eq:endpoint-index" data-reference-type="eqref" data-reference="long269:eq:endpoint-index">[long269:eq:endpoint-index]</a> is $`2^{a}`$ and it is strict.

<div id="long269:res:all-scale-lattice" class="lemma">

**Lemma 17** (finite denominator clearing). *For all integers $`0\le u\le b`$ the window mass $`h_b\sum_{a=u}^{b-1}s_a`$ is a natural number. If $`S=N/D`$ with $`N\in\mathbb{Z}`$ and $`D\in\mathbb{N}_{>0}`$, then $`DX_a\in\mathbb{Z}`$ for every $`a\ge1`$, and there are indices $`1\le i<j\le D+1`$ for which $`X_i-X_j\in\mathbb{Z}`$.*

</div>

<div class="proof">

*Proof.* An empty window has mass zero. Otherwise $`b\ge1`$, and every integer $`x<2^{b}`$ has $`2`$-height exponent at most $`b-1`$ while its other height exponents are at most those at $`2^{b}`$, so $`\operatorname{H}(x)\mid\operatorname{H}_b/2=h_b`$ and every term of the finite window clears at $`h_b`$. Writing $`v_a=h_a\sum_{u<a}s_u\in\mathbb{N}`$ gives $`DX_a=h_aN-Dv_a\in\mathbb{Z}`$. Among $`D+1`$ of these integers two share a residue modulo $`D`$, and the corresponding states differ by an integer. ◻

</div>

The strict upper endpoint is what permits the division by two. Checked as the [window clearing identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L158), the [all-scale lattice](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L196) and the [collision](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L296), over the [boundary divisibility](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L51) and the [half-height identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L101).

<div id="long269:res:actual-cancellation" class="theorem">

**Theorem 18** (positive reduced carries from rationality). *<span id="long269:res:lead-carry-bridge" label="long269:res:lead-carry-bridge"></span> <span id="long269:res:actual-carry-bound" label="long269:res:actual-carry-bound"></span><span id="long269:res:denominator-reduction" label="long269:res:denominator-reduction"></span> Suppose $`S=N/D`$ with $`N\in\mathbb{Z}`$, $`D\in\mathbb{N}_{>0}`$, and write
``` math
D=2^{u}3^{v}5^{w}B,\qquad u,v,w\in\mathbb{N},\quad B\in\mathbb{N}_{>0},\quad\gcd(B,30)=1,
 \qquad a_D=u+1+2v+3w .
```
Then for every $`a\ge a_D`$ the number $`z_a=BX_a`$ is a positive integer and
``` math
z_{a+1}=b_az_a-Bm_a,\qquad 1\le z_a\le K(B,a)\le90B(a+1)^{2} .
```*

</div>

<div class="proof">

*Proof.* Let $`M=2^{u}3^{v}5^{w}`$. For $`a\ge a_D`$ we have $`2^{a}\ge2^{u+1}`$, $`2^{a}\ge3^{v}`$ and $`2^{a}\ge5^{w}`$, using $`3<2^{2}`$ and $`5<2^{3}`$; hence $`M\mid h_a`$. In the clearing identity $`DX_a=h_aN-Dv_a`$ of Lemma <a href="#long269:res:all-scale-lattice" data-reference-type="ref" data-reference="long269:res:all-scale-lattice">17</a> both terms on the right are divisible by $`M`$, so dividing by $`M`$ shows that $`BX_a`$ is an integer. Positivity and the recurrence come from <a href="#long269:eq:shell-digit-identity" data-reference-type="eqref" data-reference="long269:eq:shell-digit-identity">[long269:eq:shell-digit-identity]</a>, and the upper bound is Theorem <a href="#long269:res:actual-tail-bound" data-reference-type="ref" data-reference="long269:res:actual-tail-bound">16</a> with the floor taken, since $`z_a`$ is an integer below $`BQ(n_a)`$. Finally $`n_a\le3a`$, so $`Q(n_a)\le a^{2}+\tfrac83a+2\le90(a+1)^{2}`$. ◻

</div>

The smooth part $`M`$ affects only the onset $`a_D`$; the surviving carry bound depends on the coprime factor $`B`$. The bridge is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalityCarryBridge.lean#L324) against the cruder width $`90B(a+1)^{2}`$, which is the form the formal consumer uses; the particular onset $`a_D=u+1+2v+3w`$ and the sharper bound $`K(B,a)`$ are the paper statement above. The abstract cancellation is checked separately: every fixed smooth factor divides the running height once the cutoff reaches it ([absorption](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L548)), a shared factor cancels from the recurrence ([cancellation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L581)), and positivity, the bound and the window identity descend through it ([bound transfer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L601), [window transfer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L612)).

The integral branch has one further exact property, recorded because it constrains any attempt to build a surviving seed by hand.

<div id="long269:res:pinning" class="proposition">

**Proposition 19** (upward closure and rigidity). *For every $`a`$, $`X_a=(m_a+X_{a+1})/b_a>0`$, and if $`X_a\in\mathbb{Z}`$ then $`X_n\in\mathbb{Z}`$ for every $`n\ge a`$. Moreover, fix $`A`$, a positive width function $`w`$ with $`w(A+k)/2^{k}\to0`$, and a real orbit $`(y_n)_{n\ge A}`$ satisfying $`y_{n+1}=b_ny_n-m_n`$. If $`y_n`$ and $`X_n`$ both lie in $`(m_n/b_n,\;m_n/b_n+w(n)]`$ for every $`n\ge A`$, then $`y_A=X_A`$.*

</div>

<div class="proof">

*Proof.* The identity is the recurrence solved for $`X_a`$, and positivity holds because every shell contains its dyadic left endpoint. Integer coefficients give upward closure. For the last assertion, the difference of the two orbits is multiplied by $`b_n\ge2`$ at each step while the common window bounds its absolute value at time $`A+k`$ by $`w(A+k)`$, so $`2^{k}|y_A-X_A|\le w(A+k)`$ and the stated decay forces equality. ◻

</div>

<a id="long269:sec:escape"></a>

# Residue windows and the equivalence band

The statements of this section are about integer sequences. For a start $`\ell\ge1`$ and a length $`h\ge1`$ define
``` math
W_{\ell,h}=\prod_{j=0}^{h-1}b_{\ell+j},
 \qquad
 F_{\ell,0}=0,
 \qquad
 F_{\ell,h+1}=b_{\ell+h}F_{\ell,h}+m_{\ell+h},
```
the [window base](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L417) and the [window forcing](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L422). Iterating the recurrence gives the division-free identity
``` math
\begin{equation}
\label{long269:eq:window-identity}
 X_{\ell+h}=W_{\ell,h}X_\ell-F_{\ell,h},
 \qquad\text{and}\qquad
 z_{\ell+h}=W_{\ell,h}z_\ell-BF_{\ell,h}
\end{equation}
```
for any integral carry with $`z_{n+1}=b_nz_n-Bm_n`$; the integral form is the [checked window identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L480), over the [affine window identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L455) and the [scaled forcing identity](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L469), and the real form is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L68) for the genuine tail. For $`C>0`$ let $`\operatorname{lpr}_C(N)`$ be the unique integer in $`\{1,\ldots,C\}`$ congruent to $`N`$ modulo $`C`$, so $`\operatorname{lpr}_C(0)=C`$; this is the [canonical representative](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L26), with its [range](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L31) and its [congruence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L52) checked. The vanishing residue is represented by $`C`$, and that choice is what makes the next statement a modular one.

<div id="long269:res:consumer" class="proposition">

**Proposition 20** (the finite residue contradiction). *Let $`C>0`$ and let $`c`$ be an integer with $`0<c`$ and $`|c|\le K`$. If $`c\equiv N\pmod C`$ and $`K<\operatorname{lpr}_C(N)`$, then the hypotheses are contradictory.*

</div>

<div class="proof">

*Proof.* The canonical representative lies in $`\{1,\ldots,C\}`$, and the inequalities put $`c`$ strictly between $`0`$ and $`C`$. If $`N\equiv0\pmod C`$ its representative is $`C`$ while $`c\bmod C=c\ne0`$. Otherwise $`c`$ and $`\operatorname{lpr}_C(N)`$ are each their own residue and congruence makes them equal, contradicting $`|c|\le K<\operatorname{lpr}_C(N)`$. ◻

</div>

The abstract one-window predicate is the [residue-escape condition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L71), with the contrapositive [bounding the residue from a bounded positive state](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L96). The natural-state version is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L76), the integer carry version is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L110), and the exact classifier $`\operatorname{lpr}_C(N)=|c|`$ under $`|c|\le C`$ is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L138) as well. Applying it inside a window uses the forcing of the endpoint carry to the canonical residue, [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L497).

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
The window may depend on both $`B`$ and $`a_0`$. The general predicate is the [cofinal local-window escape condition](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L629), and the instance at the fixed bound $`K_0(B,a)=90B(a+1)^{2}`$ is the [actual producer](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalityCarryBridge.lean#L397). Every $`b_a`$ is positive, so $`W_{\ell,h}>0`$ is automatic.

<div id="long269:res:actual-escape-endpoint" class="theorem">

**Theorem 21** (the equivalence band). *<span id="long269:res:lead-escape-equivalence" label="long269:res:lead-escape-equivalence"></span><span id="long269:res:windowconsumer" label="long269:res:windowconsumer"></span> Let $`G:\mathbb{N}_{>0}\times\mathbb{N}\to\mathbb{N}`$ satisfy $`K(B,a)\le G(B,a)`$ for all $`B`$ and $`a`$, and $`G(B,a)/2^{a}\to0`$ as $`a\to\infty`$ for each fixed $`B`$. Then
``` math
\mathsf E(G)\quad\Longleftrightarrow\quad S\notin\mathbb{Q}.
```
Both $`K`$ of <a href="#long269:eq:actual-bound" data-reference-type="eqref" data-reference="long269:eq:actual-bound">[long269:eq:actual-bound]</a> and $`K_0(B,a)=90B(a+1)^{2}`$ lie in this band, so $`\mathsf E(K)`$, $`\mathsf E(K_0)`$ and irrationality of $`S`$ are mutually equivalent. The lower half of the band cannot be dropped: $`\mathsf E(0)`$ holds vacuously, since every least positive residue is at least $`1`$.*

</div>

<div class="proof">

*Proof.* Suppose $`\mathsf E(G)`$ and suppose $`S=N/D`$ were rational. Theorem <a href="#long269:res:actual-cancellation" data-reference-type="ref" data-reference="long269:res:actual-cancellation">18</a> supplies $`B\ge1`$ coprime to $`30`$, an onset $`a_D`$, and positive integers $`z_a=BX_a\le K(B,a)\le G(B,a)`$ for $`a\ge a_D`$ satisfying the cleared recurrence. Apply <a href="#long269:eq:actual-escape" data-reference-type="eqref" data-reference="long269:eq:actual-escape">[long269:eq:actual-escape]</a> with $`a_0=a_D`$ to obtain a window $`(\ell,h)`$ with $`\ell\ge a_D`$. By <a href="#long269:eq:window-identity" data-reference-type="eqref" data-reference="long269:eq:window-identity">[long269:eq:window-identity]</a>, $`z_{\ell+h}\equiv-BF_{\ell,h}`$ modulo $`W_{\ell,h}`$, while $`0<z_{\ell+h}\le G(B,\ell+h)<\operatorname{lpr}_{W_{\ell,h}}(-BF_{\ell,h})`$. Proposition <a href="#long269:res:consumer" data-reference-type="ref" data-reference="long269:res:consumer">20</a> is the contradiction, so $`S`$ is irrational.

Conversely suppose $`S\notin\mathbb{Q}`$, and fix $`B\ge1`$ coprime to $`30`$ and $`a_0\ge1`$. Set $`\ell=a_0`$. In $`X_\ell=h_\ell\bigl(S-\sum_{a<\ell}s_a\bigr)`$ the finite prefix is rational and $`h_\ell`$ is a positive rational, so $`BX_\ell`$ is irrational and its distance $`\delta`$ from $`\mathbb{Z}`$ is positive. Suppose no length $`h`$ escaped, so that $`r_h=\operatorname{lpr}_{W_{\ell,h}}(-BF_{\ell,h})\le G(B,\ell+h)`$ for every $`h\ge1`$. Then $`k_h=(BF_{\ell,h}+r_h)/W_{\ell,h}`$ is an integer, and multiplying <a href="#long269:eq:window-identity" data-reference-type="eqref" data-reference="long269:eq:window-identity">[long269:eq:window-identity]</a> by $`B`$ gives
``` math
BX_\ell-k_h=\frac{BX_{\ell+h}-r_h}{W_{\ell,h}} .
```
Both $`BX_{\ell+h}`$ and $`r_h`$ are positive, the first at most $`BQ(n_{\ell+h})`$ by Theorem <a href="#long269:res:actual-tail-bound" data-reference-type="ref" data-reference="long269:res:actual-tail-bound">16</a> and the second at most $`G(B,\ell+h)`$, so the numerator has absolute value at most $`\max\bigl(BQ(n_{\ell+h}),G(B,\ell+h)\bigr)`$. Each $`b_a\ge2`$ gives $`W_{\ell,h}\ge2^{h}`$, so
``` math
\begin{aligned}
 0<\delta\le|BX_\ell-k_h|
 &\le\frac{\max\bigl(BQ(n_{\ell+h}),\,G(B,\ell+h)\bigr)}{2^{h}}\\
 &=2^{\ell}\cdot
 \frac{\max\bigl(BQ(n_{\ell+h}),\,G(B,\ell+h)\bigr)}{2^{\ell+h}}
 \longrightarrow0.
 \end{aligned}
```
as $`h\to\infty`$, because $`Q(n_{\ell+h})`$ is quadratic in $`\ell+h`$ and $`G(B,a)=o(2^{a})`$. This contradiction proves $`\mathsf E(G)`$.

For the two named bounds, $`K\le K_0`$ by Theorem <a href="#long269:res:actual-cancellation" data-reference-type="ref" data-reference="long269:res:actual-cancellation">18</a>, both are quadratic in $`a`$ for fixed $`B`$, and $`K\le K`$ trivially. Finally $`\operatorname{lpr}_C(N)\ge1>0`$ always, so $`\mathsf E(0)`$ holds whatever $`S`$ is, while $`0\le K`$ fails. ◻

</div>

The converse direction is checked in Lean at a strictly greater generality than the fixed bound: irrationality implies escape against any short bound that the window growth eventually beats, [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L327), and in particular against every bound dominated by $`c(B)(n+1)^{2}`$, [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L355). The enlarged little-$`o(8^a)`$ band, with the cap-domination hypothesis retained, is checked by the [octic window-band equivalence](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/R12/OcticWindowBand.lean#L74). The forward direction at the fixed bound $`K_0`$ is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalityCarryBridge.lean#L479), over the abstract consumer [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L645) and its packaged absorbed form [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L689). The two directions combine into the equivalence [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L392) for the shifted tail and [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L398) for the series value itself. The Lean equivalence is stated at $`K_0`$; the band of Theorem <a href="#long269:res:actual-escape-endpoint" data-reference-type="ref" data-reference="long269:res:actual-escape-endpoint">21</a> is the paper statement.

Theorem <a href="#long269:res:actual-escape-endpoint" data-reference-type="ref" data-reference="long269:res:actual-escape-endpoint">21</a> settles a question that a reader is entitled to ask about the criterion. Sharpening the bound below $`K`$ does not weaken the producer, since escape against a bound that fails to dominate the actual carries proves nothing; the zero bound is the extreme case. Enlarging the bound up to any subexponential function does not weaken it either. The producer is therefore a restatement of Erdős #269 for $`P=\{2,3,5\}`$ throughout the band, and work on it is work on the target. Equivalence preserves truth and settles nothing about difficulty, so the reformulation may still be the easier representation to attack; what it does not admit is a cheaper bound.

Two exact countermodels rule out further shortcuts. For $`(W,F,B)=(6,4,1)`$ we have $`\operatorname{lpr}_6(-4)=2`$, so the canonical residue need not be coprime to the accumulated base. For $`(W,F,B)=(60,47,37)`$ we have $`\operatorname{lpr}_{60}(-37\cdot47)=1`$, so a fixed window has no denominator-independent lower bound on that residue. The window may therefore depend genuinely on $`B`$.

<a id="how-fast-the-window-base-grows"></a>

## How fast the window base grows

The crude estimate $`W_{\ell,h}\ge2^{h}`$ is all the equivalence needs. The actual height formula gives more, and the extra information sets the scale of any finite search.

<div id="long269:res:window-growth" class="proposition">

**Proposition 22** (window-growth law). *Put $`\theta_3=\log_32`$ and $`\theta_5=\log_52`$. For all $`\ell\ge0`$ and $`h\ge1`$,
``` math
W_{\ell,h}=2^{h}\,
 3^{\lfloor(\ell+h)\theta_3\rfloor-\lfloor\ell\theta_3\rfloor}\,
 5^{\lfloor(\ell+h)\theta_5\rfloor-\lfloor\ell\theta_5\rfloor},
 \qquad
 \frac{8^{h}}{15}<W_{\ell,h}<15\cdot8^{h} .
```*

</div>

<div class="proof">

*Proof.* Telescoping <a href="#long269:eq:dyadic-alphabet" data-reference-type="eqref" data-reference="long269:eq:dyadic-alphabet">[long269:eq:dyadic-alphabet]</a> gives $`W_{\ell,h}=\operatorname{H}_{\ell+h}/\operatorname{H}_\ell`$, and the displayed formula is that quotient written out. Each floor difference differs from $`h\theta_p`$ by less than one, and $`3^{\theta_3}=5^{\theta_5}=2`$, so the $`3`$-factor lies strictly between $`2^{h}/3`$ and $`3\cdot2^{h}`$ and the $`5`$-factor strictly between $`2^{h}/5`$ and $`5\cdot2^{h}`$. Multiplying the three ranges gives the bounds. ◻

</div>

<div id="long269:res:no-bounded-length" class="corollary">

**Corollary 23** (no bounded-length escape at all starts). *Fix $`B\ge1`$ coprime to $`30`$ and $`H\ge1`$. Only finitely many starts $`\ell`$ admit an escaping window of length at most $`H`$ against the bound $`K`$.*

</div>

<div class="proof">

*Proof.* A least positive residue never exceeds its modulus, so escape at $`(\ell,h)`$ requires $`K(B,\ell+h)<W_{\ell,h}<15\cdot8^{h}\le15\cdot8^{H}`$. On the other hand $`j_a\ge a-1`$, since the powers $`2,\ldots,2^{a-1}`$ already lie below $`2^{a}`$, so $`K(B,\ell+h)\ge\lfloor B((\ell-1)^{2}+10(\ell-1)+27)/9\rfloor`$, which tends to infinity with $`\ell`$. ◻

</div>

Corollary <a href="#long269:res:no-bounded-length" data-reference-type="ref" data-reference="long269:res:no-bounded-length">23</a> is the exact reason a finite scan cannot approach the cofinal quantifier by widening its denominator range alone. Rearranging its inequality, an escaping window at start $`\ell`$ and endpoint $`a=\ell+h`$ must satisfy
``` math
3h>\log_2K(B,a)-\log_215,
```
so the necessary search depth grows like $`\bigl(\log_2B+2\log_2\ell\bigr)/3`$. This is a lower bound on the length that can possibly work, and it is not an upper bound on the first length that does. Producing the latter is exactly the open problem, and by Theorem <a href="#long269:res:actual-escape-endpoint" data-reference-type="ref" data-reference="long269:res:actual-escape-endpoint">21</a> it needs effective control of $`\operatorname{dist}(BX_\ell,\mathbb{Z})`$: counting window growth is easy, and keeping a scaled tail away from the integers is the arithmetic content.

*Status.* The problem treated here is open, and this note does not close it. Every statement below marked as checked is a proposition that the pinned Lean kernel accepts from the sources this note links to, with no `sorry`, no added axiom, and no unchecked evaluation. That is a claim about the formal statement, not about its mathematical interest, its novelty, or the original problem. The unresolved obligations are named exactly, in their own section, and none of the finite computations, reductions, or no-go results here removes one of them.

*Companion system context.* The [claim and trust boundary](../mirror/claim-faithful-publication-systems-paper.pdf#nameddest=systems-trust), [cold-clone route to proof authority](../mirror/cold-clone-to-proof-receipt.pdf#nameddest=cold-clone-authority), and [public contribution protocol](../mirror/open-source-mathematics-strategy.pdf#nameddest=strategy-protocol) are described in sibling papers. Those descriptions do not change the mathematical status of this note.

<a id="long269:sec:evidence"></a>

# The finite evidence

Three finite computations bear on the problem. Each is exact integer or certified-enclosure arithmetic, none is a Lean theorem, and none settles an instance.

<a id="the-dyadic-window-scan"></a>

## The dyadic-window scan

A *certificate* is a finite tuple of integers recording one instance of the inequality in <a href="#long269:eq:actual-escape" data-reference-type="eqref" data-reference="long269:eq:actual-escape">[long269:eq:actual-escape]</a>, so that a reader can recheck it in a line. The integer-only [dyadic-window checker](https://github.com/wcook04/plectis-lean-erdos249-257/tree/ee650b32b8b2cb98b94e5500df5370d85f7403b8/scripts/check_erdos269_dyadic_windows.py) constructs the ordered pure-power jumps, the block bases and the block digits from exact multiplicity counts, and reproduces the following, with columns the denominator $`B`$, the start $`\ell`$, the length $`h`$, the endpoint jump index $`j_{\ell+h}`$, the window base, the forcing, the residue $`R=\operatorname{lpr}_{W}(-BF)`$ and the bound $`K`$ of <a href="#long269:eq:actual-bound" data-reference-type="eqref" data-reference="long269:eq:actual-bound">[long269:eq:actual-bound]</a>.
``` math
\begin{array}{c|c|c|c|r|r|r|r}
B&\ell&h&j_{\ell+h}&W&F&R&K\\ \hline
1&1&2&4&60&47&13&9\\
7&1&3&5&360&289&137&95\\
16&1&4&7&10800&8735&640&352
\end{array}
```
The first row reads as follows. The window starts at $`\ell=1`$ and has length $`2`$, so $`W=b_1b_2=6\cdot10=60`$; the accumulated forcing is $`F=47`$; and $`\operatorname{lpr}_{60}(-47)=13`$, since $`-47+60=13`$, which exceeds $`K(1,3)=\lfloor(16+40+27)/9\rfloor=9`$. The third row lies outside the domain of <a href="#long269:eq:actual-escape" data-reference-type="eqref" data-reference="long269:eq:actual-escape">[long269:eq:actual-escape]</a>, since $`\gcd(16,30)=2`$, and is displayed to illustrate the window arithmetic at greater depth.

A fresh scan over every $`B\le5000`$ coprime to $`30`$ and every $`100\le\ell\le3000`$ tested $`3{,}869{,}934`$ pairs and found an escaping window in every case, of length at most $`18`$ with search depth permitted to $`24`$. The distribution of first successful lengths concentrates at $`10`$ to $`12`$, which is where Corollary <a href="#long269:res:no-bounded-length" data-reference-type="ref" data-reference="long269:res:no-bounded-length">23</a> predicts the shortest possible window to lie over this range. The computation uses integers only and is reproducible from the pinned checker with `--max-denominator 5000 --start-min 100 --start-max 3000 --max-length 24 --assert-packet`. Neither the scan nor the three displayed certificates proves escape for unbounded $`B`$ or for cofinally many starts, and by Corollary <a href="#long269:res:no-bounded-length" data-reference-type="ref" data-reference="long269:res:no-bounded-length">23</a> no scan at bounded length can.

<a id="two-finite-denominator-exclusions"></a>

## Two finite denominator exclusions

<div id="long269:res:lead-block-exclusion" class="theorem">

**Theorem 24** (window-$`128`$ block exclusion, computational certificate). *At window length $`L=128`$, launch $`a_1=10005`$ and $`64`$ starts, no rational value of the $`\{2,3,5\}`$ running-LCM series has reduced denominator $`MB`$ with $`M`$ a $`30`$-smooth divisor of $`2^{10005}3^{6312}5^{4308}`$, $`\gcd(B,30)=1`$ and $`1<B\le B_{\max}`$, where $`B_{\max}`$ is the $`106`$-digit integer
``` math
\begin{aligned}
 B_{\max}={}&1134599670999687767349520845707093359257353022286558739363600235\\
 &016103207564063373270305324172145281971729 ,
\end{aligned}
```
so that $`\log_2B_{\max}=348.9846\ldots`$*

</div>

The exponent triple $`(10005,6312,4308)`$ is the height exponent triple of $`\operatorname{H}(2^{10005})`$, so the certificate normalises by the full height at its launch. Lemma <a href="#long269:res:all-scale-lattice" data-reference-type="ref" data-reference="long269:res:all-scale-lattice">17</a> normalises by the half height $`h_{10005}`$; the certificate’s smooth family is accordingly the larger one. The recorded quantities are the window product with $`\log_2P=386.40993\ldots`$, the exclusion index $`J=1`$ certified from a reduced basis lying inside the per-start budget, an enclosure of width $`9.674\times10^{-227}`$, and a maximum ratio $`\max X/W=0.185997`$. This is a computational certificate and nothing else: no Lean declaration carries any part of it, so it rests on the correctness of the exact integer engine that produced it, and the certificate record is held in the author’s formal-mathematics archive, outside the public source of this release.

<div id="long269:res:cf-exclusion" class="theorem">

**Theorem 25** (continued-fraction exclusion, computational certificate). *The normalised tail $`X_1`$ has $`13{,}109`$ certified partial quotients, so it is not rational with denominator at most $`2^{22482}`$, about $`10^{6768}`$.*

</div>

The certification is by common prefix of the continued fractions of the two endpoints of an interval provably containing $`X_1`$, so no approximation heuristic enters, and the truncation was independently checked to agree with the direct smooth-number sum as an exact rational. The machine-readable witness and replay receipt for this large computation are not included in the public release, so the statement remains an archived ordinary computational certificate rather than a publicly replayed or Lean-checked result. The recorded statistics are a largest denominator of $`22{,}483`$ bits, a largest partial quotient of $`129{,}114`$, a mean partial quotient of $`23.4133`$, observed Gauss–Kuzmin frequencies $`0.4208`$, $`0.1665`$, $`0.0917`$, $`0.0575`$, $`0.0391`$ against the predicted $`0.4150`$, $`0.1699`$, $`0.0931`$, $`0.0589`$, $`0.0406`$, and a Lévy constant of $`1.18869`$ against $`\pi^{2}/(12\log2)=1.18657`$. No Liouville behaviour and no algebraic or self-similar continued-fraction structure appears below that height.

Each exclusion is finite and neither contains the other: one is indexed by a lattice at a fixed launch and fixed smooth part, the other by continued-fraction depth at $`a=1`$. Denominators beyond the recorded finite ranges are not excluded by either certificate, so neither settles an instance of the problem.

<a id="long269:sec:open"></a>

# The remaining arithmetic questions

<div id="long269:prob:producer" class="problem">

**Problem 26** (actual cofinal residue escape). Prove $`\mathsf E(K)`$ for the actual digits <a href="#long269:eq:actual-digit" data-reference-type="eqref" data-reference="long269:eq:actual-digit">[long269:eq:actual-digit]</a> and the bound <a href="#long269:eq:actual-bound" data-reference-type="eqref" data-reference="long269:eq:actual-bound">[long269:eq:actual-bound]</a>.

</div>

Every term in this question is a finite integer quantity, and a proof must produce a later window for every reduced denominator and every prescribed onset. The tail estimate and the smooth-factor cancellation are proved above and are not additional hypotheses. By Theorem <a href="#long269:res:actual-escape-endpoint" data-reference-type="ref" data-reference="long269:res:actual-escape-endpoint">21</a> the problem is a restatement of Erdős #269 for $`P=\{2,3,5\}`$.

<div id="long269:prob:tails269" class="problem">

**Problem 27** (nonintegrality of every reduced tail). For every $`B\ge1`$ with $`\gcd(B,30)=1`$ and every $`a\ge1`$, prove
``` math
\begin{equation}
\label{long269:eq:tail-nonintegrality}
 BX_a\notin\mathbb{Z}.
\end{equation}
```

</div>

<div id="long269:res:tails-equivalence" class="proposition">

**Proposition 28** (the reduced-tail question is also the target). *Statement <a href="#long269:eq:tail-nonintegrality" data-reference-type="eqref" data-reference="long269:eq:tail-nonintegrality">[long269:eq:tail-nonintegrality]</a>, quantified over every $`B\ge1`$ coprime to $`30`$ and every $`a\ge1`$, is equivalent to irrationality of $`S`$.*

</div>

<div class="proof">

*Proof.* If $`BX_a\in\mathbb{Z}`$ for some such $`B`$ and $`a`$, then $`X_a\in\mathbb{Q}`$, and since $`S=\sum_{j<a}s_j+X_a/h_a`$ with $`h_a`$ a positive rational and the prefix a finite sum of rationals, $`S\in\mathbb{Q}`$. Conversely if $`S\in\mathbb{Q}`$, then Theorem <a href="#long269:res:actual-cancellation" data-reference-type="ref" data-reference="long269:res:actual-cancellation">18</a> produces $`B`$ coprime to $`30`$ with $`BX_a\in\mathbb{Z}`$ for every $`a\ge a_D`$. ◻

</div>

The abstract form of the first implication is [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/BoundedRadixTailEscape.lean#L183). Problem <a href="#long269:prob:tails269" data-reference-type="ref" data-reference="long269:prob:tails269">27</a> is therefore a second restatement of the target, and its pointwise shape is the more convenient one: if $`BX_a`$ is integral at one index, the integer-coefficient recurrence makes it integral at every later index, so a single index decides it. Proposition <a href="#long269:res:actual-dichotomy" data-reference-type="ref" data-reference="long269:res:actual-dichotomy">15</a> does not exclude that branch, since it constrains $`X_a`$ alone and a rational value may keep a surviving denominator coprime to $`30`$.

<a id="the-analytic-route-and-what-it-would-need"></a>

## The analytic route and what it would need

For the de-duplicated series put
``` math
\mathcal D_{2,3,5}=1+
 \sum_{t\in\{2^{n},3^{n},5^{n}:n\ge1\}}
 \frac{1}{2^{\lfloor\log_2t\rfloor}3^{\lfloor\log_3t\rfloor}
           5^{\lfloor\log_5t\rfloor}} ,
```
whose dyadic coding is the joint rotation word $`\delta_{3,a}=\lfloor(a+1)\theta_3\rfloor-\lfloor a\theta_3\rfloor`$ and $`\delta_{5,a}=\lfloor(a+1)\theta_5\rfloor-\lfloor a\theta_5\rfloor`$, with $`b_a=2\cdot3^{\delta_{3,a}}5^{\delta_{5,a}}`$.

<div id="long269:prob:representation" class="problem">

**Problem 29** (function-faithful two-dimensional representation). Express $`\mathcal D_{2,3,5}`$ as a nonconstant algebraic combination of values of a specified two-dimensional Hecke–Mahler, cone-generating or multivariate Mahler function and verify every hypothesis of a published value theorem; or give a conditional theorem under an explicit logarithmic nondegeneracy hypothesis; or prove that the literal series has no representation in the specified finite-dimensional class.

</div>

Individual irrationality of $`\theta_3`$ and $`\theta_5`$ is what Theorem <a href="#long269:res:infinite-rank" data-reference-type="ref" data-reference="long269:res:infinite-rank">10</a> uses, and it is weaker than the joint equidistribution or the rational independence of $`1,\theta_3,\theta_5`$ that a two-dimensional value theorem may need; the stronger hypothesis is not assumed anywhere above. The finite-observer formalisation isolates the precise faithfulness requirement: equality in a finite observer must imply equality after symbolic realisation, and a genuine finite-dimensional factorisation forces the realised symbolic span to be finite-dimensional ([residue-coboundary form](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L109), [symbolic realisation](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L293), [checked](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L334)), with the carry residue and residue digit confined to their declared intervals ([carry interval](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L150), [digit interval](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L157)). No theorem here proves that the literal realised span is infinite.

<a id="structural-constraints-already-in-place"></a>

## Structural constraints already in place

The radix alphabet extends without difficulty. For ordered primes $`p_1<\cdots<p_s`$ an interval $`(p_1^{a},p_1^{a+1})`$ contains at most one power from each other channel, because consecutive $`p_i`$-powers have ratio $`p_i>p_1`$, so its block radix belongs to the $`2^{s-1}`$-letter alphabet $`\{p_1\prod_{i=2}^{s}p_i^{\varepsilon_i}:\varepsilon_i\in\{0,1\}\}`$. The quantitative questions are the interesting ones: effective recurrence or discrepancy for the actual four-letter $`\{2,6,10,30\}`$ word, an asymptotic with an error term for the restricted two-dimensional shell counts that generate $`m_a`$, or the exact separated rank of the literal kernel under a specified family of shifts.

Three-channel rigidity and carry-lift extinction already exclude one proposed argument in four exact steps. Under channel surjectivity, ordinary block nullity is equivalent to the perturbation being a coboundary of a channel potential ([potential classifier](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreeChannelBlockRigidity.lean#L59)). Zero perturbations on genuine $`2\to3`$ and $`2\to5`$ transitions then identify all three potential values and force the perturbation to vanish at every index. For an integral lift, that vanishing makes a nonzero initial error grow by the exact product of the successive bases, and bases at least two make its absolute value at least $`2^{N}`$, contradicting even a single index-$`N`$ bound strictly below $`2^{N}`$ ([one-index extinction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L178)); consequently no uniform bound on the lift error can hold either ([uniform extinction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L238)). A separate four-state calculation reaches the obstruction earlier: four real states in $`(0,1)`$ with unit-accuracy integral lifts and the two anchor equalities force the first complete $`2`$-block sum to be $`1`$, so that block cannot be null ([first-block sum](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L289), [four-state obstruction](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L308)).

These lift conclusions are conditional. The paper constructs the actual orbit and its bounded integral carry under rationality, and it does not construct a faithful lift with the two anchors or the block nullity those auxiliary statements require. The actual carry supplies a weighted block defect instead, so any successful argument along that line must use the weighted identity or construct a different faithful lift.

A single conditional single-channel criterion is also on record. For the pure $`2`$-channel sum the Cantor states lie in an explicit open interval ([confinement](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/PurePowerIrrationality.lean#L61)), consecutive states are separated ([gap bound](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/PurePowerIrrationality.lean#L74)), a small nonzero linear form forces irrationality ([criterion](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/PurePowerIrrationality.lean#L94)), and clearing together with small gaps assembles to irrationality ([assembly](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/PurePowerIrrationality.lean#L156)). The clearing and small-gap hypotheses are not discharged for any concrete series, so no irrationality statement follows from them here.

<a id="where-the-problem-stands"></a>

## Where the problem stands

Erdős #269 is settled for $`|P|=2`$, at the level of transcendence, and open for every $`|P|\ge3`$. For $`P=\{2,3,5\}`$ the reduction is complete on the arithmetic side: the literal digit, the tail, the integral recurrence, the smooth-factor cancellation, the explicit onset and the sharp carry bound all refer to the same series, and Theorem <a href="#long269:res:actual-escape-endpoint" data-reference-type="ref" data-reference="long269:res:actual-escape-endpoint">21</a> shows that the one remaining condition is the problem itself throughout an entire band of bounds. Three obstructions mark the limits. Arbitrary-order minors exclude every finite exact separation of the kernel, and Theorem <a href="#long269:res:uniform-rank" data-reference-type="ref" data-reference="long269:res:uniform-rank">12</a> excludes even approximate separation of its normalised carry below half a jump. The bounded-radix alternative leaves integral tails untouched. The residue countermodels show that coprimality alone gives no denominator-independent residue bound, and Corollary <a href="#long269:res:no-bounded-length" data-reference-type="ref" data-reference="long269:res:no-bounded-length">23</a> shows that no bounded-length search can reach the cofinal quantifier. What remains is to force the literal word’s residue outside the finite carry interval, with the window allowed to depend on the denominator and to begin beyond the onset.

<a id="statements-and-declarations"></a>

## Statements and declarations

<a id="evidence."></a>

#### Evidence.

Steve Fan’s two-prime argument is an ordinary proof over the cited Bugeaud–Laurent theorem and carries no Lean declaration. The arbitrary-order kernel minors and the exclusion of finite separation are Lean theorems in `KernelCarryRank`. The named source statements for the literal recurrence and fixed-split rationality bridge are Lean theorems as well. The [source-current validation receipt](https://github.com/wcook04/plectis-erdos/blob/06f57893e0f9c6d80668048f26f096367ae4cfe7/verification/erdos269-wavea-validation.json) byte-matches these modules and records their compilation inside the public recursive import closure; its named declaration-by-declaration axiom audit is for the R12 Wave A results, not for these rank declarations. Comparator names the finite $`(2,3,5)`$ minor $`-1/15`$, the running-LCM height identity, and a conditional carry-escape consumer; it is not the evidence for the arbitrary-order theorem. The actual-series reduction is given; the source-specific cofinal escape remains unproved. Named Lean sources below are locators, not a blanket end-to-end coverage claim. The quadratic tail bound, the explicit onset $`a_D`$, the sharp bound $`K`$, and Theorem <a href="#long269:res:uniform-rank" data-reference-type="ref" data-reference="long269:res:uniform-rank">12</a> are ordinary proofs in this paper; the three finite computations of Section <a href="#long269:sec:evidence" data-reference-type="ref" data-reference="long269:sec:evidence">8</a> are computational certificates.

<a id="artefact-and-data-availability."></a>

#### Artefact and data availability.

The [pinned formal-source revision](https://github.com/wcook04/plectis-lean-erdos249-257/tree/ee650b32b8b2cb98b94e5500df5370d85f7403b8) contains the Lean sources, the fixed toolchain, the library manifest, and the exact dyadic-window checker used in the finite scan. Proof authority rests in those pinned sources. The present text is exposition and navigation.

<a id="funding-and-competing-interests."></a>

#### Funding and competing interests.

This work received no external funding. The author declares no competing interests.

<a id="acknowledgements."></a>

#### Acknowledgements.

The two-prime factorisation, its Hecke–Mahler reduction and the running-LCM identity for every $`|P|`$ are credited to Steve Fan. The transcendence input is credited to Yann Bugeaud and Michel Laurent and to the earlier work of Loxton and van der Poorten cited by them. The problem numbering and status follow the Erdős Problems catalogue maintained by Thomas Bloom \[erdosproblems\].

<a id="long269:long:extended"></a>

# Extended record: migrated arguments and finite evidence

This part of the record holds material that the short note compressed or moved. Nothing here is an additional result; every statement is either an auxiliary form of a theorem of the note, a historical or bibliographic detail, or the exact source inventory. The canonical references are the note’s own labels.

<a id="long269:long:history"></a>

## The historical and catalogue record

In the primary 1988 source Erdős states the infinite-$`P`$ assertion as a simple exercise and presents persistence for a finite number of primes greater than one as a probable extension, and not as a theorem \[erdos1988, p. 106\]. The current open status is supplied by the catalogue \[erdosproblems\], and is not inferred from that conjectural wording. The 1974 letter writes “given primes $`p_1,\ldots,p_r`$” without explicitly restricting $`r`$, so the singleton case, whose value is $`p/(p-1)`$, must be excluded by hand; the modern restriction $`|P|\ge2`$ does that.

The letter’s de-duplicated assertion is made for a general finite list of primes and supplies no proof, so it is an asserted historical result and not an open problem. The note therefore restricts its open statement to the repeated series $`\mathcal R_P`$. A recovered proof of the letter’s assertion, or a transcendence statement for $`\mathcal D_P`$ with $`|P|\ge3`$, would be a different question and needs its own formulation.

The two-prime argument of the note is independent of the unprinted argument in the letter, and it is not the first public proof. Steve Fan posted the same factorisation, the same Hecke–Mahler reduction and the same conclusion in the discussion thread of the problem’s page on 26 June 2026 \[fan2026comment\], with follow-up remarks extending the argument to arbitrary coprime pairs; a further comment there observes that the argument does not seem to generalise immediately to $`|P|\ge3`$. The manuscript of the note was first released publicly on 22 July 2026, at commit `a9d3ab8`.

The statement of the problem has been formalised as a conjecture with an unfilled proof in the *Formal Conjectures* collection \[formalconjectures269\]. Its Nat-indexed series includes the empty-prefix least-common-multiple term, so its value differs from the conventional one by a rational constant; transporting a theorem across that boundary needs an explicit series-identification lemma, which is not supplied here.

<a id="long269:long:general-carries"></a>

## The abstract carry lemmas in their general form

The note applies the carry machinery to the literal $`\{2,3,5\}`$ orbit. The underlying statements are about integer sequences alone, they are reusable, and they are recorded here in the generality in which they are checked.

Let $`D=D_{\mathrm{sm}}B`$ with $`D_{\mathrm{sm}}=2^{u}3^{v}5^{w}`$ and $`\gcd(B,30)=1`$, and let $`(c_n)`$ be an integer sequence satisfying $`c_{n+1}=b_nc_n-Dm_n`$ for an integer radix word $`(b_n)`$ and forcing word $`(m_n)`$.

<div id="long269:long:denominator-reduction" class="proposition">

**Proposition 30** (conditional denominator reduction). *If $`c_n=D_{\mathrm{sm}}d_n`$ for every $`n`$, with $`D_{\mathrm{sm}}>0`$, then the recurrence, positivity, upper bound and window identity for $`(c_n)`$ reduce to the same four statements for $`(d_n)`$ with multiplier $`B`$ in place of $`D`$.*

</div>

Height absorption alone does not imply divisibility of a carry state. The identity $`DX_a=h_aN-Dv_a`$ of Lemma <a href="#long269:res:all-scale-lattice" data-reference-type="ref" data-reference="long269:res:all-scale-lattice">17</a> is what supplies it for the actual orbit, and Theorem <a href="#long269:res:actual-cancellation" data-reference-type="ref" data-reference="long269:res:actual-cancellation">18</a> is the instance in which the note uses it. The formal consumer takes the common-factor form as a hypothesis.

<div id="long269:long:windowconsumer" class="proposition">

**Proposition 31** (conditional extinction of bounded carries). *Let $`(b_n)`$ and $`(m_n)`$ be a radix word and a forcing word, let $`G:\mathbb{N}_{>0}\times\mathbb{N}\to\mathbb{N}`$, and assume cofinal local-window escape against $`G`$. Fix $`B>0`$ coprime to $`30`$. There is no integral sequence $`(d_n)`$ satisfying simultaneously $`d_{n+1}=b_nd_n-Bm_n`$, $`d_n>0`$ and $`|d_n|\le G(B,n)`$ for every $`n\ge0`$.*

</div>

<div class="proof">

*Proof.* Choose one escaping window $`(\ell,h)`$. The window identity gives $`d_{\ell+h}\equiv-BF_{\ell,h}`$ modulo $`|W_{\ell,h}|`$. The endpoint state is positive and at most $`G(B,\ell+h)`$, whereas the canonical positive residue of the right-hand side exceeds that bound, so Proposition <a href="#long269:res:consumer" data-reference-type="ref" data-reference="long269:res:consumer">20</a> applies. ◻

</div>

Coprimality with $`30`$ is used by the escape hypothesis to select a window; once a window is fixed, the finite contradiction does not use it. The formalisation carries the edge cases: a zero window base is excluded, a zero residue is represented by the full modulus, and positivity prevents the endpoint carry from vanishing. The packaged absorbed form takes a nonzero smooth factor, the exact factorisation $`c_n=D_{\mathrm{sm}}d_n`$, the absorbed recurrence for $`(c_n)`$ and the positive short bound for $`(d_n)`$, and derives the same contradiction in one statement.

<a id="long269:long:finite-geometry"></a>

## Worked finite examples

The ten smallest values of the running least common multiple at $`\{2,3,5\}`$ are tabulated in Section <a href="#long269:sec:lcm" data-reference-type="ref" data-reference="long269:sec:lcm">2</a>. They illustrate both parts of Proposition <a href="#long269:res:cell" data-reference-type="ref" data-reference="long269:res:cell">3</a>: the value is constant on $`\{5,6,7\}`$ and on $`\{9,10\}`$, and each change multiplies by a single prime, by $`2`$ at $`x=2,4,8`$, by $`3`$ at $`x=3,9`$ and by $`5`$ at $`x=5`$. Also $`\operatorname{L}(10)=8\cdot9\cdot5=360`$ is the least common multiple of the smooth numbers $`1,2,3,4,5,6,8,9,10`$.

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

Multiplying block radices along a run of blocks gives the product of the jump-word letters over that run: for instance $`b_1b_2=60`$ is the product of the four multipliers at $`3,4,5,8`$. Block $`4`$ is the only one among the first six carrying an internal power in both channels, and block $`5`$ carries neither, so its radix falls back to the terminal factor alone.

<a id="long269:long:experiments"></a>

## The finite-scan histogram

The scan of Section <a href="#long269:sec:evidence" data-reference-type="ref" data-reference="long269:sec:evidence">8</a> covers every $`B\le5000`$ coprime to $`30`$ and every start $`100\le\ell\le3000`$, with search depth permitted to $`24`$. It tested $`3{,}869{,}934`$ pairs, found an escaping window in every case, and the distribution of first successful lengths was
``` math
\resizebox{\linewidth}{!}{$\begin{array}{c|rrrrrrrrrrrrrrr}
h&4&5&6&7&8&9&10&11&12&13&14&15&16&17&18\\ \hline
\#&1&104&812&5437&51409&237423&735450&1431226&1132756&236752&34910&3076&521&49&8
\end{array}$}
```
The first case at the maximal observed length $`18`$ is $`B=917`$ at start $`\ell=2980`$, with endpoint jump index $`6179`$, window base $`18139852800000000`$, forcing $`13196471407660025821045`$, residue $`76322101735`$ and bound $`3896420420`$. An earlier run of the same checker over every $`B\le1000`$ coprime to $`30`$ and every start $`100\le\ell\le500`$ tested $`106{,}666`$ pairs with maximal first successful length $`14`$, whose first case is $`B=359`$ at start $`291`$, endpoint jump index $`627`$, base $`5038848000000`$, forcing $`25864575212865807`$, residue $`213175287`$ and bound $`15932659`$.

By Corollary <a href="#long269:res:no-bounded-length" data-reference-type="ref" data-reference="long269:res:no-bounded-length">23</a> these histograms describe a bounded region. The observed concentration at lengths $`10`$ to $`12`$ sits just above the necessary depth $`\bigl(\log_2K(B,\ell+h)-\log_215\bigr)/3`$ supplied by Proposition <a href="#long269:res:window-growth" data-reference-type="ref" data-reference="long269:res:window-growth">22</a>, which is what a reader should expect if the residues behave like generic ones inside this range.

<a id="long269:long:sources"></a>

## Source inventory

Each entry names an informal statement and the Lean declaration that carries it. Each link is pinned to its own immutable revision; the exact-reference inventory records the revisions and their comparison with the current public source commit.

| informal statement | linked Lean source |
|:---|:---|
| smooth lattice value | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L32) |
| pure-power height | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L37) |
| lattice kernel | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L41) |
| smooth prefix index set | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L47) |
| running least common multiple | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L54) |
| prefix value divides the height | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L60) |
| divisibility into the height | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L78) |
| first pure-power membership | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L85) |
| second pure-power membership | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L98) |
| third pure-power membership | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L111) |
| running-lcm identity | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L124) |
| cell relation | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L164) |
| cell constancy of the height | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L170) |
| cell constancy of the running value | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L180) |
| cell constancy of the kernel | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L192) |
| positive power sets | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L205) |
| channel cardinality | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L209) |
| exclusion of the origin | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L220) |
| channel disjointness | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L230) |
| positive jump channels | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L244) |
| positive jump count | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L250) |
| jump set with the origin | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L274) |
| jump count with the origin | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L279) |
| first height step | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L295) |
| second height step | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L306) |
| third height step | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L317) |
| first coordinate step | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L327) |
| second coordinate step | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L340) |
| third coordinate step | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L353) |
| exponent box | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L369) |
| point height | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L374) |
| height fibre | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L378) |
| fibre sum | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L385) |
| height-fibre normal form | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L407) |
| cubic majorant | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L431) |
| origin value | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L444) |
| value at two | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L451) |
| value at three | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L459) |
| value at six | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L468) |
| non-separation witness | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L480) |
| variable-base tail step | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L488) |
| expanded tail step | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L491) |
| smooth exponent shell | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L501) |
| short-interval uniqueness | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L510) |
| first-coordinate projection | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L544) |
| third-coordinate projection | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L586) |
| sorted quadratic estimate | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L630) |
| quadratic shell bound | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L647) |
| dyadic internal power | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L663) |
| internal-power uniqueness | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L669) |
| dyadic block base | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L751) |
| exact dyadic radix alphabet | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L762) |
| bounded-radix consequence | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L774) |
| rank-two certificate | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreePrimeRunningLcm.lean#L827) |
| no integer rotation orbit | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L154) |
| height factorisation | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L218) |
| kernel factorisation | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L259) |
| two-prime outer product | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L278) |
| two-prime vanishing minors | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L298) |
| uniform minors, general form | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L313) |
| uniform minors for primes | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L376) |
| no finite separation | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L388) |
| second-order minor | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L560) |
| third-order minor | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L570) |
| misleading proportional row | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L583) |
| failure of that proportionality | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/KernelCarryRank.lean#L592) |
| ordered block digit | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicBlockThresholdPartition.lean#L150) |
| normalised state step | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicOrderedTailRecurrence.lean#L110) |
| shell summability | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicShellSummability.lean#L142) |
| infinite tail recurrence | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicShellSummability.lean#L177) |
| integer-or-cofinally-far dichotomy | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/DyadicShellSummability.lean#L188) |
| boundary divisibility | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L51) |
| half-height identity | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L101) |
| window clearing identity | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L158) |
| all-scale rationality lattice | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L196) |
| normalised-state collision | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalLatticeReduction.lean#L296) |
| least positive residue | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L26) |
| positive representative range | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L31) |
| representative congruence | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L52) |
| escape condition | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L71) |
| finite natural-state contradiction | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L76) |
| contrapositive form | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L96) |
| integer least-positive-residue obstruction | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L110) |
| exact residue classifier | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ResidueEscape.lean#L138) |
| window base | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L417) |
| window forcing | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L422) |
| affine window identity | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L455) |
| scaled forcing identity | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L469) |
| integral carry window | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L480) |
| endpoint residue identification | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L497) |
| absorbed smooth factor | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L548) |
| common-factor cancellation | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L581) |
| reduced bound transfer | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L601) |
| reduced window transfer | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L612) |
| cofinal window hypothesis | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L629) |
| reduced-carry extinction | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L645) |
| absorbed-carry extinction | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RestrictedFloorSum.lean#L689) |
| real window identity | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L68) |
| escape from irrationality, general bound | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L327) |
| escape from irrationality, quadratic family | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L355) |
| escape from irrationality, actual bound | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L379) |
| producer equivalence, shifted tail | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L392) |
| producer equivalence, series value | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CofinalWindowEscapeEquivalence.lean#L398) |
| rationality-to-carry bridge | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalityCarryBridge.lean#L324) |
| the actual producer | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalityCarryBridge.lean#L397) |
| irrationality from the producer | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/RationalityCarryBridge.lean#L479) |
| bounded-radix alternative | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/BoundedRadixTailEscape.lean#L89) |
| rational value from an integral scaled tail | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/BoundedRadixTailEscape.lean#L183) |
| channel potential classifier | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/ThreeChannelBlockRigidity.lean#L59) |
| one-index lift extinction | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L178) |
| uniform lift extinction | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L238) |
| first-block sum | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L289) |
| four-state obstruction | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/CarryLiftExtinction.lean#L308) |
| residue-coboundary form | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L109) |
| carry interval | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L150) |
| digit interval | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L157) |
| symbolic realisation | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L293) |
| finite realised span | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/WeightedPhaseCarry.lean#L334) |
| Cantor-state confinement | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/PurePowerIrrationality.lean#L61) |
| state gap bound | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/PurePowerIrrationality.lean#L74) |
| small-form criterion | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/PurePowerIrrationality.lean#L94) |
| conditional assembly | [](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Erdos269/PurePowerIrrationality.lean#L156) |
| staircase index engine | [staircase indices](https://github.com/wcook04/plectis-lean-erdos249-257/blob/ee650b32b8b2cb98b94e5500df5370d85f7403b8/ErdosProblems/Shared/IrrationalRotationStaircase.lean#L271) |

<a id="sec:erdos-269-complete-family-map"></a>

# Complete result-family map

This section places every registered family for this problem in the shared 70-family reader order. The five display bands control exposition only; the separate promotion state currently covers 6 families and is reported but does not hide or strengthen any family. Mathematical statements and evidence modes come from the public claim registry. Across all eight problems the public result-atom catalog contains 681 exact packet coordinates; this problem contributes 65. The recovered source catalog contains 682 rows; 1 row(s) belong to families absent from the current claim registry and remain disclosed as detached source rows. Catalog rows expose bounded statement excerpts plus full-source digests, not a claim that every complete packet statement is reproduced here.

<a id="three-prime-lcm-cells"></a>

## Three prime lcm cells

**Reader position.** 6 of 70; display band: front door. Formal editorial disposition: merge. These are separate classifications.

**Reader entry.** Exact running-LCM product, logarithmic-cell constancy, coordinate jump ratios, and jump count.

Exact running-LCM product, logarithmic-cell constancy, coordinate jump ratios, and jump count.

**Authority and reach.** Lean kernel; Comparator-selected; locally proved result; novelty unassessed.

**Exact boundary.** Cell structure alone does not prove irrationality.

**Result-atom population.** 5 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** exact selected interface; 1 executable interface(s), 1 repository-registered selected result interface(s).

**Publication placement.** This family is also admitted to the short note.

<a id="two-prime-transcendence"></a>

## Two prime transcendence

**Reader position.** 17 of 70; display band: major result. Formal editorial disposition: hold. These are separate classifications.

**Reader entry.** Both two-prime running-lcm series are proved transcendental by an authored deduction from an external theorem.

Both two-prime running-lcm series are proved transcendental by an authored deduction from an external theorem.

**Authority and reach.** paper argument plus cited theorem; paper plus external theorem.

**Exact boundary.** Comparator cannot certify the external analytic input.

**Result-atom population.** 1 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** not applicable to comparator; 0 executable interface(s), 0 repository-registered selected result interface(s).

**Publication placement.** This family is also admitted to the short note.

<a id="weighted-phase-carry-observer"></a>

## Weighted phase carry observer

**Reader position.** 24 of 70; display band: mechanism. Formal editorial disposition: hold. These are separate classifications.

**Reader entry.** An exact weighted-phase carry recurrence splits into a finite residue digit and an uncontrolled integral quotient coboundary; an explicit function-faithful finite-dimensional observer then forces finite realised span.

An exact weighted-phase carry recurrence splits into a finite residue digit and an uncontrolled integral quotient coboundary; an explicit function-faithful finite-dimensional observer then forces finite realised span.

**Authority and reach.** Lean kernel; locally proved result; novelty unassessed.

**Exact boundary.** The recurrence supplies a finite residue coordinate but leaves an uncontrolled integral quotient coboundary; it proves neither a finite-state quotient nor a literal infinite realised span. Finite realised span requires an explicit factorisation through a finite-dimensional function-faithful observer, and scalar evaluation alone is insufficient. No irrationality conclusion follows from this observer alone. The actual rationality-to-positive-reduced-carry bridge is established separately; cofinal local-window escape remains open.

**Result-atom population.** 7 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** exact selected interface; 1 executable interface(s), 0 repository-registered selected result interface(s).

**Publication placement.** This family remains in the complete long record and is not a short-note headline.

- `ErdosProblems.Erdos269.carry_eq_residueDigit_add_coboundary`

- `ErdosProblems.Erdos269.carryResidue_mem_interval`

- `ErdosProblems.Erdos269.residueDigit_mem_interval`

- `ErdosProblems.Erdos269.finite_realisedSpan_of_factorisation`

<a id="height-fibre-and-shell"></a>

## Height fibre and shell

**Reader position.** 28 of 70; display band: mechanism. Formal editorial disposition: merge. These are separate classifications.

**Reader entry.** Finite height-fibre normal form and a quadratic smooth-shell multiplicity bound.

Finite height-fibre normal form and a quadratic smooth-shell multiplicity bound.

**Authority and reach.** Lean kernel; locally proved result; novelty unassessed.

**Exact boundary.** These fibre bounds are counting input, not an escape producer. The separate actual-series divisibility bridge is established.

**Result-atom population.** 5 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** represented by selected interface; 0 executable interface(s), 0 repository-registered selected result interface(s).

**Publication placement.** This family remains in the complete long record and is not a short-note headline.

- `ErdosProblems.Erdos269.finiteSmoothKernelSum_groupedByHeight`

- `ErdosProblems.Erdos269.smoothExponentShell_card_quadratic`

<a id="conditional-carry-escape"></a>

## Conditional carry escape

**Reader position.** 42 of 70; display band: frontier. Formal editorial disposition: hold. These are separate classifications.

**Reader entry.** Under the denominator-dependent cofinal local-window residue-escape predicate, no positive reduced carry can satisfy the exact multiplier recurrence together with its short bound. The load-bearing consumer is no_positive_reducedCarry_of_cofinalLocalWindowEscape; an absorbed nonzero common-factor carry reduces exactly to that consumer. CofinalLocalWindowEscape, windowBase, windowForcing, leastPositiveResidue, and the absorbed-carry bridge are subordinate finite-window mechanism evidence.

Under the denominator-dependent cofinal local-window residue-escape predicate, no positive reduced carry can satisfy the exact multiplier recurrence together with its short bound. The load-bearing consumer is no_positive_reducedCarry_of_cofinalLocalWindowEscape; an absorbed nonzero common-factor carry reduces exactly to that consumer. CofinalLocalWindowEscape, windowBase, windowForcing, leastPositiveResidue, and the absorbed-carry bridge are subordinate finite-window mechanism evidence.

**Authority and reach.** Lean kernel; Comparator-selected; conditional no-go consumer; novelty and significance unassessed.

**Exact boundary.** The representative assumes b,m : $`\mathbb{N}`$ $`\to`$ $`\mathbb{N}`$, shortBound : $`\mathbb{N}`$ $`\to`$ $`\mathbb{N}`$ $`\to`$ $`\mathbb{N}`$, CofinalLocalWindowEscape b m shortBound, and for each positive B coprime to 30 a positive integer-valued d with d(n+1) = (b n : $`\mathbb{Z}`$) d(n) $`-`$ (B : $`\mathbb{Z}`$) (m n : $`\mathbb{Z}`$) and Int.natAbs (d n) $`\le`$ shortBound B n; it then gives False. The absorbed-carry bridge additionally assumes smoothFactor $`\ne`$ 0, c n = smoothFactor \* d n, and the corresponding exact absorbed recurrence, then cancels that factor to the same reduced consumer. The representative remains a conditional consumer for arbitrary words. For the actual three-prime word, the rationality-to-reduced-carry bridge is established separately; the source-specific cofinal escape producer is not proved. This is not a \#269 endpoint or irrationality proof, and no actual-series identification, novelty, priority, significance, or external-review claim is made. It is one conditional window-carry family, distinct from the finite residue, rank-two, and weighted-phase observer families.

**Result-atom population.** 37 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** exact selected interface; 1 executable interface(s), 1 repository-registered selected result interface(s).

**Publication placement.** This family is also admitted to the short note.

- `ErdosProblems.Erdos269.CofinalLocalWindowEscape`

- `ErdosProblems.Erdos269.no_positive_reducedCarry_of_cofinalLocalWindowEscape`

- `ErdosProblems.Erdos269.windowBase`

- `ErdosProblems.Erdos269.windowForcing`

- `ErdosProblems.Erdos269.leastPositiveResidue`

- `ErdosProblems.Erdos269.no_positive_absorbedCarry_of_cofinalLocalWindowEscape`

<a id="rank-two-kernel-no-go"></a>

## Rank two kernel no go

**Reader position.** 54 of 70; display band: frontier. Formal editorial disposition: hold. These are separate classifications.

**Reader entry.** The 2,3,5 kernel is not rank one and its smallest displayed minor equals -1/15.

The 2,3,5 kernel is not rank one and its smallest displayed minor equals -1/15.

**Authority and reach.** Lean kernel; Comparator-selected; no-go result.

**Exact boundary.** Failure of rank one does not itself imply irrationality.

**Result-atom population.** 3 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** exact selected interface; 1 executable interface(s), 1 repository-registered selected result interface(s).

**Publication placement.** This family is also admitted to the short note.

<a id="dyadic-block-alphabet"></a>

## Dyadic block alphabet

**Reader position.** 62 of 70; display band: technical support. Formal editorial disposition: merge. These are separate classifications.

**Reader entry.** The exact dyadic block alphabet is 2, 6, 10, and 30.

The exact dyadic block alphabet is 2, 6, 10, and 30.

**Authority and reach.** Lean kernel; locally proved result; novelty unassessed.

**Exact boundary.** The finite alphabet does not supply the needed carry escape.

**Result-atom population.** 5 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** represented by selected interface; 0 executable interface(s), 0 repository-registered selected result interface(s).

**Publication placement.** This family remains in the complete long record and is not a short-note headline.

- `ErdosProblems.Erdos269.dyadicBlockBase235_cases`

<a id="three-prime-finite-search"></a>

## Three prime finite search

**Reader position.** 64 of 70; display band: technical support. Formal editorial disposition: hold. These are separate classifications.

**Reader entry.** A local-window checker searches 106666 denominator and start pairs and records small certificates.

A local-window checker searches 106666 denominator and start pairs and records small certificates.

**Authority and reach.** external exact computation; finite computation.

**Exact boundary.** Finite search is not a cofinal statement.

**Result-atom population.** 2 of 681 public coordinates. The public atom catalog groups them under this family.

**Comparator assurance.** not applicable to comparator; 0 executable interface(s), 0 repository-registered selected result interface(s).

**Publication placement.** This family remains in the complete long record and is not a short-note headline.

<div class="thebibliography">

10

P. Erdős and R. L. Graham, [*Old and New Problems and Results in Combinatorial Number Theory*](https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf), Monogr. Enseign. Math. 28, Geneva, 1980, p. 65. For a possibly infinite prime set $`Q`$, the page states the infinite-$`Q`$ irrationality and asks what happens for finite $`Q`$ with more than one element. P. Erdős, *On the irrationality of certain series: problems and results*, in A. Baker (ed.), *New Advances in Transcendence Theory*, Cambridge UP, 1988, pp. 102–109, doi:[10.1017/CBO9780511897184.009](https://doi.org/10.1017/CBO9780511897184.009). P. Erdős, [*Letter to the Editor*](https://www.fq.math.ca/Scanned/12-4/letter.pdf) (written 1 January 1973), Fibonacci Quart. **12** (1974), no. 4, p. 335. The letter poses the full series as a conjecture and asserts irrationality after retaining only the distinct running-LCM values, for a general finite list of primes, without proof. T. F. Bloom, [*Erdős Problem \#269*](https://www.erdosproblems.com/269), `erdosproblems.com/269`, accessed 28 July 2026 (page displays “last edited 28 December 2025”). The current record labels the finite-support problem open, cites `[ErGr80, p. 65]` and `[Er88c, p. 106]`, routes to the 1974 letter on p. 335, records the infinite-prime and de-duplicated variants, and explicitly describes its status as the website owner’s present assessment, with no guarantee of literature completeness. The Formal Conjectures Authors, [*FormalConjectures.ErdosProblems.`269`*](https://github.com/google-deepmind/formal-conjectures/blob/f776d2f2039351b00737ffcafb9d7d7666e1d9af/FormalConjectures/ErdosProblems/269.lean), Lean source at commit `f776d2f`, 2025, accessed 28 July 2026. T. M. Apostol, [*Introduction to Analytic Number Theory*](https://doi.org/10.1007/978-1-4757-5579-4), Springer, New York, 1976. A. Hildebrand, *On the number of positive integers $`\le x`$ and free of prime factors $`>y`$*, J. Number Theory **22** (1986), 289–307, [DOI](https://doi.org/10.1016/0022-314X(86)90013-2). H. L. Montgomery and R. C. Vaughan, *The Prime Number Theorem*, in *Multiplicative Number Theory I: Classical Theory*, Cambridge Studies in Advanced Mathematics 97, Cambridge University Press, 2007, pp. 168–198, doi:[10.1017/CBO9780511618314.008](https://doi.org/10.1017/CBO9780511618314.008). V. Kovač and T. Tao, [*On several irrationality problems for Ahmes series*](https://doi.org/10.1007/s10474-025-01528-0), Acta Math. Hungar. **175** (2025), 572–608, doi:[10.1007/s10474-025-01528-0](https://doi.org/10.1007/s10474-025-01528-0); [arXiv:2406.17593](https://arxiv.org/abs/2406.17593), 2024. Y. Bugeaud and M. Laurent, *Transcendence and continued fraction expansion of values of Hecke–Mahler series*, Acta Arith. **209** (2023), 59–90, doi:10.4064/aa220323-18-1; [authors’ Online First PDF](https://irma.math.unistra.fr/~bugeaud/travaux/BuMLAA.pdf), [arXiv:2203.12901v1](https://arxiv.org/abs/2203.12901). Theorem 1.1 appears on p. 3 of the linked Online First PDF; its introduction, p. 2, attributes the zero-shift case to Loxton and van der Poorten. The original result is Theorem 8, p. 40, of \[loxtonvdp1977\]. J. H. Loxton and A. J. van der Poorten, *Arithmetic properties of certain functions in several variables III*, Bull. Austral. Math. Soc. **16** (1977), 15–47, [doi:10.1017/S0004972700022978](https://doi.org/10.1017/S0004972700022978); Theorem 8, p. 40. S. Fan, comment on Erdős Problem \#269, [erdosproblems.com forum, thread 269](https://www.erdosproblems.com/forum/thread/269), 26 June 2026. The comment gives the running-LCM identity for every $`|P|`$, the two-channel factorisation, the Hecke–Mahler reduction, and the transcendence conclusion for $`|P|=2`$; follow-up comments there note the extension to arbitrary coprime pairs.

</div>
